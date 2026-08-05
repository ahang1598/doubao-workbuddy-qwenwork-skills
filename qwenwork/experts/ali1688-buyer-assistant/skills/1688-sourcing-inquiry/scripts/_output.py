#!/usr/bin/env python3
"""
统一输出工具
"""

import json

from _errors import SkillError, AuthError, GatewayAuthError


def make_output(success: bool, markdown: str = "", data: dict = None,
                error_code: str = "", required_scope: str = "",
                current_scope: str = "") -> dict:
    """构建标准输出字典（仅包含非空字段）"""
    result = {"success": success}
    if markdown:
        result["markdown"] = markdown
    if data is not None:
        result["data"] = data
    if error_code:
        result["error_code"] = error_code
    if required_scope:
        result["required_scope"] = required_scope
    if current_scope:
        result["current_scope"] = current_scope
    return result


def print_output(output: dict):
    """打印标准 JSON 输出"""
    print(json.dumps(output, ensure_ascii=False, indent=2))


def print_error(e: Exception, default_data: dict = None):
    """将异常转为标准错误输出并打印"""
    if isinstance(e, GatewayAuthError):
        output = make_output(
            success=False,
            error_code=e.error_code,
            markdown=e.message,
            required_scope=e.required_scope,
        )
    elif isinstance(e, AuthError):
        output = make_output(
            success=False,
            markdown=f"❌ {e.message}\n\n请检查 `ali1688-buyer` MCP 连接器是否已完成 OAuth 授权；如授权过期，请在连接器设置中重新授权。",
            data=default_data,
        )
    elif isinstance(e, SkillError):
        output = make_output(success=False, markdown=f"❌ {e.message}", data=default_data)
    elif isinstance(e, ValueError):
        output = make_output(success=False, markdown=f"❌ 参数错误：{e}", data=default_data)
    else:
        output = make_output(success=False, markdown=f"❌ 操作失败：{e}", data=default_data)
    print_output(output)
