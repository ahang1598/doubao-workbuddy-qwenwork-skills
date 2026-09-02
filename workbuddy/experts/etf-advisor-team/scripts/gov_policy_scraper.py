# -*- coding: utf-8 -*-
"""
Gov Policy Scraper — 政府部委政策新闻汇总采集

数据源:
  - 国家统计局 (stats.gov.cn)
  - 国家发改委 (ndrc.gov.cn)
  - 财政部 (mof.gov.cn)
  - 工信部 (miit.gov.cn)
  - 国家能源局 (nea.gov.cn)

功能模块:
  1. 统计局最新数据发布
  2. 发改委政策动态
  3. 财政部财政数据
  4. 工信部产业政策
  5. 能源局能源数据

用法:
  python gov_policy_scraper.py --all                   # 全部部委
  python gov_policy_scraper.py --stats                 # 仅统计局
  python gov_policy_scraper.py --ndrc                  # 仅发改委
  python gov_policy_scraper.py --mof                   # 仅财政部
  python gov_policy_scraper.py --miit                  # 仅工信部
  python gov_policy_scraper.py --nea                   # 仅能源局
  python gov_policy_scraper.py --all --output FinancialData/gov_policy.md
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
# HTML Parsing Helpers
# ============================================================

def extract_news_list(html, base_url, max_items=15):
    """通用政府网站新闻列表提取"""
    results = []

    # 尝试多种常见的列表模式
    # Pattern 1: <li><a href="..." title="...">text</a><span>date</span></li>
    patterns = [
        # 带title属性的链接 + 日期span
        re.compile(
            r'<a[^>]+href="([^"]*)"[^>]*title="([^"]*)"[^>]*>.*?</a>'
            r'[\s\S]*?(\d{4}[-/]\d{2}[-/]\d{2})',
            re.DOTALL
        ),
        # 链接文本 + 日期
        re.compile(
            r'<a[^>]+href="([^"]*)"[^>]*>((?:(?!<a).)*?)</a>'
            r'[\s\S]*?(\d{4}[-/]\d{2}[-/]\d{2})',
            re.DOTALL
        ),
    ]

    for pattern in patterns:
        for m in pattern.finditer(html):
            href, title, date = m.groups()
            title = re.sub(r'<[^>]+>', '', title).strip()
            if not title or len(title) < 6:
                continue
            if href and not href.startswith("http"):
                if href.startswith("/"):
                    href = base_url + href
                else:
                    href = base_url + "/" + href
            date = date.replace("/", "-")
            results.append({"title": title[:100], "url": href, "date": date})

        if results:
            break  # 第一个pattern有结果就停

    # 去重
    seen = set()
    unique = []
    for r in results:
        key = r["title"][:20]
        if key not in seen:
            seen.add(key)
            unique.append(r)

    return unique[:max_items]

def fetch_page(url, encoding="utf-8"):
    """获取页面HTML"""
    try:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        except requests.exceptions.SSLError:
            print("WARN: SSL 证书校验失败，降级为跳过校验（仅用于公开数据采集）", file=sys.stderr)
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT, verify=False)
        resp.encoding = encoding
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"  ⚠️ 请求失败 [{url}]: {e}", file=sys.stderr)
        return None

# ============================================================
# Module 1: 国家统计局
# ============================================================

def fetch_stats_data():
    """国家统计局 — 最新数据发布、新闻"""
    results = []

    # 最新发布
    urls = [
        ("https://www.stats.gov.cn/sj/zxfb/", "最新发布"),
        ("https://www.stats.gov.cn/sj/sjjd/", "数据解读"),
    ]

    for url, section in urls:
        html = fetch_page(url)
        if not html:
            continue
        items = extract_news_list(html, "https://www.stats.gov.cn")
        for item in items[:8]:
            item["section"] = section
            results.append(item)

    return results[:15]

# ============================================================
# Module 2: 国家发改委
# ============================================================

def fetch_ndrc_policy():
    """发改委 — 政策发布与解读"""
    results = []

    urls = [
        ("https://www.ndrc.gov.cn/xxgk/zcfb/", "政策发布"),
        ("https://www.ndrc.gov.cn/xwdt/xwfb/", "新闻发布"),
    ]

    for url, section in urls:
        html = fetch_page(url)
        if not html:
            continue
        items = extract_news_list(html, "https://www.ndrc.gov.cn")
        for item in items[:8]:
            item["section"] = section
            results.append(item)

    return results[:15]

# ============================================================
# Module 3: 财政部
# ============================================================

def fetch_mof_data():
    """财政部 — 财政数据与政策"""
    results = []

    urls = [
        ("https://www.mof.gov.cn/zhengwuxinxi/caizhengxinwen/", "财政新闻"),
        ("https://www.mof.gov.cn/zhengwuxinxi/zhengcefabu/", "政策发布"),
    ]

    for url, section in urls:
        html = fetch_page(url)
        if not html:
            continue
        items = extract_news_list(html, "https://www.mof.gov.cn")
        for item in items[:8]:
            item["section"] = section
            results.append(item)

    return results[:15]

# ============================================================
# Module 4: 工信部
# ============================================================

def fetch_miit_policy():
    """工信部 — 产业政策与数据"""
    results = []

    urls = [
        ("https://www.miit.gov.cn/xwdt/gxdt/ldhd/index.html", "工信要闻"),
        ("https://www.miit.gov.cn/zwgk/zcwj/wjfb/index.html", "政策文件"),
    ]

    for url, section in urls:
        html = fetch_page(url)
        if not html:
            continue
        items = extract_news_list(html, "https://www.miit.gov.cn")
        for item in items[:8]:
            item["section"] = section
            results.append(item)

    return results[:15]

# ============================================================
# Module 5: 国家能源局
# ============================================================

def fetch_nea_data():
    """能源局 — 能源数据与政策"""
    results = []

    urls = [
        ("https://www.nea.gov.cn/sjzz/index.htm", "数据信息"),
        ("https://www.nea.gov.cn/xwzx/index.htm", "新闻中心"),
    ]

    for url, section in urls:
        html = fetch_page(url)
        if not html:
            continue
        items = extract_news_list(html, "https://www.nea.gov.cn")
        for item in items[:8]:
            item["section"] = section
            results.append(item)

    return results[:15]

# ============================================================
# Formatters
# ============================================================

def format_md(data):
    """格式化为Markdown"""
    lines = [
        "# 政府部委政策与数据动态",
        f"\n> 采集时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"> 📎 信源URL：统计局 `stats.gov.cn/sj/zxfb/` | 发改委 `ndrc.gov.cn/xxgk/zcfb/` | 财政部 `mof.gov.cn/zhengwuxinxi/` | 工信部 `miit.gov.cn/xwdt/` | 能源局 `nea.gov.cn/sjzz/`",
        ""
    ]

    source_map = {
        "stats": ("国家统计局", "stats.gov.cn"),
        "ndrc": ("国家发改委", "ndrc.gov.cn"),
        "mof": ("财政部", "mof.gov.cn"),
        "miit": ("工信部", "miit.gov.cn"),
        "nea": ("国家能源局", "nea.gov.cn"),
    }

    for key, (name, domain) in source_map.items():
        items = data.get(key)
        if not items:
            continue

        lines.append(f"## {name}")
        lines.append(f"> 来源：{domain}")
        lines.append("")

        # 按section分组
        sections = {}
        for item in items:
            sec = item.get("section", "其他")
            if sec not in sections:
                sections[sec] = []
            sections[sec].append(item)

        for sec, sec_items in sections.items():
            lines.append(f"### {sec}")
            lines.append("")
            lines.append("| 序号 | 标题 | 日期 |")
            lines.append("|------|------|------|")
            for i, item in enumerate(sec_items, 1):
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
    parser = argparse.ArgumentParser(description="政府部委政策新闻汇总采集")
    parser.add_argument("--all", action="store_true", help="采集全部部委")
    parser.add_argument("--stats", action="store_true", help="国家统计局")
    parser.add_argument("--ndrc", action="store_true", help="发改委")
    parser.add_argument("--mof", action="store_true", help="财政部")
    parser.add_argument("--miit", action="store_true", help="工信部")
    parser.add_argument("--nea", action="store_true", help="国家能源局")
    parser.add_argument("--json", action="store_true", help="JSON格式输出")
    parser.add_argument("--output", type=str, help="输出文件路径")
    args = parser.parse_args()

    if not any([args.all, args.stats, args.ndrc, args.mof, args.miit, args.nea]):
        args.all = True

    data = {}

    if args.all or args.stats:
        print("📊 采集国家统计局...", file=sys.stderr)
        data["stats"] = fetch_stats_data()

    if args.all or args.ndrc:
        print("📊 采集发改委...", file=sys.stderr)
        data["ndrc"] = fetch_ndrc_policy()

    if args.all or args.mof:
        print("📊 采集财政部...", file=sys.stderr)
        data["mof"] = fetch_mof_data()

    if args.all or args.miit:
        print("📊 采集工信部...", file=sys.stderr)
        data["miit"] = fetch_miit_policy()

    if args.all or args.nea:
        print("📊 采集能源局...", file=sys.stderr)
        data["nea"] = fetch_nea_data()

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
