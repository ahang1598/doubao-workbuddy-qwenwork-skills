#!/usr/bin/env python3
"""Build a tearsheet only from files already fetched through WorkBuddy Connector."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import metrics  # noqa: E402
import render  # noqa: E402


def read_returns(path: str) -> pd.Series:
    frame = pd.read_csv(path)
    if frame.empty:
        raise ValueError(f"input has zero rows: {path}")
    columns = {column.lower().strip(): column for column in frame.columns}
    date_column = columns.get("date") or frame.columns[0]
    frame[date_column] = pd.to_datetime(frame[date_column], errors="coerce")
    frame = frame.dropna(subset=[date_column]).sort_values(date_column).set_index(date_column)
    if "return" in columns:
        return frame[columns["return"]].astype(float).dropna()
    if "ret" in columns:
        return frame[columns["ret"]].astype(float).dropna()
    for candidate in ("nav", "close", "unit_nav"):
        if candidate in columns:
            return metrics.nav_to_returns(frame[columns[candidate]].astype(float)).dropna()
    numeric = frame.select_dtypes("number")
    if numeric.empty:
        raise ValueError(f"input has no return, nav, close, or numeric column: {path}")
    return metrics.nav_to_returns(numeric.iloc[:, 0].astype(float)).dropna()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--nav", help="strategy CSV with date,nav")
    source.add_argument("--returns", help="strategy CSV with date,return")
    parser.add_argument(
        "--benchmark-csv",
        help="optional index rows exported from call_pandadata get_index_daily",
    )
    parser.add_argument("--ppy", type=int, default=252)
    parser.add_argument("--rf", type=float, default=0.02)
    parser.add_argument("--rolling-window", type=int)
    parser.add_argument("--out", required=True)
    parser.add_argument("--html", required=True)
    parser.add_argument("--title", default="策略绩效 Tearsheet")
    args = parser.parse_args()

    strategy_path = args.nav or args.returns
    returns = read_returns(strategy_path)
    if len(returns) < 3:
        raise ValueError("strategy series has fewer than three usable observations")
    benchmark = read_returns(args.benchmark_csv) if args.benchmark_csv else None
    payload = metrics.compute_all(
        returns,
        ppy=args.ppy,
        rf_annual=args.rf,
        bench_returns=benchmark,
        rolling_window=args.rolling_window,
    )
    payload["backend"] = "workbuddy-pandadata-connector-export"
    payload["status"] = "ok"
    payload["degraded"] = []
    payload["sources"] = {
        "strategy": str(Path(strategy_path).resolve()),
        "benchmark": str(Path(args.benchmark_csv).resolve()) if args.benchmark_csv else None,
    }
    print(render.build_summary_text(payload))
    Path(args.out).write_text(render.to_json(payload), encoding="utf-8")
    Path(args.html).write_text(render.to_html(payload, args.title), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
