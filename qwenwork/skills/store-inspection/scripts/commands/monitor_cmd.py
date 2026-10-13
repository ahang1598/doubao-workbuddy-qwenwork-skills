"""``monitor`` 命令族：通知明细查询。"""

from __future__ import annotations

import argparse

from scripts.app import AppContext
from scripts.commands.base import BaseCommand
from scripts.commands.registry import register_command



@register_command
class MonitorCommand(BaseCommand):
    name = "monitor"
    help = "通知明细查询（任务派发进度）"

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.description = (
            "查询「通知发送状态」（pending / sent / failed）。\n"
            "区分两个相近概念：\n"
            "  · 通知发送状态（本命令）—— 钉钉消息有没有发出去；\n"
            "  · 提交状态（用户填没填表）—— 走 `dispatch instances` 或 "
            "`dispatch notifications --filter unfilled`。"
        )
        sub = parser.add_subparsers(dest="subcommand", required=True)

        mq = sub.add_parser(
            "query",
            help="查询通知明细",
            description=(
                "查询通知明细。常见组合：\n"
                "  · 按门店名查：    --store-name <名> --task-id <ID>\n"
                "  · 按状态查失败：  --notify-status failed --task-id <ID>"
            ),
        )
        mq.add_argument("--task-id", default=None, help="按任务 ID 过滤")
        mq.add_argument("--store-name", default=None, help="按门店名称过滤")
        mq.add_argument(
            "--notify-status",
            default=None,
            choices=["pending", "sent", "failed"],
            help="按通知状态过滤",
        )
        mq.add_argument("--limit", type=int, default=None)
        mq.set_defaults(func=_query)


def _query(args, ctx: AppContext) -> int:
    rows = ctx.monitor.query_notifications(
        task_id=args.task_id,
        store_name=args.store_name,
        notify_status=args.notify_status,
        limit=args.limit,
    )
    print(ctx.monitor.format_notifications_as_markdown(rows))
    return 0
