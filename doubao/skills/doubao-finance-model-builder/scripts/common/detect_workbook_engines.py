#!/usr/bin/env python3
"""Report spreadsheet engines available in the current runtime."""

import argparse
import importlib.util
import json
import os
import shutil
from pathlib import Path
from typing import Optional


def resolve_soffice(explicit: Optional[str]) -> Optional[str]:
    candidates = [
        explicit,
        os.environ.get("SOFFICE_PATH"),
        shutil.which("soffice"),
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
        "/usr/lib/libreoffice/program/soffice",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(Path(candidate).resolve())
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--soffice")
    args = parser.parse_args()
    openpyxl_ok = importlib.util.find_spec("openpyxl") is not None
    soffice = resolve_soffice(args.soffice)
    result = {
        "portable_python": {
            "available": openpyxl_ok,
            "openpyxl": openpyxl_ok,
            "libreoffice": bool(soffice),
            "soffice": soffice,
        },
        "recommended_generation_engine": "openpyxl" if openpyxl_ok else None,
        "recommended_audit_engine": "portable_python_libreoffice" if openpyxl_ok and soffice else None,
        "formal_formula_workbook_possible": bool(openpyxl_ok and soffice),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if openpyxl_ok else 1)


if __name__ == "__main__":
    main()
