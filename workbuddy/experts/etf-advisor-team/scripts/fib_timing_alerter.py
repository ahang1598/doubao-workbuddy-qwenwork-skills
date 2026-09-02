# -*- coding: utf-8 -*-
"""斐波时间窗口预警器 (Fibonacci Timing Alerter) — v1.18

═══════════════════════════════════════════════════════════════════════════════
为什么需要本脚本？
═══════════════════════════════════════════════════════════════════════════════
《六个面/技术面》§2.3 提出：

  斐波那契时间窗口（3 / 5 / 8 / 13 / 21 / 34 / 55 / 89）的本质，是共识的情绪周期
  与资金的持仓周期的共振点。从一个显著的"前期高点 / 低点"开始向后推算 N 个交易日,
  到达斐波数列的某一项时,是趋势反转的高概率时间节点。**该信号只作预警,不作
  交易唯一依据**。

虽然斐波时间窗口不能独立做决策,但作为 trade_advisor 的"时间维度过滤器"非常有价值：
  ▸ 当 phase_triangle_detector 给出"主升浪末段"的判断 + 同时落入斐波 21/34/55 窗口,
    则建议把仓位从 100% 降到 50%（双重确认顶部预警）。
  ▸ 当 phase_triangle_detector 给出"筑底反转"判断 + 同时落入斐波窗口,则把
    "首次试仓"提前到该窗口前 2 日布局。

═══════════════════════════════════════════════════════════════════════════════
算法
═══════════════════════════════════════════════════════════════════════════════
Step 1：从近 250 日 K 线中识别"显著高低点"（用滑动窗口 ±10 日内最高/最低）
Step 2：对每个锚点,推算 forward N 日（N ∈ FIB_SEQ）的窗口日期
Step 3：当前日落入未来 ±2 日的斐波窗口时给出预警
Step 4：输出未来 90 日内所有"高概率反转窗口"日历

═══════════════════════════════════════════════════════════════════════════════
使用方式
═══════════════════════════════════════════════════════════════════════════════
```bash
python scripts/fib_timing_alerter.py 600519
python scripts/fib_timing_alerter.py 600519 --pivot-window 10 --look-forward 90
```

输出：FinancialData/{code}_fib_timing.json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

WORKSPACE_ROOT = SCRIPT_DIR.parents[2]
FINANCIAL_DATA_DIR = WORKSPACE_ROOT / "FinancialData"

FIB_SEQ = [3, 5, 8, 13, 21, 34, 55, 89]
TOLERANCE_DAYS = 2  # 当前日落入窗口 ±2 日仍视为命中


def _load_kline(code: str, days: int = 250) -> List[Dict[str, Any]]:
    try:
        import chip_distribution_analyzer as cda  # type: ignore
        recs = cda.fetch_kline_records(code, days=days)
        if recs:
            return recs
    except Exception:
        pass
    p = FINANCIAL_DATA_DIR / f"{code}_kline.json"
    if p.exists():
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            recs = d.get("K线数据", []) if isinstance(d, dict) else d
            return recs[-days:] if isinstance(recs, list) else []
        except Exception:
            return []
    return []


# ═══════════════════════════════════════════════════════════════════════════════
# Step 1：识别显著高低点
# ═══════════════════════════════════════════════════════════════════════════════

def detect_pivots(records: List[Dict[str, Any]], window: int = 10) -> List[Dict[str, Any]]:
    """前后 window 日内的局部极值视为显著锚点"""
    pivots: List[Dict[str, Any]] = []
    if len(records) < window * 2 + 1:
        return pivots
    highs = [float(r.get("最高", r.get("收盘", 0)) or 0) for r in records]
    lows = [float(r.get("最低", r.get("收盘", 0)) or 0) for r in records]
    dates = [r.get("交易日期", r.get("日期", "")) for r in records]
    for i in range(window, len(records) - window):
        win_h = highs[i - window:i + window + 1]
        win_l = lows[i - window:i + window + 1]
        if highs[i] == max(win_h):
            pivots.append({"日期": dates[i], "类型": "HIGH", "价": highs[i], "索引": i})
        elif lows[i] == min(win_l):
            pivots.append({"日期": dates[i], "类型": "LOW", "价": lows[i], "索引": i})
    return pivots


# ═══════════════════════════════════════════════════════════════════════════════
# Step 2：从每个锚点推算斐波时间窗口
# ═══════════════════════════════════════════════════════════════════════════════

def project_fib_windows(pivots: List[Dict[str, Any]],
                        records: List[Dict[str, Any]],
                        look_forward_days: int = 90) -> List[Dict[str, Any]]:
    """对每个锚点向后推算 FIB_SEQ 中所有日期"""
    if not records:
        return []
    last_date_str = records[-1].get("交易日期", records[-1].get("日期", ""))
    try:
        last_date = datetime.fromisoformat(last_date_str[:10]).date()
    except Exception:
        last_date = datetime.now().date()
    look_end = last_date + timedelta(days=look_forward_days)

    windows: List[Dict[str, Any]] = []
    for piv in pivots:
        try:
            piv_date = datetime.fromisoformat(piv["日期"][:10]).date()
        except Exception:
            continue
        for fib in FIB_SEQ:
            target = piv_date + timedelta(days=int(fib * 1.45))  # 交易日近似自然日 = 1.45×
            if target < last_date - timedelta(days=10) or target > look_end:
                continue
            windows.append({
                "锚点日期": piv["日期"][:10],
                "锚点类型": piv["类型"],
                "锚点价": piv["价"],
                "斐波N": fib,
                "目标日期": target.isoformat(),
                "距今天数": (target - last_date).days,
            })
    windows.sort(key=lambda x: x["目标日期"])
    return windows


# ═══════════════════════════════════════════════════════════════════════════════
# Step 3：当前日是否命中
# ═══════════════════════════════════════════════════════════════════════════════

def find_active_alerts(windows: List[Dict[str, Any]], today: datetime) -> List[Dict[str, Any]]:
    today_d = today.date()
    active: List[Dict[str, Any]] = []
    for w in windows:
        try:
            tgt = datetime.fromisoformat(w["目标日期"]).date()
        except Exception:
            continue
        delta = abs((tgt - today_d).days)
        if delta <= TOLERANCE_DAYS:
            entry = dict(w)
            entry["命中偏差日"] = (tgt - today_d).days
            active.append(entry)
    return active


# ═══════════════════════════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════════════════════════

def analyze(code: str, pivot_window: int = 10, look_forward: int = 90) -> Optional[Dict[str, Any]]:
    records = _load_kline(code, days=250)
    if not records or len(records) < 30:
        print(f"[ERR] {code} K线数据不足", file=sys.stderr)
        return None

    pivots = detect_pivots(records, window=pivot_window)
    # 仅保留近 120 日的锚点（远端锚点穿透力衰减）
    pivots = pivots[-15:] if len(pivots) > 15 else pivots
    if not pivots:
        print(f"[WARN] {code} 未识别到显著高低点", file=sys.stderr)

    windows = project_fib_windows(pivots, records, look_forward_days=look_forward)
    active = find_active_alerts(windows, datetime.now())

    # 去重：同一目标日期可能多个锚点命中,保留最近锚点
    grouped: Dict[str, Dict[str, Any]] = {}
    for w in windows:
        key = w["目标日期"]
        if key not in grouped or w["锚点日期"] > grouped[key]["锚点日期"]:
            grouped[key] = w
    deduped = sorted(grouped.values(), key=lambda x: x["目标日期"])

    out = {
        "股票代码": code,
        "锚点窗口": pivot_window,
        "前瞻天数": look_forward,
        "斐波数列": FIB_SEQ,
        "显著高低点数": len(pivots),
        "显著高低点": pivots[-10:],  # 仅展示最近 10 个
        "未来斐波窗口": deduped,
        "当前命中预警": active,
        "预警判定": "ACTIVE" if active else "NO_ACTIVE_ALERT",
    }
    out_path = FINANCIAL_DATA_DIR / f"{code}_fib_timing.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] {code} 斐波时间窗口预警输出 → {out_path}")
    print(f"     锚点 {len(pivots)} 个 / 未来斐波窗口 {len(deduped)} 个")
    if active:
        for a in active:
            print(f"     ⚠ 命中 {a['目标日期']}（距今 {a['命中偏差日']} 日）"
                  f" 锚点={a['锚点类型']}@{a['锚点日期']} 斐波N={a['斐波N']}")
    else:
        print("     当前无活跃斐波窗口（仅作预警,非交易信号）")
    return out


def main():
    p = argparse.ArgumentParser(description="斐波时间窗口预警器 v1.18")
    p.add_argument("code", help="A 股代码（6 位数字）")
    p.add_argument("--pivot-window", type=int, default=10, help="高低点识别窗口（默认 ±10 日）")
    p.add_argument("--look-forward", type=int, default=90, help="向后预测天数（默认 90）")
    args = p.parse_args()
    if not (len(args.code) == 6 and args.code.isdigit()):
        print(f"[ERR] 非法 A 股代码：{args.code}", file=sys.stderr)
        sys.exit(1)
    res = analyze(args.code, pivot_window=args.pivot_window, look_forward=args.look_forward)
    if not res:
        sys.exit(1)


if __name__ == "__main__":
    main()
