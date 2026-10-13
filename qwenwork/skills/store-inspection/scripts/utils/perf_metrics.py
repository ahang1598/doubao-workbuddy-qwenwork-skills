"""性能监控工具。

提供 ``@timed`` 装饰器和 ``PerfReport`` 类，用于追踪单次命令执行期间的
API 调用耗时、调用次数、缓存命中率等指标。

使用方式：
    from scripts.utils.perf_metrics import timed, perf_report

    @timed("stats.query_task_records")
    def query_task_records(...):
        ...

    # 命令结束时输出报告
    perf_report.summary()
"""

from __future__ import annotations

import functools
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, TypeVar

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


@dataclass
class MetricEntry:
    """单个指标的统计记录。"""

    name: str
    call_count: int = 0
    total_time: float = 0.0
    min_time: float = float("inf")
    max_time: float = 0.0

    @property
    def avg_time(self) -> float:
        return self.total_time / self.call_count if self.call_count > 0 else 0.0

    def record(self, elapsed: float) -> None:
        self.call_count += 1
        self.total_time += elapsed
        self.min_time = min(self.min_time, elapsed)
        self.max_time = max(self.max_time, elapsed)


class PerfReport:
    """命令级性能报告收集器。

    线程安全说明：本类设计为单线程主流程使用。并发查询在子线程内
    不会调用 report 方法，只在主线程汇总时写入。
    """

    def __init__(self) -> None:
        self._metrics: Dict[str, MetricEntry] = {}
        self._cache_hits: int = 0
        self._cache_misses: int = 0
        self._api_calls: int = 0
        self._start_time: Optional[float] = None

    def start(self) -> None:
        """标记命令开始。"""
        self._start_time = time.time()

    def record(self, name: str, elapsed: float) -> None:
        """记录一次方法调用耗时。"""
        if name not in self._metrics:
            self._metrics[name] = MetricEntry(name=name)
        self._metrics[name].record(elapsed)

    def record_cache_hit(self) -> None:
        self._cache_hits += 1

    def record_cache_miss(self) -> None:
        self._cache_misses += 1

    def record_api_call(self) -> None:
        self._api_calls += 1

    @property
    def cache_hit_rate(self) -> float:
        total = self._cache_hits + self._cache_misses
        return self._cache_hits / total if total > 0 else 0.0

    @property
    def elapsed(self) -> float:
        if self._start_time is None:
            return 0.0
        return time.time() - self._start_time

    def summary(self) -> str:
        """生成可读的性能摘要报告。"""
        lines: List[str] = []
        lines.append("=" * 60)
        lines.append("性能报告")
        lines.append("=" * 60)
        lines.append(f"总耗时: {self.elapsed:.3f}s")
        lines.append(f"API 调用次数: {self._api_calls}")
        lines.append(
            f"缓存命中率: {self.cache_hit_rate:.1%} "
            f"({self._cache_hits}/{self._cache_hits + self._cache_misses})"
        )
        lines.append("-" * 60)
        lines.append(f"{'方法':<40} {'次数':>5} {'总耗时':>8} {'平均':>8}")
        lines.append("-" * 60)

        sorted_metrics = sorted(
            self._metrics.values(), key=lambda m: m.total_time, reverse=True
        )
        for m in sorted_metrics:
            lines.append(
                f"{m.name:<40} {m.call_count:>5} "
                f"{m.total_time:>7.3f}s {m.avg_time:>7.3f}s"
            )
        lines.append("=" * 60)

        report = "\n".join(lines)
        logger.info("\n%s", report)
        return report

    def reset(self) -> None:
        """重置所有指标（用于命令间隔离）。"""
        self._metrics.clear()
        self._cache_hits = 0
        self._cache_misses = 0
        self._api_calls = 0
        self._start_time = None


# 全局单例，供整个命令生命周期共享
perf_report = PerfReport()


def timed(metric_name: Optional[str] = None) -> Callable[[F], F]:
    """计时装饰器，自动记录方法耗时到全局 PerfReport。

    Args:
        metric_name: 指标名称。如果为 None，使用 ``module.func_name``。

    Usage:
        @timed("stats.query_task_records")
        def query_task_records(self, ...):
            ...
    """

    def decorator(fn: F) -> F:
        name = metric_name or f"{fn.__module__}.{fn.__qualname__}"

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            t0 = time.time()
            try:
                return fn(*args, **kwargs)
            finally:
                elapsed = time.time() - t0
                perf_report.record(name, elapsed)
                logger.debug("%s 耗时 %.3fs", name, elapsed)

        return wrapper  # type: ignore[return-value]

    return decorator


__all__ = ["timed", "perf_report", "PerfReport", "MetricEntry"]
