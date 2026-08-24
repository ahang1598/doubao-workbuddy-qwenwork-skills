"""Radar — multi-dimensional score chart with side notes.

Source: ai_slides/docs/radar.md + renderers/radar.js

Borrowed design rules:
- 4-6 dimensions (recommended). Score range 0-100.
- Wide container (col>=12, row>=12): chart left, notes right
- Notes panel: one line per dim, format "{dim}: {score}  {desc}"
  (we don't split dim/desc/score across three columns — ai_slides
  rule "注释不要再拆标题、描述、数值三层")
- Polygon fill is the brand color at ~28% opacity (true ``<a:alpha>``
  transparency, so concentric rings + axes read through the area), with a
  solid 1.5pt brand-color border and vertex dots. No shadow.
- Concentric grid: 4 rings; axis lines from center to each vertex
- Dimension labels rendered outside the outermost ring
"""

from __future__ import annotations

import math

from pptx.dml.color import RGBColor

from ._base import (
    Emu, MSO_ANCHOR, MSO_SHAPE, PP_ALIGN, add_paragraph, fill_solid,
    lighten, no_border, no_fill, no_shadow, set_border, set_fill_alpha,
    set_text,
)


def add_radar(
    slide,
    origin: tuple[int, int],
    size: tuple[int, int],
    dimensions: list,
    style,
    *,
    rings: int = 4,
    max_score: float = 100.0,
    show_notes: bool | None = None,
):
    """Add a radar / spider chart with optional side-notes panel.

    ``dimensions``: ``[{"name": str, "score": float, "desc": str | None}, ...]``
                    4-6 entries recommended.
    """
    ox, oy = origin
    w, h = size
    pal = style.palette
    fonts = style.fonts
    n = len(dimensions)
    if n < 3:
        raise ValueError("radar requires ≥3 dimensions")

    # auto: notes shown when container is wider than ~1.4x its height
    if show_notes is None:
        show_notes = w > int(h * 1.3)

    if show_notes:
        chart_w = int(w * 0.62)
        notes_x = ox + chart_w + Emu(228600)
        notes_w = w - chart_w - Emu(228600)
    else:
        chart_w = w
        notes_x = ox
        notes_w = 0

    chart_h = h
    cx = ox + chart_w // 2
    cy = oy + chart_h // 2
    radius = min(chart_w, chart_h) // 2 - Emu(548640)
    if radius < Emu(457200):
        radius = Emu(457200)

    shapes: list = []

    def polar_pt(theta, r):
        return (cx + int(r * math.sin(theta)), cy - int(r * math.cos(theta)))

    # rings
    for k in range(1, rings + 1):
        rr = radius * k // rings
        ring = slide.shapes.add_shape(MSO_SHAPE.OVAL, cx - rr, cy - rr, rr * 2, rr * 2)
        no_fill(ring)
        set_border(ring, lighten(pal.muted, 0.4), 0.5)
        no_shadow(ring)
        shapes.append(ring)

    # axes + labels
    for i, dim in enumerate(dimensions):
        theta = 2 * math.pi * i / n
        ax, ay = polar_pt(theta, radius)
        line = slide.shapes.add_connector(1, cx, cy, ax, ay)
        line.line.color.rgb = lighten(pal.muted, 0.3)
        line.line.width = Emu(6350)
        shapes.append(line)

        lx, ly = polar_pt(theta, radius + Emu(228600))
        lbl_w = Emu(914400)
        lbl_h = Emu(228600)
        tb = slide.shapes.add_textbox(lx - lbl_w // 2, ly - lbl_h // 2, lbl_w, lbl_h)
        set_text(tb, dim["name"], size=10, bold=True, color=pal.on_bg,
                 font=fonts.body, align=PP_ALIGN.CENTER)
        shapes.append(tb)

    # data polygon as freeform
    points = []
    for i, dim in enumerate(dimensions):
        theta = 2 * math.pi * i / n
        score = max(0.0, min(float(max_score), float(dim["score"])))
        r = int(radius * score / max_score)
        points.append(polar_pt(theta, r))

    if points:
        builder = slide.shapes.build_freeform(points[0][0], points[0][1], scale=1.0)
        if len(points) > 1:
            builder.add_line_segments([(px, py) for px, py in points[1:]], close=True)
        poly = builder.convert_to_shape()
        # True semi-transparent area fill (not a tint) so the rings + axes
        # read through the polygon — the professional radar look. No shadow.
        fill_solid(poly, pal.primary)
        set_fill_alpha(poly, 28)
        no_shadow(poly)
        set_border(poly, pal.primary, 1.5)
        shapes.append(poly)

        # vertex dots
        dot_d = Emu(91440)
        for px, py in points:
            dot = slide.shapes.add_shape(MSO_SHAPE.OVAL, px - dot_d // 2, py - dot_d // 2, dot_d, dot_d)
            fill_solid(dot, pal.primary)
            no_border(dot)
            no_shadow(dot)
            shapes.append(dot)

    # side notes panel
    if show_notes and notes_w > Emu(685800):
        notes_tb = slide.shapes.add_textbox(notes_x, oy + Emu(228600), notes_w, chart_h - Emu(457200))
        notes_tb.text_frame.word_wrap = True
        first = True
        for dim in dimensions:
            line = f"{dim['name']}  ·  {int(round(float(dim['score'])))}"
            desc = dim.get("desc") or dim.get("copy")
            if first:
                set_text(notes_tb, line, size=12, bold=True, color=pal.primary,
                         font=fonts.header, align=PP_ALIGN.LEFT)
                first = False
            else:
                add_paragraph(notes_tb.text_frame, line, size=12, bold=True,
                              color=pal.primary, font=fonts.header,
                              align=PP_ALIGN.LEFT, space_before=10)
            if desc:
                add_paragraph(notes_tb.text_frame, desc, size=10, color=pal.muted,
                              font=fonts.body, align=PP_ALIGN.LEFT, space_before=2)
        shapes.append(notes_tb)

    return shapes
