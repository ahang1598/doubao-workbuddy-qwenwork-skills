"""claw_pipe_http.py - HTTP/1.1 over Windows 命名管道客户端（stdlib-only，无第三方依赖）

桌面形态下，skill 的云端接口调用经主进程 SkillApiProxy（\\\\.\\pipe\\claw-skill）转发：
代理由主进程统一注入 businessCredential 鉴权，skill 侧零业务凭证，仅携带
CLAW_SKILL_TOKEN 本机防借用令牌（主进程经 AgentServer 环境变量注入、孙进程继承）。

为什么手写：requests/urllib 都不支持 Windows 命名管道；Node 侧管道服务端是
流式（byte-stream）管道，用 os.open（CreateFile）按普通文件读写即可，无需 pywin32。

仅实现 skill 所需最小子集：
  - 每请求一连接（服务端按连接创建管道实例，ERROR_PIPE_BUSY 等位重试）
  - 请求：显式 Content-Length + Connection: close
  - 响应：Content-Length / chunked / 读至 EOF 三种 body 形态
  - iter_lines() 增量读取，支撑 SSE 长连接（PPT 生成单轮可达数十分钟）

PipeHttpResponse 对齐 requests.Response 的最小接口
（status_code / headers / text / json() / iter_lines() / raise_for_status() /
上下文管理），调用点与旧 requests 写法互换即可。
"""

from __future__ import annotations

import json
import os
import time

# 默认管道（主进程 SkillApiProxy；@core/net/pipe-paths 的 PIPE_CHANNELS.skill 同源）
DEFAULT_PIPE_PATH = r"\\.\pipe\claw-skill"

# ERROR_PIPE_BUSY = 231：服务端管道实例暂时占满，等位重试
_ERROR_PIPE_BUSY = 231
_CONNECT_TIMEOUT_SEC = 10.0
_HEAD_MAX_BYTES = 64 * 1024


class PipeHttpError(Exception):
    """管道 HTTP 调用失败（连接/协议层错误）。"""


def pipe_path_from_url(url: str) -> str:
    """np://claw-skill → \\\\.\\pipe\\claw-skill（authority 段即管道名，与 jiuwen np_transport 同约定）。"""
    rest = url[5:]  # 去掉 np://
    name = rest.split("/", 1)[0].strip()
    if not name:
        raise PipeHttpError(f"np:// URL 缺少管道名: {url}")
    return "\\\\.\\pipe\\" + name


def _connect(pipe_path: str, timeout: float) -> int:
    """CreateFile 连接管道（ERROR_PIPE_BUSY 等位重试）。返回 os fd。"""
    deadline = time.monotonic() + timeout
    while True:
        try:
            return os.open(pipe_path, os.O_RDWR | os.O_BINARY)
        except OSError as exc:
            if getattr(exc, "winerror", None) == _ERROR_PIPE_BUSY and time.monotonic() < deadline:
                time.sleep(0.05)
                continue
            raise PipeHttpError(f"连接命名管道失败 {pipe_path}: {exc}") from exc


def _write_all(fd: int, data: bytes) -> None:
    view = memoryview(data)
    while view:
        written = os.write(fd, view)
        view = view[written:]


def _read_head(fd: int) -> tuple[bytes, bytes]:
    """读取响应头（至 \\r\\n\\r\\n），返回 (头字节, 已读出的 body 前缀)。"""
    buf = bytearray()
    while True:
        idx = buf.find(b"\r\n\r\n")
        if idx >= 0:
            return bytes(buf[:idx]), bytes(buf[idx + 4:])
        if len(buf) > _HEAD_MAX_BYTES:
            raise PipeHttpError("响应头超限（>64KiB）")
        chunk = os.read(fd, 65536)
        if not chunk:
            raise PipeHttpError("读取响应头时连接被关闭")
        buf.extend(chunk)


def _parse_head(head: bytes) -> tuple[int, dict[str, str]]:
    lines = head.decode("iso-8859-1").split("\r\n")
    parts = lines[0].split(" ", 2)
    if len(parts) < 2 or not parts[1].isdigit():
        raise PipeHttpError(f"非法响应行: {lines[0]!r}")
    headers: dict[str, str] = {}
    for line in lines[1:]:
        if not line or ":" not in line:
            continue
        k, v = line.split(":", 1)
        headers[k.strip().lower()] = v.strip()
    return int(parts[1]), headers


class _BodyReader:
    """响应 body 增量读取：identity（Content-Length / 读至 EOF）与 chunked 两种形态。"""

    def __init__(self, fd: int, headers: dict[str, str], initial: bytes):
        self._fd = fd
        self._chunked = "chunked" in headers.get("transfer-encoding", "").lower()
        length = headers.get("content-length", "")
        self._remaining: int | None = int(length) if length.isdigit() else None
        self._buf = bytearray(initial)
        self._eof = False

    def _fill(self, need: int | None = None) -> None:
        """至少读够 need 字节（None = 读一轮即可）；EOF 置位。"""
        while not self._eof and (need is None or len(self._buf) < need):
            try:
                chunk = os.read(self._fd, 65536)
            except OSError as exc:
                raise PipeHttpError(f"读取响应体失败: {exc}") from exc
            if not chunk:
                self._eof = True
                break
            self._buf.extend(chunk)
            if need is None:
                break

    def _readline(self) -> bytes:
        while True:
            idx = self._buf.find(b"\n")
            if idx >= 0:
                line = bytes(self._buf[: idx + 1])
                del self._buf[: idx + 1]
                return line
            if self._eof:
                line = bytes(self._buf)
                self._buf.clear()
                return line
            self._fill()

    def iter_chunks(self):
        """逐块产出 body 字节（chunked 已解码）。"""
        if not self._chunked:
            remaining = self._remaining
            while True:
                if self._buf:
                    data = bytes(self._buf)
                    self._buf.clear()
                    if remaining is not None:
                        # 多读的留给下一次（Connection: close 下实际不会发生）
                        data, rest = data[:remaining], data[remaining:]
                        self._buf.extend(rest)
                    if data:
                        yield data
                    if remaining is not None:
                        remaining -= len(data)
                        if remaining <= 0:
                            return
                if self._eof:
                    return
                self._fill()
            return
        # chunked：逐 chunk 解析（尺寸行十六进制 + CRLF，0 尺寸 + trailer 区结束）
        while True:
            line = self._readline().strip()
            try:
                size = int(line.split(b";", 1)[0] or b"0", 16)
            except ValueError:
                raise PipeHttpError(f"非法 chunk 头: {line!r}")
            if size == 0:
                while True:
                    trailer = self._readline()
                    if trailer in (b"\r\n", b"\n", b""):
                        break
                return
            self._fill(size + 2)  # data + CRLF
            if len(self._buf) < size:
                raise PipeHttpError("chunk 数据不完整（连接提前关闭）")
            data = bytes(self._buf[:size])
            del self._buf[: size + 2]
            yield data


class PipeHttpResponse:
    """对齐 requests.Response 的最小接口，与旧调用点互换。"""

    def __init__(self, fd: int, status: int, headers: dict[str, str], initial: bytes):
        self._fd = fd
        self.status_code = status
        self.headers = headers
        self._reader = _BodyReader(fd, headers, initial)
        self._closed = False

    def iter_lines(self, decode_unicode: bool = False):
        """按行产出（不含换行符；decode_unicode=True 时产出 str）——SSE 流式消费用。"""
        pending = b""
        for chunk in self._reader.iter_chunks():
            pending += chunk
            while True:
                idx = pending.find(b"\n")
                if idx < 0:
                    break
                line = pending[:idx]
                pending = pending[idx + 1:]
                if line.endswith(b"\r"):
                    line = line[:-1]
                yield line.decode("utf-8", errors="replace") if decode_unicode else line
        if pending:
            line = pending[:-1] if pending.endswith(b"\r") else pending
            yield line.decode("utf-8", errors="replace") if decode_unicode else line

    def read(self) -> bytes:
        return b"".join(self._reader.iter_chunks())

    @property
    def text(self) -> str:
        return self.read().decode("utf-8", errors="replace")

    def json(self):
        return json.loads(self.text)

    def raise_for_status(self) -> None:
        if not (200 <= self.status_code < 300):
            raise PipeHttpError(f"HTTP {self.status_code}: {self.text[:500]}")

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            try:
                os.close(self._fd)
            except OSError:
                pass

    def __enter__(self) -> "PipeHttpResponse":
        return self

    def __exit__(self, *exc) -> bool:
        self.close()
        return False


def pipe_request(
    method: str,
    path: str,
    *,
    body: bytes = b"",
    headers: dict[str, str] | None = None,
    pipe_path: str = DEFAULT_PIPE_PATH,
    token: str = "",
    connect_timeout: float = _CONNECT_TIMEOUT_SEC,
) -> PipeHttpResponse:
    """经命名管道发一个 HTTP/1.1 请求。响应体流式可读（调用方负责 close/with）。

    无读超时（os.read 阻塞读）——SSE 长流为设计内场景，活性由服务端心跳 +
    调用方自身的轮询/监控逻辑保证（generate_ppt.py 的心跳线程与日志监控）。
    """
    if not path.startswith("/"):
        path = "/" + path
    hdrs = {
        "Host": "claw-skill",
        "Connection": "close",
        "Content-Length": str(len(body)),
    }
    if token:
        hdrs["Authorization"] = f"Bearer {token}"
    for k, v in (headers or {}).items():
        hdrs[k] = v
    head = f"{method} {path} HTTP/1.1\r\n" + "".join(f"{k}: {v}\r\n" for k, v in hdrs.items()) + "\r\n"
    fd = _connect(pipe_path, connect_timeout)
    try:
        _write_all(fd, head.encode("ascii") + body)
        raw_head, rest = _read_head(fd)
    except Exception:
        os.close(fd)
        raise
    status, resp_headers = _parse_head(raw_head)
    return PipeHttpResponse(fd, status, resp_headers, rest)


def post_json(
    path: str,
    payload,
    *,
    pipe_path: str = DEFAULT_PIPE_PATH,
    token: str = "",
    extra_headers: dict[str, str] | None = None,
) -> tuple[int, dict]:
    """POST JSON 并收回完整 JSON 响应（小 body 场景：OSMS prepare/completeAndQuery 等）。"""
    headers = {"Content-Type": "application/json"}
    if extra_headers:
        headers.update(extra_headers)
    with pipe_request(
        "POST",
        path,
        body=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        pipe_path=pipe_path,
        token=token,
    ) as resp:
        text = resp.text
        return resp.status_code, (json.loads(text) if text else {})
