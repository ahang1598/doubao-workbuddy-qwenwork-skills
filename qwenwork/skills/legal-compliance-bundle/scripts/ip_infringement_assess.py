#!/usr/bin/env python3
"""
ip_infringement_assess.py — 知识产权侵权评估 (Skill #30)
评估知识产权侵权风险。
"""
import sys
from datetime import datetime

def assess_infringement(ip_type: str, description: str, is_commercial: bool = True) -> str:
    risk_factors = {
        "商标": {"高风险": ["在相同商品上使用相同商标", "使用驰名商标"], "中风险": ["在类似商品上使用近似商标", "可能导致混淆"], "低风险": ["描述性使用", "在先使用"]},
        "著作权": {"高风险": ["全文复制", "实质性相似", "商业使用"], "中风险": ["部分引用未注明出处", "改编作品"], "低风险": ["合理引用", "个人学习使用"]},
        "专利": {"高风险": ["完整实施专利权利要求", "制造销售侵权产品"], "中风险": ["部分落入权利要求范围", "使用侵权方法"], "低风险": ["研究实验使用", "在先技术抗辩"]},
        "商业秘密": {"高风险": ["明知是商业秘密仍使用", "违反保密协议"], "中风险": ["员工跳槽带走技术", "反向工程"], "低风险": ["独立开发", "公开渠道获取"]}
    }
    factors = risk_factors.get(ip_type, risk_factors["商标"])
    
    report = f"# 知识产权侵权风险评估\n\n"
    report += f"**评估时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    report += f"**IP类型**: {ip_type}\n"
    report += f"**商业使用**: {'是' if is_commercial else '否'}\n\n"
    report += "---\n\n## 风险因素对照\n\n"
    for level, items in factors.items():
        emoji = {"高风险": "🔴", "中风险": "🟡", "低风险": "🟢"}[level]
        report += f"### {emoji} {level}\n"
        for item in items:
            report += f"- {item}\n"
        report += "\n"
    report += "## 建议\n\n"
    report += "1. 进行正式的FTO（自由实施）分析\n"
    report += "2. 咨询知识产权律师获取专业意见\n"
    report += "3. 如确有侵权风险，考虑许可、规避设计或和解\n"
    return report

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip-type", default="商标", choices=["商标", "著作权", "专利", "商业秘密"])
    parser.add_argument("--description", default="")
    parser.add_argument("--non-commercial", action="store_true")
    parser.add_argument("--output", "-o")
    args = parser.parse_args()
    result = assess_infringement(args.ip_type, args.description, not args.non-commercial)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f: f.write(result)
        print(f"✅ 已保存至: {args.output}")
    else: print(result)

if __name__ == "__main__": main()
