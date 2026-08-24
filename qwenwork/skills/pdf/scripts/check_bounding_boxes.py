#!/usr/bin/env python3
"""
check_bounding_boxes.py — validate fields.json for the overlay form-fill path.

Reports two classes of error:
- Intersecting label/entry bounding boxes (would cause overlapping text)
- Entry box height smaller than the font size (text will clip)

Reads fields.json (the schema fill_form_overlay.py consumes). Coordinates
follow pdfplumber's convention: y=0 at the TOP of the page, y increases
downward — the same convention extract_form_structure.py produces.

Usage:
    python scripts/check_bounding_boxes.py <fields.json>
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class RectAndField:
    rect: list[float]
    rect_type: str       # "label" or "entry"
    field: dict


def get_bounding_box_messages(fields_json_stream) -> list[str]:
    messages: list[str] = []
    fields = json.load(fields_json_stream)
    messages.append(f"Read {len(fields['form_fields'])} fields")

    def rects_intersect(r1: list[float], r2: list[float]) -> bool:
        disjoint_horizontal = r1[0] >= r2[2] or r1[2] <= r2[0]
        disjoint_vertical = r1[1] >= r2[3] or r1[3] <= r2[1]
        return not (disjoint_horizontal or disjoint_vertical)

    rects_and_fields: list[RectAndField] = []
    for f in fields["form_fields"]:
        rects_and_fields.append(RectAndField(f["label_bounding_box"], "label", f))
        rects_and_fields.append(RectAndField(f["entry_bounding_box"], "entry", f))

    has_error = False
    for i, ri in enumerate(rects_and_fields):
        for j in range(i + 1, len(rects_and_fields)):
            rj = rects_and_fields[j]
            same_page = ri.field["page_number"] == rj.field["page_number"]
            if same_page and rects_intersect(ri.rect, rj.rect):
                has_error = True
                if ri.field is rj.field:
                    messages.append(
                        f"FAILURE: intersection between label and entry bounding boxes "
                        f"for `{ri.field['description']}` ({ri.rect}, {rj.rect})"
                    )
                else:
                    messages.append(
                        f"FAILURE: intersection between {ri.rect_type} bounding box for "
                        f"`{ri.field['description']}` ({ri.rect}) and {rj.rect_type} bounding box "
                        f"for `{rj.field['description']}` ({rj.rect})"
                    )
                if len(messages) >= 20:
                    messages.append("Aborting further checks; fix bounding boxes and try again")
                    return messages

        if ri.rect_type == "entry" and "entry_text" in ri.field:
            font_size = ri.field["entry_text"].get("font_size", 14)
            entry_height = ri.rect[3] - ri.rect[1]
            if entry_height < font_size:
                has_error = True
                messages.append(
                    f"FAILURE: entry bounding box height ({entry_height}) for "
                    f"`{ri.field['description']}` is too short for the text content "
                    f"(font size: {font_size}). Increase the box height or decrease the font size."
                )
                if len(messages) >= 20:
                    messages.append("Aborting further checks; fix bounding boxes and try again")
                    return messages

    if not has_error:
        messages.append("SUCCESS: All bounding boxes are valid")
    return messages


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: check_bounding_boxes.py <fields.json>", file=sys.stderr)
        sys.exit(1)
    path = Path(sys.argv[1])
    if not path.exists():
        print(f"Error: fields.json not found: {path}", file=sys.stderr)
        sys.exit(1)
    with path.open() as f:
        messages = get_bounding_box_messages(f)
    for msg in messages:
        print(msg)
    if any(m.startswith("FAILURE") for m in messages):
        sys.exit(2)


if __name__ == "__main__":
    main()
