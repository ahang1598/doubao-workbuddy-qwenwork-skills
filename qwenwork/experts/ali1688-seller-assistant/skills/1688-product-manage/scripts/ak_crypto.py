"""
AK 本地对称加密

方案（仅使用 Python 标准库）：
  密钥派生  PBKDF2-HMAC-SHA256(machine_id, kdf_salt, 100_000 iterations) → 32 字节
  流加密    SHA-256 计数器模式（CTR 等价）：keystream = SHA256(key‖nonce‖i) 循环 XOR
  完整性    Encrypt-then-MAC：HMAC-SHA256(key, kdf_salt‖nonce‖ciphertext)

存储格式：  "v1:" + base64( kdf_salt[16] ‖ nonce[16] ‖ mac[32] ‖ ciphertext )

机器 ID 获取顺序：
  Windows → HKLM\\SOFTWARE\\Microsoft\\Cryptography\\MachineGuid
  macOS   → ioreg IOPlatformUUID
  Linux   → /etc/machine-id | /var/lib/dbus/machine-id
  fallback → DATA_DIR/.device_id（首次随机生成并持久化）
"""
from __future__ import annotations

import base64
import hashlib
import hmac as _hmac
import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

_KDF_ITERATIONS = 100_000
_PREFIX = "v1:"
_SALT_LEN = 16
_NONCE_LEN = 16
_MAC_LEN = 32   # HMAC-SHA256


# ── 机器 ID ───────────────────────────────────────────────────────────────────

def _get_machine_id() -> str:
    if sys.platform == "win32":
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Cryptography",
            )
            guid, _ = winreg.QueryValueEx(key, "MachineGuid")
            winreg.CloseKey(key)
            logger.debug("Windows: 使用注册表 MachineGuid 作为设备 ID")
            return guid
        except Exception as e:
            logger.debug("Windows MachineGuid 读取失败: %s", e)

    elif sys.platform == "darwin":
        try:
            import subprocess
            result = subprocess.run(
                ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
                capture_output=True, text=True,
            )
            for line in result.stdout.splitlines():
                if "IOPlatformUUID" in line:
                    uuid = line.split('"')[-2]
                    logger.debug("macOS: 使用 IOPlatformUUID 作为设备 ID")
                    return uuid
        except Exception as e:
            logger.debug("macOS IOPlatformUUID 读取失败: %s", e)

    else:
        for path in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
            try:
                mid = Path(path).read_text().strip()
                if mid:
                    logger.debug("Linux: 使用 %s 作为设备 ID", path)
                    return mid
            except Exception:
                pass

    return _get_or_create_fallback_id()


def _get_or_create_fallback_id() -> str:
    from _const import DATA_DIR
    fallback_file = DATA_DIR / ".device_id"
    try:
        if fallback_file.exists():
            mid = fallback_file.read_text().strip()
            if mid:
                logger.debug("使用本地持久化设备 ID（fallback）")
                return mid
    except Exception:
        pass

    import secrets
    mid = secrets.token_hex(16)
    try:
        fallback_file.parent.mkdir(parents=True, exist_ok=True)
        fallback_file.write_text(mid)
        logger.debug("已生成并持久化新设备 ID（fallback）")
    except Exception as e:
        logger.warning("设备 ID 持久化失败，本次使用内存值: %s", e)
    return mid


# ── 密钥派生 ──────────────────────────────────────────────────────────────────

def derive_key(machine_id: str, kdf_salt: bytes) -> bytes:
    """PBKDF2-HMAC-SHA256 派生 32 字节 AES 等价密钥。"""
    return hashlib.pbkdf2_hmac(
        "sha256",
        machine_id.encode("utf-8"),
        kdf_salt,
        _KDF_ITERATIONS,
        dklen=32,
    )


# ── 流加密（SHA-256 CTR）────────────────────────────────────────────────────

def _keystream(key: bytes, nonce: bytes, length: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    counter = 0
    while total < length:
        block = hashlib.sha256(key + nonce + counter.to_bytes(4, "big")).digest()
        chunks.append(block)
        total += len(block)
        counter += 1
    return b"".join(chunks)[:length]


def _xor(data: bytes, stream: bytes) -> bytes:
    return bytes(a ^ b for a, b in zip(data, stream))


# ── 公开接口 ──────────────────────────────────────────────────────────────────

def encrypt_ak(plaintext: str, machine_id: str | None = None) -> str:
    """加密 AK，返回 'v1:<base64>' 格式字符串。"""
    mid = machine_id or _get_machine_id()
    kdf_salt = os.urandom(_SALT_LEN)
    nonce = os.urandom(_NONCE_LEN)
    key = derive_key(mid, kdf_salt)

    raw = plaintext.encode("utf-8")
    ciphertext = _xor(raw, _keystream(key, nonce, len(raw)))
    mac = _hmac.new(key, kdf_salt + nonce + ciphertext, hashlib.sha256).digest()

    blob = base64.b64encode(kdf_salt + nonce + mac + ciphertext).decode("ascii")
    return _PREFIX + blob


def decrypt_ak(token: str, machine_id: str | None = None) -> str:
    """解密 'v1:<base64>' 格式 AK，HMAC 校验失败时抛 ValueError。"""
    if not token.startswith(_PREFIX):
        raise ValueError("不是有效的加密格式（缺少版本前缀）")

    mid = machine_id or _get_machine_id()
    data = base64.b64decode(token[len(_PREFIX):])

    kdf_salt = data[:_SALT_LEN]
    nonce = data[_SALT_LEN:_SALT_LEN + _NONCE_LEN]
    mac = data[_SALT_LEN + _NONCE_LEN:_SALT_LEN + _NONCE_LEN + _MAC_LEN]
    ciphertext = data[_SALT_LEN + _NONCE_LEN + _MAC_LEN:]

    key = derive_key(mid, kdf_salt)
    expected_mac = _hmac.new(key, kdf_salt + nonce + ciphertext, hashlib.sha256).digest()
    if not _hmac.compare_digest(mac, expected_mac):
        raise ValueError("AK 完整性校验失败（HMAC 不匹配），数据可能已损坏或来自其他机器")

    return _xor(ciphertext, _keystream(key, nonce, len(ciphertext))).decode("utf-8")


def is_encrypted(value: str) -> bool:
    return value.startswith(_PREFIX)
