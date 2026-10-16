"""Academic chart: depth/altitude profile (oceanographic / atmospheric)."""

from __future__ import annotations

from .._common import (
    _dist_font_sizes,
    _estimate_label_width_px,
    _fmt_axis,
    _pick_series_colors,
    _resolve_font,
    _resolve_palette,
    _rgb_prefix,
    _variant_is_classic,
    _xesc,
)
from . import _academic_rigor as rigor
from ._shared import tr


# Multi-mode whitelist.
#   with_gradient : d(var)/dz derivative curve to the right of the main panel,
#     sharing the Y (depth) axis. Template = left_right_2to1.
#     Trigger: single series, n_pts >= 30.
#     Validator: depths strictly monotonic (sorted shallow→deep or deep→shallow).
def _validate_depth_gradient(s):
    series = s.get("series") or []
    if len(series) != 1:
        return (False, "need exactly 1 series")
    depths = series[0].get("depths") or []
    if len(depths) < 30:
        return (False, "need >= 30 points")
    inc = all(depths[i] <= depths[i + 1] for i in range(len(depths) - 1))
    dec = all(depths[i] >= depths[i + 1] for i in range(len(depths) - 1))
    if not (inc or dec):
        return (False, "depths must be monotonic")
    return (True, "")


_DEPTH_PROFILE_MULTI_WHITELIST = {
    "with_gradient": (
        "left_right_2to1",
        lambda s: len(s.get("series") or []) == 1 and len((s.get("series") or [{}])[0].get("depths") or []) >= 30,
        lambda s: _validate_depth_gradient(s),
    ),
}


def _series_color(pal, i, n_series: int | None = None):
    """Pick a stable per-series color."""
    series_colors = pal.get("series")
    if series_colors and i < len(series_colors):
        return series_colors[i]
    if n_series and n_series > 0:
        cols = _pick_series_colors(pal, n_series)
        return cols[i % len(cols)]
    palette_order = [
        pal.get("accent", "rgba(163,88,50,1)"),
        pal.get("secondary", "rgba(28,28,26,0.6)"),
        pal.get("ink", "rgba(28,28,26,1)"),
    ]
    return palette_order[i % len(palette_order)]


def make_depth_profile(
    series,
    *,
    depth_unit: str = "m",
    value_unit: str = "",
    value_title: str | None = None,
    depth_title: str = "Depth",
    title: str | None = None,
    subtitle: str | None = None,
    figure_label: str | None = None,
    note: str | None = None,
    source: str | None = None,
    depth_inverted: bool = True,
    reference_levels=None,
    annotate_water_layers: bool = True,
    width: float | None = None,
    height: float = 1200,
    font_family: str | None = None,
    palette=None,
    variant: str | None = None,
    multi_mode: str = "auto",
) -> str:
    """Depth / altitude profile. Returns a complete ``<svg>...</svg>`` string.

    Each entry in ``series`` is a dict with:
        ``name``: str
        ``depths``: list[float] (shallow -> deep)
        ``values``: list[float] (same length)
        ``ci_up`` / ``ci_dn``: list[float] optional
        ``err``: list[float] symmetric alternative

    When ``annotate_water_layers`` is True (default), and the first series has
    enough points, the plot auto-detects the thermocline (depth range of the
    maximum ``|dT/dz|``) and labels three oceanographic zones:

      * Mixed layer   (above the thermocline top)
      * Thermocline   (shaded band between d_top and d_bot of max gradient)
      * Deep water    (below the thermocline bottom)

    Users can override by passing explicit ``reference_levels=[(depth, label), …]``;
    the auto-detection runs only if ``reference_levels`` is None.
    """
    _variant_is_classic("depth_profile", variant)
    if palette is None:
        palette = "archive_ink"
    pal = _resolve_palette(palette)
    body_font, heading_font = _resolve_font(font_family)
    # If a sub-panel multi_mode is in play and the caller used the default portrait width, widen the canvas so the
    # left_right_2to1 template fits the 900×480 minimum.
    if width is None:
        width = 1200.0 if multi_mode in ("auto", "with_gradient") else 820.0
    W, H = float(width), float(height)

    series = [s for s in (series or []) if s.get("depths") and s.get("values")]
    n_series = len(series)
    fs = _dist_font_sizes(W, H, max(4, n_series or 4))

    if not series:
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}">'
            f'<text x="{W / 2}" y="{H / 2}" text-anchor="middle" font-size="16" '
            f'fill="{pal["ink6"]}">{_xesc(tr("No data"))}</text></svg>'
        )

    all_depths = []
    all_vals = []
    for s in series:
        d = s["depths"]
        v = s["values"]
        all_depths.extend(d)
        all_vals.extend(v)
        if s.get("ci_up"):
            all_vals.extend(s["ci_up"])
        if s.get("ci_dn"):
            all_vals.extend(s["ci_dn"])
        if s.get("err"):
            for vv, e in zip(v, s["err"]):
                all_vals.append(vv - e)
                all_vals.append(vv + e)

    v_ticks, v_min, v_max = rigor.nice_axis(min(all_vals), max(all_vals), 5)
    d_ticks, d_min, d_max = rigor.nice_axis(min(all_depths), max(all_depths), 6)

    margin_top = 130
    margin_bot = 140
    margin_left = 110
    margin_right = 60
    if H < 700:
        # Short embed canvases size margins from the text they actually carry.
        heads = [
            f
            for v, f in ((title, fs["title"] + 8), (subtitle, fs["subtitle"] + 6), (figure_label, fs["figure"] + 4))
            if v
        ]
        margin_top = 24 + sum(heads) + fs["ytick"] * 0.5
        margin_bot = (
            fs["ytick"]
            + 20
            + (fs["yaxis"] * 1.6 if value_title or value_unit else 0)
            + (max(13.0, fs["foot"]) + 16 if note or source else 0)
        )
        margin_left = (
            64
            + fs["yaxis"]
            + max(_estimate_label_width_px(f"{v:g}", fs["ytick"], font_family=body_font) for v in d_ticks)
        )
        margin_right = 28

    plot_x_left = margin_left
    plot_x_right = W - margin_right
    plot_y_top = margin_top
    plot_y_bot = H - margin_bot

    _plot_bbox = rigor.bbox_from_edges(plot_x_left, plot_x_right, plot_y_top, plot_y_bot)
    _signals = {"series": series, "n_pts": len(series[0].get("depths") or []) if series else 0}
    _mm_mode, _mm_template, _mm_reason = rigor.resolve_multi_mode_v2(
        multi_mode,
        _DEPTH_PROFILE_MULTI_WHITELIST,
        _signals,
        _plot_bbox,
    )
    _sub_bbox = None
    if _mm_mode is not None and _mm_template is not None:
        _gutter = 28.0
        if _mm_mode == "with_gradient":
            _ordered = sorted(zip(series[0]["depths"], series[0]["values"]))
            _deriv = rigor.kernel_derivative([p[0] for p in _ordered], [p[1] for p in _ordered])
            _gradient_values = [p[1] for p in _deriv]
            if _gradient_values:
                _ticks, _lo, _hi = rigor.nice_axis(min(_gradient_values), max(_gradient_values), 4)
                _main_w = max(
                    _estimate_label_width_px(_fmt_axis(v, v_max - v_min), fs["ytick"], font_family=body_font)
                    for v in v_ticks
                )
                _sub_w = max(
                    _estimate_label_width_px(
                        _fmt_axis(v, _hi - _lo), max(10.0, fs["ytick"] * 0.88), font_family=body_font
                    )
                    for v in _ticks
                )
                _gutter = max(_gutter, (_main_w + _sub_w) / 2 + 12)
        _rects = rigor.allocate_main_sub(_plot_bbox, _mm_template, gutter_free=_gutter)
        _main_bb = _rects["main"]
        _sub_bbox = _rects["sub"]
        if _mm_template.startswith("left_right"):
            plot_x_right = _main_bb.x1
        else:
            plot_y_bot = _main_bb.y1

    def X(v):
        return rigor._lin(v, v_min, v_max, plot_x_left, plot_x_right)

    def Y(d):
        if depth_inverted:
            # shallow (small d) at top, deep (large d) at bottom
            return rigor._lin(d, d_min, d_max, plot_y_top, plot_y_bot)
        return rigor._lin(d, d_min, d_max, plot_y_bot, plot_y_top)

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
            y_ticks=d_ticks,
            y_min=d_min if not depth_inverted else d_max,
            y_max=d_max if not depth_inverted else d_min,
            x_ticks=v_ticks,
            x_min=v_min,
            x_max=v_max,
            orient="both",
        )
    )

    # Runs only if the user did not supply ``reference_levels`` and ``annotate_water_layers`` is on.
    auto_zones = None
    if annotate_water_layers and reference_levels is None:
        s0 = series[0]
        d_arr = list(s0.get("depths") or [])
        v_arr = list(s0.get("values") or [])
        pairs = sorted(zip(d_arr, v_arr), key=lambda p: p[0])
        d_sorted = [p[0] for p in pairs]
        v_sorted = [p[1] for p in pairs]
        if len(d_sorted) >= 8:
            n = len(d_sorted)
            grad = [0.0] * n
            for i in range(1, n - 1):
                dz = d_sorted[i + 1] - d_sorted[i - 1]
                grad[i] = (v_sorted[i + 1] - v_sorted[i - 1]) / dz if dz else 0.0
            grad[0] = grad[1]
            grad[-1] = grad[-2]
            abs_g = [abs(g) for g in grad]
            g_max = max(abs_g) if abs_g else 0.0
            if g_max > 1e-9:
                thresh = 0.60 * g_max
                i_peak = max(range(n), key=lambda i: abs_g[i])
                # expand window around peak while |grad| >= threshold
                i_top = i_peak
                while i_top > 0 and abs_g[i_top - 1] >= thresh:
                    i_top -= 1
                i_bot = i_peak
                while i_bot < n - 1 and abs_g[i_bot + 1] >= thresh:
                    i_bot += 1
                d_top = d_sorted[i_top]
                d_bot = d_sorted[i_bot]
                d_peak = d_sorted[i_peak]
                # Need a non-degenerate band and some surface/deep room on both
                # sides, else annotation adds noise rather than clarity.
                span = d_max - d_min
                if d_bot - d_top > span * 0.05 and d_top - d_min > span * 0.03 and d_max - d_bot > span * 0.03:
                    auto_zones = {"d_top": d_top, "d_bot": d_bot, "d_peak": d_peak}

    # Draw auto zones (shaded band + dashed edges + right-edge labels + arrow).
    if auto_zones is not None:
        d_top = auto_zones["d_top"]
        d_bot = auto_zones["d_bot"]
        d_peak = auto_zones["d_peak"]
        y_top_px = Y(d_top)
        y_bot_px = Y(d_bot)
        y_peak_px = Y(d_peak)
        band_fill = f"{_rgb_prefix(pal['accent'])}0.10)"
        parts.append(
            f'<rect x="{plot_x_left:.1f}" y="{min(y_top_px, y_bot_px):.1f}" '
            f'width="{plot_x_right - plot_x_left:.1f}" '
            f'height="{abs(y_bot_px - y_top_px):.1f}" '
            f'fill="{band_fill}" stroke="none"/>'
        )
        for yv in (y_top_px, y_bot_px):
            parts.append(
                f'<line x1="{plot_x_left:.1f}" y1="{yv:.1f}" '
                f'x2="{plot_x_right:.1f}" y2="{yv:.1f}" '
                f'stroke="{pal["ink6"]}" stroke-width="1.0" stroke-dasharray="6 4"/>'
            )
        # Zone labels on the RIGHT edge (small italic chip)
        lab_fs = max(13.0, fs["label"])
        ink = pal["ink"]
        bg = pal.get("bg", "rgba(255,255,255,0.9)")
        bg_halo = f"{_rgb_prefix(bg)}0.9)" if bg else "rgba(255,255,255,0.9)"

        def _zone_label(y_center, text, weight="600"):
            est_w = _estimate_label_width_px(text, lab_fs, font_family=body_font) + 10
            x_right = plot_x_right - 6
            x_left_box = x_right - est_w
            parts.append(
                f'<rect x="{x_left_box:.1f}" '
                f'y="{y_center - lab_fs * 0.85:.1f}" '
                f'width="{est_w:.1f}" height="{lab_fs * 1.4:.1f}" '
                f'fill="{bg_halo}" stroke="none" rx="2"/>'
            )
            parts.append(
                f'<text x="{x_right - 4:.1f}" y="{y_center + lab_fs * 0.32:.1f}" '
                f'font-size="{lab_fs:.1f}" fill="{ink}" '
                f'text-anchor="end" font-weight="{weight}">{_xesc(text)}</text>'
            )

        # Mixed layer: midpoint between plot top and thermocline top
        mixed_mid_y = (plot_y_top + min(y_top_px, y_bot_px)) * 0.5
        if abs(mixed_mid_y - plot_y_top) > lab_fs * 1.5:
            _zone_label(mixed_mid_y, tr("Mixed layer"))
        therm_mid_y = (y_top_px + y_bot_px) * 0.5
        _zone_label(
            therm_mid_y,
            tr("Thermocline ({top}–{bottom} {unit})", top=f"{d_top:.0f}", bottom=f"{d_bot:.0f}", unit=depth_unit),
            weight="700",
        )
        # Deep water: midpoint between thermocline bottom and plot bottom
        deep_mid_y = (max(y_top_px, y_bot_px) + plot_y_bot) * 0.5
        if abs(deep_mid_y - plot_y_bot) > lab_fs * 1.5:
            _zone_label(deep_mid_y, tr("Deep water"))

        # Arrow pointing to steepest-gradient depth (left side of plot so it doesn't collide with the right-edge zone
        # labels). Interpolate value at d_peak on the first series.
        s0 = series[0]
        d_arr = list(s0.get("depths") or [])
        v_arr = list(s0.get("values") or [])
        pairs = sorted(zip(d_arr, v_arr), key=lambda p: p[0])
        d_sorted = [p[0] for p in pairs]
        v_sorted = [p[1] for p in pairs]
        v_peak = v_sorted[0]
        for i in range(len(d_sorted) - 1):
            if d_sorted[i] <= d_peak <= d_sorted[i + 1]:
                t = (
                    ((d_peak - d_sorted[i]) / (d_sorted[i + 1] - d_sorted[i]))
                    if d_sorted[i + 1] != d_sorted[i]
                    else 0.0
                )
                v_peak = v_sorted[i] + t * (v_sorted[i + 1] - v_sorted[i])
                break
        ax_x = X(v_peak)
        ax_y = y_peak_px
        # arrow origin: 90px to the left (inside plot) with text "steepest ∂/∂z"
        ar_x1 = max(plot_x_left + 20, ax_x - 110)
        parts.append(
            f'<line x1="{ar_x1:.1f}" y1="{ax_y:.1f}" x2="{ax_x - 6:.1f}" y2="{ax_y:.1f}" '
            f'stroke="{pal["accent"]}" stroke-width="1.6"/>'
        )
        parts.append(
            f'<polygon points="{ax_x:.1f},{ax_y:.1f} {ax_x - 8:.1f},{ax_y - 4:.1f} '
            f'{ax_x - 8:.1f},{ax_y + 4:.1f}" fill="{pal["accent"]}" stroke="none"/>'
        )
        parts.append(
            f'<text x="{ar_x1 - 4:.1f}" y="{ax_y - 5:.1f}" '
            f'font-size="{lab_fs:.1f}" fill="{ink}" font-weight="600" '
            f'text-anchor="end" font-style="italic">steepest ∂/∂z</text>'
        )

    if reference_levels:
        for depth_val, rl_label in reference_levels:
            if depth_val < d_min or depth_val > d_max:
                continue
            y_r = Y(depth_val)
            parts.append(
                rigor.draw_reference_line(
                    y_r,
                    plot_x_left,
                    plot_x_right,
                    pal=pal,
                    orient="horizontal",
                    dash="5 4",
                    label=rl_label,
                    label_fs=fs["label"],
                )
            )

    for i, s in enumerate(series):
        depths = s["depths"]
        values = s["values"]
        ci_up = s.get("ci_up")
        ci_dn = s.get("ci_dn")
        err = s.get("err")
        if ci_up is None and err is not None:
            ci_up = [v + e for v, e in zip(values, err)]
            ci_dn = [v - e for v, e in zip(values, err)]
        if ci_up is not None and ci_dn is not None:
            c = _series_color(pal, i, n_series)
            fill = f"{_rgb_prefix(c)}0.18)"
            poly = []
            for d, u in zip(depths, ci_up):
                poly.append(f"{X(u):.1f},{Y(d):.1f}")
            for d, lo in zip(reversed(depths), reversed(ci_dn)):
                poly.append(f"{X(lo):.1f},{Y(d):.1f}")
            parts.append(f'<polygon points="{" ".join(poly)}" fill="{fill}" stroke="none"/>')

    for i, s in enumerate(series):
        depths = s["depths"]
        values = s["values"]
        c = _series_color(pal, i, n_series)
        d_path = " ".join(
            f"{'M' if k == 0 else 'L'} {X(v):.1f} {Y(d):.1f}" for k, (d, v) in enumerate(zip(depths, values))
        )
        parts.append(f'<path d="{d_path}" fill="none" stroke="{c}" stroke-width="2"/>')
        # markers at sample points for small series
        if len(depths) <= 40:
            for d, v in zip(depths, values):
                parts.append(f'<circle cx="{X(v):.1f}" cy="{Y(d):.1f}" r="2.4" fill="{c}" stroke="none"/>')

    parts.append(
        rigor.draw_x_axis(
            plot_x_left,
            plot_x_right,
            plot_y_bot,
            v_ticks,
            v_min,
            v_max,
            unit=value_unit,
            pal=pal,
            fs_tick=fs["ytick"],
            fs_title=fs["yaxis"],
            title=value_title,
        )
    )
    # Y axis (depth): draw_y_axis maps v_min at bottom. For inverted depth we
    # draw a custom axis so ticks render correctly (0 at top, d_max at bottom).
    parts.append(
        _draw_depth_axis(
            plot_x_left,
            plot_y_top,
            plot_y_bot,
            d_ticks,
            d_min,
            d_max,
            inverted=depth_inverted,
            unit=depth_unit,
            pal=pal,
            fs_tick=fs["ytick"],
            fs_title=fs["yaxis"],
            title=depth_title,
        )
    )

    # legend if multiple series — placed in the bottom-right corner so it
    # clears the typical ocean-salinity curve (increases with depth, i.e. the
    # top-right area is occupied by the data).
    if n_series > 1:
        lg_fs = max(13.0, fs["label"])
        line_h = lg_fs * 1.5
        max_w = (
            max(
                _estimate_label_width_px(s.get("name", tr("Series {i}", i=i)), lg_fs, font_family=body_font)
                for i, s in enumerate(series)
            )
            + 36
        )
        lg_box_h = line_h * n_series + 8
        # Pick the plot corner whose legend box covers the fewest curve samples (densely interpolated).
        samples = []
        for s in series:
            pts = sorted(zip(s["depths"], s["values"]))
            for (d0, v0), (d1, v1) in zip(pts, pts[1:]):
                for k in range(9):
                    t = k / 8
                    samples.append((X(v0 + (v1 - v0) * t), Y(d0 + (d1 - d0) * t)))
            samples.extend((X(v), Y(d)) for d, v in pts)
        for depth_val, _ in reference_levels or []:
            if d_min <= depth_val <= d_max:  # reference labels sit at the right end of their line
                samples.extend((plot_x_right - k * 12, Y(depth_val)) for k in range(12))
        corners = [
            (plot_x_right - 10, plot_y_bot - lg_box_h - 10),
            (plot_x_right - 10, plot_y_top + 10),
            (plot_x_left + max_w + 10, plot_y_bot - lg_box_h - 10),
            (plot_x_left + max_w + 10, plot_y_top + 10),
        ]

        def covered(corner):
            x1, y0 = corner
            return sum(1 for px, py in samples if x1 - max_w - 6 <= px <= x1 + 6 and y0 - 6 <= py <= y0 + lg_box_h + 6)

        lg_x, lg_y = min(corners, key=covered)
        parts.append(
            f'<rect x="{lg_x - max_w:.1f}" y="{lg_y:.1f}" '
            f'width="{max_w:.1f}" height="{lg_box_h:.1f}" '
            f'fill="{pal.get("bg", "rgba(255,255,255,0.85)")}" '
            f'stroke="{pal["ink1"]}" stroke-width="0.8"/>'
        )
        for i, s in enumerate(series):
            name = s.get("name", tr("Series {i}", i=i + 1))
            c = _series_color(pal, i, n_series)
            y_line = lg_y + 10 + i * line_h + lg_fs * 0.6
            parts.append(
                f'<line x1="{lg_x - max_w + 8:.1f}" y1="{y_line - lg_fs * 0.3:.1f}" '
                f'x2="{lg_x - max_w + 26:.1f}" y2="{y_line - lg_fs * 0.3:.1f}" '
                f'stroke="{c}" stroke-width="2.4"/>'
            )
            parts.append(
                f'<text x="{lg_x - max_w + 32:.1f}" y="{y_line:.1f}" '
                f'font-size="{lg_fs}" fill="{pal["ink"]}">{_xesc(name)}</text>'
            )

    if _sub_bbox is not None and _mm_mode == "with_gradient":
        sx_left, sx_right, sy_top, sy_bot = rigor.bbox_to_edges(_sub_bbox)
        sub_fs_tick = max(10.0, fs["ytick"] * 0.88)
        sub_fs_title = max(10.0, fs["yaxis"] * 0.88)

        s0 = series[0]
        depths0 = list(s0["depths"])
        values0 = list(s0["values"])
        # Normalize so depths are increasing for derivative; we take d(var)/dz
        pairs = sorted(zip(depths0, values0), key=lambda p: p[0])
        d_sorted = [p[0] for p in pairs]
        v_sorted = [p[1] for p in pairs]
        deriv_pts = rigor.kernel_derivative(d_sorted, v_sorted)  # list[(z, dy/dz)]

        if deriv_pts:
            dy_vals = [dy for _, dy in deriv_pts]
            dmin, dmax = min(dy_vals), max(dy_vals)
            if dmin == dmax:
                dmin -= 1.0
                dmax += 1.0
            sx_ticks, sx_dmin, sx_dmax = rigor.nice_axis(dmin, dmax, 4)

            def SX(v):
                return rigor._lin(v, sx_dmin, sx_dmax, sx_left, sx_right)

            def SY(d):
                # Share Y with main (depth), honoring inversion
                if depth_inverted:
                    return rigor._lin(d, d_min, d_max, sy_top, sy_bot)
                return rigor._lin(d, d_min, d_max, sy_bot, sy_top)

            # Grid in sub panel (vertical grid for the shared depth)
            parts.append(
                rigor.draw_grid(
                    sx_left,
                    sx_right,
                    sy_top,
                    sy_bot,
                    pal=pal,
                    y_ticks=d_ticks,
                    y_min=d_min if not depth_inverted else d_max,
                    y_max=d_max if not depth_inverted else d_min,
                    orient="horizontal",
                )
            )
            if sx_dmin <= 0.0 <= sx_dmax:
                parts.append(
                    f'<line x1="{SX(0.0):.1f}" y1="{sy_top:.1f}" '
                    f'x2="{SX(0.0):.1f}" y2="{sy_bot:.1f}" '
                    f'stroke="{pal["ink6"]}" stroke-width="1" stroke-dasharray="4 3"/>'
                )

            dcol = _series_color(pal, 0)
            d_path = " ".join(
                f"{'M' if k == 0 else 'L'} {SX(dy):.1f} {SY(z):.1f}" for k, (z, dy) in enumerate(deriv_pts)
            )
            parts.append(f'<path d="{d_path}" fill="none" stroke="{dcol}" stroke-width="1.8"/>')
            parts.append(
                rigor.draw_x_axis(
                    sx_left,
                    sx_right,
                    sy_bot,
                    sx_ticks,
                    sx_dmin,
                    sx_dmax,
                    pal=pal,
                    fs_tick=sub_fs_tick,
                    fs_title=sub_fs_title,
                    title=tr("d/dz"),
                    show_tick_labels=True,
                )
            )
            # Sub Y axis (depth) — hide tick labels to avoid duplication with main
            parts.append(
                _draw_depth_axis(
                    sx_left,
                    sy_top,
                    sy_bot,
                    d_ticks,
                    d_min,
                    d_max,
                    inverted=depth_inverted,
                    unit="",
                    pal=pal,
                    fs_tick=sub_fs_tick,
                    fs_title=sub_fs_title,
                    title=None,
                )
            )
            parts.append(
                f'<text x="{sx_left:.1f}" y="{sy_top - 8:.1f}" '
                f'font-size="{sub_fs_title:.1f}" fill="{pal["ink"]}" '
                f'font-weight="600">{_xesc(tr("Gradient d/dz"))}</text>'
            )

    parts.append(rigor.draw_footer(note, source, pal, fs, plot_x_left, plot_x_right, H - 32))

    return rigor.wrap_svg(parts, W, H, body_font)


def _draw_depth_axis(x, y_top, y_bot, ticks, d_min, d_max, *, inverted, unit, pal, fs_tick, fs_title, title):
    """Vertical axis with optional inversion."""
    ink = pal.get("ink", "rgba(28,28,26,1)")
    parts = [
        f'<line x1="{x:.1f}" y1="{y_top:.1f}" x2="{x:.1f}" y2="{y_bot:.1f}" stroke="{ink}" stroke-width="1.2" data-role="y-axis"/>'
    ]
    span = max(d_max - d_min, 1e-9)
    from .._common import _fmt_axis as _fa

    for v in ticks:
        if v < d_min - 1e-9 or v > d_max + 1e-9:
            continue
        if inverted:
            y = rigor._lin(v, d_min, d_max, y_top, y_bot)
        else:
            y = rigor._lin(v, d_min, d_max, y_bot, y_top)
        parts.append(f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x - 5:.1f}" y2="{y:.1f}" stroke="{ink}" stroke-width="1"/>')
        parts.append(
            f'<text x="{x - 7:.1f}" y="{y + fs_tick * 0.35:.1f}" '
            f'font-size="{fs_tick}" text-anchor="end" fill="{ink}">'
            f"{_xesc(_fa(v, span))}</text>"
        )
    if unit:
        title = f"{title} ({unit})" if title else unit
    if title:
        fs_t = fs_title or max(13.0, fs_tick * 1.05)
        xt = x - fs_tick * 3.2
        yt = (y_top + y_bot) * 0.5
        parts.append(
            f'<text x="{xt:.1f}" y="{yt:.1f}" font-size="{fs_t}" fill="{ink}" '
            f'text-anchor="middle" transform="rotate(-90 {xt:.1f} {yt:.1f})" '
            f'font-weight="600">{_xesc(title)}</text>'
        )
    return "".join(parts)
