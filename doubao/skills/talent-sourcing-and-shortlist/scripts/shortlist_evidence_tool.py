#!/usr/bin/env python3
"""Deterministic candidate dedupe, evidence completeness, and shortlist gates."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path

PROTECTED = {
    "age", "birth_date", "gender", "sex", "race", "ethnicity", "religion",
    "marital_status", "pregnancy", "disability", "health", "nationality",
}
CLAIM_FIELDS = {
    "claim_id", "claim", "claim_type", "critical", "object_id", "period",
    "unit", "source_ids", "source_tier", "confidence", "conflict_state",
}
CLAIM_TYPES = {"fact", "calculation", "inference", "assumption", "management_claim", "unknown"}
SOURCE_TIERS = {"primary", "counterparty", "official", "secondary", "lead_only"}
CONFIDENCE = {"high", "medium", "low"}
CONFLICT_STATES = {"none", "open", "resolved"}
ALLOWED_STATES = {"ready", "degraded", "intake_required", "confirmation_required", "routed", "stopped"}


def digest(payload):
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def claim_gate(claims):
    invalid, unsupported, unknown_ids, unknown_objects = [], [], [], set()
    for claim in claims:
        missing = sorted(CLAIM_FIELDS - set(claim))
        malformed = (
            claim.get("claim_type") not in CLAIM_TYPES
            or claim.get("source_tier") not in SOURCE_TIERS
            or claim.get("confidence") not in CONFIDENCE
            or claim.get("conflict_state") not in CONFLICT_STATES
        )
        if missing or malformed:
            invalid.append({"claim_id": claim.get("claim_id"), "missing": missing, "malformed": malformed})
        if claim.get("claim_type") == "unknown":
            unknown_ids.append(claim.get("claim_id"))
            unknown_objects.add(claim.get("object_id"))
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
        "unknown_objects": sorted(item for item in unknown_objects if item is not None),
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
    actual_hash = hashlib.sha256(full_path.read_bytes()).hexdigest()
    result = {
        "pass": True,
        "files_exist": True,
        "hash_match": actual_hash == compact.get("full_sha256"),
        "status_match": full.get("status") == compact.get("status"),
        "counts_match": full.get("counts") == compact.get("counts"),
    }
    result["pass"] = all(result.values())
    return result


def _run(payload, artifact_dir):
    claims = payload.get("claims") or []
    claim_result = claim_gate(claims)
    unknown_claim_objects = set(claim_result.pop("unknown_objects"))
    required = payload.get("required_criteria") or []
    seen, duplicates, eligible, pending, excluded = set(), [], [], [], []
    for row in payload.get("candidates") or []:
        candidate_id = row.get("candidate_id")
        if not candidate_id:
            pending.append({"candidate_id": None, "unknown": ["candidate_id"]})
            continue
        if candidate_id in seen:
            duplicates.append(candidate_id)
            continue
        seen.add(candidate_id)
        evidence = row.get("evidence") or []
        evidenced_fields = {item.get("criterion") for item in evidence if item.get("source_locator")}
        missing = sorted(set(required) - evidenced_fields)
        if candidate_id in unknown_claim_objects:
            pending.append({"candidate_id": candidate_id, "unknown": ["critical_claim_unknown"]})
        elif missing:
            pending.append({"candidate_id": candidate_id, "unknown": missing})
        elif row.get("failed_required_criteria"):
            excluded.append({"candidate_id": candidate_id, "failed": row["failed_required_criteria"]})
        else:
            eligible.append({"candidate_id": candidate_id, "evidence_count": len(evidence)})
    protected = sorted(PROTECTED.intersection(payload.get("decision_fields", [])))
    gates = {
        "claim_gate": claim_result,
        "deliverable_gate": {"pass": bool(payload.get("candidates"))},
        "permission_gate": {"pass": True, "reason": "read_compute_only", "executed": False},
        "artifact_gate": {"pass": True, "files_exist": True, "hash_match": True, "status_match": True, "counts_match": True},
        "dedupe_gate": {"pass": not duplicates, "duplicates": duplicates},
        "privacy_gate": {"pass": not protected, "forbidden_fields": protected},
    }
    counts = {
        "input": len(payload.get("candidates") or []),
        "unique": len(seen),
        "eligible": len(eligible),
        "pending_unknown": len(pending),
        "excluded": len(excluded),
    }
    full = {
        "schema_version": "hr-shortlist-evidence-tool/1.0",
        "claims": claims,
        "counts": counts,
        "eligible": eligible,
        "pending_unknown": pending,
        "excluded": excluded,
        "gates": gates,
        "status": "ready" if all(gate["pass"] for gate in gates.values()) and not pending else "degraded",
    }
    if full["status"] not in ALLOWED_STATES:
        raise ValueError("invalid artifact state")
    artifact_dir.mkdir(parents=True, exist_ok=True)
    full_path, compact_path = artifact_dir / "full.json", artifact_dir / "compact.json"
    _write_json(full_path, full)
    full_hash = hashlib.sha256(full_path.read_bytes()).hexdigest()
    compact = {
        "schema_version": full["schema_version"],
        "status": full["status"],
        "counts": counts,
        "gates": gates,
        "full_sha256": full_hash,
    }
    _write_json(compact_path, compact)
    full["gates"]["artifact_gate"] = validate_artifacts(full_path, compact_path)
    full["status"] = "ready" if all(gate["pass"] for gate in full["gates"].values()) and not pending else "degraded"
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
    artifact_dir = args.artifact_dir or tempfile.mkdtemp(prefix="hr-shortlist-artifacts-")
    result = run(json.loads(Path(args.input).read_text(encoding="utf-8")), artifact_dir)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
