"""Academic chart: engineering stress–strain curve with elastic / plastic shaded
regions, yield / ultimate / fracture markers, and derived mechanical properties
"""

from __future__ import annotations

from .._common import (
    _dist_font_sizes,
    _estimate_label_width_px,
    _resolve_font,
    _resolve_palette,
    _rgba_with_alpha,
    _variant_is_classic,
    _xesc,
)
from . import _academic_rigor as rigor
from ._shared import tr


# Multi-mode whitelist (mode → (template, trigger, validator))
#   with_tangent_modulus : tangent modulus (dσ/dε) sub-panel sharing x axis
def _validate_tangent(signals):
    xs = signals.get("xs") or []
    if len(xs) < 4:
        return (False, "need >= 4 points (sparse digitised curves are interpolated)")
    # Strain should be monotonically non-decreasing (allow duplicates).
    for i in range(len(xs) - 1):
        if xs[i + 1] < xs[i] - 1e-12:
            return (False, "strain must be monotonically increasing")
    return (True, "")


_STRESS_STRAIN_MULTI_WHITELIST = {
    "with_tangent_modulus": (
        "top_bottom_3to1",
        lambda s: len(s.get("xs") or []) >= 20,  # auto only for dense curves; explicit mode works from 4
        lambda s: _validate_tangent(s),
    ),
}


def _youngs_modulus(curve, elastic_region):
    """Compute Young's modulus from the slope of the curve inside ``elastic_region``."""
    if not curve or not elastic_region:
        return None
    s_lo, s_hi = elastic_region
    inside = [(x, y) for x, y in curve if s_lo <= x <= s_hi]
    if len(inside) < 2:
        return None
    x1, y1 = inside[0]
    x2, y2 = inside[-1]
    if x2 == x1:
        return None
    return (y2 - y1) / (x2 - x1)


def _auto_detect_features(curve):
    """Infer elastic region, yield / ultimate / fracture points from a raw stress–strain curve."""
    if not curve or len(curve) < 5:
        return {"elastic_region": None, "yield_point": None, "ultimate_point": None, "fracture_point": None}

    xs = [p[0] for p in curve]
    ys = [p[1] for p in curve]
    n = len(curve)

    # the origin, where the curve is cleanly linear.
    def _slope(i):
        if xs[i] <= xs[0]:
            return 0.0
        return (ys[i] - ys[0]) / (xs[i] - xs[0])

    # The first measured interval precedes any detected plastic response.
    # Averaging several secants on sparse input can include plastic samples.
    first = next((i for i in range(1, n) if xs[i] > xs[0]), None)
    init_slope = _slope(first) if first is not None else 0.0
    if init_slope <= 0:
        return {"elastic_region": None, "yield_point": None, "ultimate_point": None, "fracture_point": None}

    # init_slope OR consecutive secant slope < 70% of init_slope — this is
    # the end of the elastic regime (yield onset).
    yield_i = None
    for i in range(first + 1, n):
        sec = _slope(i)
        if xs[i] <= xs[i - 1]:
            continue
        local = (ys[i] - ys[i - 1]) / (xs[i] - xs[i - 1])
        if sec < 0.85 * init_slope or local < 0.70 * init_slope:
            yield_i = i - 1
            break

    # yield within the data — pure elastic sample).
    if yield_i is None:
        elastic_region = (xs[0], xs[-1])
        yield_point = None
    else:
        elastic_region = (xs[0], xs[yield_i])
        yield_point = (xs[yield_i], ys[yield_i])

    i_uts = max(range(n), key=lambda i: ys[i])
    ultimate_point = (xs[i_uts], ys[i_uts])

    # chart meaningful for curves that are elastic-only)
    if i_uts < n - 1:
        fracture_point = (xs[-1], ys[-1])
    else:
        fracture_point = None

    # Suppress yield==UTS to avoid double-marker visual clash
    if yield_point is not None and ultimate_point is not None and abs(yield_point[0] - ultimate_point[0]) < 1e-9:
        yield_point = None

    return {
        "elastic_region": elastic_region,
        "yield_point": yield_point,
        "ultimate_point": ultimate_point,
        "fracture_point": fracture_point,
    }


def _plot_marker(cx, cy, kind, color):
    """Shape markers for yield (square), ultimate (triangle), fracture (×)."""
    if kind == "yield":
        s = 8
        return (
            f'<rect x="{cx - s:.1f}" y="{cy - s:.1f}" width="{s * 2:.1f}" '
            f'height="{s * 2:.1f}" fill="{color}" stroke="rgba(28,28,26,1)" '
            f'stroke-width="1.2"/>'
        )
    if kind == "ultimate":
        s = 10
        pts = [
            (cx, cy - s),
            (cx - s, cy + s * 0.7),
            (cx + s, cy + s * 0.7),
        ]
        poly = " ".join(f"{p[0]:.1f},{p[1]:.1f}" for p in pts)
        return f'<polygon points="{poly}" fill="{color}" stroke="rgba(28,28,26,1)" stroke-width="1.2"/>'
    s = 8
    return (
        f'<line x1="{cx - s:.1f}" y1="{cy - s:.1f}" '
        f'x2="{cx + s:.1f}" y2="{cy + s:.1f}" '
        f'stroke="{color}" stroke-width="2.4"/>'
        f'<line x1="{cx - s:.1f}" y1="{cy + s:.1f}" '
        f'x2="{cx + s:.1f}" y2="{cy - s:.1f}" '
        f'stroke="{color}" stroke-width="2.4"/>'
    )


def _pchip_dense(xs, ys, n=80):
    """Shape-preserving (monotone cubic) resample of sparse digitised points → (xs, ys, slopes)."""
    pts = sorted(dict(zip(xs, ys)).items())
    X = [p[0] for p in pts]
    Y = [p[1] for p in pts]
    m = len(X)
    if m < 2:
        return X, Y, [0.0] * m
    h = [X[i + 1] - X[i] for i in range(m - 1)]
    delta = [(Y[i + 1] - Y[i]) / h[i] for i in range(m - 1)]
    d = [0.0] * m
    d[0], d[-1] = delta[0], delta[-1]
    for i in range(1, m - 1):
        if delta[i - 1] * delta[i] > 0:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            d[i] = (w1 + w2) / (w1 / delta[i - 1] + w2 / delta[i])
    out_x, out_y, out_d = [], [], []
    for k in range(n + 1):
        x = X[0] + (X[-1] - X[0]) * k / n
        i = min(m - 2, max(0, next((j for j in range(m - 1) if x <= X[j + 1]), m - 2)))
        t = (x - X[i]) / h[i]
        h00, h10, h01, h11 = 2 * t**3 - 3 * t**2 + 1, t**3 - 2 * t**2 + t, -2 * t**3 + 3 * t**2, t**3 - t**2
        y = h00 * Y[i] + h10 * h[i] * d[i] + h01 * Y[i + 1] + h11 * h[i] * d[i + 1]
        dy = (
            (6 * t**2 - 6 * t) * Y[i]
            + (3 * t**2 - 4 * t + 1) * h[i] * d[i]
            + (-6 * t**2 + 6 * t) * Y[i + 1]
            + (3 * t**2 - 2 * t) * h[i] * d[i + 1]
        ) / h[i]
        out_x.append(x)
        out_y.append(y)
        out_d.append(dy)
    return out_x, out_y, out_d


def _make_stress_strain_multi(
    curves,
    *,
    hardening,
    strain_unit,
    stress_unit,
    title,
    subtitle,
    figure_label,
    note,
    source,
    width,
    height,
    font_family,
    palette,
    markers,
):
    """Overlaid σ–ε curves (one per material/condition) + optional dσ/dε–ε work-hardening panel."""
    from .._common import _derive_series_colors

    if not isinstance(curves, dict) or not curves:
        raise ValueError("curves must be {name: [(strain, stress), ...]} with at least one curve")
    data = {}
    for name, pts in curves.items():
        pts = [(float(x), float(y)) for x, y in pts]
        if len(pts) < 2:
            raise ValueError(f"stress_strain curve {name!r} needs >= 2 points")
        if any(b[0] < a[0] for a, b in zip(pts, pts[1:])):
            raise ValueError(f"stress_strain curve {name!r}: strain must be non-decreasing")
        data[str(name)] = pts
    pal = _resolve_palette(palette or "archive_ink")
    body_font, heading_font = _resolve_font(font_family)
    W, H = float(width), float(height)
    fs = _dist_font_sizes(W, H, max(4, len(data)))
    colors = _derive_series_colors(pal, len(data), mode="distinct")
    # dσ/dε per unit strain, in the stress unit (Kocks–Mecking convention); % strain → ×100
    mod_factor = 100.0 if strain_unit.strip() in ("%", "percent", "pct") else 1.0
    mod_unit = stress_unit

    title_anchor = max(
        40.0,
        14
        + (fs["title"] + 8 if title else 0)
        + (fs["subtitle"] + 6 if subtitle else 0)
        + (fs["figure"] + 4 if figure_label else 0),
    )
    leg_fs = fs["legend"] if "legend" in fs else fs["label"]
    legend_items, lx, ly, rows = [], 0.0, 0, 1
    for name, color in zip(data, colors):
        w = 30 + _estimate_label_width_px(name, leg_fs, font_family=body_font) + 24
        if lx and lx + w > W - 140:
            lx, ly, rows = 0.0, ly + 1, rows + 1
        legend_items.append((name, color, lx, ly))
        lx += w
    legend_top = title_anchor + 10
    legend_h = rows * leg_fs * 1.6 if len(data) > 1 else 0
    left = (
        30
        + fs["yaxis"] * 1.6
        + max(
            _estimate_label_width_px(f"{v:g}", fs["ytick"], font_family=body_font)
            for v in (0, max(y for c in data.values() for _, y in c))
        )
    )
    right = W - 40
    top = legend_top + legend_h + 24
    foot = (max(13.0, fs["foot"]) + 14) if (note or source) else 0
    bottom = H - (fs["ytick"] + fs["yaxis"] * 1.4 + 40) - foot
    if hardening:
        gap = fs["label"] * 1.4 + 22  # shared strain axis: the top panel keeps tick marks only
        main_bot = top + (bottom - top - gap) * 0.6
        sub_top, sub_bot = main_bot + gap, bottom
    else:
        main_bot = bottom
    xs_all = [x for c in data.values() for x, _ in c]
    ys_all = [y for c in data.values() for _, y in c]
    x_ticks, x_min, x_max = rigor.nice_axis(min(0.0, min(xs_all)), max(xs_all), 6)
    y_ticks, y_min, y_max = rigor.nice_axis(min(0.0, min(ys_all)), max(ys_all), 5)
    X = lambda v: rigor._lin(v, x_min, x_max, left, right)
    Y = lambda v: rigor._lin(v, y_min, y_max, main_bot, top)
    parts = rigor.draw_canvas_bg(pal, W, H)
    parts.append(
        rigor.draw_title_block(
            left,
            title_anchor,
            right - left,
            title=title,
            subtitle=subtitle,
            figure_label=figure_label,
            pal=pal,
            fs=fs,
            body_font=body_font,
            heading_font=heading_font,
        )
    )
    if len(data) > 1:
        for name, color, lx, row in legend_items:
            y = legend_top + row * leg_fs * 1.6 + leg_fs * 0.5
            parts.append(f'<path d="M{left + lx:.1f},{y:.1f} h22" stroke="{color}" stroke-width="2.6"/>')
            parts.append(
                f'<text x="{left + lx + 30:.1f}" y="{y + leg_fs * 0.35:.1f}" font-size="{leg_fs:.1f}" '
                f'fill="{pal["ink"]}">{_xesc(name)}</text>'
            )
    parts.append(
        rigor.draw_grid(
            left, right, top, main_bot, pal=pal, y_ticks=y_ticks, y_min=y_min, y_max=y_max, orient="horizontal"
        )
    )
    strain_title = tr("Strain ({unit})", unit=strain_unit) if strain_unit else tr("Strain")
    for (name, pts), color in zip(data.items(), colors):
        d = " ".join(f"{'M' if i == 0 else 'L'} {X(x):.1f} {Y(y):.1f}" for i, (x, y) in enumerate(pts))
        parts.append(
            f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2.4" stroke-linejoin="round" '
            f'data-role="curve" data-series={_quote(name)}/>'
        )
        if markers:
            for x, y in pts:
                parts.append(f'<circle cx="{X(x):.1f}" cy="{Y(y):.1f}" r="3.2" fill="{color}"/>')
        # UTS and fracture of each curve, unlabelled marks (values go to the caption/table)
        ux, uy = max(pts, key=lambda p: p[1])
        parts.append(_plot_marker(X(ux), Y(uy), "ultimate", color))
        fx, fy = pts[-1]
        if (fx, fy) != (ux, uy):
            parts.append(_plot_marker(X(fx), Y(fy), "fracture", color))
    parts.append(
        rigor.draw_y_axis(
            left,
            top,
            main_bot,
            y_ticks,
            y_min,
            y_max,
            pal=pal,
            fs_tick=fs["ytick"],
            fs_title=fs["yaxis"],
            side="left",
            title=tr("Stress ({unit})", unit=stress_unit) if stress_unit else tr("Stress"),
        )
    )
    parts.append(
        rigor.draw_x_axis(
            left,
            right,
            main_bot,
            x_ticks,
            x_min,
            x_max,
            pal=pal,
            fs_tick=fs["ytick"],
            fs_title=fs["yaxis"],
            title=None if hardening else strain_title,
            show_tick_labels=not hardening,
        )
    )
    if hardening:
        derivs = {}
        for name, pts in data.items():
            # The hardening rate is read past yield: interpolate the plastic points only, so the elastic
            # slope (E, ~100x larger) neither spikes nor flattens the panel.
            yp = _auto_detect_features(pts)["yield_point"] if len(pts) >= 5 else None
            k = next((i for i, p in enumerate(pts) if yp and p[0] >= yp[0]), 1 if len(pts) > 3 else 0)
            plastic = pts[k:]
            dx, _, dd = _pchip_dense([p[0] for p in plastic], [p[1] for p in plastic])
            derivs[name] = [(x, v * mod_factor) for x, v in zip(dx, dd)]
        vals = sorted(v for c in derivs.values() for _, v in c)
        if not vals:
            raise ValueError("stress_strain hardening: no plastic range to differentiate")
        lo_v = min(0.0, vals[0])
        d_ticks, d_min, d_max = rigor.nice_axis(lo_v, max(vals[-1], lo_v + 1e-9), 4)
        SY = lambda v: rigor._lin(max(d_min, min(d_max, v)), d_min, d_max, sub_bot, sub_top)
        parts.append(
            rigor.draw_grid(
                left, right, sub_top, sub_bot, pal=pal, y_ticks=d_ticks, y_min=d_min, y_max=d_max, orient="horizontal"
            )
        )
        if d_min < 0 < d_max:
            parts.append(rigor.draw_zero_line(left, right, SY(0.0), pal=pal))
        for (name, c), color in zip(derivs.items(), colors):
            d = " ".join(f"{'M' if i == 0 else 'L'} {X(x):.1f} {SY(v):.1f}" for i, (x, v) in enumerate(c))
            parts.append(
                f'<path d="{d}" fill="none" stroke="{color}" stroke-width="1.8" data-role="hardening-rate" '
                f"data-series={_quote(name)}/>"
            )
        parts.append(
            rigor.draw_y_axis(
                left,
                sub_top,
                sub_bot,
                d_ticks,
                d_min,
                d_max,
                pal=pal,
                fs_tick=fs["ytick"] * 0.9,
                fs_title=fs["yaxis"] * 0.9,
                side="left",
                title=f"dσ/dε ({mod_unit})",
            )
        )
        parts.append(
            rigor.draw_x_axis(
                left,
                right,
                sub_bot,
                x_ticks,
                x_min,
                x_max,
                pal=pal,
                fs_tick=fs["ytick"],
                fs_title=fs["yaxis"],
                title=strain_title,
            )
        )
        parts.append(
            f'<text x="{left + 8:.1f}" y="{sub_top - 10:.1f}" font-size="{fs["label"]:.1f}" '
            f'fill="{pal["ink6"]}">{_xesc(tr("Work-hardening rate"))}</text>'
        )
    foot_fs = max(13.0, fs["foot"])
    if note:
        parts.append(
            f'<text x="{left:.1f}" y="{H - 20:.1f}" font-size="{foot_fs}" fill="{pal["ink6"]}" '
            f'font-style="italic">{_xesc(note)}</text>'
        )
    if source:
        parts.append(
            f'<text x="{right:.1f}" y="{H - 20:.1f}" font-size="{foot_fs}" fill="{pal["ink6"]}" '
            f'text-anchor="end" font-style="italic">{_xesc(source)}</text>'
        )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}" font-family="{body_font}">'
        + "".join(parts)
        + "</svg>"
    )


def _quote(value):
    from xml.sax.saxutils import quoteattr

    return quoteattr(str(value))


def make_stress_strain(
    curve=None,
    *,
    curves=None,
    hardening: bool = False,
    markers: bool | None = None,
    yield_point=None,
    ultimate_point=None,
    fracture_point=None,
    elastic_region=None,
    plastic_region=None,
    strain_unit: str = "",
    stress_unit: str = "MPa",
    title: str | None = None,
    subtitle: str | None = None,
    figure_label: str | None = None,
    note: str | None = None,
    source: str | None = None,
    show_youngs_modulus: bool = True,
    auto_annotate: bool = True,
    multi_mode: str = "auto",
    width: float = 1200,
    height: float = 820,
    font_family: str | None = None,
    palette=None,
    variant: str | None = None,
) -> str:
    """Stress–strain curve.

    Parameters
    ----------
    curve : list of ``(strain, stress)`` pairs.
    yield_point / ultimate_point / fracture_point : ``(strain, stress)`` or ``None``.
    elastic_region / plastic_region : ``(strain_start, strain_end)`` or ``None``;
        drawn as translucent background bands.
    show_youngs_modulus : include ``E (Young's) = … GPa`` in the stats box when
        the elastic region is provided (slope converted to GPa only if stress
        unit is ``MPa``).
    auto_annotate : when True (default), any of ``elastic_region``,
        ``yield_point``, ``ultimate_point``, ``fracture_point`` that is ``None``
        is auto-detected from the curve shape (elastic slope / yield onset /
        global max / final sample). Pass ``False`` to suppress annotation
        entirely when the caller supplies none of these.
    curves : ``{name: [(strain, stress), ...]}`` overlays several materials/conditions on one σ–ε axis
        (legend, ▲ UTS and × fracture per curve). Sparse digitised points are fine.
    hardening : with ``curves`` (or a single ``curve``), adds a work-hardening dσ/dε–ε panel below,
        computed from a monotone-cubic interpolation of the points (no ≥20-point requirement).
    markers : draw the supplied points (default: on when a curve has < 15 points, i.e. digitised data).
    multi_mode="with_tangent_modulus" on a single ``curve`` needs >= 4 points; sparse ones are interpolated.
    """
    _variant_is_classic("stress_strain", variant)
    if curves is not None or hardening:
        if curves is None:
            if curve is None:
                raise TypeError("stress_strain needs curve=[(strain, stress), ...] or curves={name: [...]}")
            curves = {tr("Specimen"): curve}
        elif curve is not None:
            raise TypeError("pass either curve= (one curve) or curves={name: [...]}, not both")
        if markers is None:
            markers = min(len(c) for c in curves.values()) < 15
        return _make_stress_strain_multi(
            curves,
            hardening=hardening,
            strain_unit=strain_unit,
            stress_unit=stress_unit,
            title=title,
            subtitle=subtitle,
            figure_label=figure_label,
            note=note,
            source=source,
            width=width,
            height=height,
            font_family=font_family,
            palette=palette,
            markers=bool(markers),
        )
    if curve is None:
        raise TypeError("stress_strain needs curve=[(strain, stress), ...] or curves={name: [...]}")
    # user-provided value always wins; auto only fills gaps so an "unadorned"
    # curve becomes immediately readable without extra config.
    if auto_annotate:
        _auto = _auto_detect_features(curve)
        if elastic_region is None:
            elastic_region = (
                (curve[0][0], yield_point[0]) if yield_point is not None and curve else _auto["elastic_region"]
            )
        if yield_point is None:
            yield_point = _auto["yield_point"]
        if ultimate_point is None:
            ultimate_point = _auto["ultimate_point"]
        if fracture_point is None:
            fracture_point = _auto["fracture_point"]
        # Plastic region fallback: between yield strain and fracture/final x
        if plastic_region is None and yield_point is not None:
            end_x = fracture_point[0] if fracture_point is not None else curve[-1][0]
            if end_x > yield_point[0]:
                plastic_region = (yield_point[0], end_x)
    if palette is None:
        palette = "archive_ink"
    pal = _resolve_palette(palette)
    body_font, heading_font = _resolve_font(font_family)
    W, H = float(width), float(height)
    n = len(curve)
    fs = _dist_font_sizes(W, H, max(4, n))

    # Reserve the actual measured stats footprint, including font clamping and
    # padding, before assigning any plot or annotation coordinates.
    stats = []
    E = _youngs_modulus(curve, elastic_region) if show_youngs_modulus else None
    if E is not None:
        if strain_unit.strip() in ("%", "percent", "pct"):
            E *= 100.0
        # Convert to GPa if stress is MPa (slope = MPa / unitless strain = MPa, then / 1000)
        if stress_unit.lower() == "mpa":
            stats.append((tr("E (Young's)"), f"{E / 1000.0:.3g} GPa"))
        else:
            stats.append((tr("E (Young's)"), f"{E:.3g} {stress_unit}"))
    if yield_point is not None:
        stats.append(("σ_yield", f"{yield_point[1]:.3g} {stress_unit}"))
    if ultimate_point is not None:
        stats.append(("σ_UTS", f"{ultimate_point[1]:.3g} {stress_unit}"))
    if fracture_point is not None:
        stats.append(("ε_f", f"{fracture_point[0]:.3g}{strain_unit}"))

    title_anchor = max(
        40.0,
        14
        + (fs["title"] + 8 if title else 0)
        + (fs["subtitle"] + 6 if subtitle else 0)
        + (fs["figure"] + 4 if figure_label else 0),
    )
    stats_parts = []
    stats_right = 120.0
    stats_top = title_anchor + 14
    stats_bottom = stats_top
    compact = H < 600
    if compact:
        # Short canvases list the summary values as wrapped text rows instead of tall chips.
        stats_fs = fs["label"]
        stats_top = title_anchor - 14 if not (title or subtitle or figure_label) else title_anchor + 8
        rows, line = [], ""
        for label, value in stats:
            piece = f"{label} {value}"
            trial = f"{line} · {piece}" if line else piece
            if line and _estimate_label_width_px(trial, stats_fs, font_family=body_font) > W - 56:
                rows.append(line)
                trial = piece
            line = trial
        if line:
            rows.append(line)
        for i, row in enumerate(rows):
            stats_parts.append(
                f'<text x="28" y="{stats_top + stats_fs * (0.84 + 1.35 * i):.1f}" font-size="{stats_fs:.1f}" '
                f'fill="{pal["ink"]}">{_xesc(row)}</text>'
            )
        stats_bottom = stats_top + len(rows) * stats_fs * 1.35
    for entry in stats if not compact else ():
        _, measured = rigor.draw_stats_box(12, 0, [entry], pal=pal, fs=fs["label"], font_family=body_font)
        panel_width = measured[2]
        if stats_right + panel_width > W - 60 and stats_right > 120:
            stats_right = 120.0
            stats_top = stats_bottom + 10
        fragment, measured = rigor.draw_stats_box(
            stats_right + 12, stats_top, [entry], pal=pal, fs=fs["label"], font_family=body_font
        )
        stats_parts.append(fragment)
        stats_right = measured[2] + 18
        stats_bottom = max(stats_bottom, measured[3])
    stats_svg = "".join(stats_parts)
    margin_top = max(140.0, stats_bottom + 2 * max(13.0, fs["label"]) + 32)
    margin_bot = 120
    margin_left = 120
    margin_right = 60
    if compact:
        margin_top = stats_bottom + max(13.0, fs["label"]) * 1.6 + 30
        margin_bot = fs["ytick"] + fs["yaxis"] * 1.4 + 34 + (max(13.0, fs["foot"]) + 12 if note or source else 0)
        margin_left = (
            fs["yaxis"] * 1.5
            + 30
            + max(
                _estimate_label_width_px(f"{v:g}", fs["ytick"], font_family=body_font)
                for v in (0, max(p[1] for p in curve))
            )
        )
        margin_right = 28
    plot_x_left = margin_left
    plot_x_right = W - margin_right
    plot_y_top = margin_top
    plot_y_bot = H - margin_bot

    xs = [p[0] for p in curve]
    ys = [p[1] for p in curve]
    if not xs:
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}">'
            f'<text x="{W / 2}" y="{H / 2}" text-anchor="middle" font-size="16" '
            f'fill="{pal["ink6"]}">{_xesc(tr("No data"))}</text></svg>'
        )

    _plot_bbox = rigor.bbox_from_edges(plot_x_left, plot_x_right, plot_y_top, plot_y_bot)
    _mm_signals = {"xs": xs, "ys": ys}
    _mm_mode, _mm_template, _mm_reason = rigor.resolve_multi_mode_v2(
        multi_mode,
        _STRESS_STRAIN_MULTI_WHITELIST,
        _mm_signals,
        _plot_bbox,
    )
    _sub_bbox = None
    if _mm_mode is not None and _mm_template is not None:
        _rects = rigor.allocate_main_sub(_plot_bbox, _mm_template)
        _sub_bbox = _rects["sub"]
        _main_bb = _rects["main"]
        plot_y_bot = _main_bb.y1 - 12
        _sub_bbox = rigor.bbox_from_edges(_sub_bbox.x0, _sub_bbox.x1, _sub_bbox.y0 + 12, _sub_bbox.y1)

    x_min_data = min(0.0, min(xs))
    y_min_data = min(0.0, min(ys))
    x_ticks, x_min, x_max = rigor.nice_axis(x_min_data, max(xs), 6)
    y_ticks, y_min, y_max = rigor.nice_axis(y_min_data, max(ys), 5)

    def X(v):
        return rigor._lin(v, x_min, x_max, plot_x_left, plot_x_right)

    def Y(v):
        return rigor._lin(v, y_min, y_max, plot_y_bot, plot_y_top)

    parts = rigor.draw_canvas_bg(pal, W, H)

    parts.append(
        rigor.draw_title_block(
            plot_x_left,
            title_anchor,
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

    elastic_color = _rgba_with_alpha(pal.get("secondary", pal["ink"]), 0.12)
    plastic_color = _rgba_with_alpha(pal["accent"], 0.10)
    _band_label_fs = max(13.0, fs["label"])

    # Band labels occupy their own header row; no curve can strike through
    # them, even when the elastic interval is only one sample wide.
    def _band_label(xa, xb, label, chip_y_offset):
        est_w = _estimate_label_width_px(label, _band_label_fs, font_family=body_font) + 6
        mid_x = (xa + xb) * 0.5
        chip_x = max(plot_x_left + est_w * 0.5 + 8, min(plot_x_right - est_w * 0.5 - 8, mid_x))
        chip_y = stats_bottom + _band_label_fs + (4 if compact else 12)
        return (
            f'<line x1="{mid_x:.1f}" y1="{plot_y_top:.1f}" '
            f'x2="{chip_x:.1f}" y2="{chip_y + 5:.1f}" '
            f'stroke="{pal["ink4"]}" stroke-width="0.8"/>'
            f'<text x="{chip_x:.1f}" y="{chip_y:.1f}" '
            f'font-size="{_band_label_fs:.1f}" fill="{pal["ink6"]}" text-anchor="middle" '
            f'font-style="italic">{_xesc(label)}</text>'
        )

    if elastic_region:
        e_lo, e_hi = elastic_region
        xa = X(max(x_min, e_lo))
        xb = X(min(x_max, e_hi))
        parts.append(
            f'<rect x="{xa:.1f}" y="{plot_y_top:.1f}" '
            f'width="{max(0.0, xb - xa):.1f}" '
            f'height="{plot_y_bot - plot_y_top:.1f}" '
            f'fill="{elastic_color}" stroke="none"/>'
        )
        parts.append(_band_label(xa, xb, tr("Elastic"), 0.0))
    if plastic_region:
        p_lo, p_hi = plastic_region
        xa = X(max(x_min, p_lo))
        xb = X(min(x_max, p_hi))
        parts.append(
            f'<rect x="{xa:.1f}" y="{plot_y_top:.1f}" '
            f'width="{max(0.0, xb - xa):.1f}" '
            f'height="{plot_y_bot - plot_y_top:.1f}" '
            f'fill="{plastic_color}" stroke="none"/>'
        )
        # Plastic chip (if used) is staggered slightly lower to avoid colliding
        # with the Elastic chip when both land close together.
        parts.append(_band_label(xa, xb, tr("Plastic"), _band_label_fs + 2.0))

    d = " ".join(f"{'M' if i == 0 else 'L'} {X(x):.1f} {Y(y):.1f}" for i, (x, y) in enumerate(curve))
    parts.append(f'<path d="{d}" fill="none" stroke="{pal["accent"]}" stroke-width="2.4" stroke-linejoin="round"/>')

    marker_color = pal.get("secondary", pal["ink"])
    marker_fs = max(13.0, fs["label"])
    annotations = []
    if yield_point is not None:
        xp, yp = yield_point
        cx, cy = X(xp), Y(yp)
        parts.append(_plot_marker(cx, cy, "yield", marker_color))
        annotations.append((cx, cy, f"σ_y = {yp:g} {stress_unit}", -10))
    if ultimate_point is not None:
        xp, yp = ultimate_point
        cx, cy = X(xp), Y(yp)
        parts.append(_plot_marker(cx, cy, "ultimate", pal["accent"]))
        annotations.append((cx, cy, f"σ_UTS = {yp:g} {stress_unit}", -10))
    if fracture_point is not None:
        xp, yp = fracture_point
        cx, cy = X(xp), Y(yp)
        parts.append(_plot_marker(cx, cy, "fracture", pal["ink"]))
        # ε_f sits ~ ``marker_fs * 1.5`` BELOW the fracture marker (not above)
        # so it never collides with the top-right stats box which starts at
        # plot_y_top + 6 and extends down.
        annotations.append((cx, cy, f"ε_f = {xp:g}", marker_fs * 1.5))

    def segment_hits(box, a, b):
        """Liang–Barsky clipping: reject labels touched by any curve segment."""
        lo, hi = 0.0, 1.0
        for axis in (0, 1):
            delta = b[axis] - a[axis]
            if abs(delta) < 1e-12:
                if not box[axis] <= a[axis] <= box[axis + 2]:
                    return False
                continue
            t0, t1 = (box[axis] - a[axis]) / delta, (box[axis + 2] - a[axis]) / delta
            lo, hi = max(lo, min(t0, t1)), min(hi, max(t0, t1))
            if lo > hi:
                return False
        return True

    curve_pixels = [(X(x), Y(y)) for x, y in curve]
    occupied = [(cx - 12, cy - 12, cx + 12, cy + 12) for cx, cy, _, _ in annotations]
    for cx, cy, lab, dy in annotations:
        label_width = _estimate_label_width_px(lab, marker_fs, bold=True, font_family=body_font) + 6
        candidates = []
        for offset in (dy, -30, 36, -58, 64, -90, 96, -140, 146):
            for lx in (cx + 18, cx - label_width - 18, cx - label_width / 2):
                lx = max(plot_x_left + 8, min(plot_x_right - label_width - 8, lx))
                ly = cy + offset
                box = (lx - 3, ly - marker_fs, lx + label_width + 3, ly + marker_fs * 0.25)
                if box[1] < plot_y_top - 34 or box[3] > plot_y_bot - 10:
                    continue
                if any(
                    not (box[2] < other[0] or other[2] < box[0] or box[3] < other[1] or other[3] < box[1])
                    for other in occupied
                ):
                    continue
                if any(
                    segment_hits(box, a, b)
                    for a, b in ((curve_pixels[i - 1], curve_pixels[i]) for i in range(1, len(curve_pixels)))
                ):
                    continue
                candidates.append((abs(offset - dy) + abs(lx - cx) * 0.1, lx, ly, box))
        if not candidates:
            raise ValueError("stress_strain: annotation labels do not fit; increase width or height")
        _, lx, ly, box = min(candidates)
        occupied.append(box)
        parts.append(
            f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="{marker_fs:.1f}" '
            f'fill="{pal["ink"]}" font-weight="600">{_xesc(lab)}</text>'
        )

    parts.append(
        rigor.draw_y_axis(
            plot_x_left,
            plot_y_top,
            plot_y_bot,
            y_ticks,
            y_min,
            y_max,
            unit=stress_unit,
            pal=pal,
            fs_tick=fs["ytick"],
            fs_title=fs["yaxis"],
            title=tr("Stress ({unit})", unit=stress_unit) if stress_unit else tr("Stress"),
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
            unit=strain_unit if _sub_bbox is None else "",
            pal=pal,
            fs_tick=fs["ytick"],
            fs_title=fs["yaxis"],
            title=(tr("Strain ({unit})", unit=strain_unit) if strain_unit else tr("Strain"))
            if _sub_bbox is None
            else None,
            show_tick_labels=(_sub_bbox is None),
        )
    )

    if _sub_bbox is not None and _mm_mode == "with_tangent_modulus":
        _sx_l, _sx_r, _sy_t, _sy_b = rigor.bbox_to_edges(_sub_bbox)
        sub_fs_tick = max(10.0, fs["ytick"] * 0.88)
        sub_fs_title = max(10.0, fs["yaxis"] * 0.88)

        # Derivative dσ/dε via the shared rigor helper.
        _deriv = rigor.kernel_derivative(xs, ys) if len(xs) >= 20 else list(zip(*_pchip_dense(xs, ys)[::2]))
        modulus_factor = 100.0 if strain_unit.strip() in ("%", "percent", "pct") else 1.0
        modulus_unit = stress_unit
        if stress_unit.lower() == "mpa":
            modulus_factor /= 1000.0
            modulus_unit = "GPa"
        _deriv = [(x, d * modulus_factor) for x, d in _deriv]
        if _deriv:
            _d_vals = [d for _, d in _deriv]
            _d_min_v = min(_d_vals)
            _d_max_v = max(_d_vals)
            # Clamp absurd end-point spikes (titration pattern): symmetric pad.
            if _d_max_v == _d_min_v:
                _d_max_v = _d_min_v + 1.0
            _d_ticks, _d_min_a, _d_max_a = rigor.nice_axis(_d_min_v, _d_max_v, 4)

            def _SX(v):
                return rigor._lin(v, x_min, x_max, _sx_l, _sx_r)

            def _SY(v):
                return rigor._lin(v, _d_min_a, _d_max_a, _sy_b, _sy_t)

            parts.append(
                rigor.draw_grid(
                    _sx_l,
                    _sx_r,
                    _sy_t,
                    _sy_b,
                    pal=pal,
                    y_ticks=_d_ticks,
                    y_min=_d_min_a,
                    y_max=_d_max_a,
                    orient="horizontal",
                )
            )
            # Zero line if the derivative spans 0.
            if _d_min_a <= 0.0 <= _d_max_a:
                parts.append(rigor.draw_zero_line(_sx_l, _sx_r, _SY(0.0), pal=pal))

            _dpts = [(_SX(x), _SY(d)) for x, d in _deriv]
            _dd = " ".join(f"{'M' if i == 0 else 'L'} {px:.1f} {py:.1f}" for i, (px, py) in enumerate(_dpts))
            parts.append(f'<path d="{_dd}" fill="none" stroke="{pal["accent"]}" stroke-width="1.6"/>')

            parts.append(
                rigor.draw_y_axis(
                    _sx_l,
                    _sy_t,
                    _sy_b,
                    _d_ticks,
                    _d_min_a,
                    _d_max_a,
                    pal=pal,
                    fs_tick=sub_fs_tick,
                    fs_title=sub_fs_title,
                    title=None,
                    side="left",
                )
            )
            parts.append(
                f'<text x="{_sx_l + 8:.1f}" y="{_sy_t - 14:.1f}" font-size="{sub_fs_title:.1f}" '
                f'fill="{pal["ink"]}" font-weight="600">Tangent modulus · dσ/dε ({_xesc(modulus_unit)})</text>'
            )
            # Sub X axis (shared with main, visible tick labels).
            parts.append(
                rigor.draw_x_axis(
                    _sx_l,
                    _sx_r,
                    _sy_b,
                    x_ticks,
                    x_min,
                    x_max,
                    unit=strain_unit,
                    pal=pal,
                    fs_tick=sub_fs_tick,
                    fs_title=sub_fs_title,
                    title=tr("Strain ({unit})", unit=strain_unit) if strain_unit else tr("Strain"),
                    show_tick_labels=True,
                )
            )

    parts.append(stats_svg)

    parts.append(rigor.draw_footer(note, source, pal, fs, plot_x_left, plot_x_right, H - 32))

    return rigor.wrap_svg(parts, W, H, body_font)
