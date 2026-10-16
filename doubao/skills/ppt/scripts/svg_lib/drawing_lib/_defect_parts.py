"""Crystal-defect parts drawn like materials-science textbook figures (Callister, Hull & Bacon)."""

from __future__ import annotations

import math
import random

from ..atomize_svg_to_slide._geometry import fmt
from ._bio_parts import _circ, _el, _look, _mix, _poly, _smooth
from ._construction import _inside, clip_segment, hatch
from ._geometry import Box, _finite, _union
from ._help import _drawing_api
from ._parts import _INK
from ._matter_parts import _ball_gradient, _clip_half, _finish, _sphere_look, _spec_gradient, _style, _voronoi_clip
from ._tech_parts import _head, _txt

_ACCENT = "#C0392B"
_LETTERS = {"A": 0.0, "B": 1 / 3, "C": 2 / 3}
_LAYER_COLORS = ("#5B8FD1", "#E08A4F", "#5FAE6E")


def _balls(holder, defs, look, points, r, fill, gid):
    """Atoms of one colour: one native path of circles; spheres shading goes into ``look`` (rich)."""
    if not points:
        return
    holder.append(
        _el(
            "path",
            d=" ".join(_circ(x, y, r) for x, y in points),
            fill=fill,
            stroke=_mix(fill, "#000000", 0.3),
            stroke_width=max(0.4, r * 0.06),
        )
    )
    if look is not None:
        if not any(g.get("id") == "spec" for g in defs):
            defs.append(_spec_gradient())
        defs.append(_ball_gradient(gid, fill))
        for x, y in points:
            _sphere_look(look, x, y, r * 0.97, gid)


def _perp(x, y, size, angle=0.0):
    """Path data of a ⊥ whose bar centre (the core) is (x, y); angle rotates it clockwise (degrees)."""
    a = math.radians(angle)
    c, s = math.cos(a), math.sin(a)
    pt = lambda u, v: (x + u * c - v * s, y + u * s + v * c)
    (x1, y1), (x2, y2), (x3, y3) = pt(-size / 2, 0), pt(size / 2, 0), pt(0, -size)
    return f"M{fmt(x1)} {fmt(y1)} L{fmt(x2)} {fmt(y2)} M{fmt(x)} {fmt(y)} L{fmt(x3)} {fmt(y3)}", [
        (x1, y1),
        (x2, y2),
        (x3, y3),
    ]


def _perp_mark(holder, x, y, size, angle, color, halo=True):
    d, pts = _perp(x, y, size, angle)
    sw = max(1.4, size * 0.16)
    if halo:
        holder.append(_el("path", d=d, fill="none", stroke="#FFFFFF", stroke_width=sw * 2.4, stroke_linecap="round"))
    holder.append(_el("path", d=d, fill="none", stroke=color, stroke_width=sw, stroke_linecap="square"))
    xs, ys = zip(*pts)
    pad = sw * (1.2 if halo else 0.5)
    return Box(min(xs) - pad, min(ys) - pad, max(xs) - min(xs) + 2 * pad, max(ys) - min(ys) + 2 * pad)


def _layer_grid(offsets, n_cols, r):
    """Close-packed rows (bottom row first) as {row: [(x, y)]}; offsets are fractions of the in-plane pitch."""
    p, h = 2.2 * r, 2.05 * r
    return p, h, {j: [((i + off) * p, -j * h) for i in range(n_cols)] for j, off in enumerate(offsets)}


def _atom_box(rows, r):
    pts = [q for row in rows.values() for q in row]
    xs, ys = [x for x, _ in pts], [y for _, y in pts]
    return Box(min(xs) - r, min(ys) - r, max(xs) - min(xs) + 2 * r, max(ys) - min(ys) + 2 * r)


def _fault_runs(stacking):
    """Interior layers whose h/c character departs from the majority (Jagodzinski notation), as (first, last) runs."""
    kinds = {j: "h" if stacking[j - 1] == stacking[j + 1] else "c" for j in range(1, len(stacking) - 1)}
    if not kinds:
        return []
    dominant = "h" if sum(k == "h" for k in kinds.values()) > len(kinds) / 2 else "c"
    runs = []
    for j in sorted(k for k, v in kinds.items() if v != dominant):
        if runs and runs[-1][1] == j - 1:
            runs[-1][1] = j
        else:
            runs.append([j, j])
    return [tuple(run) for run in runs]


@_drawing_api(
    "parts",
    purpose="密排面堆垛侧视图（教科书风格）：按 A/B/C 字母错位排原子层，左侧标层字母，自动高亮层错 / FCC 中的 HCP 薄层。",
    returns="Geometry（原点在中心；端口四边/center，有层错时 fault、fault2… 为高亮带右端）",
    semantics=(
        'stacking 自下而上的层序（只含 A/B/C、相邻不同），如 "ABCABABC"（内禀层错）、"ABAB"（HCP）；A/B/C 横向错位 0、1/3、2/3 原子间距。',
        "fault_tint=True 时按 h/c 序列找出偏离主周期的层（ABC 中的 ABAB 段或 ABAB 中的 C 层）并铺浅色带；labels=True 在左侧写层字母。",
        'colors 为 A/B/C 三层的颜色；style="rich" 加球体明暗（一个局部 SVG），"flat" 全原生。',
    ),
    example='d.place(close_packed("ABCABABCABC", n_cols=10), at=(480, 270), key="isf")',
    rank=30,
)
def close_packed(
    stacking="ABCABC", *, n_cols=10, r=10, labels=True, fault_tint=True, colors=_LAYER_COLORS, style="rich"
):
    rich = _style(style)
    _finite(n_cols, r)
    stacking = str(stacking).upper()
    if len(stacking) < 2 or set(stacking) - set(_LETTERS) or any(a == b for a, b in zip(stacking, stacking[1:])):
        raise ValueError('stacking must use A/B/C with no two equal neighbours, e.g. "ABCABC"')
    p, h, rows = _layer_grid([_LETTERS[c] for c in stacking], int(n_cols), r)
    holder, defs = _el("g"), _el("defs")
    holder.append(defs)
    atoms = _atom_box(rows, r)
    frame = _el(
        "rect",
        x=atoms.x,
        y=atoms.y,
        width=atoms.width,
        height=atoms.height,
        fill="none",
        stroke="none",
        data_outline="1",
    )
    holder.append(frame)
    boxes, ports = [atoms], {}
    if fault_tint:
        x0, x1 = atoms.x - r * 0.5, atoms.x + atoms.width + r * 0.5
        for k, (a, b) in enumerate(_fault_runs(stacking)):
            y0, y1 = -b * h - h / 2, -a * h + h / 2
            holder.append(
                _el(
                    "rect",
                    x=x0,
                    y=y0,
                    width=x1 - x0,
                    height=y1 - y0,
                    fill="#FCE7B2",
                    stroke="#D4A13A",
                    stroke_width=1,
                    stroke_dasharray="5 3",
                )
            )
            boxes.append(Box(x0 - 0.5, y0 - 0.5, x1 - x0 + 1, y1 - y0 + 1))
            ports["fault" if not k else f"fault{k + 1}"] = (x1, (y0 + y1) / 2)
    look = _look() if rich else None
    for letter, color in zip("ABC", colors):
        pts = [q for j, c in enumerate(stacking) if c == letter for q in rows[j]]
        _balls(holder, defs, look, pts, r, color, f"cp{letter}")
    if look is not None:
        holder.append(look)
    if labels:
        fs = max(10.0, r * 1.25)
        for j, c in enumerate(stacking):
            t, b = _txt(
                atoms.x - r * 0.6,
                -j * h + fs * 0.36,
                c,
                fs,
                anchor="end",
                weight="bold",
                fill=_mix(colors["ABC".index(c)], "#000000", 0.35),
            )
            holder.append(t)
            boxes.append(b)
    return _finish(holder, defs, _union(boxes), **ports)


@_drawing_api(
    "parts",
    purpose="孪晶界（教科书风格）：密排原子层在孪晶面两侧镜像排列，红色孪晶界线、孪晶侧浅色衬底，虚线示出原子列在界面处折转。",
    returns="Geometry（原点在中心；端口 boundary 为孪晶界右端，matrix/twin 为两侧中心，另有四边/center）",
    semantics=(
        "n_layers 为原子层数（自下而上），twin_at 为孪晶面所在层（0 < twin_at < n_layers-1），其上为孪晶；n_cols 为每层原子数，r 为原子半径。",
        "两侧原子列方向互为镜像（FCC 沿 [1-10] 投影 …ABCA|CBA…），虚线示出两条原子列的人字形折转。",
        'matrix/twin 为两侧原子颜色；style="rich" 加球体明暗，"flat" 全原生。',
    ),
    example='d.place(twin_lattice(9, 12, twin_at=4), at=(480, 270), key="twin")',
    rank=31,
)
def twin_lattice(n_layers=8, n_cols=10, *, twin_at=4, r=10, matrix="#5B8FD1", twin="#D9825B", style="rich"):
    rich = _style(style)
    _finite(n_layers, n_cols, twin_at, r)
    n_layers, n_cols, t = int(n_layers), int(n_cols), int(twin_at)
    if not 0 < t < n_layers - 1:
        raise ValueError("twin_at must leave at least one layer on each side: 0 < twin_at < n_layers - 1")
    shift = lambda j: (j if j <= t else 2 * t - j) / 3  # continuous column shift, mirrored above the twin plane
    p, h, rows = _layer_grid([shift(j) % 1 for j in range(n_layers)], n_cols, r)
    holder, defs = _el("g"), _el("defs")
    holder.append(defs)
    atoms = _atom_box(rows, r)
    yb = -t * h
    top = atoms.y - r * 0.4
    holder.append(
        _el(
            "rect",
            x=atoms.x - r * 0.4,
            y=top,
            width=atoms.width + r * 0.8,
            height=yb - top,
            fill="#FBEDE4",
            stroke="none",
            data_outline="1",
        )
    )
    look = _look() if rich else None
    _balls(holder, defs, look, [q for j in range(t + 1) for q in rows[j]], r, matrix, "tm")
    _balls(holder, defs, look, [q for j in range(t + 1, n_layers) for q in rows[j]], r, twin, "tt")
    if look is not None:
        holder.append(look)
    valid = [i for i in range(-n_layers, n_cols) if all(0 <= i + shift(j) < n_cols for j in range(n_layers))]
    for i0 in sorted({valid[0], valid[-1]}) if valid else ():
        guide = [((i0 + shift(j)) * p, -j * h) for j in range(n_layers)]
        holder.append(
            _el(
                "path",
                d=_poly(guide, False),
                fill="none",
                stroke=_INK,
                stroke_opacity=0.55,
                stroke_width=max(1, r * 0.12),
                stroke_dasharray=f"{fmt(r * 0.5)} {fmt(r * 0.35)}",
            )
        )
    x0, x1 = atoms.x - r * 0.6, atoms.x + atoms.width + r * 0.6
    holder.append(
        _el(
            "path",
            d=f"M{fmt(x0)} {fmt(yb)} L{fmt(x1)} {fmt(yb)}",
            fill="none",
            stroke=_ACCENT,
            stroke_width=max(1.6, r * 0.26),
            stroke_linecap="round",
        )
    )
    cx = atoms.x + atoms.width / 2
    return _finish(
        holder,
        defs,
        _union([atoms, Box(x0 - 2, yb - 2, x1 - x0 + 4, 4)]),
        boundary=(x1, yb),
        twin=(cx, (atoms.y + yb) / 2),
        matrix=(cx, (yb + atoms.y + atoms.height) / 2),
    )


def _edge_ux(x, y, b, nu=0.3):
    """Isotropic-elastic u_x of an edge dislocation at the origin (SVG y down; extra half-plane at y < 0), centred."""
    th = math.atan2(-y, x)
    u = b / (2 * math.pi) * (th + math.sin(2 * th) / (4 * (1 - nu)))
    return u - b / 4 if y < 0 else u + b / 4


@_drawing_api(
    "parts",
    purpose="刃位错（教科书风格）：方形点阵中自上插入一列多余半原子面止于位错核心，邻近原子列平滑弯曲，核心画 ⊥，虚线滑移面与柏氏矢量 b。",
    returns="Geometry（原点在中心；端口 core 位错核心、top 多余半原子面顶端、slip 滑移面左端，burgers=True 时 burgers 为 b 箭头中点）",
    semantics=(
        "n_cols 为滑移面上方的原子列数（奇数，正中一列是多余半原子面；下方少一列），n_rows 为原子行数（上方约一半），r 为原子半径。",
        "原子位置按各向同性弹性位移场 u_x 计算，原子列的弯曲和滑移面两侧的错配是真实形状；多余半原子面用 accent 色。",
        'slip_plane=True 画虚线滑移面；burgers=True 在滑移面右端画 b 箭头（长度 = 一个原子间距）；style="rich" 加球体明暗。',
    ),
    example='d.place(edge_dislocation(), at=(480, 270), key="edge")',
    rank=32,
)
def edge_dislocation(
    n_rows=7, n_cols=11, *, r=9, slip_plane=True, burgers=True, fill="#8FB3DE", accent="#D9825B", style="rich"
):
    rich = _style(style)
    _finite(n_rows, n_cols, r)
    n_rows, n_cols = int(n_rows), int(n_cols)
    if n_cols < 3 or n_cols % 2 == 0 or n_rows < 3:
        raise ValueError("n_cols must be odd and ≥ 3 (the middle column is the extra half-plane); n_rows ≥ 3")
    p = 2.9 * r
    up, down = (n_rows + 1) // 2, n_rows // 2
    mid = (n_cols - 1) // 2
    ys_up = [-p / 2 - j * p for j in reversed(range(up))]
    ys_dn = [p / 2 + j * p for j in range(down)]
    pos = lambda X, y: (X + _edge_ux(X, y, p), y)
    upper = {k: [pos((k - mid) * p, y) for y in ys_up] for k in range(n_cols)}
    lower = {i: [pos((i - mid + 0.5) * p, y) for y in ys_dn] for i in range(n_cols - 1)}
    holder, defs = _el("g"), _el("defs")
    holder.append(defs)
    pts = [q for col in upper.values() for q in col] + [q for col in lower.values() for q in col]
    xs = [x for x, _ in pts]
    atoms = Box(min(xs) - r, ys_up[0] - r, max(xs) - min(xs) + 2 * r, ys_dn[-1] - ys_up[0] + 2 * r)
    holder.append(
        _el(
            "rect",
            x=atoms.x,
            y=atoms.y,
            width=atoms.width,
            height=atoms.height,
            fill="none",
            stroke="none",
            data_outline="1",
        )
    )
    bond, bw = "#B8C2CE", max(1.0, r * 0.16)
    cols = []
    for k in range(n_cols):
        if k == mid:
            continue
        cols.append(upper[k] + lower[k if k < mid else k - 1])
    rows = [[upper[k][j] for k in range(n_cols)] for j in range(up)] + [
        [lower[i][j] for i in range(n_cols - 1)] for j in range(down)
    ]
    holder.append(
        _el(
            "path",
            d=" ".join(_smooth(c) for c in cols) + " " + " ".join(_smooth(rw) for rw in rows),
            fill="none",
            stroke=bond,
            stroke_width=bw,
            stroke_linecap="round",
        )
    )
    holder.append(
        _el(
            "path",
            d=_smooth(upper[mid]),
            fill="none",
            stroke=_mix(accent, "#FFFFFF", 0.2),
            stroke_width=bw * 1.4,
            stroke_linecap="round",
        )
    )
    look = _look() if rich else None
    _balls(
        holder,
        defs,
        look,
        [q for k, c in upper.items() if k != mid for q in c] + [q for c in lower.values() for q in c],
        r,
        fill,
        "ed",
    )
    _balls(holder, defs, look, upper[mid], r, accent, "ex")
    if look is not None:
        holder.append(look)
    boxes = [atoms]
    x0, x1 = atoms.x - p * 0.3, atoms.x + atoms.width + p * 0.3
    if slip_plane:
        holder.append(
            _el(
                "path",
                d=f"M{fmt(x0)} 0 L{fmt(x1)} 0",
                fill="none",
                stroke=_INK,
                stroke_width=max(1, r * 0.14),
                stroke_dasharray=f"{fmt(r * 0.7)} {fmt(r * 0.45)}",
            )
        )
        boxes.append(Box(x0, -1, x1 - x0, 2))
    boxes.append(_perp_mark(holder, 0, 0, p * 0.62, 0, _ACCENT))
    ports = dict(core=(0, 0), top=(0, ys_up[0] - r), slip=(x0, 0))
    if burgers:
        hd, ax0 = max(6.0, r * 0.8), x1 + p * 0.25
        holder.append(
            _el(
                "path",
                d=f"M{fmt(ax0)} 0 L{fmt(ax0 + p - hd * 0.8)} 0",
                fill="none",
                stroke=_ACCENT,
                stroke_width=max(1.4, r * 0.2),
            )
        )
        holder.append(_head(ax0 + p, 0, 1, 0, hd, _ACCENT))
        t, b = _txt(ax0 + p / 2, -hd * 0.7, "b", max(11.0, r * 1.4), fill=_ACCENT, weight="bold", italic=True)
        holder.append(t)
        boxes += [b, Box(ax0, -hd / 2, p, hd)]
        ports["burgers"] = (ax0 + p / 2, 0)
    return _finish(holder, defs, _union(boxes), **ports)


@_drawing_api(
    "parts",
    purpose="位错符号 ⊥（小号可放置符号）：横线为滑移面、竖线指向多余半原子面。",
    returns="Geometry（原点在中心；端口 core 为横线中点即位错核心）",
    semantics=(
        "size 为横线长与竖线高；angle 顺时针旋转（度），180 即 ⊤（反号位错）；color 为线色，白色衬边保证压在图上也清楚。",
    ),
    example='d.place(dislocation_symbol(16), at=(480, 270), key="perp")',
    rank=34,
)
def dislocation_symbol(size=14, angle=0, *, color=_ACCENT):
    _finite(size, angle)
    holder = _el("g")
    box = _perp_mark(holder, 0, 0, size, angle, color)
    holder[0].set("data-outline", "1")
    return _finish(holder, None, box, core=(0, 0))


def _centroid(poly):
    a = cx = cy = 0.0
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        c = x1 * y2 - x2 * y1
        a, cx, cy = a + c, cx + (x1 + x2) * c, cy + (y1 + y2) * c
    if abs(a) < 1e-9:
        return sum(x for x, _ in poly) / len(poly), sum(y for _, y in poly) / len(poly), 0.0
    return cx / (3 * a), cy / (3 * a), abs(a) / 2


def _edge_distance(pt, poly):
    best = math.inf
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        dx, dy = x2 - x1, y2 - y1
        t = max(0.0, min(1.0, ((pt[0] - x1) * dx + (pt[1] - y1) * dy) / (dx * dx + dy * dy or 1)))
        best = min(best, math.hypot(pt[0] - x1 - t * dx, pt[1] - y1 - t * dy))
    return best


def _rect_grains(w, h, n, rnd):
    """Poisson-disc seeds in the rectangle, relaxed twice (Lloyd) for equiaxed grains."""
    seeds, spacing, tries = [], math.sqrt(w * h / n) * 0.75, 0
    while len(seeds) < n and tries < 5000:
        tries += 1
        q = (rnd.uniform(0, w), rnd.uniform(0, h))
        if all(math.hypot(q[0] - s[0], q[1] - s[1]) > spacing * (1 if tries < 2500 else 0.5) for s in seeds):
            seeds.append(q)
    box = [(0, 0), (w, 0), (w, h), (0, h)]
    for _ in range(2):
        seeds = [_centroid(c)[:2] for c in _voronoi_clip(seeds, box)]
    return _voronoi_clip(seeds, box)


@_drawing_api(
    "parts",
    purpose="多晶组织（教科书/金相风格）：矩形内 Voronoi 晶粒 + 晶界，晶粒按取向换色调并带取向细纹，可加平直退火孪晶带与晶内 ⊥ 位错。",
    returns="Geometry（原点在中心；端口 g0…gN 为晶粒中心（自上而下、自左而右），twin0… 为孪晶带中心，另有四边/center）",
    semantics=(
        "width/height 为区域尺寸，n_grains 为晶粒数，seed 决定确定性的晶粒形状与取向。",
        "twins 为含退火孪晶的晶粒数（取最大的几个晶粒，各一条贯穿晶粒的平行边孪晶带）；dislocations 为晶内 ⊥ 标记个数，方向随晶粒取向。",
        'fill 为基色；style="rich" 在每个晶粒内加取向细纹（孪晶带内为镜像方向，一个局部 SVG），"flat" 只有色调与晶界。',
    ),
    example='d.place(polycrystal(420, 280, n_grains=16, twins=3, dislocations=6), at=(480, 270), key="poly")',
    rank=33,
)
def polycrystal(width=360, height=240, *, n_grains=14, twins=3, dislocations=0, seed=1, fill="#D5DCE4", style="rich"):
    rich = _style(style)
    _finite(width, height, n_grains, twins, dislocations)
    w, h = float(width), float(height)
    if w <= 0 or h <= 0 or n_grains < 1:
        raise ValueError("width/height must be positive and n_grains ≥ 1")
    rnd = random.Random(seed)
    cells = _rect_grains(w, h, int(n_grains), rnd)
    band_rows = max(1, round(math.sqrt(len(cells) * h / w)))
    info = sorted(((_centroid(c), c) for c in cells), key=lambda t: (int(t[0][1] / h * band_rows), t[0][0]))
    holder = _el("g")
    holder.append(_el("rect", x=0, y=0, width=w, height=h, fill=fill, stroke="none", data_outline="1"))
    look = _look() if rich else None
    gb = _mix(fill, "#000000", 0.55)
    ports, twin_count = {}, min(int(twins), len(cells))
    twin_ids = set(sorted(range(len(info)), key=lambda k: -info[k][0][2])[:twin_count])
    marks = []
    for k, ((cx, cy, area), poly) in enumerate(info):
        theta = rnd.uniform(0, 180)
        t = 0.16 * math.cos(math.radians(2 * theta)) + rnd.uniform(-0.04, 0.04)
        tone = _mix(fill, "#FFFFFF", t) if t > 0 else _mix(fill, "#000000", -t)
        holder.append(_el("path", d=_poly(poly), fill=tone, stroke="none"))
        size = math.sqrt(area)
        gap, ink = max(5.0, size / 7), _mix(tone, "#000000", 0.1)
        ports[f"g{k}"] = (cx, cy)
        hatched = [poly]
        if k in twin_ids:
            phi = math.radians(theta + rnd.choice((-1, 1)) * 55)
            nx, ny = -math.sin(phi), math.cos(phi)
            c0 = nx * cx + ny * cy + rnd.uniform(-0.12, 0.12) * size
            half = size * 0.1
            band = _clip_half(_clip_half(poly, 0, 0, nx, ny, c0 + half), 0, 0, -nx, -ny, -(c0 - half))
            if len(band) >= 3:
                hatched = [
                    q
                    for q in (_clip_half(poly, 0, 0, nx, ny, c0 - half), _clip_half(poly, 0, 0, -nx, -ny, -(c0 + half)))
                    if len(q) >= 3
                ]
                twin_tone = _mix(tone, "#FFFFFF", 0.45)
                holder.append(_el("path", d=_poly(band), fill=twin_tone, stroke="none"))
                if look is not None:  # lamellae inside the twin run mirrored about the twin plane
                    look.append(
                        hatch(
                            band,
                            angle=2 * math.degrees(phi) - theta,
                            gap=gap,
                            stroke=_mix(twin_tone, "#000000", 0.1),
                            stroke_width=0.6,
                        ).element
                    )
                ux, uy, L = math.cos(phi), math.sin(phi), w + h
                segs = []
                for c in (c0 - half, c0 + half):
                    bx, by = nx * c, ny * c
                    segs += clip_segment((bx - ux * L, by - uy * L), (bx + ux * L, by + uy * L), poly)
                holder.append(
                    _el(
                        "path",
                        d=" ".join(f"M{fmt(a[0])} {fmt(a[1])} L{fmt(b[0])} {fmt(b[1])}" for a, b in segs),
                        fill="none",
                        stroke=_mix(gb, "#FFFFFF", 0.25),
                        stroke_width=0.9,
                    )
                )
                ports[f"twin{len([p for p in ports if p.startswith('twin')])}"] = _centroid(band)[:2]
        if look is not None:
            for q in hatched:
                look.append(hatch(q, angle=theta, gap=gap, stroke=ink, stroke_width=0.6).element)
        marks.append((poly, theta, size))
    holder.append(
        _el(
            "path",
            d=" ".join(_poly(c) for c in cells),
            fill="none",
            stroke=gb,
            stroke_width=1.3,
            stroke_linejoin="round",
        )
    )
    if look is not None:
        holder.append(look)
    sym = max(8.0, min(14.0, math.sqrt(w * h / max(1, n_grains)) / 6))
    for n in range(int(dislocations)):
        poly, theta, size = marks[(n * 7 + 3) % len(marks)]
        xs, ys = [x for x, _ in poly], [y for _, y in poly]
        for _ in range(60):
            q = (rnd.uniform(min(xs), max(xs)), rnd.uniform(min(ys), max(ys)))
            if _inside(q, poly) and _edge_distance(q, poly) > sym * 1.2:
                _perp_mark(holder, q[0], q[1] + sym / 2, sym, theta % 90 - 45, _ACCENT, halo=False)
                break
    holder.append(_el("rect", x=0, y=0, width=w, height=h, fill="none", stroke=gb, stroke_width=1.6))
    return _finish(holder, None, Box(-0.8, -0.8, w + 1.6, h + 1.6), **ports)
