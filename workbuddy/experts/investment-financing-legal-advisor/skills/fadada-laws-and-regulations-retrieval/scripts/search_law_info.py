#!/usr/bin/env python3
"""通过 RicheeAI 内部 API 执行法律法规检索。"""

import json
import os
import ssl
import sys
import urllib.request
from urllib.error import HTTPError, URLError


ENDPOINT = "/claw/searchTool/lawInfo"
DEFAULT_API_BASE = "https://claw.richee.cn/claw-api"


class RequestValidationError(ValueError):
    """命令行请求体不符合新版法律检索契约。"""


def get_proxy_handler():
    """仅使用显式代理环境变量，避免读取失效的系统代理。"""
    proxies = {}
    http_proxy = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
    https_proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    if http_proxy:
        proxies["http"] = http_proxy
    if https_proxy:
        proxies["https"] = https_proxy
    return urllib.request.build_opener(urllib.request.ProxyHandler(proxies))


def get_auth_token():
    token = os.environ.get("RICHEEAI_TOKEN")
    if not token:
        raise RequestValidationError(
            "未找到认证 Token。请确保在 RicheeAI cowork 会话中运行此脚本。"
        )
    return token


def get_api_base_url():
    return os.environ.get("RICHEEAI_API_BASE", DEFAULT_API_BASE).rstrip("/")


def parse_request(raw_request):
    """解析并轻量校验命令行传入的 JSON 请求体。"""
    try:
        payload = json.loads(raw_request)
    except json.JSONDecodeError as exc:
        raise RequestValidationError(f"请求参数不是有效 JSON: {exc.msg}") from exc

    if not isinstance(payload, dict):
        raise RequestValidationError("请求参数必须是 JSON 对象")

    scene = payload.get("retrievalScene")
    if not isinstance(scene, str) or not scene.strip():
        raise RequestValidationError("retrievalScene 必须是非空字符串")

    if "searchContent" in payload and not isinstance(payload["searchContent"], str):
        raise RequestValidationError("searchContent 必须是字符串")

    if "structuredFields" in payload and not isinstance(payload["structuredFields"], dict):
        raise RequestValidationError("structuredFields 必须是 JSON 对象")

    payload["retrievalScene"] = scene.strip()
    return payload


def build_http_request(payload, token, base_url):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "richee-token": token,
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 "
            "Safari/537.36 RicheeAI/1.0"
        ),
        "Accept": "application/json",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Content-Type": "application/json; charset=utf-8",
    }
    return urllib.request.Request(
        f"{base_url.rstrip('/')}{ENDPOINT}",
        data=body,
        headers=headers,
        method="POST",
    )


def search_law_info(payload):
    """发送新版 JSON Body 请求并返回可序列化结果。"""
    token = get_auth_token()
    request = build_http_request(payload, token, get_api_base_url())
    opener = get_proxy_handler()
    opener.add_handler(urllib.request.HTTPSHandler(context=ssl.create_default_context()))

    try:
        with opener.open(request, timeout=180) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        error_body = exc.read().decode("utf-8") if hasattr(exc, "read") else str(exc)
        return {
            "success": False,
            "error": f"HTTP 错误 {exc.code}: {error_body}",
            "request": payload,
        }
    except URLError as exc:
        return {
            "success": False,
            "error": f"请求失败: {exc.reason}",
            "request": payload,
        }
    except json.JSONDecodeError as exc:
        return {
            "success": False,
            "error": f"响应 JSON 解析错误: {exc.msg}",
            "request": payload,
        }
    except Exception as exc:
        return {
            "success": False,
            "error": f"未知错误: {exc}",
            "request": payload,
        }


def print_error(message):
    print(json.dumps({"success": False, "error": message}, ensure_ascii=False))


def main():
    if len(sys.argv) != 2:
        print_error(
            '请提供一个 JSON 请求对象。用法: python3 search_law_info.py '
            "'{\"retrievalScene\":\"law_semantic\",\"searchContent\":\"检索内容\"}'"
        )
        return 1

    try:
        payload = parse_request(sys.argv[1])
        result = search_law_info(payload)
    except RequestValidationError as exc:
        print_error(str(exc))
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
