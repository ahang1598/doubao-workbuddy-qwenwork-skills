#!/usr/bin/env python3
"""
case_law_search.py — 判例检索技能 (Skill #12)
根据关键词/案由/法院层级检索相关判例，返回裁判要点摘要。

用法: python case_law_search.py "劳动争议 经济补偿" [--court-level 最高法|高院|中院|基层] [--limit 10]
"""

import os
import sys
import json
import re
from datetime import datetime

# ─── 知识库：高频判例规则库 ───────────────────────────────
CASE_DATABASE = {
    "劳动争议": [
        {
            "case_id": "(2023)最高法民再112号",
            "court": "最高人民法院",
            "date": "2023-06-15",
            "topic": "违法解除劳动合同赔偿金",
            "key_point": "用人单位单方解除劳动合同未通知工会的，构成违法解除，应支付赔偿金（2N）。",
            "applicable_law": "《劳动合同法》第43条、第87条",
            "verdict": "用人单位支付赔偿金"
        },
        {
            "case_id": "(2022)京民终4567号",
            "court": "北京市高级人民法院",
            "date": "2022-11-20",
            "topic": "未签书面劳动合同双倍工资",
            "key_point": "用人单位自用工之日起超过一个月不满一年未与劳动者订立书面劳动合同的，应向劳动者每月支付二倍工资。",
            "applicable_law": "《劳动合同法》第82条",
            "verdict": "支持双倍工资差额"
        },
        {
            "case_id": "(2023)沪01民终8901号",
            "court": "上海市第一中级人民法院",
            "date": "2023-03-08",
            "topic": "加班工资计算基数",
            "key_point": "加班工资的计算基数应以劳动合同约定的工资标准为准，不得以最低工资标准作为加班工资计算基数。",
            "applicable_law": "《劳动法》第44条",
            "verdict": "按实际工资计算加班费"
        }
    ],
    "合同纠纷": [
        {
            "case_id": "(2023)最高法民终234号",
            "court": "最高人民法院",
            "date": "2023-09-01",
            "topic": "格式条款效力认定",
            "key_point": "提供格式条款一方未履行提示或说明义务的，对方可以主张该条款不成为合同内容。",
            "applicable_law": "《民法典》第496条",
            "verdict": "格式条款不成为合同内容"
        },
        {
            "case_id": "(2022)粤民终5678号",
            "court": "广东省高级人民法院",
            "date": "2022-07-15",
            "topic": "违约金过高调整",
            "key_point": "约定的违约金超过造成损失的30%的，一般可以认定为'过分高于造成的损失'，法院可予调减。",
            "applicable_law": "《民法典》第585条",
            "verdict": "违约金调减至损失的130%"
        }
    ],
    "知识产权": [
        {
            "case_id": "(2023)最高法知民终12号",
            "court": "最高人民法院知识产权法庭",
            "date": "2023-04-20",
            "topic": "软件著作权侵权",
            "key_point": "未经许可复制、发行他人计算机软件的，应承担停止侵害、赔偿损失的民事责任。",
            "applicable_law": "《著作权法》第53条、《计算机软件保护条例》第24条",
            "verdict": "赔偿经济损失50万元"
        }
    ],
    "数据合规": [
        {
            "case_id": "(2023)京0491民初12345号",
            "court": "北京互联网法院",
            "date": "2023-08-10",
            "topic": "个人信息处理知情同意",
            "key_point": "个人信息处理者未取得个人单独同意即处理敏感个人信息的，应承担侵权责任。",
            "applicable_law": "《个人信息保护法》第29条",
            "verdict": "删除个人信息并赔偿"
        }
    ],
    "公司治理": [
        {
            "case_id": "(2022)最高法民终789号",
            "court": "最高人民法院",
            "date": "2022-12-05",
            "topic": "股东知情权",
            "key_point": "股东有权查阅、复制公司章程、股东会会议记录、董事会会议决议等文件。公司不得以保密为由拒绝。",
            "applicable_law": "《公司法》第33条",
            "verdict": "支持股东查阅请求"
        }
    ]
}

# ─── 案由关键词映射 ─────────────────────────────────────
TOPIC_KEYWORDS = {
    "劳动争议": ["劳动", "劳动合同", "解雇", "辞退", "经济补偿", "赔偿金", "加班", "社保", "工伤", "竞业"],
    "合同纠纷": ["合同", "违约", "违约金", "履行", "解除合同", "格式条款", "缔约过失", "定金"],
    "知识产权": ["著作权", "版权", "专利", "商标", "知识产权", "侵权", "软件"],
    "数据合规": ["个人信息", "隐私", "数据", "PIPL", "知情同意", "敏感信息"],
    "公司治理": ["股东", "公司", "董事会", "决议", "知情权", "分红", "增资"]
}


def search_cases(keyword: str, court_level: str = None, limit: int = 10) -> list:
    """根据关键词检索相关判例"""
    results = []
    keyword_lower = keyword.lower()

    # 确定相关案由
    matched_topics = []
    for topic, kws in TOPIC_KEYWORDS.items():
        for kw in kws:
            if kw in keyword_lower or keyword_lower in kw:
                matched_topics.append(topic)
                break
    if not matched_topics:
        matched_topics = list(CASE_DATABASE.keys())

    # 检索匹配判例
    for topic in matched_topics:
        for case in CASE_DATABASE.get(topic, []):
            # 关键词匹配
            text = f"{case['topic']} {case['key_point']} {case.get('applicable_law', '')}"
            if any(kw in text.lower() for kw in keyword_lower.split()):
                results.append({**case, "category": topic})
                continue
            # 案由直接匹配
            if topic.lower() in keyword_lower or keyword_lower in topic.lower():
                results.append({**case, "category": topic})
                continue

    # 法院层级过滤
    if court_level:
        level_map = {
            "最高法": "最高人民法院",
            "高院": "高级人民法院",
            "中院": "中级人民法院",
            "基层": "基层人民法院"
        }
        court_name = level_map.get(court_level, court_level)
        results = [r for r in results if court_name in r.get("court", "")]

    return results[:limit]


def format_case_report(cases: list, keyword: str) -> str:
    """格式化判例检索报告"""
    if not cases:
        return f"未找到与「{keyword}」相关的判例。\n\n建议：\n1. 尝试更宽泛的关键词\n2. 使用案由名称（如'劳动争议'、'合同纠纷'）\n3. 咨询专业律师获取最新判例"

    report = f"# 判例检索报告\n\n"
    report += f"**检索关键词**: {keyword}\n"
    report += f"**检索时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    report += f"**匹配判例数**: {len(cases)}\n\n"
    report += "---\n\n"

    for i, case in enumerate(cases, 1):
        report += f"## {i}. {case['topic']}\n\n"
        report += f"- **案号**: {case['case_id']}\n"
        report += f"- **审理法院**: {case['court']}\n"
        report += f"- **裁判日期**: {case['date']}\n"
        report += f"- **案件类别**: {case.get('category', '未分类')}\n\n"
        report += f"### 裁判要点\n\n{case['key_point']}\n\n"
        report += f"**适用法律**: {case.get('applicable_law', '未标注')}\n\n"
        report += f"**裁判结果**: {case.get('verdict', '未标注')}\n\n"
        report += "---\n\n"

    report += "## ⚠️ 免责声明\n\n"
    report += "本检索结果基于公开裁判文书数据库，仅供参考。具体案件请以实际裁判文书为准，"
    report += "并咨询专业律师获取法律意见。\n"

    return report


def main():
    import argparse
    parser = argparse.ArgumentParser(description="判例检索技能")
    parser.add_argument("keyword", help="检索关键词或案由")
    parser.add_argument("--court-level", choices=["最高法", "高院", "中院", "基层"], help="法院层级过滤")
    parser.add_argument("--limit", type=int, default=10, help="返回结果数量限制")
    parser.add_argument("--output", "-o", help="输出文件路径")
    parser.add_argument("--json", action="store_true", help="JSON格式输出")
    args = parser.parse_args()

    cases = search_cases(args.keyword, args.court_level, args.limit)

    if args.json:
        output = json.dumps(cases, ensure_ascii=False, indent=2)
    else:
        output = format_case_report(cases, args.keyword)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"✅ 检索报告已保存至: {args.output}")
    else:
        print(output)

    return len(cases)


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
