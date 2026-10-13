#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministic price-volume variance decomposition."""
from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Optional


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


def decomp(
    budget_volume: Optional[Any],
    budget_price: Optional[Any],
    actual_volume: Optional[Any],
    actual_price: Optional[Any],
    *,
    unit: str,
    period: str,
    tolerance: Optional[Any],
) -> Dict[str, Any]:
    keys = {
        "budget_volume": budget_volume,
        "budget_price": budget_price,
        "actual_volume": actual_volume,
        "actual_price": actual_price,
    }
    if any(v is None for v in keys.values()):
        return {
            "status": "error",
            "error_code": "missing_input",
            "null_fields": [k for k, v in keys.items() if v is None],
        }
    try:
        bq, bp, aq, ap = (
            decimal(budget_volume, "budget_volume"),
            decimal(budget_price, "budget_price"),
            decimal(actual_volume, "actual_volume"),
            decimal(actual_price, "actual_price"),
        )
        tolerance_decimal = (
            None if tolerance is None else decimal(tolerance, "tolerance")
        )
    except ValueError as exc:
        return {"status": "error", "error_code": "invalid_decimal", "detail": str(exc)}
    if tolerance_decimal is not None and tolerance_decimal < 0:
        return {"status": "error", "error_code": "negative_tolerance"}
    budget_amount = bq * bp
    actual_amount = aq * ap
    total_var = actual_amount - budget_amount
    volume_effect = (aq - bq) * bp
    price_effect = (ap - bp) * aq
    checksum = volume_effect + price_effect
    recon_difference = checksum - total_var
    ok = (
        None
        if tolerance_decimal is None
        else abs(recon_difference) <= tolerance_decimal
    )
    return {
        "status": "degraded" if ok is None else "ok" if ok else "error",
        "artifact_state": "degraded" if ok is None else "ready" if ok else "stopped",
        "error_code": (
            "missing_tolerance" if ok is None else None if ok else "recon_failed"
        ),
        "budget_amount": text(budget_amount),
        "actual_amount": text(actual_amount),
        "total_variance": text(total_var),
        "volume_effect": text(volume_effect),
        "price_effect": text(price_effect),
        "recon_sum_effects": text(checksum),
        "recon_difference": text(recon_difference),
        "recon_ok": ok,
        "favorable": total_var > Decimal("0"),
        "calculation": {
            "unit": unit,
            "period": period,
            "formula": {
                "budget_amount": "budget_volume * budget_price",
                "actual_amount": "actual_volume * actual_price",
                "total_variance": "actual_amount - budget_amount",
                "volume_effect": "(actual_volume - budget_volume) * budget_price",
                "price_effect": "(actual_price - budget_price) * actual_volume",
                "reconciliation": "abs(volume_effect + price_effect - total_variance) <= tolerance",
            },
            "tolerance": (
                None if tolerance_decimal is None else text(tolerance_decimal)
            ),
            "numeric_serialization": "decimal_string",
        },
        "unknowns": (
            [
                {
                    "missing": "tolerance",
                    "blocked_slots": ["recon_ok", "strong_variance_conclusion"],
                }
            ]
            if tolerance_decimal is None
            else []
        ),
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Price-volume variance decomposition")
    p.add_argument("--budget-volume", required=True)
    p.add_argument("--budget-price", required=True)
    p.add_argument("--actual-volume", required=True)
    p.add_argument("--actual-price", required=True)
    p.add_argument("--unit", required=True)
    p.add_argument("--period", required=True)
    p.add_argument("--tolerance")
    args = p.parse_args()
    out = decomp(
        args.budget_volume,
        args.budget_price,
        args.actual_volume,
        args.actual_price,
        unit=args.unit,
        period=args.period,
        tolerance=args.tolerance,
    )
    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0 if out.get("status") in {"ok", "degraded"} else 2


if __name__ == "__main__":
    sys.exit(main())
