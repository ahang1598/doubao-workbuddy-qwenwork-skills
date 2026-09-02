#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
指数估值与择时数据采集脚本
==========================
采集指数估值(PE/PB/股息率/历史分位)、股债性价比等核心择时数据，
直接对应买卖信号的量化判断。

数据源：
  - 中证指数官网 (csi.csindex.cn) — 指数估值(PE/PB/股息率)
  - 东方财富 DataCenter — 指数估值历史/市场情绪
  - 集思录 (jisilu.cn) — ETF溢价率（辅助）

支持的常用指数：
  沪深300(000300), 中证500(000905), 中证1000(000852),
  创业板指(399006), 科创50(000688), 上证50(000016),
  中证全指(000985), 中证红利(000922), 恒生指数(HSI) 等

用法：
  python fund_valuation_scraper.py 000300                # 沪深300估值
  python fund_valuation_scraper.py 000300 --json         # JSON输出
  python fund_valuation_scraper.py 000300 --output val.json --json
  python fund_valuation_scraper.py --equity-bond-ratio   # 股债性价比
"""

import re
import sys
import json
import time
import argparse
import requests
from datetime import datetime
from typing import Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

# --------------------------------------------------------------------------- #
#  常量
# --------------------------------------------------------------------------- #

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

HEADERS_EAST = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://quote.eastmoney.com/",
}

TIMEOUT = 15

# 常用指数代码映射（用于中证指数官网查询）
INDEX_MAP = {
    "000300": {"name": "沪深300", "market": "sh"},
    "000905": {"name": "中证500", "market": "sh"},
    "000852": {"name": "中证1000", "market": "sz"},
    "399006": {"name": "创业板指", "market": "sz"},
    "000688": {"name": "科创50", "market": "sh"},
    "000016": {"name": "上证50", "market": "sh"},
    "000985": {"name": "中证全指", "market": "sh"},
    "000922": {"name": "中证红利", "market": "sh"},
    "399001": {"name": "深证成指", "market": "sz"},
    "000001": {"name": "上证指数", "market": "sh"},
    "399852": {"name": "中证1000", "market": "sz"},
}


def _safe_float(v, default=None):
    if v is None or v == "-" or v == "" or v == "None" or v == "--":
        return default
    try:
        return float(str(v).replace(",", ""))
    except (ValueError, TypeError):
        return default


# --------------------------------------------------------------------------- #
#  1. 中证指数官网 — 指数估值数据
# --------------------------------------------------------------------------- #

def fetch_csi_valuation(index_code: str) -> Dict[str, Any]:
    """从中证指数官网获取指数估值（PE/PB/股息率）"""
    try:
        # 中证指数官网 API
        url = "https://csi-web-dev.oss-cn-shanghai-finance-1-pub.aliyuncs.com/static/html/csindex/public/uploads/file/autofile/indicator/"
        # 构建文件名
        filename = f"{index_code}indicator.json"
        resp = requests.get(f"{url}{filename}", headers=HEADERS, timeout=TIMEOUT)

        if resp.status_code == 200:
            data = resp.json()
            if data:
                latest = data[-1] if isinstance(data, list) else data
                return {
                    "source": "中证指数",
                    "index_code": index_code,
                    "index_name": INDEX_MAP.get(index_code, {}).get("name", index_code),
                    "date": latest.get("tradedate", ""),
                    "PE_TTM": _safe_float(latest.get("pe_ttm")),
                    "PB_LF": _safe_float(latest.get("pb_lf")),
                    "股息率": _safe_float(latest.get("dividend_yield_ratio")),
                }
    except Exception:
        pass
    return {"error": "中证指数官网估值获取失败", "index_code": index_code}


# --------------------------------------------------------------------------- #
#  2. 东方财富 — 指数估值与历史分位
# --------------------------------------------------------------------------- #

def fetch_eastmoney_valuation(index_code: str) -> Dict[str, Any]:
    """从东方财富获取指数估值数据"""
    # 东财指数估值 API
    market = INDEX_MAP.get(index_code, {}).get("market", "sh")
    secid = f"1.{index_code}" if market == "sh" else f"0.{index_code}"

    try:
        # 东财指数实时数据（含PE/PB）
        url = "https://push2.eastmoney.com/api/qt/stock/get"
        params = {
            "secid": secid,
            "fields": "f43,f44,f45,f46,f47,f48,f57,f58,f162,f167,f170,f171",
            "ut": "fa5fd1943c7b386f172d6893dbfba10b",
            "fltt": 2,
        }
        resp = requests.get(url, params=params, headers=HEADERS_EAST, timeout=TIMEOUT)
        d = resp.json().get("data", {})
        if d:
            return {
                "source": "东方财富",
                "index_code": d.get("f57", index_code),
                "index_name": d.get("f58", ""),
                "最新点位": d.get("f43"),
                "涨跌幅": d.get("f170"),
                "PE_TTM": d.get("f162"),
                "PB": d.get("f167"),
            }
    except Exception:
        pass
    return {"error": "东财指数估值获取失败"}


def fetch_index_pe_history(index_code: str, years: int = 10) -> Dict[str, Any]:
    """获取指数PE历史数据用于计算分位数"""
    market = INDEX_MAP.get(index_code, {}).get("market", "sh")
    secid = f"1.{index_code}" if market == "sh" else f"0.{index_code}"

    try:
        # 东财 K线数据 API（月线，获取PE历史）
        url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
        params = {
            "secid": secid,
            "fields1": "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
            "klt": 101,  # 日线
            "fqt": 0,
            "beg": f"{datetime.now().year - years}0101",
            "end": "20500101",
            "ut": "fa5fd1943c7b386f172d6893dbfba10b",
        }
        resp = requests.get(url, params=params, headers=HEADERS_EAST, timeout=TIMEOUT)
        data = resp.json().get("data", {})
        klines = data.get("klines", [])

        if klines:
            # 提取收盘价序列
            closes = []
            for line in klines:
                parts = line.split(",")
                if len(parts) >= 6:
                    close = _safe_float(parts[2])
                    if close:
                        closes.append(close)

            if closes:
                current = closes[-1]
                # 计算当前点位在历史中的分位
                lower_count = sum(1 for c in closes if c < current)
                percentile = round(lower_count / len(closes) * 100, 1)

                return {
                    "index_code": index_code,
                    "数据周期": f"近{years}年",
                    "数据点数": len(closes),
                    "当前点位": current,
                    "历史最高": max(closes),
                    "历史最低": min(closes),
                    "当前点位分位": percentile,
                }
    except Exception:
        pass
    return {"error": "指数历史数据获取失败"}


# --------------------------------------------------------------------------- #
#  3. 股债性价比（风险溢价率/FED模型）
# --------------------------------------------------------------------------- #

def fetch_equity_bond_ratio() -> Dict[str, Any]:
    """
    计算股债性价比 = 沪深300盈利收益率(1/PE) - 10年期国债收益率
    当比值越高，说明股票资产相对债券越有吸引力
    """
    result = {}

    try:
        # 1. 获取沪深300 PE
        hs300_val = fetch_eastmoney_valuation("000300")
        pe = hs300_val.get("PE_TTM")
        if pe and pe > 0:
            earnings_yield = round(1 / pe * 100, 2)  # 盈利收益率(%)
            result["沪深300_PE_TTM"] = pe
            result["沪深300_盈利收益率(%)"] = earnings_yield
        else:
            result["error_pe"] = "沪深300 PE获取失败"
            return result

        # 2. 获取10年期国债收益率
        try:
            url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
            params = {
                "reportName": "RPT_BOND_TREASURY_YIELD",
                "columns": "ALL",
                "sortColumns": "SOLAR_DATE",
                "sortTypes": "-1",
                "pageSize": 1,
                "pageNumber": 1,
                "source": "WEB",
                "client": "WEB",
                "filter": "(SECURITY_CODE=\"EMM00588704\")",
            }
            resp = requests.get(url, params=params, headers=HEADERS_EAST, timeout=TIMEOUT)
            data = resp.json()
            if data.get("success"):
                records = data.get("result", {}).get("data", [])
                if records:
                    bond_yield = _safe_float(records[0].get("YIELD", 0))
                    if bond_yield:
                        result["10年期国债收益率(%)"] = bond_yield
                    else:
                        # 使用备用默认值
                        bond_yield = 2.0  # 近期大致水平
                        result["10年期国债收益率(%)"] = bond_yield
                        result["_国债收益率备注"] = "使用估计值"
                else:
                    bond_yield = 2.0
                    result["10年期国债收益率(%)"] = bond_yield
                    result["_国债收益率备注"] = "API无数据，使用估计值"
            else:
                bond_yield = 2.0
                result["10年期国债收益率(%)"] = bond_yield
                result["_国债收益率备注"] = "API调用失败，使用估计值"
        except Exception:
            bond_yield = 2.0
            result["10年期国债收益率(%)"] = bond_yield
            result["_国债收益率备注"] = "获取异常，使用估计值"

        # 3. 计算股债性价比
        spread = round(earnings_yield - bond_yield, 2)
        result["股债利差(%)"] = spread
        result["采集时间"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 4. 评估信号
        # 历史经验：
        # 股债利差 > 6% 极度低估（对应历史90%+分位），强烈买入
        # 股债利差 > 4% 低估（对应历史70%+分位），可买入
        # 股债利差 2%-4% 合理
        # 股债利差 < 2% 高估，减仓
        # 股债利差 < 0% 极度高估，大幅减仓
        if spread > 6:
            result["信号"] = "极度低估（股票性价比远高于债券），强烈买入权益"
            result["估计分位"] = "90%+"
        elif spread > 4:
            result["信号"] = "低估（股票性价比高于债券），可加仓权益"
            result["估计分位"] = "70%-90%"
        elif spread > 2:
            result["信号"] = "合理（股债平衡），维持当前配置"
            result["估计分位"] = "30%-70%"
        elif spread > 0:
            result["信号"] = "偏高估（债券性价比上升），减仓权益"
            result["估计分位"] = "10%-30%"
        else:
            result["信号"] = "极度高估（债券性价比远高于股票），大幅减仓权益"
            result["估计分位"] = "0%-10%"

    except Exception as e:
        result["error"] = f"股债性价比计算失败: {e}"

    return result


# --------------------------------------------------------------------------- #
#  4. 综合估值分析
# --------------------------------------------------------------------------- #

def fetch_comprehensive_valuation(index_code: str) -> Dict[str, Any]:
    """综合多源估值数据"""
    results = {}

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {
            pool.submit(fetch_csi_valuation, index_code): "csi",
            pool.submit(fetch_eastmoney_valuation, index_code): "eastmoney",
            pool.submit(fetch_index_pe_history, index_code): "history",
            pool.submit(fetch_equity_bond_ratio): "eq_bond",
        }
        for future in as_completed(futures):
            key = futures[future]
            try:
                results[key] = future.result()
            except Exception as e:
                results[key] = {"error": str(e)}

    # 融合估值数据
    csi = results.get("csi", {})
    east = results.get("eastmoney", {})
    hist = results.get("history", {})
    eq_bond = results.get("eq_bond", {})

    # 取PE/PB最佳值（中证优先）
    pe = csi.get("PE_TTM") or east.get("PE_TTM")
    pb = csi.get("PB_LF") or east.get("PB")
    dividend_yield = csi.get("股息率")

    # 点位分位
    point_percentile = hist.get("当前点位分位")

    # 综合估值判断
    valuation_signal = "无法判断"
    if point_percentile is not None:
        if point_percentile <= 20:
            valuation_signal = "极度低估"
        elif point_percentile <= 30:
            valuation_signal = "低估"
        elif point_percentile <= 70:
            valuation_signal = "合理"
        elif point_percentile <= 80:
            valuation_signal = "偏高估"
        else:
            valuation_signal = "极度高估"

    merged = {
        "指数代码": index_code,
        "指数名称": INDEX_MAP.get(index_code, {}).get("name", csi.get("index_name", east.get("index_name", ""))),
        "采集时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "估值数据": {
            "PE_TTM": pe,
            "PB": pb,
            "股息率(%)": dividend_yield,
            "当前点位": east.get("最新点位") or hist.get("当前点位"),
            "涨跌幅(%)": east.get("涨跌幅"),
        },
        "历史分位": {
            "数据周期": hist.get("数据周期", ""),
            "当前点位分位(%)": point_percentile,
            "历史最高": hist.get("历史最高"),
            "历史最低": hist.get("历史最低"),
        },
        "股债性价比": {
            "股债利差(%)": eq_bond.get("股债利差(%)"),
            "沪深300盈利收益率(%)": eq_bond.get("沪深300_盈利收益率(%)"),
            "10年期国债收益率(%)": eq_bond.get("10年期国债收益率(%)"),
            "信号": eq_bond.get("信号"),
        },
        "综合估值信号": valuation_signal,
        "买卖建议": _generate_trading_advice(point_percentile, eq_bond),
        "原始数据": results,
    }

    return merged


def _generate_trading_advice(point_percentile: Optional[float],
                             eq_bond: Dict) -> Dict[str, str]:
    """基于估值数据生成买卖建议"""
    advice = {}

    if point_percentile is not None:
        if point_percentile <= 20:
            advice["估值信号"] = "极度低估，强烈买入/加倍定投"
            advice["建议仓位"] = "80%-100%（权益上限）"
            advice["定投策略"] = "加倍定投金额"
        elif point_percentile <= 30:
            advice["估值信号"] = "低估，可买入/正常定投"
            advice["建议仓位"] = "60%-80%"
            advice["定投策略"] = "正常定投"
        elif point_percentile <= 70:
            advice["估值信号"] = "合理，持有/正常定投"
            advice["建议仓位"] = "40%-60%"
            advice["定投策略"] = "正常定投"
        elif point_percentile <= 80:
            advice["估值信号"] = "偏高估，分档止盈50%"
            advice["建议仓位"] = "20%-40%"
            advice["定投策略"] = "减半定投金额"
        elif point_percentile <= 90:
            advice["估值信号"] = "高估，分档止盈80%"
            advice["建议仓位"] = "10%-20%"
            advice["定投策略"] = "暂停定投"
        else:
            advice["估值信号"] = "极度高估，清仓"
            advice["建议仓位"] = "0%-10%"
            advice["定投策略"] = "暂停定投，等待回落"
    else:
        advice["估值信号"] = "估值数据不足，无法判断"

    # 叠加股债性价比
    eq_signal = eq_bond.get("信号", "")
    if eq_signal:
        advice["股债性价比信号"] = eq_signal

    return advice


# --------------------------------------------------------------------------- #
#  Markdown 格式化
# --------------------------------------------------------------------------- #

def format_valuation_md(data: Dict) -> str:
    """格式化估值报告为Markdown"""
    lines = [
        f"# {data.get('指数名称', '')}（{data.get('指数代码', '')}）估值与择时分析",
        f"**采集时间**: {data.get('采集时间', '')}",
        f"**综合估值信号**: {data.get('综合估值信号', '')}",
        "",
        "---",
        "",
        "## 一、估值数据",
        "",
        "| 指标 | 数值 |",
        "|------|------|",
    ]

    val = data.get("估值数据", {})
    for k, v in val.items():
        lines.append(f"| {k} | {v if v is not None else '—'} |")

    lines.extend(["", "## 二、历史分位", ""])
    hist = data.get("历史分位", {})
    lines.append("| 指标 | 数值 |")
    lines.append("|------|------|")
    for k, v in hist.items():
        lines.append(f"| {k} | {v if v is not None else '—'} |")

    lines.extend(["", "## 三、股债性价比（FED模型）", ""])
    eq = data.get("股债性价比", {})
    lines.append("| 指标 | 数值 |")
    lines.append("|------|------|")
    for k, v in eq.items():
        lines.append(f"| {k} | {v if v is not None else '—'} |")

    lines.extend(["", "## 四、买卖建议", ""])
    advice = data.get("买卖建议", {})
    lines.append("| 维度 | 建议 |")
    lines.append("|------|------|")
    for k, v in advice.items():
        lines.append(f"| {k} | {v} |")

    return "\n".join(lines)


# --------------------------------------------------------------------------- #
#  主入口
# --------------------------------------------------------------------------- #

def main():
    parser = argparse.ArgumentParser(description="指数估值与择时数据采集")
    parser.add_argument("index_code", nargs="?", default="",
                        help="指数代码（如 000300=沪深300, 000905=中证500）")
    parser.add_argument("--equity-bond-ratio", action="store_true",
                        help="仅获取股债性价比")
    parser.add_argument("--json", action="store_true", help="JSON输出")
    parser.add_argument("--output", type=str, help="输出到文件")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细日志")
    args = parser.parse_args()

    if args.equity_bond_ratio:
        result = fetch_equity_bond_ratio()
    elif args.index_code:
        result = fetch_comprehensive_valuation(args.index_code.strip())
    else:
        parser.error("必须提供指数代码，或使用 --equity-bond-ratio")
        return

    if args.json:
        output = json.dumps(result, ensure_ascii=False, indent=2)
    else:
        if args.equity_bond_ratio:
            lines = ["# 股债性价比（FED模型）", ""]
            lines.append("| 指标 | 数值 |")
            lines.append("|------|------|")
            for k, v in result.items():
                if not k.startswith("_"):
                    lines.append(f"| {k} | {v} |")
            output = "\n".join(lines)
        else:
            output = format_valuation_md(result)

    if args.output:
        import os
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"已保存到 {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
