#!/usr/bin/env python3
"""
extract_form_structure.py — extract form layout from a non-fillable PDF.

Uses pdfplumber to find:
- Text labels with their exact PDF coordinates
- Horizontal lines (row boundaries)
- Small square rectangles (checkboxes)
- Row boundaries derived from horizontal lines

Output is a JSON file feeding fill_form_overlay.py via fields.json.

Coordinate system note: pdfplumber returns coordinates with y=0 at the
TOP of the page (y increases downward). fill_form_overlay.py reads
these directly when fields.json declares `pdf_width`/`pdf_height` and
flips Y internally for pypdf's bottom-left origin.

Usage:
    python scripts/extract_form_structure.py <input.pdf> <output.json>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def extract_form_structure(pdf_path: Path) -> dict:
    try:
        import pdfplumber
    except ImportError:
        print(
            "Error: pdfplumber required. Run: pip install pdfplumber",
            file=sys.stderr,
        )
        sys.exit(1)

    structure: dict = {
        "pages": [],
        "labels": [],
        "lines": [],
        "checkboxes": [],
        "row_boundaries": [],
    }

    with pdfplumber.open(str(pdf_path)) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            structure["pages"].append({
                "page_number": page_num,
                "width": float(page.width),
                "height": float(page.height),
            })

            for word in page.extract_words():
                structure["labels"].append({
                    "page": page_num,
                    "text": word["text"],
                    "x0": round(float(word["x0"]), 1),
                    "top": round(float(word["top"]), 1),
                    "x1": round(float(word["x1"]), 1),
                    "bottom": round(float(word["bottom"]), 1),
                })

            for line in page.lines:
                if abs(float(line["x1"]) - float(line["x0"])) > page.width * 0.5:
                    structure["lines"].append({
                        "page": page_num,
                        "y": round(float(line["top"]), 1),
                        "x0": round(float(line["x0"]), 1),
                        "x1": round(float(line["x1"]), 1),
                    })

            for rect in page.rects:
                width = float(rect["x1"]) - float(rect["x0"])
                height = float(rect["bottom"]) - float(rect["top"])
                if 5 <= width <= 15 and 5 <= height <= 15 and abs(width - height) < 2:
                    structure["checkboxes"].append({
                        "page": page_num,
                        "x0": round(float(rect["x0"]), 1),
                        "top": round(float(rect["top"]), 1),
                        "x1": round(float(rect["x1"]), 1),
                        "bottom": round(float(rect["bottom"]), 1),
                        "center_x": round((float(rect["x0"]) + float(rect["x1"])) / 2, 1),
                        "center_y": round((float(rect["top"]) + float(rect["bottom"])) / 2, 1),
                    })

    # Group horizontal lines by page → derive row boundaries.
    lines_by_page: dict[int, list[float]] = {}
    for line in structure["lines"]:
        lines_by_page.setdefault(line["page"], []).append(line["y"])

    for page, y_coords in lines_by_page.items():
        ys = sorted(set(y_coords))
        for i in range(len(ys) - 1):
            structure["row_boundaries"].append({
                "page": page,
                "row_top": ys[i],
                "row_bottom": ys[i + 1],
                "row_height": round(ys[i + 1] - ys[i], 1),
            })

    return structure


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: extract_form_structure.py <input.pdf> <output.json>", file=sys.stderr)
        sys.exit(1)

    pdf_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    if not pdf_path.exists():
        print(f"Error: input PDF not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Extracting structure from {pdf_path}...")
    structure = extract_form_structure(pdf_path)

    output_path.write_text(json.dumps(structure, indent=2), encoding="utf-8")

    print("Found:")
    print(f"  - {len(structure['pages'])} page(s)")
    print(f"  - {len(structure['labels'])} text label(s)")
    print(f"  - {len(structure['lines'])} horizontal line(s)")
    print(f"  - {len(structure['checkboxes'])} checkbox(es)")
    print(f"  - {len(structure['row_boundaries'])} row boundary(ies)")
    print(f"Saved to {output_path}")


if __name__ == "__main__":
    main()
