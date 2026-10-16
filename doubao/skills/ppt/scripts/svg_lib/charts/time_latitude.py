"""Academic chart: time-latitude (Hovmöller) diagram."""

from __future__ import annotations

import math

from .._common import (
    _dist_font_sizes,
    _fmt_axis,
    _resolve_font,
    _resolve_palette,
    _rgb_prefix,
    _variant_is_classic,
    _xesc,
)
from . import _academic_rigor as rigor
from ._shared import tr


# Multi-mode whitelist (mode → (template, trigger, validator)).
#   with_zonal_mean : right-side mini panel showing per-latitude time-average
#                     bars sharing the Y (latitude) axis with the main plot.
# Dict insertion order defines priority under multi_mode="auto".
def _validate_time_latitude_zonal(s):
    n_t = int(s.get("n_times", 0))
    n_lat = int(s.get("n_lats", 0))
    rows = int(s.get("rows", 0))
    cols = int(s.get("cols", 0))
    if n_t < 20:
        return (False, "need n_times >= 20")
    if n_lat < 2:
        return (False, "need n_lats >= 2")
    if rows != n_t or cols != n_lat:
        return (False, f"matrix shape ({rows}x{cols}) must equal (n_times x n_lats) ({n_t}x{n_lat})")
    return (True, "")


_TIME_LATITUDE_MULTI_WHITELIST = {
    "with_zonal_mean": (
        "left_right_3to1",
        lambda s: int(s.get("n_times", 0)) >= 20,
        lambda s: _validate_time_latitude_zonal(s),
    ),
}


def _diverging_stops(pal):
    """Build a 3-stop diverging ramp: cool - neutral - warm."""
    neutral = pal.get("bg", "rgba(240,235,222,1)")
    warm = pal.get("accent", "rgba(163,88,50,1)")
    cool = pal.get("secondary", None)
    if not cool or cool == pal.get("ink"):
        cool = "rgba(42,86,122,1)"
    return [cool, neutral, warm]


def _sequential_stops(pal):
    bg = pal.get("bg", "rgba(240,235,222,1)")
    accent = pal.get("accent", "rgba(163,88,50,1)")
    return [bg, accent]


def _contour_segments_matrix(matrix, level, xs, ys):
    from .contour import _contour_segments

    return _contour_segments(matrix, level, xs, ys)


def make_time_latitude(
    matrix,
    times,
    latitudes,
    *,
    time_unit: str = "",
    lat_unit: str = "°",
    value_unit: str = "",
    value_title: str | None = None,
    title: str | None = None,
    subtitle: str | None = None,
    figure_label: str | None = None,
    note: str | None = None,
    source: str | None = None,
    log_color: bool = False,
    diverging: bool = False,
    contour_overlay: bool = False,
    anomaly: bool = False,
    width: float = 1400,
    height: float = 760,
    font_family: str | None = None,
    palette=None,
    variant: str | None = None,
    multi_mode: str = "auto",
) -> str:
    """Hovmöller time-latitude diagram.

    ``matrix[t][lat]`` is the scalar value at time ``times[t]`` and latitude
    ``latitudes[lat]``. Returns a complete ``<svg>...</svg>`` string.
    """
    _variant_is_classic("time_latitude", variant)
    if palette is None:
        palette = "archive_ink"
    pal = _resolve_palette(palette)
    body_font, heading_font = _resolve_font(font_family)
    W, H = float(width), float(height)
    fs = _dist_font_sizes(W, H, max(len(times) // 4, 6))

    n_t = len(times)
    n_lat = len(latitudes)
    if n_t == 0 or n_lat == 0 or not matrix:
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}">'
            f'<text x="{W / 2}" y="{H / 2}" text-anchor="middle" font-size="16" '
            f'fill="{pal["ink6"]}">{_xesc(tr("No data"))}</text></svg>'
        )

    # shape validation — fail fast at API boundary rather than at matrix[i][j]
    if len(matrix) != n_t:
        raise ValueError(f"matrix rows ({len(matrix)}) must equal len(times) ({n_t})")
    if any(len(row) != n_lat for row in matrix):
        bad = [i for i, row in enumerate(matrix) if len(row) != n_lat]
        raise ValueError(f"each matrix row must equal len(latitudes) ({n_lat}); mismatched rows: {bad[:5]}")

    # transpose for drawing: for each (t, lat) we draw a cell at that x,y.
    # matrix shape: [n_t][n_lat]
    flat_vals = []
    for row in matrix:
        for v in row:
            if v is None or (isinstance(v, float) and not math.isfinite(v)):
                continue
            flat_vals.append(v)
    if not flat_vals:
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}">'
            f'<text x="{W / 2}" y="{H / 2}" text-anchor="middle" font-size="16" '
            f'fill="{pal["ink6"]}">{_xesc(tr("No data"))}</text></svg>'
        )

    v_min_raw = min(flat_vals)
    v_max_raw = max(flat_vals)

    if anomaly:
        v_abs = max(abs(v_min_raw), abs(v_max_raw))
        v_lo, v_hi = -v_abs, v_abs
        diverging = True
    else:
        v_lo, v_hi = v_min_raw, v_max_raw
    if log_color:
        v_lo = max(v_lo, 1e-30)

    if diverging or anomaly:
        stops = _diverging_stops(pal)
    else:
        stops = _sequential_stops(pal)

    margin_top = 110
    margin_bot = 130
    margin_left = 110
    cbar_w = 24
    margin_right = 160  # colorbar + unit text room
    if H < rigor.COMPACT_HEIGHT:
        margin_top, margin_bot, margin_left = rigor.compact_margins(
            fs, title=title, subtitle=subtitle, figure_label=figure_label, footer=bool(note or source)
        )
        margin_right = 130

    plot_x_left = margin_left
    plot_x_right = W - margin_right
    plot_y_top = margin_top
    plot_y_bot = H - margin_bot

    _full_plot_bbox = rigor.bbox_from_edges(
        plot_x_left,
        plot_x_right,
        plot_y_top,
        plot_y_bot,
    )
    _mm_signals = {
        "n_times": n_t,
        "n_lats": n_lat,
        "rows": len(matrix),
        "cols": len(matrix[0]) if matrix else 0,
    }
    _mm_mode, _mm_template, _mm_reason = rigor.resolve_multi_mode_v2(
        multi_mode,
        _TIME_LATITUDE_MULTI_WHITELIST,
        _mm_signals,
        _full_plot_bbox,
    )
    _sub_bbox = None
    if _mm_mode is not None and _mm_template is not None:
        _rects = rigor.allocate_main_sub(_full_plot_bbox, _mm_template)
        _main_bb = _rects["main"]
        _sub_bbox = _rects["sub"]
        # Shrink the main plot horizontally; colorbar will move to just past
        # the sub panel so both share the right-side gutter.
        plot_x_right = _main_bb.x1

    t_min, t_max = min(times), max(times)
    if t_max == t_min:
        t_max = t_min + 1
    lat_min, lat_max = min(latitudes), max(latitudes)
    if lat_max == lat_min:
        lat_max = lat_min + 1

    def X(t):
        return rigor._lin(t, t_min, t_max, plot_x_left, plot_x_right)

    def Y(lat):
        return rigor._lin(lat, lat_min, lat_max, plot_y_bot, plot_y_top)

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

    def cell_x_bounds(i):
        if i == 0:
            left = times[0]
        else:
            left = 0.5 * (times[i - 1] + times[i])
        if i == n_t - 1:
            right = times[-1]
        else:
            right = 0.5 * (times[i] + times[i + 1])
        return left, right

    def cell_y_bounds(j):
        if j == 0:
            lo = latitudes[0]
        else:
            lo = 0.5 * (latitudes[j - 1] + latitudes[j])
        if j == n_lat - 1:
            hi = latitudes[-1]
        else:
            hi = 0.5 * (latitudes[j] + latitudes[j + 1])
        return lo, hi

    for i in range(n_t):
        tL, tR = cell_x_bounds(i)
        xL, xR = X(tL), X(tR)
        for j in range(n_lat):
            lLo, lHi = cell_y_bounds(j)
            yLo, yHi = Y(lLo), Y(lHi)  # yLo is screen y for lower lat (bottom)
            v = matrix[i][j]
            if v is None or (isinstance(v, float) and not math.isfinite(v)):
                continue
            fill = rigor.value_to_color(v, v_lo, v_hi, pal, log=log_color, stops=stops)
            x0 = min(xL, xR)
            w = abs(xR - xL)
            y0 = min(yLo, yHi)
            h = abs(yHi - yLo)
            parts.append(
                f'<rect x="{x0:.2f}" y="{y0:.2f}" width="{w + 0.6:.2f}" '
                f'height="{h + 0.6:.2f}" fill="{fill}" stroke="none"/>'
            )

    if contour_overlay:
        # pick 5 isoline levels evenly between v_lo and v_hi (excluding endpoints)
        n_levels = 5
        levels = [v_lo + (v_hi - v_lo) * (k + 1) / (n_levels + 1) for k in range(n_levels)]
        ink6 = pal["ink6"]
        # transpose: contour expects matrix[row=y_idx][col=x_idx]
        # input is matrix[t_idx][lat_idx]; we need matrix[lat_idx][t_idx]
        trans = [[matrix[ti][li] for ti in range(n_t)] for li in range(n_lat)]
        for level in levels:
            segs = _contour_segments_matrix(trans, level, times, latitudes)
            for p1, p2 in segs:
                parts.append(
                    f'<line x1="{X(p1[0]):.1f}" y1="{Y(p1[1]):.1f}" '
                    f'x2="{X(p2[0]):.1f}" y2="{Y(p2[1]):.1f}" '
                    f'stroke="{ink6}" stroke-width="0.8" stroke-dasharray="2 2"/>'
                )

    # X axis: time. Detect year-style values (integers in the usual historical
    # range) and bypass the thousands-separator in ``_fmt_axis`` by using the
    # categorical draw path with pre-formatted labels.
    t_ticks, _t_min_a, _t_max_a = rigor.nice_axis(t_min, t_max, 7)
    t_span = t_max - t_min
    visible_t = [v for v in t_ticks if t_min <= v <= t_max]

    def _fmt_t(v):
        # Year-like: integer in a plausible calendar range *and* the axis
        # span is at least ~a decade — don't apply the thousands separator.
        if abs(v) < 10000 and abs(v - round(v)) < 1e-9 and t_span > 10:
            return str(round(v))
        return _fmt_axis(v, t_span if t_span > 0 else abs(v) or 1)

    x_tick_positions = [rigor._lin(v, t_min, t_max, plot_x_left, plot_x_right) for v in visible_t]
    x_tick_labels = [_fmt_t(v) for v in visible_t]
    parts.append(
        rigor.draw_x_axis(
            plot_x_left,
            plot_x_right,
            plot_y_bot,
            x_tick_positions,
            t_min,
            t_max,
            unit=time_unit,
            pal=pal,
            fs_tick=fs["ytick"],
            fs_title=fs["yaxis"],
            title=tr("Time"),
            categories=x_tick_labels,
        )
    )

    # Y axis: latitude. Prefer standard graticule 90/60/30/0.
    pref_ticks = [-90, -60, -30, 0, 30, 60, 90]
    use_ticks = [t for t in pref_ticks if lat_min <= t <= lat_max]
    if len(use_ticks) < 3:
        use_ticks, _, _ = rigor.nice_axis(lat_min, lat_max, 6)
    # Fold the lat_unit into the axis title so it reads "Latitude (°)" instead
    # of leaving an orphan ``°`` chip hovering above the plot.
    y_title_full = tr("Latitude ({unit})", unit=lat_unit) if lat_unit else tr("Latitude")
    parts.append(
        rigor.draw_y_axis(
            plot_x_left,
            plot_y_top,
            plot_y_bot,
            use_ticks,
            lat_min,
            lat_max,
            unit="",
            pal=pal,
            fs_tick=fs["ytick"],
            fs_title=fs["yaxis"],
            title=y_title_full,
            side="left",
        )
    )

    parts.append(
        f'<rect x="{plot_x_left:.1f}" y="{plot_y_top:.1f}" '
        f'width="{plot_x_right - plot_x_left:.1f}" height="{plot_y_bot - plot_y_top:.1f}" '
        f'fill="none" stroke="{pal["ink"]}" stroke-width="1.2"/>'
    )

    if _sub_bbox is not None and _mm_mode == "with_zonal_mean":
        _sx_l, _sx_r, _sy_t, _sy_b = rigor.bbox_to_edges(_sub_bbox)
        # Compute per-latitude time mean (skip NaN / None entries).
        zonal = []
        for j in range(n_lat):
            vals = []
            for i in range(n_t):
                v = matrix[i][j]
                if v is None:
                    continue
                fv = float(v)
                if isinstance(fv, float) and not math.isfinite(fv):
                    continue
                vals.append(fv)
            zonal.append(sum(vals) / len(vals) if vals else 0.0)

        z_lo = min(zonal) if zonal else 0.0
        z_hi = max(zonal) if zonal else 1.0
        if z_lo == z_hi:
            z_hi = z_lo + 1.0
        # Keep a symmetric range if we are plotting an anomaly (consistent with
        # the main panel's semantics).
        if anomaly:
            z_abs = max(abs(z_lo), abs(z_hi))
            z_lo, z_hi = -z_abs, z_abs
        _z_ticks, _z_min_a, _z_max_a = rigor.nice_axis(z_lo, z_hi, 3)

        # Reserve a little vertical room for the sub x-axis labels/title and a little top gutter so the sub tracks the
        # main plot box inset.
        _sub_top_pad = 0.0
        _sub_bot_pad = 30.0
        _sub_lr_pad = 14.0
        ax_x0 = _sx_l + _sub_lr_pad
        ax_x1 = _sx_r - _sub_lr_pad

        def ZX(v):
            return rigor._lin(v, _z_min_a, _z_max_a, ax_x0, ax_x1)

        def ZY(lat):
            # Mirror the main plot's latitude mapping so each row shares its y.
            return rigor._lin(lat, lat_min, lat_max, plot_y_bot, plot_y_top)

        sub_fs_tick = max(10.0, fs["ytick"] * 0.85)
        sub_fs_title = max(10.0, fs["yaxis"] * 0.85)

        # Faint sub-panel grid (vertical, aligned on x ticks).
        parts.append(
            rigor.draw_grid(
                ax_x0,
                ax_x1,
                plot_y_top,
                plot_y_bot,
                pal=pal,
                x_ticks=_z_ticks,
                x_min=_z_min_a,
                x_max=_z_max_a,
                orient="vertical",
            )
        )
        # Zero reference line if the range straddles zero.
        if _z_min_a <= 0 <= _z_max_a:
            _zx0 = ZX(0.0)
            parts.append(
                f'<line x1="{_zx0:.1f}" y1="{plot_y_top:.1f}" '
                f'x2="{_zx0:.1f}" y2="{plot_y_bot:.1f}" '
                f'stroke="{pal["ink4"]}" stroke-width="1" stroke-dasharray="3 3"/>'
            )

        # Horizontal bars: one per latitude row, length ∝ zonal[j], centered on the latitude pixel position.
        _bar_fill = f"{_rgb_prefix(pal['accent'])}0.45)"
        _bar_stroke = f"{_rgb_prefix(pal['accent'])}0.85)"
        # Bar thickness scales with available vertical space / n_lat.
        bar_h = max(2.0, min(16.0, (plot_y_bot - plot_y_top) / max(1, n_lat) * 0.75))
        _x_zero = ZX(0.0) if _z_min_a <= 0 <= _z_max_a else ZX(_z_min_a)

        def _clamp(v, lo, hi):
            return max(lo, min(hi, v))

        for j in range(n_lat):
            cy = ZY(latitudes[j])
            # Clamp the mapped end position to the sub-panel's x range so
            # out-of-domain bars (defensive) are visually cropped at the frame.
            end_x = _clamp(ZX(zonal[j]), ax_x0, ax_x1)
            x_zero_c = _clamp(_x_zero, ax_x0, ax_x1)
            x0b = min(x_zero_c, end_x)
            w_b = abs(end_x - x_zero_c)
            # Also clamp the vertical extent so a bar near the top/bottom of
            # the latitude range never pokes outside the sub panel's y range.
            y_top = _clamp(cy - bar_h / 2, plot_y_top, plot_y_bot)
            y_bot = _clamp(cy + bar_h / 2, plot_y_top, plot_y_bot)
            h_b = max(0.0, y_bot - y_top)
            # And ensure the bar width stays within the sub x range even
            # if upstream x0 drifted via floating-point.
            if x0b + w_b > ax_x1:
                w_b = max(0.0, ax_x1 - x0b)
            if x0b < ax_x0:
                w_b -= ax_x0 - x0b
                x0b = ax_x0
            parts.append(
                f'<rect x="{x0b:.2f}" y="{y_top:.2f}" '
                f'width="{w_b:.2f}" height="{h_b:.2f}" '
                f'fill="{_bar_fill}" stroke="{_bar_stroke}" stroke-width="0.6"/>'
            )

        # Sub X axis (time-mean values). Main-plot Y tick labels remain visible
        # on the main plot's left axis; the sub does not re-draw them.
        parts.append(
            rigor.draw_x_axis(
                ax_x0,
                ax_x1,
                plot_y_bot,
                _z_ticks,
                _z_min_a,
                _z_max_a,
                unit=value_unit,
                pal=pal,
                fs_tick=sub_fs_tick,
                fs_title=sub_fs_title,
                title=tr("Zonal mean"),
                show_tick_labels=True,
            )
        )
        parts.append(
            f'<text x="{ax_x0:.1f}" y="{plot_y_top - 8:.1f}" '
            f'font-size="{sub_fs_title:.1f}" fill="{pal["ink"]}" '
            f'font-weight="600">{_xesc(tr("Time mean"))}</text>'
        )
        # Bounding box around the sub panel for visual containment.
        parts.append(
            f'<rect x="{ax_x0:.1f}" y="{plot_y_top:.1f}" '
            f'width="{(ax_x1 - ax_x0):.1f}" height="{(plot_y_bot - plot_y_top):.1f}" '
            f'fill="none" stroke="{pal["ink"]}" stroke-width="1.0" opacity="0.6"/>'
        )

    if _sub_bbox is not None:
        # When the zonal-mean sub panel is active, the colorbar sits to the right of the sub panel (not the main plot)
        # so both share the right gutter and the sub bars line up vertically with the main plot's lat axis.
        _sx_l, _sx_r, _sy_t, _sy_b = rigor.bbox_to_edges(_sub_bbox)
        cbar_x = _sx_r + 30
    else:
        cbar_x = plot_x_right + 30
    cbar_y = plot_y_top
    cbar_h = plot_y_bot - plot_y_top
    parts.append(
        rigor.draw_colorbar(
            cbar_x,
            cbar_y,
            cbar_w,
            cbar_h,
            v_lo,
            v_hi,
            pal=pal,
            unit=value_unit,
            log=log_color,
            orient="vertical",
            stops=stops,
            fs_tick=fs["ytick"],
            title=value_title,
        )
    )

    parts.append(rigor.draw_footer(note, source, pal, fs, plot_x_left, plot_x_right, H - 32))

    return rigor.wrap_svg(parts, W, H, body_font)
