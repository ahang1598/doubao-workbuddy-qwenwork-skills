# -*- coding: utf-8 -*-
"""
AH Premium Scraper — A+H 股溢价抓取（双重估值锚）

为什么需要：
  1. A+H 同时上市公司的 A/H 折溢价率及其历史分位, 是双重估值的重要锚:
     A 股相对 H 股溢价过高 → A 股估值偏贵; 折价 → 相对便宜。
  2. data_sources.md 已列出同花顺/东财 AH 比价源, 但无脚本——本脚本补齐。
  3. A 类一手公开源:
       - 东财 push2 clist (b:DLMK1011 = AH 比价板块)

输出：FinancialData/ah_premium.json（全市场）或 {code}_ah_premium.json（指定 A 股）
  {
    "metadata": {...},
    "summary": {"count": 78, "status": "ok",
                "target": {"a_code","name","a_price","h_price","premium_pct"}},
    "ah_list": [{a_code,h_code,name,a_price,h_price,premium_pct}]
  }

用法：
  python ah_premium_scraper.py              # 全部 A+H 比价
  python ah_premium_scraper.py --code 601318 # 查指定 A 股的 AH 溢价
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import requests
except ImportError:
    print("ERROR: requests required.", file=sys.stderr)
    sys.exit(1)

TIMEOUT = 25

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://quote.eastmoney.com/",
    "Accept": "application/json, text/plain, */*",
}

PUSH2_CLIST = "https://push2.eastmoney.com/api/qt/clist/get"


def _get(url: str, params=None) -> Any:
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"_error": str(e)}


def _f(v: Any) -> float:
    if v in (None, "", "-"):
        return 0.0
    try:
        return float(v)
    except Exception:
        return 0.0


def fetch_ah() -> List[Dict[str, Any]]:
    """全市场 A+H 比价（东财 AH 板块）。
    字段：f2=H现价 f3=H涨跌 f12=H代码 f14=名称 f191=A溢价率 f193=A代码 ..."""
    out: List[Dict[str, Any]] = []
    params = {
        "pn": 1, "pz": 300, "po": 1, "np": 1, "fltt": 2, "invt": 2,
        "fid": "f3",
        "fs": "b:DLMK1011",
        "fields": "f1,f2,f3,f12,f14,f186,f190,f191,f192,f193,f201,f202,f203",
    }
    js = _get(PUSH2_CLIST, params=params)
    try:
        diff = (js.get("data") or {}).get("diff") or []
    except Exception:
        diff = []
    for it in diff:
        out.append({
            "name": it.get("f14") or "",
            "h_code": it.get("f12") or "",
            "h_price": _f(it.get("f2")),
            "a_code": it.get("f193") or it.get("f201") or "",
            "a_price": _f(it.get("f190")) or _f(it.get("f202")),
            "premium_pct": _f(it.get("f191")),   # A 股相对 H 股溢价率(%)
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--code", default=None, help="指定 A 股代码, 如 601318")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    print(f"[ah_premium] {'code=' + args.code if args.code else 'full market'}")
    ah = fetch_ah()
    status = "ok" if ah else "degraded"

    target: Optional[Dict[str, Any]] = None
    if args.code:
        for it in ah:
            if str(it.get("a_code")) == args.code or args.code in str(it.get("a_code")):
                target = it
                break

    base = Path(__file__).resolve().parents[3] / "FinancialData"
    summary: Dict[str, Any] = {"count": len(ah), "status": status}
    if target:
        summary["target"] = target
        prem = target["premium_pct"]
        summary["verdict"] = ("A 股大幅溢价(偏贵)" if prem > 50 else
                              "A 股溢价" if prem > 10 else
                              "A/H 接近" if prem > -10 else "A 股折价(相对便宜)")

    payload = {
        "metadata": {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "data_sources": ["东财 push2 clist AH 比价板块 (A 类一手)"],
            "compliance": "A class primary source (eastmoney)",
        },
        "summary": summary,
        "ah_list": ah if not args.code else ([target] if target else []),
        "fallback_urls": {
            "em_ah": "https://quote.eastmoney.com/center/gridlist.html#ah_comparison",
            "ths_ah": "https://q.10jqka.com.cn/hk/ahcb/",
            "web_search": f'"{args.code or "AH股"}" A/H 溢价率 比价',
        },
    }
    out_path = (Path(args.out) if args.out else
                base / (f"{args.code}_ah_premium.json" if args.code else "ah_premium.json"))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ok] wrote {out_path}  count={len(ah)} status={status}")
    if target:
        print(f"  target {target['name']} 溢价={target['premium_pct']}% -> {summary.get('verdict')}")
    if status == "degraded":
        print("  [hint] 接口无返回, 请用 web_fetch 访问 fallback_urls 兜底")
    return 0


if __name__ == "__main__":
    sys.exit(main())
