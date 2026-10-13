#!/usr/bin/env python3
"""Temporary local browser interface for DTS-AI API-key entry.

The interface listens only on a temporary 127.0.0.1 port, opens the system
default browser, accepts one same-origin form submission, and passes the API
key only to an in-process save callback. It never logs request paths or bodies
and never writes credentials itself.
"""

from __future__ import annotations

import html
import os
import secrets
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Callable, Mapping, Optional, Tuple
from urllib.parse import parse_qs


LOOPBACK_HOST = "127.0.0.1"
DEFAULT_TIMEOUT_SECONDS = 300.0
MAX_BODY_BYTES = 16 * 1024
MAX_API_KEY_CHARS = 8192
MAX_FORM_FIELDS = 2
SUPPORTED_LANGUAGES = ("en", "zh-CN")
UI_TEXT: Mapping[str, Mapping[str, str]] = {
    "en": {
        "html_lang": "en",
        "page_title": "DTS-AI API Key Setup",
        "brand": "DTS-AI local setup",
        "local": "Local only · 127.0.0.1",
        "heading": "Configure your DTS-AI API Key",
        "lead": (
            "The key is submitted directly to the temporary local helper "
            "and saved in a current-user-only JSON file."
        ),
        "existing": (
            "An API Key is already configured. Submitting this form replaces "
            "the local credential."
        ),
        "label": "DTS-AI API Key",
        "placeholder": "Paste your API Key",
        "notice": (
            "The key is sent only in this local POST request. It is never "
            "placed in the URL, command arguments, page source, or logs."
        ),
        "save": "Save API Key",
        "cancel": "Cancel",
        "invalid": "Enter a non-empty API Key without whitespace or control characters.",
        "rejected_title": "Request rejected",
        "rejected_message": "This local setup session does not accept the request.",
        "cancelled_title": "Cancelled",
        "cancelled_message": "No API Key was saved. You can close this page.",
        "save_failed_title": "Configuration failed",
        "save_failed_message": "Return to the task so the system can check and retry.",
        "saved_title": "Configuration complete",
        "saved_message": "You can close this page and return to the task.",
    },
    "zh-CN": {
        "html_lang": "zh-CN",
        "page_title": "DTS-AI API Key 配置",
        "brand": "DTS-AI 本地配置",
        "local": "仅限本机 · 127.0.0.1",
        "heading": "配置 DTS-AI API Key",
        "lead": "API Key 将直接提交给短生命周期的本地助手，并保存到仅当前用户可访问的 JSON 文件。",
        "existing": "已存在 API Key 配置。提交此表单将替换本地凭据。",
        "label": "DTS-AI API Key",
        "placeholder": "粘贴 API Key",
        "notice": "API Key 仅通过本地 POST 请求提交，不会进入 URL、命令参数、页面源码或日志。",
        "save": "保存 API Key",
        "cancel": "取消",
        "invalid": "请输入非空且不含空白边界或控制字符的 API Key。",
        "rejected_title": "请求已拒绝",
        "rejected_message": "当前本地配置会话不接受此请求。",
        "cancelled_title": "已取消",
        "cancelled_message": "未保存 API Key。你可以关闭此页面。",
        "save_failed_title": "配置失败",
        "save_failed_message": "请返回任务，让系统检查后重试。",
        "saved_title": "配置完成",
        "saved_message": "你可以关闭此页面并返回任务。",
    },
}
SECURITY_HEADERS: Tuple[Tuple[str, str], ...] = (
    ("Cache-Control", "no-store, max-age=0"),
    ("Pragma", "no-cache"),
    ("Referrer-Policy", "same-origin"),
    ("X-Content-Type-Options", "nosniff"),
    ("X-Frame-Options", "DENY"),
    ("Cross-Origin-Opener-Policy", "same-origin"),
    ("Cross-Origin-Resource-Policy", "same-origin"),
    (
        "Content-Security-Policy",
        "default-src 'none'; style-src 'unsafe-inline'; "
        "form-action 'self'; frame-ancestors 'none'; base-uri 'none'",
    ),
    ("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()"),
)


class BrowserApiKeyUIError(Exception):
    """Browser API-key interface failure with a fixed public error code."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


class _LoopbackHTTPServer(HTTPServer):
    allow_reuse_address = False


class _Session:
    def __init__(
        self,
        commit: Callable[[str], bool],
        path_token: str,
        csrf_token: str,
        language: str,
        existing_configured: bool,
    ):
        self.commit = commit
        self.csrf_token = csrf_token
        self.language = language
        self.existing_configured = existing_configured
        self.form_path = f"/{path_token}/"
        self.submit_path = f"/{path_token}/submit"
        self.cancel_path = f"/{path_token}/cancel"
        self.origin = ""
        self.expected_host = ""
        self.completed = threading.Event()
        self.result = "PENDING"


def _language_text(language: str) -> Mapping[str, str]:
    if language not in SUPPORTED_LANGUAGES:
        raise BrowserApiKeyUIError("INVALID_INPUT")
    return UI_TEXT[language]


def _render_form(
    *,
    csrf_token: str,
    submit_path: str,
    cancel_path: str,
    language: str,
    existing_configured: bool,
    error_message: Optional[str] = None,
) -> str:
    strings = _language_text(language)
    csrf = html.escape(csrf_token, quote=True)
    submit = html.escape(submit_path, quote=True)
    cancel = html.escape(cancel_path, quote=True)
    existing = (
        f'<div class="existing">{html.escape(strings["existing"])}</div>'
        if existing_configured
        else ""
    )
    error = (
        f'<div class="error" role="alert">{html.escape(error_message)}</div>'
        if error_message
        else ""
    )
    return f"""<!doctype html>
<html lang="{html.escape(strings["html_lang"], quote=True)}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{html.escape(strings["page_title"])}</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #17223b;
      --muted: #667085;
      --line: #d9e1ef;
      --cloud: #f4f7fb;
      --paper: #ffffff;
      --blue: #1677ff;
      --blue-deep: #0b57c9;
      --teal: #0f7b8d;
      --danger-bg: #fff6ed;
      --danger: #9a3412;
      font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont,
        "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      display: grid;
      min-height: 100vh;
      margin: 0;
      place-items: center;
      color: var(--ink);
      background:
        linear-gradient(135deg, rgba(22,119,255,.09), transparent 34rem),
        var(--cloud);
    }}
    main {{
      width: min(640px, calc(100% - 28px));
      padding: 34px;
      border: 1px solid var(--line);
      border-radius: 22px;
      background: var(--paper);
      box-shadow: 0 22px 60px rgba(28,48,82,.11);
    }}
    .masthead {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 18px;
      margin-bottom: 30px;
    }}
    .brand {{
      display: flex;
      align-items: center;
      gap: 11px;
      font-size: 13px;
      font-weight: 780;
      letter-spacing: .07em;
      text-transform: uppercase;
    }}
    .mark {{
      width: 28px;
      height: 28px;
      border: 7px solid var(--blue);
      border-right-color: var(--teal);
      border-radius: 8px;
      transform: rotate(45deg);
    }}
    .local {{
      padding: 7px 11px;
      border: 1px solid #b7e0d8;
      border-radius: 999px;
      color: #176657;
      background: #effbf7;
      font-size: 12px;
      font-weight: 700;
    }}
    h1 {{
      margin: 0;
      font-size: clamp(30px, 6vw, 48px);
      line-height: 1.06;
      letter-spacing: -.04em;
    }}
    .lead {{
      margin: 15px 0 26px;
      color: var(--muted);
      line-height: 1.7;
    }}
    .existing, .error {{
      margin-bottom: 18px;
      padding: 13px 15px;
      border-radius: 12px;
      font-size: 14px;
      line-height: 1.55;
    }}
    .existing {{
      border: 1px solid #bfdbfe;
      color: #1e4f91;
      background: #eff6ff;
    }}
    .error {{
      border: 1px solid #fed7aa;
      color: var(--danger);
      background: var(--danger-bg);
    }}
    label span {{
      display: block;
      margin-bottom: 8px;
      font-size: 13px;
      font-weight: 750;
    }}
    input {{
      width: 100%;
      height: 50px;
      padding: 0 14px;
      border: 1px solid #cbd5e1;
      border-radius: 11px;
      outline: none;
      background: #fbfcfe;
      color: var(--ink);
      font: 500 15px/1 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    }}
    input:focus {{
      border-color: var(--blue);
      box-shadow: 0 0 0 4px rgba(22,119,255,.13);
    }}
    .notice {{
      margin: 14px 0 22px;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.65;
    }}
    .actions {{
      display: flex;
      justify-content: flex-end;
      gap: 12px;
    }}
    .cancel-form {{ margin-top: 10px; text-align: right; }}
    button {{
      min-width: 132px;
      height: 44px;
      border: 0;
      border-radius: 10px;
      cursor: pointer;
      font: 750 14px/1 inherit;
    }}
    .primary {{
      color: #fff;
      background: var(--blue);
      box-shadow: 0 10px 22px rgba(22,119,255,.22);
    }}
    .primary:hover {{ background: var(--blue-deep); }}
    .cancel {{
      color: var(--muted);
      background: #eef2f7;
    }}
    button:focus-visible {{
      outline: 3px solid rgba(22,119,255,.28);
      outline-offset: 3px;
    }}
    @media (max-width: 560px) {{
      main {{ padding: 24px 20px; }}
      .masthead {{ align-items: flex-start; flex-direction: column; }}
      .actions {{ display: block; }}
      .cancel-form {{ margin-top: 12px; }}
      button {{ width: 100%; }}
    }}
  </style>
</head>
<body>
  <main>
    <div class="masthead">
      <div class="brand"><span class="mark"></span>{html.escape(strings["brand"])}</div>
      <div class="local">{html.escape(strings["local"])}</div>
    </div>
    <h1>{html.escape(strings["heading"])}</h1>
    <p class="lead">{html.escape(strings["lead"])}</p>
    {existing}
    {error}
    <form method="post" action="{submit}" autocomplete="off">
      <input type="hidden" name="csrf" value="{csrf}">
      <label>
        <span>{html.escape(strings["label"])}</span>
        <input
          type="password"
          name="api_key"
          autocomplete="off"
          autocapitalize="none"
          spellcheck="false"
          maxlength="{MAX_API_KEY_CHARS}"
          placeholder="{html.escape(strings["placeholder"], quote=True)}"
          required
          autofocus
        >
      </label>
      <p class="notice">{html.escape(strings["notice"])}</p>
      <div class="actions">
        <button class="primary" type="submit">{html.escape(strings["save"])}</button>
      </div>
    </form>
    <form class="cancel-form" method="post" action="{cancel}">
      <input type="hidden" name="csrf" value="{csrf}">
      <button class="cancel" type="submit">{html.escape(strings["cancel"])}</button>
    </form>
  </main>
</body>
</html>
"""


def _render_result(title: str, message: str, *, success: bool, language: str) -> str:
    strings = _language_text(language)
    accent = "#1677ff" if success else "#9a3412"
    symbol = "✓" if success else "×"
    return f"""<!doctype html>
<html lang="{html.escape(strings["html_lang"], quote=True)}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    :root {{
      font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont,
        "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
      color: #17223b;
      background: #f4f7fb;
    }}
    body {{ display: grid; min-height: 100vh; margin: 0; place-items: center; }}
    main {{
      width: min(470px, calc(100% - 30px));
      padding: 38px;
      border: 1px solid #d9e1ef;
      border-radius: 20px;
      background: #fff;
      box-shadow: 0 18px 50px rgba(28,48,82,.09);
      text-align: center;
    }}
    .symbol {{
      display: grid;
      width: 54px;
      height: 54px;
      margin: 0 auto 20px;
      place-items: center;
      border-radius: 16px;
      color: #fff;
      background: {accent};
      font-size: 30px;
      font-weight: 800;
    }}
    h1 {{ margin: 0; font-size: 28px; letter-spacing: -.03em; }}
    p {{ margin: 13px 0 0; color: #667085; line-height: 1.7; }}
  </style>
</head>
<body>
  <main>
    <div class="symbol">{symbol}</div>
    <h1>{html.escape(title)}</h1>
    <p>{html.escape(message)}</p>
  </main>
</body>
</html>
"""


def _is_valid_api_key(value: object) -> bool:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > MAX_API_KEY_CHARS
        or value != value.strip()
    ):
        return False
    return not any(ord(character) < 32 or ord(character) == 127 for character in value)


def _handler_type(session: _Session) -> type[BaseHTTPRequestHandler]:
    class ApiKeyHandler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.0"
        server_version = "DTSLocalApiKeyUI"
        sys_version = ""

        def log_message(self, _format: str, *args: object) -> None:
            return

        def setup(self) -> None:
            super().setup()
            self.connection.settimeout(5.0)

        def _send_html(self, status: int, document: str) -> None:
            body = document.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            for name, value in SECURITY_HEADERS:
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(body)
            self.close_connection = True

        def _host_is_valid(self) -> bool:
            values = self.headers.get_all("Host", [])
            return len(values) == 1 and values[0] == session.expected_host

        def _post_is_same_origin(self) -> bool:
            origins = self.headers.get_all("Origin", [])
            if origins:
                if len(origins) != 1 or origins[0] != session.origin:
                    return False
            else:
                referers = self.headers.get_all("Referer", [])
                if (
                    len(referers) != 1
                    or referers[0] != session.origin + session.form_path
                ):
                    return False
            fetch_sites = self.headers.get_all("Sec-Fetch-Site", [])
            return not fetch_sites or (
                len(fetch_sites) == 1 and fetch_sites[0] == "same-origin"
            )

        def _read_form(self, expected_fields: set[str]) -> Mapping[str, str]:
            if self.headers.get_all("Transfer-Encoding", []):
                raise ValueError()
            content_types = self.headers.get_all("Content-Type", [])
            if len(content_types) != 1 or (
                content_types[0].partition(";")[0].strip().lower()
                != "application/x-www-form-urlencoded"
            ):
                raise ValueError()
            content_lengths = self.headers.get_all("Content-Length", [])
            if len(content_lengths) != 1 or not content_lengths[0].isdigit():
                raise ValueError()
            length = int(content_lengths[0])
            if length <= 0 or length > MAX_BODY_BYTES:
                raise ValueError()
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise ValueError()
            parsed = parse_qs(
                raw.decode("utf-8"),
                keep_blank_values=True,
                strict_parsing=True,
                max_num_fields=MAX_FORM_FIELDS,
            )
            if set(parsed) != expected_fields:
                raise ValueError()
            if any(len(values) != 1 for values in parsed.values()):
                raise ValueError()
            return {key: values[0] for key, values in parsed.items()}

        def _reject(self, status: int = 404) -> None:
            strings = _language_text(session.language)
            self._send_html(
                status,
                _render_result(
                    strings["rejected_title"],
                    strings["rejected_message"],
                    success=False,
                    language=session.language,
                ),
            )

        def do_GET(self) -> None:
            if (
                session.completed.is_set()
                or not self._host_is_valid()
                or self.path != session.form_path
            ):
                self._reject()
                return
            self._send_html(
                200,
                _render_form(
                    csrf_token=session.csrf_token,
                    submit_path=session.submit_path,
                    cancel_path=session.cancel_path,
                    language=session.language,
                    existing_configured=session.existing_configured,
                ),
            )

        def do_POST(self) -> None:
            if (
                session.completed.is_set()
                or not self._host_is_valid()
                or not self._post_is_same_origin()
            ):
                self._reject(403)
                return

            if self.path == session.cancel_path:
                try:
                    fields = self._read_form({"csrf"})
                except (OSError, UnicodeError, ValueError):
                    self._reject(400)
                    return
                if not secrets.compare_digest(fields["csrf"], session.csrf_token):
                    self._reject(403)
                    return
                strings = _language_text(session.language)
                self._send_html(
                    200,
                    _render_result(
                        strings["cancelled_title"],
                        strings["cancelled_message"],
                        success=False,
                        language=session.language,
                    ),
                )
                session.result = "CANCELLED"
                session.completed.set()
                return

            if self.path != session.submit_path:
                self._reject()
                return
            try:
                fields = self._read_form({"csrf", "api_key"})
            except (OSError, UnicodeError, ValueError):
                self._reject(400)
                return
            if not secrets.compare_digest(fields["csrf"], session.csrf_token):
                self._reject(403)
                return

            api_key = fields["api_key"]
            if not _is_valid_api_key(api_key):
                self._send_html(
                    400,
                    _render_form(
                        csrf_token=session.csrf_token,
                        submit_path=session.submit_path,
                        cancel_path=session.cancel_path,
                        language=session.language,
                        existing_configured=session.existing_configured,
                        error_message=_language_text(session.language)["invalid"],
                    ),
                )
                return

            try:
                committed = session.commit(api_key)
            except Exception:
                committed = False
            if not committed:
                strings = _language_text(session.language)
                self._send_html(
                    500,
                    _render_result(
                        strings["save_failed_title"],
                        strings["save_failed_message"],
                        success=False,
                        language=session.language,
                    ),
                )
                session.result = "UNAVAILABLE"
                session.completed.set()
                return

            strings = _language_text(session.language)
            self._send_html(
                200,
                _render_result(
                    strings["saved_title"],
                    strings["saved_message"],
                    success=True,
                    language=session.language,
                ),
            )
            session.result = "CONFIGURED"
            session.completed.set()

        def do_HEAD(self) -> None:
            self._reject(405)

        def do_PUT(self) -> None:
            self._reject(405)

        def do_DELETE(self) -> None:
            self._reject(405)

        def do_OPTIONS(self) -> None:
            self._reject(405)

    return ApiKeyHandler


def _open_system_browser(url: str) -> bool:
    if sys.platform.startswith("linux") and not (
        os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
    ):
        return False
    return bool(webbrowser.open(url, new=2, autoraise=True))


def run_browser_api_key_ui(
    commit: Callable[[str], bool],
    *,
    existing_configured: bool = False,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    opener: Optional[Callable[[str], bool]] = None,
    on_ready: Optional[Callable[[], None]] = None,
    language: str = "en",
) -> None:
    """Open the local form and return after a successful save, cancellation, or timeout."""
    _language_text(language)
    if (
        not callable(commit)
        or not isinstance(existing_configured, bool)
        or not isinstance(timeout_seconds, (int, float))
        or timeout_seconds <= 0
        or timeout_seconds > 900
    ):
        raise BrowserApiKeyUIError("INVALID_INPUT")
    if opener is None:
        opener = _open_system_browser

    session = _Session(
        commit,
        secrets.token_urlsafe(32),
        secrets.token_urlsafe(32),
        language,
        existing_configured,
    )
    try:
        server = _LoopbackHTTPServer((LOOPBACK_HOST, 0), _handler_type(session))
    except OSError as exc:
        raise BrowserApiKeyUIError("UNAVAILABLE") from exc

    host, port = server.server_address
    session.origin = f"http://{host}:{port}"
    session.expected_host = f"{host}:{port}"
    url = session.origin + session.form_path
    try:
        try:
            opened = bool(opener(url))
        except Exception as exc:
            raise BrowserApiKeyUIError("OPEN_FAILED") from exc
        if not opened:
            raise BrowserApiKeyUIError("OPEN_FAILED")
        if on_ready is not None:
            on_ready()

        deadline = time.monotonic() + float(timeout_seconds)
        while not session.completed.is_set():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise BrowserApiKeyUIError("TIMEOUT")
            server.timeout = min(0.25, remaining)
            server.handle_request()

        if session.result != "CONFIGURED":
            raise BrowserApiKeyUIError(session.result)
    finally:
        server.server_close()
