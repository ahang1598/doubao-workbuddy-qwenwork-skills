"""Curve construction and contour queries; all geometry remains caller-owned."""

from __future__ import annotations

import math
from functools import lru_cache
from ..atomize_svg_to_slide._geometry import Matrix, fmt, path_segments, parse_transform
from ._geometry import Curve, PathFrame, _curve_metrics, _finite, _point, _unit, _MAX_POINTS
from ._help import _drawing_api


def _polyline(points, closed=False):
    d = "M " + " L ".join(f"{fmt(x)} {fmt(y)}" for x, y in points)
    return d + (" Z" if closed else "")


@_drawing_api(
    "curves",
    purpose="由关键点生成平滑穿点曲线。",
    returns="Curve",
    semantics=(
        "采用弦长参数的三次 Hermite 曲线，逐点穿过输入；默认 alpha=0.5 为向心参数。",
        "tension 在 0–1 间，越大切线手柄越短；1 为直线轮廓。closed=True 首尾平滑相接。",
        "开放曲线可用 start_direction/end_direction 指定端点切线方向；默认使用相邻点方向。",
        "不会自动消除过冲或自交；需要保持单调时使用 tension=1 或调整关键点。",
    ),
    example="curve = smooth_curve(points, closed=True, tension=0.2)",
    limits=("开放曲线至少两个点，闭合至少三个点；相邻点不得重复，最多 8192 点。",),
)
def smooth_curve(
    points, *, closed=False, tension=0, alpha=0.5, start_direction=None, end_direction=None, tolerance=0.25
):
    pts = [_point(p) for p in points]
    _finite(tension, alpha, tolerance)
    if not 0 <= tension <= 1 or not 0 <= alpha <= 1 or tolerance <= 0:
        raise ValueError("tension/alpha must be in [0,1]; tolerance must be positive")
    if closed and len(pts) > 1 and pts[-1] == pts[0]:
        pts.pop()
    if not (3 if closed else 2) <= len(pts) <= _MAX_POINTS:
        raise ValueError("Invalid number of curve points")
    pairs = list(zip(pts, pts[1:] + (pts[:1] if closed else [])))
    lengths = [math.dist(a, b) for a, b in pairs]
    if min(lengths) <= 1e-12:
        raise ValueError("Adjacent curve points must be distinct")
    if closed and (start_direction is not None or end_direction is not None):
        raise ValueError("Closed curves have no endpoint direction overrides")
    if tension == 1:
        return Curve(_polyline(pts, closed), tolerance)
    dt = [length**alpha for length in lengths]
    tangents = []
    for i, p in enumerate(pts):
        if not closed and i in (0, len(pts) - 1):
            j = 0 if i == 0 else len(pts) - 2
            direction = start_direction if i == 0 else end_direction
            unit = (
                _unit(direction)
                if direction is not None
                else _unit((pts[j + 1][0] - pts[j][0], pts[j + 1][1] - pts[j][1]))
            )
            tangents.append(tuple(v * lengths[j] / dt[j] * (1 - tension) for v in unit))
        else:
            prev = pts[i - 1]
            nxt = pts[(i + 1) % len(pts)]
            a = dt[i - 1]
            b = dt[i]
            tangents.append(
                tuple(((p[k] - prev[k]) / a * b + (nxt[k] - p[k]) / b * a) / (a + b) * (1 - tension) for k in (0, 1))
            )
    commands = [f"M {fmt(pts[0][0])} {fmt(pts[0][1])}"]
    for i, (a, b) in enumerate(pairs):
        c = tuple(a[k] + tangents[i][k] * dt[i] / 3 for k in (0, 1))
        e = tuple(b[k] - tangents[(i + 1) % len(pts)][k] * dt[i] / 3 for k in (0, 1))
        commands.append("C " + " ".join(fmt(v) for point in (c, e, b) for v in point))
    if closed:
        commands.append("Z")
    return Curve(" ".join(commands), tolerance)


@lru_cache(maxsize=128)
def _simple_orientation(d, tolerance):
    points, closed, _ = _curve_metrics(d, tolerance)
    if not closed:
        raise ValueError("Outward normals need a simple closed contour")
    area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(points, points[1:]))
    if abs(area) < 1e-12:
        raise ValueError("Closed contour has no defined interior")
    segments = [
        (min(a[0], b[0]), max(a[0], b[0]), min(a[1], b[1]), max(a[1], b[1]), i, a, b)
        for i, (a, b) in enumerate(zip(points, points[1:]))
    ]
    active = []
    checks = 0

    def orient(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    for item in sorted(segments):
        x0, x1, y0, y1, i, a, b = item
        active = [s for s in active if s[1] >= x0]
        for other in active:
            checks += 1
            if checks > 200000:
                raise ValueError("Contour simplicity check exceeds budget; use left/right normals")
            _, _, v0, v1, j, c, e = other
            if abs(i - j) == 1 or {i, j} == {0, len(segments) - 1}:
                continue
            if y1 < v0 or v1 < y0:
                continue
            oa, ob = orient(a, b, c), orient(a, b, e)
            oc, od = orient(c, e, a), orient(c, e, b)
            if oa * ob <= 0 and oc * od <= 0:
                raise ValueError("Self-intersecting contour has no unique outward normal; use left/right")
        active.append(item)
    return -1 if area > 0 else 1


def curve_frame(curve, distance, normal):
    points, closed, lengths = _curve_metrics(curve.d, curve.tolerance)
    _finite(distance)
    if normal not in ("left", "right", "outward"):
        raise ValueError("normal must be left, right or outward")
    if normal == "outward" and not closed:
        raise ValueError("Outward normals need a simple closed contour")
    point, tangent = curve.at(distance)
    sign = 1 if normal == "left" else -1
    if normal == "outward":
        sign = _simple_orientation(curve.d, curve.tolerance)
    d = distance % lengths[-1] if closed else max(0, min(lengths[-1], distance))
    return PathFrame(point, tangent, (-tangent[1] * sign, tangent[0] * sign), d)


def trim_curve(curve, start, end, wrap):
    points, closed, lengths = _curve_metrics(curve.d, curve.tolerance)
    length = lengths[-1]
    start, end = _point((start, end))
    if not 0 <= start <= length or not 0 <= end <= length:
        raise ValueError("Trim distances must lie in [0, length]")
    if wrap and not closed:
        raise ValueError("wrap requires a closed curve")
    if wrap and end <= start:
        end += length
    if wrap and end == start:
        end += length
    if end <= start:
        raise ValueError("Trim end must be after start")
    stations = [(s, p) for s, p in zip(lengths, points)]
    if end > length:
        stations += [(s + length, p) for s, p in zip(lengths[1:], points[1:])]
    result = [curve.at(start)[0]]
    result.extend(p for s, p in stations if start < s < end and p != result[-1])
    last = curve.at(end)[0]
    if last != result[-1]:
        result.append(last)
    if len(result) < 2:
        raise ValueError("Trimmed curve has no length")
    return Curve(_polyline(result, closed and abs(end - start - length) < 1e-9), curve.tolerance)


def ray_curve(curve, origin, direction, hit, normal):
    origin = _point(origin)
    direction = _unit(direction)
    if hit not in ("nearest", "farthest"):
        raise ValueError("hit must be nearest or farthest")
    points, _, lengths = _curve_metrics(curve.d, curve.tolerance)
    hits = []
    cross = lambda a, b: a[0] * b[1] - a[1] * b[0]
    for i, (a, b) in enumerate(zip(points, points[1:])):
        s = (b[0] - a[0], b[1] - a[1])
        q = (a[0] - origin[0], a[1] - origin[1])
        den = cross(direction, s)
        if abs(den) > 1e-10 * max(1, math.hypot(*s)):
            t = cross(q, s) / den
            u = cross(q, direction) / den
            if t >= -1e-9 and -1e-9 <= u <= 1 + 1e-9:
                hits.append((max(0, t), lengths[i] + max(0, min(1, u)) * (lengths[i + 1] - lengths[i])))
        elif abs(cross(q, direction)) < 1e-9:
            ta = sum(q[k] * direction[k] for k in (0, 1))
            tb = sum((b[k] - origin[k]) * direction[k] for k in (0, 1))
            if max(ta, tb) < 0:
                continue
            for t in (max(0, min(ta, tb)), max(ta, tb)):
                u = (t - ta) / (tb - ta)
                hits.append((t, lengths[i] + u * (lengths[i + 1] - lengths[i])))
    if not hits:
        raise ValueError("Ray does not intersect the selected contour")
    _, distance = (min if hit == "nearest" else max)(hits, key=lambda item: item[0])
    return curve.frame(distance, normal=normal)


def geometry_contour(geometry, subpath, tolerance):
    if type(subpath) is not int or subpath < 0:
        raise ValueError("subpath must be a nonnegative integer")
    node = geometry.element
    matrix = Matrix()
    while True:
        if any(node.get(k) not in (None, "none") for k in ("clip-path", "filter", "mask")):
            raise ValueError("Select the unclipped source geometry for contour queries")
        matrix = matrix.then(parse_transform(node.get("transform", "")))
        tag = node.tag.split("}")[-1]
        if tag != "g":
            break
        children = [c for c in node if c.tag.split("}")[-1] not in ("defs", "title", "desc", "metadata")]
        if len(children) != 1:
            # A labelled node (frame followed by text lines) uses its frame as outline.
            if (
                children
                and children[0].tag.split("}")[-1] not in ("text", "g")
                and (
                    all(c.tag.split("}")[-1] == "text" for c in children[1:]) or children[0].get("data-outline") == "1"
                )
            ):
                children = children[:1]
            else:
                raise ValueError("Select one component before querying its contour")
        node = children[0]
    n = lambda key, default="0": float(node.get(key, default))
    if tag == "path":
        d = node.get("d", "")
    elif tag in ("polyline", "polygon"):
        from ..atomize_svg_to_slide._geometry import numbers

        values = numbers(node.get("points", ""))
        if len(values) % 2:
            raise ValueError("Invalid contour points")
        d = _polyline(list(zip(values[::2], values[1::2])), tag == "polygon")
    elif tag == "line":
        d = _polyline([(n("x1"), n("y1")), (n("x2"), n("y2"))])
    elif tag in ("circle", "ellipse"):
        x, y = n("cx"), n("cy")
        rx = n("r") if tag == "circle" else n("rx")
        ry = rx if tag == "circle" else n("ry")
        d = f"M {x + rx} {y} A {rx} {ry} 0 1 1 {x - rx} {y} A {rx} {ry} 0 1 1 {x + rx} {y} Z"
    elif tag == "rect":
        x, y, w, h = n("x"), n("y"), n("width"), n("height")
        rx = min(w / 2, n("rx", node.get("ry", "0")))
        ry = min(h / 2, n("ry", node.get("rx", "0")))
        if rx <= 0 or ry <= 0:
            d = _polyline([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], True)
        else:
            d = (
                f"M {x + rx} {y} H {x + w - rx} A {rx} {ry} 0 0 1 {x + w} {y + ry} V {y + h - ry} "
                f"A {rx} {ry} 0 0 1 {x + w - rx} {y + h} H {x + rx} A {rx} {ry} 0 0 1 {x} {y + h - ry} V {y + ry} "
                f"A {rx} {ry} 0 0 1 {x + rx} {y} Z"
            )
    else:
        raise ValueError("Contour queries require path or primitive geometry")
    paths = []
    for op, values in path_segments(d):
        if op == "M":
            paths.append([])
        if not paths:
            raise ValueError("Contour must start with M")
        paths[-1].append(op + " " + " ".join(fmt(v) for v in values))
    if subpath >= len(paths):
        raise ValueError("Contour subpath does not exist")
    curve = Curve(" ".join(paths[subpath]), tolerance)
    if matrix == Matrix():
        return curve
    points, closed = curve.samples()
    return Curve(_polyline([matrix.point(*p) for p in points], closed), tolerance)
