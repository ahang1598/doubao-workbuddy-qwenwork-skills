"""CDP WebSocket 客户端（Browser, Page, Element）。

通过原生 WebSocket 与 Chrome DevTools Protocol 通信，实现浏览器自动化控制。
基于 xiaohongshu-interact 项目的 cdp.py 适配。
"""

from __future__ import annotations

import json
import logging
import random
import time
from typing import Any

import requests
import websockets.sync.client as ws_client

from .errors import CDPError, ElementNotFoundError
from .stealth import REALISTIC_UA, STEALTH_JS

logger = logging.getLogger(__name__)


def sleep_random(min_seconds: float, max_seconds: float) -> None:
    """随机等待指定范围内的时间，用于模拟真人操作节奏。

    Args:
        min_seconds: 最小等待秒数。
        max_seconds: 最大等待秒数。
    """
    time.sleep(random.uniform(min_seconds, max_seconds))


class CDPClient:
    """底层 CDP WebSocket 通信客户端。"""

    def __init__(self, ws_url: str) -> None:
        self._ws = ws_client.connect(ws_url, max_size=50 * 1024 * 1024)
        self._id = 0
        self._callbacks: dict[int, Any] = {}
        self._event_listeners: dict[str, list[callable]] = {}
        self._event_queue: list[dict[str, Any]] = []
        self._listener_running = False
        self._listener_thread: Any = None

    def send(self, method: str, params: dict | None = None) -> dict:
        """发送 CDP 命令并等待结果。"""
        self._id += 1
        msg: dict[str, Any] = {"id": self._id, "method": method}
        if params:
            msg["params"] = params
        self._ws.send(json.dumps(msg))
        return self._wait_for(self._id)

    def _wait_for(self, msg_id: int, timeout: float = 30.0) -> dict:
        """等待指定 id 的响应。"""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                raw = self._ws.recv(timeout=max(0.1, deadline - time.monotonic()))
            except TimeoutError:
                break
            data = json.loads(raw)
            if data.get("id") == msg_id:
                if "error" in data:
                    raise CDPError(f"CDP 错误: {data['error']}")
                return data.get("result", {})
        raise CDPError(f"等待 CDP 响应超时 (id={msg_id})")

    def close(self) -> None:
        import contextlib

        with contextlib.suppress(Exception):
            self._ws.close()


class Page:
    """CDP 页面对象，封装常用操作。"""

    def __init__(self, cdp: CDPClient, target_id: str, session_id: str) -> None:
        self._cdp = cdp
        self.target_id = target_id
        self.session_id = session_id
        self._ws = cdp._ws
        self._id_counter = 1000
        self._pending_events: list[dict[str, Any]] = []

    def _send_session(self, method: str, params: dict | None = None) -> dict:
        """向 session 发送命令。"""
        self._id_counter += 1
        msg: dict[str, Any] = {
            "id": self._id_counter,
            "method": method,
            "sessionId": self.session_id,
        }
        if params:
            msg["params"] = params
        self._ws.send(json.dumps(msg))
        return self._wait_session(self._id_counter)

    def _wait_session(self, msg_id: int, timeout: float = 60.0) -> dict:
        """等待 session 响应，非目标消息（事件）缓存到 _pending_events。"""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                raw = self._ws.recv(timeout=max(0.1, deadline - time.monotonic()))
            except TimeoutError:
                break
            data = json.loads(raw)
            if data.get("id") == msg_id:
                if "error" in data:
                    raise CDPError(f"CDP 错误: {data['error']}")
                return data.get("result", {})
            # 非目标响应的消息（事件等）缓存起来，避免丢失
            if "method" in data:
                self._pending_events.append(data)
        raise CDPError(f"等待 session 响应超时 (id={msg_id})")

    def navigate(self, url: str) -> None:
        """导航到指定 URL。"""
        logger.info("导航到: %s", url)
        self._send_session("Page.navigate", {"url": url})

    def wait_for_load(self, timeout: float = 60.0) -> None:
        """等待页面加载完成（通过轮询 document.readyState）。"""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                state = self.evaluate("document.readyState")
                if state == "complete":
                    return
            except CDPError:
                pass
            time.sleep(0.5)
        logger.warning("等待页面加载超时")

    def wait_dom_stable(self, timeout: float = 10.0, interval: float = 0.5) -> None:
        """等待 DOM 稳定（连续两次 DOM 快照一致）。"""
        last_html = ""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                html = self.evaluate("document.body ? document.body.innerHTML.length : 0")
                if html == last_html and html != "":
                    return
                last_html = html
            except CDPError:
                pass
            time.sleep(interval)

    def evaluate(self, expression: str, timeout: float = 30.0) -> Any:
        """执行 JavaScript 表达式并返回结果（仅在主文档执行）。"""
        result = self._send_session(
            "Runtime.evaluate",
            {
                "expression": expression,
                "returnByValue": True,
                "awaitPromise": False,
            },
        )
        if "exceptionDetails" in result:
            raise CDPError(f"JS 执行异常: {result['exceptionDetails']}")
        remote_obj = result.get("result", {})
        return remote_obj.get("value")

    def evaluate_in_iframe(self, expression: str) -> Any:
        """在 iframe 内执行 JavaScript 表达式并返回结果。

        先在主文档执行，如果返回 None/null/false 则尝试在所有 iframe 内执行。
        视频号发布页面的内容在 iframe 内，需要穿透 iframe 执行 JS。

        策略：Runtime.evaluate 获取 iframe 对象 → Runtime.callFunctionOn
        在 iframe 上执行 function(){ return iframe.contentDocument 上下文中的表达式 }。
        """
        # 先在主文档执行
        main_result = self.evaluate(expression)
        if main_result is not None and main_result is not False and main_result != 0:
            return main_result

        # 主文档没结果，穿透 iframe 执行
        iframe_count = self.evaluate("document.querySelectorAll('iframe').length")
        if not iframe_count:
            return main_result

        for i in range(iframe_count):
            try:
                # 获取第 i 个 iframe 的 JS objectId
                iframe_result = self._send_session(
                    "Runtime.evaluate",
                    {
                        "expression": f"document.querySelectorAll('iframe')[{i}]",
                        "returnByValue": False,
                    },
                )
                iframe_obj_id = iframe_result.get("result", {}).get("objectId")
                if not iframe_obj_id:
                    continue

                # 在 iframe 的 contentDocument 上下文中执行表达式
                # 将 expression 包装成一个函数，在 iframe.contentDocument 上执行
                call_result = self._send_session(
                    "Runtime.callFunctionOn",
                    {
                        "objectId": iframe_obj_id,
                        "functionDeclaration": (
                            "function() {"
                            "  var document = this.contentDocument;"
                            "  if (!document) return null;"
                            f"  return ({expression});"
                            "}"
                        ),
                        "returnByValue": True,
                    },
                )
                if "exceptionDetails" in call_result:
                    continue
                val = call_result.get("result", {}).get("value")
                if val is not None and val is not False and val != 0:
                    return val
            except CDPError:
                continue

        return main_result

    def evaluate_function(self, function_body: str, *args: Any) -> Any:
        """执行 JavaScript 函数并返回结果。

        function_body 是一个完整的函数体，如 `() => { return 1; }`
        """
        result = self._send_session(
            "Runtime.evaluate",
            {
                "expression": f"({function_body})()",
                "returnByValue": True,
                "awaitPromise": False,
            },
        )
        if "exceptionDetails" in result:
            raise CDPError(f"JS 函数执行异常: {result['exceptionDetails']}")
        remote_obj = result.get("result", {})
        return remote_obj.get("value")

    def query_selector(self, selector: str) -> str | None:
        """查找单个元素，返回 objectId 或 None。"""
        result = self._send_session(
            "Runtime.evaluate",
            {
                "expression": f"document.querySelector({json.dumps(selector)})",
                "returnByValue": False,
            },
        )
        remote_obj = result.get("result", {})
        if remote_obj.get("subtype") == "null" or remote_obj.get("type") == "undefined":
            return None
        return remote_obj.get("objectId")

    def query_selector_all(self, selector: str) -> list[str]:
        """查找多个元素，返回 objectId 列表。"""
        # 通过 JS 返回元素数量，然后逐个获取
        count = self.evaluate(f"document.querySelectorAll({json.dumps(selector)}).length")
        if not count:
            return []
        object_ids = []
        for i in range(count):
            result = self._send_session(
                "Runtime.evaluate",
                {
                    "expression": (f"document.querySelectorAll({json.dumps(selector)})[{i}]"),
                    "returnByValue": False,
                },
            )
            obj = result.get("result", {})
            oid = obj.get("objectId")
            if oid:
                object_ids.append(oid)
        return object_ids

    def has_element(self, selector: str) -> bool:
        """检查元素是否存在（支持 iframe 穿透）。"""
        return self.evaluate_in_iframe(
            f"document.querySelector({json.dumps(selector)}) !== null"
        ) is True

    def wait_for_element(self, selector: str, timeout: float = 30.0) -> str:
        """等待元素出现，返回 objectId。"""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            oid = self.query_selector(selector)
            if oid:
                return oid
            time.sleep(0.5)
        raise ElementNotFoundError(selector)

    def click_element(self, selector: str) -> None:
        """点击指定选择器的元素（通过 CDP Input 事件，isTrusted=true，支持 iframe 穿透）。

        对于 iframe 内的元素，需要加上 iframe 自身的偏移量，
        因为 Input.dispatchMouseEvent 的坐标是相对于视口的。
        """
        # 先在主文档查找
        box = self.evaluate(
            f"""
            (() => {{
                const el = document.querySelector({json.dumps(selector)});
                if (!el) return null;
                el.scrollIntoView({{block: 'center'}});
                const rect = el.getBoundingClientRect();
                return {{x: rect.left + rect.width / 2, y: rect.top + rect.height / 2}};
            }})()
            """
        )

        if not box:
            # 主文档找不到，穿透 iframe 查找
            # 需要获取 iframe 的偏移量 + 元素在 iframe 内的位置
            box = self._click_element_in_iframe(selector)

        if not box:
            return
        x = box["x"] + random.uniform(-3, 3)
        y = box["y"] + random.uniform(-3, 3)
        self.mouse_move(x, y)
        time.sleep(random.uniform(0.03, 0.08))
        self.mouse_click(x, y)

    def _click_element_in_iframe(self, selector: str) -> dict | None:
        """在 iframe 内查找元素并返回视口坐标。

        返回 {"x": ..., "y": ...} 或 None。
        坐标 = iframe 在主文档中的偏移 + 元素在 iframe 内的位置。
        """
        iframe_count = self.evaluate("document.querySelectorAll('iframe').length")
        if not iframe_count:
            return None

        for i in range(iframe_count):
            try:
                # 获取 iframe 在主文档中的偏移
                iframe_box = self.evaluate(
                    f"""
                    (() => {{
                        const iframe = document.querySelectorAll('iframe')[{i}];
                        if (!iframe) return null;
                        const rect = iframe.getBoundingClientRect();
                        return {{x: rect.left, y: rect.top}};
                    }})()
                    """
                )
                if not iframe_box:
                    continue

                # 获取 iframe 的 objectId
                iframe_result = self._send_session(
                    "Runtime.evaluate",
                    {
                        "expression": f"document.querySelectorAll('iframe')[{i}]",
                        "returnByValue": False,
                    },
                )
                iframe_obj_id = iframe_result.get("result", {}).get("objectId")
                if not iframe_obj_id:
                    continue

                # 在 iframe 内查找元素并获取其在 iframe 内的位置
                call_result = self._send_session(
                    "Runtime.callFunctionOn",
                    {
                        "objectId": iframe_obj_id,
                        "functionDeclaration": (
                            "function(sel) {"
                            "  var doc = this.contentDocument;"
                            "  if (!doc) return null;"
                            "  var el = doc.querySelector(sel);"
                            "  if (!el) return null;"
                            "  el.scrollIntoView({block: 'center'});"
                            "  var rect = el.getBoundingClientRect();"
                            "  return {x: rect.left + rect.width / 2,"
                            "          y: rect.top + rect.height / 2};"
                            "}"
                        ),
                        "arguments": [{"value": selector}],
                        "returnByValue": True,
                    },
                )
                el_box = call_result.get("result", {}).get("value")
                if el_box:
                    return {
                        "x": iframe_box["x"] + el_box["x"],
                        "y": iframe_box["y"] + el_box["y"],
                    }
            except CDPError:
                continue

        return None

    def input_text(self, selector: str, text: str) -> None:
        """向指定选择器的元素输入文本。"""
        self.evaluate(
            f"""
            (() => {{
                const el = document.querySelector({json.dumps(selector)});
                if (!el) return;
                el.focus();
                el.value = {json.dumps(text)};
                el.dispatchEvent(new Event('input', {{bubbles: true}}));
                el.dispatchEvent(new Event('change', {{bubbles: true}}));
            }})()
            """
        )

    def input_content_editable(self, selector: str, text: str) -> None:
        """向 contentEditable 元素输入文本（拟人化逐字输入，模拟真实打字行为）。

        拟人化策略：
        - 每个字符随机间隔 50-200ms，偶尔有短暂停顿模拟思考
        - 每隔 15-35 个字符随机触发一次"输错-删除"行为
        - 换行符前后有额外停顿，模拟段落切换思考
        """
        # 1. focus 元素
        self.evaluate(
            f"""
            (() => {{
                const el = document.querySelector({json.dumps(selector)});
                if (el) el.focus();
            }})()
            """
        )
        time.sleep(random.uniform(0.1, 0.3))

        # 2. 全选清空（Ctrl+A + Backspace）
        self._send_session(
            "Input.dispatchKeyEvent",
            {"type": "keyDown", "key": "a", "code": "KeyA", "modifiers": 2},
        )
        self._send_session(
            "Input.dispatchKeyEvent",
            {"type": "keyUp", "key": "a", "code": "KeyA", "modifiers": 2},
        )
        self._send_session(
            "Input.dispatchKeyEvent",
            {
                "type": "keyDown",
                "key": "Backspace",
                "code": "Backspace",
                "windowsVirtualKeyCode": 8,
            },
        )
        self._send_session(
            "Input.dispatchKeyEvent",
            {
                "type": "keyUp",
                "key": "Backspace",
                "code": "Backspace",
                "windowsVirtualKeyCode": 8,
            },
        )
        time.sleep(random.uniform(0.15, 0.4))

        # 3. 拟人化逐字输入
        # 下一次触发"输错-删除"的字符计数阈值
        next_typo_threshold = random.randint(15, 35)
        chars_since_last_typo = 0

        # 常见的相邻键盘错误字符（用于模拟手误）
        typo_neighbors = "qwertyuiopasdfghjklzxcvbnm"

        for char in text:
            if char == "\n":
                # 换行前停顿更长，模拟段落切换
                time.sleep(random.uniform(0.3, 0.8))
                self.press_key("Enter")
                # 换行后也停顿一下，模拟开始新段落前的思考
                time.sleep(random.uniform(0.2, 0.6))
                chars_since_last_typo = 0
                continue

            # 判断是否触发"输错-删除"行为
            chars_since_last_typo += 1
            should_make_typo = (
                chars_since_last_typo >= next_typo_threshold
                and random.random() < 0.4  # 40% 概率触发
                and char not in ("\n", " ")  # 空格和换行不触发
            )

            if should_make_typo:
                # 输入 1-2 个错误字符
                typo_count = random.randint(1, 2)
                for _ in range(typo_count):
                    wrong_char = random.choice(typo_neighbors)
                    self._send_session(
                        "Input.dispatchKeyEvent",
                        {"type": "keyDown", "text": wrong_char},
                    )
                    self._send_session(
                        "Input.dispatchKeyEvent",
                        {"type": "keyUp", "text": wrong_char},
                    )
                    time.sleep(random.uniform(0.05, 0.15))

                # 停顿一下，模拟"发现输错了"
                time.sleep(random.uniform(0.2, 0.5))

                # 删除错误字符
                for _ in range(typo_count):
                    self._send_session(
                        "Input.dispatchKeyEvent",
                        {
                            "type": "keyDown",
                            "key": "Backspace",
                            "code": "Backspace",
                            "windowsVirtualKeyCode": 8,
                        },
                    )
                    self._send_session(
                        "Input.dispatchKeyEvent",
                        {
                            "type": "keyUp",
                            "key": "Backspace",
                            "code": "Backspace",
                            "windowsVirtualKeyCode": 8,
                        },
                    )
                    time.sleep(random.uniform(0.05, 0.12))

                # 重置计数器和下一次阈值
                chars_since_last_typo = 0
                next_typo_threshold = random.randint(15, 35)

                # 删完后短暂停顿再继续
                time.sleep(random.uniform(0.1, 0.3))

            # 输入正确字符
            self._send_session(
                "Input.dispatchKeyEvent",
                {"type": "keyDown", "text": char},
            )
            self._send_session(
                "Input.dispatchKeyEvent",
                {"type": "keyUp", "text": char},
            )

            # 字符间随机间隔：基础 50-150ms，偶尔有短暂停顿（模拟思考/看屏幕）
            base_delay = random.uniform(0.05, 0.15)
            if random.random() < 0.05:
                # 5% 概率触发较长停顿（0.5-1.5s），模拟思考或分心
                base_delay += random.uniform(0.5, 1.5)
            elif random.random() < 0.1:
                # 10% 概率触发中等停顿（0.2-0.5s）
                base_delay += random.uniform(0.2, 0.5)
            time.sleep(base_delay)

    def get_element_text(self, selector: str) -> str | None:
        """获取元素文本内容（支持 iframe 穿透）。"""
        return self.evaluate_in_iframe(
            f"""
            (() => {{
                const el = document.querySelector({json.dumps(selector)});
                return el ? el.textContent : null;
            }})()
            """
        )

    def get_element_attribute(self, selector: str, attr: str) -> str | None:
        """获取元素属性值。"""
        return self.evaluate(
            f"""
            (() => {{
                const el = document.querySelector({json.dumps(selector)});
                return el ? el.getAttribute({json.dumps(attr)}) : null;
            }})()
            """
        )

    def get_elements_count(self, selector: str) -> int:
        """获取匹配元素数量。"""
        result = self.evaluate(f"document.querySelectorAll({json.dumps(selector)}).length")
        return result if isinstance(result, int) else 0

    def scroll_by(self, x: int, y: int) -> None:
        """滚动页面。"""
        self.evaluate(f"window.scrollBy({x}, {y})")

    def scroll_to(self, x: int, y: int) -> None:
        """滚动到指定位置。"""
        self.evaluate(f"window.scrollTo({x}, {y})")

    def scroll_to_bottom(self) -> None:
        """滚动到页面底部。"""
        self.evaluate("window.scrollTo(0, document.body.scrollHeight)")

    def scroll_element_into_view(self, selector: str) -> None:
        """将元素滚动到可视区域。"""
        self.evaluate(
            f"""
            (() => {{
                const el = document.querySelector({json.dumps(selector)});
                if (el) el.scrollIntoView({{behavior: 'smooth', block: 'center'}});
            }})()
            """
        )

    def scroll_nth_element_into_view(self, selector: str, index: int) -> None:
        """将第 N 个匹配元素滚动到可视区域。"""
        self.evaluate(
            f"""
            (() => {{
                const els = document.querySelectorAll({json.dumps(selector)});
                if (els[{index}]) els[{index}].scrollIntoView(
                    {{behavior: 'smooth', block: 'center'}}
                );
            }})()
            """
        )

    def get_scroll_top(self) -> int:
        """获取当前滚动位置。"""
        result = self.evaluate(
            "window.pageYOffset || document.documentElement.scrollTop"
            " || document.body.scrollTop || 0"
        )
        return int(result) if result else 0

    def get_viewport_height(self) -> int:
        """获取视口高度。"""
        result = self.evaluate("window.innerHeight")
        return int(result) if result else 768

    def _find_element_in_iframes(self, selector: str) -> str | None:
        """在所有 iframe 中查找元素，返回元素的 objectId。

        通过 JS 获取 iframe 对象，再用 Runtime.callFunctionOn 在 iframe 上
        执行 this.contentDocument.querySelector(sel)。
        这种方式不受 isolated world 限制，能正确访问 iframe 内的 DOM。

        Returns:
            元素的 objectId，找不到返回 None。
        """
        # 获取 iframe 数量
        iframe_count = self.evaluate("document.querySelectorAll('iframe').length")
        if not iframe_count:
            return None

        for i in range(iframe_count):
            try:
                # 获取第 i 个 iframe 的 JS objectId
                iframe_result = self._send_session(
                    "Runtime.evaluate",
                    {
                        "expression": f"document.querySelectorAll('iframe')[{i}]",
                        "returnByValue": False,
                    },
                )
                iframe_obj_id = iframe_result.get("result", {}).get("objectId")
                if not iframe_obj_id:
                    continue

                # 在 iframe 对象上执行 JS，查找目标元素
                call_result = self._send_session(
                    "Runtime.callFunctionOn",
                    {
                        "objectId": iframe_obj_id,
                        "functionDeclaration": (
                            "function(sel) {"
                            "  var doc = this.contentDocument;"
                            "  if (!doc) return null;"
                            "  return doc.querySelector(sel) || null;"
                            "}"
                        ),
                        "arguments": [{"value": selector}],
                        "returnByValue": False,
                    },
                )
                el_obj = call_result.get("result", {})
                if el_obj.get("subtype") == "null" or el_obj.get("type") == "undefined":
                    continue

                el_obj_id = el_obj.get("objectId")
                if el_obj_id:
                    return el_obj_id

            except CDPError:
                continue

        return None

    def set_file_input(self, selector: str, files: list[str]) -> None:
        """设置文件输入框的文件（通过 CDP DOM.setFileInputFiles）。

        先在主文档查找，找不到则穿透 iframe 查找。
        视频号发布页面的内容在 iframe 内，需要穿透 iframe 查找。

        iframe 穿透策略（已验证可行）：
        1. Runtime.evaluate 获取 iframe 的 JS objectId
        2. Runtime.callFunctionOn 在 iframe 对象上执行 this.contentDocument.querySelector
        3. DOM.describeNode 获取 backendNodeId
        4. DOM.setFileInputFiles(backendNodeId) 设置文件
        """
        # 先在主文档查找
        doc = self._send_session("DOM.getDocument", {"depth": 0})
        root_node_id = doc["root"]["nodeId"]
        result = self._send_session(
            "DOM.querySelector",
            {"nodeId": root_node_id, "selector": selector},
        )
        node_id = result.get("nodeId", 0)
        if node_id != 0:
            self._send_session(
                "DOM.setFileInputFiles",
                {"nodeId": node_id, "files": files},
            )
            return

        # 主文档找不到，穿透 iframe 查找
        el_obj_id = self._find_element_in_iframes(selector)
        if not el_obj_id:
            raise ElementNotFoundError(selector)

        # 获取 backendNodeId
        described = self._send_session(
            "DOM.describeNode",
            {"objectId": el_obj_id},
        )
        backend_node_id = described.get("node", {}).get("backendNodeId", 0)
        if backend_node_id == 0:
            raise ElementNotFoundError(selector)

        self._send_session(
            "DOM.setFileInputFiles",
            {"backendNodeId": backend_node_id, "files": files},
        )

    def dispatch_wheel_event(self, delta_y: float) -> None:
        """触发滚轮事件以激活懒加载。"""
        self.evaluate(
            f"""
            (() => {{
                let target = document.documentElement;
                const event = new WheelEvent('wheel', {{
                    deltaY: {delta_y},
                    deltaMode: 0,
                    bubbles: true,
                    cancelable: true,
                    view: window,
                }});
                target.dispatchEvent(event);
            }})()
            """
        )

    def mouse_move(self, x: float, y: float) -> None:
        """移动鼠标。"""
        self._send_session(
            "Input.dispatchMouseEvent",
            {"type": "mouseMoved", "x": x, "y": y},
        )

    def mouse_click(self, x: float, y: float, button: str = "left") -> None:
        """在指定坐标点击。"""
        self._send_session(
            "Input.dispatchMouseEvent",
            {"type": "mousePressed", "x": x, "y": y, "button": button, "clickCount": 1},
        )
        self._send_session(
            "Input.dispatchMouseEvent",
            {"type": "mouseReleased", "x": x, "y": y, "button": button, "clickCount": 1},
        )

    def type_text(self, text: str, delay_ms: int = 50) -> None:
        """逐字符输入文本。"""
        for char in text:
            self._send_session(
                "Input.dispatchKeyEvent",
                {"type": "keyDown", "text": char},
            )
            self._send_session(
                "Input.dispatchKeyEvent",
                {"type": "keyUp", "text": char},
            )
            if delay_ms > 0:
                time.sleep(delay_ms / 1000.0)

    def press_key(self, key: str) -> None:
        """按下并释放指定键。"""
        key_map = {
            "Enter": {"key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13},
            "ArrowDown": {
                "key": "ArrowDown",
                "code": "ArrowDown",
                "windowsVirtualKeyCode": 40,
            },
            "Tab": {"key": "Tab", "code": "Tab", "windowsVirtualKeyCode": 9},
        }
        info = key_map.get(key, {"key": key, "code": key})
        self._send_session(
            "Input.dispatchKeyEvent",
            {"type": "keyDown", **info},
        )
        self._send_session(
            "Input.dispatchKeyEvent",
            {"type": "keyUp", **info},
        )

    def inject_stealth(self) -> None:
        """注入反检测脚本。"""
        self._send_session(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": STEALTH_JS},
        )

    def remove_element(self, selector: str) -> None:
        """移除 DOM 元素。"""
        self.evaluate(
            f"""
            (() => {{
                const el = document.querySelector({json.dumps(selector)});
                if (el) el.remove();
            }})()
            """
        )

    def hover_element(self, selector: str) -> None:
        """悬停到元素中心。"""
        box = self.evaluate(
            f"""
            (() => {{
                const el = document.querySelector({json.dumps(selector)});
                if (!el) return null;
                const rect = el.getBoundingClientRect();
                return {{x: rect.left + rect.width / 2, y: rect.top + rect.height / 2}};
            }})()
            """
        )
        if box:
            self.mouse_move(box["x"], box["y"])

    def select_all_text(self, selector: str) -> None:
        """选中输入框内所有文本。"""
        self.evaluate(
            f"""
            (() => {{
                const el = document.querySelector({json.dumps(selector)});
                if (!el) return;
                el.focus();
                el.select ? el.select() : document.execCommand('selectAll');
            }})()
            """
        )


class Browser:
    """Chrome 浏览器 CDP 控制器。"""

    def __init__(self, host: str = "127.0.0.1", port: int = 9222) -> None:
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self._cdp: CDPClient | None = None

    def connect(self) -> None:
        """连接到 Chrome DevTools。"""
        resp = requests.get(f"{self.base_url}/json/version", timeout=5)
        resp.raise_for_status()
        info = resp.json()
        ws_url = info["webSocketDebuggerUrl"]
        logger.info("连接到 Chrome: %s", ws_url)
        self._cdp = CDPClient(ws_url)

    def new_page(self, url: str = "about:blank") -> Page:
        """创建新页面。"""
        if not self._cdp:
            self.connect()
        assert self._cdp is not None

        # 创建 target
        result = self._cdp.send("Target.createTarget", {"url": url})
        target_id = result["targetId"]

        # 附加到 target
        result = self._cdp.send(
            "Target.attachToTarget",
            {"targetId": target_id, "flatten": True},
        )
        session_id = result["sessionId"]

        page = Page(self._cdp, target_id, session_id)

        # 注入反检测（必须在 enable domains 之前）
        page.inject_stealth()

        # UA 覆盖
        page._send_session(
            "Emulation.setUserAgentOverride",
            {"userAgent": REALISTIC_UA},
        )

        # 随机 viewport（模拟真实屏幕尺寸）
        page._send_session(
            "Emulation.setDeviceMetricsOverride",
            {
                "width": random.randint(1366, 1920),
                "height": random.randint(768, 1080),
                "deviceScaleFactor": 1,
                "mobile": False,
            },
        )

        # 拒绝权限弹窗（位置、通知等）
        import contextlib

        for perm in ("geolocation", "notifications", "midi", "camera", "microphone"):
            with contextlib.suppress(CDPError):
                self._cdp.send(
                    "Browser.setPermission",
                    {"permission": {"name": perm}, "setting": "denied"},
                )

        # 启用必要的 domain
        page._send_session("Page.enable")
        page._send_session("DOM.enable")
        page._send_session("Runtime.enable")

        return page

    def get_existing_page(self) -> Page | None:
        """获取已有页面（优先小红书页面，其次非空白/Chrome内部页面）。"""
        if not self._cdp:
            self.connect()
        assert self._cdp is not None

        resp = requests.get(f"{self.base_url}/json", timeout=5)
        targets = resp.json()

        xhs_page = None
        other_page = None

        for target in targets:
            if target.get("type") != "page":
                continue
            url = target.get("url", "")
            if url == "about:blank":
                continue

            target_id = target["id"]
            result = self._cdp.send(
                "Target.attachToTarget",
                {"targetId": target_id, "flatten": True},
            )
            session_id = result["sessionId"]
            page = Page(self._cdp, target_id, session_id)
            page._send_session("Page.enable")
            page._send_session("DOM.enable")
            page._send_session("Runtime.enable")
            page.inject_stealth()

            if "channels.weixin.qq.com" in url:
                return page
            elif not url.startswith("chrome://") and other_page is None:
                other_page = page

        return other_page

    def close_page(self, page: Page) -> None:
        """关闭页面。"""
        import contextlib

        if self._cdp:
            with contextlib.suppress(CDPError):
                self._cdp.send("Target.closeTarget", {"targetId": page.target_id})

    def close(self) -> None:
        """关闭连接。"""
        if self._cdp:
            self._cdp.close()
            self._cdp = None

    def _start_listener(self) -> None:
        """启动消息监听线程。"""
        if self._listener_running:
            return

        self._listener_running = True

        import threading

        def listener_loop():
            while self._listener_running:
                try:
                    raw = self._ws.recv(timeout=0.1)
                    if raw:
                        data = json.loads(raw)
                        method = data.get("method")
                        params = data.get("params")

                        # 响应消息 (有 id)
                        if "id" in data:
                            msg_id = data["id"]
                            if msg_id in self._callbacks:
                                callback = self._callbacks[msg_id]
                                if callback:
                                    try:
                                        if "error" in data:
                                            callback.set_exception(
                                                CDPError(f"CDP 错误: {data['error']}")
                                            )
                                        else:
                                            callback.set_result(data.get("result", {}))
                                    finally:
                                        del self._callbacks[msg_id]

                        # 事件消息 (没有 id)
                        if method and params:
                            self._event_queue.append({"method": method, "params": params})

                except TimeoutError:
                    continue
                except Exception as listener_error:
                    logger.warning("监听线程异常: %s", listener_error)

        self._listener_thread = threading.Thread(target=listener_loop, daemon=True)
        self._listener_thread.start()

    def _stop_listener(self) -> None:
        """停止消息监听线程。"""
        self._listener_running = False

    def add_event_listener(self, method: str, callback: callable) -> None:
        """添加事件监听器。"""
        if method not in self._event_listeners:
            self._event_listeners[method] = []
        self._event_listeners[method].append(callback)

    def remove_event_listener(self, method: str, callback: callable) -> None:
        """移除事件监听器。"""
        import contextlib

        if method in self._event_listeners:
            with contextlib.suppress(ValueError):
                self._event_listeners[method].remove(callback)


class NetworkCapture:
    """网络请求捕获器，用于捕获指定 API 的请求和响应。

    通过轮询 WebSocket 消息来捕获 CDP Network 域的事件，
    避免依赖异步事件监听器，与同步 WebSocket 模型兼容。

    使用方式：
        with NetworkCapture(page, "web_api/sns/v2/note") as capture:
            page.click_element(PUBLISH_BUTTON)
            request, response = capture.wait_for_capture()
    """

    PUBLISH_API_URL = "web_api/sns/v2/note"

    def __init__(
        self,
        page: Page,
        url_pattern: str = PUBLISH_API_URL,
        timeout: float = 30.0,
    ) -> None:
        self._page = page
        self._url_pattern = url_pattern
        self._timeout = timeout
        self._request_data: dict[str, Any] | None = None
        self._response_data: dict[str, Any] | None = None
        self._captured = False
        self._request_id: str | None = None

    def __enter__(self) -> NetworkCapture:
        """启动网络监听。"""
        self._page._send_session("Network.enable", {})
        self._captured = False
        self._request_data = None
        self._response_data = None
        self._request_id = None
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """停止网络监听。"""
        import contextlib

        with contextlib.suppress(CDPError):
            self._page._send_session("Network.disable", {})

    def wait_for_capture(self) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        """等待捕获到匹配的请求和响应。

        先消费 Page._pending_events 中被 _wait_session 缓存的事件，
        再轮询 WebSocket 获取新消息。

        Returns:
            (request_data, response_data) - 捕获到的请求和响应数据
            如果超时则返回 (None, None)
        """
        deadline = time.monotonic() + self._timeout

        while time.monotonic() < deadline:
            # 优先消费 _wait_session 缓存的事件
            while self._page._pending_events:
                cached_event = self._page._pending_events.pop(0)
                self._dispatch_event(cached_event)
                if self._captured and self._request_data and self._response_data:
                    return self._request_data, self._response_data

            # 从 WebSocket 轮询新消息
            try:
                remaining = max(0.1, deadline - time.monotonic())
                raw = self._page._ws.recv(timeout=min(remaining, 0.5))
            except TimeoutError:
                continue
            except Exception as recv_error:
                logger.warning("接收 WebSocket 消息异常: %s", recv_error)
                continue

            if not raw:
                continue

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue

            # 非事件消息（如其他命令的响应）跳过
            if "method" not in data:
                continue

            self._dispatch_event(data)

            if self._captured and self._request_data and self._response_data:
                return self._request_data, self._response_data

        logger.warning("等待捕获超时: %s", self._url_pattern)
        return None, None

    def _dispatch_event(self, data: dict[str, Any]) -> None:
        """分发单条 CDP 事件消息。"""
        method = data.get("method")
        params = data.get("params", {})
        session_id = data.get("sessionId")

        # 只处理当前 session 的事件
        if session_id and session_id != self._page.session_id:
            return

        if method == "Network.requestWillBeSent":
            self._handle_request_will_be_sent(params)
        elif method == "Network.responseReceived":
            self._handle_response_received(params)
        elif method == "Network.loadingFinished" and self._request_id:
            loading_request_id = params.get("requestId")
            if (
                loading_request_id == self._request_id
                and self._request_data
                and not self._response_data
            ):
                self._fetch_response_body(loading_request_id)

    def _handle_request_will_be_sent(self, params: dict[str, Any]) -> None:
        """处理 Network.requestWillBeSent 事件。"""
        request = params.get("request", {})
        url = request.get("url", "")
        request_method = request.get("method", "")

        if self._url_pattern in url and request_method == "POST" and not self._captured:
            self._request_id = params.get("requestId")
            self._request_data = {
                "url": url,
                "method": request_method,
                "headers": request.get("headers", {}),
                "postData": request.get("postData"),
            }
            logger.info("捕获到发布请求: %s (requestId=%s)", url, self._request_id)

    def _handle_response_received(self, params: dict[str, Any]) -> None:
        """处理 Network.responseReceived 事件。"""
        request_id = params.get("requestId")
        if request_id != self._request_id or not self._request_data:
            return

        response = params.get("response", {})
        url = response.get("url", "")
        if self._url_pattern not in url:
            return

        logger.info("捕获到发布响应: %s (status=%s)", url, response.get("status"))
        # 尝试立即获取响应体（可能还没准备好）
        self._fetch_response_body(request_id)

    def _fetch_response_body(self, request_id: str) -> None:
        """获取响应体内容。"""
        try:
            body_result = self._page._send_session(
                "Network.getResponseBody",
                {"requestId": request_id},
            )
            self._response_data = {
                "body": body_result.get("body"),
                "base64Encoded": body_result.get("base64Encoded", False),
            }
            self._captured = True
            logger.info("成功获取发布响应体")
        except CDPError as fetch_error:
            logger.debug("获取响应体暂未就绪: %s", fetch_error)
