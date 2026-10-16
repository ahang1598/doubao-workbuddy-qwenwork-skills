"""Chemistry / materials parts drawn like textbook figures: atom, lattice, particle."""

from __future__ import annotations

import math
import random

from ..atomize_svg_to_slide._geometry import fmt
from ._bio_parts import _el, _look, _mix, _radial, _smooth
from ._geometry import Box, _finite, _union
from ._geometry import label as _label
from ._help import _drawing_api
from ._parts import _INK, _circ, _finish, _style
from ._device_parts import CPK


def _is_dark(color):
    c = color.lstrip("#")
    if len(c) != 6:
        return False
    r, g, b = (int(c[k : k + 2], 16) for k in (0, 2, 4))
    return 0.299 * r + 0.587 * g + 0.114 * b < 150


def _text(x, y, content, fs, *, fill, anchor="middle", weight="bold"):
    t = _el("text", x=x, y=y, font_size=fs, text_anchor=anchor, fill=fill, font_weight=weight)
    t.text = str(content)
    b = _label(str(content), font_size=fs, text_anchor=anchor, font_weight=weight).bounds
    return t, Box(x + b.x, y - fs + b.y, b.width, b.height)


def _sphere_look(look, cx, cy, r, gid):
    """Gradient body + soft specular spot for one sphere (appended to an appearance group)."""
    look.append(_el("circle", cx=cx, cy=cy, r=r, fill=f"url(#{gid})"))
    look.append(
        _el(
            "ellipse",
            cx=cx - r * 0.36,
            cy=cy - r * 0.4,
            rx=r * 0.3,
            ry=r * 0.2,
            fill="url(#spec)",
            transform=f"rotate(-35 {fmt(cx - r * 0.36)} {fmt(cy - r * 0.4)})",
        )
    )


def _spec_gradient():
    g = _el("radialGradient", id="spec", cx="50%", cy="50%", r="50%")
    g.append(_el("stop", offset="0", stop_color="#FFFFFF", stop_opacity=0.9))
    g.append(_el("stop", offset="1", stop_color="#FFFFFF", stop_opacity=0))
    return g


def _ball_gradient(gid, fill):
    return _radial(gid, _mix(fill, "#FFFFFF", 0.45), _mix(fill, "#000000", 0.3), fx=0.36, fy=0.32)


@_drawing_api(
    "parts",
    purpose="原子/离子小球（教科书风格）：径向渐变球体明暗 + 镜面高光，球心写元素符号，可带电荷上标。",
    returns="Geometry（原点在中心；端口 center 及四边）",
    semantics=(
        "symbol 写在球心（原生文字）；r 为半径；fill 为原子色（原生圆，可改色）。",
        'charge 为电荷上标文字，如 "+"、"2+"、"-"，写在球右上方。',
        'style="rich" 加渐变与高光（一个局部 SVG）；"flat" 只有纯色原生圆和文字。批量排布用 lattice()。',
    ),
    example='d.place(atom("Na", fill="#E24C3B", charge="+"), at=(300, 200), key="na")',
    rank=4,
)
def atom(
    symbol="", *, r=12, fill="#4A6FA5", stroke="none", text_fill="#FFFFFF", font_size=None, charge=None, style="rich"
):
    rich = _style(style)
    _finite(r)
    holder, defs = _el("g"), _el("defs")
    holder.append(defs)
    edge = stroke if stroke != "none" else (_mix(fill, "#000000", 0.35) if rich else "none")
    holder.append(
        _el(
            "circle",
            cx=0,
            cy=0,
            r=r,
            fill=fill,
            stroke=edge,
            stroke_width=max(0.5, r * 0.05) if edge != "none" else None,
            data_outline="1",
        )
    )
    boxes = [Box(-r, -r, 2 * r, 2 * r)]
    if rich:
        defs.append(_ball_gradient("ball", fill))
        defs.append(_spec_gradient())
        look = _look()
        _sphere_look(look, 0, 0, r - (max(0.5, r * 0.05) / 2 if edge != "none" else 0), "ball")
        holder.append(look)
    if symbol:
        fs = font_size or r * (0.95 if len(str(symbol)) < 2 else 0.85)
        t, _ = _text(0, fs * 0.36, symbol, fs, fill=text_fill)
        holder.append(t)
    if charge:
        cfs = max(6, r * 0.62)
        t, b = _text(r * 0.78, -r * 0.62, charge, cfs, fill=_INK, anchor="start")
        holder.append(t)
        boxes.append(b)
    return _finish(holder, defs, _union(boxes))


@_drawing_api(
    "parts",
    purpose="晶格/层状结构（教科书风格）：按行列排布立体原子球，可画键、晶胞框、空位标记与后层（立体感）。",
    returns="Geometry（原点在中心；端口四边/center）",
    semantics=(
        "rows 为每行的原子列表，元素为 (symbol, fill)、symbol 字符串或 None（空位）；pitch 为原子间距，layer_gap 为行距。",
        "offsets 为每行的横向错位（单位：pitch），用于 ABC/ABAB 堆垛；r 为原子半径（默认 0.36·pitch）。",
        "bonds=True 在原子下画短键（同行相邻、上下行相邻；有错位时连斜向最近邻）。",
        "unit_cell=(i0, j0, i1, j1) 以原子 (列 i, 行 j) 中心为角画虚线晶胞框；show_vacancies=True 在 None 位置画虚线小圈。",
        "depth>0 在右上方 (depth·pitch·0.35) 处画一层浅色后层，营造三维感；r≥8 时球心写元素符号。",
        'style="rich" 每个原子带渐变与高光（合为一个局部 SVG）；"flat" 全部纯色原生。',
    ),
    example='d.place(lattice([[("O", "#A9BBD6")] * 8, [("Na", "#E24C3B"), None] * 4], pitch=26, bonds=True, unit_cell=(0, 0, 2, 1)), at=(260, 160), key="p2")',
    rank=5,
)
def lattice(
    rows,
    *,
    pitch=24,
    layer_gap=None,
    r=None,
    offsets=None,
    bonds=False,
    unit_cell=None,
    depth=0,
    show_vacancies=False,
    style="rich",
):
    rich = _style(style)
    if isinstance(rows, int) or (isinstance(rows, tuple) and len(rows) == 2 and all(isinstance(v, int) for v in rows)):
        n_rows, n_cols = (rows, rows) if isinstance(rows, int) else rows  # lattice(4) / lattice((3, 6)): uniform grid
        rows = [[("", "#4A6FA5")] * n_cols for _ in range(n_rows)]
    _finite(pitch)
    layer_gap = layer_gap or pitch
    r = r or pitch * 0.36
    holder, defs = _el("g"), _el("defs")
    holder.append(defs)
    atoms, vacancies = [], []  # (i, j, cx, cy, symbol, fill)
    for j, row in enumerate(rows):
        dx = (offsets[j] if offsets else 0) * pitch
        for i, item in enumerate(row):
            cx, cy = dx + i * pitch, j * layer_gap
            if not item:
                vacancies.append((cx, cy))
                continue
            symbol, fill = (item, "#4A6FA5") if isinstance(item, str) else item
            atoms.append((i, j, cx, cy, symbol, fill))
    links = []
    by_row = {}
    for a in atoms:
        by_row.setdefault(a[1], []).append(a)
    for j, row in by_row.items():
        row = sorted(row, key=lambda a: a[0])
        for a, b in zip(row, row[1:]):
            if b[0] == a[0] + 1:
                links.append((a[2], a[3], b[2], b[3]))
        for a in row:
            for b in by_row.get(j + 1, ()):
                if abs(b[2] - a[2]) <= pitch * 0.5 + 1e-6:
                    links.append((a[2], a[3], b[2], b[3]))
    bond_w = max(1.0, r * 0.38)
    first = [True]

    def put(el):
        if first[0] and el.get("stroke-opacity") is None:
            el.set("data-outline", "1")
            first[0] = False
        holder.append(el)

    def draw_bonds(ox, oy, color, light):
        if not (bonds and links):
            return
        put(
            _el(
                "path",
                d=" ".join(
                    f"M{fmt(x1 + ox)} {fmt(y1 + oy)} L{fmt(x2 + ox)} {fmt(y2 + oy)}" for x1, y1, x2, y2 in links
                ),
                stroke=color,
                stroke_width=bond_w,
                stroke_linecap="round",
                fill="none",
            )
        )
        if light:
            holder.append(
                _el(
                    "path",
                    d=" ".join(
                        f"M{fmt(x1 + ox)} {fmt(y1 + oy)} L{fmt(x2 + ox)} {fmt(y2 + oy)}" for x1, y1, x2, y2 in links
                    ),
                    stroke=light,
                    stroke_width=bond_w * 0.4,
                    stroke_linecap="round",
                    fill="none",
                )
            )

    boxes = [Box(cx - r, cy - r, 2 * r, 2 * r) for _, _, cx, cy, _, _ in atoms] or [Box(-r, -r, 2 * r, 2 * r)]
    if depth > 0:
        # Back layer sits half a pitch diagonally behind: smaller and muted so it reads as depth, not noise.
        ox, oy = depth * pitch * 0.5, -depth * pitch * 0.5
        rb = r * 0.78
        draw_bonds(ox, oy, "#D5D9DF", None)
        for _, _, cx, cy, _, fill in atoms:
            back = _mix(_mix(fill, "#8A939E", 0.5), "#FFFFFF", 0.45)
            put(
                _el(
                    "circle",
                    cx=cx + ox,
                    cy=cy + oy,
                    r=rb,
                    fill=back,
                    stroke=_mix(back, "#000000", 0.12),
                    stroke_width=0.5,
                )
            )
            boxes.append(Box(cx + ox - rb, cy + oy - rb, 2 * rb, 2 * rb))
    draw_bonds(0, 0, "#8A939E", "#C3C9D1" if rich else None)
    for _, _, cx, cy, _, fill in atoms:
        edge = _mix(fill, "#000000", 0.3)
        put(
            _el(
                "circle",
                cx=cx,
                cy=cy,
                r=r,
                fill=fill,
                stroke=edge if rich else None,
                stroke_width=max(0.4, r * 0.05) if rich else None,
            )
        )
    if rich and atoms:
        defs.append(_spec_gradient())
        gids = {}
        for k, fill in enumerate(dict.fromkeys(a[5] for a in atoms)):
            gids[fill] = f"ball{k}"
            defs.append(_ball_gradient(f"ball{k}", fill))
        look = _look()
        for _, _, cx, cy, _, fill in atoms:
            _sphere_look(look, cx, cy, r - max(0.4, r * 0.05) / 2, gids[fill])
        holder.append(look)
    if r >= 8:
        for _, _, cx, cy, symbol, fill in atoms:
            if symbol:
                fs = r * (0.9 if len(symbol) < 2 else 0.75)
                t, _ = _text(cx, cy + fs * 0.36, symbol, fs, fill="#FFFFFF" if _is_dark(fill) else _INK)
                holder.append(t)
    if show_vacancies:
        for cx, cy in vacancies:
            # dashed ring as a fine polygon: straight contours keep native dashes (circles would embed)
            ring = [
                (cx + r * 0.7 * math.cos(2 * math.pi * k / 36), cy + r * 0.7 * math.sin(2 * math.pi * k / 36))
                for k in range(36)
            ]
            put(
                _el(
                    "path",
                    d="M" + " L".join(f"{fmt(x)} {fmt(y)}" for x, y in ring) + " Z",
                    fill="none",
                    stroke="#8A939E",
                    stroke_width=max(0.8, r * 0.08),
                    stroke_dasharray=f"{fmt(r * 0.28)} {fmt(r * 0.22)}",
                )
            )
            boxes.append(Box(cx - r, cy - r, 2 * r, 2 * r))
    if unit_cell:
        i0, j0, i1, j1 = unit_cell
        dx0 = (offsets[j0] if offsets and j0 < len(offsets) else 0) * pitch
        x0, x1 = sorted((dx0 + i0 * pitch, dx0 + i1 * pitch))
        y0, y1 = sorted((j0 * layer_gap, j1 * layer_gap))
        sw = max(1.0, r * 0.12)
        put(
            _el(
                "rect",
                x=x0,
                y=y0,
                width=max(x1 - x0, 1e-3),
                height=max(y1 - y0, 1e-3),
                fill="none",
                stroke="#C0392B",
                stroke_width=sw,
                stroke_dasharray=f"{fmt(sw * 4)} {fmt(sw * 2.5)}",
            )
        )
        boxes.append(Box(x0 - sw, y0 - sw, x1 - x0 + 2 * sw, y1 - y0 + 2 * sw))
    return _finish(holder, defs, _union(boxes))


def _clip_half(poly, px, py, nx, ny, c):
    """Keep the part of polygon where nx*x + ny*y <= c (Sutherland-Hodgman)."""
    out = []
    n = len(poly)
    for k in range(n):
        a, b = poly[k], poly[(k + 1) % n]
        fa, fb = nx * a[0] + ny * a[1] - c, nx * b[0] + ny * b[1] - c
        if fa <= 0:
            out.append(a)
        if (fa <= 0) != (fb <= 0):
            t = fa / (fa - fb)
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return out


def _grain_seeds(n, radius, rnd):
    pts, spacing = [], radius * 1.5 / math.sqrt(max(n, 1))
    tries = 0
    while len(pts) < n and tries < 4000:
        tries += 1
        rr = radius * math.sqrt(rnd.random()) * 0.95
        a = rnd.uniform(0, 2 * math.pi)
        p = (rr * math.cos(a), rr * math.sin(a))
        lim = spacing * (0.8 if tries < 2000 else 0.4)
        if all(math.hypot(p[0] - q[0], p[1] - q[1]) > lim for q in pts):
            pts.append(p)
    return pts


def _voronoi_cells(seeds, radius, samples=96):
    circle = [
        (radius * math.cos(2 * math.pi * k / samples), radius * math.sin(2 * math.pi * k / samples))
        for k in range(samples)
    ]
    return _voronoi_clip(seeds, circle)


def _voronoi_clip(seeds, boundary):
    """Voronoi cells of ``seeds`` clipped to the convex ``boundary`` polygon."""
    cells = []
    for i, (x, y) in enumerate(seeds):
        poly = boundary
        for j, (u, v) in enumerate(seeds):
            if i == j:
                continue
            nx, ny = u - x, v - y
            c = (u * u + v * v - x * x - y * y) / 2
            poly = _clip_half(poly, x, y, nx, ny, c)
            if not poly:
                break
        if len(poly) >= 3:
            cells.append(poly)
    return cells


def _crack(rnd, inner, length, start_angle):
    """Polyline from the rim inward with jitter; returns (points, branch points)."""
    a = start_angle
    x, y = inner * 0.98 * math.cos(a), inner * 0.98 * math.sin(a)
    heading = a + math.pi + rnd.uniform(-0.35, 0.35)
    steps = 7
    seg = length / steps
    pts = [(x, y)]
    for _ in range(steps):
        heading += rnd.uniform(-0.45, 0.45)
        x, y = x + seg * math.cos(heading), y + seg * math.sin(heading)
        if math.hypot(x, y) > inner * 0.97:
            break
        pts.append((x, y))
    return pts, heading


@_drawing_api(
    "parts",
    purpose="颗粒/晶粒截面（教科书风格）：Voronoi 多边形晶粒 + 细晶界、核壳、分叉细裂纹、外包覆层。",
    returns="Geometry（原点在中心；端口 center/四边/shell/coating）",
    semantics=(
        "r 为颗粒（含壳）半径；grains>0 时按 seed 生成确定性的 Voronoi 晶粒（原生多边形，色调微差），晶界为细线。",
        "shell 为核壳外层厚度（0 表示无壳），shell_fill 为壳色；coating>0 在 r 外加一圈包覆层（如碳包覆），coating_fill 可改色。",
        "cracks 为裂纹条数：从边缘向内的细分叉裂纹，颜色由 accent 压暗；accent 默认取 fill 压暗。",
        'style="rich" 加整体径向明暗与高光（一个局部 SVG）；"flat" 只有纯色原生形状。',
    ),
    example='d.place(particle(70, grains=6, shell=8, cracks=2, coating=4, fill="#E8E2D6"), at=(200, 180), key="particle")',
    rank=7,
)
def particle(
    r,
    *,
    fill="#E8E2D6",
    stroke="#6B6F78",
    grains=0,
    shell=0,
    shell_fill="#B9C8E0",
    cracks=0,
    accent=None,
    coating=0,
    coating_fill=None,
    style="rich",
    seed=1,
):
    rich = _style(style)
    _finite(r)
    rnd = random.Random(seed)
    holder, defs = _el("g"), _el("defs")
    holder.append(defs)
    R = r + coating
    sw = max(1.0, r * 0.02)
    outline = True

    def disc(radius, color, **kw):
        nonlocal outline
        el = _el("circle", cx=0, cy=0, r=radius, fill=color, **kw)
        if outline:
            el.set("data-outline", "1")
            outline = False
        holder.append(el)

    if coating:
        disc(R, coating_fill or _mix(stroke, "#000000", 0.25), stroke=_mix(stroke, "#000000", 0.45), stroke_width=sw)
    if shell:
        disc(r, shell_fill, stroke=stroke, stroke_width=sw)
    inner = r - shell
    disc(
        inner,
        fill,
        stroke=stroke if not shell else _mix(shell_fill, "#000000", 0.3),
        stroke_width=sw * (1 if not shell else 0.7),
    )
    gb = _mix(fill, "#000000", 0.38)
    if grains > 0:
        seeds = _grain_seeds(int(grains), inner, rnd)
        cells = _voronoi_cells(seeds, inner - sw * 0.5)
        for poly in cells:
            t = rnd.uniform(-0.09, 0.09)
            tone = _mix(fill, "#FFFFFF", t) if t > 0 else _mix(fill, "#000000", -t)
            holder.append(
                _el(
                    "path",
                    d="M" + " L".join(f"{fmt(x)} {fmt(y)}" for x, y in poly) + " Z",
                    fill=tone,
                    stroke=gb,
                    stroke_width=max(0.5, r * 0.009),
                    stroke_linejoin="round",
                )
            )
    if rich:
        defs.append(_el("radialGradient", id="pshade", cx="50%", cy="50%", r="50%", fx="36%", fy="32%"))
        g = defs[-1]
        g.append(_el("stop", offset="0", stop_color="#FFFFFF", stop_opacity=0.45))
        g.append(_el("stop", offset=".6", stop_color="#FFFFFF", stop_opacity=0))
        g.append(_el("stop", offset="1", stop_color="#000000", stop_opacity=0.22))
        look = _look()
        look.append(_el("circle", cx=0, cy=0, r=R - sw / 2, fill="url(#pshade)"))
        if shell or coating:
            # thin bright rim on the interfaces reads as a glossy shell
            look.append(
                _el(
                    "circle",
                    cx=0,
                    cy=0,
                    r=r - sw * 1.5,
                    fill="none",
                    stroke="#FFFFFF",
                    stroke_opacity=0.35,
                    stroke_width=sw,
                )
            )
        holder.append(look)
    accent = accent or _mix(fill, "#000000", 0.45)
    ink = _mix(accent, "#000000", 0.3)
    for k in range(int(cracks)):
        a0 = 2.1 + k * 2 * math.pi / max(cracks, 1) + (rnd.uniform(-0.4, 0.4) if k else 0)
        pts, heading = _crack(rnd, inner, inner * rnd.uniform(0.55, 0.8), a0)
        if len(pts) < 2:
            continue
        holder.append(
            _el(
                "path",
                d="M" + " L".join(f"{fmt(x)} {fmt(y)}" for x, y in pts),
                stroke=ink,
                stroke_width=max(0.8, r * 0.018),
                fill="none",
                stroke_linecap="round",
                stroke_linejoin="round",
            )
        )
        for bi in (len(pts) // 2, len(pts) * 3 // 4):
            if bi <= 0 or bi >= len(pts) - 1:
                continue
            bx, by = pts[bi]
            px, py = pts[bi + 1][0] - bx, pts[bi + 1][1] - by
            h = math.atan2(py, px) + rnd.choice((-1, 1)) * rnd.uniform(0.5, 0.9)
            bpts, _ = _crack_branch(rnd, bx, by, h, inner * rnd.uniform(0.12, 0.22), inner)
            if len(bpts) >= 2:
                holder.append(
                    _el(
                        "path",
                        d="M" + " L".join(f"{fmt(x)} {fmt(y)}" for x, y in bpts),
                        stroke=ink,
                        stroke_width=max(0.5, r * 0.011),
                        fill="none",
                        stroke_linecap="round",
                        stroke_linejoin="round",
                    )
                )
    return _finish(holder, defs, Box(-R, -R, 2 * R, 2 * R), shell=(r, 0), coating=(R, 0))


def _crack_branch(rnd, x, y, heading, length, inner):
    pts, steps = [(x, y)], 4
    for _ in range(steps):
        heading += rnd.uniform(-0.35, 0.35)
        x, y = x + length / steps * math.cos(heading), y + length / steps * math.sin(heading)
        if math.hypot(x, y) > inner * 0.97:
            break
        pts.append((x, y))
    return pts, heading


_GROUPS = {
    "NH2": ("N", "H", "H"),
    "OH": ("O", "H"),
    "NO2": ("N", "O", "O"),
    "CH3": ("C", "H", "H", "H"),
    "SH": ("S", "H"),
    "F": ("F",),
    "Cl": ("Cl",),
}
_TOPOLOGIES = ("square", "hex", "cage", "channel")


def _pd(pts, closed=True):
    return "M" + " L".join(f"{fmt(x)} {fmt(y)}" for x, y in pts) + (" Z" if closed else "")


def _framework_net(topology, nx, ny, p):
    """(nodes, edges, pores[(centre, polygon)], depth flags) of the 2-D net, in local px."""
    if topology == "square":
        nodes = [(i * p, j * p) for j in range(ny + 1) for i in range(nx + 1)]
        idx = lambda i, j: j * (nx + 1) + i
        edges = [(idx(i, j), idx(i + 1, j)) for j in range(ny + 1) for i in range(nx)] + [
            (idx(i, j), idx(i, j + 1)) for j in range(ny) for i in range(nx + 1)
        ]
        pores = [
            (
                (i * p + p / 2, j * p + p / 2),
                [(i * p, j * p), ((i + 1) * p, j * p), ((i + 1) * p, (j + 1) * p), (i * p, (j + 1) * p)],
            )
            for j in range(ny)
            for i in range(nx)
        ]
        return nodes, edges, pores
    if topology == "hex":  # honeycomb (hcb): flat-top hexagonal pores
        a = p / math.sqrt(3)
        nodes, key, edges, pores = [], {}, set(), []
        for i in range(nx):
            for j in range(ny):
                cx, cy = 1.5 * a * i, math.sqrt(3) * a * (j + 0.5 * (i % 2))
                poly = [(cx + a * math.cos(math.pi / 3 * k), cy + a * math.sin(math.pi / 3 * k)) for k in range(6)]
                ids = []
                for x, y in poly:
                    kk = (round(x, 3), round(y, 3))
                    if kk not in key:
                        key[kk] = len(nodes)
                        nodes.append((x, y))
                    ids.append(key[kk])
                edges.update(tuple(sorted((ids[k], ids[(k + 1) % 6]))) for k in range(6))
                pores.append(((cx, cy), poly))
        return nodes, sorted(edges), pores
    # channel: two walls along x with a 1-D channel between them
    h = p * 1.1
    nodes = [(i * p, y) for y in (0, h) for i in range(nx + 1)]
    edges = [(i, i + 1) for i in range(nx)] + [(nx + 1 + i, nx + 2 + i) for i in range(nx)]
    return (
        nodes,
        edges,
        [((i * p + p / 2, h / 2), [(i * p, 0), ((i + 1) * p, 0), ((i + 1) * p, h), (i * p, h)]) for i in range(nx)],
    )


def _boundary(polys):
    """Exterior loop of edge-sharing polygons: edges used once, chained head to tail."""
    key = lambda p: (round(p[0], 3), round(p[1], 3))
    count = {}
    for poly in polys:
        for a, b in zip(poly, poly[1:] + poly[:1]):
            e = frozenset((key(a), key(b)))
            count[e] = count.get(e, 0) + 1
    nxt = {}
    for poly in polys:
        for a, b in zip(poly, poly[1:] + poly[:1]):
            if count[frozenset((key(a), key(b)))] == 1:
                nxt[key(a)] = key(b)
    start = min(nxt)
    loop, cur = [start], nxt[start]
    while cur != start and len(loop) <= len(nxt):
        loop.append(cur)
        cur = nxt[cur]
    return loop


def _sbu(x, y, s, color, shape, muted=False):
    """Metal node / SBU: faceted coordination octahedron (VESTA style) or a small metal-oxo cluster."""
    if muted:
        color = _mix(color, "#FFFFFF", 0.45)
    edge = _mix(color, "#000000", 0.45)
    if shape == "cluster":
        out = [
            _el(
                "circle",
                cx=x,
                cy=y,
                r=s * 0.55,
                fill=CPK_O,
                stroke=_mix(CPK_O, "#000000", 0.4),
                stroke_width=max(0.4, s * 0.05),
            )
        ]
        for k in range(4):
            a = math.pi / 4 + k * math.pi / 2
            out.append(
                _el(
                    "circle",
                    cx=x + s * 0.62 * math.cos(a),
                    cy=y + s * 0.62 * math.sin(a),
                    r=s * 0.42,
                    fill=color,
                    stroke=edge,
                    stroke_width=max(0.4, s * 0.05),
                )
            )
        return out
    v = [(x, y - s), (x + s, y), (x, y + s), (x - s, y)]
    ap = (x - s * 0.18, y - s * 0.16)  # apex toward the viewer, light from upper left
    shades = (0.38, 0.05, -0.25, 0.15)
    out = [_el("path", d=_pd(v), fill=color, stroke=edge, stroke_width=max(0.5, s * 0.07), stroke_linejoin="round")]
    for k, t in enumerate(shades):
        tone = _mix(color, "#FFFFFF", t) if t > 0 else _mix(color, "#000000", -t)
        out.append(
            _el(
                "path",
                d=_pd([ap, v[k], v[(k + 1) % 4]]),
                fill=tone,
                stroke=_mix(color, "#000000", 0.3),
                stroke_width=max(0.3, s * 0.03),
                stroke_linejoin="round",
            )
        )
    return out


CPK_O = "#E24C3B"


def _linker(a, b, cut, w, color, ring=True):
    """Organic linker between two nodes: two-tone rod + para-phenylene ring (aromatic circle) at the middle."""
    (x1, y1), (x2, y2) = a, b
    L = math.hypot(x2 - x1, y2 - y1) or 1
    ux, uy = (x2 - x1) / L, (y2 - y1) / L
    p0, p1 = (x1 + ux * cut, y1 + uy * cut), (x2 - ux * cut, y2 - uy * cut)
    d = f"M{fmt(p0[0])} {fmt(p0[1])} L{fmt(p1[0])} {fmt(p1[1])}"
    dark = _mix(color, "#000000", 0.4)
    out = [
        _el("path", d=d, stroke=dark, stroke_width=w + 1.2, stroke_linecap="round", fill="none"),
        _el("path", d=d, stroke=color, stroke_width=w, stroke_linecap="round", fill="none"),
        _el(
            "path",
            d=d,
            stroke=_mix(color, "#FFFFFF", 0.55),
            stroke_width=w * 0.3,
            stroke_linecap="round",
            fill="none",
            transform=f"translate({fmt(uy * w * 0.2)} {fmt(-ux * w * 0.2)})",
        ),
    ]
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    rr = w * 1.9
    if ring and L - 2 * cut > rr * 3:
        ang = math.atan2(uy, ux)
        hexa = [
            (mx + rr * math.cos(ang + math.pi / 3 * k), my + rr * math.sin(ang + math.pi / 3 * k)) for k in range(6)
        ]
        out.append(
            _el(
                "path",
                d=_pd(hexa),
                fill=_mix(color, "#FFFFFF", 0.75),
                stroke=dark,
                stroke_width=max(0.7, w * 0.28),
                stroke_linejoin="round",
            )
        )
        out.append(_el("circle", cx=mx, cy=my, r=rr * 0.52, fill="none", stroke=dark, stroke_width=max(0.5, w * 0.2)))
    return out, (mx, my), rr, (ux, uy)


@_drawing_api(
    "parts",
    purpose="多孔骨架（MOF/COF/沸石/介孔材料，期刊风格）：金属节点/SBU（多面体或簇）+ 带苯环的有机连接体 + 开放孔道，"
    "可标开放金属位点、孔内悬挂官能团（如 -NH2）、孔内客体小分子（CO2/H2O/CH4…）。",
    returns="Geometry（原点在中心；端口 pore{k} 孔心、node{k} 节点、edge{k} 连接体中点、oms{k} 开放金属位、fg{k} 官能团、guest{k} 客体；channel 拓扑另有 inlet/outlet）",
    semantics=(
        'topology="square"（sql 方格网，cells=(列, 行) 个孔）、"hex"（蜂窝 hcb，六边形孔道，COF/MOF-74 类）、"cage"（MOF-5 式立方笼：8 个 SBU + 12 根连接体，中心黄色球表示孔腔）、'
        '"channel"（一维孔道纵剖面：上下两道骨架壁夹一条通道，用于扩散/筛分/吸附示意，cells[0] 为段数）。',
        'pitch 为节点间距；node 为金属节点色，node_shape="polyhedron"（配位八面体，三面明暗）或 "cluster"（金属-氧簇）；linker 为连接体色，中点画苯环（芳香圈）。',
        'open_metal_sites=True（或节点序号列表）在节点朝孔一侧画亮色金属位小球（端口 oms{k}）；functional_groups="NH2"/"OH"/"NO2"/"CH3"… 挂在连接体苯环上伸向孔内（端口 fg{k}）。',
        'guests=["CO2", "CO2", "H2O"] 依次放进各孔（{孔序号: [...]} 指定孔），预设分子同 molecule()，自动缩放；style="rich" 加孔腔明暗（一个局部 SVG），"flat" 全原生。',
    ),
    example='mof = d.place(porous_framework("square", cells=(3, 2), open_metal_sites=True, functional_groups="NH2", guests=["CO2"] * 4), at=(300, 220), key="mof")\n'
    'd.callout("c", "CO₂ 吸附于孔内", mof.port("guest0"), at=(520, 80), font_size=13)',
    rank=6,
)
def porous_framework(
    topology="square",
    *,
    cells=(3, 2),
    pitch=80,
    node="#3C78B5",
    node_shape="polyhedron",
    linker="#7E8794",
    pore_fill="#EEF4FA",
    open_metal_sites=False,
    oms_color="#F2A93B",
    functional_groups=None,
    guests=None,
    cage_color="#F2C94C",
    style="rich",
    seed=1,
):
    from ._device_parts import molecule
    from ._geometry import _scoped

    rich = _style(style)
    if topology not in _TOPOLOGIES:
        raise ValueError(f"topology must be one of {_TOPOLOGIES}")
    if node_shape not in ("polyhedron", "cluster"):
        raise ValueError('node_shape must be "polyhedron" or "cluster"')
    _finite(pitch)
    rnd = random.Random(seed)
    nx, ny = (cells, cells) if isinstance(cells, int) else cells
    p = float(pitch)
    bond = p / math.sqrt(3) if topology == "hex" else p  # node-to-node distance
    s = bond * 0.17  # node half-size
    w = max(2.2, bond * 0.05)  # linker rod width
    holder, defs = _el("g"), _el("defs")
    holder.append(defs)
    boxes, ports = [], {}
    back = set()
    if topology == "cage":
        e = p * 1.5
        ox, oy = e * 0.42, -e * 0.34
        front = [(0, 0), (e, 0), (e, e), (0, e)]
        nodes = front + [(x + ox, y + oy) for x, y in front]
        edges = (
            [(k, (k + 1) % 4) for k in range(4)]
            + [(4 + k, 4 + (k + 1) % 4) for k in range(4)]
            + [(k, k + 4) for k in range(4)]
        )
        back = {4, 5, 6, 7}
        centre = (e / 2 + ox / 2, e / 2 + oy / 2)
        pores = [(centre, nodes[4:5] + nodes[5:7] + [nodes[2], nodes[3], nodes[0]])]
        holder.append(
            _el(
                "path",
                d=_pd([nodes[0], nodes[4], nodes[5], nodes[6], nodes[2], nodes[3]]),
                fill=pore_fill,
                stroke="none",
                data_outline="1",
            )
        )
    else:
        nodes, edges, pores = _framework_net(topology, nx, ny, p)
        outline = [_boundary([q for _, q in pores])]  # one closed exterior contour: arrows land on the framework edge
        holder.append(
            _el(
                "path",
                d=_pd(outline[0]),
                fill=pore_fill,
                stroke=_mix(pore_fill, "#000000", 0.12),
                stroke_width=0.6,
                data_outline="1",
            )
        )
    if rich:
        g = _el("radialGradient", id="pore", cx="50%", cy="50%", r="60%")
        g.append(_el("stop", offset="0", stop_color="#FFFFFF", stop_opacity=0.9))
        g.append(_el("stop", offset=".7", stop_color="#FFFFFF", stop_opacity=0))
        g.append(_el("stop", offset="1", stop_color=_mix(pore_fill, "#1E3A5F", 0.5), stop_opacity=0.35))
        defs.append(g)
        look = _look()
        if topology == "channel":  # bright channel axis, darker toward the walls
            defs.append(_el("linearGradient", id="chan", x1=0, y1=0, x2=0, y2=1))
            for off, op in ((0, 0.3), (0.5, 0), (1, 0.3)):
                defs[-1].append(_el("stop", offset=off, stop_color=_mix(pore_fill, "#1E3A5F", 0.5), stop_opacity=op))
        for poly in (outline if topology == "channel" else [q for _, q in pores]) if topology != "cage" else ():
            look.append(_el("path", d=_pd(poly), fill="url(#chan)" if topology == "channel" else "url(#pore)"))
        holder.append(look)

    def draw_edge(k, i, j, muted=False):
        out, mid, rr, u = _linker(
            nodes[i],
            nodes[j],
            s * 0.8,
            w * (0.8 if muted else 1),
            _mix(linker, "#FFFFFF", 0.45) if muted else linker,
            ring=not muted or topology != "cage",
        )
        holder.extend(out)
        ports[f"edge{k}"] = mid
        return mid, rr, u

    def draw_node(k, muted=False):
        x, y = nodes[k]
        sk = s * (0.82 if muted else 1)
        holder.extend(_sbu(x, y, sk, node, node_shape, muted))
        boxes.append(Box(x - sk, y - sk, 2 * sk, 2 * sk))
        ports[f"node{k}"] = (x, y)

    rings = []
    behind = [k for k, (i, j) in enumerate(edges) if i in back or j in back]
    for k in behind:
        draw_edge(k, *edges[k], muted=edges[k][0] in back and edges[k][1] in back)
    for k in sorted(back):
        draw_node(k, muted=True)
    if topology == "cage":
        (cx, cy), R = pores[0][0], p * 0.62
        holder.append(
            _el(
                "circle",
                cx=cx,
                cy=cy,
                r=R,
                fill=cage_color,
                fill_opacity=0.55 if not rich else 0.35,
                stroke=_mix(cage_color, "#000000", 0.25),
                stroke_width=0.8,
            )
        )
        if rich:
            g = _el("radialGradient", id="cagesph", cx="50%", cy="50%", r="50%", fx="35%", fy="30%")
            g.append(_el("stop", offset="0", stop_color="#FFFFFF", stop_opacity=0.85))
            g.append(_el("stop", offset=".45", stop_color=cage_color, stop_opacity=0.35))
            g.append(_el("stop", offset="1", stop_color=_mix(cage_color, "#7A5A00", 0.5), stop_opacity=0.55))
            defs.append(g)
            look = _look()
            look.append(_el("circle", cx=cx, cy=cy, r=R, fill="url(#cagesph)"))
            holder.append(look)
    for k, (i, j) in enumerate(edges):
        if k not in behind:
            rings.append((k,) + draw_edge(k, i, j))
    for k in range(len(nodes)):
        if k not in back:
            draw_node(k)
    for k, (c, _) in enumerate(pores):
        ports[f"pore{k}"] = c
    # open metal sites: a bright metal ball on the node vertex that faces the nearest pore
    sites = range(len(nodes)) if open_metal_sites is True else (open_metal_sites or ())
    for n, k in enumerate(i for i in sites if i not in back):
        x, y = nodes[k]
        (px, py), _ = min(pores, key=lambda q: math.dist(q[0], (x, y)))
        a = math.atan2(py - y, px - x)
        ox_, oy_ = x + s * 0.95 * math.cos(a), y + s * 0.95 * math.sin(a)
        r = s * 0.36
        ring = [
            (ox_ + r * 1.6 * math.cos(math.pi * k / 12), oy_ + r * 1.6 * math.sin(math.pi * k / 12)) for k in range(24)
        ]
        holder.append(
            _el(
                "path",
                d=_pd(ring),
                fill="none",
                stroke=oms_color,
                stroke_width=max(0.6, r * 0.25),  # polygon keeps dashes native
                stroke_dasharray=f"{fmt(r * 0.5)} {fmt(r * 0.35)}",
            )
        )
        holder.append(
            _el("circle", cx=ox_, cy=oy_, r=r, fill=oms_color, stroke=_mix(oms_color, "#000000", 0.4), stroke_width=0.6)
        )
        ports[f"oms{n}"] = (ox_, oy_)
        boxes.append(Box(ox_ - r * 1.6, oy_ - r * 1.6, r * 3.2, r * 3.2))
    # functional groups dangling from linker rings into a neighbouring pore
    if functional_groups:
        spec = (
            [(k, functional_groups) for n, (k, *_) in enumerate(rings) if n % 2 == 0]
            if isinstance(functional_groups, str)
            else list(functional_groups)
        )
        info = {k: (mid, rr, u) for k, mid, rr, u in rings}
        for n, (k, grp) in enumerate(spec):
            if k not in info:
                continue
            (mx, my), rr, (ux, uy) = info[k]
            sides = [
                v
                for v in ((-uy, ux), (uy, -ux))
                if min(math.dist(c, (mx + v[0] * p * 0.5, my + v[1] * p * 0.5)) for c, _ in pores) < p * 0.3
            ]
            if not sides:
                continue
            vx, vy = sides[n % len(sides)]
            ax_, ay_ = mx + rr * vx * 0.87, my + rr * vy * 0.87
            atoms = _GROUPS.get(grp, (grp,))
            hx, hy = ax_ + vx * rr * 0.9, ay_ + vy * rr * 0.9
            hr = rr * 0.58
            holder.append(
                _el(
                    "path",
                    d=f"M{fmt(ax_)} {fmt(ay_)} L{fmt(hx)} {fmt(hy)}",
                    stroke=_mix(linker, "#000000", 0.4),
                    stroke_width=max(1, w * 0.5),
                    stroke_linecap="round",
                )
            )
            base = math.atan2(vy, vx)
            for m, sym in enumerate(atoms[1:]):
                b = base + (m - (len(atoms) - 2) / 2) * (math.pi / 2.4)
                sx, sy = hx + hr * 1.5 * math.cos(b), hy + hr * 1.5 * math.sin(b)
                sr = hr * (0.6 if sym == "H" else 0.85)
                holder.append(
                    _el(
                        "path",
                        d=f"M{fmt(hx)} {fmt(hy)} L{fmt(sx)} {fmt(sy)}",
                        stroke="#9AA1AB",
                        stroke_width=max(0.8, w * 0.35),
                    )
                )
                holder.append(
                    _el(
                        "circle",
                        cx=sx,
                        cy=sy,
                        r=sr,
                        fill=CPK.get(sym, "#9AA1AB"),
                        stroke=_mix(CPK.get(sym, "#9AA1AB"), "#000000", 0.4),
                        stroke_width=0.5,
                    )
                )
                boxes.append(Box(sx - sr, sy - sr, 2 * sr, 2 * sr))
            c0 = CPK.get(atoms[0], "#9AA1AB")
            holder.append(_el("circle", cx=hx, cy=hy, r=hr, fill=c0, stroke=_mix(c0, "#000000", 0.4), stroke_width=0.6))
            ports[f"fg{n}"] = (hx, hy)
    if guests:
        plan = guests.items() if isinstance(guests, dict) else [(k % len(pores), [g]) for k, g in enumerate(guests)]
        per = {}
        for pk, names in plan:
            per.setdefault(int(pk) % len(pores), []).extend([names] if isinstance(names, str) else names)
        gk = 0
        fgs = [v for k, v in ports.items() if k.startswith("fg")]
        for pk, names in sorted(per.items()):
            (cx, cy), _ = pores[pk]
            near = [f for f in fgs if math.dist(f, (cx, cy)) < bond * 0.6]
            if near:  # shift the guests away from groups hanging into this pore
                fx, fy = sum(f[0] for f in near) / len(near) - cx, sum(f[1] for f in near) / len(near) - cy
                fl = math.hypot(fx, fy) or 1
                cx, cy = cx - fx / fl * bond * 0.12, cy - fy / fl * bond * 0.12
            k_ = (
                p * (0.75 if topology == "cage" else 0.5) / 108 / math.sqrt(len(names))
            )  # 108 px ≈ CO2 length at scale 1
            for m, name in enumerate(names):
                mol = molecule(name, style="flat", labels=False, rotate=rnd.uniform(-35, 35), scale=k_)
                a = 2 * math.pi * m / len(names) + rnd.uniform(-0.3, 0.3)
                d_ = p * (0.24 if topology == "cage" else 0.16) if len(names) > 1 else 0
                gx, gy = cx + d_ * math.cos(a), cy + d_ * math.sin(a)
                el = _scoped(mol.element, f"g{gk}")
                wrap = _el("g", transform=f"translate({fmt(gx)} {fmt(gy)})")
                wrap.append(el)
                holder.append(wrap)
                b = mol.bounds
                boxes.append(Box(gx + b.x, gy + b.y, b.width, b.height))
                ports[f"guest{gk}"] = (gx, gy)
                gk += 1
    if topology == "channel":
        h = nodes[nx + 1][1]
        ports.update(inlet=(-s * 1.5, h / 2), outlet=(nx * p + s * 1.5, h / 2), channel=(nx * p / 2, h / 2))
        boxes.append(Box(-s * 1.5, 0, nx * p + 3 * s, h))
    return _finish(holder, defs, _union(boxes), **ports)


_MP_KINDS = ("fragment", "fiber", "film", "bead")


def _grow(poly, d):
    """Offset a closed polygon by d along vertex normals (outward for counter-clockwise screen order)."""
    n, out = len(poly), []
    area = sum(poly[k][0] * poly[(k + 1) % n][1] - poly[(k + 1) % n][0] * poly[k][1] for k in range(n))
    sgn = 1 if area > 0 else -1
    for k in range(n):
        (ax, ay), (bx, by) = poly[k - 1], poly[(k + 1) % n]
        tx, ty = bx - ax, by - ay
        L = math.hypot(tx, ty) or 1
        dk = d[k] if isinstance(d, (list, tuple)) else d
        out.append((poly[k][0] + ty / L * dk * sgn, poly[k][1] - tx / L * dk * sgn))
    return out


def _mp_outline(kind, size, rnd):
    if kind == "bead":
        return [
            (size / 2 * math.cos(2 * math.pi * k / 48), size / 2 * math.sin(2 * math.pi * k / 48)) for k in range(48)
        ]
    if kind == "fragment":  # angular shard: few long straight facets, one broken notch
        n, pts = 8, []
        for k in range(n):
            a = 2 * math.pi * k / n + rnd.uniform(-0.18, 0.18)
            rr = size / 2 * rnd.uniform(0.72, 1.0)
            pts.append((rr * math.cos(a), rr * math.sin(a) * 0.78))
        return pts
    if kind == "film":  # thin sheet with a wavy, torn outline
        pts = []
        for k in range(40):
            a = 2 * math.pi * k / 40
            rr = 1 + 0.08 * math.sin(3 * a + 1) + 0.05 * math.sin(7 * a) + rnd.uniform(-0.03, 0.03)
            pts.append((size * 0.55 * rr * math.cos(a), size * 0.33 * rr * math.sin(a) + size * 0.06 * math.sin(2 * a)))
        return pts
    # fiber: long curved filament of constant width, frayed ends
    w, L = size * 0.12, size
    spine = [(-L / 2 + L * t, size * 0.16 * math.sin(math.pi * 1.6 * t + 0.4)) for t in (k / 24 for k in range(25))]
    ns = []
    for k in range(25):
        a, b = spine[max(k - 1, 0)], spine[min(k + 1, 24)]
        l = math.hypot(b[0] - a[0], b[1] - a[1])
        ns.append((-(b[1] - a[1]) / l, (b[0] - a[0]) / l))
    top = [(x + nx * w / 2, y + ny * w / 2) for (x, y), (nx, ny) in zip(spine, ns)]
    bot = [(x - nx * w / 2, y - ny * w / 2) for (x, y), (nx, ny) in zip(spine, ns)]
    return (
        top
        + [(spine[-1][0] + w * 0.3, spine[-1][1] + w * 0.15)]
        + bot[::-1]
        + [(spine[0][0] - w * 0.3, spine[0][1] - w * 0.1)]
    )


@_drawing_api(
    "parts",
    purpose="微塑料/颗粒污染物（期刊风格）：碎片（棱角碎块）、纤维、薄膜、微珠；aged=True 老化（泛黄、裂纹、蚀坑），biofilm=True 外包生物膜（EPS 绒层 + 杆菌）。",
    returns="Geometry（原点在中心；端口 center/四边、surface 为上表面点、crack0/pit0（aged）、biofilm/bacteria{k}（biofilm））",
    semantics=(
        'kind="fragment" 不规则多棱碎片（rich 时有受光面）、"fiber" 弯曲纤维（端头磨损）、"film" 起伏薄膜（半透明）、"bead" 球形微珠；size 为最大尺寸 px。',
        "fill 为聚合物颜色（默认蓝色 PE/PP 碎片，可传任意颜色——轮胎磨损颗粒、煤灰、纳米颗粒通用）。",
        'aged=True：表面泛黄、出现贯穿性裂纹与小蚀坑（UV/机械老化）；biofilm=True：外包一圈不规则 EPS 绒层与杆状/球状细菌（"塑料圈" plastisphere）。',
        'style="rich" 加受光面/高光（一个局部 SVG），"flat" 全原生；seed 控制形状且确定。',
    ),
    example='mp = d.place(microplastic("fragment", 90, aged=True, biofilm=True), at=(240, 200), key="mp")\n'
    'd.callout("bf", "生物膜", mp.port("biofilm"), at=(360, 90), font_size=13)',
    rank=7,
)
def microplastic(
    kind="fragment",
    size=80,
    *,
    fill="#5B8FD1",
    aged=False,
    biofilm=False,
    biofilm_color="#8FA35A",
    bacteria="#7A5C3A",
    style="rich",
    seed=2,
):
    rich = _style(style)
    if kind not in _MP_KINDS:
        raise ValueError(f"kind must be one of {_MP_KINDS}")
    _finite(size)
    rnd = random.Random(seed)
    body = _mix(fill, "#E2B85C", 0.8) if aged else fill
    edge = _mix(body, "#000000", 0.45)
    poly = _mp_outline(kind, float(size), rnd)
    holder, defs = _el("g"), _el("defs")
    holder.append(defs)
    ports, boxes = {}, []
    smooth = kind in ("film", "bead")
    shape_d = _smooth(poly, closed=True) if smooth else _pd(poly)
    if biofilm:  # EPS halo: irregular, fuzzy, translucent
        th = size * (0.11 if kind != "fiber" else 0.07)
        halo = _grow(poly, [th * (1 + 0.35 * math.sin(k * 1.7) + rnd.uniform(-0.15, 0.15)) for k in range(len(poly))])
        holder.append(
            _el(
                "path",
                d=_smooth(halo, closed=True),
                fill=_mix(biofilm_color, "#FFFFFF", 0.45),
                fill_opacity=0.75,
                stroke=_mix(biofilm_color, "#000000", 0.25),
                stroke_width=max(0.6, size * 0.008),
                data_outline="1",
            )
        )
        xs, ys = [p[0] for p in halo], [p[1] for p in halo]
        boxes.append(Box(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)))
        ports["biofilm"] = min(halo, key=lambda q: q[1])
    holder.append(
        _el(
            "path",
            d=shape_d,
            fill=body,
            fill_opacity=0.82 if kind == "film" else None,
            stroke=edge,
            stroke_width=max(0.8, size * 0.012),
            stroke_linejoin="round",
            data_outline=None if biofilm else "1",
        )
    )
    xs, ys = [p[0] for p in poly], [p[1] for p in poly]
    boxes.append(Box(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)))
    if kind == "film":  # folded lip and a second, thinner layer
        fold = [poly[k] for k in range(30, 38)]
        lip = fold + [(x + size * 0.04, y - size * 0.05) for x, y in fold[::-1]]
        holder.append(
            _el(
                "path",
                d=_smooth(lip, closed=True),
                fill=_mix(body, "#FFFFFF", 0.3),
                stroke=edge,
                stroke_width=max(0.6, size * 0.008),
            )
        )
    if kind == "fiber":  # frayed ends: a few short filaments
        n = len(poly) // 2
        ends = [(poly[0], poly[-2]), (poly[n - 2], poly[n])]
        for (a, b), sgn in zip(ends, (-1, 1)):
            mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
            for k in range(3):
                holder.append(
                    _el(
                        "path",
                        d=f"M{fmt(mx)} {fmt(my + (k - 1) * size * 0.025)} "
                        f"l{fmt(sgn * size * rnd.uniform(0.04, 0.08))} {fmt((k - 1) * size * 0.03)}",
                        stroke=edge,
                        stroke_width=max(0.6, size * 0.01),
                        stroke_linecap="round",
                        fill="none",
                    )
                )
        ports["tip"] = (poly[n - 2][0], poly[n - 2][1])
    if rich:
        look = _look()
        if kind == "fragment":  # light facets: fan from an off-centre ridge point
            rx, ry = -size * 0.08, -size * 0.1
            n = len(poly)
            for k in range(n):
                a, b = poly[k], poly[(k + 1) % n]
                nxv, nyv = (b[1] - a[1]), -(b[0] - a[0])  # facet normal ~ outward
                lit = -(nxv * -0.6 + nyv * -0.8) / (math.hypot(nxv, nyv) or 1)
                tone = "#FFFFFF" if lit < 0 else "#000000"
                look.append(
                    _el("path", d=_pd([(rx, ry), a, b]), fill=tone, fill_opacity=round(min(0.35, abs(lit) * 0.3), 3))
                )
        else:
            gid = "mpshade"
            g = _el("radialGradient", id=gid, cx="50%", cy="50%", r="60%", fx="35%", fy="30%")
            g.append(_el("stop", offset="0", stop_color="#FFFFFF", stop_opacity=0.6))
            g.append(_el("stop", offset=".55", stop_color="#FFFFFF", stop_opacity=0))
            g.append(_el("stop", offset="1", stop_color="#000000", stop_opacity=0.25))
            defs.append(g)
            look.append(_el("path", d=shape_d, fill=f"url(#{gid})"))
            if kind == "fiber":
                n = len(poly) // 2
                look.append(
                    _el(
                        "path",
                        d=_smooth([(x * 0.98, y - size * 0.02) for x, y in poly[2 : n - 3]]),
                        fill="none",
                        stroke="#FFFFFF",
                        stroke_opacity=0.55,
                        stroke_width=size * 0.022,
                        stroke_linecap="round",
                    )
                )
        holder.append(look)
    if aged:
        ink = _mix(body, "#000000", 0.6)
        inner = [(x * 0.78, y * 0.78) for x, y in poly]
        cracks = []
        for c in range(2 if kind != "fiber" else 3):
            k = (c * len(poly) // (2 if kind != "fiber" else 3) + len(poly) // 5) % len(poly)
            x, y = inner[k] if kind != "fiber" else poly[k]
            if kind == "fiber":  # transverse cracks across the filament
                o = poly[len(poly) - 1 - k]
                cracks.append([(x, y), ((x + o[0]) / 2 + size * 0.01, (y + o[1]) / 2), o])
                continue
            pts, h = [(x, y)], math.atan2(-y, -x)
            for _ in range(5):
                h += rnd.uniform(-0.5, 0.5)
                x, y = x + size * 0.07 * math.cos(h), y + size * 0.07 * math.sin(h)
                pts.append((x, y))
            cracks.append(pts)
        holder.append(
            _el(
                "path",
                d=" ".join(_pd(c, False) for c in cracks),
                fill="none",
                stroke=ink,
                stroke_width=max(0.7, size * 0.012),
                stroke_linejoin="round",
                stroke_linecap="round",
            )
        )
        ports["crack0"] = cracks[0][len(cracks[0]) // 2]
        if kind != "fiber":
            pits = []
            for _ in range(5):
                a, rr = rnd.uniform(0, 2 * math.pi), rnd.uniform(0.15, 0.55)
                px, py = math.cos(a) * rr * (max(xs) - min(xs)) / 2, math.sin(a) * rr * (max(ys) - min(ys)) / 2
                pr = size * rnd.uniform(0.018, 0.03)
                pits.append(
                    f"M{fmt(px + pr)} {fmt(py)} A{fmt(pr)} {fmt(pr * 0.7)} 0 1 0 {fmt(px - pr)} {fmt(py)} "
                    f"A{fmt(pr)} {fmt(pr * 0.7)} 0 1 0 {fmt(px + pr)} {fmt(py)} Z"
                )
                ports.setdefault("pit0", (px, py))
            holder.append(_el("path", d=" ".join(pits), fill=_mix(body, "#000000", 0.35), stroke="none"))
    if biofilm:  # bacteria embedded in the EPS: rods + a few cocci
        ring = _grow(poly, size * (0.055 if kind != "fiber" else 0.035))
        step = max(1, len(ring) // (9 if kind != "fiber" else 12))
        bl, bw = size * 0.085, size * 0.036
        rods = []
        for n_, k in enumerate(range(rnd.randrange(step), len(ring), step)):
            (x, y), (ax, ay) = ring[k], ring[(k + 1) % len(ring)]
            ang = math.atan2(ay - y, ax - x) + rnd.uniform(-0.5, 0.5)
            if n_ % 4 == 3:
                rods.append(
                    f"M{fmt(x + bw * 0.6)} {fmt(y)} A{fmt(bw * 0.6)} {fmt(bw * 0.6)} 0 1 0 {fmt(x - bw * 0.6)} {fmt(y)} "
                    f"A{fmt(bw * 0.6)} {fmt(bw * 0.6)} 0 1 0 {fmt(x + bw * 0.6)} {fmt(y)} Z"
                )
            else:
                c, s_ = math.cos(ang) * bl / 2, math.sin(ang) * bl / 2
                rods.append(f"M{fmt(x - c)} {fmt(y - s_)} L{fmt(x + c)} {fmt(y + s_)}")
            ports[f"bacteria{n_}"] = (x, y)
        holder.append(
            _el(
                "path",
                d=" ".join(r for r in rods if "L" in r),
                stroke=bacteria,
                stroke_width=bw,
                stroke_linecap="round",
                fill="none",
            )
        )
        holder.append(
            _el(
                "path",
                d=" ".join(r for r in rods if "A" in r) or "M0 0",
                fill=_mix(bacteria, "#8FA35A", 0.4),
                stroke="none",
            )
        )
    ports["surface"] = min(poly, key=lambda q: q[1])
    return _finish(holder, defs, _union(boxes), **ports)


_PE_FEATURES = ("carbon_whisker", "coke", "sulfur", "agglomeration", "crack")


def _pe_features(features):
    out = []
    for f in features or ():
        name, opts = (f, {}) if isinstance(f, str) else (f[0], dict(f[1]) if len(f) > 1 else {})
        if name not in _PE_FEATURES:
            raise ValueError(f"feature must be one of {_PE_FEATURES}")
        out.append((name, opts))
    return out


def _covered(p, parts, skip=(), slack=0.0):
    return any(k not in skip and math.hypot(p[0] - x, p[1] - y) < r - slack for k, (x, y, r, _) in enumerate(parts))


def _pe_tube(pts, w):
    """Closed outline around a polyline with constant width (a carbon nanofibre)."""
    from ._device_parts import _taper

    return _taper(pts, w, w * 0.92)


@_drawing_api(
    "parts",
    purpose="多孔复合电极截面（期刊风格）：两相烧结颗粒互穿网络（颈部连接）+ 孔隙，底部致密电解质，自动标出三相界面 TPB；"
    "可叠加积碳晶须（顶端生长）、积碳膜、硫吸附、颗粒团聚粗化、裂纹等退化。",
    returns="Geometry（原点在中心；端口 top 气体侧、electrolyte、pore{k}、phaseA{k}/phaseB{k} 颗粒中心、tpb{k} 三相界面点、"
    "whisker{k}_base/_tip、coke0、sulfur0、agglomerate{k}、crack0）",
    semantics=(
        "SOFC/SOEC 阳极（Ni-YSZ）/阴极（LSM-YSZ）、电池复合电极（活性物质+导电剂）、催化层、烧结陶瓷通用；phases 为两相名称（写进图例），colors=(A 色, B 色[, 孔色, 电解质色])。",
        "porosity 为孔隙率（0.1–0.6，按此比例挖掉颗粒位）；particle_r 为颗粒半径（默认按尺寸自动）；相邻颗粒部分重叠形成烧结颈，颈处画细晶界。",
        "tpb=True 在 A 相、B 相与孔三者交汇处（含 A 颗粒与电解质表面的交点）画红色小点，端口 tpb0…；electrolyte=True 底部画致密电解质层（electrolyte_name 改名）。",
        'features=["carbon_whisker", "sulfur"] 或 [("carbon_whisker", {"count": 3})]：carbon_whisker 从 A 颗粒长出弯曲碳纤维、金属颗粒被顶在纤维顶端；coke 积碳膜包覆 A 相；'
        "sulfur 硫原子吸附于 A 相外表面；agglomeration A 相颗粒长大合并（TPB 随之减少）；crack 贯穿电解质/电极的裂纹。",
        'legend=True 在下方画相/孔/TPB 图例；style="rich" 加颗粒球面明暗（一个局部 SVG），"flat" 全原生；seed 确定形状。',
    ),
    example='e = d.place(porous_electrode(440, 260, phases=("Ni", "YSZ"), features=[("carbon_whisker", {"count": 3})]), at=(300, 200), key="anode")\n'
    'd.callout("tpb", "三相界面 TPB", e.port("tpb0"), at=(560, 80), font_size=13)',
    rank=8,
)
def porous_electrode(
    width=440,
    height=260,
    *,
    phases=("Ni", "YSZ"),
    colors=("#8C97A3", "#EADFC3"),
    porosity=0.3,
    particle_r=None,
    electrolyte=True,
    electrolyte_name="电解质",
    tpb=True,
    features=(),
    legend=True,
    font_size=12,
    style="rich",
    seed=4,
):
    rich = _style(style)
    _finite(width, height, porosity)
    if not 0 <= porosity <= 0.7:
        raise ValueError("porosity must be within 0–0.7")
    feats = _pe_features(features)
    names = {n for n, _ in feats}
    rnd = random.Random(seed)
    W, H = float(width), float(height)
    ca, cb = colors[0], colors[1]
    pore = colors[2] if len(colors) > 2 else "#EEF4FA"
    elec = colors[3] if len(colors) > 3 else _mix(cb, "#000000", 0.12)
    E = H * 0.17 if electrolyte else 0.0
    top_e = H - E
    r0 = float(particle_r or max(7.0, min(W, H) / 13))
    sp = r0 * 1.62
    holder, defs = _el("g"), _el("defs")
    holder.append(defs)
    bg = _el("rect", x=0, y=0, width=W, height=top_e, fill=pore, data_outline="1")
    holder.append(bg)

    # jittered close packing; each site phase A/B; `porosity` of the sites stay empty
    parts, rows = [], int((top_e - r0 * 0.3) / (sp * 0.866)) + 1
    for j in range(rows):
        y = top_e - r0 * 0.25 - j * sp * 0.866
        if y < r0 * 0.7:
            break
        x = r0 * 1.05 + (sp / 2 if j % 2 else 0)
        while x <= W - r0 * 1.05:
            if (j == 0 and rnd.random() > 0.15) or rnd.random() >= max(0.0, porosity - 0.08) * 1.15:
                rr = r0 * rnd.uniform(0.9, 1.08)
                parts.append(
                    (
                        x + rnd.uniform(-0.16, 0.16) * r0,
                        y + rnd.uniform(-0.14, 0.14) * r0,
                        rr,
                        "A" if rnd.random() < 0.5 else "B",
                    )
                )
            x += sp
    if "agglomeration" in names:  # coarsening: some A particles swallow their A neighbours
        opts = dict(feats)["agglomeration"]
        keep, gone, aggl = [], set(), []
        cand = [k for k, p in enumerate(parts) if p[3] == "A"]
        rnd.shuffle(cand)
        for k in cand[: max(1, int(opts.get("count", max(2, len(cand) // 7))))]:
            if k in gone:
                continue
            x, y, rr, _ = parts[k]
            R = rr * 1.55
            for m, (u, v, s, ph) in enumerate(parts):
                if m != k and ph == "A" and math.hypot(u - x, v - y) < R + s * 0.3:
                    gone.add(m)
            parts[k] = (x, y, R, "A")
            aggl.append(k)
        idx = {}
        for k, p in enumerate(parts):
            if k not in gone:
                idx[k] = len(keep)
                keep.append(p)
        aggl = [idx[k] for k in aggl if k in idx]
        parts = keep
    # drop particles not connected (through overlaps) to the electrolyte / bottom row
    touch = lambda a, b: math.hypot(a[0] - b[0], a[1] - b[1]) < a[2] + b[2] - 0.5
    live = {k for k, p in enumerate(parts) if p[1] + p[2] > top_e - r0 * 0.4}
    frontier = list(live)
    while frontier:
        k = frontier.pop()
        for m, q in enumerate(parts):
            if m not in live and touch(parts[k], q):
                live.add(m)
                frontier.append(m)
    remap = {k: i for i, k in enumerate(sorted(live))}
    parts = [parts[k] for k in sorted(live)]
    if "agglomeration" in names:
        aggl = [remap[k] for k in aggl if k in remap]

    y_lo, y_hi = min([y - rr for x, y, rr, _ in parts] or [0]), max([y + rr for x, y, rr, _ in parts] or [top_e])
    bg.set("y", fmt(min(0.0, y_lo - r0 * 0.3)))
    bg.set("height", fmt(max(top_e, y_hi) - min(0.0, y_lo - r0 * 0.3)))
    sw = max(0.8, r0 * 0.075)
    edge = {"A": _mix(ca, "#000000", 0.45), "B": _mix(cb, "#000000", 0.4)}
    fillc = {"A": ca, "B": cb}
    coke = "coke" in names
    if coke:  # amorphous carbon film: dark, slightly bumpy rim around A
        film = []
        for x, y, rr, ph in parts:
            if ph == "A":
                pts = [
                    (
                        x + rr * (1.17 + 0.05 * math.sin(7 * a + x)) * math.cos(a),
                        y + rr * (1.17 + 0.05 * math.sin(7 * a + x)) * math.sin(a),
                    )
                    for a in [2 * math.pi * q / 20 for q in range(20)]
                ]
                film.append(_smooth(pts, closed=True))
        holder.append(_el("path", d=" ".join(film), fill="#3D3A38", stroke="none"))
    for ph in ("B", "A"):  # outline pass then fill pass → only the union outline survives
        mine = [p for p in parts if p[3] == ph]
        for x, y, rr, _ in mine:
            holder.append(_el("circle", cx=x, cy=y, r=rr, fill=fillc[ph], stroke=edge[ph], stroke_width=sw * 2))
        for x, y, rr, _ in mine:
            holder.append(_el("circle", cx=x, cy=y, r=rr - sw * 0.02, fill=fillc[ph]))
        # sintering necks: thin grain boundary along the chord of every same-phase contact
        gbs = []
        for i, a in enumerate(mine):
            for b in mine[i + 1 :]:
                d = math.hypot(a[0] - b[0], a[1] - b[1])
                if d < a[2] + b[2] - 0.5 and d > abs(a[2] - b[2]) + 0.5:
                    t = (d * d + a[2] ** 2 - b[2] ** 2) / (2 * d)
                    h = math.sqrt(max(a[2] ** 2 - t * t, 0))
                    ux, uy = (b[0] - a[0]) / d, (b[1] - a[1]) / d
                    mx, my = a[0] + ux * t, a[1] + uy * t
                    gbs.append(
                        f"M{fmt(mx - uy * h * 0.92)} {fmt(my + ux * h * 0.92)} L{fmt(mx + uy * h * 0.92)} {fmt(my - ux * h * 0.92)}"
                    )
        if gbs:
            holder.append(
                _el(
                    "path",
                    d=" ".join(gbs),
                    fill="none",
                    stroke=edge[ph],
                    stroke_width=max(0.5, sw * 0.6),
                    stroke_opacity=0.55,
                )
            )
    if rich:
        defs.append(_el("radialGradient", id="pe_sh", cx="50%", cy="50%", r="50%", fx="35%", fy="30%"))
        for off, col, op in (("0", "#FFFFFF", 0.5), (".55", "#FFFFFF", 0), ("1", "#000000", 0.2)):
            defs[-1].append(_el("stop", offset=off, stop_color=col, stop_opacity=op))
        look = _look()
        for x, y, rr, ph in parts:
            look.append(_el("circle", cx=x, cy=y, r=rr * 0.97, fill="url(#pe_sh)", opacity=0.9 if ph == "A" else 0.65))
        holder.append(look)

    ports, boxes = {}, [Box(0, min(0.0, y_lo - r0 * 0.3), W, max(H, y_hi) - min(0.0, y_lo - r0 * 0.3))]
    # electrolyte: dense layer with a few faint grains; truncates the bottom row flat (sintered onto it)
    if electrolyte:
        holder.append(
            _el("rect", x=0, y=top_e, width=W, height=E, fill=elec, stroke=_mix(elec, "#000000", 0.45), stroke_width=sw)
        )
        segs, x = [], rnd.uniform(0.3, 0.8) * E
        while x < W - 4:
            segs.append(f"M{fmt(x)} {fmt(top_e + sw)} L{fmt(x + rnd.uniform(-0.25, 0.25) * E)} {fmt(H - sw)}")
            x += E * rnd.uniform(0.9, 1.6)
        holder.append(_el("path", d=" ".join(segs), fill="none", stroke=_mix(elec, "#000000", 0.25), stroke_width=0.6))
        ports["electrolyte"] = (W / 2, top_e + E / 2)
    # pores: well-separated open spots (largest clearance first)
    cand, step = [], r0 * 0.5
    yy = r0 * 0.8
    while yy < top_e - r0 * 0.3:
        xx = r0 * 0.8
        while xx < W - r0 * 0.8:
            c = min((math.hypot(xx - x, yy - y) - rr for x, y, rr, _ in parts), default=r0)
            if c > r0 * 0.3:
                cand.append((c, xx, yy))
            xx += step
        yy += step
    pores = []
    for c, xx, yy in sorted(cand, reverse=True):
        if all(math.hypot(xx - u, yy - v) > r0 * 2.2 for u, v in pores):
            pores.append((xx, yy))
    pores.sort(key=lambda p: (round(p[1] / r0), p[0]))
    ports.update({f"pore{k}": p for k, p in enumerate(pores)})
    na = nb = 0
    for x, y, rr, ph in sorted(parts, key=lambda p: (p[1], p[0])):
        if ph == "A":
            ports[f"phaseA{na}"] = (x, y)
            na += 1
        else:
            ports[f"phaseB{nb}"] = (x, y)
            nb += 1
    # triple-phase boundary: A/B circle intersections (and A/electrolyte-surface crossings) left open to a pore
    tpbs = []
    if tpb and not coke:
        for i, a in enumerate(parts):
            for j, b in enumerate(parts):
                if a[3] != "A" or b[3] != "B":
                    continue
                d = math.hypot(a[0] - b[0], a[1] - b[1])
                if not (abs(a[2] - b[2]) < d < a[2] + b[2]):
                    continue
                t = (d * d + a[2] ** 2 - b[2] ** 2) / (2 * d)
                h = math.sqrt(max(a[2] ** 2 - t * t, 0))
                ux, uy = (b[0] - a[0]) / d, (b[1] - a[1]) / d
                for s in (1, -1):
                    p = (a[0] + ux * t - s * uy * h, a[1] + uy * t + s * ux * h)
                    if p[1] < top_e - 1 and not _covered(p, parts, skip=(i, j), slack=-0.6):
                        tpbs.append(p)
            if electrolyte and a[3] == "A" and a[1] + a[2] > top_e:
                h = math.sqrt(max(a[2] ** 2 - (top_e - a[1]) ** 2, 0))
                for p in ((a[0] - h, top_e), (a[0] + h, top_e)):
                    if not _covered((p[0], p[1] - 0.8), parts, skip=(i,), slack=-0.6):
                        tpbs.append(p)
        uniq = []
        for p in sorted(tpbs, key=lambda q: (q[1], q[0])):
            if all(math.dist(p, q) > r0 * 0.45 for q in uniq):
                uniq.append(p)
        tpbs = uniq
        rr = max(1.8, r0 * 0.16)
        holder.append(
            _el(
                "path",
                d=" ".join(_circ(x, y, rr) for x, y in tpbs) or "M0 0",
                fill="#D62839",
                stroke="#FFFFFF",
                stroke_width=max(0.6, rr * 0.35),
            )
        )
        ports.update({f"tpb{k}": p for k, p in enumerate(tpbs)})
    if "agglomeration" in names:
        ports.update({f"agglomerate{k}": parts[i][:2] for k, i in enumerate(aggl)})
    if coke:
        a0 = next((p for p in parts if p[3] == "A" and not _covered((p[0], p[1] - p[2] * 1.1), parts)), None)
        if a0:
            ports["coke0"] = (a0[0], a0[1] - a0[2] * 1.08)
    if "sulfur" in names:  # adsorbed S atoms on the exposed A surface
        dots, sr = [], max(1.4, r0 * 0.13)
        for i, (x, y, rr, ph) in enumerate(parts):
            if ph != "A":
                continue
            n = max(8, int(2 * math.pi * rr / (sr * 3.2)))
            for q in range(n):
                a = 2 * math.pi * (q + 0.5 * (i % 2)) / n
                p = (x + (rr + sr * 0.9) * math.cos(a), y + (rr + sr * 0.9) * math.sin(a))
                if p[1] < top_e - sr and not _covered(p, parts, skip=(i,), slack=-sr * 0.5):
                    dots.append(p)
        holder.append(
            _el(
                "path",
                d=" ".join(_circ(x, y, sr) for x, y in dots) or "M0 0",
                fill="#E9C21C",
                stroke="#8A6D00",
                stroke_width=max(0.4, sr * 0.25),
            )
        )
        if dots:
            ports["sulfur0"] = min(dots, key=lambda p: p[1])
    if "carbon_whisker" in names:  # tip growth: filament pushes the metal particle off the surface
        opts = dict(feats)["carbon_whisker"]
        count = int(opts.get("count", 3))
        tops = sorted(
            [
                (y - rr, k)
                for k, (x, y, rr, ph) in enumerate(parts)
                if ph == "A" and not _covered((x, y - rr - 1), parts, skip=(k,))
            ]
        )
        chosen = []
        for _, k in tops:
            if all(abs(parts[k][0] - parts[m][0]) > W / (count + 1.5) for m in chosen):
                chosen.append(k)
            if len(chosen) == count:
                break
        for n_, k in enumerate(chosen):
            x, y, rr, _ = parts[k]
            mr = rr * 0.58
            cw = mr * 1.35  # fibre diameter ≈ diameter of the metal particle riding on its tip
            L = r0 * rnd.uniform(3.6, 4.8) * float(opts.get("length", 1))
            a = -math.pi / 2 + rnd.uniform(-0.35, 0.35)
            p, pts = (x + rr * math.cos(a) * 0.9, y + rr * math.sin(a) * 0.9), []
            pts.append(p)
            for _ in range(9):
                a += rnd.uniform(-0.38, 0.38)
                a = min(max(a, -math.pi * 0.85), -math.pi * 0.15)
                p = (p[0] + L / 9 * math.cos(a), p[1] + L / 9 * math.sin(a))
                pts.append(p)
            tube = _pe_tube(pts, cw)
            holder.append(_el("path", d=_smooth(tube, closed=True), fill="#2F2D2C", stroke="#141312", stroke_width=0.7))
            holder.append(
                _el(
                    "path",
                    d=_pd(pts[1:-1], False),
                    fill="none",
                    stroke="#8E8A86",
                    stroke_width=max(0.6, cw * 0.22),
                    stroke_dasharray=f"{fmt(cw * 0.9)} {fmt(cw * 0.6)}",
                )
            )  # hollow graphitic core
            tx, ty = pts[-1]
            hx, hy = math.cos(a), math.sin(a)  # pear-shaped metal tip
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
                for q in [2 * math.pi * s / 18 for s in range(18)]
            ]
            holder.append(_el("path", d=_smooth(tip, closed=True), fill=ca, stroke=edge["A"], stroke_width=sw * 1.2))
            if rich:
                holder.append(
                    _el("path", d=_smooth(tip, closed=True), fill="url(#pe_sh)", opacity=0.9, data_appearance="1")
                )
            ports[f"whisker{n_}_base"], ports[f"whisker{n_}_tip"] = pts[0], (tx + hx * mr * 1.2, ty + hy * mr * 1.2)
            xs, ys = [q[0] for q in tube + tip], [q[1] for q in tube + tip]
            boxes.append(Box(min(xs) - 1, min(ys) - 1, max(xs) - min(xs) + 2, max(ys) - min(ys) + 2))
    if "crack" in names:
        opts = dict(feats)["crack"]
        x0 = W * float(opts.get("at", 0.68))
        y_end = H if electrolyte else top_e
        y_start = top_e - r0 * 2.5
        pts, x = [], x0
        n = 12
        for q in range(n + 1):
            yq = y_start + (y_end - y_start) * q / n
            pts.append((x, yq))
            x += rnd.uniform(-0.35, 0.35) * r0
        w0 = max(2.5, r0 * 0.35)
        wedge = [(px - w0 * (1 - 0.75 * q / n) / 2, py) for q, (px, py) in enumerate(pts)] + [
            (px + w0 * (1 - 0.75 * q / n) / 2, py) for q, (px, py) in reversed(list(enumerate(pts)))
        ]
        holder.append(
            _el("path", d=_pd(wedge), fill="#FFFFFF", stroke="#3A3F46", stroke_width=0.9, stroke_linejoin="round")
        )
        ports["crack0"] = pts[n // 2 + 2]
    tops_y = min([y - rr for x, y, rr, _ in parts] or [0])
    ports["top"] = (W / 2, tops_y)
    if not electrolyte:
        ports["electrolyte"] = (W / 2, H)
    if legend:
        fs = font_size
        items = [(ca, phases[0], "disc"), (cb, phases[1], "disc"), (pore, "孔隙", "rect")]
        if electrolyte:
            items.append((elec, electrolyte_name, "rect"))
        if tpb and not coke and tpbs:
            items.append(("#D62839", "TPB", "dot"))
        x, y = 0.0, max(H, y_hi) + fs * 1.5
        for col, name, kind in items:
            if kind == "disc":
                holder.append(
                    _el(
                        "circle",
                        cx=x + fs * 0.5,
                        cy=y - fs * 0.35,
                        r=fs * 0.5,
                        fill=col,
                        stroke=_mix(col, "#000000", 0.45),
                        stroke_width=0.8,
                    )
                )
            elif kind == "dot":
                holder.append(
                    _el(
                        "circle",
                        cx=x + fs * 0.5,
                        cy=y - fs * 0.35,
                        r=fs * 0.3,
                        fill=col,
                        stroke="#FFFFFF",
                        stroke_width=0.8,
                    )
                )
            else:
                holder.append(
                    _el(
                        "rect",
                        x=x,
                        y=y - fs * 0.85,
                        width=fs,
                        height=fs,
                        fill=col,
                        stroke=_mix(col, "#000000", 0.35),
                        stroke_width=0.8,
                    )
                )
            t, b = _text(x + fs * 1.35, y, name, fs, fill=_INK, anchor="start", weight="normal")
            holder.append(t)
            boxes.append(b)
            x = b.x + b.width + fs * 1.1
    return _finish(holder, defs, _union(boxes), **ports)
