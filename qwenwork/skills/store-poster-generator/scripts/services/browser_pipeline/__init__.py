"""
浏览器自动化 Pipeline 框架。

将 Pipeline 调度、BrowserStep、启动器等
收拢为一个内聚的包，业务代码只需从此包 import。

公开 API：
- PipelineStep / FunctionalStep / StepResult / StepStatus — 步骤定义
- PipelineContext — 共享上下文
- Pipeline — 调度器
- BrowserStep / WorkerResult / RunFn — 统一的浏览器任务步骤
- launch_detached_step / read_worker_result / is_worker_alive / DetachedWorkerHandle — 启动器
"""

from services.browser_pipeline.step import (
    FunctionalStep,
    PipelineStep,
    StepResult,
    StepStatus,
)
from services.browser_pipeline.context import PipelineContext
from services.browser_pipeline.pipeline import Pipeline
from services.browser_pipeline.browser_step import (
    BrowserStep,
    RunFn,
    WorkerResult,
)
from services.browser_pipeline.detached_launcher import (
    DetachedWorkerHandle,
    launch_detached_step,
    read_worker_result,
    is_worker_alive,
)

__all__ = [
    "BrowserStep",
    "FunctionalStep",
    "Pipeline",
    "PipelineContext",
    "PipelineStep",
    "StepResult",
    "StepStatus",
    "RunFn",
    "WorkerResult",
    "DetachedWorkerHandle",
    "launch_detached_step",
    "read_worker_result",
    "is_worker_alive",
]
