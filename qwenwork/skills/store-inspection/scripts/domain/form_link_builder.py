"""表单链接拼接（需求文档 §2.4.2）。

钉钉 AI 表格表单 URL 通过 ``prefill_<fieldName>=值`` 参数预填字段值。

约束：
- 仅 text/number/single/multi 4 种字段类型支持预填；其他类型由店长手填。
- 预填值如含特殊符号（空格、``&``、``#``、``%`` 等）必须按 URL 编码转义。
- 骨架字段中对店长可见的字段使用中文展示名（「派发日期」「店长」），
  隐藏字段保留英文内部名（inspection_id、task_id、store_id 等）。
- 任务实例表首字段（主键）固定为 ``inspection_id``，通过
  ``prefill_inspection_id=<INSP_xxx>`` 在 URL 中初始化，
  在表单视图中隐藏（不透出给店长）。
- ``task_id`` 字段关联任务记录，同一次任务所有行值相同，通过
  ``prefill_task_id=<task_id>`` 预填，在表单视图中隐藏。
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from urllib.parse import quote, urlencode, urlparse, urlunparse

from scripts.domain.schema import FIELD_DISPLAY_DISPATCH_DATE, FIELD_DISPLAY_INSPECTION_ID


def build(
    form_base_url: str,
    *,
    inspection_id: str,
    task_id: str,
    template_id: str,
    store_id: str,
    notification_id: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> str:
    """拼接带 prefill 参数的表单链接。

    Args:
        form_base_url: 表单原始分享链接，可带或不带原 query string。
        inspection_id: 巡检记录唯一主键（``INSP_{task_id}_{store_id}``），
            对应任务实例表首字段 ``inspection_id``（primaryDoc）。生成的 URL 中
            会包含 ``prefill_inspection_id=<inspection_id>``。
        task_id: 任务 ID，关联任务记录表，同一次任务所有行值相同。
            生成的 URL 中会包含 ``prefill_task_id=<task_id>``，在表单视图中隐藏。
        template_id / store_id: 其余骨架字段，必填。
        notification_id: 关联任务通知表的 notification_id，可选。
            生成的 URL 中会包含 ``prefill_notification_id=<notification_id>``，
            在表单视图中隐藏，用于判断是否已提交。
        extra: 额外的 ``prefill_<name>: value`` 字段（用于扩展，比如 store_name、
            manager_user_id、任务派发时间 等需要一并预填的骨架字段）。

    Returns:
        拼接好的完整 URL。

    Raises:
        ValueError: form_base_url 为空，或 inspection_id / task_id / template_id / store_id 为空。
    """
    if not form_base_url:
        raise ValueError("form_base_url 不能为空")
    if "alidocs.dingtalk.com" in form_base_url:
        raise ValueError(
            f"form_base_url 域名错误：应使用 docs.dingtalk.com 而非 alidocs.dingtalk.com。"
            f"实际链接: {form_base_url}"
        )
    if "/i/notable/" in form_base_url:
        raise ValueError(
            f"form_base_url 格式错误：不存在 /i/notable/ 路径。"
            f"正确格式: https://docs.dingtalk.com/notable/share/form/{{shareUuid}}?source=link  "
            f"实际链接: {form_base_url}"
        )
    if "/i/nodes/" in form_base_url:
        raise ValueError(
            f"form_base_url 类型错误：/i/nodes/ 是 Base 编辑链接，不是表单分享链接。"
            f"实际链接: {form_base_url}"
        )
    if not inspection_id:
        raise ValueError("inspection_id 不能为空")
    if not task_id:
        raise ValueError("task_id 不能为空")
    if not template_id:
        raise ValueError("template_id 不能为空")
    if not store_id:
        raise ValueError("store_id 不能为空")

    prefills: Dict[str, Any] = {
        f"prefill_{FIELD_DISPLAY_INSPECTION_ID}": inspection_id,
        "prefill_task_id": task_id,
        "prefill_template_id": template_id,
        "prefill_store_id": store_id,
    }
    if notification_id:
        prefills["prefill_notification_id"] = notification_id
    if extra:
        for k, v in extra.items():
            if v is None:
                continue
            key = k if k.startswith("prefill_") else f"prefill_{k}"
            prefills[key] = v

    parsed = urlparse(form_base_url)
    # 用 quote 处理值，保留 = 和 & 之间的结构由 urlencode 负责
    new_query = urlencode(
        {k: _stringify(v) for k, v in prefills.items()},
        quote_via=quote,
        safe="",
    )
    if parsed.query:
        merged_query = parsed.query + "&" + new_query
    else:
        merged_query = new_query

    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            merged_query,
            parsed.fragment,
        )
    )


def _stringify(value: Any) -> str:
    """把 list/数字/bool 等转成 URL 友好的字符串。

    list（多选）的处理：钉钉表单 prefill 多选用 ``,`` 分隔。
    """
    if isinstance(value, list):
        return ",".join(str(x) for x in value)
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _build_share_url_from_form_info(form_info: dict) -> str:
    """从 formInfo 字典中提取 shareUuid 并拼接分享链接。

    Args:
        form_info: 包含 shareUuid 和 status 的 formInfo 字典。

    Returns:
        分享链接字符串，条件不满足时返回空字符串。
    """
    share_uuid = form_info.get("shareUuid")
    status = form_info.get("status")
    if share_uuid and str(status) == "1":
        return f"https://docs.dingtalk.com/notable/share/form/{share_uuid}?source=link"
    return ""


def extract_form_share_url(view_detail: dict) -> str:
    """从视图详情中提取表单分享 URL。

    兼容两种 API 返回结构：
    - 路径 1（旧版）: ``data.custom.formInfo.shareUuid``
    - 路径 2（新版）: ``data.views[0].custom.formInfo.shareUuid``

    Args:
        view_detail: aitable_view_get_detail 返回的视图详情。

    Returns:
        分享链接字符串，无法提取时返回空字符串。
    """
    data = view_detail.get("data") or {}

    # 路径 1：data.custom.formInfo（旧版/单视图直接返回）
    custom = data.get("custom") or {}
    form_info = custom.get("formInfo") or {}
    url = _build_share_url_from_form_info(form_info)
    if url:
        return url

    # 路径 2：data.views[].custom.formInfo（新版/视图列表返回）
    views = data.get("views")
    if isinstance(views, list):
        for view in views:
            if not isinstance(view, dict):
                continue
            view_custom = view.get("custom") or {}
            view_form_info = view_custom.get("formInfo") or {}
            url = _build_share_url_from_form_info(view_form_info)
            if url:
                return url

    return ""


__all__ = ["build", "extract_form_share_url"]
