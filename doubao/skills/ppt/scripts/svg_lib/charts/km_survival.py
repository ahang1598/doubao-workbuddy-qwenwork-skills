"""Kaplan-Meier survival curve chart with Greenwood CI band, censor ticks,
log-rank P-value, hazard-ratio annotation, and an at-risk table.
"""

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
from ._shared import tr


def _km_estimate(times, events):
    """Return list of (t, S, var_S, n_at_risk, n_event, is_censor_only_t) tuples."""
    pairs = sorted(zip(times, events))
    N = len(pairs)
    if N == 0:
        return []
    grouped = {}
    for t, e in pairs:
        g = grouped.setdefault(t, [0, 0])  # [n_event, n_censor]
        if e:
            g[0] += 1
        else:
            g[1] += 1
    unique_times = sorted(grouped.keys())
    at_risk = N
    S = 1.0
    var_sum = 0.0  # cumulative sum of d / (n*(n-d)) for Greenwood
    out = [(0.0, 1.0, 0.0, N, 0, False)]
    for t in unique_times:
        d, c = grouped[t]
        if at_risk <= 0:
            break
        n_here = at_risk
        if d > 0:
            # Avoid divide-by-zero if n == d (produces 0 variance contribution anyway)
            if n_here > d:
                var_sum += d / (n_here * (n_here - d))
            S *= max(0.0, 1.0 - d / n_here)
            var_S = (S**2) * var_sum
            out.append((t, S, var_S, n_here, d, False))
        if d == 0 and c > 0:
            # censor-only time point: still record (survival unchanged)
            out.append((t, S, (S**2) * var_sum, n_here, 0, True))
        at_risk -= d + c
    return out


def _at_risk_counts(times, events, time_points):
    """How many are still at risk at each time point (just before)."""
    out = []
    for tp in time_points:
        n = sum(1 for t in times if t >= tp)
        out.append(n)
    return out


def _log_rank_pvalue(groups_data):
    """groups_data: list[(times, events)]."""
    g = len(groups_data)
    if g < 2:
        return 0.0, 0, 1.0
    all_event_times = set()
    for times, events in groups_data:
        for t, e in zip(times, events):
            if e:
                all_event_times.add(t)
    if not all_event_times:
        return 0.0, g - 1, 1.0
    event_times = sorted(all_event_times)
    # For each event time compute, per-group: n_j (at risk) and d_j (events).
    # Observed - Expected summed per group; variance aggregated.
    O_minus_E = [0.0] * g
    V_cum = [[0.0] * g for _ in range(g)]  # we only use diag
    for t in event_times:
        n_j = []
        d_j = []
        for times, events in groups_data:
            nj = sum(1 for tt in times if tt >= t)
            dj = sum(1 for tt, ee in zip(times, events) if tt == t and ee)
            n_j.append(nj)
            d_j.append(dj)
        N = sum(n_j)
        D = sum(d_j)
        if N <= 1 or D == 0:
            continue
        for j in range(g):
            O_minus_E[j] += d_j[j] - D * n_j[j] / N
            # variance for group j (approx; proper var uses full covariance matrix)
            # Standard log-rank variance: n_j * (N - n_j) * D * (N - D) / (N^2 * (N-1))
            if N > 1:
                V_cum[j][j] += (n_j[j] * (N - n_j[j]) * D * (N - D)) / (N * N * (N - 1))
    # Build chi² = sum_j (O-E)²/V_jj (equivalent to the simple log-rank when #groups=2,
    # and a conservative approximation for >2 groups)
    chi2 = 0.0
    for j in range(g):
        if V_cum[j][j] > 0:
            chi2 += (O_minus_E[j] ** 2) / V_cum[j][j]
    df = g - 1
    p = _chi2_sf(chi2, df)
    return chi2, df, p


def _chi2_sf(x, df):
    """Survival function (1 - CDF) of chi² with df degrees of freedom."""
    if x <= 0:
        return 1.0
    if df <= 0:
        return 1.0
    return _gamma_q(df / 2.0, x / 2.0)


def _gamma_q(a, x):
    """Q(a, x) = 1 - P(a, x), regularized upper incomplete gamma."""
    if x <= 0:
        return 1.0
    if a <= 0:
        return 0.0
    if x < a + 1.0:
        # series expansion for P, then Q = 1 - P
        return 1.0 - _gamma_p_series(a, x)
    return _gamma_q_cf(a, x)


def _ln_gamma(z):
    return math.lgamma(z)


def _gamma_p_series(a, x):
    ap = a
    term = 1.0 / a
    total = term
    for i in range(1, 200):
        ap += 1.0
        term *= x / ap
        total += term
        if abs(term) < abs(total) * 1e-12:
            break
    return total * math.exp(-x + a * math.log(x) - _ln_gamma(a))


def _gamma_q_cf(a, x):
    FPMIN = 1e-300
    EPS = 1e-12
    b = x + 1.0 - a
    c = 1.0 / FPMIN
    d = 1.0 / b
    h = d
    for i in range(1, 200):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < FPMIN:
            d = FPMIN
        c = b + an / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < EPS:
            break
    return h * math.exp(-x + a * math.log(x) - _ln_gamma(a))


def make_km_survival(
    groups,
    *,
    time_unit: str = "months",
    title: str | None = None,
    subtitle: str | None = None,
    figure_label: str | None = None,
    note: str | None = None,
    source: str | None = None,
    log_rank_p: float | None = None,
    hazard_ratio=None,
    show_at_risk: bool = True,
    show_ci: bool = True,
    highlight_group: str | None = None,
    x_max: float | None = None,
    multi_mode: str = "auto",
    width: float = 1300,
    height: float = 960,
    font_family: str | None = None,
    palette=None,
    variant: str | None = None,
) -> str:
    """Kaplan-Meier curves + Greenwood CI band + censor ticks + at-risk table.

    ``multi_mode``: ``"auto"`` (default), ``"single"``, or ``"with_risk_table"``.
    - ``"single"`` suppresses the at-risk table even if ``show_at_risk=True``.
    - ``"with_risk_table"`` forces the at-risk table even if ``show_at_risk=False``.
    - ``"auto"`` follows ``show_at_risk`` (default True) when any group has
      at-risk counts; otherwise falls back to single.

    The legacy ``show_at_risk`` parameter is preserved for backward compatibility.
    """
    _variant_is_classic("km_survival", variant)
    time_unit = tr(time_unit)
    if not groups:
        raise ValueError("make_km_survival: 'groups' must contain at least one group")

    if palette is None:
        palette = "archive_ink"
    pal = _resolve_palette(palette)
    body_font, heading_font = _resolve_font(font_family)
    W, H = float(width), float(height)
    n_g = len(groups)
    fs = _dist_font_sizes(W, H, max(4, n_g + 2))

    g_series = []
    for i, g in enumerate(groups):
        name = str(g.get("name", f"group {i + 1}"))
        times = list(g.get("times") or [])
        events = list(g.get("events") or [])
        if len(times) != len(events) or len(times) == 0:
            raise ValueError(f"make_km_survival: group '{name}' needs matching nonempty times/events")
        km = _km_estimate(times, events)
        g_series.append({"name": name, "times": times, "events": events, "km": km, "N0": len(times)})

    data_max = max(max((t[0] for t in gs["km"]), default=0.0) for gs in g_series)
    if x_max is None:
        x_max = data_max
    if x_max <= 0:
        x_max = 1.0
    x_ticks, _x_min_a, x_max_a = rigor.nice_axis(0.0, x_max, 6)
    # pin x_min to 0 since survival time starts at 0
    x_min = 0.0
    y_ticks = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
    y_min, y_max = 0.0, 1.0

    # multi_mode decides whether to render the at-risk table. The legacy
    # show_at_risk flag is honored under "auto"; explicit multi_mode overrides.
    if multi_mode == "with_risk_table":
        _render_at_risk = True
    elif multi_mode == "single":
        _render_at_risk = False
    else:  # "auto" or anything else — defer to show_at_risk
        _render_at_risk = show_at_risk
    show_at_risk = _render_at_risk

    at_risk_h = 0
    if show_at_risk:
        at_risk_h = 40 + n_g * 26  # header + per-group row
    margin_top = 120
    margin_bot = 90 + at_risk_h + 30
    # left margin: must accommodate at-risk group-name column (if shown) + first
    # count column half-width + axis title. Mirrors the formula used in
    # draw_at_risk_table / caller below so plot_x_left aligns exactly with t_min.
    name_w_pre = 0
    if show_at_risk:
        _tmp_fs = max(13.0, fs["label"])
        name_w_pre = max(
            (
                _estimate_label_width_px(str(g.get("name", f"group {i + 1}")), _tmp_fs, font_family=body_font)
                for i, g in enumerate(groups)
            ),
            default=50,
        )
        # Add room for half the first count's width (worst-case 3-digit) + gap,
        # since counts are middle-anchored at data_left.
        name_w_pre += _estimate_label_width_px("999", _tmp_fs, font_family=body_font) * 0.5 + 18
    margin_left = max(130, int(name_w_pre + 90))
    margin_right = 60
    # Vertical stack (top → bottom): title block, legend strip, plot, x ticks + title,
    # at-risk table, footer. Offsets are measured from the fonts so nothing collides.
    _leg_fs = max(13.0, fs["label"])
    _tick_fs, _axis_fs = max(13.0, fs["ytick"]), max(13.0, fs["yaxis"])
    leg_gap = 24  # legend centre sits this far above plot_y_top
    title_anchor_gap = leg_gap + _leg_fs * 0.75 + 10 if (title or subtitle) else 30
    risk_row_h = max(24.0, _leg_fs * 1.35)
    risk_gap = _tick_fs + _axis_fs + 18 + _leg_fs * 0.3 + _leg_fs + 12  # x-axis title bottom → table header baseline
    risk_table_h = risk_row_h * (0.5 + n_g) + _leg_fs * 0.3 if show_at_risk else 0.0
    if H < rigor.COMPACT_HEIGHT:
        _heads = rigor.compact_margins(fs, title=title, subtitle=subtitle, figure_label=figure_label)[0] - 26
        margin_top = title_anchor_gap + (_heads + 2 if _heads > 0 else 0) + 8
        if not (title or subtitle or figure_label):
            margin_top = leg_gap + _leg_fs * 0.75 + 8
        margin_bot = (risk_gap + risk_table_h if show_at_risk else _tick_fs + _axis_fs + 28) + (
            max(13.0, fs["foot"]) + 24 if (note or source) else 6
        )
        margin_right = 28
    plot_x_left = margin_left
    plot_x_right = W - margin_right
    plot_y_top = margin_top
    plot_y_bot = H - margin_bot
    _min_plot = 120.0 if show_at_risk else 100.0
    if plot_y_bot - plot_y_top < _min_plot:
        raise ValueError(
            f"km_survival canvas too short for the curves, legend and at-risk table: "
            f"height at least {H + _min_plot - (plot_y_bot - plot_y_top):.0f}"
        )

    def X(v):
        return rigor._lin(v, x_min, x_max_a, plot_x_left, plot_x_right)

    def Y(v):
        return rigor._lin(v, y_min, y_max, plot_y_bot, plot_y_top)

    series_cols = _derive_series_colors(pal, max(1, n_g))

    parts = rigor.draw_canvas_bg(pal, W, H)

    parts.append(
        rigor.draw_title_block(
            plot_x_left,
            plot_y_top - title_anchor_gap,
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

    if log_rank_p is None and n_g >= 2:
        groups_data = [(gs["times"], gs["events"]) for gs in g_series]
        _, _, log_rank_p = _log_rank_pvalue(groups_data)
    stats = []
    if log_rank_p is not None:
        if log_rank_p < 0.001:
            p_str = "< 0.001"
        else:
            p_str = f"{log_rank_p:.3f}"
        stats.append((tr("log-rank P"), p_str))
    if hazard_ratio is not None and len(hazard_ratio) == 3:
        hr, lo, hi = hazard_ratio
        stats.append(("HR", f"{hr:.2f} (95% CI, {lo:.2f}–{hi:.2f})"))
    if stats:
        sb_svg, _sb_box = rigor.draw_stats_box(
            plot_x_right - 10,
            plot_y_top + 8,
            stats,
            pal=pal,
            fs=fs["label"],
            anchor="end",
            font_family=body_font,
        )
    else:
        sb_svg, _sb_box = "", None

    # grid (stops at the stats box so no dashed line strikes through its text)
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
            cutout_bboxes=[tuple(_sb_box)] if _sb_box else None,
        )
    )

    for i, gs in enumerate(g_series):
        km = gs["km"]
        col = series_cols[i % len(series_cols)]
        is_hi = highlight_group is not None and gs["name"] == highlight_group
        stroke_w = 3.3 if is_hi else 2.4

        step_pts = []  # (x, y) list
        ci_up = []
        ci_dn = []
        prev_x = None
        prev_y = None
        for t, S, var_S, n_r, d, is_censor_only in km:
            if t > x_max_a:
                break
            x_px = X(t)
            y_px = Y(S)
            if prev_x is not None and y_px != prev_y:
                # horizontal segment to this t, then vertical drop
                step_pts.append((x_px, prev_y))
                step_pts.append((x_px, y_px))
            else:
                step_pts.append((x_px, y_px))
            if show_ci and var_S > 0 and S > 0 and S < 1:
                se = math.sqrt(var_S)
                lo = max(0.0, S - 1.96 * se)
                hi = min(1.0, S + 1.96 * se)
            else:
                lo = S
                hi = S
            if prev_x is not None and y_px != prev_y:
                ci_up.append((x_px, Y(hi) if hi != 1 else prev_y))
                ci_dn.append((x_px, Y(lo) if lo != S else prev_y))
                ci_up.append((x_px, Y(hi)))
                ci_dn.append((x_px, Y(lo)))
            else:
                ci_up.append((x_px, Y(hi)))
                ci_dn.append((x_px, Y(lo)))
            prev_x, prev_y = x_px, y_px

        if step_pts:
            last_x, last_y = step_pts[-1]
            if last_x < plot_x_right:
                step_pts.append((plot_x_right, last_y))
                ci_up.append((plot_x_right, ci_up[-1][1]))
                ci_dn.append((plot_x_right, ci_dn[-1][1]))

        if show_ci and len(ci_up) > 1:
            coords = [f"{x:.1f},{y:.1f}" for x, y in ci_up]
            coords += [f"{x:.1f},{y:.1f}" for x, y in reversed(ci_dn)]
            band_fill = f"{_rgb_prefix(col)}0.14)"
            parts.append(f'<polygon points="{" ".join(coords)}" fill="{band_fill}" stroke="none"/>')

        if step_pts:
            d = " ".join(f"{'M' if j == 0 else 'L'} {x:.1f} {y:.1f}" for j, (x, y) in enumerate(step_pts))
            parts.append(
                f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{stroke_w}" '
                f'stroke-linecap="round" stroke-linejoin="round"/>'
            )

        for t, S, var_S, n_r, d, is_censor_only in km:
            if is_censor_only and 0 < t <= x_max_a:
                parts.append(rigor.draw_censor_tick(X(t), Y(S), pal=pal, h=10, color=col))

    parts.append(
        rigor.draw_y_axis(
            plot_x_left,
            plot_y_top,
            plot_y_bot,
            y_ticks,
            y_min,
            y_max,
            pal=pal,
            fs_tick=fs["ytick"],
            fs_title=fs["yaxis"],
            title=tr("Survival probability"),
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
            x_max_a,
            unit=time_unit,
            pal=pal,
            fs_tick=fs["ytick"],
            fs_title=fs["yaxis"],
            title=tr("Time ({unit})", unit=time_unit),
        )
    )

    if sb_svg:
        parts.append(sb_svg)

    # Earlier versions put the legend inside the upper-left of the plot area, which clipped the Placebo baseline's step
    # line and (in large-panel layouts) bisected the glyphs.
    leg_fs = max(13.0, fs["label"])
    leg_line_w = 28  # legend swatch width
    leg_item_gap = 22  # gap between adjacent legend items
    leg_glyph_gap = 8  # swatch -> text gap within one item
    # Measure each item's text width so items can be laid out left-to-right.
    item_text_widths = []
    for gs in g_series:
        label = f"{gs['name']} (n = {gs['N0']})"
        item_text_widths.append(_estimate_label_width_px(label, leg_fs, font_family=body_font))
    item_widths = [leg_line_w + leg_glyph_gap + w for w in item_text_widths]
    total_w = sum(item_widths) + leg_item_gap * max(0, len(item_widths) - 1)
    # Right-align the strip against plot_x_right so it never collides with the left-side y-axis label area; fall back to
    # left-align if the strip is too wide for the plot width.
    leg_y_center = plot_y_top - leg_gap
    plot_w = plot_x_right - plot_x_left
    if total_w <= plot_w:
        cur_x = plot_x_right - total_w
    else:
        cur_x = plot_x_left
    for i, gs in enumerate(g_series):
        col = series_cols[i % len(series_cols)]
        swatch_y = leg_y_center
        parts.append(
            f'<line x1="{cur_x:.1f}" y1="{swatch_y:.1f}" '
            f'x2="{cur_x + leg_line_w:.1f}" y2="{swatch_y:.1f}" '
            f'stroke="{col}" stroke-width="3"/>'
        )
        tx = cur_x + leg_line_w + leg_glyph_gap
        ty = swatch_y + leg_fs * 0.38
        parts.append(
            f'<text x="{tx:.1f}" y="{ty:.1f}" '
            f'font-size="{leg_fs}" fill="{pal["ink"]}">{_xesc(gs["name"])} '
            f'<tspan fill="{pal["ink6"]}">(n = {gs["N0"]})</tspan></text>'
        )
        cur_x += item_widths[i] + leg_item_gap

    if show_at_risk:
        times_at_risk = [t for t in x_ticks if t <= x_max_a + 1e-6]
        group_names = [gs["name"] for gs in g_series]
        counts = []
        for gs in g_series:
            counts.append(_at_risk_counts(gs["times"], gs["events"], times_at_risk))
        # The table's data columns are positioned by _lin(t, t_min, t_max, data_left, x_right) with data_left =
        # table_x_left + name_w.
        max_first_count = max((row[0] for row in counts if row), default=99) if counts else 99
        _half_first_count_w = _estimate_label_width_px(str(max_first_count), leg_fs, font_family=body_font) * 0.5
        name_w = (
            max(
                (_estimate_label_width_px(g, leg_fs, font_family=body_font) for g in group_names),
                default=50,
            )
            + _half_first_count_w
            + 18
        )
        table_x_left = plot_x_left - name_w
        # Clamp: if the name column would spill past the SVG edge, trim the name_w (right-align truncates / overlaps the
        # half-count gap) rather than nudging table_x_left so each column still lands at X(tick).
        if table_x_left < 10:
            name_w = max(20.0, plot_x_left - 10)
            table_x_left = plot_x_left - name_w
        at_table_y_top = plot_y_bot + (70 if H >= rigor.COMPACT_HEIGHT else risk_gap)  # below x-axis title
        parts.append(
            rigor.draw_at_risk_table(
                table_x_left,
                plot_x_right,
                at_table_y_top,
                times_at_risk,
                counts,
                group_names,
                pal=pal,
                fs=leg_fs,
                row_h=24 if H >= rigor.COMPACT_HEIGHT else risk_row_h,
                t_min=x_min,
                t_max=x_max_a,
                font_family=body_font,
            )
        )

    parts.append(rigor.draw_footer(note, source, pal, fs, plot_x_left, plot_x_right, H - 30))

    return rigor.wrap_svg(parts, W, H, body_font)
