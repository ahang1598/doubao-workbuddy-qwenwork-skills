"""
浏览器初始化步骤。

作为流水线的第一个步骤，负责通过 CDP 创建浏览器连接和移动端页面，
并将 page 注入到 PipelineContext 中供后续步骤使用。
"""

from services.meituan.browser_helper import create_mobile_page
from services.browser_pipeline import (
    FunctionalStep, PipelineContext, StepResult, StepStatus,
)


def run(
    context: PipelineContext,
    *,
    device_name: str,
    headless: bool,
) -> StepResult:
    """初始化浏览器环境。"""
    print(f"   📱 初始化浏览器 (设备: {device_name}, headless: {headless})")

    try:
        browser, page = create_mobile_page(
            device_name=device_name,
            headless=headless,
        )
    except Exception as error:
        return StepResult(
            step_name="setup_browser",
            status=StepStatus.FAILED,
            message=f"浏览器初始化失败: {error}",
        )

    context.set("_browser", browser)
    context.page = page

    return StepResult(
        step_name="setup_browser",
        status=StepStatus.SUCCESS,
        message=f"浏览器已就绪 (设备: {device_name})",
        data={"device": device_name, "browser_version": browser.version},
    )


def create_step(
    *,
    device_name: str = "iphone14",
    headless: bool = False,
) -> FunctionalStep:
    """构建浏览器初始化步骤。"""
    return FunctionalStep(
        name="setup_browser",
        run_fn=lambda ctx: run(ctx, device_name=device_name, headless=headless),
    )