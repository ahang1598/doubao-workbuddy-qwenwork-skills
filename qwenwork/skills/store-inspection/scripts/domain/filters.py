"""dws record query/update 的 filter 结构化 JSON 构造助手。

dws 的 filter 不是 SQL，而是嵌套的 ``operator/operands`` 结构（详见需求文档 §3.3）：

::

    {
        "operator": "and",
        "operands": [
            {"operator": "eq", "operands": ["fldXxx", "value"]},
            {"operator": "after", "operands": ["fldYyy", "2026-04-24T10:00:00+08:00"]}
        ]
    }

本模块仅提供 dict 构造助手，不依赖 dws_client，便于单测。
"""

from __future__ import annotations

from typing import Any, Dict, List


def eq(field_id: str, value: Any) -> Dict[str, Any]:
    """等于。"""
    return {"operator": "eq", "operands": [field_id, value]}


def neq(field_id: str, value: Any) -> Dict[str, Any]:
    """不等于。"""
    return {"operator": "neq", "operands": [field_id, value]}


def gt(field_id: str, value: Any) -> Dict[str, Any]:
    return {"operator": "gt", "operands": [field_id, value]}


def gte(field_id: str, value: Any) -> Dict[str, Any]:
    return {"operator": "gte", "operands": [field_id, value]}


def lt(field_id: str, value: Any) -> Dict[str, Any]:
    return {"operator": "lt", "operands": [field_id, value]}


def lte(field_id: str, value: Any) -> Dict[str, Any]:
    return {"operator": "lte", "operands": [field_id, value]}


def after(field_id: str, ts: str) -> Dict[str, Any]:
    """日期 > ts。"""
    return {"operator": "after", "operands": [field_id, ts]}


def before(field_id: str, ts: str) -> Dict[str, Any]:
    return {"operator": "before", "operands": [field_id, ts]}


def any_of(field_id: str, *values: Any) -> Dict[str, Any]:
    """multipleSelect 命中任一。"""
    return {"operator": "anyOf", "operands": [field_id, *values]}


def all_of(field_id: str, *values: Any) -> Dict[str, Any]:
    return {"operator": "allOf", "operands": [field_id, *values]}


def is_empty(field_id: str) -> Dict[str, Any]:
    return {"operator": "isEmpty", "operands": [field_id]}


def is_not_empty(field_id: str) -> Dict[str, Any]:
    return {"operator": "isNotEmpty", "operands": [field_id]}


def and_(*conditions: Dict[str, Any]) -> Dict[str, Any]:
    """组合多个条件为 AND。空条件列表会触发 ValueError。"""
    if not conditions:
        raise ValueError("and_ 需要至少一个子条件")
    return {"operator": "and", "operands": list(conditions)}


def or_(*conditions: Dict[str, Any]) -> Dict[str, Any]:
    if not conditions:
        raise ValueError("or_ 需要至少一个子条件")
    return {"operator": "or", "operands": list(conditions)}


__all__ = [
    "eq",
    "neq",
    "gt",
    "gte",
    "lt",
    "lte",
    "after",
    "before",
    "any_of",
    "all_of",
    "is_empty",
    "is_not_empty",
    "and_",
    "or_",
]
