#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""选品搜索命令 — CLI 入口（关键词选品 + 图搜选品）"""

import json
import os
import sys

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')))
from scripts._sys._output import print_output, print_error
from scripts._sys._mcp import load_json_payload
from scripts.biz.product_search_helper.service import (
    parse_select_offer_result,
    parse_image_search_offer_result,
)


def search(filters: str = "", page_no: str = "1", page_size: str = "20",
           rank_type: str = "", rank_field: str = "",
           image_url: str = "", image_base64: str = "",
           region: str = "", keyword: str = "", mcp_result_file: str = ""):
    """选品搜索 MCP 结果后处理（支持关键词和图搜两种模式）"""
    try:
        payload = load_json_payload(mcp_result_file or None)
        if image_url or image_base64:
            result = parse_image_search_offer_result(payload)
        elif filters:
            json.loads(filters)
            result = parse_select_offer_result(payload, page_size=int(page_size))
        else:
            print_output(False, "❌ 缺少必需的选品参数，请指定 --filters 或 --image_url", {})
            return

        total = result.get("total", 0)
        items = result.get("data", [])

        # 为品牌商品注入授权链接，避免 AI 自行拼接 URL
        brand_url_tpl = "https://air.1688.com/app/channel-fe/distribution-work/brand.html#/auth_apply?offerId={}"
        for item in items:
            if item.get("isBrandOffer") and not item.get("isBrandAuth"):
                item["brandAuthUrl"] = brand_url_tpl.format(item.get("offerId", ""))

        summary = f"找到 {total} 个商品，当前展示 {len(items)} 个"
        print_output(True, summary, result)
    except json.JSONDecodeError as e:
        print_output(False, f"❌ 筛选条件 JSON 格式错误：{e}", {})
    except Exception as e:
        print_error(e)
