#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
基金详细信息采集脚本 — ETF 顾问团队内置数据采集引擎
功能：针对单只或批量基金，从天天基金网采集详细信息（特色数据/风险指标、基金经理、
      持有人结构、评级、分红送配、资产配置、持仓集中度等）
数据源：天天基金网 HTML 页面 + FundArchivesDatas / F10DataApi / JSON API
参考：fund_info_scraper - V3 - 20260227.py

用法：
  # 查询单只基金全部详情
  python fund_detail_scraper.py 000001

  # 查询指定模块
  python fund_detail_scraper.py 000001 --sections 特色数据,基金经理,基金评级

  # 批量查询（逗号分隔）
  python fund_detail_scraper.py 000001,000002,000003 --sections 特色数据

  # JSON 输出
  python fund_detail_scraper.py 000001 --json

  # 批量查询并输出到文件
  python fund_detail_scraper.py 000001,000002 --output result.json --json

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
import time
import random
import argparse
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading


# --------------------------------------------------------------------------- #
#  核心采集类
# --------------------------------------------------------------------------- #

class FundDetailScraper:
    """天天基金网 单只基金详细信息采集器"""

    BASE_URL = "https://fundf10.eastmoney.com"
    API_URL = f"{BASE_URL}/FundArchivesDatas.aspx"
    F10_DATA_API = f"{BASE_URL}/F10DataApi.aspx"
    FUND_API = "https://api.fund.eastmoney.com"
    NAV_API = f"{FUND_API}/f10/lsjz"
    JJGG_API = f"{FUND_API}/f10/JJGG"
    HYPZ_API = f"{FUND_API}/f10/HYPZ/"
    GRADE_API = f"{FUND_API}/F10/JJPJ/"

    # 评级字段映射
    GRADE_FIELDS = [
        ("RDATE", "评级日期"), ("ZSPJ", "招商评级"),
        ("SZPJ3", "上海证券3年期"), ("SZPJ5", "上海证券5年期"),
        ("JAPJ", "济安金信评级"), ("CXPJ3", "晨星评级"),
    ]

    # 全部可采集的模块
    ALL_SECTIONS = [
        "基本概况", "基金经理", "基金评级", "特色数据",
        "分红送配", "阶段涨幅", "季度年度涨幅",
        "基金持仓", "债券持仓", "持仓变动走势",
        "行业配置", "资产配置",
        "规模变动", "持有人结构",
        "财务指标", "收入分析", "费用分析",
    ]

    def __init__(self, fund_code: str, max_workers: int = 8):
        self.fund_code = fund_code.strip()
        self.max_workers = max_workers
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": f"{self.BASE_URL}/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        })
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=max_workers,
            pool_maxsize=max_workers * 2,
            max_retries=2,
        )
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self._print_lock = threading.Lock()

    # ================================================================== #
    #  通用工具
    # ================================================================== #

    def _get_page(self, page_key: str) -> Optional[BeautifulSoup]:
        url = f"{self.BASE_URL}/{page_key}_{self.fund_code}.html"
        try:
            resp = self.session.get(url, timeout=15)
            resp.encoding = "utf-8"
            if resp.status_code == 200:
                return BeautifulSoup(resp.text, "html.parser")
        except Exception:
            pass
        return None

    def _get_api_data(self, data_type: str, extra_params: dict = None) -> Optional[str]:
        params = {
            "type": data_type, "code": self.fund_code,
            "topline": 10, "year": "", "month": "", "rt": random.random(),
        }
        if extra_params:
            params.update(extra_params)
        try:
            resp = self.session.get(self.API_URL, params=params, timeout=15)
            resp.encoding = "utf-8"
            text = resp.text
            m = re.search(r'content:"(.*?)"(?:,|\})', text, re.DOTALL)
            if m and m.group(1):
                return m.group(1)
            return text if len(text) > 30 else None
        except Exception:
            return None

    def _get_f10_data_api(self, data_type: str) -> Optional[str]:
        params = {"type": data_type, "code": self.fund_code, "date": "", "rt": random.random()}
        try:
            resp = self.session.get(self.F10_DATA_API, params=params, timeout=15)
            resp.encoding = "utf-8"
            return resp.text if resp.status_code == 200 else None
        except Exception:
            return None

    def _get_json_api(self, url: str, params: dict) -> Optional[Dict]:
        params["callback"] = "jQuery"
        params["_"] = int(time.time() * 1000)
        try:
            resp = self.session.get(url, params=params, timeout=15)
            text = resp.text
            m = re.search(r"jQuery\((.*)\)", text, re.DOTALL)
            if m:
                result = json.loads(m.group(1))
                if result.get("ErrCode") == 0:
                    return result
            if text.startswith("{"):
                result = json.loads(text)
                if result.get("ErrCode") == 0:
                    return result
        except Exception:
            pass
        return None

    @staticmethod
    def _safe_text(element) -> str:
        if element:
            text = element.get_text(strip=True)
            return text.replace("\xa0", " ").replace("\u3000", " ")
        return ""

    def _parse_html_table(self, html_str: str) -> List[Dict]:
        if not html_str:
            return []
        soup = BeautifulSoup(html_str, "html.parser")
        results = []
        for table in soup.find_all("table"):
            rows = table.find_all("tr")
            if not rows:
                continue
            ths = rows[0].find_all("th")
            if not ths:
                continue
            headers = [self._safe_text(th) for th in ths]
            for row in rows[1:]:
                cells = [self._safe_text(c) for c in row.find_all("td")]
                if cells and len(cells) == len(headers) and any(cells):
                    results.append(dict(zip(headers, cells)))
        return results

    def _parse_api_html_full(self, html_str: str) -> Dict:
        if not html_str:
            return {}
        soup = BeautifulSoup(html_str, "html.parser")
        data = {}
        for idx, table in enumerate(soup.find_all("table")):
            title = ""
            title_th = table.find("th", class_="title")
            if title_th:
                title = self._safe_text(title_th)
            if not title:
                prev = table.find_previous_sibling(["h4", "h3"])
                if prev:
                    title = self._safe_text(prev)
            rows = table.find_all("tr")
            if not rows:
                continue
            ths = rows[0].find_all("th")
            headers = [self._safe_text(th) for th in ths] if ths else []
            data_rows = rows[1:] if ths else rows
            table_data = []
            for row in data_rows:
                cells = [self._safe_text(c) for c in row.find_all(["td", "th"])]
                if not any(cells):
                    continue
                if headers and len(cells) == len(headers):
                    table_data.append(dict(zip(headers, cells)))
                elif cells:
                    table_data.append(cells)
            key = title if title else f"表格{idx + 1}"
            if table_data:
                data[key] = table_data
        return data

    def _parse_f10_json_array(self, text: str) -> List[Dict]:
        if not text:
            return []
        m = re.search(r'Data:\s*(\[.*\])', text)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass
        return []

    def _stars(self, val) -> str:
        if not val:
            return "---"
        try:
            return "★" * int(val)
        except (ValueError, TypeError):
            return str(val)

    def _li_text(self, li_tag) -> str:
        for tip in li_tag.find_all("div", class_="infoTips"):
            tip.decompose()
        for tbl in li_tag.find_all("table"):
            tbl.decompose()
        return self._safe_text(li_tag)

    # ================================================================== #
    #  各模块采集方法
    # ================================================================== #

    def parse_jbgk(self) -> Dict:
        """基本概况"""
        soup = self._get_page("jbgk")
        if not soup:
            return {}
        data = {}
        for table in soup.find_all("table", class_="info"):
            for row in table.find_all("tr"):
                for th, td in zip(row.find_all("th"), row.find_all("td")):
                    key = self._safe_text(th)
                    if key:
                        data[key] = self._safe_text(td)
        for box in soup.find_all("div", class_="boxitem"):
            title_el = box.find("h4", class_="t")
            if title_el:
                title = self._safe_text(title_el)
                txt = box.find("div", class_="txt_in")
                if txt and title:
                    data[title] = self._safe_text(txt)
        return data

    def parse_jjjl(self) -> Dict:
        """基金经理"""
        soup = self._get_page("jjjl")
        if not soup:
            return {}
        data = {"经理变动一览": [], "现任经理简介": [], "历任基金一览": []}

        table = soup.find("table", class_="jloff")
        if not table:
            for t in soup.find_all("table"):
                if t.find("th", string=re.compile("任职日期|基金经理|起始期")):
                    table = t
                    break
        if table:
            rows = table.find_all("tr")
            headers = [self._safe_text(th) for th in rows[0].find_all("th")] if rows else []
            for row in rows[1:]:
                cells = [self._safe_text(td) for td in row.find_all("td")]
                if cells and headers:
                    data["经理变动一览"].append(dict(zip(headers, cells)))

        for intro in soup.find_all("div", class_="jl_intro"):
            entry = {}
            name_el = intro.find("span", class_="name")
            desc_el = intro.find("p")
            if name_el:
                entry["姓名"] = self._safe_text(name_el)
            if desc_el:
                entry["简介"] = self._safe_text(desc_el)
            if entry:
                data["现任经理简介"].append(entry)
        if not data["现任经理简介"]:
            for ms in soup.find_all("div", class_="ms"):
                text = self._safe_text(ms)
                if text and len(text) > 10:
                    data["现任经理简介"].append({"简介": text})

        for ft in soup.find_all("table", class_="ftrs"):
            rows = ft.find_all("tr")
            if rows:
                headers = [self._safe_text(th) for th in rows[0].find_all("th")]
                for row in rows[1:]:
                    cells = [self._safe_text(td) for td in row.find_all("td")]
                    if cells and headers:
                        data["历任基金一览"].append(dict(zip(headers, cells)))
        return data

    def parse_jjpj(self) -> Dict:
        """基金评级"""
        data = {"评级数据": []}
        result = self._get_json_api(self.GRADE_API, {
            "fundcode": self.fund_code, "pageIndex": 1, "pageSize": 50,
        })
        if result and result.get("Data"):
            for row in result["Data"]:
                entry = {}
                for api_key, cn_name in self.GRADE_FIELDS:
                    val = row.get(api_key, "")
                    entry[cn_name] = val if api_key == "RDATE" else self._stars(val)
                if any(v != "---" for v in entry.values()):
                    data["评级数据"].append(entry)

        soup = self._get_page("jjpj")
        if soup:
            about_div = soup.find("div", class_="pjjg_about")
            if about_div:
                data["评级说明"] = self._safe_text(about_div)
        return data

    def parse_tsdata(self) -> Dict:
        """特色数据（风险指标、投资风格）— 含夏普比率、最大回撤等关键筛选指标"""
        soup = self._get_page("tsdata")
        if not soup:
            return {}
        data = {"风险等级": {}, "风险指标": {}, "投资风格": []}

        for div in soup.find_all("div", class_="fxdj"):
            text = self._safe_text(div)
            if "所有基金" in text:
                active = div.find("span", class_=re.compile("active|on|cur"))
                data["风险等级"]["在所有基金中"] = self._safe_text(active) if active else text
            elif "同类基金" in text:
                active = div.find("span", class_=re.compile("active|on|cur"))
                data["风险等级"]["在同类基金中"] = self._safe_text(active) if active else text

        fxtb = soup.find("table", class_="fxtb")
        if fxtb:
            rows = fxtb.find_all("tr")
            if rows:
                headers = [self._safe_text(cell) for cell in rows[0].find_all(["th", "td"])]
                for row in rows[1:]:
                    cells = [self._safe_text(td) for td in row.find_all("td")]
                    if cells:
                        label = cells[0]
                        for i, val in enumerate(cells[1:], 1):
                            if i < len(headers) and val:
                                data["风险指标"][f"{label}_{headers[i]}"] = val

        fgtb = soup.find("table", class_="fgtb")
        if fgtb:
            rows = fgtb.find_all("tr")
            for row in rows[1:]:
                cells = [self._safe_text(td) for td in row.find_all("td")]
                if cells and len(cells) >= 2:
                    data["投资风格"].append({
                        "报告期": cells[0],
                        "风格": cells[1] if len(cells) > 1 else "",
                    })
        return data

    def parse_fhsp(self) -> Dict:
        """分红送配"""
        soup = self._get_page("fhsp")
        if not soup:
            return {}
        data = {"分红记录": [], "拆分记录": []}
        search_scope = soup.find_all("div", class_=re.compile("w790|boxitem|box790")) or [soup]
        for scope in search_scope:
            for table in scope.find_all("table", class_=re.compile("comm|fhsp")):
                rows = table.find_all("tr")
                if not rows:
                    continue
                headers = [self._safe_text(th) for th in rows[0].find_all("th")]
                if not headers or any("热点" in h or "手机" in h for h in headers):
                    continue
                prev_h4 = table.find_previous("h4")
                section = self._safe_text(prev_h4) if prev_h4 else ""
                key = "拆分记录" if "拆分" in section else "分红记录"
                for row in rows[1:]:
                    cells = [self._safe_text(td) for td in row.find_all("td")]
                    if cells and headers and len(cells) == len(headers):
                        entry = dict(zip(headers, cells))
                        if not any("暂无" in v for v in entry.values()):
                            data[key].append(entry)
        return data

    def fetch_jdzf(self) -> Dict:
        """阶段涨幅"""
        html_content = self._get_api_data("jdzf")
        if not html_content:
            return {}
        soup = BeautifulSoup(html_content, "html.parser")
        data = {"阶段涨幅明细": []}
        uls = soup.find_all("ul")
        if len(uls) > 1:
            header_lis = uls[0].find_all("li")
            headers = [self._li_text(li) for li in header_lis]
            if headers and not headers[0]:
                headers[0] = "阶段"
            for ul in uls[1:]:
                lis = ul.find_all("li")
                values = [self._li_text(li) for li in lis]
                if values and any(values):
                    entry = {}
                    for i, h in enumerate(headers):
                        if i < len(values) and h:
                            entry[h] = values[i]
                    data["阶段涨幅明细"].append(entry)
        return data

    def fetch_jndzf(self) -> Dict:
        """季度涨幅、年度涨幅"""
        data = {}
        for api_key, title in [("jdndzf", "季度涨幅"), ("yearzf", "年度涨幅"), ("quarterzf", "季度涨幅明细")]:
            html = self._get_api_data(api_key)
            rows = self._parse_jndzf_table(html)
            if rows:
                data[title] = rows
        return data

    def _parse_jndzf_table(self, html_str: str) -> List[Dict]:
        if not html_str:
            return []
        soup = BeautifulSoup(html_str, "html.parser")
        for tip in soup.find_all("div", class_="infoTips"):
            tip.decompose()
        for p_tag in soup.find_all("p", class_="sifen"):
            p_tag.replace_with(p_tag.get_text(strip=True))
        for tbl in soup.find_all("table", class_="tbsi"):
            tbl.decompose()
        main_table = soup.find("table", class_="jndxq") or soup.find("table")
        if not main_table:
            return []
        rows = main_table.find_all("tr")
        if not rows:
            return []
        headers = [self._safe_text(th) for th in rows[0].find_all("th")]
        if headers and not headers[0]:
            headers[0] = "项目"
        result = []
        for row in rows[1:]:
            values = [self._safe_text(c) for c in row.find_all("td")]
            if not any(values):
                continue
            entry = {}
            for i, h in enumerate(headers):
                if i < len(values) and h:
                    entry[h] = values[i]
            result.append(entry)
        return result

    def fetch_jjcc(self) -> Dict:
        """基金持仓(股票)"""
        html = self._get_api_data("jjcc")
        return self._parse_api_html_full(html) if html else {}

    def fetch_zqcc(self) -> Dict:
        """债券持仓"""
        html = self._get_api_data("zqcc")
        return self._parse_api_html_full(html) if html else {}

    def fetch_ccbdzs(self) -> Dict:
        """持仓变动走势（持仓集中度 + 换手率）"""
        data = {"持仓集中度": [], "发起资金参与": []}
        text = self._get_f10_data_api("ccbdzs")
        for item in self._parse_f10_json_array(text):
            data["持仓集中度"].append({
                "报告期": item.get("REPORTDATE", ""),
                "前十持仓集中度(%)": item.get("FSTOCKCENTER", ""),
                "换手率(%)": item.get("STOCKTURNOVER", ""),
            })
        text2 = self._get_f10_data_api("nbzjcy")
        for item in self._parse_f10_json_array(text2):
            data["发起资金参与"].append({
                "报告期": item.get("REPORTDATE", ""),
                "持有份额": item.get("TOTALHOLD", ""),
                "持有比例(%)": item.get("HOLDRATIO", ""),
            })
        return data

    def fetch_hytz(self) -> Dict:
        """行业配置"""
        data = {"季度行业配置": []}
        result = self._get_json_api(self.HYPZ_API, {"fundCode": self.fund_code, "year": ""})
        if result and result.get("Data"):
            fund_data = result["Data"]
            data["基金名称"] = fund_data.get("ShortName", "")
            for quarter in fund_data.get("QuarterInfos", []):
                q_data = {
                    "季度": f"第{quarter.get('Quarter', '')}季度",
                    "截止日期": quarter.get("JZRQ", ""),
                    "行业列表": [],
                }
                for hy in quarter.get("HYPZInfo", []):
                    q_data["行业列表"].append({
                        "行业名称": hy.get("HYMC", ""),
                        "市值": hy.get("SZDesc", ""),
                        "占净值比(%)": hy.get("ZJZBL", ""),
                    })
                data["季度行业配置"].append(q_data)
        return data

    def parse_zcpz(self) -> Dict:
        """资产配置"""
        soup = self._get_page("zcpz")
        if not soup:
            return {}
        data = {"资产配置摘要": "", "资产配置明细": []}
        for box in soup.find_all("div", class_="boxitem"):
            text = self._safe_text(box)
            if "截至" in text and "净资产" in text:
                data["资产配置摘要"] = text[:300]
                break
        for table in soup.find_all("table", class_=re.compile("w782.*comm")):
            rows = table.find_all("tr")
            if not rows:
                continue
            headers = [self._safe_text(th) for th in rows[0].find_all(["th", "td"])]
            if not headers or any(kw in " ".join(headers) for kw in ["手机", "热点"]):
                continue
            for row in rows[1:]:
                cells = [self._safe_text(td) for td in row.find_all("td")]
                if cells and len(cells) == len(headers):
                    entry = dict(zip(headers, cells))
                    if any(v and v != "---" for v in entry.values()):
                        data["资产配置明细"].append(entry)
        return data

    def fetch_gmbd(self) -> Dict:
        """规模变动"""
        html = self._get_api_data("gmbd")
        return self._parse_api_html_full(html) if html else {}

    def fetch_cyrjg(self) -> Dict:
        """持有人结构"""
        html = self._get_api_data("cyrjg")
        return self._parse_api_html_full(html) if html else {}

    def fetch_cwzb(self) -> Dict:
        """财务指标"""
        html = self._get_api_data("cwzb")
        return self._parse_api_html_full(html) if html else {}

    def parse_srfx(self) -> Dict:
        """收入分析"""
        soup = self._get_page("srfx")
        if not soup:
            return {}
        data = {"收入明细": []}
        for table in soup.find_all("table", class_=re.compile("w782.*comm")):
            rows = table.find_all("tr")
            if not rows:
                continue
            headers = [self._safe_text(th) for th in rows[0].find_all(["th", "td"])]
            if not headers or any(kw in " ".join(headers) for kw in ["手机", "热点"]):
                continue
            for row in rows[1:]:
                cells = [self._safe_text(td) for td in row.find_all("td")]
                if cells and len(cells) == len(headers):
                    entry = dict(zip(headers, cells))
                    if any(v and v != "---" for v in entry.values()):
                        data["收入明细"].append(entry)
        return data

    def parse_fyfx(self) -> Dict:
        """费用分析"""
        soup = self._get_page("fyfx")
        if not soup:
            return {}
        data = {"费用明细": []}
        for table in soup.find_all("table", class_=re.compile("w782.*comm")):
            rows = table.find_all("tr")
            if not rows:
                continue
            headers = [self._safe_text(th) for th in rows[0].find_all(["th", "td"])]
            if not headers or any(kw in " ".join(headers) for kw in ["手机", "热点"]):
                continue
            for row in rows[1:]:
                cells = [self._safe_text(td) for td in row.find_all("td")]
                if cells and len(cells) == len(headers):
                    entry = dict(zip(headers, cells))
                    if any(v and v != "---" for v in entry.values()):
                        data["费用明细"].append(entry)
        return data

    # ================================================================== #
    #  提取关键筛选指标（供 fund_screener.py 二次筛选使用）
    # ================================================================== #

    def extract_screening_metrics(self) -> Dict[str, Any]:
        """
        快速采集用于筛选的关键指标，返回扁平化 dict。
        覆盖：风险指标（夏普/最大回撤/波动率等）、基金经理、持有人结构、评级。
        这是 fund_screener.py --enrich 模式的核心调用入口。
        """
        metrics = {"基金代码": self.fund_code}

        # 并发采集 特色数据 + 基金经理 + 持有人结构 + 基金评级 + 分红送配
        tasks = {
            "tsdata": self.parse_tsdata,
            "jjjl": self.parse_jjjl,
            "cyrjg": self.fetch_cyrjg,
            "jjpj": self.parse_jjpj,
            "fhsp": self.parse_fhsp,
        }
        results = {}
        with ThreadPoolExecutor(max_workers=5) as pool:
            futures = {pool.submit(fn): key for key, fn in tasks.items()}
            for future in as_completed(futures):
                key = futures[future]
                try:
                    results[key] = future.result()
                except Exception:
                    results[key] = {}

        # --- 从特色数据提取风险指标 ---
        tsdata = results.get("tsdata", {})
        risk = tsdata.get("风险指标", {})
        for raw_key, val in risk.items():
            # raw_key 格式: "标准差_近1年" / "夏普比率_近1年" / "最大回撤_近1年" 等
            metrics[raw_key] = self._to_float(val)

        risk_level = tsdata.get("风险等级", {})
        if risk_level:
            metrics["风险等级_全部基金"] = risk_level.get("在所有基金中", "")
            metrics["风险等级_同类基金"] = risk_level.get("在同类基金中", "")

        # --- 从基金经理提取关键信息 ---
        jjjl = results.get("jjjl", {})
        managers = jjjl.get("经理变动一览", [])
        if managers:
            # 取最近一条（当前经理）
            current = managers[0]
            metrics["基金经理"] = current.get("基金经理", "")
            # 计算任职天数
            start_str = current.get("任职日期", "") or current.get("起始期", "")
            if start_str:
                try:
                    # 处理 "YYYY-MM-DD -- 至今" 格式
                    date_str = start_str.split("--")[0].strip().split("至")[0].strip()
                    # 再处理可能的 "YYYY-MM-DD" 格式
                    date_str = re.search(r"\d{4}-\d{2}-\d{2}", date_str)
                    if date_str:
                        start_date = datetime.strptime(date_str.group(), "%Y-%m-%d")
                        metrics["经理任职天数"] = (datetime.now() - start_date).days
                        metrics["经理任职年限"] = round(metrics["经理任职天数"] / 365.25, 2)
                except Exception:
                    pass
            metrics["任期收益"] = current.get("任期收益", "") or current.get("任职回报", "")
        # 经理简介
        intros = jjjl.get("现任经理简介", [])
        if intros:
            metrics["基金经理简介"] = intros[0].get("简介", "")

        # --- 从持有人结构提取 ---
        cyrjg = results.get("cyrjg", {})
        # cyrjg 可能包含多个表格，取最近的一组
        for table_name, rows in cyrjg.items():
            if isinstance(rows, list) and rows:
                for row in rows:
                    if isinstance(row, dict):
                        for k, v in row.items():
                            if "机构" in k and "比例" in k:
                                val = self._to_float(v.replace("%", ""))
                                if val is not None:
                                    metrics["机构持有比例"] = val
                            elif "个人" in k and "比例" in k:
                                val = self._to_float(v.replace("%", ""))
                                if val is not None:
                                    metrics["个人持有比例"] = val
                            elif "内部" in k and "比例" in k:
                                val = self._to_float(v.replace("%", ""))
                                if val is not None:
                                    metrics["内部持有比例"] = val
                break  # 只取第一个表

        # --- 从评级提取 ---
        jjpj = results.get("jjpj", {})
        ratings = jjpj.get("评级数据", [])
        if ratings:
            latest = ratings[0]
            for cn_name in ["招商评级", "上海证券3年期", "上海证券5年期", "济安金信评级", "晨星评级"]:
                val = latest.get(cn_name, "---")
                if val != "---":
                    metrics[cn_name] = val
                    # 也存数字版本方便筛选
                    star_count = val.count("★")
                    if star_count > 0:
                        metrics[f"{cn_name}_数值"] = star_count

        # --- 从分红送配提取分红指标 ---
        fhsp = results.get("fhsp", {})
        dividend_records = fhsp.get("分红记录", [])
        metrics["累计分红次数"] = len(dividend_records)

        # 解析每条分红记录的日期和金额
        now = datetime.now()
        one_year_ago = now - timedelta(days=365)
        total_dividend_per_share = 0.0
        recent_1y_count = 0
        recent_1y_amount = 0.0

        for record in dividend_records:
            # 提取每份派现金额，格式如 "每份派现金0.0230元"
            amount_str = record.get("每份分红", "") or record.get("每10份分红", "")
            amount = 0.0
            per_10 = False
            if amount_str:
                m = re.search(r"([\d.]+)\s*元", amount_str)
                if m:
                    amount = float(m.group(1))
                    if "10份" in amount_str:
                        per_10 = True
                        amount = amount / 10.0

            total_dividend_per_share += amount

            # 解析日期判断是否在近1年内
            date_str = record.get("权益登记日", "") or record.get("除息日", "")
            if date_str:
                try:
                    d = datetime.strptime(date_str.strip(), "%Y-%m-%d")
                    if d >= one_year_ago:
                        recent_1y_count += 1
                        recent_1y_amount += amount
                except (ValueError, TypeError):
                    pass

        metrics["成立来累计每份派现"] = round(total_dividend_per_share, 4)
        metrics["近1年分红次数"] = recent_1y_count
        metrics["近1年累计每份派现"] = round(recent_1y_amount, 4)

        return metrics

    @staticmethod
    def _to_float(val) -> Optional[float]:
        if val is None:
            return None
        if isinstance(val, (int, float)):
            return float(val)
        val = str(val).strip().replace("%", "").replace("--", "").replace("---", "")
        if not val:
            return None
        try:
            return float(val)
        except ValueError:
            return None

    # ================================================================== #
    #  全量采集（供 --sections 参数使用）
    # ================================================================== #

    SECTION_MAP = {
        "基本概况":       ("jbgk",    "parse_jbgk"),
        "基金经理":       ("jjjl",    "parse_jjjl"),
        "基金评级":       ("jjpj",    "parse_jjpj"),
        "特色数据":       ("tsdata",  "parse_tsdata"),
        "分红送配":       ("fhsp",    "parse_fhsp"),
        "阶段涨幅":       ("jdzf",    "fetch_jdzf"),
        "季度年度涨幅":   ("jndzf",   "fetch_jndzf"),
        "基金持仓":       ("ccmx",    "fetch_jjcc"),
        "债券持仓":       ("ccmx1",   "fetch_zqcc"),
        "持仓变动走势":   ("ccbdzs",  "fetch_ccbdzs"),
        "行业配置":       ("hytz",    "fetch_hytz"),
        "资产配置":       ("zcpz",    "parse_zcpz"),
        "规模变动":       ("gmbd",    "fetch_gmbd"),
        "持有人结构":     ("cyrjg",   "fetch_cyrjg"),
        "财务指标":       ("cwzb",    "fetch_cwzb"),
        "收入分析":       ("srfx",    "parse_srfx"),
        "费用分析":       ("fyfx",    "parse_fyfx"),
    }

    def scrape_sections(self, sections: List[str] = None) -> Dict[str, Any]:
        """采集指定模块（或全部），返回 {模块名: 数据dict}"""
        if not sections:
            sections = list(self.SECTION_MAP.keys())

        total = len(sections)
        results = {}
        completed = [0]
        lock = threading.Lock()

        def _run(name):
            if name not in self.SECTION_MAP:
                return name, {}
            _, method_name = self.SECTION_MAP[name]
            try:
                func = getattr(self, method_name)
                data = func()
                with lock:
                    completed[0] += 1
                    print(f"  [{completed[0]}/{total}] OK {name}", file=sys.stderr)
                return name, data
            except Exception as e:
                with lock:
                    completed[0] += 1
                    print(f"  [{completed[0]}/{total}] FAIL {name}: {e}", file=sys.stderr)
                return name, {}

        print(f"开始采集基金 [{self.fund_code}] 的 {total} 个模块...", file=sys.stderr)
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = {pool.submit(_run, name): name for name in sections}
            for future in as_completed(futures):
                name, data = future.result()
                results[name] = data

        # 按 sections 顺序返回
        ordered = {}
        for name in sections:
            if name in results:
                ordered[name] = results[name]
        return ordered


# --------------------------------------------------------------------------- #
#  批量采集入口（供 fund_screener.py 调用）
# --------------------------------------------------------------------------- #

def batch_extract_metrics(fund_codes: List[str], max_workers: int = 8) -> List[Dict[str, Any]]:
    """
    批量采集多只基金的关键筛选指标。
    返回: [{基金代码, 夏普比率_近1年, 最大回撤_近1年, 基金经理, ...}, ...]
    """
    results = []
    total = len(fund_codes)
    completed = [0]
    lock = threading.Lock()

    def _scrape_one(code: str) -> Dict[str, Any]:
        scraper = FundDetailScraper(code, max_workers=4)
        metrics = scraper.extract_screening_metrics()
        with lock:
            completed[0] += 1
            print(f"  详情采集 [{completed[0]}/{total}] {code} 完成", file=sys.stderr)
        return metrics

    print(f"开始批量采集 {total} 只基金的详细指标...", file=sys.stderr)
    start = time.time()

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_scrape_one, code): code for code in fund_codes}
        for future in as_completed(futures):
            code = futures[future]
            try:
                metrics = future.result()
                results.append(metrics)
            except Exception as e:
                print(f"  详情采集 {code} 失败: {e}", file=sys.stderr)
                results.append({"基金代码": code, "_error": str(e)})

    # 按输入顺序排序，避免并发完成顺序导致输出抖动
    code_order = {code: i for i, code in enumerate(fund_codes)}
    results.sort(key=lambda r: code_order.get(r.get("基金代码", ""), 999))

    elapsed = time.time() - start
    print(f"批量采集完成，{total} 只基金耗时 {elapsed:.1f} 秒", file=sys.stderr)
    return results



# --------------------------------------------------------------------------- #
#  数据格式化
# --------------------------------------------------------------------------- #

def data_to_markdown(fund_code: str, data: Dict[str, Any]) -> str:
    """将采集数据转换为 Markdown"""
    lines = [f"# 基金 {fund_code} 详细信息\n"]
    lines.append(f"> 数据来源：天天基金网 | 采集时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"> 📎 信源API：`https://fundf10.eastmoney.com/FundArchivesDatas.aspx` (特色数据/持仓) | `https://fundf10.eastmoney.com/F10DataApi.aspx` (行业配置/资产配置) | `https://api.fund.eastmoney.com/f10/lsjz` (净值) | `https://api.fund.eastmoney.com/F10/JJPJ/` (评级) | `https://fundf10.eastmoney.com/jbgk_{fund_code}.html` (概况)\n")

    for section_name, section_data in data.items():
        if not section_data:
            continue
        lines.append(f"## {section_name}\n")
        lines.append(_format_data(section_data))
        lines.append("")

    return "\n".join(lines)


def _format_data(data: Any, level: int = 0) -> str:
    """递归格式化数据"""
    if isinstance(data, dict):
        lines = []
        for key, val in data.items():
            if isinstance(val, list):
                lines.append(f"### {key}\n")
                lines.append(_format_list(val))
            elif isinstance(val, dict):
                lines.append(f"### {key}\n")
                lines.append(_format_data(val, level + 1))
            elif val:
                lines.append(f"- **{key}**: {val}")
        return "\n".join(lines)
    elif isinstance(data, list):
        return _format_list(data)
    elif isinstance(data, str):
        return data
    return str(data) if data else ""


def _format_list(items: List) -> str:
    """将列表格式化为 Markdown 表格"""
    if not items:
        return ""
    dict_items = [it for it in items if isinstance(it, dict)]
    if dict_items:
        headers = list(dict_items[0].keys())
        lines = ["| " + " | ".join(headers) + " |"]
        lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
        for item in dict_items:
            cells = [str(item.get(h, "")).replace("|", "/").replace("\n", " ") for h in headers]
            lines.append("| " + " | ".join(cells) + " |")
        return "\n".join(lines) + "\n"
    return "\n".join(f"- {item}" for item in items)


# --------------------------------------------------------------------------- #
#  CLI 入口
# --------------------------------------------------------------------------- #

def main():
    parser = argparse.ArgumentParser(
        description="基金详细信息采集工具 — ETF 顾问团队",
    )
    parser.add_argument("codes", nargs="?", default="",
                        help="基金代码，逗号分隔支持批量 (如: 000001,000002)")
    parser.add_argument("--sections", "-s", default="",
                        help="采集模块，逗号分隔 (如: 特色数据,基金经理,基金评级)")
    parser.add_argument("--metrics-only", "-m", action="store_true",
                        help="仅提取关键筛选指标（扁平化JSON）")
    parser.add_argument("--json", "-j", action="store_true",
                        help="JSON 格式输出")
    parser.add_argument("--output", "-o", default="",
                        help="输出文件路径")
    parser.add_argument("--workers", "-w", type=int, default=8,
                        help="并发线程数 (默认8)")
    parser.add_argument("--list-sections", action="store_true",
                        help="列出所有可用模块")

    args = parser.parse_args()
    sys.stdout.reconfigure(encoding='utf-8')

    if args.list_sections:
        print("可用的采集模块：\n")
        for name in FundDetailScraper.ALL_SECTIONS:
            print(f"  - {name}")
        sys.exit(0)

    codes = [c.strip() for c in args.codes.split(",") if c.strip()]
    if not codes:
        print("[错误] 请提供至少一个基金代码", file=sys.stderr)
        sys.exit(1)

    sections = [s.strip() for s in args.sections.split(",") if s.strip()] if args.sections else None

    # 仅提取筛选指标模式
    if args.metrics_only:
        results = batch_extract_metrics(codes, max_workers=args.workers)
        output = json.dumps(results, ensure_ascii=False, indent=2)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output)
            print(f"结果已保存到: {args.output}", file=sys.stderr)
        else:
            print(output)
        sys.exit(0)

    # 全量/指定模块采集
    all_results = {}
    for code in codes:
        scraper = FundDetailScraper(code, max_workers=args.workers)
        data = scraper.scrape_sections(sections)
        all_results[code] = data

    if args.json:
        output = json.dumps(all_results, ensure_ascii=False, indent=2)
    else:
        parts = []
        for code, data in all_results.items():
            parts.append(data_to_markdown(code, data))
        output = "\n---\n\n".join(parts)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"结果已保存到: {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
