"""Expand supported marker geometry at the true path endpoint and orientation."""

from __future__ import annotations

import copy
from functools import lru_cache
import math
import re
import xml.etree.ElementTree as ET

from ._geometry import number, numbers, path_segments, rotate, scale, translate, transform_element


@lru_cache(maxsize=64)
def _resources(defs):
    return {e.get("id"): e for e in ET.fromstring(defs)} if defs else {}


def _points(element):
    name = element.tag.split("}")[-1]
    if name == "line":
        return [
            (number(element.get("x1", "0")), number(element.get("y1", "0"))),
            (number(element.get("x2", "0")), number(element.get("y2", "0"))),
        ]
    if name in ("polygon", "polyline"):
        v = numbers(element.get("points", ""))
        if len(v) % 2:
            raise ValueError("Invalid points")
        return list(zip(v[::2], v[1::2]))
    if name == "rect":
        x = number(element.get("x", "0"))
        y = number(element.get("y", "0"))
        w = number(element.get("width", "0"))
        h = number(element.get("height", "0"))
        return [(x, y), (x + w, y + h)]
    if name in ("circle", "ellipse"):
        x = number(element.get("cx", "0"))
        y = number(element.get("cy", "0"))
        rx = number(element.get("r", element.get("rx", "0")))
        ry = number(element.get("r", element.get("ry", "0")))
        return [(x - rx, y - ry), (x + rx, y + ry)]
    if name == "path":
        pts = []
        for op, v in path_segments(element.get("d", "")):
            if op == "A":
                raise ValueError("Arc marker bounds")
            pts.extend(zip(v[::2], v[1::2]))
        return pts
    raise ValueError("Unsupported marker geometry")


def _placements(element):
    """Original vertices and exact endpoint tangents (not sampled arc joints)."""
    name = element.tag.split("}")[-1]
    segments = []
    closed = name == "polygon"
    if name in ("line", "polyline", "polygon"):
        pts = _points(element)
        if name == "polygon" and pts:
            pts.append(pts[0])
        for start, end in zip(pts, pts[1:]):
            v = (end[0] - start[0], end[1] - start[1])
            segments.append((start, end, v, v))
    elif name == "path":
        current = None
        start = None
        for op, v in path_segments(element.get("d", "")):
            if op == "M":
                if current is not None:
                    raise ValueError("Multiple marker subpaths")
                current = start = tuple(v)
                continue
            if current is None:
                raise ValueError("Missing initial moveto")
            closed = op == "Z"
            if op == "Z":
                end = start
                refs = [end]
            else:
                end = tuple(v[-2:])
                if op == "A":
                    from ._geometry import arc_to_cubics

                    curves = arc_to_cubics(*current, *v)
                    if curves and curves[0][0] == "C":
                        refs = [tuple(curves[0][1][:2]), tuple(curves[-1][1][2:4]), end]
                    else:
                        refs = [end]
                else:
                    refs = list(zip(v[::2], v[1::2]))
            first = next((p for p in refs if p != current), end)
            last = next((p for p in reversed([current] + refs[:-1]) if p != end), current)
            segments.append(
                (current, end, (first[0] - current[0], first[1] - current[1]), (end[0] - last[0], end[1] - last[1]))
            )
            current = end
    else:
        raise ValueError("Unsupported marker host")
    if not segments:
        raise ValueError("Empty marker host")

    def direction(indices, which):
        for i in indices:
            dx, dy = segments[i][which]
            if math.hypot(dx, dy) > 1e-12:
                return math.atan2(dy, dx)
        return None

    result = [("marker-start", segments[0][0], math.degrees(direction(range(len(segments)), 2) or 0))]
    for i in range(len(segments) - 1) if element.get("marker-mid") not in (None, "none") else ():
        incoming = direction(range(i, -1, -1), 3)
        outgoing = direction(range(i + 1, len(segments)), 2)
        if incoming is None:
            angle = outgoing or 0
        elif outgoing is None:
            angle = incoming
        else:
            dx = math.cos(incoming) + math.cos(outgoing)
            dy = math.sin(incoming) + math.sin(outgoing)
            if math.hypot(dx, dy) < 1e-10:
                raise ValueError("Ambiguous reversal at marker-mid")
            angle = math.atan2(dy, dx)
        result.append(("marker-mid", segments[i][1], math.degrees(angle)))
    end_angle = direction(range(len(segments) - 1, -1, -1), 3) or 0
    if closed:
        # SVG closes the terminal join: its end marker uses the joining tangent
        # bisector, while marker-start retains the first outgoing direction.
        outgoing = direction(range(len(segments)), 2) or 0
        dx = math.cos(end_angle) + math.cos(outgoing)
        dy = math.sin(end_angle) + math.sin(outgoing)
        if math.hypot(dx, dy) < 1e-10:
            raise ValueError("Ambiguous closed marker join")
        end_angle = math.atan2(dy, dx)
    result.append(("marker-end", segments[-1][1], math.degrees(end_angle)))
    return result


def expand_markers(element: ET.Element, defs: str):
    """Return [host, endpoint atoms], or None to retain the marked host as SVG."""
    if not any(element.get(k) for k in ("marker-start", "marker-mid", "marker-end")):
        return [element]
    host = copy.deepcopy(element)
    output = []
    for key in ("marker-start", "marker-mid", "marker-end"):
        if host.get(key) == "none":
            host.attrib.pop(key)
    try:
        resources = _resources(defs)
        selected = []
        for key in ("marker-start", "marker-mid", "marker-end"):
            ref = element.get(key)
            if not ref or ref == "none":
                continue
            match = re.fullmatch(r"url\(#([^)]+)\)", ref.strip())
            marker = resources.get(match[1]) if match else None
            if marker is None or marker.tag.split("}")[-1] != "marker":
                return None
            visible = [e for e in marker if e.tag.split("}")[-1] not in ("title", "desc")]
            if not visible:
                if key == "marker-mid":
                    return None
                continue
            selected.append((key, marker, visible))
        if not selected:
            return [host]
        if number(element.get("opacity", "1")) != 1 or any(
            element.get(k) for k in ("filter", "clip-path", "mask", "transform")
        ):
            return None
        placements = _placements(element)
        for key, marker, children in selected:
            if any(marker.get(k) for k in ("style", "class", "filter", "clip-path", "mask", "transform", "opacity")):
                return None
            if marker.get("markerUnits", "strokeWidth") not in ("strokeWidth", "userSpaceOnUse"):
                return None
            unit = (
                number(element.get("stroke-width", "1"))
                if marker.get("markerUnits", "strokeWidth") == "strokeWidth"
                else 1
            )
            mw = number(marker.get("markerWidth", "3"))
            mh = number(marker.get("markerHeight", "3"))
            if min(mw, mh, unit) <= 0:
                return None
            vb = numbers(marker.get("viewBox", f"0 0 {mw} {mh}"))
            if len(vb) != 4 or min(vb[2:]) <= 0:
                return None
            vx, vy, vw, vh = vb
            aspect = marker.get("preserveAspectRatio", "xMidYMid meet").split()
            if aspect not in (["xMidYMid"], ["xMidYMid", "meet"], ["none"]):
                return None
            if aspect == ["none"] and abs(mw / vw - mh / vh) > 1e-9:
                return None
            vs = min(mw / vw, mh / vh)
            ox = (mw - vw * vs) / 2
            oy = (mh - vh * vs) / 2
            refx = number(marker.get("refX", "0"))
            refy = number(marker.get("refY", "0"))
            for placement_key, pos, angle in placements:
                if placement_key != key:
                    continue
                orient = marker.get("orient", "0")
                if orient == "auto-start-reverse":
                    if key == "marker-start":
                        angle += 180
                elif orient != "auto":
                    angle = number(orient.removesuffix("deg"))
                transform = translate(*pos).then(rotate(angle)).then(scale(unit * vs)).then(translate(-refx, -refy))
                for child in children:
                    atom = copy.deepcopy(child)
                    for attr in (
                        "fill",
                        "stroke",
                        "stroke-width",
                        "fill-opacity",
                        "stroke-opacity",
                        "stroke-linecap",
                        "stroke-linejoin",
                    ):
                        if attr not in atom.attrib and attr in marker.attrib:
                            atom.set(attr, marker.get(attr))
                    atom.attrib.setdefault("fill", "#000000")
                    atom.attrib.setdefault("stroke", "none")
                    for attr in ("fill", "stroke"):
                        val = atom.get(attr)
                        if val == "context-stroke":
                            atom.set(attr, element.get("stroke", "none"))
                        elif val == "context-fill":
                            atom.set(attr, element.get("fill", "#000000"))
                    if any(
                        atom.get(k) for k in ("filter", "mask", "clip-path", "style", "class", "transform", "opacity")
                    ):
                        return None
                    if any("url(" in atom.get(k, "") for k in ("fill", "stroke")):
                        return None
                    if atom.get("display") == "none" or atom.get("visibility") in ("hidden", "collapse"):
                        continue
                    if atom.tag.split("}")[-1] == "line" and atom.get("stroke") == "none":
                        continue
                    if atom.tag.split("}")[-1] == "polyline" and atom.get("fill") != "none":
                        return None
                    if any(number(atom.get(k, "1")) != 1 for k in ("fill-opacity", "stroke-opacity")):
                        return None
                    pts = _points(atom)
                    if not pts:
                        return None
                    xs = [(x - vx) * vs + ox for x, y in pts]
                    ys = [(y - vy) * vs + oy for x, y in pts]
                    pad_x = pad_y = 0.0
                    if atom.get("stroke") != "none":
                        half = number(atom.get("stroke-width", "1")) * vs / 2
                        if atom.tag.split("}")[-1] == "line" and atom.get("stroke-linecap", "butt") == "butt":
                            dx = pts[1][0] - pts[0][0]
                            dy = pts[1][1] - pts[0][1]
                            length = math.hypot(dx, dy)
                            if not length:
                                return None
                            pad_x = abs(dy) / length * half
                            pad_y = abs(dx) / length * half
                        else:
                            limit = (
                                number(atom.get("stroke-miterlimit", "4"))
                                if (
                                    atom.tag.split("}")[-1] in ("polygon", "polyline", "path")
                                    and atom.get("stroke-linejoin", "miter") == "miter"
                                )
                                else 1
                            )
                            pad_x = pad_y = half * max(1, limit)
                    if marker.get("overflow", "hidden") != "visible" and (
                        min(xs) - pad_x < -1e-8
                        or max(xs) + pad_x > mw + 1e-8
                        or min(ys) - pad_y < -1e-8
                        or max(ys) + pad_y > mh + 1e-8
                    ):
                        return None
                    output.append(transform_element(atom, transform))
            host.attrib.pop(key, None)
        return [host] + output
    except (ValueError, ET.ParseError):
        return None
