"""``share`` 命令族：把当前 ``base_id`` 包装成标准化分享语句。

设计动机：
- 一个用户已经把巡店任务派发系统配好了（绑定了钉钉 AI表格、维护好了门店清单 /
  巡店模版），希望把整套配置共享给同事 / 团队成员。
- 接收方只要安装了 ``store-inspection`` Skill，把分享语句粘贴给自己的 Agent，
  Agent 解析出 ``BASE_ID`` 后调用现有 ``init url`` 即可完成绑定，无需新增接收侧 CLI。

子命令：
- ``share generate``：生成可被对方 Skill 直接识别的标准分享语句

> 不持久化任何东西，仅 stdout 输出；不自动调用钉钉接口给对方加管理员（当前不
> 支持自动加协作者），由 Skill 在调用前提示用户在 AI 表格中手动添加。
"""

from __future__ import annotations

import argparse

from scripts.app import AppContext
from scripts.commands.base import BaseCommand
from scripts.commands.registry import register_command
from scripts.infrastructure import config as cfg
from scripts.utils.output import err


# 标准分享语句模板（多行字符串）
# 必须包含 "BASE_ID = <BAS_xxx>" 字样，便于接收方 Agent 用正则识别。
_SHARE_TEMPLATE_HEAD = "---- 巡店任务派发配置分享 -----"
_SHARE_TEMPLATE_TAIL = "----------------------------"


@register_command
class ShareCommand(BaseCommand):
    name = "share"
    help = "巡店配置分享：生成标准分享语句，对方粘贴给 Agent 即可绑定"

    def configure(self, parser: argparse.ArgumentParser) -> None:
        sub = parser.add_subparsers(dest="subcommand", required=True)

        sg = sub.add_parser(
            "generate",
            help="生成可被对方 Skill 直接识别的分享语句",
        )
        sg.add_argument(
            "--base-id",
            default=None,
            help="可选；不传则自动读取当前已绑定的 base_id",
        )
        sg.add_argument(
            "--note",
            default=None,
            help="可选附加说明，会附在分享语句末尾",
        )
        sg.set_defaults(func=_generate)


# ---------------------------------------------------------------------------
# handlers
# ---------------------------------------------------------------------------

def _generate(args, ctx: AppContext) -> int:  # noqa: ARG001 - ctx 未使用但保持签名
    base_id = args.base_id or cfg.get_base_id()
    if not base_id:
        err(
            "当前未绑定 base_id，无法生成分享语句。"
            "请先运行 `store-inspection init create` 或 `init url <BASE_ID>`，"
            "或显式传入 `--base-id BAS_xxx`。"
        )
        return 1

    base_url = f"https://docs.dingtalk.com/i/nodes/{base_id}"

    lines = [
        _SHARE_TEMPLATE_HEAD,
        "请安装 store-inspection 技能，",
        f"然后将 BASE_ID = {base_id} 设置为巡店任务的 baseId。",
        f"AI 表格链接：{base_url}",
    ]
    if args.note:
        lines.append(f"备注：{args.note}")
    lines.append(_SHARE_TEMPLATE_TAIL)
    lines.append("\n📌 请将以上信息发送到你的 QoderWork 助手，以完成巡店任务派发系统的绑定。")

    # 主体输出（stdout）
    print("\n".join(lines))

    # 操作提醒（stderr，不污染主体，方便用户复制）
    print(
        "\n⚠️ 分享前请确认：已在 AI 表格中将对方加为协作者（管理员或可编辑），"
        "否则对方无法读写表格。当前工具未提供自动加协作者的能力，"
        "请在 AI 表格右上角『分享』菜单中手动添加。",
    )
    return 0
