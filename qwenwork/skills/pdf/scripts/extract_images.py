#!/usr/bin/env python3
"""
extract_images.py — PDF Image Extraction

Extracts all embedded images from a PDF, saving them to an output directory.
Reports image metadata (size, format, page location).

Usage:
    python scripts/extract_images.py document.pdf --output images/
    python scripts/extract_images.py document.pdf --output images/ --min-size 50
    python scripts/extract_images.py document.pdf --output images/ --format png
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def extract_embedded_images(pdf_path: Path, output_dir: Path,
                             min_dimension: int, force_format: str | None) -> list[dict]:
    """
    Extract all embedded images from the PDF.
    Returns a list of metadata dicts for each saved image.
    """
    try:
        import pypdf
    except ImportError:
        print("Error: pypdf required. Run: pip install pypdf", file=sys.stderr)
        sys.exit(1)

    try:
        from PIL import Image
        import io
        pil_available = True
    except ImportError:
        pil_available = False

    output_dir.mkdir(parents=True, exist_ok=True)
    reader = pypdf.PdfReader(str(pdf_path))
    saved: list[dict] = []
    img_counter = 0

    for page_idx, page in enumerate(reader.pages):
        try:
            page_images = page.images
        except Exception:
            continue

        for img_obj in page_images:
            img_counter += 1
            raw_data = img_obj.data
            name_hint = img_obj.name or f"img_{img_counter}"

            # Determine format and extension
            ext = Path(name_hint).suffix.lower().lstrip(".") or "png"
            if force_format:
                ext = force_format.lower()

            out_name = f"page{page_idx+1:03d}_{img_counter:04d}.{ext}"
            out_path = output_dir / out_name

            # If PIL is available, check dimensions and optionally convert
            if pil_available:
                try:
                    img = Image.open(io.BytesIO(raw_data))
                    width, height = img.size
                    if width < min_dimension or height < min_dimension:
                        continue  # skip tiny images (likely icons or decorations)
                    if force_format:
                        img.save(str(out_path), force_format.upper())
                    else:
                        out_path.write_bytes(raw_data)
                    img_format = img.format or ext.upper()
                    mode = img.mode
                except Exception:
                    out_path.write_bytes(raw_data)
                    width, height, img_format, mode = 0, 0, ext.upper(), "unknown"
            else:
                if min_dimension > 0:
                    pass  # can't check without PIL; save anyway
                out_path.write_bytes(raw_data)
                width, height, img_format, mode = 0, 0, ext.upper(), "unknown"

            saved.append({
                "file": str(out_path),
                "page": page_idx + 1,
                "index": img_counter,
                "width_px": width,
                "height_px": height,
                "format": img_format,
                "mode": mode,
                "size_bytes": len(raw_data),
            })

    return saved


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract images embedded in a PDF.")
    parser.add_argument("pdf_file", help="Input PDF path")
    parser.add_argument("--output", "-o", required=True, help="Output directory for images")
    parser.add_argument("--min-size", type=int, default=20, metavar="PX",
                        help="Minimum dimension (px) — skip smaller images (default: 20)")
    parser.add_argument("--format", choices=["png", "jpg", "jpeg", "bmp"],
                        help="Force output format (default: keep original)")
    parser.add_argument("--report", help="Save JSON report to this file path")
    args = parser.parse_args()

    pdf_path = Path(args.pdf_file)
    if not pdf_path.exists():
        print(f"Error: file not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Extracting images from {pdf_path}…")
    records = extract_embedded_images(
        pdf_path,
        Path(args.output),
        min_dimension=args.min_size,
        force_format=args.format,
    )

    if not records:
        print("No images found (or all below minimum size threshold).")
        return

    print(f"Saved {len(records)} image(s) to {args.output}/")
    for rec in records:
        dim = f"{rec['width_px']}×{rec['height_px']}px" if rec["width_px"] else "?"
        print(f"  [{rec['page']:>3}] {Path(rec['file']).name}  {dim}  {rec['format']}")

    if args.report:
        import pypdf as _pypdf
        total_pages = len(_pypdf.PdfReader(str(pdf_path)).pages)
        report_path = Path(args.report)
        report_path.write_text(
            json.dumps({"source": str(pdf_path), "total_pages": total_pages, "images": records}, indent=2),
            encoding="utf-8"
        )
        print(f"JSON report → {report_path}")


if __name__ == "__main__":
    main()
