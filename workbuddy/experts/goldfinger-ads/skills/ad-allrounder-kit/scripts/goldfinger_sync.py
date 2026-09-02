#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
艾投 → 金手指 复盘自动回灌器 (goldfinger_sync.py)

用途：生成复盘后一键同步到金手指平台，自动处理三大坑并强制回读校验。
- 坑1 单条 payload 超 65535 字节被静默截断 → 自动分片 + MD5 校验
- 坑2 无删除接口 → 失败不重复灌，先回读探测
- 坑3 append 语义 → 重试前先查是否已写入

鉴权（2026-08-27 起改为 OAuth；2026-08-31 起接入方式改为连接器依赖）：
专家包**不再自带 `.mcp.json`**，改为在 `plugin.json` 声明
`dependencies.connectors: ["jinshouzhi"]`，引用 WorkBuddy 已上架的金手指连接器；
OAuth 配置由连接器侧维护。用户在「连接器 →金手指 MCP」点连接、跳转金手指授权即可，
**不再手填 Token**。授权后的 accessToken 由平台加密托管（`mcpOAuth`），
**不以环境变量下发给脚本**。

因此调用金手指有两条路，优先级如下：
  1) **首选：直接调 MCP 工具**（`mcp__jinshouzhi__*`）—— 由平台自动带 OAuth 凭证，脚本无需拿 token。
  2) 兜底：本脚本直连 HTTP。仅当环境里显式提供 `GOLD_FINGER_TOKEN` / `GOLDFINGER_MCP_TOKEN`
     （如联调、CI、或旧 token 模式）时可用；取不到就抛 TokenMissing 并引导用户去连接器授权。
本脚本**只读不申请**，绝不调用 regenerate —— 那会让已生效的凭证立即失效。

用法:
  python3 goldfinger_sync.py --project "踏雪香薰" --md 复盘.md --html 报告.html \
      --kind final_review --title "艾投·投放结案复盘_踏雪香薰_20260825" \
      --metrics '{"cost":72230,"orders":598}'
返回: JSON（含 artifact ids / 校验结果 / 查看链接）
"""
import json, urllib.request, urllib.error, hashlib, argparse, sys, os

BASE = "https://ad-goldfinger.app.fitgroup-fat.com"
MCP = BASE + "/mcp"
# 单片正文安全上限（utf8 字节）。中文经 JSON 转义会膨胀，故远低于 65535 硬上限
CHUNK_LIMIT = 40000
SAFE_SINGLE = 55000  # 单条 payload 序列化后超过此值就走分片

# 兜底直连时可用的环境变量（OAuth 模式下平台不下发，仅联调/CI 场景手动提供）
ENV_KEYS = ("GOLD_FINGER_TOKEN", "GOLDFINGER_MCP_TOKEN")
# 旧版脚本自管 Token 的遗留路径，仅作兼容读取，不再写入
LEGACY_TOKEN_FILE = os.path.expanduser("~/.workbuddy/.goldfinger_mcp_token")

GUIDE = (
    "金手指还没授权，先连一下（不用填 Token，点一下跳转授权就行）：\n"
    "  1) 打开 WorkBuddy →「连接器」→ 找到「金手指 MCP」；\n"
    "  2) 点「连接」，会跳到金手指页面，登录并同意授权；\n"
    "  3) 回来跟艾投说一声，我立刻重新同步。\n"
    "（授权代表你的账号身份，连好后只会读写你自己的项目数据。）\n"
    "提示：授权后请优先让我直接调用金手指 MCP 工具；本脚本直连仅用于联调，"
    "需显式提供 GOLD_FINGER_TOKEN 环境变量。"
)


class TokenMissing(RuntimeError):
    """金手指未授权 / 凭证失效 —— 应引导用户去连接器完成 OAuth 授权，而非静默失败。"""


def get_token():
    """只读取平台注入/环境变量中的 Token，绝不主动申请或刷新。"""
    for k in ENV_KEYS:
        v = (os.environ.get(k) or "").strip()
        if v:
            return v
    if os.path.exists(LEGACY_TOKEN_FILE):  # 兼容期：读旧文件，但不再新建
        v = open(LEGACY_TOKEN_FILE).read().strip()
        if v:
            return v
    raise TokenMissing(GUIDE)


def _auth_headers(extra=None):
    h = {"Content-Type": "application/json", "Authorization": "Bearer " + get_token()}
    if extra:
        h.update(extra)
    return h


def mcp_call(name, args, rid=1, timeout=60):
    body = json.dumps({"jsonrpc": "2.0", "id": rid, "method": "tools/call",
                       "params": {"name": name, "arguments": args}}).encode()
    req = urllib.request.Request(MCP, data=body,
                                 headers=_auth_headers({"Accept": "application/json, text/event-stream"}))
    try:
        raw = json.loads(urllib.request.urlopen(req, timeout=timeout).read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise TokenMissing("金手指授权已失效或未授权（需重新连接）。\n" + GUIDE) from None
        raise
    if "error" in raw:
        err = raw["error"] or {}
        # 未授权可能以 JSON-RPC error 形式返回（HTTP 仍为 200/401），需单独识别
        if err.get("code") == -32001 or "未授权" in str(err.get("message", "")) \
           or raw.get("error_code") == "missing_bearer_token":
            raise TokenMissing("金手指授权已失效或未授权（需重新连接）。\n" + GUIDE)
        raise RuntimeError(f"MCP error: {err}")
    res = raw.get("result", {})
    text = res["content"][0]["text"]
    if res.get("isError"):
        raise RuntimeError(f"工具执行失败：{text}")
    return json.loads(text)


class RestUnavailable(RuntimeError):
    """REST 侧不可用（外网环境要求 WorkBuddy 授权身份，不认 MCP Token）。
    非致命：所有能力都应能只靠 MCP 通道完成，REST 仅作可选增强。"""


def http_json(path, method="GET", payload=None, timeout=30, auth=True):
    """访问金手指 REST。⚠️ 2026-08-27 起外网环境 REST 全部 401
    （错误原文：「外网环境不支持企业网关身份，请完成 WorkBuddy 授权」），
    且**不认 MCP Token**。因此调用方必须把 REST 当"可选增强"，
    捕获 RestUnavailable 后降级到 MCP，绝不因 REST 挂掉而整体失败。"""
    data = json.dumps(payload).encode() if payload is not None else None
    headers = _auth_headers() if auth else {"Content-Type": "application/json"}
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=headers)
    try:
        return json.loads(urllib.request.urlopen(req, timeout=timeout).read().decode())
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            body = ""
            try:
                body = e.read().decode()[:200]
            except Exception:
                pass
            raise RestUnavailable(
                f"REST 接口 {path} 返回 {e.code}，本环境需 WorkBuddy 授权身份（MCP Token 不适用）。{body}"
            ) from None
        raise


def http_json_safe(path, method="GET", payload=None, timeout=30):
    """REST 可选调用：不可用时返回 None 而不抛，交由调用方降级到 MCP。"""
    try:
        return http_json(path, method, payload, timeout)
    except (RestUnavailable, TokenMissing, urllib.error.URLError, OSError):
        return None


class ProjectSourceMismatch(RuntimeError):
    """MCP 与 REST 的项目库不一致 —— 服务端问题，需金手指侧修复，不可绕过。"""


def ensure_project(name):
    """定位项目，返回 (project_id, created)。绝不猜近似名。

    **鉴权兜底策略（2026-08-27）**：
    - MCP 通道是唯一必需依赖（写复盘走它，读校验也走它，保持同源）。
    - REST 仅作可选增强；外网环境 REST 全部 401（要求 WorkBuddy 授权身份、不认 MCP Token），
      此时**自动降级为纯 MCP 模式**，不阻断主流程。
    - 只有「REST 可用且与 MCP 明显是两套库」时才抛 ProjectSourceMismatch。
    """
    mcp_items = (mcp_call("list_projects", {}, 2) or {}).get("projects", []) or []
    for p in mcp_items:
        if p.get("name") == name:
            return p["id"], False

    # REST 可选：拿不到就走纯 MCP 模式
    rest = http_json_safe("/api/projects")
    rest_items = (rest or {}).get("items", []) or []
    rest_hit = next((p for p in rest_items if p["name"] == name), None)

    if rest_hit and mcp_items:
        mcp_ids = {p.get("id") for p in mcp_items}
        rest_ids = {p["id"] for p in rest_items}
        if not (mcp_ids & rest_ids):
            raise ProjectSourceMismatch(
                f"项目「{name}」在金手指网页端（REST）存在（id={rest_hit['id']}），"
                f"但 MCP 通道查不到它。\n"
                f"MCP 可见项目：{[p.get('name') for p in mcp_items]}\n"
                f"→ 这是**金手指服务端 MCP 与网页端数据源不一致**（MCP 疑似仍连 mock 库），"
                f"艾投侧无法绕过，请让金手指把 MCP 接到真实项目库后重试。\n"
                f"（复盘已存本地，不会丢；修好后重跑同步即可。）")

    # 需要新建项目：MCP 无建项目能力，只能试 REST；REST 也不可用则明确报缺口
    created = http_json_safe("/api/projects", "POST", {"name": name})
    if not created or not created.get("id"):
        avail = [p.get("name") for p in mcp_items]
        raise ProjectSourceMismatch(
            f"金手指里没有项目「{name}」，而现在**无法自动新建**——\n"
            f"建项目只有 REST 接口，但本环境 REST 需要 WorkBuddy 授权身份（返回 401），MCP 侧没有建项目工具。\n"
            f"MCP 当前可见项目：{avail or '（无）'}\n"
            f"→ 请在金手指网页端先手动建好项目「{name}」，或改用已有项目名重跑。\n"
            f"（复盘已存本地，不会丢。）")

    recheck = (mcp_call("list_projects", {}, 3) or {}).get("projects", []) or []
    if mcp_items and not any(p.get("id") == created["id"] for p in recheck):
        raise ProjectSourceMismatch(
            f"已在网页端创建项目「{name}」(id={created['id']})，但 MCP 通道仍看不到它。\n"
            f"→ 金手指 MCP 与网页端数据源不一致，需服务端修复后重试。")
    return created["id"], True


def split_by_bytes(text, limit=CHUNK_LIMIT):
    """按 utf8 字节切片，保守估算 JSON 转义膨胀（×2）"""
    chunks, buf, blen = [], "", 0
    for ch in text:
        cost = len(ch.encode()) * 2
        if blen + cost > limit and buf:
            chunks.append(buf); buf, blen = ch, cost
        else:
            buf += ch; blen += cost
    if buf:
        chunks.append(buf)
    return chunks


def write_artifact(project, title, kind, payload, rid=10):
    return mcp_call("upsert_review_artifact", {
        "project_id": project, "title": title, "kind": kind, "payload": payload}, rid)


def sync(project_name, md_text=None, html_text=None, kind="final_review",
         title=None, metrics=None, intent=None, cron=None, extra=None):
    report = {"project": project_name, "written": [], "verified": {}, "warnings": []}

    pid, created = ensure_project(project_name)
    report["project_id"] = pid
    report["project_created"] = created

    # ---- 1. 复盘意图 ----
    if intent:
        r = mcp_call("upsert_review_intent",
                     {"project_id": pid, "payload": intent}, 11)
        report["written"].append({"type": "intent", "id": r.get("id")})

    # ---- 2. Markdown 正文（小体量，单条写） ----
    if md_text:
        p = {"source": "aitou", "format": "markdown", "content_md": md_text}
        if metrics: p["metrics"] = metrics
        if extra: p.update(extra)
        ser = len(json.dumps(p, ensure_ascii=False).encode())
        if ser > SAFE_SINGLE:
            report["warnings"].append(f"markdown payload {ser}B 超安全线，已分片")
            for i, ck in enumerate(split_by_bytes(md_text), 1):
                r = write_artifact(pid, f"{title}_正文分片{i}", "final_review_chunk",
                                   {"source": "aitou", "format": "md_chunk",
                                    "chunkIndex": i, "content_md_chunk": ck}, 20 + i)
                report["written"].append({"type": "md_chunk", "index": i, "id": r.get("id")})
        else:
            r = write_artifact(pid, title, kind, p, 12)
            report["written"].append({"type": "markdown", "id": r.get("id")})

    # ---- 3. HTML 报告（大体量，自动分片 + MD5） ----
    if html_text:
        md5 = hashlib.md5(html_text.encode()).hexdigest()
        ser_probe = len(json.dumps({"content_html": html_text}, ensure_ascii=False).encode())
        if ser_probe > SAFE_SINGLE:
            chunks = split_by_bytes(html_text)
            for i, ck in enumerate(chunks, 1):
                r = write_artifact(pid,
                                   f"{title}_HTML分片{i}of{len(chunks)}",
                                   "full_report_html_chunk",
                                   {"source": "aitou", "format": "html_chunk",
                                    "chunkIndex": i, "chunkTotal": len(chunks),
                                    "fullMd5": md5, "fullCharLen": len(html_text),
                                    "content_html_chunk": ck,
                                    "reassemble": "按 chunkIndex 升序拼接 content_html_chunk"}, 30 + i)
                report["written"].append({"type": "html_chunk", "index": i, "id": r.get("id")})
            report["html_md5"] = md5
            report["html_chunks"] = len(chunks)
        else:
            r = write_artifact(pid, title + "_HTML", "full_report_html",
                               {"source": "aitou", "format": "html",
                                "content_html": html_text, "fullMd5": md5}, 13)
            report["written"].append({"type": "html", "id": r.get("id")})

    # ---- 4. 复盘定时（默认关闭，符合"自动化默认不开"纪律） ----
    if cron:
        r = mcp_call("upsert_review_schedule", {
            "project_id": pid, "cron_expr": cron,
            "title": f"艾投·{project_name} 每日复盘日报", "enabled": False}, 14)
        report["written"].append({"type": "schedule", "id": r.get("id"), "enabled": False})

    # ---- 5. 强制回读校验（核心纪律：能 json.loads 才算成功） ----
    # 回读必须与写入同源（都走 MCP），否则两套库不一致时会误判成功/失败
    try:
        ctx = mcp_call("get_project_context", {"project_id": pid}, 5)
    except TokenMissing:
        raise
    except Exception:
        ctx = http_json_safe(f"/api/projects/{pid}") or {}  # REST 仅兜底，不可用则为空
    arts = (ctx.get("review") or {}).get("artifacts") or []
    ok_ids, bad_ids = [], []
    parts = {}
    for a in arts:
        try:
            pj = json.loads(a["payload_json"])
            ok_ids.append(a["id"])
            if pj.get("format") == "html_chunk" and pj.get("fullMd5") == report.get("html_md5"):
                parts[pj["chunkIndex"]] = pj["content_html_chunk"]
        except Exception:
            bad_ids.append(a["id"])
    report["verified"] = {"parsable": len(ok_ids), "truncated": len(bad_ids),
                          "truncated_ids": bad_ids}
    if html_text and parts:
        merged = "".join(parts[k] for k in sorted(parts))
        report["verified"]["html_md5_match"] = (
            hashlib.md5(merged.encode()).hexdigest() == report["html_md5"])
        report["verified"]["html_chars"] = len(merged)
    if bad_ids:
        report["warnings"].append(f"{len(bad_ids)} 条历史材料被截断（需页面清理）")

    report["view_api"] = f"{BASE}/api/projects/{pid}"
    report["view_note"] = ("该 REST 链接需 WorkBuddy 授权身份才能打开；"
                           "外网环境请用 MCP get_project_context(project_id) 查看。")
    report["auth_mode"] = "mcp_token" if any(os.environ.get(k) for k in ENV_KEYS) else "oauth_or_session"
    report["platform_url"] = BASE
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--project")
    ap.add_argument("--md"); ap.add_argument("--html")
    ap.add_argument("--kind", default="final_review")
    ap.add_argument("--title"); ap.add_argument("--metrics")
    ap.add_argument("--intent"); ap.add_argument("--cron")
    ap.add_argument("--check-token", action="store_true",
                    help="只检查 Token 是否已配置且有效，不写入任何内容")
    a = ap.parse_args()
    if not a.check_token and not a.project:
        ap.error("--project 为必填（除非只做 --check-token）")

    try:
        if a.check_token:
            # 必须打 MCP 通道校验：/api/me 在 FAT 环境不校验 Bearer，
            # 无效 Token 也会返回 200「本地访客」，用它检查等于没检查。
            probe = mcp_call("list_projects", {}, 1)
            me = http_json_safe("/api/me") or {}
            print(json.dumps({"token_ok": True,
                              "projects": probe.get("count"),
                              "display_name": me.get("display_name"),
                              "user_id": me.get("user_id"),
                              "channel": me.get("channel")}, ensure_ascii=False, indent=2))
            sys.exit(0)
        md = open(a.md, encoding="utf-8").read() if a.md else None
        ht = open(a.html, encoding="utf-8").read() if a.html else None
        out = sync(a.project, md, ht, a.kind,
                   a.title or f"艾投·复盘_{a.project}",
                   json.loads(a.metrics) if a.metrics else None,
                   json.loads(a.intent) if a.intent else None, a.cron)
        print(json.dumps(out, ensure_ascii=False, indent=2))
    except TokenMissing as e:
        # 不打堆栈，直接给用户能照做的引导
        print(json.dumps({"token_ok": False, "need_setup": True,
                          "guide": str(e)}, ensure_ascii=False, indent=2))
        sys.exit(2)
    except ProjectSourceMismatch as e:
        # 服务端数据源不一致：如实报，不假报成功、不静默降级
        print(json.dumps({"synced": False, "blocked_by": "goldfinger_server",
                          "reason": str(e)}, ensure_ascii=False, indent=2))
        sys.exit(3)
