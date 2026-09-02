# -*- coding: utf-8 -*-
"""
Logistics & Freight Scraper — 航运运价 / 物流景气（基本面 §外需+周期 · 情绪面 §宏观景气）

为什么需要：
  · 航运运价（SCFI 上海出口集运 / CCFI / BDI 波罗的海干散货）是**全球贸易与外需景气**的高频
    前瞻指标，直接关联航运、港口、外贸、大宗周期板块；
  · 快递/邮政业务量是**内需消费与电商景气**读数，关联快递物流、消费板块；
  · 现有信源缺物流运价维度，本脚本补齐周期/外需侧高频信号。

数据源（A 类一手 / B 类权威转引）：
  1. 东方财富 push2 — BDI 等全球指数行情（best-effort）
  2. 上海航运交易所 SCFI/CCFI（官网周报；多为图表/PDF，走 fallback web_fetch）
  3. 国家邮政局 快递业务量月报（官网；走 fallback web_fetch）

输出：FinancialData/logistics_freight.json

合规性：A 类一手为主；官网图表/PDF 类无结构化 API 者，输出 fallback_urls 供 web_fetch 补全。
  严禁引用 Wind/Clarksons 等付费墙数据。

用法：
  python logistics_freight_scraper.py
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

try:
    import requests
except ImportError:
    print("ERROR: requests required.", file=sys.stderr)
    sys.exit(1)

TIMEOUT = 25
PUSH2_GET = "https://push2.eastmoney.com/api/qt/stock/get"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://quote.eastmoney.com/",
    "Accept": "application/json, text/plain, */*",
}

# 东财全球指数 secid 候选（BDI/航运相关，best-effort，多候选级联）
GLOBAL_INDICES = [
    {"name": "BDI 波罗的海干散货指数", "secids": ["100.BDI", "100.UDI"]},
]


def _get(url: str, params: Dict[str, Any]) -> Any:
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"_error": str(e)}


def _safe_float(v: Any) -> float:
    if v in (None, "", "-"):
        return 0.0
    try:
        return float(v)
    except Exception:
        return 0.0


def fetch_index(name: str, secids: List[str]) -> Dict[str, Any] | None:
    for secid in secids:
        js = _get(PUSH2_GET, {
            "fields": "f43,f44,f45,f46,f57,f58,f60,f170,f171",
            "secid": secid, "fltt": 2,
        })
        data = (js or {}).get("data") or {}
        price = _safe_float(data.get("f43"))
        if data and price > 0:
            return {
                "name": name,
                "secid": secid,
                "code": data.get("f57"),
                "index_name": data.get("f58"),
                "latest": price,
                "change_pct": _safe_float(data.get("f170")),
                "prev_close": _safe_float(data.get("f60")),
            }
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="航运运价/物流景气")
    ap.add_argument("--out")
    args = ap.parse_args()

    print("[logistics_freight] fetching shipping/freight indices ...")
    indices: List[Dict[str, Any]] = []
    for it in GLOBAL_INDICES:
        rec = fetch_index(it["name"], it["secids"])
        if rec:
            indices.append(rec)

    signals: List[str] = []
    for rec in indices:
        chg = rec.get("change_pct", 0.0)
        if chg >= 3:
            signals.append(f"{rec['name']} 上涨 {chg}%（外需/贸易景气回暖）")
        elif chg <= -3:
            signals.append(f"{rec['name']} 下跌 {chg}%（外需/贸易景气走弱）")

    status = "ok" if indices else "degraded"
    summary = {
        "status": status,
        "index_count": len(indices),
        "signals": signals,
        "note": "SCFI/CCFI 集运指数与邮政快递业务量需 web_fetch 官网补全（见 fallback_urls）",
    }

    payload = {
        "metadata": {
            "scraper": "logistics_freight_scraper.py",
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "data_sources": [
                "东财 push2 全球指数 (A 类一手, best-effort)",
                "上海航运交易所 SCFI/CCFI 官网 (A 类一手, fallback)",
                "国家邮政局 月度业务量 (A 类一手, fallback)",
            ],
            "compliance": "A 类一手为主；图表/PDF 类无 API 者走 fallback；严禁付费墙数据",
        },
        "summary": summary,
        "indices": indices,
        "fallback_urls": {
            "scfi_ccfi": "https://www.sse.net.cn/index/singleIndex?indexType=scfi",
            "shipping_exchange": "https://www.chineseshipping.com.cn/",
            "post_bureau": "https://www.spb.gov.cn/gjyzj/c100015/common_list.shtml",
            "em_global": "https://quote.eastmoney.com/center/gridlist.html#global_quote",
            "web_search_scfi": "SCFI 上海出口集装箱运价指数 最新 一周",
            "web_search_express": "国家邮政局 快递业务量 月度 同比 最新",
            "web_search_bdi": "BDI 波罗的海干散货指数 最新 走势",
        },
    }
    out_path = Path(args.out) if args.out else \
        Path(__file__).resolve().parents[3] / "FinancialData" / "logistics_freight.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ok] wrote {out_path} status={status}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
