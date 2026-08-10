#!/usr/bin/env python3
"""Validate that DCF JSON, workbook, scenarios and report share one model."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


def finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def validate(normalized: dict[str, Any], calculated: dict[str, Any], audit: dict[str, Any], workbook_audit: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    incomplete: list[str] = []
    warnings: list[str] = []
    checks: list[dict[str, Any]] = []

    base_name = calculated.get("base_scenario")
    base = calculated.get("scenarios", {}).get(base_name, {})
    expected_wacc = base.get("wacc")
    expected_per_share = base.get("per_share_value")

    def add(name: str, passed: bool, actual: Any, expected: Any, message: str, level: str = "error") -> None:
        checks.append({"check": name, "actual": actual, "expected": expected, "status": "通过" if passed else ("未完成" if level == "incomplete" else "错误"), "notes": message})
        if not passed:
            (incomplete if level == "incomplete" else errors).append(message)

    add("直接工作簿审计", workbook_audit.get("status") == "PASS" and workbook_audit.get("workflow") == "dcf", {"status": workbook_audit.get("status"), "workflow": workbook_audit.get("workflow")}, {"status": "PASS", "workflow": "dcf"}, "DCF最终工作簿必须通过直接审计")
    direct_metrics = workbook_audit.get("metrics") if isinstance(workbook_audit.get("metrics"), dict) else {}
    for key in ("formula_error_count", "direct_circular_count", "external_link_formula_count"):
        add(f"直接审计.{key}", direct_metrics.get(key) == 0, direct_metrics.get(key), 0, f"直接工作簿审计指标不合格：{key}")
    add("计算验证状态", audit.get("calculation_validation_status") == "PASS", audit.get("calculation_validation_status"), "PASS", "标准化输入与确定性计算验证必须先通过")
    add("关键字段来源覆盖率", finite(audit.get("source_coverage_ratio")) and abs(audit["source_coverage_ratio"] - 1.0) <= 1e-12, audit.get("source_coverage_ratio"), 1.0, "关键字段来源覆盖率必须为100%")
    add("字段来源映射审计", audit.get("source_mapping_audit_passed") is True, audit.get("source_mapping_audit_passed"), True, "必须逐字段确认来源ID真实存在且与使用值一致")
    add("未解决来源冲突", audit.get("source_conflict_count") == 0, audit.get("source_conflict_count"), 0, "存在未解决来源冲突或未执行冲突检查")
    add("分证券元数据", audit.get("share_class_metadata_complete") is True, audit.get("share_class_metadata_complete"), True, "分证券必须完整记录估值日股数、不复权价格、日期、币种、汇率、独立市值和来源")
    add("公司行动检索", audit.get("corporate_action_review_complete") is True, audit.get("corporate_action_review_complete"), True, "必须从最近可靠股本日至估值日检索并记录所有股本变动公告")
    add("估值日股数", audit.get("share_count_as_of_valuation_date") is True, audit.get("share_count_as_of_valuation_date"), True, "分证券股数必须反映估值日前已经生效的送股、转增、增发、回购、转换和ADR/H股变化")
    add("股价股数口径", audit.get("price_share_basis_consistent") is True, audit.get("price_share_basis_consistent"), True, "市场价值必须使用不复权近端收盘价乘以同口径估值日股数")
    add("独立市值反向校验", audit.get("market_cap_cross_check_passed") is True, audit.get("market_cap_cross_check_passed"), True, "股价乘股数必须与同日独立市值来源在容差内一致")
    add("未计入公司行动", audit.get("corporate_action_unapplied_count") == 0, audit.get("corporate_action_unapplied_count"), 0, "存在估值日前已生效但未计入股数的公司行动")
    add("关键输出硬编码", audit.get("hardcoded_key_output_count") == 0, audit.get("hardcoded_key_output_count"), 0, "摘要、DCF、情景或敏感性存在硬编码关键结果")
    add("情景共享模型", audit.get("scenario_uses_shared_model") is True, audit.get("scenario_uses_shared_model"), True, "三种情景必须调用同一DCF模型")
    add("敏感性共享模型", audit.get("sensitivity_uses_shared_model") is True, audit.get("sensitivity_uses_shared_model"), True, "敏感性必须重算同一DCF模型")

    def compare_outputs(name: str, values: Any, expected: Any, tolerance: float) -> None:
        if not isinstance(values, dict) or len(values) < 2 or not finite(expected):
            add(name, False, values, expected, f"{name}缺少至少两个用户可见位置或计算基准", "incomplete")
            return
        bad = {key: value for key, value in values.items() if not finite(value) or not math.isclose(float(value), float(expected), rel_tol=1e-9, abs_tol=tolerance)}
        add(name, not bad, bad if bad else values, expected, f"{name}与确定性计算结果不一致")

    compare_outputs("WACC跨页一致性", audit.get("wacc_outputs"), expected_wacc, 1e-10)
    compare_outputs("每股价值跨产物一致性", audit.get("per_share_outputs"), expected_per_share, 1e-6)

    def rollforward(key: str) -> None:
        rows = audit.get(key)
        if not isinstance(rows, list) or not rows:
            add(key, False, rows, ">0", f"缺少{key}")
            return
        for index, row in enumerate(rows):
            difference = row.get("difference") if isinstance(row, dict) else None
            tolerance = row.get("tolerance", 0.01) if isinstance(row, dict) else None
            passed = finite(difference) and finite(tolerance) and abs(float(difference)) <= float(tolerance)
            period = row.get("period", index + 1) if isinstance(row, dict) else index + 1
            add(f"{key}.{period}", passed, difference, f"abs <= {tolerance}", f"{key}在期间{period}未通过")

    if audit.get("three_statements_in_scope") is True:
        rollforward("balance_sheet_checks")
        rollforward("cash_rollforward_checks")

    for key, label in (("share_bridge_difference", "股数桥"), ("equity_bridge_difference", "企业价值到股权价值桥")):
        value = audit.get(key)
        add(label, finite(value) and abs(float(value)) <= 1e-6, value, 0, f"{label}不平或未提供检查")

    tv_share = base.get("terminal_value_share_of_ev")
    if not finite(tv_share):
        add("终值占比", False, tv_share, "<=85%", "无法计算基准情景终值占比")
    elif tv_share > 0.90:
        add("终值占比", False, tv_share, "<=90%", "终值占比超过90%，不得输出点估值")
    elif tv_share > 0.85:
        add("终值占比", False, tv_share, "<=85%", "终值占比超过85%，必须延长显性期或重建稳态过渡", "incomplete")
    elif tv_share > 0.75:
        warnings.append("基准情景终值占比超过75%，应扩大敏感性并降低结论置信度")

    if audit.get("all_visible_sheets_rendered") is not True:
        incomplete.append("尚未确认所有用户可见工作表完成视觉检查")
    unresolved = audit.get("unresolved_warning_count")
    if unresolved not in (0, None):
        incomplete.append(f"仍有 {unresolved} 项未解决警告")

    status = "FAIL" if errors else ("INCOMPLETE" if incomplete else "PASS")
    return {
        "model_status_code": status,
        "model_status": {"PASS": "通过", "INCOMPLETE": "未完成", "FAIL": "失败"}[status],
        "errors": errors,
        "incomplete_reasons": incomplete,
        "warnings": warnings,
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="校验DCF最终Excel、报告与确定性计算的一致性")
    parser.add_argument("normalized", type=Path)
    parser.add_argument("calculated", type=Path)
    parser.add_argument("audit", type=Path)
    parser.add_argument("--workbook-audit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = validate(
        json.loads(args.normalized.read_text(encoding="utf-8")),
        json.loads(args.calculated.read_text(encoding="utf-8")),
        json.loads(args.audit.read_text(encoding="utf-8")),
        json.loads(args.workbook_audit.read_text(encoding="utf-8")),
    )
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if result["model_status_code"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
