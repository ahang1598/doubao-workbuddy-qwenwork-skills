"""record 操作的公共助手。

封装"按 fieldName 写 cells / 解析 record"等所有业务模块共用的转换逻辑，
避免每个模块都重复 fieldName→fieldId 的映射。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, List, Optional

from scripts.infrastructure.mapping_cache import MappingCache

logger = logging.getLogger(__name__)


def extract_cell_value(cell: Any, field_name: str = "") -> Any:
    """从 AiTable cell 原始值中提取业务值，统一处理各种字段类型。

    AiTable 不同字段类型的 API 返回结构各不相同，本函数按以下优先级解析：

    - **url 类型**：``{"link": "https://...", "text": "..."}`` → 取 ``link``，fallback ``text``
    - **singleSelect 类型**：``{"id": "xxx", "name": "sent"}`` → 取 ``name``，fallback ``id``
    - **multiSelect 类型**：``[{"id": "xxx", "name": "tag1"}, ...]`` → 各项 ``name`` 用逗号拼接
    - **普通 dict**（含 ``value``/``text`` 键）：取 ``value``，fallback ``text``
    - **纯字符串/数字**：直接返回

    设计原则：优先从标准表格格式取值，然后兼容纯字符串；不兼容其他非标格式。

    Args:
        cell: AiTable API 返回的 cell 原始值。
        field_name: 字段名，用于 url 类型字段的特殊处理（可选）。

    Returns:
        提取出的业务值；无法提取时返回 None。
    """
    if cell is None:
        return None

    # 纯字符串 / 数字 / 布尔：直接返回
    if not isinstance(cell, (dict, list)):
        return cell

    # user / member 类型：[{"userId": "xxx", "corpId": "...", ...}, ...]
    # 优先识别：列表中第一个 dict 含 userId 键
    if isinstance(cell, list) and cell and isinstance(cell[0], dict) and "userId" in cell[0]:
        return cell  # 返回完整列表，由调用方按需提取 userId

    # attachment 类型：[{"filename": "...", "url": "...", "resourceId": "...", "size": ..., "type": "image"}, ...]
    # 识别方式：列表中第一个 dict 含 url 或 resourceId 键（attachment 特征字段）
    # 必须在 multiSelect 之前判断，否则 attachment 会被误解析为逗号拼接的 resourceId 字符串
    if isinstance(cell, list) and cell and isinstance(cell[0], dict) and (
        "url" in cell[0] or "resourceId" in cell[0]
    ):
        return cell  # 原样保留完整附件列表，由调用方提取 url 等信息

    # multiSelect 类型：[{"id": "...", "name": "..."}, ...]
    if isinstance(cell, list):
        names = [item.get("name") or item.get("id") for item in cell if isinstance(item, dict)]
        return ",".join(str(n) for n in names if n is not None) or None

    # dict 类型：按键名判断具体类型
    # url 类型：{"link": "https://...", "text": "..."}
    if "link" in cell:
        return cell.get("link") or cell.get("text") or None

    # singleSelect 类型：{"id": "...", "name": "..."}（有 name 但无 value/link）
    if "name" in cell and "value" not in cell and "link" not in cell:
        return cell.get("name") or cell.get("id") or None

    # 普通 dict：{"value": "..."} 或 {"text": "..."}
    return cell.get("value") or cell.get("text") or None


def build_cell_value(
    field_type: str,
    value: Any,
    *,
    corp_id: Optional[str] = None,
) -> Any:
    """将业务值按 AITable 官方字段类型规范转换为合法的写入格式。

    统一封装各字段类型的健壮性转换，避免各模块散落的格式处理逻辑不一致。
    调用方只需传入字段类型和原始业务值，本函数保证输出符合 AITable API 规范。

    支持的字段类型及转换规则：

    - ``richText``：接受 str 或 dict；str 转为 ``{"markdown": "..."}``；
      已是合法 dict（含 ``markdown`` 键）则直接返回；其他 dict 尝试提取文本后转换。
    - ``url``：接受 str 或 ``{"text":..., "link":...}`` dict；
      裸字符串自动包装为 ``{"text": value, "link": value}``；
      已是合法 dict 则直接返回。
    - ``user``：接受 userId 字符串、userId 列表或已包装的 dict/list；
      统一转为 ``[{"userId": "xxx", "corpId": "..."}]``。
      ``corp_id`` 为 ``None`` 时不追加 ``corpId`` 键。
    - ``date``：接受毫秒时间戳（int）、ISO 日期字符串（str）；直接透传。
    - ``text`` / ``number`` / ``singleSelect`` / ``multipleSelect`` /
      ``checkbox`` / ``telephone`` / ``email`` / ``barcode`` / ``idCard``：
      直接透传，不做额外转换。
    - 未知类型：直接透传。

    Args:
        field_type: AITable 字段类型字符串，如 ``"richText"``、``"url"``、``"text"``。
        value: 原始业务值。``None`` 直接返回 ``None``。
        corp_id: 组织 corpId，仅 ``user`` 类型写入时使用。

    Returns:
        符合 AITable API 写入规范的值。
    """
    if value is None:
        return None

    if field_type == "richText":
        if isinstance(value, str):
            return {"markdown": value}
        if isinstance(value, dict):
            if "markdown" in value:
                return value
            # 兼容旧 doc 格式或其他 dict：提取纯文本后转换
            text = value.get("text") or value.get("value") or str(value)
            return {"markdown": text}
        return {"markdown": str(value)}

    if field_type == "url":
        if isinstance(value, str):
            return {"text": value, "link": value}
        if isinstance(value, dict) and "link" in value:
            return value
        return {"text": str(value), "link": str(value)}

    if field_type == "user":
        # user 类型写入格式：[{"userId": "staff_001", "corpId": "dingxxx"}]
        return _build_user_value(value, corp_id)

    if field_type == "member":
        # member 类型写入时传 userId 字符串数组，如 ["user123"]（保留向后兼容）
        if isinstance(value, str):
            return [value]
        if isinstance(value, list):
            return value
        return [str(value)]

    # text / number / singleSelect / multipleSelect / checkbox /
    # date / telephone / email / barcode / idCard 等：直接透传
    return value


def _build_user_value(value: Any, corp_id: Optional[str] = None) -> list:
    """将各种形式的 userId 输入统一转为 user 类型写入格式。

    返回 ``[{"userId": "xxx", "corpId": "..."}]``（corp_id 为 None 时不含 corpId 键）。
    """
    def _make_entry(user_id: str) -> dict:
        entry: dict = {"userId": user_id}
        if corp_id:
            entry["corpId"] = corp_id
        return entry

    def _ensure_corp_id(entry: dict) -> dict:
        """已有 dict 但缺少 corpId 时补齐。"""
        if corp_id and "corpId" not in entry:
            entry["corpId"] = corp_id
        return entry

    if isinstance(value, str):
        return [_make_entry(value)]
    if isinstance(value, list):
        if value and isinstance(value[0], dict):
            return [_ensure_corp_id(dict(item)) for item in value]
        return [_make_entry(str(v)) for v in value]
    if isinstance(value, dict) and "userId" in value:
        return [_ensure_corp_id(dict(value))]
    return [_make_entry(str(value))]


def extract_url_value(value: Any) -> str:
    """从 AiTable url 类型字段值中提取链接字符串。

    AiTable 的 url 类型字段在读取时返回 ``{"link": "...", "text": "..."}`` 格式的
    dict，而非裸字符串。本函数统一处理两种情况，确保始终返回 str。

    Args:
        value: url 字段的原始值，可能是 dict 或 str。

    Returns:
        提取出的 URL 字符串；无法提取时返回空字符串。
    """
    if isinstance(value, dict):
        return value.get("link") or value.get("text") or ""
    return value or ""


def extract_user_id(value: Any) -> str:
    """从 user 类型字段值中提取第一个 userId。

    AiTable 的 user 类型字段在读取时返回 ``[{"userId": "xxx", "corpId": "..."}]``
    格式的列表。本函数统一处理多种输入格式，确保始终返回 userId 字符串：

    - ``[{"userId": "xxx", ...}]`` → ``"xxx"``
    - ``{"userId": "xxx", ...}`` → ``"xxx"``
    - ``"plain_user_id"`` → ``"plain_user_id"``（裸字符串透传）
    - ``None`` / 空值 → ``""``

    Args:
        value: user 字段的原始值。

    Returns:
        提取出的 userId 字符串；无法提取时返回空字符串。
    """
    if value is None:
        return ""
    if isinstance(value, list) and value and isinstance(value[0], dict):
        return value[0].get("userId") or ""
    if isinstance(value, dict):
        return value.get("userId") or ""
    if isinstance(value, str):
        return value
    return ""


def extract_open_dingtalk_id(value: Any) -> str:
    """从 user 类型字段值中提取第一个 openDingTalkId。

    AiTable 的 user 类型字段在读取时返回
    ``[{"userId": "xxx", "openDingTalkId": "oid_xxx", ...}]`` 格式的列表。
    本函数提取 openDingTalkId，用于 dws chat message send 命令。

    - ``[{"openDingTalkId": "oid_xxx", ...}]`` → ``"oid_xxx"``
    - ``{"openDingTalkId": "oid_xxx", ...}`` → ``"oid_xxx"``
    - ``None`` / 空值 → ``""``
    """
    if value is None:
        return ""
    if isinstance(value, list) and value and isinstance(value[0], dict):
        return value[0].get("openDingTalkId") or ""
    if isinstance(value, dict):
        return value.get("openDingTalkId") or ""
    return ""


def cells_by_name(
    cache: MappingCache,
    base_id: str,
    table_name: str,
    values: Dict[str, Any],
) -> Dict[str, Any]:
    """将 ``{fieldName: value}`` 转为 ``{fieldId: build_cell_value(type, value)}``。

    自动根据 schema 中定义的字段类型调用 :func:`build_cell_value` 做格式转换，
    确保 ``user`` / ``url`` / ``richText`` 等特殊类型字段的值符合 AITable 写入规范。
    跳过 ``None`` 值。
    """
    field_map = cache.get_field_map(base_id, table_name)
    type_map = _get_field_type_map(table_name)

    # 延迟获取 corp_id，仅当本次写入包含 user 类型字段时才读取
    corp_id: Optional[str] = None
    need_corp_id = any(
        type_map.get(name) == "user"
        for name in values
        if values[name] is not None
    )
    if need_corp_id:
        from scripts.infrastructure.config import get_corp_id
        corp_id = get_corp_id()

    out: Dict[str, Any] = {}
    for name, value in values.items():
        if value is None:
            continue
        if name not in field_map:
            raise KeyError(
                f"字段 {name!r} 在表 {table_name!r} 中不存在（可能未在 schema 注册或表结构被改动）"
            )
        field_type = type_map.get(name)
        if field_type:
            value = build_cell_value(field_type, value, corp_id=corp_id)
        out[field_map[name]] = value
    return out


def _get_field_type_map(table_name: str) -> Dict[str, str]:
    """从 schema 中获取指定表的 ``{fieldName: fieldType}`` 映射。

    对于动态表（不在 ``TABLES`` 中的表），返回空 dict，不做类型转换。
    """
    from scripts.domain import schema as S

    schema = S.TABLES.get(table_name)
    if not schema:
        return {}
    return {f["name"]: f["type"] for f in schema["fields"]}


def extract_records(payload: Any) -> List[Dict[str, Any]]:
    """从 ``aitable record query`` 返回中提取 records 列表。

    兼容多种风格：
    - ``{"records": [...]}``
    - ``{"data": {"records": [...]}}``
    - 直接 list
    """
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    if isinstance(payload.get("records"), list):
        return payload["records"]
    data = payload.get("data")
    if isinstance(data, dict):
        return extract_records(data)
    return []


def get_record_id(record: Dict[str, Any]) -> Optional[str]:
    return record.get("recordId") or record.get("id")


def values_by_name(
    cache: MappingCache,
    base_id: str,
    table_name: str,
    record: Dict[str, Any],
) -> Dict[str, Any]:
    """把一条 record 的 ``cells`` 从 fieldId-key 翻译回 fieldName-key。

    若 record 中没有 cells 字段，返回空 dict。
    """
    cells = record.get("cells") or record.get("fields") or {}
    if not isinstance(cells, dict):
        return {}
    field_map = cache.get_field_map(base_id, table_name)
    reverse = {fid: name for name, fid in field_map.items()}
    out: Dict[str, Any] = {}
    for k, v in cells.items():
        name = reverse.get(k, k)
        out[name] = v
    return out


__all__ = [
    "build_cell_value",
    "cells_by_name",
    "extract_cell_value",
    "extract_open_dingtalk_id",
    "extract_records",
    "extract_url_value",
    "extract_user_id",
    "get_record_id",
    "values_by_name",
]
