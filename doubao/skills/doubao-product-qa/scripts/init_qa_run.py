#!/usr/bin/env python3
"""创建可继续填充且不会把未执行写成通过的 qa-run.json。"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from qa_run_common import (
    DELIVERY_CARRIERS,
    DELIVERY_FORMATS,
    PROFILE_FILES,
    TASK_MODES,
    TEST_INTENTS,
)


FORMAT_CARRIER = {
    "inline_markdown": "inline",
    "markdown": "local",
    "csv": "local",
    "json": "local",
    "docx": "office_file",
    "xlsx": "office_file",
    "pptx": "office_file",
    "pdf": "office_file",
    "lark_doc": "lark_doc",
    "lark_sheets": "lark_sheets",
    "lark_base": "lark_base",
    "lark_ppt": "lark_ppt",
    "multi": "multi",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="初始化 qa-run.json")
    parser.add_argument("out", type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--profile", choices=sorted(PROFILE_FILES), required=True)
    parser.add_argument("--test-intent", choices=sorted(TEST_INTENTS), required=True)
    parser.add_argument("--target-name", required=True)
    parser.add_argument("--target-type", default="unknown")
    parser.add_argument("--target-source", default="")
    parser.add_argument("--request-summary", required=True)
    parser.add_argument("--task-mode", choices=sorted(TASK_MODES), required=True)
    parser.add_argument("--delivery-format", choices=sorted(DELIVERY_FORMATS), required=True)
    parser.add_argument("--delivery-carrier", choices=sorted(DELIVERY_CARRIERS))
    parser.add_argument("--output-file", action="append", default=[])
    parser.add_argument(
        "--output-spec",
        action="append",
        default=[],
        metavar="FORMAT:FILENAME",
        help="混合交付物；例如 docx:测试方案.docx，可重复",
    )
    parser.add_argument("--required-section", action="append", default=[])
    parser.add_argument("--section-order", action="append", default=[])
    parser.add_argument("--scope-source", action="append", default=[])
    parser.add_argument("--exclude-source", action="append", default=[])
    parser.add_argument("--scope-round", action="append", default=[])
    parser.add_argument("--exclude-round", action="append", default=[])
    parser.add_argument("--allow-new-execution", action="store_true")
    return parser.parse_args()


def default_filename(target_name: str, output_format: str) -> str:
    safe_name = re.sub(r"[/\\:\x00-\x1f]+", "-", target_name).strip(" .-") or "QA"
    native_title = {
        "lark_doc": "QA测试方案与报告",
        "lark_sheets": "QA测试用例与追踪",
        "lark_base": "QA协作台账",
        "lark_ppt": "QA评审汇报",
    }.get(output_format)
    if native_title:
        return f"{safe_name}-{native_title}"
    suffix = {
        "markdown": ".md",
        "csv": ".csv",
        "json": ".json",
        "docx": ".docx",
        "xlsx": ".xlsx",
        "pptx": ".pptx",
        "pdf": ".pdf",
    }.get(output_format, "")
    return f"{safe_name}-QA收口报告{suffix}"


def parse_output_specs(values: list[str]) -> list[dict[str, str]]:
    specs: list[dict[str, str]] = []
    for value in values:
        output_format, separator, filename = value.partition(":")
        if not separator or output_format not in DELIVERY_FORMATS - {"inline_markdown", "multi"} or not filename:
            raise ValueError(f"非法 --output-spec：{value}，应为 FORMAT:FILENAME")
        specs.append({
            "format": output_format,
            "carrier": FORMAT_CARRIER[output_format],
            "filename": filename,
        })
    return specs


def main() -> int:
    args = parse_args()
    path = args.out.expanduser().resolve()
    if path.exists():
        print(f"拒绝覆盖已有文件：{path}", file=sys.stderr)
        return 2
    try:
        output_specs = parse_output_specs(args.output_spec)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.delivery_format == "multi" and len(output_specs) < 2:
        print("delivery-format=multi 时必须提供至少两个 --output-spec", file=sys.stderr)
        return 2
    artifact_required = args.delivery_format != "inline_markdown"
    filenames = list(dict.fromkeys(args.output_file))
    if output_specs:
        filenames = [item["filename"] for item in output_specs]
        artifact_required = True
    if artifact_required and not filenames:
        filenames = [default_filename(args.target_name, args.delivery_format)]
    if not output_specs and artifact_required:
        output_specs = [
            {
                "format": args.delivery_format,
                "carrier": args.delivery_carrier or FORMAT_CARRIER[args.delivery_format],
                "filename": filename,
            }
            for filename in filenames
        ]
    distinct_formats = {item["format"] for item in output_specs}
    effective_format = (
        "multi"
        if len(distinct_formats) > 1
        else (next(iter(distinct_formats)) if distinct_formats else args.delivery_format)
    )
    distinct_carriers = {item["carrier"] for item in output_specs}
    effective_carrier = (
        "multi"
        if len(distinct_carriers) > 1
        else (
            next(iter(distinct_carriers))
            if distinct_carriers
            else (args.delivery_carrier or FORMAT_CARRIER[effective_format])
        )
    )
    default_sections = ["测试报告", "详细用例", "Bug 单"] if args.delivery_format == "markdown" else []
    required_sections = list(dict.fromkeys(args.required_section or default_sections))
    section_order = list(dict.fromkeys(args.section_order or required_sections))
    normalized_request = " ".join(args.request_summary.split())
    payload = {
        "schema_version": 2,
        "run_id": args.run_id,
        "revision": 1,
        "profile": args.profile,
        "test_intent": args.test_intent,
        "execution_level": "blocked",
        "selected_path": "undetermined",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "target": {"type": args.target_type, "name": args.target_name, "source": args.target_source},
        "request_contract": {
            "request_summary": normalized_request,
            "request_hash": f"sha256:{hashlib.sha256(normalized_request.encode('utf-8')).hexdigest()}",
            "task_mode": args.task_mode,
            "scope": {
                "included_source_ids": list(dict.fromkeys(args.scope_source)),
                "excluded_source_ids": list(dict.fromkeys(args.exclude_source)),
                "included_rounds": list(dict.fromkeys(args.scope_round)),
                "excluded_rounds": list(dict.fromkeys(args.exclude_round)),
            },
            "evidence_policy": {
                "allow_new_execution": bool(args.allow_new_execution),
                "allow_precheck_bug_promotion": False,
                "required_bug_evidence_level": "L2_observation",
            },
            "delivery": {
                "artifact_required": artifact_required,
                "format": effective_format,
                "carrier": effective_carrier,
                "filenames": filenames,
                "artifacts": output_specs,
                "required_sections": required_sections,
                "section_order": section_order,
                "must_surface_to_user": True,
            },
        },
        "phase_receipts": [],
        "input": {
            "summary": "",
            "sources": [],
            "assumptions": [],
            "conflicts": [],
            "artifacts": [],
        },
        "open_questions": [],
        "change_ledger": [
            {
                "id": "CHG-001",
                "revision": 1,
                "action": "ADD",
                "object_type": "run",
                "added_ids": [args.run_id],
                "removed_ids": [],
                "modified_ids": [],
                "before_count": 0,
                "after_count": 1,
                "delta_count": 1,
                "source": "任务初始化",
                "summary": "建立 QA canonical 记录",
            }
        ],
        "environment": {},
        "screenshot_policy": "unconfirmed",
        "plan": {"scope": [], "out_of_scope": [], "entry_criteria": [], "exit_criteria": [], "regression": []},
        "requirements": [],
        "risk_mechanisms": [],
        "observed_surfaces": [],
        "cases": [],
        "executions": [],
        "evidence": [],
        "bugs": [],
        "bug_candidates": [],
        "risks": [],
        "acceptance_checks": [],
        "blockers": [],
        "manual_handoff": {
            "required": False, "status": "not_required", "reason": "",
            "target_platform": "", "operator": "", "prerequisites": [],
            "case_ids": [], "evidence_requirements": [], "result_submission": [],
        },
        "unverified": [],
        "coverage": {
            "requirement_total": 0, "requirement_linked": 0, "requirement_unlinked": 0,
            "p0_requirement_total": 0, "p0_requirement_linked": 0,
            "case_total": 0, "case_status_counts": {},
            "acceptance_total": 0, "acceptance_status_counts": {},
        },
        "release_decision": {"decision": "undetermined", "rationale": "尚未执行。", "conditions": []},
        "delivery_manifest": {"source_revision": 1, "outputs": []},
        "test_data": {
            "writes_allowed": False, "accounts": [], "created_records": [],
            "cleanup": {"required": False, "status": "completed", "command": "none", "residuals": []},
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
