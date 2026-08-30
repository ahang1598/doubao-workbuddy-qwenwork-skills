#!/usr/bin/env python3
"""Validate the QwenWork suite source tree and quick-template assets."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

from validate_docx import inspect_docx


SUITE_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_PLUGIN_FIELDS = ("name", "displayName", "displayNameEn", "description", "descriptionEn", "skills")
REQUIRED_SKILL_FIELDS = (
    "name_en",
    "name",
    "displayName",
    "description",
    "description_en",
    "argument-hint",
    "argument-hint-en",
    "user-invocable",
)
QUICK_SKILLS = {
    "cn-prenuptial-property-agreement",
    "cn-marital-property-agreement",
    "cn-divorce-agreement",
    "cn-cohabitation-agreement",
    "cn-family-property-partition",
    "cn-adult-voluntary-guardianship-agreement",
}
BANNED_ACTIVE_PATTERNS = (
    "必须恰好四个",
    "选择卡固定为四个",
    "第四个选项固定命名",
    "其他（请填写）",
    "多选需求拆成数张单选卡",
    "每轮最多两张",
)
EXPECTED_DISPLAY_NAME = "婚姻家事法律专家"
REQUIRED_QWEN_DOCX_RULES = (
    "scripts/validate_docx.py",
    "不得调用 LibreOffice",
    "不得先运行转换器再判断缺失",
)


def parse_frontmatter(path: Path) -> dict[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("missing opening frontmatter fence")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise ValueError("missing closing frontmatter fence") from exc
    result: dict[str, str] = {}
    for line in lines[1:end]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, sep, value = line.partition(":")
        if not sep:
            raise ValueError(f"invalid frontmatter line: {line}")
        result[key.strip()] = value.strip().strip('"').strip("'")
    return result


def validate(root: Path = SUITE_ROOT) -> list[str]:
    errors: list[str] = []
    plugin_path = root / ".qoder-plugin" / "plugin.json"
    try:
        plugin = json.loads(plugin_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"invalid plugin.json: {exc}"]
    if not isinstance(plugin, dict):
        errors.append("plugin.json root must be an object")
        return errors
    for key in REQUIRED_PLUGIN_FIELDS:
        if not plugin.get(key):
            errors.append(f"plugin.json missing {key}")
    if plugin.get("displayName") != EXPECTED_DISPLAY_NAME:
        errors.append(f"plugin displayName must be {EXPECTED_DISPLAY_NAME}")
    if not re.fullmatch(r"[a-z0-9-]+", str(plugin.get("name", ""))):
        errors.append("plugin name must be an English slug")

    suite = json.loads((root / "suite.json").read_text(encoding="utf-8"))
    if plugin.get("name") != suite.get("name"):
        errors.append("plugin and suite names differ")
    if plugin.get("version") != suite.get("version"):
        errors.append("plugin and suite versions differ")

    declared = []
    for item in plugin.get("skills", []):
        skill_dir = (root / item).resolve()
        try:
            skill_dir.relative_to(root.resolve())
        except ValueError:
            errors.append(f"skill path escapes suite: {item}")
            continue
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.is_file():
            errors.append(f"missing SKILL.md: {item}")
            continue
        declared.append(skill_dir.name)
        try:
            frontmatter = parse_frontmatter(skill_file)
        except ValueError as exc:
            errors.append(f"{skill_file.relative_to(root)}: {exc}")
            continue
        for key in REQUIRED_SKILL_FIELDS:
            if key not in frontmatter or frontmatter[key] == "":
                errors.append(f"{skill_file.relative_to(root)} missing {key}")
        if frontmatter.get("name_en") != skill_dir.name:
            errors.append(f"{skill_file.relative_to(root)} name_en must match its directory")
        if frontmatter.get("user-invocable") not in {"true", "false"}:
            errors.append(f"{skill_file.relative_to(root)} user-invocable must be true or false")

    actual = sorted(path.parent.name for path in (root / "skills").glob("*/SKILL.md"))
    if sorted(declared) != actual:
        errors.append("plugin skills list does not exactly match skills/*/SKILL.md")
    if sorted(suite.get("implemented_skills", [])) != actual:
        errors.append("suite implemented_skills does not exactly match skills/*/SKILL.md")

    link_pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    for path in [root / "README.md", *sorted((root / "references").glob("*.md")), *sorted((root / "skills").glob("*/SKILL.md"))]:
        text = path.read_text(encoding="utf-8")
        for link in link_pattern.findall(text):
            if "://" in link or link.startswith("#"):
                continue
            if not (path.parent / link).resolve().exists():
                errors.append(f"broken link in {path.relative_to(root)}: {link}")

    active_files = [root / "README.md", root / "README_EN.md", *sorted((root / "references").glob("*.md")), *sorted((root / "skills").glob("*/SKILL.md"))]
    for path in active_files:
        text = path.read_text(encoding="utf-8")
        for banned in BANNED_ACTIVE_PATTERNS:
            if banned in text:
                errors.append(f"obsolete Qwen interaction rule in {path.relative_to(root)}: {banned}")

    deliverable_text = (root / "references" / "deliverable-standard.md").read_text(encoding="utf-8")
    for required in REQUIRED_QWEN_DOCX_RULES:
        if required not in deliverable_text:
            errors.append(f"deliverable standard missing Qwen DOCX rule: {required}")

    for skill_name in QUICK_SKILLS:
        docx = root / "skills" / skill_name / "assets" / "quick-template.docx"
        if not docx.is_file():
            errors.append(f"missing quick DOCX asset: {docx.relative_to(root)}")
            continue
        result = inspect_docx(docx)
        if not result["ok"]:
            errors.append(f"invalid quick DOCX {docx.relative_to(root)}: {'; '.join(result['errors'])}")
        if result.get("author") != EXPECTED_DISPLAY_NAME:
            errors.append(f"quick DOCX author must be {EXPECTED_DISPLAY_NAME}: {docx.relative_to(root)}")

    qa_path = root / "references" / "quick-template-qa.json"
    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    qa_hashes = {item["skill"]: item["sha256"] for item in qa.get("templates", [])}
    if set(qa_hashes) != QUICK_SKILLS:
        errors.append("quick-template QA manifest does not exactly match quick-template skills")
    for skill_name in QUICK_SKILLS:
        docx = root / "skills" / skill_name / "assets" / "quick-template.docx"
        if docx.is_file():
            actual_hash = hashlib.sha256(docx.read_bytes()).hexdigest()
            if qa_hashes.get(skill_name) != actual_hash:
                errors.append(f"quick-template QA hash mismatch: {docx.relative_to(root)}")

    for junk in root.rglob(".DS_Store"):
        errors.append(f"release source contains macOS metadata: {junk.relative_to(root)}")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print(json.dumps({"ok": False, "errors": errors}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps({"ok": True, "skills": 17, "quick_docx_assets": 6}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
