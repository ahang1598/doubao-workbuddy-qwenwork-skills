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
    "exchange_filing",
    "official_organization",
    "authoritative_physical_data",
}
DATABASE_TYPES = {
    "structured_financial_database",
    "authoritative_market_database",
}
NON_CURRENT_PARAMETER_ORIGINS = {
    "adjacent_rule",
    "prior_version",
    "other_jurisdiction",
    "industry_experience",
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
            if claim.get("supported") is not True:
                errors.append(f"{claim_id}: critical claim is unsupported")
        published = date_value(claim.get("published_at"))
        if as_of and published and published > as_of:
            errors.append(f"{claim_id}: source is after as_of")
        if not claim.get("supported", False):
            warnings.append(f"{claim_id}: unsupported; preserve as unknown")
        parameter_origin = claim.get("parameter_origin", "current_event")
        if (
            parameter_origin in NON_CURRENT_PARAMETER_ORIGINS
            and claim.get("asserted_as_current") is True
        ):
            errors.append(
                f"{claim_id}: non-current parameter cannot be asserted as current"
            )
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
