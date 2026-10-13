"""统一时间格式化工具。

所有写入 AI 表格 ``date`` 类型字段（schema 中带 ``_DATE_TIME_CONFIG`` 的字段）
的位置都应使用本模块的 :func:`fmt_datetime`，避免出现「日期字段缺时分秒」
的问题。

历史背景：
    早期代码里部分 date 字段（如 ``notified_at`` / ``initiated_at``）写入时
    误用了 ``now.strftime("%Y-%m-%d")``，丢失了时分秒精度，导致：
    1) 任务记录排序、复用判断不准确（同一天多次派发无法按精确时间排序）；
    2) 通知明细的派发时间无法定位到分钟级，运营同学排障困难。

    引入本模块后约定：所有写入 date 字段一律使用 ``fmt_datetime``；
    仅当业务确实只需日期粒度（如「按当天分组查询」）才用 ``fmt_date``。
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

#: 与 ``scripts.domain.schema._DATE_TIME_CONFIG`` 中
#: ``{"formatter": "YYYY-MM-DD HH:mm:ss"}`` 对齐。
DATETIME_FMT = "%Y-%m-%d %H:%M:%S"

#: 仅日期粒度，用于按天分组查询、日期前缀匹配等纯查询场景。
DATE_FMT = "%Y-%m-%d"


def fmt_datetime(dt: Optional[datetime] = None) -> str:
    """格式化为 ``"YYYY-MM-DD HH:mm:ss"``。

    Args:
        dt: 待格式化的时间，默认 :func:`datetime.datetime.now`。

    Returns:
        如 ``"2026-04-27 09:18:42"`` 的字符串。

    Note:
        所有 date 字段写入都应使用本函数，**禁止直接调用** ``strftime``。
    """
    return (dt or datetime.now()).strftime(DATETIME_FMT)


def fmt_date(dt: Optional[datetime] = None) -> str:
    """格式化为 ``"YYYY-MM-DD"``。

    仅用于按当天分组查询、日期前缀匹配等不需要时分秒的场景。
    **禁止用于写入 date 字段**，会导致丢失时分秒。
    """
    return (dt or datetime.now()).strftime(DATE_FMT)


# ---------------------------------------------------------------------------
# 毫秒时间戳 ↔ datetime 转换（AI 表格 date 字段专用）
# ---------------------------------------------------------------------------

#: 合理时间戳范围：2020-01-01 ~ 2100-01-01（毫秒）
_MIN_REASONABLE_MS = 1_577_836_800_000  # 2020-01-01T00:00:00 UTC
_MAX_REASONABLE_MS = 4_102_444_800_000  # 2100-01-01T00:00:00 UTC


def to_timestamp_ms(dt: Optional[datetime] = None) -> int:
    """将 datetime 转为毫秒时间戳。

    **注意**：本函数用于需要毫秒时间戳的内部计算场景（如冷却判断、时间差比较）。
    **写入 AITable date 字段时请使用** :func:`fmt_datetime`，传格式化日期字符串，
    否则数值会被 AITable 当作年份解析，导致显示为 1779 年等异常值。

    Args:
        dt: 待转换的时间，默认 :func:`datetime.datetime.now`。

    Returns:
        毫秒级整数时间戳。

    Raises:
        ValueError: 生成的时间戳不在 2020~2100 年合理范围内。
    """
    import time as _time

    dt = dt or datetime.now()
    ms = int(_time.mktime(dt.timetuple()) * 1000)
    if not (_MIN_REASONABLE_MS <= ms <= _MAX_REASONABLE_MS):
        raise ValueError(
            f"时间戳 {ms} 超出合理范围 (2020~2100)，"
            f"原始时间: {dt.isoformat()}"
        )
    return ms


def from_timestamp_ms(ms: int) -> datetime:
    """将毫秒时间戳解析为 datetime。

    Args:
        ms: 毫秒级整数时间戳。

    Returns:
        本地 datetime 实例。

    Raises:
        ValueError: 时间戳不在 2020~2100 年合理范围内。
    """
    if not (_MIN_REASONABLE_MS <= ms <= _MAX_REASONABLE_MS):
        raise ValueError(
            f"时间戳 {ms} 超出合理范围 (2020~2100)"
        )
    return datetime.fromtimestamp(ms / 1000.0)


__all__ = [
    "DATETIME_FMT", "DATE_FMT",
    "fmt_datetime", "fmt_date",
    "to_timestamp_ms", "from_timestamp_ms",
]
