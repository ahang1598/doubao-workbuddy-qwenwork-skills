"""
流水线调度器。

Pipeline 按顺序执行已注册的步骤，支持运行时动态插入/移除/替换步骤。

用法示例：
    pipeline = Pipeline(name="my-workflow")
    pipeline.add_step(MyStepA())
    pipeline.add_step(MyStepB())
    context = pipeline.execute(param1="value1")
"""

from __future__ import annotations

import time
from typing import Any

from services.browser_pipeline.context import PipelineContext
from services.browser_pipeline.step import PipelineStep, StepResult, StepStatus


class Pipeline:
    """流水线调度器。

    按顺序执行已注册的步骤，支持运行时动态管理步骤列表。
    """

    def __init__(self, name: str) -> None:
        self._name = name
        self._steps: list[PipelineStep] = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def steps(self) -> list[PipelineStep]:
        """当前注册的步骤列表（只读副本）。"""
        return list(self._steps)

    def add_step(self, step: PipelineStep) -> Pipeline:
        """追加步骤到流水线末尾。"""
        self._steps.append(step)
        return self

    def insert_step(self, index: int, step: PipelineStep) -> Pipeline:
        """在指定位置插入步骤。"""
        self._steps.insert(index, step)
        return self

    def remove_step(self, step_name: str) -> Pipeline:
        """按名称移除步骤。"""
        self._steps = [s for s in self._steps if s.name != step_name]
        return self

    def replace_step(self, step_name: str, new_step: PipelineStep) -> Pipeline:
        """按名称替换步骤。"""
        self._steps = [
            new_step if s.name == step_name else s
            for s in self._steps
        ]
        return self

    def execute(self, **params: Any) -> PipelineContext:
        """执行流水线中的所有步骤。

        Args:
            **params: 传递给 PipelineContext 的初始参数

        Returns:
            执行完成后的 PipelineContext（包含所有步骤结果）
        """
        context = PipelineContext(**params)
        total_steps = len(self._steps)

        print(f"\n{'='*60}")
        print(f"🚀 流水线 [{self._name}] 开始执行 ({total_steps} 个步骤)")
        print(f"{'='*60}")

        for index, step in enumerate(self._steps, start=1):
            step_label = f"[{index}/{total_steps}] {step.name}"

            if context.should_abort and not step.run_on_abort:
                result = StepResult(
                    step_name=step.name,
                    status=StepStatus.SKIPPED,
                    message=f"流水线已中止: {context.abort_reason}",
                )
                context.record_result(result)
                print(f"  ⏭️  {step_label} — 已跳过 (流水线中止)")
                continue

            if step.should_skip(context):
                result = StepResult(
                    step_name=step.name,
                    status=StepStatus.SKIPPED,
                    message="步骤主动跳过",
                )
                context.record_result(result)
                print(f"  ⏭️  {step_label} — 已跳过")
                continue

            print(f"\n  ▶️  {step_label} 开始执行...")
            start_time = time.monotonic()

            try:
                result = step.run(context)
                result.duration_seconds = time.monotonic() - start_time
            except Exception as error:
                result = StepResult(
                    step_name=step.name,
                    status=StepStatus.FAILED,
                    message=f"未捕获异常: {error}",
                    duration_seconds=time.monotonic() - start_time,
                )
                context.abort(f"步骤 [{step.name}] 异常: {error}")

            context.record_result(result)

            status_icon = {
                StepStatus.SUCCESS: "✅",
                StepStatus.FAILED: "❌",
                StepStatus.SKIPPED: "⏭️",
            }.get(result.status, "❓")

            print(
                f"  {status_icon} {step_label} — {result.status.value} "
                f"({result.duration_seconds:.1f}s)"
            )
            if result.message:
                print(f"     💬 {result.message}")

        self._print_summary(context)
        return context

    def _print_summary(self, context: PipelineContext) -> None:
        """打印流水线执行摘要。"""
        results = context.results
        total_duration = sum(r.duration_seconds for r in results)
        success_count = sum(1 for r in results if r.status == StepStatus.SUCCESS)
        failed_count = sum(1 for r in results if r.status == StepStatus.FAILED)
        skipped_count = sum(1 for r in results if r.status == StepStatus.SKIPPED)

        print(f"\n{'='*60}")
        print(f"📊 流水线 [{self._name}] 执行完成")
        print(f"   ✅ 成功: {success_count}  ❌ 失败: {failed_count}  ⏭️ 跳过: {skipped_count}")
        print(f"   ⏱️  总耗时: {total_duration:.1f}s")

        if context.should_abort:
            print(f"   ⚠️  中止原因: {context.abort_reason}")

        print(f"{'='*60}\n")
