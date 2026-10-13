#!/usr/bin/env python3
"""技能ID: contract-risk-score | 合同风险评分"""
import json, re
from typing import Dict, Any

RISK_CHECKS = [
    ("甲方信息完整", [r"甲方.*名称", r"甲方.*地址", r"甲方法定代表人"], 10, "缺少甲方基本信息"),
    ("乙方信息完整", [r"乙方.*名称", r"乙方.*地址", r"乙方法定代表人"], 10, "缺少乙方基本信息"),
    ("金额明确", [r"\d+.*元", "总价", "费用"], 10, "合同金额不明确"),
    ("期限明确", ["期限", "有效期", r"\d{4}.*年"], 8, "合同期限不明确"),
    ("违约责任", ["违约责任", "违约金", "赔偿"], 12, "缺少违约责任条款"),
    ("争议解决", ["仲裁", "诉讼", "法院", "争议解决"], 10, "缺少争议解决条款"),
    ("知识产权", ["知识产权", "专利", "著作权"], 8, "知识产权归属不明"),
    ("保密条款", ["保密", "商业秘密"], 8, "缺少保密条款"),
    ("不可抗力", ["不可抗力"], 6, "缺少不可抗力条款"),
    ("合同解除", ["解除合同", "终止条件"], 10, "缺少合同解除条件"),
    ("签章要素", ["签章", "签字", "盖章", "日期"], 8, "缺少签章要素"),
]

def skill_function(input_data):
    text = input_data.get("contract_text", "")
    if not text:
        return {"status": "error", "message": "请提供合同文本"}
    score = 100
    details = []
    risks = []
    for name, patterns, weight, msg in RISK_CHECKS:
        matched = any(re.search(p, text, re.IGNORECASE) for p in patterns)
        if matched:
            details.append({"检查项": name, "状态": "通过", "得分": weight})
        else:
            score -= weight
            details.append({"检查项": name, "状态": "缺失", "扣分": weight})
            risks.append(msg)
    score = max(0, score)
    grade = "A" if score >= 80 else ("B" if score >= 60 else ("C" if score >= 40 else "D"))
    return {"status": "success", "result": {"风险评分": score, "评级": grade, "检查详情": details, "主要风险": risks}}

if __name__ == "__main__":
    test = "甲方名称：北京科技，地址：北京市海淀区，法人：张三。乙方名称：上海贸易，地址：上海浦东。合同总价500000元。争议提交仲裁委员会仲裁。甲方签字盖章。乙方签字盖章。"
    print(json.dumps(skill_function({"contract_text": test}), ensure_ascii=False, indent=2))
