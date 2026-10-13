"""``dispatch`` 命令族：派发任务（一次性手动调用，由 Agent 按业务节奏触发）。

子命令（创建与派发**物理隔离**，杜绝重复建表）：
  init           — **唯一能建表的入口**。当前周期内有任务则复用，无任务则新建；
                   引导分享 form_url，输出 task_context；不发任何消息。
  notify         — **派发入口**（主命令）。按 task_id 反查任务记录，找不到直接
                   报错；找到则执行通知派发。**不接受 --template-id**，从参数
                   层面阻止误触发建表。
  set-status     — 更新任务状态（进行中 / 已完成 / 已禁用）。
  notifications  — 查询任务通知明细，支持多维度过滤（JSON 输出）。
  list-pending   — 查询某任务下『已通知未填写』的成员列表（JSON）；
                   等价于 ``dispatch notifications --filter unfilled``。

非交互式用法（Agent 推荐）：
  # 路径 A · 全新派发：先 init 拿到 task_id，再 notify 通知人群
  dispatch init --template-id TPL_xxx [--form-url <已有链接>]
  dispatch notify --task-id TASK_xxx --form-url <分享链接>

  # 路径 B · 已有任务派发（用户回复链接 / 中断恢复 / 补发）
  dispatch notify --task-id TASK_xxx --form-url <分享链接>
  dispatch notify --task-id TASK_xxx --only-pending   # 仅催未填写

> 周期触发：本 CLI **不内置 daemon / cron**，每次调用都是一次性命令；
> 周期性派发由 Agent 按业务节奏在恰当时机调用 ``dispatch init`` +
> ``dispatch notify``，CLI 不感知调度器存在。
"""

from __future__ import annotations

import argparse
from datetime import datetime
from typing import List, Optional

from scripts.app import AppContext
from scripts.commands.base import BaseCommand
from scripts.commands.registry import register_command
from scripts.utils.output import apply_list_options, err, print_json, warn


@register_command
class DispatchCommand(BaseCommand):
    name = "dispatch"
    help = "派发任务（一次性手动调用，CLI 不内置 daemon / 周期触发）"

    def configure(self, parser: argparse.ArgumentParser) -> None:
        sub = parser.add_subparsers(dest="subcommand", required=True)

        # ── init ─────────────────────────────────────────────────────
        # 唯一能建表的入口：当前周期内有任务则复用，无任务则新建。
        di = sub.add_parser(
            "init",
            help="创建或复用派发任务（当前周期内有任务则复用，无则新建），输出 task_context",
        )
        di.add_argument("--template-id", required=True, help="模版 ID")
        di.add_argument(
            "--form-url",
            default=None,
            help=(
                "表单分享链接（含 /notable/share/form/）。"
                "传入合法链接时跳过交互式引导，直接写入任务记录。"
            ),
        )
        di.add_argument(
            "--extra-info",
            default=None,
            metavar="TEXT",
            help=(
                "本次派发附加给店长的额外信息，会渲染到消息模板的 {额外信息} / "
                "{extra_info} 占位符；模板未使用占位符时，自动追加到正文末尾。"
                "同时持久化到任务记录的 extra_info 字段，提醒消息也会带上同一份内容。"
            ),
        )
        di.set_defaults(func=_init)

        # ── notify ───────────────────────────────────────────────────
        # 派发入口（主命令）：按 task_id 派发，**不接受 --template-id**，物理上不能建表。
        dnotify = sub.add_parser(
            "notify",
            help="按 task_id 派发任务到目标门店（不创建任务，找不到 task_id 直接报错）",
        )
        _add_task_args(dnotify)
        dnotify.set_defaults(func=_task)

        # ── query ────────────────────────────────────────────────────
        dq = sub.add_parser(
            "query",
            help="查询任务列表，支持按模版/状态/日期过滤（JSON 输出）",
        )
        dq.add_argument("--template-id", default=None, help="按模版 ID 过滤")
        dq.add_argument(
            "--status",
            default=None,
            choices=["进行中", "已完成", "部分失败", "已禁用"],
            help="按任务状态过滤",
        )
        dq.add_argument("--date-from", default=None, metavar="YYYY-MM-DD", help="发起日期下限（含）")
        dq.add_argument("--date-to", default=None, metavar="YYYY-MM-DD", help="发起日期上限（含）")
        dq.add_argument("--limit", type=int, default=None, help="最多返回 N 条")
        dq.add_argument(
            "--last-n",
            type=int,
            default=None,
            metavar="N",
            help="查询模版最后 N 次派发（需配合 --template-id）",
        )
        dq.add_argument(
            "--today",
            action="store_true",
            help="仅查询今天的任务（等价于 --date-from today --date-to today）",
        )
        dq.add_argument(
            "--fields",
            default=None,
            metavar="FIELD1,FIELD2,...",
            help="仅返回指定字段（逗号分隔），如 task_id,template_id,status",
        )
        dq.add_argument(
            "--count-only",
            action="store_true",
            help="仅返回符合条件的总数 {\"total\": N}，不返回数据体",
        )
        dq.set_defaults(func=_query)

        # ── update ───────────────────────────────────────────────────
        du = sub.add_parser(
            "update",
            help="更新任务信息（form_url / 追加派发范围记录）",
        )
        du.add_argument("--task-id", required=True, help="任务 ID")
        du.add_argument("--form-url", default=None, help="更新表单分享链接")
        du.add_argument(
            "--scope",
            default=None,
            metavar="SCOPE_DESC",
            help="追加一条派发范围记录到 dispatch_log（如：华东大区）",
        )
        du.set_defaults(func=_update)

        # ── set-status ───────────────────────────────────────────────
        ds = sub.add_parser(
            "set-status",
            help="更新任务状态（进行中 / 已完成 / 已禁用）",
        )
        ds.add_argument("--task-id", required=True, help="任务 ID")
        ds.add_argument(
            "--set",
            required=True,
            dest="new_status",
            choices=["进行中", "已完成", "部分失败", "已禁用"],
            help="目标状态",
        )
        ds.set_defaults(func=_status)

        # ── notifications ────────────────────────────────────────────
        dd = sub.add_parser(
            "notifications",
            help="查询任务通知明细，支持多维度过滤（JSON 输出）",
            description=(
                "查询任务通知明细，支持按状态 / 时间窗 / 滞留时长过滤（JSON 输出）。\n"
                "典型催办场景：配合 `--filter unfilled --stayed-over-minutes 30`，"
                "找出通知发出 30 分钟仍未填写的店，再走 `dispatch notify --only-pending` 二次催办。"
            ),
        )
        dd.add_argument("--task-id", required=True, help="任务 ID")
        dd.add_argument(
            "--filter",
            default=None,
            dest="status_filter",
            choices=["sent", "filled", "unfilled", "failed"],
            help=(
                "状态过滤：sent=已派发；filled=已填写；"
                "unfilled=未填写（等价于原 list-pending）；failed=失败"
            ),
        )
        dd.add_argument(
            "--notified-from",
            default=None,
            metavar="YYYY-MM-DD HH:mm",
            help="通知时间下限（含）",
        )
        dd.add_argument(
            "--notified-to",
            default=None,
            metavar="YYYY-MM-DD HH:mm",
            help="通知时间上限（含）",
        )
        dd.add_argument(
            "--stayed-over-minutes",
            type=int,
            default=None,
            metavar="N",
            help="通知发出后超过 N 分钟仍未填写的记录（催办场景）",
        )
        dd.add_argument("--limit", type=int, default=None, help="最多返回 N 条")
        dd.add_argument(
            "--fields",
            default=None,
            metavar="FIELD1,FIELD2,...",
            help="仅返回指定字段（逗号分隔），如 store_id,store_name,notify_status",
        )
        dd.add_argument(
            "--count-only",
            action="store_true",
            help="仅返回符合条件的总数 {\"total\": N}，不返回数据体",
        )
        dd.set_defaults(func=_notifications)

        # ── list-pending ─────────────────────────────────────────────
        # 兼容别名：内部调用 _detail（自动映射 filter=unfilled）
        dlp = sub.add_parser(
            "list-pending",
            help="[兼容别名] 查询某任务下『已通知未填写』的成员列表，等价于 `dispatch detail --filter unfilled`",
        )
        dlp.add_argument("--task-id", required=True, help="任务 ID")
        dlp.add_argument(
            "--limit",
            type=int,
            default=None,
            help="最多返回 N 条（默认全部返回）",
        )
        dlp.add_argument(
            "--fields",
            default=None,
            metavar="FIELD1,FIELD2,...",
            help="仅返回指定字段（逗号分隔），如 store_id,store_name,notify_status",
        )
        dlp.add_argument(
            "--count-only",
            action="store_true",
            help="仅返回符合条件的总数 {\"total\": N}，不返回数据体",
        )
        dlp.set_defaults(func=_list_pending_compat)

        # ── instances ────────────────────────────────────────────────
        # 查询动态任务实例表中的巡检记录，支持多维度过滤。
        di_inst = sub.add_parser(
            "instances",
            help="查询任务实例记录（动态任务表中的巡检记录），支持按字段过滤",
        )
        di_inst.add_argument("--task-id", required=True, help="任务 ID")
        di_inst.add_argument("--store-id", default=None, help="按门店 ID 过滤")
        di_inst.add_argument(
            "--filter",
            nargs=2,
            action="append",
            metavar=("FIELD", "VALUE"),
            dest="field_filters",
            help="按字段值过滤，格式 --filter 字段名 值，可多次使用",
        )
        di_inst.add_argument(
            "--filter-empty",
            nargs="+",
            metavar="FIELD",
            help="过滤指定字段为空的记录",
        )
        di_inst.add_argument(
            "--filter-not-empty",
            nargs="+",
            metavar="FIELD",
            help="过滤指定字段不为空的记录",
        )
        di_inst.add_argument(
            "--limit", type=int, default=None, help="最多返回条数",
        )
        di_inst.add_argument(
            "--fields",
            default=None,
            metavar="FIELD1,FIELD2,...",
            help="仅输出指定字段（逗号分隔）",
        )
        di_inst.add_argument(
            "--count-only",
            action="store_true",
            help='仅输出总数 {"count": N}，不返回数据体',
        )
        di_inst.set_defaults(func=_instances)

        # ── update-instance ──────────────────────────────────────────
        # 更新动态任务实例表中的自定义字段值（不可修改骨架字段）。
        di_upd = sub.add_parser(
            "update-instance",
            help="更新任务实例记录中的自定义字段值（不可修改骨架字段）",
        )
        di_upd.add_argument("--task-id", required=True, help="任务 ID")
        di_upd.add_argument(
            "--record-id", required=True, help="记录 ID（recordId）",
        )
        di_upd.add_argument(
            "--set",
            nargs=2,
            action="append",
            metavar=("FIELD", "VALUE"),
            dest="field_values",
            required=True,
            help="设置字段值，格式 --set 字段名 值，可多次使用",
        )
        di_upd.set_defaults(func=_update_instance)

def _add_task_args(p: argparse.ArgumentParser) -> None:
    """装配 ``dispatch task`` / ``dispatch notify`` 共用参数。

    抽出到独立函数是为了让 ``notify`` 别名与 ``task`` 在 argparse 层面
    100% 等价（同样的参数集、同样的默认值、同样的 choices），任何后续
    参数变动只需改一处。
    """
    p.add_argument(
        "--task-id",
        required=True,
        help="任务 ID（必须已存在；用 `dispatch init` 创建）",
    )
    p.add_argument(
        "--form-url",
        default=None,
        help=(
            "表单分享链接（含 /notable/share/form/）。"
            "传入合法链接时自动写入任务记录的 form_url 字段，"
            "无需手动通过 dws aitable record update 写入。"
        ),
    )
    p.add_argument(
        "--all",
        action="store_true",
        dest="send_all",
        help=(
            "向所有活跃门店派发（全量派发）。"
            "必须显式传入此参数才会全量派发，防止遗漏 --target-store-ids 导致误发全量。"
            "与 --target-store-ids / --tags / --only-pending 互斥。"
        ),
    )
    p.add_argument(
        "--target-store-ids",
        default=None,
        help="仅派发指定门店，逗号分隔，如 S001,S002",
    )
    p.add_argument(
        "--on-duplicate",
        default=None,
        choices=["ask", "resend", "skip"],
        help=(
            "重复通知策略：skip=跳过已通知；resend=全部重发；ask=逐店询问。"
            "未传时 CLI 会先探测当前任务是否已有通知记录，若有则直接退出"
            "并输出结构化提示（status=need_user_decision），由 Agent 把"
            "「跳过」/「重发」两个选项呈现给用户决策后再带参重新执行。"
        ),
    )
    p.add_argument(
        "--only-pending",
        action="store_true",
        help=(
            "仅向『已通知未填写』的成员重发通知。启用时：\n"
            "  • 自动用『通知表 sent - 巡检表已存在』计算目标，"
            "无需手动 --target-store-ids；\n"
            "  • 自动忽略 --on-duplicate（强制 resend，因为目标本身就是已通知）；\n"
            "  • 自动跳过 need_user_decision 探测（无须二次确认）。\n"
            "适用于：用户要求『重新通知未填写的人』的场景。"
        ),
    )
    p.add_argument(
        "--cooldown-seconds",
        type=int,
        default=1800,
        help=(
            "冷却保护窗口（秒，默认 1800=半小时）。"
            "上次 notified_at 在该窗口内的门店将被静默跳过，"
            "避免短时间内重复骚扰。传 0 禁用冷却。"
            "通常与 --only-pending 一起使用。"
        ),
    )
    p.add_argument(
        "--scope",
        default=None,
        metavar="SCOPE_DESC",
        help=(
            "派发范围描述（如：华东大区）。"
            "派发完成后自动追加到任务记录的 dispatch_log 字段（JSON 数组），"
            "便于后续查询每次派发的覆盖范围。"
        ),
    )
    p.add_argument(
        "--tags",
        default=None,
        help=(
            "按标签过滤目标门店（逗号分隔，如：华北,示范店），任意命中即发送。"
            "与 --target-store-ids 互斥。"
        ),
    )
    p.add_argument(
        "--extra-info",
        default=None,
        metavar="TEXT",
        help=(
            "本次派发附加给店长的额外信息，会渲染到消息模板的 {额外信息} / "
            "{extra_info} 占位符；模板未使用占位符时，自动追加到正文末尾。"
            "传入后会覆盖任务记录已持久化的 extra_info；不传则沿用任务记录中"
            "上一次派发时写入的内容（提醒消息也会带上同一份内容）。"
        ),
    )
    p.add_argument(
        "--message-override",
        default=None,
        metavar="MARKDOWN",
        help=(
            "一次性覆盖派发消息正文（Markdown），仅本次派发生效，"
            "不会写入模板表的 dispatch_message 字段。"
            "与 --message-override-file 互斥。"
        ),
    )
    p.add_argument(
        "--message-override-file",
        default=None,
        metavar="FILE",
        help=(
            "从文件读取一次性覆盖的派发消息正文（Markdown），仅本次派发生效，"
            "不会写入模板表的 dispatch_message 字段。"
            "与 --message-override 互斥。"
        ),
    )


# ──────────────────────────────────────────────────────────────────────
# init（唯一建表入口）
# ──────────────────────────────────────────────────────────────────────

def _init(args: argparse.Namespace, ctx: AppContext) -> int:
    """``dispatch init``：创建或复用派发任务，输出 task_context。

    这是**唯一能建表的入口**。task_context 字段：
      task_id, instance_table_name, instance_table_id,
      notification_table_name, notification_table_id,
      form_url, form_view_id, is_new, is_table_shared

    复用规则（固定）：当前周期内有任务 → 返回已有任务；无任务 → 新建。
    周期由模版的 ``dispatch_cycle`` 字段控制（per_day / per_week / per_month）。
    """
    tpl = ctx.template_manager.get_template(args.template_id)
    if not tpl:
        err(f"模板不存在: {args.template_id}")
        return 1

    # 固定使用 latest 策略：当前周期内有任务则复用，无则新建
    task_context = ctx.dispatcher.ensure_task(
        tpl,
        reuse_strategy="latest",
        form_url=getattr(args, "form_url", None),
        force_new=False,
        extra_info=getattr(args, "extra_info", None),
    )
    # 输出时去掉内部字段 notif_field_map（太冗长，Agent 无需关心）
    output = {k: v for k, v in task_context.items() if k != "notif_field_map"}
    print_json(output)

    if not task_context.get("form_url"):
        task_id = task_context.get("task_id", "<TASK_ID>")
        template_id = task_context.get("template_id", "<TPL_ID>")
        warn(
            "暂时无法自动获取表单分享链接，可能是 AI 表格服务同步延迟导致。\n"
            "\n"
            "━━━ 首选方案：引导用户发布表单后系统自动获取 ━━━\n"
            "请引导用户在 AI 表格中打开表单视图，完成以下操作：\n"
            "  1. 将「店长」字段设为必填（点击字段右侧设置图标，开启「必填」开关）\n"
            "  2. 点击右上角「分享」按钮开启分享开关\n"
            "用户完成后回复「已发布」，然后重新执行：\n"
            f"  cd <SKILL_DIR> && uv run python scripts/cli.py dispatch init "
            f"--template-id {template_id} --reuse {task_id}\n"
            "系统会自动通过 shareUuid 获取分享链接。\n"
            "\n"
            "━━━ 备选方案：用户手动复制分享链接 ━━━\n"
            "如果重新执行 dispatch init 后仍然无法自动获取，\n"
            "请用户在表单视图中点击「分享」→ 复制分享链接，然后执行：\n"
            f"  cd <SKILL_DIR> && uv run python scripts/cli.py dispatch notify "
            f"--task-id {task_id} --form-url \"<用户粘贴的分享链接>\"\n"
            "合法链接格式：https://docs.dingtalk.com/notable/share/form/v01...?source=link\n"
            "\n"
            "⚠️ Agent 绝对不要自行拼接或猜测分享链接格式！（H13）\n"
            f"（任务 ID: {task_id}）"
        )
        return 1

    return 0


# ──────────────────────────────────────────────────────────────────────
# task（派发入口；融合原 _notify 的全部逻辑；不接受 --template-id）
# ──────────────────────────────────────────────────────────────────────

def _task(args: argparse.Namespace, ctx: AppContext) -> int:
    """``dispatch task`` / ``dispatch notify``：按 task_id 派发任务。

    这是**唯一的派发入口**，物理上不能建表（参数层不接受 --template-id）。
    流程：
      1. ``_find_task_by_id`` 兜底校验 task_id 存在；找不到则友好报错并返回 1。
         （**不会**降级为新建任务，避免重复建表的故障再次发生。）
      2. 用 ``ensure_task(reuse_strategy=task_id, form_url=...)`` 加载完整
         task_context（含 notif_field_map）。由于第 1 步已校验存在，
         ``ensure_task`` 在此分支不会触发降级新建。
      3. only-pending / decision-mode 分支处理。
      4. ``notify_targets`` 完成实际派发。
    """
    task_id = args.task_id

    # 1) 兜底校验 task_id 存在 —— 找不到直接报错，绝不降级新建。
    task_record = _find_task_by_id(ctx, task_id)
    if not task_record:
        err(
            f"找不到任务记录: {task_id}\n"
            "可能原因：\n"
            "  • task_id 拼写错误（请用 `dispatch list-pending --task-id <ID>` "
            "或检查任务记录表确认）\n"
            "  • 该任务尚未创建 → 请先执行 "
            "`dispatch init --template-id <TPL_ID>` 创建任务\n"
            "本命令不会自动创建任务，避免重复建表。"
        )
        return 1

    template_id = task_record.get("template_id", "")
    tpl = ctx.template_manager.get_template(template_id)
    if not tpl:
        err(f"模板不存在: {template_id}（来自任务记录 {task_id}）")
        return 1

    # 2) 直接把已知的 task_record 传给 ensure_task，跳过所有查询逻辑。
    # 不能用 reuse_strategy=task_id，因为 _resolve_existing_task 内部只查
    # 当天任务（query_today_tasks），跨天的 task_id 会找不到并降级为新建，
    # 导致重复建表（已复现：昨天的任务今天执行 dispatch notify 会建今天的表）。
    task_context = ctx.dispatcher.ensure_task(
        tpl,
        existing_task=task_record,
        form_url=getattr(args, "form_url", None),
    )
    if not task_context.get("form_url"):
        err(
            f"任务 {task_id} 的 form_url 未配置。\n"
            "请先在 AI 表格中打开表单视图，完成以下操作：\n"
            "  1. 将「店长」字段设为必填（点击字段右侧设置图标，开启「必填」开关）\n"
            "  2. 点击右上角「分享」按钮开启分享并获取分享链接（格式：含 /notable/share/form/）\n"
            "然后通过以下任一方式传入链接：\n"
            f"  方式 1（推荐）：dispatch task --task-id {task_id} --form-url <分享链接>\n"
            "  方式 2：通过 dws aitable record update 将链接写入任务记录的 form_url 字段"
        )
        return 1

    only_pending = bool(getattr(args, "only_pending", False))
    cooldown_seconds = getattr(args, "cooldown_seconds", 1800)
    send_all = bool(getattr(args, "send_all", False))

    # 2.5) 范围校验：必须显式指定发送范围，防止误发全量
    has_scope = (
        send_all
        or only_pending
        or getattr(args, "target_store_ids", None)
        or getattr(args, "tags", None)
    )
    if not has_scope:
        err(
            "未指定发送范围，拒绝执行。请显式指定以下参数之一：\n"
            "  --all                 向所有活跃门店派发（全量）\n"
            "  --target-store-ids    仅向指定门店派发（逗号分隔 store_id）\n"
            "  --tags                按标签过滤目标门店\n"
            "  --only-pending        仅向已通知未填写的门店重发\n"
            "\n"
            "示例：\n"
            f"  dispatch notify --task-id {task_id} --all\n"
            f"  dispatch notify --task-id {task_id} --target-store-ids S001,S002"
        )
        return 1

    # 互斥校验：--all 与 --target-store-ids / --tags / --only-pending 互斥
    if send_all and (getattr(args, "target_store_ids", None) or getattr(args, "tags", None) or only_pending):
        err(
            "--all 与 --target-store-ids / --tags / --only-pending 互斥，"
            "请只选择一种范围控制方式。"
        )
        return 1

    # 3) only-pending 模式：跳过 decision 探测、强制 resend
    # 该模式下，目标本身就是『已通知未填写』，重发是天然语义，无需用户决策。
    if only_pending:
        if args.on_duplicate is not None and args.on_duplicate != "resend":
            warn(
                f"--only-pending 已启用，--on-duplicate={args.on_duplicate} 将被忽略，"
                "强制按 resend 处理（目标本身就是已通知未填写的成员）。"
            )
        args.on_duplicate = "resend"
    else:
        # 未传 --on-duplicate 时，先探测当前任务是否有已通知门店：
        # 命中重复 → 输出结构化提示让 Agent 询问用户「跳过 / 重发」后再带参重跑；
        # 没有重复 → 按 resend 默认走（行为等价于全新派发，不会真重发）。
        if args.on_duplicate is None:
            decision = _maybe_prompt_duplicate_decision(
                ctx, task_id, task_context, tpl, None,
            )
            if decision is not None:
                return decision
            args.on_duplicate = "resend"

    # 3.5) 状态校验：已禁用的任务拒绝派发
    task_status = task_record.get("status", "")
    if task_status == "已禁用":
        err(
            f"任务 {task_id} 的状态为「已禁用」，拒绝派发。\n"
            "如需恢复派发，请先执行：\n"
            f"  dispatch status --task-id {task_id} --set 进行中"
        )
        return 1

    # 4) 解析 --message-override（一次性覆盖，不写入模板表）
    message_override_raw = getattr(args, "message_override", None)
    message_override_file = getattr(args, "message_override_file", None)
    if message_override_raw and message_override_file:
        err("--message-override 与 --message-override-file 不能同时使用")
        return 2
    message_override = message_override_raw
    if message_override_file:
        from pathlib import Path
        override_path = Path(message_override_file)
        if not override_path.exists():
            err(f"--message-override-file 指向的文件不存在: {message_override_file}")
            return 2
        try:
            message_override = override_path.read_text(encoding="utf-8")
        except OSError as exc:
            err(f"--message-override-file 读取失败: {exc}")
            return 2

    # 5) 实际派发
    scope_desc = getattr(args, "scope", None)
    target_store_ids = _parse_store_ids(getattr(args, "target_store_ids", None))
    tags = [t.strip() for t in args.tags.split(",") if t.strip()] if getattr(args, "tags", None) else None
    summary = ctx.dispatcher.notify_targets(
        tpl,
        task_context,
        duplicate_strategy=args.on_duplicate,
        only_pending=only_pending,
        cooldown_seconds=cooldown_seconds,
        scope_desc=scope_desc,
        target_store_ids=target_store_ids,
        tags=tags,
        extra_info=getattr(args, "extra_info", None),
        message_override=message_override,
    )
    print_json(summary.to_dict())
    return 0 if summary.failed == 0 else 1


# ──────────────────────────────────────────────────────────────────────
# list-pending
# ──────────────────────────────────────────────────────────────────────

def _list_pending(args: argparse.Namespace, ctx: AppContext) -> int:
    """``dispatch list-pending``：查询某任务下『已通知未填写』的成员列表。

    判定规则：通知表中 ``notify_status=sent`` 但巡检表中无对应 store_id 记录。
    输出 JSON：
        {
          "task_id": "...",
          "instance_table_id": "...",
          "notification_table_id": "...",
          "pending_count": 3,
          "pending_members": [
            {"store_id": "...", "store_name": "...", "manager_name": "...",
             "notified_at": "...", "send_count": 2, "notification_id": "..."}
          ]
        }
    """
    task_id = args.task_id

    task_record = _find_task_by_id(ctx, task_id)
    if not task_record:
        err(
            f"未找到任务记录: {task_id}。\n"
            "请确认 task_id 正确，或先执行 `dispatch init --template-id <TPL_ID>` 创建任务。"
        )
        return 1

    template_id = task_record.get("template_id", "")
    tpl = ctx.template_manager.get_template(template_id)
    if not tpl:
        err(f"模板不存在: {template_id}（来自任务记录 {task_id}）")
        return 1

    # 直接把已知的 task_record 传给 ensure_task，跳过跨天查询逻辑，
    # 避免昨天的任务今天执行 list-pending 时被误判为"找不到"而降级新建。
    task_context = ctx.dispatcher.ensure_task(tpl, existing_task=task_record)

    instance_table_id = task_context.get("instance_table_id", "")
    notification_table_id = task_context.get("notification_table_id", "")

    pending = ctx.dispatcher.query_pending_notifications(
        task_id=task_id,
        notification_table_id=notification_table_id,
        task_table_id=instance_table_id,
    )

    limit = getattr(args, "limit", None)
    if limit is not None and limit > 0:
        pending = pending[:limit]

    print_json({
        "task_id": task_id,
        "instance_table_id": instance_table_id,
        "notification_table_id": notification_table_id,
        "pending_count": len(pending),
        "pending_members": pending,
    })
    return 0


# ──────────────────────────────────────────────────────────────────────
# query（任务查询）
# ──────────────────────────────────────────────────────────────────────

def _query(args: argparse.Namespace, ctx: AppContext) -> int:
    """``dispatch query``：查询任务列表，支持多维度过滤。

    输出 JSON 格式的任务列表，按 task_date 倒序排列。
    """
    from datetime import date as _date

    template_id = getattr(args, "template_id", None)
    status = getattr(args, "status", None)
    date_from = getattr(args, "date_from", None)
    date_to = getattr(args, "date_to", None)
    limit = getattr(args, "limit", None)
    last_n = getattr(args, "last_n", None)
    today = getattr(args, "today", False)

    # --today 快捷参数
    if today:
        today_str = _date.today().isoformat()
        date_from = date_from or today_str
        date_to = date_to or today_str

    # --last-n 需配合 --template-id
    if last_n is not None:
        if not template_id:
            err("--last-n 需配合 --template-id 使用")
            return 1
        limit = last_n

    tasks = ctx.dispatcher.query_tasks(
        template_id=template_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )
    fields = getattr(args, "fields", None)
    count_only = getattr(args, "count_only", False)
    result = apply_list_options(tasks, fields=fields, count_only=count_only)
    if count_only:
        print_json(result)
    else:
        print_json({"count": len(result), "tasks": result})
    return 0

# ──────────────────────────────────────────────────────────────────────
# update（更新任务信息）
# ──────────────────────────────────────────────────────────────────────

def _update(args: argparse.Namespace, ctx: AppContext) -> int:
    """``dispatch update``：更新任务信息（form_url / 追加派发范围记录）。"""
    task_id = args.task_id
    form_url = getattr(args, "form_url", None)
    scope = getattr(args, "scope", None)

    if form_url is None and scope is None:
        err("请至少提供 --form-url 或 --scope 中的一个参数")
        return 1

    ok = ctx.dispatcher.update_task(
        task_id,
        form_url=form_url,
        scope_desc=scope,
    )
    if ok:
        print_json({"status": "ok", "task_id": task_id})
        return 0
    else:
        err(f"更新任务 {task_id} 失败，请检查 task_id 是否正确")
        return 1

# ──────────────────────────────────────────────────────────────────────
# status（更新任务状态）
# ──────────────────────────────────────────────────────────────────────

def _status(args: argparse.Namespace, ctx: AppContext) -> int:
    """``dispatch status``：更新任务状态。"""
    task_id = args.task_id
    new_status = args.new_status

    ok = ctx.dispatcher.update_task(task_id, status=new_status)
    if ok:
        print_json({"status": "ok", "task_id": task_id, "new_status": new_status})
        return 0
    else:
        err(f"更新任务 {task_id} 状态失败，请检查 task_id 是否正确")
        return 1

# ──────────────────────────────────────────────────────────────────────
# detail（通知明细查询）
# ──────────────────────────────────────────────────────────────────────

def _notifications(args: argparse.Namespace, ctx: AppContext) -> int:
    """``dispatch notifications``：查询任务通知明细，支持多维度过滤。

    输出 JSON：
        {
          "task_id": "...",
          "instance_table_id": "...",
          "notification_table_id": "...",
          "count": 3,
          "members": [...]
        }
    """
    task_id = args.task_id
    status_filter = getattr(args, "status_filter", None)
    notified_from = getattr(args, "notified_from", None)
    notified_to = getattr(args, "notified_to", None)
    stayed_over_minutes = getattr(args, "stayed_over_minutes", None)
    limit = getattr(args, "limit", None)

    task_record = _find_task_by_id(ctx, task_id)
    if not task_record:
        err(
            f"未找到任务记录: {task_id}。\n"
            "请确认 task_id 正确，或先执行 `dispatch init --template-id <TPL_ID>` 创建任务。"
        )
        return 1

    template_id = task_record.get("template_id", "")
    tpl = ctx.template_manager.get_template(template_id)
    if not tpl:
        err(f"模板不存在: {template_id}（来自任务记录 {task_id}）")
        return 1

    task_context = ctx.dispatcher.ensure_task(tpl, existing_task=task_record)
    instance_table_id = task_context.get("instance_table_id", "")
    notification_table_id = task_context.get("notification_table_id", "")

    members = ctx.dispatcher.query_notification_details(
        notification_table_id=notification_table_id,
        instance_table_id=instance_table_id,
        status_filter=status_filter,
        notified_from=notified_from,
        notified_to=notified_to,
        stayed_over_minutes=stayed_over_minutes,
        limit=limit,
    )

    fields = getattr(args, "fields", None)
    count_only = getattr(args, "count_only", False)
    result = apply_list_options(members, fields=fields, count_only=count_only)
    if count_only:
        print_json(result)
    else:
        print_json({
            "task_id": task_id,
            "instance_table_id": instance_table_id,
            "notification_table_id": notification_table_id,
            "count": len(result),
            "members": result,
        })
    return 0

# ──────────────────────────────────────────────────────────────────────
# list-pending 兼容别名
# ──────────────────────────────────────────────────────────────────────

def _list_pending_compat(args: argparse.Namespace, ctx: AppContext) -> int:
    """``dispatch list-pending``：兼容别名，内部调用 _notifications（filter=unfilled）。

    等价于 ``dispatch notifications --task-id <ID> --filter unfilled``。
    保留以兼容 Agent 历史指令，不破坏现有调用链。
    """
    # 注入 status_filter=unfilled，其余参数透传
    args.status_filter = "unfilled"
    args.notified_from = None
    args.notified_to = None
    args.stayed_over_minutes = None
    return _notifications(args, ctx)

# ──────────────────────────────────────────────────────────────────────
# 内部辅助
# ──────────────────────────────────────────────────────────────────────

def _maybe_prompt_duplicate_decision(
    ctx: AppContext,
    task_id: str,
    task_context: dict,
    tpl: dict,
    target_ids: Optional[List[str]],
) -> Optional[int]:
    """``dispatch task`` 在未传 ``--on-duplicate`` 时的重复探测。

    Returns:
        - ``None`` → 没有已通知门店，调用方应继续按默认（resend）派发；
        - ``int`` → 已输出 ``status=need_user_decision`` JSON，调用方应直接返回此退出码。

    设计目的：
        把「是否覆盖已通知用户」的决策权交还给用户。CLI 不直接动作，
        而是通过结构化输出让 Agent 把两个选项呈现给用户。
    """
    notification_table_id = task_context.get("notification_table_id", "")
    if not notification_table_id:
        return None

    try:
        dispatched_ids = ctx.dispatcher.query_dispatched_store_ids(
            notification_table_id, task_id
        )
    except Exception as exc:  # noqa: BLE001 — 探测失败不应阻断派发流程
        warn(
            f"探测已通知门店失败（将按默认策略全量派发，可能重复发送通知）：{exc}"
        )
        return None

    # 计算「目标门店中已通知的」交集
    if target_ids:
        already_sent = [sid for sid in target_ids if sid in dispatched_ids]
    else:
        # 不限制目标 → 解析模板全部目标后求交集
        try:
            all_targets = ctx.dispatcher._resolve_targets(tpl) or []
        except Exception as exc:  # noqa: BLE001
            warn(
                f"解析模板目标门店失败（将按默认策略全量派发，可能通知范围不符合预期）：{exc}"
            )
            return None
        all_target_ids = [t.get("store_id") for t in all_targets if t.get("store_id")]
        already_sent = [sid for sid in all_target_ids if sid in dispatched_ids]

    if not already_sent:
        return None

    # 命中重复 → 输出结构化提示，让 Agent 询问用户后再带参重跑
    print_json({
        "status": "need_user_decision",
        "task_id": task_id,
        "already_sent_store_ids": already_sent,
        "already_sent_count": len(already_sent),
        "message": (
            f"任务 {task_id} 中有 {len(already_sent)} 个门店已通知过，"
            "请询问用户选择处理策略，然后重新执行 dispatch task 时携带 "
            "--on-duplicate 参数。"
        ),
        "options": [
            {
                "id": "skip",
                "label": "跳过已通知门店，仅补发未通知的",
                "command_suffix": "--on-duplicate skip",
            },
            {
                "id": "resend",
                "label": "全部重发（已通知门店也会再次收到消息）",
                "command_suffix": "--on-duplicate resend",
            },
        ],
    })
    return 0


def _parse_store_ids(raw: Optional[str]) -> Optional[List[str]]:
    """将逗号分隔的门店 ID 字符串解析为列表；None 或空串返回 None。"""
    if not raw:
        return None
    ids = [s.strip() for s in raw.split(",") if s.strip()]
    return ids if ids else None


def _find_task_by_id(ctx: AppContext, task_id: str) -> Optional[dict]:
    """在任务记录表中按 task_id 精确查找一条记录，返回其 fields dict。

    实现要点：
    - 使用 dws filter 在服务端按 task_id 精确过滤，避免随任务记录表行数
      增长导致全表拉取超时（曾因全表拉取触发 aitable TIMEOUT_ERROR，最终
      被静默吞成"未找到任务记录"，误导用户以为 task_id 写错）。
    - filter 必须用 ``F.and_`` 包裹，否则 dws 会静默忽略 filter 等同于全表
      查询（参见 .aone_copilot/issue/aitable-filter-upsert-overwrite.md）。
    - DwsError 与其他异常分别处理，把底层错误（含 trace_id / 超时码）原样
      暴露给用户，便于排查。
    """
    from scripts.domain import filters as F
    from scripts.domain import schema as S
    from scripts.domain.exceptions import DwsError
    from scripts.domain.records import extract_records, values_by_name

    try:
        task_table_id = ctx.dispatcher.cache.get_table_id(
            ctx.dispatcher.base_id, S.TASK_RECORD_TABLE
        )
    except Exception as exc:
        err(
            f"未找到任务记录表（{S.TASK_RECORD_TABLE}）：{exc}\n"
            "请先运行 init validate 检查初始化状态。"
        )
        return None

    try:
        task_id_field_id = ctx.dispatcher.cache.get_field_id(
            ctx.dispatcher.base_id, S.TASK_RECORD_TABLE, "task_id"
        )
        payload = ctx.dispatcher.client.aitable_record_query(
            ctx.dispatcher.base_id,
            task_table_id,
            # 必须用 F.and_ 包裹单条件，否则 dws 会静默忽略 filter 退化为全表查询
            F.and_(F.eq(task_id_field_id, task_id)),
            limit=1,
        )
        records = extract_records(payload)
        for r in records:
            # cells 以 fieldId 为 key，需翻译回 fieldName 才能按名称取值
            fields = values_by_name(
                ctx.dispatcher.cache,
                ctx.dispatcher.base_id,
                S.TASK_RECORD_TABLE,
                r,
            )
            # 服务端已按 task_id 精确过滤，此处再校验一次防御性兜底
            if fields.get("task_id") == task_id:
                return {
                    "record_id": r.get("recordId") or r.get("id", ""),
                    **fields,
                }
        return None
    except DwsError as exc:
        # 把底层错误（含 trace_id / 超时码 / stderr）原样暴露，避免被误读为"task_id 不存在"
        err(
            f"查询任务记录 {task_id} 失败（dws 调用异常，非 task_id 不存在）：{exc}\n"
            "常见原因：aitable 服务端超时（server_error_code=TIMEOUT_ERROR）"
            "或网络波动，可稍后重试。"
        )
        return None
    except Exception as exc:
        err(f"查询任务记录 {task_id} 失败: {exc}")
        return None


# ---------------------------------------------------------------------------
# dispatch instances — 查询任务实例记录
# ---------------------------------------------------------------------------

def _instances(args: argparse.Namespace, ctx: AppContext) -> int:
    """``dispatch instances``：查询任务实例记录（动态任务表中的巡检记录）。"""
    field_filters = dict(args.field_filters) if args.field_filters else None
    results = ctx.dispatcher.query_instances(
        args.task_id,
        field_filters=field_filters,
        filter_empty=getattr(args, "filter_empty", None),
        filter_not_empty=getattr(args, "filter_not_empty", None),
        store_id=args.store_id,
        limit=args.limit,
    )
    if args.count_only:
        print_json({"count": len(results)})
        return 0
    if args.fields:
        keep = [f.strip() for f in args.fields.split(",")]
        results = [
            {k: v for k, v in r.items() if k in keep or k == "record_id"}
            for r in results
        ]
    print_json(results)
    return 0


# ---------------------------------------------------------------------------
# dispatch update-instance — 更新实例字段值
# ---------------------------------------------------------------------------

def _update_instance(args: argparse.Namespace, ctx: AppContext) -> int:
    """``dispatch update-instance``：更新任务实例记录中的自定义字段值。"""
    field_values = dict(args.field_values)
    try:
        ok = ctx.dispatcher.update_instance_fields(
            args.task_id,
            args.record_id,
            field_values,
        )
    except Exception as exc:
        err(str(exc))
        return 1
    if ok:
        print_json({"status": "ok", "record_id": args.record_id})
        return 0
    err("更新失败，请检查 task_id 和 record_id 是否正确")
    return 1
