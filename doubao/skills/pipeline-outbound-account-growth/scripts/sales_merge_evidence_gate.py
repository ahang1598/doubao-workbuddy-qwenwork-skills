#!/usr/bin/env python3
"""Executable evidence rules for the ten absorbed Sales merge/mode sources."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from pipeline_forecast import evaluate_claims


EXPECTED_SLUGS = {
    "plan-deal-strategy",
    "build-competitive-brief",
    "build-business-case",
    "analyze-account-signals",
    "enrich-company-and-contact-data",
    "prioritize-accounts",
    "review-forecast",
    "sales-company-research",
    "find-customer-quotes",
    "find-key-internal-sources",
}
EXPECTED_CONNECTORS = {
    "salesforce", "hubspot", "apollo", "zoominfo", "answers-ask-user-input", "index"
}
REQUIRED_ARTIFACTS = {"merge_coverage_result", "claim_ledger", "evidence_compact"}
ACCOUNT_BUCKETS = {"优先跟进", "持续观察", "暂停触达"}


def base_checks(fixture: dict) -> List[str]:
    failures: List[str] = []
    if fixture.get("source_slug") not in EXPECTED_SLUGS:
        failures.append("source_slug not in ten-item Sales coverage set")
    claim_gate = evaluate_claims(fixture.get("claims"))
    failures.extend(f"claim_schema: {item}" for item in claim_gate["failures"])
    available = set(fixture.get("available_artifacts") or [])
    missing = sorted(REQUIRED_ARTIFACTS - available)
    if missing:
        failures.append(f"missing fixed artifacts: {missing}")
    evidence = fixture.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        failures.append("evidence must be a non-empty list")
    else:
        for index, item in enumerate(evidence):
            if not isinstance(item, dict) or not all(item.get(key) for key in ("evidence_id", "evidence_type", "source_id")):
                failures.append(f"evidence[{index}] missing id/type/source")
    return failures


def rule_checks(fixture: dict) -> List[str]:
    slug = fixture["source_slug"]
    facts = fixture.get("facts") or {}
    failures: List[str] = []
    if slug == "plan-deal-strategy":
        if not facts.get("deal_anchor") or facts.get("truth_source") != "crm_truth":
            failures.append("deal strategy requires anchored CRM truth")
        if not facts.get("actions") or any(not action.get("risk_id") for action in facts["actions"]):
            failures.append("every action must link to a risk")
    elif slug == "build-competitive-brief":
        if facts.get("competitor_presence") == "unconfirmed" and facts.get("posture") != "预防性应对":
            failures.append("unconfirmed competitor must remain preventive")
        if facts.get("unsupported_claims"):
            failures.append("unsupported competitive claims present")
        if not facts.get("禁用表述"):
            failures.append("competitive output requires prohibited-language guidance")
    elif slug == "build-business-case":
        if set(facts.get("input_labels") or []) != {"Known", "Inferred", "Assumed", "Missing"}:
            failures.append("business case must preserve four evidence labels")
        if facts.get("calculation_tool") != "roi_value_model":
            failures.append("business case must route arithmetic to roi_value_model")
    elif slug == "analyze-account-signals":
        if facts.get("delta_claimed") and not facts.get("prior_snapshot_id"):
            failures.append("delta requires prior snapshot")
        if facts.get("crm_overridden"):
            failures.append("communications cannot override CRM truth")
    elif slug == "enrich-company-and-contact-data":
        if facts.get("input_ids") != facts.get("output_ids"):
            failures.append("enrichment set conservation failed")
        if not facts.get("unresolved_separate"):
            failures.append("unresolved entities must remain separate")
    elif slug == "prioritize-accounts":
        rows = facts.get("accounts") or []
        ids = [row.get("account_id") for row in rows]
        if len(ids) != len(set(ids)):
            failures.append("account appears in more than one bucket")
        if any(row.get("bucket") not in ACCOUNT_BUCKETS for row in rows):
            failures.append("invalid neutral account bucket")
        if facts.get("unknown_ranked"):
            failures.append("unknown account cannot be ranked")
    elif slug == "review-forecast":
        if not facts.get("current_snapshot_id"):
            failures.append("forecast requires current truth snapshot")
        if facts.get("movement_claimed") and not facts.get("prior_snapshot_id"):
            failures.append("movement requires prior snapshot")
        probabilities = facts.get("probabilities") or []
        if any(not isinstance(value, (int, float)) or value < 0 or value > 1 for value in probabilities):
            failures.append("forecast probability outside 0..1")
        if facts.get("calculation_tool") != "pipeline_forecast":
            failures.append("forecast must route arithmetic to pipeline_forecast")
    elif slug == "sales-company-research":
        if not facts.get("sourced_context") or not facts.get("draft_only") or facts.get("sent"):
            failures.append("research-to-outreach must remain sourced and draft-only")
    elif slug == "find-customer-quotes":
        quote = facts.get("quote") or {}
        if quote.get("verbatim") not in (quote.get("source_text") or ""):
            failures.append("quote is not verbatim from source text")
        if quote.get("speaker_state") != "confirmed_external" or not quote.get("source_id"):
            failures.append("quote speaker/source not grounded")
    elif slug == "find-key-internal-sources":
        if not facts.get("read_only") or not facts.get("canonical_source"):
            failures.append("internal route must be canonical and read-only")
        if facts.get("message_sent") or facts.get("ownership_changed"):
            failures.append("internal routing support performed a side effect")
    return failures


def evaluate_fixture(fixture: dict) -> dict:
    failures = base_checks(fixture)
    if fixture.get("source_slug") in EXPECTED_SLUGS:
        failures.extend(rule_checks(fixture))
    return {
        "fixture_id": fixture.get("fixture_id"),
        "source_slug": fixture.get("source_slug"),
        "passed": not failures,
        "failures": failures,
    }


def evaluate_file(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    fixtures = payload.get("fixtures")
    if not isinstance(fixtures, list):
        raise ValueError("fixtures must be a list")
    results = [evaluate_fixture(fixture) for fixture in fixtures]
    covered = {item["source_slug"] for item in results}
    connector_fixtures = payload.get("connector_fixtures")
    if not isinstance(connector_fixtures, list):
        raise ValueError("connector_fixtures must be a list")
    connector_failures = []
    connector_slugs = set()
    for fixture in connector_fixtures:
        connector_slugs.add(fixture.get("source_slug"))
        if (
            fixture.get("disposition") != "connector_or_tool"
            or fixture.get("layer") != "support"
            or fixture.get("business_decision") is not False
        ):
            connector_failures.append(fixture.get("source_slug"))
    return {
        "passed": (
            all(item["passed"] for item in results)
            and covered == EXPECTED_SLUGS
            and len(results) == 10
            and connector_slugs == EXPECTED_CONNECTORS
            and len(connector_fixtures) == 6
            and not connector_failures
        ),
        "coverage": len(covered & EXPECTED_SLUGS),
        "expected": 10,
        "missing_slugs": sorted(EXPECTED_SLUGS - covered),
        "connector_support_coverage": len(connector_slugs & EXPECTED_CONNECTORS),
        "connector_support_expected": 6,
        "connector_failures": connector_failures,
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture-file", required=True)
    args = parser.parse_args()
    try:
        output = evaluate_file(Path(args.fixture_file))
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        output = {"passed": False, "error": str(exc)}
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if output.get("passed") else 2


if __name__ == "__main__":
    sys.exit(main())
