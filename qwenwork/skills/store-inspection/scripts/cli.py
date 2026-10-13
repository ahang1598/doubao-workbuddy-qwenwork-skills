"""CLI 入口（``store-inspection`` console_script）。

精简的入口模块，本身不包含任何业务逻辑：

1. 通过 :func:`scripts.commands.load_all_commands` 触发命令自动注册。
2. :func:`build_parser` 遍历注册表，给每条命令挂上对应的 sub-parser。
3. :func:`main` 解析命令行 → 实例化 :class:`AppContext` → 调用 ``args.func(args, ctx)``。

所有命令处理函数与服务编排逻辑都在 ``scripts/commands/`` 与 ``scripts/services/`` 内。
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Optional, Sequence

# ── 依赖路径解析 ────────────────────────────────────────────────────────────

SCRIPTS_DIR = Path(__file__).resolve().parent
REQUIREMENTS_FILE = SCRIPTS_DIR.parent / "requirements.txt"

_VENV_RELATIVE_PARTS = ("workspace", ".store-inspection-skills-group", "pip-env")
_VENV_FALLBACK_ROOT = (SCRIPTS_DIR / ".." / ".." / "..").resolve()


def _resolve_deps_dir() -> Path:
    """解析依赖安装目录的绝对路径。

    优先级：
    1. AGENT_WORK_ROOT 环境变量
    2. 回退到 scripts/ 的上三级目录
    """
    agent_root = os.environ.get("AGENT_WORK_ROOT")
    base = Path(agent_root) if agent_root else _VENV_FALLBACK_ROOT
    return base.joinpath(*_VENV_RELATIVE_PARTS)


def _setup_environment() -> None:
    """初始化依赖目录、sys.path 和环境变量。"""
    deps_dir = _resolve_deps_dir()
    deps_dir_str = str(deps_dir)

    # 将依赖目录加入 PYTHONPATH
    existing_pythonpath = os.environ.get("PYTHONPATH", "")
    if deps_dir_str not in existing_pythonpath.split(os.pathsep):
        os.environ["PYTHONPATH"] = (
            deps_dir_str + os.pathsep + existing_pythonpath
            if existing_pythonpath
            else deps_dir_str
        )

    # 加入当前进程的 sys.path
    if deps_dir_str not in sys.path:
        sys.path.insert(0, deps_dir_str)

    # 注入环境变量供子进程使用
    os.environ["SKILL_VENV_PYTHON"] = sys.executable
    os.environ["SKILL_DEPS_DIR"] = deps_dir_str

    # 将项目根目录（scripts/ 的父目录）加入 sys.path，确保 `from scripts.xxx` 包导入正常
    project_root_str = str(SCRIPTS_DIR.parent)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)


_setup_environment()

from scripts.app import AppContext
from scripts.commands import load_all_commands, registry
from scripts.domain.exceptions import StoreTaskDispatcherError
from scripts.utils.output import err

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """构造主 parser 并挂载所有已注册命令。"""
    # 触发自动注册（幂等，重复调用安全）
    load_all_commands()

    parser = argparse.ArgumentParser(
        prog="store-inspection",
        description="门店任务中心自动派发系统 CLI",
    )
    parser.add_argument(
        "--log-level",
        default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="日志级别（默认 WARNING）",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    for name, cmd in registry.items():
        cmd_parser = sub.add_parser(name, help=cmd.help)
        cmd.configure(cmd_parser)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI 入口函数。

    Args:
        argv: 命令行参数（默认从 ``sys.argv`` 读取）。

    Returns:
        进程退出码：0 成功，>0 各种失败。
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level, logging.WARNING),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    ctx = AppContext()
    try:
        return int(args.func(args, ctx) or 0)
    except StoreTaskDispatcherError as exc:
        err(str(exc))
        return 1
    except KeyboardInterrupt:
        err("用户中断")
        return 130
    except Exception as exc:  # pragma: no cover - 兜底
        logger.exception("未预期的异常")
        err(f"未预期的异常: {exc}")
        return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
