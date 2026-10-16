"""Rooted circular phylograms with aligned classification and measurement rings."""

from __future__ import annotations

import math
from xml.sax.saxutils import quoteattr

from ._chart_layout import finite, wrap_lines
from ._network_core import aligned_tracks, node_colors, node_radii, render_label_rails, render_size_key
from ._phylo_core import normalize_tree
from ._polar import PolarGeometry, legend_rows, path, polar_layout, render_legend, render_tracks, stroke
from ._shared import tr


def _tree_tracks(data, tracks, palette):
    raw = []
    if any(node["category"] != "Nodes" for node in data["leaves"]):
        raw.append(
            {
                "name": "Classification",
                "kind": "category",
                "values": {node["id"]: node["category"] for node in data["leaves"]},
            }
        )
    raw.extend(tracks or [])
    return aligned_tracks(raw, data["original_order"], data["leaf_order"], palette)


def render_phylogeny_plot(canvas, bbox, tree, *, leaf_order=None, tracks=None, branch_mode="auto"):
    """Append a true circular rooted tree inside an absolute-coordinate bbox."""
    data = normalize_tree(tree, branch_mode, leaf_order)
    rings = _tree_tracks(data, tracks, canvas.pal)
    x0, y0, x1, y1 = (finite(v, "bbox") for v in bbox)
    if x1 <= x0 or y1 <= y0:
        raise ValueError("bbox requires left < right and top < bottom")
    rail = min(180, (x1 - x0) * 0.18) if any(node["label"] for node in data["nodes"]) else 0
    thickness = 20
    extent = min((x1 - x0) / 2 - rail - 34, (y1 - y0) / 2 - 22)
    radius = extent - len(rings) * (thickness + 4) - (14 if rings else 0)
    if radius < 35:
        raise ValueError("plot bbox is too small for tree topology and annotation tracks")
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    geometry = PolarGeometry(cx, cy, 0, radius, len(data["leaves"]))
    from ._academic_rigor import SharedScale

    scale = SharedScale((0, data["max_distance"] or 1))
    positions = {
        node["id"]: geometry.point(scale.map(node["distance"], 0, radius), node["angle"]) for node in data["nodes"]
    }
    radii = node_radii(data["nodes"], maximum=min(11, max(4, radius / math.sqrt(len(data["leaves"])) * 0.25)))
    colors = {node["id"]: node.get("color", canvas.pal["ink4"]) for node in data["nodes"]}
    colors.update(node_colors(data["leaves"], canvas.pal))
    for node in data["nodes"]:
        r0 = scale.map(node["distance"], 0, radius)
        children = node["children"]
        if len(children) > 1 and r0:
            stroke(
                canvas,
                geometry.arc(r0, children[0]["angle"], children[-1]["angle"]),
                node.get("color", canvas.pal["ink4"]),
                1.15,
                data_role="phylo-clade-arc",
                data_node_id=node["id"],
            )
        for child in children:
            r1 = scale.map(child["distance"], 0, radius)
            stroke(
                canvas,
                path([geometry.point(r0, child["angle"]), geometry.point(r1, child["angle"])]),
                child.get("color", canvas.pal["ink4"]),
                1.35,
                data_role="phylo-branch",
                data_parent=node["id"],
                data_child=child["id"],
                data_length=child.get("branch_length", "unspecified"),
                data_display_length=child["distance"] - node["distance"],
                data_r_start=r0,
                data_r_end=r1,
            )
    outer = render_tracks(canvas, geometry, rings, radius + 14, thickness) if rings else radius
    leaf_ids = set(data["leaf_order"])
    for node in data["leaves"]:
        if scale.map(node["distance"], 0, radius) < radius - 0.01:
            stroke(
                canvas,
                path([positions[node["id"]], geometry.point(radius, node["angle"])]),
                canvas.pal["ink2"],
                0.75,
                stroke_dasharray="2 3",
                data_role="phylo-tip-guide",
                data_node_id=node["id"],
            )
    # Coincident zero-length tips share one glyph while retaining every ID.
    marker_groups = {}
    for node in data["nodes"]:
        if node["id"] not in leaf_ids and not node["_sized"]:
            continue
        point = positions[node["id"]]
        key = tuple(round(v, 7) for v in point)
        marker_groups.setdefault(key, []).append(node)
    for group in marker_groups.values():
        if len(group) > 1 and any(node["_sized"] for node in group):
            raise ValueError("coincident zero-length nodes cannot display separate sizes; omit their size encoding")
        node = group[0]
        x, y = positions[node["id"]]
        r = radii[node["id"]] if node["_sized"] else 2.5
        attrs = f'data-role="phylo-node" data-node-id={quoteattr(node["id"])} data-node-ids={quoteattr(" | ".join(n["id"] for n in group))}'
        if node.get("size") is not None:
            attrs += f' data-size="{node["size"]}"'
        elif node["_sized"]:
            attrs += ' data-size-missing="true" stroke-dasharray="2 1"'
        fill = colors[node["id"]] if r else canvas.pal.get("bg") or "#fff"
        canvas.parts.append(
            f'<circle cx="{x:.4f}" cy="{y:.4f}" r="{r if r else 2.2:.4f}" fill={quoteattr(fill)} stroke={quoteattr(colors[node["id"]])} stroke-width=".8" {attrs}/>'
        )
    items = []
    for node in data["nodes"]:
        point = geometry.point(outer + 5, node["angle"]) if node["id"] in leaf_ids else positions[node["id"]]
        items.append({"id": node["id"], "label": node["label"], "point": point, "radius": 0})
    boxes = render_label_rails(canvas, items, (x0, y0, x1, y1), rail) if rail else []
    return {
        "plot_bbox": tuple(bbox),
        "positions": positions,
        "node_radii": radii,
        "distance_scale": scale,
        "radius": radius,
        "max_distance": data["max_distance"],
        "branch_mode": data["branch_mode"],
        "leaf_order": data["leaf_order"],
        "tracks": rings,
        "protected_labels": boxes,
    }


def make_phylogeny(
    tree,
    *,
    leaf_order=None,
    tracks=None,
    branch_mode="auto",
    title=None,
    subtitle=None,
    figure_label=None,
    note=None,
    width=1100,
    height=850,
    palette=None,
    font_family=None,
):
    """Return a rooted circular phylogram from Newick or a nested tree.

    Nested nodes: ``{id, label?, branch_length?, children?, category?, size?}``.
    Leaves require unique IDs; internal IDs may be omitted. Only explicit labels
    are drawn. Newick leaf names become IDs and labels; quoted names/comments
    are supported. Root length must be omitted or zero. Lengths are finite and
    nonnegative. Auto uses supplied lengths if complete, or unit-edge cladogram
    lengths if none are supplied; partial lengths require an explicit mode.

    Root-to-tip radius preserves cumulative branch length, including unequal
    tips. Dashed guides align tips with annotation rings and do not add length.
    ``leaf_order`` must retain contiguous clades (sibling order may change).
    Leaf categories add a classification ring. Additional tracks use the polar
    heatmap/category/bar/point schema; values are a leaf-ID map or array aligned
    to the original traversal order. Node area maps optional nonnegative size.
    The canvas grows when needed to preserve every explicitly requested label.
    """
    data = normalize_tree(tree, branch_mode, leaf_order)
    track_count = len(tracks or []) + int(any(node["category"] != "Nodes" for node in data["leaves"]))
    n = len(data["leaves"])
    width = max(finite(width, "width", minimum=300), 360 + track_count * 48 + max(0, math.sqrt(n) - 6) * 28)
    canvas = polar_layout(width, height, palette, font_family, n_items=n)
    top = canvas.header(title, subtitle, figure_label)
    rings = _tree_tracks(data, tracks, canvas.pal)
    rows, legend_height = legend_rows(canvas, [], rings)
    size_key_h = 38 if any(node["size"] is not None for node in data["nodes"]) else 0
    legend_height += size_key_h
    explanation = tr("Dashed extensions align tips with rings; they do not contribute branch length.")
    if any(node["_sized"] for node in data["nodes"]):
        explanation += tr(" Node area: size; open node: zero; dashed open node: missing.")
    if note:
        explanation += " " + str(note)
    note_height = (
        len(wrap_lines(explanation, canvas.width - 56, canvas.font_sizes["foot"], canvas.font))
        * canvas.font_sizes["foot"]
        * 1.35
        + 12
    )
    rail = min(180, (canvas.width - 56) * 0.18)
    sides = {-1: 0.0, 1: 0.0}
    leaves = set(data["leaf_order"])
    for node in data["nodes"]:
        if node["label"]:
            at_center = node["id"] not in leaves and node["distance"] == 0
            side = 1 if math.cos(node["angle"]) >= 0 or at_center else -1
            sides[side] += (
                len(wrap_lines(node["label"], rail, canvas.font_sizes["label"], canvas.font))
                * canvas.font_sizes["label"]
                * 1.35
                + 7
            )
    rail = min(180, (canvas.width - 56) * 0.18)
    ring_room = track_count * 24 + (14 if track_count else 0)
    radius_floor = 35 + ring_room + max(0, math.sqrt(n) - 3) * 20
    if canvas.width - 56 < 2 * (rail + 34 + radius_floor):
        canvas.width = 56 + 2 * (rail + 34 + radius_floor)
    plot_height = max(2 * (radius_floor + 22), max(sides.values()) + 20)
    canvas.height = max(canvas.height, top + plot_height + legend_height + note_height + 72)
    bottom = canvas.height - legend_height - note_height - 66
    context = render_phylogeny_plot(
        canvas,
        (28, top, canvas.width - 28, bottom),
        tree,
        leaf_order=leaf_order,
        tracks=tracks,
        branch_mode=branch_mode,
    )
    length = context["max_distance"] / 5 or context["max_distance"]
    if length:
        exponent = 10 ** math.floor(math.log10(length))
        if exponent:
            length = max(1, math.floor(length / exponent)) * exponent
        pixels = context["distance_scale"].map(length, 0, context["radius"])
        stroke(
            canvas,
            path([(28, bottom + 20), (28 + pixels, bottom + 20)]),
            canvas.ink,
            1.4,
            data_role="branch-scale",
            data_length=length,
        )
        for x in (28, 28 + pixels):
            stroke(canvas, path([(x, bottom + 16), (x, bottom + 24)]), canvas.ink, 1.2)
        units = tr("branch length") if context["branch_mode"] == "length" else tr("edges (cladogram)")
        canvas.text(
            f"{length:.4g} {units}",
            28 + pixels + 12,
            bottom + 13,
            fs=canvas.font_sizes["foot"],
            color=canvas.pal["ink6"],
        )
    render_legend(canvas, rows, bottom + 40)
    render_size_key(canvas, data["nodes"], context["node_radii"], bottom + 40 + legend_height - size_key_h)
    canvas.text(
        explanation,
        28,
        bottom + 44 + legend_height,
        fs=canvas.font_sizes["foot"],
        color=canvas.pal["ink6"],
        width=canvas.width - 56,
    )
    return canvas.svg("Rooted circular phylogeny with true topology, branch lengths and aligned leaf annotations")
