#!/usr/bin/env python3
"""Validate the compact real-data research evidence used by fast/standard modes."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


class GateError(RuntimeError):
    pass


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GateError(f"invalid JSON {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise GateError(f"JSON root must be an object: {path}")
    return payload


def require_text(path: Path, minimum: int) -> None:
    if not path.is_file() or len(path.read_text(encoding="utf-8-sig").strip()) < minimum:
        raise GateError(f"missing or insufficient evidence: {path.name}")


def validate(stage: Path, mode: str) -> dict[str, Any]:
    manifest = read_json(stage / "manifest.json")
    receipt = read_json(stage / "data_call_receipt.json")
    backtest = read_json(stage / "compact_backtest.json")
    require_text(stage / "factor_formula.md", 40)
    require_text(stage / "final_delivery_summary.md", 120)

    if str(manifest.get("status", "")).lower() not in {"complete", "completed", "passed"}:
        raise GateError("manifest status is not completed")
    if str(manifest.get("data_mode", "")).lower() != "real":
        raise GateError("manifest.data_mode must be real")
    expected_depth = "formula_only" if mode == "fast" else "targeted"
    if manifest.get("source_depth") != expected_depth:
        raise GateError(f"manifest.source_depth must be {expected_depth}")

    required_receipt = ("method", "actual_parameters", "status", "rows", "date_range", "key_fields")
    missing = [key for key in required_receipt if receipt.get(key) in (None, "", [])]
    if missing:
        raise GateError(f"data call receipt missing: {', '.join(missing)}")
    if str(receipt["status"]).lower() not in {"success", "passed", "complete", "completed"}:
        raise GateError("data call did not succeed")
    if int(receipt["rows"]) <= 0:
        raise GateError("data call returned zero rows")
    if not isinstance(receipt["actual_parameters"], dict):
        raise GateError("actual_parameters must be an object")
    if not isinstance(receipt["date_range"], list) or len(receipt["date_range"]) != 2:
        raise GateError("date_range must contain the first and last data date")
    if not isinstance(receipt["key_fields"], list) or len(receipt["key_fields"]) < 2:
        raise GateError("key_fields must list at least two returned fields")

    if backtest.get("executed") is not True:
        raise GateError("compact backtest was not actually executed")
    if int(backtest.get("n_periods", 0)) < 20:
        raise GateError("compact backtest requires at least 20 periods")
    if int(backtest.get("execution_lag_periods", 0)) < 1:
        raise GateError("execution_lag_periods must be at least 1")
    if float(backtest.get("round_trip_cost", -1)) < 0:
        raise GateError("round_trip_cost is missing or invalid")
    if not str(backtest.get("data_source", "")).strip():
        raise GateError("compact backtest must identify its data source")
    metrics = backtest.get("metrics")
    if not isinstance(metrics, dict):
        raise GateError("compact backtest metrics must be an object")
    required_metrics = {"total_return", "annualized_return", "sharpe", "max_drawdown"}
    if not required_metrics.issubset(metrics):
        raise GateError("compact backtest is missing required metrics")
    chart_count = int(backtest.get("validation_chart_count", 0))
    chart_limit = 4 if mode == "fast" else 6
    if chart_count > chart_limit:
        raise GateError(f"validation_chart_count exceeds {mode} limit {chart_limit}")

    return {
        "success": True,
        "mode": mode,
        "checks": [
            {"id": "real_data", "status": "pass", "rows": int(receipt["rows"])},
            {"id": "data_receipt", "status": "pass", "method": receipt["method"]},
            {"id": "actual_backtest", "status": "pass", "n_periods": int(backtest["n_periods"])},
            {"id": "anti_lookahead", "status": "pass", "lag": int(backtest["execution_lag_periods"])},
            {"id": "cost_and_metrics", "status": "pass", "metrics": sorted(required_metrics)},
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage-dir", type=Path, required=True)
    parser.add_argument("--mode", choices=("fast", "standard"), required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    try:
        result = validate(args.stage_dir.resolve(), args.mode)
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except GateError as exc:
        result = {"success": False, "mode": args.mode, "error": str(exc)}
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
