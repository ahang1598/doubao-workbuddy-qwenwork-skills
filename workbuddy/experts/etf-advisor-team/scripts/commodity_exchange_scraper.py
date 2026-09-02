# -*- coding: utf-8 -*-
"""
Commodity Exchange Scraper — 四大商品期货交易所官方日行情统一采集器
                            （基本面 §成本端 + 行业景气：周期股价量先行指标）

为什么需要：
  · `commodity_spot_scraper.py` 只取东财 push2 主力价（代理且沙箱常被封），缺**库存/仓单**；
  · 上期所/大商所/郑商所/广期所每日免费披露「结算价 + 成交量 + 持仓量（+库存/仓单）」，
    是有色/化工/煤炭/黑色/建材/食品/农产品/电新近全部周期行业最权威的一手量价源；
  · 结算价 = 成本端先行指标；持仓量/库存变化 = 行业景气与供需拐点信号。

数据源（全部 A 类一手·政府/交易所公开，无需认证）：
  1. 上期所 SHFE  https://www.shfe.com.cn/data/dailydata/kx/kx{YYYYMMDD}.dat   （JSON 日行情）
                 https://www.shfe.com.cn/data/dailydata/{YYYYMMDD}weeklystock.dat（库存周报）
  2. 郑商所 CZCE  http://www.czce.com.cn/cn/DFSStaticFiles/Future/{Y}/{YYYYMMDD}/FutureDataDaily.txt
  3. 大商所 DCE   http://www.dce.com.cn/publicweb/quotesdata/dayQuotesCh.html （表单 POST）
  4. 广期所 GFEX  http://www.gfex.com.cn/u/interfacesWebTiDayQuotes/loadList   （JSON POST）

设计原则（严格遵守信源诚信铁律 + 优雅降级）：
  - 仅取交易所官方页，永不爬 SMM/Mysteel/百川/卓创/隆众/Wind 等 D 类付费墙；
  - 非交易日/未收盘/接口被封 → 自动回溯最近交易日、降级为 status=degraded + fallback_urls，
    绝不崩溃、绝不编造数字。

输出：FinancialData/commodity_exchange.json

用法：
  python commodity_exchange_scraper.py                       # 四大交易所全量
  python commodity_exchange_scraper.py --exchange shfe       # 仅上期所
  python commodity_exchange_scraper.py --date 20260529       # 指定交易日
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import requests
except ImportError:
    print("ERROR: requests is required. Install with: pip install requests", file=sys.stderr)
    sys.exit(1)

TIMEOUT = 25
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, text/html, */*",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

# 品种 -> 所属行业（用于个股/行业关联与景气信号归类）
VARIETY_INDUSTRY = {
    # 有色
    "铜": "有色金属", "铝": "有色金属", "锌": "有色金属", "铅": "有色金属",
    "镍": "有色金属", "锡": "有色金属", "氧化铝": "有色金属", "不锈钢": "有色金属",
    # 贵金属
    "黄金": "贵金属", "白银": "贵金属",
    # 黑色 / 建材
    "螺纹钢": "黑色/建材", "热轧卷板": "黑色/建材", "线材": "黑色/建材",
    "铁矿石": "黑色/建材", "玻璃": "黑色/建材", "纯碱": "黑色/建材",
    # 煤炭 / 能化
    "焦煤": "煤炭", "焦炭": "煤炭", "动力煤": "煤炭",
    "原油": "能源化工", "燃料油": "能源化工", "沥青": "能源化工", "液化石油气": "能源化工",
    "甲醇": "能源化工", "乙二醇": "能源化工", "苯乙烯": "能源化工", "PTA": "能源化工",
    "短纤": "能源化工", "PVC": "能源化工", "聚乙烯": "能源化工", "聚丙烯": "能源化工",
    "尿素": "能源化工", "烧碱": "能源化工", "纯苯": "能源化工", "对二甲苯": "能源化工",
    "丁二烯橡胶": "能源化工", "天然橡胶": "能源化工",
    # 新能源
    "工业硅": "电新/新能源", "碳酸锂": "电新/新能源", "多晶硅": "电新/新能源",
    # 农产品 / 食品
    "豆粕": "农产品/食品", "豆油": "农产品/食品", "豆一": "农产品/食品", "豆二": "农产品/食品",
    "玉米": "农产品/食品", "玉米淀粉": "农产品/食品", "棕榈油": "农产品/食品",
    "鸡蛋": "农产品/食品", "生猪": "农产品/食品", "白糖": "农产品/食品",
    "棉花": "农产品/食品", "棉纱": "农产品/食品", "菜籽油": "农产品/食品",
    "菜籽粕": "农产品/食品", "苹果": "农产品/食品", "红枣": "农产品/食品",
    "花生": "农产品/食品", "粳米": "农产品/食品", "白小麦": "农产品/食品",
}

# 郑商所合约只给字母代码（如 UR/FG），此处映射为中文名 + 行业，便于信号可读
CZCE_CODE_INFO = {
    "WH": ("强麦", "农产品/食品"), "PM": ("普麦", "农产品/食品"),
    "CF": ("棉花", "农产品/纺织"), "CY": ("棉纱", "农产品/纺织"),
    "SR": ("白糖", "农产品/食品"), "OI": ("菜籽油", "农产品/食品"),
    "RI": ("早籼稻", "农产品/食品"), "RM": ("菜籽粕", "农产品/食品"),
    "RS": ("油菜籽", "农产品/食品"), "JR": ("粳稻", "农产品/食品"),
    "LR": ("晚籼稻", "农产品/食品"), "AP": ("苹果", "农产品/食品"),
    "CJ": ("红枣", "农产品/食品"), "PK": ("花生", "农产品/食品"),
    "MA": ("甲醇", "能源化工"), "TA": ("PTA", "能源化工"),
    "PF": ("短纤", "能源化工"), "PX": ("对二甲苯", "能源化工"),
    "PR": ("瓶片", "能源化工"), "UR": ("尿素", "能源化工"),
    "SH": ("烧碱", "能源化工"), "SA": ("纯碱", "黑色/建材"),
    "FG": ("玻璃", "黑色/建材"), "SF": ("硅铁", "黑色/建材"),
    "SM": ("锰硅", "黑色/建材"), "ZC": ("动力煤", "煤炭"),
}


def _safe_float(v: Any) -> Optional[float]:
    if v in (None, "", "-", "—"):
        return None
    try:
        return float(str(v).replace(",", "").strip())
    except Exception:
        return None


def _clean(s: Any) -> str:
    return re.sub(r"\s+", "", str(s or ""))


def _recent_trade_days(anchor: Optional[str], lookback: int = 8) -> List[str]:
    """从 anchor(YYYYMMDD)或今天起向前回溯，跳过周末，给出候选交易日列表。"""
    if anchor:
        try:
            d = datetime.strptime(anchor, "%Y%m%d")
        except Exception:
            d = datetime.now()
    else:
        d = datetime.now()
    days: List[str] = []
    cur = d
    while len(days) < lookback:
        if cur.weekday() < 5:  # 0-4 周一到周五
            days.append(cur.strftime("%Y%m%d"))
        cur -= timedelta(days=1)
    return days


# ============================================================
# 上期所 SHFE — JSON 日行情 + 库存周报
# ============================================================

def fetch_shfe(date_candidates: List[str]) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "exchange": "SHFE", "name": "上海期货交易所",
        "compliance": "A 类一手（交易所官方公开 .dat）",
        "official_url": "https://www.shfe.com.cn/statements/dataview.html",
        "contracts": [], "inventory": [],
    }
    for day in date_candidates:
        url = f"https://www.shfe.com.cn/data/dailydata/kx/kx{day}.dat"
        try:
            r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            if r.status_code != 200 or not r.text.strip():
                continue
            js = r.json()
        except Exception as e:
            out.setdefault("errors", []).append(f"daily {day}: {e}")
            continue
        rows = (js or {}).get("o_curinstrument") or []
        if not rows:
            continue
        out["trade_date"] = day
        for row in rows:
            prod = _clean(row.get("PRODUCTNAME"))
            month = _clean(row.get("DELIVERYMONTH"))
            if not prod or month in ("小计", "总计", "") or "总计" in month or "小计" in month:
                continue
            settle = _safe_float(row.get("SETTLEMENTPRICE"))
            if settle is None:
                continue
            out["contracts"].append({
                "variety": prod,
                "industry": VARIETY_INDUSTRY.get(prod, ""),
                "contract": f"{prod}{month}",
                "settle": settle,
                "close": _safe_float(row.get("CLOSEPRICE")),
                "pre_settle": _safe_float(row.get("PRESETTLEMENTPRICE")),
                "change": _safe_float(row.get("ZD2_CHG")),
                "volume": _safe_float(row.get("VOLUME")),
                "open_interest": _safe_float(row.get("OPENINTEREST")),
            })
        break
    # 库存周报（best-effort）
    for day in date_candidates:
        url = f"https://www.shfe.com.cn/data/dailydata/{day}weeklystock.dat"
        try:
            r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            if r.status_code != 200 or not r.text.strip():
                continue
            js = r.json()
        except Exception:
            continue
        rows = (js or {}).get("o_cursor") or []
        if not rows:
            continue
        out["inventory_date"] = day
        for row in rows:
            var = _clean(row.get("VARNAME"))
            wgt = _safe_float(row.get("WRTWGHTS"))
            if not var or wgt is None:
                continue
            out["inventory"].append({
                "variety": var,
                "warehouse": _clean(row.get("WHABBRNAME")),
                "stock": wgt,
                "change": _safe_float(row.get("WRTCHANGE")),
            })
        break
    if not out["contracts"]:
        out["fallback_hint"] = "用 web_fetch https://www.shfe.com.cn/statements/dataview.html 获取最新日行情"
    return out


# ============================================================
# 郑商所 CZCE — FutureDataDaily.txt（竖线分隔）
# ============================================================

def fetch_czce(date_candidates: List[str]) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "exchange": "CZCE", "name": "郑州商品交易所",
        "compliance": "A 类一手（交易所官方静态文件 .txt）",
        "official_url": "http://www.czce.com.cn/cn/jysj/mrhq/H770301index_1.htm",
        "contracts": [],
    }
    for day in date_candidates:
        year = day[:4]
        url = (f"http://www.czce.com.cn/cn/DFSStaticFiles/Future/{year}/{day}/"
               f"FutureDataDaily.txt")
        try:
            r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            if r.status_code != 200 or not r.text.strip():
                continue
            r.encoding = r.apparent_encoding or "utf-8"
            text = r.text
        except Exception as e:
            out.setdefault("errors", []).append(f"{day}: {e}")
            continue
        lines = [ln for ln in text.splitlines() if ln.count("|") >= 10]
        parsed = 0
        for ln in lines:
            cols = [c.strip() for c in ln.split("|")]
            contract = cols[0]
            # 跳过表头/合计行
            if not re.match(r"^[A-Za-z]{1,3}\d{3}$", contract):
                continue
            settle = _safe_float(cols[6]) if len(cols) > 6 else None
            if settle is None:
                continue
            var = re.match(r"^[A-Za-z]+", contract).group(0)
            cn, ind = CZCE_CODE_INFO.get(var.upper(), ("", ""))
            out["contracts"].append({
                "contract": contract,
                "variety_code": var,
                "variety": cn or var,
                "industry": ind,
                "pre_settle": _safe_float(cols[1]),
                "close": _safe_float(cols[5]) if len(cols) > 5 else None,
                "settle": settle,
                "change": _safe_float(cols[7]) if len(cols) > 7 else None,
                "volume": _safe_float(cols[9]) if len(cols) > 9 else None,
                "open_interest": _safe_float(cols[10]) if len(cols) > 10 else None,
                "oi_change": _safe_float(cols[11]) if len(cols) > 11 else None,
            })
            parsed += 1
        if parsed:
            out["trade_date"] = day
            break
    if not out["contracts"]:
        out["fallback_hint"] = ("用 web_fetch http://www.czce.com.cn/cn/jysj/mrhq/H770301index_1.htm "
                                "获取动力煤/玻璃/纯碱/白糖/棉花/苹果最新结算价")
    return out


# ============================================================
# 大商所 DCE — 表单 POST（HTML，反爬较严，best-effort）
# ============================================================

def fetch_dce(date_candidates: List[str]) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "exchange": "DCE", "name": "大连商品交易所",
        "compliance": "A 类一手（交易所官方页，表单 POST）",
        "official_url": "http://www.dce.com.cn/publicweb/quotesdata/dayQuotesCh.html",
        "contracts": [],
    }
    url = "http://www.dce.com.cn/publicweb/quotesdata/dayQuotesCh.html"
    dce_headers = dict(HEADERS)
    dce_headers["Referer"] = url
    dce_headers["Origin"] = "http://www.dce.com.cn"
    dce_headers["Content-Type"] = "application/x-www-form-urlencoded"
    for day in date_candidates:
        y, m, d = int(day[:4]), int(day[4:6]), int(day[6:8])
        data = {
            "dayQuotes.variety": "all",
            "dayQuotes.trade_type": "0",
            "year": str(y), "month": str(m - 1), "day": str(d),  # DCE month 0-based
        }
        try:
            r = requests.post(url, data=data, headers=dce_headers, timeout=TIMEOUT)
            if r.status_code != 200:
                continue
            r.encoding = r.apparent_encoding or "utf-8"
            html = r.text
        except Exception as e:
            out.setdefault("errors", []).append(f"{day}: {e}")
            continue
        # 解析 HTML 表格行
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S)
        parsed = 0
        for row in rows:
            cells = [re.sub(r"<[^>]+>", "", c).strip()
                     for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)]
            if len(cells) < 11:
                continue
            var = _clean(cells[0])
            month = _clean(cells[1])
            if not var or not re.match(r"^\d{3,4}$", month) or var in ("品种", "总计", "小计"):
                continue
            settle = _safe_float(cells[6])
            if settle is None:
                continue
            out["contracts"].append({
                "variety": var,
                "industry": VARIETY_INDUSTRY.get(var, ""),
                "contract": f"{var}{month}",
                "pre_settle": _safe_float(cells[2]),
                "close": _safe_float(cells[5]),
                "settle": settle,
                "change": _safe_float(cells[8]) if len(cells) > 8 else None,
                "volume": _safe_float(cells[10]) if len(cells) > 10 else None,
                "open_interest": _safe_float(cells[11]) if len(cells) > 11 else None,
            })
            parsed += 1
        if parsed:
            out["trade_date"] = day
            break
    if not out["contracts"]:
        out["fallback_hint"] = ("用 web_fetch http://www.dce.com.cn/publicweb/quotesdata/dayQuotesCh.html "
                                "获取焦煤/焦炭/铁矿石/玉米/豆粕/豆油最新结算价与持仓")
    return out


# ============================================================
# 广期所 GFEX — JSON POST（工业硅 / 碳酸锂 / 多晶硅）
# ============================================================

def fetch_gfex(date_candidates: List[str]) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "exchange": "GFEX", "name": "广州期货交易所",
        "compliance": "A 类一手（交易所官方接口 JSON POST）",
        "official_url": "http://www.gfex.com.cn/gfex/rihq/hqsj_tjsj.shtml",
        "contracts": [],
    }
    url = "http://www.gfex.com.cn/u/interfacesWebTiDayQuotes/loadList"
    for day in date_candidates:
        try:
            r = requests.post(url, data={"trade_date": day, "trade_type": "0"},
                              headers=HEADERS, timeout=TIMEOUT)
            if r.status_code != 200 or not r.text.strip():
                continue
            js = r.json()
        except Exception as e:
            out.setdefault("errors", []).append(f"{day}: {e}")
            continue
        rows = js.get("data") if isinstance(js, dict) else None
        if not rows:
            continue
        parsed = 0
        for row in rows:
            var = _clean(row.get("variety") or row.get("varietyOrder"))
            month = _clean(row.get("delivMonth") or row.get("deliveryMonth"))
            settle = _safe_float(row.get("clearPrice") or row.get("settlePrice"))
            if not var or settle is None:
                continue
            out["contracts"].append({
                "variety": var,
                "industry": VARIETY_INDUSTRY.get(var, "电新/新能源"),
                "contract": f"{var}{month}",
                "settle": settle,
                "close": _safe_float(row.get("close")),
                "pre_settle": _safe_float(row.get("preClearPrice") or row.get("preSettlePrice")),
                "change": _safe_float(row.get("zd")),
                "volume": _safe_float(row.get("volume")),
                "open_interest": _safe_float(row.get("openInterest") or row.get("openinterest")),
            })
            parsed += 1
        if parsed:
            out["trade_date"] = day
            break
    if not out["contracts"]:
        out["fallback_hint"] = ("用 web_fetch http://www.gfex.com.cn/gfex/rihq/hqsj_tjsj.shtml "
                                "获取工业硅/碳酸锂/多晶硅最新结算价")
    return out


EXCHANGES = {
    "shfe": fetch_shfe,
    "czce": fetch_czce,
    "dce": fetch_dce,
    "gfex": fetch_gfex,
}


def _build_signals(results: Dict[str, Any]) -> List[str]:
    """跨交易所主力合约（同品种取持仓量最大者）涨跌幅 TOP 信号。"""
    main_by_var: Dict[str, Dict[str, Any]] = {}
    for ex in results.values():
        for c in ex.get("contracts", []):
            var = c.get("variety") or c.get("variety_code")
            if not var or c.get("settle") in (None, 0):
                continue
            oi = c.get("open_interest") or 0
            if var not in main_by_var or oi > (main_by_var[var].get("open_interest") or 0):
                pre = c.get("pre_settle")
                pct = ((c["settle"] - pre) / pre * 100) if pre else None
                rec = dict(c)
                rec["change_pct"] = pct
                main_by_var[var] = rec
    ranked = sorted([v for v in main_by_var.values() if v.get("change_pct") is not None],
                    key=lambda x: abs(x["change_pct"]), reverse=True)[:8]
    return [f"{r.get('variety') or r.get('variety_code')}({r.get('industry','')}) "
            f"{r['change_pct']:+.2f}%" for r in ranked]


def main() -> int:
    ap = argparse.ArgumentParser(description="四大商品期货交易所官方日行情采集")
    ap.add_argument("--exchange", choices=list(EXCHANGES.keys()) + ["all"], default="all")
    ap.add_argument("--date", help="指定交易日 YYYYMMDD（默认自动回溯最近交易日）")
    ap.add_argument("--out")
    args = ap.parse_args()

    now = datetime.now().isoformat(timespec="seconds")
    fd = Path(__file__).resolve().parents[3] / "FinancialData"
    cands = _recent_trade_days(args.date)

    targets = EXCHANGES if args.exchange == "all" else {args.exchange: EXCHANGES[args.exchange]}
    results: Dict[str, Any] = {}
    for key, fn in targets.items():
        print(f"[commodity_exchange] 抓取 {key.upper()}...", file=sys.stderr)
        try:
            results[key] = fn(cands)
        except Exception as e:
            results[key] = {"exchange": key.upper(), "error": str(e), "contracts": []}

    total = sum(len(v.get("contracts", [])) for v in results.values())
    status = "ok" if total else "degraded"
    signals = _build_signals(results) if total else []

    payload = {
        "metadata": {
            "scraper": "commodity_exchange_scraper.py",
            "generated_at": now,
            "date_candidates": cands,
            "data_sources": [
                "上期所 SHFE / 郑商所 CZCE / 大商所 DCE / 广期所 GFEX 官方日行情（A 类一手）",
            ],
            "compliance": "全部交易所官方公开接口；禁用 SMM/Mysteel/百川/卓创/隆众/Wind 等付费墙。",
            "note": "结算价=成本端先行指标；持仓量/库存变化=供需景气拐点信号。非交易日自动回溯。",
        },
        "summary": {
            "status": status,
            "contract_count": total,
            "by_exchange": {k: len(v.get("contracts", [])) for k, v in results.items()},
            "signals": signals,
        },
        "exchanges": results,
        "fallback_urls": {
            "shfe": "https://www.shfe.com.cn/statements/dataview.html",
            "czce": "http://www.czce.com.cn/cn/jysj/mrhq/H770301index_1.htm",
            "dce": "http://www.dce.com.cn/publicweb/quotesdata/dayQuotesCh.html",
            "gfex": "http://www.gfex.com.cn/gfex/rihq/hqsj_tjsj.shtml",
            "web_search": "上期所 大商所 郑商所 广期所 今日结算价 持仓 库存",
        },
    }
    out_path = Path(args.out) if args.out else fd / "commodity_exchange.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[commodity_exchange] status={status} contracts={total} -> {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
