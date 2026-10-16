"""Electromagnetism / circuit teaching parts drawn like textbook figures (Halliday-style)."""

from __future__ import annotations

import math

from ..atomize_svg_to_slide._geometry import fmt
from ._bio_parts import _circ, _el, _look, _mix
from ._geometry import Box, _finite, _union
from ._help import _drawing_api
from ._tech_parts import _centered_text, _finish, _head, _linear, _poly, _start, _style, _txt, circuit_symbol

_WIRE = "#1E1E1E"
_CURRENT = "#D0342C"
_FIELD = "#3A5D8F"
_COPPER = "#B5652B"
_IRON = "#8E979F"


def _arrow(holder, boxes, x1, y1, x2, y2, color, sw, head):
    """Straight arrow with a filled head whose tip is (x2, y2)."""
    n = math.hypot(x2 - x1, y2 - y1) or 1
    bx, by = x2 - (x2 - x1) / n * head * 0.8, y2 - (y2 - y1) / n * head * 0.8
    holder.append(
        _el(
            "path",
            d=f"M{fmt(x1)} {fmt(y1)} L{fmt(bx)} {fmt(by)}",
            fill="none",
            stroke=color,
            stroke_width=sw,
            stroke_linecap="round",
        )
    )
    holder.append(_head(x2, y2, x2 - x1, y2 - y1, head, color))
    boxes.append(Box(min(x1, x2) - head / 2, min(y1, y2) - head / 2, abs(x2 - x1) + head, abs(y2 - y1) + head))


def _hit(x, y, r, keep):
    return any(b.x - r < x < b.x + b.width + r and b.y - r < y < b.y + b.height + r for b in keep)


def _marks(points, direction, r, color, sw):
    """⊗ (into the page) or ⊙ (out of the page) marks merged into two native paths."""
    if not points:
        return []
    rings = _el("path", d=" ".join(_circ(x, y, r) for x, y in points), fill="#FFFFFF", stroke=color, stroke_width=sw)
    if direction == "in":
        q = r * 0.58
        sym = _el(
            "path",
            d=" ".join(
                f"M{fmt(x - q)} {fmt(y - q)} L{fmt(x + q)} {fmt(y + q)} M{fmt(x + q)} {fmt(y - q)} "
                f"L{fmt(x - q)} {fmt(y + q)}"
                for x, y in points
            ),
            fill="none",
            stroke=color,
            stroke_width=sw,
            stroke_linecap="round",
        )
    else:
        sym = _el("path", d=" ".join(_circ(x, y, max(1.2, r * 0.3)) for x, y in points), fill=color, stroke="none")
    return [rings, sym]


def _field_label(holder, boxes, x, y, text, direction, fs, color, anchor="end"):
    """'B' (italic bold) followed by a small ⊗/⊙ legend mark; baseline at y, anchored at x."""
    el, b = _txt(0, 0, text, fs, fill=color, weight="bold", italic=True)
    r = fs * 0.32
    w = b.width + 4 + 2 * r
    x0 = x - w if anchor == "end" else x
    el, b = _txt(x0, y, text, fs, fill=color, anchor="start", weight="bold", italic=True)
    holder.append(el)
    boxes.append(b)
    holder.extend(_marks([(x0 + b.width + 4 + r, y - fs * 0.34)], direction, r, color, 1.1))
    boxes.append(Box(x0 + b.width + 4 - 0.6, y - fs * 0.34 - r - 0.6, 2 * r + 1.2, 2 * r + 1.2))


def _check_dir(direction):
    if direction not in ("in", "out"):
        raise ValueError('direction must be "in" (⊗, into the page) or "out" (⊙, out of the page)')


@_drawing_api(
    "parts",
    purpose="垂直纸面的匀强磁场区域：整齐的 ⊗（向里）/ ⊙（向外）标记网格 + 虚线区域框 + B 标注，可留出空洞让线圈/导体棒压在上面。",
    returns="Geometry（端口 center、四角 tl/tr/bl/br、四边；keepout 给出时另有 hole 为空洞中心）",
    semantics=(
        'width/height 为区域尺寸；direction="in" 画 ⊗、"out" 画 ⊙；spacing 为标记间距，mark_r 为标记半径（默认 spacing×0.16）。',
        "keepout=(x, y, w, h)（相对区域中心的局部坐标）或其列表：这些框内不画标记，放在上面的部件不会压住标记；导轨+导体棒直接用 rails_rod(field=…)。",
        'region=True 画虚线区域框；label="B" 写在框右上角外侧并附小标记，label=None 不写。全部原生，style 仅为接口一致。',
    ),
    example='d.place(field_marks(360, 220, direction="in", keepout=(-60, -40, 120, 80)), at=(480, 270), key="B")',
    rank=20,
)
def field_marks(
    width,
    height,
    *,
    direction="in",
    spacing=36,
    mark_r=None,
    region=True,
    label="B",
    keepout=None,
    color=_FIELD,
    font_size=16,
    style="rich",
):
    _finite(width, height, spacing)
    _check_dir(direction)
    _style(style)
    if spacing <= 0:
        raise ValueError("spacing must be positive")
    r = mark_r or max(4.0, min(9.0, spacing * 0.16))
    holder, defs = _el("g"), None
    w, h = float(width), float(height)
    keep = []
    for k in [keepout] if keepout and not isinstance(keepout[0], (tuple, list, Box)) else (keepout or ()):
        b = k if isinstance(k, Box) else Box(*k)
        keep.append(Box(b.x + w / 2, b.y + h / 2, b.width, b.height))
    cols, rows = max(1, int(w // spacing)), max(1, int(h // spacing))
    gx, gy = w / cols, h / rows
    pts = [(gx * (i + 0.5), gy * (j + 0.5)) for j in range(rows) for i in range(cols)]
    pts = [p for p in pts if not _hit(p[0], p[1], r + 3, keep)]
    boxes = [Box(0, 0, w, h)]
    if region:
        holder.append(
            _el(
                "rect",
                x=0,
                y=0,
                width=w,
                height=h,
                fill="none",
                stroke=_mix(color, "#FFFFFF", 0.2),
                stroke_width=1.1,
                stroke_dasharray="6 4",
            )
        )
    holder.extend(_marks(pts, direction, r, color, max(1.0, r * 0.2)))
    if label:
        _field_label(holder, boxes, w, -font_size * 0.45, label, direction, font_size, color)
    ports = dict(tl=(0, 0), tr=(w, 0), bl=(0, h), br=(w, h), center=(w / 2, h / 2))
    if keep:
        ports["hole"] = (keep[0].x + keep[0].width / 2, keep[0].y + keep[0].height / 2)
    return _finish(holder, defs, _union(boxes), **ports)


def _current_dir(current, s):
    """+1 = current flows lead_a → lead_b."""
    if current in (None, False):
        return 0
    table = {"a_to_b": 1, "b_to_a": -1, "cw": s, "ccw": -s}
    if current not in table:
        raise ValueError('current must be None, "cw", "ccw", "a_to_b" or "b_to_a"')
    return table[current]


def _helix(x0, pitch, turns, R, e, s, n=18):
    """Projected helix split into back and front half-turn polylines (each starts where the previous ended)."""
    back, front, mids = [], [], []
    for c in range(turns):
        for half in (0, 1):
            th0 = 2 * math.pi * c + math.pi * half
            pts = []
            for i in range(n + 1):
                th = th0 + math.pi * i / n
                pts.append((x0 + pitch * th / (2 * math.pi) + s * e * math.sin(th), R * math.cos(th)))
            is_front = (half == 0) == (s > 0)
            (front if is_front else back).append(pts)
            if is_front:
                mids.append((pts[n // 2], pts[n // 2 + 1]))
    return back, front, mids


def _wire_paint(color, sw):
    return dict(fill="none", stroke=color, stroke_width=sw, stroke_linecap="round", stroke_linejoin="round")


@_drawing_api(
    "parts",
    purpose="线圈（教科书电磁学插图）：螺线管（立体螺旋，前圈深、后圈浅，可加铁芯）、单匝线圈（正视圆/矩形或透视椭圆）、环形线圈；可画电流方向箭头、内部磁感线与 N/S 极。",
    returns="Geometry（端口 lead_a/lead_b 为两根引线末端；end_a/end_b 为两端面中心，axis 为轴心；给出 current 时另有 north/south 为两极端面）",
    semantics=(
        'kind="solenoid" 轴线水平，length 为绕线长、diameter 为直径、turns 为匝数；core="iron" 在后圈与前圈之间画铁芯（立体渐变）；winding="right"/"left" 为绕向。',
        'current="cw"/"ccw" 为从右端（lead_b 一侧）沿轴看去的环绕方向，也可传 "a_to_b"/"b_to_a"；按右手定则自动给 north/south 端口，引线标 I 与箭头；field_lines=True 画管内匀强磁感线与两条外部回线（需 current）。',
        'kind="loop" 单匝线圈：shape="circle"/"rect"，view="face"（正视，cw/ccw 为观察者所见）或 "perspective"（透视，轴线水平，cw/ccw 从右看）；kind="toroid" 环形线圈（正视圆环 + 径向匝；current 为环内 B 的环绕方向）。',
        '接电流计：g = d.place(circuit_symbol("galvanometer"), …)，再 d.line(coil.port("lead_b"), g.port("a"), route="orthogonal")；磁铁插入线圈示意时让 magnet 的 north 端口对准 end_a。',
    ),
    example='d.place(coil(8, length=220, diameter=90, core="iron", current="cw", field_lines=True), at=(480, 270), key="L")',
    rank=21,
)
def coil(
    turns=8,
    *,
    kind="solenoid",
    length=None,
    diameter=80,
    core=False,
    current=None,
    winding="right",
    shape="circle",
    view="perspective",
    field_lines=False,
    lead=None,
    wire=_COPPER,
    stroke_width=None,
    current_color=_CURRENT,
    field_color=_FIELD,
    label_current="I",
    font_size=14,
    style="rich",
):
    if kind not in ("solenoid", "loop", "toroid"):
        raise ValueError("coil kind must be solenoid, loop or toroid")
    if winding not in ("right", "left"):
        raise ValueError('winding must be "right" or "left"')
    if core not in (False, None, True, "iron", "air"):
        raise ValueError('core must be False or "iron"')
    _finite(diameter)
    rich = _style(style)
    turns = max(1, int(turns))
    s = -1 if winding == "right" else 1  # helix parametrisation: s=-1 is right-handed
    if kind == "loop":
        return _loop(
            diameter,
            length,
            shape,
            view,
            current,
            s,
            lead,
            wire,
            stroke_width,
            current_color,
            label_current,
            font_size,
            rich,
        )
    if kind == "toroid":
        return _toroid(
            turns, diameter, current, lead, wire, stroke_width, current_color, label_current, font_size, rich
        )
    turns = max(2, turns)
    R = diameter / 2
    L = float(length or max(turns * 18, diameter * 1.6))
    _finite(L)
    pitch = L / turns
    sw = stroke_width or max(2.0, min(4.2, pitch * 0.2))
    e = min(R * 0.24, pitch * 0.5)  # oblique offset of the near half-turn
    lead = R * 0.7 if lead is None else lead
    dirn = _current_dir(current, s)
    holder, defs = _start(rich)
    back, front, mids = _helix(0, pitch, turns, R, e, s)
    xa, xb = 0.0, L  # helix starts and ends at the bottom (y = R)
    boxes = [Box(-e - sw, -R - sw, L + 2 * e + 2 * sw, 2 * R + 2 * sw)]
    back_c, front_c = _mix(wire, "#FFFFFF", 0.45), _mix(wire, "#000000", 0.12)
    # outline first: the envelope of the winding (invisible) keeps contour / lint geometry sane
    holder.append(
        _el(
            "path",
            d=_poly([(-e, -R), (L + e, -R), (L + e, R), (-e, R)], True),
            fill="none",
            stroke="none",
            data_outline="1",
        )
    )
    holder.append(_el("path", d=" ".join(_poly(p) for p in back), **_wire_paint(back_c, sw * 0.8)))
    cr = R * 0.62
    if core in (True, "iron"):
        ext = min(R * 0.5, 22)
        cx0, cx1 = -ext, L + ext
        ce = e * 0.62
        body = (
            f"M{fmt(cx0)} {fmt(-cr)} H{fmt(cx1)} A{fmt(ce)} {fmt(cr)} 0 0 1 {fmt(cx1)} {fmt(cr)} H{fmt(cx0)} "
            f"A{fmt(ce)} {fmt(cr)} 0 0 1 {fmt(cx0)} {fmt(-cr)} Z"
        )
        holder.append(_el("path", d=body, fill=_IRON, stroke=_mix(_IRON, "#000000", 0.4), stroke_width=1.1))
        holder.append(
            _el(
                "ellipse",
                cx=cx1,
                cy=0,
                rx=ce,
                ry=cr,
                fill=_mix(_IRON, "#FFFFFF", 0.3),
                stroke=_mix(_IRON, "#000000", 0.4),
                stroke_width=1.1,
            )
        )
        if rich:
            defs.append(
                _linear(
                    "iron", [(0, "#FFFFFF", 0.55), (0.35, "#FFFFFF", 0.1), (0.7, "#000000", 0.12), (1, "#000000", 0.35)]
                )
            )
            look = _look()
            look.append(
                _el("path", d=f"M{fmt(cx0)} {fmt(-cr)} H{fmt(cx1)} V{fmt(cr)} H{fmt(cx0)} Z", fill="url(#iron)")
            )
            holder.append(look)
        boxes.append(Box(cx0 - ce, -cr, cx1 - cx0 + 2 * ce, 2 * cr))
    ports = dict(end_a=(0, 0), end_b=(L, 0), axis=(L / 2, 0))
    m = -s * dirn  # sign of the magnetic moment along +x (right-hand rule)
    if field_lines and dirn:
        fc = field_color
        ext = R * 0.9
        ys = (-cr * 0.55, 0, cr * 0.55)
        d = " ".join(f"M{fmt(-ext)} {fmt(y)} H{fmt(L + ext)}" for y in ys)
        holder.append(_el("path", d=d, fill="none", stroke=fc, stroke_width=1.3))
        for y in ys:
            tip = (L + ext + 7, y) if m > 0 else (-ext - 7, y)
            holder.append(_head(tip[0], tip[1], m, 0, 8, fc))
        boxes.append(Box(-ext - 8, -cr, L + 2 * ext + 16, 2 * cr))
        # two return loops outside, closing from the N end back to the S end
        ry = R + max(26, R * 0.55)
        rets = []
        for sg in (-1, 1):
            y0 = sg * cr * 0.55
            rets.append(
                f"M{fmt(L + ext)} {fmt(y0)} C{fmt(L + ext + R * 1.1)} {fmt(y0)} {fmt(L + ext + R * 0.6)} {fmt(sg * ry)} {fmt(L / 2)} {fmt(sg * ry)} "
                f"C{fmt(-ext - R * 0.6)} {fmt(sg * ry)} {fmt(-ext - R * 1.1)} {fmt(y0)} {fmt(-ext)} {fmt(y0)}"
            )
            holder.append(_head(L / 2 - m * 7, sg * ry, -m, 0, 8, fc))
            boxes.append(Box(-ext - R * 0.8, min(y0, sg * ry) - 1, L + 2 * ext + R * 1.6, abs(sg * ry - y0) + 2))
        holder.append(_el("path", d=" ".join(rets), fill="none", stroke=fc, stroke_width=1.1, stroke_dasharray="5 3"))
    holder.append(_el("path", d=" ".join(_poly(p) for p in front), **_wire_paint(front_c, sw)))
    if rich:
        look = _look()
        look.append(
            _el(
                "path",
                d=" ".join(_poly(p) for p in front),
                fill="none",
                stroke="#FFFFFF",
                stroke_width=sw * 0.32,
                stroke_opacity=0.55,
                stroke_linecap="round",
                transform=f"translate({fmt(-sw * 0.2)} {fmt(-sw * 0.25)})",
            )
        )
        holder.append(look)
    ya = R + lead
    holder.append(
        _el(
            "path",
            d=f"M{fmt(xa)} {fmt(R)} V{fmt(ya)} M{fmt(xb)} {fmt(R)} V{fmt(ya)}",
            **_wire_paint(_WIRE, max(1.6, sw * 0.6)),
        )
    )
    for x in (xa, xb):
        holder.append(_el("circle", cx=x, cy=ya, r=2.6, fill=_WIRE))
    boxes.append(Box(xa - 3, R, xb - xa + 6, lead + 3))
    ports.update(lead_a=(xa, ya), lead_b=(xb, ya))
    if dirn:
        cc = current_color
        k = max(1, turns // 3)
        for i, (p, q) in enumerate(mids):
            if i % k == k // 2 or turns <= 3:
                dx, dy = (q[0] - p[0]) * dirn, (q[1] - p[1]) * dirn
                n = math.hypot(dx, dy) or 1
                mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
                holder.append(_head(mx + dx / n * 5, my + dy / n * 5, dx, dy, 10, cc))
        # current on lead_a: into the coil (up) when a→b
        ym = R + lead * 0.55
        holder.append(_head(xa, ym - 5 * dirn, 0, -dirn, 9, cc))
        el, b = _txt(
            xa - 7, ym + font_size * 0.35, label_current, font_size, fill=cc, anchor="end", italic=True, weight="bold"
        )
        holder.append(el)
        boxes.append(b)
        north, south = ((L, 0), (0, 0)) if m > 0 else ((0, 0), (L, 0))
        ports.update(north=north, south=south)
    return _finish(holder, defs, _union(boxes), **ports)


def _loop(diameter, length, shape, view, current, s, lead, wire, stroke_width, cc, label_current, fs, rich):
    if shape not in ("circle", "rect"):
        raise ValueError("loop shape must be circle or rect")
    if view not in ("face", "perspective"):
        raise ValueError("loop view must be face or perspective")
    R = diameter / 2
    sw = stroke_width or 3.0
    lead = R * 0.55 if lead is None else lead
    holder, defs = _start(rich)
    gap = max(8.0, R * 0.14)
    dirn = 0 if current in (None, False) else {"cw": 1, "ccw": -1}.get(current)
    if dirn is None:
        raise ValueError('loop current must be None, "cw" or "ccw"')
    wp = _wire_paint(_mix(wire, "#000000", 0.12), sw)
    boxes, ports, heads = [], {}, []
    if view == "face":
        W = (length or diameter) / 2 if shape == "rect" else R
        if shape == "circle":
            a0 = math.asin(min(0.9, gap / 2 / R))
            p0 = (-R * math.sin(a0), R * math.cos(a0))
            p1 = (R * math.sin(a0), R * math.cos(a0))
            d = f"M{fmt(p0[0])} {fmt(p0[1])} A{fmt(R)} {fmt(R)} 0 1 1 {fmt(p1[0])} {fmt(p1[1])}"
            for ang in (-math.pi / 2, 0, math.pi / 2, math.pi):  # top, right, bottom-ish skipped below
                if abs(ang - math.pi / 2) < 1e-9:
                    continue
                x, y = R * math.cos(ang), R * math.sin(ang)
                heads.append((x, y, -math.sin(ang) * dirn, math.cos(ang) * dirn))
        else:
            p0, p1 = (-gap / 2, R), (gap / 2, R)
            d = _poly([p0, (-W, R), (-W, -R), (W, -R), (W, R), p1])
            heads += [(0, -R, dirn, 0), (W, 0, 0, dirn), (-W, 0, 0, -dirn)]
        holder.append(_el("path", d=d, data_outline="1", **wp))
        boxes.append(Box(-W - sw, -R - sw, 2 * W + 2 * sw, 2 * R + 2 * sw))
        ports["center"] = (0, 0)
    else:
        e = R * 0.34
        n = 36
        th_gap = math.asin(min(0.9, gap / 2 / e))
        front = [
            (e * math.sin(t), R * math.cos(t)) for t in (th_gap + (math.pi - th_gap) * i / n for i in range(n + 1))
        ]
        back = [
            (e * math.sin(t), R * math.cos(t)) for t in (math.pi + (math.pi - th_gap) * i / n for i in range(n + 1))
        ]
        if shape == "rect":
            W = (length or diameter) * 0.5
            front = [(e * 0.5, R), (e, R * 0.55), (e, -R * 0.95), (e * 0.5, -R)]
            back = [(e * 0.5, -R), (-e * 0.5, -R), (-e, -R * 0.95), (-e, R * 0.55), (-e * 0.5, R)]
            p0, p1 = (-e * 0.5, R), (e * 0.5, R)
        else:
            p0, p1 = back[-1], front[0]
        holder.append(
            _el(
                "path",
                d=_poly([(-e, -R), (e, -R), (e, R), (-e, R)], True),
                fill="none",
                stroke="none",
                data_outline="1",
            )
        )
        holder.append(_el("path", d=_poly(back), **_wire_paint(_mix(wire, "#FFFFFF", 0.45), sw * 0.8)))
        holder.append(_el("path", d=_poly(front), **wp))
        p0, p1 = (p0, p1) if p0[0] < p1[0] else (p1, p0)
        # cw seen from the right end: current runs up the near (right) arc
        heads.append((e, 0, 0, -dirn))
        boxes.append(Box(-e - sw, -R - sw, 2 * e + 2 * sw, 2 * R + 2 * sw))
        ports.update(center=(0, 0), axis=(0, 0))
        if dirn:
            ports.update(north=(-e - 4, 0) if dirn > 0 else (e + 4, 0), south=(e + 4, 0) if dirn > 0 else (-e - 4, 0))
    ya = max(p0[1], p1[1]) + lead
    holder.append(
        _el(
            "path",
            d=f"M{fmt(p0[0])} {fmt(p0[1])} V{fmt(ya)} M{fmt(p1[0])} {fmt(p1[1])} V{fmt(ya)}",
            **_wire_paint(_WIRE, max(1.6, sw * 0.6)),
        )
    )
    for p in (p0, p1):
        holder.append(_el("circle", cx=p[0], cy=ya, r=2.6, fill=_WIRE))
    boxes.append(Box(p0[0] - 3, min(p0[1], p1[1]), p1[0] - p0[0] + 6, ya - min(p0[1], p1[1]) + 3))
    ports.update(lead_a=(p0[0], ya), lead_b=(p1[0], ya))
    if dirn:
        for x, y, dx, dy in heads:
            nn = math.hypot(dx, dy) or 1
            holder.append(_head(x + dx / nn * 6, y + dy / nn * 6, dx, dy, 11, cc))
        if label_current:
            hx, hy = heads[0][0], heads[0][1]
            el, b = _txt(
                hx + (14 if view == "perspective" else 0),
                hy - (12 if view == "face" else -fs * 0.35),
                label_current,
                fs,
                fill=cc,
                anchor="start" if view == "perspective" else "middle",
                italic=True,
                weight="bold",
            )
            holder.append(el)
            boxes.append(b)
    return _finish(holder, defs, _union(boxes), **ports)


def _toroid(turns, diameter, current, lead, wire, stroke_width, cc, label_current, fs, rich):
    R = diameter / 2
    ri = R * 0.58
    turns = max(6, turns)
    sw = stroke_width or 2.4
    lead = R * 0.35 if lead is None else lead
    holder, defs = _start(rich)
    core = _IRON
    ring = (
        f"M{fmt(R * 0.93)} 0 A{fmt(R * 0.93)} {fmt(R * 0.93)} 0 1 0 {fmt(-R * 0.93)} 0 A{fmt(R * 0.93)} {fmt(R * 0.93)} 0 1 0 {fmt(R * 0.93)} 0 Z "
        f"M{fmt(ri * 1.07)} 0 A{fmt(ri * 1.07)} {fmt(ri * 1.07)} 0 1 1 {fmt(-ri * 1.07)} 0 A{fmt(ri * 1.07)} {fmt(ri * 1.07)} 0 1 1 {fmt(ri * 1.07)} 0 Z"
    )
    holder.append(
        _el(
            "path",
            d=ring,
            fill=_mix(core, "#FFFFFF", 0.45),
            stroke=_mix(core, "#000000", 0.3),
            stroke_width=1.1,
            fill_rule="evenodd",
            data_outline="1",
        )
    )
    gap = 2 * math.pi / turns
    th0 = math.pi / 2 + gap / 2  # leave the bottom turn open for the leads
    front, back = [], []
    for i in range(turns - 1):
        t = th0 + i * gap
        t2 = t + gap * 0.5
        front.append(f"M{fmt(ri * math.cos(t))} {fmt(ri * math.sin(t))} L{fmt(R * math.cos(t))} {fmt(R * math.sin(t))}")
        back.append(
            f"M{fmt(R * math.cos(t))} {fmt(R * math.sin(t))} L{fmt(ri * math.cos(t2))} {fmt(ri * math.sin(t2))}"
        )
    holder.append(_el("path", d=" ".join(back), **_wire_paint(_mix(wire, "#FFFFFF", 0.45), sw * 0.7)))
    holder.append(_el("path", d=" ".join(front), **_wire_paint(_mix(wire, "#000000", 0.12), sw)))
    tb = th0 + (turns - 1.5) * gap
    pa = (ri * math.cos(th0), ri * math.sin(th0))
    pb = (ri * math.cos(tb + gap * 0.5), ri * math.sin(tb + gap * 0.5))
    ya = R + lead
    holder.append(
        _el(
            "path",
            d=f"M{fmt(pa[0])} {fmt(pa[1])} L{fmt(pa[0] * 0.3)} {fmt(R * 0.75)} V{fmt(ya)} "
            f"M{fmt(pb[0])} {fmt(pb[1])} L{fmt(pb[0] * 0.3)} {fmt(R * 0.75)} V{fmt(ya)}",
            **_wire_paint(_WIRE, 1.6),
        )
    )
    xa, xb = sorted((pa[0] * 0.3, pb[0] * 0.3))
    for x in (xa, xb):
        holder.append(_el("circle", cx=x, cy=ya, r=2.6, fill=_WIRE))
    boxes = [Box(-R - sw, -R - sw, 2 * R + 2 * sw, 2 * R + lead + 2 * sw)]
    ports = dict(center=(0, 0), lead_a=(xa, ya), lead_b=(xb, ya))
    if current in ("cw", "ccw"):
        dirn = 1 if current == "cw" else -1
        rm = (R + ri) / 2
        holder.append(
            _el("path", d=_circ(0, 0, rm), fill="none", stroke=_FIELD, stroke_width=1.2, stroke_dasharray="5 3")
        )
        for ang in (-math.pi / 2, 0, math.pi):
            x, y = rm * math.cos(ang), rm * math.sin(ang)
            holder.append(
                _head(
                    x - math.sin(ang) * dirn * 5,
                    y + math.cos(ang) * dirn * 5,
                    -math.sin(ang) * dirn,
                    math.cos(ang) * dirn,
                    9,
                    _FIELD,
                )
            )
        el, b = _centered_text(0, 0, "B", fs, fill=_FIELD, italic=True, weight="bold")
        holder.append(el)
        boxes.append(b)
    elif current not in (None, False):
        raise ValueError('toroid current must be None, "cw" or "ccw"')
    return _finish(holder, defs, _union(boxes), **ports)


def _place_on(holder, boxes, g, a, b, kind=None):
    """Put a horizontal symbol (a at local (0, 0), b at (L, 0)) on the segment a→b; text and meter dials stay upright."""
    import copy

    (ax, ay), (bx, by) = a, b
    ang = math.degrees(math.atan2(by - ay, bx - ax))
    el = copy.deepcopy(g.element)
    ox, oy = g.ports["a"]
    if kind in _UPRIGHT and abs(ang) > 1e-6:  # meter dials and letters, ± signs follow the page, not the wire
        cx, cy = (g.ports["b"][0] - g.ports["a"][0]) / 2, 0.0  # symbol centre in its own (pre-centring) frame
        leaves = [n for n in el.iter() if n.tag != "g"]
        for n in leaves[2:]:  # [0] = leads, [1] = body circle
            if n.tag != "text":
                n.set("transform", f"rotate({fmt(-ang)} {fmt(cx)} {fmt(cy)})")
    texts = [t for t in el.iter("text")]
    for t in texts:  # keep labels upright: counter-rotate around their anchor
        tx, ty = float(t.get("x")), float(t.get("y"))
        t.set("transform", f"rotate({fmt(-ang)} {fmt(tx)} {fmt(ty - float(t.get('font-size')) * 0.35)})")
    wrap = _el("g", transform=f"translate({fmt(ax)} {fmt(ay)}) rotate({fmt(ang)}) translate({fmt(-ox)} {fmt(-oy)})")
    wrap.append(el)
    holder.append(wrap)
    c, s_ = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    bb = g.bounds
    pts = [
        (bb.x - ox, bb.y - oy),
        (bb.x + bb.width - ox, bb.y - oy),
        (bb.x - ox, bb.y + bb.height - oy),
        (bb.x + bb.width - ox, bb.y + bb.height - oy),
    ]
    pts = [(ax + x * c - y * s_, ay + x * s_ + y * c) for x, y in pts]
    xs, ys = zip(*pts)
    boxes.append(Box(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)))


_SIDES = ("top", "right", "bottom", "left")
_UPRIGHT = ("galvanometer",)


def _loop_layout(elements):
    """[('battery', 'left'), …] or [kind, …] (clockwise from the top) → {side: [(kind, opts), …]}."""
    out = {k: [] for k in _SIDES}
    items = list(elements)
    if items and all(isinstance(e, str) for e in items):
        order = {1: ("left",), 2: ("left", "right"), 3: ("left", "top", "right"), 4: ("left", "top", "right", "bottom")}
        sides = order.get(len(items)) or [_SIDES[(i + 3) % 4] for i in range(len(items))]
        items = list(zip(items, sides))
    for e in items:
        if isinstance(e, dict):
            e = dict(e)
            kind = e.pop("kind")
            side = e.pop("side")
            opts = e
        else:
            kind, side, *rest = e
            opts = dict(rest[0]) if rest else {}
        if side not in _SIDES:
            raise ValueError(f"circuit_loop side must be one of {_SIDES}")
        out[side].append((kind, opts))
    return out


@_drawing_api(
    "parts",
    purpose="矩形电路回路：把 circuit_symbol 元件按边放在矩形四边，自动正交布线（直角转角、无手算坐标），可画电流方向箭头与节点。",
    returns="Geometry（端口 tl/tr/bl/br 为四角；每个元件的 <kind>（重名时 <kind>2…）为元件中心，<kind>.a/<kind>.b 为两端；四边/center）",
    semantics=(
        'elements=[("battery", "left"), ("switch", "top"), ("resistor", "right"), ("inductor", "bottom")]，每项可加第三个 dict 传 circuit_symbol 参数（name/value/deflect…），'
        '或用 {"kind":…, "side":…, "name":…}；只给 kind 列表时按 左→上→右→下 依次放。同一边多个元件等距排开。',
        'width/height 为回路导线矩形尺寸；current="cw"/"ccw" 在空着的导线段上画红色电流箭头（标 I）；元件文字始终正立、写在回路外侧。',
        "junctions=[(side, t)] 在边上 t∈(0,1) 处画实心节点并给端口 j0、j1…（接并联支路时用 d.line 连到这些端口）。RL/RC 电路：circuit_loop(…) + 旁边配 sample_function 画增长/衰减曲线。",
    ),
    example='d.place(circuit_loop(300, 180, [("battery", "left", {"name": "ε"}), ("switch", "top", {"name": "S"}), '
    '("resistor", "right", {"name": "R"}), ("inductor", "bottom", {"name": "L"})], current="cw"), at=(480, 270), key="rl")',
    rank=22,
)
def circuit_loop(
    width,
    height,
    elements,
    *,
    current=None,
    symbol_length=None,
    junctions=(),
    stroke=_WIRE,
    stroke_width=1.8,
    current_color=_CURRENT,
    label_current="I",
    font_size=13,
    style="rich",
):
    _finite(width, height)
    _style(style)
    if current not in (None, "cw", "ccw"):
        raise ValueError('current must be None, "cw" or "ccw"')
    W, H = float(width), float(height)
    sides = _loop_layout(elements)
    corners = {"tl": (0, 0), "tr": (W, 0), "br": (W, H), "bl": (0, H)}
    # clockwise run of each side (start, end) and its outward normal
    runs = {
        "top": ((0, 0), (W, 0), (0, -1)),
        "right": ((W, 0), (W, H), (1, 0)),
        "bottom": ((W, H), (0, H), (0, 1)),
        "left": ((0, H), (0, 0), (-1, 0)),
    }
    holder = _el("g")
    holder.append(
        _el("path", d=_poly([(0, 0), (W, 0), (W, H), (0, H)], True), fill="none", stroke="none", data_outline="1")
    )
    boxes = [Box(-stroke_width, -stroke_width, W + 2 * stroke_width, H + 2 * stroke_width)]
    ports = dict(corners)
    wires, free = [], []
    seen = {}
    for side in _SIDES:
        (sx, sy), (ex, ey), (nx, ny) = runs[side]
        span = math.hypot(ex - sx, ey - sy)
        items = sides[side]
        n = len(items)
        L = symbol_length or min(90.0, span / (n + 0.6)) if n else 0
        cuts = []
        for i, (kind, opts) in enumerate(items):
            t = (i + 0.5) / n
            cx, cy = sx + (ex - sx) * t, sy + (ey - sy) * t
            ux, uy = (ex - sx) / span, (ey - sy) / span
            # symbols run left→right / top→bottom so their own labels (above the body) end up outside the loop
            if side in ("top", "bottom"):
                a, b = (cx - L / 2, cy), (cx + L / 2, cy)
            else:
                a, b = (cx, cy - L / 2), (cx, cy + L / 2)
            opts = dict(opts)
            name, value = opts.pop("name", None), opts.pop("value", None)
            g = circuit_symbol(kind, length=L, stroke=stroke, stroke_width=stroke_width, font_size=font_size, **opts)
            _place_on(holder, boxes, g, a, b, kind)
            _side_labels(holder, boxes, side, (cx, cy), g, name, value, font_size, stroke)
            k = kind if kind not in seen else f"{kind}{seen[kind] + 1}"
            seen[kind] = seen.get(kind, 0) + 1
            ports[k] = (cx, cy)
            ports[f"{k}.a"] = a
            ports[f"{k}.b"] = b
            ta = ((a[0] - sx) * ux + (a[1] - sy) * uy) / span
            tb = ((b[0] - sx) * ux + (b[1] - sy) * uy) / span
            cuts.append((min(ta, tb), max(ta, tb)))
        # wire pieces between symbols (clockwise parameter along the side)
        t0 = 0.0
        for lo, hi in sorted(cuts) + [(1.0, 1.0)]:
            if lo - t0 > 1e-6:
                p = (sx + (ex - sx) * t0, sy + (ey - sy) * t0)
                q = (sx + (ex - sx) * lo, sy + (ey - sy) * lo)
                wires.append((p, q))
                free.append((side, p, q))
            t0 = max(t0, hi)
    d = " ".join(f"M{fmt(p[0])} {fmt(p[1])} L{fmt(q[0])} {fmt(q[1])}" for p, q in wires)
    holder.insert(
        1,
        _el(
            "path",
            d=d,
            fill="none",
            stroke=stroke,
            stroke_width=stroke_width,
            stroke_linecap="square",
            stroke_linejoin="miter",
        ),
    )
    for i, (side, t) in enumerate(junctions):
        (sx, sy), (ex, ey), _ = runs[side]
        p = (sx + (ex - sx) * t, sy + (ey - sy) * t)
        holder.append(_el("circle", cx=p[0], cy=p[1], r=stroke_width * 1.9, fill=stroke))
        ports[f"j{i}"] = p
    if current:
        sg = 1 if current == "cw" else -1
        best = {}
        for side, p, q in free:  # longest free piece on each side carries an arrow
            ln = math.hypot(q[0] - p[0], q[1] - p[1])
            if ln > 34 and ln > best.get(side, (0,))[0]:
                best[side] = (ln, p, q)
        for k, (side, (ln, p, q)) in enumerate(sorted(best.items(), key=lambda kv: _SIDES.index(kv[0]))):
            mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
            dx, dy = (q[0] - p[0]) / ln * sg, (q[1] - p[1]) / ln * sg
            holder.append(_head(mx + dx * 6, my + dy * 6, dx, dy, 10, current_color))
            if k == 0 and label_current:
                nx, ny = runs[side][2]
                lx, ly = mx - nx * 12, my - ny * 12 + font_size * 0.35
                el, b = _txt(
                    lx,
                    ly,
                    label_current,
                    font_size,
                    fill=current_color,
                    italic=True,
                    weight="bold",
                    anchor="middle" if nx == 0 else ("start" if nx < 0 else "end"),
                )
                holder.append(el)
                boxes.append(b)
    return _finish(holder, None, _union(boxes), **ports)


def _side_labels(holder, boxes, side, c, g, name, value, fs, stroke):
    """Upright name/value outside the loop for vertical or bottom symbols."""
    body = max(-g.bounds.y, g.bounds.y + g.bounds.height)  # half-thickness of the symbol across the wire
    cx, cy = c
    lines = [(t, f, col) for t, f, col in ((name, fs, stroke), (value, fs * 0.92, _mix(stroke, "#FFFFFF", 0.25))) if t]
    if not lines:
        return
    if side in ("left", "right"):
        x = cx + (-(body + 6) if side == "left" else body + 6)
        anchor = "end" if side == "left" else "start"
        y = cy - (len(lines) - 1) * fs * 0.6 + fs * 0.36
        for t, f, col in lines:
            el, b = _txt(x, y, t, f, fill=col, anchor=anchor, italic=(t == name))
            holder.append(el)
            boxes.append(b)
            y += fs * 1.2
    elif side == "top":
        y = cy - body - 5 - (len(lines) - 1) * fs * 1.15
        for t, f, col in lines:
            el, b = _txt(cx, y, t, f, fill=col, italic=(t == name))
            holder.append(el)
            boxes.append(b)
            y += fs * 1.15
    else:
        y = cy + body + fs * 1.05
        for t, f, col in lines:
            el, b = _txt(cx, y, t, f, fill=col, italic=(t == name))
            holder.append(el)
            boxes.append(b)
            y += fs * 1.15


@_drawing_api(
    "parts",
    purpose="导轨 + 导体棒（电磁感应经典图）：两根平行金属导轨、可滑动的粗导体棒（接触点）、速度箭头 v、左端负载（电阻/电流计/灯），可叠 ⊗/⊙ 磁场与感应电流箭头。",
    returns="Geometry（端口 rod_top/rod_bottom 为棒与导轨接触点，rod 为棒中点，load 为负载中心，rail_top_end/rail_bottom_end 为导轨右端，四边/center）",
    semantics=(
        'length 为导轨长、gap 为两轨间距；rod_at∈(0,1) 为棒在导轨上的位置；velocity="right"/"left"/None 画速度箭头 v（标在棒外侧，不压磁场标记）。',
        'load="resistor"/"galvanometer"/"lamp"/None（None 时左端直接短接），load_name 写标号（默认 R/G）；field="in"/"out" 铺满导轨围成的区域并上下各外扩一行（棒夹在两列之间、I 标在两行之间，只在棒/导轨/负载/箭头旁留约半格间隙），B 图例在网格右上外侧；field_spacing 调密度。',
        'current="cw"/"ccw" 画回路感应电流箭头（棒上与导轨上）并标 I；方向由作者按楞次定律给出（向里磁场、棒右移时为 "ccw"）。可另用 d.callout 标 F安 等。',
    ),
    example='d.place(rails_rod(420, 160, rod_at=0.62, velocity="right", load="resistor", field="in", current="ccw"), at=(480, 270), key="rr")',
    rank=23,
)
def rails_rod(
    length=420,
    gap=160,
    *,
    rod_at=0.6,
    velocity="right",
    load="resistor",
    load_name=None,
    current=None,
    field="in",
    field_spacing=40,
    rail_color="#6F7782",
    rod_color=_COPPER,
    current_color=_CURRENT,
    field_color=_FIELD,
    font_size=15,
    style="rich",
):
    _finite(length, gap, rod_at)
    rich = _style(style)
    if velocity not in (None, "right", "left"):
        raise ValueError('velocity must be "right", "left" or None')
    if load not in (None, "resistor", "galvanometer", "lamp", "resistor_iec"):
        raise ValueError("load must be resistor, galvanometer, lamp or None")
    if field not in (None, "in", "out"):
        raise ValueError('field must be "in", "out" or None')
    if current not in (None, "cw", "ccw"):
        raise ValueError('current must be None, "cw" or "ccw"')
    Lr, G = float(length), float(gap)
    rod_at = min(0.92, max(0.12, rod_at))
    holder, defs = _start(rich)
    rail_w = 5.0
    sp = float(field_spacing)
    k = max(2, 2 * round(G / sp / 2))  # even row count: the rod midpoint and the I label sit between rows
    gy = G / k
    over = gy - 4 if field else 26.0  # rod overhang beyond the rails (reaches the field margin row)
    xr = Lr * rod_at
    boxes = [Box(0, -rail_w, Lr, G + 2 * rail_w)]
    holder.append(
        _el("path", d=_poly([(0, 0), (Lr, 0), (Lr, G), (0, G)], True), fill="none", stroke="none", data_outline="1")
    )
    sym_len = min(G * 0.7, 100.0)
    kind = "galvanometer" if load == "galvanometer" else load
    rw = 9.0
    vy = -over - 10  # velocity arrow just above the rod tip, outside the field region
    sgc = 1 if current == "cw" else -1  # cw: down the rod (right side of the loop)
    r = max(4.5, min(8.0, sp * 0.16))
    clear = 2.5  # gap between a mark's ring and any drawn object
    half = min(9.0, gy / 2 - r - clear - 0.3) if field else 9.0  # I arrow/label fit between two mark rows
    fs_i = min(font_size, 2 * half / 1.1)
    i_arrow = Box(xr + rw / 2 + 2, G / 2 - half, 11, 2 * half)
    i_label = (i_arrow.x + i_arrow.width + 2 + fs_i * 0.35, G / 2)
    if field:
        # region = rail-bounded area + one row above and below (uniform half-cell margin all round)
        hw_load = circuit_symbol(kind, length=sym_len).bounds.height / 2 if load else 1.5
        xl = hw_load  # columns start at the load's edge so no column collides with it
        # rod sits midway between two columns; the I label sits between rows, so no mark has to be dropped
        nl, nr = max(1, round((xr - xl) / sp)), max(1, round((Lr - xr) / sp))
        xs = [xl + (xr - xl) / nl * (i + 0.5) for i in range(nl)] + [xr + (Lr - xr) / nr * (i + 0.5) for i in range(nr)]
        ys = [gy * (j + 0.5) for j in range(-1, k + 1)]
        obstacles = [
            Box(xr - rw / 2, -over, rw, G + 2 * over),
            Box(-hw_load, G / 2 - sym_len / 2, 2 * hw_load, sym_len),
            Box(-1, 0, 2, G),
        ]
        for y in (0, G):
            obstacles.append(Box(0, y - rail_w / 2, Lr, rail_w))
        if current:
            obstacles += [i_arrow, Box(i_label[0] - fs_i * 0.35, i_label[1] - fs_i * 0.5, fs_i * 0.7, fs_i)]
            obstacles += [Box(xr * 0.5 - 8, y - 7, 16, 14) for y in (0, G)]

        def free(x, y):
            for b in obstacles:
                dx = max(b.x - x, 0, x - b.x - b.width)
                dy = max(b.y - y, 0, y - b.y - b.height)
                if math.hypot(dx, dy) < r + clear:
                    return False
            return True

        pts = [(x, y) for y in ys for x in xs if free(x, y)]
        holder.extend(_marks(pts, field, r, field_color, max(1.0, r * 0.2)))
        boxes.append(Box(0, -gy, Lr, G + 2 * gy))
        # legend right of the top margin row, outside the grid
        _field_label(
            holder, boxes, Lr + 10, -gy / 2 + font_size * 0.36, "B", field, font_size, field_color, anchor="start"
        )
    for y in (0, G):
        holder.append(
            _el(
                "rect",
                x=-2,
                y=y - rail_w / 2,
                width=Lr + 2,
                height=rail_w,
                rx=rail_w / 2,
                fill=_mix(rail_color, "#FFFFFF", 0.35),
                stroke=_mix(rail_color, "#000000", 0.25),
                stroke_width=1,
            )
        )
    if rich:
        defs.append(_linear("rail", [(0, "#FFFFFF", 0.7), (0.5, "#FFFFFF", 0.05), (1, "#000000", 0.2)]))
        look = _look()
        for y in (0, G):
            look.append(
                _el("rect", x=-2, y=y - rail_w / 2, width=Lr + 2, height=rail_w, rx=rail_w / 2, fill="url(#rail)")
            )
        holder.append(look)
    ports = {}
    if load:
        g = circuit_symbol(kind, length=sym_len, stroke=_WIRE, stroke_width=1.8, font_size=font_size - 2)
        top, bot = (0, G / 2 - sym_len / 2), (0, G / 2 + sym_len / 2)
        holder.append(
            _el(
                "path", d=f"M0 0 V{fmt(top[1])} M0 {fmt(bot[1])} V{fmt(G)}", fill="none", stroke=_WIRE, stroke_width=1.8
            )
        )
        _place_on(holder, boxes, g, top, bot, kind)
        nm = load_name if load_name is not None else {"galvanometer": "G", "lamp": "L"}.get(kind, "R")
        if nm:
            hw = max(-g.bounds.y, g.bounds.y + g.bounds.height)
            el, b = _txt(-hw - 6, G / 2 + font_size * 0.36, nm, font_size, fill=_WIRE, anchor="end", italic=True)
            holder.append(el)
            boxes.append(b)
        ports["load"] = (0, G / 2)
    else:
        holder.append(_el("path", d=f"M0 0 V{fmt(G)}", fill="none", stroke=_WIRE, stroke_width=2.2))
        ports["load"] = (0, G / 2)
    # rod: thick copper bar with contact dots
    holder.append(
        _el(
            "rect",
            x=xr - rw / 2,
            y=-over,
            width=rw,
            height=G + 2 * over,
            rx=2.5,
            fill=rod_color,
            stroke=_mix(rod_color, "#000000", 0.35),
            stroke_width=1.1,
        )
    )
    if rich:
        defs.append(_linear("rod", [(0, "#FFFFFF", 0.5), (0.45, "#FFFFFF", 0.05), (1, "#000000", 0.25)], x2=1, y2=0))
        look = _look()
        look.append(_el("rect", x=xr - rw / 2, y=-over, width=rw, height=G + 2 * over, rx=2.5, fill="url(#rod)"))
        holder.append(look)
    for y in (0, G):
        holder.append(_el("circle", cx=xr, cy=y, r=3.4, fill="#FFFFFF", stroke=_WIRE, stroke_width=1.4))
    boxes.append(Box(xr - rw / 2, -over, rw, G + 2 * over))
    if velocity:
        sg = 1 if velocity == "right" else -1
        _arrow(holder, boxes, xr, vy, xr + sg * 58, vy, _WIRE, 2.2, 11)
        el, b = _txt(
            xr + sg * 64,
            vy + font_size * 0.36,
            "v",
            font_size + 1,
            fill=_WIRE,
            anchor="start" if sg > 0 else "end",
            italic=True,
            weight="bold",
        )
        holder.append(el)
        boxes.append(b)
    if current:
        cc = current_color
        ax = i_arrow.x + i_arrow.width / 2
        holder.append(
            _el(
                "path",
                d=f"M{fmt(ax)} {fmt(G / 2 - sgc * half)} V{fmt(G / 2 + sgc * (half - 8))}",
                fill="none",
                stroke=cc,
                stroke_width=2.2,
                stroke_linecap="round",
            )
        )
        holder.append(_head(ax, G / 2 + sgc * half, 0, sgc, 10, cc))
        el, b = _centered_text(i_label[0], i_label[1], "I", fs_i, fill=cc, italic=True, weight="bold")
        holder.append(el)
        boxes += [b, i_arrow]
        for y, dx in ((0, sgc), (G, -sgc)):  # drawn on the rails themselves
            holder.append(_head(xr * 0.5 + dx * 8, y, dx, 0, 14, cc))
    ports.update(rod_top=(xr, 0), rod_bottom=(xr, G), rod=(xr, G / 2), rail_top_end=(Lr, 0), rail_bottom_end=(Lr, G))
    return _finish(holder, defs, _union(boxes), **ports)
