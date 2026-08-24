#!/usr/bin/env python3
"""
fill_form_overlay.py — fill a non-fillable PDF by overlaying text stamps.

For AcroForm PDFs use ``fill_form.py``. For flat / scanned PDFs (no widget
fields), use this script: it overlays text on top of the page at agent-supplied
coordinates by drawing onto a reportlab stamp page and merging that stamp
into the target page with pypdf.

Why a stamp+merge instead of pypdf's ``FreeText`` annotation?
- ``FreeText`` is a PDF annotation; the viewer looks up the named font at
  display time. Chinese / Japanese / Korean text named with ``font="Arial"``
  renders as empty boxes on most viewers.
- The reportlab stamp embeds the actual glyph bytes (via ``_fonts.py``'s
  CJK-aware ``registerFont`` family), so the output PDF is self-contained
  and renders the same everywhere.

Coordinate convention (matches extract_form_structure.py output):
- fields.json uses TOP-left origin: y=0 at top of page, y grows downward.
- When ``pages[i]`` carries ``pdf_width`` / ``pdf_height``, coordinates are
  PDF points (the form_structure path).
- When ``pages[i]`` carries ``image_width`` / ``image_height``, coordinates
  are pixels in the rendered page image (the visual-estimation path); this
  script scales them to PDF points.

Inside the writer we flip Y once: PDF's native origin is BOTTOM-left.

Usage:
    python scripts/fill_form_overlay.py <input.pdf> <fields.json> <output.pdf>

See also: extract_form_structure.py, check_bounding_boxes.py.
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))


def _require(name: str, install: str):
    """Import a top-level module by name or exit with a clear pip hint."""
    try:
        return __import__(name)
    except ImportError:
        print(f"Error: {name} required. Run: {install}", file=sys.stderr)
        sys.exit(1)


def _transform_box_topleft_to_pdf(
    bbox: list[float],
    pdf_width: float,
    pdf_height: float,
    src_width: float | None = None,
    src_height: float | None = None,
) -> tuple[float, float, float, float]:
    """Convert a top-left bounding box to PDF (bottom-left origin) points.

    ``bbox`` is ``[x0, top, x1, bottom]`` in the source coordinate space.
    Returns ``(left, bottom, right, top)`` in PDF points.
    """
    x_scale = 1.0 if src_width is None else pdf_width / float(src_width)
    y_scale = 1.0 if src_height is None else pdf_height / float(src_height)
    left = bbox[0] * x_scale
    right = bbox[2] * x_scale
    top_pdf = pdf_height - (bbox[1] * y_scale)
    bottom_pdf = pdf_height - (bbox[3] * y_scale)
    return left, bottom_pdf, right, top_pdf


def _hex_to_rgb01(hex_color: str) -> tuple[float, float, float]:
    s = hex_color.lstrip("#")
    if len(s) != 6:
        return 0.0, 0.0, 0.0
    r, g, b = int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)
    return r / 255.0, g / 255.0, b / 255.0


def _build_stamp(
    page_width: float,
    page_height: float,
    stamps: list[dict],
    cjk_family: str | None,
    cjk_bold_family: str | None,
) -> bytes:
    """Render a one-page reportlab PDF carrying every text stamp for this page."""
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(page_width, page_height))
    c.saveState()
    for s in stamps:
        text = s["text"]
        left, bottom, right, top = s["rect"]
        font_size = float(s.get("font_size") or 12)
        bold = bool(s.get("bold"))
        r, g, b = _hex_to_rgb01(s.get("font_color") or "000000")

        # Decide font: contains_cjk → registered CJK family, else core PDF font.
        from _fonts import contains_cjk  # local import; fast after first call
        if contains_cjk(text) and cjk_family:
            font_name = cjk_bold_family if (bold and cjk_bold_family) else cjk_family
        else:
            font_name = "Helvetica-Bold" if bold else "Helvetica"

        c.setFillColorRGB(r, g, b)
        c.setFont(font_name, font_size)

        # Baseline: place text near the top of the entry box, with the font's
        # baseline ≈ top - font_size + small descent buffer. Reportlab y grows
        # upward, so "near top" means a high y.
        baseline_y = top - font_size + (font_size * 0.18)
        # Clip to box bottom if the box is shorter than the font.
        baseline_y = max(baseline_y, bottom)
        c.drawString(left, baseline_y, text)
    c.restoreState()
    c.save()
    return buf.getvalue()


def fill_pdf_form(
    input_pdf_path: Path,
    fields_json_path: Path,
    output_pdf_path: Path,
) -> int:
    _require("pypdf", "pip install pypdf")
    _require("reportlab", "pip install reportlab")

    from pypdf import PdfReader, PdfWriter

    # Register CJK family once for the whole run; idempotent.
    try:
        from _fonts import register_cjk_font
        font_result = register_cjk_font()
    except Exception as exc:  # pragma: no cover — defensive
        print(f"Warning: CJK font registration failed: {exc}", file=sys.stderr)
        font_result = None

    cjk_family = getattr(font_result, "family", None) if (font_result and font_result.ok) else None
    cjk_bold_family = getattr(font_result, "bold_family", None) if (font_result and font_result.ok) else None
    if cjk_family:
        print(f"CJK font: {cjk_family} (bold: {cjk_bold_family or 'fallback to regular'})")
    else:
        reason = getattr(font_result, "reason", "unknown")
        print(
            "Warning: no CJK font registered — Chinese/Japanese/Korean text will "
            f"render as boxes. Reason: {reason}",
            file=sys.stderr,
        )

    fields_data = json.loads(fields_json_path.read_text(encoding="utf-8"))

    reader = PdfReader(str(input_pdf_path))
    writer = PdfWriter()
    writer.append(reader)

    # Index pages metadata for quick lookup.
    pages_meta = {p["page_number"]: p for p in fields_data["pages"]}

    # Group stamps by page so we render one stamp PDF per page.
    stamps_by_page: dict[int, list[dict]] = {}
    for field in fields_data["form_fields"]:
        if "entry_text" not in field or "text" not in field["entry_text"]:
            continue
        entry = field["entry_text"]
        text = entry["text"]
        if not text:
            continue

        page_num = field["page_number"]
        page_info = pages_meta[page_num]
        page = reader.pages[page_num - 1]
        pdf_w = float(page.mediabox.width)
        pdf_h = float(page.mediabox.height)

        if "pdf_width" in page_info:
            rect = _transform_box_topleft_to_pdf(field["entry_bounding_box"], pdf_w, pdf_h)
        else:
            rect = _transform_box_topleft_to_pdf(
                field["entry_bounding_box"],
                pdf_w,
                pdf_h,
                src_width=page_info["image_width"],
                src_height=page_info["image_height"],
            )

        stamps_by_page.setdefault(page_num, []).append({
            "text": text,
            "rect": rect,
            "font_size": entry.get("font_size", 12),
            "font_color": entry.get("font_color", "000000"),
            "bold": entry.get("bold", False),
        })

    written = 0
    from pypdf import PdfReader as _PdfReader
    for page_num, stamps in stamps_by_page.items():
        target_page = writer.pages[page_num - 1]
        page_w = float(target_page.mediabox.width)
        page_h = float(target_page.mediabox.height)
        stamp_bytes = _build_stamp(page_w, page_h, stamps, cjk_family, cjk_bold_family)
        stamp_reader = _PdfReader(io.BytesIO(stamp_bytes))
        target_page.merge_page(stamp_reader.pages[0])
        written += len(stamps)

    with output_pdf_path.open("wb") as out:
        writer.write(out)

    print(f"Filled {written} field(s) across {len(stamps_by_page)} page(s) → {output_pdf_path}")
    return written


def main() -> None:
    if len(sys.argv) != 4:
        print(
            "Usage: fill_form_overlay.py <input.pdf> <fields.json> <output.pdf>",
            file=sys.stderr,
        )
        sys.exit(1)

    input_pdf = Path(sys.argv[1])
    fields_json = Path(sys.argv[2])
    output_pdf = Path(sys.argv[3])

    if not input_pdf.exists():
        print(f"Error: input PDF not found: {input_pdf}", file=sys.stderr)
        sys.exit(1)
    if not fields_json.exists():
        print(f"Error: fields.json not found: {fields_json}", file=sys.stderr)
        sys.exit(1)

    fill_pdf_form(input_pdf, fields_json, output_pdf)


if __name__ == "__main__":
    main()
