#!/usr/bin/env python3
"""Compute market and stock price-analysis metrics from local JSON input."""

import argparse
import json
import math
import statistics
import sys
from datetime import date
from pathlib import Path



def emit(message):
    sys.stderr.write("%s\n" % message)


def finite(name, value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s 必须为有限数" % name)
    return number


def iso_date(name, value):
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError("%s 必须为 YYYY-MM-DD" % name) from exc


def parse_series(items, name="series"):
    if not isinstance(items, list) or len(items) < 2:
        raise ValueError("%s 至少需要两个价格观测" % name)
    points = []
    previous_day = None
    seen = set()
    for idx, raw in enumerate(items):
        if not isinstance(raw, dict):
            raise ValueError("%s[%s] 必须是对象" % (name, idx))
        day = iso_date("%s[%s].date" % (name, idx), raw.get("date"))
        if day in seen:
            raise ValueError("%s 包含重复日期: %s" % (name, day.isoformat()))
        if previous_day is not None and day <= previous_day:
            raise ValueError("%s 必须按日期严格递增" % name)
        close = finite("%s[%s].close" % (name, idx), raw.get("close"))
        if close <= 0:
            raise ValueError("%s[%s].close 必须为正" % (name, idx))
        item = {"close": close}
        for field in ("open", "high", "low", "volume", "amount", "turnover_rate"):
            if raw.get(field) is not None:
                value = finite("%s[%s].%s" % (name, idx, field), raw[field])
                if field in {"open", "high", "low"} and value <= 0:
                    raise ValueError("%s[%s].%s 必须为正" % (name, idx, field))
                if field in {"volume", "amount", "turnover_rate"} and value < 0:
                    raise ValueError("%s[%s].%s 不得为负" % (name, idx, field))
                item[field] = value
        if "high" in item:
            candidates = [item["close"]]
            if "open" in item:
                candidates.append(item["open"])
            if "low" in item:
                candidates.append(item["low"])
            if item["high"] < max(candidates):
                raise ValueError("%s[%s].high 低于 open/low/close" % (name, idx))
        if "low" in item:
            candidates = [item["close"]]
            if "open" in item:
                candidates.append(item["open"])
            if "high" in item:
                candidates.append(item["high"])
            if item["low"] > min(candidates):
                raise ValueError("%s[%s].low 高于 open/high/close" % (name, idx))
        points.append((day, item))
        seen.add(day)
        previous_day = day
    return points


def slice_series(series, start_date=None, end_date=None):
    start = iso_date("analysis.start_date", start_date) if start_date else series[0][0]
    end = iso_date("analysis.end_date", end_date) if end_date else series[-1][0]
    if start > end:
        raise ValueError("analysis.start_date 不得晚于 end_date")
    sliced = [point for point in series if start <= point[0] <= end]
    if len(sliced) < 2:
        raise ValueError("分析窗口内至少需要两个价格观测")
    return sliced


def daily_returns(series):
    return [
        (series[idx][0], series[idx][1]["close"] / series[idx - 1][1]["close"] - 1.0)
        for idx in range(1, len(series))
    ]


def total_return(series):
    return series[-1][1]["close"] / series[0][1]["close"] - 1.0


def annualized_volatility(series, annualization):
    values = [value for _, value in daily_returns(series)]
    if len(values) < 2:
        return None
    return statistics.stdev(values) * math.sqrt(annualization)


def correlation(left, right):
    if len(left) < 3 or len(left) != len(right):
        return None
    mean_left = statistics.fmean(left)
    mean_right = statistics.fmean(right)
    numerator = sum((x - mean_left) * (y - mean_right) for x, y in zip(left, right))
    denominator = math.sqrt(
        sum((x - mean_left) ** 2 for x in left)
        * sum((y - mean_right) ** 2 for y in right)
    )
    return numerator / denominator if denominator else None


def beta(asset_returns, benchmark_returns):
    if len(asset_returns) < 3 or len(asset_returns) != len(benchmark_returns):
        return None
    mean_asset = statistics.fmean(asset_returns)
    mean_benchmark = statistics.fmean(benchmark_returns)
    variance = sum((value - mean_benchmark) ** 2 for value in benchmark_returns)
    if variance == 0:
        return None
    covariance = sum(
        (asset - mean_asset) * (benchmark - mean_benchmark)
        for asset, benchmark in zip(asset_returns, benchmark_returns)
    )
    return covariance / variance


def max_drawdown_detail(series):
    peak_idx = 0
    worst = 0.0
    worst_peak_idx = 0
    worst_trough_idx = 0
    for idx, (_, item) in enumerate(series):
        if item["close"] > series[peak_idx][1]["close"]:
            peak_idx = idx
        drawdown = item["close"] / series[peak_idx][1]["close"] - 1.0
        if drawdown < worst:
            worst = drawdown
            worst_peak_idx = peak_idx
            worst_trough_idx = idx
    recovery_idx = None
    peak_price = series[worst_peak_idx][1]["close"]
    for idx in range(worst_trough_idx + 1, len(series)):
        if series[idx][1]["close"] >= peak_price:
            recovery_idx = idx
            break
    return {
        "max_drawdown": worst,
        "peak_date": series[worst_peak_idx][0].isoformat(),
        "peak_close": peak_price,
        "trough_date": series[worst_trough_idx][0].isoformat(),
        "trough_close": series[worst_trough_idx][1]["close"],
        "trading_days_peak_to_trough": worst_trough_idx - worst_peak_idx,
        "recovery_date": series[recovery_idx][0].isoformat() if recovery_idx is not None else None,
        "recovered_within_window": recovery_idx is not None,
    }


def path_statistics(series, annualization):
    returns = daily_returns(series)
    return_values = [value for _, value in returns]
    best = max(returns, key=lambda item: item[1])
    worst = min(returns, key=lambda item: item[1])
    highest = max(series, key=lambda item: item[1]["close"])
    lowest = min(series, key=lambda item: item[1]["close"])
    up_days = sum(value > 0 for value in return_values)
    flat_days = sum(value == 0 for value in return_values)
    return {
        "start_date": series[0][0].isoformat(),
        "end_date": series[-1][0].isoformat(),
        "calendar_days": (series[-1][0] - series[0][0]).days,
        "price_observations": len(series),
        "return_observations": len(returns),
        "start_close": series[0][1]["close"],
        "end_close": series[-1][1]["close"],
        "total_return": total_return(series),
        "annualized_volatility": annualized_volatility(series, annualization),
        "highest_close": highest[1]["close"],
        "highest_close_date": highest[0].isoformat(),
        "lowest_close": lowest[1]["close"],
        "lowest_close_date": lowest[0].isoformat(),
        "current_drawdown_from_period_high": series[-1][1]["close"] / highest[1]["close"] - 1.0,
        "position_in_period_range": (
            (series[-1][1]["close"] - lowest[1]["close"])
            / (highest[1]["close"] - lowest[1]["close"])
            if highest[1]["close"] != lowest[1]["close"] else None
        ),
        "best_day": {"date": best[0].isoformat(), "return": best[1]},
        "worst_day": {"date": worst[0].isoformat(), "return": worst[1]},
        "up_day_share": up_days / len(returns),
        "flat_day_share": flat_days / len(returns),
        "drawdown": max_drawdown_detail(series),
    }


def aligned_prices(asset, benchmark):
    asset_map = {day: item for day, item in asset}
    benchmark_map = {day: item for day, item in benchmark}
    common = sorted(set(asset_map).intersection(benchmark_map))
    return (
        [(day, asset_map[day]) for day in common],
        [(day, benchmark_map[day]) for day in common],
    )


def benchmark_comparison(asset, benchmark, annualization):
    aligned_asset, aligned_benchmark = aligned_prices(asset, benchmark)
    if len(aligned_asset) < 2:
        return {"status": "insufficient_common_dates", "common_price_observations": len(aligned_asset)}
    asset_return = total_return(aligned_asset)
    benchmark_return = total_return(aligned_benchmark)
    asset_daily = [value for _, value in daily_returns(aligned_asset)]
    benchmark_daily = [value for _, value in daily_returns(aligned_benchmark)]
    positive = [(a, b) for a, b in zip(asset_daily, benchmark_daily) if b > 0]
    negative = [(a, b) for a, b in zip(asset_daily, benchmark_daily) if b < 0]

    def capture(pairs):
        if not pairs:
            return None
        asset_mean = statistics.fmean(item[0] for item in pairs)
        benchmark_mean = statistics.fmean(item[1] for item in pairs)
        return asset_mean / benchmark_mean if benchmark_mean != 0 else None

    relative_wealth = (1.0 + asset_return) / (1.0 + benchmark_return) - 1.0
    return {
        "status": "available",
        "comparison_start_date": aligned_asset[0][0].isoformat(),
        "comparison_end_date": aligned_asset[-1][0].isoformat(),
        "common_price_observations": len(aligned_asset),
        "common_return_observations": len(asset_daily),
        "asset_total_return": asset_return,
        "benchmark_total_return": benchmark_return,
        "arithmetic_excess_return": asset_return - benchmark_return,
        "relative_wealth_return": relative_wealth,
        "correlation": correlation(asset_daily, benchmark_daily),
        "beta": beta(asset_daily, benchmark_daily),
        "up_capture": capture(positive),
        "down_capture": capture(negative),
        "asset_annualized_volatility": annualized_volatility(aligned_asset, annualization),
        "benchmark_annualized_volatility": annualized_volatility(aligned_benchmark, annualization),
    }


def numeric_field_values(series, field):
    return [(day, item[field]) for day, item in series if item.get(field) is not None]


def liquidity_metric(series, field, baseline_days):
    values = numeric_field_values(series, field)
    if len(values) < 2:
        return {"status": "unavailable", "observations": len(values)}
    raw = [value for _, value in values]
    result = {
        "status": "available",
        "observations": len(values),
        "mean": statistics.fmean(raw),
        "median": statistics.median(raw),
        "minimum": min(raw),
        "maximum": max(raw),
    }
    n = int(baseline_days)
    if n > 0 and len(raw) >= 2 * n:
        previous = raw[-2 * n:-n]
        latest = raw[-n:]
        previous_mean = statistics.fmean(previous)
        latest_mean = statistics.fmean(latest)
        result["latest_window"] = {
            "days": n,
            "previous_mean": previous_mean,
            "latest_mean": latest_mean,
            "ratio_to_previous": latest_mean / previous_mean if previous_mean != 0 else None,
        }
    else:
        result["latest_window"] = {
            "days": n,
            "status": "insufficient_data",
            "required_observations": 2 * n,
        }
    if len(raw) >= 3:
        mean = statistics.fmean(raw)
        std = statistics.stdev(raw)
        ranked = sorted(
            [
                {
                    "date": day.isoformat(),
                    "value": value,
                    "z_score": (value - mean) / std if std else None,
                }
                for day, value in values
            ],
            key=lambda item: item["value"],
            reverse=True,
        )[:5]
        result["top_spikes"] = ranked
    return result


def liquidity_statistics(series, baseline_days):
    return {
        "amount": liquidity_metric(series, "amount", baseline_days),
        "volume": liquidity_metric(series, "volume", baseline_days),
        "turnover_rate": liquidity_metric(series, "turnover_rate", baseline_days),
        "preferred_activity_metric": (
            "amount" if len(numeric_field_values(series, "amount")) >= 2
            else "turnover_rate" if len(numeric_field_values(series, "turnover_rate")) >= 2
            else "volume" if len(numeric_field_values(series, "volume")) >= 2
            else None
        ),
    }


def directional_turning_points(series, threshold):
    if threshold <= 0 or threshold >= 1:
        raise ValueError("analysis.phase_threshold 必须在 0 与 1 之间")
    if len(series) < 3:
        return [0, len(series) - 1]
    turning = [0]
    mode = None
    high_idx = 0
    low_idx = 0
    for idx in range(1, len(series)):
        close = series[idx][1]["close"]
        if close >= series[high_idx][1]["close"]:
            high_idx = idx
        if close <= series[low_idx][1]["close"]:
            low_idx = idx
        if mode is None:
            if close / series[high_idx][1]["close"] - 1.0 <= -threshold:
                if high_idx != turning[-1]:
                    turning.append(high_idx)
                mode = "down"
                low_idx = idx
            elif close / series[low_idx][1]["close"] - 1.0 >= threshold:
                if low_idx != turning[-1]:
                    turning.append(low_idx)
                mode = "up"
                high_idx = idx
        elif mode == "up":
            if close >= series[high_idx][1]["close"]:
                high_idx = idx
            elif close / series[high_idx][1]["close"] - 1.0 <= -threshold:
                if high_idx != turning[-1]:
                    turning.append(high_idx)
                mode = "down"
                low_idx = idx
        else:
            if close <= series[low_idx][1]["close"]:
                low_idx = idx
            elif close / series[low_idx][1]["close"] - 1.0 >= threshold:
                if low_idx != turning[-1]:
                    turning.append(low_idx)
                mode = "up"
                high_idx = idx
    if turning[-1] != len(series) - 1:
        turning.append(len(series) - 1)
    return sorted(set(turning))


def phase_statistics(series, threshold):
    points = directional_turning_points(series, threshold)
    phases = []
    for phase_id, (start_idx, end_idx) in enumerate(zip(points[:-1], points[1:]), start=1):
        subset = series[start_idx:end_idx + 1]
        change = total_return(subset)
        highest = max(subset, key=lambda item: item[1]["close"])
        lowest = min(subset, key=lambda item: item[1]["close"])
        if change > 0:
            direction = "up"
        elif change < 0:
            direction = "down"
        else:
            direction = "flat"
        activity_field = (
            "amount" if len(numeric_field_values(subset, "amount")) >= 2
            else "turnover_rate" if len(numeric_field_values(subset, "turnover_rate")) >= 2
            else "volume" if len(numeric_field_values(subset, "volume")) >= 2
            else None
        )
        activity_mean = None
        if activity_field:
            activity_mean = statistics.fmean(value for _, value in numeric_field_values(subset, activity_field))
        phases.append({
            "phase_id": phase_id,
            "start_date": subset[0][0].isoformat(),
            "end_date": subset[-1][0].isoformat(),
            "start_close": subset[0][1]["close"],
            "end_close": subset[-1][1]["close"],
            "return": change,
            "direction": direction,
            "highest_close": highest[1]["close"],
            "highest_close_date": highest[0].isoformat(),
            "lowest_close": lowest[1]["close"],
            "lowest_close_date": lowest[0].isoformat(),
            "trading_days": len(subset) - 1,
            "calendar_days": (subset[-1][0] - subset[0][0]).days,
            "max_drawdown": max_drawdown_detail(subset)["max_drawdown"],
            "activity_metric": activity_field,
            "average_activity": activity_mean,
        })
    return {
        "method": "directional_change",
        "threshold": threshold,
        "turning_point_dates": [series[idx][0].isoformat() for idx in points],
        "phases": phases,
    }


def event_window_return(series, event_day, before, after):
    dates = [day for day, _ in series]
    first_idx = next((idx for idx, day in enumerate(dates) if day >= event_day), None)
    if first_idx is None:
        return None
    start_idx = first_idx + int(before)
    end_idx = first_idx + int(after)
    if start_idx < 0 or end_idx >= len(series) or start_idx >= end_idx:
        return None
    return {
        "anchor_trading_date": series[first_idx][0].isoformat(),
        "start_date": series[start_idx][0].isoformat(),
        "end_date": series[end_idx][0].isoformat(),
        "return": series[end_idx][1]["close"] / series[start_idx][1]["close"] - 1.0,
    }


def event_analysis(events, asset, benchmarks):
    output = []
    for idx, event in enumerate(events or []):
        if not isinstance(event, dict):
            raise ValueError("events[%s] 必须是对象" % idx)
        event_day = iso_date("events[%s].date" % idx, event.get("date"))
        windows = event.get("windows", [[-1, 1], [-3, 3]])
        if not isinstance(windows, list) or not windows:
            raise ValueError("events[%s].windows 必须为非空数组" % idx)
        benchmark_name = event.get("benchmark")
        if benchmark_name is not None and benchmark_name not in benchmarks:
            raise ValueError("events[%s].benchmark 不存在: %s" % (idx, benchmark_name))
        event_result = {
            "date": event_day.isoformat(),
            "label": str(event.get("label", "")).strip() or None,
            "category": str(event.get("category", "")).strip() or None,
            "fact_status": str(event.get("fact_status", "verified")).strip(),
            "windows": [],
        }
        for window in windows:
            if not isinstance(window, list) or len(window) != 2:
                raise ValueError("events[%s].windows 每项必须为 [before, after]" % idx)
            before, after = int(window[0]), int(window[1])
            asset_window = event_window_return(asset, event_day, before, after)
            row = {"before": before, "after": after, "asset": asset_window}
            if benchmark_name and asset_window:
                benchmark_window = event_window_return(
                    benchmarks[benchmark_name], event_day, before, after
                )
                row["benchmark_name"] = benchmark_name
                row["benchmark"] = benchmark_window
                if benchmark_window:
                    row["arithmetic_excess_return"] = (
                        asset_window["return"] - benchmark_window["return"]
                    )
            event_result["windows"].append(row)
        output.append(event_result)
    return output


def pricing_bridge(data):
    if not data:
        return None
    metric = str(data.get("metric", "")).strip()
    horizon = str(data.get("horizon", "")).strip()
    basis = str(data.get("basis", "")).strip()
    if not metric or not horizon or not basis:
        raise ValueError("pricing_bridge 必须声明 metric、horizon 与 basis，且前后口径恒定")
    points = []
    for side in ("start", "end"):
        raw = data.get(side)
        if not isinstance(raw, dict):
            raise ValueError("pricing_bridge.%s 缺失" % side)
        point = {
            "date": iso_date("pricing_bridge.%s.date" % side, raw.get("date")),
            "price": finite("pricing_bridge.%s.price" % side, raw.get("price")),
            "estimate": finite("pricing_bridge.%s.estimate" % side, raw.get("estimate")),
            "multiple": finite("pricing_bridge.%s.multiple" % side, raw.get("multiple")),
        }
        if min(point["price"], point["estimate"], point["multiple"]) <= 0:
            raise ValueError("pricing_bridge 的 price、estimate、multiple 必须为正")
        points.append(point)
    start, end = points
    if start["date"] >= end["date"]:
        raise ValueError("pricing_bridge.start.date 必须早于 end.date")
    log_price = math.log(end["price"] / start["price"])
    log_estimate = math.log(end["estimate"] / start["estimate"])
    log_multiple = math.log(end["multiple"] / start["multiple"])
    gap = log_price - log_estimate - log_multiple
    return {
        "metric": metric,
        "horizon": horizon,
        "basis": basis,
        "start": {**start, "date": start["date"].isoformat()},
        "end": {**end, "date": end["date"].isoformat()},
        "price_return": end["price"] / start["price"] - 1.0,
        "estimate_change": end["estimate"] / start["estimate"] - 1.0,
        "multiple_change": end["multiple"] / start["multiple"] - 1.0,
        "log_price_change": log_price,
        "log_estimate_component": log_estimate,
        "log_multiple_component": log_multiple,
        "log_reconciliation_gap": gap,
        "start_identity_gap": start["price"] / (start["estimate"] * start["multiple"]) - 1.0,
        "end_identity_gap": end["price"] / (end["estimate"] * end["multiple"]) - 1.0,
        "component_shares": {
            "estimate": log_estimate / log_price if abs(log_price) > 1e-12 else None,
            "multiple": log_multiple / log_price if abs(log_price) > 1e-12 else None,
        },
        "warning": "仅在前后使用同一预测指标、同一预测期和同一会计口径时，才可把该桥解释为盈利预期与估值倍数的定价分解。",
    }


def compute(data):
    if not isinstance(data, dict):
        raise ValueError("输入必须是 JSON 对象")
    metadata = data.get("metadata") or {}
    series_block = data.get("series")
    if not isinstance(series_block, dict) or "asset" not in series_block:
        raise ValueError("input.series.asset 缺失")
    full_asset = parse_series(series_block["asset"], "series.asset")
    analysis = data.get("analysis") or {}
    if not isinstance(analysis, dict):
        raise ValueError("analysis 必须是对象")
    annualization = int(analysis.get("annualization", 252))
    if annualization <= 0:
        raise ValueError("analysis.annualization 必须为正")
    phase_threshold = finite("analysis.phase_threshold", analysis.get("phase_threshold", 0.08))
    baseline_days = int(analysis.get("volume_baseline_days", 20))
    if baseline_days <= 0:
        raise ValueError("analysis.volume_baseline_days 必须为正")
    asset = slice_series(full_asset, analysis.get("start_date"), analysis.get("end_date"))

    raw_benchmarks = series_block.get("benchmarks") or {}
    if series_block.get("benchmark") is not None:
        if raw_benchmarks:
            raise ValueError("series.benchmark 与 series.benchmarks 不得同时提供")
        raw_benchmarks = {"benchmark": series_block["benchmark"]}
    if not isinstance(raw_benchmarks, dict):
        raise ValueError("series.benchmarks 必须是对象")
    benchmarks = {}
    for name, raw in raw_benchmarks.items():
        parsed = parse_series(raw, "series.benchmarks.%s" % name)
        benchmarks[str(name)] = slice_series(
            parsed, analysis.get("start_date"), analysis.get("end_date")
        )

    result = {
        "metadata": metadata,
        "analysis_parameters": {
            "annualization": annualization,
            "phase_threshold": phase_threshold,
            "volume_baseline_days": baseline_days,
            "price_adjustment": metadata.get("price_adjustment"),
        },
        "path": path_statistics(asset, annualization),
        "liquidity": liquidity_statistics(asset, baseline_days),
        "phases": phase_statistics(asset, phase_threshold),
        "benchmarks": {
            name: benchmark_comparison(asset, benchmark, annualization)
            for name, benchmark in benchmarks.items()
        },
        "events": event_analysis(data.get("events", []), asset, benchmarks),
        "pricing_bridge": pricing_bridge(data.get("pricing_bridge")),
        "warnings": [],
    }
    if len(asset) < 40:
        result["warnings"].append("分析窗口少于 40 个价格观测：波动率、Beta 与阶段划分稳定性有限。")
    if not benchmarks:
        result["warnings"].append("未提供市场或行业基准：无法区分共同 Beta 与公司特异表现。")
    if result["liquidity"]["preferred_activity_metric"] is None:
        result["warnings"].append("未提供成交额、换手率或成交量：无法分析量价与流动性变化。")
    if not metadata.get("price_adjustment"):
        result["warnings"].append("未声明价格复权口径：区间收益可能受分红、拆股或送转影响。")
    if not data.get("events"):
        result["warnings"].append("未提供已核验事件清单：脚本只描述价格路径，不支持事件归因。")
    return result


def self_test():
    asset = []
    market = []
    prices = [100, 103, 107, 111, 116, 112, 107, 101, 96, 99, 104, 110]
    market_prices = [100, 101, 102, 103, 104, 103, 102, 101, 100, 101, 102, 103]
    for idx, (price, benchmark_price) in enumerate(zip(prices, market_prices), start=1):
        day = "2026-01-%02d" % idx
        asset.append({
            "date": day,
            "open": price,
            "high": price * 1.01,
            "low": price * 0.99,
            "close": price,
            "volume": 1000 + idx * 100,
            "amount": (1000 + idx * 100) * price,
        })
        market.append({"date": day, "close": benchmark_price})
    fixture = {
        "metadata": {"ticker": "TEST", "price_adjustment": "back_adjusted"},
        "series": {"asset": asset, "benchmarks": {"market": market}},
        "analysis": {"phase_threshold": 0.08, "volume_baseline_days": 3},
        "events": [{"date": "2026-01-05", "label": "test", "benchmark": "market"}],
        "pricing_bridge": {
            "metric": "EPS",
            "horizon": "FY2027E constant horizon",
            "basis": "adjusted",
            "start": {"date": "2026-01-01", "price": 100, "estimate": 5, "multiple": 20},
            "end": {"date": "2026-01-12", "price": 110, "estimate": 5.5, "multiple": 20},
        },
    }
    result = compute(fixture)
    if abs(result["path"]["total_return"] - 0.10) > 1e-12:
        raise AssertionError(result)
    if result["benchmarks"]["market"]["status"] != "available":
        raise AssertionError(result)
    if len(result["phases"]["phases"]) < 2:
        raise AssertionError(result)
    if any("highest_close" not in phase or "lowest_close" not in phase
           for phase in result["phases"]["phases"]):
        raise AssertionError(result)
    if abs(result["pricing_bridge"]["log_reconciliation_gap"]) > 1e-12:
        raise AssertionError(result)
    if result["events"][0]["windows"][0]["asset"] is None:
        raise AssertionError(result)
    emit("SELF_TEST_PASS")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="计算个股区间走势、相对表现、量价、阶段、事件窗口与定价桥。"
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
