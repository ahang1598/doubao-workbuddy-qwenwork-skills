#!/usr/bin/env python3
"""Validate normalized comps data and calculate auditable valuation outputs.

The script standardizes share count, dividend-adjusted book value and EV,
calculates trading multiples and Core statistics, and produces reverse-implied
fundamentals and sensitivity tables. Peer classification, metric routing and
premium/discount remain documented analytical judgments.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import date
from pathlib import Path
from typing import Any


CLASSIFICATIONS = {"Target", "Core", "Secondary", "Excluded"}
DATA_QUALITY = {"Pass", "Limited", "Fail"}
DATA_TIERS = {"A", "B", "C", "D"}
OUTPUT_MODES = {"decision-brief", "full-report", "audit-pack"}
PEER_ROLES = {
    "Commercial Core",
    "Stage Core",
    "Mature Boundary",
    "Pipeline/Model Boundary",
    "Global/Scale Boundary",
    "Excluded",
}
EV_METRICS = {
    "ltm_ev_revenue": "ltm_revenue",
    "ntm_ev_revenue": "ntm_revenue",
    "ltm_ev_ebitda": "ltm_ebitda",
    "ntm_ev_ebitda": "ntm_ebitda",
}
PE_METRICS = {"ltm_pe": "ltm_net_income", "ntm_pe": "ntm_net_income"}
PS_METRICS = {"ltm_ps": "ltm_revenue", "ntm_ps": "ntm_revenue"}
FCF_YIELD_METRICS = {"ltm_fcf_yield": "ltm_fcf", "ntm_fcf_yield": "ntm_fcf"}
BOOK_METRICS = {"price_to_book": "adjusted_bvps"}
REFERENCE_METRICS = {"ltm_roe"}
ALL_METRICS = (
    tuple(EV_METRICS)
    + tuple(PE_METRICS)
    + tuple(PS_METRICS)
    + tuple(FCF_YIELD_METRICS)
    + tuple(BOOK_METRICS)
    + tuple(REFERENCE_METRICS)
)
VALUATION_METRICS = (
    set(EV_METRICS)
    | set(PE_METRICS)
    | set(PS_METRICS)
    | set(FCF_YIELD_METRICS)
    | set(BOOK_METRICS)
)
FINANCIAL_FIELDS = {
    "ltm_revenue",
    "ntm_revenue",
    "ltm_ebitda",
    "ntm_ebitda",
    "ltm_net_income",
    "ntm_net_income",
    "ltm_fcf",
    "ntm_fcf",
}
EV_BRIDGE_FIELDS = {
    "debt",
    "cash",
    "preferred_equity",
    "noncontrolling_interest",
    "debt_like_adjustments",
    "non_operating_investments",
}
SHARE_ADD_FIELDS = {
    "incremental_options",
    "unvested_rsus",
    "performance_shares",
    "convertible_incremental_shares",
    "other_dilution",
    "settled_issuance_shares",
}
SHARE_SUB_FIELDS = {"settled_buyback_shares"}
PEER_SCORE_WEIGHTS = {
    "business_overlap": 0.35,
    "business_model": 0.25,
    "revenue_structure": 0.25,
    "market_cap_band": 0.15,
}
METRIC_LABELS_CN = {
    "ltm_ev_revenue": "最近十二个月企业价值/营业收入倍数（LTM EV/Revenue）",
    "ntm_ev_revenue": "未来十二个月企业价值/营业收入倍数（NTM EV/Revenue）",
    "ltm_ev_ebitda": "最近十二个月企业价值/息税折旧摊销前利润倍数（LTM EV/EBITDA）",
    "ntm_ev_ebitda": "未来十二个月企业价值/息税折旧摊销前利润倍数（NTM EV/EBITDA）",
    "ltm_pe": "最近十二个月市盈率（LTM P/E）",
    "ntm_pe": "未来十二个月市盈率（NTM P/E）",
    "ltm_ps": "最近十二个月市销率（LTM P/S）",
    "ntm_ps": "未来十二个月市销率（NTM P/S）",
    "ltm_fcf_yield": "最近十二个月自由现金流收益率（LTM FCF Yield）",
    "ntm_fcf_yield": "未来十二个月自由现金流收益率（NTM FCF Yield）",
    "price_to_book": "市净率（P/B）",
    "ltm_roe": "最近十二个月净资产收益率（LTM ROE）",
}


class InputError(ValueError):
    """Raised when normalized input cannot be calculated safely."""


def parse_date(value: Any, field: str, ticker: str | None = None) -> date:
    label = f"{ticker}.{field}" if ticker else field
    if not isinstance(value, str):
        raise InputError(f"{label} must be an ISO date string (YYYY-MM-DD)")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise InputError(f"{label} must be an ISO date string (YYYY-MM-DD)") from exc


def number(value: Any, field: str, ticker: str, *, required: bool = False) -> float | None:
    if value is None:
        if required:
            raise InputError(f"{ticker}.{field} is required")
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InputError(f"{ticker}.{field} must be numeric or null")
    result = float(value)
    if not math.isfinite(result):
        raise InputError(f"{ticker}.{field} must be finite")
    return result


def source_ids_from_mapping(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, dict):
        found: list[str] = []
        source_id = value.get("source_id")
        if isinstance(source_id, str) and source_id.strip():
            found.append(source_id.strip())
        for child in value.values():
            found.extend(source_ids_from_mapping(child))
        return found
    if isinstance(value, list):
        found: list[str] = []
        for child in value:
            found.extend(source_ids_from_mapping(child))
        return found
    return []


def positive_ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or numerator <= 0 or denominator <= 0:
        return None
    return numerator / denominator


def percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise InputError("Cannot calculate a percentile from an empty list")
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def normalize_classification(value: Any, ticker: str) -> str:
    if not isinstance(value, str):
        raise InputError(f"{ticker}.classification is required")
    normalized = value.strip().title()
    if normalized not in CLASSIFICATIONS:
        allowed = ", ".join(sorted(CLASSIFICATIONS))
        raise InputError(f"{ticker}.classification must be one of: {allowed}")
    return normalized


def validate_payload_metadata(
    payload: dict[str, Any], valuation_date: date, warnings: list[str]
) -> dict[str, Any]:
    raw_tier = payload.get("data_tier")
    if raw_tier is None:
        data_tier = "D"
        warnings.append("未提供数据等级；输出已按最保守的 D 级数据处理")
    elif not isinstance(raw_tier, str) or raw_tier.strip().upper() not in DATA_TIERS:
        raise InputError("data_tier must be A, B, C, or D")
    else:
        data_tier = raw_tier.strip().upper()

    raw_mode = payload.get("output_mode", "decision-brief")
    if not isinstance(raw_mode, str) or raw_mode.strip().lower() not in OUTPUT_MODES:
        raise InputError("output_mode must be decision-brief, full-report, or audit-pack")
    output_mode = raw_mode.strip().lower()

    fx_rates = payload.get("fx_rates", [])
    if not isinstance(fx_rates, list):
        raise InputError("fx_rates must be an array")
    normalized_fx: list[dict[str, Any]] = []
    for index, item in enumerate(fx_rates):
        if not isinstance(item, dict):
            raise InputError(f"fx_rates[{index}] must be an object")
        pair = item.get("pair")
        if not isinstance(pair, str) or "/" not in pair:
            raise InputError(f"fx_rates[{index}].pair must use BASE/QUOTE format")
        rate = number(item.get("rate"), f"fx_rates[{index}].rate", "meta", required=True)
        assert rate is not None
        if rate <= 0:
            raise InputError(f"fx_rates[{index}].rate must be positive")
        rate_date = parse_date(item.get("rate_date"), f"fx_rates[{index}].rate_date")
        if rate_date > valuation_date:
            raise InputError(f"fx_rates[{index}].rate_date is after valuation_date")
        age = (valuation_date - rate_date).days
        if age > 3:
            warnings.append(
                f"{pair}：汇率日期比估值基准日早 {age} 天，请解释日期不一致的原因"
            )
        source_id = item.get("source_id")
        if not isinstance(source_id, str) or not source_id.strip():
            warnings.append(f"{pair}：缺少汇率来源编号（source_id）")
        normalized_fx.append(
            {
                "pair": pair.upper(),
                "rate": rate,
                "rate_date": rate_date.isoformat(),
                "source_id": source_id,
            }
        )

    source_ledger = payload.get("source_ledger", [])
    if not isinstance(source_ledger, list):
        raise InputError("source_ledger must be an array")
    source_ids: set[str] = set()
    for index, source in enumerate(source_ledger):
        if not isinstance(source, dict):
            raise InputError(f"source_ledger[{index}] must be an object")
        source_id = source.get("source_id")
        if not isinstance(source_id, str) or not source_id.strip():
            raise InputError(f"source_ledger[{index}].source_id is required")
        if source_id in source_ids:
            raise InputError(f"source_ledger source_id {source_id} is duplicated")
        source_ids.add(source_id)
        for field in ("publication_date", "estimate_date"):
            if source.get(field) is None:
                continue
            parsed = parse_date(source[field], f"source_ledger[{index}].{field}")
            if parsed > valuation_date:
                raise InputError(f"source_ledger[{index}].{field} is after valuation_date")

    if data_tier in {"A", "B"} and not source_ledger:
        warnings.append(
            f"输入声明为 {data_tier} 级数据，但来源台账为空；在补齐来源、快照和字段覆盖前，不应形成高置信度结论"
        )

    for fx in normalized_fx:
        if fx["source_id"] and source_ids and fx["source_id"] not in source_ids:
            warnings.append(f"{fx['pair']}：汇率来源编号未出现在来源台账中")

    raw_companies = payload.get("companies", [])
    report_currency = payload.get("currency")
    required_pairs: set[str] = set()
    for company in raw_companies if isinstance(raw_companies, list) else []:
        if not isinstance(company, dict):
            continue
        source_currency = company.get("source_currency")
        if (
            isinstance(source_currency, str)
            and isinstance(report_currency, str)
            and source_currency.upper() != report_currency.upper()
        ):
            required_pairs.add(f"{source_currency.upper()}/{report_currency.upper()}")
    provided_pairs = {item["pair"] for item in normalized_fx}
    missing_pairs = sorted(pair for pair in required_pairs if pair not in provided_pairs)
    if missing_pairs:
        raise InputError(f"Missing FX metadata for: {', '.join(missing_pairs)}")

    return {
        "data_tier": data_tier,
        "output_mode": output_mode,
        "fx_rates": normalized_fx,
        "source_count": len(source_ledger),
        "source_ids": source_ids,
    }


def validate_cash_bridge(
    company: dict[str, Any], ticker: str, deductible_cash: float, warnings: list[str]
) -> dict[str, float] | None:
    raw = company.get("cash_bridge")
    if raw is None:
        if deductible_cash > 0:
            warnings.append(
                f"{ticker}：缺少现金调节表，无法将可扣现金与报告流动资金勾稽"
            )
        return None
    if not isinstance(raw, dict):
        raise InputError(f"{ticker}.cash_bridge must be an object")
    fields = (
        "cash_and_equivalents",
        "term_deposits",
        "short_term_investments",
        "restricted_cash",
        "operating_cash_reserve",
    )
    normalized: dict[str, float] = {}
    for field in fields:
        value = number(raw.get(field, 0.0), f"cash_bridge.{field}", ticker)
        normalized[field] = 0.0 if value is None else value
        if normalized[field] < 0:
            raise InputError(f"{ticker}.cash_bridge.{field} must be non-negative")
    reported_deductible = number(
        raw.get("deductible_cash"), "cash_bridge.deductible_cash", ticker, required=True
    )
    assert reported_deductible is not None
    if reported_deductible < 0:
        raise InputError(f"{ticker}.cash_bridge.deductible_cash must be non-negative")
    expected = (
        normalized["cash_and_equivalents"]
        + normalized["term_deposits"]
        + normalized["short_term_investments"]
        - normalized["restricted_cash"]
        - normalized["operating_cash_reserve"]
    )
    tolerance = max(1e-6, abs(reported_deductible) * 0.01)
    if abs(expected - reported_deductible) > tolerance:
        raise InputError(
            f"{ticker}.cash_bridge does not reconcile: components imply {expected}, "
            f"but deductible_cash is {reported_deductible}"
        )
    if abs(reported_deductible - deductible_cash) > tolerance:
        raise InputError(
            f"{ticker}.cash must equal cash_bridge.deductible_cash for the EV calculation"
        )
    normalized["deductible_cash"] = reported_deductible
    return normalized


def validate_dates(company: dict[str, Any], valuation_date: date) -> None:
    ticker = company["ticker"]
    for field in ("price_date", "balance_sheet_date", "share_count_date"):
        if field == "share_count_date" and company.get(field) is None:
            continue
        parsed = parse_date(company.get(field), field, ticker)
        if parsed > valuation_date:
            raise InputError(f"{ticker}.{field} is after valuation_date")

    has_ntm = any(
        company.get(field) is not None
        for field in FINANCIAL_FIELDS
        if field.startswith("ntm_")
    )
    estimate_date_value = company.get("estimate_date")
    if has_ntm and estimate_date_value is None:
        raise InputError(f"{ticker}.estimate_date is required when NTM data is present")
    if estimate_date_value is not None:
        estimate_date = parse_date(estimate_date_value, "estimate_date", ticker)
        if estimate_date > valuation_date:
            raise InputError(f"{ticker}.estimate_date is after valuation_date")


def derive_share_count(
    company: dict[str, Any], ticker: str, warnings: list[str]
) -> tuple[float, dict[str, Any] | None]:
    direct = number(company.get("diluted_shares"), "diluted_shares", ticker)
    components = company.get("share_count")
    if components is None:
        if direct is None or direct <= 0:
            raise InputError(f"{ticker}.diluted_shares or share_count is required and must be positive")
        return direct, None
    if not isinstance(components, dict):
        raise InputError(f"{ticker}.share_count must be an object")

    basic = number(components.get("basic_shares"), "share_count.basic_shares", ticker, required=True)
    assert basic is not None
    if basic <= 0:
        raise InputError(f"{ticker}.share_count.basic_shares must be positive")
    bridge: dict[str, float] = {"basic_shares": basic}
    for field in SHARE_ADD_FIELDS | SHARE_SUB_FIELDS:
        value = number(components.get(field, 0.0), f"share_count.{field}", ticker)
        bridge[field] = 0.0 if value is None else value
        if bridge[field] < 0:
            raise InputError(f"{ticker}.share_count.{field} must be non-negative")

    derived = basic + sum(bridge[field] for field in SHARE_ADD_FIELDS) - sum(
        bridge[field] for field in SHARE_SUB_FIELDS
    )
    if derived <= 0:
        raise InputError(f"{ticker}: derived diluted shares are non-positive")

    unsettled_asr = number(
        components.get("unsettled_asr_estimated_shares", 0.0),
        "share_count.unsettled_asr_estimated_shares",
        ticker,
    )
    if unsettled_asr is not None and unsettled_asr < 0:
        raise InputError(f"{ticker}.share_count.unsettled_asr_estimated_shares must be non-negative")
    bridge["unsettled_asr_estimated_shares"] = 0.0 if unsettled_asr is None else unsettled_asr
    bridge["derived_diluted_shares"] = derived
    if bridge["unsettled_asr_estimated_shares"] > 0:
        warnings.append(
            f"{ticker}：已披露尚未结算的加速股份回购（ASR）预计股份，但未计入完全稀释股本"
        )
    if direct is not None and abs(direct - derived) / derived > 0.01:
        warnings.append(
            f"{ticker}：输入的完全稀释股本与组成项调节结果相差超过 1%，已采用调节表结果"
        )
    return derived, bridge


def validate_market_data_basis(
    company: dict[str, Any],
    ticker: str,
    valuation_date: date,
    price: float,
    diluted_shares: float,
    known_source_ids: set[str],
) -> dict[str, Any]:
    share_count_date = parse_date(company.get("share_count_date"), "share_count_date", ticker)
    price_date = parse_date(company.get("price_date"), "price_date", ticker)
    if share_count_date != valuation_date:
        raise InputError(f"{ticker}.share_count_date must equal valuation_date")
    if price_date > valuation_date or (valuation_date - price_date).days > 7:
        raise InputError(f"{ticker}.price_date must be the valuation date or a recent prior trading day")
    if company.get("price_basis") != "unadjusted_close":
        raise InputError(f"{ticker}.price_basis must be unadjusted_close for market capitalization")

    reference_market_cap = number(
        company.get("reference_market_cap"), "reference_market_cap", ticker, required=True
    )
    assert reference_market_cap is not None
    if reference_market_cap <= 0:
        raise InputError(f"{ticker}.reference_market_cap must be positive")
    market_cap_date = parse_date(company.get("market_cap_date"), "market_cap_date", ticker)
    if market_cap_date != price_date:
        raise InputError(f"{ticker}.market_cap_date must equal price_date")
    market_cap_source_id = company.get("market_cap_source_id")
    if not isinstance(market_cap_source_id, str) or market_cap_source_id not in known_source_ids:
        raise InputError(f"{ticker}.market_cap_source_id must reference source_ledger")
    tolerance_pct = number(
        company.get("market_cap_tolerance_pct", 0.02),
        "market_cap_tolerance_pct",
        ticker,
        required=True,
    )
    assert tolerance_pct is not None
    if tolerance_pct < 0 or tolerance_pct > 0.10:
        raise InputError(f"{ticker}.market_cap_tolerance_pct must be between 0 and 0.10")
    calculated_market_cap = price * diluted_shares
    difference_pct = (calculated_market_cap - reference_market_cap) / reference_market_cap
    if abs(difference_pct) > tolerance_pct:
        raise InputError(
            f"{ticker}: price × valuation-date shares does not reconcile to independent market cap; "
            f"difference={difference_pct:.4%}"
        )

    review = company.get("corporate_action_review")
    if not isinstance(review, dict):
        raise InputError(f"{ticker}.corporate_action_review is required")
    baseline_date = parse_date(review.get("baseline_share_date"), "corporate_action_review.baseline_share_date", ticker)
    search_start = parse_date(review.get("search_start_date"), "corporate_action_review.search_start_date", ticker)
    reviewed_through = parse_date(review.get("reviewed_through_date"), "corporate_action_review.reviewed_through_date", ticker)
    if search_start > baseline_date:
        raise InputError(f"{ticker}.corporate_action_review.search_start_date is after baseline_share_date")
    if reviewed_through != valuation_date:
        raise InputError(f"{ticker}.corporate_action_review.reviewed_through_date must equal valuation_date")
    review_source_ids = review.get("source_ids")
    if (
        not isinstance(review_source_ids, list)
        or not review_source_ids
        or any(source_id not in known_source_ids for source_id in review_source_ids)
    ):
        raise InputError(f"{ticker}.corporate_action_review.source_ids must reference source_ledger")
    if review.get("no_unrecorded_actions_confirmed") is not True:
        raise InputError(f"{ticker}.corporate_action_review must confirm complete coverage")
    actions = review.get("actions")
    if not isinstance(actions, list):
        raise InputError(f"{ticker}.corporate_action_review.actions must be an array")
    last_after_shares: float | None = None
    last_effective_date: date | None = None
    for index, action in enumerate(actions):
        if not isinstance(action, dict):
            raise InputError(f"{ticker}.corporate_action_review.actions[{index}] must be an object")
        if action.get("source_id") not in known_source_ids:
            raise InputError(f"{ticker}.corporate_action_review.actions[{index}].source_id is invalid")
        announcement_date = parse_date(action.get("announcement_date"), f"corporate_action_review.actions[{index}].announcement_date", ticker)
        effective_date = parse_date(action.get("effective_date"), f"corporate_action_review.actions[{index}].effective_date", ticker)
        before_shares = number(action.get("before_shares"), f"corporate_action_review.actions[{index}].before_shares", ticker, required=True)
        change_shares = number(action.get("change_shares"), f"corporate_action_review.actions[{index}].change_shares", ticker, required=True)
        after_shares = number(action.get("after_shares"), f"corporate_action_review.actions[{index}].after_shares", ticker, required=True)
        assert before_shares is not None and change_shares is not None and after_shares is not None
        tolerance = max(1e-8, abs(after_shares) * 1e-6)
        if abs(before_shares + change_shares - after_shares) > tolerance:
            raise InputError(f"{ticker}.corporate_action_review.actions[{index}] share roll-forward does not reconcile")
        if effective_date <= valuation_date:
            if announcement_date > valuation_date:
                raise InputError(f"{ticker}: corporate action was not public by valuation_date")
            if action.get("applied_to_share_count") is not True:
                raise InputError(f"{ticker}: effective corporate action was not applied to share count")
            if effective_date > price_date:
                raise InputError(f"{ticker}: price_date predates an effective corporate action")
            if last_effective_date is not None and effective_date < last_effective_date:
                raise InputError(f"{ticker}: corporate actions must be ordered by effective_date")
            if last_after_shares is not None and abs(before_shares - last_after_shares) > tolerance:
                raise InputError(f"{ticker}: corporate action share roll-forward is discontinuous")
            last_after_shares = after_shares
            last_effective_date = effective_date
    if last_after_shares is not None:
        tolerance = max(1e-8, abs(last_after_shares) * 1e-6)
        if abs(last_after_shares - diluted_shares) > tolerance:
            raise InputError(f"{ticker}: valuation-date shares do not reflect the last effective corporate action")
    return {
        "share_count_date": share_count_date.isoformat(),
        "price_basis": "unadjusted_close",
        "reference_market_cap": reference_market_cap,
        "market_cap_date": market_cap_date.isoformat(),
        "market_cap_source_id": market_cap_source_id,
        "market_cap_difference_pct": difference_pct,
        "corporate_action_review_complete": True,
    }


def derive_book_value(
    company: dict[str, Any],
    ticker: str,
    price_date: date,
    diluted_shares: float,
    share_bridge: dict[str, Any] | None,
    warnings: list[str],
) -> dict[str, Any]:
    common_equity = number(company.get("common_equity"), "common_equity", ticker)
    reported_bvps = number(company.get("reported_bvps"), "reported_bvps", ticker)
    book_shares = number(company.get("book_value_shares"), "book_value_shares", ticker)
    if book_shares is None and share_bridge is not None:
        book_shares = share_bridge["basic_shares"]
    if book_shares is None and common_equity is not None:
        book_shares = diluted_shares
        warnings.append(
            f"{ticker}：缺少每股净资产计算股本，已使用完全稀释股本推导每股净资产（BVPS）"
        )
    if book_shares is not None and book_shares <= 0:
        raise InputError(f"{ticker}.book_value_shares must be positive")
    if common_equity is not None and common_equity <= 0:
        warnings.append(f"{ticker}：普通股股东权益不为正，市净率（P/B）无经济意义（NM）")
    if reported_bvps is not None and reported_bvps <= 0:
        warnings.append(f"{ticker}：报告每股净资产（BVPS）不为正，市净率（P/B）无经济意义（NM）")

    computed_bvps = None
    if common_equity is not None and book_shares is not None and common_equity > 0:
        computed_bvps = common_equity / book_shares
    if computed_bvps is not None and reported_bvps is not None:
        if abs(computed_bvps - reported_bvps) / computed_bvps > 0.01:
            warnings.append(
                f"{ticker}：报告每股净资产与普通股股东权益除以匹配股本的结果相差超过 1%，已采用计算值"
            )
    base_bvps = computed_bvps if computed_bvps is not None else reported_bvps
    base_equity = common_equity

    dividends = company.get("dividends", [])
    if not isinstance(dividends, list):
        raise InputError(f"{ticker}.dividends must be an array")
    deduction_amount = 0.0
    deduction_per_share = 0.0
    applied: list[dict[str, Any]] = []
    for index, item in enumerate(dividends):
        if not isinstance(item, dict):
            raise InputError(f"{ticker}.dividends[{index}] must be an object")
        ex_date = parse_date(item.get("ex_date"), f"dividends[{index}].ex_date", ticker)
        dps = number(item.get("dps"), f"dividends[{index}].dps", ticker, required=True)
        assert dps is not None
        if dps < 0:
            raise InputError(f"{ticker}.dividends[{index}].dps must be non-negative")
        reduced = item.get("equity_already_reduced")
        if not isinstance(reduced, bool):
            raise InputError(
                f"{ticker}.dividends[{index}].equity_already_reduced must be boolean"
            )
        eligible = number(
            item.get("eligible_shares"), f"dividends[{index}].eligible_shares", ticker
        )
        should_apply = ex_date <= price_date and not reduced
        item_result = {
            "type": item.get("type", "unspecified"),
            "ex_date": ex_date.isoformat(),
            "dps": dps,
            "equity_already_reduced": reduced,
            "applied": should_apply,
        }
        if should_apply:
            if base_equity is not None and book_shares is not None:
                entitled_shares = book_shares if eligible is None else eligible
                deduction_amount += dps * entitled_shares
                deduction_per_share += dps * entitled_shares / book_shares
                item_result["eligible_shares"] = entitled_shares
            elif eligible is not None:
                raise InputError(
                    f"{ticker}.dividends[{index}]: eligible_shares requires common_equity and book_value_shares"
                )
            else:
                deduction_per_share += dps
        applied.append(item_result)

    adjusted_equity = None if base_equity is None else base_equity - deduction_amount
    adjusted_bvps = None if base_bvps is None else base_bvps - deduction_per_share
    if adjusted_equity is not None and adjusted_equity <= 0:
        warnings.append(f"{ticker}：股息调整后普通股股东权益不为正，市净率（P/B）无经济意义（NM）")
    if adjusted_bvps is not None and adjusted_bvps <= 0:
        warnings.append(f"{ticker}：股息调整后每股净资产（BVPS）不为正，市净率（P/B）无经济意义（NM）")

    return {
        "common_equity": common_equity,
        "book_value_shares": book_shares,
        "reported_bvps_input": reported_bvps,
        "reported_bvps": base_bvps,
        "dividend_deduction": deduction_amount,
        "dividend_deduction_per_share": deduction_per_share,
        "adjusted_common_equity": adjusted_equity,
        "adjusted_bvps": adjusted_bvps,
        "dividends": applied,
    }


def derive_peer_assessment(company: dict[str, Any], ticker: str) -> dict[str, Any] | None:
    if company["classification"] == "Target":
        return None
    scores = company.get("peer_scores")
    if not isinstance(scores, dict):
        raise InputError(f"{ticker}.peer_scores is required for non-target companies")
    normalized: dict[str, float] = {}
    for field in PEER_SCORE_WEIGHTS:
        value = number(scores.get(field), f"peer_scores.{field}", ticker, required=True)
        assert value is not None
        if not 0 <= value <= 5:
            raise InputError(f"{ticker}.peer_scores.{field} must be between 0 and 5")
        normalized[field] = value
    quality_value = company.get("data_quality")
    if not isinstance(quality_value, str):
        raise InputError(f"{ticker}.data_quality is required")
    quality = quality_value.strip().title()
    if quality not in DATA_QUALITY:
        raise InputError(f"{ticker}.data_quality must be Pass, Limited, or Fail")
    total = sum(normalized[field] * PEER_SCORE_WEIGHTS[field] for field in normalized)
    eligible_for_core_statistics = (
        quality == "Pass"
        and total >= 3.5
        and all(
            normalized[field] >= 3
            for field in ("business_overlap", "business_model", "revenue_structure")
        )
    )
    return {
        "scores": normalized,
        "weighted_score": total,
        "data_quality": quality,
        "eligible_for_core_statistics": eligible_for_core_statistics,
    }


def derive_company(
    company: dict[str, Any], valuation_date: date, warnings: list[str], known_source_ids: set[str]
) -> dict[str, Any]:
    if not isinstance(company, dict):
        raise InputError("Every company must be an object")
    raw_ticker = company.get("ticker")
    if not isinstance(raw_ticker, str) or not raw_ticker.strip():
        raise InputError("Every company requires a non-empty ticker")
    ticker = raw_ticker.strip().upper()
    company = dict(company)
    company["ticker"] = ticker
    classification = normalize_classification(company.get("classification"), ticker)
    company["classification"] = classification
    peer_assessment = derive_peer_assessment(company, ticker)
    raw_role = company.get("peer_role")
    peer_role = None
    if classification != "Target":
        if raw_role is None:
            peer_role = "Excluded" if classification == "Excluded" else None
            if peer_role is None:
                warnings.append(f"{ticker}：缺少同行经济角色，请补充分组理由")
        elif not isinstance(raw_role, str) or raw_role.strip() not in PEER_ROLES:
            allowed = ", ".join(sorted(PEER_ROLES))
            raise InputError(f"{ticker}.peer_role must be one of: {allowed}")
        else:
            peer_role = raw_role.strip()
    if classification == "Excluded" and any(
        company.get(field) is None for field in ("price", "price_date", "balance_sheet_date")
    ):
        warnings.append(
            f"{ticker}：排除公司的财务数据不完整，仅保留用于同行分类审计"
        )
        return {
            "name": company.get("name", ticker),
            "ticker": ticker,
            "classification": classification,
            "peer_role": peer_role,
            "peer_assessment": peer_assessment,
            "selection_rationale": company.get("selection_rationale"),
            "classification_rationale": company.get("classification_rationale"),
            "metric_rationale": company.get("metric_rationale"),
            "field_sources": company.get("field_sources"),
            "price_date": company.get("price_date"),
            "share_count_date": company.get("share_count_date"),
            "balance_sheet_date": company.get("balance_sheet_date"),
            "estimate_date": company.get("estimate_date"),
            "price": None,
            "diluted_shares": None,
            "share_count_bridge": None,
            "market_cap": None,
            "net_debt_bridge": None,
            "enterprise_value": None,
            "ev_bridge": None,
            "cash_bridge": None,
            "financials": {field: None for field in FINANCIAL_FIELDS},
            "book_value": {
                "common_equity": None,
                "book_value_shares": None,
                "reported_bvps_input": None,
                "reported_bvps": None,
                "dividend_deduction": None,
                "dividend_deduction_per_share": None,
                "adjusted_common_equity": None,
                "adjusted_bvps": None,
                "dividends": [],
            },
            "average_common_equity": None,
            "metrics": {metric: None for metric in ALL_METRICS},
        }
    validate_dates(company, valuation_date)

    for field in ("balance_sheet_publication_date", "share_count_publication_date"):
        value = company.get(field)
        if value is None:
            if field == "balance_sheet_publication_date":
                warnings.append(
                    f"{ticker}：缺少资产负债表公开日期，无法完整审计历史时点可得性"
                )
            continue
        parsed = parse_date(value, field, ticker)
        if parsed > valuation_date:
            raise InputError(f"{ticker}.{field} is after valuation_date")

    price = number(company.get("price"), "price", ticker, required=True)
    assert price is not None
    if price <= 0:
        raise InputError(f"{ticker}.price must be greater than zero")
    price_date = parse_date(company["price_date"], "price_date", ticker)
    if price_date != valuation_date:
        warnings.append(
            f"{ticker}：价格日期与估值基准日不同，请确认是否正确采用此前最近交易日"
        )

    diluted_shares, share_bridge = derive_share_count(company, ticker, warnings)
    market_cap = price * diluted_shares
    market_data_audit = validate_market_data_basis(
        company, ticker, valuation_date, price, diluted_shares, known_source_ids
    )

    bridge: dict[str, float] = {}
    for field in EV_BRIDGE_FIELDS:
        value = number(company.get(field, 0.0), field, ticker)
        bridge[field] = 0.0 if value is None else value
        if bridge[field] < 0:
            raise InputError(
                f"{ticker}: EV bridge inputs must be non-negative; use the named sides of the bridge"
            )
    cash_bridge = validate_cash_bridge(company, ticker, bridge["cash"], warnings)
    net_debt_bridge = (
        bridge["debt"]
        + bridge["preferred_equity"]
        + bridge["noncontrolling_interest"]
        + bridge["debt_like_adjustments"]
        - bridge["cash"]
        - bridge["non_operating_investments"]
    )
    enterprise_value = market_cap + net_debt_bridge
    if enterprise_value <= 0:
        warnings.append(f"{ticker}：企业价值不为正，企业价值类倍数无经济意义（NM）")

    financials = {
        field: number(company.get(field), field, ticker) for field in FINANCIAL_FIELDS
    }
    if company.get("estimate_date") is not None:
        estimate_date = parse_date(company["estimate_date"], "estimate_date", ticker)
        estimate_age = (valuation_date - estimate_date).days
        if estimate_age > 120:
            warnings.append(
                f"{ticker}：未来十二个月（NTM）预测快照距估值基准日 {estimate_age} 天，请评估预测新鲜度"
            )
    balance_sheet_date = parse_date(company["balance_sheet_date"], "balance_sheet_date", ticker)
    balance_sheet_age = (valuation_date - balance_sheet_date).days
    if balance_sheet_age > 270:
        warnings.append(
            f"{ticker}：资产负债表距估值基准日 {balance_sheet_age} 天，企业价值调节表可能已过期"
        )
    book_value = derive_book_value(
        company, ticker, price_date, diluted_shares, share_bridge, warnings
    )
    average_common_equity = number(
        company.get("average_common_equity"), "average_common_equity", ticker
    )
    reported_roe = number(company.get("ltm_roe"), "ltm_roe", ticker)
    calculated_roe = positive_ratio(financials["ltm_net_income"], average_common_equity)
    if calculated_roe is not None and reported_roe is not None:
        if abs(calculated_roe - reported_roe) > 0.01:
            warnings.append(
                f"{ticker}：输入的最近十二个月净资产收益率与净利润除以平均普通股权益的结果相差超过 1 个百分点，已采用计算值"
            )
    ltm_roe = calculated_roe if calculated_roe is not None else reported_roe
    if ltm_roe is not None and abs(ltm_roe) > 1:
        warnings.append(f"{ticker}：最近十二个月净资产收益率（LTM ROE）的绝对值超过 100%，请确认输入使用小数形式")

    metrics: dict[str, float | None] = {}
    for metric, denominator_field in EV_METRICS.items():
        metrics[metric] = positive_ratio(enterprise_value, financials[denominator_field])
    for metric, denominator_field in PE_METRICS.items():
        metrics[metric] = positive_ratio(market_cap, financials[denominator_field])
    for metric, denominator_field in PS_METRICS.items():
        metrics[metric] = positive_ratio(market_cap, financials[denominator_field])
    for metric, numerator_field in FCF_YIELD_METRICS.items():
        metrics[metric] = positive_ratio(financials[numerator_field], market_cap)
    metrics["price_to_book"] = positive_ratio(price, book_value["adjusted_bvps"])
    metrics["ltm_roe"] = ltm_roe if ltm_roe is not None and ltm_roe > 0 else None

    if peer_assessment is not None:
        total = peer_assessment["weighted_score"]
        quality = peer_assessment["data_quality"]
        scores = peer_assessment["scores"]
        if classification == "Core" and (
            total < 3.5
            or quality != "Pass"
            or any(scores[field] < 3 for field in ("business_overlap", "business_model", "revenue_structure"))
        ):
            warnings.append(
                f"{ticker}：核心可比公司分类未满足默认评分或数据质量门槛，已从核心统计中排除"
            )
        if classification == "Secondary" and quality == "Fail":
            warnings.append(f"{ticker}：辅助可比公司的数据质量为不通过，建议改列排除公司")

    return {
        "name": company.get("name", ticker),
        "ticker": ticker,
        "classification": classification,
        "peer_role": peer_role,
        "peer_assessment": peer_assessment,
        "selection_rationale": company.get("selection_rationale"),
        "classification_rationale": company.get("classification_rationale"),
        "metric_rationale": company.get("metric_rationale"),
        "field_sources": company.get("field_sources"),
        "price_date": company["price_date"],
        "share_count_date": company.get("share_count_date"),
        "balance_sheet_date": company["balance_sheet_date"],
        "estimate_date": company.get("estimate_date"),
        "price": price,
        "diluted_shares": diluted_shares,
        "share_count_bridge": share_bridge,
        "market_cap": market_cap,
        "market_data_audit": market_data_audit,
        "net_debt_bridge": net_debt_bridge,
        "enterprise_value": enterprise_value,
        "ev_bridge": bridge,
        "cash_bridge": cash_bridge,
        "financials": financials,
        "book_value": book_value,
        "average_common_equity": average_common_equity,
        "metrics": metrics,
    }


def core_statistics(companies: list[dict[str, Any]], warnings: list[str]) -> dict[str, Any]:
    marked_core = [company for company in companies if company["classification"] == "Core"]
    core = [
        company
        for company in marked_core
        if (company.get("peer_assessment") or {}).get("eligible_for_core_statistics") is True
    ]
    excluded_count = len(marked_core) - len(core)
    if excluded_count:
        warnings.append(
            f"有 {excluded_count} 家标记为核心可比公司的候选未通过硬门槛，未纳入主统计"
        )
    if len(core) < 3:
        warnings.append(
            f"仅有 {len(core)} 家核心可比公司，四分位数结论稳健性不足"
        )
    output: dict[str, Any] = {}
    for metric in ALL_METRICS:
        values = [
            company["metrics"][metric]
            for company in core
            if company["metrics"][metric] is not None
        ]
        if not values:
            output[metric] = {
                "count": 0,
                "p25": None,
                "median": None,
                "p75": None,
                "robust": False,
            }
            continue
        if len(values) < 3:
            warnings.append(
                f"{METRIC_LABELS_CN.get(metric, metric)}：仅有 {len(values)} 个有效核心可比公司观测值，统计结论稳健性不足"
            )
        output[metric] = {
            "count": len(values),
            "p25": percentile(values, 0.25),
            "median": percentile(values, 0.50),
            "p75": percentile(values, 0.75),
            "robust": len(values) >= 3,
        }
    return output


def implied_values(target: dict[str, Any], statistics: dict[str, Any]) -> dict[str, Any]:
    shares = target["diluted_shares"]
    net_debt = target["net_debt_bridge"]
    output: dict[str, Any] = {}

    for metric, financial_field in EV_METRICS.items():
        stats = statistics[metric]
        fundamental = target["financials"][financial_field]
        if stats["count"] == 0 or fundamental is None or fundamental <= 0:
            output[metric] = None
            continue
        prices = {
            key: ((stats[key] * fundamental) - net_debt) / shares
            for key in ("p25", "median", "p75")
        }
        output[metric] = {
            "low": prices["p25"],
            "median": prices["median"],
            "high": prices["p75"],
            "anchors": prices,
        }

    for metric, financial_field in PE_METRICS.items():
        stats = statistics[metric]
        fundamental = target["financials"][financial_field]
        if stats["count"] == 0 or fundamental is None or fundamental <= 0:
            output[metric] = None
            continue
        prices = {
            key: (stats[key] * fundamental) / shares
            for key in ("p25", "median", "p75")
        }
        output[metric] = {
            "low": prices["p25"],
            "median": prices["median"],
            "high": prices["p75"],
            "anchors": prices,
        }

    for metric, financial_field in PS_METRICS.items():
        stats = statistics[metric]
        fundamental = target["financials"][financial_field]
        if stats["count"] == 0 or fundamental is None or fundamental <= 0:
            output[metric] = None
            continue
        prices = {
            key: (stats[key] * fundamental) / shares
            for key in ("p25", "median", "p75")
        }
        output[metric] = {
            "low": prices["p25"],
            "median": prices["median"],
            "high": prices["p75"],
            "anchors": prices,
        }

    for metric, financial_field in FCF_YIELD_METRICS.items():
        stats = statistics[metric]
        fundamental = target["financials"][financial_field]
        if stats["count"] == 0 or fundamental is None or fundamental <= 0:
            output[metric] = None
            continue
        prices = {
            key: (fundamental / stats[key]) / shares
            for key in ("p25", "median", "p75")
        }
        output[metric] = {
            "low": prices["p75"],
            "median": prices["median"],
            "high": prices["p25"],
            "anchors": prices,
            "note": "自由现金流收益率与估值方向相反：第75百分位数收益率对应价值低端，第25百分位数对应价值高端",
        }

    stats = statistics["price_to_book"]
    bvps = target["book_value"]["adjusted_bvps"]
    if stats["count"] == 0 or bvps is None or bvps <= 0:
        output["price_to_book"] = None
    else:
        prices = {key: stats[key] * bvps for key in ("p25", "median", "p75")}
        output["price_to_book"] = {
            "low": prices["p25"],
            "median": prices["median"],
            "high": prices["p75"],
            "anchors": prices,
        }
    return output


def pb_roe_cross_check(
    companies: list[dict[str, Any]], target: dict[str, Any], warnings: list[str]
) -> dict[str, Any] | None:
    observations = [
        (company["metrics"]["ltm_roe"], company["metrics"]["price_to_book"], company["ticker"])
        for company in companies
        if company["classification"] == "Core"
        and (company.get("peer_assessment") or {}).get("eligible_for_core_statistics") is True
        and company["metrics"]["ltm_roe"] is not None
        and company["metrics"]["price_to_book"] is not None
    ]
    if len(observations) < 4:
        warnings.append(
            f"市净率—净资产收益率（P/B–ROE）交叉检查仅有 {len(observations)} 个有效核心可比公司观测值，未运行回归"
        )
        return None
    xs = [item[0] for item in observations]
    ys = [item[1] for item in observations]
    x_mean = sum(xs) / len(xs)
    y_mean = sum(ys) / len(ys)
    ss_x = sum((value - x_mean) ** 2 for value in xs)
    if ss_x <= 1e-8:
        warnings.append("核心可比公司的净资产收益率离散度不足，未运行市净率—净资产收益率（P/B–ROE）交叉检查")
        return None
    beta = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys)) / ss_x
    alpha = y_mean - beta * x_mean
    fitted = [alpha + beta * x for x in xs]
    ss_res = sum((y - fit) ** 2 for y, fit in zip(ys, fitted))
    ss_total = sum((y - y_mean) ** 2 for y in ys)
    r_squared = None if ss_total <= 1e-12 else 1 - ss_res / ss_total
    target_roe = target["metrics"]["ltm_roe"]
    target_pb = target["metrics"]["price_to_book"]
    predicted_pb = None if target_roe is None else alpha + beta * target_roe
    implied_share = None
    target_bvps = target["book_value"]["adjusted_bvps"]
    if predicted_pb is not None and predicted_pb > 0 and target_bvps is not None:
        implied_share = predicted_pb * target_bvps
    if predicted_pb is not None and predicted_pb <= 0:
        warnings.append("市净率—净资产收益率（P/B–ROE）回归预测的目标市净率不为正，应视为无效结果")
    residual = None if target_pb is None or predicted_pb is None else target_pb - predicted_pb
    return {
        "count": len(observations),
        "tickers": [item[2] for item in observations],
        "model": "市净率 = 截距 + 斜率 × 最近十二个月净资产收益率（小数）",
        "alpha": alpha,
        "beta": beta,
        "r_squared": r_squared,
        "target_roe": target_roe,
        "actual_target_pb": target_pb,
        "predicted_target_pb": predicted_pb,
        "target_pb_residual": residual,
        "implied_share_value": implied_share,
    }


def calculate_value(
    target: dict[str, Any], metric: str, anchor: float, fundamental: float,
    *, net_debt: float | None = None, shares: float | None = None
) -> float:
    used_shares = target["diluted_shares"] if shares is None else shares
    used_net_debt = target["net_debt_bridge"] if net_debt is None else net_debt
    if used_shares <= 0 or anchor <= 0 or fundamental <= 0:
        raise InputError("Valuation anchor, fundamental and diluted shares must be positive")
    if metric in EV_METRICS:
        return (anchor * fundamental - used_net_debt) / used_shares
    if metric in PE_METRICS or metric in PS_METRICS:
        return anchor * fundamental / used_shares
    if metric in FCF_YIELD_METRICS:
        return fundamental / anchor / used_shares
    if metric in BOOK_METRICS:
        return anchor * fundamental
    raise InputError(f"Unsupported valuation metric: {metric}")


def market_implied_fundamentals(
    target: dict[str, Any], requests: Any
) -> list[dict[str, Any]]:
    if requests is None:
        return []
    if not isinstance(requests, list):
        raise InputError("market_implied_requests must be an array")
    output: list[dict[str, Any]] = []
    for index, request in enumerate(requests):
        if not isinstance(request, dict):
            raise InputError(f"market_implied_requests[{index}] must be an object")
        metric = request.get("metric")
        if metric not in VALUATION_METRICS:
            raise InputError(f"market_implied_requests[{index}].metric is unsupported")
        benchmark = number(
            request.get("benchmark"), f"market_implied_requests[{index}].benchmark", "target", required=True
        )
        assert benchmark is not None
        if benchmark <= 0:
            raise InputError(f"market_implied_requests[{index}].benchmark must be positive")
        if metric in EV_METRICS:
            field = EV_METRICS[metric]
            implied = target["enterprise_value"] / benchmark
            current = target["financials"][field]
        elif metric in PE_METRICS:
            field = PE_METRICS[metric]
            implied = target["market_cap"] / benchmark
            current = target["financials"][field]
        elif metric in PS_METRICS:
            field = PS_METRICS[metric]
            implied = target["market_cap"] / benchmark
            current = target["financials"][field]
        elif metric in FCF_YIELD_METRICS:
            field = FCF_YIELD_METRICS[metric]
            implied = target["market_cap"] * benchmark
            current = target["financials"][field]
        else:
            field = BOOK_METRICS[metric]
            implied = target["price"] / benchmark
            current = target["book_value"][field]
        gap = None if current is None or current == 0 else implied / current - 1
        output.append(
            {
                "name": request.get("name", f"request_{index + 1}"),
                "metric": metric,
                "benchmark": benchmark,
                "implied_fundamental_field": field,
                "implied_fundamental": implied,
                "current_fundamental": current,
                "implied_vs_current": gap,
            }
        )
    return output


def sensitivity_analysis(target: dict[str, Any], spec: Any) -> dict[str, Any] | None:
    if spec is None:
        return None
    if not isinstance(spec, dict):
        raise InputError("sensitivity must be an object")
    metric = spec.get("metric")
    if metric not in VALUATION_METRICS:
        raise InputError("sensitivity.metric is unsupported")
    anchors_raw = spec.get("anchors")
    fundamentals_raw = spec.get("fundamentals")
    if not isinstance(anchors_raw, list) or not anchors_raw:
        raise InputError("sensitivity.anchors must be a non-empty array")
    if not isinstance(fundamentals_raw, list) or not fundamentals_raw:
        raise InputError("sensitivity.fundamentals must be a non-empty array")
    if len(anchors_raw) > 15 or len(fundamentals_raw) > 15:
        raise InputError("sensitivity axes cannot exceed 15 values each")
    anchors = [number(value, "sensitivity.anchors", "target", required=True) for value in anchors_raw]
    fundamentals = [
        number(value, "sensitivity.fundamentals", "target", required=True)
        for value in fundamentals_raw
    ]
    if any(value is None or value <= 0 for value in anchors + fundamentals):
        raise InputError("sensitivity axis values must be positive")
    net_debt = number(spec.get("net_debt_bridge"), "sensitivity.net_debt_bridge", "target")
    shares = number(spec.get("diluted_shares"), "sensitivity.diluted_shares", "target")
    rows = []
    for fundamental in fundamentals:
        assert fundamental is not None
        row = {
            "fundamental": fundamental,
            "share_values": [
                calculate_value(
                    target, metric, anchor, fundamental, net_debt=net_debt, shares=shares
                )
                for anchor in anchors
                if anchor is not None
            ],
        }
        rows.append(row)
    return {
        "metric": metric,
        "anchors": anchors,
        "fundamental_label": spec.get("fundamental_label"),
        "net_debt_bridge": target["net_debt_bridge"] if net_debt is None else net_debt,
        "diluted_shares": target["diluted_shares"] if shares is None else shares,
        "rows": rows,
    }


def scenario_analysis(target: dict[str, Any], scenarios: Any) -> list[dict[str, Any]]:
    if scenarios is None:
        return []
    if not isinstance(scenarios, list):
        raise InputError("scenarios must be an array")
    output: list[dict[str, Any]] = []
    for index, scenario in enumerate(scenarios):
        if not isinstance(scenario, dict):
            raise InputError(f"scenarios[{index}] must be an object")
        metric = scenario.get("metric")
        if metric not in VALUATION_METRICS:
            raise InputError(f"scenarios[{index}].metric is unsupported")
        anchor = number(scenario.get("anchor"), f"scenarios[{index}].anchor", "target", required=True)
        fundamental = number(
            scenario.get("fundamental"), f"scenarios[{index}].fundamental", "target", required=True
        )
        net_debt = number(
            scenario.get("net_debt_bridge"), f"scenarios[{index}].net_debt_bridge", "target"
        )
        shares = number(
            scenario.get("diluted_shares"), f"scenarios[{index}].diluted_shares", "target"
        )
        assert anchor is not None and fundamental is not None
        output.append(
            {
                "name": scenario.get("name", f"scenario_{index + 1}"),
                "metric": metric,
                "anchor": anchor,
                "fundamental": fundamental,
                "net_debt_bridge": target["net_debt_bridge"] if net_debt is None else net_debt,
                "diluted_shares": target["diluted_shares"] if shares is None else shares,
                "implied_share_value": calculate_value(
                    target, metric, anchor, fundamental, net_debt=net_debt, shares=shares
                ),
            }
        )
    return output


def calculate(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise InputError("Input must be a JSON object")
    valuation_date = parse_date(payload.get("valuation_date"), "valuation_date")
    target_ticker_value = payload.get("target_ticker")
    if not isinstance(target_ticker_value, str) or not target_ticker_value.strip():
        raise InputError("target_ticker is required")
    target_ticker = target_ticker_value.strip().upper()
    raw_companies = payload.get("companies")
    if not isinstance(raw_companies, list) or not raw_companies:
        raise InputError("companies must be a non-empty array")

    warnings: list[str] = []
    metadata = validate_payload_metadata(payload, valuation_date, warnings)
    companies = [
        derive_company(company, valuation_date, warnings, metadata["source_ids"])
        for company in raw_companies
    ]
    tickers = [company["ticker"] for company in companies]
    if len(tickers) != len(set(tickers)):
        raise InputError("Each ticker must appear only once")
    matches = [company for company in companies if company["ticker"] == target_ticker]
    if len(matches) != 1:
        raise InputError("target_ticker must match exactly one company")
    target = matches[0]
    if target["classification"] != "Target":
        raise InputError("The target company classification must be Target")

    blocking_issues: list[str] = []
    for company in companies:
        if company["classification"] == "Target":
            continue
        ticker = company["ticker"]
        if company.get("peer_role") is None:
            blocking_issues.append(f"{ticker}：缺少同行经济角色")
        for field, label in (
            ("selection_rationale", "候选池纳入理由"),
            ("classification_rationale", "最终分类理由"),
            ("metric_rationale", "可用与弃用指标理由"),
        ):
            if not company.get(field):
                blocking_issues.append(f"{ticker}：缺少{label}")
        assessment = company.get("peer_assessment")
        if company["classification"] == "Core" and assessment and not assessment.get("eligible_for_core_statistics"):
            blocking_issues.append(f"{ticker}：核心可比公司未通过评分或数据质量硬门槛")

    analysis_summary = payload.get("analysis_summary")
    if not isinstance(analysis_summary, dict):
        blocking_issues.append("缺少可比公司分析摘要，不能由倍数统计直接跳到估值结论")
        analysis_summary = {}
    else:
        for field, label in (
            ("conclusion", "结论"),
            ("peer_comparison", "目标公司与核心同行逐项比较"),
            ("premium_discount_rationale", "溢折价理由"),
        ):
            if not analysis_summary.get(field):
                blocking_issues.append(f"可比公司分析摘要缺少{label}")
        invalidation = analysis_summary.get("invalidation_conditions")
        if not isinstance(invalidation, list) or len(invalidation) < 3:
            blocking_issues.append("可比公司分析摘要必须提供至少三项可观察失效条件")

    valuation_profile = payload.get("valuation_profile")
    primary_metrics: list[str] = []
    if isinstance(valuation_profile, dict):
        raw_primary = valuation_profile.get("primary_metrics", [])
        if isinstance(raw_primary, list):
            primary_metrics = [item for item in raw_primary if isinstance(item, str)]
    for metric in primary_metrics:
        field = (
            EV_METRICS.get(metric)
            or PE_METRICS.get(metric)
            or PS_METRICS.get(metric)
            or FCF_YIELD_METRICS.get(metric)
        )
        if metric.startswith("ntm_") and field and target["financials"].get(field) is None:
            warnings.append(
                f"目标公司的主指标“{METRIC_LABELS_CN.get(metric, metric)}”缺少未来十二个月基本面数据，不得静默改用最近十二个月数据"
            )

    required_source_groups = (
        "price",
        "diluted_shares",
        "capital_structure",
        "primary_fundamentals",
        "corporate_actions",
        "market_cap_cross_check",
    )
    known_source_ids = metadata["source_ids"]
    for company in companies:
        if company["classification"] == "Excluded":
            continue
        ticker = company["ticker"]
        mapping = company.get("field_sources")
        invalid_groups: list[str] = []
        for group in required_source_groups:
            ids = source_ids_from_mapping(mapping.get(group)) if isinstance(mapping, dict) else []
            if not ids or any(source_id not in known_source_ids for source_id in ids):
                invalid_groups.append(group)
        if company["classification"] != "Target":
            ids = source_ids_from_mapping(mapping.get("peer_analysis")) if isinstance(mapping, dict) else []
            if not ids or any(source_id not in known_source_ids for source_id in ids):
                invalid_groups.append("peer_analysis")
        if invalid_groups:
            blocking_issues.append(f"{ticker}：字段来源映射为空或引用无效：{', '.join(invalid_groups)}")
    if any(metric in PS_METRICS for metric in primary_metrics):
        if not isinstance(valuation_profile, dict) or valuation_profile.get(
            "ps_revenue_basis_checked"
        ) is not True:
            warnings.append(
                "市销率（P/S）被选为主指标，但未确认收入确认口径、总额法/净额法和一次性收入已经标准化"
            )
        if not isinstance(valuation_profile, dict) or valuation_profile.get(
            "ps_capital_structure_comparable"
        ) is not True:
            warnings.append(
                "市销率（P/S）被选为主指标，但未确认目标公司与核心可比公司的资本结构足够接近；应优先检查企业价值/营业收入倍数"
            )
    if metadata["data_tier"] == "D" and any(metric.startswith("ntm_") for metric in primary_metrics):
        warnings.append(
            "D 级数据正在用于未来十二个月（NTM）主估值指标，应缩小结论范围或补充更可靠预测"
        )

    statistics = core_statistics(companies, warnings)
    primary_counts = [
        statistics.get(metric, {}).get("count", 0)
        for metric in primary_metrics
        if metric in statistics
    ]
    if primary_metrics and (not primary_counts or max(primary_counts) < 3):
        blocking_issues.append("主估值锚少于三家有效核心可比公司，不得形成稳健估值区间")
    if metadata["source_count"] == 0:
        blocking_issues.append("来源台账为空，无法形成可审计结论")

    model_status_code = "PASS" if not blocking_issues else "INCOMPLETE"
    return {
        "meta": {
            "valuation_date": valuation_date.isoformat(),
            "currency": payload.get("currency"),
            "unit": payload.get("unit"),
            "target_ticker": target_ticker,
            "valuation_profile": valuation_profile,
            "data_tier": metadata["data_tier"],
            "output_mode": metadata["output_mode"],
            "fx_rates": metadata["fx_rates"],
            "source_count": metadata["source_count"],
            "source_coverage_required_groups": list(required_source_groups),
            "percentile_method": "按位置 (n-1)×p 进行线性插值",
            "model_status_code": model_status_code,
            "model_status": "通过" if model_status_code == "PASS" else "未完成",
        },
        "companies": companies,
        "core_statistics": statistics,
        "pb_roe_cross_check": pb_roe_cross_check(companies, target, warnings),
        "implied_share_values": implied_values(target, statistics),
        "market_implied_fundamentals": market_implied_fundamentals(
            target, payload.get("market_implied_requests")
        ),
        "sensitivity_analysis": sensitivity_analysis(target, payload.get("sensitivity")),
        "scenario_analysis": scenario_analysis(target, payload.get("scenarios")),
        "analysis_summary": analysis_summary,
        "blocking_issues": blocking_issues,
        "warnings": warnings,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "计算股本与企业价值调节表、股息调整后市净率、交易倍数、"
            "核心可比公司统计、市场反推基本面和敏感性。"
        )
    )
    parser.add_argument("input", type=Path, help="标准化可比公司 JSON 输入文件")
    parser.add_argument("--output", type=Path, help="结果 JSON 输出路径")
    parser.add_argument("--indent", type=int, default=2, help="JSON 缩进空格数，默认为 2")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        result = calculate(payload)
    except (OSError, json.JSONDecodeError, InputError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2

    rendered = json.dumps(result, ensure_ascii=False, indent=args.indent, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
