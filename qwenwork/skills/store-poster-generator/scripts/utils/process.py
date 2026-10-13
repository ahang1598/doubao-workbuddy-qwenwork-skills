"""
进程工具：提供通过 venv Python 启动独立子进程的通用方法。

所有需要在 scripts/ 中拉起子进程的场景都应使用本模块，
确保子进程运行在 cli.py 注入的 venv 环境中。
"""

import os
import subprocess
import sys
from pathlib import Path

# scripts/ 目录，子进程需要将其加入 PYTHONPATH 以找到 services 等模块
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent


def get_venv_python() -> str:
    """获取 venv Python 路径（由 cli.py 通过 SKILL_VENV_PYTHON 环境变量注入）。

    fallback 到当前 sys.executable。
    """
    venv_python = os.environ.get("SKILL_VENV_PYTHON")
    if venv_python and Path(venv_python).exists():
        return venv_python
    return sys.executable


def launch_detached_script(
    script_path: str | Path,
    args: list[str],
    *,
    stdout_log: str | Path | None = None,
    stderr_log: str | Path | None = None,
    inherit_output: bool = True,
) -> subprocess.Popen:
    """通过 venv Python 以独立子进程启动指定脚本（主进程退出后子进程仍存活）。

    Args:
        script_path: 要执行的 Python 脚本路径
        args: 传递给脚本的参数列表
        stdout_log: stdout 重定向的日志文件路径（可选，默认丢弃）
        stderr_log: stderr 重定向的日志文件路径（可选，默认丢弃）
        inherit_output: 为 True 时 stdout/stderr 继承主进程（CLI 可直接看到输出），
                        同时仍通过 --stdout-log 参数让子进程自行写入日志文件

    Returns:
        启动的 Popen 对象
    """
    venv_python = get_venv_python()
    command = [venv_python, str(script_path)] + args

    if inherit_output:
        stdout_target = None  # 继承主进程 stdout
        stderr_target = None  # 继承主进程 stderr
    else:
        stdout_target = open(stdout_log, "w") if stdout_log else subprocess.DEVNULL
        stderr_target = open(stderr_log, "w") if stderr_log else subprocess.DEVNULL

    env = os.environ.copy()
    scripts_dir = str(_SCRIPTS_DIR)
    python_path = env.get("PYTHONPATH", "")
    if scripts_dir not in python_path.split(os.pathsep):
        env["PYTHONPATH"] = scripts_dir + (os.pathsep + python_path if python_path else "")

    return subprocess.Popen(
        command,
        stdout=stdout_target,
        stderr=stderr_target,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
        close_fds=True,
        env=env,
    )
