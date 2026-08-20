"""Manifest read/write.

The on-disk format is JSON with the schema defined by :class:`Manifest`
in :mod:`._types`. We keep dump/load codepaths trivial so the manifest
stays human-readable / model-readable.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

from ._types import CollageEntry, Manifest, PageImage


def _manifest_to_dict(m: Manifest) -> dict[str, Any]:
    """Serialize Manifest dataclass to a dict suitable for json.dump.

    Uses ``dataclasses.asdict`` for nested dataclasses; explicitly drops
    no fields (we keep ``text_relpath``/``thumbnail_relpath`` as ``null``
    so the model can detect "render attempted but produced no text"
    without having to inspect ``warnings``).
    """
    return {
        "schema_version": m.schema_version,
        "source_path": m.source_path,
        "source_filename": m.source_filename,
        "source_hash": m.source_hash,
        "source_size_bytes": m.source_size_bytes,
        "kind": m.kind,
        "rendered_at_utc": m.rendered_at_utc,
        "output_dir": m.output_dir,
        "page_count": m.page_count,
        "rendered_page_count": m.rendered_page_count,
        "collage_count": m.collage_count,
        "extracted_text_chars": m.extracted_text_chars,
        "text_relpath": m.text_relpath,
        "thumbnail_relpath": m.thumbnail_relpath,
        "pages": [dataclasses.asdict(p) for p in m.pages],
        "collages": [dataclasses.asdict(c) for c in m.collages],
        "warnings": list(m.warnings),
        "options": dict(m.options),
        "summary": dict(m.summary),
    }


def write_manifest(m: Manifest, output_dir: str | Path) -> Path:
    """Write manifest.json into ``output_dir`` and return the file path.

    Creates the directory if missing.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "manifest.json"
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(_manifest_to_dict(m), fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return path


def load_manifest(output_dir: str | Path) -> Manifest:
    """Load manifest.json from ``output_dir``.

    Raises FileNotFoundError if the manifest is missing. Unknown fields
    are silently dropped; missing fields fall back to dataclass defaults.
    """
    path = Path(output_dir) / "manifest.json"
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    m = Manifest()
    for k, v in data.items():
        if not hasattr(m, k):
            continue
        if k == "pages":
            m.pages = [PageImage(**d) for d in v]
        elif k == "collages":
            m.collages = [CollageEntry(**d) for d in v]
        else:
            setattr(m, k, v)
    return m
