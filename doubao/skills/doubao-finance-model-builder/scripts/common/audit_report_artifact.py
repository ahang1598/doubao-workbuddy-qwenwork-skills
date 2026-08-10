#!/usr/bin/env python3
"""Hash-lock a generated report to the deterministic calculation file it cites."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(report: Path, calculated: Path, workflow: str) -> dict:
    errors: list[str] = []
    report_hash = sha256(report) if report.is_file() else None
    calculated_hash = sha256(calculated) if calculated.is_file() else None
    text = report.read_text(encoding="utf-8") if report.is_file() else ""
    marker = f"CALCULATED_SHA256:{calculated_hash}" if calculated_hash else None
    if not report.is_file():
        errors.append("主要报告不存在")
    if not calculated.is_file():
        errors.append("确定性计算文件不存在")
    if marker and marker not in text:
        errors.append("报告未包含与确定性计算文件一致的哈希标记")
    if "[INCOMPLETE]" in text or "{{" in text or "TODO" in text.upper():
        errors.append("报告仍含未完成占位符")
    return {
        "status": "FAIL" if errors else "PASS",
        "workflow": workflow,
        "artifact_type": "generated_report",
        "artifact_path": str(report),
        "artifact_sha256": report_hash,
        "calculated_path": str(calculated),
        "calculated_sha256": calculated_hash,
        "errors": errors,
        "warnings": [],
        "metrics": {"calculated_hash_marker_present": bool(marker and marker in text)},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="审计并锁定由确定性计算生成的报告")
    parser.add_argument("report", type=Path)
    parser.add_argument("calculated", type=Path)
    parser.add_argument("--workflow", required=True, choices=("dcf", "comps", "lbo", "three_statements"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.report, args.calculated, args.workflow)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
