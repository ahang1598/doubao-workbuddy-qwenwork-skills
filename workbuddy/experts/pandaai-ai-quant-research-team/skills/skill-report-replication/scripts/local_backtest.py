#!/usr/bin/env python
"""Run the bundled local BACKTEST engine for report-replication projects.

The engine consumes real market data plus a strategy signal log and writes
auditable backtest artifacts under 04_backtest_strategy/.
"""

from __future__ import annotations

import argparse
import html
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


REQUIRED_SIGNAL_COLUMNS = ["date", "symbol", "factor", "direction"]


@dataclass
class BacktestConfig:
    project_dir: Path
    market_data: Path
    signal_log: Path
    date_col: str
    symbol_col: str
    price_col: str
    initial_cash: float
    cost_bps: float
    slippage_bps: float
    max_weight_per_symbol: float
    execution_lag: int
    annualization: float


def read_table(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    if suffix in {".csv", ".txt"}:
        return pd.read_csv(path)
    if suffix in {".json", ".jsonl"}:
        return pd.read_json(path, lines=suffix == ".jsonl")
    raise ValueError(f"unsupported data file: {path}")


def normalize_market_data(df: pd.DataFrame, cfg: BacktestConfig) -> pd.DataFrame:
    missing = [col for col in [cfg.date_col, cfg.symbol_col, cfg.price_col] if col not in df.columns]
    if missing:
        raise ValueError(f"market data missing columns: {missing}")

    out = df[[cfg.date_col, cfg.symbol_col, cfg.price_col]].copy()
    out.columns = ["date", "symbol", "close"]
    out["date"] = pd.to_datetime(out["date"])
    out["symbol"] = out["symbol"].astype(str)
    out["close"] = pd.to_numeric(out["close"], errors="coerce")
    out = out.dropna(subset=["date", "symbol", "close"])
    out = out.sort_values(["symbol", "date"])
    out = out.drop_duplicates(["date", "symbol"], keep="last")
    if out.empty:
        raise ValueError("market data is empty after cleaning")
    if (out["close"] <= 0).any():
        raise ValueError("market data contains non-positive prices")
    out["return"] = out.groupby("symbol")["close"].pct_change()
    return out


def read_signal_jsonl(path: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            date = rec.get("date")
            signals = rec.get("signals")
            if not date or not isinstance(signals, dict):
                raise ValueError(f"signal_log line {line_no} must contain date and signals")
            for symbol, payload in signals.items():
                if not isinstance(payload, dict):
                    raise ValueError(f"signal_log line {line_no} payload for {symbol} must be an object")
                factor = payload.get("factor", payload.get("ie"))
                direction = payload.get("direction")
                rows.append(
                    {
                        "date": date,
                        "symbol": str(symbol),
                        "factor": factor,
                        "direction": direction,
                    }
                )
    if not rows:
        raise ValueError("signal_log contains no records")
    return pd.DataFrame(rows)


def normalize_signals(df: pd.DataFrame) -> pd.DataFrame:
    missing = [col for col in REQUIRED_SIGNAL_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"signals missing columns: {missing}")
    out = df[REQUIRED_SIGNAL_COLUMNS].copy()
    out["date"] = pd.to_datetime(out["date"])
    out["symbol"] = out["symbol"].astype(str)
    out["factor"] = pd.to_numeric(out["factor"], errors="coerce")
    out["direction"] = pd.to_numeric(out["direction"], errors="coerce").fillna(0)
    out["direction"] = np.sign(out["direction"]).astype(float)
    out = out.dropna(subset=["date", "symbol"])
    out = out.sort_values(["symbol", "date"])
    out = out.drop_duplicates(["date", "symbol"], keep="last")
    if out.empty:
        raise ValueError("signals are empty after cleaning")
    return out


def build_positions(signals: pd.DataFrame, cfg: BacktestConfig) -> pd.DataFrame:
    positions = signals.copy()
    positions["raw_position"] = positions["direction"]
    if cfg.execution_lag > 0:
        positions["position"] = positions.groupby("symbol")["raw_position"].shift(cfg.execution_lag)
    else:
        positions["position"] = positions["raw_position"]
    positions["position"] = positions["position"].fillna(0.0)

    gross = positions.groupby("date")["position"].transform(lambda s: s.abs().sum())
    weights = positions["position"] / gross.replace(0, np.nan)
    weights = weights.fillna(0.0)
    positions["weight"] = weights.clip(-cfg.max_weight_per_symbol, cfg.max_weight_per_symbol)

    capped_gross = positions.groupby("date")["weight"].transform(lambda s: s.abs().sum())
    positions["weight"] = positions["weight"] / capped_gross.replace(0, np.nan)
    positions["weight"] = positions["weight"].fillna(0.0)
    return positions


def run_backtest(market: pd.DataFrame, signals: pd.DataFrame, cfg: BacktestConfig) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    positions = build_positions(signals, cfg)
    merged = market.merge(positions, on=["date", "symbol"], how="left")
    merged[["factor", "direction", "raw_position", "position", "weight"]] = merged[
        ["factor", "direction", "raw_position", "position", "weight"]
    ].fillna(0.0)

    merged = merged.sort_values(["symbol", "date"])
    merged["prev_weight"] = merged.groupby("symbol")["weight"].shift(1).fillna(0.0)
    merged["turnover"] = (merged["weight"] - merged["prev_weight"]).abs()
    merged["gross_exposure"] = merged["weight"].abs()
    merged["contribution"] = merged["weight"] * merged["return"].fillna(0.0)

    cost_rate = (cfg.cost_bps + cfg.slippage_bps) / 10000.0
    daily = (
        merged.groupby("date")
        .agg(
            gross_return=("contribution", "sum"),
            turnover=("turnover", "sum"),
            gross_exposure=("gross_exposure", "sum"),
            active_symbols=("weight", lambda s: int((s.abs() > 0).sum())),
        )
        .reset_index()
    )
    daily["cost"] = daily["turnover"] * cost_rate
    daily["net_return"] = daily["gross_return"] - daily["cost"]
    daily["equity"] = cfg.initial_cash * (1.0 + daily["net_return"]).cumprod()
    daily["nav"] = daily["equity"] / cfg.initial_cash
    daily["peak_nav"] = daily["nav"].cummax()
    daily["drawdown"] = daily["nav"] / daily["peak_nav"] - 1.0

    trades = merged.loc[merged["turnover"] > 1e-12, [
        "date",
        "symbol",
        "close",
        "prev_weight",
        "weight",
        "turnover",
        "factor",
        "direction",
    ]].copy()
    trades["notional_change"] = trades["turnover"] * cfg.initial_cash
    trades["estimated_cost"] = trades["notional_change"] * cost_rate
    return daily, trades, merged


def max_drawdown_duration(drawdown: pd.Series) -> int:
    max_duration = 0
    current = 0
    for value in drawdown.fillna(0.0):
        if value < 0:
            current += 1
            max_duration = max(max_duration, current)
        else:
            current = 0
    return max_duration


def compute_metrics(daily: pd.DataFrame, cfg: BacktestConfig) -> dict[str, float]:
    returns = daily["net_return"].fillna(0.0)
    n = len(returns)
    final_nav = float(daily["nav"].iloc[-1]) if n else 1.0
    total_return = final_nav - 1.0
    ann_return = final_nav ** (cfg.annualization / n) - 1.0 if n > 0 and final_nav > 0 else np.nan
    ann_vol = returns.std(ddof=1) * math.sqrt(cfg.annualization) if n > 1 else np.nan
    downside = returns[returns < 0]
    downside_vol = downside.std(ddof=1) * math.sqrt(cfg.annualization) if len(downside) > 1 else np.nan
    sharpe = ann_return / ann_vol if ann_vol and not np.isnan(ann_vol) and ann_vol != 0 else np.nan
    sortino = ann_return / downside_vol if downside_vol and not np.isnan(downside_vol) and downside_vol != 0 else np.nan
    max_dd = float(daily["drawdown"].min()) if n else np.nan
    calmar = ann_return / abs(max_dd) if max_dd and not np.isnan(max_dd) and max_dd != 0 else np.nan
    win_rate = float((returns > 0).mean()) if n else np.nan
    avg_turnover = float(daily["turnover"].mean()) if n else np.nan
    return {
        "periods": float(n),
        "final_nav": final_nav,
        "total_return": total_return,
        "annual_return": float(ann_return),
        "annual_volatility": float(ann_vol),
        "downside_volatility": float(downside_vol),
        "sharpe": float(sharpe),
        "sortino": float(sortino),
        "calmar": float(calmar),
        "max_drawdown": max_dd,
        "max_drawdown_duration": float(max_drawdown_duration(daily["drawdown"])),
        "win_rate": win_rate,
        "avg_turnover": avg_turnover,
        "total_cost": float(daily["cost"].sum()) if n else 0.0,
    }


def fmt_pct(value: float) -> str:
    if value is None or np.isnan(value):
        return "NA"
    return f"{value * 100:.2f}%"


def fmt_num(value: float) -> str:
    if value is None or np.isnan(value):
        return "NA"
    return f"{value:.4f}"


def write_signal_matrix(signals: pd.DataFrame, output_path: Path) -> None:
    matrix = signals.pivot_table(index="date", columns="symbol", values="direction", aggfunc="last")
    matrix.sort_index().to_csv(output_path, encoding="utf-8-sig")


def write_html_report(project_dir: Path, daily: pd.DataFrame, trades: pd.DataFrame, metrics: dict[str, float], cfg: BacktestConfig) -> None:
    report_path = project_dir / "04_backtest_strategy" / "backtest_report.html"
    rows = "\n".join(
        f"<tr><th>{html.escape(k)}</th><td>{fmt_pct(v) if 'return' in k or 'volatility' in k or k in {'max_drawdown', 'win_rate'} else fmt_num(v)}</td></tr>"
        for k, v in metrics.items()
    )
    last_rows = daily.tail(10).copy()
    daily_table = "\n".join(
        "<tr>"
        f"<td>{row.date.strftime('%Y-%m-%d')}</td>"
        f"<td>{fmt_pct(row.net_return)}</td>"
        f"<td>{fmt_num(row.nav)}</td>"
        f"<td>{fmt_pct(row.drawdown)}</td>"
        f"<td>{fmt_num(row.turnover)}</td>"
        "</tr>"
        for row in last_rows.itertuples()
    )
    content = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>BACKTEST 本地回测报告</title>
  <style>
    body {{ font-family: Arial, "Microsoft YaHei", sans-serif; margin: 32px; color: #18212f; line-height: 1.6; }}
    h1, h2 {{ color: #111827; }}
    table {{ border-collapse: collapse; width: 100%; margin: 12px 0 24px; }}
    th, td {{ border: 1px solid #d6dae1; padding: 8px 10px; text-align: left; }}
    th {{ background: #f3f5f8; }}
    .note {{ background: #f8fafc; border-left: 4px solid #64748b; padding: 12px; }}
  </style>
</head>
<body>
  <h1>BACKTEST 本地回测报告</h1>
  <div class="note">
    本报告由 skill 内置本地回测引擎生成。信号按 date/symbol 对齐行情，默认使用滞后一根执行，收益来自真实输入行情的收盘价变化。
    这不是因子验证理论净值的替代品，而是根据 strategy signal log 重建的本地执行口径回测。
  </div>
  <h2>运行配置</h2>
  <table>
    <tr><th>市场数据</th><td>{html.escape(str(cfg.market_data))}</td></tr>
    <tr><th>信号日志</th><td>{html.escape(str(cfg.signal_log))}</td></tr>
    <tr><th>初始资金</th><td>{cfg.initial_cash:.2f}</td></tr>
    <tr><th>手续费 bps</th><td>{cfg.cost_bps:.2f}</td></tr>
    <tr><th>滑点 bps</th><td>{cfg.slippage_bps:.2f}</td></tr>
    <tr><th>执行滞后</th><td>{cfg.execution_lag}</td></tr>
  </table>
  <h2>核心绩效</h2>
  <table>{rows}</table>
  <h2>最近 10 期权益</h2>
  <table>
    <tr><th>日期</th><th>净收益</th><th>NAV</th><th>回撤</th><th>换手</th></tr>
    {daily_table}
  </table>
  <h2>产物路径</h2>
  <ul>
    <li><code>04_backtest_strategy/backtest_logs/equity_curve.csv</code></li>
    <li><code>04_backtest_strategy/backtest_logs/performance_metrics.csv</code></li>
    <li><code>04_backtest_strategy/backtest_logs/trades.csv</code></li>
    <li><code>03_factor_validation/data/backtest_alignment_audit.csv</code></li>
  </ul>
</body>
</html>
"""
    report_path.write_text(content, encoding="utf-8")


def update_manifest(project_dir: Path, cfg: BacktestConfig, metrics: dict[str, float]) -> None:
    manifest_path = project_dir / "manifest.json"
    if not manifest_path.exists():
        return
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    manifest["backtest_engine"] = {
        "name": "report-replication local BACKTEST",
        "version": "1",
        "status": "ran",
        "script": "scripts/local_backtest.py",
    }
    manifest["backtest_entrypoint"] = "scripts/local_backtest.py"
    manifest["backtest_command"] = " ".join(sys.argv)
    manifest.setdefault("run_history", []).append(
        {
            "stage": "local_backtest",
            "market_data": str(cfg.market_data),
            "signal_log": str(cfg.signal_log),
            "final_nav": metrics.get("final_nav"),
            "max_drawdown": metrics.get("max_drawdown"),
        }
    )
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_outputs(cfg: BacktestConfig, daily: pd.DataFrame, trades: pd.DataFrame, merged: pd.DataFrame, signals: pd.DataFrame, metrics: dict[str, float]) -> None:
    strategy_dir = cfg.project_dir / "04_backtest_strategy"
    logs_dir = strategy_dir / "backtest_logs"
    validation_data_dir = cfg.project_dir / "03_factor_validation" / "data"
    strategy_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    validation_data_dir.mkdir(parents=True, exist_ok=True)

    daily.to_csv(logs_dir / "equity_curve.csv", index=False, encoding="utf-8-sig")
    trades.to_csv(logs_dir / "trades.csv", index=False, encoding="utf-8-sig")
    merged.to_csv(logs_dir / "position_return_detail.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([metrics]).to_csv(logs_dir / "performance_metrics.csv", index=False, encoding="utf-8-sig")
    write_signal_matrix(signals, validation_data_dir / "direction_matrix_from_strategy.csv")
    daily[["date", "net_return", "nav", "drawdown", "turnover"]].to_csv(
        validation_data_dir / "portfolio_returns_dir_full.csv",
        index=False,
        encoding="utf-8-sig",
    )
    audit = pd.DataFrame(
        [
            {
                "dimension": "source",
                "factor_validation": "strategy-direction validation uses signal log and close-to-close returns",
                "backtest_actual": "local BACKTEST engine uses the same signal log with execution lag and transaction costs",
                "explanation": "If factor validation used a different return timing or cost setting, NAV divergence is expected.",
            },
            {
                "dimension": "final_nav",
                "factor_validation": "",
                "backtest_actual": metrics.get("final_nav"),
                "explanation": "Generated by scripts/local_backtest.py.",
            },
            {
                "dimension": "max_drawdown",
                "factor_validation": "",
                "backtest_actual": metrics.get("max_drawdown"),
                "explanation": "Drawdown is computed from local BACKTEST NAV.",
            },
        ]
    )
    audit.to_csv(validation_data_dir / "backtest_alignment_audit.csv", index=False, encoding="utf-8-sig")
    write_html_report(cfg.project_dir, daily, trades, metrics, cfg)
    raw = {
        "metrics": metrics,
        "rows": {
            "equity_curve": len(daily),
            "trades": len(trades),
            "position_return_detail": len(merged),
        },
    }
    (strategy_dir / "backtest_report_raw.html").write_text(
        "<pre>" + html.escape(json.dumps(raw, ensure_ascii=False, indent=2)) + "</pre>",
        encoding="utf-8",
    )
    update_manifest(cfg.project_dir, cfg, metrics)


def parse_args() -> BacktestConfig:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_dir", help="Project directory, e.g. /home/coder/project/replication/report-replication/{report_id}")
    parser.add_argument("--market-data", required=True, help="CSV/Parquet market data with date, symbol, close columns.")
    parser.add_argument(
        "--signal-log",
        help="JSONL signal log. Defaults to 04_backtest_strategy/backtest_logs/signal_log.jsonl under project_dir.",
    )
    parser.add_argument("--date-col", default="date")
    parser.add_argument("--symbol-col", default="symbol")
    parser.add_argument("--price-col", default="close")
    parser.add_argument("--initial-cash", type=float, default=1_000_000.0)
    parser.add_argument("--cost-bps", type=float, default=2.0)
    parser.add_argument("--slippage-bps", type=float, default=1.0)
    parser.add_argument("--max-weight-per-symbol", type=float, default=1.0)
    parser.add_argument("--execution-lag", type=int, default=1)
    parser.add_argument("--annualization", type=float, default=252.0)
    args = parser.parse_args()

    project_dir = Path(args.project_dir).expanduser().resolve()
    signal_log = Path(args.signal_log).expanduser().resolve() if args.signal_log else project_dir / "04_backtest_strategy" / "backtest_logs" / "signal_log.jsonl"
    return BacktestConfig(
        project_dir=project_dir,
        market_data=Path(args.market_data).expanduser().resolve(),
        signal_log=signal_log,
        date_col=args.date_col,
        symbol_col=args.symbol_col,
        price_col=args.price_col,
        initial_cash=args.initial_cash,
        cost_bps=args.cost_bps,
        slippage_bps=args.slippage_bps,
        max_weight_per_symbol=args.max_weight_per_symbol,
        execution_lag=args.execution_lag,
        annualization=args.annualization,
    )


def main() -> int:
    cfg = parse_args()
    if not cfg.project_dir.exists():
        raise FileNotFoundError(f"project_dir does not exist: {cfg.project_dir}")
    if not cfg.market_data.exists():
        raise FileNotFoundError(f"market data does not exist: {cfg.market_data}")
    if not cfg.signal_log.exists():
        raise FileNotFoundError(f"signal log does not exist: {cfg.signal_log}")

    market = normalize_market_data(read_table(cfg.market_data), cfg)
    signals = normalize_signals(read_signal_jsonl(cfg.signal_log))
    daily, trades, merged = run_backtest(market, signals, cfg)
    if daily.empty:
        raise ValueError("backtest generated no equity rows")
    metrics = compute_metrics(daily, cfg)
    write_outputs(cfg, daily, trades, merged, signals, metrics)
    print(json.dumps({"ok": True, "project_dir": str(cfg.project_dir), "metrics": metrics}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
