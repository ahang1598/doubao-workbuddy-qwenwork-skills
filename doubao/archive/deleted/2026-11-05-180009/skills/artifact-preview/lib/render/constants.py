"""Shared default constants for the render package.

These mirror the legacy values from ``trace_llm_judge.py`` so behavior is
preserved 1:1 after migration. Callers are free to override on a
per-call basis via keyword arguments — the defaults exist purely to
avoid magic numbers in the consumer code.
"""

from __future__ import annotations

DEFAULT_PDF_DPI = 150

# Page-count cap for any per-page renderer (PDF / PPTX-via-LO / HTML
# segment). 12-15 is roughly where a long-doc judge starts losing
# context-window value per extra page.
DEFAULT_MAX_PAGES_RENDER = 15

# LibreOffice headless conversion timeout. PPT decks > 50 MB or with many
# embedded images can take ~60 s legitimately, so 180 s is a generous cap
# that still bounds total render time.
DEFAULT_LIBREOFFICE_TIMEOUT_SEC = 180.0

DEFAULT_HTML_VIEWPORT_WIDTH = 1280
DEFAULT_HTML_VIEWPORT_HEIGHT = 800

DEFAULT_MIN_GROUP_SIZE = 2
DEFAULT_MAX_PER_TILE = 9
DEFAULT_OUT_MAX_DIM = 2048
DEFAULT_OUT_ASPECT_MIN = 0.5
DEFAULT_OUT_ASPECT_MAX = 2.0
DEFAULT_JPEG_QUALITY = 85
DEFAULT_CELL_MARGIN = 6
DEFAULT_LABEL_FONT_SIZE = 18

# Candidate (cols, rows) grids for collage. Always cells = cols*rows
# bounded by DEFAULT_MAX_PER_TILE; the picker chooses based on aspect
# ratio of the input cells.
DEFAULT_GRID_CANDIDATES: tuple[tuple[int, int], ...] = (
    (2, 1), (1, 2),
    (2, 2),
    (3, 2), (2, 3),
    (3, 3),
    (4, 2), (2, 4),
)
