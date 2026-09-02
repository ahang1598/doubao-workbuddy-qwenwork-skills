# -*- coding: utf-8 -*-
"""
China Property & Infrastructure Scraper — 中国地产 + 基建高频数据

数据源:
  1. 国家统计局 — 70 大中城市房价指数（已被 macro_data_scraper 部分覆盖，本脚本补充）
  2. 中指院 / 克而瑞 — 30 大中城市商品房成交（需 web_fetch 兜底）
  3. 东方财富 datacenter — 房地产销售 / 投资 / 新开工 / 竣工高频数据
  4. 财政部 — 专项债发行进度
  5. 水泥 / 沥青 / 螺纹钢期现货 — 基建链条景气度（东财商品板块）

功能模块:
  1. 70 城房价指数（一线 / 二线 / 三线）
  2. 房地产投资 / 新开工 / 竣工同比（统计局月度）
  3. 30 大中城市商品房成交（高频代理 — 通过 wind / 国家统计局）
  4. 专项债发行进度（财政部公开数据）
  5. 基建链条商品（水泥 / 沥青 / 螺纹钢）
  6. 综合：大财政 + REITs 主题包触发判断

用法:
  python china_property_scraper.py --all
  python china_property_scraper.py --house-price
  python china_property_scraper.py --investment
  python china_property_scraper.py --infrastructure
  python china_property_scraper.py --all --output FinancialData/china_property.md
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
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: requests is required.", file=sys.stderr)
    sys.exit(1)


TIMEOUT = 20
HEADERS = {
    "User-Agent": "Mozilla/5.0 AppleWebKit/537.36",
    "Referer": "https://data.eastmoney.com/",
    "Accept": "application/json, text/plain, */*",
}

# 东财 datacenter 房地产专题接口
# 房地产开发投资完成额
EM_PROP_INVEST_URL = ("https://datacenter-web.eastmoney.com/api/data/v1/get?"
                      "sortColumns=REPORT_DATE&sortTypes=-1&pageSize=24&pageNumber=1&"
                      "reportName=RPT_ECONOMY_FIDEDIVE&columns=ALL")

# 70 大中城市房价指数
EM_HOUSE_PRICE_URL = ("https://datacenter-web.eastmoney.com/api/data/v1/get?"
                      "sortColumns=REPORT_DATE&sortTypes=-1&pageSize=12&pageNumber=1&"
                      "reportName=RPT_ECONOMY_HOUSE_PRICE&columns=ALL")

# 商品房销售面积/金额
EM_PROP_SALES_URL = ("https://datacenter-web.eastmoney.com/api/data/v1/get?"
                     "sortColumns=REPORT_DATE&sortTypes=-1&pageSize=24&pageNumber=1&"
                     "reportName=RPT_ECONOMY_FIDESALE&columns=ALL")

# 基建链条品种（东财商品板块按品种 push2）
INFRA_COMMODITIES = {
    "rb2510": "螺纹钢主连",
    "i2509": "铁矿石主连",
    "FG2509": "玻璃主连",
    "TA2509": "PTA 主连",
    "MA2509": "甲醇主连",
}

# 专项债 - 财政部 / Wind 通常需 web_fetch
SPECIAL_BOND_INFO = {
    "official_url": "https://www.mof.gov.cn/zhengwuxinxi/caizhengshuju/",
    "alt_search": "新增专项债发行进度 {YYYY} 财政部",
    "key_signal": "全年新增专项债限额完成度 >70% = 财政发力前置；<40% = 后置预期",
}


def _http_get(url, timeout=TIMEOUT):
    return requests.get(url, headers=HEADERS, timeout=timeout)


def _safe_json(url):
    try:
        r = _http_get(url)
        r.raise_for_status()
        data = r.json()
        return data.get("result", {}).get("data", []) if isinstance(data, dict) else []
    except Exception as exc:
        print(f"⚠️ {url[:60]}: {exc}", file=sys.stderr)
        return []


def fetch_house_price():
    """70 大中城市新建商品住宅价格指数。"""
    rows = _safe_json(EM_HOUSE_PRICE_URL)
    if not rows:
        return None

    # 通常字段：REPORT_DATE / 一线/二线/三线 同环比
    latest = rows[0] if rows else {}
    return {
        "latest_date": str(latest.get("REPORT_DATE", "")).split(" ")[0],
        "data_rows": rows[:12],  # 近 12 月
        "interpretation": ("一线房价同比 +5% 持续 = 地产链景气拐点；"
                          "全国同比连续 -5% 以上 = 政策刺激预期升温"),
    }


def fetch_property_investment():
    """房地产开发投资 + 新开工 + 竣工。"""
    rows = _safe_json(EM_PROP_INVEST_URL)
    if not rows:
        return None
    return {
        "latest_date": str(rows[0].get("REPORT_DATE", "")).split(" ")[0],
        "recent_data": rows[:12],
        "interpretation": ("开发投资同比 -10% 以下 = 行业出清深化；转正 = 拐点确认；"
                          "新开工连续 3 月环比 + → 后续 6-12 月施工链景气改善"),
    }


def fetch_property_sales():
    """商品房销售面积/金额。"""
    rows = _safe_json(EM_PROP_SALES_URL)
    if not rows:
        return None
    return {
        "latest_date": str(rows[0].get("REPORT_DATE", "")).split(" ")[0],
        "recent_data": rows[:12],
        "interpretation": ("销售同比 +5% 持续 = 销售拐点确认；"
                          "克而瑞 30 大城市周度成交是更高频领先指标，建议 web_fetch 补充"),
    }


def fetch_infra_commodities():
    """基建链条商品 — 螺纹/铁矿/水泥相关。"""
    results = []
    for code, name in INFRA_COMMODITIES.items():
        # 东财 push2 商品行情
        url = f"https://push2.eastmoney.com/api/qt/stock/get?secid=113.{code}&fields=f43,f44,f45,f46,f47,f60,f170"
        try:
            r = _http_get(url)
            r.raise_for_status()
            d = r.json().get("data", {}) if isinstance(r.json(), dict) else {}
            if d:
                results.append({
                    "code": code,
                    "name": name,
                    "latest": d.get("f43"),
                    "change_pct": d.get("f170"),
                    "high": d.get("f44"),
                    "low": d.get("f45"),
                    "volume": d.get("f47"),
                })
        except Exception:
            continue
    return results if results else None


def fetch_special_bond():
    """专项债发行进度 — 元数据/抓取建议。"""
    return SPECIAL_BOND_INFO


def to_markdown(house_price, investment, sales, infra, special_bond):
    lines = []
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines.append("# 中国地产 + 基建高频数据\n")
    lines.append(f"**数据采集时间**: {ts}")
    lines.append("📎 **信源API**: 东财 datacenter 房地产 RPT API + push2 期货行情 API + 财政部公开数据\n")
    lines.append("---\n")

    # 1. 房价
    lines.append("## 1. 70 大中城市房价指数\n")
    if house_price:
        lines.append(f"- **最新报告期**: {house_price['latest_date']}")
        rows = house_price.get("data_rows", [])
        if rows:
            # 取关键字段（具体字段以接口返回为准，做兼容显示）
            lines.append("| 月份 | 关键指标 |")
            lines.append("|------|---------|")
            for row in rows[:6]:
                date = str(row.get("REPORT_DATE", "")).split(" ")[0]
                # 显示前 3 个非 ID 字段
                kvs = [f"{k}={v}" for k, v in row.items()
                       if k not in ("REPORT_DATE",) and v is not None][:5]
                lines.append(f"| {date} | {' / '.join(kvs)} |")
        lines.append(f"\n> {house_price['interpretation']}\n")
    else:
        lines.append("⚠️ 房价数据获取失败，建议 web_fetch 国家统计局月度数据\n")

    # 2. 房地产投资
    lines.append("## 2. 房地产开发投资 / 新开工 / 竣工\n")
    if investment:
        lines.append(f"- **最新报告期**: {investment['latest_date']}")
        rows = investment.get("recent_data", [])
        if rows:
            lines.append("| 月份 | 关键指标（投资/新开工/施工/竣工 同比%） |")
            lines.append("|------|----------------------------------------|")
            for row in rows[:6]:
                date = str(row.get("REPORT_DATE", "")).split(" ")[0]
                kvs = [f"{k}={v}" for k, v in row.items()
                       if k not in ("REPORT_DATE",) and v is not None][:5]
                lines.append(f"| {date} | {' / '.join(kvs)} |")
        lines.append(f"\n> {investment['interpretation']}\n")
    else:
        lines.append("⚠️ 投资数据获取失败\n")

    # 3. 商品房销售
    lines.append("## 3. 商品房销售面积 / 金额（高频代理）\n")
    if sales:
        lines.append(f"- **最新报告期**: {sales['latest_date']}")
        lines.append(f"\n> {sales['interpretation']}\n")
        lines.append("**高频补充建议**：")
        lines.append("- `web_fetch('https://industry.cric.cn/', '提取 30 大中城市商品房周度成交')` — 克而瑞")
        lines.append("- `web_search '30大中城市商品房成交面积 周度 {YYYY-MM}'`")
        lines.append("")
    else:
        lines.append("⚠️ 销售数据获取失败\n")

    # 4. 基建链条
    lines.append("## 4. 基建链条商品（螺纹钢 / 铁矿 / 水泥相关）\n")
    if infra:
        lines.append("| 品种 | 最新价 | 涨跌幅 | 最高 | 最低 |")
        lines.append("|------|-------|--------|------|------|")
        for x in infra:
            lines.append(
                f"| {x['name']} ({x['code']}) | {x['latest']} | "
                f"{x.get('change_pct', '—')}% | {x.get('high', '—')} | {x.get('low', '—')} |"
            )
        lines.append("\n**研判口径**：")
        lines.append("- **螺纹钢**：基建 + 地产新开工核心原料，价格走势 = 实物工作量晴雨表")
        lines.append("- **沥青 / 玻璃**：基建（沥青）+ 地产竣工（玻璃）链条")
        lines.append("- 螺纹 + 铁矿同步上行 = 实物量回升；分化 = 库存因素扰动")
        lines.append("")
    else:
        lines.append("⚠️ 期货行情获取失败（非交易时段会返回空）\n")

    # 5. 专项债
    lines.append("## 5. 专项债发行进度 — 大财政主题入口指标\n")
    lines.append(f"- **官方数据源**: {special_bond['official_url']}")
    lines.append(f"- **关键信号**: {special_bond['key_signal']}")
    lines.append(f"- **抓取建议**: `web_search '{special_bond['alt_search']}'`")
    lines.append("")

    # 6. 综合判断
    lines.append("## 6. 综合研判 — 大财政 + REITs 主题包触发判断\n")
    lines.append("| 维度 | 大财政受益方向触发条件 | 当前观察 |")
    lines.append("|------|---------------------|---------|")
    lines.append("| 专项债发行进度 | 上半年 > 60% 限额 = 前置发力 | 见上节 |")
    lines.append("| 螺纹钢/铁矿 | 30 日均价突破年线 + 成交放大 | 见第 4 节 |")
    lines.append("| 70 城房价同比 | 一线企稳回升 = 地产链拐点 | 见第 1 节 |")
    lines.append("| 商品房销售 | 30 大城市周度成交 +20% 持续 | web_fetch 克而瑞兜底 |")
    lines.append("| 新开工 | 同比转正 + 连续 2 月环比+ | 见第 2 节 |")
    lines.append("\n**3+ 维触发 → 大财政主题包配置（建材/工程机械/REITs）权重提升至 15%+**\n")

    lines.append("---\n")
    lines.append("## 数据信源\n")
    lines.append("- **东财 datacenter RPT_ECONOMY_HOUSE_PRICE / FIDEDIVE / FIDESALE** — 国家统计局数据镜像")
    lines.append("- **东财 push2 期货行情** — 上海期货交易所 / 大连商品交易所")
    lines.append("- **财政部财政数据** — https://www.mof.gov.cn/zhengwuxinxi/caizhengshuju/")
    lines.append("- **克而瑞 / 中指院** — 30 大中城市周度商品房成交（web_fetch / web_search 兜底）")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="中国地产 + 基建高频采集")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--house-price", action="store_true")
    parser.add_argument("--investment", action="store_true")
    parser.add_argument("--sales", action="store_true")
    parser.add_argument("--infrastructure", action="store_true")
    parser.add_argument("--bond", action="store_true")
    parser.add_argument("--output", help="Markdown 输出路径")
    parser.add_argument("--json", help="JSON 数据输出")
    args = parser.parse_args()

    if not any([args.all, args.house_price, args.investment, args.sales,
                args.infrastructure, args.bond]):
        parser.print_help()
        return 1

    house_price = fetch_house_price() if (args.all or args.house_price) else None
    investment = fetch_property_investment() if (args.all or args.investment) else None
    sales = fetch_property_sales() if (args.all or args.sales) else None
    infra = fetch_infra_commodities() if (args.all or args.infrastructure) else None
    special_bond = fetch_special_bond() if (args.all or args.bond) else SPECIAL_BOND_INFO

    md = to_markdown(house_price, investment, sales, infra, special_bond)

    if args.output:
        out_path = Path(args.output).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(md, encoding="utf-8")
        print(f"✅ 输出: {out_path}")
    else:
        print(md)

    if args.json:
        json_path = Path(args.json).resolve()
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps({
            "house_price": house_price, "investment": investment, "sales": sales,
            "infrastructure": infra, "special_bond": special_bond,
            "collected_at": datetime.now().isoformat(),
        }, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        print(f"✅ JSON: {json_path}")

    if not any([house_price, investment, sales, infra]):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
