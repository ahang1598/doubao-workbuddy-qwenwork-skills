"""
Chrome · 6 层 in-figure chrome helper

layers:
    1. kicker · 图上方 § 标签 (mono·9pt·primary)
    2. figure_title · 主标题 (serif bold·17pt·ink)
    3. encoding_note · 顶右侧 encoding 说明 (italic·8pt·gray)  |  legend_chips (dandelion mode)
    4. hairline (top) · 分隔线 (y=60)
    4b. figure_number · "FIGURE 26" small kicker · y=70 · mono 8pt gray (dandelion mode)
        · encoding_note fallback 到 y=70 右 · 与 figure_number 明确不重叠
    5. hairline (bottom) · 分隔线 · legacy y=300 · dandelion mode y=278
    6. how_to_read 4-step band · y=[280, 300] (dandelion mode)
    7. figure_caption · y=316 (italic·9pt·gray)
    8. source · y=328 (mono·8pt·gray·letter=1.2)

body 区域：
    legacy mode · y=[66, 296]
    dandelion mode (figure_number/how_to_read/legend_chips) · y=[76, 274]

用法：
    from svg_relation_lib.chrome import top_chrome, bottom_chrome, BODY
    parts = []
    parts.append(top_chrome(kicker="§ ROOT CAUSE · FISHBONE",
                             title="Cloud gaming latency root cause",
                             encoding_note="6 category × 3 sub-cause",
                             palette=GS_RESEARCH))
    parts.append(render_body(data, palette))   # 内容 · 900×336 body
    parts.append(bottom_chrome(caption="6 category · post-incident",
                                source="Source · SRE incident review",
                                palette=GS_RESEARCH))
    svg = svg_wrapper("".join(parts))

Dandelion 增强用法 (可选参数, 老 preset 不传时输出 byte-identical)：
    parts.append(top_chrome(kicker="§ ARCHITECTURE",
                             title="System architecture",
                             figure_number="FIGURE 26",
                             legend_chips=[("#003A84", "Sync"), ("#C8AA6E", "Async")],
                             palette=palette))
    parts.append(bottom_chrome(caption="", source="Source · SRE",
                                how_to_read=[
                                    ("1", "Direction", "top-to-bottom flow"),
                                    ("2", "Branches", "diamond gates split"),
                                    ("3", "Loops", "reverse arrow"),
                                    ("4", "Shapes", "rect=step, oval=terminal"),
                                ],
                                palette=palette))
"""
from __future__ import annotations
from typing import NamedTuple, Optional, Sequence, Tuple
from .engine import text, line, rect, circle, CANVAS_W
from .palettes import Palette


class BodyBox(NamedTuple):
    """chrome 内部预留给 pattern 主视觉的 body 区域"""
    x0: int = 20
    y0: int = 66
    x1: int = 880
    y1: int = 296

    @property
    def w(self) -> int:
        return self.x1 - self.x0

    @property
    def h(self) -> int:
        return self.y1 - self.y0

    @property
    def cx(self) -> int:
        return (self.x0 + self.x1) // 2

    @property
    def cy(self) -> int:
        return (self.y0 + self.y1) // 2


BODY = BodyBox()
# body_dandelion · 上下让出 figure_number(y=70) 和 how_to_read(y=280-300)
BODY_DANDELION = BodyBox(x0=20, y0=76, x1=880, y1=274)


def top_chrome(
    kicker: str,
    title: str,
    palette: Palette,
    encoding_note: str = "",
    x_margin: int = 20,
    figure_number: Optional[str] = None,
    legend_chips: Optional[Sequence[Tuple[str, str]]] = None,
) -> str:
    """kicker + title + encoding_note/legend_chips + top hairline + figure_number

    Backwards-compatible: when figure_number/legend_chips are None the output
    is byte-identical to the pre-enhancement version.
    """
    parts = []
    if kicker:
        parts.append(text(x_margin, 24, kicker,
                          size=9, color=palette.primary,
                          family=palette.mono_family, bold=True,
                          letter=palette.kicker_letter_spacing))
    if title:
        is_serif_bold = palette.title_style == "serif_bold"
        parts.append(text(x_margin, 48, title,
                          size=17, color=palette.ink,
                          family=palette.head_family if is_serif_bold else palette.body_family,
                          bold=True))
    # Top-right region · legend_chips takes priority over encoding_note
    if legend_chips:
        cx_right = CANVAS_W - x_margin
        for color, label in reversed(list(legend_chips)):
            parts.append(text(cx_right, 24, label, size=8,
                              color=palette.gray, family=palette.body_family,
                              anchor="end"))
            lbl_w = max(24, int(len(label) * 5.2))
            chip_x = cx_right - lbl_w - 12
            parts.append(rect(chip_x, 17, 8, 8, fill=color))
            cx_right = chip_x - 14
    elif encoding_note:
        parts.append(text(CANVAS_W - x_margin, 24, encoding_note,
                          size=8, color=palette.gray,
                          family=palette.body_family, italic=True,
                          anchor="end"))
    parts.append(line(x_margin, 60, CANVAS_W - x_margin, 60,
                      color=palette.hair, w=1))
    # figure_number strip · y=70 (below top hairline)
    # 左对齐 figure_number · 右对齐 encoding_note fallback (若被 legend_chips 顶掉)
    if figure_number:
        parts.append(text(x_margin, 70, figure_number, size=8,
                          color=palette.gray, family=palette.mono_family,
                          bold=True, letter=1.2))
    if legend_chips and encoding_note:
        # 右对齐 encoding_note 到 y=70 · 明确避开 figure_number 左侧
        parts.append(text(CANVAS_W - x_margin, 70, encoding_note, size=8,
                          color=palette.gray, family=palette.body_family,
                          italic=True, anchor="end"))
    return "".join(parts)


def bottom_chrome(
    caption: str,
    source: str,
    palette: Palette,
    x_margin: int = 20,
    how_to_read: Optional[Sequence[Tuple]] = None,
) -> str:
    """bottom hairline + how_to_read band + caption + source

    Layout (dandelion mode · how_to_read 存在):
        y=278   bottom hairline (上移让位)
        y=286   "HOW TO READ" mono kicker
        y=289   step title baseline (8pt bold ink)
        y=290   step number circle center (r=6, primary fill)
        y=298   step desc baseline (7pt gray)
        y=316   caption (italic 9pt gray)
        y=328   source (mono 8pt gray, letter=1.2, right-anchored)

    Layout (legacy mode · how_to_read=None):
        y=300   bottom hairline
        y=316   caption
        y=328   source

    Backwards-compatible: when how_to_read is None the output is
    byte-identical to the pre-enhancement version.

    how_to_read: sequence of (step_num, title, desc) or (title, desc)
    """
    parts = []
    # Bottom hairline · dandelion mode 上移到 y=278 让位 how_to_read
    if how_to_read:
        parts.append(line(x_margin, 278, CANVAS_W - x_margin, 278,
                          color=palette.hair, w=1))
    else:
        parts.append(line(x_margin, 300, CANVAS_W - x_margin, 300,
                          color=palette.hair, w=1))
    if how_to_read:
        # "HOW TO READ" mono kicker · y=286
        parts.append(text(x_margin, 286, "HOW TO READ", size=7,
                          color=palette.gray, family=palette.mono_family,
                          bold=True, letter=1.4))
        n_steps = len(how_to_read)
        if n_steps > 0:
            band_x0 = x_margin + 88
            band_x1 = CANVAS_W - x_margin
            step_w = (band_x1 - band_x0) / n_steps
            for i, item in enumerate(how_to_read):
                if len(item) == 3:
                    num, ttl, dsc = item
                else:
                    num, ttl, dsc = str(i + 1), item[0], item[1]
                sx = band_x0 + i * step_w
                # circle center y=290 · 与 kicker/title 同水平带 (y=286-298)
                parts.append(circle(sx + 6, 290, 6, fill=palette.primary))
                parts.append(text(sx + 6, 293, str(num), size=7,
                                  color=palette.bg,
                                  family=palette.mono_family, bold=True,
                                  anchor="middle"))
                # step title baseline y=289
                parts.append(text(sx + 18, 289, ttl, size=8,
                                  color=palette.ink,
                                  family=palette.body_family, bold=True))
                # step desc baseline y=298
                parts.append(text(sx + 18, 298, dsc, size=7,
                                  color=palette.gray,
                                  family=palette.body_family))
    # caption · y=316 · 与 how_to_read (y=280-300) 不再互斥 · 保留独立
    if caption:
        parts.append(text(x_margin, 316, caption,
                          size=9, color=palette.gray,
                          family=palette.body_family, italic=True))
    if source:
        parts.append(text(CANVAS_W - x_margin, 328, source,
                          size=8, color=palette.gray,
                          family=palette.mono_family, letter=1.2,
                          anchor="end"))
    return "".join(parts)


__all__ = ["BODY", "BODY_DANDELION", "BodyBox", "top_chrome", "bottom_chrome"]
