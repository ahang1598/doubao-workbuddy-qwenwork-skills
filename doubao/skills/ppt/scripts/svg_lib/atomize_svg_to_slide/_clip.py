"""Native intersections for solid convex contours under one convex clip."""

from __future__ import annotations
import copy
import math
import xml.etree.ElementTree as ET
from ._geometry import Matrix, number, numbers, fmt, parse_transform, path_segments
from ._resources import name, resource_index, URL_REF
from ._bounds import paint_bounds, svg_bounds, mapped

EPS = 1e-9


def cross(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def area(p):
    return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(p, p[1:] + p[:1])) / 2


def convex(p):
    if len(p) < 3 or abs(area(p)) < EPS:
        return False
    turns = [cross(p[i - 1], p[i], p[(i + 1) % len(p)]) for i in range(len(p))]
    return all(v >= -EPS for v in turns) or all(v <= EPS for v in turns)


def contains(p, clip):
    return all(cross(a, b, p) >= -EPS for a, b in zip(clip, clip[1:] + clip[:1]))


def intersect(subject, clip):
    output = list(subject)
    for a, b in zip(clip, clip[1:] + clip[:1]):
        previous = output
        output = []
        if not previous:
            break
        start = previous[-1]
        sd = cross(a, b, start)
        for end in previous:
            ed = cross(a, b, end)
            if (ed >= -EPS) != (sd >= -EPS):
                t = sd / (sd - ed)
                output.append((start[0] + t * (end[0] - start[0]), start[1] + t * (end[1] - start[1])))
            if ed >= -EPS:
                output.append(end)
            start, sd = end, ed
    result = []
    for p in output:
        if not result or math.dist(p, result[-1]) > EPS:
            result.append(p)
    if len(result) > 1 and math.dist(result[0], result[-1]) <= EPS:
        result.pop()
    return result if len(result) >= 3 and abs(area(result)) > EPS else []


def polygon(node):
    n = name(node)

    def num(k, d="0"):
        return number(node.get(k, d))

    if n == "rect":
        if num("rx") or num("ry"):
            return None
        x, y, w, h = num("x"), num("y"), num("width"), num("height")
        if min(w, h) <= 0:
            return []
        return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    if n in ("polygon", "polyline"):
        v = numbers(node.get("points", ""))
        if len(v) % 2:
            return None
        pts = list(zip(v[::2], v[1::2]))
    elif n == "path":
        pts = []
        for op, v in path_segments(node.get("d", "")):
            if op == "M":
                if pts:
                    return None
                pts.append(tuple(v))
            elif op == "L":
                pts.append(tuple(v))
            elif op != "Z":
                return None
    else:
        return None
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts.pop()
    return pts


def clip_polygon(element, defs):
    refs = URL_REF.findall(element.get("clip-path", ""))
    resource = resource_index(defs).get(refs[0]) if len(refs) == 1 else None
    if resource is None or name(resource) != "clipPath":
        return None
    if any(resource.get(k) for k in ("clip-path", "filter", "mask", "style")):
        return None
    children = [n for n in resource if name(n) not in ("title", "desc")]
    if len(children) != 1:
        return None
    child = children[0]
    if child.get("display") == "none" or child.get("visibility") in ("hidden", "collapse"):
        return None
    if any(child.get(k) for k in ("clip-path", "filter", "mask", "style")):
        return None
    if child.get("clip-rule", resource.get("clip-rule", "nonzero")) != "nonzero":
        return None
    pts = polygon(child)
    if not pts or not convex(pts):
        return None
    matrix = parse_transform(resource.get("transform", "")).then(parse_transform(child.get("transform", "")))
    units = resource.get("clipPathUnits", "userSpaceOnUse")
    if units == "objectBoundingBox":
        box = paint_bounds(element)
        if box is None or min(box[2:]) <= 0:
            return None
        x, y, w, h = box
        matrix = Matrix(a=w, d=h, e=x, f=y).then(matrix)
    elif units != "userSpaceOnUse":
        return None
    pts = [matrix.point(*p) for p in pts]
    if not convex(pts):
        return None
    if area(pts) < 0:
        pts.reverse()
    return pts


def expand_clip(element, defs):
    """Return an unclipped local g, or None when SVG compositing is required."""
    from ._svg_input import _effective

    if element.get("clip-path") in (None, "none"):
        return None
    try:
        clip = clip_polygon(element, defs)
        if clip is None:
            return None
        out = ET.Element("g")
        if element.get("transform"):
            out.set("transform", element.get("transform"))

        def visit(node, inherited, matrix, root=False):
            current = _effective(node, inherited)
            n = name(node)
            if current.get("display") == "none":
                return
            if not root and current.get("clip-path") not in (None, "none"):
                raise ValueError("Nested clip")
            if any(
                current.get(k) not in (None, "none", "normal", "auto")
                for k in ("filter", "mask", "mix-blend-mode", "isolation")
            ):
                raise ValueError("Composited clip")
            if not root:
                matrix = matrix.then(parse_transform(current.get("transform", "")))
            current.attrib.pop("transform", None)
            current.attrib.pop("clip-path", None)
            if n in ("g", "svg"):
                if number(current.get("opacity", "1")) != 1:
                    raise ValueError("Group alpha")
                for child in node:
                    if name(child) not in ("defs", "title", "desc", "metadata"):
                        visit(child, current.attrib, matrix)
                return
            if current.get("visibility") in ("hidden", "collapse"):
                return
            if any(current.get(k) not in (None, "none") for k in ("marker-start", "marker-mid", "marker-end")):
                raise ValueError("Marked clip")
            # A bbox wholly inside the clip proves clipping has no effect.
            bounds = svg_bounds(current, defs, unknown_none=True)
            if bounds is not None:
                x, y, w, h = bounds
                box = mapped((x, y, x + w, y + h), matrix)
                if all(
                    contains(p, clip) for p in ((box[0], box[1]), (box[2], box[1]), (box[2], box[3]), (box[0], box[3]))
                ):
                    if matrix != Matrix():
                        current.set("transform", matrix.svg())
                    out.append(current)
                    return
            pts = polygon(current)
            if pts is None or (pts and not convex(pts)):
                raise ValueError("Complex clipped contour")
            if (
                current.get("stroke", "none") not in ("none", "transparent")
                and number(current.get("stroke-width", "1")) > 0
            ):
                raise ValueError("Clipping a stroke changes its outline")
            if current.get("fill-rule", "nonzero") != "nonzero" or "url(" in current.get("fill", ""):
                raise ValueError("Clipped paint needs original object coordinates")
            if current.get("fill", "#000000") in ("none", "transparent"):
                return
            pts = intersect([matrix.point(*p) for p in pts], clip)
            if not pts:
                return
            result = copy.deepcopy(current)
            result.tag = "polygon"
            for key in ("x", "y", "width", "height", "rx", "ry", "d", "points", "pathLength"):
                result.attrib.pop(key, None)
            result.set("points", " ".join(f"{fmt(x)},{fmt(y)}" for x, y in pts))
            result.attrib.setdefault("fill", "#000000")
            out.append(result)

        visit(element, {}, Matrix(), True)
        return out
    except (ValueError, TypeError, ZeroDivisionError):
        return None
