#!/usr/bin/env python3
"""
compliance_audit_checklist.py — 合规审计清单生成器 (Skill #50)
根据企业类型和行业生成内部合规审计检查表。

用法: python compliance_audit_checklist.py --type <企业类型> [--scope <检查范围>] [--output checklist.md]
"""

import sys
import json
from datetime import datetime
from pathlib import Path

# ─── 合规审计检查项 ───
AUDIT_CATEGORIES = {
    "劳动用工": {
        "scope": ["general", "labor", "all"],
        "items": [
            {"id": "AL001", "item": "劳动合同签订率是否达到100%", "severity": "high", "law": "《劳动合同法》第10条"},
            {"id": "AL002", "item": "劳动合同必备条款是否完整", "severity": "high", "law": "《劳动合同法》第17条"},
            {"id": "AL003", "item": "试用期是否符合法定要求", "severity": "high", "law": "《劳动合同法》第19-21条"},
            {"id": "AL004", "item": "加班制度是否合规（加班费、时长上限）", "severity": "high", "law": "《劳动法》第41-44条"},
            {"id": "AL005", "item": "社保五险一金缴纳是否合规", "severity": "high", "law": "《社会保险法》第58条"},
            {"id": "AL006", "item": "员工手册是否经民主程序制定并向员工公示", "severity": "medium", "law": "《劳动合同法》第4条"},
            {"id": "AL007", "item": "竞业限制协议是否合理（期限≤2年、有经济补偿）", "severity": "medium", "law": "《劳动合同法》第23-24条"},
            {"id": "AL008", "item": "解除/终止劳动合同程序是否合规", "severity": "high", "law": "《劳动合同法》第36-50条"},
            {"id": "AL009", "item": "女职工/未成年工特殊保护是否到位", "severity": "high", "law": "《劳动法》第58-65条"},
            {"id": "AL010", "item": "劳务派遣用工是否符合比例限制（≤10%）", "severity": "medium", "law": "《劳务派遣暂行规定》第4条"},
        ],
    },
    "数据安全与隐私": {
        "scope": ["general", "data", "all"],
        "items": [
            {"id": "AD001", "item": "是否制定并公布隐私政策", "severity": "high", "law": "《个人信息保护法》第17条"},
            {"id": "AD002", "item": "个人信息收集是否遵循最小必要原则", "severity": "high", "law": "《个人信息保护法》第6条"},
            {"id": "AD003", "item": "是否取得个人的有效同意", "severity": "high", "law": "《个人信息保护法》第13-14条"},
            {"id": "AD004", "item": "敏感个人信息是否取得单独同意", "severity": "high", "law": "《个人信息保护法》第29条"},
            {"id": "AD005", "item": "是否提供个人信息查阅/复制/更正/删除途径", "severity": "high", "law": "《个人信息保护法》第44-47条"},
            {"id": "AD006", "item": "数据跨境传输是否通过安全评估/标准合同", "severity": "high", "law": "《个人信息保护法》第38-39条"},
            {"id": "AD007", "item": "是否采取加密、去标识化等安全措施", "severity": "medium", "law": "《个人信息保护法》第51条"},
            {"id": "AD008", "item": "是否制定数据泄露应急预案", "severity": "medium", "law": "《个人信息保护法》第57条"},
            {"id": "AD009", "item": "是否进行数据分类分级管理", "severity": "medium", "law": "《数据安全法》第21条"},
            {"id": "AD010", "item": "是否建立数据安全管理制度", "severity": "medium", "law": "《数据安全法》第27条"},
        ],
    },
    "合同管理": {
        "scope": ["general", "contract", "all"],
        "items": [
            {"id": "AC001", "item": "合同审批流程是否规范", "severity": "medium", "law": "内控制度"},
            {"id": "AC002", "item": "合同条款是否经过法律审查", "severity": "medium", "law": "内控制度"},
            {"id": "AC003", "item": "合同签署权限是否明确", "severity": "high", "law": "《民法典》代理制度"},
            {"id": "AC004", "item": "合同台账和档案管理是否完善", "severity": "low", "law": "内控制度"},
            {"id": "AC005", "item": "合同履行跟踪是否到位", "severity": "medium", "law": "内控制度"},
            {"id": "AC006", "item": "违约处理流程是否明确", "severity": "medium", "law": "《民法典》合同编"},
            {"id": "AC007", "item": "合同到期预警机制是否建立", "severity": "low", "law": "内控制度"},
        ],
    },
    "知识产权": {
        "scope": ["general", "ip", "all"],
        "items": [
            {"id": "AI001", "item": "商标注册和续展是否及时", "severity": "high", "law": "《商标法》"},
            {"id": "AI002", "item": "专利申请和维护是否规范", "severity": "medium", "law": "《专利法》"},
            {"id": "AI003", "item": "著作权归属是否明确（特别是职务作品）", "severity": "high", "law": "《著作权法》"},
            {"id": "AI004", "item": "商业秘密保护措施是否到位", "severity": "high", "law": "《反不正当竞争法》"},
            {"id": "AI005", "item": "员工知识产权归属协议是否签订", "severity": "medium", "law": "《专利法》第6条"},
            {"id": "AI006", "item": "第三方知识产权侵权风险是否排查", "severity": "medium", "law": "《专利法》《商标法》"},
        ],
    },
    "企业治理": {
        "scope": ["general", "governance", "all"],
        "items": [
            {"id": "AG001", "item": "股东会/董事会决议是否规范", "severity": "high", "law": "《公司法》"},
            {"id": "AG002", "item": "关联交易是否履行披露和审批程序", "severity": "high", "law": "《公司法》第21条"},
            {"id": "AG003", "item": "反腐败/反商业贿赂制度是否建立", "severity": "high", "law": "《刑法》第163-164条"},
            {"id": "AG004", "item": "反洗钱/KYC制度是否合规", "severity": "medium", "law": "《反洗钱法》"},
            {"id": "AG005", "item": "财务制度是否健全", "severity": "medium", "law": "《会计法》"},
            {"id": "AG006", "item": "税务申报是否合规", "severity": "high", "law": "《税收征收管理法》"},
        ],
    },
}


def generate_checklist(scope: str = "all") -> dict:
    """Generate audit checklist based on scope."""
    checklist = {}
    total_items = 0
    
    for category, data in AUDIT_CATEGORIES.items():
        if scope in data["scope"] or scope == "all":
            checklist[category] = data["items"]
            total_items += len(data["items"])
    
    return {"checklist": checklist, "total_items": total_items}


def generate_report(scope: str, result: dict) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    lines = [
        "# 内部合规审计检查表",
        "",
        f"**生成时间**: {now}",
        f"**检查范围**: {scope}",
        f"**检查项总数**: {result['total_items']}",
        "",
        "---",
        "",
        "## 使用说明",
        "",
        "请对每个检查项进行评估，在「结果」列标注：✅合规 / ⚠️部分合规 / ❌不合规 / N/A不适用",
        "在「备注」列记录发现的问题和整改措施。",
        "",
    ]
    
    for category, items in result["checklist"].items():
        lines.extend([f"## {category}", ""])
        lines.append("| 编号 | 检查项 | 法律依据 | 风险 | 结果 | 备注 |")
        lines.append("|------|--------|----------|------|------|------|")
        
        for item in items:
            sev = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(item["severity"], "⚪")
            lines.append(f"| {item['id']} | {item['item']} | {item['law']} | {sev} | ___ | ___ |")
        
        lines.append("")
    
    # Summary section
    lines.extend([
        "## 审计结论",
        "",
        "| 类别 | 合规项 | 不合规项 | 合规率 |",
        "|------|--------|----------|--------|",
    ])
    
    for category in result["checklist"]:
        lines.append(f"| {category} | __ / __ | __ / __ | __% |")
    
    lines.extend([
        "| **合计** | __ | __ | __% |",
        "",
        "## 整改计划",
        "",
        "| 序号 | 问题描述 | 整改措施 | 责任人 | 完成期限 | 状态 |",
        "|------|----------|----------|--------|----------|------|",
        "| 1 | | | | | ⬜ |",
        "| 2 | | | | | ⬜ |",
        "",
        "---",
        "",
        "## 免责声明",
        "",
        "本检查表由AI自动生成，仅供参考。合规审计建议由专业律师或合规团队执行。",
        "",
        f"*Generated by Legal Compliance Skill Bundle v1.0.0*",
    ])
    
    return "\n".join(lines)


def main():
    scope = "all"
    output_file = None
    
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--scope" and i + 1 < len(args):
            scope = args[i + 1]
            i += 2
        elif args[i] == "--output" and i + 1 < len(args):
            output_file = args[i + 1]
            i += 2
        elif args[i] == "--type" and i + 1 < len(args):
            scope = args[i + 1]  # alias
            i += 2
        else:
            i += 1
    
    result = generate_checklist(scope)
    print(f"已生成合规审计检查表: {len(result['checklist'])}个类别, {result['total_items']}个检查项")
    
    report = generate_report(scope, result)
    
    if output_file:
        Path(output_file).write_text(report, encoding="utf-8")
        print(f"检查表已保存: {output_file}")
    else:
        print("\n" + report)


if __name__ == "__main__":
    main()
