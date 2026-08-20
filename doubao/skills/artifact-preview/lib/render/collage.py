"""Multi-page collage tiling.

The strategy mirrors the legacy ``trace_llm_judge`` implementation:

1. Group **consecutive** input cells by some "source key" (typically the
   filename root with the page suffix stripped). The grouping is a
   caller responsibility — we just tile a flat sequence here.
2. For each group, pick a (cols, rows) grid that maximizes
   pages-per-collage while keeping the output aspect ratio in a
   readable window ([0.5, 2.0] by default).
3. Pages within a group are letterboxed (resize-preserving-aspect onto
   a white cell) and labeled with a small page-number tag.
4. Long groups are chunked: the first N-1 chunks get the "primary"
   grid; the final partial chunk picks a smaller grid tailored to its
   remaining count.

All helpers are pure-PIL — no IO. The caller is responsible for
encoding the resulting :class:`CollageResult` images to JPEG/PNG and
writing to disk or base64 data URIs.
"""

from __future__ import annotations

import logging
import math
from typing import Any, Sequence

from .constants import (
    DEFAULT_CELL_MARGIN,
    DEFAULT_GRID_CANDIDATES,
    DEFAULT_LABEL_FONT_SIZE,
    DEFAULT_MAX_PER_TILE,
    DEFAULT_MIN_GROUP_SIZE,
    DEFAULT_OUT_ASPECT_MAX,
    DEFAULT_OUT_ASPECT_MIN,
    DEFAULT_OUT_MAX_DIM,
)
from .types import CollageResult

logger = logging.getLogger(__name__)


def pick_grid(
    aspect_ratio: float,
    n_available: int,
    *,
    max_per_tile: int = DEFAULT_MAX_PER_TILE,
    out_aspect_min: float = DEFAULT_OUT_ASPECT_MIN,
    out_aspect_max: float = DEFAULT_OUT_ASPECT_MAX,
    grid_candidates: Sequence[tuple[int, int]] = DEFAULT_GRID_CANDIDATES,
) -> tuple[int, int]:
    """Pick (cols, rows) maximizing compression while keeping output
    aspect inside ``[out_aspect_min, out_aspect_max]``.

    ``aspect_ratio`` is cell-width / cell-height of the typical input
    page. Strategy:

    1. Filter candidates with ``cells <= min(max_per_tile, n_available)``.
    2. Among the filtered set, prefer those whose
       ``out_aspect = cols * cell_aspect / rows`` lies in the readable
       window. Tie-break by closest-to-square (smaller ``|log out_aspect|``).
    3. Falls back to the least-bad candidate when nothing fits the
       window (extreme inputs like 5:1 panoramas).
    """
    cap = min(max_per_tile, max(1, n_available))
    r = max(aspect_ratio, 1e-6)
    within: list[tuple[int, float, int, int]] = []
    outside: list[tuple[int, float, int, int]] = []
    for cols, rows in grid_candidates:
        cells = cols * rows
        if cells > cap:
            continue
        out_aspect = (cols * r) / rows
        score = abs(math.log(out_aspect))
        tup = (cells, score, cols, rows)
        if out_aspect_min <= out_aspect <= out_aspect_max:
            within.append(tup)
        else:
            outside.append(tup)
    pool = within if within else outside
    if not pool:
        return (1, 2) if aspect_ratio >= 1.0 else (2, 1)
    pool.sort(key=lambda x: (-x[0], x[1]))
    _cells, _score, c, rr = pool[0]
    return (c, rr)


def letterbox_cell(
    img: Any,
    cell_w: int,
    cell_h: int,
    *,
    bg: tuple[int, int, int] = (255, 255, 255),
) -> Any:
    """Resize ``img`` preserving aspect into ``(cell_w, cell_h)`` on a
    solid background. PIL is imported lazily so callers without Pillow
    only see the ImportError when they actually try to compose.
    """
    from PIL import Image

    iw, ih = img.size
    scale = min(cell_w / max(iw, 1), cell_h / max(ih, 1))
    new_w = max(1, int(round(iw * scale)))
    new_h = max(1, int(round(ih * scale)))
    resized = img.resize((new_w, new_h), Image.LANCZOS)
    canvas = Image.new("RGB", (cell_w, cell_h), bg)
    canvas.paste(resized, ((cell_w - new_w) // 2, (cell_h - new_h) // 2))
    return canvas


def draw_cell_label(canvas: Any, label: str) -> None:
    """Draw a small page-number tag at the top-left corner of ``canvas``.

    Best-effort font lookup: DejaVu Sans Bold → DejaVu Sans → PIL's
    bitmap default. Silently no-ops if PIL.ImageDraw / ImageFont are
    missing (extremely unusual — Pillow includes both).
    """
    try:
        from PIL import ImageDraw, ImageFont
    except Exception:
        return
    draw = ImageDraw.Draw(canvas)
    font = None
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        try:
            font = ImageFont.truetype(path, DEFAULT_LABEL_FONT_SIZE)
            break
        except Exception:
            continue
    if font is None:
        font = ImageFont.load_default()
    try:
        bbox = draw.textbbox((0, 0), label, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    except Exception:
        tw, th = 80, 18
    pad = 4
    box = [0, 0, tw + 2 * pad, th + 2 * pad]
    draw.rectangle(box, fill=(0, 0, 0))
    draw.text((pad, pad), label, fill=(255, 255, 255), font=font)


def compose_collage(
    cells: list[tuple[str, Any]],
    cols: int,
    rows: int,
    *,
    out_max_dim: int = DEFAULT_OUT_MAX_DIM,
    cell_margin: int = DEFAULT_CELL_MARGIN,
) -> Any:
    """Tile ``cells`` (list of ``(label, PIL.Image)``) into a single
    canvas, ``cols`` × ``rows``, white background.

    Cell size is auto-picked from the median input aspect so the
    composite's longest dimension stays ``<= out_max_dim``. Labels are
    rendered as overlays inside each cell (no extra row height
    reserved).
    """
    from PIL import Image

    if not cells:
        raise ValueError("compose_collage: cells must be non-empty")

    aspects = [c[1].size[0] / max(1, c[1].size[1]) for c in cells]
    med_aspect = sorted(aspects)[len(aspects) // 2]
    margin = cell_margin

    cell_w = cell_h = 0
    for guess_cell_w in (600, 540, 480, 420, 380):
        cell_w = guess_cell_w
        cell_h = int(round(cell_w / max(med_aspect, 1e-6)))
        total_w = cols * cell_w + (cols + 1) * margin
        total_h = rows * cell_h + (rows + 1) * margin
        if max(total_w, total_h) <= out_max_dim:
            break
    else:
        max_cell_w = max(1, (out_max_dim - (cols + 1) * margin) // cols)
        max_cell_h = max(1, (out_max_dim - (rows + 1) * margin) // rows)
        cell_w = max(1, min(max_cell_w, int(max_cell_h * med_aspect)))
        cell_h = max(1, min(max_cell_h, int(cell_w / max(med_aspect, 1e-6))))

    total_w = cols * cell_w + (cols + 1) * margin
    total_h = rows * cell_h + (rows + 1) * margin
    canvas = Image.new("RGB", (total_w, total_h), (255, 255, 255))
    for idx, (label, img) in enumerate(cells):
        r = idx // cols
        c = idx % cols
        cell_canvas = letterbox_cell(img, cell_w, cell_h)
        if label:
            draw_cell_label(cell_canvas, label)
        x = margin + c * (cell_w + margin)
        y = margin + r * (cell_h + margin)
        canvas.paste(cell_canvas, (x, y))
    return canvas


def _balanced_chunks(run: list[int], per_tile: int) -> list[list[int]]:
    """Split ``run`` into tiles of nearly equal size, none smaller than the rest
    by more than one item.

    ``per_tile`` is the capacity of the preferred grid, so the tile count is
    ``ceil(len(run) / per_tile)`` and every item ends up in exactly one tile.
    Greedy filling would instead leave a remainder that can be a single item.

    >>> [len(c) for c in _balanced_chunks(list(range(10)), 9)]
    [5, 5]
    >>> [len(c) for c in _balanced_chunks(list(range(5)), 4)]
    [3, 2]
    >>> [len(c) for c in _balanced_chunks(list(range(19)), 9)]
    [7, 6, 6]
    """
    n = len(run)
    if n == 0:
        return []
    per_tile = max(1, per_tile)
    tiles = max(1, -(-n // per_tile))  # ceil
    base, extra = divmod(n, tiles)
    chunks: list[list[int]] = []
    idx = 0
    for t in range(tiles):
        size = base + (1 if t < extra else 0)
        chunks.append(run[idx: idx + size])
        idx += size
    return chunks


def build_collages(
    items: list[tuple[str, str, Any]],
    *,
    min_group: int = DEFAULT_MIN_GROUP_SIZE,
    max_per_tile: int = DEFAULT_MAX_PER_TILE,
    out_max_dim: int = DEFAULT_OUT_MAX_DIM,
) -> list[CollageResult]:
    """Tile a flat sequence of ``(group_key, label, PIL.Image)`` cells.

    Consecutive items sharing the same ``group_key`` form a group; each
    group of size ``>= min_group`` is split into chunks of size
    ``cols*rows`` (chosen by :func:`pick_grid`) and each chunk becomes
    one :class:`CollageResult`.

    Items belonging to a group of size ``< min_group`` are skipped (the
    caller already has the originals; collaging a single page wastes
    tokens and resolution).

    Returns
    -------
    list[CollageResult]
        Empty list when no group meets the size threshold.
    """
    try:
        from PIL import Image  # noqa: F401
    except Exception as exc:
        logger.warning("[collage] Pillow unavailable: %s", exc)
        return []

    if not items:
        return []

    runs: list[list[int]] = []
    cur_key: str | None = None
    cur_run: list[int] = []
    for i, (group_key, _label, _img) in enumerate(items):
        if group_key == cur_key:
            cur_run.append(i)
        else:
            if cur_run:
                runs.append(cur_run)
            cur_run = [i]
            cur_key = group_key
    if cur_run:
        runs.append(cur_run)

    out: list[CollageResult] = []
    for run in runs:
        if len(run) < max(2, min_group):
            continue
        run_aspects = sorted(
            items[i][2].size[0] / max(1, items[i][2].size[1]) for i in run
        )
        med_aspect = run_aspects[len(run_aspects) // 2]
        primary_cols, primary_rows = pick_grid(
            med_aspect, len(run), max_per_tile=max_per_tile,
        )
        primary_per_tile = primary_cols * primary_rows

        # Balance the run across ceil(n / per_tile) tiles instead of filling
        # each tile to capacity. Filling greedily can leave a 1-item remainder,
        # and a 1-item tile used to be dropped — which silently hid the last
        # page of, say, a 10-page document tiled 9-up.
        for chunk_indices in _balanced_chunks(run, primary_per_tile):
            cols, rows = pick_grid(
                med_aspect, len(chunk_indices), max_per_tile=max_per_tile,
            )

            cells: list[tuple[str, Any]] = []
            cell_labels: list[str] = []
            for gi in chunk_indices:
                _gkey, label, img = items[gi]
                cells.append((label, img))
                cell_labels.append(label)
            try:
                collage_img = compose_collage(
                    cells, cols, rows, out_max_dim=out_max_dim,
                )
            except Exception as exc:
                logger.warning(
                    "[collage] compose failed (%d cells, %dx%d): %s",
                    len(cells), cols, rows, exc,
                )
                continue
            out.append(CollageResult(
                image=collage_img,
                cols=cols,
                rows=rows,
                cell_labels=cell_labels,
                source_indices=list(chunk_indices),
            ))
    return out
