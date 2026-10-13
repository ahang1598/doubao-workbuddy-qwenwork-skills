#!/usr/bin/env python3
"""
termination_risk.py — 解雇风险评估技能 (Skill #22)
评估用人单位解除劳动合同的法律风险。

用法: python termination_risk.py --reason <解除原因> --details <详情> [--output report.md]
      python termination_risk.py --interactive
"""

import sys
import json
from datetime import datetime
from pathlib import Path

# ─── 解雇原因与法律风险 ───
TERMINATION_REASONS = {
    "严重违纪": {
        "legal_basis": "《劳动合同法》第39条第(二)项",
        "conditions": [
            "规章制度经过民主程序制定",
            "规章制度已向劳动者公示",
            "违纪行为确属严重",
            "有充分的证据证明违纪事实",
            "通知工会",
        ],
        "risk_level": "medium",
        "tips": "建议：保留完整的违纪记录和处理流程，确保规章制度合法有效",
        "compensation": "无需支付经济补偿金",
    },
    "试用期不合格": {
        "legal_basis": "《劳动合同法》第39条第(一)项",
        "conditions": [
            "试用期在法定期限内",
            "有明确的录用条件",
            "录用条件已告知劳动者",
            "有证据证明不符合录用条件",
            "在试用期届满前作出决定",
        ],
        "risk_level": "high",
        "tips": "建议：录用条件需书面化并由员工签字确认，考核需有客观标准",
        "compensation": "无需支付经济补偿金",
    },
    "不胜任工作": {
        "legal_basis": "《劳动合同法》第40条第(二)项",
        "conditions": [
            "有明确的考核标准",
            "经考核确实不胜任",
            "经过培训或调岗",
            "培训/调岗后仍不胜任",
            "提前30日书面通知或额外支付1个月工资",
            "通知工会",
        ],
        "risk_level": "high",
        "tips": "建议：必须先培训或调岗，不能直接解除！程序复杂，建议HR全程留痕",
        "compensation": "需支付经济补偿金（N）",
    },
    "客观情况变化": {
        "legal_basis": "《劳动合同法》第40条第(三)项",
        "conditions": [
            "客观情况发生重大变化",
            "导致合同无法履行",
            "经协商未能达成一致",
            "提前30日书面通知或额外支付1个月工资",
            "通知工会",
        ],
        "risk_level": "high",
        "tips": "建议：'客观情况'需有充分依据，协商过程需留痕",
        "compensation": "需支付经济补偿金（N）",
    },
    "经济性裁员": {
        "legal_basis": "《劳动合同法》第41条",
        "conditions": [
            "符合法定裁员情形（破产重整/经营困难/技术革新等）",
            "裁减20人以上或占总人数10%以上",
            "提前30日向工会或全体职工说明",
            "听取工会或职工意见",
            "向劳动行政部门报告",
            "优先留用特定人员",
        ],
        "risk_level": "high",
        "tips": "建议：程序复杂，建议聘请专业劳动法律师指导",
        "compensation": "需支付经济补偿金（N）",
    },
    "协商解除": {
        "legal_basis": "《劳动合同法》第36条",
        "conditions": [
            "双方真实意思表示",
            "书面协议",
            "明确补偿方案",
        ],
        "risk_level": "low",
        "tips": "建议：协商解除最安全，但需确保员工自愿签字，避免胁迫嫌疑",
        "compensation": "协商确定，通常N或N+1",
    },
    "劳动合同期满": {
        "legal_basis": "《劳动合同法》第44条",
        "conditions": [
            "合同期限届满",
            "不属于应续签情形",
            "用人单位维持或提高条件而劳动者不续签的除外",
        ],
        "risk_level": "low",
        "tips": "注意：连续订立两次固定期限合同后，劳动者有权要求签订无固定期限合同",
        "compensation": "2008年后需支付经济补偿金（除用人单位维持或提高条件续签被拒情形）",
    },
    "严重失职": {
        "legal_basis": "《劳动合同法》第39条第(三)项",
        "conditions": [
            "劳动者严重失职",
            "营私舞弊",
            "给用人单位造成重大损害",
            "有充分证据",
            "通知工会",
        ],
        "risk_level": "medium",
        "tips": "建议：'重大损害'需在规章制度中明确量化标准",
        "compensation": "无需支付经济补偿金",
    },
}


def assess_risk(reason: str, details: str = "") -> dict:
    """Assess termination risk for a given reason."""
    if reason not in TERMINATION_REASONS:
        return {
            "reason": reason,
            "found": False,
            "message": f"未找到'{reason}'的预设分析。建议咨询专业律师。",
        }
    
    info = TERMINATION_REASONS[reason]
    return {
        "reason": reason,
        "found": True,
        "legal_basis": info["legal_basis"],
        "risk_level": info["risk_level"],
        "conditions": info["conditions"],
        "tips": info["tips"],
        "compensation": info["compensation"],
        "details": details,
    }


def generate_report(assessment: dict) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}
    
    lines = [
        "# 解雇风险评估报告",
        "",
        f"**生成时间**: {now}",
        f"**解除原因**: {assessment['reason']}",
        "",
        "---",
        "",
        "## 风险概览",
        "",
        f"| 项目 | 内容 |",
        f"|------|------|",
        f"| 解除原因 | {assessment['reason']} |",
        f"| 法律依据 | {assessment.get('legal_basis', 'N/A')} |",
        f"| 风险等级 | {risk_emoji.get(assessment.get('risk_level'), '❓')} {assessment.get('risk_level', 'unknown').upper()} |",
        f"| 经济补偿 | {assessment.get('compensation', 'N/A')} |",
        "",
        "## 合法解除的前提条件",
        "",
    ]
    
    for i, cond in enumerate(assessment.get("conditions", []), 1):
        lines.append(f"{i}. {cond}")
    lines.append("")
    
    lines.extend([
        "## 风险提示与建议",
        "",
        f"💡 {assessment.get('tips', '请咨询专业律师')}",
        "",
    ])
    
    if assessment.get("details"):
        lines.extend([
            "## 案件详情",
            "",
            f"> {assessment['details']}",
            "",
        ])
    
    lines.extend([
        "---",
        "",
        "## 经济补偿金速算",
        "",
        "| 工龄 | 补偿标准 |",
        "|------|----------|",
        "| 每满1年 | 1个月工资 |",
        "| 6个月以上不满1年 | 1个月工资 |",
        "| 不满6个月 | 0.5个月工资 |",
        "| 月工资上限 | 当地社平工资3倍 |",
        "",
        "## 免责声明",
        "",
        "本报告由AI自动生成，仅供参考，不构成法律意见。",
        "解除劳动合同建议由专业劳动法律师进行风险评估。",
        "",
        f"*Generated by Legal Compliance Skill Bundle v1.0.0*",
    ])
    
    return "\n".join(lines)


def interactive_mode():
    print("=" * 50)
    print("解雇风险评估 — 交互式模式")
    print("=" * 50)
    print("\n可选解除原因:")
    for i, reason in enumerate(TERMINATION_REASONS.keys(), 1):
        info = TERMINATION_REASONS[reason]
        emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}[info["risk_level"]]
        print(f"  {i}. {emoji} {reason}")
    
    print("\n请输入序号或原因名称:")
    choice = input("> ").strip()
    
    try:
        idx = int(choice) - 1
        reason = list(TERMINATION_REASONS.keys())[idx]
    except (ValueError, IndexError):
        reason = choice
    
    details = input("请输入补充说明（可选）: ").strip()
    return reason, details


def main():
    reason = None
    details = ""
    output_file = None
    
    if "--interactive" in sys.argv:
        reason, details = interactive_mode()
    elif "--reason" in sys.argv:
        idx = sys.argv.index("--reason")
        if idx + 1 < len(sys.argv):
            reason = sys.argv[idx + 1]
    
    if "--details" in sys.argv:
        idx = sys.argv.index("--details")
        if idx + 1 < len(sys.argv):
            details = sys.argv[idx + 1]
    
    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        if idx + 1 < len(sys.argv):
            output_file = sys.argv[idx + 1]
    
    if not reason:
        print("用法:")
        print("  python termination_risk.py --interactive")
        print("  python termination_risk.py --reason '严重违纪' [--details '连续旷工3天'] [--output report.md]")
        sys.exit(1)
    
    assessment = assess_risk(reason, details)
    
    if not assessment.get("found"):
        print(f"[WARN] {assessment['message']}")
        sys.exit(1)
    
    print(f"\n风险等级: {assessment['risk_level'].upper()}")
    print(f"法律依据: {assessment['legal_basis']}")
    print(f"经济补偿: {assessment['compensation']}")
    
    report = generate_report(assessment)
    
    if output_file:
        Path(output_file).write_text(report, encoding="utf-8")
        print(f"报告已保存: {output_file}")
    else:
        print("\n" + report)


if __name__ == "__main__":
    main()
