"""
Detached 子进程入口脚本。

由 detached_launcher.py 通过 launch_detached_script 启动。
通过 --fn 参数动态加载指定的函数，
连接 CDP 浏览器、创建 page、执行 fn(browser, page, params)、写入结果文件。

纯标准库 CDP 实现，无需 Playwright。

用法（由 detached_launcher.py 自动调用，不需要手动执行）：
    python _detached_worker_runner.py \
        --fn services.meituan.steps.check_login.run \
        --ws-endpoint ws://127.0.0.1:9222/devtools/browser/xxx \
        --result-file /path/to/result.json \
        --timeout 120

    可选参数：
        --device-name iphone14    （移动端设备模拟）
        --extra '{"key":"value"}' （传递给函数的额外 JSON 参数）
"""

import argparse
import importlib
import json
import os
import sys
import time
from typing import Callable

from services.browser_pipeline.browser_step import WorkerResult

def _load_fn(fn_path: str) -> Callable:
    """通过完整路径动态加载函数。

    Args:
        fn_path: 如 "services.meituan.steps.check_login.run"

    Returns:
        可调用的函数对象
    """
    module_path, fn_name = fn_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    fn = getattr(module, fn_name)

    if not callable(fn):
        raise TypeError(f"{fn_path} 不是可调用对象")

    return fn

def _create_page_with_device(browser, device_name: str | None):
    """创建页面，如果指定了设备名则应用移动端模拟。"""
    if not device_name:
        return browser.new_page()

    from services.meituan.device_profiles import get_device_profile
    profile = get_device_profile(device_name)
    return browser.new_page(
        user_agent=profile.user_agent,
        viewport={"width": profile.viewport_width, "height": profile.viewport_height},
        device_scale_factor=profile.device_scale_factor,
        is_mobile=profile.is_mobile,
        has_touch=profile.has_touch,
    )

def _write_result(
    result_file: str,
    result: WorkerResult,
    fn_path: str,
    stdout_log: str | None = None,
) -> None:
    """将 WorkerResult 序列化为 JSON 写入结果文件。"""
    payload = {
        "status": result.status,
        "message": result.message,
        "data": result.data,
        "run_fn": fn_path,
        "pid": os.getpid(),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    if stdout_log:
        payload["logs"] = _read_tail_lines(stdout_log)
    with open(result_file, "w", encoding="utf-8") as file_handle:
        json.dump(payload, file_handle, ensure_ascii=False, indent=2)
    print(f"📝 结果已写入: {result_file}", flush=True)

def _read_tail_lines(file_path: str, max_lines: int = 1000) -> str:
    """读取文件最后 max_lines 行。"""
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
            tail = lines[-max_lines:] if len(lines) > max_lines else lines
            return "".join(tail)
    except (OSError, IOError):
        return ""

def _run_worker(args, run_fn: Callable, extra_params: dict) -> WorkerResult:
    """通过 CDP 连接浏览器并执行 run_fn。"""
    from services.browser.cdp_client import connect_over_cdp

    browser = connect_over_cdp(args.ws_endpoint)
    try:
        print(f"✅ 浏览器连接成功 (version: {browser.version})", flush=True)

        page = _create_page_with_device(browser, args.device_name)
        print("✅ 页面已创建", flush=True)

        return run_fn(browser, page, extra_params)

    except Exception as error:
        print(f"❌ 子进程异常: {error}", file=sys.stderr, flush=True)
        return WorkerResult(
            status="failed",
            message=f"子进程执行异常: {error}",
        )
    finally:
        try:
            browser.close()
        except Exception:
            pass

def main() -> None:
    parser = argparse.ArgumentParser(description="Detached worker 子进程入口")
    parser.add_argument("--fn", required=True, help="子进程函数的完整模块路径")
    parser.add_argument("--ws-endpoint", required=True, help="CDP WebSocket endpoint")
    parser.add_argument("--result-file", required=True, help="结果 JSON 文件路径")
    parser.add_argument("--timeout", type=int, default=120, help="超时秒数")
    parser.add_argument("--device-name", default=None, help="设备模拟配置名称")
    parser.add_argument("--extra", default=None, help="传递给函数的额外 JSON 参数")
    parser.add_argument("--stdout-log", default=None, help="stdout 日志文件路径（退出时截取尾部写入 result）")
    args = parser.parse_args()

    run_fn = _load_fn(args.fn)

    extra_params = {}
    if args.extra:
        extra_params = json.loads(args.extra)

    print(f"🚀 启动子进程任务 (PID={os.getpid()})", flush=True)
    print(f"   函数: {args.fn}", flush=True)
    print(f"   超时: {args.timeout}s", flush=True)
    if args.device_name:
        print(f"   设备: {args.device_name}", flush=True)

    result = _run_worker(args, run_fn, extra_params)

    _write_result(args.result_file, result, args.fn, stdout_log=args.stdout_log)

    if result.status == "failed":
        sys.exit(1)

if __name__ == "__main__":
    main()