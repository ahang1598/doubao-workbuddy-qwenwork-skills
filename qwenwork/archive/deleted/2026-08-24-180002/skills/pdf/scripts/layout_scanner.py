"""CLI: scan a non-fillable PDF for the geometry needed to place text.

Produces a JSON description of the raw page structure:
- ``labels``   : every extracted word with its bounding box
- ``lines``    : long horizontal rules that mark row boundaries
- ``checkboxes``: small near-square rectangles
- ``row_boundaries``: consecutive line pairs and their heights

Coordinates are in PDF points with y measured from the top of the page.

Usage: python layout_scanner.py <input.pdf> <output.json>
"""

import json
import sys

import pdfplumber

# Heuristics for what counts as a rule line / checkbox rectangle.
_MIN_LINE_SPAN_RATIO = 0.5   # a rule must span > 50% of the page width
_BOX_MIN = 5                 # checkbox side length lower bound (points)
_BOX_MAX = 15                # checkbox side length upper bound (points)
_BOX_SQUARENESS = 2          # max |width - height| to still count as square


def _scan_page(page, page_number, structure):
    """Append labels, lines and checkboxes found on one page to ``structure``."""
    structure["pages"].append(
        {
            "page_number": page_number,
            "width": float(page.width),
            "height": float(page.height),
        }
    )

    for word in page.extract_words():
        structure["labels"].append(
            {
                "page": page_number,
                "text": word["text"],
                "x0": round(float(word["x0"]), 1),
                "top": round(float(word["top"]), 1),
                "x1": round(float(word["x1"]), 1),
                "bottom": round(float(word["bottom"]), 1),
            }
        )

    for line in page.lines:
        if abs(float(line["x1"]) - float(line["x0"])) > page.width * _MIN_LINE_SPAN_RATIO:
            structure["lines"].append(
                {
                    "page": page_number,
                    "y": round(float(line["top"]), 1),
                    "x0": round(float(line["x0"]), 1),
                    "x1": round(float(line["x1"]), 1),
                }
            )

    for rect in page.rects:
        width = float(rect["x1"]) - float(rect["x0"])
        height = float(rect["bottom"]) - float(rect["top"])
        if (
            _BOX_MIN <= width <= _BOX_MAX
            and _BOX_MIN <= height <= _BOX_MAX
            and abs(width - height) < _BOX_SQUARENESS
        ):
            structure["checkboxes"].append(
                {
                    "page": page_number,
                    "x0": round(float(rect["x0"]), 1),
                    "top": round(float(rect["top"]), 1),
                    "x1": round(float(rect["x1"]), 1),
                    "bottom": round(float(rect["bottom"]), 1),
                    "center_x": round((float(rect["x0"]) + float(rect["x1"])) / 2, 1),
                    "center_y": round((float(rect["top"]) + float(rect["bottom"])) / 2, 1),
                }
            )


def _derive_row_boundaries(structure):
    """Turn the collected horizontal lines into consecutive row bands."""
    ys_by_page = {}
    for line in structure["lines"]:
        ys_by_page.setdefault(line["page"], []).append(line["y"])

    for page, ys in ys_by_page.items():
        ys = sorted(set(ys))
        for top, bottom in zip(ys, ys[1:]):
            structure["row_boundaries"].append(
                {
                    "page": page,
                    "row_top": top,
                    "row_bottom": bottom,
                    "row_height": round(bottom - top, 1),
                }
            )


def scan_layout(pdf_path):
    structure = {
        "pages": [],
        "labels": [],
        "lines": [],
        "checkboxes": [],
        "row_boundaries": [],
    }
    with pdfplumber.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf.pages, 1):
            _scan_page(page, page_number, structure)
    _derive_row_boundaries(structure)
    return structure


def main(argv):
    if len(argv) != 3:
        print("Usage: layout_scanner.py <input.pdf> <output.json>")
        sys.exit(1)

    pdf_path, output_path = argv[1], argv[2]
    print(f"Extracting structure from {pdf_path}...")
    structure = scan_layout(pdf_path)

    with open(output_path, "w") as handle:
        json.dump(structure, handle, indent=2)

    print("Found:")
    print(f"  - {len(structure['pages'])} pages")
    print(f"  - {len(structure['labels'])} text labels")
    print(f"  - {len(structure['lines'])} horizontal lines")
    print(f"  - {len(structure['checkboxes'])} checkboxes")
    print(f"  - {len(structure['row_boundaries'])} row boundaries")
    print(f"Saved to {output_path}")


if __name__ == "__main__":
    main(sys.argv)
