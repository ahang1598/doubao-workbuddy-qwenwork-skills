"""Text-sized nodes and collision-aware label placement; no styling decisions."""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET

from ..atomize_svg_to_slide._geometry import fmt
from ._geometry import Box, Geometry, _finite, _union, label
from ._help import _drawing_api
from ._text import wrap_label


_SHAPES = ("rect", "pill", "ellipse")


@_drawing_api(
    "shapes",
    purpose="按文字测量自动确定节点框大小，生成带文字的节点几何。",
    returns="Geometry",
    semantics=(
        "先按 max_width 换行（省略则单行），再按文字边界加 padding 得到框尺寸；min_width/min_height 可保证同组节点不小于某尺寸。",
        "shape 为 rect/pill/ellipse；rect 用 rx 圆角，pill 为全圆角，ellipse 的半轴按文字框外接椭圆放大。",
        "fill/stroke 等框样式通过 box_style 传入，文字样式通过 **text_style 传入（如 fill、font_weight）。",
        "局部原点为框左上角；端口 center/top/bottom/left/right 位于框边中点，可直接用于 node.port 连线。",
    ),
    example="node_geo = text_box(text, font_size=size, max_width=width, padding=(12, 8),\n"
    "                    box_style=dict(fill=fill, stroke=stroke), fill=text_color)\n"
    'node = drawing.add(name, node_geo, at=position, own_anchor="center")',
    limits=("不缩小字号、不截断文字；单个字符组超过 max_width 时报错。",),
    rank=8,
)
def text_box(
    content,
    *,
    font_size,
    max_width=None,
    padding=(12, 8),
    shape="rect",
    rx=8,
    min_width=0,
    min_height=0,
    font_family=None,
    line_height=None,
    box_style=None,
    **text_style,
):
    if shape not in _SHAPES:
        raise ValueError(f"shape must be one of {_SHAPES}")
    try:
        pad_x, pad_y = padding
    except TypeError:
        pad_x = pad_y = padding
    _finite(pad_x, pad_y, rx, min_width, min_height)
    if min(pad_x, pad_y, rx, min_width, min_height) < 0:
        raise ValueError("padding, rx and minimum sizes cannot be negative")
    style = {k: v for k, v in text_style.items() if k not in ("text_anchor", "text-anchor")}
    if max_width is None:
        text = label(
            content,
            font_size=font_size,
            font_family=font_family,
            line_height=line_height,
            text_anchor="middle",
            **style,
        )
    else:
        text = wrap_label(
            content,
            max_width=max_width,
            font_size=font_size,
            font_family=font_family,
            line_height=line_height,
            text_anchor="middle",
            **style,
        )
    tb = text.bounds
    width = max(min_width, tb.width + 2 * pad_x)
    height = max(min_height, tb.height + 2 * pad_y)
    if shape == "ellipse":
        # Inscribe the padded text box: an ellipse through its corners has semi-axes sqrt(2)x.
        width, height = max(min_width, width * math.sqrt(2)), max(min_height, height * math.sqrt(2))
    paint = {"fill": "none"} | dict(box_style or {})
    from ._geometry import ellipse, rect

    if shape == "ellipse":
        frame = ellipse(width / 2, height / 2, cx=width / 2, cy=height / 2, **paint)
    else:
        radius = height / 2 if shape == "pill" else min(rx, width / 2, height / 2)
        frame = rect(width, height, rx=radius, **paint)
    dx = width / 2 - (tb.x + tb.width / 2)
    dy = height / 2 - (tb.y + tb.height / 2)
    holder = ET.Element("g")
    holder.append(frame.element)
    for line in text.element:
        node = ET.SubElement(holder, line.tag, dict(line.attrib))
        node.text = line.text
        node.set("x", fmt(float(line.get("x", "0")) + dx))
        node.set("y", fmt(float(line.get("y", "0")) + dy))
    bounds = _union([frame.bounds, Box(tb.x + dx, tb.y + dy, tb.width, tb.height)])
    ports = {
        "center": (width / 2, height / 2),
        "top": (width / 2, 0),
        "bottom": (width / 2, height),
        "left": (0, height / 2),
        "right": (width, height / 2),
    }
    directions = {"top": (0, -1), "bottom": (0, 1), "left": (-1, 0), "right": (1, 0)}
    return Geometry(holder, bounds, ports, directions, {k: (-v[1], v[0]) for k, v in directions.items()})


def _box_overlap(a, b):
    w = min(a.x + a.width, b.x + b.width) - max(a.x, b.x)
    h = min(a.y + a.height, b.y + b.height) - max(a.y, b.y)
    return w * h if w > 0 and h > 0 else 0.0


def _segment_box_hits(p, q, box):
    from ._routing import crosses

    return crosses(p, q, box)


def _outline(node, layout):
    """Canvas polyline of a node's single contour, or None for multi-part/text nodes."""
    try:
        curve = node.geometry.contour(0, tolerance=1.0)
    except (ValueError, TypeError):
        return None
    from ._geometry import _flatten

    points, _ = _flatten(curve.d, curve.tolerance)
    matrix = layout.matrix(node)
    pts = [matrix.point(*q) for q in points]
    return list(zip(pts, pts[1:]))


def _obstacles(drawing, layout, avoid, exclude=()):
    """Boxes to keep clear, plus segments not to cross."""
    from ._scene import Connector, Node

    boxes, segments = [], []

    def add_node(node):
        box = layout.bounds(node)
        if box.width * box.height > drawing.width * drawing.height * 0.08:
            outline = _outline(node, layout)
            if outline is not None:
                segments.extend(outline)
                return
        boxes.append(box)

    if avoid is None:
        for key, item in drawing.items:
            if key in exclude:
                continue
            if isinstance(item, Node):
                add_node(item)
            elif isinstance(item, Connector):
                segments.extend(_connector_segments(item, layout))
        return boxes, segments
    for obstacle in avoid:
        if isinstance(obstacle, Node):
            if obstacle.drawing is not drawing:
                raise ValueError("Obstacle belongs to another drawing")
            add_node(obstacle)
        elif isinstance(obstacle, Box):
            boxes.append(obstacle)
        else:
            raise TypeError("avoid items must be Box or Node")
    return boxes, segments


def _connector_points(connector, layout):
    from ._geometry import _flatten

    d = connector.element(layout).get("d")
    points, _ = _flatten(d, 0.5)
    return list(points)


def _connector_segments(connector, layout):
    points = _connector_points(connector, layout)
    return list(zip(points, points[1:]))


def _score(box, boxes, segments, canvas):
    w, h = canvas
    visible = max(0, min(box.x + box.width, w) - max(0, box.x)) * max(0, min(box.y + box.height, h) - max(0, box.y))
    outside = max(0.0, box.width * box.height - visible)
    if outside < 1e-6:
        outside = 0.0
    overlap = sum(_box_overlap(box, b) for b in boxes)
    if overlap < 1e-6:
        overlap = 0.0
    hits = sum(1 for p, q in segments if _segment_box_hits(p, q, box))
    return outside * 4 + overlap + hits * box.width * box.height * 0.5, overlap, hits, outside


def _owner(target):
    from ._scene import Anchor, ContourAnchor, Edge

    return target.node.key if isinstance(target, (Anchor, ContourAnchor, Edge)) else None


def _along(points, fraction):
    """Point at `fraction` of the polyline's length and the unit left normal there."""
    lengths = [0.0]
    for p, q in zip(points, points[1:]):
        lengths.append(lengths[-1] + math.dist(p, q))
    if lengths[-1] <= 0:
        raise ValueError("Connector has no length")
    target = fraction * lengths[-1]
    i = max(0, min(len(points) - 2, next(j for j in range(len(lengths) - 1) if lengths[j + 1] >= target)))
    p, q = points[i], points[i + 1]
    seg = math.dist(p, q) or 1
    t = (target - lengths[i]) / seg
    return p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t, -(q[1] - p[1]) / seg, (q[0] - p[0]) / seg


_SCREEN = {"above": (0, -1), "top": (0, -1), "below": (0, 1), "bottom": (0, 1), "left": (-1, 0), "right": (1, 0)}


def edge_label_center(anchor, layout):
    """Live centre of an edge label: beside the line's midpoint, clear of the stroke by `gap`."""
    points = _connector_points(anchor.connector, layout)
    mx, my, nx, ny = _along(points, anchor.fraction)
    sign = anchor.side
    if isinstance(sign, str):
        vx, vy = _SCREEN[sign]
        sign = -1 if nx * vx + ny * vy < -1e-9 else 1
    w, h = anchor.size
    offset = anchor.gap + abs(nx) * w / 2 + abs(ny) * h / 2
    cx, cy = mx + sign * nx * offset, my + sign * ny * offset
    if len(points) == 2:
        (x1, y1), (x2, y2) = points
        dx, dy = abs(x2 - x1), abs(y2 - y1)
        if min(dx, dy) >= 6:
            if dy <= dx:
                out = (min(y1, y2) - anchor.gap - h / 2) if sign * ny < 0 else (max(y1, y2) + anchor.gap + h / 2)
                if abs(out - my) - h / 2 <= max(3 * h, 36):
                    cx, cy = mx, out
            else:
                out = (min(x1, x2) - anchor.gap - w / 2) if sign * nx < 0 else (max(x1, x2) + anchor.gap + w / 2)
                if abs(out - mx) - w / 2 <= max(3 * h, 36):
                    cx, cy = out, my
    return cx, cy


def edge_label_anchor(drawing, connector, geometry, side, gap=4.0, fraction=0.5):
    """EdgeLabelAnchor for `connector`: the clearest of a few spots near the middle (both sides unless `side`"""
    from ._scene import EdgeLabelAnchor, Node, _Layout

    size = (geometry.bounds.width, geometry.bounds.height)
    if side is not None and side not in _SCREEN:
        raise ValueError(f"label_side must be one of {sorted(_SCREEN)} (or omit it to pick the clearer side)")
    layout = _Layout(drawing)
    key = next(k for k, v in drawing.items if v is connector)
    boxes, segments = _obstacles(drawing, layout, None, exclude=(key,))
    segments += _connector_segments(connector, layout)
    frames = [layout.bounds(n) for n in drawing.nodes.values() if isinstance(n, Node)]
    best = None
    for rank, f in enumerate((fraction, 0.4, 0.6, 0.3, 0.7)):
        for sign in (side,) if side is not None else (1, -1):
            cx, cy = edge_label_center(EdgeLabelAnchor(connector, f, sign, gap, size), layout)
            box = Box(cx - size[0] / 2, cy - size[1] / 2, *size)
            score = _score(box, boxes, segments, (drawing.width, drawing.height))[0]
            score += sum(
                _box_overlap(box, b)
                for b in frames
                if not (
                    b.x <= box.x
                    and b.y <= box.y
                    and box.x + box.width <= b.x + b.width
                    and box.y + box.height <= b.y + b.height
                )
            )
            if best is None or (score, rank) < best[:2]:
                best = (score, rank, f, sign)
        if best[0] == 0:
            break
    return EdgeLabelAnchor(connector, best[2], best[3], gap, size)


def place_label(drawing, key, geometry, target, avoid, gap, sides):
    from ._scene import Anchor, ContourAnchor, _Layout

    if not isinstance(geometry, Geometry):
        raise TypeError("label geometry must be Geometry")
    _finite(gap)
    layout = _Layout(drawing)
    x, y = layout.point(target)
    w, h = geometry.bounds.width, geometry.bounds.height
    owner = _owner(target)
    boxes, segments = _obstacles(drawing, layout, avoid, exclude=(owner,) if owner else ())
    base = {
        "right": (gap, -h / 2),
        "left": (-gap - w, -h / 2),
        "top": (-w / 2, -gap - h),
        "bottom": (-w / 2, gap),
        "top_right": (gap, -gap - h),
        "bottom_right": (gap, gap),
        "top_left": (-gap - w, -gap - h),
        "bottom_left": (-gap - w, gap),
    }
    order = list(sides) if sides else list(base)
    for side in order:
        if side not in base:
            raise ValueError(f"Unknown label side {side!r}")
    owner_box = layout.bounds(drawing.nodes[owner]) if owner else None
    # Slide each side's candidate along its edge and outward in small steps, so a
    # crowded preferred side can still find a clear spot before falling back.
    steps = (0, 1, -1, 2, -2, 3)
    unit = max(h, 8.0)
    best = None
    for rank, side in enumerate(order):
        dx0, dy0 = base[side]
        horizontal = side in ("left", "right")
        for distance, step in enumerate(steps):
            for push in (0, 1, 2):
                dx = (
                    dx0
                    + (0 if horizontal else step * w / 3)
                    + (push * unit * (1 if "right" in side else -1 if "left" in side else 0))
                )
                dy = (
                    dy0
                    + (step * unit if horizontal else 0)
                    + (push * unit * (1 if "bottom" in side else -1 if "top" in side else 0))
                )
                box = Box(x + dx, y + dy, w, h)
                score = _score(box, boxes, segments, (drawing.width, drawing.height))
                if owner_box is not None:
                    covered = _box_overlap(box, owner_box)
                    score = (score[0] + covered, score[1] + covered, score[2], score[3])
                candidate = (score[0], rank, distance + push, side, dx, dy, score)
                if best is None or candidate[:3] < best[:3]:
                    best = candidate
            if best[0] == 0 and best[1] == rank:
                break
        if best[0] == 0:
            break
    _, _, _, side, dx, dy, score = best
    at = target.shifted(dx, dy) if isinstance(target, (Anchor, ContourAnchor)) else (x + dx, y + dy)
    node = drawing.add(key, geometry, at=at, own_anchor="top_left")
    node.placement = {
        "side": side,
        "overlap_area": score[1],
        "line_hits": score[2],
        "outside_area": score[3],
        "clear": score[0] == 0,
    }
    return node


def label_connector(drawing, key, connector_key, geometry, avoid, gap, position):
    from ._scene import Connector, _Layout

    item = dict(drawing.items).get(connector_key)
    if not isinstance(item, Connector):
        raise ValueError(f"{connector_key!r} is not a connector in this drawing")
    if not isinstance(geometry, Geometry):
        raise TypeError("label geometry must be Geometry")
    _finite(gap)
    layout = _Layout(drawing)
    points = _connector_points(item, layout)
    lengths = [0.0]
    for p, q in zip(points, points[1:]):
        lengths.append(lengths[-1] + math.dist(p, q))
    total = lengths[-1]
    if total <= 0:
        raise ValueError("Connector has no length")
    w, h = geometry.bounds.width, geometry.bounds.height
    boxes, segments = _obstacles(drawing, layout, avoid, exclude=(connector_key,))
    own = list(zip(points, points[1:]))
    fractions = [position] if position is not None else [0.5, 0.4, 0.6, 0.3, 0.7, 0.2, 0.8]
    best = None
    for rank, fraction in enumerate(fractions):
        if not 0 <= fraction <= 1:
            raise ValueError("position must be between 0 and 1")
        target = fraction * total
        i = max(0, min(len(points) - 2, next(j for j in range(len(lengths) - 1) if lengths[j + 1] >= target)))
        p, q = points[i], points[i + 1]
        seg = math.dist(p, q) or 1
        t = (target - lengths[i]) / seg
        mx, my = p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t
        nx, ny = -(q[1] - p[1]) / seg, (q[0] - p[0]) / seg
        for side_rank, sign in enumerate((1, -1)):
            for push in (0, 1, 2):
                offset = gap + push * max(h, 8.0) + abs(nx) * w / 2 + abs(ny) * h / 2
                cx = mx + sign * nx * offset
                cy = my + sign * ny * offset
                box = Box(cx - w / 2, cy - h / 2, w, h)
                score = _score(box, boxes, segments + own, (drawing.width, drawing.height))
                candidate = (score[0], rank + push, side_rank, box, score)
                if best is None or candidate[:3] < best[:3]:
                    best = candidate
        if best[0] == 0:
            break
    _, _, _, box, score = best
    node = drawing.add(key, geometry, at=(box.x, box.y), own_anchor="top_left")
    node.placement = {"overlap_area": score[1], "line_hits": score[2], "outside_area": score[3], "clear": score[0] == 0}
    return node
