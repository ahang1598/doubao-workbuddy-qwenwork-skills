# -*- coding: utf-8 -*-
"""Chrome 进程管理（跨平台）。"""

from __future__ import annotations

import argparse
import contextlib
import json
import logging
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

from wc.stealth import STEALTH_ARGS

logger = logging.getLogger(__name__)

# 默认远程调试端口
DEFAULT_PORT = 9222

# 全局进程追踪
_chrome_process: subprocess.Popen | None = None

# 各平台 Chrome 默认路径
_CHROME_PATHS: dict[str, list[str]] = {
    "Darwin": [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
    ],
    "Linux": [
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/snap/bin/chromium",
    ],
    "Windows": [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ],
}


def _get_default_data_dir() -> str:
    """返回默认 Chrome Profile 目录路径。"""
    return str(Path.home() / ".dingclaw" / "wechat-channels" / "chrome-profile")


def is_port_open(port: int, host: str = "127.0.0.1") -> bool:
    """TCP socket 级端口检测（秒级响应）。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        try:
            s.connect((host, port))
            return True
        except (ConnectionRefusedError, TimeoutError, OSError):
            return False


def find_chrome() -> str | None:
    """查找 Chrome 可执行文件路径。"""
    env_path = os.getenv("CHROME_BIN")
    if env_path and os.path.isfile(env_path):
        return env_path

    chrome = (
        shutil.which("google-chrome")
        or shutil.which("chromium")
        or shutil.which("chrome")
        or shutil.which("chrome.exe")
    )
    if chrome:
        return chrome

    system = platform.system()

    if system == "Windows":
        for env_var in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
            base = os.environ.get(env_var, "")
            if base:
                candidate = os.path.join(base, "Google", "Chrome", "Application", "chrome.exe")
                if os.path.isfile(candidate):
                    return candidate

    for path in _CHROME_PATHS.get(system, []):
        if os.path.isfile(path):
            return path

    return None


def is_chrome_running(port: int = DEFAULT_PORT) -> bool:
    """检查指定端口的 Chrome 是否在运行。"""
    return is_port_open(port)


def launch_chrome(
    port: int = DEFAULT_PORT,
    headless: bool = False,
    user_data_dir: str | None = None,
    chrome_bin: str | None = None,
) -> subprocess.Popen | None:
    """启动 Chrome 进程（带远程调试端口）。"""
    global _chrome_process

    if is_port_open(port):
        logger.info("Chrome 已在运行 (port=%d)，跳过启动", port)
        return None

    if not chrome_bin:
        chrome_bin = find_chrome()
    if not chrome_bin:
        raise FileNotFoundError("未找到 Chrome，请设置 CHROME_BIN 环境变量或安装 Chrome")

    if not user_data_dir:
        user_data_dir = _get_default_data_dir()

    args = [
        chrome_bin,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={user_data_dir}",
        *STEALTH_ARGS,
        "https://channels.weixin.qq.com",
    ]

    if headless:
        args.append("--headless=new")

    proxy = os.getenv("WC_PROXY")
    if proxy:
        args.append(f"--proxy-server={proxy}")
        logger.info("使用代理: %s", _mask_proxy(proxy))

    logger.info("启动 Chrome: port=%d, headless=%s, profile=%s", port, headless, user_data_dir)
    process = subprocess.Popen(
        args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    _chrome_process = process

    _wait_for_chrome(port)
    return process


def close_chrome(process: subprocess.Popen) -> None:
    """关闭 Chrome 进程。"""
    if process.poll() is not None:
        return

    try:
        process.terminate()
        process.wait(timeout=5)
    except (subprocess.TimeoutExpired, OSError):
        process.kill()
        process.wait(timeout=3)

    logger.info("Chrome 进程已关闭")


def kill_chrome(port: int = DEFAULT_PORT) -> None:
    """关闭指定端口的 Chrome 实例。"""
    global _chrome_process

    # 策略1: 通过 CDP 关闭
    try:
        import requests

        resp = requests.get(f"http://127.0.0.1:{port}/json/version", timeout=2)
        if resp.status_code == 200:
            ws_url = resp.json().get("webSocketDebuggerUrl")
            if ws_url:
                import websockets.sync.client

                ws = websockets.sync.client.connect(ws_url)
                ws.send(json.dumps({"id": 1, "method": "Browser.close"}))
                ws.close()
                logger.info("通过 CDP Browser.close 关闭 Chrome (port=%d)", port)
                time.sleep(1)
    except Exception:
        pass

    # 策略2: terminate 追踪的子进程
    if _chrome_process and _chrome_process.poll() is None:
        try:
            _chrome_process.terminate()
            _chrome_process.wait(timeout=5)
            logger.info("通过 terminate 关闭追踪的 Chrome 进程")
        except Exception:
            with contextlib.suppress(Exception):
                _chrome_process.kill()
    _chrome_process = None

    # 策略3: 通过端口查找并终止进程
    if is_port_open(port):
        pids = _find_pids_by_port(port)
        if pids:
            for pid in pids:
                _kill_pid(pid)
            logger.info("通过进程终止关闭 Chrome (port=%d)", port)

    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if not is_port_open(port):
            return
        time.sleep(0.5)

    if is_port_open(port):
        logger.warning("端口 %d 仍被占用，kill 可能未完全生效", port)


def ensure_chrome(
    port: int = DEFAULT_PORT,
    headless: bool = False,
    user_data_dir: str | None = None,
    chrome_bin: str | None = None,
) -> bool:
    """确保 Chrome 在指定端口可用。"""
    if is_port_open(port):
        return True

    try:
        launch_chrome(
            port=port,
            headless=headless,
            user_data_dir=user_data_dir,
            chrome_bin=chrome_bin,
        )
        return is_port_open(port)
    except FileNotFoundError as e:
        logger.error("启动 Chrome 失败: %s", e)
        return False


def restart_chrome(
    port: int = DEFAULT_PORT,
    headless: bool = False,
    user_data_dir: str | None = None,
    chrome_bin: str | None = None,
) -> subprocess.Popen | None:
    """重启 Chrome。"""
    logger.info("重启 Chrome: port=%d, headless=%s", port, headless)
    kill_chrome(port)
    time.sleep(1)
    return launch_chrome(
        port=port,
        headless=headless,
        user_data_dir=user_data_dir,
        chrome_bin=chrome_bin,
    )


def _wait_for_chrome(port: int, timeout: float = 15.0) -> None:
    """等待 Chrome 调试端口就绪。"""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if is_port_open(port):
            logger.info("Chrome 已就绪 (port=%d)", port)
            return
        time.sleep(0.5)
    logger.warning("等待 Chrome 就绪超时 (port=%d)", port)


def _find_pids_by_port(port: int) -> list[int]:
    """查找占用指定端口的进程 PID。"""
    try:
        if sys.platform == "win32":
            result = subprocess.run(
                ["netstat", "-ano", "-p", "TCP"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                return []
            pids: list[int] = []
            for line in result.stdout.splitlines():
                if f":{port}" in line and "LISTENING" in line:
                    parts = line.split()
                    with contextlib.suppress(ValueError, IndexError):
                        pids.append(int(parts[-1]))
            return list(set(pids))
        else:
            result = subprocess.run(
                ["lsof", "-ti", f":{port}"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0 or not result.stdout.strip():
                return []
            pids = []
            for p in result.stdout.strip().split("\n"):
                with contextlib.suppress(ValueError):
                    pids.append(int(p))
            return pids
    except Exception:
        return []


def _kill_pid(pid: int) -> None:
    """终止指定 PID 的进程。"""
    try:
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/F"],
                capture_output=True,
                timeout=5,
            )
        else:
            import signal

            os.kill(pid, signal.SIGTERM)
    except Exception:
        logger.debug("终止进程 %d 失败", pid)


def _mask_proxy(proxy_url: str) -> str:
    """隐藏代理 URL 中的敏感信息。"""
    from urllib.parse import urlparse

    try:
        parsed = urlparse(proxy_url)
        if parsed.username:
            return proxy_url.replace(parsed.username, "***").replace(
                parsed.password or "", "***"
            )
    except Exception:
        pass
    return proxy_url


def has_display() -> bool:
    """检测当前环境是否有图形界面。"""
    system = platform.system()
    if system in ("Windows", "Darwin"):
        return True
    return bool(os.getenv("DISPLAY") or os.getenv("WAYLAND_DISPLAY"))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="Chrome 进程管理")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="调试端口")
    parser.add_argument("--headless", action="store_true", help="无头模式")
    parser.add_argument("--kill", action="store_true", help="关闭 Chrome")
    args = parser.parse_args()

    if args.kill:
        kill_chrome(args.port)
        print(json.dumps({"success": True, "message": "Chrome 已关闭"}))
    else:
        try:
            process = launch_chrome(port=args.port, headless=args.headless)
            if process:
                print(json.dumps({"success": True, "message": f"Chrome 已启动 (port={args.port})"}))
            else:
                print(json.dumps({"success": True, "message": f"Chrome 已在运行 (port={args.port})"}))
        except FileNotFoundError as e:
            print(json.dumps({"success": False, "error": str(e)}))
            sys.exit(2)
