#!/usr/bin/env python3
"""Shared exception types for local post-processing scripts."""

from __future__ import annotations


class SkillError(Exception):
    def __init__(self, message: str, code: int = 500, data: dict | None = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.data = data or {}


class AuthError(SkillError):
    def __init__(self, message: str = "认证失败"):
        super().__init__(message, code=401)


class ParamError(SkillError):
    def __init__(self, message: str = "请求参数不合法"):
        super().__init__(message, code=400)


class RateLimitError(SkillError):
    def __init__(self, message: str = "请求被限流，请稍后重试"):
        super().__init__(message, code=429)


class ServiceError(SkillError):
    def __init__(self, message: str = "服务异常，请稍后重试"):
        super().__init__(message, code=500)


class GatewayAuthError(SkillError):
    def __init__(self, error_code: str = "", message: str = "网关授权错误", required_scope: str = ""):
        super().__init__(message, code=403)
        self.error_code = error_code
        self.required_scope = required_scope
