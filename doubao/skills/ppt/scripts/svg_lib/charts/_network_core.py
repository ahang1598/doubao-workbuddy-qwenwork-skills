"""Deterministic scientific graph layout and shared ID-aligned label rails."""

from __future__ import annotations

import math
from collections import defaultdict
from xml.sax.saxutils import quoteattr

from ._academic_rigor import SeriesContext
from ._chart_layout import finite, wrap_lines
from ._polar import normalize_tracks, path, stroke


def normalize_network(nodes, edges):
    """Preserve every supplied node/edge; IDs and displayed labels are separate."""
    data, seen = [], set()
    for raw in nodes:
        if not isinstance(raw, dict) or "id" not in raw:
            raise ValueError("nodes require dictionaries with an id")
        node = dict(raw)
        if not isinstance(node["id"], str) or not node["id"] or node["id"] in seen:
            raise ValueError("node ids must be unique nonempty strings")
        seen.add(node["id"])
        node["label"] = str(node["label"]) if node.get("label") is not None else None
        node["category"] = str(node.get("category", "Nodes"))
        node["size"] = finite(node["size"], "node size", minimum=0) if node.get("size") is not None else None
        node["_sized"] = "size" in raw
        data.append(node)
    if not data:
        raise ValueError("provide at least one node")
    links = []
    for raw in edges:
        if not isinstance(raw, dict):
            raise TypeError("edges must be dictionaries")
        edge = dict(raw)
        if edge.get("source") not in seen or edge.get("target") not in seen:
            raise ValueError("every edge endpoint must name an existing node id")
        for key in ("weight", "correlation", "pvalue"):
            if edge.get(key) is not None:
                edge[key] = finite(edge[key], key)
        if edge.get("correlation") is not None and not -1 <= edge["correlation"] <= 1:
            raise ValueError("correlation must be inside [-1, 1]")
        if edge.get("pvalue") is not None and not 0 <= edge["pvalue"] <= 1:
            raise ValueError("pvalue must be inside [0, 1]")
        edge["_magnitude"] = abs(edge.get("weight") if edge.get("weight") is not None else edge.get("correlation") or 0)
        edge["_weighted"] = edge.get("weight") is not None or edge.get("correlation") is not None
        edge["_sign"] = edge.get("correlation") if edge.get("correlation") is not None else edge.get("weight")
        links.append(edge)
    return data, links


def aligned_tracks(tracks, original_ids, ordered_ids, palette):
    """Accept ID maps or arrays in original input order, never positional guessing."""
    original = list(original_ids)
    raw = []
    for track in tracks or []:
        item = dict(track)
        values = item.get("values")
        if isinstance(values, dict):
            if set(values) - set(original):
                raise ValueError("track values contain unknown ids")
            item["values"] = [values.get(key) for key in original]
        if item.get("kind") == "category" and item.get("values") is not None:
            keys = list(dict.fromkeys(str(v) for v in item["values"] if v is not None))
            context = SeriesContext(keys, pal=palette)
            item["colors"] = {key: context.color_of(key) for key in keys} | item.get("colors", {})
        raw.append(item)
    return normalize_tracks(raw, [original.index(key) for key in ordered_ids], palette)


def node_colors(nodes, palette):
    categories = list(dict.fromkeys(node["category"] for node in nodes))
    context = SeriesContext(categories, pal=palette)
    return {node["id"]: node.get("color", context.color_of(node["category"])) for node in nodes}


def node_radii(nodes, maximum=13):
    limit = max((node["size"] for node in nodes if node.get("size") is not None), default=0)
    return {
        node["id"]: maximum * math.sqrt(node["size"] / limit)
        if node.get("size") is not None and limit
        else 0.0
        if node.get("_sized")
        else 5.5
        for node in nodes
    }


def render_size_key(canvas, nodes, radii, top, left=28):
    """Draw numerical area references using the same radii as graph/tree nodes."""
    sized = [node for node in nodes if node.get("size") is not None]
    if not sized:
        return
    limit = max(node["size"] for node in sized)
    maximum = max(radii[node["id"]] for node in sized)
    canvas.text("Node size", left, top + 8, fs=canvas.font_sizes["foot"], color=canvas.pal["ink6"])
    x = left + canvas.measure("Node size", canvas.font_sizes["foot"]) + 24
    for value in [limit / 4, limit / 2, limit] if limit else [0]:
        radius = maximum * math.sqrt(value / limit) if limit else 2.2
        color = canvas.pal["ink4"]
        fill = color if limit else canvas.pal.get("bg") or "#fff"
        canvas.parts.append(
            f'<circle cx="{x + maximum:.4f}" cy="{top + 14:.4f}" r="{radius:.4f}" fill={quoteattr(fill)} stroke={quoteattr(color)} stroke-width=".8" data-role="node-size-key" data-size="{value}"/>'
        )
        label = f"{value:.3g}"
        canvas.text(label, x + maximum * 2 + 9, top + 8, fs=canvas.font_sizes["foot"], color=canvas.pal["ink6"])
        x += maximum * 2 + 28 + canvas.measure(label, canvas.font_sizes["foot"])


def force_positions(nodes, edges):
    """Fruchterman–Reingold with deterministic starts and absolute edge strengths."""
    ordered = sorted(nodes, key=lambda node: (node["category"], node["id"]))
    n = len(ordered)
    index = {node["id"]: i for i, node in enumerate(ordered)}
    xy = [[0.8 * math.cos(math.tau * i / n), 0.8 * math.sin(math.tau * i / n)] for i in range(n)]
    if n == 1:
        return {ordered[0]["id"]: (0.0, 0.0)}
    k = math.sqrt(3.0 / n)
    largest = max((edge["_magnitude"] for edge in edges), default=1) or 1
    for iteration in range(180):
        delta = [[-p[0] * 0.10, -p[1] * 0.10] for p in xy]
        for i in range(n):
            for j in range(i):
                dx, dy = xy[i][0] - xy[j][0], xy[i][1] - xy[j][1]
                distance = max(1e-8, math.hypot(dx, dy))
                force = k * k / (distance * distance)
                for axis, diff in enumerate((dx, dy)):
                    delta[i][axis] += diff * force
                    delta[j][axis] -= diff * force
        for edge in edges:
            i, j = index[edge["source"]], index[edge["target"]]
            if i == j:
                continue
            dx, dy = xy[i][0] - xy[j][0], xy[i][1] - xy[j][1]
            distance = math.hypot(dx, dy)
            weight = 0.25 + 0.75 * edge["_magnitude"] / largest if edge["_weighted"] else 1.0
            force = distance / k * weight
            for axis, diff in enumerate((dx, dy)):
                delta[i][axis] -= diff * force
                delta[j][axis] += diff * force
        temperature = 0.12 * (1 - iteration / 180) + 0.001
        for i in range(n):
            norm = math.hypot(*delta[i]) or 1
            for axis in range(2):
                xy[i][axis] += delta[i][axis] / norm * min(norm, temperature)
    return {node["id"]: tuple(xy[i]) for i, node in enumerate(ordered)}


def graph_positions(nodes, edges, mode, supplied=None):
    if mode not in {"force", "radial", "bipartite"}:
        raise ValueError("layout must be force, radial or bipartite")
    if mode == "bipartite":
        if any(node.get("side") not in {"left", "right"} for node in nodes):
            raise ValueError("bipartite nodes require side='left' or 'right'")
        sides = {node["id"]: node["side"] for node in nodes}
        if any(sides[e["source"]] == sides[e["target"]] for e in edges):
            raise ValueError("bipartite edges must connect opposite sides")
    if supplied is not None:
        if mode == "radial":
            raise ValueError("radial angles come from outer node order; positions are for force/bipartite")
        if not isinstance(supplied, dict) or set(supplied) != {n["id"] for n in nodes}:
            raise ValueError("positions must map every node id to [x, y]")
        xy = {}
        for key, pair in supplied.items():
            if len(pair) != 2:
                raise ValueError("positions require [x, y] pairs")
            xy[key] = tuple(finite(v, "position") for v in pair)
        if len(set(xy.values())) != len(xy):
            raise ValueError("coincident node positions cannot distinguish nodes; supply distinct coordinates")
        return xy
    if mode == "force":
        return force_positions(nodes, edges)
    if mode == "bipartite":
        result = {}
        for side in ("left", "right"):
            group = [node for node in nodes if node["side"] == side]
            for i, node in enumerate(group):
                result[node["id"]] = (-1 if side == "left" else 1, 2 * (i + 0.5) / len(group) - 1)
        return result
    if any(node.get("side", "outer") not in {"inner", "outer"} for node in nodes):
        raise ValueError("radial nodes use side='inner' or 'outer'")
    result = {}
    for side, radius in (("outer", 1.0), ("inner", 0.32)):
        group = [node for node in nodes if node.get("side", "outer") == side]
        for i, node in enumerate(group):
            angle = -math.pi / 2 + (i + 0.5) * math.tau / len(group)
            r = 0 if len(group) == 1 and side == "inner" else radius
            result[node["id"]] = (r * math.cos(angle), r * math.sin(angle))
    return result


def fit_positions(positions, bbox):
    x0, y0, x1, y1 = bbox
    xs, ys = zip(*positions.values())
    dx, dy = max(xs) - min(xs), max(ys) - min(ys)
    if not math.isfinite(dx) or not math.isfinite(dy):
        magnitude = max(abs(v) for point in positions.values() for v in point)
        return fit_positions({key: (x / magnitude, y / magnitude) for key, (x, y) in positions.items()}, bbox)
    unit = max(dx, dy)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    minimum_x, minimum_y = min(xs), min(ys)
    if not unit:
        return {key: (cx, cy) for key in positions}
    relative_x, relative_y = dx / unit, dy / unit
    pixels = min((x1 - x0) / relative_x if relative_x else math.inf, (y1 - y0) / relative_y if relative_y else math.inf)
    return {
        key: (
            cx + ((x - minimum_x) / unit - relative_x / 2) * pixels,
            cy + ((y - minimum_y) / unit - relative_y / 2) * pixels,
        )
        for key, (x, y) in positions.items()
    }


def separate_nodes(positions, radii, bbox):
    """Resolve node collisions in a force layout without dropping graph members."""
    x0, y0, x1, y1 = bbox
    keys = sorted(positions)
    points = {key: list(positions[key]) for key in keys}
    for _ in range(240):
        largest = 0.0
        for i, a in enumerate(keys):
            for b in keys[:i]:
                dx, dy = points[a][0] - points[b][0], points[a][1] - points[b][1]
                distance = math.hypot(dx, dy)
                desired = max(2.2, radii[a]) + max(2.2, radii[b]) + 4
                overlap = desired - distance
                if overlap <= 0:
                    continue
                largest = max(largest, overlap)
                if distance < 1e-9:
                    dx, dy, distance = math.cos(i * 2.4), math.sin(i * 2.4), 1.0
                for axis, delta in enumerate((dx, dy)):
                    shift = delta / distance * overlap * 0.51
                    points[a][axis] += shift
                    points[b][axis] -= shift
        for key in keys:
            points[key][0] = min(x1, max(x0, points[key][0]))
            points[key][1] = min(y1, max(y0, points[key][1]))
        if largest < 0.01:
            return {key: tuple(point) for key, point in points.items()}
    raise ValueError("node sizes cannot fit inside this plot bbox; increase width and height")


def label_height(canvas, nodes, rail_width):
    heights = [
        len(wrap_lines(node["label"], rail_width, canvas.font_sizes["label"], canvas.font))
        * canvas.font_sizes["label"]
        * 1.35
        + 7
        for node in nodes
        if node.get("label")
    ]
    return max(0, sum(sorted(heights, reverse=True)[: math.ceil(len(heights) / 2) + 1]))


def render_label_rails(canvas, items, bbox, rail_width):
    """Use measured rows; this plot-only function never changes its bounding box."""
    x0, y0, x1, y1 = bbox
    cx = (x0 + x1) / 2
    groups = {-1: [], 1: []}
    for item in items:
        if not item.get("label"):
            continue
        row = dict(item)
        row["height"] = (
            len(wrap_lines(row["label"], rail_width, canvas.font_sizes["label"], canvas.font))
            * canvas.font_sizes["label"]
            * 1.35
        )
        side = row.get("side") or (1 if row["point"][0] >= cx else -1)
        groups[side].append(row)
    protected = []
    for side, rows in groups.items():
        rows.sort(key=lambda row: (row["point"][1], row["id"]))
        needed = sum(row["height"] + 7 for row in rows) - 7
        if needed > y1 - y0 + 0.01:
            raise ValueError("plot bbox is too short for requested labels; increase its height")
        used = y0
        for row in rows:
            row["top"] = max(used, row["point"][1] - row["height"] / 2)
            used = row["top"] + row["height"] + 7
        ceiling = y1
        for row in reversed(rows):
            row["top"] = min(row["top"], ceiling - row["height"])
            ceiling = row["top"] - 7
        for row in rows:
            tx = x0 if side < 0 else x1
            edge = x0 + rail_width + 8 if side < 0 else x1 - rail_width - 8
            px, py = row["point"]
            gap = row.get("radius", 0) + 3
            start = (px + side * gap, py)
            end = (edge, row["top"] + row["height"] / 2)
            elbow = edge - side * 12
            stroke(canvas, path([start, (elbow, py), end]), canvas.pal["ink2"], 0.7, data_role="label-leader")
            canvas.text(
                row["label"],
                tx,
                row["top"],
                fs=canvas.font_sizes["label"],
                width=rail_width,
                anchor="start" if side < 0 else "end",
            )
            protected.append(
                (
                    tx if side < 0 else tx - rail_width,
                    row["top"],
                    tx + rail_width if side < 0 else tx,
                    row["top"] + row["height"],
                )
            )
    return protected


def render_edges(canvas, edges, positions, radii):
    maximum = max((edge["_magnitude"] for edge in edges), default=1) or 1
    counts, ranks = defaultdict(int), defaultdict(int)
    for edge in edges:
        counts[tuple(sorted((edge["source"], edge["target"])))] += 1
    for i, edge in enumerate(edges):
        source, target = edge["source"], edge["target"]
        key = tuple(sorted((source, target)))
        rank = ranks[key]
        ranks[key] += 1
        a, b = positions[source], positions[target]
        signed = edge["_sign"]
        color = (
            canvas.pal["ink4"]
            if signed is None or signed == 0
            else canvas.pal["accent"]
            if signed > 0
            else canvas.pal["secondary"]
        )
        color = edge.get("color", color)
        width = 0.7 + 3.5 * edge["_magnitude"] / maximum if edge["_weighted"] else 1.4
        p = edge.get("pvalue")
        attrs = {
            "data_role": "network-edge",
            "data_edge_index": i,
            "data_source": source,
            "data_target": target,
            "stroke_opacity": 0.8 if p is None or p < 0.05 else 0.42,
        }
        for field in ("weight", "correlation", "pvalue"):
            if edge.get(field) is not None:
                attrs["data_" + field] = edge[field]
        if p is not None and p >= 0.05:
            attrs["stroke_dasharray"] = "4 3"
        if source == target:
            r = max(6, radii[source]) + 10 + rank * 9
            x, y = a
            d = f"M{x:.4f},{y:.4f} C{x + r * 2:.4f},{y - r * 2:.4f} {x - r * 2:.4f},{y - r * 2:.4f} {x:.4f},{y:.4f}"
        else:
            dx, dy = b[0] - a[0], b[1] - a[1]
            length = math.hypot(dx, dy) or 1
            start = (a[0] + dx / length * radii[source], a[1] + dy / length * radii[source])
            end = (b[0] - dx / length * radii[target], b[1] - dy / length * radii[target])
            offset = (rank - (counts[key] - 1) / 2) * 16
            if source != key[0]:
                offset = -offset
            control = ((a[0] + b[0]) / 2 - dy / length * offset, (a[1] + b[1]) / 2 + dx / length * offset)
            d = f"M{start[0]:.4f},{start[1]:.4f} Q{control[0]:.4f},{control[1]:.4f} {end[0]:.4f},{end[1]:.4f}"
        stroke(canvas, d, color, width, **attrs)


def render_nodes(canvas, nodes, positions, radii, colors, role="network-node"):
    for node in nodes:
        x, y = positions[node["id"]]
        radius = radii[node["id"]]
        fill = colors[node["id"]] if radius > 0 else canvas.pal.get("bg") or "#fff"
        attrs = f'data-role="{role}" data-node-id={quoteattr(node["id"])} data-category={quoteattr(node["category"])}'
        if node.get("size") is not None:
            attrs += f' data-size="{node["size"]}"'
        elif node.get("_sized"):
            attrs += ' data-size-missing="true" stroke-dasharray="2 1"'
        canvas.parts.append(
            f'<circle cx="{x:.4f}" cy="{y:.4f}" r="{radius if radius else 2.2:.4f}" fill={quoteattr(fill)} stroke={quoteattr(colors[node["id"]])} stroke-width="1.3" {attrs}/>'
        )
