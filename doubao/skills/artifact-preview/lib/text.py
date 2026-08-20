"""Text/markdown/json renderer.

Plain text gets copied to ``text.md`` verbatim. No images. Used for
``.txt`` / ``.md`` / ``.json`` / ``.csv`` / ``.yaml`` / etc.
"""

from __future__ import annotations

import logging
from pathlib import Path

from ._types import Manifest, RenderOptions

logger = logging.getLogger(__name__)

_MAX_TEXT_BYTES = 5 * 1024 * 1024


def render(
    src: Path,
    out_dir: Path,
    opts: RenderOptions,  # noqa: ARG001 — options reserved for future caps
    manifest: Manifest,
) -> None:
    size = src.stat().st_size
    text_path = out_dir / "text.md"
    if size > _MAX_TEXT_BYTES:
        with open(src, "rb") as fh:
            data = fh.read(_MAX_TEXT_BYTES)
        try:
            content = data.decode("utf-8", errors="replace")
        except Exception:
            content = data.decode("latin-1", errors="replace")
        content += f"\n...[truncated at {_MAX_TEXT_BYTES} bytes; full size {size}]\n"
        manifest.warnings.append(f"text truncated at {_MAX_TEXT_BYTES} bytes")
    else:
        with open(src, encoding="utf-8", errors="replace") as fh:
            content = fh.read()
    text_path.write_text(content, encoding="utf-8")
    manifest.text_relpath = "text.md"
    manifest.extracted_text_chars = len(content)
    manifest.summary["bytes"] = size
    manifest.summary["lines"] = content.count("\n") + (0 if content.endswith("\n") else 1)
