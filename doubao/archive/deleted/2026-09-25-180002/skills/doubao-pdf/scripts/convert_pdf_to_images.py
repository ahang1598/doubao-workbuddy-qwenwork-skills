"""Render PDF pages to size-limited PNG images for visual review."""

import argparse
import os

import pymupdf


def convert(pdf_path, output_dir, max_dim=1000):
    os.makedirs(output_dir, exist_ok=True)
    with pymupdf.open(pdf_path) as document:
        for index, page in enumerate(document, start=1):
            scale_200_dpi = 200 / 72
            scale_to_limit = max_dim / max(page.rect.width, page.rect.height)
            scale = min(scale_200_dpi, scale_to_limit)
            pixmap = page.get_pixmap(
                matrix=pymupdf.Matrix(scale, scale),
                alpha=False,
            )

            image_path = os.path.join(output_dir, f"page_{index}.png")
            pixmap.save(image_path)
            size = (pixmap.width, pixmap.height)
            print(f"Saved page {index} as {image_path} (size: {size})")

        print(f"Converted {document.page_count} pages to PNG images")


def main():
    """Parse arguments and render the requested PDF pages."""
    parser = argparse.ArgumentParser(
        description="Render PDF pages to size-limited PNG images."
    )
    parser.add_argument("input_pdf", help="Path to the input PDF")
    parser.add_argument("output_directory", help="Directory for rendered PNG files")
    args = parser.parse_args()
    convert(args.input_pdf, args.output_directory)


if __name__ == "__main__":
    main()
