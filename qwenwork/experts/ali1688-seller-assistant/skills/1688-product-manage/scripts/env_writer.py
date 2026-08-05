"""
.env 文件原子读写器
保留非 OAUTH_1688_ 前缀的变量，仅更新 Token 相关变量
"""
from __future__ import annotations

import logging
import os
import sys
import tempfile
from collections import OrderedDict
from pathlib import Path

logger = logging.getLogger(__name__)


def _set_file_permissions(path: str) -> None:
    """设置文件权限为仅所有者可读写（跨平台）。"""
    if sys.platform == "win32":
        try:
            import subprocess
            username = os.environ.get("USERNAME", "")
            if username:
                subprocess.run(
                    ["icacls", path, "/inheritance:r", "/grant:r", f"{username}:F"],
                    check=True,
                    capture_output=True,
                )
        except Exception as e:
            logger.debug("Windows 文件权限设置失败（非致命）: %s", e)
    else:
        os.chmod(path, 0o600)


def read_env(env_path: Path) -> OrderedDict[str, str]:
    """读取 .env 文件为有序字典，忽略注释和空行"""
    result: OrderedDict[str, str] = OrderedDict()
    if not env_path.exists():
        return result
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        result[key.strip()] = value.strip()
    return result


def write_env(env_path: Path, updates: dict[str, str]) -> None:
    """
    原子更新 .env 文件中的指定 key。
    保留文件中不在 updates 中的变量不变。

    Args:
        env_path: .env 文件路径
        updates: 要写入/更新的 key-value 字典
    """
    existing = read_env(env_path)
    existing.update(updates)

    # 构建文件内容
    lines = ["# 1688 OAuth Token (由 authorize.py 自动维护，请勿手动修改)"]
    for key, value in existing.items():
        lines.append(f"{key}={value}")
    content = "\n".join(lines) + "\n"

    # 原子写入：临时文件 + os.replace
    env_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=str(env_path.parent),
        prefix=".env_",
        suffix=".tmp",
    )
    try:
        os.write(fd, content.encode("utf-8"))
        os.close(fd)
        _set_file_permissions(tmp_path)
        try:
            os.replace(tmp_path, str(env_path))
        except PermissionError:
            if sys.platform == "win32":
                try:
                    os.unlink(str(env_path))
                except OSError:
                    pass
                os.replace(tmp_path, str(env_path))
            else:
                raise
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def get_env_value(key: str, env_path: Path | None = None) -> str | None:
    """
    获取环境变量值。
    优先从 os.environ 读取，其次从 .env 文件解析。
    """
    value = os.environ.get(key)
    if value:
        return value
    if env_path and env_path.exists():
        env_data = read_env(env_path)
        return env_data.get(key)
    return None
