#!/usr/bin/env python3
"""Portable direct audit for formula workbooks."""

import argparse
import json
from pathlib import Path

from portable_workbook_audit import audit_contract


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("workbook")
    parser.add_argument("contract")
    parser.add_argument("output")
    parser.add_argument("--recalculate", choices=["auto", "required", "off"], default="auto")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--soffice", help="LibreOffice soffice executable; also accepts SOFFICE_PATH")
    args = parser.parse_args()

    contract = json.loads(Path(args.contract).read_text(encoding="utf-8"))
    contract["_contract_path"] = str(Path(args.contract).resolve())
    result = audit_contract(
        args.workbook,
        contract,
        recalculate=args.recalculate,
        timeout=args.timeout,
        soffice_path=args.soffice,
    )
    Path(args.output).write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
