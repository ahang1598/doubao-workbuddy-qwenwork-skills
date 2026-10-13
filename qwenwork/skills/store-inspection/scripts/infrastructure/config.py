"""Skill 配置文件读写。

设计原则：
- 仅持久化 ``base_id`` 一个字段到 config.json
- 4 张表的 tableId / 字段的 fieldId 不持久化（详见 mapping_cache.py）
- 同目录另有 ``sync_state.json``，由 :mod:`sync_state` 维护，本模块不参与

存储路径优先级（从高到低）：

1. 显式传入 ``config_path``
2. 环境变量 ``STORE_TASK_DISPATCHER_CONFIG``
3. ``$AGENT_WORK_ROOT/workspace/store-inspection/config.json``
   （由 Agent 宿主环境注入 ``AGENT_WORK_ROOT`` 时使用）
4. ``~/.store-inspection/config.json``
   （通用兜底路径，不绑定任何具体 Agent 宿主）
5. 相对当前工作目录的 :data:`LEGACY_CONFIG_RELPATH`
   （向后兼容旧版路径；仅当家目录路径不存在但旧路径存在时回退）
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

from scripts.domain.exceptions import ConfigError

logger = logging.getLogger(__name__)

# 通用兜底：放在用户家目录，不绑定任何具体 Agent 宿主
DEFAULT_CONFIG_HOME = Path("~/.store-inspection/config.json")

# 旧版兜底路径（向后兼容）：仅当家目录路径不存在、但旧路径已存在时复用，
# 避免已有用户从 ``.aone_copilot/store-inspection/config.json``
# 升级后丢配置。
LEGACY_CONFIG_RELPATH = Path(".aone_copilot/store-inspection/config.json")

# 别名：保持 ``from scripts.infrastructure.config import DEFAULT_CONFIG_RELPATH``
# 等外部 import 兼容（指向旧路径常量，仅用于向后兼容场景）。
DEFAULT_CONFIG_RELPATH = LEGACY_CONFIG_RELPATH

# AGENT_WORK_ROOT 下的优先存储子目录
AGENT_WORKSPACE_SUBDIR = Path("workspace/store-inspection")


def _resolve_config_path(config_path: Optional[Path] = None) -> Path:
    """解析配置文件绝对路径。

    解析顺序（详见模块 docstring）：

    1. 显式传入 ``config_path``
    2. 环境变量 ``STORE_TASK_DISPATCHER_CONFIG``
    3. ``$AGENT_WORK_ROOT/workspace/store-inspection/config.json``
    4. ``~/.store-inspection/config.json``（通用兜底）
    5. 旧版 ``./.aone_copilot/store-inspection/config.json``
       （仅当家目录路径不存在、但旧路径已存在时回退，用于平滑迁移）
    """
    if config_path is not None:
        return Path(config_path).expanduser().resolve()
    env = os.environ.get("STORE_TASK_DISPATCHER_CONFIG")
    if env:
        return Path(env).expanduser().resolve()
    agent_work_root = os.environ.get("AGENT_WORK_ROOT")
    if agent_work_root:
        return (Path(agent_work_root) / AGENT_WORKSPACE_SUBDIR / "config.json").resolve()

    # 通用兜底：用户家目录
    home_path = DEFAULT_CONFIG_HOME.expanduser().resolve()
    # 仅当家目录路径不存在、且旧版路径已存在时，沿用旧路径以兼容老用户
    legacy_path = (Path.cwd() / LEGACY_CONFIG_RELPATH).resolve()
    if not home_path.exists() and legacy_path.exists():
        return legacy_path
    return home_path


def load(config_path: Optional[Path] = None) -> dict:
    """读取配置。文件不存在或为空时返回空 dict。

    Raises:
        ConfigError: 文件存在但 JSON 格式损坏。
    """
    path = _resolve_config_path(config_path)
    if not path.exists():
        return {}
    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise ConfigError(f"读取配置失败 {path}: {exc}") from exc
    if not text:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"配置文件 JSON 损坏 {path}: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"配置文件根对象必须是 JSON object，实际是 {type(data).__name__}")
    return data


def save(
    base_id: str,
    config_path: Optional[Path] = None,
    *,
    corp_id: Optional[str] = None,
) -> Path:
    """覆写配置，持久化 ``base_id`` 及可选的 ``corp_id``。

    Args:
        base_id: AI 表格 Base ID（必填）。
        config_path: 显式配置路径，为 ``None`` 时按优先级自动解析。
        corp_id: 组织 corpId，首次初始化时通过
            ``dws contact user get-self`` 获取后持久化，后续无需重复查询。
    """
    if not base_id or not isinstance(base_id, str):
        raise ConfigError("base_id 必须是非空字符串")
    path = _resolve_config_path(config_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # 保留已有配置（如 dws_bin_path），只覆盖 base_id 和 corp_id
    existing = load(config_path) if path.exists() else {}
    payload = {**existing, "base_id": base_id}
    if corp_id:
        payload["corp_id"] = corp_id
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.debug("config.json saved at %s", path)
    return path


def get_base_id(config_path: Optional[Path] = None) -> Optional[str]:
    """便捷方法：直接拿 base_id，未配置返回 ``None``。"""
    data = load(config_path)
    base_id = data.get("base_id")
    if base_id and isinstance(base_id, str):
        return base_id
    return None


def get_corp_id(config_path: Optional[Path] = None) -> Optional[str]:
    """便捷方法：直接拿 corp_id，未配置返回 ``None``。"""
    data = load(config_path)
    corp_id = data.get("corp_id")
    if corp_id and isinstance(corp_id, str):
        return corp_id
    return None


def get_dws_bin_path(config_path: Optional[Path] = None) -> Optional[str]:
    """便捷方法：读取本地配置的 dws 可执行文件路径，未配置返回 ``None``。

    本地开发时可在 config.json 中写入::

        { "dws_bin_path": "~/.qoderwork/bin/dws" }

    其他环境不配置此项，``DwsClient`` 将直接使用 ``dws`` 命令。
    """
    data = load(config_path)
    dws_bin_path = data.get("dws_bin_path")
    if dws_bin_path and isinstance(dws_bin_path, str):
        return str(Path(dws_bin_path).expanduser())
    return None

def remove_base_id(config_path: Optional[Path] = None) -> None:
    """仅移除配置中的 base_id 字段，保留其余配置（如 dws_bin_path）。"""
    path = _resolve_config_path(config_path)
    if not path.exists():
        return
    data = load(config_path)
    data.pop("base_id", None)
    data.pop("corp_id", None)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.debug("base_id removed from config.json at %s", path)


def reset(config_path: Optional[Path] = None) -> None:
    """删除配置文件（不会删除 AI表格 本身）。"""
    path = _resolve_config_path(config_path)
    if path.exists():
        path.unlink()
        logger.debug("config.json removed at %s", path)


__all__ = [
    "DEFAULT_CONFIG_HOME",
    "DEFAULT_CONFIG_RELPATH",
    "LEGACY_CONFIG_RELPATH",
    "load",
    "save",
    "get_dws_bin_path",
    "get_base_id",
    "get_corp_id",
    "remove_base_id",
    "reset",
]
