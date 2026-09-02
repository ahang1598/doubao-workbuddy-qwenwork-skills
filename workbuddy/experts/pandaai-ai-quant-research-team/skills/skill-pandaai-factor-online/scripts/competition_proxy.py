#!/usr/bin/env python3
"""Offline proxy for the public PandaAI competition A/B/C score.

The input is a normalized JSON snapshot, not a CLI command:

{
    "as_of": "2026-07-31",
    "factors": [{
        "name": "F-A17",
        "effective_date": "2026-01-10",
        "rank_ic": [{"date": "2026-01-12", "value": 0.04,
                     "sample_type": "in_sample"}],
        "ic": [{"date": "2026-01-12", "value": 0.03}],
        "portfolio_months": [{"month": "2026-07", "excess_month": 0.02,
                           "portfolio_daily_returns": [0.001, -0.002],
                           "benchmark_daily_returns": [0.0005, -0.001],
                           "turnover": 0.4, "max_drawdown": 0.05}]
  }]
}

It never calls pandaai-cli, creates factors, or claims to reproduce official points. B is
unavailable until effective-date records exist; C is a single-factor proxy unless the input is a
pool-level composite daily ledger.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path


def parse_date(value: str) -> dt.date:
    text = str(value)
    if len(text) == 8 and text.isdigit():
        return dt.datetime.strptime(text, "%Y%m%d").date()
    return dt.date.fromisoformat(text[:10])


def number(value: object) -> float | None:
    if isinstance(value, str):
        text = value.strip().replace("%", "")
        if not text:
            return None
        try:
            parsed = float(text)
        except ValueError:
            return None
        return parsed / 100 if value.strip().endswith("%") else parsed
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def five_year_cutoff(as_of: dt.date) -> dt.date:
    try:
        return as_of.replace(year=as_of.year - 5)
    except ValueError:  # 29 February
        return as_of.replace(year=as_of.year - 5, day=28)


def monthly_means(records: list[dict]) -> dict[str, float]:
    buckets: dict[str, list[float]] = defaultdict(list)
    for record in records:
        try:
            date = parse_date(record["date"])
        except (KeyError, TypeError, ValueError):
            continue
        value = number(record.get("value", record.get("rank_ic")))
        if value is not None:
            buckets[date.strftime("%Y-%m")].append(value)
    return {month: statistics.mean(values) for month, values in sorted(buckets.items())}


def stats(rank_values: list[float], ic_values: list[float] | None = None,
          direction: int = 1, win_threshold: float = 0.02) -> dict[str, float | int | None]:
    if not rank_values:
        return {"periods": 0, "mean": None, "rank_ic_mean": None, "icir": None,
                "win_rate": None, "win_periods": 0}
    ic_values = ic_values or []
    mean = statistics.mean(rank_values)
    deviation = statistics.stdev(ic_values) if len(ic_values) > 1 else None
    ic_mean = statistics.mean(ic_values) if ic_values else None
    win_count = (sum(value > win_threshold for value in ic_values) if direction == 1
                 else sum(value < -win_threshold for value in ic_values))
    return {
        "periods": len(rank_values),
        "mean": mean,
        "rank_ic_mean": mean,
        "icir": ic_mean / deviation if ic_mean is not None and deviation else None,
        "win_rate": win_count / len(ic_values) if ic_values else None,
        "win_periods": len(ic_values),
    }


def product_return(values: list[float]) -> float | None:
    if not values:
        return None
    result = 1.0
    for value in values:
        result *= 1 + value
    return result - 1


def max_drawdown(values: list[float]) -> float | None:
    if not values:
        return None
    nav = peak = 1.0
    drawdown = 0.0
    for value in values:
        nav *= 1 + value
        peak = max(peak, nav)
        drawdown = max(drawdown, 1 - nav / peak)
    return drawdown


def _selected(records: list[dict], cutoff: dt.date) -> tuple[list[dict], bool]:
    selected, has_marker = [], False
    for record in records:
        try:
            date = parse_date(record["date"])
        except (KeyError, TypeError, ValueError):
            continue
        sample_type = str(record.get("sample_type", "")).lower()
        is_oos = bool(record.get("out_of_sample")) or sample_type in {"oos", "out_of_sample"}
        has_marker |= "sample_type" in record or "out_of_sample" in record
        if date >= cutoff or is_oos:
            selected.append(record)
    return selected, has_marker


def _values_by_date(records: list[dict], key: str = "value") -> dict[dt.date, float]:
    values = {}
    for record in records:
        try:
            date = parse_date(record["date"])
            value = number(record.get(key, record.get("value")))
        except (KeyError, TypeError, ValueError):
            continue
        if value is not None:
            values[date] = value
    return values


def score_a(records: list[dict], as_of: dt.date, direction: int = 1,
            win_records: list[dict] | None = None, win_threshold: float = 0.02,
            ic_records: list[dict] | None = None, decay: float = 1.0,
            factor_effective_date: dt.date | None = None) -> dict:
    """Score A from the fixed five-year entry window plus marked OOS records.

    RankIC is the mean of all valid rebalance-period RankIC values. ICIR and win rate use
    the matching Pearson IC sequence, never monthly RankIC means.
    """
    anchor = factor_effective_date or as_of
    cutoff = five_year_cutoff(anchor)
    selected, has_marker = _selected(records, cutoff)
    rank_values = [value for value in _values_by_date(selected).values()]
    source = ic_records if ic_records is not None else win_records
    if source is None:
        source = [{"date": r.get("date"), "value": r.get("ic")} for r in selected
                  if r.get("ic") is not None]
    selected_dates = {parse_date(r["date"]) for r in selected if r.get("date")}
    ic_values = [value for date, value in _values_by_date(source).items()
                 if date in selected_dates]
    metrics = stats(rank_values, ic_values, direction, win_threshold)
    score = (abs(metrics["rank_ic_mean"]) * abs(metrics["icir"]) * metrics["win_rate"]
             if metrics["rank_ic_mean"] is not None and metrics["icir"] is not None
             and metrics["win_rate"] is not None else None)
    age_months = None
    if factor_effective_date:
        age_months = max(0, (as_of.year - factor_effective_date.year) * 12
                         + as_of.month - factor_effective_date.month)
    cap = 0.70 if age_months is not None and age_months < 6 else 1.0
    na = min(max((score or 0) / 0.08, 0), cap) * decay if score is not None else None
    warnings = []
    if not has_marker:
        warnings.append("OOS markers are absent; A uses the fixed five-year window only")
    if not ic_values:
        warnings.append("matching Pearson IC records are absent; A score is unavailable")
    return {"score": score, "na": na, "anchor": 0.08,
            "monthly_rank_ic": monthly_means(selected),
            "metrics": metrics, "warnings": warnings}


def score_b(records: list[dict], effective_date: str | None, direction: int = 1,
            ic_records: list[dict] | None = None) -> dict:
    if not effective_date:
        return {"available": False, "score": None, "anchor": 0.06,
                "reason": "effective_date is required; official B starts after pool entry"}
    effective = parse_date(effective_date)
    fresh, fresh_dates = [], set()
    for record in records:
        try:
            date = parse_date(record["date"])
        except (KeyError, TypeError, ValueError):
            continue
        if date > effective:
            fresh.append(record)
            fresh_dates.add(date)
    source = ic_records if ic_records is not None else [
        {"date": r.get("date"), "value": r.get("ic")} for r in fresh if r.get("ic") is not None
    ]
    ic_values = [value for date, value in _values_by_date(source).items() if date in fresh_dates]
    metrics = stats([value for date, value in _values_by_date(fresh).items()],
                    ic_values, direction)
    score = (abs(metrics["rank_ic_mean"]) * abs(metrics["icir"]) * metrics["win_rate"]
             if metrics["rank_ic_mean"] is not None and metrics["icir"] is not None
             and metrics["win_rate"] is not None else None)
    return {"available": bool(metrics["periods"]), "score": score, "anchor": 0.06,
            "metrics": metrics, "reason": None if metrics["periods"] else "no post-effective records",
            "warnings": [] if ic_values else ["matching Pearson IC records are absent"]}


def annualized_excess(portfolio: list[float], benchmark: list[float]) -> float | None:
    if not portfolio or not benchmark or len(portfolio) != len(benchmark):
        return None
    n = len(portfolio)
    rp, rb = product_return(portfolio), product_return(benchmark)
    return ((1 + rp) ** (252 / n) - 1) - ((1 + rb) ** (252 / n) - 1)


def score_c(months: list[dict]) -> dict:
    monthly_scores = []
    warnings = []
    for month in months:
        portfolio = [number(value) for value in month.get("portfolio_daily_returns", [])]
        portfolio = [value for value in portfolio if value is not None]
        benchmark = [number(value) for value in month.get("benchmark_daily_returns", [])]
        benchmark = [value for value in benchmark if value is not None]
        daily = portfolio
        proxy_daily = [number(value) for value in month.get("daily_excess_returns", [])]
        proxy_daily = [value for value in proxy_daily if value is not None]
        excess_ann = annualized_excess(portfolio, benchmark)
        official = bool(portfolio and benchmark and len(portfolio) == len(benchmark))
        if not official:
            daily = proxy_daily
            excess_ann = None
            if daily:
                excess_ann = ((1 + product_return(daily)) ** (252 / len(daily)) - 1)
                warnings.append(f"{month.get('month', '?')}: excess-only rebalance proxy, not official Rex_ann/SR")
        turnover = number(month.get("turnover", month.get("turnover_month")))
        drawdown = number(month.get("max_drawdown", month.get("max_dd_month")))
        if excess_ann is None or turnover is None or len(daily) < 2:
            warnings.append(f"incomplete month: {month.get('month', '?')}")
            continue
        if drawdown is None:
            drawdown = max_drawdown(daily)
        if drawdown is None:
            warnings.append(f"incomplete month: {month.get('month', '?')}")
            continue
        daily_std = statistics.stdev(daily)
        sharpe = (statistics.mean(daily) / daily_std * math.sqrt(252)
                  if daily_std else 0.0)
        penalty = 1 - 1.2 * drawdown
        if penalty < 0:
            warnings.append(f"{month.get('month', '?')}: drawdown penalty below zero, rawC clamped to zero")
            raw = 0.0
        else:
            raw = max(excess_ann, 0) / max(turnover, 0.3) * sharpe * penalty
        monthly_scores.append({"month": month.get("month"), "raw": raw,
                               "nc": min(max(raw / 0.6, 0), 1),
                               "excess_ann": excess_ann, "sharpe_ann": sharpe,
                               "turnover": turnover, "max_drawdown": drawdown,
                               "official_daily_ledger": official})
    return {"available": bool(monthly_scores), "anchor": 0.6,
            "monthly": monthly_scores,
            "score": statistics.mean(item["raw"] for item in monthly_scores) if monthly_scores else None,
            "warnings": warnings}


def evaluate(snapshot: dict, as_of: str | None = None) -> dict:
    end = parse_date(as_of or snapshot.get("as_of"))
    rows = []
    for factor in snapshot.get("factors", []):
        direction = int(factor.get("direction", 1))
        effective = (parse_date(factor["effective_date"])
                     if factor.get("effective_date") else None)
        ic = factor.get("ic", factor.get("ic_sequence", []))
        a = score_a(factor.get("rank_ic", []), end, direction=direction,
                    ic_records=ic, factor_effective_date=effective)
        b = score_b(factor.get("rank_ic", []), factor.get("effective_date"),
                    direction=direction, ic_records=ic)
        c = score_c(factor.get("portfolio_months", []))
        rows.append({"name": factor.get("name"), "direction": direction,
                     "A_proxy": a, "B_proxy": b, "C_proxy": c})
    return {"as_of": end.isoformat(), "official_score": False,
            "warning": "Local proxy only; official B/C require platform post-effective and pool ledgers.",
            "factors": rows}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--as-of", help="override snapshot as_of, YYYY-MM-DD")
    args = parser.parse_args()
    snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
    print(json.dumps(evaluate(snapshot, args.as_of), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
