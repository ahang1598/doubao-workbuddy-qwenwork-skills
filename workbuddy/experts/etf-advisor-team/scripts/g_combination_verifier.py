# -*- coding: utf-8 -*-
"""G1-G6 三维联动验证器 (G-Combination Verifier) — v1.16

═══════════════════════════════════════════════════════════════════════════════
为什么需要本脚本？
═══════════════════════════════════════════════════════════════════════════════
faces/资金面.md 模块 1.7 提出**G1-G6 资金 × 筹码 × 价格**三维联动六组合：

  G1 量价齐升 + 筹码集中  → 多头共振（最强买点）
  G2 缩量上涨 + 筹码锁定  → 主升浪持续
  G3 放量滞涨 + 筹码发散  → 顶部预警
  G4 缩量下跌 + 筹码守恒  → 洗盘
  G5 放量下跌 + 筹码逃逸  → 主力出货
  G6 量价背离 + 筹码异常  → 陷阱（需特别警惕）

判定逻辑：基于 chip_distribution_analyzer 输出的 L1-L4 指标 + 近期 K 线量价数据，
按 6 种组合的特征条件做模式匹配，每组合给出"匹配度 0-100"评分。

═══════════════════════════════════════════════════════════════════════════════
使用方式
═══════════════════════════════════════════════════════════════════════════════
```bash
python scripts/g_combination_verifier.py 600519
```

输出：FinancialData/{code}_g_combination.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

WORKSPACE_ROOT = SCRIPT_DIR.parents[2]
FINANCIAL_DATA_DIR = WORKSPACE_ROOT / "FinancialData"
FINANCIAL_DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load_kline(code: str, days: int = 60) -> List[Dict[str, Any]]:
    try:
        import chip_distribution_analyzer as cda  # type: ignore
        return cda.fetch_kline_records(code, days=days)
    except Exception:
        cache = FINANCIAL_DATA_DIR / f"{code}_kline.json"
        if cache.exists():
            try:
                d = json.loads(cache.read_text(encoding="utf-8"))
                return d.get("K线数据", []) if isinstance(d, dict) else d
            except Exception:
                return []
    return []


def _load_chip(code: str) -> Optional[Dict[str, Any]]:
    cache = FINANCIAL_DATA_DIR / f"{code}_chip_distribution.json"
    if cache.exists():
        try:
            return json.loads(cache.read_text(encoding="utf-8"))
        except Exception:
            pass
    try:
        import chip_distribution_analyzer as cda  # type: ignore
        return cda.analyze(code)
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# 价量特征提取
# ═══════════════════════════════════════════════════════════════════════════════

def _extract_features(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    if len(records) < 20:
        return {}
    closes = [r.get("收盘", 0) or 0 for r in records]
    vols = [r.get("成交量(手)", 0) or 0 for r in records]
    cur = closes[-1]
    # 近 5/20 日量价
    vol_5 = sum(vols[-5:]) / 5
    vol_20 = sum(vols[-20:]) / 20
    vol_ratio = vol_5 / vol_20 if vol_20 > 0 else 1.0
    return_5 = (cur - closes[-6]) / closes[-6] if len(closes) >= 6 and closes[-6] > 0 else 0
    return_20 = (cur - closes[-21]) / closes[-21] if len(closes) >= 21 and closes[-21] > 0 else 0
    # 量价相关性（近 20 日）
    price_changes = [closes[i] - closes[i - 1] for i in range(-19, 0) if i - 1 >= -len(closes)]
    vol_changes = [vols[i] - vols[i - 1] for i in range(-19, 0) if i - 1 >= -len(vols)]
    corr = _correlation(price_changes, vol_changes)
    return {
        "current_price": cur,
        "return_5d": return_5,
        "return_20d": return_20,
        "vol_5d_avg": vol_5,
        "vol_20d_avg": vol_20,
        "vol_ratio_5_20": vol_ratio,
        "price_vol_correlation_20d": corr,
    }


def _correlation(xs: List[float], ys: List[float]) -> float:
    if len(xs) != len(ys) or len(xs) < 2:
        return 0.0
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((xs[i] - mx) * (ys[i] - my) for i in range(n))
    dx = sum((xs[i] - mx) ** 2 for i in range(n)) ** 0.5
    dy = sum((ys[i] - my) ** 2 for i in range(n)) ** 0.5
    return num / (dx * dy) if dx * dy > 0 else 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# G1-G6 模式匹配
# ═══════════════════════════════════════════════════════════════════════════════

def match_g_combinations(features: Dict[str, Any],
                          chip_indicators: Dict[str, Any]) -> Dict[str, Any]:
    """对每个 G1-G6 给出匹配度 0-100。"""
    if not features:
        return {}

    L1 = chip_indicators.get("L1_basic", {})
    concentration_90 = L1.get("concentration_90_pct", 30) / 100  # 默认 30%
    lockup = L1.get("lockup_ratio_90d", 0)
    dispersion = chip_indicators.get("L3_risk", {}).get("dispersion", 0.1)
    profit_ratio = L1.get("profit_ratio", 0.5)

    ret5 = features.get("return_5d", 0)
    ret20 = features.get("return_20d", 0)
    vol_ratio = features.get("vol_ratio_5_20", 1.0)
    corr = features.get("price_vol_correlation_20d", 0)

    scores: Dict[str, Dict[str, Any]] = {}

    # ─── G1 量价齐升 + 筹码集中（多头共振） ─────────────────────────
    g1 = 0
    if ret5 > 0.03:
        g1 += 25
    if vol_ratio > 1.3:
        g1 += 25
    if concentration_90 < 0.20:
        g1 += 25
    if lockup > 0.4:
        g1 += 25
    scores["G1_量价齐升+筹码集中"] = {
        "score": g1,
        "label": "多头共振（最强买点）",
        "matched": g1 >= 75,
    }

    # ─── G2 缩量上涨 + 筹码锁定（主升浪） ────────────────────────────
    g2 = 0
    if 0.01 < ret5 <= 0.10:
        g2 += 30
    if 0.7 <= vol_ratio <= 1.0:
        g2 += 30
    if lockup > 0.5:
        g2 += 25
    if concentration_90 < 0.18:
        g2 += 15
    scores["G2_缩量上涨+筹码锁定"] = {
        "score": g2,
        "label": "主升浪持续",
        "matched": g2 >= 75,
    }

    # ─── G3 放量滞涨 + 筹码发散（顶部预警） ──────────────────────────
    g3 = 0
    if vol_ratio > 1.5:
        g3 += 30
    if abs(ret5) < 0.02:
        g3 += 25
    if concentration_90 > 0.25:
        g3 += 25
    if dispersion > 0.12:
        g3 += 20
    scores["G3_放量滞涨+筹码发散"] = {
        "score": g3,
        "label": "顶部预警",
        "matched": g3 >= 75,
    }

    # ─── G4 缩量下跌 + 筹码守恒（洗盘） ──────────────────────────────
    g4 = 0
    if -0.10 < ret5 < -0.02:
        g4 += 30
    if vol_ratio < 0.85:
        g4 += 30
    if lockup > 0.35:
        g4 += 25
    if concentration_90 < 0.22:
        g4 += 15
    scores["G4_缩量下跌+筹码守恒"] = {
        "score": g4,
        "label": "洗盘整理",
        "matched": g4 >= 75,
    }

    # ─── G5 放量下跌 + 筹码逃逸（主力出货） ──────────────────────────
    g5 = 0
    if ret5 < -0.03:
        g5 += 30
    if vol_ratio > 1.4:
        g5 += 30
    if lockup < 0.25:
        g5 += 25
    if dispersion > 0.10:
        g5 += 15
    scores["G5_放量下跌+筹码逃逸"] = {
        "score": g5,
        "label": "主力出货",
        "matched": g5 >= 75,
    }

    # ─── G6 量价背离 + 筹码异常（陷阱） ──────────────────────────────
    g6 = 0
    # 价涨量缩 或 价跌量增（背离）
    if (ret5 > 0.02 and vol_ratio < 0.8) or (ret5 < -0.02 and vol_ratio > 1.4):
        g6 += 30
    if abs(corr) < 0.2:
        g6 += 25
    if dispersion > 0.15 or concentration_90 > 0.30:
        g6 += 25
    if abs(ret20) > 0.20 and profit_ratio > 0.85:
        # 涨幅过大且大部分筹码获利 → 陷阱可能
        g6 += 20
    scores["G6_量价背离+筹码异常"] = {
        "score": g6,
        "label": "陷阱预警",
        "matched": g6 >= 75,
    }

    # ─── 主导组合 ────────────────────────────────────────────────
    dominant = max(scores.items(), key=lambda x: x[1]["score"])

    return {
        "g_scores": scores,
        "dominant_combination": dominant[0],
        "dominant_score": dominant[1]["score"],
        "dominant_label": dominant[1]["label"],
    }


def analyze(code: str) -> Dict[str, Any]:
    records = _load_kline(code, days=60)
    if not records or len(records) < 20:
        return {"code": code, "error": f"K 线不足（{len(records)}）"}

    chip_data = _load_chip(code)
    if not chip_data or "indicators" not in chip_data:
        return {"code": code, "error": "筹码数据缺失，请先运行 chip_distribution_analyzer.py"}

    features = _extract_features(records)
    g_result = match_g_combinations(features, chip_data["indicators"])

    return {
        "code": code,
        "as_of": records[-1].get("日期", ""),
        "current_price": features.get("current_price"),
        "price_volume_features": features,
        "G_combinations": g_result,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="G1-G6 三维联动验证器 (v1.16 — faces/资金面.md 模块 1.7)")
    parser.add_argument("code")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--output")
    args = parser.parse_args()

    result = analyze(args.code)
    out_path = Path(args.output) if args.output else \
        FINANCIAL_DATA_DIR / f"{args.code}_g_combination.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if "error" in result:
            print(f"[g_combination_verifier] {args.code} 失败: {result['error']}")
            return 1
        gc = result.get("G_combinations", {})
        print(f"[g_combination_verifier] {args.code} 完成 → {out_path}")
        print(f"  主导组合: {gc.get('dominant_combination')} "
              f"({gc.get('dominant_score')}/100, {gc.get('dominant_label')})")
        for name, info in gc.get("g_scores", {}).items():
            mark = "✓" if info.get("matched") else " "
            print(f"  [{mark}] {name}: {info['score']}/100  ({info['label']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
