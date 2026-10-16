"""Academic chart: parallel coordinates plot."""

from __future__ import annotations

import math

from .._common import (
    _derive_series_colors,
    _dist_font_sizes,
    _estimate_label_width_px,
    _resolve_font,
    _resolve_palette,
    _rgb_prefix,
    _variant_is_classic,
    _xesc,
)
from . import _academic_rigor as rigor


# Multi-mode whitelist: with_axis_corr → bar strip of Spearman rank correlation
# between adjacent axes. Trigger: n_axes >= 4. Validator: adequate per-axis data.
def _validate_axis_corr(signals):
    n_axes = int(signals.get("n_axes", 0))
    n_samples_valid = int(signals.get("n_samples_valid", 0))
    if n_axes < 4:
        return (False, f"need >=4 axes (got {n_axes})")
    if n_samples_valid < 3:
        return (False, f"need >=3 complete samples (got {n_samples_valid})")
    return (True, "")


_PCOORDS_MULTI_WHITELIST = {
    "with_axis_corr": (
        "top_bottom_2to1",
        lambda s: int(s.get("n_axes", 0)) >= 4,
        lambda s: _validate_axis_corr(s),
    ),
}


def _rank(arr):
    """Return 1-based ranks with ties broken by position (stable, no tie-average)."""
    sorted_idx = sorted(range(len(arr)), key=lambda i: arr[i])
    ranks = [0] * len(arr)
    for r, i in enumerate(sorted_idx):
        ranks[i] = r + 1
    return ranks


def _pearson(xs, ys):
    n = len(xs)
    if n < 2:
        return 0.0
    mx = sum(xs) / n
    my = sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sx = (sum((x - mx) ** 2 for x in xs)) ** 0.5
    sy = (sum((y - my) ** 2 for y in ys)) ** 0.5
    return sxy / (sx * sy) if sx * sy > 0 else 0.0


def _spearman(xs, ys):
    return _pearson(_rank(xs), _rank(ys))


def _quartiles(values):
    """Return (q1, median, q3) using the "exclusive" method commonly used in plots."""
    if not values:
        return 0.0, 0.0, 0.0
    s = sorted(values)
    n = len(s)

    def _pct(p):
        if n == 1:
            return s[0]
        rank = (n - 1) * p
        lo = math.floor(rank)
        hi = math.ceil(rank)
        if lo == hi:
            return s[lo]
        frac = rank - lo
        return s[lo] + (s[hi] - s[lo]) * frac

    return _pct(0.25), _pct(0.5), _pct(0.75)


def make_parallel_coords(
    samples,
    axes,
    *,
    title: str | None = None,
    subtitle: str | None = None,
    figure_label: str | None = None,
    note: str | None = None,
    source: str | None = None,
    highlight_group: str | None = None,
    show_quartile_band: bool = True,
    group_palette=None,
    width: float = 1400,
    height: float = 760,
    font_family: str | None = None,
    palette=None,
    variant: str | None = None,
    multi_mode: str = "auto",
) -> str:
    """Parallel coordinates plot.

    ``samples``: list of dict with keys ``values`` (list[float], len == len(axes))
      and optional ``group`` (str).
    ``axes``: list of ``(axis_name, unit)`` tuples.
    """
    _variant_is_classic("parallel_coords", variant)
    if palette is None:
        palette = "archive_ink"
    pal = _resolve_palette(palette)
    body_font, heading_font = _resolve_font(font_family)
    W, H = float(width), float(height)

    n_axes = len(axes)
    if n_axes < 2 or not samples:
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}">'
            f'<text x="{W / 2}" y="{H / 2}" text-anchor="middle" font-size="16" '
            f'fill="{pal["ink6"]}">Need ≥2 axes and ≥1 sample</text></svg>'
        )

    per_axis = [[] for _ in range(n_axes)]
    for s in samples:
        vals = s.get("values", [])
        for i in range(min(len(vals), n_axes)):
            try:
                per_axis[i].append(float(vals[i]))
            except (TypeError, ValueError):
                pass

    axis_ranges = []  # list of (ticks, v_min, v_max)
    for col_vals in per_axis:
        if not col_vals:
            axis_ranges.append(([0.0, 1.0], 0.0, 1.0))
            continue
        ticks, vmin, vmax = rigor.nice_axis(min(col_vals), max(col_vals), 5)
        axis_ranges.append((ticks, vmin, vmax))

    group_order = []
    group_seen = set()
    for s in samples:
        g = s.get("group")
        if g is not None and g not in group_seen:
            group_seen.add(g)
            group_order.append(g)
    if group_palette:
        g_colors = {g: group_palette.get(g, pal["accent"]) for g in group_order}
    else:
        n_g = max(1, len(group_order))
        colors = _derive_series_colors(pal, n_g, mode="distinct")
        g_colors = {g: colors[i] for i, g in enumerate(group_order)}

    fs = _dist_font_sizes(W, H, max(4, n_axes))
    margin_top = 100  # title block anchor
    margin_bot = 110
    margin_left = 90
    margin_right = 90

    # legend band sits between title and the plot's axis-name row.
    legend_h = 36 if group_order else 0
    plot_x_left = margin_left
    plot_x_right = W - margin_right
    # Reserve extra vertical space (76 px) for axis name + unit above the vertical axes themselves.
    plot_y_top = margin_top + legend_h + 96
    plot_y_bot = H - margin_bot

    # Count samples with all valid values across all axes.
    n_samples_valid = 0
    for s in samples:
        vals = s.get("values", [])
        if len(vals) < n_axes:
            continue
        ok = True
        for v in vals[:n_axes]:
            try:
                float(v)
            except (TypeError, ValueError):
                ok = False
                break
        if ok:
            n_samples_valid += 1

    _full_plot_bbox = rigor.bbox_from_edges(
        plot_x_left,
        plot_x_right,
        plot_y_top,
        plot_y_bot,
    )
    _mm_signals = {
        "n_axes": n_axes,
        "n_samples_valid": n_samples_valid,
    }
    _mm_mode, _mm_template, _mm_reason = rigor.resolve_multi_mode_v2(
        multi_mode,
        _PCOORDS_MULTI_WHITELIST,
        _mm_signals,
        _full_plot_bbox,
    )
    _sub_bbox = None
    if _mm_mode is not None and _mm_template is not None:
        # Wide gutter so the main-axis category labels (m1→m2 …) and the
        # Spearman sub-panel's y-axis + title have breathing room.
        _rects = rigor.allocate_main_sub(_full_plot_bbox, _mm_template, gutter_shared=70)
        _main_bb = _rects["main"]
        _sub_bbox = _rects["sub"]
        plot_y_bot = _main_bb.y1

    axis_fs = max(13.0, fs["label"])
    tick_fs = max(11.0, fs["ytick"])

    def ax_x(i):
        if n_axes == 1:
            return (plot_x_left + plot_x_right) * 0.5
        return plot_x_left + i * (plot_x_right - plot_x_left) / (n_axes - 1)

    def Y_for(i, v):
        _, vmin, vmax = axis_ranges[i]
        return rigor._lin(v, vmin, vmax, plot_y_bot, plot_y_top)

    parts = rigor.draw_canvas_bg(pal, W, H)

    # title: anchor just above the legend band
    parts.append(
        rigor.draw_title_block(
            plot_x_left,
            margin_top - 10,
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

    ink = pal["ink"]
    ink6 = pal["ink6"]

    if group_order:
        legend_fs = max(13.0, fs["label"])
        lg_y = margin_top + 24
        cursor_x = plot_x_left
        swatch_r = 6
        for g in group_order:
            col = g_colors[g]
            parts.append(
                f'<circle cx="{cursor_x + swatch_r:.1f}" cy="{lg_y:.1f}" r="{swatch_r}" '
                f'fill="{col}" stroke="{ink}" stroke-width="0.6"/>'
            )
            text_x = cursor_x + swatch_r * 2 + 6
            parts.append(
                f'<text x="{text_x:.1f}" y="{lg_y + legend_fs * 0.35:.1f}" '
                f'font-size="{legend_fs}" fill="{ink}">{_xesc(g)}</text>'
            )
            tw = _estimate_label_width_px(str(g), legend_fs, font_family=body_font)
            cursor_x = text_x + tw + 24
            if cursor_x > plot_x_right - 100:
                cursor_x = plot_x_left
                lg_y += legend_fs + 6

    if show_quartile_band:
        band_w = 10.0
        band_fill = f"{_rgb_prefix(pal['accent'])}0.12)"
        band_stroke = f"{_rgb_prefix(pal['accent'])}0.4)"
        for i in range(n_axes):
            if not per_axis[i]:
                continue
            q1, med, q3 = _quartiles(per_axis[i])
            x_center = ax_x(i)
            y_hi = Y_for(i, q3)
            y_lo = Y_for(i, q1)
            y_top = min(y_hi, y_lo)
            y_bot = max(y_hi, y_lo)
            parts.append(
                f'<rect x="{x_center - band_w / 2:.1f}" y="{y_top:.1f}" '
                f'width="{band_w:.1f}" height="{y_bot - y_top:.1f}" '
                f'fill="{band_fill}" stroke="{band_stroke}" stroke-width="0.8"/>'
            )
            y_med = Y_for(i, med)
            parts.append(
                f'<line x1="{x_center - band_w / 2 - 3:.1f}" y1="{y_med:.1f}" '
                f'x2="{x_center + band_w / 2 + 3:.1f}" y2="{y_med:.1f}" '
                f'stroke="{pal["accent"]}" stroke-width="1.4"/>'
            )

    def draw_sample(s, is_hi):
        vals = s.get("values", [])
        if len(vals) < n_axes:
            return ""
        d_parts = []
        for i in range(n_axes):
            try:
                v = float(vals[i])
            except (TypeError, ValueError):
                return ""
            x = ax_x(i)
            y = Y_for(i, v)
            d_parts.append(f"{'M' if i == 0 else 'L'} {x:.1f} {y:.1f}")
        d = " ".join(d_parts)
        g = s.get("group")
        if is_hi:
            col = g_colors.get(g, pal["accent"]) if g else pal["accent"]
            return f'<path d="{d}" fill="none" stroke="{col}" stroke-width="2.2" stroke-opacity="0.95"/>'
        else:
            if g and g in g_colors:
                col = g_colors[g]
                return f'<path d="{d}" fill="none" stroke="{col}" stroke-width="1.1" stroke-opacity="0.55"/>'
            # ungrouped → muted ink2
            muted_col = f"{_rgb_prefix(ink)}0.28)"
            return f'<path d="{d}" fill="none" stroke="{muted_col}" stroke-width="0.9"/>'

    for s in samples:
        if highlight_group and s.get("group") == highlight_group:
            continue
        parts.append(draw_sample(s, is_hi=False))
    if highlight_group:
        for s in samples:
            if s.get("group") == highlight_group:
                parts.append(draw_sample(s, is_hi=True))

    for i in range(n_axes):
        x = ax_x(i)
        ticks, vmin, vmax = axis_ranges[i]
        parts.append(
            f'<line x1="{x:.1f}" y1="{plot_y_top:.1f}" x2="{x:.1f}" y2="{plot_y_bot:.1f}" '
            f'stroke="{ink}" stroke-width="1.2"/>'
        )
        span = vmax - vmin
        _labels = rigor._tick_label_map(ticks, span)
        for tv in ticks:
            if tv < vmin - 1e-9 or tv > vmax + 1e-9:
                continue
            ty = Y_for(i, tv)
            parts.append(
                f'<line x1="{x - 4:.1f}" y1="{ty:.1f}" x2="{x + 4:.1f}" y2="{ty:.1f}" stroke="{ink}" stroke-width="1"/>'
            )
            # label on left side (except last axis → put on right)
            if i == n_axes - 1:
                lx = x + 7
                anchor = "start"
            else:
                lx = x - 7
                anchor = "end"
            parts.append(
                f'<text x="{lx:.1f}" y="{ty + tick_fs * 0.35:.1f}" '
                f'font-size="{tick_fs}" fill="{ink6}" text-anchor="{anchor}">'
                f"{_xesc(_labels[tv])}</text>"
            )
        # axis title (above axis) — placed above the top-tick numeric label row.
        # The top tick is drawn at y ≈ plot_y_top + tick_fs*0.35; with tick_fs up
        # to ~17 the top-tick bbox reaches to about y ≈ plot_y_top - 15. Axis
        # name baseline at plot_y_top - 48 keeps its 22px bbox safely above.
        ax_name, ax_unit = axes[i]
        parts.append(
            f'<text x="{x:.1f}" y="{plot_y_top - 58:.1f}" font-size="{axis_fs}" '
            f'fill="{ink}" text-anchor="middle" font-weight="600">{_xesc(ax_name)}</text>'
        )
        if ax_unit:
            parts.append(
                f'<text x="{x:.1f}" y="{plot_y_top - 28:.1f}" '
                f'font-size="{max(11.0, axis_fs * 0.85):.1f}" fill="{ink6}" '
                f'text-anchor="middle" font-style="italic">{_xesc(ax_unit)}</text>'
            )

    # stats summary — single-line chip at the title row, right-aligned. Keeping
    # it to one line (one text element) avoids colliding with the right-most
    # axis's name / unit / top-tick labels directly beneath it. The previous
    # multi-row stats panel occupied the same vertical band as those labels
    # and triggered bbox_overlap warnings at every rendering scale.
    _stats_fs = max(13.0, fs["label"])
    _stats_parts = [f"n = {len(samples)}"]
    if group_order:
        _stats_parts.append(f"{len(group_order)} groups")
    _stats_parts.append(f"{n_axes} axes")
    _stats_text = " · ".join(_stats_parts)
    parts.append(
        f'<text x="{plot_x_right:.1f}" y="{margin_top - 4:.1f}" '
        f'font-size="{_stats_fs}" fill="{pal["ink6"]}" text-anchor="end" '
        f'font-feature-settings="tnum">{_xesc(_stats_text)}</text>'
    )

    if _sub_bbox is not None and _mm_mode == "with_axis_corr":
        _render_axis_corr_sub(
            parts,
            _sub_bbox,
            samples,
            axes,
            per_axis,
            ax_x,
            pal=pal,
            fs=fs,
            body_font=body_font,
        )

    parts.append(rigor.draw_footer(note, source, pal, fs, plot_x_left, plot_x_right, H - 36))

    return rigor.wrap_svg(parts, W, H, body_font)


# Multi-mode sub-panel renderer: Spearman rank correlation between adjacent axes.
def _render_axis_corr_sub(
    parts,
    sub_bbox,
    samples,
    axes,
    per_axis,
    ax_x_fn,
    *,
    pal,
    fs,
    body_font,
):
    """Bar strip plotting Spearman(axis_i, axis_{i+1}) at the midpoint of each adjacent axis pair."""
    sx0, sy0 = sub_bbox.x0, sub_bbox.y0
    sx1, sy1 = sub_bbox.x1, sub_bbox.y1
    ink = pal.get("ink", "rgba(28,28,26,1)")
    ink6 = pal.get("ink6", "rgba(28,28,26,0.6)")
    accent = pal.get("accent", "rgba(163,88,50,1)")

    n_axes = len(axes)
    # Compute Spearman between axis i and i+1 using samples with both values valid.
    corrs = []
    for i in range(n_axes - 1):
        xs = []
        ys = []
        for s in samples:
            vals = s.get("values", [])
            if len(vals) <= i + 1:
                continue
            try:
                x = float(vals[i])
                y = float(vals[i + 1])
            except (TypeError, ValueError):
                continue
            xs.append(x)
            ys.append(y)
        if len(xs) >= 3:
            r = _spearman(xs, ys)
        else:
            r = 0.0
        corrs.append((i, r, len(xs)))

    _pad_top = 24.0
    _pad_bot = 32.0
    _pad_left = 60.0
    _pad_right = 20.0
    ax_y0 = sy0 + _pad_top
    ax_y1 = sy1 - _pad_bot

    _sub_title_fs = max(11.0, fs["label"])
    parts.append(
        f'<text x="{sx0:.1f}" y="{sy0 + _sub_title_fs:.1f}" '
        f'font-size="{_sub_title_fs:.1f}" fill="{ink6}" font-style="italic">'
        f"Spearman rank correlation · adjacent axes</text>"
    )

    # Y axis: -1 ... 1
    y_ticks = [-1.0, -0.5, 0.0, 0.5, 1.0]
    y_vmin, y_vmax = -1.0, 1.0

    def Y(v):
        return rigor._lin(v, y_vmin, y_vmax, ax_y1, ax_y0)

    y_zero = Y(0.0)

    # Draw Y axis on left of sub region (shared x positions with main axes).
    sub_fs_tick = max(10.0, fs["ytick"] * 0.88)
    parts.append(
        rigor.draw_y_axis(
            sx0 + _pad_left,
            ax_y0,
            ax_y1,
            y_ticks,
            y_vmin,
            y_vmax,
            pal=pal,
            fs_tick=sub_fs_tick,
            title="ρ",
            side="left",
        )
    )

    parts.append(rigor.draw_zero_line(sx0 + _pad_left, sx1 - _pad_right, y_zero, pal=pal))

    if n_axes >= 2:
        gap_px = ax_x_fn(1) - ax_x_fn(0)
    else:
        gap_px = 60.0
    bar_w = min(gap_px * 0.6, 40.0)

    for i, r, n in corrs:
        # X: midpoint between axis i and axis i+1
        cx = (ax_x_fn(i) + ax_x_fn(i + 1)) * 0.5
        # Clamp cx so bars stay within sub panel region
        bx = cx - bar_w * 0.5
        y_val = Y(r)
        y_top = min(y_val, y_zero)
        y_bot = max(y_val, y_zero)
        parts.append(
            f'<rect x="{bx:.1f}" y="{y_top:.1f}" '
            f'width="{bar_w:.1f}" height="{(y_bot - y_top):.1f}" '
            f'fill="{accent}" stroke="{ink}" stroke-width="0.6" opacity="0.85"/>'
        )
        val_fs = max(10.0, fs["label"] - 1)
        if r >= 0:
            ly = y_top - 4
            baseline_adj = 0.0
        else:
            ly = y_bot + val_fs
            baseline_adj = 0.0
        parts.append(
            f'<text x="{cx:.1f}" y="{ly + baseline_adj:.1f}" '
            f'font-size="{val_fs:.1f}" fill="{ink}" text-anchor="middle">'
            f"{r:.2f}</text>"
        )
        # pair tick label (axis_i → axis_{i+1}) just below bottom
        name_i = axes[i][0] if i < len(axes) else str(i)
        name_j = axes[i + 1][0] if (i + 1) < len(axes) else str(i + 1)
        label_fs = max(9.0, fs["label"] - 2)
        parts.append(
            f'<text x="{cx:.1f}" y="{ax_y1 + label_fs + 4:.1f}" '
            f'font-size="{label_fs:.1f}" fill="{ink6}" text-anchor="middle">'
            f"{_xesc(name_i)}→{_xesc(name_j)}</text>"
        )
