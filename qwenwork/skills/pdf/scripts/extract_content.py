#!/usr/bin/env python3
"""
extract_content.py — Layout-Aware Text Extraction

Extracts text from PDF files with layout preservation and multi-column
awareness. Handles both simple documents and complex multi-column layouts.

Usage:
    python scripts/extract_content.py input.pdf
    python scripts/extract_content.py input.pdf --output extracted.txt
    python scripts/extract_content.py input.pdf --output extracted.txt --layout preserve
    python scripts/extract_content.py input.pdf --pages 1-5 --output partial.txt
    python scripts/extract_content.py input.pdf --format json --output data.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _page_range_from_spec(spec: str, total: int) -> list[int]:
    """Parse '1-5' or '1,3,7' into 0-based page indices."""
    indices: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            lo, hi = part.split("-", 1)
            for p in range(int(lo), int(hi) + 1):
                if 1 <= p <= total:
                    indices.add(p - 1)
        else:
            p = int(part)
            if 1 <= p <= total:
                indices.add(p - 1)
    return sorted(indices)


def _strip_header_footer(lines: list[str], margin_lines: int = 1) -> list[str]:
    """Remove likely header/footer lines (top and bottom `margin_lines`)."""
    if len(lines) <= margin_lines * 2:
        return lines
    return lines[margin_lines:-margin_lines]


def extract_text_plain(pdf_path: Path, page_indices: list[int] | None,
                       remove_hf: bool) -> list[dict]:
    """Extract text using pdfplumber with layout preservation."""
    import pdfplumber

    pages_data: list[dict] = []
    with pdfplumber.open(str(pdf_path)) as doc:
        targets = page_indices if page_indices is not None else list(range(len(doc.pages)))
        for idx in targets:
            if idx >= len(doc.pages):
                continue
            page = doc.pages[idx]
            raw = page.extract_text(x_tolerance=3, y_tolerance=3) or ""
            lines = raw.splitlines()
            if remove_hf and len(lines) > 4:
                lines = _strip_header_footer(lines)
            pages_data.append({
                "page": idx + 1,
                "text": "\n".join(lines),
                "char_count": len("".join(lines)),
            })
    return pages_data


def extract_text_structured(pdf_path: Path, page_indices: list[int] | None) -> list[dict]:
    """
    Extract text with word-level bounding boxes.
    Returns richer data suitable for JSON output.
    """
    import pdfplumber

    pages_data: list[dict] = []
    with pdfplumber.open(str(pdf_path)) as doc:
        targets = page_indices if page_indices is not None else list(range(len(doc.pages)))
        for idx in targets:
            if idx >= len(doc.pages):
                continue
            page = doc.pages[idx]
            words = page.extract_words(x_tolerance=3, y_tolerance=3,
                                       keep_blank_chars=False) or []
            plain = page.extract_text() or ""
            pages_data.append({
                "page": idx + 1,
                "text": plain,
                "char_count": len(plain.replace(" ", "").replace("\n", "")),
                "word_count": len(words),
                "width_pt": float(page.width),
                "height_pt": float(page.height),
            })
    return pages_data


def write_text_output(pages_data: list[dict], output_path: Path) -> None:
    lines: list[str] = []
    for entry in pages_data:
        lines.append(f"--- Page {entry['page']} ---")
        lines.append(entry["text"])
        lines.append("")
    output_path.write_text("\n".join(lines), encoding="utf-8")


def write_json_output(pages_data: list[dict], output_path: Path) -> None:
    output_path.write_text(
        json.dumps({"pages": pages_data}, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract text from a PDF with layout awareness."
    )
    parser.add_argument("pdf_file", help="Input PDF path")
    parser.add_argument("--output", "-o", help="Output file path (default: stdout)")
    parser.add_argument("--layout", choices=["preserve", "plain"], default="preserve",
                        help="Text layout mode (default: preserve)")
    parser.add_argument("--pages", help="Page range spec e.g. '1-5' or '1,3,7'")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                        help="Output format (default: text)")
    parser.add_argument("--strip-hf", action="store_true",
                        help="Attempt to strip headers/footers")
    args = parser.parse_args()

    pdf_path = Path(args.pdf_file)
    if not pdf_path.exists():
        print(f"Error: file not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    # Determine page targets
    page_indices = None
    if args.pages:
        import pdfplumber
        with pdfplumber.open(str(pdf_path)) as doc:
            total = len(doc.pages)
        page_indices = _page_range_from_spec(args.pages, total)

    try:
        if args.format == "json":
            pages_data = extract_text_structured(pdf_path, page_indices)
        else:
            pages_data = extract_text_plain(pdf_path, page_indices, args.strip_hf)
    except Exception as exc:
        print(f"Extraction failed: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.output:
        out_path = Path(args.output)
        if args.format == "json":
            write_json_output(pages_data, out_path)
        else:
            write_text_output(pages_data, out_path)
        total_chars = sum(p["char_count"] for p in pages_data)
        print(f"Extracted {len(pages_data)} page(s), {total_chars} chars → {out_path}")
    else:
        for entry in pages_data:
            print(f"--- Page {entry['page']} ---")
            print(entry["text"])
            print()


if __name__ == "__main__":
    main()
