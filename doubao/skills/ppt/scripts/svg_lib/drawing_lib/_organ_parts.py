"""Organ / tissue / nervous-system parts drawn like journal figures: intestinal_wall, neuron, brain, heart, nephron, bbb_unit."""

from __future__ import annotations

import math
import random

from ..atomize_svg_to_slide._geometry import fmt
from ._bio_parts import _el, _look, _mix, _radial, _smooth, _linear
from ._earth_parts import _style, _finish, _d, _cr, _offset, _band, _along, _circ, _oval, _inside, _tube, _head
from ._geometry import Box, _finite
from ._help import _drawing_api

_INK = "#3A2E2A"


def _sw(v):
    return max(0.35, v)


def _stadium(cx, cy, length, width, ang):
    """Rod / capsule outline centred at (cx, cy) along angle ``ang``."""
    r, h = width / 2, max(0.0, length / 2 - width / 2)
    c, s = math.cos(ang), math.sin(ang)
    pts = []
    for k in range(9):
        t = -math.pi / 2 + math.pi * k / 8
        pts.append((h + r * math.cos(t), r * math.sin(t)))
    for k in range(9):
        t = math.pi / 2 + math.pi * k / 8
        pts.append((-h + r * math.cos(t), r * math.sin(t)))
    return _smooth([(cx + x * c - y * s, cy + x * s + y * c) for x, y in pts], closed=True)


def _clip_half(poly, a, b, c):
    """Keep the part of ``poly`` where a*x + b*y <= c (Sutherland-Hodgman, one plane)."""
    out = []
    n = len(poly)
    for i in range(n):
        p, q = poly[i], poly[(i + 1) % n]
        fp, fq = a * p[0] + b * p[1] - c, a * q[0] + b * q[1] - c
        if fp <= 0:
            out.append(p)
        if (fp <= 0) != (fq <= 0):
            t = fp / (fp - fq)
            out.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t))
    return out


def _arclen(pts):
    acc = [0.0]
    for a, b in zip(pts, pts[1:]):
        acc.append(acc[-1] + math.dist(a, b))
    return acc


def _at(pts, acc, dist):
    """Point and unit normal at arc length ``dist`` of a polyline."""
    dist = max(0.0, min(acc[-1], dist))
    lo = 0
    while lo < len(acc) - 2 and acc[lo + 1] < dist:
        lo += 1
    a, b = pts[lo], pts[lo + 1]
    L = (acc[lo + 1] - acc[lo]) or 1e-9
    t = (dist - acc[lo]) / L
    tx, ty = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t), (-ty, tx)


_MICROBE_COLORS = ("#5E8FC2", "#E09A4F", "#7DB37A", "#C46F7E", "#8E7BB8", "#4FA9A2", "#D4B54A", "#9A6B4F")


def _microbes(W, y0, y1, s, rnd, avoid):
    """Diverse lumen microbes: rods, cocci (single/diplo/chains), spirilla and vibrios."""
    items, placed = [], []
    n = int(W / (9.5 * s))
    tries = 0
    while len(items) < n and tries < n * 60:
        tries += 1
        x, y = rnd.uniform(8 * s, W - 8 * s), rnd.uniform(y0, y1)
        size = rnd.uniform(0.75, 1.35) * s
        if any(math.dist((x, y), p) < (r + 7.5 * size) for p, r in placed) or avoid((x, y)):
            continue
        u = rnd.random()
        kind = "rod" if u < 0.38 else "coccus" if u < 0.66 else "spiral" if u < 0.82 else "vibrio"
        col = _MICROBE_COLORS[rnd.randrange(len(_MICROBE_COLORS))]
        items.append(
            (
                kind,
                x,
                y,
                size,
                rnd.uniform(-0.9, 0.9) + (math.pi / 2 if rnd.random() < 0.25 else 0),
                col,
                rnd.choice((1, 2, 2, 3, 4)),
            )
        )
        placed.append(((x, y), 7.5 * size))
    return items


def _microbe_paths(items, s):
    """Group microbe geometry by colour: filled bodies + stroked (spiral/vibrio) bodies."""
    fills, strokes, ports = {}, {}, []
    for kind, x, y, k, a, col, m in items:
        c, sn = math.cos(a), math.sin(a)
        if kind == "rod":
            fills.setdefault(col, []).append(_stadium(x, y, 12 * k, 4.6 * k, a))
        elif kind == "coccus":
            r = 2.6 * k
            m = min(m, 3)
            for j in range(m):
                o = (j - (m - 1) / 2) * r * 1.85
                fills.setdefault(col, []).append(_circ(x + c * o, y + sn * o, r))
        elif kind == "spiral":
            L, A = 15 * k, 2.2 * k
            pts = [(-L / 2 + L * t / 24, A * math.sin(t / 24 * 3 * 2 * math.pi)) for t in range(25)]
            pts = [(x + px * c - py * sn, y + px * sn + py * c) for px, py in pts]
            strokes.setdefault((col, round(2.1 * k, 2)), []).append(_smooth(pts))
        else:
            L = 10 * k
            pts = [(-L / 2 + L * t / 8, -2.4 * k * math.sin(math.pi * t / 8)) for t in range(9)]
            pts = [(x + px * c - py * sn, y + px * sn + py * c) for px, py in pts]
            strokes.setdefault((col, round(3.6 * k, 2)), []).append(_smooth(pts))
        ports.append((x, y))
    els = []
    for col, ds in fills.items():
        els.append(_el("path", d=" ".join(ds), fill=col, stroke=_mix(col, "#1E1A18", 0.45), stroke_width=_sw(0.6 * s)))
    for (col, w), ds in strokes.items():
        els.append(
            _el(
                "path",
                d=" ".join(ds),
                fill="none",
                stroke=_mix(col, "#1E1A18", 0.45),
                stroke_width=w + 1.1 * s,
                stroke_linecap="round",
                stroke_linejoin="round",
            )
        )
        els.append(
            _el(
                "path",
                d=" ".join(ds),
                fill="none",
                stroke=col,
                stroke_width=w,
                stroke_linecap="round",
                stroke_linejoin="round",
            )
        )
    return els, ports


def _villus_surface(W, villi, s, rnd, ytip, ybase, ycrypt, cwid):
    """Apical epithelial surface, left → right (tissue lies on the +normal side)."""
    pitch = W / villi
    hw = pitch * 0.36
    ctrl = [(0, ybase + 12 * s)]
    tips = []
    for i in range(villi):
        cx = (i + 0.5) * pitch
        top = ytip + rnd.uniform(-4, 9) * s
        tips.append((cx, top))
        ctrl += [
            (cx - hw, ybase),
            (cx - hw * 0.96, (ybase + top) / 2 + 6 * s),
            (cx - hw * 0.86, top + hw * 0.55),
            (cx - hw * 0.5, top + hw * 0.1),
            (cx, top),
            (cx + hw * 0.5, top + hw * 0.1),
            (cx + hw * 0.86, top + hw * 0.55),
            (cx + hw * 0.96, (ybase + top) / 2 + 6 * s),
            (cx + hw, ybase),
        ]
        if i < villi - 1:
            xm = (i + 1) * pitch
            ctrl += [
                (xm - cwid, ybase + 12 * s),
                (xm - cwid, ycrypt - cwid * 0.9),
                (xm - cwid * 0.6, ycrypt - cwid * 0.25),
                (xm, ycrypt),
                (xm + cwid * 0.6, ycrypt - cwid * 0.25),
                (xm + cwid, ycrypt - cwid * 0.9),
                (xm + cwid, ybase + 12 * s),
            ]
    ctrl.append((W, ybase + 12 * s))
    return _cr(ctrl, 8), tips, pitch, hw


@_drawing_api(
    "parts",
    purpose="肠壁纵切（教科书级）：肠腔多样菌群（杆菌/球菌/螺旋菌/弧菌）、黏液层、绒毛与隐窝的柱状上皮（刷状缘、紧密连接、基底核）、杯状细胞、带基底分泌颗粒的肠内分泌细胞、固有层（毛细血管袢、中央乳糜管、免疫细胞）、黏膜肌层与固有肌层（肌间神经丛），含迷走传入末梢。",
    returns="Geometry（原点在中心；端口 lumen/mucus/epithelium/enterocyte/goblet/tight_junction/eec/eec_base/vagal_terminal/vagal_fiber/lamina_propria/capillary/lacteal/immune/dendritic/crypt/muscularis/myenteric/villus_tip{k}/microbe{k}）",
    semantics=(
        "width 为宽度，高≈0.7×宽（layers=False 时去掉肌层，更矮）；villi 为绒毛数。",
        "cells 选上皮细胞类型（enterocyte/goblet/enteroendocrine）；eec 位于中间绒毛的右侧壁，颗粒在基底侧，迷走传入纤维从底边 vagal_fiber 上行到 vagal_terminal 贴近其基底。",
        'lumen_microbes / immune 控制菌群与免疫细胞；style="rich" 加明暗与黏蛋白纤维（一个局部 SVG），"flat" 全原生。',
        '文字放外面用 callout 指端口；5-HT 释放用 d.arrow(p.port("eec_base"), p.port("vagal_terminal"))。',
    ),
    example='gut = d.place(intestinal_wall(380), at=(210, 220), key="gut")\n'
    'd.callout("eec", "肠内分泌细胞", gut.port("eec"), at=(420, 60), font_size=12)',
    rank=24,
)
def intestinal_wall(
    width=420,
    *,
    villi=5,
    layers=True,
    cells=("enterocyte", "goblet", "enteroendocrine"),
    lumen_microbes=True,
    immune=True,
    epithelium="#F1D3C3",
    nucleus="#6A5796",
    lamina="#F8E7DC",
    mucus="#D7ECE4",
    muscle="#D69488",
    nerve="#E2B13C",
    style="rich",
    seed=4,
):
    rich = _style(style)
    _finite(width)
    villi = int(villi)
    if villi < 1:
        raise ValueError("villi must be ≥ 1")
    bad = set(cells) - {"enterocyte", "goblet", "enteroendocrine"}
    if bad:
        raise ValueError(f"unknown cell types {sorted(bad)}")
    rnd = random.Random(seed)
    W = float(width)
    s = W / 420.0
    T = 15 * s  # epithelium height (columnar)
    ytip, ybase, ycrypt = 72 * s, 160 * s, 212 * s
    ymm = 238 * s  # muscularis mucosae
    H = 300 * s if layers else ymm + 8 * s
    surf, tips, pitch, hw = _villus_surface(W, villi, s, rnd, ytip, ybase, ycrypt, 13.5 * s)
    acc = _arclen(surf)
    holder, defs = _el("g"), _el("defs")
    holder.append(defs)
    ports = {}
    lumen_col = "#FBF6EC"
    holder.append(
        _el(
            "rect",
            x=0,
            y=0,
            width=W,
            height=H,
            fill=lumen_col,
            stroke=_mix(lumen_col, "#7A6250", 0.35),
            stroke_width=_sw(0.8 * s),
            data_outline="1",
        )
    )
    ymu = ytip - 20 * s
    top = [(x * W / 48, ymu + 3.2 * s * math.sin(x * 0.9 + 1.3) + 1.6 * s * math.sin(x * 2.3)) for x in range(49)]
    holder.append(
        _el(
            "path",
            d=_smooth(top) + f" L{fmt(W)} {fmt(ycrypt + 4 * s)} L0 {fmt(ycrypt + 4 * s)} Z",
            fill=mucus,
            stroke=_mix(mucus, "#3F7F6C", 0.35),
            stroke_width=_sw(0.7 * s),
        )
    )
    holder.append(_el("path", d=_d(_band(surf, -5.5 * s, 0)), fill=_mix(mucus, "#3F7F6C", 0.2), stroke="none"))
    inner = _offset(surf, T * 0.6)
    holder.append(_el("path", d=_d(inner + [(W, ymm + 2 * s), (0, ymm + 2 * s)]), fill=lamina, stroke="none"))
    if layers:
        yc0, yc1, yl1 = 252 * s, 274 * s, 291 * s
        holder.append(
            _el(
                "rect",
                x=0,
                y=ymm,
                width=W,
                height=5 * s,
                fill=_mix(muscle, "#FFFFFF", 0.25),
                stroke=_mix(muscle, "#5A2A24", 0.4),
                stroke_width=_sw(0.5 * s),
            )
        )
        holder.append(
            _el(
                "rect",
                x=0,
                y=ymm + 5 * s,
                width=W,
                height=yc0 - ymm - 5 * s,
                fill=_mix(lamina, "#FFFFFF", 0.35),
                stroke="none",
            )
        )
        holder.append(
            _el(
                "rect",
                x=0,
                y=yc0,
                width=W,
                height=yc1 - yc0,
                fill=muscle,
                stroke=_mix(muscle, "#5A2A24", 0.4),
                stroke_width=_sw(0.5 * s),
            )
        )
        holder.append(
            _el(
                "rect",
                x=0,
                y=yc1 + 3 * s,
                width=W,
                height=yl1 - yc1 - 3 * s,
                fill=_mix(muscle, "#9A4A40", 0.12),
                stroke=_mix(muscle, "#5A2A24", 0.4),
                stroke_width=_sw(0.5 * s),
            )
        )
        holder.append(
            _el(
                "rect",
                x=0,
                y=yl1 + 1.5 * s,
                width=W,
                height=H - yl1 - 1.5 * s,
                fill=_mix(lamina, "#FFFFFF", 0.2),
                stroke=_mix(lamina, "#7A5040", 0.4),
                stroke_width=_sw(0.5 * s),
            )
        )
        # smooth-muscle nuclei: spindles in the inner (circular) layer, round profiles in the outer (longitudinal) layer
        spind, dots = [], []
        for row in range(3):
            y = yc0 + (row + 0.5) * (yc1 - yc0) / 3
            x = rnd.uniform(0, 14) * s
            while x < W - 6 * s:
                spind.append(_oval(x, y + rnd.uniform(-1, 1) * s, 5.5 * s, 1.1 * s, 0))
                x += rnd.uniform(15, 22) * s
        for row in range(2):
            y = yc1 + 3 * s + (row + 0.5) * (yl1 - yc1 - 3 * s) / 2
            x = rnd.uniform(0, 8) * s
            while x < W - 3 * s:
                dots.append(_circ(x, y + rnd.uniform(-1.2, 1.2) * s, 1.5 * s))
                x += rnd.uniform(7, 11) * s
        holder.append(_el("path", d=" ".join(spind + dots), fill=_mix(muscle, "#3A1410", 0.55), stroke="none"))
        # myenteric (Auerbach) plexus ganglia between the muscle layers
        gang = []
        for gx in (W * 0.2, W * 0.62, W * 0.9):
            gang.append(_oval(gx, yc1 + 1.5 * s, 13 * s, 4.2 * s, 0))
        holder.append(
            _el(
                "path",
                d=" ".join(gang),
                fill=_mix(nerve, "#FFFFFF", 0.35),
                stroke=_mix(nerve, "#5A3A08", 0.5),
                stroke_width=_sw(0.6 * s),
            )
        )
        holder.append(
            _el(
                "path",
                d=" ".join(
                    _circ(gx + k * 6 * s, yc1 + 1.5 * s, 2 * s)
                    for gx in (W * 0.2, W * 0.62, W * 0.9)
                    for k in (-1, 0, 1)
                ),
                fill=_mix(nerve, "#5A3A08", 0.45),
                stroke="none",
            )
        )
        # submucosa: arteriole/venule pair and a Meissner plexus ganglion
        for vx, rr, wall, lum in (
            (W * 0.08, 4.2 * s, "#C2575E", "#E8A0A4"),
            (W * 0.44, 3.4 * s, "#B0434B", "#D9737A"),
            (W * 0.51, 5 * s, "#7E5A8E", "#C9AFD3"),
            (W * 0.8, 3.8 * s, "#B0434B", "#D9737A"),
        ):
            holder.append(
                _el(
                    "ellipse",
                    cx=vx,
                    cy=(ymm + yc0) / 2 + 2.5 * s,
                    rx=rr * 1.35,
                    ry=rr,
                    fill=lum,
                    stroke=wall,
                    stroke_width=1.6 * s,
                )
            )
        holder.append(
            _el(
                "path",
                d=_oval(W * 0.3, (ymm + yc0) / 2 + 2.5 * s, 7 * s, 3 * s, 0),
                fill=_mix(nerve, "#FFFFFF", 0.35),
                stroke=_mix(nerve, "#5A3A08", 0.5),
                stroke_width=_sw(0.6 * s),
            )
        )
        ports.update(
            muscularis=(W * 0.4, (yc0 + yc1) / 2),
            longitudinal=(W * 0.4, (yc1 + yl1) / 2),
            myenteric=(W * 0.62, yc1 + 1.5 * s),
            submucosa=(W * 0.4, (ymm + yc0) / 2),
            serosa=(W * 0.4, (yl1 + H) / 2),
        )
    lact, caps = [], []
    for i, (cx, ty) in enumerate(tips):
        h_core = ybase - ty
        lact.append(_tube([(cx, ybase + 30 * s), (cx, ybase - h_core * 0.3), (cx, ty + 30 * s)], 6 * s, 5 * s)[0])
        off = (hw - T) * 0.62
        loop = [
            (cx - off, ybase + 34 * s),
            (cx - off, ybase - h_core * 0.45),
            (cx - off * 0.7, ty + T + 7 * s),
            (cx, ty + T + 3.5 * s),
            (cx + off * 0.7, ty + T + 7 * s),
            (cx + off, ybase - h_core * 0.45),
            (cx + off, ybase + 34 * s),
        ]
        caps.append(_cr(loop, 8))
    holder.append(
        _el(
            "path",
            d=" ".join(_smooth(p, closed=True) for p in lact),
            fill="#FFF8DD",
            stroke="#CDB56A",
            stroke_width=_sw(0.6 * s),
        )
    )
    capd = " ".join(_d(c, False) for c in caps)
    holder.append(
        _el(
            "path",
            d=capd,
            fill="none",
            stroke="#8E1E28",
            stroke_width=3.6 * s,
            stroke_linecap="round",
            stroke_linejoin="round",
        )
    )
    holder.append(
        _el(
            "path",
            d=capd,
            fill="none",
            stroke="#D8444C",
            stroke_width=2.2 * s,
            stroke_linecap="round",
            stroke_linejoin="round",
        )
    )
    mid_v = villi // 2
    ports.update(capillary=caps[mid_v][len(caps[mid_v]) // 3], lacteal=(tips[mid_v][0], (tips[mid_v][1] + ybase) / 2))
    holder.append(
        _el(
            "path",
            d=_d(_band(surf, 0, T)),
            fill=epithelium,
            stroke=_mix(epithelium, "#6A3A2A", 0.45),
            stroke_width=_sw(0.6 * s),
        )
    )
    holder.append(
        _el(
            "path",
            d=_d(_offset(surf, T), False),
            fill="none",
            stroke=_mix(epithelium, "#6A3A2A", 0.55),
            stroke_width=_sw(0.9 * s),
        )
    )
    cw = 7.4 * s
    nslots = int(acc[-1] / cw)
    # EEC sits on the right flank of the middle villus, low down.
    want_eec = "enteroendocrine" in cells
    cxm, tym = tips[mid_v]
    target = (cxm + hw * 0.96, ybase - (ybase - tym) * 0.38)
    eec_slot = (
        min(range(nslots), key=lambda j: math.dist(_at(surf, acc, (j + 0.5) * cw)[0], target)) if want_eec else -99
    )
    walls, nucs, gob_t, gob_n, gran, tj, brush = [], [], [], [], [], [], []
    goblet_slots = []
    next_gob = rnd.randint(3, 6)
    for j in range(nslots):
        p, n = _at(surf, acc, (j + 0.5) * cw)
        b0, nb = _at(surf, acc, j * cw)
        ang = math.atan2(n[1], n[0])
        walls.append(_d([b0, (b0[0] + nb[0] * T, b0[1] + nb[1] * T)], False))
        tj.append(_circ(b0[0] + nb[0] * 1.3 * s, b0[1] + nb[1] * 1.3 * s, 0.95 * s))
        if abs(j - eec_slot) <= 1:
            continue
        if "goblet" in cells and j == next_gob:
            next_gob = j + rnd.randint(5, 8)
            goblet_slots.append(j)
            gob_t.append(_oval(p[0] + n[0] * T * 0.4, p[1] + n[1] * T * 0.4, T * 0.42, cw * 0.62, ang))
            gob_n.append(_oval(p[0] + n[0] * T * 0.87, p[1] + n[1] * T * 0.87, T * 0.09, cw * 0.4, ang))
            for _k in range(4):
                g = rnd.uniform(-0.5, 0.5) * cw * 0.6
                d = rnd.uniform(0.2, 0.55) * T
                gran.append(_circ(p[0] + n[0] * d - n[1] * g, p[1] + n[1] * d + n[0] * g, 0.8 * s))
            continue
        if "enterocyte" in cells:
            dpt = T * (0.64 + rnd.uniform(-0.05, 0.05))
            nucs.append(_oval(p[0] + n[0] * dpt, p[1] + n[1] * dpt, T * 0.2, cw * 0.26, ang))
            # brush border: microvilli on the apical surface
            for k in (-0.3, 0, 0.3):
                bx, by = p[0] - n[1] * k * cw, p[1] + n[0] * k * cw
                brush.append(f"M{fmt(bx)} {fmt(by)} L{fmt(bx - n[0] * 2.4 * s)} {fmt(by - n[1] * 2.4 * s)}")
    holder.append(
        _el(
            "path", d=" ".join(walls), fill="none", stroke=_mix(epithelium, "#6A3A2A", 0.35), stroke_width=_sw(0.45 * s)
        )
    )
    if brush:
        holder.append(
            _el(
                "path",
                d=" ".join(brush),
                fill="none",
                stroke=_mix(epithelium, "#6A3A2A", 0.5),
                stroke_width=_sw(0.55 * s),
                stroke_linecap="round",
            )
        )
    if gob_t:
        holder.append(_el("path", d=" ".join(gob_t), fill="#EAF3F6", stroke="#7E9AA8", stroke_width=_sw(0.6 * s)))
        holder.append(_el("path", d=" ".join(gran), fill="#A9C3CF", stroke="none"))
        holder.append(_el("path", d=" ".join(gob_n), fill=_mix(nucleus, "#000000", 0.1), stroke="none"))
        p, n = _at(surf, acc, (goblet_slots[len(goblet_slots) // 2] + 0.5) * cw)
        ports["goblet"] = (p[0] + n[0] * T * 0.36, p[1] + n[1] * T * 0.36)
    if nucs:
        holder.append(
            _el(
                "path", d=" ".join(nucs), fill=nucleus, stroke=_mix(nucleus, "#000000", 0.3), stroke_width=_sw(0.35 * s)
            )
        )
        p, n = _at(surf, acc, (nslots // 3 + 0.5) * cw)
        ports["enterocyte"] = (p[0] + n[0] * T * 0.5, p[1] + n[1] * T * 0.5)
    holder.append(_el("path", d=" ".join(tj), fill="#2F2440", stroke="none"))
    p, n = _at(surf, acc, (nslots // 3) * cw)
    ports["tight_junction"] = (p[0] + n[0] * 1.3 * s, p[1] + n[1] * 1.3 * s)
    p, n = _at(surf, acc, (nslots // 4 + 0.5) * cw)
    ports["epithelium"] = (p[0] + n[0] * T * 0.5, p[1] + n[1] * T * 0.5)
    if want_eec:
        p, n = _at(surf, acc, (eec_slot + 0.5) * cw)
        tx, ty = -n[1], n[0]
        ap, ba = cw * 0.5, cw * 1.45
        depth = T * 1.08
        P = lambda u, v: (p[0] + n[0] * v + tx * u, p[1] + n[1] * v + ty * u)
        shape = [
            P(-ap, 0),
            P(-ap * 0.9, depth * 0.3),
            P(-ba, depth * 0.78),
            P(-ba * 0.8, depth),
            P(0, depth * 1.06),
            P(ba * 0.8, depth),
            P(ba, depth * 0.78),
            P(ap * 0.9, depth * 0.3),
            P(ap, 0),
        ]
        holder.append(
            _el("path", d=_smooth(shape, closed=True), fill="#F7D27A", stroke="#A9781B", stroke_width=_sw(0.8 * s))
        )
        holder.append(
            _el(
                "path",
                d=_oval(*P(0, depth * 0.45), T * 0.17, cw * 0.36, math.atan2(n[1], n[0])),
                fill=nucleus,
                stroke=_mix(nucleus, "#000000", 0.3),
                stroke_width=_sw(0.35 * s),
            )
        )
        g = []
        for k in range(16):
            u = rnd.uniform(-0.85, 0.85) * ba * 0.9
            v = depth * rnd.uniform(0.7, 0.97)
            g.append(_circ(*P(u, v), 0.95 * s))
        holder.append(_el("path", d=" ".join(g), fill="#B5462E", stroke="none"))
        mv = " ".join(
            f"M{fmt(P(u * ap, 0)[0])} {fmt(P(u * ap, 0)[1])} L{fmt(P(u * ap, -3 * s)[0])} {fmt(P(u * ap, -3 * s)[1])}"
            for u in (-0.6, 0, 0.6)
        )
        holder.append(
            _el("path", d=mv, fill="none", stroke="#A9781B", stroke_width=_sw(0.6 * s), stroke_linecap="round")
        )
        ports.update(eec=P(0, depth * 0.5), eec_base=P(0, depth * 1.06), eec_apex=P(0, 0))
        eb = P(0, depth * 1.06)
        term = (eb[0] + n[0] * 7 * s, eb[1] + n[1] * 7 * s)
    else:
        term = (tips[mid_v][0] + hw * 0.4, (tips[mid_v][1] + ybase) * 0.55)
    if immune:
        lym, lymn, mac, macn, dcs = [], [], [], [], []
        spots = []
        for i, (cx, ty) in enumerate(tips):
            spots.append(("lym", cx - hw * 0.32, ty + (ybase - ty) * 0.55))
            spots.append(("lym" if i % 2 else "mac", cx + hw * 0.3, ty + (ybase - ty) * 0.28))
        for i in range(villi - 1):
            spots.append(("mac" if i % 2 == 0 else "lym", (i + 1) * pitch + 2 * s, ymm - 7 * s))
        spots.append(("dc", tips[0][0] + hw * 0.05, ybase - 2 * s))
        for kind, x, y in spots:
            if kind == "lym":
                lym.append(_circ(x, y, 3.4 * s))
                lymn.append(_circ(x + 0.4 * s, y - 0.2 * s, 2.5 * s))
            elif kind == "mac":
                pts = [
                    (
                        x + 6.5 * s * (1 + 0.18 * math.sin(3 * t + i)) * math.cos(t),
                        y + 4.6 * s * (1 + 0.18 * math.sin(3 * t + i)) * math.sin(t),
                    )
                    for t in (2 * math.pi * k / 14 for k in range(14))
                ]
                mac.append(_smooth(pts, closed=True))
                macn.append(_oval(x - 1 * s, y, 2.6 * s, 1.7 * s, 0.4))
                ports.setdefault("immune", (x, y))
            else:
                arms = []
                for k in range(5):
                    a = -math.pi / 2 + (k - 2) * 0.75
                    L = (11 if k in (1, 2, 3) else 8) * s
                    arms.append(
                        _smooth(
                            _tube(
                                [
                                    (x, y),
                                    (x + math.cos(a) * L * 0.5, y + math.sin(a) * L * 0.5 + 1.5 * s),
                                    (x + math.cos(a) * L, y + math.sin(a) * L),
                                ],
                                3.2 * s,
                                1.2 * s,
                                per=5,
                            )[0],
                            closed=True,
                        )
                    )
                dcs.extend(arms)
                dcs.append(_circ(x, y, 4 * s))
                macn.append(_circ(x, y, 2.1 * s))
                ports["dendritic"] = (x, y)
        holder.append(_el("path", d=" ".join(mac + dcs), fill="#E7C6A6", stroke="#9C6B44", stroke_width=_sw(0.55 * s)))
        holder.append(_el("path", d=" ".join(lym), fill="#E5DDF0", stroke="#6E5A98", stroke_width=_sw(0.5 * s)))
        holder.append(_el("path", d=" ".join(lymn + macn), fill="#4B3C7A", stroke="none"))
        ports.setdefault("immune", spots[0][1:])
    fx0 = tips[mid_v][0] + 6 * s
    fiber = _cr(
        [
            (fx0 + 10 * s, H),
            (fx0 + 6 * s, ymm + 16 * s),
            (fx0, ymm - 8 * s),
            (fx0, ybase),
            (fx0 + (term[0] - fx0) * 0.3, term[1] + 14 * s),
            term,
        ],
        8,
    )
    fx0 += 10 * s
    br = []
    for da in (-0.8, 0.8):
        a = math.atan2(term[1] - fiber[-4][1], term[0] - fiber[-4][0]) + da
        e = (term[0] + math.cos(a) * 6 * s, term[1] + math.sin(a) * 6 * s)
        br.append(_d([term, e], False))
    fd = _d(fiber, False) + " " + " ".join(br)
    holder.append(
        _el(
            "path",
            d=fd,
            fill="none",
            stroke=_mix(nerve, "#5A3A08", 0.55),
            stroke_width=3.2 * s,
            stroke_linecap="round",
            stroke_linejoin="round",
        )
    )
    holder.append(
        _el(
            "path",
            d=fd,
            fill="none",
            stroke=nerve,
            stroke_width=1.9 * s,
            stroke_linecap="round",
            stroke_linejoin="round",
        )
    )
    vari = [fiber[len(fiber) * k // 6] for k in (2, 3, 4)] + [term]
    holder.append(
        _el(
            "path",
            d=" ".join(_circ(x, y, 2 * s) for x, y in vari),
            fill=nerve,
            stroke=_mix(nerve, "#5A3A08", 0.55),
            stroke_width=_sw(0.6 * s),
        )
    )
    ports.update(vagal_terminal=term, vagal_fiber=(fx0, H))
    mic_ports = []
    if lumen_microbes:
        items = _microbes(W, 8 * s, ymu + 6 * s, s, rnd, lambda q: False)
        els, mic_ports = _microbe_paths(items, s)
        holder.extend(els)
    if rich:
        look = _look()
        defs.append(_linear("lum", [("0", "#E8DCC4", 0.55), ("1", "#FFFFFF", 0)]))
        look.append(_el("rect", x=0, y=0, width=W, height=ymu, fill="url(#lum)"))
        strands = []
        for k in range(int(W / (9 * s))):
            x0 = k * 9 * s + rnd.uniform(0, 4) * s
            y0 = ymu + rnd.uniform(3, 14) * s
            pts = [(x0 + t * 3 * s, y0 + 1.6 * s * math.sin(t * 1.4 + k)) for t in range(5)]
            if not any(_inside(q, _band(surf, -1 * s, T + 2 * s)) or q[1] > ybase for q in pts):
                strands.append(_smooth(pts))
        look.append(
            _el("path", d=" ".join(strands), fill="none", stroke="#6FA592", stroke_width=0.5 * s, stroke_opacity=0.6)
        )
        defs.append(_linear("epi", [("0", "#FFFFFF", 0.35), ("1", "#7A3A2A", 0.12)]))
        look.append(_el("path", d=_d(_band(surf, 0, T)), fill="url(#epi)"))
        look.append(
            _el(
                "path",
                d=capd,
                fill="none",
                stroke="#FFFFFF",
                stroke_width=0.7 * s,
                stroke_opacity=0.55,
                stroke_linecap="round",
            )
        )
        if mic_ports:
            look.append(
                _el(
                    "path",
                    d=" ".join(_circ(x - 1 * s, y - 1 * s, 1 * s) for x, y in mic_ports),
                    fill="#FFFFFF",
                    fill_opacity=0.55,
                )
            )
        holder.append(look)
    for k, (cx, ty) in enumerate(tips):
        ports[f"villus_tip{k}"] = (cx, ty)
    for k, q in enumerate(mic_ports):
        ports[f"microbe{k}"] = q
    ports.update(
        lumen=(W * 0.5, ymu * 0.45),
        mucus=(pitch * 0.5 + hw * 1.25, ymu + 10 * s),
        lamina_propria=(tips[0][0], ybase + 22 * s),
        crypt=(pitch, ycrypt - 6 * s),
    )
    return _finish(holder, defs, Box(0, 0, W, H), **ports)


def _branch(rnd, x, y, ang, L, w, depth, out, tips, spread=0.55):
    """Recursive tapering dendrite: appends (polyline, w0, w1) to out and the tips to tips."""
    n = 4
    pts = [(x, y)]
    a = ang
    for k in range(1, n + 1):
        a += rnd.uniform(-0.28, 0.28)
        pts.append((pts[-1][0] + math.cos(a) * L / n, pts[-1][1] + math.sin(a) * L / n))
    w1 = max(w * 0.55, 0.7)
    out.append((pts, w, w1))
    if depth <= 0:
        tips.append(pts[-1])
        return
    ex, ey = pts[-1]
    for sgn in (-1, 1):
        _branch(
            rnd,
            ex,
            ey,
            a + sgn * spread * rnd.uniform(0.7, 1.15),
            L * rnd.uniform(0.6, 0.75),
            w1,
            depth - 1,
            out,
            tips,
            spread,
        )


def _taper(pts, w0, w1):
    c = _cr(pts, 5)
    n = len(c)
    ws = [(w0 + (w1 - w0) * i / (n - 1)) / 2 for i in range(n)]
    return _smooth(_offset(c, ws) + _offset(c, [-w for w in ws])[::-1], closed=True)


def _boutons(rnd, x, y, ang, L, s, out_lines, out_b, tips):
    """Axon terminal arbor ending in synaptic boutons."""
    for k, da in enumerate((-0.55, -0.15, 0.25, 0.6)):
        a = ang + da
        m = (x + math.cos(ang) * L * 0.35, y + math.sin(ang) * L * 0.35)
        e = (m[0] + math.cos(a) * L * 0.65, m[1] + math.sin(a) * L * 0.65)
        out_lines.append(_smooth([(x, y), m, ((m[0] + e[0]) / 2 + rnd.uniform(-1, 1) * s, (m[1] + e[1]) / 2), e]))
        out_b.append(e)
        tips.append(e)


def _myelinated(c, s, r_ax, r_my, node_gap, internode, myelin):
    """Axon core path and myelin segments along polyline c; returns (axon_d, [segment polygons], [node points])."""
    acc = _arclen(c)
    axon = _smooth(_offset(c, r_ax) + _offset(c, -r_ax)[::-1], closed=True)
    segs, nodes = [], []
    if myelin:
        pos = node_gap
        while pos + internode * 0.6 < acc[-1]:
            end = min(acc[-1] - node_gap * 0.2, pos + internode)
            sub = [_at(c, acc, pos + (end - pos) * k / 10)[0] for k in range(11)]
            segs.append(_offset(sub, r_my) + _offset(sub, -r_my)[::-1])
            nodes.append(_at(c, acc, end + node_gap / 2)[0])
            pos = end + node_gap
        nodes = nodes[:-1] if nodes and _arclen(c)[-1] - acc[-1] < 0 else nodes
    return axon, segs, nodes


def _round_seg(poly, r):
    """Smooth closed outline for a myelin segment polygon (rounded ends)."""
    n = len(poly) // 2
    top, bot = poly[:n], poly[n:]
    a, b = top[-1], bot[0]
    c, d = bot[-1], top[0]
    mid1 = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    mid2 = ((c[0] + d[0]) / 2, (c[1] + d[1]) / 2)
    tx, ty = mid1[0] - mid2[0], mid1[1] - mid2[1]
    L = math.hypot(tx, ty) or 1
    tx, ty = tx / L * r * 0.5, ty / L * r * 0.5
    return _smooth(top + [(mid1[0] + tx, mid1[1] + ty)] + bot + [(mid2[0] - tx, mid2[1] - ty)], closed=True)


@_drawing_api(
    "parts",
    purpose='神经元（教科书级）：带核与尼氏体的胞体、逐级分叉的树突、轴丘与轴突、髓鞘节段与郎飞结、轴突末梢突触小结；kind="pseudounipolar" 为背根/结状神经节式感觉神经元（T 形分叉，胞体包在卫星细胞神经节内），适合画迷走传入。',
    returns="Geometry（原点在中心；端口 soma/nucleus/axon_hillock/axon/axon_end/node{k}/terminal{k}/dendrite{k}，假单极另有 peripheral/peripheral_end/central/ganglion）",
    semantics=(
        "length 为整体长度（沿 x 方向，胞体在左；假单极胞体在上方，外周支向左、中枢支向右）；myelin=False 画无髓纤维。",
        "ganglion=True 给胞体包神经节被膜与卫星细胞（假单极默认开启）；terminals=False 去掉末梢（纤维由 connect 续接时用）；color/myelin_color 改色。",
        '与其他部件相接：外周支末端 peripheral_end 接肠壁 vagal_terminal，中枢端 axon_end 接脑干 nts，用同色 d.connect(route="bezier") 补足纤维。',
        'style="rich" 加明暗、尼氏体与髓鞘高光（一个局部 SVG）；"flat" 全原生。',
    ),
    example='v = d.place(neuron(360, kind="pseudounipolar"), at=(450, 200), key="vagus")\n'
    'd.callout("ng", "结状神经节", v.port("ganglion"), at=(420, 60), font_size=12)',
    rank=25,
)
def neuron(
    length=320,
    *,
    kind="multipolar",
    myelin=True,
    ganglion=None,
    terminals=True,
    color="#E2A93B",
    myelin_color="#F4EBD0",
    nucleus="#6A5796",
    style="rich",
    seed=3,
):
    rich = _style(style)
    _finite(length)
    if kind not in ("multipolar", "bipolar", "pseudounipolar"):
        raise ValueError('kind must be "multipolar", "bipolar" or "pseudounipolar"')
    ganglion = (kind == "pseudounipolar") if ganglion is None else bool(ganglion)
    rnd = random.Random(seed)
    L = float(length)
    s = L / 320.0
    holder, defs = _el("g"), _el("defs")
    holder.append(defs)
    ports = {}
    edge = _mix(color, "#4A2E08", 0.55)
    r_ax, r_my = 1.8 * s, 4.6 * s
    gap, inter = 3.2 * s, 26 * s
    soma_r = 15 * s
    pts_all = []
    procs, tips, lines, bout, btips = [], [], [], [], []
    axon_lines = []  # polylines that get an axon (+ myelin)
    if kind == "pseudounipolar":
        sx, sy = 0.0, -34 * s
        y0 = 22 * s
        tj = (0.0, y0)
        stem = _cr(
            [(sx, sy + soma_r * 0.9), (sx - 6 * s, sy + 26 * s), (sx + 5 * s, y0 - 18 * s), (sx, y0 - 6 * s), tj], 6
        )
        periph = _cr([tj, (-L * 0.2, y0 + 2 * s), (-L * 0.38, y0 - 3 * s), (-L * 0.48, y0 + 1 * s)], 10)
        central = _cr([tj, (L * 0.2, y0 + 2 * s), (L * 0.38, y0 - 3 * s), (L * 0.44, y0 + 1 * s)], 10)
        axon_lines = [stem, periph, central]
        # peripheral sensory endings (free/branched endings) and central boutons
        pe = periph[-1]
        for da in (-0.5, -0.1, 0.35) if terminals else ():
            a = math.pi + da
            m = (pe[0] - 6 * s, pe[1] + da * 4 * s)
            e = (m[0] + math.cos(a) * 12 * s, m[1] + math.sin(a) * 12 * s)
            lines.append(_smooth([pe, m, e]))
            tips.append(e)
        if terminals:
            _boutons(rnd, central[-1][0], central[-1][1], 0, 22 * s, s, lines, bout, btips)
        ports.update(
            peripheral=periph[len(periph) // 2], peripheral_end=pe, central=central[len(central) // 2], t_junction=tj
        )
    else:
        sx, sy = (-L / 2 + 52 * s) if kind == "multipolar" else (-L * 0.12), 0.0
        if kind == "multipolar":
            for k, a in enumerate((math.pi - 0.2, math.pi + 0.65, -1.8, 1.9, math.pi * 0.72, -2.6)):
                _branch(
                    rnd,
                    sx + math.cos(a) * soma_r * 0.8,
                    sy + math.sin(a) * soma_r * 0.8,
                    a,
                    22 * s,
                    5.2 * s,
                    2,
                    procs,
                    tips,
                )
        else:
            _branch(rnd, sx - soma_r * 0.9, sy, math.pi, L * 0.16, 4.6 * s, 2, procs, tips, spread=0.5)
        x0 = sx + soma_r
        x1 = L / 2 - 26 * s
        ax = _cr([(x0, sy), (x0 + (x1 - x0) * 0.3, sy - 4 * s), (x0 + (x1 - x0) * 0.65, sy + 4 * s), (x1, sy)], 10)
        axon_lines = [ax]
        if terminals:
            _boutons(rnd, x1, sy, 0, 24 * s, s, lines, bout, btips)
    first = True
    if ganglion:
        g_rx, g_ry = 30 * s, 26 * s
        cap = _el(
            "ellipse",
            cx=sx,
            cy=sy,
            rx=g_rx,
            ry=g_ry,
            fill=_mix(color, "#FFFFFF", 0.8),
            stroke=_mix(color, "#5A3A08", 0.4),
            stroke_width=_sw(1 * s),
            data_outline="1",
        )
        holder.append(cap)
        first = False
        # neighbouring neuron somata (ghosted) to read as a ganglion
        ghosts = [
            (sx - 20 * s, sy - 9 * s, 6 * s),
            (sx + 20 * s, sy - 8 * s, 6.5 * s),
            (sx - 19 * s, sy + 11 * s, 5.5 * s),
            (sx + 20 * s, sy + 11 * s, 5 * s),
            (sx - 4 * s, sy - 20.5 * s, 4.5 * s),
            (sx + 9 * s, sy - 20 * s, 4 * s),
        ]
        holder.append(
            _el(
                "path",
                d=" ".join(_circ(*g) for g in ghosts),
                fill=_mix(color, "#FFFFFF", 0.55),
                stroke=_mix(color, "#5A3A08", 0.25),
                stroke_width=_sw(0.5 * s),
            )
        )
        holder.append(
            _el(
                "path",
                d=" ".join(_circ(x - r * 0.15, y, r * 0.38) for x, y, r in ghosts),
                fill=_mix(nucleus, "#FFFFFF", 0.5),
                stroke="none",
            )
        )
        sat = [
            _oval(sx + soma_r * 1.2 * math.cos(t), sy + soma_r * 1.12 * math.sin(t), 2.4 * s, 1 * s, t + math.pi / 2)
            for t in (2 * math.pi * k / 9 + 0.3 for k in range(9))
        ]
        holder.append(_el("path", d=" ".join(sat), fill=_mix(nucleus, "#FFFFFF", 0.15), stroke="none"))
        ports["ganglion"] = (sx - g_rx * 0.7, sy - g_ry * 0.7)
        pts_all += [(sx - g_rx, sy - g_ry), (sx + g_rx, sy + g_ry)]
    if procs:
        dd = " ".join(_taper(p, w0, w1) for p, w0, w1 in procs)
        attrs = dict(d=dd, fill=color, stroke=edge, stroke_width=_sw(0.6 * s))
        if first:
            attrs["data_outline"] = "1"
            first = False
        holder.append(_el("path", **attrs))
        for p, _, _ in procs:
            pts_all += p
    segs_all, nodes_all = [], []
    axd = []
    for c in axon_lines:
        a_d, segs, nodes = _myelinated(
            c, s, r_ax, r_my, gap, inter, myelin and c is not axon_lines[0] or (myelin and kind != "pseudounipolar")
        )
        axd.append(a_d)
        segs_all += segs
        nodes_all += nodes
        pts_all += _offset(c, r_my) + _offset(c, -r_my)
    attrs = dict(d=" ".join(axd), fill=color, stroke=edge, stroke_width=_sw(0.6 * s))
    if first:
        attrs["data_outline"] = "1"
        first = False
    holder.append(_el("path", **attrs))
    if lines:
        holder.append(
            _el("path", d=" ".join(lines), fill="none", stroke=edge, stroke_width=2.6 * s, stroke_linecap="round")
        )
        holder.append(
            _el("path", d=" ".join(lines), fill="none", stroke=color, stroke_width=1.6 * s, stroke_linecap="round")
        )
        for t in tips + btips:
            pts_all.append(t)
    if segs_all:
        holder.append(
            _el(
                "path",
                d=" ".join(_round_seg(p, r_my) for p in segs_all),
                fill=myelin_color,
                stroke=_mix(myelin_color, "#6A5020", 0.5),
                stroke_width=_sw(0.6 * s),
            )
        )
        # Schwann cell nuclei on a few internodes
        sn = []
        for k, p in enumerate(segs_all[::2]):
            m = p[len(p) // 4]
            sn.append(_oval(m[0], m[1] - 0.6 * s, 3.4 * s, 1.1 * s, 0))
        holder.append(_el("path", d=" ".join(sn), fill=_mix(nucleus, "#FFFFFF", 0.2), stroke="none"))
    if bout:
        holder.append(
            _el(
                "path",
                d=" ".join(_circ(x, y, 3.3 * s) for x, y in bout),
                fill=color,
                stroke=edge,
                stroke_width=_sw(0.7 * s),
            )
        )
        holder.append(
            _el(
                "path",
                d=" ".join(_circ(x + 0.4 * s, y + 0.3 * s, 0.75 * s) for x, y in bout for _ in (0,))
                + " "
                + " ".join(_circ(x - 1.2 * s, y - 0.6 * s, 0.6 * s) for x, y in bout),
                fill=_mix(color, "#FFFFFF", 0.7),
                stroke="none",
            )
        )
        pts_all += [(x + 3.5 * s, y + 3.5 * s) for x, y in bout] + [(x - 3.5 * s, y - 3.5 * s) for x, y in bout]
    if kind == "pseudounipolar":
        soma = [
            (sx + soma_r * math.cos(t), sy + soma_r * 0.92 * math.sin(t))
            for t in (2 * math.pi * k / 20 for k in range(20))
        ]
        hill = (sx, sy + soma_r * 0.92)
    else:
        soma = []
        for k in range(24):
            t = 2 * math.pi * k / 24
            r = soma_r * (1 + 0.1 * math.cos(3 * t + 0.5))
            soma.append((sx + r * math.cos(t), sy + r * 0.9 * math.sin(t)))
        soma[0] = (sx + soma_r * 1.35, sy)
        hill = (sx + soma_r * 1.35, sy)
    if ganglion:
        holder.append(
            _el(
                "path",
                d=_smooth([(sx + (x - sx) * 1.28, sy + (y - sy) * 1.28) for x, y in soma], closed=True),
                fill="none",
                stroke=_mix(color, "#5A3A08", 0.35),
                stroke_width=_sw(0.6 * s),
            )
        )
    holder.append(_el("path", d=_smooth(soma, closed=True), fill=color, stroke=edge, stroke_width=_sw(0.9 * s)))
    nx, ny = sx - 1.5 * s, sy - 0.5 * s
    pts_all += soma
    if rich:
        look = _look()
        defs.append(_radial("nsoma", _mix(color, "#FFFFFF", 0.55), _mix(color, "#7A4A08", 0.25)))
        look.append(_el("path", d=_smooth(soma, closed=True), fill="url(#nsoma)", fill_opacity=0.85))
        nissl = []
        for k in range(14):
            a, rr = rnd.uniform(0, 2 * math.pi), rnd.uniform(0.62, 0.88) * soma_r
            nissl.append(_oval(sx + rr * math.cos(a), sy + rr * 0.85 * math.sin(a), 1.4 * s, 0.7 * s, a))
        look.append(_el("path", d=" ".join(nissl), fill=_mix(color, "#5A2A08", 0.55), fill_opacity=0.7))
        if segs_all:
            hl = []
            for p in segs_all:
                n = len(p) // 2
                top = p[:n]
                hl.append(_d([(x, y + r_my * 0.45) for x, y in top[1:-1]], False))
            look.append(
                _el(
                    "path",
                    d=" ".join(hl),
                    fill="none",
                    stroke="#FFFFFF",
                    stroke_width=1.3 * s,
                    stroke_opacity=0.75,
                    stroke_linecap="round",
                )
            )
        if ganglion:
            defs.append(_radial("gcap", "#FFFFFF", _mix(color, "#7A4A08", 0.15)))
            look.append(_el("ellipse", cx=sx, cy=sy, rx=30 * s, ry=26 * s, fill="url(#gcap)", fill_opacity=0.35))
        holder.append(look)
    holder.append(
        _el(
            "ellipse",
            cx=nx,
            cy=ny,
            rx=6.4 * s,
            ry=5.8 * s,
            fill=_mix(nucleus, "#FFFFFF", 0.45),
            stroke=_mix(nucleus, "#000000", 0.2),
            stroke_width=_sw(0.6 * s),
        )
    )
    holder.append(_el("circle", cx=nx + 1.4 * s, cy=ny - 1 * s, r=1.9 * s, fill=nucleus, stroke="none"))
    ports.update(soma=(sx, sy), nucleus=(nx, ny), axon_hillock=hill)
    main = axon_lines[-1]
    ports["axon"] = main[len(main) // 2]
    ports["axon_end"] = btips[len(btips) // 2] if btips else main[-1]
    for k, p in enumerate(nodes_all):
        ports[f"node{k}"] = p
    for k, p in enumerate(btips):
        ports[f"terminal{k}"] = p
    for k, p in enumerate(tips):
        ports[f"dendrite{k}"] = p
    xs, ys = [p[0] for p in pts_all], [p[1] for p in pts_all]
    pad = 1.5 * s
    return _finish(
        holder,
        defs,
        Box(min(xs) - pad, min(ys) - pad, max(xs) - min(xs) + 2 * pad, max(ys) - min(ys) + 2 * pad),
        **ports,
    )


# Normalized frames (300 × ~240 units, anterior = left). Control points traced from textbook atlases.
_SAG = dict(
    cerebrum=[
        (10, 112),
        (14, 80),
        (34, 46),
        (70, 20),
        (115, 7),
        (165, 6),
        (212, 16),
        (250, 38),
        (276, 68),
        (291, 102),
        (292, 128),
        (282, 142),
        (258, 147),
        (232, 146),
        (206, 141),
        (186, 140),
        (170, 138),
        (150, 141),
        (130, 143),
        (112, 142),
        (88, 140),
        (58, 137),
        (30, 131),
        (14, 124),
    ],
    callosum=[
        (84, 104),
        (74, 92),
        (78, 76),
        (96, 63),
        (128, 55),
        (162, 55),
        (194, 62),
        (214, 75),
        (218, 88),
        (208, 96),
    ],
    cingulate=[(60, 128), (52, 102), (58, 72), (82, 48), (122, 36), (166, 36), (196, 42)],
    marginal=[(196, 42), (206, 30), (212, 17)],
    parieto_occ=[(252, 40), (244, 64), (230, 86), (214, 102)],
    calcarine=[(214, 102), (238, 112), (262, 118), (290, 120)],
    paracentral=[(140, 36), (146, 22), (150, 7)],
    thalamus=(156, 101, 25, 15),
    brainstem=[
        (164, 132),
        (184, 132),
        (190, 146),
        (188, 162),
        (184, 178),
        (182, 196),
        (180, 222),
        (178, 238),
        (162, 238),
        (160, 222),
        (154, 206),
        (142, 196),
        (134, 180),
        (136, 162),
        (148, 150),
    ],
    cerebellum=(222, 182, 52, 36),
)
_LAT = dict(
    cerebrum=[
        (10, 108),
        (14, 76),
        (34, 44),
        (70, 18),
        (116, 6),
        (166, 5),
        (214, 16),
        (252, 38),
        (278, 68),
        (292, 102),
        (292, 128),
        (282, 144),
        (262, 152),
        (238, 156),
        (214, 166),
        (190, 176),
        (160, 182),
        (126, 178),
        (98, 168),
        (82, 152),
        (80, 138),
        (64, 136),
        (40, 132),
        (18, 124),
    ],
    lateral=[(84, 140), (110, 126), (146, 112), (180, 102), (206, 96), (220, 82)],
    central=[(176, 6), (170, 22), (162, 38), (158, 54), (150, 72), (146, 90), (138, 106)],
    precentral=[(150, 10), (145, 28), (136, 46), (132, 64), (124, 82), (120, 100)],
    postcentral=[(198, 14), (192, 32), (184, 50), (180, 68), (172, 86)],
    sup_frontal=[(52, 40), (80, 34), (108, 32), (132, 36)],
    inf_frontal=[(30, 92), (58, 82), (88, 76), (118, 72)],
    sup_temporal=[(100, 154), (132, 142), (164, 132), (196, 120), (226, 104)],
    intraparietal=[(186, 62), (212, 58), (236, 66), (258, 82)],
    brainstem=[
        (176, 172),
        (204, 168),
        (210, 182),
        (206, 200),
        (202, 222),
        (200, 240),
        (182, 240),
        (180, 220),
        (176, 200),
        (172, 186),
    ],
    cerebellum=(240, 182, 48, 30),
)


def _poly_at(pts, frac):
    acc = _arclen(pts)
    return _at(pts, acc, acc[-1] * frac)[0]


def _near(p, samples, d):
    return any((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 < d * d for q in samples)


def _gyral_texture(outline, s, rnd, keep, avoid_pts, *, spacing=6.0, n=120, step=1.8, max_len=44):
    """Gyral folding pattern: sinuous sulci that start just inside the rim and run inward, plus interior meanders."""
    taken = list(avoid_pts)
    curves = []
    gap = spacing * s
    xs, ys = [p[0] for p in outline], [p[1] for p in outline]
    cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
    starts = []
    for k in range(0, len(outline), 2):  # rim seeds, pointing inward
        p, q = outline[k], outline[(k + 1) % len(outline)]
        nx, ny = -(q[1] - p[1]), q[0] - p[0]
        L = math.hypot(nx, ny) or 1
        nx, ny = nx / L, ny / L
        if (cx - p[0]) * nx + (cy - p[1]) * ny < 0:
            nx, ny = -nx, -ny
        starts.append(((p[0] + nx * 3.2 * s, p[1] + ny * 3.2 * s), math.atan2(ny, nx)))
    rnd.shuffle(starts)
    for _ in range(n * 3):
        starts.append(((rnd.uniform(min(xs), max(xs)), rnd.uniform(min(ys), max(ys))), rnd.uniform(0, 2 * math.pi)))
    for p, a in starts:
        if len(curves) >= n:
            break
        if not keep(p) or _near(p, taken, gap * 1.05):
            continue
        turn = rnd.uniform(-0.2, 0.2)
        pts = [p]
        target = rnd.uniform(16, max_len) * s
        walked = 0.0
        phase = rnd.uniform(0, 6.3)
        while walked < target:
            turn = 0.8 * turn + rnd.uniform(-0.12, 0.12) + 0.05 * math.sin(phase + walked / (4 * s))
            a += turn
            q = (pts[-1][0] + math.cos(a) * step * s, pts[-1][1] + math.sin(a) * step * s)
            if not keep(q) or _near(q, taken, gap):
                break
            pts.append(q)
            walked += step * s
        if walked >= 6 * s:
            curves.append(pts)
            taken.extend(pts)
    return curves


def _sulcus(pts, wmax):
    """Tapered filled sulcus (thin at both ends) — reads like an inked anatomical drawing."""
    c = _cr(pts[::2] if len(pts) > 6 else pts, 4)
    n = len(c)
    if n < 3:
        return ""
    ws = [wmax * (0.18 + 0.82 * max(0.0, math.sin(math.pi * i / (n - 1))) ** 0.7) / 2 for i in range(n)]
    return _smooth(_offset(c, ws) + _offset(c, [-w for w in ws])[::-1], closed=True)


@_drawing_api(
    "parts",
    purpose='大脑（教科书级）：view="sagittal" 正中矢状面（扣带回与主要沟、胼胝体、侧脑室、穹窿、丘脑、下丘脑与垂体、中脑/脑桥/延髓、带小叶与“生命树”白质的小脑）；"lateral" 外侧面（中央沟、外侧裂、额/颞/顶/枕叶脑回、小脑叶片、脑干）。regions 高亮指定脑区。',
    returns="Geometry（原点在中心；端口为各脑区名：prefrontal/hippocampus/amygdala/hypothalamus/thalamus/brainstem/nts/cerebellum/pituitary/callosum/vagus 等，详见 semantics）",
    semantics=(
        "width 为宽度（高≈0.8×宽），前（额叶）在左；整体为原生形状，沟回为原生线条。",
        "矢状面端口：prefrontal/cingulate/callosum/thalamus/hypothalamus/pituitary/hippocampus/amygdala/midbrain/pons/medulla/brainstem/nts/vagus/cerebellum/occipital；"
        "外侧面端口：prefrontal/motor/parietal/temporal/occipital/insula/hippocampus/amygdala/brainstem/nts/vagus/cerebellum。",
        "regions 为脑区名列表或 {名称: 颜色}，在该区域铺色并描边（海马、杏仁核为投影示意）；未列出的区域仍有端口。",
        "另有皮层小区端口/可高亮：矢状面 mpfc/acc/pcc/precuneus，外侧面 dlpfc/vlpfc/ipl；把外侧面脑区用在 sagittal（或反之）会报错并提示换 view。",
        '网络连接：nodes=[(脑区名或 (u, v) 比例坐标, 标签, 值)]（圆点大小∝|值|，红▲为升高、蓝▼为降低），edges=[(标签a, 标签b, 权重, "+"/"-")]（红实线正连接、蓝虚线负连接，线宽∝|权重|，向外弯）；标签自动放在点旁不压点，端口 node_标签。',
        "vagus 端口在延髓前外侧（迷走神经出脑处），nts（孤束核）在延髓背侧——迷走传入纤维接 vagus 或 nts。",
        'style="rich" 加明暗与沟回高光（一个局部 SVG）；"flat" 全原生。',
    ),
    example='b = d.place(brain(300, regions={"nts": "#E07A3C", "hypothalamus": "#5E8FC2"}), at=(700, 200), key="brain")\n'
    'd.callout("nts", "孤束核", b.port("nts"), at=(820, 330), font_size=12)',
    rank=26,
)
def brain(
    width=300,
    *,
    view="sagittal",
    regions=None,
    nodes=None,
    edges=None,
    color="#F0C3BE",
    white="#FAF1EA",
    font_size=None,
    style="rich",
    seed=6,
):
    rich = _style(style)
    _finite(width)
    if view not in ("sagittal", "lateral"):
        raise ValueError('view must be "sagittal" or "lateral"')
    rnd = random.Random(seed)
    s = width / 300.0
    P = lambda pts: [(x * s, y * s) for x, y in pts]
    F = _SAG if view == "sagittal" else _LAT
    if isinstance(regions, dict):
        tint = dict(regions)
    else:
        palette = ("#E07A3C", "#5E8FC2", "#7DB37A", "#B56FB0", "#D4B54A", "#4FA9A2", "#C4566A")
        tint = {r: palette[k % len(palette)] for k, r in enumerate(regions or ())}
    known = _BRAIN_REGIONS[view]
    node_regions = {n[0] for n in (nodes or ()) if isinstance(n[0], str)}
    bad = (set(tint) | node_regions) - known
    if bad:
        other = "lateral" if view == "sagittal" else "sagittal"
        wrong = sorted(bad & _BRAIN_REGIONS[other])
        if wrong:
            raise ValueError(
                f'{wrong} lie on the {other} surface and are not visible in view="{view}": use view="{other}", '
                f"or two brains (sagittal + lateral) side by side; {view} regions are {sorted(known)}"
            )
        raise ValueError(f"unknown {view} brain regions {sorted(bad)}; use {sorted(known)}")
    edge = _mix(color, "#5A2028", 0.55)
    sulc = _mix(color, "#6A2030", 0.5)
    holder, defs = _el("g"), _el("defs")
    holder.append(defs)
    ports = {}
    outline = _cr(P(F["cerebrum"]), 8)
    outline = outline[:-1]
    cer_d = _smooth(outline, closed=True)
    bounds_pts = list(outline)
    ccx, ccy, crx, cry = F["cerebellum"]
    ccx, ccy, crx, cry = ccx * s, ccy * s, crx * s, cry * s
    cb_out = []
    for k in range(96):
        t = 2 * math.pi * k / 96
        r = 1 + 0.035 * abs(math.sin(t * 12)) - 0.06 * max(0, math.cos(t - 2.6)) ** 6
        cb_out.append((ccx + crx * r * math.cos(t), ccy + cry * r * math.sin(t)))
    cb_col = tint.get("cerebellum", _mix(color, "#C98A70", 0.25))
    cb_edge = _mix(cb_col, "#5A2028", 0.5)
    holder.append(
        _el(
            "path",
            d=_smooth(cb_out, closed=True),
            fill=_mix(cb_col, "#FFFFFF", 0.1) if "cerebellum" in tint else cb_col,
            stroke=cb_edge,
            stroke_width=_sw(1.1 * s),
            data_outline="1",
        )
    )
    bounds_pts += cb_out
    if view == "sagittal":
        # arbor vitae: white-matter tree fanning out from the hilum by the fourth ventricle
        hx, hy = ccx - crx * 0.62, ccy + cry * 0.02
        trees, fiss = [], []
        angs = [-2.2, -1.65, -1.15, -0.7, -0.25, 0.2, 0.65, 1.1, 1.55]
        for j, a in enumerate(angs):
            L = math.hypot(crx * math.cos(a), cry * math.sin(a)) * 0.95
            ex = (ccx + crx * 0.8 * math.cos(a), ccy + cry * 0.8 * math.sin(a))
            base = (hx, hy)
            mid = (base[0] + (ex[0] - base[0]) * 0.5, base[1] + (ex[1] - base[1]) * 0.5)
            trees.append(_smooth(_tube([base, mid, ex], 5.5 * s, 1.6 * s, per=5)[0], closed=True))
            for sg in (-1, 1):
                q = (mid[0] + (ex[0] - mid[0]) * 0.35, mid[1] + (ex[1] - mid[1]) * 0.35)
                aa = math.atan2(ex[1] - mid[1], ex[0] - mid[0]) + sg * 0.55
                e2 = (q[0] + math.cos(aa) * L * 0.28, q[1] + math.sin(aa) * L * 0.28)
                trees.append(_smooth(_tube([q, e2], 2.2 * s, 0.9 * s, per=4)[0], closed=True))
            if j < len(angs) - 1:
                b = (a + angs[j + 1]) / 2
                o = (ccx + crx * 1.02 * math.cos(b), ccy + cry * 1.02 * math.sin(b))
                i_ = (ccx + crx * 0.45 * math.cos(b), ccy + cry * 0.45 * math.sin(b))
                fiss.append(_d([o, ((o[0] + i_[0]) / 2, (o[1] + i_[1]) / 2), i_], False))
        holder.append(
            _el(
                "path", d=" ".join(fiss), fill="none", stroke=cb_edge, stroke_width=_sw(0.9 * s), stroke_linecap="round"
            )
        )
        holder.append(
            _el("path", d=" ".join(trees), fill=white, stroke=_mix(cb_col, "#5A2028", 0.25), stroke_width=_sw(0.4 * s))
        )
    else:
        fol = []
        for k in range(1, 9):
            yy = ccy - cry + 2 * cry * k / 9
            half = crx * math.sqrt(max(0, 1 - ((yy - ccy) / cry) ** 2)) * 0.94
            pts = [(ccx - half + 2 * half * t / 12, yy + 1.3 * s * math.sin(t * 1.3 + k)) for t in range(13)]
            fol.append(_smooth(pts))
        holder.append(
            _el("path", d=" ".join(fol), fill="none", stroke=cb_edge, stroke_width=_sw(0.8 * s), stroke_linecap="round")
        )
    ports["cerebellum"] = (ccx + crx * 0.25, ccy + cry * 0.1)
    bs = _cr(P(F["brainstem"]) + P(F["brainstem"][:1]), 6)[:-1]
    bs_col = tint.get("brainstem", _mix(color, "#D9A88A", 0.35))
    holder.append(
        _el(
            "path",
            d=_smooth(bs, closed=True),
            fill=_mix(bs_col, "#FFFFFF", 0.1) if "brainstem" in tint else bs_col,
            stroke=_mix(bs_col, "#5A2028", 0.5),
            stroke_width=_sw(1 * s),
        )
    )
    bounds_pts += bs
    holder.append(_el("path", d=cer_d, fill=color, stroke=edge, stroke_width=_sw(1.3 * s)))
    region_els = []

    def tint_poly(name, poly):
        if name in tint:
            c = tint[name]
            region_els.append(
                _el(
                    "path",
                    d=_d(poly),
                    fill=c,
                    fill_opacity=0.55,
                    stroke=c,
                    stroke_width=_sw(1.2 * s),
                    stroke_opacity=0.9,
                )
            )

    ins = lambda p: _inside(p, outline)
    major = []
    if view == "sagittal":
        cc_line = _cr(P(F["callosum"]), 8)
        cing = _cr(P(F["cingulate"]), 8)
        # prefrontal tint: frontal cortex anterior to x≈78 (clip the outline)
        pf = _clip_half(outline, 1, 0.25, 92 * s)
        tint_poly("prefrontal", pf)
        occ = _clip_half(outline, -1, -0.5, -(258 * s))
        tint_poly("occipital", occ)
        # cingulate gyrus: band between the callosum and the cingulate sulcus
        if "cingulate" in tint:
            tint_poly("cingulate", _offset(cing[3:-3], 1.5 * s)[::-1] + _offset(cc_line[2:-2], -5 * s))
        # medial-surface core (diencephalon) fill under the callosum
        core = P(
            [
                (86, 104),
                (110, 92),
                (150, 82),
                (196, 86),
                (210, 98),
                (196, 120),
                (178, 132),
                (150, 138),
                (122, 136),
                (100, 128),
                (88, 116),
            ]
        )
        holder.append(_el("path", d=_smooth(core, closed=True), fill=_mix(color, "#E8B8A0", 0.35), stroke="none"))
        lv = _offset(cc_line[6:-14], 7.5 * s) + _offset(cc_line[6:-14], 15 * s)[::-1]
        holder.append(
            _el(
                "path",
                d=_smooth(lv, closed=True),
                fill="#CFE3EE",
                stroke=_mix("#CFE3EE", "#2A5070", 0.45),
                stroke_width=_sw(0.6 * s),
            )
        )
        fx = _cr(P([(206, 98), (186, 88), (150, 84), (124, 90), (112, 104), (114, 120)]), 6)
        holder.append(
            _el("path", d=_d(fx, False), fill="none", stroke=white, stroke_width=4.2 * s, stroke_linecap="round")
        )
        # corpus callosum: variable-width band (thick genu and splenium)
        n = len(cc_line)
        ws = [
            s
            * (
                5.5
                + 3.2 * math.exp(-(((i / (n - 1) - 0.1) / 0.12) ** 2))
                + 3.8 * math.exp(-(((i / (n - 1) - 0.92) / 0.1) ** 2))
            )
            for i in range(n)
        ]
        ccb = _offset(cc_line, ws) + _offset(cc_line, [-w for w in ws])[::-1]
        holder.append(
            _el(
                "path",
                d=_smooth(ccb, closed=True),
                fill=tint.get("callosum", white),
                stroke=_mix(color, "#5A2028", 0.4),
                stroke_width=_sw(0.8 * s),
            )
        )
        tx, ty, trx, try_ = F["thalamus"]
        th = [
            (tx * s + trx * s * math.cos(t) * (1 + 0.08 * math.cos(2 * t)), ty * s + try_ * s * math.sin(t))
            for t in (2 * math.pi * k / 30 for k in range(30))
        ]
        holder.append(
            _el(
                "path",
                d=_smooth(th, closed=True),
                fill=tint.get("thalamus", _mix(color, "#C9906E", 0.35)),
                stroke=_mix(color, "#5A2028", 0.45),
                stroke_width=_sw(0.8 * s),
            )
        )
        # hypothalamus + pituitary (stalk and gland) + optic chiasm + mammillary body
        hyp = P([(116, 121), (130, 117), (140, 124), (138, 135), (128, 139), (117, 135)])
        hc = tint.get("hypothalamus", _mix(color, "#B97A6A", 0.35))
        holder.append(
            _el(
                "path",
                d=_smooth(hyp, closed=True),
                fill=hc,
                stroke=_mix(hc, "#4A1A20", 0.45),
                stroke_width=_sw(0.8 * s),
            )
        )
        pit_c = tint.get("pituitary", "#E3B07E")
        holder.append(
            _el(
                "path",
                d=_d(P([(124, 140), (122, 150)]), False),
                fill="none",
                stroke=_mix(pit_c, "#5A3010", 0.4),
                stroke_width=2.4 * s,
                stroke_linecap="round",
            )
        )
        holder.append(
            _el(
                "ellipse",
                cx=121 * s,
                cy=154 * s,
                rx=6.5 * s,
                ry=4.6 * s,
                fill=pit_c,
                stroke=_mix(pit_c, "#5A3010", 0.45),
                stroke_width=_sw(0.7 * s),
            )
        )
        holder.append(
            _el(
                "ellipse",
                cx=106 * s,
                cy=140 * s,
                rx=4.5 * s,
                ry=2.6 * s,
                fill=white,
                stroke=_mix(color, "#5A2028", 0.45),
                stroke_width=_sw(0.6 * s),
            )
        )
        holder.append(_el("circle", cx=146 * s, cy=135 * s, r=2.6 * s, fill=_mix(color, "#B97A6A", 0.5), stroke="none"))
        bounds_pts += [(114 * s, 158.6 * s), (128 * s, 158.6 * s)]
        # deep limbic structures projected onto the midline view (dashed outline)
        hip = _cr(P([(196, 128), (184, 122), (170, 122), (158, 128), (152, 136)]), 6)
        hip_band = _offset(hip, 3.8 * s) + _offset(hip, -3.8 * s)[::-1]
        hip_c = tint.get("hippocampus", _mix(color, "#9A5A8A", 0.35))
        holder.append(
            _el(
                "path",
                d=_smooth(hip_band, closed=True),
                fill=hip_c,
                fill_opacity=0.85 if "hippocampus" in tint else 0.55,
                stroke=_mix(hip_c, "#3A1430", 0.45),
                stroke_width=_sw(0.7 * s),
            )
        )
        am_c = tint.get("amygdala", _mix(color, "#9A5A8A", 0.45))
        holder.append(
            _el(
                "ellipse",
                cx=148 * s,
                cy=128 * s,
                rx=5.5 * s,
                ry=4.2 * s,
                fill=am_c,
                fill_opacity=0.9 if "amygdala" in tint else 0.55,
                stroke=_mix(am_c, "#3A1430", 0.45),
                stroke_width=_sw(0.7 * s),
            )
        )
        for key in ("cingulate", "marginal", "parieto_occ", "calcarine", "paracentral"):
            major.append(_cr(P(F[key]), 8))
        keep = lambda p: ins(p) and _cort_sag(p, s)
        ports.update(
            prefrontal=(36 * s, 92 * s),
            cingulate=_poly_at(cing, 0.45),
            callosum=_poly_at(cc_line, 0.5),
            thalamus=(tx * s, ty * s),
            hypothalamus=(127 * s, 128 * s),
            pituitary=(121 * s, 154 * s),
            hippocampus=_poly_at(hip, 0.4),
            amygdala=(148 * s, 128 * s),
            midbrain=(170 * s, 142 * s),
            pons=(156 * s, 176 * s),
            medulla=(168 * s, 220 * s),
            brainstem=(166 * s, 190 * s),
            nts=(173 * s, 212 * s),
            vagus=(158 * s, 214 * s),
            occipital=(272 * s, 112 * s),
        )
        # 4th ventricle notch between brainstem and cerebellum + NTS nucleus in the dorsal medulla
        v4 = P([(186, 162), (194, 176), (188, 192), (182, 184)])
        holder.append(
            _el(
                "path",
                d=_smooth(v4, closed=True),
                fill="#CFE3EE",
                stroke=_mix("#CFE3EE", "#2A5070", 0.45),
                stroke_width=_sw(0.6 * s),
            )
        )
        pons_line = _cr(P([(136, 166), (152, 162), (172, 166)]), 8)
        pl = []
        for k in (-1, 0, 1, 2, 3, 4, 5):
            seg = [q for q in _offset(pons_line, -k * 4.2 * s) if _inside(q, _offset(bs, 0)) and q[0] < 170 * s]
            if len(seg) > 3:
                pl.append(_d(seg[1:-1], False))
        holder.append(
            _el("path", d=" ".join(pl), fill="none", stroke=_mix(bs_col, "#5A2028", 0.25), stroke_width=_sw(0.5 * s))
        )
        nts_c = tint.get("nts", _mix(bs_col, "#7A3A30", 0.3))
        holder.append(
            _el(
                "ellipse",
                cx=173 * s,
                cy=212 * s,
                rx=4.2 * s,
                ry=6.5 * s,
                fill=nts_c,
                stroke=_mix(nts_c, "#3A1410", 0.45),
                stroke_width=_sw(0.7 * s),
            )
        )
    else:
        for key in (
            "lateral",
            "central",
            "precentral",
            "postcentral",
            "sup_frontal",
            "inf_frontal",
            "sup_temporal",
            "intraparietal",
        ):
            major.append(_cr(P(F[key]), 8))
        tint_poly("prefrontal", _clip_half(outline, 1, 0.3, 104 * s))
        tint_poly("occipital", _clip_half(outline, -1, -0.35, -(252 * s)))
        if "motor" in tint:
            pc, cs = _cr(P(F["precentral"]), 6), _cr(P(F["central"]), 6)
            tint_poly("motor", pc + cs[::-1])
        if "parietal" in tint:
            cs = _cr(P(F["central"]), 6)
            par = [p for p in outline if p[0] > 160 * s and p[1] < 95 * s and p[0] < 250 * s]
            tint_poly("parietal", cs + [(240 * s, 82 * s)] + sorted(par, key=lambda q: -q[0]))
        if "temporal" in tint:
            lat = _cr(P(F["lateral"]), 6)
            tl = [p for p in outline if p[1] > 140 * s and 80 * s < p[0] < 245 * s]
            tint_poly("temporal", lat[:-6] + [(232 * s, 140 * s)] + sorted(tl, key=lambda q: -q[0]))
        hip_c = tint.get("hippocampus", None)
        if hip_c:
            hip = _cr(P([(132, 158), (156, 152), (180, 144), (198, 136)]), 6)
            holder_hip = _offset(hip, 3.5 * s) + _offset(hip, -3.5 * s)[::-1]
            region_els.append(
                _el(
                    "path",
                    d=_smooth(holder_hip, closed=True),
                    fill=hip_c,
                    fill_opacity=0.8,
                    stroke=_mix(hip_c, "#3A1430", 0.4),
                    stroke_width=_sw(0.7 * s),
                )
            )
        am_c = tint.get("amygdala", None)
        if am_c:
            region_els.append(
                _el(
                    "ellipse",
                    cx=122 * s,
                    cy=158 * s,
                    rx=5 * s,
                    ry=4 * s,
                    fill=am_c,
                    fill_opacity=0.85,
                    stroke=_mix(am_c, "#3A1430", 0.4),
                    stroke_width=_sw(0.7 * s),
                )
            )
        if "insula" in tint:
            region_els.append(
                _el(
                    "ellipse",
                    cx=136 * s,
                    cy=118 * s,
                    rx=18 * s,
                    ry=6 * s,
                    fill=tint["insula"],
                    fill_opacity=0.5,
                    stroke=tint["insula"],
                    stroke_width=_sw(1 * s),
                )
            )
        nts_c = tint.get("nts")
        if nts_c:
            region_els.append(
                _el(
                    "ellipse",
                    cx=200 * s,
                    cy=214 * s,
                    rx=3.6 * s,
                    ry=6 * s,
                    fill=nts_c,
                    stroke=_mix(nts_c, "#3A1410", 0.45),
                    stroke_width=_sw(0.7 * s),
                )
            )
        keep = lambda p: ins(p) and not _inside(p, _cr(P(F["brainstem"]), 4))
        ports.update(
            prefrontal=(40 * s, 70 * s),
            motor=(140 * s, 40 * s),
            parietal=(214 * s, 44 * s),
            temporal=(150 * s, 160 * s),
            occipital=(274 * s, 112 * s),
            insula=(136 * s, 118 * s),
            hippocampus=(164 * s, 150 * s),
            amygdala=(122 * s, 158 * s),
            brainstem=(190 * s, 200 * s),
            nts=(200 * s, 214 * s),
            vagus=(186 * s, 218 * s),
        )
    for name, (px, py, prx, pry) in _BRAIN_PATCHES[view].items():
        ports[name] = (px * s, py * s)
        if name in tint:
            region_els.append(
                _el(
                    "ellipse",
                    cx=px * s,
                    cy=py * s,
                    rx=prx * s,
                    ry=pry * s,
                    fill=tint[name],
                    fill_opacity=0.55,
                    stroke=tint[name],
                    stroke_width=_sw(1.2 * s),
                )
            )
    avoid = [p for c in major for p in c]
    if view == "sagittal":
        avoid += _offset(cc_line, -9 * s)
    tex = _gyral_texture(
        outline, s, rnd, lambda p: keep(p) and not _near(p, outline, 2.2 * s), avoid, spacing=5.4, n=260, max_len=58
    )
    major_d = " ".join(_sulcus(c, 3.0 * s) for c in major)
    tex_d = " ".join(_sulcus(c, 2.1 * s) for c in tex)
    holder.extend(region_els)
    holder.append(_el("path", d=major_d + " " + tex_d, fill=sulc, stroke="none"))
    if rich:
        look = _look()
        defs.append(_radial("bshade", "#FFFFFF", "#6A2030", fx=0.35, fy=0.25))
        g = defs[-1]
        g[0].set("stop-opacity", ".35")
        g[1].set("stop-opacity", ".22")
        look.append(_el("path", d=cer_d, fill="url(#bshade)"))
        look.append(_el("path", d=_smooth(cb_out, closed=True), fill="url(#bshade)", fill_opacity=0.7))
        # gyral crown highlights: light strokes offset beside each sulcus
        hl = [_d(_offset(c, 2.2 * s)[2:-2], False) for c in major + tex if len(c) > 6]
        look.append(
            _el(
                "path",
                d=" ".join(hl),
                fill="none",
                stroke="#FFFFFF",
                stroke_width=0.6 * s,
                stroke_opacity=0.35,
                stroke_linecap="round",
            )
        )
        holder.append(look)
    xs, ys = [p[0] for p in bounds_pts], [p[1] for p in bounds_pts]
    pad = 1.0 * s
    box = Box(min(xs) - pad, min(ys) - pad, max(xs) - min(xs) + 2 * pad, max(ys) - min(ys) + 2 * pad)
    if nodes:
        box = _network_overlay(holder, ports, box, nodes, edges or (), s, font_size or max(10.0, 12 * s**0.5))
    elif edges:
        raise ValueError("edges need nodes=[(region, label, value), ...] to connect")
    return _finish(holder, defs, box, **ports)


# cortical patches without a full outline: (x, y, rx, ry) in the 300-unit frame; also usable as node anchors
_BRAIN_PATCHES = {
    "sagittal": {
        "mpfc": (34, 74, 16, 13),
        "acc": (68, 84, 9, 7),
        "pcc": (200, 60, 11, 7),
        "precuneus": (230, 38, 14, 11),
    },
    "lateral": {"dlpfc": (72, 56, 22, 13), "vlpfc": (62, 104, 18, 10), "ipl": (232, 92, 20, 13)},
}
_BRAIN_REGIONS = {
    "sagittal": {
        "prefrontal",
        "cingulate",
        "callosum",
        "thalamus",
        "hypothalamus",
        "pituitary",
        "hippocampus",
        "amygdala",
        "midbrain",
        "pons",
        "medulla",
        "brainstem",
        "nts",
        "cerebellum",
        "occipital",
        "vagus",
    }
    | set(_BRAIN_PATCHES["sagittal"]),
    "lateral": {
        "prefrontal",
        "motor",
        "parietal",
        "temporal",
        "occipital",
        "insula",
        "hippocampus",
        "amygdala",
        "brainstem",
        "nts",
        "cerebellum",
        "vagus",
    }
    | set(_BRAIN_PATCHES["lateral"]),
}
_POS, _NEG = "#C0392B", "#2E6FB0"


def _network_overlay(holder, ports, box, nodes, edges, s, fs):
    """Connectivity graph on the brain: node discs sized by |value| (▲/▼ for the sign), edges coloured by sign and"""
    from ._geometry import label as _lab

    cx0, cy0 = box.x + box.width / 2, box.y + box.height * 0.45
    pos, vals = {}, {}
    for item in nodes:
        where, name = item[0], str(item[1])
        value = float(item[2]) if len(item) > 2 and item[2] is not None else 0.0
        if isinstance(where, str):
            p = ports[where]
        else:
            u, v = where
            p = (box.x + float(u) * box.width, box.y + float(v) * box.height)
        pos[name], vals[name] = p, value
        if isinstance(where, str):
            pos.setdefault(where, p)
    vmax = max([abs(v) for v in vals.values()] + [1e-9])
    rad = {n: (4.5 + 5.5 * abs(v) / vmax) * s**0.5 for n, v in vals.items()}
    wmax = max([abs(float(e[2])) if len(e) > 2 else 1.0 for e in edges] + [1e-9])
    for e in edges:
        a, b = str(e[0]), str(e[1])
        if a not in pos or b not in pos:
            raise ValueError(f"edge ({a!r}, {b!r}) must join node labels or regions given in nodes")
        w = abs(float(e[2])) if len(e) > 2 else 1.0
        sign = e[3] if len(e) > 3 else (1 if len(e) <= 2 or float(e[2]) >= 0 else -1)
        neg = sign in (-1, "-", "neg", "negative") or (isinstance(sign, (int, float)) and sign < 0)
        (x1, y1), (x2, y2) = pos[a], pos[b]
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        L = math.hypot(x2 - x1, y2 - y1) or 1
        nx, ny = -(y2 - y1) / L, (x2 - x1) / L
        if (mx - cx0) * nx + (my - cy0) * ny < 0:
            nx, ny = -nx, -ny
        bend = L * 0.18
        col = _NEG if neg else _POS
        holder.append(
            _el(
                "path",
                d=f"M{fmt(x1)} {fmt(y1)} Q{fmt(mx + nx * bend)} {fmt(my + ny * bend)} {fmt(x2)} {fmt(y2)}",
                fill="none",
                stroke=col,
                stroke_width=(1.2 + 3.0 * w / wmax) * s**0.5,
                stroke_opacity=0.85,
                stroke_linecap="round",
                stroke_dasharray=f"{fmt(4 * s**0.5)} {fmt(3 * s**0.5)}" if neg else None,
            )
        )
    pts = []
    taken = [
        Box(x - rad[n] - 1, y - rad[n] - 1, 2 * rad[n] + 2, 2 * rad[n] + 2) for n, (x, y) in pos.items() if n in vals
    ]
    for name, (x, y) in pos.items():
        if name not in vals:
            continue
        v, r = vals[name], rad[name]
        col = _NEG if v < 0 else _POS if v > 0 else "#7A7A86"
        holder.append(_el("circle", cx=x, cy=y, r=r, fill=col, stroke="#FFFFFF", stroke_width=_sw(1.4 * s**0.5)))
        if v:
            t = r * 0.5
            tri = (
                [(x, y - t), (x + t * 0.95, y + t * 0.6), (x - t * 0.95, y + t * 0.6)]
                if v > 0
                else [(x, y + t), (x + t * 0.95, y - t * 0.6), (x - t * 0.95, y - t * 0.6)]
            )
            holder.append(_el("path", d=_d(tri), fill="#FFFFFF"))
        lw = _lab(name, font_size=fs, font_weight="bold").bounds.width
        side = 1 if x >= cx0 else -1
        cands = [(side, 0), (-side, 0), (0, -1), (0, 1), (side, -1), (side, 1)]
        best = None
        own = Box(x - r - 1, y - r - 1, 2 * r + 2, 2 * r + 2)
        for sx, sy in cands:
            lx = x + sx * (r + 3) - (lw if sx < 0 else 0 if sx > 0 else lw / 2)
            ly = y + sy * (r + fs * 0.7) - fs * 0.5
            b = Box(lx - 1, ly - 1, lw + 2, fs + 2)
            if not any(
                o != own
                and b.x < o.x + o.width
                and o.x < b.x + b.width
                and b.y < o.y + o.height
                and o.y < b.y + b.height
                for o in taken
            ):
                best = b
                break
        best = best or Box(x + r + 3, y - fs * 0.5, lw, fs)
        taken.append(best)
        t = _el("text", x=best.x + 1, y=best.y + 1 + fs * 0.85, font_size=fs, font_weight="bold", fill="#2A2A33")
        t.text = name
        holder.append(t)
        pts += [(best.x, best.y), (best.x + best.width, best.y + best.height), (x - r, y - r), (x + r, y + r)]
        ports["node_" + name] = (x, y)
    xs = [box.x, box.x + box.width] + [p[0] for p in pts]
    ys = [box.y, box.y + box.height] + [p[1] for p in pts]
    return Box(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


def _cort_sag(p, s):
    """Medial cortex zone for the sagittal view: outside the cingulate/callosal core and the diencephalon."""
    x, y = p[0] / s, p[1] / s
    # exclude an ellipse around the callosum / thalamus / limbic core
    return ((x - 146) / 78) ** 2 + ((y - 96) / 50) ** 2 > 1 and not (y > 118 and 95 < x < 215)


# Frontal (coronal) section, 300-unit frame; patient's left on image right, apex down toward image right.
_HEART = dict(
    body=[
        (66, 104),
        (48, 113),
        (36, 136),
        (33, 166),
        (40, 196),
        (56, 216),
        (78, 236),
        (102, 260),
        (132, 282),
        (168, 298),
        (204, 306),
        (232, 304),
        (258, 290),
        (278, 262),
        (287, 226),
        (287, 192),
        (282, 166),
        (284, 140),
        (278, 112),
        (262, 97),
        (238, 91),
        (212, 94),
        (194, 98),
        (176, 97),
        (154, 95),
        (126, 96),
        (100, 101),
        (80, 101),
    ],
    right=[
        (70, 110),
        (93, 110),
        (110, 122),
        (117, 156),
        (120, 188),
        (124, 199),
        (131, 176),
        (131, 138),
        (129, 104),
        (151, 104),
        (153, 134),
        (154, 172),
        (160, 212),
        (170, 248),
        (178, 272),
        (160, 282),
        (132, 270),
        (102, 248),
        (86, 228),
        (80, 214),
        (64, 208),
        (50, 190),
        (44, 160),
        (48, 130),
        (58, 115),
    ],
    left=[
        (185, 108),
        (193, 136),
        (201, 157),
        (205, 128),
        (210, 110),
        (228, 101),
        (256, 103),
        (272, 118),
        (275, 142),
        (264, 160),
        (251, 170),
        (259, 196),
        (259, 230),
        (249, 262),
        (226, 286),
        (214, 280),
        (203, 244),
        (192, 206),
        (182, 168),
        (174, 138),
        (166, 120),
        (163, 108),
    ],
)


def _vessels(paths, wall, lumen, w, s):
    """Double-stroked tubes (all walls first, then all lumens) so branches merge cleanly; returns (elements, path data)."""
    ds = [_smooth(_cr(p, 6)) for p, _ in paths]
    els = [
        _el("path", d=d, fill="none", stroke=wall, stroke_width=2 * r, stroke_linejoin="round")
        for d, (_, r) in zip(ds, paths)
    ]
    els += [
        _el("path", d=d, fill="none", stroke=lumen, stroke_width=2 * r - 2 * w * s, stroke_linejoin="round")
        for d, (_, r) in zip(ds, paths)
    ]
    return els, " ".join(ds)


def _cut(p, q, r, lumen, wall, s):
    """Cut vessel end at p (vessel coming from q): the lumen seen end-on."""
    a = math.atan2(p[1] - q[1], p[0] - q[0])
    return _el(
        "path",
        d=_oval(p[0], p[1], r * 0.32, r, a),
        fill=_mix(lumen, "#2A1418", 0.3),
        stroke=wall,
        stroke_width=_sw(1.1 * s),
    )


def _semilunar(x0, x1, y, s):
    """Closed semilunar valve: two cusps cupped toward the vessel (pockets open downstream)."""
    xm = (x0 + x1) / 2
    h = (x1 - x0) * 0.32
    return (
        f"M{fmt(x0)} {fmt(y - h)} Q{fmt(x0 + (xm - x0) * 0.2)} {fmt(y + h * 0.9)} {fmt(xm)} {fmt(y)} "
        f"Q{fmt(x1 - (x1 - xm) * 0.2)} {fmt(y + h * 0.9)} {fmt(x1)} {fmt(y - h)}"
    )


def _leaflet(base, tip, w):
    """Tapered AV-valve leaflet from the annulus ``base`` to the free edge ``tip``."""
    ax, ay = tip[0] - base[0], tip[1] - base[1]
    L = math.hypot(ax, ay) or 1
    nx, ny = -ay / L * w, ax / L * w
    return _smooth(
        [
            (base[0] + nx, base[1] + ny),
            (base[0] + ax * 0.55 + nx * 0.7, base[1] + ay * 0.55 + ny * 0.7),
            tip,
            (base[0] + ax * 0.55 - nx * 0.4, base[1] + ay * 0.55 - ny * 0.4),
            (base[0] - nx * 0.5, base[1] - ny * 0.5),
        ],
        closed=True,
    )


@_drawing_api(
    "parts",
    purpose="心脏冠状切面（教科书级）：右/左心房与心室（左室壁明显厚于右室）、室间隔、心尖、三尖瓣与二尖瓣（瓣叶+腱索+乳头肌）、主动脉瓣与肺动脉瓣（半月瓣）、主动脉弓及三分支、肺动脉干分叉、上/下腔静脉、肺静脉；oxygen=True 右心偏蓝、左心偏红。",
    returns="Geometry（原点在中心；端口 ra/rv/la/lv/septum/apex/aorta/pa/svc/ivc/pv/mitral/tricuspid/aortic_valve/pulmonary_valve）",
    semantics=(
        "width 为宽度（高≈1.05×宽）；解剖学方位：患者左侧在图右，心尖朝右下。",
        "oxygen=True 右心与腔静脉/肺动脉用 venous 色、左心与肺静脉/主动脉用 arterial 色；False 时全部用中性血色。muscle 为心肌色。",
        "labels=False（默认）不写字，用 callout 指端口；labels=True 在腔内写 RA/RV/LA/LV 小缩写。",
        'style="rich" 加心肌明暗与血管高光（一个局部 SVG），"flat" 全原生。',
    ),
    example='h = d.place(heart(280), at=(300, 250), key="h")\n'
    'd.callout("lvh", "左心室肥厚", h.port("lv"), at=(520, 300), font_size=12)',
    rank=27,
)
def heart(
    width=300,
    *,
    oxygen=True,
    labels=False,
    muscle="#D9A396",
    venous="#8FA7CC",
    arterial="#CC6A6C",
    valve="#F4E9D6",
    style="rich",
):
    rich = _style(style)
    _finite(width)
    s = width / 300.0
    P = lambda pts: [(x * s, y * s) for x, y in pts]
    ven, art = (venous, arterial) if oxygen else ("#E3B9B4", "#E3B9B4")
    edge = _mix(muscle, "#4A1A18", 0.5)
    holder, defs = _el("g"), _el("defs")
    holder.append(defs)
    body = _cr(P(_HEART["body"] + _HEART["body"][:1]), 6)[:-1]
    holder.append(
        _el("path", d=_smooth(body, closed=True), fill=muscle, stroke=edge, stroke_width=_sw(1.3 * s), data_outline="1")
    )
    pts = list(body)
    vw = lambda c: _mix(c, "#3A1418", 0.38)
    r_pa, r_ao, r_cv = 10 * s, 12 * s, 11 * s
    rpa = [P([(186, 70), (150, 74), (110, 76), (72, 78), (52, 80)])]
    svc, ivc = P([(82, 112), (81, 70), (80, 22)]), P([(60, 196), (59, 260), (58, 318)])
    ao_up = P([(173, 112), (172, 80), (176, 52), (198, 34), (226, 36), (242, 54), (247, 72)])
    br = [P([(186, 40), (183, 22), (180, 6)]), P([(205, 33), (205, 16), (206, 2)]), P([(224, 36), (229, 20), (234, 6)])]
    pt = P([(140, 102), (142, 84), (156, 72), (186, 68)])
    lpa = P([(186, 68), (214, 70), (240, 76), (266, 80)])
    pvs = [P([(268, 118), (288, 112), (304, 108)]), P([(272, 146), (292, 148), (306, 151)])]
    els, _ = _vessels([(rpa[0], r_pa)], vw(ven), ven, 2.2, s)
    holder.extend(els)
    els, _ = _vessels([(svc, r_cv), (ivc, r_cv)], vw(ven), ven, 1.6, s)
    holder.extend(els)
    els, _ = _vessels([(p, 5 * s) for p in pvs], vw(art), art, 1.4, s)
    holder.extend(els)
    els, aod = _vessels([(ao_up, r_ao)] + [(b, 5.2 * s) for b in br], vw(art), art, 2.6, s)
    holder.extend(els)
    els, ptd = _vessels([(pt, r_pa), (lpa, r_pa * 0.85)], vw(ven), ven, 2.2, s)
    holder.extend(els)
    for path, r, col in (
        [(rpa[0], r_pa, ven), (svc, r_cv, ven), (lpa, r_pa * 0.85, ven), (ao_up, r_ao, art)]
        + [(b, 5.2 * s, art) for b in br]
        + [(p, 5 * s, art) for p in pvs]
    ):
        holder.append(_cut(path[-1], path[-2], r, col, vw(col), s))
    holder.append(_cut(ivc[-1], ivc[-2], r_cv, ven, vw(ven), s))
    for path, r in [(svc, r_cv), (ivc, r_cv), (ao_up, r_ao), (pt, r_pa), (lpa, r_pa)] + [
        (p, 5 * s) for p in pvs + br + rpa
    ]:
        pts += [(x + dx, y + dy) for x, y in path for dx, dy in ((r, r), (-r, -r))]
    rc = _cr(P(_HEART["right"] + _HEART["right"][:1]), 5)[:-1]
    lc = _cr(P(_HEART["left"] + _HEART["left"][:1]), 5)[:-1]
    for cav, col in ((rc, ven), (lc, art)):
        holder.append(
            _el(
                "path",
                d=_smooth(cav, closed=True),
                fill=col,
                stroke=_mix(col, "#3A1418", 0.3),
                stroke_width=_sw(0.8 * s),
            )
        )
    # trabeculae carneae: short ridges on the inner ventricular walls
    trab = []
    for poly, lo, hi in ((rc, 13, 18), (lc, 12, 15)):
        for i in range(lo * 5, hi * 5, 3):
            (x0, y0), (x1, y1) = poly[i], poly[i + 1]
            nx, ny = (y1 - y0), -(x1 - x0)
            L = math.hypot(nx, ny) or 1
            trab.append(_d([(x0, y0), (x0 + nx / L * 4 * s, y0 + ny / L * 4 * s)], False))
    holder.append(
        _el("path", d=" ".join(trab), fill="none", stroke=edge, stroke_width=_sw(1.4 * s), stroke_linecap="round")
    )
    vstroke = _mix(valve, "#5A4020", 0.5)
    pap = [
        P([(116, 268), (113, 252), (120, 242), (127, 252), (128, 268)]),
        P([(256, 248), (240, 236), (232, 222), (247, 224), (258, 236)]),
        P([(203, 262), (206, 240), (214, 232), (216, 246), (214, 270)]),
    ]
    holder.append(
        _el(
            "path",
            d=" ".join(_smooth(p, closed=True) for p in pap),
            fill=_mix(muscle, "#7A2A28", 0.15),
            stroke=edge,
            stroke_width=_sw(0.8 * s),
        )
    )
    av = [
        ((82, 213), (98, 238), (120, 243)),
        ((124, 199), (118, 228), (120, 243)),
        ((201, 157), (214, 196), (214, 233)),
        ((251, 170), (238, 201), (233, 223)),
    ]
    leaf, chord = [], []
    for base, tip, papt in av:
        b, t, pp = P([base])[0], P([tip])[0], P([papt])[0]
        leaf.append(_leaflet(b, t, 3.6 * s))
        chord += [_d([t, pp], False), _d([((b[0] + t[0] * 2) / 3, (b[1] + t[1] * 2) / 3), pp], False)]
    holder.append(
        _el("path", d=" ".join(chord), fill="none", stroke=_mix(valve, "#5A4020", 0.35), stroke_width=_sw(0.5 * s))
    )
    holder.append(_el("path", d=" ".join(leaf), fill=valve, stroke=vstroke, stroke_width=_sw(0.7 * s)))
    holder.append(
        _el(
            "path",
            d=" ".join(_circ(*P([q])[0], 2.2 * s) for q in ((82, 213), (124, 199), (201, 157), (251, 170))),
            fill="#F2EDE4",
            stroke=vstroke,
            stroke_width=_sw(0.6 * s),
        )
    )
    holder.append(
        _el(
            "path",
            d=_semilunar(162 * s, 184 * s, 106 * s, s) + " " + _semilunar(129 * s, 151 * s, 102 * s, s),
            fill="none",
            stroke=vstroke,
            stroke_width=2.6 * s,
            stroke_linecap="round",
        )
    )
    holder.append(
        _el(
            "path",
            d=_semilunar(162 * s, 184 * s, 106 * s, s) + " " + _semilunar(129 * s, 151 * s, 102 * s, s),
            fill="none",
            stroke=valve,
            stroke_width=1.3 * s,
            stroke_linecap="round",
        )
    )
    if labels:
        from ._earth_parts import _text

        for txt, x, y, col in (
            ("RA", 78, 150, ven),
            ("RV", 140, 236, ven),
            ("LA", 240, 134, art),
            ("LV", 236, 252, art),
        ):
            holder.append(_text(x * s, y * s, txt, 11 * s, fill=_mix(col, "#1A0A0A", 0.65))[0])
    if rich:
        look = _look()
        defs.append(_radial("hshade", "#FFFFFF", "#5A1A18", fx=0.3, fy=0.25))
        defs[-1][0].set("stop-opacity", ".3")
        defs[-1][1].set("stop-opacity", ".25")
        look.append(_el("path", d=_smooth(body, closed=True), fill="url(#hshade)"))
        look.append(
            _el(
                "path",
                d=aod + " " + ptd,
                fill="none",
                stroke="#FFFFFF",
                stroke_width=2 * s,
                stroke_opacity=0.35,
                stroke_linecap="round",
                transform=f"translate({fmt(-3 * s)} {fmt(-2 * s)})",
            )
        )
        holder.append(look)
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    ports = dict(
        ra=P([(80, 160)])[0],
        rv=P([(146, 236)])[0],
        la=P([(240, 128)])[0],
        lv=P([(230, 214)])[0],
        septum=P([(188, 232)])[0],
        apex=P([(234, 303)])[0],
        aorta=P([(212, 34)])[0],
        pa=P([(152, 76)])[0],
        svc=P([(81, 40)])[0],
        ivc=P([(58, 296)])[0],
        pv=P([(296, 110)])[0],
        mitral=P([(226, 164)])[0],
        tricuspid=P([(103, 206)])[0],
        aortic_valve=P([(173, 106)])[0],
        pulmonary_valve=P([(140, 102)])[0],
    )
    return _finish(holder, defs, Box(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)), **ports)


# 300 × 400 frame: cortex y<150, outer medulla 150–270, inner medulla below. Centre-line control points per segment.
_NEPH = dict(
    pct=[
        (56, 112),
        (44, 134),
        (60, 144),
        (82, 136),
        (98, 124),
        (114, 128),
        (110, 144),
        (88, 150),
        (70, 154),
        (78, 166),
        (98, 164),
        (114, 158),
        (122, 172),
        (116, 190),
    ],
    loop_desc=[(116, 190), (114, 260), (112, 330), (116, 366), (126, 376)],
    loop_asc=[(126, 376), (136, 366), (139, 330), (140, 270)],
    tal=[(140, 270), (141, 200), (142, 120), (136, 72), (114, 56), (96, 50)],
    dct=[
        (96, 50),
        (116, 38),
        (140, 36),
        (166, 46),
        (176, 70),
        (196, 82),
        (214, 66),
        (206, 44),
        (220, 28),
        (242, 34),
        (250, 54),
        (262, 66),
    ],
    cd=[(262, 6), (262, 120), (264, 260), (266, 394)],
)


def _stroke_tube(pts, wall, lumen, ow, iw, s, edge=None, extra=None):
    """Tubule drawn as wall band + lumen; returns elements. ``extra`` = (colour, width) drawn between (brush border)."""
    d = _smooth(_cr(pts, 6))
    kw = dict(fill="none", stroke_linecap="round", stroke_linejoin="round")
    els = [
        _el("path", d=d, stroke=edge or _mix(wall, "#3A2018", 0.45), stroke_width=(ow + 1.2) * s, **kw),
        _el("path", d=d, stroke=wall, stroke_width=ow * s, **kw),
    ]
    if extra:
        els.append(_el("path", d=d, stroke=extra[0], stroke_width=extra[1] * s, **kw))
    els.append(_el("path", d=d, stroke=lumen, stroke_width=iw * s, **kw))
    return els, d


@_drawing_api(
    "parts",
    purpose="肾单位（教科书级）：肾小体（双层鲍曼囊内袢状毛细血管球、足细胞，入球小动脉粗于出球小动脉）、近曲小管（盘曲、厚壁、刷状缘）、髓袢降支细段与升支细/粗段、远曲小管回到肾小体血管极（致密斑）、集合管；zones=True 衬皮质/髓质带。",
    returns="Geometry（原点在中心；端口 glomerulus/bowman/afferent/efferent/pct/loop_desc/loop_asc/dct/macula_densa/cd/cortex/medulla）",
    semantics=(
        "width 为宽度（高≈1.33×宽）；肾小体在左上，皮质在上、髓质在下，集合管在右侧下行。",
        "highlight 为节段名元组（glomerulus/pct/loop_desc/loop_asc/dct/cd），用 accent 色强调，其余节段保持中性。",
        'zones=False 去掉皮质/髓质背景带；style="rich" 加刷状缘细纹与明暗（一个局部 SVG），"flat" 全原生。',
    ),
    example='k = d.place(nephron(240, highlight=("pct",)), at=(300, 260), key="k")\n'
    'd.callout("sglt2", "SGLT2（近曲小管）", k.port("pct"), at=(520, 200), font_size=12)',
    rank=28,
)
def nephron(width=300, *, zones=True, highlight=(), accent="#D9822B", tubule="#DDAE94", blood="#C8474E", style="rich"):
    rich = _style(style)
    _finite(width)
    hl = set(highlight)
    bad = hl - {"glomerulus", "pct", "loop_desc", "loop_asc", "dct", "cd"}
    if bad:
        raise ValueError(f"unknown nephron segments {sorted(bad)}")
    s = width / 300.0
    W, H = 300 * s, 400 * s
    P = lambda pts: [(x * s, y * s) for x, y in pts]
    holder, defs = _el("g"), _el("defs")
    holder.append(defs)
    lum = "#FBF4EC"
    first = dict(data_outline="1")
    if zones:
        for y0, y1, col in ((0, 150, "#F6E7DA"), (150, 270, "#F1DCD3"), (270, 400, "#EBD2CC")):
            holder.append(
                _el(
                    "rect",
                    x=0,
                    y=y0 * s,
                    width=W,
                    height=(y1 - y0) * s,
                    fill=col,
                    stroke=_mix(col, "#7A5040", 0.25),
                    stroke_width=_sw(0.6 * s),
                    **first,
                )
            )
            first = {}
    wall = lambda seg: accent if seg in hl else tubule
    cx, cy, R = 62 * s, 86 * s, 40 * s
    cap_col = wall("glomerulus") if "glomerulus" in hl else _mix(tubule, "#FFFFFF", 0.2)
    holder.append(
        _el(
            "circle",
            cx=cx,
            cy=cy,
            r=R,
            fill=cap_col,
            stroke=_mix(cap_col, "#3A2018", 0.45),
            stroke_width=_sw(1 * s),
            **first,
        )
    )
    holder.append(
        _el(
            "circle",
            cx=cx,
            cy=cy,
            r=R - 3.2 * s,
            fill="#FFFDF8",
            stroke=_mix(cap_col, "#3A2018", 0.3),
            stroke_width=_sw(0.6 * s),
        )
    )
    vp = (cx + 2 * s, cy - R + 4 * s)
    aff = [(0, 18 * s), (26 * s, 22 * s), (50 * s, 34 * s), (vp[0] - 6 * s, vp[1] + 6 * s)]
    eff = [(vp[0] + 6 * s, vp[1] + 6 * s), (vp[0] + 10 * s, vp[1] - 14 * s), (vp[0] + 4 * s, 0)]
    dk = _mix(blood, "#2A0A0E", 0.45)
    for line, w in ((aff, 8.5), (eff, 5)):
        d = _smooth(_cr(line, 6))
        holder.append(_el("path", d=d, fill="none", stroke=dk, stroke_width=(w + 1.4) * s, stroke_linecap="butt"))
        holder.append(_el("path", d=d, fill="none", stroke=blood, stroke_width=w * s, stroke_linecap="butt"))
    loops = []
    for k, b in enumerate((-35, 10, 55, 100, 145, 190, 235)):
        b = math.radians(b)
        lc = (cx + 0.44 * R * math.cos(b), cy + 4 * s + 0.4 * R * math.sin(b))
        rl, rr = 0.3 * R, 0.1 * R
        coil = [
            (lc[0] + rl * math.cos(u) + rr * math.cos(7 * u + k), lc[1] + rl * math.sin(u) + rr * math.sin(7 * u + k))
            for u in (2 * math.pi * j / 84 for j in range(85))
        ]
        loops.append(_smooth([vp, ((vp[0] + lc[0]) / 2, (vp[1] + lc[1]) / 2 + 2 * s), coil[0]]) + " " + _smooth(coil))
    gd = " ".join(loops)
    gl = wall("glomerulus") if "glomerulus" in hl else blood
    holder.append(
        _el(
            "path",
            d=gd,
            fill="none",
            stroke=_mix(gl, "#2A0A0E", 0.45),
            stroke_width=3.6 * s,
            stroke_linecap="round",
            stroke_linejoin="round",
        )
    )
    holder.append(
        _el("path", d=gd, fill="none", stroke=gl, stroke_width=2.2 * s, stroke_linecap="round", stroke_linejoin="round")
    )
    rnd = random.Random(7)
    pods = []
    for k in range(10):
        a = math.radians(-60 + 36 * k) + rnd.uniform(-0.2, 0.2)
        r = 0.78 * R
        pods.append(_oval(cx + math.cos(a) * r, cy + 4 * s + math.sin(a) * r * 0.92, 2.8 * s, 1.6 * s, a + math.pi / 2))
    holder.append(_el("path", d=" ".join(pods), fill="#8C6BB0", stroke="#4E3A70", stroke_width=_sw(0.4 * s)))
    brush = "#E8CF98"
    segs = {}
    up = (cx - R * 0.5, cy + R * 0.87)  # urinary pole → PCT
    pct = [up] + P(_NEPH["pct"])[1:]
    order = (
        ("pct", pct, 12, 4.2, (brush, 6.8)),
        ("loop_desc", P(_NEPH["loop_desc"]), 5, 2.6, None),
        ("loop_asc", P(_NEPH["loop_asc"]), 5.4, 2.8, None),
        ("tal", P(_NEPH["tal"]), 9, 3.6, None),
        ("dct", P(_NEPH["dct"]), 9, 4, None),
        ("cd", P(_NEPH["cd"]), 15, 7, None),
    )
    for name, pts, ow, iw, extra in order:
        key = "loop_asc" if name == "tal" else name
        els, d = _stroke_tube(pts, wall(key), lum, ow, iw, s, extra=extra)
        holder.extend(els)
        segs[name] = (pts, d, ow)
    # macula densa: tall, crowded nuclei where the TAL/DCT touches the vascular pole
    md = P([(96, 50)])[0]
    holder.append(
        _el(
            "path",
            d=" ".join(_oval(md[0] + dx * s, md[1] + 3.6 * s, 0.9 * s, 2 * s, 0) for dx in (-3, -1, 1, 3)),
            fill="#5A4A86",
            stroke="none",
        )
    )
    # cuboidal-cell nuclei along the PCT / DCT walls
    nucs = []
    for name, side in (("pct", 4.1), ("dct", 3.2), ("cd", 5.4)):
        pts = _cr(segs[name][0], 6)
        for (x, y), (nx, ny) in _along(pts, 9 * s, 4 * s):
            nucs.append(_circ(x + nx * side * s, y + ny * side * s, 0.95 * s))
            nucs.append(_circ(x - nx * side * s, y - ny * side * s, 0.95 * s))
    holder.append(_el("path", d=" ".join(nucs), fill=_mix("#5A4A86", "#FFFFFF", 0.2), stroke="none"))
    if rich:
        look = _look()
        look.append(
            _el(
                "path",
                d=segs["pct"][1],
                fill="none",
                stroke="#C9A86A",
                stroke_width=6.4 * s,
                stroke_dasharray=f"{fmt(0.5 * s)} {fmt(0.9 * s)}",
                stroke_opacity=0.8,
            )
        )
        look.append(_el("path", d=segs["pct"][1], fill="none", stroke=lum, stroke_width=4.2 * s))
        look.append(
            _el(
                "path",
                d=gd,
                fill="none",
                stroke="#FFFFFF",
                stroke_width=0.7 * s,
                stroke_opacity=0.5,
                stroke_linecap="round",
            )
        )
        defs.append(_radial("nbow", "#FFFFFF", _mix(tubule, "#7A4A30", 0.2)))
        look.append(_el("circle", cx=cx, cy=cy, r=R, fill="url(#nbow)", fill_opacity=0.25))
        holder.append(look)
    ports = dict(
        glomerulus=(cx, cy + 4 * s),
        bowman=(cx - R + 1.6 * s, cy - 6 * s),
        afferent=aff[1],
        efferent=eff[1],
        pct=P([(96, 118)])[0],
        loop_desc=P([(114, 280)])[0],
        loop_asc=P([(140, 220)])[0],
        dct=P([(196, 82)])[0],
        macula_densa=md,
        cd=P([(264, 230)])[0],
        cortex=(18 * s, 140 * s),
        medulla=(18 * s, 300 * s),
        loop=P([(126, 376)])[0],
    )
    return _finish(holder, defs, Box(0, 0, W, H), **ports)


def _ring(cx, cy, r0, r1, a0, a1, n=24):
    """Annular sector between radii r0/r1 and angles a0→a1 (radians)."""
    out = [
        (cx + r1 * math.cos(a0 + (a1 - a0) * k / n), cy + r1 * math.sin(a0 + (a1 - a0) * k / n)) for k in range(n + 1)
    ]
    out += [
        (cx + r0 * math.cos(a1 - (a1 - a0) * k / n), cy + r0 * math.sin(a1 - (a1 - a0) * k / n)) for k in range(n + 1)
    ]
    return out


@_drawing_api(
    "parts",
    purpose="血脑屏障神经血管单元横切（教科书级）：毛细血管腔（含红细胞）、2–3 个内皮细胞环绕并以紧密连接封闭、基底膜、嵌于基底膜内的周细胞、星形胶质细胞终足包绕血管并经突起连到胞体、周围脑实质。",
    returns="Geometry（原点在中心；端口 lumen/endothelium/tight_junction/tight_junction{k}/basement_membrane/pericyte/endfoot/astrocyte/brain）",
    semantics=(
        "width 为宽度（近正方形）；毛细血管在中央，星形胶质细胞胞体在右上。",
        "cells 为内皮细胞数（2 或 3）；leaky=True 把紧密连接画成断开（屏障破坏示意）。",
        'style="rich" 加明暗（一个局部 SVG），"flat" 全原生；转运箭头用 d.arrow(u.port("lumen"), u.port("brain"))。',
    ),
    example='u = d.place(bbb_unit(260), at=(300, 250), key="bbb")\n'
    'd.callout("tj", "紧密连接（claudin-5）", u.port("tight_junction"), at=(520, 120), font_size=12)',
    rank=29,
)
def bbb_unit(
    width=300,
    *,
    cells=3,
    leaky=False,
    endothelium="#E9B7A8",
    astrocyte="#B9CFA0",
    pericyte="#C9A3CF",
    blood="#C8474E",
    style="rich",
):
    rich = _style(style)
    _finite(width)
    if cells not in (2, 3):
        raise ValueError("cells must be 2 or 3")
    s = width / 300.0
    W = H = 300 * s
    cx, cy = 128 * s, 160 * s
    r_l, r_e, r_bm, r_ef = 44 * s, 58 * s, 61 * s, 80 * s
    holder, defs = _el("g"), _el("defs")
    holder.append(defs)
    ports = {}
    brain = "#F2E8DA"
    holder.append(
        _el(
            "rect",
            x=0,
            y=0,
            width=W,
            height=H,
            rx=6 * s,
            fill=brain,
            stroke=_mix(brain, "#7A6040", 0.3),
            stroke_width=_sw(0.8 * s),
            data_outline="1",
        )
    )
    rnd = random.Random(5)
    np_ = [_circ(rnd.uniform(6, 294) * s, rnd.uniform(6, 294) * s, rnd.uniform(1.4, 3.4) * s) for _ in range(90)]
    holder.append(
        _el("path", d=" ".join(np_), fill="none", stroke=_mix(brain, "#8A7050", 0.3), stroke_width=_sw(0.5 * s))
    )
    ax, ay = 248 * s, 56 * s
    ast_e = _mix(astrocyte, "#2A4018", 0.45)
    procs = []
    for a_end, bend in ((-0.9, 10), (-0.25, -8), (0.45, 6)):
        e = (cx + (r_ef - 4 * s) * math.cos(a_end), cy + (r_ef - 4 * s) * math.sin(a_end))
        m = ((ax + e[0]) / 2 + bend * s, (ay + e[1]) / 2 + bend * s)
        procs.append(_smooth(_tube([(ax, ay), m, e], 9 * s, 6 * s, per=6)[0], closed=True))
    for a in (-2.4, -1.6, -0.4, 0.2):
        procs.append(
            _smooth(
                _tube(
                    [
                        (ax, ay),
                        (ax + 22 * s * math.cos(a), ay + 22 * s * math.sin(a)),
                        (ax + 40 * s * math.cos(a + 0.2), ay + 40 * s * math.sin(a + 0.2)),
                    ],
                    6 * s,
                    1.5 * s,
                    per=5,
                )[0],
                closed=True,
            )
        )
    # endfeet: 5 lobes tiling the outer ring, small clefts between them
    feet = []
    gaps = [math.radians(g) for g in (-118, -40, 30, 104, 178)]
    for k, g0 in enumerate(gaps):
        g1 = gaps[(k + 1) % len(gaps)] + (2 * math.pi if k == len(gaps) - 1 else 0)
        sec = _ring(cx, cy, r_bm + 0.4 * s, r_ef, g0 + 0.035, g1 - 0.035)
        feet.append(_smooth(sec, closed=True))
    holder.append(_el("path", d=" ".join(procs + feet), fill=astrocyte, stroke=ast_e, stroke_width=_sw(0.8 * s)))
    holder.append(
        _el("ellipse", cx=ax, cy=ay, rx=20 * s, ry=17 * s, fill=astrocyte, stroke=ast_e, stroke_width=_sw(0.9 * s))
    )
    holder.append(
        _el("ellipse", cx=ax + 1 * s, cy=ay, rx=9 * s, ry=7.5 * s, fill=_mix(astrocyte, "#3A5A2A", 0.45), stroke="none")
    )
    fil = [
        _d([(cx + r * math.cos(a), cy + r * math.sin(a)) for a in (a0 + 0.12 * j for j in range(4))], False)
        for a0 in (-1.9, -0.7, 0.5, 1.6, 2.7)
        for r in (r_bm + 9 * s,)
    ]
    holder.append(
        _el("path", d=" ".join(fil), fill="none", stroke=_mix(astrocyte, "#3A5A2A", 0.3), stroke_width=_sw(0.6 * s))
    )
    bm = "#D8C8A8"
    holder.append(
        _el("circle", cx=cx, cy=cy, r=r_bm, fill=bm, stroke=_mix(bm, "#5A4A20", 0.45), stroke_width=_sw(0.6 * s))
    )
    pa0, pa1 = math.radians(120), math.radians(200)
    per = _ring(cx, cy, r_e + 0.8 * s, r_bm + 7 * s, pa0, pa1)
    holder.append(
        _el(
            "path",
            d=_smooth(per, closed=True),
            fill=pericyte,
            stroke=_mix(pericyte, "#3A2050", 0.45),
            stroke_width=_sw(0.8 * s),
        )
    )
    pm = (pa0 + pa1) / 2
    holder.append(
        _el(
            "path",
            d=_oval(
                cx + (r_bm + 2.6 * s) * math.cos(pm),
                cy + (r_bm + 2.6 * s) * math.sin(pm),
                11 * s,
                3.4 * s,
                pm + math.pi / 2,
            ),
            fill=_mix(pericyte, "#3A2050", 0.5),
            stroke="none",
        )
    )
    holder.append(
        _el(
            "path",
            d=_d(_ring(cx, cy, r_bm + 7 * s, r_bm + 7 * s, pa0, pa1)[:25], False),
            fill="none",
            stroke=_mix(bm, "#5A4A20", 0.45),
            stroke_width=_sw(0.6 * s),
        )
    )
    holder.append(_el("circle", cx=cx, cy=cy, r=r_e, fill="#FBEFEA", stroke="none"))
    endo_e = _mix(endothelium, "#5A2018", 0.45)
    seams = [math.radians(-80 + 360 * k / cells) for k in range(cells)]
    cells_d, nucs, tj = [], [], []
    for k, a0 in enumerate(seams):
        a1 = seams[(k + 1) % cells] + (2 * math.pi if k == cells - 1 else 0)
        n = 40
        mid = (a0 + a1) / 2
        outer, inner = [], []
        for j in range(n + 1):
            a = a0 + (a1 - a0) * j / n
            bulge = 6 * s * math.exp(-(((a - mid) / 0.32) ** 2))
            outer.append((cx + r_e * math.cos(a), cy + r_e * math.sin(a)))
            inner.append((cx + (r_l - bulge) * math.cos(a), cy + (r_l - bulge) * math.sin(a)))
        cells_d.append(_smooth(outer + inner[::-1], closed=True))
        rn = (r_e + r_l - 6 * s) / 2
        nucs.append(_oval(cx + rn * math.cos(mid), cy + rn * math.sin(mid), 13 * s, 4.6 * s, mid + math.pi / 2))
        # overlapping cell margins at the seam, sealed by a tight-junction strand
        p0 = (cx + r_l * math.cos(a0), cy + r_l * math.sin(a0))
        p1 = (cx + r_e * math.cos(a0 + 0.05), cy + r_e * math.sin(a0 + 0.05))
        tj.append((p0, p1, a0))
    holder.append(_el("path", d=" ".join(cells_d), fill=endothelium, stroke=endo_e, stroke_width=_sw(0.8 * s)))
    holder.append(
        _el("path", d=" ".join(nucs), fill="#6A5796", stroke=_mix("#6A5796", "#000000", 0.3), stroke_width=_sw(0.4 * s))
    )
    tjd = []
    for k, (p0, p1, a0) in enumerate(tj):
        holder.append(_el("path", d=_d([p0, p1], False), fill="none", stroke=endo_e, stroke_width=_sw(0.9 * s)))
        for f in (0.2, 0.5, 0.8) if not leaky else (0.2, 0.8):
            q = (p0[0] + (p1[0] - p0[0]) * f, p0[1] + (p1[1] - p0[1]) * f)
            tjd.append(_circ(q[0], q[1], 1.8 * s))
        ports[f"tight_junction{k}"] = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2)
    holder.append(_el("path", d=" ".join(tjd), fill="#2F2440", stroke="none"))
    rb = (cx + 4 * s, cy + 2 * s)
    holder.append(
        _el(
            "path",
            d=_oval(rb[0], rb[1], 21 * s, 9 * s, -0.35),
            fill=blood,
            stroke=_mix(blood, "#3A0A10", 0.45),
            stroke_width=_sw(0.8 * s),
        )
    )
    holder.append(
        _el("path", d=_oval(rb[0], rb[1], 10 * s, 3.4 * s, -0.35), fill=_mix(blood, "#3A0A10", 0.25), stroke="none")
    )
    if rich:
        look = _look()
        defs.append(_radial("bbbl", "#FFFFFF", "#E8D0C8"))
        look.append(_el("circle", cx=cx, cy=cy, r=r_l - 6 * s, fill="url(#bbbl)", fill_opacity=0.35))
        look.append(
            _el("path", d=_oval(rb[0] - 6 * s, rb[1] - 4 * s, 6 * s, 1.6 * s, -0.35), fill="#FFFFFF", fill_opacity=0.4)
        )
        defs.append(_radial("bbba", "#FFFFFF", _mix(astrocyte, "#2A4018", 0.3)))
        look.append(_el("ellipse", cx=ax, cy=ay, rx=20 * s, ry=17 * s, fill="url(#bbba)", fill_opacity=0.35))
        holder.append(look)
    fa = math.radians(-5)
    ports.update(
        lumen=(cx - 14 * s, cy - 16 * s),
        endothelium=(cx + (r_e - 3 * s) * math.cos(-2.4), cy + (r_e - 3 * s) * math.sin(-2.4)),
        tight_junction=ports["tight_junction0"],
        basement_membrane=(cx + r_bm * math.cos(2.6 + 0.9), cy + r_bm * math.sin(2.6 + 0.9)),
        pericyte=(cx + (r_bm + 3 * s) * math.cos(pm), cy + (r_bm + 3 * s) * math.sin(pm)),
        endfoot=(cx + (r_ef - 8 * s) * math.cos(fa), cy + (r_ef - 8 * s) * math.sin(fa)),
        astrocyte=(ax, ay),
        brain=(40 * s, 268 * s),
        rbc=rb,
    )
    return _finish(holder, defs, Box(0, 0, W, H), **ports)


def _cell_sector(cx, cy, r0, r1, a0, a1, gap):
    """Rounded cell outline filling an annular sector, inset by ``gap``."""
    rm = (r0 + r1) / 2
    da = gap / max(rm, 1e-6)
    a0, a1, r0, r1 = a0 + da, a1 - da, r0 + gap, r1 - gap
    pts = []
    for k in range(4):
        a = a0 + (a1 - a0) * k / 3
        pts.append((cx + r1 * math.cos(a), cy + r1 * math.sin(a)))
    for k in range(4):
        a = a1 - (a1 - a0) * k / 3
        pts.append((cx + r0 * math.cos(a), cy + r0 * math.sin(a)))
    return _smooth(pts, closed=True)


@_drawing_api(
    "parts",
    purpose="根横切面（教科书级，双子叶幼根初生结构）：表皮与根毛、多层薄壁皮层（细胞间隙）、凯氏带突出显示的内皮层、中柱鞘、中柱内星芒状初生木质部（中央大导管、外始式原生木质部）与位于木质部辐角之间的韧皮部；pathways=True 画质外体/共质体途径。",
    returns="Geometry（原点在中心；端口 soil/root_hair/epidermis/cortex/endodermis/casparian/pericycle/stele/xylem/phloem；pathways 时另有 apoplast/symplast 起点与 apoplast_block 阻断点）",
    semantics=(
        "width 为整体宽度（含根毛），横切面为圆形；arms 为木质部辐角数（2–6，默认 4 = 四原型）；cortex_rings 为皮层细胞层数（3–6）。",
        "凯氏带画在内皮层细胞的径向壁上（深色木栓质/木质带 + 浅色光晕），在小尺寸下也能认出。",
        "pathways=True：右上扇区画蓝色虚线质外体途径（沿细胞壁与胞间隙穿过皮层，在凯氏带处被“⊣”阻断）与橙色实线共质体途径（经胞间连丝逐个穿过细胞，直达木质部）；图例由调用方用 legend_row 补。",
        'style="rich" 加明暗与壁纹（一个局部 SVG），"flat" 全原生；标注用 d.callout("c", "凯氏带", r.port("casparian"), ...)。',
    ),
    example='r = d.place(root_section(340, pathways=True), at=(260, 240), key="root")\n'
    'd.callout("cs", "凯氏带", r.port("casparian"), at=(520, 120), font_size=13)\n'
    'd.callout("xy", "木质部", r.port("xylem"), at=(520, 300), font_size=13)',
    rank=30,
)
def root_section(
    width=320,
    *,
    arms=4,
    cortex_rings=4,
    pathways=False,
    hairs=True,
    epidermis="#E6EDC8",
    cortex="#F4EED9",
    endodermis="#E9D8A6",
    casparian="#8C3A1E",
    xylem="#B8473A",
    phloem="#7FB069",
    style="rich",
    seed=4,
):
    rich = _style(style)
    _finite(width)
    if not 2 <= int(arms) <= 6:
        raise ValueError("arms must be 2..6")
    if not 3 <= int(cortex_rings) <= 6:
        raise ValueError("cortex_rings must be 3..6")
    arms, cortex_rings = int(arms), int(cortex_rings)
    rnd = random.Random(seed)
    R = width / 2
    cx = cy = R
    Rb = R * (0.84 if hairs else 0.99)
    s = Rb / 140.0
    r_ep0, r_cx0, r_en0, r_pc0 = Rb * 0.9, Rb * 0.47, Rb * 0.405, Rb * 0.355
    wall_c = "#8A7F5A"
    sw = _sw(0.55 * s)
    holder, defs = _el("g"), _el("defs")
    holder.append(defs)
    ports = {}
    # 1. native outline: whole root disc (walls/intercellular space colour)
    holder.append(
        _el(
            "circle",
            cx=cx,
            cy=cy,
            r=Rb,
            fill=_mix(cortex, wall_c, 0.35),
            stroke=_mix(epidermis, "#3A4A10", 0.5),
            stroke_width=_sw(1.1 * s),
            data_outline="1",
        )
    )
    # 2. root hairs: tubular outgrowths of single epidermal cells (trichoblasts)
    n_ep = max(24, int(2 * math.pi * (r_ep0 + Rb) / 2 / (11 * s)))
    hair_d, hair_idx = [], []
    if hairs:
        for k in range(n_ep):
            if k % 3 != 1:
                continue
            a = 2 * math.pi * (k + 0.5) / n_ep
            bend = rnd.uniform(-0.25, 0.25)
            L = R - Rb
            ctrl = [(cx + (Rb - 2 * s) * math.cos(a), cy + (Rb - 2 * s) * math.sin(a))]
            for f in (0.35, 0.7, 1.0):
                aa = a + bend * f * L / Rb
                rr = Rb + L * f * rnd.uniform(0.86, 0.98)
                ctrl.append((cx + rr * math.cos(aa), cy + rr * math.sin(aa)))
            hair_d.append(_smooth(_tube(ctrl, 5 * s, 3.6 * s, per=6)[0], closed=True))
            hair_idx.append(k)
        holder.append(
            _el("path", d=" ".join(hair_d), fill=epidermis, stroke=_mix(epidermis, "#3A4A10", 0.45), stroke_width=sw)
        )
    # 3. epidermis: one ring of brick-like cells
    ep = [
        _cell_sector(cx, cy, r_ep0, Rb, 2 * math.pi * k / n_ep, 2 * math.pi * (k + 1) / n_ep, 0.7 * s)
        for k in range(n_ep)
    ]
    holder.append(_el("path", d=" ".join(ep), fill=epidermis, stroke=_mix(epidermis, "#3A4A10", 0.35), stroke_width=sw))
    # 4. cortex: rings of rounded parenchyma cells with triangular intercellular spaces; inner rings in radial rows
    th = (r_ep0 - r_cx0) / cortex_rings
    cells = []
    centers = []
    for k in range(cortex_rings):
        frac = k / max(1, cortex_rings - 1)
        r0 = r_cx0 + th * k
        rr = r0 + th / 2
        rad = th * 0.5 * (0.94 + 0.06 * frac)
        n = max(10, int(2 * math.pi * rr / (2 * rad * (1.02 + 0.1 * frac))))
        off = rnd.uniform(0, 1)
        ring = []
        for j in range(n):
            a = 2 * math.pi * (j + off) / n
            jitter = 1 + rnd.uniform(-0.05, 0.05)
            px, py = cx + rr * math.cos(a), cy + rr * math.sin(a)
            ring.append((a, px, py))
            cells.append(
                _oval(px, py, rad * jitter * 0.96, rad * min(1.12, 2 * math.pi * rr / n / (2 * rad)) * 0.92, a)
            )
        centers.append((rr, ring))
    holder.append(_el("path", d=" ".join(cells), fill=cortex, stroke=_mix(cortex, wall_c, 0.55), stroke_width=sw))
    # 5. endodermis: one ring of compact brick cells; Casparian strip in every radial (anticlinal) wall
    n_en = max(16, int(2 * math.pi * (r_en0 + r_cx0) / 2 / (9.5 * s)))
    en = [
        _cell_sector(cx, cy, r_en0, r_cx0, 2 * math.pi * k / n_en, 2 * math.pi * (k + 1) / n_en, 0.55 * s)
        for k in range(n_en)
    ]
    holder.append(
        _el("path", d=" ".join(en), fill=endodermis, stroke=_mix(endodermis, wall_c, 0.7), stroke_width=_sw(0.7 * s))
    )
    halo, strip = [], []
    r_cs = (r_en0 + r_cx0) / 2
    for k in range(n_en):
        a = 2 * math.pi * k / n_en
        ux, uy = math.cos(a), math.sin(a)
        p0 = (cx + (r_cs - 2.2 * s) * ux, cy + (r_cs - 2.2 * s) * uy)
        p1 = (cx + (r_cs + 2.2 * s) * ux, cy + (r_cs + 2.2 * s) * uy)
        halo.append(_oval(cx + r_cs * ux, cy + r_cs * uy, 3.6 * s, 2.0 * s, a))
        strip.append(_d([p0, p1], False))
    holder.append(_el("path", d=" ".join(halo), fill=_mix(casparian, "#FFFFFF", 0.55), stroke="none"))
    holder.append(
        _el("path", d=" ".join(strip), fill="none", stroke=casparian, stroke_width=_sw(2.0 * s), stroke_linecap="round")
    )
    # 6. pericycle
    n_pc = max(14, int(2 * math.pi * (r_pc0 + r_en0) / 2 / (7.5 * s)))
    pc = [
        _cell_sector(cx, cy, r_pc0, r_en0, 2 * math.pi * (k + 0.5) / n_pc, 2 * math.pi * (k + 1.5) / n_pc, 0.5 * s)
        for k in range(n_pc)
    ]
    pc_col = _mix(cortex, "#C9D6A0", 0.4)
    holder.append(_el("path", d=" ".join(pc), fill=pc_col, stroke=_mix(pc_col, wall_c, 0.6), stroke_width=sw))
    # 7. stele: parenchyma background, xylem star (exarch: small protoxylem at the arm tips, big metaxylem at the centre)
    stele_bg = _mix(cortex, "#E8E0C0", 0.5)
    holder.append(
        _el("circle", cx=cx, cy=cy, r=r_pc0, fill=stele_bg, stroke=_mix(stele_bg, wall_c, 0.5), stroke_width=sw)
    )
    a_off = -math.pi / 2 + (math.pi / arms if arms % 2 == 0 else 0) + math.pi / 4 * (arms == 4)
    star = []
    rs_out, rs_in = r_pc0 - 2.5 * s, r_pc0 * 0.36
    for k in range(arms * 2):
        a = a_off + math.pi * k / arms
        rr = rs_out if k % 2 == 0 else rs_in
        star.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    xl = _mix(xylem, "#FFFFFF", 0.7)
    holder.append(
        _el(
            "path", d=_smooth(star, closed=True), fill=xl, stroke=_mix(xylem, "#FFFFFF", 0.2), stroke_width=_sw(0.8 * s)
        )
    )
    vessels = [(cx, cy, r_pc0 * 0.2)]
    for k in range(arms):
        a = a_off + 2 * math.pi * k / arms
        ux, uy = math.cos(a), math.sin(a)
        for f, vr in ((0.4, 0.135), (0.62, 0.095), (0.8, 0.065), (0.93, 0.042)):
            rr = r_pc0 * f
            vessels.append((cx + rr * ux, cy + rr * uy, r_pc0 * vr))
    holder.append(
        _el(
            "path",
            d=" ".join(_circ(x, y, r) for x, y, r in vessels),
            fill="#FFFFFF",
            stroke=xylem,
            stroke_width=_sw(1.6 * s),
        )
    )
    # 8. phloem: between the xylem arms, sieve tubes (larger, pale) + companion cells (small, dense)
    ph_pts = []
    ph_cells, comp = [], []
    for k in range(arms):
        a = a_off + 2 * math.pi * (k + 0.5) / arms
        ux, uy = math.cos(a), math.sin(a)
        pr = r_pc0 * 0.7
        px, py = cx + pr * ux, cy + pr * uy
        ph_pts.append((px, py))
        pw = min(r_pc0 * 0.27, math.pi * pr / arms * 0.6)
        holder.append(
            _el(
                "path",
                d=_oval(px, py, r_pc0 * 0.17, pw, a),
                fill=phloem,
                stroke=_mix(phloem, "#1E3A10", 0.45),
                stroke_width=_sw(0.8 * s),
            )
        )
        for j, (dr, dt, rr_) in enumerate(
            (
                (-0.05, -0.42, 0.055),
                (-0.05, 0.42, 0.055),
                (0.06, 0, 0.06),
                (-0.08, 0, 0.05),
                (0.07, -0.55, 0.045),
                (0.07, 0.55, 0.045),
            )
        ):
            tx, ty = -uy, ux
            x = px + ux * r_pc0 * dr + tx * pw * dt
            y = py + uy * r_pc0 * dr + ty * pw * dt
            ph_cells.append(_circ(x, y, r_pc0 * rr_))
            comp.append(_circ(x + tx * r_pc0 * rr_ * 1.1, y + ty * r_pc0 * rr_ * 1.1, r_pc0 * 0.022))
    holder.append(
        _el(
            "path",
            d=" ".join(ph_cells),
            fill=_mix(phloem, "#FFFFFF", 0.55),
            stroke=_mix(phloem, "#1E3A10", 0.35),
            stroke_width=sw,
        )
    )
    holder.append(_el("path", d=" ".join(comp), fill=_mix(phloem, "#1E3A10", 0.55), stroke="none"))
    if rich:
        look = _look()
        defs.append(_radial("rsec", "#FFFFFF", "#000000", fx=0.4, fy=0.36))
        look.append(_el("circle", cx=cx, cy=cy, r=Rb, fill="url(#rsec)", fill_opacity=0.1))
        # nuclei in a few cortex cells, starch grains (amyloplasts) in inner cortex
        nuc = []
        for rr, ring in centers[1:]:
            for a, px, py in ring[::4]:
                nuc.append(_circ(px + 1.2 * s * math.cos(a + 1), py + 1.2 * s * math.sin(a + 1), 1.4 * s))
        look.append(_el("path", d=" ".join(nuc), fill=_mix(cortex, "#6A5A3A", 0.55), fill_opacity=0.6))
        look.append(
            _el(
                "path",
                d=" ".join(_circ(x - r * 0.3, y - r * 0.3, r * 0.3) for x, y, r in vessels),
                fill=xl,
                fill_opacity=0.6,
            )
        )
        holder.append(look)
    # 9. transport pathways (upper-right sector)
    if pathways:
        ap_c, sy_c = "#2E6FB0", "#D9822B"
        a_ap = math.radians(-38)
        # apoplast: along walls between cells — weave through the intercellular spaces at each ring boundary
        pts = [(cx + (R - 4 * s) * math.cos(a_ap), cy + (R - 4 * s) * math.sin(a_ap))]
        for k in range(cortex_rings + 1):
            rr = r_ep0 - th * k
            wob = (1 if k % 2 else -1) * 0.022
            pts.append((cx + rr * math.cos(a_ap + wob), cy + rr * math.sin(a_ap + wob)))
        stop = (cx + (r_cs + 3.2 * s) * math.cos(a_ap), cy + (r_cs + 3.2 * s) * math.sin(a_ap))
        pts[-1] = stop
        holder.append(
            _el(
                "path",
                d=_d(pts, False),
                fill="none",
                stroke=ap_c,
                stroke_width=_sw(1.9 * s),
                stroke_dasharray=f"{fmt(4 * s)} {fmt(2.6 * s)}",
                stroke_linecap="round",
                stroke_linejoin="round",
            )
        )
        ux, uy = math.cos(a_ap), math.sin(a_ap)
        tx, ty = -uy, ux
        bar = [(stop[0] + tx * 5 * s, stop[1] + ty * 5 * s), (stop[0] - tx * 5 * s, stop[1] - ty * 5 * s)]
        holder.append(
            _el("path", d=_d(bar, False), fill="none", stroke=ap_c, stroke_width=_sw(2.6 * s), stroke_linecap="round")
        )
        ports.update(apoplast=pts[0], apoplast_block=stop)
        # symplast: from a root hair through cell centres (plasmodesmata dots on each wall) into the xylem
        a_sy = math.radians(-58)
        sp = [(cx + (R - 6 * s) * math.cos(a_sy), cy + (R - 6 * s) * math.sin(a_sy))]
        dots = []
        for rr, ring in centers[::-1]:
            best = min(ring, key=lambda c: abs(math.atan2(math.sin(c[0] - a_sy), math.cos(c[0] - a_sy))))
            sp.append((best[1], best[2]))
        sp.append((cx + (r_en0 + r_cx0) / 2 * math.cos(a_sy + 0.07), cy + (r_en0 + r_cx0) / 2 * math.sin(a_sy + 0.07)))
        tgt_arm = min(
            range(arms),
            key=lambda k: abs(
                math.atan2(
                    math.sin(a_off + 2 * math.pi * k / arms - a_sy), math.cos(a_off + 2 * math.pi * k / arms - a_sy)
                )
            ),
        )
        aa = a_off + 2 * math.pi * tgt_arm / arms
        aa = a_sy + math.atan2(math.sin(aa - a_sy), math.cos(aa - a_sy))  # same branch as a_sy (no wrap-around)
        sp.append(
            (cx + (r_pc0 + r_en0) / 2 * math.cos((aa + a_sy) / 2), cy + (r_pc0 + r_en0) / 2 * math.sin((aa + a_sy) / 2))
        )
        tip = (cx + r_pc0 * 0.8 * math.cos(aa), cy + r_pc0 * 0.8 * math.sin(aa))
        sp.append(tip)
        for p, q in zip(sp[1:-1], sp[2:]):
            dots.append(_circ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2, 1.5 * s))
        curve = _cr(sp, 6)
        holder.append(
            _el(
                "path",
                d=_d(curve[:-2], False),
                fill="none",
                stroke=sy_c,
                stroke_width=_sw(1.9 * s),
                stroke_linecap="round",
                stroke_linejoin="round",
            )
        )
        ex, ey = curve[-1]
        bx, by = curve[-4]
        L = math.hypot(ex - bx, ey - by) or 1
        holder.append(_head(ex, ey, (ex - bx) / L, (ey - by) / L, 6 * s, sy_c))
        holder.append(_el("path", d=" ".join(dots), fill="#FFFFFF", stroke=sy_c, stroke_width=_sw(0.8 * s)))
        ports["symplast"] = sp[0]
    a_lab = math.radians(150)
    ux, uy = math.cos(a_lab), math.sin(a_lab)
    rr_cx = centers[cortex_rings // 2][0]
    ports.update(
        soil=(cx + (Rb + (R - Rb) * 0.6) * math.cos(2.3), cy + (Rb + (R - Rb) * 0.6) * math.sin(2.3)),
        epidermis=(cx + (r_ep0 + Rb) / 2 * ux, cy + (r_ep0 + Rb) / 2 * uy),
        cortex=(cx + rr_cx * ux, cy + rr_cx * uy),
        endodermis=(cx + r_cs * math.cos(a_lab + 0.2), cy + r_cs * math.sin(a_lab + 0.2)),
        casparian=(
            cx + r_cs * math.cos(2 * math.pi * round((a_lab - 0.3) / (2 * math.pi) * n_en) / n_en),
            cy + r_cs * math.sin(2 * math.pi * round((a_lab - 0.3) / (2 * math.pi) * n_en) / n_en),
        ),
        pericycle=(cx + (r_pc0 + r_en0) / 2 * math.cos(a_lab + 0.5), cy + (r_pc0 + r_en0) / 2 * math.sin(a_lab + 0.5)),
        stele=(cx, cy),
        xylem=vessels[0][:2],
        phloem=ph_pts[0],
    )
    if hair_idx:
        k = hair_idx[len(hair_idx) // 3]
        a = 2 * math.pi * (k + 0.5) / n_ep
        ports["root_hair"] = (cx + (Rb + R) / 2 * math.cos(a), cy + (Rb + R) / 2 * math.sin(a))
    return _finish(holder, defs, Box(0, 0, 2 * R, 2 * R), **ports)
