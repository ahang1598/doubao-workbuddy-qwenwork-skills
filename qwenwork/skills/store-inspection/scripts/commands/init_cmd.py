"""``init`` 命令族：系统初始化与 AI表格 绑定。

子命令：``create / query / url / validate / unbind``
"""

from __future__ import annotations

import argparse

from scripts.app import AppContext
from scripts.commands.base import BaseCommand
from scripts.commands.registry import register_command
from scripts.domain.exceptions import DuplicateBaseError
from scripts.infrastructure import config as cfg
from scripts.utils.output import err, ok, print_json, warn


@register_command
class InitCommand(BaseCommand):
    name = "init"
    help = "系统初始化"

    def configure(self, parser: argparse.ArgumentParser) -> None:
        sub = parser.add_subparsers(dest="subcommand", required=True)

        ic = sub.add_parser("create", help="新建 AI表格 并绑定（模式 A）")
        ic.add_argument(
            "--name",
            default=None,
            help="表格名称（1~50 字符，默认：门店巡检任务中心）",
        )
        ic.set_defaults(func=_create)

        iq = sub.add_parser("query", help="列出/搜索已有 AI表格（模式 B）")
        iq.add_argument("--keyword", default=None, help="按关键词搜索（≥2 字符）")
        iq.set_defaults(func=_query)

        iu = sub.add_parser("url", help="通过 URL 或 BASE_ID 绑定（模式 C）")
        iu.add_argument("url_or_id")
        iu.add_argument(
            "--auto-repair",
            action="store_true",
            help="校验失败时自动补齐缺失表/字段（不会修复字段类型不匹配）",
        )
        iu.set_defaults(func=_url)

        iv = sub.add_parser("validate", help="校验当前 AI表格 结构")
        iv.set_defaults(func=_validate)

        iub = sub.add_parser(
            "unbind",
            help="解除当前 AI表格 绑定（清除本地配置，不删除 AI表格 数据）",
        )
        iub.add_argument(
            "--confirm",
            action="store_true",
            help="确认解除绑定（必填，未传则拒绝执行并提示重读 Skill 文档）",
        )
        iub.set_defaults(func=_unbind)


# ---------------------------------------------------------------------------
# handlers
# ---------------------------------------------------------------------------


def _create(args, ctx: AppContext) -> int:
    kwargs = {}
    if args.name is not None:
        kwargs["base_name"] = args.name
    try:
        base_id = ctx.initializer.init_create(**kwargs)
    except DuplicateBaseError as exc:
        existing_name = exc.args[0].split("「")[1].split("」")[0] if "「" in exc.args[0] else kwargs.get("base_name", "门店巡检任务中心")
        suggested_name = f"{existing_name}-2"
        warn(f"检测到已存在同名 AI表格：{exc.args[0]}")
        print(f"  已有 AI表格 ID  : {exc.base_id}")
        print(f"  已有 AI表格 链接: {exc.base_link}")
        print()
        print("需要用户确认后续操作，请告知用户选择以下其中一项：")
        print(f"  [1] 复用已有 AI表格（推荐）：运行 `init url {exc.base_id}`")
        print(f"  [2] 换名新建（建议名称：{suggested_name!r}）：运行 `init create --name {suggested_name!r}`")
        print("  [q] 取消，不做任何操作")
        return 1
    ok(f"AI表格 创建并绑定成功: {base_id}")
    print(f"链接: https://docs.dingtalk.com/i/nodes/{base_id}")
    print(
        "⚠️ 请勿修改 3 张固定表的表名（门店清单 / 巡店模版 / 任务记录），"
        "也不要重命名各表的骨架字段。"
    )
    print(
        "注意：通知明细表为动态表，由系统在每次派发时自动创建，无需手工维护。"
    )
    print(
        "下一步：运行 `check` 命令验证表结构，或直接通过 "
        "`uv run python scripts/cli.py template create` 创建巡检模版。"
    )
    return 0


def _query(args, ctx: AppContext) -> int:
    candidates = ctx.initializer.init_query(args.keyword)
    if not candidates:
        warn("未找到匹配的 AI表格，可改用 `init url` 直接输入链接绑定。")
        return 1
    print("候选 AI表格 列表（仅展示，不会自动绑定，请用 init url 完成绑定）：")
    for i, b in enumerate(candidates, 1):
        print(f"  {i}. {b.get('baseName', '')}  ({b.get('baseId', '')})")
    return 0


def _url(args, ctx: AppContext) -> int:
    base_id = ctx.initializer.init_url(
        args.url_or_id, auto_repair=args.auto_repair
    )
    ok(f"AI表格 已绑定: {base_id}")
    return 0


def _validate(args, ctx: AppContext) -> int:
    bid = cfg.get_base_id()
    if not bid:
        warn("当前未绑定任何 AI表格，请选择以下操作之一：")
        print("  [1] 新建 AI表格：运行 `init create`")
        print("  [2] 绑定已有 AI表格：运行 `init url <BASE_ID 或链接>`")
        return 2
    report = ctx.initializer.validate(bid)
    print_json(report.to_dict())
    return 0 if report.is_passed else 1


def _unbind(args, ctx: AppContext) -> int:
    if not args.confirm:
        err(
            "解除绑定需要追加 --confirm 参数。\n"
            "  用途：清除本地配置文件，解除与当前 AI表格 的绑定关系，不会删除 AI表格 数据。\n"
            "  请重读 Skill 文档 references/setup/01-init.md#init-unbind 了解解除绑定的完整流程。"
        )
        return 2
    existing_base_id = cfg.get_base_id()
    if not existing_base_id:
        warn("当前未绑定任何 AI表格，无需解除绑定。")
        return 0
    ctx.initializer.reset()
    ok(f"已解除 AI表格 绑定（原 base_id: {existing_base_id}）。")
    print("AI表格 数据未受影响，如需重新绑定可使用 `init url` 或 `init create`。")
    return 0
