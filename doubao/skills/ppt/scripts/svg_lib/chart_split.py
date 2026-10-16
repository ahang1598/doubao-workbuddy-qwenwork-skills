"""Semi-editable chart placement: chart SVG -> local SVG layers + native text and color blocks."""

from __future__ import annotations

import copy
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from ._common import _estimate_label_width_px
from .atomize_svg_to_slide import atomize_svg_to_slide, compose_slide
from .atomize_svg_to_slide._bounds import path_bounds
from .atomize_svg_to_slide._config import _CFG
from .atomize_svg_to_slide._geometry import Matrix, arc_to_cubics, fmt, parse_transform, path_segments
from .atomize_svg_to_slide._svg_input import _INHERITED

_SVG = "http://www.w3.org/2000/svg"
_SML = "https://www.larkoffice.com/sml/2.0"
_OPAQUE = ("clip-path", "mask", "filter", "style")
_PAINT = (
    "fill",
    "fill-opacity",
    "stroke",
    "stroke-width",
    "stroke-opacity",
    "stroke-linejoin",
    "stroke-linecap",
    "stroke-miterlimit",
    "opacity",
)
_MIN_BLOCK = 5.0
_MAX_PAINTS = 24
_EPS = 0.75


def _local(tag):
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


def _num(value, default=0.0):
    try:
        return float(str(value).strip().removesuffix("px"))
    except (TypeError, ValueError):
        return default


class _Atom:
    __slots__ = ("el", "kind", "boxes", "key", "layer", "slot")

    def __init__(self, el, kind, box, key=None):
        self.el, self.kind, self.boxes, self.key = el, kind, [box], key
        self.layer = self.slot = None


def _flatten(parent, inherited, matrix, out, canvas):
    for child in parent:
        name = _local(child.tag)
        if name in ("defs", "title", "desc", "metadata", "style", "") or child.get("display") == "none":
            continue
        own = parse_transform(child.get("transform", "")) if child.get("transform") else Matrix()
        if name == "g" and not any(child.get(k) for k in _OPAQUE) and _num(child.get("opacity", 1), 1) == 1:
            inh = dict(inherited)
            inh.update({k: v for k, v in child.attrib.items() if k in _INHERITED})
            _flatten(child, inh, matrix.then(own), out, canvas)
            continue
        el = copy.deepcopy(child)
        for key, value in inherited.items():
            if el.get(key) is None:
                el.set(key, value)
        total = matrix.then(own)
        el.attrib.pop("transform", None)
        if total != Matrix():
            el.set("transform", total.svg())
        out.append((el, total))


def _transform_box(box, matrix):
    if box is None:
        return None
    x0, y0, x1, y1 = box
    pts = [matrix.point(x, y) for x, y in ((x0, y0), (x1, y0), (x0, y1), (x1, y1))]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def _text_box(el):
    fs = _num(el.get("font-size", 16), 16)
    family = el.get("font-family")
    anchor = el.get("text-anchor", "start")
    x0, y0 = _num((el.get("x") or "0").split()[0]), _num((el.get("y") or "0").split()[0])
    lines = []
    if el.text and el.text.strip():
        lines.append((x0, y0, el.text, fs, anchor))
    for node in el:
        if _local(node.tag) != "tspan":
            continue
        size = _num(node.get("font-size", fs), fs)
        x = _num(node.get("x").split()[0]) if node.get("x") else x0
        y = _num(node.get("y").split()[0]) if node.get("y") else y0
        content = "".join(node.itertext())
        if node.get("x") or node.get("y") or not lines:
            lines.append((x, y, content, size, node.get("text-anchor", anchor)))
        else:
            px, py, ptext, psize, panchor = lines[-1]
            lines[-1] = (px, py, ptext + content, max(psize, size), panchor)
    if not lines:
        lines = [(x0, y0, "".join(el.itertext()), fs, anchor)]
    boxes = []
    for x, y, content, size, a in lines:
        w = _estimate_label_width_px(content, size, font_family=family, bold=True) * 1.1
        left = x - w / 2 if a == "middle" else x - w if a == "end" else x
        boxes.append((left - size * 0.3, y - size * 1.15, left + w + size * 0.3, y + size * 0.45))
    return (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))


def _absolute(d):
    """Absolute M/L/C/Q/Z with arcs as cubics, so paths concatenate and transform safely."""
    out, x, y = [], 0.0, 0.0
    for op, v in path_segments(d):
        if op == "A":
            for cop, cv in arc_to_cubics(x, y, *v):
                out.append((cop, list(cv)))
            x, y = v[-2:]
            continue
        out.append((op, list(v)))
        if v:
            x, y = v[-2:]
    return out


def _shape_path(el):
    name = _local(el.tag)
    g = lambda k: _num(el.get(k))
    if name == "rect":
        x, y, w, h = g("x"), g("y"), g("width"), g("height")
        rx = el.get("rx") or el.get("ry")
        r = min(_num(rx), w / 2, h / 2) if rx else 0
        if r > 0:
            return (
                f"M{x + r} {y} H{x + w - r} A{r} {r} 0 0 1 {x + w} {y + r} V{y + h - r} "
                f"A{r} {r} 0 0 1 {x + w - r} {y + h} H{x + r} A{r} {r} 0 0 1 {x} {y + h - r} "
                f"V{y + r} A{r} {r} 0 0 1 {x + r} {y} Z"
            )
        return f"M{x} {y} H{x + w} V{y + h} H{x} Z"
    if name in ("circle", "ellipse"):
        cx, cy = g("cx"), g("cy")
        rx = g("r") if name == "circle" else g("rx")
        ry = g("r") if name == "circle" else g("ry")
        return f"M{cx - rx} {cy} A{rx} {ry} 0 1 0 {cx + rx} {cy} A{rx} {ry} 0 1 0 {cx - rx} {cy} Z"
    if name == "polygon":
        nums = [_num(t) for t in el.get("points", "").replace(",", " ").split()]
        if len(nums) < 6:
            return None
        pts = list(zip(nums[0::2], nums[1::2]))
        return "M" + " L".join(f"{a} {b}" for a, b in pts) + " Z"
    if name == "path":
        return el.get("d")
    return None


def _geometry_box(el):
    name = _local(el.tag)
    if name == "text":
        return _text_box(el)
    if name == "line":
        xs, ys = (_num(el.get("x1")), _num(el.get("x2"))), (_num(el.get("y1")), _num(el.get("y2")))
        return min(xs), min(ys), max(xs), max(ys)
    if name == "polyline":
        nums = [_num(t) for t in el.get("points", "").replace(",", " ").split()]
        if len(nums) < 2:
            return None
        return min(nums[0::2]), min(nums[1::2]), max(nums[0::2]), max(nums[1::2])
    d = _shape_path(el)
    if d:
        try:
            x0, y0, x1, y1 = path_bounds(d)
            return x0, y0, x1, y1
        except (ValueError, ZeroDivisionError):
            return None
    return None


def _visual_box(el, matrix, canvas):
    if _local(el.tag) == "g" or any(el.get(k) for k in ("filter", "mask", "clip-path")):
        boxes = []
        for node in el.iter():
            if node is el:
                continue
            b = _geometry_box(node)
            if b is None and _local(node.tag) not in ("g", "tspan"):
                return canvas
            if b is not None:
                boxes.append(
                    _transform_box(
                        b,
                        matrix.then(parse_transform(node.get("transform", "")) if node.get("transform") else Matrix()),
                    )
                )
        if not boxes or el.get("filter"):
            return canvas
        box = (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))
    else:
        b = _geometry_box(el)
        if b is None:
            return canvas
        box = _transform_box(b, matrix)
    pad = _num(el.get("stroke-width", 1), 1) * max(1.0, matrix.scale) / 2 + _EPS
    if any(el.get(k) for k in ("marker-start", "marker-mid", "marker-end")):
        pad += 6 * _num(el.get("stroke-width", 1), 1) + 6
    return box[0] - pad, box[1] - pad, box[2] + pad, box[3] + pad


def _is_background(el, matrix, vx, vy, vw, vh):
    """Plain canvas/panel fill rect: native, so the SVG layers stay small and text stays clickable."""
    if (
        _local(el.tag) != "rect"
        or matrix != Matrix()
        or el.get("rx")
        or any(el.get(k) for k in ("filter", "mask", "clip-path"))
    ):
        return False
    fill = (el.get("fill") or "").lower()
    if not fill or fill == "none" or "url(" in fill:
        return False
    w, h = _num(el.get("width")), _num(el.get("height"))
    return w * h >= 0.6 * vw * vh


def _paint_key(el):
    return tuple((el.get(k) or "").strip().lower() for k in _PAINT)


def _is_axis_rect(name, segments, matrix):
    if matrix.b or matrix.c:
        return False
    if name == "rect":
        return True
    if name not in ("path", "polygon"):
        return False
    pts = [(v[-2], v[-1]) for op, v in segments if op in ("M", "L") and len(v) >= 2]
    if any(op not in ("M", "L", "Z") for op, _ in segments) or not 4 <= len(pts) <= 5:
        return False
    xs, ys = {round(p[0], 2) for p in pts}, {round(p[1], 2) for p in pts}
    return len(xs) == 2 and len(ys) == 2


def _block_candidate(el, matrix, canvas_area, scale=1.0):
    name = _local(el.tag)
    if name not in ("rect", "circle", "ellipse", "polygon", "path"):
        return False
    fill = (el.get("fill") or "#000000").strip().lower()
    if fill in ("none", "transparent") or "url(" in fill or fill == "currentcolor":
        return False
    if el.get("fill-rule") == "evenodd" or el.get("stroke-dasharray") not in (None, "none", ""):
        return False
    if any(el.get(k) for k in ("marker-start", "marker-mid", "marker-end", "filter", "mask", "clip-path")):
        return False
    if "url(" in (el.get("stroke") or ""):
        return False
    stroked = (el.get("stroke") or "none").lower() not in ("none", "transparent") and _num(
        el.get("stroke-width", 1), 1
    ) > 0
    if stroked:
        # Native borders are whole pixels (>=1): only merge strokes that render that way already.
        px = _num(el.get("stroke-width", 1), 1) * (matrix.scale if matrix != Matrix() else 1.0) * scale
        if px < 0.75 or abs(px - round(px)) > 0.25:
            return False
    d = _shape_path(el)
    if not d:
        return False
    try:
        segments = path_segments(d)
        x0, y0, x1, y1 = path_bounds(d)
    except (ValueError, ZeroDivisionError):
        return False
    if stroked and name == "path":
        starts = [i for i, (op, _) in enumerate(segments) if op == "M"] + [len(segments)]
        for a, b in zip(starts, starts[1:]):
            if segments[b - 1][0] != "Z":
                return False
    if not _is_axis_rect(name, segments, matrix):
        # Lint treats a native shape's bounding box as its frame: wedges, discs and polygons
        # would "contain" nearby labels and overlap each other, so they stay in SVG.
        return False
    s = matrix.scale if matrix != Matrix() else 1.0
    w, h = (x1 - x0) * s, (y1 - y0) * s
    if _num(el.get("fill-opacity", 1), 1) * _num(el.get("opacity", 1), 1) < 0.3:
        return False  # faint bands, tracks and halos are decoration, not recolorable data
    return min(w, h) >= _MIN_BLOCK and w * h < 0.9 * canvas_area


def _overlaps(a, b):
    return a[0] < b[2] + _EPS and b[0] < a[2] + _EPS and a[1] < b[3] + _EPS and b[1] < a[3] + _EPS


def _merged_path(atom):
    pieces = []
    for el, matrix in atom.el:
        for op, v in _absolute(_shape_path(el)):
            if op == "Z":
                pieces.append("Z")
                continue
            pts = [matrix.point(v[i], v[i + 1]) for i in range(0, len(v), 2)]
            pieces.append(op + " " + " ".join(f"{fmt(px)} {fmt(py)}" for px, py in pts))
    first = atom.el[0][0]
    attrs = {k: first.get(k) for k in _PAINT if first.get(k) is not None}
    attrs.setdefault("fill", "#000000")
    scale = atom.el[0][1].scale
    if "stroke-width" in attrs and scale != 1:
        attrs["stroke-width"] = fmt(_num(attrs["stroke-width"]) * scale)
    attrs["d"] = " ".join(pieces)
    return ET.Element(f"{{{_SVG}}}path", attrs)


def _point_in_poly(x, y, pts):
    inside = False
    for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            inside = not inside
    return inside


def _text_backings(texts, atoms):
    """Native swatches under labels printed on wedges/discs kept in SVG."""
    from .drawing_lib._geometry import _flatten as _sample

    solids = []
    for atom in atoms:
        if atom.kind != "embed" or len(atom.el) != 1:
            continue
        el, matrix = atom.el[0]
        fill = (el.get("fill") or "").strip()
        if not fill.startswith("#") or _num(el.get("fill-opacity", 1), 1) * _num(el.get("opacity", 1), 1) < 0.95:
            continue
        d = _shape_path(el)
        if not d:
            continue
        try:
            pts, _ = _sample(d, 0.5)
        except (ValueError, ZeroDivisionError):
            continue
        solids.append((fill, [matrix.point(px, py) for px, py in pts]))
    out = []
    for text in texts:
        x0, y0, x1, y1 = text.boxes[0]
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        for fill, poly in reversed(solids):
            if _point_in_poly(cx, cy, poly):
                w, h = (x1 - x0) * 0.6, (y1 - y0) * 0.6
                corners = [
                    (cx - w / 2, cy - h / 2),
                    (cx + w / 2, cy - h / 2),
                    (cx + w / 2, cy + h / 2),
                    (cx - w / 2, cy + h / 2),
                ]
                if all(_point_in_poly(px, py, poly) for px, py in corners):
                    swatch = ET.Element(
                        f"{{{_SVG}}}rect",
                        {"x": fmt(cx - w / 2), "y": fmt(cy - h / 2), "width": fmt(w), "height": fmt(h), "fill": fill},
                    )
                    out.append(
                        _Atom(
                            [(swatch, Matrix())],
                            "native",
                            (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2),
                            ("__backing__", id(swatch)),
                        )
                    )
                break
    return out


def _layers(atoms):
    texts = [a.boxes[0] for a in atoms if a.kind == "native" and a.key is None]

    def encloses_foreign_text(boxes):
        # A merged shape's frame must not wrap text that sits outside its own marks.
        x0, y0 = min(b[0] for b in boxes), min(b[1] for b in boxes)
        x1, y1 = max(b[2] for b in boxes), max(b[3] for b in boxes)
        for t in texts:
            if t[0] < x1 and x0 < t[2] and t[1] < y1 and y0 < t[3]:
                cx, cy = (t[0] + t[2]) / 2, (t[1] + t[3]) / 2
                if not any(b[0] <= cx <= b[2] and b[1] <= cy <= b[3] for b in boxes):
                    return True
        return False

    layers = []
    # Text goes on top: an SVG layer above native text would swallow clicks meant for the text.
    texts_last = [a for a in atoms if not (a.kind == "native" and a.key is None)]
    final_texts = [a for a in atoms if a.kind == "native" and a.key is None]
    for atom in texts_last:
        placed = [a for layer in layers for a in layer[1]]
        lower = -1
        conflicts = [p for p in placed if any(_overlaps(pb, ab) for pb in p.boxes for ab in atom.boxes)]
        for p in conflicts:
            lower = max(lower, p.layer if layers[p.layer][0] == atom.kind else p.layer + 1)
        if atom.key is not None:
            target = next(
                (
                    g
                    for g in placed
                    if g.key == atom.key
                    and g.kind == "native"
                    and not any(_overlaps(gb, ab) for gb in g.boxes for ab in atom.boxes)
                    and all(p.layer < g.layer or (p.layer == g.layer and p.slot < g.slot) for p in conflicts)
                    and not encloses_foreign_text(g.boxes + atom.boxes)
                ),
                None,
            )
            if target is not None:
                target.boxes.extend(atom.boxes)
                target.el.extend(atom.el)
                continue
        index = next((i for i in range(max(lower, 0), len(layers)) if layers[i][0] == atom.kind), None)
        if index is None:
            layers.append((atom.kind, []))
            index = len(layers) - 1
        atom.layer, atom.slot = index, len(layers[index][1])
        layers[index][1].append(atom)
    if final_texts:
        backing = _text_backings(final_texts, atoms)
        if backing:
            layers.append(("native", backing))
        layers.append(("native", final_texts))
    return layers


def _native_font(family):
    """Chart web-font stacks → fonts Slides and PPTX both ship (CJK-capable)."""
    if not family:
        return family
    first = family.split(",")[0].strip().strip("'\"").lower()
    # Feishu renders the chart library's default stacks with its sans fallback; match that look.
    if first in (
        "source serif",
        "georgia",
        "serif",
        "inter",
        "helvetica neue",
        "helvetica",
        "arial",
        "sans-serif",
        "system-ui",
    ):
        return "思源黑体"
    return family


def split_chart_svg(
    svg: str, *, x: float, y: float, width: float, height: float | None = None, merge_blocks: bool = True
) -> str:
    """Return an SML fragment placing ``svg`` at (x, y) with native text and recolorable blocks."""
    root = ET.fromstring(svg)
    if _local(root.tag) != "svg" or not root.get("viewBox"):
        raise ValueError("split_chart_svg expects a chart <svg> with a viewBox")
    vx, vy, vw, vh = (float(v) for v in root.get("viewBox").replace(",", " ").split())
    scale = width / vw if height is None else min(width / vw, height / vh)
    canvas = (vx - 1e6, vy - 1e6, vx + vw + 1e6, vy + vh + 1e6)
    defs = [c for c in root if _local(c.tag) in ("defs", "style")]
    flat = []
    _flatten(root, {k: v for k, v in root.attrib.items() if k in _INHERITED}, Matrix(), flat, canvas)

    candidates = [i for i, (el, m) in enumerate(flat) if merge_blocks and _block_candidate(el, m, vw * vh, scale)]
    if len({_paint_key(flat[i][0]) for i in candidates}) > _MAX_PAINTS:
        candidates = []
    candidates = set(candidates)
    atoms = []
    for i, (el, matrix) in enumerate(flat):
        box = _visual_box(el, matrix, canvas)
        if _is_background(el, matrix, vx, vy, vw, vh):
            atoms.append(_Atom([(el, matrix)], "native", box, ("__background__", i)))
            continue
        if _local(el.tag) == "text":
            for node in el.iter():
                if node.get("font-family"):
                    node.set("font-family", _native_font(node.get("font-family")))
            atoms.append(_Atom([(el, matrix)], "native", box))
        elif i in candidates:
            atoms.append(_Atom([(el, matrix)], "native", box, _paint_key(el)))
        else:
            atoms.append(_Atom([(el, matrix)], "embed", box))

    root_attrs = {k: v for k, v in root.attrib.items() if k not in ("width", "height", "data-chart-lib")}
    fragments = []
    saved = {k: _CFG[k] for k in ("svg_w", "svg_h", "slide_x0", "slide_y0", "slide_w", "slide_h")}
    try:
        _CFG.update(
            svg_w=vw, svg_h=vh, slide_x0=x - vx * scale, slide_y0=y - vy * scale, slide_w=vw * scale, slide_h=vh * scale
        )
        for kind, items in _layers(atoms):
            sub = ET.Element(f"{{{_SVG}}}svg", root_attrs)
            body = []
            for atom in items:
                if atom.key is not None and atom.key[0] not in ("__background__", "__backing__"):
                    body.append(_merged_path(atom))
                else:
                    body.extend(el for el, _ in atom.el)
            text = "".join(ET.tostring(e, encoding="unicode") for e in body)
            if kind == "embed" and ("url(" in text or "href" in text):
                sub.extend(copy.deepcopy(defs))
            sub.extend(body)
            serialized = ET.tostring(sub, encoding="unicode")
            if kind == "embed":
                bx0 = max(vx, min(b[0] for a in items for b in a.boxes) - 2)
                by0 = max(vy, min(b[1] for a in items for b in a.boxes) - 2)
                bx1 = min(vx + vw, max(b[2] for a in items for b in a.boxes) + 2)
                by1 = min(vy + vh, max(b[3] for a in items for b in a.boxes) + 2)
                if bx1 - bx0 < 1 or by1 - by0 < 1:
                    bx0, by0, bx1, by1 = vx, vy, vx + vw, vy + vh
                sub.set("viewBox", f"{fmt(bx0)} {fmt(by0)} {fmt(bx1 - bx0)} {fmt(by1 - by0)}")
                serialized = ET.tostring(sub, encoding="unicode")
                fragments.append(
                    f'<embed topLeftX="{x + (bx0 - vx) * scale:.2f}" topLeftY="{y + (by0 - vy) * scale:.2f}" '
                    f'width="{(bx1 - bx0) * scale:.2f}" height="{(by1 - by0) * scale:.2f}">{serialized}</embed>'
                )
            else:
                with tempfile.TemporaryDirectory() as tmp:
                    path = Path(tmp) / "layer.svg"
                    path.write_text(serialized, encoding="utf-8")
                    fragments.append(atomize_svg_to_slide(path))
    finally:
        _CFG.update(saved)
    return _separate_stacked_text(compose_slide(f'<slide xmlns="{_SML}"><data></data></slide>', *fragments))


def _separate_stacked_text(xml):
    """Push apart native label lines whose boxes overlap vertically."""
    import re as _re

    pat = _re.compile(r'<shape type="text"([^>]*)>')
    boxes = []
    for m in pat.finditer(xml):
        attrs = m.group(1)
        get = lambda k: _re.search(rf'\b{k}="([-\d.]+)"', attrs)
        if not all(get(k) for k in ("topLeftX", "topLeftY", "width", "height")):
            continue
        x, y, w, h = (float(get(k).group(1)) for k in ("topLeftX", "topLeftY", "width", "height"))
        if h > 16:
            continue
        boxes.append([m.start(1), m.end(1), x, y, w, h])
    if len(boxes) < 2:
        return xml
    order = sorted(range(len(boxes)), key=lambda i: (boxes[i][3], boxes[i][2]))
    moved = {}
    placed = []
    for i in order:
        _, _, x, y, w, h = boxes[i]
        for px, py, pw, ph in placed:
            # Stacked lines only: a later line starting below an earlier one but inside its box.
            # Items on the same baseline (legend rows) are side by side, not stacked.
            if x < px + pw - 1 and px < x + w - 1 and py + 0.5 < y < py + ph:
                y = py + ph + 0.5
        if y != boxes[i][3]:
            moved[i] = y
        placed.append((x, y, w, h))
    if not moved:
        return xml
    out, last = [], 0
    for i, (s, e, *_r) in enumerate(boxes):
        if i in moved:
            attrs = _re.sub(r'\btopLeftY="[-\d.]+"', f'topLeftY="{moved[i]:.2f}"', xml[s:e], count=1)
            out.append(xml[last:s])
            out.append(attrs)
            last = e
    out.append(xml[last:])
    return "".join(out)


ET.register_namespace("", _SVG)
