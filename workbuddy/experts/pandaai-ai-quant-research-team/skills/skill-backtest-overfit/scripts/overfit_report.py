"""
OverfitReport — orchestrates DSR, PBO, haircut and MinTRL into a single
verdict on whether a backtest is likely the product of selection bias /
multiple testing.

Usage (programmatic)
--------------------
    from overfit_report import build_report
    report = build_report(
        selected_returns=best_strategy_daily_returns,   # 1D array
        trials_matrix=all_configs_daily_returns,         # T x N (optional)
        n_trials=200,                                    # multiple-testing count
        periods_per_year=252,
    )
    print(report["verdict"])

CLI
---
    python overfit_report.py --returns selected.csv --trials trials.csv --n-trials 200
"""
from __future__ import annotations

import argparse
import json
import math
from typing import Optional

import numpy as np
import pandas as pd

from deflated_sharpe import (
    deflated_sharpe_ratio,
    minimum_track_record_length,
    sharpe_ratio,
    _skew_kurt,
)
from haircut import haircut_sharpe
from pbo_cscv import probability_of_backtest_overfitting


def build_report(
    selected_returns: np.ndarray,
    n_trials: int,
    trials_matrix: Optional[np.ndarray] = None,
    periods_per_year: int = 252,
    dsr_threshold: float = 0.95,
    pbo_threshold: float = 0.50,
    n_blocks: int = 16,
    haircut_method: str = "bonferroni",
) -> dict:
    r = np.asarray(selected_returns, dtype=float)
    r = r[~np.isnan(r)]
    ann = math.sqrt(periods_per_year)
    sr_pp = sharpe_ratio(r)
    skew, kurt = _skew_kurt(r)

    # --- Deflated Sharpe (uses cross-trial variance when trials are given) ---
    all_trial_sharpes = None
    if trials_matrix is not None:
        tm = np.asarray(trials_matrix, dtype=float)
        all_trial_sharpes = [sharpe_ratio(tm[:, j]) for j in range(tm.shape[1])]
        all_trial_sharpes = [s for s in all_trial_sharpes if not math.isnan(s)]
        n_trials = max(n_trials, len(all_trial_sharpes))

    dsr = deflated_sharpe_ratio(r, n_trials=n_trials,
                                all_trial_sharpes=all_trial_sharpes,
                                threshold=dsr_threshold)

    # --- Haircut Sharpe ---
    hc = haircut_sharpe(sr_pp, n_obs=r.size, n_tests=n_trials, method=haircut_method)

    # --- Minimum Track Record Length (to beat SR=0) ---
    mintrl = minimum_track_record_length(sr_pp, 0.0, skew, kurt)

    # --- PBO (needs the full trial matrix) ---
    pbo_block = None
    if trials_matrix is not None and np.asarray(trials_matrix).shape[1] >= 2:
        pbo_block = probability_of_backtest_overfitting(
            np.asarray(trials_matrix, float), n_blocks=n_blocks).summary()

    # --- Verdict ---
    flags = []
    if dsr.deflated_sharpe_ratio < dsr_threshold:
        flags.append(f"DSR {dsr.deflated_sharpe_ratio:.2f} < {dsr_threshold}")
    if pbo_block is not None and pbo_block["pbo"] > pbo_threshold:
        flags.append(f"PBO {pbo_block['pbo']:.2f} > {pbo_threshold}")
    if hc.adjusted_sharpe * ann < 0.5:
        flags.append(f"haircut Sharpe {hc.adjusted_sharpe * ann:.2f} < 0.5")
    if mintrl > r.size:
        flags.append(f"MinTRL {mintrl:.0f} > sample {r.size}")

    passed = len(flags) == 0
    verdict = (
        "PASS - survives multiple-testing correction"
        if passed else
        "FAIL - likely overfit / selection-biased: " + "; ".join(flags)
    )

    return {
        "verdict": verdict,
        "passed": passed,
        "observed_sharpe_annual": round(sr_pp * ann, 4),
        "skew": round(skew, 4),
        "kurtosis": round(kurt, 4),
        "n_obs": int(r.size),
        "n_trials": int(n_trials),
        "deflated_sharpe_ratio": round(dsr.deflated_sharpe_ratio, 4),
        "deflation_benchmark_sr0_annual": round(dsr.deflated_benchmark_sr0 * ann, 4),
        "psr_vs_zero": round(dsr.psr_vs_zero, 4),
        "haircut": {
            "method": hc.method,
            "adjusted_sharpe_annual": round(hc.adjusted_sharpe * ann, 4),
            "haircut_pct": round(hc.haircut, 4),
            "observed_pvalue": hc.observed_pvalue,
            "adjusted_pvalue": hc.adjusted_pvalue,
        },
        "minimum_track_record_length": round(mintrl, 1),
        "pbo": pbo_block,
    }


def render_text(report: dict) -> str:
    lines = [
        "=" * 64,
        " BACKTEST OVERFITTING REPORT",
        "=" * 64,
        f" Verdict : {report['verdict']}",
        "-" * 64,
        f" Observed Sharpe (annual) : {report['observed_sharpe_annual']}",
        f" Trials (multiple tests)  : {report['n_trials']}",
        f" Observations             : {report['n_obs']}",
        f" Skew / Kurtosis          : {report['skew']} / {report['kurtosis']}",
        "-" * 64,
        f" Deflated Sharpe Ratio    : {report['deflated_sharpe_ratio']} "
        f"(benchmark SR0 {report['deflation_benchmark_sr0_annual']} ann.)",
        f" PSR vs 0                 : {report['psr_vs_zero']}",
        f" Haircut Sharpe ({report['haircut']['method']}): "
        f"{report['haircut']['adjusted_sharpe_annual']} "
        f"(-{report['haircut']['haircut_pct']:.0%})",
        f" Min Track Record Length  : {report['minimum_track_record_length']} obs",
    ]
    if report["pbo"] is not None:
        lines.append(f" PBO                      : {report['pbo']['pbo']} "
                     f"({report['pbo']['n_splits']} CSCV splits)")
    lines.append("=" * 64)
    return "\n".join(lines)


def _load_series(path: str) -> np.ndarray:
    df = pd.read_csv(path)
    col = df.columns[-1] if df.shape[1] == 1 else (
        "returns" if "returns" in df.columns else df.columns[-1])
    return df[col].to_numpy(dtype=float)


def main():
    ap = argparse.ArgumentParser(description="Backtest overfitting report")
    ap.add_argument("--returns", required=True, help="CSV of the selected strategy's per-period returns")
    ap.add_argument("--trials", help="CSV (T x N) of every tried config's per-period returns")
    ap.add_argument("--n-trials", type=int, default=1, help="number of configurations tried")
    ap.add_argument("--periods-per-year", type=int, default=252)
    ap.add_argument("--out", help="write JSON report to this path")
    args = ap.parse_args()

    selected = _load_series(args.returns)
    trials = pd.read_csv(args.trials).to_numpy(float) if args.trials else None
    report = build_report(selected, n_trials=args.n_trials, trials_matrix=trials,
                          periods_per_year=args.periods_per_year)
    print(render_text(report))
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=2)
        print(f"\nJSON written to {args.out}")


if __name__ == "__main__":
    main()
