#!/usr/bin/env python3
"""
HTTP 请求工具模块

提供 HTTP 请求功能，支持代理环境。
"""

import json
import os
import ssl
import urllib.request
from urllib.error import HTTPError, URLError


def get_auth_token():
    """从环境变量获取认证 Token"""
    token = os.environ.get("RICHEEAI_TOKEN")
    if not token:
        print(json.dumps({
            "success": False,
            "error": "未找到认证 Token。请确保在 RicheeAI cowork 会话中运行此脚本。",
            "hint": "RICHEEAI_TOKEN 环境变量未设置"
        }, ensure_ascii=False))
        return None
    return token


def get_api_base_url():
    """从环境变量获取 API 基础域名"""
    return os.environ.get("RICHEEAI_API_BASE", "https://claw.richee.cn/claw-api")


def make_request(url, headers, data=None, method="GET", timeout=60, return_response=False):
    """
    发送 HTTP 请求

    Args:
        url: 请求URL
        headers: 请求头
        data: 请求体（bytes）
        method: 请求方法
        timeout: 超时时间（秒）
        return_response: 是否返回响应对象（用于获取响应头）

    Returns:
        bytes 或 dict 或 (bytes, response): 成功返回bytes，失败返回错误dict
    """
    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    # 创建 SSL 上下文
    ssl_context = ssl.create_default_context()

    try:
        https_handler = urllib.request.HTTPSHandler(context=ssl_context)
        opener = urllib.request.build_opener(https_handler)
        with opener.open(req, timeout=timeout) as response:
            content = response.read()
            if return_response:
                return (content, response)
            return content

    except HTTPError as e:
        error_body = e.read().decode("utf-8") if hasattr(e, "read") else str(e)
        return {
            "success": False,
            "error": f"HTTP 错误 {e.code}: {error_body}",
            "error_type": "http_error",
            "status_code": e.code
        }

    except URLError as e:
        error_reason = str(e.reason)
        return {
            "success": False,
            "error": f"网络请求失败: {error_reason}",
            "error_type": "network_error"
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"未知错误: {str(e)}",
            "error_type": "unknown_error"
        }


def make_json_request(url, headers, data=None, method="GET", timeout=60):
    """
    发送 HTTP 请求并解析 JSON 响应

    Args:
        url: 请求URL
        headers: 请求头
        data: 请求体（dict，会自动转为JSON）
        method: 请求方法
        timeout: 超时时间（秒）

    Returns:
        dict: {"success": True/False, "data": ..., "error": ...}
    """
    if data is not None and isinstance(data, dict):
        data = json.dumps(data).encode("utf-8")

    result = make_request(url, headers, data, method, timeout)

    # 如果返回的是错误字典，直接返回
    if isinstance(result, dict):
        return result

    # result 是 bytes，解析 JSON
    try:
        parsed = json.loads(result.decode("utf-8"))

        # 统一处理 API 响应格式
        # API 返回格式: {"code": "000000", "message": "...", "success": true, "data": {...}, "callSuccess": true}
        is_success = parsed.get("success") or parsed.get("callSuccess")
        code = parsed.get("code")
        if not is_success:
            is_success = code in (200, "200", "000000", 0, "0")

        if is_success:
            return {"success": True, "data": parsed.get("data")}
        else:
            return {
                "success": False,
                "error": parsed.get("message") or parsed.get("msg", "请求失败"),
                "code": code
            }
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "error": f"JSON 解析错误: {str(e)}",
            "error_type": "json_error"
        }
