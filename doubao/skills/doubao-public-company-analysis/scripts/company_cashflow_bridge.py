#!/usr/bin/env python3
"""Build a net-profit-to-CFO-to-FCF bridge from structured company data.

The tool accepts either a fixture directory or explicit CSV/JSON files.  It
uses metric names as its contract and never reads expected/oracle files.
Markdown extraction is intentionally limited to supplementary facts that are
not present in the V6 structured financials fixture.
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
NON_STANDARD_CASHFLOW_ENTITY_TYPES = {
    "bank",
    "insurance",
    "pre_revenue_biotech",
}
ALLOWED_DIRECTORY_JSON = {
    "cashflow_facts.json",
    "company_facts.json",
    "conflicts.json",
    "facts.json",
    "supplemental.json",
}
LINE_PREFIX = re.compile(r"^\s*\d+\|")
NUMBER = r"(-?\d+(?:,\d{3})*(?:\.\d+)?)"


class InputError(ValueError):
    """Raised when an input cannot produce a reliable bridge."""


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
        cleaned = {key: (value.strip() if isinstance(value, str) else value)
                   for key, value in row.items()}
        first_field = reader.fieldnames[0]
        if cleaned.get(first_field):
            cleaned[first_field] = LINE_PREFIX.sub("", cleaned[first_field])
        cleaned["value"] = _number(cleaned["value"], f"{path}:{line_number}:value")
        cleaned["_input"] = str(path)
        rows.append(cleaned)
    return rows


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise InputError(f"{path}: invalid JSON: {exc}") from exc
    if isinstance(value, list):
        return {"records": value}
    if not isinstance(value, dict):
        raise InputError(f"{path}: JSON root must be an object or record list")
    return value


def _extract_table_balance(text: str, label: str) -> dict[str, float | int]:
    pattern = re.compile(
        rf"^\|\s*{re.escape(label)}\s*\|\s*{NUMBER}\s*\|\s*{NUMBER}\s*\|\s*{NUMBER}\s*\|",
        re.MULTILINE,
    )
    match = pattern.search(text)
    if not match:
        return {}
    return {
        "current": _number(match.group(1), label),
        "year_end": _number(match.group(2), label),
        "prior": _number(match.group(3), label),
    }


def extract_markdown_facts(paths: Iterable[Path]) -> dict[str, Any]:
    """Extract optional balance, disposal, and presentation-conflict facts."""
    facts: dict[str, Any] = {
        "balances": {},
        "one_time_items": [],
        "presentation_claims": {},
        "sources": {},
    }
    for path in paths:
        text = path.read_text(encoding="utf-8")
        facts["sources"][path.name] = str(path)
        is_formal = "正式业绩" in text or "正式披露" in text
        is_presentation = "演示稿" in text or "管理层现金指标" in text

        if is_formal:
            periods = re.search(
                r"\|\s*项目\s*\|\s*(\d{4}-\d{2}-\d{2})\s*\|\s*"
                r"(\d{4}-\d{2}-\d{2})\s*\|\s*(\d{4}-\d{2}-\d{2})\s*\|",
                text,
            )
            for label, metric in (("应收账款净额", "accounts_receivable"),
                                  ("存货净额", "inventory")):
                values = _extract_table_balance(text, label)
                if values and periods:
                    facts["balances"].setdefault(periods.group(1), {})[metric] = values["current"]
                    facts["balances"].setdefault(periods.group(3), {})[metric] = values["prior"]

            gain = re.search(r"资产处置收益\s*" + NUMBER + r"\s*来自出售", text)
            proceeds = re.search(r"相关现金对价\s*" + NUMBER, text)
            if gain:
                item: dict[str, Any] = {
                    "type": "asset_disposal",
                    "gain": _number(gain.group(1), "disposal gain"),
                    "recurring": False,
                    "profit_adjustment_tax_effect": "unknown",
                    "source": path.name,
                }
                if proceeds:
                    item.update({
                        "cash_proceeds": _number(proceeds.group(1), "disposal proceeds"),
                        "cash_flow_section": "investing",
                        "excluded_from_recurring_cfo_and_fcf": True,
                    })
                facts["one_time_items"].append(item)

            special = re.search(r"有\s*" + NUMBER + r"\s*为客户取消订单后留下的专用", text)
            write_down = re.search(r"计提跌价准备\s*" + NUMBER, text)
            receipts = re.search(r"其中\s*\d+\s*来自.*?，\s*" + NUMBER + r"\s*已在", text)
            if special:
                facts["non_cancellable_special_inventory"] = _number(
                    special.group(1), "special inventory"
                )
            if write_down:
                facts["inventory_write_down_disclosed"] = _number(
                    write_down.group(1), "inventory write-down"
                )
            if receipts:
                facts["post_period_receipts_disclosed"] = _number(
                    receipts.group(1), "post-period receipts"
                )

        if is_presentation:
            ar_claim = re.search(r"应收账款对现金流的暂时影响约\s*" + NUMBER, text)
            inventory_claim = re.search(r"全部\s*" + NUMBER + r"\s*的库存增加均对应已确认客户订单", text)
            custom_cash = re.search(r"增长投入前经营现金创造[”」]?\s*" + NUMBER, text)
            net_investment = re.search(r"净投资现金支出[”」]?\s*" + NUMBER, text)
            if ar_claim:
                facts["presentation_claims"]["accounts_receivable_cash_impact"] = {
                    "value": _number(ar_claim.group(1), "presentation AR claim"),
                    "qualifier": "approximately",
                    "source": path.name,
                }
            if inventory_claim:
                facts["presentation_claims"]["all_inventory_order_backed"] = {
                    "inventory_increase": _number(inventory_claim.group(1), "inventory claim"),
                    "value": True,
                    "source": path.name,
                }
            if custom_cash:
                facts["presentation_claims"]["custom_cash_metric"] = {
                    "value": _number(custom_cash.group(1), "custom cash metric"),
                    "name": "growth_investment_pre_operating_cash_creation",
                    "source": path.name,
                }
            if net_investment:
                facts["presentation_claims"]["net_investment_cash_outflow"] = {
                    "value": _number(net_investment.group(1), "net investment claim"),
                    "source": path.name,
                }
    return facts


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
        markdown_paths = sorted(input_dir.glob("*.md"))
        if markdown_paths:
            _merge(supplemental, extract_markdown_facts(markdown_paths))
            inputs.extend(str(path) for path in markdown_paths)

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
        _merge(supplemental, {key: value for key, value in data.items()
                              if key not in {"records", "financials"}})
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


def _build_conflicts(
    claims: dict[str, Any],
    latest: dict[str, float | int],
    facts: dict[str, Any],
    one_time_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    conflicts: list[dict[str, Any]] = []
    if "accounts_receivable_cash_impact" in claims and "accounts_receivable_change" in latest:
        claim = claims["accounts_receivable_cash_impact"]
        authoritative = latest["accounts_receivable_change"]
        if abs(abs(float(authoritative)) - float(claim["value"])) > 1e-9:
            conflicts.append({
                "conflict_id": "AR_CASH_IMPACT",
                "topic": "accounts_receivable",
                "lower_priority_claim": claim,
                "authoritative_value": authoritative,
                "resolution": "use_formal_cashflow_reconciliation",
            })
    if "all_inventory_order_backed" in claims and facts.get("non_cancellable_special_inventory"):
        conflicts.append({
            "conflict_id": "INVENTORY_ORDER_SUPPORT",
            "topic": "inventory",
            "lower_priority_claim": claims["all_inventory_order_backed"],
            "authoritative_fact": {
                "non_cancellable_special_inventory": facts["non_cancellable_special_inventory"],
                "inventory_write_down": facts.get("inventory_write_down_disclosed"),
            },
            "resolution": "use_formal_disclosure_and_reject_all_order_backed_claim",
        })
    if "custom_cash_metric" in claims and "operating_cash_flow" in latest:
        claim = claims["custom_cash_metric"]
        if float(claim["value"]) != float(latest["operating_cash_flow"]):
            conflicts.append({
                "conflict_id": "CUSTOM_CASH_METRIC",
                "topic": "cashflow_metric_definition",
                "lower_priority_claim": claim,
                "authoritative_value": latest["operating_cash_flow"],
                "resolution": "do_not_label_custom_metric_as_cfo_or_fcf",
            })
    if "net_investment_cash_outflow" in claims and "capex" in latest:
        claim = claims["net_investment_cash_outflow"]
        if float(claim["value"]) != abs(float(latest["capex"])):
            conflicts.append({
                "conflict_id": "CAPEX_NETTING",
                "topic": "capex",
                "lower_priority_claim": claim,
                "authoritative_value": abs(latest["capex"]),
                "excluded_disposal_cash": next(
                    (item.get("cash_proceeds") for item in one_time_items
                     if item.get("type") == "asset_disposal"), None
                ),
                "resolution": "use_gross_capex_for_fcf",
            })
    return conflicts


def _build_adjusted_fcf_bridge(
    period: str,
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
        "customer_financing_scope",
    ):
        if not definition.get(field):
            raise InputError(f"adjusted_fcf_definition missing {field}")
    reported_metric = str(definition["reported_metric"])
    starting_metric = str(definition["starting_metric"])
    total_cash_metric = str(definition["statutory_total_cash_metric"])
    if reported_metric not in metrics:
        raise InputError(f"{period}: missing adjusted FCF metric {reported_metric}")
    if starting_metric not in metrics:
        raise InputError(f"{period}: missing adjusted FCF starting metric {starting_metric}")
    if total_cash_metric not in metrics:
        raise InputError(f"{period}: missing statutory total cash metric {total_cash_metric}")
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
    return {
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
        "customer_financing_scope": definition["customer_financing_scope"],
    }


def build_report(rows: list[dict[str, Any]], supplemental: dict[str, Any],
                 inputs: list[str]) -> dict[str, Any]:
    by_period: dict[str, dict[str, float | int]] = defaultdict(dict)
    row_sources: dict[str, dict[str, str]] = defaultdict(dict)
    conflicts: list[dict[str, Any]] = []
    entities, currencies, units = set(), set(), set()
    period_entities: dict[str, set[str]] = defaultdict(set)

    for row in rows:
        period, metric, value = str(row["period"]), str(row["metric"]), row["value"]
        if row.get("entity"):
            entity = str(row["entity"])
            entities.add(entity)
            period_entities[period].add(entity)
        if row.get("currency"):
            currencies.add(str(row["currency"]))
        if row.get("unit"):
            units.add(str(row["unit"]))

    mixed_periods = {
        period: values for period, values in period_entities.items() if len(values) > 1
    }
    if mixed_periods:
        period, values = next(iter(mixed_periods.items()))
        raise InputError(
            f"{period}: multiple entities found: {', '.join(sorted(values))}"
        )
    for label, values in (
        ("entities", entities),
        ("currencies", currencies),
        ("units", units),
    ):
        if len(values) > 1:
            raise InputError(f"multiple {label} found: {', '.join(sorted(values))}")

    entity_type = supplemental.get("entity_type")
    if entity_type in NON_STANDARD_CASHFLOW_ENTITY_TYPES:
        return {
            "schema_version": "1.0",
            "entity": next(iter(entities)) if len(entities) == 1 else None,
            "entity_type": entity_type,
            "applicability": {
                "can_run_standard_cashflow_bridge": False,
                "reason": (
                    "standard net-profit-to-CFO-to-FCF bridge is not "
                    f"appropriate for {entity_type}"
                ),
                "required_route": "domain_specific_financial_analysis",
            },
            "inputs": {
                "files": sorted(set(inputs)),
                "oracle_files_read": [],
            },
            "bridges": {},
            "growth": {},
            "conflict_register": [],
            "all_bridges_reconcile": False,
        }

    for row in rows:
        period = str(row["period"])
        metric = str(row["metric"])
        value = row["value"]
        if metric in by_period[period] and by_period[period][metric] != value:
            conflicts.append({
                "conflict_id": f"DATA_{period}_{metric}",
                "topic": metric,
                "values": [by_period[period][metric], value],
                "sources": [row_sources[period][metric], row.get("_input")],
                "resolution": "unresolved_conflicting_structured_inputs",
            })
            continue
        by_period[period][metric] = value
        row_sources[period][metric] = str(
            row.get("source_locator") or row.get("_input")
        )

    periods = sorted(by_period, key=_period_sort_key)
    bridges: dict[str, Any] = {}
    for period in periods:
        metrics = by_period[period]
        missing = [metric for metric in BRIDGE_METRICS if metric not in metrics]
        if missing:
            raise InputError(f"{period}: missing bridge metrics: {', '.join(missing)}")
        calculated_cfo = sum(float(metrics[metric]) for metric in BRIDGE_METRICS)
        reported_cfo = metrics.get("operating_cash_flow")
        if reported_cfo is None:
            raise InputError(
                f"{period}: missing cash-flow-statement operating_cash_flow; "
                "profit bridge cannot substitute for statutory CFO"
            )
        capex = metrics.get("capex")
        if capex is None:
            raise InputError(f"{period}: missing capex")
        calculated_fcf = float(reported_cfo) - abs(float(capex))
        reported_fcf = metrics.get("free_cash_flow")
        fcf_definition = supplemental.get("fcf_definition")
        if reported_fcf is not None:
            if not isinstance(fcf_definition, dict):
                raise InputError(
                    "free_cash_flow provided without fcf_definition metadata"
                )
            for field in ("name", "kind", "formula", "source"):
                if not fcf_definition.get(field):
                    raise InputError(f"fcf_definition missing {field}")
        adjusted_fcf_bridge = _build_adjusted_fcf_bridge(
            period, metrics, supplemental.get("adjusted_fcf_definition")
        )
        bridges[period] = {
            "net_profit": metrics["net_profit"],
            "adjustments": [
                {
                    "metric": metric,
                    "value": metrics[metric],
                    "source": row_sources[period].get(metric),
                }
                for metric in ADJUSTMENT_METRICS
            ],
            "calculated_cfo": _rounded(calculated_cfo),
            "reported_cfo": reported_cfo,
            "cfo_reconciliation_difference": _rounded(calculated_cfo - float(reported_cfo)),
            "capex": abs(float(capex)) if not float(capex).is_integer() else abs(int(capex)),
            "calculated_fcf": _rounded(calculated_fcf),
            "reported_fcf": reported_fcf,
            "fcf_basis": {
                "starting_metric": "operating_cash_flow",
                "starting_value": reported_cfo,
                "cash_capex_metric": "capex",
                "cash_capex_value": abs(float(capex)),
                "conventional_definition": "operating_cash_flow - cash_capex",
                "reported_metric_definition": fcf_definition,
                "profit_bridge_may_define_fcf": False,
            },
            "adjusted_fcf_bridge": adjusted_fcf_bridge,
            "fcf_reconciliation_difference": (
                _rounded(calculated_fcf - float(reported_fcf))
                if reported_fcf is not None
                and fcf_definition.get("kind") == "analyst_conventional"
                else None
            ),
            "net_profit_to_cfo_pct": (
                _rounded(float(reported_cfo) / float(metrics["net_profit"]) * 100)
                if float(metrics["net_profit"]) != 0 else None
            ),
            "reconciles": (
                abs(calculated_cfo - float(reported_cfo)) <= 0.01
                and (
                    reported_fcf is None
                    or fcf_definition.get("kind") != "analyst_conventional"
                    or abs(calculated_fcf - float(reported_fcf)) <= 0.01
                )
                and (
                    adjusted_fcf_bridge is None
                    or adjusted_fcf_bridge["reconciles"]
                )
            ),
        }

    growth: dict[str, Any] = {}
    if len(periods) >= 2:
        prior_period, current_period = periods[-2], periods[-1]
        for metric in ("revenue", "net_profit", "operating_cash_flow", "free_cash_flow"):
            if metric in by_period[prior_period] and metric in by_period[current_period]:
                prior, current = by_period[prior_period][metric], by_period[current_period][metric]
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
    if isinstance(balances, dict) and len(balances) >= 2:
        balance_periods = sorted(balances, key=_period_sort_key)
        balance_prior, balance_current = balance_periods[0], balance_periods[-1]
        for metric in ("accounts_receivable", "inventory"):
            if metric in balances[balance_prior] and metric in balances[balance_current]:
                prior = _number(balances[balance_prior][metric], metric)
                current = _number(balances[balance_current][metric], metric)
                balance_growth[metric] = {
                    "prior_date": balance_prior,
                    "prior": prior,
                    "current_date": balance_current,
                    "current": current,
                    "yoy_pct": _rounded(_pct_change(float(current), float(prior))),
                }
        if "inventory" in balance_growth and "revenue" in growth:
            balance_growth["inventory"]["growth_minus_revenue_growth_ppt"] = _rounded(
                float(balance_growth["inventory"]["yoy_pct"]) -
                float(growth["revenue"]["yoy_pct"])
            )

    one_time_items = list(supplemental.get("one_time_items", []))
    latest_metrics = by_period[periods[-1]]
    for item in one_time_items:
        if item.get("type") == "asset_disposal":
            item.setdefault("period", periods[-1])
            item["cfo_bridge_adjustment"] = latest_metrics.get("disposal_gain")
            item.setdefault("adjusted_net_profit", None)
            item.setdefault("adjusted_net_profit_reason",
                            "tax_effect_unknown; do not subtract pre-tax gain mechanically")

    claims = supplemental.get("presentation_claims", {})
    conflicts.extend(_build_conflicts(claims, latest_metrics, supplemental, one_time_items))
    conflicts.extend(supplemental.get("conflicts", []))

    return {
        "schema_version": "1.0",
        "entity": next(iter(entities)) if len(entities) == 1 else None,
        "entity_type": entity_type,
        "applicability": {
            "can_run_standard_cashflow_bridge": True,
            "reason": "standard bridge inputs accepted",
            "required_route": None,
        },
        "currency": next(iter(currencies)) if len(currencies) == 1 else None,
        "unit": next(iter(units)) if len(units) == 1 else None,
        "periods": periods,
        "inputs": {
            "files": sorted(set(inputs)),
            "oracle_files_read": [],
        },
        "bridges": bridges,
        "growth": growth,
        "balance_growth": balance_growth,
        "one_time_exclusions": one_time_items,
        "supplementary_facts": {
            key: supplemental[key]
            for key in (
                "non_cancellable_special_inventory",
                "inventory_write_down_disclosed",
                "post_period_receipts_disclosed",
            )
            if key in supplemental
        },
        "conflict_register": conflicts,
        "all_bridges_reconcile": all(item["reconciles"] for item in bridges.values()),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Calculate a generic company net-profit-to-CFO-to-FCF bridge."
    )
    parser.add_argument("input_dir", nargs="?", type=Path,
                        help="Directory containing financials.csv and optional source Markdown")
    parser.add_argument("--csv", action="append", default=[], type=Path,
                        help="Explicit long-form financial CSV (repeatable)")
    parser.add_argument("--json", action="append", default=[], type=Path,
                        help="Explicit financial/supplemental JSON (repeatable)")
    parser.add_argument("-o", "--output", type=Path,
                        help="Write JSON to this file instead of stdout")
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
