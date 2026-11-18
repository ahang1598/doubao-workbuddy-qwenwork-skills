#!/usr/bin/env python3
"""Shared V3 finalizer: Markdown first, optional publishers."""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent


def run(script, *args):
    return subprocess.run(
        [sys.executable, str(HERE / script), *map(str, args)],
        capture_output=True,
        text=True,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("report")
    parser.add_argument("facts")
    parser.add_argument("--docx", action="store_true")
    parser.add_argument("--redacted-facts")
    parser.add_argument("--manifest")
    args = parser.parse_args()
    report = Path(args.report).resolve()
    facts = Path(args.facts).resolve()
    manifest_path = (
        Path(args.manifest).resolve()
        if args.manifest
        else report.with_name(report.stem + "-manifest.json")
    )
    capabilities_path = report.with_name(report.stem + "-capabilities.json")
    gates = []

    validation = run(
        "validate_facts.py",
        facts,
        "--capabilities-out",
        capabilities_path,
    )
    gates.append(
        {
            "name": "facts",
            "passed": validation.returncode == 0,
            "stdout": validation.stdout[-4000:],
            "stderr": validation.stderr[-4000:],
        }
    )
    lint = run("lint_report.py", report, facts)
    gates.append(
        {
            "name": "report",
            "passed": lint.returncode == 0,
            "stdout": lint.stdout[-4000:],
            "stderr": lint.stderr[-4000:],
        }
    )
    if not all(gate["passed"] for gate in gates):
        manifest_path.write_text(
            json.dumps({"status": "FAILED", "gates": gates}, ensure_ascii=False, indent=2)
            + "\n",
            encoding="utf-8",
        )
        print(f"FAILED: see {manifest_path}")
        return 1

    text = report.read_text(encoding="utf-8")
    display = re.sub(r"\{fact:[^}]+\}", "", text)
    display_path = report.with_name(report.stem + "-display.md")
    display_path.write_text(display, encoding="utf-8")
    products = {"markdown": str(display_path), "capabilities": str(capabilities_path)}
    warnings = []

    if args.redacted_facts:
        redaction = run("privacy_scrub.py", facts, args.redacted_facts)
        if redaction.returncode:
            warnings.append("facts redaction failed: " + redaction.stderr[-1000:])
        else:
            products["redacted_facts"] = str(Path(args.redacted_facts).resolve())

    if args.docx:
        docx_path = report.with_suffix(".docx")
        publisher = run("make_docx.py", report, docx_path)
        if publisher.returncode:
            warnings.append("DOCX publisher failed; Markdown remains valid")
        else:
            products["docx"] = str(docx_path)

    manifest = {
        "status": "PASSED",
        "gates": gates,
        "products": products,
        "warnings": warnings,
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"display={display_path}")
    print(f"manifest={manifest_path}")
    for warning in warnings:
        print("WARNING:", warning)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
