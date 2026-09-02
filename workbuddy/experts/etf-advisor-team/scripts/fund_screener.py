#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
公募基金多维度筛选脚本 — ETF 顾问团队内置筛选引擎
功能：从天天基金网获取全市场公募基金排行数据，支持多条件组合筛选，
      可选启用二次富化（enrich）获取夏普比率/最大回撤/基金经理等高级指标进行深度筛选。
数据源：天天基金网 rankhandler.aspx API + fund_detail_scraper.py（高级指标）

用法：
  # 基础筛选（秒级）
  python fund_screener.py --type gp --conditions '近1年>20,最新规模>2' --sort 近1年 --limit 20

  # 带高级指标二次筛选（先缩小候选池，再逐只采集详细指标）
  python fund_screener.py --type all --conditions '近1年>50,最新规模>2' --sort 近1年 --limit 20 \
      --enrich --enrich-conditions '夏普比率_近1年>2,经理任职年限>=2'

  # 获取 Top N 基金的详细信息
  python fund_screener.py --type all --conditions '近1年>80' --sort 近1年 --detail-top 5

  # 使用内置模板
  python fund_screener.py --template 长跑型主动权益基金 --limit 20

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


import os
import re
import sys
import json
import time
import math
import argparse
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# --------------------------------------------------------------------------- #
#  常量
# --------------------------------------------------------------------------- #

RANK_API = "http://fund.eastmoney.com/data/rankhandler.aspx"

# fund_detail_scraper.py 的路径（同目录）
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 高级指标字段别名（二次筛选用）— 来自 fund_detail_scraper.py extract_screening_metrics()
ENRICH_FIELD_ALIAS = {
    "夏普比率": "夏普比率_近1年",
    "夏普比率近1年": "夏普比率_近1年",
    "夏普比率近2年": "夏普比率_近2年",
    "夏普比率近3年": "夏普比率_近3年",
    "最大回撤": "最大回撤_近1年",
    "最大回撤近1年": "最大回撤_近1年",
    "最大回撤近2年": "最大回撤_近2年",
    "最大回撤近3年": "最大回撤_近3年",
    "标准差": "标准差_近1年",
    "标准差近1年": "标准差_近1年",
    "标准差近2年": "标准差_近2年",
    "标准差近3年": "标准差_近3年",
    "经理任职年限": "经理任职年限",
    "经理任职天数": "经理任职天数",
    "机构持有比例": "机构持有比例",
    "个人持有比例": "个人持有比例",
    "招商评级": "招商评级_数值",
    "晨星评级": "晨星评级_数值",
    "济安金信评级": "济安金信评级_数值",
    "累计分红次数": "累计分红次数",
    "近1年分红次数": "近1年分红次数",
    "分红次数": "近1年分红次数",
    "近1年累计每份派现": "近1年累计每份派现",
    "每份派现": "近1年累计每份派现",
    "成立来累计每份派现": "成立来累计每份派现",
}

# API 返回每条记录的字段索引 (逗号分隔, 共25字段)
FIELD_MAP = {
    "基金代码":      0,
    "基金简称":      1,
    "拼音缩写":      2,
    "净值日期":      3,
    "单位净值":      4,
    "累计净值":      5,
    "日增长率":      6,
    "近1周":         7,
    "近1月":         8,
    "近3月":         9,
    "近6月":        10,
    "近1年":        11,
    "近2年":        12,
    "近3年":        13,
    "今年来":       14,
    "成立来":       15,
    "成立日期":     16,
    "购买标志":     17,
    "自定义数值":   18,
    "原费率":       19,
    "优惠费率":     20,
    "费率标志1":    21,
    "费率2":        22,
    "费率标志2":    23,
    "最新规模":     24,   # 单位：亿元（从API返回数据推断）
}

# 支持的筛选字段别名映射 → 标准字段名
FIELD_ALIAS = {
    # 收益率
    "近1年收益率":   "近1年",
    "近2年收益率":   "近2年",
    "近3年收益率":   "近3年",
    "近6月收益率":   "近6月",
    "近3月收益率":   "近3月",
    "近1月收益率":   "近1月",
    "近1周收益率":   "近1周",
    "日增长率":     "日增长率",
    "今年以来":     "今年来",
    "今年以来收益率": "今年来",
    "成立以来":     "成立来",
    "成立以来收益率": "成立来",
    # 净值
    "单位净值":     "单位净值",
    "累计净值":     "累计净值",
    # 规模
    "最新规模":     "最新规模",
    "规模":         "最新规模",
    # 成立时间
    "成立日期":     "成立日期",
    "成立年限":     "成立年限",  # 特殊：需计算
    # 简称 / 代码
    "基金简称":     "基金简称",
    "基金代码":     "基金代码",
    "基金名称":     "基金简称",
}

# 基金类型代码
FUND_TYPE_MAP = {
    "all":   "全部",
    "gp":    "股票型",
    "hh":    "混合型",
    "zq":    "债券型",
    "zs":    "指数型",
    "qdii":  "QDII",
    "fof":   "FOF",
    "hb":    "货币型",
    # 用户可用中文
    "全部":   "all",
    "股票型": "gp",
    "混合型": "hh",
    "债券型": "zq",
    "指数型": "zs",
    "QDII":  "qdii",
    "FOF":   "fof",
    "货币型": "hb",
    "股票":   "gp",
    "混合":   "hh",
    "债券":   "zq",
    "指数":   "zs",
}

# 排序字段 → API sc 参数
SORT_SC_MAP = {
    "日增长率": "rzdf",
    "近1周":    "1zzf",
    "近1月":    "1yzf",
    "近3月":    "3yzf",
    "近6月":    "6yzf",
    "近1年":    "1nzf",
    "近2年":    "2nzf",
    "近3年":    "3nzf",
    "今年来":   "jnzf",
    "成立来":   "lnzf",
    "单位净值": "dwjz",
    "累计净值": "ljjz",
    "近1年收益率": "1nzf",
    "近3年收益率": "3nzf",
}

# --------------------------------------------------------------------------- #
#  内置筛选模板
# --------------------------------------------------------------------------- #

TEMPLATES = {
    "长跑型主动权益基金": {
        "fund_type": "all",
        "conditions": [
            ("成立年限", ">=", 5),
            ("近3年", "top%", 25),
            ("最新规模", ">=", 2),
            ("最新规模", "<=", 200),
        ],
        "sort_by": "近3年",
        "sort_desc": True,
        "description": "成立≥5年 + 近3年同类排名前25% + 规模2-200亿",
    },
    "稳健型纯债基金": {
        "fund_type": "zq",
        "conditions": [
            ("近1年", ">", 0),
            ("最新规模", ">=", 5),
        ],
        "sort_by": "近1年",
        "sort_desc": True,
        "description": "债券型 + 近1年收益>0 + 规模≥5亿",
    },
    "低波动固收+基金": {
        "fund_type": "hh",
        "conditions": [
            ("近1年", ">", 3),
            ("近3月", ">", 0),
        ],
        "sort_by": "近1年",
        "sort_desc": True,
        "description": "混合型 + 近1年收益>3% + 近3月收益>0",
    },
    "高分红指数基金": {
        "fund_type": "zs",
        "conditions": [
            ("最新规模", ">=", 5),
            ("近1年", ">", 0),
        ],
        "sort_by": "近1年",
        "sort_desc": True,
        "description": "指数型 + 规模≥5亿 + 近1年收益>0",
    },
    "近1年高收益基金": {
        "fund_type": "all",
        "conditions": [
            ("近1年", ">", 80),
            ("最新规模", ">=", 1),
        ],
        "sort_by": "近1年",
        "sort_desc": True,
        "description": "全市场 + 近1年收益>80% + 规模≥1亿",
    },
}


# --------------------------------------------------------------------------- #
#  核心类
# --------------------------------------------------------------------------- #

class FundScreener:
    """公募基金多维度筛选引擎"""

    PAGE_SIZE = 5000  # 每页获取条数（天天基金API最大支持约5000）

    def __init__(self, max_workers: int = 8):
        self.max_workers = max_workers
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "http://fund.eastmoney.com/data/fundranking.html",
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        })
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=max_workers,
            pool_maxsize=max_workers * 2,
            max_retries=3,
        )
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self._print_lock = threading.Lock()

    def _print(self, msg: str):
        with self._print_lock:
            print(msg, file=sys.stderr)

    # ------------------------------------------------------------------ #
    #  Step 1: 从天天基金网获取全市场基金排行数据
    # ------------------------------------------------------------------ #

    def _fetch_rank_page(self, fund_type: str, sort_col: str, sort_desc: bool,
                         page: int, page_size: int, sd: str, ed: str) -> Tuple[List[str], int]:
        """获取单页排行数据，返回 (记录列表, 总记录数)"""
        params = {
            "op": "ph",
            "dt": "kf",
            "ft": fund_type,
            "rs": "",
            "gs": 0,
            "sc": sort_col,
            "st": "desc" if sort_desc else "asc",
            "sd": sd,
            "ed": ed,
            "qdii": "",
            "tabSubtype": ",,,,,",
            "pi": page,
            "pn": page_size,
            "dx": 1,
            "v": time.time(),
        }
        resp = self.session.get(RANK_API, params=params, timeout=30)
        text = resp.text

        # 解析 var rankData = {datas:[...],allRecords:N,...};
        total_match = re.search(r"allRecords:(\d+)", text)
        total = int(total_match.group(1)) if total_match else 0

        datas_match = re.search(r'datas:\[(.*?)\],allRecords', text, re.DOTALL)
        if not datas_match:
            return [], total

        raw = datas_match.group(1).strip()
        if not raw:
            return [], total

        # 每条记录被双引号包裹，以","分隔
        records = re.findall(r'"([^"]+)"', raw)
        return records, total

    def fetch_all_funds(self, fund_type: str = "all", sort_col: str = "zzf",
                        sort_desc: bool = True) -> List[Dict[str, Any]]:
        """获取全市场指定类型基金的排行数据，返回结构化列表"""
        today = datetime.now()
        ed = today.strftime("%Y-%m-%d")
        sd = (today - timedelta(days=365)).strftime("%Y-%m-%d")

        self._print(f"正在获取 [{FUND_TYPE_MAP.get(fund_type, fund_type)}] 类型基金数据...")

        # 先获取第1页以确定总数
        records_p1, total = self._fetch_rank_page(fund_type, sort_col, sort_desc,
                                                   1, self.PAGE_SIZE, sd, ed)
        if total == 0:
            self._print("未获取到任何基金数据。")
            return []

        self._print(f"全市场 [{FUND_TYPE_MAP.get(fund_type, fund_type)}] 基金总数: {total}")

        all_records = list(records_p1)

        # 如果还有更多页，并发获取
        total_pages = math.ceil(total / self.PAGE_SIZE)
        if total_pages > 1:
            self._print(f"分页获取: 共 {total_pages} 页, 并发 {self.max_workers} 线程...")
            with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
                futures = {
                    pool.submit(
                        self._fetch_rank_page, fund_type, sort_col, sort_desc,
                        p, self.PAGE_SIZE, sd, ed
                    ): p
                    for p in range(2, total_pages + 1)
                }
                for future in as_completed(futures):
                    page_no = futures[future]
                    try:
                        recs, _ = future.result()
                        all_records.extend(recs)
                        self._print(f"  第 {page_no}/{total_pages} 页完成, 本页 {len(recs)} 条")
                    except Exception as e:
                        self._print(f"  第 {page_no}/{total_pages} 页失败: {e}")

        self._print(f"共获取 {len(all_records)} 条记录")

        # 解析为结构化数据
        funds = []
        for rec in all_records:
            fields = rec.split(",")
            if len(fields) < 25:
                continue
            fund = self._parse_record(fields)
            if fund:
                funds.append(fund)

        self._print(f"解析完成: {len(funds)} 只基金")
        return funds

    def _parse_record(self, fields: List[str]) -> Optional[Dict[str, Any]]:
        """将逗号分隔的字段列表解析为结构化字典"""
        try:
            fund = {
                "基金代码": fields[0].strip(),
                "基金简称": fields[1].strip(),
                "拼音缩写": fields[2].strip(),
                "净值日期": fields[3].strip(),
                "单位净值": self._to_float(fields[4]),
                "累计净值": self._to_float(fields[5]),
                "日增长率": self._to_float(fields[6]),
                "近1周":    self._to_float(fields[7]),
                "近1月":    self._to_float(fields[8]),
                "近3月":    self._to_float(fields[9]),
                "近6月":    self._to_float(fields[10]),
                "近1年":    self._to_float(fields[11]),
                "近2年":    self._to_float(fields[12]),
                "近3年":    self._to_float(fields[13]),
                "今年来":   self._to_float(fields[14]),
                "成立来":   self._to_float(fields[15]),
                "成立日期": fields[16].strip(),
                "原费率":   fields[19].strip() if len(fields) > 19 else "",
                "优惠费率": fields[20].strip() if len(fields) > 20 else "",
                "最新规模": self._to_float(fields[24]) if len(fields) > 24 else None,
            }

            # 计算成立年限
            if fund["成立日期"]:
                try:
                    est_date = datetime.strptime(fund["成立日期"], "%Y-%m-%d")
                    fund["成立年限"] = round((datetime.now() - est_date).days / 365.25, 2)
                except ValueError:
                    fund["成立年限"] = None
            else:
                fund["成立年限"] = None

            return fund
        except (IndexError, ValueError):
            return None

    @staticmethod
    def _to_float(val: str) -> Optional[float]:
        """安全转换字符串为浮点数"""
        if not val or val.strip() in ("", "---", "--", "null"):
            return None
        val = val.strip().replace("%", "")
        try:
            return float(val)
        except ValueError:
            return None

    # ------------------------------------------------------------------ #
    #  Step 2: 多条件筛选
    # ------------------------------------------------------------------ #

    @staticmethod
    def parse_conditions(cond_str: str) -> List[Tuple[str, str, Any]]:
        """
        解析条件字符串，支持格式:
        '近1年收益率>20,最新规模>2,成立年限>=3,基金简称 contains 半导体'
        支持运算符: >, >=, <, <=, =, !=, top%, contains, !contains
        返回: [(字段名, 运算符, 数值或字符串), ...]
        """
        conditions = []
        if not cond_str:
            return conditions

        parts = [c.strip() for c in cond_str.split(",") if c.strip()]
        # 支持的运算符（顺序重要，先匹配长的）
        # 注意: contains/!contains 为字符串包含匹配，需优先于数值运算符检测
        str_ops = ["!contains", "contains"]
        num_ops = [">=", "<=", "!=", ">", "<", "=", "top%"]

        for part in parts:
            matched = False
            # 先尝试字符串运算符
            for op in str_ops:
                if op in part:
                    idx = part.index(op)
                    field = part[:idx].strip()
                    value_str = part[idx + len(op):].strip()
                    field = FIELD_ALIAS.get(field, field)
                    if field and value_str:
                        conditions.append((field, op, value_str))
                        matched = True
                    break
            if matched:
                continue
            # 再尝试数值运算符
            for op in num_ops:
                if op in part:
                    idx = part.index(op)
                    field = part[:idx].strip()
                    value_str = part[idx + len(op):].strip()
                    # 标准化字段名
                    field = FIELD_ALIAS.get(field, field)
                    try:
                        value = float(value_str)
                    except ValueError:
                        continue
                    conditions.append((field, op, value))
                    matched = True
                    break
            if not matched:
                print(f"[警告] 无法解析条件: {part}", file=sys.stderr)

        return conditions

    def apply_filter(self, funds: List[Dict], conditions: List[Tuple[str, str, Any]],
                     logic: str = "AND") -> Tuple[List[Dict], List[Dict[str, Any]]]:
        """
        对基金列表应用筛选条件。
        返回: (符合条件的基金列表, 筛选漏斗步骤记录)
        """
        funnel = []
        funnel.append({
            "步骤": "初始标的池",
            "条件": "全市场符合品类范围的基金",
            "剩余数量": len(funds),
        })

        if not conditions:
            return funds, funnel

        if logic == "AND":
            result = list(funds)
            for field, op, value in conditions:
                before = len(result)
                result = [f for f in result if self._check_condition(f, field, op, value, funds)]
                # 漏斗显示：字符串运算符用引号包裹值
                display_val = f'"{value}"' if isinstance(value, str) else value
                funnel.append({
                    "步骤": f"条件过滤: {field} {op} {display_val}",
                    "条件": f"{field} {op} {display_val}",
                    "过滤前": before,
                    "剩余数量": len(result),
                    "淘汰数量": before - len(result),
                })
        elif logic == "OR":
            result_set = set()
            for field, op, value in conditions:
                matched = [i for i, f in enumerate(funds) if self._check_condition(f, field, op, value, funds)]
                result_set.update(matched)
                display_val = f'"{value}"' if isinstance(value, str) else value
                funnel.append({
                    "步骤": f"条件匹配(OR): {field} {op} {display_val}",
                    "条件": f"{field} {op} {display_val}",
                    "本条件匹配数": len(matched),
                    "累计匹配数": len(result_set),
                })
            result = [funds[i] for i in sorted(result_set)]
        else:
            result = list(funds)

        funnel.append({
            "步骤": "最终筛选结果",
            "条件": f"全部条件({logic})",
            "剩余数量": len(result),
        })

        return result, funnel

    def _check_condition(self, fund: Dict, field: str, op: str, value: Any,
                         all_funds: List[Dict] = None) -> bool:
        """检查单只基金是否满足单个条件"""
        fund_val = fund.get(field)

        # contains / !contains: 字符串包含匹配
        if op == "contains":
            if fund_val is None:
                return False
            return str(value) in str(fund_val)
        elif op == "!contains":
            if fund_val is None:
                return True  # 值为空时视为不包含
            return str(value) not in str(fund_val)

        # top% 特殊处理：排名百分比筛选
        if op == "top%":
            if all_funds is None or fund_val is None:
                return False
            # 获取所有非None值并排序（降序，收益率越高排名越靠前）
            all_vals = [f.get(field) for f in all_funds if f.get(field) is not None]
            if not all_vals:
                return False
            all_vals.sort(reverse=True)
            total = len(all_vals)
            try:
                rank = all_vals.index(fund_val) + 1
            except ValueError:
                return False
            percentile = (rank / total) * 100
            return percentile <= value

        if fund_val is None:
            return False

        if op == ">":
            return fund_val > value
        elif op == ">=":
            return fund_val >= value
        elif op == "<":
            return fund_val < value
        elif op == "<=":
            return fund_val <= value
        elif op == "=":
            return abs(fund_val - value) < 0.001
        elif op == "!=":
            return abs(fund_val - value) >= 0.001
        return False

    # ------------------------------------------------------------------ #
    #  Step 3: 排序与输出
    # ------------------------------------------------------------------ #

    @staticmethod
    def sort_funds(funds: List[Dict], sort_by: str, desc: bool = True) -> List[Dict]:
        """按指定字段排序"""
        sort_by = FIELD_ALIAS.get(sort_by, sort_by)
        return sorted(
            funds,
            key=lambda f: (f.get(sort_by) is not None, f.get(sort_by) or 0),
            reverse=desc,
        )

    def to_json(self, funds: List[Dict], funnel: List[Dict],
                fund_type: str, conditions: List[Tuple], sort_by: str,
                limit: int) -> Dict:
        """输出为结构化JSON"""
        display = funds[:limit]
        return {
            "筛选任务": {
                "筛选范围": f"{FUND_TYPE_MAP.get(fund_type, fund_type)}公募基金",
                "数据截止日期": datetime.now().strftime("%Y-%m-%d"),
                "数据来源": "天天基金网",
                "筛选条件": [
                    {"字段": f, "运算符": o, "阈值": v}
                    for f, o, v in conditions
                ],
                "排序字段": sort_by,
                "结果数量上限": limit,
            },
            "筛选漏斗": funnel,
            "筛选结果": [
                {
                    "序号": i + 1,
                    "基金代码": f["基金代码"],
                    "基金简称": f["基金简称"],
                    "成立日期": f["成立日期"],
                    "最新规模(亿元)": f.get("最新规模"),
                    "单位净值": f.get("单位净值"),
                    "日增长率": f.get("日增长率"),
                    "近1周": f.get("近1周"),
                    "近1月": f.get("近1月"),
                    "近3月": f.get("近3月"),
                    "近6月": f.get("近6月"),
                    "近1年": f.get("近1年"),
                    "近2年": f.get("近2年"),
                    "近3年": f.get("近3年"),
                    "今年来": f.get("今年来"),
                    "成立来": f.get("成立来"),
                    "成立年限": f.get("成立年限"),
                    "优惠费率": f.get("优惠费率"),
                }
                for i, f in enumerate(display)
            ],
            "总符合条件数": len(funds),
        }

    def to_markdown(self, funds: List[Dict], funnel: List[Dict],
                    fund_type: str, conditions: List[Tuple], sort_by: str,
                    limit: int, template_name: str = None, enrich_data: Dict = None) -> str:
        """输出为标准化 Markdown 格式"""
        lines = []
        today = datetime.now().strftime("%Y-%m-%d")
        display = funds[:limit]

        # ---- 一、筛选任务核心信息 ----
        lines.append("# 公募基金筛选结果报告\n")
        lines.append("## 【一、筛选任务核心信息】\n")
        lines.append(f"1. **筛选范围**：{FUND_TYPE_MAP.get(fund_type, fund_type)}公募基金 | "
                     f"市场范围：中国境内 | 数据截止日期：{today}")
        lines.append(f"   - 数据来源：天天基金网（fund.eastmoney.com）")
        lines.append(f"   - 📎 信源API：`http://fund.eastmoney.com/data/rankhandler.aspx` (基金排行筛选)")
        if enrich_data:
            lines.append(f"   - 📎 增强信源：`https://fundf10.eastmoney.com/FundArchivesDatas.aspx` (特色数据/风险指标)")
        lines.append("")

        if template_name:
            tpl = TEMPLATES.get(template_name, {})
            lines.append(f"2. **使用模板**：「{template_name}」")
            lines.append(f"   - 模板说明：{tpl.get('description', '')}\n")

        lines.append(f"3. **筛选条件**：")
        if conditions:
            for i, (f, o, v) in enumerate(conditions, 1):
                if o == "contains":
                    v_display = f'包含"{v}"'
                    lines.append(f"   - 条件{i}：{f} {v_display}")
                elif o == "!contains":
                    v_display = f'不包含"{v}"'
                    lines.append(f"   - 条件{i}：{f} {v_display}")
                else:
                    v_display = f"{v}%" if "%" in str(o) else v
                    lines.append(f"   - 条件{i}：{f} {o} {v_display}")
        else:
            lines.append("   - 无额外筛选条件（返回全部）")
        lines.append(f"\n4. **排序规则**：按 {sort_by} 降序排列")
        lines.append(f"5. **输出上限**：{limit} 条\n")

        # ---- 二、筛选过程回溯 ----
        lines.append("## 【二、筛选过程回溯】\n")
        lines.append("| 步骤 | 条件 | 剩余数量 |")
        lines.append("|------|------|----------|")
        for step in funnel:
            lines.append(
                f"| {step.get('步骤', '')} | {step.get('条件', '')} | "
                f"{step.get('剩余数量', '')} |"
            )
        lines.append("")

        # ---- 三、筛选结果明细 ----
        lines.append("## 【三、筛选结果明细】\n")
        lines.append(f"共 **{len(funds)}** 只基金符合全部条件，"
                     f"以下展示前 **{len(display)}** 条：\n")

        # 表头
        header = ("| 序号 | 基金代码 | 基金简称 | 成立日期 | 最新规模(亿元) | "
                  "单位净值 | 近1月 | 近3月 | 近6月 | 近1年 | 近3年 | "
                  "今年来 | 成立来 | 优惠费率 |")
        sep = ("|------|----------|----------|----------|---------------|"
               "----------|-------|-------|-------|-------|-------|"
               "--------|--------|----------|")
        lines.append(header)
        lines.append(sep)

        for i, f in enumerate(display, 1):
            lines.append(
                f"| {i} "
                f"| {f['基金代码']} "
                f"| {f['基金简称']} "
                f"| {f.get('成立日期', '')} "
                f"| {self._fmt(f.get('最新规模'))} "
                f"| {self._fmt(f.get('单位净值'))} "
                f"| {self._pct(f.get('近1月'))} "
                f"| {self._pct(f.get('近3月'))} "
                f"| {self._pct(f.get('近6月'))} "
                f"| {self._pct(f.get('近1年'))} "
                f"| {self._pct(f.get('近3年'))} "
                f"| {self._pct(f.get('今年来'))} "
                f"| {self._pct(f.get('成立来'))} "
                f"| {f.get('优惠费率', '')} |"
            )

        lines.append("")

        # Top3 客观数据亮点
        if len(display) >= 1:
            lines.append("### Top标的客观数据亮点\n")
            for i, f in enumerate(display[:3], 1):
                highlights = []
                if f.get("近1年") is not None:
                    highlights.append(f"近1年收益率 {f['近1年']}%")
                if f.get("近3年") is not None:
                    highlights.append(f"近3年收益率 {f['近3年']}%")
                if f.get("最新规模") is not None:
                    highlights.append(f"最新规模 {f['最新规模']}亿元")
                if f.get("成立年限") is not None:
                    highlights.append(f"成立 {f['成立年限']:.1f} 年")
                # 高级指标（如果有）
                code = f["基金代码"]
                if enrich_data and code in enrich_data:
                    m = enrich_data[code]
                    if m.get("夏普比率_近1年") is not None:
                        highlights.append(f"夏普比率(近1年) {m['夏普比率_近1年']}")
                    if m.get("最大回撤_近1年") is not None:
                        highlights.append(f"最大回撤(近1年) {m['最大回撤_近1年']}")
                    if m.get("基金经理"):
                        highlights.append(f"基金经理 {m['基金经理']}")
                    if m.get("经理任职年限") is not None:
                        highlights.append(f"任职 {m['经理任职年限']} 年")
                lines.append(f"- **Top{i} {f['基金代码']} {f['基金简称']}**："
                             f"{'；'.join(highlights)}")
            lines.append("")

        # 高级指标明细表（如果有 enrich_data）
        if enrich_data and len(display) > 0:
            enriched_display = [f for f in display if f["基金代码"] in enrich_data]
            if enriched_display:
                lines.append("### 高级指标明细\n")
                lines.append("| 基金代码 | 基金简称 | 夏普比率(1Y) | 最大回撤(1Y) | 标准差(1Y) | 基金经理 | 任职年限 | 机构占比 |")
                lines.append("|----------|----------|-------------|-------------|-----------|----------|---------|---------|")
                for f in enriched_display:
                    m = enrich_data.get(f["基金代码"], {})
                    lines.append(
                        f"| {f['基金代码']} "
                        f"| {f['基金简称']} "
                        f"| {self._fmt_val(m.get('夏普比率_近1年'))} "
                        f"| {self._fmt_val(m.get('最大回撤_近1年'))} "
                        f"| {self._fmt_val(m.get('标准差_近1年'))} "
                        f"| {m.get('基金经理', '--')} "
                        f"| {self._fmt_val(m.get('经理任职年限'))} "
                        f"| {self._fmt_val(m.get('机构持有比例'), '%')} |"
                    )
                lines.append("")

        # ---- 四、合规与风险强制提示 ----
        lines.append("## 【四、合规与风险强制提示】\n")
        lines.append("> 以上筛选结果仅基于公开历史数据完成条件匹配，不构成任何投资建议、"
                     "收益承诺或产品推荐。基金有风险，投资需谨慎。历史业绩不代表未来表现，"
                     "基金的过往业绩并不预示其未来收益表现。\n")

        # 专项风险提示
        type_name = FUND_TYPE_MAP.get(fund_type, fund_type)
        if fund_type in ("gp", "股票型"):
            lines.append("**专项风险提示**：股票型基金主要投资于股票市场，"
                         "受宏观经济、政策变化、市场情绪等因素影响，净值波动较大，"
                         "可能面临较大的短期亏损风险。\n")
        elif fund_type in ("hh", "混合型"):
            lines.append("**专项风险提示**：混合型基金投资于股票和债券等多类资产，"
                         "虽然相比纯股票型基金风险有所分散，但仍存在较大的市场波动风险。\n")
        elif fund_type in ("zq", "债券型"):
            lines.append("**专项风险提示**：债券型基金主要面临利率风险和信用风险，"
                         "在利率上行周期中可能出现净值回撤。\n")
        elif fund_type in ("qdii", "QDII"):
            lines.append("**专项风险提示**：QDII基金投资于境外市场，除市场风险外，"
                         "还面临汇率波动风险、境外市场政策变化风险等。\n")
        elif fund_type in ("zs", "指数型"):
            lines.append("**专项风险提示**：指数型基金以跟踪特定指数为目标，"
                         "存在跟踪误差风险，且在指数下跌时基金净值同样会下跌。\n")
        else:
            lines.append(f"**专项风险提示**：{type_name}基金存在与其投资策略相关的特定风险，"
                         f"请仔细评估自身风险承受能力。\n")

        lines.append("> 建议您在投资前仔细阅读基金的《基金合同》《招募说明书》等法律文件，"
                     "充分了解产品的风险收益特征与自身风险承受能力。\n")

        # ---- 五、补充优化建议 ----
        lines.append("## 【五、补充优化建议】\n")
        if len(funds) > 100:
            lines.append(f"1. 本次筛选结果数量较多（{len(funds)}只），"
                         f"建议增加筛选条件以缩小范围，如增加规模、成立年限、"
                         f"近3年收益率等条件。")
        elif len(funds) == 0:
            lines.append("1. 本次筛选无符合条件的标的，建议适当放宽筛选条件。")
        else:
            lines.append(f"1. 本次筛选结果 {len(funds)} 只基金，数量适中。")

        lines.append("2. 可补充的进阶筛选维度：基金经理任职年限、最大回撤、"
                     "夏普比率、机构持有比例等（使用 `--enrich` 参数启用高级指标筛选）。")
        lines.append("3. 适用场景模板推荐：" + "、".join(
            f"「{name}」" for name in list(TEMPLATES.keys())[:3]
        ))
        lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _fmt(val) -> str:
        if val is None:
            return "--"
        if isinstance(val, float):
            return f"{val:.4f}" if val < 10 else f"{val:.2f}"
        return str(val)

    @staticmethod
    def _pct(val) -> str:
        if val is None:
            return "--"
        return f"{val:.2f}%"

    @staticmethod
    def _fmt_val(val, suffix: str = "") -> str:
        if val is None:
            return "--"
        if isinstance(val, float):
            return f"{val:.2f}{suffix}"
        return f"{val}{suffix}"


# --------------------------------------------------------------------------- #
#  高级指标条件解析（enrich 模式）
# --------------------------------------------------------------------------- #

def parse_enrich_conditions(cond_str: str) -> List[Tuple[str, str, float]]:
    """解析高级指标筛选条件字符串"""
    conditions = []
    if not cond_str:
        return conditions
    parts = [c.strip() for c in cond_str.split(",") if c.strip()]
    ops = [">=", "<=", "!=", ">", "<", "="]
    for part in parts:
        matched = False
        for op in ops:
            if op in part:
                idx = part.index(op)
                field = part[:idx].strip()
                value_str = part[idx + len(op):].strip()
                field = ENRICH_FIELD_ALIAS.get(field, field)
                try:
                    value = float(value_str)
                except ValueError:
                    continue
                conditions.append((field, op, value))
                matched = True
                break
        if not matched:
            print(f"[警告] 无法解析高级条件: {part}", file=sys.stderr)
    return conditions


def check_enrich_condition(fund: Dict, field: str, op: str, value: float) -> bool:
    """检查单只基金是否满足高级指标条件"""
    fund_val = fund.get(field)
    if fund_val is None:
        return False
    if not isinstance(fund_val, (int, float)):
        try:
            fund_val = float(str(fund_val).replace("%", "").replace("--", "").strip())
        except (ValueError, TypeError):
            return False
    if op == ">":
        return fund_val > value
    elif op == ">=":
        return fund_val >= value
    elif op == "<":
        return fund_val < value
    elif op == "<=":
        return fund_val <= value
    elif op == "=":
        return abs(fund_val - value) < 0.001
    elif op == "!=":
        return abs(fund_val - value) >= 0.001
    return False


# --------------------------------------------------------------------------- #
#  CLI 入口
# --------------------------------------------------------------------------- #

def resolve_fund_type(raw: str) -> str:
    """将用户输入的基金类型转换为API参数"""
    raw = raw.strip()
    if raw in FUND_TYPE_MAP:
        mapped = FUND_TYPE_MAP[raw]
        # 如果映射结果还是中文，继续转换
        if mapped in FUND_TYPE_MAP:
            return FUND_TYPE_MAP[mapped]
        return mapped if mapped in ("all", "gp", "hh", "zq", "zs", "qdii", "fof", "hb") else raw
    return raw


def main():
    parser = argparse.ArgumentParser(
        description="公募基金多维度筛选工具 — ETF 顾问团队",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 全市场近1年收益率>50%的基金
  python fund_screener.py --type all --conditions "近1年>50" --sort 近1年 --limit 20

  # 股票型基金，近1年收益率>80%，规模>2亿
  python fund_screener.py --type gp --conditions "近1年>80,最新规模>2" --sort 近1年

  # 使用内置模板
  python fund_screener.py --template 长跑型主动权益基金

  # JSON格式输出
  python fund_screener.py --type all --conditions "近1年>100" --sort 近1年 --json
        """,
    )
    parser.add_argument("--type", "-t", default="all",
                        help="基金类型: all/gp/hh/zq/zs/qdii/fof/hb 或中文（默认all）")
    parser.add_argument("--conditions", "-c", default="",
                        help="筛选条件，逗号分隔 (如: 近1年>50,最新规模>2,成立年限>=3)")
    parser.add_argument("--logic", "-l", default="AND", choices=["AND", "OR"],
                        help="多条件逻辑: AND(默认) 或 OR")
    parser.add_argument("--sort", "-s", default="近1年",
                        help="排序字段 (默认: 近1年)")
    parser.add_argument("--desc", action="store_true", default=True,
                        help="降序排列 (默认)")
    parser.add_argument("--asc", action="store_true", default=False,
                        help="升序排列")
    parser.add_argument("--limit", "-n", type=int, default=20,
                        help="结果数量上限 (默认20, 最多50)")
    parser.add_argument("--template", "-T", default="",
                        help="使用内置模板 (如: 长跑型主动权益基金)")
    parser.add_argument("--json", "-j", action="store_true",
                        help="以JSON格式输出")
    parser.add_argument("--output", "-o", default="",
                        help="输出文件路径")
    parser.add_argument("--workers", "-w", type=int, default=8,
                        help="并发线程数 (默认8)")
    parser.add_argument("--detail-top", type=int, default=0,
                        help="对Top N只基金获取详细信息 (默认0=不获取)")
    parser.add_argument("--enrich", "-e", action="store_true",
                        help="启用高级指标二次筛选（自动采集夏普比率/最大回撤/基金经理等）")
    parser.add_argument("--enrich-conditions", "-ec", default="",
                        help="高级指标筛选条件 (如: 夏普比率_近1年>2,经理任职年限>=2)")
    parser.add_argument("--enrich-sort", "-es", default="",
                        help="高级指标排序字段 (如: 夏普比率_近1年)")
    parser.add_argument("--enrich-limit", "-el", type=int, default=0,
                        help="二次筛选前的候选池上限 (默认=limit*3，避免采集过多)")
    parser.add_argument("--list-templates", action="store_true",
                        help="列出所有内置模板")
    parser.add_argument("--list-enrich-fields", action="store_true",
                        help="列出所有可用的高级指标字段")
    parser.add_argument("--keyword", "-k", default="",
                        help="按基金简称关键词筛选，多个关键词用|分隔表示OR (如: 半导体|芯片)")
    parser.add_argument("--exclude-keyword", "-xk", default="",
                        help="排除基金简称包含指定关键词的基金，多个关键词用|分隔 (如: 联接|C)")

    args = parser.parse_args()

    # stdout UTF-8
    sys.stdout.reconfigure(encoding='utf-8')

    # 列出模板
    if args.list_templates:
        print("可用的内置筛选模板：\n")
        for name, tpl in TEMPLATES.items():
            print(f"  「{name}」")
            print(f"    类型: {FUND_TYPE_MAP.get(tpl['fund_type'], tpl['fund_type'])}")
            print(f"    说明: {tpl['description']}")
            print(f"    条件: {tpl['conditions']}")
            print()
        sys.exit(0)

    # 列出高级指标字段
    if args.list_enrich_fields:
        print("可用的高级指标字段（通过 --enrich 启用）：\n")
        enrich_fields = [
            ("夏普比率_近1年", "每承担一单位风险的超额收益（近1年）"),
            ("夏普比率_近2年", "每承担一单位风险的超额收益（近2年）"),
            ("夏普比率_近3年", "每承担一单位风险的超额收益（近3年）"),
            ("标准差_近1年", "年化波动率（近1年）"),
            ("标准差_近2年", "年化波动率（近2年）"),
            ("标准差_近3年", "年化波动率（近3年）"),
            ("最大回撤_近1年", "最高点到最低点的最大跌幅（近1年）"),
            ("最大回撤_近2年", "最高点到最低点的最大跌幅（近2年）"),
            ("最大回撤_近3年", "最高点到最低点的最大跌幅（近3年）"),
            ("经理任职年限", "当前基金经理管理本基金的年限"),
            ("经理任职天数", "当前基金经理管理本基金的天数"),
            ("机构持有比例", "机构投资者持有份额占比（%）"),
            ("个人持有比例", "个人投资者持有份额占比（%）"),
            ("招商评级_数值", "招商评级星级数 (1-5)"),
            ("晨星评级_数值", "晨星评级星级数 (1-5)"),
            ("济安金信评级_数值", "济安金信评级星级数 (1-5)"),
            ("基金经理", "当前基金经理姓名"),
            ("累计分红次数", "成立以来的总分红次数"),
            ("近1年分红次数", "近12个月内的分红次数"),
            ("近1年累计每份派现", "近12个月累计每份派现金额（元）"),
            ("成立来累计每份派现", "成立以来累计每份派现金额（元）"),
        ]
        print(f"  {'字段名':<22} {'说明'}")
        print(f"  {'-'*22} {'-'*40}")
        for field, desc in enrich_fields:
            print(f"  {field:<22} {desc}")
        print("\n别名映射（简写→完整字段名）：")
        for alias, full in sorted(ENRICH_FIELD_ALIAS.items()):
            if alias != full:
                print(f"  {alias} → {full}")
        sys.exit(0)

    # 解析参数
    template_name = args.template.strip()
    if template_name:
        if template_name not in TEMPLATES:
            print(f"[错误] 未找到模板「{template_name}」", file=sys.stderr)
            print(f"可用模板: {', '.join(TEMPLATES.keys())}", file=sys.stderr)
            sys.exit(1)
        tpl = TEMPLATES[template_name]
        fund_type = tpl["fund_type"]
        conditions = list(tpl["conditions"])
        sort_by = tpl.get("sort_by", "近1年")
        sort_desc = tpl.get("sort_desc", True)
    else:
        fund_type = resolve_fund_type(args.type)
        conditions = FundScreener.parse_conditions(args.conditions)
        sort_by = FIELD_ALIAS.get(args.sort.strip(), args.sort.strip())
        sort_desc = not args.asc

    limit = min(args.limit, 50)

    # --keyword / --exclude-keyword 转换为 contains/!contains 条件
    if args.keyword:
        keywords = [kw.strip() for kw in args.keyword.split("|") if kw.strip()]
        for kw in keywords:
            conditions.append(("基金简称", "contains", kw))
    if args.exclude_keyword:
        ex_keywords = [kw.strip() for kw in args.exclude_keyword.split("|") if kw.strip()]
        for kw in ex_keywords:
            conditions.append(("基金简称", "!contains", kw))

    # 当有多个 keyword（|分隔）时，使用 OR 逻辑仅对关键词条件生效
    # 实现方式：如果有多个 contains 条件且用户用 | 分隔了关键词，
    # 需要预先过滤（任一关键词匹配即可），然后再应用其余条件
    keyword_contains = [(f, o, v) for f, o, v in conditions if o == "contains" and f == "基金简称"]
    if len(keyword_contains) > 1:
        # 多关键词 OR 逻辑：移除 contains 条件，手动预过滤
        conditions = [(f, o, v) for f, o, v in conditions if not (o == "contains" and f == "基金简称")]

    # 确定API排序参数
    sort_sc = SORT_SC_MAP.get(sort_by, "zzf")

    # 执行
    start_time = time.time()
    screener = FundScreener(max_workers=args.workers)

    # 获取全市场数据
    all_funds = screener.fetch_all_funds(fund_type, sort_col=sort_sc, sort_desc=sort_desc)
    if not all_funds:
        print("[错误] 未获取到任何基金数据，请检查网络连接。", file=sys.stderr)
        sys.exit(1)

    # 多关键词 OR 预过滤（--keyword "A|B" 表示简称包含A或B）
    keyword_funnel_step = None
    if len(keyword_contains) > 1:
        before_kw = len(all_funds)
        kw_values = [v for _, _, v in keyword_contains]
        all_funds = [f for f in all_funds
                     if any(kw in str(f.get("基金简称", "")) for kw in kw_values)]
        keyword_funnel_step = {
            "步骤": f"关键词过滤(OR): 基金简称包含 {'|'.join(kw_values)}",
            "条件": f"基金简称 contains {'|'.join(kw_values)}",
            "过滤前": before_kw,
            "剩余数量": len(all_funds),
            "淘汰数量": before_kw - len(all_funds),
        }

    # 应用筛选
    filtered, funnel = screener.apply_filter(all_funds, conditions, logic=args.logic)

    # 将关键词预过滤步骤插入漏斗（在初始标的池之后）
    if keyword_funnel_step:
        funnel.insert(1, keyword_funnel_step)

    # 排序
    filtered = screener.sort_funds(filtered, sort_by, sort_desc)

    elapsed = time.time() - start_time
    screener._print(f"\n筛选完成，耗时 {elapsed:.1f} 秒")
    screener._print(f"符合条件: {len(filtered)} / {len(all_funds)}")

    # ---- 二次富化：高级指标采集与筛选 ----
    enrich_data = {}  # {基金代码: metrics_dict}
    if args.enrich or args.detail_top > 0:
        # 导入本地 fund_detail_scraper
        sys.path.insert(0, SCRIPT_DIR)
        from fund_detail_scraper import FundDetailScraper, batch_extract_metrics

        if args.enrich:
            # 确定候选池范围
            enrich_pool_limit = args.enrich_limit if args.enrich_limit > 0 else min(limit * 3, 100)
            enrich_pool = filtered[:enrich_pool_limit]
            screener._print(f"\n启用高级指标采集: 对候选池前 {len(enrich_pool)} 只基金获取详细指标...")

            codes = [f["基金代码"] for f in enrich_pool]
            metrics_list = batch_extract_metrics(codes, max_workers=min(args.workers, 8))

            for m in metrics_list:
                code = m.get("基金代码", "")
                if code:
                    enrich_data[code] = m

            # 将高级指标合并到基金数据
            for fund in enrich_pool:
                code = fund["基金代码"]
                if code in enrich_data:
                    for k, v in enrich_data[code].items():
                        if k not in fund and v is not None:
                            fund[k] = v

            # 解析并应用高级指标筛选条件
            if args.enrich_conditions:
                enrich_conds = parse_enrich_conditions(args.enrich_conditions)
                if enrich_conds:
                    before_enrich = len(enrich_pool)
                    enriched = []
                    for fund in enrich_pool:
                        if all(check_enrich_condition(fund, f, o, v) for f, o, v in enrich_conds):
                            enriched.append(fund)
                    filtered = enriched
                    funnel.append({
                        "步骤": "高级指标二次筛选",
                        "条件": args.enrich_conditions,
                        "过滤前": before_enrich,
                        "剩余数量": len(filtered),
                        "淘汰数量": before_enrich - len(filtered),
                    })
                    screener._print(f"高级指标筛选: {before_enrich} → {len(filtered)}")
                else:
                    filtered = enrich_pool
            else:
                filtered = enrich_pool

            # 高级指标排序
            if args.enrich_sort:
                enrich_sort_field = ENRICH_FIELD_ALIAS.get(args.enrich_sort.strip(), args.enrich_sort.strip())
                filtered = sorted(
                    filtered,
                    key=lambda f: (f.get(enrich_sort_field) is not None,
                                   f.get(enrich_sort_field) if isinstance(f.get(enrich_sort_field), (int, float)) else 0),
                    reverse=sort_desc,
                )
                sort_by = enrich_sort_field

        elif args.detail_top > 0:
            # 仅对 Top N 采集详情
            detail_pool = filtered[:args.detail_top]
            screener._print(f"\n获取 Top {len(detail_pool)} 只基金的详细信息...")
            codes = [f["基金代码"] for f in detail_pool]
            metrics_list = batch_extract_metrics(codes, max_workers=min(args.workers, 8))
            for m in metrics_list:
                code = m.get("基金代码", "")
                if code:
                    enrich_data[code] = m
            # 合并到基金数据
            for fund in detail_pool:
                code = fund["基金代码"]
                if code in enrich_data:
                    for k, v in enrich_data[code].items():
                        if k not in fund and v is not None:
                            fund[k] = v

    elapsed_total = time.time() - start_time
    if elapsed_total > elapsed + 0.5:
        screener._print(f"总耗时（含高级指标采集）: {elapsed_total:.1f} 秒")

    # 输出
    if args.json:
        result_json = screener.to_json(filtered, funnel, fund_type, conditions, sort_by, limit)
        # 附加高级指标到 JSON 输出
        if enrich_data:
            for item in result_json.get("筛选结果", []):
                code = item.get("基金代码", "")
                if code in enrich_data:
                    item["高级指标"] = {k: v for k, v in enrich_data[code].items()
                                        if k != "基金代码" and v is not None}
        output = json.dumps(result_json, ensure_ascii=False, indent=2)
    else:
        output = screener.to_markdown(
            filtered, funnel, fund_type, conditions, sort_by, limit,
            template_name=template_name or None, enrich_data=enrich_data,
        )

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"结果已保存到: {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
