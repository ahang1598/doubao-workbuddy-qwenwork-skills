#!/usr/bin/env python3
"""Run a transparent equity screen with filters, winsorized z-scores, and near misses."""

import datetime as dt
import argparse
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path



def emit(message):
    sys.stderr.write("%s\n" % message)


def finite(name, value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s 必须为有限数" % name)
    return number


def quantile(values, probability):
    if not values:
        raise ValueError("quantile 需要非空数组")
    if not 0 <= probability <= 1:
        raise ValueError("winsor 分位数必须在 [0,1]")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = probability * (len(ordered) - 1)
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def compare(value, operator, expected):
    if operator == ">":
        return value > expected
    if operator == ">=":
        return value >= expected
    if operator == "<":
        return value < expected
    if operator == "<=":
        return value <= expected
    if operator == "==":
        return value == expected
    if operator == "!=":
        return value != expected
    if operator == "in":
        if not isinstance(expected, list):
            raise ValueError("in 的过滤值必须是数组")
        return value in expected
    if operator == "not_in":
        if not isinstance(expected, list):
            raise ValueError("not_in 的过滤值必须是数组")
        return value not in expected
    raise ValueError("不支持的过滤运算符: %s" % operator)


def apply_filters(candidate, filters):
    failures = []
    for index, rule in enumerate(filters):
        field = str(rule.get("field", "")).strip()
        operator = str(rule.get("op", "")).strip()
        if not field or not operator or "value" not in rule:
            raise ValueError("filters[%d] 缺少 field/op/value" % index)
        actual = candidate.get(field)
        passed = actual is not None and compare(actual, operator, rule["value"])
        if not passed:
            failures.append({
                "field": field,
                "op": operator,
                "expected": rule["value"],
                "actual": actual,
            })
    return failures


def prepare_factors(candidates, factors, group_by):
    prepared = {}
    diagnostics = []
    for index, factor in enumerate(factors):
        field = str(factor.get("field", "")).strip()
        if not field or field in prepared:
            raise ValueError("factor field 缺失或重复: %s" % field)
        direction = factor.get("direction", "high")
        if direction not in {"high", "low"}:
            raise ValueError("factor direction 只允许 high/low: %s" % field)
        weight = finite("factors[%d].weight" % index, factor.get("weight", 1.0))
        if weight < 0:
            raise ValueError("factor weight 不得为负；方向请使用 high/low 表达: %s" % field)
        winsor = factor.get("winsor", [0.0, 1.0])
        if not isinstance(winsor, list) or len(winsor) != 2:
            raise ValueError("factor.winsor 必须是 [lower, upper]")
        lower_p = finite("winsor.lower", winsor[0])
        upper_p = finite("winsor.upper", winsor[1])
        if not 0 <= lower_p <= upper_p <= 1:
            raise ValueError("winsor 必须满足 0<=lower<=upper<=1")
        raw_values = []
        for candidate in candidates:
            value = candidate.get(field)
            if value is not None:
                raw_values.append(finite("%s.%s" % (candidate["ticker"], field), value))
        if not raw_values:
            raise ValueError("因子 %s 没有任何可用值" % field)
        lower = quantile(raw_values, lower_p)
        upper = quantile(raw_values, upper_p)

        winsorized = {}
        for candidate in candidates:
            value = candidate.get(field)
            if value is not None:
                number = finite("%s.%s" % (candidate["ticker"], field), value)
                winsorized[candidate["ticker"]] = min(max(number, lower), upper)

        groups = defaultdict(list)
        for candidate in candidates:
            ticker = candidate["ticker"]
            if ticker in winsorized:
                group = str(candidate.get(group_by, "UNCLASSIFIED")) if group_by else "ALL"
                groups[group].append(winsorized[ticker])
        group_stats = {}
        for group, values in groups.items():
            mean = statistics.fmean(values)
            std = statistics.pstdev(values) if len(values) >= 2 else 0.0
            group_stats[group] = {"mean": mean, "population_std": std, "count": len(values)}
            if len(values) < 2 or std == 0:
                diagnostics.append(
                    "因子 %s 的分组 %s 样本不足或方差为 0，标准分记为 0。" % (field, group)
                )
        required = factor.get("required", False)
        if not isinstance(required, bool):
            raise ValueError("factor.required 必须为 JSON 布尔值: %s" % field)
        prepared[field] = {
            "direction": direction,
            "weight": weight,
            "required": required,
            "winsor_limits": [lower, upper],
            "winsor_percentiles": [lower_p, upper_p],
            "winsorized": winsorized,
            "group_stats": group_stats,
        }
    return prepared, sorted(set(diagnostics))


def score_candidates(candidates, prepared, group_by, missing_policy):
    if missing_policy not in {"reweight", "zero"}:
        raise ValueError("missing_policy 只允许 reweight/zero")
    total_abs_weight = sum(abs(item["weight"]) for item in prepared.values())
    if total_abs_weight == 0:
        raise ValueError("因子绝对权重之和必须大于 0")
    scored = []
    excluded_missing = []
    for candidate in candidates:
        ticker = candidate["ticker"]
        missing_required = [
            field for field, factor in prepared.items()
            if factor["required"] and ticker not in factor["winsorized"]
        ]
        if missing_required:
            excluded_missing.append({"ticker": ticker, "missing_required_factors": missing_required})
            continue
        contributions = []
        raw_score = 0.0
        used_abs_weight = 0.0
        for field, factor in prepared.items():
            raw = candidate.get(field)
            if ticker not in factor["winsorized"]:
                contributions.append({
                    "factor": field,
                    "raw": raw,
                    "winsorized": None,
                    "z_score": None,
                    "directional_z": None,
                    "weight": factor["weight"],
                    "contribution": 0.0,
                    "status": "missing",
                })
                if missing_policy == "zero":
                    used_abs_weight += abs(factor["weight"])
                continue
            group = str(candidate.get(group_by, "UNCLASSIFIED")) if group_by else "ALL"
            stats = factor["group_stats"][group]
            value = factor["winsorized"][ticker]
            z_score = (value - stats["mean"]) / stats["population_std"] if stats["population_std"] else 0.0
            directional_z = z_score if factor["direction"] == "high" else -z_score
            contribution = directional_z * factor["weight"]
            raw_score += contribution
            used_abs_weight += abs(factor["weight"])
            contributions.append({
                "factor": field,
                "raw": finite("%s.%s" % (ticker, field), raw),
                "winsorized": value,
                "group": group,
                "group_mean": stats["mean"],
                "group_population_std": stats["population_std"],
                "z_score": z_score,
                "directional_z": directional_z,
                "weight": factor["weight"],
                "contribution": contribution,
                "status": "used",
            })
        if used_abs_weight == 0:
            excluded_missing.append({"ticker": ticker, "missing_required_factors": ["all factors"]})
            continue
        score = (
            raw_score * total_abs_weight / used_abs_weight
            if missing_policy == "reweight" else raw_score
        )
        scored.append({
            "ticker": ticker,
            "name": candidate.get("name"),
            "group": candidate.get(group_by) if group_by else None,
            "score": score,
            "raw_score_before_missing_reweight": raw_score,
            "used_abs_weight": used_abs_weight,
            "total_abs_weight": total_abs_weight,
            "factor_contributions": contributions,
        })
    scored.sort(key=lambda item: (-item["score"], item["ticker"]))
    for rank, item in enumerate(scored, 1):
        item["rank"] = rank
    return scored, excluded_missing


def compute(data):
    as_of = str(data.get("as_of", "")).strip()
    if not as_of:
        raise ValueError("as_of 缺失；筛选必须锁定数据时点")
    try:
        dt.date.fromisoformat(as_of)
    except ValueError as exc:
        raise ValueError("as_of 必须为 YYYY-MM-DD") from exc
    raw_candidates = data.get("candidates")
    if not isinstance(raw_candidates, list) or not raw_candidates:
        raise ValueError("candidates 必须是非空数组")
    candidates = []
    seen = set()
    for index, raw in enumerate(raw_candidates):
        if not isinstance(raw, dict):
            raise ValueError("candidates[%d] 必须是对象" % index)
        ticker = str(raw.get("ticker", "")).strip()
        if not ticker or ticker in seen:
            raise ValueError("ticker 缺失或重复: %s" % ticker)
        seen.add(ticker)
        candidate = dict(raw)
        candidate["ticker"] = ticker
        candidates.append(candidate)
    filters = data.get("filters") or []
    factors = data.get("factors")
    if not isinstance(factors, list) or not factors:
        raise ValueError("factors 必须是非空数组")

    eligible = []
    rejected = []
    near_misses = []
    for candidate in candidates:
        failures = apply_filters(candidate, filters)
        if failures:
            item = {"ticker": candidate["ticker"], "failed_filters": failures}
            rejected.append(item)
            if len(failures) == 1:
                near_misses.append(item)
        else:
            eligible.append(candidate)
    if not eligible:
        return {
            "as_of": as_of,
            "universe_count": len(candidates),
            "eligible_count": 0,
            "ranked_count": 0,
            "funnel": [
                {"stage": "universe", "count": len(candidates)},
                {"stage": "hard_filters", "count": 0},
            ],
            "ranked": [],
            "near_misses": near_misses,
            "rejected": rejected,
            "warnings": ["硬过滤后没有候选，未运行因子排名。"],
        }

    group_by = data.get("group_by")
    prepared, diagnostics = prepare_factors(eligible, factors, group_by)
    scored, excluded_missing = score_candidates(
        eligible, prepared, group_by, data.get("missing_policy", "reweight")
    )
    top_n = int(data.get("top_n", len(scored)))
    if top_n < 1:
        raise ValueError("top_n 必须为正整数")
    factor_methodology = {}
    for field, item in prepared.items():
        factor_methodology[field] = {
            "direction": item["direction"],
            "weight": item["weight"],
            "required": item["required"],
            "winsor_percentiles": item["winsor_percentiles"],
            "winsor_limits": item["winsor_limits"],
            "group_statistics": item["group_stats"],
        }
    return {
        "as_of": as_of,
        "universe_count": len(candidates),
        "eligible_count": len(eligible),
        "ranked_count": len(scored),
        "selected_count": min(top_n, len(scored)),
        "funnel": [
            {"stage": "universe", "count": len(candidates)},
            {"stage": "hard_filters", "count": len(eligible)},
            {"stage": "complete_required_factors", "count": len(scored)},
            {"stage": "top_n", "count": min(top_n, len(scored))},
        ],
        "factor_methodology": factor_methodology,
        "ranked": scored[:top_n],
        "all_scored": scored,
        "near_misses": near_misses,
        "rejected": rejected,
        "excluded_missing_required": excluded_missing,
        "warnings": diagnostics,
        "method_note": (
            "先硬过滤，再对可用样本做分位数缩尾与总体标准差 z-score；"
            "可选分组内标准化；缺失值按声明策略处理。排名不是投资建议。"
        ),
    }


def self_test():
    fixture = {
        "as_of": "2026-06-30",
        "candidates": [
            {"ticker": "A", "sector": "Tech", "market_cap": 100, "growth": 0.30, "pe": 15},
            {"ticker": "B", "sector": "Tech", "market_cap": 120, "growth": 0.10, "pe": 30},
            {"ticker": "C", "sector": "Industrial", "market_cap": 90, "growth": 0.20, "pe": 12},
            {"ticker": "D", "sector": "Industrial", "market_cap": 40, "growth": 0.50, "pe": 8},
        ],
        "filters": [{"field": "market_cap", "op": ">=", "value": 50}],
        "factors": [
            {"field": "growth", "direction": "high", "weight": 0.6, "winsor": [0, 1], "required": True},
            {"field": "pe", "direction": "low", "weight": 0.4, "winsor": [0, 1], "required": True},
        ],
        "top_n": 2,
    }
    result = compute(fixture)
    if result["eligible_count"] != 3 or result["selected_count"] != 2:
        raise AssertionError(result)
    if result["near_misses"][0]["ticker"] != "D":
        raise AssertionError(result)
    if result["ranked"][0]["ticker"] not in {"A", "C"}:
        raise AssertionError(result)
    if not all("factor_contributions" in item for item in result["ranked"]):
        raise AssertionError(result)
    emit("SELF_TEST_PASS")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="运行透明的股票硬过滤、缩尾 z-score 排名和近失候选分析。"
    )
    parser.add_argument("input_json", nargs="?")
    parser.add_argument("--output")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        self_test()
        return 0
    if not args.input_json or not args.output:
        parser.error("需要 input_json 和 --output，或使用 --self-test")
    try:
        data = json.loads(Path(args.input_json).read_text(encoding="utf-8"))
        result = compute(data)
    except Exception as exc:
        emit("[错误] %s" % exc)
        return 1
    payload = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    Path(args.output).write_text(payload + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
