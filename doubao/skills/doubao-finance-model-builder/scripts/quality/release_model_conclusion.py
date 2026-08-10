#!/usr/bin/env python3
"""Regenerate a release decision from a consolidated quality report."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("run_quality_gates.py")
SPEC = importlib.util.spec_from_file_location("run_quality_gates", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("quality_report", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = json.loads(args.quality_report.read_text(encoding="utf-8"))
    status = str(report.get("overall_status", "INCOMPLETE")).upper()
    if status not in MODULE.STATUSES or status == "NOT_APPLICABLE":
        status = "INCOMPLETE"
    decision = MODULE.release_decision(status)
    args.output.write_text(json.dumps(decision, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(decision, ensure_ascii=False, indent=2))
    return 0 if decision["conclusion_allowed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
