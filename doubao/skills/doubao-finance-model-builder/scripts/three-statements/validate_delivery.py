#!/usr/bin/env python3
"""Validate a three-statement delivery against a direct workbook audit."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any


def finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate(
    manifest: dict[str, Any],
    workbook_audit: dict[str, Any],
    *,
    audit_directory: Path | None = None,
    verify_workbook: bool = True,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    checks: list[dict[str, Any]] = []

    def record(name: str, passed: bool, actual: Any, expected: Any, message: str) -> None:
        checks.append({
            "check": name,
            "actual": actual,
            "expected": expected,
            "status": "通过" if passed else "错误",
            "notes": message,
        })
        if not passed:
            errors.append(message)

    # These items describe research provenance or manual visual QA. Calculation
    # integrity is deliberately taken only from the direct workbook audit below.
    source_coverage = manifest.get("source_coverage_ratio")
    record(
        "关键字段来源覆盖率",
        finite_number(source_coverage) and abs(float(source_coverage) - 1.0) <= 1e-12,
        source_coverage,
        1.0,
        "关键字段来源覆盖率必须为100%",
    )
    record(
        "字段来源映射审计",
        manifest.get("source_mapping_audit_passed") is True,
        manifest.get("source_mapping_audit_passed"),
        True,
        "必须逐字段确认来源ID真实存在且与使用值一致",
    )
    conflicts = manifest.get("source_conflict_count")
    record("未解决来源冲突", conflicts == 0, conflicts, 0, "存在未解决的数据来源冲突或未执行冲突检查")
    hardcodes = manifest.get("hardcoded_calculation_count")
    record("计算区硬编码", hardcodes == 0, hardcodes, 0, "计算区存在硬编码结果或未执行检查")
    plugs = manifest.get("unexplained_plug_count")
    record("未解释配平项", plugs == 0, plugs, 0, "存在未解释的现金、权益或其他配平项")

    audit_status = workbook_audit.get("status")
    record("直接工作簿审计状态", audit_status == "PASS", audit_status, "PASS", "直接工作簿审计未通过")
    audit_errors = workbook_audit.get("errors")
    record("直接审计错误清零", isinstance(audit_errors, list) and not audit_errors, audit_errors, [], "直接工作簿审计仍有错误")
    audit_warnings = workbook_audit.get("warnings")
    if isinstance(audit_warnings, list) and audit_warnings:
        warnings.extend(f"直接工作簿审计警告：{item}" for item in audit_warnings)

    metrics = workbook_audit.get("metrics") if isinstance(workbook_audit.get("metrics"), dict) else {}
    metric_requirements = {
        "formula_error_count": 0,
        "direct_circular_count": 0,
        "duplicate_semantic_key_count": 0,
        "failed_check_rows": 0,
    }
    for key, expected in metric_requirements.items():
        actual = metrics.get(key)
        record(f"直接审计.{key}", actual == expected, actual, expected, f"直接工作簿审计指标不合格：{key}")
    formula_count = metrics.get("formula_count")
    record("工作簿公式数量", finite_number(formula_count) and formula_count > 0, formula_count, ">0", "工作簿未检测到公式")
    required_count = metrics.get("required_sheet_count")
    present_count = metrics.get("present_required_sheet_count")
    record(
        "必需工作表完整",
        finite_number(required_count) and required_count > 0 and present_count == required_count,
        present_count,
        required_count,
        "必需工作表不完整",
    )

    if verify_workbook:
        workbook_path_value = workbook_audit.get("workbook_path")
        workbook_path = Path(workbook_path_value) if isinstance(workbook_path_value, str) and workbook_path_value else None
        if workbook_path is not None and not workbook_path.is_absolute() and audit_directory is not None:
            workbook_path = audit_directory / workbook_path
        exists = workbook_path is not None and workbook_path.is_file()
        record("审计目标工作簿存在", exists, str(workbook_path) if workbook_path else None, "existing file", "直接审计引用的工作簿不存在")
        expected_hash = workbook_audit.get("workbook_sha256")
        actual_hash = file_sha256(workbook_path) if exists else None
        record(
            "工作簿哈希锁定",
            isinstance(expected_hash, str) and len(expected_hash) == 64 and actual_hash == expected_hash,
            actual_hash,
            expected_hash,
            "工作簿已在直接审计后发生变化，或审计未提供有效SHA-256",
        )

    visual = manifest.get("all_visible_sheets_rendered")
    if visual is not True:
        warnings.append("尚未确认所有用户可见工作表均完成视觉检查")

    status = "FAIL" if errors else ("INCOMPLETE" if warnings else "PASS")
    return {
        "model_status_code": status,
        "model_status": {"PASS": "通过", "INCOMPLETE": "未完成", "FAIL": "失败"}[status],
        "errors": errors,
        "warnings": warnings,
        "checks": checks,
    }


def self_test() -> dict[str, Any]:
    manifest = {
        "source_coverage_ratio": 1.0,
        "source_mapping_audit_passed": True,
        "source_conflict_count": 0,
        "hardcoded_calculation_count": 0,
        "unexplained_plug_count": 0,
        "all_visible_sheets_rendered": True,
    }
    audit = {
        "status": "PASS",
        "errors": [],
        "warnings": [],
        "metrics": {
            "formula_error_count": 0,
            "direct_circular_count": 0,
            "duplicate_semantic_key_count": 0,
            "failed_check_rows": 0,
            "formula_count": 1,
            "required_sheet_count": 7,
            "present_required_sheet_count": 7,
        },
    }
    return validate(manifest, audit, verify_workbook=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="校验三表工作簿交付审计清单")
    parser.add_argument("manifest", type=Path, nargs="?")
    parser.add_argument("--workbook-audit", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        result = self_test()
    else:
        if args.manifest is None or args.workbook_audit is None:
            parser.error("Provide a manifest JSON and --workbook-audit, or use --self-test")
        result = validate(
            json.loads(args.manifest.read_text(encoding="utf-8")),
            json.loads(args.workbook_audit.read_text(encoding="utf-8")),
            audit_directory=args.workbook_audit.parent,
        )
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if result["model_status_code"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
