"""Collage + thumbnail wrapper — IO + manifest layer over
:mod:`render.collage`.

The shared library returns :class:`render.types.CollageResult` (PIL
images + metadata); this module is responsible for:

* loading per-page PNGs from disk into PIL,
* invoking ``build_collages`` from the shared lib,
* writing each result as a JPEG and recording a
  :class:`CollageEntry` in the manifest.

Thumbnail logic stays here (single-page utility, not worth a shared
helper — it's just ``Image.thumbnail``).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from ._types import CollageEntry, Manifest, RenderOptions
from .render.collage import build_collages as _shared_build
from .render.constants import DEFAULT_MAX_PER_TILE, DEFAULT_MIN_GROUP_SIZE

logger = logging.getLogger(__name__)

_THUMBNAIL_MAX_DIM = 768


def build_collages(
    out_dir: Path,
    manifest: Manifest,
    opts: RenderOptions,
) -> None:
    """Load page PNGs, tile them via the shared lib, write JPEG collages."""
    try:
        from PIL import Image as PILImage
    except Exception as exc:
        manifest.warnings.append(f"Pillow unavailable: {exc}")
        return

    pages = list(manifest.pages)
    if len(pages) < DEFAULT_MIN_GROUP_SIZE:
        return

    items: list[tuple[str, str, Any]] = []
    for p in pages:
        try:
            im = PILImage.open(out_dir / p.relpath)
            im.load()
            if im.mode != "RGB":
                im = im.convert("RGB")
        except Exception as exc:
            manifest.warnings.append(f"collage load {p.relpath} failed: {exc}")
            continue
        # All pages from one source share the same group key — the skill
        # always renders one source per output dir.
        items.append(("source", f"p{p.page}", im))

    if not items:
        return

    results = _shared_build(
        items,
        min_group=DEFAULT_MIN_GROUP_SIZE,
        max_per_tile=DEFAULT_MAX_PER_TILE,
        out_max_dim=opts.out_max_dim,
    )
    if not results:
        return

    collages_dir = out_dir / "collages"
    collages_dir.mkdir(exist_ok=True)
    for ci, res in enumerate(results, start=1):
        out_path = collages_dir / f"c{ci}.jpg"
        try:
            res.image.save(
                out_path,
                format="JPEG",
                quality=opts.jpeg_quality,
                optimize=True,
            )
        except Exception as exc:
            manifest.warnings.append(f"collage {ci} save failed: {exc}")
            continue
        # Map labels like "p3" back to ints for ``covers_pages``.
        covers: list[int] = []
        for lbl in res.cell_labels:
            if lbl.startswith("p") and lbl[1:].isdigit():
                covers.append(int(lbl[1:]))
        manifest.collages.append(CollageEntry(
            relpath=str(out_path.relative_to(out_dir)),
            covers_pages=covers,
            grid_cols=res.cols,
            grid_rows=res.rows,
            size_bytes=out_path.stat().st_size,
        ))

    manifest.collage_count = len(manifest.collages)

    # A page that never made it into a collage would be invisible to a model
    # following the documented "thumbnail, then collages" reading order, so say
    # so explicitly rather than letting collage_count imply full coverage.
    covered = {pg for entry in manifest.collages for pg in entry.covers_pages}
    uncovered = [p.page for p in pages if p.page not in covered]
    if uncovered:
        shown = ", ".join(f"pages/{p.relpath.split('/')[-1]}"
                          for p in pages if p.page in set(uncovered))
        manifest.warnings.append(
            f"pages not included in any collage: {uncovered} — Read them "
            f"directly: {shown}"
        )


def make_thumbnail(
    out_dir: Path,
    manifest: Manifest,
    opts: RenderOptions,
) -> None:
    """Save a small JPEG thumbnail = first rendered page, downscaled.

    Sets ``manifest.thumbnail_relpath`` on success.
    """
    if not manifest.pages:
        return
    try:
        from PIL import Image as PILImage
    except Exception:
        manifest.warnings.append("Pillow unavailable for thumbnail")
        return

    first = manifest.pages[0]
    src = out_dir / first.relpath
    try:
        with PILImage.open(src) as im:
            im = im.convert("RGB")
            im.thumbnail((_THUMBNAIL_MAX_DIM, _THUMBNAIL_MAX_DIM), PILImage.LANCZOS)
            out = out_dir / "thumb.jpg"
            im.save(out, format="JPEG", quality=max(70, min(opts.jpeg_quality, 90)))
        manifest.thumbnail_relpath = "thumb.jpg"
    except Exception as exc:
        manifest.warnings.append(f"thumbnail failed: {exc}")
