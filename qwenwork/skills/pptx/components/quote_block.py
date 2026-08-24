"""Quote block — CEO message, strategy callout, long quote.

Source: ai_slides/docs/quote-block.md + renderers/quote-block.js

Borrowed design rules:
- Fields: ``kicker`` (small label), ``title`` (heading), ``copy`` (required body)
- ``variant``: ``"line"`` (default: soft bg, brand-color left rule, kicker shown)
              ``"dark"`` (dark bg, light text, brand emphasis)
- Narrow-tall layout: when w < h, kicker is hidden (avoids three text
  layers crammed in a side column). We do the same.
- Background uses ``--theme-card-soft-bg`` (shared with metric-card) →
  we lighten primary toward off-white.
"""

from __future__ import annotations

from pptx.dml.color import RGBColor

from ._base import (
    Emu, MSO_ANCHOR, MSO_SHAPE, PP_ALIGN, add_card_shell, add_paragraph,
    fill_solid, lighten, no_border, no_shadow, set_text,
)


def add_quote_block(
    slide,
    origin: tuple[int, int],
    size: tuple[int, int],
    content: dict,
    style,
    *,
    variant: str = "line",
):
    """Add a quote block.

    ``content``: ``{"kicker": str | None, "title": str | None, "copy": str (required),
                   "author": str | None, "role": str | None}``
    ``author``/``role`` are our extension (ai_slides keeps the quote
    content-only) — useful for attribution slides; rendered after copy.
    """
    ox, oy = origin
    w, h = size
    pal = style.palette
    fonts = style.fonts

    is_dark = variant == "dark"
    is_narrow = w < h          # follow ai_slides side-column rule

    if is_dark:
        bg_color = pal.on_bg
        text_color = pal.bg
        kicker_color = lighten(pal.accent, 0.1)
        title_color = pal.bg
        rule_color = pal.accent
    else:
        bg_color = lighten(pal.primary, 0.92)    # very soft tint of brand
        text_color = pal.on_bg
        kicker_color = pal.primary
        title_color = pal.primary
        rule_color = pal.primary

    card = add_card_shell(slide, ox, oy, w, h, fill=bg_color, border=None)
    card.text_frame.margin_left = Emu(365760)
    card.text_frame.margin_right = Emu(228600)
    card.text_frame.margin_top = Emu(228600)
    card.text_frame.margin_bottom = Emu(228600)

    shapes = [card]

    # Left rule for "line" variant (positioned outside the card text margins)
    if variant == "line":
        rule_w = Emu(45720)        # ~3.6pt
        rule = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            ox + Emu(91440), oy + Emu(228600),
            rule_w, h - Emu(457200),
        )
        fill_solid(rule, rule_color)
        no_border(rule)
        no_shadow(rule)
        shapes.insert(0, rule)

    tf = card.text_frame
    first_set = False

    # kicker — skipped in narrow side-column layouts
    if content.get("kicker") and not is_narrow:
        set_text(card, str(content["kicker"]).upper(),
                 size=11, bold=True, color=kicker_color,
                 font=fonts.body, align=PP_ALIGN.LEFT)
        first_set = True

    # title
    if content.get("title"):
        if first_set:
            add_paragraph(tf, content["title"],
                          size=20, bold=True, color=title_color,
                          font=fonts.header, align=PP_ALIGN.LEFT, space_before=6)
        else:
            set_text(card, content["title"],
                     size=20, bold=True, color=title_color,
                     font=fonts.header, align=PP_ALIGN.LEFT)
            first_set = True

    # copy (required)
    copy_text = content["copy"]
    if first_set:
        add_paragraph(tf, copy_text,
                      size=16, italic=True, color=text_color,
                      font=fonts.header, align=PP_ALIGN.LEFT, space_before=8)
    else:
        set_text(card, copy_text,
                 size=16, italic=True, color=text_color,
                 font=fonts.header, align=PP_ALIGN.LEFT)
        first_set = True

    # attribution (our extension)
    if content.get("author"):
        add_paragraph(tf, content["author"],
                      size=12, bold=True, color=kicker_color,
                      font=fonts.header, align=PP_ALIGN.LEFT, space_before=12)
    if content.get("role"):
        add_paragraph(tf, content["role"],
                      size=11, color=pal.muted if not is_dark else lighten(pal.bg, 0.25),
                      font=fonts.body, align=PP_ALIGN.LEFT, space_before=2)

    return shapes
