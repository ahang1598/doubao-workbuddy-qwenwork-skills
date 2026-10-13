#!/usr/bin/env python3
"""Validate a registration checklist against its structured source input."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from build_registration_checklist import (
    InputError,
    STATUS_LABELS,
    allowed_public_emails,
    detect_pii,
    detect_unapproved_output_emails,
    ensure_distinct_paths,
    read_json,
    render_markdown,
    validate_payload,
)


REQUIRED_HEADINGS = [
    "## 适用范围与结论",
    "## 关键缺口",
    "## 分阶段执行清单",
    "## 材料总表",
    "## 冲突与待确认项",
    "## 来源台账",
    "## Tool 与数据授权状态",
    "## 隐私与使用限制",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Source JSON")
    parser.add_argument("--checklist", required=True, type=Path, help="Checklist Markdown")
    parser.add_argument("--strict", action="store_true", help="Apply all release gates")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    issues: list[str] = []
    warnings: list[str] = []
    try:
        ensure_distinct_paths(args.input, args.checklist, None)
        data, raw = read_json(args.input)
        payload, input_warnings = validate_payload(data)
        try:
            text = args.checklist.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"IO_ERROR: 无法读取清单：{exc}", file=sys.stderr)
            return 3
    except InputError as exc:
        print(f"INPUT_ERROR: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"IO_ERROR: {exc}", file=sys.stderr)
        return 3

    for heading in REQUIRED_HEADINGS:
        if heading not in text:
            issues.append(f"缺少必需标题：{heading}")
    for item in payload["items"]:
        marker = f"<!-- item:{item['id']} -->"
        if text.count(marker) != 1:
            issues.append(f"事项标记必须且只能出现一次：{item['id']}")
            continue
        start = text.index(marker)
        remaining_markers = [
            position
            for other in payload["items"]
            if other["id"] != item["id"]
            and (position := text.find(f"<!-- item:{other['id']} -->", start + len(marker))) != -1
        ]
        section_end = text.find("\n## ", start + len(marker))
        end_candidates = remaining_markers + ([section_end] if section_end != -1 else [])
        end = min(end_candidates) if end_candidates else len(text)
        segment = text[start:end]
        label = f"[{STATUS_LABELS[item['evidence_status']]}]"
        if label not in segment:
            issues.append(f"事项区块缺少状态标签：{item['id']} {label}")
        for source_id in item["source_ids"]:
            if source_id not in segment:
                issues.append(f"事项区块缺少来源：{item['id']} {source_id}")
    for source in payload["sources"]:
        if source["id"] not in text:
            issues.append(f"来源未出现在清单中：{source['id']}")
    pii = detect_pii(text)
    if pii:
        issues.append("清单含可能的个人敏感数据：" + ", ".join(pii))
    unapproved_emails = detect_unapproved_output_emails(text, allowed_public_emails(data))
    if unapproved_emails:
        issues.append("清单含未获准的邮箱地址：" + ", ".join(unapproved_emails))
    if "密码" not in text or "验证码" not in text:
        warnings.append("隐私限制未显式覆盖密码和验证码")
    warnings.extend(input_warnings)

    if args.strict:
        if warnings:
            issues.extend(f"严格模式告警：{warning}" for warning in warnings)
        expected_hash = hashlib.sha256(raw).hexdigest()
        expected_markdown = render_markdown(payload, expected_hash, input_warnings)
        if text != expected_markdown:
            issues.append("严格模式要求清单与当前输入的确定性生成结果完全一致；请重新生成后再校验")
        if not payload["items"]:
            issues.append("严格模式至少需要一个事项")
        if not any(source["official"] for source in payload["sources"]):
            issues.append("严格模式至少需要一个官方来源；否则只能作为通用准备框架")
        if not any(item["evidence_status"] == "confirmed" for item in payload["items"]):
            issues.append("严格模式至少需要一个已确认事项；否则不得标记核验完成")

    result = {
        "ok": not issues,
        "strict": args.strict,
        "item_count": len(payload["items"]),
        "issue_count": len(issues),
        "warning_count": len(warnings),
        "issues": issues,
        "warnings": warnings,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
