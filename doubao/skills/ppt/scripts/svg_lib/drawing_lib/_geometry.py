"""Local geometry, primitive shapes, labels and sampled construction paths."""

from __future__ import annotations

import bisect
import copy
from dataclasses import dataclass, field
from functools import lru_cache
import math
import re
import unicodedata
import xml.etree.ElementTree as ET
from ..atomize_svg_to_slide._geometry import Matrix, arc_to_cubics, fmt, path_segments, rotate, scale, translate
from ..atomize_svg_to_slide._resources import URL_REF, XLINK
from ._help import _drawing_api


Point = tuple[float, float]


_MAX_POINTS = 8192


def _finite(*values):
    if not all(math.isfinite(float(v)) for v in values):
        raise ValueError("Geometry coordinates must be finite")


def _point(value):
    x, y = value
    _finite(x, y)
    return float(x), float(y)


def _unit(value):
    x, y = _point(value)
    length = math.hypot(x, y)
    if length <= 1e-12:
        raise ValueError("Direction must be nonzero")
    return x / length, y / length


@dataclass(frozen=True)
class PathFrame:
    """A local point and unit tangent/normal; all values are snapshots."""

    point: Point
    tangent: Point
    normal: Point
    distance: float | None


def _map_direction(matrix, direction):
    x, y = direction
    return _unit((matrix.a * x + matrix.c * y, matrix.b * x + matrix.d * y))


def _map_normal(matrix, normal):
    x, y = normal
    det = matrix.a * matrix.d - matrix.b * matrix.c
    if abs(det) < 1e-15:
        raise ValueError("Cannot transform a port normal through a singular matrix")
    return _unit(((matrix.d * x - matrix.b * y) / det, (-matrix.c * x + matrix.a * y) / det))


_PAINT_OPACITY = {
    "fill": "fill-opacity",
    "stroke": "stroke-opacity",
    "stop-color": "stop-opacity",
    "flood-color": "flood-opacity",
    "color": None,
}


def _paint_color(value):
    """rgb()/rgba()/CSS named/#RGB colour → ('#RRGGBB', alpha); other paints (none, url(), currentColor) → (value, None)."""
    from .._color_compat import parse_color

    text = str(value).strip()
    if text.lower() == "transparent":
        return "none", None
    parsed = parse_color(text)
    return parsed if parsed else (text, None)


def _color_id(value):
    """Colour → token safe inside an XML id / url(#…) reference."""
    hexed, alpha = _paint_color(value)
    token = hexed.lstrip("#").lower()
    if alpha is not None and alpha < 1:
        token += f"a{round(alpha * 100)}"
    return re.sub(r"[^A-Za-z0-9_-]", "_", token)


def _attrs(values):
    out = {
        k.replace("_", "-"): fmt(v) if isinstance(v, (int, float)) else str(v)
        for k, v in values.items()
        if v is not None
    }
    # Normalise rgb()/rgba()/named colours to #RRGGBB(+opacity): PowerPoint/Slides ignore rgba alpha.
    for paint, opacity in _PAINT_OPACITY.items():
        if paint not in out:
            continue
        hexed, alpha = _paint_color(out[paint])
        out[paint] = hexed
        if opacity and alpha is not None and alpha < 1:
            total = alpha * float(out.get(opacity, 1))
            out[opacity] = fmt(round(total, 4))
    return out


@_drawing_api(
    "section",
    purpose="描述裁切窗口或边界框。",
    returns="Box",
    semantics=("x/y/width/height 使用局部 SVG 坐标；宽高非负。", "Box 是几何值，不是动态位置绑定。"),
    example="window = Box(x, y, width, height)",
    limits=(),
    common=False,
)
@dataclass(frozen=True)
class Box:
    x: float
    y: float
    width: float
    height: float

    def __post_init__(self):
        _finite(self.x, self.y, self.width, self.height)
        if min(self.width, self.height) < 0:
            raise ValueError("Box dimensions cannot be negative")

    @_drawing_api(
        "section",
        purpose="读取边界框上的一个位置。",
        returns="Point 快照",
        semantics=("返回局部 (x, y) 坐标；要随画布对象联动，应使用 Node.anchor。",),
        example='point = geometry.bounds.anchor("center")',
        limits=(),
        common=False,
    )
    def anchor(self, name="center"):
        positions = {
            "top_left": (0, 0),
            "top": (0.5, 0),
            "top_right": (1, 0),
            "left": (0, 0.5),
            "center": (0.5, 0.5),
            "right": (1, 0.5),
            "bottom_left": (0, 1),
            "bottom": (0.5, 1),
            "bottom_right": (1, 1),
        }
        if name not in positions:
            raise ValueError(f"Unknown box anchor {name!r}")
        u, v = positions[name]
        return self.x + u * self.width, self.y + v * self.height

    def transformed(self, matrix):
        return _box(matrix.point(*self.anchor(k)) for k in ("top_left", "top_right", "bottom_left", "bottom_right"))

    def padded(self, amount):
        return Box(self.x - amount, self.y - amount, self.width + 2 * amount, self.height + 2 * amount)


def _box(points):
    points = list(points)
    if not points:
        return Box(0, 0, 0, 0)
    xs, ys = zip(*points)
    return Box(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


def _union(boxes):
    return _box(p for b in boxes for p in (b.anchor("top_left"), b.anchor("bottom_right")))


def _hits(b, boxes, pad=2):
    """Whether box ``b`` comes within ``pad`` of any of ``boxes``."""
    return any(
        b.x < o.x + o.width + pad
        and o.x < b.x + b.width + pad
        and b.y < o.y + o.height + pad
        and o.y < b.y + b.height + pad
        for o in boxes
    )


def _ink_box(box, style, joined=False):
    if style.get("stroke", "none") in ("none", "transparent"):
        return box
    width = float(style.get("stroke_width", style.get("stroke-width", 1)))
    _finite(width)
    if width < 0:
        raise ValueError("Stroke width cannot be negative")
    pad = width / 2
    if joined and style.get("stroke_linejoin", "miter") == "miter":
        pad *= max(1, float(style.get("stroke_miterlimit", 4)))
    return box.padded(pad)


def _scoped(element, prefix):
    """Copy reusable geometry and rename its internal resources per instance."""
    result = copy.deepcopy(element)
    ids = {n.get("id"): f"{prefix}-{n.get('id')}" for n in result.iter() if n.get("id")}
    for node in result.iter():
        if node.get("id"):
            node.set("id", ids[node.get("id")])
        for key, value in list(node.attrib.items()):
            value = URL_REF.sub(lambda m: "url(#" + ids.get(m[1], m[1]) + ")", value)
            if key in ("href", XLINK) and value.startswith("#"):
                value = "#" + ids.get(value[1:], value[1:])
            node.set(key, value)
    return result


@_drawing_api(
    "shapes",
    purpose="把已解析的局部 SVG 片段包装为可组合几何。",
    returns="Geometry",
    semantics=(
        "element 为 Element，bounds 显式传 Box；可信静态 g 可由 ET.fromstring 解析，保留原分组与轮廓。",
        "Box 与端口使用片段整体放入 Node 前的根坐标系；片段内（含根上的）transform 需已计入。",
        "不自动推算任意分组的外框，不裁切、归零或换算物理单位；命名端口优先用 with_ports 添加。",
        "group / Drawing.to_svg 会隔离片段内部 ID 及本地属性引用；共享资源使用 Drawing.add_defs。",
    ),
    example="import xml.etree.ElementTree as ET\npart = Geometry(ET.fromstring(fragment_xml), Box(x, y, width, height))\npart = part.with_ports(contact=contact_xy)",
    limits=(
        "仅承接可信静态片段；不会净化脚本、事件属性、外链或无效引用。",
        "构造器保存 Element 引用；需要独立快照时先 deepcopy，with_ports 会返回带深拷贝的新 Geometry。",
    ),
    common=False,
)
@dataclass(frozen=True)
class Geometry:
    element: ET.Element = field(repr=False, compare=False)
    bounds: Box
    ports: dict[str, Point] = field(default_factory=dict)
    port_directions: dict[str, Point] = field(default_factory=dict)
    port_tangents: dict[str, Point] = field(default_factory=dict)

    @_drawing_api(
        "export",
        purpose="把局部几何导出为可混入手写 SVG 的字符串。",
        returns="str（SVG 元素片段）",
        semantics=(
            "保留当前元素的坐标、变换与分组，不添加 svg 外壳，不修改原 Element。",
            "含内部 ID 时须传 id_prefix；调用方须保证实例前缀及导出后的 ID 在整图中唯一。",
            "前缀以 ASCII 字母或下划线开头，后续可含字母、数字、下划线、点、短横线。",
            "重写内部 ID 及属性中的 url(#id)、href、ET 解析后的 xlink:href；片段外资源引用保持原样。",
        ),
        example='parts.append(part.to_svg_fragment(id_prefix="part1"))',
        limits=("仅承接可信静态片段；不重写样式表文本，不导出 Python 端口或锚点绑定。",),
        common=False,
    )
    def to_svg_fragment(self, *, id_prefix=None):
        """Serialize local geometry without a document wrapper or live bindings."""
        if id_prefix is not None:
            if not isinstance(id_prefix, str):
                raise TypeError("id_prefix must be a string or None")
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]*", id_prefix):
                raise ValueError("id_prefix must be a nonempty SVG identifier prefix")
        ids = [node.get("id") for node in self.element.iter() if node.get("id")]
        if id_prefix is None and ids:
            raise ValueError("Geometry with internal IDs requires a unique id_prefix")
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate SVG IDs inside Geometry")
        element = self.element if id_prefix is None else _scoped(self.element, id_prefix)
        return ET.tostring(element, encoding="unicode")

    @_drawing_api(
        "anchors",
        purpose="给几何定义可连接的局部接口。",
        returns="新 Geometry",
        semantics=(
            "端口接收局部 (x, y) 或 Curve.frame/ray 返回的 PathFrame；后者保存位置、切线和法线，弧长不作为命名端口属性。",
            "原 Geometry 不变；加入画布后用 node.port(name) 获取动态引用。",
        ),
        example="part = part.with_ports(outlet=(x, y))",
        limits=(),
        common=False,
    )
    def with_ports(self, **ports):
        points = dict(self.ports)
        directions = dict(self.port_directions)
        tangents = dict(self.port_tangents)
        for key, value in ports.items():
            points[key] = _point(value.point if isinstance(value, PathFrame) else value)
            if isinstance(value, PathFrame):
                directions[key] = _unit(value.normal)
                tangents[key] = _unit(value.tangent)
            else:
                directions.pop(key, None)
                tangents.pop(key, None)
        return Geometry(copy.deepcopy(self.element), self.bounds, points, directions, tangents)

    def transformed(self, matrix):
        _finite(matrix.a, matrix.b, matrix.c, matrix.d, matrix.e, matrix.f)
        wrapper = ET.Element("g", {"transform": matrix.svg()})
        wrapper.append(copy.deepcopy(self.element))
        return Geometry(
            wrapper,
            self.bounds.transformed(matrix),
            {k: matrix.point(*p) for k, p in self.ports.items()},
            {k: _map_normal(matrix, p) for k, p in self.port_directions.items()},
            {k: _map_direction(matrix, p) for k, p in self.port_tangents.items()},
        )

    @_drawing_api(
        "curves",
        purpose="提取当前几何的一条轮廓，供取点和求交。",
        returns="Curve 快照",
        semantics=(
            "subpath 从 0 开始；支持单个 path、矩形、圆/椭圆、多边形、折线及其变换包装。",
            "不包含描边厚度；多部件 group 需先选择具体部件。裁切或滤镜后的可见轮廓不在此推断。",
            "outward 指所选简单闭合轮廓的外侧，不推断复合孔洞；位置与方向均受采样 tolerance 影响。",
        ),
        example="outline = part.contour(subpath=0, tolerance=0.1)",
        common=False,
    )
    def contour(self, subpath=0, *, tolerance=0.25):
        from ._curves import geometry_contour

        return geometry_contour(self, subpath, tolerance)

    @_drawing_api(
        "shapes",
        purpose="平移局部几何。",
        returns="新 Geometry",
        semantics=("返回副本，不改变已存在的 Node；更新实例用 Node.set_geometry 或 Node.move_to。",),
        example="part = part.moved(dx, dy)",
        limits=(),
        common=False,
    )
    def moved(self, dx, dy):
        return self.transformed(translate(*_point((dx, dy))))

    @_drawing_api(
        "shapes",
        purpose="旋转局部几何和端口。",
        returns="新 Geometry",
        semantics=("degrees 单位为度；about 默认取当前几何边界中心，显式坐标使用局部坐标。",),
        example="part = part.rotated(angle, about=pivot)",
        limits=(),
        common=False,
    )
    def rotated(self, degrees, about=None):
        _finite(degrees)
        x, y = _point(about or self.bounds.anchor())
        return self.transformed(translate(x, y).then(rotate(degrees)).then(translate(-x, -y)))

    @_drawing_api(
        "shapes",
        purpose="等比缩放局部几何和端口。",
        returns="新 Geometry",
        semantics=("factor 必须为正；about 默认局部原点。",),
        example="part = part.scaled(factor)",
        limits=(),
        common=False,
    )
    def scaled(self, factor, about=(0, 0)):
        _finite(factor)
        if factor <= 0:
            raise ValueError("Scale must be positive")
        x, y = _point(about)
        return self.transformed(translate(x, y).then(scale(factor)).then(translate(-x, -y)))

    @_drawing_api(
        "shapes",
        purpose="分别缩放局部几何的横向与纵向，并保持端口联动。",
        returns="新 Geometry",
        semantics=(
            "x_factor/y_factor 均须为正；about 为局部坐标，默认局部原点。",
            "保留 SVG 非等比变换语义，描边、子对象和端口随之变换，不烘焙成固定线宽。",
            "atomizer 对没有共同合成效果的组继续拆分；非等比叶子可保留独立 SVG，不保证原生 shape。",
        ),
        example="variant = part.stretched(x_factor, y_factor, about=pivot)",
        common=False,
    )
    def stretched(self, x_factor, y_factor, about=(0, 0)):
        _finite(x_factor, y_factor)
        if x_factor <= 0 or y_factor <= 0:
            raise ValueError("Stretch factors must be positive")
        x, y = _point(about)
        return self.transformed(translate(x, y).then(Matrix(a=x_factor, d=y_factor)).then(translate(-x, -y)))


@_drawing_api(
    "shapes",
    purpose="创建矩形或圆角矩形。",
    returns="Geometry",
    semantics=("x/y 为局部左上角；width/height 为尺寸；rx 为圆角半径。",),
    example="part = rect(width, height, rx=radius, **paint)",
    limits=(),
    style=True,
)
def rect(width, height, *, x=0, y=0, rx=0, **style):
    box = Box(x, y, width, height)
    _finite(rx)
    if rx < 0:
        raise ValueError("Corner radius cannot be negative")
    element = ET.Element("rect", _attrs(dict(x=x, y=y, width=width, height=height, rx=rx, **style)))
    return Geometry(element, _ink_box(box, style))


@_drawing_api(
    "shapes",
    purpose="创建椭圆或圆。",
    returns="Geometry",
    semantics=("rx/ry 是半径；省略 ry 时等于 rx；cx/cy 为局部中心。",),
    example="part = ellipse(rx, ry, **paint)",
    limits=(),
    style=True,
)
def ellipse(rx, ry=None, *, cx=0, cy=0, **style):
    ry = rx if ry is None else ry
    box = Box(cx - rx, cy - ry, 2 * rx, 2 * ry)
    return Geometry(ET.Element("ellipse", _attrs(dict(cx=cx, cy=cy, rx=rx, ry=ry, **style))), _ink_box(box, style))


@_drawing_api(
    "shapes",
    purpose="用顶点序列构造闭合轮廓。",
    returns="Geometry",
    semantics=("points 是至少三个局部 (x, y) 顶点，按轮廓顺序提供。",),
    example="part = polygon(points, **paint)",
    limits=(),
    style=True,
)
def polygon(points, **style):
    points = [_point(p) for p in points]
    if len(points) < 3:
        raise ValueError("Polygon needs at least three points")
    element = ET.Element("polygon", _attrs(style))
    element.set("points", " ".join(f"{fmt(x)},{fmt(y)}" for x, y in points))
    return Geometry(element, _ink_box(_box(points), style, True))


@_drawing_api(
    "shapes",
    purpose="组合局部部件，保持它们的相对坐标。",
    returns="Geometry",
    semantics=(
        "parts 都是 Geometry；不自动排列或均分布局。",
        "内部资源 ID 会隔离；子端口以 part_0.name 等名称暴露，ports 可指定组端口。",
    ),
    example="assembly = group(*parts, ports=ports)",
    limits=(),
)
def group(*parts, ports=None):
    element = ET.Element("g")
    for i, part in enumerate(parts):
        element.append(_scoped(part.element, f"part-{i}"))
    combined_ports = {f"part_{i}.{k}": v for i, part in enumerate(parts) for k, v in part.ports.items()}
    directions = {f"part_{i}.{k}": v for i, part in enumerate(parts) for k, v in part.port_directions.items()}
    tangents = {f"part_{i}.{k}": v for i, part in enumerate(parts) for k, v in part.port_tangents.items()}
    result = Geometry(element, _union(p.bounds for p in parts), combined_ports, directions, tangents)
    return result.with_ports(**ports) if ports else result


def _split_curve(points):
    levels = [points]
    while len(levels[-1]) > 1:
        levels.append([((a[0] + b[0]) / 2, (a[1] + b[1]) / 2) for a, b in zip(levels[-1], levels[-1][1:])])
    return [p[0] for p in levels], [p[-1] for p in reversed(levels)]


@lru_cache(maxsize=128)
def _flatten(d, tolerance):
    _finite(tolerance)
    if tolerance <= 0:
        raise ValueError("Sampling tolerance must be positive")
    result = []
    current = None
    start = None
    closed = False

    def append(p):
        if not result or math.dist(result[-1], p) > 1e-12:
            if len(result) >= _MAX_POINTS:
                raise ValueError("Path sampling exceeds 8192 points; increase tolerance")
            result.append(tuple(p))

    def curve(points, depth=0):
        chord = math.dist(points[0], points[-1])
        length = sum(math.dist(a, b) for a, b in zip(points, points[1:]))
        # Control-polygon excess also catches collinear overshooting curves.
        if length - chord <= tolerance and max(math.dist(p, points[0]) for p in points) <= chord + tolerance:
            if chord:
                distance = max(
                    abs(
                        (p[0] - points[0][0]) * (points[-1][1] - points[0][1])
                        - (p[1] - points[0][1]) * (points[-1][0] - points[0][0])
                    )
                    / chord
                    for p in points
                )
            else:
                distance = length
            if distance <= tolerance:
                append(points[-1])
                return
        if depth >= 20:
            raise ValueError("Path tolerance is too small for this geometry")
        left, right = _split_curve(points)
        curve(left, depth + 1)
        curve(right, depth + 1)

    for op, values in path_segments(d):
        if closed:
            raise ValueError("Construction paths must have one continuous subpath")
        if op == "M":
            if current is not None:
                raise ValueError("Construction paths must have one continuous subpath")
            current = start = tuple(values)
            append(current)
        elif current is None:
            raise ValueError("Path must start with moveto")
        elif op == "Z":
            append(start)
            current = start
            closed = True
        elif op == "L":
            current = tuple(values)
            append(current)
        elif op in ("C", "Q"):
            curve([current] + list(zip(values[::2], values[1::2])))
            current = tuple(values[-2:])
        elif op == "A":
            for kind, v in arc_to_cubics(*current, *values):
                if kind == "L":
                    append(tuple(v))
                else:
                    curve([current] + list(zip(v[::2], v[1::2])))
                current = tuple(v[-2:])
    if len(result) < 2:
        raise ValueError("Construction path needs nonzero length")
    return tuple(result), closed


@lru_cache(maxsize=128)
def _curve_metrics(d, tolerance):
    points, closed = _flatten(d, tolerance)
    lengths = [0.0]
    for a, b in zip(points, points[1:]):
        lengths.append(lengths[-1] + math.dist(a, b))
    return points, closed, tuple(lengths)


@_drawing_api(
    "repeat",
    purpose="配置构造操作使用的中心线和采样精度。",
    returns="Curve",
    semantics=(
        "d 为单一连续、非零长度 SVG 路径；tolerance 单位是源 SVG 坐标。",
        "repeat/ribbon 也可直接接收路径字符串，无须先创建 Curve。",
    ),
    example="curve = Curve(path_data, tolerance=tolerance)",
    limits=("采样有点数和递归上限；过于苛刻的精度会报错。",),
    common=False,
)
@dataclass(frozen=True)
class Curve:
    d: str
    tolerance: float = 0.25

    def samples(self):
        return _flatten(self.d, self.tolerance)

    @_drawing_api(
        "curves",
        purpose="按弧长截取一段曲线。",
        returns="Curve",
        semantics=(
            "start/end 使用局部弧长，需在 0 到 length 内；开放路径要求 start < end。",
            "闭合路径 wrap=True 时可跨首尾；相同 start/end 表示一整圈。结果为按当前 tolerance 采样的折线。",
        ),
        example="section = curve.trim(start_distance, end_distance, wrap=False)",
    )
    def trim(self, start, end, *, wrap=False):
        from ._curves import trim_curve

        return trim_curve(self, start, end, wrap)

    @_drawing_api(
        "curves",
        purpose="获取轮廓点及其切线、法线。",
        returns="PathFrame",
        semantics=(
            "distance 是局部弧长；端点截断/闭合取模与 Curve.at 一致。",
            "normal 可选 left=(-ty,tx)、right 或 outward；outward 只用于简单闭合轮廓。",
            "返回 point/tangent/normal/distance 快照；角点取出边方向，不承诺唯一数学法线。",
        ),
        example='frame = curve.frame(distance, normal="outward")',
    )
    def frame(self, distance, *, normal="left"):
        from ._curves import curve_frame

        return curve_frame(self, distance, normal)

    @_drawing_api(
        "curves",
        purpose="沿射线寻找真实轮廓交点。",
        returns="PathFrame",
        semantics=(
            "origin/direction 使用轮廓局部坐标，方向必须非零；只保留射线前方交点。",
            "hit 为 nearest 或 farthest；多个子路径需先用 Geometry.contour 选择；精度受 tolerance 控制。",
        ),
        example='frame = curve.ray(origin, direction, hit="nearest", normal="outward")',
        limits=("无交点时报错；共线时选择线段端点或射线原点，角点法线按对应采样边确定。",),
    )
    def ray(self, origin, direction, *, hit="nearest", normal="left"):
        from ._curves import ray_curve

        return ray_curve(self, origin, direction, hit, normal)

    @_drawing_api(
        "curves",
        purpose="把曲线转成可绘制、可组合的几何。",
        returns="Geometry",
        semantics=('保持原始路径；默认 fill="none"，描边由调用方指定。',),
        example="part = curve.to_geometry(stroke=color, stroke_width=width)",
        style=True,
    )
    def to_geometry(self, **style):
        return path(self.d, **{"fill": "none", **style})

    @property
    @_drawing_api(
        "repeat",
        purpose="读取采样路径的累计长度。",
        returns="float",
        semantics=("长度基于自适应采样，不是符号积分结果。",),
        example="distance = curve.length",
        limits=(),
        common=False,
        is_property=True,
    )
    def length(self):
        return _curve_metrics(self.d, self.tolerance)[2][-1]

    @_drawing_api(
        "repeat",
        purpose="沿采样中心线按弧长取点和方向。",
        returns="(Point, 单位切线)",
        semantics=("distance 使用局部弧长单位；开放路径截到两端，闭合路径按总长取模。",),
        example="point, tangent = curve.at(distance)",
        limits=(),
        common=False,
    )
    def at(self, distance):
        points, closed, lengths = _curve_metrics(self.d, self.tolerance)
        _finite(distance)
        distance = distance % lengths[-1] if closed else max(0, min(lengths[-1], distance))
        i = min(len(points) - 2, max(0, bisect.bisect_right(lengths, distance) - 1))
        a, b = points[i : i + 2]
        segment = lengths[i + 1] - lengths[i]
        fraction = (distance - lengths[i]) / segment
        tangent = ((b[0] - a[0]) / segment, (b[1] - a[1]) / segment)
        return (a[0] + (b[0] - a[0]) * fraction, a[1] + (b[1] - a[1]) * fraction), tangent


@_drawing_api(
    "shapes",
    purpose="从 SVG 路径字符串创建形状。",
    returns="Geometry",
    semantics=(
        "d 使用 SVG 路径命令；通常自动计算几何边界。",
        "bounds 可传 Box 或 (x, y, width, height)，用于明确复杂形状的布局边界。",
    ),
    example="part = path(path_data, **paint)",
    limits=(),
    style=True,
)
def path(d, *, bounds=None, **style):
    element = ET.Element("path", {"d": d, **_attrs(style)})
    if bounds is None:
        from ..atomize_svg_to_slide._bounds import paint_bounds, path_bounds

        exact = paint_bounds(element)
        if exact is None:
            conservative = path_bounds(d)
            if conservative is None:
                raise ValueError("Empty path; provide explicit bounds if intentional")
            x, y, right, bottom = conservative
            box = Box(x, y, right - x, bottom - y)
        else:
            box = Box(*exact)
    else:
        box = bounds if isinstance(bounds, Box) else Box(*bounds)
    return Geometry(element, _ink_box(box, style, True))


@_drawing_api(
    "shapes",
    purpose="创建单行或显式换行的文字几何。",
    returns="Geometry",
    semantics=(
        "font_size 必填，使用源 SVG 单位；content 中的换行符生成多行文字。",
        "font_family、line_height 控制字体和行距；字距可用 letter_spacing。",
        "文字边界依赖可用字体测量，否则按字符估算。",
    ),
    example="text_part = label(text, font_size=size, font_family=family, **paint)",
    limits=("不自动换行或缩小字号；实际服务端字体替代仍可能改变外观。",),
    style=True,
)
def label(content, *, font_size, font_family=None, line_height=None, **style):
    from ..atomize_svg_to_slide._font_metrics import measure_text

    _finite(font_size)
    if font_size <= 0:
        raise ValueError("Font size must be positive")
    line_height = font_size * 1.25 if line_height is None else line_height
    _finite(line_height)
    if line_height <= 0:
        raise ValueError("Line height must be positive")
    if line_height < 3:
        line_height *= font_size  # 1.35 means a multiple of font_size, as in CSS/PowerPoint
    spacing = style.get("letter_spacing", style.get("letter-spacing", 0))
    if isinstance(spacing, str):
        if spacing.endswith("em"):
            spacing = float(spacing[:-2]) * font_size
        elif spacing.endswith("px"):
            spacing = float(spacing[:-2])
        elif spacing == "normal":
            spacing = 0
        else:
            spacing = float(spacing)
    _finite(spacing)
    anchor = style.get("text_anchor", style.get("text-anchor", "start"))
    if anchor not in ("start", "middle", "end"):
        raise ValueError("Unsupported text anchor")
    lines = str(content).split("\n")
    element = ET.Element("g")
    boxes = []
    for i, text in enumerate(lines):
        baseline = font_size + i * line_height
        attributes = dict(x=0, y=baseline, font_size=font_size, font_family=font_family, **style)
        ET.SubElement(element, "text", _attrs(attributes)).text = text
        metric = measure_text(
            text,
            font_family or "sans-serif",
            font_size,
            str(style.get("font_weight", "normal")),
            style.get("font_style", "normal"),
        )
        gap_width = max(0, len(text) - 1) * spacing
        if metric:
            width = max(0, metric.advance + gap_width)
            left = min(0, metric.left)
            right = max(width, metric.right + gap_width)
            top = min(-font_size, metric.top)
            bottom = max(font_size * 0.25, metric.bottom)
        else:
            width = max(
                0,
                sum(font_size * (1 if unicodedata.east_asian_width(c) in ("W", "F") else 0.7) for c in text)
                + gap_width,
            )
            left, right, top, bottom = 0, width, -font_size, font_size * 0.25
        shift = width / 2 if anchor == "middle" else width if anchor == "end" else 0
        boxes.append(Box(left - shift, baseline + top, right - left, bottom - top))
    bounds = _union(boxes)
    return Geometry(element, bounds, {"baseline": (0, font_size)})
