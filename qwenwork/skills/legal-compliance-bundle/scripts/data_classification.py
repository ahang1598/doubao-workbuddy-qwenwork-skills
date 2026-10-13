#!/usr/bin/env python3
"""data_classification.py — 数据分类分级 (Skill #35)"""
import sys, json
from datetime import datetime

LEVELS = {
    "1级-公开": {"desc": "可公开的数据", "examples": ["公司简介", "公开产品信息"], "protection": "无特殊保护要求"},
    "2级-内部": {"desc": "仅限内部使用", "examples": ["内部通知", "一般业务数据"], "protection": "禁止外部传播"},
    "3级-机密": {"desc": "重要业务数据", "examples": ["客户信息", "财务数据", "合同文件"], "protection": "加密存储、访问控制"},
    "4级-绝密": {"desc": "核心敏感数据", "examples": ["核心算法", "商业秘密", "个人敏感信息"], "protection": "加密存储+传输、最小授权、审计追踪"}
}

def classify(data_items: list) -> dict:
    result = {}
    for item in data_items:
        name = item.get("name", "未知数据")
        category = item.get("category", "业务数据")
        level = item.get("level", "2级-内部")
        result[name] = {"category": category, "level": level, "protection": LEVELS.get(level, {}).get("protection", "")}
    return result

def generate_report(data_items: list) -> str:
    report = f"# 数据分类分级评估报告\n\n**评估时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n---\n\n"
    report += "## 分级标准\n\n"
    for level, info in LEVELS.items():
        report += f"### {level}\n- 说明: {info['desc']}\n- 示例: {', '.join(info['examples'])}\n- 保护措施: {info['protection']}\n\n"
    report += "---\n\n## 评估结果\n\n"
    if not data_items:
        report += "请提供待评估的数据清单。\n"
    else:
        for item in data_items:
            report += f"- **{item.get('name','')}** | 类别: {item.get('category','')} | 等级: {item.get('level','')}\n"
    report += "\n---\n\n## 建议\n\n1. 建立数据资产台账\n2. 根据分类分级实施差异化保护\n3. 定期评估和更新分类等级\n4. 员工数据安全意识培训\n"
    return report

def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--input", "-i", help="数据清单JSON文件")
    p.add_argument("--output", "-o")
    a = p.parse_args()
    items = []
    if a.input:
        with open(a.input, "r", encoding="utf-8") as f: items = json.load(f)
    r = generate_report(items)
    if a.output:
        with open(a.output, "w", encoding="utf-8") as f: f.write(r)
        print(f"✅ 已保存至: {a.output}")
    else: print(r)

if __name__ == "__main__": main()
