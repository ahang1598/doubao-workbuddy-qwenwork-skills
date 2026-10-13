#!/usr/bin/env python3
"""
regulation_explain.py — 法规解读技能 (Skill #13)
将法律条文转化为通俗易懂的语言解释，附带实际应用场景。

用法: python regulation_explain.py "《劳动合同法》第47条" [--detail brief|full]
"""

import sys
import json
from datetime import datetime

# ─── 法规知识库 ─────────────────────────────────────────
REGULATION_DB = {
    "劳动合同法": {
        "第47条": {
            "原文": "经济补偿按劳动者在本单位工作的年限，每满一年支付一个月工资的标准向劳动者支付。六个月以上不满一年的，按一年计算；不满六个月的，向劳动者支付半个月工资的经济补偿。",
            "通俗解释": "公司辞退你时，要给你一笔补偿金。算法很简单：干满1年补1个月工资，干了6个月到1年也算1个月，不满6个月补半个月。这里的'月工资'是离职前12个月的平均工资。",
            "实际案例": "小王在公司工作了3年7个月，月薪10000元。被辞退时应得经济补偿：4个月 × 10000元 = 40000元。",
            "注意事项": [
                "月工资高于当地社平工资3倍的，按3倍计算且年限最高不超过12年",
                "月工资指离职前12个月的平均工资（含奖金、津贴）",
                "协商解除、经济性裁员、劳动合同到期不续签等情况适用"
            ]
        },
        "第82条": {
            "原文": "用人单位自用工之日起超过一个月不满一年未与劳动者订立书面劳动合同的，应当向劳动者每月支付二倍的工资。",
            "通俗解释": "公司雇了你但超过1个月还没签书面合同，从第2个月开始要给你双倍工资，最多补11个月。这是法律对不签合同的惩罚。",
            "实际案例": "小李入职后公司一直没签合同，工作了8个月。应得双倍工资差额：7个月 × 月薪 = 7个月工资的额外赔偿。",
            "注意事项": [
                "仲裁时效为1年，从知道权利被侵害之日起算",
                "员工拒签的，用人单位应在1个月内书面终止劳动关系",
                "双倍工资上限为11个月（第2个月到第12个月）"
            ]
        }
    },
    "民法典": {
        "第496条": {
            "原文": "格式条款是当事人为了重复使用而预先拟定，并在订立合同时未与对方协商的条款。采用格式条款订立合同的，提供格式条款的一方应当遵循公平原则确定当事人之间的权利和义务，并采取合理的方式提示对方注意免除或者减轻其责任等与对方有重大利害关系的条款。",
            "通俗解释": "格式条款就是'甲方模板合同'里那些你没得商量的条款。法律要求提供方必须明确提醒你注意那些对你不利的条款，比如免责条款。如果没提醒你，你可以主张这些条款不算数。",
            "实际案例": "保险合同中的免责条款用极小字体印刷，未特别提示投保人。法院认定该免责条款不成为合同内容。",
            "注意事项": [
                "未履行提示/说明义务的格式条款，对方可主张不成为合同内容",
                "不合理地免除己方责任、加重对方责任、排除对方主要权利的格式条款无效",
                "格式条款与非格式条款不一致的，以非格式条款为准"
            ]
        }
    },
    "个人信息保护法": {
        "第13条": {
            "原文": "符合下列情形之一的，个人信息处理者方可处理个人信息：（一）取得个人的同意；（二）为订立、履行个人作为一方当事人的合同所必需...",
            "通俗解释": "处理别人个人信息必须有合法理由。最常见的就是'用户同意'，但也有例外——比如签合同必须要的信息、法律要求的、紧急情况等可以不经过同意。",
            "实际案例": "APP要求获取通讯录权限但与核心功能无关，用户拒绝后无法使用APP。该行为违反知情同意原则。",
            "注意事项": [
                "同意必须是自愿、明确的，不能默认勾选",
                "处理敏感信息需要'单独同意'",
                "14岁以下未成年人的信息需要监护人同意"
            ]
        }
    }
}


def explain_regulation(ref: str, detail: str = "full") -> str:
    """解读法律条文"""
    # 解析引用格式：《法律名》第X条
    import re
    match = re.search(r"《([^》]+)》\s*第\s*(\d+)\s*条", ref)
    if not match:
        return f"无法解析法律条文引用：{ref}\n\n请使用格式：《法律名》第X条\n例如：《劳动合同法》第47条"

    law_name = match.group(1)
    article = f"第{match.group(2)}条"

    law_data = REGULATION_DB.get(law_name)
    if not law_data:
        return f"暂未收录《{law_name}》的条文解读。\n\n已收录：{', '.join(REGULATION_DB.keys())}"

    article_data = law_data.get(article)
    if not article_data:
        return f"暂未收录《{law_name}》{article}的解读。\n\n已收录条文：{', '.join(law_data.keys())}"

    # 生成报告
    report = f"# 法规解读：《{law_name}》{article}\n\n"
    report += f"**解读时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
    report += "---\n\n"

    report += f"## 📜 法条原文\n\n{article_data['原文']}\n\n"
    report += f"## 💡 通俗解释\n\n{article_data['通俗解释']}\n\n"

    if detail == "full":
        report += f"## 📋 实际案例\n\n{article_data['实际案例']}\n\n"
        report += "## ⚠️ 注意事项\n\n"
        for note in article_data.get("注意事项", []):
            report += f"- {note}\n"
        report += "\n"

    report += "---\n\n⚠️ *本解读仅供参考，具体案件请咨询专业律师。*\n"
    return report


def main():
    import argparse
    parser = argparse.ArgumentParser(description="法规解读技能")
    parser.add_argument("reference", help="法律条文引用，如'《劳动合同法》第47条'")
    parser.add_argument("--detail", choices=["brief", "full"], default="full", help="详细程度")
    parser.add_argument("--output", "-o", help="输出文件路径")
    args = parser.parse_args()

    result = explain_regulation(args.reference, args.detail)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"✅ 解读已保存至: {args.output}")
    else:
        print(result)


if __name__ == "__main__":
    main()
