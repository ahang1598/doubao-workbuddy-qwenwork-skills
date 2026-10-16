"""Positions for ordered trees with measured node sizes; no drawing or page layout."""

from __future__ import annotations

from collections.abc import Hashable, Mapping, Sequence
from dataclasses import dataclass
import math
from types import MappingProxyType

from ._geometry import Box
from ._help import _drawing_api


@_drawing_api(
    "anchors",
    purpose="保存有序树的纯几何布局结果。",
    returns="TreeLayout 快照",
    semantics=(
        "由 tree_layout 返回；boxes/depths 为只读映射，edges/leaf_order 为元组。",
        "boxes 使用现有 Box；edges 只表示输入父子关系，leaf_order 是按输入子序列的 DFS 叶序，不自动创建 next 线。",
    ),
    example="layout = tree_layout(root, children, sizes)\nroot_box = layout.boxes[root]",
    common=False,
)
@dataclass(frozen=True)
class TreeLayout:
    boxes: Mapping[Hashable, Box]
    depths: Mapping[Hashable, int]
    edges: tuple[tuple[Hashable, Hashable], ...]
    leaf_order: tuple[Hashable, ...]
    bounds: Box
    direction: str


def _number(value, name, *, positive=False):
    if isinstance(value, (str, bytes, bool)):
        raise TypeError(f"{name} must be a number")
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if not math.isfinite(result) or (result <= 0 if positive else result < 0):
        raise ValueError(f"{name} must be finite and {'positive' if positive else 'nonnegative'}")
    return result


def _pair(value, name):
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise TypeError(f"{name} must contain two coordinates")
    try:
        a, b = value
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must contain two coordinates") from exc
    return a, b


def _finite_sum(*values):
    try:
        result = math.fsum(values)
    except OverflowError as exc:
        raise ValueError("Tree layout exceeds finite coordinate range") from exc
    if not math.isfinite(result):
        raise ValueError("Tree layout exceeds finite coordinate range")
    return result


def _key(value):
    try:
        hash(value)
    except TypeError as exc:
        raise TypeError("Tree node IDs must be hashable") from exc


_GEOMETRY_REL_TOL = 1e-7


def _precision_error():
    raise ValueError(
        "Tree layout loses node dimensions or spacing at floating-point precision. "
        "Translate or rescale the input geometry."
    )


def _check_extent(start, size):
    end = _finite_sum(start, size)
    actual = _finite_sum(end, -start)
    if actual <= 0 or not math.isclose(actual, size, rel_tol=_GEOMETRY_REL_TOL):
        _precision_error()
    return end


def _check_gap(actual, required, coordinates, dimensions):
    if required > 0:
        # A positive requested gap must not disappear, even if it is smaller
        # than one ULP of the translated coordinates.
        if actual <= 0 or (actual < required and not math.isclose(actual, required, rel_tol=_GEOMETRY_REL_TOL)):
            _precision_error()
    elif actual < 0:
        # Touching boxes can acquire a tiny negative difference after reflection or translation.
        tolerance = min(
            8 * max(math.ulp(value) for value in coordinates),
            min(dimensions) * _GEOMETRY_REL_TOL,
        )
        if -actual > tolerance:
            _precision_error()


def _check_output_precision(boxes, depths, leaf_order, bounds, direction, gap, level_gap):
    """Validate actual returned coordinates in O(N), without another layout pass."""
    horizontal = direction in ("right", "left")
    reverse = direction in ("up", "left")
    previous_at_depth, bands, cross_intervals = {}, {}, {}
    for node, box in boxes.items():
        right = _check_extent(box.x, box.width)
        bottom = _check_extent(box.y, box.height)
        start, end, size = (box.y, bottom, box.height) if horizontal else (box.x, right, box.width)
        cross_intervals[node] = start, end, size
        depth = depths[node]
        if depth in previous_at_depth:
            prior_start, prior_end, prior_size = previous_at_depth[depth]
            _check_gap(_finite_sum(start, -prior_end), gap, (prior_start, prior_end, start, end), (prior_size, size))
        previous_at_depth[depth] = start, end, size
        near, far, forward_size = (box.x, right, box.width) if horizontal else (box.y, bottom, box.height)
        if reverse:
            near, far = -far, -near
        if depth in bands:
            old_near, old_far, old_size = bands[depth]
            bands[depth] = min(old_near, near), max(old_far, far), min(old_size, forward_size)
        else:
            bands[depth] = near, far, forward_size
    for first, second in zip(leaf_order, leaf_order[1:]):
        start_a, end_a, size_a = cross_intervals[first]
        start_b, end_b, size_b = cross_intervals[second]
        _check_gap(_finite_sum(start_b, -end_a), gap, (start_a, end_a, start_b, end_b), (size_a, size_b))
    for depth in range(len(bands) - 1):
        near_a, far_a, size_a = bands[depth]
        near_b, far_b, size_b = bands[depth + 1]
        _check_gap(_finite_sum(near_b, -far_a), level_gap, (near_a, far_a, near_b, far_b), (size_a, size_b))
    _check_extent(bounds.x, bounds.width)
    _check_extent(bounds.y, bounds.height)


@_drawing_api(
    "anchors",
    purpose="按节点实际宽高排布有序真树，只返回位置和关系。",
    returns="TreeLayout：boxes、depths、edges、leaf_order、bounds、direction",
    semantics=(
        "root/children 使用可哈希节点ID；children 的值为有序子ID序列，未列子的节点视为叶子。",
        "sizes[id] 为 (width, height) 或 Box（只取宽高）；尺寸必须正且有限，无关的额外 sizes 条目忽略。",
        "子树跨度不含尾部间距；相邻子树由父层统一加入 sibling_gap，同深度按最大主轴尺寸加 level_gap。",
        "direction 支持 down/up/right/left；竖向孩子从左到右，横向从上到下，物理宽高不交换。",
        "origin 固定整树 bounds 的左上角，不是根节点左上角；输入不变，结果是新快照。",
    ),
    example="layout = tree_layout(root, children, {key: g.bounds for key, g in parts.items()})\n"
    "for key, box in layout.boxes.items():\n"
    '    drawing.add(key, parts[key], at=box.anchor("top_left"), own_anchor="top_left")',
    limits=(
        "拒绝环、多父DAG、重复child、未连接的children声明或缺失尺寸；共享节点不展开复制。",
        "浮点精度不足以保留节点宽高或所需间距时拒绝返回布局；请平移或调整输入尺度。",
        "只排节点占位，不生成SVG、箭尖或页模板，不自动测字/避让所有连线/装入画布。",
        "sizes 需包含作者所需的描边与标签占位；不保证节点增删后的跨状态坐标不变。",
    ),
    rank=5,
)
def tree_layout(root, children, sizes, *, origin=(0, 0), sibling_gap=24, level_gap=48, direction="down"):
    if not isinstance(children, Mapping) or not isinstance(sizes, Mapping):
        raise TypeError("children and sizes must be mappings")
    if direction not in ("down", "up", "right", "left"):
        raise ValueError("direction must be down, up, right or left")
    gap = _number(sibling_gap, "sibling_gap")
    level_gap = _number(level_gap, "level_gap")
    ox, oy = _pair(origin, "origin")
    # Origins may be negative; unlike dimensions/gaps they need no sign bound.
    if any(isinstance(v, (str, bytes, bool)) for v in (ox, oy)):
        raise TypeError("origin coordinates must be numbers")
    try:
        ox, oy = float(ox), float(oy)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("origin coordinates must be finite") from exc
    if not math.isfinite(ox) or not math.isfinite(oy):
        raise ValueError("origin coordinates must be finite")
    _key(root)
    graph, parents = {}, {}
    for node, values in children.items():
        _key(node)
        if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
            raise TypeError("Each children entry must be an ordered sequence of IDs")
        kids, seen = tuple(values), set()
        for child in kids:
            _key(child)
            if child in seen:
                raise ValueError(f"Duplicate child {child!r} of {node!r}")
            if child in parents:
                raise ValueError(f"Multiple parents for {child!r}; DAG nodes are not copied")
            seen.add(child)
            parents[child] = node
        graph[node] = kids
    if root in parents:
        raise ValueError("The root has a parent: cycle or incorrect root")

    # Iterative walks avoid a recursion-depth limit for long, valid chains.
    order, depths, stack = [], {}, [(root, 0)]
    while stack:
        node, depth = stack.pop()
        if node in depths:
            raise ValueError("Cycle or shared node in tree")
        order.append(node)
        depths[node] = depth
        stack.extend((child, depth + 1) for child in reversed(graph.get(node, ())))
    if any(node not in depths for node in graph):
        raise ValueError("children contains disconnected declarations or an unreachable cycle")

    dimensions, cross_size, forward_size = {}, {}, {}
    horizontal = direction in ("right", "left")
    for node in order:
        if node not in sizes:
            raise ValueError(f"Missing size for tree node {node!r}")
        value = sizes[node]
        w, h = (value.width, value.height) if isinstance(value, Box) else _pair(value, "node size")
        w, h = _number(w, "node width", positive=True), _number(h, "node height", positive=True)
        dimensions[node] = w, h
        cross_size[node], forward_size[node] = (h, w) if horizontal else (w, h)

    spans, children_spans = {}, {}
    for node in reversed(order):
        kids = graph.get(node, ())
        width = _finite_sum(*(spans[child] for child in kids), gap * max(0, len(kids) - 1))
        children_spans[node] = width
        spans[node] = max(cross_size[node], width)
    band_sizes = [0.0] * (max(depths.values()) + 1)
    for node in order:
        band_sizes[depths[node]] = max(band_sizes[depths[node]], forward_size[node])
    band_starts = [0.0]
    for size in band_sizes[:-1]:
        band_starts.append(_finite_sum(band_starts[-1], size, level_gap))
    forward_extent = _finite_sum(band_starts[-1], band_sizes[-1])
    cross_extent = spans[root]

    boxes, offsets = {}, {root: 0.0}
    for node in order:
        cross = _finite_sum(offsets[node], (spans[node] - cross_size[node]) / 2)
        forward = band_starts[depths[node]]
        w, h = dimensions[node]
        if direction in ("up", "left"):
            forward = _finite_sum(forward_extent, -forward, -forward_size[node])
        x, y = (forward, cross) if horizontal else (cross, forward)
        x, y = _finite_sum(ox, x), _finite_sum(oy, y)
        _finite_sum(x, w)
        _finite_sum(y, h)
        boxes[node] = Box(x, y, w, h)
        cursor = _finite_sum(offsets[node], (spans[node] - children_spans[node]) / 2)
        kids = graph.get(node, ())
        for i, child in enumerate(kids):
            offsets[child] = cursor
            if i + 1 < len(kids):
                cursor = _finite_sum(cursor, spans[child], gap)
    width, height = (forward_extent, cross_extent) if horizontal else (cross_extent, forward_extent)
    _finite_sum(ox, width)
    _finite_sum(oy, height)
    leaf_order = tuple(node for node in order if not graph.get(node))
    bounds = Box(ox, oy, width, height)
    _check_output_precision(boxes, depths, leaf_order, bounds, direction, gap, level_gap)
    return TreeLayout(
        MappingProxyType(boxes),
        MappingProxyType(depths),
        tuple((node, child) for node in order for child in graph.get(node, ())),
        leaf_order,
        bounds,
        direction,
    )
