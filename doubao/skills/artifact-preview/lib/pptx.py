"""PPTX wrapper — IO + manifest layer over :mod:`render.pptx`.

Text comes from python-pptx; screenshots from LibreOffice → PDF → PNG
(both handled by the shared lib). All extracted bytes/strings are
written to ``out_dir`` here. PPTX text MUST be written before any
later renderer touches ``text.md`` (the shared collage pass below
preserves it; we leave a defensive comment in case future renderers
get reordered).
"""

from __future__ import annotations

import logging
from pathlib import Path

from ._types import Manifest, PageImage, RenderOptions
from .render.pptx import extract_pptx_text, render_pptx_via_libreoffice

logger = logging.getLogger(__name__)


def render(
    src: Path,
    out_dir: Path,
    opts: RenderOptions,
    manifest: Manifest,
) -> None:
    try:
        pptx_bytes = src.read_bytes()
    except Exception as exc:
        manifest.warnings.append(f"failed to read pptx: {exc}")
        return

    text, slide_titles, total_slides = extract_pptx_text(pptx_bytes)
    if total_slides == 0 and not text:
        manifest.warnings.append("pptx parse produced no slides or text")

    manifest.page_count = total_slides
    manifest.summary["slide_count"] = total_slides
    manifest.summary["slide_titles"] = slide_titles[: opts.max_pages]

    # Write the PPTX-specific text BEFORE any LibreOffice→PDF roundtrip
    # so a later renderer cannot accidentally clobber text.md.
    if text:
        text_path = out_dir / "text.md"
        text_path.write_text(text, encoding="utf-8")
        manifest.text_relpath = "text.md"
        manifest.extracted_text_chars = len(text)

    if not opts.text_only:
        pages_dir = out_dir / "pages"
        pages_dir.mkdir(exist_ok=True)
        page_images, err = render_pptx_via_libreoffice(
            pptx_bytes, max_pages=opts.max_pages, soffice_path=opts.soffice,
        )
        if err:
            manifest.warnings.append(f"pptx render: {err}")
        for pi in page_images:
            png_path = pages_dir / f"p{pi.page:03}.png"
            try:
                png_path.write_bytes(pi.png_bytes)
            except Exception as exc:
                manifest.warnings.append(
                    f"pptx page {pi.page} write failed: {exc}",
                )
                continue
            manifest.pages.append(PageImage(
                page=pi.page,
                relpath=str(png_path.relative_to(out_dir)),
                size_bytes=png_path.stat().st_size,
                width=pi.width,
                height=pi.height,
            ))
        manifest.rendered_page_count = len(manifest.pages)
