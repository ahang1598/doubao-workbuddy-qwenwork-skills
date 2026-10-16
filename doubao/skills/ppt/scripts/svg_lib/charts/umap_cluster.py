"""Academic UMAP / t-SNE / PCA cluster scatter. Pure stdlib — no matplotlib /
numpy / scipy. Draws scatter points colored by cluster, two axis-arrow axes
"""

from __future__ import annotations

import math

from .._common import (
    _derive_series_colors,
    _dist_font_sizes,
    _estimate_label_width_px,
    _resolve_font,
    _resolve_palette,
    _rgb_tuple,
    _variant_is_classic,
    _xesc,
)
from . import _academic_rigor as rigor
from ._shared import tr


# Multi-mode whitelist: maps mode name → (template, trigger, validator).
# Dict insertion order defines priority under multi_mode="auto".
def _validate_marker(s):
    md = s.get("marker_data")
    if not md:
        return (False, "marker_data missing")
    needed = ("genes", "clusters", "mean_expr", "pct_expr")
    for k in needed:
        if k not in md:
            return (False, f"missing {k}")
    if len(md["clusters"]) < 2 or len(md["genes"]) < 2:
        return (False, "need >= 2 clusters and >= 2 genes")
    return (True, "")


_UMAP_MULTI_WHITELIST = {
    "with_marker_dotplot": (
        "left_right_1to1",
        lambda s: s.get("marker_data") is not None,
        _validate_marker,
    ),
}


def _normalize_points(points, clusters=None):
    """Accept either list of {"x","y","cluster"} dicts, or a (coords, clusters)"""
    if clusters is None:
        return list(points)
    if len(points) != len(clusters):
        raise ValueError("coords and clusters length mismatch")
    out = []
    for xy, c in zip(points, clusters):
        if isinstance(xy, dict):
            out.append(xy)
        else:
            out.append({"x": float(xy[0]), "y": float(xy[1]), "cluster": c})
    return out


def make_umap_cluster(
    points,
    clusters=None,
    *,
    cluster_names=None,
    cluster_colors=None,
    title: str | None = None,
    subtitle: str | None = None,
    figure_label: str | None = None,
    note: str | None = None,
    source: str | None = None,
    axis_names=("UMAP 1", "UMAP 2"),
    show_cluster_labels: bool = True,
    show_legend: bool = True,
    alpha: float = 0.6,
    r: float | None = None,
    width: float = 1050,
    height: float = 1050,
    font_family: str | None = None,
    palette=None,
    variant: str | None = None,
    multi_mode: str = "auto",
    marker_data: dict | None = None,
) -> str:
    """UMAP / t-SNE / PCA style cluster scatter.

    ``points`` is a list of ``{"x","y","cluster"}`` dicts, OR a list of
    ``(x, y)`` tuples when ``clusters`` is also provided as a parallel list.

    When ``multi_mode="auto"`` and ``marker_data`` is given, the plot carves a
    right-hand dotplot sub-panel showing cluster × gene mean / pct expression.
    """
    _variant_is_classic("umap_cluster", variant)
    points = _normalize_points(points, clusters)
    if not points:
        raise ValueError("points must be a non-empty list.")

    if palette is None:
        palette = "archive_ink"
    pal = _resolve_palette(palette)
    body_font, heading_font = _resolve_font(font_family)
    W, H = float(width), float(height)
    n = len(points)

    if cluster_names is None:
        seen = []
        for p in points:
            c = p["cluster"]
            if c not in seen:
                seen.append(c)
        cluster_names = seen
    k = len(cluster_names)

    # Derive cluster colors — fall back to palette-derived series
    if cluster_colors is None:
        series = _derive_series_colors(pal, k)
        cluster_colors = {name: series[i] for i, name in enumerate(cluster_names)}
    else:
        # fill any missing cluster with derived series
        series = _derive_series_colors(pal, k)
        filled = {}
        for i, name in enumerate(cluster_names):
            filled[name] = cluster_colors.get(name, series[i])
        cluster_colors = filled

    fs = _dist_font_sizes(W, H, max(4, k))
    fs_label = max(13.0, fs["label"])
    fs_legend = max(12.0, fs["legend"])

    margin_top = 110.0
    margin_bot = 110.0
    margin_left = 70.0
    margin_right = 70.0

    plot_x_left = margin_left
    plot_x_right = W - margin_right
    plot_y_top = margin_top
    plot_y_bot = H - margin_bot

    _canvas_bbox = rigor.bbox_from_edges(plot_x_left, plot_x_right, plot_y_top, plot_y_bot)
    _chosen_mode, _chosen_template, _reason = rigor.resolve_multi_mode_v2(
        multi_mode,
        _UMAP_MULTI_WHITELIST,
        {"marker_data": marker_data},
        _canvas_bbox,
    )
    _sub_bbox = None
    if _chosen_mode == "with_marker_dotplot":
        _rects = rigor.allocate_main_sub(_canvas_bbox, "left_right_3to1", gutter_free=36.0)
        plot_x_right = _rects["main"].x1  # shrink main plot
        _sub_bbox = _rects["sub"]

    # Data ranges with 4% padding on each side
    xs = [p["x"] for p in points]
    ys = [p["y"] for p in points]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    if x_max == x_min:
        x_max = x_min + 1.0
    if y_max == y_min:
        y_max = y_min + 1.0
    x_pad = (x_max - x_min) * 0.04
    y_pad = (y_max - y_min) * 0.04
    x_min -= x_pad
    x_max += x_pad
    y_min -= y_pad
    y_max += y_pad

    def X(v):
        return rigor._lin(v, x_min, x_max, plot_x_left, plot_x_right)

    def Y(v):
        return rigor._lin(v, y_min, y_max, plot_y_bot, plot_y_top)

    if r is None:
        if n > 5000:
            r = 1.0
        elif n > 1000:
            r = 1.6
        else:
            r = 2.4

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

    cluster_centroids = {name: [0.0, 0.0, 0] for name in cluster_names}
    # R2 P2: dense UMAP (> 500 points) gets a white hairline stroke so dots
    # don't mush together — classic Nature / Cell UMAP convention.
    _white_stroke = n > 500
    for p in points:
        c = p["cluster"]
        col = cluster_colors.get(c, pal["accent"])
        cx, cy = X(p["x"]), Y(p["y"])
        parts.append(
            rigor.draw_scatter_point(
                cx,
                cy,
                pal,
                r=r,
                fill_color=col,
                fill_opacity=alpha,
                n_points_hint=n,
                use_white_stroke=_white_stroke,
            )
        )
        if c in cluster_centroids:
            cluster_centroids[c][0] += cx
            cluster_centroids[c][1] += cy
            cluster_centroids[c][2] += 1

    for centroid in cluster_centroids.values():
        _, _, cnt = centroid
        if cnt > 0:
            centroid[0] /= cnt
            centroid[1] /= cnt

    parts.append(
        rigor.draw_embedding_axes(
            plot_x_left, plot_x_right, plot_y_top, plot_y_bot, axis_names, pal=pal, label_fs=fs_label
        )
    )

    # Lint-driven approach: a label text bbox that overlaps a scatter dot
    # (whose center is outside the dot) counts as embed_svg_text_shape_overlap.
    # So for every cluster:
    #   1) start at the centroid
    #   2) push the label radially outward (away from the overall scatter
    #      centroid) until no scatter dot of ANY cluster lies inside the
    #      label's text bbox.
    #   3) then run a label-vs-label repulsion so halo rects stay disjoint.
    #   4) if the label moved, draw a thin leader line centroid -> label.
    #   5) wrap the glyphs with draw_label_with_halo so the halo rect
    #      encloses the text (text-container-overflow safe) and reads over
    #      busy backgrounds.
    if show_cluster_labels:
        # pre-compute global scatter centroid (used as the "push away from"
        # anchor) — this is the mean of all point screen coordinates.
        _all_cx = sum(X(p["x"]) for p in points) / float(n)
        _all_cy = sum(Y(p["y"]) for p in points) / float(n)
        # pre-compute every point's screen position + its draw radius
        _pt_cx = [X(p["x"]) for p in points]
        _pt_cy = [Y(p["y"]) for p in points]
        _pt_r = r

        _halo_pad_x = 5.0
        _halo_pad_y = 2.5
        # ascent and descent heuristics must match the lint validator's
        # text-bbox model (_SVG_TEXT_ASCENT_RATIO ~ 0.82, descent ~ 0.22).
        _asc = 0.82
        _dsc = 0.22
        _label_h_text = fs_label * (_asc + _dsc)

        _label_items = []
        for name in cluster_names:
            ccx, ccy, cnt = cluster_centroids[name]
            if cnt == 0:
                continue
            label = str(name)
            tw = _estimate_label_width_px(label, fs_label, bold=True, font_family=body_font)
            _label_items.append(
                {
                    "name": name,
                    "anchor_cx": ccx,
                    "anchor_cy": ccy,
                    "lx": ccx,  # label text x (center, text-anchor=middle)
                    "ly": ccy + fs_label * 0.33,  # baseline y
                    "tw": tw,
                    "label": label,
                }
            )

        def _text_bbox(it):
            # mirrors embed_svg_validator._svg_visual_bbox for text with
            # text-anchor=middle: box.x = x - w/2
            halo_rx = it["lx"] - it["tw"] * 0.5 - _halo_pad_x
            halo_ry = it["ly"] - fs_label * _asc - _halo_pad_y
            halo_rw = it["tw"] + _halo_pad_x * 2
            halo_rh = _label_h_text + _halo_pad_y * 2
            return halo_rx, halo_ry, halo_rx + halo_rw, halo_ry + halo_rh

        def _dot_in_label(it):
            """Return True if any scatter dot's bbox overlaps the halo bbox"""
            bx0, by0, bx1, by1 = _text_bbox(it)
            # text center for the lint "inside shape" short-circuit — but
            # here we check overlap with the opposite primitive. The lint
            # does: shape overlaps text AND text.center outside shape. For a
            # tiny scatter dot of radius ~2 the text center will always be
            # outside it (unless the label literally sits on the dot). So we
            # simply require no dot bbox intersects the halo bbox.
            r_dot = _pt_r + 0.6  # include stroke margin
            for px, py in zip(_pt_cx, _pt_cy):
                if px + r_dot < bx0 or px - r_dot > bx1:
                    continue
                if py + r_dot < by0 or py - r_dot > by1:
                    continue
                return True
            return False

        def _radial_push(it, dx_hint, dy_hint, max_steps=22, step=11.0):
            """Push label along a radial direction until no dot intersects"""
            # pre-compute direction unit vector (away from global centroid).
            vx = it["anchor_cx"] - _all_cx
            vy = it["anchor_cy"] - _all_cy
            vl = math.hypot(vx, vy)
            if vl < 1e-6:
                # centroid is dead center — pick a stable direction based
                # on cluster index (deterministic across renders).
                i = cluster_names.index(it["name"]) if it["name"] in cluster_names else 0
                k_total = max(1, k)
                ang = 2.0 * math.pi * i / k_total - math.pi * 0.5
                ux, uy = math.cos(ang), math.sin(ang)
            else:
                ux, uy = vx / vl, vy / vl
            if dx_hint is not None:
                ux, uy = dx_hint, dy_hint
            for _ in range(max_steps):
                if not _dot_in_label(it):
                    return
                nlx = it["lx"] + ux * step
                nly = it["ly"] + uy * step
                # keep inside plot area
                half_w = it["tw"] * 0.5 + _halo_pad_x + 1
                half_h = _label_h_text * 0.5 + _halo_pad_y + 1
                if nlx - half_w < plot_x_left + 2 or nlx + half_w > plot_x_right - 2:
                    ux = -ux * 0.5
                if nly - half_h < plot_y_top + 2 or nly + half_h > plot_y_bot - 2:
                    uy = -uy * 0.5
                it["lx"] += ux * step
                it["ly"] += uy * step

        for it in _label_items:
            _radial_push(it, None, None)

        # Label-vs-label de-collision: push the smaller-y label up and the
        # other down until halo rects no longer intersect. Up to 40 passes.
        for _ in range(40):
            moved = False
            _label_items.sort(key=lambda t: t["ly"])
            for i in range(len(_label_items)):
                for j in range(i + 1, len(_label_items)):
                    a = _label_items[i]
                    b = _label_items[j]
                    ax0, ay0, ax1, ay1 = _text_bbox(a)
                    bx0, by0, bx1, by1 = _text_bbox(b)
                    if ax1 <= bx0 or bx1 <= ax0:
                        continue
                    if ay1 <= by0 or by1 <= ay0:
                        continue
                    # overlap — push them apart vertically by the smaller of
                    # the two overlap amounts.
                    overlap_y = min(ay1, by1) - max(ay0, by0) + 1.5
                    half = overlap_y * 0.5
                    # Keep both inside plot area
                    if a["ly"] - half - _label_h_text * 0.5 > plot_y_top + 4:
                        a["ly"] -= half
                    if b["ly"] + half + _label_h_text * 0.5 < plot_y_bot - 4:
                        b["ly"] += half
                    moved = True
            if not moved:
                break

        # Re-check against dots after label-label resolution — one more
        # radial sweep per label to recover.
        for it in _label_items:
            if _dot_in_label(it):
                _radial_push(it, None, None, max_steps=10, step=8.0)

        # Final rescue pass: if any label still intersects a dot (which can happen when the radial direction was blocked
        # by the plot edge or by another cluster), scan multiple angles around the centroid and keep the first direction
        # that admits a non-overlapping position within a reasonable push distance.
        for it in _label_items:
            if not _dot_in_label(it):
                continue
            # Reset to anchor and try 16 directions × 20 steps.
            original_lx, original_ly = it["lx"], it["ly"]
            best = None
            for ang_i in range(16):
                ang = 2.0 * math.pi * ang_i / 16.0
                ux, uy = math.cos(ang), math.sin(ang)
                it["lx"] = it["anchor_cx"]
                it["ly"] = it["anchor_cy"] + fs_label * 0.33
                for step_i in range(1, 20):
                    it["lx"] = it["anchor_cx"] + ux * step_i * 9.0
                    it["ly"] = it["anchor_cy"] + fs_label * 0.33 + uy * step_i * 9.0
                    half_w = it["tw"] * 0.5 + _halo_pad_x + 1
                    half_h = _label_h_text * 0.5 + _halo_pad_y + 1
                    if (
                        it["lx"] - half_w < plot_x_left + 2
                        or it["lx"] + half_w > plot_x_right - 2
                        or it["ly"] - half_h < plot_y_top + 2
                        or it["ly"] + half_h > plot_y_bot - 2
                    ):
                        break
                    if not _dot_in_label(it):
                        d = step_i
                        if best is None or d < best[0]:
                            best = (d, it["lx"], it["ly"])
                        break
            if best is not None:
                it["lx"], it["ly"] = best[1], best[2]
            else:
                it["lx"], it["ly"] = original_lx, original_ly

        for it in _label_items:
            anchor_cx, anchor_cy = it["anchor_cx"], it["anchor_cy"]
            lx, ly = it["lx"], it["ly"]
            # Visual distance from centroid to label center
            cx_lab = lx
            cy_lab = ly - fs_label * (_asc - 0.5)
            dx = cx_lab - anchor_cx
            dy = cy_lab - anchor_cy
            dist = math.hypot(dx, dy)
            if dist > fs_label * 0.9:
                # leader line stops at the halo rect edge (not into text)
                # — approximate by scaling 92% of the way.
                lead_t = max(0.0, 1.0 - (fs_label * 0.9 + 2) / dist)
                tx2 = anchor_cx + dx * lead_t
                ty2 = anchor_cy + dy * lead_t
                parts.append(
                    f'<line x1="{anchor_cx:.1f}" y1="{anchor_cy:.1f}" '
                    f'x2="{tx2:.1f}" y2="{ty2:.1f}" '
                    f'stroke="{pal.get("ink4", "rgba(28,28,26,0.4)")}" '
                    f'stroke-width="0.7" stroke-dasharray="2 2"/>'
                )
            parts.append(
                rigor.draw_label_with_halo(
                    lx,
                    ly,
                    it["label"],
                    pal,
                    fs=fs_label,
                    anchor="middle",
                    color=pal["ink"],
                    halo_alpha=0.9,
                    halo_pad_x=_halo_pad_x,
                    halo_pad_y=_halo_pad_y,
                    bold=True,
                    font_family=body_font,
                )
            )

    # Centroid labels already identify each cluster inside the plot, so the legend becomes a secondary read — moving it
    # to a horizontal strip below plot_y_bot keeps every data point visible while still giving a canonical colour → name
    # mapping.
    if show_legend:
        row_h = fs_legend * 1.6
        dot_slot_w = 14.0
        glyph_gap = 6.0
        item_gap = 20.0
        item_text_widths = [
            _estimate_label_width_px(str(name), fs_legend, font_family=body_font) for name in cluster_names
        ]
        item_widths = [dot_slot_w + glyph_gap + w for w in item_text_widths]
        plot_w = plot_x_right - plot_x_left
        # Try single-row layout first; if items don't fit, wrap into two rows.
        total_w_single = sum(item_widths) + item_gap * max(0, len(item_widths) - 1)
        if total_w_single <= plot_w:
            rows = [list(range(len(item_widths)))]
        else:
            # Greedy two-row split: fill row 0 until it would overflow, then
            # push remainder to row 1.
            rows = [[], []]
            cur_w = 0.0
            r = 0
            for i, w in enumerate(item_widths):
                add = w + (item_gap if rows[r] else 0.0)
                if cur_w + add > plot_w and r == 0:
                    r = 1
                    cur_w = 0.0
                    add = w
                rows[r].append(i)
                cur_w += add
        # Baseline for the first row: ~44px below plot_y_bot (clears UMAP
        # bottom-left axis arrows). Second row (if any) sits one row below.
        strip_y0 = plot_y_bot + 44
        for r_idx, row in enumerate(rows):
            if not row:
                continue
            row_w = sum(item_widths[i] for i in row) + item_gap * max(0, len(row) - 1)
            cur_x = plot_x_left + max(0.0, (plot_w - row_w) * 0.5)
            row_cy = strip_y0 + r_idx * row_h
            for pos, i in enumerate(row):
                name = cluster_names[i]
                dot_x = cur_x + dot_slot_w * 0.5
                parts.append(
                    f'<circle cx="{dot_x:.2f}" cy="{row_cy:.2f}" r="5.5" fill="{cluster_colors[name]}" stroke="none"/>'
                )
                text_x = cur_x + dot_slot_w + glyph_gap
                parts.append(
                    f'<text x="{text_x:.1f}" y="{row_cy + fs_legend * 0.35:.1f}" '
                    f'font-size="{fs_legend}" fill="{pal["ink"]}" '
                    f'font-family="{body_font}">{_xesc(str(name))}</text>'
                )
                cur_x += item_widths[i] + item_gap

    parts.append(
        f'<text x="{W - 20:.1f}" y="{plot_y_top - 50:.1f}" '
        f'font-size="{fs_legend}" fill="{pal["ink6"]}" '
        f'text-anchor="end" font-style="italic" font-family="{body_font}">'
        f"{_xesc(tr('n = {n} cells, k = {k} clusters', n=n, k=k))}</text>"
    )

    foot_fs = max(13.0, fs["foot"])
    foot_y = H - 32
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

    if _sub_bbox is not None and _chosen_mode == "with_marker_dotplot":
        parts.append(
            _render_marker_dotplot(
                _sub_bbox,
                marker_data,
                cluster_colors,
                cluster_names,
                pal,
                body_font,
                fs,
            )
        )

    return rigor.wrap_svg(parts, W, H, body_font)


def _render_marker_dotplot(
    sub_bbox,
    marker_data,
    cluster_colors,
    cluster_names_main,
    pal,
    body_font,
    fs,
) -> str:
    """Draw cluster × gene expression dotplot on the right sub-panel."""
    genes = list(marker_data["genes"])
    md_clusters = list(marker_data["clusters"])
    mean_expr = marker_data["mean_expr"]
    pct_expr = marker_data["pct_expr"]
    # Map md cluster → row index in md tables
    md_index = {c: i for i, c in enumerate(md_clusters)}
    # Row order: main's cluster_names first, then any md clusters not in main
    row_order = list(cluster_names_main) + [c for c in md_clusters if c not in cluster_names_main]

    sx0, sy0, sx1, sy1 = sub_bbox.x0, sub_bbox.y0, sub_bbox.x1, sub_bbox.y1
    ink = pal.get("ink", "rgba(28,28,26,1)")
    ink6 = pal.get("ink6", "rgba(28,28,26,0.6)")
    ink2 = pal.get("ink2", "rgba(28,28,26,0.2)")
    ink4 = pal.get("ink4", "rgba(28,28,26,0.4)")
    accent = pal.get("accent", "#D96A2E")

    # Font sizes = main × 0.88
    fs_hdr = max(13.0, fs["label"] * 1.0)
    fs_label = max(11.0, fs["label"] * 0.88)
    fs_tick = max(10.0, fs["label"] * 0.80)

    # Layout: header title row, column gene labels row (bottom), row cluster
    # labels on left, legend swatches on top-right of panel header.
    pad = 12.0
    label_left_w = max(
        50.0, max((_estimate_label_width_px(c, fs_label, font_family=body_font) for c in row_order), default=50.0) + 8.0
    )
    gene_label_h = max(
        fs_tick * 5.0, 56.0
    )  # bottom reserved for rotated gene labels (steeper 60° angle needs more height but less horizontal reach)
    legend_h = fs_hdr * 2.6 + 10.0
    grid_x0 = sx0 + label_left_w
    grid_x1 = sx1 - pad
    grid_y0 = sy0 + legend_h + fs_hdr + 8
    grid_y1 = sy1 - gene_label_h
    n_rows = len(row_order)
    n_cols = len(genes)
    if n_rows == 0 or n_cols == 0 or grid_x1 <= grid_x0 or grid_y1 <= grid_y0:
        return ""
    cell_w = (grid_x1 - grid_x0) / n_cols
    cell_h = (grid_y1 - grid_y0) / n_rows
    r_max = min(cell_w, cell_h) * 0.42
    r_min = r_max * 0.2

    # Compute mean_expr normalization across whole marker_data
    all_m = [m for row in mean_expr for m in row]
    m_lo = min(all_m) if all_m else 0.0
    m_hi = max(all_m) if all_m else 1.0
    if m_hi == m_lo:
        m_hi = m_lo + 1.0

    def mean_to_color(m):
        # linear interp ink2 (low) → accent (high) via blend on RGB
        t = (m - m_lo) / (m_hi - m_lo)
        t = max(0.0, min(1.0, t))
        # parse accent (hex) → rgb; fallback to accent for all
        r2, g2, b2 = _rgb_tuple(accent)
        # low color: muted ink2 — approximate with 20% opacity of accent
        r1 = int(r2 + (255 - r2) * 0.78)
        g1 = int(g2 + (255 - g2) * 0.78)
        b1 = int(b2 + (255 - b2) * 0.78)
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)
        return f"rgb({r},{g},{b})"

    parts = []
    parts.append(
        f'<text x="{sx0 + pad:.1f}" y="{sy0 + fs_hdr + 2:.1f}" font-size="{fs_hdr:.1f}" '
        f'fill="{ink}" font-weight="700" font-family="{body_font}">{_xesc(tr("Marker expression"))}</text>'
    )
    # Vertical hairline separating main plot from sub panel
    parts.append(
        f'<line x1="{sx0:.1f}" y1="{sy0:.1f}" x2="{sx0:.1f}" y2="{sy1:.1f}" '
        f'stroke="{ink2}" stroke-width="0.6" stroke-dasharray="3 3"/>'
    )
    for ri, cname in enumerate(row_order):
        cy = grid_y0 + cell_h * (ri + 0.5)
        col = cluster_colors.get(cname, ink)
        parts.append(
            f'<circle cx="{sx0 + pad + 5:.1f}" cy="{cy:.1f}" r="4.5" fill="{col}" stroke="{ink}" stroke-width="0.5"/>'
        )
        parts.append(
            f'<text x="{sx0 + pad + 15:.1f}" y="{cy + fs_label * 0.35:.1f}" font-size="{fs_label:.1f}" '
            f'fill="{ink}" font-style="italic" font-family="{body_font}">{_xesc(str(cname))}</text>'
        )

    # Padding bumped from 8→16 px so the label origin sits well below the dot grid before rotation starts.
    _gene_label_pad = 16.0
    for gi, gname in enumerate(genes):
        cx = grid_x0 + cell_w * (gi + 0.5)
        y = grid_y1 + _gene_label_pad
        parts.append(
            f'<text x="{cx:.1f}" y="{y:.1f}" font-size="{fs_tick:.1f}" fill="{ink}" '
            f'text-anchor="start" transform="rotate(60 {cx:.1f} {y:.1f})" '
            f'font-family="{body_font}">{_xesc(str(gname))}</text>'
        )

    for ri, cname in enumerate(row_order):
        md_ri = md_index.get(cname)
        if md_ri is None:
            continue
        for gi in range(n_cols):
            pct = max(0.0, min(1.0, float(pct_expr[md_ri][gi])))
            m = float(mean_expr[md_ri][gi])
            if pct <= 0.01:
                continue
            cx = grid_x0 + cell_w * (gi + 0.5)
            cy = grid_y0 + cell_h * (ri + 0.5)
            r = r_min + (r_max - r_min) * (pct**0.5)
            fill = mean_to_color(m)
            parts.append(
                f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{fill}" stroke="{ink4}" stroke-width="0.4"/>'
            )

    # Legends (top-right of panel): size legend + mean colorbar.
    lg_x = sx1 - pad - 100
    lg_y = sy0 + fs_hdr + 10
    parts.append(
        f'<text x="{lg_x:.1f}" y="{lg_y + fs_tick:.1f}" font-size="{fs_tick:.1f}" '
        f'fill="{ink6}" font-family="{body_font}">{_xesc(tr("% expr"))}</text>'
    )
    # Reference circles row — y center placed so the TOP of the biggest reference circle sits well below the caption
    # baseline.
    _circle_row_cy = lg_y + fs_tick + r_max + 6
    for i, pct_ref in enumerate((0.25, 0.5, 1.0)):
        cxr = lg_x + 10 + i * 28
        cyr = _circle_row_cy
        rr = r_min + (r_max - r_min) * (pct_ref**0.5)
        parts.append(
            f'<circle cx="{cxr:.1f}" cy="{cyr:.1f}" r="{rr:.1f}" fill="{ink6}" stroke="{ink4}" stroke-width="0.4"/>'
        )
        parts.append(
            f'<text x="{cxr:.1f}" y="{cyr + rr + fs_tick + 2:.1f}" font-size="{fs_tick * 0.9:.1f}" '
            f'fill="{ink6}" text-anchor="middle" font-family="{body_font}">{int(pct_ref * 100)}</text>'
        )
    # Mean colorbar: left of size legend if room; else below
    cb_x0 = sx0 + pad + label_left_w - pad
    cb_x1 = lg_x - 10
    if cb_x1 - cb_x0 >= 60:
        cb_y = lg_y + fs_tick + 8
        cb_h = 8
        n_steps = 16
        step_w = (cb_x1 - cb_x0) / n_steps
        for i in range(n_steps):
            t = i / (n_steps - 1)
            m = m_lo + t * (m_hi - m_lo)
            parts.append(
                f'<rect x="{cb_x0 + i * step_w:.1f}" y="{cb_y:.1f}" '
                f'width="{step_w + 0.5:.2f}" height="{cb_h}" fill="{mean_to_color(m)}" stroke="none"/>'
            )
        parts.append(
            f'<text x="{cb_x0:.1f}" y="{cb_y + cb_h + fs_tick + 2:.1f}" font-size="{fs_tick * 0.9:.1f}" '
            f'fill="{ink6}" font-family="{body_font}">{m_lo:.2g}</text>'
        )
        parts.append(
            f'<text x="{cb_x1:.1f}" y="{cb_y + cb_h + fs_tick + 2:.1f}" font-size="{fs_tick * 0.9:.1f}" '
            f'fill="{ink6}" text-anchor="end" font-family="{body_font}">{m_hi:.2g}</text>'
        )
        parts.append(
            f'<text x="{(cb_x0 + cb_x1) * 0.5:.1f}" y="{cb_y - 2:.1f}" font-size="{fs_tick:.1f}" '
            f'fill="{ink6}" text-anchor="middle" font-family="{body_font}">{_xesc(tr("mean expr"))}</text>'
        )

    return "".join(parts)
