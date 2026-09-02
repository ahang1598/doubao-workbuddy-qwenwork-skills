#!/usr/bin/env python3
"""
Seasonal Index Calculator for Amazon FBA Inventory Planning

Implements the classic Ratio-to-Moving-Average method to extract
monthly or weekly seasonal indices from multi-year sales data.

Usage examples:
  python seasonal_index.py --csv sales.csv --freq monthly
  python seasonal_index.py --csv sales.csv --freq weekly --date-col date --value-col units
"""

from __future__ import annotations

import argparse
import sys
from typing import Dict

import numpy as np
import pandas as pd


def seasonal_index_monthly(
    df: pd.DataFrame,
    value_col: str = "sales",
    date_col: str = "date",
) -> Dict[int, float]:
    """
    Ratio-to-Moving-Average seasonal index (monthly).

    Returns dict {1: index_jan, ..., 12: index_dec}
    where the 12 indices sum to 12 (mean = 1.0).
    """
    data = df[[date_col, value_col]].copy()
    data[date_col] = pd.to_datetime(data[date_col])
    data = data.sort_values(date_col).set_index(date_col)

    monthly = data[value_col].resample("MS").sum().to_frame(value_col)

    # 12-month moving average, then center it
    monthly["MA"] = monthly[value_col].rolling(window=12, center=True).mean()
    monthly["CMA"] = monthly["MA"].rolling(window=2, center=True).mean()

    monthly["ratio"] = monthly[value_col] / monthly["CMA"]
    monthly["month"] = monthly.index.month

    prelim = monthly.groupby("month")["ratio"].mean()
    if prelim.isna().any() or len(prelim) < 12:
        raise ValueError(
            "Not enough data to compute a full 12-month seasonal index. "
            "Need at least ~24 months of observations."
        )

    final_index = prelim * (12 / prelim.sum())
    return final_index.to_dict()


def seasonal_index_weekly(
    df: pd.DataFrame,
    value_col: str = "sales",
    date_col: str = "date",
) -> Dict[int, float]:
    """
    Ratio-to-Moving-Average seasonal index (weekly, 52 weeks).

    Returns dict {1: index_w1, ..., 52: index_w52}
    where the 52 indices sum to 52 (mean = 1.0).
    """
    data = df[[date_col, value_col]].copy()
    data[date_col] = pd.to_datetime(data[date_col])
    data = data.sort_values(date_col).set_index(date_col)

    weekly = data[value_col].resample("W-MON").sum().to_frame(value_col)

    weekly["MA"] = weekly[value_col].rolling(window=52, center=True).mean()
    weekly["CMA"] = weekly["MA"].rolling(window=2, center=True).mean()
    weekly["ratio"] = weekly[value_col] / weekly["CMA"]

    weekly["weekofyear"] = weekly.index.isocalendar().week.astype(int)
    # Fold week 53 into week 52 for consistency
    weekly.loc[weekly["weekofyear"] == 53, "weekofyear"] = 52

    prelim = weekly.groupby("weekofyear")["ratio"].mean()
    if len(prelim) < 40:  # allow some missing weeks
        raise ValueError(
            "Not enough weekly data to compute a reliable seasonal index. "
            "Need at least ~2 years of weekly observations."
        )

    final_index = prelim * (52 / prelim.sum())
    return final_index.to_dict()


def peak_coefficient(indices: Dict[int, float], peak_months: list[int] | None = None) -> float:
    """Average seasonal index over the given peak months (default 11 & 12)."""
    if peak_months is None:
        peak_months = [11, 12]
    vals = [indices[m] for m in peak_months if m in indices]
    if not vals:
        raise ValueError(f"None of the peak months {peak_months} found in indices.")
    return float(np.mean(vals))


def main():
    parser = argparse.ArgumentParser(description="Calculate seasonal indices for FBA planning")
    parser.add_argument("--csv", required=True, help="Path to CSV with date and sales columns")
    parser.add_argument("--freq", choices=["monthly", "weekly"], default="monthly")
    parser.add_argument("--date-col", default="date")
    parser.add_argument("--value-col", default="sales")
    parser.add_argument("--peak-months", default="11,12", help="Comma-separated months for peak coefficient")
    args = parser.parse_args()

    df = pd.read_csv(args.csv)
    if args.date_col not in df.columns or args.value_col not in df.columns:
        print(f"CSV must contain columns: {args.date_col}, {args.value_col}", file=sys.stderr)
        sys.exit(1)

    if args.freq == "monthly":
        indices = seasonal_index_monthly(df, value_col=args.value_col, date_col=args.date_col)
        print("Monthly Seasonal Indices:")
        for m in range(1, 13):
            print(f"  {m:2d}: {indices.get(m, float('nan')):.4f}")
    else:
        indices = seasonal_index_weekly(df, value_col=args.value_col, date_col=args.date_col)
        print("Weekly Seasonal Indices (1-52):")
        for w in sorted(indices.keys()):
            print(f"  W{w:02d}: {indices[w]:.4f}")

    try:
        peak_m = [int(x) for x in args.peak_months.split(",")]
        coef = peak_coefficient(indices, peak_m if args.freq == "monthly" else None)
        if args.freq == "monthly":
            print(f"\nPeak coefficient (months {peak_m}): {coef:.3f}")
    except Exception:
        pass


if __name__ == "__main__":
    main()
