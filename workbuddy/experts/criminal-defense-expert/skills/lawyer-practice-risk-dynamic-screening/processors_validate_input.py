#!/usr/bin/env python3
"""Validate input data for lawyer practice risk screening.

Checks that required fields are present and valid before risk scanning.
"""
import json
import sys


def validate(data: dict) -> dict:
    """Validate input data. Returns validation result."""
    required = ["case_type", "role", "actions"]
    missing = [f for f in required if f not in data]
    if missing:
        return {"valid": False, "missing_fields": missing}
    return {"valid": True, "fields_checked": len(required)}


def main():
    if len(sys.argv) > 1:
        data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    else:
        data = json.load(sys.stdin)
    result = validate(data)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
