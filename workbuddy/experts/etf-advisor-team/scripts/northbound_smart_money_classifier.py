# -*- coding: utf-8 -*-
"""北向资金长/短线二分分类器 (Northbound Smart-Money Classifier) — v1.18

═══════════════════════════════════════════════════════════════════════════════
为什么需要本脚本？
═══════════════════════════════════════════════════════════════════════════════
《六个面/资金面》§4.3.2 指出："北向资金"是个混合概念，它实际包含两类完全不同
的行为模式：

  A. 配置盘（Smart Money / 长线）：
     ▸ 主力席位：JPMorgan、Vanguard、BlackRock 等海外机构托管
     ▸ 行为特征：低换手 (turnover < 0.5%)、单边趋势（连续 N 日同方向）
     ▸ 决策依据：基本面 + 估值 + 宏观流动性
     ▸ 跟随价值：高 — 是真正反映"国际机构对 A 股长期判断"的信号

  B. 交易盘（Trading Book / 短线）：
     ▸ 主力席位：野村、巴克莱、HSBC（亚洲交易部）等
     ▸ 行为特征：高换手 (turnover > 1.5%)、来回 (3 日内反转 > 30%)
     ▸ 决策依据：技术面 + 量化模型 + 套利
     ▸ 跟随价值：低 — 噪音大，可能在三日内反向

第一性原理：**只有配置盘的方向才有跟随价值**，把两者混在一起看会失真。

本脚本基于 ccass_scraper 输出的 {code}_northbound.json，使用四维度评分把每日
北向变动近似拆分为"配置盘 vs 交易盘"，并输出净配置盘信号。

═══════════════════════════════════════════════════════════════════════════════
判定指标（5 维度复合）
═══════════════════════════════════════════════════════════════════════════════
  1. 换手率 turnover = abs(daily_chg_shares) / 总持股   (低=配置)
  2. 持仓方向连续性 streak = 连续同方向天数            (高=配置)
  3. 反转率 reversal = 3日内反转天数 / 3                (低=配置)
  4. 单日变动幅度的绝对值 / 60日均值                    (中等=配置, 极大=交易)
  5. 与股价同步性                                       (背离=配置, 同步=交易)

合成评分 0-100：> 60 配置盘主导 / 40-60 混合 / < 40 交易盘主导

═══════════════════════════════════════════════════════════════════════════════
使用方式
═══════════════════════════════════════════════════════════════════════════════
```bash
python scripts/northbound_smart_money_classifier.py 600519
```
依赖：FinancialData/{code}_northbound.json （ccass_scraper 输出）

输出：FinancialData/{code}_northbound_smart_money.json
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


def _load_northbound(code: str) -> Optional[List[Dict[str, Any]]]:
    p = FINANCIAL_DATA_DIR / f"{code}_northbound.json"
    if not p.exists():
        return None
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        rows = d.get("northbound", {}).get("history", []) or d.get("history", [])
        # 时间正序（最旧→最新）
        rows = sorted(rows, key=lambda r: r.get("HOLD_DATE", "") or "")
        return rows
    except Exception:
        return None


def _load_kline_closes(code: str) -> Dict[str, float]:
    """读取 K线生成 {date: close} 映射（用于股价同步性指标）"""
    out: Dict[str, float] = {}
    p = FINANCIAL_DATA_DIR / f"{code}_kline.json"
    if not p.exists():
        return out
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        recs = d.get("K线数据", []) if isinstance(d, dict) else d
        for r in recs:
            dt = r.get("交易日期") or r.get("日期")
            cl = r.get("收盘")
            if dt and cl:
                out[dt[:10]] = float(cl)
    except Exception:
        pass
    return out


# ═══════════════════════════════════════════════════════════════════════════════
# 五维度计算
# ═══════════════════════════════════════════════════════════════════════════════

def _compute_features(rows: List[Dict[str, Any]], price_map: Dict[str, float]) -> Dict[str, Any]:
    if len(rows) < 10:
        return {}
    shares = [float(r.get("SHARES_HOLD", 0) or 0) for r in rows]
    dates = [str(r.get("HOLD_DATE", ""))[:10] for r in rows]
    daily_chg = [shares[i] - shares[i - 1] for i in range(1, len(shares))]

    # 1. 平均换手率
    turnovers = []
    for i in range(1, len(shares)):
        if shares[i - 1] > 0:
            turnovers.append(abs(daily_chg[i - 1]) / shares[i - 1] * 100)
    avg_turnover = sum(turnovers) / len(turnovers) if turnovers else 0.0

    # 2. 方向连续性（最长 streak）
    if not daily_chg:
        max_streak = 0
    else:
        streak = 1
        max_streak = 1
        for i in range(1, len(daily_chg)):
            if (daily_chg[i] > 0 and daily_chg[i - 1] > 0) or \
               (daily_chg[i] < 0 and daily_chg[i - 1] < 0):
                streak += 1
                max_streak = max(max_streak, streak)
            else:
                streak = 1

    # 3. 反转率（3日内反转）
    reversal_days = 0
    total_check = 0
    for i in range(2, len(daily_chg)):
        total_check += 1
        win = daily_chg[i - 2:i + 1]
        pos = sum(1 for x in win if x > 0)
        neg = sum(1 for x in win if x < 0)
        if pos > 0 and neg > 0:
            reversal_days += 1
    reversal_rate = reversal_days / total_check if total_check else 0.0

    # 4. 极端单日占比
    abs_chg = [abs(x) for x in daily_chg]
    avg_abs = sum(abs_chg) / len(abs_chg) if abs_chg else 0
    extreme_days = sum(1 for x in abs_chg if x > avg_abs * 3)
    extreme_ratio = extreme_days / len(abs_chg) if abs_chg else 0

    # 5. 与股价同步性
    price_aligned = 0
    price_diverged = 0
    for i in range(1, len(rows)):
        d = dates[i]
        d_prev = dates[i - 1]
        if d in price_map and d_prev in price_map:
            price_chg = price_map[d] - price_map[d_prev]
            if (price_chg > 0 and daily_chg[i - 1] > 0) or (price_chg < 0 and daily_chg[i - 1] < 0):
                price_aligned += 1
            elif (price_chg > 0 and daily_chg[i - 1] < 0) or (price_chg < 0 and daily_chg[i - 1] > 0):
                price_diverged += 1
    sync_total = price_aligned + price_diverged
    sync_rate = price_aligned / sync_total if sync_total else 0.5

    return {
        "样本天数": len(rows),
        "平均日换手率%": round(avg_turnover, 4),
        "最长同向streak": max_streak,
        "3日内反转率": round(reversal_rate, 3),
        "极端单日占比": round(extreme_ratio, 3),
        "与股价同步率": round(sync_rate, 3),
        "净持股变动股数": shares[-1] - shares[0] if len(shares) >= 2 else 0,
    }


def _smart_money_score(feat: Dict[str, Any]) -> Dict[str, Any]:
    """合成评分 0-100，越高越倾向配置盘"""
    if not feat:
        return {"评分": None, "标签": "数据不足"}
    score = 50.0
    # 维度 1：低换手 → +
    turnover = feat.get("平均日换手率%", 0)
    if turnover < 0.3:
        score += 15
    elif turnover < 0.5:
        score += 10
    elif turnover > 1.5:
        score -= 15
    elif turnover > 1.0:
        score -= 8
    # 维度 2：长 streak → +
    streak = feat.get("最长同向streak", 0)
    if streak >= 8:
        score += 12
    elif streak >= 5:
        score += 6
    # 维度 3：低反转率 → +
    rev = feat.get("3日内反转率", 0.5)
    if rev < 0.2:
        score += 10
    elif rev > 0.5:
        score -= 12
    # 维度 4：极端日少 → +
    extreme = feat.get("极端单日占比", 0)
    if extreme < 0.05:
        score += 5
    elif extreme > 0.15:
        score -= 8
    # 维度 5：与价同步性 — 配置盘倾向逆势/无关，0.4-0.6 最佳
    sync = feat.get("与股价同步率", 0.5)
    if 0.40 <= sync <= 0.60:
        score += 5
    elif sync > 0.80 or sync < 0.20:
        score -= 5

    score = max(0.0, min(100.0, score))
    if score >= 60:
        label = "配置盘主导（跟随价值高）"
    elif score >= 40:
        label = "混合（需结合其它指标）"
    else:
        label = "交易盘主导（噪音大，少跟随）"
    return {"评分": round(score, 1), "标签": label}


# ═══════════════════════════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════════════════════════

def analyze(code: str) -> Optional[Dict[str, Any]]:
    rows = _load_northbound(code)
    if not rows:
        print(f"[ERR] 缺少 {code}_northbound.json，先跑 ccass_scraper.py northbound {code}", file=sys.stderr)
        return None
    price_map = _load_kline_closes(code)
    feat = _compute_features(rows, price_map)
    sm = _smart_money_score(feat)

    # 判定净配置盘信号方向
    net_chg = feat.get("净持股变动股数", 0) if feat else 0
    direction = "增持" if net_chg > 0 else ("减持" if net_chg < 0 else "持平")
    if sm.get("评分") is not None and sm["评分"] >= 60:
        signal = f"配置盘{direction}（高跟随价值）"
        signal_strength = "GREEN" if direction == "增持" else "RED"
    elif sm.get("评分") is not None and sm["评分"] >= 40:
        signal = f"混合{direction}（中等参考）"
        signal_strength = "YELLOW"
    else:
        signal = f"交易盘{direction}（噪音，少跟随）"
        signal_strength = "GREY"

    out = {
        "股票代码": code,
        "样本范围": {
            "起": str(rows[0].get("HOLD_DATE", ""))[:10],
            "止": str(rows[-1].get("HOLD_DATE", ""))[:10],
            "天数": len(rows),
        },
        "五维特征": feat,
        "配置盘评分": sm,
        "净持股变动方向": direction,
        "净信号": signal,
        "净信号等级": signal_strength,
        "判定阈值": {"配置盘 ≥": 60, "混合": "40-60", "交易盘 <": 40},
    }
    out_path = FINANCIAL_DATA_DIR / f"{code}_northbound_smart_money.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] {code} 北向长/短线分类输出 → {out_path}")
    print(f"     配置盘评分={sm.get('评分')} → {sm.get('标签')}")
    print(f"     净信号={signal}（{signal_strength}）")
    return out


def main():
    p = argparse.ArgumentParser(description="北向资金长/短线二分分类器 v1.18")
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
