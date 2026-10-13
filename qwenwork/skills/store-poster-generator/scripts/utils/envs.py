import os
from pathlib import Path

IS_IN_DWS = bool(os.environ.get("DWS"))

# 当前文件: scripts/utils/envs.py
# workspace 位于 scripts 的上 5 级目录（根据项目结构推算）
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
_WORKSPACE_FALLBACK = _SCRIPTS_DIR.parent.parent.parent.parent.parent / "workspace"


def get_workspace_dir() -> Path:
    """获取 workspace 目录路径。

    优先级：
    1. AGENT_WORK_ROOT/workspace/
    2. 从当前文件路径向上推算（.parent * 5 / workspace）
    """
    agent_work_root = os.environ.get("AGENT_WORK_ROOT")
    if agent_work_root:
        workspace = Path(agent_work_root) / "workspace"
        if workspace.is_dir():
            return workspace

    if _WORKSPACE_FALLBACK.is_dir():
        return _WORKSPACE_FALLBACK

    raise EnvironmentError(
        "无法确定 workspace 目录：AGENT_WORK_ROOT 未设置且 fallback 路径不存在"
    )


def get_workspace_bin_dir() -> Path:
    """获取 workspace/.bin 目录路径。"""
    return get_workspace_dir() / ".bin"


def get_log_dir(subdir: str = "") -> Path:
    """获取日志目录路径（位于 workspace/.bin 下）。

    Args:
        subdir: 子目录名（可选），如 "cdp-runtime"、"workflows"

    Returns:
        日志目录 Path，已确保目录存在
    """
    try:
        log_dir = get_workspace_bin_dir() / subdir if subdir else get_workspace_bin_dir()
    except EnvironmentError:
        log_dir = Path("/tmp") / subdir if subdir else Path("/tmp")

    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir
