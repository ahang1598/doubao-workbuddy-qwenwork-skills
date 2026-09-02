# -*- coding: utf-8 -*-
"""
Metals Scraper — 工业金属与战略矿产价格

数据源:
  1. FRED API — LME 工业金属现货价（铜/铝/锌/镍/锡/铅）+ Stooq 备源
  2. 上海有色网 SMM / 东方财富商品板块 — 国内有色金属现货
  3. 战略矿产：稀土价格指数、锂/钴/镍 / 铀（公开数据 + web_fetch 兜底）

功能模块:
  1. LME 6 大基础金属价格走势（FRED 月度）
  2. 国内有色金属指数（东财商品板块 push2 接口）
  3. 战略矿产专项（稀土 / 锂 / 钴 / 镍 / 铀）
  4. 商品轮动信号判断（贵金属→工业金属切换条件）

用法:
  python metals_scraper.py --all
  python metals_scraper.py --lme
  python metals_scraper.py --domestic
  python metals_scraper.py --strategic
  python metals_scraper.py --all --output FinancialData/metals_market.md
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
import sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: requests is required.", file=sys.stderr)
    sys.exit(1)


TIMEOUT = 25
HEADERS = {
    "User-Agent": "Mozilla/5.0 AppleWebKit/537.36",
    "Referer": "https://quote.eastmoney.com/",
    "Accept": "*/*",
}

FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
STOOQ_CSV = "https://stooq.com/q/d/l/?s={sym}&d1={start}&d2={end}&i=d"

# FRED LBMA / IMF / 国际金属机构数据
LME_SERIES = {
    "PCOPPUSDM":  ("LME 铜现货", "USD/吨", "industrial"),
    "PALUMUSDM":  ("LME 铝现货", "USD/吨", "industrial"),
    "PZINCUSDM":  ("LME 锌现货", "USD/吨", "industrial"),
    "PNICKUSDM":  ("LME 镍现货", "USD/吨", "industrial"),
    "PTINUSDM":   ("LME 锡现货", "USD/吨", "industrial"),
    "PLEADUSDM":  ("LME 铅现货", "USD/吨", "industrial"),
    "PIORECRUSDM": ("中国进口铁矿石", "USD/吨", "industrial"),
}

# Stooq 工业金属期货合约（备源 - 日度）
STOOQ_METALS = {
    "hg.f": ("COMEX 铜期货", "美元/磅"),
    "@nq.f": ("纳指期货", "指数"),  # 占位，实际不用
}

# 东财商品板块 push2 接口（中国相关商品指数）
EM_COMMODITY_URL = ("https://push2.eastmoney.com/api/qt/clist/get?"
                    "fs=m:108+t:13&fields=f12,f14,f2,f3,f17,f15,f16&pn=1&pz=50")

# 战略矿产关键词（用于 web_fetch / web_search 兜底）
STRATEGIC_MINERALS = {
    "rare_earth": {
        "name": "稀土",
        "代表品种": ["氧化镨钕（Pr-Nd Oxide）", "氧化镝", "氧化铽"],
        "数据源": "上海有色网 SMM / 中国稀土行业协会",
        "fetch_url": "https://hq.smm.cn/rare-earth",
        "search": "氧化镨钕 价格 {YYYY-MM} 上海有色网",
        "key_signal": "氧化镨钕 >70 万元/吨 = 强势区；< 40 万元/吨 = 底部",
    },
    "lithium": {
        "name": "锂",
        "代表品种": ["电池级碳酸锂", "氢氧化锂"],
        "数据源": "上海有色网 SMM / 百川盈孚",
        "fetch_url": "https://hq.smm.cn/lithium",
        "search": "电池级碳酸锂 价格 {YYYY-MM} 上海有色网",
        "key_signal": "碳酸锂 >12 万元/吨 = 反转信号；<8 万元/吨 = 行业底部",
    },
    "cobalt": {
        "name": "钴",
        "代表品种": ["MB 钴标准级", "硫酸钴"],
        "数据源": "MB（Metal Bulletin）/ 上海有色网",
        "fetch_url": "https://hq.smm.cn/cobalt",
        "search": "钴 价格 {YYYY-MM} cobalt price",
        "key_signal": "MB 钴 >25 美元/磅 = 强势；<15 美元/磅 = 底部",
    },
    "nickel": {
        "name": "镍",
        "代表品种": ["LME 3M 镍", "硫酸镍"],
        "数据源": "LME / 上海有色网",
        "fetch_url": "https://hq.smm.cn/nickel",
        "search": "LME nickel 3M price {YYYY-MM}",
        "key_signal": "LME 镍 >2 万美元/吨 = 强势；<1.5 万美元/吨 = 弱势",
    },
    "uranium": {
        "name": "铀",
        "代表品种": ["U3O8 现货", "Cameco 报价"],
        "数据源": "UxC / Cameco / TradeTech",
        "fetch_url": "https://www.cameco.com/invest/markets/uranium-price",
        "search": "uranium U3O8 spot price {YYYY-MM}",
        "key_signal": "U3O8 >80 美元/磅 = 强势区；>100 美元/磅 = 短期顶部信号",
    },
    "tungsten_antimony": {
        "name": "钨锑（小金属）",
        "代表品种": ["黑钨精矿", "锑锭"],
        "数据源": "上海有色网 SMM / 长江有色",
        "fetch_url": "https://hq.smm.cn/minor-metals",
        "search": "黑钨精矿 锑锭 价格 {YYYY-MM}",
        "key_signal": "战略小金属，与军工 / 半导体出口管制强相关",
    },
}


def _http_get(url, timeout=TIMEOUT):
    return requests.get(url, headers=HEADERS, timeout=timeout)


def fetch_fred_series(series_id, days=730):
    url = FRED_CSV.format(sid=series_id)
    try:
        r = _http_get(url)
        r.raise_for_status()
        reader = csv.reader(io.StringIO(r.text))
        rows = list(reader)
        if len(rows) < 2:
            return []
        out = []
        cutoff = (datetime.now() - timedelta(days=days)).date()
        for row in rows[1:]:
            if len(row) < 2:
                continue
            d_str, v_str = row[0].strip(), row[1].strip()
            if v_str in ("", ".", "NA"):
                continue
            try:
                d = datetime.strptime(d_str, "%Y-%m-%d").date()
                if d < cutoff:
                    continue
                out.append((d, float(v_str)))
            except (ValueError, TypeError):
                continue
        return out
    except Exception as exc:
        print(f"⚠️ FRED {series_id}: {exc}", file=sys.stderr)
        return []


def fetch_lme_metals():
    """6 大 LME 工业金属现货价（FRED 月度数据）。"""
    result = {}
    for sid, (name, unit, _) in LME_SERIES.items():
        data = fetch_fred_series(sid, days=730)
        if not data:
            continue
        latest_date, latest = data[-1]
        month_ago = data[-2][1] if len(data) > 1 else None
        quarter_ago = data[-4][1] if len(data) > 3 else None
        year_ago = data[-13][1] if len(data) > 12 else None

        result[sid] = {
            "name": name,
            "unit": unit,
            "latest_date": latest_date.strftime("%Y-%m-%d"),
            "latest": round(latest, 2),
            "month_ago": round(month_ago, 2) if month_ago else None,
            "quarter_ago": round(quarter_ago, 2) if quarter_ago else None,
            "year_ago": round(year_ago, 2) if year_ago else None,
            "month_change_pct": round((latest/month_ago-1)*100, 2) if month_ago else None,
            "quarter_change_pct": round((latest/quarter_ago-1)*100, 2) if quarter_ago else None,
            "year_change_pct": round((latest/year_ago-1)*100, 2) if year_ago else None,
        }
    return result


def fetch_em_commodity():
    """东财商品板块。f12=代码 f14=名称 f2=最新价 f3=涨跌幅"""
    try:
        r = _http_get(EM_COMMODITY_URL)
        r.raise_for_status()
        data = r.json()
        rows = data.get("data", {}).get("diff", []) if isinstance(data, dict) else []
        if not rows:
            return None
        return [{
            "code": x.get("f12"),
            "name": x.get("f14"),
            "latest": x.get("f2"),
            "change_pct": x.get("f3"),
            "high": x.get("f15"),
            "low": x.get("f16"),
        } for x in rows[:30]]
    except Exception as exc:
        print(f"⚠️ 东财商品: {exc}", file=sys.stderr)
        return None


def fetch_strategic_overview():
    """战略矿产 — 返回元数据 + 抓取建议（数据多需 web_fetch / web_search 兜底）。"""
    return STRATEGIC_MINERALS


def to_markdown(lme_data, em_data, strategic):
    lines = []
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines.append("# 工业金属与战略矿产市场\n")
    lines.append(f"**数据采集时间**: {ts}")
    lines.append("📎 **信源API**: FRED LME 月度金属价 API + 东财商品板块 push2 API + 上海有色网兜底\n")
    lines.append("---\n")

    # 1. LME 工业金属
    lines.append("## 1. LME 6 大工业金属现货走势（月度）\n")
    if lme_data:
        lines.append("| 品种 | 最新值 | 月环比 | 季度变化 | 同比 | 最新月 |")
        lines.append("|------|-------|--------|---------|-----|-------|")
        for sid, d in lme_data.items():
            lines.append(
                f"| {d['name']} | {d['latest']:.2f} {d['unit']} | "
                f"{d['month_change_pct']:+.2f}%" if d['month_change_pct'] is not None else "—"
                f" | "
                f"{d['quarter_change_pct']:+.2f}%" if d['quarter_change_pct'] is not None else "—"
                f" | "
                f"{d['year_change_pct']:+.2f}%" if d['year_change_pct'] is not None else "—"
                f" | {d['latest_date']} |"
            )
        lines.append("")
        lines.append("**研判口径**：")
        lines.append("- **铜（Dr. Copper）**：全球工业景气晴雨表，月环比 >5% 持续 = 全球补库存周期启动")
        lines.append("- **镍/锂电池金属**：新能源车需求决定中长期方向")
        lines.append("- **铁矿石**：中国地产 + 基建链条核心原料，与中国 PMI 高度同步")
        lines.append("")
    else:
        lines.append("⚠️ FRED LME 数据获取失败\n")

    # 2. 国内商品板块
    lines.append("## 2. 国内商品市场板块行情\n")
    if em_data:
        lines.append("| 代码 | 名称 | 最新价 | 涨跌幅 | 最高 | 最低 |")
        lines.append("|------|------|-------|--------|------|------|")
        for x in em_data[:20]:
            lines.append(
                f"| {x['code']} | {x['name']} | {x['latest']} | "
                f"{x['change_pct']}% | {x.get('high', '—')} | {x.get('low', '—')} |"
            )
        lines.append("")
    else:
        lines.append("⚠️ 东财商品板块获取失败（非交易时段会返回空）\n")

    # 3. 战略矿产
    lines.append("## 3. 战略矿产价格跟踪（需 web_fetch / web_search 补充）\n")
    if strategic:
        for key, info in strategic.items():
            lines.append(f"### {info['name']}\n")
            lines.append(f"- **代表品种**: {' / '.join(info['代表品种'])}")
            lines.append(f"- **主数据源**: {info['数据源']}")
            lines.append(f"- **抓取链接**: `web_fetch('{info['fetch_url']}', '提取最新现货价 + 周/月变动')`")
            lines.append(f"- **搜索备源**: `web_search '{info['search']}'`")
            lines.append(f"- **关键信号**: {info['key_signal']}")
            lines.append("")

    # 4. 商品轮动综合判断
    lines.append("## 4. 综合研判 — 商品轮动序列触发判断\n")
    lines.append("| 阶段 | 主导品种 | 触发信号 | 当前观察 |")
    lines.append("|------|---------|---------|---------|")
    lines.append("| ① 贵金属阶段（衰退末期） | 黄金/白银 | 实际利率下行 + 央行宽松预期 | 见 `gold_market.md` |")
    lines.append("| ② 工业金属阶段（复苏早期） | 铜/铝/铁矿 | LME 铜月环比 >5% + 中国 PMI > 50 | 见上表 |")
    lines.append("| ③ 能源阶段（扩张中段） | 原油/天然气 | OPEC+ 维持限产 + 全球补库 | 见 `eia_energy.md` |")
    lines.append("| ④ 农产品阶段（过热末段） | 大豆/玉米/小麦 | CPI 持续上行 + 极端天气 | 需 `web_search USDA WASDE` |")
    lines.append("")
    lines.append("**轮动切换规则**：")
    lines.append("- 贵金属→工业金属：实际利率见底回升 + LME 铜价突破 200 日均线")
    lines.append("- 工业金属→能源：油铜比突破长期均值 + OPEC+ 减产 / 地缘冲突")
    lines.append("- 战略矿产独立线索：与商品轮动并行，由产业政策 / 供应集中度 / 出口管制驱动")
    lines.append("")

    lines.append("---\n")
    lines.append("## 数据信源\n")
    lines.append("- **FRED LME / IMF Primary Commodity API** — 月度全球大宗商品价格")
    lines.append("- **东方财富商品板块 push2 API** — 国内期货行情")
    lines.append("- **上海有色网 SMM** — 国内有色金属现货 + 战略矿产")
    lines.append("- **Cameco / UxC** — 铀价权威报价")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="工业金属与战略矿产采集")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--lme", action="store_true")
    parser.add_argument("--domestic", action="store_true")
    parser.add_argument("--strategic", action="store_true")
    parser.add_argument("--output", help="Markdown 输出路径")
    parser.add_argument("--json", help="JSON 数据输出")
    args = parser.parse_args()

    if not any([args.all, args.lme, args.domestic, args.strategic]):
        parser.print_help()
        return 1

    lme_data = fetch_lme_metals() if (args.all or args.lme) else {}
    em_data = fetch_em_commodity() if (args.all or args.domestic) else None
    strategic = fetch_strategic_overview() if (args.all or args.strategic) else {}

    md = to_markdown(lme_data, em_data, strategic)

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
            "lme": lme_data, "domestic": em_data, "strategic": strategic,
            "collected_at": datetime.now().isoformat(),
        }, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        print(f"✅ JSON: {json_path}")

    if not lme_data and not em_data and not strategic:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
