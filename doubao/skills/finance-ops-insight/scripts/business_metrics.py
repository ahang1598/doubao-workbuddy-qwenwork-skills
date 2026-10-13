#!/usr/bin/env python3
"""Currency-agnostic operating finance metrics with explicit assumptions."""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from typing import Any


def d(value: Any, field: str) -> Decimal:
    if value is None:
        raise ValueError(f"{field} is required")
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if not result.is_finite():
        raise ValueError(f"{field} must be finite")
    return result


def number(value: Decimal) -> str:
    return format(value, "f")


def calculation_metadata(payload: dict[str, Any], formula: str) -> dict[str, str]:
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        raise ValueError("metadata is required")
    unit = metadata.get("unit")
    period = metadata.get("period")
    tolerance_value = metadata.get("tolerance")
    if not unit or not period or tolerance_value is None:
        raise ValueError("metadata.unit, metadata.period and metadata.tolerance are required")
    tolerance = d(tolerance_value, "metadata.tolerance")
    if tolerance < 0:
        raise ValueError("metadata.tolerance must be non-negative")
    return {
        "unit": str(unit),
        "period": str(period),
        "formula": formula,
        "tolerance": number(tolerance),
        "numeric_serialization": "decimal_string",
    }


def break_even(payload: dict[str, Any]) -> dict[str, Any]:
    calculation = calculation_metadata(
        payload, "break_even_units = fixed_cost / (unit_price - unit_variable_cost)"
    )
    fixed = d(payload.get("fixed_cost"), "fixed_cost")
    price = d(payload.get("unit_price"), "unit_price")
    variable = d(payload.get("unit_variable_cost"), "unit_variable_cost")
    contribution = price - variable
    if contribution <= 0:
        return {
            "status": "not_computable",
            "reason": "unit contribution must be positive",
            "unit_contribution": number(contribution),
        }
    units = fixed / contribution
    return {
        "status": "ok",
        "formula": "fixed_cost / (unit_price - unit_variable_cost)",
        "unit_contribution": number(contribution),
        "break_even_units": number(units),
        "break_even_revenue": number(units * price),
        "assumptions": payload.get("assumptions") or [],
        "calculation": calculation,
    }


def client_profitability(payload: dict[str, Any]) -> dict[str, Any]:
    calculation = calculation_metadata(
        payload, "profit = revenue - direct_cost - allocated_cost; margin = profit / revenue"
    )
    rows = payload.get("clients")
    if not isinstance(rows, list) or not rows:
        raise ValueError("clients must be a non-empty list")
    output = []
    unknowns = []
    for index, row in enumerate(rows):
        revenue = d(row.get("revenue"), f"clients[{index}].revenue")
        direct = d(row.get("direct_cost"), f"clients[{index}].direct_cost")
        allocated_value = row.get("allocated_cost")
        allocated = (
            None
            if allocated_value is None or allocated_value == "unknown"
            else d(allocated_value, f"clients[{index}].allocated_cost")
        )
        profit = None if allocated is None else revenue - direct - allocated
        if allocated is None:
            unknowns.append(
                {
                    "client_id": row.get("client_id", str(index)),
                    "missing": "allocated_cost",
                    "blocked_slots": ["profit", "profit_margin"],
                }
            )
        output.append(
            {
                "client_id": row.get("client_id", str(index)),
                "revenue": number(revenue),
                "direct_cost": number(direct),
                "allocated_cost": None if allocated is None else number(allocated),
                "profit": None if profit is None else number(profit),
                "profit_margin": (
                    None if profit is None or revenue == 0 else number(profit / revenue)
                ),
            }
        )
    return {
        "status": "degraded" if unknowns else "ok",
        "allocation_driver": payload.get("allocation_driver"),
        "allocation_status": (
            "user_supplied" if payload.get("allocation_driver") else "not_allocated_or_unknown"
        ),
        "clients": output,
        "unknowns": unknowns,
        "calculation": calculation,
    }


def concentration(payload: dict[str, Any]) -> dict[str, Any]:
    calculation = calculation_metadata(
        payload, "share_i = revenue_i / total_revenue; HHI = sum(share_i ^ 2)"
    )
    rows = payload.get("customers")
    if not isinstance(rows, list) or not rows:
        raise ValueError("customers must be a non-empty list")
    amounts = [(row.get("customer_id"), d(row.get("revenue"), "customer revenue")) for row in rows]
    total = sum((amount for _, amount in amounts), Decimal(0))
    if total <= 0:
        raise ValueError("total customer revenue must be positive")
    shares_decimal = sorted(
        ((customer_id, amount, amount / total) for customer_id, amount in amounts),
        key=lambda row: row[2],
        reverse=True,
    )
    shares = [
        {
            "customer_id": customer_id,
            "revenue": number(amount),
            "share": number(share),
        }
        for customer_id, amount, share in shares_decimal
    ]
    top_n_value = payload.get("top_n")
    top_n = int(top_n_value) if top_n_value is not None else None
    if top_n is not None and top_n <= 0:
        raise ValueError("top_n must be a positive integer")
    return {
        "status": "ok",
        "total_revenue": number(total),
        "shares": shares,
        "top_n": top_n,
        "top_n_share": (
            None
            if top_n is None
            else number(sum((row[2] for row in shares_decimal[:top_n]), Decimal("0")))
        ),
        "hhi": number(sum((row[2] ** 2 for row in shares_decimal), Decimal("0"))),
        "risk_threshold": payload.get("risk_threshold"),
        "risk_status": "unassessed" if payload.get("risk_threshold") is None else "user_policy_applied",
        "unknowns": (
            [{"missing": "top_n", "blocked_slots": ["top_n_share"]}]
            if top_n is None
            else []
        ),
        "calculation": calculation,
    }


def seasonal(payload: dict[str, Any]) -> dict[str, Any]:
    calculation = calculation_metadata(
        payload, "seasonal_index_month = average(month values) / average(all values)"
    )
    rows = payload.get("periods")
    if not isinstance(rows, list) or not rows:
        raise ValueError("periods must be a non-empty list")
    grouped: dict[int, list[Decimal]] = defaultdict(list)
    years = set()
    for row in rows:
        month = int(row.get("month"))
        year = int(row.get("year"))
        if month < 1 or month > 12:
            raise ValueError("month must be between 1 and 12")
        grouped[month].append(d(row.get("value"), "period value"))
        years.add(year)
    overall = sum((value for values in grouped.values() for value in values), Decimal(0))
    count = sum(len(values) for values in grouped.values())
    average = overall / count if count else Decimal(0)
    indices = {
        str(month): (
            None
            if average == 0
            else number(sum(values, Decimal(0)) / Decimal(len(values)) / average)
        )
        for month, values in sorted(grouped.items())
    }
    return {
        "status": "ok",
        "years_observed": len(years),
        "evidence_state": "supported_for_seasonality" if len(years) >= 2 else "observational_only",
        "seasonal_indices": indices,
        "calculation": calculation,
    }


def recurring_costs(payload: dict[str, Any]) -> dict[str, Any]:
    calculation = calculation_metadata(
        payload, "annualized_cost = amount * periods_per_year"
    )
    rows = payload.get("costs")
    if not isinstance(rows, list):
        raise ValueError("costs must be a list")
    output = []
    for index, row in enumerate(rows):
        amount = d(row.get("amount"), f"costs[{index}].amount")
        periods = d(row.get("periods_per_year"), f"costs[{index}].periods_per_year")
        output.append(
            {
                "cost_id": row.get("cost_id", str(index)),
                "annualized_cost": number(amount * periods),
                "usage_status": row.get("usage_status", "unknown"),
                "action": "review",
            }
        )
    return {
        "status": "ok",
        "costs": output,
        "no_auto_cancel": True,
        "calculation": calculation,
    }


def pricing_sensitivity(payload: dict[str, Any]) -> dict[str, Any]:
    calculation = calculation_metadata(
        payload, "contribution = (unit_price - unit_variable_cost) * volume"
    )
    scenarios = payload.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError("scenarios must be a non-empty list")
    rows = []
    for index, scenario in enumerate(scenarios):
        price = d(scenario.get("unit_price"), f"scenarios[{index}].unit_price")
        volume = d(scenario.get("volume"), f"scenarios[{index}].volume")
        variable = d(
            scenario.get("unit_variable_cost"),
            f"scenarios[{index}].unit_variable_cost",
        )
        rows.append(
            {
                "scenario_id": scenario.get("scenario_id", str(index)),
                "revenue": number(price * volume),
                "contribution": number((price - variable) * volume),
                "formula": "(unit_price - unit_variable_cost) * volume",
            }
        )
    return {
        "status": "ok",
        "scenarios": rows,
        "elasticity_source": payload.get("elasticity_source"),
        "no_volume_response_inferred": True,
        "calculation": calculation,
    }


def period_digest(payload: dict[str, Any]) -> dict[str, Any]:
    calculation = calculation_metadata(
        payload, "surplus_or_profit = revenue - cost; change = last_period - first_period"
    )
    periods = payload.get("periods")
    basis = payload.get("basis")
    if not isinstance(periods, list) or not periods:
        raise ValueError("periods must be a non-empty list")
    if basis not in {"cash", "accrual", "management"}:
        raise ValueError("basis must be cash, accrual, or management")
    rows = []
    for index, period in enumerate(periods):
        revenue = d(period.get("revenue"), f"periods[{index}].revenue")
        cost = d(period.get("cost"), f"periods[{index}].cost")
        rows.append(
            {
                "period": period.get("period", str(index)),
                "revenue": number(revenue),
                "cost": number(cost),
                "surplus_or_profit": number(revenue - cost),
            }
        )
    return {
        "status": "ok",
        "basis": basis,
        "period_count": len(rows),
        "periods": rows,
        "first_to_last_change": {
            "revenue": number(
                Decimal(str(rows[-1]["revenue"])) - Decimal(str(rows[0]["revenue"]))
            ),
            "surplus_or_profit": number(
                Decimal(str(rows[-1]["surplus_or_profit"]))
                - Decimal(str(rows[0]["surplus_or_profit"]))
            ),
        },
        "statutory_report": False,
        "calculation": calculation,
    }


OPERATIONS = {
    "break_even": break_even,
    "client_profitability": client_profitability,
    "concentration": concentration,
    "seasonal": seasonal,
    "recurring_costs": recurring_costs,
    "pricing_sensitivity": pricing_sensitivity,
    "period_digest": period_digest,
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--operation", required=True, choices=sorted(OPERATIONS))
    parser.add_argument("--input-json", required=True)
    args = parser.parse_args()
    try:
        output = OPERATIONS[args.operation](json.loads(args.input_json))
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        output = {"status": "error", "error": str(exc)}
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if output.get("status") != "error" else 2


if __name__ == "__main__":
    sys.exit(main())
