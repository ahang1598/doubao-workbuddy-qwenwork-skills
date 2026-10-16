"""Detail review: which subject nodes of a schematic are drawn too plainly. Structure-only, no vocabulary."""

from __future__ import annotations

import re

_SHAPES = {"rect", "circle", "ellipse", "path", "polygon", "polyline", "line"}


def _complexity(node):
    """(shape count, path segments, distinct fills) of a node's own geometry, text ignored."""
    shapes = segments = 0
    fills = set()
    for el in node.geometry.element.iter():
        tag = el.tag.rsplit("}", 1)[-1]
        if tag not in _SHAPES:
            continue
        shapes += 1
        if tag == "path":
            segments += len(re.findall(r"[MLHVCSQTAZmlhvcsqtaz]", el.get("d", "")))
        fill = el.get("fill")
        if fill and fill != "none":
            fills.add(fill.lower())
    return shapes, segments, len(fills)


def _label(node):
    return " ".join("".join(node.geometry.element.itertext()).split())


def _num(el, key):
    try:
        return round(float(el.get(key) or 0))
    except ValueError:
        return 0


def _primitive(el, tag):
    """(signature, curve segments, straight segments) of one shape; identical copies share a signature."""
    curves = lines = 0
    if tag in ("path", "polygon", "polyline"):
        if tag == "path":
            ops = re.findall(r"[MLHVCSQTAZmlhvcsqtaz]", el.get("d", ""))
            curves = sum(o in "CSQTAcsqta" for o in ops)
            lines = sum(o in "LHVZlhvz" for o in ops)
            nums = re.findall(r"-?[\d.]+(?:e-?\d+)?", el.get("d", ""))
        else:
            nums = re.findall(r"-?[\d.]+(?:e-?\d+)?", el.get("points", ""))
            lines = len(nums) // 2
        try:
            xs, ys = [float(v) for v in nums[0::2]], [float(v) for v in nums[1::2]]
            size = (round(max(xs) - min(xs)), round(max(ys) - min(ys)))
        except ValueError:
            size = ()
        sig = (tag, curves, lines, size)
    elif tag == "circle":
        sig = (tag, _num(el, "r"))
    elif tag == "ellipse":
        sig = (tag, _num(el, "rx"), _num(el, "ry"))
    elif tag == "rect":
        sig = (tag, _num(el, "width"), _num(el, "height"))
    else:
        sig = (tag, round(((_num(el, "x2") - _num(el, "x1")) ** 2 + (_num(el, "y2") - _num(el, "y1")) ** 2) ** 0.5))
    return sig, curves, lines


def _structure(node):
    """(distinct primitives, curve segments, segments of the most detailed outline, distinct fills)."""
    seen, fills = {}, set()
    for el in node.geometry.element.iter():
        tag = el.tag.rsplit("}", 1)[-1]
        if tag not in _SHAPES:
            continue
        sig, curves, lines = _primitive(el, tag)
        seen.setdefault(sig, (curves, lines))
        fill = el.get("fill")
        if fill and fill != "none":
            fills.add(fill.lower())
    curves = sum(c for c, _ in seen.values())
    longest = max((c + l for c, l in seen.values()), default=0)
    return len(seen), curves, longest, len(fills)


def _detailed(node):
    if node.kind == "part":
        return True  # library parts are drawn with their identifying features
    distinct, curves, longest, fills = _structure(node)
    # icon level: a few primitives, one hexagon/cloud outline, a circle with repeated rays -> plain
    return (distinct >= 4 and fills >= 3) or distinct >= 6 or curves >= 10 or longest >= 24


def _is_frame(node):
    """An unfilled outline with no label (zoom window, panel border) is layout, not an object."""
    if _label(node):
        return False
    fills = [el.get("fill") for el in node.geometry.element.iter() if el.tag.rsplit("}", 1)[-1] in _SHAPES]
    return bool(fills) and all(f in (None, "none") for f in fills)


# Extra subject words → part suggestions ("cell:kind" = cell(kind=...)); names absent from the registry are skipped, and a
# bare English stem also matches any registered part whose name contains it (new parts are picked up automatically).
_PART_WORDS = {
    "细菌": ("cell:bacterium", "biofilm_section"),
    "bacteri": ("cell:bacterium", "biofilm_section"),
    "菌膜": ("biofilm_section",),
    "土壤": ("soil",),
    "soil": ("soil",),
    "根际": ("soil", "root_section"),
    "能带": ("energy",),
    "能级": ("energy",),
    "band": ("energy",),
    "energy": ("energy",),
    "编码器": ("encoder_decoder",),
    "解码器": ("encoder_decoder",),
    "encoder": ("encoder_decoder",),
    "decoder": ("encoder_decoder",),
    "特征图": ("tensor_block",),
    "feature map": ("tensor_block",),
    "卷积": ("tensor_block",),
    "张量": ("tensor_block",),
    "t细胞": ("cell:t_cell",),
    "t 细胞": ("cell:t_cell",),
    "巨噬": ("cell:macrophage",),
    "macrophage": ("cell:macrophage",),
    "中性粒": ("cell:neutrophil",),
    "neutrophil": ("cell:neutrophil",),
    "树突状": ("cell:dendritic",),
    "上皮": ("cell:epithelial",),
    "肿瘤": ("cell:tumor",),
    "癌细胞": ("cell:tumor",),
    "tumor": ("cell:tumor",),
    "浆细胞": ("cell:plasma",),
}
_NOT_DETAIL = {"block", "legend_row", "text_box"}


def _registered_parts():
    from ._help import _DRAWING_APIS

    return {n for n, d in _DRAWING_APIS.items() if d.topic == "parts" and "." not in n}


def _resolve(name, parts):
    if name.startswith("cell:"):
        from ._bio_parts import _CELL_KINDS

        return [f'cell(kind="{name[5:]}")'] if "cell" in parts and name[5:] in _CELL_KINDS else []
    if name in parts:
        return [name]
    return sorted(p for p in parts if name in p)[:2]


def suggest_parts(text):
    """Registered parts that fit a subject label, matched against the help alias index and _PART_WORDS."""
    from ._help import _HELP_ALIASES

    parts = _registered_parts() - _NOT_DETAIL
    low = text.casefold()
    hits = [(len(w), names) for w, names in _PART_WORDS.items() if w in low]
    hits += [(len(a), (t,)) for a, t in _HELP_ALIASES.items() if len(a) >= 2 and t in parts and a.casefold() in low]
    hits += [(len(p), (p,)) for p in parts if len(p) >= 4 and p in low]
    out = []
    for _, names in sorted(hits, key=lambda h: -h[0]):
        for name in names:
            for r in _resolve(name, parts):
                if r not in out and not (r == "cell" and any(o.startswith("cell(") for o in out)):
                    out.append(r)
    return out[:3]


def _stacked_rects(drawing, nodes, boxes):
    """Same-size rectangles offset along one diagonal step (fake 3-D feature maps / tensor stacks)."""
    rects = [n for n in nodes if n.kind in ("rect", "box") and boxes[n.key].width > 4 and boxes[n.key].height > 4]
    seen, found = set(), []
    for a in rects:
        if a.key in seen:
            continue
        ba = boxes[a.key]
        for b in rects:
            bb = boxes[b.key]
            dx, dy = bb.x - ba.x, bb.y - ba.y
            if b is a or abs(bb.width - ba.width) > 2 or abs(bb.height - ba.height) > 2:
                continue
            if not (2 <= abs(dx) <= 0.5 * ba.width and 2 <= abs(dy) <= 0.5 * ba.height):
                continue
            chain, cur = [a, b], bb
            while True:
                nxt = next(
                    (
                        c
                        for c in rects
                        if c not in chain
                        and abs(boxes[c.key].x - cur.x - dx) < 1.5
                        and abs(boxes[c.key].y - cur.y - dy) < 1.5
                        and abs(boxes[c.key].width - ba.width) <= 2
                    ),
                    None,
                )
                if nxt is None:
                    break
                chain.append(nxt)
                cur = boxes[nxt.key]
            numeric = any(
                n.kind == "text" and re.search(r"\d", _label(n)) and _gap(boxes[n.key], ba) < max(ba.width, ba.height)
                for n in nodes
            )
            if len(chain) >= 3 or numeric:
                seen.update(c.key for c in chain)
                found.append([c.key for c in chain])
                break
    if not found:
        return []
    parts = _registered_parts()
    use = "、".join(p for p in ("tensor_block", "encoder_decoder") if p in parts) or "svg_at 手写立体外形"
    keys = [k for chain in found for k in chain][:4]
    return [
        {
            "kind": "fake_3d_stack",
            "keys": keys,
            "hint": f"{'、'.join(keys)} 是同尺寸矩形错位叠放（假立体的特征图/张量层）：改用 {use}"
            "（有顶面/侧面和网格，尺寸按 c/h/w 标注），不要用错位矩形拼",
        }
    ]


def review_drawing(drawing, *, limit=3):
    """[] when the figure's subjects are drawn with detail; otherwise up to `limit` plain subjects plus layout notes."""
    from ._scene import Node, Connector, Anchor, ContourAnchor, Edge, _Layout

    layout = _Layout(drawing)
    nodes = [n for _, n in drawing.items if isinstance(n, Node)]
    if not nodes:
        return []
    boxes = {n.key: layout.bounds(n) for n in nodes}
    canvas = drawing.width * drawing.height

    def nearest(point):
        x, y = point
        best, gap = None, 14.0
        for n in nodes:
            b = boxes[n.key]
            dx = max(b.x - x, 0, x - b.x - b.width)
            dy = max(b.y - y, 0, y - b.y - b.height)
            if (dx * dx + dy * dy) ** 0.5 <= gap and (n.kind != "text" or best is None):
                best, gap = n, (dx * dx + dy * dy) ** 0.5
        return best

    degree = {}
    for _, item in drawing.items:
        if not isinstance(item, Connector):
            continue
        for ref in (item.start, item.end):
            node = ref.node if isinstance(ref, (Anchor, ContourAnchor, Edge)) else None
            if node is None and isinstance(ref, (tuple, list)):
                node = nearest(ref)
            if node is not None:
                degree[node.key] = degree.get(node.key, 0) + 1

    # a text node sitting on a plain rect/ellipse is that shape's label: one object, degrees merged
    label_of, merged = {}, {}
    for t in nodes:
        if t.kind != "text":
            continue
        tb = boxes[t.key]
        cx, cy = tb.x + tb.width / 2, tb.y + tb.height / 2
        for s in nodes:
            sb = boxes[s.key]
            if s.kind in ("rect", "ellipse") and sb.x <= cx <= sb.x + sb.width and sb.y <= cy <= sb.y + sb.height:
                label_of[s.key] = _label(t)
                merged[t.key] = s.key
                degree[s.key] = degree.get(s.key, 0) + degree.pop(t.key, 0)
                break

    candidates = []
    for n in nodes:
        if n.key in merged or _is_frame(n) or boxes[n.key].width * boxes[n.key].height > 0.4 * canvas:
            continue
        if n.kind is None and not _complexity(n)[0]:
            continue  # callout / auto labels
        if n.kind == "text" and not degree.get(n.key):
            continue  # captions and annotations are text by design
        if not degree.get(n.key) and n.kind not in ("part", "svg", "box", "rect", "ellipse"):
            continue
        candidates.append(n)
    if not candidates:
        return []
    area = sorted((boxes[n.key].width * boxes[n.key].height for n in candidates), reverse=True)
    big = area[min(2, len(area) - 1)]
    subjects = [n for n in candidates if degree.get(n.key) or boxes[n.key].width * boxes[n.key].height >= big]
    detailed = [n for n in subjects if _detailed(n)]
    rank = lambda n: (-degree.get(n.key, 0), -boxes[n.key].width * boxes[n.key].height)
    # the figure's main characters: the few most connected / largest subjects
    main = sorted(subjects, key=rank)[: max(3, len(subjects) // 3)]
    plain = [n for n in main if not _detailed(n)]
    out = []
    if plain and sum(_detailed(n) for n in main) < len(main) / 2:
        for n in plain[:limit]:
            shapes = _complexity(n)[0]
            text = _label(n) or label_of.get(n.key, "")
            drawn = {
                "box": "一个文字框",
                "rect": "一个矩形",
                "ellipse": "一个椭圆",
                "text": "一段纯文字",
                "svg": f"图标级 svg_at（{_structure(n)[0]} 种简单图元，重复的算一种）",
            }.get(n.kind, f"{shapes} 个简单图形")
            fit = suggest_parts(f"{text} {n.key}")
            use = f"用 {' / '.join(fit)} " if fit else "用对应部件"
            out.append(
                {
                    "kind": "plain_subject",
                    "keys": [n.key],
                    "label": text[:24],
                    "degree": degree.get(n.key, 0),
                    "parts": fit,
                    "hint": f"{n.key}{'「' + text[:16] + '」' if text else ''} 是图里的主体之一（{degree.get(n.key, 0)} 条连线），"
                    f"但只画成{drawn}：如果它是实体（蛋白、细胞、器件、颗粒、模型结构…），{use}或 svg_at 手写外形、"
                    "再 node.replace_svg 原位替换（连线跟着走）；如果只是概念或步骤标签，保留方框即可",
                }
            )
    out.extend(_stacked_rects(drawing, nodes, boxes))
    out.extend(_isolated(subjects, nodes, boxes, degree, merged))
    out.extend(_apart_pairs(drawing, layout, boxes, nearest))
    # two long parallel horizontal lines: a membrane/layer sketched with d.line
    lines = []
    for key, item in drawing.items:
        if isinstance(item, Connector) and not item.style.get("marker_end"):
            try:
                (x1, y1), (x2, y2) = layout.point(item.start), layout.point(item.end)
            except (TypeError, ValueError):
                continue
            if abs(y1 - y2) < 1 and abs(x2 - x1) > drawing.width * 0.4:
                lines.append((key, y1))
    lines.sort(key=lambda kv: kv[1])
    for (ka, ya), (kb, yb) in zip(lines, lines[1:]):
        if 6 <= yb - ya <= 40:
            out.append(
                {
                    "kind": "sketched_layer",
                    "keys": [ka, kb],
                    "hint": f"{ka}/{kb} 两条平行长线像手画的膜或界面层：膜用 d.add('mem', membrane(\"M x0 y L x1 y\", "
                    f"thickness={yb - ya:.0f}))，器件/界面层用 layer_stack / interface_section",
                }
            )
            break
    glyphs = [n.key for n in nodes if n.kind == "text" and re.fullmatch(r"\s*[⊣→←↑↓⟶⇒⊥⟵]+\s*", _label(n))]
    if glyphs:
        out.append(
            {
                "kind": "glyph_arrow",
                "keys": glyphs[:4],
                "hint": f"{'、'.join(glyphs[:4])} 用字符表示箭头/抑制：改成 d.arrow(a, b, head='arrow'/'inhibit')，端点落在对象上",
            }
        )
    if len(subjects) >= 4 and len(detailed) / len(subjects) < 0.2 and any(o["kind"] == "plain_subject" for o in out):
        fits = {}
        for n in subjects:
            fit = [] if _detailed(n) else suggest_parts(f"{_label(n) or label_of.get(n.key, '')} {n.key}")
            if fit:
                fits[n.key] = fit[0]
        named = "；".join(f"{k} → {p}" for k, p in list(fits.items())[:4])
        out.append(
            {
                "kind": "mostly_plain",
                "keys": [],
                "parts": sorted(set(fits.values())),
                "hint": f"{len(subjects)} 个主体里只有 {len(detailed)} 个有细节，整张图读起来像流程图而不是机制图"
                + (f"（可换成部件：{named}）" if named else ""),
            }
        )
    return out


def _gap(a, b):
    dx = max(a.x - b.x - b.width, b.x - a.x - a.width, 0)
    dy = max(a.y - b.y - b.height, b.y - a.y - a.height, 0)
    return (dx * dx + dy * dy) ** 0.5


def _isolated(subjects, nodes, boxes, degree, merged, near=12):
    """Subjects with no connector, not contained in and not touching any other drawn object."""
    others = [
        n for n in nodes if n.kind != "text" and n.key not in merged and (n.kind is not None or _complexity(n)[0])
    ]
    lonely = []
    for n in subjects:
        if degree.get(n.key) or n.kind == "text":
            continue
        b = boxes[n.key]
        if not any(o is not n and _gap(b, boxes[o.key]) < near for o in others):
            lonely.append(n.key)
    if len(lonely) < 2:
        return []
    names = "、".join(lonely[:4])
    return [
        {
            "kind": "isolated_subject",
            "keys": lonely[:4],
            "hint": f"{names} 与图中其他对象没有任何关系（无连线、未接触）：机制图里每个主体都应通过箭头/接触/包含与其他对象相连",
        }
    ]


def _apart_pairs(drawing, layout, boxes, nearest):
    """Mounted parts on two different hosts joined by an unmarked line: a receptor–ligand bond drawn across a gap."""
    from ._scene import Connector, Anchor, ContourAnchor, Edge

    out = []
    for key, item in drawing.items:
        if not isinstance(item, Connector) or item.style.get("marker_end") or item.style.get("marker_start"):
            continue
        ends = []
        for ref in (item.start, item.end):
            node = ref.node if isinstance(ref, (Anchor, ContourAnchor, Edge)) else None
            if node is None and isinstance(ref, (tuple, list)):
                node = nearest(ref)
            ends.append(node)
        a, b = ends
        if a is None or b is None or a is b or a.kind != "part" or b.kind != "part":
            continue
        ha, hb = getattr(a, "mounted_on", None), getattr(b, "mounted_on", None)
        if not ha or not hb or ha == hb or ha not in boxes or hb not in boxes:
            continue
        if _gap(boxes[ha], boxes[hb]) < 12:
            continue
        out.append(
            {
                "kind": "apart_binding",
                "keys": [key, a.key, b.key],
                "hint": f"{a.key}（在 {ha} 上）与 {b.key}（在 {hb} 上）用无箭头线隔空相连：受体-配体结合应直接接触——"
                '改用 cell_interface([{"top": 受体, "bottom": 配体}])，或把两细胞移到贴合',
            }
        )
        break
    return out
