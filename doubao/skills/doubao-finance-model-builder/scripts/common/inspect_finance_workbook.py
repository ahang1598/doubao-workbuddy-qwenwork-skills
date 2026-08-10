#!/usr/bin/env python3
"""Inspect a finance workbook without modifying it."""

import argparse
import json
from pathlib import Path

from portable_workbook_audit import inspect_workbook_structure


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("workbook")
    parser.add_argument("output")
    args = parser.parse_args()
    result = inspect_workbook_structure(args.workbook)
    Path(args.output).write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
