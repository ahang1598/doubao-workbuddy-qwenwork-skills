"""Liver microanatomy: hepatic stellate cell / myofibroblast (``cell(kind=...)``) and the sinusoid section ``liver_sinusoid``."""

from __future__ import annotations

import math
import random

from ..atomize_svg_to_slide._geometry import fmt
from ._bio_parts import _el, _look, _mix, _radial, _smooth, _circ, _check_style, _finish, _ellipse_d
from ._geometry import Box, _finite
from ._help import _drawing_api

_LIPID = "#F2D16B"
_COLLAGEN = "#C2542E"


def _taper_d(spine, w0, w1):
    left, right = [], []
    n = len(spine)
    for i, (x, y) in enumerate(spine):
        a, b = spine[max(0, i - 1)], spine[min(n - 1, i + 1)]
        tx, ty = b[0] - a[0], b[1] - a[1]
        L = math.hypot(tx, ty) or 1
        w = (w0 + (w1 - w0) * i / (n - 1)) / 2
        left.append((x - ty / L * w, y + tx / L * w))
        right.append((x + ty / L * w, y - tx / L * w))
    return _smooth(left + right[::-1], closed=True)


def _wavy(x0, y0, x1, y1, amp, waves, phase=0.0, n=28):
    L = math.hypot(x1 - x0, y1 - y0) or 1
    ux, uy = (x1 - x0) / L, (y1 - y0) / L
    pts = [
        (
            x0 + ux * L * t / n - uy * amp * math.sin(2 * math.pi * waves * t / n + phase),
            y0 + uy * L * t / n + ux * amp * math.sin(2 * math.pi * waves * t / n + phase),
        )
        for t in range(n + 1)
    ]
    return _smooth(pts)


def _fibre_bundle(x0, y0, x1, y1, w, color, k, sw):
    """Banded collagen fibre bundle: several wavy fibrils with D-period cross-banding."""
    d = []
    for j in range(k):
        off = (j - (k - 1) / 2) * w / max(1, k - 1) if k > 1 else 0
        L = math.hypot(x1 - x0, y1 - y0) or 1
        nx, ny = -(y1 - y0) / L, (x1 - x0) / L
        d.append(_wavy(x0 + nx * off, y0 + ny * off, x1 + nx * off, y1 + ny * off, w * 0.18, 2.2, phase=j * 0.9))
    return _el("path", d=" ".join(d), fill="none", stroke=color, stroke_width=sw, stroke_linecap="round")


def _stellate_parts(cx, cy, rx, ry, *, activated, fill, membrane, rich, seed, angle=0.0, band=None):
    """Elements + bound points + ports for a stellate cell centred at (cx, cy) with long axis along ``angle`` (rad)."""
    rnd = random.Random(seed)
    els, look, pts, ports = [], [], [], {}
    m = min(rx, ry)
    ca, sa = math.cos(angle), math.sin(angle)
    P = lambda u, v: (cx + u * ca - v * sa, cy + u * sa + v * ca)
    if not activated:
        # quiescent: small body with long, thin, branched processes that wrap the sinusoid (pericyte-like)
        body = []
        for i in range(48):
            a = 2 * math.pi * i / 48
            k = 1 + 0.06 * math.sin(3 * a + seed)
            body.append(P(rx * 0.55 * k * math.cos(a), ry * 0.62 * k * math.sin(a)))
        proc = []
        if band:
            # flattened in the space of Disse: long processes run along the sinusoid, a short one wraps the endothelium
            dirs = [(math.pi + 0.06, 2.6), (-0.05, 2.4), (math.pi - 0.1, 1.6), (0.12, 1.7)]
        else:
            dirs = [(2 * math.pi * (i + 0.3 + rnd.uniform(-0.12, 0.12)) / 5, rnd.uniform(1.1, 1.55)) for i in range(5)]
        for i, (a, Lk) in enumerate(dirs):
            sp, ang = [P(rx * 0.42 * math.cos(a), ry * 0.45 * math.sin(a))], a
            L = rx * Lk
            for j in range(10):
                ang += rnd.uniform(-0.16, 0.16) if not band else 0
                u = rx * 0.42 * math.cos(a) + math.cos(ang) * L * (j + 1) / 10
                v = ry * 0.45 * math.sin(a) + math.sin(ang) * L * (j + 1) / 10
                if band:
                    v = max(-band * 0.7, min(band * 0.7, v + band * 0.18 * math.sin(j * 0.9 + i)))
                sp.append(P(u, v))
            proc.append(_taper_d(sp, m * 0.3, m * 0.06))
            pts += sp
            ports[f"process{i}"] = sp[-1]
            if band:
                continue
            b0 = sp[5]
            ba = ang + rnd.choice((-1, 1)) * 0.8
            sp2 = [b0] + [
                (b0[0] + math.cos(ba + angle) * L * 0.35 * t / 4, b0[1] + math.sin(ba + angle) * L * 0.35 * t / 4)
                for t in range(1, 5)
            ]
            proc.append(_taper_d(sp2, m * 0.14, m * 0.04))
            pts += sp2
        els.append(
            _el(
                "path",
                d=_smooth(body, closed=True),
                fill=fill,
                stroke=membrane,
                stroke_width=max(1.0, m * 0.05),
                data_outline="1",
            )
        )
        els.append(
            _el(
                "path",
                d=" ".join(proc),
                fill=fill,
                stroke=membrane,
                stroke_width=max(0.8, m * 0.04),
                stroke_linejoin="round",
            )
        )
        els.append(_el("path", d=_smooth(body, closed=True), fill=fill))
        # nucleus pushed aside / indented by the lipid droplets
        nc = P(-rx * 0.18, ry * 0.1)
        els.append(
            _el(
                "path",
                d=_ellipse_d(nc[0], nc[1], rx * 0.22, ry * 0.2, math.degrees(angle)),
                fill=_mix(membrane, "#FFFFFF", 0.55),
                stroke=_mix(membrane, "#000000", 0.2),
                stroke_width=1,
            )
        )
        drops = [(0.2, -0.22, 0.17), (0.32, 0.12, 0.15), (0.08, 0.3, 0.12), (-0.02, -0.35, 0.11), (0.42, -0.12, 0.1)]
        dd = []
        for u, v, r in drops:
            x, y = P(rx * u, ry * v)
            dd.append(_circ(x, y, m * r))
        els.append(
            _el(
                "path",
                d=" ".join(dd),
                fill=_LIPID,
                stroke=_mix(_LIPID, "#7A5A10", 0.5),
                stroke_width=max(0.6, m * 0.025),
            )
        )
        if rich:
            hl = [_circ(*P(rx * u - m * r * 0.3, ry * v - m * r * 0.3), m * r * 0.32) for u, v, r in drops]
            look.append(_el("path", d=" ".join(hl), fill="#FFFFFF", fill_opacity=0.6))
        ports.update(nucleus=nc, lipid=P(rx * 0.2, -ry * 0.22))
        pts += body
    else:
        # activated myofibroblast: elongated spindle, lipid droplets lost, stress fibres, secreted collagen
        spine = [P(-rx * 1.0 + 2 * rx * t / 20, ry * 0.08 * math.sin(math.pi * t / 20 * 2 + seed)) for t in range(21)]
        prof = [ry * (0.16 + 0.84 * math.sin(math.pi * t / 20) ** 1.2) for t in range(21)]
        left, right = [], []
        for i, (x, y) in enumerate(spine):
            a, b = spine[max(0, i - 1)], spine[min(20, i + 1)]
            tx, ty = b[0] - a[0], b[1] - a[1]
            L = math.hypot(tx, ty) or 1
            w = prof[i] * (1.08 if i % 5 == 2 else 1)
            left.append((x - ty / L * w, y + tx / L * w))
            right.append((x + ty / L * w * 0.9, y - tx / L * w * 0.9))
        body = left + right[::-1]
        # short lamellipodia / processes at both poles
        poles = []
        for sgn, base in ((-1, spine[0]), (1, spine[-1])):
            inner = spine[3] if sgn < 0 else spine[-4]
            for dv in (-0.2, 0.24):
                a0 = angle + (math.pi if sgn < 0 else 0) + dv
                sp = [inner] + [
                    (
                        base[0] + math.cos(a0) * rx * 0.34 * t / 5,
                        base[1] + math.sin(a0) * rx * 0.34 * t / 5 + dv * ry * 0.4 * t / 5,
                    )
                    for t in range(1, 6)
                ]
                poles.append(_taper_d(sp, ry * 0.3, ry * 0.05))
                pts += sp
        els.append(
            _el(
                "path",
                d=_smooth(body, closed=True),
                fill=fill,
                stroke=membrane,
                stroke_width=max(1.0, m * 0.05),
                data_outline="1",
            )
        )
        els.append(_el("path", d=" ".join(poles), fill=fill, stroke=membrane, stroke_width=max(0.8, m * 0.04)))
        els.append(_el("path", d=_smooth(body, closed=True), fill=fill))
        # stress fibres: parallel actin cables along the long axis (α-SMA)
        sf = []
        for j in range(5):
            v = (j - 2) * ry * 0.17
            a0, a1 = P(-rx * 0.78, v * 0.7), P(rx * 0.78, v * 0.7)
            mid = P(0, v)
            sf.append(f"M{fmt(a0[0])} {fmt(a0[1])} Q{fmt(mid[0])} {fmt(mid[1])} {fmt(a1[0])} {fmt(a1[1])}")
        sf_c = "#B23A48"
        els.append(
            _el(
                "path",
                d=" ".join(sf),
                fill="none",
                stroke=sf_c,
                stroke_width=max(0.7, m * 0.045),
                stroke_opacity=0.85,
                stroke_linecap="round",
            )
        )
        nc = P(rx * 0.05, 0)
        els.append(
            _el(
                "path",
                d=_ellipse_d(nc[0], nc[1], rx * 0.3, ry * 0.3, math.degrees(angle)),
                fill=_mix(membrane, "#FFFFFF", 0.55),
                stroke=_mix(membrane, "#000000", 0.2),
                stroke_width=1,
            )
        )
        els.append(
            _el(
                "ellipse",
                cx=nc[0] + rx * 0.08 * ca,
                cy=nc[1] + rx * 0.08 * sa,
                rx=m * 0.09,
                ry=m * 0.08,
                fill=_mix(membrane, "#000000", 0.25),
            )
        )
        # secreted collagen bundles running alongside the cell
        cols = []
        for v, w in ((ry * 1.3, ry * 0.45), (-ry * 1.25, ry * 0.38)):
            a0, a1 = P(-rx * 1.15, v), P(rx * 1.15, v)
            cols.append(_fibre_bundle(a0[0], a0[1], a1[0], a1[1], w, _COLLAGEN, 4, max(1.0, m * 0.07)))
            pts += [P(-rx * 1.15, v + w), P(rx * 1.15, v - w)]
        els.extend(cols)
        ports.update(nucleus=nc, stress_fiber=P(-rx * 0.45, ry * 0.17), collagen=P(rx * 0.6, ry * 1.35))
        pts += body
    if rich:
        look.insert(0, _el("path", d=els[0].get("d"), fill="#FFFFFF", fill_opacity=0.18))
    return els, look, pts, ports


def _stellate_cell(rx, ry, *, activated, fill, membrane, style, seed):
    rich = _check_style(style)
    ry = (rx * (0.42 if activated else 0.9)) if ry is None or ry == rx else ry
    _finite(rx, ry)
    holder, defs = _el("g"), _el("defs")
    holder.append(defs)
    els, look, pts, ports = _stellate_parts(
        0, 0, rx, ry, activated=activated, fill=fill, membrane=membrane, rich=rich, seed=seed
    )
    holder.extend(els)
    if rich and look:
        g = _look()
        g.extend(look)
        holder.append(g)
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    pad = 2
    return _finish(
        holder,
        defs,
        Box(min(xs) - pad, min(ys) - pad, max(xs) - min(xs) + 2 * pad, max(ys) - min(ys) + 2 * pad),
        **ports,
    )


@_drawing_api(
    "parts",
    purpose="肝窦纵切（教科书级）：窦腔（红细胞）、带窗孔的扁平内皮、Disse 间隙（微绒毛伸入）、两侧肝细胞板（带核、胆小管）、窦腔内 Kupffer 细胞、Disse 间隙内的肝星状细胞（静息：脂滴+细长突起；活化：肌成纤维细胞+应力纤维），fibrosis 时 Disse 间隙沉积胶原、内皮窗孔消失（毛细血管化）。",
    returns="Geometry（原点在中心；端口 lumen/endothelium/fenestra/disse/hepatocyte/hepatocyte2/bile_canaliculus/kupffer/stellate/collagen/rbc0…/inflow/outflow）",
    semantics=(
        "width 为长度（高≈0.62×宽）；血流自左向右（inflow → outflow，门管区 → 中央静脉）。",
        'stellate="quiescent"（默认）或 "activated"；fibrosis=0–1 为 Disse 间隙胶原沉积程度（>0 时窗孔按比例减少，≥0.5 内皮下出现基底膜）。',
        "kupffer=True 在窦腔内画 Kupffer 细胞（贴内皮的巨噬细胞，含吞噬泡）；cells 为每侧肝细胞数（2–6）。",
        '不写文字：用 d.callout("hsc", "肝星状细胞", s.port("stellate"), at=(...)) 标注；style="flat" 全原生。',
    ),
    example='s = d.place(liver_sinusoid(520, stellate="activated", fibrosis=.6), at=(480, 300), key="sin")\n'
    'd.callout("hsc", "活化 HSC", s.port("stellate"), at=(860, 470), font_size=13)\n'
    'd.callout("kc", "Kupffer 细胞", s.port("kupffer"), at=(110, 90), font_size=13)',
    rank=31,
)
def liver_sinusoid(
    width=560,
    *,
    stellate="quiescent",
    fibrosis=0.0,
    kupffer=True,
    cells=4,
    hepatocyte="#E9B9A0",
    endothelium="#C98C8C",
    blood="#C8323C",
    stellate_color="#E8DDB8",
    style="rich",
    seed=3,
):
    rich = _check_style(style)
    _finite(width, fibrosis)
    if stellate not in ("quiescent", "activated"):
        raise ValueError('stellate must be "quiescent" or "activated"')
    if not 2 <= int(cells) <= 6:
        raise ValueError("cells must be 2..6 hepatocytes per plate")
    fibrosis = max(0.0, min(1.0, float(fibrosis)))
    cells = int(cells)
    rnd = random.Random(seed)
    W = float(width)
    H = W * 0.62
    s = W / 560.0
    holder, defs = _el("g"), _el("defs")
    holder.append(defs)
    look = _look() if rich else None
    ports = {}
    # vertical bands (top → bottom): hepatocyte plate | Disse | endothelium | lumen | endothelium | Disse | hepatocyte plate
    hep_h = H * 0.26
    dis_h = H * 0.11 + fibrosis * H * 0.02
    end_h = 5.5 * s
    y_hep1 = hep_h
    y_dis1 = y_hep1 + dis_h
    y_lum0 = y_dis1 + end_h
    y_lum1 = H - hep_h - dis_h - end_h
    y_dis2 = y_lum1 + end_h
    y_hep2 = y_dis2 + dis_h
    hep_line = _mix(hepatocyte, "#5A2A1A", 0.45)
    # 1. native outline: whole tissue block (plates' colour); lumen etc. on top
    holder.append(
        _el(
            "rect",
            x=0,
            y=0,
            width=W,
            height=H,
            rx=10 * s,
            fill=_mix(hepatocyte, "#FFFFFF", 0.2),
            stroke=hep_line,
            stroke_width=1.1 * s,
            data_outline="1",
        )
    )
    # 2. Disse spaces (pale, with microvilli) and lumen
    disse_c = "#F7F1E6"
    for y0 in (y_hep1, y_dis2):
        holder.append(_el("rect", x=0, y=y0, width=W, height=dis_h, fill=disse_c))
    lumen_c = _mix(blood, "#FFFFFF", 0.86)
    holder.append(_el("rect", x=0, y=y_lum0, width=W, height=y_lum1 - y_lum0, fill=lumen_c))
    # 3. hepatocyte plates: polygonal cells with nuclei; bile canaliculi between neighbours
    cw = W / cells
    hep_d, nuc_d, bc_d, mv = [], [], [], []
    for row, (y0, y1, face) in enumerate(((0, y_hep1, y_hep1), (y_hep2, H, y_hep2))):
        off = cw * 0.5 * row
        xs = [0] + [off + cw * k + rnd.uniform(-0.08, 0.08) * cw for k in range(1, cells + (1 if row else 0))] + [W]
        xs = sorted(x for x in xs if 0 <= x <= W)
        for a, b in zip(xs, xs[1:]):
            if b - a < cw * 0.3:
                continue
            g = 2.2 * s
            top, bot = (g, y1 - g) if row == 0 else (y0 + g, H - g)
            pts = [(a + g, top), (b - g, top), (b - g, bot), (a + g, bot)]
            hep_d.append("M" + " L".join(f"{fmt(x)} {fmt(y)}" for x, y in pts) + " Z")
            cx, cy = (a + b) / 2, (y0 + y1) / 2 + (-hep_h * 0.08 if row == 0 else hep_h * 0.08)
            r = min(b - a, y1 - y0) * 0.17
            nuc_d.append(_circ(cx, cy, r))
            if b < W - 1:
                bc_y = (y0 + y1) / 2 + (hep_h * 0.22 if row == 0 else -hep_h * 0.22)
                bc_d.append(_circ(b, bc_y, 3.2 * s))
            # microvilli of the sinusoidal face into the Disse space
            n_mv = max(3, int((b - a) / (7 * s)))
            for k in range(n_mv):
                x = a + (b - a) * (k + 0.5) / n_mv
                mv.append(f"M{fmt(x)} {fmt(face)} L{fmt(x)} {fmt(face + (1 if row == 0 else -1) * dis_h * 0.45)}")
            ports.setdefault(
                "hepatocyte" if row == 0 else "hepatocyte2", (cx, cy - r * 1.8 if row == 0 else cy + r * 1.8)
            )
    holder.append(
        _el("path", d=" ".join(hep_d), fill=hepatocyte, stroke=hep_line, stroke_width=1 * s, stroke_linejoin="round")
    )
    holder.append(
        _el(
            "path",
            d=" ".join(mv),
            fill="none",
            stroke=_mix(hepatocyte, "#5A2A1A", 0.25),
            stroke_width=1.5 * s,
            stroke_linecap="round",
        )
    )
    holder.append(
        _el(
            "path",
            d=" ".join(nuc_d),
            fill=_mix(hepatocyte, "#5A3A7A", 0.45),
            stroke=_mix(hepatocyte, "#3A1A3A", 0.5),
            stroke_width=0.9 * s,
        )
    )
    holder.append(_el("path", d=" ".join(bc_d), fill="#E8D25A", stroke="#8A7420", stroke_width=0.8 * s))
    if bc_d:
        bx = float(bc_d[0].split()[0][1:]) - 3.2 * s
        ports["bile_canaliculus"] = (bx, (0 + y_hep1) / 2 + hep_h * 0.22)
    # 4. collagen in the Disse space (fibrosis) + basement membrane (capillarisation)
    if fibrosis > 0:
        for y0 in (y_hep1, y_dis2):
            k = 1 + int(fibrosis * 3)
            for j in range(k):
                x0 = W * (0.04 + 0.9 * j / k) + rnd.uniform(0, W * 0.05)
                x1 = min(W * 0.98, x0 + W * (0.18 + 0.25 * fibrosis))
                holder.append(
                    _fibre_bundle(
                        x0,
                        y0 + dis_h * 0.5,
                        x1,
                        y0 + dis_h * 0.5 + rnd.uniform(-1, 1) * dis_h * 0.1,
                        dis_h * 0.5,
                        _COLLAGEN,
                        3,
                        1.1 * s,
                    )
                )
        ports["collagen"] = (W * 0.3, y_dis2 + dis_h * 0.5)
        if fibrosis >= 0.5:
            for y in (y_dis1 - 1.2 * s, y_dis2 + 1.2 * s):
                holder.append(
                    _el(
                        "path", d=f"M0 {fmt(y)} L{fmt(W)} {fmt(y)}", fill="none", stroke="#7A6A9A", stroke_width=1.6 * s
                    )
                )
    # 5. fenestrated endothelium: thin cells with gaps (fenestrae), flattened nuclei bulging into the lumen
    n_fen = int(round(7 * (1 - fibrosis)))
    end_d, fen = [], []
    for y0 in (y_dis1, y_lum1):
        gaps = sorted(W * (k + 0.5 + rnd.uniform(-0.2, 0.2)) / max(1, n_fen) for k in range(n_fen))
        x = 0.0
        gw = 6 * s
        for gx in gaps + [W + gw]:
            if gx - gw / 2 > x:
                end_d.append(
                    f"M{fmt(x)} {fmt(y0)} L{fmt(min(W, gx - gw / 2))} {fmt(y0)} L{fmt(min(W, gx - gw / 2))} {fmt(y0 + end_h)} "
                    f"L{fmt(x)} {fmt(y0 + end_h)} Z"
                )
            if gx < W:
                fen.append((gx, y0 + end_h / 2))
            x = gx + gw / 2
    holder.append(
        _el("path", d=" ".join(end_d), fill=endothelium, stroke=_mix(endothelium, "#000000", 0.3), stroke_width=0.6 * s)
    )
    en_nuc = []
    for x, y0, sgn in ((W * 0.22, y_lum0, 1), (W * 0.7, y_lum0, 1), (W * 0.45, y_lum1, -1), (W * 0.88, y_lum1, -1)):
        en_nuc.append(_ellipse_d(x, y0 + sgn * 3.5 * s, 16 * s, 4.5 * s))
    holder.append(
        _el(
            "path",
            d=" ".join(en_nuc),
            fill=_mix(endothelium, "#4A2A5A", 0.45),
            stroke=_mix(endothelium, "#000000", 0.4),
            stroke_width=0.6 * s,
        )
    )
    ports["endothelium"] = (W * 0.58, y_lum0 + 1)
    if fen:
        ports["fenestra"] = fen[len(fen) // 4] if len(fen) > 3 else fen[0]
    # 6. red blood cells flowing in the lumen
    from ._bio_parts import _rbc_items, _rbc_gradient

    rbcs = []
    lum_mid, lum_h = (y_lum0 + y_lum1) / 2, y_lum1 - y_lum0
    xs_r = [W * f for f in (0.08, 0.3, 0.42, 0.58, 0.8, 0.93)]
    for k, x in enumerate(xs_r):
        y = lum_mid + (lum_h * 0.22 if k % 2 else -lum_h * 0.2)
        rbcs.append(("face" if k % 3 else "side", x, y, lum_h * 0.17, rnd.uniform(-25, 25)))
        ports[f"rbc{k}"] = (x, y)
    if rich:
        defs.append(_rbc_gradient(blood, gid="lsrbc"))
    nat, lk = _rbc_items(rbcs, blood, rich, gid="lsrbc")
    holder.extend(nat)
    if rich:
        look.extend(lk)
    # 7. Kupffer cell: macrophage clinging to the endothelium, with phagosomes
    if kupffer:
        kx, ky = W * 0.18, y_lum0 + lum_h * 0.32
        kr = lum_h * 0.26
        kp = []
        for i in range(60):
            a = 2 * math.pi * i / 60
            kk = 1 + 0.1 * math.sin(5 * a + 1) + 0.06 * math.sin(9 * a)
            kp.append((kx + kr * 1.35 * kk * math.cos(a), ky + kr * 0.8 * kk * math.sin(a)))
        kc = "#D7C6E6"
        holder.append(_el("path", d=_smooth(kp, closed=True), fill=kc, stroke="#6A4A8A", stroke_width=1.1 * s))
        bean = [
            (
                kx - kr * 0.2 + kr * 0.5 * (1 - 0.4 * math.exp(-(((a - math.pi) / 0.6) ** 2))) * math.cos(a),
                ky + kr * 0.3 * (1 - 0.4 * math.exp(-(((a - math.pi) / 0.6) ** 2))) * math.sin(a),
            )
            for a in (2 * math.pi * i / 36 for i in range(36))
        ]
        holder.append(_el("path", d=_smooth(bean, closed=True), fill="#9A80BA", stroke="#5A3A7A", stroke_width=0.8 * s))
        holder.append(
            _el(
                "path",
                d=_circ(kx + kr * 0.62, ky - kr * 0.1, kr * 0.22)
                + " "
                + _circ(kx + kr * 0.3, ky + kr * 0.42, kr * 0.14),
                fill="#F4EEF8",
                stroke="#6A4A8A",
                stroke_width=0.8 * s,
            )
        )
        ports["kupffer"] = (kx, ky - kr * 0.55)
    # 8. hepatic stellate cell in the lower Disse space
    act = stellate == "activated"
    sx, sy = W * 0.62, y_dis2 + dis_h * 0.5
    srx = W * (0.12 if act else 0.075)
    sry = dis_h * (0.42 if act else 0.95)
    els, slook, pts, sp = _stellate_parts(
        sx,
        sy,
        srx,
        sry,
        activated=act,
        fill=stellate_color,
        membrane="#8A7A3A",
        rich=rich,
        seed=seed,
        band=None if act else dis_h / 2,
    )
    holder.extend(els)
    if rich:
        look.extend(slook)
    ports["stellate"] = (sx, sy)
    if act:
        ports.setdefault("collagen", sp.get("collagen"))
    else:
        ports["lipid"] = sp["lipid"]
    if rich:
        defs.append(_radial("lsh", "#FFFFFF", "#5A2A1A", fx=0.4, fy=0.3))
        g0 = defs[-1]
        g0[0].set("stop-opacity", ".15")
        g0[1].set("stop-opacity", ".12")
        look.insert(0, _el("rect", x=0, y=0, width=W, height=H, rx=10 * s, fill="url(#lsh)"))
        look.append(
            _el(
                "path",
                d=" ".join(
                    f"M{fmt(W * a)} {fmt(lum_mid + d)} L{fmt(W * b)} {fmt(lum_mid + d)}"
                    for a, b, d in ((0.33, 0.4, -lum_h * 0.02), (0.66, 0.74, lum_h * 0.05))
                ),
                stroke="#FFFFFF",
                stroke_width=2 * s,
                stroke_opacity=0.7,
                stroke_linecap="round",
            )
        )
        holder.append(look)
    ports.update(
        lumen=(W * 0.5, lum_mid), disse=(W * 0.3, y_hep1 + dis_h * 0.5), inflow=(0, lum_mid), outflow=(W, lum_mid)
    )
    return _finish(holder, defs, Box(0, 0, W, H), **ports)
