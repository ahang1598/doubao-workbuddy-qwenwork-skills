#!/usr/bin/env python3
"""Deterministic calculations and artifact checks for derivatives research."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation, getcontext
import hashlib
import io
import json
import os
from pathlib import Path
import stat
from typing import Any


VERSION = "derivatives-engine-v6"
INPUT_VERSION = "derivatives-engine-input-v6"
CSV_FORMULA_PREFIXES = ("=", "+", "-", "@")
CSV_NUMERIC_FIELDS = {
    "basis.csv": {
        "cash_full_price_per_100", "funding_cost_per_100",
        "theoretical_futures_price_per_100", "market_minus_theoretical_per_100",
        "net_basis_per_100", "full_basis_per_100", "net_carry_per_100", "bnoc_per_100",
        "irr_decimal", "irr_minus_financing_decimal", "basis_convergence_pnl",
        "signed_net_carry_pnl", "total_convergence_pnl", "bnoc_pnl_equivalent",
    },
    "account.csv": {
        "starting_equity", "eligible_adjustments", "existing_margin", "proposed_margin",
        "verified_margin_offset", "cash_restrictions", "bridge_equity", "total_margin",
        "calculated_available_cash", "reported_available_cash",
        "reconciliation_difference_calculated_minus_reported", "cash_floor", "margin_cap",
    },
    "short_options.csv": {
        "contracts", "multiplier", "units", "close_cost", "premium_received_total",
        "mark_to_close_pnl", "assignment_notional", "underlying_price_floor",
    },
    "scenarios.csv": {
        "pnl_component_count", "pnl_total", "cash_adjustments_total",
        "bridge_equity_after_scenario", "existing_margin", "proposed_margin",
        "verified_margin_offset", "total_margin", "available_cash_after_stress",
    },
}
CSV_REQUIRED_FIELDS = {
    "basis.csv": (
        "basis_convergence_pnl", "bnoc_is_diagnostic_not_additional_pnl", "bnoc_per_100",
        "bnoc_pnl_equivalent", "cash_full_price_per_100", "direction",
        "direction_consistent", "expected_basis_direction", "full_basis_per_100",
        "funding_cost_per_100", "futures_valuation", "id", "irr_decimal",
        "irr_minus_financing_decimal", "market_minus_theoretical_per_100",
        "net_basis_per_100", "net_carry_per_100", "signed_net_carry_pnl",
        "source_fields", "theoretical_futures_price_per_100", "total_convergence_pnl",
    ),
    "account.csv": (
        "bridge_equity", "calculated_available_cash", "cash_floor", "cash_floor_ok",
        "cash_restriction_items", "cash_restrictions", "eligible_adjustments",
        "equity_adjustments", "existing_margin", "id", "margin_cap", "margin_cap_ok",
        "proposed_margin", "reconciliation_difference_calculated_minus_reported",
        "reported_available_cash", "source_fields", "starting_equity", "total_margin",
        "verified_margin_offset",
    ),
    "short_options.csv": (
        "assignment_notional", "close_cost", "close_price_source", "contracts", "id",
        "mark_to_close_pnl", "maximum_loss_after_premium", "maximum_loss_before_premium",
        "multiplier", "option_type", "premium_received_total", "side",
        "source_fields", "underlying_price_floor", "units",
    ),
    "scenarios.csv": (
        "all_known_constraints_passed", "available_cash_after_stress",
        "bridge_equity_after_scenario", "cash_adjustments", "cash_adjustments_total",
        "cash_floor_ok", "component_sum_matches_total", "existing_margin", "id",
        "margin_cap_ok", "pnl_component_count", "pnl_components", "pnl_total",
        "proposed_margin", "scenario_as_of", "scenario_definition_id", "scenario_marks",
        "scenario_plan_id", "source_fields", "total_margin", "verified_margin_offset",
    ),
}
SUMMARY_REQUIRED_FIELDS = {
    "version", "basis_trades", "account", "short_options", "instruments",
    "scenario_definitions", "scenario_plans", "scenarios", "field_sources", "checks",
}
NUMERIC_INPUT_FIELDS = {
    "accrued_interest_per_100", "amount", "base_mark", "carry_income_per_100",
    "cash_clean_price_per_100", "cash_floor", "close_ask_per_unit", "close_fees",
    "contracts", "conversion_factor", "day_basis", "days_to_delivery", "face_value",
    "financing_rate_decimal", "futures_price_per_100", "margin_cap", "multiplier",
    "premium_received_total", "proposed_margin", "reported_available_cash",
    "scenario_price", "signed_contracts", "signed_quantity", "starting_equity", "strike",
    "underlying_price_floor", "verified_margin_offset", "existing_margin",
}
TOP_LEVEL_FIELDS = {
    "version", "basis_trades", "account", "short_options", "instruments",
    "scenario_definitions", "scenario_plans", "scenarios", "field_sources",
}
BASIS_FIELDS = {
    "id", "direction", "cash_clean_price_per_100", "accrued_interest_per_100",
    "futures_price_per_100", "conversion_factor", "financing_rate_decimal",
    "days_to_delivery", "day_basis", "carry_income_per_100", "face_value",
}
ACCOUNT_FIELDS = {
    "id", "starting_equity", "equity_adjustments", "existing_margin",
    "proposed_margin", "verified_margin_offset", "cash_restrictions",
    "reported_available_cash", "cash_floor", "margin_cap",
}
EQUITY_ADJUSTMENT_FIELDS = {"id", "amount", "already_in_starting_equity"}
CASH_RESTRICTION_FIELDS = {"id", "amount"}
SHORT_OPTION_FIELDS = {
    "id", "option_type", "side", "contracts", "multiplier", "strike",
    "close_ask_per_unit", "close_fees", "premium_received_total",
    "underlying_price_floor",
}
INSTRUMENT_FIELDS = {"id", "kind", "base_mark", "multiplier"}
SCENARIO_DEFINITION_FIELDS = {"id", "marks"}
SCENARIO_MARK_FIELDS = {"id", "scenario_price"}
SCENARIO_PLAN_FIELDS = {"id", "positions"}
SCENARIO_POSITION_FIELDS = {"id", "instrument_id", "signed_contracts", "signed_quantity"}
SCENARIO_FIELDS = {
    "id", "plan_id", "definition_id", "as_of", "pnl_components",
    "external_valued_components", "cash_adjustments", "existing_margin",
    "proposed_margin", "verified_margin_offset",
}
EXTERNAL_COMPONENT_FIELDS = {"id", "valuation_source", "amount"}
SCENARIO_CASH_FIELDS = {
    "id", "amount", "source", "confirmed", "available_at", "restriction_status",
    "already_in_bridge_equity",
}
getcontext().prec = 28


def decimal(value: Any, field: str) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise ValueError(f"{field} must be numeric")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if not result.is_finite():
        raise ValueError(f"{field} must be finite")
    return result


def nonnegative(value: Any, field: str) -> Decimal:
    result = decimal(value, field)
    if result < 0:
        raise ValueError(f"{field} must be nonnegative")
    return result


def positive(value: Any, field: str) -> Decimal:
    result = decimal(value, field)
    if result <= 0:
        raise ValueError(f"{field} must be positive")
    return result


def identifier(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a nonempty string")
    return value.strip()


def reject_unknown_fields(row: dict[str, Any], allowed: set[str], field: str) -> None:
    unknown = sorted(set(row) - allowed)
    if unknown:
        raise ValueError(f"{field} contains unknown fields: {', '.join(unknown)}")


def aware_datetime(value: Any, field: str) -> datetime:
    text = identifier(value, field)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO-8601 datetime") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must include a timezone")
    return parsed


def decimal_text(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return decimal_text(value)
    if isinstance(value, dict):
        return {key: json_value(child) for key, child in value.items()}
    if isinstance(value, list):
        return [json_value(child) for child in value]
    return value


def semantic_input_value(value: Any) -> Any:
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (Decimal, int, float)):
        return decimal_text(decimal(value, "input numeric value"))
    if isinstance(value, dict):
        return {key: semantic_input_value(child) for key, child in value.items()}
    if isinstance(value, list):
        return [semantic_input_value(child) for child in value]
    return value


def parse_json_bytes(data: bytes) -> Any:
    return json.loads(data.decode("utf-8"), parse_float=Decimal, parse_int=Decimal)


def numeric_input_paths(value: Any, path: str = "") -> set[str]:
    result: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "field_sources":
                continue
            child_path = f"{path}/{key}"
            if key in NUMERIC_INPUT_FIELDS and child is not None:
                result.add(child_path)
            result.update(numeric_input_paths(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            result.update(numeric_input_paths(child, f"{path}/{index}"))
    return result


def normalize_field_sources(payload: dict[str, Any], *, required: bool) -> dict[str, dict[str, str]]:
    raw = payload.get("field_sources")
    if raw is None and not required:
        return {}
    if not isinstance(raw, dict):
        raise ValueError("field_sources must be an object keyed by JSON-pointer field path")
    normalized: dict[str, dict[str, str]] = {}
    for path, item in raw.items():
        if not isinstance(path, str) or not path.startswith("/") or "//" in path:
            raise ValueError("field_sources keys must be absolute JSON-pointer field paths")
        if not isinstance(item, dict) or set(item) - {"source", "as_of", "unit", "currency"}:
            raise ValueError(f"field_sources[{path}] has an invalid schema")
        source = identifier(item.get("source"), f"field_sources[{path}].source")
        as_of = identifier(item.get("as_of"), f"field_sources[{path}].as_of")
        aware_datetime(as_of, f"field_sources[{path}].as_of")
        normalized[path] = {"source": source, "as_of": as_of}
        for optional in ("unit", "currency"):
            if item.get(optional) is not None:
                normalized[path][optional] = identifier(
                    item[optional], f"field_sources[{path}].{optional}"
                )
    numeric_paths = numeric_input_paths(payload)
    missing = numeric_paths - set(normalized)
    if required and missing:
        raise ValueError("missing field_sources for numeric inputs: " + ", ".join(sorted(missing)))
    extra = set(normalized) - numeric_paths
    if extra:
        raise ValueError("field_sources contains non-numeric or unknown paths: " + ", ".join(sorted(extra)))
    return dict(sorted(normalized.items()))


def source_subset(field_sources: dict[str, dict[str, str]], *prefixes: str) -> dict[str, dict[str, str]]:
    return {
        path: item for path, item in field_sources.items()
        if any(path == prefix or path.startswith(prefix + "/") for prefix in prefixes)
    }


def unique_rows(rows: Any, field: str) -> list[dict[str, Any]]:
    if rows is None:
        return []
    if not isinstance(rows, list):
        raise ValueError(f"{field} must be a list")
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"{field}[{index}] must be an object")
        key = identifier(row.get("id"), f"{field}[{index}].id")
        if key in seen:
            raise ValueError(f"duplicate {field} id: {key}")
        seen.add(key)
        result.append(row)
    return result


def sum_amounts(rows: Any, field: str) -> Decimal:
    total = Decimal("0")
    for index, row in enumerate(unique_rows(rows, field)):
        total += decimal(row.get("amount"), f"{field}[{index}].amount")
    return total


def calculate_basis_trade(row: dict[str, Any]) -> dict[str, Any]:
    reject_unknown_fields(row, BASIS_FIELDS, "basis_trades row")
    key = identifier(row.get("id"), "basis_trades.id")
    direction = row.get("direction")
    if direction not in {"buy_basis", "sell_basis"}:
        raise ValueError(f"{key}.direction must be buy_basis or sell_basis")
    sign = Decimal("1") if direction == "buy_basis" else Decimal("-1")
    clean = positive(row.get("cash_clean_price_per_100"), f"{key}.cash_clean_price_per_100")
    accrued = nonnegative(row.get("accrued_interest_per_100"), f"{key}.accrued_interest_per_100")
    futures = positive(row.get("futures_price_per_100"), f"{key}.futures_price_per_100")
    factor = positive(row.get("conversion_factor"), f"{key}.conversion_factor")
    rate = decimal(row.get("financing_rate_decimal"), f"{key}.financing_rate_decimal")
    days = positive(row.get("days_to_delivery"), f"{key}.days_to_delivery")
    day_basis = positive(row.get("day_basis"), f"{key}.day_basis")
    carry = nonnegative(row.get("carry_income_per_100"), f"{key}.carry_income_per_100")
    face = positive(row.get("face_value"), f"{key}.face_value")

    full = clean + accrued
    funding = full * rate * days / day_basis
    theoretical = (clean + funding - carry) / factor
    net_basis = clean - futures * factor
    full_basis = full - futures * factor
    net_carry = carry - funding
    bnoc = net_basis - net_carry
    convergence = -sign * net_basis
    signed_carry = sign * net_carry
    total = convergence + signed_carry
    bnoc_equivalent = -sign * bnoc
    if total != bnoc_equivalent:
        raise AssertionError("basis decomposition is internally inconsistent")

    market_gap = futures - theoretical
    if market_gap > 0:
        valuation, expected = "futures_overvalued", "buy_basis"
    elif market_gap < 0:
        valuation, expected = "futures_undervalued", "sell_basis"
    else:
        valuation, expected = "at_theoretical", "none"
    irr = (futures * factor + carry - clean) / full * day_basis / days
    scale = face / Decimal("100")
    return {
        "id": key,
        "direction": direction,
        "cash_full_price_per_100": full,
        "funding_cost_per_100": funding,
        "theoretical_futures_price_per_100": theoretical,
        "market_minus_theoretical_per_100": market_gap,
        "futures_valuation": valuation,
        "expected_basis_direction": expected,
        "direction_consistent": direction == expected if expected != "none" else None,
        "net_basis_per_100": net_basis,
        "full_basis_per_100": full_basis,
        "net_carry_per_100": net_carry,
        "bnoc_per_100": bnoc,
        "irr_decimal": irr,
        "irr_minus_financing_decimal": irr - rate,
        "basis_convergence_pnl": convergence * scale,
        "signed_net_carry_pnl": signed_carry * scale,
        "total_convergence_pnl": total * scale,
        "bnoc_pnl_equivalent": bnoc_equivalent * scale,
        "bnoc_is_diagnostic_not_additional_pnl": True,
    }


def account_inputs(row: dict[str, Any]) -> dict[str, Any]:
    reject_unknown_fields(row, ACCOUNT_FIELDS, "account")
    for required in ("equity_adjustments", "verified_margin_offset", "cash_restrictions"):
        if required not in row:
            raise ValueError(f"account.{required} is required; use an explicit empty or zero value")
    starting = decimal(row.get("starting_equity"), "account.starting_equity")
    adjustments = Decimal("0")
    adjustment_rows = []
    for index, item in enumerate(unique_rows(row.get("equity_adjustments"), "account.equity_adjustments")):
        reject_unknown_fields(
            item, EQUITY_ADJUSTMENT_FIELDS, f"account.equity_adjustments[{index}]"
        )
        included = item.get("already_in_starting_equity")
        if type(included) is not bool:
            raise ValueError(
                f"account.equity_adjustments[{index}].already_in_starting_equity must be boolean"
            )
        amount = decimal(item.get("amount"), f"account.equity_adjustments[{index}].amount")
        applied = not included
        if applied:
            adjustments += amount
        adjustment_rows.append({
            "id": identifier(item.get("id"), f"account.equity_adjustments[{index}].id"),
            "amount": amount,
            "already_in_starting_equity": included,
            "applied_to_bridge": applied,
        })
    existing = nonnegative(row.get("existing_margin"), "account.existing_margin")
    proposed = nonnegative(row.get("proposed_margin"), "account.proposed_margin")
    offset = nonnegative(row.get("verified_margin_offset"), "account.verified_margin_offset")
    if offset > existing + proposed:
        raise ValueError("verified margin offset exceeds gross margin")
    restrictions = Decimal("0")
    restriction_rows = []
    for index, item in enumerate(
        unique_rows(row.get("cash_restrictions"), "account.cash_restrictions")
    ):
        reject_unknown_fields(
            item, CASH_RESTRICTION_FIELDS, f"account.cash_restrictions[{index}]"
        )
        amount = nonnegative(
            item.get("amount"), f"account.cash_restrictions[{index}].amount"
        )
        restrictions += amount
        restriction_rows.append({
            "id": identifier(item.get("id"), f"account.cash_restrictions[{index}].id"),
            "amount": amount,
        })
    return {
        "starting_equity": starting,
        "equity_adjustments": adjustment_rows,
        "eligible_adjustments": adjustments,
        "existing_margin": existing,
        "proposed_margin": proposed,
        "verified_margin_offset": offset,
        "cash_restriction_items": restriction_rows,
        "cash_restrictions": restrictions,
    }


def calculate_account(row: dict[str, Any]) -> dict[str, Any]:
    values = account_inputs(row)
    bridge_equity = values["starting_equity"] + values["eligible_adjustments"]
    total_margin = (
        values["existing_margin"] + values["proposed_margin"] - values["verified_margin_offset"]
    )
    available = bridge_equity - total_margin - values["cash_restrictions"]
    reported = row.get("reported_available_cash")
    reported_value = decimal(reported, "account.reported_available_cash") if reported is not None else None
    cash_floor = row.get("cash_floor")
    cash_floor_value = decimal(cash_floor, "account.cash_floor") if cash_floor is not None else None
    margin_cap = row.get("margin_cap")
    margin_cap_value = decimal(margin_cap, "account.margin_cap") if margin_cap is not None else None
    return {
        "id": identifier(row.get("id", "account"), "account.id"),
        **values,
        "bridge_equity": bridge_equity,
        "total_margin": total_margin,
        "calculated_available_cash": available,
        "reported_available_cash": reported_value,
        "reconciliation_difference_calculated_minus_reported": (
            available - reported_value if reported_value is not None else None
        ),
        "cash_floor": cash_floor_value,
        "cash_floor_ok": available >= cash_floor_value if cash_floor_value is not None else None,
        "margin_cap": margin_cap_value,
        "margin_cap_ok": total_margin <= margin_cap_value if margin_cap_value is not None else None,
    }


def calculate_short_option(row: dict[str, Any]) -> dict[str, Any]:
    reject_unknown_fields(row, SHORT_OPTION_FIELDS, "short_options row")
    key = identifier(row.get("id"), "short_options.id")
    option_type = row.get("option_type")
    if option_type not in {"put", "call"}:
        raise ValueError(f"{key}.option_type must be put or call")
    if row.get("side") != "short":
        raise ValueError(f"{key}.side must be short")
    contracts = positive(row.get("contracts"), f"{key}.contracts")
    if contracts != contracts.to_integral_value():
        raise ValueError(f"{key}.contracts must be an integer")
    multiplier = positive(row.get("multiplier"), f"{key}.multiplier")
    strike = positive(row.get("strike"), f"{key}.strike")
    close_ask = nonnegative(row.get("close_ask_per_unit"), f"{key}.close_ask_per_unit")
    if "close_fees" not in row:
        raise ValueError(f"{key}.close_fees is required for an exact close cost")
    fees = nonnegative(row.get("close_fees"), f"{key}.close_fees")
    premium = row.get("premium_received_total")
    premium_value = (
        nonnegative(premium, f"{key}.premium_received_total") if premium is not None else None
    )
    floor = row.get("underlying_price_floor")
    floor_value = decimal(floor, f"{key}.underlying_price_floor") if floor is not None else None
    units = contracts * multiplier
    close_cost = close_ask * units + fees
    assignment_notional = strike * units
    put_loss_before_premium = (
        max(Decimal("0"), (strike - floor_value) * units)
        if option_type == "put" and floor_value is not None
        else None
    )
    put_loss_after_premium = (
        max(Decimal("0"), put_loss_before_premium - premium_value)
        if put_loss_before_premium is not None and premium_value is not None
        else None
    )
    return {
        "id": key,
        "option_type": option_type,
        "side": "short",
        "contracts": contracts,
        "multiplier": multiplier,
        "units": units,
        "close_price_source": "ask",
        "close_cost": close_cost,
        "premium_received_total": premium_value,
        "mark_to_close_pnl": premium_value - close_cost if premium_value is not None else None,
        "assignment_notional": assignment_notional,
        "underlying_price_floor": floor_value,
        "maximum_loss_before_premium": (
            put_loss_before_premium
            if option_type == "put" and put_loss_before_premium is not None
            else "unknown_without_underlying_price_floor" if option_type == "put" else "unbounded"
        ),
        "maximum_loss_after_premium": (
            put_loss_after_premium
            if option_type == "put" and put_loss_after_premium is not None
            else "unknown_without_underlying_price_floor"
            if option_type == "put" and floor_value is None
            else "unknown_without_entry_premium" if option_type == "put" else "unbounded"
        ),
    }


def load_instruments(rows: Any) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    normalized: list[dict[str, Any]] = []
    lookup: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(unique_rows(rows, "instruments")):
        reject_unknown_fields(row, INSTRUMENT_FIELDS, f"instruments[{index}]")
        key = identifier(row.get("id"), f"instruments[{index}].id")
        kind = row.get("kind")
        if kind not in {"futures", "cash", "spot"}:
            raise ValueError(f"instruments[{index}].kind must be futures, cash or spot")
        base_mark = decimal(row.get("base_mark"), f"instruments[{index}].base_mark")
        if kind == "futures":
            multiplier = positive(row.get("multiplier"), f"instruments[{index}].multiplier")
        else:
            supplied = row.get("multiplier")
            if supplied is not None and decimal(supplied, f"instruments[{index}].multiplier") != 1:
                raise ValueError(f"instruments[{index}].multiplier must be omitted or one")
            multiplier = Decimal("1")
        value = {
            "id": key,
            "kind": kind,
            "base_mark": base_mark,
            "multiplier": multiplier,
        }
        normalized.append(value)
        lookup[key] = value
    return normalized, lookup


def load_scenario_definitions(
    rows: Any, instruments: dict[str, dict[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Decimal]]]:
    normalized: list[dict[str, Any]] = []
    lookup: dict[str, dict[str, Decimal]] = {}
    for index, row in enumerate(unique_rows(rows, "scenario_definitions")):
        reject_unknown_fields(
            row, SCENARIO_DEFINITION_FIELDS, f"scenario_definitions[{index}]"
        )
        key = identifier(row.get("id"), f"scenario_definitions[{index}].id")
        marks: list[dict[str, Any]] = []
        prices: dict[str, Decimal] = {}
        for mark_index, mark in enumerate(
            unique_rows(row.get("marks"), f"scenario_definitions[{index}].marks")
        ):
            reject_unknown_fields(
                mark,
                SCENARIO_MARK_FIELDS,
                f"scenario_definitions[{index}].marks[{mark_index}]",
            )
            instrument = identifier(
                mark.get("id"),
                f"scenario_definitions[{index}].marks[{mark_index}].id",
            )
            price = decimal(
                mark.get("scenario_price"),
                f"scenario_definitions[{index}].marks[{mark_index}].scenario_price",
            )
            prices[instrument] = price
            marks.append({"id": instrument, "scenario_price": price})
        if not marks:
            raise ValueError(f"scenario definition {key} requires at least one mark")
        if set(prices) != set(instruments):
            raise ValueError(
                f"scenario definition {key} must provide one mark for every frozen instrument"
            )
        lookup[key] = prices
        normalized.append({"id": key, "marks": marks})
    return normalized, lookup


def load_scenario_plans(
    rows: Any, instruments: dict[str, dict[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    normalized: list[dict[str, Any]] = []
    lookup: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(unique_rows(rows, "scenario_plans")):
        reject_unknown_fields(row, SCENARIO_PLAN_FIELDS, f"scenario_plans[{index}]")
        key = identifier(row.get("id"), f"scenario_plans[{index}].id")
        positions = []
        for position_index, position in enumerate(
            unique_rows(row.get("positions"), f"scenario_plans[{index}].positions")
        ):
            field = f"scenario_plans[{index}].positions[{position_index}]"
            reject_unknown_fields(position, SCENARIO_POSITION_FIELDS, field)
            if any(name in position for name in ("kind", "base_mark", "multiplier")):
                raise ValueError(
                    f"{field} must reference frozen instrument terms instead of overriding them"
                )
            position_id = identifier(position.get("id"), f"{field}.id")
            instrument_id = identifier(position.get("instrument_id"), f"{field}.instrument_id")
            if instrument_id not in instruments:
                raise ValueError(f"{field}.instrument_id is not a frozen instrument")
            instrument = instruments[instrument_id]
            if instrument["kind"] == "futures":
                quantity = decimal(position.get("signed_contracts"), f"{field}.signed_contracts")
                if quantity != quantity.to_integral_value():
                    raise ValueError(f"{field}.signed_contracts must be an integer")
                quantity_field = "signed_contracts"
            else:
                quantity = decimal(position.get("signed_quantity"), f"{field}.signed_quantity")
                quantity_field = "signed_quantity"
            positions.append({
                "id": position_id,
                "instrument_id": instrument_id,
                quantity_field: quantity,
            })
        if not positions:
            raise ValueError(f"scenario plan {key} requires at least one position")
        value = {"id": key, "positions": positions}
        normalized.append(value)
        lookup[key] = value
    return normalized, lookup


def scenario_position(
    row: dict[str, Any], instrument: dict[str, Any], marks: dict[str, Decimal], field: str
) -> dict[str, Any]:
    key = row["id"]
    instrument_id = row["instrument_id"]
    kind = instrument["kind"]
    base_mark = instrument["base_mark"]
    multiplier = instrument["multiplier"]
    scenario_price = marks[instrument_id]
    price_change = scenario_price - base_mark
    if kind == "futures":
        signed_quantity = row["signed_contracts"]
        pnl = signed_quantity * multiplier * price_change
        method = "signed_contracts * multiplier * (scenario_price - base_mark)"
        quantity_field = "signed_contracts"
    else:
        signed_quantity = row["signed_quantity"]
        pnl = signed_quantity * price_change
        method = "signed_quantity * (scenario_price - base_mark)"
        quantity_field = "signed_quantity"
    return {
        "id": key,
        "component_type": kind,
        "instrument_id": instrument_id,
        quantity_field: signed_quantity,
        "multiplier": multiplier,
        "base_mark": base_mark,
        "scenario_price": scenario_price,
        "price_change": price_change,
        "pnl": pnl,
        "calculation_method": method,
        "engine_calculated": True,
    }


def external_scenario_component(row: dict[str, Any], field: str) -> dict[str, Any]:
    reject_unknown_fields(row, EXTERNAL_COMPONENT_FIELDS, field)
    key = identifier(row.get("id"), f"{field}.id")
    source = identifier(row.get("valuation_source"), f"{field}.valuation_source")
    amount = decimal(row.get("amount"), f"{field}.amount")
    return {
        "id": key,
        "component_type": "external_valuation",
        "valuation_source": source,
        "pnl": amount,
        "calculation_method": "caller_provided_external_valuation",
        "engine_calculated": False,
    }


def calculate_scenario(
    row: dict[str, Any],
    account: dict[str, Any],
    definitions: dict[str, dict[str, Decimal]],
    plans: dict[str, dict[str, Any]],
    instruments: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    reject_unknown_fields(row, SCENARIO_FIELDS, "scenarios row")
    key = identifier(row.get("id"), "scenarios.id")
    if "cash_adjustments" not in row:
        raise ValueError(f"scenario.{key}.cash_adjustments is required; use an explicit empty list")
    definition_id = identifier(row.get("definition_id"), f"scenario.{key}.definition_id")
    if definition_id not in definitions:
        raise ValueError(f"scenario {key} references an unknown scenario definition")
    plan_id = identifier(row.get("plan_id"), f"scenario.{key}.plan_id")
    if plan_id not in plans:
        raise ValueError(f"scenario {key} references an unknown scenario plan")
    marks = definitions[definition_id]
    positions = [
        scenario_position(
            item,
            instruments[item["instrument_id"]],
            marks,
            f"scenario.{key}.positions[{index}]",
        )
        for index, item in enumerate(plans[plan_id]["positions"])
    ]
    if row.get("pnl_components") is not None and row.get("external_valued_components") is not None:
        raise ValueError(
            f"scenario {key} cannot provide both pnl_components and external_valued_components"
        )
    external_rows = (
        row.get("external_valued_components")
        if row.get("external_valued_components") is not None
        else row.get("pnl_components")
    )
    external = [
        external_scenario_component(
            item, f"scenario.{key}.external_valued_components[{index}]"
        )
        for index, item in enumerate(
            unique_rows(external_rows, f"scenario.{key}.external_valued_components")
        )
    ]
    components = [*positions, *external]
    if not components:
        raise ValueError(f"scenario {key} requires at least one PnL component")
    pnl = sum((item["pnl"] for item in components), Decimal("0"))
    raw_cash_rows = unique_rows(
        row.get("cash_adjustments"), f"scenario.{key}.cash_adjustments"
    )
    scenario_as_of_text = row.get("as_of")
    scenario_as_of = aware_datetime(scenario_as_of_text, f"scenario.{key}.as_of")
    account_bridge_ids = {
        item["id"]
        for item in [
            *account["equity_adjustments"],
            *account["cash_restriction_items"],
        ]
    }
    cash_rows = []
    cash_adjustments = Decimal("0")
    for index, item in enumerate(raw_cash_rows):
        field = f"scenario.{key}.cash_adjustments[{index}]"
        reject_unknown_fields(item, SCENARIO_CASH_FIELDS, field)
        adjustment_id = identifier(item.get("id"), f"{field}.id")
        if adjustment_id in account_bridge_ids:
            raise ValueError(
                f"{field}.id duplicates an account bridge or restriction item"
            )
        amount = decimal(item.get("amount"), f"scenario.{key}.cash_adjustments[{index}].amount")
        source = identifier(item.get("source"), f"{field}.source")
        if item.get("confirmed") is not True:
            raise ValueError(f"{field}.confirmed must be true")
        available_at_text = item.get("available_at")
        available_at = aware_datetime(available_at_text, f"{field}.available_at")
        if available_at > scenario_as_of:
            raise ValueError(f"{field}.available_at is later than scenario as_of")
        if item.get("restriction_status") != "unrestricted":
            raise ValueError(f"{field}.restriction_status must be unrestricted")
        if item.get("already_in_bridge_equity") is not False:
            raise ValueError(f"{field}.already_in_bridge_equity must be false")
        cash_rows.append({
            "id": adjustment_id,
            "amount": amount,
            "source": source,
            "confirmed": True,
            "available_at": identifier(available_at_text, f"{field}.available_at"),
            "restriction_status": "unrestricted",
            "already_in_bridge_equity": False,
            "applied_to_scenario_bridge": True,
        })
        cash_adjustments += amount
    existing = nonnegative(
        row.get("existing_margin", account["existing_margin"]), f"scenario.{key}.existing_margin"
    )
    proposed = nonnegative(
        row.get("proposed_margin", account["proposed_margin"]), f"scenario.{key}.proposed_margin"
    )
    offset = nonnegative(
        row.get("verified_margin_offset", account["verified_margin_offset"]),
        f"scenario.{key}.verified_margin_offset",
    )
    if offset > existing + proposed:
        raise ValueError(f"scenario {key} margin offset exceeds gross margin")
    total_margin = existing + proposed - offset
    equity = account["bridge_equity"] + pnl + cash_adjustments
    available = equity - total_margin - account["cash_restrictions"]
    cash_ok = available >= account["cash_floor"] if account["cash_floor"] is not None else None
    margin_ok = total_margin <= account["margin_cap"] if account["margin_cap"] is not None else None
    known_checks = [value for value in (cash_ok, margin_ok) if value is not None]
    return {
        "id": key,
        "scenario_plan_id": plan_id,
        "scenario_definition_id": definition_id,
        "scenario_as_of": identifier(scenario_as_of_text, f"scenario.{key}.as_of"),
        "scenario_marks": [
            {"id": instrument, "scenario_price": price}
            for instrument, price in marks.items()
        ],
        "pnl_components": components,
        "pnl_component_count": len(components),
        "pnl_total": pnl,
        "component_sum_matches_total": sum(
            (item["pnl"] for item in components), Decimal("0")
        ) == pnl,
        "cash_adjustments": cash_rows,
        "cash_adjustments_total": cash_adjustments,
        "bridge_equity_after_scenario": equity,
        "existing_margin": existing,
        "proposed_margin": proposed,
        "verified_margin_offset": offset,
        "total_margin": total_margin,
        "available_cash_after_stress": available,
        "cash_floor_ok": cash_ok,
        "margin_cap_ok": margin_ok,
        "all_known_constraints_passed": all(known_checks) if known_checks else None,
    }


def calculate(payload: dict[str, Any], *, require_provenance: bool = True) -> dict[str, Any]:
    if not isinstance(payload, dict) or payload.get("version") != INPUT_VERSION:
        raise ValueError(f"input version must be {INPUT_VERSION}")
    if require_provenance is not True:
        raise ValueError("field-level provenance is mandatory and cannot be disabled")
    reject_unknown_fields(payload, TOP_LEVEL_FIELDS, "input")
    field_sources = normalize_field_sources(payload, required=True)
    basis_rows = unique_rows(payload.get("basis_trades"), "basis_trades")
    basis = [
        {
            **calculate_basis_trade(row),
            "source_fields": source_subset(field_sources, f"/basis_trades/{index}"),
        }
        for index, row in enumerate(basis_rows)
    ]
    option_rows = unique_rows(payload.get("short_options"), "short_options")
    options = [
        {
            **calculate_short_option(row),
            "source_fields": source_subset(field_sources, f"/short_options/{index}"),
        }
        for index, row in enumerate(option_rows)
    ]
    account_row = payload.get("account")
    if account_row is not None and not isinstance(account_row, dict):
        raise ValueError("account must be an object")
    account = calculate_account(account_row) if account_row is not None else None
    if account is not None:
        account["source_fields"] = source_subset(field_sources, "/account")
    instruments, instrument_lookup = load_instruments(payload.get("instruments"))
    scenario_definitions, definition_lookup = load_scenario_definitions(
        payload.get("scenario_definitions"), instrument_lookup
    )
    scenario_plans, plan_lookup = load_scenario_plans(
        payload.get("scenario_plans"), instrument_lookup
    )
    scenario_rows = unique_rows(payload.get("scenarios"), "scenarios")
    if scenario_rows and account is None:
        raise ValueError("scenarios require account inputs")
    scenario_mode = any((instruments, scenario_definitions, scenario_plans, scenario_rows))
    if scenario_mode and not all((instruments, scenario_definitions, scenario_plans, scenario_rows)):
        raise ValueError(
            "scenario analysis requires instruments, definitions, plans and scenario rows"
        )
    pairs = []
    for index, row in enumerate(scenario_rows):
        pairs.append((
            identifier(row.get("plan_id"), f"scenarios[{index}].plan_id"),
            identifier(row.get("definition_id"), f"scenarios[{index}].definition_id"),
        ))
    expected_pairs = {
        (plan_id, definition_id)
        for plan_id in plan_lookup
        for definition_id in definition_lookup
    }
    if scenario_mode and (len(pairs) != len(set(pairs)) or set(pairs) != expected_pairs):
        raise ValueError(
            "scenarios must cover every scenario plan and definition exactly once"
        )
    scenarios = [
        {
            **calculate_scenario(row, account, definition_lookup, plan_lookup, instrument_lookup),
            "source_fields": source_subset(
                field_sources,
                "/account",
                "/instruments",
                "/scenario_definitions",
                "/scenario_plans",
                f"/scenarios/{index}",
            ),
        }
        for index, row in enumerate(scenario_rows)
    ]
    shared_times: dict[str, str] = {}
    for row in scenarios:
        definition_id = row["scenario_definition_id"]
        scenario_as_of = row["scenario_as_of"]
        if definition_id in shared_times and shared_times[definition_id] != scenario_as_of:
            raise ValueError(
                f"all plans sharing scenario definition {definition_id} must use the same "
                "as_of, cash adjustments and margin are plan-specific"
            )
        shared_times[definition_id] = scenario_as_of
    return {
        "version": VERSION,
        "basis_trades": basis,
        "account": account,
        "short_options": options,
        "instruments": instruments,
        "scenario_definitions": scenario_definitions,
        "scenario_plans": scenario_plans,
        "scenarios": scenarios,
        "field_sources": field_sources,
        "checks": {
            "basis_decomposition_checked": len(basis),
            "account_total_margin_includes_existing_and_proposed": account is not None,
            "short_option_close_uses_ask": len(options),
            "scenario_totals_derived_from_components": len(scenarios),
            "scenario_components_retained": len(scenarios),
            "scenario_contract_terms_frozen": len(instruments),
            "scenario_plan_definition_coverage_complete": (
                len(pairs) == len(expected_pairs) and set(pairs) == expected_pairs
            ),
            "scenario_definition_conditions_shared": len(shared_times),
            "scenario_definition_as_of_shared": len(shared_times),
        },
    }


def open_directory(path: Path, *, create: bool = False, exclusive_leaf: bool = False) -> int:
    path = Path(path)
    if path.is_absolute() and len(path.parts) > 1 and path.parts[1] in {"var", "tmp"}:
        alias = Path("/") / path.parts[1]
        expected = Path("/private") / path.parts[1]
        if alias.is_symlink() and alias.resolve() == expected:
            path = expected.joinpath(*path.parts[2:])
    if ".." in path.parts:
        raise ValueError("directory path must not contain parent traversal")
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open("/" if path.is_absolute() else ".", flags)
    parts = path.parts[1:] if path.is_absolute() else path.parts
    if exclusive_leaf and not any(part not in ("", ".") for part in parts):
        os.close(descriptor)
        raise ValueError("output directory must name a new non-root directory")
    try:
        for index, part in enumerate(parts):
            if part in ("", "."):
                continue
            leaf = index == len(parts) - 1
            try:
                child = os.open(part, flags, dir_fd=descriptor)
            except FileNotFoundError:
                if not create:
                    raise
                os.mkdir(part, 0o700, dir_fd=descriptor)
                child = os.open(part, flags, dir_fd=descriptor)
            else:
                if exclusive_leaf and leaf:
                    os.close(child)
                    raise FileExistsError(f"output directory already exists: {path}")
            details = os.fstat(child)
            if not stat.S_ISDIR(details.st_mode):
                os.close(child)
                raise ValueError(f"expected a directory without symlink: {part}")
            os.close(descriptor)
            descriptor = child
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def read_regular_bytes_at(directory_fd: int, name: str) -> tuple[bytes, os.stat_result]:
    if Path(name).name != name:
        raise ValueError(f"expected a leaf filename: {name}")
    flags = (
        os.O_RDONLY
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
        | getattr(os, "O_CLOEXEC", 0)
    )
    descriptor = os.open(name, flags, dir_fd=directory_fd)
    try:
        details = os.fstat(descriptor)
        if not stat.S_ISREG(details.st_mode):
            raise ValueError(f"expected a regular file without symlink: {name}")
        chunks = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks), details
    finally:
        os.close(descriptor)


def read_regular_bytes(path: Path) -> tuple[bytes, os.stat_result]:
    directory_fd = open_directory(Path(path).parent)
    try:
        return read_regular_bytes_at(directory_fd, Path(path).name)
    finally:
        os.close(directory_fd)


def regular_file_digest(path: Path) -> tuple[str, int]:
    data, details = read_regular_bytes(path)
    return hashlib.sha256(data).hexdigest(), details.st_size


def sha256(path: Path) -> str:
    return regular_file_digest(path)[0]


def regular_file_size(path: Path) -> int:
    return regular_file_digest(path)[1]


class exclusive_text:
    def __init__(self, path: Path, *, newline: str | None = None):
        self.path = path
        self.newline = newline
        self.stream = None

    def __enter__(self):
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        self.directory_fd = open_directory(self.path.parent)
        try:
            descriptor = os.open(self.path.name, flags, 0o600, dir_fd=self.directory_fd)
        except BaseException:
            os.close(self.directory_fd)
            raise
        self.stream = os.fdopen(
            descriptor, "w", encoding="utf-8", newline=self.newline
        )
        return self.stream

    def __exit__(self, exc_type, exc, traceback):
        assert self.stream is not None
        self.stream.close()
        os.close(self.directory_fd)


def write_text_exclusive(path: Path, text: str) -> None:
    with exclusive_text(path) as stream:
        stream.write(text)


def write_bytes_exclusive_at(directory_fd: int, name: str, data: bytes) -> None:
    if Path(name).name != name:
        raise ValueError(f"expected a leaf filename: {name}")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(name, flags, 0o600, dir_fd=directory_fd)
    try:
        view = memoryview(data)
        while view:
            written = os.write(descriptor, view)
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def write_text_exclusive_at(directory_fd: int, name: str, text: str) -> None:
    write_bytes_exclusive_at(directory_fd, name, text.encode("utf-8"))


def read_text_no_follow(path: Path) -> str:
    data, _ = read_regular_bytes(path)
    return data.decode("utf-8")


def parse_csv_bytes(data: bytes, name: str) -> tuple[list[str], list[dict[str, str]]]:
    stream = io.StringIO(data.decode("utf-8"), newline="")
    reader = csv.DictReader(stream)
    fields = reader.fieldnames
    if fields is None:
        raise ValueError(f"missing CSV header: {name}")
    return fields, list(reader)


def csv_cell(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        text = json.dumps(
            json_value(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
    elif isinstance(value, str):
        text = value
    elif isinstance(value, Decimal):
        return decimal_text(value)
    else:
        return value
    return "'" + text if text.startswith(CSV_FORMULA_PREFIXES) else text


def write_csv(path: Path, rows: list[dict[str, Any]], fields: tuple[str, ...]) -> None:
    with exclusive_text(path, newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: csv_cell(row.get(key)) for key in fields})


def csv_bytes(rows: list[dict[str, Any]], fields: tuple[str, ...]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    for row in rows:
        writer.writerow({key: csv_cell(row.get(key)) for key in fields})
    return stream.getvalue().encode("utf-8")


def write_outputs(
    payload: dict[str, Any],
    result: dict[str, Any],
    out_dir: Path,
    *,
    input_bytes: bytes | None = None,
    require_provenance: bool = True,
) -> dict[str, Any]:
    if require_provenance is not True:
        raise ValueError("field-level provenance is mandatory and cannot be disabled")
    normalized_sources = normalize_field_sources(payload, required=True)
    if result.get("field_sources") != normalized_sources:
        raise ValueError("result field_sources do not match calculation input")
    raw_input = input_bytes if input_bytes is not None else (
        json.dumps(json_value(payload), ensure_ascii=False, indent=2) + "\n"
    ).encode("utf-8")
    parsed_input = parse_json_bytes(raw_input)
    if not isinstance(parsed_input, dict) or parsed_input.get("version") != INPUT_VERSION:
        raise ValueError("input bytes do not contain the calculation payload version")
    if semantic_input_value(parsed_input) != semantic_input_value(payload):
        raise ValueError("input bytes do not match the calculation payload")
    directory_fd = open_directory(out_dir, create=True, exclusive_leaf=True)
    names = [
        "input.json", "summary.json", "basis.csv", "account.csv", "short_options.csv",
        "scenarios.csv",
    ]
    json_result = json_value(result)
    try:
        write_bytes_exclusive_at(directory_fd, "input.json", raw_input)
        write_text_exclusive_at(
            directory_fd,
            "summary.json",
            json.dumps(json_result, ensure_ascii=False, indent=2) + "\n",
        )
        csv_outputs = {
            "basis.csv": (result["basis_trades"], CSV_REQUIRED_FIELDS["basis.csv"]),
            "account.csv": (
                [result["account"]] if result["account"] else [],
                CSV_REQUIRED_FIELDS["account.csv"],
            ),
            "short_options.csv": (
                result["short_options"], CSV_REQUIRED_FIELDS["short_options.csv"]
            ),
            "scenarios.csv": (result["scenarios"], CSV_REQUIRED_FIELDS["scenarios.csv"]),
        }
        for name, (rows, fields) in csv_outputs.items():
            write_bytes_exclusive_at(directory_fd, name, csv_bytes(rows, fields))
        listed = []
        for name in names:
            data, details = read_regular_bytes_at(directory_fd, name)
            listed.append({
                "path": name,
                "sha256": hashlib.sha256(data).hexdigest(),
                "bytes": details.st_size,
            })
        manifest = {
            "version": VERSION,
            "input_path": "input.json",
            "input_sha256": hashlib.sha256(raw_input).hexdigest(),
            "provenance_required": True,
            "field_sources_sha256": hashlib.sha256(
                json.dumps(
                    normalized_sources, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                ).encode("utf-8")
            ).hexdigest(),
            "files": listed,
            "row_counts": {
                "basis.csv": len(result["basis_trades"]),
                "account.csv": 1 if result["account"] else 0,
                "short_options.csv": len(result["short_options"]),
                "scenarios.csv": len(result["scenarios"]),
            },
            "numeric_columns": {
                name: sorted(fields) for name, fields in CSV_NUMERIC_FIELDS.items()
            },
            "required_columns": {
                name: list(fields) for name, fields in CSV_REQUIRED_FIELDS.items()
            },
        }
        write_text_exclusive_at(
            directory_fd,
            "manifest.json",
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        )
    finally:
        os.close(directory_fd)
    manifest_path = out_dir / "manifest.json"
    verify_manifest_data(manifest_path)
    write_text_exclusive(
        out_dir / "run.log",
        f"engine={VERSION}\nstatus=passed\nmanifest_sha256={sha256(manifest_path)}\n",
    )
    verify_manifest(manifest_path)
    return manifest


def _verify_manifest_data(path: Path) -> tuple[dict[str, Any], str]:
    manifest_data, _ = read_regular_bytes(path)
    manifest = json.loads(manifest_data.decode("utf-8"))
    if (
        manifest.get("version") != VERSION
        or not isinstance(manifest.get("files"), list)
        or manifest.get("provenance_required") is not True
    ):
        raise ValueError("invalid manifest")
    listed: set[str] = set()
    contents: dict[str, bytes] = {}
    directory_fd = open_directory(path.parent)
    try:
        for row in manifest["files"]:
            if not isinstance(row, dict):
                raise ValueError("invalid manifest file entry")
            name = identifier(row.get("path"), "manifest.files.path")
            if Path(name).name != name or name in listed:
                raise ValueError(f"invalid or missing manifest file: {name}")
            listed.add(name)
            try:
                data, details = read_regular_bytes_at(directory_fd, name)
            except (OSError, ValueError) as exc:
                raise ValueError(f"invalid or missing manifest file: {name}") from exc
            if (
                hashlib.sha256(data).hexdigest() != row.get("sha256")
                or details.st_size != row.get("bytes")
            ):
                raise ValueError(f"manifest mismatch: {name}")
            contents[name] = data
    finally:
        os.close(directory_fd)
    expected = {
        "input.json", "summary.json", "basis.csv", "account.csv", "short_options.csv",
        "scenarios.csv",
    }
    if listed != expected:
        raise ValueError("manifest file set is incomplete")
    input_data = contents["input.json"]
    if (
        manifest.get("input_path") != "input.json"
        or manifest.get("input_sha256") != hashlib.sha256(input_data).hexdigest()
    ):
        raise ValueError("manifest input hash does not bind the preserved input bytes")
    input_payload = parse_json_bytes(input_data)
    if not isinstance(input_payload, dict) or input_payload.get("version") != INPUT_VERSION:
        raise ValueError("preserved input version does not match engine input version")
    field_sources = normalize_field_sources(input_payload, required=True)
    source_hash = hashlib.sha256(
        json.dumps(
            field_sources, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()
    if manifest.get("field_sources_sha256") != source_hash:
        raise ValueError("manifest field_sources hash changed")
    summary = json.loads(contents["summary.json"].decode("utf-8"))
    if not isinstance(summary, dict) or set(summary) != SUMMARY_REQUIRED_FIELDS:
        raise ValueError("summary field contract changed")
    if summary.get("version") != VERSION:
        raise ValueError("summary version does not match engine version")
    if summary.get("field_sources") != field_sources:
        raise ValueError("summary field_sources do not match the preserved input")
    expected_result = calculate(input_payload)
    expected_summary = json_value(expected_result)
    if summary != expected_summary:
        raise ValueError(
            "summary row contract changed: content does not match deterministic "
            "recalculation from input.json"
        )
    if not all(isinstance(summary[name], list) for name in (
        "basis_trades", "short_options", "instruments", "scenario_definitions",
        "scenario_plans", "scenarios",
    )) or (summary["account"] is not None and not isinstance(summary["account"], dict)):
        raise ValueError("summary collection contract changed")
    if not isinstance(summary["checks"], dict):
        raise ValueError("summary checks contract changed")
    expected_counts = {
        "basis.csv": len(summary["basis_trades"]),
        "account.csv": 1 if summary["account"] else 0,
        "short_options.csv": len(summary["short_options"]),
        "scenarios.csv": len(summary["scenarios"]),
    }
    parsed_csv = {name: parse_csv_bytes(contents[name], name) for name in expected_counts}
    actual_counts = {name: len(rows) for name, (_, rows) in parsed_csv.items()}
    if manifest.get("row_counts") != expected_counts or actual_counts != expected_counts:
        raise ValueError("summary, CSV and manifest row counts disagree")
    numeric_columns = manifest.get("numeric_columns")
    if numeric_columns != {name: sorted(fields) for name, fields in CSV_NUMERIC_FIELDS.items()}:
        raise ValueError("manifest numeric-column contract changed")
    required_columns = {name: list(fields) for name, fields in CSV_REQUIRED_FIELDS.items()}
    if manifest.get("required_columns") != required_columns:
        raise ValueError("manifest required-column contract changed")
    summary_rows = {
        "basis.csv": summary["basis_trades"],
        "account.csv": [summary["account"]] if summary["account"] else [],
        "short_options.csv": summary["short_options"],
        "scenarios.csv": summary["scenarios"],
    }
    expected_result_rows = {
        "basis.csv": expected_result["basis_trades"],
        "account.csv": [expected_result["account"]] if expected_result["account"] else [],
        "short_options.csv": expected_result["short_options"],
        "scenarios.csv": expected_result["scenarios"],
    }
    for name, fields in CSV_NUMERIC_FIELDS.items():
        header, rows = parsed_csv[name]
        expected_header = list(CSV_REQUIRED_FIELDS[name])
        if header != expected_header:
            raise ValueError(f"CSV column contract changed: {name}")
        if contents[name] != csv_bytes(expected_result_rows[name], CSV_REQUIRED_FIELDS[name]):
            raise ValueError(f"CSV does not match the complete summary rows: {name}")
        for row_index, summary_row in enumerate(summary_rows[name]):
            if not isinstance(summary_row, dict) or set(summary_row) != set(expected_header):
                raise ValueError(f"summary row contract changed: {name}[{row_index}]")
            if name == "basis.csv":
                expected_sources = source_subset(field_sources, f"/basis_trades/{row_index}")
            elif name == "account.csv":
                expected_sources = source_subset(field_sources, "/account")
            elif name == "short_options.csv":
                expected_sources = source_subset(field_sources, f"/short_options/{row_index}")
            else:
                expected_sources = source_subset(
                    field_sources,
                    "/account",
                    "/instruments",
                    "/scenario_definitions",
                    "/scenario_plans",
                    f"/scenarios/{row_index}",
                )
            if summary_row["source_fields"] != expected_sources:
                raise ValueError(f"summary source mapping changed: {name}[{row_index}]")
        for row_index, (csv_row, summary_row) in enumerate(zip(rows, summary_rows[name])):
            expected_sources = json.dumps(
                summary_row["source_fields"],
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            if csv_row["source_fields"] != expected_sources:
                raise ValueError(f"CSV source mapping changed: {name}[{row_index}]")
            for field in fields:
                expected = "" if summary_row[field] is None else str(summary_row[field])
                actual = csv_row[field]
                if actual != expected:
                    raise ValueError(f"numeric CSV mismatch: {name}[{row_index}].{field}")
                if actual:
                    decimal(actual, f"{name}[{row_index}].{field}")
    result = {"status": "passed", "files_verified": len(listed), "row_counts": actual_counts}
    return result, hashlib.sha256(manifest_data).hexdigest()


def verify_manifest_data(path: Path) -> dict[str, Any]:
    return _verify_manifest_data(path)[0]


def verify_manifest(path: Path) -> dict[str, Any]:
    result, manifest_sha256 = _verify_manifest_data(path)
    expected_log = (
        f"engine={VERSION}\nstatus=passed\nmanifest_sha256={manifest_sha256}\n"
    )
    if read_text_no_follow(path.parent / "run.log") != expected_log:
        raise ValueError("run.log is missing or does not bind the verified manifest")
    return {**result, "completion_receipt_verified": True}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("calculate")
    run.add_argument("input", type=Path)
    run.add_argument("--out-dir", type=Path, required=True)
    verify = commands.add_parser("verify")
    verify.add_argument("manifest", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "verify":
            value = verify_manifest(args.manifest)
        else:
            input_bytes, _ = read_regular_bytes(args.input)
            payload = parse_json_bytes(input_bytes)
            result = calculate(payload, require_provenance=True)
            manifest = write_outputs(
                payload,
                result,
                args.out_dir,
                input_bytes=input_bytes,
                require_provenance=True,
            )
            value = {"status": "passed", "result": result, "manifest": manifest}
        print(json.dumps(json_value(value), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "failed", "reason": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
