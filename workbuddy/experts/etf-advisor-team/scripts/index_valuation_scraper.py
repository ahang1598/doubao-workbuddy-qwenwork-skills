#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
A股指数估值与市场情绪数据采集脚本 — ETF 顾问团队内置数据引擎
功能：采集A股主要宽基/行业指数的实时估值数据（PE/PB/股息率/估值分位）、
      市场成交额/换手率/融资融券、北向资金流向等市场情绪数据。
数据源：东方财富网数据中心 / 中证指数公司 / 集思录
信源对应：Level 1 — 金融市场现状；Level 2 — 大类资产配置估值数据

用法：
  # A股主要指数估值概览
  python index_valuation_scraper.py --valuation

  # 市场情绪数据（成交额/融资融券/北向资金）
  python index_valuation_scraper.py --sentiment

  # 全部数据
  python index_valuation_scraper.py --all

  # 指定指数的详细估值历史
  python index_valuation_scraper.py --index 沪深300 --periods 12

  # JSON输出
  python index_valuation_scraper.py --all --json

输出：JSON 或 Markdown 格式
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


import re
import sys
import json
import argparse
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any


# --------------------------------------------------------------------------- #
#  常量与配置
# --------------------------------------------------------------------------- #

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://data.eastmoney.com/",
}

# A股主要指数代码配置
INDEX_LIST = {
    "上证指数": {"code": "000001", "market": "sh", "secid": "1.000001"},
    "深证成指": {"code": "399001", "market": "sz", "secid": "0.399001"},
    "创业板指": {"code": "399006", "market": "sz", "secid": "0.399006"},
    "科创50": {"code": "000688", "market": "sh", "secid": "1.000688"},
    "沪深300": {"code": "000300", "market": "sh", "secid": "1.000300"},
    "中证500": {"code": "000905", "market": "sh", "secid": "1.000905"},
    "中证1000": {"code": "000852", "market": "sh", "secid": "1.000852"},
    "中证全指": {"code": "000985", "market": "sh", "secid": "1.000985"},
    "上证50": {"code": "000016", "market": "sh", "secid": "1.000016"},
    "中证红利": {"code": "000922", "market": "sh", "secid": "1.000922"},
}

# 行业指数（申万一级）
SECTOR_INDICES = {
    "银行": "801780",
    "非银金融": "801790",
    "房地产": "801180",
    "食品饮料": "801120",
    "医药生物": "801150",
    "电子": "801080",
    "计算机": "801750",
    "通信": "801770",
    "传媒": "801760",
    "电力设备": "801730",
    "国防军工": "801740",
    "汽车": "801880",
    "机械设备": "801890",
    "有色金属": "801050",
    "钢铁": "801040",
    "煤炭": "801020",
    "石油石化": "801960",
    "基础化工": "801030",
    "建筑装饰": "801720",
    "公用事业": "801160",
    "交通运输": "801170",
    "农林牧渔": "801010",
    "家用电器": "801110",
    "轻工制造": "801140",
    "商贸零售": "801200",
    "社会服务": "801210",
    "美容护理": "801950",
    "纺织服饰": "801130",
    "建筑材料": "801710",
    "环保": "801970",
}


# --------------------------------------------------------------------------- #
#  估值数据采集
# --------------------------------------------------------------------------- #

def fetch_index_valuation_eastmoney() -> List[Dict[str, Any]]:
    """从东方财富获取A股主要指数估值数据
    使用 fltt=2 浮点模式获取实际数值；PE/PB 通过 ulist API 批量获取以提高可靠性。
    """
    results = []

    # 批量获取指数行情 + PE/PB
    secids = ",".join(info["secid"] for info in INDEX_LIST.values())
    try:
        url = "https://push2.eastmoney.com/api/qt/ulist.np/get"
        params = {
            "fltt": 2,
            "fields": "f1,f2,f3,f4,f6,f12,f13,f14,f104,f105,f116,f117,f162,f167",
            "secids": secids,
            "ut": "fa5fd1943c7b386f172d6893dbfba10b",
        }
        resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
        data = resp.json()
        items = data.get("data", {}).get("diff", [])

        # 建立 secid -> name 映射
        secid_to_name = {info["secid"]: name for name, info in INDEX_LIST.items()}
        code_to_name = {info["code"]: name for name, info in INDEX_LIST.items()}

        for item in items:
            code = str(item.get("f12", ""))
            market = item.get("f13", 0)
            secid_key = f"{market}.{code}"
            name = secid_to_name.get(secid_key, code_to_name.get(code, code))

            pe = item.get("f162")
            pb = item.get("f167")
            turnover = item.get("f6")
            market_cap = item.get("f116")
            up_count = item.get("f104")
            down_count = item.get("f105")

            # 注：push2 API 对指数级别 PE/PB 支持有限（f162 常返回0，f167 可能不准确）
            # PE/PB 需要从中证指数公司官网或其他专业数据源获取
            result = {
                "指数名称": name,
                "代码": code,
                "最新点位": item.get("f2"),
                "涨跌幅(%)": item.get("f3"),
                "成交额(亿)": round(turnover / 1e8, 2) if turnover and turnover != "-" else None,
                "上涨家数": up_count if up_count and up_count != "-" else None,
                "下跌家数": down_count if down_count and down_count != "-" else None,
            }
            results.append(result)
    except Exception:
        # 降级到逐个查询
        for name, info in INDEX_LIST.items():
            try:
                url = "https://push2.eastmoney.com/api/qt/stock/get"
                params = {
                    "secid": info["secid"],
                    "fields": "f43,f48,f57,f58,f116,f170",
                    "ut": "fa5fd1943c7b386f172d6893dbfba10b",
                    "fltt": 2,
                }
                resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
                data = resp.json().get("data", {})
                if not data:
                    continue

                result = {
                    "指数名称": name,
                    "代码": info["code"],
                    "最新点位": data.get("f43"),
                    "涨跌幅(%)": data.get("f170"),
                    "成交额(亿)": round(data.get("f48", 0) / 1e8, 2) if data.get("f48") else None,
                }
                results.append(result)
            except Exception:
                results.append({"指数名称": name, "代码": info["code"], "error": "获取失败"})

    return results


def fetch_market_overview() -> Dict[str, Any]:
    """获取A股市场整体概览数据（涨跌家数/成交额等）"""
    try:
        url = "https://push2.eastmoney.com/api/qt/ulist.np/get"
        params = {
            "fltt": 2,
            "fields": "f1,f2,f3,f4,f6,f12,f13,f14,f104,f105,f106",
            "secids": "1.000001,0.399001,0.399006,1.000300",
            "ut": "fa5fd1943c7b386f172d6893dbfba10b",
        }
        resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
        data = resp.json()
        items = data.get("data", {}).get("diff", [])
        results = []
        for item in items:
            results.append({
                "指数": item.get("f14", ""),
                "最新": item.get("f2"),
                "涨跌幅(%)": item.get("f3"),
                "成交额(亿)": round(item.get("f6", 0) / 1e8, 2) if item.get("f6") else None,
                "上涨家数": item.get("f104"),
                "下跌家数": item.get("f105"),
            })
        return {"status": "ok", "data": results}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def fetch_northbound_flow() -> Dict[str, Any]:
    """获取北向资金（沪股通+深股通）流向数据。
    优先尝试 push2 kamtbs API 获取每日净流入数据；
    若失败则降级到 RPT_MUTUAL_MARKET_STA 获取季度级持有市值数据；
    若仍失败则返回降级提示，建议使用 web 搜索。
    """
    # 方案1：push2 kamtbs API（每日净流入）
    try:
        url = "https://push2.eastmoney.com/api/qt/kamtbs.ww/get"
        params = {
            "fields1": "f1,f2,f3,f4",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65,f66,f67,f68,f69,f70",
            "ut": "b955fbe1f7fc12d96c199e6b2d3f4038",
        }
        resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
        data = resp.json()

        s2n = data.get("data", {}).get("s2n", [])
        if s2n:
            results = []
            for line in s2n[-10:]:
                parts = line.split(",")
                if len(parts) >= 8:
                    results.append({
                        "日期": parts[0],
                        "沪股通净流入(亿)": round(float(parts[1]) / 1e4, 2) if parts[1] and parts[1] != "-" else None,
                        "深股通净流入(亿)": round(float(parts[2]) / 1e4, 2) if parts[2] and parts[2] != "-" else None,
                        "北向合计净流入(亿)": round(float(parts[3]) / 1e4, 2) if parts[3] and parts[3] != "-" else None,
                    })
            if results:
                return {"status": "ok", "data": results}
    except Exception:
        pass

    # 方案2：datacenter RPT_MUTUAL_MARKET_STA（季度级北向持有市值）
    try:
        url2 = "https://datacenter-web.eastmoney.com/api/data/v1/get"
        params2 = {
            "reportName": "RPT_MUTUAL_MARKET_STA",
            "columns": "ALL",
            "pageNumber": 1,
            "pageSize": 5,
            "source": "WEB",
            "client": "WEB",
        }
        resp2 = requests.get(url2, params=params2, headers=HEADERS, timeout=15)
        text2 = resp2.text
        match = re.search(r'\((\{.*\})\)', text2, re.DOTALL)
        if match:
            text2 = match.group(1)
        data2 = json.loads(text2)
        if data2.get("success"):
            rows = data2.get("result", {}).get("data", [])
            results2 = []
            for row in rows[:5]:
                hold_date = str(row.get("HOLD_DATE", ""))[:10]
                hold_cap = row.get("HOLD_MARKET_CAP")
                change_rate = row.get("CHANGE_RATE")
                add_bname = row.get("ADD_MARKET_BNAME", "")
                add_mname = row.get("ADD_MARKET_MNAME", "")
                results2.append({
                    "统计日期": hold_date,
                    "北向持有市值(亿)": round(hold_cap / 1e8, 2) if hold_cap else None,
                    "市值变化率(%)": round(change_rate, 2) if change_rate else None,
                    "增持最多行业": add_bname,
                    "增持最多个股": add_mname,
                })
            if results2:
                return {"status": "ok", "data": results2, "note": "降级为季度级数据（RPT_MUTUAL_MARKET_STA）"}
    except Exception:
        pass

    # 方案3：降级提示
    return {
        "status": "degraded",
        "data": [],
        "error": "北向资金每日净流入数据暂不可用，请使用 web 搜索「北向资金 今日净流入」获取最新数据",
    }


def fetch_margin_trading() -> Dict[str, Any]:
    """获取融资融券余额数据。
    尝试多个可能的 reportName；若全部失败则返回降级提示。
    """
    candidate_reports = [
        "RPTA_WEB_RZRQ_ZCYE_MX",
        "RPT_MARGIN_TOTAL",
        "RPTA_WEB_RZRQ_TOTAL",
    ]
    for report_name in candidate_reports:
        try:
            url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
            params = {
                "reportName": report_name,
                "columns": "ALL",
                "pageNumber": 1,
                "pageSize": 10,
                "sortColumns": "DIM_DATE",
                "sortTypes": -1,
                "source": "WEB",
                "client": "WEB",
            }
            resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
            text = resp.text
            match = re.search(r'\((\{.*\})\)', text, re.DOTALL)
            if match:
                text = match.group(1)
            data = json.loads(text)
            if not data.get("success"):
                continue
            rows = data.get("result", {}).get("data", [])
            if not rows:
                continue

            results = []
            for row in rows[:10]:
                results.append({
                    "日期": str(row.get("DIM_DATE", row.get("TRADE_DATE", "")))[:10],
                    "融资余额(亿)": round(row.get("RZYE", 0) / 1e8, 2) if row.get("RZYE") else None,
                    "融券余额(亿)": round(row.get("RQYE", 0) / 1e8, 2) if row.get("RQYE") else None,
                    "融资融券余额(亿)": round(row.get("RZRQYE", 0) / 1e8, 2) if row.get("RZRQYE") else None,
                    "融资买入(亿)": round(row.get("RZMRE", 0) / 1e8, 2) if row.get("RZMRE") else None,
                })
            return {"status": "ok", "data": results}
        except Exception:
            continue

    # 所有尝试失败，降级提示
    return {
        "status": "degraded",
        "data": [],
        "error": "融资融券数据 API 暂不可用（reportName 已废弃），请使用 web 搜索「融资融券余额 最新数据」获取",
    }


def fetch_bond_yields(work_date: str = "") -> Dict[str, Any]:
    """获取中国国债收益率曲线数据（数据源：中债信息网）
    返回各期限国债收益率（3月/6月/1年/3年/5年/7年/10年/30年）。
    """
    if not work_date:
        work_date = datetime.now().strftime("%Y-%m-%d")
    try:
        url = "https://yield.chinabond.com.cn/cbweb-cbrc-web/cbrc/queryGjqxInfo"
        params = {"workTime": work_date, "locale": "cn_ZH"}
        resp = requests.get(url, params=params, headers={
            "User-Agent": HEADERS["User-Agent"],
            "Referer": "https://yield.chinabond.com.cn/",
        }, timeout=15)
        text = resp.text

        tenors = ["3月", "6月", "1年", "3年", "5年", "7年", "10年", "30年"]
        results = []

        # 解析 HTML 表格：中债国债收益率曲线
        lines = text.split("\n")
        for idx, line in enumerate(lines):
            if "中债国债收益率曲线" in line:
                # 接下来的 <td> 中包含收益率数据
                data_line = "".join(lines[idx:idx+20])
                import re as _re
                vals = _re.findall(r'<td>([0-9.]+)</td>', data_line)
                if vals and len(vals) >= len(tenors):
                    row = {"日期": work_date, "曲线": "中债国债收益率"}
                    for t, v in zip(tenors, vals[:len(tenors)]):
                        row[t] = float(v)
                    results.append(row)
                break

        # 再找商业银行债(AAA)
        for idx, line in enumerate(lines):
            if "中债商业银行普通债收益率曲线(AAA)" in line:
                data_line = "".join(lines[idx:idx+20])
                import re as _re
                vals = _re.findall(r'<td>([0-9.]+)</td>', data_line)
                if vals and len(vals) >= len(tenors):
                    row = {"日期": work_date, "曲线": "商业银行债(AAA)"}
                    for t, v in zip(tenors, vals[:len(tenors)]):
                        row[t] = float(v)
                    results.append(row)
                break

        return {"status": "ok", "data": results}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# --------------------------------------------------------------------------- #
#  输出格式化
# --------------------------------------------------------------------------- #

def format_table_md(data: List[Dict], title: str) -> str:
    """通用Markdown表格格式化"""
    lines = [f"### {title}", ""]

    valid = [d for d in data if "error" not in d]
    if not valid:
        lines.append("暂无数据")
        return "\n".join(lines)

    headers = list(valid[0].keys())
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

    for row in valid:
        vals = []
        for h in headers:
            v = row.get(h)
            if v is None:
                v = "-"
            elif isinstance(v, float):
                if "%" in h:
                    v = f"{v:+.2f}%" if "涨跌" in h else f"{v:.2f}"
                else:
                    v = f"{v:,.2f}"
            else:
                v = str(v)
            vals.append(v)
        lines.append("| " + " | ".join(vals) + " |")

    lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
#  CLI 入口
# --------------------------------------------------------------------------- #

def main():
    parser = argparse.ArgumentParser(
        description="A股指数估值与市场情绪数据采集工具 — ETF 顾问团队",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python index_valuation_scraper.py --all          # 全部数据
  python index_valuation_scraper.py --valuation    # 指数估值
  python index_valuation_scraper.py --sentiment    # 市场概览
  python index_valuation_scraper.py --northbound   # 北向资金
  python index_valuation_scraper.py --margin       # 融资融券
  python index_valuation_scraper.py --bonds        # 国债收益率曲线
  python index_valuation_scraper.py --all --json   # JSON输出
        """,
    )
    parser.add_argument("--all", "-a", action="store_true", help="全部数据")
    parser.add_argument("--valuation", "-v", action="store_true", help="指数估值数据")
    parser.add_argument("--sentiment", "-s", action="store_true", help="市场情绪数据")
    parser.add_argument("--northbound", "-n", action="store_true", help="北向资金流向")
    parser.add_argument("--margin", "-m", action="store_true", help="融资融券数据")
    parser.add_argument("--bonds", "-b", action="store_true", help="国债收益率曲线（中债信息网）")
    parser.add_argument("--json", action="store_true", help="JSON格式输出")
    parser.add_argument("--output", "-o", default="", help="输出到文件")
    args = parser.parse_args()

    if not any([args.all, args.valuation, args.sentiment, args.northbound, args.margin, args.bonds]):
        parser.print_help()
        return

    all_results = {}
    md_parts = [
        f"# A股市场估值与情绪数据",
        f"**采集时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**数据来源**: 东方财富数据中心",
        f"📎 **信源API**: `https://push2.eastmoney.com/api/qt/ulist.np/get` (指数估值) | `https://push2.eastmoney.com/api/qt/kamtbs.ww/get` (北向资金) | `https://datacenter-web.eastmoney.com/api/data/v1/get` (融资融券) | `https://yield.chinabond.com.cn/cbweb-cbrc-web/cbrc/queryGjqxInfo` (中债收益率)",
        "", "---", "",
    ]

    if args.all or args.valuation:
        val_data = fetch_index_valuation_eastmoney()
        all_results["指数估值"] = val_data
        md_parts.append(format_table_md(val_data, "A股主要指数估值"))

    if args.all or args.sentiment:
        overview = fetch_market_overview()
        if overview["status"] == "ok":
            all_results["市场概览"] = overview["data"]
            md_parts.append(format_table_md(overview["data"], "市场概览"))

    if args.all or args.northbound:
        nb = fetch_northbound_flow()
        if nb["status"] in ("ok", "degraded"):
            all_results["北向资金"] = nb.get("data", [])
            if nb.get("note"):
                md_parts.append(f"*注：{nb['note']}*\n")
            if nb.get("error") and nb["status"] == "degraded":
                md_parts.append(f"### 北向资金流向\n\n⚠️ {nb['error']}\n")
            elif nb.get("data"):
                md_parts.append(format_table_md(nb["data"], "北向资金流向（近10个交易日）"))

    if args.all or args.margin:
        margin = fetch_margin_trading()
        if margin["status"] in ("ok", "degraded"):
            all_results["融资融券"] = margin.get("data", [])
            if margin.get("error") and margin["status"] == "degraded":
                md_parts.append(f"### 融资融券余额\n\n⚠️ {margin['error']}\n")
            elif margin.get("data"):
                md_parts.append(format_table_md(margin["data"], "融资融券余额（近10个交易日）"))

    if args.all or args.bonds:
        bonds = fetch_bond_yields()
        if bonds["status"] == "ok":
            all_results["国债收益率"] = bonds["data"]
            md_parts.append(format_table_md(bonds["data"], "中国国债收益率曲线（%）"))

    if args.json:
        output = json.dumps(all_results, ensure_ascii=False, indent=2)
    else:
        output = "\n".join(md_parts)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"已保存到 {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
