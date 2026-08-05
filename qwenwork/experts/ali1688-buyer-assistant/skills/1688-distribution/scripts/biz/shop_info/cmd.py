#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""店铺和工具信息查询命令"""

import os
import sys

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')))
from scripts._sys._output import print_output, print_error
from scripts._sys._mcp import load_json_payload
from scripts.biz.shop_info.service import parse_shop_and_tool_info, filter_available_tools


def _format_shop_list(tool_list: list) -> str:
    """将 toolList 格式化为可读的 Markdown 文本。"""
    if not tool_list:
        return "当前没有绑定任何店铺。"

    lines = ["您当前绑定的店铺如下：\n"]
    for tool in tool_list:
        app_name = tool.get("appName", "未知工具")
        lines.append(f"**【{app_name}】**")
        for channel in tool.get("channelList", []):
            channel_desc = channel.get("channelDesc", channel.get("channel", "未知渠道"))
            for shop in channel.get("shopList", []):
                shop_name = shop.get("shopName", "未知店铺")
                shop_code = shop.get("shopCode", "")
                lines.append(f"  - {channel_desc} · {shop_name}（店铺编码：{shop_code}）")
        lines.append("")
    return "\n".join(lines)


def query(mcp_result_file: str = ""):
    """查询店铺和工具信息 MCP 结果后处理"""
    try:
        payload = load_json_payload(mcp_result_file or None)
        result = parse_shop_and_tool_info(payload)
        tool_list = result.get("toolList", [])
        available_tools = filter_available_tools(tool_list)
        markdown = _format_shop_list(available_tools)
        print_output(True, markdown, {"toolList": available_tools})
    except Exception as e:
        print_error(e)
