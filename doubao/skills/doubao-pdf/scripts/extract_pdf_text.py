"""Extract visible PDF text as plain text or structured JSON."""

import argparse
import json
from pathlib import Path

import pymupdf


def extract(pdf_path, output_path, structured=False):
    with pymupdf.open(pdf_path) as document:
        if structured:
            pages = []
            for page_number, page in enumerate(document, start=1):
                pages.append({
                    "page": page_number,
                    "width": page.rect.width,
                    "height": page.rect.height,
                    "text": page.get_text("text", sort=True),
                    "blocks": [list(block) for block in page.get_text("blocks", sort=True)],
                    "words": [list(word) for word in page.get_text("words", sort=True)],
                })
            Path(output_path).write_text(
                json.dumps({"pages": pages}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        else:
            pages = [page.get_text("text", sort=True) for page in document]
            Path(output_path).write_text("\n\f\n".join(pages), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(
        description="Extract visible PDF text with PyMuPDF in reading order."
    )
    parser.add_argument("input_pdf")
    parser.add_argument("output")
    parser.add_argument(
        "--structured",
        action="store_true",
        help="Write JSON containing page text, blocks, words, and coordinates.",
    )
    args = parser.parse_args()
    extract(args.input_pdf, args.output, structured=args.structured)


if __name__ == "__main__":
    main()
