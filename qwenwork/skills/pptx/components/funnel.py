"""Funnel — caller-controlled per-step width, label/value distinction, optional note.

Source: ai_slides/docs/funnel.md + renderers/funnel.js

Borrowed design rules:
- Each step has explicit ``width`` (CSS ``--w`` in ai_slides, like
  ``"26%"``). NOT auto-linear-tapered — the *caller* controls funnel
  shape. We accept either a percent string ``"26%"`` or a float 0-1.
- Steps render TOP-TO-BOTTOM, narrowest at top → widest at bottom
  (note: ai_slides goes narrow→wide, opposite of a classic Western
  conversion funnel; we follow ai_slides).
- Each step has ``label`` (small/grey) + ``value`` (strong heading).
- Depth coloring: ``data-step="1..4"`` ramps light→dark. We use
  ``depth_ramp`` with the brand color.
- Optional ``note`` rendered as italic footer.
- Optional ``title`` at the top.
"""

from __future__ import annotations

from pptx.dml.color import RGBColor

from ._base import (
    Emu, MSO_ANCHOR, MSO_SHAPE, PP_ALIGN, add_paragraph, darken, depth_ramp,
    fill_solid, no_border, no_shadow, set_text,
)


def add_funnel(
    slide,
    origin: tuple[int, int],
    size: tuple[int, int],
    steps: list,
    style,
    *,
    title: str | None = None,
    note: str | None = None,
    orientation: str = "narrow_top",   # "narrow_top" (ai_slides) | "narrow_bottom" (classic)
):
    """Add a funnel with caller-controlled per-step widths.

    ``steps``: ``[{"label": str, "value": str, "width": str | float}, ...]``
               ``width`` accepts ``"26%"`` or ``0.26``.
    """
    ox, oy = origin
    w, h = size
    pal = style.palette
    fonts = style.fonts
    n = len(steps)
    if n == 0:
        return []

    shapes: list = []
    cursor_y = oy
    title_reserved = 0
    if title:
        title_reserved = Emu(411480)
        tb = slide.shapes.add_textbox(ox, cursor_y, w, title_reserved)
        set_text(tb, title, size=16, bold=True, color=pal.on_bg,
                 font=fonts.header, align=PP_ALIGN.LEFT)
        shapes.append(tb)
        cursor_y += title_reserved

    note_reserved = Emu(365760) if note else 0
    body_h = h - title_reserved - note_reserved

    gap = Emu(91440)
    step_h = (body_h - gap * (n - 1)) // n

    ramp = depth_ramp(pal.primary, n, light_first=True)
    # If classic orientation, reverse ramp (top wide, bottom narrow, top darkest)
    if orientation == "narrow_bottom":
        ramp = list(reversed(ramp))

    for i, step in enumerate(steps):
        # parse width: "26%" → 0.26; 0.26 stays; "0.26" → 0.26
        raw_w = step.get("width", 1.0)
        if isinstance(raw_w, str):
            s = raw_w.strip().rstrip("%")
            try:
                wf = float(s) / (100.0 if "%" in raw_w else 1.0)
            except ValueError:
                wf = 1.0
        else:
            wf = float(raw_w)
            if wf > 1.0:
                wf = wf / 100.0
        wf = max(0.05, min(1.0, wf))

        if orientation == "narrow_bottom":
            wf_eff = 1.0 - ((1.0 - wf) * (i / max(n - 1, 1))) if False else wf
        seg_w = int(w * wf)
        sx = ox + (w - seg_w) // 2
        sy = cursor_y + i * (step_h + gap)

        seg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, sx, sy, seg_w, step_h)
        fill_solid(seg, ramp[i])
        no_border(seg)
        no_shadow(seg)
        seg.text_frame.margin_left = Emu(228600)
        seg.text_frame.margin_right = Emu(228600)
        seg.text_frame.margin_top = Emu(91440)
        seg.text_frame.margin_bottom = Emu(91440)
        seg.text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE
        seg.text_frame.word_wrap = True

        # text color: lighten ramp = darker text, dark fill = light text.
        # NOTE: pal.muted on lightened-primary is low contrast (similar tones);
        # use on_bg for labels on light fills so the label stays legible.
        is_dark = i >= max(1, n // 2)
        label_color = pal.bg if is_dark else pal.on_bg
        value_color = pal.bg if is_dark else pal.primary

        set_text(seg, step.get("label", ""), size=10, bold=True,
                 color=label_color, font=fonts.body, align=PP_ALIGN.CENTER)
        if step.get("value"):
            add_paragraph(seg.text_frame, str(step["value"]), size=14, bold=True,
                          color=value_color, font=fonts.header,
                          align=PP_ALIGN.CENTER, space_before=4)
        shapes.append(seg)

    if note:
        note_tb = slide.shapes.add_textbox(ox, oy + h - note_reserved, w, note_reserved)
        set_text(note_tb, note, size=10, italic=True, color=pal.muted,
                 font=fonts.body, align=PP_ALIGN.LEFT)
        shapes.append(note_tb)

    return shapes
