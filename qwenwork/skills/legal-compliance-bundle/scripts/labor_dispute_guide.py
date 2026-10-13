#!/usr/bin/env python3
"""
技能ID: labor-dispute-guide
技能名称: 劳动争议指南
模块: 劳动合规
功能: 劳动仲裁/诉讼流程指引，给出维权路径和时限
"""

import json
from typing import Dict, List, Any

DISPUTE_TYPES = {
    "工资拖欠": {
        "path": ["协商", "劳动监察投诉", "劳动仲裁", "诉讼"],
        "limitation": "离职后1年内",
        "documents": ["劳动合同", "工资条/银行流水", "考勤记录", "催款记录"],
        "tips": "保留工资条和银行流水作为核心证据",
    },
    "违法解除": {
        "path": ["协商", "劳动仲裁（要求恢复劳动关系或2N赔偿）", "诉讼"],
        "limitation": "知道被解除之日起1年内",
        "documents": ["解除通知书", "劳动合同", "工资流水", "工作记录"],
        "tips": "公司需证明解除合法性，举证责任在公司",
    },
    "未签合同": {
        "path": ["协商", "劳动仲裁（双倍工资差额）", "诉讼"],
        "limitation": "入职满1年后的1年内",
        "documents": ["入职记录", "工资流水", "考勤", "工牌/工服照片"],
        "tips": "未签书面合同可主张最多11个月双倍工资",
    },
    "社保未缴": {
        "path": ["社保稽核投诉", "劳动仲裁"],
        "limitation": "离职后1年内",
        "documents": ["劳动合同", "工资流水", "社保查询记录"],
        "tips": "社保问题优先向社保局投诉，仲裁时效争议较多",
    },
    "工伤认定": {
        "path": ["工伤认定申请（30日内单位/1年内个人）", "劳动能力鉴定", "工伤赔偿协商/仲裁"],
        "limitation": "事故发生后1年内申请工伤认定",
        "documents": ["事故报告", "医疗诊断", "劳动合同", "证人证言"],
        "tips": "单位30日内不申请的，个人1年内可直接申请",
    },
    "竞业限制": {
        "path": ["协商", "劳动仲裁", "诉讼"],
        "limitation": "知道或应当知道权利被侵害之日起1年内",
        "documents": ["竞业限制协议", "补偿金支付记录", "新工作证明"],
        "tips": "公司未支付3个月补偿金的，可请求解除竞业限制",
    },
}


def skill_function(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """劳动争议维权指引"""
    try:
        dispute_type = input_data.get("dispute_type", "")
        details = input_data.get("details", "")

        if dispute_type not in DISPUTE_TYPES:
            return {
                "status": "success",
                "result": {
                    "提示": f"未找到'{dispute_type}'的专项指引",
                    "可选类型": list(DISPUTE_TYPES.keys()),
                    "通用流程": [
                        "1. 收集证据（合同、工资条、考勤、聊天记录）",
                        "2. 与公司协商",
                        "3. 向当地劳动监察大队投诉",
                        "4. 申请劳动仲裁（免费，60天内结案）",
                        "5. 对仲裁不服可向法院起诉",
                    ],
                },
            }

        info = DISPUTE_TYPES[dispute_type]

        return {
            "status": "success",
            "result": {
                "争议类型": dispute_type,
                "维权路径": " → ".join(info["path"]),
                "仲裁时效": info["limitation"],
                "所需材料": info["documents"],
                "实操建议": info["tips"],
                "仲裁流程": [
                    "1. 准备仲裁申请书+证据材料",
                    "2. 到用人单位所在地或合同履行地仲裁委立案",
                    "3. 仲裁委5日内决定是否受理",
                    "4. 受理后45日内结案（复杂可延长至60日）",
                    "5. 对裁决不服15日内可向法院起诉",
                ],
                "费用": "劳动仲裁免费，诉讼费10元",
            },
            "法律依据": "《劳动争议调解仲裁法》《劳动合同法》",
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    test_input = {"dispute_type": "违法解除", "details": "公司口头通知被裁，无书面通知"}
    result = skill_function(test_input)
    print(json.dumps(result, ensure_ascii=False, indent=2))
