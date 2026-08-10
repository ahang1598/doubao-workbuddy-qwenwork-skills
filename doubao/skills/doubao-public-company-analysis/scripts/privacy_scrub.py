#!/usr/bin/env python3
"""Create a redacted copy of a facts ledger. Stdlib only."""

import argparse
import json
import re
from pathlib import Path


SENSITIVE_KEY = re.compile(
    r"(?i)(?:full_?name|id_?(?:number|card)|passport|bank_?account|"
    r"card_?number|phone|mobile|email|exact_?address|credential|secret)"
)
SENSITIVE_VALUE = [
    re.compile(r"\b\d{17}[\dXx]\b"),
    re.compile(r"\b1[3-9]\d{9}\b"),
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
]


def redact(value, key="", stats=None):
    stats = stats if stats is not None else {"redacted": 0}
    if SENSITIVE_KEY.search(key):
        stats["redacted"] += 1
        return "[REDACTED]"
    if isinstance(value, dict):
        return {item: redact(child, item, stats) for item, child in value.items()}
    if isinstance(value, list):
        return [redact(child, key, stats) for child in value]
    if isinstance(value, str):
        result = value
        for pattern in SENSITIVE_VALUE:
            result, count = pattern.subn("[REDACTED]", result)
            stats["redacted"] += count
        return result
    return value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("output")
    args = parser.parse_args()
    try:
        payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    except Exception as error:
        print(f"ERROR: {error}")
        return 2
    stats = {"redacted": 0}
    cleaned = redact(payload, stats=stats)
    Path(args.output).write_text(
        json.dumps(cleaned, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(stats, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
