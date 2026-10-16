"""Bacterial envelope and biofilm parts drawn like Nature Reviews Microbiology figures."""

from __future__ import annotations

import math
import random

from ..atomize_svg_to_slide._geometry import fmt
from ._bio_parts import (
    _el,
    _look,
    _mix,
    _circ,
    _smooth,
    _poly,
    _linear,
    _check_style,
    _finish,
    _lipid_rows,
    _lipid_group,
)
from ._construction import _inside
from ._geometry import Box, PathFrame, _finite, _hits, label
from ._help import _drawing_api
from ._parts import _INK

_PROTEINS = ("tripartite_pump", "porin", "abc", "mfs", "channel")
_SPANS_OM = ("tripartite_pump", "porin")
_DEFAULT_COLOR = {
    "tripartite_pump": "#3A7FC1",
    "porin": "#3E9A8A",
    "abc": "#5B4BA8",
    "mfs": "#C0605A",
    "channel": "#2E8B57",
}


def _text(x, y, s, fs, fill, *, anchor="start", bold=True):
    t = _el("text", x=x, y=y, font_size=fs, fill=fill, text_anchor=anchor, font_weight="bold" if bold else None)
    t.text = str(s)
    return t


def _tbox(x, y, s, fs, anchor="start", bold=True):
    w = label(str(s), font_size=fs, font_weight="bold" if bold else "normal").bounds.width
    x0 = x - (w / 2 if anchor == "middle" else w if anchor == "end" else 0)
    return Box(x0, y - fs * 0.92, w, fs * 1.2)


def _rod(x, y, w, h, fill, edge=None, sw=0.8):
    """Rounded vertical rod (a transmembrane helix / strand)."""
    return _el(
        "rect",
        x=x,
        y=y,
        width=w,
        height=h,
        rx=min(w, h) / 2,
        fill=fill,
        stroke=edge or "none",
        stroke_width=sw if edge else None,
    )


def _hexes(points, r):
    d = []
    for cx, cy in points:
        d.append(
            _poly(
                [
                    (cx + r * math.cos(math.pi / 3 * k + math.pi / 6), cy + r * math.sin(math.pi / 3 * k + math.pi / 6))
                    for k in range(6)
                ]
            )
        )
    return " ".join(d)


def _drug(cx, cy, r, color="#D23B3B"):
    """Small two-ring drug molecule glyph (fused hexagons), one native path."""
    dx = r * math.sqrt(3)
    return _el(
        "path",
        d=_hexes([(cx - dx / 2, cy), (cx + dx / 2, cy)], r),
        fill=color,
        stroke=_mix(color, "#000000", 0.4),
        stroke_width=0.9,
        stroke_linejoin="round",
    )


def _segments(x0, x1, holes, pad=0.0):
    """Complement of hole intervals inside [x0, x1]."""
    out, cur = [], x0
    for a, b in sorted(holes):
        if a - pad > cur:
            out.append((cur, a - pad))
        cur = max(cur, b + pad)
    if x1 > cur:
        out.append((cur, x1))
    return [(a, b) for a, b in out if b - a > 6]


def _bilayer_strip(x0, x1, y, T, color, rich, seed, *, lps=None):
    """Straight bilayer from x0 to x1 at midline y. Returns (native band, look-or-native group, outer head xs)."""
    from ._geometry import Curve

    curve = Curve(f"M{fmt(x0)} {fmt(y)} L{fmt(x1)} {fmt(y)}", tolerance=0.3)
    rows = _lipid_rows(curve, T, color, closed=False, inward=1, seed=seed)
    head = T * 0.17
    n = max(4, int(curve.length / (head * 2.25)))
    step = curve.length / max(1, n - 1)
    xs = [x0 + i * step for i in range(n)]
    if lps:
        rows["heads_out"] = []
    band = _el("rect", x=x0, y=y - T * 0.39, width=x1 - x0, height=T * 0.78, fill=_mix(color, "#FFFFFF", 0.78))
    return band, _lipid_group(rows, T, color, native=not rich), xs


def _tripartite(g, x, ys, colors, rich, rnd):
    """AcrB (IM) + AcrA hairpins (periplasm) + TolC (OM barrel + periplasmic α-tunnel). Returns ports."""
    om_t, om_b, im_t, im_b, T = ys
    P = im_t - om_b
    cb, ca, ct = colors
    eb, ea, et = (_mix(c, "#000000", 0.38) for c in colors)
    nh, hw = 9, 7.5
    tw = nh * hw + (nh - 1) * 1.6
    for k in range(nh):
        hx = x - tw / 2 + k * (hw + 1.6)
        fill = cb if k % 2 == 0 else _mix(cb, "#FFFFFF", 0.25)
        g.append(_rod(hx, im_t - 3, hw, T + 6, fill, eb if rich else None))
    top = im_t - P * 0.47
    base_w = tw + 14
    for k, (dxa, shade) in enumerate(((-1, 0.18), (1, 0.0), (0, 0.32))):
        cx = x + dxa * base_w * 0.22
        w = base_w * (0.5 if dxa else 0.44)
        pts = [
            (cx - w / 2, im_t - 1),
            (cx - w * 0.56, im_t - P * 0.16),
            (cx - w * 0.4, im_t - P * 0.3),
            (cx - w * 0.24, top + 6),
            (cx + w * 0.24, top + 6),
            (cx + w * 0.4, im_t - P * 0.3),
            (cx + w * 0.56, im_t - P * 0.16),
            (cx + w / 2, im_t - 1),
        ]
        g.append(_el("path", d=_smooth(pts, closed=True), fill=_mix(cb, "#FFFFFF", shade), stroke=eb, stroke_width=1))
    # funnel (docking) domain where TolC meets AcrB
    g.append(
        _el(
            "path",
            d=_poly([(x - 20, top + 10), (x - 15, top - 2), (x + 15, top - 2), (x + 20, top + 10)]),
            fill=_mix(cb, "#FFFFFF", 0.1),
            stroke=eb,
            stroke_width=1,
            stroke_linejoin="round",
        )
    )
    # entry cleft (substrate vestibule) between protomers on the periplasmic/IM side
    cleft = (x - base_w * 0.36, im_t - P * 0.14)
    g.append(
        _el(
            "path",
            d=f"M{fmt(cleft[0] - 7)} {fmt(cleft[1] + 6)} Q{fmt(cleft[0] + 4)} {fmt(cleft[1])} {fmt(cleft[0] + 12)} "
            f"{fmt(cleft[1] - 10)}",
            fill="none",
            stroke=_mix(cb, "#000000", 0.55),
            stroke_width=2.2,
            stroke_linecap="round",
        )
    )
    t_bot = top - 1
    wt = 38
    tun = [
        (x - wt / 2, om_b + 1),
        (x - wt / 2, t_bot - 14),
        (x - wt * 0.36, t_bot),
        (x + wt * 0.36, t_bot),
        (x + wt / 2, t_bot - 14),
        (x + wt / 2, om_b + 1),
    ]
    g.append(_el("path", d=_poly(tun), fill=ct, stroke=et, stroke_width=1, stroke_linejoin="round"))
    wb = 44
    g.append(
        _el(
            "rect",
            x=x - wb / 2,
            y=om_t - 4,
            width=wb,
            height=om_b - om_t + 6,
            rx=5,
            fill=_mix(ct, "#FFFFFF", 0.12),
            stroke=et,
            stroke_width=1,
        )
    )
    # lumen running through TolC (open state, continuous with the AcrB funnel)
    g.append(
        _el(
            "path",
            d=_poly(
                [
                    (x - 6.5, om_t - 4),
                    (x - 6.5, t_bot - 12),
                    (x - 4, t_bot - 1),
                    (x + 4, t_bot - 1),
                    (x + 6.5, t_bot - 12),
                    (x + 6.5, om_t - 4),
                ]
            ),
            fill=_mix(ct, "#FFFFFF", 0.72),
            stroke="none",
        )
    )
    # β-strands on the barrel, α-helix striping on the tunnel
    strands = " ".join(
        f"M{fmt(x - wb / 2 + 4 + k * 5.2)} {fmt(om_b)} L{fmt(x - wb / 2 + 7 + k * 5.2)} {fmt(om_t - 2)}"
        for k in range(8)
        if abs(x - wb / 2 + 5.5 + k * 5.2 - x) > 8
    )
    g.append(_el("path", d=strands, fill="none", stroke=et, stroke_width=0.9, stroke_opacity=0.75))
    helix = []
    y = om_b + 6
    while y < t_bot - 16:
        for sx in (-1, 1):
            a, b = x + sx * 8, x + sx * (wt / 2 - 2)
            helix.append(f"M{fmt(a)} {fmt(y + 3)} L{fmt(b)} {fmt(y)}")
        y += 6.5
    g.append(
        _el(
            "path",
            d=" ".join(helix),
            fill="none",
            stroke=_mix(ct, "#FFFFFF", 0.45),
            stroke_width=1.2,
            stroke_linecap="round",
        )
    )
    for sx in (-1, 1):
        for depth, shade in ((0, 0.0), (1, 0.28)):
            off = sx * (wt / 2 + 6 + depth * 8)
            bx = x + sx * (base_w * 0.5 + 3 - depth * 9)
            beads = [(bx, im_t - 9), (bx - sx * 5, im_t - P * 0.2), (x + off + sx * 4, im_t - P * 0.33)]
            fill = _mix(ca, "#FFFFFF", shade)
            # α-hairpin: two antiparallel coiled helices up the tunnel side
            hy0, hy1 = beads[-1][1] - 4, om_b + P * 0.16
            hx = x + off
            g.append(
                _el(
                    "path",
                    d=_poly(
                        [(hx - 3.6, hy0), (hx - 3.6, hy1 + 3), (hx, hy1 - 1), (hx + 3.6, hy1 + 3), (hx + 3.6, hy0)]
                    ),
                    fill=fill,
                    stroke=ea,
                    stroke_width=0.8,
                    stroke_linejoin="round",
                )
            )
            g.append(
                _el("path", d=f"M{fmt(hx)} {fmt(hy0 - 2)} V{fmt(hy1 + 4)}", fill="none", stroke=ea, stroke_width=0.6)
            )
            g.append(
                _el(
                    "path",
                    d=" ".join(_circ(px, py, r) for (px, py), r in zip(beads, (5.2, 5.6, 5))),
                    fill=fill,
                    stroke=ea,
                    stroke_width=0.8,
                )
            )
            # lipid anchor into the inner-membrane outer leaflet
            g.append(
                _el(
                    "path",
                    d=f"M{fmt(beads[0][0])} {fmt(im_t - 4)} V{fmt(im_t + T * 0.3)}",
                    fill="none",
                    stroke=ea,
                    stroke_width=1.2,
                )
            )
    return dict(
        entry=PathFrame(cleft, (0.0, -1.0), (1.0, 0.0), None),
        exit=(x, om_t - 6),
        center=(x, (om_b + im_t) / 2),
        foot_om=(x - wb / 2 - 2, x + wb / 2 + 2),
        foot_im=(x - tw / 2 - 2, x + tw / 2 + 2),
        hole_pg=(x - wt / 2 - 22, x + wt / 2 + 22),
        label_y=om_t,
    )


def _porin(g, x, ys, color, rich):
    om_t, om_b, im_t, im_b, T = ys
    e = _mix(color, "#000000", 0.38)
    bw, gap = 20.0, 2.0
    tw = 3 * bw + 2 * gap
    for k in range(3):
        bx = x - tw / 2 + k * (bw + gap)
        g.append(
            _el(
                "rect",
                x=bx,
                y=om_t - 5,
                width=bw,
                height=om_b - om_t + 10,
                rx=6,
                fill=_mix(color, "#FFFFFF", 0.14 * (k == 1)),
                stroke=e,
                stroke_width=1,
            )
        )
        g.append(
            _el(
                "rect",
                x=bx + bw / 2 - 3.2,
                y=om_t - 3,
                width=6.4,
                height=om_b - om_t + 6,
                rx=3,
                fill=_mix(color, "#FFFFFF", 0.7),
            )
        )
        g.append(
            _el(
                "path",
                d=" ".join(
                    f"M{fmt(bx + 2.5 + j * 4.5)} {fmt(om_b + 3)} L{fmt(bx + 4 + j * 4.5)} {fmt(om_t - 3)}"
                    for j in (0, 3)
                ),
                fill="none",
                stroke=e,
                stroke_width=0.8,
                stroke_opacity=0.7,
            )
        )
    return dict(
        entry=(x, om_b + 7),
        exit=(x, om_t - 7),
        center=(x, (om_t + om_b) / 2),
        foot_om=(x - tw / 2 - 1, x + tw / 2 + 1),
        label_y=om_t,
    )


def _abc(g, x, ys, color, rich, fs):
    om_t, om_b, im_t, im_b, T = ys
    e = _mix(color, "#000000", 0.38)
    light = _mix(color, "#FFFFFF", 0.3)
    hw = 7.0
    for sx in (-1, 1):
        for k in range(3):
            hx = x + sx * (6 + k * (hw + 1.4)) - (hw if sx < 0 else 0)
            g.append(_rod(hx, im_t - 4, hw, T + 18, color if (k + (sx > 0)) % 2 == 0 else light, e if rich else None))
    nbd = _mix(color, "#E0A458", 0.55)
    for sx in (-1, 1):
        g.append(
            _el(
                "ellipse",
                cx=x + sx * 15,
                cy=im_b + 22,
                rx=15,
                ry=11,
                fill=nbd,
                stroke=_mix(nbd, "#000000", 0.38),
                stroke_width=1,
            )
        )
    g.append(
        _el(
            "path",
            d=_circ(x - 3.5, im_b + 22, 3.4) + " " + _circ(x + 3.5, im_b + 22, 3.4),
            fill="#F2C14E",
            stroke=_mix("#F2C14E", "#000000", 0.45),
            stroke_width=0.8,
        )
    )
    t = _text(x, im_b + 22 + 11 + fs * 0.82, "ATP", fs * 0.7, _mix(nbd, "#000000", 0.5), anchor="middle")
    g.append(t)
    w = 2 * (6 + 3 * hw + 2.8)
    return dict(
        entry=(x - w / 2 - 4, (im_t + im_b) / 2 + 3),
        exit=(x, im_t - 7),
        center=(x, (im_t + im_b) / 2),
        foot_im=(x - w / 2 - 1, x + w / 2 + 1),
        label_y=im_b + 38 + fs * 0.9,
        extra_box=_tbox(x, im_b + 22 + 11 + fs * 0.82, "ATP", fs * 0.7, "middle"),
    )


def _mfs(g, x, ys, color, rich):
    om_t, om_b, im_t, im_b, T = ys
    e = _mix(color, "#000000", 0.38)
    light = _mix(color, "#FFFFFF", 0.3)
    hw = 5.6
    for sx in (-1, 1):
        for k in range(6):
            hx = x + sx * (4.5 + k * (hw + 1)) - (hw if sx < 0 else 0)
            lift = 2 * math.sin(k * 1.3)
            g.append(_rod(hx, im_t - 4 + lift, hw, T + 8, color if k % 2 == 0 else light, e if rich else None, 0.6))
    w = 2 * (4.5 + 6 * (hw + 1))
    return dict(
        entry=(x, im_b + 7),
        exit=(x, im_t - 7),
        center=(x, (im_t + im_b) / 2),
        foot_im=(x - w / 2 - 1, x + w / 2 + 1),
        label_y=im_b + 6,
    )


def _channel(g, x, ys, color, rich):
    om_t, om_b, im_t, im_b, T = ys
    e = _mix(color, "#000000", 0.38)
    for sx in (-1, 1):
        g.append(_rod(x + sx * 4 - (11 if sx < 0 else 0), im_t - 6, 11, T + 12, color, e))
    return dict(
        entry=(x, im_b + 8),
        exit=(x, im_t - 8),
        center=(x, (im_t + im_b) / 2),
        foot_im=(x - 16, x + 16),
        label_y=im_b + 6,
    )


@_drawing_api(
    "parts",
    purpose="细菌包膜横截面（期刊级）：革兰阴性=外膜（LPS：O 抗原链/核心寡糖/脂质 A）+ 周质薄肽聚糖网 + 内膜；革兰阳性=厚肽聚糖 + 磷壁酸；膜上外排泵/孔蛋白/ABC/MFS/通道。",
    returns="Geometry（原点在中心；端口 outside/outer_membrane/periplasm/peptidoglycan/inner_membrane/cytoplasm，每个蛋白 p{i}/p{i}_entry/p{i}_exit）",
    semantics=(
        '自上而下：胞外 → 外膜 → 周质 → 内膜 → 胞质；层名原生文字写在左侧（gram="positive" 为 肽聚糖/细胞膜）。',
        'proteins 每项 {"kind": tripartite_pump|porin|abc|mfs|channel, "at": 0–1 沿膜位置, "label": "AcrAB–TolC", "color": 主色}；'
        "tripartite_pump=AcrB 三聚体（跨膜螺旋+周质 porter 叶）+ AcrA 发夹 + TolC β 桶/α 隧道，横跨内膜-周质-外膜；porin=外膜 β 桶三聚体；"
        "abc=两个 TMD + 两个 NBD 与 ATP；mfs=12 螺旋束。蛋白处膜脂断开、LPS 让位。",
        "p{i}_entry 为底物进入处（AcrB 周质侧裂隙 / 胞质侧），p{i}_exit 为出口（TolC/孔蛋白顶端 = 胞外，内膜蛋白 = 周质侧）；"
        'drugs=True 在入口和出口各画一个药物分子，配 d.arrow(env.port("p0_entry"), env.port("p0_exit"), curve=) 表示外排。',
        '蛋白名自动放在胞外顶部（外膜蛋白）或胞质（内膜蛋白），挤时错行；style="flat" 全原生。',
    ),
    example='env = d.place(cell_envelope(820, proteins=[{"kind": "tripartite_pump", "at": .3, "label": "AcrAB–TolC"},\n'
    '    {"kind": "porin", "at": .62, "label": "OmpF"}, {"kind": "abc", "at": .85, "label": "MacAB"}], drugs=True), at=(450, 200))\n'
    'd.arrow(env.port("p0_entry"), env.port("p0_exit"), curve=-.3, color="#D23B3B")',
    rank=4,
)
def cell_envelope(
    width=820,
    *,
    gram="negative",
    proteins=(),
    drugs=False,
    font_size=13,
    om_color="#4F7FB8",
    im_color="#9A88C9",
    pg_color="#5E9E57",
    style="rich",
    seed=4,
):
    rich = _check_style(style)
    if gram not in ("negative", "positive"):
        raise ValueError('gram must be "negative" or "positive"')
    _finite(width, font_size)
    W, fs, T = float(width), float(font_size), 22.0
    neg = gram == "negative"
    proteins = list(proteins)
    for p in proteins:
        if not isinstance(p, dict) or p.get("kind") not in _PROTEINS:
            raise ValueError(f"each protein must be a dict with kind in {_PROTEINS}")
        if not neg and p["kind"] in _SPANS_OM:
            raise ValueError(f'{p["kind"]} needs an outer membrane (gram="negative")')
        if not 0 <= float(p.get("at", 0.5)) <= 1:
            raise ValueError('protein "at" must be within 0..1')
    rnd = random.Random(seed)
    side_names = ("胞外", "外膜", "周质", "内膜", "胞质") if neg else ("胞外", "细胞壁", "周质", "细胞膜", "胞质")
    lab_w = max(label(s, font_size=fs, font_weight="bold").bounds.width for s in side_names + ("肽聚糖",)) + 14
    x0, x1 = lab_w, W
    top_band = fs * 1.6 + 6  # protein-name row above the O-antigen brush
    if neg:
        out_h = top_band + 50
        om_t = out_h
        om_b = om_t + T
        P = 112.0
        im_t = om_b + P
    else:
        out_h = top_band + 34
        om_t = om_b = out_h  # no outer membrane; wall starts here
        P = 92.0
        im_t = om_b + P
    im_b = im_t + T
    cyto_h = 30 + fs * 2.6
    if any(p["kind"] == "abc" for p in proteins):
        cyto_h = max(cyto_h, 44 + fs * 2.9)
    H = im_b + cyto_h
    ys = (om_t, om_b, im_t, im_b, T)
    out_c, peri_c, cyto_c = "#EAF2F8", "#F5F2E6", "#FBF1E6"
    holder, defs = _el("g"), _el("defs")
    holder.append(defs)
    holder.append(_el("rect", x=0, y=0, width=W, height=H, fill=out_c, data_outline="1"))
    holder.append(_el("rect", x=0, y=om_b, width=W, height=im_t - om_b, fill=peri_c))
    holder.append(_el("rect", x=0, y=im_t, width=W, height=H - im_t, fill=cyto_c))
    if rich:
        look = _look()
        defs.append(_linear("ce_cyto", [("0", "#FFFFFF", "0"), ("1", _mix(cyto_c, "#C98B5A", 0.35), ".6")]))
        look.append(_el("rect", x=0, y=im_b, width=W, height=H - im_b, fill="url(#ce_cyto)"))
        defs.append(_linear("ce_out", [("0", "#FFFFFF", ".7"), ("1", "#FFFFFF", "0")]))
        look.append(_el("rect", x=0, y=0, width=W, height=om_t, fill="url(#ce_out)"))
        holder.append(look)

    # proteins first (geometry only) so membranes, LPS and peptidoglycan can make room
    span = (x0 + 50, x1 - 50)
    built = []
    for i, p in enumerate(proteins):
        x = span[0] + (span[1] - span[0]) * float(p.get("at", 0.5))
        kind = p["kind"]
        color = p.get("color") or _DEFAULT_COLOR[kind]
        g = _el("g")
        if kind == "tripartite_pump":
            cols = p.get("colors") or (color, "#E3A33B", "#8E5BB5")
            info = _tripartite(g, x, ys, cols, rich, rnd)
        elif kind == "porin":
            info = _porin(g, x, ys, color, rich)
        elif kind == "abc":
            info = _abc(g, x, ys, color, rich, fs)
        elif kind == "mfs":
            info = _mfs(g, x, ys, color, rich)
        else:
            info = _channel(g, x, ys, color, rich)
        built.append((i, p, x, color, g, info))
    om_holes = [b[5]["foot_om"] for b in built if "foot_om" in b[5]]
    im_holes = [b[5]["foot_im"] for b in built if "foot_im" in b[5]]
    pg_holes = [b[5]["hole_pg"] for b in built if "hole_pg" in b[5]]

    natives, looks = [], []
    nag, nam = pg_color, _mix(pg_color, "#FFFFFF", 0.42)
    pep = "#C8892E"
    rows = 2 if neg else 6
    pg_top = om_b + P * 0.2 if neg else om_t + 6
    row_gap = 11.0 if neg else (P - 22) / rows
    sugar_w, sugar_h = 7.0, 5.2
    sugars_a, sugars_b, peps = [], [], []
    for r in range(rows):
        yy = pg_top + r * row_gap
        shift = (r % 2) * sugar_w * 0.9
        for a, b in _segments(x0 + 2, x1 - 2, pg_holes, 4):
            k = 0
            xx = a + shift
            while xx + sugar_w < b:
                (sugars_a if k % 2 == 0 else sugars_b).append(
                    f"M{fmt(xx + 1.4)} {fmt(yy)} H{fmt(xx + sugar_w - 1.4)} Q{fmt(xx + sugar_w)} {fmt(yy)} {fmt(xx + sugar_w)} {fmt(yy + 1.4)} "
                    f"V{fmt(yy + sugar_h - 1.4)} Q{fmt(xx + sugar_w)} {fmt(yy + sugar_h)} {fmt(xx + sugar_w - 1.4)} {fmt(yy + sugar_h)} "
                    f"H{fmt(xx + 1.4)} Q{fmt(xx)} {fmt(yy + sugar_h)} {fmt(xx)} {fmt(yy + sugar_h - 1.4)} V{fmt(yy + 1.4)} "
                    f"Q{fmt(xx)} {fmt(yy)} {fmt(xx + 1.4)} {fmt(yy)} Z"
                )
                if k % 2 == 1 and r < rows - 1 and rnd.random() < 0.75:
                    px = xx + sugar_w / 2
                    peps.append(
                        f"M{fmt(px)} {fmt(yy + sugar_h)} L{fmt(px + rnd.uniform(-2, 2))} {fmt(yy + row_gap * 0.5)} "
                        f"L{fmt(px + rnd.uniform(-1, 1))} {fmt(yy + row_gap)}"
                    )
                xx += sugar_w + 0.8
                k += 1
    pg_bot = pg_top + (rows - 1) * row_gap + sugar_h
    natives.append(_el("path", d=" ".join(peps), fill="none", stroke=pep, stroke_width=1.3, stroke_linecap="round"))
    natives.append(_el("path", d=" ".join(sugars_a), fill=nag, stroke=_mix(nag, "#000000", 0.35), stroke_width=0.4))
    natives.append(_el("path", d=" ".join(sugars_b), fill=nam, stroke=_mix(nag, "#000000", 0.3), stroke_width=0.4))
    if neg:
        # Braun's lipoprotein tethers: OM inner leaflet → peptidoglycan
        lpp = []
        for a, b in _segments(x0 + 10, x1 - 10, om_holes + pg_holes, 6):
            xx = a + 22
            while xx < b - 10:
                lpp.append(
                    f"M{fmt(xx)} {fmt(om_b - 3)} C{fmt(xx + 4)} {fmt(om_b + 8)} {fmt(xx - 4)} {fmt(pg_top - 8)} {fmt(xx + 1)} {fmt(pg_top)}"
                )
                xx += rnd.uniform(70, 110)
        natives.append(
            _el(
                "path",
                d=" ".join(lpp),
                fill="none",
                stroke=_mix(pep, "#000000", 0.2),
                stroke_width=1.6,
                stroke_linecap="round",
            )
        )
    else:
        # wall teichoic acids (anchored in PG, poking out) and lipoteichoic acids (anchored in the membrane)
        wta, lta, beads = [], [], []
        xx = x0 + 14
        k = 0
        while xx < x1 - 8:
            if not any(a - 6 < xx < b + 6 for a, b in im_holes):
                lipo = k % 3 == 1
                y_lo = im_t + T * 0.25 if lipo else pg_top + row_gap * rnd.randint(1, 3)
                y_hi = pg_top - rnd.uniform(14, 26)
                pts = [(xx + 2.2 * math.sin(j * 1.1 + k), y_lo + (y_hi - y_lo) * j / 8) for j in range(9)]
                (lta if lipo else wta).append(_smooth(pts))
                beads += [
                    _circ(px, py, 1.7)
                    for px, py in pts[3 if lipo else 1 :: 2]
                    if py < (pg_top - 2 if lipo else y_lo - 3)
                ]
            xx += rnd.uniform(26, 40)
            k += 1
        natives.append(
            _el("path", d=" ".join(wta), fill="none", stroke="#8A5A9E", stroke_width=1.6, stroke_linecap="round")
        )
        natives.append(
            _el("path", d=" ".join(lta), fill="none", stroke="#B5618A", stroke_width=1.6, stroke_linecap="round")
        )
        natives.append(
            _el("path", d=" ".join(beads), fill="#F2C14E", stroke=_mix("#F2C14E", "#000000", 0.4), stroke_width=0.5)
        )
    holder.extend(natives)

    if neg:
        lps_x = []
        for j, (a, b) in enumerate(_segments(x0, x1, om_holes)):
            band, grp, xs = _bilayer_strip(a, b, (om_t + om_b) / 2, T, om_color, rich, seed + j, lps=True)
            holder.append(band)
            (looks if rich else holder).append(grp)
            lps_x += xs
        # LPS: lipid A head (outer leaflet) + core oligosaccharide + O-antigen repeat chain
        head = T * 0.17
        lipid_a, core, oag, core2 = [], [], [], []
        exits = [b[5]["exit"][0] for b in built if b[1]["kind"] in _SPANS_OM]
        for k, lx in enumerate(lps_x):
            hy = om_t + head
            lipid_a.append(
                f"M{fmt(lx - head * 1.05)} {fmt(hy + head * 0.8)} V{fmt(hy - head * 0.3)} "
                f"Q{fmt(lx)} {fmt(hy - head * 1.5)} {fmt(lx + head * 1.05)} {fmt(hy - head * 0.3)} V{fmt(hy + head * 0.8)} Z"
            )
            cy = om_t - 2.6
            core.append(_circ(lx, cy, 2.1))
            core2.append(_circ(lx + 0.6, cy - 4.2, 1.9))
            if any(abs(lx - ex) < 18 for ex in exits):
                continue
            units = rnd.choice((0, 2, 3, 4, 4, 5, 5, 6))
            phase = rnd.uniform(0, 6.3)
            for u in range(units * 2):
                py = cy - 8 - u * 3.6
                px = lx + 1.6 * math.sin(phase + u * 0.7) + u * 0.25 * math.sin(phase)
                oag.append(_circ(px, py, 1.55))
        lps_col = "#2F5D8C"
        holder.append(
            _el("path", d=" ".join(lipid_a), fill=lps_col, stroke=_mix(lps_col, "#000000", 0.35), stroke_width=0.3)
        )
        holder.append(_el("path", d=" ".join(core), fill="#E08A3C", stroke="none"))
        holder.append(_el("path", d=" ".join(core2), fill="#C8644A", stroke="none"))
        holder.append(
            _el("path", d=" ".join(oag), fill="#4E9F7A", stroke=_mix("#4E9F7A", "#000000", 0.3), stroke_width=0.3)
        )
    for j, (a, b) in enumerate(_segments(x0, x1, im_holes)):
        band, grp, _ = _bilayer_strip(a, b, (im_t + im_b) / 2, T, im_color, rich, seed + 20 + j)
        holder.append(band)
        if rich:
            looks.append(grp)
        else:
            holder.append(grp)
    if rich and looks:
        lk = _look()
        lk.extend(looks)
        holder.append(lk)

    ports, boxes, texts = {}, [], []
    for i, p, x, color, g, info in built:
        holder.append(g)
        ports[f"p{i}"] = info["center"]
        ports[f"p{i}_entry"] = info["entry"]
        ports[f"p{i}_exit"] = info["exit"]
        if "extra_box" in info:
            boxes.append(info["extra_box"])
    lab_rows = [(side_names[0], top_band + (om_t - top_band) / 2 + fs * 0.35)]
    if neg:
        lab_rows += [(side_names[1], (om_t + om_b) / 2 + fs * 0.35), (side_names[2], om_b + P * 0.62 + fs * 0.35)]
    else:
        lab_rows += [(side_names[1], (pg_top + pg_bot) / 2 + fs * 0.35)]
    lab_rows += [(side_names[3], (im_t + im_b) / 2 + fs * 0.35), (side_names[4], im_b + cyto_h * 0.5 + fs * 0.35)]
    hdr = _mix(_INK, "#FFFFFF", 0.05)
    for s, y in lab_rows:
        texts.append(_text(6, y, s, fs, hdr))
        boxes.append(_tbox(6, y, s, fs))
    sub = fs * 0.78
    small = [("肽聚糖", (pg_top + pg_bot) / 2 + sub * 0.35)] if neg else []
    if neg:
        small.append(("LPS", om_t - 16 + sub * 0.35))
    for s, y in small:
        if not _hits(_tbox(6, y, s, sub), boxes):
            texts.append(_text(6, y, s, sub, "#5B6573", bold=False))
            boxes.append(_tbox(6, y, s, sub, bold=False))
    if drugs:
        for i, p, x, color, g, info in built:
            ex, ey = info["exit"]
            en = info["entry"]
            en = en.point if isinstance(en, PathFrame) else en
            holder.append(_drug(en[0] - 10, en[1] + 2, 3.6))
            holder.append(_drug(ex + 15, ey - 22 if p["kind"] in _SPANS_OM else ey - 6, 3.6))
    for i, p, x, color, g, info in built:
        name = p.get("label")
        if not name:
            continue
        col = _mix(color, "#000000", 0.42)
        lh = fs * 1.25
        if p["kind"] in _SPANS_OM:
            cands = [
                ((x + 10, fs * 1.05 + 3), "start"),
                ((x - 10, fs * 1.05 + 3), "end"),
                ((x + 10, fs * 1.05 + 3 + lh * 0.9), "start"),
            ]
        else:
            ly = info["label_y"] + fs * 1.05
            cands = [((x, ly), "middle"), ((x, ly + lh), "middle"), ((x + 30, ly), "start")]
        pick = None
        for (tx, ty), anc in cands:
            b = _tbox(tx, ty, name, fs, anc)
            if b.x >= x0 - 4 and b.x + b.width <= W - 2 and b.y + b.height <= H - 1 and not _hits(b, boxes):
                pick = (tx, ty, anc, b)
                break
        if pick is None:
            (tx, ty), anc = cands[0]
            pick = (tx, ty, anc, _tbox(tx, ty, name, fs, anc))
        tx, ty, anc, b = pick
        texts.append(_text(tx, ty, name, fs, col, anchor=anc))
        boxes.append(b)
    holder.extend(texts)
    xm = (x0 + x1) / 2
    ports.update(
        outside=(xm, top_band + 6),
        periplasm=(xm, (om_b + im_t) / 2 if neg else pg_bot + (im_t - pg_bot) / 2),
        peptidoglycan=(xm, (pg_top + pg_bot) / 2),
        inner_membrane=(xm, (im_t + im_b) / 2),
        cytoplasm=(xm, im_b + cyto_h * 0.55),
    )
    ports["cell_wall"] = ports["peptidoglycan"]
    if neg:
        ports["outer_membrane"] = (xm, (om_t + om_b) / 2)
    return _finish(holder, defs, Box(0, 0, W, H), **ports)


_BF_FEATURES = ("channels", "persisters", "eDNA", "qs")
_GRADIENTS = {
    "oxygen": ("#E9A23B", "#5A3E8C", "有氧", "缺氧", "O₂"),
    "nutrient": ("#3E9A6A", "#8C5A3E", "营养充足", "营养匮乏", "营养"),
}


def _mushroom(cx, base, w, h, rnd):
    """Outline points (closed) of a mushroom microcolony: narrow stalk widening into a lobed cap."""
    stalk = w * 0.34
    pts = [(cx - stalk / 2, base)]
    pts.append((cx - stalk * 0.55, base - h * 0.3))
    pts.append((cx - w * 0.42, base - h * 0.48))
    lobes = 7
    for k in range(lobes + 1):
        a = math.pi * (1 - k / lobes)
        r = 1 + rnd.uniform(-0.06, 0.08)
        pts.append((cx + w / 2 * math.cos(a) * r, base - h * 0.55 - h * 0.45 * math.sin(a) * r))
    pts.append((cx + w * 0.42, base - h * 0.48))
    pts.append((cx + stalk * 0.55, base - h * 0.3))
    pts.append((cx + stalk / 2, base))
    return pts


def _lerp_hex(a, b, t):
    return _mix(a, b, max(0.0, min(1.0, t)))


def _capsule(x, y, L, R, ang):
    """Rod-shaped bacterium (capsule of body length L, radius R, axis angle ang) or a coccus when L == 0."""
    if L == 0:
        return _circ(x, y, R)
    ux, uy = math.cos(ang), math.sin(ang)
    nx, ny = -uy, ux
    a = (x - ux * L / 2, y - uy * L / 2)
    b = (x + ux * L / 2, y + uy * L / 2)
    return (
        f"M{fmt(a[0] + nx * R)} {fmt(a[1] + ny * R)} L{fmt(b[0] + nx * R)} {fmt(b[1] + ny * R)} "
        f"A{fmt(R)} {fmt(R)} 0 0 0 {fmt(b[0] - nx * R)} {fmt(b[1] - ny * R)} L{fmt(a[0] - nx * R)} {fmt(a[1] - ny * R)} "
        f"A{fmt(R)} {fmt(R)} 0 0 0 {fmt(a[0] + nx * R)} {fmt(a[1] + ny * R)} Z"
    )


@_drawing_api(
    "parts",
    purpose="生物膜纵切面（期刊级）：底部附着表面、EPS 基质包裹的蘑菇状微菌落（杆菌/球菌）、菌落间水通道、O₂/营养梯度（有氧→缺氧，带色标）、休眠持留菌、eDNA 与群体感应信号分子。",
    returns="Geometry（原点在中心；端口 surface 表面、channel 水通道、top 生物膜顶、core 菌落深部、persister 持留菌、colony{i} 各菌落）",
    semantics=(
        'width/height 为截面尺寸（色标与图例在其下方）；colonies 为微菌落数，cell="rod"|"coccus"|"mixed" 为菌体形态。',
        'gradient="oxygen"|"nutrient"：菌体颜色自菌落表面（橙/绿，代谢活跃）向深部（紫/褐，缺氧/饥饿）渐变，底部画小色标。',
        "features 可含 channels（水通道与流动箭头）/persisters（深部休眠菌，暗色描边高亮）/eDNA（基质中的胞外 DNA 丝）/qs（群体感应小分子点）。",
        'surface_label 为表面名（如 "导管表面"）；style="rich" 加 EPS 半透明纹理与菌体高光，"flat" 全原生。',
    ),
    example='bf = d.place(biofilm_section(760, 300, gradient="oxygen", surface_label="导管表面"), at=(450, 230))\n'
    'd.callout("p", "持留菌（抗生素耐受）", bf.port("persister"), at=(820, 120), font_size=14)',
    rank=4,
)
def biofilm_section(
    width=760,
    height=300,
    *,
    gradient="oxygen",
    features=_BF_FEATURES,
    colonies=4,
    cell="mixed",
    surface_label="附着表面",
    eps_color="#9CC3D9",
    font_size=13,
    style="rich",
    seed=6,
):
    rich = _check_style(style)
    if gradient not in _GRADIENTS:
        raise ValueError('gradient must be "oxygen" or "nutrient"')
    if cell not in ("rod", "coccus", "mixed"):
        raise ValueError('cell must be "rod", "coccus" or "mixed"')
    features = tuple(features)
    for f in features:
        if f not in _BF_FEATURES:
            raise ValueError(f"features must be from {_BF_FEATURES}")
    _finite(width, height, font_size)
    W, H, fs = float(width), float(height), float(font_size)
    n = max(1, int(colonies))
    rnd = random.Random(seed)
    hot, cold, hot_name, cold_name, gname = _GRADIENTS[gradient]
    sub_h = 18.0
    base = H - sub_h
    holder, defs = _el("g"), _el("defs")
    holder.append(defs)
    holder.append(_el("rect", x=0, y=0, width=W, height=H, fill="#EEF6FB", data_outline="1"))
    if rich:
        look = _look()
        defs.append(_linear("bf_water", [("0", "#FFFFFF", ".8"), ("1", "#D6E9F4", ".0")]))
        look.append(_el("rect", x=0, y=0, width=W, height=base, fill="url(#bf_water)"))
        holder.append(look)
    sub_c = "#B9B1A4"
    holder.append(_el("rect", x=0, y=base, width=W, height=sub_h, fill=sub_c))
    holder.append(
        _el("path", d=f"M0 {fmt(base)} H{fmt(W)}", fill="none", stroke=_mix(sub_c, "#000000", 0.45), stroke_width=1.4)
    )
    hatch = " ".join(f"M{fmt(x)} {fmt(H)} L{fmt(x + 9)} {fmt(base + 2)}" for x in range(-6, int(W), 12))
    holder.append(_el("path", d=hatch, fill="none", stroke=_mix(sub_c, "#000000", 0.25), stroke_width=0.8))
    slot = W / n
    cols = []
    for i in range(n):
        cx = slot * (i + 0.5) + rnd.uniform(-slot * 0.06, slot * 0.06)
        w = slot * rnd.uniform(0.66, 0.76)
        h = (base - fs * 1.2 - 10) * rnd.uniform(0.72, 0.95)
        cols.append((cx, w, h, _mushroom(cx, base, w, h, rnd)))
    film_h = 9.0
    eps_edge = _mix(eps_color, "#000000", 0.3)
    eps_d = " ".join(_smooth(poly, closed=True) for *_, poly in cols)
    holder.append(_el("rect", x=0, y=base - film_h, width=W, height=film_h, fill=_mix(eps_color, "#FFFFFF", 0.35)))
    holder.append(_el("path", d=eps_d, fill=_mix(eps_color, "#FFFFFF", 0.25), stroke=eps_edge, stroke_width=1.1))
    if rich:
        look = _look()
        gid = "bf_eps"
        defs.append(_linear(gid, [("0", "#FFFFFF", ".45"), ("1", eps_color, ".25")]))
        look.append(_el("path", d=eps_d, fill=f"url(#{gid})"))
        tex = []
        for cx, w, h, poly in cols:
            for _ in range(int(w * h / 260)):
                x, y = rnd.uniform(cx - w / 2, cx + w / 2), rnd.uniform(base - h, base)
                if _inside((x, y), poly):
                    a = rnd.uniform(0, math.pi)
                    L = rnd.uniform(5, 10)
                    tex.append(
                        f"M{fmt(x)} {fmt(y)} q{fmt(L * 0.5 * math.cos(a) + 2)} {fmt(L * 0.5 * math.sin(a) - 2)} "
                        f"{fmt(L * math.cos(a))} {fmt(L * math.sin(a))}"
                    )
        look.append(_el("path", d=" ".join(tex), fill="none", stroke=eps_edge, stroke_width=0.6, stroke_opacity=0.35))
        holder.append(look)
    # cells, coloured by depth below the colony surface
    ports, boxes = {}, []
    cells_by_col = []
    persisters = []
    deep_pts = []
    for i, (cx, w, h, poly) in enumerate(cols):
        top = base - h
        placed = []
        tries = 0
        target = int(w * h / 95)
        while len(placed) < target and tries < target * 40:
            tries += 1
            x, y = rnd.uniform(cx - w / 2, cx + w / 2), rnd.uniform(top, base - 3)
            rod = cell == "rod" or (cell == "mixed" and rnd.random() < 0.65)
            L, R = (rnd.uniform(9, 13), 2.9) if rod else (0.0, rnd.uniform(3.2, 3.9))
            ang = rnd.uniform(0, math.pi)
            ends = [
                (x + L / 2 * math.cos(ang), y + L / 2 * math.sin(ang)),
                (x - L / 2 * math.cos(ang), y - L / 2 * math.sin(ang)),
            ]
            if not all(_inside(e, poly) for e in ends + [(x, y - R - 1), (x, y + R + 1)]):
                continue
            if any(math.dist((x, y), (px, py)) < max(pl, L) * 0.5 + R + pr + 0.8 for px, py, pl, pr, _ in placed):
                continue
            placed.append((x, y, L, R, ang))
        # depth: distance from point to the colony outline (approx via samples)
        edge_pts = []
        for a, b in zip(poly, poly[1:] + poly[:1]):
            if a[1] >= base - 0.5 and b[1] >= base - 0.5:
                continue
            for t in range(6):
                edge_pts.append((a[0] + (b[0] - a[0]) * t / 6, a[1] + (b[1] - a[1]) * t / 6))
        maxd = min(w, h) * 0.42
        groups = {}
        for x, y, L, R, ang in placed:
            dd = min(math.dist((x, y), e) for e in edge_pts) / maxd
            dd = max(dd, ((y - top) / h) ** 1.4 * (0.95 if gradient == "nutrient" else 0.8))
            dd = min(1.0, dd)
            q = min(4, int(dd * 5))
            groups.setdefault(q, []).append((x, y, L, R, ang))
            if dd > 0.7:
                deep_pts.append((dd, x, y, L, R, ang))
        cells_by_col.append(groups)
        ports[f"colony{i}"] = (cx, top + h * 0.4)
    if "persisters" in features and deep_pts:
        deep_pts.sort(key=lambda t: -t[0])
        chosen = []
        for t in deep_pts:
            if all(math.dist(t[1:3], c[1:3]) > 40 for c in chosen):
                chosen.append(t)
            if len(chosen) >= max(2, n):
                break
        persisters = chosen
    pset = {(round(t[1], 2), round(t[2], 2)) for t in persisters}

    cell_d = _capsule
    for q in range(5):
        col = _lerp_hex(hot, cold, q / 4)
        ds = [cell_d(*c) for g in cells_by_col for c in g.get(q, ()) if (round(c[0], 2), round(c[1], 2)) not in pset]
        if ds:
            holder.append(_el("path", d=" ".join(ds), fill=col, stroke=_mix(col, "#000000", 0.35), stroke_width=0.6))
    if rich:
        look = _look()
        sh = []
        for g in cells_by_col:
            for x, y, L, R, ang in (c for qq in g.values() for c in qq):
                sh.append(
                    _circ(x - R * 0.3 - math.cos(ang) * L * 0.2, y - R * 0.35 - math.sin(ang) * L * 0.2, R * 0.38)
                )
        look.append(_el("path", d=" ".join(sh), fill="#FFFFFF", fill_opacity=0.45))
        holder.append(look)
    if persisters:
        pc = "#3B3B46"
        holder.append(
            _el("path", d=" ".join(cell_d(*t[1:]) for t in persisters), fill="#8E8E99", stroke=pc, stroke_width=1.6)
        )
        holder.append(
            _el(
                "path",
                d=" ".join(_circ(t[1], t[2], max(t[3] / 2, t[4]) + 4.5) for t in persisters),
                fill="none",
                stroke="#C0392B",
                stroke_width=1.3,
            )
        )
        ports["persister"] = (persisters[0][1], persisters[0][2])
    if "eDNA" in features:
        ed = []
        for cx, w, h, poly in cols:
            for _ in range(2):
                x, y = rnd.uniform(cx - w * 0.3, cx + w * 0.3), rnd.uniform(base - h * 0.85, base - h * 0.25)
                pts = [(x + k * 5, y + 3.2 * math.sin(k * 1.3 + x)) for k in range(7)]
                if all(_inside(p, poly) for p in pts):
                    ed.append(_smooth(pts))
                    ed.append(_smooth([(px, py + 2.6 * math.cos(k * 1.3 + x)) for k, (px, py) in enumerate(pts)]))
        holder.append(
            _el("path", d=" ".join(ed), fill="none", stroke="#2E5C9A", stroke_width=1.1, stroke_linecap="round")
        )
    if "qs" in features:
        qs = []
        for cx, w, h, poly in cols:
            for _ in range(10):
                a = rnd.uniform(math.pi * 1.05, math.pi * 1.95)
                r = rnd.uniform(0.3, 0.62)
                x, y = cx + w / 2 * r * math.cos(a) * 1.6, base - h * 0.55 + h * 0.45 * r * math.sin(a) * 1.6
                if 0 < y < base - 4:
                    qs.append(_circ(x, y, 1.7))
        holder.append(
            _el("path", d=" ".join(qs), fill="#E2574C", stroke=_mix("#E2574C", "#000000", 0.35), stroke_width=0.4)
        )
    if "channels" in features and n >= 2:
        flow = "#2E7BC4"
        segs, heads = [], []
        for i in range(n - 1):
            gx = (cols[i][0] + cols[i][1] / 2 + cols[i + 1][0] - cols[i + 1][1] / 2) / 2
            # S-shaped convective flow down into the channel and back out
            y0 = base - min(cols[i][2], cols[i + 1][2]) * 0.82
            segs.append(
                f"M{fmt(gx - 6)} {fmt(y0)} C{fmt(gx - 4)} {fmt(y0 + 30)} {fmt(gx - 5)} {fmt(base - 50)} {fmt(gx - 3)} {fmt(base - 32)}"
            )
            heads.append(
                _el("path", d=_poly([(gx - 3, base - 26), (gx - 7.5, base - 35), (gx + 1.2, base - 34.4)]), fill=flow)
            )
            if i == (n - 1) // 2:
                ports["channel"] = (gx, base - 46)
        holder.append(_el("path", d=" ".join(segs), fill="none", stroke=flow, stroke_width=1.5, stroke_linecap="round"))
        holder.extend(heads)
    # labels and gradient bar under the section
    texts = []
    t = _text(8, H - 4.5, surface_label, fs * 0.82, _INK)
    texts.append(t)
    boxes.append(_tbox(8, H - 4.5, surface_label, fs * 0.82))
    ly = H + 10 + fs
    bar_w = min(160.0, W * 0.28)
    bx = W - bar_w - 8 - label(cold_name, font_size=fs * 0.85).bounds.width
    gl = _el("g")
    nseg = 10
    for k in range(nseg):
        gl.append(
            _el(
                "rect",
                x=bx + bar_w * k / nseg,
                y=ly - fs * 0.75,
                width=bar_w / nseg + 0.3,
                height=fs * 0.7,
                fill=_lerp_hex(hot, cold, k / (nseg - 1)),
            )
        )
    holder.append(gl)
    holder.append(
        _el(
            "rect",
            x=bx,
            y=ly - fs * 0.75,
            width=bar_w,
            height=fs * 0.7,
            fill="none",
            stroke="#5E6773",
            stroke_width=0.6,
        )
    )
    for s, x, anc in ((hot_name, bx - 5, "end"), (cold_name, bx + bar_w + 5, "start")):
        texts.append(_text(x, ly, s, fs * 0.85, _INK, anchor=anc, bold=False))
        boxes.append(_tbox(x, ly, s, fs * 0.85, anc, bold=False))
    texts.append(
        _text(bx + bar_w / 2, ly - fs * 1.05, gname + " 梯度", fs * 0.8, "#5B6573", anchor="middle", bold=False)
    )
    boxes.append(_tbox(bx + bar_w / 2, ly - fs * 1.05, gname + " 梯度", fs * 0.8, "middle", bold=False))
    # small legend for persisters / eDNA / QS at the left
    lx = 8
    items = []
    if persisters:
        items.append(("p", "持留菌"))
    if "eDNA" in features:
        items.append(("d", "eDNA"))
    if "qs" in features:
        items.append(("q", "QS 信号"))
    for kind, s in items:
        cy = ly - fs * 0.38
        if kind == "p":
            holder.append(
                _el("path", d=cell_d(lx + 7, cy, 9, 2.9, 0), fill="#8E8E99", stroke="#3B3B46", stroke_width=1.4)
            )
        elif kind == "d":
            holder.append(
                _el(
                    "path",
                    d=_smooth([(lx + k * 3.2, cy + 2.5 * math.sin(k * 1.4)) for k in range(6)]),
                    fill="none",
                    stroke="#2E5C9A",
                    stroke_width=1.1,
                )
            )
        else:
            holder.append(
                _el(
                    "path",
                    d=" ".join(_circ(lx + 3 + k * 5, cy + (k % 2) * 2 - 1, 1.7) for k in range(3)),
                    fill="#E2574C",
                )
            )
        texts.append(_text(lx + 19, ly, s, fs * 0.85, _INK, bold=False))
        bb = _tbox(lx + 19, ly, s, fs * 0.85, bold=False)
        boxes.append(bb)
        lx = bb.x + bb.width + 16
    holder.extend(texts)
    boxes.append(Box(0, 0, W, H))
    tallest = max(cols, key=lambda c: c[2])
    ports.update(
        surface=PathFrame((W / 2, base), (1.0, 0.0), (0.0, -1.0), None),
        top=(tallest[0], base - tallest[2]),
        core=(tallest[0], base - tallest[2] * 0.38),
    )
    ports.setdefault("persister", ports["core"])
    ports.setdefault("channel", (cols[0][0] + cols[0][1] / 2 + 4, base - 40))
    from ._geometry import _union

    return _finish(holder, defs, _union(boxes), **ports)
