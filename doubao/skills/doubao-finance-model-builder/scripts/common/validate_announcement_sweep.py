#!/usr/bin/env python3
"""Validate the official latest-announcement sweep before financial modeling."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import date
from pathlib import Path
from typing import Any


ROLES = {"announcement_search_result", "announcement_document"}
DISPOSITIONS = {"incorporated", "not_material", "blocking"}
MARKER = re.compile(r"\[DISCOVERED_ANNOUNCEMENT_ID:([^\]]+)\]")
NO_RESULTS = "[NO_RELEVANT_ANNOUNCEMENTS]"


def parse_date(value: Any, field: str, errors: list[str]) -> date | None:
    if not isinstance(value, str):
        errors.append(f"{field} must be YYYY-MM-DD")
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        errors.append(f"{field} must be YYYY-MM-DD")
        return None


def safe_file(root: Path, value: Any, field: str, errors: list[str]) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{field} is required")
        return None
    candidate = (root / value).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        errors.append(f"{field} escapes root")
        return None
    if not candidate.is_file():
        errors.append(f"{field} file not found: {value}")
        return None
    return candidate


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate(payload: dict[str, Any], root: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if payload.get("schema_version") != "1.0":
        errors.append("schema_version must be 1.0")
    if not isinstance(payload.get("company"), str) or not payload["company"].strip():
        errors.append("company is required")
    identifiers = payload.get("security_identifiers")
    if not isinstance(identifiers, list) or not identifiers or not all(isinstance(x, str) and x.strip() for x in identifiers):
        errors.append("security_identifiers must be a non-empty string list")
        identifiers = []
    valuation_date = parse_date(payload.get("valuation_date"), "valuation_date", errors)
    cutoff = parse_date(payload.get("information_cutoff_date"), "information_cutoff_date", errors)
    if valuation_date and cutoff and cutoff > valuation_date:
        errors.append("information_cutoff_date cannot be later than valuation_date")

    evidence_by_id: dict[str, dict[str, Any]] = {}
    texts: dict[str, str] = {}
    evidence = payload.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        errors.append("evidence must be a non-empty list")
        evidence = []
    for index, item in enumerate(evidence):
        prefix = f"evidence[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        evidence_id = item.get("evidence_id")
        if not isinstance(evidence_id, str) or not evidence_id.strip() or evidence_id in evidence_by_id:
            errors.append(f"{prefix}.evidence_id must be non-empty and unique")
            continue
        evidence_by_id[evidence_id] = item
        if item.get("role") not in ROLES:
            errors.append(f"{prefix}.role is invalid")
        if item.get("authority_tier") != "primary":
            errors.append(f"{prefix}.authority_tier must be primary")
        if not isinstance(item.get("url"), str) or not item["url"].startswith(("http://", "https://")):
            errors.append(f"{prefix}.url must be an HTTP(S) URL")
        published = parse_date(item.get("published_date"), f"{prefix}.published_date", errors)
        if published and cutoff and published > cutoff:
            errors.append(f"{prefix}.published_date is after information_cutoff_date")
        for file_key, hash_key in (("local_file", "sha256"), ("text_file", "text_sha256")):
            path = safe_file(root, item.get(file_key), f"{prefix}.{file_key}", errors)
            expected = item.get(hash_key)
            if path and (not isinstance(expected, str) or sha256(path) != expected.lower()):
                errors.append(f"{prefix}.{hash_key} mismatch")
            if path and file_key == "text_file":
                text = path.read_text(encoding="utf-8", errors="replace")
                texts[evidence_id] = text
                names = [payload.get("company", ""), *identifiers]
                if not any(name and name.lower() in text.lower() for name in names):
                    errors.append(f"{prefix}.text_file does not identify the issuer")

    discovered: set[str] = set()
    sweeps = payload.get("sweeps")
    if not isinstance(sweeps, list) or not sweeps:
        errors.append("sweeps must be a non-empty list")
        sweeps = []
    for index, sweep in enumerate(sweeps):
        prefix = f"sweeps[{index}]"
        if not isinstance(sweep, dict):
            errors.append(f"{prefix} must be an object")
            continue
        start = parse_date(sweep.get("search_start_date"), f"{prefix}.search_start_date", errors)
        end = parse_date(sweep.get("search_end_date"), f"{prefix}.search_end_date", errors)
        if start and end and start > end:
            errors.append(f"{prefix} search_start_date is after search_end_date")
        if end and cutoff and end != cutoff:
            errors.append(f"{prefix}.search_end_date must equal information_cutoff_date")
        if not isinstance(sweep.get("official_entry_url"), str) or not sweep["official_entry_url"].startswith(("http://", "https://")):
            errors.append(f"{prefix}.official_entry_url must be an HTTP(S) URL")
        queries = sweep.get("queries")
        if not isinstance(queries, list) or not queries or not all(isinstance(x, str) and x.strip() for x in queries):
            errors.append(f"{prefix}.queries must be a non-empty string list")
        result_ids = sweep.get("result_evidence_ids")
        if not isinstance(result_ids, list) or not result_ids:
            errors.append(f"{prefix}.result_evidence_ids must be non-empty")
            result_ids = []
        if sweep.get("completed") is not True or sweep.get("coverage_gaps") != []:
            errors.append(f"{prefix} must be completed with no coverage gaps")
        for evidence_id in result_ids:
            item = evidence_by_id.get(evidence_id)
            if not item or item.get("role") != "announcement_search_result":
                errors.append(f"{prefix} references invalid search-result evidence: {evidence_id}")
                continue
            text = texts.get(evidence_id, "")
            markers = set(MARKER.findall(text))
            if markers and NO_RESULTS in text:
                errors.append(f"{prefix} search result contains both discovery and no-result markers")
            if not markers and NO_RESULTS not in text:
                errors.append(f"{prefix} search result lacks discovery or no-result marker")
            discovered |= markers

    announcements = payload.get("announcements")
    if not isinstance(announcements, list):
        errors.append("announcements must be a list")
        announcements = []
    announcement_ids: set[str] = set()
    blocking = 0
    for index, item in enumerate(announcements):
        prefix = f"announcements[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        announcement_id = item.get("announcement_id")
        if not isinstance(announcement_id, str) or not announcement_id.strip() or announcement_id in announcement_ids:
            errors.append(f"{prefix}.announcement_id must be non-empty and unique")
            continue
        announcement_ids.add(announcement_id)
        evidence_item = evidence_by_id.get(item.get("evidence_id"))
        if not evidence_item or evidence_item.get("role") != "announcement_document":
            errors.append(f"{prefix}.evidence_id must reference announcement_document evidence")
        published = parse_date(item.get("published_date"), f"{prefix}.published_date", errors)
        if published and cutoff and published > cutoff:
            errors.append(f"{prefix}.published_date is after information_cutoff_date")
        if not isinstance(item.get("category"), str) or not item["category"].strip():
            errors.append(f"{prefix}.category is required")
        disposition = item.get("disposition")
        if disposition not in DISPOSITIONS:
            errors.append(f"{prefix}.disposition is invalid")
        if disposition == "blocking":
            blocking += 1
        if not isinstance(item.get("rationale"), str) or not item["rationale"].strip():
            errors.append(f"{prefix}.rationale is required")
        if disposition == "incorporated" and not item.get("affected_model_fields"):
            errors.append(f"{prefix}.affected_model_fields is required when incorporated")

    missing = discovered - announcement_ids
    unlisted = announcement_ids - discovered
    if missing:
        errors.append("discovered announcements not dispositioned: " + ", ".join(sorted(missing)))
    if unlisted:
        errors.append("announcements absent from official search results: " + ", ".join(sorted(unlisted)))

    status = "FAIL" if errors or blocking else "PASS"
    return {
        "model_status_code": status,
        "errors": errors,
        "warnings": warnings,
        "discovered_announcement_count": len(discovered),
        "blocking_announcement_count": blocking,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="验证最新公告增量检索证据")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.manifest.read_text(encoding="utf-8"))
    result = validate(payload, args.root)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if result["model_status_code"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
