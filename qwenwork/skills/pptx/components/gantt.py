"""Gantt — month columns, grouped tasks, planned-vs-actual dual bars.

Source: ai_slides/docs/gantt.md + renderers/gantt.js

Borrowed design rules:
- Fixed shape: "month capsules + timeline axis + grouped task cards +
  planned/actual dual bars". Caller does NOT pass a title — use a
  separate heading slide-shape above.
- ``columns``: time-axis labels (default 1月..12月). Range count drives x scale.
- ``groups``: ``[{"label": str, "desc": str | None, "tasks": [...]}]``
  Lane rail on the left shows group label.
- ``variant: "ungrouped"`` removes the left lane rail and treats top-level
  ``tasks: [...]`` as a flat list.
- Each task has ``plannedStart/plannedEnd`` and ``actualStart/actualEnd``
  (1-indexed columns). Falls back to ``start/end`` shorthand if neither
  pair is given.
- Planned bar: light tint. Actual bar: solid primary (or ``tone: "dark"``
  for emphasis). Stacked: actual sits on top of planned.
- Legend "实际 / 预计" shown by default; suppress with ``legend=False``.
"""

from __future__ import annotations

from pptx.dml.color import RGBColor

from ._base import (
    Emu, MSO_ANCHOR, MSO_SHAPE, PP_ALIGN, add_paragraph, darken, fill_solid,
    lighten, no_border, no_shadow, set_border, set_text,
)


def add_gantt(
    slide,
    origin: tuple[int, int],
    size: tuple[int, int],
    style,
    *,
    columns: list | None = None,
    groups: list | None = None,
    tasks: list | None = None,
    variant: str = "grouped",
    legend: bool = True,
    legend_labels: tuple[str, str] = ("Actual", "Planned"),
):
    """Add a gantt chart.

    Either ``groups`` (grouped mode) OR ``tasks`` (ungrouped) must be set.
    Task fields: ``label``, ``plannedStart``/``plannedEnd`` and/or
    ``actualStart``/``actualEnd`` (1-indexed columns; or use ``start``/``end``).
    Optional per task: ``tone`` = "soft" | "dark", ``value`` (short label
    rendered inside the actual bar).
    """
    ox, oy = origin
    w, h = size
    pal = style.palette
    fonts = style.fonts

    if columns is None:
        columns = [f"{i+1}月" for i in range(12)]
    n_cols = len(columns)
    if n_cols < 2:
        raise ValueError("gantt requires ≥2 columns")

    is_grouped = variant != "ungrouped" and groups
    flat_tasks = []
    if is_grouped:
        for g in groups:
            for t in g.get("tasks", []):
                flat_tasks.append((g, t))
    else:
        for t in tasks or []:
            flat_tasks.append((None, t))
    if not flat_tasks:
        return []

    # layout regions
    header_h = Emu(411480)
    legend_h = Emu(228600) if legend else 0
    body_y = oy + header_h
    body_h = h - header_h - legend_h
    rail_w = Emu(1645920) if is_grouped else 0     # ~1.8 inch group rail
    chart_x = ox + rail_w
    chart_w = w - rail_w

    shapes: list = []

    # column header (month capsules) + axis
    col_w = chart_w // n_cols
    for i, col in enumerate(columns):
        cx = chart_x + i * col_w
        cap_w = int(col_w * 0.72)
        cap = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            cx + (col_w - cap_w) // 2, oy,
            cap_w, header_h - Emu(91440),
        )
        fill_solid(cap, lighten(pal.muted, 0.7))
        no_border(cap)
        no_shadow(cap)
        cap.text_frame.margin_left = Emu(45720)
        cap.text_frame.margin_right = Emu(45720)
        cap.text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE
        set_text(cap, col, size=10, bold=True, color=pal.on_bg,
                 font=fonts.body, align=PP_ALIGN.CENTER)
        shapes.append(cap)

    # body grid lines
    for i in range(n_cols + 1):
        x = chart_x + i * col_w
        ln = slide.shapes.add_connector(1, x, body_y, x, body_y + body_h)
        ln.line.color.rgb = lighten(pal.muted, 0.6)
        ln.line.width = Emu(6350)
        shapes.append(ln)

    # rows
    n_rows = len(flat_tasks)
    row_h = body_h // max(n_rows, 1)
    # Stack planned (upper) + actual (lower) cleanly with a small visible gap.
    # Previously both bars shared row-center ± 45720 EMU, so they always
    # overlapped — looked like one chunky bar with a halo. Allocate the row's
    # vertical budget so planned sits in the top half, actual in the bottom
    # half, each with a fixed height and a small gap between them.
    stack_gap = Emu(36576)
    bar_total = int(row_h * 0.64)
    planned_bar_h = bar_total * 38 // 100
    actual_bar_h = bar_total - planned_bar_h - stack_gap
    if actual_bar_h < Emu(91440):
        # extremely thin rows — give up the gap, share the budget
        planned_bar_h = bar_total // 2
        actual_bar_h = bar_total // 2
        stack_gap = 0
    stack_top_pad = (row_h - (planned_bar_h + stack_gap + actual_bar_h)) // 2

    # group rail spans
    if is_grouped:
        # group each task to its group index
        cursor = 0
        for g in groups:
            tcount = len(g.get("tasks", []))
            if tcount == 0:
                continue
            g_y = body_y + cursor * row_h
            g_h = tcount * row_h
            rail = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, ox, g_y, rail_w - Emu(91440), g_h)
            fill_solid(rail, lighten(pal.primary, 0.85))
            set_border(rail, lighten(pal.primary, 0.6), 0.5)
            rail.text_frame.margin_left = Emu(137160)
            rail.text_frame.margin_right = Emu(137160)
            rail.text_frame.margin_top = Emu(91440)
            rail.text_frame.word_wrap = True
            set_text(rail, g.get("label", ""), size=11, bold=True,
                     color=pal.primary, font=fonts.header, align=PP_ALIGN.LEFT)
            if g.get("desc"):
                add_paragraph(rail.text_frame, g["desc"], size=9, color=pal.muted,
                              font=fonts.body, align=PP_ALIGN.LEFT, space_before=2)
            shapes.append(rail)
            cursor += tcount

    # task bars + labels
    for i, (group, task) in enumerate(flat_tasks):
        ry = body_y + i * row_h

        # task label inside leftmost extent of its bar group? ai_slides
        # puts label above the actual bar inline at the start column.
        ps, pe = task.get("plannedStart"), task.get("plannedEnd")
        ast, aen = task.get("actualStart"), task.get("actualEnd")
        if ps is None and pe is None and ast is None and aen is None:
            ps, pe = task.get("start"), task.get("end")
            ast, aen = ps, pe

        # planned bar — top half of the row stack
        if ps is not None and pe is not None and pe >= ps:
            x1 = chart_x + col_w * (ps - 1)
            x2 = chart_x + col_w * pe
            pby = ry + stack_top_pad
            pbar = slide.shapes.add_shape(
                MSO_SHAPE.RECTANGLE, x1, pby, max(x2 - x1, Emu(91440)), planned_bar_h,
            )
            fill_solid(pbar, lighten(pal.primary, 0.6))
            no_border(pbar)
            no_shadow(pbar)
            shapes.append(pbar)

        # actual bar — bottom half of the row stack, gap below the planned bar
        if ast is not None and aen is not None and aen >= ast:
            x1 = chart_x + col_w * (ast - 1)
            x2 = chart_x + col_w * aen
            tone = task.get("tone")
            # tone="dark" stays in the primary family (darken 25%) so the
            # legend's "Actual" swatch is still recognizable as the base
            # color. Previously this jumped to pal.on_bg (near-black), which
            # made the legend feel wrong.
            if tone == "dark":
                color = darken(pal.primary, 0.25)
            elif tone == "soft":
                color = lighten(pal.primary, 0.2)
            else:
                color = pal.primary
            aby = ry + stack_top_pad + planned_bar_h + stack_gap
            abar = slide.shapes.add_shape(
                MSO_SHAPE.RECTANGLE, x1, aby, max(x2 - x1, Emu(91440)), actual_bar_h,
            )
            fill_solid(abar, color)
            no_border(abar)
            no_shadow(abar)
            if task.get("value"):
                abar.text_frame.margin_left = Emu(91440)
                abar.text_frame.margin_right = Emu(91440)
                abar.text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE
                set_text(abar, task["value"], size=9, bold=True, color=pal.bg,
                         font=fonts.body, align=PP_ALIGN.LEFT)
            shapes.append(abar)

        # task label above the row, leftmost
        lbl_tb = slide.shapes.add_textbox(chart_x, ry, Emu(2286000), Emu(228600))
        set_text(lbl_tb, task["label"], size=10, color=pal.on_bg,
                 font=fonts.body, align=PP_ALIGN.LEFT)
        shapes.append(lbl_tb)

    # legend
    if legend:
        lg_y = oy + h - legend_h
        # actual swatch
        sw_d = Emu(137160)
        sw1 = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, chart_x, lg_y + Emu(45720), sw_d, sw_d)
        fill_solid(sw1, pal.primary)
        no_border(sw1)
        shapes.append(sw1)
        t1 = slide.shapes.add_textbox(chart_x + sw_d + Emu(45720), lg_y, Emu(914400), legend_h)
        set_text(t1, legend_labels[0], size=9, color=pal.muted, font=fonts.body,
                 align=PP_ALIGN.LEFT)
        shapes.append(t1)
        sw2_x = chart_x + Emu(1097280)
        sw2 = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, sw2_x, lg_y + Emu(45720), sw_d, sw_d)
        fill_solid(sw2, lighten(pal.primary, 0.6))
        no_border(sw2)
        shapes.append(sw2)
        t2 = slide.shapes.add_textbox(sw2_x + sw_d + Emu(45720), lg_y, Emu(914400), legend_h)
        set_text(t2, legend_labels[1], size=9, color=pal.muted, font=fonts.body,
                 align=PP_ALIGN.LEFT)
        shapes.append(t2)

    return shapes
