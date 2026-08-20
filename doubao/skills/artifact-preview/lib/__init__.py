"""artifact-preview hub library.

Public surface (reachable as ``from lib import ...`` once
``bin/preview`` adds the hub root to ``sys.path``):

* :class:`_types.Manifest` / :class:`_types.RenderOptions` etc — the
  on-disk manifest schema models.
* :func:`dispatch.render` / :func:`dispatch.detect_kind` — the public
  entrypoint used by both the CLI and any external Python consumer.
* :mod:`render` — pure rendering primitives (text + per-page PNG +
  collage) shared with ``swalm.core.utils.artifact_render`` on the host
  side via re-export.
"""

from . import render  # re-export sub-package for ``from lib import render``
from ._common import (
    ArtifactPreviewError,
    ErrCode,
    emit,
    err,
    lazy_import,
    ok,
)
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
    CollageEntry,
    Manifest,
    PageImage,
    RenderOptions,
)
from .cache import compute_source_hash, default_output_root, resolve_output_dir
from .dispatch import detect_kind, parse_page_range, render as dispatch_render
from .manifest import load_manifest, write_manifest

__all__ = [
    "ArtifactPreviewError",
    "CollageEntry",
    "ErrCode",
    "KIND_DOCX",
    "KIND_HTML",
    "KIND_IMAGE",
    "KIND_PDF",
    "KIND_PPTX",
    "KIND_TEXT",
    "KIND_UNKNOWN",
    "KIND_XLSX",
    "KIND_ZIP",
    "Manifest",
    "PageImage",
    "RenderOptions",
    "compute_source_hash",
    "default_output_root",
    "detect_kind",
    "dispatch_render",
    "emit",
    "err",
    "lazy_import",
    "load_manifest",
    "ok",
    "parse_page_range",
    "render",
    "resolve_output_dir",
    "write_manifest",
]

__version__ = "0.1.0"
