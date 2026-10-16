"""Academic rigor primitives — the shared foundation for ~40 academic charts."""

from __future__ import annotations

import math
import random

from .._common import (
    _estimate_label_width_px,
    _fmt_axis_ticks,
    _hls_to_rgba,
    _is_dark_palette,
    _render_title_block,
    _rgb_prefix,
    _rgb_to_hls,
    _rgb_tuple,
    _xesc,
)
from ._shared import tr

# 1. Axis / tick / grid helpers
_NICE_STEPS = (1.0, 2.0, 2.5, 5.0, 10.0)


def nice_axis(v_min: float, v_max: float, n_ticks: int = 5):
    """Nice-number axis ticks."""
    v_min, v_max = float(v_min), float(v_max)
    if not math.isfinite(v_min) or not math.isfinite(v_max):
        raise ValueError("axis bounds must be finite")
    if n_ticks < 1:
        raise ValueError("n_ticks must be positive")
    if v_max < v_min:
        v_min, v_max = v_max, v_min
    if v_max == v_min:
        pad = abs(v_max) * 0.5 if v_max else 0.5
        v_min -= pad
        v_max += pad
    raw = (v_max - v_min) / max(1, n_ticks)
    if not math.isfinite(raw) or raw <= 0:
        raise ValueError("axis range is not representable")
    mag = 10 ** math.floor(math.log10(raw)) if raw > 0 else 1.0
    norm = raw / mag
    for s in _NICE_STEPS:
        if norm <= s:
            step = s * mag
            break
    else:
        step = 10.0 * mag
    step = max(step, math.ulp(max(abs(v_min), abs(v_max))))
    v_min_a = math.floor(v_min / step) * step
    v_max_a = math.ceil(v_max / step) * step
    if v_max_a - v_min_a < step * 0.5:
        v_max_a += step
    count = round((v_max_a - v_min_a) / step)
    ticks = list(dict.fromkeys(float(f"{v_min_a + i * step:.17g}") for i in range(count + 1)))
    return ticks, v_min_a, v_max_a


def log_axis(v_min: float, v_max: float):
    """Decade log axis."""
    if not all(math.isfinite(v) and v > 0 for v in (v_min, v_max)):
        raise ValueError("log axes require positive finite bounds")
    if v_max < v_min:
        v_min, v_max = v_max, v_min
    k_lo = math.floor(math.log10(v_min))
    k_hi = math.ceil(math.log10(v_max))
    if k_hi - k_lo < 1:
        k_hi = k_lo + 1
    decades = list(range(int(k_lo), int(k_hi) + 1))
    lower = 10.0**k_lo if k_lo >= -323 else v_min
    upper = 10.0**k_hi if k_hi <= 308 else v_max
    return decades, lower, upper


def log_ticks(v_min: float, v_max: float, *, min_count: int = 4, max_count: int = 7):
    """Labeled ticks for a log axis on [v_min, v_max] (true values, placed at log positions)."""
    if not all(math.isfinite(v) and v > 0 for v in (v_min, v_max)):
        raise ValueError("log axes require positive finite bounds")
    lo, hi = sorted((float(v_min), float(v_max)))
    tol = 1e-9

    def mantissa_ticks(mants):
        e0, e1 = max(-323, math.floor(math.log10(lo))), min(308, math.ceil(math.log10(hi)))
        out = []
        for e in range(e0, e1 + 1):
            for m in mants:
                t = float(f"{m * 10.0**e:.12g}")
                if lo * (1 - tol) <= t <= hi * (1 + tol):
                    out.append(t)
        return out

    best = []
    for mants in ((1,), (1, 2, 5), (1, 2, 3, 5), (1, 1.5, 2, 3, 5, 7), tuple(range(1, 10))):
        ticks = mantissa_ticks(mants)
        if len(ticks) >= min_count:
            if len(ticks) > max_count:
                ticks = ticks[:: math.ceil(len(ticks) / max_count)]
            return ticks
        best = ticks if len(ticks) > len(best) else best
    for n in range(min_count, max_count + 4):
        ticks, _, _ = nice_axis(lo, hi, n)
        ticks = [float(f"{t:.12g}") for t in ticks if t > 0 and lo * (1 - tol) <= t <= hi * (1 + tol)]
        if len(ticks) >= min_count:
            return ticks[: max_count + 2] if len(ticks) <= max_count + 2 else ticks[::2]
        best = ticks if len(ticks) > len(best) else best
    return best


def _lin(v: float, v_min: float, v_max: float, p_min: float, p_max: float) -> float:
    if v_max == v_min:
        return (p_min + p_max) * 0.5
    t = (v - v_min) / (v_max - v_min)
    return p_min + t * (p_max - p_min)


def _log_lin(v: float, v_min: float, v_max: float, p_min: float, p_max: float) -> float:
    if not all(math.isfinite(value) and value > 0 for value in (v, v_min, v_max)):
        raise ValueError("log coordinates require positive finite values")
    lv, lmin, lmax = (math.log10(value) for value in (v, v_min, v_max))
    if lmax == lmin:
        return (p_min + p_max) * 0.5
    t = (lv - lmin) / (lmax - lmin)
    return p_min + t * (p_max - p_min)


def _tick_label_map(ticks, span):
    """Uniformly formatted labels for one tick set (same decimals, same grouping)."""
    ticks = list(ticks)
    return dict(zip(ticks, _fmt_axis_ticks(ticks, span if span > 0 else None)))


def draw_y_axis(
    x: float,
    y_top: float,
    y_bot: float,
    ticks,
    v_min: float,
    v_max: float,
    unit: str = "",
    pal: dict | None = None,
    fs_tick: float = 13.0,
    fs_title: float | None = None,
    title: str | None = None,
    log: bool = False,
    side: str = "left",
    show_tick_labels: bool = True,
) -> str:
    """Draw vertical Y axis: axis line, major ticks, labels, optional rotated title and unit chip."""
    pal = pal or {}
    ink = pal.get("ink", "rgba(28,28,26,1)")
    ink6 = pal.get("ink6", "rgba(28,28,26,0.6)")
    ink4 = pal.get("ink4", "rgba(28,28,26,0.4)")
    tick_sign = -1 if side == "left" else 1
    anchor = "end" if side == "left" else "start"
    label_dx = -6 if side == "left" else 6
    parts = [
        f'<line x1="{x:.1f}" y1="{y_top:.1f}" x2="{x:.1f}" y2="{y_bot:.1f}" stroke="{ink}" stroke-width="1.2" data-role="y-axis"/>'
    ]
    span = v_max - v_min
    if log:
        for k in ticks:
            v = 10**k
            y = _log_lin(v, v_min, v_max, y_bot, y_top)
            parts.append(
                f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x + tick_sign * 5:.1f}" y2="{y:.1f}" '
                f'stroke="{ink}" stroke-width="1"/>'
            )
            if show_tick_labels:
                label = "10"
                parts.append(
                    f'<text x="{x + label_dx:.1f}" y="{y + fs_tick * 0.35:.1f}" '
                    f'font-size="{fs_tick}" text-anchor="{anchor}" fill="{ink}">{_xesc(label)}'
                    f'<tspan font-size="{fs_tick * 0.7:.1f}" baseline-shift="super">{int(k)}</tspan></text>'
                )
            # minor ticks 2..9
            for m in range(2, 10):
                vm = m * (10**k)
                if vm < v_min or vm > v_max:
                    continue
                ym = _log_lin(vm, v_min, v_max, y_bot, y_top)
                parts.append(
                    f'<line x1="{x:.1f}" y1="{ym:.1f}" x2="{x + tick_sign * 3:.1f}" y2="{ym:.1f}" '
                    f'stroke="{ink4}" stroke-width="0.8"/>'
                )
    else:
        tick_labels = _tick_label_map(ticks, span)
        for v in ticks:
            if v < v_min - 1e-9 or v > v_max + 1e-9:
                continue
            y = _lin(v, v_min, v_max, y_bot, y_top)
            parts.append(
                f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x + tick_sign * 5:.1f}" y2="{y:.1f}" '
                f'stroke="{ink}" stroke-width="1"/>'
            )
            if show_tick_labels:
                parts.append(
                    f'<text x="{x + label_dx:.1f}" y="{y + fs_tick * 0.35:.1f}" '
                    f'font-size="{fs_tick}" text-anchor="{anchor}" fill="{ink}">'
                    f"{_xesc(tick_labels[v])}</text>"
                )
    if title:
        fs_t = fs_title or max(13.0, fs_tick * 1.05)
        # rotated axis title to the far left
        xt = x + (tick_sign * (fs_tick * 3.2))
        yt = (y_top + y_bot) * 0.5
        parts.append(
            f'<text x="{xt:.1f}" y="{yt:.1f}" font-size="{fs_t}" fill="{ink}" '
            f'text-anchor="middle" transform="rotate(-90 {xt:.1f} {yt:.1f})" '
            f'font-weight="600">{_xesc(title)}</text>'
        )
    if unit and not _title_has_unit(title, unit):
        # Place unit chip in the narrow gap between the title block (above) and the topmost tick label (below).
        _unit_fs = min(14.0, max(11.0, fs_tick * 0.7))
        # Chip baseline: at least 10-15px above axis top; measured so chip
        # descender clears the top tick label's ascender by >= 4px.
        _chip_y = y_top - fs_tick * 0.55 - 4
        # Anchor to axis-line x (slightly outside the plot), to avoid stacking
        # with tick-label column.
        _chip_dx = -4 if side == "left" else 4
        _chip_anchor = "end" if side == "left" else "start"
        parts.append(
            f'<text x="{x + _chip_dx:.1f}" y="{_chip_y:.1f}" font-size="{_unit_fs:.1f}" '
            f'fill="{ink6}" text-anchor="{_chip_anchor}" font-style="italic">{_xesc(unit)}</text>'
        )
    return "".join(parts)


def _title_has_unit(title, unit):
    """An axis title that already names its unit ("Z' (Ω·cm²)") needs no separate italic unit label."""
    norm = lambda t: str(t or "").replace(" ", "").replace("·", "").replace("⋅", "")
    return bool(title) and norm(unit) in norm(title)


def draw_x_axis(
    x_left: float,
    x_right: float,
    y: float,
    ticks,
    v_min: float,
    v_max: float,
    unit: str = "",
    pal: dict | None = None,
    fs_tick: float = 13.0,
    fs_title: float | None = None,
    title: str | None = None,
    log: bool = False,
    categories=None,
    show_tick_labels: bool = True,
) -> str:
    """Draw horizontal X axis."""
    pal = pal or {}
    ink = pal.get("ink", "rgba(28,28,26,1)")
    ink6 = pal.get("ink6", "rgba(28,28,26,0.6)")
    ink4 = pal.get("ink4", "rgba(28,28,26,0.4)")
    parts = [
        f'<line x1="{x_left:.1f}" y1="{y:.1f}" x2="{x_right:.1f}" y2="{y:.1f}" stroke="{ink}" stroke-width="1.2" data-role="x-axis"/>'
    ]
    span = v_max - v_min
    if categories is not None:
        # ticks are x-positions in viewBox, categories are string labels
        for xp, cat in zip(ticks, categories):
            parts.append(
                f'<line x1="{xp:.1f}" y1="{y:.1f}" x2="{xp:.1f}" y2="{y + 5:.1f}" stroke="{ink}" stroke-width="1"/>'
            )
            if show_tick_labels:
                parts.append(
                    f'<text x="{xp:.1f}" y="{y + fs_tick + 8:.1f}" '
                    f'font-size="{fs_tick}" text-anchor="middle" fill="{ink}">{_xesc(cat)}</text>'
                )
    elif log:
        for k in ticks:
            v = 10**k
            xp = _log_lin(v, v_min, v_max, x_left, x_right)
            parts.append(
                f'<line x1="{xp:.1f}" y1="{y:.1f}" x2="{xp:.1f}" y2="{y + 5:.1f}" stroke="{ink}" stroke-width="1"/>'
            )
            if show_tick_labels:
                parts.append(
                    f'<text x="{xp:.1f}" y="{y + fs_tick + 8:.1f}" '
                    f'font-size="{fs_tick}" text-anchor="middle" fill="{ink}">10'
                    f'<tspan font-size="{fs_tick * 0.7:.1f}" baseline-shift="super">{int(k)}</tspan></text>'
                )
            for m in range(2, 10):
                vm = m * (10**k)
                if vm < v_min or vm > v_max:
                    continue
                xm = _log_lin(vm, v_min, v_max, x_left, x_right)
                parts.append(
                    f'<line x1="{xm:.1f}" y1="{y:.1f}" x2="{xm:.1f}" y2="{y + 3:.1f}" '
                    f'stroke="{ink4}" stroke-width="0.8"/>'
                )
    else:
        tick_labels = _tick_label_map(ticks, span)
        for v in ticks:
            if v < v_min - 1e-9 or v > v_max + 1e-9:
                continue
            xp = _lin(v, v_min, v_max, x_left, x_right)
            parts.append(
                f'<line x1="{xp:.1f}" y1="{y:.1f}" x2="{xp:.1f}" y2="{y + 5:.1f}" stroke="{ink}" stroke-width="1"/>'
            )
            if show_tick_labels:
                parts.append(
                    f'<text x="{xp:.1f}" y="{y + fs_tick + 8:.1f}" '
                    f'font-size="{fs_tick}" text-anchor="middle" fill="{ink}">'
                    f"{_xesc(tick_labels[v])}</text>"
                )
    if title:
        fs_t = fs_title or max(13.0, fs_tick * 1.05)
        xc = (x_left + x_right) * 0.5
        parts.append(
            f'<text x="{xc:.1f}" y="{y + fs_tick + fs_t + 18:.1f}" font-size="{fs_t}" '
            f'fill="{ink}" text-anchor="middle" font-weight="600">{_xesc(title)}</text>'
        )
    if unit and not _title_has_unit(title, unit):
        # Shift unit chip below the end-tick label line to avoid overlapping with it.
        parts.append(
            f'<text x="{x_right:.1f}" y="{y + fs_tick * 2.3 + 8:.1f}" '
            f'font-size="{max(13.0, fs_tick * 0.95):.1f}" fill="{ink6}" '
            f'text-anchor="end" font-style="italic">{_xesc(unit)}</text>'
        )
    return "".join(parts)


def draw_grid(
    x_left: float,
    x_right: float,
    y_top: float,
    y_bot: float,
    pal: dict | None = None,
    y_ticks=None,
    y_min: float | None = None,
    y_max: float | None = None,
    x_ticks=None,
    x_min: float | None = None,
    x_max: float | None = None,
    orient: str = "horizontal",
    log_y: bool = False,
    log_x: bool = False,
    *,
    stroke_width: float = 0.5,
    dash: str = "2 3",
    opacity: float = 0.6,
    cutout_bboxes=None,
) -> str:
    """Dashed grid lines."""
    pal = pal or {}
    grid = pal.get("grid", "rgba(28,28,26,0.12)")
    # Fold opacity into the stroke color so dasharray/opacity on the <line>
    # don't double-dim already-translucent grid colors coming from palettes.
    if opacity < 1.0:
        gr, gg, gb = _rgb_tuple(grid)
        # multiply the palette grid alpha (parsed from the rgba string) by opacity
        import re as _re

        m = _re.match(r"\s*rgba?\(\s*[\d.]+\s*,\s*[\d.]+\s*,\s*[\d.]+(?:\s*,\s*([\d.]+))?", grid or "")
        base_a = float(m.group(1)) if (m and m.group(1)) else 1.0
        grid = f"rgba({gr},{gg},{gb},{base_a * opacity:.3f})"

    def _horiz_segments(x0, x1, y):
        """Return list of (sx, sy, ex, ey) horizontal segments that avoid cutouts."""
        if not cutout_bboxes:
            return [(x0, y, x1, y)]
        xs = sorted((x0, x1))
        # start with full span, repeatedly subtract overlapping x-intervals of
        # each cutout the line's y falls inside.
        intervals = [(xs[0], xs[1])]
        for cx0, cy0, cx1, cy1 in cutout_bboxes:
            if not (cy0 <= y <= cy1):
                continue
            new_intervals = []
            for a, b in intervals:
                if cx1 <= a or cx0 >= b:
                    new_intervals.append((a, b))
                    continue
                if cx0 > a:
                    new_intervals.append((a, cx0))
                if cx1 < b:
                    new_intervals.append((cx1, b))
            intervals = new_intervals
        return [(a, y, b, y) for a, b in intervals if (b - a) > 0.5]

    def _vert_segments(xp, y0, y1):
        if not cutout_bboxes:
            return [(xp, y0, xp, y1)]
        ys = sorted((y0, y1))
        intervals = [(ys[0], ys[1])]
        for cx0, cy0, cx1, cy1 in cutout_bboxes:
            if not (cx0 <= xp <= cx1):
                continue
            new_intervals = []
            for a, b in intervals:
                if cy1 <= a or cy0 >= b:
                    new_intervals.append((a, b))
                    continue
                if cy0 > a:
                    new_intervals.append((a, cy0))
                if cy1 < b:
                    new_intervals.append((cy1, b))
            intervals = new_intervals
        return [(xp, a, xp, b) for a, b in intervals if (b - a) > 0.5]

    parts = []
    if orient in ("horizontal", "both") and y_ticks and y_min is not None and y_max is not None:
        for v in y_ticks:
            if log_y:
                y = _log_lin(10**v if isinstance(v, int) else v, y_min, y_max, y_bot, y_top)
            else:
                y = _lin(v, y_min, y_max, y_bot, y_top)
            for sx, sy, ex, ey in _horiz_segments(x_left, x_right, y):
                parts.append(
                    f'<line x1="{sx:.1f}" y1="{sy:.1f}" x2="{ex:.1f}" y2="{ey:.1f}" '
                    f'stroke="{grid}" stroke-width="{stroke_width}" stroke-dasharray="{dash}"/>'
                )
    if orient in ("vertical", "both") and x_ticks and x_min is not None and x_max is not None:
        for v in x_ticks:
            if log_x:
                xp = _log_lin(10**v if isinstance(v, int) else v, x_min, x_max, x_left, x_right)
            else:
                xp = _lin(v, x_min, x_max, x_left, x_right)
            for sx, sy, ex, ey in _vert_segments(xp, y_top, y_bot):
                parts.append(
                    f'<line x1="{sx:.1f}" y1="{sy:.1f}" x2="{ex:.1f}" y2="{ey:.1f}" '
                    f'stroke="{grid}" stroke-width="{stroke_width}" stroke-dasharray="{dash}"/>'
                )
    return "".join(parts)


# 2. Uncertainty / significance
def draw_error_bar(
    cx: float,
    cy: float,
    err_up: float,
    err_dn: float,
    pal: dict | None = None,
    kind: str = "SD",
    width: float = 12.0,
    color: str | None = None,
    stroke_w: float = 1.4,
) -> str:
    """Vertical error bar: top cap, bottom cap, central line. ``kind`` is informational."""
    pal = pal or {}
    c = color or pal.get("ink", "rgba(28,28,26,1)")
    y_top = cy - err_up
    y_bot = cy + err_dn
    hw = width * 0.5
    parts = [
        f'<line x1="{cx:.1f}" y1="{y_top:.1f}" x2="{cx:.1f}" y2="{y_bot:.1f}" stroke="{c}" stroke-width="{stroke_w}"/>',
        (
            f'<line x1="{cx - hw:.1f}" y1="{y_top:.1f}" x2="{cx + hw:.1f}" y2="{y_top:.1f}" '
            f'stroke="{c}" stroke-width="{stroke_w}"/>'
        ),
        (
            f'<line x1="{cx - hw:.1f}" y1="{y_bot:.1f}" x2="{cx + hw:.1f}" y2="{y_bot:.1f}" '
            f'stroke="{c}" stroke-width="{stroke_w}"/>'
        ),
    ]
    return "".join(parts)


def draw_jittered_points(
    cx: float,
    ys,
    col_w: float,
    pal: dict | None = None,
    seed: int = 0,
    r: float = 2.4,
    alpha: float = 0.55,
    color: str | None = None,
) -> str:
    """Column of ``len(ys)`` dots jittered ±col_w/5 around ``cx``. Deterministic via ``seed``."""
    pal = pal or {}
    base_color = color or pal.get("ink", "rgba(28,28,26,1)")
    fill = f"{_rgb_prefix(base_color)}{alpha})"
    stroke = pal.get("ink6", "rgba(28,28,26,0.6)")
    rng = random.Random(seed)
    span = col_w / 5.0
    parts = []
    for y in ys:
        dx = (rng.random() - 0.5) * 2 * span
        parts.append(
            f'<circle cx="{cx + dx:.2f}" cy="{y:.2f}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="0.6"/>'
        )
    return "".join(parts)


def draw_scatter_point(
    cx: float,
    cy: float,
    pal: dict | None = None,
    *,
    r: float = 3.0,
    fill_color: str | None = None,
    fill_opacity: float = 0.78,
    stroke_width: float | None = None,
    stroke_color: str | None = None,
    stroke_opacity: float = 1.0,
    n_points_hint: int = 100,
    use_white_stroke: bool = False,
) -> str:
    """Journal-grade scatter point: half-transparent fill + darker same-hue stroke."""
    pal = pal or {}
    fill = fill_color or pal.get("accent", "rgba(163,88,50,1)")

    if use_white_stroke:
        stroke_color = "#FFFFFF"
        if stroke_width is None:
            stroke_width = 0.4
    else:
        # Auto stroke color: HSL lightness -25% (bounded ≥ 0.1), hue/sat preserved.
        if stroke_color is None:
            fr, fg, fb = _rgb_tuple(fill)
            h, l, s = _rgb_to_hls(fr, fg, fb)
            l_new = max(l - 0.25, 0.1)
            stroke_color = _hls_to_rgba(h, l_new, s, 1.0)

        if stroke_width is None:
            stroke_width = 0.6 if n_points_hint < 200 else 0.4

    fill_rgba = f"{_rgb_prefix(fill)}{fill_opacity})"
    stroke_rgba = (
        f"{_rgb_prefix(stroke_color)}{stroke_opacity})"
        if (stroke_opacity < 1.0 and not use_white_stroke)
        else stroke_color
    )
    return (
        f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r}" '
        f'fill="{fill_rgba}" stroke="{stroke_rgba}" stroke-width="{stroke_width}"/>'
    )


def draw_sig_bracket(
    x1: float,
    x2: float,
    y_top: float,
    label: str,
    pal: dict | None = None,
    fs: float = 14.0,
    tick_h: float = 6.0,
    color: str | None = None,
) -> str:
    """Inter-group significance bracket with text label. ``y_top`` is the top of the bracket."""
    pal = pal or {}
    c = color or pal.get("ink", "rgba(28,28,26,1)")
    xc = (x1 + x2) * 0.5
    d = f"M {x1:.1f} {y_top + tick_h:.1f} L {x1:.1f} {y_top:.1f} L {x2:.1f} {y_top:.1f} L {x2:.1f} {y_top + tick_h:.1f}"
    parts = [
        f'<path d="{d}" fill="none" stroke="{c}" stroke-width="1.2"/>',
        (
            f'<text x="{xc:.1f}" y="{y_top - 4:.1f}" font-size="{max(13.0, fs):.1f}" '
            f'fill="{c}" text-anchor="middle">{_xesc(label)}</text>'
        ),
    ]
    return "".join(parts)


def sig_marker(p: float) -> str:
    """Translate P-value to conventional star notation. Thresholds 0.05 / 0.01 / 0.001."""
    if p is None or not math.isfinite(p):
        return "ns"
    if p < 0.001:
        return "***"
    if p < 0.01:
        return "**"
    if p < 0.05:
        return "*"
    return "ns"


# 2b. Pairwise statistical tests (pure stdlib)
def _normal_sf(z: float) -> float:
    """One-tailed survival function for standard normal via erfc."""
    return 0.5 * math.erfc(z / math.sqrt(2))


def _betainc_approx(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta I_x(a,b) via continued-fraction expansion (Numerical Recipes / Lentz-style)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    # log B(a,b) * x^a * (1-x)^b
    lnbt = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1.0 - x)
    # Choose which side of the continued fraction converges faster. Standard trick: if x > (a+1)/(a+b+2), use the
    # symmetry I_x(a,b) = 1 - I_{1-x}(b,a).
    if x > (a + 1.0) / (a + b + 2.0):
        return 1.0 - _betainc_approx(b, a, 1.0 - x)
    EPS = 1e-12
    MAX_ITER = 300
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < EPS:
        d = EPS
    d = 1.0 / d
    h = d
    for m in range(1, MAX_ITER + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < EPS:
            d = EPS
        c = 1.0 + aa / c
        if abs(c) < EPS:
            c = EPS
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < EPS:
            d = EPS
        c = 1.0 + aa / c
        if abs(c) < EPS:
            c = EPS
        d = 1.0 / d
        de = d * c
        h *= de
        if abs(de - 1.0) < EPS:
            break
    return math.exp(lnbt) * h / a


def _student_t_sf(t: float, df: float) -> float:
    """One-tailed survival P(T > t) for Student's t with df degrees of freedom."""
    if t <= 0.0:
        # Symmetry: P(T > -|t|) = 1 - P(T > |t|).
        return 1.0 - _student_t_sf(-t, df) if t < 0.0 else 0.5
    if df <= 0.0:
        return 1.0
    x = df / (df + t * t)
    return 0.5 * _betainc_approx(df / 2.0, 0.5, x)


def student_t_critical(df: float, confidence: float = 0.95) -> float:
    """Two-sided Student-t critical value, without a runtime statistics dependency."""
    if not math.isfinite(df) or df <= 0 or not 0 < confidence < 1:
        raise ValueError("positive finite degrees of freedom and 0 < confidence < 1 are required")
    target = (1.0 - confidence) / 2.0
    low, high = 0.0, 1.0
    while _student_t_sf(high, df) > target:
        high *= 2.0
    for _ in range(60):
        middle = (low + high) / 2.0
        if _student_t_sf(middle, df) > target:
            low = middle
        else:
            high = middle
    return (low + high) / 2.0


def _scaled_stat_groups(a, b):
    """Common affine normalization for dimensionless tests and effect sizes."""
    values = [float(v) for v in (*a, *b)]
    if not values or any(not math.isfinite(v) for v in values):
        raise ValueError("statistical samples must contain finite values")
    anchor = values[0]
    shifted = [v - anchor for v in values]
    if any(not math.isfinite(v) for v in shifted):
        maximum = max(abs(v) for v in values)
        shifted = [v / maximum - anchor / maximum for v in values]
    scale = max(abs(v) for v in shifted)
    normalized = [v / scale for v in shifted] if scale else shifted
    return normalized[: len(a)], normalized[len(a) :]


def _welch_t_test(a, b) -> float:
    """Welch's unequal-variances two-sample t-test. Returns two-sided p-value."""
    n1, n2 = len(a), len(b)
    if n1 < 2 or n2 < 2:
        return 1.0
    a, b = _scaled_stat_groups(a, b)
    m1 = sum(a) / n1
    m2 = sum(b) / n2
    v1 = sum((x - m1) ** 2 for x in a) / (n1 - 1)
    v2 = sum((x - m2) ** 2 for x in b) / (n2 - 1)
    if v1 == 0.0 and v2 == 0.0:
        return 1.0 if m1 == m2 else 0.0
    se = math.sqrt(v1 / n1 + v2 / n2)
    if se == 0.0:
        return 1.0 if m1 == m2 else 0.0
    t = (m1 - m2) / se
    num = (v1 / n1 + v2 / n2) ** 2
    den = (v1 / n1) ** 2 / (n1 - 1) + (v2 / n2) ** 2 / (n2 - 1)
    if den <= 0.0:
        return 1.0
    df = num / den
    return _student_t_sf(abs(t), df) * 2.0


def _student_t_test(a, b) -> float:
    """Student's equal-variances two-sample t-test. Returns two-sided p-value."""
    n1, n2 = len(a), len(b)
    if n1 < 2 or n2 < 2:
        return 1.0
    a, b = _scaled_stat_groups(a, b)
    m1 = sum(a) / n1
    m2 = sum(b) / n2
    v1 = sum((x - m1) ** 2 for x in a) / (n1 - 1)
    v2 = sum((x - m2) ** 2 for x in b) / (n2 - 1)
    if v1 == 0.0 and v2 == 0.0:
        return 1.0 if m1 == m2 else 0.0
    df = n1 + n2 - 2
    sp2 = ((n1 - 1) * v1 + (n2 - 1) * v2) / df
    se = math.sqrt(sp2 * (1.0 / n1 + 1.0 / n2))
    if se == 0.0:
        return 1.0 if m1 == m2 else 0.0
    t = (m1 - m2) / se
    return _student_t_sf(abs(t), df) * 2.0


def _mann_whitney_u(a, b) -> float:
    """Mann-Whitney U test (two-sided)."""
    n1, n2 = len(a), len(b)
    if n1 < 1 or n2 < 1:
        return 1.0
    combined = [(float(v), "a") for v in a] + [(float(v), "b") for v in b]
    combined.sort(key=lambda t: t[0])
    ranks = [0.0] * len(combined)
    i = 0
    while i < len(combined):
        j = i
        while j < len(combined) and combined[j][0] == combined[i][0]:
            j += 1
        avg_rank = (i + j + 1) / 2.0  # 1-based ranks
        for k in range(i, j):
            ranks[k] = avg_rank
        i = j
    r_a = sum(ranks[k] for k, (_, g) in enumerate(combined) if g == "a")
    u1 = r_a - n1 * (n1 + 1) / 2.0
    mu = n1 * n2 / 2.0
    n = n1 + n2
    i = 0
    tie_sum = 0.0
    while i < len(combined):
        j = i
        while j < len(combined) and combined[j][0] == combined[i][0]:
            j += 1
        t = j - i
        if t > 1:
            tie_sum += t**3 - t
        i = j
    sigma2 = n1 * n2 * (n + 1) / 12.0
    if n > 1:
        sigma2 -= n1 * n2 * tie_sum / (12.0 * n * (n - 1))
    if sigma2 <= 0.0:
        return 1.0
    sigma = math.sqrt(sigma2)
    diff = u1 - mu
    if diff > 0.5:
        z = (diff - 0.5) / sigma
    elif diff < -0.5:
        z = (diff + 0.5) / sigma
    else:
        z = 0.0
    return _normal_sf(abs(z)) * 2.0


def sensible_pairs(n_g: int):
    """Return pairwise index tuples for ``n_g`` groups under the "sensible"
    strategy: all adjacent ``(i, i+1)``, plus a *control vs far* pair
    ``(0, n_g-1)`` when ``n_g >= 3``, plus ``(0, n_g//2)`` when ``n_g >= 5``.

    Returns a list of ``(i, j)`` index tuples (no p-values). De-duplicated,
    stable order."""
    if n_g < 2:
        return []
    pairs = []
    seen = set()
    for i in range(n_g - 1):
        pairs.append((i, i + 1))
        seen.add((i, i + 1))
    if n_g >= 3 and (0, n_g - 1) not in seen:
        pairs.append((0, n_g - 1))
        seen.add((0, n_g - 1))
    if n_g >= 5 and (0, n_g // 2) not in seen:
        pairs.append((0, n_g // 2))
        seen.add((0, n_g // 2))
    return pairs


_PAIRWISE_TESTS = {
    "welch": _welch_t_test,
    "student": _student_t_test,
    "mann_whitney": _mann_whitney_u,
}


def pairwise_test(groups_values, method: str = "welch", pair_strategy="sensible"):
    """Run a pairwise statistical test over multiple groups of samples."""
    if method not in _PAIRWISE_TESTS:
        raise ValueError(f"method must be one of {list(_PAIRWISE_TESTS)}, got {method!r}")
    n_g = len(groups_values)
    if pair_strategy == "all":
        pairs = [(i, j) for i in range(n_g) for j in range(i + 1, n_g)]
    elif pair_strategy == "sensible":
        pairs = sensible_pairs(n_g)
    elif isinstance(pair_strategy, (list, tuple)):
        pairs = list(pair_strategy)
    else:
        raise ValueError(f"pair_strategy must be 'sensible'/'all' or list of (i,j), got {pair_strategy!r}")
    test_fn = _PAIRWISE_TESTS[method]
    return [(i, j, test_fn(groups_values[i], groups_values[j])) for (i, j) in pairs]


# 3. Fit / stats
def draw_fit_line(
    points,
    pal: dict | None = None,
    color: str | None = None,
    stroke_w: float = 2.0,
    dash: str | None = None,
) -> str:
    """Fit line through screen-coord ``points``. ``dash`` → stroke-dasharray value."""
    pal = pal or {}
    c = color or pal.get("accent", "rgba(163,88,50,1)")
    d = " ".join(f"{'M' if i == 0 else 'L'} {x:.1f} {y:.1f}" for i, (x, y) in enumerate(points))
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<path d="{d}" fill="none" stroke="{c}" stroke-width="{stroke_w}"{dash_attr}/>'


def draw_stats_box(
    x: float,
    y: float,
    stats,
    pal: dict | None = None,
    fs: float = 14.0,
    anchor: str = "start",
    *,
    bold_values: bool = True,
    show_panel: bool = True,
    panel_alpha: float = 0.9,
    panel_pad_x: float = 12.0,
    panel_pad_y: float = 8.0,
    panel_color: str | None = None,
    label_sep: float = 14.0,
    font_family: str | None = None,
    accent_bar: bool = True,
    tabular_nums: bool = True,
):
    """Journal-grade stats summary chip (R² / P / n / slope / RMSE ...)."""
    pal = pal or {}
    ink = pal.get("ink", "rgba(28,28,26,1)")
    ink6 = pal.get("ink6", "rgba(28,28,26,0.6)")
    bg = pal.get("bg", "rgba(255,255,255,1)")
    accent = pal.get("accent", "rgba(163,88,50,1)")
    # Clamp fs to ensure readability at embed scale.
    fs = max(13.0, float(fs))
    line_h = fs * 1.35

    # Two-column widths: left column = labels (regular), right column = values (bold).
    max_label_w = 0.0
    max_value_w = 0.0
    for lab, val in stats:
        lw = _estimate_label_width_px(str(lab), fs, bold=False, font_family=font_family)
        vw = _estimate_label_width_px(str(val), fs, bold=bold_values, font_family=font_family)
        max_label_w = max(max_label_w, lw)
        max_value_w = max(max_value_w, vw)

    bar_w = 2.0 if accent_bar else 0.0
    # inner content width + horizontal padding on both sides + accent-bar strip
    panel_w = max_label_w + label_sep + max_value_w + panel_pad_x * 2 + bar_w
    panel_h = max(1, len(stats)) * line_h + panel_pad_y * 2

    # Panel x placement respects anchor as before: ``x`` is the *attachment point* the caller supplied (e.g.
    # plot_x_right - 10 with anchor="end").
    if anchor == "end":
        px = x - panel_w + panel_pad_x
    elif anchor == "middle":
        px = x - panel_w * 0.5
    else:
        px = x - panel_pad_x
    py = y

    parts = []
    if show_panel:
        panel_c = panel_color if panel_color is not None else bg
        panel_fill = f"{_rgb_prefix(panel_c)}{panel_alpha})"
        parts.append(
            f'<rect x="{px:.1f}" y="{py:.1f}" width="{panel_w:.1f}" height="{panel_h:.1f}" '
            f'fill="{panel_fill}" stroke="none" rx="3"/>'
        )
    if accent_bar:
        parts.append(
            f'<rect x="{px:.1f}" y="{py:.1f}" width="{bar_w:.1f}" height="{panel_h:.1f}" '
            f'fill="{accent}" stroke="none"/>'
        )

    # Column anchors (fixed inside the panel):
    #   label_x = panel left + bar + pad_x  (anchor="start")
    #   value_x = panel right - pad_x       (anchor="end")
    label_x = px + bar_w + panel_pad_x
    value_x = px + panel_w - panel_pad_x
    val_weight = ' font-weight="600"' if bold_values else ""
    tnum_attr = ' font-feature-settings="tnum"' if tabular_nums else ""

    for i, (lab, val) in enumerate(stats):
        y_line = py + panel_pad_y + fs * 0.95 + i * line_h
        parts.append(
            f'<text x="{label_x:.1f}" y="{y_line:.1f}" text-anchor="start" '
            f'font-size="{fs}" fill="{ink6}">{_xesc(str(lab))}</text>'
        )
        parts.append(
            f'<text x="{value_x:.1f}" y="{y_line:.1f}" text-anchor="end" '
            f'font-size="{fs}" fill="{ink}"{val_weight}{tnum_attr}>{_xesc(str(val))}</text>'
        )

    bbox = (px, py, px + panel_w, py + panel_h)
    return "".join(parts), bbox


def draw_label_with_halo(
    x,
    y,
    text,
    pal,
    *,
    fs=14,
    anchor="start",
    color=None,
    halo_color=None,
    halo_alpha=0.78,
    halo_pad_x=4,
    halo_pad_y=2,
    bold=False,
    italic=False,
    font_family=None,
):
    """Text label with a translucent halo rectangle underneath."""
    pal = pal or {}
    fs = float(fs)
    if color is None:
        if _is_dark_palette(pal):
            color = pal.get("ink_fg", pal.get("ink", "rgba(240,235,222,1)"))
        else:
            color = pal.get("ink", "rgba(28,28,26,1)")
    if halo_color is None:
        halo_color = pal.get("bg", "rgba(250,248,242,1)")
    # width estimate (depends on bold / font_family)
    est_w = _estimate_label_width_px(text, fs, letter_spacing_em=0, bold=bold, font_family=font_family)
    if anchor == "middle":
        rx = x - est_w * 0.5 - halo_pad_x
    elif anchor == "end":
        rx = x - est_w - halo_pad_x
    else:  # start
        rx = x - halo_pad_x
    rw = est_w + halo_pad_x * 2
    ry = y - fs * 0.82 - halo_pad_y
    rh = fs * 1.05 + halo_pad_y * 2
    halo_fill = f"{_rgb_prefix(halo_color)}{halo_alpha})"
    style_attrs = []
    if bold:
        style_attrs.append('font-weight="600"')
    if italic:
        style_attrs.append('font-style="italic"')
    if font_family:
        style_attrs.append(f'font-family="{font_family}"')
    style_str = (" " + " ".join(style_attrs)) if style_attrs else ""
    parts = [
        f'<rect x="{rx:.1f}" y="{ry:.1f}" width="{rw:.1f}" height="{rh:.1f}" fill="{halo_fill}" rx="2"/>',
        (
            f'<text x="{x:.1f}" y="{y:.1f}" font-size="{fs}" fill="{color}" '
            f'text-anchor="{anchor}"{style_str}>{_xesc(text)}</text>'
        ),
    ]
    return "".join(parts)


# 4. Reference line / threshold
def draw_reference_line(
    x_or_y: float,
    start: float,
    end: float,
    pal: dict | None = None,
    orient: str = "vertical",
    dash: str = "4 4",
    color: str | None = None,
    label: str | None = None,
    label_fs: float = 14.0,
    label_anchor: str = "start",
) -> str:
    """Dashed reference line (threshold / baseline) with optional label."""
    pal = pal or {}
    c = color or pal.get("ink4", "rgba(28,28,26,0.4)")
    fs = max(13.0, label_fs)
    if orient == "vertical":
        parts = [
            (
                f'<line x1="{x_or_y:.1f}" y1="{start:.1f}" x2="{x_or_y:.1f}" y2="{end:.1f}" '
                f'stroke="{c}" stroke-width="1" stroke-dasharray="{dash}"/>'
            )
        ]
        if label:
            parts.append(
                f'<text x="{x_or_y + 4:.1f}" y="{min(start, end) + fs:.1f}" '
                f'font-size="{fs}" fill="{c}" text-anchor="{label_anchor}">{_xesc(label)}</text>'
            )
    else:
        parts = [
            (
                f'<line x1="{start:.1f}" y1="{x_or_y:.1f}" x2="{end:.1f}" y2="{x_or_y:.1f}" '
                f'stroke="{c}" stroke-width="1" stroke-dasharray="{dash}"/>'
            )
        ]
        if label:
            parts.append(
                f'<text x="{max(start, end) - 4:.1f}" y="{x_or_y - 4:.1f}" '
                f'font-size="{fs}" fill="{c}" text-anchor="end">{_xesc(label)}</text>'
            )
    return "".join(parts)


# 5. Colorbar / color mapping
def _mix_rgb(c1, c2, t):
    r1, g1, b1 = _rgb_tuple(c1)
    r2, g2, b2 = _rgb_tuple(c2)
    return (
        int(r1 + (r2 - r1) * t),
        int(g1 + (g2 - g1) * t),
        int(b1 + (b2 - b1) * t),
    )


def value_to_color(
    v: float,
    v_min: float,
    v_max: float,
    pal: dict | None = None,
    log: bool = False,
    stops=None,
) -> str:
    """Map scalar ``v`` → ``rgba(...)``."""
    pal = pal or {}
    if log:
        if not all(math.isfinite(value) and value > 0 for value in (v, v_min, v_max)):
            raise ValueError("log colors require positive finite values")
        v_eff, lo, hi = (math.log10(value) for value in (v, v_min, v_max))
    else:
        v_eff, lo, hi = v, v_min, v_max
    t = 0.5 if hi == lo else max(0.0, min(1.0, (v_eff - lo) / (hi - lo)))
    if stops:
        if len(stops) == 1:
            return stops[0]
        pos = t * (len(stops) - 1)
        i = int(pos)
        if i >= len(stops) - 1:
            return stops[-1]
        f = pos - i
        r, g, b = _mix_rgb(stops[i], stops[i + 1], f)
    else:
        base = pal.get("accent", "rgba(163,88,50,1)")
        bg = pal.get("bg", "rgba(255,255,255,1)")
        r, g, b = _mix_rgb(bg, base, t)
    return f"rgba({r},{g},{b},1)"


def draw_colorbar(
    x: float,
    y: float,
    w: float,
    h: float,
    v_min: float,
    v_max: float,
    pal: dict | None = None,
    unit: str = "",
    log: bool = False,
    orient: str = "horizontal",
    stops=None,
    fs_tick: float = 13.0,
    title: str | None = None,
    n_bands: int = 32,
) -> str:
    """Draw a horizontal or vertical colorbar."""
    pal = pal or {}
    ink = pal.get("ink", "rgba(28,28,26,1)")
    fs = max(13.0, fs_tick)
    parts = []
    for i in range(n_bands):
        t_lo = i / n_bands
        t_hi = (i + 1) / n_bands
        if log:
            lv = 10.0 ** (math.log10(v_min) + (math.log10(v_max) - math.log10(v_min)) * (t_lo + t_hi) * 0.5)
        else:
            lv = v_min + (v_max - v_min) * (t_lo + t_hi) * 0.5
        c = value_to_color(lv, v_min, v_max, pal, log=log, stops=stops)
        if orient == "horizontal":
            bx = x + w * t_lo
            bw = w / n_bands + 0.5
            parts.append(f'<rect x="{bx:.2f}" y="{y:.1f}" width="{bw:.2f}" height="{h:.1f}" fill="{c}"/>')
        else:
            by = y + h - h * t_hi
            bh = h / n_bands + 0.5
            parts.append(f'<rect x="{x:.1f}" y="{by:.2f}" width="{w:.1f}" height="{bh:.2f}" fill="{c}"/>')
    parts.append(
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="none" stroke="{ink}" stroke-width="1"/>'
    )
    if log and v_min != v_max:
        decades, _, _ = log_axis(v_min, v_max)
        decades = [k for k in decades if -323 <= k <= 308 and v_min <= 10.0**k <= v_max]
        available = w if orient == "horizontal" else h
        max_labels = max(2, int(available / (fs * (5.0 if orient == "horizontal" else 1.8))))
        if len(decades) > max_labels:
            decades = [decades[round(i * (len(decades) - 1) / (max_labels - 1))] for i in range(max_labels)]
        for k in decades:
            v = 10**k
            if v < v_min or v > v_max:
                continue
            if orient == "horizontal":
                tx = _log_lin(v, v_min, v_max, x, x + w)
                parts.append(
                    f'<line x1="{tx:.1f}" y1="{y + h:.1f}" x2="{tx:.1f}" y2="{y + h + 4:.1f}" '
                    f'stroke="{ink}" stroke-width="1"/>'
                )
                parts.append(
                    f'<text x="{tx:.1f}" y="{y + h + fs + 6:.1f}" font-size="{fs}" '
                    f'fill="{ink}" text-anchor="middle">10'
                    f'<tspan font-size="{fs * 0.7:.1f}" baseline-shift="super">{int(k)}</tspan></text>'
                )
            else:
                ty = _log_lin(v, v_min, v_max, y + h, y)
                parts.append(
                    f'<line x1="{x + w:.1f}" y1="{ty:.1f}" x2="{x + w + 4:.1f}" y2="{ty:.1f}" '
                    f'stroke="{ink}" stroke-width="1"/>'
                )
                parts.append(
                    f'<text x="{x + w + 6:.1f}" y="{ty + fs * 0.35:.1f}" font-size="{fs}" '
                    f'fill="{ink}" text-anchor="start">10'
                    f'<tspan font-size="{fs * 0.7:.1f}" baseline-shift="super">{int(k)}</tspan></text>'
                )
    else:
        ticks = [v_min] if v_min == v_max else nice_axis(v_min, v_max, 4)[0]
        span = v_max - v_min
        tolerance = max(abs(span) * 1e-12, math.ulp(v_min), math.ulp(v_max))
        tick_labels = _tick_label_map(ticks, span)
        for v in ticks:
            if v < v_min - tolerance or v > v_max + tolerance:
                continue
            if orient == "horizontal":
                tx = _lin(v, v_min, v_max, x, x + w)
                parts.append(
                    f'<line x1="{tx:.1f}" y1="{y + h:.1f}" x2="{tx:.1f}" y2="{y + h + 4:.1f}" '
                    f'stroke="{ink}" stroke-width="1"/>'
                )
                parts.append(
                    f'<text x="{tx:.1f}" y="{y + h + fs + 6:.1f}" font-size="{fs}" '
                    f'fill="{ink}" text-anchor="middle">'
                    f"{_xesc(tick_labels[v])}</text>"
                )
            else:
                ty = _lin(v, v_min, v_max, y + h, y)
                parts.append(
                    f'<line x1="{x + w:.1f}" y1="{ty:.1f}" x2="{x + w + 4:.1f}" y2="{ty:.1f}" '
                    f'stroke="{ink}" stroke-width="1"/>'
                )
                parts.append(
                    f'<text x="{x + w + 6:.1f}" y="{ty + fs * 0.35:.1f}" font-size="{fs}" '
                    f'fill="{ink}" text-anchor="start">'
                    f"{_xesc(tick_labels[v])}</text>"
                )
    if title or unit:
        label_txt = " / ".join(s for s in (title, unit) if s)
        if orient == "horizontal":
            parts.append(
                f'<text x="{x:.1f}" y="{y - 6:.1f}" font-size="{fs}" '
                f'fill="{ink}" font-weight="600">{_xesc(label_txt)}</text>'
            )
        else:
            parts.append(
                f'<text x="{x + w * 0.5:.1f}" y="{y - 6:.1f}" font-size="{fs}" '
                f'fill="{ink}" font-weight="600" text-anchor="middle">{_xesc(label_txt)}</text>'
            )
    return "".join(parts)


def draw_axis_arrow(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    pal: dict | None = None,
    label: str | None = None,
    label_fs: float = 14.0,
    head_size: float = 8.0,
    color: str | None = None,
) -> str:
    """UMAP-style arrow axis with optional end label (e.g. "UMAP 1 →")."""
    pal = pal or {}
    c = color or pal.get("ink", "rgba(28,28,26,1)")
    fs = max(13.0, label_fs)
    parts = [f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{c}" stroke-width="1.4"/>']
    dx = x2 - x1
    dy = y2 - y1
    L = math.hypot(dx, dy) or 1.0
    ux, uy = dx / L, dy / L
    px, py = -uy, ux
    hx = x2 - ux * head_size
    hy = y2 - uy * head_size
    pts = [
        (x2, y2),
        (hx + px * head_size * 0.45, hy + py * head_size * 0.45),
        (hx - px * head_size * 0.45, hy - py * head_size * 0.45),
    ]
    poly = " ".join(f"{p[0]:.1f},{p[1]:.1f}" for p in pts)
    parts.append(f'<polygon points="{poly}" fill="{c}" stroke="none"/>')
    if label:
        # place along the arrow near the end, offset perpendicular
        lx = x1 + (x2 - x1) * 0.5
        ly = y1 + (y2 - y1) * 0.5
        # offset below if horizontal, left if vertical
        if abs(ux) > abs(uy):  # mostly horizontal
            ly_off = ly + fs + 6
            parts.append(
                f'<text x="{lx:.1f}" y="{ly_off:.1f}" font-size="{fs}" fill="{c}" '
                f'text-anchor="middle" font-weight="600">{_xesc(label)}</text>'
            )
        else:
            lx_off = lx - 8
            parts.append(
                f'<text x="{lx_off:.1f}" y="{ly:.1f}" font-size="{fs}" fill="{c}" '
                f'text-anchor="middle" font-weight="600" '
                f'transform="rotate(-90 {lx_off:.1f} {ly:.1f})">{_xesc(label)}</text>'
            )
    return "".join(parts)


# 6. Decorative labels
def draw_n_label(x: float, y: float, n: int, pal: dict | None = None, fs: float = 14.0, anchor: str = "start") -> str:
    """Draw a single "n = NN" label."""
    pal = pal or {}
    ink6 = pal.get("ink6", "rgba(28,28,26,0.6)")
    fs = max(13.0, fs)
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-size="{fs}" fill="{ink6}" '
        f'text-anchor="{anchor}" font-style="italic">n = {int(n)}</text>'
    )


def draw_censor_tick(x: float, y: float, pal: dict | None = None, h: float = 6.0, color: str | None = None) -> str:
    """KM-plot right-censored tick: short vertical mark through a step line."""
    pal = pal or {}
    c = color or pal.get("ink", "rgba(28,28,26,1)")
    return (
        f'<line x1="{x:.1f}" y1="{y - h * 0.5:.1f}" x2="{x:.1f}" y2="{y + h * 0.5:.1f}" '
        f'stroke="{c}" stroke-width="1.4"/>'
    )


def draw_at_risk_table(
    x_left: float,
    x_right: float,
    y_top: float,
    times,
    counts,
    group_names,
    pal: dict | None = None,
    fs: float = 14.0,
    row_h: float = 22.0,
    t_min: float | None = None,
    t_max: float | None = None,
    font_family: str | None = None,
) -> str:
    """Kaplan-Meier at-risk table."""
    pal = pal or {}
    ink = pal.get("ink", "rgba(28,28,26,1)")
    ink6 = pal.get("ink6", "rgba(28,28,26,0.6)")
    ink1 = pal.get("ink1", "rgba(28,28,26,0.12)")
    fs = max(13.0, fs)
    if t_min is None:
        t_min = min(times) if times else 0
    if t_max is None:
        t_max = max(times) if times else 1
    # left margin: widest group name + room for the half-width of the leftmost
    # (middle-anchored) count cell + a visual gap. Without the half-count term
    # a long group name ("Placebo (long name)") butts up against the first
    # count value ("80") when font-size grows.
    name_w_text = max(
        (_estimate_label_width_px(g, fs, font_family=font_family) for g in group_names),
        default=50,
    )
    # Estimate the leftmost count column width using the widest count across all
    # rows (fall back to 3-digit worst case if counts not supplied yet).
    try:
        max_count_str = str(max((row[0] for row in counts if row), default=99))
    except (ValueError, TypeError, IndexError):
        max_count_str = "999"
    first_count_half_w = _estimate_label_width_px(max_count_str, fs, font_family=font_family) * 0.5
    name_w = name_w_text + first_count_half_w + 18
    data_left = x_left + name_w
    parts = []
    parts.append(
        f'<text x="{x_left:.1f}" y="{y_top:.1f}" font-size="{fs}" fill="{ink}" font-weight="600">{_xesc(tr("No. at risk"))}</text>'
    )
    y_rows_top = y_top + row_h * 0.5
    parts.append(
        f'<line x1="{x_left:.1f}" y1="{y_rows_top:.1f}" x2="{x_right:.1f}" y2="{y_rows_top:.1f}" '
        f'stroke="{ink1}" stroke-width="1"/>'
    )
    for ri, (gname, row) in enumerate(zip(group_names, counts)):
        y = y_rows_top + row_h * (ri + 1)
        parts.append(f'<text x="{x_left:.1f}" y="{y:.1f}" font-size="{fs}" fill="{ink6}">{_xesc(gname)}</text>')
        for ti, (t, c) in enumerate(zip(times, row)):
            if t_max > t_min:
                tx = _lin(t, t_min, t_max, data_left, x_right)
            else:
                tx = data_left + ti * (x_right - data_left) / max(1, len(times) - 1)
            parts.append(
                f'<text x="{tx:.1f}" y="{y:.1f}" font-size="{fs}" fill="{ink}" text-anchor="middle">{int(c)}</text>'
            )
    return "".join(parts)


# 10. Multi-subplot layout primitives
# Minimum (W, H) required for a template to render without overcrowding.
_TEMPLATE_MIN_SIZE = {
    "top_bottom_3to1": (700, 520),
    "top_bottom_2to1": (700, 520),  # same floor as 3to1; sub gets 1/3 instead of 1/4
    "top_bottom_1to1": (700, 700),  # equal split needs much more vertical room
    "left_right_3to1": (900, 480),
    "left_right_2to1": (900, 480),  # same floor; sub widens from 1/4 to 1/3
    "left_right_1to1": (900, 480),  # equal split keeps same floor (sub = main width)
    "marginal_cross": (780, 580),
    "inset": (780, 420),
}


def can_fit_multi(W: float, H: float, template: str) -> bool:
    """Return True if the plot box is large enough for the given multi template."""
    min_w, min_h = _TEMPLATE_MIN_SIZE.get(template, (0, 0))
    return W >= min_w and H >= min_h


def allocate_subplot_rects(
    plot_x_left: float,
    plot_x_right: float,
    plot_y_top: float,
    plot_y_bot: float,
    template: str,
    gutter_shared: float = 10.0,
    gutter_free: float = 28.0,
) -> dict:
    """Partition the plot box into ``main`` and ``sub`` rectangles."""
    W = plot_x_right - plot_x_left
    H = plot_y_bot - plot_y_top
    if template == "top_bottom_3to1":
        sub_h = (H - gutter_shared) * 0.25
        main_h = H - gutter_shared - sub_h
        return {
            "main": (plot_x_left, plot_x_right, plot_y_top, plot_y_top + main_h),
            "sub": (plot_x_left, plot_x_right, plot_y_top + main_h + gutter_shared, plot_y_bot),
        }
    if template == "top_bottom_2to1":
        sub_h = (H - gutter_shared) / 3.0
        main_h = H - gutter_shared - sub_h
        return {
            "main": (plot_x_left, plot_x_right, plot_y_top, plot_y_top + main_h),
            "sub": (plot_x_left, plot_x_right, plot_y_top + main_h + gutter_shared, plot_y_bot),
        }
    if template == "top_bottom_1to1":
        sub_h = (H - gutter_shared) * 0.5
        main_h = H - gutter_shared - sub_h
        return {
            "main": (plot_x_left, plot_x_right, plot_y_top, plot_y_top + main_h),
            "sub": (plot_x_left, plot_x_right, plot_y_top + main_h + gutter_shared, plot_y_bot),
        }
    if template == "left_right_3to1":
        sub_w = (W - gutter_free) * 0.25
        main_w = W - gutter_free - sub_w
        return {
            "main": (plot_x_left, plot_x_left + main_w, plot_y_top, plot_y_bot),
            "sub": (plot_x_left + main_w + gutter_free, plot_x_right, plot_y_top, plot_y_bot),
        }
    if template == "left_right_2to1":
        sub_w = (W - gutter_free) / 3.0
        main_w = W - gutter_free - sub_w
        return {
            "main": (plot_x_left, plot_x_left + main_w, plot_y_top, plot_y_bot),
            "sub": (plot_x_left + main_w + gutter_free, plot_x_right, plot_y_top, plot_y_bot),
        }
    if template == "left_right_1to1":
        sub_w = (W - gutter_free) * 0.5
        main_w = W - gutter_free - sub_w
        return {
            "main": (plot_x_left, plot_x_left + main_w, plot_y_top, plot_y_bot),
            "sub": (plot_x_left + main_w + gutter_free, plot_x_right, plot_y_top, plot_y_bot),
        }
    if template == "marginal_cross":
        top_h = (H - gutter_shared) * 0.18
        right_w = (W - gutter_shared) * 0.18
        return {
            "main": (
                plot_x_left,
                plot_x_right - right_w - gutter_shared,
                plot_y_top + top_h + gutter_shared,
                plot_y_bot,
            ),
            "top": (plot_x_left, plot_x_right - right_w - gutter_shared, plot_y_top, plot_y_top + top_h),
            "sub": (plot_x_right - right_w, plot_x_right, plot_y_top + top_h + gutter_shared, plot_y_bot),
        }
    if template == "inset":
        inset_w = W * 0.30
        inset_h = H * 0.30
        pad = 12
        return {
            "main": (plot_x_left, plot_x_right, plot_y_top, plot_y_bot),
            "sub": (plot_x_right - inset_w - pad, plot_x_right - pad, plot_y_top + pad, plot_y_top + pad + inset_h),
        }
    raise ValueError(f"Unknown multi template: {template!r}")


def resolve_multi_mode(
    requested: str,
    whitelist: dict,
    data_signals: dict,
    W: float,
    H: float,
) -> tuple:
    """Resolve ``multi_mode`` for a chart."""
    if requested is None or requested == "single":
        return (None, None)
    if requested == "auto":
        for mode, (template, trigger) in whitelist.items():
            if trigger(data_signals) and can_fit_multi(W, H, template):
                return (mode, template)
        return (None, None)
    if requested not in whitelist:
        raise ValueError(f"Unknown multi_mode {requested!r}. Allowed: {list(whitelist) + ['auto', 'single']}")
    template, _ = whitelist[requested]
    if not can_fit_multi(W, H, template):
        min_w, min_h = _TEMPLATE_MIN_SIZE[template]
        raise ValueError(
            f"multi_mode {requested!r} needs a plot area of at least {min_w} x {min_h}; received {W:g} x {H:g}"
        )
    return (requested, template)


def draw_zero_line(
    x_left: float,
    x_right: float,
    y: float,
    pal: dict | None = None,
    stroke_width: float = 1.0,
    dasharray: str = "4 4",
) -> str:
    """Horizontal zero/reference line for residual / diff subplots."""
    pal = pal or {}
    ink4 = pal.get("ink4", "rgba(28,28,26,0.35)")
    return (
        f'<line x1="{x_left:.1f}" y1="{y:.1f}" x2="{x_right:.1f}" y2="{y:.1f}" '
        f'stroke="{ink4}" stroke-width="{stroke_width}" stroke-dasharray="{dasharray}"/>'
    )


def draw_selection_box(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    pal: dict | None = None,
    stroke_width: float = 1.0,
) -> str:
    """Selection rectangle used by inset / zoom modes to mark the source region."""
    pal = pal or {}
    accent = pal.get("accent", "#D96A2E")
    x_lo, x_hi = min(x1, x2), max(x1, x2)
    y_lo, y_hi = min(y1, y2), max(y1, y2)
    return (
        f'<rect x="{x_lo:.1f}" y="{y_lo:.1f}" width="{(x_hi - x_lo):.1f}" '
        f'height="{(y_hi - y_lo):.1f}" fill="none" stroke="{accent}" '
        f'stroke-width="{stroke_width}" stroke-dasharray="3 3"/>'
    )


# 11. Phase-0 shared infrastructure for multi-figure composition
# These primitives standardize cross-panel contracts: bbox type, shared scale,
# shared series color/order, layout allocators (facet/tracks/sparkline), and
# protected-region overlap checks. Everything above (sections 1-10) remains
# untouched for backward compatibility with the already-completed charts.
from collections import namedtuple as _namedtuple

LayoutError = type("LayoutError", (ValueError,), {})

# Canonical bbox tuple: (x0, y0, x1, y1) with x0<=x1, y0<=y1.
BBox = _namedtuple("BBox", ["x0", "y0", "x1", "y1"])


def bbox_from_edges(x_left: float, x_right: float, y_top: float, y_bot: float) -> BBox:
    """Build a BBox from the legacy ``(x_left, x_right, y_top, y_bot)`` ordering used by subplot rects in section 10."""
    return BBox(min(x_left, x_right), min(y_top, y_bot), max(x_left, x_right), max(y_top, y_bot))


def bbox_to_edges(b: BBox) -> tuple:
    """Reverse of :func:`bbox_from_edges` — ``(x_left, x_right, y_top, y_bot)``."""
    return (b.x0, b.x1, b.y0, b.y1)


def bbox_width(b: BBox) -> float:
    return b.x1 - b.x0


def bbox_height(b: BBox) -> float:
    return b.y1 - b.y0


def bbox_intersect(a: BBox, b: BBox, tol: float = 0.0) -> bool:
    """Return True if two bboxes overlap by more than ``tol`` on both axes."""
    return not (a.x1 - tol < b.x0 or b.x1 - tol < a.x0 or a.y1 - tol < b.y0 or b.y1 - tol < a.y0)


def bbox_overlap_area(a: BBox, b: BBox) -> float:
    dx = max(0.0, min(a.x1, b.x1) - max(a.x0, b.x0))
    dy = max(0.0, min(a.y1, b.y1) - max(a.y0, b.y0))
    return dx * dy


class SharedScale:
    """Cross-panel coordinate domain + ticks + optional transform."""

    __slots__ = ("domain", "ticks", "transform")

    def __init__(self, domain, ticks=None, transform: str = "linear"):
        if domain is None or len(domain) != 2:
            raise ValueError("SharedScale: domain must be (v_min, v_max)")
        self.domain = (float(domain[0]), float(domain[1]))
        if not all(math.isfinite(value) for value in self.domain) or self.domain[0] > self.domain[1]:
            raise ValueError("SharedScale: bounds must be finite and ordered")
        self.ticks = list(ticks) if ticks is not None else None
        if transform not in ("linear", "log10"):
            raise ValueError(f"SharedScale: unknown transform {transform!r}")
        self.transform = transform
        if transform == "log10" and self.domain[0] <= 0:
            raise ValueError("SharedScale: log10 requires positive bounds")

    def map(self, v: float, p0: float, p1: float) -> float:
        """Map data value ``v`` → pixel in ``[p0, p1]``."""
        v_min, v_max = self.domain
        if self.transform == "log10":
            if not math.isfinite(v) or v <= 0:
                raise ValueError("SharedScale: log10 requires positive finite values")
            v, v_min, v_max = (math.log10(value) for value in (v, v_min, v_max))
        if v_max == v_min:
            return (p0 + p1) * 0.5
        return p0 + (v - v_min) / (v_max - v_min) * (p1 - p0)


class SeriesContext:
    """Cross-panel identity ↔ color/order/label mapping."""

    __slots__ = ("colors", "ids", "labels", "order")

    def __init__(self, ids, pal=None, order=None, labels=None, series_colors=None):
        self.ids = list(ids)
        self.order = list(order) if order is not None else list(ids)
        if series_colors is not None:
            if len(series_colors) != len(self.ids):
                raise ValueError("SeriesContext: series_colors length mismatch")
            self.colors = {sid: c for sid, c in zip(self.ids, series_colors)}
        elif pal is not None:
            from .._common import _derive_series_colors

            derived = _derive_series_colors(pal, len(self.ids))
            self.colors = {sid: c for sid, c in zip(self.ids, derived)}
        else:
            self.colors = {sid: "#4A7FA3" for sid in self.ids}
        self.labels = dict(labels) if labels else {sid: str(sid) for sid in self.ids}

    def color_of(self, sid) -> str:
        return self.colors.get(sid, self.colors[self.ids[0]] if self.ids else "#4A7FA3")

    def label_of(self, sid) -> str:
        return self.labels.get(sid, str(sid))


def allocate_main_sub(
    bbox: BBox,
    template: str,
    gutter_shared: float = 10.0,
    gutter_free: float = 28.0,
    protected: tuple = (),
) -> dict:
    """Canonical replacement for :func:`allocate_subplot_rects`."""
    rects = allocate_subplot_rects(
        bbox.x0,
        bbox.x1,
        bbox.y0,
        bbox.y1,
        template=template,
        gutter_shared=gutter_shared,
        gutter_free=gutter_free,
    )
    out = {}
    for k, (xl, xr, yt, yb) in rects.items():
        out[k] = BBox(xl, yt, xr, yb)
    return out


def allocate_facet_grid(
    bbox: BBox,
    n: int,
    cols: int | None = None,
    gutter: float = 24.0,
    min_cell: tuple = (220.0, 180.0),
) -> list:
    """Partition ``bbox`` into ``n`` equal cells."""
    if n <= 0:
        raise LayoutError("allocate_facet_grid: n must be positive")
    if cols is None:
        cols = max(1, math.ceil(math.sqrt(n)))
    rows = math.ceil(n / cols)
    W, H = bbox_width(bbox), bbox_height(bbox)
    cell_w = (W - gutter * (cols - 1)) / cols
    cell_h = (H - gutter * (rows - 1)) / rows
    if cell_w < min_cell[0] or cell_h < min_cell[1]:
        raise LayoutError(
            f"facet grid cell too small: {cell_w:.0f}x{cell_h:.0f}, need >= {min_cell[0]:.0f}x{min_cell[1]:.0f}"
        )
    cells = []
    for i in range(n):
        r, c = divmod(i, cols)
        x0 = bbox.x0 + c * (cell_w + gutter)
        y0 = bbox.y0 + r * (cell_h + gutter)
        cells.append(BBox(x0, y0, x0 + cell_w, y0 + cell_h))
    return cells


def allocate_tracks(
    bbox: BBox,
    weights,
    gutter: float = 6.0,
    orient: str = "v",
    min_track: float = 60.0,
) -> list:
    """Multi-track alignment layout."""
    if not weights:
        raise LayoutError("allocate_tracks: weights must be non-empty")
    w_total = float(sum(weights))
    if w_total <= 0:
        raise LayoutError("allocate_tracks: weights must sum to > 0")
    n = len(weights)
    if orient == "v":
        avail_h = bbox_height(bbox) - gutter * (n - 1)
        y = bbox.y0
        out = []
        for w in weights:
            h = avail_h * (w / w_total)
            if h < min_track:
                raise LayoutError(f"track too short: {h:.1f}, min {min_track:.1f}")
            out.append(BBox(bbox.x0, y, bbox.x1, y + h))
            y += h + gutter
        return out
    if orient == "h":
        avail_w = bbox_width(bbox) - gutter * (n - 1)
        x = bbox.x0
        out = []
        for w in weights:
            dw = avail_w * (w / w_total)
            if dw < min_track:
                raise LayoutError(f"track too narrow: {dw:.1f}, min {min_track:.1f}")
            out.append(BBox(x, bbox.y0, x + dw, bbox.y1))
            x += dw + gutter
        return out
    raise LayoutError(f"allocate_tracks: unknown orient {orient!r}")


def assert_no_overlap(
    new_bbox: BBox,
    protected: tuple,
    tol: float = 2.0,
    name: str = "sub-panel",
) -> None:
    """Raise :class:`LayoutError` if ``new_bbox`` overlaps any protected region"""
    for i, p in enumerate(protected):
        if bbox_intersect(new_bbox, p, tol=tol):
            raise LayoutError(f"{name} bbox {tuple(new_bbox)} overlaps protected region [{i}]={tuple(p)}")


def collect_protected_bboxes(parts: list) -> list:
    """Best-effort scan of already-emitted SVG fragments to extract bounding"""
    import re

    bboxes = []
    rect_re = re.compile(
        r'<rect[^>]*\sx="([-\d.]+)"[^>]*\sy="([-\d.]+)"[^>]*\swidth="([-\d.]+)"[^>]*\sheight="([-\d.]+)"'
    )
    for part in parts:
        if not isinstance(part, str):
            continue
        for m in rect_re.finditer(part):
            x = float(m.group(1))
            y = float(m.group(2))
            w = float(m.group(3))
            h = float(m.group(4))
            if w > 0 and h > 0:
                bboxes.append(BBox(x, y, x + w, y + h))
    return bboxes


def can_fit_multi_v2(bbox: BBox, template) -> bool:
    """Strict successor to :func:`can_fit_multi`."""
    if template is None:
        return bbox_width(bbox) >= 400.0 and bbox_height(bbox) >= 300.0
    if template not in _TEMPLATE_MIN_SIZE:
        raise ValueError(f"can_fit_multi_v2: unknown template {template!r}")
    min_w, min_h = _TEMPLATE_MIN_SIZE[template]
    return bbox_width(bbox) >= min_w and bbox_height(bbox) >= min_h


def resolve_multi_mode_v2(
    requested,
    whitelist: dict,
    data_signals: dict,
    bbox: BBox,
) -> tuple:
    """Enhanced ``resolve_multi_mode`` with."""
    if requested is None or requested in ("single", "off"):
        return (None, None, "")
    if requested == "auto":
        for mode, spec in whitelist.items():
            template = spec[0]
            trigger = spec[1] if len(spec) > 1 else (lambda s: True)
            validator = spec[2] if len(spec) > 2 else (lambda s: (True, ""))
            if not trigger(data_signals):
                continue
            ok, why = validator(data_signals)
            if not ok or not can_fit_multi_v2(bbox, template):
                continue
            return (mode, template, "")
        return (None, None, "auto: no mode matched signals")
    if requested not in whitelist:
        raise ValueError(f"Unknown multi_mode {requested!r}. Allowed: {list(whitelist) + ['auto', 'single', 'off']}")
    spec = whitelist[requested]
    template = spec[0]
    validator = spec[2] if len(spec) > 2 else (lambda s: (True, ""))
    ok, why = validator(data_signals)
    if not ok:
        raise ValueError(f"multi_mode {requested!r}: {why or 'invalid data for this mode'}")
    if not can_fit_multi_v2(bbox, template):
        minimum = _TEMPLATE_MIN_SIZE.get(template, (400.0, 300.0))
        raise ValueError(
            f"multi_mode {requested!r} needs a plot area of at least {minimum[0]:g} x {minimum[1]:g}; "
            f"received {bbox_width(bbox):g} x {bbox_height(bbox):g}"
        )
    return (requested, template, "")


def effect_size_cohens_d(a, b) -> tuple:
    """Hedges-correction-free Cohen's d with large-sample 95% CI."""
    n1, n2 = len(a), len(b)
    if n1 < 2 or n2 < 2:
        raise ValueError("Cohen's d requires at least two observations in each group")
    if any(not math.isfinite(float(v)) for v in (*a, *b)):
        raise ValueError("Cohen's d requires finite observations")
    a, b = _scaled_stat_groups(a, b)
    m1 = sum(a) / n1
    m2 = sum(b) / n2
    v1 = sum((x - m1) ** 2 for x in a) / (n1 - 1)
    v2 = sum((x - m2) ** 2 for x in b) / (n2 - 1)
    sp = math.sqrt(((n1 - 1) * v1 + (n2 - 1) * v2) / max(1, n1 + n2 - 2))
    if sp <= 0:
        raise ValueError("Cohen's d is undefined when pooled variance is zero")
    d = (m2 - m1) / sp
    se = math.hypot(math.sqrt((n1 + n2) / (n1 * n2)), d / math.sqrt(2 * (n1 + n2)))
    return (d, d - 1.96 * se, d + 1.96 * se)


def ecdf_points(values) -> list:
    """Return the step-function points ``[(v, F)]`` for the empirical CDF."""
    xs = sorted(float(v) for v in values)
    n = len(xs)
    if n == 0:
        return []
    out = []
    for i, v in enumerate(xs):
        out.append((v, (i + 1) / n))
    return out


def kernel_derivative(xs, ys, bw: float | None = None) -> list:
    """Smoothed finite-difference ∂y/∂x over the input series."""
    n = len(xs)
    if n < 2:
        return []
    # Simple centered differences, no smoothing when ``bw`` is None.
    out = []
    for i in range(n):
        if i == 0:
            dy = (ys[1] - ys[0]) / (xs[1] - xs[0] + 1e-12)
        elif i == n - 1:
            dy = (ys[n - 1] - ys[n - 2]) / (xs[n - 1] - xs[n - 2] + 1e-12)
        else:
            dy = (ys[i + 1] - ys[i - 1]) / (xs[i + 1] - xs[i - 1] + 1e-12)
        out.append((xs[i], dy))
    return out


def draw_source_marker(
    kind: str,
    pal: dict | None = None,
    **geom,
) -> str:
    """Return a short SVG fragment marking a region/line in the main panel"""
    pal = pal or {}
    accent = pal.get("accent", "#D96A2E")
    if kind == "vline":
        x = geom["x"]
        y0 = geom["y0"]
        y1 = geom["y1"]
        return (
            f'<line x1="{x:.1f}" y1="{y0:.1f}" x2="{x:.1f}" y2="{y1:.1f}" '
            f'stroke="{accent}" stroke-width="1.2" stroke-dasharray="4 4"/>'
        )
    if kind == "hline":
        y = geom["y"]
        x0 = geom["x0"]
        x1 = geom["x1"]
        return (
            f'<line x1="{x0:.1f}" y1="{y:.1f}" x2="{x1:.1f}" y2="{y:.1f}" '
            f'stroke="{accent}" stroke-width="1.2" stroke-dasharray="4 4"/>'
        )
    if kind == "box":
        return draw_selection_box(
            geom["x0"],
            geom["y0"],
            geom["x1"],
            geom["y1"],
            pal=pal,
        )
    if kind == "point":
        x = geom["x"]
        y = geom["y"]
        return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{accent}" stroke="white" stroke-width="1"/>'
    raise ValueError(f"draw_source_marker: unknown kind {kind!r}")


# Short slide canvases: margins sized from the text actually drawn
COMPACT_HEIGHT = 600.0


def compact_margins(
    fs: dict,
    *,
    title=None,
    subtitle=None,
    figure_label=None,
    footer: bool = False,
    foot_offset: float = 32.0,
    x_title: bool = True,
    y_title: bool = True,
    y_tick_w: float | None = None,
    top_extra: float = 0.0,
    bot_extra: float = 0.0,
) -> tuple[float, float, float]:
    """``(margin_top, margin_bot, margin_left)`` for the ``draw_x_axis``/``draw_y_axis`` layout."""
    tick = max(13.0, fs.get("ytick", 19.0))
    axis = max(13.0, fs.get("yaxis", tick))
    heads = [
        f
        for v, f in (
            (subtitle, fs.get("subtitle", 14) + 6),
            (title, fs.get("title", 22) + 8),
            (figure_label, fs.get("figure", 13) + 4),
        )
        if v
    ]
    top = (26 + sum(heads) if heads else tick * 0.55 + 26) + top_extra
    bot = (tick + axis * 1.25 + 28 if x_title else tick * 1.3 + 14) + bot_extra
    if footer:
        bot = max(bot + max(13.0, fs.get("foot", 13)) + 6, bot + foot_offset - 6)
    label_w = tick * 2.6 if y_tick_w is None else y_tick_w
    left = tick * 3.2 + axis * 0.85 + 8 if y_title else label_w + 14
    return top, bot, max(left, label_w + 14)


# Figure chrome shared by the single-canvas academic charts
def draw_canvas_bg(pal: dict, W: float, H: float) -> list:
    """Initial ``parts`` list: a full-canvas background rect when the palette has ``bg``."""
    if pal.get("bg"):
        return [f'<rect x="0" y="0" width="{W:.1f}" height="{H:.1f}" fill="{pal["bg"]}"/>']
    return []


def draw_title_block(
    x_left, anchor_y, width, *, title, subtitle, figure_label, pal, fs, body_font, heading_font
) -> str:
    """Title / subtitle / figure-label header using the chart's ``fs`` sizes and palette inks."""
    title_svg, _ = _render_title_block(
        x_left,
        anchor_y,
        width,
        title=title,
        subtitle=subtitle,
        figure_label=figure_label,
        ink=pal["ink"],
        muted=pal["ink6"],
        title_font_size=fs["title"],
        subtitle_font_size=fs["subtitle"],
        figure_font_size=fs["figure"],
        body_font=body_font,
        heading_font=heading_font,
    )
    return title_svg


def draw_note_source(note, source, *, x_left, x_right, y, fs, color) -> str:
    """Italic footer: ``note`` left-aligned at ``x_left``, ``source`` right-aligned at ``x_right``."""
    out = []
    if note:
        out.append(
            f'<text x="{x_left:.1f}" y="{y:.1f}" font-size="{fs}" '
            f'fill="{color}" font-style="italic">{_xesc(note)}</text>'
        )
    if source:
        out.append(
            f'<text x="{x_right:.1f}" y="{y:.1f}" font-size="{fs}" '
            f'fill="{color}" text-anchor="end" font-style="italic">{_xesc(source)}</text>'
        )
    return "".join(out)


def wrap_svg(parts, W: float, H: float, body_font: str) -> str:
    """Join ``parts`` into the outer ``<svg>`` with a ``W x H`` viewBox and default font."""
    body = "".join(parts)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}" font-family="{body_font}">{body}</svg>'
    )


def draw_footer(note, source, pal: dict, fs: dict, x_left, x_right, y) -> str:
    """Standard academic footer: ``draw_note_source`` at ``max(13, fs["foot"])`` in ``pal["ink6"]``."""
    return draw_note_source(
        note, source, x_left=x_left, x_right=x_right, y=y, fs=max(13.0, fs["foot"]), color=pal["ink6"]
    )


def draw_ecdf_subpanel(sub_bbox, curves, *, x_min, x_max, x_ticks, x_unit, x_title, pal, fs) -> str:
    """ECDF step curves ``[(samples, color), ...]`` in a sub-panel sharing the main x domain."""
    sx_left, sx_right, sy_top, sy_bot = bbox_to_edges(sub_bbox)
    sub_fs_tick = max(10.0, fs["ytick"] * 0.88)
    sub_fs_title = max(10.0, fs["yaxis"] * 0.88)
    sub_y_min, sub_y_max = 0.0, 1.0
    sub_y_ticks = [0.0, 0.25, 0.5, 0.75, 1.0]

    def SX(v):
        return _lin(v, x_min, x_max, sx_left, sx_right)

    def SY(v):
        return _lin(v, sub_y_min, sub_y_max, sy_bot, sy_top)

    parts = [
        draw_grid(
            sx_left,
            sx_right,
            sy_top,
            sy_bot,
            pal=pal,
            y_ticks=sub_y_ticks,
            y_min=sub_y_min,
            y_max=sub_y_max,
            orient="horizontal",
        )
    ]
    for samples, col in curves:
        pts = ecdf_points(samples)
        if not pts:
            continue
        d_parts = [f"M {SX(x_min):.1f} {SY(0.0):.1f}", f"L {SX(pts[0][0]):.1f} {SY(0.0):.1f}"]
        prev_F = 0.0
        for v, F in pts:
            d_parts.append(f"L {SX(v):.1f} {SY(prev_F):.1f}")
            d_parts.append(f"L {SX(v):.1f} {SY(F):.1f}")
            prev_F = F
        d_parts.append(f"L {SX(x_max):.1f} {SY(prev_F):.1f}")
        parts.append(f'<path d="{" ".join(d_parts)}" fill="none" stroke="{col}" stroke-width="1.6"/>')
    parts.append(
        draw_y_axis(
            sx_left,
            sy_top,
            sy_bot,
            sub_y_ticks,
            sub_y_min,
            sub_y_max,
            pal=pal,
            fs_tick=sub_fs_tick,
            fs_title=sub_fs_title,
            title=tr("ECDF"),
            side="left",
        )
    )
    parts.append(
        draw_x_axis(
            sx_left,
            sx_right,
            sy_bot,
            x_ticks,
            x_min,
            x_max,
            unit=x_unit,
            pal=pal,
            fs_tick=sub_fs_tick,
            fs_title=sub_fs_title,
            title=x_title,
            show_tick_labels=True,
        )
    )
    return "".join(parts)


def draw_magnitude_hist_subpanel(
    edges, values, v_min, v_max, *, color_range, stops=None, x_title, pal, fs_tick, fs_title
) -> str:
    """Count histogram of ``values`` over ``[v_min, v_max]`` whose bars reuse the main colormap."""
    sx_left, sx_right, sy_top, sy_bot = edges
    n_bins = max(6, min(24, int(math.sqrt(len(values)))))
    bin_w_m = (v_max - v_min) / n_bins
    counts = [0] * n_bins
    for mv in values:
        k = int((mv - v_min) / bin_w_m) if bin_w_m > 0 else 0
        if k == n_bins:
            k = n_bins - 1
        if 0 <= k < n_bins:
            counts[k] += 1
    c_hi = max(counts) if counts else 1
    x_ticks_m, xm_min, xm_max = nice_axis(v_min, v_max, 5)
    y_ticks_m, ym_min, ym_max = nice_axis(0, c_hi, 4)

    def _SX(v):
        return _lin(v, xm_min, xm_max, sx_left, sx_right)

    def _SY(v):
        return _lin(v, ym_min, ym_max, sy_bot, sy_top)

    parts = [
        draw_grid(
            sx_left,
            sx_right,
            sy_top,
            sy_bot,
            pal=pal,
            y_ticks=y_ticks_m,
            y_min=ym_min,
            y_max=ym_max,
            orient="horizontal",
        )
    ]
    for i, h in enumerate(counts):
        x0 = _SX(v_min + i * bin_w_m)
        x1 = _SX(v_min + (i + 1) * bin_w_m)
        y_top_bar = _SY(h)
        y_bot_bar = _SY(0)
        mid_mag = v_min + (i + 0.5) * bin_w_m
        col = value_to_color(mid_mag, color_range[0], color_range[1], pal=pal, stops=stops)
        parts.append(
            f'<rect x="{x0:.2f}" y="{y_top_bar:.2f}" '
            f'width="{(x1 - x0 - 0.5):.2f}" height="{(y_bot_bar - y_top_bar):.2f}" '
            f'fill="{col}" stroke="{pal.get("bg", "rgba(255,255,255,1)")}" '
            f'stroke-width="1"/>'
        )
    parts.append(
        draw_y_axis(
            sx_left,
            sy_top,
            sy_bot,
            y_ticks_m,
            ym_min,
            ym_max,
            pal=pal,
            fs_tick=fs_tick,
            fs_title=fs_title,
            title=tr("Count"),
            side="left",
        )
    )
    parts.append(
        draw_x_axis(
            sx_left,
            sx_right,
            sy_bot,
            x_ticks_m,
            xm_min,
            xm_max,
            pal=pal,
            fs_tick=fs_tick,
            fs_title=fs_title,
            title=x_title,
            show_tick_labels=True,
        )
    )
    parts.append(
        f'<text x="{sx_left:.1f}" y="{sy_top - 8:.1f}" '
        f'font-size="{fs_title:.1f}" fill="{pal["ink"]}" '
        f'font-weight="600">{_xesc(tr("Magnitude distribution"))}</text>'
    )
    return "".join(parts)


def draw_embedding_axes(plot_x_left, plot_x_right, plot_y_top, plot_y_bot, axis_names, *, pal, label_fs) -> str:
    """Short L-shaped arrow axes in the bottom-left corner (UMAP / t-SNE convention)."""
    arrow_x0 = plot_x_left + 10.0
    arrow_y0 = plot_y_bot - 10.0
    arrow_len = min(140.0, (plot_x_right - plot_x_left) * 0.18, (plot_y_bot - plot_y_top) * 0.18)
    return draw_axis_arrow(
        arrow_x0,
        arrow_y0,
        arrow_x0 + arrow_len,
        arrow_y0,
        pal=pal,
        label=axis_names[0],
        label_fs=label_fs,
        head_size=10.0,
    ) + draw_axis_arrow(
        arrow_x0,
        arrow_y0,
        arrow_x0,
        arrow_y0 - arrow_len,
        pal=pal,
        label=axis_names[1],
        label_fs=label_fs,
        head_size=10.0,
    )
