#!/usr/bin/env python3
"""
AK 认证模块

AK 来源：只从 AK_STORE_FILE（{workspace}/.1688-AK/.ak_store.json）读取。
不再从 ALI_1688_AK 环境变量或 ~/.openclaw/openclaw.json 读取。
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import time
import uuid
from typing import Optional
from urllib.parse import urlparse, parse_qs, quote

from _const import AK_STORE_FILE, SKILL_VERSION

logger = logging.getLogger(__name__)


def get_ak_from_env() -> tuple[Optional[str], Optional[str]]:
    """兼容旧接口：返回 (ak_id, ak_secret)，AK 不存在时返回 (None, None)"""
    raw = get_ak_raw()
    if not raw:
        return None, None
    return extract_ak_keys(raw)

def get_ak_raw() -> Optional[str]:
    """从 AK_STORE_FILE 读取原始 AK 字符串"""
    if not AK_STORE_FILE.exists():
        return None
    try:
        with open(AK_STORE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("ak") or None
    except Exception:
        return None


def extract_ak_keys(raw_ak: str) -> tuple[Optional[str], Optional[str]]:
    """
    从原始 AK 字符串中提取 AccessKeyID 和 AccessKeySecret。
    AK 格式：base64url 编码后，前 32 位为 Secret，剩余为 ID。
    """
    if not raw_ak:
        return None, None

    try:
        from ak_crypto import is_encrypted, decrypt_ak
        if is_encrypted(raw_ak):
            raw_ak = decrypt_ak(raw_ak)
    except Exception as e:
        logger.warning("AK 解密失败: %s", e)
        return None, None

    try:
        padded = raw_ak + "=" * (-len(raw_ak) % 4)
        decoded = base64.urlsafe_b64decode(padded).decode("utf-8")
        secret = decoded[:32]
        ak_id = decoded[32:]
        if ak_id:
            return ak_id, secret
    except Exception:
        pass

    if len(raw_ak) > 32:
        return raw_ak[32:], raw_ak[:32]

    return None, None


def _get_content_md5(body: str) -> str:
    digest = hashlib.md5(body.encode("utf-8")).digest()
    return base64.b64encode(digest).decode("utf-8")


def _get_canonicalized_resource(uri: str) -> str:
    parsed = urlparse(uri)
    path = parsed.path or "/"
    if not parsed.query:
        return path
    params = parse_qs(parsed.query, keep_blank_values=True)
    sorted_params = sorted(params.items())
    query_parts = []
    for key, values in sorted_params:
        for value in sorted(values):
            query_parts.append(f"{quote(key, safe='')}={quote(value, safe='')}")
    return f"{path}?{'&'.join(query_parts)}"


def build_auth_headers(
    method: str,
    uri: str,
    body: str,
    content_type: str = "application/json",
) -> Optional[dict]:
    """
    构建带 AK 签名的请求头。
    AK 不存在时返回 None。
    """
    raw_ak = get_ak_raw()
    if not raw_ak:
        logger.warning("AK 未配置，请先运行 configure 命令")
        return None

    ak_id, ak_secret = extract_ak_keys(raw_ak)
    if not ak_id or not ak_secret:
        logger.warning("AK 格式无效")
        return None

    timestamp = str(int(time.time()))
    nonce = uuid.uuid4().hex[:8]
    content_md5 = _get_content_md5(body)

    csk_headers = {
        "x-csk-ak": ak_id,
        "x-csk-time": timestamp,
        "x-csk-nonce": nonce,
        "x-csk-content-md5": content_md5,
        "x-csk-version": SKILL_VERSION,
    }

    sorted_keys = sorted(csk_headers.keys())
    canonicalized_headers = "".join(
        f"{key.lower()}:{csk_headers[key].strip()}\n"
        for key in sorted_keys
    )

    string_to_sign = "\n".join([
        method.upper(),
        content_md5,
        content_type,
        timestamp,
    ]) + "\n" + canonicalized_headers + _get_canonicalized_resource(uri)

    signature = hmac.new(
        ak_secret.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    sign_base64 = base64.b64encode(signature).decode("utf-8")

    return {
        "Content-Type": content_type,
        "x-csk-sign": sign_base64,
        **csk_headers,
    }
