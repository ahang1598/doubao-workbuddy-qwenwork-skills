#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministic per-line gross margin without embedded business thresholds."""
from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List


def decimal(value: Any, field: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field} must be a finite decimal") from exc
    if not result.is_finite():
        raise ValueError(f"{field} must be a finite decimal")
    return result


def text(value: Decimal) -> str:
    return format(value, "f")


def calculation_metadata(payload: Dict[str, Any]) -> Dict[str, str]:
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        raise ValueError("metadata is required")
    unit = metadata.get("unit")
    period = metadata.get("period")
    tolerance_value = metadata.get("tolerance")
    if not unit or not period or tolerance_value is None:
        raise ValueError("metadata.unit, metadata.period and metadata.tolerance are required")
    tolerance = decimal(tolerance_value, "metadata.tolerance")
    if tolerance < 0:
        raise ValueError("metadata.tolerance must be non-negative")
    return {
        "unit": str(unit),
        "period": str(period),
        "formula": "contribution = revenue - direct_cost; gross_margin_pct = contribution / revenue",
        "tolerance": text(tolerance),
        "numeric_serialization": "decimal_string",
    }


def flag_for(gm: Decimal, thresholds: Dict[str, Any] | None) -> str:
    if gm < Decimal("0"):
        return "NEGATIVE"
    if not thresholds:
        return "UNASSESSED_NO_POLICY"
    low = thresholds.get("low_margin")
    high = thresholds.get("high_margin")
    if low is not None and gm < decimal(low, "thresholds.low_margin"):
        return "BELOW_USER_THRESHOLD"
    if high is not None and gm >= decimal(high, "thresholds.high_margin"):
        return "ABOVE_USER_THRESHOLD"
    return "WITHIN_USER_THRESHOLDS"


def calc_lines(
    payload: Dict[str, Any], thresholds: Dict[str, Any] | None = None
) -> Dict[str, Any]:
    calculation = calculation_metadata(payload)
    lines = payload.get("lines")
    if not isinstance(lines, list):
        return {"status": "error", "error_code": "lines_must_be_list"}
    if not lines:
        return {"status": "error", "error_code": "empty_lines", "lines": []}
    for ln in lines:
        if ln.get("revenue") is None or ln.get("direct_cost") is None:
            return {
                "status": "error",
                "error_code": "missing_input",
                "null_line": ln.get("line"),
            }
    out_lines = []
    for ln in lines:
        rev = decimal(ln["revenue"], "revenue")
        cost = decimal(ln["direct_cost"], "direct_cost")
        gm_abs = rev - cost
        if rev == Decimal("0"):
            gm_pct = None
            flag = "UNDEFINED_ZERO_REVENUE"
        else:
            gm_pct = gm_abs / rev
            flag = flag_for(gm_pct, thresholds)
        units = ln.get("units")
        per_unit = None
        if units is not None and decimal(units, "units") != Decimal("0"):
            per_unit = gm_abs / decimal(units, "units")
        out_lines.append(
            {
                "line": ln.get("line"),
                "revenue": text(rev),
                "direct_cost": text(cost),
                "contribution": text(gm_abs),
                "gross_margin_pct": None if gm_pct is None else text(gm_pct),
                "margin_per_unit": None if per_unit is None else text(per_unit),
                "flag": flag,
            }
        )
    out_lines.sort(key=lambda x: (x["gross_margin_pct"] is None, Decimal(x["gross_margin_pct"] or "0")))
    return {
        "status": "ok",
        "lines": out_lines,
        "line_count": len(out_lines),
        "threshold_source": "user_policy" if thresholds else None,
        "calculation": calculation,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Gross margin calculator")
    p.add_argument(
        "--input-json",
        type=str,
        required=True,
        help='JSON object with metadata and lines',
    )
    p.add_argument(
        "--thresholds-json",
        type=str,
        default="",
        help='Optional user policy: {"low_margin": 0.1, "high_margin": 0.4}',
    )
    args = p.parse_args()
    try:
        payload = json.loads(args.input_json)
        thresholds = json.loads(args.thresholds_json) if args.thresholds_json else None
        out = calc_lines(payload, thresholds)
    except (json.JSONDecodeError, ValueError) as e:
        json.dump(
            {"status": "error", "error_code": "invalid_input", "detail": str(e)},
            sys.stdout,
            ensure_ascii=False,
            indent=2,
        )
        sys.stdout.write("\n")
        return 2
    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0 if out.get("status") == "ok" else 2


if __name__ == "__main__":
    sys.exit(main())
