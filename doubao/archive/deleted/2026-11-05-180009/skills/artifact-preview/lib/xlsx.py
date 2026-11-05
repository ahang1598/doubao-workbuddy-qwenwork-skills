"""XLSX wrapper — IO + manifest layer over :mod:`render.xlsx`.

No screenshots for xlsx (matches legacy trace_llm_judge behavior). All
sheets are dumped to a single ``text.md`` and the per-sheet summary is
recorded in ``manifest.summary``.
"""

from __future__ import annotations

import logging
from pathlib import Path

from ._types import Manifest, RenderOptions
from .render.xlsx import extract_xlsx_text

logger = logging.getLogger(__name__)


def render(
    src: Path,
    out_dir: Path,
    opts: RenderOptions,  # noqa: ARG001 -- text-only renderer ignores opts
    manifest: Manifest,
) -> None:
    try:
        xlsx_bytes = src.read_bytes()
    except Exception as exc:
        manifest.warnings.append(f"failed to read xlsx: {exc}")
        return

    text, sheets = extract_xlsx_text(xlsx_bytes)
    manifest.summary["sheets"] = sheets
    manifest.summary["sheet_count"] = len(sheets)
    if not text:
        manifest.warnings.append("xlsx parse produced no text")
        return

    text_path = out_dir / "text.md"
    text_path.write_text(text, encoding="utf-8")
    manifest.text_relpath = "text.md"
    manifest.extracted_text_chars = len(text)
