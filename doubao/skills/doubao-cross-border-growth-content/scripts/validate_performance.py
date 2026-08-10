#!/usr/bin/env python3
"""Validate ecommerce performance math and budget-action safety.

Input is a JSON object from a file or stdin. The script uses only the Python
standard library and returns a JSON report. It does not choose budgets.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


VALID_MATURITY = {"mature", "partial", "immature", "unknown"}
VALID_PROFIT_STATUS = {"verified", "scenario_only", "unknown"}


def relative_close(actual: float, expected: float, tolerance: float) -> bool:
    scale = max(abs(actual), abs(expected), 1e-9)
    return abs(actual - expected) / scale <= tolerance


def positive_number(data: dict[str, Any], key: str) -> float | None:
    value = data.get(key)
    if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0:
        return float(value)
    return None


def compute_metrics(data: dict[str, Any]) -> dict[str, float]:
    spend = positive_number(data, "spend")
    revenue = positive_number(data, "revenue")
    orders = positive_number(data, "orders")
    clicks = positive_number(data, "clicks")
    impressions = positive_number(data, "impressions")

    metrics: dict[str, float] = {}
    if clicks is not None and impressions is not None:
        metrics["ctr"] = clicks / impressions
    if spend is not None and clicks is not None:
        metrics["cpc"] = spend / clicks
    if orders is not None and clicks is not None:
        metrics["cvr"] = orders / clicks
    if spend is not None and orders is not None:
        metrics["cpa"] = spend / orders
    if revenue is not None and spend is not None:
        metrics["roas"] = revenue / spend
        metrics["acos"] = spend / revenue
    if spend is not None and impressions is not None:
        metrics["cpm"] = spend / impressions * 1000
    return metrics


def validate(data: dict[str, Any], tolerance: float) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    blockers: list[str] = []
    metrics = compute_metrics(data)

    reported = data.get("reported", {})
    if reported is None:
        reported = {}
    if not isinstance(reported, dict):
        errors.append("reported must be an object")
        reported = {}

    for key, expected in metrics.items():
        actual = reported.get(key)
        if isinstance(actual, (int, float)) and not isinstance(actual, bool):
            if not relative_close(float(actual), expected, tolerance):
                blockers.append(
                    f"reported_{key}_conflicts: reported={actual}, computed={expected:.6f}"
                )

    maturity = data.get("maturity", "unknown")
    if not isinstance(maturity, str) or maturity not in VALID_MATURITY:
        errors.append(f"maturity must be one of {sorted(VALID_MATURITY)}")
        maturity = "unknown"

    profitability = data.get("profitability", {})
    if profitability is None:
        profitability = {}
    if not isinstance(profitability, dict):
        errors.append("profitability must be an object")
        profitability = {}

    profit_status = profitability.get("status", "unknown")
    if not isinstance(profit_status, str) or profit_status not in VALID_PROFIT_STATUS:
        errors.append(
            f"profitability.status must be one of {sorted(VALID_PROFIT_STATUS)}"
        )
        profit_status = "unknown"

    decision = data.get("decision", {})
    if decision is None:
        decision = {}
    if not isinstance(decision, dict):
        errors.append("decision must be an object")
        decision = {}

    current_budget = positive_number(decision, "current_budget")
    proposed_budget = positive_number(decision, "proposed_budget")
    action = decision.get("action")
    budget_increase = (
        current_budget is not None
        and proposed_budget is not None
        and proposed_budget > current_budget
    )
    scaling = budget_increase or action == "scale"

    if budget_increase and action != "scale":
        blockers.append("budget_increase_is_scaling_even_if_action_has_another_label")

    if scaling:
        if maturity != "mature":
            blockers.append("scaling_blocked_by_data_maturity")
        if profit_status != "verified":
            blockers.append("scaling_blocked_by_unverified_profitability")

        safety_roas = positive_number(profitability, "safety_roas")
        safety_cpa = positive_number(profitability, "safety_cpa")
        if safety_roas is None and safety_cpa is None:
            blockers.append("scaling_blocked_without_verified_safety_threshold")
        if safety_roas is not None:
            roas = metrics.get("roas")
            if roas is None:
                blockers.append("scaling_blocked_without_reconciled_roas")
            elif roas < safety_roas:
                blockers.append(
                    f"scaling_blocked_below_safety_roas: {roas:.4f} < {safety_roas:.4f}"
                )
        if safety_cpa is not None:
            cpa = metrics.get("cpa")
            if cpa is None:
                blockers.append("scaling_blocked_without_reconciled_cpa")
            elif cpa > safety_cpa:
                blockers.append(
                    f"scaling_blocked_above_safety_cpa: {cpa:.4f} > {safety_cpa:.4f}"
                )

    if profit_status != "verified":
        warnings.append("profitability thresholds are scenario-only or unknown")
    if maturity != "mature":
        warnings.append("data is not mature enough for a final winner or scaling decision")

    blockers = list(dict.fromkeys(blockers))
    return {
        "ok": not errors and not blockers,
        "computed_metrics": {key: round(value, 6) for key, value in metrics.items()},
        "maturity": maturity,
        "profitability_status": profit_status,
        "scaling_detected": scaling,
        "errors": errors,
        "warnings": warnings,
        "blockers": blockers,
    }


def load_json(path: str) -> dict[str, Any]:
    if path == "-":
        payload = json.load(sys.stdin)
    else:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("input JSON must be an object")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="JSON file path or - for stdin")
    parser.add_argument(
        "--tolerance",
        type=float,
        default=0.02,
        help="relative tolerance for reported-versus-computed metrics",
    )
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    if not math.isfinite(args.tolerance) or args.tolerance < 0:
        parser.error("--tolerance must be a non-negative finite number")

    try:
        report = validate(load_json(args.input), args.tolerance)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "errors": [str(exc)]}, ensure_ascii=False))
        return 2

    print(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2 if args.pretty else None,
            sort_keys=True,
        )
    )
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
