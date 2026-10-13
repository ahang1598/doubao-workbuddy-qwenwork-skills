"""
流水线步骤定义。

提供 PipelineStep（抽象基类）、FunctionalStep（函数式实现）、
StepStatus（状态枚举）、StepResult（结果数据类）。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from services.browser_pipeline.context import PipelineContext


class StepStatus(Enum):
    """步骤执行状态。"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StepResult:
    """单个步骤的执行结果。"""
    step_name: str
    status: StepStatus
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    duration_seconds: float = 0.0


class PipelineStep(ABC):
    """流水线步骤基类。

    子类需实现：
    - name: 步骤名称（用于日志和结果标识）
    - run(context): 执行逻辑

    可选重写：
    - should_skip(context): 判断是否跳过本步骤
    - run_on_abort: 流水线中止后是否仍然执行
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """步骤的唯一标识名称。"""

    @abstractmethod
    def run(self, context: PipelineContext) -> StepResult:
        """执行步骤逻辑。

        Args:
            context: 流水线共享上下文

        Returns:
            StepResult 表示执行结果
        """

    def should_skip(self, context: PipelineContext) -> bool:
        """判断是否跳过本步骤，默认不跳过。"""
        return False

    @property
    def run_on_abort(self) -> bool:
        """流水线中止后是否仍然执行此步骤，默认 False。

        清理类步骤（如 teardown）应重写此属性返回 True。
        """
        return False


class FunctionalStep(PipelineStep):
    """函数式流水线步骤。

    通过构造参数配置，无需继承即可创建步骤。
    适用于逻辑简单、不需要自定义类的场景。

    用法示例：
        step = FunctionalStep(
            name="setup",
            run_fn=my_setup_function,
            run_on_abort=False,
        )
    """

    def __init__(
        self,
        name: str,
        run_fn: Callable[[PipelineContext], StepResult],
        *,
        run_on_abort: bool = False,
    ) -> None:
        self._name = name
        self._run_fn = run_fn
        self._run_on_abort = run_on_abort

    @property
    def name(self) -> str:
        return self._name

    @property
    def run_on_abort(self) -> bool:
        return self._run_on_abort

    def run(self, context: PipelineContext) -> StepResult:
        return self._run_fn(context)
