#!/usr/bin/env python3
"""
全局常量定义
"""
import os
from pathlib import Path


# ── Skill 名称与版本 ──────────────────────────────────────────────────────────
SKILL_NAME = "1688-product-manage"
SKILL_VERSION = "0.1.0"

# ── Skill 根目录 ──────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

# ── Workspace 目录自动发现 ────────────────────────────────────────────────────
def _find_workspace_dir() -> Path:
    """
    查找 workspace 目录。

    查找顺序：
    1. 环境变量 AGENT_WORK_ROOT + /workspace
    2. 从当前目录向上查找名为 workspace 的目录
    3. 从当前目录向上，查找各层级下的 workspace 子目录
    4. 从当前目录向上查找 .skills 目录，其兄弟目录 workspace
    5. fallback 到当前目录
    """
    agent_work_root = os.environ.get("AGENT_WORK_ROOT")
    if agent_work_root:
        workspace_dir = Path(agent_work_root) / "workspace"
        return workspace_dir  # 不存在时后续会自动创建

    cwd = Path.cwd().resolve()

    # 2. 从当前目录向上查找名为 workspace 的目录
    for parent in [cwd] + list(cwd.parents):
        if parent.name == "workspace":
            return parent

    # 3. 从当前目录向上，检查各层级下是否存在 workspace 子目录
    for parent in [cwd] + list(cwd.parents):
        workspace_dir = parent / "workspace"
        if workspace_dir.exists() and workspace_dir.is_dir():
            return workspace_dir

    # 4. 查找 .skills 的兄弟目录 workspace
    for parent in cwd.parents:
        skills_dir = parent / ".skills"
        if skills_dir.exists() and skills_dir.is_dir():
            workspace_dir = parent / "workspace"
            return workspace_dir

    return cwd


WORKSPACE_DIR = _find_workspace_dir()

# ── AK 本地存储目录 ────────────────────────────────────────────────────────────
AK_DATA_DIR = WORKSPACE_DIR / ".1688-AK"
AK_STORE_FILE = AK_DATA_DIR / ".ak_store.json"

# ── API 网关 ──────────────────────────────────────────────────────────────────
BASE_URL = "https://skills-gateway.1688.com"
# BASE_URL = "https://pre-1688gateway.alibaba-inc.com"
# ── 超时与重试 ────────────────────────────────────────────────────────────────
HTTP_TIMEOUT = 30
RETRY_MAX = 3
RETRY_DELAY_BASE = 1

# ── 网关 Token 相关错误码（Agent 可自动恢复）───────────────────────────────────
_GATEWAY_AUTH_ERROR_CODES = {
    "1688_token_expired",
    "1688_invalid_token",
    "1688_token_missing",
    "1688_scope_insufficient",
}

# ── 授权端点 ────────────────────────────────────────────────────────────
AUTHORIZE_ENDPOINT = "https://air.1688.com/app/tai/oauth_page/index.html"
AUTHORIZATION_TIMEOUT = 300

# ── 授权模式标识 ────────────────────────────────────────────────────────
AUTH_MODE_OAUTH = "oauth"
AUTH_MODE_AK = "AKLocal"

# ── 运行时数据目录（Token 存储、缓存等）──────────────────────────────────────
DATA_DIR = AK_DATA_DIR.parent / ".1688-oauth"

# ── 统一日志文件路径 ──────────────────────────────────────────────────────────
LOG_FILE = DATA_DIR / "skill.log"

# ── OAuth 客户端配置（预留，AK 模式暂不需要）──────────────────────────────────
CLIENT_ID = os.environ.get("OAUTH_1688_CLIENT_ID", "3767346c-f079-4d16-8049-8ede627a480e")

# ── OAuth 服务端端点（预留，AK 模式暂不需要）────────────────────────────────────
# 用 authorization_code 换取 Token 的网关端点
TOKEN_ENDPOINT = "https://skills-gateway.1688.com/api/get_token_by_auth_code/1.0.0"
# 用 Refresh Token 换取新 Token 的网关端点
REFRESH_TOKEN_ENDPOINT = "https://skills-gateway.1688.com/api/refresh_token/1.0.0"
# Revoke 端点（吊销 Access Token / Refresh Token）
REVOKE_ENDPOINT = "https://skills-gateway.1688.com/api/revoke_token/1.0.0"
# Scope 列表查询端点
SCOPE_LIST_ENDPOINT = "https://skills-gateway.1688.com/api/query_all_scope/1.0.0"

# ── 回调服务器 ────────────────────────────────────────────────────────────────
import sys as _sys
# Windows 上 localhost 可能解析为 ::1（IPv6），固定用 127.0.0.1 避免 DNS 歧义，
# 同时确保 redirect_uri 与服务端绑定地址严格一致。
CALLBACK_HOST = "127.0.0.1" if _sys.platform == "win32" else "localhost"
# Windows 防火墙对绑定 0.0.0.0 的进程会拦截入向连接（即使是 localhost 流量）；
# 绑定 127.0.0.1 明确标识为 loopback，防火墙不干预。
CALLBACK_BIND_ADDRESS = "127.0.0.1" if _sys.platform == "win32" else "0.0.0.0"
CALLBACK_PORT_START = 8080
CALLBACK_PORT_RETRIES = 10

# ── 超时配置 ────────────────────────────────────────────────────────────
TOKEN_REFRESH_MARGIN = 60
SCOPE_CACHE_TTL = 86400

# ── .env 文件（OAuth Token 存储，预留）─────────────────────────────────────────
ENV_FILE = DATA_DIR / ".env"

# ── Scope 缓存文件（预留）────────────────────────────────────────────────────
SCOPE_CACHE_FILE = DATA_DIR / ".scope_cache.json"

# ── .env / 安全存储中的 Token 变量名（预留）─────────────────────────────────────────
ENV_ACCESS_TOKEN = "OAUTH_1688_ACCESS_TOKEN"
ENV_REFRESH_TOKEN = "OAUTH_1688_REFRESH_TOKEN"
ENV_TOKEN_SCOPE = "OAUTH_1688_TOKEN_SCOPE"
ENV_TOKEN_EXPIRES_AT = "OAUTH_1688_TOKEN_EXPIRES_AT"
ENV_REFRESH_TOKEN_EXPIRES_AT = "OAUTH_1688_REFRESH_TOKEN_EXPIRES_AT"
ENV_CLIENT_ID = "OAUTH_1688_CLIENT_ID"
ENV_REDIRECT_URI = "OAUTH_1688_REDIRECT_URI"

# ── Keychain 服务名（预留）───────────────────────────────────────────────────
KEYCHAIN_SERVICE = "com.1688.oauth"

# ── 回调页面模板路径（预留，OAuth 模式使用）──────────────────────────────────────────
CALLBACK_TEMPLATE = BASE_DIR / "templates" / "callback.html"
