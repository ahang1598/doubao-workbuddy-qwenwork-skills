# -*- coding: utf-8 -*-
"""
Gold Market Scraper — 黄金核心定价数据

数据源:
  1. FRED API — 黄金 LBMA 现货价、美元黄金走势
  2. SPDR Gold Trust (GLD) — ETF 持仓变动（公开 JSON / Stooq）
  3. CFTC COT 报告 — COMEX 黄金非商业净多持仓（含 web_fetch 兜底）
  4. 世界黄金协会 — 央行季度购金（web_search 兜底）

功能模块:
  1. 黄金现货价 + 历史走势（FRED）
  2. SPDR GLD ETF 持仓变动（吨/盎司）
  3. CFTC COT 黄金非商业净多持仓
  4. 央行购金 + 实际利率联动信号

用法:
  python gold_market_scraper.py --all
  python gold_market_scraper.py --price
  python gold_market_scraper.py --etf
  python gold_market_scraper.py --cot
  python gold_market_scraper.py --all --output FinancialData/gold_market.md
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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "*/*",
}

FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"

# 关键序列
GOLD_SERIES = {
    "GOLDAMGBD228NLBM": ("LBMA 黄金 AM 定盘价", "USD/oz"),
    "GOLDPMGBD228NLBM": ("LBMA 黄金 PM 定盘价", "USD/oz"),
}

# Stooq 公开 CSV（备源 — 免费/无 API key）
STOOQ_GLD = "https://stooq.com/q/d/l/?s=gld.us&d1={start}&d2={end}&i=d"
STOOQ_GOLD = "https://stooq.com/q/d/l/?s=xauusd&d1={start}&d2={end}&i=d"


def _http_get(url, timeout=TIMEOUT):
    return requests.get(url, headers=HEADERS, timeout=timeout)


def fetch_fred_series(series_id, days=180):
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
                v = float(v_str)
                out.append((d, v))
            except (ValueError, TypeError):
                continue
        return out
    except Exception as exc:
        print(f"⚠️ FRED {series_id}: {exc}", file=sys.stderr)
        return []


def fetch_stooq_csv(symbol_url, days=180):
    """Stooq 公开 CSV API。返回 [(date, open, high, low, close, volume)]"""
    end = datetime.now().strftime("%Y%m%d")
    start = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
    url = symbol_url.format(start=start, end=end)
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
                volume = float(row[5]) if len(row) > 5 and row[5] else None
                out.append((d, close, volume))
            except (ValueError, TypeError):
                continue
        return out
    except Exception as exc:
        print(f"⚠️ Stooq {symbol_url[:50]}: {exc}", file=sys.stderr)
        return []


def fetch_gold_price():
    """黄金价格 + 走势分析。"""
    result = {}
    # FRED LBMA
    for sid, (name, unit) in GOLD_SERIES.items():
        data = fetch_fred_series(sid, days=180)
        if data:
            result[sid] = {"name": name, "unit": unit, "data": data}
            break  # AM/PM 取一个就够

    # Stooq 备源
    stooq_data = fetch_stooq_csv(STOOQ_GOLD, days=180)
    if stooq_data:
        result["XAUUSD_stooq"] = {
            "name": "XAU/USD 现货黄金（Stooq）",
            "unit": "USD/oz",
            "data": [(d, c) for (d, c, _) in stooq_data],
        }

    return result


def fetch_gld_etf():
    """SPDR GLD ETF 行情 + 估算持仓变动（GLD 每股 ≈ 0.0936 oz，可换算总持仓）。"""
    data = fetch_stooq_csv(STOOQ_GLD, days=180)
    if not data:
        return None
    latest_date, latest_close, latest_vol = data[-1]
    week_ago = data[-6] if len(data) > 6 else (None, None, None)
    month_ago = data[-22] if len(data) > 22 else (None, None, None)

    return {
        "symbol": "GLD",
        "name": "SPDR Gold Trust ETF",
        "latest_date": latest_date.strftime("%Y-%m-%d"),
        "latest_price": round(latest_close, 2),
        "latest_volume": int(latest_vol) if latest_vol else None,
        "week_ago_price": round(week_ago[1], 2) if week_ago[1] else None,
        "month_ago_price": round(month_ago[1], 2) if month_ago[1] else None,
        "week_change_pct": round((latest_close / week_ago[1] - 1) * 100, 2)
                           if week_ago[1] else None,
        "month_change_pct": round((latest_close / month_ago[1] - 1) * 100, 2)
                            if month_ago[1] else None,
        "note": ("GLD 实时持仓数据需访问 https://www.spdrgoldshares.com/ "
                 "或用 web_fetch 提取。本脚本提供价格 + 量价数据作为持仓变动代理指标"
                 "（量增价升 → 流入；量增价跌 → 抛售）"),
        "history_30d": [(d.strftime("%Y-%m-%d"), c) for (d, c, _) in data[-30:]],
    }


def fetch_cot_gold():
    """CFTC COT 报告 — COMEX 黄金非商业净多持仓。

    CFTC 公开 ZIP（/cot/<year>.zip）较大，纯 requests 无法稳定解析。
    这里返回访问指引，让 agent 用 web_fetch + web_search 提取最新一周净多持仓。
    """
    return {
        "source_url": "https://www.cftc.gov/dea/futures/deacmesf.htm",
        "alt_url": "https://www.cmegroup.com/markets/metals/precious/gold.cot.html",
        "note": ("CFTC COT 周报数据格式较特殊（每周五更新前一周二数据）。"
                 "建议用 web_fetch 抓取上述页面的 'Non-Commercial Long/Short' 数据。"),
        "fallback_search": [
            "site:cftc.gov COT gold non-commercial net long latest",
            "COMEX gold managed money net long position {YYYY-MM}",
        ],
        "key_signal": (
            "净多持仓 > 250k 手 = 多头拥挤（黄金阶段顶部风险）；"
            "净多持仓 < 100k 手 = 多头出清（黄金阶段底部信号）"
        ),
    }


def fetch_central_bank_gold():
    """央行购金 — 季度数据由世界黄金协会发布。"""
    return {
        "source": "世界黄金协会 World Gold Council",
        "url": "https://www.gold.org/goldhub/data/gold-demand-by-country",
        "note": ("央行购金为季度数据（WGC Q1/Q2/Q3/Q4 报告发布）。"
                 "建议用 web_search 'central bank gold purchases {YYYY} quarterly' 获取最新数据。"),
        "fallback_search": [
            "site:gold.org central bank gold purchases quarterly",
            "World Gold Council Gold Demand Trends {YYYY}-Q{N}",
        ],
        "key_signal": (
            "全球央行季度净购金 > 200 吨 → 黄金长期支撑；"
            "净抛售 → 黄金阶段顶部"
        ),
        "context": (
            "2024-2025 全球央行购金创历史纪录，主要买家：中国、波兰、印度、土耳其。"
            "去美元化叙事下，央行购金成为黄金长期上涨的结构性驱动力。"
        ),
    }


def to_markdown(price_data, gld_data, cot_data, cb_data):
    lines = []
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines.append(f"# 黄金市场核心定价数据\n")
    lines.append(f"**数据采集时间**: {ts}")
    lines.append("📎 **信源API**: FRED LBMA 黄金定盘价 API + Stooq 现货黄金 CSV API + CFTC COT 报告\n")
    lines.append("---\n")

    # 1. 价格
    lines.append("## 1. 黄金现货价格走势\n")
    if price_data:
        for sid, info in price_data.items():
            data = info["data"]
            if not data:
                continue
            latest_date, latest_val = data[-1]
            week_ago = data[-6][1] if len(data) > 6 else None
            month_ago = data[-22][1] if len(data) > 22 else None
            quarter_ago = data[-66][1] if len(data) > 66 else None

            lines.append(f"### {info['name']} ({info['unit']})\n")
            lines.append("| 时点 | 价格 | 变化 |")
            lines.append("|------|------|------|")
            lines.append(f"| 最新（{latest_date}） | **{latest_val:.2f}** | — |")
            if week_ago:
                lines.append(f"| 1 周前 | {week_ago:.2f} | {(latest_val/week_ago-1)*100:+.2f}% |")
            if month_ago:
                lines.append(f"| 1 月前 | {month_ago:.2f} | {(latest_val/month_ago-1)*100:+.2f}% |")
            if quarter_ago:
                lines.append(f"| 3 月前 | {quarter_ago:.2f} | {(latest_val/quarter_ago-1)*100:+.2f}% |")
            lines.append("")
    else:
        lines.append("⚠️ 黄金价格获取失败\n")

    # 2. GLD ETF
    lines.append("## 2. SPDR Gold Trust (GLD) ETF — 持仓变动代理指标\n")
    if gld_data:
        lines.append(f"- **最新收盘价**: ${gld_data['latest_price']}（{gld_data['latest_date']}）")
        lines.append(f"- **1 周变化**: {gld_data['week_change_pct']:+.2f}%" if gld_data['week_change_pct'] is not None else "- 1 周变化: —")
        lines.append(f"- **1 月变化**: {gld_data['month_change_pct']:+.2f}%" if gld_data['month_change_pct'] is not None else "- 1 月变化: —")
        if gld_data.get("latest_volume"):
            lines.append(f"- **最新成交量**: {gld_data['latest_volume']:,} 股")
        lines.append("")
        lines.append(f"> 📌 {gld_data['note']}")
        lines.append("")
    else:
        lines.append("⚠️ GLD ETF 数据获取失败\n")

    # 3. COT
    lines.append("## 3. CFTC COT 报告 — COMEX 黄金非商业净多持仓\n")
    lines.append(f"- **数据源**: {cot_data['source_url']}")
    lines.append(f"- **备源**: {cot_data['alt_url']}")
    lines.append(f"- **关键信号**: {cot_data['key_signal']}")
    lines.append("")
    lines.append("**Agent 操作指引**：")
    lines.append(f"- 用 `web_fetch('{cot_data['alt_url']}', '提取最新一周 Managed Money 净多持仓 + 总持仓')` 获取详细数据")
    lines.append(f"- 备选搜索：`{cot_data['fallback_search'][0]}`")
    lines.append("")

    # 4. 央行购金
    lines.append("## 4. 央行购金 + 实际利率联动信号\n")
    lines.append(f"- **数据源**: {cb_data['source']} ({cb_data['url']})")
    lines.append(f"- **关键信号**: {cb_data['key_signal']}")
    lines.append(f"- **当前背景**: {cb_data['context']}")
    lines.append("")
    lines.append("**Agent 操作指引**：")
    lines.append(f"- 用 `web_search '{cb_data['fallback_search'][0]}'` 获取最新季度数据")
    lines.append("")

    # 5. 综合研判
    lines.append("## 5. 综合研判矩阵 — 金银双轮主题包入口判断\n")
    lines.append("| 信号维度 | 多头加分 | 空头扣分 | 当前观察 |")
    lines.append("|---------|---------|---------|---------|")
    lines.append("| 实际利率（10Y TIPS） | <0.5% 强支撑 | >2% 承压 | 见 `us_inflation.md` |")
    lines.append("| 美元指数 DXY | <100 利好 | >105 压力 | 见 `global_market.md` |")
    lines.append("| GLD ETF 持仓 | 持续增持 | 连续减持 | 本文件第 2 节 |")
    lines.append("| CFTC 净多 | 100-200k 健康区 | >250k 拥挤 / <100k 出清 | web_fetch 兜底 |")
    lines.append("| 央行购金 | >200 吨/季 | <100 吨/季 | WGC 季报 |")
    lines.append("| 地缘风险 GPR | 急升 | 缓和 | 见 `risk_indices.md` |")
    lines.append("")
    lines.append("**金银双轮触发**：5 维信号至少 4 维多头加分 → 主题包配置权重提升至 15-20%")
    lines.append("**主题退出**：实际利率突破 2% + GLD 连续减持 + CFTC 净多 >250k → 减半")
    lines.append("")

    lines.append("---\n")
    lines.append("## 数据信源\n")
    lines.append("- **FRED LBMA Gold Fixing API** — https://fred.stlouisfed.org/series/GOLDPMGBD228NLBM")
    lines.append("- **Stooq XAU/USD CSV API** — https://stooq.com/q/?s=xauusd")
    lines.append("- **Stooq GLD ETF CSV API** — https://stooq.com/q/?s=gld.us")
    lines.append("- **CFTC COT 黄金报告** — https://www.cftc.gov/dea/futures/deacmesf.htm")
    lines.append("- **CME 黄金 COT 页面** — https://www.cmegroup.com/markets/metals/precious/gold.cot.html")
    lines.append("- **世界黄金协会** — https://www.gold.org/goldhub/")
    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="黄金市场核心定价数据采集")
    parser.add_argument("--all", action="store_true", help="全部模块")
    parser.add_argument("--price", action="store_true", help="黄金现货价格")
    parser.add_argument("--etf", action="store_true", help="GLD ETF 持仓代理")
    parser.add_argument("--cot", action="store_true", help="CFTC COT 报告")
    parser.add_argument("--cb", action="store_true", help="央行购金")
    parser.add_argument("--output", help="Markdown 输出路径")
    parser.add_argument("--json", help="JSON 数据输出")
    args = parser.parse_args()

    if not any([args.all, args.price, args.etf, args.cot, args.cb]):
        parser.print_help()
        return 1

    price_data = fetch_gold_price() if (args.all or args.price) else {}
    gld_data = fetch_gld_etf() if (args.all or args.etf) else None
    cot_data = fetch_cot_gold() if (args.all or args.cot) else {}
    cb_data = fetch_central_bank_gold() if (args.all or args.cb) else {}

    md = to_markdown(price_data, gld_data, cot_data, cb_data)

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
            "price": {sid: {"name": v["name"], "unit": v["unit"],
                            "data": [(d.strftime("%Y-%m-%d"), val) for d, val in v["data"]]}
                      for sid, v in price_data.items()},
            "gld_etf": gld_data,
            "cot": cot_data,
            "central_bank": cb_data,
            "collected_at": datetime.now().isoformat(),
        }, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        print(f"✅ JSON: {json_path}")

    if not price_data and not gld_data:
        print("⚠️ 价格/ETF 全部失败", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
