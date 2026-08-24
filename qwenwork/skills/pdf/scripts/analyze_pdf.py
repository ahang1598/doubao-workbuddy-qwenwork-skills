#!/usr/bin/env python3
"""
analyze_pdf.py — PDF Analysis Engine

Inspects a PDF file and reports its type, structure, language signals,
and per-page classification. Output is printed as JSON to stdout.

Usage:
    python scripts/analyze_pdf.py <input.pdf> [--json] [--verbose]

Output fields:
    page_count      total pages
    pdf_type        "text" | "scanned" | "mixed"
    scanned_ratio   fraction of pages that appear scanned (0.0–1.0)
    has_text        true if any extractable text was found
    has_images      true if any embedded images were found
    has_forms       true if the PDF has AcroForm fields
    language_hint   detected script/language (e.g. "latin", "cjk", "arabic")
    pages           list of per-page summaries
    metadata        PDF document metadata dict
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _detect_language_hint(sample_text: str) -> str:
    """Classify the dominant script from a sample of text."""
    if not sample_text:
        return "unknown"
    codepoints = [ord(ch) for ch in sample_text if not ch.isspace()]
    if not codepoints:
        return "unknown"
    cjk = sum(1 for cp in codepoints if 0x4E00 <= cp <= 0x9FFF or 0x3040 <= cp <= 0x30FF)
    arabic = sum(1 for cp in codepoints if 0x0600 <= cp <= 0x06FF)
    latin = sum(1 for cp in codepoints if cp < 0x0250)
    total = len(codepoints)
    if cjk / total > 0.25:
        return "cjk"
    if arabic / total > 0.25:
        return "arabic"
    if latin / total > 0.50:
        return "latin"
    return "mixed"


def _page_is_scanned(page_text: str, image_count: int) -> bool:
    """
    Heuristic: a page is considered scanned if it has embedded images
    but very little or no extractable text.
    """
    text_chars = len(page_text.strip()) if page_text else 0
    return image_count > 0 and text_chars < 30


def scan_pdf_structure(pdf_path: Path) -> dict:
    """
    Open the PDF and collect structural metadata and per-page analysis.
    Returns a dict ready for JSON serialisation.
    """
    try:
        import pypdf
        import pdfplumber
    except ImportError as exc:
        return {"error": f"Missing dependency: {exc}. Run: pip install pypdf pdfplumber"}

    result = {
        "source": str(pdf_path),
        "page_count": 0,
        "pdf_type": "text",
        "scanned_ratio": 0.0,
        "has_text": False,
        "has_images": False,
        "has_forms": False,
        "language_hint": "unknown",
        "pages": [],
        "metadata": {},
    }

    # --- pypdf pass: metadata, forms, image detection ----------------------
    try:
        reader = pypdf.PdfReader(str(pdf_path))
        result["page_count"] = len(reader.pages)

        meta = reader.metadata or {}
        result["metadata"] = {k.lstrip("/"): str(v) for k, v in meta.items()}

        # AcroForm detection
        acroform = reader.trailer.get("/Root", {}).get("/AcroForm")
        result["has_forms"] = acroform is not None

        # Per-page image count via pypdf
        pypdf_pages_images = []
        for page in reader.pages:
            try:
                imgs = page.images
                pypdf_pages_images.append(len(imgs))
            except Exception:
                pypdf_pages_images.append(0)

    except pypdf.errors.PdfReadError as exc:
        result["error"] = f"Cannot read PDF: {exc}"
        return result

    # --- pdfplumber pass: text extraction and per-page analysis ------------
    all_text_parts: list[str] = []
    scanned_page_count = 0

    try:
        with pdfplumber.open(str(pdf_path)) as plumber_doc:
            for idx, page in enumerate(plumber_doc.pages):
                page_text = page.extract_text() or ""
                img_count = pypdf_pages_images[idx] if idx < len(pypdf_pages_images) else 0
                is_scanned = _page_is_scanned(page_text, img_count)
                if is_scanned:
                    scanned_page_count += 1
                if page_text.strip():
                    all_text_parts.append(page_text)

                result["pages"].append({
                    "page": idx + 1,
                    "text_chars": len(page_text.strip()),
                    "image_count": img_count,
                    "likely_scanned": is_scanned,
                    "width_pt": float(page.width),
                    "height_pt": float(page.height),
                })
    except Exception as exc:
        result["warning"] = f"pdfplumber pass failed: {exc}"

    # --- Aggregate --------------------------------------------------------
    total_pages = result["page_count"]
    result["scanned_ratio"] = round(scanned_page_count / total_pages, 3) if total_pages else 0.0
    result["has_text"] = bool(all_text_parts)
    result["has_images"] = any(p.get("image_count", 0) > 0 for p in result["pages"])

    if result["scanned_ratio"] >= 0.9:
        result["pdf_type"] = "scanned"
    elif result["scanned_ratio"] >= 0.1:
        result["pdf_type"] = "mixed"
    else:
        result["pdf_type"] = "text"

    sample = " ".join(all_text_parts)[:2000]
    result["language_hint"] = _detect_language_hint(sample)

    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze a PDF file and report its structural properties."
    )
    parser.add_argument("pdf_file", help="Path to the PDF file to analyze")
    parser.add_argument("--json", action="store_true", help="Output raw JSON (default is pretty JSON)")
    parser.add_argument("--verbose", action="store_true", help="Include per-page details in output")
    args = parser.parse_args()

    pdf_path = Path(args.pdf_file)
    if not pdf_path.exists():
        print(json.dumps({"error": f"File not found: {pdf_path}"}))
        sys.exit(1)

    report = scan_pdf_structure(pdf_path)

    if not args.verbose:
        report.pop("pages", None)

    indent = None if args.json else 2
    print(json.dumps(report, indent=indent, ensure_ascii=False))

    # Exit non-zero if analysis found an error
    if "error" in report:
        sys.exit(2)


if __name__ == "__main__":
    main()
