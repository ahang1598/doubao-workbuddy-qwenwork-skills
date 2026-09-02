#!/usr/bin/env python3
"""
quick_validate.py — 对一个 skill 目录做轻量结构校验。

校验项（通用）：
- SKILL.md 存在
- 含 YAML frontmatter
- frontmatter 仅含允许的键（name / description / license / allowed-tools / metadata / compatibility）
- name / description 必填且符合规范

可选 --type {A|C}：按流程 skill 类型加额外结构校验
  - A：流程编排型（需 scripts/response_io.py + 并发设计）
  - C：长 SOP 型（SKILL.md 行数 + references 拆分）
  （Tier 1 wrapper / 通用工具 / 浏览器 skill 的校验走 linkfox-skill-creator，本器不覆盖）
可选 --strict：把软警告升级为错误

实现：基于公开的 skill 结构惯例；fallback 到极小的 frontmatter 解析器，因此
不强依赖 PyYAML。
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

try:
    import yaml  # type: ignore
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


ALLOWED_PROPERTIES = {
    "name",
    "description",
    "license",
    "allowed-tools",
    "metadata",
    "compatibility",
}

SCRIPT_DIR = Path(__file__).resolve().parent
CREATOR_ROOT = SCRIPT_DIR.parent
LINKFOXAGENT_V2_ROOT = CREATOR_ROOT.parent
CANONICAL_RUNTIME_FILES = {
    "response_io.py": SCRIPT_DIR / "response_io.py",
    "linkfox_paths.py": LINKFOXAGENT_V2_ROOT / "_shared" / "linkfox_paths.py",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _check_runtime_file_hashes(skill_path: Path, filenames: tuple[str, ...]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    errors.extend(_check_placeholder_leaks(skill_path))
    for filename in filenames:
        target = skill_path / "scripts" / filename
        canonical = CANONICAL_RUNTIME_FILES[filename]
        if not target.exists():
            errors.append(f"缺少 scripts/{filename}")
            continue
        if not canonical.exists():
            warnings.append(f"无法找到标准文件 {canonical}，跳过 scripts/{filename} hash 校验")
            continue
        if _sha256(target) != _sha256(canonical):
            errors.append(
                f"scripts/{filename} 与标准源不同；请从 {canonical} 复制最新版，保持路径规范同步"
            )
    return errors, warnings


def _parse_frontmatter_fallback(text: str) -> dict:
    """极小 frontmatter 解析器：仅支持 `key: value` 单行格式。"""
    result: dict = {}
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(
                f"frontmatter 解析失败（未安装 PyYAML，仅支持单行 key: value）：{raw_line!r}"
            )
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if value.startswith(("'", '"')) and value.endswith(("'", '"')) and len(value) >= 2:
            value = value[1:-1]
        result[key] = value
    return result


SKILL_NAME_RE = re.compile(r"^[a-z0-9-]+$")


def _validate_skill_name(name: str, label: str) -> tuple[bool, str]:
    if not SKILL_NAME_RE.match(name):
        return False, (
            f"{label} '{name}' 只能包含小写字母、数字和连字符 '-' "
            "(allowed pattern: ^[a-z0-9-]+$)"
        )
    if name.startswith("-") or name.endswith("-") or "--" in name:
        return False, (
            f"{label} '{name}' 不能以 '-' 开头/结尾，也不能包含连续 '--'"
        )
    if len(name) > 64:
        return False, (
            f"{label} '{name}' 过长（{len(name)} 字符）。最大 64 字符。"
        )
    return True, "ok"


def _validate_frontmatter(frontmatter: dict, directory_name: str) -> tuple[bool, str]:
    unexpected_keys = set(frontmatter.keys()) - ALLOWED_PROPERTIES
    if unexpected_keys:
        return False, (
            f"Unexpected key(s) in SKILL.md frontmatter: {', '.join(sorted(unexpected_keys))}. "
            f"Allowed properties are: {', '.join(sorted(ALLOWED_PROPERTIES))}"
        )

    if "name" not in frontmatter:
        return False, "Missing 'name' in frontmatter"
    if "description" not in frontmatter:
        return False, "Missing 'description' in frontmatter"

    name = frontmatter.get("name", "")
    if not isinstance(name, str):
        return False, f"Name must be a string, got {type(name).__name__}"
    name = name.strip()
    ok, msg = _validate_skill_name(directory_name, "目录名")
    if not ok:
        return False, msg
    ok, msg = _validate_skill_name(name, "frontmatter name")
    if not ok:
        return False, msg
    if name != directory_name:
        return False, (
            f"frontmatter name '{name}' 必须与目录名 '{directory_name}' 完全一致"
        )

    description = frontmatter.get("description", "")
    if not isinstance(description, str):
        return False, f"Description must be a string, got {type(description).__name__}"
    description = description.strip()
    if description:
        if "<" in description or ">" in description:
            return False, "Description cannot contain angle brackets (< or >)"
        if len(description) > 1024:
            return False, (
                f"Description is too long ({len(description)} characters). "
                f"Maximum is 1024 characters."
            )

    compatibility = frontmatter.get("compatibility", "")
    if compatibility:
        if not isinstance(compatibility, str):
            return False, (
                f"Compatibility must be a string, got {type(compatibility).__name__}"
            )
        if len(compatibility) > 500:
            return False, (
                f"Compatibility is too long ({len(compatibility)} characters). "
                f"Maximum is 500 characters."
            )

    return True, "ok"


def _check_description_bilingual(description: str) -> list[str]:
    """检查 description 双语 + 反向补漏。返回软警告列表。"""
    warnings = []
    has_chinese = bool(re.search(r"[\u4e00-\u9fff]", description))
    has_english = bool(re.search(r"[a-zA-Z]{3,}", description))
    if not (has_chinese and has_english):
        warnings.append(
            "description 缺少双语触发短语（应同时含中文和英文）"
        )

    reverse_keywords = ["即使", "even if", "也应", "should also", "尽管", "casual"]
    if not any(kw in description.lower() for kw in [k.lower() for k in reverse_keywords]):
        warnings.append(
            "description 缺少反向补漏关键词（即使 / even if / 也应 / should also 之一）"
        )
    return warnings


PLACEHOLDER_PATTERNS = (
    (re.compile(r"\blinkfox-(?:xxx|yyy)\b"), "linkfox-xxx/linkfox-yyy 示例占位符"),
    (re.compile(r"\blinkfox-<[^>\s]+>"), "linkfox-<...> 模板占位符"),
    (re.compile(r"<YYYY-MM-DD>|<session>"), "落盘路径日期/session 模板占位符"),
    (re.compile(r"\blinkfox-generated-media-\d+\.(?:png|jpe?g|webp|gif|mp4|webm|mov|mp3|wav)\b"), "linkfox-generated-media 示例媒体文件名"),
    (re.compile(r"(?:^|/)\.\.\./linkfox/"), "省略号形式的伪绝对路径"),
)


def _check_placeholder_leaks(skill_path: Path) -> list[str]:
    """拦截从 creator 模板照抄到产物里的占位符、假路径与示例媒体文件名。"""
    errors: list[str] = []
    # creator 自身包含模板示例；只校验被创建/被优化的目标 skill。
    if skill_path.resolve() == CREATOR_ROOT.resolve():
        return errors

    scan_files = [skill_path / "SKILL.md"]
    refs_dir = skill_path / "references"
    if refs_dir.is_dir():
        scan_files.extend(refs_dir.rglob("*.md"))

    for path in scan_files:
        if not path.exists() or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            for pattern, label in PLACEHOLDER_PATTERNS:
                if pattern.search(line):
                    errors.append(
                        f"{path.relative_to(skill_path)}:{lineno} 残留 {label}，"
                        "必须替换为 linkfoxagent-v2/ 实时目录中存在的真实 skill slug"
                    )
    return errors


def _check_archetype_a(skill_path: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    runtime_errors, runtime_warnings = _check_runtime_file_hashes(
        skill_path,
        ("response_io.py", "linkfox_paths.py"),
    )
    errors.extend(runtime_errors)
    warnings.extend(runtime_warnings)

    # 并发编排软检查：多步流程若完全没有并发设计标注，提醒确认是否应并行。
    try:
        skill_md = (skill_path / "SKILL.md").read_text(encoding="utf-8")
    except OSError:
        skill_md = ""
    step_headings = re.findall(r"(?m)^#{2,4}\s*步骤\s*\S", skill_md)
    # 大纲化后步骤多写成总览表行（| S1 ... | S2 ...），也算作步骤数
    table_steps = re.findall(r"(?m)^\|\s*S\d+\b", skill_md)
    step_count = max(len(step_headings), len(table_steps))

    concurrency_markers = ("依赖", "并行", "并发", "执行编排")
    if step_count >= 2 and not any(m in skill_md for m in concurrency_markers):
        warnings.append(
            "多步流程未见并发设计标注（缺 依赖 / 并行 / 执行编排）——"
            "确认是否所有步骤都必须串行；无数据依赖的步骤应并行以缩短墙钟时间"
        )

    # 大纲化护栏（治长流程注意力失焦）：长流程的 SKILL.md 应当是大纲，
    # 单步血肉拆到 references/steps/S<N>.md，agent 按步加载。
    body_lines = _count_body_lines(skill_md)
    has_steps_dir = (skill_path / "references" / "steps").is_dir()
    if not has_steps_dir and (step_count >= 4 or body_lines > 200):
        warnings.append(
            f"长流程未大纲化（步骤数={step_count}，SKILL.md 正文≈{body_lines} 行，"
            "且无 references/steps/）——建议把 SKILL.md 收成大纲（执行编排 + 流水线总览表），"
            "单步细节拆到 references/steps/S<N>.md 按步加载，避免一次性灌入导致注意力失焦"
        )
    return errors, warnings


def _count_body_lines(skill_md: str) -> int:
    """统计 SKILL.md 去掉 frontmatter 后的正文行数。"""
    text = skill_md
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            nl = text.find("\n", end + 1)
            text = text[nl + 1:] if nl != -1 else ""
    return len([ln for ln in text.splitlines()])


def _check_archetype_c(skill_path: Path, strict: bool) -> tuple[list[str], list[str]]:
    errors = []
    warnings = []
    skill_md_path = skill_path / "SKILL.md"
    line_count = len(skill_md_path.read_text(encoding="utf-8").splitlines())
    if line_count > 500:
        msg = f"类型 C 的 SKILL.md 行数 {line_count} > 500，应拆 references/"
        if strict:
            errors.append(msg)
        else:
            warnings.append(msg)
    if not (skill_path / "references").exists():
        warnings.append("类型 C 通常需要 references/ 拆分领域知识，未发现")
    return errors, warnings


def validate_skill(skill_path, archetype: str | None = None, strict: bool = False):
    """archetype 参数保留为内部变量名（A/B/C/D），CLI 暴露为 --type。"""
    skill_path = Path(skill_path)

    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        return False, ["SKILL.md not found"], []

    content = skill_md.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return False, ["No YAML frontmatter found"], []

    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return False, ["Invalid frontmatter format"], []

    frontmatter_text = match.group(1)

    if HAS_YAML:
        try:
            frontmatter = yaml.safe_load(frontmatter_text)
            if not isinstance(frontmatter, dict):
                return False, ["Frontmatter must be a YAML dictionary"], []
        except yaml.YAMLError as e:
            return False, [f"Invalid YAML in frontmatter: {e}"], []
    else:
        try:
            frontmatter = _parse_frontmatter_fallback(frontmatter_text)
        except ValueError as e:
            return False, [str(e)], []

    ok, msg = _validate_frontmatter(frontmatter, skill_path.name)
    if not ok:
        return False, [msg], []

    errors: list[str] = []
    warnings: list[str] = []

    description = (frontmatter.get("description") or "").strip()
    desc_warnings = _check_description_bilingual(description)
    if strict:
        errors.extend(desc_warnings)
    else:
        warnings.extend(desc_warnings)

    if archetype:
        archetype = archetype.upper()
        if archetype == "A":
            arch_errs, arch_warns = _check_archetype_a(skill_path)
            errors.extend(arch_errs)
            if strict:
                errors.extend(arch_warns)
            else:
                warnings.extend(arch_warns)
        elif archetype == "C":
            arch_errs, arch_warns = _check_archetype_c(skill_path, strict)
            errors.extend(arch_errs)
            warnings.extend(arch_warns)
        else:
            return False, [f"Unknown skill type: {archetype} (expected A/C)"], []

    return len(errors) == 0, errors, warnings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("skill_path", help="skill 目录路径")
    parser.add_argument(
        "--type",
        dest="skill_type",
        choices=["A", "C", "a", "c"],
        help="按流程 skill 类型 (A 编排 / C 长 SOP) 加额外结构校验",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="把软警告升级为错误",
    )
    args = parser.parse_args()

    valid, errors, warnings = validate_skill(args.skill_path, args.skill_type, args.strict)

    if errors:
        print("ERRORS:")
        for e in errors:
            print(f"  - {e}")
    if warnings:
        print("WARNINGS:")
        for w in warnings:
            print(f"  - {w}")
    if valid:
        print("Skill is valid!")
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
