"""``attachment`` 命令族：AI 表格附件字段下载链接获取。

子命令：``get-urls``
"""

from __future__ import annotations

import argparse
import json
from typing import Any, Dict, List, Optional

from scripts.app import AppContext
from scripts.commands.base import BaseCommand
from scripts.commands.registry import register_command
from scripts.utils.output import err, ok, print_json, warn


@register_command
class AttachmentCommand(BaseCommand):
    name = "attachment"
    help = "AI 表格附件字段下载链接获取"

    def configure(self, parser: argparse.ArgumentParser) -> None:
        sub = parser.add_subparsers(dest="subcommand", required=True)

        get_urls = sub.add_parser("get-urls", help="获取指定记录指定字段的附件下载链接")
        get_urls.add_argument("--base-id", required=True, help="AI 表格 Base ID")
        get_urls.add_argument("--table-id", required=True, help="数据表 ID (sheetId)")
        get_urls.add_argument(
            "--field-id",
            required=True,
            help="附件字段的 fieldId",
        )
        get_urls.add_argument(
            "--record-id",
            default=None,
            help="指定记录 ID（不传则获取所有记录的附件链接）",
        )
        get_urls.add_argument(
            "--limit",
            type=int,
            default=20,
            help="最多返回记录数（默认 20，仅在未指定 --record-id 时生效）",
        )
        get_urls.add_argument(
            "--url-only",
            action="store_true",
            help="仅输出下载 URL（每行一个），适合管道使用",
        )
        get_urls.set_defaults(func=_get_urls)


# ---------------------------------------------------------------------------
# handlers
# ---------------------------------------------------------------------------


def _get_urls(args: argparse.Namespace, ctx: AppContext) -> int:
    """获取附件字段的下载链接。"""
    base_id: str = args.base_id
    table_id: str = args.table_id
    field_id: str = args.field_id
    record_id: Optional[str] = args.record_id
    limit: int = args.limit
    url_only: bool = args.url_only

    # 构造过滤条件：如果指定了 record_id，按 record_id 过滤
    filters = None
    query_limit = None if record_id else limit

    result = ctx.client.aitable_record_query(
        base_id=base_id,
        table_id=table_id,
        filters=filters,
        limit=query_limit,
    )

    records = (result.get("data") or {}).get("records") or []

    # 如果指定了 record_id，从结果中过滤
    if record_id:
        records = [r for r in records if r.get("recordId") == record_id]
        if not records:
            err(f"未找到记录: {record_id}")
            return 1

    attachments_output = _extract_attachments(records, field_id)

    if not attachments_output:
        warn("未找到任何附件数据（字段可能为空或非附件类型）")
        return 0

    if url_only:
        for item in attachments_output:
            for attachment in item["attachments"]:
                print(attachment["url"])
    else:
        ok(f"共找到 {sum(len(item['attachments']) for item in attachments_output)} 个附件")
        print_json(attachments_output)

    return 0


def _extract_attachments(
    records: List[Dict[str, Any]], field_id: str
) -> List[Dict[str, Any]]:
    """从记录列表中提取指定字段的附件信息。

    Returns:
        列表，每个元素包含 recordId 和该记录下的附件列表。
    """
    output: List[Dict[str, Any]] = []

    for record in records:
        record_id = record.get("recordId", "")
        cells = record.get("cells") or {}
        field_value = cells.get(field_id)

        if not field_value or not isinstance(field_value, list):
            continue

        attachments = []
        for item in field_value:
            if not isinstance(item, dict):
                continue
            attachment_info = {
                "filename": item.get("filename", ""),
                "url": item.get("url", ""),
                "size": item.get("size", 0),
                "type": item.get("type", ""),
                "resourceId": item.get("resourceId", ""),
            }
            if attachment_info["url"]:
                attachments.append(attachment_info)

        if attachments:
            output.append({
                "recordId": record_id,
                "attachments": attachments,
            })

    return output
