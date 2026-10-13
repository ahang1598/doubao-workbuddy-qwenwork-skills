#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile


try:
    from scripts._bootstrap import ensure_skill_import_root
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _bootstrap import ensure_skill_import_root

ROOT = ensure_skill_import_root(__file__)

from labor_contract_review.review_result import (
    ReportValidationError,
    extract_issues,
    normalize_report_markdown,
    validate_report_markdown,
)
from scripts.annotate_docx import annotate_docx, build_default_output_path, resolve_document_path


def main() -> int:
    parser = argparse.ArgumentParser(description="根据已输出的 Markdown 报告生成 Word 批注版。")
    parser.add_argument("--report", "-r", type=Path, required=True, help="已输出的 Markdown 审查报告。")
    parser.add_argument("--document", "-d", type=Path, required=True, help="原始 docx 文件路径。")
    parser.add_argument("--output", "-o", type=Path, default=None, help="批注版 docx 输出路径。")
    parser.add_argument("--issues-output", type=Path, default=None, help="可选：保存从报告反解析出的 issues JSON。")
    args = parser.parse_args()

    report_markdown = normalize_report_markdown(args.report.read_text(encoding="utf-8"))
    try:
        validate_report_markdown(report_markdown)
    except ReportValidationError as exc:
        print(f"报告校验失败：{exc}", file=sys.stderr)
        return 1

    issues = extract_issues({"report_markdown": report_markdown}, report_markdown)
    document_path = resolve_document_path(args.document)
    output_path = args.output or build_default_output_path(document_path)

    with tempfile.TemporaryDirectory() as tempdir:
        issues_path = args.issues_output or Path(tempdir) / "issues.json"
        issues_path.parent.mkdir(parents=True, exist_ok=True)
        issues_path.write_text(json.dumps({"issues": issues}, ensure_ascii=False, indent=2), encoding="utf-8")
        result, warnings = annotate_docx(document_path, issues_path, output_path)

    if result.status == "deliverable":
        print(f"批注合同下载地址：{result.output_path}")
        print(f"成功写入批注：{result.applied_count} 条；跳过：{result.skipped_count + len(warnings)} 条")
    elif result.status == "no_annotation_needed":
        print(result.message or "合同无风险，无需生成批注版。")
    else:
        print(result.message or "批注版生成失败。", file=sys.stderr)
    for warning in warnings:
        print(f"警告：{warning}", file=sys.stderr)
    return 0 if result.status != "failed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
