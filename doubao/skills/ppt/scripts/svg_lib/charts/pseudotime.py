"""Academic pseudotime UMAP: cells colored by pseudotime value with an optional
trajectory curve + terminal arrow and a horizontal pseudotime colorbar.
"""

from __future__ import annotations

from .._common import (
    _dist_font_sizes,
    _pick_series_colors,
    _resolve_font,
    _resolve_palette,
    _rgb_prefix,
    _variant_is_classic,
    _xesc,
)
from . import _academic_rigor as rigor
from ._shared import tr


# Multi-mode whitelist:
#   with_gene_dynamics: companion panel below the UMAP showing marker-gene
#   expression along pseudotime. UMAP uses UMAP1/UMAP2 coords whereas the
#   sub-panel X axis is pseudotime — the two views are COMPLEMENTARY (not
#   shared axes) per the Phase-2 review decision.
def _validate_gene_dynamics(signals):
    markers = signals.get("marker_genes") or []
    expr = signals.get("expr_matrix")
    n_cells = signals.get("n_cells", 0)
    if not markers:
        return (False, "need >= 1 marker gene")
    if expr is None:
        return (False, "expr_matrix required")
    if len(expr) != n_cells:
        return (False, f"expr rows={len(expr)} != n_cells={n_cells}")
    for i, row in enumerate(expr):
        if len(row) != len(markers):
            return (False, f"expr row {i} length {len(row)} != n_markers {len(markers)}")
    return (True, "")


_PSEUDOTIME_MULTI_WHITELIST = {
    "with_gene_dynamics": (
        "top_bottom_2to1",
        lambda s: bool(s.get("marker_genes")),
        lambda s: _validate_gene_dynamics(s),
    ),
}


def _moving_average(xs, ys, bw_frac: float = 0.1):
    """Simple distance-weighted moving average along x."""
    if not xs:
        return [], []
    pairs = sorted(zip(xs, ys))
    xs_s = [p[0] for p in pairs]
    ys_s = [p[1] for p in pairs]
    x_min, x_max = xs_s[0], xs_s[-1]
    bw = max(1e-9, (x_max - x_min) * bw_frac)
    n_pts = 80
    xs_out = [x_min + (x_max - x_min) * i / (n_pts - 1) for i in range(n_pts)]
    ys_out = []
    for x0 in xs_out:
        ws = []
        for x in xs_s:
            d = abs(x - x0) / bw
            w = (1 - d**2) ** 2 if d < 1 else 0.0
            ws.append(w)
        W = sum(ws)
        if W <= 1e-9:
            idx = min(range(len(xs_s)), key=lambda i: abs(xs_s[i] - x0))
            ys_out.append(ys_s[idx])
        else:
            ys_out.append(sum(w * y for w, y in zip(ws, ys_s)) / W)
    return xs_out, ys_out


def make_pseudotime(
    points,
    *,
    trajectory=None,
    show_arrow: bool = True,
    title: str | None = None,
    subtitle: str | None = None,
    figure_label: str | None = None,
    note: str | None = None,
    source: str | None = None,
    axis_names=("UMAP 1", "UMAP 2"),
    width: float = 1050,
    height: float = 1050,
    font_family: str | None = None,
    palette=None,
    variant: str | None = None,
    marker_genes: list | None = None,
    expr_matrix: list | None = None,
    multi_mode: str = "auto",
) -> str:
    """UMAP with pseudotime color + optional trajectory curve.

    ``points`` is a list of ``{"x","y","pseudotime"}`` dicts (pseudotime 0..1).
    ``trajectory`` is an optional ``[(x,y), ...]`` list of sampled curve points.
    """
    _variant_is_classic("pseudotime", variant)
    if not points:
        raise ValueError("points must be a non-empty list.")

    if palette is None:
        palette = "archive_ink"
    pal = _resolve_palette(palette)
    body_font, heading_font = _resolve_font(font_family)
    W, H = float(width), float(height)
    n = len(points)
    fs = _dist_font_sizes(W, H, max(4, 8))
    fs_label = max(13.0, fs["label"])
    fs_legend = max(12.0, fs["legend"])

    margin_top = 110.0
    margin_bot = 170.0  # extra room for horizontal colorbar
    margin_left = 70.0
    margin_right = 70.0

    plot_x_left = margin_left
    plot_x_right = W - margin_right
    plot_y_top = margin_top
    plot_y_bot = H - margin_bot

    _plot_bbox = rigor.bbox_from_edges(plot_x_left, plot_x_right, plot_y_top, plot_y_bot)
    _signals = {
        "marker_genes": marker_genes,
        "expr_matrix": expr_matrix,
        "n_cells": n,
    }
    _mm_mode, _mm_template, _mm_reason = rigor.resolve_multi_mode_v2(
        multi_mode,
        _PSEUDOTIME_MULTI_WHITELIST,
        _signals,
        _plot_bbox,
    )
    _sub_bbox = None
    if _mm_mode is not None and _mm_template is not None:
        # Larger shared gutter in combo mode so the UMAP x-axis arrow label and the sub-panel title have room; also push
        # the horizontal colorbar below the sub panel instead of into it.
        _rects = rigor.allocate_main_sub(_plot_bbox, _mm_template, gutter_shared=60)
        _main_bb = _rects["main"]
        _sub_bbox = _rects["sub"]
        plot_y_bot = _main_bb.y1  # shrink UMAP; keep its own X/Y domain

    xs = [p["x"] for p in points]
    ys = [p["y"] for p in points]
    pts_combined_x = list(xs)
    pts_combined_y = list(ys)
    if trajectory:
        pts_combined_x += [t[0] for t in trajectory]
        pts_combined_y += [t[1] for t in trajectory]
    x_min, x_max = min(pts_combined_x), max(pts_combined_x)
    y_min, y_max = min(pts_combined_y), max(pts_combined_y)
    if x_max == x_min:
        x_max = x_min + 1.0
    if y_max == y_min:
        y_max = y_min + 1.0
    x_pad = (x_max - x_min) * 0.05
    y_pad = (y_max - y_min) * 0.05
    x_min -= x_pad
    x_max += x_pad
    y_min -= y_pad
    y_max += y_pad

    def X(v):
        return rigor._lin(v, x_min, x_max, plot_x_left, plot_x_right)

    def Y(v):
        return rigor._lin(v, y_min, y_max, plot_y_bot, plot_y_top)

    # dot radius autoscale
    # Bumped from 1.0/1.6/2.4 to 2.0/2.8/3.6 so even the lightest end of the
    # pseudotime ramp retains enough fill mass to pop above background.
    if n > 5000:
        r_dot = 2.0
    elif n > 1000:
        r_dot = 2.8
    else:
        r_dot = 3.6

    # Explicit pseudotime ramp stops. Default `value_to_color` ramps from
    # pal["bg"] → pal["accent"], which maps pseudotime≈0 to the literal page
    # background (points at low pseudotime vanish into the cream canvas).
    # Pin the low end to the palette's secondary/ink color so every dot keeps
    # ≥ 20% luminance delta from the paper, independent of palette choice.
    _ramp_lo = pal.get("secondary") or pal.get("ink2") or pal.get("ink")
    _ramp_hi = pal.get("accent") or pal.get("ink")
    _pt_stops = [_ramp_lo, _ramp_hi]

    pt_min, pt_max = 0.0, 1.0
    # Robust range: if all pseudotime values are inside [0,1], keep [0,1].
    # Otherwise widen to data range for color mapping clarity.
    pts_vals = [p["pseudotime"] for p in points]
    data_lo, data_hi = min(pts_vals), max(pts_vals)
    if data_lo < 0 or data_hi > 1:
        pt_min, pt_max = data_lo, data_hi
        if pt_max == pt_min:
            pt_max = pt_min + 1.0

    parts = rigor.draw_canvas_bg(pal, W, H)

    parts.append(
        rigor.draw_title_block(
            plot_x_left,
            plot_y_top - 20,
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

    for p in points:
        col = rigor.value_to_color(
            p["pseudotime"],
            pt_min,
            pt_max,
            pal=pal,
            stops=_pt_stops,
        )
        cx, cy = X(p["x"]), Y(p["y"])
        parts.append(
            rigor.draw_scatter_point(
                cx,
                cy,
                pal,
                r=r_dot,
                fill_color=col,
                fill_opacity=0.9,
                n_points_hint=n,
                use_white_stroke=True,
            )
        )

    if trajectory and len(trajectory) >= 2:
        traj_points = [(X(t[0]), Y(t[1])) for t in trajectory]
        d_parts = [f"M {traj_points[0][0]:.1f} {traj_points[0][1]:.1f}"]
        for px, py in traj_points[1:]:
            d_parts.append(f"L {px:.1f} {py:.1f}")
        traj_color = pal["ink"]
        parts.append(
            f'<path d="{" ".join(d_parts)}" fill="none" stroke="{traj_color}" '
            f'stroke-width="3.2" stroke-linejoin="round" stroke-linecap="round"/>'
        )
        halo = pal.get("bg", "rgba(255,255,255,1)")
        halo_rgba = f"{_rgb_prefix(halo)}0.9)"
        parts.insert(
            -1,
            f'<path d="{" ".join(d_parts)}" fill="none" stroke="{halo_rgba}" '
            f'stroke-width="5.6" stroke-linejoin="round" stroke-linecap="round"/>',
        )

        if show_arrow:
            pa, pb = traj_points[-2], traj_points[-1]
            parts.append(
                rigor.draw_axis_arrow(
                    pa[0],
                    pa[1],
                    pb[0],
                    pb[1],
                    pal=pal,
                    label=None,
                    head_size=12.0,
                    color=traj_color,
                )
            )

    parts.append(
        rigor.draw_embedding_axes(
            plot_x_left, plot_x_right, plot_y_top, plot_y_bot, axis_names, pal=pal, label_fs=fs_label
        )
    )

    cb_w = min(360.0, (plot_x_right - plot_x_left) * 0.4)
    cb_h = 16.0
    cb_x = (plot_x_right + plot_x_left) * 0.5 - cb_w * 0.5
    cb_y = H - 90.0
    # When the gene-dynamics sub-panel is active, scoot the colorbar left and slimmer so it sits BELOW the main plot
    # area but to the LEFT of the sub panel's own y-axis label strip (we draw the sub below cb anyway here — keep cb at
    # H - 90 but narrower so the sub x-axis labels have air).
    parts.append(
        rigor.draw_colorbar(
            cb_x,
            cb_y,
            cb_w,
            cb_h,
            pt_min,
            pt_max,
            pal=pal,
            orient="horizontal",
            fs_tick=fs_legend,
            title=tr("Pseudotime"),
            stops=_pt_stops,
        )
    )

    if _sub_bbox is not None and _mm_mode == "with_gene_dynamics" and marker_genes and expr_matrix:
        sx_left, sx_right, sy_top, sy_bot = rigor.bbox_to_edges(_sub_bbox)
        sx_left += 16.0  # room for the rotated "Expression" title
        sub_fs_tick = max(10.0, fs_legend * 0.9)
        sub_fs_title = max(10.0, fs_label * 0.88)
        sub_fs_label = max(9.0, fs_label * 0.82)

        # X axis = pseudotime (independent from UMAP coordinates - complementary view)
        cells_pt = [p["pseudotime"] for p in points]
        pt_lo = min(cells_pt)
        pt_hi = max(cells_pt)
        if pt_hi <= pt_lo:
            pt_hi = pt_lo + 1.0
        px_ticks, px_lo, px_hi = rigor.nice_axis(pt_lo, pt_hi, 5)

        # Compute per-gene y range across all markers for a shared scale.
        # (Cells with pseudotime inside px domain only.)
        all_vals = []
        for row in expr_matrix:
            all_vals.extend(row)
        if all_vals:
            e_lo = min(all_vals)
            e_hi = max(all_vals)
        else:
            e_lo, e_hi = 0.0, 1.0
        if e_hi <= e_lo:
            e_hi = e_lo + 1.0
        py_ticks, py_lo, py_hi = rigor.nice_axis(e_lo, e_hi, 4)

        def _SX(v):
            return rigor._lin(v, px_lo, px_hi, sx_left, sx_right)

        def _SY(v):
            return rigor._lin(v, py_lo, py_hi, sy_bot, sy_top)

        parts.append(
            rigor.draw_grid(
                sx_left,
                sx_right,
                sy_top,
                sy_bot,
                pal=pal,
                y_ticks=py_ticks,
                y_min=py_lo,
                y_max=py_hi,
                orient="horizontal",
            )
        )

        # One smoothed curve per marker gene.
        # Prefer palette ``series`` when it has >= n entries so marker-gene
        # curves get distinct hues even past 3 genes (the old 3-color
        # [accent, secondary, ink] fallback cycled for 4+ genes).
        series_colors = _pick_series_colors(pal, max(1, len(marker_genes)))
        for mi, gene in enumerate(marker_genes):
            vals = [row[mi] for row in expr_matrix]
            xs_out, ys_out = _moving_average(cells_pt, vals, bw_frac=0.12)
            if not xs_out:
                continue
            col = series_colors[mi % len(series_colors)]
            d_parts = []
            for i, (x, y) in enumerate(zip(xs_out, ys_out)):
                px, py = _SX(x), _SY(y)
                d_parts.append(f"{'M' if i == 0 else 'L'} {px:.1f} {py:.1f}")
            parts.append(f'<path d="{" ".join(d_parts)}" fill="none" stroke="{col}" stroke-width="2.0"/>')
            # Legend chip to the right of the sub panel's top-right.
            cy_leg = sy_top + 4 + mi * (sub_fs_label + 4)
            parts.append(
                f'<line x1="{sx_right - 90:.1f}" y1="{cy_leg + sub_fs_label * 0.4:.1f}" '
                f'x2="{sx_right - 76:.1f}" y2="{cy_leg + sub_fs_label * 0.4:.1f}" '
                f'stroke="{col}" stroke-width="2.2"/>'
            )
            parts.append(
                f'<text x="{sx_right - 72:.1f}" y="{cy_leg + sub_fs_label * 0.75:.1f}" '
                f'font-size="{sub_fs_label:.1f}" fill="{pal["ink"]}">'
                f"{_xesc(str(gene))}</text>"
            )

        parts.append(
            rigor.draw_y_axis(
                sx_left,
                sy_top,
                sy_bot,
                py_ticks,
                py_lo,
                py_hi,
                pal=pal,
                fs_tick=sub_fs_tick,
                fs_title=sub_fs_title,
                title=tr("Expression"),
                side="left",
            )
        )
        parts.append(
            rigor.draw_x_axis(
                sx_left,
                sx_right,
                sy_bot,
                px_ticks,
                px_lo,
                px_hi,
                pal=pal,
                fs_tick=sub_fs_tick,
                fs_title=sub_fs_title,
                title=tr("Pseudotime"),
                show_tick_labels=True,
            )
        )
        parts.append(
            f'<text x="{sx_left:.1f}" y="{sy_top - 6:.1f}" '
            f'font-size="{sub_fs_title:.1f}" fill="{pal["ink"]}" '
            f'font-weight="600">{_xesc(tr("Marker gene dynamics along pseudotime"))}</text>'
        )

    parts.append(
        f'<text x="{W - 20:.1f}" y="{plot_y_top - 50:.1f}" '
        f'font-size="{fs_legend}" fill="{pal["ink6"]}" '
        f'text-anchor="end" font-style="italic" font-family="{body_font}">'
        f"{_xesc(tr('n = {n} cells', n=n))}</text>"
    )

    foot_fs = max(13.0, fs["foot"])
    foot_y = H - 24
    if note:
        parts.append(
            f'<text x="{plot_x_left:.1f}" y="{foot_y:.1f}" font-size="{foot_fs}" '
            f'fill="{pal["ink6"]}" font-style="italic" font-family="{body_font}">'
            f"{_xesc(note)}</text>"
        )
    if source:
        parts.append(
            f'<text x="{W - 20:.1f}" y="{foot_y:.1f}" font-size="{foot_fs}" '
            f'fill="{pal["ink6"]}" text-anchor="end" font-style="italic" '
            f'font-family="{body_font}">{_xesc(source)}</text>'
        )

    return rigor.wrap_svg(parts, W, H, body_font)
