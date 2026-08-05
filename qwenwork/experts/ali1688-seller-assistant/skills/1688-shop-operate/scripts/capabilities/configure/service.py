#!/usr/bin/env python3
"""AK 配置服务 — 校验、写入、状态查询"""

import json
import os
import sys
from pathlib import Path
from typing import Tuple

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..')))
from _const import AK_STORE_FILE

SKILL_NAME = "1688-shopkeeper"


def validate_ak(ak: str) -> Tuple[bool, str]:
    """校验明文 AK 格式，返回 (is_valid, error_msg)"""
    if not ak:
        return False, "AK 不能为空"
    if len(ak) < 32:
        return False, f"AK 长度不足（当前 {len(ak)}，需要至少 32 位）"
    allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-=")
    if not all(c in allowed for c in ak):
        return False, "AK 包含非法字符"
    return True, ""


def _encrypt(ak: str) -> str:
    from ak_crypto import encrypt_ak
    return encrypt_ak(ak)


def _decrypt(value: str) -> str:
    from ak_crypto import is_encrypted, decrypt_ak
    if not is_encrypted(value):
        # 兼容旧版明文存储，读取后自动迁移
        return value
    return decrypt_ak(value)


def configure_via_ak_store(ak: str) -> bool:
    """将 AK 加密后存储到 ak_store 文件"""
    try:
        encrypted = _encrypt(ak)
        AK_STORE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(AK_STORE_FILE, "w", encoding="utf-8") as f:
            json.dump({"ak": encrypted}, f, ensure_ascii=False)
        return True
    except Exception:
        return False


def check_existing_config() -> Tuple[bool, str, str]:
    """
    检查是否已有 AK。

    返回：(has_ak, ak_value, source)
    source 可能的值："ak_store", ""
    """
    if AK_STORE_FILE.exists():
        try:
            with open(AK_STORE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            store_ak = data.get("ak", "")
            if store_ak:
                plaintext = _decrypt(store_ak)
                # 旧明文数据读取成功后就地迁移为加密格式
                if plaintext == store_ak:
                    configure_via_ak_store(plaintext)
                return True, plaintext, "ak_store"
        except Exception:
            pass

    return False, "", ""


def remove_ak_via_ak_store() -> bool:
    """从 ak_store 文件中移除 AK"""
    try:
        if AK_STORE_FILE.exists():
            AK_STORE_FILE.unlink()
        return True
    except Exception:
        return False


def configure_ak(ak: str) -> Tuple[bool, str]:
    """
    配置 AK：写入 ak_store 文件。
    统一入口，供 callback_server 和 cmd 调用。

    返回：(success, storage_location)
    storage_location 可能的值："ak_store", ""
    """
    if configure_via_ak_store(ak):
        return True, "ak_store"
    return False, ""


def remove_ak() -> bool:
    """
    移除 AK：删除 ak_store 文件。
    统一入口，供 cmd 调用。
    """
    return remove_ak_via_ak_store()
