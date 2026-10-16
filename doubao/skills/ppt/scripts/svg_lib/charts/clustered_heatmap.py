"""Clustered heatmap with pairwise-complete Euclidean average linkage."""

from __future__ import annotations

import math
import sys
from decimal import Decimal, localcontext

from ._matrix_core import aligned_matrix, masked, mean, numeric_matrix, render_matrix, reorder_annotation
from ._shared import tr


def _euclid(a, b):
    pairs = [(ai, bi) for ai, bi in zip(a, b) if ai is not None and bi is not None]
    if not pairs:
        raise ValueError("Cannot cluster vectors with no shared observed values; provide an explicit dendrogram order")
    # Pairwise-complete Euclidean distance, scaled for observed dimensionality.
    distance = math.hypot(*(ai - bi for ai, bi in pairs)) * math.sqrt(len(a) / len(pairs))
    if not math.isfinite(distance):
        raise OverflowError("Euclidean distance exceeds float range; clustering uses stable distance normalization")
    return distance


def _wide_distance(a, b):
    """Rare fallback: preserve distance ordering beyond the float exponent range."""
    pairs = [(ai, bi) for ai, bi in zip(a, b) if ai is not None and bi is not None]
    if not pairs:
        raise ValueError("Cannot cluster vectors with no shared observed values; provide an explicit dendrogram order")
    with localcontext() as context:
        context.prec = 40
        squared = sum((Decimal(ai) - Decimal(bi)) ** 2 for ai, bi in pairs)
        return (squared * Decimal(len(a)) / len(pairs)).sqrt()


def _hcluster(data_rows):
    """Average-linkage hierarchical clustering of ``data_rows``."""
    n = len(data_rows)
    if n == 0:
        return [], []
    if n == 1:
        return [0], []
    # Start: each row is a cluster. Represent each active cluster as (id, members, size, centroid_vec_for_display).
    active = {i: {"members": [i], "size": 1} for i in range(n)}
    decimal_mode = False
    try:
        dists = {(i, j): _euclid(data_rows[i], data_rows[j]) for i in range(n) for j in range(i + 1, n)}
    except OverflowError:
        decimal_mode = True
        dists = {(i, j): _wide_distance(data_rows[i], data_rows[j]) for i in range(n) for j in range(i + 1, n)}
    linkage = []
    next_id = n
    heights = {i: 0.0 for i in range(n)}
    for step in range(n - 1):
        best_pair = None
        best_d = float("inf")
        active_ids = list(active.keys())
        for a_idx in range(len(active_ids)):
            for b_idx in range(a_idx + 1, len(active_ids)):
                i, j = active_ids[a_idx], active_ids[b_idx]
                key = (i, j) if i < j else (j, i)
                dd = dists.get(key)
                if dd is None:
                    continue
                if dd < best_d:
                    best_d = dd
                    best_pair = (i, j)
        if best_pair is None:
            raise RuntimeError("Clustering could not construct a complete tree; refusing to omit observations")
        i, j = best_pair
        ni, nj = active[i]["size"], active[j]["size"]
        new_id = next_id
        next_id += 1
        new_members = active[i]["members"] + active[j]["members"]
        linkage.append((i, j, best_d, ni + nj))
        heights[new_id] = best_d
        # Update distances to the newly merged cluster
        new_dists = {}
        for other in active_ids:
            if other == i or other == j:
                continue
            key_oi = (min(other, i), max(other, i))
            key_oj = (min(other, j), max(other, j))
            d_oi = dists.get(key_oi, 0.0)
            d_oj = dists.get(key_oj, 0.0)
            if decimal_mode:
                with localcontext() as context:
                    context.prec = 40
                    d_new = (ni * d_oi + nj * d_oj) / (ni + nj)
            else:
                d_new = (ni / (ni + nj)) * d_oi + (nj / (ni + nj)) * d_oj
            new_dists[(min(other, new_id), max(other, new_id))] = d_new
        # Remove old distances referencing i or j
        dists = {k: v for k, v in dists.items() if i not in k and j not in k}
        dists.update(new_dists)
        del active[i]
        del active[j]
        active[new_id] = {"members": new_members, "size": ni + nj}

    # Leaf order: traverse the final merge tree. Build children map.
    children = {}
    for merge_step, (a, b, d, s) in enumerate(linkage):
        children[n + merge_step] = (a, b)

    def leaves(node):
        if node < n:
            return [node]
        a, b = children[node]
        return leaves(a) + leaves(b)

    root = (n + len(linkage) - 1) if linkage else 0
    order = leaves(root) if linkage else [0]
    if len(linkage) != n - 1 or sorted(order) != list(range(n)):
        raise RuntimeError("Clustering must preserve every row or column index")
    if decimal_mode:
        with localcontext() as context:
            context.prec = 40
            largest = max(distance for _, _, distance, _ in linkage)
            divisor = largest if largest > Decimal(sys.float_info.max) else Decimal(1)
            linkage = [(a, b, float(distance / divisor), size) for a, b, distance, size in linkage]
    return order, linkage


def _apply_user_order(user_dendrogram, n):
    """Validate a permutation and a binary tree; infer order from a supplied tree."""
    if user_dendrogram is None:
        return None, None
    if not isinstance(user_dendrogram, dict):
        raise TypeError("dendrogram must be a dict with order and/or linkage")
    order = user_dendrogram.get("order")
    linkage = list(user_dendrogram.get("linkage") or [])
    leaves = {i: [i] for i in range(n)}
    heights = {i: 0 for i in range(n)}
    if linkage:
        if len(linkage) != n - 1:
            raise ValueError("dendrogram linkage must contain exactly n-1 merges")
        active = set(range(n))
        for step, row in enumerate(linkage):
            if len(row) != 4:
                raise ValueError("each linkage row must be (child_a, child_b, distance, size)")
            a, b, distance, size = row
            if (
                any(not isinstance(v, int) or isinstance(v, bool) for v in (a, b))
                or a == b
                or a not in active
                or b not in active
            ):
                raise ValueError("invalid or reused dendrogram child")
            if not math.isfinite(distance) or distance < max(heights[a], heights[b]):
                raise ValueError("dendrogram distances must be finite and not decrease toward the root")
            merged = leaves[a] + leaves[b]
            if size != len(merged):
                raise ValueError("dendrogram size must equal the number of descendant leaves")
            active.remove(a)
            active.remove(b)
            active.add(n + step)
            leaves[n + step] = merged
            heights[n + step] = distance
        if order is None:
            order = leaves[n + len(linkage) - 1]
    if order is None:
        raise ValueError("dendrogram requires an explicit order or a non-empty linkage")
    if (
        len(order) != n
        or any(not isinstance(i, int) or isinstance(i, bool) for i in order)
        or sorted(order) != list(range(n))
    ):
        raise ValueError("dendrogram order must be a permutation of all matrix indices")
    positions = {leaf: index for index, leaf in enumerate(order)}
    for group in leaves.values():
        group_positions = [positions[i] for i in group]
        if max(group_positions) - min(group_positions) + 1 != len(group):
            raise ValueError("dendrogram order must keep each subtree contiguous to avoid crossing branches")
    return list(order), linkage


def _dendrogram_segments(order, linkage, n):
    """Compute U-shaped line segments for a dendrogram."""
    if not linkage:
        return [], 0.0
    # Leaf x-position by orig id = order.index(id)
    pos = [0.0] * (n + len(linkage))
    for leaf_pos, orig in enumerate(order):
        pos[orig] = float(leaf_pos)
    heights = [0.0] * (n + len(linkage))
    children = {}
    for step, (a, b, d, s) in enumerate(linkage):
        node_id = n + step
        heights[node_id] = d
        children[node_id] = (a, b)
        pos[node_id] = (pos[a] + pos[b]) * 0.5

    max_h = max(heights) if heights else 1.0
    if max_h <= 0:
        max_h = 1.0

    segs = []
    for step, (a, b, d, s) in enumerate(linkage):
        node_id = n + step
        xa = pos[a]
        xb = pos[b]
        ha = heights[a]
        hb = heights[b]
        hc = heights[node_id]
        # vertical lines from a and b up to hc
        segs.append((xa, ha, xa, hc, hc))
        segs.append((xb, hb, xb, hc, hc))
        segs.append((xa, hc, xb, hc, hc))
    return segs, max_h


def _render_dendrogram_horizontal(segs, max_h, x_left, x_right, y_top, y_bot, pal, n_leaves):
    """Render horizontal (row) dendrogram."""
    if not segs or n_leaves < 2:
        return ""
    dend_c = pal.get("muted", pal.get("ink6", "rgba(28,28,26,0.6)"))

    def px(d):
        # d=0 → x_right (leaf side), d=max_h → x_left (root side)
        if max_h <= 0:
            return x_right
        return x_right - (d / max_h) * (x_right - x_left)

    def py(leaf_pos):
        if n_leaves <= 1:
            return (y_top + y_bot) * 0.5
        return y_top + (leaf_pos + 0.5) * (y_bot - y_top) / n_leaves

    parts = []
    for x1, y1, x2, y2, hc in segs:
        parts.append(
            f'<line x1="{px(y1):.1f}" y1="{py(x1):.1f}" '
            f'x2="{px(y2):.1f}" y2="{py(x2):.1f}" '
            f'stroke="{dend_c}" stroke-width="0.5"/>'
        )
    return "".join(parts)


def _render_dendrogram_vertical(segs, max_h, x_left, x_right, y_top, y_bot, pal, n_leaves):
    """Render vertical (col) dendrogram above the heatmap."""
    if not segs or n_leaves < 2:
        return ""
    dend_c = pal.get("muted", pal.get("ink6", "rgba(28,28,26,0.6)"))

    def px(leaf_pos):
        if n_leaves <= 1:
            return (x_left + x_right) * 0.5
        return x_left + (leaf_pos + 0.5) * (x_right - x_left) / n_leaves

    def py(d):
        if max_h <= 0:
            return y_bot
        return y_bot - (d / max_h) * (y_bot - y_top)

    parts = []
    for x1, y1, x2, y2, hc in segs:
        parts.append(
            f'<line x1="{px(x1):.1f}" y1="{py(y1):.1f}" '
            f'x2="{px(x2):.1f}" y2="{py(y2):.1f}" '
            f'stroke="{dend_c}" stroke-width="0.5"/>'
        )
    return "".join(parts)


def make_clustered_heatmap(
    matrix,
    row_labels,
    col_labels,
    *,
    title=None,
    subtitle=None,
    figure_label=None,
    note=None,
    source=None,
    value_unit="",
    log_color=False,
    row_dendrogram=None,
    col_dendrogram=None,
    col_annotation=None,
    row_annotation=None,
    show_values=False,
    width=1300,
    height=1080,
    font_family=None,
    palette=None,
    variant=None,
    multi_mode="auto",
    cell_text=None,
    pvalues=None,
    mask=None,
    colormap="auto",
    midpoint=None,
    vmin=None,
    vmax=None,
    upper_matrix=None,
    upper_scale=None,
    size_matrix=None,
    size_max=None,
    size_label="Size",
):
    """Cluster rows and columns; user order/linkage may replace either tree.

    Missing observations use pairwise-complete, dimension-adjusted Euclidean
    distance; no overlap between vectors is an error rather than an imputation.
    ``row_annotation`` and ``col_annotation`` retain the single-track sequence
    API and also accept dicts mapping track names to sequences. All cell layers
    are reordered together. Split triangles require a shared row/column order.
    """
    data = masked(numeric_matrix(matrix), mask)
    nr, nc = len(data), len(data[0])
    if len(row_labels) != nr or len(col_labels) != nc:
        raise ValueError("row_labels / col_labels must match the matrix shape")
    for name, annotation, n in [("row_annotation", row_annotation, nr), ("col_annotation", col_annotation, nc)]:
        tracks = (
            annotation.values() if isinstance(annotation, dict) else ([annotation] if annotation is not None else [])
        )
        if any(len(track) != n for track in tracks):
            raise ValueError(f"{name} tracks must have {n} values")
    r_order, r_link = _apply_user_order(row_dendrogram, nr)
    c_order, c_link = _apply_user_order(col_dendrogram, nc)
    if r_order is None:
        r_order, r_link = _hcluster(data)
    if c_order is None:
        c_order, c_link = _hcluster([[data[r][c] for r in range(nr)] for c in range(nc)])
    if upper_matrix is not None and (nr != nc or r_order != c_order):
        raise ValueError(
            "A split clustered matrix requires equal row / column orders; provide matching dendrogram orders"
        )

    def reordered(values, name):
        values = aligned_matrix(values, (nr, nc), name)
        return [[values[r][c] for c in c_order] for r in r_order] if values is not None else None

    disp = reordered(data, "matrix")
    row_callback = col_callback = None
    if r_link:
        rs, rh = _dendrogram_segments(r_order, r_link, nr)
        row_callback = lambda x0, x1, y0, y1, pal: _render_dendrogram_horizontal(rs, rh, x0, x1, y0, y1, pal, nr)
    if c_link:
        cs, ch = _dendrogram_segments(c_order, c_link, nc)
        col_callback = lambda x0, x1, y0, y1, pal: _render_dendrogram_vertical(cs, ch, x0, x1, y0, y1, pal, nc)
    modes = {None, "auto", "single", "none", "with_cluster_sizes"}
    if multi_mode not in modes:
        raise ValueError(f"Unknown clustered_heatmap multi_mode {multi_mode!r}")
    if isinstance(row_annotation, dict):
        candidates = list(row_annotation.values())
        categorical = [
            values for values in candidates if any(v is not None and not isinstance(v, (int, float)) for v in values)
        ]
        cluster_track = (
            categorical[0]
            if categorical
            else (candidates[0] if candidates and multi_mode == "with_cluster_sizes" else None)
        )
    else:
        cluster_track = row_annotation
    cluster_keys = (
        [(v[0] if isinstance(v, (tuple, list)) else v) for v in cluster_track] if cluster_track is not None else []
    )
    groups = list(dict.fromkeys(str(v) for v in cluster_keys if v is not None))
    enabled = multi_mode == "with_cluster_sizes" or (multi_mode == "auto" and len(groups) >= 2)
    if enabled and len(groups) < 2:
        raise ValueError("with_cluster_sizes requires a row annotation with at least two groups")
    summary = None
    if enabled:
        items = []
        for group in groups:
            rows = [i for i, v in enumerate(cluster_keys) if v is not None and str(v) == group]
            scores = [(c, mean([abs(data[r][c]) for r in rows if data[r][c] is not None])) for c in range(nc)]
            observed = sorted([(c, v) for c, v in scores if v is not None], key=lambda p: -p[1])
            items.append((group, len(rows), [str(col_labels[c]) for c, _ in observed[:3]]))
        summary = {"title": "Cluster sizes / top features", "items": items}
    variant = (
        ("circle_full" if size_matrix is not None else "square_flat_full")
        if variant in {None, "classic", "default", "academic"}
        else variant
    )
    return render_matrix(
        disp,
        [row_labels[i] for i in r_order],
        [col_labels[j] for j in c_order],
        variant=variant,
        show_values=show_values,
        scale_options={
            "vmin": vmin,
            "vmax": vmax,
            "midpoint": midpoint,
            "colormap": colormap,
            "log": log_color,
            "label": tr("Value ({unit})", unit=value_unit) if value_unit else tr("Value"),
        },
        cell_text=reordered(cell_text, "cell_text"),
        pvalues=reordered(pvalues, "pvalues"),
        upper_matrix=reordered(upper_matrix, "upper_matrix"),
        upper_scale=upper_scale,
        mask=reordered(mask, "mask"),
        size_matrix=reordered(size_matrix, "size_matrix"),
        size_max=size_max,
        size_label=size_label,
        row_annotation=reorder_annotation(row_annotation, r_order),
        col_annotation=reorder_annotation(col_annotation, c_order),
        dendrograms=(row_callback, col_callback),
        summary=summary,
        title=title,
        subtitle=subtitle,
        figure_label=figure_label,
        note=note,
        source=source,
        width=width,
        height=height,
        font_family=font_family,
        palette=palette,
        metadata={
            "chart": "clustered_heatmap",
            "row_order": r_order,
            "col_order": c_order,
            "resolved_mode": "with_cluster_sizes" if enabled else "single",
            "fallback_reason": None,
        },
    )
