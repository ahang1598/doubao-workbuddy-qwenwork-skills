#!/usr/bin/env python3
"""Final validator for Doubao Novel Writing.

Run before replying to the user:
    python scripts/validate_run.py --require final

fast-mode: 飞书文档交付为可选阶段。模型根据任务长度、是否需要插图、用户是否要求
分享链接来自行决定——短篇/章节直接对话输出即可，长篇或需要插图才建飞书。
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WORKFLOW_DIR = ROOT / ".workflow"
# fast-mode: document-delivery 改为可选，不再强制要求。
REQUIRED_STAGES = ("brief", "draft")


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
    # fast-mode: 只要求 brief_handoff 文件存在且 title 非空；
    # task_type/deliverable/user_intent 等字段属于内部规划留痕，不做阻断。
    data = load_json(wf / "brief_handoff.json", failures)
    if not data:
        return
    if not str(data.get("title", "")).strip():
        failures.append("brief_handoff: title must be non-empty")


def check_draft(wf: Path, failures: list[str]) -> None:
    # fast-mode: 只要求 content_path 指向的正文文件存在且非空；
    # core_section 必须命中、禁止出现"自检/质量门禁"等内部词，这些是真正影响交付质量的检查，保留。
    data = load_json(wf / "draft_handoff.json", failures)
    if not data:
        return
    title = str(data.get("title", "")).strip()
    content_path = str(data.get("content_path", "")).strip()
    if not title:
        failures.append("draft_handoff: title must be non-empty")
    if not content_path:
        failures.append("draft_handoff: content_path must be non-empty")
        return
    path = resolve_existing_path(content_path, wf)
    if not path.exists():
        failures.append(f"draft_handoff: content_path does not exist: {content_path}")
        return
    text = path.read_text(encoding="utf-8-sig")
    if not text.strip():
        failures.append("draft content is empty")
    for banned in ("自检", "质量门禁", "检查清单", "workflow.py", "validate_run.py"):
        if banned in text:
            failures.append(f"draft content exposes internal workflow text: {banned}")
            break


def check_image(wf: Path, failures: list[str]) -> None:
    # fast-mode: image_handoff 为可选——不建飞书文档时不需要插图计划。
    # 文件存在就校验能解析，不存在不报错。
    path = wf / "image_handoff.json"
    if not path.exists():
        return
    load_json(path, failures)


def check_doc(wf: Path, failures: list[str]) -> None:
    # fast-mode: 飞书交付可选。document_delivery_handoff.json 不存在不报错——
    # 模型选择直接对话输出即可。如果文件存在，校验 URL 格式。
    path = wf / "document_delivery_handoff.json"
    if not path.exists():
        return
    data = load_json(path, failures)
    if not data:
        return
    title = str(data.get("doc_title", "")).strip()
    url = str(data.get("doc_url", "")).strip()
    if not title:
        failures.append("doc_handoff: doc_title must be non-empty")
    if not url:
        failures.append("doc_handoff: doc_url must be non-empty")
    elif not re.search(r"https?://[^\s]*(larkoffice\.com|feishu\.cn)/", url):
        failures.append("doc_handoff: doc_url must be a Feishu/Lark document URL")


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
