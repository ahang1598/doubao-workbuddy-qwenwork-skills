"""
文件存储后端

当 OS Keychain 不可用时（如沙箱环境），将 Token 和元数据
存储在本地 JSON 文件中。

文件权限设置为 0o600（仅文件所有者可读写）。
"""
from __future__ import annotations

import json
import logging
import os
import sys
import tempfile
from pathlib import Path

from _const import DATA_DIR

logger = logging.getLogger(__name__)

ENCRYPTED_TOKEN_FILE = DATA_DIR / ".token_store.json"


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


def _load_store() -> dict[str, str]:
    if not ENCRYPTED_TOKEN_FILE.exists():
        return {}
    try:
        raw = ENCRYPTED_TOKEN_FILE.read_text(encoding="utf-8")
        return json.loads(raw)
    except (json.JSONDecodeError, Exception) as e:
        logger.warning("存储文件读取失败: %s，将重建", e)
        return {}


def _save_store(data: dict[str, str]) -> None:
    json_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    ENCRYPTED_TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=str(ENCRYPTED_TOKEN_FILE.parent),
        prefix=".token_",
        suffix=".tmp",
    )
    try:
        os.write(fd, json_bytes)
        os.close(fd)
        _set_file_permissions(tmp_path)
        try:
            os.replace(tmp_path, str(ENCRYPTED_TOKEN_FILE))
        except PermissionError:
            if sys.platform == "win32":
                # Windows 下目标文件可能被其他进程持有，先删除再替换
                try:
                    os.unlink(str(ENCRYPTED_TOKEN_FILE))
                except OSError:
                    pass
                os.replace(tmp_path, str(ENCRYPTED_TOKEN_FILE))
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


def enc_store_token(key: str, value: str) -> None:
    store = _load_store()
    store[key] = value
    _save_store(store)
    logger.debug("Token 已写入文件存储: key=%s", key)


def enc_load_token(key: str) -> str | None:
    store = _load_store()
    return store.get(key) or None


def enc_delete_token(key: str) -> None:
    store = _load_store()
    if key in store:
        del store[key]
        _save_store(store)
        logger.debug("Token 已从文件存储删除: key=%s", key)
    else:
        logger.debug("文件存储中无此 Token，跳过删除: key=%s", key)
