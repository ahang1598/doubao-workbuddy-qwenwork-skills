#!/usr/bin/env python3
"""Validate normalized records for navigate-campus-places-and-services."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any


MODES = {"service_guide", "place_resolution"}
STATUSES = {"verified", "verified_with_caveat", "partial", "unresolved"}
# A club's permanent office is a stable place. Only the event/temporary
# variant needs an event_scope. Keeping the values separate prevents a valid
# permanent-office record from being rejected.
DYNAMIC_PLACE_TYPES = {"club_event", "event", "registration", "exam_room"}
PLACE_TYPES = {
    "building",
    "office",
    "club_office",
    "club_event",
    "event",
    "registration",
    "exam_room",
    "other",
}
SOURCE_TYPES = {"school_official", "transaction_first_party", "user_current_document", "map_spatial"}
SERVICE_CHANNELS = {"online", "offline", "both", "unknown"}
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MAP_ALLOWED_SUPPORTS = {
    "address",
    "coordinates",
    "entrance",
    "entrance_landmark",
    "distance",
    "route",
}


def nonempty(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return value is not None


def valid_iso_date(value: Any) -> bool:
    """Return True only for real calendar dates written as YYYY-MM-DD."""
    if not isinstance(value, str) or not ISO_DATE.fullmatch(value):
        return False
    try:
        dt.date.fromisoformat(value)
    except ValueError:
        return False
    return True


def dotted_field_exists(record: dict[str, Any], field: str) -> bool:
    """Return whether a dotted top-level claim names a non-empty record field."""
    current: Any = record
    for part in field.split("."):
        if not isinstance(current, dict) or part not in current:
            return False
        current = current[part]
    return nonempty(current)


def validate_string_list(value: Any, field: str, errors: list[str], *, required: bool = False) -> None:
    if value is None and not required:
        return
    if not isinstance(value, list):
        errors.append(f"{field} must be an array")
        return
    if required and not value:
        errors.append(f"{field} must be a non-empty array")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        errors.append(f"{field} entries must be non-empty strings")


def validate_source(
    source: Any,
    index: int,
    record: dict[str, Any],
    errors: list[str],
) -> None:
    if not isinstance(source, dict):
        errors.append(f"sources[{index}] must be an object")
        return
    # Required by references/service-record-schema.md for every source.
    for key in ("type", "title", "publisher", "published_or_updated_at", "accessed_at"):
        if not nonempty(source.get(key)):
            errors.append(f"sources[{index}].{key} is required")
    if nonempty(source.get("type")) and source.get("type") not in SOURCE_TYPES:
        errors.append(f"sources[{index}].type must be one of {sorted(SOURCE_TYPES)}")
    supports = source.get("supports")
    if not isinstance(supports, list) or not supports:
        errors.append(f"sources[{index}].supports must be a non-empty array")
    elif any(not isinstance(item, str) or not item.strip() for item in supports):
        errors.append(f"sources[{index}].supports entries must be non-empty strings")
    else:
        if len(supports) != len(set(supports)):
            errors.append(f"sources[{index}].supports entries must be unique")
        for field in supports:
            if isinstance(field, str) and field.strip() and not dotted_field_exists(record, field):
                errors.append(f"sources[{index}].supports references missing or empty field: {field}")
        if source.get("type") == "map_spatial":
            disallowed = sorted(set(supports) - MAP_ALLOWED_SUPPORTS)
            if disallowed:
                errors.append(
                    f"sources[{index}] map_spatial cannot support non-spatial fields: {disallowed}"
                )
    if not nonempty(source.get("url_or_document")):
        errors.append(f"sources[{index}].url_or_document is required")
    accessed_at = source.get("accessed_at")
    if nonempty(accessed_at) and not valid_iso_date(accessed_at):
        errors.append(f"sources[{index}].accessed_at must be a valid calendar date in YYYY-MM-DD")
    published = source.get("published_or_updated_at")
    if nonempty(published) and published != "unknown":
        if not valid_iso_date(published):
            errors.append(
                f"sources[{index}].published_or_updated_at must be a valid calendar date in YYYY-MM-DD or unknown"
            )


def validate_record(record: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(record, dict):
        return ["record must be a JSON object"]

    mode = record.get("mode")
    status = record.get("status")
    if mode not in MODES:
        errors.append(f"mode must be one of {sorted(MODES)}")
    if status not in STATUSES:
        errors.append(f"status must be one of {sorted(STATUSES)}")

    institution = record.get("institution")
    if not isinstance(institution, dict) or not nonempty(institution.get("name")):
        errors.append("institution.name is required")

    sources = record.get("sources")
    if not isinstance(sources, list) or not sources:
        errors.append("sources must be a non-empty array")
    else:
        for index, source in enumerate(sources):
            validate_source(source, index, record, errors)

    unresolved = record.get("unresolved", [])
    validate_string_list(unresolved, "unresolved", errors)
    if status in {"verified", "verified_with_caveat"} and nonempty(unresolved):
        errors.append(f"status {status} requires unresolved to be empty")
    if status in {"partial", "unresolved"} and not nonempty(unresolved):
        errors.append(f"status {status} requires at least one unresolved item")

    if mode == "service_guide":
        if not nonempty(record.get("service_name")):
            errors.append("service_name is required for service_guide")
        channel = record.get("channel")
        if channel is not None and channel not in SERVICE_CHANNELS:
            errors.append(f"channel must be one of {sorted(SERVICE_CHANNELS)}")
        for field in ("audience", "materials", "steps"):
            validate_string_list(record.get(field), field, errors)
        if not nonempty(record.get("responsible_unit")) and status == "verified":
            errors.append("verified service_guide requires responsible_unit")
        if not nonempty(record.get("steps")) and status == "verified":
            errors.append("verified service_guide requires non-empty steps")
        if isinstance(sources, list) and sources and not any(
            isinstance(source, dict) and source.get("type") != "map_spatial" for source in sources
        ):
            errors.append("service_guide requires at least one non-map source")

    if mode == "place_resolution":
        if not nonempty(record.get("query_label")):
            errors.append("query_label is required for place_resolution")
        place_type = record.get("place_type")
        if not nonempty(place_type):
            errors.append("place_type is required for place_resolution")
        elif place_type not in PLACE_TYPES:
            errors.append(f"place_type must be one of {sorted(PLACE_TYPES)}")
        if status == "verified" and not nonempty(record.get("canonical_name")):
            errors.append("verified place_resolution requires canonical_name")
        if place_type in DYNAMIC_PLACE_TYPES:
            event_scope = record.get("event_scope")
            if not isinstance(event_scope, dict):
                errors.append(f"{place_type} requires event_scope")
            elif place_type == "exam_room":
                if not nonempty(event_scope.get("date")):
                    errors.append("exam_room requires event_scope.date")
                elif not valid_iso_date(event_scope.get("date")):
                    errors.append("exam_room event_scope.date must be a valid calendar date in YYYY-MM-DD")
                if not nonempty(event_scope.get("term_or_batch")):
                    errors.append("exam_room requires event_scope.term_or_batch")
            elif place_type in {"event", "registration", "club_event"}:
                if not nonempty(event_scope.get("name")):
                    errors.append(f"{place_type} requires event_scope.name")
                if not any(nonempty(event_scope.get(key)) for key in ("date", "term_or_batch", "session")):
                    errors.append(f"{place_type} requires date, term_or_batch, or session context")
                if nonempty(event_scope.get("date")) and not valid_iso_date(event_scope.get("date")):
                    errors.append(
                        f"{place_type} event_scope.date must be a valid calendar date in YYYY-MM-DD"
                    )

    if status in {"verified", "verified_with_caveat"} and isinstance(sources, list):
        supported = {
            field
            for source in sources
            if isinstance(source, dict) and isinstance(source.get("supports"), list)
            for field in source["supports"]
            if isinstance(field, str)
        }
        if mode == "service_guide":
            for field in ("responsible_unit", "steps"):
                if nonempty(record.get(field)) and field not in supported:
                    errors.append(f"status {status} requires source support for {field}")
        if mode == "place_resolution" and nonempty(record.get("canonical_name")):
            if "canonical_name" not in supported:
                errors.append(f"status {status} requires source support for canonical_name")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path, help="Path to a normalized JSON record")
    args = parser.parse_args()

    try:
        record = json.loads(args.record.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"ERROR: file not found: {args.record}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"ERROR: cannot read {args.record}: {exc}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print(f"ERROR: invalid JSON: {exc}", file=sys.stderr)
        return 2

    errors = validate_record(record)
    if errors:
        print("INVALID")
        for error in errors:
            print(f"- {error}")
        return 1

    print("VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
