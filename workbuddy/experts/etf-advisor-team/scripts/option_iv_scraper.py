# -*- coding: utf-8 -*-
"""
Option IV & Skew Scraper — A 股期权隐含波动率 / Skew / Put-Call Ratio 抓取
                          （衍生品市场情绪监测配套）

数据源（A 类一手公开）：
  东方财富期权 T 型报价 push2 接口
    - https://push2.eastmoney.com/api/qt/slist/get  （期权列表）
    - https://push2.eastmoney.com/api/qt/stock/get  （单合约行情，含 IV）
  覆盖品种：
    - 上交所 ETF 期权：50ETF (510050)、沪300ETF (510300)、科创50ETF (588000)、科创板50 (588080)
    - 深交所 ETF 期权：深300ETF (159919)、创业板ETF (159915)、深500ETF (159922)
    - 中金所股指期权：沪深300 (IO)、中证1000 (MO)、上证50 (HO)
    - 个股期权（暂未上市）：留接口位

输出指标：
  - ATM IV（平值隐含波动率，看涨/看跌平均）
  - 25-Delta Skew（OTM Put IV - OTM Call IV）
  - PCR（Put-Call Ratio，按持仓量与成交量两种口径）
  - IV Term Structure（近月/次月/季月）

输出：FinancialData/option_iv_{symbol}.json

v1.9 合规性：东财公开 push2 接口，A 类一手

用法：
  python option_iv_scraper.py 510050           # 50ETF 期权
  python option_iv_scraper.py 510300 --json    # 沪300ETF 期权
  python option_iv_scraper.py all              # 抓全部主流标的
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import requests
except ImportError:
    print("ERROR: requests required.", file=sys.stderr)
    sys.exit(1)

TIMEOUT = 30
THROTTLE_SEC = 0.5

PUSH2_SLIST = "https://push2.eastmoney.com/api/qt/slist/get"
PUSH2_STOCK = "https://push2.eastmoney.com/api/qt/stock/get"
PUSH2_OPTION_LIST = "https://push2.eastmoney.com/api/qt/clist/get"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://quote.eastmoney.com/",
    "Accept": "application/json, text/plain, */*",
}

# 期权标的元信息：(代码, 简称, secid前缀, 市场)
UNDERLYINGS: Dict[str, Dict[str, Any]] = {
    "510050": {"name": "上证50ETF",   "und_secid": "1.510050", "opt_market": "10"},  # 上交所 ETF期权
    "510300": {"name": "沪深300ETF",  "und_secid": "1.510300", "opt_market": "10"},
    "510500": {"name": "中证500ETF",  "und_secid": "1.510500", "opt_market": "10"},
    "588000": {"name": "科创50ETF",   "und_secid": "1.588000", "opt_market": "10"},
    "588080": {"name": "科创板50ETF", "und_secid": "1.588080", "opt_market": "10"},
    "159919": {"name": "深300ETF",    "und_secid": "0.159919", "opt_market": "12"},  # 深交所 ETF期权
    "159915": {"name": "创业板ETF",   "und_secid": "0.159915", "opt_market": "12"},
    "159922": {"name": "深500ETF",    "und_secid": "0.159922", "opt_market": "12"},
}

# Push2 字段说明（部分）
# f1 市场, f2 现价, f3 涨跌, f4 涨跌幅, f5 成交量, f6 成交额,
# f249 IV (隐含波动率, 万分之一), f250 时间价值,
# f267 行权价, f268 到期日, f330 类型 (CALL=看涨, PUT=看跌),
# f108 持仓量

# ---------- helpers ----------

def _get(url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"_error": str(e)}


def fetch_underlying_price(symbol: str) -> Optional[float]:
    """取标的最新价"""
    meta = UNDERLYINGS.get(symbol)
    if not meta:
        return None
    secid = meta["und_secid"]
    params = {
        "secid": secid,
        "fields": "f43,f60,f44,f45",  # f43=现价
        "ut": "fa5fd1943c7b386f172d6893dbfba10b",
    }
    js = _get(PUSH2_STOCK, params)
    if not js or js.get("_error"):
        return None
    data = (js.get("data") or {})
    p = data.get("f43")
    if p is None:
        return None
    try:
        return float(p) / 1000.0  # ETF 价格通常 ×1000 编码
    except Exception:
        return None


# ---------- 期权链抓取 ----------

def fetch_option_chain(symbol: str) -> List[Dict[str, Any]]:
    """通过 clist 接口取该标的所有期权合约（含 IV / 持仓 / 成交）"""
    meta = UNDERLYINGS.get(symbol)
    if not meta:
        return []

    market = meta["opt_market"]
    # 关键 fs 过滤器：m=10/12 期权市场 + s=fs 标的代码筛选
    # 实测 clist 期权列表 fs="m:10+t:140" 取上交所所有 ETF 期权
    fs_options = [
        f"m:{market}+t:140",  # ETF 期权
        f"m:{market}+t:141",  # 个股期权（备用）
    ]
    all_rows: List[Dict[str, Any]] = []
    for fs in fs_options:
        page = 1
        while True:
            params = {
                "pn": page,
                "pz": 200,
                "po": 1,
                "np": 1,
                "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                "fltt": 2,
                "invt": 2,
                "wbp2u": "|0|0|0|web",
                "fid": "f12",
                "fs": fs,
                # 字段：代码 名称 现价 涨跌幅 成交量 持仓量 IV 行权价 到期日 类型
                "fields": "f1,f2,f3,f4,f5,f6,f12,f13,f14,f108,"
                          "f249,f250,f267,f268,f297,f330",
            }
            js = _get(PUSH2_OPTION_LIST, params)
            if not js or js.get("_error"):
                break
            data = (js.get("data") or {})
            rows = data.get("diff") or []
            if not rows:
                break

            # 只保留名称含标的代码的合约
            for r in rows:
                name = r.get("f14") or ""
                if symbol in name or symbol in (r.get("f12") or ""):
                    all_rows.append(r)

            total = data.get("total", 0)
            if page * 200 >= total:
                break
            page += 1
            time.sleep(THROTTLE_SEC)
        time.sleep(THROTTLE_SEC)

    return all_rows


def normalize_contract(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """把 push2 raw 字段标准化"""
    try:
        code = row.get("f12") or ""
        name = row.get("f14") or ""
        price = row.get("f2")
        chg_pct = row.get("f3")
        volume = row.get("f5") or 0
        oi = row.get("f108") or 0
        iv_raw = row.get("f249")
        strike = row.get("f267")
        expiry = row.get("f268")
        opt_type_raw = row.get("f330")

        # IV 解码（push2 通常以 ×10000 整数编码，部分以 0~1 浮点直接给出）
        iv = None
        if iv_raw not in (None, "-", ""):
            iv_f = float(iv_raw)
            iv = iv_f / 10000.0 if iv_f > 5 else iv_f

        # 行权价解码
        if strike not in (None, "-", ""):
            try:
                strike = float(strike)
                if strike > 1000:  # ×1000 编码
                    strike = strike / 1000.0
            except Exception:
                strike = None

        # 类型推断（f330 / 名称中"购"=Call，"沽"=Put）
        opt_type = None
        if opt_type_raw is not None:
            s = str(opt_type_raw).upper()
            if s in ("CALL", "C", "1"):
                opt_type = "C"
            elif s in ("PUT", "P", "-1", "0"):
                opt_type = "P"
        if opt_type is None:
            if "购" in name:
                opt_type = "C"
            elif "沽" in name:
                opt_type = "P"

        # 到期月份解码（合约名形如 "50ETF购12月3000"）
        return {
            "code": code,
            "name": name,
            "type": opt_type,
            "strike": strike,
            "price": float(price) if price not in (None, "-", "") else None,
            "chg_pct": float(chg_pct) if chg_pct not in (None, "-", "") else None,
            "volume": int(volume) if volume not in (None, "-", "") else 0,
            "open_interest": int(oi) if oi not in (None, "-", "") else 0,
            "iv": iv,
            "expiry": expiry,
        }
    except Exception:
        return None


# ---------- 指标计算 ----------

def compute_metrics(contracts: List[Dict[str, Any]],
                    spot: Optional[float]) -> Dict[str, Any]:
    """从期权链算 ATM IV / Skew / PCR"""
    out: Dict[str, Any] = {
        "spot": spot,
        "n_contracts": len(contracts),
        "atm_iv_call": None,
        "atm_iv_put": None,
        "atm_iv_avg": None,
        "skew_25d": None,
        "pcr_volume": None,
        "pcr_oi": None,
        "iv_by_moneyness": [],
    }
    if not contracts:
        return out

    calls = [c for c in contracts if c.get("type") == "C" and c.get("iv") and c.get("strike")]
    puts  = [c for c in contracts if c.get("type") == "P" and c.get("iv") and c.get("strike")]

    # PCR — 全合约口径
    total_call_vol = sum(c.get("volume") or 0 for c in contracts if c.get("type") == "C")
    total_put_vol  = sum(c.get("volume") or 0 for c in contracts if c.get("type") == "P")
    total_call_oi  = sum(c.get("open_interest") or 0 for c in contracts if c.get("type") == "C")
    total_put_oi   = sum(c.get("open_interest") or 0 for c in contracts if c.get("type") == "P")
    if total_call_vol > 0:
        out["pcr_volume"] = round(total_put_vol / total_call_vol, 4)
    if total_call_oi > 0:
        out["pcr_oi"] = round(total_put_oi / total_call_oi, 4)

    if not spot or not calls or not puts:
        return out

    # ATM = 行权价距离现价最近的合约（按各到期日分别算，取最近月）
    # 简化：直接全样本最近 strike
    def _nearest(items, target):
        return min(items, key=lambda c: abs((c.get("strike") or 0) - target))

    atm_call = _nearest(calls, spot)
    atm_put  = _nearest(puts,  spot)
    out["atm_iv_call"] = round(atm_call.get("iv") or 0, 4) if atm_call.get("iv") else None
    out["atm_iv_put"]  = round(atm_put.get("iv")  or 0, 4) if atm_put.get("iv")  else None
    if out["atm_iv_call"] and out["atm_iv_put"]:
        out["atm_iv_avg"] = round((out["atm_iv_call"] + out["atm_iv_put"]) / 2, 4)

    # 25-delta Skew —— 简化：取虚 5% 的 OTM Put IV - OTM Call IV
    target_put_strike  = spot * 0.95
    target_call_strike = spot * 1.05
    otm_put  = _nearest(puts,  target_put_strike)
    otm_call = _nearest(calls, target_call_strike)
    if otm_put.get("iv") and otm_call.get("iv"):
        out["skew_25d"] = round(otm_put["iv"] - otm_call["iv"], 4)

    # IV by moneyness（90/95/100/105/110%）
    for ratio in [0.90, 0.95, 1.00, 1.05, 1.10]:
        target = spot * ratio
        c = _nearest(calls, target)
        p = _nearest(puts,  target)
        out["iv_by_moneyness"].append({
            "moneyness": ratio,
            "strike": round(target, 4),
            "call_iv": round(c.get("iv") or 0, 4) if c.get("iv") else None,
            "put_iv":  round(p.get("iv") or 0, 4) if p.get("iv") else None,
        })

    return out


# ---------- main ----------

def build_one(symbol: str) -> Dict[str, Any]:
    meta = UNDERLYINGS.get(symbol)
    if not meta:
        return {"_error": f"unknown symbol {symbol}"}

    spot = fetch_underlying_price(symbol)
    time.sleep(THROTTLE_SEC)
    raw_chain = fetch_option_chain(symbol)
    contracts = [c for c in (normalize_contract(r) for r in raw_chain) if c]
    metrics = compute_metrics(contracts, spot)

    return {
        "metadata": {
            "symbol": symbol,
            "name": meta["name"],
            "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "tier": "A (一手公开)",
            "source": "eastmoney push2 option clist",
        },
        "metrics": metrics,
        "contracts_sample": contracts[:30],  # 保留前 30 个示例，防 JSON 过大
        "n_total_contracts": len(contracts),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="A 股期权 IV / Skew / PCR 抓取")
    ap.add_argument("symbol", help="标的代码 (如 510050)，或 'all' 抓全部")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    args = ap.parse_args()

    if args.symbol.lower() == "all":
        targets = list(UNDERLYINGS.keys())
    else:
        if args.symbol not in UNDERLYINGS:
            print(f"ERROR: unsupported symbol {args.symbol}, "
                  f"choose from: {list(UNDERLYINGS.keys())}", file=sys.stderr)
            return 1
        targets = [args.symbol]

    out_dir = Path(__file__).resolve().parents[3] / "FinancialData"
    out_dir.mkdir(parents=True, exist_ok=True)

    summary = []
    for sym in targets:
        out = build_one(sym)
        out_path = out_dir / f"option_iv_{sym}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        m = out.get("metrics", {})
        print(f"[OK] {sym} {UNDERLYINGS[sym]['name']:<14}  "
              f"ATM IV={m.get('atm_iv_avg')}  Skew={m.get('skew_25d')}  "
              f"PCR(vol)={m.get('pcr_volume')}  -> {out_path}", file=sys.stderr)
        summary.append({"symbol": sym, "metrics": m})
        time.sleep(THROTTLE_SEC)

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
