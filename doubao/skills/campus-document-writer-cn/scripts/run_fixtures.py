#!/usr/bin/env python3
"""Run all strict fixtures without echoing candidate text or sensitive values."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from validate_output import FixtureError, load_fixture, validate


def main() -> int:
    skill_root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description="Run campus-document-writer-cn offline fixtures.")
    parser.add_argument("--fixtures-dir", type=Path, default=skill_root / "fixtures")
    parser.add_argument("--report", type=Path, help="optional JSON summary path")
    args = parser.parse_args()
    paths = sorted(args.fixtures_dir.rglob("*.json"))
    if not paths:
        print("ERROR NO_FIXTURES", file=sys.stderr)
        return 2
    results = []
    failed = False
    for path in paths:
        try:
            fixture = load_fixture(path)
        except FixtureError as exc:
            print(f"ERROR FIXTURE_INVALID file={path.name} code={exc}", file=sys.stderr)
            return 2
        issues = validate(fixture, fixture["candidate_output"])
        actual_valid = not issues
        expected_codes = sorted(fixture.get("expected_issue_codes", []))
        codes_match = "expected_issue_codes" not in fixture or issues == expected_codes
        assertion_pass = actual_valid == fixture["expected_valid"] and codes_match
        failed = failed or not assertion_pass
        row = {"id": fixture["id"], "category": fixture["category"], "expected_valid": fixture["expected_valid"], "actual_valid": actual_valid, "issue_codes": issues, "assertion": "PASS" if assertion_pass else "FAIL"}
        results.append(row)
        print(f"{row['id']} {row['assertion']} actual={'VALID' if actual_valid else 'INVALID'} issues={','.join(issues) if issues else 'NONE'}")
    summary = {"fixture_count": len(results), "passed": sum(r["assertion"] == "PASS" for r in results), "failed": sum(r["assertion"] == "FAIL" for r in results), "results": results}
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"SUMMARY total={summary['fixture_count']} passed={summary['passed']} failed={summary['failed']}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
