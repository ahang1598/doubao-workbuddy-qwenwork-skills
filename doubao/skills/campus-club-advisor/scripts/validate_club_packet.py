#!/usr/bin/env python3
"""Validate input or scored-output JSON for campus-club-advisor."""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any


VERIFICATION_STATUSES = {
    "verified_current",
    "verified_exists",
    "probable",
    "stale",
    "unverified",
    "conflict",
}
OFFICIAL_SOURCE_TYPES = {"school_official", "supervising_unit"}
RECOMMENDATION_STATES = {
    "recommended",
    "recommended_recruitment_unconfirmed",
    "hold_needs_profile",
    "hold_verification",
    "excluded",
}


def _is_list_of_strings(value: Any) -> bool:
    return isinstance(value, list) and all(
        isinstance(item, str) and item.strip() for item in value
    )


def _date_value(value: Any) -> date | None:
    if not isinstance(value, str) or value == "unknown":
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _source_age_days(source: dict[str, Any], as_of: date) -> int | None:
    published = _date_value(source.get("published_or_updated_at"))
    if published is None or published > as_of:
        return None
    return (as_of - published).days


def validate_input(data: dict[str, Any], as_of: date | None = None) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    profile = data.get("profile")
    if not isinstance(profile, dict):
        return ["profile must be an object"], warnings

    for field in ("interests", "goals"):
        if not _is_list_of_strings(profile.get(field)):
            errors.append(f"profile.{field} must be a non-empty string array")

    time_info = profile.get("time")
    if not isinstance(time_info, dict):
        errors.append("profile.time must be an object")
    elif not isinstance(time_info.get("hours_per_week_available"), (int, float)):
        errors.append("profile.time.hours_per_week_available must be numeric")

    clubs = data.get("clubs")
    if not isinstance(clubs, list) or not clubs:
        errors.append("clubs must be a non-empty array")
        return errors, warnings

    ids: set[str] = set()
    profile_school = profile.get("school")

    weights = data.get("weights", {})
    if not isinstance(weights, dict):
        errors.append("weights must be an object")
    else:
        known_weights = []
        for key, value in weights.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                errors.append(f"weights.{key} must be numeric")
            elif value < 0:
                errors.append(f"weights.{key} must be non-negative")
            else:
                known_weights.append(float(value))
        if weights and not sum(known_weights):
            errors.append("at least one weight must be positive")

    for index, club in enumerate(clubs):
        prefix = f"clubs[{index}]"
        if not isinstance(club, dict):
            errors.append(f"{prefix} must be an object")
            continue
        club_id = club.get("id")
        if not isinstance(club_id, str) or not club_id.strip():
            errors.append(f"{prefix}.id is required")
        elif club_id in ids:
            errors.append(f"{prefix}.id is duplicated: {club_id}")
        else:
            ids.add(club_id)
        if not isinstance(club.get("name"), str) or not club["name"].strip():
            errors.append(f"{prefix}.name is required")
        club_school = club.get("school")
        if (
            isinstance(profile_school, str)
            and profile_school.strip()
            and isinstance(club_school, str)
            and club_school.strip()
            and profile_school.strip() != club_school.strip()
        ):
            errors.append(f"{prefix}.school does not match profile.school")
        if not isinstance(club.get("attributes"), dict):
            errors.append(f"{prefix}.attributes must be an object")

        verification = club.get("verification")
        if not isinstance(verification, dict):
            errors.append(f"{prefix}.verification must be an object")
            continue
        status = verification.get("status")
        if status not in VERIFICATION_STATUSES:
            errors.append(f"{prefix}.verification.status is invalid: {status}")
            continue
        checked_at = _date_value(verification.get("checked_at"))
        if checked_at is None:
            errors.append(f"{prefix}.verification.checked_at must be YYYY-MM-DD")

        sources = verification.get("sources")
        if not isinstance(sources, list):
            errors.append(f"{prefix}.verification.sources must be an array")
            continue
        official_sources = []
        current_official_sources = []
        recent_official_sources = []
        stale_official_sources = []
        record_as_of = as_of or checked_at or date.today()
        for source_index, source in enumerate(sources):
            source_prefix = f"{prefix}.verification.sources[{source_index}]"
            if not isinstance(source, dict):
                errors.append(f"{source_prefix} must be an object")
                continue
            if not isinstance(source.get("title"), str) or not source["title"].strip():
                errors.append(f"{source_prefix}.title is required")
            if not isinstance(source.get("publisher"), str) or not source["publisher"].strip():
                errors.append(f"{source_prefix}.publisher is required")
            source_date = source.get("published_or_updated_at")
            if not isinstance(source_date, str) or not source_date.strip():
                errors.append(f"{source_prefix}.published_or_updated_at is required")
            elif source_date != "unknown" and _date_value(source_date) is None:
                errors.append(f"{source_prefix}.published_or_updated_at must be YYYY-MM-DD or unknown")
            source_type = source.get("source_type")
            if not isinstance(source_type, str) or not source_type.strip():
                errors.append(f"{source_prefix}.source_type is required")
            supports = source.get("supports")
            if not _is_list_of_strings(supports):
                errors.append(f"{source_prefix}.supports must be a non-empty string array")
            url = source.get("url")
            if not isinstance(url, str) or not url.startswith(("http://", "https://")):
                errors.append(f"{source_prefix}.url must be an HTTP(S) URL")
            supports_existence = isinstance(supports, list) and "existence" in supports
            if source_type in OFFICIAL_SOURCE_TYPES and supports_existence:
                official_sources.append(source)
                published = _date_value(source_date)
                if published and published > record_as_of:
                    errors.append(f"{source_prefix}.published_or_updated_at cannot be in the future")
                elif published and (record_as_of - published).days <= 366:
                    current_official_sources.append(source)
                if published and published <= record_as_of:
                    if (record_as_of - published).days <= 1095:
                        recent_official_sources.append(source)
                    else:
                        stale_official_sources.append(source)
            elif source_type in OFFICIAL_SOURCE_TYPES and not supports_existence:
                warnings.append(f"{source_prefix} is official but does not support existence")

        if status in {"verified_current", "verified_exists"} and not official_sources:
            errors.append(f"{prefix} needs a school official/supervising-unit source")
        if status == "verified_current" and not current_official_sources:
            errors.append(f"{prefix} verified_current needs a dated official source within 12 months")
        if status == "verified_exists" and not recent_official_sources:
            errors.append(f"{prefix} verified_exists needs an official source within 36 months")
        if status == "stale" and not stale_official_sources:
            warnings.append(f"{prefix} stale should cite an official source older than 36 months")
        if status in {"probable", "stale", "unverified", "conflict"}:
            warnings.append(f"{prefix} must stay outside the confirmed recommendation section")

    return errors, warnings


def validate_packet(data: dict[str, Any], as_of: date | None = None) -> tuple[list[str], list[str]]:
    """Public deterministic contract used by QA fixtures.

    ``as_of`` makes age-boundary tests reproducible; production callers may
    omit it and the validator uses each record's checked_at date.
    """
    return validate_input(data, as_of=as_of)


def validate_output(data: dict[str, Any]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    clubs = data.get("clubs")
    if not isinstance(clubs, list):
        return ["clubs must be an array"], warnings
    for index, club in enumerate(clubs):
        prefix = f"clubs[{index}]"
        if not isinstance(club, dict):
            errors.append(f"{prefix} must be an object")
            continue
        state = club.get("recommendation_state")
        if state not in RECOMMENDATION_STATES:
            errors.append(f"{prefix}.recommendation_state is invalid: {state}")
        score = club.get("match_score")
        if score is not None and not isinstance(score, (int, float)):
            errors.append(f"{prefix}.match_score must be numeric or null")
        coverage = club.get("coverage")
        if not isinstance(coverage, (int, float)) or not 0 <= coverage <= 1:
            errors.append(f"{prefix}.coverage must be between 0 and 1")
        verification = club.get("verification") or {}
        status = verification.get("status")
        checked_at = _date_value(verification.get("checked_at"))
        sources = verification.get("sources")
        if status in {"verified_current", "verified_exists"}:
            if checked_at is None:
                errors.append(f"{prefix}.verification.checked_at must be YYYY-MM-DD")
            if not isinstance(sources, list) or not sources:
                errors.append(f"{prefix}.verification.sources must be a non-empty array")
                sources = []
            for source_index, source in enumerate(sources):
                source_prefix = f"{prefix}.verification.sources[{source_index}]"
                if not isinstance(source, dict):
                    errors.append(f"{source_prefix} must be an object")
                    continue
                if not isinstance(source.get("title"), str) or not source["title"].strip():
                    errors.append(f"{source_prefix}.title is required")
                if not isinstance(source.get("publisher"), str) or not source["publisher"].strip():
                    errors.append(f"{source_prefix}.publisher is required")
                if _date_value(source.get("published_or_updated_at")) is None:
                    errors.append(f"{source_prefix}.published_or_updated_at must be YYYY-MM-DD")
                if not isinstance(source.get("url"), str) or not source["url"].startswith(("http://", "https://")):
                    errors.append(f"{source_prefix}.url must be an HTTP(S) URL")
                if not isinstance(source.get("source_type"), str) or not source["source_type"].strip():
                    errors.append(f"{source_prefix}.source_type is required")
                if not _is_list_of_strings(source.get("supports")):
                    errors.append(f"{source_prefix}.supports must be a non-empty string array")
        if state and state.startswith("recommended") and status not in {
            "verified_current",
            "verified_exists",
        }:
            errors.append(f"{prefix} recommends a club without verified status")
        if state and state.startswith("recommended") and status == "verified_exists":
            sources = sources or []
            if checked_at is None or not any(
                source.get("source_type") in OFFICIAL_SOURCE_TYPES
                and "existence" in (source.get("supports") or [])
                and (_source_age_days(source, checked_at) is not None)
                and _source_age_days(source, checked_at) <= 1095
                for source in sources
                if isinstance(source, dict)
            ):
                errors.append(f"{prefix} recommended verified_exists is older than 36 months")
        if state == "recommended" and club.get("vetoes"):
            errors.append(f"{prefix} recommends a club with vetoes")
        if coverage < 0.60 and state and state.startswith("recommended"):
            errors.append(f"{prefix} recommends a club with coverage below 0.60")
    return errors, warnings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="JSON file to validate")
    parser.add_argument(
        "--kind",
        choices=("input", "output"),
        default="input",
        help="Validation mode (default: input)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"valid": False, "errors": [str(exc)]}, ensure_ascii=False))
        return 2

    if not isinstance(data, dict):
        errors, warnings = ["root must be an object"], []
    elif args.kind == "input":
        errors, warnings = validate_input(data)
    else:
        errors, warnings = validate_output(data)
    print(
        json.dumps(
            {"valid": not errors, "errors": errors, "warnings": warnings},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
