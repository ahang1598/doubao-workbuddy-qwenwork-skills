#!/usr/bin/env python3
"""Final validator for Doubao Novel Writing Feishu document delivery.

Run before replying to the user:
    python scripts/validate_run.py --require final

It fails closed when Doubao Novel Writing has not created and verified a Feishu/Lark Doc.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WORKFLOW_DIR = ROOT / ".workflow"
REQUIRED_STAGES = ("brief", "draft", "image", "document-delivery")


def emit(payload: dict[str, Any], code: int = 0) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    raise SystemExit(code)


def load_json(path: Path, failures: list[str]) -> dict[str, Any] | None:
    if not path.exists():
        failures.append(f"missing file: {path}")
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        failures.append(f"invalid JSON: {path} ({exc})")
        return None
    if not isinstance(data, dict):
        failures.append(f"JSON must be object: {path}")
        return None
    return data


def norm(value: Any) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value).strip().lower()


def resolve_existing_path(path_value: str, wf: Path) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    candidates = [Path.cwd() / path, ROOT / path, wf / path]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return ROOT / path


def check_state(wf: Path, failures: list[str]) -> None:
    state = load_json(wf / "state.json", failures)
    if not state:
        return
    completed = state.get("completed")
    if not isinstance(completed, list):
        failures.append("state.completed must be a list")
        completed = []
    for stage in REQUIRED_STAGES:
        if stage not in completed:
            failures.append(f"state.completed missing stage: {stage}")
    if state.get("current_stage") != "done":
        failures.append(f"state.current_stage must be 'done', got {state.get('current_stage')!r}")


def require(data: dict[str, Any] | None, label: str, rules: dict[str, str], failures: list[str]) -> None:
    if not data:
        return
    for key, expected in rules.items():
        if key not in data:
            failures.append(f"{label}: missing {key}")
        elif norm(data[key]) != expected:
            failures.append(f"{label}: {key} must be {expected!r}, got {data[key]!r}")


def check_brief(wf: Path, failures: list[str]) -> None:
    data = load_json(wf / "brief_handoff.json", failures)
    if not data:
        return
    for field in ("task_type", "deliverable", "title", "user_intent"):
        if not str(data.get(field, "")).strip():
            failures.append(f"brief_handoff: {field} must be non-empty")
    if norm(data.get("deliverable")) != "feishu_doc":
        failures.append("brief_handoff: deliverable must be feishu_doc")


def check_draft(wf: Path, failures: list[str]) -> None:
    data = load_json(wf / "draft_handoff.json", failures)
    require(data, "draft_handoff", {"ready_for_doc": "yes"}, failures)
    if not data:
        return
    title = str(data.get("title", "")).strip()
    content_path = str(data.get("content_path", "")).strip()
    core = str(data.get("core_section", "")).strip()
    if not title:
        failures.append("draft_handoff: title must be non-empty")
    if core not in {"可复制正文", "可复制方案"}:
        failures.append("draft_handoff: core_section must be 可复制正文 or 可复制方案")
    if not content_path:
        failures.append("draft_handoff: content_path must be non-empty")
    else:
        path = resolve_existing_path(content_path, wf)
        if not path.exists():
            failures.append(f"draft_handoff: content_path does not exist: {content_path}")
        else:
            text = path.read_text(encoding="utf-8-sig")
            if core and core not in text:
                failures.append(f"draft content missing required core section: {core}")
            if "可复制使用版" in text or "核心设定与人物关系" in text:
                failures.append("draft content contains banned section for正文类任务")
            if "自检" in text or "质量门禁" in text or "检查清单" in text:
                failures.append("draft content must not expose internal checks")


def check_image(wf: Path, failures: list[str]) -> None:
    data = load_json(wf / "image_handoff.json", failures)
    require(data, "image_handoff", {"image_insertable": "yes"}, failures)
    if not data:
        return
    if not str(data.get("image_source", "")).strip():
        failures.append("image_handoff: image_source must be non-empty")
    if norm(data.get("image_in_body_plan", "yes")) not in {"yes", "pass"}:
        failures.append("image_handoff: image must be planned for document body, not attachment only")


def check_doc(wf: Path, failures: list[str]) -> None:
    data = load_json(wf / "document_delivery_handoff.json", failures)
    require(
        data,
        "doc_handoff",
        {"doc_created": "yes", "fetched_back": "pass", "image_in_doc": "yes", "ready_for_final": "yes"},
        failures,
    )
    if not data:
        return
    url = str(data.get("doc_url", "")).strip()
    title = str(data.get("doc_title", "")).strip()
    if not title:
        failures.append("doc_handoff: doc_title must be non-empty")
    if not url:
        failures.append("doc_handoff: doc_url must be non-empty")
    elif not re.search(r"https?://[^\s]*(larkoffice\.com|feishu\.cn)/", url):
        failures.append("doc_handoff: doc_url must be a Feishu/Lark document URL")
    if norm(data.get("chat_fulltext_output", "no")) not in {"no", "false"}:
        failures.append("doc_handoff: final reply must not paste full text in chat")


def validate(args: argparse.Namespace) -> None:
    wf = Path(args.workflow).resolve()
    failures: list[str] = []
    check_state(wf, failures)
    if args.require == "final":
        check_brief(wf, failures)
        check_draft(wf, failures)
        check_image(wf, failures)
        check_doc(wf, failures)
    if failures:
        emit({"status": "fail", "workflow": str(wf), "failures": failures}, 1)
    emit({"status": "pass", "workflow": str(wf)})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate Doubao Novel Writing Feishu document delivery")
    parser.add_argument("--workflow", default=str(DEFAULT_WORKFLOW_DIR))
    parser.add_argument("--require", choices=("final",), default="final")
    return parser


def main() -> None:
    validate(build_parser().parse_args())


if __name__ == "__main__":
    main()
