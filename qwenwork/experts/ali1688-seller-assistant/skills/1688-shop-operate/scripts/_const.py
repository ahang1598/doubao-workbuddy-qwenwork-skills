#!/usr/bin/env python3
"""
全局常量定义
"""
import os
from pathlib import Path
# ── Skill 根目录 ──────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
# ── Skill 版本 ────────────────────────────────────────────────────────────────
SKILL_VERSION = "1.0.0"
# ── OpenClaw 配置文件路径 ──────────────────────────────────────────────────────
OPENCLAW_CONFIG_PATH: Path = Path(
    os.environ.get("OPENCLAW_CONFIG_DIR", Path.home() / ".openclaw")
) / "openclaw.json"
# ── Workspace 目录自动发现 ────────────────────────────────────────────────────
def _find_workspace_dir() -> Path:
    """
    查找 workspace 目录。
    查找顺序：
    1. 环境变量 AGENT_WORK_ROOT + /workspace
    2. 从当前目录向上查找 workspace 目录
    3. 从当前目录向上查找 .skills 目录，其兄弟目录 workspace
    4. fallback 到当前目录
    """
    agent_work_root = os.environ.get("AGENT_WORK_ROOT")
    if agent_work_root:
        workspace_dir = Path(agent_work_root) / "workspace"
        return workspace_dir  # 不存在时后续会自动创建
    cwd = Path.cwd().resolve()
    for parent in [cwd] + list(cwd.parents):
        if parent.name == "workspace":
            return parent
    for parent in cwd.parents:
        skills_dir = parent / ".skills"
        if skills_dir.exists() and skills_dir.is_dir():
            workspace_dir = parent / "workspace"
            return workspace_dir
    return cwd
WORKSPACE_DIR = _find_workspace_dir()
# ── 运行时数据目录（Token 存储、缓存等）──────────────────────────────────────
DATA_DIR = WORKSPACE_DIR / ".1688-oauth"
# ── 统一日志文件路径 ──────────────────────────────────────────────────────────
LOG_FILE = DATA_DIR / "skill.log"
# ── AK 本地存储目录（独立于 OAuth 数据目录）──────────────────────────────────
AK_DATA_DIR = WORKSPACE_DIR / ".1688-AK"
AK_STORE_FILE = AK_DATA_DIR / ".ak_store.json"
# ── AK 环境变量名（仅供引用，_auth.py 已不从此读取）──────────────────────────
ENV_AK = "ALI_1688_AK"
# ── OAuth 客户端配置 ──────────────────────────────────────────────────────────
CLIENT_ID = os.environ.get("OAUTH_1688_CLIENT_ID", "3767346c-f079-4d16-8049-8ede627a480e")
# ── OAuth 服务端端点 ──
# 授权页面（用户在浏览器中完成登录授权）
AUTHORIZE_ENDPOINT = "https://air.1688.com/app/tai/oauth_page/index.html"
AUTHORIZE_ENDPOINT_LOCAL = "https://air.1688.com/app/tai/oauth_page/index.html"
# 用 authorization_code 换取 Token 的网关端点
TOKEN_ENDPOINT = "https://skills-gateway.1688.com/api/get_token_by_auth_code/1.0.0"
# 用 Refresh Token 换取新 Token 的网关端点
REFRESH_TOKEN_ENDPOINT = "https://skills-gateway.1688.com/api/refresh_token/1.0.0"
# Revoke 端点（吊销 Access Token / Refresh Token，通过 tokenTypeHint 区分）
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
# ── 超时 ──────────────────────────────────────────────────────────────────────
AUTHORIZATION_TIMEOUT = 300
HTTP_TIMEOUT = 30
TOKEN_REFRESH_MARGIN = 60
SCOPE_CACHE_TTL = 86400
# ── .env 文件 ─────────────────────────────────────────────────────────────────
ENV_FILE = DATA_DIR / ".env"
# ── Scope 缓存文件 ────────────────────────────────────────────────────────────
SCOPE_CACHE_FILE = DATA_DIR / ".scope_cache.json"
# ── .env / 安全存储中的 Token 变量名 ─────────────────────────────────────────
ENV_ACCESS_TOKEN = "OAUTH_1688_ACCESS_TOKEN"
ENV_REFRESH_TOKEN = "OAUTH_1688_REFRESH_TOKEN"
ENV_TOKEN_SCOPE = "OAUTH_1688_TOKEN_SCOPE"
ENV_TOKEN_EXPIRES_AT = "OAUTH_1688_TOKEN_EXPIRES_AT"
ENV_REFRESH_TOKEN_EXPIRES_AT = "OAUTH_1688_REFRESH_TOKEN_EXPIRES_AT"
ENV_CLIENT_ID = "OAUTH_1688_CLIENT_ID"
ENV_REDIRECT_URI = "OAUTH_1688_REDIRECT_URI"
# ── 授权模式 ──────────────────────────────────────────────────────────────────
AUTH_MODE_OAUTH = "oauth"
AUTH_MODE_AK = "AK"
AUTH_MODE_AK_LOCAL = "AKLocal"
# ── Keychain 服务名 ───────────────────────────────────────────────────────────
KEYCHAIN_SERVICE = "com.1688.oauth"
# ── 回调页面模板路径 ──────────────────────────────────────────────────────────
CALLBACK_TEMPLATE = BASE_DIR / "templates" / "callback.html"