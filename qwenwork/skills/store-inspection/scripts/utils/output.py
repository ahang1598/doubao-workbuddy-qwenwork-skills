"""CLI 输出助手 + 通用 CLI 入参解析函数。

集中放在 utils/，避免 commands 模块各自重复实现。
"""

from __future__ import annotations

import json
import sys
import unicodedata
from datetime import datetime
from typing import Any, List, Optional, Sequence

def print_json(obj: Any) -> None:
    """以 2 空格缩进、不转义中文的方式打印 JSON。"""
    print(json.dumps(obj, ensure_ascii=False, indent=2, default=str))

def ok(msg: str) -> None:
    print(f"[OK] {msg}")

def warn(msg: str) -> None:
    print(f"[WARN] {msg}", file=sys.stderr)

def err(msg: str) -> None:
    print(f"[ERROR] {msg}", file=sys.stderr)

def _display_width(text: Any) -> int:
    """返回字符串在等宽终端下的显示宽度。

    East Asian Wide / Fullwidth 字符按 2 计算，其他按 1。
    None / 非字符串会先转字符串。
    """
    if text is None:
        return 0
    if not isinstance(text, str):
        text = str(text)
    width = 0
    for ch in text:
        if unicodedata.east_asian_width(ch) in ("W", "F"):
            width += 2
        else:
            width += 1
    return width

def _pad_cell(text: Any, width: int) -> str:
    """按显示宽度左对齐填充。"""
    s = "" if text is None else str(text)
    pad = max(width - _display_width(s), 0)
    return s + " " * pad

def print_table(
    headers: Sequence[str],
    rows: Sequence[Sequence[Any]],
    *,
    title: Optional[str] = None,
) -> None:
    """渲染纯文本表格，自适应列宽（含中文宽度修正）。

    Args:
        headers: 表头列表
        rows:    行数据列表，每行长度应与 headers 一致；不足会补空，超出会截断
        title:   可选标题，渲染在表格上方

    空 ``rows`` 时打印「(无数据)」。
    """
    if title:
        print(title)

    if not headers:
        print("(无数据)")
        return

    cols = len(headers)
    norm_rows: List[List[str]] = []
    for raw in rows:
        cells = list(raw) + [""] * (cols - len(raw))
        cells = cells[:cols]
        norm_rows.append(["" if c is None else str(c) for c in cells])

    if not norm_rows:
        print("(无数据)")
        return

    widths = [_display_width(h) for h in headers]
    for row in norm_rows:
        for i, cell in enumerate(row):
            w = _display_width(cell)
            if w > widths[i]:
                widths[i] = w

    sep = "+" + "+".join("-" * (w + 2) for w in widths) + "+"

    def render(cells: Sequence[str]) -> str:
        return (
            "| "
            + " | ".join(_pad_cell(c, widths[i]) for i, c in enumerate(cells))
            + " |"
        )

    print(sep)
    print(render(list(headers)))
    print(sep)
    for row in norm_rows:
        print(render(row))
    print(sep)

def apply_list_options(
    items: List[Any],
    fields: Optional[str] = None,
    count_only: bool = False,
    limit: Optional[int] = None,
    sort_by: Optional[str] = None,
    sort_order: str = "desc",
) -> Any:
    """对列表查询结果应用通用的 ``--fields`` / ``--count-only`` / ``--sort-by`` 选项。

    Args:
        items:      原始数据列表（每个元素为 dict）。
        fields:     逗号分隔的字段名字符串；``None`` 表示返回全部字段。
        count_only: 为 ``True`` 时仅返回 ``{"total": N}``，优先级高于 ``fields``。
        limit:      查询时使用的 limit 值；当结果数等于 limit 时附加截断提示。
        sort_by:    排序字段名；``None`` 表示不排序。
        sort_order: 排序方向：``"asc"`` 升序 / ``"desc"`` 降序（默认 desc）。

    Returns:
        - ``count_only=True``：``{"total": N}``
        - ``fields`` 非空：过滤后的列表（每个 dict 只保留指定字段）
        - 否则：原始列表
        - 当结果数等于 limit 时，返回包含 ``_truncated`` 和 ``_hint`` 的包装对象
    """
    if count_only:
        return {"total": len(items)}

    # 排序（降级兜底）：服务端已通过 DWS --sort 实现排序，此处保留作为
    # 当服务端排序字段不存在或未生效时的客户端内存排序兜底。
    if sort_by:
        reverse = sort_order == "desc"
        items = sorted(items, key=lambda x: x.get(sort_by) or "", reverse=reverse)

    if fields:
        selected_keys = [f.strip() for f in fields.split(",") if f.strip()]
        items = [
            {key: item[key] for key in selected_keys if key in item}
            for item in items
        ]

    # 截断提示：当结果数等于 limit 时，可能存在更多数据
    if limit is not None and len(items) >= limit:
        return {
            "_truncated": True,
            "_hint": f"结果已达上限 {limit} 条，可能存在更多数据，请缩小筛选范围或增大 --limit",
            "total": len(items),
            "items": items,
        }

    return items

def split_csv(text: Optional[str]) -> Optional[List[str]]:
    """逗号分隔字符串拆数组。``None`` 透传，空串返回空列表。"""
    if text is None:
        return None
    return [p.strip() for p in text.split(",") if p.strip()]

def parse_iso(text: Optional[str]) -> Optional[datetime]:
    """解析 ISO8601 字符串。

    - 兼容 ``Z`` 后缀（UTC）
    - 无 tz 时使用 :data:`scripts.infrastructure.sync_state.DEFAULT_TZ`
    - 解析失败返回 ``None``
    """
    if not text:
        return None
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        # 延迟导入，避免循环依赖（utils 不应在模块顶层依赖 infrastructure）
        from scripts.infrastructure import sync_state as ss

        dt = dt.replace(tzinfo=ss.DEFAULT_TZ)
    return dt

__all__ = [
    "print_json",
    "ok",
    "warn",
    "err",
    "print_table",
    "split_csv",
    "parse_iso",
]
