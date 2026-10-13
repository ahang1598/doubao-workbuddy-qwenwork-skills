"""
纯标准库 CDP（Chrome DevTools Protocol）客户端。

提供 SimpleWebSocket / CdpBrowser / CdpPage 三层封装，

公开 API：
- CdpBrowser(ws_endpoint)  — 连接已有 CDP 浏览器实例
- CdpPage                  — 单个页面的操作封装（goto / url / title / inner_text / screenshot / …）
"""

from __future__ import annotations

import base64
import json
import os
import socket
import struct
import threading
import time
from typing import Any, Callable
from urllib.parse import urlparse
import urllib.request
import urllib.error


# ── WebSocket 客户端（纯标准库） ─────────────────────────────────

class SimpleWebSocket:
    """基于标准库 socket 的最小 WebSocket 客户端，仅支持 CDP 场景。"""

    def __init__(self, url: str, timeout: float = 30.0):
        parsed = urlparse(url)
        self.host = parsed.hostname or "127.0.0.1"
        self.port = parsed.port or 80
        self.path = parsed.path or "/"

        self.sock = socket.create_connection((self.host, self.port), timeout=timeout)
        self.sock.settimeout(timeout)
        self._handshake()
        self._lock = threading.Lock()

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

        header = bytearray()
        header.append(0x81)  # FIN=1, opcode=text

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

        with self._lock:
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


# ── CDP 会话封装 ─────────────────────────────────────────────────

class CdpSession:
    """对单个 CDP target 的 WebSocket 连接，提供 send_command / recv 等方法。"""

    def __init__(self, ws_url: str, timeout: float = 30.0):
        self._ws = SimpleWebSocket(ws_url, timeout=timeout)
        self._command_id = 0
        self._timeout = timeout

    def send_command(self, method: str, params: dict | None = None) -> dict:
        """发送 CDP 命令并等待对应 id 的响应。"""
        self._command_id += 1
        command_id = self._command_id

        message = {"id": command_id, "method": method}
        if params:
            message["params"] = params

        self._ws.send(json.dumps(message))

        deadline = time.monotonic() + self._timeout
        while time.monotonic() < deadline:
            raw = self._ws.recv()
            response = json.loads(raw)
            if response.get("id") == command_id:
                if "error" in response:
                    error_info = response["error"]
                    raise RuntimeError(
                        f"CDP 命令 {method} 失败: {error_info.get('message', error_info)}"
                    )
                return response.get("result", {})
            # 忽略事件消息，继续等待

        raise TimeoutError(f"CDP 命令 {method} 超时 ({self._timeout}s)")

    def send_command_no_wait(self, method: str, params: dict | None = None) -> int:
        """发送 CDP 命令但不等待响应，返回 command_id。"""
        self._command_id += 1
        command_id = self._command_id

        message = {"id": command_id, "method": method}
        if params:
            message["params"] = params

        self._ws.send(json.dumps(message))
        return command_id

    def recv_until(
        self,
        predicate: Callable[[dict], bool],
        timeout: float | None = None,
    ) -> dict:
        """持续接收消息直到 predicate 返回 True。"""
        effective_timeout = timeout or self._timeout
        deadline = time.monotonic() + effective_timeout

        while time.monotonic() < deadline:
            raw = self._ws.recv()
            message = json.loads(raw)
            if predicate(message):
                return message

        raise TimeoutError(f"等待消息超时 ({effective_timeout}s)")

    def close(self) -> None:
        self._ws.close()


# ── CdpPage ──────────────────────────────────────────────────────

class CdpPage:
    """单个浏览器页面的 CDP 操作封装。

    提供与 Playwright Page 兼容的常用 API：
    goto / url / title / inner_text / wait_for_timeout / wait_for_url /
    close / screenshot / evaluate
    """

    def __init__(self, session: CdpSession, target_id: str):
        self._session = session
        self._target_id = target_id
        self._enable_domains()

    def _enable_domains(self) -> None:
        """启用必要的 CDP 域。"""
        self._session.send_command("Page.enable")
        self._session.send_command("Runtime.enable")
        self._session.send_command("Network.enable")

    @property
    def url(self) -> str:
        """获取当前页面 URL。"""
        result = self.evaluate("document.location.href")
        return result if isinstance(result, str) else ""

    def title(self) -> str:
        """获取当前页面标题。"""
        result = self.evaluate("document.title")
        return result if isinstance(result, str) else ""

    def goto(
        self,
        url: str,
        *,
        timeout: int = 30000,
        wait_until: str = "load",
    ) -> None:
        """导航到指定 URL。

        Args:
            url: 目标 URL
            timeout: 超时毫秒数
            wait_until: 等待策略 ("load" | "domcontentloaded" | "networkidle")
        """
        self._session.send_command("Page.navigate", {"url": url})

        event_name = {
            "load": "Page.loadEventFired",
            "domcontentloaded": "Page.domContentEventFired",
            "networkidle": "Page.loadEventFired",
        }.get(wait_until, "Page.loadEventFired")

        try:
            self._session.recv_until(
                lambda msg: msg.get("method") == event_name,
                timeout=timeout / 1000.0,
            )
        except TimeoutError:
            raise TimeoutError(f"页面加载超时 ({timeout}ms): {url}")

    def evaluate(self, expression: str) -> Any:
        """在页面上下文中执行 JavaScript 表达式并返回结果。"""
        result = self._session.send_command(
            "Runtime.evaluate",
            {
                "expression": expression,
                "returnByValue": True,
                "awaitPromise": True,
            },
        )
        remote_object = result.get("result", {})

        if result.get("exceptionDetails"):
            exception_text = (
                result["exceptionDetails"]
                .get("exception", {})
                .get("description", "Unknown JS error")
            )
            raise RuntimeError(f"JS 执行异常: {exception_text}")

        return remote_object.get("value")

    def inner_text(self, selector: str) -> str:
        """获取匹配选择器的元素的 innerText。"""
        escaped_selector = selector.replace("\\", "\\\\").replace("'", "\\'")
        expression = f"document.querySelector('{escaped_selector}')?.innerText || ''"
        result = self.evaluate(expression)
        return result if isinstance(result, str) else ""

    def wait_for_timeout(self, timeout_ms: int) -> None:
        """等待指定毫秒数（简单 sleep）。"""
        time.sleep(timeout_ms / 1000.0)

    def wait_for_url(
        self,
        url_or_predicate: str | Callable[[str], bool],
        *,
        timeout: int = 30000,
    ) -> None:
        """等待页面 URL 变化到匹配条件。

        Args:
            url_or_predicate: 目标 URL 字符串或判断函数
            timeout: 超时毫秒数
        """
        if isinstance(url_or_predicate, str):
            target_url = url_or_predicate
            predicate = lambda current_url: current_url == target_url
        else:
            predicate = url_or_predicate

        deadline = time.monotonic() + timeout / 1000.0
        poll_interval = 0.5

        while time.monotonic() < deadline:
            current_url = self.url
            if predicate(current_url):
                return
            time.sleep(poll_interval)

        raise TimeoutError(f"等待 URL 变化超时 ({timeout}ms)")

    def wait_for_selector(
        self,
        selector: str,
        *,
        timeout: int = 30000,
    ) -> None:
        """等待选择器匹配的元素出现在 DOM 中。"""
        escaped_selector = selector.replace("\\", "\\\\").replace("'", "\\'")
        deadline = time.monotonic() + timeout / 1000.0
        poll_interval = 0.3

        while time.monotonic() < deadline:
            result = self.evaluate(
                f"document.querySelector('{escaped_selector}') !== null"
            )
            if result:
                return
            time.sleep(poll_interval)

        raise TimeoutError(f"等待选择器 '{selector}' 超时 ({timeout}ms)")

    def screenshot(self, *, path: str | None = None, full_page: bool = False) -> bytes:
        """截取页面截图。

        Args:
            path: 保存路径（可选）
            full_page: 是否截取整个页面

        Returns:
            PNG 图片的 bytes 数据
        """
        params: dict[str, Any] = {"format": "png"}

        if full_page:
            layout = self._session.send_command(
                "Page.getLayoutMetrics",
            )
            content_size = layout.get("contentSize", layout.get("cssContentSize", {}))
            if content_size:
                params["clip"] = {
                    "x": 0,
                    "y": 0,
                    "width": content_size.get("width", 1920),
                    "height": content_size.get("height", 1080),
                    "scale": 1,
                }

        result = self._session.send_command("Page.captureScreenshot", params)
        image_data = base64.b64decode(result["data"])

        if path:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "wb") as image_file:
                image_file.write(image_data)

        return image_data

    def close(self) -> None:
        """关闭当前页面。"""
        try:
            self._session.send_command(
                "Target.closeTarget",
                {"targetId": self._target_id},
            )
        except (RuntimeError, ConnectionError, OSError):
            pass
        finally:
            try:
                self._session.close()
            except OSError:
                pass


# ── CdpBrowser ───────────────────────────────────────────────────

class CdpBrowser:
    """CDP 浏览器连接封装。

    通过 CDP WebSocket endpoint 连接已有浏览器实例，
    提供 new_page / close / version 等方法。
    """

    def __init__(self, ws_endpoint: str, timeout: float = 30.0):
        self._ws_endpoint = ws_endpoint
        self._timeout = timeout
        self._port = self._extract_port(ws_endpoint)
        self._session = CdpSession(ws_endpoint, timeout=timeout)
        self._version: str | None = None
        self._pages: list[CdpPage] = []

    @staticmethod
    def _extract_port(ws_endpoint: str) -> int:
        """从 ws_endpoint 中提取端口号。"""
        parsed = urlparse(ws_endpoint)
        return parsed.port or 9222

    @property
    def version(self) -> str:
        """获取浏览器版本号。"""
        if self._version is None:
            try:
                url = f"http://127.0.0.1:{self._port}/json/version"
                with urllib.request.urlopen(url, timeout=5) as response:
                    data = json.loads(response.read().decode())
                    self._version = data.get("Browser", "unknown")
            except (urllib.error.URLError, OSError, json.JSONDecodeError):
                self._version = "unknown"
        return self._version

    def new_page(
        self,
        *,
        user_agent: str | None = None,
        viewport: dict[str, int] | None = None,
        device_scale_factor: float | None = None,
        is_mobile: bool | None = None,
        has_touch: bool | None = None,
    ) -> CdpPage:
        """创建新页面（tab）。

        Args:
            user_agent: 自定义 User-Agent
            viewport: 视口尺寸 {"width": int, "height": int}
            device_scale_factor: 设备像素比
            is_mobile: 是否模拟移动端
            has_touch: 是否支持触摸

        Returns:
            CdpPage 实例
        """
        result = self._session.send_command(
            "Target.createTarget",
            {"url": "about:blank"},
        )
        target_id = result["targetId"]

        target_ws_url = self._get_target_ws_url(target_id)
        page_session = CdpSession(target_ws_url, timeout=self._timeout)
        page = CdpPage(page_session, target_id)

        if user_agent:
            page._session.send_command(
                "Network.setUserAgentOverride",
                {"userAgent": user_agent},
            )

        if viewport or device_scale_factor or is_mobile is not None or has_touch is not None:
            metrics_params: dict[str, Any] = {
                "width": viewport.get("width", 0) if viewport else 0,
                "height": viewport.get("height", 0) if viewport else 0,
                "deviceScaleFactor": device_scale_factor or 0,
                "mobile": is_mobile if is_mobile is not None else False,
            }
            page._session.send_command(
                "Emulation.setDeviceMetricsOverride",
                metrics_params,
            )

            if has_touch:
                page._session.send_command(
                    "Emulation.setTouchEmulationEnabled",
                    {"enabled": True},
                )

        self._pages.append(page)
        return page

    def _get_target_ws_url(self, target_id: str) -> str:
        """通过 HTTP API 获取指定 target 的 WebSocket URL。"""
        tabs_url = f"http://127.0.0.1:{self._port}/json"
        with urllib.request.urlopen(tabs_url, timeout=5) as response:
            tabs = json.loads(response.read().decode())

        for tab in tabs:
            if tab.get("id") == target_id:
                ws_url = tab.get("webSocketDebuggerUrl")
                if ws_url:
                    return ws_url

        raise RuntimeError(f"未找到 target {target_id} 的 WebSocket URL")

    def close(self) -> None:
        """关闭浏览器连接（不关闭浏览器进程本身）。"""
        for page in self._pages:
            try:
                page.close()
            except (RuntimeError, ConnectionError, OSError):
                pass
        self._pages.clear()

        try:
            self._session.close()
        except OSError:
            pass

    def __enter__(self) -> CdpBrowser:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


# ── 便捷工厂函数 ─────────────────────────────────────────────────

def connect_over_cdp(ws_endpoint: str, *, timeout: float = 30.0) -> CdpBrowser:
    """通过 CDP WebSocket endpoint 连接浏览器。

    等价于 playwright.chromium.connect_over_cdp() 的替代。
    """
    return CdpBrowser(ws_endpoint, timeout=timeout)
