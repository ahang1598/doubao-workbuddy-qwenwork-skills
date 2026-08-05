#!/usr/bin/env python3
"""Generate a shop operation diagnostic report from MCP tool results."""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..")))

from _output import make_output, print_error, print_output
from capabilities.post_process_report.service import build_report


COMMAND_NAME = "post_process_report"
COMMAND_DESC = "基于 MCP 返回数据生成店铺经营健康诊断报告"


def _read_payload(args: argparse.Namespace) -> dict:
    if args.input_file:
        with open(args.input_file, "r", encoding="utf-8") as file:
            return json.load(file)

    raw = sys.stdin.read().strip()
    if not raw:
        raise ValueError("缺少输入 JSON，请通过 --input-file 或 stdin 传入 MCP 工具返回数据")
    return json.loads(raw)


def main() -> int:
    parser = argparse.ArgumentParser(description="店铺经营健康诊断报告后处理")
    parser.add_argument("--input-file", help="包含 MCP 工具返回数据的 JSON 文件路径")
    args = parser.parse_args()

    try:
        payload = _read_payload(args)
        result = build_report(payload)
        print_output(make_output(
            success=True,
            markdown=result["markdown"],
            data=result["data"],
        ))
        return 0
    except Exception as exc:
        print_error(exc, {"data": {}})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
