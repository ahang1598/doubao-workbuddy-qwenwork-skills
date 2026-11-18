#!/usr/bin/env python3
"""Build a net-profit-to-CFO-to-FCF bridge and payout coverage report from structured company data.

Pure-stdlib deterministic calculator accepting an input directory or explicit CSV/JSON files.
All calculations follow strict accounting identity contracts with zero case-specific hardcoding.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


BRIDGE_METRICS = (
    "net_profit",
    "depreciation_amortization",
    "share_based_compensation",
    "disposal_gain",
    "inventory_write_down",
    "accounts_receivable_change",
    "inventory_change",
    "accounts_payable_change",
    "contract_liabilities_change",
    "other_operating_items_change",
)
ADJUSTMENT_METRICS = BRIDGE_METRICS[1:]
REPORTED_METRICS = ("operating_cash_flow", "capex", "free_cash_flow")
NON_STANDARD_CASHFLOW_PROFILES = {
    "balance_sheet_driven",
    "pre_revenue",
}
ALLOWED_DIRECTORY_JSON = {
    "adjustments.json",
    "payouts.json",
    "cashflow_facts.json",
    "company_facts.json",
    "conflicts.json",
    "facts.json",
    "supplemental.json",
}
LINE_PREFIX = re.compile(r"^\s*\d+\|")


class InputError(ValueError):
    """Raised when an input cannot produce a reliable financial bridge."""


def _number(value: Any, field: str) -> float | int:
    if isinstance(value, bool) or value is None:
        raise InputError(f"{field} must be numeric")
    try:
        result = float(str(value).replace(",", "").strip())
    except ValueError as exc:
        raise InputError(f"{field} must be numeric: {value!r}") from exc
    return int(result) if result.is_integer() else result


def _clean_csv_line(line: str) -> str:
    return LINE_PREFIX.sub("", line)


def load_csv(path: Path) -> list[dict[str, Any]]:
    """Load long-form financial rows using the documented metric schema."""
    text = path.read_text(encoding="utf-8-sig")
    reader = csv.DictReader(_clean_csv_line(line) for line in text.splitlines())
    required = {"period", "metric", "value"}
    if not reader.fieldnames or not required.issubset(reader.fieldnames):
        raise InputError(f"{path}: CSV requires columns {sorted(required)}")

    rows: list[dict[str, Any]] = []
    for line_number, row in enumerate(reader, 2):
        if not row.get("metric") or not row.get("period"):
            continue
        cleaned = {
            key: (value.strip() if isinstance(value, str) else value)
            for key, value in row.items()
        }
        first_field = reader.fieldnames[0]
        if cleaned.get(first_field):
            cleaned[first_field] = LINE_PREFIX.sub("", cleaned[first_field])
        cleaned["value"] = _number(cleaned["value"], f"{path}:{line_number}:value")
        cleaned["_input"] = str(path)
        rows.append(cleaned)
    return rows


def load_json(path: Path) -> dict[str, Any]:
    """Load supplemental definitions, adjustments, payouts, or record arrays from JSON."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise InputError(f"{path}: invalid JSON: {exc}") from exc
    if isinstance(value, list):
        return {"records": value}
    if not isinstance(value, dict):
        raise InputError(f"{path}: JSON root must be an object or record list")
    return value


def _merge(target: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    for key, value in incoming.items():
        if key in target and isinstance(target[key], dict) and isinstance(value, dict):
            _merge(target[key], value)
        elif key in target and isinstance(target[key], list) and isinstance(value, list):
            target[key].extend(value)
        else:
            target[key] = value
    return target


def _rows_from_json(data: dict[str, Any], source: str) -> list[dict[str, Any]]:
    raw_rows = data.get("records", data.get("financials", []))
    if not isinstance(raw_rows, list):
        raise InputError(f"{source}: records/financials must be an array")
    rows = []
    for index, row in enumerate(raw_rows):
        if not isinstance(row, dict) or not {"period", "metric", "value"}.issubset(row):
            raise InputError(f"{source}: record {index} requires period, metric, value")
        item = dict(row)
        item["value"] = _number(item["value"], f"{source}:record {index}:value")
        item["_input"] = source
        rows.append(item)
    return rows


def resolve_inputs(
    input_dir: Path | None,
    csv_paths: list[Path],
    json_paths: list[Path],
) -> tuple[list[dict[str, Any]], dict[str, Any], list[str]]:
    """Collect structured rows and supplemental metadata from directory, CSV, and JSON args."""
    rows: list[dict[str, Any]] = []
    supplemental: dict[str, Any] = {}
    inputs: list[str] = []

    if input_dir:
        if not input_dir.is_dir():
            raise InputError(f"input directory does not exist: {input_dir}")
        default_csv = input_dir / "financials.csv"
        if default_csv.exists() and default_csv not in csv_paths:
            csv_paths = [default_csv, *csv_paths]
        for name in sorted(ALLOWED_DIRECTORY_JSON):
            candidate = input_dir / name
            if candidate.exists() and candidate not in json_paths:
                json_paths.append(candidate)

    for path in csv_paths:
        if not path.is_file():
            raise InputError(f"CSV does not exist: {path}")
        rows.extend(load_csv(path))
        inputs.append(str(path))
    for path in json_paths:
        if not path.is_file():
            raise InputError(f"JSON does not exist: {path}")
        data = load_json(path)
        rows.extend(_rows_from_json(data, str(path)))
        _merge(
            supplemental,
            {key: value for key, value in data.items() if key not in {"records", "financials"}},
        )
        inputs.append(str(path))
    if not rows:
        raise InputError("no financial records found; provide a directory, --csv, or --json")
    return rows, supplemental, inputs


def _pct_change(current: float, prior: float) -> float | None:
    if prior == 0:
        return None
    return (current / prior - 1) * 100


def _rounded(value: float | int | None) -> float | int | None:
    if value is None:
        return None
    if abs(float(value) - round(float(value))) < 1e-12:
        return int(round(float(value)))
    return round(float(value), 6)


def _period_sort_key(period: str) -> tuple[int, int, str]:
    match = re.search(r"(\d{4})(?:H([12])|Q([1-4]))?", period)
    if not match:
        return (0, 0, period)
    subperiod = int(match.group(2) or match.group(3) or 0)
    return (int(match.group(1)), subperiod, period)


def _prior_year_period(current: str, periods: Iterable[str], *, balance: bool = False) -> str | None:
    match = re.fullmatch(r"(?:FY)?(\d{4})(?:(?:H[12]|Q[1-4])(?:-?YTD)?)?", current)
    if match is None and balance:
        match = re.fullmatch(r"(\d{4})-\d{2}-\d{2}", current)
    if match is None:
        return None
    prior_year = f"{int(match.group(1)) - 1:04d}"
    prior = current[:match.start(1)] + prior_year + current[match.end(1):]
    return prior if prior in periods else None


def _sum_optional_items(raw: Any, field: str) -> tuple[float, Any]:
    """Normalize an optional numeric value, dict, or item list into a float total."""
    if raw is None:
        return 0.0, None
    if isinstance(raw, (int, float, str)) and not isinstance(raw, bool):
        val = float(_number(raw, field))
        if val < 0:
            raise InputError(f"{field} must be non-negative")
        return val, _rounded(val)
    if isinstance(raw, dict):
        total = 0.0
        cleaned: dict[str, float | int | None] = {}
        for k, v in raw.items():
            num = float(_number(v, f"{field}.{k}"))
            if num < 0:
                raise InputError(f"{field}.{k} must be non-negative")
            total += num
            cleaned[str(k)] = _rounded(num)
        return total, cleaned
    if isinstance(raw, list):
        total = 0.0
        cleaned_list = []
        for idx, entry in enumerate(raw):
            if not isinstance(entry, dict) or not entry.get("name") or entry.get("amount") is None:
                raise InputError(f"{field}[{idx}] requires name and amount")
            num = float(_number(entry["amount"], f"{field}[{idx}].amount"))
            if num < 0:
                raise InputError(f"{field}[{idx}].amount must be non-negative")
            total += num
            cleaned_list.append({"name": str(entry["name"]), "amount": _rounded(num)})
        return total, cleaned_list
    raise InputError(f"{field} must be a number, object, or list")


def _build_adjusted_fcf_bridge(
    metrics: dict[str, float | int],
    definition: Any,
) -> dict[str, Any] | None:
    if definition is None:
        return None
    if not isinstance(definition, dict):
        raise InputError("adjusted_fcf_definition must be an object")
    for field in (
        "name",
        "reported_metric",
        "starting_metric",
        "statutory_total_cash_metric",
        "source",
    ):
        if not definition.get(field):
            raise InputError(f"adjusted_fcf_definition missing {field}")
    reported_metric = str(definition["reported_metric"])
    starting_metric = str(definition["starting_metric"])
    total_cash_metric = str(definition["statutory_total_cash_metric"])
    missing = [
        metric for metric in (reported_metric, starting_metric, total_cash_metric)
        if metric not in metrics
    ]
    if missing:
        return {
            "name": definition["name"],
            "missing_metrics": missing,
            "reconciles": False,
        }
    adjustments = definition.get("adjustments", [])
    if not isinstance(adjustments, list):
        raise InputError("adjusted_fcf_definition.adjustments must be an array")
    adjustment_total = 0.0
    normalized = []
    for index, item in enumerate(adjustments):
        if not isinstance(item, dict):
            raise InputError(f"adjusted FCF adjustment {index} must be an object")
        for field in ("name", "amount", "cash_or_non_cash", "source"):
            if item.get(field) in {None, ""}:
                raise InputError(f"adjusted FCF adjustment {index} missing {field}")
        amount = float(_number(item["amount"], f"adjusted FCF adjustment {index}"))
        adjustment_total += amount
        normalized.append({**item, "amount": _rounded(amount)})
    reconciled = float(metrics[starting_metric]) + adjustment_total
    reported = float(metrics[reported_metric])
    result: dict[str, Any] = {
        "name": definition["name"],
        "reported_metric": reported_metric,
        "reported_value": _rounded(reported),
        "starting_metric": starting_metric,
        "starting_value": metrics[starting_metric],
        "statutory_total_cash_metric": total_cash_metric,
        "statutory_total_cash_value": metrics[total_cash_metric],
        "adjustments": normalized,
        "calculated_value": _rounded(reconciled),
        "unreconciled_difference": _rounded(reconciled - reported),
        "reconciles": abs(reconciled - reported) <= 0.01,
        "source": definition["source"],
    }
    if definition.get("scope_notes"):
        result["scope_notes"] = definition["scope_notes"]
    return result


def _classify_fcf_discrepancy(
    calculated_fcf: float | None,
    reported_fcf: float | int | None,
) -> dict[str, Any] | None:
    """Compute numeric gap and direction between conventional FCF and company-reported FCF."""
    if calculated_fcf is None or reported_fcf is None:
        return None
    diff = float(calculated_fcf) - float(reported_fcf)
    if abs(diff) <= 0.01:
        direction = "aligned"
    elif diff > 0:
        direction = "reported_lower_than_conventional"
    else:
        direction = "reported_higher_than_conventional"
    return {
        "conventional_minus_reported": _rounded(diff),
        "direction": direction,
    }


def _apply_one_time_cash_adjustments(
    period: str,
    reported_cfo: float | int | None,
    calculated_fcf: float | None,
    raw_adjustments: Any,
) -> dict[str, Any] | None:
    """Normalize CFO/FCF by reversing one-time cash items already inside reported CFO."""
    if raw_adjustments is None:
        return None
    if not isinstance(raw_adjustments, list):
        raise InputError(f"one_time_cash_adjustments[{period}] must be an array")
    if not raw_adjustments or reported_cfo is None:
        return None

    total_cfo_delta = 0.0
    normalized_items = []
    for index, item in enumerate(raw_adjustments):
        if not isinstance(item, dict):
            raise InputError(f"one_time_cash_adjustments[{period}][{index}] must be an object")
        for field in ("name", "amount", "cash_direction", "source"):
            if item.get(field) in {None, ""}:
                raise InputError(
                    f"one_time_cash_adjustments[{period}][{index}] missing {field}"
                )
        if "already_in_reported_cfo" not in item or not isinstance(item["already_in_reported_cfo"], bool):
            raise InputError(
                f"one_time_cash_adjustments[{period}][{index}] requires boolean already_in_reported_cfo"
            )
        amount = float(_number(item["amount"], f"one_time_cash_adjustments[{period}][{index}].amount"))
        if amount < 0:
            raise InputError(
                f"one_time_cash_adjustments[{period}][{index}].amount must be non-negative; specify cash_direction"
            )
        direction = str(item["cash_direction"])
        if direction not in {"outflow", "inflow"}:
            raise InputError(
                f"one_time_cash_adjustments[{period}][{index}].cash_direction must be 'outflow' or 'inflow'"
            )
        if item["already_in_reported_cfo"]:
            signed_effect = amount if direction == "outflow" else -amount
        else:
            signed_effect = 0.0
        total_cfo_delta += signed_effect
        normalized_items.append({
            "name": str(item["name"]),
            "amount": _rounded(amount),
            "cash_direction": direction,
            "already_in_reported_cfo": item["already_in_reported_cfo"],
            "normalization_delta": _rounded(signed_effect),
            "source": str(item["source"]),
        })

    normalized_cfo = float(reported_cfo) + total_cfo_delta
    normalized_fcf = float(calculated_fcf) + total_cfo_delta if calculated_fcf is not None else None
    return {
        "items": normalized_items,
        "total_cfo_normalization_delta": _rounded(total_cfo_delta),
        "normalized_cfo": _rounded(normalized_cfo),
        "normalized_fcf": _rounded(normalized_fcf),
        "is_company_official_non_gaap": False,
    }


def _compute_shareholder_coverage(
    period: str,
    cash_fcf: float | None,
    normalized_fcf: float | int | None,
    payout_spec: Any,
) -> dict[str, Any] | None:
    """Compute cash shareholder return coverage strictly against cash-basis FCF."""
    if payout_spec is None:
        return None
    if not isinstance(payout_spec, dict):
        raise InputError(f"shareholder_payouts[{period}] must be an object")

    dividends = float(_number(payout_spec.get("cash_dividends", 0), f"shareholder_payouts[{period}].cash_dividends"))
    buybacks = float(_number(payout_spec.get("cash_buybacks", 0), f"shareholder_payouts[{period}].cash_buybacks"))
    if dividends < 0 or buybacks < 0:
        raise InputError(f"shareholder_payouts[{period}] dividends/buybacks must be non-negative")

    other_dist_total, other_dist_detail = _sum_optional_items(
        payout_spec.get("other_cash_distributions"),
        f"shareholder_payouts[{period}].other_cash_distributions",
    )
    other_related_total, other_related_detail = _sum_optional_items(
        payout_spec.get("other_related_cash_outflows"),
        f"shareholder_payouts[{period}].other_related_cash_outflows",
    )
    non_cash_total, non_cash_detail = _sum_optional_items(
        payout_spec.get("non_cash_capital_commitments"),
        f"shareholder_payouts[{period}].non_cash_capital_commitments",
    )

    total_return = dividends + buybacks + other_dist_total
    total_with_related = total_return + other_related_total

    def _ratio_block(fcf_val: float | int | None) -> dict[str, Any] | None:
        if fcf_val is None:
            return None
        f = float(fcf_val)
        return {
            "fcf_basis_value": _rounded(f),
            "fully_covered": f >= total_return - 1e-9,
            "cash_surplus_or_gap": _rounded(f - total_return),
            "payout_of_fcf_pct": _rounded((total_return / f) * 100) if f > 0 else None,
            "fcf_coverage_multiple": _rounded(f / total_return) if total_return > 0 else None,
            "surplus_after_other_related_cash_outflows": (
                _rounded(f - total_with_related) if other_related_detail is not None else None
            ),
        }

    return {
        "cash_dividends": _rounded(dividends),
        "cash_buybacks": _rounded(buybacks),
        "other_cash_distributions": other_dist_detail,
        "total_cash_shareholder_return": _rounded(total_return),
        "other_related_cash_outflows": other_related_detail,
        "cash_fcf_coverage": _ratio_block(cash_fcf),
        "normalized_fcf_coverage": _ratio_block(normalized_fcf),
        "non_cash_capital_commitments": {
            "total": _rounded(non_cash_total),
            "detail": non_cash_detail,
            "excluded_from_cash_payout_coverage": True,
        } if non_cash_detail is not None else None,
    }


def build_report(
    rows: list[dict[str, Any]],
    supplemental: dict[str, Any],
    inputs: list[str],
) -> dict[str, Any]:
    """Build reconciled per-period cashflow bridges, growth rates, and payout coverage."""
    by_period: dict[str, dict[str, float | int]] = defaultdict(dict)
    row_sources: dict[str, dict[str, str]] = defaultdict(dict)
    conflicts: list[dict[str, Any]] = []
    metadata: dict[str, str | None] = {}
    for field in ("entity", "currency", "unit", "scope"):
        values = {str(row[field]).strip() for row in rows if row.get(field)}
        if len(values) > 1:
            raise InputError(f"multiple {field} values found: {', '.join(sorted(values))}")
        if values and any(not row.get(field) for row in rows):
            raise InputError(f"{field} is missing from some financial records")
        metadata[field] = next(iter(values), None)

    cashflow_profile = supplemental.get("cashflow_profile") or supplemental.get("entity_profile")
    standard_applicable = supplemental.get("standard_cashflow_applicable", True)
    if standard_applicable is False or cashflow_profile in NON_STANDARD_CASHFLOW_PROFILES:
        return {
            "schema_version": "3.0",
            "entity": metadata["entity"],
            "cashflow_profile": cashflow_profile,
            "applicability": {
                "can_run_standard_cashflow_bridge": False,
                "reason": (
                    "standard net-profit-to-CFO-to-FCF bridge is marked non-applicable "
                    f"for profile={cashflow_profile or 'custom'}"
                ),
            },
            "inputs": {
                "files": sorted(set(inputs)),
            },
            "bridges": {},
            "growth": {},
            "conflict_register": [],
            "all_bridges_reconcile": False,
        }

    conflicting_metrics: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        period = str(row["period"])
        metric = str(row["metric"])
        value = row["value"]
        source = str(row.get("source_locator") or row.get("_input"))
        if metric in by_period[period]:
            prior_value = by_period[period][metric]
            if prior_value != value and (metric != "capex" or abs(prior_value) != abs(value)):
                conflicting_metrics[period].add(metric)
                conflicts.append({
                    "conflict_id": f"DATA_{period}_{metric}",
                    "topic": metric,
                    "values": [by_period[period][metric], value],
                    "sources": [row_sources[period][metric], source],
                    "resolution": "unresolved_conflicting_structured_inputs",
                })
            continue
        by_period[period][metric] = value
        row_sources[period][metric] = source

    for period, metrics in conflicting_metrics.items():
        for metric in metrics:
            del by_period[period][metric]

    periods = sorted(by_period, key=_period_sort_key)
    one_time_by_period = supplemental.get("one_time_cash_adjustments")
    if one_time_by_period is not None and not isinstance(one_time_by_period, dict):
        raise InputError("one_time_cash_adjustments must map periods to adjustment arrays")
    payouts_by_period = supplemental.get("shareholder_payouts")
    if payouts_by_period is not None and not isinstance(payouts_by_period, dict):
        raise InputError("shareholder_payouts must map periods to payout objects")

    raw_additional = supplemental.get("additional_bridge_metrics")
    if raw_additional is not None and not isinstance(raw_additional, list):
        raise InputError("additional_bridge_metrics must be an array")
    additional_bridge = [
        str(m) for m in (raw_additional or []) if isinstance(m, str) and m
    ]
    bridge_order = tuple(dict.fromkeys((*BRIDGE_METRICS, "other_non_cash_items", "other_working_capital_changes", *additional_bridge)))
    adjustment_order = tuple(m for m in bridge_order if m != "net_profit")
    bridges: dict[str, Any] = {}
    for period in periods:
        metrics = by_period[period]
        unprovided_standard = [metric for metric in BRIDGE_METRICS if metric not in metrics]
        present_bridge_items = [metric for metric in bridge_order if metric in metrics]
        net_profit = metrics.get("net_profit")
        subtotal_present = (
            sum(float(metrics[metric]) for metric in present_bridge_items)
            if present_bridge_items else None
        )
        calculated_cfo = subtotal_present if net_profit is not None else None
        reported_cfo = metrics.get("operating_cash_flow")
        capex = abs(metrics["capex"]) if "capex" in metrics else None
        calculated_fcf = (
            float(reported_cfo) - float(capex)
            if reported_cfo is not None and capex is not None else None
        )
        cfo_difference = (
            calculated_cfo - float(reported_cfo)
            if calculated_cfo is not None and reported_cfo is not None else None
        )
        partial_residual = (
            float(reported_cfo) - float(subtotal_present)
            if subtotal_present is not None and reported_cfo is not None else None
        )

        reported_fcf = metrics.get("free_cash_flow")
        fcf_definition = supplemental.get("fcf_definition")
        if reported_fcf is not None:
            if not isinstance(fcf_definition, dict):
                raise InputError("free_cash_flow provided without fcf_definition metadata")
            for field in ("name", "kind", "formula", "source"):
                if not fcf_definition.get(field):
                    raise InputError(f"fcf_definition missing {field}")
        fcf_difference = (
            calculated_fcf - float(reported_fcf)
            if calculated_fcf is not None and reported_fcf is not None
            and fcf_definition.get("kind") == "analyst_conventional" else None
        )
        fcf_discrepancy = _classify_fcf_discrepancy(calculated_fcf, reported_fcf)

        adjusted_definitions = supplemental.get("adjusted_fcf_definitions")
        if adjusted_definitions is not None and not isinstance(adjusted_definitions, dict):
            raise InputError("adjusted_fcf_definitions must map periods to definitions")
        legacy_definition = supplemental.get("adjusted_fcf_definition")
        if adjusted_definitions is not None:
            adjusted_definition = adjusted_definitions.get(period)
            needs_period_definition = (period not in adjusted_definitions) and (reported_fcf is not None)
        elif legacy_definition is not None and len(periods) == 1:
            adjusted_definition = legacy_definition
            needs_period_definition = False
        else:
            adjusted_definition = None
            needs_period_definition = (legacy_definition is not None) and (reported_fcf is not None)
        adjusted_fcf_bridge = (
            {"missing_period_definition": period, "reconciles": False}
            if needs_period_definition
            else _build_adjusted_fcf_bridge(metrics, adjusted_definition)
        )

        one_time_norm = _apply_one_time_cash_adjustments(
            period,
            reported_cfo,
            calculated_fcf,
            one_time_by_period.get(period) if one_time_by_period else None,
        )
        payout_cov = _compute_shareholder_coverage(
            period,
            calculated_fcf,
            one_time_norm["normalized_fcf"] if one_time_norm else None,
            payouts_by_period.get(period) if payouts_by_period else None,
        )

        adjustment_keys = [metric for metric in adjustment_order if metric in metrics]
        bridges[period] = {
            "net_profit": net_profit,
            "unprovided_standard_metrics": unprovided_standard,
            "adjustments": [
                {
                    "metric": metric,
                    "value": metrics[metric],
                    "source": row_sources[period].get(metric),
                }
                for metric in adjustment_keys
            ],
            "calculated_cfo": _rounded(calculated_cfo),
            "present_items_subtotal": _rounded(subtotal_present),
            "reported_cfo": reported_cfo,
            "cfo_reconciliation_difference": _rounded(cfo_difference),
            "unreconciled_cfo_residual": _rounded(partial_residual),
            "capex": capex,
            "calculated_fcf": _rounded(calculated_fcf),
            "reported_fcf": reported_fcf,
            "fcf_discrepancy": fcf_discrepancy,
            "fcf_basis": {
                "starting_metric": "operating_cash_flow",
                "starting_value": reported_cfo,
                "cash_capex_metric": "capex",
                "cash_capex_value": capex,
                "conventional_definition": "operating_cash_flow - cash_capex",
                "reported_metric_definition": fcf_definition,
            },
            "adjusted_fcf_bridge": adjusted_fcf_bridge,
            "one_time_normalization": one_time_norm,
            "shareholder_payout_coverage": payout_cov,
            "fcf_reconciliation_difference": _rounded(fcf_difference),
            "net_profit_to_cfo_pct": (
                _rounded(float(reported_cfo) / float(net_profit) * 100)
                if reported_cfo is not None and net_profit else None
            ),
            "reconciles": (
                not conflicting_metrics.get(period)
                and cfo_difference is not None and abs(cfo_difference) <= 0.01
                and calculated_fcf is not None
                and (fcf_difference is None or abs(fcf_difference) <= 0.01)
                and (adjusted_fcf_bridge is None or adjusted_fcf_bridge["reconciles"])
            ),
        }

    growth: dict[str, Any] = {}
    current_period = periods[-1]
    prior_period = _prior_year_period(current_period, by_period)
    if prior_period is not None:
        prior_metrics, current_metrics = by_period[prior_period], by_period[current_period]
        for metric in ("revenue", "net_profit", "operating_cash_flow", "free_cash_flow"):
            if metric == "free_cash_flow":
                prior = bridges[prior_period]["calculated_fcf"]
                current = bridges[current_period]["calculated_fcf"]
            else:
                prior, current = prior_metrics.get(metric), current_metrics.get(metric)
            if prior is not None and current is not None:
                growth[metric] = {
                    "prior_period": prior_period,
                    "prior": prior,
                    "current_period": current_period,
                    "current": current,
                    "yoy_pct": _rounded(_pct_change(float(current), float(prior))),
                    "absolute_change": _rounded(float(current) - float(prior)),
                }

    balances = supplemental.get("balances", {})
    balance_growth: dict[str, Any] = {}
    balance_current = (
        max(balances, key=_period_sort_key) if isinstance(balances, dict) and balances else None
    )
    balance_prior = (
        _prior_year_period(balance_current, balances, balance=True) if balance_current else None
    )
    if balance_prior is not None:
        revenue_pct = growth.get("revenue", {}).get("yoy_pct")
        shared_keys = sorted(set(balances[balance_prior]) & set(balances[balance_current]))
        for metric in shared_keys:
            prior = _number(balances[balance_prior][metric], metric)
            current = _number(balances[balance_current][metric], metric)
            yoy_pct = _rounded(_pct_change(float(current), float(prior)))
            entry: dict[str, Any] = {
                "prior_date": balance_prior,
                "prior": prior,
                "current_date": balance_current,
                "current": current,
                "yoy_pct": yoy_pct,
            }
            if (
                (balance_prior, balance_current) == (prior_period, current_period)
                and yoy_pct is not None and revenue_pct is not None
            ):
                entry["growth_minus_revenue_growth_ppt"] = _rounded(yoy_pct - revenue_pct)
            balance_growth[metric] = entry

    conflicts.extend(supplemental.get("conflicts", []))

    return {
        "schema_version": "3.0",
        "entity": metadata["entity"],
        "cashflow_profile": cashflow_profile,
        "applicability": {
            "can_run_standard_cashflow_bridge": True,
            "reason": "standard bridge inputs accepted",
        },
        "currency": metadata["currency"],
        "unit": metadata["unit"],
        "scope": metadata["scope"],
        "input_metadata_complete": all(metadata.values()),
        "periods": periods,
        "inputs": {
            "files": sorted(set(inputs)),
        },
        "bridges": bridges,
        "growth": growth,
        "balance_growth": balance_growth,
        "conflict_register": conflicts,
        "all_bridges_reconcile": all(item["reconciles"] for item in bridges.values()),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Calculate a generic company net-profit-to-CFO-to-FCF bridge and payout coverage."
    )
    parser.add_argument(
        "input_dir",
        nargs="?",
        type=Path,
        help="Directory containing financials.csv and optional supplemental JSON files",
    )
    parser.add_argument(
        "--csv",
        action="append",
        default=[],
        type=Path,
        help="Explicit long-form financial CSV (repeatable)",
    )
    parser.add_argument(
        "--json",
        action="append",
        default=[],
        type=Path,
        help="Explicit financial/supplemental JSON (repeatable)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Write JSON to this file instead of stdout",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        rows, supplemental, inputs = resolve_inputs(args.input_dir, args.csv, args.json)
        report = build_report(rows, supplemental, inputs)
        rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
        return 0
    except (InputError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
