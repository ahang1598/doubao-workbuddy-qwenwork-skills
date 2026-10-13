#!/usr/bin/env python3
"""Compute portfolio concentration, correlations, beta, liquidity, and stress loss."""

import argparse
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

from market_analysis import beta, correlation


def emit(message):
    sys.stderr.write("%s\n" % message)


def parse_return_series(items):
    values = {}
    for item in items or []:
        day = str(item["date"])
        value = float(item["return"])
        if not math.isfinite(value):
            raise ValueError("return 必须为有限数")
        values[day] = value
    return values


def hhi(weights):
    return sum(value * value for value in weights)


def aligned_pair(left, right, window=None):
    days = sorted(set(left).intersection(right))
    if window:
        days = days[-int(window):]
    return [left[d] for d in days], [right[d] for d in days], days


def correlation_matrix(series_by_ticker, tickers, window):
    matrix = {}
    sample_sizes = {}
    for left in tickers:
        matrix[left] = {}
        sample_sizes[left] = {}
        for right in tickers:
            a, b, days = aligned_pair(series_by_ticker.get(left, {}), series_by_ticker.get(right, {}), window)
            matrix[left][right] = 1.0 if left == right and len(days) >= 3 else correlation(a, b)
            sample_sizes[left][right] = len(days)
    return matrix, sample_sizes


def portfolio_series(positions, series_by_ticker):
    tickers = [item["ticker"] for item in positions]
    if not tickers:
        return {}
    common = None
    for ticker in tickers:
        days = set(series_by_ticker.get(ticker, {}))
        common = days if common is None else common.intersection(days)
    result = {}
    for day in sorted(common or []):
        result[day] = sum(
            float(item["weight"]) * series_by_ticker[item["ticker"]][day]
            for item in positions
        )
    return result


def compute(data):
    positions = data.get("positions")
    if not isinstance(positions, list) or not positions:
        raise ValueError("positions 必须是非空数组")
    tickers = []
    weights = []
    seen = set()
    for item in positions:
        ticker = str(item.get("ticker", "")).strip()
        if not ticker or ticker in seen:
            raise ValueError("ticker 缺失或重复: %s" % ticker)
        seen.add(ticker)
        weight = float(item["weight"])
        if not math.isfinite(weight):
            raise ValueError("weight 必须为有限数")
        tickers.append(ticker)
        weights.append(weight)

    gross = sum(abs(value) for value in weights)
    net = sum(weights)
    if gross <= 0:
        raise ValueError("gross exposure 必须大于 0")
    absolute_shares = [abs(value) / gross for value in weights]
    security_hhi = hhi(absolute_shares)

    signed_clusters = defaultdict(float)
    gross_clusters = defaultdict(float)
    for item, weight in zip(positions, weights):
        cluster = str(item.get("cluster") or "UNCLASSIFIED")
        signed_clusters[cluster] += weight
        gross_clusters[cluster] += abs(weight)
    signed_cluster_hhi = hhi(value / gross for value in signed_clusters.values())
    gross_cluster_hhi = hhi(value / gross for value in gross_clusters.values())

    result = {
        "exposure": {"net": net, "gross": gross},
        "concentration": {
            "security_hhi": security_hhi,
            "effective_positions": 1.0 / security_hhi if security_hhi else None,
            "signed_cluster_hhi": signed_cluster_hhi,
            "gross_cluster_hhi": gross_cluster_hhi,
            "gross_cluster_weights": {
                key: value / gross for key, value in sorted(gross_clusters.items())
            },
            "note": "HHI 衡量权重集中，不替代相关性或压力损失。",
        },
    }

    participation = float(data.get("participation_rate", 0.20))
    if not 0 < participation <= 1:
        raise ValueError("participation_rate 必须在 (0,1] 内")
    liquidity = {}
    for item in positions:
        if item.get("shares") is not None and item.get("adv_shares") is not None:
            shares = abs(float(item["shares"]))
            adv = float(item["adv_shares"])
            liquidity[item["ticker"]] = {
                "liquidation_days": shares / (participation * adv) if adv > 0 else None,
                "participation_rate": participation,
            }
    if liquidity:
        result["liquidity"] = liquidity

    raw_returns = data.get("returns", {})
    if raw_returns:
        series_by_ticker = {
            ticker: parse_return_series(raw_returns.get(ticker, []))
            for ticker in tickers
        }
        windows = [int(value) for value in data.get("correlation_windows", [60, 250])]
        if not windows or any(value < 3 for value in windows):
            raise ValueError("correlation_windows 必须为不小于 3 的正整数")
        result["correlations"] = {}
        for window in windows:
            matrix, sizes = correlation_matrix(series_by_ticker, tickers, window)
            result["correlations"][str(window)] = {
                "matrix": matrix, "sample_sizes": sizes
            }

        portfolio = portfolio_series(positions, series_by_ticker)
        benchmark = parse_return_series(data.get("benchmark", []))
        if portfolio and benchmark:
            p_values, b_values, days = aligned_pair(portfolio, benchmark)
            result["portfolio_beta"] = {
                "beta": beta(p_values, b_values),
                "correlation": correlation(p_values, b_values),
                "sample_size": len(days),
            }

    scenarios = []
    for scenario in data.get("scenarios", []):
        shocks = scenario.get("shocks", {})
        missing = [ticker for ticker in tickers if ticker not in shocks]
        pnl = sum(
            float(item["weight"]) * float(shocks.get(item["ticker"], 0.0))
            for item in positions
        )
        scenarios.append({
            "name": scenario.get("name", "unnamed"),
            "portfolio_return": pnl,
            "missing_shocks": missing,
        })
    if scenarios:
        result["scenarios"] = scenarios
    return result


def self_test():
    fixture = {
        "positions": [
            {"ticker": "A", "weight": 0.6, "cluster": "X", "shares": 100, "adv_shares": 1000},
            {"ticker": "B", "weight": 0.4, "cluster": "X", "shares": 100, "adv_shares": 500},
        ],
        "returns": {
            "A": [
                {"date": "1", "return": 0.01}, {"date": "2", "return": 0.02},
                {"date": "3", "return": -0.01}, {"date": "4", "return": 0.00},
            ],
            "B": [
                {"date": "1", "return": 0.00}, {"date": "2", "return": 0.01},
                {"date": "3", "return": -0.02}, {"date": "4", "return": 0.01},
            ],
        },
        "benchmark": [
            {"date": "1", "return": 0.005}, {"date": "2", "return": 0.015},
            {"date": "3", "return": -0.01}, {"date": "4", "return": 0.005},
        ],
        "correlation_windows": [4],
        "participation_rate": 0.2,
        "scenarios": [{"name": "down", "shocks": {"A": -0.1, "B": -0.2}}],
    }
    result = compute(fixture)
    if abs(result["concentration"]["security_hhi"] - 0.52) > 1e-12:
        raise AssertionError(result)
    if abs(result["scenarios"][0]["portfolio_return"] + 0.14) > 1e-12:
        raise AssertionError(result)
    if abs(result["liquidity"]["A"]["liquidation_days"] - 0.5) > 1e-12:
        raise AssertionError(result)
    emit("SELF_TEST_PASS")


def main(argv=None):
    parser = argparse.ArgumentParser(description="计算组合集中度、相关性、Beta、流动性和压力损失。")
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
