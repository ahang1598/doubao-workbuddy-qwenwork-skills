#!/usr/bin/env python3
"""Deterministic customer value model plus local delivery gates."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from artifact_receipts import file_sha256, validate_artifact_receipts, write_json


SCHEMA_VERSION = "sales.roi-value-model.v1"
SCENARIOS = ("low", "base", "high")
PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_ARTIFACTS = set(
    json.loads((PACKAGE_ROOT / "config" / "runtime.json").read_text(encoding="utf-8"))
    ["claim_artifact_permission_gate"]["required_artifacts"]
)
CLAIM_FIELDS = {
    "claim_id", "claim", "claim_type", "critical", "object_id", "period",
    "unit", "source_ids", "source_tier", "confidence", "conflict_state",
}
CLAIM_TYPES = {"fact", "calculation", "inference", "assumption", "management_claim", "unknown"}
SOURCE_TIERS = {
    "primary", "customer_primary", "counterparty", "official", "crm_truth",
    "transaction_primary", "secondary", "lead_only",
}
CONFIDENCE = {"high", "medium", "low"}
CONFLICT_STATES = {"none", "open", "resolved"}
STRONG_SOURCE_TIERS = {
    "primary",
    "customer_primary",
    "counterparty",
    "official",
    "crm_truth",
    "transaction_primary",
}
SAFE_ACTIONS = {"read", "analyze", "draft"}
CONFIRM_ACTIONS = {"send", "write", "create", "publish", "update"}
DENY_ACTIONS = {"delete", "pay", "bribe", "bypass_control"}


def canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def sha256(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def number(value: Decimal) -> int | float:
    integral = value.to_integral_value()
    return int(integral) if value == integral else float(value)


def decimal_or_unknown(value: Any, field: str, unknowns: List[dict]) -> Optional[Decimal]:
    if value is None or (isinstance(value, str) and value.strip().lower() in {"", "unknown", "null"}):
        unknowns.append({"field": field, "reason": "missing_numeric_input"})
        return None
    try:
        result = Decimal(str(value))
    except InvalidOperation:
        unknowns.append({"field": field, "reason": "invalid_numeric_input"})
        return None
    if not result.is_finite():
        unknowns.append({"field": field, "reason": "non_finite_numeric_input"})
        return None
    return result


def evaluate_claims(claims: Any) -> dict:
    if not isinstance(claims, list) or not claims:
        return {"passed": False, "failures": ["claims must be a non-empty list"], "unknown_count": 0}
    failures: List[str] = []
    unknown_count = 0
    for index, claim in enumerate(claims):
        if not isinstance(claim, dict):
            failures.append(f"claims[{index}] must be an object")
            continue
        missing = sorted(CLAIM_FIELDS - set(claim))
        additional = sorted(set(claim) - CLAIM_FIELDS)
        if missing:
            failures.append(f"claims[{index}] missing {missing}")
            continue
        if additional:
            failures.append(f"claims[{index}] additional fields {additional}")
        if not all(isinstance(claim[field], str) and claim[field] for field in ("claim_id", "claim", "object_id", "period")):
            failures.append(f"claims[{index}] string fields invalid")
        if not isinstance(claim["critical"], bool):
            failures.append(f"claims[{index}].critical must be boolean")
        if claim["unit"] is not None and not isinstance(claim["unit"], str):
            failures.append(f"claims[{index}].unit must be string or null")
        if not isinstance(claim["source_ids"], list) or not all(isinstance(item, str) and item for item in claim["source_ids"]):
            failures.append(f"claims[{index}].source_ids must be a string list")
        if claim["claim_type"] not in CLAIM_TYPES:
            failures.append(f"claims[{index}].claim_type invalid")
        if claim["source_tier"] not in SOURCE_TIERS:
            failures.append(f"claims[{index}].source_tier invalid")
        if claim["confidence"] not in CONFIDENCE:
            failures.append(f"claims[{index}].confidence invalid")
        if claim["conflict_state"] not in CONFLICT_STATES:
            failures.append(f"claims[{index}].conflict_state invalid")
        if claim.get("claim_type") == "unknown":
            unknown_count += 1
            continue
        if claim.get("critical") and (
            not claim.get("source_ids")
            or claim.get("source_tier") not in STRONG_SOURCE_TIERS
        ):
            failures.append(f"claims[{index}] critical claim lacks strong source")
    return {"passed": not failures, "failures": failures, "unknown_count": unknown_count}


def evaluate_artifacts(context: dict) -> dict:
    return validate_artifact_receipts(
        context.get("artifact_receipts"), REQUIRED_ARTIFACTS
    )


def evaluate_permissions(requests: Any) -> dict:
    requests = requests or []
    failures: List[str] = []
    confirmation_required: List[str] = []
    denied: List[str] = []
    for index, request in enumerate(requests):
        action = request.get("action")
        if action in DENY_ACTIONS:
            denied.append(action)
        elif action in CONFIRM_ACTIONS and not (
            request.get("preview") and request.get("permission_confirmed")
        ):
            confirmation_required.append(action or f"request_{index}")
        elif action not in SAFE_ACTIONS | CONFIRM_ACTIONS:
            failures.append(f"unsupported action: {action}")
    return {
        "passed": not failures and not confirmation_required and not denied,
        "failures": failures,
        "confirmation_required": confirmation_required,
        "denied": denied,
        "execution": "not_executed" if confirmation_required or denied else "allowed",
    }


def run_gates(payload: dict, artifact_receipts: Any = None) -> dict:
    context = dict(payload.get("gate_context") or {})
    if artifact_receipts is not None:
        context["artifact_receipts"] = artifact_receipts
    claim_gate = evaluate_claims(payload.get("claims"))
    artifact_gate = evaluate_artifacts(context)
    permission_gate = evaluate_permissions(context.get("permission_requests"))
    if permission_gate["denied"]:
        state = "stopped"
    elif permission_gate["confirmation_required"]:
        state = "confirmation_required"
    elif not claim_gate["passed"] or not artifact_gate["passed"] or claim_gate["unknown_count"]:
        state = "degraded"
    else:
        state = "ready"
    return {
        "claim_gate": claim_gate,
        "artifact_gate": artifact_gate,
        "permission_gate": permission_gate,
        "artifact_state": state,
    }


def calculate_scenario(name: str, data: Any) -> dict:
    unknowns: List[dict] = []
    if not isinstance(data, dict):
        return {"scenario": name, "status": "unknown", "unknowns": [{"field": name, "reason": "scenario_missing"}]}
    drivers = data.get("benefit_drivers")
    costs = data.get("costs")
    if not isinstance(drivers, list) or not drivers:
        unknowns.append({"field": f"scenarios.{name}.benefit_drivers", "reason": "non_empty_list_required"})
        drivers = []
    if not isinstance(costs, list) or not costs:
        unknowns.append({"field": f"scenarios.{name}.costs", "reason": "non_empty_list_required"})
        costs = []

    benefit_rows = []
    total_benefit = Decimal("0")
    for index, row in enumerate(drivers):
        prefix = f"scenarios.{name}.benefit_drivers[{index}]"
        quantity = decimal_or_unknown(row.get("quantity"), f"{prefix}.quantity", unknowns)
        unit_value = decimal_or_unknown(row.get("unit_value"), f"{prefix}.unit_value", unknowns)
        realization = decimal_or_unknown(row.get("realization_rate"), f"{prefix}.realization_rate", unknowns)
        value = None if None in (quantity, unit_value, realization) else quantity * unit_value * realization
        if value is not None:
            total_benefit += value
        benefit_rows.append(
            {
                "driver_id": row.get("driver_id") or str(index),
                "formula": "quantity * unit_value * realization_rate",
                "quantity": None if quantity is None else number(quantity),
                "unit_value": None if unit_value is None else number(unit_value),
                "realization_rate": None if realization is None else number(realization),
                "benefit": None if value is None else number(value),
            }
        )

    cost_rows = []
    total_cost = Decimal("0")
    for index, row in enumerate(costs):
        prefix = f"scenarios.{name}.costs[{index}]"
        amount = decimal_or_unknown(row.get("amount"), f"{prefix}.amount", unknowns)
        if amount is not None:
            total_cost += amount
        cost_rows.append(
            {
                "cost_id": row.get("cost_id") or str(index),
                "amount": None if amount is None else number(amount),
            }
        )

    if unknowns:
        net_value = None
        roi = None
        status = "unknown"
    else:
        net = total_benefit - total_cost
        net_value = number(net)
        roi = None if total_cost == 0 else float(net / total_cost)
        status = "ok" if total_cost > 0 else "not_computable"
        if total_cost == 0:
            unknowns.append({"field": f"scenarios.{name}.costs", "reason": "total_cost_must_be_positive_for_roi"})
    return {
        "scenario": name,
        "status": status,
        "benefit_formula": "sum(quantity * unit_value * realization_rate)",
        "cost_formula": "sum(cost.amount)",
        "benefit_drivers": benefit_rows,
        "costs": cost_rows,
        "total_benefit": None if unknowns else number(total_benefit),
        "total_cost": None if unknowns else number(total_cost),
        "net_value": net_value,
        "roi": roi,
        "unknowns": unknowns,
    }


def calculate(payload: dict, out_dir: Optional[Path] = None) -> Tuple[dict, dict]:
    scenarios = payload.get("scenarios") or {}
    results = {name: calculate_scenario(name, scenarios.get(name)) for name in SCENARIOS}
    unknowns = [
        dict(item, scenario=name)
        for name, result in results.items()
        for item in result["unknowns"]
    ]
    for field in ("object_id", "currency", "period"):
        if not payload.get(field):
            unknowns.append({"field": field, "reason": "required_metadata_missing"})
    claim_gate = evaluate_claims(payload.get("claims"))
    permission_gate = evaluate_permissions(
        (payload.get("gate_context") or {}).get("permission_requests")
    )
    if permission_gate["denied"]:
        base_state = "stopped"
    elif permission_gate["confirmation_required"]:
        base_state = "confirmation_required"
    elif not claim_gate["passed"] or claim_gate["unknown_count"] or unknowns:
        base_state = "degraded"
    else:
        base_state = "ready"
    counts = {
        "records": len(results),
        "claims": len(payload.get("claims") or []),
        "unknowns": len(unknowns),
    }
    manifest = {
        "artifact_state": base_state,
        "counts": counts,
        "required_artifacts": sorted(REQUIRED_ARTIFACTS),
    }
    paths = {
        "roi_full_json": str(out_dir / "roi-value-model.full.json") if out_dir else None,
        "roi_compact_json": str(out_dir / "roi-value-model.compact.json") if out_dir else None,
        "roi_final_json": str(out_dir / "roi-value-model.final.json") if out_dir else None,
        "claim_ledger": str(out_dir / "claim-ledger.json") if out_dir else None,
    }
    full_file = {
        "artifact_name": "roi_full_json",
        "manifest": manifest,
        "schema_version": SCHEMA_VERSION,
        "tool": "roi_value_model",
        "object_id": payload.get("object_id"),
        "currency": payload.get("currency"),
        "period": payload.get("period"),
        "formula_policy": "explicit_inputs_no_default_benchmarks",
        "results": results,
        "claims": payload.get("claims") or [],
        "unknowns": unknowns,
        "artifact_paths": paths,
    }
    compact_file = {
        "artifact_name": "roi_compact_json",
        "manifest": manifest,
        "schema_version": SCHEMA_VERSION,
        "tool": "roi_value_model",
        "artifact_state": base_state,
        "core_results": {
            name: {
                "status": result["status"],
                "net_value": result["net_value"],
                "roi": result["roi"],
            }
            for name, result in results.items()
        },
        "unknowns": unknowns,
        "source_index": sorted(
            {source for claim in payload.get("claims") or [] for source in claim.get("source_ids", [])}
        ),
        "full_artifact_path": paths["roi_full_json"],
    }
    ledger_file = {
        "artifact_name": "claim_ledger",
        "manifest": manifest,
        "schema_version": SCHEMA_VERSION,
        "claims": payload.get("claims") or [],
    }
    receipts = []
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)
        write_json(Path(paths["roi_full_json"]), full_file)
        full_hash = file_sha256(Path(paths["roi_full_json"]))
        compact_file["full_sha256"] = full_hash
        write_json(Path(paths["roi_compact_json"]), compact_file)
        compact_hash = file_sha256(Path(paths["roi_compact_json"]))
        write_json(Path(paths["claim_ledger"]), ledger_file)
        ledger_hash = file_sha256(Path(paths["claim_ledger"]))
        final_file = {
            "artifact_name": "roi_final_json",
            "manifest": manifest,
            "schema_version": SCHEMA_VERSION,
            "core_results": compact_file["core_results"],
            "input_artifact_hashes": {
                "roi_full_json": full_hash,
                "roi_compact_json": compact_hash,
                "claim_ledger": ledger_hash,
            },
        }
        write_json(Path(paths["roi_final_json"]), final_file)
        for name, path in paths.items():
            receipts.append({
                "artifact_name": name,
                "path": path,
                "expected_sha256": file_sha256(Path(path)),
            })
    gates = run_gates(payload, receipts)
    if unknowns and gates["artifact_state"] == "ready":
        gates["artifact_state"] = "degraded"
    full = dict(
        full_file,
        gates=gates,
        artifact_receipts=receipts,
        sha256=next((item["expected_sha256"] for item in receipts if item["artifact_name"] == "roi_full_json"), None),
    )
    compact = dict(
        compact_file,
        hard_gates=gates,
        artifact_receipts=receipts,
        full_sha256=next((item["expected_sha256"] for item in receipts if item["artifact_name"] == "roi_full_json"), None),
    )
    return full, compact


def finalize(payload: dict) -> dict:
    approved = payload.get("approved_context") or {}
    candidate = payload.get("candidate") or {}
    approved_claim_gate = evaluate_claims(approved.get("claims"))
    candidate_claim_gate = evaluate_claims(candidate.get("claims"))
    checks = {}
    for key in ("source_ids", "object_ids", "numeric_values"):
        allowed = set(approved.get(key) or [])
        used = set(candidate.get(key) or [])
        checks[key] = {"extra": sorted(used - allowed), "passed": used <= allowed}
    approved_claim_ids = {
        claim["claim_id"] for claim in approved.get("claims") or []
        if isinstance(claim, dict) and "claim_id" in claim
    }
    candidate_claim_ids = {
        claim["claim_id"] for claim in candidate.get("claims") or []
        if isinstance(claim, dict) and "claim_id" in claim
    }
    checks["claim_ids"] = {
        "extra": sorted(candidate_claim_ids - approved_claim_ids),
        "passed": candidate_claim_ids <= approved_claim_ids,
    }
    accepted = (
        approved_claim_gate["passed"]
        and candidate_claim_gate["passed"]
        and all(item["passed"] for item in checks.values())
    )
    return {
        "status": "finalized" if accepted else "rejected_source_lock",
        "accepted": accepted,
        "schema_validation": {
            "approved_claims": approved_claim_gate,
            "candidate_claims": candidate_claim_gate,
        },
        "checks": checks,
        "candidate": candidate if accepted else None,
    }


def load_payload(args: argparse.Namespace) -> dict:
    if args.input_json:
        return json.loads(args.input_json)
    if args.input_file:
        return json.loads(Path(args.input_file).read_text(encoding="utf-8"))
    raise ValueError("one of --input-json or --input-file is required")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--operation", choices=["calculate", "gate", "finalize"], default="calculate")
    parser.add_argument("--input-json")
    parser.add_argument("--input-file")
    parser.add_argument("--out-dir")
    args = parser.parse_args()
    try:
        payload = load_payload(args)
        if args.operation == "calculate":
            full, compact = calculate(payload, Path(args.out_dir) if args.out_dir else None)
            output = {"status": "ok", "full": full, "compact": compact}
        elif args.operation == "gate":
            output = {"status": "ok", "gates": run_gates(payload)}
        else:
            output = finalize(payload)
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        output = {"status": "error", "error": str(exc)}
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if output.get("status") != "error" else 2


if __name__ == "__main__":
    sys.exit(main())
