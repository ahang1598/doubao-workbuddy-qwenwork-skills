"""Metric card — single big number with kicker, value, optional delta desc.

Source: ai_slides/docs/metric-card.md + renderers/metric-card.js

Borrowed design rules:
- ``kicker`` is a small label (category/module name), rendered above the value
- ``value`` is the headline figure; font auto-scales with container width
- ``desc`` supports multi-line via ``\\n``; auto-greens +/+growth keywords,
  auto-reds -/decrease keywords (see ``_base.auto_delta_color``)
- ``variant``: ``"tech"`` (default: light card, thin border)
              ``"primary"`` (brand-color background, white text)
              ``"highlight"`` (alias for primary)
- Compact mode (col<=8, row<=7) shrinks value font; we approximate via
  width-based size selection
- Same ``layout`` should contain at most ONE ``variant="primary"`` card;
  enforcement is on the caller, not us
"""

from __future__ import annotations

import unicodedata

from pptx.dml.color import RGBColor

from ._base import (
    Emu, MSO_ANCHOR, PP_ALIGN, add_card_shell, add_paragraph,
    auto_delta_color, set_text,
)


def add_metric_card(
    slide,
    origin: tuple[int, int],
    size: tuple[int, int],
    content: dict,
    style,
    *,
    variant: str = "tech",
):
    """Add a single-metric card.

    ``content``: ``{"kicker": str | None, "value": str (required), "desc": str | None}``
    """
    ox, oy = origin
    w, h = size
    pal = style.palette
    fonts = style.fonts

    is_primary = variant in ("primary", "highlight")

    if is_primary:
        bg = pal.primary
        border = None
        kicker_color = pal.bg
        value_color = pal.bg
        desc_color = pal.bg
    else:
        bg = pal.bg
        border = pal.secondary
        kicker_color = pal.muted
        value_color = pal.primary
        desc_color = pal.on_bg

    card = add_card_shell(slide, ox, oy, w, h, fill=bg, border=border, border_width_pt=1.0)
    card.text_frame.margin_left = Emu(228600)
    card.text_frame.margin_right = Emu(228600)
    card.text_frame.margin_top = Emu(182880)
    card.text_frame.margin_bottom = Emu(182880)

    value_text = str(content["value"])

    # Auto-scale: width-based size buckets. ai_slides drives this via
    # CSS clamp(), we approximate with discrete steps so PowerPoint
    # renders deterministically.
    inches_w = w / 914400
    if inches_w >= 4.0:
        value_size, kicker_size, desc_size = 48, 12, 13
    elif inches_w >= 2.8:
        value_size, kicker_size, desc_size = 40, 11, 12
    elif inches_w >= 2.0:
        value_size, kicker_size, desc_size = 32, 10, 11
    else:
        value_size, kicker_size, desc_size = 26, 9, 10

    # 数值与单位是不可拆分的展示原子；按可用宽度保守缩放，正文仍可换行。
    display_units = sum(
        1.0 if unicodedata.east_asian_width(char) in ("W", "F") else 0.55
        for char in value_text
    )
    usable_width_pt = max(
        w - int(card.text_frame.margin_left) - int(card.text_frame.margin_right),
        1,
    ) / 12700
    fitted_size = int(usable_width_pt * 0.90 / max(display_units, 1.0))
    value_size = max(18, min(value_size, fitted_size))

    tf = card.text_frame
    first_para_used = False

    # kicker (capsule label; we render as uppercase tracked text instead
    # of an actual capsule to keep the OOXML clean)
    if content.get("kicker"):
        kicker_text = str(content["kicker"]).upper()
        set_text(
            card,
            kicker_text,
            size=kicker_size,
            bold=True,
            color=kicker_color,
            font=fonts.body,
            align=PP_ALIGN.LEFT,
        )
        first_para_used = True

    # value
    if first_para_used:
        add_paragraph(
            tf, value_text,
            size=value_size, bold=True, color=value_color,
            font=fonts.header, align=PP_ALIGN.LEFT, space_before=4,
        )
    else:
        set_text(
            card, value_text,
            size=value_size, bold=True, color=value_color,
            font=fonts.header, align=PP_ALIGN.LEFT,
        )
        first_para_used = True

    # desc — split on \n; each line gets its own paragraph; auto-color deltas
    desc = content.get("desc")
    if desc:
        for line in str(desc).split("\n"):
            if not line.strip():
                continue
            line_color = auto_delta_color(line, pal) if not is_primary else desc_color
            add_paragraph(
                tf, line,
                size=desc_size,
                color=line_color or desc_color,
                font=fonts.body,
                align=PP_ALIGN.LEFT,
                space_before=6,
            )

    return [card]
