"""Reaction kinetics (time vs concentration/response) with optional per-curve
exponential or linear fit, rate constants, and error bars. Pure stdlib.
"""

from __future__ import annotations

import math

from .._common import (
    _derive_series_colors,
    _dist_font_sizes,
    _estimate_label_width_px,
    _resolve_font,
    _resolve_palette,
    _variant_is_classic,
    _xesc,
)
from . import _academic_rigor as rigor
from ._chart_layout import ChartLayout, wrap_lines
from ._shared import tr


# Multi-mode whitelist: with_rate_bars → horizontal bar plot of rate constants
# per curve. Trigger: n_curves >= 3. Validator: >=2 curves have usable k from fit.
def _kinetics_count_curves(signals):
    return int(signals.get("n_curves", 0))


def _validate_rate_bars(signals):
    good = signals.get("n_curves_with_k", 0)
    if good < 2:
        return (False, f"need >=2 curves with rate constant (got {good})")
    return (True, "")


_KINETICS_MULTI_WHITELIST = {
    "with_rate_bars": (
        "left_right_3to1",
        lambda s: _kinetics_count_curves(s) >= 3,
        lambda s: _validate_rate_bars(s),
    ),
}


def _ols(xs, ys):
    """Simple OLS. Returns (slope, intercept, r2)."""
    n = len(xs)
    if n < 2:
        return 0.0, (ys[0] if ys else 0.0), 0.0
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    syy = sum((y - my) ** 2 for y in ys)
    slope = sxy / sxx if sxx > 0 else 0.0
    intercept = my - slope * mx
    ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(xs, ys))
    r2 = 1.0 - ss_res / syy if syy > 0 else 0.0
    return slope, intercept, r2


def _fit_exp1(times, values):
    """First-order decay/growth fit:  y = A * exp(-k*t) + B."""
    n = len(times)
    if n < 3:
        return (0.0, 0.0, 0.0, 0.0, False)
    y0 = values[0]
    y_end = values[-1]
    tail = values[max(0, n - 3) :]
    B = sum(tail) / len(tail)
    # decide decay vs growth: if y_end > y0, growth → fit (y_end - y) decay
    growth = y_end > y0
    if growth:
        B = max(values) + 1e-6
        residuals = [B - y for y in values]
    else:
        residuals = [y - B for y in values]
    # keep only positive residuals for log
    xs_fit = []
    ys_fit = []
    for t, r in zip(times, residuals):
        if r > 1e-9:
            xs_fit.append(t)
            ys_fit.append(math.log(r))
    if len(xs_fit) < 2:
        return (0.0, 0.0, B, 0.0, False)
    slope, intercept, r2 = _ols(xs_fit, ys_fit)
    k = -slope  # positive for decay
    A = math.exp(intercept)
    if growth:
        # y = B - A*exp(-k*t)  ->  caller interprets A as negative
        A = -A
    return (A, k, B, r2, True)


def _apply_exp1(t: float, A: float, k: float, B: float) -> float:
    return A * math.exp(-k * t) + B


def _apply_linear(t: float, slope: float, intercept: float) -> float:
    return slope * t + intercept


def make_kinetics(
    curves,
    *,
    time_unit: str = "s",
    value_unit: str = "mM",
    value_label: str = "Response",
    time_label: str | None = None,
    title: str | None = None,
    subtitle: str | None = None,
    figure_label: str | None = None,
    note: str | None = None,
    source: str | None = None,
    show_rate_constants: bool = True,
    width: float = 1200,
    height: float = 820,
    font_family: str | None = None,
    palette=None,
    variant: str | None = None,
    multi_mode: str = "auto",
) -> str:
    """Time-resolved response with optional per-curve fit.

    ``curves`` is a list of ``{name, time, value, err?, fit_type?}``.
    Omitted ``fit_type`` means ``none``: connect supplied points without fitting.
    Choose ``exp1`` or ``linear`` only when that model fits the experimental
    question; ``show_rate_constants=False`` only hides annotations, not a
    requested fit. Set ``value_label`` and ``value_unit`` to the measured quantity
    (for normalized responses, use an explicit label and an empty unit).
    """
    _variant_is_classic("kinetics", variant)
    if palette is None:
        palette = "archive_ink"
    pal = _resolve_palette(palette)
    body_font, heading_font = _resolve_font(font_family)
    W, H = float(width), float(height)

    curves = curves or []
    if not curves:
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}">'
            f'<text x="{W / 2}" y="{H / 2}" text-anchor="middle" font-size="16" '
            f'fill="{pal["ink6"]}">{_xesc(tr("No data"))}</text></svg>'
        )

    for index, curve in enumerate(curves):
        times = curve.get("time", []) or []
        values = curve.get("value", []) or []
        errors = curve.get("err", []) or []
        if not times or len(times) != len(values):
            raise ValueError(f"kinetics curve {index}: time and value must have equal nonzero lengths")
        if errors and len(errors) != len(times):
            raise ValueError(f"kinetics curve {index}: err must match time/value length")
        if curve.get("fit_type", "none") not in ("none", "exp1", "linear"):
            raise ValueError(f"kinetics curve {index}: fit_type must be none, exp1, or linear")

    fs = _dist_font_sizes(W, H, max(4, len(curves)))
    series_colors = _derive_series_colors(pal, len(curves))

    foot_fs = max(13.0, fs["foot"], W / 45)
    foot_lines = []
    for prefix, value in ((tr("Notes. "), note), (tr("Source. "), source)):
        if value:
            foot_lines.extend(wrap_lines(prefix + str(value), W - 56, foot_fs, body_font))
    footer_height = len(foot_lines) * foot_fs * 1.35 + (28 if foot_lines else 0)
    margin_top = 110
    margin_bot = max(140, footer_height + fs["ytick"] * 1.35 + fs["yaxis"] * 1.35 + 24)
    margin_left = 110
    margin_right = 70
    if H < rigor.COMPACT_HEIGHT:
        # Legend (multi-curve) / k caption sits below the x-axis title; reserve its rows.
        _lg_fs = max(13.0, fs["legend"])
        _lg_rows = 0
        if len(curves) > 1 or show_rate_constants:
            _avail, _cur, _lg_rows = W - 180, 0.0, 1
            for _ci, _c in enumerate(curves):
                _w = 34 + _estimate_label_width_px(
                    str(_c.get("name", "")) + (" · k = 0.000 s⁻¹" if show_rate_constants else ""),
                    _lg_fs,
                    font_family=body_font,
                )
                if _cur and _cur + _w > _avail:
                    _lg_rows, _cur = _lg_rows + 1, _w
                else:
                    _cur += _w
        margin_top, _bot, margin_left = rigor.compact_margins(
            fs, title=title, subtitle=subtitle, figure_label=figure_label
        )
        margin_bot = (
            max(
                _bot,
                fs["ytick"] + fs["yaxis"] + 46 + _lg_fs * 0.4 + (_lg_rows - 1) * _lg_fs * 1.5 + 10 if _lg_rows else 0,
            )
            + footer_height
        )
        margin_right = 36
    plot_x_left = margin_left
    plot_x_right = W - margin_right
    plot_y_top = margin_top
    plot_y_bot = H - margin_bot
    if plot_y_bot - plot_y_top < 130:
        raise ValueError("kinetics canvas is too short for full note/source text and the plotting area")

    all_t = []
    all_v = []
    for c in curves:
        all_t.extend(c.get("time", []))
        all_v.extend(c.get("value", []))
        for v, e in zip(c.get("value", []), c.get("err", []) or []):
            all_v.append(v + (e or 0))
            all_v.append(v - (e or 0))

    if not all_t:
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}">'
            f'<text x="{W / 2}" y="{H / 2}" text-anchor="middle" font-size="16" '
            f'fill="{pal["ink6"]}">{_xesc(tr("No time points"))}</text></svg>'
        )

    x_ticks, x_min, x_max = rigor.nice_axis(min(all_t), max(all_t), 6)
    y_ticks, y_min, y_max = rigor.nice_axis(min(all_v), max(all_v), 5)

    def X(v):
        return rigor._lin(v, x_min, x_max, plot_x_left, plot_x_right)

    def Y(v):
        return rigor._lin(v, y_min, y_max, plot_y_bot, plot_y_top)

    fit_results = []
    for c in curves:
        times = c.get("time", []) or []
        values = c.get("value", []) or []
        fit_type = c.get("fit_type", "none")
        res = {"fit_type": fit_type, "ok": False}
        if fit_type == "exp1":
            A, k, B, r2, ok = _fit_exp1(times, values)
            res.update({"A": A, "k": k, "B": B, "r2": r2, "ok": ok})
        elif fit_type == "linear":
            slope, intercept, r2 = _ols(times, values)
            res.update({"slope": slope, "intercept": intercept, "r2": r2, "ok": True})
        fit_results.append(res)

    _full_plot_bbox = rigor.bbox_from_edges(
        plot_x_left,
        plot_x_right,
        plot_y_top,
        plot_y_bot,
    )

    def _k_of(res):
        if not res.get("ok"):
            return None
        if res.get("fit_type") == "exp1":
            k = res.get("k")
            return k if (k is not None and math.isfinite(k) and k > 0) else None
        return None

    _k_values = [_k_of(r) for r in fit_results]
    _mm_signals = {
        "n_curves": len(curves),
        "n_curves_with_k": sum(1 for k in _k_values if k is not None),
    }
    _mm_mode, _mm_template, _mm_reason = rigor.resolve_multi_mode_v2(
        multi_mode,
        _KINETICS_MULTI_WHITELIST,
        _mm_signals,
        _full_plot_bbox,
    )
    _sub_bbox = None
    if _mm_mode is not None and _mm_template is not None:
        _rects = rigor.allocate_main_sub(_full_plot_bbox, _mm_template)
        _main_bb = _rects["main"]
        _sub_bbox = _rects["sub"]
        plot_x_right = _main_bb.x1

        def X(v):
            return rigor._lin(v, x_min, x_max, plot_x_left, plot_x_right)

    _series_ctx = rigor.SeriesContext(
        ids=[c.get("name", tr("curve {i}", i=i + 1)) for i, c in enumerate(curves)],
        pal=pal,
        series_colors=series_colors,
    )

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

    n_samp = 80
    sample_ts = [x_min + i * (x_max - x_min) / (n_samp - 1) for i in range(n_samp)]
    for ci, (c, res) in enumerate(zip(curves, fit_results)):
        color = series_colors[ci]
        if res.get("ok"):
            if res["fit_type"] == "exp1":
                line_pts = [(X(t), Y(_apply_exp1(t, res["A"], res["k"], res["B"]))) for t in sample_ts]
            else:
                line_pts = [(X(t), Y(_apply_linear(t, res["slope"], res["intercept"]))) for t in sample_ts]
            line_pts = [(x, max(min(y, plot_y_bot), plot_y_top)) for x, y in line_pts]
            parts.append(rigor.draw_fit_line(line_pts, pal=pal, color=color, stroke_w=2.0))

    # Draw raw-data lines + points + error bars.
    _emitted_circles = set()
    for ci, c in enumerate(curves):
        color = series_colors[ci]
        times = c.get("time", []) or []
        values = c.get("value", []) or []
        errs = c.get("err", []) or [0.0] * len(times)
        # A requested model is a separate layer; otherwise the supplied data
        # itself is the main line, including non-monotonic pulse responses.
        if len(times) >= 2:
            pts = [(X(t), Y(v)) for t, v in zip(times, values)]
            d = " ".join(f"{'M' if i == 0 else 'L'} {x:.1f} {y:.1f}" for i, (x, y) in enumerate(pts))
            line_style = (
                'stroke-width="1.0" stroke-dasharray="2 3" opacity="0.55"'
                if fit_results[ci].get("ok")
                else 'stroke-width="2.0"'
            )
            parts.append(f'<path d="{d}" fill="none" stroke="{color}" {line_style}/>')
        for t, v, e in zip(times, values, errs):
            cx, cy = X(t), Y(v)
            key = (round(cx, 1), round(cy, 1))
            if e and e > 0:
                parts.append(
                    rigor.draw_error_bar(
                        cx,
                        cy,
                        err_up=cy - Y(v + e),
                        err_dn=Y(v - e) - cy,
                        pal=pal,
                        color=color,
                        width=9.0,
                        stroke_w=1.1,
                    )
                )
            if key in _emitted_circles:
                # Skip the duplicate circle but keep the error bar; downstream
                # curves still render their own lines so the series stays visible.
                continue
            _emitted_circles.add(key)
            parts.append(
                f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="4" fill="{color}" stroke="{pal["ink"]}" stroke-width="0.6"/>'
            )

    parts.append(
        rigor.draw_x_axis(
            plot_x_left,
            plot_x_right,
            plot_y_bot,
            x_ticks,
            x_min,
            x_max,
            unit="",  # The axis title below already carries the unit.
            pal=pal,
            fs_tick=fs["ytick"],
            fs_title=fs["yaxis"],
            title=f"{time_label} ({time_unit})" if time_label else tr("Time ({unit})", unit=time_unit),
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
            unit="",  # Avoid a second, floating unit beside the title block.
            pal=pal,
            fs_tick=fs["ytick"],
            fs_title=fs["yaxis"],
            title=tr("{label} ({unit})", label=tr(value_label), unit=value_unit) if value_unit else tr(value_label),
            side="left",
        )
    )

    # stats box — rate constants are inlined into the legend labels below so
    # the box no longer floats over the plot area. Keep ``show_rate_constants``
    # as the gate so callers that opt out still get a bare curve plot.
    _legend_k_suffix = {}
    if show_rate_constants:
        for ci, (c, res) in enumerate(zip(curves, fit_results)):
            name = c.get("name", tr("curve {i}", i=ci + 1))
            if res.get("ok") and res["fit_type"] == "exp1":
                _legend_k_suffix[ci] = f"  k={res['k']:.3g} {time_unit}⁻¹"
            elif res.get("ok") and res["fit_type"] == "linear":
                slope_unit = f"{value_unit}/{time_unit}" if value_unit else f"{time_unit}⁻¹"
                _legend_k_suffix[ci] = f"  slope={res['slope']:.3g} {slope_unit}"
            else:
                _legend_k_suffix[ci] = ""

    if len(curves) > 1:
        lg_fs = max(13.0, fs["legend"])
        # Place below the x-axis title band — draw_x_axis consumes roughly fs_tick + fs_title + 18 px below plot_y_bot.
        _tick_fs = max(13.0, fs["ytick"])
        _title_fs = max(13.0, fs["yaxis"])
        lg_y = plot_y_bot + _tick_fs + _title_fs + 46
        lg_x = plot_x_left
        for ci, c in enumerate(curves):
            color = series_colors[ci]
            name = c.get("name", tr("curve {i}", i=ci + 1))
            label = f"{name}{_legend_k_suffix.get(ci, '')}"
            parts.append(
                f'<circle cx="{lg_x:.1f}" cy="{lg_y - lg_fs * 0.35:.1f}" r="5" '
                f'fill="{color}" stroke="{pal["ink"]}" stroke-width="0.6"/>'
            )
            parts.append(
                f'<text x="{lg_x + 10:.1f}" y="{lg_y:.1f}" font-size="{lg_fs}" '
                f'fill="{pal["ink"]}">{_xesc(label)}</text>'
            )
            lg_x += 10 + _estimate_label_width_px(str(label), lg_fs, font_family=body_font) + 24
            # wrap to next row if we exceed plot_x_right
            if lg_x > plot_x_right - 50 and ci < len(curves) - 1:
                lg_x = plot_x_left
                lg_y += lg_fs * 1.5
    elif show_rate_constants and len(curves) == 1 and _legend_k_suffix.get(0):
        # Single curve: still show the k value just below the plot in a
        # small italic caption rather than inside the plot.
        cap_fs = max(13.0, fs["legend"])
        cap_text = (curves[0].get("name") or "fit") + _legend_k_suffix[0]
        parts.append(
            f'<text x="{plot_x_left:.1f}" y="{plot_y_bot + fs["ytick"] + fs["yaxis"] + 46:.1f}" font-size="{cap_fs}" '
            f'fill="{pal["ink6"]}" font-style="italic">{_xesc(cap_text)}</text>'
        )

    if _sub_bbox is not None and _mm_mode == "with_rate_bars":
        _render_rate_bars_sub(
            parts,
            _sub_bbox,
            curves,
            _k_values,
            _series_ctx,
            pal=pal,
            fs=fs,
            body_font=body_font,
            time_unit=time_unit,
        )

    footer_layout = ChartLayout(W, H, pal, font_family)
    for index, line in enumerate(foot_lines):
        footer_layout.text(line, 28, H - footer_height + 12 + index * foot_fs * 1.35, fs=foot_fs, color=pal["ink6"])
    parts.extend(footer_layout.parts)

    return rigor.wrap_svg(parts, W, H, body_font)


# Multi-mode sub-panel renderer: horizontal bars for rate constants k.
def _render_rate_bars_sub(
    parts,
    sub_bbox,
    curves,
    k_values,
    series_ctx,
    *,
    pal,
    fs,
    body_font,
    time_unit,
):
    """Horizontal bar chart of per-curve rate constant k."""
    sx0, sy0 = sub_bbox.x0, sub_bbox.y0
    sx1, sy1 = sub_bbox.x1, sub_bbox.y1
    ink = pal.get("ink", "rgba(28,28,26,1)")
    ink6 = pal.get("ink6", "rgba(28,28,26,0.6)")

    rows = []
    for i, (c, k) in enumerate(zip(curves, k_values)):
        if k is None or not math.isfinite(k):
            continue
        name = c.get("name", tr("curve {i}", i=i + 1))
        rows.append({"name": name, "k": k})
    if not rows:
        return

    _pad_left = 70.0
    _pad_right = 16.0
    _pad_top = 24.0
    _pad_bot = 36.0
    ax_x0 = sx0 + _pad_left
    ax_x1 = sx1 - _pad_right
    ax_y0 = sy0 + _pad_top
    ax_y1 = sy1 - _pad_bot
    row_h = (ax_y1 - ax_y0) / max(1, len(rows))

    k_max = max(r["k"] for r in rows)
    k_min = 0.0
    x_ticks, x_vmin, x_vmax = rigor.nice_axis(k_min, k_max, 4)

    def X(v):
        return rigor._lin(v, x_vmin, x_vmax, ax_x0, ax_x1)

    _sub_title_fs = max(11.0, fs["label"])
    parts.append(
        f'<text x="{sx0:.1f}" y="{sy0 + _sub_title_fs:.1f}" '
        f'font-size="{_sub_title_fs:.1f}" fill="{ink6}" font-style="italic">'
        f"{_xesc(tr('Rate constants k'))}</text>"
    )

    row_label_fs = max(10.0, fs["label"] - 1)
    bar_h = max(6.0, row_h * 0.6)
    for i, r in enumerate(rows):
        y_center = ax_y0 + (i + 0.5) * row_h
        color = series_ctx.color_of(r["name"])
        # Row label on the left — wrap in halo so axis-tick-labels and gridlines
        # beneath don't bleed through.
        parts.append(
            rigor.draw_label_with_halo(
                ax_x0 - 8,
                y_center + row_label_fs * 0.33,
                str(r["name"]),
                pal,
                fs=row_label_fs,
                anchor="end",
                color=ink,
                bold=True,
                font_family=body_font,
            )
        )
        bx0 = X(0.0)
        bx1 = X(r["k"])
        parts.append(
            f'<rect x="{bx0:.1f}" y="{y_center - bar_h * 0.5:.1f}" '
            f'width="{(bx1 - bx0):.1f}" height="{bar_h:.1f}" '
            f'fill="{color}" stroke="{ink}" stroke-width="0.6" opacity="0.85"/>'
        )
        # Value label at bar end — halo keeps the "0.5" readable when the bar
        # tip grazes the sub-panel X gridline.
        val_fs = max(10.0, fs["label"] - 1)
        val_x = bx1 + 4
        val_anchor = "start"
        # if too close to right edge, place inside bar
        if bx1 + 60 > ax_x1:
            val_x = bx1 - 4
            val_anchor = "end"
        parts.append(
            rigor.draw_label_with_halo(
                val_x,
                y_center + val_fs * 0.33,
                f"{r['k']:.3g}",
                pal,
                fs=val_fs,
                anchor=val_anchor,
                color=ink,
                font_family=body_font,
            )
        )

    sub_fs_tick = max(10.0, fs["ytick"] * 0.88)
    sub_fs_title = max(10.0, fs["yaxis"] * 0.88)
    parts.append(
        rigor.draw_x_axis(
            ax_x0,
            ax_x1,
            ax_y1,
            x_ticks,
            x_vmin,
            x_vmax,
            pal=pal,
            fs_tick=sub_fs_tick,
            fs_title=sub_fs_title,
            title=f"k ({time_unit}⁻¹)" if time_unit else "k",
            show_tick_labels=True,
        )
    )
