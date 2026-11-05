"""ZIP renderer — list contents into ``text.md``.

Just lists entries. We deliberately don't recurse-render: a zip can
contain arbitrary file types and rendering each one would explode
preview cost. The model can extract & call ``preview render`` on
individual files of interest.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

from ._types import Manifest, RenderOptions


def render(
    src: Path,
    out_dir: Path,
    opts: RenderOptions,  # noqa: ARG001
    manifest: Manifest,
) -> None:
    try:
        with zipfile.ZipFile(src) as zf:
            entries = zf.infolist()
    except zipfile.BadZipFile as exc:
        manifest.warnings.append(f"bad zip: {exc}")
        return

    lines = [f"# {src.name}", f"total entries: {len(entries)}", ""]
    total_uncompressed = 0
    for info in entries:
        size = info.file_size
        total_uncompressed += size
        kind = "DIR " if info.is_dir() else "FILE"
        lines.append(f"{kind}\t{size:>12} bytes\t{info.filename}")
    lines.append("")
    lines.append(f"total uncompressed size: {total_uncompressed} bytes")

    content = "\n".join(lines)
    text_path = out_dir / "text.md"
    text_path.write_text(content, encoding="utf-8")
    manifest.text_relpath = "text.md"
    manifest.extracted_text_chars = len(content)
    manifest.summary["entry_count"] = len(entries)
    manifest.summary["total_uncompressed_bytes"] = total_uncompressed
