#!/usr/bin/env python3
"""Validate per-source authorization, freshness, and evidence capability."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any, TextIO

from privacy_utils import sanitize


TOOL_STATUS = {
    "available_authorized",
    "available_authorization_pending",
    "unavailable",
    "not_used",
}
SOURCE_KINDS = {
    "official_current",
    "official_historical",
    "user_material",
    "search_summary",
    "secondary",
}
CAPABILITIES = {
    "deadline",
    "eligibility",
    "recognition",
    "process",
    "historical_reference",
    "discovery_only",
    "user_goal",
}
ACCESS_METHODS = {"public_web", "user_provided", "offline"}
AUTH_STATUS = {"authorized", "pending", "restricted", "not_applicable"}
VERIFY_STATUS = {"verified_current", "historical_reference", "user_material", "unverified"}
FRESHNESS = {"current", "historical", "unknown", "not_applicable"}


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="检查动态事实来源的授权、时效和证据能力。")
    result.add_argument("input", nargs="?", default="-", help="来源账本 JSON；默认从 stdin 读取。")
    result.add_argument("--strict", action="store_true", help="要求 final_ready 且无未解决项。")
    result.add_argument("--compact", action="store_true", help="输出单行 JSON。")
    return result


def load_json(input_name: str, stdin: TextIO) -> Any:
    if input_name == "-":
        return json.load(stdin)
    with Path(input_name).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def date_value(value: Any, field: str, errors: list[str], *, datetime_required: bool = False) -> dt.date | dt.datetime | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{field}: expected non-empty ISO date")
        return None
    try:
        if datetime_required:
            parsed = dt.datetime.fromisoformat(value)
            if parsed.tzinfo is None:
                raise ValueError("timezone required")
            return parsed
        return dt.date.fromisoformat(value)
    except ValueError:
        errors.append(f"{field}: invalid ISO {'datetime with timezone' if datetime_required else 'date'}")
        return None


def strings(value: Any, field: str, errors: list[str], *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        errors.append(f"{field}: expected an array of non-empty strings")
        return []
    if not allow_empty and not value:
        errors.append(f"{field}: must not be empty")
    return [item.strip() for item in value]


def validate(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        return {"ok": False, "errors": ["root must be an object"], "warnings": []}
    errors: list[str] = []
    warnings: list[str] = []
    runtime = data.get("runtime")
    if not isinstance(runtime, dict):
        errors.append("runtime: expected object")
        runtime = {}
    tool_status = runtime.get("network_tool_status")
    if tool_status not in TOOL_STATUS:
        errors.append("runtime.network_tool_status: invalid")
    evaluated_at = date_value(runtime.get("evaluated_at"), "runtime.evaluated_at", errors, datetime_required=True)

    final_ready = data.get("final_ready")
    if not isinstance(final_ready, bool):
        errors.append("final_ready: expected boolean")
        final_ready = False
    unresolved = strings(data.get("unresolved", []), "unresolved", errors, allow_empty=True)
    conflicts = strings(data.get("conflicts", []), "conflicts", errors, allow_empty=True)
    if final_ready and (unresolved or conflicts):
        errors.append("final_ready cannot coexist with unresolved or conflicts")

    sources = data.get("sources")
    if not isinstance(sources, list) or not sources:
        errors.append("sources: expected non-empty array")
        sources = []
    seen: set[str] = set()
    current_verified = 0
    unresolved_source = False
    for index, source in enumerate(sources):
        path = f"sources[{index}]"
        if not isinstance(source, dict):
            errors.append(f"{path}: expected object")
            continue
        source_id = source.get("source_id")
        if not isinstance(source_id, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,31}", source_id):
            errors.append(f"{path}.source_id: invalid")
        elif source_id in seen:
            errors.append(f"{path}.source_id: duplicate")
        else:
            seen.add(source_id)
        for field in ("publisher", "source", "applicable_scope"):
            if not isinstance(source.get(field), str) or not source[field].strip():
                errors.append(f"{path}.{field}: expected non-empty string")
        kind = source.get("source_kind")
        access = source.get("access_method")
        auth = source.get("authorization_status")
        verify = source.get("verification_status")
        freshness = source.get("freshness")
        if kind not in SOURCE_KINDS:
            errors.append(f"{path}.source_kind: invalid")
        if access not in ACCESS_METHODS:
            errors.append(f"{path}.access_method: invalid")
        if auth not in AUTH_STATUS:
            errors.append(f"{path}.authorization_status: invalid")
        if verify not in VERIFY_STATUS:
            errors.append(f"{path}.verification_status: invalid")
        if freshness not in FRESHNESS:
            errors.append(f"{path}.freshness: invalid")
        capabilities = strings(source.get("capabilities"), f"{path}.capabilities", errors)
        invalid_caps = sorted(set(capabilities) - CAPABILITIES)
        if invalid_caps:
            errors.append(f"{path}.capabilities: invalid values {invalid_caps}")

        published = date_value(source.get("published_at"), f"{path}.published_at", errors)
        updated = date_value(source.get("updated_at"), f"{path}.updated_at", errors)
        retrieved = date_value(source.get("retrieved_at"), f"{path}.retrieved_at", errors, datetime_required=True)
        valid_until = date_value(source.get("valid_until"), f"{path}.valid_until", errors)
        if published and updated and updated < published:
            errors.append(f"{path}: updated_at precedes published_at")
        evaluation_date = evaluated_at.date() if isinstance(evaluated_at, dt.datetime) else None
        for field, value in (("published_at", published), ("updated_at", updated)):
            if value and evaluation_date and value > evaluation_date:
                errors.append(f"{path}.{field}: date is in the future")
        if evaluated_at and retrieved and retrieved > evaluated_at:
            errors.append(f"{path}: retrieved_at is in the future")
        if valid_until and evaluation_date and valid_until < evaluation_date:
            if freshness != "historical":
                errors.append(f"{path}: expired source must be historical")
            if verify == "verified_current":
                errors.append(f"{path}: expired source cannot be verified_current")

        if access == "public_web":
            if auth == "authorized":
                if tool_status != "available_authorized":
                    errors.append(f"{path}: authorized web source requires available_authorized tool")
                if retrieved is None:
                    errors.append(f"{path}: authorized web source requires retrieved_at")
            elif verify == "verified_current":
                errors.append(f"{path}: pending/restricted web source cannot be verified_current")
        elif auth != "not_applicable":
            errors.append(f"{path}: non-web source authorization_status must be not_applicable")

        if kind == "search_summary":
            if set(capabilities) != {"discovery_only"} or verify != "unverified":
                errors.append(f"{path}: search_summary supports discovery_only and must remain unverified")
        if kind == "official_historical" and verify != "historical_reference":
            errors.append(f"{path}: official_historical must be historical_reference")
        if kind == "user_material":
            if access != "user_provided" or auth != "not_applicable" or verify != "user_material":
                errors.append(f"{path}: user_material access/authorization/verification mismatch")
        if verify == "verified_current":
            if kind != "official_current" or freshness != "current":
                errors.append(f"{path}: verified_current requires official_current and current freshness")
            else:
                current_verified += 1
            if not (published or updated):
                errors.append(f"{path}: verified_current requires published_at or updated_at")
            if valid_until is None:
                errors.append(f"{path}: verified_current requires valid_until")
            if "discovery_only" in capabilities:
                errors.append(f"{path}: verified_current cannot use discovery_only capability")
        if verify in {"unverified", "historical_reference"} or auth in {"pending", "restricted"}:
            unresolved_source = True

    if final_ready and unresolved_source:
        errors.append("final_ready cannot include unverified, historical, pending, or restricted sources")
    claim_verified = bool(final_ready and current_verified and not errors)
    if not final_ready:
        warnings.append("ledger is not final_ready")
    return {
        "ok": not errors,
        "final_ready": bool(final_ready),
        "claim_verified": claim_verified,
        "errors": errors,
        "warnings": warnings,
    }


def emit(payload: dict[str, Any], compact: bool, *, stderr: bool = False) -> None:
    print(
        json.dumps(sanitize(payload), ensure_ascii=False, indent=None if compact else 2),
        file=sys.stderr if stderr else sys.stdout,
    )


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        data = load_json(args.input, sys.stdin)
    except (OSError, json.JSONDecodeError) as exc:
        emit({"ok": False, "errors": [str(exc)], "warnings": []}, args.compact, stderr=True)
        return 2
    result = validate(data)
    emit(result, args.compact)
    if not result["ok"]:
        return 2
    if args.strict and not result["claim_verified"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
