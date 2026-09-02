#!/usr/bin/env python3
"""
Bayesian demand forecasting helpers for Amazon FBA inventory planning.

Implements two practical approaches:

1) Bayesian Poisson-Gamma rate model (conjugate)
   - Good when daily demand is count-like and roughly Poisson
   - Posterior mean of λ used as forecast daily demand
   - Posterior std used as uncertainty proxy for safety stock

2) Bayesian exponential smoothing (simple adaptive level)
   - Prior on level + sequential Bayesian update with observation noise
   - More robust for continuous-valued or noisy daily sales

Usage:
  python forecast_bayesian.py --series 10,12,9,14,11,13,12,15 --method poisson-gamma
  python forecast_bayesian.py --csv sales.csv --method bayes-es --alpha-prior 0.2
  python forecast_bayesian.py --series 0,0,2,0,1,0,0,3,0,0,1 --method poisson-gamma --horizon-days 30
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from typing import List, Sequence, Tuple


def load_series_from_csv(path: str, value_col: str = "sales") -> List[float]:
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
    return [float(p.strip()) for p in text.split(",") if p.strip()]


def poisson_gamma_forecast(
    series: Sequence[float],
    prior_a: float = 1.0,
    prior_b: float = 1.0,
) -> Tuple[float, float, float, float]:
    """
    Poisson likelihood + Gamma(a, b) prior on rate λ  (shape-rate parameterization).

    After observing counts x1..xn over n days:
      a_n = a0 + sum(xi)
      b_n = b0 + n
      E[λ] = a_n / b_n
      Var[λ] = a_n / b_n^2

    Returns: (mean_lambda, std_lambda, posterior_a, posterior_b)
    """
    if not series:
        raise ValueError("series is empty")
    # Round / floor negatives for count model
    xs = [max(0.0, float(x)) for x in series]
    n = len(xs)
    a_n = prior_a + sum(xs)
    b_n = prior_b + n
    mean = a_n / b_n
    var = a_n / (b_n ** 2)
    std = math.sqrt(max(var, 0.0))
    return mean, std, a_n, b_n


def bayesian_exp_smoothing(
    series: Sequence[float],
    prior_level: float | None = None,
    prior_var: float = 25.0,
    obs_var: float = 16.0,
) -> Tuple[float, float]:
    """
    Simple Bayesian level model (scalar Kalman / Bayesian ES):

      level ~ N(μ0, P0)
      y_t   ~ N(level, R)

    Sequential update yields posterior mean/variance of level.
    Returns (posterior_mean, posterior_std).
    """
    if not series:
        raise ValueError("series is empty")
    xs = [float(x) for x in series]
    mu = float(xs[0] if prior_level is None else prior_level)
    P = max(prior_var, 1e-6)
    R = max(obs_var, 1e-6)

    for y in xs:
        # Predict: level is random walk with no process noise here (can add Q if needed)
        # Update
        K = P / (P + R)
        mu = mu + K * (y - mu)
        P = (1 - K) * P

    return mu, math.sqrt(max(P, 0.0))


def main():
    parser = argparse.ArgumentParser(description="Bayesian demand forecast for FBA planning")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--csv", help="CSV with sales column")
    src.add_argument("--series", help="Comma-separated daily sales, oldest → newest")

    parser.add_argument(
        "--method",
        choices=["poisson-gamma", "bayes-es"],
        default="poisson-gamma",
        help="poisson-gamma (default) or bayes-es",
    )
    parser.add_argument("--value-col", default="sales")
    parser.add_argument("--horizon-days", type=int, default=30)

    # Poisson-Gamma priors
    parser.add_argument("--prior-a", type=float, default=1.0, help="Gamma shape prior (poisson-gamma)")
    parser.add_argument("--prior-b", type=float, default=1.0, help="Gamma rate prior (poisson-gamma)")

    # Bayes ES priors
    parser.add_argument("--prior-level", type=float, default=None, help="Prior mean level for bayes-es")
    parser.add_argument("--prior-var", type=float, default=25.0, help="Prior variance for bayes-es")
    parser.add_argument("--obs-var", type=float, default=16.0, help="Observation noise variance for bayes-es")

    args = parser.parse_args()

    if args.csv:
        series = load_series_from_csv(args.csv, value_col=args.value_col)
    else:
        series = parse_series_arg(args.series)

    if len(series) < 1:
        print("No valid observations.", file=sys.stderr)
        sys.exit(1)

    print("=" * 56)
    print("FBA BAYESIAN DEMAND FORECAST")
    print("=" * 56)
    print(f"Observations:  {len(series)}")

    if args.method == "poisson-gamma":
        mean, std, a_n, b_n = poisson_gamma_forecast(series, args.prior_a, args.prior_b)
        print("Method:        Poisson-Gamma (conjugate rate model)")
        print(f"Prior Gamma:   a={args.prior_a}, b={args.prior_b}")
        print(f"Posterior:     a={a_n:.3f}, b={b_n:.3f}")
        print(f"E[λ] daily:    {mean:.4f}")
        print(f"Std[λ]:        {std:.4f}")
        # Predictive daily std roughly sqrt(E[λ] + Var[λ]) for Poisson-Gamma
        pred_std = math.sqrt(max(mean + std ** 2, 0.0))
        print(f"Pred daily std:{pred_std:.4f}  (incl. Poisson noise)")
        daily = mean
        demand_std = pred_std
    else:
        mean, std = bayesian_exp_smoothing(
            series,
            prior_level=args.prior_level,
            prior_var=args.prior_var,
            obs_var=args.obs_var,
        )
        print("Method:        Bayesian exponential smoothing (scalar level)")
        print(f"Posterior μ:   {mean:.4f}")
        print(f"Posterior σ:   {std:.4f}")
        daily = mean
        demand_std = std

    print(f"Horizon:       {args.horizon_days} days")
    print(f"Horizon total: {daily * args.horizon_days:.1f} units")
    print("-" * 56)
    print("Pass to restock calculator:")
    print(f"  --daily-sales {daily:.4f} --std-demand {demand_std:.4f}")
    print("=" * 56)
    print("Notes:")
    print("  - Poisson-Gamma suits count-like daily demand; use weakly informative priors.")
    print("  - bayes-es suits noisy continuous sales; tune obs-var to residual noise.")
    print("  - For strong seasonality, deseasonalize first or use seasonal_index.py.")


if __name__ == "__main__":
    main()
