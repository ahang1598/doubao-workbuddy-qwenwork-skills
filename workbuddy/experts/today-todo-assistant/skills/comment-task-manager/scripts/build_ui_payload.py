#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
腾讯公益留言运营专家 · 留言回复页面载荷组装 + 后台缓存写入脚本
====================================================
职责：把「留言精简列表 + 上下文 + AI 建议回复映射」在本地拼装成
open_comment_reply_ui 的完整入参 JSON，并**直接通过 MCP 协议调用
set_common_data_cache 写入后台缓存**（参考 alert-expert/skills/_common/mcp_client.py
的 streamable-HTTP JSON-RPC 直连模式；不直连业务 oapi，避免额外注册接口），
Agent 随后只需把返回的缓存 key 作为 data_cache_id 传给 open_comment_reply_ui，
大载荷完全不经过 LLM 输出（消除模型转录膨胀：实测 64KB 文件曾被膨胀为 5.9MB
工具入参、单步 85.4s）。

输入（均位于 run_dir，由 fetch_payload.py 产出 + Agent 生成阶段写入）：
  {run_dir}/raw/unreplied_comments.json   提供 total / risk_total
  {run_dir}/comments_brief.json           留言精简列表（12 个协议字段，原始顺序）
  {run_dir}/contexts.json                 两段式上下文（projects + contexts）
  {run_dir}/ai_suggestions.json           Agent 生成的 {"<comment_id>": "<建议>", ...}

输出：
  {run_dir}/ui_payload.json               始终落盘（indent=2），方便定位排查
  stdout 汇总 JSON                        含 data_cache_id（缓存写入成功时）

用法：
  python3 skills/comment-task-manager/scripts/build_ui_payload.py \
    --run-dir "output/.cache/<ts>" \
    [--token "<get_mcp_token 返回的 token>"] \
    [--suggestions-file "output/.cache/<ts>/ai_suggestions.json"] \
    [--caller-expert-id "comment-assistant"] \
    [--endpoint "<显式覆盖 MCP 端点>"]

stdout 输出一行汇总 JSON：
  {"payload_path": "...", "list_len": N, "payload_bytes": B,
   "data_cache_id": "<key 或 null>", "cache_write": "ok|failed",
   "missing_suggestions": ["<comment_id>", ...]}

Agent 使用约定：
  - cache_write=ok：调用 open_comment_reply_ui 只传
    {"caller_expert_id": ..., "data_cache_id": data_cache_id}（无需 Read ui_payload.json）
  - cache_write=failed：降级为 Read ui_payload.json 后原样透传完整入参
    （caller_expert_id/total/risk_total/list/submit）
"""

import argparse
import json
import os
import re
import stat
import sys
import time
import urllib.request

# 可观测埋点（非关键路径：SDK 不可用时自动降级为 no-op，绝不影响业务流程）
sys.path.insert(
    0,
    os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "_common")
    ),
)
from observe_bootstrap import (  # noqa: E402
    expert_version,
    galileo_observer,
    galileo_topic,
    observe_span,
)

EXIT_OK = 0
EXIT_PARAM_ERROR = 2

# ---------------------------------------------------------------------------
# MCP token 全局缓存（对齐 invoice-expert skills/_common/mcp_client.py 约定，
# 与 fetch_payload.py 共享同一文件）
#
# - 固定全局路径 ~/.workbuddy/.gongyi_token，跨专家共享（同一台机器同一环境）；
#   token 内含环境段（_prod_ / _test_），测试/正式环境切换由后端换发 token 天然隔离，
#   无需按环境分文件
# - 本地不判断过期时间（get_mcp_token 响应无 expires_in 契约）：文件里有就直接用，
#   过期以接口实际鉴权失败为准——识别口径对齐 mcp_client._is_auth_error：
#   「先确认是错误响应，再在错误文案里匹配鉴权关键词」，命中后打印 need_refresh JSON
#   并以特定退出码退出，Agent 据此调 get_mcp_token 重取（新 token 覆盖写回缓存）后重跑
# ---------------------------------------------------------------------------
TOKEN_CACHE_PATH = os.path.expanduser(os.path.join("~", ".workbuddy", ".gongyi_token"))

# 鉴权失败关键词（仅在返回确为"错误"时命中才视为 token 失效，避免正常业务文案误伤）
AUTH_HINTS = (
    "unauthorized", "unauthenticated", "token expired", "token invalid",
    "invalid token", "permission denied", "forbidden", "鉴权失败",
    "未登录", "登录失效", "401",
)

EXIT_NO_TOKEN = 3       # 本地无 token 缓存
EXIT_NEED_REFRESH = 4   # 接口鉴权失败，token 过期/失效


def load_cached_token():
    """读取全局缓存的 token；文件不存在或内容为空时返回 None"""
    try:
        with open(TOKEN_CACHE_PATH, encoding="utf-8") as f:
            token = f.read().strip()
        return token or None
    except OSError:
        return None


def save_token_cache(token):
    """把新获取的 token 覆盖写入全局缓存（0600 权限），供后续 run / 其他专家复用"""
    try:
        os.makedirs(os.path.dirname(TOKEN_CACHE_PATH), exist_ok=True)
        with open(TOKEN_CACHE_PATH, "w", encoding="utf-8") as f:
            f.write(token)
        os.chmod(TOKEN_CACHE_PATH, stat.S_IRUSR | stat.S_IWUSR)
    except OSError as e:
        print(f"[build] token 缓存写入失败（不影响本次运行）: {e!r}", file=sys.stderr)


def clear_token_cache():
    """token 失效时删除全局缓存，避免后续 run 继续复用坏 token"""
    try:
        os.remove(TOKEN_CACHE_PATH)
    except OSError:
        pass


def emit_need_refresh(reason):
    """鉴权失败统一出口：打印 need_refresh JSON（对齐 mcp_client 约定）。"""
    print(json.dumps(
        {"need_refresh": True, "error": "token_invalid", "message": reason},
        ensure_ascii=False,
    ))


def is_auth_error_text(err_text):
    """判断接口错误文案是否表示鉴权失败（token 过期/失效）。

    关键词只在错误文案中匹配——本函数只会在接口已抛错时被调用，
    因此不会出现成功返回误判（对齐 mcp_client._is_auth_error 的语义）。
    """
    text = str(err_text).lower()
    return any(h in text for h in AUTH_HINTS)

# submit 固定契约（一字不差，不得改写）
# 格式为可路由句式："执行X专家的Y步骤"
# Host 据此解析专家名与步骤名；回复由 APP 直连后台接口提交，提交完成后按此文案通知本专家刷新
SUBMIT_CONTRACT = {
    "next_step": "执行comment-assistant专家的刷新留言列表步骤"
}

# --------------------------------------------------------------------------- #
# MCP streamable-HTTP 直连（参考 alert-expert/skills/_common/mcp_client.py，
# 用 urllib 实现，零第三方依赖；不直连业务 oapi，无需额外注册接口）
# --------------------------------------------------------------------------- #
MCP_PROTOCOL_VERSION = "2024-11-05"
# 环境路由：与 fetch_payload.py 同口径，按 token 中的 _prod_/_test_ 环境段判定，
# 不枚举具体 token 前缀（gy_open_mcp_* / gy_open_mcp_test_* / gy_mcp_at_* 等）
MCP_ENDPOINT_PROD = "https://ssl.gongyi.qq.com/gygw-web/api/open/tob/mcp"
MCP_ENDPOINT_TEST = "https://ssl.gongyi.qq.com/gygw-test/api/open/tob/mcp"

# ⚠️ ssl.gongyi.qq.com 前置 EdgeOne WAF 会拦截非浏览器 UA，必须带浏览器特征头
COMMON_UA = "Mozilla/5.0 (compatible; comment-assistant/1.0)"
COMMON_ORIGIN = "https://ssl.gongyi.qq.com"


def fail(message: str, exit_code: int = EXIT_PARAM_ERROR) -> None:
    print(f"build_ui_payload error: {message}", file=sys.stderr)
    sys.exit(exit_code)


def load_json(path: str):
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def get_mcp_endpoint(token: str, endpoint_override: str = "") -> str:
    """按 token 中的环境段路由 MCP 端点；无法判定时 fail-closed，用 --endpoint 显式指定。"""
    if endpoint_override:
        return endpoint_override
    if "_prod_" in token:
        return MCP_ENDPOINT_PROD
    if "_test_" in token:
        return MCP_ENDPOINT_TEST
    fail("token 中未识别到环境段（_prod_ / _test_），请用 --endpoint 显式指定 MCP 端点")


def _mcp_post(url: str, token: str, session_id, payload: dict, timeout: int):
    """发送一次 MCP JSON-RPC 请求，返回 (响应体 dict|None, 新 session_id)；兼容 SSE 响应。"""
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "User-Agent": COMMON_UA,
        "Origin": COMMON_ORIGIN,
        "Authorization": "Bearer " + token,
    }
    if session_id:
        headers["Mcp-Session-Id"] = session_id
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
        new_sid = resp.headers.get("Mcp-Session-Id", session_id)
        content_type = resp.headers.get("Content-Type", "")
    if "text/event-stream" in content_type:
        for line in raw.splitlines():
            if line.startswith("data:"):
                data = line[len("data:"):].strip()
                if data:
                    try:
                        return json.loads(data), new_sid
                    except json.JSONDecodeError:
                        continue
        return None, new_sid
    try:
        return json.loads(raw), new_sid
    except json.JSONDecodeError:
        return None, new_sid


def call_mcp_tool(url: str, token: str, tool_name: str, arguments: dict, timeout: int = 60):
    """initialize → notifications/initialized → tools/call，返回工具文本输出。"""
    init_body, sid = _mcp_post(url, token, None, {
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": MCP_PROTOCOL_VERSION, "capabilities": {},
                   "clientInfo": {"name": "comment-assistant", "version": "1.0.0"}},
    }, timeout)
    if init_body is None or "result" not in init_body:
        raise RuntimeError(f"MCP initialize 失败: {str(init_body)[:200]}")
    # initialized 通知（无 id，无需读响应）
    try:
        _mcp_post(url, token, sid, {
            "jsonrpc": "2.0", "method": "notifications/initialized", "params": {},
        }, timeout)
    except Exception:
        pass
    call_body, _ = _mcp_post(url, token, sid, {
        "jsonrpc": "2.0", "id": 2, "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }, timeout)
    if call_body is None or "result" not in call_body:
        raise RuntimeError(f"MCP tools/call({tool_name}) 失败: {str(call_body)[:200]}")
    result = call_body["result"]
    content = result.get("content", []) or []
    text = "".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text").strip()
    if result.get("isError"):
        raise RuntimeError(f"MCP 工具 {tool_name} 返回错误: {text[:300]}")
    return text


def extract_cache_key(text: str):
    """从 set_common_data_cache 返回中提取缓存 key（兼容字段名差异与外层包裹文本）。"""
    if not text:
        return None
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return text.strip() or None  # 直接返回了纯 key 文本
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None

    def _find(node):
        if isinstance(node, dict):
            for name in ("data_cache_id", "cache_key", "snapshot_id", "key"):
                v = node.get(name)
                if isinstance(v, str) and v:
                    return v
            for v in node.values():
                found = _find(v)
                if found:
                    return found
        elif isinstance(node, list):
            for v in node:
                found = _find(v)
                if found:
                    return found
        return None

    return _find(obj)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="拼装 open_comment_reply_ui 完整入参、写文件并写入后台缓存")
    parser.add_argument("--run-dir", required=True, help="本轮工作目录（含 raw/、contexts.json、comments_brief.json）")
    parser.add_argument(
        "--token",
        default=None,
        help="MCP Token（get_mcp_token 返回；按 prod/test 环境段自动路由 MCP 端点）；不传时读全局缓存 ~/.workbuddy/.gongyi_token",
    )
    parser.add_argument(
        "--suggestions-file",
        default=None,
        help="AI 建议回复映射文件（默认 {run_dir}/ai_suggestions.json）",
    )
    parser.add_argument(
        "--caller-expert-id", default="comment-assistant", help="调用方 expert id"
    )
    parser.add_argument(
        "--endpoint",
        default="",
        help="MCP 端点显式覆盖（可选）；不传时按 token 中的 prod/test 环境段自动路由",
    )
    parser.add_argument("--timeout", type=int, default=60, help="HTTP 超时秒数")
    return parser.parse_args(argv)


def build_payload(run_dir: str, suggestions: dict, caller_expert_id: str) -> tuple:
    """拼装完整载荷，返回 (payload, missing_suggestions)。"""
    brief = load_json(os.path.join(run_dir, "comments_brief.json")) or []
    contexts_payload = load_json(os.path.join(run_dir, "contexts.json")) or {}
    projects = contexts_payload.get("projects") or {}
    contexts = contexts_payload.get("contexts") or {}
    raw_comments = load_json(os.path.join(run_dir, "raw", "unreplied_comments.json")) or {}

    items = []
    missing = []
    for item in brief:
        if not isinstance(item, dict):
            continue
        comment_id = item.get("comment_id")
        suggestion = suggestions.get(str(comment_id), "")
        if not suggestion:
            missing.append(str(comment_id))

        otype = item.get("object_type")
        oid = str(item.get("object_id") or "")
        ctx = contexts.get(f"{otype}:{oid}") or {}

        process_name = ""
        refer_process_num = 0
        if otype == "project":
            pid = str(item.get("object_id") or "")
            plist = (projects.get(pid) or {}).get("process_list") or []
            refer_process_num = len(plist)
        elif otype == "process":
            pdetail = ctx.get("process_detail") or {}
            if pdetail:
                process_name = pdetail.get("content_title") or ""
                refer_process_num = 1

        # 零转录原地挂载：12 个协议字段原样 + 3 个增强字段，共 15 个
        merged = dict(item)
        # comment_id 协议为 uint64，必须保持 JSON number（fetch_payload.py 落盘时已
        # 统一转换；此处为防御性兜底，兼容旧缓存目录中的字符串形态数据）
        cid = merged.get("comment_id")
        if isinstance(cid, str) and cid.isdigit():
            merged["comment_id"] = int(cid)
        merged["ai_suggestion"] = suggestion
        merged["process_name"] = process_name
        merged["refer_process_num"] = refer_process_num
        items.append(merged)

    payload = {
        "caller_expert_id": caller_expert_id,
        "total": raw_comments.get("total", len(items)),
        "risk_total": raw_comments.get("risk_total", 0),
        "list": items,
        "submit": dict(SUBMIT_CONTRACT),
    }
    return payload, missing


def write_data_cache(endpoint: str, token: str, payload: dict, timeout: int):
    """调 set_common_data_cache 写入后台缓存，返回缓存 key（失败抛异常由调用方降级）。"""
    # data 不含 caller_expert_id（调用级参数），只缓存 UI 数据本体
    data = {
        "total": payload["total"],
        "risk_total": payload["risk_total"],
        "list": payload["list"],
        "submit": payload["submit"],
    }
    text = call_mcp_tool(endpoint, token, "set_common_data_cache", {
        "caller_expert_id": payload["caller_expert_id"],
        "data": data,
    }, timeout)
    key = extract_cache_key(text)
    if not key:
        raise RuntimeError(f"set_common_data_cache 返回中未找到缓存 key: {text[:200]}")
    return key


# 模块级观测结果透传：_main 内记录关键业务指标，main 的 trace.set_result 统一上报
_OBSERVE_RESULT = {}


def _main(argv=None) -> int:
    global _OBSERVE_RESULT
    _OBSERVE_RESULT = {}
    args = parse_args(argv)
    run_dir = os.path.abspath(args.run_dir)
    if not os.path.isdir(run_dir):
        fail(f"run_dir 不存在: {run_dir}")

    suggestions_path = args.suggestions_file or os.path.join(run_dir, "ai_suggestions.json")
    suggestions = load_json(suggestions_path) or {}
    if not isinstance(suggestions, dict):
        fail(f"建议映射文件格式错误（应为 JSON 对象）: {suggestions_path}")

    with observe_span("comment_assistant.build.assemble", kind="tool"):
        payload, missing = build_payload(run_dir, suggestions, args.caller_expert_id)

    # 记录组装结果与 id 列表，供埋点上报
    list_len = len(payload["list"])
    comment_ids = [str(it.get("comment_id")) for it in payload["list"] if isinstance(it, dict)]
    _OBSERVE_RESULT["total"] = payload.get("total")
    _OBSERVE_RESULT["risk_total"] = payload.get("risk_total")
    _OBSERVE_RESULT["comment_count"] = list_len
    _OBSERVE_RESULT["comment_ids"] = comment_ids
    _OBSERVE_RESULT["missing_suggestion_count"] = len(missing)
    # 提交请求的简单字段（data 中除 list 外的字段）
    _OBSERVE_RESULT["submit_total"] = payload.get("total")
    _OBSERVE_RESULT["submit_risk_total"] = payload.get("risk_total")
    _OBSERVE_RESULT["submit_next_step"] = (payload.get("submit") or {}).get("next_step")

    # 始终落盘 ui_payload.json（indent=2），方便定位排查；再直连 MCP 写后台缓存
    payload_path = os.path.join(run_dir, "ui_payload.json")
    with open(payload_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    payload_bytes = os.path.getsize(payload_path)

    # --token 显式传入时优先使用（通常为新获取的 token，覆盖写回全局缓存）；
    # 未传时读全局缓存文件，文件里有就直接用、不重新拉取
    if args.token:
        token = args.token
        save_token_cache(token)
    else:
        token = load_cached_token()
        if not token:
            emit_need_refresh(
                f"本地无 token 缓存({TOKEN_CACHE_PATH} 不存在或为空)，"
                "请 agent 调用 get_mcp_token 获取 token 后以 --token 传入"
            )
            return EXIT_NO_TOKEN

    cache_key = None
    cache_write = "failed"
    try:
        endpoint = get_mcp_endpoint(token, args.endpoint)
        with observe_span(
            "comment_assistant.build.set_common_data_cache",
            kind="tool",
            attributes={
                "payload_bytes": payload_bytes,
                "list_len": list_len,
                "comment_ids": comment_ids,
                # 提交请求的简单字段（data 中除 list 外的字段）
                "submit_total": payload.get("total"),
                "submit_risk_total": payload.get("risk_total"),
                "submit_next_step": (payload.get("submit") or {}).get("next_step"),
            },
        ):
            cache_key = write_data_cache(endpoint, token, payload, args.timeout)
        cache_write = "ok"
        _OBSERVE_RESULT["data_cache_id"] = cache_key
        _OBSERVE_RESULT["cache_write"] = "ok"
    except Exception as e:
        print(f"[build] 警告：set_common_data_cache 写入失败: {e!r}", file=sys.stderr)
        if is_auth_error_text(repr(e)):
            # token 过期/失效：删除全局缓存并打印 need_refresh JSON（对齐 mcp_client 约定），
            # Agent 据此调 get_mcp_token 获取新 token 后以 --token 重跑本脚本
            clear_token_cache()
            emit_need_refresh(
                f"set_common_data_cache 鉴权失败，token 缓存已清除({TOKEN_CACHE_PATH})，"
                "请 agent 调用 get_mcp_token 重新获取后以 --token 重跑"
            )
            return EXIT_NEED_REFRESH
        # 非鉴权类失败（网络/服务端业务错误）：保留缓存，按通用失败退出
        fail(f"set_common_data_cache 写入失败: {e!r}")

    print(
        json.dumps(
            {
                "payload_path": payload_path,
                "list_len": len(payload["list"]),
                "payload_bytes": payload_bytes,
                "data_cache_id": cache_key,
                "cache_write": cache_write,
                "missing_suggestions": missing,
            },
            ensure_ascii=False,
        )
    )
    if missing:
        print(
            f"[build] 警告：{len(missing)} 条留言缺少建议回复（ai_suggestion 置空）",
            file=sys.stderr,
        )
    return EXIT_OK


# 退出码 → 埋点错误类型映射（仅非 0 时上报 error_type）
_EXIT_ERROR_TYPES = {
    EXIT_NO_TOKEN: "NO_CACHED_TOKEN",
    EXIT_NEED_REFRESH: "TOKEN_INVALID",
}


def main(argv=None) -> int:
    """埋点 trace 包装：上报整体耗时、退出码与业务结果；失败不影响业务。"""
    observer = galileo_observer(
        "comment-assistant",
        expert_version(),
        galileo_topic=galileo_topic(),
        spool_dir=os.path.join("output", ".observe"),
    )
    run_id = str(int(time.time()))
    with observer.trace(
        "comment_assistant.build_ui_payload",
        run_id=run_id,
        session_id=run_id,
        attributes={"entrypoint": "build_ui_payload"},
    ) as observe_trace:
        try:
            exit_code = _main(argv)
        except SystemExit as error:
            code = error.code if isinstance(error.code, int) else 1
            observe_trace.set_result(
                success=(code == 0),
                error_type=None if code == 0 else "BUILD_FAILED",
                status_message=None if code == 0 else "build ui payload failed",
                attributes={"exit_code": code},
            )
            raise
        result_attrs = {"exit_code": exit_code}
        result_attrs.update(_OBSERVE_RESULT)
        observe_trace.set_result(
            success=(exit_code == 0),
            error_type=_EXIT_ERROR_TYPES.get(exit_code),
            attributes=result_attrs,
        )
        return exit_code


if __name__ == "__main__":
    sys.exit(main())
