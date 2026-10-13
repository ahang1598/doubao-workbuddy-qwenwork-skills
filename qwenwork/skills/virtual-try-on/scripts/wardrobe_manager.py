#!/usr/bin/env python3
"""店铺管理器 — 启动本地 HTTP 服务并唤起浏览器打开管理页面。

自动获取 tmpCode + storeId，启动一个轻量 HTTP 服务托管管理页面，
支持查看衣服列表、删除衣服、更新店铺信息等操作。

本地服务同时充当 API 反向代理，解决浏览器跨域限制。

用法:
    python wardrobe_manager.py
    python wardrobe_manager.py --port 8765
    python wardrobe_manager.py --corp-id xxx --staff-id yyy
"""

from __future__ import annotations

import argparse
import http.server
import json
import os
import signal
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path

# 复用 try_on_cli 中的工具函数
sys.path.insert(0, str(Path(__file__).parent))
from try_on_cli import (
    TEAMBITION_HOST,
    REQUEST_TIMEOUT,
    REQUEST_HEADERS,
    fetch_user_info_from_dws,
    api_tmp_code,
    api_init,
    http_post,
)

DEFAULT_PORT = 8764


_TEMPLATE_PATH = Path(__file__).parent / "wardrobe_manager.html"


def build_html() -> str:
    """读取店铺管理页面 HTML 模板。

    从同目录下的 wardrobe_manager.html 读取，
    所有 API 请求通过本地代理 /proxy/ 路径转发，
    corpId/tmpCode/storeId 由后端自动注入，前端无需关心。
    """
    return _TEMPLATE_PATH.read_text(encoding="utf-8")


# ── HTTP 服务 & API 反向代理 ──────────────────────────────────────────────────

class ProxyHandler(http.server.BaseHTTPRequestHandler):
    """处理页面请求和 API 反向代理（解决跨域问题）。

    路由:
      GET  /           → 返回管理页面 HTML
      POST /proxy/soa/ → 转发到 soa API，自动注入 corpId + tmpCode
      POST /proxy/client/ → 转发到前端 API，自动注入 storeId
    """

    page_bytes: bytes = b""
    corp_id: str = ""
    tmp_code: str = ""
    tmp_token: str = ""

    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(self.page_bytes)))
        self.end_headers()
        self.wfile.write(self.page_bytes)

    def do_POST(self):
        path = self.path

        # 读取请求体
        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length) if content_length > 0 else b"{}"
        try:
            client_payload = json.loads(raw_body)
        except json.JSONDecodeError:
            client_payload = {}

        if path.startswith("/proxy/soa/"):
            api_path = path.replace("/proxy/soa", "", 1)
            target_url = f"{TEAMBITION_HOST}/api/opt/soa/dress-mirror{api_path}"
            client_payload["corpId"] = self.corp_id
            client_payload["tmpCode"] = self.tmp_code

        elif path.startswith("/proxy/client/"):
            api_path = path.replace("/proxy/client", "", 1)
            target_url = f"{TEAMBITION_HOST}/api/opt/dress-mirror{api_path}"
            client_payload["storeId"] = self.tmp_token

        else:
            self._send_json(404, {"success": False, "error": f"未知代理路径: {path}"})
            return

        # 转发请求
        try:
            response = http_post(target_url, client_payload, headers=REQUEST_HEADERS)
            try:
                resp_body = response.json()
            except Exception:
                resp_body = {"success": False, "error": response.text[:500]}
            self._send_json(response.status_code, resp_body)
        except TimeoutError:
            self._send_json(504, {"success": False, "error": "上游 API 请求超时"})
        except ConnectionError as error:
            self._send_json(502, {"success": False, "error": f"上游 API 请求失败: {error}"})
        except Exception as error:
            self._send_json(500, {"success": False, "error": f"代理内部错误: {error}"})

    def _send_json(self, status_code: int, data: dict) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def create_server(
    corp_id: str,
    tmp_code: str,
    tmp_token: str,
    port: int = DEFAULT_PORT,
) -> http.server.HTTPServer:
    """创建 HTTP 服务实例。"""
    page_html = build_html()
    page_bytes = page_html.encode("utf-8")

    ProxyHandler.page_bytes = page_bytes
    ProxyHandler.corp_id = corp_id
    ProxyHandler.tmp_code = tmp_code
    ProxyHandler.tmp_token = tmp_token

    return http.server.HTTPServer(("127.0.0.1", port), ProxyHandler)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="wardrobe_manager.py",
        description="AI导购 · 店铺管理器 — 唤起浏览器管理衣橱",
    )
    parser.add_argument("--port", type=int, default=DEFAULT_PORT,
                        help=f"本地 HTTP 服务端口（默认 {DEFAULT_PORT}）")
    parser.add_argument("--corp-id", required=False, dest="corp_id", default="",
                        help="企业 corpId（可选，自动获取）")
    parser.add_argument("--staff-id", required=False, dest="staff_id", default="",
                        help="员工 userId/staffId（可选，自动获取）")
    parser.add_argument("--tmp-code", required=False, dest="tmp_code", default="",
                        help="已有的 tmpCode（可选，自动获取）")
    parser.add_argument("--daemon", action="store_true", default=False,
                        help=argparse.SUPPRESS)  # 内部参数，由 spawn_daemon 自动传入
    return parser.parse_args()


def get_pid_file(port: int) -> Path:
    """返回 PID 文件路径。"""
    return Path(__file__).parent / f".wardrobe_manager_{port}.pid"


def spawn_daemon(corp_id: str, tmp_code: str, port: int) -> int:
    """以独立子进程方式启动守护服务（跨平台兼容）。

    通过 subprocess.Popen 重新启动本脚本的 --daemon 模式，
    macOS/Linux/Windows 均可用，子进程完全脱离父进程生命周期。
    返回子进程 PID。
    """
    daemon_cmd = [
        sys.executable, str(Path(__file__).resolve()),
        "--daemon",
        "--corp-id", corp_id,
        "--tmp-code", tmp_code,
        "--port", str(port),
    ]

    kwargs: dict = {}

    if sys.platform == "win32":
        # Windows: 使用 CREATE_NO_WINDOW + CREATE_NEW_PROCESS_GROUP 脱离父进程
        CREATE_NO_WINDOW = 0x08000000
        CREATE_NEW_PROCESS_GROUP = 0x00000200
        kwargs["creationflags"] = CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP
    else:
        # Unix: 在新会话中启动，脱离终端
        kwargs["start_new_session"] = True

    # stdin/stdout/stderr 重定向到 DEVNULL，完全脱离终端 IO
    process = subprocess.Popen(
        daemon_cmd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        **kwargs,
    )
    return process.pid

def run_daemon_server(corp_id: str, tmp_code: str, port: int) -> None:
    """守护进程内部执行：启动 HTTP 服务并阻塞运行。

    仅由 --daemon 模式调用，不应被外部直接调用。
    """
    # 初始化获取 storeId
    tmp_token = api_init(corp_id=corp_id, tmp_code=tmp_code)

    server = create_server(corp_id=corp_id, tmp_code=tmp_code, tmp_token=tmp_token, port=port)

    pid_file = get_pid_file(port)
    pid_file.write_text(str(os.getpid()))

    def shutdown_server():
        server.shutdown()
        pid_file.unlink(missing_ok=True)
        os._exit(0)

    def handle_shutdown(signum, frame):
        shutdown_server()

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)
    if sys.platform != "win32":
        signal.signal(signal.SIGHUP, signal.SIG_IGN)

    # 半小时后自动关闭
    auto_shutdown_timer = threading.Timer(30 * 60, shutdown_server)
    auto_shutdown_timer.daemon = True
    auto_shutdown_timer.start()

    server.serve_forever()

def main() -> None:
    args = parse_args()

    # --daemon 模式：由 spawn_daemon 启动，直接运行服务
    if args.daemon:
        run_daemon_server(
            corp_id=args.corp_id,
            tmp_code=args.tmp_code,
            port=args.port,
        )
        return

    # 正常模式：获取鉴权信息 → 启动守护子进程 → 打开浏览器 → 退出
    if args.tmp_code and args.corp_id:
        corp_id = args.corp_id
        tmp_code = args.tmp_code
    else:
        print("🔑 正在获取用户信息和鉴权码...")
        user_info = fetch_user_info_from_dws()
        corp_id = args.corp_id or user_info["corpId"]
        tmp_code = args.tmp_code or api_tmp_code(
            corp_id=corp_id,
            staff_id=args.staff_id or user_info["staffId"],
            org_user_name=user_info.get("orgUserName", ""),
            org_user_mobile=user_info.get("orgUserMobile", ""),
            org_name=user_info.get("orgName", ""),
        )
        print("✅ 鉴权码获取成功")

    # 验证 storeId 可获取（确认鉴权有效）
    print("📦 正在初始化试衣间...")
    api_init(corp_id=corp_id, tmp_code=tmp_code)
    print("✅ 试衣间初始化完成")

    port = args.port
    url = f"http://127.0.0.1:{port}"

    # 以独立子进程方式启动守护服务
    daemon_pid = spawn_daemon(corp_id=corp_id, tmp_code=tmp_code, port=port)

    print(f"🪞 店铺管理页面已启动: {url}")

    # 打开浏览器
    webbrowser.open(url)

    # 输出 JSON 供调用方解析
    pid_file = get_pid_file(port)
    print(json.dumps({
        "success": True,
        "url": url,
        "port": port,
        "pid": daemon_pid,
        "pid_file": str(pid_file),
    }, ensure_ascii=False))

if __name__ == "__main__":
    main()
