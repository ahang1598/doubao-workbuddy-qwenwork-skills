"""Opt-in scene/atomizer observations, distinct from drawing or validation."""

from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET
from ._geometry import Box
from ._help import _drawing_api


def _box_data(box):
    return [box.x, box.y, box.width, box.height] if box is not None else None


def inspect_drawing(drawing, keys, overlaps):
    from ._scene import Node, Anchor, ContourAnchor, Edge, _Layout
    from ..atomize_svg_to_slide._bounds import svg_bounds

    requested = set(keys)
    missing = requested - drawing.keys
    if missing:
        raise KeyError("Unknown drawing objects: " + ", ".join(sorted(missing)))
    defs = ET.Element("defs")
    defs.extend(drawing.definitions)
    definitions = ET.tostring(defs, encoding="unicode")
    layout = _Layout(drawing)
    items = []
    errors = []
    for z, (key, item) in enumerate(drawing.items):
        if requested and key not in requested:
            continue
        row = {"key": key, "kind": "node" if isinstance(item, Node) else "connector", "z_index": z}
        try:
            if isinstance(item, Node):
                box = layout.bounds(item)
                row["layout_bounds"] = _box_data(box)
                row["port_count"] = len(item.geometry.ports)
                target = item.target
                row["relative_to"] = target.node.key if isinstance(target, (Anchor, ContourAnchor, Edge)) else None
                if requested:
                    source = ET.Element("g", {"transform": layout.matrix(item).svg()})
                    source.append(item.geometry.element)
                    info = {}
                    b = svg_bounds(
                        source, definitions, (0, 0, drawing.width, drawing.height), unknown_none=True, diagnostics=info
                    )
                    row["ink_bounds"] = list(b) if b else None
                    row["ink_bounds_evidence"] = info
                    row["ports"] = {}
                    for name in item.geometry.ports:
                        ref = item.port(name)
                        data = {"point": layout.point(ref)}
                        if name in item.geometry.port_directions:
                            frame = layout.frame(ref)
                            data.update(normal=frame.normal, tangent=frame.tangent)
                        row["ports"][name] = data
            else:
                element = item.element(layout)
                info = {}
                b = svg_bounds(
                    element, definitions, (0, 0, drawing.width, drawing.height), unknown_none=True, diagnostics=info
                )
                box = Box(*b) if b else None
                row["layout_bounds"] = _box_data(box)
                row["ink_bounds_evidence"] = info
                if requested:
                    row.update(
                        route=item.route,
                        start=layout.point(item.start),
                        end=layout.point(item.end),
                        waypoints=[layout.point(p) for p in item.waypoints],
                        path=element.get("d"),
                    )
                    for label, reference in [("start", item.start), ("end", item.end)]:
                        try:
                            row[label + "_normal"] = layout.frame(reference).normal
                        except ValueError:
                            pass
            row["outside_canvas"] = bool(
                box
                and (box.x < 0 or box.y < 0 or box.x + box.width > drawing.width or box.y + box.height > drawing.height)
            )
        except (ValueError, TypeError, KeyError) as error:
            row["error"] = str(error)
            errors.append({"key": key, "message": str(error)})
        items.append(row)
    result = {
        "canvas": [drawing.width, drawing.height],
        "objects": items,
        "errors": errors,
        "bounds_note": "layout_bounds/ink_bounds use SVG canvas units, not Slides selection bounds; inspect_svg reports conversion boxes.",
    }
    if overlaps:
        collisions = []
        for i, a in enumerate(items):
            if not a.get("layout_bounds"):
                continue
            x, y, w, h = a["layout_bounds"]
            for b in items[i + 1 :]:
                if not b.get("layout_bounds"):
                    continue
                bx, by, bw, bh = b["layout_bounds"]
                iw = min(x + w, bx + bw) - max(x, bx)
                ih = min(y + h, by + bh) - max(y, by)
                if iw > 0 and ih > 0:
                    collisions.append({"keys": [a["key"], b["key"]], "bbox_overlap_area": iw * ih})
        result["overlaps"] = collisions
        result["overlap_note"] = "Bounding-box intersections are candidates, not proof of visible occlusion."
    return result


@_drawing_api(
    "inspect",
    purpose="查询 SVG 转换选择、原因与选择框。",
    returns="dict（可 JSON 序列化）",
    semantics=(
        "svg_path 指向源 SVG；沿用当前 set_mapping 配置，报告 selection_bounds 使用 Slides 坐标。",
        "object_ids 可指定源对象或分组 ID；只返回相关记录，无匹配 ID 会出现在 unmatched_ids。",
        "报告含 native/svg/mixed/omitted 决策、实际转换阶段原因、源特征、每个输出框及边界估计依据。",
        "原生文字 outputs[].font_policy 对照有效源字号、自然缩放与实际 SML 字号，含下限/字幕策略和富文本 run；保留 SVG 的文字不假报原生 clamp。",
        "svg/mixed 可为保留透明度或效果的正常选择；不能单凭 embed 数量判定失败或删除效果。",
        "source_viewport_fallback=True 表示边界无法估计，需要重点检查；整页大小本身不一定是错误。",
        "只读取/计算，不写文件、不修图、不加入强制流程。",
    ),
    example='report = inspect_svg(svg_path, object_ids=["body", "wire"])',
)
def inspect_svg(svg_path, *, object_ids=None):
    from ..atomize_svg_to_slide import inspect_svg as inspect_conversion

    return inspect_conversion(Path(svg_path), object_ids=object_ids)


def label_candidates(drawing, geometry, target, avoid, gap):
    from ._geometry import Geometry, _finite
    from ._scene import Node, _Layout

    if not isinstance(geometry, Geometry):
        raise TypeError("label_geometry must be Geometry")
    _finite(gap)
    if gap < 0:
        raise ValueError("Label gap must be nonnegative")
    layout = _Layout(drawing)
    x, y = layout.point(target)
    w, h = geometry.bounds.width, geometry.bounds.height
    boxes = []
    for obstacle in avoid:
        if isinstance(obstacle, Node):
            if obstacle.drawing is not drawing:
                raise ValueError("Obstacle belongs to another drawing")
            boxes.append((obstacle.key, layout.bounds(obstacle)))
        elif isinstance(obstacle, Box):
            boxes.append((None, obstacle))
        else:
            raise TypeError("Avoidance regions must be Box or Node")
    positions = [
        ("right", gap, -h / 2),
        ("left", -gap - w, -h / 2),
        ("top", -w / 2, -gap - h),
        ("bottom", -w / 2, gap),
        ("top_right", gap, -gap - h),
        ("bottom_right", gap, gap),
        ("top_left", -gap - w, -gap - h),
        ("bottom_left", -gap - w, gap),
    ]
    result = []
    for rank, (side, dx, dy) in enumerate(positions):
        bx, by = x + dx, y + dy
        collisions = []
        area = 0
        for key, box in boxes:
            iw = max(0, min(bx + w, box.x + box.width) - max(bx, box.x))
            ih = max(0, min(by + h, box.y + box.height) - max(by, box.y))
            if iw * ih:
                area += iw * ih
                collisions.append(key)
        visible = max(0, min(bx + w, drawing.width) - max(0, bx)) * max(0, min(by + h, drawing.height) - max(0, by))
        outside = max(0, w * h - visible)
        result.append(
            {
                "side": side,
                "at": (bx, by),
                "offset": (dx, dy),
                "own_anchor": "top_left",
                "bounds": [bx, by, w, h],
                "overlap_area": area,
                "overlaps": collisions,
                "outside_area": outside,
                "score": outside * 4 + area,
                "_rank": rank,
            }
        )
    result.sort(key=lambda item: (item["score"], item["_rank"]))
    for item in result:
        item.pop("_rank")
    return result


_TEXT_INHERIT = ("font-size", "font-family", "font-weight", "font-style", "text-anchor", "dominant-baseline")


def _node_texts(item):
    """(text element, local matrix, inherited text attributes) for every <text> in a node."""
    from ..atomize_svg_to_slide._geometry import Matrix, parse_transform

    texts = []

    def walk(el, m, inherited):
        if el.get("transform"):
            m = m.then(parse_transform(el.get("transform")))
        inherited = {**inherited, **{k: el.get(k) for k in _TEXT_INHERIT if el.get(k) is not None}}
        if el.tag.split("}")[-1] == "text":
            texts.append((el, m, inherited))
            return
        for child in el:
            walk(child, m, inherited)

    walk(item.geometry.element, Matrix(), {})
    return texts


def _emitted_text_box(el, m, attrs, ratio, min_font):
    """Canvas box of the native text shape to_slide emits for this <text> (same font size, clamp, width"""
    import re
    from ..atomize_svg_to_slide._font_metrics import measure_text, text_advance, lint_floor_width, baseline_offset
    from ..atomize_svg_to_slide._paint import _map_svg_font_family
    from ..atomize_svg_to_slide._text_layout import native_text_baseline

    text = re.sub(r"[\t\r\n ]+", " ", "".join(el.itertext())).strip(" ")
    if not text:
        return None
    probe = type(el)(
        el.tag, {**{k: v for k, v in attrs.items() if k in ("text-anchor", "dominant-baseline")}, **el.attrib}
    )
    baseline = native_text_baseline(probe)
    if baseline is None or abs(m.b) > 1e-6 or abs(m.c) > 1e-6:
        return None  # rotated / shaped text: the converter keeps it as SVG
    try:
        fs = float(str(attrs.get("font-size") or 11).replace("px", "")) * m.scale
        x, y = m.point(float(el.get("x") or 0), float(el.get("y") or 0))
    except ValueError:
        return None
    slide_fs = max(min_font, fs * ratio) if min_font else fs * ratio
    family = _map_svg_font_family(attrs.get("font-family") or "")
    weight = (
        "bold" if str(attrs.get("font-weight") or "") in ("600", "700", "800", "900", "bold", "bolder") else "normal"
    )
    style = "italic" if attrs.get("font-style") in ("italic", "oblique") else "normal"
    metric = measure_text(text, family or "sans-serif", slide_fs, weight, style)
    advance = text_advance(text, family, slide_fs, weight, style, 0)
    overhang = max(0, metric.right - metric.advance, -metric.left) if metric is not None else 0
    w = (
        max(1, advance + overhang + slide_fs * 0.5, lint_floor_width(text, family, slide_fs, weight) + slide_fs * 0.1)
        / ratio
    )
    anchor = attrs.get("text-anchor") or "start"
    x0 = x - (w / 2 if anchor == "middle" else w if anchor == "end" else 0)
    alphabetic = y + baseline_offset(baseline, fs, measure_text(text, family or "sans-serif", fs, weight, style))
    h = max(fs, slide_fs / ratio)
    return Box(x0, alphabetic - 0.35 * fs - h / 2, w, h)


def _text_boxes(drawing, layout, width=None, *, emitted=False):
    """Canvas boxes of text, keyed by owning node."""
    from ._scene import Node
    from ._geometry import label
    from ..atomize_svg_to_slide._config import _CFG

    ratio = width / drawing.width if width else 1.0
    min_font = max(6, int(_CFG.get("min_slide_font_size", 10)) or 6) if width else 0
    out = []
    for key, item in drawing.items:
        if not isinstance(item, Node):
            continue
        root = item.geometry.element
        texts = _node_texts(item)
        if not texts:
            continue
        shapes = [n for n in root.iter() if n.tag.split("}")[-1] in ("rect", "ellipse", "circle", "path", "polygon")]
        own = not shapes or len(texts) == 1 and len(shapes) <= 1
        node_matrix = layout.matrix(item)
        if own:
            out.append((key, layout.bounds(item)))  # a label or text box: its own box is the text
            if not emitted:
                continue
        for el, m, attrs in texts:
            full = node_matrix.then(m)
            box = _emitted_text_box(el, full, attrs, ratio, min_font) if emitted else None
            if box is None and own:
                continue
            if box is None:
                fs = float(attrs.get("font-size") or 12)
                anchor = attrs.get("text-anchor", "start")
                w = label(el.text or " ", font_size=fs).bounds.width
                x, y = float(el.get("x") or 0), float(el.get("y") or 0)
                x0 = x - (w / 2 if anchor == "middle" else w if anchor == "end" else 0)
                box = Box(x0, y - fs * 0.9, w, fs * 1.15).transformed(full)
            out.append((key, box))
    return out


def _diagonal_box_covers(segment, box):
    """A straight, clearly diagonal line converts to one native <line>; lint treats its bounding box as solid."""
    (x1, y1), (x2, y2) = segment
    if min(abs(x2 - x1), abs(y2 - y1)) < 6:
        return False
    lx, ly, lw, lh = min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1)
    return (
        box.width > 0
        and box.height > 0
        and lx < box.x + box.width
        and box.x < lx + lw
        and ly < box.y + box.height
        and box.y < ly + lh
    )


def _inside_node(drawing, layout, key, segment):
    """The line starts or ends inside that node (a label inside a part the line belongs to)."""
    node = drawing.nodes.get(key)
    if node is None:
        return False
    b = layout.bounds(node)
    return any(b.x <= x <= b.x + b.width and b.y <= y <= b.y + b.height for x, y in segment)


def check_drawing(drawing, *, gap=2.0, width=None):
    """Cheap self-check before export: text on text, lines through text, content off canvas."""
    from ._scene import Connector, Node, Anchor, ContourAnchor, Edge, _Layout
    from ._labels import _connector_segments
    from ._routing import crosses

    layout = _Layout(drawing)
    problems = []
    texts = _text_boxes(drawing, layout)
    emitted = _text_boxes(drawing, layout, width, emitted=True)
    polys = _part_polygons(drawing, layout)
    for i, (ka, a) in enumerate(texts):
        for kb, b in texts[i + 1 :]:
            w = min(a.x + a.width, b.x + b.width) - max(a.x, b.x)
            h = min(a.y + a.height, b.y + b.height) - max(a.y, b.y)
            if w > gap and h > gap:
                problems.append(
                    {"kind": "text_overlap", "keys": [ka, kb], "hint": f"move {kb} or {ka} apart by {min(w, h):.0f}px"}
                )
    for key, item in drawing.items:
        if not isinstance(item, Connector):
            continue
        ends = set()
        for ref in (item.start, item.end):
            if isinstance(ref, (Anchor, ContourAnchor, Edge)):
                ends.add(ref.node.key)
        segs = _connector_segments(item, layout)
        if segs:  # a leader pointing into a part (organelle in a cell) crosses only that host's own outline/labels
            ends |= _hosts((segs[0][0], segs[-1][1]), polys, layout, drawing)
        boxed, crossed = set(), set()
        for tk, tb in emitted:
            if tk in ends or tk in crossed:
                continue
            inner = Box(tb.x + gap, tb.y + gap, max(0, tb.width - 2 * gap), max(0, tb.height - 2 * gap))
            if any(crosses(p, q, inner) for p, q in segs):
                raw = not any(isinstance(ref, (Anchor, ContourAnchor, Edge)) for ref in (item.start, item.end))
                hint = (
                    f"{key} is drawn between raw (x, y) points: pass the node objects instead, e.g. "
                    f"d.arrow(node_a, node_b) — ends then land on outlines and never cross the nodes' own text"
                    if raw
                    else f'route {key} around {tk} (route="orthogonal", avoid=[node]) or move the label'
                )
                crossed.add(tk)
                problems.append({"kind": "line_through_text", "keys": [key, tk], "hint": hint})
            elif (
                tk not in boxed
                and len(segs) == 1
                and _diagonal_box_covers(segs[0], inner)
                and not _inside_node(drawing, layout, tk, segs[0])
            ):
                boxed.add(tk)
                problems.append(
                    {
                        "kind": "line_box_over_text",
                        "keys": [key, tk],
                        "hint": f"the diagonal {key} misses {tk}, but its bounding box covers the label and the server "
                        "lint checks text contrast against that box (reported as text_color_contrast): "
                        f'use route="orthogonal" for {key} or move {tk} out of the line\'s box',
                    }
                )
    for key, item in drawing.items:
        if isinstance(item, Node):
            b = layout.bounds(item)
            if b.x < -0.5 or b.y < -0.5 or b.x + b.width > drawing.width + 0.5 or b.y + b.height > drawing.height + 0.5:
                corner = _corner_mistake(item, b, drawing)
                problems.append(
                    {
                        "kind": "off_canvas",
                        "keys": [key],
                        "hint": f"{key} spans x {b.x:.0f}–{b.x + b.width:.0f}, y {b.y:.0f}–{b.y + b.height:.0f} on a "
                        f"{drawing.width:g}×{drawing.height:g} canvas: move it inside (place/*_at put the "
                        "shape's centre at `at`; geometry built in canvas coordinates goes in with d.add)"
                        + (
                            f" — it sticks out by exactly half its size, so `at` was probably meant as the "
                            f"top-left corner: use at=({b.x + b.width:.0f}, {b.y + b.height:.0f}) (centre) "
                            "or insert=(x, y) for top-left"
                            if corner
                            else ""
                        ),
                    }
                )
    problems.extend(_parts_overlap(drawing, layout, polys))
    problems.extend(_frame_conflicts(drawing, layout, texts, gap))
    problems.extend(_invisible_ends(drawing))
    problems.extend(_heads_on_edges(drawing, layout))
    problems.extend(_hand_strokes_through_text(drawing, layout, emitted, gap))
    return problems


_SHAPE_TAGS = ("rect", "circle", "ellipse", "path", "polygon", "polyline", "line")


def _clear(value, default):
    v = (value if value is not None else default).strip().lower().replace(" ", "")
    return v in ("none", "transparent") or (
        v.startswith("rgba(") and v.rstrip(")").split(",")[-1] in ("0", "0.0", ".0")
    )


def _invisible(node):
    """A node that paints nothing: every shape has no fill and no stroke (or zero opacity), and there is no text."""
    root = node.geometry.element
    if any(el.tag.split("}")[-1] == "text" for el in root.iter()):
        return False
    shapes = [el for el in root.iter() if el.tag.split("}")[-1] in _SHAPE_TAGS]
    if not shapes:
        return False
    if any((el.get("opacity") or "").strip() in ("0", "0.0") for el in root.iter()):
        return True
    return all(
        (_clear(el.get("fill"), "#000") or (el.get("fill-opacity") or "").strip() in ("0", "0.0"))
        and (_clear(el.get("stroke"), "none") or (el.get("stroke-opacity") or "").strip() in ("0", "0.0"))
        for el in shapes
    )


def _invisible_ends(drawing):
    from ._scene import Connector, Anchor, ContourAnchor, Edge

    problems = []
    for key, item in drawing.items:
        if not isinstance(item, Connector):
            continue
        for ref in (item.start, item.end):
            node = ref.node if isinstance(ref, (Anchor, ContourAnchor, Edge)) else None
            if node is not None and _invisible(node):
                problems.append(
                    {
                        "kind": "invisible_endpoint",
                        "keys": [key, node.key],
                        "hint": f"{key} 端点落在不可见辅助点 {node.key} 上：直接把 Node 传给 arrow，"
                        "或用 node.contour_toward(src)/edge_toward 让箭头停在对象轮廓上",
                    }
                )
                break
    return problems


def _seg_dist(p, a, b):
    (px, py), (ax, ay), (bx, by) = p, a, b
    dx, dy = bx - ax, by - ay
    t = 0.0 if not (dx or dy) else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return ((px - ax - t * dx) ** 2 + (py - ay - t * dy) ** 2) ** 0.5


def _width(style, default=1.0):
    try:
        return float(style.get("stroke_width", style.get("stroke-width", default)))
    except (TypeError, ValueError):
        return default


def _on_edge(node):
    """A node declared to sit on another object's edge (data-on-edge="1": a carrier on a band edge, a marker on a line)."""
    return any(el.get("data-on-edge") == "1" for el in node.geometry.element.iter())


def _heads_on_edges(drawing, layout):
    """An arrowhead whose tip lies on the outline of an object that is not one of the arrow's endpoints."""
    from ._scene import Connector, Anchor, ContourAnchor, Edge
    from ._labels import _connector_points, _outline

    outlines = {}
    problems = []
    for key, item in drawing.items:
        if not isinstance(item, Connector):
            continue
        heads = [name for name in ("marker_end", "marker_start") if item.style.get(name)]
        if not heads:
            continue
        try:
            points = _connector_points(item, layout)
        except (ValueError, TypeError):
            continue
        if len(points) < 2:
            continue
        ends = {r.node.key for r in (item.start, item.end) if isinstance(r, (Anchor, ContourAnchor, Edge))}
        if any(_on_edge(drawing.nodes[k]) for k in ends):
            continue  # the arrow points at something that sits on an edge by design
        related = set(ends)
        for k in ends:
            host = getattr(drawing.nodes[k], "mounted_on", None)
            if host:
                related.add(host)
        related |= {k for k, n in drawing.nodes.items() if getattr(n, "mounted_on", None) in ends}
        tol = max(2.5, _width(item.style, 2) * 1.2)
        for name in heads:
            tip = points[-1] if name == "marker_end" else points[0]
            for nk, node in drawing.nodes.items():
                if nk in related or _invisible(node) or _on_edge(node):
                    continue
                b = layout.bounds(node)
                if not (b.x - tol <= tip[0] <= b.x + b.width + tol and b.y - tol <= tip[1] <= b.y + b.height + tol):
                    continue
                if nk not in outlines:
                    outlines[nk] = _outline(node, layout)
                segs = outlines[nk]
                if not segs:
                    continue
                reach = tol + _width({k.replace("-", "_"): v for k, v in node.geometry.element.attrib.items()}, 1) / 2
                if any(_seg_dist(tip, a, c) <= reach for a, c in segs):
                    problems.append(
                        {
                            "kind": "head_on_edge",
                            "keys": [key, nk],
                            "hint": f"{key} 的箭头尖 ({tip[0]:.0f}, {tip[1]:.0f}) 压在 {nk} 的边线上："
                            f"让箭头停在目标对象上（传 Node 或 contour_toward），或把端点移离 {nk} 的轮廓",
                        }
                    )
                    break
    return problems


def _stroke_segments(node, layout, samples=8):
    """Canvas segments of a hand-drawn open stroke (d.path / d.polyline with fill none); None for anything else."""
    from ..atomize_svg_to_slide._geometry import path_segments, arc_to_cubics

    root = node.geometry.element
    if root.tag.split("}")[-1] != "path" or not _clear(root.get("fill"), "#000") or _clear(root.get("stroke"), "none"):
        return None
    try:
        ops = path_segments(root.get("d", ""))
    except ValueError:
        return None
    m = layout.matrix(node)
    pts, out, cur, start = [], [], None, None

    def bez(p0, ctrl):
        q = [p0] + list(zip(ctrl[::2], ctrl[1::2]))
        for i in range(1, samples + 1):
            t, r = i / samples, list(q)
            while len(r) > 1:
                r = [((1 - t) * a[0] + t * b[0], (1 - t) * a[1] + t * b[1]) for a, b in zip(r, r[1:])]
            pts.append(r[0])

    for op, v in ops:
        if op == "M":
            if len(pts) > 1:
                out.append(pts)
            pts = [tuple(v)]
            cur = start = tuple(v)
        elif op == "L":
            pts.append(tuple(v))
            cur = tuple(v)
        elif op in ("C", "Q"):
            bez(cur, v)
            cur = tuple(v[-2:])
        elif op == "A":
            for kind, w in arc_to_cubics(*cur, *v):
                if kind == "L":
                    pts.append(tuple(w))
                else:
                    bez(cur, w)
                cur = tuple(w[-2:])
        elif op == "Z" and start is not None:
            pts.append(start)
            cur = start
    if len(pts) > 1:
        out.append(pts)
    return [(m.point(*a), m.point(*b)) for run in out for a, b in zip(run, run[1:])]


def _hand_strokes_through_text(drawing, layout, texts, gap):
    from ._scene import Node
    from ._routing import crosses

    problems = []
    for key, item in drawing.items:
        if not isinstance(item, Node):
            continue
        segs = _stroke_segments(item, layout)
        if not segs:
            continue
        ends = [segs[0][0], segs[-1][1]]
        for tk, tb in texts:
            if tk == key or _inside_node(drawing, layout, tk, ends):
                continue
            inner = Box(tb.x + gap, tb.y + gap, max(0, tb.width - 2 * gap), max(0, tb.height - 2 * gap))
            if any(crosses(p, q, inner) for p, q in segs):
                problems.append(
                    {
                        "kind": "line_through_text",
                        "keys": [key, tk],
                        "hint": f"手写线 {key} 穿过文字 {tk}：改用 d.arrow/d.line 并把节点对象传作端点"
                        f'（route="orthogonal" 可绕开），或把 {tk} 挪开',
                    }
                )
                break
            if len(segs) == 1 and _diagonal_box_covers(segs[0], inner):
                problems.append(
                    {
                        "kind": "line_box_over_text",
                        "keys": [key, tk],
                        "hint": f"斜线 {key} 没碰到 {tk}，但服务端按斜线外接框算文字对比度（报 text_color_contrast）："
                        f"改成折线/水平竖直线，或把 {tk} 移出该外接框",
                    }
                )
                break
    return problems


def _filled_frames(drawing, layout):
    """Bounding boxes of filled, non-text nodes: Slides lint treats these as text containers."""
    from ._scene import Node

    out = []
    for key, item in drawing.items:
        if not isinstance(item, Node):
            continue
        if item.geometry.element.get("data-appearance") == "1":
            continue  # appearance layers convert to local SVG, which lint does not treat as containers
        tags = [
            n
            for n in item.geometry.element.iter()
            if n.tag.split("}")[-1] in ("rect", "ellipse", "circle", "path", "polygon")
        ]
        if any(n.tag.split("}")[-1] == "text" for n in item.geometry.element.iter()):
            continue
        if not any((n.get("fill") or "#000").lower() not in ("none", "transparent") for n in tags):
            continue
        b = layout.bounds(item)
        if min(b.width, b.height) <= 3 or b.width * b.height > 0.6 * drawing.width * drawing.height:
            continue
        out.append((key, b))
    return out


def _badge_text(tb, fb):
    """Short text centred on a small disc/square (a numbered badge): its line box is taller than the badge but the"""
    if max(fb.width, fb.height) > 48 or tb.width > fb.width + 2:
        return False
    dx = abs(tb.x + tb.width / 2 - fb.x - fb.width / 2)
    dy = abs(tb.y + tb.height / 2 - fb.y - fb.height / 2)
    return dx <= fb.width * 0.2 and dy <= fb.height * 0.3


def _frame_conflicts(drawing, layout, texts, gap):
    on_edge = {k for k, n in drawing.nodes.items() if _on_edge(n)}
    frames = [(k, b) for k, b in _filled_frames(drawing, layout) if k not in on_edge]
    problems = []
    inter = lambda a, b: (
        min(a.x + a.width, b.x + b.width) - max(a.x, b.x),
        min(a.y + a.height, b.y + b.height) - max(a.y, b.y),
    )
    inside = lambda a, b: (
        a.x >= b.x - 0.5
        and a.y >= b.y - 0.5
        and a.x + a.width <= b.x + b.width + 0.5
        and a.y + a.height <= b.y + b.height + 0.5
    )
    for tk, tb in texts:
        if tk in on_edge:
            continue
        for fk, fb in frames:
            w, h = inter(tb, fb)
            if w > gap and h > gap and not inside(tb, fb) and not _badge_text(tb, fb):
                problems.append(
                    {
                        "kind": "text_straddles_frame",
                        "keys": [tk, fk],
                        "hint": f"{tk} half-overlaps the bounding box of {fk}; move it fully inside or ≥{gap:.0f}px outside that box",
                    }
                )
    return problems


def _polygon(node, layout):
    """Canvas outline polygon of a node's main contour (None when it has no single closed outline)."""
    from ._labels import _outline

    segs = _outline(node, layout)
    if not segs or len(segs) < 3:
        return None
    return [a for a, _ in segs]


def _in_polygon(p, poly):
    x, y, inside = p[0], p[1], False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            inside = not inside
    return inside


def _part_polygons(drawing, layout):
    from ._scene import Node

    out = {}
    for key, item in drawing.items:
        if isinstance(item, Node) and item.kind in ("part", "svg") and not _invisible(item):
            poly = _polygon(item, layout)
            if poly:
                out[key] = poly
    return out


def _hosts(points, polys, layout, drawing, margin=1.5):
    """Parts whose outline strictly contains one of these points: a leader pointing into a part (an organelle"""
    found = set()
    for key, poly in polys.items():
        b = layout.bounds(drawing.nodes[key])
        for p in points:
            if (
                b.x <= p[0] <= b.x + b.width
                and b.y <= p[1] <= b.y + b.height
                and _in_polygon(p, poly)
                and min(_seg_dist(p, a, c) for a, c in zip(poly, poly[1:] + poly[:1])) > margin
            ):
                found.add(key)
    return found


def _overlap_share(pa, pb, ba, bb, floor=0.0, n=16):
    """Fraction of the smaller outline's area covered by the other (grid sampling over the box intersection)."""
    x0, y0 = max(ba.x, bb.x), max(ba.y, bb.y)
    x1, y1 = min(ba.x + ba.width, bb.x + bb.width), min(ba.y + ba.height, bb.y + bb.height)
    if x1 <= x0 or y1 <= y0:
        return 0.0
    area = lambda poly: abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(poly, poly[1:] + poly[:1]))) / 2
    small = min(area(pa), area(pb))
    if small <= 0 or (x1 - x0) * (y1 - y0) <= floor * small:
        return 0.0
    dx, dy = (x1 - x0) / n, (y1 - y0) / n
    hits = sum(
        1
        for i in range(n)
        for j in range(n)
        if _in_polygon((x0 + (i + 0.5) * dx, y0 + (j + 0.5) * dy), pa)
        and _in_polygon((x0 + (i + 0.5) * dx, y0 + (j + 0.5) * dy), pb)
    )
    return hits * dx * dy / small


def _related(a, b):
    """Intended contact: mounted on / pinned to the other part."""
    from ._scene import Anchor, ContourAnchor, Edge

    for x, y in ((a, b), (b, a)):
        if getattr(x, "mounted_on", None) == y.key:
            return True
        if isinstance(x.target, (Anchor, ContourAnchor, Edge)) and x.target.node is y:
            return True
    return False


def _parts_overlap(drawing, layout, polys, share=0.15, inside=0.85):
    """Two placed parts whose filled bodies overlap substantially without one sitting inside the other."""
    problems = []
    keys = [k for k in polys if drawing.nodes[k].kind == "part"]
    boxes = {k: layout.bounds(drawing.nodes[k]) for k in keys}
    order = {k: i for i, (k, _) in enumerate(drawing.items)}
    for i, ka in enumerate(keys):
        for kb in keys[i + 1 :]:
            a, b = drawing.nodes[ka], drawing.nodes[kb]
            if _related(a, b):
                continue
            s = _overlap_share(polys[ka], polys[kb], boxes[ka], boxes[kb], share)
            if share < s < inside:
                top = kb if order[kb] > order[ka] else ka
                problems.append(
                    {
                        "kind": "parts_overlap",
                        "keys": [ka, kb],
                        "hint": f"{top} 盖住了 {kb if top == ka else ka} 约 {s:.0%} 的主体：把两者拉开；"
                        "有意的接触/吞噬改成贴边（mount 到对方 contour_at，或 pin 到对方端口），"
                        "内含关系就把小的整个放进大的里面",
                    }
                )
    return problems


def _corner_mistake(item, b, drawing):
    """A centre-anchored shape that would fit on the canvas if `at` were its top-left corner."""
    if item.own_anchor != "center" or item.kind not in ("rect", "box", "ellipse", "svg", "part", "text"):
        return False
    x, y = b.x + b.width / 2, b.y + b.height / 2
    return (
        (b.x < -0.5 or b.y < -0.5)
        and x >= -0.5
        and y >= -0.5
        and x + b.width <= drawing.width + 0.5
        and y + b.height <= drawing.height + 0.5
    )
