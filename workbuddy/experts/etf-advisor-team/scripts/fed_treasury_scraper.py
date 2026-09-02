# -*- coding: utf-8 -*-
"""
Fed Treasury Scraper — 美联储官方数据采集

数据源:
  1. Federal Reserve H.15 CSV API — 美国国债收益率曲线
  2. Federal Reserve RSS Feeds — 货币政策决议/声明
  3. FRED-style endpoints — 联邦基金利率

功能模块:
  1. 美国国债收益率曲线 (1M~30Y全期限)
  2. 美联储货币政策声明/会议纪要
  3. 联邦基金利率

用法:
  python fed_treasury_scraper.py --all                # 全部模块
  python fed_treasury_scraper.py --yields             # 国债收益率曲线
  python fed_treasury_scraper.py --policy             # 货币政策动态
  python fed_treasury_scraper.py --ffr                # 联邦基金利率
  python fed_treasury_scraper.py --all --output FinancialData/fed_data.md
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
import csv
import io
import json
import re
import sys
import xml.etree.ElementTree as ET
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

TIMEOUT = 20
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "*/*",
}

# H.15 收益率 series IDs
# https://www.federalreserve.gov/datadownload/Choose.aspx?rel=H15
YIELD_SERIES = {
    "1M": "RIFLGFCM01_N.B",
    "3M": "RIFLGFCM03_N.B",
    "6M": "RIFLGFCM06_N.B",
    "1Y": "RIFLGFCY01_N.B",
    "2Y": "RIFLGFCY02_N.B",
    "3Y": "RIFLGFCY03_N.B",
    "5Y": "RIFLGFCY05_N.B",
    "7Y": "RIFLGFCY07_N.B",
    "10Y": "RIFLGFCY10_N.B",
    "20Y": "RIFLGFCY20_N.B",
    "30Y": "RIFLGFCY30_N.B",
}

# 联邦基金利率 series
FFR_SERIES = "RIFSPFF_N.B"

# ============================================================
# Module 1: 美国国债收益率曲线
# ============================================================

def fetch_treasury_yields(obs=10):
    """从美联储H.15下载国债收益率（CSV格式）"""
    # 使用预计算的 series hash（包含1M~30Y全部CMT收益率）
    series_hash = "bf17364827e38702b42a58cf8eaa3f78"
    url = (
        f"https://www.federalreserve.gov/datadownload/Output.aspx"
        f"?rel=H15&series={series_hash}&lastobs={obs}"
        f"&from=&to=&filetype=csv&label=include&layout=seriescolumn"
    )
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        text = resp.text
    except Exception as e:
        print(f"  ⚠️ H.15收益率请求失败: {e}", file=sys.stderr)
        return None

    # 解析CSV: 前几行是header, 然后是Time Period + 各期限列
    lines = text.strip().split("\n")

    # 找到 "Time Period" 开头的行
    header_idx = None
    for i, line in enumerate(lines):
        if line.startswith('"Time Period"') or line.startswith("Time Period"):
            header_idx = i
            break

    if header_idx is None:
        print("  ⚠️ 无法解析H.15 CSV格式", file=sys.stderr)
        return None

    # 解析header行获取列名
    reader = csv.reader(io.StringIO("\n".join(lines[header_idx:])))
    headers = next(reader)

    # 映射列号到期限名
    col_map = {}
    for col_idx, col_name in enumerate(headers):
        for tenor, series_id in YIELD_SERIES.items():
            if series_id in col_name:
                col_map[col_idx] = tenor
                break

    # 解析数据行
    results = []
    for row in reader:
        if not row or not row[0].strip():
            continue
        date_str = row[0].strip().strip('"')
        entry = {"date": date_str}
        for col_idx, tenor in col_map.items():
            val = row[col_idx].strip().strip('"') if col_idx < len(row) else "ND"
            try:
                entry[tenor] = float(val)
            except (ValueError, TypeError):
                entry[tenor] = None
        results.append(entry)

    return results

# ============================================================
# Module 2: 联邦基金利率
# ============================================================

def fetch_fed_funds_rate(obs=20):
    """获取联邦基金有效利率"""
    # FFR series hash
    ffr_hash = "bcb44e57fb57efbe90002369321bfb3f"
    url = (
        f"https://www.federalreserve.gov/datadownload/Output.aspx"
        f"?rel=H15&series={ffr_hash}&lastobs={obs}"
        f"&from=&to=&filetype=csv&label=include&layout=seriescolumn"
    )
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        text = resp.text
    except Exception as e:
        print(f"  ⚠️ 联邦基金利率请求失败: {e}", file=sys.stderr)
        return None

    lines = text.strip().split("\n")
    header_idx = None
    for i, line in enumerate(lines):
        if line.startswith('"Time Period"') or line.startswith("Time Period"):
            header_idx = i
            break

    if header_idx is None:
        return None

    reader = csv.reader(io.StringIO("\n".join(lines[header_idx:])))
    next(reader)  # skip header
    results = []
    for row in reader:
        if not row or not row[0].strip():
            continue
        date_str = row[0].strip().strip('"')
        val = row[1].strip().strip('"') if len(row) > 1 else "ND"
        try:
            results.append({"date": date_str, "ffr": float(val)})
        except ValueError:
            results.append({"date": date_str, "ffr": None})

    return results

# ============================================================
# Module 3: 货币政策声明 (RSS)
# ============================================================

def fetch_monetary_policy():
    """从美联储RSS获取最新货币政策声明/新闻"""
    url = "https://www.federalreserve.gov/feeds/press_monetary.xml"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
    except Exception as e:
        print(f"  ⚠️ 货币政策RSS请求失败: {e}", file=sys.stderr)
        return None

    items = []
    for item in root.findall(".//item")[:10]:
        title = item.findtext("title", "").strip()
        link = item.findtext("link", "").strip()
        pub_date = item.findtext("pubDate", "").strip()
        desc = item.findtext("description", "").strip()
        # 清理HTML标签
        desc = re.sub(r"<[^>]+>", "", desc).strip()
        if title:
            items.append({
                "title": title,
                "date": pub_date,
                "link": link,
                "summary": desc[:200] if desc else "",
            })

    return items

# ============================================================
# Formatters
# ============================================================

def format_md(data):
    """格式化为Markdown"""
    lines = [
        "# 美联储官方数据",
        f"\n> 数据来源：美联储官网(federalreserve.gov) | 采集时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        ""
    ]

    if "yields" in data and data["yields"]:
        lines.append("## 美国国债收益率曲线")
        lines.append("")
        tenors = list(YIELD_SERIES.keys())
        header = "| 日期 | " + " | ".join(tenors) + " |"
        sep = "|------|" + "|".join(["------"] * len(tenors)) + "|"
        lines.append(header)
        lines.append(sep)
        for entry in data["yields"]:
            vals = []
            for t in tenors:
                v = entry.get(t)
                vals.append(f"{v:.2f}%" if v is not None else "ND")
            lines.append(f"| {entry['date']} | " + " | ".join(vals) + " |")
        lines.append("")

        # 最新曲线解读
        if data["yields"]:
            latest = data["yields"][-1]
            y2 = latest.get("2Y")
            y10 = latest.get("10Y")
            if y2 is not None and y10 is not None:
                spread = round(y10 - y2, 2)
                inv = "**倒挂**" if spread < 0 else "正常"
                lines.append(f"**2Y-10Y利差**: {spread}% ({inv})")
                lines.append("")

    if "ffr" in data and data["ffr"]:
        lines.append("## 联邦基金有效利率")
        lines.append("")
        latest = data["ffr"][0]
        lines.append(f"**最新: {latest['ffr']}%**（{latest['date']}）")
        lines.append("")
        lines.append("| 日期 | 利率(%) |")
        lines.append("|------|--------|")
        for r in data["ffr"][:15]:
            val = f"{r['ffr']:.2f}" if r['ffr'] is not None else "ND"
            lines.append(f"| {r['date']} | {val} |")
        lines.append("")

    if "policy" in data and data["policy"]:
        lines.append("## 美联储货币政策动态")
        lines.append(f"📎 **信源API**: `https://www.federalreserve.gov/feeds/press_monetary.xml`")
        lines.append("")
        for item in data["policy"]:
            lines.append(f"### {item['title']}")
            lines.append(f"- **发布日期**: {item['date']}")
            if item['summary']:
                lines.append(f"- **摘要**: {item['summary']}")
            if item['link']:
                lines.append(f"- **链接**: {item['link']}")
            lines.append("")

    return "\n".join(lines)

# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="美联储官方数据采集 — 国债收益率/货币政策/联邦基金利率")
    parser.add_argument("--all", action="store_true", help="采集全部模块")
    parser.add_argument("--yields", action="store_true", help="国债收益率曲线")
    parser.add_argument("--policy", action="store_true", help="货币政策声明")
    parser.add_argument("--ffr", action="store_true", help="联邦基金利率")
    parser.add_argument("--obs", type=int, default=10, help="数据观测期数（默认10）")
    parser.add_argument("--json", action="store_true", help="JSON格式输出")
    parser.add_argument("--output", type=str, help="输出文件路径")
    args = parser.parse_args()

    if not any([args.all, args.yields, args.policy, args.ffr]):
        args.all = True

    data = {}

    if args.all or args.yields:
        print("📊 采集国债收益率...", file=sys.stderr)
        data["yields"] = fetch_treasury_yields(args.obs)

    if args.all or args.ffr:
        print("📊 采集联邦基金利率...", file=sys.stderr)
        data["ffr"] = fetch_fed_funds_rate(args.obs)

    if args.all or args.policy:
        print("📊 采集货币政策动态...", file=sys.stderr)
        data["policy"] = fetch_monetary_policy()

    if args.json:
        output = json.dumps(data, ensure_ascii=False, indent=2)
    else:
        output = format_md(data)

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"✅ 已保存至 {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
