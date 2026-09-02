#!/usr/bin/env python3
"""Fetch completed factor results once and emit a compact local summary.

Input is a UTF-8 text file with one row per run:
    run_id [name] [direction] [group_number]

The full CLI payload is cached per run ID. Subsequent invocations skip cached runs unless
``--refresh`` is supplied. Raw chart series never go to stdout; only the compact metrics table
is printed, so this command is suitable for large result sets and interrupted sessions.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from batch import extract  # noqa: E402
from competition_proxy import max_drawdown, product_return, score_a, score_c  # noqa: E402


def read_manifest(path: Path) -> list[dict]:
    rows, seen = [], set()
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if not 1 <= len(parts) <= 4:
            raise ValueError(f"{path}:{lineno}: expected run_id [name] [direction] [group_number]")
        run_id = parts[0]
        if run_id in seen:
            raise ValueError(f"{path}:{lineno}: duplicate run_id {run_id}")
        direction = parts[2] if len(parts) >= 3 else "1"
        if direction not in {"0", "1"}:
            raise ValueError(f"{path}:{lineno}: direction must be 0 or 1")
        groups = int(parts[3]) if len(parts) == 4 else None
        if groups is not None and groups not in range(2, 11):
            raise ValueError(f"{path}:{lineno}: group_number must be 2-10")
        rows.append({"run_id": run_id, "name": parts[1] if len(parts) >= 2 else run_id,
                     "direction": direction, "group_number": groups})
        seen.add(run_id)
    return rows


def atomic_json(path: Path, value: object) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)


def fetch(run_id: str, timeout: int) -> dict:
    proc = subprocess.run(["pandaai-cli", "--json", "factor_result", run_id],
                          capture_output=True, text=True, timeout=timeout)
    try:
        payload = json.loads(proc.stdout)
    except ValueError:
        return {"success": False, "error": {"message": (proc.stdout + proc.stderr).strip()[:500]}}
    if proc.returncode and payload.get("success", True):
        payload.setdefault("success", False)
    return payload


def chart_records(payload: dict, series_name: str, cycle: int) -> list[dict]:
    """Read the CLI chart without emitting its large series to stdout.

    The chart is daily. The platform scores only the pool's rebalance dates, so a local review
    samples every ``cycle`` trading dates from the common backtest start. All candidates in a
    comparison must share that start and cycle; the platform remains authoritative for its own
    rebalance anchor.
    """
    analysis = payload.get("factor_analysis") or (payload.get("results") or {}).get("factor_analysis") or {}
    chart = analysis.get(series_name) or {}
    x_series, y_series = chart.get("x", []), chart.get("y", [])
    if not x_series or not y_series:
        return []
    dates = x_series[0].get("data", []) if isinstance(x_series[0], dict) else []
    values = next((item.get("data", []) for item in y_series
                   if isinstance(item, dict) and item.get("name") ==
                   ("Rank_IC" if series_name.endswith("rank_ic_sequence_chart") else "IC")), [])
    count = min(len(dates), len(values))
    # Some CLI runs already return one point per rebalance. Detect that from calendar spacing;
    # only daily charts need a second sampling pass.
    parsed_dates = []
    for value in dates[:count]:
        try:
            parsed_dates.append(dt.date.fromisoformat(str(value)[:10]))
        except ValueError:
            parsed_dates.append(None)
    gaps = [(b - a).days for a, b in zip(parsed_dates, parsed_dates[1:]) if a and b]
    gaps.sort()
    median_gap = gaps[len(gaps) // 2] if gaps else 0
    step = cycle if cycle > 1 and median_gap < max(2, cycle - 1) else 1
    records = []
    for index in range(0, count, step):
        try:
            records.append({"date": dates[index], "value": float(values[index])})
        except (TypeError, ValueError):
            continue
    return records


def rank_ic_records(payload: dict, cycle: int) -> list[dict]:
    return chart_records(payload, "query_rank_ic_sequence_chart", cycle)


def ic_records(payload: dict, cycle: int) -> list[dict]:
    return chart_records(payload, "query_ic_sequence_chart", cycle)


def c_proxy_months(payload: dict, direction: str, cycle: int) -> list[dict]:
    """Build a rebalance-period C proxy from the direction-selected excess chart.

    CLI exposes one cumulative observation per rebalance, not the official pool's daily ledger.
    The resulting month records are deliberately a proxy: returns and drawdown are measured at the
    rebalance frequency and turnover is estimated as the reported per-rebalance rate times the
    number of observations in the month.
    """
    analysis = payload.get("factor_analysis") or (payload.get("results") or {}).get("factor_analysis") or {}
    chart = analysis.get("query_factor_excess_chart") or {}
    x_series, y_series = chart.get("x", []), chart.get("y", [])
    if not x_series or not y_series:
        return []
    dates = x_series[0].get("data", []) if isinstance(x_series[0], dict) else []
    chart_label = "组10" if direction == "1" else "组1"
    group_label = "分组10" if direction == "1" else "分组1"
    cumulative = next((item.get("data", []) for item in y_series
                       if isinstance(item, dict) and item.get("name") == chart_label), [])
    groups = {item.get("group"): item for item in analysis.get("query_group_return_analysis", [])}
    try:
        turnover = float(str(groups[group_label].get("turnoverRate", "")).rstrip("%")) / 100
    except (KeyError, TypeError, ValueError):
        return []
    months: dict[str, list[float]] = {}
    previous = 0.0
    for date, current in zip(dates, cumulative):
        try:
            current = float(current)
            period_return = (1 + current) / (1 + previous) - 1
            month = dt.date.fromisoformat(str(date)[:10]).strftime("%Y-%m")
        except (TypeError, ValueError, ZeroDivisionError):
            continue
        months.setdefault(month, []).append(period_return)
        previous = current
    return [{"month": month, "excess_month": product_return(returns),
             "daily_excess_returns": returns, "turnover": turnover * len(returns),
             "max_drawdown": max_drawdown(returns)} for month, returns in sorted(months.items())]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("manifest", type=Path)
    ap.add_argument("--out-dir", type=Path, default=Path("result-cache"))
    ap.add_argument("--group-number", type=int, choices=range(2, 11), default=10)
    ap.add_argument("--cycle", type=int, choices=range(1, 11), default=5,
                    help="shared rebalance cycle used to sample the CLI daily RankIC chart")
    ap.add_argument("--timeout", type=int, default=180)
    ap.add_argument("--refresh", action="store_true", help="refetch even when cached")
    args = ap.parse_args()
    rows = read_manifest(args.manifest)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    summary = []
    for index, row in enumerate(rows, 1):
        raw_path = args.out_dir / f"{row['run_id']}.json"
        status = "cached"
        if args.refresh or not raw_path.exists():
            try:
                payload = fetch(row["run_id"], args.timeout)
            except (OSError, subprocess.TimeoutExpired) as exc:
                payload = {"success": False, "error": {"message": str(exc)}}
            atomic_json(raw_path, payload)
            status = "fetched"
        else:
            payload = json.loads(raw_path.read_text(encoding="utf-8"))
        item = {"run_id": row["run_id"], "name": row["name"], "direction": row["direction"],
                "status": status, "success": bool(payload.get("success"))}
        if item["success"]:
            try:
                item["metrics"] = extract(payload, row["direction"],
                                            row["group_number"] or args.group_number)
                records = rank_ic_records(payload, args.cycle)
                if records:
                    ic = ic_records(payload, args.cycle)
                    result = score_a(records, dt.date.fromisoformat(records[-1]["date"][:10]),
                                     direction=int(row["direction"]), ic_records=ic)
                    item["A_proxy"] = {
                        "score": result["score"], "anchor": result["anchor"],
                        "metrics": result["metrics"], "rebalance_observations": len(records),
                        "first_date": records[0]["date"][:10], "last_date": records[-1]["date"][:10],
                        "warning": "local rebalance anchor starts at the first CLI chart date; verify against pool settings",
                    }
                c_months = c_proxy_months(payload, row["direction"], args.cycle)
                if c_months:
                    result = score_c(c_months)
                    item["C_rebalance_proxy"] = {
                        "score": result["score"], "anchor": result["anchor"],
                        "months": len(result["monthly"]),
                        "warning": "rebalance-period single-factor proxy; not the official daily pool ledger",
                    }
            except (KeyError, TypeError, ValueError) as exc:
                item["success"] = False
                item["error"] = str(exc)
        else:
            item["error"] = (payload.get("error") or {}).get("message", "factor_result failed")
        summary.append(item)
        print(f"[{index}/{len(rows)}] {row['name']}: {status}, "
              f"{'ok' if item['success'] else 'failed'}")
    atomic_json(args.out_dir / "summary.json", {"group_number": args.group_number, "results": summary})
    print(f"saved {len(summary)} compact rows and raw payloads under {args.out_dir}")
    return 0 if all(item["success"] for item in summary) else 1


if __name__ == "__main__":
    raise SystemExit(main())
