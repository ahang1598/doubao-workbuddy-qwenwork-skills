"""Exact dash geometry for straight contours; curves retain their SVG stroke."""

from __future__ import annotations

import copy
import math
import xml.etree.ElementTree as ET
from ._geometry import number, numbers, path_segments, fmt
from ._resources import name


def contours(element):
    n = name(element)

    def num(k, d="0"):
        return number(element.get(k, d))

    if n == "line":
        return [[(num("x1"), num("y1")), (num("x2"), num("y2"))]]
    if n in ("polyline", "polygon"):
        v = numbers(element.get("points", ""))
        if len(v) < 4 or len(v) % 2:
            raise ValueError("Invalid contour")
        p = list(zip(v[::2], v[1::2]))
        if n == "polygon":
            p.append(p[0])
        return [p]
    if n == "rect":
        if num("rx") or num("ry"):
            raise ValueError("Rounded contour")
        x, y, w, h = num("x"), num("y"), num("width"), num("height")
        return [[(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)]]
    if n == "path":
        result = []
        for op, v in path_segments(element.get("d", "")):
            if op == "M":
                result.append([tuple(v)])
            elif op == "L" and result:
                result[-1].append(tuple(v))
            elif op == "Z" and result:
                result[-1].append(result[-1][0])
            else:
                raise ValueError("Curved dash contour")
        return result
    raise ValueError("Unsupported dash contour")


def dash_path(element):
    pattern = numbers(element.get("stroke-dasharray", ""))
    if not pattern or min(pattern) < 0:
        raise ValueError("Invalid dash pattern")
    if len(pattern) % 2:
        pattern *= 2
    if sum(pattern) < 1e-12:
        return None
    offset = number(element.get("stroke-dashoffset", "0")) % sum(pattern)
    chunks = []
    steps = 0
    for points in contours(element):
        if len(points) < 2:
            continue
        idx = 0
        phase = offset
        while phase > 0 and phase >= pattern[idx]:
            phase -= pattern[idx]
            idx = (idx + 1) % len(pattern)
        remaining = pattern[idx] - phase
        active = []
        parts = []
        for a, b in zip(points, points[1:]):
            length = math.dist(a, b)
            if length < 1e-12:
                continue
            distance = 0
            while distance < length - 1e-10:
                steps += 1
                if steps > 20000:
                    raise ValueError("Dash expansion limit exceeded")
                start = (a[0] + (b[0] - a[0]) * distance / length, a[1] + (b[1] - a[1]) * distance / length)
                if remaining < 1e-10:
                    if idx % 2 == 0:
                        if not active:
                            parts.append([start, start])
                        else:
                            parts.append(active)
                            active = []
                    idx = (idx + 1) % len(pattern)
                    remaining = pattern[idx]
                    continue
                take = min(remaining, length - distance)
                distance += take
                remaining -= take
                end = (a[0] + (b[0] - a[0]) * distance / length, a[1] + (b[1] - a[1]) * distance / length)
                if idx % 2 == 0:
                    if not active:
                        active = [start]
                    active.append(end)
                elif active:
                    parts.append(active)
                    active = []
        if active:
            parts.append(active)
        # A new on-dash beginning exactly at the endpoint has a visible cap.
        if remaining < 1e-10 and idx % 2 == 1 and element.get("stroke-linecap", "butt") != "butt":
            parts.append([points[-1], points[-1]])
        # Join a dash crossing the closure seam instead of adding two end caps.
        if (
            len(parts) > 1
            and points[0] == points[-1]
            and math.dist(parts[0][0], points[0]) < 1e-8
            and math.dist(parts[-1][-1], points[0]) < 1e-8
        ):
            parts = [parts[-1] + parts[0][1:]] + parts[1:-1]
        chunks.extend(parts)
    return " ".join("M " + " L ".join(f"{fmt(x)} {fmt(y)}" for x, y in p) for p in chunks)


def can_dash(element):
    try:
        dash_path(element)
        return True
    except ValueError:
        return False


def native_dash(element, defs, converter):
    from ._path import _custom_shape_from_svg_path
    from ._arrow import _border_attrs_from_svg, _endpoint_decoration_xml, _marker_kind

    d = dash_path(element)
    cleaned = copy.deepcopy(element)
    for k in ("stroke-dasharray", "stroke-dashoffset"):
        cleaned.attrib.pop(k, None)
    if d is None:
        return converter(ET.tostring(cleaned, encoding="unicode"), defs)
    fills = ""
    if name(element) != "line" and element.get("fill", "none") not in ("none", "transparent"):
        base = copy.deepcopy(cleaned)
        base.set("stroke", "none")
        for k in ("marker-start", "marker-mid", "marker-end"):
            base.attrib.pop(k, None)
        fills = converter(ET.tostring(base, encoding="unicode"), defs)
    for k in ("marker-start", "marker-mid", "marker-end"):
        cleaned.attrib.pop(k, None)
    tag = ET.tostring(cleaned, encoding="unicode")
    dots = []
    segments = []
    pending = None
    for op, values in path_segments(d):
        if op == "M":
            pending = tuple(values)
        elif op == "L" and pending == tuple(values):
            dots.append(pending)
            pending = None
            continue
        if op == "M":
            segments.append((op, values))
        else:
            segments.append((op, values))
            pending = None
    # Remove moveto-only dot subpaths from the stroked contour.
    filtered = []
    for i, (op, v) in enumerate(segments):
        if op == "M" and (i + 1 == len(segments) or segments[i + 1][0] == "M"):
            continue
        filtered.append(op + " " + " ".join(fmt(n) for n in v))
    d = " ".join(filtered)
    stroke = element.get("stroke", "none")
    sw = number(element.get("stroke-width", "1"))
    alpha = number(element.get("opacity", "1")) * number(element.get("stroke-opacity", "1"))
    body = (
        _custom_shape_from_svg_path(
            d,
            tag,
            fill="none",
            stroke=stroke,
            stroke_w=sw,
            opacity=number(element.get("opacity", "1")),
            all_defs=defs,
            border_attrs=_border_attrs_from_svg(tag),
        )
        if d
        else ""
    )
    body = body or ""
    if dots and element.get("stroke-linecap", "butt") != "butt":
        # Slides' custom-path renderer does not reliably render repeated tiny
        # arc contours. Native ellipse/rect atoms are stable at this scale.
        from ._convert import convert_circle, convert_rect

        r = sw / 2
        for x, y in dots:
            if element.get("stroke-linecap") == "square":
                dot = ET.Element("rect", {"x": fmt(x - r), "y": fmt(y - r), "width": fmt(sw), "height": fmt(sw)})
                convert = convert_rect
            else:
                dot = ET.Element("circle", {"cx": fmt(x), "cy": fmt(y), "r": fmt(r)})
                convert = convert_circle
            dot.set("fill", stroke)
            dot.set("stroke", "none")
            dot.set("opacity", fmt(alpha))
            body += convert(ET.tostring(dot, encoding="unicode"), defs)
    cs = contours(element)
    for key, pt, ref in [("marker-start", cs[0][0], cs[0][1]), ("marker-end", cs[-1][-1], cs[-1][-2])]:
        if element.get(key):
            body += _endpoint_decoration_xml(
                *pt, *ref, marker_kind=_marker_kind(element.get(key)), stroke=stroke, stroke_w=sw, opacity=alpha
            )
    return fills + body
