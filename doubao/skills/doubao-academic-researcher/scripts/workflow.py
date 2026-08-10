#!/usr/bin/env python3
"""Runtime gatekeeper for doubao-academic-researcher.

This script is intentionally small and dependency-free. It does not judge
research quality; it only enforces stage order and handoff shape so the model
cannot silently skip phases.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WORKFLOW_DIR = ROOT / ".workflow"

STAGES = ("literature-scout", "research-synthesis", "review-writing", "document-delivery")

BLOCKED_ROUTES = {
    "NEED_REQUIREMENT_CHECKLIST": "literature-scout",
    "NEED_SCOUT_HANDOFF": "literature-scout",
    "NEED_SCOUT_REDO": "literature-scout",
    "NEED_SCOUT_SUPPLEMENT": "literature-scout",
    "NEED_SYNTHESIS_HANDOFF": "research-synthesis",
    "NEED_SYNTHESIS_FIX": "research-synthesis",
    "NEED_SYNTHESIS_REDO": "research-synthesis",
    "NEED_SYNTHESIS_REWORK": "research-synthesis",
    "NEED_REVIEW_HANDOFF": "review-writing",
    "NEED_REVIEW_REDO": "review-writing",
    "NEED_DOC_HANDOFF": "document-delivery",
    "NEED_DOC_FIX": "document-delivery",
    "NEED_DOCUMENT_REDO": "document-delivery",
}

SCOUT_REQUIRED = {
    "read_gate": "pass",
    "seed_query": "done",
    "verification": "done",
    "role_tags": "present",
    "ready_for_synthesis": "yes",
}

VALID_SOURCE_QUALITY = {"a", "b"}
VALID_AUTHORITY_SIGNALS = {
    "top_journal",
    "high_citation",
    "classic",
    "official",
    "core_journal",
}

VAGUE_QUALITY_BASIS = {
    "sci",
    "ssci",
    "sci/ssci",
    "英文期刊",
    "外文期刊",
    "国际期刊",
}

VALID_PRIORITY = {"main", "secondary"}
VALID_IN_SCOPE = {"yes", "no"}

SYNTHESIS_REQUIRED = {
    "read_gate": "pass",
    "gate_status": "clear",
    "ready_for_review": "yes",
}

SYNTHESIS_POOLS = (
    "claim_pool",
    "citation_pool",
    "tension_pool",
    "gap_pool",
)

REVIEW_REQUIRED = {
    "read_gate": "pass",
    "self_gate": "pass",
    "draft_shape_checked": "pass",
    "ready_for_final": "yes",
}

DOC_REQUIRED = {
    "doc_created": "yes",
    "fetched_back": "pass",
    "ready_for_final": "yes",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def emit(payload: dict[str, Any], exit_code: int = 0) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    raise SystemExit(exit_code)


def workflow_dir(args: argparse.Namespace) -> Path:
    return Path(args.workflow).resolve()


def state_path(wf: Path) -> Path:
    return wf / "state.json"


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        emit({"status": "error", "blocked": "MISSING_FILE", "path": str(path)}, 2)
    except json.JSONDecodeError as exc:
        emit(
            {
                "status": "error",
                "blocked": "INVALID_JSON",
                "path": str(path),
                "message": str(exc),
            },
            2,
        )
    if not isinstance(data, dict):
        emit({"status": "error", "blocked": "JSON_MUST_BE_OBJECT", "path": str(path)}, 2)
    return data


def load_state(wf: Path) -> dict[str, Any]:
    path = state_path(wf)
    if not path.exists():
        return {
            "current_stage": "not-initialized",
            "completed": [],
            "last_blocked": None,
            "updated_at": None,
        }
    return load_json(path)


def save_state(wf: Path, state: dict[str, Any]) -> None:
    wf.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = now_iso()
    state_path(wf).write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def normalize(value: Any) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value).strip().lower()


def require_fields(data: dict[str, Any], required: dict[str, str]) -> list[str]:
    failures: list[str] = []
    for key, expected in required.items():
        if key not in data:
            failures.append(f"missing {key}")
        elif normalize(data[key]) != expected:
            failures.append(f"{key} must be {expected!r}, got {data[key]!r}")
    return failures


def non_empty_pool(data: dict[str, Any], key: str) -> bool:
    value = data.get(key)
    if isinstance(value, list):
        return len(value) > 0
    if isinstance(value, str):
        return bool(value.strip())
    return False


def scout_handoff_path(wf: Path) -> Path:
    return wf / "scout_handoff.json"


def checklist_path(wf: Path) -> Path:
    return wf / "requirement_checklist.json"


def synthesis_handoff_path(wf: Path) -> Path:
    return wf / "synthesis_handoff.json"


def review_handoff_path(wf: Path) -> Path:
    return wf / "review_handoff.json"


def doc_handoff_path(wf: Path) -> Path:
    return wf / "doc_handoff.json"


def check_requirement_checklist(data: dict[str, Any]) -> list[str]:
    """校验 Step 0 需求拆解清单的形态与字段取值（方案 B）。

    只做确定性痕迹/格式校验，不判断主次拆得对不对（那属于内容质量，靠
    SKILL 指令 + 子代理 review 把关）。要求：requirements 为非空列表；每条含
    requirement/priority/in_scope/carrier 非空；priority 只能 main/secondary；
    in_scope 只能 yes/no；至少一条 priority=main。
    """
    failures: list[str] = []
    requirements = data.get("requirements")
    if not isinstance(requirements, list) or not requirements:
        failures.append("requirement_checklist: requirements must be a non-empty list")
        return failures
    has_main = False
    for idx, item in enumerate(requirements):
        if not isinstance(item, dict):
            failures.append(f"requirement_checklist: requirement[{idx}] must be an object")
            continue
        rid = str(item.get("id") or f"#{idx}")
        for field in ("requirement", "priority", "in_scope", "carrier"):
            if not str(item.get(field, "")).strip():
                failures.append(f"requirement_checklist: {rid} missing {field}")
        priority = normalize(item.get("priority"))
        if priority and priority not in VALID_PRIORITY:
            failures.append(
                f"requirement_checklist: {rid} priority must be one of {sorted(VALID_PRIORITY)}, "
                f"got {item.get('priority')!r}"
            )
        if priority == "main":
            has_main = True
        in_scope = normalize(item.get("in_scope"))
        if in_scope and in_scope not in VALID_IN_SCOPE:
            failures.append(
                f"requirement_checklist: {rid} in_scope must be one of {sorted(VALID_IN_SCOPE)}, "
                f"got {item.get('in_scope')!r}"
            )
    if not has_main:
        failures.append("requirement_checklist: at least one requirement must have priority 'main'")
    return failures


def check_core_literature(data: dict[str, Any]) -> list[str]:
    """校验 scout_handoff 的核心文献质量痕迹。只做确定性检查，不判学术价值。

    要求：core_literature 为非空列表；每条含 venue/url/read_status/source_quality/
    authority_signal/quality_basis；source_quality 必须是 A/B；authority_signal 必须是
    正向权威信号；read_status 不能是 metadata_only；全集至少一条 is_seminal。
    """
    failures: list[str] = []
    core = data.get("core_literature")
    if not isinstance(core, list) or not core:
        failures.append("core_literature must be a non-empty list (每条核心文献的质量痕迹)")
        return failures
    has_seminal = False
    for idx, item in enumerate(core):
        if not isinstance(item, dict):
            failures.append(f"core_literature[{idx}] must be an object")
            continue
        cid = str(item.get("id") or item.get("citation_key") or f"#{idx}")
        venue = str(item.get("venue", "")).strip()
        url = str(item.get("url", "")).strip()
        read_status = normalize(item.get("read_status"))
        quality = normalize(item.get("source_quality"))
        signal = normalize(item.get("authority_signal"))
        basis = str(item.get("quality_basis", "")).strip()
        if not venue:
            failures.append(f"core_literature {cid}: missing venue")
        if not url:
            failures.append(f"core_literature {cid}: missing url")
        if not read_status:
            failures.append(f"core_literature {cid}: missing read_status")
        elif read_status == "metadata_only":
            failures.append(f"core_literature {cid}: read_status cannot be metadata_only for core evidence")
        if quality not in VALID_SOURCE_QUALITY:
            failures.append(f"core_literature {cid}: source_quality must be A or B, got {item.get('source_quality')!r}")
        if signal not in VALID_AUTHORITY_SIGNALS:
            failures.append(
                f"core_literature {cid}: authority_signal must be one of "
                f"{sorted(VALID_AUTHORITY_SIGNALS)}, got {item.get('authority_signal')!r}"
            )
        if not basis:
            failures.append(
                f"core_literature {cid}: missing quality_basis "
                "(如 CSSCI/北大核心/SCI分区/影响因子/被引数/顶刊顶会/经典奠基/官方来源)"
            )
        elif basis.strip().lower() in VAGUE_QUALITY_BASIS:
            failures.append(
                f"core_literature {cid}: quality_basis is too vague; "
                "provide concrete evidence such as JCR/中科院分区、IF、被引数、顶刊顶会、经典奠基地位"
            )
        if normalize(item.get("is_seminal")) in {"yes", "true", "1"}:
            has_seminal = True
    if not has_seminal:
        failures.append("core_literature: at least one entry must be is_seminal=yes (需含该方向的奠基作/高引经典)")
    return failures


def validate_checklist_file(path: Path) -> dict[str, Any]:
    data = load_json(path)
    failures = check_requirement_checklist(data)
    if failures:
        emit(
            {
                "status": "blocked",
                "blocked": "NEED_REQUIREMENT_CHECKLIST",
                "reason": "; ".join(failures),
            },
            1,
        )
    return data


def validate_scout_handoff(path: Path) -> dict[str, Any]:
    data = load_json(path)
    failures = require_fields(data, SCOUT_REQUIRED)
    failures.extend(check_core_literature(data))
    if failures:
        emit(
            {
                "status": "blocked",
                "blocked": "NEED_SCOUT_REDO",
                "reason": "; ".join(failures),
            },
            1,
        )
    return data


def validate_synthesis_handoff(path: Path) -> dict[str, Any]:
    data = load_json(path)
    failures = require_fields(data, SYNTHESIS_REQUIRED)
    for key in SYNTHESIS_POOLS:
        if not non_empty_pool(data, key):
            failures.append(f"{key} must be non-empty")
    if failures:
        emit(
            {
                "status": "blocked",
                "blocked": "NEED_SYNTHESIS_REDO",
                "reason": "; ".join(failures),
            },
            1,
        )
    return data


def validate_review_handoff(path: Path, wf: Path | None = None) -> dict[str, Any]:
    data = load_json(path)
    failures = require_fields(data, REVIEW_REQUIRED)
    report_path = (wf or path.parent) / "review_draft_check.json"
    if not report_path.exists():
        failures.append(f"missing {report_path.name}")
    else:
        try:
            report = json.loads(report_path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            failures.append(f"{report_path.name} must be valid JSON")
        else:
            if not isinstance(report, dict):
                failures.append(f"{report_path.name} must be a JSON object")
            elif normalize(report.get("status")) != "pass":
                failures.append(f"{report_path.name} status must be 'pass'")
    if failures:
        emit(
            {
                "status": "blocked",
                "blocked": "NEED_REVIEW_REDO",
                "reason": "; ".join(failures),
            },
            1,
        )
    return data


def validate_doc_handoff(path: Path) -> dict[str, Any]:
    data = load_json(path)
    failures = require_fields(data, DOC_REQUIRED)
    for key in ("doc_id", "doc_url"):
        if not str(data.get(key, "")).strip():
            failures.append(f"{key} must be non-empty")
    if normalize(data.get("logic_graph_inserted")) not in {"yes", "skipped", "not_applicable"}:
        failures.append("logic_graph_inserted must be 'yes', 'skipped', or 'not_applicable'")
    if normalize(data.get("logic_graph_checked")) not in {"yes", "pass"}:
        failures.append("logic_graph_checked must be yes/pass")
    if normalize(data.get("literature_map_table")) not in {"yes", "pass"}:
        failures.append("literature_map_table must be yes/pass")
    if normalize(data.get("literature_map_position")) != "correct":
        failures.append("literature_map_position must be 'correct'")
    if normalize(data.get("placeholder_removed")) not in {"yes", "pass"}:
        failures.append("placeholder_removed must be yes/pass")
    if normalize(data.get("rich_block_ban_checked")) not in {"yes", "pass"}:
        failures.append("rich_block_ban_checked must be yes/pass")
    if normalize(data.get("citation_format_checked")) not in {"yes", "pass"}:
        failures.append("citation_format_checked must be yes/pass")
    if normalize(data.get("reference_links_checked")) not in {"yes", "pass"}:
        failures.append("reference_links_checked must be yes/pass")
    if normalize(data.get("main_section_heading_checked")) not in {"yes", "pass"}:
        failures.append("main_section_heading_checked must be yes/pass")
    if normalize(data.get("topic_heading_sequence_checked")) not in {"yes", "pass"}:
        failures.append("topic_heading_sequence_checked must be yes/pass")
    if normalize(data.get("section_lit_index_checked")) not in {"yes", "pass"}:
        failures.append("section_lit_index_checked must be yes/pass")
    if normalize(data.get("fixed_section_lit_checked")) not in {"yes", "pass"}:
        failures.append("fixed_section_lit_checked must be yes/pass")
    if failures:
        emit(
            {
                "status": "blocked",
                "blocked": "NEED_DOC_FIX",
                "reason": "; ".join(failures),
            },
            1,
        )
    return data


def cmd_init(args: argparse.Namespace) -> None:
    wf = workflow_dir(args)
    checklist_note = None
    if getattr(args, "checklist", None):
        source = Path(args.checklist).resolve()
        validate_checklist_file(source)
        target = wf / "requirement_checklist.json"
        wf.mkdir(parents=True, exist_ok=True)
        if source != target.resolve():
            shutil.copyfile(source, target)
        checklist_note = str(target)
    state = {
        "topic": args.topic or "",
        "current_stage": "literature-scout",
        "completed": [],
        "last_blocked": None,
        "requirement_checklist": checklist_note,
        "updated_at": now_iso(),
    }
    save_state(wf, state)
    payload = {"status": "ok", "next_stage": "literature-scout", "state": str(state_path(wf))}
    if checklist_note:
        payload["requirement_checklist"] = checklist_note
    emit(payload)


def cmd_enter(args: argparse.Namespace) -> None:
    wf = workflow_dir(args)
    stage = args.stage
    state = load_state(wf)

    if stage not in STAGES:
        emit({"status": "error", "blocked": "UNKNOWN_STAGE", "stage": stage}, 2)

    if stage == "literature-scout":
        path = checklist_path(wf)
        if not path.exists():
            emit(
                {
                    "status": "blocked",
                    "blocked": "NEED_REQUIREMENT_CHECKLIST",
                    "next_stage": "literature-scout",
                    "reason": "Step 0 需求拆解未落盘：先写 .workflow/requirement_checklist.json 再进入检索阶段",
                },
                1,
            )
        validate_checklist_file(path)
        if state["current_stage"] == "not-initialized":
            save_state(wf, {**state, "current_stage": "literature-scout"})
        emit({"status": "ok", "stage": stage, "message": "stage entry allowed"})

    if stage == "research-synthesis":
        path = scout_handoff_path(wf)
        if not path.exists():
            emit(
                {
                    "status": "blocked",
                    "blocked": "NEED_SCOUT_HANDOFF",
                    "next_stage": "literature-scout",
                },
                1,
            )
        validate_scout_handoff(path)
        emit({"status": "ok", "stage": stage, "message": "stage entry allowed"})

    if stage == "review-writing":
        path = synthesis_handoff_path(wf)
        if not path.exists():
            emit(
                {
                    "status": "blocked",
                    "blocked": "NEED_SYNTHESIS_HANDOFF",
                    "next_stage": "research-synthesis",
                },
                1,
            )
        validate_synthesis_handoff(path)
        emit({"status": "ok", "stage": stage, "message": "stage entry allowed"})

    if stage == "document-delivery":
        path = review_handoff_path(wf)
        if not path.exists():
            emit(
                {
                    "status": "blocked",
                    "blocked": "NEED_REVIEW_HANDOFF",
                    "next_stage": "review-writing",
                },
                1,
            )
        validate_review_handoff(path, wf)
        emit({"status": "ok", "stage": stage, "message": "stage entry allowed"})

    emit({"status": "error", "blocked": "UNREACHABLE_STAGE", "stage": stage}, 2)


def cmd_accept(args: argparse.Namespace) -> None:
    wf = workflow_dir(args)
    wf.mkdir(parents=True, exist_ok=True)
    stage = args.stage
    source = Path(args.handoff).resolve()
    state = load_state(wf)
    completed = list(state.get("completed", []))

    if stage == "literature-scout":
        validate_scout_handoff(source)
        target = scout_handoff_path(wf)
        next_stage = "research-synthesis"
    elif stage == "research-synthesis":
        validate_synthesis_handoff(source)
        target = synthesis_handoff_path(wf)
        next_stage = "review-writing"
    elif stage == "review-writing":
        validate_review_handoff(source, wf)
        target = review_handoff_path(wf)
        next_stage = "document-delivery"
    elif stage == "document-delivery":
        validate_doc_handoff(source)
        target = doc_handoff_path(wf)
        next_stage = "done"
    else:
        emit({"status": "error", "blocked": "UNKNOWN_STAGE", "stage": stage}, 2)

    if source != target.resolve():
        shutil.copyfile(source, target)
    if stage not in completed:
        completed.append(stage)
    save_state(
        wf,
        {
            **state,
            "current_stage": next_stage,
            "completed": completed,
            "last_blocked": None,
        },
    )
    emit(
        {
            "status": "ok",
            "accepted_stage": stage,
            "handoff": str(target),
            "next_stage": next_stage,
        }
    )


def cmd_block(args: argparse.Namespace) -> None:
    wf = workflow_dir(args)
    state = load_state(wf)
    code = args.code.replace("BLOCKED:", "").strip()
    next_stage = BLOCKED_ROUTES.get(code)
    if not next_stage:
        emit({"status": "error", "blocked": "UNKNOWN_BLOCKED_CODE", "code": code}, 2)
    save_state(
        wf,
        {
            **state,
            "current_stage": next_stage,
            "last_blocked": code,
        },
    )
    emit({"status": "blocked", "blocked": code, "next_stage": next_stage}, 1)


def cmd_status(args: argparse.Namespace) -> None:
    wf = workflow_dir(args)
    emit({"status": "ok", "workflow": str(wf), "state": load_state(wf)})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="doubao-academic-researcher workflow gatekeeper")
    parser.add_argument("--workflow", default=str(DEFAULT_WORKFLOW_DIR), help="workflow state directory")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="initialize workflow state")
    p_init.add_argument("--topic", default="", help="research topic / brief")
    p_init.add_argument("--checklist", default="", help="optional requirement_checklist.json to register")
    p_init.set_defaults(func=cmd_init)

    p_enter = sub.add_parser("enter", help="check whether a stage may start")
    p_enter.add_argument("stage", choices=STAGES)
    p_enter.set_defaults(func=cmd_enter)

    p_accept = sub.add_parser("accept", help="validate and accept a stage handoff JSON")
    p_accept.add_argument("stage", choices=STAGES)
    p_accept.add_argument("handoff", help="handoff JSON path")
    p_accept.set_defaults(func=cmd_accept)

    p_block = sub.add_parser("block", help="record a BLOCKED code and route to next stage")
    p_block.add_argument("code", help="blocked code, with or without BLOCKED: prefix")
    p_block.set_defaults(func=cmd_block)

    p_status = sub.add_parser("status", help="print workflow state")
    p_status.set_defaults(func=cmd_status)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
