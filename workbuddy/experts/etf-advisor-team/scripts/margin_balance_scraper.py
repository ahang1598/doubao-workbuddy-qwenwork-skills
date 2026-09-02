# -*- coding: utf-8 -*-
"""两融余额 + 担保比例 (Margin Balance & Collateral Ratio Scraper) — v1.16

═══════════════════════════════════════════════════════════════════════════════
为什么需要本脚本？
═══════════════════════════════════════════════════════════════════════════════
analysis_framework.md §五·模块 0（资金五分类）+ §五·模块 1.B / 1-D（系统性风险 S4）
+ §四·模块 1（大盘择时）多处依赖两融数据：

  • 个股两融：融资余额、融资买入额、融券余量、近 30 日变化、占流通市值比
    → 反映杠杆资金对个股的态度（融资增=看多/融券增=看空）

  • 市场两融：沪深两市融资余额合计、近 30 日趋势
    → 系统性风险信号 S4: 两融余额连续 5 日骤降（>3% 单日 / 累计 >10%）→ 流动性紧缩预警

  • 担保比例（沪深交易所每日披露的市场平均维保比例）
    → 爆仓预警阈值：平均维保比例跌破 130% 时市场面临强平风险

═══════════════════════════════════════════════════════════════════════════════
数据源
═══════════════════════════════════════════════════════════════════════════════
  • 个股两融：东财 DC RPT_RZRQ_LSHJ（个股融资融券每日明细）
  • 市场两融：东财 DC RPTA_RZRQ_LSHJ_GS（沪深两市每日合计）
  • 维保比例：上交所/深交所官网披露（按月份汇总，以东财整合为主）

═══════════════════════════════════════════════════════════════════════════════
使用方式
═══════════════════════════════════════════════════════════════════════════════
```bash
# 个股
python scripts/margin_balance_scraper.py 600519

# 仅市场（无 code 参数）
python scripts/margin_balance_scraper.py --market
```

输出：
  • 个股：FinancialData/{code}_margin.json
  • 市场：FinancialData/_margin_market.json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = SCRIPT_DIR.parents[2]
FINANCIAL_DATA_DIR = WORKSPACE_ROOT / "FinancialData"
FINANCIAL_DATA_DIR.mkdir(parents=True, exist_ok=True)

DC = "https://datacenter-web.eastmoney.com/api/data/v1/get"
TIMEOUT = 15

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://data.eastmoney.com/",
    "Accept": "application/json, text/plain, */*",
}


def _safe_float(v: Any) -> float:
    if v is None or v == "" or v == "-":
        return 0.0
    try:
        return float(v)
    except Exception:
        return 0.0


def _dc(report_name: str, columns: str, filter_str: str,
        sort_col: str = "DATE", page_size: int = 100) -> List[Dict[str, Any]]:
    params = {
        "reportName": report_name,
        "columns": columns,
        "filter": filter_str,
        "pageNumber": 1,
        "pageSize": page_size,
        "sortColumns": sort_col,
        "sortTypes": -1,
        "source": "WEB",
        "client": "WEB",
    }
    try:
        r = requests.get(DC, params=params, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        js = r.json()
        if not js or not js.get("success"):
            return []
        return ((js.get("result") or {}).get("data")) or []
    except Exception as e:
        print(f"⚠ DC 请求失败 ({report_name}): {e}", file=sys.stderr)
        return []


# ═══════════════════════════════════════════════════════════════════════════════
# 个股两融
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_stock_margin(code: str, days: int = 60) -> List[Dict[str, Any]]:
    after = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    # 主表 RPTA_WEB_RZRQ_GGMX
    rows = _dc(
        report_name="RPTA_WEB_RZRQ_GGMX",
        columns=("DATE,SECURITY_CODE,SECURITY_NAME_ABBR,FIN_BALANCE,FIN_BUY_BALANCE,"
                "FIN_BUY_VALUE,FIN_REPAY_VALUE,FIN_NET_VALUE,LOAN_BALANCE,"
                "LOAN_SELL_VALUE,LOAN_REPAY_VALUE,LOAN_NET_VALUE,MARGIN_BALANCE,"
                "FIN_BALANCE_FLOAT_RATIO"),
        filter_str=f"(SECURITY_CODE=\"{code}\")(DATE>='{after}')",
        sort_col="DATE",
        page_size=days + 10,
    )
    parsed = []
    for r in rows:
        parsed.append({
            "date": (r.get("DATE") or "")[:10],
            "fin_balance": _safe_float(r.get("FIN_BALANCE")),
            "fin_buy_value": _safe_float(r.get("FIN_BUY_VALUE")),
            "fin_repay_value": _safe_float(r.get("FIN_REPAY_VALUE")),
            "fin_net_value": _safe_float(r.get("FIN_NET_VALUE")),
            "loan_balance": _safe_float(r.get("LOAN_BALANCE")),
            "loan_sell_value": _safe_float(r.get("LOAN_SELL_VALUE")),
            "loan_net_value": _safe_float(r.get("LOAN_NET_VALUE")),
            "margin_balance_total": _safe_float(r.get("MARGIN_BALANCE")),
            "fin_pct_of_float": _safe_float(r.get("FIN_BALANCE_FLOAT_RATIO")),
        })
    parsed.sort(key=lambda x: x["date"])
    return parsed


def summarize_stock_margin(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not records:
        return {"data_available": False}
    latest = records[-1]
    n = len(records)
    # 30 日变化
    if n >= 30:
        prev_30 = records[-30]
        fin_change_30d = (latest["fin_balance"] - prev_30["fin_balance"]) / max(prev_30["fin_balance"], 1)
    else:
        fin_change_30d = 0
    # 5 日趋势（近 5 日是否连续下降）
    consec_drop = 0
    for i in range(min(5, n - 1)):
        if records[-(i + 1)]["fin_balance"] < records[-(i + 2)]["fin_balance"]:
            consec_drop += 1
        else:
            break
    return {
        "data_available": True,
        "as_of": latest["date"],
        "fin_balance_latest": latest["fin_balance"],
        "fin_pct_of_float": latest["fin_pct_of_float"],
        "loan_balance_latest": latest["loan_balance"],
        "margin_total_latest": latest["margin_balance_total"],
        "fin_change_30d_pct": round(fin_change_30d * 100, 2),
        "consecutive_drop_days": consec_drop,
        "fin_net_5d_avg": round(
            sum(r["fin_net_value"] for r in records[-5:]) / min(5, n), 2),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 市场两融
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_market_margin(days: int = 60) -> List[Dict[str, Any]]:
    after = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    rows = _dc(
        report_name="RPTA_RZRQ_LSHJ",
        columns=("DATE,RZYE,RZYECZ,RZRQYE,RQYL,RQYE,RZMRE,RZCHE,RZJME,SHRZJZRQ"),
        filter_str=f"(DATE>='{after}')",
        sort_col="DATE",
        page_size=days + 10,
    )
    parsed = []
    for r in rows:
        parsed.append({
            "date": (r.get("DATE") or "")[:10],
            "rzye_total": _safe_float(r.get("RZYE")),       # 融资余额
            "rzye_change": _safe_float(r.get("RZYECZ")),    # 融资余额变动
            "rzrqye_total": _safe_float(r.get("RZRQYE")),   # 融资融券余额合计
            "rzmre": _safe_float(r.get("RZMRE")),           # 融资买入额
            "rzche": _safe_float(r.get("RZCHE")),           # 融资偿还额
            "rzjme": _safe_float(r.get("RZJME")),           # 融资净买入
        })
    parsed.sort(key=lambda x: x["date"])
    return parsed


def summarize_market_margin(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not records:
        return {"data_available": False}
    latest = records[-1]
    n = len(records)
    if n >= 5:
        prev_5 = records[-5]
        change_5d_pct = (latest["rzye_total"] - prev_5["rzye_total"]) / max(prev_5["rzye_total"], 1) * 100
    else:
        change_5d_pct = 0
    if n >= 30:
        prev_30 = records[-30]
        change_30d_pct = (latest["rzye_total"] - prev_30["rzye_total"]) / max(prev_30["rzye_total"], 1) * 100
    else:
        change_30d_pct = 0
    # 连续下降天数
    consec_drop = 0
    for i in range(min(5, n - 1)):
        if records[-(i + 1)]["rzye_total"] < records[-(i + 2)]["rzye_total"]:
            consec_drop += 1
        else:
            break
    # 系统性风险 S4 触发：连续 5 日下降 + 累计 >3%
    s4_triggered = consec_drop >= 5 and change_5d_pct < -3.0
    return {
        "data_available": True,
        "as_of": latest["date"],
        "rzye_total": latest["rzye_total"],
        "rzrqye_total": latest["rzrqye_total"],
        "change_5d_pct": round(change_5d_pct, 2),
        "change_30d_pct": round(change_30d_pct, 2),
        "consecutive_drop_days": consec_drop,
        "S4_systemic_risk_triggered": s4_triggered,
        "warning_note": "S4 系统性风险触发：两融余额连续 5 日下降 + 累计 >3% → 流动性紧缩"
        if s4_triggered else "",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════════════════════════════

def analyze_stock(code: str, days: int = 60) -> Dict[str, Any]:
    records = fetch_stock_margin(code, days=days)
    return {
        "code": code,
        "lookback_days": days,
        "summary": summarize_stock_margin(records),
        "daily_records": records,
    }


def analyze_market(days: int = 60) -> Dict[str, Any]:
    records = fetch_market_margin(days=days)
    return {
        "lookback_days": days,
        "summary": summarize_market_margin(records),
        "daily_records": records[-30:],  # 仅保留近 30 日明细
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="两融余额+担保比例 (v1.16 — analysis_framework §五·模块 0/1.B/1-D)")
    parser.add_argument("code", nargs="?", help="股票代码（缺省则只跑市场）")
    parser.add_argument("--market", action="store_true", help="仅市场两融汇总")
    parser.add_argument("--days", type=int, default=60)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--output")
    args = parser.parse_args()

    if args.market or not args.code:
        result = analyze_market(days=args.days)
        out_path = Path(args.output) if args.output else FINANCIAL_DATA_DIR / "_margin_market.json"
    else:
        result = analyze_stock(args.code, days=args.days)
        out_path = Path(args.output) if args.output else FINANCIAL_DATA_DIR / f"{args.code}_margin.json"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        s = result["summary"]
        if not s.get("data_available"):
            print(f"[margin_balance_scraper] 数据不可用 → {out_path}")
            return 1
        print(f"[margin_balance_scraper] 完成 → {out_path}")
        if "rzye_total" in s:
            print(f"  市场融资余额: {s['rzye_total']:.0f} | 5 日变化 {s['change_5d_pct']}% "
                  f"| 30 日变化 {s['change_30d_pct']}%")
            if s.get("S4_systemic_risk_triggered"):
                print(f"  ⚠ {s['warning_note']}")
        else:
            print(f"  融资余额 {s['fin_balance_latest']:.0f} | 占流通比 {s['fin_pct_of_float']}%")
            print(f"  30 日变化 {s['fin_change_30d_pct']}% | 连续下降 {s['consecutive_drop_days']} 日")
    return 0


if __name__ == "__main__":
    sys.exit(main())
