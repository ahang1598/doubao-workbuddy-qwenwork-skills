#!/usr/bin/env python3
"""图片搜索 MCP 结果后处理 CLI入口"""

COMMAND_NAME = "image_search"
COMMAND_DESC = "图片搜索1688商品"

import os
import sys
import argparse

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..')))

from _output import print_error, print_output
from mcp_postprocess import build_search_result, format_search_output, load_json_payload


def main():
    parser = argparse.ArgumentParser(description="图片搜索 - 处理 MCP find_product 返回结果")
    parser.add_argument("--image", "-i", default="", help="原始图片 URL 或图片标识（仅用于结果元数据）")
    parser.add_argument("--mcp-result-file", help="MCP find_product 原始 JSON 文件；不传则从 stdin 读取")
    args = parser.parse_args()

    try:
        payload = load_json_payload(args.mcp_result_file)
        result = build_search_result(payload, search_type="image_similarity", source_image=args.image)
        total = result.get("total_results", 0)
        header = f"✅ 找到 {total} 个匹配商品" if total else "未找到匹配商品"
        print_output(format_search_output(result, header))
    except Exception as e:
        print_error(e, {"data": {}})


if __name__ == "__main__":
    main()
