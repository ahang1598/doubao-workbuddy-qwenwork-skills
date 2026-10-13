"""Bounded input for Agent-authored recaps; never wait for a model on stdin."""
import io
import json
import os
from pathlib import Path
import queue
import stat
import sys
import threading

MAX_BYTES = 2 * 1024 * 1024
INPUT_TIMEOUT = 5
RETRY = '请在当前执行中写好复盘 JSON 文件，再 recap-submit --input-file <文件路径>；不要等待后台生成。'


class RecapInputError(ValueError):
    def __init__(self, code, message, *, line=None, column=None):
        self.code = code
        self.line = line
        self.column = column
        super().__init__(message + ' ' + RETRY)


def _read_fd(fd, received=None):
    data = bytearray()
    while len(data) <= MAX_BYTES:
        chunk = os.read(fd, min(65536, MAX_BYTES + 1 - len(data)))
        if not chunk:
            break
        if received is not None:
            received.set()
        data.extend(chunk)
    return bytes(data)


def _stdin_bytes():
    if sys.stdin.isatty():
        raise RecapInputError('RECAP_INPUT_REQUIRED', 'recap-submit 需要已生成的复盘内容。')
    # In-process callers can provide a finite memory stream, with no OS descriptor.
    if isinstance(sys.stdin, (io.StringIO, io.BytesIO)):
        value = sys.stdin.read(MAX_BYTES + 1)
        return value.encode('utf-8') if isinstance(value, str) else value
    results = queue.Queue(maxsize=1)
    received = threading.Event()
    fd = os.dup(sys.stdin.fileno())

    def read():
        try:
            results.put(_read_fd(fd, received))
        except OSError:
            results.put(RecapInputError('RECAP_INPUT_UNREADABLE', '无法读取复盘输入。'))
        finally:
            os.close(fd)

    # Raw descriptor reads avoid holding Python's buffered stdin lock at shutdown.
    # A daemon lets this one-shot CLI exit even if the host never closes its pipe.
    threading.Thread(target=read, daemon=True).start()
    try:
        value = results.get(timeout=INPUT_TIMEOUT)
    except queue.Empty:
        code = 'RECAP_INPUT_INCOMPLETE' if received.is_set() else 'RECAP_INPUT_REQUIRED'
        raise RecapInputError(code, '5 秒内未收到完整输入及 EOF。') from None
    if isinstance(value, Exception):
        raise value
    return value


def read_submission(input_file=None):
    try:
        if input_file is None:
            raw = _stdin_bytes()
        else:
            # Reject FIFOs/devices rather than hanging while opening an input file.
            fd = os.open(Path(input_file), os.O_RDONLY | getattr(os, 'O_NONBLOCK', 0))
            try:
                if not stat.S_ISREG(os.fstat(fd).st_mode):
                    raise RecapInputError('RECAP_INPUT_UNREADABLE', '复盘输入必须是普通 JSON 文件。')
                raw = _read_fd(fd)
            finally:
                os.close(fd)
    except (OSError, UnicodeError):
        raise RecapInputError('RECAP_INPUT_UNREADABLE', '无法读取复盘输入，请检查文件是否存在且可读。') from None
    if len(raw) > MAX_BYTES:
        raise RecapInputError('RECAP_INPUT_TOO_LARGE', '复盘输入不能超过 2 MiB。')
    if not raw.strip():
        raise RecapInputError('RECAP_INPUT_REQUIRED', '复盘输入为空。')
    try:
        value = json.loads(raw.decode('utf-8'))
    except json.JSONDecodeError as error:
        # The parser's reason contains no document text; never echo error.doc.
        raise RecapInputError("RECAP_INVALID_JSON",
                              f"JSON 语法错误：{error.msg}（第 {error.lineno} 行，第 {error.colno} 列）。请按位置局部修复，保留已有内容。",
                              line=error.lineno, column=error.colno) from None
    except (UnicodeError, ValueError, RecursionError):
        raise RecapInputError('RECAP_INVALID_JSON', '请提供完整、有效的 UTF-8 JSON。') from None
    if not isinstance(value, dict):
        raise RecapInputError('RECAP_INVALID_PAYLOAD', '复盘 JSON 顶层必须是对象。')
    return value
