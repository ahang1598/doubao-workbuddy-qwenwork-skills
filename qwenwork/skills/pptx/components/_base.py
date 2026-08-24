"""Shared geometry / drawing helpers for components.

Lightweight utilities common to multiple components. Keep this file
small — single-component math belongs in the component module.
"""

from __future__ import annotations

import re
from typing import Iterable

from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Pt

from helpers import (
    add_paragraph,
    fill_solid,
    no_border,
    no_fill,
    no_shadow,
    set_border,
    set_fill_alpha,
    set_text,
)

__all__ = [
    "EMU_PER_INCH",
    "EMU_PER_PT",
    "EMU_PER_CM",
    "blend",
    "lighten",
    "darken",
    "depth_ramp",
    "polar",
    "col_edges",
    "auto_delta_color",
    "add_card_shell",
    "MSO_SHAPE",
    "MSO_ANCHOR",
    "PP_ALIGN",
    "Emu",
    "Pt",
    "set_text",
    "add_paragraph",
    "fill_solid",
    "no_border",
    "no_fill",
    "no_shadow",
    "set_border",
    "set_fill_alpha",
]


EMU_PER_INCH = 914400
EMU_PER_PT = 12700
EMU_PER_CM = 360000


def blend(a: RGBColor, b: RGBColor, t: float) -> RGBColor:
    """Linear blend two RGBColor values. ``t=0`` returns a; ``t=1`` returns b."""
    t = max(0.0, min(1.0, t))
    ar, ag, ab = a[0], a[1], a[2]
    br, bg, bb = b[0], b[1], b[2]
    return RGBColor(
        int(ar + (br - ar) * t),
        int(ag + (bg - ag) * t),
        int(ab + (bb - ab) * t),
    )


def lighten(c: RGBColor, t: float) -> RGBColor:
    """Move ``c`` toward white by fraction ``t`` (0..1)."""
    return blend(c, RGBColor(0xFF, 0xFF, 0xFF), t)


def darken(c: RGBColor, t: float) -> RGBColor:
    """Move ``c`` toward black by fraction ``t`` (0..1)."""
    return blend(c, RGBColor(0x00, 0x00, 0x00), t)


def depth_ramp(base: RGBColor, n: int, *, light_first: bool = True) -> list[RGBColor]:
    """Return ``n`` colors stepped from light→dark (or reverse) around ``base``.

    Borrowed from ai_slides convention: `data-step="1..4"` etc. use a
    palette ramp where outer/early steps are lighter and inner/late
    steps are darker. For layered-diagram, light_first=True puts the
    lightest shade on the outermost layer.
    """
    if n <= 0:
        return []
    if n == 1:
        return [base]
    out: list[RGBColor] = []
    for i in range(n):
        # spread from -0.35 (light) to +0.20 (dark) around base
        t = i / (n - 1)
        if light_first:
            shade_t = (1 - t) * 0.35       # lighten more for early
            dark_t = t * 0.20              # darken more for late
        else:
            shade_t = t * 0.35
            dark_t = (1 - t) * 0.20
        c = lighten(base, shade_t) if shade_t > dark_t else darken(base, dark_t)
        out.append(c)
    return out


def polar(cx: int, cy: int, theta_rad: float, radius_emu: int) -> tuple[int, int]:
    """Polar → cartesian. 0 rad = right, increases counterclockwise (standard math)."""
    import math
    x = cx + int(radius_emu * math.cos(theta_rad))
    y = cy + int(radius_emu * math.sin(theta_rad))
    return x, y


def col_edges(ox: int, w: int, n: int) -> list[int]:
    """Return ``n+1`` column boundaries spanning ``[ox, ox+w]`` evenly.

    Integer ``w // n`` slicing drops the remainder, so ``ox + i*col_w``
    accumulates error and the last column never reaches ``ox+w`` — columns
    look misaligned on the right edge. This distributes the rounding so the
    first edge is exactly ``ox`` and the last is exactly ``ox+w``.

    Usage::

        edges = col_edges(ox, w, n)
        for i in range(n):
            cx, cw = edges[i], edges[i + 1] - edges[i]
    """
    if n <= 0:
        return [ox]
    return [ox + round(i * w / n) for i in range(n + 1)]


_PCT_RE = re.compile(r"[+-]?\d+(\.\d+)?%")
_INCREASE_KEYWORDS = ("+", "增长", "提升", "↑", "up", "growth")
_DECREASE_KEYWORDS = ("-", "下降", "下跌", "减少", "↓", "down", "decline")


def auto_delta_color(text: str, palette) -> RGBColor | None:
    """Detect +/- delta in a desc string and return success/danger color.

    ai_slides metric-card convention: `+18%` / `增长18%` / `提升25%`
    auto-greens; `-12%` / `下降12%` / `下跌8%` auto-reds. We return
    None for neutral text so the caller can use the default body color.
    """
    if not text:
        return None
    lower = text.lower()
    has_increase = any(k in lower or k in text for k in _INCREASE_KEYWORDS)
    has_decrease = any(k in lower or k in text for k in _DECREASE_KEYWORDS)
    # disambiguate raw "-" inside a date
    if has_decrease and re.search(r"\d{4}-\d{2}", text) and "-" not in lower.replace(text, ""):
        has_decrease = False
    if has_increase and not has_decrease:
        return RGBColor(0x16, 0xA3, 0x4A)   # green-600
    if has_decrease and not has_increase:
        return RGBColor(0xDC, 0x26, 0x26)   # red-600
    return None


def add_card_shell(
    slide,
    x: int, y: int, w: int, h: int,
    *,
    fill: RGBColor | None,
    border: RGBColor | None = None,
    border_width_pt: float = 1.0,
    radius_kind: str = "rect",   # "rect" (default) | "rounded"
):
    """Standard card outer shape: square-cornered, flat (no shadow).

    Defaults to a plain rectangle with the inherited theme shadow killed —
    rounded corners + soft shadows read as "AI-generated" and most themes
    forbid them. Pass ``radius_kind="rounded"`` only when a capsule/pill is
    the intended design language (e.g. progress tracks).

    Returns the shape. Caller fills text via ``shape.text_frame``.
    """
    shape_enum = MSO_SHAPE.ROUNDED_RECTANGLE if radius_kind == "rounded" else MSO_SHAPE.RECTANGLE
    card = slide.shapes.add_shape(shape_enum, x, y, w, h)
    if fill is not None:
        fill_solid(card, fill)
    else:
        card.fill.background()
    if border is not None:
        set_border(card, border, border_width_pt)
    else:
        no_border(card)
    no_shadow(card)
    card.text_frame.word_wrap = True
    return card
