"""
淘宝登录验证服务。

通过独立子进程启动 CDP 浏览器，打开淘宝登录页等待用户登录。
主进程启动子进程后直接返回，子进程独立运行（超时自动退出）。
"""

from pathlib import Path

from services.browser.cdp_launcher import launch_cdp_browser
from utils.envs import get_log_dir
from utils.process import launch_detached_script

_WORKER_SCRIPT = Path(__file__).parent / "_taobao_login_worker.py"
_DEFAULT_TIMEOUT_SECONDS = 30


def start_taobao_login(*, timeout: int = _DEFAULT_TIMEOUT_SECONDS) -> dict:
    """启动淘宝登录验证（非阻塞，主进程直接返回）。

    1. 确保 CDP 浏览器实例可用（非无头模式，用户需要看到登录页面）
    2. 通过独立子进程打开淘宝登录页
    3. 主进程立即返回，子进程独立运行

    Args:
        timeout: 登录超时秒数，默认 30s

    Returns:
        {"worker_pid": int, "ws_endpoint": str, "timeout": int}
    """
    cdp_info = launch_cdp_browser(headless=False)
    ws_endpoint = cdp_info["ws_endpoint"]

    worker_args = [
        "--ws-endpoint", ws_endpoint,
        "--timeout", str(timeout),
    ]

    log_dir = get_log_dir("workflows")
    stdout_log = log_dir / "taobao-login.stdout.log"
    stderr_log = log_dir / "taobao-login.stderr.log"

    print(f"🚀 启动淘宝登录验证 (timeout={timeout}s)...")
    print(f"   WebSocket endpoint: {ws_endpoint}")

    process = launch_detached_script(
        _WORKER_SCRIPT,
        worker_args,
        stdout_log=stdout_log,
        stderr_log=stderr_log,
    )

    print(f"   Worker PID: {process.pid}")
    print(f"✅ 登录验证子进程已启动，请编写一个 bash 脚本, 每间隔 3s 检查一下进程 {process.pid} 是否存活, 若不存活则询问用户是否完成登录。")

    return {
        "worker_pid": process.pid,
        "ws_endpoint": ws_endpoint,
        "timeout": timeout,
    }