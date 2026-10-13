"""自定义异常体系。

所有业务模块抛出的异常都应继承自 ``StoreTaskDispatcherError``，便于上层
（CLI / Skill）统一捕获并友好提示。
"""

from __future__ import annotations

from typing import Any, Optional


class StoreTaskDispatcherError(Exception):
    """所有自定义异常的基类。"""


class DwsError(StoreTaskDispatcherError):
    """dws CLI 子进程调用失败时抛出。

    Attributes:
        code: dws 返回的错误码（若返回 JSON 中含 ``code`` 字段则取之，否则为 ``None``）。
        message: 错误信息。
        stdout: dws 命令的原始 stdout（便于排错）。
        stderr: dws 命令的原始 stderr。
        args_list: 触发错误的命令参数列表。
    """

    def __init__(
        self,
        message: str,
        *,
        code: Optional[str] = None,
        stdout: str = "",
        stderr: str = "",
        args_list: Optional[list] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.stdout = stdout
        self.stderr = stderr
        self.args_list = args_list or []

    def __str__(self) -> str:  # pragma: no cover - 仅用于调试展示
        prefix = f"[{self.code}] " if self.code else ""
        return f"{prefix}{self.message}"


class InitializationError(StoreTaskDispatcherError):
    """系统初始化阶段失败（AI表格 不可访问、表创建失败等）。"""

class DuplicateBaseError(InitializationError):
    """创建 AI表格 时检测到同名 AI表格 已存在。

    Attributes:
        base_id: 已存在的 AI表格 ID。
        base_link: 已存在的 AI表格 访问链接。
    """

    def __init__(self, message: str, *, base_id: str, base_link: str) -> None:
        super().__init__(message)
        self.base_id = base_id
        self.base_link = base_link

    def __str__(self) -> str:
        return f"{self.args[0]}（base_id={self.base_id}，链接={self.base_link}）"


class SchemaValidationError(StoreTaskDispatcherError):
    """4 张表的结构校验失败（表缺失、字段缺失、类型不匹配等）。

    Attributes:
        report: 结构化的校验报告，可被上层用于自动修复或友好提示。
    """

    def __init__(self, message: str, *, report: Optional[dict] = None) -> None:
        super().__init__(message)
        self.report = report or {}


class DispatchError(StoreTaskDispatcherError):
    """派发流程异常（消息发送失败、目标门店为空等）。"""


class SyncError(StoreTaskDispatcherError):
    """业务表→实例表轮询同步异常。"""


class ConfigError(StoreTaskDispatcherError):
    """配置文件读取/写入异常。"""


__all__ = [
    "StoreTaskDispatcherError",
    "DwsError",
    "InitializationError",
    "DuplicateBaseError",
    "SchemaValidationError",
    "DispatchError",
    "SyncError",
    "ConfigError",
]
