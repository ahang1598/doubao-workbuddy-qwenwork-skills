#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""铺货执行服务 — 内置铺货接口调用"""

import json
import os
import sys

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')))
from scripts._sys._mcp import fail_if_tool_error, loads_if_json, unwrap_mcp_payload


def parse_distribute_result(payload) -> dict:
    """处理 MCP distribute_offer 返回结果。"""
    inner = unwrap_mcp_payload(payload)
    inner = loads_if_json(inner)
    fail_if_tool_error(inner)

    data_wrapper = inner.get("data", inner)
    if isinstance(data_wrapper, dict):
        if "data" not in data_wrapper:
            data = dict(data_wrapper)
            data["errorCode"] = data.get("errorCode", inner.get("errorCode", ""))
            return data
        data_str = data_wrapper.get("data", "")
        error_code = data_wrapper.get("errorCode", "")
    else:
        data_str = data_wrapper if isinstance(data_wrapper, str) else ""
        error_code = inner.get("errorCode", "")

    try:
        data = json.loads(data_str) if data_str else {}
    except Exception:
        data = {}
    data["errorCode"] = error_code
    return data
