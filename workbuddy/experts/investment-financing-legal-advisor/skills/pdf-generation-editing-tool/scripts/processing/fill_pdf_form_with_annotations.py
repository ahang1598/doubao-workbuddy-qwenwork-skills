import json
import os
import sys
import importlib.util
from io import BytesIO


def ensure_deps():
    missing = [p for p in ("pypdf", "reportlab") if importlib.util.find_spec(p) is None]
    if missing:
        import subprocess
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install",
             "--break-system-packages", "-q"] + missing
        )

ensure_deps()

from pypdf import PdfReader, PdfWriter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas

# Fills a PDF by adding text annotations defined in `fields.json`. See forms.md.


def transform_coordinates(bbox, image_width, image_height, pdf_width, pdf_height):
    """Transform bounding box from image coordinates to PDF coordinates"""
    x_scale = pdf_width / image_width
    y_scale = pdf_height / image_height

    left = bbox[0] * x_scale
    right = bbox[2] * x_scale

    # Flip Y coordinates for PDF
    top = pdf_height - (bbox[1] * y_scale)
    bottom = pdf_height - (bbox[3] * y_scale)

    return left, bottom, right, top


def fill_pdf_form(input_pdf_path, fields_json_path, output_pdf_path):
    """Fill the PDF form with data from fields.json using embedded Chinese font"""

    # Register built-in Chinese font (always available in reportlab)
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    CHINESE_FONT = "STSong-Light"

    with open(fields_json_path, "r", encoding="utf-8") as f:
        fields_data = json.load(f)

    reader = PdfReader(input_pdf_path)
    writer = PdfWriter()
    writer.append(reader)

    pdf_dimensions = {}
    for i, page in enumerate(reader.pages):
        mediabox = page.mediabox
        pdf_dimensions[i + 1] = [mediabox.width, mediabox.height]

    # Group fields by page
    fields_by_page = {}
    for field in fields_data["form_fields"]:
        page_num = field["page_number"]
        if page_num not in fields_by_page:
            fields_by_page[page_num] = []
        fields_by_page[page_num].append(field)

    # Create overlay PDFs for each page with fields
    for page_num, fields in fields_by_page.items():
        pdf_width, pdf_height = pdf_dimensions[page_num]
        overlay_buffer = BytesIO()
        c = canvas.Canvas(overlay_buffer, pagesize=(pdf_width, pdf_height))

        for field in fields:
            page_info = next(
                p for p in fields_data["pages"] if p["page_number"] == page_num
            )
            image_width = page_info["image_width"]
            image_height = page_info["image_height"]

            transformed_box = transform_coordinates(
                field["entry_bounding_box"],
                image_width,
                image_height,
                pdf_width,
                pdf_height,
            )

            if "entry_text" not in field or "text" not in field["entry_text"]:
                continue
            entry_text = field["entry_text"]
            text = entry_text.get("text", "")
            if not text:
                continue

            font_size = entry_text.get("font_size", 14)
            font_color = entry_text.get("font_color", "000000")

            # Parse color
            try:
                r = int(font_color[0:2], 16) / 255.0
                g = int(font_color[2:4], 16) / 255.0
                b = int(font_color[4:6], 16) / 255.0
            except:
                r, g, b = 0, 0, 0

            c.setFont(CHINESE_FONT, font_size)
            c.setFillColorRGB(r, g, b)

            left, bottom, right, top = transformed_box
            c.drawString(left + 2, top - font_size, text)

        c.save()
        overlay_buffer.seek(0)
        overlay_reader = PdfReader(overlay_buffer)
        if overlay_reader.pages:
            writer.add_page_overlay_pdf(overlay_reader, page_number=page_num - 1)

    with open(output_pdf_path, "wb") as output:
        writer.write(output)

    total_fields = sum(len(fields) for fields in fields_by_page.values())
    print(f"Successfully filled PDF form and saved to {output_pdf_path}")
    print(f"Added {total_fields} text annotations with embedded Chinese font")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(
            "Usage: fill_pdf_form_with_annotations.py [input pdf] [fields.json] [output pdf]"
        )
        sys.exit(1)
    input_pdf = sys.argv[1]
    fields_json = sys.argv[2]
    output_pdf = sys.argv[3]

    fill_pdf_form(input_pdf, fields_json, output_pdf)
