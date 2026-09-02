# -*- coding: utf-8 -*-
"""
CSIndex Valuation Scraper — 中证指数有限公司官方数据采集

数据源: 中证指数官网 API (https://www.csindex.com.cn/)

功能模块:
  1. 指数行情（日度行情、涨跌幅、成交量）
  2. 指数估值（PE/PB/股息率）
  3. 指数基本信息

用法:
  python csindex_valuation_scraper.py --all               # 全部宽基指数
  python csindex_valuation_scraper.py --index 000300       # 指定指数代码
  python csindex_valuation_scraper.py --perf               # 行情数据
  python csindex_valuation_scraper.py --valuation          # 估值数据
  python csindex_valuation_scraper.py --all --output FinancialData/csindex_data.md
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


import argparse
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: requests is required. Install with: pip install requests", file=sys.stderr)
    sys.exit(1)

# ============================================================
# Configuration
# ============================================================

TIMEOUT = 15
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Referer": "https://www.csindex.com.cn/",
}

# 核心宽基+热门指数
DEFAULT_INDICES = [
    ("000300", "沪深300"),
    ("000905", "中证500"),
    ("000852", "中证1000"),
    ("000016", "上证50"),
    ("399006", "创业板指"),
    ("000688", "科创50"),
    ("399303", "国证2000"),
    ("H30533", "中证红利"),
    ("930997", "中证全指"),
]

# ============================================================
# API Helpers
# ============================================================

def csindex_api(endpoint, params=None):
    """统一中证指数API请求"""
    url = f"https://www.csindex.com.cn/{endpoint}"
    try:
        try:
            resp = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
        except requests.exceptions.SSLError:
            print("WARN: SSL 证书校验失败，降级为跳过校验（仅用于公开数据采集）", file=sys.stderr)
            resp = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT, verify=False)
        resp.raise_for_status()
        data = resp.json()
        return data
    except Exception as e:
        print(f"  ⚠️ 中证API请求失败 [{endpoint}]: {e}", file=sys.stderr)
        return None

# ============================================================
# Module 1: 指数行情
# ============================================================

def fetch_index_perf(index_code, days=30):
    """获取指数日度行情"""
    end = datetime.now().strftime("%Y%m%d")
    start = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")

    data = csindex_api("csindex-home/perf/index-perf", {
        "indexCode": index_code,
        "startDate": start,
        "endDate": end,
    })
    if not data or data.get("code") != "200" or not data.get("data"):
        return None

    results = []
    for r in data["data"]:
        results.append({
            "date": r.get("tradeDate", ""),
            "name": r.get("indexNameCn", ""),
            "open": r.get("open"),
            "high": r.get("high"),
            "low": r.get("low"),
            "close": r.get("close"),
            "change": r.get("change"),
            "change_pct": r.get("changePct"),
            "turnover": r.get("turnover"),  # 成交额（元）
        })
    return results

# ============================================================
# Module 2: 指数估值 (PE/PB/股息率)
# ============================================================

def fetch_index_valuation(index_code):
    """获取指数估值 — PE、PB、股息率"""
    end = datetime.now().strftime("%Y%m%d")
    start = (datetime.now() - timedelta(days=60)).strftime("%Y%m%d")

    # 尝试估值接口
    data = csindex_api("csindex-home/perf/index-perf-valuations", {
        "indexCode": index_code,
        "startDate": start,
        "endDate": end,
    })
    if data and data.get("code") == "200" and data.get("data"):
        results = []
        for r in data["data"]:
            results.append({
                "date": r.get("tradeDate", ""),
                "pe": r.get("pe"),
                "pb": r.get("pb"),
                "dividend_yield": r.get("dividendYield"),
            })
        return results

    # 备用: 尝试另一个估值端点
    data2 = csindex_api("csindex-home/perf/index-valuation", {
        "indexCode": index_code,
    })
    if data2 and data2.get("code") == "200" and data2.get("data"):
        d = data2["data"]
        return [{
            "date": d.get("tradeDate", datetime.now().strftime("%Y%m%d")),
            "pe": d.get("pe") or d.get("peTtm"),
            "pb": d.get("pb") or d.get("pbMrq"),
            "dividend_yield": d.get("dividendYield"),
        }]

    return None

# ============================================================
# Module 3: 指数基本信息
# ============================================================

def fetch_index_info(index_code):
    """获取指数基本信息"""
    data = csindex_api("csindex-home/index/detail/index-detail", {
        "indexCode": index_code,
    })
    if not data or data.get("code") != "200" or not data.get("data"):
        return None

    d = data["data"]
    return {
        "code": index_code,
        "name_cn": d.get("indexNameCn", ""),
        "name_en": d.get("indexNameEn", ""),
        "base_date": d.get("baseDate", ""),
        "base_point": d.get("basePoint"),
        "constituent_count": d.get("constituentNum"),
        "market_cap": d.get("indexMarketCap"),
        "index_type": d.get("indexClassify", ""),
    }

# ============================================================
# Formatters
# ============================================================

def format_md(all_data):
    """格式化为Markdown"""
    lines = [
        "# 中证指数官方数据",
        f"\n> 数据来源：中证指数有限公司(csindex.com.cn) | 采集时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"> 📎 信源API：`https://www.csindex.com.cn/csindex-home/perf/index-perf` (行情) | `https://www.csindex.com.cn/csindex-home/perf/index-perf-valuations` (估值) | `https://www.csindex.com.cn/csindex-home/index/detail/index-detail` (信息)",
        ""
    ]

    # 行情汇总表
    if any(d.get("perf") for d in all_data.values()):
        lines.append("## 指数行情")
        lines.append("")
        lines.append("| 指数 | 最新收盘 | 涨跌幅 | 近5日涨跌 | 近20日涨跌 |")
        lines.append("|------|---------|--------|----------|-----------|")
        for code, d in all_data.items():
            perf = d.get("perf")
            if not perf:
                continue
            name = d.get("name", code)
            latest = perf[-1] if perf else {}
            close = latest.get("close", "—")
            chg = latest.get("change_pct")
            chg_str = f"{chg:.2f}%" if chg is not None else "—"

            # 近5日和近20日涨跌
            chg5 = chg20 = "—"
            if len(perf) >= 5:
                c5 = perf[-5].get("close")
                cl = perf[-1].get("close")
                if c5 and cl:
                    chg5 = f"{(cl - c5) / c5 * 100:.2f}%"
            if len(perf) >= 20:
                c20 = perf[-20].get("close")
                cl = perf[-1].get("close")
                if c20 and cl:
                    chg20 = f"{(cl - c20) / c20 * 100:.2f}%"

            lines.append(f"| {name} | {close} | {chg_str} | {chg5} | {chg20} |")
        lines.append("")

    # 估值汇总表
    if any(d.get("valuation") for d in all_data.values()):
        lines.append("## 指数估值")
        lines.append("")
        lines.append("| 指数 | PE(TTM) | PB(MRQ) | 股息率 |")
        lines.append("|------|---------|---------|--------|")
        for code, d in all_data.items():
            val = d.get("valuation")
            if not val:
                continue
            name = d.get("name", code)
            latest = val[-1] if val else {}
            pe = latest.get("pe")
            pb = latest.get("pb")
            dy = latest.get("dividend_yield")
            pe_str = f"{pe:.2f}" if pe is not None else "—"
            pb_str = f"{pb:.2f}" if pb is not None else "—"
            dy_str = f"{dy:.2f}%" if dy is not None else "—"
            lines.append(f"| {name} | {pe_str} | {pb_str} | {dy_str} |")
        lines.append("")

    # 各指数详细行情
    for code, d in all_data.items():
        perf = d.get("perf")
        if not perf or len(perf) <= 1:
            continue
        name = d.get("name", code)
        lines.append(f"### {name}({code}) 近期行情")
        lines.append("")
        lines.append("| 日期 | 收盘 | 涨跌幅 | 成交额(亿) |")
        lines.append("|------|------|--------|-----------|")
        for r in perf[-10:]:
            chg = r.get("change_pct")
            chg_str = f"{chg:.2f}%" if chg is not None else "—"
            tv = r.get("turnover")
            tv_str = f"{tv / 1e8:.1f}" if tv else "—"
            lines.append(f"| {r['date']} | {r.get('close', '—')} | {chg_str} | {tv_str} |")
        lines.append("")

    return "\n".join(lines)

# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="中证指数官方数据采集 — 行情/估值")
    parser.add_argument("--all", action="store_true", help="采集全部默认指数")
    parser.add_argument("--index", type=str, action="append", help="指定指数代码（可多次使用）")
    parser.add_argument("--perf", action="store_true", help="行情数据")
    parser.add_argument("--valuation", action="store_true", help="估值数据")
    parser.add_argument("--days", type=int, default=30, help="行情天数（默认30）")
    parser.add_argument("--json", action="store_true", help="JSON格式输出")
    parser.add_argument("--output", type=str, help="输出文件路径")
    args = parser.parse_args()

    # 确定要采集的指数
    if args.index:
        indices = [(c, c) for c in args.index]
    else:
        indices = DEFAULT_INDICES

    if not any([args.perf, args.valuation]):
        args.perf = True
        args.valuation = True

    all_data = {}
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _fetch_one_index(code_name_pair):
        """并发采集单个指数的行情+估值"""
        code, name = code_name_pair
        print(f"📊 采集 {name}({code})...", file=sys.stderr)
        result = {"name": name}
        if args.perf:
            result["perf"] = fetch_index_perf(code, args.days)
        if args.valuation:
            result["valuation"] = fetch_index_valuation(code)
        return code, result

    # 3并发（中证指数官网限流温和，3线程足够安全）
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(_fetch_one_index, pair): pair[0] for pair in indices}
        for future in as_completed(futures):
            code, result = future.result()
            all_data[code] = result

    if args.json:
        output = json.dumps(all_data, ensure_ascii=False, indent=2)
    else:
        output = format_md(all_data)

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"✅ 已保存至 {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
