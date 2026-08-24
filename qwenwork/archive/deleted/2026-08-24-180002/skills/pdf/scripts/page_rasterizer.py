"""CLI: rasterize every PDF page to a PNG, downscaling oversized pages.

Renders at 200 DPI and clamps the longest side to ``MAX_EDGE`` pixels so the
resulting images stay manageable for downstream visual analysis.

Usage: python page_rasterizer.py <input pdf> <output directory>
"""

import os
import sys

from pdf2image import convert_from_path

MAX_EDGE = 1000


def _clamp_to_max_edge(image, max_edge=MAX_EDGE):
    """Shrink ``image`` proportionally if either side exceeds ``max_edge``."""
    width, height = image.size
    if width <= max_edge and height <= max_edge:
        return image
    factor = min(max_edge / width, max_edge / height)
    return image.resize((int(width * factor), int(height * factor)))


def rasterize(pdf_path, output_dir, max_edge=MAX_EDGE):
    pages = convert_from_path(pdf_path, dpi=200)
    for index, page in enumerate(pages):
        page = _clamp_to_max_edge(page, max_edge)
        destination = os.path.join(output_dir, f"page_{index + 1}.png")
        page.save(destination)
        print(f"Saved page {index + 1} as {destination} (size: {page.size})")
    print(f"Converted {len(pages)} pages to PNG images")


def main(argv):
    if len(argv) != 3:
        print("Usage: page_rasterizer.py [input pdf] [output directory]")
        sys.exit(1)
    rasterize(argv[1], argv[2])


if __name__ == "__main__":
    main(sys.argv)
