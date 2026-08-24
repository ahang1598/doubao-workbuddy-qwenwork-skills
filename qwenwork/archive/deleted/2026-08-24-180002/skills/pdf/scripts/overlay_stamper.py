"""CLI: stamp free-text annotations onto a non-fillable PDF.

Reads a ``fields.json`` describing pages and form fields, converts each entry
box into PDF annotation space (handling both PDF-point and image-pixel input
coordinate systems), and writes the annotated document.

Usage: python overlay_stamper.py [input pdf] [fields.json] [output pdf]
"""

import json
import sys

from pypdf import PdfReader, PdfWriter
from pypdf.annotations import FreeText

_DEFAULT_FONT = "Arial"
_DEFAULT_FONT_SIZE = 14
_DEFAULT_FONT_COLOR = "000000"


def _rect_from_image_space(bbox, image_width, image_height, pdf_width, pdf_height):
    """Map a pixel-space box (y-down) to PDF annotation space (y-up)."""
    x_scale = pdf_width / image_width
    y_scale = pdf_height / image_height
    left = bbox[0] * x_scale
    right = bbox[2] * x_scale
    top = pdf_height - (bbox[1] * y_scale)
    bottom = pdf_height - (bbox[3] * y_scale)
    return left, bottom, right, top


def _rect_from_pdf_space(bbox, pdf_height):
    """Flip a PDF-point box (y-down as authored) to annotation space (y-up)."""
    left = bbox[0]
    right = bbox[2]
    top = pdf_height - bbox[1]
    bottom = pdf_height - bbox[3]
    return left, bottom, right, top


def _page_dimensions(reader):
    """Return {1-based page number: [width, height]} from the source PDF."""
    dimensions = {}
    for index, page in enumerate(reader.pages):
        box = page.mediabox
        dimensions[index + 1] = [box.width, box.height]
    return dimensions


def _resolve_rect(field, page_meta, pdf_width, pdf_height):
    """Choose the right coordinate transform for one field's entry box."""
    if "pdf_width" in page_meta:
        return _rect_from_pdf_space(field["entry_bounding_box"], float(pdf_height))
    return _rect_from_image_space(
        field["entry_bounding_box"],
        page_meta["image_width"],
        page_meta["image_height"],
        float(pdf_width),
        float(pdf_height),
    )


def stamp_form(input_pdf, fields_json, output_pdf):
    with open(fields_json) as handle:
        document = json.load(handle)

    reader = PdfReader(input_pdf)
    writer = PdfWriter()
    writer.append(reader)

    dimensions = _page_dimensions(reader)
    page_meta_by_number = {p["page_number"]: p for p in document["pages"]}

    stamped = 0
    for field in document["form_fields"]:
        page_num = field["page_number"]
        pdf_width, pdf_height = dimensions[page_num]
        rect = _resolve_rect(
            field, page_meta_by_number[page_num], pdf_width, pdf_height
        )

        entry_text = field.get("entry_text")
        if not entry_text or not entry_text.get("text"):
            continue

        annotation = FreeText(
            text=entry_text["text"],
            rect=rect,
            font=entry_text.get("font", _DEFAULT_FONT),
            font_size=f"{entry_text.get('font_size', _DEFAULT_FONT_SIZE)}pt",
            font_color=entry_text.get("font_color", _DEFAULT_FONT_COLOR),
            border_color=None,
            background_color=None,
        )
        writer.add_annotation(page_number=page_num - 1, annotation=annotation)
        stamped += 1

    with open(output_pdf, "wb") as handle:
        writer.write(handle)

    print(f"Successfully filled PDF form and saved to {output_pdf}")
    print(f"Added {stamped} text annotations")


def main(argv):
    if len(argv) != 4:
        print("Usage: overlay_stamper.py [input pdf] [fields.json] [output pdf]")
        sys.exit(1)
    stamp_form(argv[1], argv[2], argv[3])


if __name__ == "__main__":
    main(sys.argv)
