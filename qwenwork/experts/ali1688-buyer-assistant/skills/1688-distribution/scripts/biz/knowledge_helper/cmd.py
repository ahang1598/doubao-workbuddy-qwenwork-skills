#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分销知识库查询命令"""

import os
import sys

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')))
from scripts._sys._output import print_output, print_error
from scripts._sys._mcp import load_json_payload
from scripts.biz.knowledge_helper.service import (
    query_knowledge, list_channels, list_businesses
)


def query(query: str = "", channel: str = "default", business: str = "default", mcp_result_file: str = ""):
    """
    查询分销知识库

    用法：
      python3 scripts/cli.py knowledge_helper query --query="铺货流程"
      python3 scripts/cli.py knowledge_helper query --query="发货" --channel="抖音" --business="自动分销"
      python3 scripts/cli.py knowledge_helper query --query="退款" --channel="淘宝" --business="default"
    """
    try:
        if not query:
            print_output(False, "❌ 缺少必填参数 query（查询问题）", {})
            return

        payload = load_json_payload(mcp_result_file or None)
        result = query_knowledge(query=query, channel=channel, business=business, payload=payload)

        if result.get("success"):
            doc_list = result.get("data", [])
            count = len(doc_list)
            if count > 0:
                top_score = max(d.get("score", 0) for d in doc_list)
                md = f"✅ 查询成功，返回 {count} 条结果，最高相关度 {top_score:.2f}"
            else:
                md = "查询成功，但未找到相关文档，建议换个关键词或使用默认渠道/工具重试"
            print_output(True, md, result)
        else:
            print_output(False, f"查询失败：{result.get('error', '未知错误')}", result)
    except Exception as e:
        print_error(e)


def channels():
    """
    列出所有支持的渠道

    用法：
      python3 scripts/cli.py knowledge_helper channels
    """
    try:
        ch_list = list_channels()
        print_output(True, f"支持 {len(ch_list)} 个渠道", {"channels": ch_list})
    except Exception as e:
        print_error(e)


def businesses():
    """
    列出所有支持的工具

    用法：
      python3 scripts/cli.py knowledge_helper businesses
    """
    try:
        biz_list = list_businesses()
        print_output(True, f"支持 {len(biz_list)} 个工具", {"businesses": biz_list})
    except Exception as e:
        print_error(e)
