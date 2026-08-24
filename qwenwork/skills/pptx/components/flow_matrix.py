"""Flow matrix — architecture diagram with layered rows + side labels.

Source: ai_slides/docs/flow-matrix.md + renderers/flow-matrix.js

Borrowed design rules:
- Used for "multi-layer architecture / business ecosystem / capability
  structure / system composition / rule decision chain".
- NOT a generic grid of cards. ai_slides explicit rule: "适合内容必须有
  明确层级，例如输入层 / 理解层 / 匹配层 / 输出层; 如果只是普通清单, 不应选择架构图."
- Structure: ``rows``, each with ``leftLabel`` (layer name) + ``nodes``
  (2-4 cells). >4 nodes per row → wrap into multiple rows; we enforce
  cap at 5 but warn at 4+.
- Optional top ``title`` and a bottom ``platform`` strip (the "底部
  平台/链路" element from the spec).
- Each row has a tinted band background; nodes are filled cards with
  title + optional description.
- Color: rows share band tint; nodes inherit per-row depth.
"""

from __future__ import annotations

from pptx.dml.color import RGBColor

from ._base import (
    Emu, MSO_ANCHOR, MSO_SHAPE, PP_ALIGN, add_paragraph, depth_ramp,
    fill_solid, lighten, no_border, no_shadow, set_border, set_text,
)


def add_flow_matrix(
    slide,
    origin: tuple[int, int],
    size: tuple[int, int],
    rows: list,
    style,
    *,
    title: str | None = None,
    platform: dict | None = None,
):
    """Add a layered flow-matrix / architecture diagram.

    ``rows``: ``[{"leftLabel": str (or "label"|"title"),
                 "nodes": [{"title": str, "desc": str | None}, ...]}, ...]``
              2-4 nodes per row (5 max).
    ``platform``: ``{"label": str, "desc": str | None}`` optional bottom strip.
    """
    ox, oy = origin
    w, h = size
    pal = style.palette
    fonts = style.fonts
    if not rows:
        return []

    shapes: list = []

    # title strip
    title_reserved = 0
    if title:
        title_reserved = Emu(457200)
        tb = slide.shapes.add_textbox(ox, oy, w, title_reserved)
        set_text(tb, title, size=16, bold=True, color=pal.on_bg,
                 font=fonts.header, align=PP_ALIGN.LEFT)
        shapes.append(tb)

    # bottom platform strip
    plat_reserved = Emu(548640) if platform else 0

    body_y = oy + title_reserved
    body_h = h - title_reserved - plat_reserved
    n = len(rows)
    row_gap = Emu(91440)
    row_h = (body_h - row_gap * (n - 1)) // n

    rail_w = Emu(1645920)   # ~1.8"
    cell_x = ox + rail_w + Emu(91440)
    cell_band_w = w - rail_w - Emu(91440)

    band_ramp = depth_ramp(pal.primary, n, light_first=True)

    # Shared column grid across all rows: cell widths are determined by the
    # MAX node count across the deck, so a 2-cell row's cells line up with
    # the first 2 columns of a 3-cell row. Anything else makes rows look
    # like they're stretching to fill width inconsistently.
    max_nodes = max((len(r.get("nodes", [])[:5]) for r in rows), default=1)
    max_nodes = max(max_nodes, 1)
    inner_gap = Emu(91440)
    grid_cell_w = (cell_band_w - inner_gap * (max_nodes + 1)) // max_nodes

    for ri, row in enumerate(rows):
        y = body_y + ri * (row_h + row_gap)
        band_color = lighten(band_ramp[ri], 0.7)

        # row band (subtle bg behind nodes)
        band = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, cell_x, y, cell_band_w, row_h)
        fill_solid(band, band_color)
        no_border(band)
        no_shadow(band)
        shapes.append(band)

        # left label rail
        rail = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, ox, y, rail_w, row_h)
        fill_solid(rail, band_ramp[ri])
        no_border(rail)
        no_shadow(rail)
        rail.text_frame.margin_left = Emu(137160)
        rail.text_frame.margin_right = Emu(137160)
        rail.text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE
        rail.text_frame.word_wrap = True
        label = row.get("leftLabel") or row.get("label") or row.get("title") or ""
        text_color = pal.bg if ri >= max(1, n // 2) else pal.on_bg
        set_text(rail, label, size=12, bold=True, color=text_color,
                 font=fonts.header, align=PP_ALIGN.LEFT)
        shapes.append(rail)

        # node cells inside band — pinned to the shared column grid
        nodes = row.get("nodes", [])[:5]
        if not nodes:
            continue
        cell_h = row_h - Emu(91440)
        cy = y + (row_h - cell_h) // 2
        for ni, node in enumerate(nodes):
            nx = cell_x + inner_gap + ni * (grid_cell_w + inner_gap)
            card = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, nx, cy, grid_cell_w, cell_h)
            fill_solid(card, pal.bg)
            set_border(card, lighten(pal.primary, 0.4), 0.75)
            no_shadow(card)
            card.text_frame.margin_left = Emu(91440)
            card.text_frame.margin_right = Emu(91440)
            card.text_frame.margin_top = Emu(60960)
            card.text_frame.word_wrap = True
            set_text(card, node.get("title", ""), size=12, bold=True,
                     color=pal.primary, font=fonts.header, align=PP_ALIGN.LEFT)
            if node.get("desc"):
                add_paragraph(card.text_frame, node["desc"], size=10,
                              color=pal.on_bg, font=fonts.body,
                              align=PP_ALIGN.LEFT, space_before=3)
            shapes.append(card)

    # platform strip (bottom)
    if platform:
        py = oy + h - plat_reserved
        plat = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, ox, py, w, plat_reserved - Emu(45720))
        fill_solid(plat, pal.on_bg)
        no_border(plat)
        no_shadow(plat)
        plat.text_frame.margin_left = Emu(228600)
        plat.text_frame.margin_right = Emu(228600)
        plat.text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE
        set_text(plat, platform.get("label", ""), size=12, bold=True,
                 color=pal.bg, font=fonts.header, align=PP_ALIGN.LEFT)
        if platform.get("desc"):
            add_paragraph(plat.text_frame, platform["desc"], size=10,
                          color=lighten(pal.bg, 0.05), font=fonts.body,
                          align=PP_ALIGN.LEFT, space_before=2)
        shapes.append(plat)

    return shapes
