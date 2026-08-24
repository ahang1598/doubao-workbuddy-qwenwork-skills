"""Allocation bars — budget/channel/resource percentage breakdown.

Source: ai_slides/docs/allocation-bars.md + renderers/allocation-bars.js

Borrowed design rules:
- Each row: left label | right value text | full-width progress bar below
- ``items[].percent`` (0-100) drives bar length; ``items[].value`` is a
  free-form string (e.g. ``"¥19 万 · 31.7%"``) shown right-aligned
- ``items[].tone``: ``accent``/``primary``/``green``/``soft``/``muted``
  maps to fill color; ``items[].color`` overrides explicitly
- Optional ``title``, ``subtitle``, ``note`` (allocation-principle footer)
- Recommended item count: 2-6
- Typography: label = list-title-size, value = title-sm (NOT KPI-large),
  note = caption — value is data not headline
"""

from __future__ import annotations

from pptx.dml.color import RGBColor

from ._base import (
    Emu, MSO_ANCHOR, MSO_SHAPE, PP_ALIGN, add_paragraph, fill_solid,
    lighten, no_border, no_shadow, set_border, set_text,
)


_TONE_MAP_NAMES = ("accent", "primary", "green", "soft", "muted")


def _tone_color(tone: str | None, palette) -> RGBColor:
    if tone == "accent":
        return palette.accent
    if tone == "primary":
        return palette.primary
    if tone == "green":
        return RGBColor(0x16, 0xA3, 0x4A)
    if tone == "soft":
        return lighten(palette.primary, 0.5)
    if tone == "muted":
        return palette.muted
    return palette.primary


def add_allocation_bars(
    slide,
    origin: tuple[int, int],
    size: tuple[int, int],
    items: list,
    style,
    *,
    title: str | None = None,
    subtitle: str | None = None,
    note: str | None = None,
):
    """Add allocation/percentage bars.

    ``items``: ``[{"label": str, "value": str, "percent": float, "tone": str | None,
                  "color": RGBColor | None}, ...]``  (2-6 recommended)
    """
    ox, oy = origin
    w, h = size
    pal = style.palette
    fonts = style.fonts

    shapes: list = []
    cursor_y = oy

    # title
    if title:
        title_h = Emu(411480)   # ~32pt line
        tb = slide.shapes.add_textbox(ox, cursor_y, w, title_h)
        set_text(tb, title, size=18, bold=True, color=pal.on_bg,
                 font=fonts.header, align=PP_ALIGN.LEFT)
        if subtitle:
            add_paragraph(tb.text_frame, subtitle, size=11, color=pal.muted,
                          font=fonts.body, align=PP_ALIGN.LEFT, space_before=2)
        shapes.append(tb)
        cursor_y += title_h + (Emu(228600) if subtitle else Emu(91440))

    # note footer
    note_reserved = Emu(411480) if note else 0
    bars_area_h = max(h - (cursor_y - oy) - note_reserved, Emu(914400))

    n = len(items)
    if n == 0:
        return shapes
    row_gap = Emu(91440)
    row_h = (bars_area_h - row_gap * (n - 1)) // n

    label_col_w = max(int(w * 0.32), Emu(1828800))
    value_col_w = max(int(w * 0.18), Emu(1097280))
    bar_x = ox
    bar_w_full = w

    for item in items:
        # text row (label left, value right)
        label_tb = slide.shapes.add_textbox(ox, cursor_y, label_col_w, Emu(274320))
        set_text(label_tb, item["label"], size=12, bold=True, color=pal.on_bg,
                 font=fonts.body, align=PP_ALIGN.LEFT)
        shapes.append(label_tb)

        value_tb = slide.shapes.add_textbox(
            ox + w - value_col_w, cursor_y,
            value_col_w, Emu(274320),
        )
        set_text(value_tb, item.get("value", ""), size=12, bold=True, color=pal.muted,
                 font=fonts.body, align=PP_ALIGN.RIGHT)
        shapes.append(value_tb)

        # bar row
        bar_y = cursor_y + Emu(304800)
        bar_h = min(row_h - Emu(304800), Emu(228600))
        if bar_h < Emu(91440):
            bar_h = Emu(91440)

        # track
        track = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, bar_x, bar_y, bar_w_full, bar_h)
        fill_solid(track, lighten(pal.muted, 0.75))
        no_border(track)
        no_shadow(track)
        track.adjustments[0] = 0.5  # max-rounded (capsule progress bar — intentional)
        shapes.append(track)

        # fill
        pct = max(0.0, min(100.0, float(item.get("percent", 0))))
        if pct > 0:
            fill_w = int(bar_w_full * pct / 100)
            color = item.get("color") or _tone_color(item.get("tone"), pal)
            seg = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, bar_x, bar_y, fill_w, bar_h)
            fill_solid(seg, color)
            no_border(seg)
            no_shadow(seg)
            seg.adjustments[0] = 0.5
            shapes.append(seg)

        cursor_y += row_h + row_gap

    # note footer
    if note:
        note_tb = slide.shapes.add_textbox(ox, oy + h - note_reserved, w, note_reserved)
        set_text(note_tb, note, size=10, italic=True, color=pal.muted,
                 font=fonts.body, align=PP_ALIGN.LEFT)
        shapes.append(note_tb)

    return shapes
