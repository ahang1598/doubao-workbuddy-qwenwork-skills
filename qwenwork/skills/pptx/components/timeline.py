"""Timeline / milestone — date axis + phase bars + delivery cards + exit gates.

Source: ai_slides/docs/milestone.md + renderers/milestone.js

Borrowed design rules:
- Three horizontal bands stacked vertically:
  1. ``scale``: date axis with tick marks at each phase boundary
  2. ``bars``:  phase bars showing duration; ``tone`` = strong | dark
  3. ``cards``: per-phase delivery card with kicker + title + deliverables
     list + exit-gate footer
- ``--phase-count`` drives column count (1 col per phase). 3-6 typical.
- Each phase has explicit ``label`` (kicker), ``title``, ``deliverables``
  (bullet list), ``exit_gate`` (acceptance criterion for advancing).
- Dates supplied as boundary array (n+1 dates for n phases) OR derived
  from per-phase ``duration`` if dates absent.
- ai_slides distinguishes ``milestone`` (has dates + gates + cards)
  from ``progress`` (only stages). We're milestone-flavored — this is
  more useful as a "timeline" for our consumers.
"""

from __future__ import annotations

from pptx.dml.color import RGBColor

from ._base import (
    Emu, MSO_ANCHOR, MSO_SHAPE, PP_ALIGN, add_paragraph, col_edges, fill_solid,
    lighten, no_border, no_shadow, set_border, set_text,
)


def add_timeline(
    slide,
    origin: tuple[int, int],
    size: tuple[int, int],
    phases: list,
    style,
    *,
    boundary_dates: list | None = None,
):
    """Add a milestone-style timeline.

    ``phases``: ``[{"label": str, "title": str, "duration": str | None,
                   "tone": "strong" | "dark" | None,
                   "deliverables": [str, ...],
                   "exit_gate": str | None}, ...]``  (3-6 recommended)
    ``boundary_dates``: ``[str, ...]`` length = ``len(phases) + 1`` for
                       calendar markers; if omitted, ticks are unlabeled.
    """
    ox, oy = origin
    w, h = size
    pal = style.palette
    fonts = style.fonts
    n = len(phases)
    if n == 0:
        return []

    # band heights
    scale_h = Emu(457200) if boundary_dates else Emu(228600)
    bars_h = Emu(411480)
    cards_h = h - scale_h - bars_h - Emu(137160)
    if cards_h < Emu(1097280):
        cards_h = h - scale_h - bars_h
        # if still too cramped, drop card content
    gap_v = Emu(137160)

    edges = col_edges(ox, w, n)
    shapes: list = []

    # --- scale band ---
    axis_y = oy + scale_h - Emu(137160)
    axis = slide.shapes.add_connector(1, ox, axis_y, ox + w, axis_y)
    axis.line.color.rgb = pal.muted
    axis.line.width = Emu(19050)
    shapes.append(axis)

    # ticks + boundary dates (n+1 boundaries)
    for i in range(n + 1):
        tick_x = edges[i]
        # vertical tick
        tk = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,
                                    tick_x - Emu(7620), axis_y - Emu(91440),
                                    Emu(15240), Emu(182880))
        fill_solid(tk, pal.primary)
        no_border(tk)
        shapes.append(tk)
        # date label above tick
        if boundary_dates and i < len(boundary_dates):
            db = slide.shapes.add_textbox(
                tick_x - Emu(457200), oy,
                Emu(914400), scale_h - Emu(228600),
            )
            db.text_frame.vertical_anchor = MSO_ANCHOR.BOTTOM
            set_text(db, str(boundary_dates[i]),
                     size=10, bold=True, color=pal.muted,
                     font=fonts.body, align=PP_ALIGN.CENTER)
            shapes.append(db)

    # --- bars band ---
    bars_y = oy + scale_h
    for i, phase in enumerate(phases):
        bx = edges[i] + Emu(45720)
        bw = edges[i + 1] - edges[i] - Emu(91440)
        tone = phase.get("tone")
        if tone == "dark":
            color = pal.on_bg
        elif tone == "strong":
            color = pal.primary
        else:
            color = lighten(pal.primary, 0.3)
        bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, bx, bars_y, bw, bars_h)
        fill_solid(bar, color)
        no_border(bar)
        no_shadow(bar)
        bar.text_frame.margin_left = Emu(137160)
        bar.text_frame.margin_right = Emu(137160)
        bar.text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE
        duration = phase.get("duration") or f"阶段{i+1}"
        set_text(bar, duration, size=11, bold=True, color=pal.bg,
                 font=fonts.body, align=PP_ALIGN.CENTER)
        shapes.append(bar)

    # --- cards band ---
    cards_y = bars_y + bars_h + gap_v
    for i, phase in enumerate(phases):
        cx = edges[i] + Emu(45720)
        cw = edges[i + 1] - edges[i] - Emu(91440)
        card = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, cx, cards_y, cw, cards_h)
        fill_solid(card, pal.bg)
        set_border(card, lighten(pal.muted, 0.3), 0.75)
        no_shadow(card)
        card.text_frame.margin_left = Emu(137160)
        card.text_frame.margin_right = Emu(137160)
        card.text_frame.margin_top = Emu(91440)
        card.text_frame.vertical_anchor = MSO_ANCHOR.TOP
        card.text_frame.word_wrap = True

        if phase.get("label"):
            set_text(card, str(phase["label"]).upper(),
                     size=9, bold=True, color=pal.accent,
                     font=fonts.body, align=PP_ALIGN.LEFT)
            add_paragraph(card.text_frame, phase["title"],
                          size=12, bold=True, color=pal.on_bg,
                          font=fonts.header, align=PP_ALIGN.LEFT, space_before=2)
        else:
            set_text(card, phase["title"],
                     size=12, bold=True, color=pal.on_bg,
                     font=fonts.header, align=PP_ALIGN.LEFT)

        if phase.get("deliverables"):
            add_paragraph(card.text_frame, "交付清单" if _looks_chinese(phase.get("title", "")) else "Deliverables",
                          size=9, bold=True, color=pal.muted,
                          font=fonts.body, align=PP_ALIGN.LEFT, space_before=8)
            for item in phase["deliverables"]:
                add_paragraph(card.text_frame, f"·  {item}",
                              size=10, color=pal.on_bg, font=fonts.body,
                              align=PP_ALIGN.LEFT, space_before=2)

        if phase.get("exit_gate"):
            gate_label = "退出门槛" if _looks_chinese(phase.get("title", "")) else "Exit gate"
            add_paragraph(card.text_frame, f"{gate_label}  {phase['exit_gate']}",
                          size=9, italic=True, color=pal.primary,
                          font=fonts.body, align=PP_ALIGN.LEFT, space_before=8)

        shapes.append(card)

    return shapes


def _looks_chinese(text: str) -> bool:
    for ch in text or "":
        if "\u4e00" <= ch <= "\u9fff":
            return True
    return False
