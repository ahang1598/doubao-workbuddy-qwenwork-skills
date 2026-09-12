#!/usr/bin/env python3
"""Unified CLI for wb-finance-skill signal scripts.

Examples:
  python3 scripts/run_signal.py --engine candlestick --input data.csv --code 600519
  python3 scripts/run_signal.py --engine vcp --code sh600519 --source westock --limit 120
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=FutureWarning)

ROOT = Path(__file__).resolve().parent
PRICE_ACTION = ROOT / "price-action"
QUANT = ROOT / "quant"

ENGINE_MODULES = {
    "candlestick": (PRICE_ACTION, "candlestick_patterns"),
    "basic": (PRICE_ACTION, "basic_indicators"),
    "elliott": (PRICE_ACTION, "elliott_wave"),
    "harmonic": (PRICE_ACTION, "harmonic_patterns"),
    "ichimoku": (PRICE_ACTION, "ichimoku"),
    "chan": (PRICE_ACTION, "chan_theory"),
    "smc": (PRICE_ACTION, "smart_money"),
    "pair": (QUANT, "pair_trading"),
    "seasonality": (QUANT, "seasonality"),
    "volatility": (QUANT, "volatility"),
    "factor_multi": (QUANT, "factor_multi"),
    "factor_fundamental": (QUANT, "factor_fundamental"),
}


def _normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    rename = {
        "last": "close",
        "vol": "volume",
        "turnover": "amount",
    }
    df = df.rename(columns=rename)
    required = ["open", "high", "low", "close"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"missing OHLC columns: {missing}; got {list(df.columns)}")
    if "volume" not in df.columns:
        df["volume"] = 0
    if "amount" not in df.columns:
        df["amount"] = df["volume"] * df["close"]
    for c in ["open", "high", "low", "close", "volume", "amount"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["open", "high", "low", "close"])
    return df


def _load_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "date" in [str(c).lower() for c in df.columns]:
        for c in df.columns:
            if str(c).lower() == "date":
                df[c] = pd.to_datetime(df[c], errors="coerce")
                df = df.set_index(c)
                break
    return _normalize_ohlcv(df)


def _parse_markdown_table(text: str) -> pd.DataFrame:
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|") or "---" in line:
            continue
        parts = [p.strip() for p in line.strip("|").split("|")]
        rows.append(parts)
    if len(rows) < 2:
        raise ValueError("westock output did not contain a markdown table")
    header, body = rows[0], rows[1:]
    df = pd.DataFrame(body, columns=header)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.set_index("date").sort_index()
    return _normalize_ohlcv(df)


def _load_westock(code: str, period: str, limit: int) -> pd.DataFrame:
    cmd = ["westock-data", "kline", code, "--period", period, "--limit", str(limit)]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if res.returncode != 0:
        raise RuntimeError(f"westock-data failed: {res.stderr or res.stdout}")
    return _parse_markdown_table(res.stdout)


def _summarize_series(series: pd.Series) -> dict:
    series = series.dropna()
    latest = int(series.iloc[-1]) if len(series) else 0
    return {
        "bars": int(len(series)),
        "latest_signal": latest,
        "long_count": int((series == 1).sum()),
        "short_count": int((series == -1).sum()),
        "last_10": [int(x) for x in series.tail(10).tolist()],
    }


def _run_engine(engine: str, code: str, df: pd.DataFrame) -> dict:
    if engine not in ENGINE_MODULES:
        raise ValueError(f"unknown engine: {engine}")
    path, module_name = ENGINE_MODULES[engine]
    sys.path.insert(0, str(path))
    try:
        mod = __import__(module_name)
    except ModuleNotFoundError as exc:
        return {
            "engine": engine,
            "code": code,
            "status": "missing_dependency",
            "missing_dependency": exc.name,
            "suggested_install": f"pip install {exc.name}",
        }
    engine_obj = mod.SignalEngine()
    signals = engine_obj.generate({code: df})
    series = signals[code]
    return {"engine": engine, "code": code, "status": "ok", **_summarize_series(series)}


def _run_vcp(code: str, df: pd.DataFrame) -> dict:
    """Lightweight VCP detector using 4 rolling windows.

    Heuristic: drawdowns and volume averages should contract across windows;
    current close should be close to recent high.
    """
    if len(df) < 60:
        return {"engine": "vcp", "code": code, "status": "insufficient_data", "bars": len(df), "need": 60}
    d = df.tail(80).copy()
    close = d["close"]
    vol = d["volume"].replace(0, np.nan)
    chunks = np.array_split(d, 4)
    contractions = []
    for i, ch in enumerate(chunks, start=1):
        high = float(ch["high"].max())
        low = float(ch["low"].min())
        drawdown = (low / high - 1) * 100 if high else 0
        volume_avg = float(ch["volume"].mean()) if "volume" in ch else 0
        contractions.append({"stage": i, "drawdown_pct": round(drawdown, 2), "volume_avg": round(volume_avg, 0)})
    dd = [abs(x["drawdown_pct"]) for x in contractions]
    vv = [x["volume_avg"] for x in contractions]
    dd_score = sum(1 for a, b in zip(dd, dd[1:]) if b <= a) / 3
    vol_score = sum(1 for a, b in zip(vv, vv[1:]) if b <= a) / 3 if all(vv) else 0
    recent_high = float(d["high"].tail(20).max())
    last_close = float(close.iloc[-1])
    near_high = last_close / recent_high if recent_high else 0
    score = round((dd_score * 40 + vol_score * 35 + min(near_high, 1) * 25), 1)
    if score >= 75:
        status = "mature_watchlist"
    elif score >= 60:
        status = "forming"
    else:
        status = "not_vcp"
    return {
        "engine": "vcp",
        "code": code,
        "status": status,
        "score": score,
        "last_close": round(last_close, 3),
        "trigger_price": round(recent_high, 3),
        "invalid_below": round(float(d["low"].tail(20).min()), 3),
        "contractions": contractions,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--engine", required=True, choices=sorted(list(ENGINE_MODULES) + ["vcp"]))
    p.add_argument("--code", required=True)
    p.add_argument("--input", help="CSV with open/high/low/close/volume columns")
    p.add_argument("--source", choices=["csv", "westock"], default="csv")
    p.add_argument("--period", default="day")
    p.add_argument("--limit", type=int, default=120)
    p.add_argument("--pretty", action="store_true")
    args = p.parse_args()

    if args.source == "westock":
        df = _load_westock(args.code, args.period, args.limit)
    else:
        if not args.input:
            raise SystemExit("--input is required when --source=csv")
        df = _load_csv(args.input)

    result = _run_vcp(args.code, df) if args.engine == "vcp" else _run_engine(args.engine, args.code, df)
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0 if result.get("status") in ("ok", "forming", "mature_watchlist", "not_vcp") else 1


if __name__ == "__main__":
    raise SystemExit(main())
