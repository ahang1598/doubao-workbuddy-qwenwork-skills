"""
PKCE (Proof Key for Code Exchange) 工具
遵循 RFC 7636，仅支持 S256 方法（OAuth 2.1 强制要求）
"""
from __future__ import annotations

import base64
import hashlib
import secrets


def generate_pair() -> tuple[str, str]:
    """
    生成 PKCE code_verifier 和 code_challenge 对。

    Returns:
        (code_verifier, code_challenge)
    """
    # RFC 7636: 43-128 字符。64 字节 → base64url 编码后 86 字符
    random_bytes = secrets.token_bytes(64)
    code_verifier = base64.urlsafe_b64encode(random_bytes).rstrip(b"=").decode("ascii")

    # S256: code_challenge = BASE64URL(SHA256(ASCII(code_verifier)))
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")

    return code_verifier, code_challenge
