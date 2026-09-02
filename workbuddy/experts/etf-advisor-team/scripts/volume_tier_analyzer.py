# -*- coding: utf-8 -*-
"""量能层级有效性比对 (Volume Tier Analyzer) — v1.18

═══════════════════════════════════════════════════════════════════════════════
为什么需要本脚本？
═══════════════════════════════════════════════════════════════════════════════
《六个面/技术面》§2.2 给出量能有效性的两条铁律：

  铁律 1：放量必须满足"≥ 过去 5-10 日均量 × 2 倍"且"持续 ≥ 2 日"才算有效，
          单日脉冲式放量多为资金对倒,不构成共识。

  铁律 2：周线级别量能 > 日线级别量能 > 分钟级别量能,大周期的量能变化才代表
          大资金的真实共识方向。"日线放量 + 周线缩量"的不一致是陷阱信号。

  →  仅看日线量能容易被"对倒、洗盘"误导,必须把日线/周线两级量能放在一起做
     交叉验证,才能判断"放量"是否构成有效共识。

本脚本输出每只个股的量能层级矩阵：
  ▸ 日线量能层级（5 档：极缩 / 缩量 / 正常 / 温和放量 / 异常放量）
  ▸ 周线量能层级（同 5 档）
  ▸ 一致性矩阵（5×5 表格,标记当前位置 + 历史对比）
  ▸ "有效共识"判定（日周双放量 → 真实共识；日线放量+周线缩量 → 假信号）

═══════════════════════════════════════════════════════════════════════════════
使用方式
═══════════════════════════════════════════════════════════════════════════════
```bash
python scripts/volume_tier_analyzer.py 600519
```

输出：FinancialData/{code}_volume_tier.json
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

# 量能档位分界（基于"过去 N 日均量"的倍数）
TIER_BOUNDS = [
    (0.40, "极缩"),
    (0.70, "缩量"),
    (1.30, "正常"),
    (2.00, "温和放量"),
    (float("inf"), "异常放量"),
]


def _load_kline(code: str, days: int = 200) -> List[Dict[str, Any]]:
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


def _classify_tier(ratio: float) -> str:
    for bound, label in TIER_BOUNDS:
        if ratio < bound:
            return label
    return "异常放量"


# ═══════════════════════════════════════════════════════════════════════════════
# 日线量能层级
# ═══════════════════════════════════════════════════════════════════════════════

def daily_volume_tier(records: List[Dict[str, Any]], window: int = 10) -> Dict[str, Any]:
    if len(records) < window + 5:
        return {}
    vols = [float(r.get("成交量", 0) or 0) for r in records]
    closes = [float(r.get("收盘", 0) or 0) for r in records]
    today_vol = vols[-1]
    avg = sum(vols[-window - 1:-1]) / window
    ratio = today_vol / avg if avg > 0 else 0
    tier = _classify_tier(ratio)

    # 是否持续性（近 2 日均放量）
    last2_avg = (vols[-1] + vols[-2]) / 2 if len(vols) >= 2 else 0
    sustained = last2_avg > avg * 2 if avg > 0 else False

    # 当前价格方向
    pct = (closes[-1] - closes[-2]) / closes[-2] * 100 if len(closes) >= 2 and closes[-2] > 0 else 0

    # 近 5 日各档位分布
    distribution: Dict[str, int] = {label: 0 for _, label in TIER_BOUNDS}
    for i in range(max(0, len(vols) - 5), len(vols)):
        if i < window:
            continue
        a = sum(vols[i - window:i]) / window
        if a > 0:
            t = _classify_tier(vols[i] / a)
            distribution[t] = distribution.get(t, 0) + 1

    return {
        "今日量比": round(ratio, 2),
        "当前档位": tier,
        "今日涨跌幅%": round(pct, 2),
        "持续性放量": sustained,
        "近5日分布": distribution,
        "均量窗口": window,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 周线量能层级（按 5 个交易日聚合）
# ═══════════════════════════════════════════════════════════════════════════════

def _to_weekly(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """日线→周线（每 5 日聚合，简化版本，不严格周对齐）"""
    weekly: List[Dict[str, Any]] = []
    for i in range(0, len(records), 5):
        chunk = records[i:i + 5]
        if not chunk:
            continue
        opens = [float(r.get("开盘", r.get("收盘", 0)) or 0) for r in chunk]
        closes = [float(r.get("收盘", 0) or 0) for r in chunk]
        highs = [float(r.get("最高", r.get("收盘", 0)) or 0) for r in chunk]
        lows = [float(r.get("最低", r.get("收盘", 0)) or 0) for r in chunk]
        vols = [float(r.get("成交量", 0) or 0) for r in chunk]
        weekly.append({
            "周起": chunk[0].get("交易日期"),
            "周止": chunk[-1].get("交易日期"),
            "开盘": opens[0],
            "收盘": closes[-1],
            "最高": max(highs) if highs else 0,
            "最低": min(lows) if lows else 0,
            "成交量": sum(vols),
        })
    return weekly


def weekly_volume_tier(records: List[Dict[str, Any]], window: int = 8) -> Dict[str, Any]:
    weekly = _to_weekly(records)
    if len(weekly) < window + 2:
        return {}
    vols = [r["成交量"] for r in weekly]
    closes = [r["收盘"] for r in weekly]
    today_vol = vols[-1]
    avg = sum(vols[-window - 1:-1]) / window
    ratio = today_vol / avg if avg > 0 else 0
    tier = _classify_tier(ratio)
    pct = (closes[-1] - closes[-2]) / closes[-2] * 100 if len(closes) >= 2 and closes[-2] > 0 else 0
    return {
        "本周量比": round(ratio, 2),
        "当前档位": tier,
        "本周涨跌幅%": round(pct, 2),
        "均量窗口": window,
        "周线样本数": len(weekly),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 一致性判定（5×5 矩阵）
# ═══════════════════════════════════════════════════════════════════════════════

CONSISTENCY_MATRIX = {
    # (日线, 周线) → 含义
    ("异常放量", "异常放量"): ("REAL_BREAKOUT", "日周双异常放量 → 共识真信号（强）"),
    ("异常放量", "温和放量"): ("REAL_BREAKOUT", "日周双放量 → 共识有效"),
    ("温和放量", "温和放量"): ("REAL_BREAKOUT", "稳健放量 → 健康共识"),
    ("温和放量", "异常放量"): ("REAL_BREAKOUT", "周线异常 → 大资金共识强"),
    ("异常放量", "正常"): ("FAKE_PULSE", "日线异常但周线未跟 → 单日对倒/脉冲风险"),
    ("异常放量", "缩量"): ("FAKE_PULSE", "日线放量 + 周线缩量 → 警惕陷阱"),
    ("温和放量", "缩量"): ("FAKE_PULSE", "短期放量但中期缩量 → 共识不足"),
    ("缩量", "缩量"): ("CONSENSUS_LOW", "日周双缩 → 共识极弱（震荡或筑底）"),
    ("缩量", "正常"): ("CONSENSUS_LOW", "日缩周稳 → 短期惜售"),
    ("正常", "正常"): ("NEUTRAL", "无明显特征"),
    ("极缩", "极缩"): ("EXTREME_QUIET", "极度地量 → 反转前置信号或长期低迷"),
}


def consistency(daily_tier: str, weekly_tier: str) -> Dict[str, Any]:
    key = (daily_tier, weekly_tier)
    if key in CONSISTENCY_MATRIX:
        code, desc = CONSISTENCY_MATRIX[key]
    else:
        code, desc = ("MIXED", f"日线={daily_tier} / 周线={weekly_tier}（混合,需结合价位与趋势）")
    color = {
        "REAL_BREAKOUT": "GREEN",
        "FAKE_PULSE": "RED",
        "CONSENSUS_LOW": "YELLOW",
        "EXTREME_QUIET": "YELLOW",
        "NEUTRAL": "GREY",
        "MIXED": "GREY",
    }.get(code, "GREY")
    return {"代码": code, "描述": desc, "等级": color}


# ═══════════════════════════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════════════════════════

def analyze(code: str) -> Optional[Dict[str, Any]]:
    records = _load_kline(code, days=200)
    if not records or len(records) < 30:
        print(f"[ERR] {code} K线数据不足", file=sys.stderr)
        return None
    d = daily_volume_tier(records)
    w = weekly_volume_tier(records)
    if not d or not w:
        print(f"[ERR] {code} 量能层级计算失败", file=sys.stderr)
        return None
    cons = consistency(d.get("当前档位", ""), w.get("当前档位", ""))
    out = {
        "股票代码": code,
        "日线量能": d,
        "周线量能": w,
        "一致性": cons,
        "档位定义": [
            {"档": label, "上限倍数": bound if bound != float("inf") else "∞"}
            for bound, label in TIER_BOUNDS
        ],
    }
    out_path = FINANCIAL_DATA_DIR / f"{code}_volume_tier.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] {code} 量能层级分析输出 → {out_path}")
    print(f"     日线={d.get('当前档位')}（量比 {d.get('今日量比')}）")
    print(f"     周线={w.get('当前档位')}（量比 {w.get('本周量比')}）")
    print(f"     一致性 → {cons.get('代码')}：{cons.get('描述')}")
    return out


def main():
    p = argparse.ArgumentParser(description="量能层级有效性比对器 v1.18")
    p.add_argument("code", help="A 股代码（6 位数字）")
    args = p.parse_args()
    if not (len(args.code) == 6 and args.code.isdigit()):
        print(f"[ERR] 非法 A 股代码：{args.code}", file=sys.stderr)
        sys.exit(1)
    res = analyze(args.code)
    if not res:
        sys.exit(1)


if __name__ == "__main__":
    main()
