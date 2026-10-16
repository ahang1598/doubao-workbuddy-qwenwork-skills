"""Circular construction, repetitions, ribbons, extrusion and cutaways."""

from __future__ import annotations

import copy
import math
from typing import Callable
import xml.etree.ElementTree as ET
from ..atomize_svg_to_slide._geometry import Matrix, fmt, number, parse_transform, rotate, translate
from ._geometry import (
    Box,
    Curve,
    Geometry,
    PathFrame,
    Point,
    _MAX_POINTS,
    _box,
    _finite,
    _point,
    _scoped,
    group,
    path,
    polygon,
    rect,
)
from ._help import _drawing_api


@_drawing_api(
    "curves",
    purpose="从圆外点构造圆的两个切点。",
    returns="tuple[Point, ...] 坐标快照",
    semantics=(
        "center 与 point 使用同一二维坐标系；圆外返回两点，圆上返回 (point,)，圆内抛 ValueError。",
        "圆外第一支位于 center→point 向量的 +90° 侧，第二支位于 −90° 侧；即 cross(point-center, 切点-center) 分别为正、负，不按画面上/下排序。",
        "切点可传给 Geometry.with_ports 或用于自由路径；不自动选分支，圆或目标点变化后需重新计算。",
        "先在圆的本体二维截面求切点，再投影到画面；屏幕上的投影椭圆不能直接当圆套用。",
    ),
    example="contacts = circle_tangent_points(center, radius, outside)\ncontact = contacts[branch]\npart = part.with_ports(contact=contact)",
    limits=(
        "radius 必须为正；坐标、半径及计算结果非有限时抛 ValueError。",
        "圆上判断使用浮点距离相等，不隐式吸附；圆上只返回接点，不产生非零长度切线段。",
        "极端坐标尺度受浮点精度限制；分支方向是数学约定，接近的输出可能舍入重合。",
    ),
    common=False,
)
def circle_tangent_points(center, radius, point) -> tuple[Point, ...]:
    """Return circle contacts on the +90/-90 sides of ``point-center``."""
    cx, cy = _point(center)
    px, py = _point(point)
    radius = float(radius)
    _finite(radius)
    if radius <= 0:
        raise ValueError("Circle radius must be positive")
    dx, dy = px - cx, py - cy
    distance = math.hypot(dx, dy)
    _finite(dx, dy, distance)
    if distance < radius:
        raise ValueError("Point must lie on or outside the circle")
    if distance == radius:
        return ((px, py),)
    ux, uy = dx / distance, dy / distance
    ratio = radius / distance
    along = radius * ratio
    across = radius * math.sqrt((1 - ratio) * (1 + ratio))
    contacts = (
        (cx + along * ux - across * uy, cy + along * uy + across * ux),
        (cx + along * ux + across * uy, cy + along * uy - across * ux),
    )
    for contact in contacts:
        _finite(*contact)
    return contacts


def _circular_parameters(center, radius, start_degrees, sweep_degrees):
    center = _point(center)
    radius, start, sweep = map(float, (radius, start_degrees, sweep_degrees))
    _finite(radius, start, sweep)
    if radius <= 0:
        raise ValueError("Circle radius must be positive")
    if not 0 < abs(sweep) <= 360:
        raise ValueError("Sweep must be nonzero and at most 360 degrees in magnitude")
    return center, radius, start % 360, sweep


def _circular_point(center, radius, degrees):
    degrees %= 360
    cardinal = {0: (1, 0), 90: (0, 1), 180: (-1, 0), 270: (0, -1)}
    unit = cardinal.get(degrees)
    if unit is None:
        angle = math.radians(degrees)
        unit = math.cos(angle), math.sin(angle)
    return _point((center[0] + radius * unit[0], center[1] + radius * unit[1]))


def _arc_xy(point):
    # Preserve short sweeps instead of rounding nearby endpoints together.
    return " ".join(format(value, ".17g") for value in point)


def _circular_commands(center, radius, start, sweep):
    first = _circular_point(center, radius, start)
    commands = ["M " + _arc_xy(first)]
    count = 2 if abs(sweep) > 180 else 1
    for index in range(1, count + 1):
        end = (
            first
            if index == count and abs(sweep) == 360
            else _circular_point(center, radius, start + sweep * index / count)
        )
        commands.append(f"A {radius:.17g} {radius:.17g} 0 0 {int(sweep > 0)} " + _arc_xy(end))
    return commands, first, end


@_drawing_api(
    "curves",
    purpose="按圆心、半径和有符号扫角构造真实圆弧。",
    returns="Geometry",
    semantics=(
        "center 为局部 (x, y)，radius 为半径；角度单位是度，0° 指向 +x，SVG 的 y 向下，正扫角为顺时针。",
        "start_degrees 可跨越 0°；sweep_degrees 保留方向，0 < 绝对值 ≤ 360，不自动改取短弧。",
        '局部弧不闭合，默认 fill="none"；±360 构成闭合整圆。使用 SVG A 命令，不用几条弦代替圆弧。',
        "端口 center/start/mid/end 为同坐标系快照，mid 在扫角一半处；整圆 start=end，加入 Node 后端口随变换。",
    ),
    example="arc = circular_arc(center, radius, start_degrees, sweep_degrees, **paint)",
    limits=(
        "半径须为正；零扫角、超过一周或非有限参数抛 ValueError。",
        "不自动选定角标半径、标注文字或构图；需要填充扇形时用 annular_sector。",
    ),
    common=False,
    style=True,
)
def circular_arc(center, radius, start_degrees, sweep_degrees, **style):
    """Create an open circular arc; a signed full turn is closed without a seam."""
    center, radius, start, sweep = _circular_parameters(center, radius, start_degrees, sweep_degrees)
    commands, first, end = _circular_commands(center, radius, start, sweep)
    if abs(sweep) == 360:
        commands.append("Z")
    style.setdefault("fill", "none")
    return path(" ".join(commands), **style).with_ports(
        center=center, start=first, mid=_circular_point(center, radius, start + sweep / 2), end=end
    )


@_drawing_api(
    "curves",
    purpose="构造闭合环扇形、普通扇形或完整圆环。",
    returns="Geometry",
    semantics=(
        "center 为局部 (x, y)；0 ≤ inner_radius < outer_radius。角度单位为度，0° 指向 +x，SVG 正扫角顺时针。",
        "0 < |sweep_degrees| ≤ 360；跨 0°、负向和大于半圆的扫角保持原意，不自动补角或取短弧。",
        "inner_radius=0 得到普通扇形；±360 时为完整圆环或实心圆。完整环的内外轮廓反向独立闭合，孔洞不填实，也不画径向接缝。",
        "端口 center、outer_start/outer_end、inner_start/inner_end 对应真实位置；mid 取平均半径上的扫角中点，不是面积重心。内半径为0时两个inner端口均为center。",
    ),
    example="region = annular_sector(center, inner_radius, outer_radius, start_degrees, sweep_degrees, **paint)",
    limits=(
        "无效半径、零扫角、超过一周或非有限参数抛 ValueError。",
        "只构造几何，不生成图表数据、配色、标签或图例；端口随 Node 变换，参数变化后重新构造。",
    ),
    common=False,
    style=True,
)
def annular_sector(center, inner_radius, outer_radius, start_degrees, sweep_degrees, **style):
    """Create a sector with opposite inner winding; full rings have no radial edge."""
    center, outer, start, sweep = _circular_parameters(center, outer_radius, start_degrees, sweep_degrees)
    inner = float(inner_radius)
    _finite(inner)
    if not 0 <= inner < outer:
        raise ValueError("Radii must satisfy 0 <= inner_radius < outer_radius")
    commands, outer_start, outer_end = _circular_commands(center, outer, start, sweep)
    inner_start = _circular_point(center, inner, start)
    inner_end = inner_start if abs(sweep) == 360 else _circular_point(center, inner, start + sweep)
    if abs(sweep) == 360:
        commands.append("Z")
        if inner:
            inner_commands, _, _ = _circular_commands(center, inner, start, -sweep)
            commands.extend(inner_commands + ["Z"])
    else:
        commands.append("L " + _arc_xy(inner_end))
        if inner:
            inner_commands, _, _ = _circular_commands(center, inner, start + sweep, -sweep)
            commands.extend(inner_commands[1:])
        commands.append("Z")
    return path(" ".join(commands), **style).with_ports(
        center=center,
        outer_start=outer_start,
        outer_end=outer_end,
        inner_start=inner_start,
        inner_end=inner_end,
        mid=_circular_point(center, inner + (outer - inner) / 2, start + sweep / 2),
    )


@_drawing_api(
    "repeat",
    purpose="沿中心线排列自定义部件。",
    returns="Geometry",
    semantics=(
        "template 可以是 Geometry，也可以是 factory(index, t)；t 是 0–1 的归一化弧长，factory 返回 Geometry。",
        "curve 可以是路径字符串或 Curve；count 与 spacing 必须且只能指定一个。",
        "normal_offset 沿路径法线偏移；orient=True 时跟随切线；pivot 选择部件边界锚点。",
        "count 模式：开放路径受 include_end 控制，闭合路径不重复首尾；phase 仅用于 spacing 模式。",
        "放置点端口名为 item_0；部件端口名为 item_0.outlet 等。",
    ),
    example="parts = repeat_along_path(factory, path_data, count=count)",
    limits=("数量上限为 8192；不自动避免部件相互重叠。",),
)
def repeat_along_path(
    template: Geometry | Callable[[int, float], Geometry],
    curve,
    *,
    count=None,
    spacing=None,
    phase=0,
    normal_offset=0,
    orient=True,
    include_end=True,
    pivot="center",
):
    curve = curve if isinstance(curve, Curve) else Curve(curve)
    length = curve.length
    _, closed = curve.samples()
    _finite(phase, normal_offset)
    if (count is None) == (spacing is None):
        raise ValueError("Specify exactly one of count or spacing")
    if count is not None:
        if isinstance(count, bool) or int(count) != count or not 1 <= count <= _MAX_POINTS:
            raise ValueError("Count must be an integer between 1 and 8192")
        count = int(count)
        if phase:
            raise ValueError("Phase is used with spacing, not count")
        if closed:
            distances = [i * length / count for i in range(count)]
        elif count == 1:
            distances = [length / 2]
        elif include_end:
            distances = [i * length / (count - 1) for i in range(count)]
        else:
            distances = [(i + 0.5) * length / count for i in range(count)]
    else:
        _finite(spacing)
        if spacing <= 0 or phase < 0:
            raise ValueError("Spacing must be positive and phase nonnegative")
        n = max(0, int(math.floor((length - phase) / spacing)) + 1)
        if n > _MAX_POINTS:
            raise ValueError("Too many repeated objects")
        distances = [phase + i * spacing for i in range(n) if not closed or phase + i * spacing < length - 1e-10]
    parts = []
    ports = {}
    for i, distance in enumerate(distances):
        point, tangent = curve.at(distance)
        x = point[0] - normal_offset * tangent[1]
        y = point[1] + normal_offset * tangent[0]
        geometry = template(i, distance / length) if callable(template) else template
        if not isinstance(geometry, Geometry):
            raise TypeError("Repeat factory must return Geometry")
        px, py = geometry.bounds.anchor(pivot)
        angle = math.degrees(math.atan2(tangent[1], tangent[0])) if orient else 0
        matrix = translate(x, y).then(rotate(angle)).then(translate(-px, -py))
        transformed = geometry.transformed(matrix)
        parts.append(transformed)
        ports[f"item_{i}"] = (x, y)
        ports.update({f"item_{i}.{k}": matrix.point(*p) for k, p in geometry.ports.items()})
        ports.update(
            {
                f"item_{i}.{k}": PathFrame(
                    transformed.ports[k], transformed.port_tangents.get(k, (normal[1], -normal[0])), normal, None
                )
                for k, normal in transformed.port_directions.items()
            }
        )
    return group(*parts, ports=ports)


@_drawing_api(
    "ribbon",
    purpose="沿中心线构造等宽或变宽带。",
    returns="Geometry",
    semantics=(
        "curve 可以是路径字符串或 Curve；width 是宽度数值或 width(t) 函数，t 为归一化弧长。",
        "宽度非负且不能全为零；闭合路径的 width(0) 与 width(1) 必须一致。",
        "miter_limit 限制尖角斜接长度，超限用斜切连接。",
    ),
    example="band = ribbon(path_data, width=width_at, **paint)",
    limits=(
        "开放带为平截口；闭合带使用 evenodd 保留孔洞。",
        "过宽或自交带不自动推断遮挡关系；闭合带可能由 atomizer 保留为 SVG。",
    ),
    style=True,
)
def ribbon(curve, width, *, miter_limit=3, **style):
    """Offset a sampled centerline."""
    curve = curve if isinstance(curve, Curve) else Curve(curve)
    raw, closed = curve.samples()
    points = list(raw[:-1] if closed else raw)
    _finite(miter_limit)
    if miter_limit < 1:
        raise ValueError("Miter limit must be at least one")
    distances = [0.0]
    for a, b in zip(points, points[1:]):
        distances.append(distances[-1] + math.dist(a, b))
    widths = [float(width(d / curve.length) if callable(width) else width) for d in distances]
    _finite(*widths)
    if min(widths) < 0 or max(widths) <= 0:
        raise ValueError("Band widths must be nonnegative and not all zero")
    if closed and callable(width) and abs(float(width(1)) - widths[0]) > 1e-8:
        raise ValueError("Closed-band widths must agree at both ends")

    def normal(a, b):
        size = math.dist(a, b)
        return -(b[1] - a[1]) / size, (b[0] - a[0]) / size

    def side(sign):
        result = []
        for i, p in enumerate(points):
            a = normal(points[i - 1], p) if i or closed else normal(p, points[1])
            b = normal(p, points[(i + 1) % len(points)]) if i + 1 < len(points) or closed else a
            half = sign * widths[i] / 2
            den = 1 + a[0] * b[0] + a[1] * b[1]
            offset = ((a[0] + b[0]) * half / den, (a[1] + b[1]) * half / den) if den > 1e-10 else (math.inf, math.inf)
            if math.hypot(*offset) <= abs(half) * miter_limit + 1e-10:
                result.append((p[0] + offset[0], p[1] + offset[1]))
            else:
                result.extend([(p[0] + a[0] * half, p[1] + a[1] * half), (p[0] + b[0] * half, p[1] + b[1] * half)])
        return result

    left, right = side(1), side(-1)
    if closed:
        d = " ".join("M " + " L ".join(f"{fmt(x)} {fmt(y)}" for x, y in ring) + " Z" for ring in (left, right))
        result = path(d, **{**style, "fill_rule": "evenodd"})
    else:
        result = polygon(left + list(reversed(right)), **style)
    return result.with_ports(start=points[0], end=points[0] if closed else points[-1])


@_drawing_api(
    "extrude",
    purpose="给凸轮廓增加平行厚度与可见侧面。",
    returns="Geometry",
    semantics=(
        "points 为单个凸多边形的局部顶点；depth=(dx, dy) 是非零厚度方向。",
        "front/side 为样式字典；side 也可用 factory(edge_index, unit_normal) 返回各面样式。",
        "back 可选；返回 front_center、back_center 端口。",
    ),
    example="solid = extrude(points, depth, front=front_paint, side=side_paint)",
    limits=("只支持非退化凸轮廓；不做透视、自动光照或真实三维重建。",),
)
def extrude(points, depth, *, front, side, back=None):
    """Parallel 2.5-D extrusion of one convex polygon; paints are caller-owned."""
    points = [_point(p) for p in points]
    dx, dy = _point(depth)
    if len(points) > 1 and points[0] == points[-1]:
        points.pop()
    from ..atomize_svg_to_slide._clip import convex, area

    if not convex(points):
        raise ValueError("Extrusion needs one non-degenerate convex contour")
    if math.hypot(dx, dy) < 1e-12:
        raise ValueError("Extrusion depth must be nonzero")
    sign = 1 if area(points) > 0 else -1
    parts = []
    if back is not None:
        parts.append(polygon([(x + dx, y + dy) for x, y in points], **back))
    for i, (a, b) in enumerate(zip(points, points[1:] + points[:1])):
        normal = (sign * (b[1] - a[1]), -sign * (b[0] - a[0]))
        if normal[0] * dx + normal[1] * dy > 1e-10:
            length = math.hypot(*normal)
            unit = (normal[0] / length, normal[1] / length)
            paint = side(i, unit) if callable(side) else side
            parts.append(polygon([a, b, (b[0] + dx, b[1] + dy), (a[0] + dx, a[1] + dy)], **paint))
    parts.append(polygon(points, **front))
    center = _box(points).anchor()
    return group(*parts, ports={"front_center": center, "back_center": (center[0] + dx, center[1] + dy)})


def _clip_window(element, definitions, clip):
    """Put filled leaves in clipPath; SVG does not allow a group child there."""
    shapes = {"path", "rect", "circle", "ellipse", "polygon", "polyline", "line", "text", "use"}
    inherited_names = {
        "fill-rule",
        "clip-rule",
        "visibility",
        "font-family",
        "font-size",
        "font-style",
        "font-weight",
        "font-stretch",
        "font-variant",
        "letter-spacing",
        "word-spacing",
        "text-anchor",
        "direction",
        "writing-mode",
        "dominant-baseline",
        "alignment-baseline",
    }
    references = {node.get("id"): node for node in element.iter() if node.get("id")}

    def visit(node, matrix, inherited, uses=()):
        tag = node.tag.split("}")[-1]
        if tag == "defs":
            if not uses:
                definitions.extend(list(node))
            return
        if tag in ("title", "desc", "metadata"):
            return
        attrs = dict(node.attrib)
        # Public constructors use presentation attributes. Also retain the
        # same precedence for inline declarations in caller-owned fragments.
        for declaration in attrs.pop("style", "").split(";"):
            if ":" in declaration:
                key, value = declaration.split(":", 1)
                attrs[key.strip()] = value.strip().removesuffix("!important").strip()
        if attrs.get("display") == "none":
            return
        if any(attrs.get(key, "none") != "none" for key in ("clip-path", "mask")):
            raise ValueError("Cutaway window needs filled geometry, not an existing clip or mask")
        matrix = matrix.then(parse_transform(attrs.get("transform", "")))
        style = dict(inherited)
        for key in inherited_names & attrs.keys():
            if attrs[key] not in ("inherit", "unset"):
                style[key] = attrs[key]
        if tag == "g":
            for child in node:
                visit(child, matrix, style, uses)
            return
        if tag == "use":
            href = attrs.get("href", attrs.get("{http://www.w3.org/1999/xlink}href", ""))
            if href.startswith("#") and href[1:] in references:
                identifier = href[1:]
                if identifier in uses:
                    raise ValueError("Cyclic cutaway window use reference")
                matrix = matrix.then(translate(number(attrs.get("x", "0")), number(attrs.get("y", "0"))))
                visit(references[identifier], matrix, style, (*uses, identifier))
                return
        if tag not in shapes:
            raise ValueError(f"Unsupported cutaway window element: {tag}")
        node = copy.deepcopy(node)
        if uses:
            # Definitions keep their original scoped IDs; expanded instances
            # must not duplicate them in the clipPath.
            attrs.pop("id", None)
            for child in node.iter():
                child.attrib.pop("id", None)
        node.attrib.clear()
        node.attrib.update({**style, **attrs})
        for key in ("fill-rule", "clip-rule"):
            if node.get(key) in ("inherit", "unset"):
                node.attrib.pop(key)
        rule = style.get("clip-rule", style.get("fill-rule", "nonzero"))
        node.set("clip-rule", "nonzero" if rule == "initial" else rule)
        node.attrib.pop("filter", None)  # Window is filled geometry, not filtered ink.
        if matrix != Matrix():
            node.set("transform", matrix.svg())
        else:
            node.attrib.pop("transform", None)
        clip.append(node)

    visit(element, Matrix(), {})


@_drawing_api(
    "section",
    purpose="通过窗口显示已经提供的内部结构。",
    returns="Geometry",
    semantics=(
        "geometry 是源几何，可用 group 组合手绘纹理；window 是同一局部坐标系下的 Box 或 Geometry。",
        "窗口取路径、基本图形或其变换组合的填充区域；组合取并集，显式 clip-rule 优先，否则沿用 fill-rule 保留孔洞，不包含描边或滤镜范围。",
        "返回边界与端口筛选按源和窗口的外接框交集；操作创建几何快照，不动态绑定另一个 Node 的内容。",
    ),
    example="section = cutaway(assembly, window)",
    limits=(
        "纹理和内部结构需要调用方提供；已带 clip-path/mask 的窗口会拒绝，先提供其填充轮廓；复杂裁切可能保留为 SVG。",
        "局部 defs/use 会展开；共享 use 引用需调用方提供可直接裁切的图形及 clip-rule，构造时不解析画布中的共享定义。",
    ),
)
def cutaway(geometry, window):
    """Reveal supplied geometry through a window; no internal structure is invented."""
    window = rect(window.width, window.height, x=window.x, y=window.y) if isinstance(window, Box) else window
    if not isinstance(window, Geometry):
        raise TypeError("Window must be Box or Geometry")
    root = ET.Element("g")
    definitions = ET.SubElement(root, "defs")
    clip = ET.SubElement(definitions, "clipPath", {"id": "window"})
    _clip_window(_scoped(window.element, "window-shape"), definitions, clip)
    body = ET.SubElement(root, "g", {"clip-path": "url(#window)"})
    body.append(_scoped(geometry.element, "content"))
    a, b = geometry.bounds, window.bounds
    x, y = max(a.x, b.x), max(a.y, b.y)
    box = Box(x, y, max(0, min(a.x + a.width, b.x + b.width) - x), max(0, min(a.y + a.height, b.y + b.height) - y))
    ports = {
        k: p
        for k, p in geometry.ports.items()
        if box.x <= p[0] <= box.x + box.width and box.y <= p[1] <= box.y + box.height
    }
    return Geometry(
        root,
        box,
        ports,
        {k: v for k, v in geometry.port_directions.items() if k in ports},
        {k: v for k, v in geometry.port_tangents.items() if k in ports},
    )


@_drawing_api(
    "section",
    purpose="裁取并放大已有结构。",
    returns="Geometry",
    semantics=(
        "window 必须是 Box；先裁切，再把窗口原点移到 (0, 0)，按正数 factor 缩放。",
        "生成的是几何快照；源结构变化后重新调用，并用 Node.set_geometry 更新实例。",
    ),
    example="detail = zoom(assembly, window, factor)",
    limits=(),
)
def zoom(geometry, window: Box, factor):
    return cutaway(geometry, window).moved(-window.x, -window.y).scaled(factor)


def _region_polygon(region):
    if isinstance(region, Box):
        return [
            (region.x, region.y),
            (region.x + region.width, region.y),
            (region.x + region.width, region.y + region.height),
            (region.x, region.y + region.height),
        ]
    pts = list(region)
    if len(pts) == 4 and all(isinstance(v, (int, float)) for v in pts):
        return _region_polygon(Box(*pts))
    pts = [_point(p) for p in pts]
    if len(pts) < 3:
        raise ValueError("region must be a Box, (x, y, width, height) or a polygon of at least 3 points")
    return pts


def _inside(pt, poly):
    x, y, inside = pt[0], pt[1], False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            inside = not inside
    return inside


@_drawing_api(
    "section",
    purpose="把一条线段裁到矩形或任意多边形内（不必自己写 Cohen–Sutherland）。",
    returns="list[(Point, Point)]：落在区域内的子线段（凹多边形可能多段，完全在外为空）",
    semantics=(
        "region 可为 Box、(x, y, width, height) 或多边形顶点列表；与线段同一坐标系。",
        "常用于把示意的晶面迹线、滑移线、剖面线、纹理线限制在晶粒/截面/窗口内，再用 d.line 或 path_at 画出。",
    ),
    example='for p, q in clip_segment((60, 300), (900, 120), Box(100, 100, 400, 300)):\n    d.line(p, q, color="#C0392B")',
    common=False,
)
def clip_segment(start, end, region):
    p, q = _point(start), _point(end)
    poly = _region_polygon(region)
    dx, dy = q[0] - p[0], q[1] - p[1]
    ts = [0.0, 1.0]
    for a, b in zip(poly, poly[1:] + poly[:1]):
        ex, ey = b[0] - a[0], b[1] - a[1]
        den = dx * ey - dy * ex
        if abs(den) < 1e-12:
            continue
        t = ((a[0] - p[0]) * ey - (a[1] - p[1]) * ex) / den
        u = ((a[0] - p[0]) * dy - (a[1] - p[1]) * dx) / den
        if 0 < t < 1 and -1e-9 <= u <= 1 + 1e-9:
            ts.append(t)
    ts.sort()
    out = []
    for t0, t1 in zip(ts, ts[1:]):
        if t1 - t0 < 1e-9:
            continue
        tm = (t0 + t1) / 2
        if not _inside((p[0] + dx * tm, p[1] + dy * tm), poly):
            continue
        a, b = (p[0] + dx * t0, p[1] + dy * t0), (p[0] + dx * t1, p[1] + dy * t1)
        if out and math.hypot(out[-1][1][0] - a[0], out[-1][1][1] - a[1]) < 1e-9:
            out[-1] = (out[-1][0], b)
        else:
            out.append((a, b))
    return out


def _hatch_segments(poly, angle, gap, offset=0.0):
    ux, uy = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    nx, ny = -uy, ux
    proj = [x * nx + y * ny for x, y in poly]
    along = [x * ux + y * uy for x, y in poly]
    lo, hi = min(along) - 1, max(along) + 1
    segs = []
    c = math.floor((min(proj) - offset) / gap) * gap + offset
    while c <= max(proj):
        if c > min(proj):
            p = (nx * c + ux * lo, ny * c + uy * lo)
            q = (nx * c + ux * hi, ny * c + uy * hi)
            segs.extend(clip_segment(p, q, poly))
        c += gap
    return segs


@_drawing_api(
    "section",
    purpose="在矩形或任意多边形内画等距平行剖面线（斜线填充、晶面迹线、金属截面纹理）。",
    returns="Geometry（与 region 同一坐标系，用 d.add(key, hatch(...)) 原样叠加）",
    semantics=(
        "angle 为线的方向（度，0=水平，正值顺时针）；gap 为线距；offset 平移整组线。",
        '线已裁到区域内（凹多边形也正确）；**style 为描边样式，默认 stroke="#555555"、stroke_width=1。',
    ),
    example='d.rect_at((300, 270), 200, 120, fill="#EEF2F6", stroke="#555555")\n'
    'd.add("hatch", hatch(Box(200, 210, 200, 120), angle=45, gap=10, stroke="#8A939E"))',
    common=False,
    style=True,
)
def hatch(region, *, angle=45, gap=8, offset=0, **style):
    _finite(angle, gap, offset)
    if gap <= 0:
        raise ValueError("gap must be positive")
    poly = _region_polygon(region)
    segs = _hatch_segments(poly, angle, gap, offset)
    style = {"stroke": "#555555", "stroke_width": 1, "fill": "none", **style}
    if not segs:
        return polygon(poly, fill="none", stroke="none")
    d = " ".join(f"M{fmt(a[0])} {fmt(a[1])} L{fmt(b[0])} {fmt(b[1])}" for a, b in segs)
    return path(d, **style)
