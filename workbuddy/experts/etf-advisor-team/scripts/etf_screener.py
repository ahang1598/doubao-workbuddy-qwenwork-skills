#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
场内ETF/LOF全市场筛选引擎 — ETF 顾问团队内置

功能：从东方财富获取全市场场内ETF行情数据（含涨跌幅、市值、换手率、资金流向等），
      支持多条件组合筛选、关键词搜索、分类汇总。
      可选启用二次增强（--enrich），逐只补充近1年/3年涨幅、夏普比率等高级指标。

数据源：
  - 主源：东方财富 Push2 clist API（全量ETF列表+行情）
  - 备源：腾讯财经 qt.gtimg.cn（主源不可达时降级）
  - 增强：天天基金 pingzhongdata API（阶段涨幅/规模信息）

用法：
  # 全市场ETF列表（按成交额降序）
  python etf_screener.py --sort 成交额 --desc --limit 30

  # 按关键词筛选（多词OR匹配）
  python etf_screener.py -k "通信设备|5G" --sort 涨跌幅 --desc --limit 20

  # 组合条件筛选
  python etf_screener.py -c "总市值>10,换手率>1" --sort 涨跌幅 --desc --limit 30

  # 带增强（补充近1年涨幅等高级指标）
  python etf_screener.py -k "有色金属|稀土" --enrich --sort 近1年涨幅 --desc --limit 15

  # 使用内置模板
  python etf_screener.py --template 年度涨幅榜 --limit 30

  # JSON输出
  python etf_screener.py --sort 涨跌幅 --desc --limit 20 --json

输出：Markdown 或 JSON 格式
"""

# --- UTF-8 bootstrap (auto-injected, idempotent) ---
import os as _bootstrap_os, sys as _bootstrap_sys
_bootstrap_dir = _bootstrap_os.path.dirname(_bootstrap_os.path.abspath(__file__))
if _bootstrap_dir not in _bootstrap_sys.path:
    _bootstrap_sys.path.insert(0, _bootstrap_dir)
try:
    from _utf8_bootstrap import enable_utf8_io as _bootstrap_enable
    _bootstrap_enable()
except Exception:
    pass
# --- end UTF-8 bootstrap ---


import os
import re
import sys
import json
import time
import argparse
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# --------------------------------------------------------------------------- #
#  常量
# --------------------------------------------------------------------------- #

PUSH2_API = "https://push2.eastmoney.com/api/qt/clist/get"
TENCENT_QUOTE_URL = "https://qt.gtimg.cn/q="
PINGZHONG_API = "http://fund.eastmoney.com/pingzhongdata/{code}.js"

HEADERS_QUOTE = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://quote.eastmoney.com/",
    "Accept": "*/*",
}

HEADERS_FUND = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://fund.eastmoney.com/",
}

PAGE_SIZE = 500
WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
CACHE_DIR = os.path.join(WORKSPACE_ROOT, "FinancialData", "_cache")
ETF_CODE_CACHE_NAME = "fund_recommend_etf_tencent_codes.json"
ENRICH_FIELDS = {
    "近1年涨幅(%)", "近3年涨幅(%)", "近6月涨幅(%)",
    "近3月涨幅(%)", "近1月涨幅(%)", "今年来涨幅(%)", "规模信息",
}

# --------------------------------------------------------------------------- #
#  安全常量
# --------------------------------------------------------------------------- #

# ETF 代码合法格式：6 位纯数字
_RE_ETF_CODE = re.compile(r"^\d{6}$")

# 允许 _request_with_retry 访问的 URL 白名单前缀（纵深防御）
_ALLOWED_URL_PREFIXES = (
    "https://push2.eastmoney.com/",
    "https://qt.gtimg.cn/",
    "http://fund.eastmoney.com/",
    "http://www.cninfo.com.cn/",
)

# ETF 市场参数白名单
_VALID_MARKETS = frozenset({"all", "sh", "sz"})

# --------------------------------------------------------------------------- #

# ETF fs 参数（东方财富 Push2）

ETF_FS_MAP = {
    "all": ["m:1+s:1128", "m:0+s:1128"],   # 沪市ETF + 深市ETF
    "sh":  ["m:1+s:1128"],                   # 仅沪市ETF
    "sz":  ["m:0+s:1128"],                   # 仅深市ETF
}

# ETF代码前缀 → 市场
ETF_PREFIXES_SH = ("510", "511", "512", "513", "515", "516", "517", "518",
                   "560", "561", "562", "563", "588")
ETF_PREFIXES_SZ = ("159",)

# 基础字段映射（Push2 API 返回字段 → 标准名称）
FIELD_MAP = {
    "代码":          "f12",
    "名称":          "f14",
    "最新价":        "f2",
    "涨跌幅(%)":     "f3",
    "涨跌额":        "f4",
    "成交量(手)":    "f5",
    "成交额":        "f6",
    "换手率(%)":     "f8",
    "PE(动态)":      "f9",
    "最高":          "f15",
    "最低":          "f16",
    "开盘":          "f17",
    "昨收":          "f18",
    "总市值":        "f20",
    "流通市值":      "f21",
    "PB":            "f23",
    "60日涨跌(%)":   "f24",
    "年初至今(%)":   "f25",
    "上市日期":      "f26",
    "主力净流入":    "f62",
}

# 筛选字段别名
FIELD_ALIAS = {
    "涨跌幅":       "涨跌幅(%)",
    "换手率":       "换手率(%)",
    "60日涨跌":     "60日涨跌(%)",
    "年初至今":     "年初至今(%)",
    "市值":         "总市值",
    "成交额(亿)":   "成交额",
    "成交额(万)":   "成交额",
    "规模":         "总市值",
    # 增强字段别名
    "近1年涨幅":    "近1年涨幅(%)",
    "近3年涨幅":    "近3年涨幅(%)",
    "近6月涨幅":    "近6月涨幅(%)",
    "近3月涨幅":    "近3月涨幅(%)",
    "近1月涨幅":    "近1月涨幅(%)",
    "今年来涨幅":   "今年来涨幅(%)",
    "近1年":        "近1年涨幅(%)",
    "近3年":        "近3年涨幅(%)",
    "近6月":        "近6月涨幅(%)",
    "近3月":        "近3月涨幅(%)",
    "近1月":        "近1月涨幅(%)",
    "今年来":       "今年来涨幅(%)",
}

# 内置模板
TEMPLATES = {
    "年度涨幅榜": {
        "conditions": [],
        "enrich": True,
        "sort_by": "近1年涨幅(%)",
        "sort_desc": True,
        "description": "全市场ETF按近1年涨幅排行（需增强数据）",
    },
    "今年来涨幅榜": {
        "conditions": [],
        "sort_by": "年初至今(%)",
        "sort_desc": True,
        "description": "全市场ETF按年初至今涨幅排行",
    },
    "成交活跃榜": {
        "conditions": [("总市值", ">", 5e8)],
        "sort_by": "成交额",
        "sort_desc": True,
        "description": "规模>5亿的ETF按成交额排行",
    },
    "资金净流入榜": {
        "conditions": [("总市值", ">", 5e8)],
        "sort_by": "主力净流入",
        "sort_desc": True,
        "description": "规模>5亿的ETF按主力净流入排行",
    },
    "大规模ETF": {
        "conditions": [("总市值", ">", 100e8)],
        "sort_by": "总市值",
        "sort_desc": True,
        "description": "规模>100亿的大规模ETF",
    },
}

# 打印锁（多线程安全）
_print_lock = threading.Lock()


def _print(msg: str):
    with _print_lock:
        print(msg, file=sys.stderr)


def _ensure_cache_dir() -> None:
    os.makedirs(CACHE_DIR, exist_ok=True)


def _cache_path(name: str) -> str:
    _ensure_cache_dir()
    return os.path.join(CACHE_DIR, name)


def _load_cached_json(name: str) -> Any:
    path = _cache_path(name)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _save_cached_json(name: str, payload: Any) -> None:
    path = _cache_path(name)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
    except Exception:
        pass


def _safe_float(val) -> Optional[float]:

    """安全转浮点数"""
    if val is None or val == "" or val == "-" or val == "--":
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


# --------------------------------------------------------------------------- #
#  HTTP 重试
# --------------------------------------------------------------------------- #

def _request_with_retry(method: str, url: str, max_retries: int = 2, **kwargs) -> requests.Response:
    """带指数退避重试的 HTTP 请求

    安全措施：仅允许访问白名单中的 URL 前缀，防止 SSRF。
    """
    # 安全检查：URL 白名单校验
    if not any(url.startswith(prefix) for prefix in _ALLOWED_URL_PREFIXES):
        raise ValueError(f"[安全拦截] URL 不在白名单中: {url[:80]}")

    last_err = None
    timeout = kwargs.pop("timeout", 15)
    for attempt in range(max_retries + 1):
        try:
            resp = requests.request(method, url, timeout=timeout, **kwargs)
            resp.raise_for_status()
            return resp
        except Exception as e:
            last_err = e
            if attempt < max_retries:
                wait = 1.0 * (2 ** attempt)
                time.sleep(wait)
    raise last_err


# --------------------------------------------------------------------------- #
#  ETF代码工具
# --------------------------------------------------------------------------- #

def is_etf_code(code: str) -> bool:
    """判断是否为合法的场内ETF代码

    安全措施：要求 6 位纯数字 + 合法前缀，防止注入攻击。
    """
    return bool(_RE_ETF_CODE.match(code)) and code.startswith(ETF_PREFIXES_SH + ETF_PREFIXES_SZ)


def etf_market(code: str) -> str:
    """ETF代码 → 市场(sh/sz)"""
    return "sz" if code.startswith("159") else "sh"


def etf_secid(code: str) -> str:
    """ETF代码 → 东方财富secid"""
    return f"1.{code}" if etf_market(code) == "sh" else f"0.{code}"


def etf_tencent_code(code: str) -> str:
    """ETF代码 → 腾讯行情代码"""
    return f"{etf_market(code)}{code}"


# --------------------------------------------------------------------------- #
#  数据采集：主源 — 东方财富 Push2
# --------------------------------------------------------------------------- #

def fetch_etfs_eastmoney(market: str = "all") -> List[Dict[str, Any]]:
    """从东方财富Push2获取全市场场内ETF列表+行情

    Args:
        market: "all" / "sh" / "sz"

    Returns:
        ETF列表，每项包含代码/名称/最新价/涨跌幅/成交额/市值等字段
    """
    # 安全检查：market 参数白名单校验
    if market not in _VALID_MARKETS:
        _print(f"  [安全] market 参数非法({market})，降级为 all")
        market = "all"
    fs_params = ETF_FS_MAP.get(market, ETF_FS_MAP["all"])
    all_items = []

    fields = ",".join([
        "f1,f2,f3,f4,f5,f6,f7,f8,f9",
        "f12,f13,f14,f15,f16,f17,f18",
        "f20,f21,f23,f24,f25,f26",
        "f62,f115,f128,f136,f167",
    ])

    for fs_param in fs_params:
        pn = 1
        while True:
            params = {
                "pn": pn, "pz": PAGE_SIZE, "po": 1, "np": 1,
                "fltt": 2, "invt": 2,
                "fid": "f3", "fs": fs_param, "fields": fields,
                "ut": "fa5fd1943c7b386f172d6893dbfba10b",
            }
            try:
                resp = _request_with_retry("GET", PUSH2_API, max_retries=2,
                                           params=params, headers=HEADERS_QUOTE)
                data = resp.json()
                items = data.get("data", {}).get("diff", []) if data.get("data") else []
                total = data.get("data", {}).get("total", 0) if data.get("data") else 0
            except Exception as e:
                _print(f"  [东方财富] ETF获取失败: {e}")
                break

            for item in items:
                code = str(item.get("f12", ""))
                if not code:
                    continue
                rec = {
                    "代码":          code,
                    "名称":          item.get("f14", ""),
                    "最新价":        _safe_float(item.get("f2")),
                    "涨跌幅(%)":     _safe_float(item.get("f3")),
                    "涨跌额":        _safe_float(item.get("f4")),
                    "成交量(手)":    _safe_float(item.get("f5")),
                    "成交额":        _safe_float(item.get("f6")),
                    "换手率(%)":     _safe_float(item.get("f8")),
                    "PE(动态)":      _safe_float(item.get("f9")),
                    "最高":          _safe_float(item.get("f15")),
                    "最低":          _safe_float(item.get("f16")),
                    "开盘":          _safe_float(item.get("f17")),
                    "昨收":          _safe_float(item.get("f18")),
                    "总市值":        _safe_float(item.get("f20")),
                    "流通市值":      _safe_float(item.get("f21")),
                    "PB":            _safe_float(item.get("f23")),
                    "60日涨跌(%)":   _safe_float(item.get("f24")),
                    "年初至今(%)":   _safe_float(item.get("f25")),
                    "上市日期":      item.get("f26"),
                    "主力净流入":    _safe_float(item.get("f62")),
                    "市场":          "sh" if item.get("f13") == 1 else "sz",
                    # 增强字段占位（enrich后填充）
                    "近1年涨幅(%)":  None,
                    "近3年涨幅(%)":  None,
                    "近6月涨幅(%)":  None,
                    "近3月涨幅(%)":  None,
                    "近1月涨幅(%)":  None,
                    "今年来涨幅(%)": None,
                    "规模信息":      None,
                }
                # 计算成交额(亿)方便筛选
                if rec["成交额"] is not None:
                    rec["成交额(亿)"] = round(rec["成交额"] / 1e8, 4)
                else:
                    rec["成交额(亿)"] = None
                # 总市值(亿)
                if rec["总市值"] is not None:
                    rec["总市值(亿)"] = round(rec["总市值"] / 1e8, 2)
                else:
                    rec["总市值(亿)"] = None

                all_items.append(rec)

            if not items or pn * PAGE_SIZE >= total:
                break
            pn += 1
            time.sleep(0.03)

    return all_items


# --------------------------------------------------------------------------- #
#  数据采集：备源 — 腾讯财经
# --------------------------------------------------------------------------- #

def _parse_tencent_etf_line(line: str) -> Optional[Dict]:
    """解析腾讯单行ETF行情数据"""
    if "=" not in line or '""' in line:
        return None
    try:
        raw = line.split('="')[1].rstrip('";')
        parts = raw.split("~")
        if len(parts) < 50:
            return None
        code = parts[2]
        if not is_etf_code(code):
            return None

        market = "sh" if "v_sh" in line else "sz"
        rec = {
            "代码":          code,
            "名称":          parts[1],
            "最新价":        _safe_float(parts[3]),
            "涨跌幅(%)":     _safe_float(parts[32]),
            "涨跌额":        _safe_float(parts[31]),
            "成交量(手)":    _safe_float(parts[36]),
            "成交额":        _safe_float(parts[37]) * 10000 if _safe_float(parts[37]) else None,
            "换手率(%)":     _safe_float(parts[38]),
            "PE(动态)":      _safe_float(parts[39]),
            "最高":          _safe_float(parts[33]) if len(parts) > 33 else None,
            "最低":          _safe_float(parts[34]) if len(parts) > 34 else None,
            "开盘":          _safe_float(parts[5]) if len(parts) > 5 else None,
            "昨收":          _safe_float(parts[4]) if len(parts) > 4 else None,
            "总市值":        _safe_float(parts[45]) * 1e8 if len(parts) > 45 and _safe_float(parts[45]) else None,
            "流通市值":      _safe_float(parts[44]) * 1e8 if len(parts) > 44 and _safe_float(parts[44]) else None,
            "PB":            _safe_float(parts[46]) if len(parts) > 46 else None,
            "60日涨跌(%)":   None,
            "年初至今(%)":   None,
            "上市日期":      None,
            "主力净流入":    None,
            "市场":          market,
            "近1年涨幅(%)":  None,
            "近3年涨幅(%)":  None,
            "近6月涨幅(%)":  None,
            "近3月涨幅(%)":  None,
            "近1月涨幅(%)":  None,
            "今年来涨幅(%)": None,
            "规模信息":      None,
        }
        if rec["成交额"] is not None:
            rec["成交额(亿)"] = round(rec["成交额"] / 1e8, 4)
        else:
            rec["成交额(亿)"] = None
        if rec["总市值"] is not None:
            rec["总市值(亿)"] = round(rec["总市值"] / 1e8, 2)
        else:
            rec["总市值(亿)"] = None
        return rec
    except (IndexError, ValueError):
        return None


def _get_all_etf_codes() -> List[str]:
    """获取全量ETF腾讯行情代码列表

    策略：
    - 优先复用本地缓存，避免备源场景下重复穷举腾讯代码
    - 深交所ETF：从巨潮 fund_stock.json 获取（该接口只返回深交所基金）
    - 上交所ETF：穷举前缀范围 + 腾讯行情验证（巨潮无上交所基金数据）
    """
    cached_payload = _load_cached_json(ETF_CODE_CACHE_NAME)
    if isinstance(cached_payload, dict):
        cached_codes = cached_payload.get("codes") or []
        if cached_codes:
            _print(f"  [缓存] ETF腾讯代码 {len(cached_codes)} 只")
            return cached_codes

    codes = []


    # 1. 深交所ETF — 从巨潮获取
    try:
        resp = _request_with_retry(
            "GET", "http://www.cninfo.com.cn/new/data/fund_stock.json",
            max_retries=2, headers=HEADERS_QUOTE, timeout=10)
        data = resp.json()
        stocks = data.get("stockList", [])
        for s in stocks:
            code = s.get("code", "")
            if is_etf_code(code):
                codes.append(etf_tencent_code(code))
        _print(f"  [巨潮] 深交所ETF代码: {len(codes)} 只")
    except Exception as e:
        _print(f"  [巨潮ETF代码] 获取失败: {e}")

    # 2. 上交所ETF — 穷举前缀 + 腾讯行情验证（并发化）
    sh_codes = []
    batch_size = 80  # 腾讯单次可处理更多
    tencent_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://finance.qq.com/",
    }

    # 预生成所有批次
    all_probe_batches = []
    for prefix in ETF_PREFIXES_SH:
        candidates = [f"sh{prefix}{str(i).zfill(3)}" for i in range(1000)]
        for i in range(0, len(candidates), batch_size):
            all_probe_batches.append(candidates[i:i + batch_size])

    def _probe_one_batch(batch):
        """并发探测单批ETF代码"""
        symbols = ",".join(batch)
        found = []
        try:
            resp = _request_with_retry(
                "GET", TENCENT_QUOTE_URL + symbols,
                max_retries=1, headers=tencent_headers, timeout=10)
            resp.encoding = "gbk"
            for line in resp.text.strip().split("\n"):
                if '=""' not in line and "~" in line:
                    try:
                        raw = line.split('="')[1].rstrip('";')
                        parts = raw.split("~")
                        if len(parts) >= 50 and parts[1]:
                            found.append(f"sh{parts[2]}")
                    except (IndexError, ValueError):
                        pass
        except Exception:
            pass
        return found

    from concurrent.futures import ThreadPoolExecutor, as_completed
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = [pool.submit(_probe_one_batch, b) for b in all_probe_batches]
        for future in as_completed(futures):
            sh_codes.extend(future.result())

    if sh_codes:
        _print(f"  [腾讯穷举] 上交所ETF代码: {len(sh_codes)} 只")
        codes.extend(sh_codes)

    deduped_codes = list(dict.fromkeys(codes))
    if deduped_codes:
        _save_cached_json(ETF_CODE_CACHE_NAME, {
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "codes": deduped_codes,
        })

    return deduped_codes



def fetch_etfs_tencent() -> List[Dict[str, Any]]:
    """备源：腾讯财经批量获取ETF行情"""
    codes = _get_all_etf_codes()
    if not codes:
        _print("  [腾讯信源] 无法获取ETF代码列表")
        return []

    # 安全检查：过滤非法代码格式（合法格式: sh/sz + 6位数字）
    _re_tencent_code = re.compile(r"^(?:sh|sz)\d{6}$")
    safe_codes = [c for c in codes if _re_tencent_code.match(c)]
    if len(safe_codes) < len(codes):
        _print(f"  [安全] 过滤了 {len(codes) - len(safe_codes)} 个非法格式代码")
    codes = safe_codes

    _print(f"  [腾讯信源] 获取 {len(codes)} 只ETF代码，分批请求行情...")
    all_items = []
    batch_size = 50
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://finance.qq.com/",
    }

    for i in range(0, len(codes), batch_size):
        batch = codes[i:i + batch_size]
        symbols = ",".join(batch)
        try:
            resp = _request_with_retry("GET", TENCENT_QUOTE_URL + symbols,
                                       max_retries=1, headers=headers, timeout=10)
            resp.encoding = "gbk"
            for line in resp.text.strip().split("\n"):
                rec = _parse_tencent_etf_line(line)
                if rec:
                    all_items.append(rec)
        except Exception as e:
            _print(f"  [腾讯信源] 批次 {i//batch_size+1} 失败: {e}")

    return all_items


# --------------------------------------------------------------------------- #
#  多信源调度
# --------------------------------------------------------------------------- #

_MIN_ETF_COUNT = 200  # 全市场ETF至少200只
_ETF_LIST_CACHE_TTL_SEC = 24 * 3600  # ETF 全量列表缓存 24h


def _cache_path() -> "Path":
    """返回 ETF 列表缓存文件路径。缓存目录在本目录的 .cache/ 下。"""
    from pathlib import Path as _P
    cache_dir = _P(__file__).resolve().parent.parent / ".cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / "etf_list.json"


def _load_etf_cache(market: str) -> Optional[Tuple[List[Dict], str]]:
    """若本地缓存存在且未过期，返回 (ETF 列表, 缓存来源)，否则 None。

    缓存减少每次启动因东方财富超时浪费 10s 的问题。
    """
    import json as _json
    import time as _time
    try:
        p = _cache_path()
        if not p.exists():
            return None
        data = _json.loads(p.read_text(encoding="utf-8"))
        if data.get("market") != market:
            return None
        age = _time.time() - data.get("timestamp", 0)
        if age > _ETF_LIST_CACHE_TTL_SEC:
            return None
        items = data.get("items", [])
        source = data.get("source", "cache")
        if len(items) >= _MIN_ETF_COUNT:
            return items, f"本地缓存（{source}，{int(age/60)}分钟前）"
    except Exception:
        pass
    return None


def _save_etf_cache(market: str, items: List[Dict], source: str) -> None:
    """保存 ETF 列表到本地缓存，忽略一切异常。"""
    import json as _json
    import time as _time
    try:
        p = _cache_path()
        p.write_text(
            _json.dumps({
                "market": market,
                "source": source,
                "timestamp": _time.time(),
                "items": items,
            }, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception:
        pass


def fetch_all_etfs(market: str = "all") -> Tuple[List[Dict], str]:
    """获取全市场场内ETF列表（多信源降级 + 本地缓存）。

    执行顺序：
    1. 东方财富 Push2（实时行情最全）
    2. 腾讯财经（备源，列表覆盖更全）
    3. 本地缓存（24h 内有效，兜底避免东财连接失败浪费 10s+）

    Returns:
        (ETF列表, 实际使用的信源名称)
    """
    # 信源1：东方财富
    try:
        _print("  [数据源] 尝试 东方财富 Push2...")
        items = fetch_etfs_eastmoney(market)
        if len(items) >= _MIN_ETF_COUNT:
            _print(f"  [数据源] 东方财富 成功, 获取 {len(items)} 只ETF")
            _save_etf_cache(market, items, "东方财富")
            return items, "东方财富"
        elif items:
            _print(f"  [数据源] 东方财富 数据量偏少({len(items)}), 尝试备源")
        else:
            _print("  [数据源] 东方财富 返回空数据, 尝试备源")
    except Exception as e:
        _print(f"  [数据源] 东方财富 失败: {e}")

    # 信源2：腾讯财经
    try:
        _print("  [数据源] 尝试 腾讯财经...")
        items = fetch_etfs_tencent()
        if items:
            _print(f"  [数据源] 腾讯财经 成功, 获取 {len(items)} 只ETF")
            _save_etf_cache(market, items, "腾讯财经")
            return items, "腾讯财经"
    except Exception as e:
        _print(f"  [数据源] 腾讯财经 失败: {e}")

    # 信源3（兜底）：本地缓存
    cached = _load_etf_cache(market)
    if cached is not None:
        items, source = cached
        _print(f"  [数据源] ⚠️ 在线信源均不可用，启用{source}，共 {len(items)} 只ETF")
        return items, source

    _print("  [数据源] 所有信源均失败（含本地缓存）")
    return [], ""


# --------------------------------------------------------------------------- #
#  增强数据：天天基金 pingzhongdata API
# --------------------------------------------------------------------------- #

def _fetch_enrich_one(code: str) -> Dict[str, Any]:
    """获取单只ETF的增强数据（阶段涨幅+规模）"""
    result = {"代码": code}
    # 安全检查：code 必须为 6 位纯数字
    if not _RE_ETF_CODE.match(code):
        return result
    try:
        url = PINGZHONG_API.format(code=code)
        resp = requests.get(url, headers=HEADERS_FUND, timeout=10)
        if resp.status_code != 200:
            return result
        text = resp.text

        # 提取阶段涨幅
        patterns = [
            (r'var\s+syl_1n\s*=\s*"([^"]*)"', "近1年涨幅(%)"),
            (r'var\s+syl_6y\s*=\s*"([^"]*)"', "近6月涨幅(%)"),
            (r'var\s+syl_3y\s*=\s*"([^"]*)"', "近3月涨幅(%)"),
            (r'var\s+syl_1y\s*=\s*"([^"]*)"', "近1月涨幅(%)"),
            (r'var\s+syl_3n\s*=\s*"([^"]*)"', "近3年涨幅(%)"),
            (r'var\s+syl_jn\s*=\s*"([^"]*)"', "今年来涨幅(%)"),
        ]
        for pattern, key in patterns:
            match = re.search(pattern, text)
            if match and match.group(1):
                result[key] = _safe_float(match.group(1))

        # 规模信息
        match = re.search(r'var\s+Data_fundScale\s*=\s*"([^"]*)"', text)
        if match:
            result["规模信息"] = match.group(1)

    except Exception:
        pass
    return result


def enrich_etfs(etfs: List[Dict], max_workers: int = 8) -> List[Dict]:
    """批量增强ETF数据（天天基金阶段涨幅）"""
    codes = [etf["代码"] for etf in etfs]
    code_to_etf = {etf["代码"]: etf for etf in etfs}

    _print(f"\n正在增强 {len(codes)} 只ETF的阶段涨幅数据...")
    done_count = 0
    total = len(codes)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_fetch_enrich_one, code): code for code in codes}
        for future in as_completed(futures):
            code = futures[future]
            try:
                result = future.result()
                etf = code_to_etf.get(code)
                if etf:
                    for key in ["近1年涨幅(%)", "近3年涨幅(%)", "近6月涨幅(%)",
                                "近3月涨幅(%)", "近1月涨幅(%)", "今年来涨幅(%)", "规模信息"]:
                        if key in result and result[key] is not None:
                            etf[key] = result[key]
            except Exception:
                pass
            done_count += 1
            if done_count % 50 == 0 or done_count == total:
                _print(f"  增强进度: {done_count}/{total}")

    return etfs


def _conditions_require_enrich(conditions: List[Tuple[str, str, Any]]) -> bool:
    return any(field in ENRICH_FIELDS for field, _, _ in conditions)


def _select_enrich_pool(etfs: List[Dict], limit: int) -> List[Dict]:
    if not etfs:
        return []
    candidate_limit = min(len(etfs), max(limit * 4, limit, 80))
    return etfs[:candidate_limit]


# --------------------------------------------------------------------------- #
#  筛选引擎
# --------------------------------------------------------------------------- #


class ETFScreener:
    """场内ETF多维度筛选引擎"""

    SUPPORTED_OPS = {">", ">=", "<", "<=", "=", "!=", "contains", "!contains", "top%"}

    def __init__(self):
        self.data_source = ""

    @staticmethod
    def resolve_field(field_name: str) -> str:
        """解析字段名（支持别名）"""
        return FIELD_ALIAS.get(field_name, field_name)

    @staticmethod
    def parse_conditions(cond_str: str) -> List[Tuple[str, str, Any]]:
        """解析条件字符串

        格式: "字段>值,字段>=值,字段 contains 关键词"
        """
        if not cond_str or not cond_str.strip():
            return []

        conditions = []
        for part in cond_str.split(","):
            part = part.strip()
            if not part:
                continue

            # 尝试匹配操作符
            matched = False
            for op in [">=", "<=", "!=", ">", "<", "=", "top%", "!contains", "contains"]:
                if op == "top%":
                    m = re.match(r'^(.+?)\s+top%\s+(.+)$', part)
                elif op in ("contains", "!contains"):
                    m = re.match(rf'^(.+?)\s+{re.escape(op)}\s+(.+)$', part)
                else:
                    m = re.match(rf'^(.+?)\s*{re.escape(op)}\s*(.+)$', part)
                if m:
                    field = ETFScreener.resolve_field(m.group(1).strip())
                    val_str = m.group(2).strip()
                    if op in ("contains", "!contains"):
                        conditions.append((field, op, val_str))
                    else:
                        try:
                            conditions.append((field, op, float(val_str)))
                        except ValueError:
                            _print(f"[警告] 无法解析条件: {part}")
                    matched = True
                    break
            if not matched:
                _print(f"[警告] 无法解析条件: {part}")

        return conditions

    @staticmethod
    def _check_condition(etf: Dict, field: str, op: str, value: Any,
                         all_etfs: Optional[List[Dict]] = None) -> bool:
        """检查单只ETF是否满足条件"""
        etf_val = etf.get(field)

        if op == "contains":
            return value.lower() in str(etf_val or "").lower()
        if op == "!contains":
            return value.lower() not in str(etf_val or "").lower()

        if etf_val is None:
            return False
        try:
            etf_val = float(etf_val)
        except (ValueError, TypeError):
            return False

        if op == "top%":
            if all_etfs is None:
                return True
            all_vals = sorted(
                [float(f.get(field, 0) or 0) for f in all_etfs if f.get(field) is not None],
                reverse=True
            )
            if not all_vals:
                return True
            try:
                rank = all_vals.index(etf_val) + 1
            except ValueError:
                rank = len(all_vals)
            percentile = (rank / len(all_vals)) * 100
            return percentile <= value

        if op == ">":
            return etf_val > value
        if op == ">=":
            return etf_val >= value
        if op == "<":
            return etf_val < value
        if op == "<=":
            return etf_val <= value
        if op == "=":
            return etf_val == value
        if op == "!=":
            return etf_val != value
        return False

    def apply_filter(self, etfs: List[Dict], conditions: List[Tuple],
                     keyword: str = None, exclude_keyword: str = None,
                     ) -> Tuple[List[Dict], List[Dict]]:
        """应用筛选条件，返回 (筛选结果, 漏斗记录)"""
        funnel = [{"步骤": "初始标的池", "条件": "全市场场内ETF", "剩余数量": len(etfs)}]
        result = list(etfs)

        # 关键词筛选
        if keyword:
            keywords = [kw.strip() for kw in keyword.split("|") if kw.strip()]
            before = len(result)
            result = [e for e in result if any(kw.lower() in (e.get("名称", "") or "").lower() for kw in keywords)]
            funnel.append({
                "步骤": f"关键词: {keyword}",
                "条件": f"名称包含 \"{keyword}\"",
                "过滤前": before, "剩余数量": len(result),
                "淘汰数量": before - len(result),
            })

        # 排除关键词
        if exclude_keyword:
            ex_keywords = [kw.strip() for kw in exclude_keyword.split("|") if kw.strip()]
            for kw in ex_keywords:
                before = len(result)
                result = [e for e in result if kw.lower() not in (e.get("名称", "") or "").lower()]
                funnel.append({
                    "步骤": f"排除: {kw}",
                    "条件": f"名称不含 \"{kw}\"",
                    "过滤前": before, "剩余数量": len(result),
                    "淘汰数量": before - len(result),
                })

        # 条件筛选
        for field, op, value in conditions:
            before = len(result)
            result = [e for e in result if self._check_condition(e, field, op, value, result)]
            display_val = value if isinstance(value, str) else f"{value:g}" if isinstance(value, float) else str(value)
            funnel.append({
                "步骤": f"条件: {field} {op} {display_val}",
                "条件": f"{field} {op} {display_val}",
                "过滤前": before, "剩余数量": len(result),
                "淘汰数量": before - len(result),
            })

        funnel.append({"步骤": "最终筛选结果", "条件": "全部条件(AND)", "剩余数量": len(result)})
        return result, funnel

    @staticmethod
    def sort_etfs(etfs: List[Dict], sort_by: str, desc: bool = True) -> List[Dict]:
        """排序"""
        sort_field = FIELD_ALIAS.get(sort_by, sort_by)

        def sort_key(e):
            val = e.get(sort_field)
            if val is None:
                return float('-inf') if desc else float('inf')
            try:
                return float(val)
            except (ValueError, TypeError):
                return float('-inf') if desc else float('inf')

        return sorted(etfs, key=sort_key, reverse=desc)

    # ------------------------------------------------------------------- #
    #  输出格式化
    # ------------------------------------------------------------------- #

    def to_markdown(self, etfs: List[Dict], funnel: List[Dict],
                    conditions: List[Tuple], keyword: str = None,
                    exclude_keyword: str = None, sort_by: str = None,
                    limit: int = 50, enriched: bool = False,
                    template_name: str = None) -> str:
        """五段式Markdown报告输出"""
        lines = ["# 场内ETF筛选结果报告\n"]

        # 一、筛选任务
        lines.append("## 【一、筛选任务核心信息】\n")
        lines.append(f"1. **筛选范围**：全市场场内ETF（沪深两市）| 数据截止日期：{datetime.now().strftime('%Y-%m-%d')}")
        lines.append(f"   - 数据来源：{self.data_source}")
        lines.append(f"   - 📎 信源API：`https://push2.eastmoney.com/api/qt/clist/get` (ETF列表行情) | 备源 `https://qt.gtimg.cn/q=` (腾讯财经)")
        if template_name:
            lines.append(f"   - 使用模板：「{template_name}」")
        if enriched:
            lines.append(f"   - 增强数据：已启用（天天基金阶段涨幅）")
            lines.append(f"   - 📎 增强信源：`http://fund.eastmoney.com/pingzhongdata/<code>.js`")
        lines.append(f"\n3. **筛选条件**：")
        cond_idx = 1
        if keyword:
            lines.append(f"   - 条件{cond_idx}：名称包含 \"{keyword}\"")
            cond_idx += 1
        if exclude_keyword:
            lines.append(f"   - 条件{cond_idx}：名称不含 \"{exclude_keyword}\"")
            cond_idx += 1
        for field, op, value in conditions:
            display_val = value if isinstance(value, str) else f"{value:g}"
            lines.append(f"   - 条件{cond_idx}：{field} {op} {display_val}")
            cond_idx += 1
        if cond_idx == 1:
            lines.append("   - （无额外筛选条件）")

        if sort_by:
            lines.append(f"\n4. **排序规则**：按 {sort_by} 降序排列")
        lines.append(f"5. **输出上限**：{limit} 条\n")

        # 二、筛选过程
        lines.append("## 【二、筛选过程回溯】\n")
        lines.append("| 步骤 | 条件 | 剩余数量 |")
        lines.append("|------|------|----------|")
        for step in funnel:
            lines.append(f"| {step['步骤']} | {step['条件']} | {step['剩余数量']} |")
        lines.append("")

        # 三、结果明细
        shown = etfs[:limit]
        lines.append(f"## 【三、筛选结果明细】\n")
        lines.append(f"共 **{len(etfs)}** 只ETF符合全部条件，以下展示前 **{len(shown)}** 条：\n")

        if enriched:
            lines.append("| 序号 | 代码 | 名称 | 最新价 | 涨跌幅% | 近1月% | 近3月% | 近6月% | 近1年% | 近3年% | 今年来% | 总市值(亿) | 成交额(亿) |")
            lines.append("|------|------|------|--------|---------|--------|--------|--------|--------|--------|---------|-----------|-----------|")
            for i, etf in enumerate(shown):
                lines.append(
                    f"| {i+1} | {etf['代码']} | {etf['名称']} "
                    f"| {self._fmt(etf.get('最新价'))} "
                    f"| {self._fmt(etf.get('涨跌幅(%)'))} "
                    f"| {self._fmt(etf.get('近1月涨幅(%)'))} "
                    f"| {self._fmt(etf.get('近3月涨幅(%)'))} "
                    f"| {self._fmt(etf.get('近6月涨幅(%)'))} "
                    f"| {self._fmt(etf.get('近1年涨幅(%)'))} "
                    f"| {self._fmt(etf.get('近3年涨幅(%)'))} "
                    f"| {self._fmt(etf.get('今年来涨幅(%)'))} "
                    f"| {self._fmt(etf.get('总市值(亿)'))} "
                    f"| {self._fmt(etf.get('成交额(亿)'))} |"
                )
        else:
            lines.append("| 序号 | 代码 | 名称 | 最新价 | 涨跌幅% | 年初至今% | 60日涨跌% | 换手率% | 总市值(亿) | 成交额(亿) | 主力净流入 |")
            lines.append("|------|------|------|--------|---------|----------|----------|---------|-----------|-----------|-----------|")
            for i, etf in enumerate(shown):
                net_flow = etf.get("主力净流入")
                flow_str = self._fmt_amount(net_flow) if net_flow is not None else "--"
                lines.append(
                    f"| {i+1} | {etf['代码']} | {etf['名称']} "
                    f"| {self._fmt(etf.get('最新价'))} "
                    f"| {self._fmt(etf.get('涨跌幅(%)'))} "
                    f"| {self._fmt(etf.get('年初至今(%)'))} "
                    f"| {self._fmt(etf.get('60日涨跌(%)'))} "
                    f"| {self._fmt(etf.get('换手率(%)'))} "
                    f"| {self._fmt(etf.get('总市值(亿)'))} "
                    f"| {self._fmt(etf.get('成交额(亿)'))} "
                    f"| {flow_str} |"
                )

        # Top亮点
        if shown:
            lines.append(f"\n### Top标的客观数据亮点\n")
            for etf in shown[:3]:
                highlights = [f"**代码 {etf['代码']} {etf['名称']}**"]
                if etf.get("近1年涨幅(%)") is not None:
                    highlights.append(f"近1年涨幅 {etf['近1年涨幅(%)']}%")
                if etf.get("年初至今(%)") is not None:
                    highlights.append(f"年初至今 {etf['年初至今(%)']}%")
                if etf.get("总市值(亿)") is not None:
                    highlights.append(f"总市值 {etf['总市值(亿)']}亿")
                lines.append(f"- {'; '.join(highlights)}")

        lines.append("")

        # 四、风险提示
        lines.append("## 【四、合规与风险强制提示】\n")
        lines.append("> 以上筛选结果仅基于公开历史数据完成条件匹配，不构成任何投资建议。"
                     "基金有风险，投资需谨慎。历史业绩不代表未来表现。\n")
        lines.append("**专项风险提示**：场内ETF以跟踪特定指数为目标，存在跟踪误差风险；"
                     "场内ETF可能出现折溢价，建议在IOPV附近交易；"
                     "部分小规模ETF流动性不足，买卖时需注意冲击成本。\n")

        # 五、建议
        lines.append("## 【五、补充优化建议】\n")
        if not enriched:
            lines.append("1. 使用 `--enrich` 参数可补充近1年/3年涨幅等高级指标。")
        if len(etfs) > 50:
            lines.append("2. 结果较多，建议增加筛选条件或使用关键词缩小范围。")
        lines.append("")

        return "\n".join(lines)

    def to_json(self, etfs: List[Dict], funnel: List[Dict],
                conditions: List[Tuple], keyword: str = None,
                limit: int = 50, enriched: bool = False) -> str:
        """JSON格式输出"""
        output = {
            "筛选任务": {
                "筛选范围": "全市场场内ETF",
                "数据截止日期": datetime.now().strftime("%Y-%m-%d"),
                "数据来源": self.data_source,
                "增强数据": enriched,
                "筛选条件": [
                    {"字段": f, "运算符": o, "阈值": v} for f, o, v in conditions
                ],
                "关键词": keyword,
                "排序字段": None,
                "结果数量上限": limit,
            },
            "筛选漏斗": funnel,
            "筛选结果": etfs[:limit],
            "总符合条件数": len(etfs),
        }
        return json.dumps(output, ensure_ascii=False, indent=2)

    @staticmethod
    def _fmt(val) -> str:
        if val is None:
            return "--"
        if isinstance(val, float):
            return f"{val:.2f}"
        return str(val)

    @staticmethod
    def _fmt_amount(val) -> str:
        """格式化金额（自动选择亿/万单位）"""
        if val is None:
            return "--"
        if abs(val) >= 1e8:
            return f"{val/1e8:.2f}亿"
        elif abs(val) >= 1e4:
            return f"{val/1e4:.0f}万"
        else:
            return f"{val:.0f}"


# --------------------------------------------------------------------------- #
#  CLI
# --------------------------------------------------------------------------- #

def main():
    t0 = time.time()
    parser = argparse.ArgumentParser(
        description="场内ETF/LOF全市场筛选引擎",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-m", "--market", default="all",
                        choices=["all", "sh", "sz"],
                        help="市场范围 (default: all)")
    parser.add_argument("-k", "--keyword",
                        help="ETF名称关键词，多词用'|'分隔 (如 '通信设备|5G')")
    parser.add_argument("-xk", "--exclude-keyword",
                        help="排除关键词，多词用'|'分隔 (如 '货币|利率')")
    parser.add_argument("-c", "--conditions",
                        help="筛选条件，逗号分隔 (如 '总市值>10e8,换手率>1')")
    parser.add_argument("-s", "--sort", default="成交额",
                        help="排序字段 (default: 成交额)")
    parser.add_argument("--desc", action="store_true", default=True,
                        help="降序排列 (default)")
    parser.add_argument("--asc", action="store_true",
                        help="升序排列")
    parser.add_argument("-n", "--limit", type=int, default=30,
                        help="输出条数上限 (default: 30)")
    parser.add_argument("--enrich", action="store_true",
                        help="启用增强数据（补充近1年/3年涨幅等）")
    parser.add_argument("-T", "--template",
                        help=f"使用内置模板: {', '.join(TEMPLATES.keys())}")
    parser.add_argument("--json", action="store_true",
                        help="JSON格式输出")
    parser.add_argument("--output", "-o",
                        help="输出到文件")

    args = parser.parse_args()

    # 防御性处理：去除参数中可能的多余引号
    for attr in ("keyword", "exclude_keyword", "conditions", "sort", "template"):
        val = getattr(args, attr, None)
        if isinstance(val, str):
            setattr(args, attr, val.strip('"').strip("'"))

    # 模板处理
    template_name = None
    if args.template:
        if args.template not in TEMPLATES:
            _print(f"[错误] 未知模板: {args.template}")
            _print(f"可用模板: {', '.join(TEMPLATES.keys())}")
            sys.exit(1)
        tpl = TEMPLATES[args.template]
        template_name = args.template
        conditions = tpl.get("conditions", [])
        sort_by = tpl.get("sort_by", "成交额")
        sort_desc = tpl.get("sort_desc", True)
        need_enrich = tpl.get("enrich", False) or args.enrich
        _print(f"使用模板「{args.template}」: {tpl.get('description', '')}")
    else:
        conditions = ETFScreener.parse_conditions(args.conditions) if args.conditions else []
        sort_by = args.sort
        sort_desc = not args.asc
        need_enrich = args.enrich

    # 数据获取
    _print(f"\n正在获取全市场场内ETF数据 (市场: {args.market})...")
    screener = ETFScreener()
    etfs, source = fetch_all_etfs(args.market)
    screener.data_source = source

    if not etfs:
        _print("[错误] 无法获取ETF数据")
        sys.exit(1)

    _print(f"共获取 {len(etfs)} 只场内ETF\n")

    # 筛选
    result, funnel = screener.apply_filter(
        etfs, conditions,
        keyword=args.keyword,
        exclude_keyword=args.exclude_keyword,
    )

    _print(f"筛选结果: {len(result)} 只符合条件")

    enrich_required_for_sort = FIELD_ALIAS.get(sort_by, sort_by) in ENRICH_FIELDS
    enrich_required_for_filter = _conditions_require_enrich(conditions)

    # 增强 + 排序
    if need_enrich and result:
        if enrich_required_for_sort or enrich_required_for_filter:
            result = enrich_etfs(result)
            result = screener.sort_etfs(result, sort_by, sort_desc)
        else:
            result = screener.sort_etfs(result, sort_by, sort_desc)
            enrich_pool = _select_enrich_pool(result, args.limit)
            enrich_etfs(enrich_pool)
    else:
        result = screener.sort_etfs(result, sort_by, sort_desc)


    # 输出
    if args.json:
        output = screener.to_json(result, funnel, conditions,
                                  keyword=args.keyword, limit=args.limit,
                                  enriched=need_enrich)
    else:
        output = screener.to_markdown(result, funnel, conditions,
                                      keyword=args.keyword,
                                      exclude_keyword=args.exclude_keyword,
                                      sort_by=sort_by, limit=args.limit,
                                      enriched=need_enrich,
                                      template_name=template_name)

    # 写入文件或标准输出
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        _print(f"\n结果已保存到: {args.output}")
    else:
        print(output)

    _print(f"\n筛选完成，耗时 {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
