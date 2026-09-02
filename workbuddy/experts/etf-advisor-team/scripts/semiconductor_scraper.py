# -*- coding: utf-8 -*-
"""
Semiconductor Industry Scraper — 半导体产业链景气数据

数据源:
  1. Stooq — SOX 费城半导体指数、SMH ETF、台积电 ADR (TSM)
  2. 台积电（TSMC）月度营收 — 公开 RSS / 投资者关系页面（web_fetch 兜底）
  3. 北美半导体 BB Ratio（SEMI 协会，月度发布，需 web_fetch）
  4. 国内半导体设备与材料公司行情（东财 push2 板块）

功能模块:
  1. SOX 指数 + SMH ETF 走势（行业龙头同步指标）
  2. TSMC ADR 月度行情（与产业景气高度相关）
  3. 台积电月度营收（前瞻指标）
  4. 北美半导体 BB Ratio（订单/出货比，>1 = 景气向上）
  5. AI 三段式定位辅助（云厂商 capex / 推理成本）

用法:
  python semiconductor_scraper.py --all
  python semiconductor_scraper.py --indices
  python semiconductor_scraper.py --tsmc
  python semiconductor_scraper.py --bb-ratio
  python semiconductor_scraper.py --all --output FinancialData/semiconductor.md
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
STOOQ_CSV = "https://stooq.com/q/d/l/?s={sym}&d1={start}&d2={end}&i=d"


# 关键标的
SEMICON_SYMBOLS = {
    "^sox":   ("SOX 费城半导体指数", "指数"),
    "smh.us": ("SMH 半导体 ETF",     "USD"),
    "tsm.us": ("TSMC ADR (台积电)",  "USD"),
    "nvda.us": ("NVIDIA",            "USD"),
    "asml.us": ("ASML",              "USD"),
    "amd.us":  ("AMD",               "USD"),
    "qqq.us":  ("纳斯达克 100 ETF",  "USD"),  # 对照基准
}


# 国内半导体板块 — 东财
EM_SEMICON_INDEX_URL = ("https://push2.eastmoney.com/api/qt/clist/get?"
                        "fs=b%3ABK0480&"  # 半导体行业板块
                        "fields=f12,f14,f2,f3,f4,f5,f6,f15,f16&"
                        "fid=f3&po=1&pz=50&pn=1")


# 台积电月度营收 RSS / IR
TSMC_IR_URL = "https://investor.tsmc.com/english/monthly-revenue"
SEMI_BB_RATIO_URL = "https://www.semi.org/en/news-resources/semi-monthly-statistics"


def _http_get(url, timeout=TIMEOUT):
    return requests.get(url, headers=HEADERS, timeout=timeout)


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
                volume = float(row[5]) if len(row) > 5 and row[5] else None
                out.append((d, close, volume))
            except (ValueError, TypeError):
                continue
        return out
    except Exception as exc:
        print(f"⚠️ Stooq {symbol}: {exc}", file=sys.stderr)
        return []


def fetch_indices():
    result = {}
    for sym, (name, unit) in SEMICON_SYMBOLS.items():
        data = fetch_stooq(sym, days=180)
        if not data:
            continue
        latest_date, latest, _ = data[-1]
        week_ago = data[-6][1] if len(data) > 6 else None
        month_ago = data[-22][1] if len(data) > 22 else None
        quarter_ago = data[-66][1] if len(data) > 66 else None

        # 计算 200 日 SMA（如果数据足够）
        sma200 = None
        if len(data) >= 200:
            sma200 = sum(d[1] for d in data[-200:]) / 200

        result[sym] = {
            "name": name,
            "unit": unit,
            "latest_date": latest_date.strftime("%Y-%m-%d"),
            "latest": round(latest, 2),
            "week_change_pct": round((latest/week_ago-1)*100, 2) if week_ago else None,
            "month_change_pct": round((latest/month_ago-1)*100, 2) if month_ago else None,
            "quarter_change_pct": round((latest/quarter_ago-1)*100, 2) if quarter_ago else None,
            "sma200": round(sma200, 2) if sma200 else None,
            "above_sma200": (latest > sma200) if sma200 else None,
        }
    return result


def fetch_em_semicon():
    try:
        r = _http_get(EM_SEMICON_INDEX_URL)
        r.raise_for_status()
        data = r.json()
        rows = data.get("data", {}).get("diff", []) if isinstance(data, dict) else []
        return [{
            "code": x.get("f12"),
            "name": x.get("f14"),
            "latest": x.get("f2"),
            "change_pct": x.get("f3"),
            "amount_yi": (x.get("f6", 0) / 1e8) if x.get("f6") else None,
        } for x in rows[:30]] if rows else None
    except Exception as exc:
        print(f"⚠️ 东财半导体: {exc}", file=sys.stderr)
        return None


def fetch_tsmc_revenue():
    """台积电月度营收（公开 IR 数据，需 web_fetch 提取细节）。"""
    return {
        "ir_url": TSMC_IR_URL,
        "note": ("台积电每月 10 日左右公布上月营收。建议用 "
                 "`web_fetch('https://investor.tsmc.com/english/monthly-revenue', "
                 "'提取最新 6 个月营收同比 YoY / 环比 MoM')` 获取详细数据。"),
        "key_signal": (
            "营收同比 +20% 以上持续 3 月 = AI / 数据中心需求强劲；"
            "营收同比 -10% 以下 = 半导体周期下行确认"
        ),
        "fallback_search": "site:investor.tsmc.com monthly revenue {YYYY-MM}",
    }


def fetch_bb_ratio():
    """北美半导体 BB Ratio。"""
    return {
        "source_url": SEMI_BB_RATIO_URL,
        "note": ("SEMI 协会每月发布 'Worldwide Billings Report'。"
                 "BB Ratio = 订单 / 出货，>1 表示订单快于出货（景气扩张）。"
                 f"建议 `web_fetch('{SEMI_BB_RATIO_URL}', '提取北美半导体设备 BB Ratio + 月度账单')`"),
        "key_signal": (
            "BB Ratio >1.10 持续 = 强景气扩张；0.95-1.05 = 平衡；<0.95 = 景气下行"
        ),
        "fallback_search": "North America semiconductor billings BB ratio SEMI {YYYY-MM}",
    }


def to_markdown(indices, em_semicon, tsmc, bb_ratio):
    lines = []
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines.append("# 半导体产业链景气数据\n")
    lines.append(f"**数据采集时间**: {ts}")
    lines.append("📎 **信源API**: Stooq SOX/SMH/TSM CSV API + 东财半导体板块 + 台积电 IR + SEMI 月报\n")
    lines.append("---\n")

    # 1. 美股龙头
    lines.append("## 1. 美股半导体核心标的（同步指标）\n")
    if indices:
        lines.append("| 标的 | 最新价 | 1周变化 | 1月变化 | 3月变化 | 200日均线位置 |")
        lines.append("|------|-------|--------|---------|---------|-------------|")
        for sym, d in indices.items():
            sma_pos = ("**站上 200 日**" if d.get("above_sma200") is True else
                       "跌破 200 日" if d.get("above_sma200") is False else "—")
            lines.append(
                f"| {d['name']} ({sym}) | {d['latest']} | "
                f"{d.get('week_change_pct', '—')}% | "
                f"{d.get('month_change_pct', '—')}% | "
                f"{d.get('quarter_change_pct', '—')}% | {sma_pos} |"
            )
        lines.append("")
        lines.append("**研判口径**：")
        lines.append("- **SOX 站上 200 日均线 + 月环比 +5% 以上** = AI / 半导体景气向上确认")
        lines.append("- **TSMC 月度营收 +20% YoY** = AI 算力需求兑现")
        lines.append("- **NVDA 跑赢 SOX** = AI 主线延续；NVDA 跑输 SOX = 景气向应用端扩散")
        lines.append("")
    else:
        lines.append("⚠️ Stooq 数据获取失败\n")

    # 2. 国内半导体板块
    lines.append("## 2. 国内半导体板块龙头\n")
    if em_semicon:
        lines.append("| 代码 | 名称 | 最新价 | 涨跌幅 | 成交额(亿) |")
        lines.append("|------|------|-------|--------|-----------|")
        for x in em_semicon[:20]:
            amt = f"{x['amount_yi']:.2f}" if x.get("amount_yi") is not None else "—"
            lines.append(
                f"| {x['code']} | {x['name']} | {x['latest']} | "
                f"{x['change_pct']}% | {amt} |"
            )
        lines.append("")
    else:
        lines.append("⚠️ 国内半导体板块获取失败\n")

    # 3. 台积电营收
    lines.append("## 3. 台积电（TSMC）月度营收 — AI 景气前瞻指标\n")
    lines.append(f"- **官方页面**: {tsmc['ir_url']}")
    lines.append(f"- **关键信号**: {tsmc['key_signal']}")
    lines.append(f"- **抓取建议**: {tsmc['note']}")
    lines.append("")

    # 4. BB Ratio
    lines.append("## 4. 北美半导体 BB Ratio — 设备景气度\n")
    lines.append(f"- **数据源**: {bb_ratio['source_url']}")
    lines.append(f"- **关键信号**: {bb_ratio['key_signal']}")
    lines.append(f"- **抓取建议**: {bb_ratio['note']}")
    lines.append("")

    # 5. AI 三段式定位
    lines.append("## 5. 综合研判 — AI 三段式定位 + 长周期科技主题\n")
    lines.append("| 维度 | 早期布局 | 加速兑现 | 估值透支 |")
    lines.append("|------|---------|---------|---------|")
    lines.append("| 渗透率 | <10% | 10-50% | >50% |")
    lines.append("| TFP 信号 | <0.5% | 0.5-1.5% | >1.5%（已 price in） |")
    lines.append("| TSMC 营收 | YoY <10% | YoY 15-30% | YoY >30%（高位）|")
    lines.append("| BB Ratio | <1.0 | 1.05-1.15 | >1.15 |")
    lines.append("| 仓位指引 | 30-40% 主题占比 | 50-60% 主题占比 | 减半至 20-30% |")
    lines.append("| 历史镜像 | 互联网 1995 | 互联网 1998 | 互联网 2000 |")
    lines.append("")
    lines.append("**子方向轮动**（AI 三段式内部）：")
    lines.append("- **算力链**（GPU / 服务器 / 光模块 / 数据中心电力）→ 已进入估值透支段，标配-")
    lines.append("- **半导体设备 / 材料**（中芯国际 / 北方华创 / 沪硅产业）→ 国产替代主题，独立线索")
    lines.append("- **AI 应用端**（企业 SaaS / 终端模型 / 智能驾驶）→ 早期布局段，超配机会")
    lines.append("- **AI 终端硬件**（手机 / PC / 机器人）→ 加速兑现段，关注渗透率拐点")
    lines.append("")

    lines.append("---\n")
    lines.append("## 数据信源\n")
    lines.append("- **Stooq 美股 CSV API** — SOX/SMH/TSM/NVDA/ASML/AMD/QQQ 历史日线")
    lines.append("- **东财 push2 半导体板块 API** — b:BK0480")
    lines.append("- **台积电投资者关系** — https://investor.tsmc.com/english/monthly-revenue")
    lines.append("- **SEMI 协会月度统计** — https://www.semi.org/en/news-resources/semi-monthly-statistics")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="半导体产业链景气数据采集")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--indices", action="store_true")
    parser.add_argument("--domestic", action="store_true")
    parser.add_argument("--tsmc", action="store_true")
    parser.add_argument("--bb-ratio", action="store_true")
    parser.add_argument("--output", help="Markdown 输出路径")
    parser.add_argument("--json", help="JSON 数据输出")
    args = parser.parse_args()

    if not any([args.all, args.indices, args.domestic, args.tsmc, args.bb_ratio]):
        parser.print_help()
        return 1

    indices = fetch_indices() if (args.all or args.indices) else {}
    em_semicon = fetch_em_semicon() if (args.all or args.domestic) else None
    tsmc = fetch_tsmc_revenue() if (args.all or args.tsmc) else {}
    bb_ratio = fetch_bb_ratio() if (args.all or args.bb_ratio) else {}

    md = to_markdown(indices, em_semicon, tsmc, bb_ratio)

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
            "indices": indices, "domestic": em_semicon,
            "tsmc": tsmc, "bb_ratio": bb_ratio,
            "collected_at": datetime.now().isoformat(),
        }, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        print(f"✅ JSON: {json_path}")

    if not indices and not em_semicon:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
