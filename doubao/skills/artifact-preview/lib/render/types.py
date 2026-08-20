"""Plain dataclasses returned by the rendering primitives.

Frozen dataclasses (instead of NamedTuples) so consumers can pattern
match by attribute name and we can add fields without breaking call
sites.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PageImage:
    """One rendered page from a multi-page document.

    ``png_bytes`` is the raw PNG; downstream callers (skill / judge)
    decide whether to write to disk or base64-encode for an LLM prompt.
    ``width`` / ``height`` are derived at render time so callers don't
    have to re-decode the bytes just to compute aspect ratio.
    """

    page: int
    png_bytes: bytes
    width: int = 0
    height: int = 0


@dataclass
class CollageResult:
    """One JPEG collage built from N consecutive pages.

    ``image`` is a PIL Image (RGB). Callers render to bytes (with their
    own JPEG-quality choice) or save to disk. The metadata fields let
    the caller emit a manifest entry without re-deriving anything.
    """

    image: Any  # PIL.Image.Image, but we don't import PIL at module load
    cols: int
    rows: int
    cell_labels: list[str] = field(default_factory=list)
    source_indices: list[int] = field(default_factory=list)
