#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
全市场估值水位与股债收益比采集脚本
数据源：
  - 东方财富 DataCenter (datacenter-web.eastmoney.com) — 指数估值历史
  - 中国债券信息网 (chinamoney.com.cn) — 10年期国债收益率
  - 东方财富 Push2 (push2.eastmoney.com) — 指数实时PE/PB
信源类别：宏观周期仓位中枢量化 — 股债收益比 + 全市场PE/PB历史分位

用法：
  python market_valuation_scraper.py --all                # 全部
  python market_valuation_scraper.py --bond-yield         # 国债收益率
  python market_valuation_scraper.py --index-valuation    # 指数估值
  python market_valuation_scraper.py --equity-bond-ratio  # 股债收益比
  python market_valuation_scraper.py --all --json         # JSON输出
"""

import re
import sys
import json
import argparse
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

# --------------------------------------------------------------------------- #
#  常量
# --------------------------------------------------------------------------- #

HEADERS_EAST = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://data.eastmoney.com/",
}

HEADERS_CHINAMONEY = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.chinamoney.com.cn/",
}

DATACENTER_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"
TIMEOUT = 20


def _safe_float(v, default=None):
    if v is None or v == "-" or v == "":
        return default
    try:
        return float(v)
    except (ValueError, TypeError):
        return default


# =========================================================================== #
#  Part 1: 10年期国债收益率
# =========================================================================== #

def fetch_treasury_yield_chinamoney() -> Dict[str, Any]:
    """从中国债券信息网获取10年期国债收益率（主数据源）
    接口: chinamoney.com.cn 中国货币网 — 中债国债收益率曲线"""
    try:
        url = "https://www.chinamoney.com.cn/ags/ms/cm-u-bk-currency/CbsYldCrvQry"
        today = datetime.now().strftime("%Y-%m-%d")
        params = {
            "lang": "CN",
            "tp": "1001",  # 国债收益率曲线
            "d": today,
        }
        resp = requests.post(url, data=params, headers=HEADERS_CHINAMONEY, timeout=TIMEOUT)
        data = resp.json()
        records = data.get("records", [])

        result = {"日期": today, "数据源": "中国货币网"}
        for rec in records:
            term = rec.get("termToMaturity", "")
            yld = _safe_float(rec.get("yield"))
            if "10年" in term or term == "10Y":
                result["10年期国债收益率(%)"] = yld
            elif "1年" in term or term == "1Y":
                result["1年期国债收益率(%)"] = yld
            elif "5年" in term or term == "5Y":
                result["5年期国债收益率(%)"] = yld
            elif "30年" in term or term == "30Y":
                result["30年期国债收益率(%)"] = yld

        if "10年期国债收益率(%)" not in result:
            # 备用方式：从期限字段模糊匹配
            for rec in records:
                term = str(rec.get("termToMaturity", ""))
                if "10" in term:
                    yld = _safe_float(rec.get("yield"))
                    if yld:
                        result["10年期国债收益率(%)"] = yld
                        break

        return result
    except Exception as e:
        return {"error": f"中国货币网国债收益率获取失败: {e}"}


def fetch_treasury_yield_eastmoney() -> Dict[str, Any]:
    """从东方财富获取中国国债收益率（备用数据源）
    接口: datacenter-web.eastmoney.com RPT_ECONOMY_GOV_CNBD"""
    try:
        params = {
            "reportName": "RPT_ECONOMY_GOV_CNBD",
            "columns": "REPORT_DATE,SOLAR_DATE,EMM00166462,EMM00166466,EMM00166469,EMM00166470",
            "sortColumns": "REPORT_DATE",
            "sortTypes": "-1",
            "pageSize": 5,
            "pageNumber": 1,
            "source": "WEB", "client": "WEB",
        }
        resp = requests.get(DATACENTER_URL, params=params, headers=HEADERS_EAST, timeout=TIMEOUT)
        data = resp.json()
        if not data.get("success"):
            return {"error": "东财国债收益率API调用失败"}

        records = data.get("result", {}).get("data", [])
        if not records:
            return {"error": "无国债收益率数据"}

        latest = records[0]
        return {
            "日期": str(latest.get("SOLAR_DATE", ""))[:10],
            "数据源": "东方财富",
            "1年期国债收益率(%)": _safe_float(latest.get("EMM00166462")),
            "5年期国债收益率(%)": _safe_float(latest.get("EMM00166466")),
            "10年期国债收益率(%)": _safe_float(latest.get("EMM00166469")),
            "30年期国债收益率(%)": _safe_float(latest.get("EMM00166470")),
        }
    except Exception as e:
        return {"error": f"东财国债收益率获取失败: {e}"}


def fetch_treasury_yield() -> Dict[str, Any]:
    """双源获取国债收益率，优先中国货币网，备用东方财富"""
    result = fetch_treasury_yield_chinamoney()
    if "10年期国债收益率(%)" in result and result["10年期国债收益率(%)"] is not None:
        return result

    # 备用源
    backup = fetch_treasury_yield_eastmoney()
    if "10年期国债收益率(%)" in backup and backup["10年期国债收益率(%)"] is not None:
        backup["备注"] = "主源(中国货币网)获取失败，使用东财备用源"
        return backup

    return {"error": "双源均未获取到10年期国债收益率", "主源": result, "备用源": backup}


# =========================================================================== #
#  Part 2: 核心指数估值（PE/PB/历史分位）
# =========================================================================== #

# 指数配置 — 用于全市场估值判断
INDEX_CONFIG = [
    # (名称, 东财secid, 指数代码, 说明)
    ("沪深300", "1.000300", "000300", "大盘蓝筹代表，股债收益比锚定指数"),
    ("中证500", "1.000905", "000905", "中盘成长代表"),
    ("中证1000", "1.000852", "000852", "小盘股代表"),
    ("万得全A", "1.881001", "881001", "全市场估值水位基准"),
    ("创业板指", "0.399006", "399006", "科技成长代表"),
    ("上证指数", "1.000001", "000001", "A股整体风向标"),
]


def fetch_index_realtime_pe(secid: str) -> Dict[str, Any]:
    """获取指数实时PE/PB（东财Push2）"""
    url = "https://push2.eastmoney.com/api/qt/stock/get"
    params = {
        "secid": secid,
        "fields": "f43,f57,f58,f162,f163,f167,f116",
        "ut": "fa5fd1943c7b386f172d6893dbfba10b",
        "fltt": 2,
    }
    try:
        resp = requests.get(url, params=params, headers=HEADERS_EAST, timeout=TIMEOUT)
        data = resp.json().get("data", {})
        if not data:
            return {"error": "指数估值数据为空"}
        return {
            "代码": data.get("f57", ""),
            "名称": data.get("f58", ""),
            "最新点位": data.get("f43"),
            "PE(动态)": data.get("f162"),
            "PE(TTM)": data.get("f163"),
            "PB": data.get("f167"),
        }
    except Exception as e:
        return {"error": f"指数实时估值获取失败: {e}"}


def fetch_index_valuation_history(index_code: str, years: int = 10) -> Dict[str, Any]:
    """获取指数估值历史数据（东财 DataCenter RPT_VALUEANALYSIS_DET）
    用于计算PE/PB历史分位数"""
    secucode_mappings = {
        "000300": "000300.SH",
        "000905": "000905.SH",
        "000852": "000852.SH",
        "881001": "881001.WI",  # 万得全A
        "399006": "399006.SZ",
        "000001": "000001.SH",
    }
    secucode = secucode_mappings.get(index_code)

    all_records = []
    # 获取足够的历史数据（约 years × 250 交易日）
    target_count = years * 250
    page_size = 250
    max_pages = (target_count // page_size) + 2

    for page in range(1, max_pages + 1):
        params = {
            "reportName": "RPT_VALUEANALYSIS_DET",
            "columns": "TRADE_DATE,PE_TTM,PB_MRQ,TOTAL_MARKET_CAP",
            "filter": f"(SECUCODE='{secucode}')" if secucode else f"(SECURITY_CODE='{index_code}')",
            "sortColumns": "TRADE_DATE",
            "sortTypes": "-1",
            "pageSize": page_size,
            "pageNumber": page,
            "source": "WEB", "client": "WEB",
        }
        try:
            resp = requests.get(DATACENTER_URL, params=params, headers=HEADERS_EAST, timeout=TIMEOUT)
            data = resp.json()
            if not data.get("success"):
                break
            result = data.get("result")
            if not result or not result.get("data"):
                break
            all_records.extend(result["data"])
            if page >= result.get("pages", 1):
                break
        except Exception:
            break

    if not all_records:
        return {"error": f"指数 {index_code} 估值历史数据为空"}

    # 计算PE/PB分位
    pe_values = [r["PE_TTM"] for r in all_records
                 if r.get("PE_TTM") is not None and r["PE_TTM"] > 0]
    pb_values = [r["PB_MRQ"] for r in all_records
                 if r.get("PB_MRQ") is not None and r["PB_MRQ"] > 0]

    latest = all_records[0]
    current_pe = latest.get("PE_TTM")
    current_pb = latest.get("PB_MRQ")

    pe_pct = None
    if current_pe and pe_values:
        pe_pct = round(sum(1 for v in pe_values if v <= current_pe) / len(pe_values) * 100, 1)

    pb_pct = None
    if current_pb and pb_values:
        pb_pct = round(sum(1 for v in pb_values if v <= current_pb) / len(pb_values) * 100, 1)

    # 分段统计
    pe_stats = _calc_stats(pe_values) if pe_values else {}
    pb_stats = _calc_stats(pb_values) if pb_values else {}

    return {
        "当前PE(TTM)": current_pe,
        "PE历史分位(%)": pe_pct,
        "PE统计": pe_stats,
        "当前PB(MRQ)": current_pb,
        "PB历史分位(%)": pb_pct,
        "PB统计": pb_stats,
        "数据点数": len(all_records),
        "起始日期": str(all_records[-1].get("TRADE_DATE", ""))[:10] if all_records else "",
        "最新日期": str(all_records[0].get("TRADE_DATE", ""))[:10] if all_records else "",
    }


def _calc_stats(values: List[float]) -> Dict[str, float]:
    """计算描述性统计"""
    if not values:
        return {}
    sorted_v = sorted(values)
    n = len(sorted_v)
    return {
        "最小值": round(sorted_v[0], 2),
        "10分位": round(sorted_v[int(n * 0.1)], 2),
        "25分位": round(sorted_v[int(n * 0.25)], 2),
        "中位数": round(sorted_v[int(n * 0.5)], 2),
        "75分位": round(sorted_v[int(n * 0.75)], 2),
        "90分位": round(sorted_v[int(n * 0.9)], 2),
        "最大值": round(sorted_v[-1], 2),
        "均值": round(sum(sorted_v) / n, 2),
    }


def fetch_all_index_valuation() -> Dict[str, Any]:
    """并行获取所有核心指数估值"""
    results = {}

    def _fetch_one(name, secid, code, desc):
        realtime = fetch_index_realtime_pe(secid)
        history = fetch_index_valuation_history(code)
        return name, {
            "说明": desc,
            "实时": realtime,
            "历史分位": history,
        }

    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(_fetch_one, n, s, c, d): n
                   for n, s, c, d in INDEX_CONFIG}
        for future in as_completed(futures):
            try:
                name, data = future.result()
                results[name] = data
            except Exception as e:
                name = futures[future]
                results[name] = {"error": str(e)}

    return results


# =========================================================================== #
#  Part 3: 股债收益比 (Equity-Bond Yield Ratio)
# =========================================================================== #

def calc_equity_bond_ratio(index_valuation: Dict, treasury_yield: Dict) -> Dict[str, Any]:
    """计算股债收益比
    公式: 沪深300盈利收益率(1/PE_TTM) / 10年期国债收益率
    > 2.0: 股票极度便宜（历史大底区域）
    > 1.5: 股票相对便宜
    1.0-1.5: 中性区间
    < 1.0: 债券相对更优
    < 0.5: 股票极度昂贵"""

    # 获取沪深300 PE_TTM
    hs300 = index_valuation.get("沪深300", {})
    hs300_hist = hs300.get("历史分位", {})
    pe_ttm = hs300_hist.get("当前PE(TTM)")

    # 获取10年期国债收益率
    bond_yield = treasury_yield.get("10年期国债收益率(%)")

    if not pe_ttm or pe_ttm <= 0:
        return {"error": "沪深300 PE_TTM 数据缺失"}
    if not bond_yield or bond_yield <= 0:
        return {"error": "10年期国债收益率数据缺失"}

    # 盈利收益率 = 1/PE × 100（百分比形式）
    earnings_yield = round(100 / pe_ttm, 4)

    # 股债收益比
    ratio = round(earnings_yield / bond_yield, 4)

    # 判定估值水位
    level, position_guidance = _assess_equity_bond_level(ratio)

    return {
        "沪深300_PE_TTM": pe_ttm,
        "盈利收益率(%)": earnings_yield,
        "10年期国债收益率(%)": bond_yield,
        "股债收益比": ratio,
        "估值水位": level,
        "仓位指引": position_guidance,
        "计算公式": "盈利收益率(1/PE×100) / 10年期国债收益率",
    }


def _assess_equity_bond_level(ratio: float) -> tuple:
    """根据股债收益比判定估值水位 (5档仓位中枢)"""
    if ratio >= 2.0:
        return ("⬇ 极度低估", "激进加仓区 — 权益仓位上限可达90-100%")
    elif ratio >= 1.5:
        return ("↘ 偏低估", "积极配置区 — 权益仓位60-80%")
    elif ratio >= 1.0:
        return ("→ 中性", "均衡配置区 — 权益仓位40-60%")
    elif ratio >= 0.5:
        return ("↗ 偏高估", "谨慎减仓区 — 权益仓位20-40%")
    else:
        return ("⬆ 极度高估", "防御区 — 权益仓位0-20%")


# =========================================================================== #
#  Part 4: 综合估值水位判定 (整合PE/PB分位 + 股债收益比)
# =========================================================================== #

def calc_market_valuation_level(index_valuation: Dict, equity_bond: Dict) -> Dict[str, Any]:
    """综合全市场估值水位判定
    双维度: PE/PB历史分位 + 股债收益比"""

    # 取万得全A作为全市场基准
    wdqa = index_valuation.get("万得全A", {}).get("历史分位", {})
    pe_pct = wdqa.get("PE历史分位(%)")
    pb_pct = wdqa.get("PB历史分位(%)")

    # 取沪深300作为备选
    if pe_pct is None:
        hs300 = index_valuation.get("沪深300", {}).get("历史分位", {})
        pe_pct = hs300.get("PE历史分位(%)")
        pb_pct = hs300.get("PB历史分位(%)")

    ratio = equity_bond.get("股债收益比")

    # 估值分位维度 — 5档
    pct_level = "数据不足"
    if pe_pct is not None and pb_pct is not None:
        avg_pct = (pe_pct + pb_pct) / 2
        if avg_pct <= 20:
            pct_level = "⬇ 极度低估 (PE/PB均处于历史底部20%)"
        elif avg_pct <= 40:
            pct_level = "↘ 偏低估"
        elif avg_pct <= 60:
            pct_level = "→ 中性"
        elif avg_pct <= 80:
            pct_level = "↗ 偏高估"
        else:
            pct_level = "⬆ 极度高估 (PE/PB均处于历史顶部20%)"
    elif pe_pct is not None:
        avg_pct = pe_pct
        if avg_pct <= 20:
            pct_level = "⬇ 极度低估"
        elif avg_pct <= 40:
            pct_level = "↘ 偏低估"
        elif avg_pct <= 60:
            pct_level = "→ 中性"
        elif avg_pct <= 80:
            pct_level = "↗ 偏高估"
        else:
            pct_level = "⬆ 极度高估"
    else:
        avg_pct = None

    # 股债收益比维度
    ratio_level = equity_bond.get("估值水位", "数据不足")

    # 综合判定
    comprehensive = _comprehensive_level(avg_pct, ratio)

    return {
        "PE/PB分位均值(%)": round(avg_pct, 1) if avg_pct else None,
        "PE历史分位(%)": pe_pct,
        "PB历史分位(%)": pb_pct,
        "分位维度判定": pct_level,
        "股债收益比": ratio,
        "股债维度判定": ratio_level,
        "【综合估值水位】": comprehensive["level"],
        "【建议仓位中枢】": comprehensive["position"],
        "信号一致性": comprehensive["consistency"],
    }


def _comprehensive_level(pct: Optional[float], ratio: Optional[float]) -> Dict:
    """双维度综合判定"""
    if pct is None and ratio is None:
        return {"level": "数据不足", "position": "—", "consistency": "—"}

    # 将两个维度统一到0-100打分
    score_pct = pct if pct is not None else 50  # 默认中性
    score_ratio = 50  # 默认中性
    if ratio is not None:
        # 将股债比映射到0-100分（比值越大越低估 → 分数越低）
        if ratio >= 2.0:
            score_ratio = 10
        elif ratio >= 1.5:
            score_ratio = 30
        elif ratio >= 1.0:
            score_ratio = 50
        elif ratio >= 0.5:
            score_ratio = 70
        else:
            score_ratio = 90

    # 加权平均（PE/PB分位权重0.5 + 股债比权重0.5）
    if pct is not None and ratio is not None:
        final_score = score_pct * 0.5 + score_ratio * 0.5
        consistency = "一致" if abs(score_pct - score_ratio) <= 20 else "分歧"
    elif pct is not None:
        final_score = score_pct
        consistency = "仅分位维度"
    else:
        final_score = score_ratio
        consistency = "仅股债维度"

    # 5档判定
    if final_score <= 20:
        level = "一档：极度低估（历史大底区域）"
        position = "权益仓位上限 80-100%（中长线）/ 70%（短线）"
    elif final_score <= 40:
        level = "二档：偏低估"
        position = "权益仓位上限 60-80%（中长线）/ 50%（短线）"
    elif final_score <= 60:
        level = "三档：中性"
        position = "权益仓位上限 40-60%（中长线）/ 40%（短线）"
    elif final_score <= 80:
        level = "四档：偏高估"
        position = "权益仓位上限 20-40%（中长线）/ 25%（短线）"
    else:
        level = "五档：极度高估（历史大顶区域）"
        position = "权益仓位上限 0-20%（中长线）/ 15%（短线）"

    return {"level": level, "position": position, "consistency": consistency}


# =========================================================================== #
#  Markdown 格式化
# =========================================================================== #

def format_treasury_md(data: Dict) -> str:
    if "error" in data:
        return f"## 国债收益率\n⚠ {data['error']}\n"
    lines = ["## 国债收益率（无风险利率基准）", ""]
    lines.append("| 指标 | 数值 |")
    lines.append("|------|------|")
    for k, v in data.items():
        if v is None:
            v = "—"
        lines.append(f"| {k} | {v} |")
    return "\n".join(lines)


def format_index_valuation_md(data: Dict) -> str:
    lines = ["## 核心指数估值全景", ""]

    # 汇总表
    lines.append("### 实时估值 + 历史分位")
    lines.append("| 指数 | 最新点位 | PE(TTM) | PE分位(%) | PB(MRQ) | PB分位(%) | 数据年限 |")
    lines.append("|------|---------|---------|----------|---------|----------|---------|")

    for name, info in data.items():
        if "error" in info:
            lines.append(f"| {name} | ⚠ | {info.get('error', '')} | — | — | — | — |")
            continue
        rt = info.get("实时", {})
        hist = info.get("历史分位", {})
        point = rt.get("最新点位", "—")
        pe = hist.get("当前PE(TTM)") or rt.get("PE(TTM)")
        pe_pct = hist.get("PE历史分位(%)", "—")
        pb = hist.get("当前PB(MRQ)") or rt.get("PB")
        pb_pct = hist.get("PB历史分位(%)", "—")
        start = hist.get("起始日期", "—")
        count = hist.get("数据点数", 0)
        years = round(count / 250, 1) if count else "—"

        # 分位高亮
        pe_pct_str = f"**{pe_pct}**" if isinstance(pe_pct, (int, float)) and (pe_pct <= 20 or pe_pct >= 80) else str(pe_pct)
        pb_pct_str = f"**{pb_pct}**" if isinstance(pb_pct, (int, float)) and (pb_pct <= 20 or pb_pct >= 80) else str(pb_pct)

        lines.append(
            f"| {name} | {point} | {pe or '—'} | {pe_pct_str} "
            f"| {pb or '—'} | {pb_pct_str} | ~{years}年 |"
        )

    # 每个指数的PE/PB统计区间
    lines.append("")
    lines.append("### PE/PB 历史统计区间")
    lines.append("| 指数 | PE最小 | PE_25% | PE中位 | PE_75% | PE最大 | PB最小 | PB_25% | PB中位 | PB_75% | PB最大 |")
    lines.append("|------|-------|--------|--------|--------|-------|-------|--------|--------|--------|-------|")

    for name, info in data.items():
        hist = info.get("历史分位", {})
        if "error" in hist:
            continue
        pe_s = hist.get("PE统计", {})
        pb_s = hist.get("PB统计", {})
        lines.append(
            f"| {name} "
            f"| {pe_s.get('最小值', '—')} | {pe_s.get('25分位', '—')} "
            f"| {pe_s.get('中位数', '—')} | {pe_s.get('75分位', '—')} | {pe_s.get('最大值', '—')} "
            f"| {pb_s.get('最小值', '—')} | {pb_s.get('25分位', '—')} "
            f"| {pb_s.get('中位数', '—')} | {pb_s.get('75分位', '—')} | {pb_s.get('最大值', '—')} |"
        )

    return "\n".join(lines)


def format_equity_bond_md(data: Dict) -> str:
    if "error" in data:
        return f"## 股债收益比\n⚠ {data['error']}\n"
    lines = ["## 股债收益比（Equity-Bond Yield Ratio）", ""]
    lines.append("| 指标 | 数值 |")
    lines.append("|------|------|")
    for k, v in data.items():
        if v is None:
            v = "—"
        lines.append(f"| {k} | {v} |")
    lines.append("")
    lines.append("> **判断标准**: 股债收益比 > 2.0 极度低估 | > 1.5 偏低估 | 1.0-1.5 中性 | < 1.0 偏高估 | < 0.5 极度高估")
    return "\n".join(lines)


def format_comprehensive_md(data: Dict) -> str:
    if "error" in data:
        return f"## 综合估值水位\n⚠ {data.get('error', '')}\n"
    lines = [
        "## ⭐ 全市场综合估值水位判定", "",
        "| 维度 | 数值 |",
        "|------|------|",
    ]
    for k, v in data.items():
        if v is None:
            v = "—"
        lines.append(f"| {k} | {v} |")
    return "\n".join(lines)


def format_all_md(treasury: Dict, index_val: Dict, equity_bond: Dict,
                  comprehensive: Dict) -> str:
    parts = [
        "# 全市场估值水位与股债收益比",
        f"**采集时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**数据源**: 东方财富DataCenter + 中国货币网(chinamoney.com.cn)",
        "", "---", "",
        format_comprehensive_md(comprehensive),
        "\n---\n",
        format_equity_bond_md(equity_bond),
        "\n---\n",
        format_treasury_md(treasury),
        "\n---\n",
        format_index_valuation_md(index_val),
    ]
    return "\n".join(parts)


# --------------------------------------------------------------------------- #
#  主入口
# --------------------------------------------------------------------------- #

def fetch_all() -> Dict[str, Any]:
    """采集全部数据并计算综合指标（供 trade_advisor.py 调用）"""
    # 并行采集
    with ThreadPoolExecutor(max_workers=2) as pool:
        f_treasury = pool.submit(fetch_treasury_yield)
        f_index = pool.submit(fetch_all_index_valuation)
        treasury = f_treasury.result()
        index_val = f_index.result()

    # 计算股债收益比
    equity_bond = calc_equity_bond_ratio(index_val, treasury)

    # 综合水位判定
    comprehensive = calc_market_valuation_level(index_val, equity_bond)

    return {
        "treasury": treasury,
        "index_valuation": index_val,
        "equity_bond_ratio": equity_bond,
        "comprehensive_level": comprehensive,
    }


def main():
    parser = argparse.ArgumentParser(description="全市场估值水位与股债收益比采集")
    parser.add_argument("--all", action="store_true", help="全部数据")
    parser.add_argument("--bond-yield", action="store_true", help="国债收益率")
    parser.add_argument("--index-valuation", action="store_true", help="指数估值")
    parser.add_argument("--equity-bond-ratio", action="store_true", help="股债收益比")
    parser.add_argument("--json", action="store_true", help="JSON输出")
    parser.add_argument("--output", type=str, help="输出到文件")
    args = parser.parse_args()

    flags = [args.bond_yield, args.index_valuation, args.equity_bond_ratio]
    if not args.all and not any(flags):
        args.all = True

    if args.all:
        # 全量采集
        all_data = fetch_all()
        treasury = all_data["treasury"]
        index_val = all_data["index_valuation"]
        equity_bond = all_data["equity_bond_ratio"]
        comprehensive = all_data["comprehensive_level"]
    else:
        treasury = fetch_treasury_yield() if (args.bond_yield or args.equity_bond_ratio) else {}
        index_val = fetch_all_index_valuation() if (args.index_valuation or args.equity_bond_ratio) else {}
        equity_bond = calc_equity_bond_ratio(index_val, treasury) if args.equity_bond_ratio else {}
        comprehensive = calc_market_valuation_level(index_val, equity_bond) if args.equity_bond_ratio else {}

    if args.json:
        output = json.dumps({
            "treasury": treasury,
            "index_valuation": index_val,
            "equity_bond_ratio": equity_bond,
            "comprehensive_level": comprehensive,
        }, ensure_ascii=False, indent=2)
    else:
        output = format_all_md(treasury, index_val, equity_bond, comprehensive)

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
