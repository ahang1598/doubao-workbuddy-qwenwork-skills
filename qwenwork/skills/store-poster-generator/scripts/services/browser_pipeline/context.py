"""
流水线共享上下文。

PipelineContext 存储用户参数、中间结果等，
所有步骤通过 context 传递数据，避免步骤间直接耦合。
"""

from __future__ import annotations

from typing import Any

from services.browser_pipeline.step import StepResult


class PipelineContext:
    """步骤间共享的上下文对象。"""

    def __init__(self, **initial_params: Any) -> None:
        self._params: dict[str, Any] = dict(initial_params)
        self._results: list[StepResult] = []
        self.should_abort: bool = False
        self.abort_reason: str = ""

    def get(self, key: str, default: Any = None) -> Any:
        """获取上下文参数。"""
        return self._params.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """设置上下文参数。"""
        self._params[key] = value

    def record_result(self, result: StepResult) -> None:
        """记录步骤执行结果。"""
        self._results.append(result)

    @property
    def results(self) -> list[StepResult]:
        """获取所有步骤的执行结果（只读副本）。"""
        return list(self._results)

    def abort(self, reason: str) -> None:
        """标记流水线应中止执行。"""
        self.should_abort = True
        self.abort_reason = reason
