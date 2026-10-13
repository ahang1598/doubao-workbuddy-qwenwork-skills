"""命令注册中心（装饰器 + 自动扫描）。

提供：
- :func:`register_command(cls)` ：类装饰器，把 :class:`BaseCommand` 子类
  注册到全局 :data:`registry`，按 ``cls.name`` 排重。
- :data:`registry` ：模块级 OrderedDict，键是命令名，值是命令类实例。
- :func:`load_all_commands()` ：用 ``pkgutil`` 扫描 ``scripts.commands`` 包内
  所有模块并执行 import，触发 :func:`register_command` 完成注册。
  CLI 入口在 :func:`build_parser` 之前调一次即可。

为什么自动扫描？
- 新增命令时只需新建文件 + 加装饰器，不需要修改 ``__init__.py`` 或入口文件。
- 测试可通过 :func:`registry` 直接拿到命令类做单独构造与断言。
"""

from __future__ import annotations

import importlib
import pkgutil
from collections import OrderedDict
from typing import Dict, Type

from scripts.commands.base import BaseCommand

#: 全局命令注册表（key=命令名, value=命令实例）。
registry: "OrderedDict[str, BaseCommand]" = OrderedDict()


def register_command(cls: Type[BaseCommand]) -> Type[BaseCommand]:
    """类装饰器：把命令类注册到 :data:`registry`。

    要求被装饰的类满足：
    - 是 :class:`BaseCommand` 的子类
    - 类属性 ``name`` 非空且全局唯一

    注册时会立刻实例化（命令类应是无状态的，构造很轻量）。
    """
    if not isinstance(cls, type) or not issubclass(cls, BaseCommand):
        raise TypeError(
            f"@register_command 只能装饰 BaseCommand 的子类，收到: {cls!r}"
        )
    if not cls.name:
        raise ValueError(f"命令类 {cls.__name__} 必须设置非空的 name 属性")
    if cls.name in registry:
        existed = type(registry[cls.name]).__name__
        # 同一个类被重复 import 时（如热加载）允许覆盖；不同类同名则报错
        if existed != cls.__name__:
            raise ValueError(
                f"命令名冲突: {cls.name!r} 已被 {existed} 注册，"
                f"无法再注册 {cls.__name__}"
            )
    registry[cls.name] = cls()
    return cls


def load_all_commands() -> Dict[str, BaseCommand]:
    """扫描 ``scripts.commands`` 包内所有模块并 import，触发自动注册。

    返回当前 :data:`registry` 的快照。重复调用是幂等的。
    """
    package = importlib.import_module("scripts.commands")
    for mod_info in pkgutil.iter_modules(package.__path__):
        # 跳过基类与注册中心自身，避免循环 import
        if mod_info.name in {"base", "registry", "__init__"}:
            continue
        importlib.import_module(f"scripts.commands.{mod_info.name}")
    return dict(registry)


__all__ = ["registry", "register_command", "load_all_commands"]
