#!/usr/bin/env python3
"""
litigation_risk_assess.py — 诉讼风险评估技能 (Skill #15)
评估案件胜诉概率、成本和风险。

用法: python litigation_risk_assess.py --case-type 合同纠纷 --amount 100000 --has-contract yes
"""

import sys
import json
from datetime import datetime


def assess_risk(case_data: dict) -> dict:
    """评估诉讼风险"""
    case_type = case_data.get("case_type", "合同纠纷")
    amount = case_data.get("amount", 0)
    has_contract = case_data.get("has_contract", False)
    has_evidence = case_data.get("has_evidence", True)
    is_within_limitation = case_data.get("is_within_limitation", True)
    defendant_able_to_pay = case_data.get("defendant_able_to_pay", True)

    score = 50  # 基础分
    risks = []
    advantages = []

    # 合同因素
    if has_contract:
        score += 20
        advantages.append("✅ 有书面合同，事实认定较为清晰")
    else:
        score -= 15
        risks.append("❌ 无书面合同，需通过其他证据证明法律关系")

    # 证据因素
    if has_evidence:
        score += 15
        advantages.append("✅ 证据较为充分")
    else:
        score -= 20
        risks.append("❌ 证据不足，可能影响胜诉概率")

    # 时效因素
    if is_within_limitation:
        score += 10
        advantages.append("✅ 在诉讼时效内")
    else:
        score -= 30
        risks.append("❌ 可能超过诉讼时效，对方可主张时效抗辩")

    # 执行因素
    if defendant_able_to_pay:
        advantages.append("✅ 被告有履行能力")
    else:
        score -= 10
        risks.append("❌ 被告可能无财产可供执行，存在胜诉但拿不到钱的风险")

    # 案由修正
    case_type_modifiers = {
        "劳动争议": 10,  # 用人单位举证责任更重
        "合同纠纷": 0,
        "知识产权": -5,
        "数据合规": -5,
    }
    score += case_type_modifiers.get(case_type, 0)

    score = max(0, min(100, score))

    # 诉讼成本估算
    court_fee = _calculate_court_fee(amount)
    lawyer_fee = _estimate_lawyer_fee(amount, case_type)
    time_months = _estimate_duration(case_type)

    # 胜诉概率等级
    if score >= 80:
        win_probability = "高（80%+）"
    elif score >= 60:
        win_probability = "中高（60-80%）"
    elif score >= 40:
        win_probability = "中等（40-60%）"
    elif score >= 20:
        win_probability = "较低（20-40%）"
    else:
        win_probability = "低（<20%）"

    return {
        "score": score,
        "win_probability": win_probability,
        "risks": risks,
        "advantages": advantages,
        "costs": {
            "court_fee": court_fee,
            "lawyer_fee_estimate": lawyer_fee,
            "total_estimate": court_fee + lawyer_fee,
            "time_months": time_months
        }
    }


def _calculate_court_fee(amount: float) -> float:
    """计算法院诉讼费（财产案件标准）"""
    if amount <= 10000:
        return 50
    elif amount <= 100000:
        return 50 + (amount - 10000) * 0.025
    elif amount <= 200000:
        return 2300 + (amount - 100000) * 0.02
    elif amount <= 500000:
        return 4300 + (amount - 200000) * 0.015
    elif amount <= 1000000:
        return 8800 + (amount - 500000) * 0.01
    else:
        return 13800 + (amount - 1000000) * 0.005


def _estimate_lawyer_fee(amount: float, case_type: str) -> float:
    """估算律师费"""
    base = max(3000, amount * 0.05)
    if case_type == "知识产权":
        base *= 1.5
    return round(base, 2)


def _estimate_duration(case_type: str) -> int:
    """估算诉讼周期（月）"""
    durations = {
        "劳动争议": 4,  # 仲裁2-3月 + 可能的诉讼
        "合同纠纷": 6,
        "知识产权": 8,
        "数据合规": 6,
    }
    return durations.get(case_type, 6)


def format_report(assessment: dict, case_type: str) -> str:
    """格式化评估报告"""
    report = f"# 诉讼风险评估报告\n\n"
    report += f"**案由**: {case_type}\n"
    report += f"**评估时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
    report += "---\n\n"

    report += f"## 📊 综合评分: {assessment['score']}/100\n\n"
    report += f"**胜诉概率**: {assessment['win_probability']}\n\n"

    if assessment['advantages']:
        report += "## ✅ 有利因素\n\n"
        for a in assessment['advantages']:
            report += f"- {a}\n"
        report += "\n"

    if assessment['risks']:
        report += "## ⚠️ 不利因素\n\n"
        for r in assessment['risks']:
            report += f"- {r}\n"
        report += "\n"

    costs = assessment['costs']
    report += "## 💰 诉讼成本估算\n\n"
    report += f"- 法院诉讼费: ¥{costs['court_fee']:,.0f}\n"
    report += f"- 律师费估算: ¥{costs['lawyer_fee_estimate']:,.0f}\n"
    report += f"- **总成本估算**: ¥{costs['total_estimate']:,.0f}\n"
    report += f"- 预计周期: {costs['time_months']}个月\n\n"

    report += "---\n\n⚠️ *本评估仅供参考，不构成法律建议。*\n"
    return report


def main():
    import argparse
    parser = argparse.ArgumentParser(description="诉讼风险评估")
    parser.add_argument("--case-type", default="合同纠纷")
    parser.add_argument("--amount", type=float, default=0, help="涉案金额")
    parser.add_argument("--has-contract", action="store_true")
    parser.add_argument("--no-evidence", action="store_true")
    parser.add_argument("--expired", action="store_true", help="已过时效")
    parser.add_argument("--output", "-o")
    args = parser.parse_args()

    case_data = {
        "case_type": args.case_type,
        "amount": args.amount,
        "has_contract": args.has_contract,
        "has_evidence": not args.no_evidence,
        "is_within_limitation": not args.expired,
        "defendant_able_to_pay": True
    }

    result = assess_risk(case_data)
    report = format_report(result, args.case_type)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"✅ 评估报告已保存至: {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()
