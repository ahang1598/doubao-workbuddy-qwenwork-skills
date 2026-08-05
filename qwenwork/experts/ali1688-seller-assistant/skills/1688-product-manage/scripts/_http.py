#!/usr/bin/env python3
"""
通用 HTTP 客户端

职责：签名注入、自动重试、统一错误映射。
所有 capability 的 service 层通过 api_post() 调用 1688 API。

仅使用 Python 标准库（urllib），无第三方依赖。
"""

import json
import re
import socket
import time
import logging
from functools import wraps
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from _auth import build_auth_headers, get_user_id
from _const import BASE_URL, RETRY_DELAY_BASE, RETRY_MAX, HTTP_TIMEOUT, _GATEWAY_AUTH_ERROR_CODES, LOG_FILE
from _errors import AuthError, ParamError, RateLimitError, ServiceError, GatewayAuthError

LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8")],
    force=True,
)
logger = logging.getLogger('1688_http')


def _with_retry(max_retries: int = RETRY_MAX):
    """仅重试网络连接/超时异常，其余异常直接传播"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (ConnectionError, socket.timeout, OSError) as e:
                    last_exc = e
                    delay = min(RETRY_DELAY_BASE * (2 ** attempt), 10)
                    logger.warning("网络异常(尝试%d/%d): %s, %ds后重试",
                                   attempt + 1, max_retries, e, delay)
                    if attempt < max_retries - 1:
                        time.sleep(delay)
            raise ServiceError(f"网络异常，已重试{max_retries}次: {last_exc}")
        return wrapper
    return decorator


def _handle_http_error(e: HTTPError):
    status = e.code
    if status == 401:
        raise AuthError("签名无效或已过期（401）")
    if status == 429:
        raise RateLimitError("请求被限流（429），请稍后重试")
    if status == 400:
        raise ParamError("请求参数不合法（400）")
    raise ServiceError(f"HTTP 错误 {status}")


def _handle_biz_error(result: dict):
    """业务错误（HTTP 200 但 success=false）→ SkillError"""
    msg_code = str(result.get("msgCode") or "")
    msg_info = result.get("msgInfo")

    # 检查 1688 网关 Token 相关错误码（Agent 可自动恢复）
    if msg_code in _GATEWAY_AUTH_ERROR_CODES:
        required_scope = result.get("requiredScope", "")
        raise GatewayAuthError(
            error_code=msg_code,
            message=msg_info or f"授权错误：{msg_code}",
            required_scope=required_scope,
        )

    # 标准 HTTP 状态码映射
    code_match = re.search(r"\b(400|401|429|500)\b", msg_code)
    normalized = code_match.group(1) if code_match else ""

    if normalized == "401":
        raise AuthError("签名无效（401）")
    if normalized == "429":
        raise RateLimitError("请求被限流（429）")
    if normalized == "400":
        raise ParamError("请求参数不合法（400）")
    if normalized == "500":
        raise ServiceError("服务异常（500），请稍后重试")

    detail = msg_info or msg_code or "未知业务错误"
    raise ServiceError(str(detail))


@_with_retry()
def api_post(path: str, body: dict = None, timeout: int = None) -> dict:
    """
    POST 请求 1688 Skill 网关（自动签名 + userId 注入 + 重试 + 错误映射）

    Raises:
        AuthError / ParamError / RateLimitError / ServiceError / GatewayAuthError
    """
    url = f"{BASE_URL}{path}"
    body = body or {}

    # 从 AK 解析 userId 并注入请求体
    body["userId"] = get_user_id()

    body_str = json.dumps(body, ensure_ascii=False)

    headers = build_auth_headers("POST", path, body_str)
    if not headers:
        raise AuthError("AK 未配置")

    data = body_str.encode("utf-8")

    req = Request(url, data=data, headers=headers, method="POST")
    try:
        with urlopen(req, timeout=timeout or HTTP_TIMEOUT) as resp:
            resp_body = resp.read().decode("utf-8")
    except HTTPError as e:
        _handle_http_error(e)
    except (URLError, socket.timeout) as e:
        # URLError 包含连接失败、DNS 解析失败等
        raise ConnectionError(str(e)) from e

    result = json.loads(resp_body)
    if result.get("success") is False:
        _handle_biz_error(result)

    data = result.get("data", {})
    if not isinstance(data, dict):
        raise ServiceError("API 返回结构异常（data 不是对象）")

    return data


@_with_retry()
def api_post_raw(path: str, body: dict = None, timeout: int = None) -> dict:
    """
    POST 请求 1688 Skill 网关（自动签名 + userId 注入 + 重试 + HTTP错误映射）

    与 api_post() 的区别：返回完整的 JSON 响应体，不做 success/data 字段提取。
    用于返回格式非标准的 API（如 __success__/model/dataJson 等）。

    Raises:
        AuthError / ParamError / RateLimitError / ServiceError
    """
    url = f"{BASE_URL}{path}"
    body = body or {}

    # 从 AK 解析 userId 并注入请求体
    body["userId"] = get_user_id()

    body_str = json.dumps(body, ensure_ascii=False)

    headers = build_auth_headers("POST", path, body_str)
    if not headers:
        raise AuthError("AK 未配置")

    data = body_str.encode("utf-8")

    req = Request(url, data=data, headers=headers, method="POST")
    try:
        with urlopen(req, timeout=timeout or HTTP_TIMEOUT) as resp:
            resp_body = resp.read().decode("utf-8")
    except HTTPError as e:
        _handle_http_error(e)
    except (URLError, socket.timeout) as e:
        raise ConnectionError(str(e)) from e

    return json.loads(resp_body)
