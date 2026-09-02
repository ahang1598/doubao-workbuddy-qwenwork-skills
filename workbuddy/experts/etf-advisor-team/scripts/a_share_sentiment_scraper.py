# -*- coding: utf-8 -*-
"""
A-Share Sentiment Scraper — A股资金面与市场情绪指标

数据源:
  1. 东方财富 datacenter / push2 API — 涨跌停统计、南向资金、行业资金流
  2. 天天基金 / 东财 — 偏股新发基金、ETF 资金净流入
  3. 中证指数 / 东财 — 全 A 成交量、ERP 风险溢价

功能模块:
  1. 涨跌停统计（每日涨停 / 跌停 / 炸板率 / 连板高度）
  2. 港股通南向资金（每日净流入 + 累计）
  3. ETF 资金净流入（按类型：宽基 / 行业主题 / 跨境）
  4. 偏股型基金新发份额（月度 / 季度）
  5. 银证转账估算（用两融余额 30 日变化代理）
  6. 全 A 换手率与情绪温度

用法:
  python a_share_sentiment_scraper.py --all
  python a_share_sentiment_scraper.py --limit-up
  python a_share_sentiment_scraper.py --southbound
  python a_share_sentiment_scraper.py --etf-flow
  python a_share_sentiment_scraper.py --new-fund
  python a_share_sentiment_scraper.py --all --output FinancialData/a_share_sentiment.md
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
import re
from datetime import datetime, timedelta
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

# 东财 datacenter 涨跌停接口
LIMIT_UP_URL = "https://push2ex.eastmoney.com/getTopicZTPool"
LIMIT_DOWN_URL = "https://push2ex.eastmoney.com/getTopicDTPool"

# 港股通南向资金 — 东财
SOUTHBOUND_URL = ("https://datacenter-web.eastmoney.com/api/data/v1/get?"
                  "sortColumns=TRADE_DATE&sortTypes=-1&pageSize=30&pageNumber=1&"
                  "reportName=RPT_MUTUAL_DEAL_HISTORY&columns=ALL&"
                  "filter=(MUTUAL_TYPE=%22002%22)")  # 002 = 港股通南向

# 公募 ETF 资金净流入 — 东财 push2
ETF_FLOW_URL = ("https://push2.eastmoney.com/api/qt/clist/get?"
                "fs=b%3AMK0021,b%3AMK0022,b%3AMK0023,b%3AMK0024&"
                "fields=f12,f14,f2,f3,f62,f184,f4,f5,f6&"
                "fid=f62&po=1&pz=50&pn=1")

# 偏股新发基金（天天基金 fund.eastmoney.com）
NEW_FUND_URL = ("https://fundact.eastmoney.com/api/Fund/jsonp.aspx?"
                "jsonp=callback&Fcodes=0&"
                "Type=newfund&pageIndex=1&pageSize=30")

# 全 A 行情（用于换手率/成交计算）— 东财 push2
ALL_A_URL = ("https://push2.eastmoney.com/api/qt/stock/get?"
             "secid=1.000001&fields=f57,f58,f86,f43,f60,f47,f48")  # 上证指数代理


def _http_get(url, timeout=TIMEOUT):
    return requests.get(url, headers=HEADERS, timeout=timeout)


def fetch_limit_up_count():
    """涨停 / 跌停 / 炸板统计。东财 push2ex 返回 JSONP-like JSON。"""
    today = datetime.now().strftime("%Y%m%d")
    url = f"{LIMIT_UP_URL}?ut=7eea3edcaed734bea9cbfc24409ed989&dpt=wz.ztzt&Pageindex=0&pagesize=300&sort=fbt%3Aasc&date={today}"
    try:
        r = _http_get(url)
        r.raise_for_status()
        text = r.text
        # 处理 JSONP 包装
        if text.startswith("var "):
            text = text[text.index("(")+1:text.rindex(")")]
        elif "(" in text[:30] and text.rstrip().endswith(")"):
            text = text[text.index("(")+1:text.rindex(")")]
        data = json.loads(text)
        pool = data.get("data", {}).get("pool", []) if isinstance(data, dict) else []

        if not pool:
            return None

        # 统计：涨停个数 / 炸板数（hsl 字段判断） / 连板分布
        total_zt = len(pool)
        # 炸板：fbt > 0 表示首次涨停时间，但实际炸板需 zbc 字段
        # 这里用简化口径：连板数 = lbc 字段
        consecutive = {}
        broken = 0
        for stock in pool:
            lbc = stock.get("lbc", 1) or 1
            if lbc > 1:
                consecutive[lbc] = consecutive.get(lbc, 0) + 1
            zbc = stock.get("zbc", 0)
            if zbc and zbc > 0:
                broken += 1

        return {
            "date": today,
            "limit_up_count": total_zt,
            "broken_count": broken,
            "broken_rate_pct": round(broken / max(total_zt + broken, 1) * 100, 1),
            "consecutive_distribution": dict(sorted(consecutive.items(), reverse=True)[:5]),
            "max_consecutive": max(consecutive.keys(), default=1),
            "interpretation": ("涨停 >100 + 连板高度 ≥5 = 情绪过热；"
                               "涨停 <30 + 炸板率 >40% = 情绪低迷"),
        }
    except Exception as exc:
        print(f"⚠️ 涨停数据: {exc}", file=sys.stderr)
        return None


def fetch_southbound_flow():
    """港股通南向资金 — 近 30 日。"""
    try:
        r = _http_get(SOUTHBOUND_URL)
        r.raise_for_status()
        data = r.json()
        rows = data.get("result", {}).get("data", [])
        if not rows:
            return None

        # 取最新 + 周累计 + 月累计
        latest = rows[0]
        week_rows = rows[:5]
        month_rows = rows[:22]

        latest_net = float(latest.get("FUND_INFLOW", 0) or 0) / 1e8  # 转亿元
        week_sum = sum(float(r.get("FUND_INFLOW", 0) or 0) for r in week_rows) / 1e8
        month_sum = sum(float(r.get("FUND_INFLOW", 0) or 0) for r in month_rows) / 1e8

        return {
            "latest_date": latest.get("TRADE_DATE", "").split(" ")[0],
            "latest_net_yi": round(latest_net, 2),
            "week_sum_yi": round(week_sum, 2),
            "month_sum_yi": round(month_sum, 2),
            "interpretation": ("月累计 > 500 亿 = 南向强势流入（恒生科技 / 互联网主题入口资金）；"
                               "持续净流出 = 风险偏好回落"),
        }
    except Exception as exc:
        print(f"⚠️ 南向资金: {exc}", file=sys.stderr)
        return None


def fetch_etf_flow():
    """ETF 资金净流入 TOP 排行（按净流入金额）。"""
    try:
        r = _http_get(ETF_FLOW_URL)
        r.raise_for_status()
        data = r.json()
        rows = data.get("data", {}).get("diff", []) if isinstance(data, dict) else []
        if not rows:
            return None

        results = {"net_inflow_top": [], "net_outflow_top": []}
        # f62 = 净流入金额 (元)
        sorted_rows = sorted(rows, key=lambda x: x.get("f62", 0) or 0, reverse=True)
        for row in sorted_rows[:10]:
            results["net_inflow_top"].append({
                "code": row.get("f12"),
                "name": row.get("f14"),
                "net_inflow_yi": round((row.get("f62", 0) or 0) / 1e8, 2),
                "change_pct": row.get("f3"),
            })
        for row in sorted_rows[-10:][::-1]:
            results["net_outflow_top"].append({
                "code": row.get("f12"),
                "name": row.get("f14"),
                "net_outflow_yi": round((row.get("f62", 0) or 0) / 1e8, 2),
                "change_pct": row.get("f3"),
            })

        results["total_count"] = len(rows)
        results["interpretation"] = ("流入 TOP 集中在哪些主题 = 增量资金倾向；"
                                    "宽基 ETF 大幅流入 = 长线/被动配置盘介入")
        return results
    except Exception as exc:
        print(f"⚠️ ETF 资金流: {exc}", file=sys.stderr)
        return None


def fetch_new_fund_issuance():
    """偏股新发基金 — 近期发行规模与节奏。"""
    try:
        r = _http_get(NEW_FUND_URL)
        r.raise_for_status()
        text = r.text
        # 处理 JSONP
        m = re.search(r"\((.*)\)", text)
        if m:
            text = m.group(1)
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return None

        # 解析数据结构（天天基金返回结构因接口而异，做兜底）
        funds = data.get("Datas", []) if isinstance(data, dict) else []
        if not funds:
            return {
                "note": "天天基金新发数据结构变化，建议用 web_fetch 'https://fund.eastmoney.com/data/xinfund.html' 兜底",
                "fallback_url": "https://fund.eastmoney.com/data/xinfund.html",
            }

        # 统计偏股型新发
        equity_funds = [f for f in funds[:30]
                        if "股票" in str(f.get("FTYPE", "")) or "混合" in str(f.get("FTYPE", ""))]
        return {
            "recent_30_count": len(funds),
            "equity_count": len(equity_funds),
            "equity_ratio_pct": round(len(equity_funds) / max(len(funds), 1) * 100, 1),
            "interpretation": ("偏股型新发月规模 >500 亿 = 增量资金进场；"
                              "<200 亿 = 渠道清淡，市场底部信号之一"),
        }
    except Exception as exc:
        print(f"⚠️ 新发基金: {exc}", file=sys.stderr)
        return None


def to_markdown(limit_up, southbound, etf_flow, new_fund):
    lines = []
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines.append("# A 股资金面与市场情绪\n")
    lines.append(f"**数据采集时间**: {ts}")
    lines.append("📎 **信源API**: 东财 datacenter API (涨跌停/南向/ETF资金流) + 天天基金新发 API\n")
    lines.append("---\n")

    # 1. 涨跌停
    lines.append("## 1. 涨跌停统计 — 短线情绪温度计\n")
    if limit_up:
        lines.append(f"- **日期**: {limit_up['date']}")
        lines.append(f"- **涨停总数**: **{limit_up['limit_up_count']}** 只")
        lines.append(f"- **炸板数**: {limit_up['broken_count']} 只")
        lines.append(f"- **炸板率**: {limit_up['broken_rate_pct']}%")
        lines.append(f"- **最高连板高度**: {limit_up['max_consecutive']} 板")
        if limit_up.get("consecutive_distribution"):
            lines.append("- **连板分布**：")
            for n, cnt in limit_up["consecutive_distribution"].items():
                lines.append(f"  - {n} 板：{cnt} 只")
        lines.append(f"\n> {limit_up['interpretation']}\n")
    else:
        lines.append("⚠️ 涨跌停数据获取失败（非交易日 / 接口受限）\n")

    # 2. 南向资金
    lines.append("## 2. 港股通南向资金 — 风险偏好修复入口\n")
    if southbound:
        lines.append(f"- **最新交易日**: {southbound['latest_date']}")
        lines.append(f"- **当日净流入**: {southbound['latest_net_yi']:+.2f} 亿元")
        lines.append(f"- **周累计净流入**: {southbound['week_sum_yi']:+.2f} 亿元")
        lines.append(f"- **月累计净流入**: {southbound['month_sum_yi']:+.2f} 亿元")
        lines.append(f"\n> {southbound['interpretation']}\n")
    else:
        lines.append("⚠️ 南向资金数据获取失败\n")

    # 3. ETF 资金流
    lines.append("## 3. ETF 资金净流入 TOP — 主题资金倾向\n")
    if etf_flow:
        lines.append(f"- **当日全市场 ETF 数量**: {etf_flow['total_count']} 只")
        lines.append("\n### 净流入 TOP 10\n")
        lines.append("| # | 代码 | 名称 | 净流入(亿) | 涨跌幅 |")
        lines.append("|---|------|------|----------|--------|")
        for i, t in enumerate(etf_flow["net_inflow_top"][:10], 1):
            lines.append(f"| {i} | {t['code']} | {t['name']} | "
                        f"{t['net_inflow_yi']:+.2f} | {t['change_pct']}% |")
        lines.append("\n### 净流出 TOP 10\n")
        lines.append("| # | 代码 | 名称 | 净流出(亿) | 涨跌幅 |")
        lines.append("|---|------|------|----------|--------|")
        for i, t in enumerate(etf_flow["net_outflow_top"][:10], 1):
            lines.append(f"| {i} | {t['code']} | {t['name']} | "
                        f"{t['net_outflow_yi']:+.2f} | {t['change_pct']}% |")
        lines.append(f"\n> {etf_flow['interpretation']}\n")
    else:
        lines.append("⚠️ ETF 资金流数据获取失败\n")

    # 4. 新发基金
    lines.append("## 4. 偏股型基金新发 — 增量资金渠道\n")
    if new_fund:
        if "note" in new_fund:
            lines.append(f"⚠️ {new_fund['note']}")
            lines.append(f"备选：`web_fetch('{new_fund.get('fallback_url', '')}', '提取近 30 天偏股新发汇总')`")
        else:
            lines.append(f"- **近 30 天新发基金总数**: {new_fund['recent_30_count']}")
            lines.append(f"- **其中偏股型**: {new_fund['equity_count']} 只（{new_fund['equity_ratio_pct']}%）")
            lines.append(f"\n> {new_fund['interpretation']}")
        lines.append("")
    else:
        lines.append("⚠️ 新发基金数据获取失败\n")

    # 5. 综合
    lines.append("## 5. 综合研判 — TACO / 风险偏好修复触发\n")
    lines.append("| 信号维度 | 风险偏好回升（TACO 触发） | 风险偏好回落 |")
    lines.append("|---------|--------------------------|------------|")
    lines.append("| 涨停数 | >80 持续 + 连板高度 ≥4 | <40 + 炸板率 >50% |")
    lines.append("| 南向月累计 | 持续 >500 亿 | 持续净流出 |")
    lines.append("| ETF 流入主题 | 集中流入成长/科技 | 集中流入红利/债券 ETF |")
    lines.append("| 偏股新发 | 月规模 >500 亿 | 月规模 <200 亿 |")
    lines.append("\n**3+ 维多头 → 风险偏好修复确认 → TACO 主题包配置启动；"
                 "3+ 维空头 → 触发反向风险（防御仓位需保留）**\n")

    lines.append("---\n")
    lines.append("## 数据信源\n")
    lines.append("- **东财 push2ex 涨跌停 API** — https://push2ex.eastmoney.com/getTopicZTPool")
    lines.append("- **东财 datacenter 沪深港通 API** — RPT_MUTUAL_DEAL_HISTORY")
    lines.append("- **东财 push2 ETF 资金流 API** — https://push2.eastmoney.com/api/qt/clist/get")
    lines.append("- **天天基金新发 API** — https://fundact.eastmoney.com/api/Fund/")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="A 股资金面与情绪指标采集")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--limit-up", action="store_true")
    parser.add_argument("--southbound", action="store_true")
    parser.add_argument("--etf-flow", action="store_true")
    parser.add_argument("--new-fund", action="store_true")
    parser.add_argument("--output", help="Markdown 输出路径")
    parser.add_argument("--json", help="JSON 数据输出")
    args = parser.parse_args()

    if not any([args.all, args.limit_up, args.southbound, args.etf_flow, args.new_fund]):
        parser.print_help()
        return 1

    limit_up = fetch_limit_up_count() if (args.all or args.limit_up) else None
    southbound = fetch_southbound_flow() if (args.all or args.southbound) else None
    etf_flow = fetch_etf_flow() if (args.all or args.etf_flow) else None
    new_fund = fetch_new_fund_issuance() if (args.all or args.new_fund) else None

    md = to_markdown(limit_up, southbound, etf_flow, new_fund)

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
            "limit_up": limit_up, "southbound": southbound,
            "etf_flow": etf_flow, "new_fund": new_fund,
            "collected_at": datetime.now().isoformat(),
        }, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        print(f"✅ JSON: {json_path}")

    if not any([limit_up, southbound, etf_flow, new_fund]):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
