#!/usr/bin/env python3
"""
1688-product-manage CLI — 统一命令入口

用法：
    python3 cli.py <command> [options]
    python3 cli.py --help          查看所有可用命令

命令：
    post_process_action  处理 MCP 返回数据并保留商品运营原脚本后处理逻辑

输出 JSON：{"success": bool, "markdown": str, "data": {...}}
"""
from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = str(SKILL_DIR / "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from _output import make_output, print_error, print_output


def _discover_capabilities() -> dict[str, str]:
    """扫描 capabilities/*/cmd.py，自动注册命令。返回 {cmd_name: module_path}"""
    commands: dict[str, str] = {}
    enabled_commands = {"post_process_action"}
    caps_dir = os.path.join(SCRIPTS_DIR, "capabilities")
    if not os.path.isdir(caps_dir):
        return commands
    for name in sorted(os.listdir(caps_dir)):
        if name not in enabled_commands:
            continue
        cmd_path = os.path.join(caps_dir, name, "cmd.py")
        if not os.path.isfile(cmd_path):
            continue
        module_path = f"capabilities.{name}.cmd"
        try:
            mod = importlib.import_module(module_path)
            cmd_name = getattr(mod, "COMMAND_NAME", name)
            commands[cmd_name] = module_path
        except Exception:
            pass
    return commands


def _usage(commands: dict) -> None:
    lines = ["**1688-product-manage 用法**\n", "```"]
    for name in sorted(commands):
        handler = commands[name]
        if isinstance(handler, tuple):
            desc = handler[1]
        else:
            try:
                mod = importlib.import_module(handler)
                desc = getattr(mod, "COMMAND_DESC", "")
            except Exception:
                desc = ""
        lines.append(f"python3 cli.py {name:<20} {desc}")
    lines.append("```")
    print_output(make_output(success=True, markdown="\n".join(lines)))


OAUTH_COMMANDS: dict[str, tuple] = {}


def main() -> int:
    # 自动发现 capability 目录命令（module_path 字符串）
    cap_commands = _discover_capabilities()

    # 合并：capability 命令 + OAuth 命令（本技能不再暴露 OAuth/AK 命令）
    all_commands: dict = {**cap_commands, **OAUTH_COMMANDS}

    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        _usage(all_commands)
        return 1

    command = sys.argv[1]
    cmd_args = sys.argv[2:]

    handler = all_commands.get(command)
    if not handler:
        print_output(make_output(
            success=False,
            error_code="UNKNOWN_COMMAND",
            markdown=f"未知命令: `{command}`\n\n可用命令: {', '.join(sorted(all_commands.keys()))}",
        ))
        return 1

    try:
        if isinstance(handler, tuple):
            # OAuth 命令：直接调用函数
            result = handler[0](cmd_args)
        else:
            # capability 模块：重置 sys.argv 后调用 module.main()
            sys.argv = [f"cli.py {command}"] + cmd_args
            mod = importlib.import_module(handler)
            result = mod.main()
    except Exception as e:
        print_error(e)
        return 1

    try:
        from _tracker import report_skill_usage
        report_skill_usage()
    except Exception:
        pass

    return result if isinstance(result, int) else 0


if __name__ == "__main__":
    sys.exit(main())
