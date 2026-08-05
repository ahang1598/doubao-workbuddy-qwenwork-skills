#!/usr/bin/env python3
"""1688-product-find MCP result post-processing CLI.

The 1688 API call and user authorization are handled by the `ali1688-buyer` MCP
connector. This CLI only accepts the MCP tool result JSON and applies the
legacy deterministic post-processing logic: field normalization, markdown
formatting, and comparison selection.
"""

from __future__ import annotations

import importlib
import json
import os
import sys
from pathlib import Path

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
if sys.stdin and hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8")

SKILL_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = str(SKILL_DIR / "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)


def _output(success: bool, markdown: str = "", data: dict | None = None) -> None:
    result: dict = {"success": success}
    if markdown:
        result["markdown"] = markdown
    if data is not None:
        result["data"] = data
    print(json.dumps(result, ensure_ascii=False), flush=True)


def _discover_capabilities() -> dict[str, str]:
    commands: dict[str, str] = {}
    caps_dir = os.path.join(SCRIPTS_DIR, "capabilities")
    if not os.path.isdir(caps_dir):
        return commands
    for name in sorted(os.listdir(caps_dir)):
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
    lines = [
        "**1688-product-find 后处理 CLI 用法**",
        "",
        "先调用 MCP 工具 `find_product` / `offer_query_for_trade`，再将 MCP 返回 JSON 传给本 CLI：",
        "",
        "```",
    ]
    for name in sorted(commands):
        try:
            mod = importlib.import_module(commands[name])
            desc = getattr(mod, "COMMAND_DESC", "")
        except Exception:
            desc = ""
        lines.append(f"python3 cli.py {name:<12} {desc}")
    lines.extend([
        "```",
        "",
        "示例：",
        "```",
        "python3 cli.py text_search --query \"黑色连帽卫衣\" --mcp-result-file /tmp/find_product.json",
        "cat /tmp/find_product.json | python3 cli.py compare --image \"https://...jpg\"",
        "```",
    ])
    _output(True, "\n".join(lines))


def main() -> int:
    commands = _discover_capabilities()
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        _usage(commands)
        return 0

    command = sys.argv[1]
    handler = commands.get(command)
    if not handler:
        _output(False, f"未知命令: `{command}`\n\n可用命令: {', '.join(sorted(commands.keys()))}")
        return 1

    sys.argv = [f"cli.py {command}"] + sys.argv[2:]
    mod = importlib.import_module(handler)
    result = mod.main()
    return result if isinstance(result, int) else 0


if __name__ == "__main__":
    sys.exit(main())
