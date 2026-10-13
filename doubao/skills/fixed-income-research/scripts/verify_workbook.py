#!/usr/bin/env python3
"""Read-only bounded passive-XLSX verification; unsupported features fail closed."""

import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile
from workbook_io import inspect


def verify(path, required_sheets=(), require_formulas=False):
    return inspect(path, required_sheets, require_formulas)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--required-sheet", action="append", default=[])
    parser.add_argument("--require-formulas", action="store_true")
    args = parser.parse_args()
    try:
        result = verify(args.workbook, args.required_sheet, args.require_formulas)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, OSError, KeyError, zipfile.BadZipFile, ET.ParseError) as exc:
        parser.exit(2, f"Workbook not verified: {exc}\n")
    if result["status"] == "failed":
        parser.exit(1)


if __name__ == "__main__":
    main()
