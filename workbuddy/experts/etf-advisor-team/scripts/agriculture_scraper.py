# -*- coding: utf-8 -*-
"""
Agriculture Scraper — 农产品价格与供需

数据源:
  1. FRED API — IMF 全球农产品月度价格指数（玉米/小麦/大豆/糖/咖啡/棉花）
  2. Stooq — CBOT 玉米/大豆/小麦期货
  3. USDA WASDE 月报（需 web_fetch 兜底）
  4. 国内农产品（东财商品板块 — 豆粕/玉米/白糖/棉花期货）

功能模块:
  1. CBOT 主力农产品期货走势
  2. IMF 全球农产品价格指数（月度）
  3. 国内农产品期货（豆粕/玉米/白糖等）
  4. USDA WASDE 月报抓取建议
  5. 商品轮动末段（农产品阶段）触发判断

用法:
  python agriculture_scraper.py --all
  python agriculture_scraper.py --cbot
  python agriculture_scraper.py --imf
  python agriculture_scraper.py --domestic
  python agriculture_scraper.py --all --output FinancialData/agriculture.md
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
HEADERS = {"User-Agent": "Mozilla/5.0 AppleWebKit/537.36", "Accept": "*/*"}
FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
STOOQ_CSV = "https://stooq.com/q/d/l/?s={sym}&d1={start}&d2={end}&i=d"


# IMF 全球农产品价格指数（FRED 镜像）
IMF_AGRI_SERIES = {
    "PMAIZMTUSDM":   ("IMF 玉米全球月度价",  "USD/吨"),
    "PWHEAMTUSDM":   ("IMF 小麦全球月度价",  "USD/吨"),
    "PSOYBUSDM":     ("IMF 大豆全球月度价",  "USD/蒲式耳"),
    "PSUGAUSAUSDM":  ("IMF 糖（美国）月度价","美分/磅"),
    "PCOFFOTMUSDM":  ("IMF 咖啡其他温和月度价","美分/磅"),
    "PCOTTINDUSDM":  ("IMF 棉花 Cotlook A 指数","美分/磅"),
    "PRICENPQUSDM":  ("IMF 大米泰国月度价",  "USD/吨"),
}

# CBOT 期货（Stooq 备源）
CBOT_FUTURES = {
    "zc.f": "CBOT 玉米主连",
    "zw.f": "CBOT 小麦主连",
    "zs.f": "CBOT 大豆主连",
    "zm.f": "CBOT 豆粕主连",
    "zl.f": "CBOT 豆油主连",
    "sb.f": "ICE 原糖主连",
    "ct.f": "ICE 棉花主连",
    "kc.f": "ICE 咖啡主连",
}

# 国内农产品板块 — 东财
EM_AGRI_URL = ("https://push2.eastmoney.com/api/qt/clist/get?"
               "fs=m%3A113%2Bt%3A8&"  # 大商所农产品 / 郑商所
               "fields=f12,f14,f2,f3,f5,f6,f15,f16&"
               "fid=f3&po=1&pz=50&pn=1")

# USDA WASDE 月报
USDA_WASDE_URL = "https://www.usda.gov/oce/commodity/wasde"


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


def fetch_stooq(symbol, days=180):
    end = datetime.now().strftime("%Y%m%d")
    start = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
    url = STOOQ_CSV.format(sym=symbol, start=start, end=end)
    try:
        r = _http_get(url)
        r.raise_for_status()
        if "Date" not in r.text[:50]:
            return []
        reader = csv.reader(io.StringIO(r.text))
        rows = list(reader)
        out = []
        for row in rows[1:]:
            if len(row) < 5:
                continue
            try:
                d = datetime.strptime(row[0], "%Y-%m-%d").date()
                close = float(row[4])
                out.append((d, close))
            except (ValueError, TypeError):
                continue
        return out
    except Exception as exc:
        print(f"⚠️ Stooq {symbol}: {exc}", file=sys.stderr)
        return []


def fetch_imf_indices():
    result = {}
    for sid, (name, unit) in IMF_AGRI_SERIES.items():
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
            "month_change_pct": round((latest/month_ago-1)*100, 2) if month_ago else None,
            "quarter_change_pct": round((latest/quarter_ago-1)*100, 2) if quarter_ago else None,
            "year_change_pct": round((latest/year_ago-1)*100, 2) if year_ago else None,
        }
    return result


def fetch_cbot_futures():
    result = {}
    for sym, name in CBOT_FUTURES.items():
        data = fetch_stooq(sym, days=180)
        if not data:
            continue
        latest_date, latest = data[-1]
        week_ago = data[-6][1] if len(data) > 6 else None
        month_ago = data[-22][1] if len(data) > 22 else None
        quarter_ago = data[-66][1] if len(data) > 66 else None

        result[sym] = {
            "name": name,
            "latest_date": latest_date.strftime("%Y-%m-%d"),
            "latest": round(latest, 2),
            "week_change_pct": round((latest/week_ago-1)*100, 2) if week_ago else None,
            "month_change_pct": round((latest/month_ago-1)*100, 2) if month_ago else None,
            "quarter_change_pct": round((latest/quarter_ago-1)*100, 2) if quarter_ago else None,
        }
    return result


def fetch_em_agri():
    try:
        r = _http_get(EM_AGRI_URL)
        r.raise_for_status()
        data = r.json()
        rows = data.get("data", {}).get("diff", []) if isinstance(data, dict) else []
        return [{
            "code": x.get("f12"),
            "name": x.get("f14"),
            "latest": x.get("f2"),
            "change_pct": x.get("f3"),
        } for x in rows[:30]] if rows else None
    except Exception as exc:
        print(f"⚠️ 东财农产品: {exc}", file=sys.stderr)
        return None


def fetch_wasde_info():
    return {
        "official_url": USDA_WASDE_URL,
        "alt_url": "https://www.usda.gov/about-usda/news/wasde",
        "schedule": "USDA 每月 10-12 日发布 WASDE 月报",
        "note": ("USDA WASDE = World Agricultural Supply and Demand Estimates，"
                 "全球农产品供需预测权威报告。建议 "
                 f"`web_fetch('{USDA_WASDE_URL}', '提取最新月份玉米/大豆/小麦的全球产量、库存、消费数据')`"),
        "key_signal": (
            "玉米 / 大豆全球库销比 < 15% = 价格强势区；"
            "ENSO（厄尔尼诺/拉尼娜）切换 = 农产品阶段性主题"
        ),
    }


def to_markdown(imf_data, cbot_data, em_data, wasde):
    lines = []
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines.append("# 农产品价格与供需\n")
    lines.append(f"**数据采集时间**: {ts}")
    lines.append("📎 **信源API**: FRED IMF 农产品月度价 API + Stooq CBOT/ICE 期货 + 东财农产品板块 + USDA WASDE\n")
    lines.append("---\n")

    # 1. IMF 月度价格指数
    lines.append("## 1. IMF 全球农产品月度价格指数\n")
    if imf_data:
        lines.append("| 品种 | 最新值 | 月环比 | 季度变化 | 同比 | 最新月 |")
        lines.append("|------|-------|--------|---------|-----|-------|")
        for sid, d in imf_data.items():
            lines.append(
                f"| {d['name']} | {d['latest']} {d['unit']} | "
                f"{d.get('month_change_pct', '—')}% | "
                f"{d.get('quarter_change_pct', '—')}% | "
                f"{d.get('year_change_pct', '—')}% | {d['latest_date']} |"
            )
        lines.append("")
    else:
        lines.append("⚠️ FRED IMF 数据获取失败\n")

    # 2. CBOT 期货
    lines.append("## 2. CBOT / ICE 主力农产品期货（日线高频）\n")
    if cbot_data:
        lines.append("| 品种 | 最新价 | 1周变化 | 1月变化 | 3月变化 | 最新日期 |")
        lines.append("|------|-------|--------|---------|---------|---------|")
        for sym, d in cbot_data.items():
            lines.append(
                f"| {d['name']} ({sym}) | {d['latest']} | "
                f"{d.get('week_change_pct', '—')}% | "
                f"{d.get('month_change_pct', '—')}% | "
                f"{d.get('quarter_change_pct', '—')}% | {d['latest_date']} |"
            )
        lines.append("")
    else:
        lines.append("⚠️ CBOT 期货获取失败\n")

    # 3. 国内农产品
    lines.append("## 3. 国内农产品期货（大商所 / 郑商所）\n")
    if em_data:
        lines.append("| 代码 | 名称 | 最新价 | 涨跌幅 |")
        lines.append("|------|------|-------|--------|")
        for x in em_data[:20]:
            lines.append(
                f"| {x['code']} | {x['name']} | {x['latest']} | {x['change_pct']}% |"
            )
        lines.append("")
    else:
        lines.append("⚠️ 国内农产品板块获取失败（非交易时段返回空）\n")

    # 4. USDA WASDE
    lines.append("## 4. USDA WASDE 月报 — 全球农产品供需权威预测\n")
    lines.append(f"- **官方页面**: {wasde['official_url']}")
    lines.append(f"- **发布节奏**: {wasde['schedule']}")
    lines.append(f"- **关键信号**: {wasde['key_signal']}")
    lines.append(f"- **抓取建议**: {wasde['note']}")
    lines.append("")

    # 5. 商品轮动末段判断
    lines.append("## 5. 综合研判 — 商品轮动末段（农产品阶段）+ 粮食安全主题\n")
    lines.append("| 维度 | 农产品阶段触发条件 | 当前观察 |")
    lines.append("|------|------------------|---------|")
    lines.append("| 全球 CPI | 通胀粘性 + 食品分项贡献 >40% | 见 `us_macro.md` / `macro_data.md` |")
    lines.append("| ENSO 状态 | 拉尼娜 / 厄尔尼诺事件确认 | 需 `web_search 'ENSO advisory NOAA latest'` |")
    lines.append("| WASDE 库销比 | 玉米/大豆 < 15% | 见上节 |")
    lines.append("| CBOT 玉米 | 突破前高 + 月环比 +10% | 见第 2 节 |")
    lines.append("| 地缘扰动 | 黑海粮食通道 / 主产国出口管制 | 关注新闻面 |")
    lines.append("")
    lines.append("**3+ 维触发 → 商品轮动进入农产品末段 → 粮食安全主题 / 农业 ETF 战术配置 5-8%**\n")

    lines.append("---\n")
    lines.append("## 数据信源\n")
    lines.append("- **FRED IMF Primary Commodity API** — 月度全球农产品价格")
    lines.append("- **Stooq CBOT / ICE 期货** — zc.f / zw.f / zs.f 等日线 CSV")
    lines.append("- **东财 push2 商品板块 API** — 大商所 / 郑商所农产品")
    lines.append("- **USDA WASDE** — https://www.usda.gov/oce/commodity/wasde")
    lines.append("- **NOAA ENSO Advisory** — https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_advisory/")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="农产品价格与供需采集")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--imf", action="store_true")
    parser.add_argument("--cbot", action="store_true")
    parser.add_argument("--domestic", action="store_true")
    parser.add_argument("--wasde", action="store_true")
    parser.add_argument("--output", help="Markdown 输出路径")
    parser.add_argument("--json", help="JSON 数据输出")
    args = parser.parse_args()

    if not any([args.all, args.imf, args.cbot, args.domestic, args.wasde]):
        parser.print_help()
        return 1

    imf_data = fetch_imf_indices() if (args.all or args.imf) else {}
    cbot_data = fetch_cbot_futures() if (args.all or args.cbot) else {}
    em_data = fetch_em_agri() if (args.all or args.domestic) else None
    wasde = fetch_wasde_info() if (args.all or args.wasde) else {}

    md = to_markdown(imf_data, cbot_data, em_data, wasde)

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
            "imf": imf_data, "cbot": cbot_data, "domestic": em_data, "wasde": wasde,
            "collected_at": datetime.now().isoformat(),
        }, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        print(f"✅ JSON: {json_path}")

    if not imf_data and not cbot_data and not em_data:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
