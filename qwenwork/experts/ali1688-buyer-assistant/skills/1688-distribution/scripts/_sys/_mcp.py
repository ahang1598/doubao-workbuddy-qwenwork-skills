#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MCP result loading and unwrapping helpers.

The ali1688-buyer MCP connector owns authentication and API calls. Distribution
Python scripts only receive raw MCP tool results and apply deterministic
post-processing.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Optional

from scripts._sys._errors import ServiceError


def loads_if_json(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text:
        return value
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return value


def load_json_payload(path: Optional[str] = None) -> Any:
    raw = Path(path).read_text(encoding="utf-8") if path else sys.stdin.read()
    raw = raw.strip()
    if not raw:
        raise ValueError("缺少 MCP 工具返回结果，请通过 --mcp-result-file 或 stdin 传入 JSON")
    return json.loads(raw)


def unwrap_mcp_payload(payload: Any) -> Any:
    """Unwrap common MCP/JSON-RPC envelopes and return business data."""
    payload = loads_if_json(payload)

    if isinstance(payload, dict) and payload.get("error"):
        error = payload["error"]
        message = error.get("message") if isinstance(error, dict) else str(error)
        raise ServiceError(message or "MCP 工具调用失败")

    result = payload.get("result") if isinstance(payload, dict) and "result" in payload else payload

    if isinstance(result, dict) and result.get("isError"):
        content = result.get("content") or []
        if content and isinstance(content[0], dict):
            raise ServiceError(content[0].get("text") or "MCP 工具调用失败")
        raise ServiceError("MCP 工具调用失败")

    if isinstance(result, dict) and "content" in result:
        content = result.get("content") or []
        if content and isinstance(content[0], dict) and "text" in content[0]:
            return unwrap_mcp_payload(content[0]["text"])
        return content

    return result


def fail_if_tool_error(data: Any, default_message: str = "MCP 工具调用失败") -> None:
    if isinstance(data, dict) and (data.get("success") is False or data.get("__success__") is False):
        message = data.get("markdown") or data.get("message") or data.get("msgInfo") or data.get("error") or default_message
        raise ServiceError(str(message))

