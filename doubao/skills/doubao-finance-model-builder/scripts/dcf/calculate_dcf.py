#!/usr/bin/env python3
"""Deterministic FCFF DCF calculator for build-dcf-valuation."""

from __future__ import annotations

import argparse
import json
import math
from datetime import date
from pathlib import Path
from typing import Any


class DCFError(ValueError):
    pass


BRIDGE_ADDITIONS = ("cash", "non_operating_investments", "associates")
BRIDGE_CLAIMS = (
    "debt",
    "lease_liabilities",
    "unfunded_pension",
    "preferred_stock",
    "minority_interest",
    "other_claims",
)
SCENARIO_ZH = {"bear": "悲观", "base": "基准", "bull": "乐观"}


def scenario_zh(name: str) -> str:
    return SCENARIO_ZH.get(name.lower(), name)


def number(value: Any, field: str, default: float | None = None) -> float:
    if value is None:
        if default is None:
            raise DCFError(f"缺少数值字段：{field}")
        return default
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DCFError(f"字段 {field} 必须为数值")
    value = float(value)
    if not math.isfinite(value):
        raise DCFError(f"字段 {field} 必须为有限数值")
    return value


def iso_date(value: Any, field: str) -> date:
    if not isinstance(value, str):
        raise DCFError(f"{field} 必须为YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise DCFError(f"{field} 必须为YYYY-MM-DD") from exc


def calculate_wacc(components: dict[str, Any]) -> dict[str, float]:
    rf = number(components.get("risk_free_rate"), "risk_free_rate")
    beta = number(components.get("beta"), "beta")
    erp = number(components.get("equity_risk_premium"), "equity_risk_premium")
    crp = number(components.get("country_risk_premium"), "country_risk_premium", 0.0)
    size = number(components.get("size_premium"), "size_premium", 0.0)
    other = number(components.get("other_equity_premium"), "other_equity_premium", 0.0)
    pre_tax_debt = number(components.get("pre_tax_cost_of_debt"), "pre_tax_cost_of_debt")
    marginal_tax = number(components.get("marginal_tax_rate"), "marginal_tax_rate")
    equity_weight = number(components.get("equity_weight"), "equity_weight")
    debt_weight = number(components.get("debt_weight"), "debt_weight")
    if equity_weight < 0 or debt_weight < 0 or equity_weight + debt_weight <= 0:
        raise DCFError("资本权重不得为负，且权重合计必须大于零")
    weight_sum = equity_weight + debt_weight
    equity_weight /= weight_sum
    debt_weight /= weight_sum
    cost_of_equity = rf + beta * erp + crp + size + other
    after_tax_cost_of_debt = pre_tax_debt * (1.0 - marginal_tax)
    wacc = equity_weight * cost_of_equity + debt_weight * after_tax_cost_of_debt
    return {
        "risk_free_rate": rf,
        "beta": beta,
        "equity_risk_premium": erp,
        "country_risk_premium": crp,
        "size_premium": size,
        "other_equity_premium": other,
        "cost_of_equity": cost_of_equity,
        "pre_tax_cost_of_debt": pre_tax_debt,
        "marginal_tax_rate": marginal_tax,
        "after_tax_cost_of_debt": after_tax_cost_of_debt,
        "equity_weight": equity_weight,
        "debt_weight": debt_weight,
        "wacc": wacc,
    }


def scenario_wacc(payload: dict[str, Any], scenario: dict[str, Any]) -> tuple[float, dict[str, float] | None]:
    components = scenario.get("wacc_components", payload.get("wacc_components"))
    if components:
        detail = calculate_wacc(components)
        return detail["wacc"], detail
    wacc = number(scenario.get("wacc", payload.get("wacc")), "wacc")
    return wacc, None


def discount_time(index: int, row: dict[str, Any], convention: str) -> float:
    if row.get("discount_time") is not None:
        value = number(row["discount_time"], f"forecast[{index}].discount_time")
        if value <= 0:
            raise DCFError("折现时点 discount_time 必须大于零")
        return value
    if convention == "mid_year":
        return index - 0.5
    if convention == "end_year":
        return float(index)
    raise DCFError("折现约定 discount_convention 必须为 mid_year（年中折现）或 end_year（年末折现）")


def terminal_discount_time(meta: dict[str, Any], forecast: list[dict[str, Any]]) -> float:
    timing = meta.get("terminal_discount_timing", "end_year")
    if timing == "end_year":
        return float(len(forecast))
    if timing == "mid_year":
        return float(len(forecast)) - 0.5
    if timing == "explicit":
        return number(meta.get("terminal_discount_time"), "meta.terminal_discount_time")
    raise DCFError("终值折现时点 terminal_discount_timing 必须为 end_year、mid_year 或 explicit（显式指定）")


def bridge_values(payload: dict[str, Any]) -> dict[str, Any]:
    raw = payload.get("equity_bridge", {})
    valuation_date_raw = payload.get("meta", {}).get("valuation_date")
    valuation_date = iso_date(valuation_date_raw, "meta.valuation_date") if valuation_date_raw else None
    bridge: dict[str, Any] = {key: number(raw.get(key), f"equity_bridge.{key}", 0.0) for key in BRIDGE_ADDITIONS + BRIDGE_CLAIMS}
    bridge["diluted_shares"] = number(raw.get("diluted_shares"), "equity_bridge.diluted_shares")
    if bridge["diluted_shares"] <= 0:
        raise DCFError("完全稀释股份数 diluted_shares 必须大于零")
    raw_classes = raw.get("share_classes")
    if raw_classes is not None:
        if not isinstance(raw_classes, list) or not raw_classes:
            raise DCFError("equity_bridge.share_classes 必须为非空数组")
        normalized_classes: list[dict[str, Any]] = []
        class_by_security: dict[str, dict[str, Any]] = {}
        class_shares = 0.0
        market_cap = 0.0
        for index, item in enumerate(raw_classes):
            if not isinstance(item, dict):
                raise DCFError(f"equity_bridge.share_classes[{index}] 必须为对象")
            security_id = item.get("security_id")
            if not isinstance(security_id, str) or not security_id.strip():
                raise DCFError(f"equity_bridge.share_classes[{index}].security_id 必填")
            if security_id.strip() in class_by_security:
                raise DCFError(f"分证券证券代码重复：{security_id.strip()}")
            for field in ("exchange", "currency", "source_id"):
                value = item.get(field)
                if not isinstance(value, str) or not value.strip():
                    raise DCFError(f"equity_bridge.share_classes[{index}].{field} 必填")
            price_date = item.get("price_date")
            parsed_price_date = iso_date(price_date, f"equity_bridge.share_classes[{index}].price_date")
            if valuation_date and parsed_price_date > valuation_date:
                raise DCFError(f"equity_bridge.share_classes[{index}].price_date 晚于估值基准日")
            shares_date = item.get("shares_date")
            parsed_shares_date = None
            if shares_date is not None:
                parsed_shares_date = iso_date(shares_date, f"equity_bridge.share_classes[{index}].shares_date")
                if valuation_date and parsed_shares_date > valuation_date:
                    raise DCFError(f"equity_bridge.share_classes[{index}].shares_date 晚于估值基准日")
            price_basis = item.get("price_basis")
            if price_basis is not None and price_basis != "unadjusted_close":
                raise DCFError("分证券市值必须使用不复权收盘价 price_basis=unadjusted_close")
            shares = number(item.get("shares"), f"equity_bridge.share_classes[{index}].shares")
            price = number(item.get("price"), f"equity_bridge.share_classes[{index}].price")
            fx = number(item.get("fx_to_valuation_currency"), f"equity_bridge.share_classes[{index}].fx_to_valuation_currency")
            if shares <= 0 or price <= 0 or fx <= 0:
                raise DCFError("分证券股数、价格和汇率必须大于零")
            converted_value = shares * price * fx
            class_shares += shares
            market_cap += converted_value
            normalized = {
                    "security_id": security_id.strip(),
                    "exchange": item["exchange"].strip(),
                    "shares": shares,
                    "shares_date": shares_date,
                    "price": price,
                    "price_date": price_date,
                    "price_basis": price_basis,
                    "currency": item["currency"].strip(),
                    "fx_to_valuation_currency": fx,
                    "source_id": item["source_id"].strip(),
                    "converted_market_value": converted_value,
                }
            market_cap_fields = ("reference_market_cap", "market_cap_date", "market_cap_source_id")
            if any(item.get(field) is not None for field in market_cap_fields):
                if any(item.get(field) in (None, "") for field in market_cap_fields):
                    raise DCFError(f"equity_bridge.share_classes[{index}] 独立市值反向校验字段不完整")
                reference_market_cap = number(item.get("reference_market_cap"), f"equity_bridge.share_classes[{index}].reference_market_cap")
                tolerance_pct = number(item.get("market_cap_tolerance_pct"), f"equity_bridge.share_classes[{index}].market_cap_tolerance_pct", 0.02)
                market_cap_date = iso_date(item.get("market_cap_date"), f"equity_bridge.share_classes[{index}].market_cap_date")
                if reference_market_cap <= 0 or tolerance_pct < 0 or tolerance_pct > 0.10:
                    raise DCFError("独立市值必须大于零，市值反向校验容差必须位于0%至10%")
                if valuation_date and market_cap_date > valuation_date:
                    raise DCFError(f"equity_bridge.share_classes[{index}].market_cap_date 晚于估值基准日")
                if market_cap_date != parsed_price_date:
                    raise DCFError("独立市值日期必须与股价日期一致")
                market_cap_difference = converted_value - reference_market_cap
                market_cap_difference_pct = market_cap_difference / reference_market_cap
                if abs(market_cap_difference_pct) > tolerance_pct:
                    raise DCFError(
                        "股价×估值日股数与独立市值不一致："
                        f"security_id={security_id.strip()}, difference_pct={market_cap_difference_pct:.4%}"
                    )
                normalized.update(
                    {
                        "reference_market_cap": reference_market_cap,
                        "market_cap_date": item["market_cap_date"],
                        "market_cap_source_id": str(item["market_cap_source_id"]).strip(),
                        "market_cap_tolerance_pct": tolerance_pct,
                        "market_cap_difference": market_cap_difference,
                        "market_cap_difference_pct": market_cap_difference_pct,
                    }
                )
            normalized_classes.append(normalized)
            class_by_security[security_id.strip()] = normalized
        tolerance = max(1e-8, bridge["diluted_shares"] * 1e-6)
        if abs(class_shares - bridge["diluted_shares"]) > tolerance:
            raise DCFError(
                "分证券股数合计与完全稀释股份数不一致："
                f"share_classes={class_shares}, diluted_shares={bridge['diluted_shares']}"
            )
        bridge["share_classes"] = normalized_classes
        bridge["share_class_total_shares"] = class_shares
        bridge["current_market_cap"] = market_cap
        bridge["current_share_price_equivalent"] = market_cap / bridge["diluted_shares"]
        review = raw.get("corporate_action_review")
        if review is not None:
            if not isinstance(review, dict):
                raise DCFError("equity_bridge.corporate_action_review 必须为对象")
            baseline_date = iso_date(review.get("baseline_share_date"), "equity_bridge.corporate_action_review.baseline_share_date")
            search_start = iso_date(review.get("search_start_date"), "equity_bridge.corporate_action_review.search_start_date")
            reviewed_through = iso_date(review.get("reviewed_through_date"), "equity_bridge.corporate_action_review.reviewed_through_date")
            if search_start > baseline_date:
                raise DCFError("公司行动检索起始日不得晚于基准股本日")
            if valuation_date and reviewed_through != valuation_date:
                raise DCFError("公司行动检索截止日必须等于估值基准日")
            actions = review.get("actions")
            if not isinstance(actions, list):
                raise DCFError("equity_bridge.corporate_action_review.actions 必须为数组")
            last_effective: dict[str, tuple[date, float]] = {}
            normalized_actions: list[dict[str, Any]] = []
            for index, action in enumerate(actions):
                if not isinstance(action, dict):
                    raise DCFError(f"corporate_action_review.actions[{index}] 必须为对象")
                security = action.get("security_id")
                action_type = action.get("action_type")
                source_id = action.get("source_id")
                if not all(isinstance(value, str) and value.strip() for value in (security, action_type, source_id)):
                    raise DCFError(f"corporate_action_review.actions[{index}] 缺少证券、行动类型或来源")
                announcement_date = iso_date(action.get("announcement_date"), f"corporate_action_review.actions[{index}].announcement_date")
                effective_date = iso_date(action.get("effective_date"), f"corporate_action_review.actions[{index}].effective_date")
                before_shares = number(action.get("before_shares"), f"corporate_action_review.actions[{index}].before_shares")
                change_shares = number(action.get("change_shares"), f"corporate_action_review.actions[{index}].change_shares")
                after_shares = number(action.get("after_shares"), f"corporate_action_review.actions[{index}].after_shares")
                tolerance = max(1e-8, abs(after_shares) * 1e-6)
                if abs(before_shares + change_shares - after_shares) > tolerance:
                    raise DCFError(f"corporate_action_review.actions[{index}] 股数滚存不平")
                applied = action.get("applied_to_share_count") is True
                if valuation_date and effective_date <= valuation_date:
                    if announcement_date > valuation_date:
                        raise DCFError(f"公司行动在估值日后才公开，不得回填历史估值：{security}")
                    if not applied:
                        raise DCFError(f"估值日前已生效公司行动未计入股数：{security}")
                    security_row = class_by_security.get(security.strip())
                    if security_row and effective_date > iso_date(security_row["price_date"], f"share_classes.{security}.price_date"):
                        raise DCFError(f"{security} 股价日期早于已生效公司行动，股价与股数口径不一致")
                    prior = last_effective.get(security.strip())
                    if prior and effective_date < prior[0]:
                        raise DCFError(f"{security} 公司行动必须按生效日排序")
                    if prior and effective_date >= prior[0] and abs(before_shares - prior[1]) > tolerance:
                        raise DCFError(f"{security} 公司行动股数滚存前后不连续")
                    if not prior or effective_date >= prior[0]:
                        last_effective[security.strip()] = (effective_date, after_shares)
                normalized_actions.append({**action, "announcement_date": announcement_date.isoformat(), "effective_date": effective_date.isoformat()})
            for security, (_, after_shares) in last_effective.items():
                security_row = class_by_security.get(security)
                if security_row is None:
                    raise DCFError(f"公司行动证券未出现在share_classes：{security}")
                tolerance = max(1e-8, abs(after_shares) * 1e-6)
                if abs(security_row["shares"] - after_shares) > tolerance:
                    raise DCFError(f"{security} 估值日股数未反映最后一项已生效公司行动")
            bridge["corporate_action_review"] = {
                **review,
                "baseline_share_date": baseline_date.isoformat(),
                "search_start_date": search_start.isoformat(),
                "reviewed_through_date": reviewed_through.isoformat(),
                "actions": normalized_actions,
            }
    if raw.get("current_share_price") is not None:
        bridge["current_share_price"] = number(raw["current_share_price"], "equity_bridge.current_share_price")
    return bridge


def value_from_ev(ev: float, bridge: dict[str, Any]) -> tuple[float, float]:
    equity_value = ev + sum(bridge[k] for k in BRIDGE_ADDITIONS) - sum(bridge[k] for k in BRIDGE_CLAIMS)
    return equity_value, equity_value / bridge["diluted_shares"]


def value_scenario(payload: dict[str, Any], name: str, scenario: dict[str, Any]) -> dict[str, Any]:
    meta = payload.get("meta", {})
    convention = meta.get("discount_convention", "mid_year")
    wacc, wacc_detail = scenario_wacc(payload, scenario)
    g = number(scenario.get("terminal_growth"), f"scenarios.{name}.terminal_growth")
    if wacc <= g:
        raise DCFError(f"情景 {name}：加权平均资本成本（WACC）必须高于永续增长率（g）")
    forecast = scenario.get("forecast")
    if not isinstance(forecast, list) or len(forecast) < 2:
        raise DCFError(f"情景 {name}：显性预测期 forecast 至少包含两个期间")
    default_tax = number(scenario.get("tax_rate", payload.get("tax_rate")), f"scenarios.{name}.tax_rate")
    calculated_rows: list[dict[str, Any]] = []
    pv_forecast = 0.0
    for index, row in enumerate(forecast, start=1):
        if not isinstance(row, dict):
            raise DCFError(f"情景 {name}：预测第 {index} 行必须为对象")
        revenue = number(row.get("revenue"), f"scenarios.{name}.forecast[{index}].revenue")
        if row.get("ebit") is not None:
            ebit = number(row.get("ebit"), f"scenarios.{name}.forecast[{index}].ebit")
            ebit_margin = ebit / revenue if revenue else None
        else:
            ebit_margin = number(row.get("ebit_margin"), f"scenarios.{name}.forecast[{index}].ebit_margin")
            ebit = revenue * ebit_margin
        tax_rate = number(row.get("tax_rate"), f"scenarios.{name}.forecast[{index}].tax_rate", default_tax)
        da = number(row.get("da"), f"scenarios.{name}.forecast[{index}].da")
        capex = number(row.get("capex"), f"scenarios.{name}.forecast[{index}].capex")
        delta_nwc = number(row.get("delta_nwc"), f"scenarios.{name}.forecast[{index}].delta_nwc")
        other_noncash = number(row.get("other_noncash"), f"scenarios.{name}.forecast[{index}].other_noncash", 0.0)
        other_investment = number(row.get("other_investment"), f"scenarios.{name}.forecast[{index}].other_investment", 0.0)
        nopat = ebit * (1.0 - tax_rate)
        fcff = nopat + da - capex - delta_nwc + other_noncash - other_investment
        time = discount_time(index, row, convention)
        factor = 1.0 / ((1.0 + wacc) ** time)
        pv_fcff = fcff * factor
        pv_forecast += pv_fcff
        calculated_rows.append({
            "period": row.get("period", str(index)),
            "revenue": revenue,
            "ebit_margin": ebit_margin,
            "ebit": ebit,
            "tax_rate": tax_rate,
            "nopat": nopat,
            "da": da,
            "capex": capex,
            "delta_nwc": delta_nwc,
            "other_noncash": other_noncash,
            "other_investment": other_investment,
            "fcff": fcff,
            "discount_time": time,
            "discount_factor": factor,
            "pv_fcff": pv_fcff,
        })
    terminal_fcff = number(scenario.get("terminal_fcff"), f"scenarios.{name}.terminal_fcff", calculated_rows[-1]["fcff"])
    next_fcff = terminal_fcff * (1.0 + g)
    terminal_value = next_fcff / (wacc - g)
    terminal_time = terminal_discount_time(meta, forecast)
    terminal_factor = 1.0 / ((1.0 + wacc) ** terminal_time)
    pv_terminal = terminal_value * terminal_factor
    enterprise_value = pv_forecast + pv_terminal
    bridge = bridge_values(payload)
    equity_value, per_share = value_from_ev(enterprise_value, bridge)
    terminal_share = pv_terminal / enterprise_value if enterprise_value else None
    return {
        "name": name,
        "wacc": wacc,
        "wacc_detail": wacc_detail,
        "terminal_growth": g,
        "forecast": calculated_rows,
        "pv_forecast_fcff": pv_forecast,
        "terminal_fcff": terminal_fcff,
        "next_period_fcff": next_fcff,
        "terminal_value": terminal_value,
        "terminal_discount_time": terminal_time,
        "terminal_discount_factor": terminal_factor,
        "pv_terminal_value": pv_terminal,
        "enterprise_value": enterprise_value,
        "equity_bridge": bridge,
        "equity_value": equity_value,
        "per_share_value": per_share,
        "terminal_value_share_of_ev": terminal_share,
    }


def sensitivity_rates(payload: dict[str, Any], base: dict[str, Any]) -> tuple[list[float], list[float]]:
    supplied = payload.get("sensitivity", {})
    wacc_rates = supplied.get("wacc_rates")
    growth_rates = supplied.get("terminal_growth_rates")
    if wacc_rates is None:
        wacc_rates = [base["wacc"] + delta for delta in (-0.02, -0.01, 0.0, 0.01, 0.02)]
    if growth_rates is None:
        growth_rates = [base["terminal_growth"] + delta for delta in (-0.01, -0.005, 0.0, 0.005, 0.01)]
    wacc_rates = sorted(number(x, "sensitivity.wacc_rates") for x in wacc_rates)
    growth_rates = sorted(number(x, "sensitivity.terminal_growth_rates") for x in growth_rates)
    return wacc_rates, growth_rates


def build_sensitivity(payload: dict[str, Any], base: dict[str, Any]) -> dict[str, Any]:
    bridge = base["equity_bridge"]
    terminal_time = base["terminal_discount_time"]
    wacc_rates, growth_rates = sensitivity_rates(payload, base)
    rows = []
    for g in growth_rates:
        values = []
        for wacc in wacc_rates:
            if wacc <= g:
                values.append(None)
                continue
            pv_forecast = sum(row["fcff"] / ((1.0 + wacc) ** row["discount_time"]) for row in base["forecast"])
            terminal_value = base["terminal_fcff"] * (1.0 + g) / (wacc - g)
            pv_terminal = terminal_value / ((1.0 + wacc) ** terminal_time)
            _, per_share = value_from_ev(pv_forecast + pv_terminal, bridge)
            values.append(per_share)
        rows.append({"terminal_growth": g, "per_share_values": values})
    return {"wacc_rates": wacc_rates, "rows": rows}


def reverse_implied_growth(base: dict[str, Any]) -> dict[str, Any] | None:
    bridge = base["equity_bridge"]
    market_cap = bridge.get("current_market_cap")
    price = bridge.get("current_share_price")
    if market_cap is None and price is None:
        return None
    target_equity = market_cap if market_cap is not None else price * bridge["diluted_shares"]
    target_ev = target_equity - sum(bridge[k] for k in BRIDGE_ADDITIONS) + sum(bridge[k] for k in BRIDGE_CLAIMS)
    wacc = base["wacc"]
    terminal_time = base["terminal_discount_time"]
    pv_forecast = base["pv_forecast_fcff"]
    required_pv_terminal = target_ev - pv_forecast
    if required_pv_terminal <= 0 or base["terminal_fcff"] <= 0:
        return {"target_enterprise_value": target_ev, "implied_terminal_growth": None, "reason": "不存在具有经济意义的单变量解"}

    def residual(g: float) -> float:
        tv = base["terminal_fcff"] * (1.0 + g) / (wacc - g)
        return tv / ((1.0 + wacc) ** terminal_time) - required_pv_terminal

    low, high = -0.05, wacc - 0.0025
    if residual(low) > 0 or residual(high) < 0:
        return {"target_enterprise_value": target_ev, "implied_terminal_growth": None, "reason": "隐含值超出预设的合理求解区间"}
    for _ in range(120):
        mid = (low + high) / 2.0
        if residual(mid) > 0:
            high = mid
        else:
            low = mid
    return {"target_enterprise_value": target_ev, "implied_terminal_growth": (low + high) / 2.0, "reason": None}


def calculate(payload: dict[str, Any]) -> dict[str, Any]:
    scenarios_raw = payload.get("scenarios")
    if not isinstance(scenarios_raw, dict) or not scenarios_raw:
        raise DCFError("情景集合 scenarios 必须为非空对象")
    results = {name: value_scenario(payload, name, scenario) for name, scenario in scenarios_raw.items()}
    base_name = "base" if "base" in results else next(iter(results))
    base = results[base_name]
    warnings: list[str] = []
    for name, result in results.items():
        display_name = scenario_zh(name)
        if result["wacc"] - result["terminal_growth"] < 0.005:
            warnings.append(f"{display_name}：加权平均资本成本（WACC）与永续增长率之差低于50个基点")
        share = result["terminal_value_share_of_ev"]
        if share is not None and share > 0.75:
            warnings.append(f"{display_name}：终值占企业价值的比例超过75%，估值对长期假设较敏感")
        if result["equity_value"] <= 0:
            warnings.append(f"{display_name}：普通股权益价值为零或负数")
    return {
        "meta": payload.get("meta", {}),
        "base_scenario": base_name,
        "scenarios": results,
        "sensitivity": build_sensitivity(payload, base),
        "reverse_dcf": reverse_implied_growth(base),
        "warnings": warnings,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Calculate an FCFF DCF from normalized JSON")
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    result = calculate(payload)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
