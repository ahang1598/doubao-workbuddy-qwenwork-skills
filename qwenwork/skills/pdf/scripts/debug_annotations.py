#!/usr/bin/env python3
"""
debug_annotations.py — Visual Annotation Debugger

Renders a PDF page to an image and overlays bounding boxes from a
fill descriptor JSON (produced by inspect_form.py). Useful for verifying
that annotation coordinates are correct before committing to fill_form.py.

Supports both AcroForm descriptors and layout-based annotation descriptors.

Usage:
    # Visualise all annotations on all pages
    python scripts/debug_annotations.py form.pdf fields.json --output-dir debug/

    # Visualise a single page
    python scripts/debug_annotations.py form.pdf fields.json --page 1 \
        --output debug_page1.png

    # Higher resolution rendering
    python scripts/debug_annotations.py form.pdf fields.json --dpi 200 \
        --output-dir debug/

Color coding:
    Blue  rectangle  — AcroForm field bounding box
    Green rectangle  — Label zone (layout-based)
    Red   rectangle  — Fill zone (where text will be placed)
    Orange dot       — Exact fill_x / fill_y anchor point
"""

import argparse
import json
import sys
from pathlib import Path


COLOUR_ACROFORM_FIELD = (30, 100, 220)   # blue
COLOUR_LABEL_ZONE     = (30, 180, 80)    # green
COLOUR_FILL_ZONE      = (220, 50, 50)    # red
COLOUR_ANCHOR_DOT     = (255, 140, 0)    # orange


def _pdf_page_to_image(pdf_path: Path, page_idx: int, dpi: int):
    """Render one PDF page to a PIL Image using pypdfium2."""
    try:
        import pypdfium2 as pdfium
    except ImportError:
        print("Error: pypdfium2 required. Run: pip install pypdfium2", file=sys.stderr)
        sys.exit(1)

    pdf = pdfium.PdfDocument(str(pdf_path))
    try:
        if page_idx < 0 or page_idx >= len(pdf):
            return None
        page = pdf[page_idx]
        try:
            return page.render(scale=dpi / 72.0).to_pil()
        finally:
            page.close()
    finally:
        pdf.close()


def _draw_labelled_rect(draw, box: tuple[float, float, float, float],
                         label: str, colour: tuple[int, int, int],
                         line_width: int = 2) -> None:
    """Draw a rectangle with a small text label above it."""
    from PIL import ImageFont
    x0, y0, x1, y1 = box
    draw.rectangle([x0, y0, x1, y1], outline=colour, width=line_width)
    # Small label tag
    tag_y = max(0, y0 - 14)
    draw.rectangle([x0, tag_y, x0 + len(label) * 6 + 4, tag_y + 12],
                   fill=colour)
    try:
        draw.text((x0 + 2, tag_y + 1), label, fill=(255, 255, 255))
    except Exception:
        pass  # font loading can fail in some environments


def _draw_anchor(draw, x: float, y: float, colour: tuple[int, int, int],
                  radius: int = 5) -> None:
    draw.ellipse([x - radius, y - radius, x + radius, y + radius],
                 fill=colour, outline=(0, 0, 0), width=1)


def overlay_acroform(draw, fields: list[dict], page_num: int,
                      img_w: int, img_h: int) -> int:
    """Overlay AcroForm field boxes. Returns count drawn."""
    count = 0
    for field in fields:
        # AcroForm descriptors from inspect_form.py don't have rect coords.
        # We draw a placeholder banner to indicate field presence.
        name = field.get("name", "?")
        ftype = field.get("type", "?")
        fill = field.get("fill_value", "")
        label = f"{name} [{ftype}]"
        if fill:
            label += f" = {fill[:12]}"
        # Without rect data, stack fields vertically as an index
        y_offset = 20 + count * 22
        draw.rectangle([10, y_offset, img_w - 10, y_offset + 18],
                        outline=COLOUR_ACROFORM_FIELD, width=1)
        try:
            draw.text((14, y_offset + 2), label, fill=COLOUR_ACROFORM_FIELD)
        except Exception:
            pass
        count += 1
    return count


def overlay_layout_based(draw, annotations: list[dict], page_num: int,
                          img_w: int, img_h: int, scale_x: float,
                          scale_y: float, pdf_h: float) -> int:
    """
    Overlay annotation zones for layout-based forms.
    Coordinates in the descriptor use pdfplumber's top-origin system.
    We convert to image coordinates using the page height and DPI scale.
    """
    count = 0
    for ann in annotations:
        if ann.get("page", 1) != page_num:
            continue

        fill_val = ann.get("fill_value", "").strip()
        label_text = ann.get("label", "")

        # pdfplumber top-origin → image coordinates
        x0  = float(ann.get("x0", 0))   * scale_x
        top = float(ann.get("top", 0))   * scale_y
        x1  = float(ann.get("x1", x0 + 80)) * scale_x
        bot = float(ann.get("bottom", top + 12)) * scale_y

        # Label zone (green)
        _draw_labelled_rect(draw, (x0, top, x1, bot),
                             label_text[:10], COLOUR_LABEL_ZONE)

        # Fill anchor point (red dot + zone)
        fx = float(ann.get("fill_x", x1 + 5)) * scale_x
        fy = float(ann.get("fill_y", top))     * scale_y

        fill_x1 = fx + max(len(fill_val) * 6, 40) if fill_val else fx + 40
        fill_y1 = fy + 12 * scale_y

        _draw_labelled_rect(draw, (fx, fy, fill_x1, fill_y1),
                             fill_val[:10] if fill_val else "(empty)",
                             COLOUR_FILL_ZONE)
        _draw_anchor(draw, fx, fy, COLOUR_ANCHOR_DOT)

        count += 1
    return count


def render_debug_page(pdf_path: Path, descriptor: dict,
                       page_idx: int, dpi: int) -> "Image":
    """Render one page and draw all overlays. Returns a PIL Image."""
    from PIL import ImageDraw

    img = _pdf_page_to_image(pdf_path, page_idx, dpi)
    if img is None:
        print(f"Warning: could not render page {page_idx + 1}", file=sys.stderr)
        return None

    img_w, img_h = img.size
    draw = ImageDraw.Draw(img)
    page_num = page_idx + 1
    form_type = descriptor.get("form_type", "acroform")

    if form_type == "acroform":
        fields = descriptor.get("fields", [])
        n = overlay_acroform(draw, fields, page_num, img_w, img_h)
        print(f"  Page {page_num}: {n} AcroForm field(s) annotated")
    else:
        # For layout-based: estimate page PDF dimensions from first annotation
        annotations = descriptor.get("annotations", [])
        # scale: map PDF points → image pixels
        # Assume standard A4/Letter: pdf_h ≈ 792pt, img_h = dpi * (792/72) px
        estimated_pdf_h = 792.0
        estimated_pdf_w = 612.0
        scale_x = img_w / estimated_pdf_w
        scale_y = img_h / estimated_pdf_h

        n = overlay_layout_based(draw, annotations, page_num,
                                  img_w, img_h, scale_x, scale_y,
                                  estimated_pdf_h)
        print(f"  Page {page_num}: {n} annotation zone(s) drawn")

    # Legend
    legend_items = [
        (COLOUR_LABEL_ZONE,     "Label zone"),
        (COLOUR_FILL_ZONE,      "Fill zone"),
        (COLOUR_ANCHOR_DOT,     "Fill anchor"),
        (COLOUR_ACROFORM_FIELD, "AcroForm field"),
    ]
    lx, ly = img_w - 180, 10
    for colour, label in legend_items:
        draw.rectangle([lx, ly, lx + 16, ly + 12], fill=colour)
        try:
            draw.text((lx + 20, ly), label, fill=(0, 0, 0))
        except Exception:
            pass
        ly += 18

    return img


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render PDF pages with annotation bounding box overlays for debugging."
    )
    parser.add_argument("pdf_file", help="Input PDF path")
    parser.add_argument("descriptor_file",
                        help="JSON descriptor from inspect_form.py (with fill_value set)")
    parser.add_argument("--page", type=int, default=0,
                        help="Page number to render (1-based). 0 = all pages (default)")
    parser.add_argument("--output", "-o", help="Output image path (single page mode)")
    parser.add_argument("--output-dir", help="Output directory (multi-page mode)")
    parser.add_argument("--dpi", type=int, default=150,
                        help="Rendering DPI (default: 150; use 200-300 for fine detail)")
    args = parser.parse_args()

    pdf_path = Path(args.pdf_file)
    desc_path = Path(args.descriptor_file)

    for p in (pdf_path, desc_path):
        if not p.exists():
            print(f"Error: file not found: {p}", file=sys.stderr)
            sys.exit(1)

    descriptor = json.loads(desc_path.read_text(encoding="utf-8"))

    # Determine pages to render
    try:
        from pypdf import PdfReader
        total_pages = len(PdfReader(str(pdf_path)).pages)
    except Exception:
        total_pages = 1

    if args.page > 0:
        page_indices = [args.page - 1]
    else:
        page_indices = list(range(total_pages))

    print(f"Rendering {len(page_indices)} page(s) at {args.dpi} DPI…")

    for idx in page_indices:
        img = render_debug_page(pdf_path, descriptor, idx, args.dpi)
        if img is None:
            continue

        if args.output and len(page_indices) == 1:
            out_path = Path(args.output)
        elif args.output_dir:
            out_dir = Path(args.output_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / f"debug_page{idx+1:03d}.png"
        else:
            out_path = pdf_path.parent / f"debug_page{idx+1:03d}.png"

        img.save(str(out_path), "PNG")
        print(f"  Saved → {out_path}")

    print("Done. Review the debug images to verify annotation placement.")


if __name__ == "__main__":
    main()
