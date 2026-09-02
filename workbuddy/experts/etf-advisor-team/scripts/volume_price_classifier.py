# -*- coding: utf-8 -*-
"""量价 6 组合自动识别器 (Volume-Price Combination Classifier) — v1.18

═══════════════════════════════════════════════════════════════════════════════
为什么需要本脚本？
═══════════════════════════════════════════════════════════════════════════════
faces/技术面.md 模块 4 列出 **量价六组合** 经典识别表（来自《六个面/技术面》）：

  VP1  量价齐升  价↑量↑(>1.3 倍均量)         多头共振 / 主升浪初段
  VP2  缩量上涨  价↑量↓(<0.7 倍均量)         惜售推升 / 主升浪中段
  VP3  放量滞涨  价微变量↑(>1.3 倍)          顶部预警 / 多空争夺
  VP4  缩量下跌  价↓量↓(<0.7 倍均量)         洗盘式回调 / 抛压衰竭
  VP5  放量下跌  价↓量↑(>1.3 倍均量)         主力出货 / 趋势反转
  VP6  量价背离  价新高量未跟 / 价新低量未配合  陷阱（顶背离/底背离）

与 g_combination_verifier 的差别：
  ▸ g_combination_verifier 同时融合"筹码维度"（依赖 chip_distribution_analyzer 输出）
  ▸ 本脚本**只使用 K 线量价**就能跑出结果，作为最轻量级的入口分类器
  ▸ 输出近 60 日逐日组合时间序列 + 当前组合 + 概率最大语义解读

═══════════════════════════════════════════════════════════════════════════════
使用方式
═══════════════════════════════════════════════════════════════════════════════
```bash
python scripts/volume_price_classifier.py 600519
python scripts/volume_price_classifier.py 600519 --days 90
```

输出：FinancialData/{code}_volume_price.json
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

# ═══════════════════════════════════════════════════════════════════════════════
# 阈值常量（可按市场风格调整）
# ═══════════════════════════════════════════════════════════════════════════════
VOL_HIGH_RATIO = 1.30   # 量比 > 1.30 → 放量
VOL_LOW_RATIO = 0.70    # 量比 < 0.70 → 缩量
PRICE_UP_PCT = 1.0      # 涨幅 > 1.0% → 上涨
PRICE_DOWN_PCT = -1.0   # 涨幅 < -1.0% → 下跌
PRICE_FLAT_PCT = 0.5    # |涨幅| < 0.5% → 滞涨
DIVERGENCE_NEW_EXT_WINDOW = 20  # 新高/新低判定窗口
MA_VOL_WINDOW = 5       # 量均线窗口（5 日均量）


# ═══════════════════════════════════════════════════════════════════════════════
# 数据加载（复用 chip_distribution_analyzer.fetch_kline_records 优先）
# ═══════════════════════════════════════════════════════════════════════════════

def _load_kline(code: str, days: int = 60) -> List[Dict[str, Any]]:
    try:
        import chip_distribution_analyzer as cda  # type: ignore
        recs = cda.fetch_kline_records(code, days=days)
        if recs:
            return recs
    except Exception:
        pass
    cache = FINANCIAL_DATA_DIR / f"{code}_kline.json"
    if cache.exists():
        try:
            d = json.loads(cache.read_text(encoding="utf-8"))
            recs = d.get("K线数据", []) if isinstance(d, dict) else d
            return recs[-days:] if isinstance(recs, list) else []
        except Exception:
            return []
    return []


# ═══════════════════════════════════════════════════════════════════════════════
# 单日组合判定
# ═══════════════════════════════════════════════════════════════════════════════

def _classify_one_day(
    today_close: float,
    prev_close: float,
    today_vol: float,
    avg_vol: float,
    is_new_high: bool,
    is_new_low: bool,
    vol_at_recent_high: float,
    vol_at_recent_low: float,
) -> Dict[str, Any]:
    """对单日返回：组合代码 + 描述 + 量比 + 涨幅"""
    if prev_close <= 0:
        return {"组合": "VP_INVALID", "描述": "前收盘缺失", "量比": 0, "涨跌幅%": 0}
    pct = (today_close - prev_close) / prev_close * 100
    vol_ratio = today_vol / avg_vol if avg_vol > 0 else 0

    # 优先识别 VP6 量价背离
    if is_new_high and vol_at_recent_high > 0 and today_vol < vol_at_recent_high * 0.85:
        return {
            "组合": "VP6_顶背离",
            "描述": "价创新高量未跟（顶背离 → 警惕反转）",
            "量比": round(vol_ratio, 2),
            "涨跌幅%": round(pct, 2),
            "信号": "RED",
        }
    if is_new_low and vol_at_recent_low > 0 and today_vol < vol_at_recent_low * 0.85:
        return {
            "组合": "VP6_底背离",
            "描述": "价创新低量未配（底背离 → 抛压衰竭）",
            "量比": round(vol_ratio, 2),
            "涨跌幅%": round(pct, 2),
            "信号": "GREEN",
        }

    # 其余 5 组合
    if pct > PRICE_UP_PCT and vol_ratio > VOL_HIGH_RATIO:
        return {
            "组合": "VP1_量价齐升",
            "描述": "多头共振 / 主升浪初段（最强买点候选）",
            "量比": round(vol_ratio, 2),
            "涨跌幅%": round(pct, 2),
            "信号": "GREEN",
        }
    if pct > PRICE_UP_PCT and vol_ratio < VOL_LOW_RATIO:
        return {
            "组合": "VP2_缩量上涨",
            "描述": "惜售推升 / 主升浪中段（持有为主）",
            "量比": round(vol_ratio, 2),
            "涨跌幅%": round(pct, 2),
            "信号": "GREEN",
        }
    if abs(pct) < PRICE_FLAT_PCT and vol_ratio > VOL_HIGH_RATIO:
        return {
            "组合": "VP3_放量滞涨",
            "描述": "顶部预警 / 多空争夺（减仓警示）",
            "量比": round(vol_ratio, 2),
            "涨跌幅%": round(pct, 2),
            "信号": "ORANGE",
        }
    if pct < PRICE_DOWN_PCT and vol_ratio < VOL_LOW_RATIO:
        return {
            "组合": "VP4_缩量下跌",
            "描述": "洗盘式回调 / 抛压衰竭（择机布局）",
            "量比": round(vol_ratio, 2),
            "涨跌幅%": round(pct, 2),
            "信号": "YELLOW",
        }
    if pct < PRICE_DOWN_PCT and vol_ratio > VOL_HIGH_RATIO:
        return {
            "组合": "VP5_放量下跌",
            "描述": "主力出货 / 趋势反转（离场信号）",
            "量比": round(vol_ratio, 2),
            "涨跌幅%": round(pct, 2),
            "信号": "RED",
        }
    return {
        "组合": "VP_NEUTRAL",
        "描述": "中性区间（量价无极端特征）",
        "量比": round(vol_ratio, 2),
        "涨跌幅%": round(pct, 2),
        "信号": "GREY",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 时间序列扫描
# ═══════════════════════════════════════════════════════════════════════════════

def classify_series(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """对每日生成量价组合标签（需要前 MA_VOL_WINDOW 日预热）"""
    if len(records) < MA_VOL_WINDOW + 2:
        return []
    closes = [float(r.get("收盘", 0) or 0) for r in records]
    vols = [float(r.get("成交量", 0) or 0) for r in records]
    highs = [float(r.get("最高", r.get("收盘", 0)) or 0) for r in records]
    lows = [float(r.get("最低", r.get("收盘", 0)) or 0) for r in records]
    dates = [r.get("交易日期", r.get("日期", "")) for r in records]

    series: List[Dict[str, Any]] = []
    for i in range(MA_VOL_WINDOW, len(records)):
        # 5 日均量（不含当日）
        avg_vol = sum(vols[i - MA_VOL_WINDOW:i]) / MA_VOL_WINDOW
        # 新高/新低 判定窗口
        win_lo = max(0, i - DIVERGENCE_NEW_EXT_WINDOW)
        prev_high_window = highs[win_lo:i]
        prev_low_window = lows[win_lo:i]
        is_new_high = bool(prev_high_window) and highs[i] > max(prev_high_window)
        is_new_low = bool(prev_low_window) and lows[i] < min(prev_low_window)
        # 历史新高对应日的量
        vol_at_recent_high = 0.0
        vol_at_recent_low = 0.0
        if prev_high_window:
            idx_h = win_lo + prev_high_window.index(max(prev_high_window))
            vol_at_recent_high = vols[idx_h]
        if prev_low_window:
            idx_l = win_lo + prev_low_window.index(min(prev_low_window))
            vol_at_recent_low = vols[idx_l]

        tag = _classify_one_day(
            today_close=closes[i],
            prev_close=closes[i - 1],
            today_vol=vols[i],
            avg_vol=avg_vol,
            is_new_high=is_new_high,
            is_new_low=is_new_low,
            vol_at_recent_high=vol_at_recent_high,
            vol_at_recent_low=vol_at_recent_low,
        )
        tag["交易日期"] = dates[i]
        tag["收盘"] = round(closes[i], 2)
        series.append(tag)
    return series


# ═══════════════════════════════════════════════════════════════════════════════
# 概率最大解读 + 主导组合统计
# ═══════════════════════════════════════════════════════════════════════════════

def summarize(series: List[Dict[str, Any]], lookback: int = 20) -> Dict[str, Any]:
    if not series:
        return {"主导组合": None, "近期分布": {}, "当前组合": None}
    recent = series[-lookback:]
    counter: Dict[str, int] = {}
    for s in recent:
        k = s.get("组合", "VP_NEUTRAL")
        counter[k] = counter.get(k, 0) + 1
    # 主导（除 NEUTRAL 外占比最高）
    sorted_items = sorted(
        [(k, v) for k, v in counter.items() if k != "VP_NEUTRAL"],
        key=lambda x: -x[1],
    )
    dominant = sorted_items[0][0] if sorted_items else "VP_NEUTRAL"
    return {
        "当前组合": series[-1].get("组合"),
        "当前信号": series[-1].get("信号"),
        "当前描述": series[-1].get("描述"),
        f"最近{lookback}日主导组合": dominant,
        f"最近{lookback}日分布": counter,
        "时序长度": len(series),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════════════════════════

def analyze(code: str, days: int = 60) -> Optional[Dict[str, Any]]:
    records = _load_kline(code, days=days)
    if not records or len(records) < MA_VOL_WINDOW + 2:
        return None
    series = classify_series(records)
    summary = summarize(series, lookback=20)
    out = {
        "股票代码": code,
        "数据范围": {"起": series[0].get("交易日期") if series else None,
                "止": series[-1].get("交易日期") if series else None,
                "天数": len(series)},
        "汇总": summary,
        "时间序列": series,
        "阈值参数": {
            "放量量比阈": VOL_HIGH_RATIO,
            "缩量量比阈": VOL_LOW_RATIO,
            "上涨阈%": PRICE_UP_PCT,
            "下跌阈%": PRICE_DOWN_PCT,
            "滞涨绝对值阈%": PRICE_FLAT_PCT,
            "背离窗口日": DIVERGENCE_NEW_EXT_WINDOW,
            "量均线窗口日": MA_VOL_WINDOW,
        },
    }
    out_path = FINANCIAL_DATA_DIR / f"{code}_volume_price.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] {code} 量价六组合分析输出 → {out_path}")
    print(f"     当前组合：{summary.get('当前组合')} | 信号={summary.get('当前信号')}")
    print(f"     最近20日主导：{summary.get('最近20日主导组合')}")
    return out


def main():
    p = argparse.ArgumentParser(description="量价 6 组合自动识别器 v1.18")
    p.add_argument("code", help="股票代码（6 位数字）")
    p.add_argument("--days", type=int, default=60, help="K线回看天数（默认 60）")
    args = p.parse_args()
    res = analyze(args.code, days=args.days)
    if not res:
        print(f"[ERR] {args.code} 数据不足或抓取失败", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
