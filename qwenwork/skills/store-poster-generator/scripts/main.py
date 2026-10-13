#!/usr/bin/env python3
"""
技能查找脚本

在 AGENT_WORK_ROOT/.skills/*/SKILL.md 中按名称查找技能是否存在。

使用方式：
  uv run python cli --skillname <技能名称>

参数说明：
  uv run python cli.py skill-exists --skillname store-poster-generator
"""

import argparse
import importlib
import os
import pkgutil
import sys
from pathlib import Path


class HelpOnErrorParser(argparse.ArgumentParser):
    """参数解析失败时打印帮助信息而不是直接报错退出。"""

    def error(self, message):
        sys.stderr.write(f"错误: {message}\n\n")
        self.print_help(sys.stderr)
        sys.exit(2)


def discover_commands(subparsers) -> None:
    """自动扫描 commands/ 目录，导入每个模块并调用其 register() 注册子命令。

    每个 command 模块可通过模块级变量 ``DISABLED`` 控制是否注册：
    - 不设置或 ``DISABLED = False``（默认）：正常注册，-h 时展示
    - ``DISABLED = True``：跳过注册，-h 时隐藏
    """
    commands_package_path = Path(__file__).parent / "commands"

    for module_info in pkgutil.iter_modules([str(commands_package_path)]):
        try:
            module = importlib.import_module(f"commands.{module_info.name}")
        except Exception:
            continue
        if getattr(module, "DISABLED", False):
            continue
        if hasattr(module, "register"):
            module.register(subparsers)


def _check_workdir_env() -> None:
    """守卫方法：确保存在可用的用户工作目录变量。

    优先顺序：QODERWORK_USER_WORKDIR > QODER_WORKSPACE_DIR > WUKONG_USER_WORKDIR。
    若三者皆无，则用当前工作目录兜底（并写回 QODERWORK_USER_WORKDIR），不再阻断执行。
    """
    for key in ("QODERWORK_USER_WORKDIR", "QODER_WORKSPACE_DIR", "WUKONG_USER_WORKDIR"):
        if os.environ.get(key):
            return
    fallback = os.getcwd()
    os.environ["QODERWORK_USER_WORKDIR"] = fallback
    sys.stderr.write(
        f"[skill_context] 未检测到 QODERWORK_USER_WORKDIR/QODER_WORKSPACE_DIR，回退使用当前工作目录：{fallback}\n"
    )

def _check_user_agreement() -> None:
    pass
#     if os.environ.get("READ_USER_AGREEMENT") != "1":
#         sys.stdout.write("""\
# 错误原因: 
# 1. 当你遇到此报错时, 说明你用的 LLM 能力比较差, 未能理解或记住主技能 SKILL.md的说明. 这并不是技能或服务异常, 所以禁止 fallback 到兜底技能.
# 错误处理办法:
# 1. 我不会告诉你直接的处理办法, 请先阅读主技能的 SKILL.md, 按"执行流程"要求执行, 自然会知道处理方法.
# 2. 禁止阅读 scripts 中的文件绕过此异常.
# """)
#         sys.exit(1)

def main():
    _check_workdir_env()
    _check_user_agreement()

    parser = HelpOnErrorParser(description="Skill CLI 工具集")
    subparsers = parser.add_subparsers(
        dest="command", help="可用命令", parser_class=HelpOnErrorParser,
    )

    discover_commands(subparsers)

    args = parser.parse_args()
    if not args.command:
        parser.print_help(sys.stderr)
        sys.exit(2)

    args.handler(args)


if __name__ == "__main__":
    main()
