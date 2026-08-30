#!/usr/bin/env python3
"""Validate style spec completeness.

Checks a style spec Markdown file against the quality checklist
from extraction-pipeline.md Step 4:
  - All 6 modules present and non-empty
  - Forbidden list ≥ 3 items
  - Validation samples ≥ 2 excerpts
  - Metadata header present with required fields
  - Confidence matches sample_count

Usage:
  python spec_validator.py --input style_spec.md

Output JSON:
  {
    "valid": true/false,
    "score": "5/6",
    "checks": [ {"name": "...", "pass": true, "detail": "..."}, ... ]
  }
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys


# The 6 required modules per style-spec-template.md
REQUIRED_MODULES = [
    "整体调性",
    "语气与视角",
    "句式与节奏",
    "标志性表达",
    "禁用清单",
    "验证样本",
]

METADATA_FIELDS = ["version", "sample_count", "confidence", "created_at", "updated_at", "changelog"]


def _extract_yaml_header(text: str) -> dict | None:
    """Extract YAML front-matter between --- markers."""
    m = re.search(r"^---\s*\n(.*?)\n---", text, re.DOTALL | re.MULTILINE)
    if not m:
        return None
    header = {}
    for line in m.group(1).strip().split("\n"):
        line = line.strip()
        if line.startswith("-"):
            continue  # changelog list items
        if ":" in line:
            key, _, val = line.partition(":")
            header[key.strip()] = val.strip().strip('"').strip("'")
    return header


def _find_module_sections(text: str) -> dict[str, str]:
    """Find each module's heading and its content block."""
    sections = {}
    # Match ## or ### headings containing module names
    for mod in REQUIRED_MODULES:
        pattern = rf"#+\s*(?:模块[一二三四五六]：)?{re.escape(mod)}\s*\n(.*?)(?=\n#+\s|\Z)"
        m = re.search(pattern, text, re.DOTALL)
        if m:
            sections[mod] = m.group(1).strip()
    return sections


def _count_list_items(text: str) -> int:
    """Count Markdown list items (- or * or numbered)."""
    return len(re.findall(r"^\s*(?:[-*]\s+|\d+[.)]\s+)", text, re.MULTILINE))


def _count_blockquotes(text: str) -> int:
    """Count blockquote blocks (consecutive > lines = 1 block)."""
    blocks = re.findall(r"((?:^>\s*.*\n?)+)", text, re.MULTILINE)
    return len(blocks)


def validate(text: str) -> dict:
    """Run all validation checks on a style spec."""
    checks = []

    # Check 1: Metadata header
    header = _extract_yaml_header(text)
    if header:
        missing = [f for f in METADATA_FIELDS if f not in header and f != "changelog"]
        checks.append({
            "name": "元信息头完整",
            "pass": len(missing) == 0,
            "detail": f"缺少字段: {missing}" if missing else "version/sample_count/confidence/日期均存在",
        })
    else:
        checks.append({
            "name": "元信息头完整",
            "pass": False,
            "detail": "未找到 YAML front-matter (--- ... ---)",
        })

    # Check 2: All 6 modules present and non-empty
    sections = _find_module_sections(text)
    for mod in REQUIRED_MODULES:
        content = sections.get(mod, "")
        is_present = len(content) > 10  # more than trivial
        checks.append({
            "name": f"模块「{mod}」非空",
            "pass": is_present,
            "detail": f"{len(content)} 字" if is_present else "模块缺失或内容过少",
        })

    # Check 3: Forbidden list ≥ 3 items
    forbidden_content = sections.get("禁用清单", "")
    forbidden_count = _count_list_items(forbidden_content)
    checks.append({
        "name": "禁用清单 ≥ 3 条",
        "pass": forbidden_count >= 3,
        "detail": f"找到 {forbidden_count} 条",
    })

    # Check 4: Validation samples ≥ 2 excerpts
    sample_content = sections.get("验证样本", "")
    sample_count = _count_blockquotes(sample_content)
    checks.append({
        "name": "验证样本 ≥ 2 段",
        "pass": sample_count >= 2,
        "detail": f"找到 {sample_count} 段引用",
    })

    # Check 5: Confidence matches sample_count
    if header:
        try:
            sc = int(header.get("sample_count", 0))
            conf = header.get("confidence", "")
            expected = "high" if sc >= 5 else ("medium" if sc >= 3 else "low")
            checks.append({
                "name": "confidence 与 sample_count 匹配",
                "pass": conf == expected,
                "detail": f"sample_count={sc}, confidence={conf}, 期望={expected}",
            })
        except (ValueError, TypeError):
            checks.append({
                "name": "confidence 与 sample_count 匹配",
                "pass": False,
                "detail": "sample_count 不是有效数字",
            })

    passed = sum(1 for c in checks if c["pass"])
    total = len(checks)

    return {
        "valid": passed == total,
        "score": f"{passed}/{total}",
        "passed": passed,
        "total": total,
        "checks": checks,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate style spec completeness")
    parser.add_argument("--input", required=True, help="Path to style spec Markdown file")
    args = parser.parse_args()

    input_path = os.path.abspath(args.input)
    with open(input_path, "r", encoding="utf-8") as f:
        text = f.read()

    if not text.strip():
        print(json.dumps({"error": "Empty input file"}, ensure_ascii=False))
        sys.exit(2)

    result = validate(text)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
