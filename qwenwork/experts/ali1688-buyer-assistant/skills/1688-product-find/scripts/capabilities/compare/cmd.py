#!/usr/bin/env python3
"""商品比价 MCP 结果后处理 CLI 入口"""

COMMAND_NAME = "compare"
COMMAND_DESC = "商品比价 - 基于商品图片搜索同款并自动对比"

import os
import sys
import argparse

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..')))

from _output import print_output, print_error
from mcp_postprocess import build_compare_result, format_compare_output, load_json_payload


def main():
    parser = argparse.ArgumentParser(description="商品比价 - 处理 MCP find_product 返回结果并自动对比")
    parser.add_argument("--image", "-i", default="", help="用于 MCP 搜索的商品图片 URL（仅用于结果元数据）")
    parser.add_argument("--url", "-u", default="", help="来源商品链接或商品 ID（仅用于结果元数据）")
    parser.add_argument("--limit", "-l", type=int, default=3, help="对比商品数量，默认 3")
    parser.add_argument("--mcp-result-file", help="MCP find_product 原始 JSON 文件；不传则从 stdin 读取")
    args = parser.parse_args()

    try:
        payload = load_json_payload(args.mcp_result_file)
        result = build_compare_result(
            payload,
            source_image=args.image,
            source_url=args.url,
            limit=args.limit,
        )
        print_output(format_compare_output(result))
    except Exception as e:
        print_error(e, {"data": {}})


if __name__ == "__main__":
    main()
