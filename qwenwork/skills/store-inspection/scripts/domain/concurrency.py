"""并发执行引擎。

提供统一的并发查询能力，供所有服务复用。基于 concurrent.futures.ThreadPoolExecutor
实现，支持超时控制和错误隔离（单个失败不影响其他）。

设计原则：
- 默认 max_workers=5，避免触发 DWS API 限流
- 单个任务失败时记录日志并返回 None，不中断整体批量操作
- 提供通用 parallel_map 和专用 parallel_query 两个接口
"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")
R = TypeVar("R")

DEFAULT_MAX_WORKERS = 5
DEFAULT_TIMEOUT = 60  # 整体超时（秒）


@dataclass
class QuerySpec:
    """批量查询的单条查询规格。"""

    base_id: str
    table_id: str
    filters: Optional[dict] = None
    limit: Optional[int] = None
    sort: Optional[list] = None
    # 用于结果索引的 key，默认使用 table_id
    key: Optional[str] = None

    @property
    def result_key(self) -> str:
        return self.key or self.table_id


@dataclass
class ParallelResult:
    """并发执行的汇总结果。"""

    results: Dict[str, Any] = field(default_factory=dict)
    errors: Dict[str, Exception] = field(default_factory=dict)
    elapsed: float = 0.0

    @property
    def success_count(self) -> int:
        return len(self.results)

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def total_count(self) -> int:
        return self.success_count + self.error_count


def parallel_map(
    fn: Callable[[T], R],
    items: Sequence[T],
    *,
    max_workers: int = DEFAULT_MAX_WORKERS,
    timeout: float = DEFAULT_TIMEOUT,
) -> List[Optional[R]]:
    """对 items 并发执行 fn，返回与 items 顺序一致的结果列表。

    单个任务失败时对应位置为 None，不影响其他任务。

    Args:
        fn: 要并发执行的函数。
        items: 输入序列。
        max_workers: 最大并发线程数。
        timeout: 整体超时时间（秒）。

    Returns:
        与 items 等长的结果列表，失败项为 None。
    """
    if not items:
        return []

    # 单个任务时无需启动线程池
    if len(items) == 1:
        try:
            return [fn(items[0])]
        except Exception as exc:
            logger.warning("parallel_map 单任务执行失败: %s", exc)
            return [None]

    results: List[Optional[R]] = [None] * len(items)
    t0 = time.time()

    with ThreadPoolExecutor(max_workers=min(max_workers, len(items))) as executor:
        future_to_idx = {
            executor.submit(fn, item): idx for idx, item in enumerate(items)
        }
        for future in as_completed(future_to_idx, timeout=timeout):
            idx = future_to_idx[future]
            try:
                results[idx] = future.result()
            except Exception as exc:
                logger.warning(
                    "parallel_map 第 %d 项执行失败: %s", idx, exc
                )

    elapsed = time.time() - t0
    success = sum(1 for r in results if r is not None)
    logger.debug(
        "parallel_map 完成: %d/%d 成功, 耗时 %.3fs",
        success,
        len(items),
        elapsed,
    )
    return results


def parallel_query(
    client: Any,
    queries: Sequence[QuerySpec],
    *,
    max_workers: int = DEFAULT_MAX_WORKERS,
    timeout: float = DEFAULT_TIMEOUT,
) -> ParallelResult:
    """使用 DwsClient 并发执行多个 record_query。

    Args:
        client: DwsClient 实例。
        queries: 查询规格列表。
        max_workers: 最大并发线程数。
        timeout: 整体超时时间（秒）。

    Returns:
        ParallelResult，其中 results 按 QuerySpec.result_key 索引。
    """
    if not queries:
        return ParallelResult()

    t0 = time.time()
    result = ParallelResult()

    def _execute_query(spec: QuerySpec) -> tuple:
        """执行单个查询并返回 (key, data)。"""
        data = client.aitable_record_query(
            spec.base_id,
            spec.table_id,
            spec.filters,
            limit=spec.limit,
            sort=spec.sort,
        )
        return (spec.result_key, data)

    # 单个查询直接执行
    if len(queries) == 1:
        spec = queries[0]
        try:
            _, data = _execute_query(spec)
            result.results[spec.result_key] = data
        except Exception as exc:
            logger.warning(
                "parallel_query 查询失败 [%s]: %s", spec.result_key, exc
            )
            result.errors[spec.result_key] = exc
        result.elapsed = time.time() - t0
        return result

    with ThreadPoolExecutor(
        max_workers=min(max_workers, len(queries))
    ) as executor:
        future_to_spec = {
            executor.submit(_execute_query, spec): spec for spec in queries
        }
        for future in as_completed(future_to_spec, timeout=timeout):
            spec = future_to_spec[future]
            try:
                _, data = future.result()
                result.results[spec.result_key] = data
            except Exception as exc:
                logger.warning(
                    "parallel_query 查询失败 [%s]: %s", spec.result_key, exc
                )
                result.errors[spec.result_key] = exc

    result.elapsed = time.time() - t0
    logger.debug(
        "parallel_query 完成: %d/%d 成功, %d 失败, 耗时 %.3fs",
        result.success_count,
        result.total_count,
        result.error_count,
        result.elapsed,
    )
    return result


__all__ = [
    "parallel_map",
    "parallel_query",
    "QuerySpec",
    "ParallelResult",
    "DEFAULT_MAX_WORKERS",
    "DEFAULT_TIMEOUT",
]
