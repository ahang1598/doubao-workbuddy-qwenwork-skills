#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""UTF-8 初始化模块 — 确保 stdout/stderr 在任何终端（Windows GBK、Linux C locale 等）都能
安全输出中文 + emoji，避免 `UnicodeEncodeError: 'gbk' codec can't encode character`。

用法：在需要中文/emoji 输出的脚本顶部（import 之后）加一行：

    from _utf8_bootstrap import enable_utf8_io
    enable_utf8_io()

即可。无需传参，幂等调用（重复调用安全）。
"""

from __future__ import annotations

import io
import os
import sys


def enable_utf8_io() -> None:
    """将当前进程的 stdout/stderr 切换为 UTF-8 编码。

    工作原理：
    1. Python 3.7+ 支持通过设置 PYTHONIOENCODING 环境变量或使用 io.TextIOWrapper 重包裹
       底层 buffer 来改变文本流编码。这里采用后者，保证对运行时立即生效。
    2. Windows PowerShell 默认 chcp 936（GBK），打印 emoji 直接崩溃；这里强制切到 utf-8，
       遇到实在无法表示的字符用 `errors="replace"` 降级为 `?` 而非抛异常。
    3. 已处于 utf-8 的环境（Linux/macOS/UTF-8 终端）不会做多余切换，幂等。
    """
    # 优先设置环境变量，子进程继承（例如用 subprocess 调用其他脚本时）
    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None:
            continue
        encoding = (getattr(stream, "encoding", "") or "").lower().replace("-", "")
        if encoding in ("utf8", "utf_8"):
            continue  # 已是 UTF-8，无需处理
        buffer = getattr(stream, "buffer", None)
        if buffer is None:
            # 极端情况下没有 buffer（如 pytest 捕获），跳过
            continue
        try:
            wrapped = io.TextIOWrapper(
                buffer,
                encoding="utf-8",
                errors="replace",
                newline="",
                line_buffering=True,
            )
            setattr(sys, stream_name, wrapped)
        except Exception:
            # 任何包装失败都不要让脚本因此崩溃
            pass


if __name__ == "__main__":
    # 自测
    enable_utf8_io()
    print("✅ UTF-8 bootstrap OK：中文 + emoji 📊🔍📌 都能正常输出")
