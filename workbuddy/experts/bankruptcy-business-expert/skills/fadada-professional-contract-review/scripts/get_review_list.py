#!/usr/bin/env python3
"""
获取预制审查清单脚本

获取系统预制的所有审查清单列表。
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


def get_review_list() -> dict:
    """获取预制审查清单列表"""
    token = get_auth_token()
    if not token:
        return {"success": False, "error": "未找到认证 Token"}

    base_url = get_api_base_url()
    endpoint = "/claw/contract/reviewList"
    url = f"{base_url}{endpoint}"

    headers = {
        "richee-token": token,
        "User-Agent": "Mozilla/5.0 RicheeAI/1.0",
        "Accept": "application/json",
    }

    result = make_json_request(url, headers, method="GET", timeout=60)
    return result


def main():
    result = get_review_list()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
