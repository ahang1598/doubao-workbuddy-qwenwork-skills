"""子进程调用的统一入口：两侧都强制 UTF-8。

背景（Windows 真机诊断 45dbba0b，2026-08-07）：驱动脚本在中文 Windows 上直接崩在
`subprocess._readerthread`：

    UnicodeDecodeError: 'gbk' codec can't decode ...

原因是 `subprocess.run(..., capture_output=True, text=True)` 不指定 `encoding`
时按**系统默认编码**解码子进程输出——中文 Windows 上是 GBK。本技能的脚本会输出
大量中文错误信息与话术（`——` `「」` `≥` `≤` 等字符 GBK 不一定覆盖），于是父进程
在读管道时崩溃，连子进程到底成功没有都拿不到。

后果不止是报错：模型看到驱动脚本"炸了"，转而自造 pandoc 链路生成报告，产出了
Markdown 原样漏出的残缺 docx。

两侧都要固定编码，缺一不可：
  - 父侧 `encoding="utf-8", errors="replace"` —— 即便子进程吐了非法字节也不崩；
  - 子侧 `PYTHONUTF8` / `PYTHONIOENCODING` —— 让子进程本身用 UTF-8 写
    stdout/stderr，否则子进程在 GBK 控制台上 print 中文同样会失败。

注意：调用方**不要**再直接用 `subprocess.run`，否则这条修复会被绕过。
"""

from __future__ import annotations

import os
import subprocess

# 子进程强制 UTF-8：PYTHONUTF8 开启 UTF-8 模式（3.7+），PYTHONIOENCODING 兜底
UTF8_ENV = {"PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}


def child_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    """在当前环境基础上叠加 UTF-8 强制项；`extra` 优先级最高。"""
    env = {**os.environ, **UTF8_ENV}
    if extra:
        env.update(extra)
    return env


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    """等价于 subprocess.run(cmd, capture_output=True, text=True)，但编码固定 UTF-8。

    `errors="replace"`：宁可个别字符显示为替换符，也不要因为解码失败让整条命令
    的成功/失败信息丢失——那正是 Windows 上把模型逼去自造路径的直接原因。
    """
    kwargs.setdefault("capture_output", True)
    kwargs.setdefault("text", True)
    kwargs.setdefault("encoding", "utf-8")
    kwargs.setdefault("errors", "replace")
    if "env" in kwargs and kwargs["env"] is not None:
        kwargs["env"] = child_env(kwargs["env"])
    else:
        kwargs["env"] = child_env()
    return subprocess.run(cmd, **kwargs)
