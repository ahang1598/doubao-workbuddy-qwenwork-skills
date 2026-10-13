#!/usr/bin/env python3
"""Compile the deterministic intake card queue for a work-data file."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from intake_runtime import compile_required_cards


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("work_data", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    data = json.loads(args.work_data.read_text(encoding="utf-8"))
    intake = data.get("intake_session") or {}
    result = compile_required_cards(
        ((intake.get("coverage_assessment") or {}).get("topics") or {}),
        intake.get("collection_mode") or "fast",
        intake.get("card_responses") or [],
        audience=(data.get("audience_profile") or {}).get("audience_type"),
    )
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
