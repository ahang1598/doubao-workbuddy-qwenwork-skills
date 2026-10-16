"""Membrane bioenergetics parts drawn like Alberts / Lehninger side-view figures."""

from __future__ import annotations

import math

from ..atomize_svg_to_slide._geometry import fmt
from ._bio_parts import _el, _look, _mix, _circ, _poly, _smooth, _check_style, _finish
from ._envelope_parts import _bilayer_strip, _segments
from ._geometry import Box, _finite, _hits, label
from ._help import _drawing_api
from ._parts import _INK

_ION = "#E8A33D"
_ELECTRON = "#2F6DB5"
_PROTON = "#C0392B"


def _text(x, y, s, fs, fill, anchor="middle", bold=True):
    t = _el("text", x=x, y=y, font_size=fs, fill=fill, text_anchor=anchor, font_weight="bold" if bold else None)
    t.text = str(s)
    w = label(str(s), font_size=fs, font_weight="bold" if bold else "normal").bounds.width
    x0 = x - (w / 2 if anchor == "middle" else w if anchor == "end" else 0)
    return t, Box(x0, y - fs * 0.92, w, fs * 1.2)


def _emitted_width(s, fs, bold=True):
    """Width of the native text box the converter writes for this run (what server lint measures)."""
    from ..atomize_svg_to_slide._font_metrics import text_advance, lint_floor_width
    from ..atomize_svg_to_slide._paint import _map_svg_font_family

    fam = _map_svg_font_family("")
    weight = "bold" if bold else "normal"
    return max(text_advance(s, fam, fs, weight) + fs * 0.5, lint_floor_width(s, fam, fs, weight) + fs * 0.1)


def _inside(b, o, pad=1.0):
    return (
        b.x >= o.x + pad
        and b.y >= o.y + pad
        and b.x + b.width <= o.x + o.width - pad
        and b.y + b.height <= o.y + o.height - pad
    )


def _lobe_pts(cx, cy, rx, ry, rot=0.0, wobble=0.05, seed=0, n=28):
    ph = seed * 1.7
    c, s = math.cos(rot), math.sin(rot)
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        k = 1 + wobble * (math.sin(3 * a + ph) * 0.6 + math.sin(5 * a + ph * 1.3) * 0.4)
        x, y = rx * k * math.cos(a), ry * k * math.sin(a)
        pts.append((cx + x * c - y * s, cy + x * s + y * c))
    return pts


def _bbox(pts):
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return Box(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


def _arrow(pts, color, sw, *, head=True, dashed=False, smooth=True):
    """Polyline/curve with a filled triangular head at the last point (native path + native head)."""
    (x1, y1), (x0, y0) = pts[-1], pts[-2]
    L = math.hypot(x1 - x0, y1 - y0) or 1
    ux, uy = (x1 - x0) / L, (y1 - y0) / L
    hl, hw = sw * 3.4, sw * 2.3
    body = list(pts[:-1]) + [(x1 - ux * hl * 0.8, y1 - uy * hl * 0.8)] if head else list(pts)
    d = _smooth(body) if smooth and len(body) > 2 else _poly(body, closed=False)
    out = [
        _el(
            "path",
            d=d,
            fill="none",
            stroke=color,
            stroke_width=sw,
            stroke_linecap="round",
            stroke_linejoin="round",
            stroke_dasharray="4 3" if dashed else None,
        )
    ]
    if head:
        out.append(
            _el(
                "path",
                d=_poly(
                    [
                        (x1, y1),
                        (x1 - ux * hl - uy * hw, y1 - uy * hl + ux * hw),
                        (x1 - ux * hl + uy * hw, y1 - uy * hl - ux * hw),
                    ]
                ),
                fill=color,
                stroke="none",
            )
        )
    return out


def _cofactor(name, x, y, s=1.0):
    """Cofactor glyph by chemistry: Fe–S cluster (cube), heme (disc with Fe), Cu centre, flavin/quinone (yellow)."""
    n = str(name).lower()
    if "fe" in n and "s" in n:
        r = 2.6 * s
        return [
            _el(
                "path",
                d=_poly([(x - r, y - r * 0.2), (x - r * 0.2, y - r), (x + r, y - r * 0.6), (x + r * 0.2, y + r * 0.2)])
                + " "
                + _poly(
                    [(x - r, y - r * 0.2), (x + r * 0.2, y + r * 0.2), (x + r * 0.2, y + r * 1.1), (x - r, y + r * 0.7)]
                ),
                fill="#C9802E",
                stroke="#6E3F12",
                stroke_width=0.6,
            ),
            _el(
                "path",
                d=_poly(
                    [(x + r * 0.2, y + r * 0.2), (x + r, y - r * 0.6), (x + r, y + r * 0.3), (x + r * 0.2, y + r * 1.1)]
                ),
                fill="#E8B54A",
                stroke="#6E3F12",
                stroke_width=0.6,
            ),
        ]
    if "cu" in n:
        return [
            _el(
                "path",
                d=_circ(x - 1.6 * s, y, 2.2 * s) + " " + _circ(x + 1.6 * s, y, 2.2 * s),
                fill="#3AA6A0",
                stroke="#1D5E5A",
                stroke_width=0.6,
            )
        ]
    if any(k in n for k in ("fmn", "fad", "flavin", "q", "pq", "quinone")):
        return [
            _el(
                "path",
                d=_poly(
                    [
                        (
                            x + 3.2 * s * math.cos(math.pi / 3 * k + math.pi / 6),
                            y + 3.2 * s * math.sin(math.pi / 3 * k + math.pi / 6),
                        )
                        for k in range(6)
                    ]
                ),
                fill="#F2C14E",
                stroke="#8A6512",
                stroke_width=0.7,
            )
        ]
    if any(k in n for k in ("chl", "p680", "p700", "chlorophyll")):
        return [_el("circle", cx=x, cy=y, r=3.4 * s, fill="#3E9A4A", stroke="#1F5A26", stroke_width=0.7)]
    # heme / cytochrome / anything else: red disc with central Fe
    return [
        _el("ellipse", cx=x, cy=y, rx=3.8 * s, ry=2.6 * s, fill="#C8323C", stroke="#6E1218", stroke_width=0.6),
        _el("circle", cx=x, cy=y, r=1.1 * s, fill="#F2C14E"),
    ]


def _ion_r(s, fs):
    return max(_emitted_width(s, fs) / 2 + 1.5, fs * 0.78)


@_drawing_api(
    "parts",
    purpose="离子/质子小圆标记（H⁺、Na⁺、e⁻…）：圆半径按文字实际宽度自动放大，文字永不超出圆（服务端 text_overflows_container）。",
    returns="Geometry（原点在中心；端口 center/四边）",
    semantics=(
        'label 为离子文字；r="auto" 按原生文字框宽度定半径，传数值时取 max(数值, 自动值)。',
        "标记声明为“贴边元素”：放在膜边、通道口、箭头旁都不报 text_straddles_frame / head_on_edge。",
        "页面缩放很小（字号被抬到 10pt 下限）时把 font_size 调到 ≥10/缩放比。",
    ),
    example='h = d.place(ion_marker("H⁺"), at=(300, 120))\nd.place(ion_marker("Na⁺", color="#5B8DB8"), at=(360, 120))',
    rank=30,
)
def ion_marker(label="H⁺", *, r="auto", color=_ION, text_color=None, font_size=11):
    _finite(font_size)
    fs = float(font_size)
    rr = _ion_r(str(label), fs)
    if r != "auto":
        _finite(r)
        rr = max(float(r), rr)
    g = _el("g", data_on_edge="1")
    g.append(
        _el(
            "circle",
            cx=0,
            cy=0,
            r=rr,
            fill=color,
            stroke=_mix(color, "#000000", 0.35),
            stroke_width=0.8,
            data_outline="1",
        )
    )
    t = _el(
        "text",
        x=0,
        y=fs * 0.35,
        font_size=fs,
        fill=text_color or _mix(color, "#000000", 0.62),
        text_anchor="middle",
        font_weight="bold",
    )
    t.text = str(label)
    g.append(t)
    return _finish(g, None, Box(-rr - 0.4, -rr - 0.4, 2 * rr + 0.8, 2 * rr + 0.8), center=(0, 0))


_SHAPES = ("L", "dimer", "globular", "channel")
_SITES = ("top", "bottom", "tm", "tm_left", "tm_right")


def _complex_layout(shape, w, below, above, T):
    """Lobes [(cx, cy, rx, ry, rot, shade)], TM slab x-range, electron sites, pump x."""
    h = T / 2
    lobes = []
    if shape == "L":
        ax = -w / 2 + w * 0.2
        if below > 0:
            lobes += [
                (ax + 1, h + below * 0.2, w * 0.14, below * 0.22, 0.1, 0.12),
                (ax + 5, h + below * 0.5, w * 0.17, below * 0.22, -0.15, 0.0),
                (ax + 10, h + below * 0.77, w * 0.21, below * 0.23, 0.2, 0.22),
            ]
        if above > 0:
            lobes += [(w * 0.1, -h - above * 0.45, w * 0.18, above * 0.5, 0, 0.3)]
        sites = dict(
            bottom=(ax + 10 + w * 0.05, h + below * 0.8), tm=(ax + w * 0.12, h - 3), top=(w * 0.1, -h - above * 0.7)
        )
        pump = w * 0.3
    elif shape == "dimer":
        if below > 0:
            lobes += [
                (sx * w * 0.21, h + below * 0.5, w * 0.24, below * 0.48, sx * 0.12, 0.0 if sx < 0 else 0.14)
                for sx in (-1, 1)
            ]
        if above > 0:
            lobes += [
                (sx * w * 0.23, -h - above * 0.5, w * 0.16, above * 0.48, -sx * 0.15, 0.3 if sx < 0 else 0.38)
                for sx in (-1, 1)
            ]
        sites = dict(tm=(-w * 0.32, -h + 4), top=(w * 0.23, -h - above * 0.62), bottom=(-w * 0.2, h + below * 0.72))
        pump = 0.0
    elif shape == "globular":
        if below > 0:
            lobes += [
                (-w * 0.12, h + below * 0.48, w * 0.3, below * 0.46, 0.2, 0.0),
                (w * 0.17, h + below * 0.5, w * 0.25, below * 0.42, -0.2, 0.2),
            ]
        if above > 0:
            lobes += [(w * 0.05, -h - above * 0.5, w * 0.3, above * 0.5, 0, 0.32)]
        sites = dict(bottom=(-w * 0.1, h + below * 0.7), tm=(-w * 0.25, 0), top=(w * 0.05, -h - above * 0.6))
        pump = w * 0.3
    else:  # channel: two half-cylinders around a central pore, small caps both sides
        for sx in (-1, 1):
            if below > 0:
                lobes.append((sx * w * 0.26, h + below * 0.45, w * 0.22, below * 0.5, 0, 0.1 if sx < 0 else 0.2))
            if above > 0:
                lobes.append((sx * w * 0.26, -h - above * 0.45, w * 0.22, above * 0.5, 0, 0.25 if sx < 0 else 0.35))
        sites = dict(bottom=(0, h + below * 0.8), tm=(0, 0), top=(0, -h - above * 0.8))
        pump = 0.0
    sites.setdefault("tm", (0, 0))
    sites["tm_left"] = (-w / 2 + 6, 0)
    sites["tm_right"] = (w / 2 - 6, 0)
    return lobes, sites, pump


def _draw_complex(spec, x0, ym, T, fs, rich, look, defs, uid):
    """Draw one complex at (x0, ym) (membrane midline). Returns dict(els, texts, boxes, hole, ports, ext)."""
    shape = spec.get("shape", "globular")
    if shape not in _SHAPES:
        raise ValueError(f"membrane complex shape must be one of {_SHAPES}")
    w = float(spec.get("width") or {"L": 120, "dimer": 96, "globular": 70, "channel": 56}[shape])
    below, above = (
        float(v)
        for v in spec.get("span") or {"L": (78, 6), "dimer": (52, 26), "globular": (46, 16), "channel": (14, 14)}[shape]
    )
    _finite(w, below, above)
    color = spec.get("color") or "#5B7DB8"
    edge = _mix(color, "#000000", 0.38)
    h = T / 2
    lobes, sites, pump_x = _complex_layout(shape, w, below, above, T)
    els = []
    shapes_boxes = []
    for i, (cx, cy, rx, ry, rot, sh) in enumerate(lobes):
        pts = [(x0 + px, ym + py) for px, py in _lobe_pts(cx, cy, rx, ry, rot, seed=uid * 7 + i)]
        fill = _mix(color, "#FFFFFF", sh)
        els.append(_el("path", d=_smooth(pts, closed=True), fill=fill, stroke=edge, stroke_width=1))
        shapes_boxes.append(_bbox(pts))
        if look is not None:
            gid = f"mc{uid}_{i}"
            from ._bio_parts import _radial

            defs.append(_radial(gid, _mix(fill, "#FFFFFF", 0.45), fill))
            inner = [(x0 + px, ym + py) for px, py in _lobe_pts(cx, cy, rx * 0.94, ry * 0.94, rot, seed=uid * 7 + i)]
            look.append(_el("path", d=_smooth(inner, closed=True), fill=f"url(#{gid})", opacity=0.6))
    # transmembrane domain: slab + helix rods (dimer shows the two-fold seam)
    tm_top, tm_bot = ym - h - 3, ym + h + 3
    slab = _el(
        "rect",
        x=x0 - w / 2,
        y=tm_top,
        width=w,
        height=tm_bot - tm_top,
        rx=7,
        fill=_mix(color, "#FFFFFF", 0.45),
        stroke=edge,
        stroke_width=1,
        data_outline="1",
    )
    els.insert(0, slab)
    n = max(3, int(w / 9.5))
    hw = (w - 8 - (n - 1) * 1.6) / n
    rods_a, rods_b = [], []
    for k in range(n):
        rx0 = x0 - w / 2 + 4 + k * (hw + 1.6)
        lift = 1.5 * math.sin(k * 1.9 + uid)
        r = hw / 2
        (rods_a if k % 2 == 0 else rods_b).append(
            f"M{fmt(rx0 + r)} {fmt(tm_top + 2 + lift)} A{fmt(r)} {fmt(r)} 0 0 1 {fmt(rx0 + hw)} {fmt(tm_top + 2 + lift + r)} "
            f"V{fmt(tm_bot - 2 + lift - r)} A{fmt(r)} {fmt(r)} 0 0 1 {fmt(rx0)} {fmt(tm_bot - 2 + lift - r)} "
            f"V{fmt(tm_top + 2 + lift + r)} A{fmt(r)} {fmt(r)} 0 0 1 {fmt(rx0 + r)} {fmt(tm_top + 2 + lift)} Z"
        )
    els.append(_el("path", d=" ".join(rods_a), fill=color, stroke=edge, stroke_width=0.6))
    els.append(_el("path", d=" ".join(rods_b), fill=_mix(color, "#FFFFFF", 0.25), stroke=edge, stroke_width=0.6))
    if shape in ("dimer", "channel"):
        els.append(
            _el(
                "path",
                d=f"M{fmt(x0)} {fmt(tm_top + 1)} V{fmt(tm_bot - 1)}",
                fill="none",
                stroke=_mix(color, "#FFFFFF", 0.85),
                stroke_width=2.4 if shape == "channel" else 1.2,
            )
        )
    if look is not None:
        look.append(
            _el("rect", x=x0 - w / 2 + 3, y=tm_top + 2, width=w - 6, height=4, rx=2, fill="#FFFFFF", fill_opacity=0.35)
        )
    shapes_boxes.append(Box(x0 - w / 2, tm_top, w, tm_bot - tm_top))
    body = Box(min(b.x for b in shapes_boxes), min(b.y for b in shapes_boxes), 0, 0)
    body = Box(
        body.x,
        body.y,
        max(b.x + b.width for b in shapes_boxes) - body.x,
        max(b.y + b.height for b in shapes_boxes) - body.y,
    )
    # electron sites and cofactors along the internal path
    e_in, e_out = spec.get("e_sites") or (
        ("bottom", "tm")
        if shape in ("L",) or (shape == "globular" and below >= above)
        else ("tm", "top")
        if shape == "dimer"
        else ("top", "bottom")
    )
    for s in (e_in, e_out):
        if s not in _SITES:
            raise ValueError(f"e_sites must be among {_SITES}")
    p_in = (x0 + sites[e_in][0], ym + sites[e_in][1])
    p_out = (x0 + sites[e_out][0], ym + sites[e_out][1])
    cof = list(spec.get("cofactors") or ())
    cof_pts = []
    for i, c in enumerate(cof):
        name, rel = (c, None) if isinstance(c, str) else (c[0], c[1] if len(c) > 1 else None)
        if rel is None:
            t = (i + 1) / (len(cof) + 1)
            px, py = p_in[0] + (p_out[0] - p_in[0]) * t, p_in[1] + (p_out[1] - p_in[1]) * t
        else:
            px, py = body.x + body.width * float(rel[0]), body.y + body.height * float(rel[1])
        cof_pts.append((name, (px, py)))
    ports = {
        "e_in": p_in,
        "e_out": p_out,
        "tail": (x0, ym),
        "membrane": (x0, ym),
        "tm_l": (x0 - w / 2, ym),
        "tm_r": (x0 + w / 2, ym),
        "top": (x0, body.y),
        "bottom": (x0, body.y + body.height),
    }
    for i, (name, (px, py)) in enumerate(cof_pts):
        ports[f"cof{i}"] = (px, py)
    # proton pumping through the TM domain (bottom → top unless pump_dir="down")
    pumps = int(spec.get("pumps") or 0)
    ion = spec.get("ion", "H⁺")
    if pumps:
        px = x0 + pump_x
        reach_top = min([b.y for b in shapes_boxes if b.x <= px <= b.x + b.width] + [tm_top]) - 6
        reach_bot = max([b.y + b.height for b in shapes_boxes if b.x <= px <= b.x + b.width] + [tm_bot]) + 6
        y0, y1 = (reach_bot, reach_top) if spec.get("pump_dir", "up") == "up" else (reach_top, reach_bot)
        ports["in"], ports["out"] = (px, y0), (px, y1)
        txt = f"{pumps}{ion}" if pumps > 1 else str(ion)
        ports["_pump"] = (px, y0, y1, txt)
    return dict(
        els=els,
        cof=cof_pts,
        ports=ports,
        body=body,
        T=T,
        hole=(x0 - w / 2 - 1, x0 + w / 2 + 1),
        shapes=shapes_boxes,
        color=color,
        name=spec.get("name"),
        lobes=lobes,
        x0=x0,
        ym=ym,
    )


def _draw_pump(info, fs, texts, boxes, shapes, color=_PROTON):
    """Straight H⁺ arrow through the TM domain, from beyond the body on one side to beyond it on the other; count label at the tip."""
    px, y0, y1, txt = info["ports"].pop("_pump")
    up = y1 < y0
    ym, h = info["ym"], info["T"] / 2
    near = [b for b in info["shapes"] if b.x - 3 <= px <= b.x + b.width + 3]
    top = min(b.y for b in near) - 6
    bot = max(b.y + b.height for b in near) + 6
    top, bot = min(top, ym - h - 16), max(bot, ym + h + 16)
    y0, y1 = (bot, top) if up else (top, bot)
    info["ports"]["in"], info["ports"]["out"] = (px, y0), (px, y1)
    els = [
        _el(
            "path",
            d=f"M{fmt(px)} {fmt(y0)} V{fmt(y1)}",
            fill="none",
            stroke="#FFFFFF",
            stroke_width=5,
            stroke_linecap="round",
        )
    ]
    els += _arrow([(px, y0), (px, y1)], color, 2.2, smooth=False)
    ty = y1 - 4 if up else y1 + fs + 2
    _place(
        [
            ((px, ty), "middle"),
            ((px + 5, y1 + (fs * 0.4 if up else 0)), "start"),
            ((px - 5, y1 + (fs * 0.4 if up else 0)), "end"),
            ((px, ty - fs * 1.2 if up else ty + fs * 1.2), "middle"),
        ],
        txt,
        fs,
        color,
        shapes,
        boxes,
        texts,
    )
    return els


def _name_in_lobe(info, fs, texts, boxes, *, prefer=None):
    """Complex name: white bold inside the biggest lobe that fits it, else just outside the body."""
    name = info["name"]
    if not name:
        return
    x0, ym = info["x0"], info["ym"]
    cands = sorted(info["lobes"], key=lambda l: -l[2] * l[3])
    for cx, cy, rx, ry, rot, sh in cands:
        need = _emitted_width(str(name), fs * 1.1)
        if need < rx * 1.5 and fs * 1.3 < ry * 1.5:
            t, b = _text(x0 + cx, ym + cy + fs * 1.1 * 0.35, name, fs * 1.1, "#FFFFFF")
            texts.append(t)
            boxes.append(b)
            info["name_box"] = b
            return
    body = info["body"]
    t, b = _text(x0, body.y + body.height + fs * 1.15, name, fs * 1.05, _mix(info["color"], "#000000", 0.45))
    texts.append(t)
    boxes.append(b)


def _cofactor_marks(info, fs, texts, boxes, labels):
    els = []
    for name, (px, py) in info["cof"]:
        els += _cofactor(name, px, py)
        if not labels:
            continue
        sub = max(10.0, fs * 0.8)
        for anc, dx in (("start", 6), ("end", -6)):
            t, b = _text(px + dx, py + sub * 0.35, name, sub, _INK, anc, bold=False)
            ew = _emitted_width(str(name), sub, bold=False)
            b = Box(b.x if anc == "start" else px + dx - ew, b.y, ew, b.height)
            # inside exactly one lobe/slab, or clear of every protein shape
            owners = [s for s in info["shapes"] if _hits(b, [s], 0)]
            if (not owners or any(_inside(b, s) for s in owners)) and not _hits(b, boxes):
                texts.append(t)
                boxes.append(b)
                break
    return els


@_drawing_api(
    "parts",
    purpose="膜蛋白复合物（教科书级侧视）：跨膜结构域（螺旋束）+ 外周臂/亚基团块，可标辅因子、按亚基数画质子泵；呼吸链复合物 I–IV、光系统、细胞色素 b6f 等通用。",
    returns="Geometry（原点在中心；端口 tail/membrane=膜中线，top/bottom，e_in/e_out 电子进出位点，in/out 质子泵起止，cof{i} 辅因子）",
    semantics=(
        'shape："L"（膜臂 + 伸向下侧的外周臂，复合物 I 型）、"dimer"（二聚体，两侧都有团块，复合物 III/b6f）、"globular"（单团块，复合物 II/IV、光系统）、"channel"（中央孔道）。',
        "span=(下侧深度, 上侧深度) 为伸出膜表面的距离；width 为跨膜段宽度；membrane_thickness 与所在膜一致（默认 22）。上侧约定为 H⁺ 积累侧（膜间隙/类囊体腔/周质）。",
        'cofactors=["FMN", "Fe-S"] 沿 e_in→e_out 自动排布（或 ("FMN", (0–1 相对位置))）；图形按化学：Fe-S 立方簇、血红素红盘、Cu 双球、黄素/醌黄六边形、叶绿素绿球；cofactor_labels=True 写小字。',
        'e_sites=(进, 出) 取 "top"/"bottom"/"tm"/"tm_left"/"tm_right"，默认按形状；pumps=n 画一条穿膜 H⁺ 箭头并写 “nH⁺”（pump_dir="down" 反向，ion= 换离子）。',
        '立在膜上：d.place(membrane_complex(...), at=膜中线上的点, anchor="tail")；整条链用 transport_chain。',
    ),
    example='d.add("mem", membrane("M 60 270 L 900 270", thickness=22))\n'
    'c1 = d.place(membrane_complex("I", shape="L", cofactors=["FMN", "Fe-S", "Fe-S"], pumps=4), at=(300, 270), anchor="tail")',
    rank=31,
)
def membrane_complex(
    name=None,
    *,
    shape="globular",
    width=None,
    span=None,
    subunits=None,
    cofactors=(),
    cofactor_labels=False,
    e_sites=None,
    pumps=0,
    pump_dir="up",
    ion="H⁺",
    color="#5B7DB8",
    membrane_thickness=22,
    font_size=12,
    style="rich",
    seed=0,
):
    rich = _check_style(style)
    T, fs = float(membrane_thickness), float(font_size)
    _finite(T, fs)
    holder, defs = _el("g"), _el("defs")
    holder.append(defs)
    look = _look() if rich else None
    spec = dict(
        name=name,
        shape=shape,
        width=width,
        span=span,
        cofactors=cofactors,
        e_sites=e_sites,
        pumps=pumps,
        pump_dir=pump_dir,
        ion=ion,
        color=color,
    )
    info = _draw_complex(spec, 0.0, 0.0, T, fs, rich, look, defs, seed)
    texts, boxes = [], []
    holder.extend(info["els"])
    if look is not None and len(look):
        holder.append(look)
    holder.extend(_cofactor_marks(info, fs, texts, boxes, cofactor_labels))
    _subunit_labels(info, subunits, fs, texts, boxes)
    if info["ports"].get("_pump"):
        holder.extend(_draw_pump(info, fs, texts, boxes, info["shapes"]))
    _name_in_lobe(info, fs, texts, boxes)
    holder.extend(texts)
    from ._geometry import _union

    bounds = _union([info["body"]] + boxes + [Box(p[0] - 3, p[1] - 3, 6, 6) for k, p in info["ports"].items()])
    ports = info["ports"]
    ports["center"] = (0, 0)
    return _finish(holder, defs, bounds, **ports)


def _subunit_labels(info, subunits, fs, texts, boxes):
    """Optional short subunit names written inside lobes (in lobe order; skipped where they do not fit)."""
    if not subunits:
        return
    sub = max(10.0, fs * 0.8)
    x0, ym = info["x0"], info["ym"]
    for (cx, cy, rx, ry, rot, sh), s in zip(info["lobes"], subunits):
        if not s:
            continue
        if _emitted_width(str(s), sub) < rx * 1.5 and sub * 1.3 < ry * 1.5:
            t, b = _text(x0 + cx, ym + cy + sub * 0.35 + (ry * 0.45 if info["name"] else 0), s, sub, "#FFFFFF")
            if not _hits(b, boxes):
                texts.append(t)
                boxes.append(b)


def _text_ok(b, shapes, boxes, pad=2.0):
    """Server lint owns a text to the innermost native shape its box touches."""
    if _hits(b, boxes, pad):
        return False
    touch = [s for s in shapes if _hits(b, [s], pad)]
    inner = [s for s in touch if not any(o is not s and _inside(o, s, 0) for o in touch)]
    return all(_inside(b, s, 1.0) for s in inner)


def _place(cands, s, fs, color, shapes, boxes, texts, *, bold=True, force=True, avoid=()):
    """First candidate ((x, y), anchor) whose emitted text box passes _text_ok; returns the box or None."""
    for (x, y), anc in cands:
        t, b = _text(x, y, s, fs, color, anc, bold)
        ew = _emitted_width(str(s), fs, bold)
        x0 = x - (ew / 2 if anc == "middle" else ew if anc == "end" else 0)
        eb = Box(x0, b.y, ew, b.height)
        if _text_ok(eb, shapes, list(boxes) + list(avoid)):
            texts.append(t)
            boxes.append(eb)
            return eb
    if force:  # nothing clean: at least never on top of other text
        pick = cands[0]
        for (x, y), anc in cands:
            ew = _emitted_width(str(s), fs, bold)
            x0 = x - (ew / 2 if anc == "middle" else ew if anc == "end" else 0)
            if not _hits(Box(x0, y - fs * 0.92, ew, fs * 1.2), boxes):  # text never on text; may touch a path
                pick = ((x, y), anc)
                break
        (x, y), anc = pick
        t, b = _text(x, y, s, fs, color, anc, bold)
        ew = _emitted_width(str(s), fs, bold)
        texts.append(t)
        boxes.append(Box(x - (ew / 2 if anc == "middle" else ew if anc == "end" else 0), b.y, ew, b.height))
        return b
    return None


_ATP_LABELS = dict(c="c", a="a", b="b₂", delta="δ", gamma="γ", epsilon="ε", alpha="α", beta="β", F0="F₀", F1="F₁")


def _build_synthase(
    T, s, n_c, colors, labels, flow, rotation, proton_path, reaction, fs, rich, defs, look, uid=0, ion="H⁺"
):
    """Shapes/texts with F₁ on +y (membrane midline y=0). Returns (els, texts, boxes, shape_boxes, ports, extent)."""
    h = T / 2
    ring_c, a_c, stalk_c, al_c, be_c, de_c = colors
    els, shapes = [], []

    def add(el, box=None):
        els.append(el)
        if box is not None:
            shapes.append(box)
        return el

    Rc = 28 * s
    ry_cap = 5 * s
    ring_top, ring_bot = -h - 5 * s, h + 5 * s
    edge = _mix(ring_c, "#000000", 0.4)
    barrel = (
        f"M{fmt(-Rc)} {fmt(ring_top)} A{fmt(Rc)} {fmt(ry_cap)} 0 0 1 {fmt(Rc)} {fmt(ring_top)} V{fmt(ring_bot)} "
        f"A{fmt(Rc)} {fmt(ry_cap)} 0 0 1 {fmt(-Rc)} {fmt(ring_bot)} Z"
    )
    add(
        _el("path", d=barrel, fill=ring_c, stroke=edge, stroke_width=1, data_outline="1"),
        Box(-Rc, ring_top - ry_cap, 2 * Rc, ring_bot - ring_top + 2 * ry_cap),
    )
    # staves: n_c subunits around the ring, the front half visible; projected widths shrink toward the rims
    vis = []
    for k in range(n_c):
        a0 = -math.pi / 2 + (k + 0.5) * 2 * math.pi / n_c - math.pi / n_c * 0.5
        a1 = a0 + 2 * math.pi / n_c
        if math.cos((a0 + a1) / 2) <= 0:
            continue
        lo, hi = max(a0, -math.pi / 2), min(a1, math.pi / 2)
        if hi - lo < 1e-3:
            continue
        vis.append((Rc * math.sin(lo), Rc * math.sin(hi), k))
    lit, dark = [], []
    for x0, x1, k in vis:
        a, b = x0 + 0.9 * s, x1 - 0.9 * s
        if b - a < 0.8:
            continue
        yt = ring_top + ry_cap * math.sqrt(max(0.0, 1 - ((a + b) / 2 / Rc) ** 2)) + 1.5 * s
        yb = ring_bot + ry_cap * math.sqrt(max(0.0, 1 - ((a + b) / 2 / Rc) ** 2)) - 1.5 * s
        r = min((b - a) / 2, 3 * s)
        (lit if k % 2 == 0 else dark).append(_rrect(a, yt, b - a, yb - yt, r))
    add(_el("path", d=" ".join(lit), fill=_mix(ring_c, "#FFFFFF", 0.28), stroke=edge, stroke_width=0.6))
    add(_el("path", d=" ".join(dark), fill=_mix(ring_c, "#FFFFFF", 0.1), stroke=edge, stroke_width=0.6))
    # top cap (membrane-far face of the ring, seen slightly from above) lighter
    add(
        _el(
            "ellipse",
            cx=0,
            cy=ring_top,
            rx=Rc,
            ry=ry_cap,
            fill=_mix(ring_c, "#FFFFFF", 0.5),
            stroke=edge,
            stroke_width=1,
        )
    )
    add(
        _el(
            "ellipse",
            cx=0,
            cy=ring_top,
            rx=Rc * 0.45,
            ry=ry_cap * 0.45,
            fill=_mix(ring_c, "#FFFFFF", 0.2),
            stroke=edge,
            stroke_width=0.6,
        )
    )
    ax0, ax1 = Rc - 3 * s, Rc + 25 * s
    a_top, a_bot = -h - 8 * s, h + 8 * s
    ae = _mix(a_c, "#000000", 0.4)
    a_pts = [
        (ax0, a_top + 4 * s),
        (ax0 + 8 * s, a_top),
        (ax1 - 4 * s, a_top + 1 * s),
        (ax1, a_top + 8 * s),
        (ax1 + 1.5 * s, 0),
        (ax1, a_bot - 6 * s),
        (ax1 - 5 * s, a_bot),
        (ax0 + 6 * s, a_bot - 0.5 * s),
        (ax0, a_bot - 5 * s),
        (ax0 - 1 * s, 0),
    ]
    add(_el("path", d=_smooth(a_pts, closed=True), fill=a_c, stroke=ae, stroke_width=1), _bbox(a_pts))
    lumen = _mix(a_c, "#FFFFFF", 0.72)
    inlet = [(ax0 + 15 * s, a_top + 1.5 * s), (ax0 + 10 * s, -h * 0.5), (ax0 + 1.5 * s, -2.5 * s)]
    outlet = [(ax0 + 1.5 * s, 3.5 * s), (ax0 + 9 * s, h * 0.6), (ax0 + 13 * s, a_bot - 1.5 * s)]
    for lane in (inlet, outlet):
        add(_el("path", d=_smooth(lane), fill="none", stroke=lumen, stroke_width=4.2 * s, stroke_linecap="round"))
    yF = h + 5 * s + 20 * s + 34 * s  # F₁ centre
    rF = 34 * s
    gamma = [
        (-4.5 * s, ring_bot - 1),
        (4.5 * s, ring_bot - 1),
        (5 * s, yF - rF * 0.2),
        (3 * s, yF + rF * 0.45),
        (-3 * s, yF + rF * 0.45),
        (-5 * s, yF - rF * 0.2),
    ]
    ge = _mix(stalk_c, "#000000", 0.4)
    add(
        _el("path", d=_poly(gamma), fill=stalk_c, stroke=ge, stroke_width=1, stroke_linejoin="round"),
        Box(-5 * s, ring_bot - 1, 10 * s, yF - rF - ring_bot + 1),
    )
    eps = _lobe_pts(-10 * s, ring_bot + 6.5 * s, 8.5 * s, 5.5 * s, 0.1, seed=uid + 3)
    add(
        _el("path", d=_smooth(eps, closed=True), fill=_mix(stalk_c, "#FFFFFF", 0.35), stroke=ge, stroke_width=1),
        _bbox(eps),
    )
    # back half of the hexamer: two α lobes peeking out at the rims (β-α-β in front → α-β-α-β-α alternation)
    for sx in (-1, 1):
        pts = _lobe_pts(sx * rF * 1.12, yF - 1 * s, rF * 0.36, rF * 0.9, 0, wobble=0.03, seed=uid + sx)
        col = _mix(al_c, "#000000", 0.18)
        add(
            _el("path", d=_smooth(pts, closed=True), fill=col, stroke=_mix(col, "#000000", 0.35), stroke_width=1),
            _bbox(pts),
        )
    lobes = []
    for theta, kind in ((-60, "beta"), (60, "beta"), (0, "alpha")):
        t = math.radians(theta)
        cx = rF * 0.95 * math.sin(t)
        rx = rF * (0.33 + 0.2 * math.cos(t))
        col = be_c if kind == "beta" else al_c
        pts = _lobe_pts(cx, yF + 1 * s, rx, rF * 0.98, 0, wobble=0.04, seed=uid + theta)
        # pear shape: narrower toward the membrane (top of the hexamer as drawn)
        pts = [(cx + (px - cx) * (0.82 + 0.18 * (py - yF + rF) / (2 * rF)), py) for px, py in pts]
        lobes.append((kind, cx, rx, pts, col))
        if kind == "alpha":
            # γ passes behind the front α: draw the α after γ (already drawn above)
            pass
    for kind, cx, rx, pts, col in lobes:
        add(
            _el("path", d=_smooth(pts, closed=True), fill=col, stroke=_mix(col, "#000000", 0.38), stroke_width=1),
            _bbox(pts),
        )
        if look is not None:
            from ._bio_parts import _radial

            gid = f"atps{uid}_{kind}{int(cx)}"
            defs.append(_radial(gid, _mix(col, "#FFFFFF", 0.5), col, fx=0.36, fy=0.3))
            inner = [(cx + (px - cx) * 0.9, yF + (py - yF) * 0.93) for px, py in pts]
            look.append(_el("path", d=_smooth(inner, closed=True), fill=f"url(#{gid})", opacity=0.7))
    # nucleotide at each visible β catalytic site (interface β/α, membrane-far half)
    sites = []
    for kind, cx, rx, pts, col in lobes:
        if kind == "beta":
            sx = cx + (rx * 0.35 if cx < 0 else -rx * 0.35)
            sites.append((sx, yF + rF * 0.28))
    nucleotides = _el(
        "path", d=" ".join(_circ(x, y, 2.8 * s) for x, y in sites), fill="#F2C14E", stroke="#8A6512", stroke_width=0.7
    )
    dy = yF + rF + 3 * s
    dpts = _lobe_pts(14 * s, dy + 2 * s, 17 * s, 10 * s, 0.05, seed=uid + 9)
    bx = rF * 1.42 + 5 * s
    be = _mix(stalk_c, "#000000", 0.25)
    for off in (0, 4.2 * s):
        lane = [
            (ax1 - 8 * s + off, a_bot - 2 * s),
            (bx + off, a_bot + 14 * s),
            (bx + off, yF + rF * 0.55),
            (28 * s + off * 0.5, dy - 1 * s),
        ]
        add(_el("path", d=_smooth(lane), fill="none", stroke=be, stroke_width=3.6 * s, stroke_linecap="round"))
        add(
            _el(
                "path",
                d=_smooth(lane),
                fill="none",
                stroke=_mix(stalk_c, "#FFFFFF", 0.3 if off else 0.1),
                stroke_width=2.2 * s,
                stroke_linecap="round",
            )
        )
    shapes.append(Box(ax1 - 10 * s, a_bot - 3 * s, bx + 6.5 * s - ax1 + 10 * s, dy - a_bot + 3 * s))
    add(
        _el("path", d=_smooth(dpts, closed=True), fill=de_c, stroke=_mix(de_c, "#000000", 0.38), stroke_width=1),
        _bbox(dpts),
    )
    texts, boxes = [], []
    synth = flow == "synthesis"
    if rotation:
        ry0 = ring_bot + 15 * s
        rx_ = 17 * s
        pts = [
            (rx_ * math.cos(a), ry0 + 4.5 * s * math.sin(a)) for a in [math.radians(v) for v in range(200, -21, -20)]
        ]
        if not synth:
            pts = pts[::-1]
        els.extend(_arrow([(x, y) for x, y in pts], "#3D3D3D", 1.6 * s))
    ports = {}
    if proton_path:
        inn = [(inlet[0][0] + 3 * s, -h - 30 * s), (inlet[0][0], a_top - 1.5 * s)]
        out = [(outlet[-1][0], a_bot + 1.5 * s), (outlet[-1][0] + 2 * s, a_bot + 17 * s)]
        if synth:
            els.extend(_arrow(inn, _PROTON, 2 * s, smooth=False))
            els.extend(_arrow(out, _PROTON, 2 * s, smooth=False))
            ports.update(proton_in=inn[0], proton_out=out[-1])
        else:
            els.extend(_arrow(out[::-1], _PROTON, 2 * s, smooth=False))
            els.extend(_arrow(inn[::-1], _PROTON, 2 * s, smooth=False))
            ports.update(proton_in=out[-1], proton_out=inn[0])
        # proton on a c-subunit at the a/c interface
        els.append(_el("circle", cx=Rc - 3 * s, cy=0, r=2.4 * s, fill=_PROTON))
    else:
        ports.update(proton_in=(ax0 + 15 * s, a_top), proton_out=(ax0 + 13 * s, a_bot))
    lab = dict(_ATP_LABELS)
    if isinstance(labels, dict):
        lab.update(labels)
    sub = max(10.0, fs * 0.92)
    if labels:
        white = "#FFFFFF"
        for kind, cx, rx, pts, col in lobes:
            # lint owns a label to the innermost shape it sits in: only the lobe itself matters here
            _place(
                [((cx, yF - rF * 0.3 + sub * 0.35), "middle"), ((cx, yF + sub * 0.35), "middle")],
                lab[kind],
                sub * 1.1,
                white,
                [_bbox(pts)],
                boxes,
                texts,
                force=False,
            )
        _place(
            [((-Rc * 0.45, 2 * s + sub * 0.35), "middle"), ((-Rc * 0.55, sub * 0.35), "middle")],
            lab["c"],
            sub,
            white,
            shapes,
            boxes,
            texts,
            force=False,
        )
        _place([((ax0 + 18 * s, sub * 0.35), "middle")], lab["a"], sub, white, shapes, boxes, texts, force=False)
        _place(
            [((14 * s, dy + 2 * s + sub * 0.35), "middle"), ((33 * s, dy + 12 * s + sub * 0.35), "start")],
            lab["delta"],
            sub,
            _mix(de_c, "#000000", 0.6),
            shapes,
            boxes,
            texts,
        )
        _place(
            [((bx + 9 * s, yF + sub * 0.35), "start"), ((bx + 9 * s, yF - rF * 0.5), "start")],
            lab["b"],
            sub,
            _INK,
            shapes,
            boxes,
            texts,
        )
        _place(
            [((-21 * s, ring_bot + 21 * s), "end"), ((9 * s, ring_bot + 12 * s), "start")],
            lab["gamma"],
            sub,
            _INK,
            shapes,
            boxes,
            texts,
        )
        _place(
            [((-21 * s, ring_bot + 8 * s), "end"), ((-10 * s, ring_bot + 7 * s + sub * 0.35), "middle")],
            lab["epsilon"],
            sub,
            _INK,
            shapes,
            boxes,
            texts,
        )
        big = fs * 1.15
        _place(
            [((-Rc - 6 * s, -h - 8 * s), "end"), ((-Rc - 6 * s, big * 0.35), "end")],
            lab["F0"],
            big,
            _INK,
            shapes,
            boxes,
            texts,
        )
        _place([((-rF * 1.5 - 6 * s, yF - rF * 0.5), "end")], lab["F1"], big, _INK, shapes, boxes, texts)
    if reaction:
        lhs, rhs = reaction
        txt = f"{lhs} → {rhs}" if synth else f"{rhs} → {lhs}"
        x = -rF * 1.5 - 6 * s
        _place(
            [((x, yF + rF * 0.35), "end"), ((x, yF + rF * 0.8), "end"), ((x, yF + rF + 14 * s), "end")],
            txt,
            fs,
            "#7A4E0E",
            shapes,
            boxes,
            texts,
        )
    ports.update(
        tm_l=(-Rc, 0),
        tm_r=(ax1 + 1.5 * s, 0),
        f1=(0, yF),
        fo=(0, 0),
        top=(12 * s, dy + 8 * s),
        tail=(0, 0),
        membrane=(0, 0),
        rotor=(0, ring_bot + 15 * s),
        site=sites[0] if sites else (0, yF),
    )
    ext = Box(
        -rF * 1.5,
        -h - 31 * s if proton_path else ring_top - ry_cap,
        bx + 7 * s + rF * 1.5,
        dy + 8 * s - (-h - 31 * s if proton_path else ring_top - ry_cap),
    )
    if proton_path and ion:
        hx, hy = inn[0]
        _place(
            [((hx + 6 * s, hy + fs * 0.4), "start"), ((hx - 6 * s, hy + fs * 0.4), "end")],
            ion,
            fs,
            _PROTON,
            shapes,
            boxes,
            texts,
        )
    return els, texts, boxes, shapes, ports, ext, nucleotides


def _rrect(x, y, w, h, r):
    return (
        f"M{fmt(x + r)} {fmt(y)} H{fmt(x + w - r)} A{fmt(r)} {fmt(r)} 0 0 1 {fmt(x + w)} {fmt(y + r)} V{fmt(y + h - r)} "
        f"A{fmt(r)} {fmt(r)} 0 0 1 {fmt(x + w - r)} {fmt(y + h)} H{fmt(x + r)} A{fmt(r)} {fmt(r)} 0 0 1 {fmt(x)} {fmt(y + h - r)} "
        f"V{fmt(y + r)} A{fmt(r)} {fmt(r)} 0 0 1 {fmt(x + r)} {fmt(y)} Z"
    )


def _flip_texts(texts, boxes):
    for t in texts:
        fs = float(t.get("font-size") or t.get("font_size") or 12)
        y = float(t.get("y"))
        # mirror the text box (baseline sits ~.92 fs below the box top, box height 1.2 fs)
        top = y - fs * 0.92
        t.set("y", fmt(-(top + fs * 1.2) + fs * 0.92))
    return [Box(b.x, -(b.y + b.height), b.width, b.height) for b in boxes]


@_drawing_api(
    "parts",
    purpose="ATP 合酶 F₀F₁（教科书侧视）：膜内 c 环桶（可见 c 亚基条）+ 旁侧 a 亚基两个半通道、b₂ 外周柄直达 F₁ 远端的 δ、γ/ε 中央柄插入 α₃β₃（侧视 β-α-β 交替叶），旋转箭头、H⁺ 通路、β 位点 ADP+Pi→ATP。",
    returns="Geometry（原点在中心；端口 tail/membrane=膜中线转子轴，proton_in/proton_out，f1，fo，top（δ 远端），rotor，site（β 催化位点））",
    semantics=(
        '立在膜上：d.place(atp_synthase(), at=膜中线上的点, anchor="tail")；f1_side="bottom"（默认，F₁ 在下=基质/基质侧）或 "top"；H⁺ 从 F₁ 对侧进入。',
        'n_c 为 c 亚基数（8–15，影响桶上条纹数）；flow="hydrolysis" 反转旋转与 H⁺ 方向（ATP→ADP+Pi，V/F 型 ATP 酶作泵）；rotation/proton_path 可关。',
        'labels=True 用标准亚基名（c/a/b₂/δ/γ/ε/α/β/F₀/F₁），传 dict 覆盖个别名字，False 不写；reaction=("ADP + Pi", "ATP") 写在 F₁ 旁，None 不写。',
        "colors=(c环, a, 柄, α, β, δ) 覆盖默认配色；membrane_thickness 与所在膜一致（默认 22，全部按它缩放）。",
    ),
    example='d.add("mem", membrane("M 120 200 L 840 200", thickness=22))\n'
    'atp = d.place(atp_synthase(n_c=10), at=(480, 200), anchor="tail")',
    rank=32,
)
def atp_synthase(
    *,
    view="side",
    n_c=10,
    labels=True,
    flow="synthesis",
    rotation=True,
    proton_path=True,
    reaction=("ADP + Pi", "ATP"),
    f1_side="bottom",
    ion="H⁺",
    colors=None,
    membrane_thickness=22,
    font_size=12,
    style="rich",
    seed=0,
):
    if view != "side":
        raise ValueError('atp_synthase only draws the textbook side view (view="side")')
    if flow not in ("synthesis", "hydrolysis"):
        raise ValueError('flow must be "synthesis" or "hydrolysis"')
    if f1_side not in ("bottom", "top"):
        raise ValueError('f1_side must be "bottom" or "top"')
    if not 6 <= int(n_c) <= 17:
        raise ValueError("n_c must be between 6 and 17")
    rich = _check_style(style)
    T, fs = float(membrane_thickness), float(font_size)
    _finite(T, fs)
    s = max(T, 14.0) / 22.0
    cols = tuple(colors) if colors else ("#C9A23A", "#3F7FBF", "#6E6E8E", "#D9785A", "#6B8FCB", "#C46B9E")
    if len(cols) != 6:
        raise ValueError("colors needs 6 colors: (c-ring, a, stalks, alpha, beta, delta)")
    holder, defs = _el("g"), _el("defs")
    holder.append(defs)
    look = _look() if rich else None
    els, texts, boxes, shapes, ports, ext, nuc = _build_synthase(
        T, s, int(n_c), cols, labels, flow, rotation, proton_path, reaction, fs, rich, defs, look, seed, ion
    )
    body = _el("g")
    body.extend(els)
    if look is not None and len(look):
        body.append(look)
    body.append(nuc)
    if f1_side == "top":
        flipped = _el("g", transform="scale(1 -1)")
        flipped.append(body)
        body = flipped
        boxes = _flip_texts(texts, boxes)
        ports = {k: (x, -y) for k, (x, y) in ports.items()}
        ext = Box(ext.x, -(ext.y + ext.height), ext.width, ext.height)
    holder.append(body)
    holder.extend(texts)
    from ._geometry import _union

    bounds = _union([ext] + boxes)
    ports["center"] = (0, 0)
    return _finish(holder, defs, bounds, **ports)


def _carrier_lipid(x, ym, T, name, color, fs):
    """Lipid-soluble carrier (quinone-type): ring in the hydrophobic core + isoprenoid tail along the midplane."""
    sub = max(10.0, fs * 0.9)
    r = max(10.5, _emitted_width(str(name), sub) / 2 / math.cos(math.pi / 6) + 1.2)
    r = min(r, T * 0.9)
    edge = _mix(color, "#000000", 0.45)
    tail = []
    for k in range(7):
        tail.append((x + r * 0.85 + k * 4.2, ym + (2.2 if k % 2 else -2.2)))
    els = [
        _el(
            "path",
            d=_poly(tail, closed=False),
            fill="none",
            stroke=_mix(color, "#000000", 0.3),
            stroke_width=1.4,
            stroke_linejoin="round",
        ),
        _el(
            "path",
            d=_poly([(x + r * math.cos(math.pi / 3 * k), ym + r * math.sin(math.pi / 3 * k)) for k in range(6)]),
            fill=color,
            stroke=edge,
            stroke_width=1,
        ),
    ]
    box = Box(x - r, ym - r * 0.87, 2 * r, r * 1.74)
    t, tb = _text(x, ym + sub * 0.35, name, sub, _mix(color, "#000000", 0.65))
    return els, [t], [tb], [box], dict(e_in=(x, ym), e_out=(x, ym), center=(x, ym)), (x - r - 1, x + r + 30), box


def _carrier_peripheral(x, ym, T, name, color, fs, side, uid, cofactor=None, size=1.0):
    """Small water-soluble protein docked on one membrane surface (cytochrome c / plastocyanin / ferredoxin type)."""
    rx, ry = 13.0 * size, 10.0 * size
    sg = -1 if side == "top" else 1
    cy = ym + sg * (T / 2 + ry * 0.85)
    pts = _lobe_pts(x, cy, rx, ry, 0.2, seed=uid + 5)
    els = [_el("path", d=_smooth(pts, closed=True), fill=color, stroke=_mix(color, "#000000", 0.38), stroke_width=1)]
    els += _cofactor(cofactor or "heme", x, cy)
    return els, _bbox(pts), dict(e_in=(x - 2, cy), e_out=(x + 2, cy), center=(x, cy)), cy, ry


_MEMBER_KINDS = ("complex", "lipid", "peripheral", "atp_synthase")


def _member_kind(m):
    if isinstance(m, str):
        return dict(kind="lipid", name=m)
    if not isinstance(m, dict):
        raise ValueError("each member must be a dict (complex/carrier spec) or a short string for a lipid carrier")
    m = dict(m)
    m.setdefault("kind", "complex")
    if m["kind"] not in _MEMBER_KINDS:
        raise ValueError(f"member kind must be one of {_MEMBER_KINDS}")
    return m


@_drawing_api(
    "parts",
    purpose="膜电子传递链场景（教科书侧视）：磷脂双层条带上依次排布膜蛋白复合物、脂溶性载体（膜内醌环）、外周小蛋白载体（膜表面）与 ATP 合酶，自动画电子路径弯箭头、H⁺ 泵出箭头与计数、两侧区室名、反应式。线粒体呼吸链、类囊体光合链、细菌呼吸链通用。",
    returns="Geometry（原点在中心；每个成员端口 m{i}/m{i}_top/m{i}_bottom/m{i}_e_in/m{i}_e_out，ATP 合酶另有 m{i}_f1；按名字的同名端口 <name>；整体 top_side/bottom_side/membrane）",
    semantics=(
        'members 依次从左到右：复合物 {"name": "I", "shape": "L"/"dimer"/"globular"/"channel", "cofactors": [...], "pumps": 4, "color":, "span":, "e_sites":}（参数同 membrane_complex）；'
        '脂溶性载体 "Q" 或 {"kind": "lipid", "name": "PQ"}；外周载体 {"kind": "peripheral", "name": "cyt c", "side": "top"/"bottom", "cofactor": "heme"/"Cu"/"Fe-S", "size": 1}；{"kind": "atp_synthase", ...atp_synthase 参数}。',
        'sides=("上侧名", "下侧名") 由调用方写（如 ("膜间隙", "基质")、("类囊体腔", "基质")）；约定上侧为 H⁺ 积累侧，ATP 合酶 F₁ 朝下。',
        '电子路径按成员顺序经过每个非 ATP 合酶成员（成员加 "e": False 跳过，"to": "Q" 指定下一站，可多支汇入同一载体）；成员的 "reaction": "NADH → NAD⁺" 写在其电子入口一侧，terminal="½O₂ + 2H⁺ → H₂O" 写在最后一站出口。',
        'protons=False 关掉所有 H⁺ 箭头；gradient=n 在上侧散布 n 个 H⁺ 小圆（下侧 n//3 个）表示质子梯度；electron_label="e⁻"。',
        'width 为总宽，其余尺寸按内容；membrane="bilayer"（磷脂头尾）或 "band"（纯色带）。',
    ),
    example='etc = d.place(transport_chain([{"name": "I", "shape": "L", "cofactors": ["FMN", "Fe-S"], "pumps": 4}, "Q",\n'
    '    {"name": "III", "shape": "dimer", "pumps": 4}, {"kind": "peripheral", "name": "cyt c"}, {"name": "IV", "pumps": 2, "e_sites": ("top", "bottom")},\n'
    '    {"kind": "atp_synthase"}], sides=("膜间隙", "基质"), terminal="½O₂ + 2H⁺ → H₂O", width=860), at=(480, 270))',
    rank=33,
)
def transport_chain(
    members,
    *,
    sides=("P 侧", "N 侧"),
    electron_path=True,
    protons=True,
    terminal=None,
    gradient=0,
    electron_label="e⁻",
    ion="H⁺",
    width=860,
    membrane="bilayer",
    membrane_color="#9A88C9",
    membrane_thickness=22,
    font_size=12,
    style="rich",
    seed=3,
):
    rich = _check_style(style)
    if membrane not in ("bilayer", "band"):
        raise ValueError('membrane must be "bilayer" or "band"')
    members = [_member_kind(m) for m in members]
    if not members:
        raise ValueError("members must not be empty")
    W, T, fs = float(width), float(membrane_thickness), float(font_size)
    _finite(W, T, fs)
    h = T / 2
    top_name, bot_name = (list(sides) + ["", ""])[:2]
    lab_w = max([_emitted_width(str(s), fs) for s in (top_name, bot_name) if s] + [0]) + 10
    x0, x1 = lab_w + 4, W - 6

    def footprint(m):
        k = m["kind"]
        if k == "complex":
            info = _draw_complex(m, 0, 0, T, fs, False, None, _el("defs"), 0)
            b = info["body"]
            nw = _emitted_width(str(m.get("name") or ""), fs * 1.1) / 2 if m.get("name") else 0
            return min(b.x, -nw), max(b.x + b.width, nw)
        if k == "lipid":
            return -14, 40
        if k == "peripheral":
            r = 16 * float(m.get("size", 1.0))
            return -r, r
        s = max(T, 14.0) / 22.0
        cols = ("#000000",) * 6
        _, _, tb, sh, _, _, _ = _build_synthase(
            T,
            s,
            int(m.get("n_c", 10)),
            cols,
            m.get("labels", True),
            m.get("flow", "synthesis"),
            m.get("rotation", True),
            m.get("proton_path", protons),
            m.get("reaction", ("ADP + Pi", "ATP")),
            fs,
            False,
            _el("defs"),
            None,
            0,
            ion,
        )
        return min(b.x for b in sh + tb), max(b.x + b.width for b in sh + tb)

    fps = [footprint(m) for m in members]
    total = sum(b - a for a, b in fps)
    gap = (x1 - x0 - total) / (len(members) + 1)
    if gap < 6:
        raise ValueError(f"members do not fit in width={W:g}: need about {total + x0 + 6 * (len(members) + 1):.0f}")
    xs, cur = [], x0 + gap
    for a, b in fps:
        xs.append(cur - a)
        cur += (b - a) + gap
    above, below = 30.0, 30.0
    for m, fp in zip(members, fps):
        if m["kind"] == "complex":
            info = _draw_complex(m, 0, 0, T, fs, False, None, _el("defs"), 0)
            above = max(above, -info["body"].y - h + (fs * 1.6 if m.get("pumps") else 0))
            below = max(below, info["body"].y + info["body"].height - h + fs * 1.6)
        elif m["kind"] == "atp_synthase":
            s = max(T, 14.0) / 22.0
            below = max(below, 5 * s + 20 * s + 34 * s * 2 + 16 * s)
            above = max(above, 31 * s)
        elif m["kind"] == "peripheral":
            ext = 26 * float(m.get("size", 1.0)) + fs * 1.3
            if m.get("side", "top") == "top":
                above = max(above, ext)
            else:
                below = max(below, ext + fs * 1.3)
    above += fs * 1.4 + 8
    below += fs * 1.4 + 8
    ym = above + h
    H = ym + h + below
    holder, defs = _el("g"), _el("defs")
    holder.append(defs)
    top_c, bot_c = "#F3EEE4", "#EAF1F7"
    bg_top = Box(0, 0, W, ym - h)
    bg_bot = Box(0, ym + h, W, H - ym - h)
    holder.append(_el("rect", x=0, y=0, width=W, height=H, fill=top_c, data_outline="1"))
    holder.append(_el("rect", x=0, y=ym, width=W, height=H - ym, fill=bot_c))
    look = _look() if rich else None
    shapes = [bg_top, bg_bot]
    texts, boxes = [], []
    built = []
    holes = []
    for i, (m, x) in enumerate(zip(members, xs)):
        k = m["kind"]
        if k == "complex":
            info = _draw_complex(m, x, ym, T, fs, rich, look, defs, seed + i)
            if not protons:
                info["ports"].pop("_pump", None)
            holes.append(info["hole"])
            built.append(dict(kind=k, m=m, x=x, info=info, ports=info["ports"], shapes=info["shapes"], els=info["els"]))
        elif k == "lipid":
            els, tx, tb, sh, ports, hole, box = _carrier_lipid(
                x, ym, T, m.get("name", "Q"), m.get("color", "#F2C14E"), fs
            )
            holes.append((hole[0], hole[0] + 2 * (x - hole[0])))
            built.append(dict(kind=k, m=m, x=x, ports=ports, shapes=sh, els=els, texts=tx, tboxes=tb))
        elif k == "peripheral":
            side = m.get("side", "top")
            els, box, ports, cy, ry = _carrier_peripheral(
                x,
                ym,
                T,
                m.get("name", ""),
                m.get("color", "#D98C3A"),
                fs,
                side,
                seed + i,
                m.get("cofactor"),
                float(m.get("size", 1.0)),
            )
            built.append(dict(kind=k, m=m, x=x, ports=ports, shapes=[box], els=els, cy=cy, side=side))
        else:
            s = max(T, 14.0) / 22.0
            opts = {
                kk: v
                for kk, v in m.items()
                if kk in ("n_c", "labels", "flow", "rotation", "proton_path", "reaction", "colors")
            }
            opts.setdefault("proton_path", protons)
            cols = tuple(opts.get("colors") or ("#C9A23A", "#3F7FBF", "#6E6E8E", "#D9785A", "#6B8FCB", "#C46B9E"))
            els, tx, tb, sh, ports, ext, nuc = _build_synthase(
                T,
                s,
                int(opts.get("n_c", 10)),
                cols,
                opts.get("labels", True),
                opts.get("flow", "synthesis"),
                opts.get("rotation", True),
                opts["proton_path"],
                opts.get("reaction", ("ADP + Pi", "ATP")),
                fs,
                rich,
                defs,
                None,
                seed + i,
                ion,
            )
            g = _el("g", transform=f"translate({fmt(x)} {fmt(ym)})")
            g.extend(els)
            g.append(nuc)
            g.extend(tx)
            mv = lambda b: Box(b.x + x, b.y + ym, b.width, b.height)
            holes.append((x - 28 * s - 1, x + 28 * s + 23 * s))
            built.append(
                dict(
                    kind=k,
                    m=m,
                    x=x,
                    ports={kk: (px + x, py + ym) for kk, (px, py) in ports.items()},
                    shapes=[mv(b) for b in sh],
                    els=[g],
                    tboxes=[mv(b) for b in tb],
                )
            )
    for b in built:
        shapes.extend(b["shapes"])
        boxes.extend(b.get("tboxes", []))
    band_boxes = []
    for j, (a, b) in enumerate(_segments(0, W, holes)):
        if membrane == "bilayer":
            band, grp, _ = _bilayer_strip(a, b, ym, T, membrane_color, rich, seed + j)
            holder.append(band)
            holder.append(_wrap_look(grp) if rich else grp)
        else:
            holder.append(_el("rect", x=a, y=ym - h, width=b - a, height=T, fill=_mix(membrane_color, "#FFFFFF", 0.45)))
        band_boxes.append(Box(a, ym - T * 0.39, b - a, T * 0.78))
    shapes.extend(band_boxes)
    for b in built:
        holder.extend(b["els"])
    if look is not None and len(look):
        holder.append(look)
    for b in built:
        if b["kind"] == "complex":
            holder.extend(_cofactor_marks(b["info"], fs, texts, boxes, b["m"].get("cofactor_labels", False)))
        holder.extend(b.get("texts", []))
    chain = [i for i, b in enumerate(built) if b["kind"] != "atp_synthase" and b["m"].get("e", True)]
    names = {str(b["m"].get("name")): i for i, b in enumerate(built) if b["m"].get("name")}
    hops = []
    if electron_path:
        for n, i in enumerate(chain):
            tgt = built[i]["m"].get("to")
            nxt = [c for c in chain[n + 1 :] if built[c]["m"].get("to") is None]
            j = names.get(str(tgt)) if tgt is not None else (nxt[0] if nxt else None)
            if j is None or j == i:
                continue
            hops.append((i, j))
    hop_pts = []
    ecol = _ELECTRON

    def rim(k, toward):
        b = built[k]
        if b["kind"] not in ("lipid", "peripheral"):
            return None
        bx = b["shapes"][0]
        cx, cy = bx.x + bx.width / 2, bx.y + bx.height / 2
        sx = 1 if toward[0] > cx else -1
        return (cx + sx * (bx.width / 2 + 1.5), cy)

    for i, j in hops:
        p, q = built[i]["ports"]["e_out"], built[j]["ports"]["e_in"]
        p = rim(i, q) or p
        q = rim(j, p) or q
        mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
        avg = my - ym
        dx = abs(q[0] - p[0])
        bulge = max(8.0, dx * 0.16)
        sg = -1 if avg < -h else 1 if avg > h else (1 if q[1] >= p[1] else -1)
        c = (mx, my + sg * bulge)
        between = [b for k, b in enumerate(built) if min(i, j) < k < max(i, j)]
        if (
            between
        ):  # hop over intermediate members (a branch skipping a neighbour): arc clears their bodies on the top side
            tops = [min(sb.y for sb in b["shapes"]) for b in between]
            peak = min(tops) - 10
            c = (mx, 2 * peak - (p[1] + q[1]) / 2)
        pts = [
            (
                (1 - t) ** 2 * p[0] + 2 * (1 - t) * t * c[0] + t * t * q[0],
                (1 - t) ** 2 * p[1] + 2 * (1 - t) * t * c[1] + t * t * q[1],
            )
            for t in [k / 12 for k in range(13)]
        ]
        hop_pts.append(pts)
    # internal paths through each complex's cofactors (thin, no head)
    inner = []
    for i in chain:
        b = built[i]
        if b["kind"] != "complex":
            continue
        pts = [b["ports"]["e_in"]] + [pt for _, pt in b["info"]["cof"]] + [b["ports"]["e_out"]]
        if len(pts) >= 2 and math.dist(pts[0], pts[-1]) > 4:
            inner.append(pts)
    dense = []
    for pts in inner:
        for (ax, ay), (bx_, by_) in zip(pts, pts[1:]):
            n = max(1, int(math.dist((ax, ay), (bx_, by_)) / 4))
            dense += [(ax + (bx_ - ax) * k / n, ay + (by_ - ay) * k / n) for k in range(n + 1)]
    obst = [Box(x - 2, y - 2, 4, 4) for pts in hop_pts + [dense] for x, y in pts]
    for b in built:
        if b["kind"] == "complex":
            if b["info"]["ports"].get("_pump"):
                holder.extend(_draw_pump(b["info"], fs, texts, boxes, shapes))
                b["ports"] = b["info"]["ports"]
            _name_in_lobe_safe(b["info"], fs, texts, boxes, shapes + obst)
        elif b["kind"] == "peripheral":
            nm = b["m"].get("name")
            if nm:
                bx = b["shapes"][0]
                y = bx.y - 4 if b["side"] == "top" else bx.y + bx.height + fs + 2
                _place(
                    [
                        ((b["x"], y), "middle"),
                        ((bx.x - 3, b["cy"] + fs * 0.35), "end"),
                        ((bx.x + bx.width + 3, b["cy"] + fs * 0.35), "start"),
                    ],
                    nm,
                    fs,
                    _mix(b["m"].get("color", "#D98C3A"), "#000000", 0.5),
                    shapes,
                    boxes,
                    texts,
                    avoid=obst,
                )
    for nm, y in ((top_name, (ym - h) / 2 + fs * 0.35), (bot_name, ym + h + (H - ym - h) / 2 + fs * 0.35)):
        if nm:
            _place(
                [((6, y), "start"), ((6, y - fs * 1.4), "start"), ((6, y + fs * 1.4), "start")],
                nm,
                fs * 1.05,
                _INK,
                shapes,
                boxes,
                texts,
                avoid=obst,
            )

    # reactions at electron entry / terminal exit (on the side the site sits on)
    def react(i, pt, txt, prefer_left):
        bb = built[i].get("info", {}).get("body") if built[i]["kind"] == "complex" else built[i]["shapes"][0]
        side_top = pt[1] < ym
        far = (bb.y - 6 if side_top else bb.y + bb.height + fs + 4) if bb else pt[1]
        step = -fs * 1.3 if side_top else fs * 1.3
        rows = [pt[1] + fs * 0.35, far, far + step, far + 2 * step]
        lx, rx = (bb.x - 6, bb.x + bb.width + 6) if bb else (pt[0] - 8, pt[0] + 8)
        ew = _emitted_width(str(txt), fs)
        cands = [
            ((pt[0] + k * ew / 4, yy), "middle")
            for yy in (far, far + step)
            for k in ((0, -1, 1, -2, 2) if prefer_left else (0, 1, -1, 2, -2))
        ]
        for yy in rows:
            lr = [((lx, yy), "end"), ((rx, yy), "start")]
            cands += lr if prefer_left else lr[::-1]
        return _place(cands, txt, fs, "#5A4630", shapes, boxes, texts, avoid=obst)

    for n, b in enumerate(built):
        if b["m"].get("reaction") and b["kind"] != "atp_synthase":
            react(n, b["ports"]["e_in"], b["m"]["reaction"], True)
    if terminal and chain:
        react(chain[-1], built[chain[-1]]["ports"]["e_out"], terminal, False)
    # electron arrows drawn last among shapes so they read on top of proteins
    for pts in inner:
        holder.append(
            _el(
                "path",
                d=_smooth(pts) if len(pts) > 2 else _poly(pts, closed=False),
                fill="none",
                stroke=ecol,
                stroke_width=1.4,
                stroke_dasharray="3 2.5",
                stroke_linecap="round",
            )
        )
    for pts in hop_pts:
        holder.append(
            _el(
                "path",
                d=_smooth(pts),
                fill="none",
                stroke="#FFFFFF",
                stroke_width=4.6,
                stroke_linecap="round",
                stroke_opacity=0.8,
            )
        )
        holder.extend(_arrow(pts, ecol, 2.0))
    if hop_pts and electron_label:
        pts = hop_pts[0]
        mx, my = pts[6]
        _place(
            [((mx, my - 6), "middle"), ((mx, my + fs + 4), "middle"), ((mx + 6, my + fs * 0.35), "start")],
            electron_label,
            fs,
            ecol,
            shapes,
            boxes,
            texts,
            avoid=obst,
        )
    if gradient:
        rr = _ion_r(str(ion), max(10.0, fs * 0.85))

        def scatter(n, y0, y1, k0):
            placed = 0
            for k in range(n * 12):
                if placed >= n:
                    break
                fx = (k * 0.618 + k0) % 1
                fy = (k * 0.382 + 0.5 * k0) % 1
                cx, cy = x0 + rr + fx * (x1 - x0 - 2 * rr), y0 + rr + fy * max(1, (y1 - y0 - 2 * rr))
                bb = Box(cx - rr, cy - rr, 2 * rr, 2 * rr)
                if _hits(bb, boxes + obst, 3) or any(_hits(bb, [s], 3) for s in shapes[2:]):
                    continue
                g = ion_marker(ion, font_size=max(10.0, fs * 0.85)).element
                g.set("transform", f"translate({fmt(cx)} {fmt(cy)})")
                holder.append(g)
                boxes.append(bb)
                placed += 1

        scatter(int(gradient), fs * 1.6, ym - h - 4, 0.13)
        scatter(max(1, int(gradient) // 3), ym + h + 4, H - fs * 1.6, 0.41)
    holder.extend(texts)
    ports = {
        "top_side": (W / 2, (ym - h) / 2),
        "bottom_side": (W / 2, ym + h + (H - ym - h) / 2),
        "membrane": (W / 2, ym),
    }
    for i, b in enumerate(built):
        bb = b["shapes"][0] if b["kind"] != "complex" else b["info"]["body"]
        if b["kind"] == "atp_synthase":
            bb = Box(min(s.x for s in b["shapes"]), min(s.y for s in b["shapes"]), 0, 0)
            bb = Box(
                bb.x,
                bb.y,
                max(s.x + s.width for s in b["shapes"]) - bb.x,
                max(s.y + s.height for s in b["shapes"]) - bb.y,
            )
        own = {"": (b["x"], ym), "_top": (b["x"], bb.y), "_bottom": (b["x"], bb.y + bb.height)}
        for k in ("e_in", "e_out", "in", "out", "f1", "proton_in", "proton_out"):
            if k in b["ports"]:
                own["_" + k] = b["ports"][k]
        for suf, pt in own.items():
            ports[f"m{i}{suf}"] = pt
            nm = b["m"].get("name")
            if nm:
                ports[f"{nm}{suf}"] = pt
    return _finish(holder, defs, Box(0, 0, W, H), **ports)


def _wrap_look(grp):
    lk = _look()
    lk.append(grp)
    return lk


def _name_in_lobe_safe(info, fs, texts, boxes, obstacles):
    """Complex name inside its largest lobe (white) when it fits there clear of the electron path, else below the body."""
    name = info["name"]
    if not name:
        return
    x0, ym = info["x0"], info["ym"]
    big = fs * 1.1
    need = _emitted_width(str(name), big)
    for cx, cy, rx, ry, rot, sh in sorted(info["lobes"], key=lambda l: -l[2] * l[3]):
        if need < rx * 1.45 and big * 1.3 < ry * 1.5:
            for dy in (0, ry * 0.35, -ry * 0.35):
                t, b = _text(x0 + cx, ym + cy + dy + big * 0.35, name, big, "#FFFFFF")
                eb = Box(x0 + cx - need / 2, b.y, need, b.height)
                if not _hits(eb, boxes + [o for o in obstacles if o.width < 6], 1):
                    texts.append(t)
                    boxes.append(eb)
                    return
    body = info["body"]
    _place(
        [((x0, body.y + body.height + big + 2), "middle"), ((x0, body.y - 5), "middle")],
        name,
        big,
        _mix(info["color"], "#000000", 0.45),
        [o for o in obstacles if o.width >= 6],
        boxes,
        texts,
        avoid=[o for o in obstacles if o.width < 6],
    )
