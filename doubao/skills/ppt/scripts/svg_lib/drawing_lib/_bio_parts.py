"""Life-science parts drawn like textbook figures."""

from __future__ import annotations

import math
import random

from ..atomize_svg_to_slide._geometry import fmt
from ._geometry import Box, Geometry, _finite
from ._help import _drawing_api
from ._parts import _STYLES, _circ, _el, _finish, _with_edges
from ._parts import _style as _check_style


def _look():
    # Group opacity makes the converter keep the whole appearance layer as one local SVG
    # (instead of dozens of tiny native shapes and embeds).
    return _el("g", opacity=".999", data_appearance="1")


def _mix(color, other, t):
    """Blend two #RRGGBB colors (t=0 → color, t=1 → other)."""
    a, b = color.lstrip("#"), other.lstrip("#")
    if len(a) != 6 or len(b) != 6:
        return color
    ca = [int(a[i : i + 2], 16) for i in (0, 2, 4)]
    cb = [int(b[i : i + 2], 16) for i in (0, 2, 4)]
    return "#" + "".join(f"{round(x + (y - x) * t):02X}" for x, y in zip(ca, cb))


def _radial(gid, inner, outer, *, fx=0.38, fy=0.34):
    g = _el("radialGradient", id=gid, cx="50%", cy="50%", r="60%", fx=f"{fx:.0%}", fy=f"{fy:.0%}")
    g.append(_el("stop", offset="0", stop_color=inner))
    g.append(_el("stop", offset="1", stop_color=outer))
    return g


def _blob(rx, ry, *, wobble=0.0, lobes=0, villi=0, villus=0.0, seed=0, samples=None):
    """Closed outline around (rx, ry): ellipse, irregular (tumor) or with microvilli (T cell)."""
    samples = samples or (max(96, villi * 10) if villi else 96)
    rnd = random.Random(seed)
    phases = [rnd.uniform(0, 2 * math.pi) for _ in range(4)]
    pts = []
    for i in range(samples):
        a = 2 * math.pi * i / samples
        k = 1.0
        if wobble:
            k += wobble * (
                0.55 * math.sin(lobes * a + phases[0])
                + 0.3 * math.sin((lobes + 2) * a + phases[1])
                + 0.15 * math.sin((lobes + 5) * a + phases[2])
            )
        if villi:
            # irregular microvilli: varying height and spacing, rounded tips
            s = abs(math.sin(villi * a / 2 + 0.6 * math.sin(3 * a + phases[3])))
            k += villus * (0.6 + 0.4 * math.sin(5 * a + phases[1])) * s**4
        pts.append((rx + rx * k * math.cos(a), ry + ry * k * math.sin(a)))
    # Catmull-Rom → cubic Bézier for a smooth closed outline.
    d = [f"M{fmt(pts[0][0])} {fmt(pts[0][1])}"]
    n = len(pts)
    for i in range(n):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d.append(f"C{fmt(c1[0])} {fmt(c1[1])} {fmt(c2[0])} {fmt(c2[1])} {fmt(p2[0])} {fmt(p2[1])}")
    return " ".join(d) + " Z"


def _poly(pts, closed=True):
    return "M" + " L".join(f"{fmt(x)} {fmt(y)}" for x, y in pts) + (" Z" if closed else "")


def _smooth(pts, closed=False):
    """Catmull-Rom through points → cubic Bézier path data."""
    n = len(pts)
    if n < 3:
        return _poly(pts, closed)
    d = [f"M{fmt(pts[0][0])} {fmt(pts[0][1])}"]
    rng = range(n) if closed else range(n - 1)
    for i in rng:
        p0 = pts[i - 1] if (i or closed) else pts[0]
        p1, p2 = pts[i], pts[(i + 1) % n]
        p3 = pts[(i + 2) % n] if (closed or i + 2 < n) else pts[-1]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d.append(f"C{fmt(c1[0])} {fmt(c1[1])} {fmt(c2[0])} {fmt(c2[1])} {fmt(p2[0])} {fmt(p2[1])}")
    return " ".join(d) + (" Z" if closed else "")


def _circle_union(circles, samples=72):
    """Outline of a star-shaped union of overlapping circles as one smooth closed path."""
    cx = sum(c[0][0] for c in circles) / len(circles)
    cy = sum(c[0][1] for c in circles) / len(circles)
    pts = []
    for i in range(samples):
        a = 2 * math.pi * i / samples
        dx, dy = math.cos(a), math.sin(a)
        best = 0.0
        for (x, y), r in circles:
            ox, oy = x - cx, y - cy
            b = ox * dx + oy * dy
            disc = b * b - (ox * ox + oy * oy - r * r)
            if disc >= 0:
                best = max(best, b + math.sqrt(disc))
        pts.append((cx + dx * best, cy + dy * best))
    return _smooth(pts, closed=True)


def _hue(color, degrees, *, light=None):
    """Rotate the hue of #RRGGBB (optionally forcing HSL lightness)."""
    import colorsys

    c = color.lstrip("#")
    if len(c) != 6:
        return color
    r, g, b = (int(c[i : i + 2], 16) / 255 for i in (0, 2, 4))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    r, g, b = colorsys.hls_to_rgb((h + degrees / 360) % 1, l if light is None else light, s)
    return "#" + "".join(f"{round(v * 255):02X}" for v in (r, g, b))


def _linear(gid, stops, *, x2="0", y2="1"):
    g = _el("linearGradient", id=gid, x1="0", y1="0", x2=x2, y2=y2)
    for off, col, *op in stops:
        g.append(_el("stop", offset=off, stop_color=col, stop_opacity=op[0] if op else None))
    return g


def _lipid_rows(curve, thickness, color, *, spacing=None, closed=True, inward=1, cholesterol=0, seed=0):
    """Path data for a bilayer along a curve."""
    length = curve.length
    head = thickness * 0.17
    spacing = spacing or head * 2.25
    n = max(4 if not closed else 12, int(length / spacing))
    step = length / (n if closed else max(1, n - 1))
    base = 0.0 if closed else -thickness / 2
    tail = thickness * 0.5 - head * 1.15
    out = {k: [] for k in ("heads_out", "heads_in", "tails", "shine", "chol", "chol_head")}
    rnd = random.Random(seed)
    every = int(cholesterol) if cholesterol and cholesterol >= 2 else (5 if cholesterol else 0)
    for i in range(n):
        (x, y), (tx, ty) = curve.at(i * step if closed else min(length, i * step))
        nx, ny = -ty * inward, tx * inward

        def at(depth, along=0.0):
            dd = base + depth
            return x + nx * dd + tx * along, y + ny * dd + ty * along

        for li, (depth, store, d0, sign) in enumerate(
            ((head, "heads_out", head * 2, 1), (thickness - head, "heads_in", thickness - head * 2, -1))
        ):
            if every and (i + li * (every // 2 + 1)) % every == every - 1:
                # cholesterol: small OH head at head level, rigid steroid ring body + short tail toward midplane
                hx, hy = at(depth - sign * head * 0.25)
                out["chol_head"].append(_circ(hx, hy, head * 0.42))
                w = head * 0.42
                a0, a1 = depth + sign * head * 0.2, depth + sign * (head * 0.2 + tail * 0.62)
                p = [at(a0, -w), at(a1, -w * 0.8), at(a1, w * 0.8), at(a0, w)]
                out["chol"].append(_poly(p))
                sx, sy = at(a1)
                ex, ey = at(a1 + sign * tail * 0.3, head * 0.25)
                out["tails"].append(f"M{fmt(sx)} {fmt(sy)} L{fmt(ex)} {fmt(ey)}")
                continue
            cx, cy = at(depth)
            out[store].append(_circ(cx, cy, head))
            out["shine"].append(
                _circ(cx - (tx + nx * sign) * head * 0.32, cy - (ty + ny * sign) * head * 0.32, head * 0.36)
            )
            # two fatty-acid tails per lipid; one carries a cis-double-bond kink
            kink = rnd.random() < 0.5
            for off in (-0.36, 0.36):
                sx, sy = at(d0, head * off)
                bend = 0.45 if (kink and off > 0) else 0.12
                mx, my = at(d0 + sign * tail * 0.5, head * off * (1 + bend * 2))
                ex, ey = at(d0 + sign * tail, head * off * (1 + bend))
                out["tails"].append(f"M{fmt(sx)} {fmt(sy)} L{fmt(mx)} {fmt(my)} L{fmt(ex)} {fmt(ey)}")
    return out


def _lipid_group(rows, thickness, color, *, shine=True, native=False):
    """Elements for ``_lipid_rows`` output; ``native`` keeps paint simple (no opacity tricks)."""
    head = thickness * 0.17
    g = _el("g")
    tail_col = _mix(color, "#E9D9A6", 0.55)
    g.append(
        _el(
            "path",
            d=" ".join(rows["tails"]),
            fill="none",
            stroke=tail_col,
            stroke_width=max(0.5, head * 0.3),
            stroke_linecap="round",
            stroke_linejoin="round",
        )
    )
    if rows["chol"]:
        g.append(
            _el(
                "path",
                d=" ".join(rows["chol"]),
                fill="#E8B54A",
                stroke=_mix("#E8B54A", "#000000", 0.3),
                stroke_width=max(0.3, head * 0.12),
            )
        )
        g.append(_el("path", d=" ".join(rows["chol_head"]), fill="#C9711E", stroke="none"))
    g.append(
        _el(
            "path",
            d=" ".join(rows["heads_out"]),
            fill=color,
            stroke=None if native else _mix(color, "#000000", 0.25),
            stroke_width=None if native else max(0.25, head * 0.12),
        )
    )
    g.append(
        _el(
            "path",
            d=" ".join(rows["heads_in"]),
            fill=_mix(color, "#FFFFFF", 0.12),
            stroke=None if native else _mix(color, "#000000", 0.25),
            stroke_width=None if native else max(0.25, head * 0.12),
        )
    )
    if shine and not native and head >= 1.4:
        g.append(_el("path", d=" ".join(rows["shine"]), fill="#FFFFFF", fill_opacity=0.55, stroke="none"))
    return g


def _bilayer(outline, thickness, color, *, spacing=None, cholesterol=0):
    """Phospholipid bilayer along a closed outline: two rows of hydrophilic heads, tails pointing inward."""
    from ._geometry import Curve

    curve = Curve(outline, tolerance=0.4)
    inward = 1 if _signed_area(curve) > 0 else -1
    rows = _lipid_rows(curve, thickness, color, spacing=spacing, closed=True, inward=inward, cholesterol=cholesterol)
    return _lipid_group(rows, thickness, color)


def _signed_area(curve):
    pts, _ = curve.samples()
    return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(pts, pts[1:] + pts[:1])) / 2


def _cristae_path(length, width, *, gap, cristae=None, seed=0):
    """Inner mitochondrial membrane: inset capsule with interdigitating cristae folds (one closed path)."""
    rnd = random.Random(seed)
    g = gap
    ri = width / 2 - g
    x0, x1 = g + ri, length - g - ri
    top, bot = g, width - g
    span = max(0.0, x1 - x0)
    n = cristae if cristae is not None else max(1, int(span / max(2.5, width * 0.3)))
    if span < width * 0.15:
        n = 0
    spacing = span / (n + 1) if n else span
    fw = min(spacing * 0.5, width * 0.16)
    fil = fw * 0.45
    inner_h = bot - top
    folds = []
    for i in range(n):
        x = x0 + spacing * (i + 1) + rnd.uniform(-0.1, 0.1) * spacing
        depth = inner_h * rnd.uniform(0.52, 0.7)
        tilt = rnd.uniform(-0.15, 0.15) * spacing
        w = fw * rnd.uniform(0.85, 1.1)
        folds.append(("top" if i % 2 == 0 else "bot", x, depth, tilt, w))
    d = [f"M{fmt(x0)} {fmt(top)}"]
    for side, x, depth, tilt, w in sorted((f for f in folds if f[0] == "top"), key=lambda f: f[1]):
        a, b, yb = x - w / 2, x + w / 2, top + depth - w / 2
        d.append(f"L{fmt(a - fil)} {fmt(top)} Q{fmt(a)} {fmt(top)} {fmt(a)} {fmt(top + fil)}")
        d.append(
            f"C{fmt(a)} {fmt(top + depth * 0.5)} {fmt(a + tilt)} {fmt(yb - depth * 0.2)} {fmt(a + tilt)} {fmt(yb)}"
        )
        d.append(f"A{fmt(w / 2)} {fmt(w / 2)} 0 0 0 {fmt(b + tilt)} {fmt(yb)}")
        d.append(
            f"C{fmt(b + tilt)} {fmt(yb - depth * 0.2)} {fmt(b)} {fmt(top + depth * 0.5)} {fmt(b)} {fmt(top + fil)}"
        )
        d.append(f"Q{fmt(b)} {fmt(top)} {fmt(b + fil)} {fmt(top)}")
    d.append(f"L{fmt(x1)} {fmt(top)} A{fmt(ri)} {fmt(ri)} 0 0 1 {fmt(x1)} {fmt(bot)}")
    for side, x, depth, tilt, w in sorted((f for f in folds if f[0] == "bot"), key=lambda f: -f[1]):
        a, b, yt = x + w / 2, x - w / 2, bot - depth + w / 2
        d.append(f"L{fmt(a + fil)} {fmt(bot)} Q{fmt(a)} {fmt(bot)} {fmt(a)} {fmt(bot - fil)}")
        d.append(
            f"C{fmt(a)} {fmt(bot - depth * 0.5)} {fmt(a + tilt)} {fmt(yt + depth * 0.2)} {fmt(a + tilt)} {fmt(yt)}"
        )
        d.append(f"A{fmt(w / 2)} {fmt(w / 2)} 0 0 0 {fmt(b + tilt)} {fmt(yt)}")
        d.append(
            f"C{fmt(b + tilt)} {fmt(yt + depth * 0.2)} {fmt(b)} {fmt(bot - depth * 0.5)} {fmt(b)} {fmt(bot - fil)}"
        )
        d.append(f"Q{fmt(b)} {fmt(bot)} {fmt(b - fil)} {fmt(bot)}")
    d.append(f"L{fmt(x0)} {fmt(bot)} A{fmt(ri)} {fmt(ri)} 0 0 1 {fmt(x0)} {fmt(top)} Z")
    return " ".join(d)


def _mito(cx, cy, length, angle, color):
    """Small mitochondrion inside a cell's appearance layer: outer membrane + folded inner membrane."""
    g = _el("g", transform=f"translate({fmt(cx - length / 2)} {fmt(cy)}) rotate({fmt(angle)} {fmt(length / 2)} 0)")
    w = length * 0.46
    inner = _el("g", transform=f"translate(0 {fmt(-w / 2)})")
    inner.append(
        _el(
            "rect",
            x=0,
            y=0,
            width=length,
            height=w,
            rx=w / 2,
            fill=_mix(color, "#FFFFFF", 0.62),
            stroke=color,
            stroke_width=0.9,
        )
    )
    inner.append(
        _el(
            "path",
            d=_cristae_path(length, w, gap=max(0.9, w * 0.1), cristae=max(2, int(length / 5)), seed=int(length * 7)),
            fill=_mix(color, "#FFFFFF", 0.35),
            stroke=color,
            stroke_width=0.7,
            stroke_linejoin="round",
        )
    )
    g.append(inner)
    return g


def _er(cx, cy, r, color):
    """Rough ER: three concentric arcs hugging the nucleus."""
    g = _el("g")
    for k, extra in enumerate((r * 0.22, r * 0.38, r * 0.54)):
        rr = r + extra
        a0, a1 = math.radians(150 + k * 6), math.radians(250 - k * 4)
        x0, y0 = cx + rr * math.cos(a0), cy + rr * math.sin(a0)
        x1, y1 = cx + rr * math.cos(a1), cy + rr * math.sin(a1)
        g.append(
            _el(
                "path",
                d=f"M{fmt(x0)} {fmt(y0)} A{fmt(rr)} {fmt(rr)} 0 0 1 {fmt(x1)} {fmt(y1)}",
                fill="none",
                stroke=color,
                stroke_width=1.1,
                stroke_linecap="round",
                stroke_opacity=0.75,
            )
        )
        for t in (0.2, 0.45, 0.7, 0.9):
            a = a0 + (a1 - a0) * t
            g.append(
                _el(
                    "circle",
                    cx=cx + (rr + 1.6) * math.cos(a),
                    cy=cy + (rr + 1.6) * math.sin(a),
                    r=0.9,
                    fill=color,
                    fill_opacity=0.8,
                )
            )
    return g


def _golgi(cx, cy, size, color):
    g = _el("g")
    for k in range(4):
        w = size * (1 - k * 0.14)
        y = cy + k * size * 0.16
        g.append(
            _el(
                "path",
                d=f"M{fmt(cx - w / 2)} {fmt(y)} Q{fmt(cx)} {fmt(y - size * 0.22)} {fmt(cx + w / 2)} {fmt(y)}",
                fill="none",
                stroke=color,
                stroke_width=1.6,
                stroke_linecap="round",
                stroke_opacity=0.85,
            )
        )
    return g


_CELL_KINDS = {
    #             outline (_blob kwargs, None = custom)   nucleus(x, y, scale)  organelles
    "generic": (dict(), (1.08, 1.02, 0.36), True),
    "t_cell": (dict(villi=22, villus=0.05), (1.0, 1.0, 0.58), False),
    "tumor": (dict(wobble=0.075, lobes=3), (1.06, 0.98, 0.44), True),
    "macrophage": (None, (1.22, 1.12, 0.34), False),
    "dendritic": (None, (1.0, 1.0, 0.5), False),
    "neutrophil": (dict(wobble=0.015, lobes=9), (1.0, 1.0, 0.62), False),
    "epithelial": (None, (1.0, 1.6, 0.5), False),
    "plasma": (dict(wobble=0.02, lobes=2), (0.66, 0.92, 0.5), False),
    "bacterium": (None, None, False),
    "plant": (None, None, False),
    "stellate": (None, None, False),
    "myofibroblast": (None, None, False),
}


def _inside(pts, x, y):
    """Even-odd point-in-polygon test."""
    hit = False
    for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            hit = not hit
    return hit


def _rrect_d(w, h, r):
    """Rounded rectangle as a path starting mid-right, clockwise (contour 0.25 = bottom, 0.75 = top)."""
    a = f"A{fmt(r)} {fmt(r)} 0 0 1"
    return (
        f"M{fmt(w)} {fmt(h / 2)} V{fmt(h - r)} {a} {fmt(w - r)} {fmt(h)} H{fmt(r)} {a} 0 {fmt(h - r)} "
        f"V{fmt(r)} {a} {fmt(r)} 0 H{fmt(w - r)} {a} {fmt(w)} {fmt(r)} Z"
    )


def _ruffled(rx, ry, seed):
    """Macrophage: ruffled body with several broad, rounded-tipped pseudopodia (one closed outline)."""
    rnd = random.Random(seed)
    circles, a = [((0, 0), 0.78)], rnd.uniform(0, 1)
    while a < 2 * math.pi - 0.8:
        reach, bend = rnd.uniform(0.8, 1.05), rnd.uniform(-0.3, 0.3)
        for t, r in ((0.5, 0.4), (0.75, 0.33), (0.95, 0.28)):
            circles.append(
                ((math.cos(a + bend * t) * reach * t, math.sin(a + bend * t) * reach * t), r * rnd.uniform(0.9, 1.1))
            )
        a += rnd.uniform(1.1, 1.6)
    ph = [rnd.uniform(0, 6.3) for _ in range(2)]
    pts = []
    for i in range(160):
        a = 2 * math.pi * i / 160
        dx, dy = math.cos(a), math.sin(a)
        best = max(
            b + math.sqrt(b * b - (x * x + y * y - r * r))
            for (x, y), r in circles
            for b in [x * dx + y * dy]
            if b * b - (x * x + y * y - r * r) >= 0
        )
        best *= 1 + 0.022 * math.sin(23 * a + ph[0]) + 0.015 * math.sin(37 * a + ph[1])
        pts.append((rx + rx * best * dx, ry + ry * best * dy))
    return _smooth(pts, closed=True)


def _taper(spine, w0, w1):
    """Closed tapered ribbon around a polyline spine (width w0 at start → w1 at tip, rounded tip)."""
    n = len(spine)
    left, right = [], []
    for i, (x, y) in enumerate(spine):
        a, b = spine[max(0, i - 1)], spine[min(n - 1, i + 1)]
        tx, ty = b[0] - a[0], b[1] - a[1]
        L = math.hypot(tx, ty) or 1
        w = (w0 + (w1 - w0) * (i / (n - 1)) ** 0.7) / 2
        left.append((x - ty / L * w, y + tx / L * w))
        right.append((x + ty / L * w, y - tx / L * w))
    (x, y), (px, py) = spine[-1], spine[-2]
    L = math.hypot(x - px, y - py) or 1
    tip = (x + (x - px) / L * w1 * 0.5, y + (y - py) / L * w1 * 0.5)
    return _smooth(left + [tip] + right[::-1], closed=True)


def _dendrites(rx, ry, seed):
    """Dendritic cell processes: 6–7 long, curved, tapering, branched veils (list of closed paths, all points)."""
    rnd = random.Random(seed)
    m, out, pts = min(rx, ry), [], []

    def grow(x, y, ang, length, w0, depth):
        steps = 9
        spine = [(x, y)]
        turn = rnd.uniform(-0.09, 0.09)
        for _ in range(steps):
            ang += turn + rnd.uniform(-0.1, 0.1)
            x, y = x + math.cos(ang) * length / steps, y + math.sin(ang) * length / steps
            spine.append((x, y))
        out.append(_taper(spine, w0, max(1.2, m * 0.035)))
        pts.extend(spine)
        if depth < 2:
            for j in range(rnd.choice((1, 1, 2)) if depth == 0 else rnd.choice((0, 1))):
                at = rnd.randint(4, 6)
                bx, by = spine[at]
                prev = spine[at - 1]
                base = math.atan2(by - prev[1], bx - prev[0])
                grow(
                    bx,
                    by,
                    base + rnd.choice((-1, 1)) * rnd.uniform(0.5, 0.9),
                    length * rnd.uniform(0.38, 0.55),
                    w0 * (1 - at / steps) * 0.85,
                    depth + 1,
                )

    n = rnd.choice((6, 7))
    for i in range(n):
        a = 2 * math.pi * (i + rnd.uniform(-0.25, 0.25)) / n
        sx, sy = rx + rx * 0.82 * math.cos(a), ry + ry * 0.82 * math.sin(a)
        grow(sx, sy, a + rnd.uniform(-0.3, 0.3), m * rnd.uniform(0.95, 1.75), m * rnd.uniform(0.36, 0.5), 0)
    return out, pts


def _segmented(cx, cy, r, n, seed):
    """Neutrophil nucleus: n lobes strung along a curved spine, joined by thin chromatin bridges (one outline)."""
    rnd = random.Random(seed)
    sizes = [rnd.uniform(0.85, 1.1) for _ in range(n)]
    span = math.radians(70 + 38 * n)
    a0 = -math.pi / 2 - span / 2 + rnd.uniform(-0.3, 0.3)
    rad = r * 0.55
    m = 28 * n
    spine = []
    for i in range(m + 1):
        t = i / m
        a = a0 + span * t
        rr = rad * (1 + 0.12 * math.sin(3 * math.pi * t))
        spine.append((cx + rr * math.cos(a), cy + 0.25 * r + rr * math.sin(a) * 0.9))
    lobe = r * 0.32
    left, right = [], []
    for i, (x, y) in enumerate(spine):
        a, b = spine[max(0, i - 1)], spine[min(m, i + 1)]
        tx, ty = b[0] - a[0], b[1] - a[1]
        L = math.hypot(tx, ty) or 1
        u = i / m * n
        k = min(n - 1, int(u))
        neck = r * 0.07 if 0 < i < m else 0
        w = neck + (lobe * sizes[k] - neck) * abs(math.sin(math.pi * u)) ** 0.45
        left.append((x - ty / L * w, y + tx / L * w))
        right.append((x + ty / L * w, y - tx / L * w))
    return _smooth((left[1:] + right[::-1][:-1])[::2], closed=True)


def _lysis(outline, rx, ry, fill, membrane, stroke_width, seed):
    """Broken membrane arcs with 3 gaps + debris leaking outward. Returns (elements, extra bound points)."""
    from ._geometry import Curve
    from ._curves import curve_frame

    curve = Curve(outline, tolerance=0.4)
    L = curve.length
    rnd = random.Random(seed + 11)
    gaps = sorted((f + rnd.uniform(-0.04, 0.04)) % 1 for f in (0.06, 0.4, 0.72))
    glen = 0.075 * L
    arcs = []
    for i, g in enumerate(gaps):
        s, e = g * L + glen / 2, gaps[(i + 1) % 3] * L - glen / 2
        arcs.append(curve.trim(s % L, e % L, wrap=True).d)
    m = min(rx, ry)
    dots, frags, bits, pts = [], [], [], []
    for g in gaps:
        fr = curve_frame(curve, g * L, "outward")
        (x, y), (nx, ny), (tx, ty) = fr.point, fr.normal, fr.tangent
        for j in range(13):
            o, t = m * rnd.uniform(0.05, 0.38), m * rnd.uniform(-0.14, 0.14) * (1 + j / 6)
            px, py = x + nx * o + tx * t, y + ny * o + ty * t
            dots.append(_circ(px, py, m * rnd.uniform(0.018, 0.04)))
            pts.append((px, py))
        for j in range(2):
            o, t = m * rnd.uniform(0.12, 0.3), m * rnd.uniform(-0.12, 0.12)
            px, py = x + nx * o + tx * t, y + ny * o + ty * t
            frags.append(
                _circle_union([((px + tx * m * 0.03 * k, py + ty * m * 0.03 * k), m * 0.045) for k in (-1, 0, 1)], 20)
            )
        o = m * rnd.uniform(0.22, 0.34)
        px, py = x + nx * o, y + ny * o
        bits.append(
            f"M{fmt(px - tx * m * 0.09)} {fmt(py - ty * m * 0.09)} Q{fmt(px + nx * m * 0.05)} {fmt(py + ny * m * 0.05)} "
            f"{fmt(px + tx * m * 0.09)} {fmt(py + ty * m * 0.09)}"
        )
        pts.append((px + nx * m * 0.06, py + ny * m * 0.06))
    return [
        _el(
            "path",
            d=" ".join(arcs),
            fill="none",
            stroke=membrane,
            stroke_width=stroke_width * 1.15,
            stroke_linecap="round",
        ),
        _el("path", d=" ".join(frags), fill=_mix(fill, membrane, 0.35)),
        _el(
            "path",
            d=" ".join(bits),
            fill="none",
            stroke=membrane,
            stroke_width=stroke_width * 0.8,
            stroke_linecap="round",
        ),
        _el("path", d=" ".join(dots), fill=_mix(membrane, "#FFFFFF", 0.15)),
    ], pts


@_drawing_api(
    "parts",
    purpose="细胞（教科书风格）：双层膜、核膜与核仁、细胞器；kind 区分免疫/上皮/肿瘤/细菌等细胞类型，state 可画裂解。",
    returns="Geometry（原点在外接框中心；端口 top/bottom/left/right/center/nucleus；epithelial 另有 apical/basal；plant 另有 wall/vacuole/tonoplast/cytoplasm 等）",
    semantics=(
        'kind："generic" 普通细胞；"t_cell" 圆形大核+微绒毛（淋巴细胞）；"tumor" 不规则轮廓、大核多核仁；'
        '"macrophage" 褶皱轮廓+伪足、吞噬泡（含被吞细菌）、肾形核；"dendritic" 胞体伸出 6–7 条弯曲分支、渐细的树突，核不规则；'
        '"neutrophil" 圆形、3–5 叶分叶核+细颗粒；"epithelial" 极性柱状上皮（ry 默认 1.8·rx）：顶端刷状缘微绒毛、顶侧紧密连接、基底核；'
        '"plasma" 浆细胞：偏位核（车轮状染色质）+大量粗面内质网；"bacterium" 胶囊形、无核，画拟核与鞭毛；'
        '"plant" 植物细胞：圆角多边形，厚纤维素细胞壁（胞间层、微纤丝、胞间连丝）在质膜外，巨大中央液泡带自己的液泡膜，'
        "薄层胞质里贴边的核、带基粒的叶绿体与线粒体（wall= 壁色）；端口 wall/plasma_membrane/cytoplasm/tonoplast/vacuole/"
        'nucleus/chloroplast/mitochondrion/plasmodesma；"stellate" 静息星状细胞（周细胞样：胞体含成串视黄醇脂滴，伸出细长分支突起，端口 lipid/process{i}）；'
        '"myofibroblast" 活化肌成纤维细胞（拉长梭形、脂滴消失、胞内平行应力纤维、胞外分泌胶原纤维束，端口 stress_fiber/collagen）；轮廓 subpath=0 是质膜中线、subpath=1 是液泡膜中线，'
        '转运蛋白 d.mount(transporter(...), on=c.contour_at(t, normal="outward")) 立质膜、'
        'on=c.contour_at(t, subpath=1, normal="left") 立液泡膜（out 朝液泡腔）；膜厚 = max(8, 0.07·min(rx, ry))，传给 membrane_thickness。',
        'state="lysing" 裂解：膜断成三段弧、缺口处胞质碎片/颗粒外溢、胞质变浅；默认 "normal"。',
        'fill 为胞质色、membrane 为膜色，其余颜色自动推导；style="rich" 加渐变与纹理（局部 SVG），"flat" 全部原生。',
        "外轮廓是原生形状且为第一个子元素：连线落在膜上，contour_at / mount 可把受体立在膜上（轮廓 0.25≈底、0.75≈顶；"
        "epithelial 的 0.75 为顶端面、0.25 为基底面；dendritic 的轮廓是胞体，树突不参与）。",
    ),
    example='t = d.place(cell(70, kind="t_cell", fill="#EEF3FA", membrane="#3A5A8C"), at=(220, 200), key="t")\n'
    'd.mount(receptor(kind="car", color="#9B2D6F"), on=t.contour_at(0.92, normal="outward"), inset=3)\n'
    'e = d.place(cell(40, kind="epithelial"), at=(500, 200), key="ep")  # 另有 macrophage/dendritic/neutrophil/plasma/plant；state="lysing"',
    rank=1,
)
def cell(
    rx,
    ry=None,
    *,
    kind="generic",
    state="normal",
    fill="#F3EEF8",
    membrane="#7A6AA8",
    nucleus=None,
    style="rich",
    seed=3,
    stroke_width=2.2,
    wall=None,
    **_legacy,
):
    if kind not in _CELL_KINDS:
        raise ValueError(f"cell kind must be one of {sorted(_CELL_KINDS)}")
    if state not in ("normal", "lysing"):
        raise ValueError('cell state must be "normal" or "lysing"')
    ry = (rx * 1.8 if kind == "epithelial" else rx) if ry is None else ry
    _finite(rx, ry)
    if style not in _STYLES:
        raise ValueError('style must be "rich" or "flat"')
    lysing = state == "lysing"
    fill = _mix(fill, "#FFFFFF", 0.45) if lysing else fill
    if kind == "plant":
        if lysing:
            raise ValueError('state="lysing" is not supported for kind="plant"')
        return _plant_cell(rx, ry, fill=fill, membrane=membrane, nucleus=nucleus, style=style, seed=seed, wall=wall)
    if kind == "bacterium":
        return _bacterium(rx, ry, fill=fill, membrane=membrane, style=style, stroke_width=stroke_width, lysing=lysing)
    if kind in ("stellate", "myofibroblast"):
        if lysing:
            raise ValueError(f'state="lysing" is not supported for kind="{kind}"')
        from ._liver_parts import _stellate_cell

        return _stellate_cell(
            rx, ry, activated=kind == "myofibroblast", fill=fill, membrane=membrane, style=style, seed=seed
        )
    from ._geometry import Curve, _box

    blob, (nxk, nyk, nscale), organelles = _CELL_KINDS[kind]
    rich = style == "rich"
    m = min(rx, ry)
    nuc_fill = nucleus or _mix(membrane, "#FFFFFF", {"neutrophil": 0.2, "plasma": 0.42}.get(kind, 0.62))
    nuc_line = _mix(nuc_fill, membrane, 0.55)
    if kind == "macrophage":
        outline = _ruffled(rx, ry, seed)
    elif kind == "epithelial":
        outline = _rrect_d(2 * rx, 2 * ry, rx * 0.3)
    else:
        outline = _blob(rx, ry, seed=seed, **(blob or dict(wobble=0.04, lobes=3)))
    extra_pts = []
    holder = _el("g")
    defs = _el("defs")
    holder.append(defs)
    # 1. native outline (first child, used for contour / mount / connector endpoints)
    holder.append(
        _el(
            "path",
            d=outline,
            fill=fill,
            stroke="none" if lysing else membrane,
            stroke_width=stroke_width,
            data_outline="1",
        )
    )
    cyto_edge = _mix(fill, membrane, 0.18)
    if kind == "dendritic":
        # processes behind a soma patch so the union reads as one cell
        paths, extra_pts = _dendrites(rx, ry, seed)
        holder.append(
            _el(
                "path",
                d=" ".join(paths),
                fill=cyto_edge,
                stroke=membrane,
                stroke_width=stroke_width * 1.6,
                stroke_linejoin="round",
            )
        )
        holder.append(_el("path", d=" ".join(paths) + " " + outline, fill=cyto_edge))
    elif kind == "epithelial":
        # apical brush border: dense microvilli standing on the top membrane
        hv, wv = min(rx * 0.34, ry * 0.2), rx * 0.085
        nv = int((2 * rx - rx * 0.6) / (wv * 1.55))
        x0 = rx - (nv - 1) * wv * 1.55 / 2
        vd = " ".join(
            f"M{fmt(x - wv / 2)} 0 V{fmt(-hv + wv / 2)} A{fmt(wv / 2)} {fmt(wv / 2)} 0 0 1 {fmt(x + wv / 2)} "
            f"{fmt(-hv + wv / 2)} V0 Z"
            for x in (x0 + i * wv * 1.55 for i in range(nv))
        )
        holder.append(_el("path", d=vd, fill=cyto_edge, stroke=membrane, stroke_width=stroke_width * 0.55))
        extra_pts += [(0, -hv - stroke_width)]
    nx, ny = rx * nxk, ry * nyk
    nr = m * nscale
    if kind == "macrophage":
        bean = [
            (
                nx + nr * 1.25 * (1 - 0.45 * math.exp(-(((a - math.pi * 0.95) / 0.5) ** 2))) * math.cos(a),
                ny + nr * (1 - 0.45 * math.exp(-(((a - math.pi * 0.95) / 0.5) ** 2))) * math.sin(a),
            )
            for a in (2 * math.pi * i / 48 for i in range(48))
        ]
        nuc_d = _smooth(bean, closed=True)
    elif kind == "dendritic":
        nuc_d = _blob(nr * 1.15, nr, wobble=0.1, lobes=2, seed=seed + 4)
        nuc_d = _el("path", d=nuc_d, transform=f"translate({fmt(nx - nr * 1.15)} {fmt(ny - nr)})")
    elif kind == "neutrophil":
        nuc_d = _segmented(nx, ny, m, 3 + seed % 3, seed)
    elif kind == "epithelial":
        nuc_d = _ellipse_d(nx, ny, rx * 0.4, min(ry * 0.24, rx * 0.62))
    elif kind == "plasma":
        nuc_d = _ellipse_d(nx, ny, nr, nr * 0.94)
    else:
        nuc_d = _ellipse_d(nx, ny, nr * 1.12, nr)
    nuc_tf = None
    if not isinstance(nuc_d, str):
        nuc_tf, nuc_d = nuc_d.get("transform"), nuc_d.get("d")
    nuc_pts = list(Curve(nuc_d, tolerance=0.5).samples()[0])
    if nuc_tf:
        dx, dy = nx - nr * 1.15, ny - nr
        nuc_pts = [(x + dx, y + dy) for x, y in nuc_pts]
    if rich:
        defs.append(_radial("cyto", _mix(fill, "#FFFFFF", 0.7), cyto_edge))
        defs.append(_radial("nuc", _mix(nuc_fill, "#FFFFFF", 0.45), _mix(nuc_fill, membrane, 0.35), fx=0.4, fy=0.35))
        look = _look()
        # cytoplasm shading + inner leaflet of the bilayer
        look.append(_el("path", d=outline, fill="url(#cyto)", stroke="none"))
        if not lysing and kind != "dendritic":
            look.append(_bilayer(outline, max(7.0, m * 0.11), membrane))
        if kind == "epithelial":
            # actin cores of the microvilli + terminal web
            look.append(
                _el(
                    "path",
                    d=" ".join(
                        f"M{fmt(x)} {fmt(-hv + wv * 0.7)} V{fmt(m * 0.16)}"
                        for x in (x0 + i * wv * 1.55 for i in range(nv))
                    ),
                    stroke=_mix(membrane, "#C0582E", 0.3),
                    stroke_width=max(0.5, wv * 0.22),
                    stroke_opacity=0.7,
                )
            )
        if organelles:
            look.append(_er(nx, ny, nr * 1.15, _mix(membrane, "#FFFFFF", 0.2)))
            look.append(_golgi(rx * 0.55, ry * 0.62, m * 0.34, _mix(membrane, "#C08A3E", 0.45)))
            for fx, fy, ang in ((0.5, 1.42, 18), (1.55, 0.52, -32), (1.62, 1.45, 64)):
                look.append(_mito(rx * fx, ry * fy, m * 0.3, ang, _mix(membrane, "#C0582E", 0.55)))
            for fx, fy in ((0.42, 0.95), (1.7, 1.0), (0.95, 1.62)):
                look.append(
                    _el(
                        "circle",
                        cx=rx * fx,
                        cy=ry * fy,
                        r=m * 0.055,
                        fill=_mix(fill, "#FFFFFF", 0.5),
                        stroke=_mix(membrane, "#FFFFFF", 0.25),
                        stroke_width=0.9,
                    )
                )
        elif kind == "epithelial":
            look.append(_golgi(rx, ny - ry * 0.38, rx * 0.7, _mix(membrane, "#C08A3E", 0.45)))
            for fx, fy, ang in ((0.42, 0.62, 84), (1.58, 0.7, 96), (0.4, 1.08, 92), (1.6, 1.12, 86)):
                look.append(_mito(rx * fx, ry * fy, rx * 0.5, ang, _mix(membrane, "#C0582E", 0.55)))
            look.append(_er(rx, ry * 0.52, rx * 0.3, _mix(membrane, "#FFFFFF", 0.2)))
        elif kind in ("macrophage", "neutrophil", "dendritic"):
            # granules / lysosomes (neutrophil: fine, dense; phagocytes: fewer, larger)
            rnd = random.Random(seed + 3)
            out_pts = list(Curve(outline, tolerance=0.6).samples()[0])
            dense = kind == "neutrophil"
            gr = []
            for _ in range(140 if dense else 14):
                x, y = rnd.uniform(0, 2 * rx), rnd.uniform(0, 2 * ry)
                if (
                    _inside(out_pts, x, y)
                    and not _inside(nuc_pts, x, y)
                    and math.hypot((x - rx) / rx, (y - ry) / ry) < 0.82
                ):
                    gr.append(_circ(x, y, m * (rnd.uniform(0.012, 0.022) if dense else rnd.uniform(0.03, 0.05))))
            look.append(
                _el(
                    "path",
                    d=" ".join(gr),
                    fill=_mix(membrane, "#C0587A" if dense else "#7A2E2E", 0.35),
                    fill_opacity=0.7 if dense else 0.85,
                )
            )
            if kind != "neutrophil":
                for fx, fy, ang in ((0.62, 1.45, 30), (1.5, 0.55, -40)):
                    look.append(_mito(rx * fx, ry * fy, m * 0.24, ang, _mix(membrane, "#C0582E", 0.55)))
        elif kind == "plasma":
            look.append(
                _el("circle", cx=nx + nr * 1.28, cy=ny - nr * 0.1, r=nr * 0.42, fill="#FFFFFF", fill_opacity=0.55)
            )
            look.append(_golgi(nx + nr * 1.3, ny - nr * 0.2, nr * 0.55, _mix(membrane, "#C08A3E", 0.45)))
        else:
            # lymphocyte: thin rim of cytoplasm with a few granules
            for a in (0.5, 1.9, 3.6, 5.1):
                look.append(
                    _el(
                        "circle",
                        cx=rx + math.cos(a) * rx * 0.8,
                        cy=ry + math.sin(a) * ry * 0.8,
                        r=m * 0.035,
                        fill=_mix(membrane, "#FFFFFF", 0.3),
                        fill_opacity=0.8,
                    )
                )
        holder.append(look)
    if kind == "macrophage":
        # phagosomes: one with an engulfed rod bacterium, one with debris; lysosomes fusing
        vac = _mix(fill, "#FFFFFF", 0.55)
        vline = _mix(membrane, "#FFFFFF", 0.1)
        for fx, fy, fr in ((0.58, 0.72, 0.2), (0.66, 1.42, 0.16), (1.12, 0.48, 0.13)):
            holder.append(
                _el(
                    "circle",
                    cx=rx * fx,
                    cy=ry * fy,
                    r=m * fr,
                    fill=vac,
                    stroke=vline,
                    stroke_width=max(0.8, stroke_width * 0.5),
                )
            )
        holder.append(
            _el(
                "rect",
                x=rx * 0.58 - m * 0.13,
                y=ry * 0.72 - m * 0.055,
                width=m * 0.26,
                height=m * 0.11,
                rx=m * 0.055,
                fill="#8DBF6A",
                stroke="#4E7A35",
                stroke_width=max(0.6, m * 0.012),
                transform=f"rotate(-28 {fmt(rx * 0.58)} {fmt(ry * 0.72)})",
            )
        )
        holder.append(
            _el(
                "path",
                d=" ".join(
                    _circ(rx * (0.66 + dx), ry * (1.42 + dy), m * 0.028)
                    for dx, dy in ((-0.05, -0.03), (0.04, 0.02), (-0.01, 0.06), (0.05, -0.05))
                ),
                fill=_mix(membrane, "#7A2E2E", 0.4),
            )
        )
        holder.append(
            _el(
                "path",
                d=" ".join(_circ(rx * fx, ry * fy, m * 0.05) for fx, fy in ((0.82, 0.6), (0.86, 1.5), (1.3, 0.44))),
                fill=_mix(membrane, "#7A2E2E", 0.45),
            )
        )
    elif kind == "plasma":
        # abundant rough ER: parallel lamellae filling the cytoplasm away from the eccentric nucleus
        out_pts = list(Curve(_blob(rx * 0.9, ry * 0.9, wobble=0.02, lobes=2, seed=seed), tolerance=0.6).samples()[0])
        er = []
        for k in range(1, 9):
            rr = nr * (1.15 + 0.17 * k)
            run = []
            for i in range(73):
                a = math.radians(-150 + 300 * i / 72)
                x, y = nx + rr * math.cos(a), ny + rr * math.sin(a)
                ok = (
                    _inside(out_pts, x - rx * 0.1, y - ry * 0.1)
                    and math.hypot(x - nx - nr * 1.28, y - ny + nr * 0.1) > nr * 0.5
                )
                if ok:
                    run.append((x, y))
                if (not ok or i == 72) and len(run) > 2:
                    er.append(_poly(run, closed=False))
                if not ok:
                    run = []
        holder.append(
            _el(
                "path",
                d=" ".join(er),
                fill="none",
                stroke=_mix(membrane, "#3A6FB0", 0.25),
                stroke_width=max(0.8, m * 0.025),
                stroke_linecap="round",
                stroke_opacity=0.85,
                stroke_dasharray=f"{fmt(m * 0.06)} {fmt(m * 0.025)}",
            )
        )
    elif kind == "epithelial":
        # tight junctions: sealing strand dots at the apical lateral corners
        tj = " ".join(
            _circ(x, rx * 0.34 + k * rx * 0.12, rx * 0.05)
            for x in (stroke_width * 0.2, 2 * rx - stroke_width * 0.2)
            for k in range(3)
        )
        holder.append(_el("path", d=tj, fill=_mix(membrane, "#000000", 0.45)))
    # 2. nucleus (native, recolorable) with envelope + nucleolus
    holder.append(_el("path", d=nuc_d, fill=nuc_fill, stroke=nuc_line, stroke_width=1.4, transform=nuc_tf))
    if kind == "plasma":
        holder.append(
            _el(
                "path",
                d=" ".join(
                    _circle_union(
                        [
                            ((nx + nr * 0.72 * math.cos(a + d), ny + nr * 0.72 * math.sin(a + d)), nr * 0.17)
                            for d in (-0.12, 0, 0.12)
                        ],
                        20,
                    )
                    for a in (2 * math.pi * i / 9 + 0.2 for i in range(9))
                ),
                fill=_mix(nuc_fill, membrane, 0.7),
            )
        )
    if rich:
        nl = _look()
        nl.append(_el("path", d=nuc_d, fill="url(#nuc)", stroke="none", transform=nuc_tf))
        bx = _box(nuc_pts)
        ncx, ncy = bx.x + bx.width / 2, bx.y + bx.height / 2
        k = 1 - 4.8 / max(10.0, min(bx.width, bx.height))
        inner_tf = f"translate({fmt(ncx)} {fmt(ncy)}) scale({k:.4f}) translate({fmt(-ncx)} {fmt(-ncy)})" + (
            " " + nuc_tf if nuc_tf else ""
        )
        if kind != "neutrophil":
            nl.append(
                _el(
                    "path",
                    d=nuc_d,
                    fill="none",
                    stroke=_mix(nuc_fill, membrane, 0.45),
                    stroke_width=0.7,
                    stroke_dasharray="2 2.4",
                    transform=inner_tf,
                )
            )
        rnd = random.Random(seed + 7)
        dots = []
        for _ in range(int(14 + nr / 2)):
            x, y = rnd.uniform(bx.x, bx.x + bx.width), rnd.uniform(bx.y, bx.y + bx.height)
            if _inside(nuc_pts, x, y):
                dots.append(_circ(x, y, rnd.uniform(0.7, 1.4)))
        nl.append(_el("path", d=" ".join(dots), fill=_mix(nuc_fill, membrane, 0.6), fill_opacity=0.55))
        holder.append(nl)
    nucleoli = {"tumor": 2, "neutrophil": 0}.get(kind, 1)
    for k in range(nucleoli):
        holder.append(
            _el(
                "ellipse",
                cx=nx + nr * (0.28 - k * 0.6) * (0.4 if kind == "macrophage" else 1),
                cy=ny - nr * (0.18 - k * 0.4),
                rx=nr * 0.24,
                ry=nr * 0.2,
                fill=_mix(nuc_fill, membrane, 0.7),
                stroke="none",
            )
        )
    if lysing:
        els, pts = _lysis(outline, rx, ry, fill, membrane, stroke_width, seed)
        holder.extend(els)
        extra_pts += pts
    sw = stroke_width / 2
    pts = list(Curve(outline, tolerance=0.5).samples()[0]) + extra_pts
    if blob is not None:  # legacy analytic box (callers rely on it), grown to include any lysis debris
        grow = max(blob.get("wobble", 0), blob.get("villus", 0))
        pts += [(-grow * rx - sw, -grow * ry - sw), (2 * rx + grow * rx + sw, 2 * ry + grow * ry + sw)]
        sw = 0
    b = _box(pts)
    bounds = Box(b.x - sw, b.y - sw, b.width + 2 * sw, b.height + 2 * sw)
    if not len(defs):
        holder.remove(defs)
    ports = dict(nucleus=(nx, ny))
    if kind == "epithelial":
        ports.update(apical=(rx, -hv), basal=(rx, 2 * ry))
    return _with_edges(Geometry(holder, bounds), **ports)


def _bacterium(rx, ry, *, fill, membrane, style, stroke_width, lysing=False):
    holder, defs = _el("g"), _el("defs")
    holder.append(defs)
    w, h = 2 * rx, 2 * ry
    holder.append(
        _el(
            "rect",
            x=0,
            y=0,
            width=w,
            height=h,
            rx=ry,
            fill=fill,
            stroke="none" if lysing else membrane,
            stroke_width=stroke_width,
            data_outline="1",
        )
    )
    if style == "rich":
        defs.append(_radial("cyto", _mix(fill, "#FFFFFF", 0.7), _mix(fill, membrane, 0.2)))
        look = _look()
        look.append(_el("rect", x=0, y=0, width=w, height=h, rx=ry, fill="url(#cyto)", stroke="none"))
        if not lysing:
            look.append(
                _el(
                    "rect",
                    x=stroke_width * 2,
                    y=stroke_width * 2,
                    width=w - stroke_width * 4,
                    height=h - stroke_width * 4,
                    rx=ry - stroke_width * 2,
                    fill="none",
                    stroke=membrane,
                    stroke_width=stroke_width * 0.45,
                    stroke_opacity=0.55,
                )
            )
        pts = [(rx * 0.45 + i * rx * 1.1 / 8, ry + (ry * 0.32 if i % 2 else -ry * 0.3)) for i in range(9)]
        look.append(
            _el(
                "path",
                d="M" + " L".join(f"{fmt(x)} {fmt(y)}" for x, y in pts),
                fill="none",
                stroke=_mix(membrane, "#FFFFFF", 0.2),
                stroke_width=1.2,
                stroke_linejoin="round",
            )
        )
        for i in range(10):
            look.append(
                _el(
                    "circle",
                    cx=rx * (0.35 + (i * 0.137) % 1.3),
                    cy=ry * (0.45 + (i * 0.29) % 1.1),
                    r=1.1,
                    fill=_mix(membrane, "#FFFFFF", 0.3),
                    fill_opacity=0.7,
                )
            )
        holder.append(look)
    tail = f"M{fmt(w)} {fmt(ry)} C{fmt(w + rx * 0.3)} {fmt(ry - ry * 0.6)} {fmt(w + rx * 0.5)} {fmt(ry + ry * 0.6)} {fmt(w + rx * 0.8)} {fmt(ry)}"
    holder.append(_el("path", d=tail, fill="none", stroke=membrane, stroke_width=1.4, stroke_linecap="round"))
    box = Box(-stroke_width / 2, -stroke_width / 2 - ry * 0.6, w + rx * 0.8 + stroke_width, h + ry * 1.2 + stroke_width)
    if lysing:
        els, pts = _lysis(_rrect_d(w, h, ry * 0.999), rx, ry, fill, membrane, stroke_width, 3)
        holder.extend(els)
        from ._geometry import _box, _union

        box = _union([box, _box(pts)])
    if not len(defs):
        holder.remove(defs)
    return _with_edges(Geometry(holder, box), nucleus=(rx, ry))


def _segment(x, y, w, h, color, rich, *, rx=None):
    rx = min(w, h) / 2 if rx is None else rx
    return _el(
        "rect",
        x=x,
        y=y,
        width=w,
        height=h,
        rx=rx,
        fill=color,
        stroke=_mix(color, "#000000", 0.25) if rich else "none",
        stroke_width=0.8 if rich else 0,
    )


@_drawing_api(
    "parts",
    purpose="膜受体/抗体（分结构域着色）：抗体、CAR、GPCR、离子通道、单杆受体。",
    returns="Geometry（原点在中心；端口 head/tail/center）",
    semantics=(
        '竖直放置，head 朝上（膜外），tail 朝下（胞内）；用 d.mount(..., on=cell.contour_at(t, normal="outward")) 立在膜上。',
        'kind="antibody" Y 形：两条重链+轻链的 Fab 臂与 Fc 段；"car" scFv 头 + 铰链 + 跨膜段 + 共刺激域 + CD3ζ；'
        '"gpcr" 七次跨膜；"channel" 两半孔道；"igsf" 免疫球蛋白超家族（柄 + domains=1–3 个圆珠 Ig 结构域，PD-1/LAG-3 等）；"bar" 单杆受体。',
        "两细胞间的成对受体-配体（免疫突触、神经突触）直接用 cell_interface。",
        'color 为主色，accent 为第二结构域色；style="rich" 加结构域描边与高光。',
    ),
    example='d.mount(receptor(kind="car", color="#9B2D6F", accent="#E0A458"), on=t.contour_at(0.95, normal="outward"), inset=3)',
    rank=2,
)
def receptor(*, color="#5B1061", kind="bar", height=44, width=None, accent=None, domains=2, style="rich"):
    rich = style == "rich"
    accent = accent or _mix(color, "#E0A458", 0.6)
    light = _mix(color, "#FFFFFF", 0.45)
    holder = _el("g")
    if kind == "antibody":
        w = width or height * 0.8
        h = height
        arm, th = h * 0.5, h * 0.13

        def arm_at(sign):
            g = _el("g", transform=f"translate({fmt(w / 2)} {fmt(h * 0.52)}) rotate({fmt(sign * 38)})")
            g.append(_segment(-th / 2, -arm, th, arm, color, rich))  # heavy chain
            g.append(_segment(-th / 2 + sign * th * 0.95, -arm, th * 0.9, arm * 0.58, light, rich))  # light chain
            return g

        holder.append(arm_at(-1))
        holder.append(arm_at(1))
        holder.append(_segment(w / 2 - th * 1.05, h * 0.5, th, h * 0.5, color, rich))
        holder.append(_segment(w / 2 + th * 0.05, h * 0.5, th, h * 0.5, color, rich))
        holder.append(
            _el("rect", x=w / 2 - th * 1.2, y=h * 0.47, width=th * 2.4, height=h * 0.06, fill=accent)
        )  # hinge
        bounds = Box(0, 0, w, h)
    elif kind == "car":
        w = width or height * 0.36
        h = height
        parts = [
            (0, 0.3, color, 0.5),
            (0.3, 0.14, light, 0.16),
            (0.44, 0.14, _mix(color, "#444444", 0.35), 0.26),
            (0.58, 0.2, accent, 0.8),
            (0.78, 0.22, _mix(accent, color, 0.45), 0.62),
        ]
        for y0, hh, col, ww in parts:
            ww = w * (1.0 if y0 == 0 else ww)
            holder.append(
                _segment(
                    w / 2 - ww / 2,
                    h * y0,
                    ww,
                    h * hh - 0.6,
                    col,
                    rich,
                    rx=(ww / 2 if y0 == 0 else min(ww, h * hh) * 0.35),
                )
            )
        if rich:
            holder.append(
                _el("ellipse", cx=w * 0.38, cy=h * 0.1, rx=w * 0.16, ry=h * 0.06, fill="#FFFFFF", fill_opacity=0.45)
            )
        bounds = Box(0, 0, w, h)
    elif kind == "gpcr":
        w = width or height * 0.9
        h = height
        n = 7
        hw = w / n
        for i in range(n):
            holder.append(
                _segment(
                    i * hw + hw * 0.12, h * 0.18, hw * 0.76, h * 0.64, color if i % 2 == 0 else light, rich, rx=hw * 0.3
                )
            )
        loop_color = _mix(color, "#000000", 0.15)
        for i in range(n - 1):
            x0, x1 = i * hw + hw / 2, (i + 1) * hw + hw / 2
            y = h * 0.18 if i % 2 else h * 0.82
            bulge = -h * 0.13 if i % 2 else h * 0.13
            holder.append(
                _el(
                    "path",
                    d=f"M{fmt(x0)} {fmt(y)} C{fmt(x0)} {fmt(y + bulge)} {fmt(x1)} {fmt(y + bulge)} {fmt(x1)} {fmt(y)}",
                    fill="none",
                    stroke=loop_color,
                    stroke_width=1.5,
                    stroke_linecap="round",
                )
            )
        holder.append(
            _el(
                "path",
                d=f"M{fmt(hw / 2)} {fmt(h * 0.18)} Q{fmt(hw * 0.1)} {fmt(h * 0.02)} {fmt(hw * 0.9)} 0",
                fill="none",
                stroke=loop_color,
                stroke_width=1.5,
                stroke_linecap="round",
            )
        )
        holder.append(
            _el(
                "path",
                d=f"M{fmt(w - hw / 2)} {fmt(h * 0.82)} Q{fmt(w - hw * 0.1)} {fmt(h * 0.98)} {fmt(w - hw * 0.9)} {fmt(h)}",
                fill="none",
                stroke=loop_color,
                stroke_width=1.5,
                stroke_linecap="round",
            )
        )
        bounds = Box(0, 0, w, h)
    elif kind == "channel":
        w = width or height * 0.5
        h = height
        for x0 in (0, w * 0.58):
            holder.append(_segment(x0, 0, w * 0.42, h, color, rich, rx=w * 0.16))
            if rich:
                for k in range(3):
                    holder.append(
                        _el(
                            "rect",
                            x=x0 + w * 0.08,
                            y=h * (0.2 + k * 0.22),
                            width=w * 0.26,
                            height=h * 0.08,
                            rx=h * 0.04,
                            fill=light,
                            fill_opacity=0.8,
                        )
                    )
        bounds = Box(0, 0, w, h)
    elif kind == "igsf":
        # Ig-superfamily receptor (PD-1, LAG-3, TIGIT…): thin stalk + 1–3 rounded Ig-domain beads
        nd = max(1, min(3, int(domains)))
        w = width or max(13, height * 0.32)
        h = height
        bead = min(h * 0.62 / nd, w * 1.08)
        holder.append(
            _segment(
                w / 2 - w * 0.11,
                bead * nd * 0.5,
                w * 0.22,
                h - bead * nd * 0.5,
                _mix(color, "#000000", 0.18),
                rich,
                rx=w * 0.1,
            )
        )
        for k in range(nd):
            cy = bead * (k + 0.5) * 0.96
            holder.append(
                _el(
                    "ellipse",
                    cx=w / 2 + (0.06 if k % 2 else -0.06) * w,
                    cy=cy,
                    rx=w / 2 * 0.94,
                    ry=bead * 0.52,
                    fill=_mix(color, "#FFFFFF", 0.38) if k == 0 else color,
                    stroke=_mix(color, "#000000", 0.32) if rich else "none",
                    stroke_width=0.9 if rich else 0,
                )
            )
        bounds = Box(0, 0, w, h)
    else:
        w = width or 14
        h = height
        holder.append(_segment(0, 0, w, h * 0.42, color, rich, rx=w * 0.45))
        holder.append(_segment(w * 0.3, h * 0.38, w * 0.4, h * 0.62, color, rich, rx=w * 0.15))
        bounds = Box(0, 0, w, h)
    return _with_edges(Geometry(holder, bounds), head=(bounds.width / 2, 0), tail=(bounds.width / 2, bounds.height))


@_drawing_api(
    "parts",
    purpose="磷脂双分子层膜段（教科书风格）：沿任意路径两排亲水头 + 向内的双条疏水尾（含顺式弯折），可点缀胆固醇。",
    returns="Geometry（画布坐标；端口 start/end 为中线两端）",
    semantics=(
        "d 为膜中线（画布坐标的 SVG 路径，可弯曲）；thickness 为双层厚度，spacing 为相邻脂质间距（默认按厚度推导）。",
        "membrane 使用画布坐标，用 d.add(key, membrane(d_path)) 原样放入（不要 place）；受体用 path 上的点定位。",
        'cholesterol=True（或整数 n：每 n 个脂质一个）在两层中插入胆固醇；style="rich" 头部描边+高光，"flat" 全原生。',
        "第一个子元素是浅色膜带（data_outline），连线/contour 落在膜带上。",
    ),
    example='d.add("mem", membrane("M 40 260 C 300 200 600 200 880 260", color="#9A88C9", thickness=22, cholesterol=True))',
    rank=3,
)
def membrane(d, *, color="#9A88C9", thickness=16, spacing=None, cholesterol=False, style="rich", seed=1):
    from ._geometry import Curve, _box
    from ._construction import ribbon

    rich = _check_style(style)
    _finite(thickness)
    curve = Curve(d, tolerance=0.3)
    if spacing is not None and spacing <= 0:
        raise ValueError("spacing must be positive")
    # legacy callers passed spacing=12 meaning "head spacing"; keep it, but never let heads overlap badly
    spacing = max(spacing, thickness * 0.3) if spacing else None
    holder = _el("g")
    band = ribbon(curve, thickness * 0.78, fill=_mix(color, "#FFFFFF", 0.78), stroke="none")
    band_el = band.element
    band_el.set("data-outline", "1")
    holder.append(band_el)
    rows = _lipid_rows(
        curve,
        thickness,
        color,
        spacing=spacing,
        closed=False,
        inward=1,
        cholesterol=(cholesterol if cholesterol is not True else 5),
        seed=seed,
    )
    if rich:
        look = _look()
        look.append(_lipid_group(rows, thickness, color))
        holder.append(look)
    else:
        holder.append(_lipid_group(rows, thickness, color, native=True))
    pts, _ = curve.samples()
    b = _box(pts).padded(thickness / 2 + 1) if hasattr(_box(pts), "padded") else _box(pts)
    start, end = curve.at(0)[0], curve.at(curve.length)[0]
    return Geometry(holder, b).with_ports(start=start, end=end)


def _nucleus_layers(rx, ry, color, *, rich, seed=0, pores=True, chromatin=True, nucleoli=1):
    """Return (native_outline_el, look_el_or_None, natives_after) for a nucleus centred on (rx, ry)."""
    env = _mix(color, "#000000", 0.28)
    outline = _el(
        "ellipse",
        cx=rx,
        cy=ry,
        rx=rx,
        ry=ry,
        fill=color,
        stroke=env,
        stroke_width=max(1.2, min(rx, ry) * 0.035),
        data_outline="1",
    )
    look = None
    after = []
    m = min(rx, ry)
    rnd = random.Random(seed)
    if rich:
        look = _look()
        look.append(_el("ellipse", cx=rx, cy=ry, rx=rx, ry=ry, fill="url(#nucg)", stroke="none"))
        if chromatin and m >= 14:
            # heterochromatin: dark clumps hugging the envelope + scattered euchromatin threads
            cl, th = [], []
            for _ in range(int(10 + m / 2.5)):
                a = rnd.uniform(0, 2 * math.pi)
                k = rnd.uniform(0.8, 0.92)
                cl.append(_circ(rx + rx * k * math.cos(a), ry + ry * k * math.sin(a), m * rnd.uniform(0.035, 0.07)))
            for _ in range(int(5 + m / 6)):
                a, rr = rnd.uniform(0, 2 * math.pi), math.sqrt(rnd.uniform(0.05, 0.6))
                x, y = rx + rx * rr * math.cos(a), ry + ry * rr * math.sin(a)
                p = [(x, y)]
                for _ in range(4):
                    a += rnd.uniform(-0.8, 0.8)
                    x, y = x + math.cos(a) * m * 0.07, y + math.sin(a) * m * 0.07
                    p.append((x, y))
                th.append(_smooth(p))
            look.append(
                _el(
                    "path",
                    d=" ".join(th),
                    fill="none",
                    stroke=_mix(color, env, 0.4),
                    stroke_width=max(0.5, m * 0.014),
                    stroke_linecap="round",
                    stroke_opacity=0.45,
                )
            )
            look.append(_el("path", d=" ".join(cl), fill=_mix(color, env, 0.5), fill_opacity=0.75))
        gap = max(1.2, m * 0.045)
        look.append(
            _el(
                "ellipse",
                cx=rx,
                cy=ry,
                rx=rx - gap,
                ry=ry - gap,
                fill="none",
                stroke=env,
                stroke_width=max(0.5, m * 0.015),
                stroke_opacity=0.8,
            )
        )
        if pores and m >= 10:
            n = max(8, int(2 * math.pi * m / max(7, m * 0.22)))
            pd = []
            for i in range(n):
                a = 2 * math.pi * (i + 0.5) / n
                ca, sa = math.cos(a), math.sin(a)
                # gap in the envelope, rendered as a light pore plug bridging both membranes
                x, y = rx + (rx - gap / 2) * ca, ry + (ry - gap / 2) * sa
                pr = max(1.1, gap * 0.85)
                pd.append(_circ(x, y, pr))
            look.append(
                _el(
                    "path",
                    d=" ".join(pd),
                    fill=_mix(color, "#FFFFFF", 0.7),
                    stroke=env,
                    stroke_width=max(0.4, m * 0.012),
                )
            )
        if m >= 8:
            look.append(
                _el(
                    "ellipse",
                    cx=rx * 0.72,
                    cy=ry * 0.55,
                    rx=rx * 0.28,
                    ry=ry * 0.16,
                    fill="#FFFFFF",
                    fill_opacity=0.35,
                    transform=f"rotate(-25 {fmt(rx * 0.72)} {fmt(ry * 0.55)})",
                )
            )
    elif pores and m >= 10:
        # flat: pores as small native gaps (white dots) on the envelope
        n = max(8, int(2 * math.pi * m / max(9, m * 0.26)))
        pd = []
        for i in range(n):
            a = 2 * math.pi * (i + 0.5) / n
            pd.append(_circ(rx + rx * math.cos(a), ry + ry * math.sin(a), max(1.0, m * 0.035)))
        after.append(_el("path", d=" ".join(pd), fill=_mix(color, "#FFFFFF", 0.75), stroke=env, stroke_width=0.6))
    nuc_col = _mix(color, env, 0.75)
    for k in range(nucleoli):
        cx, cy = rx * (1.12 - k * 0.42), ry * (0.88 + k * 0.38)
        after.append(_el("ellipse", cx=cx, cy=cy, rx=m * 0.22, ry=m * 0.19, fill=nuc_col))
        if rich and m >= 12:
            after.append(
                _el("circle", cx=cx - m * 0.07, cy=cy - m * 0.06, r=m * 0.06, fill=_mix(nuc_col, "#FFFFFF", 0.35))
            )
    return outline, look, after


@_drawing_api(
    "parts",
    purpose="细胞核（独立放大）：双层核膜带核孔、染色质（异染色质贴膜团块+常染色质细丝）、核仁。",
    returns="Geometry（原点在中心；端口 top/bottom/left/right/center/nucleolus）",
    semantics=(
        "r 为半径（ry 可选，椭圆核）；color 为核质主色，核膜/染色质/核仁颜色自动加深推导。",
        "核孔与染色质随尺寸自动增减：r<10 不画核孔，r<14 不画染色质。nucleoli 为核仁数。",
        'style="rich" 外观层（渐变+染色质+核孔）为一个局部 SVG；"flat" 全原生（核膜+核孔点+核仁）。',
    ),
    example='d.place(nucleus(60, color="#B9A6DA"), at=(300, 220), key="nuc")',
    rank=13,
)
def nucleus(r, ry=None, *, color="#B9A6DA", nucleoli=1, style="rich", seed=5):
    rich = _check_style(style)
    rx, ry = r, (r if ry is None else ry)
    _finite(rx, ry)
    holder, defs = _el("g"), _el("defs")
    holder.append(defs)
    if rich:
        defs.append(_radial("nucg", _mix(color, "#FFFFFF", 0.5), _mix(color, "#000000", 0.12), fx=0.4, fy=0.35))
    outline, look, after = _nucleus_layers(rx, ry, color, rich=rich, seed=seed, nucleoli=nucleoli)
    holder.append(outline)
    if look is not None:
        holder.append(look)
    holder.extend(after)
    sw = max(1.2, min(rx, ry) * 0.035) / 2
    return _finish(holder, defs, Box(-sw, -sw, 2 * rx + 2 * sw, 2 * ry + 2 * sw), nucleolus=(rx * 1.12, ry * 0.88))


@_drawing_api(
    "parts",
    purpose="线粒体（独立放大）：外膜、内膜、向内折叠的嵴、基质颗粒与 mtDNA 环。",
    returns="Geometry（原点在中心；端口四边/center）",
    semantics=(
        "length 为长轴长度，width 默认 length*0.45；angle 旋转（度）。color 为膜色，基质/膜间隙色自动推导。",
        "嵴数量按长度自动决定（cristae 可覆盖）；length<40 不画基质颗粒与 mtDNA。",
        '外膜为原生 rect（data_outline）；style="rich" 内膜+嵴+颗粒+高光为一个局部 SVG，"flat" 时内膜嵴也原生。',
    ),
    example='d.place(mitochondrion(160, color="#C0582E"), at=(480, 300), key="mito")',
    rank=14,
)
def mitochondrion(length, *, width=None, color="#C0582E", cristae=None, angle=0, style="rich", seed=2):
    rich = _check_style(style)
    _finite(length)
    w = width or length * 0.45
    holder, defs = _el("g"), _el("defs")
    holder.append(defs)
    body = _el("g", transform=f"rotate({fmt(angle)} {fmt(length / 2)} {fmt(w / 2)})") if angle else holder
    if body is not holder:
        holder.append(body)
    ims = _mix(color, "#FFFFFF", 0.72)  # intermembrane space
    matrix = _mix(color, "#FFFFFF", 0.42)
    osw = max(1.0, w * 0.035)
    body.append(
        _el(
            "rect",
            x=0,
            y=0,
            width=length,
            height=w,
            rx=w / 2,
            fill=ims,
            stroke=_mix(color, "#000000", 0.2),
            stroke_width=osw,
            data_outline="1",
        )
    )
    gap = max(1.2, w * 0.09)
    inner_d = _cristae_path(length, w, gap=gap, cristae=cristae, seed=seed)
    if rich:
        defs.append(_linear("mtx", [("0", _mix(matrix, "#FFFFFF", 0.35)), ("1", _mix(matrix, color, 0.25))]))
        look = _look()
        look.append(_el("rect", x=0, y=0, width=length, height=w, rx=w / 2, fill="url(#mtx)", fill_opacity=0.0))
        look.append(
            _el(
                "path",
                d=inner_d,
                fill="url(#mtx)",
                stroke=color,
                stroke_width=max(0.7, w * 0.025),
                stroke_linejoin="round",
            )
        )
        if length >= 40:
            rnd = random.Random(seed + 3)
            dots = []
            for _ in range(int(length / 9)):
                dots.append(
                    _circ(rnd.uniform(w * 0.4, length - w * 0.4), rnd.uniform(w * 0.3, w * 0.7), max(0.6, w * 0.025))
                )
            look.append(_el("path", d=" ".join(dots), fill=_mix(color, "#000000", 0.1), fill_opacity=0.55))
            # mtDNA nucleoid: small twisted loop in the matrix
            cx, cy, rr = length * 0.3, w * 0.62, w * 0.045
            look.append(
                _el(
                    "path",
                    d=_smooth(
                        [
                            (cx - rr * 2, cy),
                            (cx - rr, cy - rr),
                            (cx + rr, cy + rr),
                            (cx + rr * 2, cy),
                            (cx + rr, cy - rr),
                            (cx - rr, cy + rr),
                        ],
                        closed=True,
                    ),
                    fill="none",
                    stroke=_mix(color, "#000000", 0.35),
                    stroke_width=max(0.4, w * 0.012),
                )
            )
        look.append(
            _el(
                "rect",
                x=w * 0.3,
                y=w * 0.1,
                width=length - w * 0.6,
                height=w * 0.12,
                rx=w * 0.06,
                fill="#FFFFFF",
                fill_opacity=0.4,
            )
        )
        body.append(look)
    else:
        body.append(
            _el("path", d=inner_d, fill=matrix, stroke=color, stroke_width=max(0.7, w * 0.025), stroke_linejoin="round")
        )
    bounds = Box(-osw / 2, -osw / 2, length + osw, w + osw)
    if angle:
        bounds = bounds.transformed(_rot_matrix(angle, length / 2, w / 2))
    return _finish(holder, defs, bounds)


def _rot_matrix(angle, cx, cy):
    from ..atomize_svg_to_slide._geometry import rotate, translate

    return translate(cx, cy).then(rotate(angle)).then(translate(-cx, -cy))


def _rbc_side(cx, cy, w, h):
    """Biconcave red blood cell seen edge-on: thick rim, pinched centre (dumbbell)."""
    a, t = w / 2, h / 2
    pinch = t * 0.58
    return (
        f"M{fmt(cx - a)} {fmt(cy)} C{fmt(cx - a)} {fmt(cy - t * 1.15)} {fmt(cx - a * 0.35)} {fmt(cy - t * 1.1)} "
        f"{fmt(cx - a * 0.2)} {fmt(cy - pinch * 1.25)} Q{fmt(cx)} {fmt(cy - pinch * 0.75)} {fmt(cx + a * 0.2)} {fmt(cy - pinch * 1.25)} "
        f"C{fmt(cx + a * 0.35)} {fmt(cy - t * 1.1)} {fmt(cx + a)} {fmt(cy - t * 1.15)} {fmt(cx + a)} {fmt(cy)} "
        f"C{fmt(cx + a)} {fmt(cy + t * 1.15)} {fmt(cx + a * 0.35)} {fmt(cy + t * 1.1)} {fmt(cx + a * 0.2)} {fmt(cy + pinch * 1.25)} "
        f"Q{fmt(cx)} {fmt(cy + pinch * 0.75)} {fmt(cx - a * 0.2)} {fmt(cy + pinch * 1.25)} "
        f"C{fmt(cx - a * 0.35)} {fmt(cy + t * 1.1)} {fmt(cx - a)} {fmt(cy + t * 1.15)} {fmt(cx - a)} {fmt(cy)} Z"
    )


def _rbc_items(rbcs, color, rich, *, gid="rbcg"):
    """rbcs: [(kind, cx, cy, size, angle)], kind face|side. Returns (natives, look_children)."""
    dark = _mix(color, "#000000", 0.3)
    pale = _mix(color, "#FFFFFF", 0.42)
    nat, look = [], []
    for kind, cx, cy, s, ang in rbcs:
        tr = f"rotate({fmt(ang)} {fmt(cx)} {fmt(cy)})" if ang else None
        if kind == "face":
            nat.append(
                _el(
                    "ellipse",
                    cx=cx,
                    cy=cy,
                    rx=s,
                    ry=s * 0.92,
                    fill=color,
                    stroke=dark if rich else None,
                    stroke_width=max(0.4, s * 0.05) if rich else None,
                    transform=tr,
                )
            )
            if rich:
                look.append(_el("ellipse", cx=cx, cy=cy, rx=s, ry=s * 0.92, fill=f"url(#{gid})", transform=tr))
                look.append(
                    _el(
                        "ellipse",
                        cx=cx - s * 0.38,
                        cy=cy - s * 0.42,
                        rx=s * 0.3,
                        ry=s * 0.14,
                        fill="#FFFFFF",
                        fill_opacity=0.45,
                        transform=f"rotate({fmt(ang - 30)} {fmt(cx - s * 0.38)} {fmt(cy - s * 0.42)})",
                    )
                )
            else:
                nat.append(
                    _el(
                        "ellipse", cx=cx + s * 0.05, cy=cy + s * 0.05, rx=s * 0.42, ry=s * 0.38, fill=pale, transform=tr
                    )
                )
        else:
            d = _rbc_side(cx, cy, s * 2, s * 0.78)
            nat.append(
                _el(
                    "path",
                    d=d,
                    fill=color,
                    stroke=dark if rich else None,
                    stroke_width=max(0.4, s * 0.05) if rich else None,
                    transform=tr,
                )
            )
            if rich:
                look.append(
                    _el(
                        "path",
                        d=_rbc_side(cx, cy - s * 0.12, s * 1.5, s * 0.3),
                        fill="#FFFFFF",
                        fill_opacity=0.3,
                        transform=tr,
                    )
                )
    return nat, look


def _wbc(cx, cy, r, color, rich, seed=0):
    """Neutrophil-like white cell: round, granular cytoplasm, multi-lobed nucleus."""
    nat = [
        _el(
            "circle",
            cx=cx,
            cy=cy,
            r=r,
            fill=_mix(color, "#FFFFFF", 0.7),
            stroke=_mix(color, "#000000", 0.1),
            stroke_width=max(0.6, r * 0.06),
        )
    ]
    lobes = [(-0.38, -0.1, 0.3), (0, 0.22, 0.3), (0.38, -0.05, 0.28)]
    # three lobes joined by thin chromatin bridges, traced as one outline (no overlapping subpaths)
    nd = _circle_union(
        [((cx + r * dx, cy + r * dy), r * rr) for dx, dy, rr in lobes]
        + [((cx - r * 0.19, cy + r * 0.06), r * 0.17), ((cx + r * 0.19, cy + r * 0.08), r * 0.17)],
        samples=96,
    )
    nat.append(_el("path", d=nd, fill=color))
    look = []
    if rich:
        rnd = random.Random(seed)
        dots = []
        for _ in range(int(14 + r)):
            a, rr = rnd.uniform(0, 2 * math.pi), r * math.sqrt(rnd.uniform(0.05, 0.85))
            dots.append(_circ(cx + rr * math.cos(a), cy + rr * math.sin(a), max(0.4, r * 0.04)))
        look.append(_el("path", d=" ".join(dots), fill=_mix(color, "#FFFFFF", 0.35), fill_opacity=0.6))
        look.append(
            _el("ellipse", cx=cx - r * 0.35, cy=cy - r * 0.5, rx=r * 0.3, ry=r * 0.14, fill="#FFFFFF", fill_opacity=0.5)
        )
    return nat, look


def _endo_nuclei(points, color, *, angle_of=None):
    """Elongated endothelial nuclei bulging into the lumen: [(x, y, length, thick, angle_deg)]."""
    return " ".join(_ellipse_d(x, y, l / 2, t / 2, a) for x, y, l, t, a in points)


def _ellipse_d(cx, cy, rx, ry, ang=0):
    c, s = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    p0 = (cx + rx * c, cy + rx * s)
    p1 = (cx - rx * c, cy - rx * s)
    return (
        f"M{fmt(p0[0])} {fmt(p0[1])} A{fmt(rx)} {fmt(ry)} {fmt(ang)} 1 0 {fmt(p1[0])} {fmt(p1[1])} "
        f"A{fmt(rx)} {fmt(ry)} {fmt(ang)} 1 0 {fmt(p0[0])} {fmt(p0[1])} Z"
    )


@_drawing_api(
    "parts",
    purpose="血管（纵切/横截面）：外膜/中膜平滑肌、基底膜、带核内皮细胞层、管腔内双凹圆盘红细胞，可选白细胞。",
    returns="Geometry（原点在中心；端口四边/center/lumen；纵切另有 inlet/outlet 位于管腔两端）",
    semantics=(
        'kind="longitudinal" 水平纵切（length 为长度、radius 为外半径）；kind="cross" 圆形横截面（直径 2*radius，忽略 length）。',
        "color 为管壁主色，blood 为红细胞色；rbc 为红细胞数（None 按尺寸自动），wbc 为白细胞数（默认 0）。",
        "红细胞混合正面（中央凹陷浅色）与侧面（双凹哑铃形）两种视角；尺寸小时自动减少细胞与核数量。",
        '外壁为原生形状（data_outline），管腔/红细胞原生可改色；style="rich" 加管壁纹理与红细胞立体感（共 2 个局部 SVG）。',
    ),
    example='d.place(vessel(520, 70, rbc=9, wbc=1), at=(480, 270), key="v")',
    rank=15,
)
def vessel(
    length=360,
    radius=60,
    *,
    kind="longitudinal",
    color="#D98C8C",
    blood="#C8323C",
    rbc=None,
    wbc=0,
    style="rich",
    seed=4,
):
    rich = _check_style(style)
    if kind not in ("longitudinal", "cross"):
        raise ValueError('vessel kind must be "longitudinal" or "cross"')
    _finite(length, radius)
    if kind == "cross":
        return _vessel_cross(radius, color=color, blood=blood, rbc=rbc, wbc=wbc, rich=rich, seed=seed)
    rnd = random.Random(seed)
    L, R = length, radius
    wall = R * 0.3  # media + adventitia
    endo = max(2.5, R * 0.085)
    lum_top, lum_bot = wall + endo, 2 * R - wall - endo
    wall_dark = _mix(color, "#000000", 0.25)
    endo_col = _mix(color, "#FFE6D8", 0.6)
    nuc_col = _mix(color, "#5A3A7A", 0.6)
    holder, defs = _el("g"), _el("defs")
    holder.append(defs)
    holder.append(
        _el(
            "rect",
            x=0,
            y=0,
            width=L,
            height=2 * R,
            rx=min(4, R * 0.06),
            fill=color,
            stroke=wall_dark,
            stroke_width=1.2,
            data_outline="1",
        )
    )
    lumen_col = _mix(blood, "#FFF4EE", 0.9)
    holder.append(_el("rect", x=0, y=wall, width=L, height=2 * R - 2 * wall, fill=endo_col))
    holder.append(_el("rect", x=0, y=lum_top, width=L, height=lum_bot - lum_top, fill=lumen_col))
    # endothelial nuclei, flattened and bulging into the lumen
    cell_len = max(14, R * 0.55)
    nuclei = []
    for y, s in ((wall + endo * 0.55, 1), (2 * R - wall - endo * 0.55, -1)):
        x = rnd.uniform(0.2, 0.8) * cell_len
        while x < L - cell_len * 0.3:
            nuclei.append((x, y + s * endo * 0.25, cell_len * 0.45, endo * 1.1, rnd.uniform(-2, 2)))
            x += cell_len * rnd.uniform(0.9, 1.15)
    bm = _mix(color, "#000000", 0.45)
    holder.append(
        _el(
            "path",
            d=f"M0 {fmt(wall)} H{fmt(L)} M0 {fmt(2 * R - wall)} H{fmt(L)}",
            fill="none",
            stroke=bm,
            stroke_width=max(0.6, R * 0.015),
        )
    )
    holder.append(_el("path", d=_endo_nuclei(nuclei, nuc_col), fill=nuc_col))
    if rich:
        defs.append(
            _linear("wallg", [("0", _mix(color, "#FFFFFF", 0.25)), (".5", color), ("1", _mix(color, "#000000", 0.12))])
        )
        look = _look()
        for y0 in (0, 2 * R - wall):
            look.append(_el("rect", x=0, y=y0, width=L, height=wall, fill="url(#wallg)"))
        # smooth-muscle cells: spindle outlines with elongated nuclei, staggered in rows (tunica media)
        rows = max(1, int(wall / max(5, R * 0.09)))
        spindles, snuc = [], []
        for y0, sgn in ((0, 1), (2 * R - wall, 1)):
            for k in range(rows):
                yy = y0 + wall * (k + 0.5) / rows
                x = (k % 2) * cell_len * 0.5 - cell_len * 0.3
                sl, st = cell_len * 1.05, wall / rows * 0.82
                while x < L:
                    xs = max(0, x)
                    xe = min(L, x + sl)
                    if xe - xs > sl * 0.3:
                        spindles.append(
                            _smooth(
                                [(xs, yy), ((xs + xe) / 2, yy - st / 2), (xe, yy), ((xs + xe) / 2, yy + st / 2)],
                                closed=True,
                            )
                        )
                        if xe - xs > sl * 0.6:
                            snuc.append(_ellipse_d((xs + xe) / 2, yy, sl * 0.17, st * 0.2))
                    x += sl * 0.95
        look.append(
            _el(
                "path",
                d=" ".join(spindles),
                fill=_mix(color, "#FFFFFF", 0.12),
                stroke=_mix(color, "#000000", 0.18),
                stroke_width=max(0.35, R * 0.008),
            )
        )
        look.append(_el("path", d=" ".join(snuc), fill=_mix(color, "#5A3A7A", 0.45), fill_opacity=0.8))
        # endothelial cell junctions + lumen depth shading
        junc = []
        for y, s in ((wall, 1), (2 * R - wall, -1)):
            x = cell_len * 0.9
            while x < L:
                junc.append(f"M{fmt(x)} {fmt(y)} L{fmt(x + 1.5)} {fmt(y + s * endo)}")
                x += cell_len * rnd.uniform(0.9, 1.15)
        look.append(_el("path", d=" ".join(junc), fill="none", stroke=_mix(endo_col, "#000000", 0.3), stroke_width=0.6))
        defs.append(
            _linear(
                "lumg", [("0", "#000000", 0.1), (".25", "#000000", 0), (".75", "#000000", 0), ("1", "#000000", 0.1)]
            )
        )
        look.append(_el("rect", x=0, y=lum_top, width=L, height=lum_bot - lum_top, fill="url(#lumg)"))
        look.append(_el("rect", x=0, y=wall * 0.12, width=L, height=wall * 0.22, fill="#FFFFFF", fill_opacity=0.25))
        holder.append(look)
    # blood cells (native) + their appearance layer
    lh = lum_bot - lum_top
    s = max(3.0, min(lh * 0.2, 16))
    n = rbc if rbc is not None else max(2, int(L * lh / (s * s * 9)))
    cells = []
    placed = []
    wr = s * 1.5
    wbcs = []
    for _ in range(wbc):
        for _try in range(30):
            cx, cy = rnd.uniform(wr * 1.2, L - wr * 1.2), rnd.uniform(lum_top + wr * 1.05, lum_bot - wr * 1.05)
            if all(math.dist((cx, cy), p[:2]) > p[2] + wr + 2 for p in placed):
                placed.append((cx, cy, wr))
                wbcs.append((cx, cy))
                break
    for i in range(n * 6):
        if len(cells) >= n:
            break
        face = rnd.random() < 0.55
        cx = rnd.uniform(s * 1.2, L - s * 1.2)
        cy = rnd.uniform(lum_top + s * 1.1, lum_bot - s * 1.1)
        if all(math.dist((cx, cy), p[:2]) > p[2] + s + 1.5 for p in placed):
            placed.append((cx, cy, s))
            cells.append(("face" if face else "side", cx, cy, s, rnd.uniform(-25, 25) if not face else 0))
    nat, lk = _rbc_items(cells, blood, rich)
    for cx, cy in wbcs:
        a, b = _wbc(cx, cy, wr, "#7A5BA8", rich, seed=int(cx))
        nat += a
        lk += b
    holder.extend(nat)
    if rich and lk:
        defs.append(_rbc_gradient(blood))
        look2 = _look()
        look2.extend(lk)
        holder.append(look2)
    return _finish(holder, defs, Box(-0.6, -0.6, L + 1.2, 2 * R + 1.2), lumen=(L / 2, R), inlet=(0, R), outlet=(L, R))


def _rbc_gradient(blood, gid="rbcg"):
    # biconcave disc seen face-on: darker rim, pale central pallor
    g = _el("radialGradient", id=gid, cx="50%", cy="50%", r="50%")
    g.append(_el("stop", offset="0", stop_color=_mix(blood, "#FFFFFF", 0.45)))
    g.append(_el("stop", offset=".38", stop_color=_mix(blood, "#FFFFFF", 0.2)))
    g.append(_el("stop", offset=".75", stop_color=blood))
    g.append(_el("stop", offset="1", stop_color=_mix(blood, "#000000", 0.25)))
    return g


def _vessel_cross(R, *, color, blood, rbc, wbc, rich, seed):
    rnd = random.Random(seed)
    wall = R * 0.3
    endo = max(2.5, R * 0.085)
    rl = R - wall - endo
    wall_dark = _mix(color, "#000000", 0.25)
    endo_col = _mix(color, "#FFE6D8", 0.6)
    nuc_col = _mix(color, "#5A3A7A", 0.6)
    holder, defs = _el("g"), _el("defs")
    holder.append(defs)
    holder.append(_el("circle", cx=R, cy=R, r=R, fill=color, stroke=wall_dark, stroke_width=1.2, data_outline="1"))
    holder.append(_el("circle", cx=R, cy=R, r=R - wall, fill=endo_col))
    holder.append(_el("circle", cx=R, cy=R, r=rl, fill=_mix(blood, "#FFF4EE", 0.9)))
    holder.append(
        _el(
            "circle",
            cx=R,
            cy=R,
            r=R - wall,
            fill="none",
            stroke=_mix(color, "#000000", 0.45),
            stroke_width=max(0.6, R * 0.015),
        )
    )
    n_endo = max(5, int(2 * math.pi * rl / max(14, R * 0.5)))
    nuclei = []
    for i in range(n_endo):
        a = 2 * math.pi * (i + rnd.uniform(-0.2, 0.2)) / n_endo
        rr = R - wall - endo * 0.75
        nuclei.append(
            (R + rr * math.cos(a), R + rr * math.sin(a), max(6, R * 0.32) * 0.9, endo * 1.15, math.degrees(a) + 90)
        )
    holder.append(_el("path", d=_endo_nuclei(nuclei, nuc_col), fill=nuc_col))
    if rich:
        defs.append(_radial("wallr", _mix(color, "#FFFFFF", 0.2), _mix(color, "#000000", 0.15), fx=0.5, fy=0.5))
        look = _look()
        look.append(
            _el(
                "path",
                d=_circ(R, R, R) + " " + _circ(R, R, R - wall).replace("0 1 0", "0 1 1"),
                fill="url(#wallr)",
                fill_rule="evenodd",
            )
        )
        # circumferential smooth muscle: concentric spindle arcs with nuclei
        rows = max(1, int(wall / max(5, R * 0.09)))
        sp, sn = [], []
        for k in range(rows):
            rr = R - wall * (k + 0.5) / rows
            seg = max(6, int(2 * math.pi * rr / max(12, R * 0.45)))
            th = wall / rows * 0.8
            for j in range(seg):
                a0 = 2 * math.pi * (j + 0.5 * (k % 2)) / seg
                a1 = a0 + 2 * math.pi / seg * 0.92
                am = (a0 + a1) / 2
                pts = [
                    (R + rr * math.cos(a0), R + rr * math.sin(a0)),
                    (R + (rr + th / 2) * math.cos(am), R + (rr + th / 2) * math.sin(am)),
                    (R + rr * math.cos(a1), R + rr * math.sin(a1)),
                    (R + (rr - th / 2) * math.cos(am), R + (rr - th / 2) * math.sin(am)),
                ]
                sp.append(_smooth(pts, closed=True))
                sn.append(
                    _ellipse_d(
                        R + rr * math.cos(am),
                        R + rr * math.sin(am),
                        rr * (a1 - a0) * 0.17,
                        th * 0.2,
                        math.degrees(am) + 90,
                    )
                )
        look.append(
            _el(
                "path",
                d=" ".join(sp),
                fill=_mix(color, "#FFFFFF", 0.12),
                stroke=_mix(color, "#000000", 0.18),
                stroke_width=max(0.35, R * 0.008),
            )
        )
        look.append(_el("path", d=" ".join(sn), fill=_mix(color, "#5A3A7A", 0.45), fill_opacity=0.8))
        look.append(
            _el(
                "path",
                d=f"M{fmt(R * 0.35)} {fmt(R * 0.5)} A{fmt(R * 0.82)} {fmt(R * 0.82)} 0 0 1 {fmt(R * 0.75)} {fmt(R * 0.2)}",
                fill="none",
                stroke="#FFFFFF",
                stroke_opacity=0.35,
                stroke_width=wall * 0.25,
                stroke_linecap="round",
            )
        )
        holder.append(look)
    s = max(3.0, min(rl * 0.2, 16))
    n = rbc if rbc is not None else max(2, int(rl * rl * math.pi / (s * s * 7)))
    placed, cells, wbcs = [], [], []
    wr = s * 1.5
    for _ in range(wbc):
        for _try in range(30):
            a, rr = rnd.uniform(0, 2 * math.pi), rnd.uniform(0, max(0, rl - wr * 1.1))
            p = (R + rr * math.cos(a), R + rr * math.sin(a))
            if all(math.dist(p, q[:2]) > q[2] + wr + 2 for q in placed):
                placed.append((*p, wr))
                wbcs.append(p)
                break
    for _ in range(n * 8):
        if len(cells) >= n:
            break
        a, rr = rnd.uniform(0, 2 * math.pi), rnd.uniform(0, max(0, rl - s * 1.15))
        p = (R + rr * math.cos(a), R + rr * math.sin(a))
        if all(math.dist(p, q[:2]) > q[2] + s + 1.5 for q in placed):
            placed.append((*p, s))
            face = rnd.random() < 0.6
            cells.append(("face" if face else "side", p[0], p[1], s, 0 if face else rnd.uniform(-60, 60)))
    nat, lk = _rbc_items(cells, blood, rich)
    for cx, cy in wbcs:
        a, b = _wbc(cx, cy, wr, "#7A5BA8", rich, seed=int(cx))
        nat += a
        lk += b
    holder.extend(nat)
    if rich and lk:
        defs.append(_rbc_gradient(blood))
        look2 = _look()
        look2.extend(lk)
        holder.append(look2)
    return _finish(holder, defs, Box(-0.6, -0.6, 2 * R + 1.2, 2 * R + 1.2), lumen=(R, R))


_BASE_COLORS = ("#E2574C", "#3D8ED8", "#F2B33D", "#3FAE6A")  # A, T, G, C (A-T, G-C pairs)


@_drawing_api(
    "parts",
    purpose="DNA 双螺旋：两条糖-磷酸骨架（前后交叠、近深远浅）+ 彩色碱基对横档；或展开的梯子。",
    returns="Geometry（原点在中心；端口四边/center/start/end 为螺旋轴两端）",
    semantics=(
        "length 为螺旋轴长度（水平；需要竖直时 d.place 后 set_transform(rotation=90) 或用 Geometry.rotated）；width 为螺旋直径。",
        'kind="helix" 双螺旋（每圈 turn 长度，默认 width*2.1，约 10 个碱基对）；"ladder" 平直梯子（两条平行骨架 + 碱基对）。',
        "color 为骨架 1 色，color2 为骨架 2 色（默认由 color 推导）；碱基对 A-T/G-C 四色固定，pairs=False 时横档单色。",
        '骨架为原生 path（第一条带 data_outline）；style="rich" 加磷酸基团小球与骨架高光（一个局部 SVG），"flat" 全原生。',
    ),
    example='d.place(dna(360, width=64, color="#2E5C9A"), at=(480, 200), key="dna")',
    rank=16,
)
def dna(
    length=320, *, width=56, kind="helix", color="#2E5C9A", color2=None, turn=None, pairs=True, style="rich", seed=0
):
    rich = _check_style(style)
    if kind not in ("helix", "ladder"):
        raise ValueError('dna kind must be "helix" or "ladder"')
    _finite(length, width)
    color2 = color2 or _hue(color, 150, light=0.5)
    A = width / 2
    bw = max(2.0, width * 0.1)  # backbone ribbon width
    holder, defs = _el("g"), _el("defs")
    holder.append(defs)
    rnd = random.Random(seed)
    seq = [rnd.randrange(4) for _ in range(400)]
    rung_w = max(1.2, width * 0.055)

    def base_col(k, strand):
        b = seq[k % len(seq)]
        partner = {0: 1, 1: 0, 2: 3, 3: 2}[b]
        return _BASE_COLORS[b if strand == 0 else partner]

    if kind == "ladder":
        y1, y2 = bw / 2, width - bw / 2
        holder.append(_el("rect", x=0, y=0, width=length, height=bw, rx=bw / 2, fill=color, data_outline="1"))
        holder.append(_el("rect", x=0, y=width - bw, width=length, height=bw, rx=bw / 2, fill=color2))
        step = max(rung_w * 2.6, width * 0.22)
        n = max(2, int(length / step))
        by_col = {}
        for i in range(n):
            x = (i + 0.5) * length / n
            mid = (y1 + y2) / 2
            by_col.setdefault(base_col(i, 0), []).append(
                _poly(
                    [
                        (x - rung_w / 2, y1),
                        (x + rung_w / 2, y1),
                        (x + rung_w / 2, mid - 0.4),
                        (x - rung_w / 2, mid - 0.4),
                    ]
                )
            )
            by_col.setdefault(base_col(i, 1), []).append(
                _poly(
                    [
                        (x - rung_w / 2, mid + 0.4),
                        (x + rung_w / 2, mid + 0.4),
                        (x + rung_w / 2, y2),
                        (x - rung_w / 2, y2),
                    ]
                )
            )
        for col, ds in by_col.items():
            holder.insert(2, _el("path", d=" ".join(ds), fill=col if pairs else _mix(color, "#FFFFFF", 0.5)))
        if rich:
            look = _look()
            ph = []
            for i in range(n):
                x = (i + 0.5) * length / n
                ph += [_circ(x, y1, bw * 0.42), _circ(x, y2, bw * 0.42)]
            look.append(_el("path", d=" ".join(ph), fill="#FFFFFF", fill_opacity=0.35))
            holder.append(look)
        return _finish(holder, defs, Box(0, 0, length, width), start=(0, width / 2), end=(length, width / 2))
    turn = turn or width * 2.1
    k = 2 * math.pi / turn
    samples = max(40, int(length / 2))

    def strand_pts(phase, x0, x1):
        m = max(3, int((x1 - x0) / length * samples) + 2)
        return [
            (x0 + (x1 - x0) * j / (m - 1), A + A * math.sin(k * (x0 + (x1 - x0) * j / (m - 1)) + phase))
            for j in range(m)
        ]

    def ribbon_d(pts, phase):
        # backbone ribbon: offset vertically ± bw/2, thinner where the strand turns edge-on
        top, bot = [], []
        for x, y in pts:
            depth = math.cos(k * x + phase)  # >0 front
            h = bw / 2 * (0.75 + 0.25 * abs(depth))
            top.append((x, y - h))
            bot.append((x, y + h))
        return _poly(top + bot[::-1])

    # split each strand into half-turn segments; segments with cos>0 are in front
    segs = {0: ([], []), 1: ([], [])}  # strand -> (front, back)
    for s, phase in ((0, 0.0), (1, math.pi)):
        # boundaries where cos(kx+phase)=0  → kx+phase = pi/2 + n*pi
        xs = [0.0]
        nn = math.floor((phase - math.pi / 2) / math.pi)
        while True:
            x = (math.pi / 2 + nn * math.pi - phase) / k
            if x >= length:
                break
            if x > 0:
                xs.append(x)
            nn += 1
        xs.append(length)
        for a, b in zip(xs, xs[1:]):
            if b - a < 1e-6:
                continue
            front = math.cos(k * (a + b) / 2 + phase) > 0
            segs[s][0 if front else 1].append(ribbon_d(strand_pts(phase, a, b), phase))
    cols = (color, color2)
    # rungs: base pairs at fixed spacing, colored per base, darker when behind (rungs are always between strands)
    bp = turn / 10
    n = int(length / bp)
    rung_front = {}
    for i in range(n):
        x = (i + 0.5) * bp
        y1 = A + A * math.sin(k * x)
        y2 = A + A * math.sin(k * x + math.pi)
        if abs(y1 - y2) < bw * 1.1:
            continue
        mid = (y1 + y2) / 2
        sgn = 1 if y2 > y1 else -1
        for strand, (ya, yb) in ((0, (y1, mid)), (1, (mid, y2))):
            col = base_col(i, strand) if pairs else _mix(color, "#FFFFFF", 0.45)
            ya2 = ya + sgn * bw * 0.35 if strand == 0 else ya + sgn * 0.4
            yb2 = yb - sgn * 0.4 if strand == 0 else yb - sgn * bw * 0.35
            d = _poly([(x - rung_w / 2, ya2), (x + rung_w / 2, ya2), (x + rung_w / 2, yb2), (x - rung_w / 2, yb2)])
            rung_front.setdefault(col, []).append(d)
    back_cols = [_mix(c, "#FFFFFF", 0.45) for c in cols]
    first = True
    for s in (0, 1):
        if segs[s][1]:
            el = _el("path", d=" ".join(segs[s][1]), fill=back_cols[s])
            if first:
                el.set("data-outline", "1")
                first = False
            holder.append(el)
    for col, ds in rung_front.items():
        holder.append(_el("path", d=" ".join(ds), fill=col))
    for s in (0, 1):
        if segs[s][0]:
            holder.append(_el("path", d=" ".join(segs[s][0]), fill=cols[s]))
    if rich:
        look = _look()
        # phosphate beads on front segments + glossy highlight line
        beads = []
        for s, phase in ((0, 0.0), (1, math.pi)):
            x = bp * 0.5
            while x < length:
                if math.cos(k * x + phase) > 0.15:
                    y = A + A * math.sin(k * x + phase)
                    beads.append(_circ(x, y, bw * 0.32))
                x += bp
        hl = []
        for s, phase in ((0, 0.0), (1, math.pi)):
            pts = [
                (x, A + A * math.sin(k * x + phase) - bw * 0.22)
                for x in [j * length / samples for j in range(samples + 1)]
            ]
            run = []
            for x, y in pts:
                if math.cos(k * x + phase) > 0.3:
                    run.append((x, y))
                elif run:
                    if len(run) > 2:
                        hl.append(_poly(run, closed=False))
                    run = []
            if len(run) > 2:
                hl.append(_poly(run, closed=False))
        look.append(
            _el(
                "path",
                d=" ".join(hl),
                fill="none",
                stroke="#FFFFFF",
                stroke_opacity=0.45,
                stroke_width=max(0.6, bw * 0.2),
                stroke_linecap="round",
            )
        )
        look.append(_el("path", d=" ".join(beads), fill="#FFFFFF", fill_opacity=0.3))
        holder.append(look)
    return _finish(holder, defs, Box(0, -bw / 2, length, width + bw), start=(0, A), end=(length, A))


def _strand_path(pts, bw):
    """Ribbon of half-width bw/2 around a polyline (open)."""
    left, right = [], []
    for i, (x, y) in enumerate(pts):
        x0, y0 = pts[max(0, i - 1)]
        x1, y1 = pts[min(len(pts) - 1, i + 1)]
        dx, dy = x1 - x0, y1 - y0
        n = math.hypot(dx, dy) or 1.0
        ox, oy = -dy / n * bw / 2, dx / n * bw / 2
        left.append((x + ox, y + oy))
        right.append((x - ox, y - oy))
    return _poly(left + right[::-1])


@_drawing_api(
    "parts",
    purpose="核酸操作示意：平直双链 DNA，可打开 R-loop/转录泡、单链切口、翻起的 3′/5′ 瓣、高亮被编辑碱基、PAM 区与 5′/3′ 极性。",
    returns="Geometry（原点在中心；端口 top_5/top_3/bottom_3/bottom_5、bubble、nick、flap_tip、pam、hl{i}、四边/center）",
    semantics=(
        "length 为长度、gap 为两条链间距；碱基位置用 0–1 的比例。上链 5′→3′ 自左向右，下链反向。",
        "bubble=(a, b) 两链在区间内分开成泡（R-loop/转录泡），上链抬起、下链压低，泡内留出给 guide RNA 的空间；端口 bubble 为泡中心，bubble_top/bubble_bottom 为两条分开的单链。",
        "nick=t 在上链 t 处断开（缺口）；flap=(t, 长度) 从缺口处翻起一段单链（3′ 瓣）；highlight=[(t, 颜色)] 把该位置碱基对涂色（被编辑碱基），端口 hl0、hl1…",
        "pam=(a, b) 在下链上标出 PAM 区（加粗色块）；polarity=True 在四个链端标 5′/3′（原生文字）。",
        'style="rich" 加骨架高光（一个局部 SVG），"flat" 全原生；与 nucleic_strand、protein_complex 组合画 CRISPR、转录、复制、修复机制图。',
    ),
    example='d.place(duplex(620, bubble=(.35, .6), nick=.5, highlight=[(.42, "#C2457A")], pam=(.62, .68)), at=(450, 260), key="dna")',
    rank=16,
)
def duplex(
    length=560,
    *,
    gap=34,
    color="#2E5C9A",
    color2=None,
    bubble=None,
    nick=None,
    flap=None,
    highlight=(),
    pam=None,
    pam_color="#E0A458",
    polarity=True,
    font_size=13,
    style="rich",
    seed=0,
):
    rich = _check_style(style)
    _finite(length, gap, font_size)
    color2 = color2 or _mix(color, "#FFFFFF", 0.35)
    bw = max(3.0, gap * 0.16)
    holder, defs = _el("g"), _el("defs")
    holder.append(defs)
    rnd = random.Random(seed)
    lift = gap * 0.9 if bubble else 0.0

    def frac(t, name):
        _finite(t)
        if not 0 <= t <= 1:
            raise ValueError(f"{name} must be a 0–1 fraction of the length")
        return t * length

    if bubble:
        b0, b1 = sorted((frac(bubble[0], "bubble"), frac(bubble[1], "bubble")))
        if b1 - b0 < gap:
            raise ValueError("bubble is too short for this gap; widen it")
    ramp = gap * 1.1

    def offset(x):
        if not bubble:
            return 0.0
        if x <= b0 - ramp or x >= b1 + ramp:
            return 0.0
        if b0 <= x <= b1:
            return 1.0
        t = (x - (b0 - ramp)) / ramp if x < b0 else ((b1 + ramp) - x) / ramp
        return 0.5 - 0.5 * math.cos(math.pi * t)

    xs = [length * i / 160 for i in range(161)]
    top = [(x, -gap / 2 - lift * offset(x)) for x in xs]
    bot = [(x, gap / 2 + lift * offset(x)) for x in xs]
    nick_x = frac(nick, "nick") if nick is not None else None
    cut = gap * 0.22

    def pieces(pts, x_cut):
        if x_cut is None:
            return [pts]
        return [[p for p in pts if p[0] <= x_cut - cut / 2], [p for p in pts if p[0] >= x_cut + cut / 2]]

    top_pieces = pieces(top, nick_x)
    flap_tip = None
    if flap:
        if nick_x is None:
            raise ValueError("flap needs nick= (the flap peels off at the nick)")
        fl = float(flap[1]) if len(flap) > 1 else gap * 2.2
        _finite(fl)
        y0 = -gap / 2 - lift * offset(nick_x)
        start = nick_x - cut / 2
        fpts = [(start - fl * 0.55 * (i / 24), y0 - fl * 0.9 * math.sin(math.pi / 2 * i / 24)) for i in range(25)]
        flap_tip = fpts[-1]
        right = [p for p in top_pieces[0] if p[0] < start - fl * 0.55]
        top_pieces[0] = right
        top_pieces.append(fpts[::-1])
    # base pairs (rungs) between strands where they are paired
    step = max(bw * 2.4, gap * 0.32)
    n = int(length / step)
    hl = {}
    for i, item in enumerate(highlight or ()):
        hl[i] = (frac(item[0], "highlight"), item[1] if len(item) > 1 else "#C2457A")
    rungs = {}
    for i in range(n):
        x = (i + 0.5) * length / n
        if any(abs(x - hx) < step * 0.5 for hx, _ in hl.values()):
            continue
        o = offset(x)
        ya, yb = -gap / 2 - lift * o, gap / 2 + lift * o
        col = _BASE_COLORS[rnd.randrange(4)]
        if o > 0.02:
            # unpaired bases point into the bubble as short stubs
            for y, s in ((ya, 1), (yb, -1)):
                rungs.setdefault(col, []).append(
                    _poly(
                        [
                            (x - bw * 0.3, y),
                            (x + bw * 0.3, y),
                            (x + bw * 0.3, y + s * gap * 0.3),
                            (x - bw * 0.3, y + s * gap * 0.3),
                        ]
                    )
                )
            continue
        rungs.setdefault(col, []).append(
            _poly([(x - bw * 0.3, ya), (x + bw * 0.3, ya), (x + bw * 0.3, yb), (x - bw * 0.3, yb)])
        )
    hl_ports = {}
    for i, (hx, hc) in hl.items():
        o = offset(hx)
        ya, yb = -gap / 2 - lift * o, gap / 2 + lift * o
        if o > 0.02:
            holder.append(
                _el(
                    "path",
                    d=_poly(
                        [
                            (hx - bw * 0.7, ya),
                            (hx + bw * 0.7, ya),
                            (hx + bw * 0.7, ya + gap * 0.42),
                            (hx - bw * 0.7, ya + gap * 0.42),
                        ]
                    ),
                    fill=hc,
                )
            )
            hl_ports[f"hl{i}"] = (hx, ya + gap * 0.42)
        else:
            holder.append(
                _el(
                    "path",
                    d=_poly([(hx - bw * 0.7, ya), (hx + bw * 0.7, ya), (hx + bw * 0.7, yb), (hx - bw * 0.7, yb)]),
                    fill=hc,
                )
            )
            hl_ports[f"hl{i}"] = (hx, 0.0)
    for col, ds in rungs.items():
        holder.append(_el("path", d=" ".join(ds), fill=col, fill_opacity=0.85))
    first = True
    for pts in top_pieces:
        if len(pts) > 1:
            el = _el("path", d=_strand_path(pts, bw), fill=color)
            if first:
                el.set("data-outline", "1")
                first = False
            holder.append(el)
    holder.append(_el("path", d=_strand_path(bot, bw), fill=color2))
    pam_port = None
    if pam:
        p0, p1 = sorted((frac(pam[0], "pam"), frac(pam[1], "pam")))
        pts = [p for p in bot if p0 <= p[0] <= p1]
        if len(pts) > 1:
            holder.append(_el("path", d=_strand_path(pts, bw * 1.9), fill=pam_color))
            pam_port = ((p0 + p1) / 2, gap / 2 + bw)
    if polarity:
        fs = font_size
        for x, y, t, anchor in (
            (-fs * 0.4, -gap / 2 + fs * 0.35, "5′", "end"),
            (length + fs * 0.4, -gap / 2 + fs * 0.35, "3′", "start"),
            (-fs * 0.4, gap / 2 + fs * 0.35, "3′", "end"),
            (length + fs * 0.4, gap / 2 + fs * 0.35, "5′", "start"),
        ):
            el = _el(
                "text",
                x=x,
                y=y,
                font_size=fs,
                text_anchor=anchor,
                fill=_mix(color, "#000000", 0.35),
                font_weight="bold",
            )
            el.text = t
            holder.append(el)
    if rich:
        look = _look()
        hl_d = []
        for pts in top_pieces + [bot]:
            if len(pts) > 2:
                hl_d.append(_poly([(x, y - bw * 0.22) for x, y in pts], closed=False))
        look.append(
            _el(
                "path",
                d=" ".join(hl_d),
                fill="none",
                stroke="#FFFFFF",
                stroke_opacity=0.45,
                stroke_width=max(0.6, bw * 0.22),
                stroke_linecap="round",
            )
        )
        holder.append(look)
    pad = font_size * 1.6 if polarity else 0
    top_y = min(y for pts in top_pieces for _, y in pts) - bw
    bounds = Box(-pad, top_y, length + 2 * pad, gap / 2 + lift + bw - top_y)
    ports = dict(top_5=(0, -gap / 2), top_3=(length, -gap / 2), bottom_3=(0, gap / 2), bottom_5=(length, gap / 2))
    if bubble:
        ports.update(
            bubble=((b0 + b1) / 2, 0.0),
            bubble_top=((b0 + b1) / 2, -gap / 2 - lift),
            bubble_bottom=((b0 + b1) / 2, gap / 2 + lift),
        )
    if nick_x is not None:
        ports["nick"] = (nick_x, -gap / 2 - lift * offset(nick_x))
    if flap_tip:
        ports["flap_tip"] = flap_tip
    if pam_port:
        ports["pam"] = pam_port
    ports.update(hl_ports)
    return _finish(holder, defs, bounds, **ports)


@_drawing_api(
    "parts",
    purpose="单链核酸（RNA / ssDNA）沿任意画布路径：骨架带 + 碱基短刺，可分段着色并标注（guide RNA 间隔区、PBS、RT 模板、茎环）。",
    returns="Geometry（画布坐标；端口 start/end 与各段 seg{i}）",
    semantics=(
        "d 为画布坐标的 SVG 路径（直线/曲线均可）；segments=[(起, 止, 颜色, 标签)] 用 0–1 比例给分段上色，标签为原生文字写在该段外侧。",
        'bases="up"/"down"/None 控制碱基短刺朝向（朝向配对的另一条链）；kind="rna" 默认暖色，"ssdna" 默认冷色。',
        "与 duplex 组合：沿 R-loop 泡内画 guide RNA 与靶链配对，或从 3′ 瓣接到 RT 模板。用 d.add(key, nucleic_strand(...)) 原样放入。",
    ),
    example='d.add("sg", nucleic_strand("M 300 240 L 470 240", segments=[(0, .6, "#C2457A", "间隔区 20 nt")], bases="down"))',
    rank=17,
)
def nucleic_strand(d, *, kind="rna", color=None, width=None, segments=(), bases="down", font_size=12, style="rich"):
    from ._geometry import _flatten

    rich = _check_style(style)
    if kind not in ("rna", "ssdna"):
        raise ValueError('kind must be "rna" or "ssdna"')
    color = color or ("#D9822B" if kind == "rna" else "#3D6FB6")
    width = width or 4.5
    _finite(width, font_size)
    pts = list(_flatten(d, 0.5)[0])
    if len(pts) < 2:
        raise ValueError("nucleic_strand needs a path with length")
    holder = _el("g")
    holder.append(_el("path", d=_strand_path(pts, width), fill=color, data_outline="1"))
    cum = [0.0]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        cum.append(cum[-1] + math.hypot(x1 - x0, y1 - y0))
    total = cum[-1]

    def at(t):
        s = t * total
        for i in range(1, len(cum)):
            if cum[i] >= s:
                k = (s - cum[i - 1]) / ((cum[i] - cum[i - 1]) or 1)
                (x0, y0), (x1, y1) = pts[i - 1], pts[i]
                n = math.hypot(x1 - x0, y1 - y0) or 1
                return x0 + (x1 - x0) * k, y0 + (y1 - y0) * k, -(y1 - y0) / n, (x1 - x0) / n
        x, y = pts[-1]
        return x, y, 0.0, 1.0

    ports = {"start": pts[0], "end": pts[-1]}
    for i, seg in enumerate(segments or ()):
        a, b, col = float(seg[0]), float(seg[1]), seg[2]
        sp = [at(a + (b - a) * j / 30)[:2] for j in range(31)]
        holder.append(_el("path", d=_strand_path(sp, width * 1.15), fill=col))
        x, y, nx, ny = at((a + b) / 2)
        ports[f"seg{i}"] = (x, y)
        if len(seg) > 3 and seg[3]:
            side = -1 if bases == "down" else 1
            lx, ly = x + nx * side * (width + font_size * 0.9), y + ny * side * (width + font_size * 0.9)
            el = _el(
                "text",
                x=lx,
                y=ly + font_size * 0.35,
                font_size=font_size,
                text_anchor="middle",
                fill=_mix(col, "#000000", 0.3),
                font_weight="bold",
            )
            el.text = str(seg[3])
            holder.append(el)
    if bases:
        sgn = 1 if bases == "down" else -1
        stub = []
        nstub = max(3, int(total / (width * 2.6)))
        for j in range(nstub):
            x, y, nx, ny = at((j + 0.5) / nstub)
            stub.append(
                _poly(
                    [
                        (x - ny * 0.6, y + nx * 0.6),
                        (x + nx * sgn * width * 2.2 - ny * 0.6, y + ny * sgn * width * 2.2 + nx * 0.6),
                        (x + nx * sgn * width * 2.2 + ny * 0.6, y + ny * sgn * width * 2.2 - nx * 0.6),
                        (x + ny * 0.6, y - nx * 0.6),
                    ]
                )
            )
        holder.insert(0, _el("path", d=" ".join(stub), fill=_mix(color, "#FFFFFF", 0.25)))
    if rich:
        look = _look()
        look.append(
            _el(
                "path",
                d=_poly([(x, y) for x, y in pts], closed=False),
                fill="none",
                stroke="#FFFFFF",
                stroke_opacity=0.4,
                stroke_width=max(0.6, width * 0.25),
                stroke_linecap="round",
            )
        )
        holder.append(look)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    pad = width * 2.5 + font_size * 1.5
    g = Geometry(holder, Box(min(xs) - pad, min(ys) - pad, max(xs) - min(xs) + 2 * pad, max(ys) - min(ys) + 2 * pad))
    return g.with_ports(**ports)


@_drawing_api(
    "parts",
    purpose='结合在 DNA 上的蛋白复合体（教科书式团块蛋白）：kind="bilobed" 双叶（REC/NUC 叶，如 Cas9）、"globular" 单叶、"clamp" 环形夹；可融合效应结构域（脱氨酶、逆转录酶、FokI…）。',
    returns="Geometry（原点在中心；端口 groove（双叶间 DNA 结合槽）、fused、linker、四边/center）",
    semantics=(
        'w/h 为主体外框；color 主色，lobe_labels=("REC","NUC") 叶片标签（原生文字，可传 None）；label 为整体名称（写在主体上方）。',
        'fused=("脱氨酶", 颜色) 在 fused_side（"left"/"right"/"top"）用柔性连接肽挂一个小结构域并标注；端口 fused 为该结构域中心。',
        "nickase=True 在 NUC 叶标一个“×”表示失活的切割位点（如 nCas9 D10A）；groove 端口是放 duplex 的位置。",
        "fill_opacity 默认 0.82，让结合槽里的 DNA/RNA 透出来：先 place 蛋白、再 place duplex，核酸就画在蛋白上方，读者能看清 R-loop。",
        'style="rich" 叶片径向渐变 + 表面颗粒（一个局部 SVG），"flat" 全原生。',
    ),
    example='cas = d.place(protein_complex(240, 150, label="nCas9 (D10A)", fused=("TadA 脱氨酶", "#6C5BA7"), nickase=True), at=(430, 220))',
    rank=18,
)
def protein_complex(
    w=240,
    h=150,
    *,
    kind="bilobed",
    color="#0B6E79",
    label=None,
    lobe_labels=("REC", "NUC"),
    fused=None,
    fused_side="left",
    nickase=False,
    fill_opacity=0.82,
    font_size=13,
    style="rich",
    seed=3,
):
    rich = _check_style(style)
    if kind not in ("bilobed", "globular", "clamp"):
        raise ValueError('kind must be "bilobed", "globular" or "clamp"')
    _finite(w, h, font_size)
    holder, defs = _el("g"), _el("defs")
    holder.append(defs)
    dark = _mix(color, "#000000", 0.25)
    lobes = []
    if kind == "bilobed":
        lobes = [(-w * 0.2, -h * 0.12, w * 0.34, h * 0.4, color, 0), (w * 0.2, h * 0.06, w * 0.32, h * 0.38, dark, 1)]
    elif kind == "globular":
        lobes = [(0, 0, w * 0.5, h * 0.5, color, 0)]
    first = True
    for i, (cx, cy, rx, ry, col, s) in enumerate(lobes):
        d = _blob(rx, ry, wobble=0.06, lobes=5, seed=seed + i)
        el = _el(
            "path",
            d=d,
            fill=col,
            fill_opacity=fill_opacity,
            transform=f"translate({fmt(cx - rx)} {fmt(cy - ry)})",
            stroke=_mix(col, "#000000", 0.3),
            stroke_width=1.2,
        )
        if first:
            el.set("data-outline", "1")
            first = False
        holder.append(el)
    if kind == "clamp":
        r1, r2 = min(w, h) * 0.5, min(w, h) * 0.28
        holder.append(
            _el(
                "path",
                d=_circ(0, 0, r1) + " " + _circ(0, 0, r2),
                fill=color,
                fill_rule="evenodd",
                stroke=dark,
                stroke_width=1.2,
                data_outline="1",
            )
        )
    ports = {"groove": (0, h * 0.02)}
    texts = []
    if kind == "bilobed" and lobe_labels:
        for (cx, cy, rx, ry, col, _), txt in zip(lobes, lobe_labels):
            if txt:
                # upper part of the lobe: the DNA runs through the middle groove
                t = _el(
                    "text",
                    x=cx,
                    y=cy - ry * 0.45 + font_size * 0.35,
                    font_size=font_size * 0.9,
                    text_anchor="middle",
                    fill="#FFFFFF",
                    font_weight="bold",
                )
                t.text = txt
                texts.append(t)
    if nickase and kind == "bilobed":
        cx, cy = lobes[1][0] + lobes[1][2] * 0.45, lobes[1][1] - lobes[1][3] * 0.2
        t = _el(
            "text",
            x=cx,
            y=cy + font_size * 0.35,
            font_size=font_size * 1.1,
            text_anchor="middle",
            fill="#FFFFFF",
            font_weight="bold",
        )
        t.text = "×"
        texts.append(t)
    top = -h / 2
    left, right = -w / 2, w / 2
    if fused:
        name, fcol = fused[0], fused[1] if len(fused) > 1 else "#6C5BA7"
        fr = min(w, h) * 0.26
        if fused_side == "left":
            fx, fy, lx, ly = -w / 2 - fr * 0.6, -h * 0.32, -w * 0.38, -h * 0.2
        elif fused_side == "right":
            fx, fy, lx, ly = w / 2 + fr * 0.6, -h * 0.32, w * 0.38, -h * 0.1
        elif fused_side == "top":
            fx, fy, lx, ly = -w * 0.05, -h / 2 - fr * 0.9, -w * 0.1, -h * 0.42
        else:
            raise ValueError('fused_side must be "left", "right" or "top"')
        holder.append(
            _el(
                "path",
                d=f"M{fmt(lx)} {fmt(ly)} Q{fmt((lx + fx) / 2)} {fmt((ly + fy) / 2 - fr * 0.5)} {fmt(fx)} {fmt(fy)}",
                fill="none",
                stroke=_mix(fcol, "#000000", 0.2),
                stroke_width=2.2,
                stroke_dasharray="3 2.5",
            )
        )
        holder.append(
            _el(
                "path",
                d=_blob(fr, fr * 0.85, wobble=0.07, lobes=4, seed=seed + 7),
                fill=fcol,
                transform=f"translate({fmt(fx - fr)} {fmt(fy - fr * 0.85)})",
                stroke=_mix(fcol, "#000000", 0.3),
                stroke_width=1.2,
            )
        )
        t = _el(
            "text",
            x=fx,
            y=fy - fr - font_size * 0.5,
            font_size=font_size,
            text_anchor="middle",
            fill=_mix(fcol, "#000000", 0.35),
            font_weight="bold",
        )
        t.text = str(name)
        texts.append(t)
        ports.update(fused=(fx, fy), linker=((lx + fx) / 2, (ly + fy) / 2))
        top = min(top, fy - fr - font_size * 1.4)
        left, right = min(left, fx - fr - 4), max(right, fx + fr + 4)
    if label:
        t = _el(
            "text",
            x=0,
            y=top - font_size * 0.4,
            font_size=font_size * 1.05,
            text_anchor="middle",
            fill=dark,
            font_weight="bold",
        )
        t.text = str(label)
        texts.append(t)
        top -= font_size * 1.6
    if rich and lobes:
        look = _look()
        for i, (cx, cy, rx, ry, col, _) in enumerate(lobes):
            gid = f"pc_g{i}"
            defs.append(_radial(gid, _mix(col, "#FFFFFF", 0.45), col))
            look.append(
                _el(
                    "path",
                    d=_blob(rx * 0.98, ry * 0.98, wobble=0.06, lobes=5, seed=seed + i),
                    fill=f"url(#{gid})",
                    transform=f"translate({fmt(cx - rx * 0.98)} {fmt(cy - ry * 0.98)})",
                    opacity=0.55 * fill_opacity,
                )
            )
        rnd = random.Random(seed)
        dots = [
            _circ(rnd.uniform(-w * 0.4, w * 0.4), rnd.uniform(-h * 0.4, h * 0.4), rnd.uniform(1.2, 2.4))
            for _ in range(26)
        ]
        look.append(_el("path", d=" ".join(dots), fill="#FFFFFF", fill_opacity=0.18))
        holder.append(look)
    holder.extend(texts)
    return _finish(holder, defs, Box(left, top, right - left, h / 2 - top), **ports)


def _cluster_layout(n, r, seed):
    """Loose cluster of n spheres of radius ~r (deterministic, non-overlapping, roughly round)."""
    rnd = random.Random(seed)
    pts = [(0.0, 0.0, r)]
    golden = math.pi * (3 - math.sqrt(5))
    i = 1
    while len(pts) < n and i < n * 40:
        rr = r * (0.8 + 0.35 * rnd.random())
        dist = r * 2.25 * math.sqrt(i) * 0.8
        a = i * golden + rnd.uniform(-0.3, 0.3)
        x, y = dist * math.cos(a), dist * math.sin(a)
        if all(math.dist((x, y), p[:2]) > p[2] + rr + r * 0.25 for p in pts):
            pts.append((x, y, rr))
        i += 1
    return pts


@_drawing_api(
    "parts",
    purpose="细胞因子/趋化因子等小分子簇：成簇的小球（立体高光），可选单体为二聚体小球。",
    returns="Geometry（原点在中心；端口四边/center）",
    semantics=(
        "n 为分子数，r 为单个分子半径；分子按种子松散成簇且互不重叠。",
        'kind="sphere" 单球；"dimer" 每个分子为两个相切小球（如 IL-8/IFN-γ 二聚体）；"globular" 不规则多叶球（蛋白感）。',
        'color 为主色；原生圆/路径可改色；style="rich" 加径向渐变与高光（一个局部 SVG），"flat" 纯色原生。',
        "r<4 时不画高光以免糊成一团。",
    ),
    example='d.place(cytokine(7, r=6, color="#E08A2C"), at=(620, 140), key="il2")',
    rank=17,
)
def cytokine(n=6, *, r=6, color="#E08A2C", kind="sphere", style="rich", seed=1):
    rich = _check_style(style)
    if kind not in ("sphere", "dimer", "globular"):
        raise ValueError("cytokine kind must be sphere/dimer/globular")
    _finite(r)
    holder, defs = _el("g"), _el("defs")
    holder.append(defs)
    rnd = random.Random(seed + 11)
    pts = _cluster_layout(n, r * (1.35 if kind == "dimer" else 1.0), seed)
    shapes = []  # (path_d, highlight centre, radius)
    for x, y, rr in pts:
        if kind == "dimer":
            a = rnd.uniform(0, math.pi)
            s = rr / 1.35
            c1 = (x + math.cos(a) * s * 0.8, y + math.sin(a) * s * 0.8)
            c2 = (x - math.cos(a) * s * 0.8, y - math.sin(a) * s * 0.8)
            shapes.append((_circle_union([(c1, s), (c2, s)]), [(c1, s), (c2, s)]))
        elif kind == "globular":
            lobes = []
            for j in range(4):
                a = j * math.pi / 2 + rnd.uniform(-0.4, 0.4)
                lobes.append(((x + math.cos(a) * rr * 0.38, y + math.sin(a) * rr * 0.38), rr * 0.68))
            shapes.append((_circle_union(lobes), [((x, y), rr)]))
        else:
            shapes.append((_circ(x, y, rr), [((x, y), rr)]))
    dark = _mix(color, "#000000", 0.3)
    outline = True
    for d_, _ in shapes:
        el = _el(
            "path", d=d_, fill=color, stroke=dark if rich else None, stroke_width=max(0.3, r * 0.06) if rich else None
        )
        if outline:
            el.set("data-outline", "1")
            outline = False
        holder.append(el)
    if rich and r >= 4:
        defs.append(_radial("cyk", _mix(color, "#FFFFFF", 0.55), _mix(color, "#000000", 0.2), fx=0.35, fy=0.3))
        look = _look()
        for d_, _ in shapes:
            look.append(_el("path", d=d_, fill="url(#cyk)"))
        hl = []
        for _, balls in shapes:
            for (cx, cy), s in balls:
                hl.append(_circ(cx - s * 0.35, cy - s * 0.38, s * 0.26))
        look.append(_el("path", d=" ".join(hl), fill="#FFFFFF", fill_opacity=0.7))
        holder.append(look)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    pad = max(p[2] for p in pts) + r * 0.3
    if kind == "dimer":
        pad = max(p[2] for p in pts) / 1.35 * 1.8 + 0.5
    return _finish(
        holder, defs, Box(min(xs) - pad, min(ys) - pad, max(xs) - min(xs) + 2 * pad, max(ys) - min(ys) + 2 * pad)
    )


@_drawing_api(
    "parts",
    purpose='抗体（IgG）便捷函数：等同 receptor(kind="antibody")。',
    returns="Geometry（端口 head/tail/center）",
    semantics=("height 为总高；color 重链色、accent 铰链色；可 d.place 自由摆放或 d.mount 立在膜上。",),
    example='d.place(antibody(height=60, color="#2E6FB0"), at=(400, 120), key="ab")',
    rank=18,
)
def antibody(*, color="#2E6FB0", height=44, accent=None, style="rich"):
    return receptor(kind="antibody", color=color, height=height, accent=accent, style=style)


def _icosa_face(cx, cy, R, rot=0):
    """Projected icosahedron (vertex-up): hexagonal outline + inner triangle facets (6 outer verts, 1 centre ring)."""
    outer = [
        (cx + R * math.cos(math.radians(rot + 90 + 60 * i)), cy - R * math.sin(math.radians(rot + 90 + 60 * i)))
        for i in range(6)
    ]
    inner = [
        (
            cx + R * 0.5 * math.cos(math.radians(rot + 120 * i - 90)),
            cy - R * 0.5 * math.sin(math.radians(rot + 120 * i - 90)),
        )
        for i in range(3)
    ]
    return outer, inner


@_drawing_api(
    "parts",
    purpose="病毒：包膜病毒（脂质包膜 + 刺突糖蛋白 + 基质蛋白 + 核衣壳）、无包膜二十面体衣壳（可带腺病毒式纤突），或噬菌体（二十面体头部 + 尾鞘 + 基板 + 尾丝）。",
    returns="Geometry（原点在中心；端口四边/center；噬菌体另有 head/tail 为头顶与基板）",
    semantics=(
        'kind="enveloped" 球形，r 为包膜半径（刺突向外伸出约 0.28r）；kind="phage" 竖直，r 为头部外接半径（总高约 5.2r）；'
        'kind="icosahedral" 正视二十面体衣壳（六边形轮廓 + 明暗三角面 + 壳粒点），r 为外接半径，fibers=True 从顶点伸出带末端球节的纤突（腺病毒，约 0.75r）。',
        "color 为主色（包膜/头部），accent 为刺突/尾鞘色（默认由 color 推导）。",
        "刺突数量与尾鞘环数随尺寸自动减少；外轮廓（包膜圆 / 衣壳或头部六边形）为原生形状并带 data_outline。",
        'style="rich" 加包膜脂质纹理、球形渐变与高光（一个局部 SVG），"flat" 全原生。',
    ),
    example='d.place(virus(50, kind="enveloped", color="#5B8DB8", accent="#D9534F"), at=(200, 200), key="cov")',
    rank=19,
)
def virus(r=40, *, kind="enveloped", color="#5B8DB8", accent=None, spikes=None, fibers=False, style="rich", seed=2):
    rich = _check_style(style)
    if kind not in ("enveloped", "icosahedral", "phage"):
        raise ValueError('virus kind must be "enveloped", "icosahedral" or "phage"')
    _finite(r)
    if kind == "phage":
        return _phage(r, color=color, accent=accent, rich=rich)
    if kind == "icosahedral":
        return _icosahedral(r, color=color, accent=accent, fibers=fibers, rich=rich)
    accent = accent or _hue(color, 170, light=0.55)
    holder, defs = _el("g"), _el("defs")
    holder.append(defs)
    sp_len = r * 0.28
    R0 = r + sp_len
    c = R0
    env = _mix(color, "#000000", 0.3)
    env_t = max(2.0, r * 0.11)
    # spike glycoproteins: stalk + bulbous crown (S-protein like), drawn first so they sit behind the envelope rim
    n = spikes or max(8, min(28, int(2 * math.pi * r / max(5.5, r * 0.32))))
    stalks, crowns = [], []
    for i in range(n):
        a = 2 * math.pi * i / n + 0.13
        ca, sa = math.cos(a), math.sin(a)
        tx, ty = -sa, ca
        base = r - env_t * 0.3
        tip = r + sp_len * 0.62
        w = max(0.8, r * 0.035)
        stalks.append(
            _poly(
                [
                    (c + ca * base + tx * w, c + sa * base + ty * w),
                    (c + ca * tip + tx * w * 0.8, c + sa * tip + ty * w * 0.8),
                    (c + ca * tip - tx * w * 0.8, c + sa * tip - ty * w * 0.8),
                    (c + ca * base - tx * w, c + sa * base - ty * w),
                ]
            )
        )
        cr = sp_len * 0.38
        ccx, ccy = c + ca * (r + sp_len - cr), c + sa * (r + sp_len - cr)
        crowns.append(
            _circle_union(
                [
                    (
                        (
                            ccx + (tx * k * cr * 0.55) + ca * (abs(k) * -cr * 0.2),
                            ccy + (ty * k * cr * 0.55) + sa * (abs(k) * -cr * 0.2),
                        ),
                        cr * (0.62 if k else 0.72),
                    )
                    for k in (-1, 0, 1)
                ],
                samples=24,
            )
        )
    holder.append(
        _el(
            "circle",
            cx=c,
            cy=c,
            r=r,
            fill=_mix(color, "#FFFFFF", 0.55),
            stroke=env,
            stroke_width=max(1, r * 0.03),
            data_outline="1",
        )
    )
    holder.append(_el("path", d=" ".join(stalks), fill=_mix(accent, "#000000", 0.2)))
    holder.append(
        _el(
            "path",
            d=" ".join(crowns),
            fill=accent,
            stroke=_mix(accent, "#000000", 0.3) if rich else None,
            stroke_width=max(0.3, r * 0.012) if rich else None,
        )
    )
    # envelope (lipid bilayer ring, native) + matrix layer + interior
    holder.append(_el("circle", cx=c, cy=c, r=r - env_t / 2, fill="none", stroke=color, stroke_width=env_t))
    inner_r = r - env_t * 1.6
    holder.append(_el("circle", cx=c, cy=c, r=inner_r, fill=_mix(color, "#FFFFFF", 0.78)))
    # nucleocapsid: coiled RNP strand with N-protein beads
    rnd = random.Random(seed)
    coil = []
    turns = 3 if r >= 25 else 2
    m = 60
    for j in range(m + 1):
        t = j / m
        a = t * turns * 2 * math.pi
        rr = inner_r * (0.25 + 0.5 * t)
        coil.append((c + rr * math.cos(a) + inner_r * 0.08 * math.sin(7 * a), c + rr * math.sin(a) * 0.9))
    rna = _mix(accent, "#7A1F5C", 0.5)
    holder.append(
        _el(
            "path",
            d=_smooth(coil[::2]),
            fill="none",
            stroke=rna,
            stroke_width=max(0.8, r * 0.035),
            stroke_linecap="round",
        )
    )
    if r >= 18:
        beads = [_circ(x, y, max(1.0, r * 0.045)) for x, y in coil[1::5]]
        holder.append(_el("path", d=" ".join(beads), fill=_mix(color, "#000000", 0.25)))
    if rich:
        defs.append(_radial("vg", _mix(color, "#FFFFFF", 0.85), _mix(color, "#FFFFFF", 0.35), fx=0.36, fy=0.32))
        look = _look()
        look.append(_el("circle", cx=c, cy=c, r=inner_r, fill="url(#vg)", fill_opacity=0.85))
        # lipid heads along both leaflets of the envelope
        if r >= 16:
            hd = []
            hr = env_t * 0.2
            for rr in (r - hr * 1.1, r - env_t + hr * 1.1):
                k = max(12, int(2 * math.pi * rr / (hr * 2.3)))
                for i in range(k):
                    a = 2 * math.pi * i / k
                    hd.append(_circ(c + rr * math.cos(a), c + rr * math.sin(a), hr))
            look.append(_el("path", d=" ".join(hd), fill=_mix(color, "#FFFFFF", 0.3)))
        # membrane (M/E) proteins dotted under the envelope
        mp = []
        for i in range(int(r / 3)):
            a = rnd.uniform(0, 2 * math.pi)
            rr = r - env_t * 1.25
            mp.append(_circ(c + rr * math.cos(a), c + rr * math.sin(a), max(0.8, env_t * 0.32)))
        look.append(_el("path", d=" ".join(mp), fill=_mix(accent, "#FFFFFF", 0.2)))
        look.append(
            _el(
                "ellipse",
                cx=c - r * 0.38,
                cy=c - r * 0.45,
                rx=r * 0.3,
                ry=r * 0.16,
                fill="#FFFFFF",
                fill_opacity=0.45,
                transform=f"rotate(-35 {fmt(c - r * 0.38)} {fmt(c - r * 0.45)})",
            )
        )
        holder.append(look)
    return _finish(holder, defs, Box(0, 0, 2 * R0, 2 * R0))


def _icosahedral(r, *, color, accent, fibers, rich):
    """Non-enveloped capsid viewed down a 3-fold axis: 10 visible facets shaded by tilt, capsomere dots, optional fibres."""
    accent = accent or _mix(color, "#2A2A2A", 0.35)
    holder, defs = _el("g"), _el("defs")
    holder.append(defs)
    fl = r * 0.75 if fibers else 0
    c = r + fl + r * 0.12 * bool(fibers)
    outer, inner = _icosa_face(c, c, r)
    tri = [inner]
    for i, p in enumerate(inner):
        q = inner[(i + 1) % 3]
        mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
        tri.append([p, q, min(outer, key=lambda o: math.dist(o, (2 * mx - c, 2 * my - c)))])
    for i in range(6):
        a, b = outer[i], outer[(i + 1) % 6]
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        tri.append([a, b, min(inner, key=lambda p: math.dist(p, mid))])
    dark = _mix(color, "#000000", 0.35)
    if fibers:
        # adenovirus penton fibres: thin shaft from each vertex, slight kink, terminal knob
        shafts, knobs = [], []
        for x, y in outer:
            ux, uy = (x - c) / r, (y - c) / r
            px, py = -uy, ux
            k = (x + ux * fl * 0.55 + px * fl * 0.06, y + uy * fl * 0.55 + py * fl * 0.06)
            e = (x + ux * fl, y + uy * fl)
            shafts.append(f"M{fmt(x)} {fmt(y)} Q{fmt(k[0])} {fmt(k[1])} {fmt(e[0])} {fmt(e[1])}")
            knobs.append(_circ(e[0] + ux * r * 0.07, e[1] + uy * r * 0.07, r * 0.11))
        holder.append(
            _el(
                "path",
                d=" ".join(shafts),
                fill="none",
                stroke=accent,
                stroke_width=max(0.9, r * 0.045),
                stroke_linecap="round",
            )
        )
        holder.append(
            _el(
                "path",
                d=" ".join(knobs),
                fill=_mix(accent, "#FFFFFF", 0.25),
                stroke=_mix(accent, "#000000", 0.3),
                stroke_width=max(0.4, r * 0.015),
            )
        )
    holder.append(
        _el(
            "path",
            d=_poly(outer),
            fill=color,
            stroke=dark,
            stroke_width=max(1, r * 0.04),
            stroke_linejoin="round",
            data_outline="1",
        )
    )
    # facet shading by tilt: light toward upper-left, dark toward lower-right (native, so flat keeps the 3D read)
    light, shade = [], []
    for t in tri[1:]:
        gx, gy = sum(p[0] for p in t) / 3 - c, sum(p[1] for p in t) / 3 - c
        (light if gx * -0.6 + gy * -0.8 > r * 0.12 else shade if gx * -0.6 + gy * -0.8 < -r * 0.12 else []).append(
            _poly(t)
        )
    holder.append(_el("path", d=_poly(inner), fill=_mix(color, "#FFFFFF", 0.2)))
    holder.append(_el("path", d=" ".join(light), fill=_mix(color, "#FFFFFF", 0.38)))
    holder.append(_el("path", d=" ".join(shade), fill=_mix(color, "#000000", 0.2)))
    holder.append(
        _el(
            "path",
            d=" ".join(_poly(t) for t in tri),
            fill="none",
            stroke=dark,
            stroke_width=max(0.6, r * 0.022),
            stroke_linejoin="round",
        )
    )
    # capsomeres: triangular lattice of knobs on every facet (pentons at vertices drawn larger)
    n = 5 if r >= 30 else 4
    caps = []
    for (ax, ay), (bx, by), (qx, qy) in tri:
        for i in range(1, n - 1):
            for j in range(1, n - i):
                u, v, w = i / n, j / n, (n - i - j) / n
                caps.append(_circ(ax * u + bx * v + qx * w, ay * u + by * v + qy * w, r * (0.05 if n == 5 else 0.06)))
    holder.append(
        _el("path", d=" ".join(caps), fill=_mix(color, "#FFFFFF", 0.55), stroke=dark, stroke_width=max(0.3, r * 0.012))
    )
    holder.append(
        _el(
            "path",
            d=" ".join(_circ(x, y, r * 0.075) for x, y in outer + inner),
            fill=accent,
            stroke=_mix(accent, "#000000", 0.3),
            stroke_width=max(0.3, r * 0.012),
        )
    )
    if rich:
        defs.append(_radial("icg", "#FFFFFF", _mix(color, "#000000", 0.5), fx=0.32, fy=0.28))
        look = _look()
        look.append(_el("path", d=_poly(outer), fill="url(#icg)", fill_opacity=0.2))
        holder.append(look)
    return _finish(holder, defs, Box(0, 0, 2 * c, 2 * c))


def _phage(r, *, color, accent, rich):
    accent = accent or _mix(color, "#3A3A3A", 0.45)
    holder, defs = _el("g"), _el("defs")
    holder.append(defs)
    W = r * 2.4  # total width (tail fibers splay)
    cx = W / 2
    hy = r  # head centre
    outer, inner = _icosa_face(cx, hy, r)
    dark = _mix(color, "#000000", 0.3)
    holder.append(
        _el(
            "path",
            d=_poly(outer),
            fill=color,
            stroke=dark,
            stroke_width=max(1, r * 0.04),
            stroke_linejoin="round",
            data_outline="1",
        )
    )
    # icosahedral facets: inner triangle + spokes to outer vertices
    # connect each inner vertex to the two nearest outer vertices and the outer vertex between them
    fac = []
    for p in inner:
        near = sorted(range(6), key=lambda i: math.dist(p, outer[i]))[:3]
        for i in near:
            fac.append(f"M{fmt(p[0])} {fmt(p[1])} L{fmt(outer[i][0])} {fmt(outer[i][1])}")
    holder.append(
        _el(
            "path",
            d=_poly(inner) + " " + " ".join(fac),
            fill="none",
            stroke=dark,
            stroke_width=max(0.6, r * 0.022),
            stroke_linejoin="round",
        )
    )
    neck_y = hy + r
    cw = r * 0.55
    holder.append(_el("rect", x=cx - cw / 2, y=neck_y - r * 0.04, width=cw, height=r * 0.2, rx=r * 0.05, fill=accent))
    sh_y0, sh_y1 = neck_y + r * 0.16, neck_y + r * 2.3
    sw = r * 0.34
    tail_col = _mix(accent, "#FFFFFF", 0.2)
    holder.append(
        _el(
            "rect",
            x=cx - sw / 2,
            y=sh_y0,
            width=sw,
            height=sh_y1 - sh_y0,
            rx=sw * 0.15,
            fill=tail_col,
            stroke=_mix(accent, "#000000", 0.3),
            stroke_width=max(0.5, r * 0.02),
        )
    )
    rings = max(4, min(14, int((sh_y1 - sh_y0) / max(2.5, r * 0.15))))
    rd = " ".join(
        f"M{fmt(cx - sw / 2)} {fmt(sh_y0 + (sh_y1 - sh_y0) * (i + 0.5) / rings)} H{fmt(cx + sw / 2)}"
        for i in range(rings)
    )
    holder.append(
        _el("path", d=rd, fill="none", stroke=_mix(accent, "#000000", 0.35), stroke_width=max(0.5, r * 0.025))
    )
    bp_y = sh_y1
    bw = r * 0.85
    holder.append(
        _el(
            "path",
            d=_poly(
                [
                    (cx - bw / 2, bp_y),
                    (cx + bw / 2, bp_y),
                    (cx + bw * 0.38, bp_y + r * 0.16),
                    (cx - bw * 0.38, bp_y + r * 0.16),
                ]
            ),
            fill=accent,
        )
    )
    # tail fibers: kinked legs splayed out (3 per side, back pair lighter)
    legs_front, legs_back = [], []
    foot_y = bp_y + r * 1.25
    for side in (-1, 1):
        for j, (kx, fx, store) in enumerate(((0.45, 0.55, legs_back), (0.62, 0.98, legs_front), (0.3, 0.3, legs_back))):
            sx = cx + side * bw * 0.4
            knee = (cx + side * W * kx, bp_y + r * (0.55 + 0.12 * j))
            foot = (cx + side * W * fx * 0.5, foot_y - r * 0.1 * j)
            store.append(
                f"M{fmt(sx)} {fmt(bp_y + r * 0.1)} L{fmt(knee[0])} {fmt(knee[1])} L{fmt(foot[0])} {fmt(foot[1])}"
            )
    holder.append(
        _el(
            "path",
            d=" ".join(legs_back),
            fill="none",
            stroke=_mix(accent, "#FFFFFF", 0.35),
            stroke_width=max(0.8, r * 0.045),
            stroke_linecap="round",
            stroke_linejoin="round",
        )
    )
    holder.append(
        _el(
            "path",
            d=" ".join(legs_front),
            fill="none",
            stroke=accent,
            stroke_width=max(0.9, r * 0.055),
            stroke_linecap="round",
            stroke_linejoin="round",
        )
    )
    if rich:
        defs.append(
            _linear("phg", [("0", _mix(color, "#FFFFFF", 0.45)), ("1", _mix(color, "#000000", 0.2))], x2="1", y2="1")
        )
        look = _look()
        look.append(_el("path", d=_poly(outer), fill="url(#phg)", fill_opacity=0.6))
        look.append(
            _el(
                "path",
                d=_poly([outer[0], outer[1], inner[1]]) + " " + _poly([outer[0], inner[1], inner[2]]),
                fill="#FFFFFF",
                fill_opacity=0.28,
            )
        )
        look.append(_el("path", d=_poly([outer[3], outer[4], inner[0]]), fill="#000000", fill_opacity=0.12))
        dd = []
        for k in range(3):
            rr = r * (0.2 + 0.18 * k)
            dd.append(_circ(cx + r * 0.05, hy + r * 0.05, rr))
        look.append(
            _el(
                "path",
                d=" ".join(dd),
                fill="none",
                stroke=_mix(color, "#FFFFFF", 0.55),
                stroke_width=max(0.5, r * 0.02),
                stroke_opacity=0.45,
            )
        )
        look.append(
            _el(
                "rect",
                x=cx - sw / 2 + sw * 0.14,
                y=sh_y0 + 1,
                width=sw * 0.2,
                height=sh_y1 - sh_y0 - 2,
                rx=sw * 0.1,
                fill="#FFFFFF",
                fill_opacity=0.35,
            )
        )
        holder.append(look)
    lw = max(0.9, r * 0.055)
    top = hy - r
    return _finish(
        holder,
        defs,
        Box(cx - W / 2 - lw, top - 1, W + 2 * lw, foot_y + lw - top + 1),
        head=(cx, top),
        tail=(cx, bp_y + r * 0.16),
    )


_TRANSPORTERS = ("channel", "pump", "antiporter", "symporter", "abc", "aquaporin")
_TP_COLOR = {
    "channel": "#2E8B57",
    "pump": "#C0605A",
    "antiporter": "#3A7FC1",
    "symporter": "#7A5BB0",
    "abc": "#5B4BA8",
    "aquaporin": "#2A8FB8",
}


def _tp_text(x, y, s, fs, fill, anchor="middle", bold=True):
    t = _el("text", x=x, y=y, font_size=fs, fill=fill, text_anchor=anchor, font_weight="bold" if bold else None)
    t.text = str(s)
    from ._geometry import label

    w = label(str(s), font_size=fs, font_weight="bold" if bold else "normal").bounds.width
    x0 = x - (w / 2 if anchor == "middle" else w if anchor == "end" else 0)
    return t, Box(x0, y - fs * 0.92, w, fs * 1.2)


def _tp_arrow(x, y0, y1, color, sw):
    """Short vertical arrow from y0 to y1 (head at y1) as native line + head."""
    s = 1 if y1 > y0 else -1
    hl, hw = sw * 3.2, sw * 2.4
    shaft = _el(
        "path",
        d=f"M{fmt(x)} {fmt(y0)} V{fmt(y1 - s * hl * 0.8)}",
        fill="none",
        stroke=color,
        stroke_width=sw,
        stroke_linecap="round",
    )
    head = _el("path", d=_poly([(x - hw, y1 - s * hl), (x, y1), (x + hw, y1 - s * hl)]), fill=color, stroke="none")
    return shaft, head


def _helices(x0, x1, y0, y1, n, color, rich, *, gap=1.0, wave=0.0, edge=None):
    """Row of n rounded transmembrane helix rods between x0..x1 (merged into two alternating paths)."""
    w = (x1 - x0 - gap * (n - 1)) / n
    a, b = [], []
    for k in range(n):
        x = x0 + k * (w + gap)
        lift = wave * math.sin(k * 1.7)
        h = y1 - y0
        r = w / 2
        (a if k % 2 == 0 else b).append(
            f"M{fmt(x + r)} {fmt(y0 + lift)} A{fmt(r)} {fmt(r)} 0 0 1 {fmt(x + w)} {fmt(y0 + lift + r)} "
            f"V{fmt(y0 + lift + h - r)} A{fmt(r)} {fmt(r)} 0 0 1 {fmt(x)} {fmt(y0 + lift + h - r)} "
            f"V{fmt(y0 + lift + r)} A{fmt(r)} {fmt(r)} 0 0 1 {fmt(x + r)} {fmt(y0 + lift)} Z"
        )
    e = edge or _mix(color, "#000000", 0.38)
    out = [_el("path", d=" ".join(a), fill=color, stroke=e, stroke_width=0.8)]
    if b:
        out.append(_el("path", d=" ".join(b), fill=_mix(color, "#FFFFFF", 0.28), stroke=e, stroke_width=0.8))
    return out, w


@_drawing_api(
    "parts",
    purpose="膜转运蛋白（教科书级，单个跨膜蛋白）：离子通道、P 型 ATP 酶泵、反向/同向转运体、ABC 转运体、水通道蛋白；立在任意膜上。",
    returns="Geometry（原点在中心；端口 out 胞外侧/in 胞质侧/center 膜中线/tail(=center，供 mount)；载体另有 ion_out{k}/ion_in{k}；pump/abc 另有 atp）",
    semantics=(
        'kind："channel" 两亚基夹一条贯穿孔道（中部选择性滤器收窄）；"pump" P 型 ATP 酶：跨膜螺旋束 + 胞质侧 A/P/N 结构域头部，'
        'atp=True 在 N 域旁写 ATP → ADP + Pi；"antiporter"/"symporter" 双叶载体（N/C 两半围成中央腔），两条小箭头反向/同向穿过，'
        'ions=("Na⁺", "H⁺") 标在箭头起点；"abc" 两个 TMD + 胞质侧两个 NBD 夹 ATP；"aquaporin" 沙漏形孔道 + 单列水分子 + NPA 收窄。',
        'direction="in"（默认）第一种离子由胞外进入胞质，"out" 反之；antiporter 第二种离子方向相反，symporter 相同；'
        'pump 的离子（ions[0]，默认无）按 direction 方向被泵过膜（质膜 H⁺-ATP 酶：ions=("H⁺",), direction="out"）。',
        "竖直放置，out（胞外/腔侧）朝上；flip=True 让 out 朝下（文字保持正立），用于画在胞质下方的液泡膜/类囊体膜；membrane_thickness 与所在膜厚度一致，跨膜段按它缩放（默认 22）。",
        '立在细胞上：d.mount(transporter(...), on=c.contour_at(t, normal="outward"), inset=膜厚/2)（tail 是膜中线；普通 cell 轮廓是膜外表面，'
        'cell(kind="plant") 的轮廓已是膜中线，inset=0；其液泡膜是 subpath=1，normal="left" 让 out 朝向液泡腔）；'
        "立在 membrane(path) 上：d.place(transporter(...), at=膜中线上的点) 即可（membrane 默认把 out 画在路径上方时）。",
        'color 为主色；style="rich" 加螺旋高光（局部 SVG），"flat" 全原生。',
    ),
    example='c = d.place(cell(150, kind="plant"), at=(300, 240), key="c")\n'
    'd.mount(transporter("antiporter", ions=("Na⁺", "H⁺"), direction="out", membrane_thickness=13), on=c.contour_at(0.1, normal="outward"))  # 质膜；液泡膜用 subpath=1, normal="left"\n'
    'd.place(transporter("pump", ions=("H⁺",), direction="out", atp=True), at=(200, 200), anchor="tail")  # 立在 membrane(path) 的膜线上',
    rank=3,
)
def transporter(
    kind="channel",
    *,
    ions=(),
    direction="in",
    atp=False,
    color=None,
    membrane_thickness=22,
    font_size=11,
    flip=False,
    style="rich",
):
    if kind not in _TRANSPORTERS:
        raise ValueError(f"transporter kind must be one of {list(_TRANSPORTERS)}")
    if direction not in ("in", "out"):
        raise ValueError('direction must be "in" or "out"')
    rich = _check_style(style)
    T = float(membrane_thickness)
    _finite(T, font_size)
    if T <= 0:
        raise ValueError("membrane_thickness must be positive")
    ions = tuple(ions) if not isinstance(ions, str) else (ions,)
    color = color or _TP_COLOR[kind]
    e = _mix(color, "#000000", 0.38)
    fs = float(font_size)
    s = max(T, 14.0) / 22.0  # scale of everything except text
    ht = max(T * 0.72, 13 * s)  # half height of the transmembrane part
    holder, defs = _el("g"), _el("defs")
    holder.append(defs)
    boxes = []
    texts = []
    ports = {}
    look = _look() if rich else None
    ion_col = _mix(color, "#000000", 0.55)
    if kind == "channel":
        sub_w, gap = 15 * s, 6.5 * s
        body = []
        for sx in (-1, 1):
            xa, xb = sx * gap / 2, sx * (gap / 2 + sub_w)
            # subunit: slightly bulged slab, narrower toward the pore at mid-depth (selectivity filter)
            inner = xa + sx * 2.2 * s
            pts = [
                (xa, -ht),
                (xb, -ht * 0.96),
                (xb + sx * 1.5 * s, 0),
                (xb, ht * 0.96),
                (xa, ht),
                (xa - sx * 0.2 * s, ht * 0.4),
                (inner - sx * 3.0 * s, 0),
                (xa - sx * 0.2 * s, -ht * 0.4),
            ]
            body.append(_smooth(pts, closed=True))
        holder.append(_el("path", d=" ".join(body), fill=color, stroke=e, stroke_width=0.9, data_outline="1"))
        stripes = []
        for sx in (-1, 1):
            for k in (1, 2):
                x = sx * (gap / 2 + sub_w * k / 3 + 1.2 * s)
                stripes.append(f"M{fmt(x)} {fmt(-ht + 3 * s)} V{fmt(ht - 3 * s)}")
        holder.append(
            _el(
                "path",
                d=" ".join(stripes),
                fill="none",
                stroke=_mix(color, "#000000", 0.25),
                stroke_width=0.7 * s,
                stroke_opacity=0.8,
            )
        )
        if look is not None:
            look.append(
                _el(
                    "path",
                    d=" ".join(
                        f"M{fmt(sx * (gap / 2 + sub_w * 0.2))} {fmt(-ht + 4 * s)} V{fmt(ht * 0.2)}" for sx in (-1, 1)
                    ),
                    stroke="#FFFFFF",
                    stroke_width=2.2 * s,
                    stroke_opacity=0.45,
                    stroke_linecap="round",
                )
            )
        half_w = gap / 2 + sub_w + 1.5 * s
        top, bot = -ht, ht
        if ions:
            holder.append(
                _el(
                    "circle",
                    cx=0,
                    cy=0,
                    r=2.6 * s,
                    fill="#F2C14E",
                    stroke=_mix("#F2C14E", "#000000", 0.4),
                    stroke_width=0.6,
                )
            )
            a, h = _tp_arrow(
                0,
                -ht - 2 * s if direction == "in" else ht + 2 * s,
                ht + 9 * s if direction == "in" else -ht - 9 * s,
                ion_col,
                1.5 * s,
            )
            holder.extend((a, h))
            src = -ht - 6 * s if direction == "in" else ht + 6 * s + fs * 0.8
            t, b = _tp_text(half_w + 2, src, ions[0], fs, ion_col, "start")
            texts.append((t, b))
            boxes.append(b)
            top, bot = min(top, -ht - 9 * s), max(bot, ht + 9 * s)
        ports.update(pore=(0, 0))
    elif kind == "aquaporin":
        n, hw = 6, 5.2 * s
        half_w = n / 2 * (hw + 1) + 6 * s
        body = []
        # hourglass monomer: outer vestibules wide, narrow NPA constriction at the midplane
        pts_l = [
            (-half_w, -ht),
            (-4.5 * s, -ht),
            (-1.4 * s, -ht * 0.25),
            (-1.4 * s, ht * 0.25),
            (-4.5 * s, ht),
            (-half_w, ht),
            (-half_w - 1.5 * s, 0),
        ]
        body.append(_smooth(pts_l, closed=True))
        body.append(_smooth([(-x, y) for x, y in pts_l][::-1], closed=True))
        holder.append(_el("path", d=" ".join(body), fill=color, stroke=e, stroke_width=0.9, data_outline="1"))
        rods = []
        for sx in (-1, 1):
            for k in range(3):
                x = sx * (5 * s + k * (hw + 1.2 * s) + hw / 2)
                ins = 2.5 * s if k == 0 else 1.5 * s
                rods.append(f"M{fmt(x)} {fmt(-ht + ins)} V{fmt(ht - ins)}")
        holder.append(
            _el("path", d=" ".join(rods), fill="none", stroke=_mix(color, "#000000", 0.22), stroke_width=0.8 * s)
        )
        # two half-helices meeting at the NPA motifs
        holder.append(
            _el(
                "path",
                d=" ".join(
                    f"M{fmt(sx * 2.6 * s)} {fmt(-ht * 0.62 * sy)} L{fmt(sx * 2.2 * s)} {fmt(-1.6 * s * sy)}"
                    for sx in (-1, 1)
                    for sy in (-1, 1)
                ),
                fill="none",
                stroke="#E8B54A",
                stroke_width=1.6 * s,
                stroke_linecap="round",
            )
        )
        wm = []
        hs = []
        for k in range(5):
            y = -ht - 2 * s + k * (2 * ht + 4 * s) / 4
            wm.append(_circ(0, y, 2.0 * s))
            hs.append(_circ(-2.1 * s, y + 1.2 * s, 1.1 * s))
            hs.append(_circ(2.1 * s, y + 1.2 * s, 1.1 * s))
        holder.append(_el("path", d=" ".join(hs), fill="#FFFFFF", stroke="#7A8A99", stroke_width=0.4))
        holder.append(
            _el("path", d=" ".join(wm), fill="#D9483B", stroke=_mix("#D9483B", "#000000", 0.35), stroke_width=0.4)
        )
        if look is not None:
            look.append(
                _el(
                    "path",
                    d=f"M{fmt(-half_w + 3 * s)} {fmt(-ht + 4 * s)} V{fmt(ht * 0.3)}",
                    stroke="#FFFFFF",
                    stroke_width=2.4 * s,
                    stroke_opacity=0.4,
                    stroke_linecap="round",
                )
            )
        top, bot = -ht - 4 * s, ht + 4 * s
        if ions:
            t, b = _tp_text(4 * s, -ht - 5 * s, ions[0], fs, ion_col, "start")
            texts.append((t, b))
            boxes.append(b)
        ports.update(pore=(0, 0))
    elif kind in ("antiporter", "symporter"):
        lobe_w = 17 * s
        hh = ht * 1.08
        half_w = 2 * lobe_w * 0.92
        body = []
        for sx in (-1, 1):
            # each lobe (N- / C-domain, 6 helices) tilts so the two lobes enclose a central cavity
            pts = [
                (sx * 1.2 * s, -hh * 0.88),
                (sx * lobe_w * 0.9, -hh),
                (sx * lobe_w * 1.82, -hh * 0.7),
                (sx * lobe_w * 1.86, hh * 0.55),
                (sx * lobe_w * 1.3, hh),
                (sx * 2.4 * s, hh * 0.9),
                (sx * 4.6 * s, 0),
            ]
            body.append(_smooth(pts if sx < 0 else pts[::-1], closed=True))
        holder.append(_el("path", d=" ".join(body), fill=color, stroke=e, stroke_width=0.9, data_outline="1"))
        hel = []
        for sx in (-1, 1):
            for k in range(3):
                x = sx * (lobe_w * (0.55 + k * 0.42))
                hel.append(f"M{fmt(x - sx * 1.5 * s)} {fmt(-hh * 0.78)} L{fmt(x + sx * 1.5 * s)} {fmt(hh * 0.78)}")
        holder.append(
            _el(
                "path",
                d=" ".join(hel),
                fill="none",
                stroke=_mix(color, "#000000", 0.22),
                stroke_width=0.8 * s,
                stroke_opacity=0.8,
            )
        )
        if look is not None:
            look.append(
                _el(
                    "path",
                    d=" ".join(
                        f"M{fmt(sx * lobe_w * 1.45)} {fmt(-hh * 0.6)} Q{fmt(sx * lobe_w * 1.6)} 0 "
                        f"{fmt(sx * lobe_w * 1.4)} {fmt(hh * 0.4)}"
                        for sx in (-1, 1)
                    ),
                    fill="none",
                    stroke="#FFFFFF",
                    stroke_width=2.4 * s,
                    stroke_opacity=0.4,
                    stroke_linecap="round",
                )
            )
        # two ion lanes through the protein; antiporter → opposite, symporter → same direction
        dirs = [direction, direction if kind == "symporter" else ("out" if direction == "in" else "in")]
        lane_x = (-lobe_w * 0.95, lobe_w * 0.95)
        reach = hh + 10 * s
        top, bot = -reach, reach
        lane_cols = (_mix(color, "#000000", 0.6), "#B5462E")
        for k, (lx, dk) in enumerate(zip(lane_x, dirs)):
            y0, y1 = (-reach, reach) if dk == "in" else (reach, -reach)
            a, h = _tp_arrow(lx, y0, y1, lane_cols[k], 1.6 * s)
            holder.extend((a, h))
            ports[f"ion_out{k}"] = (lx, -reach - 2 * s)
            ports[f"ion_in{k}"] = (lx, reach + 2 * s)
            if k < len(ions) and ions[k]:
                anc = "end" if k == 0 else "start"
                tx = lx - 3 * s if k == 0 else lx + 3 * s
                ty = (-reach + fs * 0.55) if dk == "in" else (reach + fs * 0.1)
                t, b = _tp_text(tx, ty, ions[k], fs, lane_cols[k], anc)
                texts.append((t, b))
                boxes.append(b)
        ports.update(cavity=(0, 0))
    elif kind == "pump":
        # P-type ATPase: 10-helix TM domain (shown as 5 rods) + stalk + cytoplasmic headpiece (A, P, N domains)
        tm_w = 30 * s
        rods, _ = _helices(-tm_w / 2, tm_w / 2, -ht, ht, 5, color, rich, gap=1.0 * s, wave=1.2 * s)
        holder.append(
            _el(
                "path",
                d=_smooth(
                    [
                        (-tm_w / 2 - 1, -ht - 1),
                        (tm_w / 2 + 1, -ht - 1),
                        (tm_w / 2 + 2.5 * s, 0),
                        (tm_w / 2 + 1, ht + 1),
                        (-tm_w / 2 - 1, ht + 1),
                        (-tm_w / 2 - 2.5 * s, 0),
                    ],
                    closed=True,
                ),
                fill=_mix(color, "#FFFFFF", 0.55),
                stroke="none",
                data_outline="1",
            )
        )
        holder.extend(rods)
        stalk_b = ht + 7 * s
        holder.append(
            _el(
                "rect",
                x=-6 * s,
                y=ht - 1,
                width=12 * s,
                height=stalk_b - ht + 2,
                rx=3 * s,
                fill=_mix(color, "#FFFFFF", 0.2),
                stroke=e,
                stroke_width=0.8,
            )
        )
        pc = _mix(color, "#E0A458", 0.35)  # P domain
        ac = _mix(color, "#7A9CC6", 0.45)  # A domain
        nc = _mix(color, "#E0A458", 0.7)  # N domain
        P = (2 * s, stalk_b + 9 * s)
        A = (-15 * s, stalk_b + 5 * s)
        N = (14 * s, stalk_b + 18 * s)
        holder.append(
            _el(
                "ellipse",
                cx=A[0],
                cy=A[1],
                rx=10 * s,
                ry=8 * s,
                fill=ac,
                stroke=_mix(ac, "#000000", 0.38),
                stroke_width=0.9,
            )
        )
        holder.append(
            _el(
                "ellipse",
                cx=N[0],
                cy=N[1],
                rx=11 * s,
                ry=9.5 * s,
                fill=nc,
                stroke=_mix(nc, "#000000", 0.38),
                stroke_width=0.9,
            )
        )
        holder.append(
            _el(
                "ellipse",
                cx=P[0],
                cy=P[1],
                rx=12 * s,
                ry=8.5 * s,
                fill=pc,
                stroke=_mix(pc, "#000000", 0.38),
                stroke_width=0.9,
            )
        )
        # bound ATP in the N-domain cleft (adenine + three phosphates)
        ax, ay = N[0] + 3 * s, N[1] + 3 * s
        holder.append(
            _el(
                "path",
                d=" ".join(_circ(ax - 3.4 * s + k * 2.6 * s, ay - k * 1.2 * s, 1.5 * s) for k in range(3)),
                fill="#F2C14E",
                stroke=_mix("#F2C14E", "#000000", 0.45),
                stroke_width=0.5,
            )
        )
        if look is not None:
            for cx, cy, r in (
                (A[0] - 3 * s, A[1] - 3 * s, 3.4 * s),
                (P[0] - 4 * s, P[1] - 3 * s, 3.6 * s),
                (N[0] - 4 * s, N[1] - 3.5 * s, 3.8 * s),
            ):
                look.append(_el("circle", cx=cx, cy=cy, r=r, fill="#FFFFFF", fill_opacity=0.4))
        half_w = max(tm_w / 2 + 2.5 * s, 25 * s)
        top, bot = -ht - 1, N[1] + 9.5 * s
        ports["atp"] = (ax, ay)
        sub = fs * 0.82
        for lab, (cx, cy) in (("A", A), ("P", P), ("N", N)):
            t, b = _tp_text(
                cx - (2.5 * s if lab == "N" else 0),
                cy + sub * 0.35 - (1.5 * s if lab == "N" else 0),
                lab,
                sub,
                _mix(color, "#000000", 0.55),
            )
            texts.append((t, b))
        if atp:
            t, b = _tp_text(
                N[0] + 13 * s, N[1] + 2 * s + fs * 0.35, "ATP → ADP + Pi", fs, _mix(nc, "#000000", 0.55), "start"
            )
            texts.append((t, b))
            boxes.append(b)
        if ions:
            y0, y1 = (-ht - 12 * s, ht * 0.2) if direction == "in" else (ht * 0.2, -ht - 12 * s)
            a, h = _tp_arrow(-tm_w * 0.12, y0, y1, "#B5462E", 1.7 * s)
            holder.extend((a, h))
            t, b = _tp_text(
                -tm_w / 2 - 3 * s, -ht - 4 * s if direction == "out" else -ht - 6 * s, ions[0], fs, "#B5462E", "end"
            )
            texts.append((t, b))
            boxes.append(b)
            top = min(top, -ht - 12 * s)
            ports["ion_out0"], ports["ion_in0"] = (-tm_w * 0.12, -ht - 13 * s), (-tm_w * 0.12, ht)
    else:  # abc
        tmd_w = 19 * s
        body = []
        for sx in (-1, 1):
            x0, x1 = sorted((sx * 1.0 * s, sx * (1 * s + tmd_w)))
            body.append(
                _smooth(
                    [(x0, -ht - 1), (x1, -ht - 1), (x1 + sx * 1.5 * s, 0), (x1, ht + 6 * s), (x0, ht + 6 * s)],
                    closed=True,
                )
            )
        holder.append(_el("path", d=" ".join(body), fill=_mix(color, "#FFFFFF", 0.5), stroke="none", data_outline="1"))
        for sx in (-1, 1):
            x0, x1 = sorted((sx * 1.6 * s, sx * (1 * s + tmd_w)))
            rods, _ = _helices(x0, x1, -ht, ht + 6 * s, 3, color, rich, gap=0.8 * s)
            holder.extend(rods)
        nbd = _mix(color, "#E0A458", 0.55)
        ny = ht + 6 * s + 10 * s
        for sx in (-1, 1):
            holder.append(
                _el(
                    "ellipse",
                    cx=sx * 11 * s,
                    cy=ny,
                    rx=12 * s,
                    ry=9.5 * s,
                    fill=nbd,
                    stroke=_mix(nbd, "#000000", 0.38),
                    stroke_width=0.9,
                )
            )
        ax, ay = 0, ny
        holder.append(
            _el(
                "path",
                d=_circ(-2.8 * s, ay, 2.7 * s) + " " + _circ(2.8 * s, ay, 2.7 * s),
                fill="#F2C14E",
                stroke=_mix("#F2C14E", "#000000", 0.45),
                stroke_width=0.6,
            )
        )
        if look is not None:
            look.append(
                _el(
                    "path",
                    d=" ".join(_circ(sx * 11 * s - 4 * s, ny - 3.5 * s, 3.4 * s) for sx in (-1, 1)),
                    fill="#FFFFFF",
                    fill_opacity=0.4,
                )
            )
        half_w = tmd_w + 2.5 * s
        top, bot = -ht - 1, ny + 9.5 * s
        ports["atp"] = (ax, ay)
        if atp:
            t, b = _tp_text(half_w + 3 * s, ny + fs * 0.35, "ATP → ADP + Pi", fs, _mix(nbd, "#000000", 0.55), "start")
            texts.append((t, b))
            boxes.append(b)
        if ions:
            y0, y1 = (-ht - 12 * s, ht * 0.3) if direction == "in" else (ht * 0.3, -ht - 12 * s)
            a, h = _tp_arrow(0, y0, y1, "#B5462E", 1.7 * s)
            holder.extend((a, h))
            t, b = _tp_text(-4 * s, -ht - 5 * s, ions[0], fs, "#B5462E", "end")
            texts.append((t, b))
            boxes.append(b)
            top = min(top, -ht - 12 * s)
            ports["ion_out0"], ports["ion_in0"] = (0, -ht - 13 * s), (0, ht)
    if look is not None and len(look):
        holder.append(look)
    ports.update(out=(0, top - 1), **{"in": (0, bot + 1)}, tail=(0, 0), center=(0, 0))
    if flip:
        # out side faces down (organelle lumen below the cytoplasm); text stays upright, only its position mirrors
        shapes = _el("g", transform="scale(1 -1)")
        shapes.extend(list(holder))
        holder = _el("g")
        holder.append(defs)
        if defs in list(shapes):
            shapes.remove(defs)
        holder.append(shapes)
        for t, b in texts:
            base = float(t.get("y")) - b.y  # baseline offset inside the text box
            t.set("y", fmt(-(b.y + b.height) + base))
        boxes = [Box(b.x, -(b.y + b.height), b.width, b.height) for b in boxes]
        top, bot = -bot, -top
        ports = {k: (x, -y) for k, (x, y) in ports.items()}
    holder.extend(t for t, _ in texts)
    from ._geometry import _union

    bounds = _union([Box(-half_w, top - 1, 2 * half_w, bot - top + 2)] + boxes)
    if not len(defs):
        holder.remove(defs)
    return _with_edges(Geometry(holder, bounds), **ports)


def _closed_normals(pts):
    """Outward unit normals of a closed polyline whose angle increases on screen (y down → clockwise)."""
    n = len(pts)
    out = []
    for i in range(n):
        a, b = pts[i - 1], pts[(i + 1) % n]
        tx, ty = b[0] - a[0], b[1] - a[1]
        L = math.hypot(tx, ty) or 1.0
        out.append((ty / L, -tx / L))
    return out


def _resample(pts, n):
    """Closed polyline resampled to n points evenly spaced by arc length."""
    seg = [math.dist(pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts))]
    total = sum(seg)
    out, acc, i = [], 0.0, 0
    for k in range(n):
        target = total * k / n
        while acc + seg[i] < target:
            acc += seg[i]
            i += 1
        t = (target - acc) / (seg[i] or 1)
        a, b = pts[i], pts[(i + 1) % len(pts)]
        out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return out


def _plant_outline(rx, ry, seed, n=360):
    """Rounded, slightly irregular rectangular polygon filling (0,0)-(2rx,2ry); starts mid-right, angle increasing."""
    rnd = random.Random(seed)
    base = [(1, -0.08), (0.985, 0.9), (0.3, 1), (-0.92, 0.97), (-1, 0.12), (-0.97, -0.93), (0.18, -1), (0.94, -0.96)]
    vs = [(u + rnd.uniform(-0.025, 0.025), v + rnd.uniform(-0.025, 0.025)) for u, v in base]
    for _ in range(4):  # Chaikin: rounded corners, straight-ish walls
        nv = []
        for i in range(len(vs)):
            a, b = vs[i], vs[(i + 1) % len(vs)]
            nv += [
                (a[0] * 0.78 + b[0] * 0.22, a[1] * 0.78 + b[1] * 0.22),
                (a[0] * 0.22 + b[0] * 0.78, a[1] * 0.22 + b[1] * 0.78),
            ]
        vs = nv
    ux0, ux1 = min(u for u, _ in vs), max(u for u, _ in vs)
    vy0, vy1 = min(v for _, v in vs), max(v for _, v in vs)
    pts = [((u - ux0) / (ux1 - ux0) * 2 * rx, (v - vy0) / (vy1 - vy0) * 2 * ry) for u, v in vs]
    pts = _resample(pts, n)
    k = min(range(n), key=lambda i: abs(pts[i][1] - ry) if pts[i][0] > rx else 1e9)
    pts = pts[k:] + pts[:k]
    if _signed_area_pts(pts) < 0:
        pts = [pts[0]] + pts[1:][::-1]
    return pts


def _signed_area_pts(pts):
    return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(pts, pts[1:] + pts[:1])) / 2


def _offset_closed(pts, d):
    ns = _closed_normals(pts)
    ds = d if isinstance(d, (list, tuple)) else [d] * len(pts)
    return [(p[0] + nx * k, p[1] + ny * k) for p, (nx, ny), k in zip(pts, ns, ds)]


def _chloroplast(cx, cy, L, W, ang, color, rich):
    """Lens-shaped chloroplast: double envelope, stroma, grana stacks joined by stroma lamellae."""
    g = _el("g", transform=f"translate({fmt(cx)} {fmt(cy)}) rotate({fmt(ang)})")
    edge = _mix(color, "#000000", 0.4)
    g.append(
        _el(
            "ellipse",
            cx=0,
            cy=0,
            rx=L / 2,
            ry=W / 2,
            fill=_mix(color, "#FFFFFF", 0.45),
            stroke=edge,
            stroke_width=max(0.6, W * 0.07),
        )
    )
    if W >= 6:
        g.append(
            _el(
                "ellipse",
                cx=0,
                cy=0,
                rx=L / 2 - W * 0.1,
                ry=W / 2 - W * 0.1,
                fill="none",
                stroke=_mix(color, "#000000", 0.2),
                stroke_width=max(0.35, W * 0.03),
            )
        )
        g.append(
            _el(
                "path",
                d=f"M{fmt(-L * 0.4)} {fmt(-W * 0.05)} L{fmt(L * 0.4)} {fmt(W * 0.05)}",
                fill="none",
                stroke=_mix(color, "#000000", 0.1),
                stroke_width=max(0.4, W * 0.05),
            )
        )
        ng = 4 if L / W > 2.2 else 3
        gw, gh = L * 0.13, W * 0.52
        stacks, discs = [], []
        for k in range(ng):
            x = -L * 0.3 + L * 0.6 * k / max(1, ng - 1) - gw / 2
            y = -gh / 2 + W * 0.05 * (k / max(1, ng - 1) * 2 - 1)
            stacks.append(f"M{fmt(x)} {fmt(y)} h{fmt(gw)} v{fmt(gh)} h{fmt(-gw)} Z")
            for j in range(1, 4):
                discs.append(f"M{fmt(x)} {fmt(y + gh * j / 4)} h{fmt(gw)}")
        g.append(_el("path", d=" ".join(stacks), fill=_mix(color, "#000000", 0.18), stroke="none"))
        g.append(
            _el(
                "path",
                d=" ".join(discs),
                fill="none",
                stroke=_mix(color, "#FFFFFF", 0.5),
                stroke_width=max(0.3, W * 0.035),
            )
        )
        if rich:
            g.append(
                _el(
                    "ellipse",
                    cx=L * 0.18,
                    cy=W * 0.22,
                    rx=W * 0.2,
                    ry=W * 0.13,
                    fill="#FFFFFF",
                    fill_opacity=0.85,
                    stroke=_mix(color, "#000000", 0.15),
                    stroke_width=0.3,
                )
            )  # starch grain
    return g


def _plant_cell(rx, ry, *, fill, membrane, nucleus, style, seed, wall):
    from ._geometry import Curve

    rich = style == "rich"
    m = min(rx, ry)
    T = max(8.0, m * 0.07)  # plasma membrane / tonoplast bilayer thickness (contour = midline)
    tw = max(7.0, m * 0.1)  # cellulose wall
    wall = wall or "#D9E6BF"
    lamella = _mix(wall, "#5E6B2E", 0.55)
    vac_c = "#E4EFF6"
    chl_c = "#4E9A43"
    nuc_fill = nucleus or _mix(membrane, "#FFFFFF", 0.55)
    N = 360
    outer = _plant_outline(rx, ry, seed, N)
    pm = _resample(_offset_closed(outer, -(tw + T / 2)), N)
    pm_n = _closed_normals(pm)
    cyt = max(3.0, m * 0.04)
    items = []
    i_nuc = int(N * 0.53)
    nl, nw = m * 0.46, m * 0.27
    items.append((i_nuc, nl, nw, "nucleus"))
    per = N / max(1, round(sum(math.dist(pm[i], pm[(i + 1) % N]) for i in range(N)) / (m * 0.44)))
    k = 0
    pos = per * 0.5
    while pos < N - 1:
        i = int(pos) % N
        dist_nuc = min(abs(i - i_nuc), N - abs(i - i_nuc))
        if dist_nuc > N * 0.085:
            if k % 3 == 2:
                items.append((i, m * 0.15, m * 0.07, "mito"))
            else:
                items.append((i, m * 0.26, m * 0.11, "chloroplast"))
            k += 1
        pos += per
    # vacuole depth profile: thin cytoplasm except where an organelle pushes the tonoplast inward
    arc = sum(math.dist(pm[i], pm[(i + 1) % N]) for i in range(N)) / N
    depth = [T + cyt] * N
    for i0, L, Wd, kind in items:
        need = T / 2 + 2.2 + Wd + 2.5 + T / 2
        half = (L / 2 + 4) / arc
        for j in range(-int(half * 1.8), int(half * 1.8) + 1):
            t = abs(j) / half
            w = 1.0 if t <= 1 else max(0.0, 0.5 + 0.5 * math.cos(math.pi * min(1.0, (t - 1) / 0.8)))
            idx = (i0 + j) % N
            depth[idx] = max(depth[idx], T + cyt + (need - T - cyt) * w)
    for _ in range(3):
        depth = [(depth[i - 1] + 2 * depth[i] + depth[(i + 1) % N]) / 4 for i in range(N)]
    tono = _offset_closed(pm, [-d for d in depth])
    tono = _resample(
        [
            (
                sum(tono[(i + j) % N][0] for j in (-2, -1, 0, 1, 2)) / 5,
                sum(tono[(i + j) % N][1] for j in (-2, -1, 0, 1, 2)) / 5,
            )
            for i in range(N)
        ],
        N,
    )

    holder, defs = _el("g"), _el("defs")
    holder.append(defs)
    band = _mix(membrane, "#FFFFFF", 0.72)
    # 1. native outline: plasma-membrane midline (subpath 0) + tonoplast midline (subpath 1), both clockwise
    holder.append(
        _el("path", d=_poly(pm) + " " + _poly(tono), fill=fill, stroke=band, stroke_width=T, data_outline="1")
    )
    # 2. vacuole lumen
    vac = _offset_closed(tono, -T / 2)
    holder.append(_el("path", d=_poly(vac), fill=vac_c, stroke="none"))
    # 3. cellulose wall: ring from the outer face (middle lamella) to the plasma membrane
    pm_out = _offset_closed(pm, T / 2)
    holder.append(
        _el("path", d=_poly(outer) + " " + _poly(pm_out[::-1]), fill=wall, stroke="none", fill_rule="evenodd")
    )
    holder.append(_el("path", d=_poly(outer), fill="none", stroke=lamella, stroke_width=max(1.2, tw * 0.2)))
    # plasmodesmata: plasma-membrane-lined channels through the wall with a central desmotubule
    pd, dt, pd_pts = [], [], []
    for f in (0.08, 0.3, 0.7, 0.9):
        i = int(N * f)
        (x, y), (nx, ny) = pm_out[i], pm_n[i]
        tx, ty = -ny, nx
        r = max(1.4, tw * 0.17)
        a0, a1 = (x - nx * 0.5, y - ny * 0.5), (x + nx * (tw + 0.5), y + ny * (tw + 0.5))
        pd.append(
            _poly(
                [
                    (a0[0] - tx * r, a0[1] - ty * r),
                    (a1[0] - tx * r, a1[1] - ty * r),
                    (a1[0] + tx * r, a1[1] + ty * r),
                    (a0[0] + tx * r, a0[1] + ty * r),
                ]
            )
        )
        dt.append(f"M{fmt(a0[0])} {fmt(a0[1])} L{fmt(a1[0])} {fmt(a1[1])}")
        pd_pts.append((x + nx * tw / 2, y + ny * tw / 2))
    holder.append(
        _el(
            "path",
            d=" ".join(pd),
            fill=_mix(fill, "#FFFFFF", 0.3),
            stroke=_mix(membrane, "#FFFFFF", 0.2),
            stroke_width=0.6,
        )
    )
    holder.append(
        _el(
            "path", d=" ".join(dt), fill="none", stroke=_mix(membrane, "#000000", 0.2), stroke_width=max(0.6, tw * 0.07)
        )
    )
    if rich:
        defs.append(_radial("pvac", "#FFFFFF", _mix(vac_c, "#7FA7C6", 0.25), fx=0.42, fy=0.38))
        look = _look()
        look.append(_el("path", d=_poly(vac), fill="url(#pvac)", stroke="none"))
        # cellulose microfibrils: fine oblique hatching inside the wall
        mid_w = _offset_closed(pm, T / 2 + tw * 0.5)
        fib = []
        for i in range(0, N, 2):
            (x, y), (nx, ny) = mid_w[i], pm_n[i]
            tx, ty = -ny, nx
            h = tw * 0.32
            fib.append(
                f"M{fmt(x - nx * h - tx * h * 0.7)} {fmt(y - ny * h - ty * h * 0.7)} L{fmt(x + nx * h + tx * h * 0.7)} "
                f"{fmt(y + ny * h + ty * h * 0.7)}"
            )
        look.append(
            _el(
                "path",
                d=" ".join(fib),
                fill="none",
                stroke=_mix(wall, "#5E6B2E", 0.3),
                stroke_width=0.55,
                stroke_opacity=0.7,
            )
        )
        holder.append(look)
    # 4. bilayers: plasma membrane (outer face = cell side of the wall) and tonoplast (outer face = cytoplasm side)
    for line in (pm, tono):
        curve = Curve(_poly(_offset_closed(line, T / 2)), tolerance=0.4)
        rows = _lipid_rows(curve, T, membrane, closed=True, inward=1 if _signed_area(curve) > 0 else -1)
        grp = _lipid_group(rows, T, membrane, native=not rich)
        if rich:
            lk = _look()
            lk.append(grp)
            holder.append(lk)
        else:
            holder.append(grp)
    # 5. organelles
    ports = {}
    mito_c = _mix(membrane, "#C0582E", 0.6)
    for i0, L, Wd, kind in items:
        (x, y), (nx, ny) = pm[i0], pm_n[i0]
        off = T / 2 + 2.2 + Wd / 2
        cx, cy = x - nx * off, y - ny * off
        ang = math.degrees(math.atan2(-nx, ny))
        if kind == "nucleus":
            g = _el("g", transform=f"translate({fmt(cx)} {fmt(cy)}) rotate({fmt(ang)})")
            g.append(
                _el(
                    "ellipse",
                    cx=0,
                    cy=0,
                    rx=L / 2,
                    ry=Wd / 2,
                    fill=nuc_fill,
                    stroke=_mix(nuc_fill, membrane, 0.6),
                    stroke_width=1.3,
                )
            )
            if rich:
                defs.append(
                    _radial("pnuc", _mix(nuc_fill, "#FFFFFF", 0.45), _mix(nuc_fill, membrane, 0.3), fx=0.4, fy=0.35)
                )
                g.append(_el("ellipse", cx=0, cy=0, rx=L / 2, ry=Wd / 2, fill="url(#pnuc)", stroke="none"))
                g.append(
                    _el(
                        "ellipse",
                        cx=0,
                        cy=0,
                        rx=L / 2 - 2,
                        ry=Wd / 2 - 2,
                        fill="none",
                        stroke=_mix(nuc_fill, membrane, 0.5),
                        stroke_width=0.6,
                        stroke_dasharray="2 2.2",
                    )
                )
            g.append(
                _el(
                    "ellipse", cx=L * 0.1, cy=-Wd * 0.05, rx=Wd * 0.2, ry=Wd * 0.17, fill=_mix(nuc_fill, membrane, 0.75)
                )
            )
            holder.append(g)
            ports["nucleus"] = (cx, cy)
        elif kind == "chloroplast":
            holder.append(_chloroplast(cx, cy, L, Wd, ang, chl_c, rich))
            ports.setdefault("chloroplast", (cx, cy))
        else:
            holder.append(_mito(cx, cy, L, ang, mito_c))
            ports.setdefault("mitochondrion", (cx, cy))
    top_i = int(N * 0.75)
    vb = (min(p[0] for p in vac), min(p[1] for p in vac), max(p[0] for p in vac), max(p[1] for p in vac))
    gap_i = int(N * 0.64)
    ports.update(
        wall=_offset_closed(pm, T / 2 + tw / 2)[top_i],
        plasma_membrane=pm[int(N * 0.82)],
        tonoplast=tono[int(N * 0.85)],
        vacuole=((vb[0] + vb[2]) / 2 + rx * 0.08, (vb[1] + vb[3]) / 2 + ry * 0.05),
        cytoplasm=_offset_closed(pm, -(T / 2 + cyt * 0.5 + T * 0.5))[gap_i],
        plasmodesma=pd_pts[0],
    )
    lw = max(1.2, tw * 0.2) / 2
    return _finish(holder, defs, Box(-lw, -lw, 2 * rx + 2 * lw, 2 * ry + 2 * lw), **ports)
