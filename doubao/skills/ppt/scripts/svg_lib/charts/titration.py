"""Titration curve (pH or response vs volume) with equivalence-point detection
(derivative maxima), pKa reference lines, and optional derivative panel.
"""

from __future__ import annotations

from .._common import (
    _dist_font_sizes,
    _estimate_label_width_px,
    _resolve_font,
    _resolve_palette,
    _rgb_prefix,
    _variant_is_classic,
    _xesc,
)
from . import _academic_rigor as rigor
from ._shared import tr


# Multi-mode whitelist.
#   with_derivative : dpH/dV curve under the main titration panel, equivalence
#     point marked with ▼ marker + pH_eq annotation. Template = top_bottom_3to1.
#     Trigger: ≥ 15 data points. Validator: xs sortable (allows strict monotonic
#     after sort by volume).
def _validate_derivative(s):
    xs = s.get("xs") or []
    if len(xs) < 15:
        return (False, "need >= 15 points")
    # Allow non-monotonic input as long as it can be sorted by x (duplicates OK
    # but each duplicate must have the same x to avoid ambiguous derivatives).
    try:
        sorted(float(x) for x in xs)
    except (TypeError, ValueError, OverflowError):
        return (False, "xs not numeric")
    return (True, "")


_TITRATION_MULTI_WHITELIST = {
    "with_derivative": (
        "top_bottom_3to1",
        lambda s: len(s.get("xs") or []) >= 15,
        lambda s: _validate_derivative(s),
    ),
}


def _central_diff(xs, ys):
    """Return dy/dx using central differences; endpoints use forward/backward."""
    n = len(xs)
    out = [0.0] * n
    if n < 2:
        return out
    out[0] = (ys[1] - ys[0]) / (xs[1] - xs[0]) if xs[1] != xs[0] else 0.0
    out[-1] = (ys[-1] - ys[-2]) / (xs[-1] - xs[-2]) if xs[-1] != xs[-2] else 0.0
    for i in range(1, n - 1):
        dx = xs[i + 1] - xs[i - 1]
        out[i] = (ys[i + 1] - ys[i - 1]) / dx if dx != 0 else 0.0
    return out


def _smooth(values, window: int = 3):
    """Simple moving-average smoothing (symmetric window). Length-preserving."""
    n = len(values)
    if n == 0 or window <= 1:
        return list(values)
    out = []
    half = window // 2
    for i in range(n):
        lo = max(0, i - half)
        hi = min(n, i + half + 1)
        seg = values[lo:hi]
        out.append(sum(seg) / len(seg))
    return out


def _detect_equivalence_points(xs, ys, min_separation_frac: float = 0.12, max_points: int = 3):
    """Return x positions of local maxima of smoothed |dy/dx|."""
    if len(xs) < 5:
        return []
    ys_s = _smooth(ys, window=3)
    deriv = _central_diff(xs, ys_s)
    adv = _smooth([abs(d) for d in deriv], window=3)
    g_max = max(adv) if adv else 0.0
    if g_max <= 0:
        return []
    span = max(xs) - min(xs)
    sep = span * min_separation_frac
    # candidate peaks: wide local maxima of adv, above 55% of global max
    cands = []
    for i in range(2, len(xs) - 2):
        if (
            adv[i] >= adv[i - 1]
            and adv[i] >= adv[i + 1]
            and adv[i] >= adv[i - 2]
            and adv[i] >= adv[i + 2]
            and adv[i] > g_max * 0.55
        ):
            cands.append((adv[i], xs[i]))
    cands.sort(reverse=True)
    peaks = []
    for mag, x in cands:
        if all(abs(x - px) > sep for px in peaks):
            peaks.append(x)
            if len(peaks) >= max_points:
                break
    peaks.sort()
    return peaks


def make_titration(
    volume,
    ph_or_response,
    *,
    x_unit: str = "mL",
    y_unit: str = "",
    y_title: str = "pH",
    title: str | None = None,
    subtitle: str | None = None,
    figure_label: str | None = None,
    note: str | None = None,
    source: str | None = None,
    equivalence_points=None,
    pka_values=None,
    show_derivative: bool = False,
    multi_mode: str = "auto",
    show_stats: bool = False,
    width: float = 1200,
    height: float = 820,
    font_family: str | None = None,
    palette=None,
    variant: str | None = None,
) -> str:
    """Titration curve with equivalence-point and pKa annotations.

    ``equivalence_points``: list of x-positions; None auto-detects.
    ``pka_values``: list of ``(y_value, label)`` tuples for horizontal pKa lines.
    ``multi_mode``: ``"auto"`` (default), ``"single"``, or ``"with_derivative"``.
      When active, a derivative sub-panel is drawn below the main plot.
    ``show_stats=True`` adds point count / volume range rows to the rail box;
    off by default (bookkeeping). V_eq always stays when equivalence points exist.
    """
    _variant_is_classic("titration", variant)
    if palette is None:
        palette = "archive_ink"
    pal = _resolve_palette(palette)
    body_font, heading_font = _resolve_font(font_family)
    W, H = float(width), float(height)

    xs = list(volume or [])
    ys = list(ph_or_response or [])
    if len(xs) != len(ys) or len(xs) < 2:
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}">'
            f'<text x="{W / 2}" y="{H / 2}" text-anchor="middle" font-size="16" '
            f'fill="{pal["ink6"]}">{_xesc(tr("Insufficient data"))}</text></svg>'
        )

    _TITRATION_MULTI_WHITELIST = {
        "with_derivative": (
            "top_bottom_3to1",
            lambda s: s.get("n_pts", 0) >= 15,
            lambda s: (s.get("n_pts", 0) >= 15 and s.get("sortable", False), "need >=15 points and sortable xs"),
        ),
    }
    _sorted = all(xs[i] <= xs[i + 1] for i in range(len(xs) - 1))
    _signals = {"n_pts": len(xs), "sortable": _sorted}
    _canvas_bbox = rigor.bbox_from_edges(110, W - 70, 110, H - 150)
    _chosen_mode, _chosen_tpl, _reason = rigor.resolve_multi_mode_v2(
        multi_mode,
        _TITRATION_MULTI_WHITELIST,
        _signals,
        _canvas_bbox,
    )
    # multi_mode wins over legacy show_derivative when it resolves; otherwise
    # legacy flag still works for back-compat. "single" explicitly disables
    # the derivative panel; "off" leaves legacy flag alone.
    if _chosen_mode == "with_derivative":
        show_derivative = True
    elif multi_mode == "single":
        show_derivative = False

    fs = _dist_font_sizes(W, H, max(4, len(xs)))

    if equivalence_points is None:
        eq_pts = _detect_equivalence_points(xs, ys)
    else:
        eq_pts = list(equivalence_points)

    # Annotation rail is measured independently from the data rectangle.
    stats = (
        [(tr("n points"), str(len(xs))), (tr("V range"), f"{min(xs):.2g}–{max(xs):.2g} {x_unit}")] if show_stats else []
    )
    if eq_pts:
        stats.append(("V_eq", ", ".join(f"{v:.2f}" for v in eq_pts)))
    _, stats_size = (
        rigor.draw_stats_box(12, 0, stats, pal=pal, fs=fs["label"], font_family=body_font)
        if stats
        else ("", (0, 0, 0, 0))
    )
    rail_texts = [f"V_eq = {v:.2f} {x_unit}" for v in eq_pts] + [tr("Buffer · pKa = {value}", value="14.00")]
    rail_width = (
        max(
            stats_size[2],
            *(_estimate_label_width_px(t, fs["label"], bold=True, font_family=body_font) for t in rail_texts),
        )
        + 36
    )
    margin_top = 110
    margin_bot = 150
    margin_left = 110
    margin_right = rail_width + 44
    if H < rigor.COMPACT_HEIGHT:
        margin_top, margin_bot, margin_left = rigor.compact_margins(
            fs, title=title, subtitle=subtitle, figure_label=figure_label, footer=bool(note or source), foot_offset=22
        )
        margin_right = rail_width + 24
    plot_x_left = margin_left
    plot_x_right = W - margin_right
    plot_y_top = margin_top
    plot_y_bot = H - margin_bot

    # If derivative panel: split plot area 70/30
    if show_derivative:
        split_h = (plot_y_bot - plot_y_top) * 0.70
        main_y_bot = plot_y_top + split_h
        deriv_y_top = main_y_bot + 40
        deriv_y_bot = plot_y_bot
    else:
        main_y_bot = plot_y_bot
        deriv_y_top = None
        deriv_y_bot = None

    x_ticks, x_min, x_max = rigor.nice_axis(min(xs), max(xs), 6)
    y_ticks, y_min, y_max = rigor.nice_axis(min(ys), max(ys), 5)

    def X(v):
        return rigor._lin(v, x_min, x_max, plot_x_left, plot_x_right)

    def Y(v):
        return rigor._lin(v, y_min, y_max, main_y_bot, plot_y_top)

    # Interpolate pH at an arbitrary volume (used for V_eq pH projection and
    # for pKa estimation at half-equivalence).
    def _interp_y(x_target):
        if not xs or not ys:
            return None
        if x_target <= xs[0]:
            return ys[0]
        if x_target >= xs[-1]:
            return ys[-1]
        for i in range(len(xs) - 1):
            if xs[i] <= x_target <= xs[i + 1]:
                dx = xs[i + 1] - xs[i]
                t = (x_target - xs[i]) / dx if dx else 0.0
                return ys[i] + t * (ys[i + 1] - ys[i])
        return ys[-1]

    # points, unless the caller explicitly supplied pka_values. The chemistry:
    # for a weak-acid titration, pKa = pH at half-equivalence (V = V_eq / 2);
    # for a diprotic acid with two eq. points, pKa2 = pH at (V_eq1 + V_eq2)/2.
    # The buffer region spans ~[0.2 V_eq, 0.8 V_eq] around the half-equivalence
    # — this is where the pH plateau is visually widest.
    auto_pka = None
    buffer_regions = []
    if eq_pts:
        auto_pka = []
        prev_v = 0.0
        for eqv in eq_pts:
            half_v = (prev_v + eqv) * 0.5
            pka_val = _interp_y(half_v)
            if pka_val is not None:
                auto_pka.append((pka_val, f"{pka_val:.2f}"))
                buffer_regions.append((prev_v + 0.2 * (eqv - prev_v), prev_v + 0.8 * (eqv - prev_v), half_v, pka_val))
            prev_v = eqv

    # User-supplied pKa overrides the auto list (keep buffer regions anyway so
    # the pH plateau is still highlighted).
    _effective_pka = pka_values if pka_values is not None else auto_pka

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

    rail_x = plot_x_right + 44
    if stats:
        stats_svg, stats_bbox = rigor.draw_stats_box(
            rail_x + 12, plot_y_top, stats, pal=pal, fs=fs["label"], font_family=body_font
        )
        rail_parts = [stats_svg]
        rail_y = stats_bbox[3] + fs["label"] + 26
    else:
        rail_parts = []
        rail_y = plot_y_top + fs["label"]

    def rail_label(label, *, color=None, bold=False):
        nonlocal rail_y
        remaining = str(label)
        while remaining:
            end = len(remaining)
            while (
                end > 1
                and _estimate_label_width_px(remaining[:end], fs["label"], bold=bold, font_family=body_font)
                > W - rail_x - 30
            ):
                end -= 1
            if end < len(remaining):
                split = remaining.rfind(" ", 0, end + 1)
                if split > 0:
                    end = split
            line, remaining = remaining[:end].rstrip(), remaining[end:].lstrip()
            rail_parts.append(
                f'<text x="{rail_x + 12:.1f}" y="{rail_y:.1f}" font-size="{fs["label"]:.1f}" '
                f'fill="{color or pal["ink6"]}" font-weight="{600 if bold else 400}">{_xesc(line)}</text>'
            )
            rail_y += fs["label"] * 1.5

    parts.append(
        rigor.draw_grid(
            plot_x_left,
            plot_x_right,
            plot_y_top,
            main_y_bot,
            pal=pal,
            y_ticks=y_ticks,
            y_min=y_min,
            y_max=y_max,
            orient="horizontal",
        )
    )

    # pKa horizontal lines (behind curve)
    # Fix bug: default label placement sat on the dashed line (text was crossed
    # out by the stroke) *and* landed on the right where it collided with the
    # rising curve. We paint the line via the primitive (first, so it goes
    # behind) then draw the label at the left edge of the plot pulled a full
    # ``fs*1.0`` ABOVE the line + halo so neither stroke nor curve clobbers it.
    # Order matters: line is appended first, label after, so the halo sits
    # above and masks the stroke underneath.
    if _effective_pka:
        for pka_val, pka_label in _effective_pka:
            if y_min <= pka_val <= y_max:
                py = Y(pka_val)
                parts.append(
                    rigor.draw_reference_line(
                        py,
                        plot_x_left,
                        plot_x_right,
                        pal=pal,
                        orient="horizontal",
                        color=pal["ink4"],
                        dash="6 4",
                    )
                )
                pka_text = f"pKa = {pka_label}" if pka_label else f"pKa = {pka_val:.2f}"
                rail_label(pka_text)

    # Only when the buffer spans a visible fraction of the x axis. The chip
    # label (lower corner so it doesn't overlap the eq. line) names the pKa.
    if buffer_regions:
        buf_fill = f"{_rgb_prefix(pal.get('secondary', pal['ink']))}0.10)"
        for bx_lo, bx_hi, half_v, pka_val in buffer_regions:
            if bx_hi - bx_lo < (x_max - x_min) * 0.03:
                continue
            xa = X(max(x_min, bx_lo))
            xb = X(min(x_max, bx_hi))
            parts.append(
                f'<rect x="{xa:.1f}" y="{plot_y_top:.1f}" '
                f'width="{max(0.0, xb - xa):.1f}" '
                f'height="{main_y_bot - plot_y_top:.1f}" '
                f'fill="{buf_fill}" stroke="none"/>'
            )
            rail_label(tr("Buffer · pKa = {value}", value=f"{pka_val:.2f}"))
    rail_y += 16

    accent = pal["accent"]
    for ex in eq_pts:
        if x_min <= ex <= x_max:
            parts.append(
                rigor.draw_reference_line(
                    X(ex),
                    plot_y_top,
                    main_y_bot,
                    pal=pal,
                    orient="vertical",
                    color=accent,
                    dash="5 4",
                )
            )

    # pH curve crosses V_eq, with a short dashed horizontal projection to the
    # Y axis showing pH_eq. These are drawn AFTER the curve so they sit on
    # top of it (see the "Main curve" block below) — we stash them for now.
    _eq_overlay = []
    for ex in sorted(eq_pts, key=lambda value: Y(_interp_y(value))):
        if not (x_min <= ex <= x_max):
            continue
        y_eq = _interp_y(ex)
        if y_eq is None:
            continue
        cx = X(ex)
        cy = Y(y_eq)
        # outer halo + inner solid accent dot
        _eq_overlay.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="9" '
            f'fill="{pal.get("bg", "rgba(255,255,255,1)")}" '
            f'stroke="{accent}" stroke-width="1.4"/>'
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="5.5" '
            f'fill="{accent}" stroke="none"/>'
        )
        _eq_overlay.append(
            f'<line x1="{plot_x_left:.1f}" y1="{cy:.1f}" '
            f'x2="{cx:.1f}" y2="{cy:.1f}" '
            f'stroke="{accent}" stroke-width="1.0" '
            f'stroke-dasharray="4 3" opacity="0.75"/>'
        )
        # Leaders terminate before the annotation rail. The projection itself
        # remains at the interpolated response; moving a label never moves data.
        label_y = rail_y
        _eq_overlay.append(
            f'<polyline points="{cx + 10:.1f},{cy:.1f} {plot_x_right + 20:.1f},{cy:.1f} '
            f'{rail_x - 8:.1f},{label_y - fs["label"] * 0.35:.1f}" '
            f'fill="none" stroke="{accent}" stroke-width="1"/>'
        )
        rail_label(f"V_eq = {ex:.2f} {x_unit}", color=accent, bold=True)
        response_label = "pH_eq" if y_title.lower() == "ph" else f"{y_title}_eq"
        rail_label(f"{response_label} = {y_eq:.2f}", color=pal["ink"], bold=True)
        rail_y += 18

    curve_pts = [(X(x), Y(y)) for x, y in zip(xs, ys)]
    d = " ".join(f"{'M' if i == 0 else 'L'} {x:.1f} {y:.1f}" for i, (x, y) in enumerate(curve_pts))
    parts.append(f'<path d="{d}" fill="none" stroke="{pal["ink"]}" stroke-width="2.0"/>')
    # Light dots at each raw point for data visibility
    for cx, cy in curve_pts:
        parts.append(f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="2.4" fill="{pal["ink"]}" stroke="none" opacity="0.75"/>')

    # Overlay equivalence-point markers (dot + horizontal projection + pH_eq
    # label) on top of the curve.
    parts.extend(_eq_overlay)

    parts.append(
        rigor.draw_y_axis(
            plot_x_left,
            plot_y_top,
            main_y_bot,
            y_ticks,
            y_min,
            y_max,
            unit=y_unit,
            pal=pal,
            fs_tick=fs["ytick"],
            fs_title=fs["yaxis"],
            title=y_title,
            side="left",
        )
    )
    if show_derivative:
        # x axis only below derivative panel; add minor x axis at main bottom too
        # Draw x-axis without labels for the main panel (just baseline), then full
        # x-axis below the derivative panel
        parts.append(
            f'<line x1="{plot_x_left:.1f}" y1="{main_y_bot:.1f}" '
            f'x2="{plot_x_right:.1f}" y2="{main_y_bot:.1f}" '
            f'stroke="{pal["ink"]}" stroke-width="1.2"/>'
        )
    else:
        parts.append(
            rigor.draw_x_axis(
                plot_x_left,
                plot_x_right,
                main_y_bot,
                x_ticks,
                x_min,
                x_max,
                unit=x_unit,
                pal=pal,
                fs_tick=fs["ytick"],
                fs_title=fs["yaxis"],
                title=tr("Volume ({unit})", unit=x_unit),
            )
        )

    if show_derivative:
        deriv = _central_diff(xs, ys)
        if deriv:
            d_min_v = min(deriv)
            d_max_v = max(deriv)
            d_ticks, d_min_a, d_max_a = rigor.nice_axis(d_min_v, d_max_v, 4)

            def Yd(v):
                return rigor._lin(v, d_min_a, d_max_a, deriv_y_bot, deriv_y_top)

            parts.append(
                rigor.draw_grid(
                    plot_x_left,
                    plot_x_right,
                    deriv_y_top,
                    deriv_y_bot,
                    pal=pal,
                    y_ticks=d_ticks,
                    y_min=d_min_a,
                    y_max=d_max_a,
                    orient="horizontal",
                )
            )
            dpts = [(X(x), Yd(d)) for x, d in zip(xs, deriv)]
            dd = " ".join(f"{'M' if i == 0 else 'L'} {x:.1f} {y:.1f}" for i, (x, y) in enumerate(dpts))
            parts.append(f'<path d="{dd}" fill="none" stroke="{accent}" stroke-width="1.6"/>')
            # mark eq points on derivative panel too
            for ex in eq_pts:
                if x_min <= ex <= x_max:
                    parts.append(
                        f'<line x1="{X(ex):.1f}" y1="{deriv_y_top:.1f}" '
                        f'x2="{X(ex):.1f}" y2="{deriv_y_bot:.1f}" '
                        f'stroke="{accent}" stroke-width="1" stroke-dasharray="5 4"/>'
                    )
            parts.append(
                rigor.draw_y_axis(
                    plot_x_left,
                    deriv_y_top,
                    deriv_y_bot,
                    d_ticks,
                    d_min_a,
                    d_max_a,
                    pal=pal,
                    fs_tick=fs["ytick"],
                    title=tr("dpH/dV"),
                    side="left",
                )
            )
            parts.append(
                rigor.draw_x_axis(
                    plot_x_left,
                    plot_x_right,
                    deriv_y_bot,
                    x_ticks,
                    x_min,
                    x_max,
                    unit=x_unit,
                    pal=pal,
                    fs_tick=fs["ytick"],
                    fs_title=fs["yaxis"],
                    title=tr("Volume ({unit})", unit=x_unit),
                )
            )

    parts.extend(rail_parts)

    parts.append(rigor.draw_footer(note, source, pal, fs, plot_x_left, plot_x_right, H - 22))

    return rigor.wrap_svg(parts, W, H, body_font)
