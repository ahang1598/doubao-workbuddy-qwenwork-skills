"""消息发送 + 模板变量替换。

钉钉 ``dws chat message send`` 默认按 **Markdown** 渲染消息内容（粗体、链接、
bullet、标题等均原生支持），且对纯文本完全兼容。本模块发送的所有消息：

- **正文**：从模版表读取 Markdown 模板字符串（``dispatch_message`` 字段），
  渲染占位符后作为 dws 的位置参数传入；模版字段为空时 fallback 到
  :mod:`scripts.domain.message_defaults` 中的内置 Markdown 默认文案。
- **标题**：从模版表读取 ``message_title`` 字段渲染后作为 ``--title`` 透传，
  钉钉消息列表中显示该标题；为空时同样 fallback 到默认值。
- **提醒消息**：复用派发模板（``dispatch_message`` + ``message_title``），
  ``reminder_round >= 2`` 时标题前缀自动加 ``【第N次提醒】``，无独立模板字段。

变量约定（中文占位符）：
- ``{门店名称}``  → instance.store_name
- ``{店长姓名}``  → instance.manager_name
- ``{派发时间}``  → instance.dispatch_time
- ``{任务名称}``  → template.name
- ``{任务表名}``  → instance.task_table_name
- ``{表单链接}``  → instance.form_link
- ``{截止时间}``  → instance.deadline_str
- ``{额外信息}``  → instance.extra_info  (来自 CLI ``--extra-info``)

英文别名（与中文占位符等价）：
- ``{store_name}``  → 门店名称
- ``{manager_name}`` → 店长姓名
- ``{dispatch_time}`` → 派发时间
- ``{task_name}``  → 任务名称
- ``{task_table_name}`` → 任务表名
- ``{form_link}``  → 表单链接
- ``{deadline}``  → 截止时间
- ``{extra_info}`` → 额外信息
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from scripts.domain.message_defaults import (
    DEFAULT_DISPATCH_MESSAGE_MARKDOWN,
    DEFAULT_DISPATCH_TITLE,
)
from scripts.domain.records import extract_open_dingtalk_id, extract_user_id
from scripts.infrastructure.dws_client import DwsClient

logger = logging.getLogger(__name__)

# 中文占位符 → 英文别名映射（支持模板中同时使用两种写法）
_ALIAS_MAP: Dict[str, str] = {
    "store_name": "门店名称",
    "manager_name": "店长姓名",
    "task_date": "任务日期",
    "dispatch_time": "派发时间",
    "task_name": "任务名称",
    "task_table_name": "任务表名",
    "form_link": "表单链接",
    "deadline": "截止时间",
    "extra_info": "额外信息",
}

# 模板里支持的变量名（中文 placeholder）
_PLACEHOLDERS = (
    "门店名称",
    "店长姓名",
    "任务日期",
    "派发时间",
    "任务名称",
    "任务表名",
    "表单链接",
    "截止时间",
    "额外信息",
)


def render(template_text: str, context: Dict[str, Any]) -> str:
    """把 ``{占位符}`` 替换为 context 中对应的值。

    同时支持中文占位符（``{门店名称}``）和英文别名（``{store_name}``）。
    未在 context 中提供的占位符会被替换为空字符串（避免漏配置导致崩溃）。
    richText 类型的 description 可能是 dict，取其文本内容。

    **空值行删除**：若某行包含占位符且该占位符的值为空（None / ""），
    替换后行内没有任何实质内容，则该整行会被完全移除，
    避免出现"- **门店**：" 这样的空字段行。
    """
    if not template_text:
        return ""
    # richText 类型返回的是 dict，提取纯文本
    if isinstance(template_text, dict):
        template_text = _extract_plain_text(template_text)
    # 逐行渲染：替换后若行内无实质内容则整行丢弃
    rendered_lines = [
        _render_line(line, context)
        for line in str(template_text).split("\n")
    ]
    # 过滤掉被标记为删除的行（None 表示该行应删除）
    kept_lines = [line for line in rendered_lines if line is not None]
    # 合并连续空行为单个空行，并去除首尾多余空行
    out = _collapse_blank_lines("\n".join(kept_lines))
    return out


def _render_line(line: str, context: Dict[str, Any]) -> Optional[str]:
    """渲染单行模板，若行内任意占位符的值为空则整行删除（返回 None）。

    判断逻辑：
    1. 检查该行是否包含任何占位符
    2. 若包含占位符，且其中任意一个占位符的值为空（None / ""），则整行删除
    3. 否则将所有占位符替换为对应值后返回渲染结果
    """
    rendered = line

    for ph in _PLACEHOLDERS:
        token = "{" + ph + "}"
        if token in rendered:
            value = context.get(ph, "")
            if not value:
                # 该行含有空值占位符，整行删除
                return None
            rendered = rendered.replace(token, str(value))

    for alias, zh_key in _ALIAS_MAP.items():
        token = "{" + alias + "}"
        if token in rendered:
            value = context.get(zh_key, context.get(alias, ""))
            if not value:
                return None
            rendered = rendered.replace(token, str(value))

    return rendered


def _collapse_blank_lines(text: str) -> str:
    """将连续多个空行合并为单个空行，并去除首尾多余空行。"""
    lines = text.split("\n")
    result_lines: list = []
    previous_was_blank = False
    for line in lines:
        if line.strip() == "":
            if not previous_was_blank:
                result_lines.append(line)
            previous_was_blank = True
        else:
            result_lines.append(line)
            previous_was_blank = False
    while result_lines and result_lines[0].strip() == "":
        result_lines.pop(0)
    while result_lines and result_lines[-1].strip() == "":
        result_lines.pop()
    return "\n".join(result_lines)


def _extract_plain_text(rich_text: Dict[str, Any]) -> str:
    """从 dws richText 格式中提取文本内容。

    AI 表格返回 richText 字段可能有两种格式：
    1. markdown 格式：{"markdown": "...原始Markdown内容..."}
       — 写入时用 build_cell_value("richText", text) 生成的格式
    2. doc 格式：{"type": "doc", "content": [{"type": "paragraph", "content": [...]}]}
       — AI 表格内部转换后的结构化存储格式

    优先处理 markdown 格式（保留完整 Markdown 语法），doc 格式作为 fallback。
    """
    # 优先：markdown 格式（写入时的原始格式，保留完整 Markdown 语法）
    if "markdown" in rich_text:
        return rich_text["markdown"] or ""

    # fallback：doc 格式（从结构化内容中提取纯文本）
    texts: List[str] = []
    for block in rich_text.get("content", []):
        for inline in block.get("content", []):
            if inline.get("type") == "text":
                texts.append(inline.get("text", ""))
    return "".join(texts)


def _resolve_message_templates(
    template: Dict[str, Any],
) -> tuple:
    """从模版 dict 中解析 (正文模板, 标题模板) 字符串对。

    - 正文：取 ``dispatch_message`` 字段；为空时 fallback 到内置默认 Markdown。
    - 标题：取 ``message_title`` 字段；为空时 fallback 到默认标题。
    - 派发与提醒消息共用同一对模板（提醒消息额外在标题前加前缀，由调用方处理）。

    richText 类型的字段在 AI 表格中可能以 dict 形式返回，这里统一抽取为
    纯文本字符串。
    """
    body = template.get("dispatch_message")
    if isinstance(body, dict):
        body = _extract_plain_text(body)

    title = template.get("message_title")

    # ── 防御性校验：字段为空时输出强警告 ──────────────────────────────
    # 正常流程下（先 preview → 再 create），message_title 和 dispatch_message
    # 一定有值。如果走到这里发现为空，说明模型可能跳过了 template preview 步骤，
    # 或者 template create 时未传入 --message-title / --dispatch-message。
    missing_fields = []
    if not body:
        missing_fields.append("dispatch_message")
    if not title:
        missing_fields.append("message_title")
    if missing_fields:
        tpl_id = template.get("template_id", "unknown")
        logger.warning(
            "模板 %s 的 %s 字段为空，已 fallback 到默认值。"
            "这通常说明创建模板时跳过了 `template preview` 步骤。"
            "请执行 `template update --template-id %s --message-title \"...\" "
            "--dispatch-message \"...\"` 补充写入。",
            tpl_id, " / ".join(missing_fields), tpl_id,
        )
        import sys
        print(
            f"[WARNING] 模板 {tpl_id} 的 {' / '.join(missing_fields)} 字段为空，"
            f"已使用默认值兜底发送。\n"
            f"⚠️ 正确流程：创建模板前应先执行 `template preview --scene <场景>` "
            f"生成完整预览，用户确认后再通过 `template create` 写入。\n"
            f"🔧 修复方法：执行 `template update --template-id {tpl_id} "
            f"--message-title \"今日门店巡检任务\" --dispatch-message-file <文件>` 补充。",
            file=sys.stderr,
        )

    body = body or DEFAULT_DISPATCH_MESSAGE_MARKDOWN
    title = title or DEFAULT_DISPATCH_TITLE
    return body, title


def _render_message_body(
    body_tpl: str,
    context: Dict[str, Any],
    ctx: Dict[str, Any],
) -> str:
    """渲染消息正文，并应用两条兜底规则：

    1. 模板未含 ``{额外信息}`` / ``{extra_info}`` 占位符，但 ctx 中 extra_info
       非空时，把额外信息以 ``> 📌 {extra_info}`` 的形式追加到正文末尾
       （在表单链接之前）。
    2. 模板未含 ``{表单链接}`` / ``{form_link}`` 占位符，但 ctx 中 form_link
       非空时，自动在末尾追加 ``[👉 立即填写]({form_link})``。

    这两条规则保证：哪怕用户写了一个极简模板，店长也总能拿到 form_link 和
    管理员临时下发的额外信息，且模板里显式使用占位符时不会重复出现。
    """
    body_str = body_tpl if isinstance(body_tpl, str) else ""

    content = render(body_tpl, context)

    # 1) 额外信息兜底（先于表单链接追加，确保链接始终在最后）
    extra_info = ctx.get("extra_info") or ctx.get("额外信息") or ""
    if (
        extra_info
        and "{额外信息}" not in body_str
        and "{extra_info}" not in body_str
    ):
        content = content.rstrip() + f"\n\n> 📌 {extra_info}"

    # 2) 表单链接兜底
    form_link = ctx.get("form_link", "")
    if (
        form_link
        and "{表单链接}" not in body_str
        and "{form_link}" not in body_str
    ):
        content = content.rstrip() + f"\n\n[👉 立即填写]({form_link})"

    return content


def build_dispatch_context(
    instance: Dict[str, Any],
    template: Dict[str, Any],
    # 兼容旧调用方式：message_context 作为位置参数
    message_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """根据消息上下文 + 模版构造模板变量字典。

    Args:
        instance: 包含 store_name/manager_name/dispatch_time/form_link 等字段的上下文字典。
                  也接受旧参数名 message_context（向后兼容）。
        template: 模版 dict，用于取 name。
        message_context: 已废弃，仅用于向后兼容，优先使用 instance。
    """
    ctx = instance if instance is not None else (message_context or {})
    # 截止时间：优先取 deadline_str，回退到 deadline 字段
    deadline_value = ctx.get("deadline_str") or ctx.get("deadline", "")
    # 额外信息：优先 extra_info，兼容中文 key
    extra_info_value = ctx.get("extra_info") or ctx.get("额外信息", "")
    # manager 字段为 user 类型，读取时返回 [{"userId":"xxx","corpId":"..."}]，不含 name
    # 优先使用上游已经反查好的 manager_name，兜底为空字符串
    manager_name = ctx.get("manager_name", "")

    return {
        "门店名称": ctx.get("store_name", ""),
        "店长姓名": manager_name,
        "任务日期": ctx.get("task_date", ""),
        "派发时间": ctx.get("dispatch_time", ""),
        "任务名称": template.get("name", ""),
        "任务表名": ctx.get("task_table_name", ""),
        "表单链接": ctx.get("form_link", ""),
        "截止时间": deadline_value,
        "额外信息": extra_info_value,
    }


class Messenger:
    """钉钉单聊消息发送器。"""

    def __init__(self, client: Optional[DwsClient] = None) -> None:
        self.client = client or DwsClient()

    def send_dispatch_message(
        self,
        instance: Dict[str, Any],
        template: Dict[str, Any],
        # 兼容旧调用方式
        message_context: Optional[Dict[str, Any]] = None,
        *,
        message_override: Optional[str] = None,
    ) -> Optional[str]:
        """发送派发通知消息（Markdown 渲染）。

        Args:
            instance: 包含 store_name/manager_name/manager_user_id/open_dingtalk_id/
                task_table_name/dispatch_time/form_link/extra_info 等字段的上下文字典。
            template: 模版 dict，从中读取 ``dispatch_message``（正文 Markdown 模板）
                和 ``message_title``（钉钉消息列表标题模板）；任一为空时
                fallback 到 :mod:`scripts.domain.message_defaults` 中的内置默认值。
            message_context: 已废弃，仅用于向后兼容，优先使用 instance。
            message_override: 一次性覆盖派发消息正文（Markdown），仅本次派发生效，
                不会写入模板表。传入时优先于 template 中的 dispatch_message。

        Returns:
            ``messageId``，发送失败抛出 :class:`DwsError`。
        """
        ctx = instance if instance is not None else (message_context or {})

        # 提取 openDingTalkId（dws chat message send 现在需要 --open-dingtalk-id）
        open_dingtalk_id = extract_open_dingtalk_id(ctx.get("manager")) or ctx.get("open_dingtalk_id", "")
        if not open_dingtalk_id:
            # 降级：尝试通过 userId 获取姓名再搜索 openDingTalkId
            manager_user_id = extract_user_id(ctx.get("manager")) or ctx.get("manager_user_id", "")
            if manager_user_id:
                manager_name = self.client.get_user_name(manager_user_id)
                if manager_name:
                    open_dingtalk_id = self.client.get_open_dingtalk_id(manager_name) or ""
            if not open_dingtalk_id:
                raise ValueError(
                    f"门店 {ctx.get('store_id')} 的 manager 缺少 openDingTalkId，无法发送消息"
                )

        # message_override 优先：一次性覆盖不写入模板表
        if message_override:
            body_tpl = message_override
            _, title_tpl = _resolve_message_templates(template)
        else:
            body_tpl, title_tpl = _resolve_message_templates(template)
        context = build_dispatch_context(ctx, template)

        content = _render_message_body(body_tpl, context, ctx)
        title = render(title_tpl, context).strip()

        result = self.client.chat_message_send(
            open_dingtalk_id, content, title=title or None,
        )
        return _extract_message_id(result)

    def send_remind_message(
        self,
        instance: Dict[str, Any],
        template: Optional[Dict[str, Any]] = None,
        # 兼容旧调用方式
        notification_row: Optional[Dict[str, Any]] = None,
        *,
        reminder_round: int = 1,
    ) -> Optional[str]:
        """发送再次提醒消息（Markdown 渲染）。

        提醒消息**复用**派发模板（``dispatch_message`` + ``message_title``），
        正文与派发完全一致；当 ``reminder_round >= 2`` 时，标题前缀自动加
        ``【第N次提醒】``；首次提醒（``reminder_round == 1``）的标题与派发一致，
        不加任何前缀。

        Args:
            instance: 通知上下文字典，含 manager_user_id/store_name/manager_name/
                task_table_name/form_link/extra_info 等字段。
            template: 模版 dict，从中读取 ``dispatch_message`` / ``message_title``；
                为空时 fallback 到 :mod:`scripts.domain.message_defaults` 中的
                内置默认值。
            notification_row: 已废弃，仅用于向后兼容，优先使用 instance。
            reminder_round: 当前是第几次提醒（从 1 开始）。值 ≥ 2 时标题加
                ``【第N次提醒】`` 前缀。
        """
        ctx = instance if instance is not None else (notification_row or {})

        # 提取 openDingTalkId（dws chat message send 现在需要 --open-dingtalk-id）
        open_dingtalk_id = extract_open_dingtalk_id(ctx.get("manager")) or ctx.get("open_dingtalk_id", "")
        if not open_dingtalk_id:
            # 降级：尝试通过 userId 获取姓名再搜索 openDingTalkId
            user_id = extract_user_id(ctx.get("manager")) or ctx.get("manager_user_id", "")
            if user_id:
                manager_name = self.client.get_user_name(user_id)
                if manager_name:
                    open_dingtalk_id = self.client.get_open_dingtalk_id(manager_name) or ""
            if not open_dingtalk_id:
                raise ValueError(
                    f"通知记录 {ctx.get('notification_id')} 的 manager 缺少 openDingTalkId"
                )

        tpl = template or {}
        body_tpl, title_tpl = _resolve_message_templates(tpl)
        context = build_dispatch_context(ctx, tpl)

        content = _render_message_body(body_tpl, context, ctx)
        title = render(title_tpl, context).strip()

        # 第 2 次及以后的提醒，自动加 `【第N次提醒】` 前缀；首次提醒与派发一致
        try:
            round_num = int(reminder_round)
        except (TypeError, ValueError):
            round_num = 1
        if round_num >= 2:
            title = f"【第{round_num}次提醒】{title}".strip()

        result = self.client.chat_message_send(
            open_dingtalk_id, content, title=title or None,
        )
        return _extract_message_id(result)

    def send_summary_message(self, open_dingtalk_id: str, content: str) -> Optional[str]:
        if not open_dingtalk_id:
            raise ValueError("open_dingtalk_id 不能为空")
        result = self.client.chat_message_send(open_dingtalk_id, content)
        return _extract_message_id(result)


def _extract_message_id(payload: Any) -> Optional[str]:
    if not isinstance(payload, dict):
        return None
    for key in ("messageId", "message_id", "id"):
        val = payload.get(key)
        if val:
            return str(val)
    data = payload.get("data")
    if isinstance(data, dict):
        return _extract_message_id(data)
    return None


__all__ = ["Messenger", "render", "build_dispatch_context"]
