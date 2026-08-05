"""
Scope 权限列表管理

职责：从服务端查询所有可用 scope，本地文件缓存（24h TTL）。
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
    SCOPE_LIST_ENDPOINT,
    SCOPE_CACHE_FILE,
    SCOPE_CACHE_TTL,
    HTTP_TIMEOUT,
)
from _auth import build_auth_headers

logger = logging.getLogger(__name__)


def _fetch_from_api() -> list[dict]:
    body_str = json.dumps({})

    from urllib.parse import urlparse as _urlparse
    endpoint_path = _urlparse(SCOPE_LIST_ENDPOINT).path

    auth_headers = build_auth_headers("POST", endpoint_path, body_str)
    if auth_headers is None:
        logger.warning("AK 未配置，将以无签名方式发送 Scope 查询请求")
        auth_headers = {"Content-Type": "application/json"}

    req = Request(SCOPE_LIST_ENDPOINT, data=body_str.encode("utf-8"),
                  headers=auth_headers, method="POST")

    ctx = ssl.create_default_context()
    with urlopen(req, timeout=HTTP_TIMEOUT, context=ctx) as resp:
        raw_body = json.loads(resp.read().decode("utf-8"))

    if not raw_body.get("success"):
        raise RuntimeError(raw_body.get("message") or raw_body.get("msgInfo")
                           or "服务端返回 success=false")

    scopes = raw_body.get("data", {}).get("response", [])
    if not isinstance(scopes, list):
        raise RuntimeError("响应格式异常：data.response 不是数组")
    return scopes


def _load_cache(cache_file: Path = SCOPE_CACHE_FILE) -> tuple[list[dict] | None, bool]:
    if not cache_file.exists():
        return None, False
    try:
        data = json.loads(cache_file.read_text(encoding="utf-8"))
        cached_at = data.get("cached_at", 0)
        scopes = data.get("scopes", [])
        if not isinstance(scopes, list) or not scopes:
            return None, False
        fresh = (time.time() - cached_at) < SCOPE_CACHE_TTL
        return scopes, fresh
    except Exception as e:
        logger.warning("读取 scope 缓存失败: %s", e)
        return None, False


def _save_cache(scopes: list[dict], cache_file: Path = SCOPE_CACHE_FILE) -> None:
    try:
        cache_data = {"cached_at": int(time.time()), "scopes": scopes}
        cache_file.write_text(json.dumps(cache_data, ensure_ascii=False, indent=2),
                              encoding="utf-8")
    except Exception as e:
        logger.warning("写入 scope 缓存失败: %s", e)


def query_all_scope(cache_file: Path = SCOPE_CACHE_FILE) -> dict:
    """
    查询所有可用 scope（带缓存）。

    Returns:
        成功: {"success": True, "scopes": [...], "from_cache": bool}
        失败: {"success": False, "error": str, "error_description": str}
    """
    cached, fresh = _load_cache(cache_file)
    if cached and fresh:
        return {"success": True, "scopes": cached, "from_cache": True}

    try:
        scopes = _fetch_from_api()
        _save_cache(scopes, cache_file)
        return {"success": True, "scopes": scopes, "from_cache": False}
    except HTTPError as e:
        error_body = ""
        try:
            error_body = e.read().decode("utf-8")
        except Exception:
            pass
        error_msg = f"HTTP {e.code}: {error_body}" if error_body else f"HTTP {e.code}"
        logger.warning("查询 scope 列表失败: %s", error_msg)
    except URLError as e:
        error_msg = f"网络错误: {e.reason}"
        logger.warning("查询 scope 列表失败: %s", error_msg)
    except Exception as e:
        error_msg = str(e)
        logger.warning("查询 scope 列表失败: %s", error_msg)

    if cached:
        return {"success": True, "scopes": cached, "from_cache": True, "stale": True}

    return {"success": False, "error": "SCOPE_QUERY_FAILED", "error_description": error_msg}


def format_scope_list_markdown(scopes: list[dict]) -> str:
    risk_order = {"低": 0, "中": 1, "高": 2}
    risk_labels = {"低": "低风险权限", "中": "中风险权限", "高": "高风险权限"}

    groups: dict[str, list[dict]] = {}
    for s in scopes:
        level = s.get("riskLevel", "低")
        groups.setdefault(level, []).append(s)

    parts = []
    for level in sorted(groups.keys(), key=lambda x: risk_order.get(x, 99)):
        label = risk_labels.get(level, f"{level}风险权限")
        parts.append(f"**{label}**\n")
        parts.append("| 权限说明 | 标识符 | 风险等级 |")
        parts.append("|----------|--------|----------|")
        for s in groups[level]:
            desc = s.get("description", s.get("scope", ""))
            scope_id = s.get("scope", "")
            parts.append(f"| {desc} | `{scope_id}` | {level} |")
        parts.append("")

    return "\n".join(parts)
