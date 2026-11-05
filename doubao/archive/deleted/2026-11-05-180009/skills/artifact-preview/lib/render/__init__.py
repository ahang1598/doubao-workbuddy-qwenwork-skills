"""Pure rendering primitives — no IO.

Single source of truth for document → text + per-page PNG + collage
rendering. Used by:

* ``bin/preview`` (this hub's CLI; runs inside the rollout VM)
* ``swalm.core.utils.artifact_render`` (host side, re-exports from here
  via ``import superskill.hub_skills.artifact_preview.lib.render`` so the
  trace_llm_judge keeps working without code duplication)

All third-party deps (``fitz`` / ``pptx`` / ``docx`` / ``openpyxl`` /
``PIL``) are lazily imported via :func:`lib._common.lazy_import` —
missing packages surface as ``DEP_MISSING`` JSON errors so the model
can ``pip install`` and retry.

System deps (LibreOffice for PPTX rendering, the system
``chromium-browser`` binary for HTML rendering) are detected at call
time and degrade to empty page lists + ``warnings`` rather than
raising. Note: HTML rendering no longer goes through Playwright —
we drive headless Chromium directly via its CLI ``--screenshot``
flag (see :mod:`.html`).
"""

from __future__ import annotations

from .collage import (
    build_collages,
    compose_collage,
    draw_cell_label,
    letterbox_cell,
    pick_grid,
)
from .constants import (
    DEFAULT_HTML_VIEWPORT_HEIGHT,
    DEFAULT_HTML_VIEWPORT_WIDTH,
    DEFAULT_LIBREOFFICE_TIMEOUT_SEC,
    DEFAULT_MAX_PAGES_RENDER,
    DEFAULT_MAX_PER_TILE,
    DEFAULT_MIN_GROUP_SIZE,
    DEFAULT_OUT_ASPECT_MAX,
    DEFAULT_OUT_ASPECT_MIN,
    DEFAULT_OUT_MAX_DIM,
    DEFAULT_PDF_DPI,
)
from .docx import extract_docx_text
from .html import render_html_screenshots
from .pdf import extract_pdf
from .pptx import (
    extract_pptx_text,
    find_libreoffice_binary,
    render_pptx_via_libreoffice,
)
from .types import CollageResult, PageImage
from .xlsx import extract_xlsx_text

__all__ = [
    "DEFAULT_HTML_VIEWPORT_HEIGHT",
    "DEFAULT_HTML_VIEWPORT_WIDTH",
    "DEFAULT_LIBREOFFICE_TIMEOUT_SEC",
    "DEFAULT_MAX_PAGES_RENDER",
    "DEFAULT_MAX_PER_TILE",
    "DEFAULT_MIN_GROUP_SIZE",
    "DEFAULT_OUT_ASPECT_MAX",
    "DEFAULT_OUT_ASPECT_MIN",
    "DEFAULT_OUT_MAX_DIM",
    "DEFAULT_PDF_DPI",
    "CollageResult",
    "PageImage",
    "build_collages",
    "compose_collage",
    "draw_cell_label",
    "extract_docx_text",
    "extract_pdf",
    "extract_pptx_text",
    "extract_xlsx_text",
    "find_libreoffice_binary",
    "letterbox_cell",
    "pick_grid",
    "render_html_screenshots",
    "render_pptx_via_libreoffice",
]
