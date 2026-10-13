#!/usr/bin/env python3
"""Validate one candidate output against a strict offline fixture contract."""

from __future__ import annotations

import argparse
import ipaddress
import json
import re
import sys
from pathlib import Path
from typing import Any

TOP_KEYS = {"id", "category", "expected_route", "description", "candidate_output", "assertions", "privacy", "expected_valid", "expected_issue_codes"}
REQUIRED_TOP = {"id", "category", "expected_route", "candidate_output", "assertions", "expected_valid"}
ASSERTION_KEYS = {"required_substrings", "forbidden_substrings", "forbidden_regexes", "max_output_chars", "allow_empty_output"}
PRIVACY_KEYS = {"scan_standard_patterns", "forbidden_literals"}
CATEGORIES = {"positive", "negative", "boundary", "regression"}
ROUTES = {"trigger", "not_trigger", "boundary"}
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
PATTERNS = {
    "PII_EMAIL": re.compile(r"(?i)(?<![\w.+-])[\w.+-]+@[A-Z0-9.-]+\.[A-Z]{2,}(?![\w.-])"),
    "PII_PHONE": re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),
    "SECRET_TOKEN": re.compile(r"(?i)(?:sk|token|bearer)[-_ :]+[A-Za-z0-9._-]{12,}"),
    "PATH_HOME": re.compile(r"(?:/Users/[^/\s]+|/home/[^/\s]+)(?:/[^\s]*)?"),
    "PATH_PRIVATE": re.compile(r"/(?:private|var|opt|srv)/(?:[^\s]+)"),
    "INTERNAL_DOMAIN": re.compile(r"(?i)\b(?:[a-z0-9-]+\.)+(?:internal|intranet|corp|lan|local)\b"),
}


class FixtureError(ValueError):
    pass


def _strings(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise FixtureError(f"{field}_INVALID")
    return value


def load_fixture(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise FixtureError("FIXTURE_READ_INVALID") from exc
    if not isinstance(data, dict):
        raise FixtureError("ROOT_NOT_OBJECT")
    if set(data) - TOP_KEYS or REQUIRED_TOP - set(data):
        raise FixtureError("TOP_FIELDS_INVALID")
    if not isinstance(data["id"], str) or not ID_RE.fullmatch(data["id"]):
        raise FixtureError("ID_INVALID")
    if data["category"] not in CATEGORIES:
        raise FixtureError("CATEGORY_INVALID")
    if data["expected_route"] not in ROUTES:
        raise FixtureError("ROUTE_INVALID")
    if not isinstance(data["candidate_output"], str) or not isinstance(data["expected_valid"], bool):
        raise FixtureError("OUTPUT_OR_EXPECTED_INVALID")
    if "description" in data and (not isinstance(data["description"], str) or not data["description"].strip()):
        raise FixtureError("DESCRIPTION_INVALID")
    assertions = data["assertions"]
    if not isinstance(assertions, dict) or set(assertions) != ASSERTION_KEYS:
        raise FixtureError("ASSERTION_FIELDS_INVALID")
    for field in ("required_substrings", "forbidden_substrings", "forbidden_regexes"):
        _strings(assertions[field], field)
    if not isinstance(assertions["max_output_chars"], int) or isinstance(assertions["max_output_chars"], bool) or assertions["max_output_chars"] <= 0:
        raise FixtureError("MAX_OUTPUT_CHARS_INVALID")
    if not isinstance(assertions["allow_empty_output"], bool):
        raise FixtureError("ALLOW_EMPTY_INVALID")
    for pattern in assertions["forbidden_regexes"]:
        try:
            re.compile(pattern)
        except re.error as exc:
            raise FixtureError("FORBIDDEN_REGEX_INVALID") from exc
    privacy = data.get("privacy", {"scan_standard_patterns": False, "forbidden_literals": []})
    if not isinstance(privacy, dict) or set(privacy) != PRIVACY_KEYS:
        raise FixtureError("PRIVACY_FIELDS_INVALID")
    if not isinstance(privacy["scan_standard_patterns"], bool):
        raise FixtureError("PRIVACY_SCAN_INVALID")
    _strings(privacy["forbidden_literals"], "privacy.forbidden_literals")
    data["privacy"] = privacy
    if "expected_issue_codes" in data:
        _strings(data["expected_issue_codes"], "expected_issue_codes")
    return data


def _private_ipv4(text: str) -> bool:
    for token in re.findall(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])", text):
        try:
            address = ipaddress.ip_address(token)
        except ValueError:
            continue
        if address.version == 4 and address.is_private:
            return True
    return False


def validate(data: dict[str, Any], output: str) -> list[str]:
    assertions = data["assertions"]
    issues: set[str] = set()
    if not output.strip() and not assertions["allow_empty_output"]:
        issues.add("OUTPUT_EMPTY")
    if len(output) > assertions["max_output_chars"]:
        issues.add("OUTPUT_TOO_LONG")
    if any(item not in output for item in assertions["required_substrings"]):
        issues.add("REQUIRED_TEXT_MISSING")
    if any(item in output for item in assertions["forbidden_substrings"]):
        issues.add("FORBIDDEN_TEXT_PRESENT")
    if any(re.search(pattern, output) for pattern in assertions["forbidden_regexes"]):
        issues.add("FORBIDDEN_PATTERN_PRESENT")
    privacy = data["privacy"]
    if any(item in output for item in privacy["forbidden_literals"]):
        issues.add("PRIVATE_LITERAL_PRESENT")
    if privacy["scan_standard_patterns"]:
        for code, pattern in PATTERNS.items():
            if pattern.search(output):
                issues.add(code)
        if _private_ipv4(output):
            issues.add("PRIVATE_IPV4")
    return sorted(issues)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a candidate output against one offline fixture.")
    parser.add_argument("--fixture", required=True, type=Path, help="UTF-8 JSON fixture")
    parser.add_argument("--output", type=Path, help="optional UTF-8 candidate text; overrides candidate_output")
    args = parser.parse_args()
    try:
        fixture = load_fixture(args.fixture)
        output = args.output.read_text(encoding="utf-8") if args.output else fixture["candidate_output"]
    except (FixtureError, OSError, UnicodeError) as exc:
        code = str(exc) if isinstance(exc, FixtureError) else "OUTPUT_READ_INVALID"
        print(f"ERROR {code}", file=sys.stderr)
        return 2
    issues = validate(fixture, output)
    state = "INVALID" if issues else "VALID"
    print(f"{fixture['id']} {state} issues={','.join(issues) if issues else 'NONE'}")
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
