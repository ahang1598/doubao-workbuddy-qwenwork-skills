#!/usr/bin/env python3
from __future__ import annotations
"""Check contribution attribution and evidence references without judging content truth."""

import argparse
import json
import re
import sys
from pathlib import Path


VALID_EVIDENCE = {"supplied", "verified", "unresolved", "conflict"}
VALID_CLAIM_TYPES = {"fact", "interpretation", "recommendation", "assumption", "question", "unclassified"}
VALID_MERGE_STATUS = {"draft", "team_review", "final_ready"}
NUMBER_RE = re.compile(r"(?<![A-Za-z])\d+(?:\.\d+)?%?")
MERGE_MARKERS = {
    "artifact_id",
    "content_blocks",
    "evidence_map",
    "duplicate_register",
    "tension_register",
    "conflict_register",
    "gap_register",
    "contribution_map",
}


def numeric_tokens(text: str) -> set[str]:
    without_list_numbers = re.sub(r"(?m)^\s*\d+[.、)]\s*", "", text)
    return set(NUMBER_RE.findall(without_list_numbers))


def audit_merge_result(payload, claim_ids=None, *, deep=False):
    errors: list[str] = []
    warnings: list[str] = []

    artifact_id = payload.get("artifact_id")
    if not isinstance(artifact_id, str) or not artifact_id.strip():
        errors.append("artifact_id is required for MergeResult")
    revision = payload.get("revision")
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
        errors.append("revision must be an integer >= 1")
    status = payload.get("status")
    if status not in VALID_MERGE_STATUS:
        errors.append(f"status must be one of: {', '.join(sorted(VALID_MERGE_STATUS))}")

    registers: dict[str, list] = {}
    for name in (
        "evidence_map",
        "duplicate_register",
        "tension_register",
        "conflict_register",
        "gap_register",
    ):
        value = payload.get(name)
        if not isinstance(value, list):
            errors.append(f"{name} must be a list")
        else:
            registers[name] = value

    contribution_map = payload.get("contribution_map")
    if not isinstance(contribution_map, dict):
        errors.append("contribution_map must be an object")

    unresolved_submissions = payload.get("unresolved_submissions", [])
    if not isinstance(unresolved_submissions, list):
        errors.append("unresolved_submissions must be a list")

    content_blocks = payload.get("content_blocks")
    if not isinstance(content_blocks, list) or not content_blocks:
        errors.append("content_blocks must be a non-empty list")
    else:
        block_ids: set[str] = set()
        for index, block in enumerate(content_blocks, start=1):
            prefix = f"content_blocks[{index}]"
            if not isinstance(block, dict):
                errors.append(f"{prefix} must be an object")
                continue
            block_id = block.get("block_id")
            if not isinstance(block_id, str) or not block_id.strip():
                errors.append(f"{prefix}.block_id is required")
            elif block_id in block_ids:
                errors.append(f"duplicate block_id: {block_id}")
            else:
                block_ids.add(block_id)
            for field in ("heading", "content"):
                if not isinstance(block.get(field), str):
                    errors.append(f"{prefix}.{field} must be a string")
            refs = block.get("source_claim_ids")
            if not isinstance(refs, list) or not all(
                isinstance(ref, str) and ref.strip() for ref in refs
            ):
                errors.append(f"{prefix}.source_claim_ids must be a string list")
            elif not refs and block.get("content"):
                warnings.append(f"{block_id or prefix} has content but no source_claim_ids")
            elif deep and claim_ids is not None:
                missing = [ref for ref in refs if ref not in claim_ids]
                if missing:
                    errors.append(
                        f"{block_id or prefix} references unknown claims: {', '.join(missing)}"
                    )

    conflict_register = registers.get("conflict_register", [])
    for item in conflict_register:
        if isinstance(item, dict) and not item.get("conflict_type"):
            warnings.append(
                f"{item.get('conflict_id', 'conflict')} needs conflict_type classification"
            )

    evidence_map = registers.get("evidence_map", [])
    if isinstance(evidence_map, list):
        for index, item in enumerate(evidence_map, start=1):
            if not isinstance(item, dict):
                errors.append(f"evidence_map[{index}] must be an object")
            elif item.get("verification") in {"unresolved", "conflict"}:
                warnings.append(f"evidence_map[{index}] requires human review")
                if status == "final_ready":
                    errors.append("final_ready is not allowed with unresolved evidence")

    if status == "final_ready":
        if conflict_register:
            errors.append("final_ready is not allowed with unresolved conflicts")
        if registers.get("gap_register"):
            errors.append("final_ready is not allowed with unresolved gaps")
        if unresolved_submissions:
            errors.append("final_ready is not allowed with unresolved_submissions")
        if payload.get("unclassified_claims"):
            errors.append("final_ready is not allowed with unclassified_claims")
    if not deep:
        warnings.append(
            "MergeResult structure checked without contributions; source_claim_ids were not cross-validated"
        )
    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit ContributionPacket collections or MergeResult JSON."
    )
    parser.add_argument(
        "path", type=Path, help="path to contributions or merge-result JSON"
    )
    args = parser.parse_args()
    try:
        payload = json.loads(args.path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[ERROR] cannot read JSON: {exc}")
        return 1

    if not isinstance(payload, dict):
        print("[ERROR] root must be an object")
        return 1

    contributions = payload.get("contributions")
    is_merge_result = (
        "artifact_id" in payload
        or "content_blocks" in payload
        or (
            "status" in payload
            and len(MERGE_MARKERS.intersection(payload)) >= 2
        )
    )
    if (not isinstance(contributions, list) or not contributions) and is_merge_result:
        errors, warnings = audit_merge_result(payload)
        for warning in warnings:
            print(f"[WARN] {warning}")
        if errors:
            for error in errors:
                print(f"[ERROR] {error}")
            return 1
        print(
            f"VALID merge result: blocks={len(payload['content_blocks'])}, "
            f"conflicts={len(payload['conflict_register'])}, gaps={len(payload['gap_register'])}"
        )
        return 0
    if not isinstance(contributions, list) or not contributions:
        print("[ERROR] contributions must be a non-empty list")
        return 1

    errors: list[str] = []
    warnings: list[str] = []
    claim_ids: set[str] = set()
    evidence_index: dict[str, str] = {}
    claim_records: list[tuple[str, str, dict]] = []
    unclassified_claims: list[str] = []
    unresolved_evidence: list[str] = []
    member_ids: set[str] = set()
    for index, contribution in enumerate(contributions, start=1):
        if not isinstance(contribution, dict):
            errors.append(f"contributions[{index}] must be an object")
            continue
        member_id = contribution.get("member_id")
        task_id = contribution.get("task_id")
        if not isinstance(member_id, str) or not member_id.strip():
            errors.append(f"contributions[{index}].member_id is required")
        else:
            member_ids.add(member_id)
        if not isinstance(task_id, str) or not task_id.strip():
            errors.append(f"contributions[{index}].task_id is required")

        claims = contribution.get("claims", [])
        evidence = contribution.get("evidence", [])
        if "claims" not in contribution or not isinstance(claims, list):
            errors.append(f"contributions[{index}].claims must be a list")
        if "evidence" not in contribution or not isinstance(evidence, list):
            errors.append(f"contributions[{index}].evidence must be a list")
        if not isinstance(claims, list) or not isinstance(evidence, list):
            continue
        for item in evidence:
            if (
                not isinstance(item, dict)
                or not isinstance(item.get("evidence_id"), str)
                or not item["evidence_id"].strip()
            ):
                errors.append(f"contributions[{index}] has an invalid evidence item")
                continue
            evidence_id = item["evidence_id"]
            if evidence_id in evidence_index:
                errors.append(f"duplicate evidence_id: {evidence_id} (members {evidence_index[evidence_id]} and {member_id})")
            evidence_index[evidence_id] = member_id
            if item.get("verification") not in VALID_EVIDENCE:
                errors.append(f"{evidence_id} has invalid verification status")
            if item.get("verification") in {"unresolved", "conflict"}:
                warnings.append(f"{evidence_id} requires human review")
                unresolved_evidence.append(evidence_id)
        for claim in claims:
            if not isinstance(claim, dict) or not isinstance(claim.get("claim_id"), str):
                errors.append(f"contributions[{index}] has an invalid claim item")
                continue
            claim_id = claim["claim_id"]
            if claim_id in claim_ids:
                errors.append(f"duplicate claim_id: {claim_id}")
            claim_ids.add(claim_id)
            claim_type = claim.get("claim_type", "unclassified")
            if claim_type not in VALID_CLAIM_TYPES:
                errors.append(f"{claim_id} has invalid claim_type: {claim_type}")
            elif claim_type == "unclassified":
                unclassified_claims.append(claim_id)
            claim_records.append((claim_id, member_id, claim))
            if not isinstance(claim.get("statement"), str) or not claim["statement"].strip():
                errors.append(f"{claim_id}.statement must be a non-empty string")
            refs = claim.get("evidence_ids", [])
            if not isinstance(refs, list):
                errors.append(f"{claim_id}.evidence_ids must be a list")
            elif not all(isinstance(ref, str) and ref.strip() for ref in refs):
                errors.append(f"{claim_id}.evidence_ids values must be non-empty strings")
            elif not refs and claim_type in {"fact", "interpretation", "unclassified"}:
                errors.append(f"{claim_id} requires evidence_ids for claim_type={claim_type}")
            if claim_type == "recommendation" and not refs and not claim.get("rationale") and not claim.get("related_claim_ids"):
                errors.append(f"{claim_id} recommendation requires rationale or related_claim_ids")

        draft_content = contribution.get("draft_content", "")
        if not isinstance(draft_content, str) or not draft_content.strip():
            errors.append(f"contributions[{index}].draft_content must be a non-empty string")
        else:
            draft_numbers = numeric_tokens(draft_content)
            claim_numbers = {
                token
                for claim in claims
                if isinstance(claim, dict) and isinstance(claim.get("statement"), str)
                for token in numeric_tokens(claim["statement"])
            }
            untracked = sorted(draft_numbers - claim_numbers)
            if untracked:
                warnings.append(
                    f"{member_id or index} draft_content has numeric tokens not represented in claims: {', '.join(untracked)}"
                )

    for claim_id, member_id, claim in claim_records:
        refs = claim.get("evidence_ids", [])
        if not isinstance(refs, list) or not all(
            isinstance(ref, str) and ref.strip() for ref in refs
        ):
            continue
        missing = [ref for ref in refs if ref not in evidence_index]
        if missing:
            errors.append(f"{claim_id} references unknown evidence: {', '.join(missing)}")
            continue
        shared = [f"{ref} (owner {evidence_index[ref]})" for ref in refs if evidence_index[ref] != member_id]
        if shared:
            warnings.append(f"{claim_id} shares evidence across packets: {', '.join(shared)}; retain source ownership")
        if claim.get("claim_type") == "recommendation" and not refs and not claim.get("rationale") and not claim.get("related_claim_ids"):
            errors.append(f"{claim_id} recommendation requires rationale or related_claim_ids")

    if unclassified_claims:
        warnings.append("unclassified claims require merge-time classification: " + ", ".join(unclassified_claims))

    if is_merge_result:
        merge_errors, merge_warnings = audit_merge_result(
            payload, claim_ids, deep=True
        )
        errors.extend(merge_errors)
        warnings.extend(merge_warnings)
        if payload.get("status") == "final_ready" and (
            unresolved_evidence or unclassified_claims
        ):
            errors.append(
                "final_ready is not allowed with unresolved evidence or unclassified claims"
            )
        if payload.get("status") == "final_ready" and (
            payload.get("unresolved_submissions")
            or payload.get("gap_register")
            or payload.get("conflict_register")
            or unresolved_evidence
            or unclassified_claims
        ):
            errors.append("final_ready is not allowed with unresolved/unclassified/conflict items")

    merge_summary = payload.get("merge_summary")
    if merge_summary is not None:
        if not isinstance(merge_summary, dict):
            errors.append("merge_summary must be an object")
        else:
            status = merge_summary.get("status")
            if status not in VALID_MERGE_STATUS:
                errors.append(f"merge_summary.status must be one of: {', '.join(sorted(VALID_MERGE_STATUS))}")
            if merge_summary.get("total_claims") not in (None, len(claim_ids)):
                errors.append(f"merge_summary.total_claims does not match audited claims={len(claim_ids)}")
            if merge_summary.get("total_evidence") not in (None, len(evidence_index)):
                errors.append(f"merge_summary.total_evidence does not match audited evidence={len(evidence_index)}")

            conflict_register = payload.get("conflict_register", [])
            gap_register = payload.get("gap_register", [])
            duplicate_register = payload.get("duplicate_register", [])
            tension_register = payload.get("tension_register", [])
            for name, register in (
                ("conflict_register", conflict_register),
                ("gap_register", gap_register),
                ("duplicate_register", duplicate_register),
                ("tension_register", tension_register),
            ):
                if not isinstance(register, list):
                    errors.append(f"{name} must be a list")

            if isinstance(conflict_register, list) and merge_summary.get("conflicts") not in (None, len(conflict_register)):
                errors.append("merge_summary.conflicts does not match conflict_register")
            if isinstance(gap_register, list) and merge_summary.get("gaps") not in (None, len(gap_register)):
                errors.append("merge_summary.gaps does not match gap_register")
            if isinstance(duplicate_register, list) and merge_summary.get("duplicate_groups") not in (None, len(duplicate_register)):
                errors.append("merge_summary.duplicate_groups does not match duplicate_register")
            if merge_summary.get("duplicate_claims") and not duplicate_register:
                warnings.append("legacy duplicate_claims is non-zero but duplicate_register is missing")
            if not payload.get("content_blocks"):
                warnings.append("merge result has no traceable content_blocks with source_claim_ids")
            if isinstance(conflict_register, list):
                for item in conflict_register:
                    if isinstance(item, dict) and not item.get("conflict_type"):
                        warnings.append(f"{item.get('conflict_id', 'conflict')} needs conflict_type classification")
            if status == "final_ready" and (unresolved_evidence or unclassified_claims):
                errors.append("final_ready is not allowed with unresolved evidence or unclassified claims")

    for warning in warnings:
        print(f"[WARN] {warning}")
    if errors:
        for error in errors:
            print(f"[ERROR] {error}")
        return 1
    print(f"VALID contributions: packets={len(contributions)}, claims={len(claim_ids)}, evidence={len(evidence_index)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
