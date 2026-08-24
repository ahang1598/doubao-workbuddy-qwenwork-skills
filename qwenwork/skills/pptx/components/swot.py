"""SWOT / probability-impact 2×2 quadrant matrix.

Source: ai_slides/docs/swot-matrix.md + renderers/swot-matrix.js

Borrowed design rules:
- ONLY for SWOT, opportunity/risk, probability×impact, investment decision
  matrices. NOT a generic 4-card grid (use highlight-title-card etc. for that).
- ``quadrants`` schema (two accepted shapes):
  1. Keyed: ``{"highHigh": {"title": ..., "items": [...]}, "highLow": ..., ...}``
     Keys: ``highHigh``/``highLow``/``lowHigh``/``lowLow``
  2. Array of 4: order = high-high, high-low, low-high, low-low
- Each quadrant: title + 3-5 bullet items
- Recommended layout: col>=20, row>=16; 2×2 fixed
- We provide a SWOT-named alias (strengths/weaknesses/opportunities/threats)
  since most callers think in those terms
"""

from __future__ import annotations

from pptx.dml.color import RGBColor

from ._base import (
    Emu, MSO_ANCHOR, MSO_SHAPE, PP_ALIGN, add_card_shell, add_paragraph,
    fill_solid, lighten, no_border, no_shadow, set_border, set_text,
)


# semantic → quadrant position mapping (col, row, color-role)
_SWOT_LAYOUT = [
    ("strengths",     "highHigh", 0, 0, "primary"),    # top-left
    ("weaknesses",    "highLow",  1, 0, "accent"),     # top-right
    ("opportunities", "lowHigh",  0, 1, "secondary"),  # bottom-left
    ("threats",       "lowLow",   1, 1, "muted"),      # bottom-right
]

_DEFAULT_TITLES = {
    "strengths": "Strengths",
    "weaknesses": "Weaknesses",
    "opportunities": "Opportunities",
    "threats": "Threats",
    "highHigh": "High prob. / High impact",
    "highLow": "High prob. / Low impact",
    "lowHigh": "Low prob. / High impact",
    "lowLow": "Low prob. / Low impact",
}


def add_swot(
    slide,
    origin: tuple[int, int],
    size: tuple[int, int],
    quadrants,
    style,
):
    """Add a 2×2 SWOT-style quadrant matrix.

    ``quadrants`` accepts three shapes:
      - SWOT keys: ``{"strengths": [...], "weaknesses": [...],
                     "opportunities": [...], "threats": [...]}``
      - SWOT objects: ``{"strengths": {"title": ..., "items": [...]}, ...}``
      - Probability/impact keys: ``{"highHigh": {...}, "highLow": {...},
                                   "lowHigh": {...}, "lowLow": {...}}``
      - Array of 4 (in highHigh/highLow/lowHigh/lowLow order)
    """
    ox, oy = origin
    w, h = size
    pal = style.palette
    fonts = style.fonts
    gap = Emu(137160)
    cw = (w - gap) // 2
    ch = (h - gap) // 2

    # normalize input → dict of swot-key → (title, items)
    norm = _normalize_quadrants(quadrants)

    shapes: list = []
    for swot_key, prob_key, col, row, role in _SWOT_LAYOUT:
        data = norm.get(swot_key) or norm.get(prob_key)
        if data is None:
            continue
        x = ox + col * (cw + gap)
        y = oy + row * (ch + gap)

        color = getattr(pal, role)
        card = add_card_shell(slide, x, y, cw, ch, fill=pal.bg, border=color, border_width_pt=1.5)
        card.text_frame.margin_left = Emu(182880)
        card.text_frame.margin_right = Emu(182880)
        card.text_frame.margin_top = Emu(137160)

        # accent band on the left edge to mark quadrant identity
        band_w = Emu(60960)
        band = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, y, band_w, ch)
        fill_solid(band, color)
        no_border(band)
        no_shadow(band)

        title = data.get("title") or _DEFAULT_TITLES.get(swot_key) or _DEFAULT_TITLES[prob_key]
        set_text(card, title, size=16, bold=True, color=color,
                 font=fonts.header, align=PP_ALIGN.LEFT)
        for item in data.get("items", [])[:5]:
            add_paragraph(card.text_frame, f"·  {item}", size=11,
                          color=pal.on_bg, font=fonts.body,
                          align=PP_ALIGN.LEFT, space_before=6)

        shapes.append(band)
        shapes.append(card)

    return shapes


def _normalize_quadrants(q) -> dict:
    """Return ``{swot_key: {"title": str | None, "items": [str, ...]}}``."""
    out: dict = {}
    if isinstance(q, list):
        keys = ["highHigh", "highLow", "lowHigh", "lowLow"]
        for i, entry in enumerate(q[:4]):
            out[keys[i]] = _normalize_entry(entry)
        return out
    if not isinstance(q, dict):
        raise TypeError("swot quadrants must be dict or list of 4")
    for key, val in q.items():
        out[key] = _normalize_entry(val)
    return out


def _normalize_entry(entry) -> dict:
    """Coerce either a list (= items) or a dict ({title, items}) to dict form."""
    if isinstance(entry, list):
        return {"title": None, "items": [str(x) for x in entry]}
    if isinstance(entry, dict):
        return {
            "title": entry.get("title"),
            "items": [str(x) for x in entry.get("items", [])],
        }
    raise TypeError(f"swot quadrant entry must be list or dict, got {type(entry)!r}")
