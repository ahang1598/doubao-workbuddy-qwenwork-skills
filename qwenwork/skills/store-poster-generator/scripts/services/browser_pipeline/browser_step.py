"""
BrowserStep：统一的浏览器任务步骤。

通过 detached 参数控制执行方式：
- detached=True（默认）：启动 detached 子进程执行，主进程立即返回
- detached=False：主进程直接连接 CDP 浏览器同步执行

所有业务 step 的 run_fn 签名统一为 (CdpBrowser, CdpPage, dict) -> WorkerResult。

用法示例（detached 子进程）：
    BrowserStep(
        name="login",
        run_fn=login.run,
        device_name="iphone14",
        abort_after_launch=True,
    )

用法示例（主进程同步执行）：
    BrowserStep(
        name="check_login",
        run_fn=check_login.run,
        device_name="iphone14",
        detached=False,
    )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from services.browser.cdp_client import CdpBrowser, CdpPage

from services.browser_pipeline.context import PipelineContext
from services.browser_pipeline.detached_launcher import launch_detached_step
from services.browser_pipeline.step import PipelineStep, StepResult, StepStatus

# run_fn 签名：(CdpBrowser, CdpPage, dict) -> WorkerResult
RunFn = Callable[[CdpBrowser, CdpPage, dict[str, Any]], "WorkerResult"]


@dataclass
class WorkerResult:
    """步骤执行结果，detached 模式下会被序列化为 JSON 写入结果文件。"""
    status: str  # "success" | "failed" | "timeout"
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)


class BrowserStep(PipelineStep):
    """统一的浏览器任务步骤。

    Args:
        name: 步骤名称
        run_fn: 业务逻辑函数，签名为 (Browser, Page, dict) -> WorkerResult
        detached: 是否在 detached 子进程中执行（默认 True）
        device_name: 设备模拟配置名称（None 表示桌面端）
        timeout: 超时秒数
        headless: 是否无头模式
        abort_after_launch: 启动后是否中止 pipeline（仅 detached=True 时有效）
        abort_message: 自定义 abort 消息模板，支持 {pid} 占位符
        extra_params: 传给 run_fn 的固定参数（与 params_builder 互斥）
        params_builder: 从 PipelineContext 动态构造 params 的回调
        validate: 主进程前置校验回调，返回 None 表示通过，返回 StepResult 表示中止
    """

    def __init__(
        self,
        name: str,
        run_fn: RunFn,
        *,
        detached: bool = False,
        device_name: str | None = None,
        timeout: int = 120,
        headless: bool = False,
        abort_after_launch: bool = False,
        abort_message: str | None = None,
        extra_params: dict[str, Any] | None = None,
        params_builder: Callable[[PipelineContext], dict[str, Any]] | None = None,
        validate: Callable[[PipelineContext], StepResult | None] | None = None,
    ) -> None:
        self._name = name
        self._run_fn = run_fn
        self._detached = detached
        self._device_name = device_name
        self._timeout = timeout
        self._headless = headless
        self._abort_after_launch = abort_after_launch
        self._abort_message = abort_message
        self._extra_params = extra_params or {}
        self._params_builder = params_builder
        self._validate = validate

    @property
    def name(self) -> str:
        return self._name

    def run(self, context: PipelineContext) -> StepResult:
        if self._validate:
            validation_result = self._validate(context)
            if validation_result is not None:
                return validation_result

        extra_params = (
            self._params_builder(context)
            if self._params_builder
            else dict(self._extra_params)
        )

        if self._detached:
            return self._run_detached(context, extra_params)
        return self._run_inline(context, extra_params)

    def _run_detached(self, context: PipelineContext, extra_params: dict) -> StepResult:
        """通过 detached 子进程执行。"""
        handle = launch_detached_step(
            run_fn=self._run_fn,
            step_name=self._name,
            timeout=self._timeout,
            headless=self._headless,
            device_name=self._device_name,
            extra_params=extra_params or None,
            inherit_output=not self._abort_after_launch,
        )

        context.set(f"{self._name}_worker_handle", handle)
        context.set(f"{self._name}_worker_pid", handle.worker_pid)
        context.set(f"{self._name}_result_file", str(handle.result_file))

        if self._abort_after_launch:
            message = (
                self._abort_message.format(pid=handle.worker_pid)
                if self._abort_message
                else f"子进程已启动 (PID={handle.worker_pid})，请等待用户操作完成后再继续"
            )
            context.abort(message)

        return StepResult(
            step_name=self._name,
            status=StepStatus.SUCCESS,
            message=f"子进程已启动 (PID={handle.worker_pid})",
            data={
                "worker_pid": handle.worker_pid,
                "result_file": str(handle.result_file),
                "stdout_log": str(handle.stdout_log),
                "stderr_log": str(handle.stderr_log),
                "timeout": handle.timeout_seconds,
            },
        )

    def _run_inline(self, context: PipelineContext, extra_params: dict) -> StepResult:
        """在主进程中直接连接 CDP 浏览器执行。"""
        from services.browser.cdp_client import connect_over_cdp
        from services.browser.cdp_launcher import launch_cdp_browser

        cdp_info = launch_cdp_browser(headless=self._headless)
        browser = connect_over_cdp(cdp_info["ws_endpoint"])

        try:
            page = self._create_page(browser)

            result = self._run_fn(browser, page, extra_params)

            try:
                page.close()
            except Exception:
                pass

            return StepResult(
                step_name=self._name,
                status=StepStatus.SUCCESS if result.status == "success" else StepStatus.FAILED,
                message=result.message,
                data=result.data,
            )

        except Exception as error:
            return StepResult(
                step_name=self._name,
                status=StepStatus.FAILED,
                message=f"执行失败: {error}",
            )

        finally:
            try:
                browser.close()
            except Exception:
                pass

    def _create_page(self, browser: CdpBrowser) -> CdpPage:
        """创建页面，如果指定了设备名则应用移动端模拟。"""
        if not self._device_name:
            return browser.new_page()

        from services.meituan.device_profiles import get_device_profile
        profile = get_device_profile(self._device_name)
        return browser.new_page(
            user_agent=profile.user_agent,
            viewport={"width": profile.viewport_width, "height": profile.viewport_height},
            device_scale_factor=profile.device_scale_factor,
            is_mobile=profile.is_mobile,
            has_touch=profile.has_touch,
        )
