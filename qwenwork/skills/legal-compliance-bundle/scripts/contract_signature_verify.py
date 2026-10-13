#!/usr/bin/env python3
"""技能ID: contract-signature-verify | 合同签署要素验证"""
import json, re
from typing import Dict, Any

def skill_function(input_data):
    text = input_data.get("contract_text", "")
    if not text:
        return {"status": "error", "message": "请提供合同文本"}
    checks = {
        "甲方签章": bool(re.search(r"甲方.{0,20}(签章|签字|盖章)", text)),
        "乙方签章": bool(re.search(r"乙方.{0,20}(签章|签字|盖章)", text)),
        "签订日期": bool(re.search(r"(签订|签署).{0,5}日期.{0,10}\d{4}", text)),
        "合同编号": bool(re.search(r"(编号|合同号).{0,10}[A-Z0-9]", text, re.IGNORECASE)),
        "甲方名称": bool(re.search(r"甲方.{0,5}(名称|：).{2,30}", text)),
        "乙方名称": bool(re.search(r"乙方.{0,5}(名称|：).{2,30}", text)),
        "份数说明": bool(re.search(r"(一式|份数|各执)", text)),
    }
    passed = sum(1 for v in checks.values() if v)
    missing = [k for k, v in checks.items() if not v]
    return {"status": "success", "result": {"验证结果": checks, "通过率": f"{passed}/{len(checks)}", "缺失要素": missing}}

if __name__ == "__main__":
    test = "甲方名称：北京科技。乙方名称：上海贸易。编号：HT-2025-001。签订日期：2025年3月1日。甲方签章。乙方签章。一式两份。"
    print(json.dumps(skill_function({"contract_text": test}), ensure_ascii=False, indent=2))
