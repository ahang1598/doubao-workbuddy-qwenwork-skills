"""svg_lib/charts/funnel.py

统一 API:  draw_funnel(data, variant, palette, ...) -> str (SVG)

Data schema:
    data = {
        "stages": [(label, value), ...],       # 至少 2 层
        "descriptions": [str, ...] | None,      # 可选，长度与 stages 一致
    }

Variants (5 共享同一份 data):
    - default_flat                  经典对称梯形漏斗（top→bottom 递减）
    - rectangle_flat                居中矩形条，宽度随值缩放
    - bar_lollipop                  横向棒棒糖（水平线 + 端点圆盘，dashboard 极简气质）
    - nested_arrow                  嵌套向下箭头（Russian doll，层层递进的叙事感）
    - pyramid_flat                  倒漏斗（top narrow, bottom wide）
"""
from __future__ import annotations

import math

from ._shared import (

    resolve_palette,
    xesc,
    auto_font_size,
    svg_open,
    svg_close,
    _rgba_with_alpha,
    rgb_tuple,
    is_dark_palette,
)


from .._common import (_ACC, _INK, _INK1, _INK2, _INK4, _INK6, _prepend_bg_if_dark, _resolve_font, _resolve_palette, _rgb_tuple, _rgba_with_alpha, _xesc, _variant_is_classic, _dispatch_to_svg_lib)
BODY_FONT = "Inter, sans-serif"
HEAD_FONT = "Georgia, serif"


# ---------------------------------------------------------------------------
# entry
# ---------------------------------------------------------------------------

def draw_funnel(
    data: dict,
    variant: str = "default_flat",
    palette: str = "archive_ink",
    width: float = 900,
    height: float = 540,
    title: str = None,
    subtitle: str = None,
) -> str:
    stages = data.get("stages") or []
    if not stages or len(stages) < 2:
        raise ValueError("draw_funnel: data['stages'] needs at least 2 entries")

    labels = [str(s[0]) for s in stages]
    values = [float(s[1]) for s in stages]
    if min(values) < 0:
        raise ValueError("draw_funnel: negative values not supported")
    if max(values) == 0:
        raise ValueError("draw_funnel: all zero values")

    descs = data.get("descriptions")
    if descs is not None and len(descs) != len(stages):
        raise ValueError("draw_funnel: descriptions must match stages length")

    pal = resolve_palette(palette)
    ctx = _Ctx(
        labels=labels,
        values=values,
        descs=descs,
        pal=pal,
        W=float(width),
        H=float(height),
        title=title,
        subtitle=subtitle,
    )

    if variant == "default_flat":
        body = _draw_default_flat(ctx)
    elif variant == "rectangle_flat":
        body = _draw_rectangle_flat(ctx)
    elif variant == "bar_lollipop":
        body = _draw_bar_lollipop(ctx)
    elif variant == "nested_arrow":
        body = _draw_nested_arrow(ctx)
    elif variant == "pyramid_flat":
        body = _draw_pyramid_flat(ctx)
    else:
        raise ValueError(
            f"unknown variant {variant!r}. Supported: default_flat, rectangle_flat, "
            "bar_lollipop, nested_arrow, pyramid_flat"
        )

    header = _header(ctx)
    return (
        svg_open(0, 0, ctx.W, ctx.H, bg=pal["bg"])
        + ctx.defs_svg()
        + header
        + body
        + svg_close()
    )


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

class _Ctx:
    """Layout / palette / defs 状态容器。"""

    def __init__(self, labels, values, descs, pal, W, H, title, subtitle):
        self.labels = labels
        self.values = values
        self.descs = descs
        self.pal = pal
        self.W = W
        self.H = H
        self.title = title
        self.subtitle = subtitle
        self.n = len(labels)
        # font sizing
        self.fs_label = auto_font_size(self.n, base=12, min_size=8, max_size=15)
        self.fs_value = max(9, self.fs_label - 1)
        self.fs_desc = max(8, self.fs_label - 3)
        # header height
        self.header_h = 50 if title else 20
        if subtitle:
            self.header_h += 18
        # plot region
        self.plot_top = self.header_h + 10
        self.plot_bot = self.H - 30
        self.plot_h = self.plot_bot - self.plot_top
        self._defs = []

    def add_def(self, s):
        self._defs.append(s)

    def defs_svg(self):
        if not self._defs:
            return ""
        return "<defs>" + "".join(self._defs) + "</defs>"

    def series_color(self, i):
        series = self.pal.get("series") or [self.pal["accent"]]
        return series[i % len(series)]

    def text_over(self, fill_col):
        """返回适合叠在 fill_col 上的文字颜色。"""
        r, g, b = rgb_tuple(fill_col)
        luma = 0.299 * r + 0.587 * g + 0.114 * b
        return self.pal["bg"] if luma < 128 else self.pal["ink"]


def _header(ctx: _Ctx) -> str:
    ink = ctx.pal["ink"]
    mut = ctx.pal["muted"]
    parts = []
    ML = 40
    if ctx.title:
        parts.append(
            f'<text x="{ML}" y="30" font-family="{HEAD_FONT}" font-size="20" '
            f'font-weight="600" fill="{ink}" letter-spacing=".03em">{xesc(ctx.title)}</text>'
        )
    if ctx.subtitle:
        y = 48 if ctx.title else 30
        parts.append(
            f'<text x="{ML}" y="{y}" font-family="{BODY_FONT}" font-size="11" '
            f'fill="{mut}" letter-spacing=".14em">{xesc(ctx.subtitle)}</text>'
        )
    if ctx.title:
        parts.append(
            f'<line x1="{ML}" y1="{ctx.header_h}" x2="{ctx.W - ML}" y2="{ctx.header_h}" '
            f'stroke="{ink}" stroke-width="0.6" opacity="0.4"/>'
        )
    return "".join(parts)


def _fmt_value(v):
    v = float(v)
    if v >= 10000:
        return f"{v:,.0f}"
    if v >= 100 or float(int(v)) == v:
        return f"{v:,.0f}"
    return f"{v:.1f}"


def _down_arrow_glyph(cx: float, cy: float, size: float, fill: str) -> str:
    """SVG path for a down-pointing arrow glyph.

    Substitute for the Unicode ↓ (U+2193) which renders as tofu when the host
    font lacks the glyph (飞书 canvas 本地字体常缺). The glyph is drawn as a
    solid triangle-headed arrow so it reads as a clear "descend" indicator.

    Args:
        cx, cy: glyph center (baseline-aligned to accompanying text center).
        size: overall glyph height in SVG units.
        fill: fill color string (e.g. 'rgba(0,0,0,0.75)').
    """
    h = float(size)
    w = h * 0.65
    shaft_w = h * 0.16
    head_h = h * 0.42
    top = cy - h / 2
    bot = cy + h / 2
    # arrow shaft (top rectangle) + triangular head (bottom)
    shaft_top_y = top
    shaft_bot_y = bot - head_h
    head_top_y = shaft_bot_y
    d = (
        f"M {cx - shaft_w / 2:.2f} {shaft_top_y:.2f} "
        f"L {cx + shaft_w / 2:.2f} {shaft_top_y:.2f} "
        f"L {cx + shaft_w / 2:.2f} {head_top_y:.2f} "
        f"L {cx + w / 2:.2f} {head_top_y:.2f} "
        f"L {cx:.2f} {bot:.2f} "
        f"L {cx - w / 2:.2f} {head_top_y:.2f} "
        f"L {cx - shaft_w / 2:.2f} {head_top_y:.2f} Z"
    )
    return f'<path d="{d}" fill="{fill}"/>'


# ---------------------------------------------------------------------------
# variant 1: default_flat (对称梯形)
# ---------------------------------------------------------------------------

def _draw_default_flat(ctx: _Ctx) -> str:
    parts = []
    max_v = max(ctx.values)
    min_v = min(ctx.values)
    # 极端动态范围：底部 stages 会退化成 <1px 的条。用 sqrt 平滑 + 最小可见宽度兜底。
    dyn_range = max_v / max(min_v, 1e-9)
    use_sqrt = dyn_range > 50
    MIN_W = 3.0  # 至少 3px 宽，保证肉眼可见

    # 左侧需要空间给：(a) descriptions 列 (b) 当窄行的 label 放到梯形外时容纳它。
    # 用 fixed 120 保证两种情况都不 clip；当 descs 存在时再多留 40px。
    desc_col_w = 60 if ctx.descs else 0
    ML = 120 + desc_col_w
    label_pad = 200  # 右侧留给 label / value / desc
    max_w = ctx.W - ML - label_pad - 40
    cx = ML + max_w / 2
    n = ctx.n
    row_gap = 3
    row_h = (ctx.plot_h - row_gap * (n - 1)) / n
    row_h = max(24.0, row_h)

    ink = ctx.pal["ink"]
    mut = ctx.pal["muted"]

    def _bar_w(v):
        if use_sqrt:
            raw = max_w * (math.sqrt(v) / math.sqrt(max_v))
        else:
            raw = max_w * (v / max_v)
        return max(MIN_W, raw)

    for i in range(n):
        v = ctx.values[i]
        top_w = _bar_w(v)
        bot_v = ctx.values[i + 1] if i + 1 < n else v
        bot_w = _bar_w(bot_v)
        y_top = ctx.plot_top + i * (row_h + row_gap)
        y_bot = y_top + row_h
        col = ctx.series_color(i)
        path = (
            f"M {cx - top_w/2:.1f} {y_top:.1f} L {cx + top_w/2:.1f} {y_top:.1f} "
            f"L {cx + bot_w/2:.1f} {y_bot:.1f} L {cx - bot_w/2:.1f} {y_bot:.1f} Z"
        )
        parts.append(f'<path d="{path}" fill="{_rgba_with_alpha(col, 0.9)}"/>')

        # in-band label centered — but if the band is too narrow, put outside so it doesn't clip
        text_col = ctx.text_over(col)
        band_min_w = min(top_w, bot_w)
        if band_min_w >= len(ctx.labels[i]) * ctx.fs_label * 0.55:
            parts.append(
                f'<text x="{cx:.1f}" y="{y_top + row_h/2 + ctx.fs_label*0.35:.1f}" '
                f'text-anchor="middle" font-family="{BODY_FONT}" font-size="{ctx.fs_label}" '
                f'font-weight="600" fill="{text_col}">{xesc(ctx.labels[i])}</text>'
            )
        else:
            # place label to the left of trapezoid so it's still visible for tiny bands
            parts.append(
                f'<text x="{cx - max_w/2 - 8:.1f}" y="{y_top + row_h/2 + ctx.fs_label*0.35:.1f}" '
                f'text-anchor="end" font-family="{BODY_FONT}" font-size="{ctx.fs_label}" '
                f'font-weight="600" fill="{ink}">{xesc(ctx.labels[i])}</text>'
            )
        # right-side value + optional description
        lx = cx + max_w / 2 + 24
        parts.append(
            f'<text x="{lx:.1f}" y="{y_top + row_h/2 - 2:.1f}" font-family="{BODY_FONT}" '
            f'font-size="{ctx.fs_value}" font-weight="600" fill="{ink}">{_fmt_value(v)}</text>'
        )
        pct = v / ctx.values[0] * 100
        parts.append(
            f'<text x="{lx:.1f}" y="{y_top + row_h/2 + ctx.fs_value + 2:.1f}" font-family="{BODY_FONT}" '
            f'font-size="{ctx.fs_desc}" fill="{mut}">{pct:.1f}% of top</text>'
        )
        if ctx.descs:
            parts.append(
                f'<text x="20" y="{y_top + row_h/2 + 3:.1f}" font-family="{BODY_FONT}" '
                f'font-size="{ctx.fs_desc}" font-style="italic" fill="{mut}">'
                f'{xesc(ctx.descs[i])}</text>'
            )
    return "".join(parts)


# ---------------------------------------------------------------------------
# variant 2: rectangle_flat
# ---------------------------------------------------------------------------

def _draw_rectangle_flat(ctx: _Ctx) -> str:
    parts = []
    max_v = max(ctx.values)
    # 极端动态范围 → sqrt 平滑 + 最小可见宽度兜底
    dyn_range = max_v / max(min(ctx.values), 1e-9)
    use_sqrt = dyn_range > 50
    MIN_W = 3.0

    # 左侧多留空间，narrow bars 的 label 放到条形外侧不 clip
    ML = 120
    label_pad = 200
    max_w = ctx.W - ML - label_pad - 40
    cx = ML + max_w / 2
    n = ctx.n
    gap = 6
    row_h = max(20.0, (ctx.plot_h - gap * (n - 1)) / n)

    ink = ctx.pal["ink"]
    mut = ctx.pal["muted"]

    for i in range(n):
        v = ctx.values[i]
        if use_sqrt:
            w = max_w * (math.sqrt(v) / math.sqrt(max_v))
        else:
            w = max_w * (v / max_v)
        w = max(MIN_W, w)
        x = cx - w / 2
        y = ctx.plot_top + i * (row_h + gap)
        col = ctx.series_color(i)
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{row_h:.1f}" '
            f'fill="{_rgba_with_alpha(col, 0.88)}"/>'
        )
        # value inside if wide enough, else outside
        if w > 80:
            parts.append(
                f'<text x="{cx:.1f}" y="{y + row_h/2 + ctx.fs_label*0.35:.1f}" '
                f'text-anchor="middle" font-family="{BODY_FONT}" '
                f'font-size="{ctx.fs_label}" font-weight="700" fill="{ctx.text_over(col)}">'
                f'{xesc(ctx.labels[i])}</text>'
            )
        else:
            parts.append(
                f'<text x="{cx - w/2 - 8:.1f}" y="{y + row_h/2 + 3:.1f}" '
                f'text-anchor="end" font-family="{BODY_FONT}" '
                f'font-size="{ctx.fs_label}" font-weight="600" fill="{ink}">'
                f'{xesc(ctx.labels[i])}</text>'
            )
        # right-side value
        parts.append(
            f'<text x="{cx + max_w/2 + 16:.1f}" y="{y + row_h/2 + 3:.1f}" '
            f'font-family="{BODY_FONT}" font-size="{ctx.fs_value}" '
            f'font-weight="600" fill="{ink}">{_fmt_value(v)}</text>'
        )
        if ctx.descs:
            parts.append(
                f'<text x="{cx + max_w/2 + 80:.1f}" y="{y + row_h/2 + 3:.1f}" '
                f'font-family="{BODY_FONT}" font-size="{ctx.fs_desc}" '
                f'font-style="italic" fill="{mut}">{xesc(ctx.descs[i])}</text>'
            )
    return "".join(parts)


# ---------------------------------------------------------------------------
# variant 3: bar_lollipop  (水平线 + 端点圆盘，现代 dashboard 气质)
# ---------------------------------------------------------------------------

def _draw_bar_lollipop(ctx: _Ctx) -> str:
    """Lollipop-style funnel.

    Each stage is a horizontal thin bar anchored to a fixed baseline (left
    axis), terminated by a solid filled disc. Disc radius is sqrt-scaled by
    value so tiny stages stay visible without dominating the chart. A subtle
    dotted guide line spans the full plot width per row, and a right-side
    numeric column pairs value + % of top. Reads like a modern KPI dashboard
    row list rather than a funnel silhouette.
    """
    parts = []
    max_v = max(ctx.values)
    min_v = min(v for v in ctx.values if v > 0) if any(v > 0 for v in ctx.values) else 1.0
    n = ctx.n

    ink = ctx.pal["ink"]
    mut = ctx.pal["muted"]

    # layout: left label column | plot region | right value column
    label_col_w = 130 if not ctx.descs else 180
    right_col_w = 130
    ML = 40
    plot_left = ML + label_col_w
    plot_right = ctx.W - ML - right_col_w
    plot_w = plot_right - plot_left

    # vertical layout
    row_gap = 4
    row_h = max(28.0, (ctx.plot_h - row_gap * (n - 1)) / n)

    # disc radius: sqrt-scaled between r_min .. r_max, clamped so disc fits row
    r_max = min(20.0, row_h * 0.45)
    r_min = max(4.0, min(6.0, r_max * 0.28))
    # sqrt weighting so dynamic range doesn't crush small stages
    dyn_range = max_v / max(min_v, 1e-9)
    use_sqrt = dyn_range > 25

    def _radius(v):
        if v <= 0:
            return r_min
        if use_sqrt:
            t = math.sqrt(v / max_v)
        else:
            t = v / max_v
        return r_min + (r_max - r_min) * t

    def _bar_len(v):
        # bar length uses same scale as radius so disc position tracks value
        if v <= 0:
            return r_min + 4
        if use_sqrt:
            t = math.sqrt(v / max_v)
        else:
            t = v / max_v
        # reserve room on the right so disc + label never touch plot_right edge
        avail = plot_w - r_max - 8
        return max(r_min + 4, avail * t)

    # per-row rendering
    for i in range(n):
        v = ctx.values[i]
        col = ctx.series_color(i)
        y = ctx.plot_top + i * (row_h + row_gap) + row_h / 2

        # 1) full-width dotted guide (very light) — orients the eye horizontally
        parts.append(
            f'<line x1="{plot_left:.1f}" y1="{y:.1f}" x2="{plot_right:.1f}" y2="{y:.1f}" '
            f'stroke="{_rgba_with_alpha(ink, 0.08)}" stroke-width="0.7" '
            f'stroke-dasharray="2 3"/>'
        )

        # 2) label on the left (right-anchored so it sits close to axis)
        label_x = plot_left - 12
        parts.append(
            f'<text x="{label_x:.1f}" y="{y + ctx.fs_label*0.35:.1f}" text-anchor="end" '
            f'font-family="{BODY_FONT}" font-size="{ctx.fs_label}" '
            f'font-weight="600" fill="{ink}">{xesc(ctx.labels[i])}</text>'
        )
        # optional description sits just below label in a smaller, italic style
        if ctx.descs:
            parts.append(
                f'<text x="{label_x:.1f}" y="{y + ctx.fs_label + ctx.fs_desc + 2:.1f}" '
                f'text-anchor="end" font-family="{BODY_FONT}" font-size="{ctx.fs_desc}" '
                f'font-style="italic" fill="{mut}">{xesc(ctx.descs[i])}</text>'
            )

        # 3) axis tick (short vertical mark under label at baseline)
        parts.append(
            f'<line x1="{plot_left:.1f}" y1="{y - 4:.1f}" x2="{plot_left:.1f}" y2="{y + 4:.1f}" '
            f'stroke="{_rgba_with_alpha(ink, 0.35)}" stroke-width="1"/>'
        )

        # 4) the lollipop: solid line from baseline out to disc center
        blen = _bar_len(v)
        r = _radius(v)
        disc_cx = plot_left + blen
        line_col = _rgba_with_alpha(col, 0.55)
        parts.append(
            f'<line x1="{plot_left:.1f}" y1="{y:.1f}" x2="{disc_cx:.1f}" y2="{y:.1f}" '
            f'stroke="{line_col}" stroke-width="2.4" stroke-linecap="round"/>'
        )
        # 5) the disc (endpoint). outer ring + inner solid gives it depth.
        parts.append(
            f'<circle cx="{disc_cx:.1f}" cy="{y:.1f}" r="{r:.1f}" '
            f'fill="{_rgba_with_alpha(col, 0.18)}"/>'
        )
        parts.append(
            f'<circle cx="{disc_cx:.1f}" cy="{y:.1f}" r="{max(r-3, r*0.55):.1f}" '
            f'fill="{col}"/>'
        )

        # 6) right-side value + pct-of-top column
        val_x = plot_right + 16
        val_str = _fmt_value(v)
        pct = v / ctx.values[0] * 100
        parts.append(
            f'<text x="{val_x:.1f}" y="{y - 2:.1f}" '
            f'font-family="{BODY_FONT}" font-size="{ctx.fs_value}" '
            f'font-weight="700" fill="{ink}">{val_str}</text>'
        )
        parts.append(
            f'<text x="{val_x:.1f}" y="{y + ctx.fs_value + 2:.1f}" '
            f'font-family="{BODY_FONT}" font-size="{ctx.fs_desc}" '
            f'fill="{mut}">{pct:.1f}% of top</text>'
        )

        # 7) drop-off badge between rows (only when there is a next stage)
        if i < n - 1:
            drop_pct = (v - ctx.values[i + 1]) / max(v, 1e-9) * 100
            if drop_pct > 0.1:
                mid_y = y + row_h / 2 + row_gap / 2
                # 用 SVG path 画下降箭头（替代 Unicode ↓ 以规避飞书 canvas 本地
                # 字体缺 U+2193 时的 tofu 方块）。glyph + number 分离绘制。
                accent_col = _rgba_with_alpha(ctx.pal["accent"], 0.75)
                num_str = f"{drop_pct:.0f}%"
                text_y = mid_y + ctx.fs_desc * 0.35
                # 放在 plot 区域内、baseline axis 右侧 6px，避开左侧 label /
                # description 列（否则层数多时 description bbox 会跟 drop tag
                # bbox 相交 → embed_svg_bbox_overlap）。
                glyph_size = ctx.fs_desc * 0.95
                glyph_cx = plot_left + 6 + glyph_size * 0.55
                parts.append(_down_arrow_glyph(glyph_cx, mid_y, glyph_size, accent_col))
                text_x = plot_left + 6 + glyph_size + 3
                parts.append(
                    f'<text x="{text_x:.1f}" y="{text_y:.1f}" '
                    f'text-anchor="start" font-family="{BODY_FONT}" '
                    f'font-size="{ctx.fs_desc}" font-weight="600" '
                    f'fill="{accent_col}">{num_str}</text>'
                )
    # left baseline axis line spanning all rows
    axis_y1 = ctx.plot_top
    axis_y2 = ctx.plot_top + n * (row_h + row_gap) - row_gap
    parts.insert(
        0,
        f'<line x1="{plot_left:.1f}" y1="{axis_y1:.1f}" x2="{plot_left:.1f}" y2="{axis_y2:.1f}" '
        f'stroke="{_rgba_with_alpha(ink, 0.28)}" stroke-width="1"/>'
    )
    return "".join(parts)


# ---------------------------------------------------------------------------
# variant 4: nested_arrow  (逐层嵌套的向下箭头，Russian doll 叙事感)
# ---------------------------------------------------------------------------

def _draw_nested_arrow(ctx: _Ctx) -> str:
    """Nested down-arrow funnel.

    Each stage is a broad downward-pointing pentagon-arrow drawn CENTERED
    horizontally. Successive stages shrink both in width (sqrt-scaled by
    value) and stack vertically inside the previous arrow's silhouette,
    giving a Russian-doll layered feel that reads clearly as narrowing
    progression. Numeric labels and stage names live inline on each arrow's
    body plate; a right-side callout column carries value + % of top for
    scannable reading. Deliberately not a trapezoid: the pointed tip makes
    the "flow" direction visually explicit.
    """
    parts = []
    max_v = max(ctx.values)
    min_v = min(v for v in ctx.values if v > 0) if any(v > 0 for v in ctx.values) else 1.0
    n = ctx.n

    ink = ctx.pal["ink"]
    mut = ctx.pal["muted"]
    bg = ctx.pal["bg"] or "rgba(255,255,255,1)"

    # layout: center the arrows in a plot region, keep a right sidebar for values
    ML = 40
    right_col_w = 150
    plot_left = ML
    plot_right = ctx.W - ML - right_col_w
    plot_w = plot_right - plot_left
    cx = plot_left + plot_w / 2

    # width scaling: sqrt so a 500k -> 42 gap doesn't collapse late stages
    dyn_range = max_v / max(min_v, 1e-9)
    use_sqrt = dyn_range > 25

    def _norm_w(v):
        if v <= 0:
            return 0.0
        if use_sqrt:
            return math.sqrt(v / max_v)
        return v / max_v

    w_max = min(plot_w - 20, 620.0)
    w_min = max(80.0, w_max * 0.28)  # smallest arrow still readable

    arrow_widths = [w_min + (w_max - w_min) * _norm_w(v) for v in ctx.values]
    # enforce strictly non-increasing widths so nested Russian-doll silhouette
    # reads correctly even when values are not strictly decreasing
    for i in range(1, n):
        arrow_widths[i] = min(arrow_widths[i], arrow_widths[i - 1] - 4)
        arrow_widths[i] = max(arrow_widths[i], w_min * 0.55)

    # vertical layout: each arrow occupies row_h; the pointed tip of arrow i
    # visually leads into arrow i+1's body. We pack them tight but avoid text
    # collision by tuning tip height and body height. Row height MUST fit
    # inside plot_h so the last arrow's tip doesn't spill past the viewBox.
    row_gap = 6 if n <= 6 else 3
    # honor available plot_h first, use 48 only as an upper visual target
    ideal_row_h = 48.0
    fit_row_h = (ctx.plot_h - row_gap * (n - 1)) / n
    row_h = max(24.0, min(ideal_row_h, fit_row_h))
    tip_h = min(18.0, row_h * 0.32)   # depth of triangular tip
    body_h = row_h - tip_h            # rectangular body region for text

    for i in range(n):
        w = arrow_widths[i]
        col = ctx.series_color(i)
        y_top = ctx.plot_top + i * (row_h + row_gap)
        y_body_bot = y_top + body_h
        y_tip = y_top + row_h
        xL = cx - w / 2
        xR = cx + w / 2

        # pentagon-arrow path: rectangle + triangular tip
        # top-left, top-right, body-right, tip, body-left → close
        path = (
            f"M {xL:.1f} {y_top:.1f} "
            f"L {xR:.1f} {y_top:.1f} "
            f"L {xR:.1f} {y_body_bot:.1f} "
            f"L {cx:.1f} {y_tip:.1f} "
            f"L {xL:.1f} {y_body_bot:.1f} Z"
        )
        parts.append(
            f'<path d="{path}" fill="{_rgba_with_alpha(col, 0.92)}"/>'
        )

        # subtle top highlight strip (adds depth without a full gradient def)
        hi_top = y_top + 3
        hi_bot = y_top + min(6.0, body_h * 0.22)
        if hi_bot - hi_top >= 2 and w > 40:
            hi_path = (
                f"M {xL + 6:.1f} {hi_top:.1f} "
                f"L {xR - 6:.1f} {hi_top:.1f} "
                f"L {xR - 6:.1f} {hi_bot:.1f} "
                f"L {xL + 6:.1f} {hi_bot:.1f} Z"
            )
            parts.append(f'<path d="{hi_path}" fill="rgba(255,255,255,0.18)"/>')

        # thin dark ridge just above the tip for definition
        ridge_y = y_body_bot - 1
        if w > 40:
            parts.append(
                f'<line x1="{xL + 4:.1f}" y1="{ridge_y:.1f}" x2="{xR - 4:.1f}" y2="{ridge_y:.1f}" '
                f'stroke="rgba(0,0,0,0.18)" stroke-width="0.8"/>'
            )

        # inline label + value plate on the body
        text_col = ctx.text_over(col)
        body_cy = y_top + body_h / 2
        label_w_est = len(ctx.labels[i]) * ctx.fs_label * 0.6
        value_str = _fmt_value(ctx.values[i])
        value_w_est = len(value_str) * ctx.fs_value * 0.6
        # need room for both stacked; use tighter of the two if body is narrow
        can_stack = body_h >= (ctx.fs_label + ctx.fs_value + 6)
        can_inline = w >= max(label_w_est, value_w_est) + 24

        if can_inline and can_stack:
            # label above value, both centered
            parts.append(
                f'<text x="{cx:.1f}" y="{body_cy - 2:.1f}" text-anchor="middle" '
                f'font-family="{BODY_FONT}" font-size="{ctx.fs_label}" font-weight="700" '
                f'fill="{text_col}">{xesc(ctx.labels[i])}</text>'
            )
            parts.append(
                f'<text x="{cx:.1f}" y="{body_cy + ctx.fs_label:.1f}" text-anchor="middle" '
                f'font-family="{BODY_FONT}" font-size="{ctx.fs_value}" font-weight="600" '
                f'fill="{_rgba_with_alpha(text_col, 0.9)}">{value_str}</text>'
            )
        elif can_inline:
            # narrow vertical space → single-line "LABEL  value"
            parts.append(
                f'<text x="{cx:.1f}" y="{body_cy + ctx.fs_label*0.35:.1f}" text-anchor="middle" '
                f'font-family="{BODY_FONT}" font-size="{ctx.fs_label}" font-weight="700" '
                f'fill="{text_col}">{xesc(ctx.labels[i])}</text>'
            )
        else:
            # too narrow for both — put label at right, value in sidebar handles it
            parts.append(
                f'<text x="{cx:.1f}" y="{body_cy + ctx.fs_label*0.35:.1f}" text-anchor="middle" '
                f'font-family="{BODY_FONT}" font-size="{max(9, ctx.fs_label-1)}" '
                f'font-weight="700" fill="{text_col}">{xesc(ctx.labels[i])}</text>'
            )

        # right-side sidebar: value + % of top + optional description
        side_x = plot_right + 16
        # anchor sidebar text to arrow body vertical center for alignment
        side_y = y_top + body_h / 2
        pct = ctx.values[i] / ctx.values[0] * 100
        parts.append(
            f'<text x="{side_x:.1f}" y="{side_y - 2:.1f}" '
            f'font-family="{BODY_FONT}" font-size="{ctx.fs_value}" '
            f'font-weight="700" fill="{ink}">{value_str}</text>'
        )
        parts.append(
            f'<text x="{side_x:.1f}" y="{side_y + ctx.fs_value + 2:.1f}" '
            f'font-family="{BODY_FONT}" font-size="{ctx.fs_desc}" '
            f'fill="{mut}">{pct:.1f}% of top</text>'
        )
        if ctx.descs:
            # italic desc sits below the pct line
            parts.append(
                f'<text x="{side_x:.1f}" y="{side_y + ctx.fs_value + ctx.fs_desc + 6:.1f}" '
                f'font-family="{BODY_FONT}" font-size="{ctx.fs_desc}" '
                f'font-style="italic" fill="{mut}">{xesc(ctx.descs[i])}</text>'
            )

        # between-row drop tag: small "-XX%" placed in the tip gutter, near arrow tip.
        # Only render when there is a next stage AND a real drop happened.
        if i < n - 1:
            next_v = ctx.values[i + 1]
            drop = ctx.values[i] - next_v
            if drop > 0:
                drop_pct = drop / max(ctx.values[i], 1e-9) * 100
                tag_y = y_tip + row_gap / 2 + 2
                # 用 path glyph 替代 Unicode ↓（飞书 canvas 本地字体缺 U+2193 →
                # tofu 方块）。glyph 在数字左侧。
                accent_col = _rgba_with_alpha(ctx.pal["accent"], 0.75)
                num_str = f"{drop_pct:.0f}%"
                text_y = tag_y + ctx.fs_desc * 0.35
                # small pill-like text off to the right of the tip (so it doesn't
                # overlap the next arrow's top edge). Uses accent color muted.
                tag_x = cx + arrow_widths[i + 1] / 2 + 12
                # glyph 先画（在 tag_x 位置），文字紧跟其后
                glyph_size = ctx.fs_desc * 0.95
                glyph_cx = tag_x + glyph_size * 0.55
                parts.append(_down_arrow_glyph(glyph_cx, tag_y, glyph_size, accent_col))
                text_x = tag_x + glyph_size + 3
                parts.append(
                    f'<text x="{text_x:.1f}" y="{text_y:.1f}" '
                    f'text-anchor="start" font-family="{BODY_FONT}" '
                    f'font-size="{ctx.fs_desc}" font-weight="600" '
                    f'fill="{accent_col}">{num_str}</text>'
                )

    return "".join(parts)


# ---------------------------------------------------------------------------
# variant 5: pyramid_flat (倒漏斗)
# ---------------------------------------------------------------------------

def _draw_pyramid_flat(ctx: _Ctx) -> str:
    """Pyramid: TOP narrow, BOTTOM wide — a strict triangular shape.

    Row-i width = (i+1)/n * max_w so silhouette forms a proper pyramid
    regardless of value distribution. Value is encoded via label on the
    right; the shape encodes the *rank/level* of each stage.
    """
    parts = []
    # need extra left margin because narrow top rows push labels outside the pyramid
    ML = 140 if ctx.descs is None else 200
    right_pad = 160
    max_w = ctx.W - ML - right_pad
    cx = ML + max_w / 2
    n = ctx.n
    gap = 3
    row_h = max(24.0, (ctx.plot_h - gap * (n - 1)) / n)

    ink = ctx.pal["ink"]
    mut = ctx.pal["muted"]

    for i in range(n):
        v = ctx.values[i]
        # pyramid geometry: top edge width = i/n * max_w, bottom edge width = (i+1)/n * max_w
        # so row 0 is a triangle tip (top_w=0), row n-1 is the widest base.
        top_w = (i / n) * max_w
        bot_w = ((i + 1) / n) * max_w
        y_top = ctx.plot_top + i * (row_h + gap)
        y_bot = y_top + row_h
        col = ctx.series_color(i)
        path = (
            f"M {cx - top_w/2:.1f} {y_top:.1f} L {cx + top_w/2:.1f} {y_top:.1f} "
            f"L {cx + bot_w/2:.1f} {y_bot:.1f} L {cx - bot_w/2:.1f} {y_bot:.1f} Z"
        )
        parts.append(f'<path d="{path}" fill="{_rgba_with_alpha(col, 0.9)}"/>')

        # label — centered inside if wide enough, else placed to the left
        band_min_w = min(top_w, bot_w) if i > 0 else bot_w / 2
        text_col = ctx.text_over(col)
        if band_min_w >= len(ctx.labels[i]) * ctx.fs_label * 0.55:
            parts.append(
                f'<text x="{cx:.1f}" y="{y_top + row_h/2 + ctx.fs_label*0.35:.1f}" '
                f'text-anchor="middle" font-family="{BODY_FONT}" font-size="{ctx.fs_label}" '
                f'font-weight="700" fill="{text_col}">{xesc(ctx.labels[i])}</text>'
            )
        else:
            # place label to the left of the pyramid so tiny top rows still show label
            parts.append(
                f'<text x="{cx - max_w/2 - 8:.1f}" y="{y_top + row_h/2 + ctx.fs_label*0.35:.1f}" '
                f'text-anchor="end" font-family="{BODY_FONT}" font-size="{ctx.fs_label}" '
                f'font-weight="600" fill="{ink}">{xesc(ctx.labels[i])}</text>'
            )
        lx = cx + max_w / 2 + 24
        parts.append(
            f'<text x="{lx:.1f}" y="{y_top + row_h/2 - 2:.1f}" font-family="{BODY_FONT}" '
            f'font-size="{ctx.fs_value}" font-weight="600" fill="{ink}">{_fmt_value(v)}</text>'
        )
        pct = v / ctx.values[0] * 100
        parts.append(
            f'<text x="{lx:.1f}" y="{y_top + row_h/2 + ctx.fs_value + 2:.1f}" '
            f'font-family="{BODY_FONT}" font-size="{ctx.fs_desc}" fill="{mut}">'
            f'{pct:.0f}%</text>'
        )
        if ctx.descs:
            # 反向金字塔（上窄下宽）：每层是 top_w < bot_w 的梯形，其视觉几何
            # 中心不在 row 中点，而是靠下（centroid_y_from_top =
            # h*(top_w + 2*bot_w) / (3*(top_w+bot_w))）。用 centroid 对齐左侧
            # description，避免像 default_flat（上宽下窄）那样把描述贴到 row
            # 中点后与实际梯形视觉中心错位。
            if top_w + bot_w > 1e-9:
                _centroid_dy = row_h * (top_w + 2 * bot_w) / (3 * (top_w + bot_w))
            else:
                _centroid_dy = row_h * 0.5
            _desc_baseline = y_top + _centroid_dy + ctx.fs_desc * 0.35
            # description 列放在漏斗最左（固定 x=16），左对齐；这样即使 pyramid
            # 底边到达 ML=200，description 也不会与漏斗形状重叠。
            parts.append(
                f'<text x="16" y="{_desc_baseline:.1f}" '
                f'font-family="{BODY_FONT}" font-size="{ctx.fs_desc}" '
                f'font-style="italic" fill="{mut}">{xesc(ctx.descs[i])}</text>'
            )
    return "".join(parts)


def make_funnel_classic(stages,
                        stage_labels=None,
                        stage_descriptions=None,
                        title: str = None,
                        subtitle: str = None,
                        figure_label: str = None,
                        note: str = None,
                        show_drop_off: bool = True,
                        show_cumulative: bool = True,
                        show_insights: bool = True,
                        width: float = 1400,
                        height: float = None,
                        footer: str = None,           # 老 API 兼容
                        primary_rgb=None,             # 老 API 兼容（忽略，走 palette）
                        max_half_w=None,              # 老 API 兼容（忽略，走自适应）
                        min_half_w=None,              # 老 API 兼容
                        font_family: str = None,
                        palette=None,
                variant: str = None) -> str:
    """
    经典漏斗图（Dandelion academic 风格）。

    stages: N 个阶段数值列表（如 [120000, 32400, 19800, 12100, 4680, 3210]）
    stage_labels: N 个阶段名（如 ["Visitors","Sign-ups",...]）
    stage_descriptions: N 个副描述（斜体小字，如 "Reached landing page"）

    title/subtitle/figure_label: 顶部
    note: 底部脚注
    show_drop_off: 左侧 DROP-OFF 面板（红色 % + 引线）
    show_cumulative: 右侧 CUMULATIVE CONVERSION 迷你条形图
    show_insights: 底部 3 张洞察卡片（OVERALL/BIGGEST/STRONGEST）

    footer/primary_rgb/max_half_w/min_half_w 参数是老 API，保留兼容但不推荐使用
    """
    if not _variant_is_classic('funnel_classic', variant):
        _data = {"stages": list(zip(stage_labels or [f"Stage {i+1}" for i in range(len(stages))], stages)), "descriptions": stage_descriptions}
        return _dispatch_to_svg_lib(
            'funnel_classic', variant, _data,
            title=title, subtitle=subtitle, figure_label=figure_label,
            palette=palette, font_family=font_family,
        )

    if not stages or len(stages) < 2:
        raise ValueError("funnel_classic: need at least 2 stages")
    if stage_labels is None:
        stage_labels = [f"Stage {i+1}" for i in range(len(stages))]
    if len(stage_labels) != len(stages):
        raise ValueError(f"funnel_classic: labels count {len(stage_labels)} != stages count {len(stages)}")
    if stage_descriptions is not None and len(stage_descriptions) != len(stages):
        raise ValueError(f"funnel_classic: descriptions count {len(stage_descriptions)} != stages count {len(stages)}")

    _pal = _resolve_palette(palette)
    _body_font, _head_font = _resolve_font(font_family)
    _INK, _INK6, _INK4, _INK2, _INK1, _ACC = (
        _pal["ink"], _pal["ink6"], _pal["ink4"], _pal["ink2"], _pal["ink1"], _pal["accent"]
    )
    c_muted = _pal.get("muted", _rgba_with_alpha(_INK, 0.6))
    c_secondary = _pal.get("secondary", _rgba_with_alpha(_INK, 0.5))
    c_bg = _pal.get("bg")
    PAPER = c_bg if c_bg else "rgba(250,248,242,1)"

    # 派生 N 段渐变色（漏斗越深越"贵"），gradient 模式沿 accent → secondary/ink
    # 用 gradient 模式的 series 派生（相邻邻近，形成阶梯感）
    n = len(stages)
    # 从 accent 派生 N 色 gradient
    # 但 accent 可能是浅色（深底 palette），需要根据背景判断方向
    def _rgb_tuple_local(s):
        return _rgb_tuple(s)
    # 简单方案：用 palette 里 secondary 作 top（浅端）、accent 作 bot（深端）；
    # 或倒过来，取决于哪个更亮
    top_col_rgb = _rgb_tuple_local(c_secondary)
    bot_col_rgb = _rgb_tuple_local(_ACC)
    top_luma = 0.299 * top_col_rgb[0] + 0.587 * top_col_rgb[1] + 0.114 * top_col_rgb[2]
    bot_luma = 0.299 * bot_col_rgb[0] + 0.587 * bot_col_rgb[1] + 0.114 * bot_col_rgb[2]
    # 想要 top 浅、bot 深 —— 若不满足则反转
    if top_luma < bot_luma:
        top_col_rgb, bot_col_rgb = bot_col_rgb, top_col_rgb
    # 若深底 palette：top 浅 = accent 亮端，bot = 更深 secondary/ink
    if c_bg:
        bg_r, bg_g, bg_b = _rgb_tuple_local(c_bg)
        bg_luma = 0.299 * bg_r + 0.587 * bg_g + 0.114 * bg_b
        if bg_luma < 100:
            # 深底：top 使用亮的 accent，bot 使用中间 palette 派生
            top_col_rgb = _rgb_tuple_local(_ACC)
            # bot 保持 secondary
            bot_col_rgb = _rgb_tuple_local(c_secondary)

    def _lerp3(a, b, t):
        return (int(a[0] + (b[0]-a[0]) * t),
                int(a[1] + (b[1]-a[1]) * t),
                int(a[2] + (b[2]-a[2]) * t))
    stage_colors = []
    for i in range(n):
        t = i / max(1, n - 1)
        rgb = _lerp3(top_col_rgb, bot_col_rgb, t)
        stage_colors.append(f"rgba({rgb[0]},{rgb[1]},{rgb[2]},1)")

    # ---------- 布局 ----------
    MARGIN_L = 90
    MARGIN_R = 90
    MARGIN_T = 145 if title else 60
    MARGIN_B = 100 if (note or show_insights) else 60

    plot_x = MARGIN_L + 260   # 漏斗中心线左界（留给 DROP-OFF 面板）
    plot_w_max = 500          # 顶层梯形最宽
    funnel_cx = plot_x + plot_w_max / 2

    row_h = 66
    row_gap = 4
    plot_y = MARGIN_T
    funnel_top = plot_y + 10

    def row_top(i): return funnel_top + i * (row_h + row_gap)
    def row_bot(i): return row_top(i) + row_h

    # height 自适应：跟层数 N 联动，避免 N=3 时底部大片留白
    # funnel_bottom → 30 gap → insight 卡片 70 → 底部呼吸
    n_stages = len(stages)
    if height is None:
        _funnel_bottom = funnel_top + n_stages * (row_h + row_gap) - row_gap
        _content_bottom = _funnel_bottom + (100 if show_insights else 10)
        _bottom_pad = 90 if note else 30
        height = _content_bottom + _bottom_pad

    top_count = stages[0]
    if top_count <= 0:
        raise ValueError("funnel_classic: first stage must be > 0")
    def width_of(i): return plot_w_max * stages[i] / top_count

    # ---------- 字号自适应（viewBox + 数据规模双重）----------
    # 关键：slide 里 3 图并列渲染宽度 ≈ 400px，viewBox=1400 → 缩放 ~0.29x
    # 字号需要相应放大，让最终视觉 >= 10px
    _n_stages_fs = len(stages)
    # 用 height 而非固定 540/height：height 是自动算的，跟层数正相关
    # 基准 = min(vb_w, vb_h) * 0.02（约 12-16pt）
    _fs_base = min(float(width), float(height)) * 0.022
    if _n_stages_fs <= 4:
        _fs_mult = 1.6
    elif _n_stages_fs <= 8:
        _fs_mult = 1.2
    elif _n_stages_fs <= 15:
        _fs_mult = 0.95
    else:
        _fs_mult = 0.75
    _fs_body_stage  = max(14.0, _fs_base * _fs_mult)          # stage label 内文
    _fs_value_stage = max(20.0, _fs_body_stage * 1.5)         # stage 大数字（Georgia）
    _fs_desc_stage  = max(11.0, _fs_body_stage * 0.75)        # italic desc
    _fs_title       = max(28.0, _fs_base * 2.4)
    _fs_subtitle    = max(14.0, _fs_base * 1.15)
    _fs_col_header  = max(12.0, _fs_base * 0.95)              # DROP-OFF / STAGE / CUMULATIVE
    _fs_drop_big    = max(16.0, _fs_body_stage * 1.15)        # 左侧 −XX%
    _fs_drop_sub    = max(11.0, _fs_body_stage * 0.8)
    _fs_cum_pct     = max(13.0, _fs_body_stage * 0.95)
    _fs_insight_hdr = max(11.0, _fs_base * 0.9)
    _fs_insight_big = max(24.0, _fs_base * 2.0)
    _fs_insight_sub = max(11.0, _fs_body_stage * 0.8)
    _fs_note        = max(11.0, _fs_body_stage * 0.85)
    _fs_narrow_lbl  = max(12.0, _fs_body_stage * 0.9)
    _fs_narrow_val  = max(15.0, _fs_body_stage * 1.15)

    parts = []
    if c_bg:
        parts.append(f'<rect width="{width}" height="{height}" fill="{PAPER}"/>')

    # ---------- 顶部标题 ----------
    if title:
        parts.append(f'<text x="{MARGIN_L}" y="52" '
                     f'font-family="{_head_font}" '
                     f'font-size="{_fs_title}" font-weight="600" fill="{_INK}" letter-spacing=".05em">'
                     f'{_xesc(title)}</text>')
    if subtitle:
        parts.append(f'<text x="{MARGIN_L}" y="76" '
                     f'font-family="{_body_font}" font-size="{_fs_subtitle}" fill="{c_muted}" '
                     f'letter-spacing=".16em">{_xesc(subtitle)}</text>')
        parts.append(f'<line x1="{MARGIN_L}" y1="92" x2="{width-MARGIN_R}" y2="92" '
                     f'stroke="{_INK}" stroke-width="0.8"/>')
    if figure_label:
        parts.append(f'<text x="{MARGIN_L}" y="112" font-family="{_body_font}" font-size="{_fs_col_header}" '
                     f'fill="{c_muted}" font-weight="600" letter-spacing=".15em">{_xesc(figure_label)}</text>')
        lbl_w = max(72, len(figure_label) * 8 + 20)
        parts.append(f'<text x="{MARGIN_L+lbl_w}" y="112" font-family="{_body_font}" font-size="{_fs_col_header}" '
                     f'fill="{c_muted}" letter-spacing=".04em">'
                     f'{_xesc(f"Funnel width proportional to user count · {n} stages")}</text>')

    # ---------- 列头 ----------
    if show_drop_off:
        parts.append(f'<text x="{MARGIN_L}" y="{plot_y - 12}" font-family="{_body_font}" '
                     f'font-size="{_fs_col_header}" font-weight="600" fill="{c_muted}" letter-spacing=".15em">DROP-OFF</text>')
    parts.append(f'<text x="{funnel_cx:.1f}" y="{plot_y - 12}" text-anchor="middle" '
                 f'font-family="{_body_font}" font-size="{_fs_col_header}" font-weight="600" fill="{c_muted}" '
                 f'letter-spacing=".15em">STAGE</text>')
    if show_cumulative:
        parts.append(f'<text x="{width-MARGIN_R}" y="{plot_y - 12}" text-anchor="end" '
                     f'font-family="{_body_font}" font-size="{_fs_col_header}" font-weight="600" fill="{c_muted}" '
                     f'letter-spacing=".15em">CUMULATIVE CONVERSION</text>')

    # 涨/跌红 & 绿色（沿用金融印刷风固定色，独立于 palette 保证语义清晰）
    RED_COL = _pal.get("funnel_drop_color", "rgba(194,93,93,1)")
    GREEN_COL = _pal.get("funnel_strong_color", "rgba(60,105,148,1)")

    # ---------- 漏斗梯形 ----------
    for i in range(n):
        name = stage_labels[i]
        count = stages[i]
        desc = stage_descriptions[i] if stage_descriptions else None
        color = stage_colors[i]
        r_, g_, b_ = _rgb_tuple(color)
        yt = row_top(i); yb = row_bot(i)

        top_w = width_of(i)
        bot_w = top_w if i == n - 1 else width_of(i + 1)
        x1t = funnel_cx - top_w / 2
        x2t = funnel_cx + top_w / 2
        x1b = funnel_cx - bot_w / 2
        x2b = funnel_cx + bot_w / 2

        d = f'M {x1t:.1f} {yt:.1f} L {x2t:.1f} {yt:.1f} L {x2b:.1f} {yb:.1f} L {x1b:.1f} {yb:.1f} Z'
        parts.append(f'<path d="{d}" fill="rgba({r_},{g_},{b_},0.88)"/>')
        parts.append(f'<rect x="{x1t:.1f}" y="{yt:.1f}" width="{top_w:.1f}" height="2.2" fill="{color}"/>')

        mid_y = (yt + yb) / 2

        # 判断放内还是外
        if top_w >= 200:
            # 内部标签：根据背景亮度选文字色
            cell_luma = 0.299 * r_ + 0.587 * g_ + 0.114 * b_
            if cell_luma < 128:
                text_col = "rgba(255,255,255,0.98)"
                sub_col = "rgba(240,242,246,0.85)"
            else:
                text_col = "rgba(30,32,38,0.9)"
                sub_col = "rgba(60,64,72,0.75)"
            # 字号自适应：随 viewBox / stage 数缩放；保证 slide 里也能看清
            # 上下 baseline 间距 = _fs_value_stage * 1.2（避免 embed_svg_validator bbox 撞）
            _gap_val = max(20.0, _fs_value_stage * 1.25)
            # label baseline：先按对称居中算，再向下 clamp，保证 label 文本上边
            # （baseline - fs*0.8）不越过梯形顶边 yt（含 2.2px 顶部装饰 rect + 1px 安全间距）。
            _label_baseline_ideal = mid_y - _gap_val * 0.65
            _label_top_min = yt + 2.2 + 1.0                    # 装饰 rect 下沿 + safety
            _label_baseline_min = _label_top_min + _fs_body_stage * 0.8
            _label_baseline = max(_label_baseline_ideal, _label_baseline_min)
            # 若上移后 value baseline 会跟 label bbox 挤在一起，同幅度下移 value / desc
            _label_shift = _label_baseline - _label_baseline_ideal
            _value_baseline = mid_y + _gap_val * 0.35 + _label_shift
            parts.append(f'<text x="{funnel_cx:.1f}" y="{_label_baseline:.1f}" text-anchor="middle" '
                         f'font-family="{_body_font}" font-size="{_fs_body_stage}" font-weight="600" '
                         f'fill="{text_col}">{_xesc(str(name))}</text>')
            parts.append(f'<text x="{funnel_cx:.1f}" y="{_value_baseline:.1f}" text-anchor="middle" '
                         f'font-family="{_head_font}" font-size="{_fs_value_stage}" font-weight="700" '
                         f'fill="{text_col}">{_xesc(f"{count:,}")}</text>')
            if desc:
                # desc baseline 位置：value baseline 下方 fs_desc + 4。需保证 desc bbox
                # 完全在 stage row 内（否则会与下一 stage 的 label bbox 相交 → embed_svg_bbox_overlap）。
                _desc_baseline = _value_baseline + _fs_desc_stage + 4
                _desc_bbox_bot = _desc_baseline + _fs_desc_stage * 0.2
                if _desc_bbox_bot <= yb - 1.0:
                    parts.append(f'<text x="{funnel_cx:.1f}" y="{_desc_baseline:.1f}" text-anchor="middle" '
                                 f'font-family="{_body_font}" font-size="{_fs_desc_stage}" fill="{sub_col}" '
                                 f'font-style="italic">{_xesc(str(desc))}</text>')
        else:
            # 窄层：标签在漏斗右侧
            edge_x = funnel_cx + max(top_w, bot_w) / 2 + 2
            lead_end = edge_x + 18
            parts.append(f'<line x1="{edge_x:.1f}" y1="{mid_y:.1f}" x2="{lead_end:.1f}" y2="{mid_y:.1f}" '
                         f'stroke="{_INK4}" stroke-width="0.6"/>')
            # narrow layer 用相对小一档字号
            tx = lead_end + 4
            parts.append(f'<text x="{tx:.1f}" y="{mid_y - _fs_narrow_val*0.6:.1f}" '
                         f'font-family="{_body_font}" font-size="{_fs_narrow_lbl}" font-weight="600" '
                         f'fill="{_INK}">{_xesc(str(name))}</text>')
            parts.append(f'<text x="{tx:.1f}" y="{mid_y + _fs_narrow_val*0.55:.1f}" '
                         f'font-family="{_head_font}" font-size="{_fs_narrow_val}" font-weight="700" '
                         f'fill="{_INK}">{_xesc(f"{count:,}")}</text>')
            if desc:
                parts.append(f'<text x="{tx:.1f}" y="{mid_y + _fs_narrow_val*0.55 + _fs_desc_stage + 4:.1f}" '
                             f'font-family="{_body_font}" font-size="{_fs_desc_stage}" fill="{c_muted}" '
                             f'font-style="italic">{_xesc(str(desc))}</text>')

    # ---------- 左侧 DROP-OFF 面板 ----------
    if show_drop_off:
        for i in range(n - 1):
            lost = stages[i] - stages[i+1]
            if lost <= 0:
                continue
            lost_rate = lost / stages[i] * 100
            y = row_bot(i) + row_gap / 2
            label_x = plot_x - 10
            # big "-XX%" 与 sub "NN dropped" 在同一 gutter 里两行，baseline 差需
            # ≥ fs_drop_big*0.2 + fs_drop_sub*0.8 + 2px（否则 fs≥17 时 bbox 相交）。
            _big_baseline_offset = -4
            _sub_baseline_offset = _big_baseline_offset + _fs_drop_big * 0.2 + _fs_drop_sub * 0.8 + 3.0
            parts.append(f'<text x="{label_x}" y="{y + _big_baseline_offset:.1f}" text-anchor="end" '
                         f'font-family="{_head_font}" font-size="{_fs_drop_big}" font-weight="700" '
                         f'fill="{RED_COL}">−{lost_rate:.1f}%</text>')
            parts.append(f'<text x="{label_x}" y="{y + _sub_baseline_offset:.1f}" text-anchor="end" '
                         f'font-family="{_body_font}" font-size="{_fs_drop_sub}" '
                         f'fill="{c_muted}">{_xesc(f"{lost:,} dropped")}</text>')
            # 引线
            x_from = label_x + 4
            x_arrow = funnel_cx - width_of(i) / 2 - 6
            if x_arrow > x_from:
                red_dim = _rgba_with_alpha(RED_COL, 0.55)
                red_solid = _rgba_with_alpha(RED_COL, 0.85)
                parts.append(f'<line x1="{x_from}" y1="{y:.1f}" x2="{x_arrow:.1f}" y2="{y:.1f}" '
                             f'stroke="{red_dim}" stroke-width="0.8" stroke-dasharray="2 2"/>')
                parts.append(f'<polygon points="{x_arrow+6:.1f},{y:.1f} {x_arrow-2:.1f},{y-3:.1f} '
                             f'{x_arrow-2:.1f},{y+3:.1f}" fill="{red_solid}"/>')

    # ---------- 右侧 CUMULATIVE 面板 ----------
    if show_cumulative:
        right_x_bar_start = funnel_cx + plot_w_max / 2 + 240
        right_x_end = width - MARGIN_R
        right_x_bar_end = right_x_end - 60
        # 若窄层标签占空间导致 bar_start < end - 100，兜底调整
        if right_x_bar_end - right_x_bar_start < 60:
            # 缩短 bar 面板
            right_x_bar_start = funnel_cx + plot_w_max / 2 + 180
        bar_area_w = right_x_bar_end - right_x_bar_start
        for i in range(n):
            count = stages[i]
            y_mid = (row_top(i) + row_bot(i)) / 2
            conv = count / top_count * 100
            bar_h = 10
            by = y_mid - bar_h / 2
            parts.append(f'<rect x="{right_x_bar_start:.1f}" y="{by:.1f}" width="{bar_area_w:.1f}" '
                         f'height="{bar_h}" fill="{_rgba_with_alpha(_INK, 0.05)}" rx="2"/>')
            fill_w = bar_area_w * count / top_count
            color = stage_colors[i]
            # Inset the fill bar 1px vertically inside the track so bg/fill never share an
            # identical bbox (validator flags exact-duplicate rects). Visually reads as a
            # progress bar seated inside a lighter track.
            parts.append(f'<rect x="{right_x_bar_start:.1f}" y="{by + 1:.1f}" width="{fill_w:.1f}" '
                         f'height="{bar_h - 2}" fill="{_rgba_with_alpha(color, 0.9)}" rx="2"/>')
            parts.append(f'<text x="{right_x_bar_end + 8:.1f}" y="{y_mid + 4:.1f}" text-anchor="start" '
                         f'font-family="{_body_font}" font-size="{_fs_cum_pct}" font-weight="600" '
                         f'fill="{_INK}">{conv:.1f}%</text>')

    # ---------- 底部洞察卡片 ----------
    if show_insights:
        insight_y = row_bot(n - 1) + 30
        insight_x = MARGIN_L
        insight_area_w = width - MARGIN_L - MARGIN_R
        insight_w = (insight_area_w - 40) / 3
        insight_gap = 20
        overall_conv = stages[-1] / stages[0] * 100
        drop_rates = [(1 - stages[i+1] / stages[i]) for i in range(n - 1)]
        biggest_drop_i = max(range(n-1), key=lambda i: drop_rates[i])
        biggest_drop_pct = drop_rates[biggest_drop_i] * 100
        best_conv_i = min(range(n-1), key=lambda i: drop_rates[i])
        best_conv_pct = (1 - drop_rates[best_conv_i]) * 100
        insights = [
            ("OVERALL CONVERSION", f"{overall_conv:.2f}%",
             f"{stages[0]:,} → {stages[-1]:,}"),
            ("BIGGEST DROP-OFF", f"−{biggest_drop_pct:.0f}%",
             f"{stage_labels[biggest_drop_i]} → {stage_labels[biggest_drop_i+1]}"),
            ("STRONGEST STEP", f"{best_conv_pct:.0f}%",
             f"{stage_labels[best_conv_i]} → {stage_labels[best_conv_i+1]}"),
        ]
        # 动态 baseline：hdr → big → sub，间距按字号自适应确保 bbox 不相交（同 KPI 布局）。
        _pad_top = 20.0
        _gap_line = 4.0
        _hdr_baseline = _pad_top
        _big_baseline = _hdr_baseline + _fs_insight_hdr * 0.2 + _fs_insight_big * 0.8 + _gap_line
        _sub_baseline = _big_baseline + _fs_insight_big * 0.2 + _fs_insight_sub * 0.8 + _gap_line
        _insight_h = max(70.0, _sub_baseline + _fs_insight_sub * 0.2 + 10.0)
        for i, (label, big, sub) in enumerate(insights):
            ix = insight_x + i * (insight_w + insight_gap)
            parts.append(f'<rect x="{ix:.1f}" y="{insight_y}" width="{insight_w:.1f}" height="{_insight_h:.1f}" '
                         f'fill="{_rgba_with_alpha(_INK, 0.03)}" stroke="{_INK4}" stroke-width="0.8"/>')
            accent = RED_COL if i == 1 else GREEN_COL
            parts.append(f'<rect x="{ix:.1f}" y="{insight_y}" width="4" height="{_insight_h:.1f}" fill="{accent}"/>')
            parts.append(f'<text x="{ix+16:.1f}" y="{insight_y+_hdr_baseline:.1f}" font-family="{_body_font}" '
                         f'font-size="{_fs_insight_hdr}" fill="{c_muted}" font-weight="600" letter-spacing=".15em">'
                         f'{_xesc(label)}</text>')
            big_col = RED_COL if i == 1 else _INK
            parts.append(f'<text x="{ix+16:.1f}" y="{insight_y+_big_baseline:.1f}" font-family="{_head_font}" '
                         f'font-size="{_fs_insight_big}" fill="{big_col}" font-weight="700">{_xesc(big)}</text>')
            parts.append(f'<text x="{ix+16:.1f}" y="{insight_y+_sub_baseline:.1f}" font-family="{_body_font}" '
                         f'font-size="{_fs_insight_sub}" fill="{c_muted}">{_xesc(sub)}</text>')

    # ---------- 底部脚注 ----------
    if note:
        foot_y = height - 32
        parts.append(f'<line x1="{MARGIN_L}" y1="{foot_y-14}" x2="{width-MARGIN_R}" y2="{foot_y-14}" '
                     f'stroke="{_INK4}" stroke-width="0.5"/>')
        parts.append(f'<text x="{MARGIN_L}" y="{foot_y}" font-family="{_body_font}" '
                     f'font-size="{_fs_note}" fill="{c_muted}">'
                     f'<tspan font-weight="600">Notes.</tspan> {_xesc(note)}</text>')
        if figure_label:
            parts.append(f'<text x="{width-MARGIN_R}" y="{foot_y}" text-anchor="end" '
                         f'font-family="{_body_font}" font-size="{max(10.0, _fs_note*0.9)}" fill="{c_muted}" '
                         f'letter-spacing=".05em">{_xesc(figure_label)}</text>')

    body = "".join(parts)
    _svg_result = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {int(width)} {int(height)}">{body}</svg>'
    return _prepend_bg_if_dark(_svg_result, _pal)


# ==============================================================
# 9b) Percent Grid 百人网格 (Financial-print, 10×10 grid + breakdown band + KPIs)
# ==============================================================
