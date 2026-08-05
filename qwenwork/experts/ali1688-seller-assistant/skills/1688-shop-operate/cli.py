#!/usr/bin/env python3
"""1688-shop-operate CLI for MCP result post-processing."""

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
    commands: dict[str, str] = {}
    enabled_commands = {"post_process_report"}
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


def _usage(commands: dict[str, str]) -> None:
    lines = ["**1688-shop-operate 用法**\n", "```"]
    for name in sorted(commands):
        try:
            mod = importlib.import_module(commands[name])
            desc = getattr(mod, "COMMAND_DESC", "")
        except Exception:
            desc = ""
        lines.append(f"python3 cli.py {name:<20} {desc}")
    lines.append("```")
    print_output(make_output(success=True, markdown="\n".join(lines)))


def main() -> int:
    commands = _discover_capabilities()
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        _usage(commands)
        return 1

    command = sys.argv[1]
    module_path = commands.get(command)
    if not module_path:
        print_output(make_output(
            success=False,
            error_code="UNKNOWN_COMMAND",
            markdown=f"未知命令: `{command}`\n\n可用命令: {', '.join(sorted(commands.keys()))}",
        ))
        return 1

    try:
        sys.argv = [f"cli.py {command}"] + sys.argv[2:]
        mod = importlib.import_module(module_path)
        result = mod.main()
        return result if isinstance(result, int) else 0
    except Exception as exc:
        print_error(exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
