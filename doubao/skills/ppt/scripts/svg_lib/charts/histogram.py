"""Academic histogram with optional KDE overlay, mean/median verticals,
Freedman-Diaconis automatic binning, right-aligned stats box.
"""

from __future__ import annotations

import math

from .._common import (
    _dist_font_sizes,
    _estimate_label_width_px,
    _fmt_axis,
    _resolve_font,
    _resolve_palette,
    _rgb_prefix,
    _variant_is_classic,
    _xesc,
    ridge_density_from_samples,
)
from . import _academic_rigor as rigor
from ._shared import tr

# Multi-mode whitelist: maps mode name → (template, trigger, validator).
# Dict insertion order defines priority under multi_mode="auto".
#   with_ecdf  : empirical CDF under the histogram (top_bottom_3to1), n ≥ 50
#   with_qq    : normal Q-Q plot to the right (left_right_3to1),      n ≥ 30
_HISTOGRAM_MULTI_WHITELIST = {
    "with_ecdf": (
        "top_bottom_2to1",
        lambda s: s.get("n", 0) >= 50,  # trigger: n ≥ 50
        lambda s: (
            (len(s.get("values", [])) > 0 and s.get("n", 0) >= 50),
            "need n>=50 with non-empty values",
        ),
    ),
    "with_qq": (
        "left_right_3to1",
        lambda s: s.get("n", 0) >= 30,  # trigger: n ≥ 30
        lambda s: (
            (len(s.get("values", [])) > 0 and s.get("n", 0) >= 30),
            "need n>=30 with non-empty values",
        ),
    ),
}


def _inv_norm_cdf(p: float) -> float:
    """Standard-normal quantile via the Beasley-Springer rational approximation."""
    import math as _m

    if p <= 0.0 or p >= 1.0:
        raise ValueError("p must be in (0,1)")
    # Standard Abramowitz-Stegun 26.2.23 approximation. For p < 0.5 operate
    # on p; for p > 0.5 operate on 1-p and flip sign at the end.
    _sign = -1.0 if p < 0.5 else 1.0
    _q = p if p < 0.5 else 1.0 - p
    t = _m.sqrt(-2.0 * _m.log(_q))
    num = 2.515517 + 0.802853 * t + 0.010328 * t * t
    den = 1.0 + 1.432788 * t + 0.189269 * t * t + 0.001308 * t * t * t
    return _sign * (t - num / den)


def _percentile(sorted_vals, p):
    """Linear-interpolation percentile. p in [0,100]."""
    n = len(sorted_vals)
    if n == 0:
        return 0.0
    if n == 1:
        return sorted_vals[0]
    k = (p / 100.0) * (n - 1)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_vals[int(k)]
    return sorted_vals[int(f)] + (sorted_vals[int(c)] - sorted_vals[int(f)]) * (k - f)


def _median(vals):
    s = sorted(vals)
    n = len(s)
    if n == 0:
        return 0.0
    if n % 2 == 1:
        return s[n // 2]
    return 0.5 * (s[n // 2 - 1] + s[n // 2])


def _freedman_diaconis_bins(vals):
    n = len(vals)
    if n < 2:
        return 1
    s = sorted(vals)
    q1 = _percentile(s, 25)
    q3 = _percentile(s, 75)
    iqr = q3 - q1
    if iqr <= 0:
        return max(1, math.ceil(math.log2(n) + 1))
    bin_w = 2.0 * iqr * (n ** (-1.0 / 3.0))
    if bin_w <= 0:
        return max(1, math.ceil(math.log2(n) + 1))
    rng = s[-1] - s[0]
    k = math.ceil(rng / bin_w) if rng > 0 else 1
    return max(5, min(80, k))  # sane floor/ceiling


def make_histogram(
    values,
    *,
    bins: int | None = None,
    x_unit: str = "",
    y_unit: str = "",
    x_title: str | None = None,
    y_title: str | None = None,
    title: str | None = None,
    subtitle: str | None = None,
    figure_label: str | None = None,
    note: str | None = None,
    source: str | None = None,
    show_kde: bool = True,
    show_mean: bool = True,
    show_median: bool = True,
    density: bool = True,
    reference_lines=None,
    highlight_range=None,
    show_stats: bool = False,
    width: float = 1200,
    height: float = 760,
    font_family: str | None = None,
    palette=None,
    variant: str | None = None,
    multi_mode: str = "auto",
) -> str:
    """Histogram with optional KDE curve + mean/median verticals + stats box.

    ``density=True`` → bars are probability density (so KDE overlays correctly).
    ``density=False`` → bars are raw counts; KDE still available but scaled to match.
    ``show_stats=True`` opts in to the n / mean / median / SD / bins box; off by
    default (mean and median are already drawn as labelled reference lines).
    """
    _variant_is_classic("histogram", variant)
    if not values:
        raise ValueError("values must be a non-empty list.")
    if palette is None:
        palette = "archive_ink"
    pal = _resolve_palette(palette)
    body_font, heading_font = _resolve_font(font_family)
    W, H = float(width), float(height)
    n = len(values)

    v_min_raw = min(values)
    v_max_raw = max(values)
    if v_min_raw == v_max_raw:
        v_min_raw -= 1
        v_max_raw += 1

    if bins is None:
        bins = _freedman_diaconis_bins(values)
    bins = max(2, int(bins))
    # Font sizes keyed to drawn bar count (the visible items on screen),
    # not raw sample count — otherwise large N shrinks fonts spuriously.
    fs = _dist_font_sizes(W, H, max(4, bins))
    bin_w = (v_max_raw - v_min_raw) / bins
    counts = [0] * bins
    for v in values:
        idx = int((v - v_min_raw) / bin_w)
        if idx == bins:
            idx = bins - 1
        if 0 <= idx < bins:
            counts[idx] += 1
    if density:
        heights = [c / (n * bin_w) for c in counts]
    else:
        heights = [float(c) for c in counts]

    x_ticks, x_min, x_max = rigor.nice_axis(v_min_raw, v_max_raw, 6)

    kde_xs = []
    kde_ys = []
    if show_kde:
        n_pts_kde = 160
        kde_vals = ridge_density_from_samples(values, x_min, x_max, n=n_pts_kde)
        kde_xs = [x_min + i * (x_max - x_min) / (n_pts_kde - 1) for i in range(n_pts_kde)]
        if density:
            kde_ys = list(kde_vals)
        else:
            # Scale KDE (density → counts/bin): count-equivalent = density * N * bin_w
            kde_ys = [d * n * bin_w for d in kde_vals]

    y_hi = max(heights) if heights else 1.0
    if kde_ys:
        y_hi = max(y_hi, max(kde_ys))
    # Bump to 1.25× so there's a clear gap below the topmost bar/KDE peak for the italic labels + stats box.
    y_hi = y_hi * 1.25
    y_ticks, y_min, y_max = rigor.nice_axis(0.0, y_hi, 5)

    max_tick_w = 0.0
    span_y = y_max - y_min
    for v in y_ticks:
        s_ = _fmt_axis(v, span_y if span_y > 0 else abs(v) or 1)
        max_tick_w = max(max_tick_w, _estimate_label_width_px(s_, fs["ytick"], font_family=body_font))

    mu = sum(values) / n
    md = _median(values)
    sd = math.sqrt(sum((v - mu) ** 2 for v in values) / max(1, n - 1)) if n > 1 else 0.0
    stats_pairs = [
        ("n", str(n)),
        (tr("mean"), f"{mu:.3g}"),
        (tr("median"), f"{md:.3g}"),
        ("SD", f"{sd:.3g}"),
        (tr("bins"), str(bins)),
    ]
    sb_svg, margin_right = "", 50
    if show_stats:
        sb_svg, stats_bbox = rigor.draw_stats_box(
            W - 30,
            116,
            stats_pairs,
            pal=pal,
            fs=fs["label"],
            anchor="end",
            font_family=body_font,
        )
        margin_right = W - stats_bbox[0] + 22

    margin_left = max_tick_w + 70
    margin_top = 110
    margin_bot = 130
    if H < rigor.COMPACT_HEIGHT:
        margin_top, margin_bot, _ = rigor.compact_margins(
            fs, title=title, subtitle=subtitle, figure_label=figure_label, footer=bool(note or source)
        )
        margin_left = max_tick_w + 56
        margin_right = min(margin_right, 28) if not show_stats else margin_right

    plot_x_left = margin_left
    plot_x_right = W - margin_right
    plot_y_top = margin_top
    plot_y_bot = H - margin_bot

    _plot_bbox = rigor.bbox_from_edges(plot_x_left, plot_x_right, plot_y_top, plot_y_bot)
    _signals = {"n": n, "values": values}
    _mm_mode, _mm_template, _mm_reason = rigor.resolve_multi_mode_v2(
        multi_mode,
        _HISTOGRAM_MULTI_WHITELIST,
        _signals,
        _plot_bbox,
    )

    # If a multi mode is active, carve out a sub region and shrink the main
    # plot box so the historic draw path reuses main.
    _sub_bbox = None
    if _mm_mode is not None and _mm_template is not None:
        # Adjacent main/sub Y-axis endpoints need room for both tick labels.
        _rects = rigor.allocate_main_sub(_plot_bbox, _mm_template, gutter_shared=max(10.0, fs["ytick"] * 1.6 + 8))
        _main_bb = _rects["main"]
        _sub_bbox = _rects["sub"]
        # Shrink the main plot box; for horizontal split templates we take the
        # left column, for vertical split templates we take the top row.
        if _mm_template.startswith("left_right"):
            plot_x_right = _main_bb.x1
        else:
            plot_y_bot = _main_bb.y1

    def X(v):
        return rigor._lin(v, x_min, x_max, plot_x_left, plot_x_right)

    def Y(v):
        return rigor._lin(v, y_min, y_max, plot_y_bot, plot_y_top)

    parts = rigor.draw_canvas_bg(pal, W, H)

    parts.append(
        rigor.draw_title_block(
            plot_x_left,
            plot_y_top - 24,
            plot_x_right - plot_x_left,
            title=title,
            subtitle=subtitle,
            figure_label=figure_label,
            pal=pal,
            fs=fs,
            body_font=body_font,
            heading_font=heading_font,
        )
    )

    parts.append(
        rigor.draw_grid(
            plot_x_left,
            plot_x_right,
            plot_y_top,
            plot_y_bot,
            pal=pal,
            y_ticks=y_ticks,
            y_min=y_min,
            y_max=y_max,
            orient="horizontal",
        )
    )

    if highlight_range:
        x1, x2 = highlight_range
        if x2 < x1:
            x1, x2 = x2, x1
        hx1 = X(max(x1, x_min))
        hx2 = X(min(x2, x_max))
        parts.append(
            f'<rect x="{hx1:.1f}" y="{plot_y_top:.1f}" width="{(hx2 - hx1):.1f}" '
            f'height="{(plot_y_bot - plot_y_top):.1f}" '
            f'fill="{_rgb_prefix(pal["accent"])}0.08)" stroke="none"/>'
        )

    accent = pal["accent"]
    bar_fill = f"{_rgb_prefix(accent)}0.42)"
    # C-polish: use white 1px stroke to add a hairline gap between adjacent bars,
    # giving the histogram a journal-grade "ticks" look rather than a flat block.
    bar_stroke = pal.get("bg", "rgba(255,255,255,1)")
    for i, h in enumerate(heights):
        x0 = X(v_min_raw + i * bin_w)
        x1 = X(v_min_raw + (i + 1) * bin_w)
        y_top = Y(h)
        y_bot = Y(0.0)
        parts.append(
            f'<rect x="{x0:.2f}" y="{y_top:.2f}" width="{(x1 - x0 - 0.5):.2f}" '
            f'height="{(y_bot - y_top):.2f}" '
            f'fill="{bar_fill}" stroke="{bar_stroke}" stroke-width="1"/>'
        )

    # KDE curve on top — C-polish: ink grey, 2px (stronger than previous 1.8).
    if kde_xs and kde_ys:
        kcolor = pal.get("ink", "rgba(28,28,26,1)")
        d_parts = []
        for i, (xk, yk) in enumerate(zip(kde_xs, kde_ys)):
            px, py = X(xk), Y(yk)
            d_parts.append(f"{'M' if i == 0 else 'L'} {px:.1f} {py:.1f}")
        parts.append(f'<path d="{" ".join(d_parts)}" fill="none" stroke="{kcolor}" stroke-width="2"/>')

    # Drop both rows ~1 line further down and keep median ~1.3 lines below mean to prevent inter-label collision on
    # tied-x cases.
    _label_mean_y = plot_y_top + fs["label"] * 2.5
    _label_median_y = plot_y_top + fs["label"] * 3.8
    if show_mean and x_min <= mu <= x_max:
        mx = X(mu)
        # C-polish: mean = 1.5px accent dashed.
        parts.append(
            f'<line x1="{mx:.1f}" y1="{plot_y_top:.1f}" x2="{mx:.1f}" y2="{plot_y_bot:.1f}" '
            f'stroke="{pal["accent"]}" stroke-width="1.5" stroke-dasharray="6 3"/>'
        )
        parts.append(
            f'<text x="{mx + 4:.1f}" y="{_label_mean_y:.1f}" '
            f'font-size="{fs["label"]:.1f}" fill="{pal["accent"]}" font-style="italic">{_xesc(tr("mean") + " " + f"{mu:.3g}")}</text>'
        )
    if show_median and x_min <= md <= x_max:
        mx = X(md)
        # C-polish: median = 1.5px ink dotted (2 3 dasharray reads as dots).
        parts.append(
            f'<line x1="{mx:.1f}" y1="{plot_y_top:.1f}" x2="{mx:.1f}" y2="{plot_y_bot:.1f}" '
            f'stroke="{pal["ink"]}" stroke-width="1.5" stroke-dasharray="1 3"/>'
        )
        # median label sits one line below the mean label so the two text rows
        # never collide when mean / median land on near-identical x.
        parts.append(
            f'<text x="{mx + 4:.1f}" y="{_label_median_y:.1f}" '
            f'font-size="{fs["label"]:.1f}" fill="{pal["ink6"]}" font-style="italic">{_xesc(tr("median") + " " + f"{md:.3g}")}</text>'
        )

    if reference_lines:
        for ref in reference_lines:
            if not ref:
                continue
            xv = ref[0]
            lbl = ref[1] if len(ref) > 1 else ""
            if xv < x_min or xv > x_max:
                continue
            parts.append(
                rigor.draw_reference_line(
                    X(xv),
                    plot_y_top,
                    plot_y_bot,
                    pal=pal,
                    orient="vertical",
                    dash="3 5",
                    color=pal["ink6"],
                    label=lbl,
                    label_fs=fs["label"],
                )
            )

    parts.append(
        rigor.draw_y_axis(
            plot_x_left,
            plot_y_top,
            plot_y_bot,
            y_ticks,
            y_min,
            y_max,
            unit=y_unit,
            pal=pal,
            fs_tick=fs["ytick"],
            fs_title=fs["yaxis"],
            title=y_title or (tr("Density") if density else tr("Count")),
            side="left",
        )
    )
    parts.append(
        rigor.draw_x_axis(
            plot_x_left,
            plot_x_right,
            plot_y_bot,
            x_ticks,
            x_min,
            x_max,
            unit=x_unit,
            pal=pal,
            fs_tick=fs["ytick"],
            fs_title=fs["yaxis"],
            title=x_title,
            show_tick_labels=(_sub_bbox is None or _mm_mode == "with_qq"),
        )
    )

    if sb_svg:
        parts.append(sb_svg)

    if _sub_bbox is not None and _mm_mode == "with_ecdf":
        # Collect protected rects so the sub bbox doesn't collide with any already-drawn panel content.
        _raw_protected = rigor.collect_protected_bboxes(parts)
        _sub_w = rigor.bbox_width(_sub_bbox)
        _sub_h = rigor.bbox_height(_sub_bbox)
        _protected = [
            b
            for b in _raw_protected
            # exclude anything wider than main plot area (bg, highlight)
            if rigor.bbox_width(b) < (plot_x_right - plot_x_left) * 0.9
            # exclude anything that lives inside the main plot box (bars)
            and not (b.y1 <= plot_y_bot + 1 and b.y0 >= plot_y_top - 1 and rigor.bbox_width(b) < _sub_w)
        ]
        rigor.assert_no_overlap(_sub_bbox, tuple(_protected), tol=2.0, name="ecdf sub-panel")

        parts.append(
            rigor.draw_ecdf_subpanel(
                _sub_bbox,
                [(values, pal.get("ink", "rgba(28,28,26,1)"))],
                x_min=x_min,
                x_max=x_max,
                x_ticks=x_ticks,
                x_unit=x_unit,
                x_title=x_title,
                pal=pal,
                fs=fs,
            )
        )

    if _sub_bbox is not None and _mm_mode == "with_qq":
        _raw_protected = rigor.collect_protected_bboxes(parts)
        _sub_w = rigor.bbox_width(_sub_bbox)
        _sub_h = rigor.bbox_height(_sub_bbox)
        _protected = [
            b
            for b in _raw_protected
            if rigor.bbox_width(b) < (plot_x_right - plot_x_left) * 0.9
            and not (b.y1 <= plot_y_bot + 1 and b.y0 >= plot_y_top - 1 and rigor.bbox_width(b) < _sub_w)
        ]
        rigor.assert_no_overlap(_sub_bbox, tuple(_protected), tol=2.0, name="qq sub-panel")

        qx_left, qx_right, qy_top, qy_bot = rigor.bbox_to_edges(_sub_bbox)
        sub_fs_tick = max(10.0, fs["ytick"] * 0.88)
        sub_fs_title = max(10.0, fs["yaxis"] * 0.88)

        # Compute sample quantiles (sorted) vs theoretical standard-normal
        # quantiles. Center probability positions via Blom's rule p=(i-3/8)/(n+1/4).
        _xs_sorted = sorted(float(v) for v in values)
        _n = len(_xs_sorted)
        _qq_pts = []
        for i, v in enumerate(_xs_sorted):
            p = (i + 1 - 0.375) / (_n + 0.25)
            p = min(max(p, 1e-6), 1.0 - 1e-6)
            z = _inv_norm_cdf(p)
            _qq_pts.append((z, v))

        # Standardize sample values for the y-axis so the reference line y=x
        # is meaningful. zs are already standard normal; compute sample mean/sd.
        _mu = sum(_xs_sorted) / _n
        _sd = math.sqrt(sum((v - _mu) ** 2 for v in _xs_sorted) / max(1, _n - 1))
        if _sd <= 0:
            _sd = 1.0
        _std_pts = [(z, (v - _mu) / _sd) for (z, v) in _qq_pts]

        _zmin = min(p[0] for p in _std_pts)
        _zmax = max(p[0] for p in _std_pts)
        _ymin = min(p[1] for p in _std_pts)
        _ymax = max(p[1] for p in _std_pts)
        _lim_lo = min(_zmin, _ymin)
        _lim_hi = max(_zmax, _ymax)
        # Symmetric padding so the y=x diagonal spans the whole square.
        _pad = (_lim_hi - _lim_lo) * 0.08
        _lim_lo -= _pad
        _lim_hi += _pad
        _x_ticks_q, _xq_min, _xq_max = rigor.nice_axis(_lim_lo, _lim_hi, 5)
        _y_ticks_q, _yq_min, _yq_max = rigor.nice_axis(_lim_lo, _lim_hi, 5)

        def _QX(v):
            return rigor._lin(v, _xq_min, _xq_max, qx_left, qx_right)

        def _QY(v):
            return rigor._lin(v, _yq_min, _yq_max, qy_bot, qy_top)

        parts.append(
            rigor.draw_grid(
                qx_left,
                qx_right,
                qy_top,
                qy_bot,
                pal=pal,
                y_ticks=_y_ticks_q,
                y_min=_yq_min,
                y_max=_yq_max,
                orient="horizontal",
            )
        )

        # y = x diagonal reference line (clipped to axes).
        _ref_lo = max(_xq_min, _yq_min)
        _ref_hi = min(_xq_max, _yq_max)
        parts.append(
            f'<line x1="{_QX(_ref_lo):.1f}" y1="{_QY(_ref_lo):.1f}" '
            f'x2="{_QX(_ref_hi):.1f}" y2="{_QY(_ref_hi):.1f}" '
            f'stroke="{pal["ink"]}" stroke-width="1.2" stroke-dasharray="5 4" '
            f'opacity="0.75"/>'
        )

        _col_pt = pal.get("accent", "rgba(217,106,46,1)")
        for z, y in _std_pts:
            parts.append(
                f'<circle cx="{_QX(z):.2f}" cy="{_QY(y):.2f}" r="2.0" fill="{_col_pt}" stroke="none" opacity="0.75"/>'
            )

        parts.append(
            rigor.draw_y_axis(
                qx_left,
                qy_top,
                qy_bot,
                _y_ticks_q,
                _yq_min,
                _yq_max,
                pal=pal,
                fs_tick=sub_fs_tick,
                fs_title=sub_fs_title,
                title=tr("Sample z"),
                side="left",
            )
        )
        parts.append(
            rigor.draw_x_axis(
                qx_left,
                qx_right,
                qy_bot,
                _x_ticks_q,
                _xq_min,
                _xq_max,
                pal=pal,
                fs_tick=sub_fs_tick,
                fs_title=sub_fs_title,
                title=tr("Theoretical z"),
                show_tick_labels=True,
            )
        )
        parts.append(
            f'<text x="{qx_left:.1f}" y="{qy_top - 8:.1f}" '
            f'font-size="{sub_fs_title:.1f}" fill="{pal["ink"]}" '
            f'font-weight="600">Normal Q-Q</text>'
        )

    parts.append(rigor.draw_footer(note, source, pal, fs, plot_x_left, plot_x_right, H - 20))

    return rigor.wrap_svg(parts, W, H, body_font)
