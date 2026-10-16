"""Expand document-local use/symbol instances with SVG inheritance and viewports."""

from __future__ import annotations

import copy
import xml.etree.ElementTree as ET
from ._geometry import number, numbers, fmt
from ._resources import name, XLINK, URL_REF


def expand_instances(root):
    index = {n.get("id"): n for n in root.iter() if n.get("id")}
    vb = numbers(root.get("viewBox", "0 0 900 336"))
    definitions = ET.Element("defs")
    counter = 0
    expanded = 0

    def length(value, axis):
        return number(value[:-1]) * vb[axis + 2] / 100 if value.endswith("%") else number(value)

    def visit(node, chain=()):
        nonlocal counter, expanded
        if name(node) != "use":
            result = copy.deepcopy(node)
            for c in list(result):
                result.remove(c)
            for c in node:
                result.append(visit(c, chain))
            return result
        expanded += 1
        if expanded > 10000:
            raise ValueError("SVG use expansion exceeds 10000 instances")
        href = node.get("href", node.get(XLINK, ""))
        if not href.startswith("#"):
            raise ValueError("use supports document-local #id references only")
        key = href[1:]
        if key in chain:
            raise ValueError("Cyclic SVG use reference: " + " -> ".join((*chain, key)))
        if key not in index:
            raise ValueError("Unknown SVG use reference: " + key)
        target = index[key]
        if name(target) not in (
            "g",
            "symbol",
            "svg",
            "rect",
            "circle",
            "ellipse",
            "line",
            "path",
            "polygon",
            "polyline",
            "text",
            "use",
        ):
            raise ValueError("Unsupported SVG use target: " + name(target))
        attrs = {k: v for k, v in node.attrib.items() if k not in ("href", XLINK, "x", "y", "width", "height", "id")}
        x = length(node.get("x", "0"), 0)
        y = length(node.get("y", "0"), 1)
        attrs["transform"] = attrs.get("transform", "") + f" translate({fmt(x)} {fmt(y)})"
        wrapper = ET.Element("g", attrs)
        if node.get("id"):
            wrapper.set("id", node.get("id"))
        item = visit(target, (*chain, key))
        item.attrib.pop("id", None)
        # Repeated instances need distinct internal resources when retained in
        # the same composited SVG. Rewrite local references along with IDs.
        counter += 1
        ids = {n.get("id"): f"atomizer-use-{counter}-{n.get('id')}" for n in item.iter() if n.get("id")}
        while any(value in index for value in ids.values()):
            counter += 1
            ids = {old: f"atomizer-use-{counter}-{old}" for old in ids}
        for descendant in item.iter():
            if descendant.get("id"):
                descendant.set("id", ids[descendant.get("id")])
            for attr, value in list(descendant.attrib.items()):
                value = URL_REF.sub(lambda m: "url(#" + ids.get(m[1], m[1]) + ")", value)
                if attr in ("href", XLINK) and value.startswith("#"):
                    value = "#" + ids.get(value[1:], value[1:])
                descendant.set(attr, value)

        if name(target) in ("symbol", "svg"):
            view = numbers(target.get("viewBox", f"0 0 {vb[2]} {vb[3]}"))
            if len(view) != 4 or min(view[2:]) <= 0:
                raise ValueError("Invalid symbol viewBox")
            w = length(node.get("width", target.get("width", str(vb[2]))), 0)
            h = length(node.get("height", target.get("height", str(vb[3]))), 1)
            if min(w, h) <= 0:
                return ET.Element("g")
            vx, vy, vw, vh = view
            sx = w / vw
            sy = h / vh
            aspect = target.get("preserveAspectRatio", "xMidYMid meet").split()
            align = aspect[0]
            mode = aspect[1] if len(aspect) > 1 else "meet"
            ox = oy = 0
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
                    raise ValueError("Unsupported symbol preserveAspectRatio")
                sx = sy = min(sx, sy) if mode == "meet" else max(sx, sy)
                ox = (w - vw * sx) * {"Min": 0, "Mid": 0.5, "Max": 1}[align[1:4]]
                oy = (h - vh * sy) * {"Min": 0, "Mid": 0.5, "Max": 1}[align[5:8]]
            item.tag = "g"
            for k in ("viewBox", "width", "height", "x", "y", "preserveAspectRatio"):
                item.attrib.pop(k, None)
            frame = ET.Element(
                "g",
                {
                    "transform": f"translate({fmt(ox)} {fmt(oy)}) scale({fmt(sx)} {fmt(sy)}) translate({fmt(-vx)} {fmt(-vy)})"
                },
            )
            frame.append(item)
            if target.get("overflow", "hidden") != "visible":
                from ._bounds import svg_bounds

                raw = ET.tostring(frame, encoding="unicode")
                b = svg_bounds(raw, viewport=(0, 0, w, h), unknown_none=True)
                if b is None or b[0] < 0 or b[1] < 0 or b[0] + b[2] > w or b[1] + b[3] > h:
                    counter += 1
                    clipid = f"atomizer-symbol-viewport-{counter}"
                    while clipid in index:
                        counter += 1
                        clipid = f"atomizer-symbol-viewport-{counter}"
                    clip = ET.SubElement(definitions, "clipPath", {"id": clipid})
                    ET.SubElement(clip, "rect", {"width": fmt(w), "height": fmt(h)})
                    clipped = ET.Element("g", {"clip-path": f"url(#{clipid})"})
                    clipped.append(frame)
                    frame = clipped
            wrapper.append(frame)
        else:
            wrapper.append(item)
        return wrapper

    result = visit(root)
    if len(definitions):
        result.append(definitions)
    return result
