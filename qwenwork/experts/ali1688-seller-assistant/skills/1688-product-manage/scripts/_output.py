#!/usr/bin/env python3
"""JSON output helpers for local post-processing scripts."""

from __future__ import annotations

import json

from _errors import SkillError


def make_output(success: bool, markdown: str = "", data: dict | None = None,
                error_code: str = "") -> dict:
    result = {"success": success}
    if markdown:
        result["markdown"] = markdown
    if data is not None:
        result["data"] = data
    if error_code:
        result["error_code"] = error_code
    return result


def print_output(output: dict) -> None:
    print(json.dumps(output, ensure_ascii=False, indent=2))


def print_error(error: Exception, default_data: dict | None = None) -> None:
    if isinstance(error, SkillError):
        output = make_output(success=False, markdown=f"❌ {error.message}", data=default_data)
    elif isinstance(error, ValueError):
        output = make_output(success=False, markdown=f"❌ 参数错误：{error}", data=default_data)
    else:
        output = make_output(success=False, markdown=f"❌ 操作失败：{error}", data=default_data)
    print_output(output)
