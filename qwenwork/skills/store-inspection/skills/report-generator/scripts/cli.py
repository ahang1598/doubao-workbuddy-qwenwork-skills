#!/usr/bin/env python3
"""
report-generator CLI 入口（零外部依赖）

本脚本仅使用 Python 标准库，负责：
1. 自动发现系统 Python 运行时（支持 macOS / Windows / Linux）
2. 定位或创建自定义 venv 虚拟环境
3. 用 pip install -r dependencies.txt 同步依赖
4. 用该 venv 的 Python 执行 main.py，并透传所有参数

使用方式：
  python3 <skill-path>/scripts/cli.py <command> [options]

示例：
  python3 scripts/cli.py generate-report data.json --fields fields.json
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
REQUIREMENTS_FILE = SCRIPTS_DIR.parent / "dependencies.txt"
CLI_MAIN_FILE = SCRIPTS_DIR / "main.py"

_VENV_SUBDIRS = (".store-inspection-report", "venv")

_PYTHON_CANDIDATES_UNIX = ("python3", "python")
_PYTHON_CANDIDATES_WIN = ("python.exe", "python3.exe")

_BIN_DIR_NAMES = {".qoderwork", ".bin"}


def _make_utf8_env(extra: dict = None) -> dict:
    """构建带 UTF-8 编码参数的环境变量字典，解决 Windows 子进程乱码问题。"""
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    if extra:
        env.update(extra)
    return env


def _is_writable_dir(directory: Path) -> bool:
    """检查目录是否存在且可写，或父目录可创建子目录。"""
    check = directory
    while not check.exists():
        check = check.parent
        if check == check.parent:
            return False
    return os.access(str(check), os.W_OK)


def _discover_python() -> str:
    """发现可用的 Python 运行时路径。

    查找策略：
    1. PATH 中的 python3 / python
    2. 从当前脚本目录向上逐级查找 .qoderwork/.bin 目录下的 python 可执行文件

    Returns:
        Python 可执行文件的绝对路径

    Raises:
        SystemExit: 找不到任何可用的 Python 运行时
    """
    candidates = _PYTHON_CANDIDATES_WIN if sys.platform == "win32" else _PYTHON_CANDIDATES_UNIX

    for name in candidates:
        found = shutil.which(name)
        if found:
            return found

    search_dir = SCRIPTS_DIR
    root = Path(search_dir.anchor)
    while search_dir != root:
        search_dir = search_dir.parent
        for bin_dir_name in _BIN_DIR_NAMES:
            bin_dir = search_dir / bin_dir_name
            if not bin_dir.is_dir():
                continue
            for name in candidates:
                python_path = bin_dir / name
                if python_path.is_file() and os.access(str(python_path), os.X_OK):
                    return str(python_path)

    print("❌ 未找到 Python 运行时。")
    print("   已尝试以下查找方式：")
    print(f"   1. PATH 中查找 {', '.join(candidates)}")
    print(f"   2. 从 {SCRIPTS_DIR} 向上查找 .qoderwork/.bin 目录下的 Python")
    print("   请确保系统已安装 Python 3.8+")
    sys.exit(1)


def _resolve_venv_dir() -> Path:
    """解析 venv 目录的绝对路径。

    优先级（逐级 fallback，选择第一个可写的位置）：
    1. AGENT_WORK_ROOT/workspace/.store-inspection-report/venv
    2. SKILL 根目录的上三级/workspace/.store-inspection-report/venv
    3. ~/.store-inspection-report/venv
    """
    candidates = []

    agent_root = os.environ.get("AGENT_WORK_ROOT")
    if agent_root:
        candidates.append(Path(agent_root) / "workspace" / _VENV_SUBDIRS[0] / _VENV_SUBDIRS[1])

    skill_ancestor = (SCRIPTS_DIR / ".." / ".." / "..").resolve()
    candidates.append(skill_ancestor / "workspace" / _VENV_SUBDIRS[0] / _VENV_SUBDIRS[1])

    candidates.append(Path.home() / _VENV_SUBDIRS[0] / _VENV_SUBDIRS[1])

    for candidate in candidates:
        if _is_writable_dir(candidate.parent):
            return candidate

    return candidates[-1]


def _get_venv_python(venv_dir: Path) -> Path:
    """返回 venv 中 python 可执行文件的路径。"""
    if sys.platform == "win32":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _get_venv_pip(venv_dir: Path) -> Path:
    """返回 venv 中 pip 可执行文件的路径。"""
    if sys.platform == "win32":
        return venv_dir / "Scripts" / "pip.exe"
    return venv_dir / "bin" / "pip"


def _is_venv_healthy(venv_python: Path) -> bool:
    """检查 venv 是否健康可用（能正常执行 python --version）。"""
    if not venv_python.exists():
        return False
    try:
        result = subprocess.run(
            [str(venv_python), "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            env=_make_utf8_env(),
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


def _recreate_venv(system_python: str, venv_dir: Path) -> bool:
    """删除已损坏的 venv 并重新创建。

    Returns:
        True 表示创建成功，False 表示创建失败
    """
    if venv_dir.exists():
        shutil.rmtree(str(venv_dir), ignore_errors=True)

    try:
        subprocess.run(
            [system_python, "-m", "venv", str(venv_dir)],
            check=True,
            text=True,
            capture_output=True,
            env=_make_utf8_env(),
        )
        return True
    except subprocess.CalledProcessError as error:
        print(f"  ⚠️ 创建虚拟环境失败: {error.stderr.strip()}")
        return False


def ensure_venv(system_python: str, venv_dir: Path) -> Path:
    """确保 venv 存在且健康可用，失败时降级为系统 Python。

    检查逻辑：
    1. venv python 存在且健康 → 直接复用
    2. venv python 存在但不健康 → 删除并重建，重建失败则降级
    3. venv python 不存在 → 新建，新建失败则降级
    4. 重建后仍不健康 → 降级为系统 Python
    """
    venv_python = _get_venv_python(venv_dir)

    if venv_python.exists():
        if _is_venv_healthy(venv_python):
            return venv_python
        print("  ⚠️ venv 不健康，尝试重建...")
        if _recreate_venv(system_python, venv_dir):
            new_python = _get_venv_python(venv_dir)
            if _is_venv_healthy(new_python):
                return new_python
        print(f"  ⚠️ venv 重建后仍不可用，降级为系统 Python: {system_python}")
        return Path(system_python)

    if _recreate_venv(system_python, venv_dir):
        new_python = _get_venv_python(venv_dir)
        if _is_venv_healthy(new_python):
            return new_python

    print(f"  ⚠️ venv 创建失败，降级为系统 Python: {system_python}")
    return Path(system_python)


def _is_using_venv(python_path: Path, venv_dir: Path) -> bool:
    """判断当前使用的 Python 是否来自 venv。"""
    try:
        return str(python_path).startswith(str(venv_dir))
    except (ValueError, TypeError):
        return False


def install_dependencies(venv_dir: Path, venv_python: Path) -> None:
    """安装依赖。如果使用 venv 则安装到 venv，否则用 --user 模式。"""
    if not REQUIREMENTS_FILE.exists():
        return

    using_venv = _is_using_venv(venv_python, venv_dir)

    if using_venv:
        venv_pip = _get_venv_pip(venv_dir)
        if venv_pip.exists():
            pip_command = [str(venv_pip)]
        else:
            pip_command = [str(venv_python), "-m", "pip"]
        install_args = pip_command + [
            "install", "-r", str(REQUIREMENTS_FILE), "-q",
        ]
    else:
        install_args = [
            str(venv_python), "-m", "pip",
            "install", "-r", str(REQUIREMENTS_FILE), "-q", "--user",
        ]

    try:
        subprocess.run(
            install_args,
            check=True,
            text=True,
            capture_output=True,
            env=_make_utf8_env(),
        )
    except subprocess.CalledProcessError as error:
        stderr_text = error.stderr.strip() if error.stderr else ""
        if "No module named pip" in stderr_text:
            print("  ⚠️ pip 不可用，跳过依赖安装（依赖可能已预装）")
            return
        print(f"  ❌ 依赖安装失败: {stderr_text}")
        sys.exit(1)


def main():
    skip_deps = "--skip-deps" in sys.argv
    forward_args = [arg for arg in sys.argv[1:] if arg != "--skip-deps"]

    system_python = _discover_python()

    venv_dir = _resolve_venv_dir()
    venv_python = ensure_venv(system_python, venv_dir)

    if not skip_deps:
        install_dependencies(venv_dir, venv_python)

    os.environ["SKILL_VENV_PYTHON"] = str(venv_python)

    if not CLI_MAIN_FILE.exists():
        print(f"  ❌ 未找到 main.py: {CLI_MAIN_FILE}")
        sys.exit(1)

    result = subprocess.run(
        [str(venv_python), str(CLI_MAIN_FILE)] + forward_args,
        env=_make_utf8_env(),
    )
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
