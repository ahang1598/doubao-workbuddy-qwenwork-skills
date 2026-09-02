"""MCP 客户端（通用请求层）。

只做「发起请求」这一件事：调用 MCP 工具，自动 JSON-RPC 握手 + 鉴权 + 失败重试 + 结构体解析。

## Token 约定（公共）
- Token 从全局固定路径读取：`~/.workbuddy/.gongyi_token`。
- **Token 缺失 / 鉴权失败（401）时**，本模块直接打印 `{"need_refresh": true, ...}` 并以退出码 1 结束，
  agent 据此调用 `get_mcp_token` 重新获取并写回后重试（详见 `skills/_common/README.md`）。

"""
import argparse
import hashlib
import hmac
import json
import os
import re
import sys
import time
import uuid
from pathlib import Path

import requests


# ---------------------------------------------------------------------------
# 配置加载：依次从两个 mcp.json 查找（前者优先，缺失再查后者）
# ---------------------------------------------------------------------------
MCP_CFG_CANDIDATES = [
    os.path.expanduser("~/.workbuddy/mcp.json"),
    os.path.expanduser("~/.workbuddy/connectors/default/mcp.json"),
]


def _find_mcp_cfg():
    """返回第一个存在的 mcp.json 路径；都不存在则取第一个作为报错路径。"""
    for path in MCP_CFG_CANDIDATES:
        if os.path.isfile(path):
            return path
    return MCP_CFG_CANDIDATES[0]


def load_gongyi():
    """读取本地 mcp.json 配置；配置缺失或 url 为空时回退到内置兜底地址。

    返回 dict（含 url / headers 等）。仅当 url 无法从配置取得时才使用
    MCP_FALLBACK_URL，配置中的 url 优先。
    """
    cfg_path = _find_mcp_cfg()
    if os.path.isfile(cfg_path):
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        server = cfg.get("mcpServers", {}).get("gongyi-open-mcp", {})
    else:
        server = {}
    if not server.get("url"):
        server["url"] = MCP_FALLBACK_URL
    return server


CALLER_EXPERT_ID = "today-todo-assistant"   # 调用方身份标识（必填，下游据此区分来源）

# MCP 协议版本（与官方 SDK 保持一致）
MCP_PROTOCOL_VERSION = "2024-11-05"

# Token 固定路径（全局统一）
MCP_TOKEN_PATH = os.path.expanduser("~/.workbuddy/.gongyi_token")


class MCPAuthError(RuntimeError):
    """MCP 鉴权失败：token 缺失 / 过期 / 401。调用方（agent）应重新获取 token。"""
    need_refresh = True


# ---------------------------------------------------------------------------
# Token 读取（固定路径 ~/.workbuddy/.gongyi_token）
# ---------------------------------------------------------------------------
def _read_token():
    """从固定路径 ~/.workbuddy/.gongyi_token 读取 token；缺失或空返回 None（不退出）。"""
    if not os.path.isfile(MCP_TOKEN_PATH):
        return None
    with open(MCP_TOKEN_PATH, "r", encoding="utf-8") as f:
        tok = f.read().strip()
    return tok or None


def load_token(session_dir=None):
    """从固定路径 ~/.workbuddy/.gongyi_token 读取 MCP token。文件缺失或为空直接要求刷新（退出）。"""
    tok = _read_token()
    if not tok:
        _auth_fail(f"MCP token 文件不存在或为空({MCP_TOKEN_PATH})，请 agent 调用 get_mcp_token 重新获取并落盘")
    return tok


# 鉴权 Header 名称与前缀（gongyi-open-mcp 实际要求 Authorization: Bearer <token>）
AUTH_HEADER_NAME = "Authorization"
AUTH_HEADER_PREFIX = "Bearer "


# 单例 session（复用连接 + 统一 UA）
_session = None


# 通用 UA / Origin（与 Web 端保持一致）
_COMMON_UA = "Mozilla/5.0 (compatible; alert-expert-shared/1.0)"
_COMMON_ORIGIN = "https://ssl.gongyi.qq.com"

# 兜底地址：mcp.json 未配置 url 时使用（生产网关 gygw-web）
MCP_FALLBACK_URL = "https://ssl.gongyi.qq.com/gygw-web/api/open/tob/mcp"


# 允许上传的图片/文档后缀
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".pdf"}


def mask(s):
    """对敏感字符串做脱敏（保留首尾，中间打码）。"""
    s = str(s)
    if len(s) <= 8:
        return "*" * len(s)
    return s[:4] + "*" * (len(s) - 8) + s[-4:]


def _sanitize(s):
    """将 MCP 返回体中疑似 token / 凭证的内容脱敏，避免明文打印。"""
    if not isinstance(s, str):
        return s
    return re.sub(r"(?i)([A-Za-z0-9_\-]{24,})", lambda m: mask(m.group(1)), s)


# ---------------------------------------------------------------------------
# 鉴权失败统一出口：打印 need_refresh 并退出（agent 据此重新获取 token）
# ---------------------------------------------------------------------------
def _auth_fail(reason):
    print(json.dumps({"success": False, "need_refresh": True,
                      "error_code": "auth_failed", "message": reason},
                     ensure_ascii=False))
    sys.exit(1)


# ---------------------------------------------------------------------------
# 通用请求层（JSON-RPC over HTTP，对齐 gongyi-open-mcp）
# ---------------------------------------------------------------------------
def _base_headers(token):
    return {
        AUTH_HEADER_NAME: AUTH_HEADER_PREFIX + token,
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "User-Agent": _COMMON_UA,
        "Origin": _COMMON_ORIGIN,
    }


def _mcp_post(url, headers, payload, timeout):
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update({"User-Agent": _COMMON_UA})
    return _session.post(url, headers=headers, json=payload, timeout=timeout)


def _extract_json(text):
    """从工具返回文本中抽出 JSON 对象（标准 MCP 把 data 放在 content[].text 内）。"""
    if not text:
        return None
    s = text.strip()
    try:
        return json.loads(s)
    except Exception:
        pass
    m = re.search(r"\{.*\}", s, re.S)
    return json.loads(m.group()) if m else None


def _parse_result(body):
    """统一解析 tools/call 的返回，兼容两种形态：
    - 标准 MCP：body['result']['content'][].text 内嵌 JSON（本项目服务端实际形态）
    - 较新 MCP：body['result']['structuredContent']['data']
    """
    if not isinstance(body, dict) or "result" not in body:
        return {"text": "", "data": None, "is_error": True}
    result = body["result"]
    if isinstance(result, dict) and isinstance(result.get("structuredContent"), dict):
        return {
            "text": "",
            "data": result["structuredContent"].get("data"),
            "is_error": bool(result.get("isError", False)),
        }
    content = (result.get("content") or []) if isinstance(result, dict) else []
    text = "".join(b.get("text", "") for b in content if b.get("type") == "text").strip()
    return {"text": text, "data": _extract_json(text), "is_error": bool(result.get("isError", False)) if isinstance(result, dict) else False}


def _parse_body(resp):
    text = resp.text
    ct = resp.headers.get("Content-Type", "")
    if "text/event-stream" in ct:
        return _extract_json(text)
    try:
        return json.loads(text)
    except Exception:
        return _extract_json(text)


def _extract_json(text):
    """从 SSE 文本流中提取最后一个 JSON 对象。"""
    if not text:
        return {}
    last = None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            line = line[len("data:"):].strip()
        if not line:
            continue
        try:
            last = json.loads(line)
        except Exception:
            continue
    if last is not None:
        return last
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            return {}
    return {}


def _init_session():
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update({"User-Agent": _COMMON_UA})
    return _session


# 鉴权失败关键词（仅在返回确为“错误”时命中，才视为需要重新登录）
_AUTH_HINTS = ("unauthorized", "unauthenticated", "token expired", "token invalid",
               "invalid token", "permission denied", "forbidden", "鉴权失败",
               "未登录", "登录失效", "401")


def _is_auth_error(body):
    """判断返回体是否表示鉴权失败。

    关键点：必须先确认返回本身是“错误响应”，再匹配鉴权关键词；不能仅凭
    正常返回内容里出现 token / 登录 / auth 等字眼就误判为需要重新登录，
    否则成功的业务返回会被错当成鉴权失败。

    错误响应判定（满足其一）：
    - JSON-RPC 协议层错误：body 含 "error" 字段
    - 工具层错误：body["result"]["isError"] 为 True
    """
    if not isinstance(body, dict):
        return False

    # 1) 仅当返回确为错误时，才提取错误文案
    err_text = ""
    if isinstance(body.get("error"), dict):
        # JSON-RPC 协议层错误，取 error 内各字段文本
        err_text = " ".join(str(v) for v in body["error"].values())
    elif isinstance(body.get("result"), dict) and body["result"].get("isError") is True:
        # 工具层错误，取 content 中文本类型的 text
        content = body["result"].get("content") or []
        err_text = " ".join(
            b.get("text", "") for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        )
    else:
        # 非错误响应（成功），直接判定不是鉴权失败
        return False

    # 2) 仅在错误文案中匹配鉴权关键词
    t = err_text.lower()
    return any(h in t for h in _AUTH_HINTS)


def call_mcp(tool_name, arguments, timeout=30):
    """调用 MCP 工具（JSON-RPC notifications/tools/call）。

    :param tool_name: 工具名（如 get_org_cos_credential）
    :param arguments: 业务参数 dict
    :param timeout: 单次请求超时（秒）
    :return: 解析后的 dict，含 {text, data, is_error}
    """
    # 强制注入正确的调用方身份：无论上游传了什么（可能是过时/错误的硬编码值），
    # 一律以本模块的 CALLER_EXPERT_ID 为准；合并进专家团后即自动切换为专家团身份。
    arguments = dict(arguments or {})
    arguments["caller_expert_id"] = CALLER_EXPERT_ID
    server = load_gongyi()
    url = server["url"]
    cfg_headers = dict(server.get("headers", {}) or {})
    # 鉴权头：token 唯一来源是 ~/.workbuddy/.gongyi_token（由 get_mcp_token 落盘）；
    # ⛔ 严禁使用 mcp.json 里注入的 Authorization（连接器已走标准 OAuth，mcp.json 不应再携带 token）
    tok = _read_token()
    if not tok:
        _auth_fail(f"MCP token 缺失({MCP_TOKEN_PATH})，请 agent 调用 get_mcp_token 重新获取并落盘")
    auth = "Bearer " + tok
    base_headers = cfg_headers
    base_headers["Authorization"] = auth
    base_headers.setdefault("Content-Type", "application/json")
    base_headers.setdefault("Accept", "application/json, text/event-stream")
    base_headers.setdefault("User-Agent", _COMMON_UA)
    base_headers.setdefault("Origin", _COMMON_ORIGIN)
    base_headers["Mcp-Session-Id"] = uuid.uuid4().hex

    last_err = None
    for attempt in range(3):
        try:
            # 1) initialize
            init_payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": CALLER_EXPERT_ID, "version": "1.0"},
                },
            }
            _mcp_post(url, base_headers, init_payload, timeout)
            # 2) initialized 通知
            _mcp_post(url, base_headers, {
                "jsonrpc": "2.0", "method": "notifications/initialized"
            }, timeout)
            # 3) tools/call
            call_payload = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": arguments},
            }
            resp = _mcp_post(url, base_headers, call_payload, timeout)
            body = _parse_body(resp)
            if _is_auth_error(body):
                _auth_fail("MCP 鉴权失败(401)，请 agent 调用 get_mcp_token 重新获取")
            return _parse_result(body)
        except Exception as e:
            last_err = e
            time.sleep(min(2 ** attempt, 5))
    return {"text": f"调用失败: {last_err}", "data": None, "is_error": True}


def get_user_and_org_info(timeout=30):
    """查询当前 token 绑定的用户与机构信息（get_user_and_org_info 工具）。

    成功返回机构信息 dict（含 org_no / org_name / type_of_organization /
    affili_pub_org / affili_pub_org_name / account_id / name）。
    失败返回 {"is_error": True, "text": "<描述>"}。
    鉴权失败沿用 call_mcp 的 _auth_fail 行为（打印 need_refresh 并退出）。
    """
    r = call_mcp("get_user_and_org_info", {}, timeout)
    if r.get("is_error"):
        return {"is_error": True, "text": r.get("text") or "get_user_and_org_info 调用失败"}
    data = r.get("data")
    if not isinstance(data, dict):
        # 兜底：structuredContent 平铺时 data 可能为空，从 text 再解析一次
        text = (r.get("text") or "").strip()
        if text:
            try:
                data = json.loads(text)
            except Exception:
                data = None
    if not isinstance(data, dict):
        return {"is_error": True, "text": "get_user_and_org_info 返回为空"}
    # 兼容服务端再包一层 data 的形态
    if "org_no" not in data and "org_name" not in data and isinstance(data.get("data"), dict):
        data = data["data"]
    return data


def set_common_data_cache(data_obj, caller_expert_id=CALLER_EXPERT_ID, timeout=30):
    """把 UI 所需数据写入公共缓存，返回 data_cache_id。

    :param data_obj: object，即"原先脚本直接输出、要整体透传给 UI 的那份完整 JSON"
                     （如 {caller_expert_id, org_cert_update_review, submit}
                      / {caller_expert_id, fundraising_program, submit}），
                     作为 {"data": <该 JSON>} 传给 set_common_data_cache
    :param caller_expert_id: 调用方身份；缺省用全局 CALLER_EXPERT_ID
    :return: str data_cache_id；调用 UI 工具时只带 caller_expert_id + 该 key
    """
    arguments = {"data": data_obj}
    if caller_expert_id:
        arguments["caller_expert_id"] = caller_expert_id
    r = call_mcp("set_common_data_cache", arguments, timeout)
    if r.get("is_error"):
        raise RuntimeError(f"set_common_data_cache 失败: {r.get('text')}")
    d = r.get("data") or {}
    if isinstance(d, dict) and "data_cache_id" not in d and isinstance(d.get("data"), dict):
        d = d["data"]
    key = d.get("data_cache_id") if isinstance(d, dict) else None
    if not key:
        raise RuntimeError(f"set_common_data_cache 未返回 data_cache_id: {r.get('text')}")
    return key
