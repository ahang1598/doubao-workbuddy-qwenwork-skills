"""
Token 安全存储层

存储策略（自动检测，无需用户干预）：
  1. 优先使用 OS Keychain（安全模式）
  2. Keychain 不可用时降级到文件存储（沙箱环境）
"""
from __future__ import annotations

import logging
import os

from _const import KEYCHAIN_SERVICE

logger = logging.getLogger(__name__)

try:
    import keyring
    import keyring.errors
    _KEYRING_INSTALLED = True
except ImportError:
    keyring = None  # type: ignore
    _KEYRING_INSTALLED = False
    logger.debug("keyring 模块未安装，将使用文件存储")


class KeychainError(Exception):
    pass


_KEYCHAIN_AVAILABLE: bool | None = None
_KEYCHAIN_DISABLED_ENV = "OAUTH_1688_DISABLE_KEYCHAIN"


def _check_keychain_available() -> bool:
    if not _KEYRING_INSTALLED:
        return False

    if os.environ.get(_KEYCHAIN_DISABLED_ENV):
        logger.debug("Keychain 已被环境变量禁用")
        return False

    test_service = f"{KEYCHAIN_SERVICE}_probe"
    test_key = "__probe__"
    test_value = "1"

    try:
        keyring.set_password(test_service, test_key, test_value)
        result = keyring.get_password(test_service, test_key)
        try:
            keyring.delete_password(test_service, test_key)
        except Exception:
            pass
        return result == test_value
    except keyring.errors.KeyringError as e:
        logger.info("Keychain 不可用（%s），将使用文件存储", e)
        return False
    except Exception as e:
        logger.info("Keychain 检测异常（%s），将使用文件存储", e)
        return False


def is_keychain_available() -> bool:
    global _KEYCHAIN_AVAILABLE
    if _KEYCHAIN_AVAILABLE is None:
        _KEYCHAIN_AVAILABLE = _check_keychain_available()
    return _KEYCHAIN_AVAILABLE


def get_storage_mode() -> str:
    return "keychain" if is_keychain_available() else "file"


def _enc_store():
    from encrypted_store import enc_store_token
    return enc_store_token


def _enc_load():
    from encrypted_store import enc_load_token
    return enc_load_token


def _enc_delete():
    from encrypted_store import enc_delete_token
    return enc_delete_token


def store_token(key: str, value: str) -> None:
    if is_keychain_available():
        try:
            keyring.set_password(KEYCHAIN_SERVICE, key, value)
            logger.debug("Token 已写入 Keychain: key=%s", key)
            return
        except keyring.errors.KeyringError as e:
            error_msg = str(e)
            logger.error("Keychain 写入失败: %s", error_msg)
            if "-67674" in error_msg or "permission" in error_msg.lower():
                raise KeychainError(
                    "macOS Keychain 权限被拒绝。请在系统弹出的对话框中点击「始终允许」。"
                ) from e
            raise KeychainError(f"Keychain 写入失败: {error_msg}") from e

    _enc_store()(key, value)


def load_token_secure(key: str) -> str | None:
    value = os.environ.get(key)
    if value:
        return value

    if is_keychain_available():
        try:
            value = keyring.get_password(KEYCHAIN_SERVICE, key)
            if value:
                return value
        except keyring.errors.KeyringError as e:
            logger.warning("Keychain 读取失败: %s", e)

    return _enc_load()(key)


def delete_token(key: str) -> None:
    if is_keychain_available():
        try:
            keyring.delete_password(KEYCHAIN_SERVICE, key)
            logger.debug("Token 已从 Keychain 删除: key=%s", key)
        except keyring.errors.PasswordDeleteError:
            logger.debug("Keychain 中无此 Token: key=%s", key)
        except keyring.errors.KeyringError as e:
            logger.warning("Keychain 删除失败: %s", e)

    _enc_delete()(key)


def save_metadata(updates: dict[str, str], env_file=None) -> None:
    if is_keychain_available():
        from env_writer import write_env
        from _const import ENV_FILE
        write_env(env_file or ENV_FILE, updates)
    else:
        from encrypted_store import enc_store_token
        for key, value in updates.items():
            enc_store_token(key, value)


def load_metadata(key: str, env_file=None) -> str | None:
    value = os.environ.get(key)
    if value:
        return value

    if is_keychain_available():
        from env_writer import get_env_value
        from _const import ENV_FILE
        return get_env_value(key, env_file or ENV_FILE)
    else:
        from encrypted_store import enc_load_token
        return enc_load_token(key)


def clear_metadata(keys: list[str], env_file=None) -> None:
    if is_keychain_available():
        from env_writer import write_env
        from _const import ENV_FILE
        write_env(env_file or ENV_FILE, {k: "" for k in keys})
    else:
        from encrypted_store import enc_delete_token
        for key in keys:
            enc_delete_token(key)

