"""Private chrome helper shared by presets · v1 原样搬 · 不改动"""
from __future__ import annotations
from ..engine import text, line
from ..palettes import Palette

# 全局画布尺寸 · 与 v1 一致
W, H = 900, 336


def _draw_chrome(p, palette: Palette, data, kicker: str):
    """Draw 6-layer chrome using palette + data attrs. duck-type · 只读 data 上的字段"""
    figure_title = getattr(data, "figure_title", "")
    encoding_note = getattr(data, "encoding_note", "")
    figure_caption = getattr(data, "figure_caption", "")
    source = getattr(data, "source", "")

    p.append(text(20, 24, kicker,
                  size=9, color=palette.primary,
                  family=palette.mono_family, bold=True,
                  letter=palette.kicker_letter_spacing))
    p.append(text(20, 48, figure_title, size=17, color=palette.ink,
                  family=palette.head_family, bold=True,
                  italic=palette.title_style.endswith("italic")))
    if encoding_note:
        p.append(text(880, 24, encoding_note, size=9,
                      color=palette.gray, family=palette.body_family,
                      italic=True, anchor="end"))
    p.append(line(20, 60, W - 20, 60, color=palette.hair, w=1))
    p.append(line(20, 300, W - 20, 300, color=palette.hair, w=1))
    if figure_caption:
        p.append(text(20, 316, figure_caption, size=9,
                      color=palette.gray, family=palette.body_family,
                      italic=True))
    if source:
        p.append(text(880, 328, source, size=8,
                      color=palette.gray, family=palette.mono_family,
                      letter=1.2, anchor="end"))
