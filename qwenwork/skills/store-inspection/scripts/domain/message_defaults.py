"""派发消息的内置 Markdown 默认模板。

当模版表中 ``dispatch_message`` / ``message_title`` 字段为空时，
:class:`scripts.services.messenger.Messenger` 会 fallback 到本模块定义的
Markdown 文案，确保店长收到的始终是带格式的可读消息（粗体店名、可点击链接、
bullet 列表）。

> 提醒消息**复用**派发模板（``dispatch_message`` + ``message_title``），由
> :class:`Messenger` 在标题前自动加 ``【第x次提醒】`` 前缀（``reminder_round
> >= 2`` 时），无需独立的 ``remind_*`` 常量。

钉钉 ``dws chat message send`` 默认按 Markdown 渲染消息内容（标题/正文均
支持），因此本模块的常量直接以 Markdown 字符串形态存储，无需任何额外的
escape / wrap 处理。

支持的占位符（与 :func:`scripts.services.messenger.render` 完全一致）：

- ``{门店名称}`` / ``{store_name}``
- ``{店长姓名}`` / ``{manager_name}``
- ``{任务日期}`` / ``{task_date}``
- ``{派发时间}`` / ``{dispatch_time}``
- ``{任务名称}`` / ``{task_name}``
- ``{任务表名}`` / ``{task_table_name}``
- ``{表单链接}`` / ``{form_link}``
- ``{截止时间}`` / ``{deadline}``
- ``{额外信息}`` / ``{extra_info}``  (来自 ``dispatch --extra-info`` 参数)
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# 派发消息 —— 标题 + 正文（提醒消息复用同一对模板）
# ---------------------------------------------------------------------------

# message_title 是钉钉消息列表中的纯文本标题（不支持 Markdown / 占位符渲染），
# 因此必须是固定的可读文本。如需自定义，在 template preview 阶段由用户确认修改。
DEFAULT_DISPATCH_TITLE = "今日门店巡检任务"

# 默认 Markdown 模板：内置 {额外信息} 占位符；该占位符为空时整行被
# render() 的"空值行删除"逻辑剥离，不影响版式。
DEFAULT_DISPATCH_MESSAGE_MARKDOWN = """### {任务名称}

**{店长姓名}** 你好，**{任务日期}** 的巡检任务待处理：

- **门店**：{门店名称}
- **任务表**：{任务表名}
- **截止时间**：{截止时间}
- **附加信息**：{额外信息}

请尽快点击下方链接填写：

[👉 立即填写]({表单链接})
"""

# ---------------------------------------------------------------------------
# 场景增强行 —— template create --scene 时插入到默认模板的"截止时间"行后面
# ---------------------------------------------------------------------------

# 每个场景对应一行 Markdown，会插入到默认模板的"截止时间"和"附加信息"之间。
# 行中的 `{检查项目}` 等占位符由 build_scene_dispatch_message() 在创建时
# 替换为 custom_fields 中的实际字段名（顿号连接），写入模板表后不再变化。
SCENE_EXTRA_LINES: dict[str, str] = {
    "inspection": "- **检查项目**：{检查项目}",
    "morning-meeting": "- **会议议程**：{会议议程}",
    "inventory": "- **盘点范围**：{盘点范围}",
}

# 场景中文名映射（用于预览展示）
SCENE_DISPLAY_NAMES: dict[str, str] = {
    "inspection": "巡店检查",
    "morning-meeting": "早会",
    "inventory": "盘点",
}

# 支持的场景列表（CLI choices 用）
SUPPORTED_SCENES = list(SCENE_EXTRA_LINES.keys())


def build_scene_dispatch_message(
    scene: str,
    custom_fields_names: list[str] | None = None,
) -> str:
    """根据场景生成完整的 dispatch_message 模板。

    在默认模板的基础上，在"截止时间"行后面插入场景增强行，
    并将场景占位符替换为 custom_fields 中的实际字段名。

    Args:
        scene: 场景标识（如 "inspection"）。不在 SCENE_EXTRA_LINES 中时
               返回纯默认模板。
        custom_fields_names: 检查项/议程等字段名列表，用顿号连接填入场景行。
                             为空时场景行中的占位符保留原样（render 时空值行删除）。

    Returns:
        完整的 Markdown 模板字符串。
    """
    extra_line = SCENE_EXTRA_LINES.get(scene, "")
    if not extra_line:
        return DEFAULT_DISPATCH_MESSAGE_MARKDOWN

    # 替换场景行中的占位符为实际字段名
    if custom_fields_names:
        items_str = "、".join(custom_fields_names)
        # 通用替换：场景行中的 {xxx} 占位符（非系统占位符）
        for placeholder in ("{检查项目}", "{会议议程}", "{盘点范围}"):
            if placeholder in extra_line:
                extra_line = extra_line.replace(placeholder, items_str)

    # 在默认模板的"截止时间"行后面插入场景增强行
    lines = DEFAULT_DISPATCH_MESSAGE_MARKDOWN.split("\n")
    result_lines: list[str] = []
    for line in lines:
        result_lines.append(line)
        if "截止时间" in line and line.strip().startswith("-"):
            result_lines.append(extra_line)

    return "\n".join(result_lines)


__all__ = [
    "DEFAULT_DISPATCH_TITLE",
    "DEFAULT_DISPATCH_MESSAGE_MARKDOWN",
    "SCENE_EXTRA_LINES",
    "SCENE_DISPLAY_NAMES",
    "SUPPORTED_SCENES",
    "build_scene_dispatch_message",
]
