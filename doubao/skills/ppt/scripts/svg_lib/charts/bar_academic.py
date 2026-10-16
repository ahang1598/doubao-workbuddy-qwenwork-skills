"""Academic bar chart with error bars, jittered sample points, N-labels, and
inter-group significance brackets. Pure stdlib — no matplotlib / numpy / scipy.
"""

from __future__ import annotations

import math

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
    ridge_density_from_samples,
)
from . import _academic_rigor as rigor


# Multi-mode whitelist: maps mode name → (template, trigger, validator). Dict insertion order defines priority under
# multi_mode="auto".
def _validate_distribution(s):
    """Need >= 2 groups with raw values (not just mean+err), each >= 5 samples."""
    groups = s.get("groups_values") or []
    if len(groups) < 2:
        return (False, "need >= 2 groups")
    for i, vals in enumerate(groups):
        if not vals or len(vals) < 5:
            return (False, f"group {i} has < 5 raw values")
    return (True, "")


def _validate_pairwise_matrix(s):
    """Need 4..8 groups, each with means (and ideally n>=1 values)."""
    groups = s.get("groups_values") or []
    n_g = len(groups)
    if n_g < 4 or n_g > 8:
        return (False, f"need 4<=n_groups<=8, got {n_g}")
    for i, vals in enumerate(groups):
        if not vals:
            return (False, f"group {i} has no values")
    return (True, "")


_BAR_ACADEMIC_MULTI_WHITELIST = {
    "with_distribution": (
        "top_bottom_3to1",
        lambda s: len(s.get("groups_values") or []) >= 2 and all(len(v) >= 5 for v in (s.get("groups_values") or [])),
        lambda s: _validate_distribution(s),
    ),
    "with_pairwise_matrix": (
        "left_right_1to1",
        lambda s: 4 <= len(s.get("groups_values") or []) <= 8,
        lambda s: _validate_pairwise_matrix(s),
    ),
}


def _mean(xs):
    if not xs:
        return 0.0
    from ._categorical import sample_summary

    return sample_summary(xs, "SD")["value"]


def _sd(xs):
    """Sample standard deviation, centered before magnitude scaling."""
    if len(xs) < 2:
        return 0.0
    from ._categorical import sample_summary

    return sample_summary(xs, "SD")["sd"]


def _sem(xs):
    n = len(xs)
    if n < 2:
        return 0.0
    return _sd(xs) / math.sqrt(n)


def _ci95(xs):
    """Two-sided Student-t 95% confidence interval of the sample mean."""
    if len(xs) < 2:
        raise ValueError("CI95 requires at least two observations per group")
    return rigor.student_t_critical(len(xs) - 1) * _sem(xs)


def _err_halfwidth(xs, kind):
    if kind == "SD":
        return _sd(xs)
    if kind == "CI95":
        return _ci95(xs)
    if kind == "SEM":
        return _sem(xs)
    raise ValueError("error_kind must be SD, SEM or CI95")


def _fmt_pvalue(p):
    if p is None or not math.isfinite(p):
        return "ns"
    if p < 0.001:
        return "P < 0.001"
    return f"P = {p:.3f}"


def make_bar_academic(
    groups,
    *,
    y_unit: str = "",
    orientation: str = "vertical",
    stack: str | None = None,
    axis_break=None,
    line_series=None,
    right_y_unit: str = "",
    right_y_title: str | None = None,
    value_domain=None,
    x_title: str | None = None,
    y_title: str | None = None,
    title: str | None = None,
    subtitle: str | None = None,
    figure_label: str | None = None,
    note: str | None = None,
    source: str | None = None,
    error_kind: str = "SEM",
    show_points: bool = True,
    pairwise_p=None,
    auto_test: str | None = None,
    pairs=None,
    highlight_group: str | None = None,
    width: float = 1200,
    height: float = 760,
    font_family: str | None = None,
    palette=None,
    variant: str | None = None,
    multi_mode: str = "auto",
    value_scale: str = "auto",
) -> str:
    """Single/multi-group academic bar chart."""
    _variant_is_classic("bar_academic", variant)
    from ._categorical import make_categorical, normalize_cell

    extended = (
        orientation != "vertical"
        or stack not in (None, "none")
        or axis_break is not None
        or line_series is not None
        or value_domain is not None
    )
    extended = (
        extended
        or multi_mode in ("single", "off", None)
        or any(isinstance(g, dict) or isinstance(g[1], dict) or g[1] is None for g in groups)
    )
    if extended:
        if multi_mode not in ("auto", "single", "off", None):
            raise ValueError("extended categorical options require single mode")
        categories, cells = [], []
        for group in groups:
            if isinstance(group, dict):
                categories.append(str(group["name"]))
                cells.append({k: v for k, v in group.items() if k != "name"})
            else:
                categories.append(str(group[0]))
                cells.append(group[1])
        return make_categorical(
            categories,
            [("Observations", cells)],
            orientation=orientation,
            stack=stack,
            axis_break=axis_break,
            line_series=line_series,
            right_y_unit=right_y_unit,
            right_y_title=right_y_title,
            value_domain=value_domain,
            single=True,
            y_unit=y_unit,
            x_title=x_title,
            y_title=y_title,
            title=title,
            subtitle=subtitle,
            figure_label=figure_label,
            note=note,
            source=source,
            error_kind=error_kind,
            show_points=show_points,
            pairwise_p=pairwise_p,
            auto_test=auto_test,
            pairs=pairs,
            width=width,
            height=height,
            font_family=font_family,
            palette=palette,
            highlight=highlight_group,
            value_scale=value_scale,
        )
    groups = [(str(name), normalize_cell(vals, error_kind)["replicates"]) for name, vals in groups]
    if not groups:
        raise ValueError("groups must be a non-empty list of (name, values).")
    for i, g in enumerate(groups):
        if not g or len(g) != 2:
            raise ValueError(f"groups[{i}] must be (name, values).")
        if not g[1]:
            raise ValueError(f"groups[{i}] ('{g[0]}') has no values.")
    # bar_academic is designed for group-wise statistical comparison with
    # error bars, jittered points and significance brackets. With a single
    # replicate per group it collapses to a plain bar — pick a different form.
    if all(len(g[1]) == 1 for g in groups):
        raise ValueError(
            "bar_academic needs >=2 replicates per group for error bars and jitter; "
            "every group has only 1 value. For single-point category comparisons use "
            "grouped_bar with summary values; "
            "do not infer intervals from single estimates."
        )
    if pairwise_p is not None and (auto_test is not None or pairs is not None):
        raise ValueError("Cannot specify pairwise_p together with auto_test/pairs. Use one API.")
    if auto_test is not None and pairs is None:
        raise ValueError("auto_test requires pairs. Pass pairs=[(i,j), ...] or pairs='all' / 'sensible'.")
    if pairs is not None and auto_test is None:
        raise ValueError("pairs requires auto_test. Pass auto_test='welch' / 'student' / 'mann_whitney'.")
    if auto_test is not None:
        from svg_lib.charts._academic_rigor import _PAIRWISE_TESTS, pairwise_test

        group_values = [vals for (_, vals) in groups]
        if isinstance(pairs, str):
            pairwise_p = pairwise_test(group_values, method=auto_test, pair_strategy=pairs)
        elif isinstance(pairs, (list, tuple)):
            if auto_test not in _PAIRWISE_TESTS:
                raise ValueError(f"auto_test must be one of {list(_PAIRWISE_TESTS)}")
            test_fn = _PAIRWISE_TESTS[auto_test]
            pairwise_p = [(i, j, test_fn(group_values[i], group_values[j])) for (i, j) in pairs]
        else:
            raise ValueError("pairs must be list of (i, j) tuples, 'all', or 'sensible'")
    if palette is None:
        palette = "archive_ink"
    pal = _resolve_palette(palette)
    body_font, heading_font = _resolve_font(font_family)
    W, H = float(width), float(height)

    n_groups = len(groups)
    total_points = sum(len(g[1]) for g in groups)
    fs = _dist_font_sizes(W, H, max(4, n_groups))

    stats = []
    for name, vals in groups:
        m = _mean(vals)
        e = _err_halfwidth(vals, error_kind) if len(vals) >= 2 else None
        stats.append({"name": name, "vals": vals, "mean": m, "err": e, "n": len(vals)})

    # Y range: include all raw points (so jitter dots don't clip)
    all_v = []
    for s in stats:
        all_v.extend(s["vals"])
        if s["err"] is not None:
            all_v.append(s["mean"] + s["err"])
            all_v.append(s["mean"] - s["err"])
    y_lo, y_hi = min(all_v), max(all_v)
    # Pad top to reserve ~20% headroom for significance brackets
    if pairwise_p:
        y_hi = y_hi + (y_hi - y_lo) * 0.25
    else:
        y_hi = y_hi + (y_hi - y_lo) * 0.08
    # If all values positive, anchor baseline at 0 (standard bar practice)
    if y_lo >= 0:
        y_lo = 0.0
    y_ticks, y_min, y_max = rigor.nice_axis(y_lo, y_hi, 5)

    max_tick_w = 0.0
    span_y = y_max - y_min
    for v in y_ticks:
        s_ = _fmt_axis(v, span_y if span_y > 0 else abs(v) or 1)
        max_tick_w = max(max_tick_w, _estimate_label_width_px(s_, fs["ytick"], font_family=body_font))
    margin_left = max_tick_w + 70  # tick label + axis title room
    margin_right = 50
    # margin_top: title block (title + subtitle) + unit-chip gap + ascender of
    # top tick label. Scale with subtitle/title font sizes rather than hard-coding
    # 110px — at large fs ("medium" renders use ytick=22), a static margin pushed
    # the unit chip into the subtitle line.
    _title_h = (
        (fs["title"] if title else 0) + (fs["subtitle"] if subtitle else 0) + (fs["figure"] if figure_label else 0)
    )
    margin_top = max(130.0, _title_h + fs["ytick"] * 0.9 + 48)
    margin_bot = 150  # x axis title + n-label + note/source

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
        "n_groups": n_groups,
        "groups_values": [list(s["vals"]) for s in stats],
        "groups_means": [s["mean"] for s in stats],
        "groups_names": [s["name"] for s in stats],
    }
    _mm_mode, _mm_template, _mm_reason = rigor.resolve_multi_mode_v2(
        multi_mode,
        _BAR_ACADEMIC_MULTI_WHITELIST,
        _mm_signals,
        _full_plot_bbox,
    )
    _sub_bbox = None
    _main_bbox = None
    _in_distribution_sub = False
    if _mm_mode is not None and _mm_template is not None:
        _rects = rigor.allocate_main_sub(_full_plot_bbox, _mm_template)
        _main_bbox = _rects["main"]
        _sub_bbox = _rects["sub"]
        # Shrink main plot box for the historic draw path.
        if _mm_template == "top_bottom_3to1":
            _in_distribution_sub = _mm_mode == "with_distribution"
            if _in_distribution_sub:
                # Reserve ~ (group label + n label + x title gap) worth of space between main plot bottom and sub-panel
                # top. Shrink main plot further so there is a clean label strip in between.
                _label_strip = fs["group"] + fs["group_n"] + 30
                plot_y_bot = min(_main_bbox.y1, _sub_bbox.y0 - _label_strip - 10)
            else:
                plot_y_bot = _main_bbox.y1
        elif _mm_template.startswith("left_right"):
            plot_x_right = _main_bbox.x1

    def Y(v):
        return rigor._lin(v, y_min, y_max, plot_y_bot, plot_y_top)

    plot_w = plot_x_right - plot_x_left
    slot_w = plot_w / n_groups
    bar_w = min(slot_w * 0.55, 90)  # thinner when many groups

    group_centers = [plot_x_left + slot_w * (i + 0.5) for i in range(n_groups)]

    parts = rigor.draw_canvas_bg(pal, W, H)

    # title block — anchor well above the plot top so the subtitle baseline
    # does not collide with the Y-axis unit chip (which lives just above the
    # top tick label). Using plot_y_top - 36 instead of -24 reserves ~12px
    # extra breathing room for the unit chip at large font sizes.
    parts.append(
        rigor.draw_title_block(
            plot_x_left,
            plot_y_top - 36,
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

    accent = pal["accent"]
    pal.get("secondary", pal["ink6"])
    ink6 = pal["ink6"]
    ink = pal["ink"]
    # Per-group distinct colors so multi-group academic bars don't collapse to one accent fill.
    series_cols = _pick_series_colors(pal, n_groups)
    y_zero = Y(max(0.0, y_min))  # baseline for bars when y_min<=0

    for i, s in enumerate(stats):
        cx = group_centers[i]
        is_hi = highlight_group is not None and s["name"] == highlight_group
        fill_color = accent if is_hi else series_cols[i % len(series_cols)]
        bar_fill = f"{_rgb_prefix(fill_color)}0.55)"
        bar_stroke = fill_color
        top_y = Y(s["mean"])
        bot_y = y_zero
        if top_y > bot_y:
            top_y, bot_y = bot_y, top_y
        parts.append(
            f'<rect x="{cx - bar_w / 2:.2f}" y="{top_y:.2f}" '
            f'width="{bar_w:.2f}" height="{(bot_y - top_y):.2f}" '
            f'fill="{bar_fill}" stroke="{bar_stroke}" stroke-width="1.4"/>'
        )

    # jitter points (over bars but under error bars)
    if show_points:
        for i, s in enumerate(stats):
            cx = group_centers[i]
            ys = [Y(v) for v in s["vals"]]
            parts.append(
                rigor.draw_jittered_points(
                    cx,
                    ys,
                    bar_w,
                    pal=pal,
                    seed=i * 97 + 13,
                    r=max(2.0, 3.0 - 0.03 * total_points),
                    alpha=0.65,
                    color=pal["ink"],
                )
            )

    for i, s in enumerate(stats):
        if s["err"] is None:
            continue
        cx = group_centers[i]
        cy = Y(s["mean"])
        err_up_px = abs(Y(s["mean"] + s["err"]) - cy)
        err_dn_px = abs(Y(s["mean"] - s["err"]) - cy)
        parts.append(
            rigor.draw_error_bar(
                cx,
                cy,
                err_up_px,
                err_dn_px,
                pal=pal,
                kind=error_kind,
                width=min(bar_w * 0.6, 22),
                color=pal["ink"],
                stroke_w=1.6,
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
            unit=y_unit,
            pal=pal,
            fs_tick=fs["ytick"],
            fs_title=fs["yaxis"],
            title=y_title,
            side="left",
        )
    )
    # X axis: categorical ticks at group centers, with error_kind suffix on x_title.
    parts.append(
        f'<line x1="{plot_x_left:.1f}" y1="{plot_y_bot:.1f}" x2="{plot_x_right:.1f}" y2="{plot_y_bot:.1f}" '
        f'stroke="{ink}" stroke-width="1.2"/>'
    )
    for i, s in enumerate(stats):
        cx = group_centers[i]
        parts.append(
            f'<line x1="{cx:.1f}" y1="{plot_y_bot:.1f}" x2="{cx:.1f}" y2="{plot_y_bot + 5:.1f}" '
            f'stroke="{ink}" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{cx:.1f}" y="{plot_y_bot + fs["group"] + 10:.1f}" '
            f'font-size="{fs["group"]:.1f}" fill="{ink}" text-anchor="middle" '
            f'font-weight="600">{_xesc(s["name"])}</text>'
        )
        parts.append(
            rigor.draw_n_label(
                cx,
                plot_y_bot + fs["group"] + fs["group_n"] + 18,
                s["n"],
                pal=pal,
                fs=fs["group_n"],
                anchor="middle",
            )
        )

    # X axis title (centered below). Suppress in with_distribution sub-panel
    # mode — the sub-panel's shared value X axis replaces the x-axis "Treatment"
    # meaning, and an extra title here would land inside the sub-panel bbox.
    if x_title and not _in_distribution_sub:
        xc = (plot_x_left + plot_x_right) * 0.5
        xt_y = plot_y_bot + fs["group"] + fs["group_n"] + 46
        parts.append(
            f'<text x="{xc:.1f}" y="{xt_y:.1f}" font-size="{fs["yaxis"]:.1f}" '
            f'fill="{ink}" text-anchor="middle" font-weight="600">{_xesc(x_title)}</text>'
        )

    # error-kind annotation (upper-left of plot) — pure disclosure
    err_lbl = f"error bars: {error_kind}" + (
        " (n ≥ 2; unavailable for n = 1)" if any(s["err"] is None for s in stats) else ""
    )
    parts.append(
        f'<text x="{plot_x_left + 4:.1f}" y="{plot_y_top + fs["label"]:.1f}" '
        f'font-size="{fs["label"]:.1f}" fill="{ink6}" font-style="italic">{_xesc(err_lbl)}</text>'
    )

    if pairwise_p:
        # sort by span so wider brackets go higher
        sorted_sig = sorted(pairwise_p, key=lambda t: abs(t[0] - t[1]))
        used_tops = []
        for a, b, p in sorted_sig:
            if a < 0 or b < 0 or a >= n_groups or b >= n_groups or a == b:
                continue
            x_a = group_centers[min(a, b)]
            x_b = group_centers[max(a, b)]
            # determine base y: max of relevant group tops (incl. error up)
            relevant = []
            for idx in (min(a, b), max(a, b)):
                relevant.append(Y(stats[idx]["mean"] + stats[idx]["err"]))
            # avoid stacking collision
            base = min(relevant) - 24
            for u_x1, u_x2, u_y in used_tops:
                # if overlap in x and bracket y too close, shift up
                if not (x_b < u_x1 - 10 or x_a > u_x2 + 10):
                    base = min(base, u_y - 32)
            # Journal format: star + explicit P-value for scannable brackets.
            if isinstance(p, str):
                from ._chart_layout import parse_p

                p = parse_p(p)
            if p is None or math.isnan(p):  # NaN check
                label_text = "ns"
            else:
                from ._chart_layout import p_label

                text = p_label(p)
                stars = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
                label_text = text if text == "ns" else f"ns ({text})" if stars == "ns" else f"{stars} {text}"
            parts.append(
                rigor.draw_sig_bracket(
                    x_a,
                    x_b,
                    base,
                    label_text,
                    pal=pal,
                    fs=fs["label"],
                    tick_h=6,
                    color=pal["ink"],
                )
            )
            used_tops.append((x_a, x_b, base))

    if _sub_bbox is not None and _mm_mode == "with_distribution":
        _render_bar_distribution_sub(
            parts,
            _sub_bbox,
            stats,
            group_centers,
            pal=pal,
            fs=fs,
            body_font=body_font,
        )
    elif _sub_bbox is not None and _mm_mode == "with_pairwise_matrix":
        _render_bar_pairwise_matrix_sub(
            parts,
            _sub_bbox,
            stats,
            pal=pal,
            fs=fs,
            body_font=body_font,
        )

    # footer: note + source
    parts.append(rigor.draw_footer(note, source, pal, fs, plot_x_left, plot_x_right, H - 20))

    return rigor.wrap_svg(parts, W, H, body_font)


def _render_bar_distribution_sub(parts, sub_bbox, stats, group_centers, *, pal, fs, body_font):
    """Ridge-style per-group KDE strip + jittered dots."""
    import random as _random

    sx0, sy0 = sub_bbox.x0, sub_bbox.y0
    sx1, sy1 = sub_bbox.x1, sub_bbox.y1
    ink = pal.get("ink", "rgba(28,28,26,1)")
    ink6 = pal.get("ink6", "rgba(28,28,26,0.6)")
    accent = pal.get("accent", "rgba(163,88,50,1)")

    n_g = len(stats)
    if n_g <= 0:
        return

    # Pad left for row label (group name)
    _pad_left = 90.0
    _pad_right = 10.0
    # Reserve enough top padding for the in-panel sub-title (one line of
    # label-size text plus 6px of breathing room).
    _pad_top = max(11.0, fs["label"]) + 10.0
    _pad_bot = 22.0
    ax_x0 = sx0 + _pad_left
    ax_x1 = sx1 - _pad_right
    ax_y0 = sy0 + _pad_top
    ax_y1 = sy1 - _pad_bot
    row_h = (ax_y1 - ax_y0) / n_g

    # Shared x domain: all raw values across all groups
    all_v = []
    for s in stats:
        all_v.extend(s["vals"])
    if not all_v:
        return
    v_min = min(all_v)
    v_max = max(all_v)
    if v_max <= v_min:
        v_max = v_min + 1.0
    _pad = (v_max - v_min) * 0.05
    v_min -= _pad
    v_max += _pad

    def X(v):
        return rigor._lin(v, v_min, v_max, ax_x0, ax_x1)

    # Sub-panel title — rendered INSIDE the sub-panel's top padding so it does not land on the main plot's x-axis
    # region.
    _sub_title_fs = max(11.0, fs["label"])
    parts.append(
        f'<text x="{sx0:.1f}" y="{sy0 + _sub_title_fs:.1f}" font-size="{_sub_title_fs:.1f}" '
        f'fill="{ink6}" font-style="italic">Distribution (half-KDE + raw dots)</text>'
    )

    for i, s in enumerate(stats):
        row_y_top = ax_y0 + i * row_h
        row_y_bot = row_y_top + row_h
        row_center = (row_y_top + row_y_bot) * 0.5
        # KDE baseline sits at row_center + 2 (slight shift below axis center so dots have room above)
        baseline_y = row_center + row_h * 0.25
        # KDE amplitude = up to 60% of row_h going upward
        amp = row_h * 0.55

        # Row label (group name) on the left
        row_label_fs = max(10.0, fs["label"] - 1)
        parts.append(
            f'<text x="{ax_x0 - 8:.1f}" y="{row_center + row_label_fs * 0.33:.1f}" '
            f'font-size="{row_label_fs:.1f}" fill="{ink}" '
            f'text-anchor="end" font-weight="600">{_xesc(s["name"])}</text>'
        )

        parts.append(
            f'<line x1="{ax_x0:.1f}" y1="{baseline_y:.1f}" x2="{ax_x1:.1f}" y2="{baseline_y:.1f}" '
            f'stroke="{ink6}" stroke-width="0.4" opacity="0.5"/>'
        )

        vals = s["vals"]
        if len(vals) >= 5:
            n_pts = 80
            densities = ridge_density_from_samples(vals, v_min, v_max, n=n_pts)
            if densities and max(densities) > 0:
                d_max = max(densities)
                xs = [v_min + k * (v_max - v_min) / (n_pts - 1) for k in range(n_pts)]
                ys_px = [baseline_y - (d / d_max) * amp for d in densities]
                # filled polygon (half violin on top of baseline)
                poly_pts = []
                for k in range(n_pts):
                    poly_pts.append(f"{X(xs[k]):.1f},{ys_px[k]:.1f}")
                poly_pts.append(f"{X(xs[-1]):.1f},{baseline_y:.1f}")
                poly_pts.append(f"{X(xs[0]):.1f},{baseline_y:.1f}")
                parts.append(
                    f'<polygon points="{" ".join(poly_pts)}" '
                    f'fill="{_rgb_prefix(accent)}0.28)" stroke="{accent}" stroke-width="1.2"/>'
                )

        dot_band_top = baseline_y + 2
        dot_band_bot = row_y_bot - 2
        if dot_band_bot <= dot_band_top:
            dot_band_bot = dot_band_top + 4
        _rng = _random.Random(i * 97 + 11)
        for v in vals:
            dx = X(v)
            dy = dot_band_top + _rng.random() * (dot_band_bot - dot_band_top)
            parts.append(f'<circle cx="{dx:.2f}" cy="{dy:.2f}" r="1.8" fill="{_rgb_prefix(ink)}0.55)" stroke="none"/>')

    # Sub X axis (bottom edge of sub plot)
    sub_x_ticks, sub_xmin, sub_xmax = rigor.nice_axis(v_min, v_max, 5)
    sub_fs_tick = max(10.0, fs["ytick"] * 0.85)
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
            fs_title=sub_fs_tick,
            show_tick_labels=True,
        )
    )


def _render_bar_pairwise_matrix_sub(parts, sub_bbox, stats, *, pal, fs, body_font):
    """Lower-triangle heatmap of Δ (group_i.mean − group_j.mean) for i>j."""
    sx0, sy0 = sub_bbox.x0, sub_bbox.y0
    sx1, sy1 = sub_bbox.x1, sub_bbox.y1
    ink = pal.get("ink", "rgba(28,28,26,1)")
    ink6 = pal.get("ink6", "rgba(28,28,26,0.6)")

    n = len(stats)
    if n < 2:
        return
    names = [s["name"] for s in stats]
    means = [s["mean"] for s in stats]

    # Compute global max |delta| for diverging normalization
    max_abs = 1e-9
    for i in range(n):
        for j in range(i):
            max_abs = max(max_abs, abs(means[i] - means[j]))

    # Layout: top labels (col names rotated), left labels (row names)
    _name_width = max(_estimate_label_width_px(name, fs["label"], bold=True, font_family=body_font) for name in names)
    # The caption and rotated column labels occupy separate measured rows.
    _pad_top = max(11.0, fs["label"]) * 1.35 + _name_width * math.sqrt(0.5) + 18
    _pad_left = max(72.0, _name_width + 12)
    _pad_right = 10.0
    _pad_bot = 10.0

    grid_x0 = sx0 + _pad_left
    grid_x1 = sx1 - _pad_right
    grid_y0 = sy0 + _pad_top
    grid_y1 = sy1 - _pad_bot

    cell_w = (grid_x1 - grid_x0) / n
    cell_h = (grid_y1 - grid_y0) / n
    cell = min(cell_w, cell_h)
    cx0 = grid_x0
    cy0 = grid_y0

    # Sub-panel title above — rendered INSIDE the sub-panel top padding so it
    # does not overlap the main-plot x axis.
    _sub_title_fs = max(11.0, fs["label"])
    parts.append(
        f'<text x="{sx0:.1f}" y="{sy0 + _sub_title_fs:.1f}" font-size="{_sub_title_fs:.1f}" '
        f'fill="{ink6}" font-style="italic">Δ matrix (row − col)</text>'
    )

    # Diverging color: blue (-) → white → orange (+)
    def _delta_color(d):
        if max_abs <= 0:
            return "rgba(240,240,240,1)"
        t = max(-1.0, min(1.0, d / max_abs))
        if t >= 0:
            # white (248, 248, 240) -> orange (217, 106, 46)
            r = 248 + (217 - 248) * t
            g = 248 + (106 - 248) * t
            b = 240 + (46 - 240) * t
        else:
            # white -> blue (74, 127, 163)
            u = -t
            r = 248 + (74 - 248) * u
            g = 248 + (127 - 248) * u
            b = 240 + (163 - 240) * u
        return f"rgb({int(r)},{int(g)},{int(b)})"

    num_fs = max(fs["label"], cell * 0.22)
    for i in range(n):
        for j in range(n):
            if i <= j:
                continue
            d = means[i] - means[j]
            x0 = cx0 + j * cell
            y0 = cy0 + i * cell
            color = _delta_color(d)
            parts.append(
                f'<rect x="{x0 + 0.5:.1f}" y="{y0 + 0.5:.1f}" '
                f'width="{cell - 1:.1f}" height="{cell - 1:.1f}" '
                f'fill="{color}" stroke="{ink6}" stroke-width="0.4"/>'
            )
            txt = f"{d:+.2f}"
            parts.append(
                f'<text x="{x0 + cell / 2:.1f}" y="{y0 + cell / 2 + num_fs * 0.33:.1f}" '
                f'text-anchor="middle" font-size="{num_fs:.1f}" fill="{ink}" '
                f'font-weight="500">{_xesc(txt)}</text>'
            )

    # Row labels (left, aligned with each row's center)
    label_fs = fs["label"]
    for i, name in enumerate(names):
        y_mid = cy0 + (i + 0.5) * cell
        parts.append(
            f'<text x="{cx0 - 6:.1f}" y="{y_mid + label_fs * 0.33:.1f}" '
            f'text-anchor="end" font-size="{label_fs:.1f}" fill="{ink}" '
            f'font-weight="600">{_xesc(name)}</text>'
        )

    # Column labels (top, rotated -45° at each column's center)
    for j, name in enumerate(names):
        x_mid = cx0 + (j + 0.5) * cell
        y_lab = cy0 - 6
        parts.append(
            f'<text x="{x_mid:.1f}" y="{y_lab:.1f}" '
            f'transform="rotate(-45 {x_mid:.1f} {y_lab:.1f})" '
            f'text-anchor="start" font-size="{label_fs:.1f}" fill="{ink}" '
            f'font-weight="600">{_xesc(name)}</text>'
        )
