# -*- coding: utf-8 -*-
"""
Carbon Market Scraper — 碳市场行情（基本面 §双碳/环保政策 · 政策面配套）

为什么需要：
  · 全国碳排放权交易（CEA）价格、成交量是**双碳政策力度与高耗能行业成本**的直接读数，
    关联电力、钢铁、建材、化工、环保（CCER）等板块；
  · 欧盟碳价（EU ETS）是出口型高耗能企业 CBAM 碳关税成本的前瞻；
  · 现有信源缺碳市场维度，本脚本补齐双碳政策落地侧高频信号。

数据源（A 类一手 / B 类权威转引）：
  1. 全国碳排放权交易（上海环交所 / cneeex.com）CEA 成交价（官网公示，多为表格/公告，走 fallback）
  2. 北京/广州/湖北等地方碳市场（试点）
  3. CCER 自愿减排（生态环境部）
  4. 欧盟碳价 EU ETS（公开行情，走 fallback web_search）

输出：FinancialData/carbon_market.json

合规性：A 类一手为主；官网公告/表格类无结构化 API 者，输出 fallback_urls 供 web_fetch 补全。
  欧盟碳价仅取公开权威转引（标注 note），严禁付费墙数据。

用法：
  python carbon_market_scraper.py
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

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
}

# 全国碳市场（上海环交所）日行情接口候选（best-effort）
CNEEEX_CANDIDATES = [
    "https://www.cneeex.com/qgtpfqjy/mrgk/",          # 每日概况页
    "https://ets.shanghai.gov.cn/",                    # 上海环交所
]


def _get_json(url: str, params: Dict[str, Any] | None = None) -> Any:
    try:
        r = requests.get(url, params=params or {}, headers=HEADERS, timeout=TIMEOUT)
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


def fetch_cea_quote() -> Dict[str, Any] | None:
    """尝试抓取全国碳市场 CEA 收盘价（best-effort，多为公告页，常需 fallback）。"""
    # 全国碳市场暂无稳定公开 JSON 行情 API，主走 fallback；此处保留探测占位
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="碳市场行情")
    ap.add_argument("--out")
    args = ap.parse_args()

    print("[carbon_market] probing national carbon market quote ...")
    cea = fetch_cea_quote()

    quotes: List[Dict[str, Any]] = []
    if cea:
        quotes.append(cea)

    status = "ok" if quotes else "degraded"
    summary = {
        "status": status,
        "quote_count": len(quotes),
        "signals": [],
        "note": ("全国碳市场(CEA)/CCER/地方试点/EU ETS 行情多为官网公告或权威媒体转引，"
                 "无稳定公开 JSON API，请用 fallback_urls 经 web_fetch/web_search 补全。"),
    }

    payload = {
        "metadata": {
            "scraper": "carbon_market_scraper.py",
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "data_sources": [
                "全国碳排放权交易 上海环交所/cneeex.com (A 类一手, fallback)",
                "生态环境部 CCER (A 类一手, fallback)",
                "EU ETS 欧盟碳价 (公开权威转引, fallback)",
            ],
            "compliance": ("A 类一手为主；公告/表格类无 API 者走 fallback；"
                           "EU ETS 仅取公开权威转引并标注；严禁付费墙数据"),
        },
        "summary": summary,
        "quotes": quotes,
        "fallback_urls": {
            "national_cea": "https://www.cneeex.com/qgtpfqjy/mrgk/",
            "sh_ets": "https://www.cneeex.com/",
            "ccer_mee": "https://www.mee.gov.cn/ywgz/ydqhbh/wsqtkz/",
            "hubei_ets": "http://www.chee.com.cn/",
            "guangzhou_ets": "http://www.cnemission.com/",
            "web_search_cea": "全国碳市场 CEA 碳排放配额 收盘价 成交量 最新",
            "web_search_ccer": "CCER 自愿减排 价格 最新 成交",
            "web_search_euets": "EU ETS 欧盟碳价 EUA 最新 欧元/吨",
        },
    }
    out_path = Path(args.out) if args.out else \
        Path(__file__).resolve().parents[3] / "FinancialData" / "carbon_market.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ok] wrote {out_path} status={status}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
