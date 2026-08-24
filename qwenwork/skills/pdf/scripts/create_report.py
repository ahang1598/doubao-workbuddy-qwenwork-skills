#!/usr/bin/env python3
"""
create_report.py — Operations Audit Report Generator

Generates a Markdown or JSON audit report summarising PDF processing operations
performed in a session. Reads operation log entries from stdin (JSON lines)
or accepts direct arguments.

Usage:
    # Pipe JSON-line events from other scripts
    echo '{"op":"merge","inputs":["a.pdf","b.pdf"],"output":"merged.pdf","status":"ok"}' \
        | python scripts/create_report.py --format markdown --output report.md

    # Generate a report for a single file analysis
    python scripts/create_report.py --analyze document.pdf --output report.md

    # Combined: analyze + validate and report
    python scripts/create_report.py --analyze document.pdf --validate --output report.md
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def analyze_summary(pdf_path: Path) -> dict:
    """Run analyze_pdf inline and return the result dict."""
    # Import our own analyze_pdf module if in the same scripts/ dir
    scripts_dir = Path(__file__).parent
    sys.path.insert(0, str(scripts_dir))
    try:
        from analyze_pdf import scan_pdf_structure
        return scan_pdf_structure(pdf_path)
    except ImportError:
        return {"error": "analyze_pdf.py not found in scripts/"}


def validate_summary(pdf_path: Path) -> dict:
    scripts_dir = Path(__file__).parent
    sys.path.insert(0, str(scripts_dir))
    try:
        from validate_pdf import run_checks
        return run_checks(pdf_path, strict=False)
    except ImportError:
        return {"error": "validate_pdf.py not found in scripts/"}


def render_markdown(pdf_path: Path | None, analysis: dict | None,
                    validation: dict | None, events: list[dict]) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines: list[str] = [
        "# PDF Pro — Operations Report",
        "",
        f"Generated: {now}",
        "",
    ]

    if pdf_path:
        lines += [f"**Source file:** `{pdf_path.name}`", ""]

    if analysis:
        lines += [
            "## File Analysis",
            "",
            f"| Property | Value |",
            f"|---|---|",
            f"| Pages | {analysis.get('page_count', '?')} |",
            f"| PDF Type | {analysis.get('pdf_type', '?')} |",
            f"| Scanned Ratio | {analysis.get('scanned_ratio', 0):.0%} |",
            f"| Has Text | {analysis.get('has_text', '?')} |",
            f"| Has Images | {analysis.get('has_images', '?')} |",
            f"| Has Forms | {analysis.get('has_forms', '?')} |",
            f"| Language Hint | {analysis.get('language_hint', '?')} |",
            "",
        ]
        meta = analysis.get("metadata", {})
        if meta:
            lines.append("### Document Metadata")
            lines.append("")
            for k, v in meta.items():
                if v and v != "None":
                    lines.append(f"- **{k}:** {v}")
            lines.append("")

    if validation:
        grade = validation.get("grade", "?")
        lines += [
            "## Validation",
            "",
            f"**Grade: {grade}**",
            "",
        ]
        errors = validation.get("errors", [])
        warnings = validation.get("warnings", [])
        if errors:
            lines.append("### Errors")
            for e in errors:
                lines.append(f"- `{e['name']}`: {e['detail']}")
            lines.append("")
        if warnings:
            lines.append("### Warnings")
            for w in warnings:
                lines.append(f"- `{w['name']}`: {w['detail']}")
            lines.append("")
        checks = validation.get("checks", [])
        passed = sum(1 for c in checks if c["status"] == "ok")
        lines.append(f"Checks passed: **{passed}/{len(checks)}**")
        lines.append("")

    if events:
        lines += ["## Operation Log", ""]
        lines += ["| # | Operation | Status | Detail |", "|---|---|---|---|"]
        for idx, ev in enumerate(events, 1):
            op = ev.get("op", "?")
            status = ev.get("status", "?")
            detail = ev.get("output", ev.get("detail", ""))
            lines.append(f"| {idx} | {op} | {status} | {detail} |")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a PDF operations audit report.")
    parser.add_argument("--analyze", metavar="PDF", help="PDF file to analyze and include")
    parser.add_argument("--validate", action="store_true",
                        help="Also run validation on the analyzed file")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown",
                        help="Report format (default: markdown)")
    parser.add_argument("--output", "-o", help="Output file path (default: stdout)")
    args = parser.parse_args()

    # Read event log from stdin if piped
    events: list[dict] = []
    if not sys.stdin.isatty():
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                pass

    pdf_path = Path(args.analyze) if args.analyze else None
    analysis = analyze_summary(pdf_path) if pdf_path and pdf_path.exists() else None
    validation = None
    if args.validate and pdf_path and pdf_path.exists():
        validation = validate_summary(pdf_path)

    if args.format == "json":
        output = json.dumps({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": str(pdf_path) if pdf_path else None,
            "analysis": analysis,
            "validation": validation,
            "events": events,
        }, indent=2, ensure_ascii=False)
    else:
        output = render_markdown(pdf_path, analysis, validation, events)

    if args.output:
        out_path = Path(args.output)
        out_path.write_text(output, encoding="utf-8")
        print(f"Report saved → {out_path}")
    else:
        print(output)


if __name__ == "__main__":
    main()
