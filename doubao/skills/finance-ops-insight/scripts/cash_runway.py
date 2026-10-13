#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rolling weekly cash projection and payroll feasibility."""
from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional


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


def project(
    opening_balance: Optional[Any],
    weeks: List[Dict[str, Any]],
    payroll_events: List[Dict[str, Any]],
    fixed_cost_weekly_cushion: Optional[Any],
    cushion_weeks: Optional[Any],
    minimum_cash_cushion: Optional[Any],
    metadata: Dict[str, Any],
) -> Dict[str, Any]:
    if opening_balance is None:
        return {"status": "error", "error_code": "missing_opening_balance"}
    if not weeks:
        return {"status": "error", "error_code": "empty_weeks"}
    unit = metadata.get("unit") if isinstance(metadata, dict) else None
    period = metadata.get("period") if isinstance(metadata, dict) else None
    tolerance_value = metadata.get("tolerance") if isinstance(metadata, dict) else None
    if not unit or not period or tolerance_value is None:
        return {
            "status": "error",
            "error_code": "missing_calculation_metadata",
            "required": ["metadata.unit", "metadata.period", "metadata.tolerance"],
        }
    try:
        tolerance = decimal(tolerance_value, "metadata.tolerance")
        opening = decimal(opening_balance, "opening_balance")
    except ValueError as exc:
        return {"status": "error", "error_code": "invalid_decimal", "detail": str(exc)}
    if tolerance < 0:
        return {"status": "error", "error_code": "negative_tolerance"}

    if minimum_cash_cushion is not None:
        cushion = decimal(minimum_cash_cushion, "minimum_cash_cushion")
        cushion_formula = "user supplied minimum_cash_cushion"
    elif fixed_cost_weekly_cushion is not None and cushion_weeks is not None:
        cushion = decimal(
            fixed_cost_weekly_cushion, "fixed_cost_weekly"
        ) * decimal(cushion_weeks, "cushion_weeks")
        cushion_formula = "fixed_cost_weekly * user supplied cushion_weeks"
    else:
        return {
            "status": "error",
            "error_code": "missing_user_cushion_policy",
            "required_any": [
                "minimum_cash_cushion",
                "fixed_cost_weekly + cushion_weeks",
            ],
        }
    bal = opening
    rows = []
    unconfirmed = Decimal("0")
    total_in = Decimal("0")
    for w in weeks:
        if w.get("inflows") is None or w.get("outflows") is None:
            return {
                "status": "error",
                "error_code": "missing_input",
                "week": w.get("week"),
            }
        inflow = decimal(w["inflows"], f"{w.get('week')}.inflows")
        outflow = decimal(w["outflows"], f"{w.get('week')}.outflows")
        conf = (
            decimal(w["confirmed_inflows"], f"{w.get('week')}.confirmed_inflows")
            if w.get("confirmed_inflows") is not None
            else None
        )
        start = bal
        end = start + inflow - outflow
        total_in += inflow
        if conf is not None:
            unconfirmed += max(Decimal("0"), inflow - conf)
        else:
            unconfirmed += inflow  # treat all as unconfirmed if not tagged
        rows.append(
            {
                "week": w.get("week"),
                "start_balance": text(start),
                "inflows": text(inflow),
                "outflows": text(outflow),
                "end_balance": text(end),
                "below_cushion": end < cushion - tolerance,
                "min_cushion": text(cushion),
            }
        )
        bal = end

    pay_out = []
    for pe in payroll_events:
        if pe.get("pay_date") is None or pe.get("amount") is None or pe.get("week_index") is None:
            return {"status": "error", "error_code": "bad_payroll_event", "event": pe}
        wi = int(pe["week_index"])
        if wi < 0 or wi >= len(rows):
            return {"status": "error", "error_code": "payroll_week_oob", "week_index": wi}
        amount = decimal(pe["amount"], "payroll.amount")
        # status based on that week end balance after all flows already netted in row;
        # interpret payroll as included in outflows; feasibility uses end_balance.
        end_b = Decimal(rows[wi]["end_balance"])
        # Payroll is already included in weekly outflows. Apply only the
        # user-supplied tolerance to the post-payroll balance and cushion.
        if end_b < -tolerance:
            status = "SHORTFALL"
        elif end_b < cushion - tolerance:
            status = "TIGHT"
        else:
            status = "CLEARED"
        pay_out.append(
            {
                "pay_date": pe["pay_date"],
                "payroll_amount": text(amount),
                "week_index": wi,
                "end_balance_after": text(end_b),
                "status": status,
            }
        )

    tagged_weeks = sum(w.get("confirmed_inflows") is not None for w in weeks)
    confirmed_coverage = Decimal(tagged_weeks) / Decimal(len(weeks))
    unconf_pct = (unconfirmed / total_in) if total_in > Decimal("0") else None

    return {
        "status": "ok",
        "opening_balance": text(opening),
        "min_cushion": text(cushion),
        "cushion_formula": cushion_formula,
        "calculation": {
            "unit": str(unit),
            "period": str(period),
            "formula": "end_balance = start_balance + inflows - outflows",
            "tolerance": text(tolerance),
            "numeric_serialization": "decimal_string",
        },
        "weeks": rows,
        "payroll": pay_out,
        "closing_balance": rows[-1]["end_balance"] if rows else None,
        "confidence": "unknown",
        "confidence_reason": "no user confidence policy supplied or inferred",
        "coverage": {
            "weeks_total": len(weeks),
            "weeks_with_confirmation_tag": tagged_weeks,
            "confirmation_tag_coverage": text(confirmed_coverage),
            "unconfirmed_inflow_pct": None if unconf_pct is None else text(unconf_pct),
        },
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Cash runway weekly projector")
    p.add_argument("--input-json", type=str, required=True, help="Full payload JSON")
    args = p.parse_args()
    try:
        payload = json.loads(args.input_json)
        out = project(
            payload.get("opening_balance"),
            payload.get("weeks") or [],
            payload.get("payroll_events") or [],
            payload.get("fixed_cost_weekly"),
            payload.get("cushion_weeks"),
            payload.get("minimum_cash_cushion"),
            payload.get("metadata") or {},
        )
    except (json.JSONDecodeError, ValueError) as e:
        json.dump(
            {"status": "error", "error_code": "invalid_json", "detail": str(e)},
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
