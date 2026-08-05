#!/usr/bin/env python3
"""
统一输出工具

所有 cmd.py 通过此模块输出 JSON，保证格式一致。
"""

import json
import os
import sys

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')))
from scripts._sys._errors import SkillError, AuthError, GatewayAuthError

def make_output(success: bool, markdown: str = "", data: dict = None,
                error_code: str = "", required_scope: str = "") -> dict:
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
    return result

def print_output(success: bool, markdown: str = "", data: dict = None):
    """打印标准 JSON 输出"""
    print(json.dumps(make_output(success, markdown, data), ensure_ascii=False, indent=2))

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
    print(json.dumps(output, ensure_ascii=False, indent=2))

def fmt_rate(v) -> str:
    """小数转百分比，如 0.857 → 85.7%；无值返回 -"""
    if v is None:
        return "-"
    try:
        f = float(v)
        return f"{f * 100:.1f}%" if f <= 1.0 else f"{f:.1f}%"
    except (TypeError, ValueError):
        return str(v)
