"""ROC / PR curve chart — academic figure for binary-classifier evaluation."""

from __future__ import annotations

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


# Multi-mode whitelist: with_roc_pr_pair → shared SeriesContext across main
# (ROC on the left) and sub (PR on the right).
def _validate_roc_pr_pair(signals):
    roc_names = signals.get("roc_names") or []
    pr_names = signals.get("pr_names") or []
    if not roc_names or not pr_names:
        return (False, "need both ROC and PR curves")
    if len(roc_names) != len(pr_names):
        return (False, f"name count mismatch: ROC {len(roc_names)} vs PR {len(pr_names)}")
    # Name overlap check — require matching model identifiers.
    if set(roc_names) != set(pr_names):
        return (False, "ROC and PR model names must match")
    return (True, "")


_ROC_PR_MULTI_WHITELIST = {
    "with_roc_pr_pair": (
        # Equal-width split: ROC and PR carry complementary information and should share screen area evenly (3:1 crushed
        # PR, 1:1 is the journal-standard pairing).
        "left_right_1to1",
        lambda s: bool(s.get("pr_names")) and bool(s.get("roc_names")),
        lambda s: _validate_roc_pr_pair(s),
    ),
}


def _trapezoid_auc(xs, ys):
    """Trapezoidal integration AUC. Assumes xs are monotonic (asc or desc)."""
    if len(xs) < 2:
        return 0.0
    # pair up and sort by x ascending so AUC sign is positive-under-curve
    pts = sorted(zip(xs, ys), key=lambda p: p[0])
    auc = 0.0
    for i in range(len(pts) - 1):
        x0, y0 = pts[i]
        x1, y1 = pts[i + 1]
        auc += (x1 - x0) * (y0 + y1) * 0.5
    return auc


def make_roc_pr(
    curves,
    *,
    mode: str = "roc",
    pr_curves=None,
    title: str | None = None,
    subtitle: str | None = None,
    figure_label: str | None = None,
    note: str | None = None,
    source: str | None = None,
    show_diagonal: bool = True,
    baseline_value: float | None = None,
    highlight_curve: str | None = None,
    width: float = 1050,
    height: float = 1050,
    font_family: str | None = None,
    palette=None,
    variant: str | None = None,
    multi_mode: str = "auto",
) -> str:
    """ROC or PR curve plot with baseline + per-curve AUC in legend.

    Each ``curves`` entry must contain ``name`` and either ``fpr+tpr`` (roc)
    or ``recall+precision`` (pr). ``auc`` is computed by trapezoid rule if absent.

    ``pr_curves`` (optional): list of PR curves with the same ``name`` set as
    ``curves``. When supplied (and multi_mode permits), the chart renders two
    coupled panels — ROC on the left, PR on the right — sharing a
    ``SeriesContext`` so model colors stay consistent across panels.
    """
    _variant_is_classic("roc_pr", variant)
    if not curves:
        raise ValueError("make_roc_pr: 'curves' must contain at least one curve")

    if palette is None:
        palette = "archive_ink"
    pal = _resolve_palette(palette)
    body_font, heading_font = _resolve_font(font_family)
    W, H = float(width), float(height)
    n_c = len(curves)
    fs = _dist_font_sizes(W, H, max(4, n_c + 3))

    is_roc = mode == "roc"

    # ``margin_top`` reserves space for the title block AND the top-most Y tick label ("1" at precision/TPR = 1.0).
    # draw_y_axis anchors the label centered on the tick position, so half of the label glyph extends above plot_y_top.
    margin_top = 150
    margin_bot = 160
    margin_left = 130
    margin_right = 60

    plot_x_left = margin_left
    plot_x_right = W - margin_right
    plot_y_top = margin_top
    plot_y_bot = H - margin_bot

    x_ticks = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
    y_ticks = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
    x_min, x_max = 0.0, 1.0
    y_min, y_max = 0.0, 1.0

    # Signals include the PR curves + name lists for cross-panel identity.
    _roc_names = [str(c.get("name", tr("curve {i}", i=i + 1))) for i, c in enumerate(curves)]
    _pr_names = [str(c.get("name", tr("curve {i}", i=i + 1))) for i, c in enumerate(pr_curves)] if pr_curves else []
    _full_plot_bbox = rigor.bbox_from_edges(
        plot_x_left,
        plot_x_right,
        plot_y_top,
        plot_y_bot,
    )
    _mm_signals = {"roc_names": _roc_names, "pr_names": _pr_names}
    _mm_mode, _mm_template, _mm_reason = rigor.resolve_multi_mode_v2(
        multi_mode,
        _ROC_PR_MULTI_WHITELIST,
        _mm_signals,
        _full_plot_bbox,
    )

    _sub_bbox = None
    if _mm_mode is not None and _mm_template is not None:
        _rects = rigor.allocate_main_sub(_full_plot_bbox, _mm_template)
        _main_bb = _rects["main"]
        _sub_bbox = _rects["sub"]
        # Shrink the main plot box on the right so the main renderer draws
        # inside _main_bb, and the sub ROC-PR partner uses _sub_bbox.
        plot_x_right = _main_bb.x1

    def X(v):
        return rigor._lin(v, x_min, x_max, plot_x_left, plot_x_right)

    def Y(v):
        return rigor._lin(v, y_min, y_max, plot_y_bot, plot_y_top)

    # Build a SeriesContext from the ROC panel's name order. The sub (PR) panel
    # reuses the same context so model colors stay consistent across panels.
    series_cols = _derive_series_colors(pal, max(1, n_c))
    _series_ctx = rigor.SeriesContext(
        ids=list(_roc_names),
        pal=pal,
        series_colors=series_cols,
    )

    processed = []
    for i, c in enumerate(curves):
        name = str(c.get("name", tr("curve {i}", i=i + 1)))
        if is_roc:
            xs = list(c.get("fpr") or [])
            ys = list(c.get("tpr") or [])
        else:
            xs = list(c.get("recall") or [])
            ys = list(c.get("precision") or [])
        if len(xs) != len(ys) or len(xs) == 0:
            raise ValueError(f"make_roc_pr: curve '{name}' has mismatched or empty x/y arrays")
        auc = c.get("auc")
        if auc is None:
            auc = _trapezoid_auc(xs, ys)
        n = c.get("n")
        processed.append(
            {
                "name": name,
                "xs": xs,
                "ys": ys,
                "auc": auc,
                "n": n,
                "color": _series_ctx.color_of(name),
            }
        )

    parts = rigor.draw_canvas_bg(pal, W, H)

    parts.append(
        rigor.draw_title_block(
            plot_x_left,
            50,
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

    # grid first
    # Pre-compute legend-panel footprint so grid can cut out the band that would
    # otherwise strike through "ModelX (AUC = ...)" rows (translucent panel
    # fill lets the dashed line still trip embed_svg_line_through_text).
    _leg_fs = max(13.0, fs["label"])
    _line_h = _leg_fs * 1.5
    _max_tw = 0.0
    for cv in processed:
        _auc_str = f"AUC = {cv['auc']:.3f}"
        if cv["n"] is not None:
            _lab = f"{cv['name']} ({_auc_str}, n = {int(cv['n'])})"
        else:
            _lab = f"{cv['name']} ({_auc_str})"
        _tw = _estimate_label_width_px(_lab, _leg_fs, font_family=body_font)
        _max_tw = max(_max_tw, _tw)
    _swatch_w = 28.0
    _pad = 10.0
    _panel_w = _swatch_w + 10 + _max_tw + _pad * 2
    _panel_h = len(processed) * _line_h + _pad
    if is_roc:
        _panel_x = plot_x_right - _panel_w - 20
        _panel_y = plot_y_bot - _panel_h - 20
    else:
        _panel_x = plot_x_right - _panel_w - 20
        _panel_y = plot_y_top + 20
    _legend_bbox = (_panel_x, _panel_y, _panel_x + _panel_w, _panel_y + _panel_h)

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
            x_ticks=x_ticks,
            x_min=x_min,
            x_max=x_max,
            orient="both",
            cutout_bboxes=[_legend_bbox],
        )
    )

    if show_diagonal and is_roc:
        parts.append(
            f'<line x1="{X(0):.1f}" y1="{Y(0):.1f}" x2="{X(1):.1f}" y2="{Y(1):.1f}" '
            f'stroke="{pal["ink4"]}" stroke-width="1.2" stroke-dasharray="5 4"/>'
        )
    elif show_diagonal and not is_roc:
        # pr baseline is a horizontal line at prevalence
        base_v = baseline_value if baseline_value is not None else 0.5
        parts.append(
            f'<line x1="{X(0):.1f}" y1="{Y(base_v):.1f}" x2="{X(1):.1f}" y2="{Y(base_v):.1f}" '
            f'stroke="{pal["ink4"]}" stroke-width="1.2" stroke-dasharray="5 4"/>'
        )

    for cv in processed:
        is_hi = highlight_curve is not None and cv["name"] == highlight_curve
        stroke_w = 3.2 if is_hi else 2.2
        pts = [(X(x), Y(y)) for x, y in zip(cv["xs"], cv["ys"])]
        d = " ".join(f"{'M' if i == 0 else 'L'} {x:.2f} {y:.2f}" for i, (x, y) in enumerate(pts))
        parts.append(
            f'<path d="{d}" fill="none" stroke="{cv["color"]}" stroke-width="{stroke_w}" '
            f'stroke-linecap="round" stroke-linejoin="round"/>'
        )

    if is_roc:
        x_title = tr("False positive rate")
        y_title = tr("True positive rate")
    else:
        x_title = tr("Recall")
        y_title = tr("Precision")
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
            title=y_title,
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
            pal=pal,
            fs_tick=fs["ytick"],
            fs_title=fs["yaxis"],
            title=x_title,
        )
    )

    leg_fs = max(13.0, fs["label"])
    line_h = leg_fs * 1.5
    entries = []
    max_tw = 0.0
    for cv in processed:
        auc_str = f"AUC = {cv['auc']:.3f}"
        if cv["n"] is not None:
            label = f"{cv['name']} ({auc_str}, n = {int(cv['n'])})"
        else:
            label = f"{cv['name']} ({auc_str})"
        tw = _estimate_label_width_px(label, leg_fs, font_family=body_font)
        max_tw = max(max_tw, tw)
        entries.append((cv["color"], label))

    swatch_w = 28.0
    pad = 10.0
    panel_w = swatch_w + 10 + max_tw + pad * 2
    panel_h = len(entries) * line_h + pad
    # roc: bottom-right; pr: top-right (less likely to collide with curves)
    if is_roc:
        panel_x = plot_x_right - panel_w - 20
        panel_y = plot_y_bot - panel_h - 20
    else:
        panel_x = plot_x_right - panel_w - 20
        panel_y = plot_y_top + 20
    bg_fill = f"{_rgb_prefix(pal.get('bg', 'rgba(255,255,255,1)'))}0.9)"
    parts.append(
        f'<rect x="{panel_x:.1f}" y="{panel_y:.1f}" width="{panel_w:.1f}" height="{panel_h:.1f}" '
        f'fill="{bg_fill}" stroke="{pal["ink2"]}" stroke-width="0.8" rx="4"/>'
    )
    for i, (col, lab) in enumerate(entries):
        y_line = panel_y + pad + leg_fs + i * line_h
        sx = panel_x + pad
        parts.append(
            f'<line x1="{sx:.1f}" y1="{y_line - leg_fs * 0.3:.1f}" '
            f'x2="{sx + swatch_w:.1f}" y2="{y_line - leg_fs * 0.3:.1f}" '
            f'stroke="{col}" stroke-width="3"/>'
        )
        parts.append(
            f'<text x="{sx + swatch_w + 8:.1f}" y="{y_line:.1f}" font-size="{leg_fs}" '
            f'fill="{pal["ink"]}">{_xesc(lab)}</text>'
        )

    if _sub_bbox is not None and _mm_mode == "with_roc_pr_pair":
        _render_roc_pr_pair_sub(
            parts,
            _sub_bbox,
            pr_curves,
            _series_ctx,
            pal=pal,
            fs=fs,
            body_font=body_font,
            baseline_value=baseline_value,
            show_diagonal=show_diagonal,
        )

    parts.append(rigor.draw_footer(note, source, pal, fs, plot_x_left, plot_x_right, H - 36))

    return rigor.wrap_svg(parts, W, H, body_font)


# Multi-mode sub-panel renderer: PR partner, shared SeriesContext
def _render_roc_pr_pair_sub(
    parts,
    sub_bbox,
    pr_curves,
    series_ctx,
    *,
    pal,
    fs,
    body_font,
    baseline_value=None,
    show_diagonal=True,
):
    """Render the PR panel inside ``sub_bbox``."""
    sx0, sy0 = sub_bbox.x0, sub_bbox.y0
    sx1, sy1 = sub_bbox.x1, sub_bbox.y1
    ink = pal.get("ink", "rgba(28,28,26,1)")
    ink4 = pal.get("ink4", "rgba(28,28,26,0.4)")
    ink6 = pal.get("ink6", "rgba(28,28,26,0.6)")

    # Padding: title above + axes labels + axis titles.
    _pad_left = 56.0
    _pad_right = 10.0
    _pad_top = 56.0
    _pad_bot = 90.0  # leaves room for x-axis + x-title + AP legend strip
    ax_x0 = sx0 + _pad_left
    ax_x1 = sx1 - _pad_right
    ax_y0 = sy0 + _pad_top
    ax_y1 = sy1 - _pad_bot

    # Fixed PR axes 0..1.
    xmin, xmax = 0.0, 1.0
    ymin, ymax = 0.0, 1.0
    sub_x_ticks = [0.0, 0.25, 0.5, 0.75, 1.0]
    sub_y_ticks = [0.0, 0.25, 0.5, 0.75, 1.0]
    sub_fs_tick = max(10.0, fs["ytick"] * 0.82)
    sub_fs_title = max(10.0, fs["yaxis"] * 0.82)

    def SX(v):
        return rigor._lin(v, xmin, xmax, ax_x0, ax_x1)

    def SY(v):
        return rigor._lin(v, ymin, ymax, ax_y1, ax_y0)

    # Sub-panel title. Anchor at the top of the sub bbox with a comfortable
    # top padding — the baseline is placed well above ``ax_y0`` so the title
    # cannot touch the top of the PR curve (precision ≈ 1 cases).
    _sub_title_fs = max(11.0, fs["label"])
    parts.append(
        f'<text x="{sx0:.1f}" y="{sy0 + _sub_title_fs + 4:.1f}" '
        f'font-size="{_sub_title_fs:.1f}" fill="{ink6}" font-style="italic">'
        f"PR partner</text>"
    )

    parts.append(
        rigor.draw_grid(
            ax_x0,
            ax_x1,
            ax_y0,
            ax_y1,
            pal=pal,
            y_ticks=sub_y_ticks,
            y_min=ymin,
            y_max=ymax,
            x_ticks=sub_x_ticks,
            x_min=xmin,
            x_max=xmax,
            orient="both",
        )
    )

    # Baseline for PR = prevalence (horizontal line).
    if show_diagonal:
        base_v = baseline_value if baseline_value is not None else 0.5
        parts.append(
            f'<line x1="{SX(0):.1f}" y1="{SY(base_v):.1f}" '
            f'x2="{SX(1):.1f}" y2="{SY(base_v):.1f}" '
            f'stroke="{ink4}" stroke-width="1" stroke-dasharray="5 4"/>'
        )

    # Preprocess + draw PR curves with shared SeriesContext colors.
    pr_entries = []
    for i, c in enumerate(pr_curves or []):
        name = str(c.get("name", tr("curve {i}", i=i + 1)))
        xs = list(c.get("recall") or [])
        ys = list(c.get("precision") or [])
        if len(xs) != len(ys) or len(xs) == 0:
            continue
        ap = c.get("ap")
        if ap is None:
            ap = _trapezoid_auc(xs, ys)  # trapezoidal PR AUC ~ AP
        color = series_ctx.color_of(name)
        pts = [(SX(x), SY(y)) for x, y in zip(xs, ys)]
        d = " ".join(f"{'M' if j == 0 else 'L'} {x:.2f} {y:.2f}" for j, (x, y) in enumerate(pts))
        parts.append(
            f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2" '
            f'stroke-linecap="round" stroke-linejoin="round"/>'
        )
        pr_entries.append((color, name, ap))

    parts.append(
        rigor.draw_y_axis(
            ax_x0,
            ax_y0,
            ax_y1,
            sub_y_ticks,
            ymin,
            ymax,
            pal=pal,
            fs_tick=sub_fs_tick,
            fs_title=sub_fs_title,
            title=tr("Precision"),
            side="left",
        )
    )
    parts.append(
        rigor.draw_x_axis(
            ax_x0,
            ax_x1,
            ax_y1,
            sub_x_ticks,
            xmin,
            xmax,
            pal=pal,
            fs_tick=sub_fs_tick,
            fs_title=sub_fs_title,
            title=tr("Recall"),
            show_tick_labels=True,
        )
    )

    # Compact AP legend placed BELOW the sub-panel x-axis (horizontal strip) rather than top-right — top-right overlaps
    # classifier curves that pass near (recall ≈ 1, precision ≈ 1).
    _leg_fs = max(10.0, fs["label"] * 0.82)
    _line_h = _leg_fs * 1.4
    labels = []
    item_widths = []
    for color, name, ap in pr_entries:
        txt = f"{name} (AP = {ap:.3f})"
        tw = _estimate_label_width_px(txt, _leg_fs, font_family=body_font)
        labels.append((color, txt))
        item_widths.append(tw)
    if labels:
        swatch_w = 18.0
        gap_x = 16.0
        gap_item = 6.0  # between swatch and text
        # Compute layout: pack items into rows that fit within ax_x1 - ax_x0.
        avail_w = ax_x1 - ax_x0
        rows = []  # list of lists of indices
        cur_row = []
        cur_w = 0.0
        for i, tw in enumerate(item_widths):
            item_w = swatch_w + gap_item + tw
            needed = item_w + (gap_x if cur_row else 0)
            if cur_row and cur_w + needed > avail_w:
                rows.append(cur_row)
                cur_row = [i]
                cur_w = item_w
            else:
                cur_row.append(i)
                cur_w += needed
        if cur_row:
            rows.append(cur_row)
        # Y start: just below the x-axis title. The x axis is drawn at ax_y1;
        # we leave room for ticks (sub_fs_tick) + title line + 10 px.
        strip_y0 = ax_y1 + sub_fs_tick + sub_fs_title + 28
        for ri, row in enumerate(rows):
            yline = strip_y0 + ri * _line_h + _leg_fs
            # Left-align the row at ax_x0.
            cursor = ax_x0
            for idx in row:
                color, txt = labels[idx]
                parts.append(
                    f'<line x1="{cursor:.1f}" y1="{yline - _leg_fs * 0.3:.1f}" '
                    f'x2="{cursor + swatch_w:.1f}" y2="{yline - _leg_fs * 0.3:.1f}" '
                    f'stroke="{color}" stroke-width="2.4"/>'
                )
                parts.append(
                    f'<text x="{cursor + swatch_w + gap_item:.1f}" y="{yline:.1f}" '
                    f'font-size="{_leg_fs}" fill="{ink}" '
                    f'font-family="{body_font}">{_xesc(txt)}</text>'
                )
                cursor += swatch_w + gap_item + item_widths[idx] + gap_x
