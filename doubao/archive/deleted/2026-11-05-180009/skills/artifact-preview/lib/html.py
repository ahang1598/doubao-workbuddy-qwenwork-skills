"""HTML wrapper — IO + manifest layer over :mod:`render.html`.

Always copies the raw HTML source to ``text.md`` (so the model can read
it even when Playwright is missing). When screenshots are enabled, the
shared library does the rendering and we write the resulting PNGs to
``out_dir/pages/``.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from ._types import Manifest, PageImage, RenderOptions
from .render.html import render_html_screenshots

logger = logging.getLogger(__name__)


def render(
    src: Path,
    out_dir: Path,
    opts: RenderOptions,
    manifest: Manifest,
) -> None:
    raw = src.read_text(encoding="utf-8", errors="replace")
    text_path = out_dir / "text.md"
    text_path.write_text(raw, encoding="utf-8")
    manifest.text_relpath = "text.md"
    manifest.extracted_text_chars = len(raw)
    manifest.summary["bytes"] = src.stat().st_size

    if opts.text_only:
        return

    pages_dir = out_dir / "pages"
    pages_dir.mkdir(exist_ok=True)

    # Hand the browser the HTML text rather than a URL built from src: the
    # renderer stages it in its own temp dir and derives the URL with
    # Path.as_uri(), which escapes spaces and non-ASCII characters and produces
    # a valid URL on every platform.
    pages, err = asyncio.run(render_html_screenshots(
        html_text=raw,
        max_pages=opts.max_pages,
        browser_path=opts.chromium,
    ))
    if err:
        manifest.warnings.append(f"html render: {err}")

    for pi in pages:
        png_path = pages_dir / f"p{pi.page:03}.png"
        try:
            png_path.write_bytes(pi.png_bytes)
        except Exception as exc:
            manifest.warnings.append(f"html page {pi.page} write failed: {exc}")
            continue
        manifest.pages.append(PageImage(
            page=pi.page,
            relpath=str(png_path.relative_to(out_dir)),
            size_bytes=png_path.stat().st_size,
            width=pi.width,
            height=pi.height,
        ))
    manifest.page_count = len(manifest.pages) or 1
    manifest.rendered_page_count = len(manifest.pages)
