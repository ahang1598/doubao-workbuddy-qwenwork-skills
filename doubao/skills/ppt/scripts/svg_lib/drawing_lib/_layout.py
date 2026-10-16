"""Layout helpers that return placements; the author keeps composition decisions."""

from __future__ import annotations

from collections.abc import Hashable, Mapping, Sequence
from dataclasses import dataclass
import math
from types import MappingProxyType

from ..atomize_svg_to_slide._geometry import fmt
from ._geometry import Box, Geometry, Point, _finite, _point
from ._help import _drawing_api


def _size(value, name):
    if isinstance(value, Geometry):
        value = value.bounds
    if isinstance(value, Box):
        w, h = value.width, value.height
    else:
        try:
            w, h = value
        except (TypeError, ValueError) as exc:
            raise TypeError(f"{name} must be (width, height), Box or Geometry") from exc
    _finite(w, h)
    if w < 0 or h < 0:
        raise ValueError(f"{name} dimensions cannot be negative")
    return float(w), float(h)


def _gap(value, name="gap"):
    _finite(value)
    if value < 0:
        raise ValueError(f"{name} cannot be negative")
    return float(value)


def _items(sizes):
    if isinstance(sizes, Mapping):
        items = list(sizes.items())
    elif isinstance(sizes, Sequence) and not isinstance(sizes, (str, bytes)):
        items = list(enumerate(sizes))
    else:
        raise TypeError("sizes must be a mapping or an ordered sequence")
    if not items:
        raise ValueError("Layout needs at least one item")
    return [(key, _size(value, f"size of {key!r}")) for key, value in items]


def _align_offset(slot, extent, align):
    if align in ("start", "top", "left"):
        return 0.0
    if align in ("center", "middle"):
        return (slot - extent) / 2
    if align in ("end", "bottom", "right"):
        return slot - extent
    raise ValueError(f"Unknown alignment {align!r}")


@_drawing_api(
    "layout",
    purpose="保存一组对象的排布结果。",
    returns="Placement 快照",
    semantics=(
        "boxes 是 key→Box 的只读映射，使用画布坐标；bounds 为全部占位的外接框。",
        '放置时用 drawing.add(key, geometry, at=placement.at(key), own_anchor="top_left")。',
    ),
    example="placement = row(sizes, gap=gap, origin=(x, y))\n"
    "for key, part in parts.items():\n"
    '    drawing.add(key, part, at=placement.at(key), own_anchor="top_left")',
    common=False,
)
@dataclass(frozen=True)
class Placement:
    boxes: Mapping[Hashable, Box]
    bounds: Box

    def at(self, key, anchor="top_left"):
        return self.boxes[key].anchor(anchor)


def _placement(boxes):
    from ._geometry import _union

    return Placement(MappingProxyType(dict(boxes)), _union(boxes.values()))


def _linear(sizes, gap, origin, align, horizontal, slot):
    items = _items(sizes)
    gap = _gap(gap)
    ox, oy = _point(origin)
    cross = max((h if horizontal else w) for _, (w, h) in items)
    if slot is not None:
        _finite(slot)
        if slot < max((w if horizontal else h) for _, (w, h) in items):
            raise ValueError("slot is smaller than the largest item")
    boxes = {}
    cursor = 0.0
    for key, (w, h) in items:
        main = w if horizontal else h
        length = float(slot) if slot is not None else main
        inner = (length - main) / 2
        offset = _align_offset(cross, h if horizontal else w, align)
        if horizontal:
            boxes[key] = Box(ox + cursor + inner, oy + offset, w, h)
        else:
            boxes[key] = Box(ox + offset, oy + cursor + inner, w, h)
        cursor += length + gap
    return _placement(boxes)


@_drawing_api(
    "layout",
    purpose="把对象横向排成一行。",
    returns="Placement",
    semantics=(
        "sizes 为有序列表或 key→(width, height)/Box/Geometry 映射；按给定顺序从 origin 向右排。",
        "gap 是相邻占位间距；align 为 top/center/bottom，按行内最高对象对齐。",
        "slot 可给每个对象固定主轴宽度并在槽内居中，用于等宽列。",
    ),
    example='placement = row({k: g for k, g in parts.items()}, gap=gap, align="center", origin=(x, y))',
    limits=("不换行、不缩放，也不检查是否超出画布；超宽时由作者调整尺寸或改用 grid。",),
    rank=10,
)
def row(sizes, *, gap=24, origin=(0, 0), align="center", slot=None):
    return _linear(sizes, gap, origin, align, True, slot)


@_drawing_api(
    "layout",
    purpose="把对象纵向排成一列。",
    returns="Placement",
    semantics=("与 row 相同，但从 origin 向下排；align 为 left/center/right。",),
    example='placement = column(parts, gap=gap, align="left", origin=(x, y))',
    limits=("不换列、不缩放。",),
    rank=11,
)
def column(sizes, *, gap=24, origin=(0, 0), align="center", slot=None):
    return _linear(sizes, gap, origin, align, False, slot)


@_drawing_api(
    "layout",
    purpose="把对象按行优先排成网格。",
    returns="Placement",
    semantics=(
        "columns 为列数；同列共享该列最大宽度，同行共享该行最大高度，对象在单元格内按 align/valign 对齐。",
        "col_gap/row_gap 分别为列间距与行间距；结果顺序与输入顺序一致。",
    ),
    example="placement = grid(parts, columns=3, col_gap=gap, row_gap=gap, origin=(x, y))",
    limits=("不自动选择列数或缩放对象。",),
    rank=12,
)
def grid(sizes, *, columns, col_gap=24, row_gap=24, origin=(0, 0), align="center", valign="center"):
    items = _items(sizes)
    if not isinstance(columns, int) or isinstance(columns, bool) or columns <= 0:
        raise ValueError("columns must be a positive integer")
    col_gap, row_gap = _gap(col_gap, "col_gap"), _gap(row_gap, "row_gap")
    ox, oy = _point(origin)
    rows = math.ceil(len(items) / columns)
    widths = [0.0] * columns
    heights = [0.0] * rows
    for index, (_, (w, h)) in enumerate(items):
        widths[index % columns] = max(widths[index % columns], w)
        heights[index // columns] = max(heights[index // columns], h)
    xs = [ox + sum(widths[:c]) + c * col_gap for c in range(columns)]
    ys = [oy + sum(heights[:r]) + r * row_gap for r in range(rows)]
    boxes = {}
    for index, (key, (w, h)) in enumerate(items):
        c, r = index % columns, index // columns
        boxes[key] = Box(xs[c] + _align_offset(widths[c], w, align), ys[r] + _align_offset(heights[r], h, valign), w, h)
    return _placement(boxes)


def _node_boxes(nodes):
    from ._scene import Node

    result = []
    for node in nodes:
        if not isinstance(node, Node):
            raise TypeError("align/distribute take Drawing nodes")
        result.append((node, node.bounds))
    if len(result) < 2:
        raise ValueError("Need at least two nodes")
    drawing = result[0][0].drawing
    if any(node.drawing is not drawing for node, _ in result):
        raise ValueError("Nodes belong to different drawings")
    return result


def _shift(node, dx, dy):
    if abs(dx) < 1e-12 and abs(dy) < 1e-12:
        return
    box = node.bounds
    node.move_to(box.x + dx, box.y + dy, own_anchor="top_left")


@_drawing_api(
    "layout",
    purpose="把已加入画布的对象沿一条边或中线对齐。",
    returns="None（移动这些 Node）",
    semantics=(
        "edge 为 left/right/top/bottom/center_x/center_y；对齐到 to 给出的坐标，省略时取首个对象的对应位置。",
        "移动后对象改为固定位置，原有 pin 绑定被替换；需要联动的对象不要再调用 align。",
    ),
    example='align(drawing.nodes["a"], drawing.nodes["b"], edge="top")',
    limits=("只按外接框对齐，不按真实轮廓或文字基线。",),
    rank=20,
)
def align(*nodes, edge="center_y", to=None):
    pairs = _node_boxes(nodes)
    getters = {
        "left": lambda b: b.x,
        "right": lambda b: b.x + b.width,
        "top": lambda b: b.y,
        "bottom": lambda b: b.y + b.height,
        "center_x": lambda b: b.x + b.width / 2,
        "center_y": lambda b: b.y + b.height / 2,
    }
    if edge not in getters:
        raise ValueError(f"Unknown edge {edge!r}")
    target = getters[edge](pairs[0][1]) if to is None else float(to)
    horizontal = edge in ("left", "right", "center_x")
    for node, box in pairs:
        delta = target - getters[edge](box)
        _shift(node, delta if horizontal else 0, 0 if horizontal else delta)


@_drawing_api(
    "layout",
    purpose="在首尾两个对象之间等距分布中间对象。",
    returns="None（移动这些 Node）",
    semantics=(
        'axis 为 x/y；按传入顺序分布，首尾对象不动；mode="gap" 使相邻间隙相等，mode="center" 使中心等距。',
        "移动后对象改为固定位置，原有 pin 绑定被替换。",
    ),
    example='distribute(*[drawing.nodes[k] for k in keys], axis="x")',
    limits=("至少三个对象；按外接框计算。",),
    rank=21,
)
def distribute(*nodes, axis="x", mode="gap"):
    pairs = _node_boxes(nodes)
    if len(pairs) < 3:
        raise ValueError("distribute needs at least three nodes")
    if axis not in ("x", "y") or mode not in ("gap", "center"):
        raise ValueError("axis must be x/y and mode gap/center")
    start = (lambda b: b.x) if axis == "x" else (lambda b: b.y)
    extent = (lambda b: b.width) if axis == "x" else (lambda b: b.height)
    first, last = pairs[0][1], pairs[-1][1]
    if mode == "center":
        a = start(first) + extent(first) / 2
        z = start(last) + extent(last) / 2
        step = (z - a) / (len(pairs) - 1)
        for i, (node, box) in enumerate(pairs[1:-1], 1):
            delta = a + step * i - (start(box) + extent(box) / 2)
            _shift(node, delta if axis == "x" else 0, 0 if axis == "x" else delta)
        return
    total = (start(last) + extent(last)) - start(first) - sum(extent(b) for _, b in pairs)
    step = total / (len(pairs) - 1)
    cursor = start(first) + extent(first) + step
    for node, box in pairs[1:-1]:
        delta = cursor - start(box)
        _shift(node, delta if axis == "x" else 0, 0 if axis == "x" else delta)
        cursor += extent(box) + step


@_drawing_api(
    "layout",
    purpose="保存环形布局及沿圆周的连接弧。",
    returns="RingLayout 快照",
    semantics=(
        "centers 为 key→节点中心；angles 为对应角度（度，0 在 +x，正值顺时针）；boxes 为放置用占位。",
        "arcs 为相邻节点之间沿同一圆周的 SVG 路径 d，已在两端按节点外接圆半径留出 gap，不穿过节点。",
    ),
    example="layout = ring(parts, center=(cx, cy), radius=r)\n"
    'node = drawing.add(key, part, at=layout.centers[key], own_anchor="center")\n'
    'drawing.add(f"arc-{i}", path(layout.arcs[i], fill="none", **line_paint))',
    common=False,
)
@dataclass(frozen=True)
class RingLayout:
    centers: Mapping[Hashable, Point]
    angles: Mapping[Hashable, float]
    boxes: Mapping[Hashable, Box]
    arcs: tuple[str, ...]
    center: Point
    radius: float


@_drawing_api(
    "layout",
    purpose="沿圆周均匀放置节点，并生成相邻节点间沿圆周的弧形连线。",
    returns="RingLayout",
    semantics=(
        "sizes 为有序列表或映射；首个对象位于 start_angle（度，-90 为正上方），按 clockwise 方向依次排列。",
        "arcs 默认首尾闭合（closed=True）；弧线是圆周上的真实圆弧，弧端按节点外接圆半径加 gap 截短，便于加 marker-end 箭头。",
        "箭头方向即排列方向；需要标签时在 layout.angles 上沿径向向外偏移放置。",
    ),
    example="layout = ring(parts, center=(cx, cy), radius=r, start_angle=-90, gap=6)",
    limits=("只保证节点中心在圆上；节点过大互相重叠时报错，需增大 radius 或缩小节点。",),
    rank=30,
)
def ring(sizes, *, center, radius, start_angle=-90, clockwise=True, closed=True, gap=6):
    items = _items(sizes)
    cx, cy = _point(center)
    _finite(radius, start_angle)
    if radius <= 0:
        raise ValueError("radius must be positive")
    gap = _gap(gap)
    n = len(items)
    step = 360.0 / n * (1 if clockwise else -1)
    centers, angles, boxes, reach = {}, {}, {}, {}
    for i, (key, (w, h)) in enumerate(items):
        angle = start_angle + step * i
        a = math.radians(angle)
        x, y = cx + radius * math.cos(a), cy + radius * math.sin(a)
        centers[key], angles[key] = (x, y), angle
        boxes[key] = Box(x - w / 2, y - h / 2, w, h)
        reach[key] = math.hypot(w, h) / 2
    keys = [k for k, _ in items]
    chord = 2 * radius * math.sin(math.pi / n) if n > 1 else math.inf
    for a, b in zip(keys, keys[1:] + keys[:1] if n > 1 else []):
        if reach[a] + reach[b] >= chord:
            raise ValueError("Ring nodes overlap; increase radius or reduce node size")
    arcs = []
    pairs = list(zip(keys, keys[1:]))
    if closed and n > 2:
        pairs.append((keys[-1], keys[0]))
    for a, b in pairs:
        trim_a = 2 * math.degrees(math.asin(min(1, (reach[a] + gap) / (2 * radius))))
        trim_b = 2 * math.degrees(math.asin(min(1, (reach[b] + gap) / (2 * radius))))
        start = angles[a] + math.copysign(trim_a, step)
        end = angles[a] + step - math.copysign(trim_b, step)
        if (end - start) * step <= 0:
            raise ValueError("Ring gap leaves no room for the connecting arc")
        p0 = (cx + radius * math.cos(math.radians(start)), cy + radius * math.sin(math.radians(start)))
        p1 = (cx + radius * math.cos(math.radians(end)), cy + radius * math.sin(math.radians(end)))
        large = 1 if abs(end - start) > 180 else 0
        sweep = 1 if clockwise else 0
        arcs.append(
            f"M {fmt(p0[0])} {fmt(p0[1])} A {fmt(radius)} {fmt(radius)} 0 {large} {sweep} {fmt(p1[0])} {fmt(p1[1])}"
        )
    return RingLayout(
        MappingProxyType(centers),
        MappingProxyType(angles),
        MappingProxyType(boxes),
        tuple(arcs),
        (cx, cy),
        float(radius),
    )


def _crossings(left, right, edges):
    lpos = {k: i for i, k in enumerate(left)}
    rpos = {k: i for i, k in enumerate(right)}
    pairs = [(lpos[a], rpos[b]) for a, b in edges]
    return sum(1 for i, (a, b) in enumerate(pairs) for c, d in pairs[i + 1 :] if (a - c) * (b - d) < 0)


@_drawing_api(
    "layout",
    purpose="重排两列对象的顺序以减少连线交叉。",
    returns="(left_order, right_order) 元组",
    semantics=(
        "left/right 为两列 key 的初始顺序；edges 为 (left_key, right_key) 连接。",
        '用重心法交替迭代并保留更优结果；fixed="left" 或 "right" 时固定一侧，只重排另一侧。',
        "返回新顺序，再用 column(...) 按该顺序放置两列，连线会更接近平行。",
    ),
    example="left_order, right_order = bipartite_order(receptors, ligands, pairs)\n"
    "left = column({k: parts[k] for k in left_order}, gap=gap, origin=(x0, y0))",
    limits=("启发式，不保证全局最少交叉；没有连线的对象保持相对次序。",),
    rank=40,
)
def bipartite_order(left, right, edges, *, fixed=None, iterations=8):
    left, right = list(left), list(right)
    if len(set(left)) != len(left) or len(set(right)) != len(right):
        raise ValueError("Duplicate keys in a column")
    edges = [tuple(e) for e in edges]
    lset, rset = set(left), set(right)
    for a, b in edges:
        if a not in lset or b not in rset:
            raise ValueError(f"Edge {(a, b)!r} references an unknown key")
    if fixed not in (None, "left", "right"):
        raise ValueError('fixed must be None, "left" or "right"')

    def reorder(moving, anchor, by_moving):
        pos = {k: i for i, k in enumerate(anchor)}

        def key(item):
            index, name = item
            linked = [pos[o] for o in by_moving.get(name, ())]
            return (sum(linked) / len(linked) if linked else index, index)

        return [name for _, name in sorted(enumerate(moving), key=key)]

    to_right, to_left = {}, {}
    for a, b in edges:
        to_right.setdefault(a, []).append(b)
        to_left.setdefault(b, []).append(a)
    best = (left, right, _crossings(left, right, edges))
    cur_l, cur_r = left, right
    for _ in range(max(1, int(iterations))):
        if fixed != "right":
            cur_r = reorder(cur_r, cur_l, to_left)
        if fixed != "left":
            cur_l = reorder(cur_l, cur_r, to_right)
        score = _crossings(cur_l, cur_r, edges)
        if score < best[2]:
            best = (cur_l, cur_r, score)
        if score == 0:
            break
    return tuple(best[0]), tuple(best[1])


@_drawing_api(
    "layout",
    purpose="保存一组错开的连线端口与转折位置。",
    returns="PortSpread 快照",
    semantics=(
        "ports[key] 是随节点联动的 Anchor；lanes[key] 是该连线的转折坐标（左右边为 x，上下边为 y）。",
        'waypoints(key, target) 返回 [转折点1, 转折点2]，传给 connect(route="polyline")，使每条线在不同位置转弯、竖段互不重叠。',
    ),
    example='spread = spread_ports(hub, "right", targets)\n'
    'drawing.connect(name, spread.ports[k], target, route="polyline", waypoints=spread.waypoints(k, target))',
    common=False,
)
@dataclass(frozen=True)
class PortSpread:
    ports: Mapping[Hashable, object]
    lanes: Mapping[Hashable, float]
    side: str
    drawing: object

    def waypoints(self, key, target):
        from ._scene import Node, _Layout

        layout = _Layout(self.drawing)
        start = layout.point(self.ports[key])
        if isinstance(target, Node):
            target = target.anchor("center")
        end = layout.point(target) if not isinstance(target, tuple) else _point(target)
        lane = self.lanes[key]
        if self.side in ("left", "right"):
            return [(lane, start[1]), (lane, end[1])]
        return [(start[0], lane), (end[0], lane)]


@_drawing_api(
    "layout",
    purpose="沿对象一条边均匀分配多个连线端口，并错开各线的转折位置。",
    returns="PortSpread",
    semantics=(
        "node 为已加入画布的 Node；side 为 left/right/top/bottom；targets 为 key→对端 Anchor/Node/坐标。",
        "按对端在边方向上的位置排序后均分端口，连线互不交叉；margin 是端口离边两端的最小距离。",
        "转折位置在节点边与最近对端之间按 lane_gap 错开：离节点越近的对端先转弯，竖段不重叠。",
        "返回的端口随 node 联动；waypoints 为当前位置快照，对象移动后重新调用。",
    ),
    example='spread = spread_ports(hub, "right", {k: drawing.nodes[k].anchor("left") for k in keys})\n'
    'target = drawing.nodes[k].anchor("left")\n'
    'drawing.connect(f"e-{k}", spread.ports[k], target, route="polyline", waypoints=spread.waypoints(k, target))',
    limits=("只在外接框边上分配；对端分布在节点两侧时请按侧分组分别调用。",),
    rank=50,
)
def spread_ports(node, side, targets, *, margin=8, lane_gap=10):
    from ._scene import Anchor, ContourAnchor, Edge, Node, _Layout

    if not isinstance(node, Node):
        raise TypeError("node must be a Drawing Node")
    if side not in ("left", "right", "top", "bottom"):
        raise ValueError("side must be left, right, top or bottom")
    if not isinstance(targets, Mapping) or not targets:
        raise ValueError("targets must be a non-empty mapping")
    margin = _gap(margin, "margin")
    lane_gap = _gap(lane_gap, "lane_gap")
    layout = _Layout(node.drawing)
    box = layout.bounds(node)
    vertical_edge = side in ("left", "right")
    span = box.height if vertical_edge else box.width
    if span - 2 * margin <= 0:
        raise ValueError("margin leaves no room on this side")

    def point(target):
        if isinstance(target, Node):
            target = target.anchor("center")
        return layout.point(target) if isinstance(target, (Anchor, ContourAnchor, Edge)) else _point(target)

    along = 1 if vertical_edge else 0
    order = sorted(targets, key=lambda k: (point(targets[k])[along], str(k)))
    n = len(order)
    edge_point = box.anchor(side)
    ports = {}
    for i, key in enumerate(order):
        t = margin + (span - 2 * margin) * (i + 1) / (n + 1)
        start = box.y if vertical_edge else box.x
        target_pos = start + t
        offset = (0, target_pos - edge_point[1]) if vertical_edge else (target_pos - edge_point[0], 0)
        ports[key] = Anchor(node, side).shifted(*offset)

    # Lanes: a turn per line between the node edge and the nearest target, nested so
    # lines ending farther along the edge turn farther out and never share a segment.
    sign = {"right": 1, "bottom": 1, "left": -1, "top": -1}[side]
    across = 0 if vertical_edge else 1
    edge = edge_point[across]
    nearest = min(point(targets[k])[across] for k in order)
    room = (nearest - edge) * sign
    if room <= lane_gap:
        raise ValueError("Targets are too close to the node edge for separate turns")
    pos = {k: point(targets[k])[along] for k in order}
    port_pos = {k: layout.point(ports[k])[along] for k in order}
    # Lines going toward smaller / larger coordinates form two nested fans. Within
    # each fan the line turning back farthest from the shared side turns first.
    lane_of = {}
    width = lane_gap * max(0, n - 1)
    first = edge + sign * max(lane_gap, (room - width) / 2)
    down = [k for k in order if pos[k] > port_pos[k] + 1e-9]
    up = [k for k in order if pos[k] < port_pos[k] - 1e-9]
    level = [k for k in order if k not in down and k not in up]
    # Down-going lines: the lowest port turns nearest the node; up-going mirror it.
    # Every line gets its own lane so no two vertical segments coincide.
    ranked = sorted(down, key=lambda k: port_pos[k], reverse=True) + level + sorted(up, key=lambda k: port_pos[k])
    for i, k in enumerate(ranked):
        lane_of[k] = first + sign * lane_gap * i
    lanes = lane_of
    for k in order:
        if (lanes[k] - edge) * sign <= 0 or (nearest - lanes[k]) * sign <= 0:
            raise ValueError("Not enough room between the node and targets for separate turns; reduce lane_gap")
    return PortSpread(MappingProxyType(ports), MappingProxyType(lanes), side, node.drawing)
