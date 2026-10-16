"""Dose-response curve with 4-parameter logistic (4PL) sigmoid fit, CI band, EC50
marker and Hill-slope summary. Pure stdlib (Nelder-Mead for the fit).
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
from ._shared import tr


# Multi-mode whitelist: with_potency_summary → horizontal dumbbell/dot of log(EC50) per curve. Trigger: n_curves >= 2.
# Validator: at least two curves have usable EC50 fits.
def _dose_response_count_curves(signals):
    """Count distinct dose-response curves (groups) from signals dict."""
    return int(signals.get("n_curves", 0))


def _validate_potency_summary(signals):
    good = signals.get("n_curves_with_fit", 0)
    if good < 2:
        return (False, f"need >=2 curves with EC50 fit (got {good})")
    return (True, "")


_DOSE_RESPONSE_MULTI_WHITELIST = {
    "with_potency_summary": (
        "top_bottom_3to1",
        lambda s: _dose_response_count_curves(s) >= 2,
        lambda s: _validate_potency_summary(s),
    ),
}


# 4PL sigmoid + Nelder-Mead fit (pure stdlib)
def _sigmoid4pl(x: float, bottom: float, top: float, ec50: float, hill: float) -> float:
    """4-parameter logistic (log-logistic): bottom + (top-bottom)/(1+(ec50/x)^hill)."""
    x = max(x, 1e-30)
    ec50 = max(ec50, 1e-30)
    try:
        return bottom + (top - bottom) / (1.0 + (ec50 / x) ** hill)
    except (OverflowError, ValueError):
        # If (ec50/x)^hill overflows, return bottom or top depending on sign.
        if (ec50 / x) > 1 and hill > 0:
            return bottom
        return top


def _loss_4pl(params, xs, ys):
    bottom, top, ec50, hill = params
    s = 0.0
    for x, y in zip(xs, ys):
        yhat = _sigmoid4pl(x, bottom, top, ec50, hill)
        s += (yhat - y) ** 2
    return s


def _fit_4pl(xs, ys, max_iter: int = 200):
    """Nelder-Mead on (bottom, top, ec50, hill). Returns (params, loss, ok)."""
    if len(xs) < 3:
        return (min(ys), max(ys), xs[len(xs) // 2] if xs else 1.0, 1.0), float("inf"), False
    bottom0 = min(ys)
    top0 = max(ys)
    # ec50: dose that gives mid-response (closest to (top+bottom)/2)
    mid = (bottom0 + top0) * 0.5
    best_i = min(range(len(xs)), key=lambda i: abs(ys[i] - mid))
    ec50_0 = max(xs[best_i], 1e-9)
    hill0 = 1.0
    x0 = [bottom0, top0, ec50_0, hill0]
    n = len(x0)
    simplex = [list(x0)]
    for i in range(n):
        pt = list(x0)
        step = 0.05 * (abs(pt[i]) if abs(pt[i]) > 1e-6 else 1.0)
        pt[i] += step
        simplex.append(pt)
    f = [_loss_4pl(p, xs, ys) for p in simplex]
    alpha, gamma, rho, sigma = 1.0, 2.0, 0.5, 0.5
    for _ in range(max_iter):
        order = sorted(range(n + 1), key=lambda i: f[i])
        simplex = [simplex[i] for i in order]
        f = [f[i] for i in order]
        centroid = [sum(simplex[i][j] for i in range(n)) / n for j in range(n)]
        xr = [centroid[j] + alpha * (centroid[j] - simplex[-1][j]) for j in range(n)]
        fr = _loss_4pl(xr, xs, ys)
        if f[0] <= fr < f[-2]:
            simplex[-1] = xr
            f[-1] = fr
            continue
        if fr < f[0]:
            xe = [centroid[j] + gamma * (xr[j] - centroid[j]) for j in range(n)]
            fe = _loss_4pl(xe, xs, ys)
            if fe < fr:
                simplex[-1] = xe
                f[-1] = fe
            else:
                simplex[-1] = xr
                f[-1] = fr
            continue
        xc = [centroid[j] + rho * (simplex[-1][j] - centroid[j]) for j in range(n)]
        fc = _loss_4pl(xc, xs, ys)
        if fc < f[-1]:
            simplex[-1] = xc
            f[-1] = fc
            continue
        best = simplex[0]
        for i in range(1, n + 1):
            simplex[i] = [best[j] + sigma * (simplex[i][j] - best[j]) for j in range(n)]
            f[i] = _loss_4pl(simplex[i], xs, ys)
        if max(f) - min(f) < 1e-9:
            break
    best = simplex[0]
    best_f = f[0]
    # Accept fit if normalized loss is reasonable: compare to variance of ys
    y_mean = sum(ys) / len(ys)
    y_var = sum((y - y_mean) ** 2 for y in ys)
    # ok if we explain >= 50% of variance (very permissive — mostly to filter degenerate)
    ok = (y_var <= 0) or (best_f / y_var < 0.5)
    return tuple(best), best_f, ok


def make_dose_response(
    points,
    *,
    dose_unit: str = "nM",
    response_unit: str = "%",
    log_dose: bool = True,
    title: str | None = None,
    subtitle: str | None = None,
    figure_label: str | None = None,
    note: str | None = None,
    source: str | None = None,
    show_ec50: bool = True,
    show_fit: bool = True,
    show_hill: bool = True,
    show_ci: bool = True,
    fit_ci=None,
    ec50_ci=None,
    width: float = 1200,
    height: float = 820,
    font_family: str | None = None,
    palette=None,
    variant: str | None = None,
    multi_mode: str = "auto",
) -> str:
    """Observed dose response with a fitted 4PL curve and optional supplied CI.

    ``points`` contains ``{dose, response, err?, group?, label?}``; ``err`` is
    caller-supplied response error, not an inferred confidence interval.
    ``fit_ci={group: [(dose, lower, upper), ...]}`` supplies pointwise fit CI in
    response units. ``ec50_ci={group: (lower, upper)}`` supplies CI in dose units.
    Intervals must come from a valid analysis; state method/level in note/source.
    ``show_ci=True`` shows supplied intervals only. Residual scatter does not
    determine a confidence interval for the fitted curve or EC50.
    """
    from xml.sax.saxutils import quoteattr
    from ._chart_layout import ChartLayout, finite, wrap_lines
    from ._xy import make_xy_chart, normalize_series

    _variant_is_classic("dose_response", variant)
    W, H = finite(width, "width", minimum=400), finite(height, "height", minimum=300)
    pal = _resolve_palette(palette or "archive_ink")
    body_font, _ = _resolve_font(font_family)
    grouped = {}
    for record in points:
        row = dict(record)
        name = str(row.get("group", tr("default")))
        dose, response = finite(row["dose"], "dose"), finite(row["response"], "response")
        if dose < 0 or (log_dose and dose == 0):
            raise ValueError("dose response requires nonnegative doses, and positive doses on a log axis")
        row.update(dose=dose, response=response)
        if row.get("err") is not None:
            row["err"] = finite(row["err"], "response error", minimum=0)
        grouped.setdefault(name, []).append(row)
    if not grouped:
        return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:g} {H:g}"><text x="{W / 2:g}" y="{H / 2:g}" text-anchor="middle" font-size="16" fill={quoteattr(pal["ink6"])}>{_xesc(tr("No data"))}</text></svg>'
    names = list(grouped)
    colors = _derive_series_colors(pal, len(names))

    def supplied_map(value, name):
        if value is None:
            return {}
        if not isinstance(value, dict) or set(value) - set(names):
            raise ValueError(f"{name} must map existing group names to supplied intervals")
        return value

    supplied_curves = supplied_map(fit_ci, "fit_ci")
    supplied_ec50 = supplied_map(ec50_ci, "ec50_ci")
    fits, series, references, disclosures = {}, [], [], []
    for name, color in zip(names, colors):
        rows = grouped[name]
        doses, responses = [r["dose"] for r in rows], [r["response"] for r in rows]
        params, loss, ok = _fit_4pl(doses, responses)
        ok = (
            ok
            and len(set(doses)) >= 4
            and max(responses) > min(responses)
            and params[2] > 0
            and all(math.isfinite(v) for v in params)
        )
        fits[name] = {"params": params, "loss": loss, "ok": ok, "n": len(rows), "ec50_ci": None}
        intervals = []
        if name in supplied_curves:
            for interval in supplied_curves[name]:
                if len(interval) != 3:
                    raise ValueError("fit_ci entries require dose, lower, upper")
                d, lo, hi = [finite(v, "fit_ci value") for v in interval]
                if d < 0 or (log_dose and d == 0) or lo > hi or d < min(doses) or d > max(doses):
                    raise ValueError("fit_ci needs positive observed-range doses and lower <= upper")
                if not ok or not lo <= _sigmoid4pl(d, *params) <= hi:
                    raise ValueError("fit_ci must contain the fitted response at each supplied dose")
                intervals.append((d, lo, hi))
            intervals.sort()
            if len(intervals) < 2 or len({r[0] for r in intervals}) != len(intervals):
                raise ValueError("fit_ci requires at least two distinct doses")
        if name in supplied_ec50:
            bounds = supplied_ec50[name]
            if len(bounds) != 2:
                raise ValueError("ec50_ci requires lower and upper in dose units")
            lo, hi = [finite(v, "ec50_ci value", minimum=0) for v in bounds]
            if not ok or lo <= 0 or not lo <= params[2] <= hi:
                raise ValueError("ec50_ci must be positive and contain the fitted EC50")
            if show_ci:
                fits[name]["ec50_ci"] = (lo, hi)
        curve = []
        if show_fit and ok:
            lo_d, hi_d = min(doses), max(doses)
            sample_doses = (
                [10 ** (math.log10(lo_d) + i * (math.log10(hi_d) - math.log10(lo_d)) / 79) for i in range(80)]
                if log_dose
                else [lo_d + i * (hi_d - lo_d) / 79 for i in range(80)]
            )
            sample_doses = sorted(set(sample_doses + [r[0] for r in intervals]))
            for dose in sample_doses:
                point = {"x": dose, "y": _sigmoid4pl(dose, *params)}
                if show_ci and intervals and intervals[0][0] <= dose <= intervals[-1][0]:
                    for left, right in zip(intervals, intervals[1:]):
                        if left[0] <= dose <= right[0]:
                            t = (dose - left[0]) / (right[0] - left[0])
                            lower, upper = left[1] + t * (right[1] - left[1]), left[2] + t * (right[2] - left[2])
                            if not lower <= point["y"] <= upper:
                                raise ValueError(
                                    "interpolated supplied fit_ci does not contain the fitted curve; provide denser valid intervals"
                                )
                            point.update(lo=lower, hi=upper)
                            break
                curve.append(point)
        observed = [
            {
                "x": row["dose"],
                "y": row["response"],
                **({"y_err": row["err"]} if row.get("err") else {}),
                **({"label": row["label"]} if row.get("label") else {}),
            }
            for row in rows
        ]
        series.append({"name": name, "points": observed, "curve": curve, "color": color})
        if ok:
            if show_hill:
                disclosures.append(
                    f"{name}: EC50 = {_fmt_sci(params[2])} {dose_unit} · Hill = {params[3]:.2f} · n = {len(rows)}"
                )
            elif show_ec50:
                disclosures.append(f"{name}: EC50 = {_fmt_sci(params[2])} {dose_unit}")
            if show_ec50:
                references.append({"axis": "x", "value": params[2], "color": color})
        elif show_hill or show_ec50:
            disclosures.append(tr("{name}: 4PL fit failed · n = {n}", name=name, n=len(rows)))
    if show_ci and (supplied_curves or supplied_ec50):
        disclosures.append(tr("Intervals: supplied CI; method and level follow the source."))
    elif supplied_curves or supplied_ec50:
        disclosures.append(tr("4PL point estimates; interval display disabled."))
    elif any(info["ok"] for info in fits.values()):
        disclosures.append(tr("4PL point estimates; confidence intervals not supplied."))
    else:
        disclosures.append(tr("4PL fit unavailable; observations retained."))

    if multi_mode not in (None, "off", "single", "auto", "with_potency_summary"):
        raise ValueError("unsupported dose response multi_mode")
    good = sum(bool(info["ok"]) for info in fits.values())
    if multi_mode == "with_potency_summary" and good < 2:
        raise ValueError("with_potency_summary requires at least two successful fits")
    potency = good >= 2 and multi_mode in ("auto", "with_potency_summary")
    fs = _dist_font_sizes(W, H, max(4, len(names)))
    # Short embed canvases cap the width-driven floor so the plot keeps its height.
    floor_fs = min(W / 50, max(12.0, H / 28))
    fs["label"] = max(fs["label"], floor_fs)
    fs["ytick"] = max(fs["ytick"], floor_fs)
    fs["yaxis"] = max(fs["yaxis"], floor_fs)
    foot_fs = max(fs["foot"], min(W / 45, floor_fs * 1.1))
    footer = []
    for prefix, value in ((tr("Notes. "), note), (tr("Source. "), source)):
        if value:
            footer += wrap_lines(prefix + str(value), W - 56, foot_fs, body_font)
    footer_h = len(footer) * foot_fs * 1.35 + (20 if footer else 0)
    potency_h = fs["label"] * 1.5 + good * fs["label"] * 1.6 + fs["ytick"] * 2.5 + 36 if potency else 0
    if potency and H - potency_h - footer_h < 360:
        if multi_mode == "with_potency_summary":
            raise ValueError("dose response and potency labels require a taller canvas")
        potency, potency_h = False, 0
    main_h = H - footer_h - potency_h

    compact = H < 600
    side_w = min(300.0, max(240.0, W * 0.3)) if compact and W >= 700 else 0.0

    def side_legend():
        layout = ChartLayout(W, H, pal, font_family)
        fs_label = floor_fs
        x0, row_top = W - 28 - side_w, 59.0 if not (title or subtitle or figure_label) else 28.0
        for name, color in zip(names, colors):
            info = fits[name]
            label = name
            if info["ok"] and (show_hill or show_ec50):
                label += f" · EC50 {_fmt_sci(info['params'][2])} {dose_unit}"
            elif not info["ok"] and (show_hill or show_ec50):
                label += tr(" · fit failed")
            layout.parts.append(
                f'<circle cx="{x0 + 4:g}" cy="{row_top + fs_label * 0.5:g}" r="4" fill={quoteattr(color)}/>'
            )
            row_top += layout.text(label, x0 + 16, row_top, fs=fs_label, width=side_w - 16, color=layout.ink)
            if show_hill:
                second = f"Hill {info['params'][3]:.2f} · n {info['n']}" if info["ok"] else f"n {info['n']}"
                row_top += (
                    layout.text(second, x0 + 16, row_top + 3, fs=fs_label, width=side_w - 16, color=pal["ink6"]) + 3
                )
            row_top += 10
        row_top += layout.text(disclosures[-1], x0, row_top, fs=fs_label, width=side_w, color=pal["ink6"])
        if row_top > main_h:
            raise ValueError("dose response legend needs a taller canvas")
        return layout.parts

    def measured_legend(layout, top):
        if side_w:
            return top
        # Group identity and fitted values share compact columns instead of
        # repeating a small legend and three full-width statistical rows.
        fs_label = min(layout.font_sizes["label"], 12.0) if compact else layout.font_sizes["label"]
        widest = max(
            layout.measure(
                name
                + (
                    f" · EC50 {_fmt_sci(fits[name]['params'][2])} {dose_unit}"
                    if fits[name]["ok"]
                    else tr(" · fit failed")
                ),
                fs_label,
            )
            for name in names
        )
        columns = min(len(names), max(1, int((W - 56) // max(widest + 44, min(300, W - 56)))))
        cell_w = (W - 56) / columns
        row_top = top
        row_height = 0.0
        for index, (name, color) in enumerate(zip(names, colors)):
            if index and index % columns == 0:
                row_top += row_height + (3 if compact else 10)
                row_height = 0.0
            x = 28 + (index % columns) * cell_w
            info = fits[name]
            label = name
            if info["ok"] and (show_hill or show_ec50):
                label += f" · EC50 {_fmt_sci(info['params'][2])} {dose_unit}"
            elif not info["ok"] and (show_hill or show_ec50):
                label += tr(" · fit failed")
            layout.parts.append(
                f'<circle cx="{x + 4:g}" cy="{row_top + fs_label * 0.5:g}" r="4" fill={quoteattr(color)}/>'
            )
            if compact and show_hill:
                label += f" · Hill {info['params'][3]:.2f} · n {info['n']}" if info["ok"] else f" · n {info['n']}"
            used = layout.text(label, x + 16, row_top, fs=fs_label, width=cell_w - 28, color=layout.ink)
            if show_hill and not compact:
                second = f"Hill {info['params'][3]:.2f} · n {info['n']}" if info["ok"] else f"n {info['n']}"
                used += (
                    layout.text(second, x + 16, row_top + used + 3, fs=fs_label, width=cell_w - 28, color=pal["ink6"])
                    + 3
                )
            row_height = max(row_height, used)
        row_top += row_height + (3 if compact else 10)
        return row_top + layout.text(disclosures[-1], 28, row_top, fs=fs_label, width=W - 56, color=pal["ink6"]) + 8

    for entry in series:
        entry["_legend"] = False
    main = make_xy_chart(
        normalize_series(series),
        width=W - (side_w + 20 if side_w else 0),
        height=main_h,
        palette=pal,
        font_family=font_family,
        title=title,
        subtitle=subtitle,
        figure_label=figure_label,
        x_title=tr("Dose ({unit})", unit=dose_unit) if dose_unit else tr("Dose"),
        y_title=tr("Response ({unit})", unit=response_unit) if response_unit else tr("Response"),
        x_transform="log10" if log_dose else "linear",
        reference_lines=references,
        legend_renderer=measured_legend,
        n_items=len(names),
        minimum_font_size=floor_fs,
    )
    body = main.split(">", 1)[1].rsplit("</svg>", 1)[0]
    parts = [body] + (side_legend() if side_w else [])
    if potency:
        context = rigor.SeriesContext(ids=names, pal=pal, series_colors=colors)
        _render_potency_summary_sub(
            parts,
            rigor.BBox(28, main_h, W - 28, H - footer_h),
            names,
            fits,
            context,
            pal=pal,
            fs=fs,
            body_font=body_font,
            dose_unit=dose_unit,
        )
    footer_layout = ChartLayout(W, H, pal, font_family)
    for i, line in enumerate(footer):
        footer_layout.text(line, 28, H - footer_h + i * foot_fs * 1.35, fs=foot_fs, color=pal["ink6"])
    parts += footer_layout.parts
    background = f'<rect width="{W:g}" height="{H:g}" fill={quoteattr(pal["bg"])}/>' if pal.get("bg") else ""
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:g} {H:g}" font-family={quoteattr(body_font)}>{background}{"".join(parts)}</svg>'


def _fmt_sci(v: float) -> str:
    """Format a number for annotation: 3 sig figs, scientific when very small/large."""
    if v is None or not math.isfinite(v):
        return "—"
    av = abs(v)
    if av == 0:
        return "0"
    if av < 0.01 or av >= 1000:
        return f"{v:.2e}"
    return f"{v:.3g}"


# Multi-mode sub-panel renderer: horizontal potency-summary (log(EC50) per curve)
def _render_potency_summary_sub(
    parts,
    sub_bbox,
    groups_order,
    fits,
    series_ctx,
    *,
    pal,
    fs,
    body_font,
    dose_unit,
):
    """Horizontal dumbbell / dot plot of log10(EC50) per curve."""
    sx0, sy0 = sub_bbox.x0, sub_bbox.y0
    sx1, sy1 = sub_bbox.x1, sub_bbox.y1
    ink = pal.get("ink", "rgba(28,28,26,1)")
    ink6 = pal.get("ink6", "rgba(28,28,26,0.6)")

    # Only rows with a successful fit go into the plot.
    rows = []
    for g in groups_order:
        info = fits.get(g)
        if info is None or not info["ok"]:
            continue
        ec50 = info["params"][2]
        hill = info["params"][3]
        if ec50 is None or not math.isfinite(ec50) or ec50 <= 0:
            continue
        log_ec50 = math.log10(ec50)
        bounds = info.get("ec50_ci")
        rows.append(
            {
                "name": g,
                "log_ec50": log_ec50,
                "hill": hill,
                "ci_lo": math.log10(bounds[0]) if bounds else log_ec50,
                "ci_hi": math.log10(bounds[1]) if bounds else log_ec50,
                "has_ci": bool(bounds),
            }
        )
    if not rows:
        return

    # Pad for row-labels on left, headroom for title line.
    row_label_fs = max(14.0, fs["label"])
    _pad_left = max(
        90.0,
        max(_estimate_label_width_px(str(r["name"]), row_label_fs, bold=True, font_family=body_font) for r in rows)
        + 16,
    )
    _pad_right = 20.0
    _pad_top = fs["label"] * 1.5 + 12
    _pad_bot = fs["ytick"] * 2.5 + 20 + max(0.0, fs["yaxis"] - fs["ytick"])
    ax_x0 = sx0 + _pad_left
    ax_x1 = sx1 - _pad_right
    ax_y0 = sy0 + _pad_top
    ax_y1 = sy1 - _pad_bot
    row_h = (ax_y1 - ax_y0) / max(1, len(rows))

    # X range: span of (ci_lo .. ci_hi) across all rows + 10% padding.
    xs_all = []
    for r in rows:
        xs_all.extend([r["ci_lo"], r["ci_hi"], r["log_ec50"]])
    v_min = min(xs_all)
    v_max = max(xs_all)
    if v_max <= v_min:
        v_min -= 0.5
        v_max += 0.5
    _span = v_max - v_min
    v_min -= _span * 0.08
    v_max += _span * 0.08
    sub_x_ticks, sub_xmin, sub_xmax = rigor.nice_axis(v_min, v_max, 5)

    def X(v):
        return rigor._lin(v, sub_xmin, sub_xmax, ax_x0, ax_x1)

    _sub_title_fs = max(11.0, fs["label"])
    parts.append(
        f'<text x="{sx0:.1f}" y="{sy0 + _sub_title_fs:.1f}" '
        f'font-size="{_sub_title_fs:.1f}" fill="{ink6}" font-style="italic">'
        f"{_xesc(tr('EC50 estimates · supplied CI · point area ∝ |Hill|' if any(r['has_ci'] for r in rows) else 'EC50 estimates · point area ∝ |Hill|'))}</text>"
    )

    all_hills = [abs(r["hill"]) for r in rows]
    hill_max = max(all_hills) if all_hills else 1.0
    hill_max = max(hill_max, 1e-9)
    r_max = 9.0

    def _radius(h):
        return r_max * math.sqrt(min(1.0, abs(h) / hill_max))

    row_label_fs = max(14.0, fs["label"])
    for i, r in enumerate(rows):
        y_center = ax_y0 + (i + 0.5) * row_h
        color = series_ctx.color_of(r["name"])
        parts.append(
            f'<text x="{ax_x0 - 8:.1f}" y="{y_center + row_label_fs * 0.33:.1f}" '
            f'font-size="{row_label_fs:.1f}" fill="{ink}" '
            f'text-anchor="end" font-weight="600">{_xesc(str(r["name"]))}</text>'
        )
        if r["has_ci"]:
            x_lo = X(r["ci_lo"])
            x_hi = X(r["ci_hi"])
            parts.append(
                f'<line x1="{x_lo:.1f}" y1="{y_center:.1f}" '
                f'x2="{x_hi:.1f}" y2="{y_center:.1f}" '
                f'stroke="{color}" stroke-width="1.6" opacity="0.75" data-role="ec50-confidence-interval" data-log-low="{r["ci_lo"]:.12g}" data-log-high="{r["ci_hi"]:.12g}"/>'
            )
            for xp in (x_lo, x_hi):
                parts.append(
                    f'<line x1="{xp:.1f}" y1="{y_center - 4:.1f}" '
                    f'x2="{xp:.1f}" y2="{y_center + 4:.1f}" '
                    f'stroke="{color}" stroke-width="1.4" opacity="0.75"/>'
                )
        # EC50 dot (size encodes Hill).
        cx = X(r["log_ec50"])
        rr = _radius(r["hill"])
        parts.append(
            f'<circle cx="{cx:.2f}" cy="{y_center:.2f}" r="{rr:.2f}" fill="{color}" stroke="{ink}" stroke-width="0.6"/>'
        )

    # Sub X axis along the bottom of the sub bbox.
    sub_fs_tick = fs["ytick"]
    sub_fs_title = fs["yaxis"]
    parts.append(
        rigor.draw_x_axis(
            ax_x0,
            ax_x1,
            ax_y1,
            sub_x_ticks,
            sub_xmin,
            sub_xmax,
            pal=pal,
            fs_tick=sub_fs_tick,
            fs_title=sub_fs_title,
            title=f"log10(EC50 / {dose_unit})" if dose_unit else "log10(EC50)",
            show_tick_labels=True,
        )
    )
