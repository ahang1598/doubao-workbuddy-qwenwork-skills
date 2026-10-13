#!/usr/bin/env python3
"""
statute_limitation.py — 诉讼时效检查技能 (Skill #16)
检查各类法律纠纷的诉讼时效是否过期。

用法: python statute_limitation.py --type <纠纷类型> --date <事件日期> [--output report.md]
"""

import sys
import json
from datetime import datetime, timedelta
from pathlib import Path

# ─── 诉讼时效规则 ───
LIMITATION_RULES = {
    "普通民事": {"years": 3, "law": "《民法典》第188条", "note": "自知道或应当知道权利受损之日起计算"},
    "合同纠纷": {"years": 3, "law": "《民法典》第188条", "note": "自知道或应当知道违约之日起计算"},
    "借款纠纷": {"years": 3, "law": "《民法典》第188条", "note": "自还款期限届满之日起计算"},
    "人身损害": {"years": 3, "law": "《民法典》第188条", "note": "自知道或应当知道损害之日起计算"},
    "劳动争议": {"years": 1, "law": "《劳动争议调解仲裁法》第27条", "note": "自知道或应当知道权利被侵害之日起计算，劳动关系存续期间不受此限"},
    "工伤认定": {"days": 365, "law": "《工伤保险条例》第17条", "note": "用人单位30日内申请；个人/近亲属1年内申请"},
    "产品质量": {"years": 2, "law": "《产品质量法》第45条", "note": "自知道或应当知道权益受损之日起计算"},
    "知识产权侵权": {"years": 3, "law": "《民法典》第188条", "note": "自知道或应当知道侵权之日起计算"},
    "买卖合同": {"years": 3, "law": "《民法典》第188条", "note": "自知道或应当知道违约之日起计算"},
    "建设工程": {"years": 3, "law": "《民法典》第188条", "note": "自知道或应当知道权利受损之日起计算"},
    "租赁合同": {"years": 3, "law": "《民法典》第188条", "note": "自知道或应当知道违约之日起计算"},
    "侵权责任": {"years": 3, "law": "《民法典》第188条", "note": "自知道或应当知道损害之日起计算"},
    "环境污染": {"years": 3, "law": "《环境保护法》第66条", "note": "自知道或应当知道损害之日起计算"},
    "海上货物运输": {"years": 1, "law": "《海商法》第257条", "note": "自交付或应当交付之日起计算"},
    "保险合同": {"years": 5, "law": "《保险法》第26条", "note": "人寿保险5年，其他保险2年"},
}


def check_limitation(dispute_type: str, event_date_str: str) -> dict:
    """Check if statute of limitations has expired."""
    # Parse event date
    for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%Y年%m月%d日"]:
        try:
            event_date = datetime.strptime(event_date_str, fmt)
            break
        except ValueError:
            continue
    else:
        return {"error": f"无法解析日期: {event_date_str}，请使用 YYYY-MM-DD 格式"}
    
    if dispute_type not in LIMITATION_RULES:
        return {"error": f"未找到'{dispute_type}'的时效规则"}
    
    rule = LIMITATION_RULES[dispute_type]
    now = datetime.now()
    
    # Calculate deadline
    if "years" in rule:
        deadline = event_date.replace(year=event_date.year + rule["years"])
    elif "days" in rule:
        deadline = event_date + timedelta(days=rule["days"])
    else:
        return {"error": "规则配置错误"}
    
    remaining = (deadline - now).days
    expired = remaining < 0
    
    # Status
    if expired:
        status = "已过期"
        risk = "high"
    elif remaining <= 90:
        status = "即将过期"
        risk = "high"
    elif remaining <= 365:
        status = "临近过期"
        risk = "medium"
    else:
        status = "有效期内"
        risk = "low"
    
    return {
        "dispute_type": dispute_type,
        "event_date": event_date_str,
        "limitation_years": rule.get("years"),
        "limitation_days": rule.get("days"),
        "law_basis": rule["law"],
        "note": rule["note"],
        "deadline": deadline.strftime("%Y-%m-%d"),
        "remaining_days": remaining,
        "expired": expired,
        "status": status,
        "risk_level": risk,
        "check_date": now.strftime("%Y-%m-%d"),
    }


def generate_report(result: dict) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    if "error" in result:
        return f"❌ 错误: {result['error']}"
    
    risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}
    
    lines = [
        "# 诉讼时效检查报告",
        "",
        f"**检查时间**: {now}",
        "",
        "---",
        "",
        "## 检查结果",
        "",
        f"| 项目 | 内容 |",
        f"|------|------|",
        f"| 纠纷类型 | {result['dispute_type']} |",
        f"| 事件日期 | {result['event_date']} |",
        f"| 法律依据 | {result['law_basis']} |",
        f"| 时效期限 | {result.get('limitation_years', 0) or 0}年" if result.get('limitation_years') else f"| 时效期限 | {result.get('limitation_days', 0)}天 |",
        f"| 届满日期 | {result['deadline']} |",
        f"| 剩余天数 | {result['remaining_days']} 天 |",
        f"| 当前状态 | {risk_emoji.get(result['risk_level'], '')} {result['status']} |",
        "",
        "## 法律提示",
        "",
        f"📝 {result['note']}",
        "",
    ]
    
    if result["expired"]:
        lines.extend([
            "## ⚠️ 时效已届满",
            "",
            "诉讼时效已过期，但请注意：",
            "1. **中止/中断**: 如存在时效中止或中断事由（如对方同意履行、提起仲裁等），时效可能重新计算",
            "2. **自愿履行**: 超过诉讼时效不影响实体权利，对方自愿履行的仍有效",
            "3. **特殊情形**: 劳动争议中，劳动关系存续期间不受时效限制",
            "",
            "建议尽快咨询专业律师，确认是否存在中止/中断事由。",
            "",
        ])
    elif result["remaining_days"] <= 90:
        lines.extend([
            "## ⚠️ 紧急提醒",
            "",
            f"诉讼时效将在{result['remaining_days']}天后届满！请立即采取行动：",
            "1. 向对方发送书面催告函（保留送达证据）",
            "2. 向法院/仲裁机构提起诉讼/仲裁",
            "3. 对方书面确认债务（构成时效中断）",
            "",
        ])
    
    lines.extend([
        "## 时效中止/中断事由",
        "",
        "| 类型 | 事由 | 法律依据 |",
        "|------|------|----------|",
        "| 中止 | 不可抗力或其他障碍 | 民法典第194条 |",
        "| 中断 | 提起诉讼/仲裁/催告/对方同意履行 | 民法典第195条 |",
        "",
        "---",
        "",
        "## 免责声明",
        "",
        "本报告由AI自动生成，仅供参考，不构成法律意见。",
        "诉讼时效的认定涉及复杂的中止/中断事由，建议咨询专业律师。",
        "",
        f"*Generated by Legal Compliance Skill Bundle v1.0.0*",
    ])
    
    return "\n".join(lines)


def main():
    dispute_type = None
    event_date = None
    output_file = None
    
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--type" and i + 1 < len(args):
            dispute_type = args[i + 1]
            i += 2
        elif args[i] == "--date" and i + 1 < len(args):
            event_date = args[i + 1]
            i += 2
        elif args[i] == "--output" and i + 1 < len(args):
            output_file = args[i + 1]
            i += 2
        elif args[i] == "--list":
            print("支持的纠纷类型:")
            for t, info in LIMITATION_RULES.items():
                limit = f"{info.get('years', 0)}年" if info.get('years') else f"{info.get('days', 0)}天"
                print(f"  • {t}: {limit} ({info['law']})")
            sys.exit(0)
        else:
            i += 1
    
    if not dispute_type or not event_date:
        print("用法:")
        print("  python statute_limitation.py --type '合同纠纷' --date '2024-01-15' [--output report.md]")
        print("  python statute_limitation.py --list  # 查看支持的纠纷类型")
        sys.exit(1)
    
    result = check_limitation(dispute_type, event_date)
    
    if "error" in result:
        print(f"[ERROR] {result['error']}")
        sys.exit(1)
    
    print(f"\n{result['dispute_type']} | 时效至: {result['deadline']} | 剩余{result['remaining_days']}天 | {result['status']}")
    
    report = generate_report(result)
    
    if output_file:
        Path(output_file).write_text(report, encoding="utf-8")
        print(f"报告已保存: {output_file}")
    else:
        print("\n" + report)


if __name__ == "__main__":
    main()
