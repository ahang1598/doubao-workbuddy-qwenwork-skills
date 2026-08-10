#!/usr/bin/env python3
"""校验飞书/Lark文档工具的交付回执。

用法：
  python3 validate_feishu_delivery.py --receipt receipt.json
  python3 validate_feishu_delivery.py --json '{"success":true,...}'

注意：本脚本验证交付回执与链接形式，不伪造、不代替飞书工具的实际创建操作。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


URL_PATTERN = re.compile(
    r"^https://[A-Za-z0-9.-]+\.(?:feishu\.cn|larksuite\.com)/"
    r"(?:docx|docs|wiki)/[A-Za-z0-9_-]+(?:[/?#].*)?$"
)


def blocked(message: str) -> None:
    print(f"DELIVERY_BLOCKED: {message}", file=sys.stderr)
    raise SystemExit(1)


def load_receipt(args: argparse.Namespace) -> dict[str, Any]:
    if args.receipt:
        try:
            raw = Path(args.receipt).read_text(encoding="utf-8")
        except OSError as exc:
            blocked(f"无法读取回执文件：{exc}")
    else:
        raw = args.json

    try:
        value = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as exc:
        blocked(f"回执不是有效JSON：{exc}")

    if not isinstance(value, dict):
        blocked("回执顶层必须是JSON对象")
    return value


def validate(value: dict[str, Any]) -> dict[str, Any]:
    if value.get("success") is not True:
        blocked(str(value.get("error") or "飞书文档创建工具未返回成功状态"))

    document_id = value.get("document_id")
    document_url = value.get("document_url") or value.get("url")
    title = value.get("title")

    if not isinstance(document_id, str) or not document_id.strip():
        blocked("缺少有效的document_id")
    if not isinstance(title, str) or not title.strip():
        blocked("缺少文档标题")
    if not isinstance(document_url, str) or not URL_PATTERN.fullmatch(document_url.strip()):
        blocked("缺少有效的飞书/Lark文档链接")

    # 如果工具提供写入状态或内容计数，将其作为强校验项。
    if "content_written" in value and value["content_written"] is not True:
        blocked("文档已创建，但内容未确认写入完成")
    if "block_count" in value:
        count = value["block_count"]
        if not isinstance(count, int) or isinstance(count, bool) or count <= 0:
            blocked("文档内容块数无效，可能是空文档")

    return {
        "delivery_verified": True,
        "title": title.strip(),
        "document_id": document_id.strip(),
        "document_url": document_url.strip(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="校验飞书/Lark文档交付回执")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--receipt", help="飞书文档工具回执JSON文件")
    source.add_argument("--json", help="飞书文档工具回执JSON字符串")
    args = parser.parse_args()

    result = validate(load_receipt(args))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
