"""Academic chart: Hertzsprung-Russell diagram."""

from __future__ import annotations

import math

from .._common import (
    _dist_font_sizes,
    _estimate_label_width_px,
    _resolve_font,
    _resolve_palette,
    _rgb_prefix,
    _rgb_tuple,
    _variant_is_classic,
    _xesc,
)
from . import _academic_rigor as rigor
from ._shared import tr
from .grouped_bar import _wrap_label

# Multi-mode whitelist (hr_diagram).
#   with_mass_hist : horizontal histogram of stellar masses (log10) in a
#     right-side sub-panel. Shared vertical direction = mass axis.
#   Trigger: masses provided with len >= 50.
#   Template: left_right_3to1.
_HR_DIAGRAM_MULTI_WHITELIST = {
    "with_mass_hist": (
        "left_right_3to1",
        lambda s: s.get("masses") is not None and len(s.get("masses") or []) >= 50,
        lambda s: (
            (
                s.get("masses") is not None
                and len(s.get("masses") or []) >= 50
                and all((m is not None and m > 0) for m in (s.get("masses") or []))
            ),
            "need len(masses) >= 50, all positive",
        ),
    ),
}


# Hot -> cool interpolation stops (approximating black-body appearance)
# Each entry: (T_in_K, rgb_color)
_TEMP_STOPS = [
    (40000, "rgba(155, 176, 255, 1)"),  # O (blue)
    (20000, "rgba(170, 191, 255, 1)"),  # B
    (10000, "rgba(202, 215, 255, 1)"),  # A (bluish white)
    (7500, "rgba(248, 247, 255, 1)"),  # F (white)
    (6000, "rgba(255, 244, 234, 1)"),  # G (yellow-white, like sun)
    (5200, "rgba(255, 210, 161, 1)"),  # K (orange)
    (3700, "rgba(255, 180, 108, 1)"),  # M (orange-red)
    (2500, "rgba(255, 140, 90, 1)"),  # Late M / brown (red)
]


def _temp_color(T):
    """Approximate black-body color for temperature in Kelvin."""
    if T >= _TEMP_STOPS[0][0]:
        return _TEMP_STOPS[0][1]
    if T <= _TEMP_STOPS[-1][0]:
        return _TEMP_STOPS[-1][1]
    for index, (T_hi, c_hi) in enumerate(_TEMP_STOPS[:-1]):
        T_lo, c_lo = _TEMP_STOPS[index + 1]
        if T_lo <= T <= T_hi:
            if T_hi == T_lo:
                return c_hi
            t = (T - T_lo) / (T_hi - T_lo)
            r1, g1, b1 = _rgb_tuple(c_lo)
            r2, g2, b2 = _rgb_tuple(c_hi)
            r = int(r1 + (r2 - r1) * t)
            g = int(g1 + (g2 - g1) * t)
            b = int(b1 + (b2 - b1) * t)
            return f"rgba({r},{g},{b},1)"
    return _TEMP_STOPS[-1][1]


_SPECTRAL = [
    ("O", 30000, 60000),
    ("B", 10000, 30000),
    ("A", 7500, 10000),
    ("F", 6000, 7500),
    ("G", 5000, 6000),
    ("K", 3700, 5000),
    ("M", 2000, 3700),
]


def _kind_marker(cx, cy, kind, r, color, ink6):
    if kind == "giant":
        return (
            f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r * 1.4:.2f}" fill="{color}" stroke="{ink6}" stroke-width="0.6"/>'
        )
    if kind == "wd":
        a = r
        pts = f"{cx:.2f},{cy - a:.2f} {cx + a:.2f},{cy:.2f} {cx:.2f},{cy + a:.2f} {cx - a:.2f},{cy:.2f}"
        return f'<polygon points="{pts}" fill="{color}" fill-opacity="0.6" stroke="{ink6}" stroke-width="0.7"/>'
    return f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" fill="{color}" stroke="{ink6}" stroke-width="0.4"/>'


def make_hr_diagram(
    stars,
    *,
    title: str | None = None,
    subtitle: str | None = None,
    figure_label: str | None = None,
    note: str | None = None,
    source: str | None = None,
    show_sun_reference: bool = True,
    evolutionary_tracks=None,
    show_spectral_class: bool = True,
    masses: list | None = None,
    show_count: bool = False,
    width: float = 1050,
    height: float = 1050,
    font_family: str | None = None,
    palette=None,
    variant: str | None = None,
    multi_mode: str = "auto",
) -> str:
    """Hertzsprung-Russell diagram, returned as a complete SVG.

    Stars accept temperature/teff/temp with luminosity/L, or bv/b_v/B-V
    with abs_mag/absolute_magnitude. Label/name aliases are equivalent.
    A call uses one coordinate system; every observation must be finite.
    Temperature and luminosity are positive, logarithmic coordinates.
    B-V and absolute magnitude are plotted directly without conversion.
    ``show_count=True`` adds an "n stars" badge (off by default: bookkeeping).
    """
    _variant_is_classic("hr_diagram", variant)
    if palette is None:
        palette = "archive_ink"
    pal = _resolve_palette(palette)
    body_font, heading_font = _resolve_font(font_family)
    W, H = float(width), float(height)
    stars, color_magnitude = _normalize_stars(stars or [])
    evolutionary_tracks = [dict(track) for track in (evolutionary_tracks or [])]
    fs = _dist_font_sizes(W, H, max(len(stars), 8))

    if not stars and not evolutionary_tracks:
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}">'
            f'<text x="{W / 2}" y="{H / 2}" text-anchor="middle" font-size="16" '
            f'fill="{pal["ink6"]}">{_xesc(tr("No data"))}</text></svg>'
        )

    # Validate all coordinates before computing domains. No observation or
    # track vertex is silently dropped, and normalization never mutates input.
    xs = [star["temperature"] for star in stars]
    ys = [star["luminosity"] for star in stars]
    for i, track in enumerate(evolutionary_tracks):
        points = list(track.get("points", []))
        for j, point in enumerate(points):
            if len(point) != 2 or not all(_finite(value) for value in point):
                raise ValueError(f"evolutionary_tracks[{i}].points[{j}] requires finite coordinates")
            if not color_magnitude and any(value <= 0 for value in point):
                raise ValueError("temperature and luminosity track coordinates must be positive")
            xs.append(point[0])
            ys.append(point[1])
        track["points"] = points
    sun_x, sun_y = (0.65, 4.83) if color_magnitude else (5778.0, 1.0)
    if show_sun_reference:
        xs.append(sun_x)
        ys.append(sun_y)
    if not xs:
        raise ValueError("at least one star or evolutionary-track point is required")
    if color_magnitude:
        T_ticks, T_min, T_max = rigor.nice_axis(min(xs), max(xs), 5)
        L_ticks, L_min, L_max = rigor.nice_axis(min(ys), max(ys), 5)
        x_pad, y_pad = (T_max - T_min) * 0.04, (L_max - L_min) * 0.04
        T_min, T_max = T_min - x_pad, T_max + x_pad
        L_min, L_max = L_min - y_pad, L_max + y_pad
    else:
        T_min, T_max = min(xs) / 1.06, max(xs) * 1.06
        _, L_min, L_max = rigor.log_axis(min(ys), max(ys))
        L_min, L_max = L_min / 1.1, L_max * 1.1
        T_ticks = _temperature_ticks(T_min, T_max)
        L_ticks = [k for k in range(math.ceil(math.log10(L_min)), math.floor(math.log10(L_max)) + 1)]

    label_fs = max(13.0, fs["label"])
    annotations = [
        (star["temperature"], star["luminosity"], str(star.get("label", ""))) for star in stars if star.get("label")
    ]
    annotations += [
        (track["points"][-1][0], track["points"][-1][1], str(track["mass"]))
        for track in evolutionary_tracks
        if track.get("points") and track.get("mass") is not None
    ]
    if show_sun_reference:
        annotations.append((sun_x, sun_y, tr("Sun reference")))
    rail_width = min(
        W * 0.28,
        max(
            130.0,
            max(
                (_estimate_label_width_px(item[2], label_fs, font_family=body_font) for item in annotations), default=0
            ),
        ),
    )
    wrapped = [_wrap_label(item[2], rail_width, label_fs, body_font) for item in annotations]
    rail_height = sum(len(lines) * label_fs * 1.3 + 16 for lines in wrapped)
    header_y = (
        24
        + (fs["title"] + 10 if title else 0)
        + (fs["subtitle"] + 10 if subtitle else 0)
        + (fs["figure"] + 10 if figure_label else 0)
    )
    plot_x_left, plot_x_right = 130.0, W - 40
    plot_y_top = header_y + (100 if show_spectral_class and not color_magnitude else 70)
    H = max(H, plot_y_top + rail_height + 130)
    plot_y_bot = H - 130

    if masses is not None and any(not _finite(value) or value <= 0 for value in masses):
        raise ValueError("masses must contain only positive finite values")
    _mm_signals = {"masses": masses}
    _mm_bbox = rigor.bbox_from_edges(plot_x_left, plot_x_right, plot_y_top, plot_y_bot)
    _mm_mode, _mm_template, _mm_reason = rigor.resolve_multi_mode_v2(
        multi_mode,
        _HR_DIAGRAM_MULTI_WHITELIST,
        _mm_signals,
        _mm_bbox,
    )
    _sub_bbox = None
    if _mm_mode is not None and _mm_template is not None:
        _rects = rigor.allocate_main_sub(_mm_bbox, _mm_template)
        _sub_bbox = _rects["sub"]
        plot_x_right = _rects["main"].x1

    if annotations:
        plot_x_right -= rail_width + 46

    def X(T):
        if color_magnitude:
            return rigor._lin(T, T_min, T_max, plot_x_left, plot_x_right)
        return rigor._log_lin(T, T_min, T_max, plot_x_right, plot_x_left)

    def Y(L):
        if color_magnitude:
            return rigor._lin(L, L_min, L_max, plot_y_top, plot_y_bot)
        return rigor._log_lin(L, L_min, L_max, plot_y_bot, plot_y_top)

    parts = rigor.draw_canvas_bg(pal, W, H)

    parts.append(
        rigor.draw_title_block(
            plot_x_left,
            header_y,
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

    if show_spectral_class and not color_magnitude:
        banner_y = plot_y_top - 28
        banner_h = 22
        for letter, T_lo, T_hi in _SPECTRAL:
            Tl = max(T_lo, T_min)
            Th = min(T_hi, T_max)
            if Th <= Tl:
                continue
            xL = min(X(Tl), X(Th))
            xR = max(X(Tl), X(Th))
            if xR - xL < 4:
                continue
            c = _temp_color((Tl + Th) * 0.5)
            parts.append(
                f'<rect x="{xL:.1f}" y="{banner_y:.1f}" width="{xR - xL:.1f}" '
                f'height="{banner_h:.1f}" fill="{c}" fill-opacity="0.55" '
                f'stroke="{pal["ink1"]}" stroke-width="0.6"/>'
            )
            xc = (xL + xR) * 0.5
            parts.append(
                f'<text x="{xc:.1f}" y="{banner_y + banner_h * 0.5 + fs["label"] * 0.33:.1f}" '
                f'font-size="{fs["label"]}" fill="{pal["ink"]}" '
                f'text-anchor="middle" font-weight="700">{letter}</text>'
            )

    grid_c = pal.get("grid", "rgba(28,28,26,0.12)")
    for value in T_ticks:
        xx = X(value)
        parts.append(
            f'<line x1="{xx:.1f}" y1="{plot_y_top:.1f}" x2="{xx:.1f}" y2="{plot_y_bot:.1f}" stroke="{grid_c}" stroke-width="0.8" stroke-dasharray="3 3"/>'
        )
    for value in L_ticks:
        yy = Y(value if color_magnitude else 10**value)
        parts.append(
            f'<line x1="{plot_x_left:.1f}" y1="{yy:.1f}" x2="{plot_x_right:.1f}" y2="{yy:.1f}" stroke="{grid_c}" stroke-width="0.8" stroke-dasharray="3 3"/>'
        )

    for track in evolutionary_tracks:
        points = track["points"]
        if len(points) >= 2:
            path = " ".join(f"{'M' if i == 0 else 'L'} {X(x):.1f} {Y(y):.1f}" for i, (x, y) in enumerate(points))
            parts.append(f'<path d="{path}" fill="none" stroke="{pal["ink6"]}" stroke-width="1.3"/>')

    # Names occupy a measured rail, separate from all data and grid lines.
    rail_x = plot_x_right + 34
    rows = sorted(zip(annotations, wrapped), key=lambda row: Y(row[0][1]))
    cursor, remaining = plot_y_top + 8, rail_height
    for (x, y, label), lines in rows:
        row_h = len(lines) * label_fs * 1.3 + 16
        top = max(cursor, min(Y(y) - label_fs * 0.5, plot_y_bot - remaining))
        center_y = top + label_fs * 0.45
        parts.append(
            f'<path d="M {X(x):.1f} {Y(y):.1f} L {plot_x_right + 14:.1f} {center_y:.1f} L {rail_x - 8:.1f} {center_y:.1f}" fill="none" stroke="{pal["ink4"]}" stroke-width="0.8" stroke-dasharray="2 3"/>'
        )
        for j, line in enumerate(lines):
            parts.append(
                f'<text x="{rail_x:.1f}" y="{top + label_fs + j * label_fs * 1.3:.1f}" font-size="{label_fs}" fill="{pal["ink"]}">{_xesc(line)}</text>'
            )
        cursor, remaining = top + row_h, remaining - row_h

    # The reference is a hollow ring. Draw it first so a measured star at the
    # solar coordinates remains visible in its original marker and color.
    if show_sun_reference:
        parts.append(
            f'<circle cx="{X(sun_x):.2f}" cy="{Y(sun_y):.2f}" r="8" fill="none" stroke="{pal["accent"]}" stroke-width="1.2"/>'
        )
    for star in stars:
        x, y = star["temperature"], star["luminosity"]
        color = pal["accent"] if color_magnitude else _temp_color(x)
        parts.append(_kind_marker(X(x), Y(y), star.get("kind", "default"), 3.2, color, pal["ink6"]))

    parts.append(
        (_draw_magnitude_axis if color_magnitude else rigor.draw_y_axis)(
            plot_x_left,
            plot_y_top,
            plot_y_bot,
            L_ticks,
            L_min,
            L_max,
            unit="mag" if color_magnitude else "L☉",
            pal=pal,
            fs_tick=fs["ytick"],
            fs_title=fs["yaxis"],
            title=tr("Absolute magnitude") if color_magnitude else tr("Luminosity"),
            log=not color_magnitude,
            side="left",
        )
    )
    # custom X axis because we need to swap tick-order (hot on left)
    parts.append(
        _draw_x_axis_inverted(
            plot_x_left,
            plot_x_right,
            plot_y_bot,
            T_ticks,
            T_min,
            T_max,
            pal=pal,
            fs_tick=fs["ytick"],
            fs_title=fs["yaxis"],
            title=tr("B−V color index") if color_magnitude else tr("Effective Temperature"),
            unit="mag" if color_magnitude else "K",
            linear=color_magnitude,
        )
    )

    parts.append(
        f'<rect x="{plot_x_left:.1f}" y="{plot_y_top:.1f}" '
        f'width="{plot_x_right - plot_x_left:.1f}" height="{plot_y_bot - plot_y_top:.1f}" '
        f'fill="none" stroke="{pal["ink"]}" stroke-width="1.2"/>'
    )

    # Placing it at (plot_y_top + 18) landed the italic badge on top of the first horizontal gridline for large canvases
    # → embed_svg_line_through_text.
    if show_count:
        parts.append(
            f'<text x="{plot_x_right:.1f}" y="{header_y + 30:.1f}" '
            f'font-size="{fs["label"]}" fill="{pal["ink6"]}" '
            f'text-anchor="end" font-style="italic">n stars = {len(stars)}</text>'
        )

    if _sub_bbox is not None and _mm_mode == "with_mass_hist" and masses:
        sx0, sx1, sy0, sy1 = (_sub_bbox.x0, _sub_bbox.x1, _sub_bbox.y0, _sub_bbox.y1)
        sub_fs_tick = max(10.0, fs["ytick"] * 0.88)
        sub_fs_title = max(10.0, fs["yaxis"] * 0.88)
        # Compute log10(mass) and bin into ~12 bins.
        _logm = [math.log10(m) for m in masses if m > 0]
        if _logm:
            lmin, lmax = min(_logm), max(_logm)
            if lmax == lmin:
                lmax = lmin + 0.5
            n_bins = 12
            bin_w = (lmax - lmin) / n_bins
            counts = [0] * n_bins
            for lm in _logm:
                idx = int((lm - lmin) / bin_w)
                if idx >= n_bins:
                    idx = n_bins - 1
                idx = max(idx, 0)
                counts[idx] += 1
            max_cnt = max(counts) if counts else 1
            # Reserve left room for tick labels and axis title.
            mass_tick_labels = [f"{10 ** (lmin + t * (lmax - lmin) / 4):.2g}" for t in range(5)]
            mass_tick_width = max(
                _estimate_label_width_px(label, sub_fs_tick, font_family=body_font) for label in mass_tick_labels
            )
            axis_x = sx0 + mass_tick_width + sub_fs_title + 20
            bar_x1 = sx1 - 10
            bar_w_full = max(10.0, bar_x1 - axis_x)
            parts.append(
                f'<text x="{axis_x:.1f}" y="{sy0 - 10:.1f}" '
                f'font-size="{sub_fs_title:.1f}" fill="{pal["ink"]}" '
                f'font-weight="600" font-family="{body_font}">{_xesc(tr("Mass hist"))}</text>'
            )
            parts.append(
                f'<line x1="{axis_x:.1f}" y1="{sy0:.1f}" x2="{axis_x:.1f}" y2="{sy1:.1f}" '
                f'stroke="{pal["ink"]}" stroke-width="1.0"/>'
            )

            # Y axis = log10(mass). Y bin tops → high mass; low mass at bottom.
            # Map lmax → sy0 (top), lmin → sy1 (bottom).
            def _MY(lm):
                return rigor._lin(lm, lmin, lmax, sy1, sy0)

            _bar_fill = pal.get("accent", "rgba(217,106,46,1)")
            for i, cnt in enumerate(counts):
                lm_lo = lmin + i * bin_w
                lm_hi = lm_lo + bin_w
                bw = bar_w_full * (cnt / max_cnt) if max_cnt > 0 else 0.0
                y_top_bar = _MY(lm_hi)
                y_bot_bar = _MY(lm_lo)
                parts.append(
                    f'<rect x="{axis_x:.1f}" y="{y_top_bar:.1f}" width="{bw:.2f}" '
                    f'height="{(y_bot_bar - y_top_bar - 1.0):.2f}" '
                    f'fill="{_rgb_prefix(_bar_fill)}0.68)" stroke="none"/>'
                )
            # Y tick labels at a few even log(mass) values.
            n_ticks = 4
            for t in range(n_ticks + 1):
                lm = lmin + t * (lmax - lmin) / n_ticks
                ty = _MY(lm)
                mval = 10**lm
                parts.append(
                    f'<line x1="{axis_x - 4:.1f}" y1="{ty:.1f}" '
                    f'x2="{axis_x:.1f}" y2="{ty:.1f}" '
                    f'stroke="{pal["ink"]}" stroke-width="0.8"/>'
                )
                parts.append(
                    f'<text x="{axis_x - 6:.1f}" y="{ty + sub_fs_tick * 0.35:.1f}" '
                    f'font-size="{sub_fs_tick:.1f}" fill="{pal["ink"]}" '
                    f'text-anchor="end" font-family="{body_font}">{mval:.2g}</text>'
                )
            yt_x = sx0 + 8
            yt_y = (sy0 + sy1) * 0.5
            parts.append(
                f'<text x="{yt_x:.1f}" y="{yt_y:.1f}" '
                f'font-size="{sub_fs_title:.1f}" fill="{pal["ink"]}" '
                f'text-anchor="middle" transform="rotate(-90 {yt_x:.1f} {yt_y:.1f})" '
                f'font-weight="600" font-family="{body_font}">log(mass)</text>'
            )

    parts.append(rigor.draw_footer(note, source, pal, fs, plot_x_left, plot_x_right, H - 32))

    return rigor.wrap_svg(parts, W, H, body_font)


def _draw_x_axis_inverted(
    x_left, x_right, y, ticks, v_min, v_max, *, pal, fs_tick, fs_title, title, unit, linear=False
):
    """Explicit Kelvin ticks also cover domains without a complete decade."""
    ink = pal["ink"]
    parts = [
        f'<line x1="{x_left:.1f}" y1="{y:.1f}" x2="{x_right:.1f}" y2="{y:.1f}" stroke="{ink}" stroke-width="1.2"/>'
    ]
    _labels = rigor._tick_label_map(ticks, v_max - v_min)
    for value in ticks:
        xp = (
            rigor._lin(value, v_min, v_max, x_left, x_right)
            if linear
            else rigor._log_lin(value, v_min, v_max, x_right, x_left)
        )
        parts.append(
            f'<line x1="{xp:.1f}" y1="{y:.1f}" x2="{xp:.1f}" y2="{y + 5:.1f}" stroke="{ink}" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{xp:.1f}" y="{y + fs_tick + 8:.1f}" font-size="{fs_tick}" text-anchor="middle" fill="{ink}">{_labels[value]}</text>'
        )
    parts.append(
        f'<text x="{(x_left + x_right) / 2:.1f}" y="{y + fs_tick + fs_title + 24:.1f}" font-size="{fs_title}" fill="{ink}" text-anchor="middle" font-weight="600">{_xesc(title)} ({_xesc(unit)})</text>'
    )
    return "".join(parts)


def _draw_magnitude_axis(x, y_top, y_bot, ticks, v_min, v_max, *, pal, fs_tick, fs_title, title, **kwargs):
    parts = [
        f'<line x1="{x:.1f}" y1="{y_top:.1f}" x2="{x:.1f}" y2="{y_bot:.1f}" stroke="{pal["ink"]}" stroke-width="1.2"/>'
    ]
    _labels = rigor._tick_label_map(ticks, v_max - v_min)
    for value in ticks:
        y = rigor._lin(value, v_min, v_max, y_top, y_bot)
        parts.append(
            f'<line x1="{x - 5:.1f}" y1="{y:.1f}" x2="{x:.1f}" y2="{y:.1f}" stroke="{pal["ink"]}" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{x - 10:.1f}" y="{y + fs_tick * 0.35:.1f}" font-size="{fs_tick}" text-anchor="end" fill="{pal["ink"]}">{_labels[value]}</text>'
        )
    cy = (y_top + y_bot) / 2
    parts.append(
        f'<text x="{x - 70:.1f}" y="{cy:.1f}" transform="rotate(-90 {x - 70:.1f} {cy:.1f})" text-anchor="middle" font-size="{fs_title}" fill="{pal["ink"]}" font-weight="600">{_xesc(title)} (mag)</text>'
    )
    return "".join(parts)


def _temperature_ticks(low, high):
    candidates = [
        factor * 10**power
        for power in range(math.floor(math.log10(low)), math.ceil(math.log10(high)) + 1)
        for factor in (1, 2, 3, 4, 5, 6, 8)
    ]
    ticks = [value for value in candidates if low <= value <= high]
    if len(ticks) < 2:
        ticks = [value for value in rigor.nice_axis(low, high, 4)[0] if low <= value <= high]
    if len(ticks) > 7:
        step = math.ceil(len(ticks) / 7)
        ticks = ticks[::step]
    return ticks


def _finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _normalize_stars(stars):
    normalized, modes = [], set()
    for i, star in enumerate(stars):
        if not isinstance(star, dict):
            raise TypeError(f"stars[{i}] must be a mapping of stellar coordinates")
        x = next((star[key] for key in ("temperature", "teff", "temp") if key in star), None)
        y = next((star[key] for key in ("luminosity", "L") if key in star), None)
        bv = next((star[key] for key in ("bv", "b_v", "B-V", "color_index") if key in star), None)
        magnitude = next(
            (star[key] for key in ("abs_mag", "absolute_magnitude", "abs_magnitude", "M_V") if key in star), None
        )
        mode = x is None and y is None and (bv is not None or magnitude is not None)
        if mode:
            x, y = bv, magnitude
        if not _finite(x) or not _finite(y):
            raise ValueError(f"stars[{i}] requires finite temperature/luminosity or bv/abs_mag coordinates")
        if not mode and (x <= 0 or y <= 0):
            raise ValueError(f"stars[{i}] temperature and luminosity must be positive")
        modes.add(mode)
        normalized.append({**star, "temperature": x, "luminosity": y, "label": star.get("label", star.get("name", ""))})
    if len(modes) > 1:
        raise ValueError("all stars must use the same temperature/luminosity or bv/abs_mag coordinate system")
    return normalized, next(iter(modes), False)
