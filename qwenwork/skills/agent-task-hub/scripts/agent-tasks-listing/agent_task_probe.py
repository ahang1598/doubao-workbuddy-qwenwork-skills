#!/usr/bin/env python3
"""agent_task_probe — 探测本机 coding agent CLI 的历史任务列表。

供千问办公 agent 调用。本脚本只读本地存档，不依赖 dws 的 auth 注入，
建议用 run_in_background 后台执行，避免长扫描阻塞其它任务。
stdout 只输出纯 JSON，日志一律走 stderr。

数据来源（本地会话存档，无需 agent 在线）：
  - qoder:     ~/.qoder/projects/<编码cwd>/<sessionId>.jsonl（含 transcript/ 子目录形态）
  - claudecode: ~/.claude/projects/<编码cwd>/<sessionId>.jsonl（与 qoder 同构）
  - qoderwork: ~/.qoderwork/projects/<编码cwd>/<sessionId>.jsonl（与 qoder 同构）
  - codex:     ~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl 与 ~/.codex/archived_sessions/

输出字段对齐 qwenwork.tasks，task-hub 可复用同一套去重与状态映射：
  chatId / title / status / createdAt / updatedAt / chatType / sourceChatId
额外附带探测侧扩展字段（agent / summary / cwd / messageCount / outputFiles / file），
不影响对齐消费。outputFiles 为任务产出的本地文件（写/编辑类工具调用提取，
list 只给路径，detail 附 exists 状态；codex 取 apply_patch，shell 重定向写入无法感知）。

用法：
  python3 agent_task_probe.py --list [--agent qoder|codex|claudecode|qoderwork|all] [--limit N] [--since-days N]
  python3 agent_task_probe.py --detail <chatId>
  python3 agent_task_probe.py --search <关键词> [--limit N]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROBE_VERSION = "1.0.0"
TITLE_MAX_LEN = 120
SUMMARY_MAX_LEN = 180

# codex rollout 开头注入的非真实用户输入（桌面端上下文、插件推荐等），
# 这些 payload.role 也是 "user"，必须过滤才能拿到真实任务 prompt。
CODEX_NOISE_RE = re.compile(
    r"^<(recommended_plugins|app-context|user_instructions|environment_context|"
    r"turn_context|attachments|instructions|user_instructions>)"
)

# qoder 首条 user 消息偶发的斜杠命令包装壳，剥壳取正文。
QODER_COMMAND_MSG_RE = re.compile(
    r"^<command-message>(?P<name>[^<]+)</command-message>\s*"
    r"(?:<command-name>[^<]*</command-name>\s*)?(?P<rest>.*)",
    re.DOTALL,
)

SYSTEM_REMINDER_RE = re.compile(r"<system-reminder>.*?</system-reminder>", re.DOTALL)


def log(msg: str) -> None:
    """日志统一走 stderr，保证 stdout 是纯 JSON。"""
    print(msg, file=sys.stderr)


def emit(payload: dict, code: int = 0) -> None:
    print(json.dumps(payload, ensure_ascii=False))
    sys.exit(code)


def emit_error(message: str, code: int = 1) -> None:
    log(f"错误：{message}")
    emit({"ok": False, "error": message}, code)


# ─── 通用工具 ────────────────────────────────────────────────


def normalize_ts(value) -> str | None:
    """归一化时间戳为 ISO8601 UTC 字符串。

    qoder 的 timestamp 混有 ISO 字符串与 epoch 毫秒两种形态；
    codex 一律 ISO。无法解析时返回 None。
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        # epoch 毫秒（qoder runtime-config 等记录）
        try:
            return datetime.fromtimestamp(value / 1000, tz=timezone.utc).isoformat()
        except (OverflowError, OSError, ValueError):
            return None
    text = str(value).strip()
    if not text:
        return None
    # Python 3.11 以下 fromisoformat 不认尾部 Z
    candidate = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        dt = datetime.fromisoformat(candidate)
    except ValueError:
        # 兜底：纯数字字符串按 epoch 毫秒处理
        if text.isdigit():
            return normalize_ts(int(text))
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def truncate_title(text: str, max_len: int = TITLE_MAX_LEN) -> str:
    one_line = " ".join(text.split())
    return one_line[:max_len] + "…" if len(one_line) > max_len else one_line


def extract_actual_request(text: str | None) -> str | None:
    """从 Codex/Qoder 存档的上下文包装里取真正的用户请求。"""
    if not text:
        return None
    text = SYSTEM_REMINDER_RE.sub("", text).strip()
    markers = (
        "## My request for Codex:",
        "## My request for Codex：",
        "## My request:",
        "## My request：",
        "## 我的请求:",
        "## 我的请求：",
    )
    for marker in markers:
        idx = text.rfind(marker)
        if idx >= 0:
            text = text[idx + len(marker):].strip()
            break
    # 附件/引用上下文经常出现在真实请求前；如果没有 My request 标记，
    # 至少不要把这些包装标题当作任务标题。
    noisy_prefixes = (
        "# Files mentioned by the user:",
        "## Referenced chats with Codex:",
        "The following is the Codex",
    )
    if any(text.startswith(prefix) for prefix in noisy_prefixes):
        parts = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        for part in reversed(parts):
            if not any(part.startswith(prefix) for prefix in noisy_prefixes):
                text = part
                break
    return text.strip() or None


def make_task_summary(agent_id: str, request_text: str, title: str) -> str:
    """本机 agent 的一句话摘要：优先表达任务意图，不用 cwd 充当摘要。"""
    source = extract_actual_request(request_text) or title
    first_line = next((line.strip() for line in source.splitlines() if line.strip()), title)
    return truncate_title(f"{agent_id}: {first_line}", SUMMARY_MAX_LEN)


def iter_jsonl(path: Path):
    """逐行解析 JSONL，损坏行跳过（本地存档偶发写一半）。"""
    try:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue
    except OSError as exc:
        log(f"读取失败 {path}: {exc}")


def walk_jsonl(root: Path, since: datetime | None = None):
    if not root.is_dir():
        return
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            if not name.endswith(".jsonl"):
                continue
            path = Path(dirpath) / name
            # 用文件 mtime 在 walk 阶段就跳过旧文件，避免全量解析
            if since is not None:
                try:
                    if path.stat().st_mtime < since.timestamp():
                        continue
                except OSError:
                    pass
            yield path


# ─── claude 系 collector（qoder / claudecode / qoderwork 同构）───

# 写/编辑类工具：其 input.file_path 即任务产出的本地文件。
# 各家工具名不同但都带 file_path 入参，按小写名匹配。
WRITE_TOOL_NAMES = {"write", "edit", "multiedit", "searchreplace", "notebookedit"}
# 单任务产出文件数上限（防异常会话拖慢输出）
OUTPUT_FILES_CAP = 200


def extract_write_tool_path(block: dict) -> str | None:
    """从 tool_use block 提取写/编辑类工具的目标文件路径。"""
    if block.get("type") != "tool_use":
        return None
    name = str(block.get("name") or "")
    if name.lower() not in WRITE_TOOL_NAMES:
        return None
    tool_input = block.get("input") or {}
    if not isinstance(tool_input, dict):
        return None
    path = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not path:
        return None
    return str(path).strip() or None

def extract_user_text(content) -> str | None:
    """提取 user 消息正文：兼容旧版字符串形态与新版 content block 列表形态
    （qoderwork 已切到 block 形态）。

    <system-reminder> 包装壳（环境信息注入）剥掉后判空；
    tool_result 类 block 无 text，自然返回 None。
    """
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        texts = [
            b.get("text", "")
            for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        ]
        text = "\n".join(t for t in texts if t)
    else:
        return None
    text = SYSTEM_REMINDER_RE.sub("", text).strip()
    return text or None


def parse_claude_family_session(path: Path, agent_id: str, chat_type: str | None) -> dict | None:
    """解析 claude 系会话存档（qoder/claudecode/qoderwork 同构）。

    chat_type 传 None 时走 qoder 默认启发式（按 cwd 区分 ide/cli）。
    """
    session_id = None
    cwd = None
    prompt = None
    started_at = None
    updated_at = None
    message_count = 0
    last_assistant = None
    output_files: list[str] = []
    output_seen: set[str] = set()

    for rec in iter_jsonl(path):
        ts = normalize_ts(rec.get("timestamp"))
        if ts:
            if started_at is None or ts < started_at:
                started_at = ts
            if updated_at is None or ts > updated_at:
                updated_at = ts

        rec_type = rec.get("type")
        if rec_type == "user":
            message = rec.get("message") or {}
            content = extract_user_text(message.get("content"))
            if not content:
                continue
            message_count += 1
            if prompt is None:
                prompt = content
                cwd = rec.get("cwd")
                session_id = rec.get("sessionId")
                started_at = normalize_ts(rec.get("timestamp")) or started_at
        elif rec_type == "assistant":
            message = rec.get("message") or {}
            content = message.get("content")
            if isinstance(content, str) and content.strip():
                last_assistant = content
            elif isinstance(content, list):
                texts = []
                for b in content:
                    if not isinstance(b, dict):
                        continue
                    if b.get("type") == "text" and b.get("text"):
                        texts.append(b["text"])
                    # 产出文件：写/编辑类 tool_use 的目标路径（保序去重）
                    fp = extract_write_tool_path(b)
                    if fp and fp not in output_seen and len(output_files) < OUTPUT_FILES_CAP:
                        output_seen.add(fp)
                        output_files.append(fp)
                if texts:
                    last_assistant = "\n".join(texts)

    if not prompt:
        return None

    # 部分早期 qoder 存档无 timestamp 记录，用文件 mtime 兜底，
    # 保证 createdAt/updatedAt 契约字段永远有值。
    if started_at is None and updated_at is None:
        try:
            mtime_iso = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
            started_at = updated_at = mtime_iso
        except OSError:
            pass

    clean_prompt = extract_actual_request(prompt) or prompt

    # 斜杠命令包装壳（如 <command-message>follow-builders</command-message>）剥壳取正文
    title_source = clean_prompt
    cmd_match = QODER_COMMAND_MSG_RE.match(prompt.strip())
    if cmd_match:
        rest = (cmd_match.group("rest") or "").strip()
        title_source = rest or f"/{cmd_match.group('name').strip()}"
    title = truncate_title(title_source)

    # 会话存档落盘即代表该轮已结束；本机探测不感知 IDE 内活跃会话，
    # 统一映射 completed，与 qwenwork 终态语义对齐。
    if chat_type is None:
        project_dir = path.parent.name
        resolved_chat_type = "ide" if "Application Support" in (cwd or project_dir) else "cli"
    else:
        resolved_chat_type = chat_type

    return {
        "chatId": f"{agent_id}:{session_id or path.stem}",
        "title": title,
        "status": "completed",
        "createdAt": started_at or updated_at,
        "updatedAt": updated_at or started_at,
        "chatType": resolved_chat_type,
        "sourceChatId": session_id or path.stem,
        # ── 探测侧扩展字段（不影响对齐消费）──
        "agent": agent_id,
        "summary": make_task_summary(agent_id, title_source, title),
        "cwd": cwd,
        "messageCount": message_count,
        "file": str(path),
        "_prompt": prompt,
        "_lastAssistant": last_assistant,
        "_outputFiles": output_files,
    }


def dedup_by_chat_id(tasks: list[dict]) -> list[dict]:
    """同一 chatId 保留 updatedAt 最新的一条。

    重复来源：qoder resume 会在多个项目目录留同 sessionId 副本；
    codex resume 的 fork 文件 session_meta 仍写旧 session_id。
    """
    best: dict[str, dict] = {}
    for task in tasks:
        prev = best.get(task["chatId"])
        if prev is None or (task.get("updatedAt") or "") > (prev.get("updatedAt") or ""):
            best[task["chatId"]] = task
    return list(best.values())


UUID_TAIL_RE = re.compile(r"([0-9a-f]{8}(?:-[0-9a-f]{4,})+)$")


def make_claude_family_collector(agent_id: str, root: Path, chat_type: str | None):
    def collect(since: datetime | None = None) -> list[dict]:
        tasks = []
        for path in walk_jsonl(root, since):
            task = parse_claude_family_session(path, agent_id, chat_type)
            if task:
                tasks.append(task)
        log(f"{agent_id}: 收集到 {len(tasks)} 个任务（{root}）")
        return tasks

    return collect


collect_qoder = make_claude_family_collector("qoder", Path.home() / ".qoder" / "projects", None)
collect_claudecode = make_claude_family_collector("claudecode", Path.home() / ".claude" / "projects", "cli")
collect_qoderwork = make_claude_family_collector("qoderwork", Path.home() / ".qoderwork" / "projects", "agent")


# ─── codex collector ─────────────────────────────────────────

# codex 的文件产出集中在 apply_patch（custom_tool_call）；shell 重定向写入
# 无法从存档可靠还原，属已知盲区。
CODEX_PATCH_FILE_RE = re.compile(
    r"^\*\*\* (?:Add File|Update File|Delete File): (.+?)\s*$"
)
CODEX_PATCH_MOVE_RE = re.compile(r"^\*\*\* Move File: (.+?) to (.+?)\s*$")


def extract_codex_patch_files(patch_text: str) -> list[str]:
    """从 apply_patch 补丁文本提取目标文件（Add/Update 与 Move 的目标端；
    Delete 不算产出）。"""
    files: list[str] = []
    for line in str(patch_text).splitlines():
        m = CODEX_PATCH_MOVE_RE.match(line)
        if m:
            files.append(m.group(2).strip())
            continue
        m = CODEX_PATCH_FILE_RE.match(line)
        if m and not line.startswith("*** Delete File:"):
            files.append(m.group(1).strip())
    return files


def parse_codex_session(path: Path) -> dict | None:
    session_id = None
    cwd = None
    started_at = None
    updated_at = None
    source = None
    originator = None
    prompt = None
    message_count = 0
    last_assistant = None
    output_files: list[str] = []
    output_seen: set[str] = set()

    for rec in iter_jsonl(path):
        ts = normalize_ts(rec.get("timestamp"))
        if ts:
            updated_at = ts if updated_at is None or ts > updated_at else ts

        rec_type = rec.get("type")
        if rec_type == "session_meta":
            payload = rec.get("payload") or {}
            session_id = payload.get("session_id") or payload.get("id")
            cwd = payload.get("cwd")
            started_at = normalize_ts(payload.get("timestamp")) or ts
            source = payload.get("source")
            originator = payload.get("originator")
            continue

        payload = rec.get("payload") if rec_type == "response_item" else None
        if not isinstance(payload, dict):
            continue

        # 产出文件：apply_patch 补丁里的 Add/Update/Move 目标，相对路径按会话 cwd 解析
        if payload.get("type") == "custom_tool_call" and payload.get("name") == "apply_patch":
            for fp in extract_codex_patch_files(payload.get("input") or ""):
                resolved = fp if os.path.isabs(fp) else os.path.normpath(os.path.join(cwd or "", fp))
                if resolved not in output_seen and len(output_files) < OUTPUT_FILES_CAP:
                    output_seen.add(resolved)
                    output_files.append(resolved)
            continue

        if payload.get("type") != "message":
            continue
        role = payload.get("role")
        text = "".join(
            c.get("text", "")
            for c in payload.get("content") or []
            if isinstance(c, dict) and isinstance(c.get("text"), str)
        ).strip()
        if not text:
            continue

        if role == "user":
            message_count += 1
            clean_text = extract_actual_request(text)
            if clean_text and re.match(r"^\[\d+\]\s+tool\s+", clean_text):
                continue
            if prompt is None and clean_text and not CODEX_NOISE_RE.match(text):
                prompt = clean_text
        elif role == "assistant":
            last_assistant = text

    if not prompt:
        return None

    # 文件名才是权威 session 标识：resume 产生的 fork 文件里 session_meta
    # 仍写旧 session_id，直接采信会导致同一任务多文件重复。
    m = UUID_TAIL_RE.search(path.stem)
    file_session_id = m.group(1) if m else path.stem
    session_id = file_session_id

    # chatType 按来源映射：exec=程序分派、vscode=IDE、桌面端归 desktop
    if source == "exec":
        chat_type = "agent"
    elif source == "vscode":
        chat_type = "ide"
    elif originator and "Desktop" in str(originator):
        chat_type = "desktop"
    else:
        chat_type = "cli"

    return {
        "chatId": f"codex:{session_id}",
        "title": truncate_title(prompt),
        "status": "completed",
        "createdAt": started_at or updated_at,
        "updatedAt": updated_at or started_at,
        "chatType": chat_type,
        "sourceChatId": session_id,
        # ── 探测侧扩展字段 ──
        "agent": "codex",
        "summary": make_task_summary("codex", prompt, truncate_title(prompt)),
        "cwd": cwd,
        "source": source,
        "messageCount": message_count,
        "file": str(path),
        "_prompt": prompt,
        "_lastAssistant": last_assistant,
        "_outputFiles": output_files,
    }


def collect_codex(since: datetime | None = None) -> list[dict]:
    codex_home = Path.home() / ".codex"
    tasks = []
    seen_files: set[Path] = set()
    for root in (codex_home / "sessions", codex_home / "archived_sessions"):
        for path in walk_jsonl(root, since):
            resolved = path.resolve()
            if resolved in seen_files:
                continue
            seen_files.add(resolved)
            task = parse_codex_session(path)
            if task:
                tasks.append(task)
    log(f"codex: 收集到 {len(tasks)} 个任务（{codex_home}/sessions + archived_sessions）")
    return tasks


COLLECTORS = {
    "qoder": collect_qoder,
    "codex": collect_codex,
    "claudecode": collect_claudecode,
    "qoderwork": collect_qoderwork,
}


# ─── 子命令实现 ───────────────────────────────────────────────


def collect_all(agent: str, since: datetime | None = None) -> list[dict]:
    names = list(COLLECTORS) if agent == "all" else [agent]
    tasks: list[dict] = []
    for name in names:
        tasks.extend(dedup_by_chat_id(COLLECTORS[name](since)))
    tasks.sort(key=lambda t: t.get("updatedAt") or "", reverse=True)
    return tasks


def strip_internal(task: dict, full: bool = False) -> dict:
    """去掉下划线内部字段；full=False 时同步裁剪超长正文。

    outputFiles：list 形态只给路径数组；detail（full=True）附磁盘存在性，
    便于消费方区分"任务产出过"与"现在还在"。
    """
    out = {k: v for k, v in task.items() if not k.startswith("_")}
    raw_files = task.get("_outputFiles") or []
    if full:
        out["prompt"] = task.get("_prompt")
        out["lastAssistant"] = task.get("_lastAssistant")
        out["outputFiles"] = [
            {"path": fp, "exists": Path(os.path.expanduser(fp)).exists()}
            for fp in raw_files
        ]
    else:
        out["outputFiles"] = list(raw_files)
    return out


def within_since(task: dict, since: datetime | None) -> bool:
    if since is None:
        return True
    ts = task.get("updatedAt") or task.get("createdAt")
    if not ts:
        return False
    try:
        dt = datetime.fromisoformat(ts)
    except ValueError:
        return False
    return dt >= since


def cmd_list(args) -> None:
    since = None
    if args.since_days and args.since_days > 0:
        since = datetime.now(timezone.utc) - timedelta(days=args.since_days)
    tasks = collect_all(args.agent, since)
    if since is not None:
        tasks = [t for t in tasks if within_since(t, since)]
    total = len(tasks)
    if args.limit and args.limit > 0:
        tasks = tasks[: args.limit]
    emit({
        "ok": True,
        "command": "list",
        "agent": args.agent,
        "total": total,
        "returned": len(tasks),
        "tasks": [strip_internal(t) for t in tasks],
    })


def cmd_detail(args) -> None:
    wanted = args.chat_id
    # 允许传裸 sessionId，自动补前缀匹配
    agents = list(COLLECTORS)
    if ":" in wanted:
        prefix, _ = wanted.split(":", 1)
        if prefix in COLLECTORS:
            agents = [prefix]
    for name in agents:
        for task in COLLECTORS[name]():
            if task["chatId"] == wanted or task["sourceChatId"] == wanted:
                emit({"ok": True, "command": "detail", "task": strip_internal(task, full=True)})
    emit_error(f"未找到任务：{wanted}", code=2)


def cmd_search(args) -> None:
    keyword = args.keyword.strip().lower()
    if not keyword:
        emit_error("--search 关键词不能为空")
    tasks = collect_all(args.agent)
    hits = []
    for task in tasks:
        haystack = " ".join(
            str(task.get(k) or "") for k in ("title", "_prompt", "cwd")
        ).lower()
        if keyword in haystack:
            hits.append(task)
    total = len(hits)
    if args.limit and args.limit > 0:
        hits = hits[: args.limit]
    emit({
        "ok": True,
        "command": "search",
        "keyword": args.keyword,
        "agent": args.agent,
        "total": total,
        "returned": len(hits),
        "tasks": [strip_internal(t) for t in hits],
    })


# ─── 入口 ────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent_task_probe.py",
        description="探测本机 coding agent 历史任务（stdout 纯 JSON，日志走 stderr）",
    )
    parser.add_argument("--version", action="version", version=f"agent_task_probe {PROBE_VERSION}")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list", action="store_true", help="列全量任务")
    group.add_argument("--detail", metavar="CHAT_ID", dest="chat_id", help="拉单条任务详情")
    group.add_argument("--search", metavar="KEYWORD", dest="keyword", help="按关键词搜任务")
    parser.add_argument(
        "--agent", choices=["qoder", "codex", "claudecode", "qoderwork", "all"], default="all",
        help="限定探测的 agent（默认 all）",
    )
    parser.add_argument("--limit", type=int, default=0, help="最多返回条数（0=不限）")
    parser.add_argument("--since-days", type=int, default=0, help="只返回最近 N 天（仅 --list）")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.list:
        cmd_list(args)
    elif args.chat_id:
        cmd_detail(args)
    elif args.keyword is not None:
        cmd_search(args)


if __name__ == "__main__":
    main()
