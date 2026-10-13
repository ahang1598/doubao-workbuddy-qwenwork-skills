#!/usr/bin/env python3
"""Normalize one platform card response into the work-data response contract."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from intake_runtime import normalize_response


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("response", type=Path)
    parser.add_argument("--answered-at", default=None)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    raw = json.loads(args.response.read_text(encoding="utf-8"))
    answered_at = args.answered_at or datetime.now(timezone.utc).isoformat()
    result = normalize_response(raw, answered_at=answered_at)
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
