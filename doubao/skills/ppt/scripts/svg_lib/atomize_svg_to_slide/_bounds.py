"""Conservative ink bounds for local SVG atoms (no rasterization or subprocess)."""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from ._geometry import number, numbers, parse_transform, path_segments
from ._resources import name, resource_index, URL_REF


def union(boxes):
    boxes = [b for b in boxes if b is not None]
    if not boxes:
        return None
    return min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)


def pad(box, amount):
    return box[0] - amount, box[1] - amount, box[2] + amount, box[3] + amount


def mapped(box, matrix):
    pts = [matrix.point(x, y) for x in (box[0], box[2]) for y in (box[1], box[3])]
    return min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)


def _marker_bounds(node, attrs, index, defs):
    """Bound marker ink in the host's local axes, independently of conversion."""
    from ._markers import _placements, expand_markers
    from ._geometry import translate, rotate, scale

    host = ET.Element(node.tag, attrs)
    host.attrib.pop("transform", None)
    placements = _placements(host)
    boxes = []
    for key, pos, angle in placements:
        ref = attrs.get(key)
        if ref in (None, "none"):
            continue
        refs = URL_REF.findall(ref)
        if len(refs) != 1 or refs[0] not in index:
            raise ValueError("Unknown marker")
        marker = index[refs[0]]
        if name(marker) != "marker":
            raise ValueError("Not a marker")
        if any(marker.get(k) for k in ("style", "class", "transform", "filter", "href")):
            raise ValueError("Unknown marker viewport effects")
        if marker.get("overflow", "hidden") == "visible":
            # No viewport clip: use actual supported geometry, including stroke.
            plain = ET.Element(node.tag, attrs)
            for k in ("transform", "opacity", "filter", "clip-path", "mask"):
                plain.attrib.pop(k, None)
            atoms = expand_markers(plain, defs)
            if atoms is None or any(any(a.get(k) for k in ("marker-start", "marker-mid", "marker-end")) for a in atoms):
                raise ValueError("Unknown visible marker ink")
            for atom in atoms[1:]:
                b = svg_bounds(atom, defs, unknown_none=True)
                if b is None:
                    raise ValueError("Unknown visible marker bounds")
                boxes.append((b[0], b[1], b[0] + b[2], b[1] + b[3]))
            return boxes
        if marker.get("overflow", "hidden") not in ("hidden", "scroll", "auto"):
            raise ValueError("Unknown marker overflow")
        units = marker.get("markerUnits", "strokeWidth")
        if units not in ("strokeWidth", "userSpaceOnUse"):
            raise ValueError("Unknown marker units")
        unit = number(attrs.get("stroke-width", "1")) if units == "strokeWidth" else 1
        mw, mh = number(marker.get("markerWidth", "3")), number(marker.get("markerHeight", "3"))
        if min(mw, mh, unit) <= 0:
            continue
        vb = numbers(marker.get("viewBox", f"0 0 {mw} {mh}"))
        if len(vb) != 4 or min(vb[2:]) <= 0:
            raise ValueError("Invalid marker viewBox")
        vx, vy, vw, vh = vb
        sx, sy = mw / vw, mh / vh
        ox = oy = 0
        aspect = marker.get("preserveAspectRatio", "xMidYMid meet").split()
        if not aspect:
            raise ValueError("Empty marker aspect ratio")
        align, mode = aspect[0], aspect[1] if len(aspect) > 1 else "meet"
        if align != "none":
            if align not in (
                "xMinYMin",
                "xMidYMin",
                "xMaxYMin",
                "xMinYMid",
                "xMidYMid",
                "xMaxYMid",
                "xMinYMax",
                "xMidYMax",
                "xMaxYMax",
            ) or mode not in ("meet", "slice"):
                raise ValueError("Unknown marker aspect ratio")
            sx = sy = min(sx, sy) if mode == "meet" else max(sx, sy)
            ox = (mw - vw * sx) * {"Min": 0, "Mid": 0.5, "Max": 1}[align[1:4]]
            oy = (mh - vh * sy) * {"Min": 0, "Mid": 0.5, "Max": 1}[align[5:8]]
        rx = (number(marker.get("refX", "0")) - vx) * sx + ox
        ry = (number(marker.get("refY", "0")) - vy) * sy + oy
        orient = marker.get("orient", "0")
        if orient == "auto-start-reverse":
            if key == "marker-start":
                angle += 180
        elif orient != "auto":
            angle = number(orient.removesuffix("deg"))
        transform = translate(*pos).then(rotate(angle)).then(scale(unit)).then(translate(-rx, -ry))
        boxes.append(mapped((0, 0, mw, mh), transform))
    return boxes


def _unit_roots(a, b, c):
    """Interior roots of a quadratic, with a stable linear limit."""
    scale = max(abs(a), abs(b), abs(c))
    if not scale:
        return ()
    a, b, c = a / scale, b / scale, c / scale
    if abs(a) < 1e-14:
        roots = () if abs(b) < 1e-14 else (-c / b,)
    else:
        discriminant = b * b - 4 * a * c
        if discriminant < -1e-14:
            return ()
        q = -0.5 * (b + math.copysign(math.sqrt(max(0, discriminant)), b))
        roots = (-b / (2 * a),) if q == 0 else (q / a, c / q)
    return (t for t in roots if 0 < t < 1)


def _bezier_extrema(controls):
    """Evaluate only derivative roots; control points are not curve extrema."""
    parameters = set()
    for axis in (0, 1):
        differences = [b[axis] - a[axis] for a, b in zip(controls, controls[1:])]
        if len(differences) == 2:
            a, b = differences
            parameters.update(_unit_roots(0, b - a, a))
        else:
            a, b, c = differences
            parameters.update(_unit_roots(a - 2 * b + c, 2 * (b - a), a))
    for t in parameters:
        points = controls
        while len(points) > 1:
            points = [((1 - t) * a[0] + t * b[0], (1 - t) * a[1] + t * b[1]) for a, b in zip(points, points[1:])]
        yield points[0]


def _arc_extrema(current, values):
    """Extrema of an SVG endpoint arc, restricted to its actual sweep."""
    rx, ry, rotation, large, sweep, x, y = values
    rx, ry = abs(rx), abs(ry)
    if not rx or not ry or current == (x, y):
        return
    phi = math.radians(rotation % 360)
    c, s = math.cos(phi), math.sin(phi)
    dx, dy = (current[0] - x) / 2, (current[1] - y) / 2
    xp, yp = c * dx + s * dy, -s * dx + c * dy
    u, v = xp / rx, yp / ry
    distance = math.hypot(u, v)
    if not distance:
        return
    if not math.isfinite(distance):
        raise ValueError("Arc radius correction is not finite")
    if distance > 1:
        rx *= distance
        ry *= distance
        u /= distance
        v /= distance
        distance = 1
    # Normalized coordinates avoid products of squared radii and cancellation
    # when radii must grow to span the endpoints.
    factor = math.sqrt(max(0, 1 - distance * distance))
    if bool(large) == bool(sweep):
        factor = -factor
    cxp, cyp = rx * (v / distance) * factor, -ry * (u / distance) * factor
    cx = c * cxp - s * cyp + (current[0] + x) / 2
    cy = s * cxp + c * cyp + (current[1] + y) / 2
    start = math.atan2((yp - cyp) / ry, (xp - cxp) / rx)
    end = math.atan2((-yp - cyp) / ry, (-xp - cxp) / rx)
    delta = end - start
    if sweep and delta < 0:
        delta += math.tau
    elif not sweep and delta > 0:
        delta -= math.tau
    # x(t)=cx+A cos(t)+B sin(t), and similarly for y(t).
    angles = (math.atan2(-ry * s, rx * c), math.atan2(ry * c, rx * s))
    for angle in angles:
        for candidate in (angle, angle + math.pi):
            offset = ((candidate - start) if sweep else (start - candidate)) % math.tau
            if offset <= abs(delta) + 1e-12:
                yield (
                    cx + rx * math.cos(candidate) * c - ry * math.sin(candidate) * s,
                    cy + rx * math.cos(candidate) * s + ry * math.sin(candidate) * c,
                )


def path_bounds(d):
    """Geometric x/y/min/max bounds, shared by drawing, paints and conversion."""
    points = []
    current = start = (0, 0)
    for op, values in path_segments(d):
        if op == "M":
            current = start = tuple(values)
            continue
        if op == "Z":
            points.extend((current, start))
            current = start
            continue
        end = tuple(values[-2:])
        if op == "A" and current == end:
            continue  # SVG omits an arc whose endpoints coincide.
        points.extend((current, end))
        if op in ("Q", "C"):
            controls = [current] + list(zip(values[::2], values[1::2]))
            points.extend(_bezier_extrema(controls))
        elif op == "A":
            points.extend(_arc_extrema(current, values))
        current = end
    if not points:
        return None
    return (min(p[0] for p in points), min(p[1] for p in points), max(p[0] for p in points), max(p[1] for p in points))


def svg_bounds(source, defs="", viewport=(0, 0, 900, 336), unknown_none=False, *, diagnostics=None):
    """Return x/y/w/h, using the source viewport only for unknown geometry."""
    root = ET.fromstring(source) if isinstance(source, str) else source
    index = resource_index(defs)

    class Unknown(ValueError):
        pass

    def walk(node, inherited):
        attrs = dict(inherited)
        attrs.update(node.attrib)
        for item in node.get("style", "").split(";"):
            k, sep, v = item.partition(":")
            if sep:
                attrs[k.strip()] = v.strip()
        if attrs.get("display") == "none":
            return None
        n = name(node)
        if n in ("defs", "title", "desc", "metadata"):
            return None

        def num(k, default="0"):
            return number(attrs.get(k, default))

        if n in ("g", "svg"):
            child_style = {
                k: v
                for k, v in attrs.items()
                if k
                in (
                    "fill",
                    "stroke",
                    "stroke-width",
                    "stroke-linecap",
                    "stroke-linejoin",
                    "stroke-miterlimit",
                    "font-size",
                    "font-family",
                    "font-weight",
                    "font-style",
                    "text-anchor",
                    "letter-spacing",
                    "dominant-baseline",
                    "alignment-baseline",
                    "baseline-shift",
                    "writing-mode",
                    "direction",
                    "unicode-bidi",
                )
            }
            box = union([walk(c, child_style) for c in node])
        elif n == "rect":
            x, y, w, h = num("x"), num("y"), num("width"), num("height")
            box = (x, y, x + w, y + h)
        elif n in ("circle", "ellipse"):
            x, y = num("cx"), num("cy")
            rx = num("r") if n == "circle" else num("rx")
            ry = rx if n == "circle" else num("ry")
            box = (x - rx, y - ry, x + rx, y + ry)
        elif n == "line":
            box = (
                min(num("x1"), num("x2")),
                min(num("y1"), num("y2")),
                max(num("x1"), num("x2")),
                max(num("y1"), num("y2")),
            )
        elif n in ("polygon", "polyline"):
            v = numbers(attrs.get("points", ""))
            if len(v) < 2 or len(v) % 2:
                raise Unknown("invalid_polygon_points")
            box = (min(v[::2]), min(v[1::2]), max(v[::2]), max(v[1::2]))
        elif n == "path":
            box = path_bounds(attrs.get("d", ""))
        elif n == "text":
            # Explicit or rich tspans are handled by the text layout machinery.
            # Unknown layout must not be cropped using a guessed glyph width.
            if len(node):
                raise Unknown("complex_text_layout")
            from ._font_metrics import measure_text, baseline_offset
            from ._text_layout import native_text_baseline

            baseline = native_text_baseline(ET.Element("text", attrs))
            if baseline is None:
                raise Unknown("complex_text_baseline")
            fs = num("font-size", "16")
            text = node.text or ""
            metric = measure_text(
                text,
                attrs.get("font-family", "sans-serif"),
                fs,
                attrs.get("font-weight", "normal"),
                attrs.get("font-style", "normal"),
            )
            if metric is None:
                raise Unknown("font_metrics_unavailable")
            x, y = num("x"), num("y") + baseline_offset(baseline, fs, metric)
            w = metric.advance + max(0, len(text) - 1) * num("letter-spacing")
            anchor = attrs.get("text-anchor", "start")
            x -= w / 2 if anchor == "middle" else w if anchor == "end" else 0
            box = (x + min(0, metric.left), y + metric.top, x + max(w, metric.right), y + metric.bottom)
        else:
            raise Unknown("unsupported_geometry:" + n)
        if box is None:
            return None
        geometric = box
        if n not in ("g", "svg") and attrs.get("stroke", "none") != "none":
            sw = max(0, num("stroke-width", "1")) / 2
            if n in ("path", "polygon", "polyline") and attrs.get("stroke-linejoin", "miter") == "miter":
                sw *= max(1, num("stroke-miterlimit", "4"))
            box = pad(box, sw)
        if any(attrs.get(k) not in (None, "none") for k in ("marker-start", "marker-mid", "marker-end")):
            box = union([box] + _marker_bounds(node, attrs, index, defs))
        effect = attrs.get("filter", "none")
        if effect != "none":
            refs = URL_REF.findall(effect)
            if len(refs) != 1 or refs[0] not in index:
                raise Unknown("unresolved_filter")
            f = index[refs[0]]
            from ._resources import inherited_resource

            f = inherited_resource(f, index)
            if f is None:
                raise Unknown("unresolved_filter_inheritance")
            gx, gy, gr, gb = geometric
            gw = gr - gx
            gh = gb - gy
            obj = f.get("filterUnits", "objectBoundingBox") == "objectBoundingBox"

            def length(k, default, axis, position):
                value = f.get(k, default)
                if obj:
                    ratio = number(value[:-1]) / 100 if value.endswith("%") else number(value)
                    return ratio * (gw if axis == 0 else gh) + ((gx if axis == 0 else gy) if position else 0)
                if value.endswith("%"):
                    return number(value[:-1]) / 100 * viewport[axis + 2] + (viewport[axis] if position else 0)
                return number(value)

            fx = length("x", "-10%", 0, True)
            fy = length("y", "-10%", 1, True)
            fw = length("width", "120%", 0, False)
            fh = length("height", "120%", 1, False)
            box = union([box, (fx, fy, fx + fw, fy + fh)])
        return mapped(box, parse_transform(node.get("transform", attrs.get("transform", ""))))

    reason = None
    try:
        box = walk(root, {})
    except (ValueError, TypeError, OverflowError) as error:
        box = None
        reason = str(error) or type(error).__name__
    if diagnostics is not None:
        diagnostics.update(
            status="unknown" if box is None else "bounded",
            reason=reason or ("empty_geometry" if box is None else "geometry_stroke_marker_filter"),
            source_viewport=list(viewport),
        )
    if box is None:
        return None if unknown_none else tuple(viewport)
    box = pad(box, 1.0)  # antialias fringe
    return box[0], box[1], max(0.01, box[2] - box[0]), max(0.01, box[3] - box[1])


def paint_bounds(element):
    """Exact geometric object bbox (no stroke/filter), in the element's axes."""
    n = name(element)

    def num(k, d="0"):
        return number(element.get(k, d))

    try:
        if n == "rect":
            return num("x"), num("y"), num("width"), num("height")
        if n in ("circle", "ellipse"):
            rx = num("r") if n == "circle" else num("rx")
            ry = rx if n == "circle" else num("ry")
            return num("cx") - rx, num("cy") - ry, 2 * rx, 2 * ry
        if n in ("polygon", "polyline"):
            v = numbers(element.get("points", ""))
            if len(v) < 4 or len(v) % 2:
                return None
            return min(v[::2]), min(v[1::2]), max(v[::2]) - min(v[::2]), max(v[1::2]) - min(v[1::2])
        if n != "path":
            return None
        box = path_bounds(element.get("d", ""))
        if box is None:
            return None
        x, y, right, bottom = box
        return x, y, right - x, bottom - y
    except (ValueError, TypeError):
        return None
