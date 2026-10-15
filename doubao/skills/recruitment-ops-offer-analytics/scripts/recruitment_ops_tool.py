#!/usr/bin/env python3
"""Deterministic recruiting pipeline, offer capability, and hard-gate engine."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from datetime import datetime
from pathlib import Path

PROTECTED = {
    "age", "birth_date", "gender", "sex", "race", "ethnicity", "religion",
    "marital_status", "pregnancy", "disability", "health", "nationality",
}
OFFER_REQUIRED = {
    "candidate_id", "legal_entity", "jurisdiction", "role", "level",
    "location", "employment_type", "start_date", "comp_components",
    "template_version",
}
CLAIM_FIELDS = {
    "claim_id", "claim", "claim_type", "critical", "object_id", "period",
    "unit", "source_ids", "source_tier", "confidence", "conflict_state",
}
CLAIM_TYPES = {"fact", "calculation", "inference", "assumption", "management_claim", "unknown"}
SOURCE_TIERS = {"primary", "counterparty", "official", "secondary", "lead_only"}
ALLOWED_STATES = {"ready", "degraded", "intake_required", "confirmation_required", "routed", "stopped"}


def parse_time(value):
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def digest(payload):
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def privacy_gate(payload):
    found = sorted(PROTECTED.intersection(payload.get("decision_fields", [])))
    return {"pass": not found, "forbidden_fields": found}


def claim_gate(claims):
    invalid, unsupported, unknown_ids = [], [], []
    for claim in claims:
        missing = sorted(CLAIM_FIELDS - set(claim))
        malformed = (
            claim.get("claim_type") not in CLAIM_TYPES
            or claim.get("source_tier") not in SOURCE_TIERS
            or claim.get("confidence") not in {"high", "medium", "low"}
            or claim.get("conflict_state") not in {"none", "open", "resolved"}
        )
        if missing or malformed:
            invalid.append({"claim_id": claim.get("claim_id"), "missing": missing, "malformed": malformed})
        if claim.get("claim_type") == "unknown":
            unknown_ids.append(claim.get("claim_id"))
        if claim.get("critical") and (
            claim.get("claim_type") == "unknown"
            or not claim.get("source_ids")
            or claim.get("source_tier") not in {"primary", "official"}
            or claim.get("conflict_state") == "open"
        ):
            unsupported.append(claim.get("claim_id"))
    return {
        "pass": bool(claims) and not invalid and not unsupported,
        "invalid_claims": invalid,
        "unsupported_critical_claims": unsupported,
        "unknown_claim_ids": unknown_ids,
    }


def _write_json(path, payload):
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def validate_artifacts(full_path, compact_path):
    exists = full_path.is_file() and compact_path.is_file()
    if not exists:
        return {"pass": False, "files_exist": False, "hash_match": False, "status_match": False, "counts_match": False}
    full = json.loads(full_path.read_text(encoding="utf-8"))
    compact = json.loads(compact_path.read_text(encoding="utf-8"))
    result = {
        "pass": True,
        "files_exist": True,
        "hash_match": hashlib.sha256(full_path.read_bytes()).hexdigest() == compact.get("full_sha256"),
        "status_match": full.get("status") == compact.get("status"),
        "counts_match": full.get("counts") == compact.get("counts"),
    }
    result["pass"] = all(result.values())
    return result


def pipeline_result(payload):
    stages = payload.get("configured_stages") or []
    snapshot = parse_time(payload.get("snapshot_at"))
    records = payload.get("records") or []
    seen, duplicates, unknowns, reached = set(), [], [], {stage: 0 for stage in stages}
    if snapshot is None:
        unknowns.append({"object_id": "pipeline", "missing": ["snapshot_at"], "impact": ["velocity", "current_stage_age"]})
    durations = {stage: [] for stage in stages}
    valid_records = []
    for row in records:
        candidate_id = row.get("candidate_id")
        if not candidate_id:
            unknowns.append({"candidate_id": None, "missing": ["candidate_id"]})
            continue
        if candidate_id in seen:
            duplicates.append(candidate_id)
            continue
        seen.add(candidate_id)
        history = row.get("history") or []
        missing = []
        if not history:
            missing.append("history")
        parsed = []
        for event in history:
            stage, entered_at = event.get("stage"), parse_time(event.get("entered_at"))
            if stage not in stages or entered_at is None:
                missing.append("valid_stage_and_entered_at")
                continue
            parsed.append((stage, entered_at))
        parsed.sort(key=lambda item: item[1])
        if missing:
            unknowns.append({"candidate_id": candidate_id, "missing": sorted(set(missing))})
        visited = {stage for stage, _ in parsed}
        for stage in visited:
            reached[stage] += 1
        for index, (stage, entered_at) in enumerate(parsed):
            end = parsed[index + 1][1] if index + 1 < len(parsed) else snapshot
            if end is not None and end >= entered_at:
                durations[stage].append((end - entered_at).total_seconds() / 86400)
        valid_records.append({"candidate_id": candidate_id, "visited": sorted(visited)})
    conversions = []
    conservation_pass = True
    for index, stage in enumerate(stages[:-1]):
        next_stage = stages[index + 1]
        denominator, numerator = reached[stage], reached[next_stage]
        if numerator > denominator:
            conservation_pass = False
        conversions.append({
            "from_stage": stage,
            "to_stage": next_stage,
            "numerator": numerator,
            "denominator": denominator,
            "rate": None if denominator == 0 else numerator / denominator,
        })
    velocity = {
        stage: {
            "n": len(values),
            "average_days": None if not values else sum(values) / len(values),
        }
        for stage, values in durations.items()
    }
    gates = {
        "claim_gate": claim_gate(payload.get("claims") or []),
        "deliverable_gate": {"pass": bool(stages) and bool(records) and snapshot is not None},
        "permission_gate": {"pass": True, "reason": "read_compute_only"},
        "artifact_gate": {"pass": True, "files_exist": True, "hash_match": True, "status_match": True, "counts_match": True},
        "conservation_gate": {"pass": conservation_pass and not duplicates, "duplicates": duplicates},
        "privacy_gate": privacy_gate(payload),
    }
    counts = {
        "records": len(records),
        "valid_unique": len(valid_records),
        "unknowns": len(unknowns),
        "duplicates": len(duplicates),
    }
    return {
        "schema_version": "hr-recruitment-tool/1.0",
        "task_type": "pipeline",
        "claims": payload.get("claims") or [],
        "snapshot_at": payload.get("snapshot_at"),
        "counts": counts,
        "configured_stages": stages,
        "reached_counts": reached,
        "conversions": conversions,
        "velocity": velocity,
        "unknowns": unknowns,
        "gates": gates,
        "status": "intake_required" if snapshot is None else (
            "ready" if all(g["pass"] for g in gates.values()) and not unknowns else "degraded"
        ),
    }


def offer_result(payload):
    offer = payload.get("offer") or {}
    missing = sorted(field for field in OFFER_REQUIRED if offer.get(field) in (None, "", []))
    approval_state = payload.get("approval_state", "unknown")
    send_permission = payload.get("send_permission", False)
    user_confirmed = payload.get("user_confirmed_send", False)
    capabilities = {
        "can_draft_offer": {"allowed": not missing, "missing": missing},
        "can_request_offer_approval": {"allowed": not missing, "missing": missing},
        "can_send_offer": {
            "allowed": not missing and approval_state == "approved" and send_permission and user_confirmed,
            "missing": missing + ([] if approval_state == "approved" else ["approved_offer"])
            + ([] if send_permission else ["send_permission"])
            + ([] if user_confirmed else ["user_confirmation"]),
        },
    }
    unknowns = [{"field": field, "impact": ["draft", "approval", "send"]} for field in missing]
    gates = {
        "claim_gate": claim_gate(payload.get("claims") or []),
        "deliverable_gate": {"pass": bool(offer)},
        "permission_gate": {
            "pass": capabilities["can_send_offer"]["allowed"] or not payload.get("send_requested", False),
            "send_executed": False,
        },
        "artifact_gate": {"pass": True, "files_exist": True, "hash_match": True, "status_match": True, "counts_match": True},
        "privacy_gate": privacy_gate(payload),
    }
    counts = {
        "offer_fields_present": len(set(offer).intersection(OFFER_REQUIRED)),
        "missing_fields": len(missing),
        "unknowns": len(unknowns),
    }
    return {
        "schema_version": "hr-recruitment-tool/1.0",
        "task_type": "offer",
        "claims": payload.get("claims") or [],
        "counts": counts,
        "offer_fields_present": sorted(set(offer).intersection(OFFER_REQUIRED)),
        "capabilities": capabilities,
        "unknowns": unknowns,
        "gates": gates,
        "side_effect": {"executed": False, "policy": "preview_only"},
        "status": (
            "confirmation_required"
            if payload.get("send_requested", False) and not capabilities["can_send_offer"]["allowed"] and not missing
            else ("ready" if all(g["pass"] for g in gates.values()) else "degraded")
        ),
    }


def _run(payload, artifact_dir):
    task_type = payload.get("task_type")
    if task_type == "pipeline":
        full = pipeline_result(payload)
    elif task_type == "offer":
        full = offer_result(payload)
    else:
        raise ValueError("task_type must be pipeline or offer")
    if full["status"] not in ALLOWED_STATES:
        raise ValueError("invalid artifact state")
    artifact_dir.mkdir(parents=True, exist_ok=True)
    full_path, compact_path = artifact_dir / "full.json", artifact_dir / "compact.json"
    _write_json(full_path, full)
    full_hash = hashlib.sha256(full_path.read_bytes()).hexdigest()
    compact = {
        "schema_version": full["schema_version"],
        "task_type": task_type,
        "status": full["status"],
        "counts": full["counts"],
        "unknown_count": len(full["unknowns"]),
        "gates": full["gates"],
        "full_sha256": full_hash,
    }
    if task_type == "pipeline":
        compact.update({"reached_counts": full["reached_counts"], "conversions": full["conversions"]})
    else:
        compact["capabilities"] = full["capabilities"]
    _write_json(compact_path, compact)
    full["gates"]["artifact_gate"] = validate_artifacts(full_path, compact_path)
    if not full["gates"]["artifact_gate"]["pass"]:
        full["status"] = "degraded"
    compact["status"], compact["gates"] = full["status"], full["gates"]
    _write_json(full_path, full)
    compact["full_sha256"] = hashlib.sha256(full_path.read_bytes()).hexdigest()
    _write_json(compact_path, compact)
    final_gate = validate_artifacts(full_path, compact_path)
    if not final_gate["pass"]:
        raise RuntimeError(f"artifact validation failed: {final_gate}")
    return {
        "full": full,
        "compact": compact,
        "full_sha256": compact["full_sha256"],
        "compact_sha256": hashlib.sha256(compact_path.read_bytes()).hexdigest(),
        "artifacts": {"full": str(full_path), "compact": str(compact_path)},
    }


def run(payload, artifact_dir=None):
    if artifact_dir is not None:
        return _run(payload, Path(artifact_dir))
    with tempfile.TemporaryDirectory() as directory:
        return _run(payload, Path(directory))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output")
    parser.add_argument("--artifact-dir")
    args = parser.parse_args()
    artifact_dir = args.artifact_dir or tempfile.mkdtemp(prefix="hr-recruitment-artifacts-")
    result = run(json.loads(Path(args.input).read_text(encoding="utf-8")), artifact_dir)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
