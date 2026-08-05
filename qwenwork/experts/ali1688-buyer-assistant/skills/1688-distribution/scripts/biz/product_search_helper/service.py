#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""选品搜索服务 — 关键词选品 + 图搜选品"""

import os
import sys
from typing import List, Optional

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')))
from scripts._sys._mcp import fail_if_tool_error, loads_if_json, unwrap_mcp_payload
from scripts._sys._errors import ServiceError


# ── 关键词选品 ────────────────────────────────────────────────────────────────

def parse_select_offer_result(payload, page_size: int = 20) -> dict:
    """处理 MCP distribution_select_offer 返回结果。"""
    inner = unwrap_mcp_payload(payload)
    inner = loads_if_json(inner)
    fail_if_tool_error(inner)

    # 兼容多种返回结构：
    # 1. list 直接返回商品数组
    # 2. {"data": {"data": [...], "total": N}} 嵌套结构
    # 3. {"data": [...], "total": N} 扁平结构
    if isinstance(inner, list):
        result = {
            "data": inner,
            "total": len(inner),
        }
    elif isinstance(inner, dict):
        data_field = inner.get("data", {})
        if isinstance(data_field, dict):
            result = {
                "data": data_field.get("data", []),
                "total": data_field.get("total", 0),
            }
        elif isinstance(data_field, list):
            result = {
                "data": data_field,
                "total": inner.get("total", len(data_field)),
            }
        else:
            result = {"data": [], "total": 0}
    else:
        result = {"data": [], "total": 0}

    if len(result["data"]) > page_size:
        result["data"] = result["data"][:page_size]
    return result


# ── 图搜选品 ─────────────────────────────────────────────────────────────────

def parse_image_search_offer_result(payload) -> dict:
    """处理 MCP same_img_offer_search 返回结果。"""
    inner = unwrap_mcp_payload(payload)
    inner = loads_if_json(inner)
    fail_if_tool_error(inner)
    return _parse_image_search_result(inner)


def _parse_image_search_result(inner: dict) -> dict:
    """解析图搜返回结果。"""
    data_wrapper = inner.get("data", inner)
    if isinstance(data_wrapper, dict) and "bizSuccess" in data_wrapper:
        payload = data_wrapper
    else:
        payload = inner

    biz_success = payload.get("bizSuccess", True)
    if biz_success is False:
        biz_msg = payload.get("bizMsg", "图搜失败")
        raise ServiceError(f"图搜失败：{biz_msg}")

    items = payload.get("data", []) or []
    return {
        "data": items,
        "total": payload.get("total", len(items)),
        "pageNum": payload.get("pageNum", 1),
        "totalPage": payload.get("totalPage", 1),
        "extendInfo": payload.get("extendInfo", {}),
    }
