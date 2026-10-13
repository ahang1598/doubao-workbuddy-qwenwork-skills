#!/usr/bin/env python3
"""Apply one normalized response to work data without mutating unrelated fields."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from intake_runtime import apply_response


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("work_data", type=Path)
    parser.add_argument("response", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.work_data.read_text(encoding="utf-8"))
    response = json.loads(args.response.read_text(encoding="utf-8"))
    result = apply_response(data, response)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
