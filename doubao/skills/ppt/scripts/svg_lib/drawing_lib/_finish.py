"""Textbook-finish tools for shapes the author draws freely."""

from __future__ import annotations

import itertools

from ..atomize_svg_to_slide._geometry import fmt
from ._bio_parts import _circle_union, _el, _lipid_group, _lipid_rows, _look, _mix, _signed_area
from ..atomize_svg_to_slide._bounds import path_bounds
from ._geometry import Box, Curve, Geometry, _finite
from ._help import _drawing_api

_ids = itertools.count(1)


def _single_subpath(d):
    # "M cx cy m -r 0 a …" (common circle idiom) opens with an empty subpath; fold it into one.
    from ..atomize_svg_to_slide._geometry import path_segments

    segs = path_segments(d)
    while len(segs) > 1 and segs[0][0] == "M" and segs[1][0] == "M":
        segs = segs[1:]
    out = []
    for op, v in segs:
        out.append(op + " " + " ".join(fmt(n) for n in v) if v else op)
    return " ".join(out)


def _geometry(holder, box):
    return Geometry(holder, Box(*box) if isinstance(box, tuple) else box)


@_drawing_api(
    "finish",
    purpose="沿任意膜路径画磷脂双分子层（亲水头 + 两条疏水尾，可带胆固醇）。",
    returns="Geometry（画布坐标）",
    semantics=(
        "d 为膜外表面的 SVG 路径（画布坐标），开放或闭合均可；闭合路径向内画，开放路径以 side=1/-1 选择朝哪一侧。",
        "thickness 为双层厚度；cholesterol 为插入胆固醇个数；用 d.add(key, bilayer(...)) 原样放入。",
        "适合自己画的细胞器膜、囊泡、内吞凹陷、脂质体、突触间隙两侧膜等库里没有的形状。",
    ),
    example='d.add("vesicle_mem", bilayer("M 300 200 A 40 40 0 1 1 300.1 200 Z", thickness=10, color="#9A88C9"))',
    rank=1,
)
def bilayer(d, *, thickness=12, color="#9A88C9", side=1, spacing=None, cholesterol=0, seed=0):
    _finite(thickness)
    curve = Curve(_single_subpath(d), tolerance=0.4)
    pts, closed = curve.samples()
    inward = (1 if _signed_area(curve) > 0 else -1) if closed else side  # open paths are the midplane
    rows = _lipid_rows(
        curve, thickness, color, spacing=spacing, closed=closed, inward=inward, cholesterol=cholesterol, seed=seed
    )
    holder = _look()
    holder.append(_lipid_group(rows, thickness, color))
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    pad = thickness * 1.2
    return _geometry(holder, (min(xs) - pad, min(ys) - pad, max(xs) - min(xs) + 2 * pad, max(ys) - min(ys) + 2 * pad))


@_drawing_api(
    "finish",
    purpose="球体明暗：给自己画的圆（分子、颗粒、细胞器、行星）加径向渐变与镜面高光。",
    returns="Geometry（画布坐标）",
    semantics=(
        "center/r 为画布坐标的圆心与半径，color 为该球的底色；叠放在你自己画的原生圆之上（同圆心同半径）。",
        "渐变与高光在转换后是一个局部 SVG；底下的原生圆仍可改色、可连线。",
    ),
    example='ball = d.ellipse_at((420, 260), 30, fill="#C0504D")\nd.add("ball_look", sphere_shading((420, 260), 30, "#C0504D"))',
    rank=2,
)
def sphere_shading(center, r, color, *, highlight=0.9):
    _finite(r)
    cx, cy = center
    gid, sid = f"fin_ball{next(_ids)}", f"fin_spec{next(_ids)}"
    holder = _look()
    defs = _el("defs")
    g = _el("radialGradient", id=gid, cx="50%", cy="50%", r="60%", fx="36%", fy="32%")
    g.append(_el("stop", offset="0", stop_color=_mix(color, "#FFFFFF", 0.45)))
    g.append(_el("stop", offset="1", stop_color=_mix(color, "#000000", 0.3)))
    s = _el("radialGradient", id=sid, cx="50%", cy="50%", r="50%")
    s.append(_el("stop", offset="0", stop_color="#FFFFFF", stop_opacity=highlight))
    s.append(_el("stop", offset="1", stop_color="#FFFFFF", stop_opacity=0))
    defs.extend([g, s])
    holder.append(defs)
    holder.append(_el("circle", cx=cx, cy=cy, r=r, fill=f"url(#{gid})"))
    hx, hy = cx - r * 0.36, cy - r * 0.4
    holder.append(
        _el(
            "ellipse",
            cx=hx,
            cy=hy,
            rx=r * 0.3,
            ry=r * 0.2,
            fill=f"url(#{sid})",
            transform=f"rotate(-35 {fmt(hx)} {fmt(hy)})",
        )
    )
    return _geometry(holder, (cx - r, cy - r, 2 * r, 2 * r))


@_drawing_api(
    "finish",
    purpose="面体明暗：给任意闭合路径加柔和径向渐变（中心亮、边缘随主色加深），用于胞质、组织、器件体块。",
    returns="Geometry（画布坐标）",
    semantics=(
        "d 为与你自己画的原生形状相同的路径（画布坐标）；叠放在其上，底层原生形状保留可编辑。",
        "light 控制中心提亮程度（0–1），focus 为高光中心在外接框中的相对位置。",
    ),
    example='d.add("tissue_look", soft_shading(tissue_path, "#F2D7D0"))',
    rank=3,
)
def soft_shading(d, color, *, light=0.6, edge=0.18, focus=(0.38, 0.34)):
    gid = f"fin_soft{next(_ids)}"
    holder = _look()
    defs = _el("defs")
    g = _el("radialGradient", id=gid, cx="50%", cy="50%", r="65%", fx=f"{focus[0]:.0%}", fy=f"{focus[1]:.0%}")
    g.append(_el("stop", offset="0", stop_color=_mix(color, "#FFFFFF", light)))
    g.append(_el("stop", offset="1", stop_color=_mix(color, "#000000", edge)))
    defs.append(g)
    holder.append(defs)
    holder.append(_el("path", d=d, fill=f"url(#{gid})", stroke="none"))
    x0, y0, x1, y1 = path_bounds(d)
    return _geometry(holder, (x0, y0, x1 - x0, y1 - y0))


@_drawing_api(
    "finish",
    purpose="把互相重叠的圆合成一条外轮廓（二聚体、分叶核、刺突冠、颗粒团簇）。",
    returns="Geometry（画布坐标，原生形状）",
    semantics=(
        "circles 为 [((cx, cy), r), ...]；重叠圆若写进同一条 path，原生形状会按 evenodd 显示成空心环，用本函数代替。",
        "样式参数同 path（fill、stroke…）；适用于大致围绕中心分布的一团圆。",
    ),
    example='d.add("dimer", circle_union([((300, 200), 12), ((318, 204), 11)], fill="#5B8DB8"))',
    rank=4,
)
def circle_union(circles, **style):
    from ._geometry import path

    d = _circle_union(circles)
    style.setdefault("fill", "#4A6FA5")
    return path(d, **style)


@_drawing_api(
    "finish",
    purpose="颜色推导：按主色得到更深的描边、更浅的内层或高光色，保持整张图同一色系。",
    returns="#RRGGBB",
    semantics=("shade(color, t) 中 t>0 变浅（混白），t<0 变深（混黑）；|t|≤1。",),
    example="edge = shade(MAIN, -0.3)\ninner = shade(MAIN, 0.55)",
    rank=5,
)
def shade(color, t):
    return _mix(color, "#FFFFFF", t) if t >= 0 else _mix(color, "#000000", -t)
