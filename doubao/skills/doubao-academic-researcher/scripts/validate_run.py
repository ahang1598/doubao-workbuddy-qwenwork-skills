#!/usr/bin/env python3
"""Validate whether a doubao-academic-researcher test run actually used workflow gates.

This is the test judgment layer. It is designed for post-run testing:

    python scripts/validate_run.py --require final

It fails closed. Missing state files, missing handoffs, invalid readiness flags,
or missing figure evidence all produce a non-zero exit with concrete failures.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WORKFLOW_DIR = ROOT / ".workflow"

MAX_REVIEW_VISIBLE_LENGTH = 2000
REVIEW_LENGTH_FLOAT_TOLERANCE = 200

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

SYNTHESIS_POOLS = (
    "claim_pool",
    "citation_pool",
    "tension_pool",
    "gap_pool",
)


def emit(payload: dict[str, Any], exit_code: int = 0) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    raise SystemExit(exit_code)


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


def check_required(data: dict[str, Any] | None, required: dict[str, str], label: str, failures: list[str]) -> None:
    if data is None:
        return
    for key, expected in required.items():
        if key not in data:
            failures.append(f"{label}: missing {key}")
        elif norm(data[key]) != expected:
            failures.append(f"{label}: {key} must be {expected!r}, got {data[key]!r}")


def check_core_literature(data: dict[str, Any] | None, failures: list[str]) -> None:
    if data is None:
        return
    core = data.get("core_literature")
    if not isinstance(core, list) or not core:
        failures.append("scout_handoff: core_literature must be a non-empty list")
        return
    has_seminal = False
    for idx, item in enumerate(core):
        if not isinstance(item, dict):
            failures.append(f"scout_handoff: core_literature[{idx}] must be an object")
            continue
        cid = str(item.get("id") or item.get("citation_key") or f"#{idx}")
        venue = str(item.get("venue", "")).strip()
        url = str(item.get("url", "")).strip()
        read_status = norm(item.get("read_status"))
        quality = norm(item.get("source_quality"))
        signal = norm(item.get("authority_signal"))
        basis = str(item.get("quality_basis", "")).strip()
        if not venue:
            failures.append(f"scout_handoff: core_literature {cid} missing venue")
        if not url:
            failures.append(f"scout_handoff: core_literature {cid} missing url")
        if not read_status:
            failures.append(f"scout_handoff: core_literature {cid} missing read_status")
        elif read_status == "metadata_only":
            failures.append(f"scout_handoff: core_literature {cid} read_status cannot be metadata_only")
        if quality not in VALID_SOURCE_QUALITY:
            failures.append(
                f"scout_handoff: core_literature {cid} source_quality must be A or B, "
                f"got {item.get('source_quality')!r}"
            )
        if signal not in VALID_AUTHORITY_SIGNALS:
            failures.append(
                f"scout_handoff: core_literature {cid} authority_signal must be one of "
                f"{sorted(VALID_AUTHORITY_SIGNALS)}, got {item.get('authority_signal')!r}"
            )
        if not basis:
            failures.append(f"scout_handoff: core_literature {cid} missing quality_basis")
        elif basis.strip().lower() in VAGUE_QUALITY_BASIS:
            failures.append(
                f"scout_handoff: core_literature {cid} quality_basis is too vague; "
                "provide JCR/中科院分区、IF、被引数、顶刊顶会或经典奠基地位"
            )
        if norm(item.get("is_seminal")) in {"yes", "true", "1"}:
            has_seminal = True
    if not has_seminal:
        failures.append("scout_handoff: core_literature must contain at least one is_seminal=yes entry")


def check_non_empty_pool(data: dict[str, Any] | None, key: str, failures: list[str]) -> None:
    if data is None:
        return
    value = data.get(key)
    ok = False
    if isinstance(value, list):
        ok = len(value) > 0
    elif isinstance(value, str):
        ok = bool(value.strip())
    if not ok:
        failures.append(f"synthesis_handoff: {key} must be non-empty")


def check_state(wf: Path, require: str, failures: list[str]) -> dict[str, Any] | None:
    state = load_json(wf / "state.json", failures)
    if state is None:
        failures.append("workflow was not initialized; expected .workflow/state.json")
        return None
    completed = state.get("completed")
    if not isinstance(completed, list):
        failures.append("state.completed must be a list")
        completed = []
    expected_by_level = {
        "scout": ["literature-scout"],
        "synthesis": ["literature-scout", "research-synthesis"],
        "review": ["literature-scout", "research-synthesis", "review-writing"],
        "final": ["literature-scout", "research-synthesis", "review-writing", "document-delivery"],
    }
    for stage in expected_by_level[require]:
        if stage not in completed:
            failures.append(f"state.completed missing stage: {stage}")
    if require == "final" and state.get("current_stage") != "done":
        failures.append(f"state.current_stage must be 'done' for final, got {state.get('current_stage')!r}")
    return state


def check_logic_graph(wf: Path, failures: list[str]) -> str:
    whiteboard_xml = wf / "figures" / "logic_graph.whiteboard.xml"
    if not whiteboard_xml.exists():
        failures.append("missing core logic graph: final validation requires figures/logic_graph.whiteboard.xml")
        return "missing"
    text = whiteboard_xml.read_text(encoding="utf-8-sig")
    if "<whiteboard type=\"mermaid\">" not in text:
        failures.append("logic graph must use <whiteboard type=\"mermaid\">")
    if "flowchart" not in text.lower():
        failures.append("logic graph must contain a flowchart")
    if "-->|" not in text:
        failures.append("logic graph must contain labeled edges like -->|关系|")
    if not re.search(r"\bN\d+(?:\s*(?:\[\[.*?\]\]|\[.*?\]|\(\(.*?\)\)|\(.*?\)|\{\{.*?\}\}))?\s*-->\|[^|]+?\|\s*N\d+\b", text):
        failures.append("logic graph must contain at least one node-to-node lineage edge like N1 -->|扩展| N2")
    if not re.search(r"\[[A-Za-z]*\d+\]|\b[A-Z]{1,3}\d+\b", text):
        failures.append("logic graph nodes must be traceable to evidence ids")
    return "inserted"


def check_doc_handoff(wf: Path, data: dict[str, Any] | None, logic_status: str, failures: list[str]) -> None:
    check_required(data, DOC_REQUIRED, "doc_handoff", failures)
    if data is None:
        return
    for key in ("doc_id", "doc_url"):
        if not str(data.get(key, "")).strip():
            failures.append(f"doc_handoff: {key} must be non-empty")
    if logic_status == "inserted" and norm(data.get("logic_graph_inserted")) != "yes":
        failures.append("doc_handoff: logic_graph_inserted must be 'yes' when logic graph whiteboard exists")
    if norm(data.get("logic_graph_checked", "pass")) not in {"yes", "pass"}:
        failures.append("doc_handoff: logic_graph_checked must be yes/pass")
    if norm(data.get("literature_map_table")) not in {"yes", "pass"}:
        failures.append("doc_handoff: literature_map_table must be yes/pass")
    if norm(data.get("literature_map_position")) != "correct":
        failures.append("doc_handoff: literature_map_position must be 'correct'")
    if norm(data.get("placeholder_removed")) not in {"yes", "pass"}:
        failures.append("doc_handoff: placeholder_removed must be yes/pass")
    if norm(data.get("rich_block_ban_checked")) not in {"yes", "pass"}:
        failures.append("doc_handoff: rich_block_ban_checked must be yes/pass")
    if norm(data.get("citation_format_checked")) not in {"yes", "pass"}:
        failures.append("doc_handoff: citation_format_checked must be yes/pass")
    if norm(data.get("reference_links_checked")) not in {"yes", "pass"}:
        failures.append("doc_handoff: reference_links_checked must be yes/pass")
    if norm(data.get("main_section_heading_checked")) not in {"yes", "pass"}:
        failures.append("doc_handoff: main_section_heading_checked must be yes/pass (一级章节必须按实际出现顺序连续编号)")
    if norm(data.get("topic_heading_sequence_checked")) not in {"yes", "pass"}:
        failures.append("doc_handoff: topic_heading_sequence_checked must be yes/pass (分主题必须按（一）（二）（三）连续编号)")
    if norm(data.get("section_lit_index_checked")) not in {"yes", "pass"}:
        failures.append("doc_handoff: section_lit_index_checked must be yes/pass (每个分主题标题下需紧接本节文献索引)")
    if norm(data.get("fixed_section_lit_checked")) not in {"yes", "pass"}:
        failures.append("doc_handoff: fixed_section_lit_checked must be yes/pass (一级章节不得出现本节文献)")


def check_requirement_checklist(wf: Path, failures: list[str]) -> None:
    """校验 Step 0 的需求拆解留痕。

    只做痕迹核查，不判断满足质量：清单必须存在、至少一条需求、
    字段齐全，且每条 in_scope==yes 的需求都回填了非空 resolution。
    """
    data = load_json(wf / "requirement_checklist.json", failures)
    if data is None:
        return
    requirements = data.get("requirements")
    if not isinstance(requirements, list) or not requirements:
        failures.append("requirement_checklist: requirements must be a non-empty list")
        return
    has_main = False
    for idx, item in enumerate(requirements):
        if not isinstance(item, dict):
            failures.append(f"requirement_checklist: requirement #{idx} must be an object")
            continue
        rid = str(item.get("id") or f"#{idx}")
        for field in ("requirement", "priority", "in_scope", "carrier"):
            if not str(item.get(field, "")).strip():
                failures.append(f"requirement_checklist: {rid} missing {field}")
        priority = norm(item.get("priority"))
        if priority and priority not in VALID_PRIORITY:
            failures.append(
                f"requirement_checklist: {rid} priority must be one of {sorted(VALID_PRIORITY)}, "
                f"got {item.get('priority')!r}"
            )
        if priority == "main":
            has_main = True
        in_scope = norm(item.get("in_scope"))
        if in_scope and in_scope not in VALID_IN_SCOPE:
            failures.append(
                f"requirement_checklist: {rid} in_scope must be one of {sorted(VALID_IN_SCOPE)}, "
                f"got {item.get('in_scope')!r}"
            )
        if in_scope == "yes" and not str(item.get("resolution", "")).strip():
            failures.append(
                f"requirement_checklist: {rid} is in_scope but resolution is empty (未说明在哪一节/以什么形式落实)"
            )
    if not has_main:
        failures.append("requirement_checklist: at least one requirement must have priority 'main'")


def check_review_draft_report(wf: Path, failures: list[str]) -> None:
    data = load_json(wf / "review_draft_check.json", failures)
    if data is None:
        return
    if norm(data.get("status")) != "pass":
        failures.append("review_draft_check: status must be pass")
    result = data.get("result")
    if not isinstance(result, dict):
        failures.append("review_draft_check: result must be an object")
        return
    try:
        paragraph_count = int(result.get("paragraph_count", 0))
    except (TypeError, ValueError):
        paragraph_count = 0
    try:
        visible_length = int(result.get("visible_length", 0))
    except (TypeError, ValueError):
        visible_length = 0
    if not 3 <= paragraph_count <= 6:
        failures.append(f"review_draft_check: paragraph_count must be 3-6, got {paragraph_count}")
    if visible_length > MAX_REVIEW_VISIBLE_LENGTH + REVIEW_LENGTH_FLOAT_TOLERANCE:
        failures.append(
            f"review_draft_check: visible_length should stay around {MAX_REVIEW_VISIBLE_LENGTH}, got {visible_length}"
        )


def validate(args: argparse.Namespace) -> None:
    wf = Path(args.workflow).resolve()
    failures: list[str] = []

    check_state(wf, args.require, failures)

    # Step 0 需求拆解清单是进入 literature-scout 的前置门槛，任何完成级别都应已存在。
    check_requirement_checklist(wf, failures)

    if args.require in {"scout", "synthesis", "review", "final"}:
        scout = load_json(wf / "scout_handoff.json", failures)
        check_required(scout, SCOUT_REQUIRED, "scout_handoff", failures)
        check_core_literature(scout, failures)

    if args.require in {"synthesis", "review", "final"}:
        synthesis = load_json(wf / "synthesis_handoff.json", failures)
        check_required(synthesis, SYNTHESIS_REQUIRED, "synthesis_handoff", failures)
        for key in SYNTHESIS_POOLS:
            check_non_empty_pool(synthesis, key, failures)
        logic_status = check_logic_graph(wf, failures)
    else:
        logic_status = "not_required"

    if args.require in {"review", "final"}:
        review = load_json(wf / "review_handoff.json", failures)
        check_required(review, REVIEW_REQUIRED, "review_handoff", failures)
        check_review_draft_report(wf, failures)

    if args.require == "final":
        doc = load_json(wf / "doc_handoff.json", failures)
        check_doc_handoff(wf, doc, logic_status, failures)

    if failures:
        emit(
            {
                "status": "fail",
                "require": args.require,
                "workflow": str(wf),
                "failures": failures,
            },
            1,
        )

    emit({"status": "pass", "require": args.require, "workflow": str(wf)})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate doubao-academic-researcher workflow artifacts")
    parser.add_argument("--workflow", default=str(DEFAULT_WORKFLOW_DIR), help="workflow state directory")
    parser.add_argument(
        "--require",
        choices=("scout", "synthesis", "review", "final"),
        default="final",
        help="required completion level",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    validate(args)


if __name__ == "__main__":
    main()
