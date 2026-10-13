#!/usr/bin/env python3
"""
Skill CLI 入口（零外部依赖）

本脚本仅使用 Python 标准库，负责：
1. 定位或创建自定义 .venv 虚拟环境（通过 uv）
2. 用 uv pip install -r dependencies.txt 同步依赖（uv 自动跳过已安装项）
3. 用该 venv 的 Python 执行 main.py，并透传所有参数

使用方式：
  python cli.py <command> [options]

示例：
  python cli.py skill-exists --skillname store-poster-generator
  python cli.py --skip-deps call-mcp list

.venv 位置由 _resolve_venv_dir() 解析，优先使用 AGENT_WORK_ROOT 环境变量。
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

# ── 常量 ────────────────────────────────────────────────────────────────────

SCRIPTS_DIR = Path(__file__).resolve().parent
REQUIREMENTS_FILE = SCRIPTS_DIR / "dependencies.txt"
CLI_MAIN_FILE = SCRIPTS_DIR / "main.py"

_VENV_RELATIVE_PARTS = ("workspace", ".store-poster-generator", "venv")
_VENV_FALLBACK_ROOT = (SCRIPTS_DIR / ".." / ".." / "..").resolve()


def _resolve_venv_dir() -> Path:
    """
    解析 .venv 目录的绝对路径。

    优先级：
    1. AGENT_WORK_ROOT 环境变量
    2. 回退到 scripts/ 的上三级目录
    """
    agent_root = os.environ.get("AGENT_WORK_ROOT")
    base = Path(agent_root) if agent_root else _VENV_FALLBACK_ROOT
    return base.joinpath(*_VENV_RELATIVE_PARTS)

def _print_step(icon: str, message: str) -> None:
    print(f"  {icon} {message}", flush=True)


def _get_venv_python(venv_dir: Path) -> Path:
    """返回 venv 中 python 可执行文件的路径。"""
    if sys.platform == "win32":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


# ── 自检与初始化 ────────────────────────────────────────────────────────────


def ensure_uv() -> str:
    """确保 uv 可用，返回 uv 的路径。不可用则退出。"""
    uv_path = shutil.which("uv")
    if not uv_path:
        print("❌ 未找到 uv 包管理器，请先安装：")
        print("   https://docs.astral.sh/uv/getting-started/installation/")
        sys.exit(1)
    return uv_path


def ensure_venv(uv_path: str, venv_dir: Path) -> Path:
    """确保 venv 存在，不存在则用 uv 创建。返回 venv python 路径。"""
    venv_python = _get_venv_python(venv_dir)

    if venv_python.exists():
        return venv_python

    try:
        subprocess.run(
            [uv_path, "venv", str(venv_dir)],
            check=True,
            text=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as error:
        _print_step("❌", f"创建虚拟环境失败: {error.stderr.strip()}")
        sys.exit(1)

    return venv_python




def _is_venv_corrupted(stderr: str) -> bool:
    """判断错误信息是否表明 venv 已损坏。"""
    corruption_signals = [
        "No module named 'encodings'",
        "Failed to inspect Python interpreter",
        "Could not find platform independent libraries",
    ]
    return any(signal in stderr for signal in corruption_signals)


def install_dependencies(uv_path: str, venv_python: Path, venv_dir: Path) -> Path:
    """用 uv 直接从 dependencies.txt 安装依赖到 venv 中。

    uv 会自动跳过已安装的包，无需手动检测缺失项。
    如果检测到 venv 损坏（如 Python 解释器失效），会自动重建。

    Returns:
        最终可用的 venv python 路径（重建后可能与传入的不同）
    """
    if not REQUIREMENTS_FILE.exists():
        return venv_python

    try:
        subprocess.run(
            [
                uv_path, "pip", "install",
                "--python", str(venv_python),
                "-r", str(REQUIREMENTS_FILE),
            ],
            check=True,
            text=True,
            capture_output=True,
        )
        return venv_python
    except subprocess.CalledProcessError as error:
        if _is_venv_corrupted(error.stderr):
            _print_step("⚠️", "检测到虚拟环境损坏，正在重建...")
            venv_python = _rebuild_venv(uv_path, venv_dir)
            return install_dependencies(uv_path, venv_python, venv_dir)
        _print_step("❌", f"依赖安装失败: {error.stderr.strip()}")
        sys.exit(1)


def _rebuild_venv(uv_path: str, venv_dir: Path) -> Path:
    """删除并重建虚拟环境，返回新的 venv python 路径。"""
    shutil.rmtree(venv_dir, ignore_errors=True)
    _print_step("🗑️", f"已删除损坏的虚拟环境: {venv_dir}")

    venv_python = ensure_venv(uv_path, venv_dir)
    _print_step("✅", "虚拟环境已重建")
    return venv_python


# ── 主入口 ──────────────────────────────────────────────────────────────────


def main():
    # 解析启动器自身的参数（不影响 cli.py 的参数）
    skip_deps = "--skip-deps" in sys.argv
    forward_args = [arg for arg in sys.argv[1:] if arg != "--skip-deps"]

    # 1. 确保 uv 可用
    uv_path = ensure_uv()

    # 2. 确保 venv 存在
    venv_dir = _resolve_venv_dir()
    venv_python = ensure_venv(uv_path, venv_dir)

    # 3. 安装依赖（venv 损坏时会自动重建，返回最新路径）
    if not skip_deps:
        venv_python = install_dependencies(uv_path, venv_python, venv_dir)

    # 4. 将 venv python 路径注入环境变量，供子进程（如 cdp_launcher）使用
    os.environ["SKILL_VENV_PYTHON"] = str(venv_python)

    # 5. 用 venv python 执行 main.py
    if not CLI_MAIN_FILE.exists():
        _print_step("❌", f"未找到 main.py: {CLI_MAIN_FILE}")
        sys.exit(1)

    result = subprocess.run(
        [str(venv_python), str(CLI_MAIN_FILE)] + forward_args,
    )
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
