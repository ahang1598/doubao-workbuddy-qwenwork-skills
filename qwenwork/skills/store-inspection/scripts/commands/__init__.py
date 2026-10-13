"""命令层：CLI 子命令的实现。

设计目标：
- 命令注册采用 **混合模式**：所有命令继承统一的 :class:`BaseCommand` 基类，
  并通过 :func:`@register_command` 装饰器自动注册到全局 :data:`registry`。
- :func:`load_all_commands` 在 CLI 启动时被 ``cli.py`` 调用，扫描本包内所有
  模块完成自动注册（无需手动维护 import 列表）。

依赖方向：
- 上游：scripts/cli.py
- 下游：scripts/app.py（通过 :class:`AppContext` 访问服务）
        + scripts/utils/output（统一的 print 助手）
"""

from scripts.commands.base import BaseCommand
from scripts.commands.registry import (
    load_all_commands,
    register_command,
    registry,
)

__all__ = [
    "BaseCommand",
    "register_command",
    "registry",
    "load_all_commands",
]
