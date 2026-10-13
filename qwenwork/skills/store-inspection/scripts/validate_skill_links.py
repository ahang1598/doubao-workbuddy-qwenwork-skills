#!/usr/bin/env python3
"""Skill 文档静态校验脚本。

校验内容（与 pack.py 打包白名单口径保持一致）：

1. 死链校验：扫描 SKILL.md / references/**/*.md 中所有 Markdown 链接 [text](path)
   与裸引用 `path.md` / `path.md#anchor`，校验目标文件存在
2. 边界校验：SKILL.md 主文件**只能**引用 references/ 下的文档，
   不允许引用 deploy/ / scripts/ / tests/ / 任意仓库根目录其他文件
   （因为 pack.py 打包时这些文件都不会进入分发包）
3. 自引用校验：references/ 下的文档不允许引用打包白名单之外的路径
   （白名单：references/** + SKILL.md + scripts/**/*.py + requirements.txt）

退出码：
- 0 全部通过
- 1 发现违规

用法：
    python scripts/validate_skill_links.py
    python scripts/validate_skill_links.py --strict-anchors  # 同时校验锚点存在
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 与 pack.py 的 INCLUDE_PATTERNS 对齐（分发包内允许出现的路径前缀）
PACK_ALLOWED_PREFIXES: tuple[str, ...] = (
    "references/",
    "scripts/",
    "SKILL.md",
    "requirements.txt",
)

# SKILL.md 严格允许的引用前缀（不允许引用 scripts/ / requirements.txt 等运行态文件）
SKILL_ALLOWED_PREFIXES: tuple[str, ...] = ("references/",)

# 匹配 Markdown 链接 [text](target) —— target 中可能含 # 锚点
MARKDOWN_LINK_PATTERN = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

# 匹配反引号包裹的相对路径引用，如 `../shared/hard-constraints.md#H6`
INLINE_PATH_PATTERN = re.compile(
    r"`((?:\.{1,2}/|references/|deploy/|scripts/|tests/)[^\s`]+\.md(?:#[^\s`]+)?)`"
)

# 匹配 ATX 标题，用于建立锚点表
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)

# 匹配显式 HTML anchor，如 <a id="H1"></a> / <a name="H1"></a>
HTML_ANCHOR_PATTERN = re.compile(
    r"""<a\s+(?:id|name)\s*=\s*["']([^"']+)["'][^>]*>""",
    re.IGNORECASE,
)


def _is_external(target: str) -> bool:
    """判断是否为外部链接 / 锚点 / mailto / 协议链接 / 占位符，不在校验范围内。"""
    if not target:
        return True
    lower = target.lower()
    if lower.startswith(("http://", "https://", "mailto:", "tel:", "ftp://")):
        return True
    # 纯锚点（同文件跳转）
    if target.startswith("#"):
        return True
    # 占位符（如消息模板中的 {表单链接} / {form_link}）
    if "{" in target or "}" in target:
        return True
    return False


# 匹配 Markdown 围栏代码块（``` 或 ~~~ 包裹）
FENCED_CODE_BLOCK_PATTERN = re.compile(
    r"^([ \t]*)(`{3,}|~{3,})[^\n]*\n.*?\n[ \t]*\2[ \t]*$",
    re.DOTALL | re.MULTILINE,
)


def _strip_code_blocks(text: str) -> str:
    """把围栏代码块内容替换为等量空行，保留行号但去掉其中的链接。"""
    def _replace(match: re.Match[str]) -> str:
        block = match.group(0)
        return "\n" * block.count("\n")

    return FENCED_CODE_BLOCK_PATTERN.sub(_replace, text)


def _slugify_anchor(text: str) -> str:
    """生成 GitHub-flavored anchor slug（粗略实现，去除 emoji / 空白 / 标点）。"""
    text = text.strip().lower()
    # 删除 markdown 行内代码反引号
    text = text.replace("`", "")
    # 把空格转成 -
    text = re.sub(r"\s+", "-", text)
    # 删除标点（保留中文、英文、数字、连字符）
    text = re.sub(r"[^\w\u4e00-\u9fff-]", "", text, flags=re.UNICODE)
    return text


def _collect_anchors(file_path: Path) -> set[str]:
    """收集一个 markdown 文件中所有合法 anchor。

    包含 3 类来源：
    1. 标题 slugify 后的 anchor（GitHub-flavored 近似实现）
    2. 显式 HTML anchor（如 `<a id="H1"></a>`）
    3. 显式 HTML anchor 的小写形式（GitHub 行为）
    """
    if not file_path.exists():
        return set()
    text = file_path.read_text(encoding="utf-8")
    anchors: set[str] = set()
    for _hashes, title in HEADING_PATTERN.findall(text):
        anchors.add(_slugify_anchor(title))
    for explicit in HTML_ANCHOR_PATTERN.findall(text):
        anchors.add(explicit)
        anchors.add(explicit.lower())
    return anchors


def _resolve(source_file: Path, raw_target: str) -> tuple[Path, str]:
    """把链接里的相对路径解析成绝对路径 + anchor。"""
    target = raw_target.split("#", 1)
    rel_path = target[0]
    anchor = target[1] if len(target) > 1 else ""

    # 去掉前后空白与可能的 angle brackets
    rel_path = rel_path.strip().strip("<>")

    base_dir = source_file.parent
    if rel_path.startswith("/"):
        # 绝对路径以仓库根为基准
        abs_path = ROOT / rel_path.lstrip("/")
    else:
        abs_path = (base_dir / rel_path).resolve()
    return abs_path, anchor


def _iter_markdown_files() -> list[Path]:
    """扫描 SKILL.md + references 下所有 markdown 文件。"""
    files: list[Path] = []
    skill_md = ROOT / "SKILL.md"
    if skill_md.exists():
        files.append(skill_md)
    references_root = ROOT / "references"
    if references_root.exists():
        files.extend(sorted(references_root.rglob("*.md")))
    return files


def _extract_link_targets(file_path: Path) -> list[tuple[str, int]]:
    """从一个 markdown 文件中提取所有 (raw_target, line_number)。

    包含 Markdown 链接 + 反引号内联路径引用。
    """
    raw_text = file_path.read_text(encoding="utf-8")
    # 把代码块挖空，避免把消息模板里的 [👉 立即填写]({表单链接}) 误识别为真实链接
    text = _strip_code_blocks(raw_text)
    targets: list[tuple[str, int]] = []

    for match in MARKDOWN_LINK_PATTERN.finditer(text):
        raw = match.group(2)
        if _is_external(raw):
            continue
        line_no = text[: match.start()].count("\n") + 1
        targets.append((raw, line_no))

    for match in INLINE_PATH_PATTERN.finditer(text):
        raw = match.group(1)
        line_no = text[: match.start()].count("\n") + 1
        targets.append((raw, line_no))

    return targets


def _relative_to_root(abs_path: Path) -> str:
    try:
        return abs_path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(abs_path)


def _is_pack_allowed(rel_path_posix: str) -> bool:
    return any(rel_path_posix.startswith(prefix) for prefix in PACK_ALLOWED_PREFIXES)


def _is_skill_allowed(rel_path_posix: str) -> bool:
    return any(rel_path_posix.startswith(prefix) for prefix in SKILL_ALLOWED_PREFIXES)


def validate(strict_anchors: bool = False) -> int:
    """执行校验，返回违规数。"""
    files = _iter_markdown_files()
    if not files:
        print("[错误] 未找到任何 SKILL.md 或 references/ 下的 markdown 文件")
        return 1

    violations: list[str] = []
    anchor_cache: dict[Path, set[str]] = {}

    for source in files:
        rel_source = _relative_to_root(source)
        is_skill_md = rel_source == "SKILL.md"

        for raw_target, line_no in _extract_link_targets(source):
            abs_target, anchor = _resolve(source, raw_target)
            rel_target = _relative_to_root(abs_target)

            # 1. 死链校验：目标文件必须存在
            if not abs_target.exists():
                violations.append(
                    f"[死链] {rel_source}:{line_no} → `{raw_target}` "
                    f"（目标 `{rel_target}` 不存在）"
                )
                continue

            # 2. 边界校验
            if is_skill_md and not _is_skill_allowed(rel_target):
                violations.append(
                    f"[SKILL.md 越界] {rel_source}:{line_no} → `{raw_target}` "
                    f"（仅允许引用 references/ 下的文档，目标 `{rel_target}` 在白名单外）"
                )
                continue

            if (not is_skill_md) and not _is_pack_allowed(rel_target):
                violations.append(
                    f"[分发包外] {rel_source}:{line_no} → `{raw_target}` "
                    f"（目标 `{rel_target}` 不在 pack.py 打包白名单内，"
                    f"打包后会变成死链）"
                )
                continue

            # 3. 锚点校验（可选，严格模式才开启）
            if strict_anchors and anchor:
                if abs_target not in anchor_cache:
                    anchor_cache[abs_target] = _collect_anchors(abs_target)
                expected_slug = _slugify_anchor(anchor)
                if expected_slug not in anchor_cache[abs_target]:
                    violations.append(
                        f"[锚点缺失] {rel_source}:{line_no} → `{raw_target}` "
                        f"（目标文件 `{rel_target}` 不存在 anchor `{anchor}`）"
                    )

    if violations:
        print(f"❌ 发现 {len(violations)} 个问题：\n")
        for item in violations:
            print(f"  - {item}")
        return len(violations)

    print(f"✅ 校验通过：{len(files)} 个 markdown 文件，所有链接均有效，且符合分发包边界。")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="校验 SKILL.md / references 下文档的链接有效性与分发包边界"
    )
    parser.add_argument(
        "--strict-anchors",
        action="store_true",
        help="同时校验锚点是否存在（基于 GitHub-flavored slugify 规则，可能有误报）",
    )
    args = parser.parse_args()

    violation_count = validate(strict_anchors=args.strict_anchors)
    sys.exit(0 if violation_count == 0 else 1)


if __name__ == "__main__":
    main()
