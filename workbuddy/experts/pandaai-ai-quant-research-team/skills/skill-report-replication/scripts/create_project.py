#!/usr/bin/env python
"""Create a standard research output directory for a report replication task."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path


DEFAULT_ROOT = Path("/home/coder/project/replication/report-replication")
SUBDIRS = [
    "01_translation",
    "02_factor_reproduction",
    "03_factor_validation/data",
    "03_factor_validation/charts",
    "03_factor_validation/data_cache",
    "04_backtest_strategy/backtest_logs",
    "06_delivery",
]


ARTIFACTS = {
    "translation": "01_translation/full_translation.md",
    "factor_reproduction": "02_factor_reproduction/ai_summary_and_factor_formula.md",
    "factor_reference_implementation": "02_factor_reproduction/reference_implementation.py",
    "factor_validation_report": "03_factor_validation/factor_validation_report.html",
    "factor_matrix": "03_factor_validation/data/ie_factor_matrix.csv",
    "strategy_direction_matrix": "03_factor_validation/data/direction_matrix_from_strategy.csv",
    "portfolio_returns_ew_full": "03_factor_validation/data/portfolio_returns_ew_full.csv",
    "portfolio_returns_ew_is": "03_factor_validation/data/portfolio_returns_ew_is.csv",
    "portfolio_returns_ew_oos": "03_factor_validation/data/portfolio_returns_ew_oos.csv",
    "portfolio_returns_dir_full": "03_factor_validation/data/portfolio_returns_dir_full.csv",
    "portfolio_returns_dir_is": "03_factor_validation/data/portfolio_returns_dir_is.csv",
    "portfolio_returns_dir_oos": "03_factor_validation/data/portfolio_returns_dir_oos.csv",
    "ic_series": "03_factor_validation/data/ic_series.csv",
    "benchmark_comparison": "03_factor_validation/data/benchmark_comparison.csv",
    "chart_ie_distribution": "03_factor_validation/charts/01_ie_distribution.png",
    "chart_ic_series": "03_factor_validation/charts/02_ic_series.png",
    "chart_is_oos_ic": "03_factor_validation/charts/03_is_oos_ic_comparison.png",
    "chart_nav_equal_weight": "03_factor_validation/charts/04_cumulative_nav_equal_weight.png",
    "chart_nav_strategy_direction": "03_factor_validation/charts/05_cumulative_nav_strategy_direction.png",
    "chart_drawdown": "03_factor_validation/charts/06_drawdown.png",
    "chart_backtest_alignment": "03_factor_validation/charts/16_backtest_alignment_nav.png",
    "chart_walkforward": "03_factor_validation/charts/19_walkforward.png",
    "chart_cost_sensitivity": "03_factor_validation/charts/18_cost_sensitivity.png",
    "pandadata_market_data": "03_factor_validation/data_cache/pandadata_market_data.csv",
    "pandadata_market_data_metadata": "03_factor_validation/data_cache/pandadata_market_data.csv.metadata.json",
    "backtest_strategy": "04_backtest_strategy/strategy.py",
    "backtest_config": "04_backtest_strategy/config.json",
    "backtest_report": "04_backtest_strategy/backtest_report.html",
    "backtest_raw_report": "04_backtest_strategy/backtest_report_raw.html",
    "backtest_signal_log": "04_backtest_strategy/backtest_logs/signal_log.jsonl",
    "backtest_equity_curve": "04_backtest_strategy/backtest_logs/equity_curve.csv",
    "backtest_trades": "04_backtest_strategy/backtest_logs/trades.csv",
    "backtest_performance_metrics": "04_backtest_strategy/backtest_logs/performance_metrics.csv",
    "backtest_position_return_detail": "04_backtest_strategy/backtest_logs/position_return_detail.csv",
    "final_delivery_summary": "06_delivery/final_delivery_summary.md",
    "failure_report": "failure_report.md",
}


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "report"


def build_manifest(report_id: str, title: str, source: str | None) -> dict:
    return {
        "report_id": report_id,
        "title": title,
        "source": source,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "python": {
            "executable": sys.executable,
            "version": sys.version,
            "major_minor": f"{sys.version_info.major}.{sys.version_info.minor}",
        },
        "backtest_engine": {
            "name": "report-replication local BACKTEST",
            "version": None,
            "status": "bundled_available",
            "script": "scripts/local_backtest.py",
            "notes": "Use the bundled local engine by default. Record external BACKTEST runner only when the user explicitly supplies one.",
        },
        "backtest_entrypoint": "scripts/local_backtest.py",
        "backtest_command": None,
        "data_sources": [],
        "assumptions": [],
        "parameters": {},
        "code_hashes": {},
        "run_history": [],
        "artifacts": dict(ARTIFACTS),
        "quality_control": {
            "status": "initialized",
            "incident": None,
            "notes": [],
        },
        "status": "initialized",
    }


def read_json_utf8(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def merge_defaults(existing: dict, defaults: dict) -> dict:
    merged = dict(defaults)
    merged.update(existing)
    merged["artifacts"] = {**defaults.get("artifacts", {}), **existing.get("artifacts", {})}
    merged["backtest_engine"] = {
        **defaults.get("backtest_engine", {}),
        **existing.get("backtest_engine", {}),
    }
    merged["quality_control"] = {
        **defaults.get("quality_control", {}),
        **existing.get("quality_control", {}),
    }
    return merged


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--title", required=True, help="Report or paper title.")
    parser.add_argument("--source", help="Original PDF path, URL, or source note.")
    parser.add_argument("--report-id", help="Stable report id. Defaults to title slug.")
    parser.add_argument("--root", default=str(DEFAULT_ROOT), help="Output root directory.")
    args = parser.parse_args()

    report_id = slugify(args.report_id or args.title)
    project_dir = Path(args.root).expanduser().resolve() / report_id
    project_dir.mkdir(parents=True, exist_ok=True)

    for subdir in SUBDIRS:
        (project_dir / subdir).mkdir(parents=True, exist_ok=True)

    manifest_path = project_dir / "manifest.json"
    defaults = build_manifest(report_id, args.title, args.source)
    if manifest_path.exists():
        manifest = merge_defaults(read_json_utf8(manifest_path), defaults)
        manifest.setdefault("status", "initialized")
    else:
        manifest = defaults

    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(json.dumps({"project_dir": str(project_dir), "manifest": str(manifest_path)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
