#!/usr/bin/env python3
"""
开始审查脚本

启动合同智能审查流程。
环境变量:
  RICHEEAI_TOKEN    - 认证 Token（由 RicheeAI 自动注入）
  RICHEEAI_API_BASE - API 基础域名（由 RicheeAI 自动注入）
  HTTP_PROXY / HTTPS_PROXY - 代理设置（可选）
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from proxy_utils import get_auth_token, get_api_base_url, make_json_request


def start_review(contract_id: str, contract_name: str, rule_list_code: str, position: str, strictness_level: int) -> dict:
    """
    开始审查

    Args:
        contract_id: 合同ID
        contract_name: 合同名称
        rule_list_code: 审查清单编码
        position: 审查立场
        strictness_level: 审查尺度（1-强势, 2-均势, 3-弱势）

    Returns:
        dict: API 响应结果
    """
    token = get_auth_token()
    if not token:
        return {"success": False, "error": "未找到认证 Token"}

    base_url = get_api_base_url()
    endpoint = "/claw/contract/startReview"
    url = f"{base_url}{endpoint}"

    body = {
        "contractId": contract_id,
        "contractName": contract_name,
        "llmReviewRuleListCode": rule_list_code,
        "reviewPosition": position,
        "strictnessLevel": strictness_level,
    }

    headers = {
        "richee-token": token,
        "User-Agent": "Mozilla/5.0 RicheeAI/1.0",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    result = make_json_request(url, headers, data=body, method="POST", timeout=60)

    # 添加 recordId 别名方便使用
    if result.get("success") and result.get("data"):
        result["recordId"] = result["data"]

    return result


def main():
    if len(sys.argv) < 6:
        print(json.dumps({
            "success": False,
            "error": "参数不足",
            "usage": "python start_review.py <contractId> <contractName> <ruleListCode> <position> <strictnessLevel>"
        }, ensure_ascii=False))
        sys.exit(1)

    contract_id = sys.argv[1].strip()
    contract_name = sys.argv[2].strip()
    rule_list_code = sys.argv[3].strip()
    position = sys.argv[4].strip()

    try:
        strictness_level = int(sys.argv[5].strip())
    except ValueError:
        print(json.dumps({"success": False, "error": "strictnessLevel 必须是整数(1-3)"}, ensure_ascii=False))
        sys.exit(1)

    if strictness_level not in [1, 2, 3]:
        print(json.dumps({"success": False, "error": "strictnessLevel 必须是 1(强势)、2(均势) 或 3(弱势)"}, ensure_ascii=False))
        sys.exit(1)

    result = start_review(contract_id, contract_name, rule_list_code, position, strictness_level)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
