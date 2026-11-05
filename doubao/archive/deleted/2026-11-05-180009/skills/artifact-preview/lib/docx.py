"""DOCX wrapper — IO + manifest layer over :mod:`render.docx`.

No image rendering for docx (matches legacy trace_llm_judge behavior).
All work is text extraction; we only write ``text.md`` and update
manifest summary.
"""

from __future__ import annotations

import logging
from pathlib import Path

from ._types import Manifest, RenderOptions
from .render.docx import extract_docx_text

logger = logging.getLogger(__name__)


def render(
    src: Path,
    out_dir: Path,
    opts: RenderOptions,  # noqa: ARG001 -- text-only renderer ignores opts
    manifest: Manifest,
) -> None:
    try:
        docx_bytes = src.read_bytes()
    except Exception as exc:
        manifest.warnings.append(f"failed to read docx: {exc}")
        return

    text, summary = extract_docx_text(docx_bytes)
    manifest.summary.update(summary)
    if not text:
        manifest.warnings.append("docx parse produced no text")
        return

    text_path = out_dir / "text.md"
    text_path.write_text(text, encoding="utf-8")
    manifest.text_relpath = "text.md"
    manifest.extracted_text_chars = len(text)
