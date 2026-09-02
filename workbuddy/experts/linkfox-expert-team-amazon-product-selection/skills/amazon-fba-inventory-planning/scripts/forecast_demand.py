#!/usr/bin/env python3
"""
Basic demand forecasting for Amazon FBA inventory planning.

Supports:
  - Simple moving average
  - Weighted moving average (recent days weighted higher)
  - Single exponential smoothing

Outputs a forecast daily demand and a simple volatility measure that can be
passed straight into calculate_restock.py as --daily-sales and --std-demand.

Usage examples:
  # From a CSV with columns: date, sales
  python forecast_demand.py --csv sales.csv --method ewma --alpha 0.2

  # From a plain list of recent daily sales (most recent last)
  python forecast_demand.py --series 10,12,9,14,11,13,12,15,10,12 --method ma --window 7

  # Weighted MA with custom decay
  python forecast_demand.py --csv sales.csv --method wma --window 14
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from typing import List, Sequence, Tuple


def moving_average(series: Sequence[float], window: int) -> Tuple[float, float]:
    """Return (forecast, sample_std) using the last `window` points."""
    if not series:
        raise ValueError("series is empty")
    w = min(window, len(series))
    tail = list(series[-w:])
    mean = sum(tail) / w
    if w < 2:
        return mean, 0.0
    var = sum((x - mean) ** 2 for x in tail) / (w - 1)
    return mean, math.sqrt(var)


def weighted_moving_average(series: Sequence[float], window: int) -> Tuple[float, float]:
    """
    Linear weights: oldest=1 ... newest=window.
    Returns (weighted_mean, weighted residual std approximation).
    """
    if not series:
        raise ValueError("series is empty")
    w = min(window, len(series))
    tail = list(series[-w:])
    weights = list(range(1, w + 1))
    w_sum = sum(weights)
    mean = sum(x * wt for x, wt in zip(tail, weights)) / w_sum
    if w < 2:
        return mean, 0.0
    # Simple unweighted std of the same window as volatility proxy
    var = sum((x - mean) ** 2 for x in tail) / (w - 1)
    return mean, math.sqrt(var)


def exponential_smoothing(series: Sequence[float], alpha: float) -> Tuple[float, float]:
    """
    Single exponential smoothing.
    Forecast = last smoothed level.
    Volatility ≈ std of one-step residuals (or of series if too short).
    """
    if not series:
        raise ValueError("series is empty")
    if not 0 < alpha <= 1:
        raise ValueError("alpha must be in (0, 1]")

    level = series[0]
    residuals: List[float] = []
    for x in series[1:]:
        pred = level
        residuals.append(x - pred)
        level = alpha * x + (1 - alpha) * level

    if len(residuals) >= 2:
        mean_r = sum(residuals) / len(residuals)
        var = sum((r - mean_r) ** 2 for r in residuals) / (len(residuals) - 1)
        std = math.sqrt(max(var, 0.0))
    elif len(series) >= 2:
        mean = sum(series) / len(series)
        var = sum((x - mean) ** 2 for x in series) / (len(series) - 1)
        std = math.sqrt(max(var, 0.0))
    else:
        std = 0.0

    return level, std


def load_series_from_csv(path: str, value_col: str = "sales") -> List[float]:
    """Load a numeric series from CSV. Uses `value_col`; sorts by date if present."""
    rows = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("CSV has no header")
        fields = {c.lower(): c for c in reader.fieldnames}
        vcol = fields.get(value_col.lower())
        if not vcol:
            raise ValueError(f"Column '{value_col}' not found. Available: {list(reader.fieldnames)}")
        dcol = fields.get("date")
        for row in reader:
            try:
                val = float(row[vcol])
            except (TypeError, ValueError):
                continue
            date = row[dcol] if dcol else ""
            rows.append((date, val))
    if dcol:
        rows.sort(key=lambda r: r[0])
    return [v for _, v in rows]


def parse_series_arg(text: str) -> List[float]:
    parts = [p.strip() for p in text.split(",") if p.strip()]
    return [float(p) for p in parts]


def main():
    parser = argparse.ArgumentParser(description="FBA demand forecast helper")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--csv", help="CSV file with a sales column (and optional date)")
    src.add_argument("--series", help="Comma-separated daily sales, oldest → newest")

    parser.add_argument(
        "--method",
        choices=["ma", "wma", "ewma"],
        default="ewma",
        help="ma=moving average, wma=weighted MA, ewma=exponential smoothing (default)",
    )
    parser.add_argument("--window", type=int, default=14, help="Window for ma/wma (default 14)")
    parser.add_argument("--alpha", type=float, default=0.2, help="Alpha for ewma (default 0.2)")
    parser.add_argument("--value-col", default="sales", help="CSV value column name (default sales)")
    parser.add_argument(
        "--horizon-days",
        type=int,
        default=30,
        help="Informational planning horizon in days (default 30)",
    )
    args = parser.parse_args()

    if args.csv:
        series = load_series_from_csv(args.csv, value_col=args.value_col)
    else:
        series = parse_series_arg(args.series)

    if len(series) < 1:
        print("No valid observations found.", file=sys.stderr)
        sys.exit(1)

    if args.method == "ma":
        forecast, std = moving_average(series, args.window)
        method_desc = f"moving average (window={min(args.window, len(series))})"
    elif args.method == "wma":
        forecast, std = weighted_moving_average(series, args.window)
        method_desc = f"weighted moving average (window={min(args.window, len(series))})"
    else:
        forecast, std = exponential_smoothing(series, args.alpha)
        method_desc = f"exponential smoothing (alpha={args.alpha})"

    total_horizon = forecast * args.horizon_days

    print("=" * 52)
    print("FBA DEMAND FORECAST")
    print("=" * 52)
    print(f"Observations:     {len(series)}")
    print(f"Method:           {method_desc}")
    print(f"Forecast daily:   {forecast:.3f}")
    print(f"Demand std (proxy): {std:.3f}")
    print(f"Horizon:          {args.horizon_days} days")
    print(f"Horizon total:    {total_horizon:.1f} units")
    print("-" * 52)
    print("Pass to restock calculator:")
    print(f"  --daily-sales {forecast:.4f} --std-demand {std:.4f}")
    print("=" * 52)


if __name__ == "__main__":
    main()
