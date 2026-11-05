"""PDF wrapper — IO + manifest layer over :mod:`render.pdf`."""

from __future__ import annotations

import logging
from pathlib import Path

from ._types import Manifest, PageImage, RenderOptions
from .dispatch import parse_page_range
from .render.pdf import extract_pdf

logger = logging.getLogger(__name__)


def render(
    src: Path,
    out_dir: Path,
    opts: RenderOptions,
    manifest: Manifest,
) -> None:
    try:
        pdf_bytes = src.read_bytes()
    except Exception as exc:
        manifest.warnings.append(f"failed to read pdf: {exc}")
        return

    # First parse with a permissive max so we don't throw away the user's
    # spec; the shared lib re-clamps against the real ``total_pages`` it
    # learns from PyMuPDF.
    selected_pages = parse_page_range(opts.page_range, 10**6)

    text, page_images, total_pages = extract_pdf(
        pdf_bytes,
        max_pages=opts.max_pages,
        page_indices=selected_pages,
        render_images=not opts.text_only,
    )
    if total_pages == 0 and not text:
        manifest.warnings.append("pdf parse produced no pages or text")
        return

    manifest.page_count = total_pages

    if not opts.text_only and page_images:
        pages_dir = out_dir / "pages"
        pages_dir.mkdir(exist_ok=True)
        for pi in page_images:
            png_path = pages_dir / f"p{pi.page:03}.png"
            try:
                png_path.write_bytes(pi.png_bytes)
            except Exception as exc:
                manifest.warnings.append(
                    f"pdf page {pi.page} write failed: {exc}",
                )
                continue
            manifest.pages.append(PageImage(
                page=pi.page,
                relpath=str(png_path.relative_to(out_dir)),
                size_bytes=png_path.stat().st_size,
                width=pi.width,
                height=pi.height,
            ))

    if text:
        text_path = out_dir / "text.md"
        text_path.write_text(text, encoding="utf-8")
        manifest.text_relpath = "text.md"
        manifest.extracted_text_chars = len(text)

    manifest.rendered_page_count = len(manifest.pages)
    manifest.summary["total_pages"] = total_pages
    manifest.summary["rendered_pages"] = manifest.rendered_page_count
