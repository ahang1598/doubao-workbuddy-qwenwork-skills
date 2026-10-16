"""Forest plot (subgroup / meta-analysis) — point estimate + supplied CI with a reference line."""

from __future__ import annotations

from .._common import (
    _dist_font_sizes,
    _estimate_label_width_px,
    _resolve_font,
    _resolve_palette,
    _variant_is_classic,
    _xesc,
)
from . import _academic_rigor as rigor
from ._chart_layout import ChartLayout, axis_caption, forest_estimate_text, forest_ci_context, forest_scale, wrap_lines
from ._composition import numeric_axis


def _forest_header(W, H, pal, font_family, fs, title, subtitle, figure_label):
    layout = ChartLayout(W, H, pal, font_family)
    top = 18.0
    for text, size, bold, color, gap in (
        (figure_label, fs["figure"], True, pal["ink6"], 6),
        (title, fs["title"], True, pal["ink"], 7),
        (subtitle, fs["subtitle"], False, pal["ink6"], 5),
    ):
        if text:
            top += layout.text(text, 50, top, fs=size, bold=bold, color=color, width=W - 100) + gap
    return layout.parts, top + (16 if top > 18.0 else 0)


def _forest_footer(W, H, pal, font_family, fs, note, source, foot_fs=None):
    layout = ChartLayout(W, H, pal, font_family)
    foot_fs = foot_fs or max(13.0, fs["foot"], W / 50)
    lines = []
    for value in (note, source):
        if value:
            lines.extend(wrap_lines(value, W - 100, foot_fs, layout.font))
    top = H - 16 - len(lines) * foot_fs * 1.35
    for index, line in enumerate(lines):
        layout.text(line, 50, top + index * foot_fs * 1.35, fs=foot_fs, color=pal["ink6"])
    return layout.parts, top - (12 if lines else 0)


def _axis_ticks(scale, reference, left, right, fs, font):
    """Nice ticks thinned for legibility while always keeping the reference line labeled."""
    from ._xy import _axis_format

    lo, hi = scale.domain
    ticks = sorted(scale.ticks or [])
    tol = (hi - lo) * 1e-9
    if lo - tol <= reference <= hi + tol and not any(
        abs(t - reference) <= max(tol, abs(reference) * 1e-9) for t in ticks
    ):
        ticks = sorted(ticks + [reference])
    if not ticks:
        return scale
    fmt = _axis_format(rigor.SharedScale(scale.domain, ticks, scale.transform))[0]
    need = max(_estimate_label_width_px(fmt(t), fs, font_family=font) for t in ticks) + 16
    ref = min(range(len(ticks)), key=lambda i: abs(ticks[i] - reference))
    if scale.transform == "log10":
        # Log spacing is uneven: keep ticks greedily outward from the reference instead of every k-th
        # index, so a narrow ratio axis keeps 0.5 / 1 / 1.5 / 2 / 3 rather than collapsing to 1 / 2.
        xs = [scale.map(t, left, right) for t in ticks]
        keep = {ref}
        for step in (1, -1):
            last = ref
            for i in range(ref + step, len(ticks) if step > 0 else -1, step):
                if abs(xs[i] - xs[last]) >= need:
                    keep.add(i)
                    last = i
        return rigor.SharedScale(scale.domain, [ticks[i] for i in sorted(keep)], scale.transform)
    for stride in range(1, len(ticks) + 1):
        kept = [t for i, t in enumerate(ticks) if (i - ref) % stride == 0]
        xs = [scale.map(t, left, right) for t in kept]
        if all(b - a >= need for a, b in zip(xs, xs[1:])):
            break
    return rigor.SharedScale(scale.domain, kept, scale.transform)


def _forest_axis(left, right, y, scale, pal, font_family, fs_tick, fs_title, title, unit, W, favours=None, mid_x=None):
    from ._categorical_table import draw_favours

    layout = ChartLayout(W, max(260, y + 120), pal, font_family)
    numeric_axis(layout, rigor.BBox(left, 0, right, y), scale, font_sizes={"xtick": fs_tick})
    fav_h = draw_favours(layout, favours, mid_x, y + fs_tick * 1.44 + 10, max(10.0, fs_tick * 0.9)) if favours else 0
    caption = axis_caption(title, unit)
    if caption:
        caption_width = min(W - 100, layout.measure(caption, fs_title))
        center = min(W - 50 - caption_width / 2, max(50 + caption_width / 2, (left + right) / 2))
        layout.text(caption, center, y + fs_tick * 1.44 + 16 + fav_h, fs=fs_title, anchor="middle", width=W - 100)
    return "".join(layout.parts)


# Multi-mode whitelist: forest + with_subgroup_facets
# Template is None because allocate_facet_grid handles layout directly.
def _validate_subgroup_facets(s):
    sg_names = s.get("subgroup_names") or []
    if len(set(sg_names)) < 2:
        return (False, "need >= 2 distinct subgroups")
    # ensure at least 1 row per subgroup has estimate
    buckets = {}
    for sg, row in zip(sg_names, s.get("rows") or []):
        if sg is None:
            continue
        buckets.setdefault(sg, []).append(row)
    valid_sgs = 0
    for sg, rs in buckets.items():
        if any(r.get("estimate") is not None and r.get("ci_lo") is not None and r.get("ci_hi") is not None for r in rs):
            valid_sgs += 1
    if valid_sgs < 2:
        return (False, "need >= 2 subgroups each with a valid row")
    return (True, "")


_FOREST_MULTI_WHITELIST = {
    "with_subgroup_facets": (
        None,  # allocate_facet_grid directly
        lambda s: len(set(s.get("subgroup_names") or [])) >= 2,
        lambda s: _validate_subgroup_facets(s),
    ),
}


def _auto_log(rows, midline_value):
    """Ratio scale: every value positive, null at 1, and the reported values span more than 10×."""
    try:
        values = [
            float(r[k])
            for r in rows
            if isinstance(r, dict) and not r.get("is_subgroup_header")
            for k in ("estimate", "ci_lo", "ci_hi")
            if r.get(k) is not None
        ]
        mid = float(midline_value)
    except (TypeError, ValueError):
        return False
    return bool(values) and mid == 1 and min(values) > 0 and max(values) / min(values) > 10


def make_forest(
    rows,
    *,
    columns=None,
    row_order=None,
    x_title: str = "Hazard ratio",
    x_unit: str = "",
    title: str | None = None,
    subtitle: str | None = None,
    figure_label: str | None = None,
    note: str | None = None,
    source: str | None = None,
    midline_value: float = 1.0,
    log_x: bool | None = None,
    left_header: str = "Subgroup",
    right_header_label: str = "Estimate (CI)",
    width: float = 1400,
    height: float = 800,
    font_family: str | None = None,
    palette=None,
    variant: str | None = None,
    subgroups=None,
    multi_mode: str = "auto",
    ci_level=None,
    value_domain=None,
    favours=None,
    heterogeneity=None,
) -> str:
    """Forest plot. ``rows`` is a list of row-dicts (see module docstring).

    - subgroup-header rows: only ``label`` + ``is_subgroup_header=True``.
    - overall rows: draw a diamond at ``estimate`` spanning ``[ci_lo, ci_hi]``.
    - normal rows: solid square + horizontal CI line + numeric annotation.
    - confidence level is never inferred from bounds. Supply global/row
      ``ci_level=95`` (percentage) or a row ``ci_label="97.38% CI"`` only when
      supported by the source. Mixed levels are shown by row; an explicit
      percentage header conflicting with supplied row levels raises an error.
    - ``log_x=None`` (default) picks a log axis for ratio effects (HR/OR/RR):
      all values positive, null line at 1 and estimates/limits spanning > 10×;
      otherwise linear. Pass ``log_x=True/False`` to fix it.
    - ``value_domain=(low, high)`` preserves an explicitly chosen domain; it
      must contain all intervals and the reference. Otherwise log ranges fit
      the supplied intervals and null instead of expanding to whole decades.
    - ``favours=("SGLT2i 更优", "安慰剂更优")`` labels each side of the null
      line with arrows under the x axis. Ratios (HR/OR, lower = better): left = treatment better;
      differences (d/SMD/MD, midline 0, positive = intervention better): right = intervention better.
    - ``heterogeneity=dict(I2=43, tau2=0.02, Q=12.1, df=6, p=0.03)`` (or a string) adds an
      "I²=43%, τ²=0.02, …" line under the pooled ``is_overall`` row.
    - Row ``n``, ``events`` (count or "212/1840") and ``p`` (0.003 or "<0.001")
      add aligned N / Events / P columns; ``is_overall=True`` rows draw a diamond.
    - For a compact slide panel, generate at its intended aspect ratio and
      inspect the embedded size. ``multi_mode="single"`` wraps long row labels;
      a large source canvas scaled to a small panel cannot preserve font size.
      Notes and source are retained on separate measured lines.
    """
    _variant_is_classic("forest", variant)
    from ._categorical_table import make_forest_table, normalize_forest_rows

    from ._shared import chart_lang, tr

    if (
        left_header in ("Subgroup", tr("Subgroup"))
        and chart_lang() == "zh"
        and subgroups is None
        and not any(isinstance(r, dict) and r.get("is_subgroup_header") for r in rows)
    ):
        # No subgroup structure: "亚组" would mislabel a list of studies/exposures.
        left_header = "项目"
    if log_x is None:
        log_x = _auto_log(rows, midline_value)
    from ._categorical_table import insert_heterogeneity

    rows = insert_heterogeneity(rows, heterogeneity)
    rows = normalize_forest_rows(rows, log_x)
    numeric = [r for r in rows if not r.get("is_subgroup_header") and r.get("estimate") is not None]
    no_ci = bool(numeric) and all(r.get("_point_only") for r in numeric)
    if no_ci and right_header_label in ("Estimate (CI)", tr("Estimate (CI)")):
        right_header_label = tr("Estimate")  # never print a "[CI]" header over rows without intervals
    rows, right_header_label = forest_ci_context(rows, right_header_label, None if no_ci else ci_level)
    extended = (
        columns is not None
        or row_order is not None
        or any(any(k in r for k in ("n", "p", "mean", "sd", "events")) for r in rows)
    )
    if extended or multi_mode in ("single", "off", None):
        if multi_mode not in ("auto", "single", "off", None):
            raise ValueError("statistics columns require single mode")
        return make_forest_table(
            rows,
            columns=columns,
            row_order=row_order,
            x_title=x_title,
            x_unit=x_unit,
            title=title,
            subtitle=subtitle,
            figure_label=figure_label,
            note=note,
            source=source,
            midline_value=midline_value,
            log_x=log_x,
            value_domain=value_domain,
            left_header=left_header,
            right_header_label=right_header_label,
            width=width,
            height=height,
            font_family=font_family,
            palette=palette,
            favours=favours,
        )
    if not rows:
        raise ValueError("make_forest: 'rows' must contain at least one row")

    if palette is None:
        palette = "archive_ink"
    pal = _resolve_palette(palette)
    body_font, heading_font = _resolve_font(font_family)
    W, H = float(width), float(height)
    n_rows = len(rows)
    fs = _dist_font_sizes(W, H, max(4, n_rows))

    data_vals = []
    for r in rows:
        if r.get("is_subgroup_header"):
            continue
        est = r.get("estimate")
        lo = r.get("ci_lo")
        hi = r.get("ci_hi")
        for v in (est, lo, hi):
            if v is not None:
                data_vals.append(v)
    if not data_vals:
        raise ValueError("make_forest: no rows with numeric estimates found")
    scale = forest_scale(data_vals, midline_value, log_x=log_x, value_domain=value_domain)
    v_min_a, v_max_a = scale.domain
    x_ticks = scale.ticks

    # Resolve subgroup names per row from kwarg or row dicts.
    subgroup_names = []
    for i, r in enumerate(rows):
        if r.get("is_subgroup_header"):
            subgroup_names.append(None)
            continue
        sg = None
        if subgroups is not None:
            if isinstance(subgroups, dict):
                sg = subgroups.get(i)
            elif isinstance(subgroups, (list, tuple)) and i < len(subgroups):
                sg = subgroups[i]
        if sg is None:
            sg = r.get("subgroup")
        subgroup_names.append(sg)

    _mm_signals = {
        "subgroup_names": subgroup_names,
        "rows": rows,
    }
    _mm_bbox_full = rigor.bbox_from_edges(50, W - 50, 130, H - 110)
    _mm_mode, _mm_template, _mm_reason = rigor.resolve_multi_mode_v2(
        multi_mode,
        _FOREST_MULTI_WHITELIST,
        _mm_signals,
        _mm_bbox_full,
    )
    if _mm_mode == "with_subgroup_facets":
        return _render_forest_subgroup_facets(
            rows=rows,
            subgroup_names=subgroup_names,
            pal=pal,
            body_font=body_font,
            heading_font=heading_font,
            fs=fs,
            W=W,
            H=H,
            v_min_a=v_min_a,
            v_max_a=v_max_a,
            x_ticks=x_ticks,
            midline_value=midline_value,
            log_x=log_x,
            x_title=x_title,
            x_unit=x_unit,
            title=title,
            subtitle=subtitle,
            figure_label=figure_label,
            note=note,
            source=source,
            left_header=left_header,
            right_header_label=right_header_label,
        )

    def _row_text(r):
        if r.get("is_subgroup_header"):
            return ""
        if r.get("estimate") is None or r.get("ci_lo") is None or r.get("ci_hi") is None:
            return ""
        return forest_estimate_text(r, midline_value)

    right_texts = [_row_text(r) for r in rows]
    axis_caption_text = axis_caption(x_title, x_unit)
    margin_left = margin_right = 50
    _, header_bottom = _forest_header(W, H, pal, body_font, fs, title, subtitle, figure_label)

    def _measure(size):
        hfs = max(size, min(size * 1.05, size + 1))
        lw = max(
            (
                _estimate_label_width_px(
                    str(r.get("label", "")),
                    size,
                    bold=r.get("is_overall", False) or r.get("is_subgroup_header", False),
                    font_family=body_font,
                )
                + (0 if r.get("is_overall") or r.get("is_subgroup_header") else 16)
                for r in rows
            ),
            default=100,
        )
        lw = max(lw, _estimate_label_width_px(left_header, hfs, bold=True, font_family=body_font)) * 1.04
        rw = max((_estimate_label_width_px(t, size, font_family=body_font) for t in right_texts), default=120)
        rw = max(rw, _estimate_label_width_px(right_header_label, hfs, bold=True, font_family=body_font)) * 1.06
        foot = min(size, max(10.0, fs["foot"]))
        tick = min(fs["ytick"], size)
        cap_fs = min(fs["yaxis"], size * 1.05)
        cap_h = (
            len(wrap_lines(axis_caption_text, W - 100, cap_fs, body_font)) * cap_fs * 1.35 if axis_caption_text else 0
        )
        top = header_bottom + hfs + 4
        _, foot_top = _forest_footer(W, H, pal, body_font, fs, note, source, foot)
        fav_h = max(10.0, tick * 0.9) * 1.35 + 6 if favours else 0
        bottom = foot_top - (6 + tick * 1.44 + (16 + cap_h if cap_h else 10) + fav_h)
        return dict(
            label_fs=size,
            header_fs=hfs,
            label_w=lw,
            right_w=rw,
            foot_fs=foot,
            tick_fs=tick,
            cap_fs=cap_fs,
            top=top,
            bottom=bottom,
        )

    # Rows get the space first: pick the largest row font that fits height and width;
    # footer and tick text are derived from (never larger than) it.
    base_fs = max(13.0, fs["label"]) if n_rows <= 15 else max(11.0, fs["label"] * 15.0 / n_rows)
    min_plot = min(0.3 * (W - 100), 250)
    col_gap = 24 if W >= 600 else 14
    from ._xy import _axis_format

    tick_fmt = _axis_format(scale)[0]

    def _fits(cand, need_ticks):
        plot_w = W - margin_left - margin_right - cand["label_w"] - cand["right_w"] - 2 * col_gap
        tick_w = (len(x_ticks) - 1) * (
            16
            + max(
                (_estimate_label_width_px(tick_fmt(t), cand["tick_fs"], font_family=body_font) for t in x_ticks),
                default=0,
            )
        )
        return (cand["bottom"] - cand["top"]) >= n_rows * cand["label_fs"] * 1.45 and plot_w >= max(
            min_plot, tick_w if need_ticks else 0
        )

    lay = None
    for need_ticks in (True, False):
        size = base_fs
        while lay is None and size >= max(10.0, base_fs - 4 if need_ticks else 10.0):
            cand = _measure(size)
            if _fits(cand, need_ticks):
                lay = cand
            size = round(size - 0.5, 2)
    if lay is None:
        lay = _measure(10.0)
    label_fs, header_fs = lay["label_fs"], lay["header_fs"]
    label_w, right_w = lay["label_w"], lay["right_w"]

    header_parts, _ = _forest_header(W, H, pal, body_font, fs, title, subtitle, figure_label)
    footer_parts, _ = _forest_footer(W, H, pal, body_font, fs, note, source, lay["foot_fs"])
    plot_x_left = margin_left + label_w + col_gap
    plot_x_right = W - margin_right - right_w - col_gap
    plot_y_top = lay["top"]
    _avail_h = lay["bottom"] - plot_y_top
    if _avail_h < n_rows * 14:
        raise ValueError("canvas is too short for forest rows and complete notes/source; increase height")

    if plot_x_right <= plot_x_left + 60:
        plot_x_left = W * 0.32
        plot_x_right = W * 0.72

    row_h = min(_avail_h / n_rows, label_fs * 3.2)
    plot_y_bot = plot_y_top + row_h * n_rows

    def Xv(v):
        if log_x:
            return rigor._log_lin(v, v_min_a, v_max_a, plot_x_left, plot_x_right)
        return rigor._lin(v, v_min_a, v_max_a, plot_x_left, plot_x_right)

    parts = rigor.draw_canvas_bg(pal, W, H)

    parts.extend(header_parts)

    # column headers — scale offset with title font so the "Subgroup" header
    # never sits inside the title text's bbox (lint flagged this on wide
    # canvases where fs["title"] grew to 38 but header_y stayed fixed at -10).
    header_y = plot_y_top - 10
    parts.append(
        f'<text x="{margin_left:.1f}" y="{header_y:.1f}" font-size="{header_fs}" '
        f'fill="{pal["ink"]}" font-weight="700">{_xesc(left_header)}</text>'
    )
    parts.append(
        f'<text x="{W - margin_right:.1f}" y="{header_y:.1f}" font-size="{header_fs}" '
        f'fill="{pal["ink"]}" font-weight="700" text-anchor="end">{_xesc(right_header_label)}</text>'
    )

    parts.append(
        f'<line x1="{margin_left:.1f}" y1="{header_y + 6:.1f}" x2="{W - margin_right:.1f}" y2="{header_y + 6:.1f}" '
        f'stroke="{pal["ink2"]}" stroke-width="1"/>'
    )

    midline_x = Xv(midline_value)

    # Each stripe spans the complete data row, including its labels and CI text. Alternate: pal["bg"] (even rows → no
    # fill, inherits bg) and a slight warm grey for odd rows.
    zebra_fill = pal["ink1"]
    for i in range(n_rows):
        if i % 2 == 1:
            y_top_row = plot_y_top + row_h * i
            parts.append(
                f'<rect x="{margin_left:.1f}" y="{y_top_row:.1f}" '
                f'width="{(W - margin_left - margin_right):.1f}" height="{row_h:.1f}" '
                f'fill="{zebra_fill}" stroke="none"/>'
            )

    parts.append(
        f'<line x1="{midline_x:.1f}" y1="{plot_y_top:.1f}" x2="{midline_x:.1f}" y2="{plot_y_bot:.1f}" '
        f'stroke="{pal["ink4"]}" stroke-width="1" stroke-dasharray="4 4"/>'
    )

    accent = pal["accent"]
    ink = pal["ink"]
    for i, r in enumerate(rows):
        y_center = plot_y_top + row_h * (i + 0.5)
        label = str(r.get("label", ""))
        if r.get("is_subgroup_header"):
            het = r.get("_het")
            role = ' data-role="forest-heterogeneity"' if het else ""
            parts.append(
                f'<text x="{margin_left + (16 if het else 0):.1f}" y="{y_center + label_fs * 0.35:.1f}" '
                f'font-size="{label_fs * (0.9 if het else 1):.1f}" fill="{pal["ink6"] if het else ink}" '
                f'font-weight="{400 if het else 700}"{role}>{_xesc(label)}</text>'
            )
            continue

        is_overall = r.get("is_overall", False)
        est = r.get("estimate")
        lo = r.get("ci_lo")
        hi = r.get("ci_hi")
        if est is None or lo is None or hi is None:
            continue

        # left-column label (indent non-header rows a bit)
        indent = 16 if not is_overall else 0
        parts.append(
            f'<text x="{margin_left + indent:.1f}" y="{y_center + label_fs * 0.35:.1f}" '
            f'font-size="{label_fs}" fill="{ink}" '
            f'font-weight="{700 if is_overall else 400}">{_xesc(label)}</text>'
        )

        if is_overall:
            # R2 P2: diamond width = actual CI span (Xv(hi)-Xv(lo)), not row width.
            cx = Xv(est)
            lx = Xv(lo)
            rx = Xv(hi)
            dh = min(max(6.0, label_fs * 0.55), row_h * 0.3)
            pts = f"{lx:.1f},{y_center:.1f} {cx:.1f},{y_center - dh:.1f} {rx:.1f},{y_center:.1f} {cx:.1f},{y_center + dh:.1f}"
            parts.append(f'<polygon points="{pts}" fill="{accent}" stroke="{ink}" stroke-width="1"/>')
        else:
            lx = Xv(max(lo, v_min_a))
            rx = Xv(min(hi, v_max_a))
            cx = Xv(est)
            point_only = r.get("_point_only", False)
            # C-polish: color CI line by significance vs midline. If CI straddles the midline → non-significant → muted
            # grey. If CI lies entirely on one side → significant → ink (strong black).
            crosses_midline = lo <= midline_value <= hi
            ci_color = pal["ink6"] if crosses_midline else pal["ink"]
            parts.append(
                ""
                if point_only
                else f'<line x1="{lx:.1f}" y1="{y_center:.1f}" x2="{rx:.1f}" y2="{y_center:.1f}" '
                f'stroke="{ci_color}" stroke-width="1.4"/>'
            )
            cap_h = 5
            if not point_only:
                parts.append(
                    f'<line x1="{lx:.1f}" y1="{y_center - cap_h:.1f}" x2="{lx:.1f}" y2="{y_center + cap_h:.1f}" '
                    f'stroke="{ci_color}" stroke-width="1.4"/>'
                )
                parts.append(
                    f'<line x1="{rx:.1f}" y1="{y_center - cap_h:.1f}" x2="{rx:.1f}" y2="{y_center + cap_h:.1f}" '
                    f'stroke="{ci_color}" stroke-width="1.4"/>'
                )
            # weight-scaled square — significant rows filled with accent,
            # non-significant rows filled with muted grey.
            w = r.get("weight")
            if w is not None and w > 0:
                size = max(6.0, min(18.0, 6.0 + 12.0 * (w / max((rr.get("weight") or 1 for rr in rows), default=1))))
            else:
                size = 10.0
            # Without an interval, significance is unknown: no accent/grey verdict.
            sq_fill = pal["ink"] if point_only else pal["ink6"] if crosses_midline else accent
            sq_stroke = pal["ink"]
            parts.append(
                f'<rect x="{cx - size / 2:.1f}" y="{y_center - size / 2:.1f}" '
                f'width="{size:.1f}" height="{size:.1f}" fill="{sq_fill}" stroke="{sq_stroke}" stroke-width="1"/>'
            )

        parts.append(
            f'<text x="{W - margin_right:.1f}" y="{y_center + label_fs * 0.35:.1f}" '
            f'font-size="{label_fs}" fill="{ink}" text-anchor="end" '
            f'font-weight="{700 if is_overall else 400}">{_xesc(right_texts[i])}</text>'
        )

    axis_y = plot_y_bot + 6
    axis_scale = _axis_ticks(scale, midline_value, plot_x_left, plot_x_right, lay["tick_fs"], body_font)
    parts.append(
        _forest_axis(
            plot_x_left,
            plot_x_right,
            axis_y,
            axis_scale,
            pal,
            body_font,
            lay["tick_fs"],
            lay["cap_fs"],
            x_title,
            x_unit,
            W,
            favours,
            midline_x,
        )
    )
    parts.extend(footer_parts)
    ci_state = "none" if no_ci else "supplied"
    parts.append(
        f'<g data-role="forest-layout" data-forest-ci="{ci_state}" data-domain-low="{v_min_a:g}" '
        f'data-domain-high="{v_max_a:g}" data-transform="{scale.transform}" '
        f'data-plot-left="{plot_x_left:g}" data-plot-right="{plot_x_right:g}"/>'
    )

    return rigor.wrap_svg(parts, W, H, body_font)


# with_subgroup_facets: vertically-stacked forest panels, shared X (effect size)
def _render_forest_subgroup_facets(
    *,
    rows,
    subgroup_names,
    pal,
    body_font,
    heading_font,
    fs,
    W,
    H,
    v_min_a,
    v_max_a,
    x_ticks,
    midline_value,
    log_x,
    x_title,
    x_unit,
    title,
    subtitle,
    figure_label,
    note,
    source,
    left_header,
    right_header_label,
):
    """Vertical facet grid: one forest panel per subgroup, shared X scale."""
    # Group rows by subgroup, preserving first-appearance order
    buckets = {}
    order = []
    for row, sg in zip(rows, subgroup_names):
        if row.get("is_subgroup_header"):
            # legacy headers are honored by inlining into their nearest sg bucket
            continue
        if sg is None:
            continue
        if sg not in buckets:
            buckets[sg] = []
            order.append(sg)
        buckets[sg].append(row)

    n_sg = len(order)
    if n_sg < 2:
        # Should not reach here given validator, but defensive
        n_sg = max(1, n_sg)

    shared_x = rigor.SharedScale(
        domain=(v_min_a, v_max_a),
        ticks=x_ticks,
        transform="log10" if log_x else "linear",
    )

    header_parts, header_bottom = _forest_header(W, H, pal, body_font, fs, title, subtitle, figure_label)
    margin_top = max(60, header_bottom + 16)
    footer_parts, footer_top = _forest_footer(W, H, pal, body_font, fs, note, source)
    axis_caption_text = axis_caption(x_title, x_unit)
    axis_title_height = len(wrap_lines(axis_caption_text, W - 100, fs["yaxis"], body_font)) * fs["yaxis"] * 1.35
    margin_bot = max(110, H - footer_top + fs["ytick"] * 1.44 + axis_title_height + 32)
    margin_left = 50
    margin_right = 50

    full_bbox = rigor.bbox_from_edges(
        margin_left,
        W - margin_right,
        margin_top,
        H - margin_bot,
    )
    try:
        cells = rigor.allocate_facet_grid(
            full_bbox,
            n=n_sg,
            cols=1,
            gutter=22.0,
            min_cell=(300.0, 100.0),
        )
    except rigor.LayoutError:
        cells = rigor.allocate_facet_grid(
            full_bbox,
            n=n_sg,
            cols=1,
            gutter=14.0,
            min_cell=(220.0, 70.0),
        )

    ink = pal["ink"]
    ink6 = pal["ink6"]
    pal.get("ink2", "rgba(28,28,26,0.2)")
    ink4 = pal.get("ink4", "rgba(28,28,26,0.4)")
    accent = pal["accent"]

    parts = rigor.draw_canvas_bg(pal, W, H)

    parts.extend(header_parts)

    # Per subgroup facet layout tracking for label widths
    # Use first-row style widths within this facet.
    label_fs = max(11.0, fs["label"])

    for si, sg in enumerate(order):
        cell = cells[si]
        f_x0, f_y0, f_x1, f_y1 = cell.x0, cell.y0, cell.x1, cell.y1
        sg_rows = buckets[sg]
        n_r = len(sg_rows)

        facet_title_fs = max(12.0, label_fs * 1.05)
        parts.append(
            f'<text x="{f_x0:.1f}" y="{f_y0 + facet_title_fs:.1f}" '
            f'font-size="{facet_title_fs:.1f}" fill="{ink}" '
            f'font-weight="700">{_xesc(str(sg))}</text>'
        )

        _row_label_w = max(
            (
                _estimate_label_width_px(
                    str(r.get("label", "")),
                    label_fs,
                    bold=r.get("is_overall", False),
                    font_family=body_font,
                )
                for r in sg_rows
            ),
            default=100,
        )
        _row_label_w = max(_row_label_w, 80)

        def _rtxt(r):
            est = r.get("estimate")
            lo = r.get("ci_lo")
            hi = r.get("ci_hi")
            if est is None or lo is None or hi is None:
                return ""
            return forest_estimate_text(r, midline_value)

        right_texts = [_rtxt(r) for r in sg_rows]
        _right_w = max(
            (_estimate_label_width_px(t, label_fs, font_family=body_font) for t in right_texts),
            default=100,
        )
        _right_w = max(_right_w, 80)

        col_gap = 16
        plot_x_left = f_x0 + _row_label_w + col_gap
        plot_x_right = f_x1 - _right_w - col_gap
        plot_y_top = f_y0 + facet_title_fs + 6
        # Reserve bottom for X axis only on the last facet; otherwise leave a thin gap
        _is_last = si == n_sg - 1
        plot_y_bot = f_y1 - (34 if _is_last else 6)

        plot_x_right = max(plot_x_left + 60, plot_x_right)

        avail_h = plot_y_bot - plot_y_top
        row_h = max(label_fs * 1.4, avail_h / max(1, n_r))
        if n_r * row_h > avail_h:
            row_h = avail_h / max(1, n_r)

        if log_x:
            midline_x_px = rigor._log_lin(midline_value, v_min_a, v_max_a, plot_x_left, plot_x_right)
        else:
            midline_x_px = rigor._lin(midline_value, v_min_a, v_max_a, plot_x_left, plot_x_right)
        parts.append(
            f'<line x1="{midline_x_px:.1f}" y1="{plot_y_top:.1f}" x2="{midline_x_px:.1f}" y2="{plot_y_bot:.1f}" '
            f'stroke="{ink4}" stroke-width="1" stroke-dasharray="4 4"/>'
        )

        for ri, r in enumerate(sg_rows):
            y_center = plot_y_top + row_h * (ri + 0.5)
            label = str(r.get("label", ""))
            is_overall = r.get("is_overall", False)
            est = r.get("estimate")
            lo = r.get("ci_lo")
            hi = r.get("ci_hi")
            if est is None or lo is None or hi is None:
                continue

            parts.append(
                f'<text x="{f_x0:.1f}" y="{y_center + label_fs * 0.33:.1f}" '
                f'font-size="{label_fs:.1f}" fill="{ink}" '
                f'font-weight="{700 if is_overall else 400}">{_xesc(label)}</text>'
            )

            def _X(v, left=plot_x_left, right=plot_x_right):
                return shared_x.map(v, left, right)

            lx = _X(max(lo, v_min_a))
            rx = _X(min(hi, v_max_a))
            cx = _X(est)

            if is_overall:
                dh = min(max(6.0, label_fs * 0.55), row_h * 0.3)
                pts = (
                    f"{lx:.1f},{y_center:.1f} "
                    f"{cx:.1f},{y_center - dh:.1f} "
                    f"{rx:.1f},{y_center:.1f} "
                    f"{cx:.1f},{y_center + dh:.1f}"
                )
                parts.append(f'<polygon points="{pts}" fill="{accent}" stroke="{ink}" stroke-width="1"/>')
            else:
                crosses = lo <= midline_value <= hi
                ci_color = ink6 if crosses else ink
                parts.append(
                    f'<line x1="{lx:.1f}" y1="{y_center:.1f}" x2="{rx:.1f}" y2="{y_center:.1f}" '
                    f'stroke="{ci_color}" stroke-width="1.4"/>'
                )
                cap_h = 5
                parts.append(
                    f'<line x1="{lx:.1f}" y1="{y_center - cap_h:.1f}" x2="{lx:.1f}" y2="{y_center + cap_h:.1f}" '
                    f'stroke="{ci_color}" stroke-width="1.4"/>'
                )
                parts.append(
                    f'<line x1="{rx:.1f}" y1="{y_center - cap_h:.1f}" x2="{rx:.1f}" y2="{y_center + cap_h:.1f}" '
                    f'stroke="{ci_color}" stroke-width="1.4"/>'
                )
                w = r.get("weight")
                if w is not None and w > 0:
                    size = max(
                        6.0, min(14.0, 6.0 + 8.0 * (w / max((rr.get("weight") or 1 for rr in sg_rows), default=1)))
                    )
                else:
                    size = 9.0
                sq_fill = ink6 if crosses else accent
                parts.append(
                    f'<rect x="{cx - size / 2:.1f}" y="{y_center - size / 2:.1f}" '
                    f'width="{size:.1f}" height="{size:.1f}" fill="{sq_fill}" stroke="{ink}" stroke-width="1"/>'
                )

            parts.append(
                f'<text x="{f_x1:.1f}" y="{y_center + label_fs * 0.33:.1f}" '
                f'font-size="{label_fs:.1f}" fill="{ink}" text-anchor="end" '
                f'font-weight="{700 if is_overall else 400}">{_xesc(right_texts[ri])}</text>'
            )

        # X axis (last facet only — shared)
        if _is_last:
            parts.append(
                _forest_axis(
                    plot_x_left,
                    plot_x_right,
                    plot_y_bot + 2,
                    shared_x,
                    pal,
                    body_font,
                    max(10.0, fs["ytick"] * 0.95),
                    max(11.0, fs["yaxis"] * 0.95),
                    x_title,
                    x_unit,
                    W,
                )
            )

    parts.extend(footer_parts)

    return rigor.wrap_svg(parts, W, H, body_font)
