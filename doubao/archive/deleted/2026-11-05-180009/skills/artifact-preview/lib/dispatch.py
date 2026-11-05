"""File-kind detection and render dispatch.

This module is the public entrypoint imported by both the CLI and any
external Python caller. :func:`render` is the only top-level function
the rest of the codebase should depend on.
"""

from __future__ import annotations

import datetime
import logging
import shutil
from pathlib import Path

from . import _common
from ._types import (
    KIND_DOCX,
    KIND_HTML,
    KIND_IMAGE,
    KIND_PDF,
    KIND_PPTX,
    KIND_TEXT,
    KIND_UNKNOWN,
    KIND_XLSX,
    KIND_ZIP,
    Manifest,
    RenderOptions,
)
from .cache import resolve_output_dir
from .manifest import load_manifest, write_manifest

logger = logging.getLogger(__name__)


# Filename-suffix → kind mapping. Mirrors trace_llm_judge._category_from_suffix
# but is the canonical version for this skill.
_SUFFIX_TO_KIND: dict[str, str] = {
    ".pdf": KIND_PDF,
    ".pptx": KIND_PPTX,
    ".ppt": KIND_PPTX,
    ".docx": KIND_DOCX,
    ".doc": KIND_DOCX,
    ".xlsx": KIND_XLSX,
    ".xlsm": KIND_XLSX,
    ".xls": KIND_XLSX,
    ".html": KIND_HTML,
    ".htm": KIND_HTML,
    ".png": KIND_IMAGE,
    ".jpg": KIND_IMAGE,
    ".jpeg": KIND_IMAGE,
    ".webp": KIND_IMAGE,
    ".gif": KIND_IMAGE,
    ".bmp": KIND_IMAGE,
    ".txt": KIND_TEXT,
    ".md": KIND_TEXT,
    ".markdown": KIND_TEXT,
    ".json": KIND_TEXT,
    ".jsonl": KIND_TEXT,
    ".yaml": KIND_TEXT,
    ".yml": KIND_TEXT,
    ".csv": KIND_TEXT,
    ".tsv": KIND_TEXT,
    ".log": KIND_TEXT,
    ".zip": KIND_ZIP,
}


def detect_kind(path: str | Path) -> str:
    """Detect file kind from the filename suffix only.

    We deliberately do not sniff file headers — the workspace is trusted
    and suffix-based dispatch is sufficient for our deliverable types.
    Unknown extensions return :data:`KIND_UNKNOWN`.
    """
    suf = Path(path).suffix.lower()
    return _SUFFIX_TO_KIND.get(suf, KIND_UNKNOWN)


def parse_page_range(spec: str | None, max_value: int) -> list[int] | None:
    """Parse a 1-indexed page-range spec like ``"1-5,10"``.

    Returns a sorted, deduplicated list of valid page numbers in
    ``[1, max_value]``. Returns None when ``spec`` is None / empty
    (caller interprets None as "all pages up to max_pages cap").

    Invalid tokens are silently dropped.
    """
    if not spec:
        return None
    pages: set[int] = set()
    for token in spec.split(","):
        t = token.strip()
        if not t:
            continue
        if "-" in t:
            try:
                lo_str, hi_str = t.split("-", 1)
                lo, hi = int(lo_str), int(hi_str)
            except ValueError:
                continue
            if lo > hi:
                lo, hi = hi, lo
            for p in range(max(1, lo), min(max_value, hi) + 1):
                pages.add(p)
        else:
            try:
                p = int(t)
            except ValueError:
                continue
            if 1 <= p <= max_value:
                pages.add(p)
    return sorted(pages) if pages else None


def render(
    input_path: str | Path,
    output_root: str | Path | None = None,
    options: RenderOptions | None = None,
) -> Manifest:
    """Render ``input_path`` to a deterministic output directory.

    Returns the resulting Manifest. When the cached output already
    exists and ``options.force=False`` the manifest is loaded from disk
    and returned without re-rendering.
    """
    opts = options or RenderOptions()
    # logical_abspath, not resolve(): resolve() collapses the workspace symlink
    # and the sandbox bind mount, which would report paths under a prefix the
    # caller never used.
    src = Path(_common.logical_abspath(input_path))
    if not src.is_file():
        raise FileNotFoundError(f"not a file: {src}")

    out_dir, source_hash = resolve_output_dir(src, output_root)

    cached_manifest = out_dir / "manifest.json"
    previous: Manifest | None = None
    if cached_manifest.exists():
        try:
            previous = load_manifest(out_dir)
        except Exception as exc:  # noqa: BLE001 - a corrupt cache just re-renders
            logger.warning("[cache] manifest load failed, re-rendering: %s", exc)
            previous = None

    if previous is not None and not opts.force:
        cached_opts = previous.options
        same_options = all(
            cached_opts.get(k) == getattr(opts, k)
            for k in ("max_pages", "collage", "page_range", "thumbnail",
                      "text_only", "jpeg_quality", "out_max_dim")
        )
        if same_options:
            logger.info("[cache] hit: %s", out_dir)
            return previous

    # A text-only render must not throw away images an earlier full render
    # produced: the caller asked to skip *work*, not to delete results.
    keep_images = bool(
        opts.text_only and previous is not None
        and (previous.pages or previous.collages or previous.thumbnail_relpath)
    )
    if out_dir.exists() and not keep_images:
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    kind = detect_kind(src)
    manifest = Manifest(
        schema_version="1",
        source_path=str(src),
        source_filename=src.name,
        source_hash=source_hash,
        source_size_bytes=src.stat().st_size,
        kind=kind,
        rendered_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        output_dir=str(out_dir),
        options={
            "max_pages": opts.max_pages,
            "collage": opts.collage,
            "page_range": opts.page_range,
            "thumbnail": opts.thumbnail,
            "text_only": opts.text_only,
            "jpeg_quality": opts.jpeg_quality,
            "out_max_dim": opts.out_max_dim,
        },
    )

    if keep_images and previous is not None:
        # Carry the existing image set forward so `info` and a later plain
        # `render` still see it.
        manifest.pages = list(previous.pages)
        manifest.collages = list(previous.collages)
        manifest.thumbnail_relpath = previous.thumbnail_relpath
        manifest.rendered_page_count = previous.rendered_page_count
        manifest.collage_count = previous.collage_count
        manifest.warnings.append(
            f"text-only render kept {len(previous.pages)} page image(s) and "
            f"{len(previous.collages)} collage(s) from an earlier full render"
        )

    if kind == KIND_UNKNOWN:
        manifest.warnings.append(f"unknown extension: {src.suffix}")
        write_manifest(manifest, out_dir)
        return manifest

    # Lazy-import format renderers so missing optional deps only fail when the
    # specific format is requested. (Each wrapper itself further lazy-imports
    # third-party libs via ``render.<kind>`` shared primitives.)
    if kind == KIND_PDF:
        from . import pdf as renderer
    elif kind == KIND_PPTX:
        from . import pptx as renderer
    elif kind == KIND_DOCX:
        from . import docx as renderer
    elif kind == KIND_XLSX:
        from . import xlsx as renderer
    elif kind == KIND_HTML:
        from . import html as renderer
    elif kind == KIND_IMAGE:
        from . import image as renderer
    elif kind == KIND_TEXT:
        from . import text as renderer
    elif kind == KIND_ZIP:
        from . import zip_ as renderer
    else:
        manifest.warnings.append(f"no renderer for kind={kind}")
        write_manifest(manifest, out_dir)
        return manifest

    try:
        renderer.render(src, out_dir, opts, manifest)
    except Exception as exc:
        logger.exception("[render] %s failed", kind)
        manifest.warnings.append(f"renderer failed: {type(exc).__name__}: {exc}")

    if opts.thumbnail and not manifest.thumbnail_relpath:
        try:
            from .collage import make_thumbnail

            make_thumbnail(out_dir, manifest, opts)
        except Exception as exc:
            logger.warning("[thumbnail] failed: %s", exc)
            manifest.warnings.append(f"thumbnail failed: {exc}")

    if opts.collage and not manifest.collages and manifest.pages:
        try:
            from .collage import build_collages

            build_collages(out_dir, manifest, opts)
        except Exception as exc:
            logger.warning("[collage] failed: %s", exc)
            manifest.warnings.append(f"collage failed: {exc}")

    write_manifest(manifest, out_dir)
    return manifest


__all__ = ["detect_kind", "parse_page_range", "render"]
