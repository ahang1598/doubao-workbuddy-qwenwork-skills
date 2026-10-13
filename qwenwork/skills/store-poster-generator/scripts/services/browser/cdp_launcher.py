"""
CDP 启动器：通过独立子进程（_cdp_server.py）启动 Chrome 并暴露 CDP 服务。

独立子进程内部直接通过 subprocess 启动 Chrome 并开启远程调试端口，
主进程退出后子进程仍然存活，支持单例复用与优雅停止。

公开 API：
- launch_cdp_browser(port, headless) -> {"pid", "port", "ws_endpoint"}
- stop_cdp_browser(port) -> bool
"""

import json
import os
import signal
import time
import urllib.request
import urllib.error
from pathlib import Path

from utils.envs import get_log_dir
from utils.process import launch_detached_script

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

DEFAULT_CDP_PORT = 9222
_CDP_POLL_INTERVAL_SECONDS = 3
_CDP_MAX_POLL_ATTEMPTS = 30

# _cdp_server.py 脚本路径（与本文件同目录）
_CDP_SERVER_SCRIPT = Path(__file__).parent / "_cdp_server.py"


# ---------------------------------------------------------------------------
# 运行时目录 / 文件
# ---------------------------------------------------------------------------


def _get_cdp_runtime_dir() -> Path:
    """获取 CDP 运行时文件存放目录（PID 文件、endpoint 文件等）。"""
    return get_log_dir("cdp-runtime")

def _get_cdp_pid_file(port: int) -> Path:
    return _get_cdp_runtime_dir() / f"chrome-cdp-{port}.pid"

def _get_cdp_endpoint_file(port: int) -> Path:
    return _get_cdp_runtime_dir() / f"chrome-cdp-{port}.endpoint"

def _get_storage_state_path(port: int) -> Path:
    """获取 storage_state 文件路径，用于跨会话保持登录态。"""
    return _get_cdp_runtime_dir() / f"storage-state-{port}.json"

def _get_cdp_user_data_dir(port: int) -> Path:
    runtime_dir = _get_cdp_runtime_dir()
    user_data_dir = runtime_dir / f"chrome-profile-{port}"
    user_data_dir.mkdir(parents=True, exist_ok=True)
    return user_data_dir


# ---------------------------------------------------------------------------
# 进程 / 端口探测
# ---------------------------------------------------------------------------


def _is_process_alive(pid: int) -> bool:
    """检查指定 PID 的进程是否仍然存活。"""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def _probe_cdp_endpoint(port: int) -> str | None:
    """探测 CDP 服务是否可用，返回 webSocketDebuggerUrl 或 None。"""
    url = f"http://127.0.0.1:{port}/json/version"
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            data = json.loads(response.read().decode())
            return data.get("webSocketDebuggerUrl")
    except (urllib.error.URLError, OSError, json.JSONDecodeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# 复用 / 等待
# ---------------------------------------------------------------------------


def _try_reuse_existing_cdp(port: int) -> dict | None:
    """尝试复用已有的 CDP 实例。

    优先探测 CDP 端口是否有服务响应（不依赖 PID 文件），
    有响应则直接复用，无需关心是谁启动的。
    返回 {"pid": int | None, "port": int, "ws_endpoint": str} 或 None。
    """
    ws_endpoint = _probe_cdp_endpoint(port)
    if ws_endpoint:
        pid = _read_pid_file(port)
        print(f"♻️  复用已有 CDP 实例 (port={port}, PID={pid or 'unknown'})")
        return {"pid": pid, "port": port, "ws_endpoint": ws_endpoint}

    pid = _read_pid_file(port)
    if pid is not None:
        if _is_process_alive(pid):
            print(f"⚠️  进程 {pid} 存活但 CDP 端口 {port} 无响应，尝试终止")
            try:
                os.kill(pid, signal.SIGTERM)
                time.sleep(1)
            except OSError:
                pass
        else:
            print(f"⚠️  PID {pid} 已不存在，清理残留文件")
        _get_cdp_pid_file(port).unlink(missing_ok=True)
        _get_cdp_endpoint_file(port).unlink(missing_ok=True)

    return None


def _read_pid_file(port: int) -> int | None:
    """读取 PID 文件，返回 PID 或 None。"""
    pid_file = _get_cdp_pid_file(port)
    if not pid_file.is_file():
        return None
    try:
        return int(pid_file.read_text().strip())
    except (ValueError, OSError):
        pid_file.unlink(missing_ok=True)
        return None


def _wait_for_cdp_ready(endpoint_file: Path, port: int) -> str:
    """轮询等待 endpoint 文件出现或 CDP 端口就绪，返回 ws_endpoint。

    每隔 _CDP_POLL_INTERVAL_SECONDS 秒检测一次，最多尝试 _CDP_MAX_POLL_ATTEMPTS 次。
    同时检测 endpoint 文件和 CDP 端口，任一就绪即返回。
    """
    for attempt in range(1, _CDP_MAX_POLL_ATTEMPTS + 1):
        if endpoint_file.is_file():
            content = endpoint_file.read_text().strip()
            if content:
                return content

        ws_endpoint = _probe_cdp_endpoint(port)
        if ws_endpoint:
            endpoint_file.write_text(ws_endpoint)
            return ws_endpoint

        print(f"   ⏳ 等待 CDP 就绪... ({attempt}/{_CDP_MAX_POLL_ATTEMPTS})")
        time.sleep(_CDP_POLL_INTERVAL_SECONDS)

    raise TimeoutError(
        f"CDP 服务在 {_CDP_MAX_POLL_ATTEMPTS} 次尝试后仍未就绪 (port={port})"
    )


# ---------------------------------------------------------------------------
# 公开 API
# ---------------------------------------------------------------------------


def launch_cdp_browser(
    *,
    port: int = DEFAULT_CDP_PORT,
    headless: bool = True,
) -> dict:
    """通过独立子进程启动 Chrome 并暴露 CDP 服务（单例模式）。

    子进程内部直接通过 subprocess 启动 Chrome 并开启远程调试端口。
    主进程退出后子进程仍然存活（detach），支持后续通过 CDP WebSocket 复用。

    Args:
        port: CDP 远程调试端口，默认 9222
        headless: 是否无头模式，默认 True

    Returns:
        {"pid": int, "port": int, "ws_endpoint": str}
    """
    existing = _try_reuse_existing_cdp(port)
    if existing:
        return existing

    user_data_dir = _get_cdp_user_data_dir(port)
    endpoint_file = _get_cdp_endpoint_file(port)
    endpoint_file.unlink(missing_ok=True)

    log_dir = _get_cdp_runtime_dir()
    stdout_log_path = log_dir / f"chrome-cdp-{port}.stdout.log"
    stderr_log_path = log_dir / f"chrome-cdp-{port}.stderr.log"

    storage_state_file = _get_storage_state_path(port)

    server_args = [
        "--port", str(port),
        "--user-data-dir", str(user_data_dir),
        "--endpoint-file", str(endpoint_file),
        "--storage-state-file", str(storage_state_file),
    ]
    if headless:
        server_args.append("--headless")

    print(f"🚀 启动 CDP 服务 (port={port}, headless={headless})...")
    print(f"   用户数据目录: {user_data_dir}")

    process = launch_detached_script(
        _CDP_SERVER_SCRIPT,
        server_args,
        stdout_log=stdout_log_path,
        stderr_log=stderr_log_path,
    )

    pid_file = _get_cdp_pid_file(port)
    pid_file.write_text(str(process.pid))
    print(f"   PID: {process.pid} (已写入 {pid_file})")

    try:
        ws_endpoint = _wait_for_cdp_ready(endpoint_file, port)
    except TimeoutError:
        error_detail = ""
        if stderr_log_path.is_file():
            error_detail = stderr_log_path.read_text()[-1500:]
        pid_file.unlink(missing_ok=True)
        raise RuntimeError(
            f"CDP 服务启动超时 (port={port}, PID={process.pid})\n"
            f"stderr 尾部:\n{error_detail}"
        )

    print("✅ CDP 服务已就绪")
    print(f"   WebSocket endpoint: {ws_endpoint}")

    return {"pid": process.pid, "port": port, "ws_endpoint": ws_endpoint}


def stop_cdp_browser(port: int = DEFAULT_CDP_PORT) -> bool:
    """停止指定端口的 CDP Chrome 实例。

    向子进程发送 SIGTERM，_cdp_server.py 收到后会优雅关闭浏览器。
    """
    pid_file = _get_cdp_pid_file(port)
    if not pid_file.is_file():
        print(f"⚠️  未找到 port={port} 的 PID 文件，可能未启动")
        return False

    try:
        pid = int(pid_file.read_text().strip())
    except (ValueError, OSError):
        pid_file.unlink(missing_ok=True)
        return False

    if _is_process_alive(pid):
        print(f"🛑 终止 CDP 服务进程 (PID={pid}, port={port})...")
        try:
            os.kill(pid, signal.SIGTERM)
            for _ in range(50):
                if not _is_process_alive(pid):
                    break
                time.sleep(0.1)
            else:
                os.kill(pid, signal.SIGKILL)
        except OSError:
            pass

    pid_file.unlink(missing_ok=True)
    _get_cdp_endpoint_file(port).unlink(missing_ok=True)
    print(f"✅ CDP 服务已停止 (port={port})")
    return True
