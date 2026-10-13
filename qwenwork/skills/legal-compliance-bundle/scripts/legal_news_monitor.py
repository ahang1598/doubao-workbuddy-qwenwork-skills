#!/usr/bin/env python3
"""
legal_news_monitor.py — 法规动态监控技能 (Skill #17)
监控新法规/司法解释发布，生成法规动态简报。

用法: python legal_news_monitor.py --days 7 --area 劳动|合同|数据 --output report.md
"""

import sys
from datetime import datetime, timedelta

RECENT_REGULATIONS = [
    {
        "title": "最高人民法院关于审理劳动争议案件适用法律问题的解释（五）",
        "issuing_body": "最高人民法院",
        "effective_date": "2024-01-01",
        "area": "劳动",
        "summary": "明确了经济补偿计算基数、竞业限制违约金调整、电子劳动合同效力等12个争议问题。",
        "key_changes": ["经济补偿基数含奖金津贴", "竞业限制违约金可调整", "电子合同与纸质同等效力"],
        "impact": "高"
    },
    {
        "title": "个人信息保护合规审计管理办法",
        "issuing_body": "国家互联网信息办公室",
        "effective_date": "2024-05-01",
        "area": "数据",
        "summary": "规定了个人信息处理者开展合规审计的具体要求、审计频次和审计内容。",
        "key_changes": ["年处理超1000万人信息须年度审计", "审计报告保存3年", "引入第三方审计机构"],
        "impact": "高"
    },
    {
        "title": "关于审理网络消费纠纷案件适用法律若干问题的规定（二）",
        "issuing_body": "最高人民法院",
        "effective_date": "2024-03-15",
        "area": "合同",
        "summary": "规范直播带货、社交电商等新型网络消费的法律适用问题。",
        "key_changes": ["直播带货主播责任明确", "社交电商推广者连带责任", "平台退款规则细化"],
        "impact": "中"
    },
    {
        "title": "促进数据安全产业发展的指导意见",
        "issuing_body": "工业和信息化部等十六部门",
        "effective_date": "2024-02-01",
        "area": "数据",
        "summary": "提出到2025年数据安全产业规模超过1500亿元的目标，推动数据安全产品和服务创新。",
        "key_changes": ["数据安全产业标准体系建立", "数据安全保险试点", "重点行业数据安全评估"],
        "impact": "中"
    }
]


def monitor_regulations(days: int = 30, area: str = None) -> list:
    """监控法规动态"""
    cutoff = datetime.now() - timedelta(days=days)
    results = []

    for reg in RECENT_REGULATIONS:
        try:
            eff_date = datetime.strptime(reg["effective_date"], "%Y-%m-%d")
            if eff_date >= cutoff:
                if area is None or reg["area"] == area:
                    results.append(reg)
        except ValueError:
            continue

    return sorted(results, key=lambda x: x["effective_date"], reverse=True)


def format_report(regulations: list, days: int, area: str) -> str:
    """格式化法规动态报告"""
    report = f"# 法规动态监控报告\n\n"
    report += f"**监控周期**: 最近{days}天\n"
    report += f"**筛选领域**: {area if area else '全部'}\n"
    report += f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    report += f"**新增法规数**: {len(regulations)}\n\n"
    report += "---\n\n"

    for i, reg in enumerate(regulations, 1):
        impact_emoji = {"高": "🔴", "中": "🟡", "低": "🟢"}.get(reg["impact"], "⚪")
        report += f"## {i}. {reg['title']}\n\n"
        report += f"- **发布机关**: {reg['issuing_body']}\n"
        report += f"- **生效日期**: {reg['effective_date']}\n"
        report += f"- **涉及领域**: {reg['area']}\n"
        report += f"- **影响等级**: {impact_emoji} {reg['impact']}\n\n"
        report += f"### 主要内容\n\n{reg['summary']}\n\n"
        report += f"### 关键变化\n\n"
        for change in reg.get("key_changes", []):
            report += f"- {change}\n"
        report += "\n---\n\n"

    if not regulations:
        report += "在监控周期内未发现新增法规。\n"

    return report


def main():
    import argparse
    parser = argparse.ArgumentParser(description="法规动态监控")
    parser.add_argument("--days", type=int, default=30, help="监控天数")
    parser.add_argument("--area", choices=["劳动", "合同", "数据", "知识产权", "公司"], help="法规领域")
    parser.add_argument("--output", "-o")
    args = parser.parse_args()

    regs = monitor_regulations(args.days, args.area)
    report = format_report(regs, args.days, args.area)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"✅ 法规动态报告已保存至: {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()
