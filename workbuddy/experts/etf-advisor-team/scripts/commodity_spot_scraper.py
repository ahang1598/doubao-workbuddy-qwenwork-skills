# -*- coding: utf-8 -*-
"""
Commodity Spot Scraper — 大宗商品现货价格 / 价格指数（基本面 §成本端 + 行业景气配套）

为什么需要：
  · 上游原材料现货价（铜/铝/钢/锂/煤/纯碱/化工品）是制造业、周期股成本端与毛利率的
    先行指标；现货-期货价差、生意社 BPI 大宗商品价格指数反映行业景气拐点；
  · 现有脚本（eia_energy / global_market）只覆盖原油与海外指数，缺一个国内大宗现货采集器。

数据源（A 类一手 / B 类权威转引）：
  1. 生意社 BPI 大宗商品价格指数 — www.100ppi.com（国内权威商品价格机构，公开页）
  2. 东方财富 期货行情 push2 — 主力合约现价（沪铜/沪铝/螺纹/铁矿/焦炭/纯碱/碳酸锂等）
       作为现货价格的高相关代理（现货数据多需 web_fetch 生意社/卓创补充）
  3. 降级兜底：生意社 / 卓创资讯 / 上海有色网 SMM（web_fetch 公开页）

输出：FinancialData/commodity_spot.json
      FinancialData/{code}_commodity.json   （--code 时输出该股相关品种）

合规性：东财公开行情 A 类；生意社/卓创为 B 类权威机构公开页，web_fetch 转引标注。

用法：
  python commodity_spot_scraper.py                  # 全品类主力期货 + BPI
  python commodity_spot_scraper.py --code 600362    # 江西铜业 -> 铜相关品种
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
PUSH2 = "https://push2.eastmoney.com/api/qt/stock/get"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://quote.eastmoney.com/",
    "Accept": "application/json, text/plain, */*",
}

# 主力期货合约 secid（东财：113.=上期所, 114.=大商所, 115.=郑商所, 142.=广期所连续）
# 使用连续主力合约代码 + 市场前缀
FUTURES = {
    "沪铜": "113.cu0", "沪铝": "113.al0", "沪锌": "113.zn0", "沪镍": "113.ni0",
    "螺纹钢": "113.rb0", "热卷": "113.hc0", "黄金": "113.au0", "白银": "113.ag0",
    "铁矿石": "114.i0", "焦炭": "114.j0", "焦煤": "114.jm0", "豆粕": "114.m0",
    "PVC": "114.v0", "塑料": "114.l0",
    "纯碱": "115.sa0", "玻璃": "115.fg0", "甲醇": "115.ma0", "PTA": "115.ta0",
    "棉花": "115.cf0", "白糖": "115.sr0", "尿素": "115.ur0",
    "碳酸锂": "142.lc0", "工业硅": "142.si0",
}

# 个股 -> 关注品种关键词（粗映射）
STOCK_COMMODITY = {
    "600362": ["沪铜"], "600111": ["碳酸锂"], "002460": ["碳酸锂"],
    "600019": ["螺纹钢", "热卷", "铁矿石"], "601012": ["工业硅"],
    "600426": ["纯碱"], "600160": ["纯碱"],
}


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


def fetch_future(name: str, secid: str) -> Dict[str, Any]:
    js = _get(PUSH2, {"fields": "f43,f44,f45,f46,f47,f48,f57,f58,f60,f170,f169", "secid": secid})
    d = (js or {}).get("data") or {}
    if not d:
        return {}
    # f43 现价(放大100), f170 涨跌幅(放大100), f169 涨跌额
    price = _safe_float(d.get("f43")) / 100 if d.get("f43") not in (None, "-") else None
    chg = _safe_float(d.get("f170")) / 100 if d.get("f170") not in (None, "-") else None
    return {
        "name": name,
        "contract": d.get("f58"),
        "price": price,
        "change_pct": chg,
        "secid": secid,
    }


def fetch_all_futures() -> List[Dict[str, Any]]:
    out = []
    for name, secid in FUTURES.items():
        info = fetch_future(name, secid)
        if info:
            out.append(info)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="大宗商品现货/期货价格采集")
    ap.add_argument("--code", help="个股代码，输出相关品种")
    ap.add_argument("--out")
    args = ap.parse_args()

    now = datetime.now().isoformat(timespec="seconds")
    fd = Path(__file__).resolve().parents[3] / "FinancialData"

    futures = fetch_all_futures()
    up = [f for f in futures if (f.get("change_pct") or 0) > 0]
    down = [f for f in futures if (f.get("change_pct") or 0) < 0]

    related: List[Dict[str, Any]] = []
    if args.code:
        kws = STOCK_COMMODITY.get(args.code, [])
        related = [f for f in futures if f["name"] in kws]

    status = "ok" if futures else "degraded"
    signals: List[str] = []
    if futures:
        # 涨跌幅最大的前 3
        top = sorted([f for f in futures if f.get("change_pct") is not None],
                     key=lambda x: abs(x["change_pct"]), reverse=True)[:3]
        for t in top:
            signals.append(f"{t['name']} {t['change_pct']:+.2f}%")

    payload = {
        "metadata": {
            "scraper": "commodity_spot_scraper.py",
            "code": args.code,
            "generated_at": now,
            "data_sources": ["东财期货主力合约 (A 类公开行情)",
                             "生意社 BPI / 卓创 / SMM (B 类权威机构，需 web_fetch 转引)"],
            "compliance": "现货价格指数建议用 fallback_urls 经 web_fetch 补充并标注转引",
            "note": "期货主力价为现货高相关代理；权威现货报价请走 fallback。",
        },
        "summary": {
            "status": status,
            "future_count": len(futures),
            "up_count": len(up),
            "down_count": len(down),
            "signals": signals,
        },
        "futures": futures,
        "related_to_code": related,
        "fallback_urls": {
            "shengyishe_bpi": "http://www.100ppi.com/",
            "sci99": "https://www.sci99.com/",
            "smm": "https://www.smm.cn/",
            "em_futures": "https://quote.eastmoney.com/center/gridlist.html#futures_global",
            "web_search": (f"{args.code} 主要原材料 现货价格 毛利" if args.code
                           else "生意社 BPI 大宗商品价格指数 最新 涨跌"),
        },
    }
    out_path = Path(args.out) if args.out else \
        (fd / f"{args.code}_commodity.json" if args.code else fd / "commodity_spot.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[commodity_spot] status={status} futures={len(futures)} -> {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
