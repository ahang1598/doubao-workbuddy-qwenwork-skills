"""Layered diagram — concentric circles, bottom-aligned, outer→inner.

Source: ai_slides/docs/layered-diagram.md + renderers/layered-diagram.js

Borrowed design rules:
- Concentric circles (NOT stacked rectangles — that was my prior mistake)
- Bottom-aligned: all circles share their bottom edge so layer labels
  read top-down from outer ring inward
- 2-6 layers; innermost can opt-in to ``tone="strong"`` for emphasis
- Solid fills only (no transparency / gradient / shadow) — ai_slides
  explicit rule: ``为保证 HTML 转 PPT/矢量时不丢层，圆层使用纯色填充``
- Outer ring is lightest, inner darkest — drives the depth ramp
- Optional top ``title`` + ``desc/subtitle``; layer label in upper part
  of each crescent (``labelY`` controls vertical position; default auto)
"""

from __future__ import annotations

from pptx.dml.color import RGBColor

from ._base import (
    Emu, MSO_ANCHOR, MSO_SHAPE, PP_ALIGN, add_paragraph, darken,
    depth_ramp, fill_solid, lighten, no_border, no_shadow, set_text,
)


def add_layered_diagram(
    slide,
    origin: tuple[int, int],
    size: tuple[int, int],
    layers: list,
    style,
    *,
    title: str | None = None,
    desc: str | None = None,
):
    """Add a concentric-circle layered diagram.

    ``layers``: outer→inner, ``[{"title"|"label": str, "tone": "strong"? }, ...]``
    Recommended 2-6 layers.
    """
    ox, oy = origin
    w, h = size
    pal = style.palette
    fonts = style.fonts
    n = len(layers)
    if n < 2:
        raise ValueError("layered_diagram requires ≥2 layers")
    if n > 6:
        raise ValueError("layered_diagram supports at most 6 layers")

    shapes: list = []

    # title strip
    title_reserved = 0
    if title:
        title_reserved = Emu(548640)
        tb = slide.shapes.add_textbox(ox, oy, w, title_reserved)
        set_text(tb, title, size=18, bold=True, color=pal.on_bg,
                 font=fonts.header, align=PP_ALIGN.LEFT)
        if desc:
            add_paragraph(tb.text_frame, desc, size=11, color=pal.muted,
                          font=fonts.body, align=PP_ALIGN.LEFT, space_before=2)
        shapes.append(tb)

    # diagram area
    diag_y = oy + title_reserved
    diag_h = h - title_reserved

    # outermost circle diameter = min(w, diag_h)
    outer_d = min(w, diag_h)
    cx = ox + w // 2
    bottom_y = diag_y + diag_h

    # depth ramp: light outer → dark inner
    ramp = depth_ramp(pal.primary, n, light_first=True)

    # Draw outer → inner so inner sits on top
    for i, layer in enumerate(layers):
        # diameter shrinks linearly; innermost is ~25% of outer
        frac = 1.0 - (i / n) * 0.78
        d = max(int(outer_d * frac), Emu(457200))
        circle_x = cx - d // 2
        circle_y = bottom_y - d        # bottom-aligned

        color = ramp[i]
        if (layer.get("tone") == "strong") and i == n - 1:
            color = darken(pal.primary, 0.15)
        circle = slide.shapes.add_shape(MSO_SHAPE.OVAL, circle_x, circle_y, d, d)
        fill_solid(circle, color)
        no_border(circle)
        no_shadow(circle)
        shapes.append(circle)

    # Labels: read top-down in the crescent between concentric rings.
    # For each layer i (outer→inner), place label in the "ring strip"
    # above the next-inner circle's top edge.
    for i, layer in enumerate(layers):
        frac_outer = 1.0 - (i / n) * 0.78
        d_outer = max(int(outer_d * frac_outer), Emu(457200))
        outer_top = bottom_y - d_outer
        if i < n - 1:
            frac_inner = 1.0 - ((i + 1) / n) * 0.78
            d_inner = max(int(outer_d * frac_inner), Emu(457200))
            inner_top = bottom_y - d_inner
            label_band_h = inner_top - outer_top
            label_y = outer_top + max((label_band_h - Emu(228600)) // 2, Emu(45720))
        else:
            # innermost: label centered inside
            d_inner = max(int(outer_d * (1.0 - (n / n) * 0.78)), Emu(457200))
            label_y = bottom_y - d_outer // 2 - Emu(114300)

        text = layer.get("title") or layer.get("label") or ""
        text_color = pal.bg if i >= n - 2 else pal.on_bg
        # Label box: roomy enough to also carry an optional `desc` line below.
        tb_h = Emu(548640) if layer.get("desc") else Emu(274320)
        tb = slide.shapes.add_textbox(
            cx - d_outer // 2, label_y, d_outer, tb_h,
        )
        set_text(tb, text, size=12, bold=True, color=text_color,
                 font=fonts.header, align=PP_ALIGN.CENTER)
        if layer.get("desc"):
            # On dark fills (inner half), use bg (white). On light fills (outer half),
            # use a desaturated on_bg so it reads against the lightened-primary fill.
            desc_color = pal.bg if i >= n - 2 else lighten(pal.on_bg, 0.25)
            add_paragraph(tb.text_frame, str(layer["desc"]),
                          size=9, color=desc_color,
                          font=fonts.body, align=PP_ALIGN.CENTER,
                          space_before=2)
        shapes.append(tb)

    return shapes
