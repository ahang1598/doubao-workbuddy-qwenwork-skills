"""Text layout summary of a Drawing as it will appear on the slide."""

from __future__ import annotations

import math

MIN_STROKE_PX = 1.0
MIN_LINK_PX = 18.0
MIN_GAP_PX = 6.0


def _text_sizes(node):
    out = []
    for el in node.geometry.element.iter():
        if el.tag.split("}")[-1] == "text":
            try:
                out.append((float(el.get("font-size", 16)), "".join(el.itertext()).strip()))
            except ValueError:
                pass
    return out


def _strokes(element):
    # Author-set strokes only: appearance layers carry deliberately fine texture lines.
    skip = {id(n) for g in element.iter() if g.get("data-appearance") == "1" for n in g.iter()}
    for el in element.iter():
        if id(el) in skip:
            continue
        w = el.get("stroke-width")
        if w and (el.get("stroke") or "none") not in ("none", "transparent"):
            try:
                yield float(w)
            except ValueError:
                pass


def _length(points):
    return sum(math.dist(a, b) for a, b in zip(points, points[1:]))


def layout_summary(drawing, *, width=None, max_lines=40):
    """Return (text, warnings) describing the drawing at slide size ``width`` px (default: canvas width)."""
    from ._labels import _connector_points
    from ._scene import Connector, Node, _Layout, Anchor, ContourAnchor, Edge

    layout = _Layout(drawing)
    scale = (width or drawing.width) / drawing.width
    px = lambda v: v * scale
    lines, warnings = [], []
    lines.append(
        f"画布 {drawing.width:g}×{drawing.height:g} → 页面 {px(drawing.width):.0f}×{px(drawing.height):.0f}px（缩放 {scale:.2f}）"
    )

    nodes = [(k, it) for k, it in drawing.items if isinstance(it, Node)]
    boxes = {}
    for key, node in nodes:
        try:
            boxes[key] = layout.bounds(node)
        except (ValueError, TypeError):
            continue
    if boxes:
        x0 = min(b.x for b in boxes.values())
        y0 = min(b.y for b in boxes.values())
        x1 = max(b.x + b.width for b in boxes.values())
        y1 = max(b.y + b.height for b in boxes.values())
        used = (x1 - x0) * (y1 - y0) / (drawing.width * drawing.height)
        lines.append(f"内容范围 x {px(x0):.0f}–{px(x1):.0f}, y {px(y0):.0f}–{px(y1):.0f}px，占画布 {used:.0%}")
        margins = dict(左=x0, 上=y0, 右=drawing.width - x1, 下=drawing.height - y1)
        big = [
            f"{k}{px(v):.0f}px"
            for k, v in margins.items()
            if v > 0.18 * (drawing.width if k in "左右" else drawing.height)
        ]
        if big:
            warnings.append(f"画布留白偏大（{'、'.join(big)}）：缩小画布或把内容铺开，否则放到页面后主体偏小")

    # objects: position/size in slide px, smallest text and stroke
    obj_lines = []
    for key, node in nodes:
        b = boxes.get(key)
        if b is None or key.startswith(("text", "path", "link")):
            continue
        cx, cy = b.x + b.width / 2, b.y + b.height / 2
        obj_lines.append(f"  {key}: 中心({px(cx):.0f},{px(cy):.0f}) 尺寸 {px(b.width):.0f}×{px(b.height):.0f}px")
    if obj_lines:
        lines.append(f"对象 {len(obj_lines)} 个（页面 px）：")
        lines.extend(obj_lines[: max_lines // 2])
        if len(obj_lines) > max_lines // 2:
            lines.append(f"  …其余 {len(obj_lines) - max_lines // 2} 个略")

    from ..atomize_svg_to_slide._config import _CFG

    floor = float(_CFG.get("min_slide_font_size") or 0)
    fonts = [(px(fs), k, t) for k, n in nodes for fs, t in _text_sizes(n)]
    if fonts:
        lo, hi = min(f[0] for f in fonts), max(f[0] for f in fonts)
        lines.append(
            f"文字 {len(fonts)} 段，按比例应为 {lo:.1f}–{hi:.1f}pt"
            + (f"（转换时低于 {floor:g}pt 的会被抬到 {floor:g}pt，框宽不变）" if floor and lo < floor else "")
        )
        raised = sorted(f for f in fonts if floor and f[0] < floor - 0.5)
        for size, key, text in raised[:3]:
            warnings.append(
                f"文字“{text[:12]}”（{key}）按比例只有 {size:.1f}pt，会被抬到 {floor:g}pt 而可能与邻近元素相压："
                f"把 font_size 设到 ≥{floor / scale:.0f}（画布单位）并预留空间"
            )

    # Library parts (group geometries) carry their own fine detail lines; check shapes the author drew.
    strokes = [
        (px(w), k)
        for k, n in nodes
        if n.geometry.element.tag.split("}")[-1] != "g"
        for w in _strokes(n.geometry.element)
    ]

    # connectors: real end points, routed length, slide stroke width
    link_lines = []
    for key, item in drawing.items:
        if not isinstance(item, Connector):
            continue
        try:
            pts = _connector_points(item, layout)
        except (ValueError, TypeError):
            continue
        ends = []
        for ref in (item.start, item.end):
            ends.append(ref.node.key if isinstance(ref, (Anchor, ContourAnchor, Edge)) else "点")
        length = px(_length(pts))
        sw = px(float(item.style.get("stroke_width", item.style.get("stroke-width", 1)) or 1))
        if not key.endswith("-leader"):
            strokes.append((sw, key))
        head = " 箭头" if item.style.get("marker_end") else ""
        link_lines.append(
            f"  {key}: {ends[0]}→{ends[1]} 实际长 {length:.0f}px，线宽 {sw:.1f}px{head}"
            f"，起({px(pts[0][0]):.0f},{px(pts[0][1]):.0f}) 止({px(pts[-1][0]):.0f},{px(pts[-1][1]):.0f})"
        )
        if length < MIN_LINK_PX and not key.endswith("-leader"):
            warnings.append(
                f"连线 {key}（{ends[0]}→{ends[1]}）在页面上只有 {length:.0f}px：拉开两端对象，否则箭头会糊在一起"
            )
    if link_lines:
        lines.append(f"连线 {len(link_lines)} 条：")
        lines.extend(link_lines[: max_lines // 2])
        if len(link_lines) > max_lines // 2:
            lines.append(f"  …其余 {len(link_lines) - max_lines // 2} 条略")
    thin = sorted({(round(w, 2), k) for w, k in strokes if w < MIN_STROKE_PX})
    if thin:
        names = "、".join(k for _, k in thin[:5])
        warnings.append(
            f"{len(thin)} 处线宽在页面上不足 {MIN_STROKE_PX:g}px（最细 {thin[0][0]:.2f}px，如 {names}）：加大 stroke_width 或缩小画布"
        )

    # cramped neighbours (non-overlapping objects closer than MIN_GAP_PX on the slide)
    keys = [k for k in boxes if not k.startswith(("text", "path", "link"))]
    tight = []
    for i, ka in enumerate(keys):
        a = boxes[ka]
        for kb in keys[i + 1 :]:
            b = boxes[kb]
            gx = max(b.x - (a.x + a.width), a.x - (b.x + b.width))
            gy = max(b.y - (a.y + a.height), a.y - (b.y + b.height))
            gap = max(gx, gy)
            if 0 <= px(gap) < MIN_GAP_PX:
                tight.append((px(gap), ka, kb))
    for gap, ka, kb in sorted(tight)[:4]:
        warnings.append(f"{ka} 与 {kb} 在页面上只隔 {gap:.0f}px：拉开或对齐成一组")

    text = "\n".join(
        lines + ([f"注意（{len(warnings)}）："] + [f"  - {w}" for w in warnings] if warnings else ["未发现尺寸问题"])
    )
    return text, warnings
