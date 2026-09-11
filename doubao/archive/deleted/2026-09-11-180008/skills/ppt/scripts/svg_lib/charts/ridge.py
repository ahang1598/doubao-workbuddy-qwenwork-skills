"""svg_lib/charts/ridge.py

统一 API: draw_ridge(data, variant, palette, ...) -> str (SVG)

Data schema:
    data = {
        "groups": [(label, [samples]), ...],  # 每组原始样本
        "unit": str | None,
    }
    draw 内部会用 KDE 把 samples 转成密度曲线。

Variants (5 共享 groups):
    - default_flat          overlap + fill (baseline)
    - outlined_separated   分离 + 只描边
    - gradient_overlap      overlap + 水平渐变填充
    - joy_division          overlap + 黑底白线 (Joy Division homage)
    - histogram_binned     分离 + histogram bins
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


from .._common import (_ACC, _INK, _INK1, _INK2, _INK4, _INK6, _derive_series_colors, _prepend_bg_if_dark, _resolve_font, _resolve_palette, _rgb_tuple, _rgba_with_alpha, _xesc, ridge_density_from_samples, _variant_is_classic, _dispatch_to_svg_lib, _estimate_label_width_px)
BODY_FONT = "Inter, sans-serif"
HEAD_FONT = "Georgia, serif"


def draw_ridge(
    data: dict,
    variant: str = "default_flat",
    palette: str = "archive_ink",
    width: float = 900,
    height: float = 540,
    title: str = None,
    subtitle: str = None,
) -> str:
    groups = data.get("groups") or []
    if len(groups) < 2:
        raise ValueError("draw_ridge: need at least 2 groups")

    labels = [str(g[0]) for g in groups]
    samples_per_group = [list(g[1]) for g in groups]
    all_samples = [s for row in samples_per_group for s in row]
    if not all_samples:
        raise ValueError("draw_ridge: no samples")

    x_min = min(all_samples)
    x_max = max(all_samples)
    pad = (x_max - x_min) * 0.05 or 1.0
    x_min -= pad
    x_max += pad

    unit = data.get("unit") or ""
    pal = resolve_palette(palette)

    ctx = _Ctx(labels, samples_per_group, x_min, x_max, unit, pal,
               float(width), float(height), title, subtitle)

    if variant == "default_flat":
        body = _draw_default_flat(ctx)
    elif variant == "outlined_separated":
        body = _draw_outlined_separated(ctx)
    elif variant == "gradient_overlap":
        body = _draw_gradient_overlap(ctx)
    elif variant == "joy_division":
        body = _draw_joy_division(ctx)
    elif variant == "histogram_binned":
        body = _draw_histogram_binned(ctx)
    else:
        raise ValueError(
            f"unknown variant {variant!r}. Supported: default_flat, outlined_separated, "
            "gradient_overlap, joy_division, histogram_binned"
        )

    return (
        svg_open(0, 0, ctx.W, ctx.H, bg=pal["bg"])
        + ctx.defs_svg()
        + _header(ctx)
        + body
        + svg_close()
    )


class _Ctx:
    def __init__(self, labels, samples, x_min, x_max, unit, pal, W, H, title, subtitle):
        self.labels = labels
        self.samples = samples
        self.x_min = x_min
        self.x_max = x_max
        self.unit = unit
        self.pal = pal
        self.W = W
        self.H = H
        self.title = title
        self.subtitle = subtitle
        self.n = len(labels)

        self.ML = 100
        self.MR = 40
        self.header_h = 20
        if title:
            self.header_h = 44
        if subtitle:
            self.header_h += 18

        self.plot_top = self.header_h + 14
        self.plot_bot = H - 40
        self.plot_h = self.plot_bot - self.plot_top
        self.plot_w = W - self.ML - self.MR

        # ---- 字号自适应（viewBox 短边 × 数据规模双重挂钩）----
        # SVG 字号相对 viewBox；slide embed 缩到 ~400px 时字号视觉缩 1/(W/400)。
        # 让 body 字号 ≥ 短边 * 2.4%，并按 n 退让。
        from .._common import _dist_font_sizes
        _fs = _dist_font_sizes(W, H, self.n)
        self.fs_label    = _fs["label"]
        self.fs_axis     = _fs["ytick"]
        self.fs_title    = _fs["title"]
        self.fs_subtitle = _fs["subtitle"]

        # Adaptive left margin: reserve enough room for the longest label so
        # long strings like "CLAUDE 3.5 SONNET" / "GEMINI 2.5 PRO" aren't clipped.
        # The previous "0.62 * fs_label" heuristic ignored per-glyph advances,
        # bold weight (Inter 700), and letter-spacing (.05-.08em); for uppercase
        # model names it under-reserved by 40-70px. Now we use the same per-glyph
        # model as embed_svg_validator so the two agree exactly.
        # Labels are rendered at x = ML - 10 with text-anchor="end", so we need
        # ML >= max_label_width + 10 + safety_pad.
        # joy_division uses letter-spacing=".08em"; other variants use ".05em".
        # We pass .08 to cover the worst case for every variant.
        max_label_px = max(
            (_estimate_label_width_px(lbl, self.fs_label, 0.08, bold=True,
                                      font_family=BODY_FONT) for lbl in labels),
            default=0.0,
        )
        # 10 = anchor offset used in text templates; +8 outer safety pad so
        # we clear OUT_OF_BOUNDS_MARGIN_PX (2px) plus rendering slack.
        self.ML = max(100, int(math.ceil(max_label_px + 10 + 8)))

        # Recompute plot_w now that ML may have grown.
        self.plot_w = W - self.ML - self.MR

        self._defs = []

    def add_def(self, s):
        self._defs.append(s)

    def defs_svg(self):
        return "<defs>" + "".join(self._defs) + "</defs>" if self._defs else ""

    def series_color(self, i):
        series = self.pal.get("series") or [self.pal["accent"]]
        return series[i % len(series)]

    def x_to_px(self, v):
        return self.ML + (v - self.x_min) / (self.x_max - self.x_min) * self.plot_w


def _header(ctx: _Ctx) -> str:
    ink = ctx.pal["ink"]
    mut = ctx.pal["muted"]
    parts = []
    ML = ctx.ML
    if ctx.title:
        # In joy_division dark bg, use bright text
        text_col = ink
        parts.append(
            f'<text x="{ML}" y="30" font-family="{HEAD_FONT}" font-size="{ctx.fs_title}" '
            f'font-weight="600" fill="{text_col}" letter-spacing=".03em">{xesc(ctx.title)}</text>'
        )
    if ctx.subtitle:
        y = 48 if ctx.title else 30
        parts.append(
            f'<text x="{ML}" y="{y}" font-family="{BODY_FONT}" font-size="{ctx.fs_subtitle}" '
            f'fill="{mut}" letter-spacing=".14em">{xesc(ctx.subtitle)}</text>'
        )
    if ctx.title:
        parts.append(
            f'<line x1="{ML}" y1="{ctx.header_h}" x2="{ctx.W - ctx.MR}" y2="{ctx.header_h}" '
            f'stroke="{ink}" stroke-width="0.6" opacity="0.4"/>'
        )
    return "".join(parts)


def _kde(samples, x_min, x_max, n=80, bandwidth=None):
    """Simple gaussian KDE."""
    if not samples:
        return [0.0] * n
    N = len(samples)
    mean = sum(samples) / N
    var = sum((s - mean) ** 2 for s in samples) / max(1, N - 1)
    std = math.sqrt(var) if var > 0 else max((x_max - x_min) * 0.01, 1e-6)
    if bandwidth is None:
        bandwidth = 1.06 * std * (N ** -0.2)
    bandwidth = max(bandwidth, (x_max - x_min) * 1e-4)
    step = (x_max - x_min) / (n - 1) if n > 1 else (x_max - x_min)
    inv_2h2 = 1.0 / (2.0 * bandwidth * bandwidth)
    coeff = 1.0 / (bandwidth * math.sqrt(2 * math.pi))
    out = []
    for i in range(n):
        x = x_min + i * step
        d = 0.0
        for s in samples:
            dd = x - s
            d += math.exp(-dd * dd * inv_2h2)
        out.append(d * coeff / N)
    return out


def _axis_bottom(ctx: _Ctx, y):
    """Bottom x-axis with ticks."""
    ink = ctx.pal["ink"]
    mut = ctx.pal["muted"]
    parts = []
    parts.append(
        f'<line x1="{ctx.ML}" y1="{y:.1f}" x2="{ctx.W - ctx.MR}" y2="{y:.1f}" '
        f'stroke="{ink}" stroke-width="0.6" opacity="0.5"/>'
    )
    for k in range(9):
        t = ctx.x_min + (ctx.x_max - ctx.x_min) * k / 8
        px = ctx.x_to_px(t)
        parts.append(
            f'<text x="{px:.1f}" y="{y + 14:.1f}" text-anchor="middle" '
            f'font-family="{BODY_FONT}" font-size="{ctx.fs_axis}" fill="{mut}">'
            f'{t:.1f}{xesc(ctx.unit)}</text>'
        )
    return "".join(parts)


# ============================================================
# variant 1: default_flat (overlap + filled)
# ============================================================
def _draw_default_flat(ctx: _Ctx) -> str:
    parts = []
    N = ctx.n
    ridge_h = 60
    row_step = max(20.0, (ctx.plot_h - ridge_h - 30) / max(1, N - 1))

    # baseline for axis
    axis_y = ctx.plot_top + (N - 1) * row_step + ridge_h + 8

    parts.append(_axis_bottom(ctx, axis_y))

    # draw from bottom (i=N-1) up, so top rows are drawn later and cover
    for i in range(N - 1, -1, -1):
        dist = _kde(ctx.samples[i], ctx.x_min, ctx.x_max, n=80)
        y_base = ctx.plot_top + i * row_step + ridge_h
        vmax = max(dist) or 1.0
        col = ctx.series_color(i)
        n_pts = len(dist)
        xs = [ctx.ML + k * ctx.plot_w / (n_pts - 1) for k in range(n_pts)]
        ys = [y_base - v / vmax * ridge_h for v in dist]

        line_d = "M " + " L ".join(f"{px:.1f} {py:.1f}" for px, py in zip(xs, ys))
        fill_d = line_d + f" L {xs[-1]:.1f} {y_base:.1f} L {xs[0]:.1f} {y_base:.1f} Z"

        parts.append(
            f'<path d="{fill_d}" fill="{_rgba_with_alpha(col, 0.55)}" '
            f'stroke="{_rgba_with_alpha(col, 0.9)}" stroke-width="1"/>'
        )
        # label
        parts.append(
            f'<text x="{ctx.ML - 10:.1f}" y="{y_base - 3:.1f}" text-anchor="end" '
            f'font-family="{BODY_FONT}" font-size="{ctx.fs_label}" '
            f'font-weight="700" fill="{col}" letter-spacing=".05em">{xesc(ctx.labels[i])}</text>'
        )

    return "".join(parts)


# ============================================================
# variant 2: outlined_separated
# ============================================================
def _draw_outlined_separated(ctx: _Ctx) -> str:
    parts = []
    ink = ctx.pal["ink"]
    mut = ctx.pal["muted"]
    N = ctx.n
    # separated: taller row_step relative to ridge_h
    row_step = ctx.plot_h / max(1, N)
    ridge_h = min(60, row_step * 0.7)

    axis_y = ctx.plot_top + (N - 1) * row_step + ridge_h + 8
    parts.append(_axis_bottom(ctx, axis_y))

    for i in range(N - 1, -1, -1):
        dist = _kde(ctx.samples[i], ctx.x_min, ctx.x_max, n=80)
        y_base = ctx.plot_top + i * row_step + ridge_h
        vmax = max(dist) or 1.0
        col = ctx.series_color(i)
        n_pts = len(dist)
        xs = [ctx.ML + k * ctx.plot_w / (n_pts - 1) for k in range(n_pts)]
        ys = [y_base - v / vmax * ridge_h for v in dist]

        line_d = "M " + " L ".join(f"{px:.1f} {py:.1f}" for px, py in zip(xs, ys))
        # baseline
        parts.append(
            f'<line x1="{ctx.ML}" y1="{y_base:.1f}" x2="{ctx.W - ctx.MR}" y2="{y_base:.1f}" '
            f'stroke="{_rgba_with_alpha(ink, 0.15)}" stroke-width="0.8"/>'
        )
        # outlined (stroke only, no fill)
        parts.append(
            f'<path d="{line_d}" fill="none" stroke="{col}" stroke-width="1.8"/>'
        )
        # label
        parts.append(
            f'<text x="{ctx.ML - 10:.1f}" y="{y_base - 3:.1f}" text-anchor="end" '
            f'font-family="{BODY_FONT}" font-size="{ctx.fs_label}" '
            f'font-weight="700" fill="{col}" letter-spacing=".05em">{xesc(ctx.labels[i])}</text>'
        )
    return "".join(parts)


# ============================================================
# variant 3: gradient_overlap
# ============================================================
def _draw_gradient_overlap(ctx: _Ctx) -> str:
    """Per-ridge vertical gradient in the series color, so ridge fill hue
    always matches its label color."""
    parts = []
    N = ctx.n
    ridge_h = 60
    row_step = max(20.0, (ctx.plot_h - ridge_h - 30) / max(1, N - 1))
    axis_y = ctx.plot_top + (N - 1) * row_step + ridge_h + 8
    parts.append(_axis_bottom(ctx, axis_y))

    for i in range(N - 1, -1, -1):
        col = ctx.series_color(i)
        r, g, b = rgb_tuple(col)
        # Vertical gradient in the SAME hue as the series/label:
        # deeper/darker at the peak (top), softer near the baseline (bottom).
        gid = f"__ridge_grad_{i}"
        ctx.add_def(
            f'<linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0%" stop-color="rgba({r},{g},{b},0.92)"/>'
            f'<stop offset="100%" stop-color="rgba({r},{g},{b},0.35)"/>'
            f'</linearGradient>'
        )

        dist = _kde(ctx.samples[i], ctx.x_min, ctx.x_max, n=80)
        y_base = ctx.plot_top + i * row_step + ridge_h
        vmax = max(dist) or 1.0
        n_pts = len(dist)
        xs = [ctx.ML + k * ctx.plot_w / (n_pts - 1) for k in range(n_pts)]
        ys = [y_base - v / vmax * ridge_h for v in dist]

        line_d = "M " + " L ".join(f"{px:.1f} {py:.1f}" for px, py in zip(xs, ys))
        fill_d = line_d + f" L {xs[-1]:.1f} {y_base:.1f} L {xs[0]:.1f} {y_base:.1f} Z"

        parts.append(
            f'<path d="{fill_d}" fill="url(#{gid})" '
            f'stroke="rgba({r},{g},{b},0.95)" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{ctx.ML - 10:.1f}" y="{y_base - 3:.1f}" text-anchor="end" '
            f'font-family="{BODY_FONT}" font-size="{ctx.fs_label}" '
            f'font-weight="700" fill="{col}" letter-spacing=".05em">{xesc(ctx.labels[i])}</text>'
        )
    return "".join(parts)


# ============================================================
# variant 4: joy_division (dark bg, occluding white lines)
# ============================================================
def _draw_joy_division(ctx: _Ctx) -> str:
    parts = []
    bg = ctx.pal["bg"]
    ink = ctx.pal["ink"]
    N = ctx.n
    # Adaptive row_step + ridge_h to fill the plot area regardless of N.
    # Budget for the axis label strip: 22px. For N groups we want
    #   plot_top + (N-1)*row_step + ridge_h + 8 + axis_pad ≈ plot_bot.
    #
    # Historically this variant used `ridge_h = 1.6 * row_step`, which made
    # each curve overshoot into the row ABOVE by 0.6 * row_step. With labels
    # anchored at `y_base - 3` (i.e. at each curve's baseline), that overshoot
    # made the top-most curve's peak visually protrude above G1's label with
    # no label of its own, and every subsequent label appeared to "belong to"
    # the curve above it. Cap `ridge_h` at `row_step` so each curve stays
    # within its own uniformly-spaced row band and labels align with the
    # curve they actually annotate. A small `0.95` factor keeps a hint of the
    # Joy Division overlap aesthetic (peaks just kiss the row above) without
    # crossing into the next label's territory.
    axis_pad = 22
    denom = max(1.0, float(N))  # N rows of height row_step fill plot_h
    row_step = max(18.0, min(80.0, (ctx.plot_h - axis_pad - 8) / denom))
    ridge_h = max(40.0, row_step * 0.95)
    axis_y = ctx.plot_top + (N - 1) * row_step + ridge_h + 8

    # draw top to bottom: later rows drawn on top -> occlude
    for i in range(N):
        dist = _kde(ctx.samples[i], ctx.x_min, ctx.x_max, n=80)
        y_base = ctx.plot_top + i * row_step + ridge_h
        vmax = max(dist) or 1.0
        n_pts = len(dist)
        xs = [ctx.ML + k * ctx.plot_w / (n_pts - 1) for k in range(n_pts)]
        ys = [y_base - v / vmax * ridge_h for v in dist]

        line_d = "M " + " L ".join(f"{px:.1f} {py:.1f}" for px, py in zip(xs, ys))
        fill_d = line_d + f" L {xs[-1]:.1f} {y_base:.1f} L {xs[0]:.1f} {y_base:.1f} Z"

        # bg fill to occlude
        parts.append(f'<path d="{fill_d}" fill="{bg}"/>')
        # white stroke
        line_color = "rgba(240,240,232,0.95)" if is_dark_palette(ctx.pal) else ink
        parts.append(
            f'<path d="{line_d}" fill="none" stroke="{line_color}" stroke-width="1.2"/>'
        )
        # label
        lbl_col = ctx.series_color(i) if not is_dark_palette(ctx.pal) else "rgba(212,233,44,0.85)"
        parts.append(
            f'<text x="{ctx.ML - 10:.1f}" y="{y_base - 3:.1f}" text-anchor="end" '
            f'font-family="{BODY_FONT}" font-size="{ctx.fs_label}" '
            f'font-weight="600" fill="{lbl_col}" letter-spacing=".08em">'
            f'{xesc(ctx.labels[i])}</text>'
        )

    # x-axis (drawn after ridges so it stays on top)
    parts.append(_axis_bottom(ctx, axis_y))
    return "".join(parts)


# ============================================================
# variant 5: histogram_binned
# ============================================================
def _draw_histogram_binned(ctx: _Ctx) -> str:
    parts = []
    ink = ctx.pal["ink"]
    N = ctx.n
    ridge_h = 56
    row_step = max(20.0, (ctx.plot_h - ridge_h - 30) / max(1, N - 1))
    axis_y = ctx.plot_top + (N - 1) * row_step + ridge_h + 8

    n_bins = 22
    bin_w = ctx.plot_w / n_bins

    parts.append(_axis_bottom(ctx, axis_y))

    for i in range(N - 1, -1, -1):
        # histogram bin
        counts = [0] * n_bins
        for s in ctx.samples[i]:
            if ctx.x_min <= s <= ctx.x_max:
                bi = min(n_bins - 1, int((s - ctx.x_min) / (ctx.x_max - ctx.x_min) * n_bins))
                counts[bi] += 1
        col = ctx.series_color(i)
        r, g, b = rgb_tuple(col)
        y_base = ctx.plot_top + i * row_step + ridge_h
        vmax = max(counts) or 1
        parts.append(
            f'<line x1="{ctx.ML}" y1="{y_base:.1f}" x2="{ctx.W - ctx.MR}" y2="{y_base:.1f}" '
            f'stroke="{_rgba_with_alpha(ink, 0.15)}" stroke-width="0.8"/>'
        )
        for bi, c in enumerate(counts):
            h = c / vmax * ridge_h
            x0 = ctx.ML + bi * bin_w
            y0 = y_base - h
            parts.append(
                f'<rect x="{x0 + 0.8:.1f}" y="{y0:.1f}" width="{bin_w - 1.6:.1f}" '
                f'height="{h:.1f}" fill="rgba({r},{g},{b},0.55)" '
                f'stroke="rgba({r},{g},{b},0.95)" stroke-width="0.7"/>'
            )
        parts.append(
            f'<text x="{ctx.ML - 10:.1f}" y="{y_base - 3:.1f}" text-anchor="end" '
            f'font-family="{BODY_FONT}" font-size="{ctx.fs_label}" '
            f'font-weight="700" fill="{col}" letter-spacing=".05em">{xesc(ctx.labels[i])}</text>'
        )
    return "".join(parts)


def make_ridge(distributions: Sequence[Sequence[float]],
               group_labels: Sequence[str] = None,
               x_range: Sequence[float] = None,
               x_labels: Sequence[str] = None,
               title: str = None,
               subtitle: str = None,
               highlight_index: int = None,
               font_family: str = None,
               palette=None,
                variant: str = None) -> str:
    """
    山脊图（Joy plot / Ridge plot · dandelion 风格）：N 组分布纵向堆叠对比，
    渐变填充 + 柔光顶线 + 群峰重叠。

    distributions: N 组预计算的密度值（每组等长）。原始样本用 ridge_density_from_samples 先做 KDE。
    group_labels:  N 个组名
    x_range:       (x_min, x_max) 用于底部刻度
    x_labels:      自定义底部刻度标签列表；不传则按 x_range 自动 nice-number 刻度
    title/subtitle: 顶部标题
    highlight_index: 高亮某组（描边加粗）
    palette:       用 palette.series 或从 accent HLS 派生 N 色环形调色板
    """
    if not _variant_is_classic('ridge', variant):
        _data = {"groups": list(zip(group_labels or [f"G{i}" for i in range(len(distributions))], distributions))}
        return _dispatch_to_svg_lib(
            'ridge', variant, _data,
            title=title, subtitle=subtitle,
            palette=palette, font_family=font_family,
        )

    _pal = _resolve_palette(palette)
    _body_font, _head_font = _resolve_font(font_family)
    _INK, _INK6, _INK4, _INK2, _INK1, _ACC = (
        _pal["ink"], _pal["ink6"], _pal["ink4"], _pal["ink2"], _pal["ink1"], _pal["accent"]
    )
    c_muted = _pal.get("muted", _rgba_with_alpha(_INK, 0.6))

    N = len(distributions)
    if N < 1:
        raise ValueError("ridge: at least one distribution required")
    lengths = {len(d) for d in distributions}
    if len(lengths) > 1:
        raise ValueError(f"ridge: all distributions must be same length, got lengths={lengths}. "
                         f"Use `ridge_density_from_samples(samples, x_min, x_max, n)` to normalize sample sizes.")
    if group_labels is None:
        group_labels = [f"组 {i+1}" for i in range(N)]

    # ---- 画布 & 布局 ----
    W = 900
    margin_r = 40
    margin_t = 80 if title else 32
    margin_b = 60

    # ROW_STEP 与 RIDGE_H 需要留出空间给左侧组名，label 越大 step 越大。
    # 先估一次 fs_label 以决定 ROW_STEP（fs_label 只依赖 W/H/N，且 H 依赖 ROW_STEP → 用近似 H）。
    from .._common import _dist_font_sizes, _estimate_label_width_px
    _H_approx = margin_t + (N - 1) * 34 + 62 + margin_b
    _label_est = _dist_font_sizes(W, _H_approx, N)["label"]

    # Adaptive left margin: labels are rendered UPPER-CASE + bold(700) +
    # letter-spacing=".08em" at x = margin_l - 14 with text-anchor="end".
    # The previous hard-coded margin_l=100 clipped model names like
    # "CLAUDE 3.5 SONNET" / "GPT-4 TURBO 128K" (validator reported 80-113px
    # left overflow). Reserve room using the same per-glyph model as
    # embed_svg_validator so we can never under-shoot.
    _upper_labels = [str(lbl).upper() for lbl in group_labels]
    _max_label_px = max(
        (_estimate_label_width_px(lbl, _label_est, 0.08, bold=True,
                                  font_family=None) for lbl in _upper_labels),
        default=0.0,
    )
    # 14 = anchor offset (see label render below); +8 safety pad clears the
    # 2px OUT_OF_BOUNDS_MARGIN_PX plus rendering slack.
    margin_l = max(100, int(math.ceil(_max_label_px + 14 + 8)))
    plot_w = W - margin_l - margin_r
    ROW_STEP = max(34.0, _label_est * 1.15 + 12)   # 组名 h + 12px 底距，避免与相邻 ridge 峰值挤到一起
    RIDGE_H = max(62.0, ROW_STEP * 1.7)             # ridge 峰值高度不小于 62
    H = margin_t + (N - 1) * ROW_STEP + RIDGE_H + margin_b

    # ---- 字号自适应（viewBox 短边 × 数据规模双重挂钩）----
    # W=900, H 随 N 动。short-side 通常 ~340-450 → base ~9-11 → title ~15-24。
    # 保证 slide 400px embed 后仍可读。
    _fs = _dist_font_sizes(W, H, N)
    fs_title    = _fs["title"]     # 顶部标题
    fs_subtitle = _fs["subtitle"]
    fs_tick     = _fs["ytick"]     # x 轴 tick label（底部）
    fs_label    = _fs["label"]     # 左侧组名

    # ridge 语义有"次序"：相邻组应色相邻近。
    # 除非 palette 显式给了 `ridge_series` 字段，否则忽略 `series`（那是 distinct 用途），
    # 直接走 gradient 模式 hue-shift。
    if _pal.get("ridge_series"):
        series_colors = list(_pal["ridge_series"])[:N]
        if len(series_colors) < N:
            # 不够则补齐
            series_colors += _derive_series_colors(
                {k: v for k, v in _pal.items() if k != "series"},
                N - len(series_colors), mode="gradient"
            )
    else:
        # 临时把 series 抹掉，让 _derive 走 hue-shift
        _pal_for_ridge = {k: v for k, v in _pal.items() if k != "series"}
        series_colors = _derive_series_colors(_pal_for_ridge, N, mode="gradient")

    def _color_alpha(rgba_str, alpha):
        r, g, b = _rgb_tuple(rgba_str)
        return f"rgba({r},{g},{b},{alpha})"

    parts = []

    # 顶部标题
    if title:
        parts.append(
            f'<text font-family="{_body_font}" x="{margin_l}" y="34" font-size="{fs_title}" font-weight="700" '
            f'fill="{_INK}" letter-spacing=".02em">{_xesc(title)}</text>'
        )
    if subtitle:
        y_sub = 52 if title else 22
        parts.append(
            f'<text font-family="{_body_font}" x="{margin_l}" y="{y_sub}" font-size="{fs_subtitle}" fill="{c_muted}" '
            f'letter-spacing=".16em" font-weight="600">{_xesc(subtitle)}</text>'
        )

    # X 轴范围
    if x_range is not None:
        x_min, x_max = float(x_range[0]), float(x_range[1])
    else:
        x_min, x_max = 0.0, 1.0

    plot_top = margin_t - 20
    plot_bot = margin_t + (N - 1) * ROW_STEP + RIDGE_H + 8

    # 刻度
    if x_labels is not None:
        n_ticks = len(x_labels)
        tick_xs = [x_min + (x_max - x_min) * k / max(1, n_ticks - 1) for k in range(n_ticks)]
        tick_texts = list(x_labels)
    else:
        span = x_max - x_min
        raw_step = span / 8
        mag = 10 ** math.floor(math.log10(max(raw_step, 1e-9)))
        for nice in (1, 2, 2.5, 5, 10):
            if raw_step / mag <= nice:
                tick_step = nice * mag
                break
        else:
            tick_step = 10 * mag
        t = math.ceil(x_min / tick_step) * tick_step
        tick_xs = []
        while t <= x_max + 1e-9:
            tick_xs.append(t)
            t += tick_step
        def _fmt_tick(v):
            if tick_step >= 1:
                if v == 0:
                    return "0"
                return f"{int(round(v)):+d}"
            else:
                dec = max(0, -math.floor(math.log10(tick_step)))
                if v == 0:
                    return "0"
                return f"{v:+.{dec}f}"
        tick_texts = [_fmt_tick(v) for v in tick_xs]

    def x_to_px(xv):
        return margin_l + (xv - x_min) / (x_max - x_min) * plot_w

    # 竖网格
    for xv in tick_xs:
        px = x_to_px(xv)
        parts.append(
            f'<line x1="{px:.1f}" y1="{plot_top}" x2="{px:.1f}" y2="{plot_bot+12}" '
            f'stroke="{_INK1}" stroke-width="1"/>'
        )

    # x=0 参考线
    if x_min <= 0 <= x_max:
        zero_px = x_to_px(0)
        parts.append(
            f'<line x1="{zero_px:.1f}" y1="{plot_top}" x2="{zero_px:.1f}" y2="{plot_bot+12}" '
            f'stroke="{_rgba_with_alpha(_INK, 0.25)}" stroke-width="1" stroke-dasharray="2 3"/>'
        )

    # 底部 x 轴
    parts.append(
        f'<line x1="{margin_l}" y1="{plot_bot+8}" x2="{W-margin_r}" y2="{plot_bot+8}" '
        f'stroke="{_rgba_with_alpha(_INK, 0.3)}" stroke-width="1"/>'
    )
    for xv, txt in zip(tick_xs, tick_texts):
        px = x_to_px(xv)
        parts.append(
            f'<text font-family="{_body_font}" x="{px:.1f}" y="{plot_bot+28}" text-anchor="middle" font-size="{fs_tick}" '
            f'fill="{c_muted}" letter-spacing=".05em">{_xesc(txt)}</text>'
        )

    # defs
    defs_body = []
    for i in range(N):
        col = series_colors[i]
        c_top = _color_alpha(col, 0.85)
        c_mid = _color_alpha(col, 0.35)
        c_bot = _color_alpha(col, 0.05)
        defs_body.append(f'<linearGradient id="ridge_fill_{i}" x1="0" y1="0" x2="0" y2="1">'
                         f'<stop offset="0%" stop-color="{c_top}"/>'
                         f'<stop offset="60%" stop-color="{c_mid}"/>'
                         f'<stop offset="100%" stop-color="{c_bot}"/>'
                         f'</linearGradient>')
    parts.append(f'<defs>{"".join(defs_body)}</defs>')

    # 山脊：下 -> 上 后画覆盖前画
    for i in range(N - 1, -1, -1):
        dist = distributions[i]
        col = series_colors[i]
        y_base = margin_t + i * ROW_STEP + RIDGE_H
        vmax = max(dist) if dist else 1
        vmin = min(dist) if dist else 0
        n_pts = len(dist)
        xs = [margin_l + k * plot_w / max(1, n_pts - 1) for k in range(n_pts)]

        if vmax <= 0 or (vmax - vmin) < 1e-9:
            baseline_offset = RIDGE_H * 0.2 if vmax > 0 else 0.0
            ys = [y_base - baseline_offset for _ in dist]
        else:
            ys = [y_base - v / vmax * RIDGE_H for v in dist]

        pts = list(zip(xs, ys))
        line_d = "M " + " L ".join(f"{px:.1f} {py:.1f}" for px, py in pts)
        fill_d = line_d + f' L {pts[-1][0]:.1f} {y_base:.1f} L {pts[0][0]:.1f} {y_base:.1f} Z'

        parts.append(f'<path d="{fill_d}" fill="url(#ridge_fill_{i})" opacity="0.95"/>')
        # 柔光顶线：改用半透明厚描边（stroke-opacity + 较宽 stroke-width）模拟原 feGaussianBlur 效果
        parts.append(f'<path d="{line_d}" fill="none" stroke="{_color_alpha(col, 0.9)}" '
                     f'stroke-width="4" stroke-opacity="0.5" stroke-linecap="round" stroke-linejoin="round"/>')
        stroke_w = 1.8 if (highlight_index is not None and i == highlight_index) else 1.2
        parts.append(f'<path d="{line_d}" fill="none" stroke="{_color_alpha(col, 0.95)}" '
                     f'stroke-width="{stroke_w}"/>')

        # 左侧组名
        parts.append(f'<text font-family="{_body_font}" x="{margin_l - 14}" y="{y_base - 4:.1f}" text-anchor="end" '
                     f'font-size="{fs_label}" font-weight="700" '
                     f'fill="{_color_alpha(col, 0.95)}" letter-spacing=".08em">{_xesc(str(group_labels[i]).upper())}</text>')

        # 峰值圆点
        if vmax > 0 and (vmax - vmin) >= 1e-9:
            peak_idx = max(range(n_pts), key=lambda k: dist[k])
            peak_x = xs[peak_idx]
            peak_y = ys[peak_idx]
            parts.append(f'<circle cx="{peak_x:.1f}" cy="{peak_y:.1f}" r="2.2" '
                         f'fill="rgba(255,255,255,0.9)" stroke="{_color_alpha(col, 0.9)}" stroke-width="0.8"/>')

    body = "".join(parts)
    _svg_result = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}">{body}</svg>'
    return _prepend_bg_if_dark(_svg_result, _pal)


