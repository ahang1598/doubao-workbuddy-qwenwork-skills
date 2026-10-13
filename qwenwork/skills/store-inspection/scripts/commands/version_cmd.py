"""``version`` 命令：查询当前技能包版本号。"""

from __future__ import annotations

import argparse
from pathlib import Path

from scripts.commands.base import BaseCommand
from scripts.commands.registry import register_command
from scripts.utils.output import ok

# VERSION 文件位于项目根目录（与 pack.py 同级）
_VERSION_FILE = Path(__file__).resolve().parent.parent.parent / "VERSION"


@register_command
class VersionCommand(BaseCommand):
    name = "version"
    help = "查询当前技能包版本号"

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.set_defaults(func=_show_version)


def _show_version(args, ctx) -> int:
    """读取 VERSION 文件并输出当前版本号。"""
    if not _VERSION_FILE.exists():
        from scripts.utils.output import warn
        warn("VERSION 文件不存在，版本号未知")
        return 1
    version = _VERSION_FILE.read_text(encoding="utf-8").strip()
    ok(f"当前版本: v{version}")
    return 0
