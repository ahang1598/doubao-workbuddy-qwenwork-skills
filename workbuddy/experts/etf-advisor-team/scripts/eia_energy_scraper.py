# -*- coding: utf-8 -*-
"""
EIA Energy Data Scraper — 美国能源信息署(EIA)官方数据采集

数据源: EIA Open Data API v2 (https://api.eia.gov/v2/)
使用 DEMO_KEY（无需注册），限速 30次/小时

功能模块:
  1. 原油价格（WTI/布伦特日度现货价）
  2. 原油库存（美国周度商业库存）
  3. 原油供需（产量/进口/出口/炼厂开工率）
  4. 天然气（Henry Hub价格 + 库存）

用法:
  python eia_energy_scraper.py --all                    # 全部模块
  python eia_energy_scraper.py --oil-price              # 原油价格
  python eia_energy_scraper.py --oil-inventory           # 原油库存
  python eia_energy_scraper.py --oil-supply              # 原油供需
  python eia_energy_scraper.py --natgas                  # 天然气
  python eia_energy_scraper.py --all --json              # JSON格式输出
  python eia_energy_scraper.py --all --output FinancialData/eia_energy.md
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
import os
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

API_BASE = "https://api.eia.gov/v2"
API_KEY = os.environ.get("EIA_API_KEY", "DEMO_KEY")  # 默认免费公开Key（限速30次/小时），可经环境变量 EIA_API_KEY 覆盖
TIMEOUT = 20

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}

# ============================================================
# API Helper
# ============================================================

def eia_query(route, params=None):
    """统一EIA API请求"""
    url = f"{API_BASE}/{route}"
    base_params = {"api_key": API_KEY}
    if params:
        base_params.update(params)
    try:
        try:
            resp = requests.get(url, params=base_params, headers=HEADERS, timeout=TIMEOUT)
        except requests.exceptions.SSLError:
            print("WARN: SSL 证书校验失败，降级为跳过校验（仅用于公开数据采集）", file=sys.stderr)
            resp = requests.get(url, params=base_params, headers=HEADERS, timeout=TIMEOUT, verify=False)
        resp.raise_for_status()
        data = resp.json()
        if "response" in data and "data" in data["response"]:
            return data["response"]["data"]
        return data
    except requests.exceptions.RequestException as e:
        print(f"  ⚠️ EIA API请求失败 [{route}]: {e}", file=sys.stderr)
        return None
    except (json.JSONDecodeError, KeyError) as e:
        print(f"  ⚠️ EIA API解析失败 [{route}]: {e}", file=sys.stderr)
        return None

# ============================================================
# Module 1: 原油价格
# ============================================================

def fetch_oil_prices(days=30):
    """获取WTI和布伦特原油日度现货价格"""
    results = {}

    # WTI现货价
    wti_data = eia_query("petroleum/pri/spt/data/", {
        "frequency": "daily",
        "data[0]": "value",
        "facets[product][]": "EPCWTI",
        "sort[0][column]": "period",
        "sort[0][direction]": "desc",
        "length": str(days),
    })
    if wti_data:
        results["WTI"] = [{"date": r.get("period"), "price": r.get("value"), "unit": "$/barrel"} for r in wti_data if r.get("value")]

    # 布伦特现货价
    brent_data = eia_query("petroleum/pri/spt/data/", {
        "frequency": "daily",
        "data[0]": "value",
        "facets[product][]": "EPCBRENT",
        "sort[0][column]": "period",
        "sort[0][direction]": "desc",
        "length": str(days),
    })
    if brent_data:
        results["Brent"] = [{"date": r.get("period"), "price": r.get("value"), "unit": "$/barrel"} for r in brent_data if r.get("value")]

    return results

# ============================================================
# Module 2: 原油库存
# ============================================================

def fetch_oil_inventory(weeks=12):
    """获取美国商业原油周度库存"""
    data = eia_query("petroleum/sum/sndw/data/", {
        "frequency": "weekly",
        "data[0]": "value",
        "facets[product][]": "EPC0",
        "facets[process][]": "SAE",
        "sort[0][column]": "period",
        "sort[0][direction]": "desc",
        "length": str(weeks),
    })
    if not data:
        return None

    results = []
    for r in data:
        if r.get("value"):
            results.append({
                "week_ending": r.get("period"),
                "inventory_mb": round(float(r["value"]) / 1000, 1),  # 千桶→百万桶
                "unit": "百万桶",
            })
    return results

# ============================================================
# Module 3: 原油供需 (产量/进口/出口/炼厂开工率)
# ============================================================

def fetch_oil_supply():
    """获取美国原油供需核心数据"""
    results = {}

    # 美国原油产量 (周度)
    prod = eia_query("petroleum/sum/sndw/data/", {
        "frequency": "weekly",
        "data[0]": "value",
        "facets[product][]": "EPC0",
        "facets[process][]": "FPF",
        "sort[0][column]": "period",
        "sort[0][direction]": "desc",
        "length": "8",
    })
    if prod:
        results["production"] = [{"week": r.get("period"), "value_kbd": r.get("value"), "unit": "千桶/日"} for r in prod if r.get("value")]

    # 美国原油进口 (周度)
    imp = eia_query("petroleum/sum/sndw/data/", {
        "frequency": "weekly",
        "data[0]": "value",
        "facets[product][]": "EPC0",
        "facets[process][]": "FIM",
        "sort[0][column]": "period",
        "sort[0][direction]": "desc",
        "length": "8",
    })
    if imp:
        results["imports"] = [{"week": r.get("period"), "value_kbd": r.get("value"), "unit": "千桶/日"} for r in imp if r.get("value")]

    # 炼厂开工率 (周度)
    util = eia_query("petroleum/sum/sndw/data/", {
        "frequency": "weekly",
        "data[0]": "value",
        "facets[product][]": "EPC0",
        "facets[process][]": "OCR",
        "sort[0][column]": "period",
        "sort[0][direction]": "desc",
        "length": "8",
    })
    if util:
        results["refinery_utilization"] = [{"week": r.get("period"), "value_pct": r.get("value"), "unit": "%"} for r in util if r.get("value")]

    return results

# ============================================================
# Module 4: 天然气
# ============================================================

def fetch_natgas(days=30, weeks=12):
    """获取Henry Hub天然气价格 + 库存"""
    results = {}

    # Henry Hub天然气现货价
    hh = eia_query("natural-gas/pri/fut/data/", {
        "frequency": "daily",
        "data[0]": "value",
        "facets[process][]": "FRC",
        "sort[0][column]": "period",
        "sort[0][direction]": "desc",
        "length": str(days),
    })
    if hh:
        results["henry_hub_price"] = [{"date": r.get("period"), "price": r.get("value"), "unit": "$/MMBtu"} for r in hh if r.get("value")]

    # 天然气库存 (周度)
    storage = eia_query("natural-gas/stor/wkly/data/", {
        "frequency": "weekly",
        "data[0]": "value",
        "facets[process][]": "SAT",
        "sort[0][column]": "period",
        "sort[0][direction]": "desc",
        "length": str(weeks),
    })
    if storage:
        results["storage"] = [{"week": r.get("period"), "value_bcf": r.get("value"), "unit": "Bcf"} for r in storage if r.get("value")]

    return results

# ============================================================
# Formatters
# ============================================================

def format_md(data, modules):
    """格式化为Markdown"""
    lines = [
        "# EIA 能源市场数据",
        f"\n> 数据来源：美国能源信息署(EIA) | 采集时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"> 📎 基础API：`{API_BASE}/` (API Key: {API_KEY})",
        ""
    ]

    if "oil_prices" in data and data["oil_prices"]:
        lines.append("## 原油现货价格")
        lines.append(f"📎 **信源API**: `{API_BASE}/petroleum/pri/spt/data/?facets[product][]=EPCWTI` (WTI) | `...EPCBRENT` (Brent)")
        lines.append("")
        prices = data["oil_prices"]
        for name in ["WTI", "Brent"]:
            if name in prices and prices[name]:
                latest = prices[name][0]
                lines.append(f"### {name}原油（最新: **{latest['price']}** 美元/桶，{latest['date']}）")
                lines.append("")
                lines.append("| 日期 | 价格($/桶) |")
                lines.append("|------|-----------|")
                for p in prices[name][:15]:
                    lines.append(f"| {p['date']} | {p['price']} |")
                lines.append("")

    if "oil_inventory" in data and data["oil_inventory"]:
        lines.append("## 美国商业原油库存（周度）")
        lines.append("")
        inv = data["oil_inventory"]
        latest = inv[0]
        prev = inv[1] if len(inv) > 1 else None
        change = ""
        if prev:
            diff = round(latest["inventory_mb"] - prev["inventory_mb"], 1)
            change = f"，周环比 **{'+' if diff >= 0 else ''}{diff}** 百万桶"
        lines.append(f"**最新: {latest['inventory_mb']} 百万桶**（{latest['week_ending']}）{change}")
        lines.append("")
        lines.append("| 周截止日 | 库存(百万桶) | 周变化 |")
        lines.append("|----------|-------------|--------|")
        for i, r in enumerate(inv[:12]):
            wc = ""
            if i + 1 < len(inv):
                d = round(r["inventory_mb"] - inv[i + 1]["inventory_mb"], 1)
                wc = f"{'+' if d >= 0 else ''}{d}"
            lines.append(f"| {r['week_ending']} | {r['inventory_mb']} | {wc} |")
        lines.append("")

    if "oil_supply" in data and data["oil_supply"]:
        lines.append("## 美国原油供需")
        lines.append("")
        supply = data["oil_supply"]
        if "production" in supply and supply["production"]:
            lines.append("### 美国原油产量（周度，千桶/日）")
            lines.append("")
            lines.append("| 周截止日 | 产量(千桶/日) |")
            lines.append("|----------|--------------|")
            for r in supply["production"][:8]:
                lines.append(f"| {r['week']} | {r['value_kbd']} |")
            lines.append("")
        if "imports" in supply and supply["imports"]:
            lines.append("### 美国原油进口（周度，千桶/日）")
            lines.append("")
            lines.append("| 周截止日 | 进口(千桶/日) |")
            lines.append("|----------|--------------|")
            for r in supply["imports"][:8]:
                lines.append(f"| {r['week']} | {r['value_kbd']} |")
            lines.append("")
        if "refinery_utilization" in supply and supply["refinery_utilization"]:
            lines.append("### 炼厂开工率（周度）")
            lines.append("")
            lines.append("| 周截止日 | 开工率(%) |")
            lines.append("|----------|----------|")
            for r in supply["refinery_utilization"][:8]:
                lines.append(f"| {r['week']} | {r['value_pct']} |")
            lines.append("")

    if "natgas" in data and data["natgas"]:
        lines.append("## 天然气市场")
        lines.append("")
        ng = data["natgas"]
        if "henry_hub_price" in ng and ng["henry_hub_price"]:
            latest = ng["henry_hub_price"][0]
            lines.append(f"### Henry Hub 天然气价格（最新: **{latest['price']}** $/MMBtu，{latest['date']}）")
            lines.append("")
            lines.append("| 日期 | 价格($/MMBtu) |")
            lines.append("|------|--------------|")
            for r in ng["henry_hub_price"][:15]:
                lines.append(f"| {r['date']} | {r['price']} |")
            lines.append("")
        if "storage" in ng and ng["storage"]:
            latest = ng["storage"][0]
            lines.append(f"### 天然气库存（最新: **{latest['value_bcf']}** Bcf，{latest['week']}）")
            lines.append("")
            lines.append("| 周截止日 | 库存(Bcf) |")
            lines.append("|----------|----------|")
            for r in ng["storage"][:12]:
                lines.append(f"| {r['week']} | {r['value_bcf']} |")
            lines.append("")

    return "\n".join(lines)

# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="EIA能源数据采集 — 原油/天然气官方数据")
    parser.add_argument("--all", action="store_true", help="采集全部模块")
    parser.add_argument("--oil-price", action="store_true", help="原油现货价格（WTI/布伦特）")
    parser.add_argument("--oil-inventory", action="store_true", help="美国商业原油库存")
    parser.add_argument("--oil-supply", action="store_true", help="原油供需（产量/进口/开工率）")
    parser.add_argument("--natgas", action="store_true", help="天然气（Henry Hub价格+库存）")
    parser.add_argument("--days", type=int, default=30, help="价格数据天数（默认30）")
    parser.add_argument("--weeks", type=int, default=12, help="库存数据周数（默认12）")
    parser.add_argument("--json", action="store_true", help="JSON格式输出")
    parser.add_argument("--output", type=str, help="输出文件路径")
    args = parser.parse_args()

    if not any([args.all, args.oil_price, args.oil_inventory, args.oil_supply, args.natgas]):
        args.all = True

    modules = []
    data = {}

    if args.all or args.oil_price:
        modules.append("oil_prices")
        print("📊 采集原油价格...", file=sys.stderr)
        data["oil_prices"] = fetch_oil_prices(args.days)

    if args.all or args.oil_inventory:
        modules.append("oil_inventory")
        print("📊 采集原油库存...", file=sys.stderr)
        data["oil_inventory"] = fetch_oil_inventory(args.weeks)

    if args.all or args.oil_supply:
        modules.append("oil_supply")
        print("📊 采集原油供需...", file=sys.stderr)
        data["oil_supply"] = fetch_oil_supply()

    if args.all or args.natgas:
        modules.append("natgas")
        print("📊 采集天然气数据...", file=sys.stderr)
        data["natgas"] = fetch_natgas(args.days, args.weeks)

    if args.json:
        output = json.dumps(data, ensure_ascii=False, indent=2)
    else:
        output = format_md(data, modules)

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"✅ 已保存至 {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
