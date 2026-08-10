#!/usr/bin/env python3
"""Validate a compact Search evidence ledger before analysis."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


PRIMARY_TYPES = {
    "regulator_filing",
    "company_ir",
    "company_primary",
    "counterparty_primary",
    "investor_primary",
    "government_rule",
    "regulator",
    "official_program",
    "law_or_regulation",
    "issuing_authority",
    "implementing_authority",
    "industry_primary",
    "exchange_market_data",
}
DATABASE_TYPES = {
    "structured_financial_database",
    "authoritative_market_database",
}
P2_CORE_SLOTS = {
    "latest_annual_report",
    "latest_interim_report",
    "cashflow_statement",
}


def date_value(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def validate(payload):
    errors = []
    warnings = []
    as_of = date_value(payload.get("as_of"))
    freeze = payload.get("freeze_point", {})
    for field in ("latest_fy", "latest_reported_period", "checked_at"):
        if not freeze.get(field):
            errors.append(f"freeze_point.{field} missing")
    if not freeze.get("ir_or_exchange_checked"):
        errors.append("freeze_point IR/exchange probe not completed")
    if freeze.get("newer_filing_exists"):
        errors.append("latest_reported_period is stale at freeze point")
    slots = payload.get("evidence_slots", [])
    if not 8 <= len(slots) <= 15:
        errors.append("evidence_slots must contain 8-15 required items")
    for index, slot in enumerate(slots):
        for field in ("id", "fact_needed", "allowed_source_types", "period", "affected_claim_ids", "status"):
            if not slot.get(field):
                errors.append(f"evidence_slots[{index}].{field} missing")
    if payload.get("contract_version") == "P2":
        by_kind = {
            slot.get("slot_kind"): slot for slot in slots if slot.get("slot_kind")
        }
        required_core = set(P2_CORE_SLOTS)
        if payload.get("company_cash_metric_used"):
            required_core.add("company_cash_metric_definition")
        for kind in sorted(required_core):
            slot = by_kind.get(kind)
            if not slot:
                errors.append(f"P2 core evidence slot missing: {kind}")
                continue
            availability = slot.get("availability")
            status = slot.get("status")
            if availability == "available":
                if status != "covered":
                    errors.append(f"P2 available core slot not covered: {kind}")
                if slot.get("source_type") not in PRIMARY_TYPES:
                    errors.append(f"P2 core slot lacks first-party source: {kind}")
                if urlparse(slot.get("source_url", "")).scheme not in {"http", "https"}:
                    errors.append(f"P2 core slot lacks valid source URL: {kind}")
            elif availability == "unavailable":
                if not slot.get("access_attempt"):
                    errors.append(f"P2 unavailable core slot lacks access_attempt: {kind}")
            else:
                errors.append(f"P2 core slot availability invalid: {kind}")
        if payload.get("analysis_ready") is True and any(
            by_kind.get(kind, {}).get("availability") == "available"
            and by_kind.get(kind, {}).get("status") != "covered"
            for kind in required_core
        ):
            errors.append("analysis_ready set before available first-party core slots covered")
        if payload.get("global_degraded") and all(
            by_kind.get(kind, {}).get("status") == "covered"
            for kind in P2_CORE_SLOTS
        ):
            errors.append("global degradation invalid when first-party core is covered")
    claims = payload.get("claims")
    if not isinstance(claims, list) or not claims:
        return {
            "passed": False,
            "errors": ["claims must be a non-empty list"],
            "warnings": [],
            "stats": {"claims": 0, "critical": 0, "primary_critical": 0},
        }
    critical = 0
    primary_critical = 0
    seen = set()
    for index, claim in enumerate(claims):
        claim_id = claim.get("id") or f"claim-{index + 1}"
        if claim_id in seen:
            errors.append(f"{claim_id}: duplicate id")
        seen.add(claim_id)
        source_type = claim.get("source_type")
        database_evidence = source_type in DATABASE_TYPES
        url = claim.get("source_url", "")
        if database_evidence:
            for field in (
                "provider",
                "dataset",
                "record_id",
                "field",
                "as_of",
            ):
                if claim.get(field) in {None, ""}:
                    errors.append(
                        f"{claim_id}: database evidence missing {field}"
                    )
            lineage_url = claim.get("underlying_source_url", "")
            authoritative = bool(claim.get("authoritative_database"))
            if (
                not authoritative
                and urlparse(lineage_url).scheme not in {"http", "https"}
            ):
                errors.append(
                    f"{claim_id}: database evidence lacks authoritative "
                    "lineage"
                )
            if claim.get("claim_kind") == "numeric":
                for field in ("value", "unit", "currency", "period"):
                    if claim.get(field) in {None, ""}:
                        errors.append(
                            f"{claim_id}: numeric database evidence "
                            f"missing {field}"
                        )
        elif urlparse(url).scheme not in {"http", "https"}:
            errors.append(f"{claim_id}: missing valid source URL")
        if not claim.get("claim"):
            errors.append(f"{claim_id}: empty claim")
        if claim.get("critical"):
            critical += 1
            primary_database = database_evidence and (
                bool(claim.get("authoritative_database"))
                or urlparse(
                    claim.get("underlying_source_url", "")
                ).scheme
                in {"http", "https"}
            )
            if source_type not in PRIMARY_TYPES and not primary_database:
                errors.append(f"{claim_id}: critical claim lacks primary source")
            else:
                primary_critical += 1
            for field in claim.get("required_context", []):
                if claim.get(field) in {None, ""}:
                    errors.append(f"{claim_id}: missing {field}")
        published = date_value(claim.get("published_at"))
        if as_of and published and published > as_of:
            errors.append(f"{claim_id}: source is after as_of")
        if not claim.get("supported", False):
            warnings.append(f"{claim_id}: unsupported; preserve as unknown")
        if claim.get("conflict") and not claim.get("conflict_note"):
            errors.append(f"{claim_id}: conflict lacks conflict_note")
    return {
        "passed": not errors,
        "errors": errors,
        "warnings": warnings,
        "stats": {
            "claims": len(claims),
            "critical": critical,
            "primary_critical": primary_critical,
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("ledger")
    parser.add_argument("--output")
    args = parser.parse_args()
    payload = json.loads(Path(args.ledger).read_text(encoding="utf-8"))
    result = validate(payload)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
