import json
import os
import sys
import subprocess
import importlib.util


def ensure_deps():
    missing = [p for p in ("pymupdf",) if importlib.util.find_spec(p) is None]
    if missing:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install",
             "--break-system-packages", "-q"] + missing
        )

ensure_deps()

import fitz  # PyMuPDF


# Converts each page of a PDF to a PNG image.


def convert(pdf_path, output_dir, max_dim=1000):
    os.makedirs(output_dir, exist_ok=True)
    doc = fitz.open(pdf_path)
    page_count = len(doc)

    for i, page in enumerate(doc):
        # Render page to image at 200 DPI
        pix = page.get_pixmap(dpi=200)
        width, height = pix.width, pix.height

        # Scale if needed
        scale_factor = min(max_dim / width, max_dim / height, 1.0)
        if scale_factor < 1.0:
            new_w = int(width * scale_factor)
            new_h = int(height * scale_factor)
            pix = page.get_pixmap(dpi=int(200 * scale_factor), matrix=fitz.Matrix(scale_factor, scale_factor))
        
        image_path = os.path.join(output_dir, f"page_{i+1}.png")
        pix.save(image_path)
        print(f"Saved page {i+1} as {image_path} (size: {pix.width}x{pix.height})")

    doc.close()
    print(f"Converted {page_count} pages to PNG images")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: convert_pdf_to_images.py [input pdf] [output directory]")
        sys.exit(1)
    pdf_path = sys.argv[1]
    output_directory = sys.argv[2]
    convert(pdf_path, output_directory)
