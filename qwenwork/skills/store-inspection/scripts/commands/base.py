"""命令基类（模板方法模式）。

每条 CLI 命令对应一个 :class:`BaseCommand` 子类，定义：
- ``name``      ：顶级命令名（如 ``init`` / ``store``）
- ``help``      ：argparse 顶级 help
- ``configure`` ：往传入的 sub-parser 上注册子命令 + 参数 + ``set_defaults(func=...)``

CLI 入口 ``scripts/cli.py`` 只关心三件事：
1. 通过 :data:`scripts.commands.registry` 拿到所有已注册命令。
2. 按 ``name`` 给主 parser 添加 sub-parser，再调用每个命令的 ``configure``。
3. 解析参数后用 ``args.func(args, ctx)`` 派发到具体处理函数。

为什么不直接用 ``argparse`` 的 ``add_subparsers`` 自由拼装？
- 把每条命令封装成类，可以保证：参数注册逻辑 + 处理函数 + help 文案在同一文件，便于维护。
- 装饰器 + 自动扫描让新增命令时只需新增文件，不需要改入口。
"""

from __future__ import annotations

import argparse
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - 仅为类型注解，避免循环 import
    from scripts.app import AppContext


class BaseCommand:
    """所有顶级命令的基类（模板方法模式）。

    子类必须覆盖：
    - 类属性 :attr:`name`   ：顶级命令名
    - 类属性 :attr:`help`   ：顶级 help 描述
    - 实例方法 :meth:`configure(parser)`：往传入的 parser 上挂子命令 / 参数 /
      ``set_defaults(func=callable(args, ctx))``
    """

    #: 顶级命令名（如 ``init``、``store``、``dispatch``）
    name: str = ""
    #: 顶级 help 描述
    help: str = ""

    def configure(self, parser: argparse.ArgumentParser) -> None:
        """在 ``parser`` 上注册本命令的子命令、参数与 ``func`` 默认值。

        约定：每个最终可执行的子命令都需要 ``set_defaults(func=...)``，
        ``func`` 的签名必须为 ``(args: argparse.Namespace, ctx: AppContext) -> int``。
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # 工具：让子命令处理函数共享一致的签名声明
    # ------------------------------------------------------------------

    @staticmethod
    def add_yes_flag(parser: argparse.ArgumentParser, help_text: str) -> None:
        """给删除/重置类高危子命令统一加 ``--yes`` 二次确认开关。"""
        parser.add_argument("--yes", action="store_true", help=help_text)


__all__ = ["BaseCommand"]
