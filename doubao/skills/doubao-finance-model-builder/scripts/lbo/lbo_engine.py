#!/usr/bin/env python3
"""Deterministic LBO return engine using only the Python standard library."""

from __future__ import annotations

import argparse
import copy
import json
import math
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


TOLERANCE = 1e-8
MAX_ITERATIONS = 300
INCOMPLETE_PREFIX = "[INCOMPLETE] "


def _number(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"Expected a number, got {value!r}")
    if not math.isfinite(float(value)):
        raise ValueError(f"Expected a finite number, got {value!r}")
    return float(value)


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _add_years(value: date, years: int) -> date:
    try:
        return value.replace(year=value.year + years)
    except ValueError:
        return value.replace(month=2, day=28, year=value.year + years)


def _xnpv(rate: float, cashflows: Sequence[Tuple[date, float]]) -> float:
    if rate <= -1.0:
        return math.inf
    start = cashflows[0][0]
    return sum(
        amount / ((1.0 + rate) ** ((when - start).days / 365.0))
        for when, amount in cashflows
    )


def xirr(cashflows: Sequence[Tuple[date, float]]) -> Optional[float]:
    """Return XIRR for conventional dated cash flows, or None if no root exists."""
    ordered = sorted(cashflows, key=lambda item: item[0])
    if not ordered or not any(amount < 0 for _, amount in ordered):
        return None
    if not any(amount > 0 for _, amount in ordered):
        return None

    low = -0.999999
    high = 1.0
    low_value = _xnpv(low, ordered)
    high_value = _xnpv(high, ordered)
    while low_value * high_value > 0 and high < 1_000_000:
        high *= 2.0
        high_value = _xnpv(high, ordered)
    if low_value * high_value > 0:
        return None

    for _ in range(250):
        middle = (low + high) / 2.0
        value = _xnpv(middle, ordered)
        if abs(value) < 1e-10:
            return middle
        if low_value * value <= 0:
            high = middle
        else:
            low = middle
            low_value = value
    return (low + high) / 2.0


def calculate_sources_and_uses(case: Dict[str, Any]) -> Dict[str, float]:
    entry = case["entry"]
    uses = {
        "equity_purchase_price": _number(entry.get("equity_purchase_price")),
        "debt_to_refinance": _number(entry.get("debt_to_refinance")),
        "preferred_stock_to_repay": _number(entry.get("preferred_stock_to_repay")),
        "other_debt_like_to_repay": _number(entry.get("other_debt_like_to_repay")),
        "transaction_fees": _number(entry.get("transaction_fees")),
        "financing_fees": _number(entry.get("financing_fees")),
        "minimum_cash": _number(entry.get("minimum_cash")),
    }
    new_debt = sum(_number(item.get("opening_balance")) for item in case["debt_tranches"])
    known_sources = {
        "new_debt": new_debt,
        "target_cash_used": _number(entry.get("target_cash_used")),
        "management_rollover": _number(entry.get("management_rollover")),
    }
    total_uses = sum(uses.values())
    sponsor_equity = total_uses - sum(known_sources.values())
    sources = {**known_sources, "sponsor_equity": sponsor_equity}
    total_sources = sum(sources.values())
    return {
        "uses": uses,
        "sources": sources,
        "total_uses": total_uses,
        "total_sources": total_sources,
        "balance_check": total_sources - total_uses,
        "sponsor_equity": sponsor_equity,
    }


def calculate_entry_valuation(case: Dict[str, Any]) -> Dict[str, float]:
    entry = case["entry"]
    purchase_price = _number(entry.get("equity_purchase_price"))
    debt = _number(entry.get("debt_to_refinance"))
    cash = _number(entry.get("cash_acquired"))
    minority = _number(entry.get("minority_interest"))
    preferred = _number(entry.get("preferred_stock"))
    other = _number(entry.get("other_debt_like"))
    ebitda = _number(entry.get("entry_ebitda"))
    net_debt = debt - cash
    other_adjustments = minority + preferred + other
    enterprise_value = purchase_price + net_debt + other_adjustments
    return {
        "equity_purchase_price": purchase_price,
        "entry_net_debt": net_debt,
        "entry_debt_like_adjustments": other_adjustments,
        "enterprise_value": enterprise_value,
        "entry_ebitda": ebitda,
        "entry_multiple": enterprise_value / ebitda if ebitda > 0 else math.nan,
    }


def validate_case(case: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []

    if not isinstance(case, dict):
        return ["Input must be a JSON object."], warnings
    for key in ("company", "as_of_date", "entry", "debt_tranches", "years", "exit"):
        if key not in case:
            errors.append(f"Missing required top-level field: {key}")
    if errors:
        return errors, warnings

    try:
        _parse_date(case["as_of_date"])
    except (TypeError, ValueError):
        errors.append("as_of_date must use YYYY-MM-DD.")

    company = case.get("company", {})
    if not isinstance(company, dict):
        errors.append("company must be an object.")
        company = {}
    if not company.get("name"):
        errors.append("company.name is required.")
    if company.get("market") not in {"A", "HK", "US"}:
        errors.append("company.market must be A, HK, or US.")
    if not company.get("currency"):
        errors.append("company.currency is required.")

    assumption_ledger = case.get("assumption_ledger")
    required_assumptions = (
        "ebitda_growth",
        "depreciation_amortization",
        "depreciation_tax_shield",
        "capex",
        "working_capital",
        "cash_taxes",
        "refinancing",
    )
    if not isinstance(assumption_ledger, dict):
        errors.append("assumption_ledger is required and must be an object.")
    else:
        for key in required_assumptions:
            value = assumption_ledger.get(key)
            if value is None or (isinstance(value, str) and not value.strip()):
                errors.append(f"assumption_ledger.{key} is required, including explicit zero assumptions.")

    entry = case.get("entry", {})
    if not isinstance(entry, dict):
        errors.append("entry must be an object.")
        entry = {}
    required_entry = ("equity_purchase_price", "debt_to_refinance", "entry_ebitda")
    for key in required_entry:
        if key not in entry:
            errors.append(f"entry.{key} is required.")
    numeric_entry = (
        "equity_purchase_price",
        "debt_to_refinance",
        "cash_acquired",
        "target_cash_used",
        "minimum_cash",
        "minority_interest",
        "preferred_stock",
        "other_debt_like",
        "preferred_stock_to_repay",
        "other_debt_like_to_repay",
        "transaction_fees",
        "financing_fees",
        "management_rollover",
        "entry_ebitda",
    )
    entry_values: Dict[str, Optional[float]] = {}
    for key in numeric_entry:
        try:
            value = _number(entry.get(key))
            entry_values[key] = value
            if value < 0:
                errors.append(f"entry.{key} cannot be negative.")
        except (TypeError, ValueError) as exc:
            entry_values[key] = None
            errors.append(f"entry.{key}: {exc}")
    if entry_values.get("entry_ebitda") is not None and entry_values["entry_ebitda"] <= 0:
        errors.append("entry.entry_ebitda must be positive.")
    if (
        entry_values.get("target_cash_used") is not None
        and entry_values.get("cash_acquired") is not None
        and entry_values["target_cash_used"] > entry_values["cash_acquired"]
    ):
        errors.append("entry.target_cash_used cannot exceed entry.cash_acquired.")

    tranches = case.get("debt_tranches")
    if not isinstance(tranches, list) or not tranches:
        errors.append("debt_tranches must contain at least one tranche.")
    else:
        names = set()
        revolvers = 0
        for index, tranche in enumerate(tranches):
            label = f"debt_tranches[{index}]"
            if not isinstance(tranche, dict):
                errors.append(f"{label} must be an object.")
                continue
            name = tranche.get("name")
            if not name:
                errors.append(f"{label}.name is required.")
            elif name in names:
                errors.append(f"Duplicate debt tranche name: {name}")
            names.add(name)
            tranche_values: Dict[str, Optional[float]] = {}
            for key in (
                "opening_balance",
                "cash_interest_rate",
                "pik_rate",
                "mandatory_amortization_rate",
                "cash_sweep_priority",
                "commitment",
            ):
                try:
                    value = _number(tranche.get(key))
                    tranche_values[key] = value
                    if value < 0:
                        errors.append(f"{label}.{key} cannot be negative.")
                except (TypeError, ValueError) as exc:
                    tranche_values[key] = None
                    errors.append(f"{label}.{key}: {exc}")
            maturity_year = tranche.get("maturity_year")
            if (
                maturity_year is not None
                and (
                    isinstance(maturity_year, bool)
                    or not isinstance(maturity_year, int)
                    or maturity_year < 1
                )
            ):
                errors.append(f"{label}.maturity_year must be a positive integer.")
            for rate_path_key in ("cash_interest_rate_by_year", "pik_rate_by_year"):
                rate_path = tranche.get(rate_path_key, {})
                if not isinstance(rate_path, dict):
                    errors.append(f"{label}.{rate_path_key} must be an object.")
                    continue
                for year_key, rate_value in rate_path.items():
                    try:
                        if int(year_key) < 1 or _number(rate_value) < 0:
                            raise ValueError("year and rate must be non-negative")
                    except (TypeError, ValueError):
                        errors.append(
                            f"{label}.{rate_path_key} contains invalid year or rate."
                        )
            if tranche_values.get("mandatory_amortization_rate") is not None and tranche_values["mandatory_amortization_rate"] > 1:
                errors.append(f"{label}.mandatory_amortization_rate cannot exceed 1.")
            if tranche.get("is_revolver"):
                revolvers += 1
                if (
                    tranche_values.get("commitment") is not None
                    and tranche_values.get("opening_balance") is not None
                    and tranche_values["commitment"] < tranche_values["opening_balance"]
                ):
                    errors.append(f"{label}.commitment cannot be below opening balance.")
        if revolvers > 1:
            errors.append("The current engine supports at most one revolver.")

    years = case.get("years")
    if not isinstance(years, list) or not years:
        errors.append("years must be a non-empty list.")
    else:
        year_numbers = [row.get("year") if isinstance(row, dict) else None for row in years]
        if any(isinstance(value, bool) or not isinstance(value, int) for value in year_numbers):
            errors.append("Each years[].year must be an integer.")
        elif year_numbers != list(range(1, len(year_numbers) + 1)):
            errors.append("years must be continuous and start at 1.")
        for index, row in enumerate(years):
            label = f"years[{index}]"
            if not isinstance(row, dict):
                errors.append(f"{label} must be an object.")
                continue
            row_values: Dict[str, Optional[float]] = {}
            for key in (
                "ebitda",
                "cash_taxes",
                "capex",
                "change_nwc",
                "other_cash_costs",
                "follow_on_equity",
                "sponsor_distribution",
            ):
                try:
                    value = _number(row.get(key))
                    row_values[key] = value
                    if key not in {"change_nwc"} and value < 0:
                        errors.append(f"{label}.{key} cannot be negative.")
                except (TypeError, ValueError) as exc:
                    row_values[key] = None
                    errors.append(f"{label}.{key}: {exc}")
            if row_values.get("ebitda") is not None and row_values["ebitda"] <= 0:
                warnings.append(f"{label}.ebitda is not positive; standard LBO suitability is weak.")

    exit_cfg = case.get("exit", {})
    if not isinstance(exit_cfg, dict):
        errors.append("exit must be an object.")
        exit_cfg = {}
    exit_years = exit_cfg.get("years")
    multiples = exit_cfg.get("multiples")
    if not isinstance(exit_years, list) or not exit_years:
        errors.append("exit.years must be a non-empty list.")
    elif years and all(isinstance(value, int) and not isinstance(value, bool) for value in exit_years):
        max_year = len(years)
        if any(value < 1 or value > max_year for value in exit_years):
            errors.append("Every exit year must be covered by years.")
        if exit_years != sorted(set(exit_years)):
            errors.append("exit.years must be unique and sorted.")
        if exit_years != [3, 4, 5, 6, 7]:
            warnings.append("Recommended default exit years are 3, 4, 5, 6, and 7.")
    else:
        errors.append("exit.years must contain integers.")
    if not isinstance(multiples, list) or not multiples:
        errors.append("exit.multiples must be a non-empty list.")
    else:
        for value in multiples:
            try:
                if _number(value) <= 0:
                    errors.append("All exit multiples must be positive.")
            except (TypeError, ValueError) as exc:
                errors.append(f"exit.multiples: {exc}")
    try:
        exit_fee_rate = _number(exit_cfg.get("exit_fee_rate"))
        if not 0 <= exit_fee_rate < 1:
            errors.append("exit.exit_fee_rate must be between 0 and 1.")
        ownership = exit_cfg.get("sponsor_ownership")
        if ownership is not None and not 0 < _number(ownership) <= 1:
            errors.append("exit.sponsor_ownership must be above 0 and at most 1.")
    except (TypeError, ValueError) as exc:
        errors.append(f"exit configuration: {exc}")

    if not errors:
        sources_uses = calculate_sources_and_uses(case)
        if sources_uses["sponsor_equity"] <= 0:
            errors.append("Calculated sponsor equity must be positive.")
        if abs(sources_uses["balance_check"]) > TOLERANCE:
            errors.append("Sources & Uses does not balance.")
        entry_valuation = calculate_entry_valuation(case)
        if any(_number(value) > entry_valuation["entry_multiple"] + TOLERANCE for value in multiples):
            warnings.append("At least one exit multiple exceeds the entry multiple; do not use it as Base without evidence.")
    provenance = case.get("provenance")
    provenance_issues: List[str] = []
    if not isinstance(provenance, dict):
        provenance_issues.append("provenance must be an object")
    else:
        source_rows = provenance.get("sources")
        field_sources = provenance.get("field_sources")
        source_ids: set[str] = set()
        if not isinstance(source_rows, list) or not source_rows:
            provenance_issues.append("provenance.sources must be a non-empty array")
        else:
            for index, source in enumerate(source_rows):
                source_id = source.get("source_id") if isinstance(source, dict) else None
                if not isinstance(source_id, str) or not source_id.strip():
                    provenance_issues.append(f"provenance.sources[{index}].source_id is required")
                elif source_id.strip() in source_ids:
                    provenance_issues.append(f"duplicate provenance source_id: {source_id.strip()}")
                else:
                    source_ids.add(source_id.strip())
        for group in ("entry", "operating_case", "debt_terms", "exit"):
            raw_ids = field_sources.get(group) if isinstance(field_sources, dict) else None
            ids = [raw_ids] if isinstance(raw_ids, str) else raw_ids
            if not isinstance(ids, list) or not ids or any(not isinstance(item, str) or item not in source_ids for item in ids):
                provenance_issues.append(f"provenance.field_sources.{group} must reference real source IDs")
    if provenance_issues:
        warnings.extend(INCOMPLETE_PREFIX + issue for issue in provenance_issues)
    management_case = case.get("management_case")
    if management_case is None:
        warnings.append("No management_case supplied; add an operating improvement comparison when Base returns are impaired or near the equity cliff.")
    elif not isinstance(management_case, dict):
        errors.append("management_case must be an object.")
    else:
        management_years = management_case.get("years")
        base_year_count = len(years) if isinstance(years, list) else 0
        if not isinstance(management_years, list) or len(management_years) != base_year_count:
            errors.append("management_case.years must cover the same continuous years as the Base case.")
        if isinstance(management_case.get("exit_year"), bool) or not isinstance(management_case.get("exit_year"), int):
            errors.append("management_case.exit_year must be an integer.")
        try:
            if _number(management_case.get("exit_multiple")) <= 0:
                errors.append("management_case.exit_multiple must be positive.")
        except (TypeError, ValueError) as exc:
            errors.append(f"management_case.exit_multiple: {exc}")
    return errors, warnings


def _normalize_tranches(case: Dict[str, Any]) -> List[Dict[str, Any]]:
    normalized = []
    for item in case["debt_tranches"]:
        normalized.append(
            {
                "name": item["name"],
                "opening_balance": _number(item.get("opening_balance")),
                "cash_interest_rate": _number(item.get("cash_interest_rate")),
                "pik_rate": _number(item.get("pik_rate")),
                "mandatory_amortization_rate": _number(item.get("mandatory_amortization_rate")),
                "cash_sweep_priority": _number(item.get("cash_sweep_priority")),
                "is_revolver": bool(item.get("is_revolver")),
                "commitment": _number(item.get("commitment")),
                "maturity_year": item.get("maturity_year"),
                "cash_interest_rate_by_year": {
                    int(key): _number(value)
                    for key, value in item.get("cash_interest_rate_by_year", {}).items()
                },
                "pik_rate_by_year": {
                    int(key): _number(value)
                    for key, value in item.get("pik_rate_by_year", {}).items()
                },
            }
        )
    return normalized


def _tranche_rate(tranche: Dict[str, Any], field: str, year: int) -> float:
    path = tranche.get(f"{field}_by_year", {})
    return path.get(year, tranche[field])


def _simulate_year(
    opening: Dict[str, float],
    tranches: List[Dict[str, Any]],
    row: Dict[str, Any],
    sponsor_ownership: float,
    opening_excess_cash: float,
) -> Dict[str, Any]:
    ending_guess = dict(opening)
    final: Dict[str, Any] = {}
    current_year = int(row["year"])

    for _ in range(MAX_ITERATIONS):
        cash_interest: Dict[str, float] = {}
        pik_interest: Dict[str, float] = {}
        mandatory_due: Dict[str, float] = {}
        balances_before_debt_service: Dict[str, float] = {}

        for tranche in tranches:
            name = tranche["name"]
            cash_rate = _tranche_rate(tranche, "cash_interest_rate", current_year)
            pik_rate = _tranche_rate(tranche, "pik_rate", current_year)
            cash_interest[name] = max(0.0, opening[name]) * cash_rate
            pik_interest[name] = max(0.0, opening[name]) * pik_rate
            scheduled_mandatory = min(
                opening[name] + pik_interest[name],
                opening[name] * tranche["mandatory_amortization_rate"],
            )
            if (
                tranche.get("maturity_year") is not None
                and current_year >= tranche["maturity_year"]
            ):
                mandatory_due[name] = opening[name] + pik_interest[name]
            else:
                mandatory_due[name] = scheduled_mandatory
            balances_before_debt_service[name] = max(
                0.0, opening[name] + pik_interest[name]
            )

        total_cash_interest = sum(cash_interest.values())
        total_pik_interest = sum(pik_interest.values())
        total_mandatory_due = sum(mandatory_due.values())
        follow_on_sponsor = _number(row.get("follow_on_equity"))
        total_follow_on = follow_on_sponsor / sponsor_ownership
        cash_before_debt = (
            _number(row.get("ebitda"))
            - _number(row.get("cash_taxes"))
            - _number(row.get("capex"))
            - _number(row.get("change_nwc"))
            - _number(row.get("other_cash_costs"))
            - total_cash_interest
            + total_follow_on
        )
        available_cash = opening_excess_cash + cash_before_debt

        sweep = {tranche["name"]: 0.0 for tranche in tranches}
        revolver_draw = {tranche["name"]: 0.0 for tranche in tranches}
        mandatory_paid = {tranche["name"]: 0.0 for tranche in tranches}
        ending = dict(balances_before_debt_service)

        revolver = next(
            (
                item
                for item in tranches
                if item["is_revolver"]
                and (
                    item.get("maturity_year") is None
                    or current_year < item["maturity_year"]
                )
            ),
            None,
        )
        draw_need = max(0.0, total_mandatory_due - available_cash)
        if revolver:
            name = revolver["name"]
            capacity = max(
                0.0, revolver["commitment"] - balances_before_debt_service[name]
            )
            draw = min(draw_need, capacity)
            revolver_draw[name] = draw
            ending[name] += draw
            available_cash += draw

        operating_cash_shortfall = max(0.0, -available_cash)
        cash_for_mandatory = max(0.0, available_cash)
        mandatory_order = sorted(
            tranches,
            key=lambda item: (
                0
                if item.get("maturity_year") is not None
                and current_year >= item["maturity_year"]
                else 1,
                item["cash_sweep_priority"],
            ),
        )
        for tranche in mandatory_order:
            name = tranche["name"]
            payment = min(mandatory_due[name], cash_for_mandatory)
            mandatory_paid[name] = payment
            ending[name] -= payment
            cash_for_mandatory -= payment

        total_mandatory_paid = sum(mandatory_paid.values())
        unpaid_mandatory = total_mandatory_due - total_mandatory_paid
        liquidity_shortfall = operating_cash_shortfall + unpaid_mandatory
        remaining = max(0.0, available_cash - total_mandatory_paid)
        for tranche in sorted(tranches, key=lambda item: item["cash_sweep_priority"]):
            name = tranche["name"]
            repayment = min(remaining, ending[name])
            sweep[name] = repayment
            ending[name] -= repayment
            remaining -= repayment
        ending_excess_cash = remaining

        requested_sponsor_distribution = _number(row.get("sponsor_distribution"))
        requested_total_distribution = requested_sponsor_distribution / sponsor_ownership
        realized_total_distribution = min(
            requested_total_distribution, ending_excess_cash
        )
        realized_sponsor_distribution = (
            realized_total_distribution * sponsor_ownership
        )
        distribution_shortfall = (
            requested_sponsor_distribution - realized_sponsor_distribution
        )
        ending_excess_cash -= realized_total_distribution

        difference = max(abs(ending[name] - ending_guess[name]) for name in ending)
        ending_guess = {
            name: (ending_guess[name] + ending[name]) / 2.0 for name in ending
        }
        final = {
            "cash_interest_by_tranche": cash_interest,
            "pik_interest_by_tranche": pik_interest,
            "cash_interest_rate_by_tranche": {
                item["name"]: _tranche_rate(
                    item, "cash_interest_rate", current_year
                )
                for item in tranches
            },
            "pik_rate_by_tranche": {
                item["name"]: _tranche_rate(item, "pik_rate", current_year)
                for item in tranches
            },
            "mandatory_due_by_tranche": mandatory_due,
            "mandatory_by_tranche": mandatory_paid,
            "sweep_by_tranche": sweep,
            "revolver_draw_by_tranche": revolver_draw,
            "ending_balances": ending,
            "cash_interest": total_cash_interest,
            "pik_interest": total_pik_interest,
            "mandatory_due": total_mandatory_due,
            "mandatory_amortization": total_mandatory_paid,
            "unpaid_mandatory": unpaid_mandatory,
            "cash_before_debt_service": cash_before_debt,
            "cash_sweep": sum(sweep.values()),
            "revolver_draw": sum(revolver_draw.values()),
            "liquidity_shortfall": liquidity_shortfall,
            "distribution_shortfall": distribution_shortfall,
            "realized_sponsor_distribution": realized_sponsor_distribution,
            "ending_excess_cash": ending_excess_cash,
        }
        if difference < TOLERANCE:
            break
    else:
        raise RuntimeError("Debt and interest iteration did not converge.")
    return final


def _build_cashflows(
    as_of: date,
    sponsor_equity: float,
    years: Sequence[Dict[str, Any]],
    exit_year: int,
    exit_sponsor_proceeds: float,
) -> List[Tuple[date, float]]:
    flows: List[Tuple[date, float]] = [(as_of, -sponsor_equity)]
    for row in years:
        year = int(row["year"])
        if year > exit_year:
            break
        amount = _number(
            row.get("realized_sponsor_distribution", row.get("sponsor_distribution"))
        ) - _number(row.get("follow_on_equity"))
        if year == exit_year:
            amount += exit_sponsor_proceeds
        if abs(amount) > TOLERANCE:
            flows.append((_add_years(as_of, year), amount))
    return flows


def run_case(case: Dict[str, Any]) -> Dict[str, Any]:
    errors, warnings = validate_case(case)
    if errors:
        raise ValueError("Invalid case:\n- " + "\n- ".join(errors))

    sources_uses = calculate_sources_and_uses(case)
    entry_valuation = calculate_entry_valuation(case)
    entry = case["entry"]
    exit_cfg = case["exit"]
    sponsor_equity = sources_uses["sponsor_equity"]
    rollover = _number(entry.get("management_rollover"))
    ownership_override = exit_cfg.get("sponsor_ownership")
    sponsor_ownership = (
        _number(ownership_override)
        if ownership_override is not None
        else sponsor_equity / (sponsor_equity + rollover)
    )

    tranches = _normalize_tranches(case)
    opening = {item["name"]: item["opening_balance"] for item in tranches}
    excess_cash = 0.0
    schedule: List[Dict[str, Any]] = []
    for row in case["years"]:
        simulated = _simulate_year(
            opening, tranches, row, sponsor_ownership, excess_cash
        )
        ending_debt = sum(simulated["ending_balances"].values())
        cash_balance = _number(entry.get("minimum_cash")) + simulated["ending_excess_cash"]
        schedule_row = {
            "year": int(row["year"]),
            "ebitda": _number(row.get("ebitda")),
            "cash_taxes": _number(row.get("cash_taxes")),
            "capex": _number(row.get("capex")),
            "change_nwc": _number(row.get("change_nwc")),
            "other_cash_costs": _number(row.get("other_cash_costs")),
            "follow_on_equity": _number(row.get("follow_on_equity")),
            "requested_sponsor_distribution": _number(row.get("sponsor_distribution")),
            **simulated,
            "sponsor_distribution": simulated["realized_sponsor_distribution"],
            "ending_debt": ending_debt,
            "ending_cash": cash_balance,
            "ending_net_debt": ending_debt - cash_balance,
        }
        schedule.append(schedule_row)
        opening = simulated["ending_balances"]
        excess_cash = simulated["ending_excess_cash"]

    as_of = _parse_date(case["as_of_date"])
    exit_fee_rate = _number(exit_cfg.get("exit_fee_rate"))
    exit_debt_like = _number(
        exit_cfg.get(
            "exit_debt_like_adjustments",
            entry_valuation["entry_debt_like_adjustments"],
        )
    )
    exit_results: List[Dict[str, Any]] = []
    return_bridges: List[Dict[str, Any]] = []
    target_diagnostics: List[Dict[str, Any]] = []
    year_lookup = {row["year"]: row for row in schedule}
    operating_lookup = {int(row["year"]): row for row in case["years"]}

    for exit_year in exit_cfg["years"]:
        schedule_row = year_lookup[exit_year]
        operating_row = operating_lookup[exit_year]
        exit_ebitda = _number(operating_row.get("ebitda"))
        for exit_multiple_raw in exit_cfg["multiples"]:
            exit_multiple = _number(exit_multiple_raw)
            enterprise_value = exit_ebitda * exit_multiple
            exit_fee = enterprise_value * exit_fee_rate
            raw_equity_value = (
                enterprise_value
                - schedule_row["ending_net_debt"]
                - exit_debt_like
                - exit_fee
            )
            equity_value = max(0.0, raw_equity_value)
            sponsor_exit_proceeds = equity_value * sponsor_ownership
            cashflows = _build_cashflows(
                as_of,
                sponsor_equity,
                schedule,
                exit_year,
                sponsor_exit_proceeds,
            )
            total_invested = -sum(amount for _, amount in cashflows if amount < 0)
            total_proceeds = sum(amount for _, amount in cashflows if amount > 0)
            profit = total_proceeds - total_invested
            moic = total_proceeds / total_invested if total_invested > 0 else None
            calculated_xirr = xirr(cashflows)

            result = {
                "exit_year": exit_year,
                "exit_multiple": exit_multiple,
                "exit_ebitda": exit_ebitda,
                "enterprise_value": enterprise_value,
                "ending_debt": schedule_row["ending_debt"],
                "ending_cash": schedule_row["ending_cash"],
                "ending_net_debt": schedule_row["ending_net_debt"],
                "exit_debt_like_adjustments": exit_debt_like,
                "exit_fee": exit_fee,
                "raw_equity_value": raw_equity_value,
                "equity_value": equity_value,
                "sponsor_ownership": sponsor_ownership,
                "sponsor_exit_proceeds": sponsor_exit_proceeds,
                "total_invested": total_invested,
                "total_proceeds": total_proceeds,
                "profit": profit,
                "moic": moic,
                "xirr": calculated_xirr,
                "cashflows": [
                    {"date": when.isoformat(), "amount": amount}
                    for when, amount in cashflows
                ],
            }
            exit_results.append(result)

            ebitda_growth = (
                exit_ebitda - entry_valuation["entry_ebitda"]
            ) * entry_valuation["entry_multiple"]
            multiple_change = exit_ebitda * (
                exit_multiple - entry_valuation["entry_multiple"]
            )
            net_debt_paydown = (
                entry_valuation["entry_net_debt"] - schedule_row["ending_net_debt"]
            )
            debt_like_change = (
                entry_valuation["entry_debt_like_adjustments"] - exit_debt_like
            )
            expected_raw_equity = (
                entry_valuation["equity_purchase_price"]
                + ebitda_growth
                + multiple_change
                + net_debt_paydown
                + debt_like_change
                - exit_fee
            )
            equity_change = raw_equity_value - entry_valuation["equity_purchase_price"]
            contributions = {
                "ebitda_growth": ebitda_growth,
                "multiple_change": multiple_change,
                "net_debt_paydown": net_debt_paydown,
                "debt_like_change": debt_like_change,
                "exit_fee": -exit_fee,
            }
            contribution_pct = {
                key: (value / equity_change if abs(equity_change) > TOLERANCE else None)
                for key, value in contributions.items()
            }
            return_bridges.append(
                {
                    "exit_year": exit_year,
                    "exit_multiple": exit_multiple,
                    "starting_equity_purchase_price": entry_valuation["equity_purchase_price"],
                    "ebitda_growth_contribution": ebitda_growth,
                    "multiple_change_contribution": multiple_change,
                    "net_debt_paydown_contribution": net_debt_paydown,
                    "debt_like_change_contribution": debt_like_change,
                    "exit_fee_contribution": -exit_fee,
                    "equity_value_change": equity_change,
                    "contribution_pct_of_equity_change": contribution_pct,
                    "expected_raw_equity_value": expected_raw_equity,
                    "actual_raw_equity_value": raw_equity_value,
                    "reconciliation_difference": raw_equity_value - expected_raw_equity,
                }
            )

            pre_exit_flows = _build_cashflows(
                as_of, sponsor_equity, schedule, exit_year, 0.0
            )
            exit_date = _add_years(as_of, exit_year)
            for target_raw in case.get("target_irrs", [0.20, 0.25, 0.30]):
                target = _number(target_raw)
                if target <= -1:
                    continue
                future_flows = pre_exit_flows[1:]
                pv_future_before_exit = sum(
                    amount
                    / ((1.0 + target) ** ((when - as_of).days / 365.0))
                    for when, amount in future_flows
                )
                discount_factor = (1.0 + target) ** (
                    (exit_date - as_of).days / 365.0
                )
                required_sponsor_exit = max(
                    0.0, (sponsor_equity - pv_future_before_exit) * discount_factor
                )
                required_total_equity = required_sponsor_exit / sponsor_ownership
                denominator_multiple = exit_ebitda * (1.0 - exit_fee_rate)
                required_exit_multiple = (
                    required_total_equity
                    + schedule_row["ending_net_debt"]
                    + exit_debt_like
                ) / denominator_multiple
                denominator_ebitda = exit_multiple * (1.0 - exit_fee_rate)
                required_exit_ebitda = (
                    required_total_equity
                    + schedule_row["ending_net_debt"]
                    + exit_debt_like
                ) / denominator_ebitda

                all_future_flows = list(future_flows)
                all_future_flows.append((exit_date, sponsor_exit_proceeds))
                pv_all_future = sum(
                    amount
                    / ((1.0 + target) ** ((when - as_of).days / 365.0))
                    for when, amount in all_future_flows
                )
                max_purchase_price = (
                    entry_valuation["equity_purchase_price"]
                    + pv_all_future
                    - sponsor_equity
                )
                target_diagnostics.append(
                    {
                        "exit_year": exit_year,
                        "exit_multiple": exit_multiple,
                        "target_irr": target,
                        "required_sponsor_exit_proceeds": required_sponsor_exit,
                        "required_exit_multiple": required_exit_multiple,
                        "required_exit_ebitda": required_exit_ebitda,
                        "max_equity_purchase_price_holding_ownership_constant": max_purchase_price,
                    }
                )

    additional_warnings = list(warnings)
    for row in schedule:
        if row["liquidity_shortfall"] > TOLERANCE:
            additional_warnings.append(
                f"Year {row['year']} has liquidity shortfall of {row['liquidity_shortfall']:.6f}."
            )
        if row["distribution_shortfall"] > TOLERANCE:
            additional_warnings.append(
                f"Year {row['year']} requested sponsor distribution exceeds available excess cash; returns use the funded amount only."
            )
    for bridge in return_bridges:
        if abs(bridge["reconciliation_difference"]) > 1e-6:
            additional_warnings.append(
                "At least one return bridge does not reconcile; inspect valuation inputs."
            )
            break

    output = {
        "company": copy.deepcopy(case["company"]),
        "as_of_date": case["as_of_date"],
        "validation_errors": [],
        "warnings": additional_warnings,
        "sources_and_uses": sources_uses,
        "entry_valuation": entry_valuation,
        "sponsor_ownership": sponsor_ownership,
        "annual_debt_schedule": schedule,
        "exit_results": exit_results,
        "return_bridge": return_bridges,
        "target_irr_diagnostics": target_diagnostics,
        "assumption_ledger": copy.deepcopy(case.get("assumption_ledger", {})),
        "methodology_notes": [
            "Cash and PIK interest use opening debt balances so the deterministic engine and non-circular Excel model share one auditable convention.",
            "PIK interest capitalizes into debt principal.",
            "Positive cash sweeps debt by priority; residual cash accumulates above minimum cash.",
            "XIRR uses actual anniversary dates and a 365-day basis.",
            "Maximum purchase price diagnostics hold sponsor ownership and all non-price assumptions constant.",
        ],
    }

    management_case = case.get("management_case")
    if isinstance(management_case, dict):
        alternative = copy.deepcopy(case)
        alternative.pop("management_case", None)
        alternative["years"] = copy.deepcopy(management_case["years"])
        alternative["exit"] = copy.deepcopy(case["exit"])
        alternative["exit"]["years"] = [int(management_case["exit_year"])]
        alternative["exit"]["multiples"] = [_number(management_case["exit_multiple"])]
        alternative_result = run_case(alternative)
        alt_exit = alternative_result["exit_results"][0]
        base_exit = next(
            (
                item for item in exit_results
                if item["exit_year"] == int(management_case["exit_year"])
                and abs(item["exit_multiple"] - _number(management_case["exit_multiple"])) <= TOLERANCE
            ),
            None,
        )
        if base_exit is None:
            raise RuntimeError("Management comparison exit year/multiple is not covered by the Base result grid.")
        output["management_case_comparison"] = {
            "name": management_case.get("name", "经营改善情景"),
            "exit_year": alt_exit["exit_year"],
            "exit_multiple": alt_exit["exit_multiple"],
            "base": {
                "exit_ebitda": base_exit["exit_ebitda"],
                "enterprise_value": base_exit["enterprise_value"],
                "equity_value": base_exit["equity_value"],
                "moic": base_exit["moic"],
                "xirr": base_exit["xirr"],
            },
            "management": {
                "exit_ebitda": alt_exit["exit_ebitda"],
                "enterprise_value": alt_exit["enterprise_value"],
                "equity_value": alt_exit["equity_value"],
                "moic": alt_exit["moic"],
                "xirr": alt_exit["xirr"],
            },
            "delta": {
                "enterprise_value": alt_exit["enterprise_value"] - base_exit["enterprise_value"],
                "equity_value": alt_exit["equity_value"] - base_exit["equity_value"],
                "moic": None if alt_exit["moic"] is None or base_exit["moic"] is None else alt_exit["moic"] - base_exit["moic"],
                "xirr": None if alt_exit["xirr"] is None or base_exit["xirr"] is None else alt_exit["xirr"] - base_exit["xirr"],
            },
        }
    incomplete_reasons = sorted({
        warning[len(INCOMPLETE_PREFIX):]
        for warning in additional_warnings
        if warning.startswith(INCOMPLETE_PREFIX)
    })
    fail_reasons: List[str] = []
    if any(abs(item["reconciliation_difference"]) > 1e-6 for item in return_bridges):
        fail_reasons.append("回报归因桥无法勾稽")
    exit_years = sorted({int(item["exit_year"]) for item in exit_results})
    exit_multiples = sorted({float(item["exit_multiple"]) for item in exit_results})
    base_year = 5 if 5 in exit_years else exit_years[len(exit_years) // 2]
    base_multiple = exit_multiples[len(exit_multiples) // 2]
    base_exit = next(item for item in exit_results if item["exit_year"] == base_year and abs(item["exit_multiple"] - base_multiple) <= TOLERANCE)
    impaired = (
        base_exit["moic"] is None
        or base_exit["moic"] < 1.0
        or base_exit["xirr"] is None
        or base_exit["xirr"] < 0
        or base_exit["equity_value"] <= 0.1 * entry_valuation["equity_purchase_price"]
    )
    if impaired and "management_case_comparison" not in output:
        incomplete_reasons.append("基准回报受损或接近股权归零，但未提供经营改善量化情景")
    status = "FAIL" if fail_reasons else ("INCOMPLETE" if incomplete_reasons else "PASS")
    output["model_status_code"] = status
    output["model_status"] = {"PASS": "通过", "INCOMPLETE": "未完成", "FAIL": "失败"}[status]
    output["blocking_issues"] = fail_reasons + sorted(set(incomplete_reasons))
    return output


def _read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    parser = argparse.ArgumentParser(description="Calculate deterministic LBO returns.")
    parser.add_argument("case", type=Path, help="Input case JSON.")
    parser.add_argument("--output", type=Path, help="Optional result JSON path.")
    args = parser.parse_args()

    case = _read_json(args.case)
    try:
        result = run_case(case)
    except (TypeError, ValueError, RuntimeError) as exc:
        parser.error(str(exc))
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
