#!/usr/bin/env python3
"""
validate_pdf.py — PDF Structural Validator

Checks that a PDF file is valid, complete, and internally consistent.
Reports page count, content coverage, form status, and potential issues.
Outputs a grade (A/B/C/D) based on quality signals.

Usage:
    python scripts/validate_pdf.py output.pdf
    python scripts/validate_pdf.py output.pdf --json
    python scripts/validate_pdf.py output.pdf --strict
"""

import argparse
import importlib.util
import json
import sys
from pathlib import Path


SCRIPT_DIRECTORY = Path(__file__).resolve().parent
if str(SCRIPT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIRECTORY))
from _cloud_runtime import (
    CloudRuntimeError,
    extract_document_tool_metadata,
    resolve_qwenwork_cli,
    run_document_tool,
)
from _execution_route import BackendFailure
from _semantic_route import execute_semantic_script


def _validation_failure_message(report: dict) -> str:
    """Return a bounded, actionable validation failure without local paths."""

    grade = str(report.get("grade", "D"))[:8]
    summaries = []
    for issue in report.get("errors", [])[:3]:
        if not isinstance(issue, dict):
            continue
        name = " ".join(str(issue.get("name", "unknown")).split())[:64]
        detail = " ".join(str(issue.get("detail", "")).split())[:240]
        summaries.append(f"{name}: {detail}" if detail else name)
    suffix = "; ".join(summaries) or "validation reported an unreadable or invalid PDF"
    return f"PDF_VALIDATION_FAILED: grade {grade}; {suffix}"


def run_checks(pdf_path: Path, strict: bool) -> dict:
    report = {
        "file": str(pdf_path),
        "size_kb": round(pdf_path.stat().st_size / 1024, 1),
        "checks": [],
        "warnings": [],
        "errors": [],
        "grade": "A",
    }

    def ok(name: str, detail: str = "") -> None:
        report["checks"].append({"name": name, "status": "ok", "detail": detail})

    def warn(name: str, detail: str = "") -> None:
        report["warnings"].append({"name": name, "detail": detail})

    def err(name: str, detail: str = "") -> None:
        report["errors"].append({"name": name, "detail": detail})

    # --- Check 1: can the file be opened? ---------------------------------
    try:
        import pypdf
        reader = pypdf.PdfReader(str(pdf_path))
        ok("file_readable", f"{len(reader.pages)} pages")
    except Exception as exc:
        err("file_readable", str(exc))
        report["grade"] = "D"
        return report

    page_count = len(reader.pages)
    report["page_count"] = page_count

    # --- Check 2: page count > 0 ------------------------------------------
    if page_count == 0:
        err("page_count", "PDF has zero pages")
    else:
        ok("page_count", str(page_count))

    # --- Check 3: all pages have dimensions --------------------------------
    malformed_pages = []
    for idx, page in enumerate(reader.pages):
        try:
            _ = page.mediabox
        except Exception:
            malformed_pages.append(idx + 1)
    if malformed_pages:
        warn("page_dimensions", f"Pages with missing mediabox: {malformed_pages}")
    else:
        ok("page_dimensions")

    # --- Check 4: content coverage (pdfplumber) ----------------------------
    try:
        import pdfplumber
        blank_pages = []
        with pdfplumber.open(str(pdf_path)) as doc:
            for idx, page in enumerate(doc.pages):
                text = page.extract_text() or ""
                images = page.images or []
                if not text.strip() and not images:
                    blank_pages.append(idx + 1)
        if blank_pages:
            if len(blank_pages) == page_count:
                warn("content_coverage", "All pages appear blank (may be scanned images)")
            else:
                warn("content_coverage", f"Blank pages: {blank_pages[:10]}")
        else:
            ok("content_coverage")
    except Exception as exc:
        warn("content_coverage", f"pdfplumber check failed: {exc}")

    # --- Check 5: no encryption blocking read ------------------------------
    if reader.is_encrypted:
        warn("encryption", "PDF is encrypted — content may not be accessible")
    else:
        ok("encryption", "not encrypted")

    # --- Check 6: metadata present (soft) ----------------------------------
    meta = reader.metadata or {}
    if strict and not meta.get("/Title") and not meta.get("/Author"):
        warn("metadata", "No title or author in metadata")
    else:
        ok("metadata", f"{len(meta)} metadata field(s)")

    # --- Check 7: file not truncated (heuristic) ----------------------------
    try:
        last_page = reader.pages[-1]
        _ = last_page.extract_text()
        ok("file_integrity")
    except Exception as exc:
        err("file_integrity", f"Last page unreadable: {exc}")

    # --- Grade assignment ---------------------------------------------------
    error_count = len(report["errors"])
    warn_count = len(report["warnings"])
    if error_count >= 2:
        report["grade"] = "D"
    elif error_count == 1:
        report["grade"] = "C"
    elif warn_count >= 3:
        report["grade"] = "B"
    elif warn_count >= 1:
        report["grade"] = "B"
    else:
        report["grade"] = "A"

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a PDF file for structural integrity.")
    parser.add_argument("pdf_file", help="PDF file to validate")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    parser.add_argument("--strict", action="store_true",
                        help="Enable additional strict checks (e.g. metadata completeness)")
    args = parser.parse_args()

    pdf_path = Path(args.pdf_file)
    if not pdf_path.exists():
        print(json.dumps({"error": f"File not found: {pdf_path}"}))
        sys.exit(1)

    def local_ready() -> bool:
        return all(
            importlib.util.find_spec(module) is not None
            for module in ("pypdf", "pdfplumber")
        )

    def cloud_ready() -> bool:
        try:
            return resolve_qwenwork_cli(required=False) is not None
        except RuntimeError:
            return False

    def print_report(report: dict) -> None:
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
            return
        grade = report.get("grade", "D")
        print(f"Validation: {grade}")
        print(f"File: {pdf_path.name}")
        print(f"Pages: {report.get('page_count', '?')}")
        for error in report.get("errors", []):
            print(f"  ERROR {error.get('name', 'unknown')}: {error.get('detail', '')}")
        for warning in report.get("warnings", []):
            print(f"  WARNING {warning.get('name', 'unknown')}: {warning.get('detail', '')}")

    def run_cloud() -> dict:
        flags = (("strict", None),) if args.strict else ()
        try:
            result = run_document_tool(
                ("document", "pdf", "validate"),
                pdf_path,
                flags=flags,
            )
        except CloudRuntimeError as exc:
            raise BackendFailure(exc.code, retryable=exc.retryable) from exc
        except RuntimeError as exc:
            raise BackendFailure("CLOUD_OPERATION_FAILED", retryable=True) from exc
        try:
            metadata = extract_document_tool_metadata(result)
        except RuntimeError as exc:
            raise BackendFailure("CLOUD_PDF_VALIDATION_INVALID", retryable=True) from exc
        report = metadata.get("report")
        if not isinstance(report, dict):
            raise BackendFailure("CLOUD_PDF_VALIDATION_INVALID", retryable=True)
        print_report(report)
        if report.get("grade") in {"C", "D"}:
            raise BackendFailure(
                "PDF_VALIDATION_FAILED",
                retryable=False,
                message=_validation_failure_message(report),
            )
        return report

    try:
        handled = execute_semantic_script(
            argv=[str(Path(__file__).resolve()), *sys.argv[1:]],
            local_ready=local_ready,
            cloud_ready=cloud_ready,
            run_cloud=run_cloud,
            local_result=lambda: {"grade": "A"},
            validate=lambda report: isinstance(report, dict) and report.get("grade") in {"A", "B"},
        )
        if handled:
            return
    except BackendFailure as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(2 if exc.code == "PDF_VALIDATION_FAILED" else 1)

    report = run_checks(pdf_path, strict=args.strict)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        grade = report["grade"]
        grade_icon = {"A": "PASS", "B": "PASS (warnings)", "C": "DEGRADED", "D": "FAIL"}
        print(f"Validation: {grade}  [{grade_icon.get(grade, grade)}]")
        print(f"File: {pdf_path.name}  ({report['size_kb']} KB)")
        print(f"Pages: {report.get('page_count', '?')}")
        if report["errors"]:
            print(f"\nErrors ({len(report['errors'])}):")
            for e in report["errors"]:
                print(f"  ✗ {e['name']}: {e['detail']}")
        if report["warnings"]:
            print(f"\nWarnings ({len(report['warnings'])}):")
            for w in report["warnings"]:
                print(f"  ⚠ {w['name']}: {w['detail']}")
        if report["checks"]:
            passed = sum(1 for c in report["checks"] if c["status"] == "ok")
            print(f"\nChecks passed: {passed}/{len(report['checks'])}")

    # Exit non-zero for C/D grades
    if report["grade"] in ("C", "D"):
        sys.exit(2)


if __name__ == "__main__":
    main()
