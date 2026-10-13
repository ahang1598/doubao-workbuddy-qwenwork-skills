#!/usr/bin/env python3
"""Exercise fixture structure and output-validation edge cases offline."""

from __future__ import annotations

import argparse
import copy
import json
import tempfile
from pathlib import Path
from typing import Any, Callable

from validate_output import FixtureError, load_fixture, validate


BASE: dict[str, Any] = {
    "id": "selftest.valid",
    "category": "regression",
    "expected_route": "trigger",
    "candidate_output": "安全候选文本",
    "assertions": {
        "required_substrings": ["安全"],
        "forbidden_substrings": ["禁止"],
        "forbidden_regexes": ["不得出现$"],
        "max_output_chars": 100,
        "allow_empty_output": False,
    },
    "privacy": {"scan_standard_patterns": False, "forbidden_literals": []},
    "expected_valid": True,
    "expected_issue_codes": [],
}


def _load(data: dict[str, Any]) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="campus-contract-selftest-") as directory:
        path = Path(directory) / "fixture.json"
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return load_fixture(path)


def _expect_error(mutator: Callable[[dict[str, Any]], None], code: str) -> bool:
    data = copy.deepcopy(BASE)
    mutator(data)
    try:
        _load(data)
    except FixtureError as exc:
        return str(exc) == code
    return False


def main() -> int:
    argparse.ArgumentParser(description="Run deterministic fixture-contract self-tests.").parse_args()
    cases: list[tuple[str, bool]] = [
        ("valid-baseline", _load(copy.deepcopy(BASE))["id"] == "selftest.valid"),
        ("missing-required", _expect_error(lambda d: d.pop("id"), "TOP_FIELDS_INVALID")),
        ("unknown-top-field", _expect_error(lambda d: d.update({"extra": True}), "TOP_FIELDS_INVALID")),
        ("invalid-id", _expect_error(lambda d: d.update({"id": ""}), "ID_INVALID")),
        ("invalid-category-enum", _expect_error(lambda d: d.update({"category": "other"}), "CATEGORY_INVALID")),
        ("invalid-route-enum", _expect_error(lambda d: d.update({"expected_route": "other"}), "ROUTE_INVALID")),
        ("invalid-description", _expect_error(lambda d: d.update({"description": []}), "DESCRIPTION_INVALID")),
        ("invalid-assertion-nested-field", _expect_error(lambda d: d["assertions"].update({"extra": []}), "ASSERTION_FIELDS_INVALID")),
        ("invalid-regex", _expect_error(lambda d: d["assertions"].update({"forbidden_regexes": ["["]}), "FORBIDDEN_REGEX_INVALID")),
        ("invalid-max-bool", _expect_error(lambda d: d["assertions"].update({"max_output_chars": True}), "MAX_OUTPUT_CHARS_INVALID")),
        ("invalid-privacy-nested-field", _expect_error(lambda d: d["privacy"].update({"extra": []}), "PRIVACY_FIELDS_INVALID")),
    ]
    loaded = _load(copy.deepcopy(BASE))
    cases.extend(
        [
            ("empty-output", validate(loaded, "") == ["OUTPUT_EMPTY", "REQUIRED_TEXT_MISSING"]),
            ("forbidden-output", validate(loaded, "安全但禁止") == ["FORBIDDEN_TEXT_PRESENT"]),
        ]
    )
    failed = [case_id for case_id, passed in cases if not passed]
    for case_id, passed in cases:
        print(f"{case_id} {'PASS' if passed else 'FAIL'}")
    print(f"SUMMARY total={len(cases)} passed={len(cases) - len(failed)} failed={len(failed)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
