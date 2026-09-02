#!/usr/bin/env python3
"""Validate structured evidence before the hot-theme team can finalize."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROUTE_MEMBERS = {'market_scan': ('market-daily-review', 'concept-rotation', 'smart-money-tracker', 'a-share-market-risk-radar'), 'theme_compare': ('market-daily-review', 'concept-rotation', 'smart-money-tracker', 'a-share-market-risk-radar'), 'candidate_shortlist': ('market-daily-review', 'concept-rotation', 'smart-money-tracker', 'stock-screener', 'a-share-market-risk-radar'), 'single_theme': ('concept-rotation', 'smart-money-tracker', 'a-share-market-risk-radar'), 'education': ()}
ROUTES = {task_type: set(members) for task_type, members in ROUTE_MEMBERS.items()}

MEMBER_METHOD_REQUIREMENTS = {
    member_id: set(methods)
    for member_id, methods in {'market-daily-review': ('get_last_trade_date', 'get_trade_cal', 'get_trade_list', 'get_index_daily', 'get_index_indicator', 'get_stock_daily', 'get_concept_list', 'get_concept_constituents', 'get_lhb_list', 'get_lhb_detail', 'get_block_trade', 'get_margin', 'get_hsgt_hold'), 'concept-rotation': ('get_last_trade_date', 'get_concept_list', 'get_concept_constituents', 'get_stock_daily'), 'smart-money-tracker': ('get_last_trade_date', 'get_lhb_list', 'get_margin', 'get_hsgt_hold', 'get_block_trade'), 'stock-screener': ('get_last_trade_date', 'get_trade_list', 'get_stock_detail', 'get_stock_daily', 'get_concept_constituents'), 'a-share-market-risk-radar': ('get_last_trade_date', 'get_margin', 'get_hsgt_hold', 'get_lhb_list', 'get_concept_list', 'get_concept_constituents', 'get_index_daily')}.items()
}

ALL_MEMBER_IDS = set(MEMBER_METHOD_REQUIREMENTS)
CANDIDATE_MARKERS = ("股票", "个股", "候选", "龙头", "名单", "股票池", "选股", "筛选", "排名")
COMPARE_MARKERS = ("对比", "比较", "哪个更强", "哪个题材", "孰强", "pk")
CAPITAL_MARKERS = ("资金确认", "资金验证", "主力", "龙虎榜", "北向", "融资", "大宗")
CURRENT_MARKERS = ("今天", "今日", "最近", "当前", "本周")

CURRENT_FACT_TYPES = {"data_fact", "derived_calculation", "expert_judgment"}
FINAL_STATUSES = {
    "priority_research",
    "continue_observe",
    "caution",
    "evidence_insufficient",
}


def validate(payload: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if payload.get("schema_version") != "pd-team-evidence/1":
        errors.append("schema_version must be pd-team-evidence/1")

    user_request = payload.get("user_request")
    if not isinstance(user_request, str) or not user_request.strip():
        errors.append("user_request must preserve the non-empty original request")
        user_request = ""
    normalized_request = user_request.lower()

    task_type = payload.get("task_type")
    if task_type not in ROUTES:
        errors.append(f"unknown task_type: {task_type!r}")
        required_members: set[str] = set()
    else:
        required_members = ROUTES[task_type]

    if any(marker in normalized_request for marker in CANDIDATE_MARKERS):
        if task_type != "candidate_shortlist":
            errors.append("candidate-style request must use candidate_shortlist")
    elif any(marker in normalized_request for marker in COMPARE_MARKERS):
        if task_type != "theme_compare":
            errors.append("comparison request must use theme_compare")

    if any(marker in normalized_request for marker in CAPITAL_MARKERS):
        if "smart-money-tracker" not in required_members:
            errors.append("capital-confirmation request must require smart-money-tracker")

    if task_type == "education" and any(
        marker in normalized_request
        for marker in CURRENT_MARKERS + CAPITAL_MARKERS + CANDIDATE_MARKERS
    ):
        errors.append("current-market or candidate request cannot use education route")

    data_required = payload.get("data_required") is True
    if task_type == "education" and data_required:
        errors.append("education route must set data_required=false")
    elif task_type in ROUTES and task_type != "education" and not data_required:
        errors.append(f"{task_type} must set data_required=true")
    reports = payload.get("member_reports")
    if not isinstance(reports, list):
        errors.append("member_reports must be a list")
        reports = []

    report_by_member: dict[str, dict[str, Any]] = {}
    all_evidence_ids: set[str] = set()
    for index, report in enumerate(reports):
        if not isinstance(report, dict):
            errors.append(f"member_reports[{index}] must be an object")
            continue
        member_id = report.get("member_id")
        if not isinstance(member_id, str) or not member_id:
            errors.append(f"member_reports[{index}] missing member_id")
            continue
        if member_id in report_by_member:
            errors.append(f"duplicate member report: {member_id}")
            continue
        if member_id not in ALL_MEMBER_IDS:
            errors.append(f"unregistered member report: {member_id}")
        report_by_member[member_id] = report

        if member_id in required_members and report.get("status") != "completed":
            errors.append(f"required member {member_id} did not complete")

        if data_required and member_id in required_members:
            if report.get("data_gate") != "OPEN":
                errors.append(f"required member {member_id} DATA_GATE is not OPEN")
            if report.get("auth_status") != "success":
                errors.append(f"required member {member_id} auth_status is not success")

        calls = report.get("calls", [])
        if not isinstance(calls, list):
            errors.append(f"{member_id}: calls must be a list")
            calls = []
        if data_required and member_id in required_members and not calls:
            errors.append(f"required member {member_id} has no business calls")

        member_evidence_ids: set[str] = set()
        methods_seen: set[str] = set()
        positive_row_calls = 0
        for call_index, call in enumerate(calls):
            if not isinstance(call, dict):
                errors.append(f"{member_id}: call {call_index} must be an object")
                continue
            evidence_id = call.get("evidence_id")
            if not isinstance(evidence_id, str) or not evidence_id:
                errors.append(f"{member_id}: call {call_index} missing evidence_id")
                continue
            if evidence_id in all_evidence_ids:
                errors.append(f"duplicate evidence_id: {evidence_id}")
            all_evidence_ids.add(evidence_id)
            member_evidence_ids.add(evidence_id)

            method = call.get("method")
            if not isinstance(method, str) or not method.startswith("get_"):
                errors.append(f"{evidence_id}: method must be a get_* business method")
            else:
                methods_seen.add(method)
            if not isinstance(call.get("params"), dict):
                errors.append(f"{evidence_id}: params must be an object")
            status = call.get("status")
            row_count = call.get("row_count")
            if not isinstance(row_count, int) or row_count < 0:
                errors.append(f"{evidence_id}: row_count must be a non-negative integer")
            elif status == "success" and row_count == 0:
                errors.append(f"{evidence_id}: zero rows require empty_after_retry")
            elif status == "empty_after_retry":
                if row_count != 0 or int(call.get("retry_count", 0)) < 1:
                    errors.append(
                        f"{evidence_id}: empty_after_retry requires row_count=0 and retry_count>=1"
                    )
            elif status != "success":
                errors.append(f"{evidence_id}: unsupported call status {status!r}")
            elif isinstance(row_count, int) and row_count > 0:
                positive_row_calls += 1
            if not isinstance(call.get("date_range"), str) or not call.get("date_range"):
                errors.append(f"{evidence_id}: date_range is required")
            if not isinstance(call.get("fields"), list) or not call.get("fields"):
                errors.append(f"{evidence_id}: fields must be a non-empty list")

        if data_required and member_id in required_members:
            if positive_row_calls == 0:
                errors.append(f"required member {member_id} has no positive-row business call")
            expected_methods = MEMBER_METHOD_REQUIREMENTS.get(member_id, set())
            missing_methods = expected_methods.difference(methods_seen)
            if missing_methods:
                errors.append(
                    f"required member {member_id} missing minimum methods: "
                    f"{sorted(missing_methods)}"
                )

        claims = report.get("claims", [])
        if not isinstance(claims, list):
            errors.append(f"{member_id}: claims must be a list")
            claims = []
        if member_id in required_members and not claims:
            errors.append(f"required member {member_id} has no claims")
        for claim_index, claim in enumerate(claims):
            validate_claim(
                claim,
                f"{member_id}: claim {claim_index}",
                member_evidence_ids,
                errors,
            )

    missing_members = required_members.difference(report_by_member)
    if missing_members:
        errors.append(f"missing required members: {sorted(missing_members)}")

    if task_type == "education" and not reports:
        errors.append("education route still requires at least one real member call")

    final_status = payload.get("final_status")
    if final_status not in FINAL_STATUSES:
        errors.append(f"invalid final_status: {final_status!r}")

    final_claims = payload.get("final_claims")
    if not isinstance(final_claims, list) or not final_claims:
        errors.append("final_claims must be a non-empty list")
        final_claims = []
    for index, claim in enumerate(final_claims):
        validate_claim(claim, f"final claim {index}", all_evidence_ids, errors)

    if data_required:
        final_evidence_ids = {
            evidence_id
            for claim in final_claims
            if isinstance(claim, dict)
            for evidence_id in claim.get("evidence_ids", [])
            if isinstance(evidence_id, str)
        }
        for member_id in sorted(required_members):
            member_prefix = f"{member_id}-CALL-"
            if not any(
                evidence_id.startswith(member_prefix)
                for evidence_id in final_evidence_ids
            ):
                errors.append(
                    f"final claims do not reference required member evidence: {member_id}"
                )

    unsupported = payload.get("unsupported_claims", [])
    if not isinstance(unsupported, list):
        errors.append("unsupported_claims must be a list")
    elif unsupported:
        errors.append("unsupported_claims must be empty before finalization")

    conflicts = payload.get("conflicts", [])
    if not isinstance(conflicts, list):
        errors.append("conflicts must be a list")
        conflicts = []
    disclosed_conflict = False
    for index, conflict in enumerate(conflicts):
        if not isinstance(conflict, dict):
            errors.append(f"conflict {index} must be an object")
            continue
        status = conflict.get("status")
        if status not in {"resolved", "disclosed"}:
            errors.append(f"conflict {index} must be resolved or disclosed")
        if status == "disclosed":
            disclosed_conflict = True
        refs = conflict.get("evidence_ids")
        if not isinstance(refs, list) or not refs:
            errors.append(f"conflict {index} requires evidence_ids")
        else:
            unknown = set(refs).difference(all_evidence_ids)
            if unknown:
                errors.append(f"conflict {index} references unknown evidence: {sorted(unknown)}")
        if not isinstance(conflict.get("resolution"), str) or not conflict.get("resolution"):
            errors.append(f"conflict {index} requires resolution text")

    if disclosed_conflict and final_status == "priority_research":
        errors.append("priority_research is not allowed with disclosed unresolved conflict")

    if not data_required:
        warnings.append("data_required=false: final output must not contain current market facts")

    return {
        "schema_version": "pd-team-evidence-validation/1",
        "task_type": task_type,
        "required_members": sorted(required_members),
        "completed_members": sorted(
            member_id
            for member_id, report in report_by_member.items()
            if report.get("status") == "completed"
        ),
        "business_call_count": sum(
            len(report.get("calls", []))
            for report in report_by_member.values()
            if isinstance(report.get("calls", []), list)
        ),
        "evidence_id_count": len(all_evidence_ids),
        "errors": errors,
        "warnings": warnings,
        "final_allowed": not errors,
    }


def validate_claim(
    claim: Any,
    label: str,
    allowed_evidence_ids: set[str],
    errors: list[str],
) -> None:
    if not isinstance(claim, dict):
        errors.append(f"{label} must be an object")
        return
    claim_type = claim.get("claim_type")
    if claim_type not in CURRENT_FACT_TYPES | {"background_knowledge"}:
        errors.append(f"{label} has invalid claim_type {claim_type!r}")
    if not isinstance(claim.get("text"), str) or not claim.get("text"):
        errors.append(f"{label} requires text")
    refs = claim.get("evidence_ids", [])
    if claim_type in CURRENT_FACT_TYPES:
        if not isinstance(refs, list) or not refs:
            errors.append(f"{label} requires evidence_ids")
            return
        unknown = set(refs).difference(allowed_evidence_ids)
        if unknown:
            errors.append(f"{label} references unknown evidence: {sorted(unknown)}")
    elif refs:
        unknown = set(refs).difference(allowed_evidence_ids)
        if unknown:
            errors.append(f"{label} references unknown evidence: {sorted(unknown)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    payload = json.loads(args.input.read_text(encoding="utf-8"))
    result = validate(payload)
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result["final_allowed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
