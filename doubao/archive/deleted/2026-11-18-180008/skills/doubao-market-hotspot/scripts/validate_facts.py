#!/usr/bin/env python3
"""Shared V3 fact-ledger validator. Stdlib only."""

import argparse
import json
import re
import sys
from pathlib import Path


ALLOWED_TYPES = {
    "fact",
    "estimate",
    "inference",
    "assumption",
    "management_claim",
    "data_gap",
}
ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]*$")
MONEY_UNITS = {"currency", "currency_unit", "money"}


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def has_value(value):
    return value is not None and value != "" and value != [] and value != {}


def get_path(data, dotted):
    current = data
    for part in dotted.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("facts")
    parser.add_argument(
        "--config",
        default=str(Path(__file__).resolve().parent.parent / "config" / "runtime.json"),
    )
    parser.add_argument("--capabilities-out")
    args = parser.parse_args()
    try:
        data = load(args.facts)
        config = load(args.config)
    except Exception as error:
        print(f"ERROR: cannot load input: {error}")
        return 2

    errors = []
    warnings = []
    meta = data.get("meta")
    if not isinstance(meta, dict):
        errors.append("meta missing or invalid")
        meta = {}
    for key in ("case_type", "as_of", "market_or_jurisdiction", "mode", "task_id"):
        if not has_value(meta.get(key)):
            errors.append(f"meta.{key} missing")
    if meta.get("case_type") and meta["case_type"] != config["case_type"]:
        errors.append(f"meta.case_type must be {config['case_type']}")
    if meta.get("mode") and meta["mode"] not in config["modes"]:
        errors.append(f"meta.mode unsupported: {meta['mode']}")

    payload = data.get("payload")
    if not isinstance(payload, dict):
        errors.append("payload missing or invalid")
        payload = {}
    mode_config = config["modes"].get(meta.get("mode"), {})
    for key in mode_config.get("required_payload", []):
        if not has_value(payload.get(key)):
            errors.append(f"payload.{key} missing or empty for mode {meta.get('mode')}")

    claims = data.get("claims")
    if not isinstance(claims, list):
        errors.append("claims must be a list")
        claims = []
    seen = set()
    for index, claim in enumerate(claims):
        prefix = f"claims[{index}]"
        if not isinstance(claim, dict):
            errors.append(f"{prefix} invalid")
            continue
        claim_id = claim.get("claim_id")
        if not isinstance(claim_id, str) or not ID_RE.fullmatch(claim_id):
            errors.append(f"{prefix}.claim_id invalid")
        elif claim_id in seen:
            errors.append(f"{prefix}.claim_id duplicate")
        else:
            seen.add(claim_id)

    fact_keys = {}
    for index, claim in enumerate(claims):
        if not isinstance(claim, dict):
            continue
        prefix = f"claims[{index}]"
        claim_type = claim.get("claim_type")
        if claim_type not in ALLOWED_TYPES:
            errors.append(f"{prefix}.claim_type invalid")
        if not has_value(claim.get("statement")):
            errors.append(f"{prefix}.statement missing")
        if claim_type in {"fact", "management_claim"}:
            if not has_value(claim.get("source")):
                errors.append(f"{prefix}.source missing")
            if not has_value(claim.get("source_date")):
                errors.append(f"{prefix}.source_date missing")
        if claim_type == "management_claim" and not has_value(
            claim.get("source_type")
        ):
            errors.append(f"{prefix}.source_type missing for management_claim")
        if claim.get("value") is not None and not has_value(claim.get("unit")):
            errors.append(f"{prefix}.unit missing")
        if claim.get("unit") in MONEY_UNITS and not has_value(claim.get("currency")):
            errors.append(f"{prefix}.currency missing for monetary value")
        input_claims = claim.get("input_claims", [])
        if claim.get("calculation") and not input_claims:
            errors.append(f"{prefix}.input_claims missing")
        if input_claims is not None and not isinstance(input_claims, list):
            errors.append(f"{prefix}.input_claims must be a list")
            input_claims = []
        for dependency in input_claims:
            if dependency not in seen:
                errors.append(f"{prefix}.input_claims unknown: {dependency}")
        evidence = claim.get("evidence", [])
        if evidence is not None and not isinstance(evidence, list):
            errors.append(f"{prefix}.evidence must be a list")
            evidence = []
        for dependency in evidence:
            if dependency not in seen:
                errors.append(f"{prefix}.evidence unknown: {dependency}")
        if claim_type in {"estimate", "inference", "assumption"} and claim.get(
            "confidence"
        ) not in {"high", "medium", "low"}:
            errors.append(f"{prefix}.confidence missing")
        if claim_type == "fact":
            key = (claim.get("statement"), claim.get("period"), claim.get("unit"))
            if key in fact_keys and fact_keys[key] != claim.get("value"):
                errors.append(f"{prefix} conflicts with another fact for same period")
            fact_keys[key] = claim.get("value")

    assumptions = data.get("assumptions", [])
    if not isinstance(assumptions, list):
        errors.append("assumptions must be a list")
    data_gaps = data.get("data_gaps", [])
    if not isinstance(data_gaps, list):
        errors.append("data_gaps must be a list")
        data_gaps = []
    for index, gap in enumerate(data_gaps):
        if isinstance(gap, str):
            if len(gap.strip()) < 8:
                warnings.append(f"data_gaps[{index}] is too vague")
        elif isinstance(gap, dict):
            if not has_value(gap.get("missing")) or not has_value(gap.get("impact")):
                errors.append(f"data_gaps[{index}] requires missing and impact")
        else:
            errors.append(f"data_gaps[{index}] invalid")

    capabilities = {}
    for name, requirements in config.get("capabilities", {}).items():
        missing = [
            dotted for dotted in requirements if not has_value(get_path(data, dotted))
        ]
        capabilities[name] = {"allowed": not missing, "missing": missing}
        if missing:
            warnings.append(f"{name}=false missing={','.join(missing)}")
    if args.capabilities_out:
        Path(args.capabilities_out).write_text(
            json.dumps(capabilities, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    for item in warnings:
        print("WARNING:", item)
    for item in errors:
        print("ERROR:", item)
    print(
        f"SUMMARY errors={len(errors)} warnings={len(warnings)} "
        f"claims={len(claims)} capabilities={json.dumps(capabilities, ensure_ascii=False)}"
    )
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
