"""Band / energy-level diagrams drawn like review-paper figures."""

from __future__ import annotations

import math

from ..atomize_svg_to_slide._geometry import fmt
from ._bio_parts import _el, _look, _mix
from ._device_parts import _dark, _finish, _head, _linear, _start, _text
from ._geometry import Box, _finite, _union, label
from ._help import _drawing_api
from ._parts import _INK

_E_COLOR, _H_COLOR, _PHOTON = "#1F3A68", "#B23A48", "#E09A12"
_TRANSFERS = (None, "type2", "z", "s")
_VACUUM_NHE = -4.44


def _width(s, fs, weight="normal"):
    return label(str(s), font_size=fs, font_weight=weight).bounds.width


def _nice_step(span):
    for step in (0.1, 0.2, 0.25, 0.5, 1, 2, 5):
        if span / step <= 8:
            return step
    return 10.0


def _fmt_v(v, step=0.01):
    digits = 0 if step >= 1 else 1 if step >= 0.1 else 2
    s = f"{v:.{digits}f}"
    return "0" if float(s) == 0 else s.replace("-", "−")


def _curve(x0, y0, x1, y1, bow, color, width=1.8, dashed=False):
    """Quadratic arrow from (x0, y0) to (x1, y1), bowing ``bow`` px to the left of travel."""
    dx, dy = x1 - x0, y1 - y0
    n = math.hypot(dx, dy) or 1
    cx, cy = (x0 + x1) / 2 + dy / n * bow, (y0 + y1) / 2 - dx / n * bow
    size = 8.5
    tx, ty = x1 - cx, y1 - cy
    tn = math.hypot(tx, ty) or 1
    ex, ey = x1 - tx / tn * size * 0.8, y1 - ty / tn * size * 0.8
    line = _el(
        "path",
        d=f"M{fmt(x0)} {fmt(y0)} Q{fmt(cx)} {fmt(cy)} {fmt(ex)} {fmt(ey)}",
        fill="none",
        stroke=color,
        stroke_width=width,
        stroke_dasharray="5 3.5" if dashed else None,
        stroke_linecap="round",
    )
    return [line, _head(x1, y1, tx, ty, size, color)], Box(
        min(x0, x1, cx), min(y0, y1, cy), abs(x1 - x0) + abs(bow) + 1, abs(y1 - y0) + abs(bow) + 1
    )


def _carrier(x, y, r, electron):
    g = _el("g")
    if electron:
        g.append(_el("circle", cx=x, cy=y, r=r, fill=_E_COLOR, stroke="#FFFFFF", stroke_width=0.8))
        g.append(_el("path", d=f"M{fmt(x - r * 0.5)} {fmt(y)} H{fmt(x + r * 0.5)}", stroke="#FFFFFF", stroke_width=1.6))
    else:
        g.append(_el("circle", cx=x, cy=y, r=r, fill="#FFFFFF", stroke=_H_COLOR, stroke_width=1.6))
        g.append(
            _el(
                "path",
                d=f"M{fmt(x - r * 0.5)} {fmt(y)} H{fmt(x + r * 0.5)} M{fmt(x)} {fmt(y - r * 0.5)} V{fmt(y + r * 0.5)}",
                stroke=_H_COLOR,
                stroke_width=1.6,
            )
        )
    return g


def _sign(x, y, s, plus, color):
    d = f"M{fmt(x - s)} {fmt(y)} H{fmt(x + s)}" + (f" M{fmt(x)} {fmt(y - s)} V{fmt(y + s)}" if plus else "")
    return _el("path", d=d, stroke=color, stroke_width=1.5, fill="none")


def _photon(x0, x1, y, fs):
    """Wavy hν arrow along y from x0 towards x1; returns (elements, boxes)."""
    sgn = 1 if x1 > x0 else -1
    end = x1 - sgn * 8
    n, amp = 24, 4.0
    pts = [(x0 + (end - x0) * i / n, y + amp * math.sin(i / n * 3 * 2 * math.pi)) for i in range(n + 1)]
    d = "M" + " L".join(f"{fmt(px)} {fmt(py)}" for px, py in pts)
    els = [
        _el("path", d=d, fill="none", stroke=_PHOTON, stroke_width=2, stroke_linejoin="round"),
        _head(x1, y, sgn, 0, 9, _PHOTON),
    ]
    t, b = _text((x0 + x1) / 2, y - amp - 5, "hν", fs, fill=_mix(_PHOTON, "#000000", 0.3), weight="bold")
    return els + [t], [Box(min(x0, x1), y - amp - 1, abs(x1 - x0), 2 * amp + 2), b]


@_drawing_api(
    "parts",
    purpose="能带/能级图（半导体能带排列、异质结、肖特基结、光催化/光伏/LED 的 CB/VB、Eg、E_F、参比电位）：期刊风格，CB/VB 色块、界面能带弯曲与空间电荷、e⁻/h⁺ 画在带边上、hν、type-II/Z/S 型电荷转移与表面反应。",
    returns='Geometry（原点在中心；端口 "名称.cb"/"名称.vb"（带边中点）、"名称.ef"、"名称.top"/"名称.bottom"、ref{i}（参比线右端）、interface{i}）',
    semantics=(
        'materials 自左向右：半导体 {"name", "cb", "vb", "color"}，可加 "ef"（费米能级）、"cb_text"/"vb_text"（该带上的表面反应，如 "O₂→•O₂⁻"）；'
        '金属 {"name", "ef", "color"}（无 cb/vb，画到 E_F 的电子海）。数值单位随 axis。',
        'axis="NHE"：电位 V vs NHE，正值向下；axis="vacuum"：能量 eV（相对真空能级，负值）。axis_label 可改纵轴标题。',
        'ref_levels=[("H⁺/H₂", 0), ("O₂/H₂O", 1.23)] 画贯穿虚线并在右侧标注；vacuum=True 加真空能级与各 E_F 的功函数 φ 箭头。',
        "contact=False 为接触前（材料间留空）；True 为接触后：按两侧 E_F 高低画界面能带弯曲（给电子侧上弯带 +，受电子侧下弯带 −）与内建电场 E。未给 ef 的半导体按 n 型估计。",
        'transfer="type2"（e⁻ 顺 CB 下行、h⁺ 沿 VB 上行；与金属相邻时 e⁻ 流向金属）/"z"/"s"（还原端 VB 的 h⁺ 与氧化端 CB 的 e⁻ 复合；"s" 自动 contact=True）；'
        'carriers/light 控制带边载流子与 hν；另画的载流子/标记要压在带边上时加 data_on_edge="1"（如 d.ellipse_at(p, r=6, data_on_edge="1")），check() 不报压线。',
    ),
    example='ed = d.place(energy_diagram([{"name": "A", "cb": -0.5, "vb": 2.7, "color": "#4A7EBB", "vb_text": "氧化"}, {"name": "B", "cb": -1.1, '
    '"vb": 1.6, "color": "#D9822B", "cb_text": "还原"}],\n    ref_levels=[("H⁺/H₂", 0), ("O₂/H₂O", 1.23)], transfer="s"), at=(480, 280), key="bands")\n'
    'd.callout("c", "表面复合位点", ed.port("B.vb"), at=(700, 470), font_size=13)',
    rank=7,
)
def energy_diagram(
    materials,
    *,
    ref_levels=(),
    axis="NHE",
    axis_label=None,
    contact=None,
    transfer=None,
    carriers=True,
    light=True,
    vacuum=False,
    values=True,
    band_width=120,
    gap=None,
    height=300,
    font_size=13,
    style="rich",
):
    _finite(band_width, height, font_size)
    if axis not in ("NHE", "vacuum"):
        raise ValueError('axis must be "NHE" or "vacuum"')
    if transfer not in _TRANSFERS:
        raise ValueError(f"transfer must be one of {_TRANSFERS}")
    if style not in ("rich", "flat"):
        raise ValueError('style must be "rich" or "flat"')
    if not materials:
        raise ValueError("materials must not be empty")
    mats = []
    for m in materials:
        if "name" not in m:
            raise ValueError('each material needs a "name"')
        metal = "cb" not in m and "vb" not in m
        if metal and "ef" not in m:
            raise ValueError(f'material {m["name"]!r}: give "cb" and "vb" (semiconductor) or "ef" (metal)')
        if not metal and ("cb" not in m or "vb" not in m):
            raise ValueError(f'material {m["name"]!r}: a semiconductor needs both "cb" and "vb"')
        mats.append(dict(m, metal=metal))
    contact = transfer == "s" if contact is None else bool(contact)
    rich, fs, w, T = style == "rich", font_size, float(band_width), max(26.0, font_size * 2.2)
    u = (lambda v: v) if axis == "NHE" else (lambda v: -v)  # u grows downward (lower electron energy)

    def ef_of(m):  # metals: given; semiconductors: given, else n-type estimate near the CB
        return m["ef"] if "ef" in m else m["cb"] + 0.3 * (m["vb"] - m["cb"])

    vac = _VACUUM_NHE if axis == "NHE" else 0.0
    vals = (
        [m[k] for m in mats for k in ("cb", "vb", "ef") if k in m]
        + [v for _, v in ref_levels]
        + ([vac] if vacuum else [])
    )
    us = [u(v) for v in vals]
    span = max(max(us) - min(us), 0.5)
    k = height / span
    step = _nice_step(span + 2 * (T + 12) / k)
    u_top = math.floor((min(us) - (T + fs + 10) / k) / step) * step
    u_bot = math.ceil((max(us) + (T + fs * 2.2) / k) / step) * step
    Y = lambda v: (u(v) - u_top) * k
    plot_h = (u_bot - u_top) * k

    n = len(mats)
    gap = (0.0 if contact else (64.0 if transfer else 36.0)) if gap is None else float(gap)
    if contact:
        gap = 0.0
    side_of = lambda i: ("left" if i == 0 else "right" if i == n - 1 else "top") if n > 1 else "left"
    react_side = lambda i: "right" if n == 1 else side_of(i)

    def zone(side):
        need = 0.0
        for i, m in enumerate(mats):
            if m["metal"]:
                continue
            if light and side_of(i) == side:
                need = max(need, 54.0)
            if react_side(i) == side:
                need = max([need] + [_width(m[t], fs) + 26 for t in ("cb_text", "vb_text") if m.get(t)])
        return need + 14

    x_mat0 = zone("left")
    xs = [x_mat0 + i * (w + gap) for i in range(n)]
    x_right = xs[-1] + w
    plot_r = x_right + zone("right")

    bends = [[] for _ in mats]  # (interface x, amplitude, depth)
    charges = []  # (interface x, donor index, acceptor index)
    if contact:
        for i in range(n - 1):
            a, b = mats[i], mats[i + 1]
            du = u(ef_of(a)) - u(ef_of(b))  # >0: b has the higher Fermi level → b donates electrons
            if abs(du) < 1e-9:
                continue
            donor, acceptor = (i + 1, i) if du > 0 else (i, i + 1)
            amp = min(26.0, max(10.0, abs(du) * k * 0.45))
            xi = xs[i + 1]
            for j, s in ((donor, -1), (acceptor, 1)):
                if not mats[j]["metal"]:
                    bends[j].append((xi, s * amp, w * 0.45))
            charges.append((xi, donor, acceptor))

    def off(j, x):
        o = 0.0
        for xi, amp, depth in bends[j]:
            d = abs(x - xi)
            if d < depth:
                o += amp * (1 - d / depth) ** 2
        return o

    def edge(j, v, x):
        return Y(v) + off(j, x)

    holder, defs = _start()
    refs, slabs, look, marks, texts, top = [], [], [], [], [], []
    boxes = [Box(0, 0, plot_r, plot_h)]
    tboxes = []
    ports = {}

    def put(x, y, s, size=fs, layer=texts, **kw):
        t, b = _text(x, y, s, size, **kw)
        layer.append(t)
        tboxes.append(b)
        boxes.append(b)
        return b

    def strip(j, v, x0, x1, dy):
        """Closed band slab between the (bent) edge at value v and the same curve shifted by dy."""
        N = 24
        e = [(x0 + (x1 - x0) * t / N, edge(j, v, x0 + (x1 - x0) * t / N)) for t in range(N + 1)]
        pts = e + [(x, y + dy) for x, y in reversed(e)]
        return "M" + " L".join(f"{fmt(x)} {fmt(y)}" for x, y in pts) + " Z", e

    ref_ys = [Y(v) for _, v in ref_levels] + ([Y(vac)] if vacuum else [])

    def clear_y(y0, y1):
        """Height nearest the middle of [y0, y1] that keeps a label clear of the reference lines."""
        mid = (y0 + y1) / 2
        if y1 <= y0:
            return mid
        options = [y0 + (y1 - y0) * t / 24 for t in range(25)]
        free = [y for y in options if all(abs(y - r) > fs * 1.1 for r in ref_ys)]
        return min(free or options, key=lambda y: abs(y - mid))

    carrier_at = {}
    r = max(6.0, fs * 0.5)
    for j, m in enumerate(mats):
        x0, x1 = xs[j], xs[j] + w
        color = m.get("color", "#7E8C9A")
        line = _mix(color, "#000000", 0.35)
        name_y = 0.0
        if m["metal"]:
            ye = Y(m["ef"])
            depth = max(2 * T, plot_h - ye - fs * 2.4)
            slabs.append(
                _el(
                    "rect",
                    x=x0,
                    y=ye,
                    width=w,
                    height=depth,
                    fill=_mix(color, "#FFFFFF", 0.1),
                    stroke=line,
                    stroke_width=1,
                )
            )
            if rich:
                gid = f"ed_metal{j}"
                defs.append(
                    _linear(gid, [(0, "#FFFFFF", 0.55), (0.4, "#FFFFFF", 0.05), (1, "#000000", 0.18)], x2=1, y2=0)
                )
                look.append(_el("rect", x=x0, y=ye, width=w, height=depth, fill=f"url(#{gid})"))
            slabs.append(_el("path", d=f"M{fmt(x0)} {fmt(ye)} H{fmt(x1)}", stroke=_INK, stroke_width=2))
            put(x0 + 6, ye + fs * 1.3, "E", fill="#FFFFFF" if _dark(color) else _INK, anchor="start", weight="bold")
            texts[-1].append(_el("tspan", font_size=fmt(fs * 0.72)))
            texts[-1][-1].text = "F"
            ports[f"{m['name']}.ef"] = ((x0 + x1) / 2, ye)
            name_y = ye + depth
            ports[f"{m['name']}.top"] = ((x0 + x1) / 2, ye)
        else:
            dark_text = _dark(color)
            for band, v, dy in (("cb", m["cb"], -T), ("vb", m["vb"], T)):
                d, e = strip(j, v, x0, x1, dy)
                slabs.append(_el("path", d=d, fill=_mix(color, "#FFFFFF", 0.08), stroke=line, stroke_width=0.9))
                slabs.append(
                    _el(
                        "path",
                        d="M" + " L".join(f"{fmt(x)} {fmt(y)}" for x, y in e),
                        fill="none",
                        stroke=line,
                        stroke_width=1.8,
                    )
                )
                if rich:
                    gid = f"ed_{band}{j}"
                    out = 0 if band == "cb" else 1  # lighter away from the gap
                    defs.append(_linear(gid, [(out, "#FFFFFF", 0.45), (1 - out, "#FFFFFF", 0.0)]))
                    look.append(_el("path", d=d, fill=f"url(#{gid})"))
                mid = (x0 + x1) / 2
                ports[f"{m['name']}.{band}"] = (mid, edge(j, v, mid))
                tc = "#FFFFFF" if dark_text else _INK
                name_w, val_s = _width(band.upper(), fs, "bold"), _fmt_v(v)
                val_w = _width(val_s, fs * 0.85)
                bent_l = any(abs(xi - x0) < 1 for xi, _, _ in bends[j])
                bent_r = any(abs(xi - x1) < 1 for xi, _, _ in bends[j])
                if bent_l and not bent_r:  # keep both labels on the flat part of the slab
                    xv, xn = x1 - 7, x1 - 15 - val_w - name_w
                elif bent_r and not bent_l:
                    xn, xv = x0 + 7, x0 + 15 + name_w + val_w
                else:
                    xn, xv = x0 + 7, x1 - 7
                sgn = -1 if band == "cb" else 1
                at = lambda x: edge(j, v, x) + sgn * T / 2 + fs * 0.36
                put(xn, at(xn + name_w / 2), band.upper(), fill=tc, anchor="start", weight="bold")
                if values:
                    put(xv, at(xv - val_w / 2), val_s, size=fs * 0.85, fill=tc, anchor="end")
            # Eg on the outer side of the gap, label towards the middle
            outer_left = side_of(j) != "right"
            ex = x0 + w * (0.16 if outer_left else 0.84)
            yc, yv = edge(j, m["cb"], ex), edge(j, m["vb"], ex)
            if yv - yc > 18:
                marks.append(_el("path", d=f"M{fmt(ex)} {fmt(yc + 8)} V{fmt(yv - 8)}", stroke=_INK, stroke_width=1.1))
                marks.append(_head(ex, yc + 1, 0, -1, 7, _INK))
                marks.append(_head(ex, yv - 1, 0, 1, 7, _INK))
            eg = abs(m["vb"] - m["cb"])
            put(
                ex + (6 if outer_left else -6),
                clear_y(yc + fs, yv - fs) + fs * 0.36,
                f"{eg:.2f} eV",
                size=fs * 0.92,
                fill=_INK,
                anchor="start" if outer_left else "end",
            )
            if "ef" in m and not (contact and bends[j]):  # after contact the separate E_F no longer holds
                ye = [(x, edge(j, m["ef"], x)) for x in (x0 + w * t / 12 for t in range(13))]
                marks.append(
                    _el(
                        "path",
                        d="M" + " L".join(f"{fmt(x)} {fmt(y)}" for x, y in ye),
                        fill="none",
                        stroke=_INK,
                        stroke_width=1.1,
                        stroke_dasharray="4 3",
                    )
                )
                ports[f"{m['name']}.ef"] = ((x0 + x1) / 2, edge(j, m["ef"], (x0 + x1) / 2))
            # carriers sit on the band edges, crowded towards the side that exchanges them
            if carriers:
                fr = (0.42, 0.6, 0.78) if side_of(j) in ("left", "top") else (0.22, 0.4, 0.58)
                if n == 1:
                    fr = (0.4, 0.58, 0.76)
                for band, v, electron in (("cb", m["cb"], True), ("vb", m["vb"], False)):
                    pts = [(x0 + w * f, edge(j, v, x0 + w * f)) for f in fr]
                    for px, py in pts:
                        top.append(_carrier(px, py, r, electron))
                    carrier_at[(j, band)] = pts
            name_y = max(edge(j, m["vb"], x) for x in (x0, (x0 + x1) / 2, x1)) + T
            ports[f"{m['name']}.top"] = ((x0 + x1) / 2, min(edge(j, m["cb"], x) for x in (x0, x1)) - T)
            yc0, yv0 = Y(m["cb"]), Y(m["vb"])
            if light and side_of(j) in ("left", "right"):
                if side_of(j) == "left":
                    els, bs = _photon(x0 - 52, x0 - 4, clear_y(yc0 + fs * 1.6, yv0 - 8), fs)
                else:
                    els, bs = _photon(x1 + 52, x1 + 4, clear_y(yc0 + fs * 1.6, yv0 - 8), fs)
                marks.extend(els)
                boxes.extend(bs)
                tboxes.extend(bs)
            for band, yv_, key in (("cb", yc0 - T / 2, "cb_text"), ("vb", yv0 + T / 2, "vb_text")):
                s = m.get(key)
                if not s:
                    continue
                sd = react_side(j)
                if sd == "top":
                    yy = (yc0 - T - 8) if band == "cb" else (yv0 + T + fs + 4)
                    put((x0 + x1) / 2, yy, s, anchor="middle", fill=_INK)
                    continue
                ex0 = x0 if sd == "left" else x1
                sg = -1 if sd == "left" else 1
                yy = edge(j, m[band], ex0) + (-T / 2 if band == "cb" else T / 2)
                marks.append(
                    _el(
                        "path", d=f"M{fmt(ex0 + sg * 3)} {fmt(yy)} H{fmt(ex0 + sg * 14)}", stroke=_INK, stroke_width=1.2
                    )
                )
                marks.append(_head(ex0 + sg * 20, yy, sg, 0, 7, _INK))
                put(ex0 + sg * 23, yy + fs * 0.36, s, anchor="end" if sd == "left" else "start", fill=_INK)
        put((x0 + x1) / 2, name_y + fs * 1.35, m["name"], size=fs * 1.08, fill=_INK, weight="bold")
        ports[f"{m['name']}.bottom"] = ((x0 + x1) / 2, name_y + fs * 1.6)

    for idx, (xi, donor, acceptor) in enumerate(charges):
        semis = [j for j in (donor, acceptor) if not mats[j]["metal"]]
        gaps = [(edge(j, mats[j]["cb"], xi), edge(j, mats[j]["vb"], xi)) for j in semis]
        lo, hi = max(g[0] for g in gaps), min(g[1] for g in gaps)
        if hi - lo < 4 * fs:
            lo, hi = min(g[0] for g in gaps), max(g[1] for g in gaps)
        yf = (lo + hi) / 2
        s = max(min(hi - lo, 120) * 0.26, fs * 2)
        for j, plus, color in ((donor, True, _H_COLOR), (acceptor, False, _E_COLOR)):
            sg = 1 if xs[j] >= xi - 1e-6 else -1
            cols = (0.05,) if mats[j]["metal"] else (0.1, 0.2)
            for c in cols:
                for dy in (-s, s):
                    marks.append(_sign(xi + sg * w * c, yf + dy, 3.6, plus, color))
        sd = 1 if xs[acceptor] > xs[donor] else -1
        a0, a1 = xi - sd * w * 0.28, xi + sd * w * 0.28
        marks.append(_el("path", d=f"M{fmt(a0)} {fmt(yf)} H{fmt(a1 - sd * 7)}", stroke=_INK, stroke_width=1.6))
        marks.append(_head(a1, yf, sd, 0, 8, _INK))
        put(xi, yf - 5, "E", size=fs * 0.95, fill=_INK, weight="bold")
        ports[f"interface{idx}"] = (xi, yf)

    arrows = []
    for i in range(n - 1):
        a, b = mats[i], mats[i + 1]
        if transfer is None or (not carriers and transfer != "type2"):
            continue
        if a["metal"] and b["metal"]:
            continue
        if a["metal"] or b["metal"]:
            s, mj = (i + 1, i) if a["metal"] else (i, i + 1)
            if transfer == "type2" and (s, "cb") in carrier_at and u(mats[s]["cb"]) < u(mats[mj]["ef"]):
                px, py = carrier_at[(s, "cb")][0 if s > mj else -1]
                tx = xs[mj] + (w * 0.75 if mj < s else w * 0.25)
                arrows.append(
                    _curve(
                        px + (r + 2) * (1 if tx > px else -1),
                        py,
                        tx,
                        Y(mats[mj]["ef"]) - 2,
                        22 if tx > px else -22,
                        _E_COLOR,
                    )
                )
            continue
        if (i, "cb") not in carrier_at or (i + 1, "cb") not in carrier_at:
            continue
        inner = lambda j, band: carrier_at[(j, band)][-1 if j == i else 0]
        if transfer == "type2":
            for band, color, downhill in (("cb", _E_COLOR, True), ("vb", _H_COLOR, False)):
                ua, ub = u(a[band]), u(b[band])
                if abs(ua - ub) < 1e-9:
                    continue
                src, dst = (i, i + 1) if (ua < ub) == downhill else (i + 1, i)
                (sx, sy), (tx, ty) = inner(src, band), inner(dst, band)
                sg = 1 if tx > sx else -1
                bow = (1 if band == "cb" else -1) * sg * 16
                arrows.append(_curve(sx + sg * (r + 2), sy, tx - sg * (r + 3), ty, bow, color))
        else:
            rp, op = (i, i + 1) if u(a["cb"]) < u(b["cb"]) else (i + 1, i)
            (sx, sy), (tx, ty) = inner(op, "cb"), inner(rp, "vb")
            sg = 1 if tx > sx else -1
            ang = math.atan2(ty - sy, tx - sx)
            arrows.append(
                _curve(
                    sx + math.cos(ang) * (r + 2),
                    sy + math.sin(ang) * (r + 2),
                    tx - math.cos(ang) * (r + 3),
                    ty - math.sin(ang) * (r + 3),
                    sg * 18,
                    "#5A4E7C",
                    2,
                    True,
                )
            )
    for els, b in arrows:
        marks.extend(els)
        boxes.append(b)

    if vacuum:
        yv = Y(vac)
        refs.append(_el("path", d=f"M0 {fmt(yv)} H{fmt(plot_r)}", stroke=_INK, stroke_width=1.2))
        for j, m in enumerate(mats):
            if "ef" not in m or (contact and bends[j]):
                continue
            x = xs[j] + w * (0.5 if m["metal"] or not carriers else 0.3 if side_of(j) != "right" else 0.7)
            ye = edge(j, m["ef"], x)
            marks.append(_el("path", d=f"M{fmt(x)} {fmt(yv + 7)} V{fmt(ye - 7)}", stroke=_INK, stroke_width=1.1))
            marks.append(_head(x, yv + 1, 0, -1, 7, _INK))
            marks.append(_head(x, ye - 1, 0, 1, 7, _INK))
            put(
                x + 5,
                min(yv + fs * 1.4, (yv + ye) / 2),
                f"φ {abs(u(m['ef']) - u(vac)):.2f} eV",
                size=fs * 0.9,
                fill=_INK,
                anchor="start",
            )

    lab = [(Y(v), s) for s, v in ref_levels] + ([(Y(vac), "E_vac")] if vacuum else [])
    order = sorted(range(len(lab)), key=lambda q: lab[q][0])
    placed = {}
    last = -1e9
    for q in order:
        yy = max(lab[q][0], last + fs * 1.25)
        placed[q] = yy
        last = yy
    for q, (yy, s) in enumerate(lab):
        free = [(0.0, plot_r)]
        for b in tboxes:  # break the line around labels it would cross
            if b.y - 2 <= yy <= b.y + b.height + 2:
                nxt = []
                for f0, f1 in free:
                    if b.x - 3 > f0:
                        nxt.append((f0, min(f1, b.x - 3)))
                    if b.x + b.width + 3 < f1:
                        nxt.append((max(f0, b.x + b.width + 3), f1))
                free = nxt
        is_vac = s == "E_vac"
        for f0, f1 in free:
            if f1 - f0 > 2 and not is_vac:
                refs.append(
                    _el(
                        "path",
                        d=f"M{fmt(f0)} {fmt(yy)} H{fmt(f1)}",
                        stroke="#6B7480",
                        stroke_width=1.1,
                        stroke_dasharray="6 4",
                    )
                )
        b = put(plot_r + 8, placed[q] + fs * 0.36, "E" if is_vac else s, fill=_INK, anchor="start")
        if is_vac:
            texts[-1].append(_el("tspan", font_size=fmt(fs * 0.72)))
            texts[-1][-1].text = "vac"
        else:
            ports[f"ref{q}"] = (plot_r + 4, yy)

    axis_d = [f"M0 0 V{fmt(plot_h)}"]
    tick_w = 0.0
    q = 0
    while u_top + q * step <= u_bot + 1e-9:
        uu = u_top + q * step
        yy = (uu - u_top) * k
        axis_d.append(f"M-5 {fmt(yy)} H0")
        b = put(-8, yy + fs * 0.36, _fmt_v(uu if axis == "NHE" else -uu, step), size=fs * 0.92, fill=_INK, anchor="end")
        tick_w = max(tick_w, b.width)
        q += 1
    title = axis_label or ("Potential (V vs NHE)" if axis == "NHE" else "Energy (eV)")
    tx = -8 - tick_w - fs * 0.9
    t, b = _text(tx, plot_h / 2, title, fs, fill=_INK, anchor="middle", rotate=-90)
    texts.append(t)
    boxes.append(b)
    marks.append(_el("path", d=" ".join(axis_d), fill="none", stroke=_INK, stroke_width=1.2))
    if axis == "NHE":  # potential grows downward: arrowhead at the bottom
        marks.append(_head(0, plot_h + 9, 0, 1, 8, _INK))
    else:
        marks.append(_head(0, -9, 0, -1, 8, _INK))
    boxes.append(Box(-6, -10, 12, plot_h + 20))

    bounds = _union(boxes)
    holder.append(
        _el(
            "rect",
            x=bounds.x,
            y=bounds.y,
            width=bounds.width,
            height=bounds.height,
            fill="none",
            stroke="none",
            data_outline="1",
        )
    )
    holder.extend(refs + slabs)
    if rich and len(look):
        g = _look()
        g.extend(look)
        holder.append(g)
    holder.extend(marks + top + texts)
    return _finish(holder, defs, bounds, **ports)
