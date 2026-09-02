# -*- coding: utf-8 -*-
"""
CFFEX Position Scraper — 中金所股指期货 / 国债期货 前 20 席位多空持仓抓取
                         （faces/资金面.md + market_regime_signals 资金面 配套, P2 锦上添花）

为什么需要：
  1. 中金所每日盘后公布股指期货(IF/IH/IC/IM)和国债期货(T/TF/TS/TL)前 20 席位的多/空/净持仓,
     可以反映机构对大盘 / 板块 / 利率方向的真实定位变化, 是大盘择时的辅助信号。
  2. 净空持仓显著提升 / 净多持仓显著提升 → 反映期货市场对现货大盘的对冲或方向判断。
  3. 与 R8-R18 信源诚信铁律一致, 仅使用 A 类一手公开源:
       - 中金所官网每日席位持仓 (http://www.cffex.com.cn/sj/ccpm/)
       - HTML / TXT 公开报告, 免费可访问

注意：
  - 本工具不与个股代码挂钩, 而是按合约/品种聚合, 输出大盘择时辅助信号
  - 中金所每个交易日 16:00 后发布前一交易日数据
  - 调用方应仅作 P2 信号使用, 不应作为个股主决策依据

输出：FinancialData/cffex_position_{date}.json
  {
    "metadata": {...},
    "summary": {
       "trade_date": "2026-05-27",
       "if_net_position": -1234,        # IF 沪深300 前 20 席位净持仓(多-空)
       "ih_net_position": 567,
       "ic_net_position": -890,
       "im_net_position": 234,
       "if_net_change":  -456,          # 较前一日变化
       "signals": ["股指期货空头加仓(IF净空+456)"]
    },
    "products": {
       "IF": {"contract": "IF2606", "long_top20": [...], "short_top20": [...]},
       "IH": {...},
       "IC": {...},
       "IM": {...}
    }
  }

v1.9 合规性：中金所官网公开数据, A 类一手源

用法：
  python cffex_position_scraper.py                     # 抓最新交易日
  python cffex_position_scraper.py --date 2026-05-27   # 指定日期
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import requests
except ImportError:
    print("ERROR: requests required.", file=sys.stderr)
    sys.exit(1)

TIMEOUT = 30

# 中金所官网两套接口（主备）
# 主：HTML 持仓排名页 http://www.cffex.com.cn/sj/ccpm/{YYYYMM}/{DD}/{PRODUCT}_1.html
# 备：TXT 文件 http://www.cffex.com.cn/sj/ccpm/{YYYYMM}/{DD}/{PRODUCT}.txt
CFFEX_HTML = "http://www.cffex.com.cn/sj/ccpm/{ym}/{d}/{prod}_1.html"
CFFEX_TXT = "http://www.cffex.com.cn/sj/ccpm/{ym}/{d}/{prod}.txt"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "http://www.cffex.com.cn/",
    "Accept": "text/html,application/xhtml+xml,*/*",
}

# 主流股指 / 国债期货品种
PRODUCTS = ["IF", "IH", "IC", "IM", "T", "TF", "TS", "TL"]


def _last_trade_date() -> str:
    """简单回退: 周末或周一上午回退到上一个工作日"""
    d = datetime.now()
    # 16:30 前数据未发, 回退到前一日
    if d.hour < 16 or (d.hour == 16 and d.minute < 30):
        d = d - timedelta(days=1)
    while d.weekday() >= 5:
        d = d - timedelta(days=1)
    return d.strftime("%Y-%m-%d")


def _fetch_text(url: str) -> str:
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.encoding = r.apparent_encoding or "utf-8"
        if r.status_code == 200 and r.text:
            return r.text
    except Exception:
        return ""
    return ""


def _parse_html_positions(html: str) -> Dict[str, List[Dict[str, Any]]]:
    """解析中金所 HTML 持仓排名页

    页面结构（简化）：
      <table>
        <tr><th>名次<th>会员<th>成交量<th>增减
            <th>会员<th>持买仓量<th>增减
            <th>会员<th>持卖仓量<th>增减
        ...20 行...
      </table>

    返回：{"long_top20": [...], "short_top20": [...]}
    """
    long_list: List[Dict[str, Any]] = []
    short_list: List[Dict[str, Any]] = []

    # 提取所有 <tr>...</tr> 行
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S)
    for row in rows:
        cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S)
        if len(cells) < 10:
            continue
        # 清洗：去除 HTML 标签和空白
        clean = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]
        # 排名列必须是整数
        if not clean[0].isdigit():
            continue
        rank = int(clean[0])
        if rank < 1 or rank > 20:
            continue

        # 持买仓 (列 5/6/7) 持卖仓 (列 8/9/10)
        try:
            buy_member = clean[4]
            buy_position = int(clean[5].replace(",", "")) if clean[5] else 0
            buy_change = int(clean[6].replace(",", "").replace("+", "")) if clean[6] else 0
            sell_member = clean[7]
            sell_position = int(clean[8].replace(",", "")) if clean[8] else 0
            sell_change = int(clean[9].replace(",", "").replace("+", "")) if clean[9] else 0
        except (ValueError, IndexError):
            continue

        if buy_member and buy_position > 0:
            long_list.append({
                "rank": rank,
                "member": buy_member,
                "position": buy_position,
                "change": buy_change,
            })
        if sell_member and sell_position > 0:
            short_list.append({
                "rank": rank,
                "member": sell_member,
                "position": sell_position,
                "change": sell_change,
            })

    return {"long_top20": long_list, "short_top20": short_list}


def _parse_txt_positions(text: str) -> Dict[str, List[Dict[str, Any]]]:
    """中金所 TXT 备用接口解析（CSV 风格, GBK 编码常见）"""
    long_list: List[Dict[str, Any]] = []
    short_list: List[Dict[str, Any]] = []

    lines = text.splitlines()
    # 中金所 TXT 通常每行：合约,排名,会员,成交,增减,会员,持买,增减,会员,持卖,增减
    for line in lines:
        if not line or "," not in line:
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 11:
            continue
        if not parts[1].isdigit():
            continue
        try:
            rank = int(parts[1])
            if rank < 1 or rank > 20:
                continue
            buy_member = parts[5]
            buy_position = int(parts[6].replace("+", "")) if parts[6] else 0
            buy_change = int(parts[7].replace("+", "")) if parts[7] else 0
            sell_member = parts[8]
            sell_position = int(parts[9].replace("+", "")) if parts[9] else 0
            sell_change = int(parts[10].replace("+", "")) if parts[10] else 0
        except (ValueError, IndexError):
            continue

        if buy_member and buy_position > 0:
            long_list.append({
                "rank": rank,
                "member": buy_member,
                "position": buy_position,
                "change": buy_change,
            })
        if sell_member and sell_position > 0:
            short_list.append({
                "rank": rank,
                "member": sell_member,
                "position": sell_position,
                "change": sell_change,
            })

    return {"long_top20": long_list, "short_top20": short_list}


def fetch_product_positions(product: str, date_str: str) -> Dict[str, Any]:
    """抓取单个品种(如 IF)在指定日期的前 20 多空席位"""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    ym = dt.strftime("%Y%m")
    d = dt.strftime("%d")

    # 主：HTML
    html = _fetch_text(CFFEX_HTML.format(ym=ym, d=d, prod=product))
    if html and "<table" in html.lower():
        positions = _parse_html_positions(html)
        if positions["long_top20"] or positions["short_top20"]:
            positions["_source"] = f"cffex::html::{product}"
            return positions

    time.sleep(0.5)

    # 备：TXT
    txt = _fetch_text(CFFEX_TXT.format(ym=ym, d=d, prod=product))
    if txt:
        positions = _parse_txt_positions(txt)
        if positions["long_top20"] or positions["short_top20"]:
            positions["_source"] = f"cffex::txt::{product}"
            return positions

    return {"long_top20": [], "short_top20": [], "_source": "none"}


# ---------- 信号汇总 ----------

NET_THRESHOLD_LARGE = 5000   # 净持仓变化绝对值 > 5000 视为显著
NET_THRESHOLD_HUGE = 10000   # > 10000 视为重大


def compute_signals(products: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    summary: Dict[str, Any] = {}
    signals: List[str] = []

    for prod in ["IF", "IH", "IC", "IM"]:
        data = products.get(prod, {})
        long_total = sum(x.get("position", 0) for x in data.get("long_top20", []))
        short_total = sum(x.get("position", 0) for x in data.get("short_top20", []))
        long_chg = sum(x.get("change", 0) for x in data.get("long_top20", []))
        short_chg = sum(x.get("change", 0) for x in data.get("short_top20", []))

        net_pos = long_total - short_total
        net_chg = long_chg - short_chg

        summary[f"{prod.lower()}_long_position"] = long_total
        summary[f"{prod.lower()}_short_position"] = short_total
        summary[f"{prod.lower()}_net_position"] = net_pos
        summary[f"{prod.lower()}_net_change"] = net_chg

        if net_chg >= NET_THRESHOLD_HUGE:
            signals.append(f"{prod}多头大幅加仓(+{net_chg})")
        elif net_chg <= -NET_THRESHOLD_HUGE:
            signals.append(f"{prod}空头大幅加仓({net_chg})")
        elif net_chg >= NET_THRESHOLD_LARGE:
            signals.append(f"{prod}多头加仓(+{net_chg})")
        elif net_chg <= -NET_THRESHOLD_LARGE:
            signals.append(f"{prod}空头加仓({net_chg})")

    summary["signals"] = signals
    return summary


# ---------- 主入口 ----------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None,
                    help="目标交易日 YYYY-MM-DD, 默认最近一个交易日")
    ap.add_argument("--products", default=None,
                    help=f"逗号分隔品种, 默认全部: {','.join(PRODUCTS)}")
    ap.add_argument("--out", default=None, help="输出路径覆盖")
    args = ap.parse_args()

    date_str = args.date or _last_trade_date()
    prod_list = args.products.split(",") if args.products else PRODUCTS

    print(f"[cffex_position] date={date_str} products={prod_list}")

    products: Dict[str, Dict[str, Any]] = {}
    for prod in prod_list:
        prod = prod.strip().upper()
        if not prod:
            continue
        data = fetch_product_positions(prod, date_str)
        products[prod] = data
        print(f"  - {prod}: long={len(data.get('long_top20', []))}  "
              f"short={len(data.get('short_top20', []))}  src={data.get('_source')}")
        time.sleep(0.4)

    summary = compute_signals(products)
    summary["trade_date"] = date_str

    payload = {
        "metadata": {
            "trade_date": date_str,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "products_requested": prod_list,
            "data_sources": [
                "cffex::sj/ccpm/{ym}/{d}/{prod}_1.html (primary)",
                "cffex::sj/ccpm/{ym}/{d}/{prod}.txt (fallback)",
            ],
            "compliance": "v1.9 A class primary source (CFFEX official)",
        },
        "summary": summary,
        "products": products,
    }

    out_path = (
        Path(args.out) if args.out else
        Path(__file__).resolve().parents[3] / "FinancialData" /
        f"cffex_position_{date_str.replace('-', '')}.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ok] wrote {out_path}")
    print(f"[summary] signals={summary.get('signals')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
