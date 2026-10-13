#!/usr/bin/env python3
"""agent_discovery — 本机 coding agent 探测程序。

供 skill 在同步前调用：探测本机装了哪些 agent CLI、各自的本地任务存档
规模与最近活跃时间，输出供 skill 提示用户"选择同步哪些 agent"。

执行建议：本脚本只读本地文件与 CLI 版本探测，不依赖 dws 的 auth 注入，
建议 run_in_background 后台执行，避免阻塞其它任务。stdout 只输出纯 JSON，
日志一律 stderr。

探测维度（每个 agent）：
  1. 二进制是否在 PATH（含常见 fallback 名）
  2. 版本号（best-effort，<bin> --version，超时即弃）
  3. 本地任务存档：存档根目录是否存在、会话文件数、最近活跃时间
  4. syncable = 有可解析存档（probe_support 的 agent）或至少装了 CLI
  5. probe_support = agent_task_probe.py 当前已支持 --list/--detail/--search

用法：
  python3 agent_discovery.py                 # 探测全部已知 agent
  python3 agent_discovery.py --no-version    # 跳过版本探测（更快）
  python3 agent_discovery.py --agent qoder codex
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

DISCOVERY_VERSION = "1.0.0"
VERSION_TIMEOUT_SEC = 8
# find 等价遍历的会话文件数上限（防止异常巨型目录拖慢探测）
MAX_SESSION_FILES = 50_000

# PATH 之外常见安装位：agent 装在这些位置时 shell PATH 未必包含
# （如 npm 全局目录未入 PATH），仅凭 shutil.which 会漏报。
EXTRA_BIN_DIRS = [
    "~/.local/bin",
    "~/.npm-global/bin",
    "/opt/homebrew/bin",
    "/usr/local/bin",
]


def log(msg: str) -> None:
    print(msg, file=sys.stderr)


def emit(payload: dict, code: int = 0) -> None:
    print(json.dumps(payload, ensure_ascii=False))
    sys.exit(code)


# ─── agent 注册表 ─────────────────────────────────────────────
#
# 新增一个 agent = 在 AGENT_REGISTRY 加一行。
#   bins        PATH 探测用的可执行名（按序取第一个命中的）
#   storage_roots 本地任务存档根目录（~ 展开），可多个
#   probe_support agent_task_probe.py 是否已支持其任务解析
#   note        存档/安装形态的补充说明（给用户看的）

AGENT_REGISTRY: list[dict] = [
    {
        "id": "qoder",
        "name": "Qoder CLI",
        "bins": ["qodercli", "qoder"],
        "storage_roots": ["~/.qoder/projects"],
        "probe_support": True,
        "note": "会话存档 ~/.qoder/projects/<编码cwd>/<sessionId>.jsonl",
    },
    {
        "id": "codex",
        "name": "OpenAI Codex",
        "bins": ["codex"],
        "storage_roots": ["~/.codex/sessions", "~/.codex/archived_sessions"],
        "probe_support": True,
        "note": "会话存档 ~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl",
    },
    {
        "id": "claudecode",
        "name": "Claude Code",
        "bins": ["claude"],
        "storage_roots": ["~/.claude/projects"],
        "probe_support": True,
        "note": "存档与 qoder 同构（projects/<编码cwd>/<sessionId>.jsonl）",
    },
    {
        "id": "qoderwork",
        "name": "QoderWork（桌面端）",
        "bins": [],
        "storage_roots": ["~/.qoderwork/projects"],
        "probe_support": True,
        "note": "桌面端，无 PATH 二进制；以存档目录存在判定，存档与 qoder 同构",
    },
    {
        "id": "qwen",
        "name": "Qwen Code CLI",
        "bins": ["qwen"],
        "storage_roots": [],
        "probe_support": False,
        "note": "本机 ~/.qwen 未见会话存档（jsonl=0），任务数据可能在云端",
    },
    {
        "id": "qwenwork",
        "name": "千问办公",
        "bins": [],
        "storage_roots": [],
        "probe_support": False,
        "note": "桌面应用 + 本地 MCP 服务，任务经 qwenwork_task_* 接口获取，不走本地存档",
    },
    {
        "id": "gemini",
        "name": "Gemini CLI",
        "bins": ["gemini"],
        "storage_roots": ["~/.gemini"],
        "probe_support": False,
        "note": "",
    },
    {
        "id": "opencode",
        "name": "OpenCode",
        "bins": ["opencode"],
        "storage_roots": ["~/.local/share/opencode", "~/.opencode"],
        "probe_support": False,
        "note": "",
    },
    {
        "id": "codebuddy",
        "name": "CodeBuddy",
        "bins": ["codebuddy"],
        "storage_roots": ["~/.codebuddy"],
        "probe_support": False,
        "note": "",
    },
]


# ─── 探测原语 ─────────────────────────────────────────────────


def resolve_binary(bins: list[str]) -> str | None:
    """先查 PATH，未命中再扫常见安装位（兼容 PATH 未配全的环境）。"""
    for name in bins:
        path = shutil.which(name)
        if path:
            return path
    for dir_template in EXTRA_BIN_DIRS:
        directory = Path(os.path.expanduser(dir_template))
        for name in bins:
            candidate = directory / name
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return str(candidate)
    return None


def probe_version(cmd_path: str) -> str | None:
    """best-effort 版本探测：失败/超时返回 None，不影响整体探测。"""
    try:
        proc = subprocess.run(
            [cmd_path, "--version"],
            capture_output=True,
            text=True,
            timeout=VERSION_TIMEOUT_SEC,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        log(f"  版本探测失败 {cmd_path}: {type(exc).__name__}")
        return None
    out = (proc.stdout or proc.stderr or "").strip()
    # 只取第一行，防止 help 文本污染
    return out.splitlines()[0][:200] if out else None


def scan_storage(roots: list[str]) -> dict:
    """统计存档根目录下的会话文件数与最近活跃时间。

    会话文件判定：*.jsonl（各主流 CLI 的会话存档格式）。
    只数文件与取 mtime，不做内容解析（那是 agent_task_probe.py 的职责）。
    """
    resolved_roots = [Path(os.path.expanduser(r)) for r in roots]
    existing = [r for r in resolved_roots if r.is_dir()]
    if not existing:
        return {
            "exists": False,
            "roots": roots,
            "sessionFiles": 0,
            "latestActivity": None,
        }

    count = 0
    latest_mtime = 0.0
    for root in existing:
        for dirpath, _dirnames, filenames in os.walk(root):
            for name in filenames:
                if not name.endswith(".jsonl"):
                    continue
                count += 1
                try:
                    mtime = os.path.getmtime(os.path.join(dirpath, name))
                    latest_mtime = max(latest_mtime, mtime)
                except OSError:
                    pass
                if count >= MAX_SESSION_FILES:
                    log(f"  存档文件数超过 {MAX_SESSION_FILES}，停止计数：{root}")
                    break
            if count >= MAX_SESSION_FILES:
                break

    latest = None
    if latest_mtime > 0:
        latest = datetime.fromtimestamp(latest_mtime, tz=timezone.utc).isoformat()

    return {
        "exists": True,
        "roots": [str(r) for r in existing],
        "sessionFiles": count,
        "latestActivity": latest,
    }


# ─── 单 agent 探测 ────────────────────────────────────────────


def discover_agent(spec: dict, with_version: bool) -> dict:
    cmd_path = resolve_binary(spec["bins"]) if spec["bins"] else None
    version = None
    if cmd_path and with_version:
        version = probe_version(cmd_path)

    storage = scan_storage(spec["storage_roots"]) if spec["storage_roots"] else {
        "exists": False,
        "roots": spec["storage_roots"],
        "sessionFiles": 0,
        "latestActivity": None,
    }

    installed = cmd_path is not None
    has_archive = storage["exists"] and storage["sessionFiles"] > 0
    # 可同步 = probe 已支持其存档解析；仅装了 CLI 但无解析支持时标注 partial
    if spec["probe_support"] and has_archive:
        syncable = True
        sync_level = "full"
    elif has_archive:
        syncable = True
        sync_level = "archive-only"
    elif installed:
        syncable = True
        sync_level = "cli-only"
    else:
        syncable = False
        sync_level = "none"

    return {
        "id": spec["id"],
        "name": spec["name"],
        "installed": installed,
        "cmd": cmd_path,
        "version": version,
        "storage": storage,
        "probeSupport": spec["probe_support"],
        "syncable": syncable,
        "syncLevel": sync_level,
        "note": spec["note"] or None,
    }


# ─── 入口 ────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="agent_discovery.py",
        description="探测本机 coding agent 安装与任务存档情况（stdout 纯 JSON，日志走 stderr）",
    )
    parser.add_argument("--version", action="version", version=f"agent_discovery {DISCOVERY_VERSION}")
    parser.add_argument("--agent", nargs="*", metavar="ID", help="只探测指定 agent（id 列表）")
    parser.add_argument("--no-version", action="store_true", help="跳过版本探测（提速）")
    args = parser.parse_args()

    registry = AGENT_REGISTRY
    if args.agent:
        known = {s["id"] for s in AGENT_REGISTRY}
        unknown = [a for a in args.agent if a not in known]
        if unknown:
            log(f"错误：未知 agent id: {', '.join(unknown)}（可选：{', '.join(sorted(known))}）")
            emit({"ok": False, "code": 1, "message": f"未知 agent id: {', '.join(unknown)}"}, code=1)
        registry = [s for s in AGENT_REGISTRY if s["id"] in set(args.agent)]

    agents = []
    for spec in registry:
        log(f"探测 {spec['id']} ...")
        agents.append(discover_agent(spec, with_version=not args.no_version))

    # 推荐顺序：probe 全支持 > 有存档 > 仅 CLI；同级按会话文件数降序。
    level_rank = {"full": 0, "archive-only": 1, "cli-only": 2, "none": 3}
    agents.sort(key=lambda a: (
        level_rank[a["syncLevel"]],
        -a["storage"]["sessionFiles"],
    ))

    syncable_ids = [a["id"] for a in agents if a["syncable"]]
    summary = {
        "probed": len(agents),
        "installed": sum(1 for a in agents if a["installed"]),
        "withArchive": sum(1 for a in agents if a["storage"]["sessionFiles"] > 0),
        "syncable": len(syncable_ids),
        "syncableIds": syncable_ids,
        "totalSessionFiles": sum(a["storage"]["sessionFiles"] for a in agents),
        # probe 已完整支持、可立即同步的 agent —— skill 默认选项直接用这个
        "recommendedDefaults": [a["id"] for a in agents if a["syncLevel"] == "full"],
    }

    emit({"ok": True, "version": DISCOVERY_VERSION, "agents": agents, "summary": summary})


if __name__ == "__main__":
    main()
