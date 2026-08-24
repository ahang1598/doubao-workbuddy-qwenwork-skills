"""Flywheel — center asset + indexed orbital nodes.

Source: ai_slides/docs/flywheel.md + renderers/flywheel.js

Borrowed design rules:
- Center has two lines: ``center.title`` (main label) + ``center.label``
  (CORE ASSET / kicker in caps)
- 3-6 nodes around an orbit ring
- Each node has 3 text levels: ``label`` (accent kicker with index),
  ``title`` (main heading), ``desc`` (one-line explanation)
- ``startAngle`` default -90° (first node at top), ``direction`` cw/ccw
- Node title length: 8-14 CJK chars; desc 1 line
- Arrow glyphs between nodes (we draw curved arc segments)
- Node count drives radial layout — more nodes need wider container
"""

from __future__ import annotations

import math

from pptx.dml.color import RGBColor

from ._base import (
    Emu, MSO_ANCHOR, MSO_SHAPE, PP_ALIGN, add_paragraph, fill_solid,
    lighten, no_border, no_shadow, set_border, set_text,
)


def add_flywheel(
    slide,
    origin: tuple[int, int],
    size: tuple[int, int],
    center: dict,
    nodes: list,
    style,
    *,
    start_angle_deg: float = -90.0,
    direction: str = "clockwise",
):
    """Add a flywheel.

    ``center``: ``{"title": str, "label": str | None}``
    ``nodes``: ``[{"label": str, "title": str, "desc": str | None, "index": int | None}, ...]``
              3-6 items.
    """
    ox, oy = origin
    w, h = size
    pal = style.palette
    fonts = style.fonts
    n = len(nodes)
    if n < 3 or n > 6:
        raise ValueError("flywheel requires 3-6 nodes")

    cx = ox + w // 2
    cy = oy + h // 2

    # Size cards relative to inter-node arc distance so they never overlap.
    # Working backward: distance between adjacent node centers along the orbit
    # ring = 2 * orbit_r * sin(pi/n). We need card_w + safety_gap <= that.
    # Use a target where card_w ≈ 0.85 * inter_node_distance.
    radius_cap = min(w, h) // 2                       # absolute cap
    # First-pass guess for card size (~ 1/3 of short side), constrained by n.
    node_card_w = min(w, h) // 3
    node_card_h = int(node_card_w * 0.55)
    # orbit_r so the cards just fit inside the body box.
    orbit_r = radius_cap - max(node_card_w, node_card_h) // 2 - Emu(91440)
    if orbit_r < Emu(457200):
        orbit_r = Emu(457200)
    # Tighten card_w if inter-node distance is smaller than card_w + gap.
    inter = int(2 * orbit_r * math.sin(math.pi / n))
    max_card_w = int(inter * 0.85)
    if node_card_w > max_card_w:
        node_card_w = max(Emu(1500000), max_card_w)
        node_card_h = int(node_card_w * 0.55)
        # Recompute orbit_r with the (possibly smaller) card size.
        orbit_r = radius_cap - max(node_card_w, node_card_h) // 2 - Emu(91440)

    shapes: list = []

    # orbit ring (dashed-like via thin solid)
    ring_d = orbit_r * 2
    ring = slide.shapes.add_shape(MSO_SHAPE.OVAL, cx - orbit_r, cy - orbit_r, ring_d, ring_d)
    ring.fill.background()
    set_border(ring, lighten(pal.primary, 0.6), 0.75)
    no_shadow(ring)
    shapes.append(ring)

    # center disc — size needs to comfortably fit `center.title`. Empirically
    # min(w, h)//4 is too small for 18pt multi-word titles; use larger disc
    # and a slightly smaller font so a single newline rarely wraps mid-word.
    center_d = min(w, h) * 32 // 100
    # Auto-shrink the title font if the disc is small.
    title_text = str(center["title"])
    longest_token = max((len(t) for t in title_text.replace("\n", " ").split()), default=0)
    # Heuristic: bold sans-serif ~ 0.62*pt per char in EMU (1pt = 12700 EMU).
    # At base size 16pt: ~ 126000 EMU per char width.
    avail = center_d - Emu(182880) * 2
    base_size = 16
    px_per_char = int(0.62 * base_size * 12700)
    fit_size = base_size
    if longest_token * px_per_char > avail:
        # shrink proportionally, clamp to [10, 16]
        fit_size = max(10, int(base_size * avail / max(1, longest_token * px_per_char)))
    center_shape = slide.shapes.add_shape(
        MSO_SHAPE.OVAL,
        cx - center_d // 2, cy - center_d // 2,
        center_d, center_d,
    )
    fill_solid(center_shape, pal.primary)
    no_border(center_shape)
    no_shadow(center_shape)
    center_shape.text_frame.margin_left = Emu(91440)
    center_shape.text_frame.margin_right = Emu(91440)
    center_shape.text_frame.word_wrap = True
    center_shape.text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE

    set_text(
        center_shape, center["title"],
        size=fit_size, bold=True, color=pal.bg,
        font=fonts.header, align=PP_ALIGN.CENTER,
    )
    if center.get("label"):
        add_paragraph(
            center_shape.text_frame, str(center["label"]).upper(),
            size=9, bold=True, color=lighten(pal.bg, 0.05),
            font=fonts.body, align=PP_ALIGN.CENTER, space_before=4,
        )
    shapes.append(center_shape)

    # node cards
    sign = 1 if direction == "clockwise" else -1
    start_rad = math.radians(start_angle_deg)
    for i, node in enumerate(nodes):
        theta = start_rad + sign * (2 * math.pi * i / n)
        nx = cx + int(orbit_r * math.cos(theta)) - node_card_w // 2
        ny = cy + int(orbit_r * math.sin(theta)) - node_card_h // 2

        card = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, nx, ny, node_card_w, node_card_h)
        fill_solid(card, pal.bg)
        set_border(card, lighten(pal.primary, 0.5), 1.0)
        no_shadow(card)
        card.text_frame.margin_left = Emu(91440)
        card.text_frame.margin_right = Emu(91440)
        card.text_frame.margin_top = Emu(60960)
        card.text_frame.word_wrap = True

        idx = node.get("index") or (i + 1)
        kicker_text = f"{idx:02d}  {node.get('label', '').upper()}"
        set_text(card, kicker_text, size=9, bold=True, color=pal.accent,
                 font=fonts.body, align=PP_ALIGN.LEFT)
        add_paragraph(
            card.text_frame, node["title"],
            size=12, bold=True, color=pal.on_bg,
            font=fonts.header, align=PP_ALIGN.LEFT, space_before=3,
        )
        if node.get("desc"):
            add_paragraph(
                card.text_frame, node["desc"],
                size=9, color=pal.muted, font=fonts.body,
                align=PP_ALIGN.LEFT, space_before=2,
            )
        shapes.append(card)

    return shapes
