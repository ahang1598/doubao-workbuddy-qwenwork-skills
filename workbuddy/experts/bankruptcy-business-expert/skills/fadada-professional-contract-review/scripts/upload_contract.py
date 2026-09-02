#!/usr/bin/env python3
"""
合同上传脚本

上传本地合同文件到服务端进行解析。
环境变量:
  RICHEEAI_TOKEN    - 认证 Token（由 RicheeAI 自动注入）
  RICHEEAI_API_BASE - API 基础域名（由 RicheeAI 自动注入）
  HTTP_PROXY / HTTPS_PROXY - 代理设置（可选）
"""

import json
import os
import sys

# 添加脚本目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from proxy_utils import get_auth_token, get_api_base_url, make_request


def upload_contract(file_path: str) -> dict:
    """
    上传合同文件

    Args:
        file_path: 合同文件路径

    Returns:
        dict: API 响应结果
    """
    token = get_auth_token()
    if not token:
        return {"success": False, "error": "未找到认证 Token"}

    base_url = get_api_base_url()
    endpoint = "/claw/contract/uploadContract"
    url = f"{base_url}{endpoint}"

    # 读取文件内容
    try:
        with open(file_path, "rb") as f:
            file_content = f.read()
    except FileNotFoundError:
        return {"success": False, "error": f"文件不存在: {file_path}"}
    except Exception as e:
        return {"success": False, "error": f"读取文件失败: {str(e)}"}

    file_name = os.path.basename(file_path)

    # 构造 multipart/form-data 请求体
    boundary = "----FormBoundary7MA4YWxkTrZu0gW"
    body_parts = []

    body_parts.append(
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{file_name}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n"
    )
    body_parts.append(file_content)
    body_parts.append(b"\r\n")
    body_parts.append(f"--{boundary}--\r\n")

    merged = []
    for part in body_parts:
        if isinstance(part, str):
            merged.append(part.encode("utf-8"))
        else:
            merged.append(part)
    body = b"".join(merged)

    headers = {
        "richee-token": token,
        "User-Agent": "Mozilla/5.0 RicheeAI/1.0",
        "Accept": "application/json",
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    }

    result = make_request(url, headers, body, "POST", timeout=300)

    # 如果返回的是错误字典，直接返回
    if isinstance(result, dict):
        return result

    # result 是 bytes，解析 JSON
    try:
        parsed = json.loads(result.decode("utf-8"))
        # 优先使用 success 字段判断，其次检查 code
        is_success = parsed.get("success") or parsed.get("callSuccess")
        code = parsed.get("code")
        if not is_success:
            is_success = code in (200, "200", "000000", 0, "0")

        if is_success:
            return {"success": True, "data": parsed.get("data")}
        else:
            return {"success": False, "error": parsed.get("message") or parsed.get("msg", "上传失败"), "code": code}
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"JSON 解析错误: {str(e)}"}


def main():
    if len(sys.argv) < 2:
        print(json.dumps({
            "success": False,
            "error": "请提供合同文件路径",
            "usage": "python upload_contract.py <文件路径>"
        }, ensure_ascii=False))
        sys.exit(1)

    file_path = sys.argv[1].strip()
    if not file_path:
        print(json.dumps({"success": False, "error": "文件路径不能为空"}, ensure_ascii=False))
        sys.exit(1)

    result = upload_contract(file_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
