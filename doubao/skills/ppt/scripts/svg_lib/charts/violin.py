"""svg_lib/charts/violin.py

Productized violin chart with 5 variants:
  * boxplot_inner_flat  — baseline (make_violin)
  * quartile_outlined   — outlined KDE + quartile line overlay
  * points_inner_flat   — Sina-plot: dots inside violin
  * half_gradient       — one-sided violin with linear gradient fill
  * kde_only            — bare KDE, no inner markers

Data schema is identical to boxplot (interchangeable):
    data = {
        "groups": [(name, [values]), ...],
        "unit": str = "",
        "highlight_name": str | None,
    }
"""
from __future__ import annotations
import math
import random
import re

from .. import _baseline as _g  # type: ignore

from ._shared import (

    auto_font_size,
    resolve_palette,
    xesc,
)


from .._common import (_ACC, _INK, _INK1, _INK2, _INK4, _INK6, _derive_series_colors, _fmt_axis, _prepend_bg_if_dark, _resolve_font, _resolve_palette, _rgba_with_alpha, _xesc, _variant_is_classic, _dispatch_to_svg_lib)
VARIANTS = (
    "boxplot_inner_flat",
    "quartile_outlined",
    "points_inner_flat",
    "half_gradient",
    "kde_only",
)


def _validate_data(data):
    if not isinstance(data, dict):
        raise TypeError(f"violin data must be dict, got {type(data).__name__}")
    groups = data.get("groups")
    if not groups:
        raise ValueError("violin data.groups is required and non-empty")
    normed = []
    for i, g in enumerate(groups):
        if not (isinstance(g, (tuple, list)) and len(g) >= 2):
            raise ValueError(f"violin group[{i}] must be (name, [values])")
        name, values = g[0], g[1]
        if not values:
            raise ValueError(f"violin group[{i}] '{name}' has empty values")
        vs = []
        for v in values:
            try:
                fv = float(v)
            except Exception:
                continue
            if fv != fv or fv in (float("inf"), -float("inf")):
                continue
            vs.append(fv)
        if not vs:
            raise ValueError(f"violin group[{i}] '{name}' has no valid numeric values")
        normed.append((str(name), vs))
    return normed


# ---------------------------------------------------------------------------
# Layout math shared by overlay/hand-crafted variants.
# Matches make_violin default layout constants (W=1200, H=620,
# MARGIN_L=110, MARGIN_R=60, MARGIN_T=130, MARGIN_B=65).
# ---------------------------------------------------------------------------
_LAYOUT = dict(W=1200.0, H=620.0, ML=110.0, MR=60.0, MT=130.0, MB=65.0)


def _plot_geom(n_groups):
    L = _LAYOUT
    plot_l = L["ML"]
    plot_r = L["W"] - L["MR"]
    plot_top = L["MT"]
    plot_bot = L["H"] - L["MB"]
    plot_w = plot_r - plot_l
    plot_h = plot_bot - plot_top
    slot_w = plot_w / max(1, n_groups)
    half = min(60.0, slot_w * 0.38)
    return plot_l, plot_r, plot_top, plot_bot, plot_w, plot_h, slot_w, half


def _y_axis(groups):
    all_vals = [v for _, vs in groups for v in vs]
    v_min, v_max = min(all_vals), max(all_vals)
    step = max(1e-9, (v_max - v_min) / 5)
    magnitude = 10 ** max(0, int(math.log10(step)))
    tick_step = round(step / magnitude) * magnitude or magnitude
    v_min_a = math.floor(v_min / tick_step) * tick_step
    v_max_a = math.ceil(v_max / tick_step) * tick_step
    if v_max_a - v_min_a < tick_step * 0.5:
        v_min_a -= tick_step
        v_max_a += tick_step
    return v_min_a, v_max_a, tick_step


def _quantile(sxs, p):
    if not sxs:
        return 0.0
    s = sorted(sxs)
    n = len(s)
    pos = p * (n - 1)
    lo = int(pos)
    hi = min(n - 1, lo + 1)
    f = pos - lo
    return s[lo] * (1 - f) + s[hi] * f


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def draw_violin(
    data: dict,
    variant: str = "boxplot_inner_flat",
    palette: str = "archive_ink",
    width: float = 900,
    height: float = 540,
    title: str = None,
    subtitle: str = None,
    y_axis_label: str = None,
    figure_label: str = None,
    note: str = None,
    source: str = None,
) -> str:
    """Return an SVG string for a violin chart in the requested variant.

    variant ∈ VARIANTS.
    """
    if variant not in VARIANTS:
        raise ValueError(
            f"unknown violin variant {variant!r}; expected one of {VARIANTS}"
        )
    groups = _validate_data(data)
    unit = data.get("unit", "") or ""
    highlight = data.get("highlight_name")

    n_groups = len(groups)
    # 用 viewBox-aware 字号（跟其它分布图统一）
    from .._common import _dist_font_sizes
    _fs_dv = _dist_font_sizes(_LAYOUT["W"], _LAYOUT["H"], n_groups)
    fs_group = _fs_dv["group"]

    # ------------------------------------------------------------------
    # baseline path: use make_violin for four of the five variants (all
    # except half_gradient which is hand-crafted below).
    # ------------------------------------------------------------------
    base_kw = dict(
        y_unit=unit,
        title=title,
        subtitle=subtitle,
        figure_label=figure_label,
        y_axis_label=y_axis_label,
        note=note,
        source=source,
        width=1200.0,       # fixed so overlay geometry matches
        height=620.0,
        palette=palette,
        highlight_group=highlight,
    )

    if variant == "boxplot_inner_flat":
        return _g.make_violin(
            groups=groups,
            show_boxplot=True, show_mean=True, show_outliers=True,
            **base_kw,
        )

    if variant == "kde_only":
        return _g.make_violin(
            groups=groups,
            show_boxplot=False, show_mean=False, show_outliers=False,
            **base_kw,
        )

    if variant == "quartile_outlined":
        svg = _g.make_violin(
            groups=groups,
            show_boxplot=False, show_mean=True, show_outliers=True,
            **base_kw,
        )
        return _overlay_quartile_lines(svg, groups)

    if variant == "points_inner_flat":
        svg = _g.make_violin(
            groups=groups,
            show_boxplot=False, show_mean=True, show_outliers=False,
            **base_kw,
        )
        return _overlay_points(svg, groups, palette)

    if variant == "half_gradient":
        return _draw_half_gradient(
            groups=groups,
            palette=palette,
            unit=unit,
            title=title,
            subtitle=subtitle,
            y_axis_label=y_axis_label,
            figure_label=figure_label,
            note=note,
            source=source,
            fs_group=fs_group,
        )

    raise ValueError(f"unhandled variant {variant!r}")


# ---------------------------------------------------------------------------
# Overlays
# ---------------------------------------------------------------------------
def _overlay_quartile_lines(svg: str, groups) -> str:
    """Add horizontal Q1/median/Q3 tick lines to a bare KDE violin."""
    n = len(groups)
    plot_l, plot_r, plot_top, plot_bot, plot_w, plot_h, slot_w, half = _plot_geom(n)
    v_min_a, v_max_a, _ = _y_axis(groups)
    span = v_max_a - v_min_a

    # Outline the KDE strokes: replace the low-alpha fill baseline uses
    # (rgba(...,0.2)) with none + slightly thicker stroke.
    svg = re.sub(
        r'(<path d="M [^"]+" )fill="rgba\((\d+),(\d+),(\d+),0\.2\)" (stroke="[^"]+" stroke-width=")1\.1"',
        lambda m: f'{m.group(1)}fill="none" {m.group(5)}1.6"',
        svg,
    )

    def yof(v):
        return plot_bot - (v - v_min_a) / span * plot_h

    extra = []
    for i, (_, vs) in enumerate(groups):
        cx = plot_l + (i + 0.5) * slot_w
        q1, q2, q3 = _quantile(vs, 0.25), _quantile(vs, 0.5), _quantile(vs, 0.75)
        for qv, scale in ((q1, 0.55), (q2, 0.85), (q3, 0.55)):
            yp = yof(qv)
            sw = "1.6" if qv == q2 else "1.0"
            extra.append(
                f'<line x1="{cx - half * scale:.1f}" y1="{yp:.1f}" '
                f'x2="{cx + half * scale:.1f}" y2="{yp:.1f}" '
                f'stroke="rgba(45,50,42,0.75)" stroke-width="{sw}"/>'
            )
    return svg.replace("</svg>", "".join(extra) + "</svg>")


def _overlay_points(svg: str, groups, palette) -> str:
    """Sina-plot: scatter dots inside the KDE outline."""
    pal = resolve_palette(palette)
    dot_col = pal.get("accent", "rgba(0,60,120,0.7)")

    n = len(groups)
    plot_l, plot_r, plot_top, plot_bot, plot_w, plot_h, slot_w, half = _plot_geom(n)
    v_min_a, v_max_a, _ = _y_axis(groups)
    span = v_max_a - v_min_a

    def yof(v):
        return plot_bot - (v - v_min_a) / span * plot_h

    rng = random.Random(3)
    extra = []
    for i, (_, vs) in enumerate(groups):
        cx = plot_l + (i + 0.5) * slot_w
        for v in vs:
            jx = cx + (rng.random() - 0.5) * half * 0.6
            extra.append(
                f'<circle cx="{jx:.1f}" cy="{yof(v):.1f}" r="1.8" fill="{dot_col}"/>'
            )
    return svg.replace("</svg>", "".join(extra) + "</svg>")


# ---------------------------------------------------------------------------
# Hand-crafted half-violin gradient variant.
# ---------------------------------------------------------------------------
def _gauss_pdf(u):
    return math.exp(-0.5 * u * u) / math.sqrt(2 * math.pi)


def _rgb_of(rgba):
    m = re.match(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", rgba or "")
    if not m:
        return 128, 128, 128
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def _draw_half_gradient(
    groups, palette, unit,
    title, subtitle, y_axis_label, figure_label, note, source, fs_group,
) -> str:
    pal = resolve_palette(palette)
    ink = pal["ink"]
    bg = pal["bg"]
    muted = pal.get("muted", pal["ink6"])
    acc = pal.get("accent", ink)
    series = list(pal.get("series") or [acc])

    N = len(groups)
    L = _LAYOUT
    W, H = L["W"], L["H"]
    ML, MR = L["ML"], L["MR"]
    MT, MB = L["MT"], 90.0
    plot_l = ML
    plot_r = W - MR
    plot_top = MT
    plot_bot = H - MB
    plot_w = plot_r - plot_l
    plot_h = plot_bot - plot_top
    slot_w = plot_w / N
    half = min(80.0, slot_w * 0.55)

    v_min_a, v_max_a, tick_step = _y_axis(groups)
    span = v_max_a - v_min_a

    # viewBox-aware 字号
    from .._common import _dist_font_sizes
    _fs_hg = _dist_font_sizes(W, H, N)
    fs_hg_title    = _fs_hg["title"]
    fs_hg_subtitle = _fs_hg["subtitle"]
    fs_hg_figure   = _fs_hg["figure"]
    fs_hg_tick     = _fs_hg["ytick"]
    fs_hg_yaxis    = _fs_hg["yaxis"]
    fs_hg_group_n  = _fs_hg["group_n"]
    fs_hg_foot     = _fs_hg["foot"]

    def yof(v):
        return plot_bot - (v - v_min_a) / span * plot_h

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {int(W)} {int(H)}">']
    parts.append(f'<rect width="{W}" height="{H}" fill="{bg}"/>')

    # header
    if title:
        parts.append(
            f'<text x="{ML}" y="45" font-family="Georgia, serif" font-size="{fs_hg_title}" '
            f'font-weight="600" fill="{ink}">{xesc(title)}</text>'
        )
    if subtitle:
        parts.append(
            f'<text x="{ML}" y="66" font-family="Inter, sans-serif" font-size="{fs_hg_subtitle}" '
            f'fill="{muted}" letter-spacing=".2em">{xesc(subtitle)}</text>'
        )
    parts.append(
        f'<line x1="{ML}" y1="80" x2="{W - MR}" y2="80" stroke="{ink}" stroke-width="0.8"/>'
    )
    if figure_label:
        parts.append(
            f'<text x="{ML}" y="102" font-family="Inter, sans-serif" font-size="{fs_hg_figure}" '
            f'fill="{muted}" font-weight="600" letter-spacing=".15em">{xesc(figure_label)}</text>'
        )

    # y-axis label
    if y_axis_label:
        ytx = plot_l - 70
        yty = plot_top + plot_h / 2
        parts.append(
            f'<text x="{ytx}" y="{yty}" transform="rotate(-90 {ytx} {yty})" '
            f'text-anchor="middle" font-family="Inter, sans-serif" font-size="{fs_hg_yaxis}" '
            f'fill="{ink}" font-weight="500">{xesc(y_axis_label)}</text>'
        )

    # y-ticks
    t = v_min_a
    while t <= v_max_a + 1e-6:
        y = yof(t)
        parts.append(
            f'<line x1="{plot_l}" y1="{y:.1f}" x2="{plot_r}" y2="{y:.1f}" '
            f'stroke="rgba(30,25,28,0.08)" stroke-width="1" stroke-dasharray="2 4"/>'
        )
        label = f"{t:g}{unit}" if unit else f"{t:g}"
        parts.append(
            f'<text x="{plot_l - 10:.1f}" y="{y + 3:.1f}" text-anchor="end" '
            f'font-family="Inter, sans-serif" font-size="{fs_hg_tick}" fill="{ink}">{xesc(label)}</text>'
        )
        t += tick_step

    # gradient defs (one per group)
    defs = []
    for i in range(N):
        col = series[i % len(series)]
        r, g_, b = _rgb_of(col)
        defs.append(
            f'<linearGradient id="halfvio_grad_{i}" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0%" stop-color="rgba({r},{g_},{b},0.85)"/>'
            f'<stop offset="100%" stop-color="rgba({r},{g_},{b},0.15)"/>'
            f'</linearGradient>'
        )
    parts.append(f'<defs>{"".join(defs)}</defs>')

    # per-group half violin + mini boxplot on the left
    for i, (name, vs) in enumerate(groups):
        cx = plot_l + (i + 0.5) * slot_w
        col = series[i % len(series)]

        # KDE
        n = len(vs)
        mean_v = sum(vs) / n
        var = sum((v - mean_v) ** 2 for v in vs) / max(1, n - 1)
        sd = math.sqrt(var) if var > 0 else max(1e-6, 0.1 * (max(vs) - min(vs) or 1.0))
        bw = 0.9 * sd * n ** (-1 / 5) if sd > 0 else 0.1
        y_lo = max(v_min_a, min(vs) - bw * 2)
        y_hi = min(v_max_a, max(vs) + bw * 2)
        n_samples = 60
        ys = [y_lo + k / (n_samples - 1) * (y_hi - y_lo) for k in range(n_samples)]
        dens = [sum(_gauss_pdf((y - v) / bw) for v in vs) / (n * bw) for y in ys]
        dmax = max(dens) or 1.0
        d = f"M {cx:.2f} {yof(ys[0]):.2f} "
        for k, dv in enumerate(dens):
            xr = cx + (dv / dmax) * half
            d += f"L {xr:.2f} {yof(ys[k]):.2f} "
        d += f"L {cx:.2f} {yof(ys[-1]):.2f} Z"
        parts.append(
            f'<path d="{d}" fill="url(#halfvio_grad_{i})" stroke="{col}" stroke-width="1.4"/>'
        )

        # mini boxplot on the left of the axis
        vs_sorted = sorted(vs)
        q1, q2, q3 = _quantile(vs_sorted, 0.25), _quantile(vs_sorted, 0.5), _quantile(vs_sorted, 0.75)
        iqr = q3 - q1
        lo_w = max(v_min_a, q1 - 1.5 * iqr, vs_sorted[0])
        hi_w = min(v_max_a, q3 + 1.5 * iqr, vs_sorted[-1])
        bx = cx - 20
        parts.append(
            f'<line x1="{bx:.1f}" y1="{yof(lo_w):.1f}" x2="{bx:.1f}" y2="{yof(hi_w):.1f}" '
            f'stroke="{ink}" stroke-width="0.8"/>'
        )
        parts.append(
            f'<rect x="{bx - 6:.1f}" y="{yof(q3):.1f}" width="12" '
            f'height="{max(1, yof(q1) - yof(q3)):.1f}" fill="{bg}" stroke="{ink}" stroke-width="1"/>'
        )
        parts.append(
            f'<line x1="{bx - 6:.1f}" y1="{yof(q2):.1f}" x2="{bx + 6:.1f}" y2="{yof(q2):.1f}" '
            f'stroke="{acc}" stroke-width="2"/>'
        )

        # group label + n
        parts.append(
            f'<text x="{cx:.1f}" y="{plot_bot + 22:.1f}" text-anchor="middle" '
            f'font-family="Inter, sans-serif" font-size="{fs_group}" '
            f'font-weight="600" fill="{ink}">{xesc(name)}</text>'
        )
        parts.append(
            f'<text x="{cx:.1f}" y="{plot_bot + 38:.1f}" text-anchor="middle" '
            f'font-family="Inter, sans-serif" font-size="{fs_hg_group_n}" fill="{muted}">n = {n}</text>'
        )

    # baseline axis
    parts.append(
        f'<line x1="{plot_l}" y1="{plot_bot}" x2="{plot_r}" y2="{plot_bot}" '
        f'stroke="{ink}" stroke-width="1"/>'
    )

    if note:
        parts.append(
            f'<text x="{ML}" y="{H - 40:.1f}" font-family="Inter, sans-serif" '
            f'font-size="{fs_hg_foot}" fill="{muted}">{xesc(note)}</text>'
        )
    if source:
        parts.append(
            f'<text x="{ML}" y="{H - 22:.1f}" font-family="Inter, sans-serif" '
            f'font-size="{fs_hg_foot}" fill="{muted}" letter-spacing=".08em">{xesc(source)}</text>'
        )

    parts.append("</svg>")
    return "".join(parts)


def make_violin(groups: Sequence[Sequence],
                y_unit: str = "",
                highlight_group: str = None,
                bandwidth: float = None,
                y_min: float = None,
                y_max: float = None,
                title: str = None,
                subtitle: str = None,
                figure_label: str = None,
                figure_note: str = None,
                y_axis_label: str = None,
                note: str = None,
                source: str = None,
                width: float = 1200.0,
                height: float = None,
                show_boxplot: bool = True,
                show_mean: bool = True,
                show_outliers: bool = True,
                show_legend: bool = True,
                per_group_n: "list[int]" = None,
                font_family: str = None,
                palette=None,
                variant: str = None) -> str:
    """
    小提琴分布图（Academic / Publication Style）：
      - 米白纸底 + 稀疏虚线网格
      - KDE 密度轮廓 + 内嵌 mini boxplot（Q1-Q3 + 中位数 + whiskers）
      - 均值空心圆 + outlier 空心圆
      - 顶部 Title / Subtitle / FIGURE caption
      - 底部 legend（KDE / Q1-Q3 / mean / whiskers / outlier）+ Notes + Source
      - X 轴组名 + n / 中位数副标签

    参数：
      groups: [(name, [values...]), ...] N 组；每组建议 20-500 数值
      y_unit: Y 轴刻度后缀。若为 "%"，Y 轴 clamp 到 [0, 100]
      highlight_group: 组名，用 accent 高亮
      bandwidth: KDE 带宽；None 自动 Silverman
      y_min/y_max: Y 轴范围
      title / subtitle / figure_label / figure_note: 顶部标题
      y_axis_label: Y 轴标题（垂直排布）
      note / source: 底部脚注
      per_group_n: [(n1,n2,...)]，若不传按数据长度自动
      palette: 配色
    """
    if not _variant_is_classic('violin', variant):
        _data = {"groups": list(groups), "unit": y_unit or "", "highlight_name": highlight_group}
        return _dispatch_to_svg_lib(
            'violin', variant, _data,
            title=title, subtitle=subtitle, figure_label=figure_label,
            palette=palette, font_family=font_family,
        )

    _pal = _resolve_palette(palette)
    _body_font, _head_font = _resolve_font(font_family)
    _INK, _INK6, _INK4, _INK2, _INK1, _ACC = (
        _pal["ink"], _pal["ink6"], _pal["ink4"], _pal["ink2"], _pal["ink1"], _pal["accent"]
    )
    c_muted = _pal.get("muted", _rgba_with_alpha(_INK, 0.6))
    paper = _pal.get("bg", "rgba(250,248,242,1)")

    if not groups:
        raise ValueError("violin: at least one group required")
    for i, g in enumerate(groups):
        if len(g) < 2 or not g[1]:
            raise ValueError(f"violin: group[{i}] must be (name, [values]) with at least 1 value")

    N = len(groups)
    all_vals = [v for _, vs in groups for v in vs]
    v_min, v_max = min(all_vals), max(all_vals)
    step = max(1e-9, (v_max - v_min) / 5)
    magnitude = 10 ** max(0, int(math.log10(step)))
    tick_step = round(step / magnitude) * magnitude or magnitude
    v_min_floor = math.floor(v_min / tick_step) * tick_step
    v_max_ceil = math.ceil(v_max / tick_step) * tick_step
    v_min_a = v_min_floor
    v_max_a = v_max_ceil
    if v_max_a - v_min_a < tick_step * 0.5:
        v_min_a = v_min_floor - tick_step
        v_max_a = v_max_ceil + tick_step
    if y_unit.strip() == "%":
        # 仅当数据真的落在问卷类 [0,100] 范围时才收敛；金融日收益率、变化率等
        # 百分比数据可以为负或超过 100，clamp 会把有效数据点画到 viewBox 外。
        if v_min >= 0 and v_max <= 100:
            v_min_a = max(0, v_min_a)
            v_max_a = min(100, v_max_a)
    if y_min is not None: v_min_a = y_min
    if y_max is not None: v_max_a = y_max
    span = v_max_a - v_min_a

    # 派生每组色（distinct 家族）
    series_cols = _derive_series_colors(_pal, N, mode="distinct")

    # ---- 画布布局 ----
    # height 缺省 None：按内容自适应（宽 1200 时约 620px 高，比原 720 省 100px 底部留白）
    if height is None:
        height = 620.0
    W, H = float(width), float(height)

    # ---- 字号自适应（先算：MARGIN_B 需要 fs_group 决定底部 3 行 label 高度）----
    # SVG 字号相对 viewBox；slide 400px embed 缩放后视觉字号缩到 1/3，
    # 所以基准要拉到短边 2.4%（W=1200,H=620 → base ≈ 14.9pt），保证可读。
    from .._common import _dist_font_sizes
    _fs = _dist_font_sizes(W, H, N)
    fs_title    = _fs["title"]
    fs_subtitle = _fs["subtitle"]
    fs_figure   = _fs["figure"]
    fs_ytick    = _fs["ytick"]
    fs_yaxis    = _fs["yaxis"]
    fs_group    = _fs["group"]
    fs_group_n  = _fs["group_n"]
    fs_side_hdr = _fs["group_n"]
    fs_side_lg  = _fs["legend"]
    fs_ins_ttl  = _fs["group_n"]
    fs_foot     = _fs["foot"]

    MARGIN_L = 110.0
    MARGIN_R = 60.0
    MARGIN_T = 130.0 if (title or subtitle) else 60.0
    # 底部 3 行 X 标签（name + n + median）距 plot_bot 的总高度：
    #   row0 offset ≈ fs_group*1.15，row1 gap fs_group*1.15，row2 gap fs_group_n*1.25，末行 bbox 高 fs_group_n
    _labels_h = max(50.0, fs_group * 1.15 + fs_group * 1.15 + fs_group_n * 1.25 + fs_group_n)
    # note/source 区（若存在）：divider gap + divider(0.5px) + note baseline gap + note fs + source gap + source fs
    _footer_gap = max(20.0, fs_group_n)  # labels 末行到 note 分割线之间的安全间距
    _note_block_h = 0.0
    if note or source:
        _note_block_h = _footer_gap + 14.0  # 到分割线
        _note_block_h += (fs_foot + 6.0) if note else 0.0  # note baseline + descender
        _note_block_h += (fs_foot + 6.0) if source else 0.0
    MARGIN_B = max(100.0, _labels_h + _note_block_h + 8.0) if (note or source) else max(65.0, _labels_h + 8.0)

    plot_l = MARGIN_L
    plot_r = W - MARGIN_R
    plot_top = MARGIN_T
    plot_bot = H - MARGIN_B
    plot_w = plot_r - plot_l
    plot_h = plot_bot - plot_top

    # 底部 note/source 位置：随 labels 末行动态放，而不是固定从 H 底部倒推。
    # 修复 embed_svg_bbox_overlap: "Notes." vs "Mdn X.XXs" 横向重叠。
    _labels_end_y = plot_bot + _labels_h  # 最后一行 Mdn bbox 底部
    _foot_divider_y = _labels_end_y + _footer_gap
    _foot_note_y = _foot_divider_y + max(14.0, fs_foot)
    _foot_source_y = _foot_note_y + (fs_foot + 6.0 if note else 0.0)

    slot_w = plot_w / N
    half_max_w = min(60.0, slot_w * 0.38)

    def yof(v):
        return plot_bot - (v - v_min_a) / span * plot_h


    parts = []
    # 页面背景
    parts.append(f'<rect x="0" y="0" width="{W:.1f}" height="{H:.1f}" fill="{paper}"/>')

    # ---- 标题 ----
    # 顶部标题 y 位置跟字号联动
    _y_title    = 20 + fs_title
    _y_subtitle = _y_title + fs_title * 0.55 + fs_subtitle
    _y_line     = _y_subtitle + 12
    _y_figure   = _y_line + 14 + fs_figure * 0.5
    if title:
        parts.append(f'<text x="{MARGIN_L:.1f}" y="{_y_title:.1f}" font-family="{_head_font}" '
                     f'font-size="{fs_title}" font-weight="600" fill="{_INK}" letter-spacing="0.1">'
                     f'{_xesc(title)}</text>')
    if subtitle:
        parts.append(f'<text x="{MARGIN_L:.1f}" y="{_y_subtitle:.1f}" font-family="{_body_font}" '
                     f'font-size="{fs_subtitle}" fill="{c_muted}" letter-spacing="0.2">'
                     f'{_xesc(subtitle)}</text>')
    if title or subtitle:
        parts.append(f'<line x1="{MARGIN_L:.1f}" y1="{_y_line:.1f}" x2="{W-MARGIN_R:.1f}" y2="{_y_line:.1f}" '
                     f'stroke="{_INK}" stroke-width="0.8"/>')
    if figure_label:
        parts.append(f'<text x="{MARGIN_L:.1f}" y="{_y_figure:.1f}" font-family="{_body_font}" '
                     f'font-size="{fs_figure}" fill="{c_muted}" font-weight="600" letter-spacing="1.5">'
                     f'{_xesc(figure_label)}</text>')
    if figure_note:
        offset = 70 if figure_label else 0
        parts.append(f'<text x="{MARGIN_L + offset:.1f}" y="{_y_figure:.1f}" font-family="{_body_font}" '
                     f'font-size="{fs_figure}" fill="{c_muted}" letter-spacing="0.4">'
                     f'{_xesc(figure_note)}</text>')

    # ---- Y 轴网格 & 刻度 ----
    tick = v_min_a
    while tick <= v_max_a + 1e-6:
        y = yof(tick)
        is_major = (round((tick - v_min_a) / tick_step) % 2 == 0)
        stroke = _rgba_with_alpha(_INK, 0.14 if is_major else 0.06)
        parts.append(f'<line x1="{plot_l:.1f}" y1="{y:.1f}" x2="{plot_r:.1f}" y2="{y:.1f}" '
                     f'stroke="{stroke}" stroke-width="1"/>')
        parts.append(f'<line x1="{plot_l - 4:.1f}" y1="{y:.1f}" x2="{plot_l:.1f}" y2="{y:.1f}" '
                     f'stroke="{c_muted}" stroke-width="0.8"/>')
        parts.append(f'<text x="{plot_l - 10:.1f}" y="{y + 3:.1f}" text-anchor="end" '
                     f'font-family="{_body_font}" font-size="{fs_ytick}" fill="{_INK}">'
                     f'{_fmt_axis(tick, span)}{y_unit}</text>')
        tick += tick_step

    # Y 轴标题（旋转）
    if y_axis_label:
        parts.append(f'<text x="{plot_l - 70:.1f}" y="{plot_top + plot_h / 2:.1f}" '
                     f'transform="rotate(-90 {plot_l - 70:.1f} {plot_top + plot_h / 2:.1f})" '
                     f'text-anchor="middle" font-family="{_body_font}" font-size="{fs_yaxis}" '
                     f'fill="{_INK}" font-weight="500">{_xesc(y_axis_label)}</text>')

    # ---- Gaussian KDE 工具 ----
    def gauss(u):
        return math.exp(-0.5 * u * u) / math.sqrt(2 * math.pi)

    def kde_density(vals, y_samples, bw):
        n = len(vals)
        return [sum(gauss((y - v) / bw) for v in vals) / (n * bw) for y in y_samples]

    def std(vs):
        m = sum(vs) / len(vs)
        return math.sqrt(sum((v - m) ** 2 for v in vs) / max(1, len(vs) - 1))

    def quantile(sorted_xs, q):
        n = len(sorted_xs)
        if n == 0: return 0
        pos = q * (n - 1)
        lo, hi = int(pos), min(int(pos) + 1, n - 1)
        frac = pos - lo
        return sorted_xs[lo] * (1 - frac) + sorted_xs[hi] * frac

    n_samples = 80

    # 先算全组的 max density，用于所有 violin 归一化到同一尺度
    group_stats = []
    global_dmax = 0.0
    for i, (name, vs) in enumerate(groups):
        vs_sorted = sorted(vs)
        n = len(vs_sorted)
        q1 = quantile(vs_sorted, 0.25); q2 = quantile(vs_sorted, 0.5); q3 = quantile(vs_sorted, 0.75)
        iqr = q3 - q1
        lo_w = max(v_min_a, q1 - 1.5 * iqr, min(vs_sorted))
        hi_w = min(v_max_a, q3 + 1.5 * iqr, max(vs_sorted))
        mean_v = sum(vs) / len(vs)
        outliers = [v for v in vs_sorted if v < lo_w or v > hi_w]

        if bandwidth is not None:
            bw = bandwidth
        else:
            sd = std(vs) if n >= 2 else max(1e-6, (v_max - v_min) / 4)
            iqr_scale = max(1e-6, iqr / 1.349) if iqr > 0 else sd
            bw = 0.9 * min(sd if sd > 0 else iqr_scale, iqr_scale) * (n ** (-1.0 / 5)) if n >= 2 else max(1e-6, span * 0.05)
            bw = max(bw, span * 0.015)

        y_lo = max(v_min_a, min(vs) - bw * 2)
        y_hi = min(v_max_a, max(vs) + bw * 2)
        y_samples = [y_lo + k / (n_samples - 1) * (y_hi - y_lo) for k in range(n_samples)]
        density = kde_density(vs, y_samples, bw)
        d_max = max(density) if density else 1e-9
        global_dmax = max(global_dmax, d_max)
        group_stats.append(dict(
            name=name, vs=vs_sorted, n=n, q1=q1, q2=q2, q3=q3,
            lo=lo_w, hi=hi_w, mean=mean_v, outliers=outliers,
            y_samples=y_samples, density=density, d_max=d_max, bw=bw))

    # ---- 每个 violin ----
    for i, s in enumerate(group_stats):
        cx = plot_l + (i + 0.5) * slot_w
        base_col = series_cols[i]
        is_hi = (highlight_group is not None and s["name"] == highlight_group)
        stroke_c = _ACC if is_hi else base_col
        fill_c = _rgba_with_alpha(_ACC, 0.25) if is_hi else _rgba_with_alpha(base_col, 0.2)

        widths = [(half_max_w * d / global_dmax) if (d / global_dmax) > 0.02 else 0.0
                  for d in s["density"]]
        pts_right = [(cx + widths[k], yof(s["y_samples"][k])) for k in range(n_samples)]
        pts_left = [(cx - widths[k], yof(s["y_samples"][k])) for k in range(n_samples - 1, -1, -1)]

        d = f"M {pts_right[0][0]:.2f} {pts_right[0][1]:.2f} "
        for (x, y) in pts_right[1:]:
            d += f"L {x:.2f} {y:.2f} "
        for (x, y) in pts_left:
            d += f"L {x:.2f} {y:.2f} "
        d += "Z"
        parts.append(f'<path d="{d}" fill="{fill_c}" stroke="{stroke_c}" stroke-width="1.1"/>')

        # 内嵌 boxplot
        if show_boxplot:
            y_hi = yof(s["hi"]); y_lo = yof(s["lo"])
            y_q3 = yof(s["q3"]); y_q1 = yof(s["q1"]); y_q2 = yof(s["q2"])
            parts.append(f'<line x1="{cx:.1f}" y1="{y_hi:.1f}" x2="{cx:.1f}" y2="{y_lo:.1f}" '
                         f'stroke="{_INK}" stroke-width="0.8"/>')
            cap_w = half_max_w * 0.28
            for wy in (y_hi, y_lo):
                parts.append(f'<line x1="{cx - cap_w / 2:.1f}" y1="{wy:.1f}" '
                             f'x2="{cx + cap_w / 2:.1f}" y2="{wy:.1f}" '
                             f'stroke="{_INK}" stroke-width="0.8"/>')
            bw2 = half_max_w * 0.22
            parts.append(f'<rect x="{cx - bw2:.1f}" y="{y_q3:.1f}" width="{2 * bw2:.1f}" '
                         f'height="{max(0.5, y_q1 - y_q3):.1f}" fill="{paper}" '
                         f'stroke="{stroke_c}" stroke-width="1"/>')
            parts.append(f'<line x1="{cx - bw2:.1f}" y1="{y_q2:.1f}" x2="{cx + bw2:.1f}" y2="{y_q2:.1f}" '
                         f'stroke="{stroke_c}" stroke-width="2" stroke-linecap="square"/>')

        # 均值
        if show_mean:
            y_mean = yof(s["mean"])
            parts.append(f'<circle cx="{cx:.1f}" cy="{y_mean:.1f}" r="3.2" fill="{paper}" '
                         f'stroke="{_INK}" stroke-width="1.2"/>')
            parts.append(f'<circle cx="{cx:.1f}" cy="{y_mean:.1f}" r="0.9" fill="{_INK}"/>')

        # outliers
        if show_outliers:
            import random as _rand
            _rand.seed(42 + i)
            for v in s["outliers"]:
                if v < v_min_a or v > v_max_a:
                    continue
                py = yof(v)
                jx = cx + (_rand.random() - 0.5) * 5
                parts.append(f'<circle cx="{jx:.1f}" cy="{py:.1f}" r="2.4" fill="none" '
                             f'stroke="{_INK}" stroke-width="1"/>')

        # X 轴组名 + n + 中位数 —— 行距按最大字号 * 1.15 预留
        _gap1 = max(22.0, fs_group * 1.15)
        _gap2 = max(17.0, fs_group_n * 1.25)
        label_y = plot_bot + max(22.0, fs_group * 1.15)
        parts.append(f'<text x="{cx:.1f}" y="{label_y:.1f}" text-anchor="middle" '
                     f'font-family="{_body_font}" font-size="{fs_group}" font-weight="600" '
                     f'fill="{_INK}">{_xesc(s["name"])}</text>')
        n_disp = per_group_n[i] if per_group_n and i < len(per_group_n) else s["n"]
        parts.append(f'<text x="{cx:.1f}" y="{label_y + _gap1:.1f}" text-anchor="middle" '
                     f'font-family="{_body_font}" font-size="{fs_group_n}" fill="{c_muted}">'
                     f'n = {n_disp}</text>')
        med_fmt = _fmt_axis(s["q2"], span)
        parts.append(f'<text x="{cx:.1f}" y="{label_y + _gap1 + _gap2:.1f}" text-anchor="middle" '
                     f'font-family="{_body_font}" font-size="{fs_group_n}" fill="{c_muted}" '
                     f'font-style="italic">Mdn {med_fmt}{y_unit}</text>')

    # X 轴基线
    parts.append(f'<line x1="{plot_l:.1f}" y1="{plot_bot:.1f}" x2="{plot_r:.1f}" y2="{plot_bot:.1f}" '
                 f'stroke="{_INK}" stroke-width="1"/>')

    # ---- 图例 ----
    if show_legend:
        lg_y = 112
        lg_x = W - MARGIN_R
        # 右起：Outlier / whiskers / mean / Q1-Q3 median / KDE density
        items = []
        if show_outliers: items.append(("Outlier", "outlier"))
        items.append(("±1.5·IQR whiskers", "whisker"))
        if show_mean: items.append(("Mean", "mean"))
        if show_boxplot: items.append(("Q1–Q3 · median", "boxmed"))
        items.append(("KDE density", "kde"))
        x_cur = lg_x
        for lab, sym in items:
            # 估算文字宽度：按 validator 侧的每字符宽度上限估算（宽字符 ~0.9em、窄字符 ~0.55em），
            # 再留出足够 padding，避免 label bbox 与相邻 swatch rect 相交。
            wide_chars = set("QOWMmw–·—")
            est_char = sum(0.90 * fs_side_lg if ch in wide_chars else 0.55 * fs_side_lg for ch in lab)
            txt_w = est_char + fs_side_lg * 0.8
            parts.append(f'<text x="{x_cur:.1f}" y="{lg_y + 3:.1f}" text-anchor="end" '
                         f'font-family="{_body_font}" font-size="{fs_side_lg}" fill="{c_muted}">'
                         f'{_xesc(lab)}</text>')
            # 符号与文字之间保留 gap（随字号 scale）
            sym_x = x_cur - txt_w - max(14.0, fs_side_lg * 1.0)
            if sym == "outlier":
                parts.append(f'<circle cx="{sym_x:.1f}" cy="{lg_y:.1f}" r="2.4" fill="none" '
                             f'stroke="{_INK}" stroke-width="1"/>')
                sym_w = 10
            elif sym == "whisker":
                parts.append(f'<line x1="{sym_x:.1f}" y1="{lg_y - 6:.1f}" x2="{sym_x:.1f}" '
                             f'y2="{lg_y + 6:.1f}" stroke="{_INK}" stroke-width="0.9"/>')
                parts.append(f'<line x1="{sym_x - 4:.1f}" y1="{lg_y - 6:.1f}" x2="{sym_x + 4:.1f}" '
                             f'y2="{lg_y - 6:.1f}" stroke="{_INK}" stroke-width="0.9"/>')
                parts.append(f'<line x1="{sym_x - 4:.1f}" y1="{lg_y + 6:.1f}" x2="{sym_x + 4:.1f}" '
                             f'y2="{lg_y + 6:.1f}" stroke="{_INK}" stroke-width="0.9"/>')
                sym_w = 14
            elif sym == "mean":
                parts.append(f'<circle cx="{sym_x:.1f}" cy="{lg_y:.1f}" r="3.2" fill="{paper}" '
                             f'stroke="{_INK}" stroke-width="1.1"/>')
                parts.append(f'<circle cx="{sym_x:.1f}" cy="{lg_y:.1f}" r="0.8" fill="{_INK}"/>')
                sym_w = 10
            elif sym == "boxmed":
                sc = series_cols[0]
                parts.append(f'<rect x="{sym_x - 4:.1f}" y="{lg_y - 6:.1f}" width="8" height="12" '
                             f'fill="{paper}" stroke="{sc}" stroke-width="0.9"/>')
                parts.append(f'<line x1="{sym_x - 4:.1f}" y1="{lg_y:.1f}" x2="{sym_x + 4:.1f}" '
                             f'y2="{lg_y:.1f}" stroke="{sc}" stroke-width="1.6"/>')
                sym_w = 12
            else:  # kde
                sc = series_cols[0]
                # 迷你 violin
                pts_l, pts_r = [], []
                for k in range(15):
                    t = k / 14.0
                    yy = lg_y - 8 + t * 16
                    d_ = math.exp(-((t - 0.4) ** 2) / (2 * 0.16 ** 2))
                    w = d_ / 1.0 * 6
                    pts_l.append((sym_x - w, yy))
                    pts_r.append((sym_x + w, yy))
                d_str = f'M {pts_l[0][0]:.1f} {pts_l[0][1]:.1f} '
                for (x, y) in pts_l[1:]:
                    d_str += f'L {x:.1f} {y:.1f} '
                for (x, y) in reversed(pts_r):
                    d_str += f'L {x:.1f} {y:.1f} '
                d_str += 'Z'
                parts.append(f'<path d="{d_str}" fill="{_rgba_with_alpha(sc, 0.2)}" '
                             f'stroke="{sc}" stroke-width="0.9"/>')
                sym_w = 16
            x_cur = sym_x - sym_w - max(16.0, fs_side_lg * 1.1)

    # ---- 脚注 ----
    if note or source:
        # 分割线与 note baseline 位置随 X 标签末行动态计算（不再固定从 H 倒推），
        # 避免 secondary label（如 "Mdn 2.17s"）与 "Notes. …" 横向 bbox 相交。
        foot_y = _foot_note_y
        parts.append(f'<line x1="{MARGIN_L:.1f}" y1="{_foot_divider_y:.1f}" x2="{W - MARGIN_R:.1f}" '
                     f'y2="{_foot_divider_y:.1f}" stroke="{_INK4}" stroke-width="0.5"/>')
        if note:
            parts.append(f'<text x="{MARGIN_L:.1f}" y="{foot_y:.1f}" font-family="{_body_font}" '
                         f'font-size="{fs_foot}" fill="{c_muted}">'
                         f'<tspan font-weight="600">Notes.</tspan> {_xesc(note)}</text>')
        if source:
            y_off = _foot_source_y if note else foot_y
            parts.append(f'<text x="{MARGIN_L:.1f}" y="{y_off:.1f}" font-family="{_body_font}" '
                         f'font-size="{fs_foot}" fill="{c_muted}">'
                         f'<tspan font-weight="600">Source.</tspan> {_xesc(source)}</text>')

    body = "".join(parts)
    _svg_result = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {int(W)} {int(H)}">{body}</svg>'
    return _prepend_bg_if_dark(_svg_result, _pal)


# ==============================================================
# 18) Nested Donut 双层甜甜圈（sunburst 2-level）
# ==============================================================
