#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
市场情绪微观数据采集脚本 — ETF 顾问团队内置数据引擎
功能：采集全市场微观情绪指标，包括：
  - 全市场涨跌家数比（上涨/下跌/平盘家数）
  - 涨停/跌停家数 + 炸板率
  - 连板高度（最高连板梯队）
  - 昨日涨停今日表现（平均涨幅、晋级率）
  - 全市场破净率（破净股数量/占比）
  - 全市场均线统计（站上/跌破200日均线的比例）
数据源：
  - 东方财富 Push2 clist (push2.eastmoney.com) — 全市场实时行情
  - 东方财富 DataCenter (datacenter-web.eastmoney.com) — 涨停/跌停/破净统计
信源对应：
  - market_regime_signals.md 底部/顶部信号（情绪信号②③）
  - analysis_framework.md §四模块1 大盘整体环境与择时

用法：
  python market_sentiment_scraper.py --all                  # 全部指标
  python market_sentiment_scraper.py --breadth              # 涨跌家数
  python market_sentiment_scraper.py --limit-stats          # 涨跌停+炸板率
  python market_sentiment_scraper.py --net-break            # 破净率
  python market_sentiment_scraper.py --all --json           # JSON输出
  python market_sentiment_scraper.py --all -o FinancialData/market_sentiment.md

输出：JSON 或 Markdown 格式
"""

import sys
import json
import argparse
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

# --------------------------------------------------------------------------- #
#  常量
# --------------------------------------------------------------------------- #

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://quote.eastmoney.com/",
}

HEADERS_DC = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://data.eastmoney.com/",
}

PUSH2_URL = "https://push2.eastmoney.com/api/qt/clist/get"
DATACENTER_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"
TIMEOUT = 20


def _safe_float(v, default=None):
    if v is None or v == "-" or v == "":
        return default
    try:
        return float(v)
    except (ValueError, TypeError):
        return default


def _safe_int(v, default=0):
    if v is None:
        return default
    try:
        return int(v)
    except (ValueError, TypeError):
        return default


# =========================================================================== #
#  Part 1: 全市场涨跌家数（Market Breadth）
# =========================================================================== #

def fetch_market_breadth() -> Dict[str, Any]:
    """从东方财富 Push2 获取全市场涨跌统计
    通过一次全量采集后内存分档统计（避免多次API调用）"""
    try:
        # 一次性全量采集所有股票涨跌幅
        all_pcts = []
        page = 1
        page_size = 5000
        while True:
            p = {
                "pn": page, "pz": page_size, "po": 1, "np": 1, "fltt": 2, "invt": 2,
                "fid": "f3",
                "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048",
                "fields": "f3",
                "ut": "fa5fd1943c7b386f172d6893dbfba10b",
            }
            resp = requests.get(PUSH2_URL, params=p, headers=HEADERS, timeout=TIMEOUT)
            d = resp.json().get("data", {})
            items = d.get("diff", [])
            if not items:
                break
            for item in items:
                pct = _safe_float(item.get("f3"))
                if pct is not None:
                    all_pcts.append(pct)
            total = _safe_int(d.get("total"), 0)
            if page * page_size >= total:
                break
            page += 1

        # 内存中一次性统计涨跌家数
        total = len(all_pcts)
        up_count = sum(1 for p in all_pcts if p > 0)
        down_count = sum(1 for p in all_pcts if p < 0)
        flat_count = total - up_count - down_count

        return {
            "全市场总股票数": total,
            "上涨家数": up_count,
            "下跌家数": down_count,
            "平盘家数": flat_count,
            "涨跌比": round(up_count / max(down_count, 1), 2),
            "上涨占比(%)": round(up_count / max(total, 1) * 100, 1),
            "情绪判定": _assess_breadth(up_count, down_count, total),
            "数据源": "东方财富Push2",
            "采集时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    except Exception as e:
        return {"error": f"涨跌家数采集失败: {e}"}


def _count_by_pct_range(pct_min=None, pct_max=None) -> int:
    """统计指定涨跌幅范围内的股票数量"""
    try:
        # 利用 pn=1,pz=1 + 筛选条件获取 total
        flt_parts = []
        if pct_min is not None:
            flt_parts.append(f"(f3>{pct_min})")
        if pct_max is not None:
            flt_parts.append(f"(f3<{pct_max})")
        flt = "+".join(flt_parts) if flt_parts else ""

        params = {
            "pn": 1, "pz": 1, "po": 1, "np": 1, "fltt": 2, "invt": 2,
            "fid": "f3",
            "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048",
            "fields": "f12",
            "ut": "fa5fd1943c7b386f172d6893dbfba10b",
        }
        if flt:
            params["fid"] = "f3"

        # 东方财富 clist 不直接支持 pct filter，改用分页方式统计
        # 换用全量小批次采集
        count = 0
        page = 1
        page_size = 5000  # 最大允许
        while True:
            p = {
                "pn": page, "pz": page_size, "po": 1, "np": 1, "fltt": 2, "invt": 2,
                "fid": "f3",
                "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048",
                "fields": "f3",
                "ut": "fa5fd1943c7b386f172d6893dbfba10b",
            }
            resp = requests.get(PUSH2_URL, params=p, headers=HEADERS, timeout=TIMEOUT)
            d = resp.json().get("data", {})
            items = d.get("diff", [])
            if not items:
                break
            for item in items:
                pct = _safe_float(item.get("f3"))
                if pct is None:
                    continue
                if pct_min is not None and pct_max is not None:
                    if pct_min <= pct <= pct_max:
                        count += 1
                elif pct_min is not None:
                    if pct >= pct_min:
                        count += 1
                elif pct_max is not None:
                    if pct <= pct_max:
                        count += 1
            total = _safe_int(d.get("total"), 0)
            if page * page_size >= total:
                break
            page += 1
        return count
    except Exception:
        return 0


def _assess_breadth(up: int, down: int, total: int) -> str:
    if up >= 3000:
        return "▲ 正向（上涨≥3000家，可积极操作）"
    elif up >= 2000:
        return "► 中性偏积极"
    elif up <= 1500:
        return "▼ 负向（上涨≤1500家，不宜操作）"
    else:
        return "► 中性"


# =========================================================================== #
#  Part 2: 涨停/跌停统计 + 连板高度 + 炸板率
# =========================================================================== #

def fetch_limit_stats() -> Dict[str, Any]:
    """从东方财富数据中心获取涨停/跌停统计"""
    try:
        result = {}

        # 涨停统计
        limit_up = _fetch_limit_pool("涨停")
        result["涨停家数"] = limit_up.get("count", 0)
        result["涨停详情"] = limit_up

        # 跌停统计
        limit_down = _fetch_limit_pool("跌停")
        result["跌停家数"] = limit_down.get("count", 0)

        # 炸板率（曾涨停但收盘未封住的比例）
        failed_up = _fetch_failed_limit_up()
        total_touched = result["涨停家数"] + failed_up.get("count", 0)
        result["曾触涨停家数"] = total_touched
        result["炸板家数"] = failed_up.get("count", 0)
        result["炸板率(%)"] = round(failed_up.get("count", 0) / max(total_touched, 1) * 100, 1)

        # 连板统计
        consecutive = _fetch_consecutive_limit()
        result["连板统计"] = consecutive
        result["最高连板"] = consecutive.get("最高连板", 0)

        # 昨日涨停今日表现
        yesterday_perf = _fetch_yesterday_limit_perf()
        result["昨涨停今表现"] = yesterday_perf

        # 情绪判定
        result["涨跌停情绪"] = _assess_limit_sentiment(result)
        result["数据源"] = "东方财富DataCenter"
        result["采集时间"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return result
    except Exception as e:
        return {"error": f"涨跌停统计采集失败: {e}"}


def _fetch_limit_pool(direction: str) -> Dict[str, Any]:
    """获取涨停/跌停池"""
    try:
        report = "RPT_LIMITUP_BASICINFO" if direction == "涨停" else "RPT_LIMITDOWN_BASICINFO"
        params = {
            "reportName": report,
            "columns": "SECURITY_CODE,SECURITY_NAME_ABBR,CHANGE_RATE,LATEST_PRICE,FIRST_LIMIT_TIME,LAST_LIMIT_TIME,LIMIT_UP_DAYS",
            "sortColumns": "CHANGE_RATE",
            "sortTypes": "-1",
            "pageSize": 500,
            "pageNumber": 1,
            "source": "WEB", "client": "WEB",
        }
        resp = requests.get(DATACENTER_URL, params=params, headers=HEADERS_DC, timeout=TIMEOUT)
        data = resp.json()
        if data.get("success") and data.get("result"):
            records = data["result"].get("data", [])
            count = data["result"].get("count", len(records))
            return {"count": count, "records_sample": records[:5]}
        return {"count": 0}
    except Exception:
        return {"count": 0}


def _fetch_failed_limit_up() -> Dict[str, Any]:
    """获取炸板（曾涨停但收盘未封住）的股票数量"""
    try:
        params = {
            "reportName": "RPT_LIMITUP_FAILEDINFO",
            "columns": "SECURITY_CODE,SECURITY_NAME_ABBR,CHANGE_RATE",
            "sortColumns": "CHANGE_RATE",
            "sortTypes": "-1",
            "pageSize": 500,
            "pageNumber": 1,
            "source": "WEB", "client": "WEB",
        }
        resp = requests.get(DATACENTER_URL, params=params, headers=HEADERS_DC, timeout=TIMEOUT)
        data = resp.json()
        if data.get("success") and data.get("result"):
            count = data["result"].get("count", 0)
            return {"count": count}
        return {"count": 0}
    except Exception:
        return {"count": 0}


def _fetch_consecutive_limit() -> Dict[str, Any]:
    """获取连板统计（连续涨停天数分布）"""
    try:
        params = {
            "reportName": "RPT_LIMITUP_BASICINFO",
            "columns": "SECURITY_CODE,SECURITY_NAME_ABBR,LIMIT_UP_DAYS,CHANGE_RATE",
            "filter": "(LIMIT_UP_DAYS>=2)",
            "sortColumns": "LIMIT_UP_DAYS",
            "sortTypes": "-1",
            "pageSize": 200,
            "pageNumber": 1,
            "source": "WEB", "client": "WEB",
        }
        resp = requests.get(DATACENTER_URL, params=params, headers=HEADERS_DC, timeout=TIMEOUT)
        data = resp.json()
        if not data.get("success") or not data.get("result"):
            return {"最高连板": 0, "连板梯队": {}}

        records = data["result"].get("data", [])
        if not records:
            return {"最高连板": 0, "连板梯队": {}}

        # 统计连板梯队
        tier_count = {}
        max_days = 0
        for rec in records:
            days = _safe_int(rec.get("LIMIT_UP_DAYS"), 0)
            if days > max_days:
                max_days = days
            tier_count[days] = tier_count.get(days, 0) + 1

        # 按天数降序排列
        sorted_tiers = dict(sorted(tier_count.items(), reverse=True))

        return {
            "最高连板": max_days,
            "连板梯队": sorted_tiers,
            "连板总家数": len(records),
            "梯队完整性": "完整" if max_days >= 5 and len(sorted_tiers) >= 3 else "断层",
        }
    except Exception:
        return {"最高连板": 0, "连板梯队": {}}


def _fetch_yesterday_limit_perf() -> Dict[str, Any]:
    """获取昨日涨停今日表现（通过DataCenter打板统计）"""
    try:
        params = {
            "reportName": "RPT_LIMITUP_STAT",
            "columns": "TRADE_DATE,ALL_COUNT,UP_COUNT,DOWN_COUNT,FLAT_COUNT,AVG_CHANGE_RATE,UP_RATE",
            "sortColumns": "TRADE_DATE",
            "sortTypes": "-1",
            "pageSize": 5,
            "pageNumber": 1,
            "source": "WEB", "client": "WEB",
        }
        resp = requests.get(DATACENTER_URL, params=params, headers=HEADERS_DC, timeout=TIMEOUT)
        data = resp.json()
        if data.get("success") and data.get("result"):
            records = data["result"].get("data", [])
            if records:
                latest = records[0]
                return {
                    "统计日期": str(latest.get("TRADE_DATE", ""))[:10],
                    "昨涨停总数": _safe_int(latest.get("ALL_COUNT")),
                    "今上涨家数": _safe_int(latest.get("UP_COUNT")),
                    "今下跌家数": _safe_int(latest.get("DOWN_COUNT")),
                    "平均涨幅(%)": _safe_float(latest.get("AVG_CHANGE_RATE")),
                    "晋级率(%)": _safe_float(latest.get("UP_RATE")),
                }
        return {"error": "无昨涨停统计数据"}
    except Exception as e:
        return {"error": f"昨涨停统计失败: {e}"}


def _assess_limit_sentiment(stats: Dict) -> str:
    up = stats.get("涨停家数", 0)
    down = stats.get("跌停家数", 0)
    burst_rate = stats.get("炸板率(%)", 50)
    max_board = stats.get("最高连板", 0)

    signals = []
    if up >= 50 and down <= 5:
        signals.append("▲ 涨停活跃+跌停极少")
    elif up <= 20 and down >= 10:
        signals.append("▼ 涨停萎缩+跌停增多")

    if burst_rate <= 30:
        signals.append("▲ 炸板率低（封板强度高）")
    elif burst_rate >= 50:
        signals.append("▼ 炸板率高（封板意愿弱）")

    if max_board >= 5:
        signals.append("▲ 连板高度充足（梯队完整）")
    elif max_board <= 3:
        signals.append("▼ 连板高度不足（市场缺乏赚钱效应）")

    if not signals:
        return "► 中性"
    return " | ".join(signals)


# =========================================================================== #
#  Part 3: 全市场破净率
# =========================================================================== #

def fetch_net_break_stats() -> Dict[str, Any]:
    """统计全市场破净股数量和占比"""
    try:
        # 方法：全A股中 PB < 1 的数量
        # 先获取全A总数
        total_params = {
            "pn": 1, "pz": 1, "po": 1, "np": 1, "fltt": 2, "invt": 2,
            "fid": "f3",
            "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048",
            "fields": "f12",
            "ut": "fa5fd1943c7b386f172d6893dbfba10b",
        }
        resp = requests.get(PUSH2_URL, params=total_params, headers=HEADERS, timeout=TIMEOUT)
        total = _safe_int(resp.json().get("data", {}).get("total"), 0)

        # 统计 PB < 1 的数量 — 通过全量分页
        break_count = 0
        page = 1
        page_size = 5000
        while True:
            params = {
                "pn": page, "pz": page_size, "po": 1, "np": 1, "fltt": 2, "invt": 2,
                "fid": "f23",  # 按PB排序
                "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048",
                "fields": "f23",  # PB
                "ut": "fa5fd1943c7b386f172d6893dbfba10b",
            }
            resp = requests.get(PUSH2_URL, params=params, headers=HEADERS, timeout=TIMEOUT)
            d = resp.json().get("data", {})
            items = d.get("diff", [])
            if not items:
                break
            for item in items:
                pb = _safe_float(item.get("f23"))
                if pb is not None and 0 < pb < 1:
                    break_count += 1
            pg_total = _safe_int(d.get("total"), 0)
            if page * page_size >= pg_total:
                break
            page += 1

        ratio = round(break_count / max(total, 1) * 100, 1)

        return {
            "全市场总数": total,
            "破净股数量": break_count,
            "破净率(%)": ratio,
            "底部信号": "▲ 触发" if ratio >= 15 else ("► 接近" if ratio >= 10 else "⚪ 未触发"),
            "说明": "破净率≥15% 为历史级底部情绪信号（参考market_regime_signals.md）",
            "数据源": "东方财富Push2",
            "采集时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    except Exception as e:
        return {"error": f"破净率统计失败: {e}"}


# =========================================================================== #
#  Part 4: 均线统计（站上/跌破200日均线比例）
# =========================================================================== #

def fetch_ma_stats() -> Dict[str, Any]:
    """统计全市场站上/跌破200日均线的比例
    底部信号：80%以上个股处于200日均线以下"""
    try:
        # 遍历全A，判断最新价 vs 200日均线
        above_count = 0
        below_count = 0
        total_valid = 0
        page = 1
        page_size = 5000
        while True:
            params = {
                "pn": page, "pz": page_size, "po": 1, "np": 1, "fltt": 2, "invt": 2,
                "fid": "f3",
                "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048",
                "fields": "f2,f260",  # f2=最新价, f260=250日均线(近似年线)
                "ut": "fa5fd1943c7b386f172d6893dbfba10b",
            }
            resp = requests.get(PUSH2_URL, params=params, headers=HEADERS, timeout=TIMEOUT)
            d = resp.json().get("data", {})
            items = d.get("diff", [])
            if not items:
                break
            for item in items:
                price = _safe_float(item.get("f2"))
                ma250 = _safe_float(item.get("f260"))
                if price is not None and ma250 is not None and price > 0 and ma250 > 0:
                    total_valid += 1
                    if price >= ma250:
                        above_count += 1
                    else:
                        below_count += 1
            pg_total = _safe_int(d.get("total"), 0)
            if page * page_size >= pg_total:
                break
            page += 1

        below_pct = round(below_count / max(total_valid, 1) * 100, 1)

        return {
            "有效统计股票数": total_valid,
            "站上250日均线": above_count,
            "跌破250日均线": below_count,
            "跌破250日均线占比(%)": below_pct,
            "底部信号": "▲ 触发" if below_pct >= 80 else ("► 接近" if below_pct >= 70 else "⚪ 未触发"),
            "说明": "80%以上个股跌破年线 = 技术面底部信号（参考market_regime_signals.md）",
            "数据源": "东方财富Push2",
            "采集时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    except Exception as e:
        return {"error": f"均线统计失败: {e}"}


# =========================================================================== #
#  汇总 & Markdown 格式化
# =========================================================================== #

def fetch_all_sentiment() -> Dict[str, Any]:
    """并行采集全部情绪指标"""
    results = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {
            pool.submit(fetch_market_breadth): "涨跌家数",
            pool.submit(fetch_limit_stats): "涨跌停统计",
            pool.submit(fetch_net_break_stats): "破净率",
            pool.submit(fetch_ma_stats): "均线统计",
        }
        for future in as_completed(futures):
            key = futures[future]
            try:
                results[key] = future.result()
            except Exception as e:
                results[key] = {"error": str(e)}
    return results


def format_md(data: Dict[str, Any]) -> str:
    lines = [
        "# 市场情绪微观数据",
        f"**采集时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**数据源**: 东方财富 Push2 + DataCenter",
        "", "---", "",
    ]

    # 1. 涨跌家数
    breadth = data.get("涨跌家数", {})
    lines.append("## 一、全市场涨跌家数")
    if "error" in breadth:
        lines.append(f"⚠ {breadth['error']}")
    else:
        lines.append(f"| 指标 | 数值 |")
        lines.append(f"|------|------|")
        for k, v in breadth.items():
            if k not in ("数据源", "采集时间"):
                lines.append(f"| {k} | {v} |")
    lines.append("")

    # 2. 涨跌停+炸板率+连板
    limit = data.get("涨跌停统计", {})
    lines.append("## 二、涨跌停统计 + 连板高度 + 炸板率")
    if "error" in limit:
        lines.append(f"⚠ {limit['error']}")
    else:
        lines.append("| 指标 | 数值 |")
        lines.append("|------|------|")
        lines.append(f"| 涨停家数 | {limit.get('涨停家数', '—')} |")
        lines.append(f"| 跌停家数 | {limit.get('跌停家数', '—')} |")
        lines.append(f"| 曾触涨停家数 | {limit.get('曾触涨停家数', '—')} |")
        lines.append(f"| 炸板家数 | {limit.get('炸板家数', '—')} |")
        lines.append(f"| 炸板率(%) | {limit.get('炸板率(%)', '—')} |")
        lines.append(f"| 最高连板 | {limit.get('最高连板', '—')} |")

        consec = limit.get("连板统计", {})
        if consec.get("连板梯队"):
            lines.append(f"| 连板梯队 | {consec['连板梯队']} |")
            lines.append(f"| 梯队完整性 | {consec.get('梯队完整性', '—')} |")

        lines.append(f"| **涨跌停情绪** | {limit.get('涨跌停情绪', '—')} |")

        # 昨涨停今表现
        yest = limit.get("昨涨停今表现", {})
        if "error" not in yest:
            lines.append("")
            lines.append("### 昨日涨停今日表现")
            lines.append("| 指标 | 数值 |")
            lines.append("|------|------|")
            for k, v in yest.items():
                lines.append(f"| {k} | {v} |")
    lines.append("")

    # 3. 破净率
    net_break = data.get("破净率", {})
    lines.append("## 三、全市场破净率")
    if "error" in net_break:
        lines.append(f"⚠ {net_break['error']}")
    else:
        lines.append("| 指标 | 数值 |")
        lines.append("|------|------|")
        for k, v in net_break.items():
            if k not in ("数据源", "采集时间"):
                lines.append(f"| {k} | {v} |")
    lines.append("")

    # 4. 均线统计
    ma = data.get("均线统计", {})
    lines.append("## 四、均线统计（250日/年线）")
    if "error" in ma:
        lines.append(f"⚠ {ma['error']}")
    else:
        lines.append("| 指标 | 数值 |")
        lines.append("|------|------|")
        for k, v in ma.items():
            if k not in ("数据源", "采集时间"):
                lines.append(f"| {k} | {v} |")
    lines.append("")

    # 综合情绪判定
    lines.append("## ⭐ 综合情绪判定")
    lines.append(_comprehensive_sentiment(data))

    return "\n".join(lines)


def _comprehensive_sentiment(data: Dict) -> str:
    signals = []
    breadth = data.get("涨跌家数", {})
    if breadth.get("上涨家数", 0) >= 3000:
        signals.append("▲ 涨跌家数正向")
    elif breadth.get("上涨家数", 9999) <= 1500:
        signals.append("▼ 涨跌家数负向")

    limit = data.get("涨跌停统计", {})
    if limit.get("涨停家数", 0) >= 50 and limit.get("跌停家数", 999) <= 5:
        signals.append("▲ 涨跌停正向")
    if limit.get("炸板率(%)", 50) <= 30:
        signals.append("▲ 炸板率正向")
    elif limit.get("炸板率(%)", 0) >= 50:
        signals.append("▼ 炸板率负向")

    net_break = data.get("破净率", {})
    if net_break.get("破净率(%)", 0) >= 15:
        signals.append("▲ 破净率触发底部信号")

    ma = data.get("均线统计", {})
    if ma.get("跌破250日均线占比(%)", 0) >= 80:
        signals.append("▲ 均线统计触发底部信号")

    if not signals:
        return "整体情绪中性，无明显极端信号。"
    return "\n".join(f"- {s}" for s in signals)


# --------------------------------------------------------------------------- #
#  CLI 入口
# --------------------------------------------------------------------------- #

def main():
    parser = argparse.ArgumentParser(description="市场情绪微观数据采集")
    parser.add_argument("--all", "-a", action="store_true", help="全部指标")
    parser.add_argument("--breadth", action="store_true", help="涨跌家数")
    parser.add_argument("--limit-stats", action="store_true", help="涨跌停+炸板率+连板")
    parser.add_argument("--net-break", action="store_true", help="破净率")
    parser.add_argument("--ma-stats", action="store_true", help="均线统计")
    parser.add_argument("--json", action="store_true", help="JSON输出")
    parser.add_argument("--output", "-o", default="", help="输出到文件")
    args = parser.parse_args()

    flags = [args.breadth, args.limit_stats, args.net_break, args.ma_stats]
    if not args.all and not any(flags):
        args.all = True

    if args.all:
        results = fetch_all_sentiment()
    else:
        results = {}
        if args.breadth:
            results["涨跌家数"] = fetch_market_breadth()
        if args.limit_stats:
            results["涨跌停统计"] = fetch_limit_stats()
        if args.net_break:
            results["破净率"] = fetch_net_break_stats()
        if args.ma_stats:
            results["均线统计"] = fetch_ma_stats()

    if args.json:
        output = json.dumps(results, ensure_ascii=False, indent=2, default=str)
    else:
        output = format_md(results)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"已保存到 {args.output}", file=sys.stderr)
    else:
        _print_utf8(output)


def _print_utf8(text: str):
    """Windows 兼容的 UTF-8 输出（避免 GBK 编码错误）。"""
    try:
        print(text)
    except UnicodeEncodeError:
        sys.stdout.buffer.write(text.encode("utf-8"))
        sys.stdout.buffer.write(b"\n")
        sys.stdout.buffer.flush()


if __name__ == "__main__":
    main()
