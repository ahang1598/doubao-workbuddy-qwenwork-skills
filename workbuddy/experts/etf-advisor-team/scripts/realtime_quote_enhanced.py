#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
多源实时行情增强脚本 — 聚合 4 大免费数据源
===========================================
数据源（按优先级）：
  1. 东方财富 Push2  (push2.eastmoney.com)  — 主源，字段最全
  2. 腾讯财经        (qt.gtimg.cn)          — 第二源，含五档/涨跌停价
  3. 新浪财经        (hq.sinajs.cn)         — 第三源，含买卖五档
  4. 网易财经        (api.money.126.net)     — 第四源，含五档/52周高低

设计理念：
  - 多源冗余：任一源宕机不影响数据获取
  - 交叉校验：多源价格自动比对，偏差>1%时告警
  - 五档盘口：东财+腾讯+新浪+网易 四源五档数据融合
  - 大盘指数：专用批量接口，一次请求获取全部核心指数
  - 分时数据：东财 trends2 接口获取当日分钟级走势

用法：
  # 个股行情（四源聚合）
  python realtime_quote_enhanced.py 600519
  python realtime_quote_enhanced.py 600519 --depth          # 含五档盘口
  python realtime_quote_enhanced.py 600519 --tick           # 含分时数据

  # 批量个股
  python realtime_quote_enhanced.py 600519,000858,601318

  # 大盘指数快照
  python realtime_quote_enhanced.py --index

  # 全市场概览（指数+情绪+北向）
  python realtime_quote_enhanced.py --overview

  # JSON 输出
  python realtime_quote_enhanced.py 600519 --json
  python realtime_quote_enhanced.py 600519 --output quote.md
"""

import re
import sys
import json
import argparse
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

# --------------------------------------------------------------------------- #
#  常量 & Headers
# --------------------------------------------------------------------------- #

TIMEOUT = 12

HEADERS_EAST = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://quote.eastmoney.com/",
}

HEADERS_SINA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://finance.sina.com.cn/",
}

HEADERS_QQ = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://stockapp.finance.qq.com/",
}

HEADERS_163 = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://money.163.com/",
}


def _safe_float(v, default=None):
    if v is None or v == "-" or v == "" or v == "None":
        return default
    try:
        return float(v)
    except (ValueError, TypeError):
        return default


def _fmt_amount(val, unit=""):
    if val is None:
        return "—"
    if abs(val) >= 1e8:
        return f"{val / 1e8:.2f}亿{unit}"
    if abs(val) >= 1e4:
        return f"{val / 1e4:.2f}万{unit}"
    return f"{val:.2f}{unit}"


def infer_market(code: str) -> str:
    """推断股票/ETF/基金所属交易所
    上交所(sh): 60xxxx股票, 688/689科创板, 5xxxxx ETF/基金(510/511/512/513/515/516/517/518/560/561/562/563/588)
    深交所(sz): 00xxxx/002/003股票, 300/301/302创业板, 159xxx ETF/基金, 12xxxx转债
    北交所(bj): 8xxxxx/4xxxxx
    """
    if code.startswith(("600", "601", "603", "605", "688", "689")):
        return "sh"
    elif code.startswith(("000", "001", "002", "003", "300", "301", "302")):
        return "sz"
    elif code.startswith("159"):
        return "sz"  # 深交所 ETF/LOF
    elif code.startswith(("510", "511", "512", "513", "515", "516", "517", "518",
                          "560", "561", "562", "563", "588")):
        return "sh"  # 上交所 ETF/LOF
    elif code.startswith(("12",)):
        return "sz"  # 深交所转债
    elif code.startswith(("11",)):
        return "sh"  # 上交所转债
    return "bj"


def infer_secid(code: str) -> str:
    return f"1.{code}" if infer_market(code) == "sh" else f"0.{code}"


# =========================================================================== #
#  Source 1: 东方财富 Push2 — 主源（字段最全）
# =========================================================================== #

def fetch_eastmoney(code: str, depth: bool = False) -> Dict[str, Any]:
    """东方财富 Push2 个股实时行情 + 可选五档"""
    secid = infer_secid(code)
    fields = ("f43,f44,f45,f46,f47,f48,f50,f51,f52,f55,f57,f58,f60,"
              "f116,f117,f162,f167,f168,f169,f170,f171,f292")
    if depth:
        # 加入五档盘口字段
        fields += (",f19,f20,f17,f18,f31,f32,f33,f34,f35,f36,f37,f38,f39,f40")
    params = {
        "secid": secid, "fields": fields,
        "ut": "fa5fd1943c7b386f172d6893dbfba10b", "fltt": 2,
    }
    try:
        resp = requests.get("https://push2.eastmoney.com/api/qt/stock/get",
                            params=params, headers=HEADERS_EAST, timeout=TIMEOUT)
        d = resp.json().get("data", {})
        if not d:
            return {"_source": "eastmoney", "error": "无数据"}
        result = {
            "_source": "eastmoney",
            "代码": d.get("f57", code), "名称": d.get("f58", ""),
            "最新价": d.get("f43"), "涨跌额": d.get("f169"), "涨跌幅": d.get("f170"),
            "今开": d.get("f46"), "昨收": d.get("f60"),
            "最高": d.get("f44"), "最低": d.get("f45"),
            "成交量": d.get("f47"), "成交额": d.get("f48"),
            "换手率": d.get("f168"), "量比": d.get("f50"), "振幅": d.get("f171"),
            "总市值": d.get("f116"), "流通市值": d.get("f117"),
            "PE": d.get("f162"), "PB": d.get("f167"),
            "52周最高": d.get("f51"), "52周最低": d.get("f52"),
            "委比": d.get("f55"),
        }
        if depth:
            result["五档"] = {
                "买一": {"价": d.get("f19"), "量": d.get("f20")},
                "买二": {"价": d.get("f17"), "量": d.get("f18")},
                "卖一": {"价": d.get("f31"), "量": d.get("f32")},
                "卖二": {"价": d.get("f33"), "量": d.get("f34")},
                "卖三": {"价": d.get("f35"), "量": d.get("f36")},
                "卖四": {"价": d.get("f37"), "量": d.get("f38")},
                "卖五": {"价": d.get("f39"), "量": d.get("f40")},
            }
        return result
    except Exception as e:
        return {"_source": "eastmoney", "error": str(e)}


# =========================================================================== #
#  Source 2: 腾讯财经 qt.gtimg.cn — 第二源（含涨跌停价）
# =========================================================================== #

def fetch_tencent(code: str) -> Dict[str, Any]:
    """腾讯财经实时行情（~分隔，50+字段）"""
    mkt = "sh" if infer_market(code) == "sh" else "sz"
    qq_code = f"{mkt}{code}"
    try:
        resp = requests.get(f"https://qt.gtimg.cn/q={qq_code}",
                            headers=HEADERS_QQ, timeout=TIMEOUT)
        resp.encoding = "gbk"
        text = resp.text.strip()
        m = re.search(r'"(.*)"', text)
        if not m or not m.group(1):
            return {"_source": "tencent", "error": "无数据"}
        parts = m.group(1).split("~")
        if len(parts) < 48:
            return {"_source": "tencent", "error": f"字段数不足: {len(parts)}"}
        result = {
            "_source": "tencent",
            "代码": parts[2], "名称": parts[1],
            "最新价": _safe_float(parts[3]),
            "昨收": _safe_float(parts[4]), "今开": _safe_float(parts[5]),
            "成交量": _safe_float(parts[6]),  # 手
            "成交额": _safe_float(parts[37]) * 10000 if _safe_float(parts[37]) else None,  # 万→元
            "涨跌额": _safe_float(parts[31]), "涨跌幅": _safe_float(parts[32]),
            "最高": _safe_float(parts[33]), "最低": _safe_float(parts[34]),
            "换手率": _safe_float(parts[38]),
            "PE": _safe_float(parts[39]),
            "总市值": _safe_float(parts[45]) * 1e8 if _safe_float(parts[45]) else None,
            "流通市值": _safe_float(parts[44]) * 1e8 if _safe_float(parts[44]) else None,
            "涨停价": _safe_float(parts[47]),
            "跌停价": _safe_float(parts[48]) if len(parts) > 48 else None,
            "量比": _safe_float(parts[49]) if len(parts) > 49 else None,
            "五档": {
                "买一": {"价": _safe_float(parts[9]),  "量": _safe_float(parts[10])},
                "买二": {"价": _safe_float(parts[11]), "量": _safe_float(parts[12])},
                "买三": {"价": _safe_float(parts[13]), "量": _safe_float(parts[14])},
                "买四": {"价": _safe_float(parts[15]), "量": _safe_float(parts[16])},
                "买五": {"价": _safe_float(parts[17]), "量": _safe_float(parts[18])},
                "卖一": {"价": _safe_float(parts[19]), "量": _safe_float(parts[20])},
                "卖二": {"价": _safe_float(parts[21]), "量": _safe_float(parts[22])},
                "卖三": {"价": _safe_float(parts[23]), "量": _safe_float(parts[24])},
                "卖四": {"价": _safe_float(parts[25]), "量": _safe_float(parts[26])},
                "卖五": {"价": _safe_float(parts[27]), "量": _safe_float(parts[28])},
            },
        }
        return result
    except Exception as e:
        return {"_source": "tencent", "error": str(e)}


# =========================================================================== #
#  Source 3: 新浪财经 hq.sinajs.cn — 第三源（含买卖五档）
# =========================================================================== #

def fetch_sina(code: str) -> Dict[str, Any]:
    """新浪财经实时行情（逗号分隔，32+字段，含买卖五档）"""
    mkt = infer_market(code)
    sina_code = f"{mkt}{code}"
    try:
        resp = requests.get(f"https://hq.sinajs.cn/list={sina_code}",
                            headers=HEADERS_SINA, timeout=TIMEOUT)
        resp.encoding = "gbk"
        m = re.search(r'"(.*)"', resp.text.strip())
        if not m or not m.group(1):
            return {"_source": "sina", "error": "无数据"}
        p = m.group(1).split(",")
        if len(p) < 32:
            return {"_source": "sina", "error": f"字段不足: {len(p)}"}
        result = {
            "_source": "sina",
            "代码": code, "名称": p[0],
            "今开": _safe_float(p[1]), "昨收": _safe_float(p[2]),
            "最新价": _safe_float(p[3]),
            "最高": _safe_float(p[4]), "最低": _safe_float(p[5]),
            "成交量": int(_safe_float(p[8], 0) / 100) if _safe_float(p[8]) else None,  # 股→手
            "成交额": _safe_float(p[9]),
            "日期": p[30], "时间": p[31],
            "五档": {
                "买一": {"价": _safe_float(p[11]), "量": int(_safe_float(p[10], 0) / 100)},
                "买二": {"价": _safe_float(p[13]), "量": int(_safe_float(p[12], 0) / 100)},
                "买三": {"价": _safe_float(p[15]), "量": int(_safe_float(p[14], 0) / 100)},
                "买四": {"价": _safe_float(p[17]), "量": int(_safe_float(p[16], 0) / 100)},
                "买五": {"价": _safe_float(p[19]), "量": int(_safe_float(p[18], 0) / 100)},
                "卖一": {"价": _safe_float(p[21]), "量": int(_safe_float(p[20], 0) / 100)},
                "卖二": {"价": _safe_float(p[23]), "量": int(_safe_float(p[22], 0) / 100)},
                "卖三": {"价": _safe_float(p[25]), "量": int(_safe_float(p[24], 0) / 100)},
                "卖四": {"价": _safe_float(p[27]), "量": int(_safe_float(p[26], 0) / 100)},
                "卖五": {"价": _safe_float(p[29]), "量": int(_safe_float(p[28], 0) / 100)},
            },
        }
        return result
    except Exception as e:
        return {"_source": "sina", "error": str(e)}


# =========================================================================== #
#  Source 4: 网易财经 api.money.126.net — 第四源（含五档+52周）
# =========================================================================== #

def fetch_netease(code: str) -> Dict[str, Any]:
    """网易财经实时行情（JSON，字段丰富）"""
    # 网易代码规则：0=上交所，1=深交所（与东财相反）
    mkt = infer_market(code)
    if mkt == "sh":
        ne_code = f"0{code}"
    else:
        ne_code = f"1{code}"
    try:
        resp = requests.get(f"https://api.money.126.net/data/feed/{ne_code},money.api",
                            headers=HEADERS_163, timeout=TIMEOUT)
        text = resp.text.strip()
        # 去掉 JSONP 回调 _ntes_quote_callback({...});
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if not m:
            return {"_source": "netease", "error": "解析失败"}
        data = json.loads(m.group())
        d = data.get(ne_code, {})
        if not d:
            return {"_source": "netease", "error": "无数据"}
        result = {
            "_source": "netease",
            "代码": code, "名称": d.get("name", ""),
            "最新价": d.get("price"), "昨收": d.get("yestclose"),
            "今开": d.get("open"), "最高": d.get("high"), "最低": d.get("low"),
            "涨跌额": d.get("updown"), "涨跌幅": d.get("percent", 0) * 100 if d.get("percent") else None,
            "成交量": d.get("volume"),  # 手
            "成交额": d.get("turnover"),
            "换手率": d.get("turnoverrate"),
            "PE": d.get("pe"),
            "PB": d.get("pb"),
            "总市值": d.get("mktcap"),
            "流通市值": d.get("mktcapfloat") if d.get("mktcapfloat") else None,
            "52周最高": d.get("high52w") if d.get("high52w") else None,
            "52周最低": d.get("low52w") if d.get("low52w") else None,
            "五档": {
                "买一": {"价": d.get("bid1"), "量": d.get("bidvol1")},
                "买二": {"价": d.get("bid2"), "量": d.get("bidvol2")},
                "买三": {"价": d.get("bid3"), "量": d.get("bidvol3")},
                "买四": {"价": d.get("bid4"), "量": d.get("bidvol4")},
                "买五": {"价": d.get("bid5"), "量": d.get("bidvol5")},
                "卖一": {"价": d.get("ask1"), "量": d.get("askvol1")},
                "卖二": {"价": d.get("ask2"), "量": d.get("askvol2")},
                "卖三": {"价": d.get("ask3"), "量": d.get("askvol3")},
                "卖四": {"价": d.get("ask4"), "量": d.get("askvol4")},
                "卖五": {"价": d.get("ask5"), "量": d.get("askvol5")},
            },
        }
        return result
    except Exception as e:
        return {"_source": "netease", "error": str(e)}


# =========================================================================== #
#  东方财富分时数据（当日分钟级走势）
# =========================================================================== #

def fetch_tick_eastmoney(code: str) -> Dict[str, Any]:
    """东方财富 trends2 分时走势（当日分钟级 OHLCV）"""
    secid = infer_secid(code)
    params = {
        "secid": secid,
        "fields1": "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13",
        "fields2": "f51,f52,f53,f54,f55",
        "iscr": 0, "ndays": 1,
        "ut": "fa5fd1943c7b386f172d6893dbfba10b",
    }
    try:
        resp = requests.get("https://push2.eastmoney.com/api/qt/stock/trends2/get",
                            params=params, headers=HEADERS_EAST, timeout=TIMEOUT)
        data = resp.json().get("data", {})
        if not data:
            return {"error": "分时数据为空"}
        name = data.get("name", "")
        pre_close = data.get("preClose")
        trends = data.get("trends", [])
        records = []
        for line in trends:
            parts = line.split(",")
            if len(parts) >= 5:
                records.append({
                    "时间": parts[0],
                    "价格": _safe_float(parts[1]),
                    "均价": _safe_float(parts[2]),
                    "成交量": _safe_float(parts[3]),
                    "成交额": _safe_float(parts[4]),
                })
        return {
            "名称": name, "昨收": pre_close,
            "数据条数": len(records),
            "分时": records[-30:] if len(records) > 30 else records,  # 最近30条
        }
    except Exception as e:
        return {"error": f"分时获取失败: {e}"}


# =========================================================================== #
#  多源聚合 & 交叉校验
# =========================================================================== #

def fetch_multi_source(code: str, depth: bool = False, tick: bool = False) -> Dict[str, Any]:
    """四源并行采集 + 交叉校验 + 融合输出"""
    results = {}
    tasks = {
        "eastmoney": lambda: fetch_eastmoney(code, depth),
        "tencent": lambda: fetch_tencent(code),
        "sina": lambda: fetch_sina(code),
        "netease": lambda: fetch_netease(code),
    }
    if tick:
        tasks["tick"] = lambda: fetch_tick_eastmoney(code)

    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(fn): name for name, fn in tasks.items()}
        for future in as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result()
            except Exception as e:
                results[name] = {"_source": name, "error": str(e)}

    # 融合 — 以东财为主，其他源补充
    merged = _merge_quotes(results, code)

    # 交叉校验
    merged["_校验"] = _cross_validate(results)

    if tick and "tick" in results and "error" not in results["tick"]:
        merged["分时数据"] = results["tick"]

    # ── 派生指标：基于近 250 日 K 线计算 52 周/换手率/成交额/超额收益 ──
    # 若 FinancialData/<code>_kline.json 存在则用缓存，否则现拉一次
    try:
        derived = _compute_kline_derived_metrics(code, merged)
        if derived:
            merged["交易元数据"] = derived
    except Exception as e:
        merged["交易元数据"] = {"error": f"K 线派生失败: {e}"}

    return merged


def _compute_kline_derived_metrics(code: str, base_quote: dict) -> Dict[str, Any]:
    """基于近 250 日日 K 线计算交易元数据卡所需字段。

    输出字段：
      - 52周最高/最低/对应日期、当前 52 周区间百分位、距 52 周高位的回撤幅度
      - 近 5/20/60 日平均换手率（需流通股本，从 base_quote 取）
      - 近 60 日日均成交额、累计成交额
      - 近 60 日振幅（最高 / 最低 − 1）
      - 近 60 日 vs 沪深 300 超额收益（用 close 比较，沪深300 单独拉）

    数据源：优先读 FinancialData/<code>_kline.json，否则调 _fetch_kline_for_chart。
    """
    # 1) 读 K 线（从 chart_generator 复用 fetch 函数）
    import os
    workspace = Path(os.environ.get("CODEBUDDY_WORKSPACE", Path(__file__).resolve().parents[3]))
    kline_cache = workspace / "FinancialData" / f"{code}_kline.json"
    records = []
    if kline_cache.exists():
        try:
            data = json.loads(kline_cache.read_text(encoding='utf-8'))
            records = data.get("K线数据") if isinstance(data, dict) else data
        except Exception:
            records = []
    if not records:
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from chart_generator import _fetch_kline_for_chart
            records = _fetch_kline_for_chart(code, 250) or []
        except Exception:
            records = []
    if not records or len(records) < 20:
        return {"error": "K 线数据不足（<20 日）"}

    # 2) 解析为 (date, open, high, low, close, vol, amount) 七元组
    parsed = []
    for r in records:
        try:
            d = r.get("日期") or r.get("date")
            o = float(r.get("开盘") or r.get("open") or 0)
            h = float(r.get("最高") or r.get("high") or 0)
            lw = float(r.get("最低") or r.get("low") or 0)
            c = float(r.get("收盘") or r.get("close") or 0)
            v = float(r.get("成交量") or r.get("volume") or 0)
            a = float(r.get("成交额") or r.get("amount") or 0)
            if d and c:
                parsed.append((d, o, h, lw, c, v, a))
        except Exception:
            continue
    if not parsed:
        return {"error": "K 线字段解析失败"}
    parsed.sort(key=lambda x: x[0])  # 升序

    # 3) 52 周（取近 250 个交易日；不足则取全部）
    win = parsed[-250:] if len(parsed) >= 250 else parsed
    highs = [(r[2], r[0]) for r in win]
    lows  = [(r[3], r[0]) for r in win]
    h_val, h_date = max(highs, key=lambda x: x[0])
    l_val, l_date = min(lows,  key=lambda x: x[0])
    cur_price = parsed[-1][4]
    if h_val > l_val:
        pct_in_range = (cur_price - l_val) / (h_val - l_val) * 100
    else:
        pct_in_range = None
    drawdown_from_high = (cur_price / h_val - 1) * 100 if h_val else None

    # 4) 换手率：需要流通股本。从 base_quote 取，单位需统一为 "股"
    float_mv = base_quote.get("流通市值")  # 元
    float_share = None
    if float_mv and cur_price:
        try:
            float_share = float(float_mv) / float(cur_price)  # 股
        except Exception:
            float_share = None

    def _avg_turnover(n):
        recent = parsed[-n:] if len(parsed) >= n else parsed
        if not float_share or float_share <= 0:
            return None
        vols = [r[5] for r in recent]
        if not vols:
            return None
        return sum(vols) / len(vols) / float_share * 100  # %

    turnover_5 = _avg_turnover(5)
    turnover_60 = _avg_turnover(60)

    # 5) 近 60 日成交额
    recent_60 = parsed[-60:] if len(parsed) >= 60 else parsed
    amount_avg_60 = sum(r[6] for r in recent_60) / len(recent_60) if recent_60 else None
    amount_sum_60 = sum(r[6] for r in recent_60) if recent_60 else None

    # 6) 近 60 日振幅（max high - min low）/ 起点 close
    if recent_60:
        max_h = max(r[2] for r in recent_60)
        min_l = min(r[3] for r in recent_60)
        start_c = recent_60[0][4]
        amplitude_60 = (max_h - min_l) / start_c * 100 if start_c else None
    else:
        amplitude_60 = None

    # 7) 近 60 日 vs 沪深 300 超额：拉沪深300 同期 close
    excess_60 = None
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from chart_generator import _fetch_kline_for_chart
        hs300 = _fetch_kline_for_chart("000300", 250) or []  # 沪深 300
        if hs300:
            hs_parsed = []
            for r in hs300:
                try:
                    d = r.get("日期") or r.get("date")
                    c = float(r.get("收盘") or r.get("close") or 0)
                    if d and c:
                        hs_parsed.append((d, c))
                except Exception:
                    continue
            hs_parsed.sort(key=lambda x: x[0])
            # 对齐：取最后 60 个 stock 交易日，找同日期 hs300 close
            if len(parsed) >= 60 and len(hs_parsed) >= 60:
                stock_window = parsed[-60:]
                hs_dict = {d: c for d, c in hs_parsed}
                start_date = stock_window[0][0]
                end_date = stock_window[-1][0]
                hs_start = hs_dict.get(start_date)
                hs_end = hs_dict.get(end_date)
                if hs_start and hs_end and hs_start > 0:
                    stock_ret = (stock_window[-1][4] / stock_window[0][4] - 1) * 100
                    hs_ret = (hs_end / hs_start - 1) * 100
                    excess_60 = stock_ret - hs_ret
    except Exception:
        excess_60 = None

    return {
        "52周最高": round(h_val, 2),
        "52周最高日期": h_date,
        "52周最低": round(l_val, 2),
        "52周最低日期": l_date,
        "52周区间百分位%": round(pct_in_range, 1) if pct_in_range is not None else None,
        "距52周高位%": round(drawdown_from_high, 2) if drawdown_from_high is not None else None,
        "近5日平均换手率%": round(turnover_5, 2) if turnover_5 is not None else None,
        "近60日平均换手率%": round(turnover_60, 2) if turnover_60 is not None else None,
        "近60日日均成交额": amount_avg_60,
        "近60日累计成交额": amount_sum_60,
        "近60日振幅%": round(amplitude_60, 1) if amplitude_60 is not None else None,
        "近60日vs沪深300超额%": round(excess_60, 2) if excess_60 is not None else None,
    }


def _merge_quotes(results: Dict, code: str) -> Dict[str, Any]:
    """融合多源数据，东财优先，其他源补充缺失字段"""
    # 优先级：东财 > 腾讯 > 新浪 > 网易
    priority = ["eastmoney", "tencent", "sina", "netease"]
    merged = {"代码": code, "采集时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

    # 基础字段融合
    for field in ["名称", "最新价", "涨跌额", "涨跌幅", "今开", "昨收", "最高", "最低",
                  "成交量", "成交额", "换手率", "量比", "振幅", "PE", "PB",
                  "总市值", "流通市值", "52周最高", "52周最低", "委比"]:
        for src in priority:
            d = results.get(src, {})
            if "error" in d:
                continue
            val = d.get(field)
            if val is not None:
                merged[field] = val
                break

    # 腾讯独有字段
    qq = results.get("tencent", {})
    if "error" not in qq:
        if qq.get("涨停价"):
            merged["涨停价"] = qq["涨停价"]
        if qq.get("跌停价"):
            merged["跌停价"] = qq["跌停价"]

    # 五档盘口融合 — 取字段最全的源
    depth_sources = []
    for src in priority:
        d = results.get(src, {})
        if "error" not in d and d.get("五档"):
            depth_data = d["五档"]
            # 检查五档数据质量
            valid_count = sum(1 for k, v in depth_data.items()
                             if v.get("价") is not None and v.get("价") != 0)
            if valid_count >= 5:
                depth_sources.append((src, depth_data, valid_count))

    if depth_sources:
        best_src = max(depth_sources, key=lambda x: x[2])
        merged["五档"] = best_src[1]
        merged["五档来源"] = best_src[0]

    # 数据源状态
    source_status = {}
    for src in priority:
        d = results.get(src, {})
        if "error" in d:
            source_status[src] = f"❌ {d['error']}"
        else:
            source_status[src] = f"✅ {d.get('最新价', '—')}"
    merged["_数据源"] = source_status

    return merged


def _cross_validate(results: Dict) -> Dict[str, Any]:
    """多源交叉校验最新价"""
    prices = {}
    for src in ["eastmoney", "tencent", "sina", "netease"]:
        d = results.get(src, {})
        if "error" not in d and d.get("最新价") is not None:
            prices[src] = d["最新价"]

    if len(prices) < 2:
        return {"状态": "⚠ 有效数据源不足，无法交叉校验", "各源价格": prices}

    vals = list(prices.values())
    avg = sum(vals) / len(vals)
    max_dev = max(abs(v - avg) / avg * 100 for v in vals) if avg != 0 else 0

    if max_dev > 1.0:
        status = f"⚠ 偏差 {max_dev:.2f}%（>1%，可能有延迟差异）"
    elif max_dev > 0.1:
        status = f"✅ 偏差 {max_dev:.2f}%（正常）"
    else:
        status = f"✅ 完全一致"

    return {"状态": status, "各源价格": prices, "最大偏差%": round(max_dev, 2)}


# =========================================================================== #
#  大盘指数快照（多源）
# =========================================================================== #

# 核心指数配置
CORE_INDICES = [
    ("上证指数",   "1.000001",  "s_sh000001"),
    ("深证成指",   "0.399001",  "s_sz399001"),
    ("创业板指",   "0.399006",  "s_sz399006"),
    ("沪深300",   "1.000300",  "s_sh000300"),
    ("中证500",   "1.000905",  "s_sh000905"),
    ("中证1000",  "0.399852",  "s_sz399852"),
    ("科创50",    "1.000688",  "s_sh000688"),
    ("上证50",    "1.000016",  "s_sh000016"),
    ("中证全指",   "1.000985",  ""),
    ("北证50",    "0.899050",  ""),
]


def fetch_indices_eastmoney() -> List[Dict]:
    """东财 ulist 批量获取指数行情"""
    secids = ",".join(idx[1] for idx in CORE_INDICES)
    params = {
        "fltt": 2,
        "fields": "f1,f2,f3,f4,f6,f12,f13,f14,f104,f105,f106",
        "secids": secids,
        "ut": "fa5fd1943c7b386f172d6893dbfba10b",
    }
    try:
        resp = requests.get("https://push2.eastmoney.com/api/qt/ulist.np/get",
                            params=params, headers=HEADERS_EAST, timeout=TIMEOUT)
        items = resp.json().get("data", {}).get("diff", [])
        results = []
        for item in items:
            results.append({
                "指数": item.get("f14", ""),
                "最新": item.get("f2"),
                "涨跌幅%": item.get("f3"),
                "涨跌额": item.get("f4"),
                "成交额": item.get("f6"),
                "上涨": item.get("f104"),
                "下跌": item.get("f105"),
            })
        return results
    except Exception as e:
        return [{"error": str(e)}]


def fetch_indices_sina() -> List[Dict]:
    """新浪简化指数行情（备用）"""
    codes = ",".join(idx[2] for idx in CORE_INDICES if idx[2])
    try:
        resp = requests.get(f"https://hq.sinajs.cn/list={codes}",
                            headers=HEADERS_SINA, timeout=TIMEOUT)
        resp.encoding = "gbk"
        lines = [l.strip() for l in resp.text.split(";") if l.strip() and '"' in l]
        results = []
        idx_map = {idx[2]: idx[0] for idx in CORE_INDICES if idx[2]}
        sina_codes = [idx[2] for idx in CORE_INDICES if idx[2]]
        for i, line in enumerate(lines):
            m = re.search(r'"(.*)"', line)
            if not m:
                continue
            parts = m.group(1).split(",")
            if len(parts) >= 5:
                name = sina_codes[i] if i < len(sina_codes) else ""
                name = idx_map.get(name, parts[0])
                results.append({
                    "指数": name,
                    "最新": _safe_float(parts[1]),
                    "涨跌幅%": _safe_float(parts[3]),
                    "涨跌额": _safe_float(parts[2]),
                    "成交量万手": round(_safe_float(parts[4], 0) / 1e4, 1),
                })
        return results
    except Exception as e:
        return [{"error": str(e)}]


def fetch_index_snapshot() -> Dict[str, Any]:
    """大盘指数快照 — 东财主源 + 新浪备用"""
    results = {}
    with ThreadPoolExecutor(max_workers=2) as pool:
        f_east = pool.submit(fetch_indices_eastmoney)
        f_sina = pool.submit(fetch_indices_sina)
        results["eastmoney"] = f_east.result()
        results["sina"] = f_sina.result()

    # 东财优先
    east = results["eastmoney"]
    if east and "error" not in east[0]:
        return {"来源": "东方财富", "数据": east}
    # 降级到新浪
    sina = results["sina"]
    if sina and "error" not in sina[0]:
        return {"来源": "新浪财经（降级）", "数据": sina}
    return {"error": "东财和新浪指数均不可用"}


# =========================================================================== #
#  Markdown 格式化
# =========================================================================== #

def format_merged_md(data: Dict[str, Any]) -> str:
    """格式化多源聚合行情"""
    lines = [
        f"## {data.get('名称', '')}（{data.get('代码', '')}）多源实时行情",
        f"**采集时间**: {data.get('采集时间', '')}",
        "",
    ]

    # 数据源状态
    src = data.get("_数据源", {})
    if src:
        lines.append("### 数据源状态")
        lines.append("| 来源 | 状态 |")
        lines.append("|------|------|")
        for name, status in src.items():
            lines.append(f"| {name} | {status} |")
        lines.append("")

    # 交叉校验
    validate = data.get("_校验", {})
    if validate:
        lines.append(f"> **交叉校验**: {validate.get('状态', '')}")
        lines.append("")

    # 核心行情
    lines.append("### 核心行情")
    lines.append("| 指标 | 数值 |")
    lines.append("|------|------|")
    skip = {"代码", "名称", "采集时间", "_数据源", "_校验", "五档", "五档来源", "分时数据"}
    for k, v in data.items():
        if k in skip or k.startswith("_"):
            continue
        if k in ("成交额", "总市值", "流通市值"):
            v = _fmt_amount(v)
        elif v is None:
            v = "—"
        lines.append(f"| {k} | {v} |")
    lines.append("")

    # 五档盘口
    depth = data.get("五档")
    if depth:
        lines.append(f"### 五档盘口（来源: {data.get('五档来源', '未知')}）")
        lines.append("| 档位 | 价格 | 数量(手) |")
        lines.append("|------|------|---------|")
        for level in ["卖五", "卖四", "卖三", "卖二", "卖一"]:
            d = depth.get(level, {})
            lines.append(f"| {level} | {d.get('价', '—')} | {d.get('量', '—')} |")
        lines.append("|------|------|---------|")
        for level in ["买一", "买二", "买三", "买四", "买五"]:
            d = depth.get(level, {})
            lines.append(f"| {level} | {d.get('价', '—')} | {d.get('量', '—')} |")
        lines.append("")

    # 分时数据
    tick_data = data.get("分时数据")
    if tick_data and "error" not in tick_data:
        lines.append("### 分时走势（最近30分钟）")
        lines.append("| 时间 | 价格 | 均价 | 成交量 |")
        lines.append("|------|------|------|--------|")
        for r in tick_data.get("分时", []):
            lines.append(
                f"| {r.get('时间', '')} | {r.get('价格', '—')} "
                f"| {r.get('均价', '—')} | {r.get('成交量', '—')} |"
            )
        lines.append("")

    return "\n".join(lines)


def format_index_md(data: Dict[str, Any]) -> str:
    """格式化大盘指数快照"""
    if "error" in data:
        return f"[!] {data['error']}"
    lines = [
        f"## 大盘指数快照",
        f"**数据源**: {data.get('来源', '')}",
        f"**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "| 指数 | 最新 | 涨跌幅% | 涨跌额 | 成交额 | 上涨 | 下跌 |",
        "|------|------|---------|--------|--------|------|------|",
    ]
    for item in data.get("数据", []):
        if "error" in item:
            continue
        amt = _fmt_amount(item.get("成交额")) if item.get("成交额") else "—"
        lines.append(
            f"| {item.get('指数', '')} "
            f"| {item.get('最新', '—')} "
            f"| {item.get('涨跌幅%', '—')} "
            f"| {item.get('涨跌额', '—')} "
            f"| {amt} "
            f"| {item.get('上涨', '—')} "
            f"| {item.get('下跌', '—')} |"
        )
    return "\n".join(lines)


# =========================================================================== #
#  主入口
# =========================================================================== #

def main():
    parser = argparse.ArgumentParser(
        description="多源实时行情增强脚本（东财+腾讯+新浪+网易 四源聚合）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python realtime_quote_enhanced.py 600519              # 四源聚合行情
  python realtime_quote_enhanced.py 600519 --depth      # 含五档盘口
  python realtime_quote_enhanced.py 600519 --tick       # 含分时数据
  python realtime_quote_enhanced.py 600519,000858       # 批量
  python realtime_quote_enhanced.py --index             # 大盘指数
  python realtime_quote_enhanced.py --overview          # 市场概览
  python realtime_quote_enhanced.py 600519 --json       # JSON输出
        """,
    )
    parser.add_argument("codes", nargs="?", default="",
                        help="股票代码（逗号分隔多只）")
    parser.add_argument("--index", action="store_true",
                        help="大盘指数快照")
    parser.add_argument("--overview", action="store_true",
                        help="市场概览")
    parser.add_argument("--depth", action="store_true",
                        help="含五档盘口")
    parser.add_argument("--tick", action="store_true",
                        help="含分时数据")
    parser.add_argument("--source", default="",
                        choices=["", "eastmoney", "tencent", "sina", "netease"],
                        help="指定单一数据源")
    parser.add_argument("--json", action="store_true",
                        help="JSON输出")
    parser.add_argument("--output", "-o", type=str,
                        help="输出到文件")
    args = parser.parse_args()

    all_output = []

    if args.index or args.overview:
        idx_data = fetch_index_snapshot()
        if args.json:
            all_output.append(json.dumps(idx_data, ensure_ascii=False, indent=2))
        else:
            all_output.append(format_index_md(idx_data))

    if args.codes:
        codes = [c.strip() for c in args.codes.split(",") if c.strip()]
        for code in codes:
            if args.source:
                # 单源模式
                fn_map = {
                    "eastmoney": lambda c=code: fetch_eastmoney(c, args.depth),
                    "tencent": lambda c=code: fetch_tencent(c),
                    "sina": lambda c=code: fetch_sina(c),
                    "netease": lambda c=code: fetch_netease(c),
                }
                data = fn_map[args.source]()
                if args.json:
                    all_output.append(json.dumps(data, ensure_ascii=False, indent=2))
                else:
                    all_output.append(f"### {code} — {args.source}")
                    all_output.append(json.dumps(data, ensure_ascii=False, indent=2))
            else:
                # 四源聚合模式
                data = fetch_multi_source(code, depth=args.depth, tick=args.tick)
                if args.json:
                    all_output.append(json.dumps(data, ensure_ascii=False, indent=2))
                else:
                    all_output.append(format_merged_md(data))
            all_output.append("")

    if not args.codes and not args.index and not args.overview:
        parser.print_help()
        sys.exit(1)

    output = "\n".join(all_output)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"已保存到 {args.output}", file=sys.stderr)
    else:
        _print_utf8(output)


def _print_utf8(text: str):
    """Windows 兼容的 UTF-8 输出（避免 GBK 编码错误）。"""
    try:
        print(text)
    except UnicodeEncodeError:
        sys.stdout.buffer.write(text.encode("utf-8"))
        sys.stdout.buffer.write(b"\n")
        sys.stdout.buffer.flush()


if __name__ == "__main__":
    main()
