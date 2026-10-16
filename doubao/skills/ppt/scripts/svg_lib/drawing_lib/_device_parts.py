"""Materials / energy device parts drawn like textbook and journal figures."""

from __future__ import annotations

import math
import random

from ..atomize_svg_to_slide._geometry import fmt
from ._bio_parts import _el, _look, _mix, _circ
from ._geometry import Box, _finite, _union, label
from ._help import _drawing_api
from ._parts import _INK, _finish, _head, _linear, _start

_TEXTURES = ("grain", "porous", "metal", "glass", "catalyst", "fiber", "flowfield", "membrane", None)


def _rich(style):
    if style not in ("rich", "flat"):
        raise ValueError('style must be "rich" or "flat"')
    return style == "rich"


def _dark(color):
    c = str(color).lstrip("#")
    if len(c) != 6:
        return False
    try:
        r, g, b = (int(c[k : k + 2], 16) for k in (0, 2, 4))
    except ValueError:
        return False
    return 0.299 * r + 0.587 * g + 0.114 * b < 140


def _text(x, y, content, fs, *, fill=_INK, anchor="middle", weight=None, rotate=None):
    """Native text with baseline at y; returns (element, box)."""
    t = _el(
        "text",
        x=x,
        y=y,
        font_size=fs,
        text_anchor=anchor,
        fill=fill,
        font_weight=weight,
        transform=f"rotate({fmt(rotate)} {fmt(x)} {fmt(y)})" if rotate else None,
    )
    t.text = str(content)
    b = label(str(content), font_size=fs, text_anchor=anchor, font_weight=weight or "normal").bounds
    if rotate in (-90, 270):
        return t, Box(x - fs, y - (b.x + b.width), fs * 1.25, b.width)
    return t, Box(x + b.x, y - fs + b.y, b.width, b.height)


def _spot(gid, color):
    g = _el("radialGradient", id=gid, cx="50%", cy="50%", r="55%", fx="34%", fy="30%")
    g.append(_el("stop", offset=0, stop_color="#FFFFFF", stop_opacity=0.8))
    g.append(_el("stop", offset=0.5, stop_color="#FFFFFF", stop_opacity=0.1))
    g.append(_el("stop", offset=1, stop_color=_mix(color, "#000000", 0.45), stop_opacity=0.35))
    return g


def _texture(look, defs, kind, x, y, w, h, fill, idx, rnd, face=1):
    edge = _mix(fill, "#000000", 0.45)
    if kind == "metal":
        gid = f"ls_metal{idx}"
        defs.append(
            _linear(gid, [(0, "#FFFFFF", 0.55), (0.35, "#FFFFFF", 0.08), (0.7, "#000000", 0.06), (1, "#000000", 0.22)])
        )
        look.append(_el("rect", x=x, y=y, width=w, height=h, fill=f"url(#{gid})"))
        if h >= 6:
            look.append(
                _el(
                    "path",
                    d=f"M{fmt(x + 2)} {fmt(y + h * 0.3)} H{fmt(x + w - 2)}",
                    stroke="#FFFFFF",
                    stroke_width=max(0.8, h * 0.1),
                    stroke_opacity=0.5,
                    fill="none",
                )
            )
    elif kind == "glass":
        gid = f"ls_glass{idx}"
        defs.append(
            _linear(
                gid,
                [(0, "#FFFFFF", 0.45), (0.45, "#FFFFFF", 0.05), (0.55, "#FFFFFF", 0.18), (1, "#FFFFFF", 0.0)],
                x2=1,
                y2=1,
            )
        )
        look.append(_el("rect", x=x, y=y, width=w, height=h, fill=f"url(#{gid})"))
        look.append(
            _el(
                "path",
                d=f"M{fmt(x)} {fmt(y + 0.8)} H{fmt(x + w)}",
                stroke="#FFFFFF",
                stroke_width=1.2,
                stroke_opacity=0.8,
                fill="none",
            )
        )
    elif kind == "grain":
        # polycrystalline columns: jittered grain boundaries + alternating shading
        n = max(3, int(w / max(14.0, h * 0.9)))
        xs = sorted([x] + [x + w * (k + rnd.uniform(-0.3, 0.3)) / n for k in range(1, n)] + [x + w])
        for k in range(len(xs) - 1):
            if k % 2:
                look.append(
                    _el("rect", x=xs[k], y=y, width=xs[k + 1] - xs[k], height=h, fill="#FFFFFF", fill_opacity=0.1)
                )
            elif k % 3 == 0:
                look.append(
                    _el("rect", x=xs[k], y=y, width=xs[k + 1] - xs[k], height=h, fill="#000000", fill_opacity=0.08)
                )
        segs = []
        for bx in xs[1:-1]:
            pts, steps = [], max(2, int(h / 7))
            for s in range(steps + 1):
                pts.append((bx + rnd.uniform(-2.5, 2.5), y + h * s / steps))
            segs.append("M" + " L".join(f"{fmt(px)} {fmt(py)}" for px, py in pts))
            if h > 18 and rnd.random() < 0.5:
                yy = y + h * rnd.uniform(0.3, 0.7)
                segs.append(f"M{fmt(bx)} {fmt(yy)} L{fmt(bx + rnd.uniform(6, 14))} {fmt(yy + rnd.uniform(-4, 4))}")
        look.append(_el("path", d=" ".join(segs), stroke=edge, stroke_width=0.8, stroke_opacity=0.55, fill="none"))
        gid = f"ls_gr{idx}"
        defs.append(_linear(gid, [(0, "#FFFFFF", 0.22), (1, "#000000", 0.12)]))
        look.append(_el("rect", x=x, y=y, width=w, height=h, fill=f"url(#{gid})"))
    elif kind == "catalyst":
        _catalyst(look, x, y, w, h, fill, rnd)
    elif kind == "fiber":
        _fibers(look, x, y, w, h, fill, rnd)
    elif kind == "flowfield":
        _flowfield(look, x, y, w, h, fill, face)
    elif kind == "membrane":
        _ionomer(look, x, y, w, h, fill, rnd)
    elif kind == "porous":
        count = max(6, int(w * h / 90))
        for _ in range(count):
            r = rnd.uniform(1.0, min(3.2, h * 0.22))
            cx, cy = rnd.uniform(x + r, x + w - r), rnd.uniform(y + r, y + h - r)
            look.append(_el("ellipse", cx=cx, cy=cy, rx=r * 1.2, ry=r, fill=edge, fill_opacity=0.35))
            look.append(
                _el(
                    "ellipse",
                    cx=cx + r * 0.3,
                    cy=cy + r * 0.35,
                    rx=r * 0.7,
                    ry=r * 0.45,
                    fill="#FFFFFF",
                    fill_opacity=0.25,
                )
            )


def _catalyst(look, x, y, w, h, fill, rnd):
    """Pt/C catalyst layer: packed carbon-black spheres decorated with Pt nanodots, wrapped in a thin ionomer film."""
    r = max(3.0, min(7.0, h * 0.3))
    carbon, pt, ion = "#454A54", "#F3F4F6", "#6FC2C8"
    spheres = []
    rows = max(1, int((h - 1) / (r * 1.7)))
    for j in range(rows):
        cy = y + h * (j + 0.5) / rows
        cx = x + r + (r * 0.9 if j % 2 else 0) + rnd.uniform(0, r * 0.4)
        while cx < x + w - r:
            rr = r * rnd.uniform(0.8, 1.0)
            spheres.append((cx, cy + rnd.uniform(-r * 0.2, r * 0.2), rr))
            cx += r * rnd.uniform(1.75, 2.15)
    film = " ".join(_circ(cx, cy, rr + max(0.8, r * 0.22)) for cx, cy, rr in spheres)
    look.append(_el("path", d=film, fill=ion, fill_opacity=0.55, stroke="none"))
    look.append(
        _el(
            "path",
            d=" ".join(_circ(cx, cy, rr) for cx, cy, rr in spheres),
            fill=carbon,
            stroke=_mix(carbon, "#000000", 0.4),
            stroke_width=0.4,
        )
    )
    look.append(
        _el(
            "path",
            d=" ".join(_circ(cx - rr * 0.32, cy - rr * 0.34, rr * 0.3) for cx, cy, rr in spheres),
            fill="#FFFFFF",
            fill_opacity=0.18,
        )
    )
    dots = []
    for cx, cy, rr in spheres:
        for k in range(5):
            a = k * 2 * math.pi / 5 + rnd.uniform(0, 1.0)
            q = rr * rnd.uniform(0.3, 0.8)
            dots.append(_circ(cx + q * math.cos(a), cy + q * math.sin(a), max(0.6, r * 0.15)))
    look.append(_el("path", d=" ".join(dots), fill=pt, stroke="#8A8F98", stroke_width=0.3))


def _fibers(look, x, y, w, h, fill, rnd):
    """Carbon-paper GDL: overlapping straight carbon fibres at shallow angles (plus a few cross-section ends)."""
    dark = _mix(fill, "#FFFFFF", 0.3) if _dark(fill) else _mix(fill, "#000000", 0.5)
    edge = _mix(fill, "#000000", 0.5)
    fw = max(1.8, min(3.6, h * 0.1))
    segs, shine, ends = [], [], []
    n = max(6, int(w * h / 520))
    for _ in range(n):
        cy = rnd.uniform(y + fw, y + h - fw)
        ang = rnd.uniform(-0.22, 0.22)
        L = rnd.uniform(w * 0.25, w * 0.6)
        cx = rnd.uniform(x, x + w)
        x0, x1 = max(x + 1, cx - L / 2), min(x + w - 1, cx + L / 2)
        y0 = min(max(cy - (cx - x0) * math.tan(ang), y + fw), y + h - fw)
        y1 = min(max(cy + (x1 - cx) * math.tan(ang), y + fw), y + h - fw)
        segs.append(f"M{fmt(x0)} {fmt(y0)} L{fmt(x1)} {fmt(y1)}")
        shine.append(f"M{fmt(x0)} {fmt(y0 - fw * 0.25)} L{fmt(x1)} {fmt(y1 - fw * 0.25)}")
    for _ in range(max(3, int(w * h / 900))):
        ends.append(_circ(rnd.uniform(x + fw, x + w - fw), rnd.uniform(y + fw, y + h - fw), fw * 0.75))
    look.append(_el("path", d=" ".join(segs), fill="none", stroke=edge, stroke_width=fw + 1, stroke_linecap="round"))
    look.append(_el("path", d=" ".join(segs), fill="none", stroke=dark, stroke_width=fw, stroke_linecap="round"))
    look.append(
        _el(
            "path",
            d=" ".join(shine),
            fill="none",
            stroke="#FFFFFF",
            stroke_width=fw * 0.3,
            stroke_opacity=0.35,
            stroke_linecap="round",
        )
    )
    look.append(_el("path", d=" ".join(ends), fill=dark, stroke=edge, stroke_width=0.6))


def _flowfield(look, x, y, w, h, fill, face):
    """Bipolar-plate flow field: ribs and gas channels open toward the MEA (face=+1 opens downward, -1 upward)."""
    n = max(3, int(w / max(18.0, h * 1.3)))
    pitch = w / n
    cw, ch = pitch * 0.55, h * 0.66
    gas = "#E7F2FB"
    ds, sh = [], []
    for k in range(n):
        cx = x + pitch * (k + 0.5)
        x0 = cx - cw / 2
        r = min(cw * 0.25, ch * 0.3)
        if face > 0:  # channel cut into the lower face
            yb = y + h
            ds.append(
                f"M{fmt(x0)} {fmt(yb)} V{fmt(yb - ch + r)} Q{fmt(x0)} {fmt(yb - ch)} {fmt(x0 + r)} {fmt(yb - ch)} "
                f"H{fmt(x0 + cw - r)} Q{fmt(x0 + cw)} {fmt(yb - ch)} {fmt(x0 + cw)} {fmt(yb - ch + r)} V{fmt(yb)} Z"
            )
            sh.append(f"M{fmt(x0 + 1)} {fmt(yb - ch + r)} V{fmt(yb)}")
        else:
            yt = y
            ds.append(
                f"M{fmt(x0)} {fmt(yt)} V{fmt(yt + ch - r)} Q{fmt(x0)} {fmt(yt + ch)} {fmt(x0 + r)} {fmt(yt + ch)} "
                f"H{fmt(x0 + cw - r)} Q{fmt(x0 + cw)} {fmt(yt + ch)} {fmt(x0 + cw)} {fmt(yt + ch - r)} V{fmt(yt)} Z"
            )
            sh.append(f"M{fmt(x0 + 1)} {fmt(yt)} V{fmt(yt + ch - r)}")
    look.append(_el("path", d=" ".join(ds), fill=gas, stroke=_mix(fill, "#000000", 0.4), stroke_width=0.8))
    look.append(_el("path", d=" ".join(sh), fill="none", stroke="#000000", stroke_opacity=0.12, stroke_width=1.6))
    dots = []
    for k in range(n):
        cx = x + pitch * (k + 0.5)
        cy = (y + h - ch / 2) if face > 0 else (y + ch / 2)
        dots.append(_circ(cx, cy, min(cw, ch) * 0.12))
    look.append(_el("path", d=" ".join(dots), fill="#7FA9CF"))


def _ionomer(look, x, y, w, h, fill, rnd):
    """PFSA membrane: hydrophobic backbone matrix with percolating hydrophilic water/sulfonate cluster channels."""
    water = "#6FB7E3"
    clusters, links, so3 = [], [], []
    rc = max(1.6, min(3.6, h * 0.1))
    pts = []
    n = max(8, int(w * h / 120))
    for _ in range(n):
        px, py = rnd.uniform(x + rc * 1.5, x + w - rc * 1.5), rnd.uniform(y + rc * 1.5, y + h - rc * 1.5)
        if all(math.dist((px, py), q) > rc * 2.6 for q in pts):
            pts.append((px, py))
    for px, py in pts:
        rr = rc * rnd.uniform(0.75, 1.15)
        clusters.append(_circ(px, py, rr))
        for k in range(5):
            a = k * 2 * math.pi / 5 + rnd.uniform(0, 0.5)
            so3.append(_circ(px + rr * math.cos(a), py + rr * math.sin(a), max(0.45, rc * 0.2)))
    for i, p in enumerate(pts):
        near = sorted(pts[:i] + pts[i + 1 :], key=lambda q: math.dist(p, q))[:1]
        for q in near:
            if math.dist(p, q) < rc * 6:
                mx, my = (p[0] + q[0]) / 2 + rnd.uniform(-rc, rc), (p[1] + q[1]) / 2 + rnd.uniform(-rc, rc)
                links.append(f"M{fmt(p[0])} {fmt(p[1])} Q{fmt(mx)} {fmt(my)} {fmt(q[0])} {fmt(q[1])}")
    look.append(
        _el(
            "path",
            d=" ".join(links),
            fill="none",
            stroke=water,
            stroke_width=rc * 0.55,
            stroke_opacity=0.6,
            stroke_linecap="round",
        )
    )
    look.append(_el("path", d=" ".join(clusters), fill=water, fill_opacity=0.85, stroke="none"))
    look.append(_el("path", d=" ".join(so3), fill="#E8C547", stroke="none"))


@_drawing_api(
    "parts",
    purpose="层状/多层器件截面（太阳能电池、薄膜叠层、电极）：教材/期刊风格，层纹理、侧引标签、厚度标尺、入射光。",
    returns="Geometry（原点在中心；每层端口 layer_i 位于该层右侧中点（侧引标签则位于标签末端），layer_i_mid 层中心，layer_i_left 左缘中点）",
    semantics=(
        "layers 为 [(名称, 厚度, 填充色)] 或 [(名称, 厚度, 填充色, 纹理)] 自上而下；纹理取 grain（多晶晶粒）/porous（多孔）/metal（金属光泽）/glass（玻璃高光）/None；texture 为未单独指定时的默认纹理。",
        "燃料电池/电解池 MEA 纹理：catalyst（碳球载 Pt 纳米点 + 离聚物膜）/fiber（碳纸纤维 GDL）/flowfield（双极板脊-流道，开口朝叠层中心）/membrane（离聚物 + 亲水簇通道）；这些层的名称一律侧引，避免压在纹理上。",
        "层厚足够时标签写在层内左侧；太薄的层自动把标签放到叠层右侧并画细引线（标签不会丢失）。",
        'scale_bar=True 或文字（如 "500 nm"）时在左侧画厚度标尺；light=True 在顶部画入射阳光箭头（hν）。',
        'style="rich" 加纹理与光泽（局部 SVG）；"flat" 全部为原生纯色形状。',
    ),
    example='d.place(layer_stack([("Ag", 8, "#B8BEC6", "metal"), ("Spiro", 22, "#C8B6E2"), ("钙钛矿", 46, "#3B3A55", "grain"), '
    '("TiO₂", 6, "#E8E8E8", "porous"), ("FTO 玻璃", 30, "#CFE6F5", "glass")], width=360, light=True), at=(400, 270), key="stack")',
    rank=6,
)
def layer_stack(
    layers,
    *,
    width=320,
    font_size=13,
    label_fill="#1E191C",
    stroke="#FFFFFF",
    texture=None,
    scale_bar=False,
    light=False,
    style="rich",
    seed=3,
):
    _finite(width, font_size)
    rich = _rich(style)
    rnd = random.Random(seed)
    holder, defs = _start()
    specs = []
    y = 0.0
    for item in layers:
        name, thick, fill = item[0], float(item[1]), item[2]
        tex = item[3] if len(item) > 3 else texture
        if tex not in _TEXTURES:
            raise ValueError(f"layer texture must be one of {_TEXTURES}")
        specs.append((name, y, thick, fill, tex))
        y += thick
    total = y
    frame = "#5E6773"
    holder.append(
        _el(
            "rect",
            x=0,
            y=0,
            width=width,
            height=total,
            fill=specs[0][3] if specs else "#FFFFFF",
            stroke="none",
            data_outline="1",
        )
    )
    boxes = [Box(-0.5, -0.5, width + 1, total + 1)]
    for name, y0, thick, fill, _ in specs:
        holder.append(_el("rect", x=0, y=y0, width=width, height=thick, fill=fill, stroke=stroke, stroke_width=0.8))
    if rich:
        look = _look()
        for i, (name, y0, thick, fill, tex) in enumerate(specs):
            if tex:
                _texture(
                    look, defs, tex, 0, y0, width, thick, fill, i, rnd, face=1 if y0 + thick / 2 < total / 2 else -1
                )
        defs.append(
            _linear(
                "ls_side",
                [(0, "#000000", 0.1), (0.06, "#000000", 0.0), (0.94, "#000000", 0.0), (1, "#000000", 0.14)],
                x2=1,
                y2=0,
            )
        )
        look.append(_el("rect", x=0, y=0, width=width, height=total, fill="url(#ls_side)"))
        holder.append(look)
    holder.append(_el("rect", x=0, y=0, width=width, height=total, fill="none", stroke=frame, stroke_width=1))

    # labels: inside when the layer is thick enough, otherwise to the right with a leader
    ports, side = {}, []
    busy = ("catalyst", "fiber", "flowfield", "membrane") if rich else ()
    for i, (name, y0, thick, fill, tex) in enumerate(specs):
        mid = y0 + thick / 2
        ports[f"layer_{i}"] = (width, mid)
        ports[f"layer_{i}_mid"] = (width / 2, mid)
        ports[f"layer_{i}_left"] = (0.0, mid)
        if not name:
            continue
        if thick >= font_size * 1.1 and tex not in busy:
            t, b = _text(
                10,
                mid + font_size * 0.36,
                name,
                font_size,
                fill="#FFFFFF" if _dark(fill) else label_fill,
                anchor="start",
            )
            holder.append(t)
        else:
            side.append([i, mid, mid])
    gap = font_size * 1.3
    for k in range(1, len(side)):  # spread side labels downward, then shift up if needed
        side[k][2] = max(side[k][2], side[k - 1][2] + gap)
    if side:
        over = side[-1][2] - max(total, side[-1][1])
        if over > 0:
            for s in side:
                s[2] -= over
            for k in range(len(side) - 2, -1, -1):
                side[k][2] = min(side[k][2], side[k + 1][2] - gap)
    lx = width + font_size * 1.6
    segs = []
    for i, mid, ly in side:
        name = specs[i][0]
        segs.append(f"M{fmt(width - min(18, width * 0.06))} {fmt(mid)} H{fmt(width + 6)} L{fmt(lx - 4)} {fmt(ly)}")
        holder.append(_el("circle", cx=width - min(18, width * 0.06), cy=mid, r=1.6, fill=_INK))
        t, b = _text(lx, ly + font_size * 0.36, name, font_size, fill=label_fill, anchor="start")
        holder.append(t)
        boxes.append(b)
        ports[f"layer_{i}"] = (b.x + b.width, ly)
    if segs:
        holder.append(_el("path", d=" ".join(segs), fill="none", stroke=_INK, stroke_width=0.8))

    if scale_bar:
        sx = -font_size * 0.9
        tick = 4
        d = [f"M{fmt(sx)} 0 V{fmt(total)}"]
        for _, y0, thick, _, _ in specs:
            d.append(f"M{fmt(sx - tick)} {fmt(y0)} H{fmt(sx + tick)}")
        d.append(f"M{fmt(sx - tick)} {fmt(total)} H{fmt(sx + tick)}")
        holder.append(_el("path", d=" ".join(d), fill="none", stroke=_INK, stroke_width=1))
        boxes.append(Box(sx - tick, 0, 2 * tick, total))
        text = scale_bar if isinstance(scale_bar, str) else "厚度"
        fs = font_size * 0.9
        t, b = _text(sx - tick - 4, total / 2, text, fs, anchor="middle", rotate=-90)
        holder.append(t)
        boxes.append(b)

    if light:
        sun = "#E89B0C"
        n = 4 if width > 200 else 3
        L = max(26.0, font_size * 2.6)
        segs = []
        for k in range(n):
            tx = width * (k + 0.7) / (n + 0.4)
            ty = -4
            x0, y0 = tx - L * 0.45, ty - L
            segs.append(f"M{fmt(x0)} {fmt(y0)} L{fmt(tx - L * 0.45 * 0.2)} {fmt(ty - L * 0.2)}")
            holder.append(_head(tx, ty, L * 0.45, L, 8, sun))
            boxes.append(Box(x0, y0, L * 0.45, L))
        holder.append(_el("path", d=" ".join(segs), fill="none", stroke=sun, stroke_width=2.2, stroke_linecap="round"))
        t, b = _text(
            width * (n - 0.3) / (n + 0.4) + font_size * 0.3,
            -L - 2,
            "hν",
            font_size,
            fill=_mix(sun, "#000000", 0.25),
            anchor="start",
            weight="bold",
        )
        holder.append(t)
        boxes.append(b)
    return _finish(holder, defs, _union(boxes), **ports)


_SECTION_TEXTURES = _TEXTURES + ("polycrystal", "mosaic")
_FEATURES = ("dendrite", "void", "crack", "particle", "flux", "pinhole", "delamination", "whisker", "adsorbate")


def _poly_d(pts, close=True):
    return "M" + " L".join(f"{fmt(x)} {fmt(y)}" for x, y in pts) + (" Z" if close else "")


def _domains(rnd, u0, v0, du, dv, cell):
    """Deterministic Voronoi cells (u, v) tiling one layer rectangle; returns (cells, internal edges)."""
    from ._matter_parts import _voronoi_clip

    nu, nv = max(1, round(du / cell)), max(1, round(dv / cell))
    su, sv = du / nu, dv / nv
    seeds = [
        (u0 + (i + 0.5 + rnd.uniform(-0.38, 0.38)) * su, v0 + (j + 0.5 + rnd.uniform(-0.38, 0.38)) * sv)
        for j in range(nv)
        for i in range(nu)
    ]
    box = [(u0, v0), (u0 + du, v0), (u0 + du, v0 + dv), (u0, v0 + dv)]
    reach = 2.6 * max(su, sv)
    cells = []
    for s in seeds:
        near = [s] + [q for q in seeds if q is not s and abs(q[0] - s[0]) < reach and abs(q[1] - s[1]) < reach]
        cells += _voronoi_clip(near, box)[:1]
    count = {}
    for poly in cells:
        for a, b in zip(poly, poly[1:] + poly[:1]):
            ka, kb = (round(a[0], 2), round(a[1], 2)), (round(b[0], 2), round(b[1], 2))
            if ka != kb:
                k = (min(ka, kb), max(ka, kb))
                count[k] = count.get(k, 0) + 1
    return cells, [k for k, n in count.items() if n == 2]


def _gb_walk(rnd, edges, start, sign, depth, cell):
    """Follow grain-boundary edges from the interface point ``start`` (u, v) for ``depth`` along sign·v."""
    adj = {}
    for a, b in edges:
        adj.setdefault(a, []).append(b)
        adj.setdefault(b, []).append(a)
    roots = [p for p in adj if abs(p[1] - start[1]) < 0.05]
    p = min(roots, key=lambda q: abs(q[0] - start[0])) if roots else None
    if p is None or abs(p[0] - start[0]) > cell:
        return None, None
    path, seen = [p], {p}
    while abs(path[-1][1] - p[1]) < depth:
        cur = path[-1]
        options = [q for q in adj[cur] if q not in seen and sign * (q[1] - cur[1]) > -0.6 * cell]
        if not options:
            break
        q = max(options, key=lambda q: sign * (q[1] - cur[1]) / (math.dist(q, cur) or 1) + rnd.uniform(0, 0.3))
        seen.add(q)
        path.append(q)
    a, b = path[-2:] if len(path) > 1 else (path[0], path[0])
    over = abs(b[1] - p[1]) - depth
    if over > 0 and abs(b[1] - a[1]) > 1e-6:
        t = 1 - over / abs(b[1] - a[1])
        path[-1] = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
    return (path, adj) if len(path) > 1 else (None, None)


def _walk(rnd, x, y, heading, length, steps, jitter):
    pts = [(x, y)]
    for _ in range(steps):
        heading += rnd.uniform(-jitter, jitter)
        x, y = x + length / steps * math.cos(heading), y + length / steps * math.sin(heading)
        pts.append((x, y))
    return pts


def _taper(pts, w0, w1):
    """Closed outline of a polyline whose width shrinks from w0 (start) to w1 (tip)."""
    total = sum(math.dist(a, b) for a, b in zip(pts, pts[1:])) or 1
    left, right, run = [], [], 0.0
    for i, (x, y) in enumerate(pts):
        if i:
            run += math.dist(pts[i - 1], pts[i])
        a, b = pts[max(0, i - 1)], pts[min(len(pts) - 1, i + 1)]
        L = math.dist(a, b) or 1
        nx, ny = -(b[1] - a[1]) / L, (b[0] - a[0]) / L
        w = (w0 + (w1 - w0) * run / total) / 2
        left.append((x + nx * w, y + ny * w))
        right.append((x - nx * w, y - ny * w))
    return left + right[::-1]


def _branches(rnd, trunk, sign, size, adj, cell, v_lo, v_hi):
    """Side branches (and twigs) off a trunk: along neighbouring grain boundaries when adj is given."""
    out = []
    trunk_set = set(trunk)
    for i in range(1, len(trunk) - 1):
        x, y = trunk[i]
        if adj is not None and trunk[i] in adj:
            for q in adj[trunk[i]]:
                if q in trunk_set or sign * (q[1] - y) < -0.5 * cell or rnd.random() < 0.2:
                    continue
                arm, prev = [trunk[i], q], trunk[i]
                for _ in range(rnd.choice((0, 1, 1, 2))):
                    nxt = [
                        r
                        for r in adj.get(arm[-1], ())
                        if r != prev and r not in trunk_set and sign * (r[1] - arm[-1][1]) > 0
                    ]
                    if not nxt:
                        break
                    prev = arm[-1]
                    arm.append(rnd.choice(nxt))
                out.append((i, arm))
        elif rnd.random() < 0.7:
            h = math.atan2(trunk[i + 1][1] - y, trunk[i + 1][0] - x) + rnd.choice((-1, 1)) * rnd.uniform(0.6, 1.0)
            arm = _walk(rnd, x, y, h, size * rnd.uniform(0.22, 0.38) * (1 - i / len(trunk) * 0.5), 3, 0.3)
            out.append((i, arm))
            if rnd.random() < 0.6:
                tx, ty = arm[1]
                out.append((i, _walk(rnd, tx, ty, h + rnd.choice((-1, 1)) * 0.8, size * 0.12, 2, 0.2)))
    return [(i, [(u, min(max(v, v_lo), v_hi)) for u, v in arm]) for i, arm in out]


def _feature(item, n_iface):
    kind, k, at = item[0], int(item[1]), float(item[2])
    rest = list(item[3:])
    opts = rest.pop() if rest and isinstance(rest[-1], dict) else {}
    size = float(rest[0]) if rest and rest[0] is not None else None
    if kind not in _FEATURES:
        raise ValueError(f"feature kind must be one of {_FEATURES}")
    if not 0 <= k < n_iface:
        raise ValueError("feature interface index out of range")
    return kind, k, at, size, opts


@_drawing_api(
    "parts",
    purpose="界面/截面（电极|电解质、异质结、涂层腐蚀、地层、薄膜）：多晶晶界、SEI 马赛克纹理，界面处枝晶/空洞/裂纹/夹杂/离子流。",
    returns="Geometry（原点在中心；端口 layer{i} 层中心、interface{i} 界面中点、dendrite{k}_base/_tip、void{k}、crack{k}_tip/_mouth、pinhole{k}、delamination{k}、particle{k}、flux{k}、whisker{k}_base/_tip、adsorbate{k}）",
    semantics=(
        "layers 同 layer_stack：[(名称, 厚度, 颜色[, 纹理])]；纹理另有 polycrystal（Voronoi 晶粒+晶界）/mosaic（SEI 式 2–3 色纳米畴）。",
        'stack="down" 自上而下叠层（界面水平），"right" 自左向右（Li | SEI | SSE）；length 为沿界面的长度，grain 为晶粒尺寸；层名写在叠层外侧，挤时自动错开加引线。',
        "features 每项 (类型, 界面序号 i, 沿界面位置 0–1[, 尺寸][, {选项}])，界面 i 位于第 i 与 i+1 层之间；尺寸为正伸入后一层、为负伸入前一层。",
        "类型：dendrite 分叉渐细枝晶（可穿过薄层继续生长，多晶层中沿晶界）、void 界面透镜状空洞（尺寸为宽度）、crack 张开型锯齿裂纹（多晶中沿晶界；选项 through=True 贯穿整层、width 口宽）、pinhole 贯穿针孔、delamination 界面分层（尺寸为长度）、"
        'particle 界面夹杂颗粒（尺寸为半径）、flux 穿过界面的箭头（选项 label="Li⁺"、color、dashed=True 画漏电子）、whisker 顶端生长纤维（积碳/纳米线：纤维从表面长出、催化颗粒被顶在顶端，尺寸为长度，选项 r 顶端颗粒半径、tip 颗粒色）、'
        "adsorbate 表面吸附原子单层（尺寸为覆盖段长度，选项 coverage=0–1 覆盖度 θ、r、fill）；选项 fill 改颜色。",
        '纹理与枝晶/空洞明暗在 style="rich" 的局部 SVG 中；晶粒、畴、枝晶、空洞、文字都是原生形状；"flat" 全原生。',
    ),
    example='sec = d.place(interface_section([("Li", 70, "#C3C9D2", "metal"), ("SEI", 16, "#B9A27C", "mosaic"), ("Li₆PS₅Cl", 150, "#E6DCC6", "polycrystal")],\n'
    '    length=220, stack="right", features=[("dendrite", 0, .35, 120), ("void", 0, .7, -40), ("flux", 0, .15, 36, {"label": "Li⁺"})]), at=(300, 220))\n'
    'd.callout("dend", "沿晶界枝晶", sec.port("dendrite0_tip"), at=(480, 120), font_size=14)',
    rank=6,
)
def interface_section(
    layers, *, length=260, stack="down", features=(), grain=26, font_size=13, label_fill="#1E191C", style="rich", seed=7
):
    _finite(length, grain, font_size)
    if stack not in ("down", "right"):
        raise ValueError('stack must be "down" or "right"')
    rich = _rich(style)
    rnd = random.Random(seed)
    L = float(length)
    down = stack == "down"

    def P(u, v):
        return (u, v) if down else (v, u)

    def pd(pts, close=True):
        return _poly_d([P(u, v) for u, v in pts], close)

    def rect(u, v, du, dv, **kw):
        x, y = P(u, v)
        return _el("rect", x=x, y=y, width=du if down else dv, height=dv if down else du, **kw)

    specs, v = [], 0.0
    for item in layers:
        tex = item[3] if len(item) > 3 else None
        if tex not in _SECTION_TEXTURES:
            raise ValueError("layer texture must be grain/porous/metal/glass/polycrystal/mosaic/None")
        specs.append((item[0], v, float(item[1]), item[2], tex))
        v += float(item[1])
    T = v
    holder, defs = _start()
    holder.append(rect(0, 0, L, T, fill=specs[0][3], data_outline="1"))
    for _, v0, th, fill, _ in specs:
        holder.append(rect(0, v0, L, th, fill=fill))

    # native textures: grains / nanodomains as one compound path per tint, boundaries as one path
    gb = {}
    for i, (_, v0, th, fill, tex) in enumerate(specs):
        if tex not in ("polycrystal", "mosaic"):
            continue
        mosaic = tex == "mosaic"
        cell = max(3.0, min(grain * 0.28, th / 2.2)) if mosaic else grain
        cells, edges = _domains(rnd, 0, v0, L, th, cell)
        tints = (
            (fill, _mix(fill, "#FFFFFF", 0.42), _mix(fill, "#000000", 0.2))
            if mosaic
            else (_mix(fill, "#FFFFFF", 0.14), fill, _mix(fill, "#000000", 0.07))
        )
        groups = [[] for _ in tints]
        for poly in cells:
            groups[rnd.choices(range(3), (5, 3, 2) if mosaic else (1, 1, 1))[0]].append(pd(poly))
        for tint, ds in zip(tints, groups):
            if ds:
                holder.append(_el("path", d=" ".join(ds), fill=tint, stroke="none"))
        line = _mix(fill, "#000000", 0.3 if mosaic else 0.42)
        holder.append(
            _el(
                "path",
                d=" ".join(pd(e, False) for e in edges),
                fill="none",
                stroke=line,
                stroke_width=0.45 if mosaic else 0.9,
                stroke_opacity=0.7 if mosaic else None,
                stroke_linejoin="round",
            )
        )
        if not mosaic:
            gb[i] = (edges, cell)
    if rich:
        look = _look()
        inner = _el("g", transform=None if down else "matrix(0 1 1 0 0 0)")
        for i, (_, v0, th, fill, tex) in enumerate(specs):
            if tex in _TEXTURES and tex:
                _texture(inner, defs, tex, 0, v0, L, th, fill, i, rnd)
            elif tex:
                gid = f"is_shade{i}"
                defs.append(_linear(gid, [(0, "#FFFFFF", 0.3), (0.5, "#FFFFFF", 0.0), (1, "#000000", 0.1)]))
                inner.append(_el("rect", x=0, y=v0, width=L, height=th, fill=f"url(#{gid})"))
                if tex == "mosaic":
                    for _ in range(int(L * th / 40)):
                        inner.append(
                            _el(
                                "circle",
                                cx=rnd.uniform(1, L - 1),
                                cy=rnd.uniform(v0 + 1, v0 + th - 1),
                                r=rnd.uniform(0.5, 1.2),
                                fill=_mix(fill, "#000000", 0.45),
                                fill_opacity=0.5,
                            )
                        )
        look.append(inner)
        holder.append(look)
    if len(specs) > 1:
        holder.append(
            _el(
                "path",
                d=" ".join(pd([(0, v0), (L, v0)], False) for _, v0, *_ in specs[1:]),
                fill="none",
                stroke=_mix(specs[0][3], "#000000", 0.55),
                stroke_width=1.1,
            )
        )

    feats = [_feature(f, len(specs) - 1) for f in features]
    ports = {f"layer{i}": P(L / 2, v0 + th / 2) for i, (_, v0, th, _, _) in enumerate(specs)}
    ports.update({f"interface{i}": P(L / 2, specs[i + 1][1]) for i in range(len(specs) - 1)})
    counts, shine, boxes = {}, [], [Box(-0.6, -0.6, (L if down else T) + 1.2, (T if down else L) + 1.2)]
    for kind, k, at, size, opts in feats:
        n = counts[kind] = counts.get(kind, -1) + 1
        vi, u0 = specs[k + 1][1], at * L
        sign = -1 if size is not None and size < 0 else 1
        tgt = k + 1 if sign > 0 else k
        src = specs[k if sign > 0 else k + 1]
        tth = specs[tgt][2]
        if kind in ("dendrite", "crack"):
            depth = abs(size) if size else tth * (0.75 if kind == "dendrite" else 0.5)
            if kind == "crack" and opts.get("through"):
                depth = tth
            # grow layer by layer (a dendrite may pierce a thin SEI first); follow grain boundaries where present
            trunk, arms, left, j, cur = [(u0, vi)], [], depth, tgt, (u0, vi)
            while left > 1 and 0 <= j < len(specs):
                jv0, jth = specs[j][1], specs[j][2]
                far = jv0 + jth if sign > 0 else jv0
                step = min(left, abs(far - cur[1]))
                seg, adj = _gb_walk(rnd, gb[j][0], cur, sign, step, gb[j][1]) if j in gb else (None, None)
                if not seg:  # no grain boundary to follow: free jagged growth
                    n_st = max(2, int(step / 9))
                    seg = _walk(
                        rnd,
                        cur[0],
                        cur[1],
                        sign * math.pi / 2,
                        step,
                        n_st,
                        0.3 if kind == "dendrite" else (0.22 if opts.get("through") else 0.55),
                    )
                    gain = (seg[-1][1] - cur[1]) or 1  # stretch so the walk ends exactly `step` deep
                    seg = [(u, cur[1] + (v_ - cur[1]) * sign * step / gain) for u, v_ in seg]
                seg = [cur] + seg[1:]
                base = len(trunk) - 1
                arms += [
                    (base + i, a)
                    for i, a in _branches(rnd, seg, sign, depth, adj, gb[j][1] if adj else depth / 4, jv0, jv0 + jth)
                    if jth > depth * 0.2
                ]
                trunk += seg[1:]
                left -= abs(seg[-1][1] - cur[1])
                cur = seg[-1]
                if abs(cur[1] - far) > 2:
                    break
                j += sign
            if kind == "dendrite":
                color = opts.get("fill") or _mix(src[3], "#000000", 0.08)
                w0 = max(3.0, depth * 0.075)
                shapes = [_taper(trunk, w0, 1.0)]
                shapes += [_taper(arm, max(1.4, w0 * (1 - i / len(trunk)) * 0.6), 0.7) for i, arm in arms]
                shapes.append(
                    [(u0 - w0 * 1.6, vi)]
                    + [
                        (
                            u0 + w0 * 1.6 * math.cos(math.pi - math.pi * q / 10),
                            vi + sign * w0 * 1.1 * math.sin(math.pi * q / 10),
                        )
                        for q in range(11)
                    ]
                )
                d_all = " ".join(pd(s) for s in shapes)
                holder.append(
                    _el(
                        "path",
                        d=d_all,
                        fill=_mix(color, "#000000", 0.45),
                        stroke=_mix(color, "#000000", 0.45),
                        stroke_width=1.3,
                        stroke_linejoin="round",
                    )
                )
                holder.append(_el("path", d=d_all, fill=color, stroke="none"))
                shine.append(
                    _el(
                        "path",
                        d=pd([(u + w0 * 0.18, v_) for u, v_ in trunk[1:-1]], False),
                        fill="none",
                        stroke="#FFFFFF",
                        stroke_opacity=0.6,
                        stroke_width=max(0.8, w0 * 0.3),
                        stroke_linecap="round",
                        stroke_linejoin="round",
                    )
                )
                ports[f"dendrite{n}_base"], ports[f"dendrite{n}_tip"] = P(*trunk[0]), P(*trunk[-1])
            else:
                # opening-mode crack: wedge that is widest at the mouth, jagged walls, dark rim around the open gap
                mouth = float(opts.get("width") or max(2.6, depth * 0.07))
                through = bool(opts.get("through"))
                tip_w = mouth * 0.45 if through else 0.3
                shapes = [_taper(trunk, mouth, tip_w)] + (
                    [] if through else [_taper(arm, mouth * 0.4, 0.2) for _, arm in arms[:2] if len(arm) > 1]
                )
                rim = _mix(specs[tgt][3], "#000000", 0.6)
                gap = opts.get("fill") or ("#FBFCFD" if mouth >= 2.5 else _mix(specs[tgt][3], "#000000", 0.72))
                d_all = " ".join(pd(s) for s in shapes)
                holder.append(_el("path", d=d_all, fill=gap, stroke=rim, stroke_width=0.9, stroke_linejoin="round"))
                shine.append(
                    _el(
                        "path",
                        d=pd([(u - mouth * 0.2, v_) for u, v_ in trunk[:-1]], False),
                        fill="none",
                        stroke="#000000",
                        stroke_opacity=0.18,
                        stroke_width=max(0.8, mouth * 0.3),
                        stroke_linecap="round",
                    )
                )
                ports[f"crack{n}_tip"] = P(*trunk[-1])
                ports[f"crack{n}_mouth"] = P(*trunk[0])
        elif kind == "void":
            w = abs(size) if size else L * 0.14
            deep, shallow = w * 0.3, w * 0.06
            ph = rnd.uniform(0, 6.3)
            top = [
                (
                    u0 - w / 2 + w * j / 24,
                    vi + sign * deep * math.sin(math.pi * j / 24) ** 0.7 * (1 + 0.1 * math.sin(ph + j * 0.3)),
                )
                for j in range(25)
            ]
            bot = [(u0 + w / 2 - w * j / 24, vi - sign * shallow * math.sin(math.pi * j / 24)) for j in range(1, 24)]
            holder.append(
                _el(
                    "path",
                    d=pd(top + bot),
                    fill=opts.get("fill") or "#FBFCFD",
                    stroke=_mix(src[3], "#000000", 0.5),
                    stroke_width=0.9,
                    stroke_linejoin="round",
                )
            )
            shine.append(
                _el(
                    "path",
                    d=pd(top[3:-3], False),
                    fill="none",
                    stroke="#000000",
                    stroke_opacity=0.12,
                    stroke_width=max(1.5, deep * 0.25),
                    stroke_linecap="round",
                )
            )
            ports[f"void{n}"] = P(u0, vi + sign * deep * 0.45)
        elif kind == "pinhole":
            # through-thickness pinhole across layer `tgt`: hourglass channel, slightly wider at both faces
            far = specs[tgt][1] + (specs[tgt][2] if sign > 0 else 0)
            r = abs(size) if size else max(2.5, tth * 0.09)
            steps = 10
            left, right = [], []
            for j in range(steps + 1):
                t = j / steps
                vv = vi + (far - vi) * t
                wj = r * (1 - 0.45 * math.sin(math.pi * t)) * (1 + rnd.uniform(-0.12, 0.12))
                du = r * 0.5 * math.sin(t * 5 + at * 9)
                left.append((u0 + du - wj, vv))
                right.append((u0 + du + wj, vv))
            holder.append(
                _el(
                    "path",
                    d=pd(left + right[::-1]),
                    fill=opts.get("fill") or "#FBFCFD",
                    stroke=_mix(specs[tgt][3], "#000000", 0.55),
                    stroke_width=0.9,
                    stroke_linejoin="round",
                )
            )
            shine.append(
                _el(
                    "path",
                    d=pd(left, False),
                    fill="none",
                    stroke="#000000",
                    stroke_opacity=0.15,
                    stroke_width=max(1, r * 0.4),
                )
            )
            ports[f"pinhole{n}"] = P(u0, (vi + far) / 2)
        elif kind == "delamination":
            # interfacial debond: long flat gap along interface k with rough walls, slightly opened in the middle
            w = abs(size) if size else L * 0.3
            open_ = float(opts.get("width") or max(3.0, min(src[2], tth) * 0.22))
            top, bot = [], []
            for j in range(25):
                t = j / 24
                uu = u0 - w / 2 + w * t
                env = math.sin(math.pi * t) ** 0.5
                top.append((uu, vi - sign * open_ * 0.35 * env * (1 + rnd.uniform(-0.25, 0.25))))
                bot.append((uu, vi + sign * open_ * 0.65 * env * (1 + rnd.uniform(-0.25, 0.25))))
            holder.append(
                _el(
                    "path",
                    d=pd(top + bot[::-1]),
                    fill=opts.get("fill") or "#FBFCFD",
                    stroke=_mix(src[3], "#000000", 0.5),
                    stroke_width=0.9,
                    stroke_linejoin="round",
                )
            )
            shine.append(
                _el(
                    "path",
                    d=pd(top[2:-2], False),
                    fill="none",
                    stroke="#000000",
                    stroke_opacity=0.15,
                    stroke_width=max(1, open_ * 0.25),
                )
            )
            ports[f"delamination{n}"] = P(u0, vi)
        elif kind == "particle":
            r = abs(size) if size else min(s[2] for s in specs) * 0.3 + 3
            cv = vi + sign * r * 0.35
            blob = [
                (
                    u0 + r * (1 + 0.12 * math.sin(3 * a + 1)) * math.cos(a),
                    cv + r * (1 + 0.1 * math.cos(2 * a)) * math.sin(a),
                )
                for a in [2 * math.pi * j / 28 for j in range(28)]
            ]
            fill = opts.get("fill") or "#6E7F96"
            holder.append(_el("path", d=pd(blob), fill=fill, stroke=_mix(fill, "#000000", 0.4), stroke_width=0.9))
            if rich:
                defs.append(_spot(f"is_p{n}", fill))
                shine.append(_el("path", d=pd(blob), fill=f"url(#is_p{n})"))
            ports[f"particle{n}"] = P(u0, cv)
        elif kind == "whisker":
            # tip-growth fibre: filament grows from the surface into the next layer, the catalyst particle rides on its tip
            Lw = abs(size) if size else tth * 0.7
            mr = float(opts.get("r") or max(3.0, Lw * 0.09))
            cw = mr * 1.3
            a = sign * math.pi / 2 + rnd.uniform(-0.3, 0.3)
            pts, p = [(u0, vi)], (u0, vi)
            for _ in range(9):
                a += rnd.uniform(-0.32, 0.32)
                a = (
                    min(max(a, sign * math.pi / 2 - 0.7), sign * math.pi / 2 + 0.7)
                    if sign > 0
                    else max(min(a, sign * math.pi / 2 + 0.7), sign * math.pi / 2 - 0.7)
                )
                p = (p[0] + Lw / 9 * math.cos(a), p[1] + Lw / 9 * math.sin(a))
                pts.append(p)
            color = opts.get("fill") or "#2F2D2C"
            holder.append(
                _el(
                    "path",
                    d=pd(_taper(pts, cw, cw * 0.92)),
                    fill=color,
                    stroke=_mix(color, "#000000", 0.5),
                    stroke_width=0.7,
                    stroke_linejoin="round",
                )
            )
            holder.append(
                _el(
                    "path",
                    d=pd(pts[1:-1], False),
                    fill="none",
                    stroke=_mix(color, "#FFFFFF", 0.45),
                    stroke_width=max(0.6, cw * 0.22),
                    stroke_dasharray=f"{fmt(cw * 0.9)} {fmt(cw * 0.6)}",
                )
            )
            hx, hy = math.cos(a), math.sin(a)
            tx, ty = pts[-1]
            tip = [
                (
                    tx
                    + hx * mr * 0.55
                    + mr * (1 + 0.25 * math.cos(q)) * math.cos(q) * hx
                    - mr * 0.85 * math.sin(q) * hy,
                    ty
                    + hy * mr * 0.55
                    + mr * (1 + 0.25 * math.cos(q)) * math.cos(q) * hy
                    + mr * 0.85 * math.sin(q) * hx,
                )
                for q in [2 * math.pi * j / 18 for j in range(18)]
            ]
            mfill = opts.get("tip") or src[3]
            holder.append(_el("path", d=pd(tip), fill=mfill, stroke=_mix(mfill, "#000000", 0.45), stroke_width=1))
            if rich:
                defs.append(_spot(f"is_w{n}", mfill))
                shine.append(_el("path", d=pd(tip), fill=f"url(#is_w{n})"))
            ports[f"whisker{n}_base"], ports[f"whisker{n}_tip"] = P(u0, vi), P(tx + hx * mr * 1.2, ty + hy * mr * 1.2)
        elif kind == "adsorbate":
            # surface coverage θ: adsorbed atoms in a monolayer on the face of the previous (sign>0) layer
            span = abs(size) if size else L * 0.5
            cov = min(max(float(opts.get("coverage", 0.5)), 0.0), 1.0)
            ar = float(opts.get("r") or max(2.4, min(tth, src[2]) * 0.07))
            n_site = max(1, int(span / (ar * 2.15)))
            u_start = min(max(u0 - span / 2, ar), L - ar - n_site * ar * 2.15)
            sites = [u_start + ar * 1.075 + j * ar * 2.15 for j in range(n_site)]
            occ = sorted(rnd.sample(sites, round(cov * len(sites))))  # exactly θ of the sites occupied
            color = opts.get("fill") or "#E9C21C"
            holder.append(
                _el(
                    "path",
                    d=" ".join(_circ(*P(u, vi + sign * ar * 0.95), ar) for u in occ) or "M0 0",
                    fill=color,
                    stroke=_mix(color, "#000000", 0.45),
                    stroke_width=max(0.4, ar * 0.22),
                )
            )
            if occ:
                ports[f"adsorbate{n}"] = P(occ[len(occ) // 2], vi + sign * ar)
        else:  # flux arrow across the interface
            span = abs(size) if size else 36.0
            color = opts.get("color") or "#D9822B"
            a, b = (u0, vi - sign * span / 2), (u0, vi + sign * span / 2)
            (x1, y1), (x2, y2) = P(*a), P(u0, b[1] - sign * 7)
            holder.append(
                _el(
                    "path",
                    d=f"M{fmt(x1)} {fmt(y1)} L{fmt(x2)} {fmt(y2)}",
                    fill="none",
                    stroke=color,
                    stroke_width=2.2,
                    stroke_linecap="round",
                    stroke_dasharray="4 3" if opts.get("dashed") else None,
                )
            )
            hx, hy = P(*b)
            holder.append(_head(hx, hy, hx - x1, hy - y1, 8, color))
            if opts.get("label"):
                fs = font_size * 0.95
                lx, ly = (
                    (u0 + fs * 0.4, vi + fs * 0.36) if down else (a[1] + (0 if sign > 0 else -span), u0 - fs * 0.45)
                )
                t, bb = _text(
                    lx, ly, opts["label"], fs, fill=_mix(color, "#000000", 0.25), anchor="start", weight="bold"
                )
                holder.append(t)
                boxes.append(bb)
            ports[f"flux{n}"] = P(u0, vi)
    if rich and shine:
        look = _look()
        look.extend(shine)
        holder.append(look)
    holder.append(rect(0, 0, L, T, fill="none", stroke="#5E6773", stroke_width=1))

    # layer names outside the section, spread apart with leaders when crowded
    names = [(i, name, v0 + th / 2) for i, (name, v0, th, _, _) in enumerate(specs) if name]
    fs = font_size
    if down:
        need = [fs * 1.3] * len(names)
    else:
        need = [label(str(nm), font_size=fs, font_weight="bold").bounds.width + fs * 0.6 for _, nm, _ in names]
    pos = [m for _, _, m in names]
    for j in range(1, len(pos)):
        pos[j] = max(pos[j], pos[j - 1] + (need[j - 1] + need[j]) / 2)
    if pos:
        shift = sum(p - m for p, (_, _, m) in zip(pos, names)) / len(pos)
        pos = [p - shift for p in pos]
    moved = any(abs(p - m) > 1 for p, (_, _, m) in zip(pos, names))
    gap = fs * (1.6 if moved else 0.5)
    segs = []
    for (i, name, mid), p in zip(names, pos):
        if down:
            t, b = _text(L + gap, p + fs * 0.36, name, fs, fill=label_fill, anchor="start", weight="bold")
            if abs(p - mid) > 1:
                segs.append(f"M{fmt(L)} {fmt(mid)} L{fmt(L + gap - 3)} {fmt(p)}")
        else:
            t, b = _text(p, -gap - fs * 0.1, name, fs, fill=label_fill, weight="bold")
            if abs(p - mid) > 1:
                segs.append(f"M{fmt(mid)} 0 L{fmt(p)} {fmt(-gap + 2)}")
        holder.append(t)
        boxes.append(b)
    if segs:
        holder.append(_el("path", d=" ".join(segs), fill="none", stroke=_INK, stroke_width=0.8))
    return _finish(holder, defs, _union(boxes), **ports)


@_drawing_api(
    "parts",
    purpose="锂离子电池截面示意：两侧金属集流体、颗粒堆积正极、多孔隔膜、层状石墨负极，电解液中 Li⁺ 迁移箭头与外电路电子流。",
    returns="Geometry（原点在中心；端口 cathode/separator/anode 为各区中心，plus/minus 为正负极外电路接点）",
    semantics=(
        "width/height 为电池本体尺寸（外电路与底部标签在其外）；cathode/anode/electrolyte/ion 为各部分颜色。",
        'direction="discharge" 时 Li⁺ 由负极经隔膜迁向正极、电子经外电路流向正极（外接“负载”）；"charge" 相反（外接“电源”）。',
        'labels=True 在底部写 集流体/正极/隔膜/负极 等文字标签；style="rich" 加颗粒立体感与金属光泽（局部 SVG）。',
    ),
    example='d.place(battery_cell(440, 220, direction="discharge"), at=(480, 280), key="cell")',
    rank=7,
)
def battery_cell(
    width=420,
    height=220,
    *,
    cathode="#C0504D",
    anode="#4A6FA5",
    electrolyte="#EAF3FA",
    ion="#E0A458",
    labels=True,
    direction="discharge",
    style="rich",
    font_size=13,
    seed=5,
):
    _finite(width, height)
    if direction not in ("discharge", "charge"):
        raise ValueError('direction must be "discharge" or "charge"')
    rich = _rich(style)
    rnd = random.Random(seed)
    W, H = float(width), float(height)
    holder, defs = _start()
    cc = max(7.0, W * 0.022)  # current collector thickness
    gap = W * 0.085  # electrolyte gap on each side of the separator
    sep = max(8.0, W * 0.028)
    elec = (W - 2 * cc - 2 * gap - sep) / 2  # electrode width
    xc0, xc1 = cc, cc + elec  # cathode
    xs0 = xc1 + gap  # separator
    xa0 = xs0 + sep + gap  # anode
    xa1 = xa0 + elec
    pad = H * 0.06
    holder.append(
        _el("rect", x=0, y=0, width=W, height=H, fill=electrolyte, stroke="#7F8A96", stroke_width=1.2, data_outline="1")
    )
    al, cu = "#AEB5BE", "#C98B5A"
    holder.append(
        _el("rect", x=0, y=0, width=cc, height=H, fill=al, stroke=_mix(al, "#000000", 0.35), stroke_width=0.8)
    )
    holder.append(
        _el("rect", x=W - cc, y=0, width=cc, height=H, fill=cu, stroke=_mix(cu, "#000000", 0.35), stroke_width=0.8)
    )

    # cathode: packed spherical particles (separate circles)
    r = min(elec / 7.5, H / 13)
    edge_c = _mix(cathode, "#000000", 0.35)
    centers = []
    rows = int((H - 2 * pad) / (r * 1.75))
    for j in range(rows):
        cy = pad + r + j * (H - 2 * pad - 2 * r) / max(1, rows - 1)
        off = r * 0.9 if j % 2 else 0
        cx = xc0 + r + off + 1
        while cx + r <= xc1 + r * 0.3:
            rr = r * rnd.uniform(0.82, 1.0)
            centers.append((cx + rnd.uniform(-1, 1), cy + rnd.uniform(-1, 1), rr))
            cx += r * 1.85
    for cx, cy, rr in centers:
        holder.append(_el("circle", cx=cx, cy=cy, r=rr, fill=cathode, stroke=edge_c, stroke_width=0.8))

    sep_fill = "#F7F7F5"
    holder.append(_el("rect", x=xs0, y=0, width=sep, height=H, fill=sep_fill, stroke="#9AA3AE", stroke_width=0.8))
    k = 0
    yy = 5.0
    while yy < H - 4:
        px = xs0 + sep * (0.3 if k % 2 else 0.68)
        holder.append(_el("ellipse", cx=px, cy=yy, rx=sep * 0.16, ry=2.2, fill="#C9D1DA"))
        yy += 7.5
        k += 1

    edge_a = _mix(anode, "#000000", 0.35)
    fh = max(3.5, H / 34)
    fgap = fh * 0.55
    flakes = []
    y = pad
    j = 0
    while y + fh <= H - pad:
        x = xa0 + (elec * 0.08 if j % 2 else 0)
        while x < xa1 - 6:
            fw = min(elec * rnd.uniform(0.32, 0.48), xa1 - x)
            if fw > 6:
                flakes.append((x, y, fw - 2))
            x += fw + 2
        y += fh + fgap
        j += 1
    for x, y, fw in flakes:
        holder.append(
            _el("rect", x=x, y=y, width=fw, height=fh, rx=fh / 2, fill=anode, stroke=edge_a, stroke_width=0.6)
        )

    left_to_right = direction == "charge"
    ion_r = max(5.0, min(gap * 0.2, H * 0.035))
    ion_edge = _mix(ion, "#000000", 0.3)
    ions = []
    for frac in (0.18, 0.42, 0.66, 0.86):
        ions.append((xc1 + gap * 0.5 + rnd.uniform(-2, 2), H * frac))
        ions.append((xa0 - gap * 0.5 + rnd.uniform(-2, 2), H * (frac + 0.1 if frac < 0.8 else 0.08)))
    arrow_c = _mix(ion, "#000000", 0.35)
    segs = []
    for fy in (0.3, 0.55, 0.78):
        ay = H * fy
        a, b = xc1 + gap * 0.2, xa0 - gap * 0.2
        if left_to_right:
            segs.append(f"M{fmt(a)} {fmt(ay)} H{fmt(b - 8)}")
            heads = [(b, ay, 1)]
        else:
            segs.append(f"M{fmt(b)} {fmt(ay)} H{fmt(a + 8)}")
            heads = [(a, ay, -1)]
        for hx, hy, dx in heads:
            holder.append(_head(hx, hy, dx, 0, 9, arrow_c))
    holder.append(
        _el(
            "path",
            d=" ".join(segs),
            fill="none",
            stroke=arrow_c,
            stroke_width=2,
            stroke_linecap="round",
            stroke_dasharray="6 3",
        )
    )
    for cx, cy in ions:
        holder.append(_el("circle", cx=cx, cy=cy, r=ion_r, fill=ion, stroke=ion_edge, stroke_width=0.8))

    if rich:
        look = _look()
        defs.append(_spot("bc_p", cathode))
        for cx, cy, rr in centers:
            look.append(_el("circle", cx=cx, cy=cy, r=rr - 0.4, fill="url(#bc_p)"))
        defs.append(_linear("bc_fl", [(0, "#FFFFFF", 0.5), (0.45, "#FFFFFF", 0.05), (1, "#000000", 0.25)]))
        for x, y, fw in flakes:
            look.append(_el("rect", x=x, y=y, width=fw, height=fh, rx=fh / 2, fill="url(#bc_fl)"))
        defs.append(
            _linear(
                "bc_m",
                [(0, "#000000", 0.2), (0.35, "#FFFFFF", 0.55), (0.65, "#FFFFFF", 0.1), (1, "#000000", 0.25)],
                x2=1,
                y2=0,
            )
        )
        look.append(_el("rect", x=0, y=0, width=cc, height=H, fill="url(#bc_m)"))
        look.append(_el("rect", x=W - cc, y=0, width=cc, height=H, fill="url(#bc_m)"))
        defs.append(_spot("bc_i", ion))
        for cx, cy in ions:
            look.append(_el("circle", cx=cx, cy=cy, r=ion_r - 0.3, fill="url(#bc_i)"))
        defs.append(_linear("bc_el", [(0, "#FFFFFF", 0.35), (1, "#FFFFFF", 0.0)]))
        look.append(_el("rect", x=cc, y=0, width=W - 2 * cc, height=H * 0.25, fill="url(#bc_el)"))
        holder.append(look)
    pfs = max(7.0, ion_r * 1.5)
    for cx, cy in ions:
        t, _ = _text(cx, cy + pfs * 0.36, "+", pfs, fill="#FFFFFF" if _dark(ion) else _INK, weight="bold")
        holder.append(t)
    boxes = [Box(-0.6, -0.6, W + 1.2, H + 1.2)]

    fs = font_size
    top = -max(34.0, H * 0.2)
    wire = "#4B5563"
    px, nx = cc / 2, W - cc / 2
    lw, lh = max(54.0, fs * 4), fs * 1.9
    holder.append(
        _el(
            "path",
            d=f"M{fmt(px)} 0 V{fmt(top)} H{fmt(W / 2 - lw / 2)} M{fmt(W / 2 + lw / 2)} {fmt(top)} H{fmt(nx)} V0",
            fill="none",
            stroke=wire,
            stroke_width=1.6,
            stroke_linejoin="round",
        )
    )
    holder.append(
        _el(
            "rect",
            x=W / 2 - lw / 2,
            y=top - lh / 2,
            width=lw,
            height=lh,
            rx=4,
            fill="#FFFFFF",
            stroke=wire,
            stroke_width=1.4,
        )
    )
    t, _ = _text(W / 2, top + fs * 0.36, "电源" if left_to_right else "负载", fs, weight="bold")
    holder.append(t)
    ex = W * 0.25 if not left_to_right else W * 0.75
    edir = -1 if not left_to_right else 1
    e_x = W * 0.78 if not left_to_right else W * 0.22
    holder.append(_head(e_x + edir * 7, top, edir, 0, 9, "#2E7BC4"))
    t, b = _text(e_x, top - 7, "e⁻", fs, fill="#2E7BC4", weight="bold")
    holder.append(t)
    boxes.append(b)
    del ex
    for x, sym in ((px, "+"), (nx, "−")):
        t, b = _text(x, top - 7, sym, fs * 1.15, weight="bold", fill=_INK)
        holder.append(t)
        boxes.append(b)
    boxes.append(Box(0, top - lh / 2, W, -top + lh / 2))
    mode = "充电" if left_to_right else "放电"
    t, b = _text(W / 2, top - lh / 2 - 6, mode, fs, fill="#5B6573")
    holder.append(t)
    boxes.append(b)

    if labels:
        ly = H + fs * 1.45
        for x, txt in (
            (cc / 2, "集流体"),
            ((xc0 + xc1) / 2, "正极"),
            (xs0 + sep / 2, "隔膜"),
            ((xa0 + xa1) / 2, "负极"),
            (W - cc / 2, "集流体"),
        ):
            t, b = _text(x, ly, txt, fs, fill=_INK)
            holder.append(t)
            boxes.append(b)
        sub = fs * 0.85
        for x, txt in (
            (cc / 2, "(Al)"),
            (W - cc / 2, "(Cu)"),
            ((xc0 + xc1) / 2, "(LiCoO₂)"),
            ((xa0 + xa1) / 2, "(石墨)"),
        ):
            t, b = _text(x, ly + sub * 1.3, txt, sub, fill="#5B6573")
            holder.append(t)
            boxes.append(b)
        gy = ly + sub * 1.3 + fs * 1.5
        gx = W / 2 - fs * 3.2
        holder.append(_el("circle", cx=gx, cy=gy - fs * 0.35, r=ion_r, fill=ion, stroke=ion_edge, stroke_width=0.8))
        t, _ = _text(gx, gy - fs * 0.35 + pfs * 0.36, "+", pfs, fill="#FFFFFF" if _dark(ion) else _INK, weight="bold")
        holder.append(t)
        t, b = _text(gx + ion_r + 5, gy, "Li⁺（电解液中迁移）", sub, fill="#5B6573", anchor="start")
        holder.append(t)
        boxes.append(b)
        boxes.append(Box(gx - ion_r, gy - fs * 0.35 - ion_r, 2 * ion_r, 2 * ion_r))
    ports = dict(
        cathode=((xc0 + xc1) / 2, H / 2),
        separator=(xs0 + sep / 2, H / 2),
        anode=((xa0 + xa1) / 2, H / 2),
        plus=(px, top),
        minus=(nx, top),
    )
    return _finish(holder, defs, _union(boxes), **ports)


_SMALL = {"H": 0.62, "F": 0.8, "Cl": 0.95, "Li": 0.85}
CPK = {
    "H": "#F2F2F2",
    "C": "#404040",
    "N": "#3A5BD9",
    "O": "#E24C3B",
    "S": "#E8C536",
    "P": "#F08A24",
    "Cl": "#3FA34D",
    "F": "#8FD16A",
    "R": "#9AA1AB",
}
_CHARGES = "+-−⁺⁻"


def _preset(spec):
    """(symbol, x, y, z) atoms and (i, j, order) bonds; z > 0 is toward the viewer (drawn later, slightly larger)."""
    s3, L = 1 / math.sqrt(3), 40
    tet = [(s3, s3, s3), (-s3, -s3, s3), (-s3, s3, -s3), (s3, -s3, -s3)]

    def view(v, ry=0.3, rx=0.2):  # tilted view so no two tetrahedral atoms overlap
        x, y, z = v
        x, z = x * math.cos(ry) + z * math.sin(ry), -x * math.sin(ry) + z * math.cos(ry)
        return x * L, y * math.cos(rx) * L - z * math.sin(rx) * L, y * math.sin(rx) + z * math.cos(rx)

    if spec == "CO2":
        return [("O", -L, 0, 0), ("C", 0, 0, 0), ("O", L, 0, 0)], [(0, 1, 2), (1, 2, 2)]
    if spec == "H2O":  # H–O–H 104.5°
        a = math.radians(104.5 / 2)
        return [
            ("O", 0, 0, 0),
            ("H", -L * 0.85 * math.sin(a), L * 0.85 * math.cos(a), 0),
            ("H", L * 0.85 * math.sin(a), L * 0.85 * math.cos(a), 0),
        ], [(0, 1, 1), (0, 2, 1)]
    if spec == "CH4":
        return [("C", 0, 0, 0)] + [("H",) + view(v) for v in tet], [(0, k, 1) for k in range(1, 5)]
    if spec == "NH3":  # trigonal pyramid, lone pair up (H–N–H 107°)
        th = math.radians(112)
        hs = [
            (math.sin(th) * math.cos(a), -math.cos(th), math.sin(th) * math.sin(a))
            for a in map(math.radians, (20, 140, 260))
        ]
        return [("N", 0, -L * 0.15, 0)] + [("H",) + view(v, 0, 0.35) for v in hs], [(0, k, 1) for k in range(1, 4)]
    if spec in ("N2", "O2", "H2"):
        sym = spec[0]
        return [(sym, -L * 0.6, 0, 0), (sym, L * 0.6, 0, 0)], [(0, 1, {"N": 3, "O": 2, "H": 1}[sym])]
    if spec == "carbamate":  # R–NH–COO⁻ (planar, 120°)

        def go(p, deg):
            return p[0] + L * math.cos(math.radians(deg)), p[1] - L * math.sin(math.radians(deg))

        n = go((0, 0), 210)
        atoms = [
            ("C", 0, 0),
            ("O", *go((0, 0), 90)),
            ("O−", *go((0, 0), -30)),
            ("N", *n),
            ("R", *go(n, 150)),
            ("H", *go(n, 270)),
        ]
        return [a + (0,) for a in atoms], [(0, 1, 2), (0, 2, 1), (0, 3, 1), (3, 4, 1), (3, 5, 1)]
    if spec == "benzene":
        ring = [(math.cos(math.radians(90 + 60 * k)), -math.sin(math.radians(90 + 60 * k))) for k in range(6)]
        atoms = [("C", x * L * 1.1, y * L * 1.1, 0) for x, y in ring] + [
            ("H", x * L * 1.9, y * L * 1.9, 0) for x, y in ring
        ]
        return atoms, [(k, (k + 1) % 6, 2 if k % 2 == 0 else 1) for k in range(6)] + [(k, k + 6, 1) for k in range(6)]
    raise ValueError(f"unknown molecule preset {spec!r}; presets: {', '.join(MOLECULES)}")


MOLECULES = ("CO2", "H2O", "CH4", "NH3", "N2", "O2", "H2", "carbamate", "benzene")


@_drawing_api(
    "parts",
    purpose="球棍分子模型：原子小球 + 单/双/三键棍，教材风格立体高光；内置常见小分子（CO2/H2O/CH4/NH3/N2/O2/H2/carbamate/benzene）正确几何与 CPK 配色。",
    returns="Geometry（原点在中心；端口 atom_i 为第 i 个原子中心）",
    semantics=(
        '预设：molecule("CO2") 直线 O=C=O、"H2O" 104.5° 弯曲、"CH4" 四面体投影、"NH3" 三角锥、"N2" 叁键、"O2"/"H2"、'
        '"carbamate" 氨基甲酸根 R–NH–COO⁻（平面 120°，O⁻ 带电荷）、"benzene" 苯环（交替双键）；CPK 配色（C 深灰、O 红、N 蓝、H 白）。',
        "自定义：atoms 为 [(元素符号, x, y, 颜色[, z])]（局部坐标 px，乘 scale；z>0 朝向观众，后画并略大）；bonds 为 [(i, j, 键级)]，键级 1/2/3 画成平行棍。",
        '符号末尾带 + / − 时（如 "O−"）球心写元素、右上角写电荷；原子半径按元素自动取（H 较小）；labels=False 不写元素符号（小尺寸客体分子用）；rotate 为预设分子的旋转角（度）。',
        'style="rich" 加球面高光（局部 SVG），"flat" 纯色原生形状。',
    ),
    example='co2 = d.place(molecule("CO2", scale=.8), at=(300, 200), key="co2")\n'
    'd.place(molecule([("O", 0, 0, "#E24C3B"), ("H", -34, 24, "#F2F2F2"), ("H", 34, 24, "#F2F2F2")], [(0, 1, 1), (0, 2, 1)]), at=(420, 200))',
    rank=8,
)
def molecule(
    atoms,
    bonds=None,
    *,
    scale=1.0,
    style="rich",
    radius=14,
    bond_color="#9AA1AB",
    font_size=None,
    labels=True,
    rotate=0,
):
    if isinstance(atoms, str):
        raw, bonds = _preset(atoms)
        c, s_ = math.cos(math.radians(rotate)), math.sin(math.radians(rotate))
        raw = [(sym, x * c - y * s_, x * s_ + y * c, z) for sym, x, y, z in raw]
        atoms = [(sym, x, y, CPK[sym.rstrip(_CHARGES)], z) for sym, x, y, z in raw]
    if bonds is None:
        raise TypeError('molecule(atoms, bonds): pass bonds, or a preset name such as molecule("CO2")')
    depth = [float(a[4]) if len(a) > 4 else 0.0 for a in atoms]
    atoms = [tuple(a[:4]) for a in atoms]
    _finite(scale, radius)
    rich = _rich(style)
    holder, defs = _start()
    pts = [(float(x) * scale, float(y) * scale) for _, x, y, _ in atoms]
    radii = [
        radius * scale * _SMALL.get(sym.rstrip(_CHARGES), 1.0) * (1 + 0.1 * z) for (sym, *_), z in zip(atoms, depth)
    ]
    stack = sorted(range(len(atoms)), key=lambda k: depth[k])  # back to front
    sw = max(2.0, 4.2 * scale)
    spacing = sw * 1.35
    edge_b = _mix(bond_color, "#000000", 0.3)
    first = True
    for i, j, order in bonds:
        (x1, y1), (x2, y2) = pts[i], pts[j]
        L = math.hypot(x2 - x1, y2 - y1) or 1
        nx, ny = -(y2 - y1) / L, (x2 - x1) / L
        order = max(1, min(3, int(order)))
        for k in range(order):
            o = (k - (order - 1) / 2) * spacing
            d = f"M{fmt(x1 + nx * o)} {fmt(y1 + ny * o)} L{fmt(x2 + nx * o)} {fmt(y2 + ny * o)}"
            holder.append(
                _el(
                    "path",
                    d=d,
                    fill="none",
                    stroke=edge_b,
                    stroke_width=sw + 1.2,
                    stroke_linecap="round",
                    data_outline="1" if first else None,
                )
            )
            holder.append(_el("path", d=d, fill="none", stroke=bond_color, stroke_width=sw, stroke_linecap="round"))
            first = False
    for (sym, _, _, color), (x, y), r in ((atoms[k], pts[k], radii[k]) for k in stack):
        holder.append(
            _el(
                "circle",
                cx=x,
                cy=y,
                r=r,
                fill=color,
                stroke=_mix(color, "#000000", 0.35),
                stroke_width=0.9,
                data_outline="1" if first else None,
            )
        )
        first = False
    if rich:
        look = _look()
        defs.append(_linear("mol_st", [(0, "#FFFFFF", 0.55), (1, "#FFFFFF", 0.0)]))
        for i, j, order in bonds:
            (x1, y1), (x2, y2) = pts[i], pts[j]
            L = math.hypot(x2 - x1, y2 - y1) or 1
            nx, ny = -(y2 - y1) / L, (x2 - x1) / L
            order = max(1, min(3, int(order)))
            for k in range(order):
                o = (k - (order - 1) / 2) * spacing - sw * 0.22
                ux, uy = (x2 - x1) / L, (y2 - y1) / L
                a, b = radii[i] * 0.95, L - radii[j] * 0.95
                if b - a < 2:
                    continue
                look.append(
                    _el(
                        "path",
                        d=f"M{fmt(x1 + ux * a + nx * o)} {fmt(y1 + uy * a + ny * o)} "
                        f"L{fmt(x1 + ux * b + nx * o)} {fmt(y1 + uy * b + ny * o)}",
                        fill="none",
                        stroke="#FFFFFF",
                        stroke_opacity=0.5,
                        stroke_width=max(0.8, sw * 0.28),
                        stroke_linecap="round",
                    )
                )
        seen = {}
        for (sym, _, _, color), (x, y), r in ((atoms[k], pts[k], radii[k]) for k in stack):
            gid = seen.get(color)
            if gid is None:
                gid = seen[color] = f"mol_s{len(seen)}"
                defs.append(_spot(gid, color))
            look.append(_el("circle", cx=x, cy=y, r=r - 0.45, fill=f"url(#{gid})"))
        holder.append(look)
    boxes = []
    for (sym, _, _, color), (x, y), r in ((atoms[k], pts[k], radii[k]) for k in stack):
        boxes.append(Box(x - r - 0.5, y - r - 0.5, 2 * r + 1, 2 * r + 1))
        el, charge = sym.rstrip(_CHARGES), sym[len(sym.rstrip(_CHARGES)) :]
        if el and labels:
            fs = font_size or r * (0.95 if len(el) == 1 else 0.78)
            t, _ = _text(x, y + fs * 0.36, el, fs, fill="#FFFFFF" if _dark(color) else _INK, weight="bold")
            holder.append(t)
        if charge and labels:
            cfs = max(7, r * 0.8)
            t, b = _text(x + r * 0.8, y - r * 0.55, charge.replace("-", "−"), cfs, anchor="start", weight="bold")
            holder.append(t)
            boxes.append(b)
    ports = {f"atom_{i}": p for i, p in enumerate(pts)}
    return _finish(holder, defs, _union(boxes), **ports)
