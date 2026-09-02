# -*- coding: utf-8 -*-
"""
PBC Policy Scraper — 中国人民银行官方数据采集

数据源: 中国人民银行官网 (https://www.pbc.gov.cn/)

功能模块:
  1. 公开市场操作（逆回购/MLF/SLF投放回笼）
  2. 货币政策动态（最新政策声明/报告）
  3. 统计数据发布（M2/社融/信贷等最新发布动态）

用法:
  python pbc_policy_scraper.py --all                  # 全部模块
  python pbc_policy_scraper.py --omo                  # 公开市场操作
  python pbc_policy_scraper.py --policy               # 货币政策动态
  python pbc_policy_scraper.py --stats                # 统计数据动态
  python pbc_policy_scraper.py --all --output FinancialData/pbc_data.md
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
import re
import sys
from datetime import datetime
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
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

# ============================================================
# HTML Parsing Helpers (无需bs4)
# ============================================================

def extract_links(html, base_url="https://www.pbc.gov.cn"):
    """从HTML提取标题+链接+日期列表"""
    # 匹配央行网站常见的列表项模式
    results = []
    # Pattern 1: <a href="..." title="...">...</a> ... <span>date</span>
    pattern = re.compile(
        r'<a[^>]+href="([^"]*)"[^>]*(?:title="([^"]*)")?[^>]*>(.*?)</a>'
        r'.*?(?:<span[^>]*>(\d{4}-\d{2}-\d{2})</span>)?',
        re.DOTALL
    )
    for m in pattern.finditer(html):
        href, title, text, date = m.groups()
        text = re.sub(r'<[^>]+>', '', text).strip()
        title = title or text
        if not title or len(title) < 4:
            continue
        if href and not href.startswith("http"):
            href = base_url + href
        results.append({
            "title": title[:120],
            "url": href,
            "date": date or "",
        })
    return results

def extract_text_content(html):
    """提取页面纯文本内容"""
    # 移除script/style
    html = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html, flags=re.DOTALL | re.IGNORECASE)
    # 移除HTML标签
    text = re.sub(r'<[^>]+>', ' ', html)
    # 合并空白
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# ============================================================
# Module 1: 公开市场操作
# ============================================================

def fetch_omo():
    """获取公开市场操作（逆回购/MLF投放回笼）"""
    url = "https://www.pbc.gov.cn/zhengcehuobisi/125207/125213/125431/index.html"
    try:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        except requests.exceptions.SSLError:
            print("WARN: SSL 证书校验失败，降级为跳过校验（仅用于公开数据采集）", file=sys.stderr)
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT, verify=False)
        resp.encoding = "utf-8"
        resp.raise_for_status()
        html = resp.text
    except Exception as e:
        print(f"  ⚠️ 央行公开市场操作请求失败: {e}", file=sys.stderr)
        return None

    # 提取公开市场操作公告列表
    items = extract_links(html)

    # 过滤出公开市场操作相关
    omo_items = []
    keywords = ["逆回购", "公开市场", "MLF", "SLF", "PSL", "再贷款", "再贴现", "国库现金"]
    for item in items:
        if any(kw in item["title"] for kw in keywords) or "公开市场" in item["url"]:
            omo_items.append(item)

    # 如果关键词过滤后为空，返回所有（该页本身就是公开市场操作页）
    if not omo_items:
        omo_items = items[:15]

    return omo_items[:15]

# ============================================================
# Module 2: 货币政策动态
# ============================================================

def fetch_monetary_policy():
    """获取货币政策相关动态"""
    results = []

    # 货币政策司-政策解读
    urls = [
        ("https://www.pbc.gov.cn/zhengcehuobisi/125207/125213/index.html", "货币政策司"),
        ("https://www.pbc.gov.cn/goutongjiaoliu/113456/113469/index.html", "新闻发布会"),
    ]

    for url, source in urls:
        try:
            try:
                resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            except requests.exceptions.SSLError:
                print("WARN: SSL 证书校验失败，降级为跳过校验（仅用于公开数据采集）", file=sys.stderr)
                resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT, verify=False)
            resp.encoding = "utf-8"
            resp.raise_for_status()
            items = extract_links(resp.text)
            for item in items[:10]:
                item["source"] = source
                results.append(item)
        except Exception as e:
            print(f"  ⚠️ 央行{source}请求失败: {e}", file=sys.stderr)

    # 去重
    seen = set()
    unique = []
    for item in results:
        key = item["title"][:30]
        if key not in seen:
            seen.add(key)
            unique.append(item)

    return unique[:15]

# ============================================================
# Module 3: 统计数据发布动态
# ============================================================

def fetch_stats_releases():
    """获取统计数据发布动态（M2/社融/信贷等）"""
    url = "https://www.pbc.gov.cn/diaochatongjisi/116219/116319/index.html"
    try:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        except requests.exceptions.SSLError:
            print("WARN: SSL 证书校验失败，降级为跳过校验（仅用于公开数据采集）", file=sys.stderr)
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT, verify=False)
        resp.encoding = "utf-8"
        resp.raise_for_status()
        html = resp.text
    except Exception as e:
        print(f"  ⚠️ 央行统计数据请求失败: {e}", file=sys.stderr)
        return None

    items = extract_links(html)

    # 过滤统计数据相关
    stats_keywords = ["统计", "社会融资", "货币", "金融", "信贷", "M2", "存款", "贷款", "外汇储备", "储备"]
    stats_items = []
    for item in items:
        if any(kw in item["title"] for kw in stats_keywords):
            stats_items.append(item)

    if not stats_items:
        stats_items = items[:15]

    return stats_items[:15]

# ============================================================
# Formatters
# ============================================================

def format_md(data):
    """格式化为Markdown"""
    lines = [
        "# 中国人民银行官方数据",
        f"\n> 数据来源：中国人民银行(pbc.gov.cn) | 采集时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"> 📎 信源URL：公开市场操作 `https://www.pbc.gov.cn/zhengcehuobisi/125207/125213/125431/index.html` | 货币政策 `https://www.pbc.gov.cn/zhengcehuobisi/125207/125213/index.html` | 统计数据 `https://www.pbc.gov.cn/diaochatongjisi/116219/116319/index.html`",
        ""
    ]

    if "omo" in data and data["omo"]:
        lines.append("## 公开市场操作")
        lines.append("")
        lines.append("| 序号 | 标题 | 日期 |")
        lines.append("|------|------|------|")
        for i, item in enumerate(data["omo"], 1):
            title = item["title"][:60]
            date = item.get("date", "—")
            url = item.get("url", "")
            if url:
                lines.append(f"| {i} | [{title}]({url}) | {date} |")
            else:
                lines.append(f"| {i} | {title} | {date} |")
        lines.append("")

    if "policy" in data and data["policy"]:
        lines.append("## 货币政策动态")
        lines.append("")
        for item in data["policy"]:
            source = item.get("source", "")
            date = item.get("date", "—")
            lines.append(f"- **[{source}]** {item['title']} ({date})")
            if item.get("url"):
                lines.append(f"  - {item['url']}")
        lines.append("")

    if "stats" in data and data["stats"]:
        lines.append("## 统计数据发布")
        lines.append("")
        lines.append("| 序号 | 标题 | 日期 |")
        lines.append("|------|------|------|")
        for i, item in enumerate(data["stats"], 1):
            title = item["title"][:60]
            date = item.get("date", "—")
            url = item.get("url", "")
            if url:
                lines.append(f"| {i} | [{title}]({url}) | {date} |")
            else:
                lines.append(f"| {i} | {title} | {date} |")
        lines.append("")

    return "\n".join(lines)

# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="中国人民银行官方数据采集 — 公开市场操作/货币政策/统计数据")
    parser.add_argument("--all", action="store_true", help="采集全部模块")
    parser.add_argument("--omo", action="store_true", help="公开市场操作")
    parser.add_argument("--policy", action="store_true", help="货币政策动态")
    parser.add_argument("--stats", action="store_true", help="统计数据发布")
    parser.add_argument("--json", action="store_true", help="JSON格式输出")
    parser.add_argument("--output", type=str, help="输出文件路径")
    args = parser.parse_args()

    if not any([args.all, args.omo, args.policy, args.stats]):
        args.all = True

    data = {}

    if args.all or args.omo:
        print("📊 采集公开市场操作...", file=sys.stderr)
        data["omo"] = fetch_omo()

    if args.all or args.policy:
        print("📊 采集货币政策动态...", file=sys.stderr)
        data["policy"] = fetch_monetary_policy()

    if args.all or args.stats:
        print("📊 采集统计数据发布...", file=sys.stderr)
        data["stats"] = fetch_stats_releases()

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
