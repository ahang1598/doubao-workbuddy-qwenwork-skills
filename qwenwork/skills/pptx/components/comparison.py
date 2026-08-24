"""Comparison — 2-4 side-by-side panels for old-vs-new, competitor analysis.

Source: ai_slides/docs/compare.md + renderers/compare.js

Borrowed design rules:
- 2-4 panels. 2/3 = horizontal; 4 = 2×2 grid.
- ONLY for actual comparisons (old vs new, competitor analysis,
  traditional vs recommended). Parallel viewpoints → use a different
  component.
- Order constraint: "traditional/old/original" renders LEFT;
  "recommended/intelligent/optimized" renders RIGHT. ``featured: true``
  marks the recommended panel; renderer auto-corrects order even if
  input has them swapped.
- 2-panel mode shows a center "VS" / "对比" badge.
- Panel structure: ``kicker`` (small label) + ``title`` + ``tagline``
  (subtitle) + ``items`` (numbered list, each w/ title+desc) + optional
  ``scale`` (bottom big number + unit).
- Sparse content (2 panels, ≤2 items each): top-align items instead
  of stretching to fill height.
"""

from __future__ import annotations

from pptx.dml.color import RGBColor

from ._base import (
    Emu, MSO_ANCHOR, MSO_SHAPE, PP_ALIGN, add_card_shell, add_paragraph,
    fill_solid, lighten, no_border, no_shadow, set_border, set_text,
)


def add_comparison(
    slide,
    origin: tuple[int, int],
    size: tuple[int, int],
    panels: list,
    style,
    *,
    vs_label: str = "VS",
):
    """Add a multi-panel comparison.

    ``panels``: ``[{
        "kicker": str | None,
        "title": str (required),
        "tagline": str | None,
        "featured": bool | None,
        "items": [{"title": str, "desc": str | None, "number": str | int | None}, ...],
        "scale": {"value": str, "unit": str} | None
    }, ...]``  (2-4 panels)
    """
    ox, oy = origin
    w, h = size
    pal = style.palette
    fonts = style.fonts
    n = len(panels)
    if n < 2 or n > 4:
        raise ValueError("comparison requires 2-4 panels")

    panels = _reorder_for_featured(panels)

    if n == 4:
        rows, cols = 2, 2
    else:
        rows, cols = 1, n

    gap = Emu(228600)
    cw = (w - gap * (cols - 1)) // cols
    ch = (h - gap * (rows - 1)) // rows

    shapes: list = []
    sparse = (n == 2 and all(len(p.get("items", [])) <= 2 for p in panels))

    for i, panel in enumerate(panels):
        row = i // cols
        col = i % cols
        x = ox + col * (cw + gap)
        y = oy + row * (ch + gap)

        featured = bool(panel.get("featured"))
        if featured:
            band_color = pal.primary
            body_border = pal.primary
        else:
            band_color = pal.muted
            body_border = lighten(pal.muted, 0.3)

        # title band
        band_h = Emu(685800)
        band = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, y, cw, band_h)
        fill_solid(band, band_color)
        no_border(band)
        no_shadow(band)
        band.text_frame.margin_left = Emu(228600)
        band.text_frame.margin_right = Emu(228600)
        band.text_frame.margin_top = Emu(91440)

        if panel.get("kicker"):
            set_text(band, str(panel["kicker"]).upper(),
                     size=10, bold=True, color=lighten(pal.bg, 0.05),
                     font=fonts.body, align=PP_ALIGN.LEFT)
            add_paragraph(band.text_frame, panel["title"],
                          size=18, bold=True, color=pal.bg,
                          font=fonts.header, align=PP_ALIGN.LEFT, space_before=2)
        else:
            set_text(band, panel["title"],
                     size=18, bold=True, color=pal.bg,
                     font=fonts.header, align=PP_ALIGN.LEFT)
        shapes.append(band)

        # body card
        body_y = y + band_h
        body_h = ch - band_h
        body = add_card_shell(slide, x, body_y, cw, body_h, fill=pal.bg,
                              border=body_border, border_width_pt=1.0)
        body.text_frame.margin_left = Emu(228600)
        body.text_frame.margin_right = Emu(228600)
        body.text_frame.margin_top = Emu(137160)
        body.text_frame.margin_bottom = Emu(137160)
        body.text_frame.vertical_anchor = MSO_ANCHOR.TOP if sparse else MSO_ANCHOR.TOP

        first_para_used = False
        if panel.get("tagline"):
            set_text(body, panel["tagline"], size=11, italic=True,
                     color=pal.muted, font=fonts.body, align=PP_ALIGN.LEFT)
            first_para_used = True

        items = panel.get("items", [])
        for idx, item in enumerate(items, start=1):
            number = item.get("number") or idx
            heading = f"{number:>02}  {item['title']}" if isinstance(number, int) else f"{number}  {item['title']}"
            line_color = pal.primary if featured else pal.on_bg
            if not first_para_used:
                set_text(body, heading, size=13, bold=True,
                         color=line_color, font=fonts.header, align=PP_ALIGN.LEFT)
                first_para_used = True
            else:
                add_paragraph(body.text_frame, heading, size=13, bold=True,
                              color=line_color, font=fonts.header,
                              align=PP_ALIGN.LEFT, space_before=10)
            if item.get("desc"):
                add_paragraph(body.text_frame, item["desc"], size=11,
                              color=pal.on_bg, font=fonts.body,
                              align=PP_ALIGN.LEFT, space_before=2)

        # bottom scale callout — rendered in its own textbox pinned to the
        # bottom of the body card. Previously this was appended as another
        # paragraph in the items text_frame: with sparse items (≤2) the
        # callout floated up to the middle of the panel and collided with
        # the center VS badge in 2-panel mode.
        if panel.get("scale"):
            scale = panel["scale"]
            scale_text = f"{scale.get('value', '')}  {scale.get('unit', '')}".strip()
            scale_h = Emu(685800)
            scale_tb = slide.shapes.add_textbox(
                x + Emu(228600),
                body_y + body_h - scale_h - Emu(137160),
                cw - Emu(457200),
                scale_h,
            )
            scale_tb.text_frame.margin_left = 0
            scale_tb.text_frame.margin_right = 0
            scale_tb.text_frame.margin_top = 0
            scale_tb.text_frame.margin_bottom = 0
            scale_tb.text_frame.vertical_anchor = MSO_ANCHOR.BOTTOM
            set_text(scale_tb, scale_text, size=22, bold=True,
                     color=pal.primary if featured else pal.muted,
                     font=fonts.header, align=PP_ALIGN.LEFT)
            shapes.append(scale_tb)

        shapes.append(body)

    # center VS badge for 2-panel case
    if n == 2:
        badge_d = Emu(548640)
        bx = ox + cw + (gap - badge_d) // 2
        by = oy + (h - badge_d) // 2
        badge = slide.shapes.add_shape(MSO_SHAPE.OVAL, bx, by, badge_d, badge_d)
        fill_solid(badge, pal.primary)
        no_border(badge)
        no_shadow(badge)
        badge.text_frame.margin_left = 0
        badge.text_frame.margin_right = 0
        badge.text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE
        set_text(badge, vs_label, size=14, bold=True, color=pal.bg,
                 font=fonts.header, align=PP_ALIGN.CENTER)
        shapes.append(badge)

    return shapes


def _reorder_for_featured(panels: list) -> list:
    """If exactly 2 panels and the featured one is left, swap so featured ends on right."""
    if len(panels) != 2:
        return list(panels)
    if panels[0].get("featured") and not panels[1].get("featured"):
        return [panels[1], panels[0]]
    return list(panels)
