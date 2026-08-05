"""
本地 OAuth 授权回调服务器

端点：
  GET  /callback      — 接收授权回调
  POST /api/exchange   — 用 authorization_code 交换 Token
  POST /api/save-ak    — 保存 AK（AK 模式）
  POST /api/shutdown   — 通知关闭
"""
from __future__ import annotations

import json
import logging
import socket
import ssl
import sys
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from _const import (
    CALLBACK_HOST,
    CALLBACK_BIND_ADDRESS,
    CALLBACK_PORT_START,
    CALLBACK_PORT_RETRIES,
    TOKEN_ENDPOINT,
    CALLBACK_TEMPLATE,
    HTTP_TIMEOUT,
    ENV_FILE,
    ENV_ACCESS_TOKEN,
    ENV_REFRESH_TOKEN,
    ENV_TOKEN_SCOPE,
    ENV_TOKEN_EXPIRES_AT,
    ENV_REFRESH_TOKEN_EXPIRES_AT,
    ENV_CLIENT_ID,
    ENV_REDIRECT_URI,
    AUTH_MODE_OAUTH,
    AUTH_MODE_AK,
)
from _auth import build_auth_headers
from secure_store import store_token as _store_token, save_metadata as _save_metadata

logger = logging.getLogger(__name__)

ERROR_HTML = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>授权失败</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
display:flex;justify-content:center;align-items:center;min-height:100vh;background:#fef2f2}
.card{text-align:center;padding:3rem 2.5rem;border-radius:1rem;background:#fff;
box-shadow:0 4px 24px rgba(0,0,0,.08);max-width:480px;width:90%}
.icon{font-size:3rem;margin-bottom:1rem}
h1{color:#dc2626;font-size:1.5rem;margin-bottom:0.75rem}
p{color:#666;line-height:1.6;margin-bottom:0.5rem}
.error-code{font-family:monospace;background:#fee2e2;color:#991b1b;
padding:0.25rem 0.5rem;border-radius:0.25rem;font-size:0.875rem}
.footer{margin-top:1.5rem;font-size:0.75rem;color:#999}
</style></head>
<body><div class="card">
<div class="icon">&#10008;</div>
<h1>授权失败</h1>
<p>{error_message}</p>
<p class="error-code">{error_code}</p>
<div class="footer">此页面仅运行在您的本地设备上 (localhost)</div>
</div></body></html>"""


class _FastBindMixin:
    """跳过 HTTPServer.server_bind() 中的 socket.getfqdn() 调用。
    默认实现对绑定地址做反向 DNS 查询，在某些网络环境下会超时 5 秒。"""
    def server_bind(self):
        import socketserver
        socketserver.TCPServer.server_bind(self)
        host, port = self.server_address[:2]
        self.server_name = socket.gethostname()
        self.server_port = port


class _ThreadingHTTPServer(_FastBindMixin, ThreadingMixIn, HTTPServer):
    """支持并发请求的 HTTP 服务器（IPv4）"""
    allow_reuse_address = True
    daemon_threads = True


class _ThreadingHTTPServerIPv6(_FastBindMixin, ThreadingMixIn, HTTPServer):
    """支持并发请求的 HTTP 服务器（IPv6）"""
    address_family = socket.AF_INET6
    allow_reuse_address = True
    daemon_threads = True


class CallbackServer:
    def __init__(self, client_id: str, redirect_uri: str, code_verifier: str,
                 state: str, env_file: Path = ENV_FILE,
                 mode: str = AUTH_MODE_OAUTH) -> None:
        self.client_id = client_id
        self.redirect_uri = redirect_uri
        self._code_verifier: str | None = code_verifier
        self._state = state
        self._env_file = env_file
        self._mode = mode
        self._port: int = CALLBACK_PORT_START
        self._server: HTTPServer | None = None
        self._server_ipv6: HTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._thread_ipv6: threading.Thread | None = None
        self._done_event = threading.Event()
        self._success = False
        self._result: dict = {}
        self._exchange_result: dict | None = None

    @property
    def port(self) -> int:
        return self._port

    @property
    def success(self) -> bool:
        return self._success

    @property
    def result(self) -> dict:
        return self._result

    def start(self) -> None:
        handler = self._create_handler()
        port = self._bind_port(handler)
        self._port = port

        if sys.platform == "win32":
            self._start_windows(handler, port)
        else:
            self._start_unix(handler, port)

        logger.info("回调服务器启动在 http://%s:%d", CALLBACK_HOST, self._port)

    def _bind_port(self, handler) -> int:
        """尝试从 CALLBACK_PORT_START 开始依次绑定，返回成功绑定的端口号。"""
        for attempt in range(CALLBACK_PORT_RETRIES):
            port = CALLBACK_PORT_START + attempt
            try:
                self._server = _ThreadingHTTPServer((CALLBACK_BIND_ADDRESS, port), handler)
                return port
            except OSError:
                if attempt == CALLBACK_PORT_RETRIES - 1:
                    raise OSError(f"无法绑定端口 {CALLBACK_PORT_START}-{port}")
                logger.warning("端口 %d 被占用，尝试 %d", port, port + 1)
        raise OSError("端口绑定失败")  # unreachable，满足类型检查

    def _start_windows(self, handler, port: int) -> None:
        """Windows：IPv4（127.0.0.1）+ IPv6（::1）分开监听。"""
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            daemon=False, name="oauth-callback-server-ipv4",
        )
        self._thread.start()
        logger.debug("Windows: IPv4 回调服务器启动在 http://127.0.0.1:%d", port)

        logger.debug("Windows: 尝试同时启动 IPv6 回调服务器（::1:%d）", port)
        try:
            self._server_ipv6 = _ThreadingHTTPServerIPv6(("::1", port), handler)
            self._thread_ipv6 = threading.Thread(
                target=self._server_ipv6.serve_forever,
                daemon=False, name="oauth-callback-server-ipv6",
            )
            self._thread_ipv6.start()
            logger.debug("Windows: IPv6 回调服务器启动在 http://[::1]:%d", port)
        except OSError as e:
            logger.warning("Windows: IPv6 回调服务器启动失败（localhost 若解析为 ::1 则回调不可达）: %s", e)

    def _start_unix(self, handler, port: int) -> None:
        """Linux/macOS：单 AF_INET6 dual-stack socket，IPV6_V6ONLY=0 同时接受 IPv4/IPv6。
        必须在 server_bind() 之前设置 IPV6_V6ONLY，故使用 bind_and_activate=False 延迟绑定。
        """
        self._server.server_close()
        self._server = _ThreadingHTTPServerIPv6(("::", port), handler, bind_and_activate=False)
        self._server.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        self._server.server_bind()
        self._server.server_activate()
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            daemon=False, name="oauth-callback-server",
        )
        self._thread.start()
        logger.debug("Unix: dual-stack 回调服务器启动在 [::]:%d（同时接受 IPv4/IPv6）", port)

    def wait(self, timeout: int = 300) -> bool:
        return self._done_event.wait(timeout=timeout)

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
            self._server = None
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        if self._server_ipv6:
            self._server_ipv6.shutdown()
            self._server_ipv6 = None
        if self._thread_ipv6:
            self._thread_ipv6.join(timeout=5)
            self._thread_ipv6 = None

    def _save_ak(self, ak: str) -> dict:
        from capabilities.configure.service import validate_ak, configure_ak
        is_valid, error_msg = validate_ak(ak)
        if not is_valid:
            return {"success": False, "error": "AK_INVALID", "error_description": error_msg}
        success, storage_location = configure_ak(ak)
        if success:
            return {"success": True, "ak": ak}
        return {"success": False, "error": "AK_SAVE_FAILED",
                "error_description": "AK 保存失败，请检查文件权限"}

    def _exchange_token(self, code: str) -> dict:
        if self._exchange_result is not None:
            return self._exchange_result

        if not self._code_verifier:
            result = {"success": False, "error": "code_verifier 已被使用，请重新授权"}
            self._exchange_result = result
            return result

        request_body = {
            "clientId": self.client_id,
            "redirectUri": self.redirect_uri,
            "code": code,
            "codeVerifier": self._code_verifier,
        }
        body_str = json.dumps(request_body)
        self._code_verifier = None

        from urllib.parse import urlparse as _urlparse
        endpoint_path = _urlparse(TOKEN_ENDPOINT).path

        auth_headers = build_auth_headers("POST", endpoint_path, body_str)
        if auth_headers is None:
            logger.warning("AK 未配置，将以无签名方式发送 Token 交换请求")
            auth_headers = {"Content-Type": "application/json"}

        req = Request(TOKEN_ENDPOINT, data=body_str.encode("utf-8"),
                      headers=auth_headers, method="POST")

        try:
            ctx = ssl.create_default_context()
            with urlopen(req, timeout=HTTP_TIMEOUT, context=ctx) as resp:
                raw_body = json.loads(resp.read().decode("utf-8"))
        except HTTPError as e:
            error_body = {}
            try:
                error_body = json.loads(e.read().decode("utf-8"))
            except Exception:
                pass
            result = {
                "success": False,
                "error": error_body.get("errorCode", f"HTTP_{e.code}"),
                "error_description": error_body.get("errorDescription",
                                                     f"Token 交换失败: HTTP {e.code}"),
            }
            self._exchange_result = result
            return result
        except URLError as e:
            result = {"success": False, "error": "NETWORK_ERROR",
                      "error_description": f"网络错误: {e.reason}"}
            self._exchange_result = result
            return result

        if not raw_body.get("success"):
            error_response = raw_body.get("data", {}).get("response", {})
            error_code = (error_response.get("error") or raw_body.get("code")
                          or raw_body.get("msgCode") or "TOKEN_EXCHANGE_FAILED")
            error_msg = (error_response.get("errorDescription") or raw_body.get("message")
                         or raw_body.get("msgInfo") or "Token 交换失败")
            result = {"success": False, "error": error_code, "error_description": error_msg}
            self._exchange_result = result
            return result

        token_response = raw_body.get("data", {}).get("response", {})
        access_token = token_response.get("accessToken", "")
        refresh_token = token_response.get("refreshToken", "")
        scope = token_response.get("scope", "")
        expires_in = token_response.get("expiresIn", 0)
        expires_at = int(time.time()) + expires_in
        refresh_expire_in = token_response.get("refreshExpireIn", 0)
        refresh_expires_at = int(time.time()) + refresh_expire_in if refresh_expire_in else 0

        _store_token(ENV_ACCESS_TOKEN, access_token)
        _store_token(ENV_REFRESH_TOKEN, refresh_token)
        _save_metadata({
            ENV_TOKEN_SCOPE: scope,
            ENV_TOKEN_EXPIRES_AT: str(expires_at),
            ENV_REFRESH_TOKEN_EXPIRES_AT: str(refresh_expires_at) if refresh_expires_at else "",
            ENV_CLIENT_ID: self.client_id,
            ENV_REDIRECT_URI: self.redirect_uri,
        }, self._env_file)

        result = {"success": True, "scope": scope, "expires_in": expires_in}
        self._exchange_result = result
        return result

    def _create_handler(self) -> type:
        server_ref = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                parsed = urlparse(self.path)
                if parsed.path == "/callback":
                    self._handle_callback(parsed)
                elif parsed.path == "/healthCheck":
                    self._handle_health_check()
                else:
                    self.send_error(404)

            def _handle_health_check(self):
                logger.info("healthCheck from %s:%s", self.client_address[0], self.client_address[1])
                body = b"ok"
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self):
                parsed = urlparse(self.path)
                if parsed.path == "/api/exchange":
                    self._handle_exchange()
                elif parsed.path == "/api/save-ak":
                    self._handle_save_ak()
                elif parsed.path == "/api/shutdown":
                    self._handle_shutdown()
                else:
                    self.send_error(404)

            def _handle_callback(self, parsed):
                params = parse_qs(parsed.query)

                if "error" in params:
                    error = params["error"][0]
                    desc = params.get("error_description", ["用户拒绝了授权"])[0]
                    server_ref._code_verifier = None
                    html = ERROR_HTML.replace("{error_message}", desc).replace("{error_code}", error)
                    self._send_html(200, html)
                    server_ref._result = {"success": False, "error": error, "error_description": desc}
                    server_ref._done_event.set()
                    return

                received_state = params.get("state", [None])[0]
                if received_state != server_ref._state:
                    server_ref._code_verifier = None
                    html = ERROR_HTML.replace(
                        "{error_message}", "安全校验失败 (state 不匹配)，可能存在 CSRF 攻击。"
                    ).replace("{error_code}", "STATE_MISMATCH")
                    self._send_html(400, html)
                    return

                code = params.get("code", [None])[0]
                callback_mode = params.get("mode", [AUTH_MODE_OAUTH])[0]

                if not code:
                    server_ref._code_verifier = None
                    html = ERROR_HTML.replace(
                        "{error_message}", "回调中缺少 authorization_code"
                    ).replace("{error_code}", "MISSING_CODE")
                    self._send_html(400, html)
                    return

                if callback_mode == AUTH_MODE_AK or server_ref._mode == AUTH_MODE_AK:
                    import json as _json
                    port = server_ref._port
                    code_json = _json.dumps(code)
                    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>1688 AK 设置</title>
<style>*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,sans-serif;display:flex;justify-content:center;
align-items:center;min-height:100vh;background:#f8f9fa}}
.card{{background:#fff;border-radius:1rem;padding:2.5rem 2rem;
box-shadow:0 4px 24px rgba(0,0,0,.06);max-width:520px;width:92%;text-align:center}}
.spinner{{width:48px;height:48px;border:4px solid #e5e7eb;border-top-color:#FF6A00;
border-radius:50%;animation:spin 0.8s linear infinite;margin:0 auto 1rem}}
@keyframes spin{{to{{transform:rotate(360deg)}}}}
.title{{font-size:1.25rem;font-weight:600;color:#333}}
</style></head><body><div class="card">
<div class="spinner"></div><div class="title">正在保存 AK...</div>
</div>
<script>
(function(){{
const AK={code_json};
fetch("http://127.0.0.1:{port}/api/save-ak",{{method:"POST",
headers:{{"Content-Type":"application/json"}},body:JSON.stringify({{ak:AK}})}})
.then(r=>r.json()).then(d=>{{
document.querySelector(".card").innerHTML=d.success?
'<div style="font-size:3rem;color:#16a34a">&#10004;</div><div class="title" style="color:#16a34a">AK 设置成功！</div><p style="color:#666;margin-top:1rem">您可以关闭此页面。</p>':
'<div style="font-size:3rem;color:#dc2626">&#10008;</div><div class="title" style="color:#dc2626">设置失败</div><p style="color:#666;margin-top:1rem">'+d.error_description+'</p>';
}}).catch(err=>{{document.querySelector(".card").innerHTML='<div>连接失败: '+err.message+'</div>';}});
}})();
</script></body></html>"""
                    self._send_html(200, html)
                    return

                try:
                    template = CALLBACK_TEMPLATE.read_text(encoding="utf-8")
                    html = template.replace("{{AUTH_CODE}}", code)
                    html = html.replace("{{SERVER_PORT}}", str(server_ref._port))
                    self._send_html(200, html)
                except FileNotFoundError:
                    self._send_html(500, ERROR_HTML.replace(
                        "{error_message}", "回调页面模板文件丢失"
                    ).replace("{error_code}", "TEMPLATE_NOT_FOUND"))

            def _handle_exchange(self):
                origin = self.headers.get("Origin", "")
                allowed = f"http://localhost:{server_ref._port}"
                allowed2 = f"http://0.0.0.0:{server_ref._port}"
                if origin and origin not in (allowed, allowed2):
                    self._send_json(403, {"success": False, "error": "CORS_DENIED"})
                    return

                content_length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(content_length)) if content_length > 0 else {}
                code = body.get("code", "")

                if not code:
                    self._send_json(400, {"success": False, "error": "MISSING_CODE"})
                    return

                result = server_ref._exchange_token(code)
                server_ref._result = result
                if result.get("success"):
                    server_ref._success = True

                self._send_json(200, result, cors_origin=origin or allowed)

            def _handle_save_ak(self):
                origin = self.headers.get("Origin", "")
                allowed = f"http://localhost:{server_ref._port}"
                allowed2 = f"http://0.0.0.0:{server_ref._port}"
                if origin and origin not in (allowed, allowed2):
                    self._send_json(403, {"success": False, "error": "CORS_DENIED"})
                    return

                content_length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(content_length)) if content_length > 0 else {}
                ak = body.get("ak", "")

                if not ak:
                    self._send_json(400, {"success": False, "error": "MISSING_AK",
                                          "error_description": "AK 不能为空"})
                    return

                result = server_ref._save_ak(ak)
                server_ref._result = result
                if result.get("success"):
                    server_ref._success = True

                self._send_json(200, result, cors_origin=origin or allowed)
                # AK 保存完成后通知服务器退出，避免等待超时
                if result.get("success"):
                    threading.Thread(target=lambda: server_ref._done_event.set(),
                                     daemon=True).start()

            def _handle_shutdown(self):
                allowed = f"http://localhost:{server_ref._port}"
                self._send_json(200, {"success": True}, cors_origin=allowed)
                threading.Thread(target=lambda: server_ref._done_event.set(),
                                 daemon=True).start()

            def _send_html(self, status: int, html: str):
                encoded = html.encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(encoded)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(encoded)

            def _send_json(self, status: int, data: dict, cors_origin: str = ""):
                encoded = json.dumps(data, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(encoded)))
                self.send_header("Cache-Control", "no-store")
                if cors_origin:
                    self.send_header("Access-Control-Allow-Origin", cors_origin)
                    self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.end_headers()
                self.wfile.write(encoded)

            def do_OPTIONS(self):
                allowed = f"http://localhost:{server_ref._port}"
                self.send_response(204)
                self.send_header("Access-Control-Allow-Origin", allowed)
                self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.end_headers()

            def log_message(self, fmt, *args):
                logger.debug(fmt, *args)

        return Handler
