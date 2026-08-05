#!/usr/bin/env python3
"""Run product-management post-processing for MCP tool results."""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..")))

from _output import make_output, print_error, print_output
from capabilities.post_process_action.service import handle_action


COMMAND_NAME = "post_process_action"
COMMAND_DESC = "处理 MCP 返回数据并保留商品运营原脚本后处理逻辑"


def _read_payload(args: argparse.Namespace) -> dict:
    if args.input_file:
        with open(args.input_file, "r", encoding="utf-8") as file:
            return json.load(file)
    raw = sys.stdin.read().strip()
    if not raw:
        raise ValueError("缺少输入 JSON，请通过 --input-file 或 stdin 传入")
    return json.loads(raw)


def main() -> int:
    parser = argparse.ArgumentParser(description="商品运营 MCP 后处理")
    parser.add_argument("--input-file", help="输入 JSON 文件路径")
    args = parser.parse_args()

    try:
        result = handle_action(_read_payload(args))
        print_output(make_output(
            success=result.get("success", True),
            markdown=result.get("markdown", ""),
            data=result.get("data"),
            error_code=result.get("error_code", ""),
        ))
        return 0 if result.get("success", True) else 1
    except Exception as exc:
        print_error(exc, {"data": {}})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
