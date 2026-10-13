"""
Detached 子进程启动器。

封装"启动 detached worker 子进程"的通用逻辑，供 DetachedWorkerStep 调用。
主进程调用 launch_detached_step() 后立即返回，子进程独立运行。

公开 API：
- launch_detached_step(run_fn, ...) -> DetachedWorkerHandle
- read_worker_result(result_file) -> dict | None
- is_worker_alive(pid) -> bool
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from services.browser.cdp_launcher import launch_cdp_browser
from utils.envs import get_log_dir
from utils.process import launch_detached_script

_RUNNER_SCRIPT = Path(__file__).parent / "_detached_worker_runner.py"


@dataclass
class DetachedWorkerHandle:
    """detached worker 启动后的句柄信息。

    调用方可通过 worker_pid 监控子进程状态，
    通过 result_file 读取执行结果。
    """
    worker_pid: int
    ws_endpoint: str
    result_file: Path
    stdout_log: Path
    stderr_log: Path
    timeout_seconds: int
    step_name: str


def launch_detached_step(
    run_fn: Callable,
    *,
    step_name: str,
    timeout: int = 120,
    device_name: str | None = None,
    headless: bool = False,
    extra_params: dict[str, Any] | None = None,
    inherit_output: bool = True,
) -> DetachedWorkerHandle:
    """启动一个 detached 子进程执行指定的浏览器任务函数。

    1. 确保 CDP 浏览器实例可用
    2. 通过独立子进程加载并调用 run_fn(browser, page, params)
    3. 主进程立即返回

    Args:
        run_fn: 子进程中执行的函数，签名为 (Browser, Page, dict) -> WorkerResult
        step_name: 步骤名称（用于日志和结果文件命名）
        timeout: 超时秒数
        device_name: 设备模拟名称（None 表示桌面端）
        headless: 是否无头模式
        extra_params: 传递给 run_fn 的参数

    Returns:
        DetachedWorkerHandle 包含 PID、结果文件路径等信息
    """
    cdp_info = launch_cdp_browser(headless=headless)
    ws_endpoint = cdp_info["ws_endpoint"]

    fn_path = f"{run_fn.__module__}.{run_fn.__qualname__}"

    log_dir = get_log_dir("detached-workers")
    result_file = log_dir / f"{step_name}.result.json"
    stdout_log = log_dir / f"{step_name}.stdout.log"
    stderr_log = log_dir / f"{step_name}.stderr.log"

    result_file.unlink(missing_ok=True)

    runner_args = [
        "--fn", fn_path,
        "--ws-endpoint", ws_endpoint,
        "--result-file", str(result_file),
        "--timeout", str(timeout),
        "--stdout-log", str(stdout_log),
    ]
    if device_name:
        runner_args.extend(["--device-name", device_name])
    if extra_params:
        runner_args.extend(["--extra", json.dumps(extra_params, ensure_ascii=False)])

    print(f"🚀 启动 detached worker: {step_name}")
    print(f"   函数: {fn_path}")
    print(f"   WebSocket: {ws_endpoint}")
    print(f"   超时: {timeout}s")
    print(f"   结果文件: {result_file}")

    process = launch_detached_script(
        _RUNNER_SCRIPT,
        runner_args,
        stdout_log=stdout_log,
        stderr_log=stderr_log,
        inherit_output=inherit_output,
    )

    print(f"   Worker PID: {process.pid}")
    print("✅ Worker 子进程已启动")

    return DetachedWorkerHandle(
        worker_pid=process.pid,
        ws_endpoint=ws_endpoint,
        result_file=result_file,
        stdout_log=stdout_log,
        stderr_log=stderr_log,
        timeout_seconds=timeout,
        step_name=step_name,
    )

def read_worker_result(result_file: str | Path) -> dict | None:
    """读取 worker 结果文件。

    Args:
        result_file: 结果 JSON 文件路径

    Returns:
        解析后的 dict，文件不存在或解析失败返回 None
    """
    path = Path(result_file)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def is_worker_alive(pid: int) -> bool:
    """检查 worker 子进程是否仍然存活。"""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False
