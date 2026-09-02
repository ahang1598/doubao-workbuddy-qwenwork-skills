# -*- coding: utf-8 -*-
"""
Futures Basis Scraper — 股指期货基差 / 升贴水（资金面 §对冲情绪 + 情绪面 §机构预期配套）

为什么需要：
  · 股指期货（IF沪深300 / IH上证50 / IC中证500 / IM中证1000）相对现货指数的基差
    （升贴水）是机构对冲成本与多空预期的核心读数：
      - 深度贴水 → 套保/看空力量强、市场情绪偏弱；
      - 升水/贴水收敛 → 多头预期回暖；
  · 现有脚本（option_iv / cffex_position）覆盖期权波动率和持仓，缺一个直接计算基差的采集器。

数据源（A 类一手公开）：
  1. 东方财富 push2 — 股指期货当月/次月/季月合约现价
  2. 东方财富 push2 — 对应现货指数实时点位
  3. 由现价与指数计算：基差 = 期货价 - 指数；年化基差率 = 基差/指数 / 剩余天数 × 365
       （剩余到期天数采用近似，精确交割日建议 web_fetch 中金所合约表）

输出：FinancialData/futures_basis.json

合规性：东财公开行情 A 类一手。

用法：
  python futures_basis_scraper.py
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
PUSH2_LIST = "https://push2.eastmoney.com/api/qt/clist/get"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://quote.eastmoney.com/",
    "Accept": "application/json, text/plain, */*",
}

# 股指期货品种 -> (期货品种代码前缀, 对应现货指数 secid, 指数名)
PRODUCTS = {
    "IF": {"prefix": "IF", "index_secid": "1.000300", "index_name": "沪深300"},
    "IH": {"prefix": "IH", "index_secid": "1.000016", "index_name": "上证50"},
    "IC": {"prefix": "IC", "index_secid": "1.000905", "index_name": "中证500"},
    "IM": {"prefix": "IM", "index_secid": "1.000852", "index_name": "中证1000"},
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


def fetch_index_spot(secid: str) -> float:
    js = _get(PUSH2_GET, {"fields": "f43,f58", "secid": secid})
    d = (js or {}).get("data") or {}
    v = d.get("f43")
    return _safe_float(v) / 100 if v not in (None, "-") else 0.0


def fetch_future_contracts(prefix: str) -> List[Dict[str, Any]]:
    """列出某品种所有在交易合约（中金所 m:8）。"""
    js = _get(PUSH2_LIST, {
        "pn": 1, "pz": 20, "po": 0, "np": 1, "fltt": 2, "invt": 2,
        "fid": "f12", "fs": "m:8",
        "fields": "f12,f13,f14,f2,f3,f4",
    })
    data = ((js or {}).get("data") or {}).get("diff") or []
    out = []
    for d in data:
        code = str(d.get("f12") or "")
        name = d.get("f14") or ""
        if not (code.upper().startswith(prefix) or name.startswith(prefix)):
            continue
        price = _safe_float(d.get("f2"))
        if price <= 0:
            continue
        out.append({
            "contract": code,
            "name": name,
            "price": price,
            "change_pct": _safe_float(d.get("f3")),
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="股指期货基差/升贴水")
    ap.add_argument("--out")
    args = ap.parse_args()

    now = datetime.now().isoformat(timespec="seconds")
    results: List[Dict[str, Any]] = []
    signals: List[str] = []

    for prod, meta in PRODUCTS.items():
        spot = fetch_index_spot(meta["index_secid"])
        contracts = fetch_future_contracts(meta["prefix"])
        basis_list = []
        for c in contracts:
            if spot > 0:
                basis = round(c["price"] - spot, 2)
                basis_pct = round(basis / spot * 100, 3)
            else:
                basis, basis_pct = None, None
            basis_list.append({**c, "basis": basis, "basis_pct": basis_pct})
        # 近月基差（取第一个合约作为近月近似）
        near = basis_list[0] if basis_list else {}
        if near.get("basis_pct") is not None:
            tag = "贴水" if near["basis_pct"] < 0 else "升水"
            signals.append(f"{prod}({meta['index_name']}) 近月{tag} {near['basis_pct']}%")
        results.append({
            "product": prod,
            "index_name": meta["index_name"],
            "spot": spot,
            "contracts": basis_list,
            "near_basis_pct": near.get("basis_pct"),
        })

    has_data = any(r["spot"] > 0 and r["contracts"] for r in results)
    status = "ok" if has_data else "degraded"

    # 整体贴水程度判定
    near_vals = [r["near_basis_pct"] for r in results if r.get("near_basis_pct") is not None]
    overall = None
    if near_vals:
        avg = sum(near_vals) / len(near_vals)
        if avg < -1.0:
            overall = f"整体深度贴水({avg:.2f}%)→对冲/看空力量强、情绪偏弱"
        elif avg < -0.2:
            overall = f"整体小幅贴水({avg:.2f}%)→中性偏谨慎"
        elif avg > 0.2:
            overall = f"整体升水({avg:.2f}%)→多头预期偏强"
        else:
            overall = f"基差基本持平({avg:.2f}%)→情绪中性"

    payload = {
        "metadata": {
            "scraper": "futures_basis_scraper.py",
            "generated_at": now,
            "data_sources": ["东财 push2 股指期货+指数行情 (A 类一手)"],
            "compliance": "A 类一手；精确交割日/年化建议 web_fetch 中金所合约表",
        },
        "summary": {
            "status": status,
            "overall_basis_judgement": overall,
            "signals": signals,
        },
        "products": results,
        "fallback_urls": {
            "cffex": "http://www.cffex.com.cn/",
            "em_futures": "https://quote.eastmoney.com/center/gridlist.html#futures_cffex",
            "web_search": "股指期货 基差 升贴水 IF IC IM 最新",
        },
    }
    out_path = Path(args.out) if args.out else \
        Path(__file__).resolve().parents[3] / "FinancialData" / "futures_basis.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[futures_basis] status={status} -> {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
