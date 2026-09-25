"""
Extract form structure from a non-fillable PDF.

This script analyzes the PDF to find:
- Text labels with their exact coordinates
- Horizontal lines (row boundaries)
- Checkboxes (small rectangles)

Output: A JSON file with the form structure that can be used to generate
accurate field coordinates for filling.

Coordinates use PyMuPDF (MuPDF) page space: the origin is at the top-left and
y increases downward. Bounding boxes store y0 as "top" (the upper edge) and y1
as "bottom" (the lower edge), so top < bottom for a valid box.

Usage: python extract_form_structure.py <input.pdf> <output.json>
"""

import argparse
import json

import pymupdf


def extract_form_structure(pdf_path):
    structure = {
        "pages": [],
        "labels": [],
        "lines": [],
        "checkboxes": [],
        "row_boundaries": []
    }

    with pymupdf.open(pdf_path) as document:
        for page_num, page in enumerate(document, 1):
            structure["pages"].append({
                "page_number": page_num,
                "width": float(page.rect.width),
                "height": float(page.rect.height)
            })

            words = page.get_text("words", sort=True)
            for word in words:
                structure["labels"].append({
                    "page": page_num,
                    "text": word[4],
                    "x0": round(float(word[0]), 1),
                    "top": round(float(word[1]), 1),
                    "x1": round(float(word[2]), 1),
                    "bottom": round(float(word[3]), 1)
                })

            for drawing in page.get_drawings():
                for item in drawing["items"]:
                    operator = item[0]
                    if operator == "l":
                        start, end = item[1], item[2]
                        midpoint_y = float((start.y + end.y) / 2)
                        if (
                            abs(float(start.y) - float(end.y)) <= 1
                            and abs(float(end.x) - float(start.x)) > page.rect.width * 0.5
                            and 0 <= midpoint_y <= page.rect.height
                            and max(float(start.x), float(end.x)) >= 0
                            and min(float(start.x), float(end.x)) <= page.rect.width
                        ):
                            structure["lines"].append({
                                "page": page_num,
                                "y": round(midpoint_y, 1),
                                "x0": round(float(min(start.x, end.x)), 1),
                                "x1": round(float(max(start.x, end.x)), 1)
                            })
                    elif operator == "re":
                        rect = pymupdf.Rect(item[1])
                        width = float(rect.width)
                        height = float(rect.height)
                        center = pymupdf.Point(
                            (rect.x0 + rect.x1) / 2,
                            (rect.y0 + rect.y1) / 2,
                        )
                        if (
                            5 <= width <= 15
                            and 5 <= height <= 15
                            and abs(width - height) < 2
                            and page.rect.contains(center)
                        ):
                            structure["checkboxes"].append({
                                "page": page_num,
                                "x0": round(float(rect.x0), 1),
                                "top": round(float(rect.y0), 1),
                                "x1": round(float(rect.x1), 1),
                                "bottom": round(float(rect.y1), 1),
                                "center_x": round(float((rect.x0 + rect.x1) / 2), 1),
                                "center_y": round(float((rect.y0 + rect.y1) / 2), 1)
                            })

    lines_by_page = {}
    for line in structure["lines"]:
        page = line["page"]
        if page not in lines_by_page:
            lines_by_page[page] = []
        lines_by_page[page].append(line["y"])

    for page, y_coords in lines_by_page.items():
        y_coords = sorted(set(y_coords))
        for i in range(len(y_coords) - 1):
            structure["row_boundaries"].append({
                "page": page,
                "row_top": y_coords[i],
                "row_bottom": y_coords[i + 1],
                "row_height": round(y_coords[i + 1] - y_coords[i], 1)
            })

    return structure


def main():
    """Parse arguments and extract visible form structure as JSON."""
    parser = argparse.ArgumentParser(
        description="Extract labels, lines, and checkboxes from a PDF form."
    )
    parser.add_argument("input_pdf", help="Path to the input PDF")
    parser.add_argument("output_json", help="Path for the output JSON file")
    args = parser.parse_args()

    print(f"Extracting structure from {args.input_pdf}...")
    structure = extract_form_structure(args.input_pdf)

    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(structure, f, indent=2)

    print(f"Found:")
    print(f"  - {len(structure['pages'])} pages")
    print(f"  - {len(structure['labels'])} text labels")
    print(f"  - {len(structure['lines'])} horizontal lines")
    print(f"  - {len(structure['checkboxes'])} checkboxes")
    print(f"  - {len(structure['row_boundaries'])} row boundaries")
    print(f"Saved to {args.output_json}")


if __name__ == "__main__":
    main()
