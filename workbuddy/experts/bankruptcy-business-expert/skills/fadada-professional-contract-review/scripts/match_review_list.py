#!/usr/bin/env python3
"""
匹配审查清单脚本

根据合同ID和立场自动匹配审查清单。
环境变量:
  RICHEEAI_TOKEN    - 认证 Token（由 RicheeAI 自动注入）
  RICHEEAI_API_BASE - API 基础域名（由 RicheeAI 自动注入）
  HTTP_PROXY / HTTPS_PROXY - 代理设置（可选）
"""

import json
import os
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from proxy_utils import get_auth_token, get_api_base_url, make_json_request


def match_review_list(contract_id: str, position: str) -> dict:
    """
    自动匹配审查清单

    Args:
        contract_id: 合同ID
        position: 审查立场

    Returns:
        dict: API 响应结果
    """
    token = get_auth_token()
    if not token:
        return {"success": False, "error": "未找到认证 Token"}

    base_url = get_api_base_url()
    endpoint = "/claw/contract/matchPositionReviewListCode"
    params = {"contractId": contract_id, "position": position}
    url = f"{base_url}{endpoint}?{urllib.parse.urlencode(params)}"

    headers = {
        "richee-token": token,
        "User-Agent": "Mozilla/5.0 RicheeAI/1.0",
        "Accept": "application/json",
    }

    result = make_json_request(url, headers, method="GET", timeout=60)
    return result


def main():
    if len(sys.argv) < 3:
        print(json.dumps({
            "success": False,
            "error": "参数不足",
            "usage": "python match_review_list.py <contractId> <position>"
        }, ensure_ascii=False))
        sys.exit(1)

    contract_id = sys.argv[1].strip()
    position = sys.argv[2].strip()

    if not contract_id or not position:
        print(json.dumps({"success": False, "error": "参数不能为空"}, ensure_ascii=False))
        sys.exit(1)

    result = match_review_list(contract_id, position)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
