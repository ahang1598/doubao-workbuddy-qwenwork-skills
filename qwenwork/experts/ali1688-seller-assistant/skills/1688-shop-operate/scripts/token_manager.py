"""
Token 生命周期管理

职责：从安全存储读取 Token、检查有效性、静默刷新、吊销、清除。
"""
from __future__ import annotations

import json
import logging
import ssl
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from _const import (
    TOKEN_ENDPOINT,
    REFRESH_TOKEN_ENDPOINT,
    REVOKE_ENDPOINT,
    CLIENT_ID,
    HTTP_TIMEOUT,
    TOKEN_REFRESH_MARGIN,
    ENV_FILE,
    ENV_ACCESS_TOKEN,
    ENV_REFRESH_TOKEN,
    ENV_TOKEN_SCOPE,
    ENV_TOKEN_EXPIRES_AT,
    ENV_REFRESH_TOKEN_EXPIRES_AT,
    ENV_CLIENT_ID,
    ENV_REDIRECT_URI,
)
from _auth import build_auth_headers
from secure_store import (
    store_token as _store_token,
    load_token_secure,
    delete_token as _delete_token,
    save_metadata as _save_metadata,
    load_metadata as _load_metadata,
    clear_metadata as _clear_metadata,
)

logger = logging.getLogger(__name__)


def load_token(env_file: Path = ENV_FILE) -> dict | None:
    """
    从安全存储加载 Token 信息。

    Returns:
        dict 含 access_token / refresh_token / scope / expires_at / expired / expiring_soon 等
        或 None（无 Token）
    """
    access_token = load_token_secure(ENV_ACCESS_TOKEN)
    if not access_token:
        return None

    refresh_token = load_token_secure(ENV_REFRESH_TOKEN)
    scope = _load_metadata(ENV_TOKEN_SCOPE, env_file) or ""
    expires_at_str = _load_metadata(ENV_TOKEN_EXPIRES_AT, env_file) or "0"
    refresh_expires_at_str = _load_metadata(ENV_REFRESH_TOKEN_EXPIRES_AT, env_file) or "0"

    try:
        expires_at = int(expires_at_str)
    except ValueError:
        expires_at = 0

    try:
        refresh_expires_at = int(refresh_expires_at_str)
    except ValueError:
        refresh_expires_at = 0

    now = int(time.time())
    expires_in = max(0, expires_at - now)
    expired = now >= expires_at
    expiring_soon = now >= (expires_at - TOKEN_REFRESH_MARGIN)
    refresh_expired = refresh_expires_at > 0 and now >= refresh_expires_at

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "scope": scope,
        "expires_at": expires_at,
        "expires_in": expires_in,
        "expired": expired,
        "expiring_soon": expiring_soon,
        "refresh_expires_at": refresh_expires_at,
        "refresh_expired": refresh_expired,
    }


def has_scope(current_scope: str, required_scope: str) -> bool:
    current = set(current_scope.split()) if current_scope else set()
    required = set(required_scope.split()) if required_scope else set()
    return required.issubset(current)


def get_merged_scope(current_scope: str, required_scope: str) -> str:
    current = set(current_scope.split()) if current_scope else set()
    required = set(required_scope.split()) if required_scope else set()
    return " ".join(sorted(current | required))


def refresh_token(env_file: Path = ENV_FILE) -> dict:
    """用 Refresh Token 刷新 Access Token。"""
    token = load_token(env_file)
    if not token or not token["refresh_token"]:
        return {"success": False, "error": "NO_REFRESH_TOKEN",
                "error_description": "无可用的 Refresh Token"}

    client_id = _load_metadata(ENV_CLIENT_ID, env_file) or CLIENT_ID
    redirect_uri = _load_metadata(ENV_REDIRECT_URI, env_file) or ""

    request_body = {
        "clientId": client_id,
        "scope": None,
        "redirectUri": redirect_uri,
        "refreshToken": token["refresh_token"],
    }
    body_str = json.dumps(request_body)

    from urllib.parse import urlparse as _urlparse
    endpoint_path = _urlparse(REFRESH_TOKEN_ENDPOINT).path

    auth_headers = build_auth_headers("POST", endpoint_path, body_str)
    if auth_headers is None:
        logger.warning("AK 未配置，将以无签名方式发送 Refresh Token 请求")
        auth_headers = {"Content-Type": "application/json"}

    req = Request(REFRESH_TOKEN_ENDPOINT, data=body_str.encode("utf-8"),
                  headers=auth_headers, method="POST")

    try:
        ctx = ssl.create_default_context()
        with urlopen(req, timeout=HTTP_TIMEOUT, context=ctx) as resp:
            raw_body = json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        error_body = {}
        try:
            error_body = json.loads(e.read().decode("utf-8"))
        except Exception:
            pass
        return {
            "success": False,
            "error": error_body.get("errorCode", f"HTTP_{e.code}"),
            "error_description": error_body.get("errorDescription", f"刷新失败: HTTP {e.code}"),
        }
    except URLError as e:
        return {"success": False, "error": "NETWORK_ERROR",
                "error_description": f"网络错误: {e.reason}"}

    if not raw_body.get("success"):
        error_response = raw_body.get("data", {}).get("response", {})
        error_code = (error_response.get("error") or raw_body.get("code")
                      or raw_body.get("msgCode") or "TOKEN_REFRESH_FAILED")
        error_msg = (error_response.get("errorDescription") or raw_body.get("message")
                     or raw_body.get("msgInfo") or "Token 刷新失败")
        return {"success": False, "error": error_code, "error_description": error_msg}

    token_response = raw_body.get("data", {}).get("response", {})
    new_access = token_response.get("accessToken", "")
    new_refresh = token_response.get("refreshToken", token["refresh_token"])
    new_scope = token_response.get("scope", token["scope"])
    new_expires_in = token_response.get("expiresIn", 0)
    new_expires_at = int(time.time()) + new_expires_in
    new_refresh_expire_in = token_response.get("refreshExpireIn", 0)
    new_refresh_expires_at = int(time.time()) + new_refresh_expire_in if new_refresh_expire_in else 0

    _store_token(ENV_ACCESS_TOKEN, new_access)
    _store_token(ENV_REFRESH_TOKEN, new_refresh)
    _save_metadata({
        ENV_TOKEN_SCOPE: new_scope,
        ENV_TOKEN_EXPIRES_AT: str(new_expires_at),
        ENV_REFRESH_TOKEN_EXPIRES_AT: str(new_refresh_expires_at) if new_refresh_expires_at else "",
    }, env_file)

    logger.info("Token 刷新成功，新 expires_in=%d", new_expires_in)
    return {"success": True, "scope": new_scope, "expires_in": new_expires_in}


def _revoke_single_token(token_value: str, token_type_hint: str,
                         env_file: Path = ENV_FILE) -> dict:
    client_id = _load_metadata(ENV_CLIENT_ID, env_file) or CLIENT_ID

    request_body = {
        "clientId": client_id,
        "tokenTypeHint": token_type_hint,
        "token": token_value,
    }
    body_str = json.dumps(request_body)

    from urllib.parse import urlparse as _urlparse
    endpoint_path = _urlparse(REVOKE_ENDPOINT).path

    auth_headers = build_auth_headers("POST", endpoint_path, body_str)
    if auth_headers is None:
        logger.warning("AK 未配置，将以无签名方式发送 Revoke 请求")
        auth_headers = {"Content-Type": "application/json"}

    req = Request(REVOKE_ENDPOINT, data=body_str.encode("utf-8"),
                  headers=auth_headers, method="POST")

    try:
        ctx = ssl.create_default_context()
        with urlopen(req, timeout=HTTP_TIMEOUT, context=ctx) as resp:
            resp.read()
        return {"success": True}
    except HTTPError as e:
        error_body = ""
        try:
            error_body = e.read().decode("utf-8")
        except Exception:
            pass
        return {"success": False, "error": f"HTTP {e.code}: {error_body}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def revoke_access(env_file: Path = ENV_FILE) -> dict:
    token = load_token(env_file)
    if not token or not token["access_token"]:
        return {"success": True, "skipped": True}
    return _revoke_single_token(token["access_token"], "access_token", env_file)


def revoke_refresh(env_file: Path = ENV_FILE) -> dict:
    token = load_token(env_file)
    if not token or not token["refresh_token"]:
        return {"success": True, "skipped": True}
    return _revoke_single_token(token["refresh_token"], "refresh_token", env_file)


def clear_token(env_file: Path = ENV_FILE) -> None:
    _delete_token(ENV_ACCESS_TOKEN)
    _delete_token(ENV_REFRESH_TOKEN)
    _clear_metadata([ENV_TOKEN_SCOPE, ENV_TOKEN_EXPIRES_AT, ENV_REFRESH_TOKEN_EXPIRES_AT], env_file)
    logger.info("本地 Token 已清除")


def ensure_valid_token(required_scope: str = "", env_file: Path = ENV_FILE) -> dict:
    """
    确保有一个有效的 Token 可用。

    Returns:
        {"valid": True, "access_token": str, "scope": str, "expires_in": int}
        或 {"valid": False, "error_code": str, "message": str, ...}
    """
    token = load_token(env_file)

    if not token:
        return {"valid": False, "error_code": "AUTH_MISSING", "message": "需要授权才能继续操作"}

    if token["expired"]:
        if token["refresh_token"]:
            result = refresh_token(env_file)
            if result["success"]:
                token = load_token(env_file)
            else:
                error = result["error"]
                if error in ("TOKEN_REVOKED", "INVALID_GRANT"):
                    return {"valid": False, "error_code": "AUTH_REVOKED",
                            "message": "授权已被撤销，需要重新授权"}
                return {"valid": False, "error_code": "AUTH_EXPIRED",
                        "message": "Token 已过期且刷新失败"}
        else:
            return {"valid": False, "error_code": "AUTH_EXPIRED", "message": "Token 已过期"}

    if token["expiring_soon"] and token["refresh_token"]:
        refresh_token(env_file)
        token = load_token(env_file)

    if required_scope and not has_scope(token["scope"], required_scope):
        return {
            "valid": False,
            "error_code": "AUTH_INSUFFICIENT_SCOPE",
            "required_scope": get_merged_scope(token["scope"], required_scope),
            "current_scope": token["scope"],
            "message": f"权限不足，需要 scope: {required_scope}",
        }

    return {
        "valid": True,
        "access_token": token["access_token"],
        "scope": token["scope"],
        "expires_in": token["expires_in"],
    }
