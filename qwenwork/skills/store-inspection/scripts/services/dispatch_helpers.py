"""派发辅助工具函数集合。

本模块从 dispatcher.py 中提取出所有模块级（不在 Dispatcher 类内）的纯工具函数
和 DispatchSummary dataclass，用于在多个服务间共享这些基础工具逻辑。
"""

from __future__ import annotations

import random
import string
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 数据类
# ---------------------------------------------------------------------------

@dataclass
class DispatchSummary:
    """单次派发的汇总结果。"""

    task_id: str
    instance_table_name: str
    template_id: str
    total: int = 0
    success: int = 0
    failed: int = 0
    skipped: int = 0
    details: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "instance_table_name": self.instance_table_name,
            "template_id": self.template_id,
            "total": self.total,
            "success": self.success,
            "failed": self.failed,
            "skipped": self.skipped,
            "details": self.details,
        }


# ---------------------------------------------------------------------------
# ID / 名称生成
# ---------------------------------------------------------------------------

def make_task_id(template_id: str, now: datetime) -> str:
    """生成任务 ID：``TASK_{template_id}_{yyyyMMddHHmmss}{rand4}``。

    - 时间部分精确到秒，避免同一分钟派发冲突。
    - 后缀为 4 位小写字母+数字随机串（与 ``generate_template_id`` 一致），
      保证同一秒内并发派发也不会产生重复 task_id。
    """
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
    return f"TASK_{template_id}_{now.strftime('%Y%m%d%H%M%S')}{suffix}"


def make_instance_table_name(template_name: str, now: datetime, granularity: str = "per_year") -> str:
    """生成动态任务表名。

    - per_year（默认）：「{模版名称}-{YYYY}」，如「每日巡检-2026」
    - per_month：「{模版名称}-{YYYY}-{MM}」，如「每日巡检-2026-04」
    """
    if granularity == "per_month":
        return f"{template_name}-{now.strftime('%Y-%m')}"
    return f"{template_name}-{now.strftime('%Y')}"


def make_notification_id(task_id: str, store_id: str) -> str:
    """生成通知 ID：``NOTIF_{task_id}_{store_id}``。"""
    return f"NOTIF_{task_id}_{store_id}"


# ---------------------------------------------------------------------------
# 截止时间计算
# ---------------------------------------------------------------------------

def _calc_deadline(now: "datetime", expected_duration: str):
    """解析 expected_duration 字符串，计算截止时间。

    Args:
        now: 任务发起时间。
        expected_duration: 格式 "Xh" / "Xm" / "XhYm"，如 "2h"、"30m"、"1h30m"。

    Returns:
        (deadline_value, deadline_str) 元组：deadline_value 为格式化日期字符串（写入 date 字段），
        deadline_str 为人类可读的短格式（用于消息渲染）。解析失败返回 (None, "")。
    """
    import re as _re
    from datetime import timedelta as _timedelta
    if not expected_duration:
        return None, ""
    total_minutes = 0
    match = _re.fullmatch(r"(?:(\d+)h)?(?:(\d+)m)?", expected_duration.strip())
    if match and (match.group(1) or match.group(2)):
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        total_minutes = hours * 60 + minutes
    if total_minutes <= 0:
        logger.warning(
            "_calc_deadline: 无法解析 expected_duration=%r，跳过截止时间计算",
            expected_duration,
        )
        return None, ""
    deadline_dt = now + _timedelta(minutes=total_minutes)
    from scripts.utils.datetime_format import fmt_datetime
    deadline_value = fmt_datetime(deadline_dt)
    deadline_str = deadline_dt.strftime("%Y-%m-%d %H:%M")
    return deadline_value, deadline_str


# ---------------------------------------------------------------------------
# payload 解析辅助函数
# ---------------------------------------------------------------------------

def _extract_table_id(payload: dict) -> Optional[str]:
    """从 dws table create/get 返回中提取 tableId。"""
    if not isinstance(payload, dict):
        return None
    for key in ("tableId", "table_id", "id"):
        val = payload.get(key)
        if val:
            return val
    if isinstance(payload.get("tables"), list) and payload["tables"]:
        first = payload["tables"][0]
        if isinstance(first, dict):
            for key in ("tableId", "id"):
                if first.get(key):
                    return first[key]
    data = payload.get("data")
    if isinstance(data, dict):
        return _extract_table_id(data)
    return None


def _extract_view_id(payload: dict) -> Optional[str]:
    """从 dws view create 返回中提取 viewId。"""
    if not isinstance(payload, dict):
        return None
    for key in ("viewId", "view_id", "id"):
        val = payload.get(key)
        if val:
            return str(val)
    data = payload.get("data")
    if isinstance(data, dict):
        return _extract_view_id(data)
    for list_key in ("items", "views"):
        items = payload.get(list_key)
        if isinstance(items, list) and items:
            first = items[0]
            if isinstance(first, dict):
                for key in ("viewId", "id"):
                    if first.get(key):
                        return str(first[key])
    return None


def _validate_form_link(link: str) -> str:
    """校验并规范化表单分享链接格式。

    合法格式（必须满足之一）：
    - ``https://docs.dingtalk.com/notable/share/form/{shareUuid}...``
    - ``https://docs.dingtalk.com/share/form/{shareUuid}...``

    常见幻觉/错误格式（会被拦截）：
    - 包含 ``/i/notable/`` 路径（不存在的 URL 路径）
    - 使用 ``alidocs.dingtalk.com`` 域名（内网域名，外部无法访问）
    - 包含 ``/i/nodes/`` 路径（这是 Base 编辑链接，不是表单分享链接）

    Returns:
        原始链接（校验通过时）。

    Raises:
        ValueError: 链接格式不合法。
    """
    if not link:
        return link
    if "/i/notable/" in link:
        raise ValueError(
            f"表单链接格式错误：不存在 /i/notable/ 路径。"
            f"正确格式: https://docs.dingtalk.com/notable/share/form/{{shareUuid}}?source=link  "
            f"实际链接: {link}"
        )
    if "alidocs.dingtalk.com" in link:
        raise ValueError(
            f"表单链接域名错误：应使用 docs.dingtalk.com 而非 alidocs.dingtalk.com。"
            f"实际链接: {link}"
        )
    if "/i/nodes/" in link:
        raise ValueError(
            f"链接类型错误：/i/nodes/ 是 Base 编辑链接，不是表单分享链接。"
            f"正确格式: https://docs.dingtalk.com/notable/share/form/{{shareUuid}}?source=link  "
            f"实际链接: {link}"
        )
    return link


def _extract_form_link_raw(payload: dict) -> str:
    """从 dws view create/get 返回中提取表单链接（内部递归实现，不含校验）。

    优先顺序：
    1. 直接字段：shareUrl / formUrl / url / shareLink / formLink
    2. custom.formInfo.shareUuid → 拼接为分享链接
    3. data 嵌套层中的上述字段
    4. items/views 列表第一项中的递归查找
    5. extract_form_share_url fallback
    """
    if not isinstance(payload, dict):
        return ""
    for key in ("shareUrl", "formUrl", "url", "shareLink", "formLink"):
        val = payload.get(key)
        if val and isinstance(val, str) and val.startswith("http"):
            return val
    # 从 custom.formInfo.shareUuid 提取并拼接分享链接
    # view get 返回结构：{..., "custom": {"formInfo": {"shareUuid": "v01xxx", "status": "1"}}}
    custom = payload.get("custom")
    if isinstance(custom, dict):
        form_info = custom.get("formInfo")
        if isinstance(form_info, dict):
            share_uuid = form_info.get("shareUuid")
            if share_uuid and isinstance(share_uuid, str):
                return f"https://docs.dingtalk.com/notable/share/form/{share_uuid}?source=link"
    data = payload.get("data")
    if isinstance(data, dict):
        link = _extract_form_link_raw(data)
        if link:
            return link
    for list_key in ("items", "views"):
        items = payload.get(list_key)
        if isinstance(items, list) and items:
            first = items[0]
            if isinstance(first, dict):
                link = _extract_form_link_raw(first)
                if link:
                    return link

    # 5. 从 formInfo.shareUuid 拼接分享链接（兼容新版 API 返回结构）
    #    优先检查 data.custom.formInfo，再检查 data.views[].custom.formInfo
    from scripts.domain.form_link_builder import extract_form_share_url
    share_url = extract_form_share_url(payload)
    if share_url:
        return share_url

    return ""


def _extract_form_link(payload: dict) -> str:
    """从 dws view create/get 返回中提取表单链接（带格式校验）。

    内部调用 :func:`_extract_form_link_raw` 提取链接，然后通过
    :func:`_validate_form_link` 校验格式。不合法的链接会记 warning
    日志并返回空字符串（降级为无链接，由调用方引导用户手动粘贴）。
    """
    link = _extract_form_link_raw(payload)
    if not link:
        return ""
    try:
        return _validate_form_link(link)
    except ValueError as exc:
        logger.warning("提取到的表单链接未通过校验: %s", exc)
        return ""


def _extract_fields_from_table(payload: dict) -> list:
    """从 aitable table get 返回中提取字段列表。"""
    if not isinstance(payload, dict):
        return []
    if isinstance(payload.get("fields"), list):
        return payload["fields"]
    if isinstance(payload.get("tables"), list) and payload["tables"]:
        first = payload["tables"][0]
        if isinstance(first, dict) and isinstance(first.get("fields"), list):
            return first["fields"]
    data = payload.get("data")
    if isinstance(data, dict):
        return _extract_fields_from_table(data)
    return []


def _extract_records(payload: dict) -> list:
    """从 aitable record query/create 返回中提取记录列表。

    兼容多种响应结构：
    - ``{"records": [...]}``
    - ``{"data": {"records": [...]}}``
    - ``{"items": [...]}``
    """
    if not isinstance(payload, dict):
        return []
    for key in ("records", "items"):
        val = payload.get(key)
        if isinstance(val, list):
            return val
    data = payload.get("data")
    if isinstance(data, dict):
        return _extract_records(data)
    return []


def _find_table_id_by_name(payload: dict, table_name: str) -> Optional[str]:
    """从 aitable base get 返回中按表名查找 tableId。

    兼容两种响应结构：
    - ``{"tables": [...]}``
    - ``{"data": {"tables": [...]}}``
    """
    if not isinstance(payload, dict):
        return None
    tables = payload.get("tables")
    if not isinstance(tables, list):
        data = payload.get("data")
        if isinstance(data, dict):
            tables = data.get("tables")
    if not isinstance(tables, list):
        return None
    for t in tables:
        if not isinstance(t, dict):
            continue
        name = t.get("tableName") or t.get("name")
        tid = t.get("tableId") or t.get("id")
        if name == table_name and tid:
            return tid
    return None


def _extract_record_id(payload: dict) -> Optional[str]:
    """从 aitable record create 返回中提取第一条记录的 recordId。

    兼容多种响应结构：
    - ``{"records": [{"recordId": "..."}]}``
    - ``{"data": {"records": [{"recordId": "..."}]}}``
    - ``{"items": [{"recordId": "..."}]}``
    """
    if not isinstance(payload, dict):
        return None
    for list_key in ("records", "items"):
        items = payload.get(list_key)
        if isinstance(items, list) and items:
            first = items[0]
            if isinstance(first, dict):
                rid = first.get("recordId") or first.get("id")
                if rid:
                    return str(rid)
    data = payload.get("data")
    if isinstance(data, dict):
        return _extract_record_id(data)
    return None


# ---------------------------------------------------------------------------
# 分享链接校验
# ---------------------------------------------------------------------------

# 「真实分享链接」的特征：必须包含这些路径片段才算合法
_VALID_SHARE_LINK_PATTERNS = (
    "/notable/share/form/",  # AI 表格官方分享链接
    "/share/form/",          # 兼容写法（部分场景下钉钉返回的短链）
)

# 「内部编辑链接」的特征：必须排除，不能当成 form_url
_INVALID_SHARE_LINK_PATTERNS = (
    "/i/nodes/",             # AI 表格内部编辑链接（用户复制浏览器地址栏会误粘贴）
)


def _is_valid_share_link(url: str) -> bool:
    """判断是否是真正的「填写表单」分享链接（非内部编辑链接）。

    规则（同时满足）：
    1. 必须以 http 开头
    2. 不能含 ``/i/nodes/``（内部编辑链接）
    3. 必须含 ``/notable/share/form/`` 或 ``/share/form/``

    Examples:
        >>> _is_valid_share_link("https://docs.dingtalk.com/notable/share/form/abc")
        True
        >>> _is_valid_share_link("https://docs.dingtalk.com/i/nodes/BAS_xx?iframeQuery=...")
        False
        >>> _is_valid_share_link("")
        False
    """
    if not url or not isinstance(url, str):
        return False
    if not url.startswith("http"):
        return False
    if any(bad in url for bad in _INVALID_SHARE_LINK_PATTERNS):
        return False
    return any(good in url for good in _VALID_SHARE_LINK_PATTERNS)


# ---------------------------------------------------------------------------
# 任务状态与用户交互
# ---------------------------------------------------------------------------

def _resolve_task_record_status(summary: "DispatchSummary") -> str:
    """根据派发汇总推断任务记录的 status 字段值。

    - total == 0：占位记录或目标为空 → "进行中"
    - failed == 0 且 success > 0：全部成功 → "已完成"
    - 其他（含全部失败）：→ "部分失败"（避免新增枚举）
    """
    if summary.total == 0:
        return "进行中"
    if summary.failed == 0:
        return "已完成"
    return "部分失败"


def _prompt_resend_for_store(store: Dict[str, Any]) -> str:
    """询问用户是否对单个【已通知】门店重发通知。

    Args:
        store: 门店 dict，至少包含 ``store_id`` / ``store_name``。

    Returns:
        用户选择：

        - ``"y"`` - 仅本店重发
        - ``"n"`` - 仅本店跳过（默认 / 回车 / 异常输入）
        - ``"a"`` - 全部已通知都重发（后续不再问）
        - ``"s"`` - 全部已通知都跳过（后续不再问）
        - ``"q"`` - 退出整个派发
    """
    store_id = store.get("store_id", "?")
    store_name = store.get("store_name", "?")
    prompt = (
        f"\n[重复通知确认] 门店【{store_name}】(id={store_id}) 已通知过。\n"
        f"  y = 仅本店重发\n"
        f"  N = 仅本店跳过（默认）\n"
        f"  a = 全部已通知都重发（后续不再问）\n"
        f"  s = 全部已通知都跳过（后续不再问）\n"
        f"  q = 退出整个派发\n"
        f"请选择 [y/N/a/s/q]: "
    )
    try:
        choice = input(prompt).strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\n[已跳过] 用户中断输入")
        return "q"
    if choice in ("y", "n", "a", "s", "q"):
        return choice
    return "n"


def _prompt_user_for_share_link(
    instance_table_id: str,
    form_view_id: str,
    base_id: str,
    current_link: str = "",
) -> str:
    """打印一段引导文案，提示 agent 在对话中引导用户完成「发布并分享表单」。

    当所有自动获取 form_url 的方式（含重试）均未成功时调用，通常是因为
    AI 表格服务同步延迟导致。本函数**不会**要求用户复制分享链接——用户
    只需在 AI 表格中完成「发布并分享」，然后告知 agent「已发布」即可。
    agent 收到确认后应重新执行 ``dispatch init``，系统会自动通过
    ``extract_form_share_url`` 从视图详情中提取 ``shareUuid`` 并拼接出
    正确的分享链接。

    **绝对不要让 agent 自行拼接/猜测分享链接格式。**

    Args:
        instance_table_id: 任务表 ID，用于拼接引导用户打开的编辑链接。
        form_view_id: 表单视图 ID，用于拼接直达表单视图的引导链接。
        base_id: Base ID，用于拼接引导链接。
        current_link: 兼容老签名保留的参数，本函数不再使用。

    Returns:
        始终返回空字符串。调用方应判断空值并阻止派发，避免发垃圾消息。

    Note:
        引导链接（``docs.dingtalk.com/i/nodes/{baseId}?iframeQuery=...``）
        是给用户「打开 AI 表格做配置」用的，绝对不能被当成 form_url。
    """
    # 1. 拼接引导链接（仅用于引导用户去打开 AI 表格，不会被当成 form_url）
    if form_view_id:
        form_edit_url = (
            f"https://docs.dingtalk.com/i/nodes/{base_id}"
            f"?iframeQuery=sheetId%3D{instance_table_id}%26viewId%3D{form_view_id}"
        )
    else:
        form_edit_url = (
            f"https://docs.dingtalk.com/i/nodes/{base_id}"
            f"?iframeQuery=sheetId%3D{instance_table_id}"
        )

    # 2. 打印引导文案（给 agent 看，agent 再据此引导用户）
    print("\n" + "=" * 60)
    print("[需要用户操作] 暂时无法自动获取表单分享链接，可能是 AI 表格服务同步延迟导致。")
    print("请 agent 按以下 3 步引导用户完成表单发布：")
    print()
    print("  1. 打开编辑链接（用于进入 AI 表格调整表单）：")
    print(f"     {form_edit_url}")
    print()
    print("  2. 调整表单：在 AI 表格中切换到【表单】视图，按需调整字段顺序、")
    print("     说明文字等。⚠️ 请务必将「店长」字段设为必填（点击字段右侧")
    print("     设置图标，开启「必填」开关），否则店长可能跳过该字段导致无法追溯")
    print()
    print("  3. 发布并分享：点击表单视图右上角的【分享】按钮，开启分享开关，")
    print("     然后回复「已发布」即可")
    print()
    print("  [首选] 用户完成发布后，agent 应重新执行 dispatch init，系统会自动")
    print("     从视图详情中提取 shareUuid 并拼接分享链接，无需用户复制链接。")
    print()
    print("  [备选] 如果重新执行 dispatch init 后仍然无法自动获取，")
    print("     请用户在表单视图中点击「分享」→ 复制分享链接，然后执行：")
    print("     dispatch notify --task-id <TASK_ID> --form-url \"<用户粘贴的链接>\"")
    print("     合法链接格式：https://docs.dingtalk.com/notable/share/form/v01...?source=link")
    print()
    print("  ⚠️ agent 绝对不要自行拼接或猜测分享链接格式！（H13）")
    print("=" * 60 + "\n")

    # 不阻塞等待 stdin，直接返回空字符串
    return ""


def _parse_notified_at(value: Any) -> Optional[datetime]:
    """解析通知表的 notified_at 字段，兼容字符串/毫秒时间戳/秒时间戳。

    支持的格式：
    - "YYYY-MM-DD HH:MM:SS"（fmt_datetime 写入格式）
    - "YYYY-MM-DDTHH:MM:SS"（ISO）
    - "YYYY-MM-DD"（仅日期，视为当天 00:00:00）
    - int / float / 数字字符串：毫秒时间戳（>= 10^12）或秒时间戳

    Returns:
        datetime 实例；解析失败返回 None。
    """
    if value is None or value == "":
        return None
    # 数字时间戳
    if isinstance(value, (int, float)):
        try:
            ts = float(value)
            if ts >= 1e12:  # 毫秒
                ts = ts / 1000.0
            return datetime.fromtimestamp(ts)
        except (OverflowError, OSError, ValueError):
            return None
    # 字符串
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        # 纯数字字符串当时间戳处理
        if s.isdigit():
            try:
                ts = float(s)
                if ts >= 1e12:
                    ts = ts / 1000.0
                return datetime.fromtimestamp(ts)
            except (OverflowError, OSError, ValueError):
                return None
        # 字符串时间格式
        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%d",
        ):
            try:
                return datetime.strptime(s, fmt)
            except ValueError:
                continue
    return None


__all__ = [
    "DispatchSummary",
    "make_task_id",
    "make_instance_table_name",
    "make_notification_id",
    "_calc_deadline",
    "_extract_table_id",
    "_extract_view_id",
    "_extract_form_link",
    "_extract_fields_from_table",
    "_extract_records",
    "_find_table_id_by_name",
    "_extract_record_id",
    "_is_valid_share_link",
    "_VALID_SHARE_LINK_PATTERNS",
    "_INVALID_SHARE_LINK_PATTERNS",
    "_resolve_task_record_status",
    "_prompt_resend_for_store",
    "_prompt_user_for_share_link",
    "_parse_notified_at",
]
