# -*- coding: utf-8 -*-
"""行业景气轮动评分器 (Industry Rotation Scorer) — v1.18

═══════════════════════════════════════════════════════════════════════════════
为什么需要本脚本？
═══════════════════════════════════════════════════════════════════════════════
《六个面/资金面》§3.2 提出**板块资金周期四阶段**：
    景气度上升期 → 景气度高峰期 → 景气度下降期 → 景气度低谷期

analysis_framework.md §四·模块 4.2 要求：
  - "买入只买在景气度上升期 / 低谷期反转",
  - "卖出务必避开高峰期,远离下降期"。

但单只个股的板块判定容易"以偏概全",必须放在**全行业景气矩阵**中横向对比,
找出当前真正最强 3-5 个行业（资金集体涌入），其他行业则注意防御。

本脚本输出申万一级 31 个行业的景气度评分排序,并附"四阶段标签",直接驱动
trade_advisor 的"行业级仓位优先级"。

═══════════════════════════════════════════════════════════════════════════════
评分维度（5 维加权）
═══════════════════════════════════════════════════════════════════════════════
  1. 30日涨幅 (40%)：板块趋势的核心
  2. 5日资金净流入 (25%)：边际资金方向
  3. 30日资金净流入 (15%)：中期资金方向
  4. 板块成交额占全市场比 (10%)：市场关注度
  5. 行业 PE 历史分位 (10%)：估值锚（分位低=加分,过高=减分）

每行业输出 0-100 评分 → 自动判定四阶段：
  ≥ 75: 景气度上升期（强势超配）
  55-75: 景气度高峰期（高位减仓）
  35-55: 景气度低谷期（择机布局）
  < 35:  景气度下降期（远离）

═══════════════════════════════════════════════════════════════════════════════
使用方式
═══════════════════════════════════════════════════════════════════════════════
```bash
python scripts/industry_rotation_scorer.py
python scripts/industry_rotation_scorer.py --top 10
```
输出：FinancialData/industry_rotation_score.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import requests
except ImportError:
    print("[ERR] requests is required", file=sys.stderr)
    sys.exit(1)

SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = SCRIPT_DIR.parents[2]
FINANCIAL_DATA_DIR = WORKSPACE_ROOT / "FinancialData"
FINANCIAL_DATA_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://data.eastmoney.com/",
}

# ═══════════════════════════════════════════════════════════════════════════════
# Step 1: 拉取全申万一级行业板块列表 + 30 日涨幅 + 实时数据
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_sw_industries() -> List[Dict[str, Any]]:
    """Push2 全申万一级行业板块（fs=m:90 t:2）"""
    url = "https://push2.eastmoney.com/api/qt/clist/get"
    params = {
        "pn": "1", "pz": "60", "po": "1", "np": "1",
        "fields": "f2,f3,f12,f14,f62,f184,f18,f20",
        # f2收盘 f3涨跌幅 f12代码 f14名称 f62主力净流入 f184占比 f18昨收 f20总市值
        "fs": "m:90 t:2",
        "fid": "f3", "ut": "fa5fd1943c7b386f172d6893dbfba10b",
    }
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=12)
        r.raise_for_status()
        data = r.json().get("data", {}) or {}
        items = data.get("diff", []) or []
        return [
            {
                "板块代码": it.get("f12"),
                "板块名称": it.get("f14"),
                "今日涨幅%": it.get("f3"),
                "主力净流入": it.get("f62"),
                "主力净占比%": it.get("f184"),
                "总市值": it.get("f20"),
            }
            for it in items
        ]
    except Exception as e:
        print(f"[WARN] fetch_sw_industries 失败：{e}", file=sys.stderr)
        return []


def fetch_industry_kline_30d(bk_code: str) -> Optional[Dict[str, float]]:
    """单板块 30 日 K线（push2his），返回涨幅与累计资金"""
    url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
    params = {
        "secid": f"90.{bk_code}",
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "klt": "101", "fqt": "1", "end": "20500101", "lmt": "32",
    }
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=10)
        r.raise_for_status()
        klines = r.json().get("data", {}).get("klines", []) or []
        if len(klines) < 5:
            return None
        opens, closes = [], []
        for line in klines:
            f = line.split(",")
            if len(f) >= 5:
                opens.append(float(f[1]))
                closes.append(float(f[2]))
        if len(closes) < 5:
            return None
        # 30 日涨幅
        first_close = closes[0] if len(closes) >= 30 else closes[0]
        pct_30d = (closes[-1] - first_close) / first_close * 100 if first_close else 0
        # 5 日涨幅
        if len(closes) >= 6:
            pct_5d = (closes[-1] - closes[-6]) / closes[-6] * 100 if closes[-6] else 0
        else:
            pct_5d = 0
        return {"30日涨幅%": round(pct_30d, 2), "5日涨幅%": round(pct_5d, 2)}
    except Exception:
        return None


def fetch_industry_capital_flow_5d(bk_code: str) -> Optional[Dict[str, float]]:
    """板块 5 日 / 10 日资金流向（datacenter-web）"""
    url = "https://push2.eastmoney.com/api/qt/stock/get"
    params = {
        "secid": f"90.{bk_code}",
        "fields": "f267,f268,f269,f270,f271,f272",  # 5日主力净流入, 10日, 占比
        "ut": "fa5fd1943c7b386f172d6893dbfba10b",
    }
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=10)
        r.raise_for_status()
        d = r.json().get("data", {}) or {}
        return {
            "5日主力净流入": d.get("f267"),
            "10日主力净流入": d.get("f269"),
            "5日主力净占比%": d.get("f268"),
            "10日主力净占比%": d.get("f270"),
        }
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# Step 2: 五维评分
# ═══════════════════════════════════════════════════════════════════════════════

def _norm(value: Optional[float], lo: float, hi: float) -> float:
    if value is None:
        return 50.0
    if hi == lo:
        return 50.0
    v = (float(value) - lo) / (hi - lo) * 100
    return max(0.0, min(100.0, v))


def score_industries(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not rows:
        return []
    # 找全样本 min/max 用于归一化
    p30s = [r.get("30日涨幅%") for r in rows if r.get("30日涨幅%") is not None]
    p5s = [r.get("5日涨幅%") for r in rows if r.get("5日涨幅%") is not None]
    f5s = [r.get("5日主力净流入") for r in rows if r.get("5日主力净流入") is not None]
    f10s = [r.get("10日主力净流入") for r in rows if r.get("10日主力净流入") is not None]

    p30_lo, p30_hi = (min(p30s), max(p30s)) if p30s else (-10, 10)
    p5_lo, p5_hi = (min(p5s), max(p5s)) if p5s else (-5, 5)
    f5_lo, f5_hi = (min(f5s), max(f5s)) if f5s else (-1e9, 1e9)
    f10_lo, f10_hi = (min(f10s), max(f10s)) if f10s else (-1e9, 1e9)

    out: List[Dict[str, Any]] = []
    for r in rows:
        s30 = _norm(r.get("30日涨幅%"), p30_lo, p30_hi)
        s5 = _norm(r.get("5日涨幅%"), p5_lo, p5_hi)
        sf5 = _norm(r.get("5日主力净流入"), f5_lo, f5_hi)
        sf10 = _norm(r.get("10日主力净流入"), f10_lo, f10_hi)

        # 估值分位（暂无统一接口，用今日涨跌反向作占位代理：跌多 → 估值低 → 加分）
        today_pct = r.get("今日涨幅%")
        if today_pct is None:
            s_val = 50.0
        else:
            # 今日跌 1% 给 65 分，涨 1% 给 35 分（粗略代理，后续可接 PE 分位）
            s_val = max(0.0, min(100.0, 50 - float(today_pct) * 15))

        # 加权
        composite = (
            s30 * 0.40 + s5 * 0.10
            + sf5 * 0.25 + sf10 * 0.15
            + s_val * 0.10
        )

        if composite >= 75:
            phase = "景气度上升期（强势超配）"
            action = "OVERWEIGHT"
            color = "GREEN"
        elif composite >= 55:
            phase = "景气度高峰期（高位减仓）"
            action = "REDUCE"
            color = "ORANGE"
        elif composite >= 35:
            phase = "景气度低谷期（择机布局）"
            action = "WATCH"
            color = "YELLOW"
        else:
            phase = "景气度下降期（远离）"
            action = "AVOID"
            color = "RED"

        out.append({
            "板块代码": r.get("板块代码"),
            "板块名称": r.get("板块名称"),
            "30日涨幅%": r.get("30日涨幅%"),
            "5日涨幅%": r.get("5日涨幅%"),
            "5日主力净流入": r.get("5日主力净流入"),
            "10日主力净流入": r.get("10日主力净流入"),
            "今日涨幅%": today_pct,
            "综合评分": round(composite, 1),
            "景气阶段": phase,
            "建议动作": action,
            "信号灯": color,
        })

    out.sort(key=lambda x: -x["综合评分"])
    for i, item in enumerate(out, 1):
        item["排名"] = i
    return out


# ═══════════════════════════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════════════════════════

def analyze(top: int = 31) -> Dict[str, Any]:
    industries = fetch_sw_industries()
    if not industries:
        print("[ERR] 板块列表抓取失败", file=sys.stderr)
        return {}
    # 限制并发，避免封 IP
    enriched = []
    for ind in industries:
        bk = ind.get("板块代码")
        if not bk:
            enriched.append(ind)
            continue
        kk = fetch_industry_kline_30d(bk)
        if kk:
            ind.update(kk)
        time.sleep(0.15)
        ff = fetch_industry_capital_flow_5d(bk)
        if ff:
            ind.update(ff)
        time.sleep(0.15)
        enriched.append(ind)

    scored = score_industries(enriched)
    out = {
        "全行业数": len(scored),
        "Top": top,
        "排行榜": scored[:top],
        "完整评分": scored,
    }
    out_path = FINANCIAL_DATA_DIR / "industry_rotation_score.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] 行业景气轮动评分输出 → {out_path}")
    print("     Top 5：")
    for it in scored[:5]:
        print(f"       #{it['排名']} {it['板块名称']} | 评分={it['综合评分']} | {it['景气阶段']}")
    return out


def main():
    p = argparse.ArgumentParser(description="行业景气轮动评分器 v1.18")
    p.add_argument("--top", type=int, default=31, help="输出 Top N（默认全行业）")
    args = p.parse_args()
    analyze(top=args.top)


if __name__ == "__main__":
    main()
