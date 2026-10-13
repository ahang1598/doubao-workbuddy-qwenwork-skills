"""``template`` 命令族：巡店模版 CRUD。

子命令：``create / update / enable / disable / get / list``

消息相关字段（重构后，3 个，全部可在 create / update 时配置）：

- ``--message-title``：派发消息标题（钉钉消息列表显示），第 N 次提醒（N≥2）
  时由 messenger 自动加 ``【第N次提醒】`` 前缀复用
- ``--description`` / ``--description-file``：模板介绍文本（管理后台展示用，
  不再参与消息渲染）
- ``--dispatch-message`` / ``--dispatch-message-file``：派发消息正文 Markdown
  模板，提醒消息复用同一份模板

所有 ``-file`` 参数与同名直接参数互斥。未配置的字段在发送消息时由
:mod:`scripts.domain.message_defaults` 提供内置 Markdown 默认文案。
``remind_topic`` / ``remind_message`` 字段已废弃，老库残留字段会被代码完全忽略。
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from scripts.app import AppContext
from scripts.commands.base import BaseCommand
from scripts.commands.registry import register_command
from scripts.utils.output import apply_list_options, err, ok, print_json

logger = logging.getLogger(__name__)


@register_command
class TemplateCommand(BaseCommand):
    name = "template"
    help = "巡店模版维护"

    def configure(self, parser: argparse.ArgumentParser) -> None:
        sub = parser.add_subparsers(dest="subcommand", required=True)

        tc = sub.add_parser("create", help="创建模版")
        tc.add_argument("--name", required=True)
        tc.add_argument(
            "--description",
            default=None,
            help=(
                "模板介绍文本（管理后台展示用，不参与消息渲染）。"
                "与 --description-file 二选一；如 create 时未配置，将以模板名兜底。"
            ),
        )
        tc.add_argument(
            "--description-file",
            default=None,
            help="从文件读取模板介绍文本（推荐用于长介绍）",
        )
        tc.add_argument(
            "--dispatch-message",
            default=None,
            help=(
                "派发消息正文 Markdown 模板，提醒消息复用同一份模板。"
                "支持 {店长姓名}/{门店名称}/{填写链接}/{额外信息} 等占位符。"
                "未配置时由 messenger 在发送时 fallback 到默认模板。"
                "与 --dispatch-message-file 二选一。"
            ),
        )
        tc.add_argument(
            "--dispatch-message-file",
            default=None,
            help="从文件读取派发消息 Markdown 模板（推荐用于长正文）",
        )

        tc.add_argument(
            "--custom-fields",
            required=True,
            help=(
                "自定义巡检字段定义（必填，至少一个），JSON 数组字符串，如 "
                "'[{\"name\":\"陈列情况\",\"type\":\"singleSelect\","
                "\"options\":[\"正常\",\"异常\"]}]'"
            ),
        )
        tc.add_argument("--target-store-ids", default=None)
        tc.add_argument("--target-store-filter", default=None, help="JSON 字符串")
        tc.add_argument("--summary-receivers", default=None, help="逗号分隔 UserID")
        tc.add_argument("--remind-time", default=None, help="cron 表达式")
        tc.add_argument("--created-by", default=None)
        tc.add_argument(
            "--disabled", action="store_true", help="创建后立即设为 disabled"
        )
        # 消息相关字段（4 个，全部可选；未配置时由 messenger fallback 到默认 Markdown 文案）
        tc.add_argument(
            "--message-title",
            default=None,
            help=(
                "派发消息标题（钉钉消息列表显示），支持 {任务名称} 等占位符。"
                "提醒消息复用同一份标题，第 N 次提醒（N≥2）由 messenger 自动加 "
                "【第N次提醒】前缀。"
            ),
        )
        tc.add_argument(
            "--granularity",
            default=None,
            choices=["per_year", "per_month"],
            help=(
                "任务粒度：per_year=按年（默认，全年共用一张巡检表）；"
                "per_month=按月（每月独立建表）"
            ),
        )
        tc.add_argument(
            "--expected-duration",
            default=None,
            metavar="DURATION",
            help=(
                "期望完成时长，格式：Xh / Xm / XhYm，如 2h、30m、1h30m。"
                "创建任务时自动计算截止时间（deadline = 派发时间 + 时长），"
                "并在通知消息中展示给店长。"
            ),
        )
        tc.set_defaults(func=_create)

        # ── template preview ──────────────────────────────────────────
        tp = sub.add_parser(
            "preview",
            help=(
                "生成模版创建预览（只读，不写数据）。"
                "输出包含完整的 user_facing_preview（配置概要 + 派发消息模板），"
                "Agent 应原封不动展示给用户确认后再执行 template create。"
            ),
        )
        tp.add_argument("--name", required=True, help="模版名称")
        tp.add_argument(
            "--custom-fields",
            required=True,
            help="自定义巡检字段定义，JSON 数组字符串",
        )
        tp.add_argument(
            "--scene",
            default=None,
            choices=["inspection", "morning-meeting", "inventory"],
            help=(
                "业务场景。传入后自动生成场景化的派发消息模板。"
                "inspection=巡店检查；morning-meeting=早会；inventory=盘点。"
                "不传则使用通用默认模板。"
            ),
        )
        tp.add_argument(
            "--granularity",
            default=None,
            choices=["per_year", "per_month"],
            help="任务粒度：per_year=按年（默认）；per_month=按月",
        )
        tp.add_argument(
            "--expected-duration",
            default=None,
            metavar="DURATION",
            help="期望完成时长，格式：Xh / Xm / XhYm",
        )
        tp.add_argument(
            "--dispatch-message",
            default=None,
            help="手动指定派发消息模板（优先于 --scene 自动生成）",
        )
        tp.add_argument(
            "--dispatch-message-file",
            default=None,
            help="从文件读取派发消息模板",
        )
        tp.set_defaults(func=_preview)

        tu = sub.add_parser("update", help="按 template_id 更新模版字段")
        tu.add_argument("--template-id", required=True)
        tu.add_argument("--name", default=None)
        tu.add_argument(
            "--description",
            default=None,
            help="模板介绍文本（管理后台展示用，不参与消息渲染）",
        )
        tu.add_argument(
            "--description-file",
            default=None,
            help="从文件读取模板介绍文本",
        )
        tu.add_argument(
            "--dispatch-message",
            default=None,
            help=(
                "派发消息正文 Markdown 模板，提醒消息复用同一份模板。"
                "支持 {店长姓名}/{门店名称}/{填写链接}/{额外信息} 等占位符。"
            ),
        )
        tu.add_argument(
            "--dispatch-message-file",
            default=None,
            help="从文件读取派发消息 Markdown 模板",
        )
        tu.add_argument("--status", default=None, choices=["enabled", "disabled"])
        tu.add_argument("--target-store-ids", default=None)
        tu.add_argument("--target-store-filter", default=None)
        tu.add_argument("--custom-fields", default=None, help="JSON 数组字符串")
        tu.add_argument("--summary-receivers", default=None)
        tu.add_argument("--dispatch-time", default=None)
        tu.add_argument("--remind-time", default=None)
        tu.add_argument("--summary-time", default=None)
        # 消息相关字段
        tu.add_argument(
            "--message-title",
            default=None,
            help=(
                "派发消息标题（支持占位符）。提醒消息复用同一份标题，"
                "第 N 次提醒（N≥2）由 messenger 自动加 【第N次提醒】前缀。"
            ),
        )
        tu.add_argument(
            "--granularity",
            default=None,
            choices=["per_year", "per_month"],
            help="任务粒度：per_year=按年（默认，全年共用一张巡检表）；per_month=按月（每月独立建表）",
        )
        tu.add_argument(
            "--expected-duration",
            default=None,
            metavar="DURATION",
            help="期望完成时长，格式：Xh / Xm / XhYm，如 2h、30m、1h30m",
        )
        tu.set_defaults(func=_update)

        te = sub.add_parser("enable", help="启用模版")
        te.add_argument("--template-id", required=True)
        te.set_defaults(func=_enable)

        td = sub.add_parser("disable", help="禁用模版")
        td.add_argument("--template-id", required=True)
        td.set_defaults(func=_disable)

        tg = sub.add_parser("get", help="按 template_id 查询模版")
        tg.add_argument("--template-id", required=True)
        tg.set_defaults(func=_get)

        tl = sub.add_parser("list", help="列出所有模版")
        tl.add_argument("--only-enabled", action="store_true")
        tl.add_argument(
            "--limit",
            type=int,
            default=10,
            metavar="N",
            help="最多返回 N 条记录（默认 10，上限 100），防止数据量过大",
        )
        tl.add_argument(
            "--sort-by",
            default="created_at",
            metavar="FIELD",
            help="排序字段名（默认 created_at）",
        )
        tl.add_argument(
            "--sort-order",
            default="desc",
            choices=["asc", "desc"],
            help="排序方向：asc 升序 / desc 降序（默认 desc，最新在前）",
        )
        tl.add_argument(
            "--fields",
            default=None,
            metavar="FIELD1,FIELD2,...",
            help="仅返回指定字段（逗号分隔），如 template_id,name,status",
        )
        tl.add_argument(
            "--count-only",
            action="store_true",
            help="仅返回符合条件的总数 {\"total\": N}，不返回数据体",
        )
        tl.set_defaults(func=_list)

        ti = sub.add_parser(
            "instances",
            help="查看某模版管理的所有任务实例表（含活跃表和历史表）",
        )
        ti.add_argument("--template-id", required=True, help="模版 ID")
        ti.set_defaults(func=_instances)


# ---------------------------------------------------------------------------
# handlers
# ---------------------------------------------------------------------------

def _read_text_arg(direct_value, file_value, arg_label: str):
    """``--xxx`` 与 ``--xxx-file`` 互斥处理：返回 ``(text, error_msg)``。

    - 两个都给：返回 ``(None, error_msg)`` 表示冲突
    - 只给 file：读文件内容返回
    - 只给 direct：直接返回
    - 都没给：返回 ``(None, None)``，由调用方判断是否必填
    """
    if direct_value and file_value:
        return None, f"{arg_label} 与 {arg_label}-file 不能同时使用"
    if file_value:
        path = Path(file_value)
        if not path.exists():
            return None, f"{arg_label}-file 指向的文件不存在: {file_value}"
        try:
            return path.read_text(encoding="utf-8"), None
        except OSError as exc:
            return None, f"{arg_label}-file 读取失败: {exc}"
    return direct_value, None


def _preview(args, ctx: AppContext) -> int:
    """template preview：生成模版创建预览（只读，不写数据）。

    输出包含完整的 user_facing_preview（配置概要 + 派发消息模板），
    Agent 应原封不动展示给用户确认，用户确认后再执行 template create。
    """
    logger.debug("template preview 开始执行，参数: %s", vars(args))

    # 解析 custom_fields JSON
    custom_fields = None
    if args.custom_fields:
        try:
            custom_fields = json.loads(args.custom_fields)
        except json.JSONDecodeError as exc:
            err(f"--custom-fields JSON 解析失败: {exc}")
            return 2

    # 解析 dispatch_message（可选，用户手动指定优先于 scene 自动生成）
    dispatch_message, err_msg = _read_text_arg(
        getattr(args, "dispatch_message", None),
        getattr(args, "dispatch_message_file", None),
        "--dispatch-message",
    )
    if err_msg:
        err(err_msg)
        return 2

    granularity = getattr(args, "granularity", None) or "per_year"
    expected_duration = getattr(args, "expected_duration", None) or ""
    scene = getattr(args, "scene", None)

    # ── dispatch_message 自动生成 ─────────────────────────────────────
    # 优先级：用户显式传入 > --scene 场景化生成 > 默认通用模板兜底
    if not dispatch_message:
        from scripts.domain.message_defaults import (
            DEFAULT_DISPATCH_MESSAGE_MARKDOWN,
            build_scene_dispatch_message,
        )
        field_names = [f["name"] for f in (custom_fields or []) if f.get("name")]
        if scene:
            dispatch_message = build_scene_dispatch_message(scene, field_names)
            logger.debug("根据 scene=%s 自动生成 dispatch_message", scene)
        else:
            dispatch_message = DEFAULT_DISPATCH_MESSAGE_MARKDOWN
            logger.debug("使用默认通用模板兜底")

    # ── 生成预览数据 ──────────────────────────────────────────────────
    preview_data: dict = {
        "name": args.name,
        "granularity": granularity,
        "expected_duration": expected_duration or "（未设置）",
    }
    if scene:
        from scripts.domain.message_defaults import SCENE_DISPLAY_NAMES
        preview_data["scene"] = f"{scene}（{SCENE_DISPLAY_NAMES.get(scene, scene)}）"
    if custom_fields:
        preview_data["custom_fields_summary"] = [
            {
                "name": f.get("name", ""),
                "type": f.get("type", "text"),
                **({"ai_review": True} if f.get("ai_review") else {}),
            }
            for f in custom_fields
        ]

    # ── message_title 默认值 ─────────────────────────────────────────
    from scripts.domain.message_defaults import DEFAULT_DISPATCH_TITLE
    message_title = DEFAULT_DISPATCH_TITLE

    # ── 生成「可直接展示给用户的确认文本」──────────────────────────────
    confirm_lines: list = []
    confirm_lines.append("## 模版配置预览\n")
    confirm_lines.append(f"- **名称**：{args.name}")
    confirm_lines.append(f"- **消息标题**：{message_title}")
    confirm_lines.append(f"- **粒度**：{granularity}")
    confirm_lines.append(f"- **期望完成时长**：{expected_duration or '（未设置）'}")
    if scene:
        from scripts.domain.message_defaults import SCENE_DISPLAY_NAMES
        confirm_lines.append(f"- **场景**：{scene}（{SCENE_DISPLAY_NAMES.get(scene, scene)}）")
    confirm_lines.append("")
    if custom_fields:
        confirm_lines.append("### 自定义字段")
        confirm_lines.append("")
        confirm_lines.append("| # | 字段名 | 类型 | AI审核 |")
        confirm_lines.append("|---|--------|------|--------|")
        for idx, f in enumerate(custom_fields, 1):
            ai_flag = "✅" if f.get("ai_review") else "—"
            confirm_lines.append(f"| {idx} | {f.get('name','')} | {f.get('type','text')} | {ai_flag} |")
        confirm_lines.append("")
    confirm_lines.append("### 派发消息模板（店长收到的通知内容）\n")
    confirm_lines.append("```markdown")
    confirm_lines.append(dispatch_message.strip() if dispatch_message else "（空）")
    confirm_lines.append("```\n")
    confirm_lines.append("---")
    confirm_lines.append("⚠️ 请确认以上配置。如需修改（消息标题、派发消息模板等），请告知具体修改点。")
    confirm_lines.append("确认无误后回复「确认」，我将执行 `template create` 完成创建。")

    user_facing_preview = "\n".join(confirm_lines)

    output: dict = {
        "status": "pending_confirm",
        "preview": preview_data,
        "user_facing_preview": user_facing_preview,
        "message_title": message_title,
        "dispatch_message_template": dispatch_message,
        "next_step": (
            "请将 user_facing_preview 字段的内容【原封不动】展示给用户。"
            "该字段已经是格式化好的 Markdown 确认文本，包含：配置概要 + 消息标题 + 完整派发消息模板。\n"
            "⚠️ 禁止精简、省略或改写 user_facing_preview 中的任何内容——"
            "特别是「派发消息模板」部分，必须完整展示给用户（含代码块）。\n"
            "用户确认后，执行 template create 命令完成实际创建，"
            "必须通过 --message-title 传入消息标题（本输出的 message_title 字段），"
            "通过 --dispatch-message 传入派发消息模板（本输出的 dispatch_message_template 字段）。"
        ),
    }
    print_json(output)
    return 0


def _create(args, ctx: AppContext) -> int:
    logger.debug("template create 开始执行，参数: %s", vars(args))

    # 解析 custom_fields JSON
    custom_fields = None
    if args.custom_fields:
        try:
            custom_fields = json.loads(args.custom_fields)
        except json.JSONDecodeError as exc:
            err(f"--custom-fields JSON 解析失败: {exc}")
            return 2

    # 解析 description（模板介绍文本，留空时以模板名兜底）
    description, err_msg = _read_text_arg(
        args.description, args.description_file, "--description",
    )
    if err_msg:
        err(err_msg)
        return 2
    if not description:
        description = args.name

    # 解析 dispatch_message（派发消息正文 Markdown 模板）
    dispatch_message, err_msg = _read_text_arg(
        args.dispatch_message, args.dispatch_message_file, "--dispatch-message",
    )
    if err_msg:
        err(err_msg)
        return 2

    granularity = getattr(args, "granularity", None) or "per_year"
    expected_duration = getattr(args, "expected_duration", None) or ""

    # ── 防护校验：message_title 必须有值 ──────────────────────────────
    # message_title 是纯文本（不支持占位符），必须由 preview 生成后传入。
    # 如果模型跳过 preview 直接 create 而未传 --message-title，使用默认值兜底
    # 但输出警告提示应先跑 preview。
    message_title = getattr(args, "message_title", None)
    if not message_title:
        from scripts.domain.message_defaults import DEFAULT_DISPATCH_TITLE
        message_title = DEFAULT_DISPATCH_TITLE
        logger.warning(
            "未传 --message-title，使用默认值「%s」。"
            "建议先执行 template preview 获取完整预览再创建。",
            message_title,
        )

    # ── 防护校验：dispatch_message 必须有值 ────────────────────────────
    # 如果模型跳过 preview 直接 create 且未传 --dispatch-message，
    # 使用默认模板兜底但输出强烈警告。
    if not dispatch_message:
        from scripts.domain.message_defaults import DEFAULT_DISPATCH_MESSAGE_MARKDOWN
        dispatch_message = DEFAULT_DISPATCH_MESSAGE_MARKDOWN
        logger.warning(
            "未传 --dispatch-message，使用默认通用模板兜底。"
            "⚠️ 正确流程：应先执行 `template preview` 获取场景化消息模板，"
            "展示给用户确认后，再通过 --dispatch-message 传入。"
        )
        # 输出提示到 stderr（Agent 可见），但不阻断创建
        import sys
        print(
            "[WARNING] --message-title 或 --dispatch-message 未显式传入，已使用默认值兜底。\n"
            "正确流程：先执行 `template preview --scene <场景>` 获取预览，"
            "用户确认后再执行 `template create --message-title \"...\" --dispatch-message \"...\"`。\n"
            "如果你跳过了 preview 步骤，消息模板可能不贴合实际业务场景。",
            file=sys.stderr,
        )

    # ── 执行实际创建 ──────────────────────────────────────────────────
    create_kwargs = dict(
        name=args.name,
        description=description,
        custom_fields=custom_fields,
        summary_receivers=args.summary_receivers,
        remind_time=args.remind_time,
        created_by=args.created_by,
        status="enabled" if not args.disabled else "disabled",
        message_title=message_title,
        dispatch_message=dispatch_message,
        granularity=granularity,
        expected_duration=expected_duration,
    )
    logger.debug("调用 create_template，参数: %s", {k: (v[:80] + '…' if isinstance(v, str) and len(v) > 80 else v) for k, v in create_kwargs.items()})

    tid = ctx.template_manager.create_template(**create_kwargs)
    logger.debug("create_template 返回 template_id=%s", tid)
    ok(f"模版已创建: {tid}")

    # 模版创建成功后，自动触发 dispatch init 建表
    logger.debug("自动触发 dispatch init，为模版 %s 创建任务实例表", tid)
    try:
        tpl = ctx.template_manager.get_template(tid)
        task_context = ctx.dispatcher.ensure_task(
            tpl,
            reuse_strategy="new",
            force_new=True,
        )
        output = {k: v for k, v in task_context.items() if k != "notif_field_map"}
        ok(f"已自动触发 dispatch init，任务表已创建")
        print_json(output)
    except Exception as exc:
        logger.debug("自动触发 dispatch init 失败: %s", exc)
        err(f"模版已创建但自动建表失败，请手动执行 dispatch init --template-id {tid}：{exc}")

    return 0
# update 时不应作为字段透传给 update_template 的 args 名（含 *_file 这类辅助参数）
_UPDATE_NON_FIELDS = {
    "template_id", "func", "subcommand", "command", "yes", "log_level",
    "description_file", "dispatch_message_file",
}


def _update(args, ctx: AppContext) -> int:
    # description / dispatch_message 优先处理 -file 形式（与 -- 直传互斥）
    description, err_msg = _read_text_arg(
        args.description, args.description_file, "--description",
    )
    if err_msg:
        err(err_msg)
        return 2
    dispatch_message, err_msg = _read_text_arg(
        args.dispatch_message, args.dispatch_message_file, "--dispatch-message",
    )
    if err_msg:
        err(err_msg)
        return 2

    fields = {
        k: v
        for k, v in vars(args).items()
        if k not in _UPDATE_NON_FIELDS and v is not None
    }
    # 用合并后的 description / dispatch_message 覆盖（可能来自 -file）
    if description is not None:
        fields["description"] = description
    if dispatch_message is not None:
        fields["dispatch_message"] = dispatch_message
    # custom_fields 如果是字符串，保持原样传给 service（service 内部会处理 list/str 两种情况）
    rid = ctx.template_manager.update_template(args.template_id, **fields)
    ok(f"模版已更新: {args.template_id} (recordId={rid})")

    # ── custom_fields 变更时自动同步已有表单视图的 visibleFieldIds ──
    if "custom_fields" in fields:
        try:
            tpl = ctx.template_manager.get_template(args.template_id)
            if not tpl:
                logger.warning("同步 visibleFieldIds: 无法读取模版 %s", args.template_id)
            else:
                active_instance_id = tpl.get("active_instance_id", "")
                form_view_id = tpl.get("form_view_id", "")
                if active_instance_id and form_view_id:
                    # 解析最新的 custom_fields
                    cf_raw = tpl.get("custom_fields", "[]")
                    cf = json.loads(cf_raw) if isinstance(cf_raw, str) else cf_raw
                    updated = ctx.dispatcher._table_manager.update_form_view_visible_fields(
                        active_instance_id, form_view_id, cf,
                    )
                    if updated:
                        ok("已自动同步表单视图的可见字段配置")
                    else:
                        logger.warning(
                            "同步 visibleFieldIds 失败，请手动检查表单视图配置 "
                            "template_id=%s table_id=%s view_id=%s",
                            args.template_id, active_instance_id, form_view_id,
                        )
                else:
                    logger.debug(
                        "同步 visibleFieldIds: 模版 %s 无活跃实例表或表单视图，跳过",
                        args.template_id,
                    )
        except Exception as exc:
            logger.warning(
                "同步 visibleFieldIds 失败（不影响模版更新）: %s", exc,
            )

    return 0


def _enable(args, ctx: AppContext) -> int:
    ctx.template_manager.enable_template(args.template_id)
    ok(f"模版已启用: {args.template_id}")
    return 0


def _disable(args, ctx: AppContext) -> int:
    ctx.template_manager.disable_template(args.template_id)
    ok(f"模版已禁用: {args.template_id}")
    return 0


def _get(args, ctx: AppContext) -> int:
    d = ctx.template_manager.get_template(args.template_id)
    if not d:
        err(f"模版不存在: {args.template_id}")
        return 1
    print_json(d)
    return 0


def _list(args, ctx: AppContext) -> int:
    templates = ctx.template_manager.list_templates(
        only_enabled=args.only_enabled,
        limit=args.limit,
        sort_by=args.sort_by,
        sort_order=args.sort_order,
    )
    result = apply_list_options(
        templates,
        fields=getattr(args, "fields", None),
        count_only=getattr(args, "count_only", False),
        limit=args.limit,
        sort_by=args.sort_by,
        sort_order=args.sort_order,
    )
    print_json(result)
    return 0


def _instances(args, ctx: AppContext) -> int:
    """template instances：查看某模版管理的所有任务实例表。

    输出 JSON：
        {
          "template_id": "...",
          "table_strategy": "auto",
          "table_row_limit": 10000,
          "active_instance_id": "...",
          "managed_instance_count": 3,
          "instances": [
            {"table_id": "...", "is_active": true/false}
          ]
        }
    """
    import json as _json

    tpl = ctx.template_manager.get_template(args.template_id)
    if not tpl:
        err(f"模版不存在: {args.template_id}")
        return 1

    active_instance_id = tpl.get("active_instance_id", "")
    managed_raw = tpl.get("managed_instance_ids", "")

    managed_ids: list = []
    if managed_raw:
        try:
            managed_ids = _json.loads(managed_raw) if isinstance(managed_raw, str) else list(managed_raw)
        except (_json.JSONDecodeError, TypeError):
            managed_ids = []

    instances = [
        {"table_id": tid, "is_active": tid == active_instance_id}
        for tid in managed_ids
    ]

    print_json({
        "template_id": args.template_id,
        "table_strategy": tpl.get("table_strategy", "auto"),
        "table_row_limit": tpl.get("table_row_limit", 10000),
        "active_instance_id": active_instance_id,
        "managed_instance_count": len(managed_ids),
        "instances": instances,
    })
    return 0
