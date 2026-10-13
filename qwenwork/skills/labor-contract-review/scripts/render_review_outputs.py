#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys


try:
    from scripts._bootstrap import ensure_skill_import_root
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _bootstrap import ensure_skill_import_root

ROOT = ensure_skill_import_root(__file__)

from labor_contract_review.review_result import ReportValidationError, load_raw_result, write_outputs


def _safe_stem(file_name: str) -> str:
    base = Path(file_name.strip()).stem
    safe = "".join(
        char if (char.isalnum() or char in "._-" or "\u4e00" <= char <= "\u9fff") else "_"
        for char in base
    )
    return safe.strip("_") or "review"


def main() -> int:
    parser = argparse.ArgumentParser(description="将审查结果整理为 Markdown 报告和批注 JSON。")
    parser.add_argument("--input", "-i", type=Path, required=True, help="审查结果 JSON。")
    parser.add_argument("--output-dir", "-o", type=Path, default=ROOT / "output")
    parser.add_argument("--stem", default=None, help="输出文件名前缀，默认使用输入文件名。")
    parser.add_argument("--file-name", default=None, help="原合同文件名；未传 --stem 时用于生成安全的输出文件名前缀。")
    parser.add_argument("--no-print-report", action="store_true", help="只生成文件，不把 Markdown 报告正文打印到 stdout。")
    args = parser.parse_args()

    stem = args.stem or (_safe_stem(args.file_name) if args.file_name else _safe_stem(args.input.name))
    try:
        report_path, issues_path = write_outputs(load_raw_result(args.input), args.output_dir, stem)
    except ReportValidationError as exc:
        print(f"报告校验失败：{exc}", file=sys.stderr)
        return 1
    if not args.no_print_report:
        print(report_path.read_text(encoding="utf-8").rstrip())
    print(f"Markdown report: {report_path}", file=sys.stderr)
    print(f"Issues JSON: {issues_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
