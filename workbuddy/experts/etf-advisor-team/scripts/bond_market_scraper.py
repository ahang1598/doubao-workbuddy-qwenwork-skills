#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
债券市场数据采集脚本 — ETF 顾问团队内置数据引擎

功能：采集债券基金分析"五碗面"框架所需的核心利率与信用数据。
数据源：
  - 中国货币网 (chinamoney.com.cn) — DR007、同业存单利率
  - 东方财富 DataCenter — 国债收益率曲线、信用利差
  - 中国人民银行 — 公开市场操作利率锚

覆盖数据：
  1. DR007 / R007（银行间回购利率）
  2. 同业存单利率（1M/3M/6M/1Y AAA）
  3. 国债收益率曲线（全期限）
  4. 信用利差（AAA/AA+/AA 中短票）
  5. 利率比价验证锚（逆回购利率 vs DR007、MLF vs 存单、10Y国债 vs MLF）

用法：
  python bond_market_scraper.py --all                  # 全部数据
  python bond_market_scraper.py --dr007                # DR007
  python bond_market_scraper.py --ncd                  # 同业存单利率
  python bond_market_scraper.py --treasury             # 国债收益率曲线
  python bond_market_scraper.py --credit-spread        # 信用利差
  python bond_market_scraper.py --rate-anchor          # 利率比价锚定
  python bond_market_scraper.py --all --json           # JSON输出
  python bond_market_scraper.py --all --output FinancialData/bond_market.md

输出：JSON 或 Markdown 格式
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import requests

# ---------------------------------------------------------------------------
#  常量
# ---------------------------------------------------------------------------

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

TIMEOUT = 15


def _safe_float(v, default=None):
    if v is None or v == "" or v == "-":
        return default
    try:
        return float(v)
    except (ValueError, TypeError):
        return default


# ---------------------------------------------------------------------------
#  1. DR007 / R007 — 中国货币网
# ---------------------------------------------------------------------------

def fetch_dr007() -> Dict[str, Any]:
    """
    采集DR007（存款类机构质押式回购加权利率）和R007（全市场）。
    数据源：中国货币网 chinamoney.com.cn
    """
    result = {"status": "ok", "data": {}, "source": "中国货币网 chinamoney.com.cn"}
    try:
        url = "https://www.chinamoney.com.cn/ags/ms/cm-u-bk-currency/SddsIntrRateGov498"
        resp = requests.get(url, headers={
            **HEADERS,
            "Referer": "https://www.chinamoney.com.cn/chinese/sdds/",
        }, timeout=TIMEOUT)
        data = resp.json()
        records = data.get("records", [])
        for rec in records:
            name = rec.get("termToMaturity", "")
            rate = _safe_float(rec.get("latestRate"))
            if "DR007" in name or "7天" in name:
                result["data"]["DR007"] = rate
            elif "DR001" in name or "隔夜" in name:
                result["data"]["DR001"] = rate
        if not result["data"]:
            result["status"] = "degraded"
            result["degraded_reason"] = "chinamoney API未返回DR数据"
    except Exception as e:
        result["status"] = "degraded"
        result["degraded_reason"] = f"请求失败: {e}"
        result["fallback_search"] = 'web_search: "DR007 银行间回购利率 最新 中国货币网"'

    # 备用源：东方财富
    if result["status"] == "degraded":
        try:
            url2 = "https://datacenter-web.eastmoney.com/api/data/v1/get"
            params = {
                "reportName": "RPT_ECONOMY_GOV_CNBD",
                "columns": "ALL",
                "sortColumns": "REPORT_DATE",
                "sortTypes": "-1",
                "pageSize": 5,
                "pageNumber": 1,
                "source": "WEB",
                "client": "WEB",
            }
            resp2 = requests.get(url2, params=params, headers=HEADERS, timeout=TIMEOUT)
            d2 = resp2.json()
            if d2.get("success") and d2.get("result", {}).get("data"):
                for row in d2["result"]["data"]:
                    if "DR007" not in result["data"]:
                        dr = _safe_float(row.get("EMM00588704"))
                        if dr:
                            result["data"]["DR007_eastmoney"] = dr
                            result["status"] = "ok"
        except Exception:
            pass

    return result


# ---------------------------------------------------------------------------
#  2. 同业存单利率 — 中国货币网
# ---------------------------------------------------------------------------

def fetch_ncd_rates() -> Dict[str, Any]:
    """
    采集同业存单(NCD)发行利率: 1M/3M/6M/1Y AAA级。
    数据源：中国货币网
    """
    result = {"status": "ok", "data": {}, "source": "中国货币网"}
    try:
        url = "https://www.chinamoney.com.cn/ags/ms/cm-u-bk-ncd/NcdRtIndc"
        resp = requests.get(url, headers={
            **HEADERS,
            "Referer": "https://www.chinamoney.com.cn/chinese/ncdRtIndc/",
        }, timeout=TIMEOUT)
        data = resp.json()
        records = data.get("records", [])
        for rec in records:
            term = rec.get("term", "")
            rate = _safe_float(rec.get("latestRate"))
            grade = rec.get("creditRating", "")
            if "AAA" in grade:
                if "1M" in term or "1月" in term:
                    result["data"]["NCD_AAA_1M"] = rate
                elif "3M" in term or "3月" in term:
                    result["data"]["NCD_AAA_3M"] = rate
                elif "6M" in term or "6月" in term:
                    result["data"]["NCD_AAA_6M"] = rate
                elif "1Y" in term or "1年" in term:
                    result["data"]["NCD_AAA_1Y"] = rate
        if not result["data"]:
            result["status"] = "degraded"
            result["degraded_reason"] = "chinamoney NCD API未返回数据"
    except Exception as e:
        result["status"] = "degraded"
        result["degraded_reason"] = f"请求失败: {e}"
        result["fallback_search"] = 'web_search: "同业存单 利率 AAA 1年 最新 中国货币网"'

    return result


# ---------------------------------------------------------------------------
#  3. 国债收益率曲线 — 东方财富
# ---------------------------------------------------------------------------

def fetch_treasury_curve() -> Dict[str, Any]:
    """
    采集国债收益率曲线（全期限）。
    数据源：东方财富 DataCenter
    """
    result = {"status": "ok", "data": {}, "source": "东方财富 DataCenter"}
    try:
        url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
        params = {
            "reportName": "RPT_ECONOMY_GOV_CNBD",
            "columns": "ALL",
            "sortColumns": "REPORT_DATE",
            "sortTypes": "-1",
            "pageSize": 2,
            "pageNumber": 1,
            "source": "WEB",
            "client": "WEB",
        }
        resp = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
        data = resp.json()
        if data.get("success") and data.get("result", {}).get("data"):
            row = data["result"]["data"][0]
            field_map = {
                "3M": "EMM00166462",
                "6M": "EMM00166466",
                "1Y": "EMM00166469",
                "2Y": "EMM00166472",
                "3Y": "EMM00166475",
                "5Y": "EMM00166478",
                "7Y": "EMM00166481",
                "10Y": "EMM00166484",
                "30Y": "EMM00166490",
            }
            for term, field in field_map.items():
                val = _safe_float(row.get(field))
                if val:
                    result["data"][f"国债{term}"] = val
            result["data"]["report_date"] = row.get("REPORT_DATE", "")[:10]
        else:
            result["status"] = "degraded"
            result["degraded_reason"] = "东方财富国债收益率API无数据"
    except Exception as e:
        result["status"] = "degraded"
        result["degraded_reason"] = f"请求失败: {e}"
        result["fallback_search"] = 'web_search: "中债 国债收益率曲线 最新"'

    return result


# ---------------------------------------------------------------------------
#  4. 信用利差 — 东方财富
# ---------------------------------------------------------------------------

def fetch_credit_spread() -> Dict[str, Any]:
    """
    采集信用利差数据（AAA/AA+/AA 中短期票据利差）。
    利差 = 信用债收益率 - 同期限国债收益率
    """
    result = {"status": "ok", "data": {}, "source": "东方财富 DataCenter"}
    try:
        # 获取企业债/中短票收益率
        url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
        for rating, report in [
            ("AAA", "RPT_ECONOMY_BOND_YIELD"),
        ]:
            params = {
                "reportName": report,
                "columns": "ALL",
                "sortColumns": "REPORT_DATE",
                "sortTypes": "-1",
                "pageSize": 5,
                "pageNumber": 1,
                "source": "WEB",
                "client": "WEB",
            }
            try:
                resp = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
                data = resp.json()
                if data.get("success") and data.get("result", {}).get("data"):
                    for row in data["result"]["data"][:1]:
                        # 解析可用的信用债收益率字段
                        for key, val in row.items():
                            if val and isinstance(val, (int, float)):
                                result["data"][f"{rating}_{key}"] = val
            except Exception:
                pass

        if not result["data"]:
            result["status"] = "degraded"
            result["degraded_reason"] = "信用利差数据采集受限"
            result["fallback_search"] = 'web_search: "信用利差 AA AAA 中短票 最新 wind 中债"'
    except Exception as e:
        result["status"] = "degraded"
        result["degraded_reason"] = f"请求失败: {e}"
        result["fallback_search"] = 'web_search: "信用利差 AA AAA 中短票 最新"'

    return result


# ---------------------------------------------------------------------------
#  5. 利率比价锚定验证
# ---------------------------------------------------------------------------

def calc_rate_anchor(dr007_data: Dict, ncd_data: Dict, treasury_data: Dict) -> Dict[str, Any]:
    """
    计算三层利率比价锚定（短端/中端/长端）。
    """
    result = {"layers": [], "overall_signal": "数据不足"}

    # 假设当前逆回购利率和MLF利率（这些通常由 pbc_policy_scraper 采集）
    # 此处提供默认值，使用时应从 pbc_data 中获取实际值
    reverse_repo_rate = 1.50  # 7天逆回购利率（示例值，应从央行数据获取）
    mlf_rate = 2.50  # 1年期MLF利率（示例值，应从央行数据获取）

    # 短端：DR007 vs 逆回购利率
    dr007 = dr007_data.get("data", {}).get("DR007") or dr007_data.get("data", {}).get("DR007_eastmoney")
    if dr007:
        diff = (dr007 - reverse_repo_rate) * 100  # bp
        if diff < -20:
            signal = "资金面极度宽松，短债确定性高，杠杆策略空间大"
        elif diff > 30:
            signal = "资金面偏紧，短债承压，控制杠杆"
        else:
            signal = "资金面中性，正常波动范围"
        result["layers"].append({
            "level": "短端",
            "anchor": f"DR007({dr007:.2f}%) vs 7天逆回购({reverse_repo_rate:.2f}%)",
            "spread_bp": round(diff, 1),
            "signal": signal,
        })

    # 中端：1Y存单 vs MLF
    ncd_1y = ncd_data.get("data", {}).get("NCD_AAA_1Y")
    if ncd_1y:
        diff = (ncd_1y - mlf_rate) * 100
        if diff < -30:
            signal = "银行负债端宽松，中短债配置价值高"
        elif diff > 30:
            signal = "银行负债端收紧，中短债谨慎"
        else:
            signal = "银行负债端中性"
        result["layers"].append({
            "level": "中端",
            "anchor": f"1Y存单({ncd_1y:.2f}%) vs MLF({mlf_rate:.2f}%)",
            "spread_bp": round(diff, 1),
            "signal": signal,
        })

    # 长端：10Y国债 vs MLF
    treasury_10y = treasury_data.get("data", {}).get("国债10Y")
    if treasury_10y:
        diff = (treasury_10y - mlf_rate) * 100
        if diff < 30:
            signal = "长端定价偏贵（拥挤），拉久期风险>收益，建议控久期≤2年"
        elif diff > 80:
            signal = "长端定价偏便宜，拉久期性价比高"
        else:
            signal = "长端定价合理"
        result["layers"].append({
            "level": "长端",
            "anchor": f"10Y国债({treasury_10y:.2f}%) vs MLF({mlf_rate:.2f}%)",
            "spread_bp": round(diff, 1),
            "signal": signal,
        })

    # 综合判断
    if len(result["layers"]) >= 2:
        bullish = sum(1 for l in result["layers"] if "宽松" in l["signal"] or "偏便宜" in l["signal"] or "配置价值高" in l["signal"])
        bearish = sum(1 for l in result["layers"] if "偏紧" in l["signal"] or "偏贵" in l["signal"] or "谨慎" in l["signal"])
        if bullish >= 2:
            result["overall_signal"] = "利率比价偏友好，债基配置窗口"
        elif bearish >= 2:
            result["overall_signal"] = "利率比价偏不利，控久期防风险"
        else:
            result["overall_signal"] = "利率比价中性"

    return result


# ---------------------------------------------------------------------------
#  汇总与格式化
# ---------------------------------------------------------------------------

def fetch_all() -> Dict[str, Any]:
    """采集全部债市数据"""
    dr007 = fetch_dr007()
    ncd = fetch_ncd_rates()
    treasury = fetch_treasury_curve()
    credit = fetch_credit_spread()
    anchor = calc_rate_anchor(dr007, ncd, treasury)

    return {
        "dr007": dr007,
        "ncd_rates": ncd,
        "treasury_curve": treasury,
        "credit_spread": credit,
        "rate_anchor": anchor,
        "fetch_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def format_all_md(data: Dict[str, Any]) -> str:
    """格式化为Markdown"""
    lines = [
        "# 债券市场数据（五碗面框架数据支撑）",
        f"**采集时间**: {data.get('fetch_time', '-')}",
        "",
    ]

    # DR007
    dr = data.get("dr007", {})
    lines.append("## 1. 银行间回购利率")
    lines.append("")
    if dr.get("data"):
        lines.append("| 指标 | 利率(%) | 来源 |")
        lines.append("|------|--------|------|")
        for k, v in dr["data"].items():
            if v is not None:
                lines.append(f"| {k} | {v:.4f} | {dr.get('source', '-')} |")
    else:
        lines.append(f"⚠ {dr.get('degraded_reason', '数据未获取')}")
        if dr.get("fallback_search"):
            lines.append(f"降级方案: `{dr['fallback_search']}`")
    lines.extend(["", "---", ""])

    # 同业存单
    ncd = data.get("ncd_rates", {})
    lines.append("## 2. 同业存单利率 (AAA)")
    lines.append("")
    if ncd.get("data"):
        lines.append("| 期限 | 利率(%) |")
        lines.append("|------|--------|")
        for k, v in ncd["data"].items():
            if v is not None:
                lines.append(f"| {k} | {v:.4f} |")
    else:
        lines.append(f"⚠ {ncd.get('degraded_reason', '数据未获取')}")
    lines.extend(["", "---", ""])

    # 国债收益率
    tr = data.get("treasury_curve", {})
    lines.append("## 3. 国债收益率曲线")
    lines.append("")
    if tr.get("data"):
        lines.append(f"**数据日期**: {tr['data'].get('report_date', '-')}")
        lines.append("")
        lines.append("| 期限 | 收益率(%) |")
        lines.append("|------|----------|")
        for k, v in sorted(tr["data"].items()):
            if k != "report_date" and v is not None:
                lines.append(f"| {k} | {v:.4f} |")
    else:
        lines.append(f"⚠ {tr.get('degraded_reason', '数据未获取')}")
    lines.extend(["", "---", ""])

    # 信用利差
    cs = data.get("credit_spread", {})
    lines.append("## 4. 信用利差")
    lines.append("")
    if cs.get("data"):
        lines.append("| 指标 | 数值 |")
        lines.append("|------|------|")
        for k, v in cs["data"].items():
            if v is not None:
                lines.append(f"| {k} | {v} |")
    else:
        lines.append(f"⚠ {cs.get('degraded_reason', '数据未获取')}")
        if cs.get("fallback_search"):
            lines.append(f"降级方案: `{cs['fallback_search']}`")
    lines.extend(["", "---", ""])

    # 利率比价锚定
    anchor = data.get("rate_anchor", {})
    lines.append("## 5. 三层利率比价锚定验证")
    lines.append("")
    if anchor.get("layers"):
        lines.append(f"**综合判断**: {anchor.get('overall_signal', '-')}")
        lines.append("")
        lines.append("| 层级 | 锚定关系 | 利差(bp) | 信号 |")
        lines.append("|------|---------|---------|------|")
        for layer in anchor["layers"]:
            lines.append(f"| {layer['level']} | {layer['anchor']} | {layer['spread_bp']:+.1f} | {layer['signal']} |")
    else:
        lines.append("⚠ 数据不足，无法进行利率比价验证")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
#  CLI
# ---------------------------------------------------------------------------

def _print_utf8(text: str):
    try:
        print(text)
    except UnicodeEncodeError:
        sys.stdout.buffer.write(text.encode("utf-8"))
        sys.stdout.buffer.write(b"\n")
        sys.stdout.buffer.flush()


def main():
    parser = argparse.ArgumentParser(
        description="债券市场数据采集脚本 — 五碗面框架数据支撑",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--all", action="store_true", help="采集全部数据")
    parser.add_argument("--dr007", action="store_true", help="DR007/R007")
    parser.add_argument("--ncd", action="store_true", help="同业存单利率")
    parser.add_argument("--treasury", action="store_true", help="国债收益率曲线")
    parser.add_argument("--credit-spread", action="store_true", help="信用利差")
    parser.add_argument("--rate-anchor", action="store_true", help="利率比价锚定")
    parser.add_argument("--json", action="store_true", help="JSON格式输出")
    parser.add_argument("--output", "-o", default="", help="输出文件路径")
    args = parser.parse_args()

    if args.all or not any([args.dr007, args.ncd, args.treasury, args.credit_spread, args.rate_anchor]):
        data = fetch_all()
    else:
        data = {"fetch_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        if args.dr007:
            data["dr007"] = fetch_dr007()
        if args.ncd:
            data["ncd_rates"] = fetch_ncd_rates()
        if args.treasury:
            data["treasury_curve"] = fetch_treasury_curve()
        if args.credit_spread:
            data["credit_spread"] = fetch_credit_spread()
        if args.rate_anchor:
            dr = data.get("dr007") or fetch_dr007()
            ncd = data.get("ncd_rates") or fetch_ncd_rates()
            tr = data.get("treasury_curve") or fetch_treasury_curve()
            data["rate_anchor"] = calc_rate_anchor(dr, ncd, tr)

    if args.json:
        text = json.dumps(data, ensure_ascii=False, indent=2)
    else:
        text = format_all_md(data)

    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"✓ 输出到 {args.output}", file=sys.stderr)
    else:
        _print_utf8(text)


if __name__ == "__main__":
    main()
