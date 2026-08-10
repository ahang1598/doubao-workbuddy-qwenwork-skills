#!/usr/bin/env python3
"""Runtime gatekeeper for Doubao Novel Writing Feishu-only delivery.

This script enforces a deterministic workflow so Doubao Novel Writing cannot end in
chat-only output or a pseudo document claim.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WORKFLOW_DIR = ROOT / ".workflow"
STAGES = ("brief", "draft", "image", "document-delivery")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def emit(payload: dict[str, Any], code: int = 0) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    raise SystemExit(code)


def wf_path(args: argparse.Namespace) -> Path:
    return Path(args.workflow).resolve()


def resolve_existing_path(path_value: str, wf: Path) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    candidates = [Path.cwd() / path, ROOT / path, wf / path]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return ROOT / path


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        emit({"status": "blocked", "blocked": "MISSING_FILE", "path": str(path)}, 2)
    except json.JSONDecodeError as exc:
        emit({"status": "blocked", "blocked": "INVALID_JSON", "path": str(path), "message": str(exc)}, 2)
    if not isinstance(data, dict):
        emit({"status": "blocked", "blocked": "JSON_MUST_BE_OBJECT", "path": str(path)}, 2)
    return data


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def state_file(wf: Path) -> Path:
    return wf / "state.json"


def load_state(wf: Path) -> dict[str, Any]:
    if not state_file(wf).exists():
        return {"current_stage": "not-initialized", "completed": [], "updated_at": None}
    return load_json(state_file(wf))


def save_state(wf: Path, state: dict[str, Any]) -> None:
    state["updated_at"] = now_iso()
    save_json(state_file(wf), state)


def norm(value: Any) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value).strip().lower()


def require_fields(data: dict[str, Any], required: dict[str, str]) -> list[str]:
    failures: list[str] = []
    for key, expected in required.items():
        if key not in data:
            failures.append(f"missing {key}")
        elif norm(data[key]) != expected:
            failures.append(f"{key} must be {expected!r}, got {data[key]!r}")
    return failures


def check_brief(data: dict[str, Any], wf: Path) -> list[str]:
    failures = []
    for field in ("task_type", "deliverable", "title", "user_intent"):
        if not str(data.get(field, "")).strip():
            failures.append(f"brief: missing {field}")
    if norm(data.get("deliverable")) != "feishu_doc":
        failures.append("brief: deliverable must be feishu_doc")
    return failures


def check_draft(data: dict[str, Any], wf: Path) -> list[str]:
    failures = require_fields(data, {"ready_for_doc": "yes"})
    for field in ("title", "content_path", "task_type", "core_section"):
        if not str(data.get(field, "")).strip():
            failures.append(f"draft_handoff: missing {field}")
    core = str(data.get("core_section", ""))
    if core not in {"可复制正文", "可复制方案"}:
        failures.append("draft_handoff: core_section must be 可复制正文 or 可复制方案")
    content_path = data.get("content_path")
    if content_path:
        resolved = resolve_existing_path(str(content_path), wf)
        if not resolved.exists():
            failures.append(f"draft_handoff: content_path does not exist: {content_path}")
    return failures


def check_image(data: dict[str, Any], wf: Path) -> list[str]:
    failures = require_fields(data, {"image_insertable": "yes"})
    if not str(data.get("image_source", "")).strip():
        failures.append("image_handoff: missing image_source")
    if not str(data.get("placement", "")).strip():
        failures.append("image_handoff: missing placement")
    if norm(data.get("image_in_body_plan", "yes")) not in {"yes", "pass"}:
        failures.append("image_handoff: image must be planned for document body, not attachment only")
    return failures


def check_doc(data: dict[str, Any], wf: Path) -> list[str]:
    failures = require_fields(data, {"doc_created": "yes", "fetched_back": "pass", "image_in_doc": "yes", "ready_for_final": "yes"})
    for field in ("doc_id", "doc_url", "doc_title"):
        if not str(data.get(field, "")).strip():
            failures.append(f"doc_handoff: missing {field}")
    if "larkoffice.com" not in str(data.get("doc_url", "")) and "feishu.cn" not in str(data.get("doc_url", "")):
        failures.append("doc_handoff: doc_url must be a Feishu/Lark document URL")
    if norm(data.get("chat_fulltext_output", "no")) not in {"no", "false"}:
        failures.append("doc_handoff: final reply must not paste full text in chat")
    return failures


CHECKS = {
    "brief": check_brief,
    "draft": check_draft,
    "image": check_image,
    "document-delivery": check_doc,
}


def cmd_init(args: argparse.Namespace) -> None:
    wf = wf_path(args)
    wf.mkdir(parents=True, exist_ok=True)
    state = {"topic": args.topic, "current_stage": "brief", "completed": [], "updated_at": now_iso()}
    save_state(wf, state)
    emit({"status": "ok", "workflow": str(wf), "current_stage": "brief"})


def cmd_enter(args: argparse.Namespace) -> None:
    wf = wf_path(args)
    stage = args.stage
    state = load_state(wf)
    completed = set(state.get("completed", []))
    prereq = {
        "brief": [],
        "draft": ["brief"],
        "image": ["brief", "draft"],
        "document-delivery": ["brief", "draft", "image"],
    }[stage]
    missing = [s for s in prereq if s not in completed]
    if missing:
        emit({"status": "blocked", "blocked": "NEED_UPSTREAM_STAGE", "stage": stage, "missing": missing}, 1)
    state["current_stage"] = stage
    save_state(wf, state)
    emit({"status": "ok", "stage": stage})


def cmd_accept(args: argparse.Namespace) -> None:
    wf = wf_path(args)
    stage = args.stage
    data = load_json(Path(args.handoff).resolve())
    failures = CHECKS[stage](data, wf)
    if failures:
        emit({"status": "blocked", "blocked": "INVALID_HANDOFF", "stage": stage, "failures": failures}, 1)
    target = wf / f"{stage.replace('-', '_')}_handoff.json"
    save_json(target, data)
    state = load_state(wf)
    completed = list(dict.fromkeys([*state.get("completed", []), stage]))
    state["completed"] = completed
    state["current_stage"] = "done" if stage == "document-delivery" else STAGES[STAGES.index(stage) + 1]
    save_state(wf, state)
    emit({"status": "ok", "stage": stage, "saved": str(target), "next_stage": state["current_stage"]})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Doubao Novel Writing Feishu-only workflow gatekeeper")
    parser.add_argument("--workflow", default=str(DEFAULT_WORKFLOW_DIR))
    sub = parser.add_subparsers(dest="command", required=True)
    p_init = sub.add_parser("init")
    p_init.add_argument("--topic", required=True)
    p_init.set_defaults(func=cmd_init)
    p_enter = sub.add_parser("enter")
    p_enter.add_argument("stage", choices=STAGES)
    p_enter.set_defaults(func=cmd_enter)
    p_accept = sub.add_parser("accept")
    p_accept.add_argument("stage", choices=STAGES)
    p_accept.add_argument("handoff")
    p_accept.set_defaults(func=cmd_accept)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
