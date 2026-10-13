"""
CDP 服务独立进程脚本。

由 cdp_launcher.py 通过 subprocess.Popen 以 detach 模式启动。
内部直接通过 subprocess 启动 Chrome 并暴露 CDP 端口，
启动成功后将 ws_endpoint 写入 endpoint 文件，然后阻塞等待信号优雅退出。

用法（由 cdp_launcher.py 自动调用，不需要手动执行）：
    python _cdp_server.py --port 9222 --user-data-dir /path/to/profile --endpoint-file /path/to/endpoint
    python _cdp_server.py --port 9222 --user-data-dir /path/to/profile --endpoint-file /path/to/endpoint --headless
"""

import argparse
import json
import signal
import subprocess
import sys
import threading
import time
import urllib.request
import urllib.error


def _wait_for_ws_endpoint(port: int, timeout: float = 15.0) -> str | None:
    """轮询等待 CDP 端口就绪，返回 webSocketDebuggerUrl 或 None。"""
    url = f"http://127.0.0.1:{port}/json/version"
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                data = json.loads(response.read().decode())
                ws_endpoint = data.get("webSocketDebuggerUrl")
                if ws_endpoint:
                    return ws_endpoint
        except (urllib.error.URLError, OSError, json.JSONDecodeError, ValueError):
            pass
        time.sleep(0.3)

    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="CDP 服务独立进程")
    parser.add_argument("--port", type=int, required=True, help="CDP 远程调试端口")
    parser.add_argument("--user-data-dir", required=True, help="用户数据目录")
    parser.add_argument("--endpoint-file", required=True, help="写入 ws_endpoint 的文件路径")
    parser.add_argument("--headless", action="store_true", help="无头模式")
    parser.add_argument("--storage-state-file", default=None, help="（已弃用，保留参数兼容性）")
    args = parser.parse_args()

    shutdown_event = threading.Event()

    def handle_signal(_signum, _frame):
        shutdown_event.set()

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    chrome_process: subprocess.Popen | None = None

    try:
        from services.browser.finder import ensure_chrome
        chrome_path = ensure_chrome()
        if not chrome_path:
            print("❌ 未找到可用的 Chrome/Chromium", file=sys.stderr, flush=True)
            sys.exit(1)

        print(f"🔍 使用 Chrome: {chrome_path}", flush=True)

        chrome_args = [
            chrome_path,
            f"--remote-debugging-port={args.port}",
            f"--user-data-dir={args.user_data_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-session-crashed-bubble",
            "--disable-infobars",
            "--hide-crash-restore-bubble",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            "--noerrdialogs",
            "--disable-extensions",
        ]

        if args.headless:
            chrome_args.append("--headless=new")

        chrome_args.append("about:blank")

        print(f"🚀 启动 Chrome (CDP port={args.port})...", flush=True)
        chrome_process = subprocess.Popen(
            chrome_args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        ws_endpoint = _wait_for_ws_endpoint(args.port)

        if not ws_endpoint:
            print(f"❌ CDP 端口 {args.port} 未就绪", file=sys.stderr, flush=True)
            sys.exit(1)

        # 写入 endpoint 文件，通知主进程
        with open(args.endpoint_file, "w") as endpoint_fp:
            endpoint_fp.write(ws_endpoint)

        print(f"✅ CDP 服务已就绪: {ws_endpoint}", flush=True)

        # 阻塞等待退出信号
        shutdown_event.wait()
        print("🛑 收到退出信号，正在关闭浏览器...", flush=True)

    except Exception as error:
        print(f"❌ CDP 服务异常: {error}", file=sys.stderr, flush=True)
        sys.exit(1)
    finally:
        if chrome_process:
            chrome_process.terminate()
            try:
                chrome_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                chrome_process.kill()

if __name__ == "__main__":
    main()