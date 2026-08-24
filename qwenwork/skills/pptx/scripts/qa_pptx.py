#!/usr/bin/env python3
"""Run the deterministic PPTX QA gates through one stable command."""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import tempfile
import zipfile
from dataclasses import asdict
from pathlib import Path

import sys

OXML_DIR = Path(__file__).resolve().parent / "oxml"
if str(OXML_DIR) not in sys.path:
    sys.path.insert(0, str(OXML_DIR))

from _pptx_package import validate_package
from _cloud_runtime import cloud_runtime_ready
from _execution_route import BackendFailure, execute_with_fallback, execution_mode
from _result_validation import validation_result_valid
from oxml.checks import DeckAuditor
from oxml.kit import unzip_guarded
from validate_pptx import _cloud as cloud_preflight
from view_issues import run_all_checks


RESULT_SCHEMA = "qwenwork.pptx.qa/v1"


def _package_audit(source: Path, original: Path | None) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="pptx-qa-") as temporary:
        unpacked = Path(temporary)
        with zipfile.ZipFile(source) as archive:
            unzip_guarded(archive, unpacked)
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            valid = DeckAuditor(unpacked, original, verbose=False).run_audit()
    return valid, output.getvalue().strip()


def run_qa(source: Path, *, original: Path | None, require_notes: bool) -> dict:
    source = source.resolve()
    original = original.resolve() if original is not None else None
    if not source.is_file() or source.suffix.lower() != ".pptx":
        raise ValueError("input must be an existing .pptx file")
    if original is not None and (
        not original.is_file() or original.suffix.lower() != ".pptx"
    ):
        raise ValueError("--original must be an existing .pptx file")

    preflight, _ = execute_with_fallback(
        mode=execution_mode(),
        local_ready=lambda: True,
        cloud_ready=cloud_runtime_ready,
        run_local=lambda: validate_package(source),
        run_cloud=lambda: cloud_preflight(source),
        validate=validation_result_valid,
    )
    findings = run_all_checks(
        source,
        template=str(original) if original is not None else None,
        require_notes=require_notes,
    )
    audit_valid, audit_detail = _package_audit(source, original)
    blocking = [asdict(finding) for finding in findings if finding.severity == "error"]
    warnings = [asdict(finding) for finding in findings if finding.severity == "warning"]
    valid = preflight.get("valid") is True and audit_valid and not any(
        finding.severity == "error" for finding in findings
    )
    return {
        "schema_version": RESULT_SCHEMA,
        "valid": valid,
        "preflight": {
            "valid": preflight.get("valid") is True,
            "issue_summary": preflight.get("issue_summary", {}),
        },
        "layout": {
            "finding_count": len(findings),
            "error_count": sum(finding.severity == "error" for finding in findings),
            "warning_count": sum(finding.severity == "warning" for finding in findings),
            "blocking_findings": blocking,
            "warnings": warnings,
        },
        "package": {
            "valid": audit_valid,
            "detail": audit_detail or None,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--original", type=Path)
    parser.add_argument("--require-notes", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    try:
        result = run_qa(
            args.input,
            original=args.original,
            require_notes=args.require_notes,
        )
    except (BackendFailure, OSError, ValueError, zipfile.BadZipFile) as exc:
        print(
            json.dumps(
                {
                    "schema_version": RESULT_SCHEMA,
                    "valid": False,
                    "error": {"message": str(exc)},
                },
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )
        return 2
    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2 if args.pretty else None,
            separators=None if args.pretty else (",", ":"),
        )
    )
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
