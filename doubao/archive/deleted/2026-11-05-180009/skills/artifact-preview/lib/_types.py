"""Shared dataclasses + enum constants for the artifact-preview manifest.

The classes here are the source of truth for the on-disk
``manifest.json`` schema. Any change here must keep
:func:`manifest.write_manifest` / :func:`manifest.load_manifest` in sync.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# File kind discriminators — used by the dispatcher to choose a renderer.
KIND_PDF = "pdf"
KIND_PPTX = "pptx"
KIND_DOCX = "docx"
KIND_XLSX = "xlsx"
KIND_HTML = "html"
KIND_IMAGE = "image"
KIND_TEXT = "text"
KIND_ZIP = "zip"
KIND_UNKNOWN = "unknown"


@dataclass
class RenderOptions:
    """Render-time options. Mirrors CLI flags 1:1.

    Attributes:
        max_pages: cap on rendered pages/slides per source.
        collage: when True, tile multi-page output into composite JPEGs.
        page_range: optional 1-indexed selector like "1-5,10". When set,
            ``max_pages`` is applied AFTER range filtering.
        thumbnail: when True, also emit a single-image overview file.
        text_only: skip image rendering; still extract text + manifest. Images
            an earlier full render already produced are kept, not deleted.
        force: when True, ignore cached output dir and re-render.
        jpeg_quality: collage JPEG quality (1-95).
        out_max_dim: longest pixel side of any output image.
        soffice: explicit LibreOffice binary path (pptx screenshots). None means
            look it up on PATH and at the platform's standard install locations.
        chromium: explicit Chromium-family browser path (html screenshots).
    """

    max_pages: int = 12
    collage: bool = True
    page_range: str | None = None
    thumbnail: bool = True
    text_only: bool = False
    force: bool = False
    jpeg_quality: int = 85
    out_max_dim: int = 2048
    soffice: str | None = None
    chromium: str | None = None


@dataclass
class PageImage:
    """A single rendered page/slide image saved to disk.

    ``relpath`` is relative to the manifest's output directory.
    """

    page: int
    relpath: str
    size_bytes: int
    width: int = 0
    height: int = 0


@dataclass
class CollageEntry:
    """A composite image tiling several consecutive pages."""

    relpath: str
    covers_pages: list[int]
    grid_cols: int
    grid_rows: int
    size_bytes: int


@dataclass
class Manifest:
    """The output manifest.json schema.

    Models read this first to learn what's available before deciding which
    images / text files to ``Read``.
    """

    schema_version: str = "1"
    source_path: str = ""
    source_filename: str = ""
    source_hash: str = ""
    source_size_bytes: int = 0
    kind: str = KIND_UNKNOWN
    rendered_at_utc: str = ""
    output_dir: str = ""

    # Counts (cheap sanity check for the model before scanning files lists)
    page_count: int = 0
    rendered_page_count: int = 0
    collage_count: int = 0
    extracted_text_chars: int = 0

    # File handles (relative to output_dir)
    text_relpath: str | None = None
    thumbnail_relpath: str | None = None
    pages: list[PageImage] = field(default_factory=list)
    collages: list[CollageEntry] = field(default_factory=list)

    # Render-time diagnostics (model uses to interpret the output)
    warnings: list[str] = field(default_factory=list)
    options: dict[str, Any] = field(default_factory=dict)

    # Best-effort kind-specific summary (e.g. sheet names, slide titles).
    # Free-form so each renderer can populate what's natural for that format.
    summary: dict[str, Any] = field(default_factory=dict)
