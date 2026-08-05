#!/usr/bin/env python3
"""
统一异常体系
"""


class SkillError(Exception):
    def __init__(self, message: str, code: int = 500, data: dict = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.data = data or {}


class AuthError(SkillError):
    """MCP/OAuth 鉴权无效或未授权 (401)"""
    def __init__(self, message: str = "MCP 连接器授权无效或已过期"):
        super().__init__(message, code=401)


class ParamError(SkillError):
    """请求参数不合法 (400)"""
    def __init__(self, message: str = "请求参数不合法"):
        super().__init__(message, code=400)


class RateLimitError(SkillError):
    """请求被限流 (429)"""
    def __init__(self, message: str = "请求被限流，请稍后重试"):
        super().__init__(message, code=429)


class ServiceError(SkillError):
    """服务端异常 / 网络异常 (500)"""
    def __init__(self, message: str = "服务异常，请稍后重试"):
        super().__init__(message, code=500)


class GatewayAuthError(SkillError):
    """
    MCP 网关返回的 OAuth 相关错误。

    Agent 识别后应引导用户检查 ali1688-buyer 连接器授权。
    """
    def __init__(self, error_code: str, message: str, required_scope: str = ""):
        super().__init__(message, code=403)
        self.error_code = error_code
        self.required_scope = required_scope
