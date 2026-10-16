"""Scientific association and enrichment networks with deterministic layouts."""

from __future__ import annotations

import math

from ._chart_layout import finite, wrap_lines
from ._network_core import (
    aligned_tracks,
    fit_positions,
    graph_positions,
    node_colors,
    node_radii,
    normalize_network,
    render_edges,
    render_label_rails,
    render_nodes,
    render_size_key,
    separate_nodes,
)
from ._polar import PolarGeometry, legend_rows, polar_layout, render_legend, render_tracks
from ._shared import tr


def render_network_plot(canvas, bbox, nodes, edges, *, layout="force", positions=None, tracks=None):
    """Append absolute-coordinate marks to ChartLayout."""
    data, links = normalize_network(nodes, edges)
    xy = graph_positions(data, links, layout, positions)
    x0, y0, x1, y1 = (finite(v, "bbox") for v in bbox)
    if x1 <= x0 or y1 <= y0:
        raise ValueError("bbox requires left < right and top < bottom")
    rail = min(175, (x1 - x0) * 0.18) if any(n["label"] for n in data) else 0
    margin = rail + 34
    outer_ids = [n["id"] for n in data if n.get("side", "outer") == "outer"]
    if tracks and layout != "radial":
        raise ValueError("outer tracks require layout='radial'")
    rings = aligned_tracks(tracks, outer_ids, outer_ids, canvas.pal) if tracks else []
    if rings and not outer_ids:
        raise ValueError("radial tracks require outer nodes")
    thickness = 20
    track_room = len(rings) * (thickness + 4) + (8 if rings else 0)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    max_loops = max((sum(e["source"] == e["target"] == n["id"] for e in links) for n in data), default=0)
    vertical_margin = max(32, 40 + (max_loops - 1) * 14) if max_loops else 32
    radius = min((x1 - x0) / 2 - margin, (y1 - y0) / 2 - vertical_margin) - track_room
    if radius < 35:
        raise ValueError("plot bbox is too small for network nodes and tracks")
    radii = node_radii(data, min(13, max(5, radius / math.sqrt(len(data)) * 0.32)))
    if layout == "radial":
        resolved = {key: (cx + x * radius, cy + y * radius) for key, (x, y) in xy.items()}
    else:
        resolved = fit_positions(xy, (cx - radius, cy - radius, cx + radius, cy + radius))
    label_sides = {key: 1 if point[0] >= cx else -1 for key, point in resolved.items()}
    if layout == "force" and positions is None:
        resolved = separate_nodes(resolved, radii, (cx - radius, cy - radius, cx + radius, cy + radius))
    if positions is not None:
        identifiers = list(resolved)
        for i, first in enumerate(identifiers):
            for second in identifiers[:i]:
                distance = math.dist(resolved[first], resolved[second])
                if distance < max(radii[first], 2.2) + max(radii[second], 2.2) + 1:
                    raise ValueError(
                        f"fixed positions overlap for {first!r} and {second!r}; "
                        "increase the canvas or provide separated positions"
                    )
    colors = node_colors(data, canvas.pal)
    render_edges(canvas, links, resolved, radii)
    render_nodes(canvas, data, resolved, radii, colors)
    label_points = dict(resolved)
    if rings:
        geometry = PolarGeometry(cx, cy, 0, radius, len(outer_ids))
        rim = render_tracks(canvas, geometry, rings, radius + 17, thickness)
        for i, key in enumerate(outer_ids):
            label_points[key] = geometry.point(rim + 4, geometry.angle(i))
    items = [
        {
            "id": n["id"],
            "label": n["label"],
            "point": label_points[n["id"]],
            "radius": radii[n["id"]],
            "side": label_sides[n["id"]],
        }
        for n in data
    ]
    boxes = render_label_rails(canvas, items, (x0, y0, x1, y1), rail) if rail else []
    return {
        "plot_bbox": tuple(bbox),
        "positions": resolved,
        "node_radii": radii,
        "node_colors": colors,
        "outer_order": outer_ids if layout == "radial" else [],
        "tracks": rings,
        "protected_labels": boxes,
        "resolved_layout": layout,
    }


def make_network(
    nodes,
    edges,
    *,
    layout="force",
    positions=None,
    tracks=None,
    title=None,
    subtitle=None,
    figure_label=None,
    note=None,
    width=1080,
    height=800,
    palette=None,
    font_family=None,
):
    """Return an SVG from precomputed graph nodes/associations, with no analysis.

    Nodes: ``{id, label?, category?, size?, color?, side?}``. IDs are unique
    strings; only explicit nonempty labels are drawn. Node area maps nonnegative
    size; zero/missing sizes use an open marker. Edges: ``{source, target,
    weight?, correlation?, pvalue?, color?}``. Width uses absolute weight (or
    absolute correlation), color uses correlation sign (or weight sign), and
    P >= .05 uses a dashed translucent stroke. Every edge remains present,
    including zero, self edges and parallel edges. P values are supplied results.

    ``layout`` is force, radial or bipartite. Explicit positions map every ID
    to [x, y], preserving aspect ratio. Radial nodes use side=inner/outer;
    outer nodes retain input order. Bipartite uses side=left/right and rejects
    within-side edges. Radial tracks use ``{name, kind, values, range?, ...}``
    (kind heatmap/category/bar/point); values are an outer-ID map or array in outer input order.
    Height/width may grow to preserve all labels and readable graph geometry.
    """
    data, links = normalize_network(nodes, edges)
    xy = graph_positions(data, links, layout, positions)
    n = len(data)
    width = max(finite(width, "width", minimum=300), 300 + max(0, math.sqrt(n) - 3.9) * 135 + len(tracks or []) * 48)
    canvas = polar_layout(width, height, palette, font_family, n_items=n)
    top = canvas.header(title, subtitle, figure_label)
    outer_ids = [node["id"] for node in data if node.get("side", "outer") == "outer"]
    if tracks and layout != "radial":
        raise ValueError("outer tracks require layout='radial'")
    rings = aligned_tracks(tracks, outer_ids, outer_ids, canvas.pal) if tracks else []
    colors = node_colors(data, canvas.pal)
    category_entries = []
    for category in dict.fromkeys(node["category"] for node in data):
        first = next(node for node in data if node["category"] == category)
        category_entries.append({"name": category, "color": colors[first["id"]], "direction": "out"})
    rows, legend_height = legend_rows(canvas, category_entries, rings)
    encodings = []
    if any(link["_sign"] is not None for link in links):
        encodings.extend(
            [
                (tr("Positive"), canvas.pal["accent"]),
                (tr("Negative"), canvas.pal["secondary"]),
                (tr("Zero / unspecified"), canvas.pal["ink4"]),
            ]
        )
    edge_rows, edge_legend_h = legend_rows(
        canvas, [{"name": label, "color": color, "direction": "out"} for label, color in encodings], []
    )
    legend_height += edge_legend_h
    size_key_h = 38 if any(node["size"] is not None for node in data) else 0
    legend_height += size_key_h
    text = ""
    if any(link["_weighted"] for link in links):
        maximum = max(link["_magnitude"] for link in links)
        text += tr("Edge width: absolute weight / correlation (0–{max}). ", max=f"{maximum:.3g}")
    if any(link.get("pvalue") is not None for link in links):
        text += tr("Dashed edge: P ≥ 0.05. ")
    if any(node["_sized"] for node in data):
        text += tr("Node area: size; open node: zero; dashed open node: missing. ")
    if note:
        text += str(note)
    footer_h = (
        len(wrap_lines(text, canvas.width - 56, canvas.font_sizes["foot"], canvas.font))
        * canvas.font_sizes["foot"]
        * 1.35
        + 14
        if text
        else 0
    )
    rail = min(175, (canvas.width - 56) * 0.18)
    groups = {-1: 0.0, 1: 0.0}
    midx = (min(p[0] for p in xy.values()) + max(p[0] for p in xy.values())) / 2 if layout != "radial" else 0
    for node in data:
        if node["label"]:
            side = 1 if xy[node["id"]][0] >= midx else -1
            groups[side] += (
                len(wrap_lines(node["label"], rail, canvas.font_sizes["label"], canvas.font))
                * canvas.font_sizes["label"]
                * 1.35
                + 7
            )
    fit_h = canvas.height - top - legend_height - footer_h - 60
    plot_h = max(fit_h, 200 + max(0, math.sqrt(n) - 6) * 38 + len(tracks or []) * 48, max(groups.values()) + 24)
    canvas.height = max(canvas.height, top + plot_h + legend_height + footer_h + 60)
    bottom = canvas.height - legend_height - footer_h - 42
    context = render_network_plot(
        canvas, (28, top, canvas.width - 28, bottom), nodes, edges, layout=layout, positions=positions, tracks=tracks
    )
    render_legend(canvas, rows, bottom + 22)
    render_legend(canvas, edge_rows, bottom + 22 + legend_height - edge_legend_h - size_key_h)
    render_size_key(canvas, data, context["node_radii"], bottom + 22 + legend_height - size_key_h)
    if text:
        canvas.text(
            text,
            28,
            bottom + legend_height + 29,
            fs=canvas.font_sizes["foot"],
            color=canvas.pal["ink6"],
            width=canvas.width - 56,
        )
    return canvas.svg("Scientific network with all supplied nodes, associations and aligned annotations")
