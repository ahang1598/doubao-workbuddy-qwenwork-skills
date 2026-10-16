"""Canvas instances, live anchors, connectors and SVG export."""

from __future__ import annotations

import copy
from dataclasses import dataclass
import math
from pathlib import Path
import xml.etree.ElementTree as ET
from ..atomize_svg_to_slide._geometry import fmt, rotate, scale, translate
from ._geometry import (
    Geometry,
    Point,
    PathFrame,
    Box,
    _attrs,
    _finite,
    _point,
    _unit,
    _map_direction,
    _scoped,
    label,
    _color_id,
)
from ._help import _drawing_api
from ._svgwrite import SvgwriteAliases, _position


@dataclass(frozen=True)
class Anchor:
    node: Node
    name: str = "center"
    is_port: bool = False
    offset: Point = (0, 0)

    @_drawing_api(
        "anchors",
        purpose="为动态锚点增加固定偏移。",
        returns="新 Anchor",
        semantics=("dx/dy 使用画布坐标，不随目标缩放或旋转；原引用不变。",),
        example='target = body.anchor("right").shifted(dx, dy)',
        limits=(),
    )
    def shifted(self, dx=0, dy=0):
        x, y = _point((dx, dy))
        return Anchor(self.node, self.name, self.is_port, (self.offset[0] + x, self.offset[1] + y))


@dataclass(frozen=True)
class Edge:
    node: Node
    toward: Anchor | Edge | Point
    clearance: float = 0


@dataclass(frozen=True, eq=False)
class EdgeLabelAnchor:
    """Centre of a connector's own label: a point along the routed line, offset along its normal by"""

    connector: object
    fraction: float
    side: object  # +1 / -1 (normal sign) or 'above' / 'below' / 'left' / 'right' (screen direction)
    gap: float
    size: tuple


@dataclass(frozen=True)
class ContourAnchor:
    node: Node
    fraction: float | None = None
    target: object = None
    origin: Point | None = None
    hit: str = "nearest"
    normal: str = "left"
    subpath: int = 0
    tolerance: float = 0.25
    offset: Point = (0, 0)

    @_drawing_api(
        "anchors",
        purpose="偏移动态轮廓端口的位置。",
        returns="新 ContourAnchor",
        semantics=("偏移使用画布坐标；位置随对象更新，法线方向保持原端口方向。",),
        example="target = body.contour_at(fraction).shifted(dx, dy)",
        common=False,
    )
    def shifted(self, dx=0, dy=0):
        from dataclasses import replace

        x, y = _point((dx, dy))
        return replace(self, offset=(self.offset[0] + x, self.offset[1] + y))


_OUTLINE_TAGS = ("rect", "circle", "ellipse", "path", "polygon")


def _pick_outline(root, extent, defs=""):
    """The shape arrows and contour queries land on: the first closed shape (looking inside a leading <g>)."""
    from ..atomize_svg_to_slide._bounds import svg_bounds

    shapes = []

    def walk(el):
        for c in el:
            if c.tag in ("defs", "title", "desc", "text", "clipPath", "mask", "marker", "symbol"):
                continue
            if c.tag in _OUTLINE_TAGS:
                shapes.append(c)
            elif c.tag == "g" and not c.get("transform"):
                walk(c)

    walk(root)
    if not shapes:
        return None
    _, _, w, h = extent

    def size(el):
        try:
            b = svg_bounds(
                f"<g>{ET.tostring(el, encoding='unicode')}</g>", defs, (-1e5, -1e5, 2e5, 2e5), unknown_none=True
            )
        except Exception:  # noqa: BLE001 — unknown geometry is simply not a candidate
            return None
        return b and (b[2], b[3])

    first = size(shapes[0])
    if first and (first[0] < 0.4 * w and first[1] < 0.4 * h):
        for el in shapes[1:]:
            s = size(el)
            if s and s[0] >= 0.8 * w and s[1] >= 0.8 * h:
                return el
    return shapes[0]


def _marked_outline(geometry, subpath, tolerance):
    """Contour of the element marked data-outline (with its accumulated transform) when the generic query cannot pick one."""
    from ..atomize_svg_to_slide._geometry import Matrix, parse_transform
    from ._curves import geometry_contour

    found = []

    def walk(el, m):
        if found:
            return
        if el.get("transform"):
            m = m.then(parse_transform(el.get("transform")))
        if el.get("data-outline") == "1" and el.tag.split("}")[-1] in _OUTLINE_TAGS:
            found.append((el, m))
            return
        for c in el:
            walk(c, m)

    walk(geometry.element, Matrix())
    if not found:
        raise ValueError("Select one component before querying its contour")
    el, m = found[0]
    holder = ET.Element("g", {"transform": m.svg()})
    holder.append(copy.deepcopy(el))
    return geometry_contour(Geometry(holder, geometry.bounds), subpath, tolerance)


def svg_geometry(svg, *, scale=1.0, size=None, ports=None):
    """Hand-written SVG fragment → centred Geometry whose first visible shape is the outline."""
    from ..atomize_svg_to_slide._bounds import svg_bounds

    if 'data-chart-lib="1"' in svg or (svg.count('data-role="') >= 8 and "data-series=" in svg):
        raise ValueError(
            "this SVG comes from the chart library: place it with chart_slide(slug, x, y, w, h, **kwargs) "
            "and pass that fragment to publish_slide together with the drawing fragment, e.g. "
            "publish_slide(page_xml, d.to_slide(...), chart_slide(...)); inside a Drawing it loses "
            "automatic fitting, native text and recolorable blocks"
        )
    root = ET.fromstring(f'<g xmlns="http://www.w3.org/2000/svg">{svg}</g>')
    for node in root.iter():
        if "}" in node.tag:
            node.tag = node.tag.split("}", 1)[1]
        if node.tag in ("script", "image", "foreignObject"):
            raise ValueError(f"<{node.tag}> is not allowed in a hand-written node SVG")
    defs = "".join(ET.tostring(d, encoding="unicode") for d in root.iter("defs"))
    bare = ET.fromstring("<g>" + "".join(ET.tostring(c, encoding="unicode") for c in root if c.tag != "defs") + "</g>")
    # Measure geometry, not stroke/marker padding, so a svg_source() round trip keeps its size.
    for node in bare.iter():
        for key in ("stroke", "stroke-width", "marker-start", "marker-mid", "marker-end", "filter"):
            node.attrib.pop(key, None)
    x, y, w, h = svg_bounds(ET.tostring(bare, encoding="unicode"), defs, (-1e5, -1e5, 2e5, 2e5))
    if w <= 0 or h <= 0:
        raise ValueError("the SVG fragment has no visible content")
    if size is not None:
        scale = (size, size) if isinstance(size, (int, float)) else tuple(size)
    if isinstance(scale, tuple):
        k = min(scale[0] / w, scale[1] / h)
    else:
        _finite(scale)
        k = float(scale)
    cx, cy = x + w / 2, y + h / 2
    outline = _pick_outline(root, (x, y, w, h), defs)
    if outline is not None:
        outline.set("data-outline", "1")
    holder = ET.Element("g", {"transform": f"scale({fmt(k)}) translate({fmt(-cx)} {fmt(-cy)})"})
    holder.extend(list(root))
    inner = ET.Element("g")
    inner.append(holder)
    hw, hh = w * k / 2, h * k / 2
    edges = {"center": (0, 0), "top": (0, -hh), "bottom": (0, hh), "left": (-hw, 0), "right": (hw, 0)}
    for name_, (px, py) in (ports or {}).items():
        edges[name_] = ((px - cx) * k, (py - cy) * k)
    geometry = Geometry(inner, Box(-hw, -hh, 2 * hw, 2 * hh)).with_ports(**edges)
    dirs = dict(geometry.port_directions)
    dirs.update({"top": (0, -1), "bottom": (0, 1), "left": (-1, 0), "right": (1, 0)})
    return Geometry(geometry.element, geometry.bounds, geometry.ports, dirs, geometry.port_tangents)


class Node:
    def __init__(self, drawing, key, geometry, at, own_anchor):
        self.drawing, self.key, self.geometry = drawing, key, geometry
        self.target, self.own_anchor = at, own_anchor
        self.rotation, self.scale = 0.0, 1.0
        self.kind = None

    @_drawing_api(
        "anchors",
        purpose="引用实例的边界锚点或局部原点。",
        returns="Anchor 动态引用",
        semantics=(
            "默认 center；支持 top_left/top/top_right/left/right/bottom_left/bottom/bottom_right 和 origin。",
            "边界锚点基于变换后的外接框；要落在真实接口上使用 Node.port。",
        ),
        example='target = body.anchor("right")',
        limits=(),
    )
    def anchor(self, name="center"):
        return Anchor(self, name)

    @_drawing_api(
        "anchors",
        purpose="引用几何上已定义的真实接口。",
        returns="Anchor 动态引用",
        semantics=(
            "先用 Geometry.with_ports 或 group 的 ports 定义局部端口；端口随实例变换。",
            "这是引用，不是坐标元组；读取快照用 Drawing.resolve。",
        ),
        example='target = body.port("outlet")',
        limits=("未知端口在解析时会报错。",),
    )
    def port(self, name):
        ports = self.geometry.ports
        if name not in ports:
            if name in (
                "top",
                "bottom",
                "left",
                "right",
                "center",
                "top_left",
                "top_right",
                "bottom_left",
                "bottom_right",
            ):
                return Anchor(self, name, False)  # plain shapes have no declared ports; their box sides are the ports
            raise ValueError(
                f"Unknown port {self.key}.{name}; available: {', '.join(sorted(ports)) or '(none)'} — "
                f"or pass the node itself to d.arrow, or use node.contour_toward(target)"
            )
        return Anchor(self, name, True)

    @_drawing_api(
        "anchors",
        purpose="按弧长比例创建动态轮廓端口。",
        returns="ContourAnchor",
        semantics=(
            "fraction 在 0–1 之间；从当前几何的指定 subpath 取点，随移动、缩放、旋转和几何替换重算。",
            "normal 为 left/right/outward；outward 仅用于简单闭合轮廓。读取位置用 resolve，位置与方向用 resolve_frame。",
        ),
        example='port = body.contour_at(0.25, normal="outward")',
    )
    def contour_at(self, fraction, *, normal="left", subpath=0, tolerance=0.25):
        _finite(fraction, tolerance)
        if not 0 <= fraction <= 1 or tolerance <= 0:
            raise ValueError("fraction must be in [0,1]; tolerance must be positive")
        return ContourAnchor(self, fraction=float(fraction), normal=normal, subpath=subpath, tolerance=tolerance)

    @_drawing_api(
        "anchors",
        purpose="朝向目标求动态轮廓交点。",
        returns="ContourAnchor",
        semantics=(
            "target 是画布坐标或动态引用；射线起点 origin 用几何局部坐标，默认几何外接框中心。",
            "hit 为 nearest/farthest；目标与主体移动后重算，求交精度由 tolerance 控制。",
            "不包含描边厚度；未知轮廓、无交点或无定义的 outward 法线会在解析时报错。",
        ),
        example='port = body.contour_toward(other.anchor("center"))',
    )
    def contour_toward(self, target, *, origin=None, hit="nearest", normal="outward", subpath=0, tolerance=0.25):
        self.drawing._check_ref(target)
        _finite(tolerance)
        if tolerance <= 0:
            raise ValueError("tolerance must be positive")
        return ContourAnchor(
            self,
            target=target,
            origin=None if origin is None else _point(origin),
            hit=hit,
            normal=normal,
            subpath=subpath,
            tolerance=tolerance,
        )

    @_drawing_api(
        "connect",
        purpose="取得朝向某目标的外接框边缘。",
        returns="Edge 动态引用",
        semantics=(
            "target 为 Anchor、Edge 或坐标；clearance 沿射线向目标方向留出非负间距。",
            "适合让引导线停在文字框之外，不是任意轮廓的精确求交。",
        ),
        example='end = note.edge_toward(body.port("outlet"), clearance=gap)',
        limits=(),
        common=False,
    )
    def edge_toward(self, target, *, clearance=0):
        _finite(clearance)
        if clearance < 0:
            raise ValueError("Edge clearance cannot be negative")
        return Edge(self, target, clearance)

    @_drawing_api(
        "anchors",
        purpose="让当前实例相对目标保持位置关系。",
        returns="当前 Node",
        semantics=(
            "target 传 Anchor/Edge 会保持联动；传 (x, y) 是固定位置。",
            "own_anchor 是当前实例的对齐点，默认 center；可用九个边界锚点、origin 或 port:name。",
            "只绑定位置，不继承目标的旋转或缩放；当前实例的方向用 set_transform 设置。",
            "offset 使用画布坐标；本操作修改当前 Node，依赖在读取边界或导出时重新解析。",
        ),
        example='note.pin(body.anchor("right"), own_anchor="left", offset=(gap, 0))',
        limits=("循环依赖会报错；Edge 不支持非零 offset，偏移绑定请传 Anchor。",),
    )
    def pin(self, target, *, own_anchor="center", offset=(0, 0)):
        self.drawing._check_ref(target)
        dx, dy = _point(offset)
        if isinstance(target, (Anchor, ContourAnchor)):
            target = target.shifted(dx, dy)
        elif isinstance(target, Edge):
            if dx or dy:
                raise ValueError("Use an Anchor for a shifted binding")
        else:
            x, y = _point(target)
            target = x + dx, y + dy
        self.target, self.own_anchor = target, own_anchor
        return self

    @_drawing_api(
        "anchors",
        purpose="把当前实例移到固定画布位置。",
        returns="当前 Node",
        semantics=(
            "x/y 为画布坐标；own_anchor=None 时沿用原对齐点。",
            "此操作会替换原来的动态位置绑定；需要联动用 Node.pin。",
        ),
        example="body.move_to(x, y)",
        limits=(),
        common=False,
    )
    def move_to(self, x, y, *, own_anchor=None):
        return self.pin(_point((x, y)), own_anchor=own_anchor or self.own_anchor)

    @_drawing_api(
        "anchors",
        purpose="替换实例的几何，并保留位置关系。",
        returns="当前 Node",
        semantics=("geometry 必须是 Geometry；依赖它的锚点在下次解析时按新边界更新。",),
        example="body.set_geometry(new_geometry)",
        limits=(),
        common=False,
    )
    def set_geometry(self, geometry):
        if not isinstance(geometry, Geometry):
            raise TypeError("Expected Geometry")
        self.geometry = geometry
        return self

    @_drawing_api(
        "anchors",
        purpose="读出节点当前外形的 SVG 片段（以节点中心为原点），作为 replace_svg 精修的起点。",
        returns="str（SVG 元素片段）",
        semantics=('坐标单位与画布相同、原点在节点外接框中心；改完直接传回 replace_svg(..., fit="own")。',),
        example='src = cell_node.svg_source()\ncell_node.replace_svg(src.replace("#F3EEF8", "#EEF3FA"), fit="own")',
        rank=3,
    )
    def svg_source(self):
        b = self.geometry.bounds
        cx, cy = b.x + b.width / 2, b.y + b.height / 2
        wrapper = ET.Element("g", {"transform": f"translate({fmt(-cx)} {fmt(-cy)})"})
        wrapper.append(copy.deepcopy(self.geometry.element))
        text = ET.tostring(wrapper, encoding="unicode")
        return text.replace(' xmlns="http://www.w3.org/2000/svg"', "").replace("ns0:", "")

    @_drawing_api(
        "anchors",
        purpose="节点替换：用自己写的 SVG 片段替换这个节点的外形，位置和所有连线/标签/挂载关系保持联动。",
        returns="当前 Node",
        semantics=(
            "svg 为一段 SVG 元素文本（可多个元素，可含 defs/渐变），坐标随意，自动按外接框居中；节点位置不变。",
            'fit="keep"（默认）等比缩放到原节点外接框内；fit="own" 保持片段原尺寸；也可传数值作为缩放倍数。',
            "第一个可见形状作为外轮廓（连线落点、contour_at、mount 用它）；ports 传 {名称: (x, y)}，坐标用片段自己的坐标。",
            "用于精修：先用部件或基础形状把图搭起来、连好线，再把需要更精细的对象逐个替换成手写 SVG。",
        ),
        example='nuc.replace_svg(\'<circle cx="0" cy="0" r="30" fill="#D9CDEA"/><circle cx="8" cy="-6" r="8" fill="#9B2D6F"/>\', ports={"pore": (30, 0)})',
        limits=("只接受可信的静态 SVG 片段；不支持脚本、外链图片和 <image>。",),
        rank=2,
    )
    def replace_svg(self, svg, *, fit="keep", ports=None):
        if fit == "own":
            scale = 1.0
        elif fit == "keep":
            old = self.geometry.bounds
            scale = (old.width, old.height)
        else:
            _finite(fit)
            scale = float(fit)
        self.geometry = svg_geometry(svg, scale=scale, ports=ports)
        if self.own_anchor == "origin":
            self.own_anchor = "center"
        return self

    @_drawing_api(
        "anchors",
        purpose="修改实例的旋转角度或等比缩放。",
        returns="当前 Node",
        semantics=(
            "rotation 是实例相对画布的绝对旋转角（度）；SVG 坐标 y 向下，正值为顺时针。",
            "scale 必须为正；数值是设置值，不是增量，绑定目标的变换不会自动叠加。",
            "位置目标和 own_anchor 保留，关联标签与端点在重新导出时更新。",
        ),
        example="body.set_transform(rotation=angle, scale=factor)",
        limits=(),
        common=False,
    )
    def set_transform(self, *, rotation=None, scale=None):
        if rotation is not None:
            _finite(rotation)
            self.rotation = float(rotation)
        if scale is not None:
            _finite(scale)
            if scale <= 0:
                raise ValueError("Scale must be positive")
            self.scale = float(scale)
        return self

    @property
    @_drawing_api(
        "anchors",
        purpose="读取当前实例在画布中的外接框。",
        returns="Box 快照",
        semantics=("读取时解析当前绑定；Box 本身不是动态引用。",),
        example="box = body.bounds",
        limits=(),
        common=False,
        is_property=True,
    )
    def bounds(self):
        return _Layout(self.drawing).bounds(self)


_CALLOUT_TEXT = {
    "fill": "fill",
    "color": "fill",
    "text_fill": "fill",
    "font_weight": "font_weight",
    "bold": "font_weight",
    "font_style": "font_style",
    "italic": "font_style",
    "text_anchor": "text_anchor",
    "letter_spacing": "letter_spacing",
    "opacity": "opacity",
    "line_height": "line_height",
}
_CALLOUT_LINE = {
    "stroke": "stroke",
    "line_color": "stroke",
    "stroke_width": "stroke_width",
    "line_width": "stroke_width",
    "stroke_dasharray": "stroke_dasharray",
    "stroke_linecap": "stroke_linecap",
    "stroke_opacity": "stroke_opacity",
}


_BOX_ANCHORS = {
    "origin",
    "center",
    "top_left",
    "top",
    "top_right",
    "left",
    "right",
    "bottom_left",
    "bottom",
    "bottom_right",
}


class _Layout:
    def __init__(self, drawing):
        self.drawing, self.cache, self.stack = drawing, {}, []

    def matrix(self, node):
        if node.key in self.cache:
            return self.cache[node.key]
        if node.key in self.stack:
            raise ValueError("Cyclic anchor binding: " + " -> ".join(self.stack + [node.key]))
        self.stack.append(node.key)
        try:
            _finite(node.rotation, node.scale)
            if node.scale <= 0:
                raise ValueError("Scale must be positive")
            base = rotate(node.rotation).then(scale(node.scale))
            if node.own_anchor == "origin":
                own = (0, 0)
            elif node.own_anchor.startswith("port:") or (
                node.own_anchor in node.geometry.ports and node.own_anchor not in _BOX_ANCHORS
            ):
                port = node.own_anchor[5:] if node.own_anchor.startswith("port:") else node.own_anchor
                if port not in node.geometry.ports:
                    raise ValueError(f"Unknown port {node.key}.{port}")
                own = base.point(*node.geometry.ports[port])
            else:
                own = node.geometry.bounds.transformed(base).anchor(node.own_anchor)
            target = self.point(node.target)
            matrix = translate(target[0] - own[0], target[1] - own[1]).then(base)
            self.cache[node.key] = matrix
            return matrix
        finally:
            self.stack.pop()

    def bounds(self, node):
        return node.geometry.bounds.transformed(self.matrix(node))

    def point(self, reference):
        self.drawing._check_ref(reference)
        if isinstance(reference, ContourAnchor):
            return self.frame(reference).point
        if isinstance(reference, Anchor):
            if reference.is_port:
                if reference.name not in reference.node.geometry.ports:
                    raise ValueError(f"Unknown port {reference.node.key}.{reference.name}")
                p = self.matrix(reference.node).point(*reference.node.geometry.ports[reference.name])
            elif reference.name == "origin":
                p = self.matrix(reference.node).point(0, 0)
            else:
                p = self.bounds(reference.node).anchor(reference.name)
            return p[0] + reference.offset[0], p[1] + reference.offset[1]
        if isinstance(reference, Edge):
            box = self.bounds(reference.node)
            target = self.point(reference.toward)
            cx, cy = box.anchor()
            dx, dy = target[0] - cx, target[1] - cy
            if abs(dx) + abs(dy) < 1e-12:
                return cx, cy
            ratios = [
                size / abs(delta) for size, delta in ((box.width / 2, dx), (box.height / 2, dy)) if abs(delta) > 1e-12
            ]
            t = min(ratios)
            extra = reference.clearance / math.hypot(dx, dy)
            return cx + (t + extra) * dx, cy + (t + extra) * dy
        if isinstance(reference, EdgeLabelAnchor):
            from ._labels import edge_label_center

            return edge_label_center(reference, self)
        return _point(reference)

    def frame(self, reference):
        self.drawing._check_ref(reference)
        if isinstance(reference, ContourAnchor):
            node = reference.node
            matrix = self.matrix(node)
            try:
                curve = node.geometry.contour(reference.subpath, tolerance=reference.tolerance)
            except ValueError:
                curve = _marked_outline(node.geometry, reference.subpath, reference.tolerance)
            if reference.fraction is not None:
                local = curve.frame(reference.fraction * curve.length, normal=reference.normal)
            else:
                target = self.point(reference.target)
                dx, dy = target[0] - matrix.e, target[1] - matrix.f
                det = matrix.a * matrix.d - matrix.b * matrix.c
                local_target = ((matrix.d * dx - matrix.c * dy) / det, (-matrix.b * dx + matrix.a * dy) / det)
                origin = reference.origin if reference.origin is not None else node.geometry.bounds.anchor()
                local = curve.ray(
                    origin,
                    (local_target[0] - origin[0], local_target[1] - origin[1]),
                    hit=reference.hit,
                    normal=reference.normal,
                )
            p = matrix.point(*local.point)
            p = (p[0] + reference.offset[0], p[1] + reference.offset[1])
            return PathFrame(
                p,
                _map_direction(matrix, local.tangent),
                _map_direction(matrix, local.normal),
                local.distance * node.scale,
            )
        if isinstance(reference, Anchor):
            if reference.is_port:
                direction = reference.node.geometry.port_directions.get(reference.name)
                if direction is None:
                    raise ValueError("Port has no direction; define it with a PathFrame")
                normal = _map_direction(self.matrix(reference.node), direction)
                tangent = _map_direction(
                    self.matrix(reference.node),
                    reference.node.geometry.port_tangents.get(reference.name, (direction[1], -direction[0])),
                )
            else:
                normals = {
                    "left": (-1, 0),
                    "right": (1, 0),
                    "top": (0, -1),
                    "bottom": (0, 1),
                    "top_left": (-1, -1),
                    "top_right": (1, -1),
                    "bottom_left": (-1, 1),
                    "bottom_right": (1, 1),
                }
                if reference.name not in normals:
                    raise ValueError("This anchor has no boundary direction")
                normal = _unit(normals[reference.name])
                tangent = (normal[1], -normal[0])
            return PathFrame(self.point(reference), tangent, normal, None)
        if isinstance(reference, Edge):
            p = self.point(reference)
            center = self.bounds(reference.node).anchor()
            normal = _unit((p[0] - center[0], p[1] - center[1]))
            return PathFrame(p, (normal[1], -normal[0]), normal, None)
        raise ValueError("A coordinate tuple has no direction")


@dataclass
class Connector:
    start: Anchor | Edge | Point
    end: Anchor | Edge | Point
    route: str
    style: dict
    waypoints: tuple = ()
    start_direction: object = None
    end_direction: object = None
    lead: float = 24
    avoid: tuple = ()
    clearance: float = 12
    bend: float = 0
    side: str = "bottom"

    def element(self, layout):
        a, b = layout.point(self.start), layout.point(self.end)
        if self.route == "loop":
            d = _loop_path(self, a, b, layout)
            return ET.Element("path", {"d": d, **_attrs({"fill": "none", "stroke": "#000000", **self.style})})
        if self.route == "arc":
            dx, dy = b[0] - a[0], b[1] - a[1]
            length = math.hypot(dx, dy) or 1
            cx = (a[0] + b[0]) / 2 - dy / length * self.bend * 2
            cy = (a[1] + b[1]) / 2 + dx / length * self.bend * 2
            d = f"M {fmt(a[0])} {fmt(a[1])} Q {fmt(cx)} {fmt(cy)} {fmt(b[0])} {fmt(b[1])}"
            return ET.Element("path", {"d": d, **_attrs({"fill": "none", "stroke": "#000000", **self.style})})
        if self.route in ("polyline", "bezier", "orthogonal"):
            from ._routing import routed_path

            def direction(value, endpoint):
                if value is None:
                    return None
                if isinstance(value, str):
                    return layout.frame(endpoint).normal
                if isinstance(value, (Anchor, Edge, ContourAnchor)):
                    return layout.frame(value).normal
                return _unit(value)

            obstacles = [layout.bounds(o) if isinstance(o, Node) else o for o in self.avoid]
            d = routed_path(
                a,
                b,
                [layout.point(p) for p in self.waypoints],
                direction(self.start_direction, self.start),
                direction(self.end_direction, self.end),
                self.lead,
                self.route,
                obstacles,
                self.clearance,
            )
        elif self.route == "straight":
            d = f"M {fmt(a[0])} {fmt(a[1])} L {fmt(b[0])} {fmt(b[1])}"
        elif self.route == "elbow":
            mid = (a[0] + b[0]) / 2
            d = f"M {fmt(a[0])} {fmt(a[1])} H {fmt(mid)} V {fmt(b[1])} H {fmt(b[0])}"
        elif self.route == "curve":
            mid = (a[0] + b[0]) / 2
            d = f"M {fmt(a[0])} {fmt(a[1])} C {fmt(mid)} {fmt(a[1])} {fmt(mid)} {fmt(b[1])} {fmt(b[0])} {fmt(b[1])}"
        else:
            raise ValueError(f"Unknown connector route {self.route!r}")
        return ET.Element("path", {"d": d, **_attrs({"fill": "none", "stroke": "#000000", **self.style})})


def _loop_path(connector, a, b, layout):
    """U-shaped return path: out of a on `side`, along a lane `lead` beyond every object between a and b, back into b."""
    drawing, side, lead = layout.drawing, connector.side, connector.lead
    axis = 1 if side in ("top", "bottom") else 0  # coordinate pushed outward
    sign = 1 if side in ("bottom", "right") else -1
    lo, hi = sorted((a[1 - axis], b[1 - axis]))
    level = max(a[axis] * sign, b[axis] * sign) + lead
    spans = []
    for node in drawing.nodes.values():
        if isinstance(node.target, EdgeLabelAnchor) and node.target.connector is connector:
            continue  # its own label sits outside the lane
        try:
            box = layout.bounds(node)
        except ValueError:
            continue
        if box.width * box.height >= 0.25 * drawing.width * drawing.height:
            continue  # backgrounds and panels
        across = (box.x, box.x + box.width) if axis == 1 else (box.y, box.y + box.height)
        if across[1] < lo or across[0] > hi:
            continue
        near, far = (box.y, box.y + box.height) if axis == 1 else (box.x, box.x + box.width)
        spans.append(tuple(sorted((near * sign, far * sign))))
    moved = True
    while moved:
        moved = False
        for s_near, s_far in spans:
            if s_near < level and s_far + lead > level + 1e-9:
                level, moved = s_far + lead, True
    lane = level * sign
    if axis == 1:
        pts = (a, (a[0], lane), (b[0], lane), b)
    else:
        pts = (a, (lane, a[1]), (lane, b[1]), b)
    return "M " + " L ".join(f"{fmt(x)} {fmt(y)}" for x, y in pts)


@_drawing_api(
    "anchors",
    purpose="创建自由放置对象的画布。",
    returns="Drawing",
    semantics=(
        "width/height 为正的源 SVG 尺寸；不附带背景、主题或布局模板。",
        "Geometry 是局部形状，加入 Drawing 后获得可绑定的 Node。",
    ),
    example="drawing = Drawing(width, height)",
    limits=(),
    rank=0,
)
class Drawing(SvgwriteAliases):
    """A free-positioned scene with live anchor dependencies and painter order."""

    def __init__(self, width, height):
        _finite(width, height)
        if min(width, height) <= 0:
            raise ValueError("Canvas dimensions must be positive")
        self.width, self.height = width, height
        self.nodes = {}
        self.items = []
        self.definitions = []
        self.keys = set()

    def _reserve(self, key):
        if not isinstance(key, str) or not key or not all(c.isalnum() or c in "_-" for c in key):
            if isinstance(key, str) and key and any(not c.isascii() or not (c.isalnum() or c in "_-") for c in key):
                raise ValueError(
                    f"key {key[:20]!r} 不是合法名字：第一个参数是 key（字母数字下划线），"
                    "正文请作为第二个参数 content 传入，如 d.callout('c1', '说明文字', target, at=...)"
                )
            raise ValueError("Object names use letters, numbers, underscores and hyphens")
        if key in self.keys:
            raise ValueError(f"Duplicate drawing object {key!r}")
        self.keys.add(key)

    def _check_ref(self, reference):
        if isinstance(reference, (Anchor, Edge, ContourAnchor)):
            if reference.node.drawing is not self:
                raise ValueError("Anchor belongs to another drawing")
        elif not isinstance(reference, EdgeLabelAnchor):
            _point(reference)

    @_drawing_api(
        "anchors",
        purpose="把局部几何加入画布。",
        returns="Node",
        semantics=(
            "key 为唯一对象名；geometry 为 Geometry；at 可传坐标或动态引用。",
            "默认把图形的局部原点放到 at：ellipse/circle/parts（cell、atom、particle、receptor…）原点在中心，rect/label/text_box/lattice/layer_stack 原点在左上角。",
            '不确定时显式写 own_anchor="center" 或 "top_left"；*_at 快捷函数一律按中心。',
            "调用顺序决定绘制顺序。",
        ),
        example="body = drawing.add(name, cell(60, 40), at=(300, 200))   # parts 原点在中心：细胞中心在 (300, 200)",
        limits=(),
        rank=1,
    )
    def add(self, key, geometry, *, at=(0, 0), own_anchor="origin"):
        if not isinstance(geometry, Geometry):
            raise TypeError("Expected Geometry")
        self._check_ref(at)
        self._reserve(key)
        node = Node(self, key, geometry, at, own_anchor)
        self.nodes[key] = node
        self.items.append((key, node))
        return node

    @_drawing_api(
        "connect",
        purpose="建立端点随对象更新的连线。",
        returns="Connector",
        semantics=(
            "start/end/waypoints 可为 Anchor、ContourAnchor、Edge 或固定坐标；动态位置在导出时重算。",
            "旧路由 straight/elbow/curve 保持原行为；polyline 经过指定路点，bezier 平滑经过路点。",
            'start_direction/end_direction 可传画布向量、方向端口或 "normal"（读取对应端点法线）；方向指向对象外部。',
            "lead 是端点引出距离或 Bezier 控制手柄上限，默认 24；bezier 可能过冲，不承诺避障。",
            "orthogonal 在路点之间求轴向路线，使中心线避开 avoid 中的 Box/Node 外接框并留 clearance 间距；粗描边需额外预留半线宽。最多 32 个障碍、64 个路点。",
            "avoid 不含起终点所在对象；起点/终点/路点进入障碍或引出线穿过障碍时会报错。",
            'route="loop" 画反馈/回路：从 start 沿 side（bottom/top/left/right）引出，在两端之间所有对象外侧 lead 处走一条通道，再折回 end（U 形三段，随对象移动重算）。',
            'label="文字"（或 label(...) 几何）在连线中点沿法线放到线外空白处，随连线移动、参与 check()；label_side 可指定 above/below/left/right，label_size 为字号（默认 14）；标签名为 key+"-label"。',
        ),
        example='drawing.connect(name, start, end, route="orthogonal",\n                start_direction="normal", avoid=obstacles, **line_paint)\n'
        'd.arrow(last, first, route="loop", side="bottom", dashed=True, label="负反馈")   # 链条下方的回路',
        limits=("只对指定矩形区域避障，不进行全局布局；法线引出段可为斜线，中间 orthogonal 路段为水平/垂直。",),
        style=True,
    )
    def connect(
        self,
        key,
        start,
        end,
        *,
        route="straight",
        waypoints=(),
        start_direction=None,
        end_direction=None,
        lead=24,
        avoid=(),
        clearance=12,
        bend=0,
        side="bottom",
        label=None,
        label_side=None,
        label_size=14,
        **style,
    ):
        self._check_ref(start)
        self._check_ref(end)
        waypoints = tuple(waypoints)
        avoid = tuple(avoid)
        _finite(lead, clearance, bend)
        if lead <= 0 or clearance < 0:
            raise ValueError("lead must be positive and clearance nonnegative")
        if len(waypoints) > 64 or len(avoid) > 32:
            raise ValueError("Routing supports at most 64 waypoints and 32 obstacles")
        if route not in ("straight", "elbow", "curve", "polyline", "bezier", "orthogonal", "arc", "loop"):
            raise ValueError("Unknown connector route; use straight/elbow/curve/arc/polyline/bezier/orthogonal/loop")
        if route == "loop" and side not in ("top", "bottom", "left", "right"):
            raise ValueError("loop side must be top/bottom/left/right")
        if route in ("straight", "elbow", "curve", "arc", "loop") and (
            waypoints or start_direction is not None or end_direction is not None or avoid
        ):
            raise ValueError("Guidance requires polyline, bezier or orthogonal routing")
        if avoid and route != "orthogonal":
            raise ValueError("avoid is supported only for orthogonal routing")
        for waypoint in waypoints:
            self._check_ref(waypoint)
        for direction in (start_direction, end_direction):
            if direction is None:
                continue
            if isinstance(direction, str):
                if direction != "normal":
                    raise ValueError("Direction string must be normal")
            elif isinstance(direction, (Anchor, Edge, ContourAnchor)):
                self._check_ref(direction)
            else:
                _unit(direction)
        for obstacle in avoid:
            if isinstance(obstacle, Node):
                if obstacle.drawing is not self:
                    raise ValueError("Obstacle belongs to another drawing")
            elif not isinstance(obstacle, Box):
                raise TypeError("Avoidance regions must be Box or Node")
        self._reserve(key)
        connector = Connector(
            start, end, route, style, waypoints, start_direction, end_direction, lead, avoid, clearance, bend, side
        )
        self.items.append((key, connector))
        if label is not None:
            self._edge_label(key, connector, label, label_side, label_size)
        return connector

    def _edge_label(self, key, connector, content, side, size):
        """Label node bound to the connector's midpoint, on the clearer side; it follows the line."""
        from ._labels import edge_label_anchor

        geometry = content if isinstance(content, Geometry) else label(str(content), font_size=size, fill="#1E191C")
        if side is None and connector.route == "loop":
            side = connector.side  # a feedback label reads outside its loop
        node = self.add(
            key + "-label", geometry, at=edge_label_anchor(self, connector, geometry, side), own_anchor="center"
        )
        node.edge_of = key
        connector.label_node = node
        return node

    @_drawing_api(
        "connect",
        purpose="组合关联标签与引导线。",
        returns="标签 Node",
        semantics=(
            "content 为文字；target 是标注指向；at 是标签位置或动态引用；font_size 必填。",
            "label_style 与 line_style 分别控制文字和线；leader_gap 控制线端与文字框间距。",
            "也可直接传常用样式：fill/color、font_weight/bold、font_style 给文字，line_color/stroke、line_width/stroke_width、dashed 给引导线。",
            '返回的标签 Node 可继续 pin；同时占用 key 和 key+"-leader" 两个名字。',
        ),
        example="note = drawing.callout(name, text, target, at=position, font_size=size,\n                       fill=ink, bold=True, line_color=line, line_width=1.2)",
        limits=("标签位置由调用方决定；不自动寻找空白区域或避开所有对象。",),
    )
    def callout(
        self,
        key,
        content,
        target,
        *,
        at,
        font_size,
        font_family=None,
        own_anchor="top_left",
        route="elbow",
        leader_gap=5,
        label_style=None,
        line_style=None,
        **style,
    ):
        label_style, line_style = dict(label_style or {}), dict(line_style or {})
        for name, value in style.items():
            if name in _CALLOUT_TEXT:
                label_style[_CALLOUT_TEXT[name]] = (
                    "bold"
                    if name == "bold" and value is True
                    else "italic"
                    if name == "italic" and value is True
                    else value
                )
            elif name in _CALLOUT_LINE:
                line_style[_CALLOUT_LINE[name]] = value
            elif name == "dashed":
                if value:
                    line_style.setdefault("stroke_dasharray", "4 3")
            else:
                raise TypeError(
                    f"callout() got an unexpected keyword {name!r}; text: {', '.join(_CALLOUT_TEXT)}; "
                    f"leader: {', '.join(_CALLOUT_LINE)}, dashed; or pass label_style={{...}} / line_style={{...}}"
                )
        if label_style.get("font_weight") is False:
            label_style.pop("font_weight")
        if label_style.get("font_style") is False:
            label_style.pop("font_style")
        note = self.add(
            key,
            label(content, font_size=font_size, font_family=font_family, **label_style),
            at=at,
            own_anchor=own_anchor,
        )
        if isinstance(target, Node):  # point at the part's box edge facing the label, as d.arrow does
            target = target.edge_toward(note.anchor("center"))
        self.connect(key + "-leader", target, note.edge_toward(target, clearance=leader_gap), route=route, **line_style)
        # Draw the leader first so the label can cover any endpoint antialiasing.
        self.items[-2], self.items[-1] = self.items[-1], self.items[-2]
        return note

    @_drawing_api(
        "resources",
        purpose="加入自定义 SVG 资源定义。",
        returns="None",
        semantics=(
            "xml 可为 XML 字符串或 Element，接受单个资源或 defs 包装；此操作修改画布。",
            '资源 ID 保持唯一；几何样式可使用 fill="url(#id)" 等引用。',
        ),
        example="drawing.add_defs(resource_xml)",
        limits=("接口不生成主题或自动构造渐变；资源兼容范围见 SVG 写作指南。",),
    )
    def add_defs(self, xml):
        node = ET.fromstring(xml) if isinstance(xml, str) else copy.deepcopy(xml)
        self.definitions.extend(list(node) if node.tag.split("}")[-1] == "defs" else [node])

    @_drawing_api(
        "anchors",
        purpose="读取当前引用对应的坐标。",
        returns="Point 快照",
        semantics=("结果是当前 (x, y)，之后不会自动更新。要保持联动，应直接传 Anchor/Edge，避免先 resolve 再绑定。",),
        example='point = drawing.resolve(body.port("outlet"))',
        limits=(),
        common=False,
    )
    def resolve(self, reference):
        return _Layout(self).point(reference)

    @_drawing_api(
        "anchors",
        purpose="读取动态端口的画布位置与方向。",
        returns="PathFrame 快照",
        semantics=(
            "返回 point/tangent/normal/distance；轮廓端口的 distance 为画布弧长，命名端口/框边缘为 None。",
            "轮廓端口和有方向的命名端口跟随实例变换。",
            "外接框边缘锚点提供画布轴向法线；普通坐标、center/origin 或无方向的命名端口会报错。",
        ),
        example="frame = drawing.resolve_frame(port)",
        common=False,
    )
    def resolve_frame(self, reference):
        return _Layout(self).frame(reference)

    @_drawing_api(
        "inspect",
        purpose="按对象查询布局框、端口位置和绘制顺序。",
        returns="dict（可 JSON 序列化）",
        semantics=(
            "不传 keys 返回全部对象的简短概览；传对象名时补充笔迹边界、端口方向和连线路径。",
            "所有坐标是当前 SVG 画布快照；错误按对象返回，便于定位循环绑定或缺失端口。",
            "overlaps=True 计算所查询对象间的外接框交叠候选，不等于真实笔迹遮挡。",
            "此处的布局/笔迹框不同于 Slides 选择框；转换结果用 inspect_svg 查询。",
        ),
        example='report = drawing.inspect("body", "wire", overlaps=True)',
    )
    def inspect(self, *keys, overlaps=False):
        from ._inspection import inspect_drawing

        return inspect_drawing(self, keys, overlaps)

    @_drawing_api(
        "inspect",
        purpose="给出少量标注位置候选及遮挡信息。",
        returns="list[dict]",
        semantics=(
            "label_geometry 可由 label/wrap_label 生成；target 为画布点或动态引用。",
            "返回八个方位的 at/offset/own_anchor、越界面积与指定 avoid 区域的框交叠面积，按分数排序。",
            '不自动放置或选定候选。结果是快照；Anchor/ContourAnchor 可用 shifted(*offset) 联动，再以 own_anchor="top_left" 放置。',
            "avoid 接收 Box/Node；全部候选都拥挤时仍返回分数，供模型改变位置或布局。",
        ),
        example="choices = drawing.label_candidates(note_geometry, target, avoid=nearby_objects)",
        common=False,
    )
    def label_candidates(self, label_geometry, target, *, avoid=(), gap=12):
        from ._inspection import label_candidates

        return label_candidates(self, label_geometry, target, avoid, gap)

    @_drawing_api(
        "layout",
        purpose="自动选择不遮挡的位置放置标签。",
        returns="标签 Node",
        semantics=(
            "target 为 Anchor/ContourAnchor/坐标；在 sides 给出的方位（默认八方位）中选择与其他对象、连线和画布边界冲突最小的位置。",
            "avoid 省略时避让调用时画布中已有的全部对象与连线；之后再加的对象不在考虑内。传 Box/Node 列表则只避让这些区域。gap 为标签与目标的距离。",
            "目标为 Anchor 时标签保持联动；placement 的 clear=True 只表示放置时无冲突。全部画完后调用 relayout_labels() 按最终画面重排并返回最终结果。",
        ),
        example='note = drawing.place_label(name, label(text, font_size=size, **paint), node.port("top"))',
        limits=("只在给定方位中选择，不移动其他对象；全部方位都拥挤时仍选最优并在 placement 中如实记录。",),
        rank=60,
    )
    def place_label(self, key, geometry, target, *, avoid=None, gap=8, sides=None):
        self._check_ref(target)
        from ._labels import place_label

        return place_label(self, key, geometry, target, avoid, gap, sides)

    @_drawing_api(
        "layout",
        purpose="为一条已有连线自动放置标签。",
        returns="标签 Node",
        semantics=(
            "connector_key 为 connect 时的名字；在连线中段两侧选择位置，标签不压在线上，也避开其他对象与连线。",
            "position 为 0–1 的弧长比例，省略时依次尝试 0.5/0.4/0.6/0.3/0.7；gap 为标签与线的距离。",
            "返回 Node 的 placement 记录遮挡面积与压线数；标签位置是当前连线的快照，改动端点后重新调用。",
        ),
        example='drawing.connect("e1", a.port("right"), b.port("left"), route="orthogonal", **line_paint)\n'
        'drawing.label_connector("e1-label", "e1", label("激活", font_size=size, **paint))',
        limits=("只沿该连线两侧选择；拥挤时选择冲突最小的位置并如实记录。",),
        rank=61,
    )
    def label_connector(self, key, connector_key, geometry, *, avoid=None, gap=4, position=None):
        from ._labels import label_connector

        return label_connector(self, key, connector_key, geometry, avoid, gap, position)

    @_drawing_api(
        "layout",
        purpose="全部对象画完后，按最终画面重新放置所有自动标签并报告冲突。",
        returns="dict（标签名 → 冲突情况）",
        semantics=(
            "对 place_label / label_connector 放过的每个标签，避让其后新增的对象、连线和其他标签，重新选位；可迭代 rounds 轮。",
            "返回每个标签的 overlap_area、line_hits、outside_area 与 clear；clear 为 False 时说明当前布局放不下，需要调整对象位置或文字。",
            "在 write/to_svg 之前调用一次即可；只移动标签，不移动其他对象。",
        ),
        example='report = drawing.relayout_labels()\nblocked = [k for k, r in report.items() if not r["clear"]]',
        limits=("启发式选位；拥挤时如实报告，不保证全部 clear。",),
        rank=62,
    )
    def relayout_labels(self, *, rounds=2):
        from ._labels import relayout_labels

        return relayout_labels(self, rounds)

    @_drawing_api(
        "layout",
        purpose="按当前画面检查所有自动标签是否被遮挡或压线。",
        returns="dict（标签名 → 冲突情况）",
        semantics=("只读查询，不移动对象；与 relayout_labels 返回同样的字段。",),
        example="report = drawing.check_labels()",
        common=False,
        rank=63,
    )
    def check_labels(self):
        from ._labels import check_labels

        return check_labels(self)

    @_drawing_api(
        "export",
        purpose="解析绑定并生成普通 SVG。",
        returns="str",
        semantics=(
            "每次调用都重新计算位置关系；不写文件，也不写入 Slides。",
            "导出后不会保留 Python 的实时约束；后续修改需要重新导出。",
            "放进幻灯片不要用它手拼 <embed>（嵌套 transform 会被判越界、文字不可编辑）——用 d.to_slide(x=, y=, width=) 交给 publish_slide。",
        ),
        example="svg = drawing.to_svg()",
        limits=("循环依赖、缺失端口、重复资源 ID 等问题会报错。",),
    )
    def to_svg(self):
        layout = _Layout(self)
        root = ET.Element(
            "svg",
            {
                "xmlns": "http://www.w3.org/2000/svg",
                "data-drawing-lib": "1",
                "viewBox": f"0 0 {fmt(self.width)} {fmt(self.height)}",
            },
        )
        if self.definitions:
            definitions = ET.SubElement(root, "defs")
            definitions.extend(copy.deepcopy(self.definitions))
        for index, (key, item) in enumerate(self.items):
            if isinstance(item, Node):
                node = ET.SubElement(root, "g", {"id": key, "transform": layout.matrix(item).svg()})
                node.append(_scoped(item.geometry.element, f"object-{index}"))
            else:
                node = item.element(layout)
                node.set("id", key)
                root.append(node)
        ids = [n.get("id") for n in root.iter() if n.get("id")]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate SVG resource/object IDs")
        return ET.tostring(root, encoding="unicode")

    @_drawing_api(
        "export",
        purpose="一次渲染预览 PNG（按画布比例，不裁白边），用于整体看一眼示意图。",
        returns="Path（PNG）",
        semantics=(
            "width 为输出像素宽；依次尝试 rsvg-convert、cairosvg、qlmanage，都没有时抛错。",
            "每张示意图最多预览一次：排版问题优先看 d.check() / d.summary()，不要反复渲染迭代。",
        ),
        example='d.preview("p05_preview.png")',
        rank=3,
    )
    def preview(self, path, *, width=1200):
        import shutil, subprocess, tempfile

        out = Path(path)
        with tempfile.TemporaryDirectory() as tmp:
            svg = self.write(Path(tmp) / "preview.svg")
            if shutil.which("rsvg-convert"):
                subprocess.run(
                    ["rsvg-convert", "-w", str(int(width)), "-b", "white", str(svg), "-o", str(out)], check=True
                )
                return out
            try:
                import cairosvg

                cairosvg.svg2png(url=str(svg), write_to=str(out), output_width=int(width), background_color="white")
                return out
            except ImportError:
                pass
            if shutil.which("qlmanage"):
                subprocess.run(
                    ["qlmanage", "-t", "-s", str(int(width)), "-o", tmp, str(svg)], check=True, capture_output=True
                )
                png = Path(tmp) / "preview.svg.png"
                h = round(width * self.height / self.width)
                if shutil.which("sips"):  # Quick Look pads to a square; crop back to the canvas ratio
                    subprocess.run(["sips", "-c", str(h), str(int(width)), str(png)], check=True, capture_output=True)
                shutil.move(str(png), out)
                return out
        raise RuntimeError("no SVG renderer found (rsvg-convert / cairosvg / qlmanage)")

    @_drawing_api(
        "export",
        purpose="将解析后的 SVG 写入本地路径。",
        returns="Path",
        semantics=(
            "path 指向输出文件；父目录需已存在，同名文件会被覆盖。",
            "仍需通过 atomize_svg_to_slide 转为 Slides 对象，并设置对应的 mapping。",
        ),
        example="svg_path = drawing.write(output_path)",
        limits=(),
    )
    def write(self, path):
        path = Path(path)
        path.write_text(self.to_svg(), encoding="utf-8")
        return path

    _AT = dict(own_anchor="center")

    @staticmethod
    def _tag(kind, node):
        node.kind = kind  # what the author used, for review(): box/rect/ellipse/text are primitives
        return node

    def _auto(self, prefix):
        i = len(self.keys)
        while f"{prefix}{i}" in self.keys:
            i += 1
        return f"{prefix}{i}"

    @_drawing_api(
        "parts",
        purpose="把部件“立”在轮廓上：底部端口贴住轮廓点，并按外法线旋转（受体插膜、探针贴表面）。",
        returns="Node",
        semantics=(
            'on 为 node.contour_at(t, normal="outward") 或 contour_toward(...)；base 为部件上贴住轮廓的端口名（默认 tail）。',
            "部件默认竖直、head 朝上；inset 为沉入轮廓的距离（正值嵌入膜内）。",
        ),
        example='for t in (0.05, 0.12, 0.2):\n    d.mount(receptor(color="#9B2D6F"), on=cell_node.contour_at(t, normal="outward"), inset=6)',
        rank=0,
    )
    def mount(self, geometry, *, on, base="tail", inset=0.0, key=None):
        frame = _Layout(self).frame(on)
        nx, ny = frame.normal
        angle = math.degrees(math.atan2(nx, -ny))
        point = (frame.point[0] - nx * inset, frame.point[1] - ny * inset)
        node = self.add(
            key or self._auto("part"), geometry, at=point, own_anchor=base if base in geometry.ports else "bottom"
        )
        host = getattr(on, "node", None)
        node.mounted_on = host.key if host is not None else None  # intended contact, not an overlap
        node.kind = "part"
        return node.set_transform(rotation=angle)

    @_drawing_api(
        "parts",
        purpose="放部件、任意 Geometry 或一段手写 SVG，以中心对齐 at（与 *_at 一致）。",
        returns="Node",
        semantics=(
            "geometry 可为部件/Geometry，也可直接传 SVG 片段字符串（坐标随意，自动居中）；anchor 默认 center。",
            "svg= 在放部件的同时把外形换成手写 SVG：尺寸缩放到该部件的外框内，部件的位置与连线关系不变（等价于 place 后 replace_svg）。",
            "size= 给手写 SVG 指定外框（数值或 (w, h)）；ports= 为手写 SVG 声明接口（片段自身坐标）。",
        ),
        example="t = d.place(cell(140, 90, fill=SOFT, membrane=MAIN), at=(220, 200))\n"
        'tu = d.place(\'<path d="M-90 0 C-90-60 90-60 90 0 C90 50-90 50-90 0Z" fill="#F7ECE6" stroke="#A34450"/>\', at=(520, 200), size=(180, 120))',
        rank=0,
    )
    def place(
        self, geometry, *, at=None, center=None, insert=None, key=None, anchor="center", svg=None, size=None, ports=None
    ):
        kind, at = _position("place", at, center, insert)
        if kind == "insert":
            anchor = "top_left"
        if isinstance(geometry, str):
            geometry = svg_geometry(geometry, size=size, ports=ports)
        elif svg is not None:
            b = geometry.bounds
            geometry = svg_geometry(svg, scale=(b.width, b.height) if size is None else 1.0, size=size, ports=ports)
        else:
            b = geometry.bounds
            cx, cy = b.x + b.width / 2, b.y + b.height / 2
            if anchor == "center" and max(abs(cx) - b.width / 2, abs(cy) - b.height / 2) > 20:
                import warnings

                warnings.warn(
                    f"[drawing] place(): this geometry is built in canvas coordinates (its centre is at "
                    f"({cx:.0f}, {cy:.0f})), but place() moves its centre to at={at}. To keep canvas coordinates "
                    f"(membrane(path), circular_arc, polylines…) use d.add(key, geometry) instead.",
                    stacklevel=2,
                )
        return self._tag("part", self.add(key or self._auto("part"), geometry, at=at, own_anchor=anchor))

    @_drawing_api(
        "shapes",
        purpose="一步放入一段手写 SVG 作为节点（中心对齐 at），连线、标签、mount 都落在它的外轮廓上。",
        returns="Node",
        semantics=(
            "svg 为 SVG 元素片段（可多个元素、可含 defs 渐变），坐标随意，自动按外接框居中；第一个可见形状作为外轮廓。",
            "size 为外框（数值或 (w, h)），省略时保持原尺寸；ports 为 {名称: (x, y)}，用片段自身坐标。",
            "库里没有、或部件不贴合内容的对象，直接用它画成教科书级外形，再像其他节点一样 arrow/callout/mount。",
        ),
        example='mito = d.svg_at((300, 200), \'<rect x="-40" y="-16" width="80" height="32" rx="16" fill="#F2C9B5" stroke="#B3593A"/>\'\n'
        '                \'<path d="M-28 0 l8 -9 l8 18 l8 -18 l8 18 l8 -9" fill="none" stroke="#B3593A"/>\', size=(90, 36))',
        rank=7,
    )
    def svg_at(self, at=None, svg=None, *, center=None, insert=None, size=None, ports=None, key=None, anchor="center"):
        kind, at = _position("svg_at", at, center, insert)
        if kind == "insert":
            anchor = "top_left"
        if svg is None:
            raise TypeError("svg_at(): svg= (an SVG fragment string) is required")
        return self._tag(
            "svg",
            self.add(key or self._auto("svg"), svg_geometry(svg, size=size, ports=ports), at=at, own_anchor=anchor),
        )

    @_drawing_api(
        "shapes",
        purpose="一步创建矩形并加入画布（中心对齐 at）。",
        returns="Node",
        semantics=('等价于 add(key, rect(w, h, rx=rx, **style), at=at, own_anchor="center")；key 省略时自动命名。',),
        example='cell = d.rect_at((450, 260), 300, 160, rx=40, fill="#F3EEF8", stroke="#9A88C9")',
        rank=2,
    )
    def rect_at(
        self,
        at=None,
        width=None,
        height=None,
        *,
        center=None,
        insert=None,
        size=None,
        key=None,
        rx=0,
        anchor="center",
        **style,
    ):
        kind, at = _position("rect_at", at, center, insert)
        if kind == "insert":
            anchor = "top_left"
        if size is not None:
            width, height = size
        if width is None or height is None:
            raise TypeError("rect_at(): pass width, height (or size=(w, h))")
        from ._geometry import rect

        return self._tag(
            "rect", self.add(key or self._auto("rect"), rect(width, height, rx=rx, **style), at=at, own_anchor=anchor)
        )

    @_drawing_api(
        "shapes",
        purpose="一步创建圆/椭圆并加入画布（圆心 at）。",
        returns="Node",
        semantics=("ry 省略时为圆；返回的 Node 可用 contour_at / contour_toward 取轮廓上的点。",),
        example='nuc = d.ellipse_at((450, 260), 60, 40, fill="#E9DDF2")',
        rank=3,
    )
    def ellipse_at(self, at=None, rx=None, ry=None, *, center=None, r=None, key=None, **style):
        _, at = _position("ellipse_at", at, center, None)
        if r is not None:
            rx, ry = (r, r) if isinstance(r, (int, float)) else r
        if rx is None:
            raise TypeError("ellipse_at(): pass rx (and ry), or r=")
        from ._geometry import ellipse

        return self._tag(
            "ellipse", self.add(key or self._auto("ellipse"), ellipse(rx, ry, **style), at=at, own_anchor="center")
        )

    @_drawing_api(
        "shapes",
        purpose="一步加入任意 SVG 路径（画布坐标）。",
        returns="Node",
        semantics=("d 直接使用画布坐标，不再平移；可写 M/L/C/Q/A/Z。",),
        example='d.path_at("M 100 300 C 200 200 300 400 400 300", stroke="#5B1061", fill="none")',
        rank=4,
    )
    def path_at(self, d, *, key=None, **style):
        from ._geometry import path

        return self.add(key or self._auto("path"), path(d, **style), at=(0, 0))

    @_drawing_api(
        "shapes",
        purpose="一步加入文字（at 为锚点，默认居中）。",
        returns="Node",
        semantics=(
            "anchor 为 Node 对齐点（center/left/right/top/...）；也接受 start/middle/end（=左/中/右对齐于 at，并设置 text-anchor）；多行用 \\n。",
        ),
        example='d.text_at((450, 40), "PD-1 抑制 T 细胞活化", font_size=20, fill="#2A1A4A", font_weight="bold")',
        rank=5,
    )
    def text_at(
        self, at=None, content=None, *, center=None, insert=None, font_size=16, key=None, anchor="center", **style
    ):
        if insert is not None:
            if at is not None or center is not None:
                raise TypeError("text_at(): pass at=/center= (centre) or insert= (baseline start), not both")
            return self.text(
                content,
                insert=insert,
                font_size=font_size,
                key=key,
                text_anchor=style.pop("text_anchor", "start"),
                **style,
            )
        _, at = _position("text_at", at, center, None)
        if content is None:
            raise TypeError("text_at(): text content is required")
        # Accept SVG text-anchor words (start/middle/end) and left/right as horizontal alignment at `at`.
        aliases = {
            "start": ("left", "start"),
            "left": ("left", "start"),
            "middle": ("center", "middle"),
            "end": ("right", "end"),
            "right": ("right", "end"),
        }
        if anchor in aliases:
            anchor, text_anchor = aliases[anchor]
            style.setdefault("text_anchor", text_anchor)
        return self._tag(
            "text",
            self.add(key or self._auto("text"), label(content, font_size=font_size, **style), at=at, own_anchor=anchor),
        )

    @_drawing_api(
        "shapes",
        purpose="一步加入按文字自适应大小的节点框（带 top/bottom/left/right 端口）。",
        returns="Node",
        semantics=(
            "fill/stroke/rx 作用在框上，text_fill 为文字颜色；max_width 控制换行。",
            '连线可用 node.port("right") 或直接把 Node 传给 arrow/line，自动落在框的轮廓上。',
        ),
        example='shp2 = d.box_at((620, 300), "SHP-2", font_size=16, fill="#9B2D6F", text_fill="#FFFFFF", rx=18)',
        rank=6,
    )
    def box_at(
        self,
        at=None,
        content=None,
        *,
        center=None,
        insert=None,
        font_size=16,
        key=None,
        max_width=None,
        padding=(12, 8),
        shape="rect",
        rx=8,
        fill="none",
        stroke="none",
        stroke_width=1,
        text_fill="#1E191C",
        anchor="center",
        **text_style,
    ):
        kind, at = _position("box_at", at, center, insert)
        if kind == "insert":
            anchor = "top_left"
        if content is None:
            raise TypeError("box_at(): text content is required")
        from ._labels import text_box

        geometry = text_box(
            content,
            font_size=font_size,
            max_width=max_width,
            padding=padding,
            shape=shape,
            rx=rx,
            box_style=dict(fill=fill, stroke=stroke, stroke_width=stroke_width),
            fill=text_fill,
            **text_style,
        )
        return self._tag("box", self.add(key or self._auto("box"), geometry, at=at, own_anchor=anchor))

    def _endpoint(self, value, other):
        if isinstance(value, Node):
            target = other.anchor("center") if isinstance(other, Node) else other
            try:
                ref = value.contour_toward(target)
                _Layout(self).point(ref)
                return ref
            except ValueError:
                return value.edge_toward(target)
        return value

    @_drawing_api(
        "connect",
        purpose="一步画连线：Node 端点自动落在轮廓上，可带激活箭头/抑制横杠/结合圆点。",
        returns="Connector",
        semantics=(
            "start/end 可传 Node（自动取朝向对方的轮廓交点）、port/contour 引用或坐标。",
            "head 为 arrow / inhibit / dot / diamond / open_arrow / None；tail 同理（起点端）。",
            "curve>0 时画向左弯的二次曲线（值为弯曲高度，负值向右）；route 可用 orthogonal/elbow/bezier。",
            'route="loop", side="bottom"（top/left/right）画反馈回路：从两端对象的同一侧引出，绕到其间所有对象外侧再折回，lead 为离对象的距离。',
            'label="文字" 把边标签放在连线中点外侧空白处（label_side=above/below/left/right 可指定），随连线移动；不要自己 text_at 摆在箭头旁。',
            "dashed=True 画虚线（如反馈、间接作用）。marker 资源自动注册，颜色跟随 stroke。",
        ),
        example='d.arrow(pd1, shp2, stroke="#9B2D6F", stroke_width=2, label="招募")\n'
        'd.arrow(shp2, cd28, head="inhibit", stroke="#C0392B", curve=40)\n'
        'd.arrow(c, a, route="loop", side="bottom", dashed=True, label="负反馈")',
        rank=7,
    )
    def arrow(
        self,
        start,
        end,
        *,
        key=None,
        head="arrow",
        tail=None,
        curve=0,
        route="straight",
        dashed=False,
        stroke="#333333",
        stroke_width=2,
        head_size=None,
        side="bottom",
        label=None,
        label_side=None,
        label_size=14,
        **style,
    ):
        key = key or self._auto("link")
        link = self._arrow_link(
            start, end, key, head, tail, curve, route, dashed, stroke, stroke_width, head_size, side, style
        )
        if label is not None:
            self._edge_label(key, link, label, label_side, label_size)
        return link

    def _arrow_link(
        self, start, end, key, head, tail, curve, route, dashed, stroke, stroke_width, head_size, loop_side, style
    ):
        from ._markers import marker, _ALIASES, _KINDS

        a, b = self._endpoint(start, end), self._endpoint(end, start)
        paint = dict(stroke=stroke, stroke_width=stroke_width, fill="none", **style)
        if dashed:
            paint.setdefault("stroke_dasharray", f"{fmt(stroke_width * 3)} {fmt(stroke_width * 2.5)}")
        size = head_size or max(7.0, stroke_width * 4.5)
        bar = head_size or max(12.0, stroke_width * 6)  # an inhibition T-bar must read clearly wider than the line
        for end_name, kind in (("marker_end", head), ("marker_start", tail)):
            if not kind:
                continue
            k = _ALIASES.get(kind, kind)
            if k not in _KINDS:
                raise ValueError(f"Unknown head {kind!r}; use one of {sorted(_KINDS)}")
            msize = bar if k == "inhibit" else size
            mid = f"m-{k}-{_color_id(stroke)}-{fmt(msize).replace('.', '_')}"
            if not any(e.get("id") == mid for e in self.definitions):
                self.add_defs(marker(k, color=stroke, size=msize, id=mid))
            paint[end_name] = f"url(#{mid})"
        if route == "loop":
            a = start.anchor(loop_side) if isinstance(start, Node) else a
            b = end.anchor(loop_side) if isinstance(end, Node) else b
            return self.connect(key, a, b, route="loop", side=loop_side, **paint)
        if route in ("orthogonal", "elbow") and (isinstance(start, Node) or isinstance(end, Node)):
            layout = _Layout(self)

            def side(node, toward):
                nb = layout.bounds(node)
                c = nb.anchor("center")
                if isinstance(toward, Node):
                    tb = layout.bounds(toward)
                    t = tb.anchor("center")
                    # Boxes stacked in different rows connect top/bottom (flowcharts, trees) even when far apart sideways.
                    if nb.y + nb.height <= tb.y or tb.y + tb.height <= nb.y:
                        return "bottom" if t[1] > c[1] else "top"
                    if nb.x + nb.width <= tb.x or tb.x + tb.width <= nb.x:
                        return "right" if t[0] > c[0] else "left"
                else:
                    t = layout.point(toward)
                dx, dy = t[0] - c[0], t[1] - c[1]
                return ("right" if dx > 0 else "left") if abs(dx) >= abs(dy) else ("bottom" if dy > 0 else "top")

            a = start.anchor(side(start, end)) if isinstance(start, Node) else a
            b = end.anchor(side(end, start)) if isinstance(end, Node) else b
            if route == "orthogonal":
                normals = {"right": (1, 0), "left": (-1, 0), "bottom": (0, 1), "top": (0, -1)}
                sd = normals[a.name] if isinstance(start, Node) else None
                ed = normals[b.name] if isinstance(end, Node) else None
                if "avoid" not in style:
                    # Route around the other boxes on the canvas so a link never runs through an unrelated node;
                    # nodes touching either endpoint (a receptor on its cell) are not obstacles.
                    ends = [n for n in (start, end) if isinstance(n, Node)]
                    eb = [layout.bounds(n).padded(4) for n in ends]
                    hit = lambda q: any(
                        q.x < e.x + e.width and e.x < q.x + q.width and q.y < e.y + e.height and e.y < q.y + q.height
                        for e in eb
                    )
                    others = [
                        n
                        for n in self.nodes.values()
                        if n not in ends
                        and not hit(layout.bounds(n))
                        and layout.bounds(n).width * layout.bounds(n).height < 0.25 * self.width * self.height
                    ]
                    if others:
                        try:
                            link = self.connect(
                                key,
                                a,
                                b,
                                route="orthogonal",
                                start_direction=sd,
                                end_direction=ed,
                                avoid=others[:32],
                                **paint,
                            )
                            from ._labels import _connector_points

                            _connector_points(link, _Layout(self))  # routing errors surface only when resolved
                            return link
                        except ValueError:
                            self.items = [(k, v) for k, v in self.items if k != key]  # no clear lane: plain route
                            self.keys.discard(key)
                return self.connect(key, a, b, route="orthogonal", start_direction=sd, end_direction=ed, **paint)
            return self.connect(key, a, b, route=route, **paint)
        if curve:
            if route != "straight":
                raise ValueError("curve works with the default straight route")
            return self.connect(key, a, b, route="arc", bend=float(curve), **paint)
        return self.connect(key, a, b, route=route, **paint)

    @_drawing_api(
        "connect",
        purpose="一步画无端点的连线（结合、膜、引导线）。",
        returns="Connector",
        semantics=("与 arrow 相同，只是默认没有端点；Node 端点同样自动落在轮廓上。",),
        example='d.line(pdl1, pd1, stroke="#5B1061", stroke_width=3)',
        rank=8,
    )
    def line(self, start, end, **kwargs):
        kwargs.setdefault("head", None)
        return self.arrow(start, end, **kwargs)

    def drawing_help(self, *names):
        """Same as the module-level drawing_help(*names): d.drawing_help('finish') works too."""
        from ._help import drawing_help

        return drawing_help(*names)

    @_drawing_api(
        "export",
        purpose="导出前自检：文字互压、连线/手写线穿过非端点文字、超出画布、端点落在不可见辅助点、箭头尖压在别的对象边线上。",
        returns="list[dict]（kind/keys/hint；空列表表示通过）",
        semantics=(
            "只检查这些真实问题；箭头端点贴着节点、受体嵌在膜上等有意接触不算问题。",
            '有意压在边线上的对象（带边上的载流子、线上的标记）创建时加 data_on_edge="1"，不再报 head_on_edge / text_straddles_frame。',
            "to_slide 会自动执行并在有问题时给出警告；按 hint 改一次即可，不需要再跑本地 lint 校准。",
        ),
        example="for p in d.check(): print(p)",
        rank=0,
    )
    def check(self, *, width=None):
        from ._inspection import check_drawing

        return _CheckResult(_annotate(self, check_drawing(self, width=width)))

    @_drawing_api(
        "export",
        purpose="细节审查：找出图里的主体节点（连线最多/面积最大）中只画成方框、矩形或纯文字的，提示是否需要精修。",
        returns="list[dict]（kind/keys/hint；空列表表示主体已有细节）",
        semantics=(
            "只看结构与几何复杂度，不靠词表：主体 = 连线多或面积大的节点；方框/单个图形/纯文字/图标级 svg_at（几个图元，重复图元算一种）算“简单”，部件与有结构的 svg_at 算“有细节”；另提示孤立主体与隔空相连的受体-配体。",
            "只提示、不阻断；它是不是实体由作者判断——是实体就用部件或 svg_at 画外形，只是步骤/概念标签就保留方框。",
            "to_slide 会自动打印结果；空列表说明不用为细节再预览。",
        ),
        example='for r in d.review(): print(r["hint"])',
        rank=0,
    )
    def review(self, *, limit=3):
        from ._review import review_drawing

        return review_drawing(self, limit=limit)

    @_drawing_api(
        "export",
        purpose="文字版排版摘要：按页面实际尺寸报告画布缩放、对象位置尺寸、连线实际长度与线宽、页面字号，并提示过细/过小/过短/过挤。",
        returns="str（同时可用 summary(..., warnings_only=True) 只取提示列表）",
        semantics=(
            "width 为放到页面上的宽度（与 to_slide 的 width 一致），所有数值换算为页面 px（文字为 pt）。",
            "连线端点、路由长度、自适应框尺寸、自动标签位置都是计算结果，用它确认排版而不必截图。",
            "to_slide(..., summary=True) 会直接打印本摘要；默认只在有提示时打印提示行。",
        ),
        example="print(d.summary(width=418))",
        rank=1,
    )
    def summary(self, *, width=None, warnings_only=False):
        from ._summary import layout_summary

        text, warns = layout_summary(self, width=width)
        return warns if warnings_only else text

    @_drawing_api(
        "export",
        purpose="一步转换为可编辑 Slides 元素片段（写 SVG + 映射 + atomize）。",
        returns="str（SML 片段，交给 publish_slide）",
        semantics=(
            "x/y/width 为页面上的落点和宽度（px），高度按画布比例；返回值直接传 publish_slide(page_xml, fragment, presentation=deck_id)。",
            "path 省略时写到临时文件；需要保留 SVG 时传 path。",
            "summary=True 打印完整文字版排版摘要（页面尺寸下的位置、连线长度、线宽、字号）；默认只在发现过细/过小/过短/过挤时打印提示，summary=False 关闭。",
        ),
        example="r = publish_slide(page_xml, d.to_slide(x=40, y=96, width=880), presentation=deck_id)",
        rank=1,
    )
    def to_slide(self, *, x, y, width, path=None, summary=None):
        import tempfile
        from ..atomize_svg_to_slide import atomize_svg_to_slide
        from ..atomize_svg_to_slide._config import _CFG

        problems = self.check(width=width)
        import sys

        if problems:
            # stderr: callers parse their own stdout (json/eval); diagnostics must not corrupt it
            print(_format_problems(problems), file=sys.stderr)
        notes = self.review()
        if notes:
            if any(n["kind"] == "mostly_plain" for n in notes):
                print(
                    "[drawing 细节审查·需修改] "
                    + "；".join(n["hint"] for n in notes)
                    + " → 写入前先把主体换成部件或带结构的 svg_at，再 d.preview() 看一次",
                    file=sys.stderr,
                )
            else:
                print(
                    "[drawing 细节审查] "
                    + "；".join(n["hint"] for n in notes)
                    + " → 有提示时先 d.preview() 看一次再精修；没有提示就不用预览",
                    file=sys.stderr,
                )
        from ._summary import layout_summary

        text, warns = layout_summary(self, width=width)
        if summary:
            print(text)
        elif warns and summary is None:
            print(_format_layout_hints(warns, width), file=sys.stderr)
        keys = ("svg_w", "svg_h", "slide_x0", "slide_y0", "slide_w", "slide_h")
        saved = {k: _CFG[k] for k in keys}
        height = width * self.height / self.width
        try:
            _CFG.update(svg_w=self.width, svg_h=self.height, slide_x0=x, slide_y0=y, slide_w=width, slide_h=height)
            if path is not None:
                return atomize_svg_to_slide(self.write(path))
            with tempfile.TemporaryDirectory() as tmp:
                return atomize_svg_to_slide(self.write(Path(tmp) / "drawing.svg"))
        finally:
            _CFG.update(saved)


_BLOCKING = ("text_overlap", "line_through_text", "off_canvas", "line_box_over_text", "text_straddles_frame")


class _CheckResult(list):
    """d.check() result: still a plain list of dicts (``== []`` when clean); prints grouped, blocking first."""

    def __str__(self):
        return _format_problems(self)


def _annotate(drawing, problems):
    """Add severity, the first key's text snippet / canvas bbox and, where computable, a concrete new position."""
    layout = _Layout(drawing)
    for p in problems:
        p.setdefault("severity", "blocking" if p.get("kind") in _BLOCKING else "warning")
        node = drawing.nodes.get((p.get("keys") or [None])[-1]) if p.get("kind") == "text_overlap" else None
        node = node or next((drawing.nodes[k] for k in p.get("keys") or [] if k in drawing.nodes), None)
        if node is None:
            continue
        try:
            b = layout.bounds(node)
        except (ValueError, TypeError):
            continue
        p.setdefault("bbox", (round(b.x), round(b.y), round(b.width), round(b.height)))
        text = " ".join("".join(node.geometry.element.itertext()).split())
        if text:
            p.setdefault("text", text[:20])
        if p.get("kind") == "text_overlap" and "suggest" not in p:
            other = drawing.nodes.get(p["keys"][0])
            try:
                o = layout.bounds(other)
                dy = (o.y + o.height + 4 - b.y) if b.y >= o.y else -(b.y + b.height + 4 - o.y)
                p["suggest"] = f"move key '{node.key}' to at=({b.x + b.width / 2:.0f}, {b.y + b.height / 2 + dy:.0f})"
            except (ValueError, TypeError, AttributeError):
                pass
    problems.sort(key=lambda p: (p.get("severity") != "blocking", p.get("kind", "")))
    return problems


def _problem_line(p):
    what = f"'{p['text']}' " if p.get("text") else ""
    box = f"bbox={p['bbox']} " if p.get("bbox") else ""
    return f"{'/'.join(p.get('keys') or [])} {what}{box}→ {p.get('suggest') or p.get('hint', '')}"


def _format_problems(problems, per_kind=2):
    """Grouped by kind, blocking kinds first; at most ``per_kind`` lines per kind plus "+N more"."""
    if not problems:
        return "[drawing check] 通过"
    groups = {}
    for p in problems:
        groups.setdefault((p.get("severity") != "blocking", p.get("kind")), []).append(p)
    blocking = sum(p.get("severity") == "blocking" for p in problems)
    lines = [f"[drawing check] {len(problems)} 处问题（{blocking} 处必须改），写入前先改："]
    for (_, kind), items in sorted(groups.items(), key=lambda kv: (kv[0][0], str(kv[0][1]))):
        lines += [f"  - {kind} {_problem_line(p)}" for p in items[:per_kind]]
        if len(items) > per_kind:
            lines.append(f"    +{len(items) - per_kind} more {kind}（同类，按同样方法改；全部见 d.check()）")
    return "\n".join(lines)


def _format_layout_hints(warns, width, cap=3):
    head = f"[drawing 排版提示 @ {width:g}px] {len(warns)} 条（不阻断）："
    return "\n".join(
        [head]
        + [f"  - {w}" for w in warns[:cap]]
        + ([f"  +{len(warns) - cap} more，print(d.summary(width={width:g})) 看全部"] if len(warns) > cap else [])
    )
