#!/usr/bin/env python3
"""1688供应商查询 MCP 结果后处理 CLI入口"""

COMMAND_NAME = "ali_1688_source_suppliers"
COMMAND_DESC = "查询1688供应商信息"

import os
import sys
import argparse
import time

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..')))

from _output import make_output, print_output, print_error

from capabilities.ali_1688_source_suppliers.service import (
    load_json_payload,
    process_1688_source_suppliers_result,
)

MAX_RETRIES = 3
RETRY_DELAY = 1  # 重试间隔秒数


class SilentArgumentParser(argparse.ArgumentParser):
    """抑制 argparse 默认错误输出的解析器"""

    def error(self, message):
        # 不输出 usage 信息，直接抛出 SystemExit
        sys.exit(2)


def main():
    parser = SilentArgumentParser(description="供应商信息查询 MCP 结果后处理")
    parser.add_argument("--query", "-q", required=True, help="供应商名称")
    parser.add_argument("--mcp-result-file", help="MCP 1688_source_suppliers 原始 JSON 文件；不传则从 stdin 读取")

    try:
        args = parser.parse_args()
    except SystemExit:
        # argparse 参数缺失时会调用 sys.exit，捕获后返回标准 JSON 格式
        print_output(make_output(
            success=False,
            markdown="❌ 参数缺失：query 不能为空。\n\n请提供查询关键字，例如：\n- `cli.py ali_1688_source_suppliers --query \"灯具供应商\"`\n- `cli.py ali_1688_source_suppliers -q \"常州工厂\"`",
            data={"data": {}},
        ))
        return

    # 重试逻辑：最多3轮重试
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            payload = load_json_payload(args.mcp_result_file)
            result = process_1688_source_suppliers_result(payload, query=args.query)
            markdown_output = result.get("markdown", "未找到供应商信息")

            # 成功时不追加引导链接
            print_output(make_output(
                success=True,
                markdown=markdown_output,
                data=result,
            ))
            return  # 成功则直接返回
        except Exception as e:
            last_error = str(e)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
                continue

    # 3轮重试后依然失败，告知用户并追加引导链接
    guide_link = "\n\n> 📌 [在1688上搜索更多供应商](https://s.1688.com/company/company_search.htm)"
    error_msg = f"❌ 查询失败（已重试{MAX_RETRIES}次）：{last_error}\n\n请稍后重试。{guide_link}"
    print_output(make_output(
        success=False,
        markdown=error_msg,
        data={"data": {}, "error": last_error, "retries": MAX_RETRIES},
    ))


if __name__ == "__main__":
    main()
