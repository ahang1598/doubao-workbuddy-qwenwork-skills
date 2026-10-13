"""``summary`` 命令族：汇总报表（一次性手动调用，由 Agent 按业务节奏触发）。"""

from __future__ import annotations

import argparse

from scripts.app import AppContext
from scripts.commands.base import BaseCommand
from scripts.commands.registry import register_command
from scripts.utils.output import err, print_json


@register_command
class SummaryCommand(BaseCommand):
    name = "summary"
    help = "汇总报表（一次性手动调用，CLI 不内置 daemon / 周期触发）"

    def configure(self, parser: argparse.ArgumentParser) -> None:
        sub = parser.add_subparsers(dest="subcommand", required=True)

        sr = sub.add_parser(
            "run",
            help="生成并推送指定模板的汇总报表",
            description=(
                "生成并推送指定模板的汇总报表。\n"
                "约束（H8）：当用户没明确指定模板 ID 时，禁止猜测——\n"
                "  必须先 `template list` 把候选展示给用户确认后再调用本命令。\n"
                "若模板的 summary_receivers 为空则不推送（仅输出 stats）。"
            ),
        )
        sr.add_argument("--template-id", required=True)
        sr.add_argument(
            "--format",
            choices=["text", "html"],
            default="text",
            help="输出格式：text（默认文本推送）、html（HTML 报告，需使用子技能 report-generator）",
        )
        sr.set_defaults(func=_run)


def _serialize(result) -> dict:
    return {
        "template_id": result.template_id,
        "receivers": result.receivers,
        "success": result.success,
        "failed": result.failed,
        "stats": result.stats.to_dict() if result.stats else None,
    }





def _run(args, ctx: AppContext) -> int:
    tpl = ctx.template_manager.get_template(args.template_id)
    if not tpl:
        err(f"模板不存在: {args.template_id}")
        return 1
    output_format = getattr(args, "format", "text")
    result = ctx.summarizer.summary_template(tpl, output_format=output_format)
    print_json(_serialize(result))
    return 0
