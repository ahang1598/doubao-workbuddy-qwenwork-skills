"""Plain-image renderer.

For PNG/JPG/etc inputs the "rendering" is just copying the file as the
single page image. We still produce a thumbnail so the model can preview
it without loading the full image into context.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from ._types import Manifest, PageImage, RenderOptions

logger = logging.getLogger(__name__)


def render(
    src: Path,
    out_dir: Path,
    opts: RenderOptions,  # noqa: ARG001 — collage/thumbnail use opts via dispatcher
    manifest: Manifest,
) -> None:
    pages_dir = out_dir / "pages"
    pages_dir.mkdir(exist_ok=True)
    dest_name = "p001" + src.suffix.lower()
    dest = pages_dir / dest_name
    shutil.copy2(src, dest)

    width = height = 0
    try:
        from PIL import Image as PILImage

        with PILImage.open(dest) as im:
            width, height = im.size
    except Exception as exc:
        logger.warning("[image] PIL probe failed: %s", exc)
        manifest.warnings.append(f"image probe failed: {exc}")

    page = PageImage(
        page=1,
        relpath=str(dest.relative_to(out_dir)),
        size_bytes=dest.stat().st_size,
        width=width,
        height=height,
    )
    manifest.pages.append(page)
    manifest.page_count = 1
    manifest.rendered_page_count = 1
    manifest.summary["dimensions"] = f"{width}x{height}" if width else "unknown"
