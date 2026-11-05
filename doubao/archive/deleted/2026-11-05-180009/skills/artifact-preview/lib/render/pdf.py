"""PDF text + per-page PNG extraction via PyMuPDF."""

from __future__ import annotations

import logging
from typing import Sequence

from .constants import DEFAULT_MAX_PAGES_RENDER, DEFAULT_PDF_DPI
from .types import PageImage

logger = logging.getLogger(__name__)


def extract_pdf(
    pdf_bytes: bytes,
    *,
    dpi: int = DEFAULT_PDF_DPI,
    max_pages: int = DEFAULT_MAX_PAGES_RENDER,
    page_indices: Sequence[int] | None = None,
    render_images: bool = True,
) -> tuple[str, list[PageImage], int]:
    """Extract text + (optionally) per-page PNG screenshots from PDF bytes.

    Parameters
    ----------
    pdf_bytes
        Raw PDF byte string.
    dpi
        Render resolution. 150 dpi yields ~1500x1125 PNGs for A4 pages —
        a good balance of legibility vs prompt-token cost when fed to a
        multimodal LLM.
    max_pages
        Cap on the number of pages rendered (when ``page_indices`` is
        None) and on the number of indices honored (when it is set).
    page_indices
        Optional explicit 1-indexed page list. When provided,
        ``max_pages`` is applied AFTER filtering. Out-of-range values
        are silently skipped.
    render_images
        When False, only text is extracted; the returned page list is
        empty. Useful for ``--text-only`` callers that don't need the
        PIL/PyMuPDF image roundtrip cost.

    Returns
    -------
    (text, pages, total_pages)
        ``text`` is per-page concatenation with ``--- Page N/total ---``
        headers. ``pages`` is the list of :class:`PageImage`. Empty +
        empty + ``0`` if PyMuPDF is missing or the bytes won't parse —
        callers should handle the degraded case explicitly.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.warning("PyMuPDF (fitz) not installed — pdf extract skipped")
        return "", [], 0

    text_parts: list[str] = []
    pages: list[PageImage] = []

    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:
        logger.warning("[pdf] open failed: %s", exc)
        return "", [], 0

    try:
        total_pages = len(doc)

        if page_indices is None:
            selected = list(range(1, min(total_pages, max_pages) + 1))
        else:
            seen: set[int] = set()
            selected = []
            for p in page_indices:
                if 1 <= p <= total_pages and p not in seen:
                    seen.add(p)
                    selected.append(p)
                if len(selected) >= max_pages:
                    break

        for page_no in selected:
            page = doc.load_page(page_no - 1)
            page_text = page.get_text()
            if page_text.strip():
                text_parts.append(
                    f"--- Page {page_no}/{total_pages} ---\n{page_text.strip()}"
                )
            if not render_images:
                continue
            try:
                mat = fitz.Matrix(dpi / 72, dpi / 72)
                pix = page.get_pixmap(matrix=mat)
                pages.append(PageImage(
                    page=page_no,
                    png_bytes=pix.tobytes("png"),
                    width=pix.width,
                    height=pix.height,
                ))
            except Exception as exc:
                logger.debug("[pdf] page %d render failed: %s", page_no, exc)
    finally:
        try:
            doc.close()
        except Exception:
            pass

    return "\n\n".join(text_parts), pages, total_pages
