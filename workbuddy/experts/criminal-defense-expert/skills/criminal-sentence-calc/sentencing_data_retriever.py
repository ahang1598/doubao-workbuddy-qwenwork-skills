#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sentencing_data_retriever.py — 地区量刑细则联网检索代理
==========================================================
置信度: 85%
用途: Phase 2/3 根据用户声明的审理地区，指导 agent 联网检索该省/市量刑指导意见实施细则
依赖: 纯 Python 标准库，无第三方依赖

设计决策:
  - 不维护本地 31 省静态数据库
  - 量刑细则属于"需要及时更新的外部知识"，联网检索天然获得最新版本
  - 本脚本为"检索编排代理"——构造搜索关键词 + 解析原则说明
  - 实际联网搜索由 agent (LLM + search tool) 执行

数据优先级:
  P0: 全国统一标准（内置）—— 刑法 + 最高人民法院量刑指导意见
  P1: 地区细则（联网检索）—— 各省高院量刑指导意见实施细则
  P2: 用户自定（最高优先级）—— 用户明确提供的量刑幅度始终覆盖 P0/P1
"""

import json
import sys
from datetime import datetime
from typing import Optional


# ============================================================
# 一、内置：全国统一量刑标准（P0，始终可用）
# ============================================================

NATIONAL_SENTENCING_BASELINE = {
    "source": "最高人民法院、最高人民检察院《关于常见犯罪的量刑指导意见（试行）》",
    "source_document_number": "法发〔2021〕21号",
    "source_type": "P0-全国统一",
    "source_url": "https://www.court.gov.cn/",
    "confidence": "high",
    "effective_date": "2021-07-01",
    "last_updated": "2024-07-01",  # 需定期核实是否被法发〔2024〕132号更新
    "note": "2024年7月起试行《量刑指导意见（二）》（法发〔2024〕132号）可能对部分罪名有更新。地区实施细则可能在以下维度进一步细化：起点刑幅度、增减比例调整范围、数额档位划分标准",
    "sentencing_factor_ranges": {
        "自首（一般）": "减少基准刑的40%以下",
        "自首（犯罪较轻）": "减少40%以上或依法免除",
        "坦白（如实供述）": "减少基准刑的20%以下",
        "立功（一般）": "减少基准刑的20%以下",
        "立功（重大）": "减少基准刑的20%-50%",
        "从犯": "减少基准刑的20%-50%",
        "未遂犯": "比照既遂犯减少50%以下",
        "认罪认罚（一般）": "减少基准刑的30%以下",
        "认罪认罚（含自首/坦白/退赃退赔/赔偿谅解/刑事和解）": "减少基准刑的60%以下",
        "退赃退赔": "减少基准刑的30%以下",
        "累犯": "增加基准刑的10%-30%",
    },
    "common_offense_adjustments": {
        "盗窃罪": {
            "数额较大": "3年以下",
            "数额巨大": "3年以上10年以下",
            "数额特别巨大": "10年以上",
            "调节比例参考": "自首-40%以下, 立功-20%以下, 从犯-20%~-50%, 认罪认罚-30%以下",
        },
        "诈骗罪": {
            "数额较大": "3年以下",
            "数额巨大": "3年以上10年以下",
            "数额特别巨大": "10年以上或无期",
        },
        "故意伤害罪": {
            "轻伤": "3年以下",
            "重伤": "3年以上10年以下",
            "致死/特别残忍": "10年以上/无期/死刑",
        },
        "交通肇事罪": {
            "基本": "3年以下",
            "逃逸/特别恶劣": "3年以上7年以下",
            "逃逸致死": "7年以上",
        },
        "抢劫罪": {
            "基本": "3年以上10年以下",
            "加重": "10年以上/无期/死刑",
        },
        "职务侵占罪": {
            "数额较大": "3年以下",
            "数额巨大": "3年以上10年以下",
            "数额特别巨大": "10年以上或无期",
        },
        "贪污/受贿罪": {
            "数额较大/较重": "3年以下",
            "数额巨大/严重": "3年以上10年以下",
            "数额特别巨大/特别严重": "10年以上/无期/死刑",
        },
    },
}


# ============================================================
# 二、省内量刑细则区域关键词映射（P1，用于构造搜索词）
# ============================================================

PROVINCE_KEYWORDS = {
    "北京":   "北京市高级人民法院 量刑指导意见实施细则",
    "上海":   "上海市高级人民法院 量刑指导意见实施细则",
    "天津":   "天津市高级人民法院 量刑指导意见实施细则",
    "重庆":   "重庆市高级人民法院 量刑指导意见实施细则",
    "广东":   "广东省高级人民法院 量刑指导意见实施细则",
    "江苏":   "江苏省高级人民法院 量刑指导意见实施细则",
    "浙江":   "浙江省高级人民法院 量刑指导意见实施细则",
    "山东":   "山东省高级人民法院 量刑指导意见实施细则",
    "四川":   "四川省高级人民法院 量刑指导意见实施细则",
    "湖北":   "湖北省高级人民法院 量刑指导意见实施细则",
    "湖南":   "湖南省高级人民法院 量刑指导意见实施细则",
    "河南":   "河南省高级人民法院 量刑指导意见实施细则",
    "河北":   "河北省高级人民法院 量刑指导意见实施细则",
    "福建":   "福建省高级人民法院 量刑指导意见实施细则",
    "安徽":   "安徽省高级人民法院 量刑指导意见实施细则",
    "辽宁":   "辽宁省高级人民法院 量刑指导意见实施细则",
    "江西":   "江西省高级人民法院 量刑指导意见实施细则",
    "陕西":   "陕西省高级人民法院 量刑指导意见实施细则",
    "山西":   "山西省高级人民法院 量刑指导意见实施细则",
    "吉林":   "吉林省高级人民法院 量刑指导意见实施细则",
    "黑龙江": "黑龙江省高级人民法院 量刑指导意见实施细则",
    "云南":   "云南省高级人民法院 量刑指导意见实施细则",
    "贵州":   "贵州省高级人民法院 量刑指导意见实施细则",
    "甘肃":   "甘肃省高级人民法院 量刑指导意见实施细则",
    "海南":   "海南省高级人民法院 量刑指导意见实施细则",
    "青海":   "青海省高级人民法院 量刑指导意见实施细则",
    "内蒙古": "内蒙古自治区高级人民法院 量刑指导意见实施细则",
    "广西":   "广西壮族自治区高级人民法院 量刑指导意见实施细则",
    "西藏":   "西藏自治区高级人民法院 量刑指导意见实施细则",
    "宁夏":   "宁夏回族自治区高级人民法院 量刑指导意见实施细则",
    "新疆":   "新疆维吾尔自治区高级人民法院 量刑指导意见实施细则",
    "深圳":   "深圳市中级人民法院 量刑指导意见实施细则 广东省",
    "广州":   "广州市中级人民法院 量刑指导意见实施细则 广东省",
}


# ============================================================
# 三、检索编排代理函数
# ============================================================

def build_search_query(offense: str, jurisdiction: str) -> dict:
    """
    根据罪名和审理地区，构造联网搜索关键词。
    
    Args:
        offense:      罪名名称，如"盗窃罪"
        jurisdiction: 审理省份/直辖市，如"广东省"
    
    Returns:
        {
            "search_query": str,            # 搜索关键词（给 agent 用于联网搜索）
            "has_province_guideline": bool, # 是否有已知的省级细则关键词
            "fallback_search": str,         # 降级搜索词（如省级无结果时）
            "province_match_type": str,     # "exact" | "fuzzy" | "unknown"
            "builtin_baseline": dict,       # P0 全国统一标准
        }
    
    Example:
        >>> result = build_search_query("盗窃罪", "广东省")
        >>> result["search_query"]
        '广东省高级人民法院 量刑指导意见实施细则 盗窃罪'
    """
    # 匹配省级关键词
    province_query = None
    match_type = "unknown"
    
    # 精确匹配
    for key, query in PROVINCE_KEYWORDS.items():
        if key in jurisdiction:
            province_query = query
            match_type = "exact"
            break
    
    # 模糊匹配（如"粤"→"广东"）
    if not province_query:
        province_aliases = {
            "粤": "广东", "苏": "江苏", "浙": "浙江", "鲁": "山东",
            "川": "四川", "鄂": "湖北", "湘": "湖南", "豫": "河南",
            "冀": "河北", "闽": "福建", "皖": "安徽", "辽": "辽宁",
            "赣": "江西", "陕": "陕西", "晋": "山西", "吉": "吉林",
            "黑": "黑龙江", "滇": "云南", "黔": "贵州", "甘": "甘肃",
            "琼": "海南", "青": "青海", "蒙": "内蒙古", "桂": "广西",
            "藏": "西藏", "宁": "宁夏", "新": "新疆",
        }
        for alias, full_name in province_aliases.items():
            if alias in jurisdiction:
                province_query = PROVINCE_KEYWORDS.get(full_name, None)
                match_type = "fuzzy"
                break
    
    # 构造搜索词
    if province_query:
        search_query = f"{province_query} {offense}"
        fallback = f"{province_query}"  # 不限定罪名的通用搜索
    else:
        search_query = f"{jurisdiction} 高级人民法院 量刑指导意见 实施细则 {offense}"
        fallback = f"{jurisdiction} 量刑指导意见 实施细则"
    
    return {
        "search_query": search_query,
        "has_province_guideline": province_query is not None,
        "fallback_search": fallback,
        "province_match_type": match_type,
        "builtin_baseline": NATIONAL_SENTENCING_BASELINE,
    }


def format_retrieval_instruction(search_result: dict) -> str:
    """
    将检索编排结果格式化为 agent 可执行的检索指令。
    
    返回一段 Markdown 格式的检索指令文本，agent 应据此执行联网搜索。
    
    Args:
        search_result: build_search_query() 的返回值
    
    Returns:
        str: Markdown 格式的检索指令
    """
    q = search_result
    
    lines = [
        "## [SCRIPT CALL] sentencing_data_retriever — 地区量刑细则检索指令",
        "",
        f"**检索时间**: {datetime.now().isoformat(timespec='seconds')}",
        f"**审理地区**: {q.get('jurisdiction', '未指定')}",
        f"**涉嫌罪名**: {q.get('offense', '未指定')}",
        f"**地区匹配**: {q['province_match_type']}",
        "",
        "### 检索步骤",
        "",
        f"**主检索词**: `{q['search_query']}`",
        f"**降级检索词**（主检索无结果时）: `{q['fallback_search']}`",
        "",
        "### 检索目标",
        "",
        "从搜索结果中提取以下结构化量刑参数：",
        "",
        "| 参数 | 说明 | 示例 |",
        "|------|------|------|",
        "| 起点刑调整 | 省级细则对起点刑的具体规定 | \"盗窃数额巨大，起点刑为4年\" |",
        "| 量刑幅度细化 | 各量刑情节的从轻/减轻比例区间 | \"自首从轻20%-40%\" |",
        "| 数额档位划分 | 省级标准对数额档位的具体金额 | \"数额巨大: 10万元以上\" |",
        "| 特殊规则 | 省级特有的量刑规则或排除条件 | \"交通肇事+酒驾不予缓刑\" |",
        "",
        "### 优先级规则（P0→P1→P2）",
        "",
        "1. **P2 用户自定** > P1 地区细则 > P0 全国统一",
        "2. 地区细则仅作为\"用户未明确提供幅度时\"的智能补充",
        "3. 联网检索结果标注 source_url + 检索时间 + 置信度",
        "4. 若联网检索无有效结果 → 降级使用 P0 全国统一标准 + **confidence: low**",
        "",
        "### 输出格式",
        "",
        "检索完成后，以以下结构返回:",
        "",
        "```json",
        "{",
        '  "source_type": "P1-地区细则" | "P0-全国统一（降级）",',
        '  "source_name": "XX省高院量刑指导意见实施细则",',
        '  "source_url": "检索结果URL",',
        '  "retrieval_time": "ISO datetime",',
        '  "confidence": "high" | "medium" | "low",',
        '  "effective_date": "细则发布日期或生效日期",',
        '  "parameters": {',
        '    "baseline_adjustments": { ... },',
        '    "range_refinements": { ... },',
        '    "threshold_refinements": { ... },',
        '    "special_rules": [ ... ]',
        "  }",
        "}",
        "```",
    ]
    
    return "\n".join(lines)


def get_retrieval_plan(offense: str, jurisdiction: Optional[str] = None) -> dict:
    """
    一站式检索编排入口。
    
    Args:
        offense:      罪名名称
        jurisdiction: 审理地区（可选），None 表示仅使用 P0 全国标准
    
    Returns:
        {
            "plan_type": "full_retrieval" | "national_only",
            "search_plan": dict | None,    # build_search_query 返回
            "instruction": str,            # format_retrieval_instruction 返回
            "national_baseline": dict,     # P0 全国标准
        }
    """
    baseline = NATIONAL_SENTENCING_BASELINE.copy()
    
    if not jurisdiction:
        return {
            "plan_type": "national_only",
            "search_plan": None,
            "instruction": "",
            "national_baseline": baseline,
        }
    
    search_plan = build_search_query(offense, jurisdiction)
    search_plan["jurisdiction"] = jurisdiction
    search_plan["offense"] = offense
    
    instruction = format_retrieval_instruction(search_plan)
    
    return {
        "plan_type": "full_retrieval",
        "search_plan": search_plan,
        "instruction": instruction,
        "national_baseline": baseline,
    }


def main():
    """CLI 入口。"""
    if len(sys.argv) < 2:
        print("用法: python sentencing_data_retriever.py <罪名> [审理地区]")
        print('示例: python sentencing_data_retriever.py "盗窃罪" "广东省"')
        print('      python sentencing_data_retriever.py "诈骗罪"')
        sys.exit(0)
    
    offense = sys.argv[1]
    jurisdiction = sys.argv[2] if len(sys.argv) >= 3 else None
    
    result = get_retrieval_plan(offense, jurisdiction)
    
    # 输出检索指令给 agent
    if result["plan_type"] == "full_retrieval":
        print(result["instruction"])
    else:
        print("## [SCRIPT CALL] sentencing_data_retriever — 未指定审理地区")
        print()
        print("仅使用 P0 全国统一量刑标准，不执行地区细则检索。")
        print()
        print(json.dumps(result["national_baseline"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
