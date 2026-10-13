#!/usr/bin/env python3
"""
legal_opinion_gen.py — 法律意见书生成技能 (Skill #14)
根据案情描述自动生成法律意见书草稿。

用法: python legal_opinion_gen.py --input case_description.txt --output opinion.md
"""

import sys
import os
from datetime import datetime

LEGAL_OPINION_TEMPLATE = """# 法律意见书

**出具日期**: {date}
**案由**: {case_type}
**委托人**: {client}

---

## 一、基本事实

{facts}

## 二、法律分析

### 2.1 适用法律法规

{applicable_laws}

### 2.2 法律关系分析

{legal_analysis}

### 2.3 风险评估

{risk_assessment}

## 三、法律意见

{opinion}

## 四、建议措施

{suggestions}

---

**免责声明**: 本法律意见书仅基于委托人提供的事实材料出具，如事实情况发生变化，法律意见可能相应调整。本意见书不构成正式法律建议，具体法律事务请咨询执业律师。

**出具人**: AI法律助手
**日期**: {date}
"""


def generate_opinion(case_input: dict) -> str:
    """生成法律意见书"""
    case_type = case_input.get("case_type", "合同纠纷")
    facts = case_input.get("facts", "")
    client = case_input.get("client", "委托人")

    # 根据案由自动匹配法律分析
    analysis_map = {
        "合同纠纷": {
            "laws": "《民法典》合同编（第463-988条）、《最高人民法院关于适用〈民法典〉合同编的解释》",
            "analysis": "本案系合同纠纷，需审查：(1) 合同是否有效成立；(2) 各方是否依约履行；(3) 违约事实是否成立；(4) 损失与违约行为的因果关系。",
            "risks": "- 合同效力风险：如存在欺诈、胁迫等情形，合同可能被撤销\n- 举证风险：需提供充分证据证明违约事实和损失金额\n- 诉讼时效风险：一般诉讼时效为3年",
            "opinion": "根据委托人提供的事实和材料，本律师认为对方已构成合同违约，委托人有权要求其承担违约责任，包括继续履行、采取补救措施或赔偿损失。",
            "suggestions": "1. 收集并保全合同原件、往来函件、付款凭证等证据\n2. 向对方发送书面催告函\n3. 催告无果后可提起民事诉讼或申请仲裁"
        },
        "劳动争议": {
            "laws": "《劳动合同法》、《劳动法》、《劳动争议调解仲裁法》",
            "analysis": "本案系劳动争议，需审查：(1) 劳动关系是否成立；(2) 用人单位解除行为是否合法；(3) 经济补偿/赔偿金的计算。",
            "risks": "- 仲裁时效风险：劳动争议仲裁时效为1年\n- 举证责任：部分事项由用人单位承担举证责任\n- 执行风险：用人单位可能无财产可供执行",
            "opinion": "根据委托人陈述的事实，用人单位的解除行为存在程序瑕疵，可能构成违法解除，委托人有权主张赔偿金（2N）。",
            "suggestions": "1. 先向劳动仲裁委员会申请仲裁\n2. 收集劳动合同、工资流水、社保记录等证据\n3. 如对仲裁裁决不服，可在15日内向法院起诉"
        }
    }

    analysis = analysis_map.get(case_type, analysis_map["合同纠纷"])

    return LEGAL_OPINION_TEMPLATE.format(
        date=datetime.now().strftime("%Y年%m月%d日"),
        case_type=case_type,
        client=client,
        facts=facts if facts else "委托人陈述的基本事实待补充...",
        applicable_laws=analysis["laws"],
        legal_analysis=analysis["analysis"],
        risk_assessment=analysis["risks"],
        opinion=analysis["opinion"],
        suggestions=analysis["suggestions"]
    )


def main():
    import argparse
    parser = argparse.ArgumentParser(description="法律意见书生成")
    parser.add_argument("--input", "-i", help="案情描述文件（JSON格式）")
    parser.add_argument("--case-type", default="合同纠纷", help="案由类型")
    parser.add_argument("--facts", default="", help="事实描述")
    parser.add_argument("--client", default="委托人", help="委托人名称")
    parser.add_argument("--output", "-o", help="输出文件路径")
    args = parser.parse_args()

    if args.input and os.path.exists(args.input):
        with open(args.input, "r", encoding="utf-8") as f:
            import json
            case_input = json.load(f)
    else:
        case_input = {
            "case_type": args.case_type,
            "facts": args.facts,
            "client": args.client
        }

    result = generate_opinion(case_input)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"✅ 法律意见书已保存至: {args.output}")
    else:
        print(result)


if __name__ == "__main__":
    main()
