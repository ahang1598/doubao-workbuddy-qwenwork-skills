"""
使用 CDP 启动系统 Chrome，打开 www.baidu.com，等待 5s 后退出。
纯标准库实现，无需安装任何第三方依赖。
"""

import base64
import json
import os
import platform
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from urllib.parse import urlparse

CDP_PORT = 9222


# ── WebSocket 客户端（纯标准库实现） ──────────────────────────────

class SimpleWebSocket:
    """基于标准库 socket 的最小 WebSocket 客户端，仅支持 CDP 场景。"""

    def __init__(self, url: str, timeout: float = 5.0):
        parsed = urlparse(url)
        self.host = parsed.hostname or "127.0.0.1"
        self.port = parsed.port or 80
        self.path = parsed.path or "/"

        self.sock = socket.create_connection((self.host, self.port), timeout=timeout)
        self.sock.settimeout(timeout)
        self._handshake()

    def _handshake(self) -> None:
        key = base64.b64encode(os.urandom(16)).decode()
        request_lines = [
            f"GET {self.path} HTTP/1.1",
            f"Host: {self.host}:{self.port}",
            "Upgrade: websocket",
            "Connection: Upgrade",
            f"Sec-WebSocket-Key: {key}",
            "Sec-WebSocket-Version: 13",
            "",
            "",
        ]
        self.sock.sendall("\r\n".join(request_lines).encode())

        # 读取响应头直到遇到空行
        response = b""
        while b"\r\n\r\n" not in response:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("WebSocket 握手失败：连接关闭")
            response += chunk

        status_line = response.split(b"\r\n")[0].decode()
        if "101" not in status_line:
            raise ConnectionError(f"WebSocket 握手失败: {status_line}")

    def send(self, message: str) -> None:
        payload = message.encode("utf-8")
        mask_key = os.urandom(4)

        # 构建帧头：FIN=1, opcode=0x1(text), MASK=1
        header = bytearray()
        header.append(0x81)

        length = len(payload)
        if length < 126:
            header.append(0x80 | length)
        elif length < 65536:
            header.append(0x80 | 126)
            header.extend(struct.pack("!H", length))
        else:
            header.append(0x80 | 127)
            header.extend(struct.pack("!Q", length))

        header.extend(mask_key)

        masked_payload = bytearray(
            byte ^ mask_key[i % 4] for i, byte in enumerate(payload)
        )
        self.sock.sendall(bytes(header) + bytes(masked_payload))

    def recv(self) -> str:
        header = self._recv_exact(2)
        opcode = header[0] & 0x0F
        masked = (header[1] & 0x80) != 0
        length = header[1] & 0x7F

        if length == 126:
            length = struct.unpack("!H", self._recv_exact(2))[0]
        elif length == 127:
            length = struct.unpack("!Q", self._recv_exact(8))[0]

        if masked:
            mask_key = self._recv_exact(4)
            raw = self._recv_exact(length)
            data = bytearray(byte ^ mask_key[i % 4] for i, byte in enumerate(raw))
        else:
            data = self._recv_exact(length)

        if opcode == 0x1:
            return bytes(data).decode("utf-8")
        if opcode == 0x8:
            raise ConnectionError("WebSocket 连接被关闭")
        return bytes(data).decode("utf-8", errors="replace")

    def _recv_exact(self, num_bytes: int) -> bytearray:
        buffer = bytearray()
        while len(buffer) < num_bytes:
            chunk = self.sock.recv(num_bytes - len(buffer))
            if not chunk:
                raise ConnectionError("连接意外关闭")
            buffer.extend(chunk)
        return buffer

    def close(self) -> None:
        try:
            close_frame = bytearray([0x88, 0x80]) + os.urandom(4)
            self.sock.sendall(bytes(close_frame))
        except OSError:
            pass
        finally:
            self.sock.close()


# ── Chrome 查找 & CDP 工具函数 ────────────────────────────────────

def find_chrome() -> str:
    """查找系统 Chrome 可执行路径。"""
    system = platform.system()

    if system == "Darwin":
        mac_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        if os.path.exists(mac_path):
            return mac_path

    if system == "Linux":
        for name in ("google-chrome-stable", "google-chrome", "chromium-browser", "chromium"):
            path = shutil.which(name)
            if path:
                return path

    if system == "Windows":
        for base in (os.environ.get("PROGRAMFILES", ""), os.environ.get("PROGRAMFILES(X86)", "")):
            candidate = os.path.join(base, "Google", "Chrome", "Application", "chrome.exe")
            if os.path.exists(candidate):
                return candidate

    raise FileNotFoundError("未找到系统 Chrome，请手动指定路径")


def wait_for_cdp_ready(port: int, timeout: float = 10.0) -> str:
    """轮询等待 CDP 端口就绪，返回 webSocketDebuggerUrl。"""
    url = f"http://127.0.0.1:{port}/json/version"
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                data = json.loads(response.read().decode())
                ws_endpoint = data.get("webSocketDebuggerUrl")
                if ws_endpoint:
                    return ws_endpoint
        except (urllib.error.URLError, OSError, json.JSONDecodeError):
            pass
        time.sleep(0.3)

    raise TimeoutError(f"CDP 端口 {port} 在 {timeout}s 内未就绪")


def navigate_via_cdp(port: int, target_url: str) -> None:
    """通过 CDP WebSocket 协议导航到指定 URL（纯标准库实现）。"""
    tabs_url = f"http://127.0.0.1:{port}/json"
    with urllib.request.urlopen(tabs_url, timeout=5) as response:
        tabs = json.loads(response.read().decode())

    page_tab = next((tab for tab in tabs if tab.get("type") == "page"), None)
    if not page_tab:
        raise RuntimeError("未找到可用的浏览器 tab")

    ws_url = page_tab["webSocketDebuggerUrl"]
    ws_conn = SimpleWebSocket(ws_url, timeout=5)

    try:
        navigate_command = json.dumps({
            "id": 1,
            "method": "Page.navigate",
            "params": {"url": target_url},
        })
        ws_conn.send(navigate_command)
        result = json.loads(ws_conn.recv())
        frame_id = result.get("result", {}).get("frameId", "N/A")
        print(f"📄 已打开页面: {target_url} (frameId={frame_id})")
    finally:
        ws_conn.close()


# ── 主流程 ────────────────────────────────────────────────────────

def main() -> None:
    chrome_path = find_chrome()
    print(f"🔍 找到 Chrome: {chrome_path}")

    user_data_dir = tempfile.mkdtemp(prefix="chrome_cdp_")
    print(f"📁 临时用户数据目录: {user_data_dir}")

    chrome_args = [
        chrome_path,
        f"--remote-debugging-port={CDP_PORT}",
        f"--user-data-dir={user_data_dir}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-extensions",
        "about:blank",
    ]

    print(f"🚀 启动 Chrome (CDP port={CDP_PORT})...")
    chrome_process = subprocess.Popen(
        chrome_args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

    try:
        ws_endpoint = wait_for_cdp_ready(CDP_PORT)
        print(f"✅ CDP 已就绪: {ws_endpoint}")

        navigate_via_cdp(CDP_PORT, "https://www.baidu.com")

        print("⏳ 等待 5 秒...")
        time.sleep(5)

    except Exception as error:
        print(f"❌ 出错: {error}", file=sys.stderr)
    finally:
        print("🛑 关闭 Chrome...")
        chrome_process.terminate()
        chrome_process.wait(timeout=5)
        print("👋 完成")


if __name__ == "__main__":
    main()
