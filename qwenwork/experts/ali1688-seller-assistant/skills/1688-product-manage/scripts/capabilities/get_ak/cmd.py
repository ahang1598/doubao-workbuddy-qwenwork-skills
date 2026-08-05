#!/usr/bin/env python3
"""AK 自动获取命令 — CLI 入口"""

from __future__ import annotations

COMMAND_NAME = "get_ak"
COMMAND_DESC = "通过浏览器自动获取并配置 AK"

import os
import sys
import subprocess


def main(args=None):
    """
    AK 自动获取命令入口。

    调用 authorize.py 启动本地回调服务器并自动打开浏览器，
    用户在浏览器中完成 1688 授权后，AK 自动写入 ak_store 文件。
    """
    if args is None:
        args = sys.argv[1:]

    # 解析 --timeout 参数（默认 300 秒）
    timeout = 300
    for i, arg in enumerate(args):
        if arg == "--timeout" and i + 1 < len(args):
            try:
                timeout = int(args[i + 1])
            except ValueError:
                pass

    # 定位 authorize.py（位于 scripts/ 目录下）
    script_dir = os.path.dirname(os.path.abspath(__file__))
    authorize_py = os.path.normpath(os.path.join(script_dir, "..", "..", "authorize.py"))
    # 项目根目录，确保子进程能正确定位 workspace
    project_root = os.path.normpath(os.path.join(script_dir, "..", "..", ".."))

    # 调用 authorize.py --mode AK 启动浏览器授权流程
    result = subprocess.run(
        [sys.executable, authorize_py, "--mode", "AK", "--timeout", str(timeout)],
        cwd=project_root,
    )
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
