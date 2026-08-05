#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分销知识库查询服务

功能：
1. 查询分销知识库（按 query / channel / business 筛选）
2. 渠道/工具名称验证
"""

import os
import sys
import json
from typing import Dict, List

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')))
from scripts._sys._mcp import fail_if_tool_error, loads_if_json, unwrap_mcp_payload

# ── 固定参数 ──────────────────────────────────────────────────────────────
DEFAULT_USER_ID = 0

# ── 渠道列表（直接传中文名称，未指定时传 "default"）──────────────────────
VALID_CHANNELS = [
    "淘宝", "天猫", "抖音", "拼多多", "快团团", "小红书", "快手",
    "微信小店", "京东", "有赞", "微店", "淘特", "微信小商店",
    "支付宝", "苏宁", "闲鱼", "饿了么", "美团", "度小店", "微盟", "微购相册",
]

# ── 工具列表（直接传中文名称，未指定时传 "default"）──────────────────────
VALID_BUSINESSES = [
    "逸淘分销铺货", "自动分销", "代发助手王", "店长铺货", "妙手分销",
    "速当家分销", "智淘分销", "甩手易分销", "无忧分销王", "晓风分销",
    "大泽云铺货", "顶卖分销", "铺货代发", "1688官方铺货", "普云铺货",
    "麦爆了分销", "马上分销", "掌中宝分销", "智汇分销", "微购相册",
    "抖掌柜分销", "旺分销铺货", "小天分销", "火牛分销王",
]


def is_valid_channel(name: str) -> bool:
    """验证渠道名称是否有效（中文名或 "default"）"""
    return name == "default" or name in VALID_CHANNELS


def is_valid_business(name: str) -> bool:
    """验证工具名称是否有效（中文名或 "default"）"""
    return name == "default" or name in VALID_BUSINESSES


def list_channels() -> List[str]:
    """返回所有支持的渠道名称列表"""
    return VALID_CHANNELS.copy()


def list_businesses() -> List[str]:
    """返回所有支持的工具名称列表"""
    return VALID_BUSINESSES.copy()


def query_knowledge(
    query: str,
    channel: str = "default",
    business: str = "default",
    payload=None,
) -> Dict:
    """
    查询分销知识库

    :param query: 用户的查询问题（必填，原封不动传递用户原话）
    :param channel: 渠道中文名（如 "抖音"），未指定时传 "default"
    :param business: 工具中文名（如 "逸淘分销铺货"），未指定时传 "default"
    :return: {"success": bool, "data": [...], "error": str}
             data 为文档数组，每条包含 score, chunking_val, source_url
    """
    # 参数校验
    if not query or not query.strip():
        return {"success": False, "data": None, "error": "查询问题不能为空", "errorCode": "PARAM_ERROR"}

    if not is_valid_channel(channel):
        return {"success": False, "data": None, "error": f"无效的渠道名称：{channel}", "errorCode": "PARAM_ERROR"}

    if not is_valid_business(business):
        return {"success": False, "data": None, "error": f"无效的工具名称：{business}", "errorCode": "PARAM_ERROR"}

    result = unwrap_mcp_payload(payload)
    result = loads_if_json(result)
    fail_if_tool_error(result)

    # 处理返回数据：MCP 结果中 data 字段可能是 JSON 字符串（文档数组）
    data = result
    if isinstance(result, dict):
        data = result.get("data", result)

    # data 可能是 JSON 字符串，需要解析
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            data = []

    return {
        "success": True,
        "data": data if isinstance(data, list) else []
    }
