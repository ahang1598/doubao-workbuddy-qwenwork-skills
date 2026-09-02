# -*- coding: utf-8 -*-
"""资金潮汐三周期分类器 (Capital Tide Classifier) — v1.18

═══════════════════════════════════════════════════════════════════════════════
为什么需要本脚本？
═══════════════════════════════════════════════════════════════════════════════
《六个面/基于第一性原理的股票资金面研究全体系.md》§3.2 提出**资金潮汐三周期**：

  长周期（宏观流动性周期）：央行货币政策决定 → 宽松 / 收紧 / 中性
  中周期（股市资金周期）   ：股市赚钱效应决定 → 增量 / 存量 / 减量
  短周期（板块资金周期）   ：行业景气度决定   → 上升 / 高峰 / 下降 / 低谷

faces/资金面.md 模块 1.1 要求"任何个股交易决策必须先确认所处资金潮汐
三周期"，本脚本输出统一周期标签，供 trade_advisor / phase_triangle_detector 引用。

═══════════════════════════════════════════════════════════════════════════════
判定规则（最简明可复现版）
═══════════════════════════════════════════════════════════════════════════════
长周期（宏观流动性）：
  - 看 M2 同比近 3 期方向 + LPR 近 6 期方向
  - M2 上升 & LPR 下降        → 宽松
  - M2 下降 & LPR 上升        → 收紧
  - 其它                       → 中性

中周期（股市资金）：
  - 看 沪深 300 近 60 日累计涨幅 + 融资余额近 30 日变化（来自 margin_balance_scraper）
  - 涨幅 > 5% & 两融上升 > 3%   → 增量
  - 涨幅 ∈ [-3%, 5%]            → 存量
  - 涨幅 < -3% & 两融下降 > 3%  → 减量

短周期（板块资金）：
  - 看个股所在行业近 30 日资金净流入（capital_flow_scraper）+ 板块涨幅
  - 涨幅 > 8% & 资金净流入       → 上升
  - 涨幅 ∈ [3%, 8%] & 流入放缓   → 高峰
  - 涨幅 < -3% & 资金净流出      → 下降
  - 涨幅 ∈ [-3%, 3%] & 流出放缓  → 低谷

═══════════════════════════════════════════════════════════════════════════════
使用方式
═══════════════════════════════════════════════════════════════════════════════
```bash
python scripts/capital_tide_classifier.py 600519
python scripts/capital_tide_classifier.py --market-only
```

输出：FinancialData/{code}_capital_tide.json  或  FinancialData/market_capital_tide.json
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
# 长周期：宏观流动性周期
# ═══════════════════════════════════════════════════════════════════════════════

def _read_macro() -> List[Dict[str, Any]]:
    p = FINANCIAL_DATA_DIR / "macro_data.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _latest_macro_series(macro: List[Dict[str, Any]], indicator: str, value_field_keywords: List[str]) -> List[float]:
    """从 macro_data.json 抽取某指标的近期数值序列（按时间倒序变正序，长度 6）"""
    for item in macro:
        if item.get("indicator") == indicator:
            data = item.get("data", []) or []
            vals: List[float] = []
            for row in data[:6]:  # 取近 6 期
                for k in value_field_keywords:
                    if k in row and isinstance(row[k], (int, float)):
                        vals.append(float(row[k]))
                        break
            return list(reversed(vals))  # 旧→新
    return []


def classify_macro_cycle() -> Dict[str, Any]:
    macro = _read_macro()
    if not macro:
        return {"周期": "UNKNOWN", "说明": "缺少 macro_data.json，先跑 macro_data_scraper"}
    m2 = _latest_macro_series(macro, "M2", ["M2同比(%)", "同比(%)"])
    lpr1y = _latest_macro_series(macro, "LPR", ["LPR_1Y(%)", "1年期LPR(%)", "LPR1Y(%)", "LPR_1年(%)"])
    if not m2 or not lpr1y:
        # 退化：只看 M2
        if len(m2) >= 3:
            up = m2[-1] > m2[0]
            return {
                "周期": "宽松" if up else "收紧",
                "说明": "仅基于 M2 同比方向（缺 LPR）",
                "M2_同比序列": m2,
            }
        return {"周期": "UNKNOWN", "说明": "M2/LPR 数据不足"}
    m2_up = m2[-1] > m2[0]
    lpr_down = lpr1y[-1] < lpr1y[0]
    if m2_up and lpr_down:
        cycle = "宽松"
    elif (not m2_up) and (not lpr_down) and lpr1y[-1] > lpr1y[0]:
        cycle = "收紧"
    else:
        cycle = "中性"
    return {
        "周期": cycle,
        "说明": f"M2 同比方向={'升' if m2_up else '降'}, LPR1Y 方向={'降' if lpr_down else '升/平'}",
        "M2_同比序列": m2,
        "LPR_1Y_序列": lpr1y,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 中周期：股市资金周期（沪深 300 + 两融）
# ═══════════════════════════════════════════════════════════════════════════════

def _read_hs300_kline(days: int = 60) -> List[Dict[str, Any]]:
    """读取沪深 300 K线（push2his.eastmoney.com 同口径）"""
    candidates = ["hs300_kline.json", "000300_kline.json", "hs300_kline_60d.json"]
    for name in candidates:
        p = FINANCIAL_DATA_DIR / name
        if p.exists():
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
                recs = d.get("K线数据", []) if isinstance(d, dict) else d
                if isinstance(recs, list):
                    return recs[-days:]
            except Exception:
                continue
    # 兜底：实时抓取
    try:
        import requests
        url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
        params = {
            "secid": "1.000300",
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
            "klt": "101", "fqt": "1", "end": "20500101", "lmt": str(days),
        }
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json().get("data", {}) or {}
        klines = data.get("klines", []) or []
        recs = []
        for line in klines:
            f = line.split(",")
            if len(f) >= 6:
                recs.append({
                    "交易日期": f[0],
                    "开盘": float(f[1]),
                    "收盘": float(f[2]),
                    "最高": float(f[3]),
                    "最低": float(f[4]),
                    "成交量": float(f[5]),
                })
        return recs
    except Exception:
        return []


def _read_market_margin_change() -> Optional[float]:
    """读取市场两融近 30 日变化%（依赖 margin_balance_scraper 输出）"""
    p = FINANCIAL_DATA_DIR / "market_margin_balance.json"
    if not p.exists():
        return None
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        series = d.get("市场两融余额序列", []) or d.get("series", []) or []
        if len(series) < 30:
            return None
        old = series[-30].get("两融余额", series[-30].get("RZRQYE", 0))
        new = series[-1].get("两融余额", series[-1].get("RZRQYE", 0))
        if not old:
            return None
        return (new - old) / old * 100
    except Exception:
        return None


def classify_market_cycle() -> Dict[str, Any]:
    kline = _read_hs300_kline(60)
    if len(kline) < 30:
        return {"周期": "UNKNOWN", "说明": "缺少沪深 300 K线，先跑 macro_data_scraper 或本脚本兜底"}
    closes = [float(r.get("收盘", 0) or 0) for r in kline if r.get("收盘")]
    if len(closes) < 30:
        return {"周期": "UNKNOWN", "说明": "沪深 300 K线收盘缺失"}
    pct_60 = (closes[-1] - closes[0]) / closes[0] * 100
    margin_chg = _read_market_margin_change()
    # 判定
    if margin_chg is None:
        # 仅看指数
        if pct_60 > 5:
            cycle = "增量"
        elif pct_60 < -3:
            cycle = "减量"
        else:
            cycle = "存量"
        note = f"沪深300 60日涨幅={pct_60:.2f}%，两融数据缺失"
    else:
        if pct_60 > 5 and margin_chg > 3:
            cycle = "增量"
        elif pct_60 < -3 and margin_chg < -3:
            cycle = "减量"
        else:
            cycle = "存量"
        note = f"沪深300 60日涨幅={pct_60:.2f}%，两融30日变化={margin_chg:.2f}%"
    return {
        "周期": cycle,
        "说明": note,
        "沪深300_60日涨幅%": round(pct_60, 2),
        "市场两融30日变化%": round(margin_chg, 2) if margin_chg is not None else None,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 短周期：板块资金周期（个股所在行业）
# ═══════════════════════════════════════════════════════════════════════════════

def _read_sector_flow(code: str) -> Optional[Dict[str, Any]]:
    """读取该股所在行业资金流（依赖 capital_flow_scraper / sector_scraper 输出）"""
    p = FINANCIAL_DATA_DIR / f"{code}_capital_flow.json"
    if not p.exists():
        return None
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return d
    except Exception:
        return None


def classify_sector_cycle(code: str) -> Dict[str, Any]:
    flow = _read_sector_flow(code)
    if not flow:
        return {"周期": "UNKNOWN", "说明": f"缺少 {code}_capital_flow.json，先跑 capital_flow_scraper"}
    # 兼容多种字段名
    sector_pct_30d = flow.get("行业30日涨幅%") or flow.get("板块30日涨幅%")
    sector_inflow_30d = flow.get("行业30日净流入亿") or flow.get("板块30日净流入亿")
    sector_inflow_5d = flow.get("行业5日净流入亿") or flow.get("板块5日净流入亿")
    if sector_pct_30d is None or sector_inflow_30d is None:
        return {"周期": "UNKNOWN", "说明": "行业涨幅/资金流字段缺失，请扩展 capital_flow_scraper 输出"}
    # 流入放缓：5 日折年率 < 30 日折年率
    inflow_slowing = (
        sector_inflow_5d is not None and sector_inflow_30d != 0
        and (sector_inflow_5d / 5) < (sector_inflow_30d / 30) * 0.6
    )
    if sector_pct_30d > 8 and sector_inflow_30d > 0 and not inflow_slowing:
        cycle = "上升"
    elif 3 <= sector_pct_30d <= 8 and inflow_slowing:
        cycle = "高峰"
    elif sector_pct_30d < -3 and sector_inflow_30d < 0:
        cycle = "下降"
    elif -3 <= sector_pct_30d <= 3 and (sector_inflow_30d is None or abs(sector_inflow_30d) < abs(sector_inflow_5d or 0) * 5):
        cycle = "低谷"
    else:
        cycle = "中性"
    return {
        "周期": cycle,
        "说明": f"行业30日涨幅={sector_pct_30d}%，30日净流入={sector_inflow_30d}亿，5日={sector_inflow_5d}亿，流入放缓={inflow_slowing}",
        "行业30日涨幅%": sector_pct_30d,
        "行业30日净流入亿": sector_inflow_30d,
        "行业5日净流入亿": sector_inflow_5d,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════════════════════════

def _alignment_score(macro: str, market: str, sector: str) -> Dict[str, Any]:
    """三周期一致性评分（决定后续仓位与方向偏好）"""
    bullish_macro = macro in ("宽松",)
    bullish_market = market in ("增量",)
    bullish_sector = sector in ("上升",)
    bearish_macro = macro in ("收紧",)
    bearish_market = market in ("减量",)
    bearish_sector = sector in ("下降",)
    bull = sum([bullish_macro, bullish_market, bullish_sector])
    bear = sum([bearish_macro, bearish_market, bearish_sector])
    if bull == 3:
        verdict = "三周期共振多头（最强买点）"
        action = "AGGRESSIVE_LONG"
    elif bear == 3:
        verdict = "三周期共振空头（最弱卖点）"
        action = "EXIT"
    elif bull == 2 and bear == 0:
        verdict = "多头主导（顺势布局）"
        action = "LONG"
    elif bear == 2 and bull == 0:
        verdict = "空头主导（防御为主）"
        action = "DEFENSE"
    elif bull == 1 and bear == 1:
        verdict = "周期矛盾（观望）"
        action = "HOLD"
    else:
        verdict = "中性"
        action = "NEUTRAL"
    return {"评级": verdict, "建议动作": action, "多头计数": bull, "空头计数": bear}


def analyze(code: Optional[str] = None) -> Dict[str, Any]:
    macro = classify_macro_cycle()
    market = classify_market_cycle()
    sector = classify_sector_cycle(code) if code else {"周期": "N/A", "说明": "未指定股票代码"}

    align = _alignment_score(macro.get("周期", ""), market.get("周期", ""), sector.get("周期", ""))

    out = {
        "股票代码": code,
        "长周期_宏观流动性": macro,
        "中周期_股市资金": market,
        "短周期_板块资金": sector,
        "三周期一致性评级": align,
    }
    if code:
        out_path = FINANCIAL_DATA_DIR / f"{code}_capital_tide.json"
    else:
        out_path = FINANCIAL_DATA_DIR / "market_capital_tide.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] 资金潮汐三周期分析输出 → {out_path}")
    print(f"     长周期={macro.get('周期')} | 中周期={market.get('周期')} | 短周期={sector.get('周期')}")
    print(f"     一致性评级：{align.get('评级')} → {align.get('建议动作')}")
    return out


def main():
    p = argparse.ArgumentParser(description="资金潮汐三周期分类器 v1.18")
    p.add_argument("code", nargs="?", help="股票代码（不传则只分析市场层）")
    p.add_argument("--market-only", action="store_true", help="只分析长周期+中周期，不分析板块")
    args = p.parse_args()
    code = None if args.market_only else args.code
    analyze(code)


if __name__ == "__main__":
    main()
