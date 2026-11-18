#!/usr/bin/env python3
"""Fail-close delivery guard for generic event-impact analysis."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


HARD_GATES = ("primary_source_gate_passed", "semantic_gate_passed")
NON_CURRENT_PARAMETER_ORIGINS = {
    "adjacent_rule",
    "prior_version",
    "other_jurisdiction",
    "industry_experience",
}
IDENTITY_CLAIM_TYPES = {
    "event_identity",
    "event_status",
    "document_role",
    "publication_date",
    "effective_date",
}


class InputError(ValueError):
    pass


def _object(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise InputError(f"{name} must be an object")
    return value


def _list(value: Any, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise InputError(f"{name} must be an array")
    return value


def guard(payload: dict[str, Any]) -> dict[str, Any]:
    payload = _object(payload, "input")
    gates = _object(payload.get("gates", {}), "gates")
    search = _object(payload.get("search", {}), "search")
    claims = _list(payload.get("claims", []), "claims")
    market_evidence = _list(
        payload.get("market_evidence", []), "market_evidence"
    )

    incoming_status = str(payload.get("status", "completed")).lower()
    hard_gate_failures = [name for name in HARD_GATES if gates.get(name) is False]
    status = "failed" if incoming_status == "failed" or hard_gate_failures else incoming_status

    claim_results = []
    external_numeric_claims = []
    unsupported_critical = []
    identity_claims = []
    for index, raw in enumerate(claims):
        claim = _object(raw, f"claims[{index}]")
        claim_id = claim.get("id")
        if not isinstance(claim_id, str) or not claim_id:
            raise InputError(f"claims[{index}].id must be a non-empty string")
        claim_type = claim.get("claim_type")
        supported = claim.get("supported") is True and bool(claim.get("source_ids"))
        origin = claim.get("parameter_origin", "current_event")
        disposition = "deliver_as_supported" if supported else "preserve_as_unknown"
        reasons = []
        if not supported:
            reasons.append("claim_lacks_source_support")
        if claim.get("critical") and not supported:
            unsupported_critical.append(claim_id)
        if claim_type in IDENTITY_CLAIM_TYPES:
            identity_claims.append((claim_id, supported))
        if origin in NON_CURRENT_PARAMETER_ORIGINS:
            disposition = "conditional_scenario_only"
            reasons.append(f"non_current_parameter_origin:{origin}")
        if claim.get("external_experience_numeric") is True or (
            claim.get("claim_kind") == "numeric"
            and origin == "industry_experience"
        ):
            external_numeric_claims.append(claim_id)
        claim_results.append(
            {
                "id": claim_id,
                "supported": supported,
                "disposition": disposition,
                "reasons": reasons,
            }
        )

    identity_stage_passed = bool(identity_claims) and all(
        supported for _, supported in identity_claims
    )
    if not identity_stage_passed:
        status = "failed"

    requested_mode = search.get("mode", "optional")
    effective_mode = requested_mode
    search_actions = []
    if requested_mode == "off" and external_numeric_claims:
        if search.get("can_upgrade", True) and not search.get("user_forbids_search", False):
            effective_mode = "required"
            search_actions.append("upgrade_search_to_required")
        else:
            search_actions.append("remove_or_downgrade_external_numeric_claims")
            for result in claim_results:
                if result["id"] in external_numeric_claims:
                    result["disposition"] = "remove_or_preserve_as_unknown"
                    result["reasons"].append("search_off_external_numeric_claim")

    has_pre_event_baseline = any(
        isinstance(item, dict)
        and item.get("supported") is True
        and item.get("is_pre_event") is True
        for item in market_evidence
    )

    may_enter_scope_stage = identity_stage_passed
    may_enter_impact_stage = identity_stage_passed and not unsupported_critical
    may_deliver = status != "failed"
    return {
        "status": status,
        "incoming_status": incoming_status,
        "hard_gate_failures": hard_gate_failures,
        "may_deliver": may_deliver,
        "query_stage_gate": {
            "identity_and_status_passed": identity_stage_passed,
            "may_enter_scope_and_parameters": may_enter_scope_stage,
            "may_enter_impact_and_market_baseline": may_enter_impact_stage,
        },
        "search": {
            "requested_mode": requested_mode,
            "effective_mode": effective_mode,
            "actions": search_actions,
        },
        "can_assess_priced_in": has_pre_event_baseline,
        "claim_results": claim_results,
        "unsupported_critical_claims": unsupported_critical,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", nargs="?", default="-")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    try:
        if args.input == "-":
            payload = json.load(sys.stdin)
        else:
            payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
        result = guard(payload)
        text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            Path(args.output).write_text(text, encoding="utf-8")
        else:
            sys.stdout.write(text)
        return 0 if result["may_deliver"] else 1
    except (OSError, json.JSONDecodeError, InputError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
