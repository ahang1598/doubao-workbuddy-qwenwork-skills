"""
浏览器清理步骤。

作为流水线的最后一个步骤，负责关闭页面和清理浏览器连接。
即使前面的步骤失败，此步骤也应尽量执行。
"""

from services.browser_pipeline import (
    FunctionalStep, PipelineContext, StepResult, StepStatus,
)


def run(context: PipelineContext) -> StepResult:
    """清理浏览器资源：关闭页面并关闭浏览器连接。"""
    errors: list[str] = []

    page = context.page
    if page:
        try:
            page.close()
            print("   🧹 页面已关闭")
        except Exception as error:
            errors.append(f"关闭页面失败: {error}")
        context.page = None

    browser = context.get("_browser")
    if browser:
        try:
            browser.close()
            print("   🧹 浏览器连接已关闭")
        except Exception as error:
            errors.append(f"关闭浏览器连接失败: {error}")

def create_step() -> FunctionalStep:
    """构建浏览器清理步骤（流水线中止后仍会执行）。"""
    return FunctionalStep(
        name="teardown_browser",
        run_fn=run,
        run_on_abort=True,
    )