"""Earth / ocean / reef parts drawn like journal figures: globe, jet_stream,
atmosphere_section, coral_polyp, symbiont.
"""

from __future__ import annotations

import math
import random

from ..atomize_svg_to_slide._geometry import fmt
from ._bio_parts import _el, _look, _mix, _radial, _smooth, _linear
from ._envelope_parts import _capsule
from ._geometry import Box, _finite, _union
from ._geometry import label as _label
from ._construction import _inside
from ._help import _drawing_api
from ._parts import _INK, _circ, _finish, _style


def _d(pts, closed=True):
    return "M" + " L".join(f"{fmt(x)} {fmt(y)}" for x, y in pts) + (" Z" if closed else "")


def _text(x, y, content, fs, *, fill=_INK, anchor="middle", weight="bold", italic=False):
    t = _el(
        "text",
        x=x,
        y=y,
        font_size=fs,
        text_anchor=anchor,
        fill=fill,
        font_weight=weight,
        font_style="italic" if italic else None,
    )
    t.text = str(content)
    b = _label(str(content), font_size=fs, text_anchor=anchor, font_weight=weight).bounds
    return t, Box(x + b.x, y - fs + b.y, b.width, b.height)


def _head(x, y, ux, uy, size, color):
    """Filled arrowhead with its tip at (x, y) pointing along unit (ux, uy)."""
    bx, by, w = x - ux * size, y - uy * size, size * 0.5
    return _el(
        "path", d=_d([(x, y), (bx - uy * w, by + ux * w), (bx + uy * w, by - ux * w)]), fill=color, stroke="none"
    )


def _arc_arrow(cx, cy, rr, a0, a1, color, sw, head):
    """Circular arc from angle a0 to a1 (radians, screen) with an arrowhead at a1."""
    n = max(8, int(abs(a1 - a0) / 0.12))
    pts = [
        (cx + rr * math.cos(a0 + (a1 - a0) * k / n), cy + rr * math.sin(a0 + (a1 - a0) * k / n)) for k in range(n + 1)
    ]
    s = 1 if a1 > a0 else -1
    ux, uy = -math.sin(a1) * s, math.cos(a1) * s
    tip = (pts[-1][0] + ux * head * 0.6, pts[-1][1] + uy * head * 0.6)
    return [
        _el("path", d=_d(pts, False), fill="none", stroke=color, stroke_width=sw, stroke_linecap="round"),
        _head(tip[0], tip[1], ux, uy, head, color),
    ]


def _ortho(lat, lon, lat0, lon0):
    """Orthographic unit-sphere projection, screen y down; returns (x, y, cos_c)."""
    p, l, p0 = math.radians(lat), math.radians(lon - lon0), math.radians(lat0)
    x = math.cos(p) * math.sin(l)
    y = math.cos(p0) * math.sin(p) - math.sin(p0) * math.cos(p) * math.cos(l)
    c = math.sin(p0) * math.sin(p) + math.cos(p0) * math.cos(p) * math.cos(l)
    return x, -y, c


def _view_args(view, lon0, tilt):
    if view not in ("polar", "side"):
        raise ValueError('view must be "polar" or "side"')
    return (90.0 if view == "polar" else float(tilt)), float(lon0)


def globe_point(r, lat, lon, *, view="polar", lon0=0, tilt=25):
    """Local (x, y) of (lat, lon) on ``globe(r, view=…, lon0=…, tilt=…)`` (origin = globe center)."""
    lat0, lon0 = _view_args(view, lon0, tilt)
    x, y, c = _ortho(lat, lon, lat0, lon0)
    if c < 0:
        n = math.hypot(x, y) or 1
        x, y = x / n, y / n
    return (r * x, r * y)


def _ice_edge(lat_edge, seed):
    rnd = random.Random(seed)
    ph = [rnd.uniform(0, 2 * math.pi) for _ in range(3)]
    return [
        (
            lon,
            min(
                89.0,
                lat_edge
                + 2.6 * math.sin(math.radians(3 * lon) + ph[0])
                + 1.6 * math.sin(math.radians(5 * lon) + ph[1])
                + 0.8 * math.sin(math.radians(9 * lon) + ph[2]),
            ),
        )
        for lon in range(0, 360, 4)
    ]


def _graticule(r, lat0, lon0, color, sw, lats=(0, 30, 60), lon_step=30):
    lines = []
    for lat in lats:
        seg, segs = [], []
        for lon in range(0, 361, 4):
            x, y, c = _ortho(lat, lon, lat0, lon0)
            if c >= 0:
                seg.append((r * x, r * y))
            elif seg:
                segs.append(seg)
                seg = []
        if seg:
            segs.append(seg)
        if len(segs) > 1 and segs[0][0] == segs[-1][-1]:
            segs[0] = segs.pop() + segs[0]
        for s in segs:
            if len(s) > 1:
                closed = math.dist(s[0], s[-1]) < 1e-6
                lines.append(_d(s[:-1] if closed else s, closed))
    for lon in range(0, 360, lon_step):
        seg = []
        for lat in range(-90, 91, 3):
            x, y, c = _ortho(lat, lon, lat0, lon0)
            if c >= -1e-9:
                seg.append((r * x, r * y))
            elif len(seg) > 1:
                lines.append(_d(seg, False))
                seg = []
            else:
                seg = []
        if len(seg) > 1:
            lines.append(_d(seg, False))
    return _el("path", d=" ".join(lines), fill="none", stroke=color, stroke_width=sw, stroke_opacity=0.7)


def _jet_layers(r, *, lat, waves, amplitude, phase, highs, lows, width, color, arrows, rich, font_size, boost):
    """Jet ribbon + flow chevrons + H/L cells for a polar globe (local coords, center 0,0)."""
    if waves < 1:
        raise ValueError("waves must be ≥ 1")
    step = 360.0 / waves
    highs, lows = list(highs or ()), list(lows or ())
    if phase is None:
        phase = highs[0] if highs else ((lows[0] - step / 2) if lows else 0.0)
    ridges = [(phase + k * step) % 360 for k in range(waves)]
    troughs = [(phase + (k + 0.5) * step) % 360 for k in range(waves)]

    def snap(lon, cands):
        return min(cands, key=lambda c: abs((lon - c + 180) % 360 - 180))

    hs, ls = [snap(h, ridges) for h in highs], [snap(v, troughs) for v in lows]
    sig = step * 0.55

    def amp(lon):
        e = 1.0
        for c in hs + ls:
            dl = (lon - c + 180) % 360 - 180
            e += boost * math.exp(-((dl / sig) ** 2))
        return amplitude * e

    def jlat(lon):
        return max(5.0, min(87.0, lat + amp(lon) * math.cos(math.radians(waves * (lon - phase)))))

    def xy(la, lo):
        x, y, _ = _ortho(la, lo, 90, 0)
        return r * x, r * y

    pts = [xy(jlat(lo / 2), lo / 2) for lo in range(0, 720, 3)]
    # stacked strokes (dark rim → body → light core) instead of an evenodd ring: stays a native shape
    items = [
        _el(
            "path",
            d=_d(pts),
            fill="none",
            stroke=_mix(color, "#000000", 0.3),
            stroke_width=width,
            stroke_linejoin="round",
        ),
        _el("path", d=_d(pts), fill="none", stroke=color, stroke_width=width * 0.84, stroke_linejoin="round"),
    ]
    items.append(
        _el(
            "path",
            d=_d(pts),
            fill="none",
            stroke=_mix(color, "#FFFFFF", 0.55),
            stroke_width=width * 0.22,
            stroke_opacity=0.85,
        )
    )
    ports = {}
    # eastward (counter-clockwise from above the pole) flow chevrons
    n_ar = arrows if arrows is not None else 2 * waves
    for k in range(int(n_ar)):
        lo = (phase + (k + 0.25) * 360 / max(n_ar, 1)) % 360
        x0, y0 = xy(jlat(lo), lo)
        x1, y1 = xy(jlat(lo + 0.8), lo + 0.8)
        n = math.hypot(x1 - x0, y1 - y0) or 1
        ux, uy = (x1 - x0) / n, (y1 - y0) / n
        s = width * 0.42
        items.append(
            _el(
                "path",
                d=_d(
                    [
                        (x0 + ux * s, y0 + uy * s),
                        (x0 - ux * s - uy * s, y0 - uy * s + ux * s),
                        (x0 - ux * s * 0.35, y0 - uy * s * 0.35),
                        (x0 - ux * s + uy * s, y0 - uy * s - ux * s),
                    ]
                ),
                fill="#FFFFFF",
                stroke="none",
            )
        )
    for k, lo in enumerate(ridges):
        ports[f"ridge{k}"] = xy(jlat(lo), lo)
    for k, lo in enumerate(troughs):
        ports[f"trough{k}"] = xy(jlat(lo), lo)
    cells = []
    for k, lo in enumerate(hs):
        cells.append(("H", f"H{k}", lo, lat + amp(lo) * 0.1, "#C8463C"))
    for k, lo in enumerate(ls):
        cells.append(("L", f"L{k}", lo, lat - amp(lo) * 0.1, "#2F64B4"))
    fs = font_size or r * 0.11
    for letter, key, lo, la, col in cells:
        cx, cy = xy(la, lo)
        rr = fs * 0.78
        items.append(
            _el(
                "circle",
                cx=cx,
                cy=cy,
                r=rr,
                fill="#FFFFFF",
                fill_opacity=0.92,
                stroke=col,
                stroke_width=max(0.8, fs * 0.08),
            )
        )
        t, _ = _text(cx, cy + fs * 0.36, letter, fs, fill=col)
        items.append(t)
        if rich:
            # NH anticyclone turns clockwise, cyclone counter-clockwise (screen y down: clockwise = +angle)
            sgn = 1 if letter == "H" else -1
            for a in (0.0, math.pi):
                items += _arc_arrow(cx, cy, rr * 1.55, a - sgn * 0.2, a + sgn * 1.7, col, max(0.7, fs * 0.07), fs * 0.3)
        ports[key] = (cx, cy)
    return items, ports


def _jet_args(jet):
    base = dict(
        lat=50,
        waves=5,
        amplitude=10,
        phase=None,
        highs=(),
        lows=(),
        width=None,
        color="#2F6DB5",
        arrows=None,
        font_size=None,
        boost=0.6,
    )
    if jet is True:
        jet = {}
    unknown = set(jet) - set(base)
    if unknown:
        raise ValueError(f"unknown jet option(s): {sorted(unknown)}")
    base.update(jet)
    return base


@_drawing_api(
    "parts",
    purpose="地球（期刊风格）：正射投影球面，极视角（北极居中）或侧视角，海洋球面/经纬网/海冰，可叠加波动急流与 H/L 气压中心。",
    returns="Geometry（原点=球心；端口 pole/equator（极视角）或 north_pole/equator/south_pole（侧视），jet= 时含 ridge{k}/trough{k}/H{k}/L{k}，points= 给的命名点）",
    semantics=(
        'view="polar" 从北极上空俯视（lon0 经线朝下、向东逆时针），"side" 侧视（tilt 为球心纬度，lon0 为中央经线）。',
        'points={"站点A": (72, -40)} 把纬度/经度变成命名端口；globe_point(r, lat, lon, view=…) 返回同一局部坐标。',
        "sea_ice=纬度（如 75）画北冰洋海冰边缘；jet=dict(lat=50, waves=5, amplitude=10, highs=[经度], lows=[经度]) 等价于叠一层 jet_stream。",
        'style="rich" 加球面明暗与大气辉光（一个局部 SVG）；"flat" 全原生。H/L 的文字在部件内，其余标注在球外用 callout 指向端口。',
    ),
    example='g = d.place(globe(150, sea_ice=76, jet=dict(highs=[10], lows=[-80])), at=(220, 200), key="earth")\n'
    'd.callout("blk", "阻塞高压", g.port("H0"), at=(400, 60), font_size=13)',
    rank=20,
)
def globe(
    r,
    *,
    view="polar",
    lon0=0,
    tilt=25,
    graticule=True,
    sea_ice=None,
    jet=None,
    points=None,
    ocean="#A8CBE6",
    ice_fill="#F6FAFD",
    style="rich",
):
    rich = _style(style)
    _finite(r)
    lat0, lon0 = _view_args(view, lon0, tilt)
    holder, defs = _el("g"), _el("defs")
    holder.append(defs)
    sw = max(0.8, r * 0.008)
    holder.append(
        _el(
            "circle", cx=0, cy=0, r=r, fill=ocean, stroke=_mix(ocean, "#000000", 0.4), stroke_width=sw, data_outline="1"
        )
    )
    if sea_ice is not None:
        edge = _ice_edge(float(sea_ice), 11)
        pts = [globe_point(r, la, lo, view=view, lon0=lon0, tilt=tilt) for lo, la in edge]
        holder.append(
            _el(
                "path",
                d=_smooth(pts, closed=True),
                fill=ice_fill,
                stroke=_mix(ice_fill, "#5E87A8", 0.45),
                stroke_width=max(0.5, r * 0.005),
            )
        )
    if graticule:
        holder.append(
            _graticule(
                r,
                lat0,
                lon0,
                "#FFFFFF",
                max(0.4, r * 0.004),
                lats=(30, 60) if view == "polar" else (-60, -30, 0, 30, 60),
            )
        )
    R = r
    if rich:
        g = _el("radialGradient", id="gshade", cx="50%", cy="50%", r="50%", fx="34%", fy="30%")
        for off, col, op in (
            ("0", "#FFFFFF", 0.38),
            (".55", "#FFFFFF", 0),
            (".86", "#0B1E33", 0.08),
            ("1", "#0B1E33", 0.34),
        ):
            g.append(_el("stop", offset=off, stop_color=col, stop_opacity=op))
        defs.append(g)
        halo = _el("radialGradient", id="ghalo", cx="50%", cy="50%", r="50%")
        for off, col, op in ((".9", "#8EC5F0", 0), (".945", "#8EC5F0", 0.55), ("1", "#8EC5F0", 0)):
            halo.append(_el("stop", offset=off, stop_color=col, stop_opacity=op))
        defs.append(halo)
        R = r * 1.06
        look = _look()
        look.append(_el("circle", cx=0, cy=0, r=r - sw / 2, fill="url(#gshade)"))
        look.append(_el("circle", cx=0, cy=0, r=R, fill="url(#ghalo)"))
        holder.append(look)
    ports = {}
    if view == "polar":
        ports.update(pole=(0.0, 0.0), equator=globe_point(r, 0, lon0, view=view, lon0=lon0))
    else:
        ports.update(
            north_pole=globe_point(r, 90, lon0, view=view, lon0=lon0, tilt=tilt),
            south_pole=globe_point(r, -90, lon0, view=view, lon0=lon0, tilt=tilt),
            equator=globe_point(r, 0, lon0, view=view, lon0=lon0, tilt=tilt),
        )
    if jet:
        if view != "polar":
            raise ValueError('jet= is drawn on view="polar" globes')
        a = _jet_args(jet)
        items, jp = _jet_layers(r, rich=rich, **{**a, "width": a["width"] or r * 0.075})
        holder.extend(items)
        ports.update(jp)
    for name, (la, lo) in (points or {}).items():
        ports[name] = globe_point(r, la, lo, view=view, lon0=lon0, tilt=tilt)
    return _finish(holder, defs, Box(-R, -R, 2 * R, 2 * R), **ports)


@_drawing_api(
    "parts",
    purpose="极视角地球上的波动急流（单独一层）：闭合的蛇形急流带 + 向东流向箭头，脊（向极）放阻塞高压 H、槽（向赤道）放冷低压 L，并画反气旋/气旋环流。",
    returns="Geometry（外接框与同 r 的 globe 相同，place 在同一中心即对齐；端口 ridge{k}/trough{k}/H{k}/L{k}）",
    semantics=(
        "lat 为急流平均纬度，waves 为罗斯贝波数，amplitude 为纬向摆幅（度）；phase 为第一个脊的经度（省略时取 highs[0]）。",
        "highs/lows 为经度列表，自动吸附到最近的脊/槽并把该处波幅放大 (1+boost) 倍，表现 Ω 型阻塞。",
        '与 globe(r, view="polar", lon0=0) 同坐标；lon0≠0 的球请改用 globe(jet=...)。width 为急流带宽（默认 0.075r）。',
        'style="rich" 给 H/L 加环流小箭头；"flat" 只画 H/L 圆标。全部原生（急流带、箭头、文字）。',
    ),
    example='d.place(globe(150), at=(220, 200), key="g")\nj = d.place(jet_stream(150, waves=4, amplitude=12, highs=[20], lows=[-70]), at=(220, 200), key="jet")',
    rank=21,
)
def jet_stream(
    r,
    *,
    lat=50,
    waves=5,
    amplitude=10,
    phase=None,
    highs=(),
    lows=(),
    width=None,
    color="#2F6DB5",
    arrows=None,
    font_size=None,
    boost=0.6,
    style="rich",
):
    rich = _style(style)
    _finite(r, lat, amplitude)
    holder = _el("g")
    items, ports = _jet_layers(
        r,
        lat=lat,
        waves=int(waves),
        amplitude=amplitude,
        phase=phase,
        highs=highs,
        lows=lows,
        width=width or r * 0.075,
        color=color,
        arrows=arrows,
        rich=rich,
        font_size=font_size,
        boost=boost,
    )
    items[0].set("data-outline", "1")
    holder.extend(items)
    return _finish(holder, None, Box(-r, -r, 2 * r, 2 * r), **ports)


_ATM_NAMES = {
    "troposphere": "对流层",
    "tropopause": "对流层顶",
    "stratosphere": "平流层",
    "jet": "急流",
    "vortex": "极涡",
    "ice": "海冰",
    "ocean": "海洋",
    "pole": "北极",
    "equator": "赤道",
}


@_drawing_api(
    "parts",
    purpose='大气经向剖面（纬度-高度，期刊风格）：渐变天空分对流层/平流层，赤道高极地低的对流层顶（副热带断裂），急流核 "J"，平流层极涡，底部海冰与海洋。',
    returns="Geometry（原点在中心；端口 tropopause/jet/vortex/ice/ocean/troposphere/stratosphere/pole/equator，lat{N} 为每 10° 的地面点；warming=True 时有 warming）",
    semantics=(
        '横轴左为赤道 (lat_range[0])、右为极地 (lat_range[1])，纵轴 0–z_top km；pole_side="left" 镜像。',
        'labels={"troposphere": "Troposphere", ...} 覆盖默认中文名，值为 None 不写；axes=True 画纬度/高度刻度。',
        'jet_core=True 或纬度（默认 45）画急流核椭圆 "J"；vortex=True 画平流层极涡（旋转箭头 + 冷核）；ice/ocean 画底部海冰与海洋（ice 可给起始纬度）。',
        'warming=True 在极地低层画暖色“北极放大”增温区；style="rich" 加天空/海洋渐变（一个局部 SVG），"flat" 全原生。',
    ),
    example='s = d.place(atmosphere_section(420, 260, warming=True), at=(660, 200), key="sec")\n'
    'd.callout("j", "急流减弱、经向化", s.port("jet"), at=(560, 40), font_size=13)',
    rank=22,
)
def atmosphere_section(
    width=420,
    height=260,
    *,
    layers=("troposphere", "tropopause", "stratosphere"),
    vortex=True,
    jet_core=True,
    ice=True,
    ocean=True,
    warming=False,
    labels=None,
    lat_range=(0, 90),
    z_top=30,
    pole_side="right",
    axes=True,
    font_size=12,
    sky="#DCEBF7",
    strat="#B9C9E6",
    style="rich",
):
    rich = _style(style)
    _finite(width, height)
    if pole_side not in ("left", "right"):
        raise ValueError('pole_side must be "left" or "right"')
    names = dict(_ATM_NAMES)
    names.update(labels or {})
    W, H = float(width), float(height)
    fs = font_size
    lat0, lat1 = lat_range
    sea_h = H * 0.1 if ocean else 0
    ground = H - sea_h  # z = 0 line
    zk = ground / float(z_top)

    def X(lat):
        t = (lat - lat0) / float(lat1 - lat0)
        return W * (t if pole_side == "right" else 1 - t)

    def Y(z):
        return ground - z * zk

    def trop_z(lat):  # km; subtropical break near 30–35°
        a = abs(lat)
        return 9.0 + 7.5 / (1 + math.exp((a - 33) / 3.2)) - 1.2 * max(0, (a - 60) / 30)

    holder, defs = _el("g"), _el("defs")
    holder.append(defs)
    holder.append(
        _el(
            "rect",
            x=0,
            y=0,
            width=W,
            height=H,
            fill=sky,
            stroke=_mix(sky, "#000000", 0.35),
            stroke_width=1,
            data_outline="1",
        )
    )
    lats = [lat0 + (lat1 - lat0) * k / 60 for k in range(61)]
    trop = [(X(la), Y(trop_z(la))) for la in lats]
    strat_poly = [(X(lat0), 0), (X(lat1), 0)] + trop[::-1]
    holder.append(_el("path", d=_d(strat_poly), fill=strat, stroke="none"))
    if ocean:
        holder.append(_el("rect", x=0, y=ground, width=W, height=sea_h, fill="#3F7FB3", stroke="none"))
    if rich:
        defs.append(
            _linear("atrop", [("0", _mix(sky, "#FFFFFF", 0.55)), ("1", _mix(sky, "#7FA9CF", 0.25))], x2="0", y2="1")
        )
        defs.append(
            _linear("astrat", [("0", _mix(strat, "#3E4F8A", 0.35)), ("1", _mix(strat, "#FFFFFF", 0.2))], x2="0", y2="1")
        )
        look = _look()
        look.append(_el("path", d=_d([(X(lat0), ground), (X(lat1), ground)] + trop[::-1]), fill="url(#atrop)"))
        look.append(_el("path", d=_d(strat_poly), fill="url(#astrat)"))
        if ocean:
            defs.append(_linear("aocean", [("0", "#5B9BCB"), ("1", "#1F4F7E")]))
            look.append(_el("rect", x=0, y=ground, width=W, height=sea_h, fill="url(#aocean)"))
        holder.append(look)
    boxes = [Box(0, 0, W, H)]
    ports = {}
    pole_x, eq_x = X(lat1), X(lat0)
    if warming:
        # surface-trapped polar warming: a quarter dome hugging the pole wall, strongest at the surface
        wx, wz = X(lat1 - (lat1 - lat0) * 0.3), 4.5
        dome = [
            (pole_x + (wx - pole_x) * math.cos(a), ground - wz * zk * math.sin(a))
            for a in (math.pi / 2 * k / 24 for k in range(25))
        ]
        for k, (s, op) in enumerate(((1, 0.3), (0.62, 0.38))):
            pts = [(pole_x + (x - pole_x) * s, ground - (ground - y) * s) for x, y in dome]
            holder.append(
                _el("path", d=_d(pts[::-1] + [(pole_x, ground)]), fill="#E8743B", fill_opacity=op, stroke="none")
            )
        ports["warming"] = (pole_x + (wx - pole_x) * 0.45, ground - wz * zk * 0.55)
    if ocean:
        ports["ocean"] = (X(lat0 + (lat1 - lat0) * 0.35), ground + sea_h / 2)
    if ice:
        ice_lat = 70 if ice is True else float(ice)
        x0, x1 = sorted((X(ice_lat), pole_x))
        th = max(4, H * 0.028)
        rnd = random.Random(4)
        top = (
            [(x0, ground)]
            + [(x0 + (x1 - x0) * k / 14, ground - th * rnd.uniform(0.7, 1.2)) for k in range(1, 14)]
            + [(x1, ground - th)]
        )
        bot = (
            [(x1, ground + th * 1.4)]
            + [(x1 - (x1 - x0) * k / 14, ground + th * rnd.uniform(0.8, 1.6)) for k in range(1, 14)]
            + [(x0 + 2, ground + th * 0.4)]
        )
        holder.append(
            _el("path", d=_d(top + bot), fill="#F4F9FC", stroke="#7FA3BF", stroke_width=0.8, stroke_linejoin="round")
        )
        ports["ice"] = ((x0 + x1) / 2, ground - th)
    if "tropopause" in layers:
        holder.append(
            _el("path", d=_d(trop, False), fill="none", stroke="#5A6B80", stroke_width=1.6, stroke_dasharray="6 3")
        )
    ports["tropopause"] = (X(lat0 + (lat1 - lat0) * 0.7), Y(trop_z(lat0 + (lat1 - lat0) * 0.7)))
    if jet_core:
        jl = 45 if jet_core is True else float(jet_core)
        jx, jy = X(jl), Y(trop_z(jl) - 1.5)
        rx, ry = W * 0.07, H * 0.075
        cols = ("#F7D9C4", "#EFA982", "#D6604D")
        for k, c in enumerate(cols):
            s = 1 - k * 0.3
            holder.append(
                _el(
                    "ellipse",
                    cx=jx,
                    cy=jy,
                    rx=rx * s,
                    ry=ry * s,
                    fill=c,
                    stroke=_mix(c, "#000000", 0.25) if k == 0 else "none",
                    stroke_width=0.8,
                )
            )
        t, b = _text(jx, jy + fs * 0.38, "J", fs * 1.05, fill="#FFFFFF")
        holder.append(t)
        ports["jet"] = (jx, jy - ry)
    if vortex:
        vx, vy = X(lat1 - (lat1 - lat0) * 0.12), Y(trop_z(lat1) + (z_top - trop_z(lat1)) * 0.52)
        vr = min(W * 0.09, (Y(trop_z(lat1)) - Y(z_top)) * 0.32)
        holder.append(
            _el("ellipse", cx=vx, cy=vy, rx=vr * 1.35, ry=vr, fill="#4B5FA8", fill_opacity=0.28, stroke="none")
        )
        holder.append(
            _el("ellipse", cx=vx, cy=vy, rx=vr * 0.55, ry=vr * 0.42, fill="#2D3E86", fill_opacity=0.6, stroke="none")
        )
        col = "#24336F"
        for a0 in (0.3, math.pi + 0.3):
            n = 14
            pts = [
                (vx + vr * 1.2 * math.cos(a0 + 2.2 * k / n), vy + vr * 0.85 * math.sin(a0 + 2.2 * k / n))
                for k in range(n + 1)
            ]
            holder.append(
                _el("path", d=_d(pts, False), fill="none", stroke=col, stroke_width=1.4, stroke_linecap="round")
            )
            a1 = a0 + 2.2
            ux, uy = -math.sin(a1) * 1.2, math.cos(a1) * 0.85
            nn = math.hypot(ux, uy)
            holder.append(_head(pts[-1][0] + ux / nn * 3, pts[-1][1] + uy / nn * 3, ux / nn, uy / nn, 6, col))
        ports["vortex"] = (vx, vy - vr)
        if names.get("vortex"):
            t, b = _text(vx, vy + fs * 0.36, names["vortex"], fs, fill="#FFFFFF")
            holder.append(t)
    # layer labels (inside, upper-left / lower-left of equator side)
    pad = fs * 0.6
    anc = "start" if pole_side == "right" else "end"
    lx = pad if pole_side == "right" else W - pad
    if "troposphere" in layers and names.get("troposphere"):
        t, b = _text(lx, Y(trop_z(lat0) * 0.5), names["troposphere"], fs, anchor=anc, fill="#2B4A6B")
        holder.append(t)
    ports["troposphere"] = (X(lat0 + (lat1 - lat0) * 0.25), Y(trop_z(lat0) * 0.45))
    if "stratosphere" in layers and names.get("stratosphere"):
        t, b = _text(
            lx, Y(z_top) + fs * 1.6, names["stratosphere"], fs, anchor=anc, fill="#FFFFFF" if rich else "#26315A"
        )
        holder.append(t)
    ports["stratosphere"] = (X(lat0 + (lat1 - lat0) * 0.25), Y((z_top + trop_z(lat0)) / 2))
    if "tropopause" in layers and names.get("tropopause"):
        tl = lat0 + (lat1 - lat0) * 0.16
        t, b = _text(
            X(tl),
            Y(trop_z(tl)) - fs * 0.45,
            names["tropopause"],
            fs * 0.88,
            anchor="middle",
            fill="#46566B",
            weight="normal",
        )
        holder.append(t)
    if ice and names.get("ice"):
        pass  # sea-ice is labelled via its port (thin strip leaves no room for inside text)
    if ocean and names.get("ocean"):
        t, b = _text(
            X(lat0 + (lat1 - lat0) * 0.5),
            ground + sea_h / 2 + fs * 0.33,
            names["ocean"],
            fs * 0.85,
            fill="#FFFFFF",
            weight="normal",
        )
        holder.append(t)
    if axes:
        ink = "#3A4654"
        tick = []
        for la in range(int(lat0), int(lat1) + 1, 30):
            x = X(la)
            tick.append(f"M{fmt(x)} {fmt(H)} L{fmt(x)} {fmt(H + 4)}")
            txt = names["equator"] if la == 0 else (names["pole"] if la == 90 else f"{la}°N")
            t, b = _text(
                x,
                H + 4 + fs,
                txt,
                fs * 0.85,
                fill=ink,
                weight="normal",
                anchor="start" if x < 1 else ("end" if x > W - 1 else "middle"),
            )
            holder.append(t)
            boxes.append(b)
        for z in range(0, int(z_top) + 1, 10):
            y = Y(z)
            ax = 0 if pole_side == "right" else W
            sgn = -1 if pole_side == "right" else 1
            tick.append(f"M{fmt(ax)} {fmt(y)} L{fmt(ax + sgn * 4)} {fmt(y)}")
            t, b = _text(
                ax + sgn * 6,
                y + fs * 0.3,
                f"{z}",
                fs * 0.85,
                fill=ink,
                weight="normal",
                anchor="end" if sgn < 0 else "start",
            )
            holder.append(t)
            boxes.append(b)
        t, b = _text(
            (0 if pole_side == "right" else W) + (-1 if pole_side == "right" else 1) * 6,
            Y(z_top) - fs * 1.15,
            "km",
            fs * 0.85,
            fill=ink,
            weight="normal",
            anchor="end" if pole_side == "right" else "start",
        )
        holder.append(t)
        boxes.append(b)
        holder.append(_el("path", d=" ".join(tick), stroke=ink, stroke_width=1, fill="none"))
    ports.update(pole=(pole_x, ground), equator=(eq_x, ground))
    for la in range(int(lat0), int(lat1) + 1, 10):
        ports[f"lat{la}"] = (X(la), ground)
    return _finish(holder, defs, _union(boxes), **ports)


def _cr(ctrl, per=10):
    """Sample a Catmull-Rom spline through ctrl points (open)."""
    out = []
    n = len(ctrl)
    for i in range(n - 1):
        p0, p1, p2 = ctrl[max(i - 1, 0)], ctrl[i], ctrl[i + 1]
        p3 = ctrl[min(i + 2, n - 1)]
        for k in range(per):
            t = k / per
            t2, t3 = t * t, t * t * t
            out.append(
                tuple(
                    0.5
                    * (
                        2 * p1[j]
                        + (-p0[j] + p2[j]) * t
                        + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                        + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3
                    )
                    for j in (0, 1)
                )
            )
    out.append(tuple(ctrl[-1]))
    return out


def _normals(pts):
    ns = []
    for i in range(len(pts)):
        a, b = pts[max(i - 1, 0)], pts[min(i + 1, len(pts) - 1)]
        tx, ty = b[0] - a[0], b[1] - a[1]
        L = math.hypot(tx, ty) or 1
        ns.append((-ty / L, tx / L))
    return ns


def _offset(pts, d):
    """Offset polyline; d may be a number or a list (one per point)."""
    ns = _normals(pts)
    ds = d if isinstance(d, (list, tuple)) else [d] * len(pts)
    return [(p[0] + n[0] * k, p[1] + n[1] * k) for p, n, k in zip(pts, ns, ds)]


def _band(pts, a, b):
    return _offset(pts, a) + _offset(pts, b)[::-1]


def _mirror(pts):
    return [(-x, y) for x, y in pts]


def _along(pts, spacing, start=0.0):
    """Points every ``spacing`` along a polyline (with unit normals)."""
    out, acc, nxt = [], 0.0, start
    ns = _normals(pts)
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        L = math.dist(a, b)
        while L > 0 and nxt <= acc + L:
            t = (nxt - acc) / L
            out.append(((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t), ns[i]))
            nxt += spacing
        acc += L
    return out


def _oval(cx, cy, rx, ry, ang):
    c, s = math.cos(ang), math.sin(ang)
    pts = [
        (cx + rx * math.cos(t) * c - ry * math.sin(t) * s, cy + rx * math.cos(t) * s + ry * math.sin(t) * c)
        for t in (2 * math.pi * k / 10 for k in range(10))
    ]
    return _smooth(pts, closed=True)


@_drawing_api(
    "parts",
    purpose="共生虫黄藻（Symbiodiniaceae，教科书级放大）：宿主共生体膜包裹的藻细胞，周缘分叶叶绿体（类囊体条纹）、带淀粉鞘与柄的蛋白核、含凝聚染色体的甲藻核、红褐色积累体、脂滴与淀粉粒。",
    returns="Geometry（原点在中心；端口 symbiosome/cell_wall/chloroplast/pyrenoid/nucleus/accumulation_body/lipid/starch）",
    semantics=(
        "r 为共生体膜半径；color 为叶绿体色（金褐色，含多甲藻素），其余颜色自动推导。",
        "stressed=True 表现热胁迫：叶绿体褪色、类囊体断裂（rich）、积累体增大，用于白化对比。",
        'style="rich" 加类囊体条纹与球面明暗（一个局部 SVG）；"flat" 全原生。文字标注在外面用 callout 指向端口。',
    ),
    example='z = d.place(symbiont(60), at=(760, 200), key="zoox")\nd.callout("pyr", "蛋白核", z.port("pyrenoid"), at=(840, 90), font_size=12)',
    rank=24,
)
def symbiont(r=40, *, color="#B8862B", host="#9C7DB0", stressed=False, style="rich", seed=3):
    rich = _style(style)
    _finite(r)
    rnd = random.Random(seed)
    holder, defs = _el("g"), _el("defs")
    holder.append(defs)
    chl = _mix(color, "#FFFFFF", 0.45) if stressed else color
    rc = r * 0.84
    # symbiosome (host-derived membrane complex): thin outer ring, pale interface space
    holder.append(
        _el(
            "circle",
            cx=0,
            cy=0,
            r=r,
            fill=_mix(host, "#FFFFFF", 0.86),
            stroke=host,
            stroke_width=max(0.6, r * 0.025),
            data_outline="1",
        )
    )
    holder.append(
        _el(
            "circle",
            cx=0,
            cy=0,
            r=r * 0.935,
            fill="none",
            stroke=_mix(host, "#FFFFFF", 0.35),
            stroke_width=max(0.4, r * 0.012),
        )
    )
    holder.append(
        _el(
            "circle",
            cx=0,
            cy=0,
            r=rc,
            fill=_mix(color, "#FFF6DC", 0.82),
            stroke=_mix(color, "#3B2A10", 0.45),
            stroke_width=max(0.8, r * 0.04),
        )
    )
    lobes, segs = [], 7
    for k in range(segs):
        a0 = 2 * math.pi * k / segs + 0.12 + rnd.uniform(-0.05, 0.05)
        a1 = a0 + 2 * math.pi / segs - 0.2
        if 3.4 < (a0 + a1) / 2 < 4.4:  # gap where the nucleus sits
            continue
        ro, ri = rc * 0.9, rc * rnd.uniform(0.6, 0.66)
        n = 10
        outer = [(ro * math.cos(a0 + (a1 - a0) * j / n), ro * math.sin(a0 + (a1 - a0) * j / n)) for j in range(n + 1)]
        bulge = lambda j: ri * (1 - 0.1 * math.sin(math.pi * j / n))  # lens-shaped lobe, thicker mid-lobe
        inner = [
            (bulge(j) * math.cos(a1 - (a1 - a0) * j / n), bulge(j) * math.sin(a1 - (a1 - a0) * j / n))
            for j in range(n + 1)
        ]
        lobes.append((a0, a1, ri, ro, outer + inner))
    holder.append(
        _el(
            "path",
            d=" ".join(_smooth(p, closed=True) for *_, p in lobes),
            fill=chl,
            stroke=_mix(chl, "#000000", 0.35),
            stroke_width=max(0.5, r * 0.015),
        )
    )
    # pyrenoid with starch sheath and stalks to the chloroplast
    px, py, pr = r * 0.1, -r * 0.12, r * 0.17
    stalk = " ".join(
        f"M{fmt(px + pr * math.cos(a))} {fmt(py + pr * math.sin(a))} "
        f"L{fmt(rc * 0.64 * math.cos(a))} {fmt(rc * 0.64 * math.sin(a))}"
        for a in (-1.1, 0.2, 1.4)
    )
    holder.append(_el("path", d=stalk, stroke=chl, stroke_width=r * 0.07, fill="none", stroke_linecap="round"))
    holder.append(
        _el(
            "circle",
            cx=px,
            cy=py,
            r=pr * 1.38,
            fill="#F5EEDB",
            stroke=_mix(chl, "#000000", 0.2),
            stroke_width=max(0.4, r * 0.012),
        )
    )
    holder.append(_el("circle", cx=px, cy=py, r=pr, fill=_mix(chl, "#6E7B3A", 0.45), stroke="none"))
    nx, ny, nr = -r * 0.36, r * 0.1, r * 0.25
    holder.append(
        _el(
            "ellipse",
            cx=nx,
            cy=ny,
            rx=nr,
            ry=nr * 1.15,
            fill="#D9CCE3",
            stroke="#7D6890",
            stroke_width=max(0.5, r * 0.018),
        )
    )
    chrom = []
    for k in range(9):
        a, rr = rnd.uniform(0, 2 * math.pi), nr * math.sqrt(rnd.uniform(0, 0.6))
        cx, cy = nx + rr * math.cos(a), ny + rr * math.sin(a) * 1.1
        ang = rnd.uniform(0, math.pi)
        L = nr * 0.22
        chrom.append(
            f"M{fmt(cx - L * math.cos(ang))} {fmt(cy - L * math.sin(ang))} "
            f"Q{fmt(cx + L * 0.5 * math.sin(ang))} {fmt(cy - L * 0.5 * math.cos(ang))} "
            f"{fmt(cx + L * math.cos(ang))} {fmt(cy + L * math.sin(ang))}"
        )
    holder.append(
        _el(
            "path",
            d=" ".join(chrom),
            fill="none",
            stroke="#5C4670",
            stroke_width=max(0.6, r * 0.03),
            stroke_linecap="round",
        )
    )
    # accumulation body (red-brown), lipid droplets, starch grains
    ab = (r * 0.3, r * 0.38, r * (0.2 if stressed else 0.13))
    holder.append(
        _el("circle", cx=ab[0], cy=ab[1], r=ab[2], fill="#A4442F", stroke="#6E2A1C", stroke_width=max(0.4, r * 0.012))
    )
    lipids = [(-r * 0.02, r * 0.42, r * 0.07), (r * 0.42, -r * 0.02, r * 0.06)]
    holder.append(
        _el(
            "path",
            d=" ".join(_circ(*c) for c in lipids),
            fill="#F6E27A",
            stroke="#C9A93A",
            stroke_width=max(0.3, r * 0.01),
        )
    )
    starch = [(-r * 0.12, -r * 0.4, 0.3), (r * 0.02, r * 0.2, -0.5)]
    holder.append(
        _el(
            "path",
            d=" ".join(_oval(x, y, r * 0.07, r * 0.045, a) for x, y, a in starch),
            fill="#FFFFFF",
            stroke="#C8BFA8",
            stroke_width=max(0.3, r * 0.01),
        )
    )
    if rich:
        look = _look()
        sw = max(0.35, r * 0.01)
        tl = []
        for a0, a1, ri, ro, _ in lobes:
            for f in (0.3, 0.5, 0.7):
                rr = ri + (ro - ri) * f
                pieces = [(a0 + 0.04, a1 - 0.04)]
                if stressed:  # swollen, broken thylakoids
                    m = (a0 + a1) / 2
                    pieces = [(a0 + 0.04, m - 0.08), (m + 0.05, a1 - 0.04)]
                for b0, b1 in pieces:
                    n = 8
                    tl.append(
                        _d(
                            [
                                (rr * math.cos(b0 + (b1 - b0) * j / n), rr * math.sin(b0 + (b1 - b0) * j / n))
                                for j in range(n + 1)
                            ],
                            False,
                        )
                    )
        look.append(
            _el(
                "path",
                d=" ".join(tl),
                fill="none",
                stroke=_mix(chl, "#000000", 0.4),
                stroke_width=sw,
                stroke_opacity=0.75,
            )
        )
        defs.append(_radial("zshade", "#FFFFFF", "#000000", fx=0.36, fy=0.3))
        g = defs[-1]
        g[0].set("stop-opacity", ".35")
        g[1].set("stop-opacity", ".14")
        look.append(_el("circle", cx=0, cy=0, r=rc, fill="url(#zshade)"))
        holder.append(look)
    a_mid = (lobes[0][0] + lobes[0][1]) / 2
    return _finish(
        holder,
        defs,
        Box(-r, -r, 2 * r, 2 * r),
        symbiosome=(r, 0),
        cell_wall=(0, -rc),
        chloroplast=(rc * 0.76 * math.cos(a_mid), rc * 0.76 * math.sin(a_mid)),
        pyrenoid=(px, py),
        nucleus=(nx, ny),
        accumulation_body=ab[:2],
        lipid=lipids[0][:2],
        starch=starch[0][:2],
    )


def _tube(ctrl, w0, w1, per=10):
    """Closed outline of a tapering tube along ctrl (open base, rounded tip)."""
    c = _cr(ctrl, per)
    n = len(c)
    ws = [(w0 + (w1 - w0) * i / (n - 1)) / 2 for i in range(n)]
    left, right = _offset(c, ws), _offset(c, [-w for w in ws])
    (tx, ty), (ax, ay) = c[-1], c[-2]
    base = math.atan2(ty - ay, tx - ax)
    cap = [
        (
            tx + ws[-1] * math.cos(base + math.pi / 2 - math.pi * k / 8),
            ty + ws[-1] * math.sin(base + math.pi / 2 - math.pi * k / 8),
        )
        for k in range(1, 8)
    ]
    return left + cap + right[::-1], c


@_drawing_api(
    "parts",
    purpose="珊瑚虫纵切面（教科书级）：带刺丝囊的触手、口盘与口/咽、外胚层-中胶层-内胚层（含虫黄藻）组织、腔肠、钙质成骨外胚层与文石骨骼（生长纹/纤维束）；bleached=True 为白化态。",
    returns="Geometry（原点在中心；端口 mouth/oral_disc/tentacle{k}/tentacle_tip{k}/ectoderm/mesoglea/gastrodermis/coelenteron/calicoblastic/skeleton/symbiont{k}，白化时另有 expelled{k}）",
    semantics=(
        "width 为部件宽度（高≈宽）；tentacles 为剖面上的触手数（左右对称，偶数）；symbionts 为每 100px 组织长度的共生藻数（默认 9）。",
        "口侧组织（触手/口盘/体壁/共肉）外层为外胚层、内层为含共生藻的内胚层；骨骼侧组织为内胚层 + 钙质成骨外胚层，紧贴文石骨骼。",
        "bleached=True：组织褪色、共生藻约剩 1/4，部分被排出到腔肠与口外（端口 expelled{k}）；tissue/symbiont_color/skeleton 可改色。",
        'style="rich" 加文石纤维束、腔肠与组织明暗（一个局部 SVG）；"flat" 全原生。文字标注在外面用 callout 指向端口；放大单个藻细胞用 symbiont()。',
    ),
    example='p = d.place(coral_polyp(280), at=(200, 220), key="healthy")\n'
    'd.callout("gd", "内胚层（含虫黄藻）", p.port("gastrodermis"), at=(330, 60), font_size=12)',
    rank=23,
)
def coral_polyp(
    width=300,
    *,
    tentacles=4,
    bleached=False,
    symbionts=None,
    tissue="#D79AA6",
    symbiont_color="#A8741E",
    skeleton="#EEE6D3",
    water="#E4F0F7",
    style="rich",
    seed=2,
):
    rich = _style(style)
    _finite(width)
    tentacles = max(0, int(tentacles))
    if tentacles % 2:
        raise ValueError("tentacles must be even (the section is mirror-symmetric)")
    rnd = random.Random(seed)
    s = width / 300.0
    P = lambda pts: [(x * s, y * s) for x, y in pts]
    if bleached:
        tissue = _mix(tissue, "#FFFFFF", 0.55)
    ecto = _mix(tissue, "#FFFFFF", 0.42)
    gastro = _mix(tissue, "#E0B98A", 0.25) if not bleached else _mix(tissue, "#F2E6DC", 0.3)
    meso = _mix(tissue, "#4A2030", 0.45)
    calico = _mix(tissue, "#B38A6A", 0.35)
    T = 18 * s  # tissue thickness
    oral = _cr(
        P(
            [
                (150, 186),
                (112, 186),
                (86, 182),
                (72, 166),
                (66, 142),
                (70, 116),
                (80, 98),
                (66, 86),
                (44, 80),
                (26, 86),
                (18, 102),
                (17, 130),
            ]
        ),
        8,
    )
    aboral = _cr(P([(150, 214), (110, 214), (78, 213), (64, 224), (54, 244), (34, 258), (0, 262)]), 8)
    skel_top = _offset(aboral, -T / 2)
    holder, defs = _el("g"), _el("defs")
    holder.append(defs)
    sk = skel_top + [(0, 300 * s)]
    sk_poly = [(150 * s, 300 * s)] + sk + _mirror(sk[::-1]) + [(-150 * s, 300 * s)]
    sk_poly = [(150 * s, skel_top[0][1])] + sk_poly[1:]
    sk_poly = (
        [(150 * s, 300 * s), (150 * s, skel_top[0][1])]
        + skel_top[1:]
        + _mirror(skel_top[::-1])[:-1]
        + [(-150 * s, skel_top[0][1]), (-150 * s, 300 * s)]
    )
    holder.append(
        _el(
            "path",
            d=_d(sk_poly),
            fill=skeleton,
            stroke=_mix(skeleton, "#5A4A30", 0.45),
            stroke_width=max(0.6, s),
            data_outline="1",
        )
    )
    # growth bands parallel to the skeleton surface
    bands = []
    for k in range(1, 5):
        off = _offset(aboral, -T / 2 - k * 9 * s)
        seg = [p for p in off if p[1] < 298 * s]
        if len(seg) > 2:
            bands.append(_d(seg, False))
            bands.append(_d(_mirror(seg), False))
    holder.append(
        _el(
            "path",
            d=" ".join(bands),
            fill="none",
            stroke=_mix(skeleton, "#8A7650", 0.45),
            stroke_width=max(0.4, 0.6 * s),
            stroke_opacity=0.8,
        )
    )
    cav_r = _offset(oral, -T / 2)[:]
    cav_b = _offset(aboral, T / 2)
    cav = cav_r[:-1] + [(0, cav_r[-2][1])] + _mirror(cav_r[:-1])[::-1][:0]
    cav = [cav_r[0]] + cav_r[1:] + [(0, cav_r[-1][1] + 8 * s)]
    cav_poly = cav + _mirror(cav[::-1]) + _mirror(cav_b) + cav_b[::-1]
    cav_poly = cav[:] + [(-x, y) for x, y in cav[::-1]] + [(-x, y) for x, y in cav_b] + cav_b[::-1]
    holder.append(_el("path", d=_d(cav_poly), fill=_mix(water, tissue, 0.12), stroke="none"))
    ports = {}
    m = tentacles // 2
    nem = []
    tip_k = 0
    tent_shapes = []
    for side in (1, -1):
        for j in range(m):
            f = (j + 0.5) / max(m, 1)
            bx = (58 - 30 * f) * s
            bi = min(range(len(oral)), key=lambda i: abs(oral[i][0] - bx) + (0 if oral[i][1] < 100 * s else 999))
            B = oral[bi]
            ang = math.radians(62 - 44 * f)  # from vertical, outward
            L = (80 - 14 * f) * s
            ux, uy = math.sin(ang), -math.cos(ang)
            bend = (12 + 6 * f) * s
            ctrl = [
                B,
                (B[0] + ux * L * 0.45 - uy * bend * 0.2, B[1] + uy * L * 0.45 + ux * bend * 0.2),
                (B[0] + ux * L * 0.8 + uy * bend * 0.6, B[1] + uy * L * 0.8 - ux * bend * 0.6),
                (B[0] + ux * L + uy * bend * 1.1, B[1] + uy * L - ux * bend * 1.1),
            ]
            if side < 0:
                ctrl = _mirror(ctrl)
            w0, w1 = 27 * s, 9 * s
            outer, c = _tube(ctrl, w0, w1)
            mid, _ = _tube(ctrl, w0 * 0.62, w1 * 0.5)
            lumen, _ = _tube(ctrl, w0 * 0.26, w1 * 0.16)
            tent_shapes.append((outer, mid, lumen, c, w0, w1))
            ports[f"tentacle_tip{tip_k}"] = c[-1]
            ports[f"tentacle{tip_k}"] = c[len(c) // 2]
            ws = [(w0 + (w1 - w0) * i / (len(c) - 1)) / 2 for i in range(len(c))]
            for sg in (1, -1):
                edge = _offset(c, [sg * w * 0.72 for w in ws])
                for (x, y), (nx_, ny_) in _along(edge[len(edge) // 5 :], 6.5 * s, 2 * s):
                    a = math.atan2(ny_, nx_)
                    nem.append(_oval(x, y, 1.9 * s, 1.1 * s, a))
            tip_k += 1
    for outer, mid, lumen, c, w0, w1 in tent_shapes:
        holder.append(
            _el(
                "path",
                d=_smooth(outer, closed=True),
                fill=ecto,
                stroke=_mix(ecto, "#5A2A38", 0.4),
                stroke_width=max(0.5, 0.8 * s),
            )
        )
        holder.append(
            _el("path", d=_smooth(mid, closed=True), fill=gastro, stroke=meso, stroke_width=max(0.4, 0.7 * s))
        )
        holder.append(_el("path", d=_smooth(lumen, closed=True), fill=_mix(water, tissue, 0.12), stroke="none"))

    def band_pair(line, a, b):
        poly = _band(line, a, b)
        return _d(poly) + " " + _d(_mirror(poly))

    holder.append(
        _el(
            "path",
            d=band_pair(oral, -T / 2, T / 2),
            fill=ecto,
            stroke=_mix(ecto, "#5A2A38", 0.4),
            stroke_width=max(0.5, 0.8 * s),
        )
    )
    holder.append(_el("path", d=band_pair(oral, -T / 2, T * 0.08), fill=gastro, stroke="none"))
    holder.append(
        _el(
            "path",
            d=band_pair(aboral, -T / 2, T / 2),
            fill=gastro,
            stroke=_mix(gastro, "#5A2A38", 0.35),
            stroke_width=max(0.5, 0.8 * s),
        )
    )
    holder.append(_el("path", d=band_pair(aboral, -T / 2, -T * 0.2), fill=calico, stroke="none"))
    mo, ma = _offset(oral, T * 0.08), _offset(aboral, -T * 0.2)
    holder.append(
        _el(
            "path",
            d=" ".join(_d(p, False) for p in (mo, _mirror(mo), ma, _mirror(ma))),
            fill="none",
            stroke=meso,
            stroke_width=max(0.6, 1.0 * s),
        )
    )
    disc = [p for p in _offset(oral, T * 0.32) if p[1] < 100 * s and p[0] > 16 * s]
    for (x, y), (nx_, ny_) in _along(disc, 7 * s, 3 * s):
        for sx in (1, -1):
            nem.append(_oval(sx * x, y, 1.9 * s, 1.1 * s, math.atan2(ny_, sx * nx_)))
    if nem:
        holder.append(
            _el(
                "path",
                d=" ".join(nem),
                fill="#FFFFFF",
                stroke=_mix(tissue, "#3C1E28", 0.6),
                stroke_width=max(0.35, 0.5 * s),
            )
        )
    dens = (9 if symbionts is None else float(symbionts)) / (100 * s)
    keep = 0.25 if bleached else 1.0
    zr = T * 0.125
    cells = []
    lines = [(_offset(oral, -T * 0.2), 1), (_offset(aboral, T * 0.18), 1)]
    for line, _ in lines:
        for half in (1, -1):
            pts = line if half > 0 else _mirror(line)
            for (x, y), _n in _along(pts, 1 / max(dens, 1e-6), rnd.uniform(0, 1 / max(dens, 1e-6))):
                if rnd.random() <= keep and abs(x) < 148 * s:
                    cells.append((x + rnd.uniform(-0.6, 0.6) * s, y + rnd.uniform(-0.8, 0.8) * s))
    for outer, mid, lumen, c, w0, w1 in tent_shapes:
        for (x, y), (nx_, ny_) in _along(c[:-3], 1 / max(dens, 1e-6) * 0.8, 4 * s):
            for sg in (1, -1):
                if rnd.random() <= keep:
                    cells.append((x + nx_ * sg * w0 * 0.2, y + ny_ * sg * w0 * 0.2))
    expelled = []
    if bleached:
        expelled = [(rnd.uniform(-30, 30) * s, rnd.uniform(150, 200) * s) for _ in range(4)] + [
            (-4 * s, 70 * s),
            (7 * s, 52 * s),
            (-6 * s, 34 * s),
        ]
    zcol = symbiont_color
    allz = cells + expelled
    if allz:
        holder.append(
            _el(
                "path",
                d=" ".join(_circ(x, y, zr) for x, y in allz),
                fill=zcol,
                stroke=_mix(zcol, "#3B2408", 0.45),
                stroke_width=max(0.3, 0.45 * s),
            )
        )
        holder.append(
            _el(
                "path",
                d=" ".join(_circ(x + zr * 0.2, y - zr * 0.15, zr * 0.36) for x, y in allz),
                fill=_mix(zcol, "#6E7B3A", 0.5),
                stroke="none",
            )
        )
    if rich:
        look = _look()
        # aragonite fibre bundles: fans radiating up from centres of calcification
        fib = []
        for row in range(3):
            for col in range(-8, 9):
                cx, cy = (col * 19 + (row % 2) * 9.5) * s, (296 - row * 22) * s
                for k in range(7):
                    a = -math.pi / 2 + (k - 3) * 0.19
                    x1, y1 = cx + math.cos(a) * 16 * s, cy + math.sin(a) * 16 * s
                    if _inside((cx, cy - 0.5 * s), sk_poly) and _inside((x1, y1), sk_poly):
                        fib.append(f"M{fmt(cx)} {fmt(cy)} L{fmt(x1)} {fmt(y1)}")
        look.append(
            _el(
                "path",
                d=" ".join(fib),
                fill="none",
                stroke=_mix(skeleton, "#9C8A64", 0.5),
                stroke_width=0.45 * s,
                stroke_opacity=0.7,
            )
        )
        defs.append(_linear("cvg", [("0", "#FFFFFF", 0.55), ("1", "#FFFFFF", 0)]))
        look.append(_el("path", d=_d(cav_poly), fill="url(#cvg)"))
        hl = [
            _d(
                _offset(c, [w * 0.22 for w in [(w0 + (w1 - w0) * i / (len(c) - 1)) / 2 for i in range(len(c))]])[2:-2],
                False,
            )
            for _, _, _, c, w0, w1 in tent_shapes
        ]
        look.append(
            _el(
                "path",
                d=" ".join(hl),
                fill="none",
                stroke="#FFFFFF",
                stroke_width=1.2 * s,
                stroke_opacity=0.45,
                stroke_linecap="round",
            )
        )
        holder.append(look)
    pts_all = list(sk_poly) + [p for o, *_ in tent_shapes for p in o] + _band(oral, -T / 2, T / 2) + expelled
    xs, ys = [p[0] for p in pts_all], [p[1] for p in pts_all]
    ports.update(
        mouth=(0, oral[-1][1] - 30 * s if False else 92 * s),
        oral_disc=oral[len(oral) * 3 // 4],
        ectoderm=_offset(oral, T * 0.3)[len(oral) // 2],
        mesoglea=mo[len(mo) // 2],
        gastrodermis=_offset(oral, -T * 0.2)[len(oral) // 2],
        coelenteron=(0, 200 * s),
        calicoblastic=_offset(aboral, -T * 0.35)[len(aboral) * 2 // 3],
        skeleton=(0, 285 * s),
    )
    ports["mouth"] = (0, (oral[-4][1] + oral[-1][1]) / 2 - 18 * s)
    for k, p in enumerate(cells):
        ports[f"symbiont{k}"] = p
    for k, p in enumerate(expelled):
        ports[f"expelled{k}"] = p
    pad = max(zr, 1.0)
    return _finish(
        holder,
        defs,
        Box(min(xs) - pad, min(ys) - pad, max(xs) - min(xs) + 2 * pad, max(ys) - min(ys) + 2 * pad),
        **ports,
    )


@_drawing_api(
    "parts",
    purpose="水体剖面（湖泊/海洋/河流，期刊风格）：空气-水面（细波纹与入射光）、随深度变暗的水柱（可分表水层/温跃层/深水层）、悬浮颗粒、"
    "分层沉积物（含孔隙水与颗粒纹理）、可选沉水植物；用来放生物、污染物、通量箭头。",
    returns="Geometry（原点在中心；端口 surface/surface_left/surface_right、water/water_top/water_bottom、thermocline、bed/bed_left/bed_right/bed_center、"
    "sediment/porewater/deep_sediment、plant{k}；方法 point(x, depth) 由 water_point 提供）",
    semantics=(
        "width/height 为整体尺寸；sediment 为沉积层占高度比例（默认 .22），air 为水面上方空气带比例（默认 .1，0 不画）。",
        'thermocline=True（或 0–1 的深度比例）画温跃层虚线并在左侧写 "表水层 / 温跃层 / 深水层"（labels=None 不写；可传 3 个名字）；kind="lake"|"sea"|"river" 只改配色。',
        "particles=N 在水柱中撒 N 个悬浮颗粒（越深越密）；plants=N 在床面画 N 株沉水植物（带叶片的茎）；layers 为沉积层数，表层为氧化层（浅褐），下层渐深并有孔隙水小点。",
        '在剖面里放东西：water_point(width, height, x, depth, ...) 返回局部坐标（x、depth 为 0–1 比例，depth 0=水面 1=床面），或直接用端口；style="rich" 加深度渐变与光线（一个局部 SVG），"flat" 全原生。',
    ),
    example='lake = d.place(water_column_section(560, 320, thermocline=True, particles=30, plants=3), at=(480, 280), key="lake")\n'
    'd.arrow(lake.port("water_top"), lake.port("bed_center"))',
    rank=21,
)
def water_column_section(
    width=520,
    height=300,
    *,
    kind="lake",
    air=0.1,
    sediment=0.22,
    thermocline=False,
    labels=("表水层", "温跃层", "深水层"),
    particles=0,
    plants=0,
    layers=3,
    font_size=12,
    water=None,
    sed_color=None,
    style="rich",
    seed=4,
):
    rich = _style(style)
    _finite(width, height)
    if kind not in ("lake", "sea", "river"):
        raise ValueError('kind must be "lake", "sea" or "river"')
    rnd = random.Random(seed)
    W, H = float(width), float(height)
    water = water or {"lake": "#7FB6C9", "sea": "#4F8FC0", "river": "#8DB8A8"}[kind]
    sed_color = sed_color or "#B08A5E"
    y_s = H * air  # water surface
    y_b = H * (1 - sediment)  # mean bed level
    deep = _mix(water, "#0F2C45", 0.55)
    holder, defs = _el("g"), _el("defs")
    holder.append(defs)

    def surf_y(x):
        return y_s + 1.6 * math.sin(x / W * 2 * math.pi * 6) + 0.8 * math.sin(x / W * 2 * math.pi * 15 + 1)

    def bed_y(x):
        return (
            y_b
            + H * 0.018 * math.sin(x / W * 2 * math.pi * 1.3 + 0.7)
            + H * 0.008 * math.sin(x / W * 2 * math.pi * 4.1)
        )

    xs = [W * k / 120 for k in range(121)]
    surf = [(x, surf_y(x)) for x in xs]
    bed = [(x, bed_y(x)) for x in xs]
    holder.append(
        _el(
            "rect",
            x=0,
            y=0,
            width=W,
            height=H,
            fill="#F4F8FB" if air else water,
            stroke=_mix(water, "#000000", 0.45),
            stroke_width=1,
            data_outline="1",
        )
    )
    holder.append(_el("path", d=_d(surf + bed[::-1]), fill=water, stroke="none"))
    if rich:
        defs.append(_linear("wcol", [("0", _mix(water, "#FFFFFF", 0.35)), (".55", water), ("1", deep)]))
        look = _look()
        look.append(_el("path", d=_d(surf + bed[::-1]), fill="url(#wcol)"))
        # light shafts from the surface fading with depth
        defs.append(_linear("wray", [("0", "#FFFFFF", 0.45), ("1", "#FFFFFF", 0)]))
        for k in range(4):
            x0 = W * (0.12 + 0.22 * k) + rnd.uniform(-10, 10)
            look.append(
                _el(
                    "path",
                    d=_d(
                        [
                            (x0, surf_y(x0)),
                            (x0 + W * 0.05, surf_y(x0)),
                            (x0 + W * 0.11, y_s + (y_b - y_s) * 0.65),
                            (x0 + W * 0.07, y_s + (y_b - y_s) * 0.65),
                        ]
                    ),
                    fill="url(#wray)",
                )
            )
        holder.append(look)
    holder.append(_el("path", d=_d(surf, False), fill="none", stroke=_mix(water, "#0F2C45", 0.4), stroke_width=1.4))
    rip = []
    for k in range(9):
        x0 = W * (0.05 + 0.105 * k) + rnd.uniform(-6, 6)
        y0 = surf_y(x0) + 5 + rnd.uniform(0, 4)
        L = W * rnd.uniform(0.025, 0.045)
        rip.append(f"M{fmt(x0)} {fmt(y0)} q{fmt(L / 2)} -2.2 {fmt(L)} 0")
    holder.append(
        _el(
            "path",
            d=" ".join(rip),
            fill="none",
            stroke="#FFFFFF",
            stroke_width=1.1,
            stroke_opacity=0.85,
            stroke_linecap="round",
        )
    )
    if air:  # incoming light: sun rays at the top-right
        sx, sy = W * 0.93, y_s * 0.45
        holder.append(_el("circle", cx=sx, cy=sy, r=y_s * 0.22, fill="#F6C445", stroke="#D9A21F", stroke_width=0.8))
        holder.append(
            _el(
                "path",
                d=" ".join(
                    f"M{fmt(sx + y_s * 0.3 * math.cos(a))} {fmt(sy + y_s * 0.3 * math.sin(a))} "
                    f"l{fmt(y_s * 0.14 * math.cos(a))} {fmt(y_s * 0.14 * math.sin(a))}"
                    for a in (math.pi * k / 4 for k in range(8))
                ),
                stroke="#D9A21F",
                stroke_width=1,
                stroke_linecap="round",
            )
        )
    # sediment: wavy-topped layers getting darker with depth, grain stipple and porewater dots
    seds, nlay = [], max(1, int(layers))
    tops = [bed] + [
        [(x, y + (H - y) * (k / nlay) + H * 0.006 * math.sin(x / W * 2 * math.pi * (2 + k) + k)) for x, y in bed]
        for k in range(1, nlay)
    ]
    for k in range(nlay):
        tone = (
            _mix(_mix(sed_color, "#E2C79A", 0.45), "#3B2A1A", 0.2 * k)
            if k == 0
            else _mix(sed_color, "#3B2A1A", 0.18 * k)
        )
        holder.append(
            _el(
                "path",
                d=_d(tops[k] + [(W, H), (0, H)]),
                fill=tone,
                stroke=_mix(tone, "#000000", 0.3),
                stroke_width=0.7 if k else 1.2,
            )
        )
        seds.append(tone)
    grains, pores = [], []
    for _ in range(int(W * (H - y_b) / 90)):
        x = rnd.uniform(3, W - 3)
        y = rnd.uniform(bed_y(x) + 3, H - 3)
        r = rnd.uniform(0.8, 2.2)
        (pores if rnd.random() < 0.25 else grains).append((x, y, r))
    holder.append(
        _el(
            "path",
            d=" ".join(_circ(*g) for g in grains),
            fill=_mix(sed_color, "#2A1E12", 0.45),
            fill_opacity=0.6,
            stroke="none",
        )
    )
    holder.append(
        _el(
            "path",
            d=" ".join(_circ(x, y, r * 0.8) for x, y, r in pores),
            fill=_mix(water, "#FFFFFF", 0.2),
            stroke="none",
        )
    )
    # plants: rooted submerged macrophytes with alternating lanceolate leaves
    ports = {}
    for k in range(int(plants)):
        x0 = W * (0.08 + 0.84 * (k + 0.5) / max(plants, 1)) + rnd.uniform(-8, 8)
        top = y_s + (y_b - y_s) * rnd.uniform(0.18, 0.38)
        geo = _plant_shapes(x0, bed_y(x0) + 2, bed_y(x0) - top, rnd)
        holder.extend(geo[0])
        ports[f"plant{k}"] = geo[1]
    for _ in range(int(particles)):
        t = rnd.random() ** 0.6
        x = rnd.uniform(6, W - 6)
        y = y_s + 8 + (bed_y(x) - y_s - 14) * t
        r = rnd.uniform(0.9, 2.2)
        a = rnd.uniform(0, math.pi)
        holder.append(
            _el(
                "path",
                d=_oval(x, y, r * 1.4, r, a),
                fill=_mix(sed_color, "#55452F", 0.3),
                fill_opacity=0.85,
                stroke="none",
            )
        )
    boxes = [Box(0, 0, W, H)]
    if thermocline:
        tz = thermocline if isinstance(thermocline, float) else 0.42
        ty = y_s + (y_b - y_s) * tz
        holder.append(
            _el(
                "path",
                d=f"M0 {fmt(ty)} H{fmt(W)}",
                stroke=_mix(water, "#0F2C45", 0.55),
                stroke_width=1.1,
                stroke_dasharray="6 4",
                fill="none",
            )
        )
        ports["thermocline"] = (W / 2, ty)
        if labels:
            fs = font_size
            for name, y in zip(labels, ((y_s + ty) / 2, ty - fs * 0.8, (ty + y_b) / 2)):
                t, b = _text(
                    8,
                    y + fs * 0.36,
                    name,
                    fs,
                    fill="#FFFFFF" if y > (y_s + y_b) / 2 else _INK,
                    anchor="start",
                    weight="normal",
                )
                holder.append(t)
                boxes.append(b)
    ports.update(
        surface=(W / 2, surf_y(W / 2)),
        surface_left=(W * 0.15, surf_y(W * 0.15)),
        surface_right=(W * 0.85, surf_y(W * 0.85)),
        water=(W / 2, (y_s + y_b) / 2),
        water_top=(W / 2, y_s + (y_b - y_s) * 0.15),
        water_bottom=(W / 2, y_s + (y_b - y_s) * 0.88),
        bed=(W / 2, bed_y(W / 2)),
        bed_center=(W / 2, bed_y(W / 2)),
        bed_left=(W * 0.15, bed_y(W * 0.15)),
        bed_right=(W * 0.85, bed_y(W * 0.85)),
        sediment=(W / 2, (bed_y(W / 2) + H) / 2),
        porewater=(W * 0.3, bed_y(W * 0.3) + (H - y_b) * 0.3),
        deep_sediment=(W / 2, H - (H - y_b) * 0.15),
    )
    if air:
        ports["air"] = (W / 2, y_s / 2)
    return _finish(holder, defs, _union(boxes), **ports)


def water_point(width, height, x, depth, *, air=0.1, sediment=0.22):
    """Local (Geometry) coordinates of relative position x (0–1, left→right) and depth (0 surface → 1 bed) in water_column_section."""
    W, H = float(width), float(height)
    y_s, y_b = H * air, H * (1 - sediment)
    return (W * x - W / 2, y_s + (y_b - y_s) * depth - H / 2)


def _plant_shapes(x0, y0, h, rnd, color="#4E8A3A"):
    """Submerged macrophyte (Potamogeton/Elodea-like): wavy stem, alternating lanceolate leaves, short roots."""
    stem = [(x0 + h * 0.05 * math.sin(t * 3.2 + rnd.uniform(0, 0.5)), y0 - h * t) for t in (k / 12 for k in range(13))]
    els = [
        _el(
            "path",
            d=_smooth(stem),
            fill="none",
            stroke=_mix(color, "#000000", 0.25),
            stroke_width=1.6,
            stroke_linecap="round",
        )
    ]
    leaves = []
    for k in range(2, 13, 2):
        x, y = stem[k]
        side = 1 if k % 4 == 0 else -1
        L = h * (0.2 - 0.008 * k)
        a = math.radians(-90 + side * 55 + rnd.uniform(-8, 8))
        tip = (x + L * math.cos(a), y + L * math.sin(a))
        nx_, ny_ = -math.sin(a) * L * 0.2, math.cos(a) * L * 0.2
        mid = ((x + tip[0]) / 2, (y + tip[1]) / 2)
        leaves.append(
            f"M{fmt(x)} {fmt(y)} Q{fmt(mid[0] + nx_)} {fmt(mid[1] + ny_)} {fmt(tip[0])} {fmt(tip[1])} "
            f"Q{fmt(mid[0] - nx_)} {fmt(mid[1] - ny_)} {fmt(x)} {fmt(y)} Z"
        )
    els.append(_el("path", d=" ".join(leaves), fill=color, stroke=_mix(color, "#000000", 0.3), stroke_width=0.6))
    roots = " ".join(
        f"M{fmt(x0)} {fmt(y0)} q{fmt(dx * 0.5)} {fmt(h * 0.04)} {fmt(dx)} {fmt(h * 0.08)}"
        for dx in (-h * 0.06, 0, h * 0.05)
    )
    els.append(_el("path", d=roots, fill="none", stroke="#6B5236", stroke_width=0.9, stroke_linecap="round"))
    return els, stem[8]


_SOIL_GRAIN = ("#E3D5B8", "#D6C29C", "#CDB58C", "#E8DCC6", "#D9B99A")  # quartz / feldspar / mica-like tints
_SOIL_WATER, _SOIL_AIR, _SOIL_OM, _SOIL_CLAY = "#A9D3EC", "#FFFFFF", "#6B4A2E", "#A9876A"
_SOIL_OXIC, _SOIL_ANOXIC = "#E9A23B", "#5A3E8C"


def _grain_outline(cx, cy, r, rnd, angular):
    """Mineral grain: angular (straight facets, sharp corners) or rounded (smooth) closed outline + its vertex list."""
    k = rnd.randint(6, 9) if angular else rnd.randint(8, 11)
    a0 = rnd.uniform(0, 2 * math.pi)
    stretch, tilt = rnd.uniform(0.72, 1.0), rnd.uniform(0, math.pi)
    pts = []
    for i in range(k):
        a = a0 + 2 * math.pi * (i + rnd.uniform(-0.28, 0.28)) / k
        rr = r * (rnd.uniform(0.78, 1.04) if angular else rnd.uniform(0.9, 1.03))
        x, y = rr * math.cos(a), rr * math.sin(a) * stretch
        pts.append((cx + x * math.cos(tilt) - y * math.sin(tilt), cy + x * math.sin(tilt) + y * math.cos(tilt)))
    return (_d(pts) if angular else _smooth(pts, closed=True)), pts


def _scaled(pts, cx, cy, k):
    return [(cx + (x - cx) * k, cy + (y - cy) * k) for x, y in pts]


@_drawing_api(
    "parts",
    purpose="土壤团聚体 / 沉积物孔隙介质剖面（教科书级）：大小不一的矿物颗粒（砂粒棱角/磨圆、粉粒、黏粒片层包膜）、有机质碎片、颗粒表面水膜、"
    "充气孔隙与充水孔隙，团聚体内部缺氧核心（外缘有氧 → 中心缺氧的径向 O₂ 梯度）、颗粒表面的微生物菌落，可选根毛伸入。",
    returns="Geometry（原点在中心；端口 oxic 有氧外缘、anoxic 缺氧核心、boundary 氧化/缺氧界面、pore 充气孔隙、water 充水孔隙、water_film 水膜、"
    'grain 砂粒、clay 黏粒、om 有机质、microbe_oxic/microbe_anoxic 两区菌落、root 根毛（root=True）、surface 沉积物表面（kind="sediment"）、四边/center）',
    semantics=(
        'kind="aggregate" 画近圆形团聚体（size 为直径），anoxic 为缺氧核心半径比例（0 不画缺氧核心）；kind="sediment" 画矩形沉积柱（size=(宽, 高)），'
        "上方一薄层上覆水，anoxic 为有氧层以下的缺氧深度比例起点（如 .3 = 表层 30% 有氧）。",
        "texture=(砂, 粉, 黏) 相对比例决定颗粒组成；microbes 为菌落数（0 不画，菌体按所在区域着色：有氧橙、缺氧紫）；om 为有机质碎片数。",
        'root=True 在团聚体左上方画一段根与伸入孔隙的根毛；legend=True 在下方画颗粒/有机质/水/空气/菌体图例与 O₂ 色标（labels 可改 ("有氧", "缺氧")）。',
        "相近部件：生物膜内的 O₂/营养梯度用 biofilm_section，湖/海/河水柱与表层沉积物用 water_column_section。",
        '过程名由调用方用 d.callout 指向端口标注；style="rich" 加径向 O₂ 着色与颗粒明暗（局部 SVG），"flat" 全原生。',
    ),
    example='agg = d.place(soil_aggregate(380), at=(330, 260), key="agg")\n'
    'd.callout("ox", "外缘有氧", agg.port("oxic"), at=(600, 90), font_size=13)\n'
    'd.callout("an", "核心缺氧", agg.port("anoxic"), at=(600, 300), font_size=13)',
    rank=22,
)
def soil_aggregate(
    size=380,
    *,
    kind="aggregate",
    anoxic=0.45,
    texture=(0.4, 0.4, 0.2),
    microbes=6,
    om=3,
    root=False,
    legend=True,
    labels=("有氧", "缺氧"),
    font_size=12,
    style="rich",
    seed=7,
):
    rich = _style(style)
    if kind not in ("aggregate", "sediment"):
        raise ValueError('kind must be "aggregate" or "sediment"')
    W, H = (float(size), float(size)) if isinstance(size, (int, float)) else (float(size[0]), float(size[1]))
    _finite(W, H, anoxic, font_size, *texture)
    if not 0 <= anoxic < 1:
        raise ValueError("anoxic must be within 0–1")
    tot = sum(texture) or 1.0
    f_sand, f_silt, f_clay = (v / tot for v in texture)
    rnd = random.Random(seed)
    fs = float(font_size)
    agg = kind == "aggregate"
    S = min(W, H)
    film = max(1.8, S * 0.008)
    holder, defs = _el("g"), _el("defs")
    holder.append(defs)
    if agg:
        R = S / 2
        ph = [rnd.uniform(0, 2 * math.pi) for _ in range(3)]
        rb = lambda a: (
            R
            * (
                0.93
                + 0.04 * math.sin(3 * a + ph[0])
                + 0.025 * math.sin(5 * a + ph[1])
                + 0.015 * math.sin(9 * a + ph[2])
            )
        )
        outline = [(rb(a) * math.cos(a), rb(a) * math.sin(a)) for a in (2 * math.pi * k / 96 for k in range(96))]
        polar = lambda x, y: (math.hypot(x, y), math.atan2(y, x))
        inside = lambda x, y, m=0.0: polar(x, y)[0] < rb(polar(x, y)[1]) - m
        depth = lambda x, y: 1 - polar(x, y)[0] / rb(polar(x, y)[1])
        y_top = -R
        holder.append(_el("path", d=_smooth(outline, closed=True), fill=_SOIL_AIR, stroke="none", data_outline="1"))
    else:
        wb = H * 0.1  # overlying water band
        x0, y_top = -W / 2, -H / 2 + wb
        inside = lambda x, y, m=0.0: x0 + m < x < -x0 - m and y_top + m < y < H / 2 - m
        depth = lambda x, y: (y - y_top) / (H / 2 - y_top)
        holder.append(
            _el(
                "rect",
                x=x0,
                y=-H / 2,
                width=W,
                height=H,
                fill=_SOIL_WATER,
                stroke=_mix(_SOIL_GRAIN[2], "#000000", 0.35),
                stroke_width=1.1,
                data_outline="1",
            )
        )
        holder.append(
            _el("rect", x=x0, y=y_top, width=W, height=H / 2 - y_top, fill=_mix(_SOIL_WATER, "#FFFFFF", 0.45))
        )  # saturated pores
    core = (1 - anoxic) if agg else anoxic  # depth at which the anoxic zone starts
    has_core = anoxic > 0
    grains = []

    def place(n, r_lo, r_hi, angular_p, tries=60):
        for _ in range(n):
            for _ in range(tries):
                r = rnd.uniform(r_lo, r_hi)
                if agg:
                    a, q = rnd.uniform(0, 2 * math.pi), math.sqrt(rnd.random())
                    x, y = q * R * math.cos(a), q * R * math.sin(a)
                else:
                    x, y = rnd.uniform(x0, -x0), rnd.uniform(y_top, H / 2)
                if not inside(x, y, r * 0.85 + film):
                    continue
                if any(math.hypot(x - gx, y - gy) < r + gr + film * 0.7 for gx, gy, gr, *_ in grains):
                    continue
                d_, pts = _grain_outline(x, y, r, rnd, rnd.random() < angular_p)
                grains.append((x, y, r, d_, pts, rnd.choice(_SOIL_GRAIN)))
                break

    area = math.pi * (S / 2) ** 2 if agg else W * (H / 2 - y_top)
    rs, rz = S * 0.07, S * 0.03  # nominal sand / silt radius
    place(int(area * 0.5 * f_sand / (math.pi * rs * rs)) + 1, rs * 0.75, rs * 1.25, 0.55, tries=120)
    place(int(area * 0.45 * f_silt / (math.pi * rz * rz)) + 1, rz * 0.7, rz * 1.3, 0.7, tries=120)
    sand = [g for g in grains if g[2] >= rs * 0.8]
    return _soil_render(
        holder,
        defs,
        rich,
        grains,
        sand,
        inside,
        depth,
        core,
        has_core,
        agg,
        W,
        H,
        S,
        film,
        f_clay,
        microbes,
        om,
        root,
        legend,
        labels,
        fs,
        rnd,
        y_top,
        outline if agg else None,
    )


def _soil_render(
    holder,
    defs,
    rich,
    grains,
    sand,
    inside,
    depth,
    core,
    has_core,
    agg,
    W,
    H,
    S,
    film,
    f_clay,
    microbes,
    om,
    root,
    legend,
    labels,
    fs,
    rnd,
    y_top,
    outline,
):
    ports, boxes, texts = {}, [], []
    zone = lambda x, y: has_core and depth(x, y) >= core
    sat = _mix(_SOIL_WATER, "#FFFFFF", 0.2)  # water-saturated pore space of the anoxic zone
    core_pts = [(x * (1 - core), y * (1 - core)) for x, y in outline] if agg and has_core else None
    yb = y_top + (H / 2 - y_top) * core if not agg and has_core else None
    if has_core:
        if agg:
            holder.append(_el("path", d=_smooth(core_pts, closed=True), fill=sat))
        else:
            holder.append(_el("rect", x=-W / 2, y=yb, width=W, height=H / 2 - yb, fill=sat))
    # O2: oxic rim → anoxic core as a soft tint over the pore space (rich), the boundary is always drawn
    if rich:
        look = _look()
        if agg:
            g = _el("radialGradient", id="soil_o2", cx="50%", cy="50%", r="50%")
            stops = (
                (
                    ("0", _SOIL_ANOXIC, 0.22),
                    (f"{1 - core:.2f}", _SOIL_ANOXIC, 0.06),
                    (f"{min(0.97, 1 - core + 0.18):.2f}", _SOIL_OXIC, 0.0),
                    ("1", _SOIL_OXIC, 0.16),
                )
                if has_core
                else (("0", _SOIL_OXIC, 0.0), ("1", _SOIL_OXIC, 0.14))
            )
            for off, col, op in stops:
                g.append(_el("stop", offset=off, stop_color=col, stop_opacity=op))
            defs.append(g)
            look.append(_el("path", d=_smooth(outline, closed=True), fill="url(#soil_o2)"))
        else:
            stops = (
                [
                    ("0", _SOIL_OXIC, ".16"),
                    (f"{core:.2f}", _SOIL_OXIC, ".0"),
                    (f"{min(1, core + 0.1):.2f}", _SOIL_ANOXIC, ".06"),
                    ("1", _SOIL_ANOXIC, ".22"),
                ]
                if has_core
                else [("0", _SOIL_OXIC, ".16"), ("1", _SOIL_OXIC, ".0")]
            )
            defs.append(_linear("soil_o2", stops))
            look.append(_el("rect", x=-W / 2, y=y_top, width=W, height=H / 2 - y_top, fill="url(#soil_o2)"))
        holder.append(look)
    # water films around every grain + capillary necks where grains nearly touch
    wet = [_smooth(_scaled(pts, gx, gy, 1 + film * 1.7 / gr), closed=True) for gx, gy, gr, _, pts, _ in grains]
    necks = []
    for i, a in enumerate(grains):
        for b in grains[i + 1 :]:
            gap = math.hypot(a[0] - b[0], a[1] - b[1]) - a[2] - b[2]
            if gap < film * 5:
                k = a[2] / (a[2] + b[2])  # neck sits where the two surfaces face each other
                necks.append((a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k, film * 2.4 + max(gap, 0) * 0.55))
    holder.append(_el("path", d=" ".join(wet + [_circ(x, y, r) for x, y, r in necks]), fill=_SOIL_WATER, stroke="none"))
    # clay: coatings (cutans) on part of the sand surfaces + a few stacked-platelet domains in narrow pores
    coats = []
    for gx, gy, gr, _, pts, _ in sand:
        if rnd.random() < 0.3 + f_clay:
            k0 = rnd.randrange(len(pts))
            seg = [pts[(k0 + q) % len(pts)] for q in range(max(3, len(pts) // 2))]
            coats.append(_smooth(_scaled(seg, gx, gy, 1 + film * 0.6 / gr)))
    if coats:
        holder.append(
            _el(
                "path",
                d=" ".join(coats),
                fill="none",
                stroke=_SOIL_CLAY,
                stroke_width=film * 1.4,
                stroke_linecap="round",
            )
        )
    by = {}
    for gx, gy, gr, d_, pts, col in grains:
        by.setdefault(col, []).append(d_)
    for col, ds in by.items():
        holder.append(
            _el(
                "path",
                d=" ".join(ds),
                fill=col,
                stroke=_mix(col, "#000000", 0.42),
                stroke_width=0.9,
                stroke_linejoin="round",
            )
        )
    clear = lambda x, y: min([math.hypot(x - gx, y - gy) - gr for gx, gy, gr, *_ in grains] + [1e9])
    step = S / 40
    holes = []
    for i in range(-20, 21):
        for j in range(-20, 21):
            x, y = i * step * (W / S), j * step * (H / S)
            if inside(x, y, step * 0.8):
                holes.append((clear(x, y), x, y))
    holes.sort(reverse=True)
    pores = []  # well-separated pore centres, biggest first
    for c, x, y in holes:
        if c > film * 2.5 and all(math.hypot(x - px, y - py) > max(c, pc) * 1.6 for pc, px, py in pores):
            pores.append((c, x, y))
    narrow = [p for p in pores if p[0] < S * 0.03]
    plates = []
    n_dom = max(1, round(len(sand) * f_clay * 0.6)) if f_clay > 0.02 else 0
    for c, x, y in (narrow or pores)[::2][:n_dom]:
        a = rnd.uniform(0, math.pi)
        ux, uy = math.cos(a), math.sin(a)
        L = min(c * 1.6, S * 0.04)
        for q in (-1, 0, 1):
            ox, oy = -uy * q * film * 1.15, ux * q * film * 1.15
            plates.append(_rod_d(x + ox, y + oy, L * (1 - 0.15 * abs(q)), film * 0.8, ux, uy))
        ports.setdefault("clay", (x, y))
    if plates:
        holder.append(
            _el("path", d=" ".join(plates), fill=_SOIL_CLAY, stroke=_mix(_SOIL_CLAY, "#000000", 0.3), stroke_width=0.5)
        )
    if rich:
        look = _look()
        defs.append(_el("radialGradient", id="soil_gr", cx="50%", cy="50%", r="55%", fx="35%", fy="30%"))
        for off, col, op in (("0", "#FFFFFF", 0.55), (".6", "#FFFFFF", 0), ("1", "#000000", 0.16)):
            defs[-1].append(_el("stop", offset=off, stop_color=col, stop_opacity=op))
        for gx, gy, gr, d_, pts, col in grains:
            look.append(_el("path", d=d_, fill="url(#soil_gr)"))
        cleav = []  # fracture traces on the larger grains
        for gx, gy, gr, d_, pts, col in sand[::2]:
            a = rnd.uniform(0, math.pi)
            cleav.append(
                f"M{fmt(gx - gr * 0.45 * math.cos(a))} {fmt(gy - gr * 0.45 * math.sin(a))} l{fmt(gr * 0.6 * math.cos(a))} {fmt(gr * 0.6 * math.sin(a))}"
            )
        look.append(_el("path", d=" ".join(cleav), fill="none", stroke="#8C7A5C", stroke_width=0.6, stroke_opacity=0.6))
        holder.append(look)
    # particulate organic matter: dark lens-shaped plant fragments with cell-wall texture, in the larger pores
    om_d, om_tex = [], []
    big_pores = [p for p in pores if p[0] > S * 0.03 and inside(p[1], p[2], S * 0.07)]
    for c, x, y in big_pores[1::2][: max(0, int(om))]:
        L, w = min(c * 2.2, S * 0.12), min(c * 0.8, S * 0.04)
        a = rnd.uniform(0, math.pi)
        ux, uy = math.cos(a), math.sin(a)
        pts = []
        for q in range(14):
            t = 2 * math.pi * q / 14
            px, py = L / 2 * math.cos(t), w / 2 * math.sin(t) * (1 + 0.25 * math.sin(3 * t + x))
            pts.append((x + px * ux - py * uy, y + px * uy + py * ux))
        om_d.append(_smooth(pts, closed=True))
        for q in range(-2, 3):
            cx_, cy_ = x + ux * q * L * 0.17, y + uy * q * L * 0.17
            om_tex.append(
                f"M{fmt(cx_ - uy * w * 0.3)} {fmt(cy_ + ux * w * 0.3)} L{fmt(cx_ + uy * w * 0.3)} {fmt(cy_ - ux * w * 0.3)}"
            )
        om_tex.append(
            f"M{fmt(x - ux * L * 0.36)} {fmt(y - uy * L * 0.36)} L{fmt(x + ux * L * 0.36)} {fmt(y + uy * L * 0.36)}"
        )
        ports.setdefault("om", (x, y))
    if om_d:
        holder.append(
            _el("path", d=" ".join(om_d), fill=_SOIL_OM, stroke=_mix(_SOIL_OM, "#000000", 0.35), stroke_width=0.8)
        )
        holder.append(
            _el("path", d=" ".join(om_tex), fill="none", stroke=_mix(_SOIL_OM, "#FFFFFF", 0.3), stroke_width=0.6)
        )
    # microbial colonies on grain surfaces inside the water film, coloured by zone
    br = max(1.6, S * 0.0065)
    mic = {True: [], False: []}
    n = max(0, int(microbes))
    ox_h = [g for g in sand if not zone(g[0], g[1])]
    an_h = [g for g in sand if zone(g[0], g[1])]
    n_an = min(len(an_h), n // 2) if has_core else 0
    spread = lambda pool, k: pool[:: max(1, len(pool) // max(1, k))][:k]
    for (gx, gy, gr, _, pts, _), deep in [(g, False) for g in spread(ox_h, n - n_an)] + [
        (g, True) for g in spread(an_h, n_an)
    ]:
        a0 = rnd.uniform(0, 2 * math.pi)
        for q in range(rnd.randint(4, 6)):
            a = a0 + q * (br * 2.8) / gr
            x, y = gx + (gr + film * 0.9) * math.cos(a), gy + (gr + film * 0.9) * math.sin(a)
            rod = rnd.random() < 0.7
            mic[deep].append(_capsule(x, y, br * 2.2 if rod else 0, br if rod else br * 1.15, a + math.pi / 2))
        ports.setdefault(
            "microbe_anoxic" if deep else "microbe_oxic",
            (gx + (gr + film) * math.cos(a0), gy + (gr + film) * math.sin(a0)),
        )
    for deep, ds in mic.items():
        if ds:
            col = _SOIL_ANOXIC if deep else _SOIL_OXIC
            holder.append(_el("path", d=" ".join(ds), fill=col, stroke=_mix(col, "#000000", 0.4), stroke_width=0.6))
    air = [p for p in pores if not zone(p[1], p[2])]
    if root and agg:
        _soil_root(holder, S, film, air, rnd, ports, boxes)
    if has_core:
        if agg:
            holder.append(_el("path", d=_dashes(core_pts, 6, 4), fill="none", stroke=_SOIL_ANOXIC, stroke_width=1.3))
            ports["boundary"] = core_pts[len(core_pts) * 7 // 8]
        else:
            holder.append(
                _el(
                    "path",
                    d=f"M{fmt(-W / 2)} {fmt(yb)} H{fmt(W / 2)}",
                    fill="none",
                    stroke=_SOIL_ANOXIC,
                    stroke_width=1.3,
                    stroke_dasharray="6 4",
                )
            )
            ports["boundary"] = (W * 0.3, yb)
    edge = _mix(_SOIL_GRAIN[2], "#000000", 0.45)
    if agg:
        holder.append(_el("path", d=_dashes(outline, 5, 3), fill="none", stroke=edge, stroke_width=1.2))
        boxes.append(Box(-S / 2, -S / 2, S, S))
    else:
        holder.append(
            _el("path", d=f"M{fmt(-W / 2)} {fmt(y_top)} H{fmt(W / 2)}", fill="none", stroke=edge, stroke_width=1.3)
        )
        boxes.append(Box(-W / 2, -H / 2, W, H))
        ports["surface"] = (0, y_top)
    sat_pores = [p for p in pores if zone(p[1], p[2])]
    ports["pore"] = (air[0][1], air[0][2]) if air else (pores[0][1], pores[0][2]) if pores else (0, y_top + S * 0.08)
    ports["water"] = (
        (sat_pores[0][1], sat_pores[0][2]) if sat_pores else (necks[0][0], necks[0][1]) if necks else ports["pore"]
    )
    big = max(sand or grains, key=lambda g: g[2] - abs(depth(g[0], g[1]) - (core if has_core else 0.5) * 0.5) * S)
    ports["grain"] = (big[0], big[1])
    ports["water_film"] = (
        big[0] + (big[2] + film * 0.8) * math.cos(-0.8),
        big[1] + (big[2] + film * 0.8) * math.sin(-0.8),
    )
    ports.setdefault("clay", ports["water"])
    ports.setdefault("om", ports["grain"])
    if agg:
        ports["anoxic"] = (0.0, 0.0)
        r_ox = S / 2 * 0.93 * (1 - core / 2 if has_core else 0.7)
        ports["oxic"] = (r_ox * math.cos(-0.75), r_ox * math.sin(-0.75))
    else:
        ports["oxic"] = (0.0, y_top + (H / 2 - y_top) * (core if has_core else 1) * 0.5)
        ports["anoxic"] = (0.0, (yb + H / 2) / 2 if has_core else H / 2 - S * 0.05)
    ports.setdefault("microbe_oxic", ports["oxic"])
    ports.setdefault("microbe_anoxic", ports["anoxic"])
    if legend:
        _soil_legend(holder, texts, boxes, has_core, labels, fs, br, microbes, air=agg)
    holder.extend(texts)
    return _finish(holder, defs, _union(boxes), **ports)


def _dashes(pts, on, off):
    """Closed polyline as explicit dash segments (dash arrays on curves would keep the shape as SVG)."""
    out, carry, drawing = [], 0.0, True
    for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
        L = math.hypot(x1 - x0, y1 - y0)
        t = 0.0
        while t < L:
            seg = min((on if drawing else off) - carry, L - t)
            if drawing:
                a, b = t / L, (t + seg) / L
                out.append(
                    f"M{fmt(x0 + (x1 - x0) * a)} {fmt(y0 + (y1 - y0) * a)} L{fmt(x0 + (x1 - x0) * b)} {fmt(y0 + (y1 - y0) * b)}"
                )
            t += seg
            carry += seg
            if carry >= (on if drawing else off) - 1e-9:
                carry, drawing = 0.0, not drawing
    return " ".join(out)


def _rod_d(cx, cy, L, w, ux, uy):
    """Thin rounded flake of length L, thickness w along (ux, uy) — a clay platelet."""
    return _capsule(cx, cy, max(0.0, L - w), w / 2, math.atan2(uy, ux))


def _soil_root(holder, S, film, air, rnd, ports, boxes):
    """Root running past the aggregate's upper-left rim; root hairs (epidermal outgrowths) curve into the nearest rim pores."""
    rc = "#C9A46A"
    spine = [
        (S * 0.52 * math.cos(a), S * 0.52 * math.sin(a)) for a in (math.radians(d) for d in (165, 195, 225, 255, 285))
    ]
    w = S * 0.075
    nrm = []
    for i, (x, y) in enumerate(spine):
        (ax, ay), (bx, by) = spine[max(0, i - 1)], spine[min(len(spine) - 1, i + 1)]
        L = math.hypot(bx - ax, by - ay) or 1
        nrm.append(((by - ay) / L, -(bx - ax) / L))  # points away from the aggregate (outward, up-left)
    half = lambda i: w / 2 * (1 - 0.25 * i / (len(spine) - 1))
    outer = [(x + nx * half(i), y + ny * half(i)) for i, ((x, y), (nx, ny)) in enumerate(zip(spine, nrm))]
    inner = [(x - nx * half(i), y - ny * half(i)) for i, ((x, y), (nx, ny)) in enumerate(zip(spine, nrm))]
    holder.append(
        _el(
            "path",
            d=_smooth(outer) + " L" + _smooth(inner[::-1])[1:] + " Z",
            fill=_mix(rc, "#FFFFFF", 0.4),
            stroke=_mix(rc, "#000000", 0.4),
            stroke_width=1,
        )
    )
    holder.append(
        _el(
            "path",
            d=_smooth(spine),
            fill="none",
            stroke=_mix(rc, "#000000", 0.15),
            stroke_width=w * 0.28,
            stroke_opacity=0.5,
        )
    )
    walls = []
    for k in range(1, 12):
        t = k / 12 * (len(spine) - 1)
        i = min(int(t), len(spine) - 2)
        f = t - i
        (x0, y0), (x1, y1) = outer[i], outer[i + 1]
        (u0, v0), (u1, v1) = inner[i], inner[i + 1]
        walls.append(
            f"M{fmt(x0 + (x1 - x0) * f)} {fmt(y0 + (y1 - y0) * f)} L{fmt(u0 + (u1 - u0) * f)} {fmt(v0 + (v1 - v0) * f)}"
        )
    holder.append(
        _el(
            "path",
            d=" ".join(walls),
            fill="none",
            stroke=_mix(rc, "#000000", 0.3),
            stroke_width=0.6,
            stroke_opacity=0.7,
        )
    )
    near = lambda p: min(math.hypot(p[1] - x, p[2] - y) for x, y in inner)
    targets = sorted((p for p in air if near(p) < S * 0.16), key=near)[:6]
    hairs = []
    for c, x, y in targets:
        bx, by = min(inner, key=lambda q: math.hypot(q[0] - x, q[1] - y))
        mx, my = (bx + x) / 2 + rnd.uniform(-1, 1) * S * 0.015, (by + y) / 2 + rnd.uniform(-1, 1) * S * 0.015
        hairs.append(f"M{fmt(bx)} {fmt(by)} Q{fmt(mx)} {fmt(my)} {fmt(x)} {fmt(y)}")
        ports.setdefault("root", (x, y))
    ports.setdefault("root", spine[1])
    if hairs:
        holder.append(
            _el(
                "path",
                d=" ".join(hairs),
                fill="none",
                stroke=_mix(rc, "#000000", 0.25),
                stroke_width=film * 0.7,
                stroke_linecap="round",
            )
        )
    xs = [p[0] for p in outer + inner]
    ys = [p[1] for p in outer + inner]
    boxes.append(Box(min(xs) - 1, min(ys) - 1, max(xs) - min(xs) + 2, max(ys) - min(ys) + 2))


def _soil_legend(holder, texts, boxes, has_core, labels, fs, br, microbes, *, air):
    """Swatch row under the section: grain, organic matter, water, air, microbes, and the O2 colour bar."""
    bb = _union(boxes)
    y = bb.y + bb.height + fs * 1.6
    s = fs * 0.95
    items = (
        [("grain", "矿物颗粒"), ("om", "有机质"), ("water", "水")]
        + ([("air", "空气")] if air else [])
        + ([("microbe", "微生物")] if microbes else [])
    )
    widths = [s + 5 + _label(t, font_size=fs * 0.9).bounds.width for _, t in items]
    bar_w = fs * 7 if has_core else 0
    bar_tw = (
        (_label(labels[0], font_size=fs * 0.85).bounds.width + _label(labels[1], font_size=fs * 0.85).bounds.width + 10)
        if has_core
        else 0
    )
    total = sum(widths) + fs * 1.2 * (len(items) - 1) + ((fs * 2 + bar_w + bar_tw) if has_core else 0)
    x = bb.x + bb.width / 2 - total / 2
    for (kind, t), w in zip(items, widths):
        cy = y - fs * 0.32
        if kind == "grain":
            holder.append(
                _el(
                    "path",
                    d=_d(
                        [
                            (x, cy + s * 0.3),
                            (x + s * 0.2, cy - s * 0.45),
                            (x + s * 0.85, cy - s * 0.4),
                            (x + s, cy + s * 0.2),
                            (x + s * 0.5, cy + s * 0.5),
                        ]
                    ),
                    fill=_SOIL_GRAIN[1],
                    stroke=_mix(_SOIL_GRAIN[1], "#000000", 0.42),
                    stroke_width=0.9,
                )
            )
        elif kind == "om":
            holder.append(_el("ellipse", cx=x + s / 2, cy=cy, rx=s / 2, ry=s * 0.25, fill=_SOIL_OM))
        elif kind == "water":
            holder.append(
                _el(
                    "rect",
                    x=x,
                    y=cy - s / 2,
                    width=s,
                    height=s,
                    rx=2,
                    fill=_SOIL_WATER,
                    stroke=_mix(_SOIL_WATER, "#000000", 0.3),
                    stroke_width=0.8,
                )
            )
        elif kind == "air":
            holder.append(
                _el(
                    "rect",
                    x=x,
                    y=cy - s / 2,
                    width=s,
                    height=s,
                    rx=2,
                    fill="#FFFFFF",
                    stroke="#8A94A3",
                    stroke_width=0.8,
                )
            )
        else:
            holder.append(
                _el(
                    "path",
                    d=_capsule(x + s * 0.3, cy, br * 2.2, br, 0) + " " + _capsule(x + s * 0.8, cy, 0, br * 1.15, 0),
                    fill=_SOIL_OXIC,
                    stroke=_mix(_SOIL_OXIC, "#000000", 0.4),
                    stroke_width=0.6,
                )
            )
        el, b = _text(x + s + 5, y, t, fs * 0.9, anchor="start", weight="normal")
        texts.append(el)
        boxes.append(b)
        x += w + fs * 1.2
    if has_core:
        x += fs * 0.8
        el, b = _text(x, y, labels[0], fs * 0.85, anchor="start", weight="normal")
        texts.append(el)
        boxes.append(b)
        bx = b.x + b.width + 5
        n = 8
        for k in range(n):
            holder.append(
                _el(
                    "rect",
                    x=bx + bar_w * k / n,
                    y=y - fs * 0.7,
                    width=bar_w / n + 0.3,
                    height=fs * 0.6,
                    fill=_mix(_SOIL_OXIC, _SOIL_ANOXIC, k / (n - 1)),
                )
            )
        holder.append(
            _el(
                "rect",
                x=bx,
                y=y - fs * 0.7,
                width=bar_w,
                height=fs * 0.6,
                fill="none",
                stroke="#5E6773",
                stroke_width=0.6,
            )
        )
        el, b = _text(bx + bar_w + 5, y, labels[1], fs * 0.85, anchor="start", weight="normal")
        texts.append(el)
        boxes.append(b)
        el, b = _text(bx + bar_w / 2, y - fs * 1.0, "O₂", fs * 0.8, fill="#5B6573", weight="normal")
        texts.append(el)
        boxes.append(b)


_ORGANISMS = ("fish", "daphnia", "copepod", "algae", "bivalve", "worm", "plant", "mouse", "human")
_ORG_COLORS = {
    "fish": "#8FA9BF",
    "daphnia": "#E9D9A6",
    "copepod": "#E7C9A0",
    "algae": "#C9A646",
    "bivalve": "#C8B49A",
    "worm": "#C9656A",
    "plant": "#4E8A3A",
    "mouse": "#F1EEEA",
    "human": "#E9D3C2",
}


def _sc(pts, k, dx=0.0, dy=0.0):
    return [(x * k + dx, y * k + dy) for x, y in pts]


def _org_fish(k, color, rich):
    ink = _mix(color, "#000000", 0.55)
    body = _cr(
        [
            (-0.5, 0),
            (-0.36, -0.13),
            (-0.1, -0.19),
            (0.18, -0.15),
            (0.36, -0.06),
            (0.42, 0),
            (0.36, 0.07),
            (0.18, 0.13),
            (-0.1, 0.15),
            (-0.36, 0.1),
            (-0.5, 0),
        ],
        6,
    )
    tail = [(-0.46, 0), (-0.62, -0.17), (-0.58, -0.04), (-0.6, 0), (-0.58, 0.04), (-0.62, 0.17)]
    dorsal = [(-0.18, -0.17), (-0.1, -0.3), (0.08, -0.17)]
    dorsal2 = [(-0.34, -0.11), (-0.3, -0.19), (-0.24, -0.14)]
    pelvic = [(-0.04, 0.14), (-0.1, 0.24), (0.04, 0.14)]
    anal = [(-0.26, 0.11), (-0.32, 0.19), (-0.18, 0.13)]
    pect = [(0.17, 0.04), (0.04, 0.12), (0.06, 0.06)]
    els = [
        _el(
            "path",
            d=_smooth(_sc(tail, k), closed=True),
            fill=_mix(color, "#000000", 0.12),
            stroke=ink,
            stroke_width=k * 0.008,
            stroke_linejoin="round",
        )
    ]
    els.append(
        _el(
            "path",
            d=" ".join(_smooth(_sc(f, k), closed=True) for f in (dorsal, dorsal2, pelvic, anal)),
            fill=_mix(color, "#000000", 0.12),
            stroke=ink,
            stroke_width=k * 0.007,
            stroke_linejoin="round",
        )
    )
    els.append(_el("path", d=_smooth(_sc(body, k), closed=True), fill=color, stroke=ink, stroke_width=k * 0.009))
    els.append(
        _el(
            "path",
            d=_smooth(
                _sc(
                    [
                        (-0.48, 0.01),
                        (-0.3, 0.1),
                        (-0.1, 0.14),
                        (0.18, 0.12),
                        (0.36, 0.06),
                        (0.2, 0.05),
                        (-0.1, 0.07),
                        (-0.3, 0.05),
                    ],
                    k,
                ),
                closed=True,
            ),
            fill=_mix(color, "#FFFFFF", 0.55),
            stroke="none",
        )
    )
    els.append(
        _el(
            "path",
            d=_smooth(_sc(pect, k), closed=True),
            fill=_mix(color, "#000000", 0.15),
            stroke=ink,
            stroke_width=k * 0.006,
        )
    )
    els.append(
        _el(
            "path",
            d=_smooth(_sc([(0.25, -0.12), (0.21, -0.02), (0.25, 0.1)], k)),
            fill="none",
            stroke=ink,
            stroke_width=k * 0.007,
        )
    )
    els.append(
        _el(
            "path",
            d=_smooth(_sc([(0.23, -0.05), (0, -0.06), (-0.25, -0.03), (-0.46, 0)], k)),
            fill="none",
            stroke=ink,
            stroke_width=k * 0.004,
            stroke_opacity=0.7,
        )
    )
    els.append(
        _el("circle", cx=0.32 * k, cy=-0.04 * k, r=0.028 * k, fill="#FFFFFF", stroke=ink, stroke_width=k * 0.005)
    )
    els.append(_el("circle", cx=0.325 * k, cy=-0.04 * k, r=0.016 * k, fill="#1E2329"))
    els.append(
        _el(
            "path",
            d=_smooth(_sc([(0.42, 0.005), (0.39, 0.03), (0.35, 0.03)], k)),
            fill="none",
            stroke=ink,
            stroke_width=k * 0.006,
        )
    )
    if rich:
        scales = []
        for i in range(7):
            for j in range(-2, 3):
                x, y = -0.3 + i * 0.065 + (j % 2) * 0.03, j * 0.045
                if abs(y) < 0.12 - abs(x + 0.05) * 0.12:
                    scales.append(
                        f"M{fmt((x - 0.018) * k)} {fmt((y - 0.02) * k)} q{fmt(0.03 * k)} {fmt(0.02 * k)} 0 {fmt(0.04 * k)}"
                    )
        return (
            els,
            [_el("path", d=" ".join(scales), fill="none", stroke=ink, stroke_width=k * 0.003, stroke_opacity=0.45)],
            dict(
                head=(0.42 * k, 0),
                tail=(-0.6 * k, 0),
                eye=(0.32 * k, -0.04 * k),
                gill=(0.21 * k, 0),
                dorsal=(-0.1 * k, -0.25 * k),
            ),
        )
    return (
        els,
        [],
        dict(
            head=(0.42 * k, 0),
            tail=(-0.6 * k, 0),
            eye=(0.32 * k, -0.04 * k),
            gill=(0.21 * k, 0),
            dorsal=(-0.1 * k, -0.25 * k),
        ),
    )


def _org_daphnia(k, color, rich):
    """Daphnia, lateral view facing left: bivalved carapace with tail spine, head with compound eye and rostrum."""
    ink = _mix(color, "#3B2A10", 0.65)
    carapace = _cr(
        [
            (-0.36, -0.14),
            (-0.24, -0.2),
            (-0.1, -0.19),
            (0.08, -0.22),
            (0.24, -0.17),
            (0.34, -0.04),
            (0.35, 0.1),
            (0.3, 0.2),
            (0.44, 0.33),
            (0.24, 0.25),
            (0.06, 0.23),
            (-0.1, 0.16),
            (-0.2, 0.08),
            (-0.27, 0.07),
            (-0.36, 0.14),
            (-0.41, 0.1),
            (-0.42, -0.02),
            (-0.36, -0.14),
        ],
        6,
    )
    els = [_el("path", d=_smooth(_sc(carapace, k), closed=True), fill=color, stroke=ink, stroke_width=k * 0.008)]
    els.append(
        _el(
            "path",
            d=_smooth(_sc([(-0.17, -0.19), (-0.2, -0.05), (-0.17, 0.1)], k)),
            fill="none",
            stroke=ink,
            stroke_width=k * 0.005,
        )
    )
    # swimming antenna: protopodite from behind the head, two rami fanning back with plumose setae
    base = [(-0.22, -0.12), (-0.12, -0.3)]
    els.append(
        _el("path", d=_d(_sc(base, k), False), stroke=ink, stroke_width=k * 0.022, stroke_linecap="round", fill="none")
    )
    rami, setae = [], []
    for ang in (-28, 8):
        pts = [(-0.12, -0.3)]
        for j in range(1, 4):
            a = math.radians(ang + 6 * j)
            pts.append((pts[-1][0] + 0.065 * math.cos(a), pts[-1][1] + 0.065 * math.sin(a)))
        rami.append(_d(_sc(pts, k), False))
        for q in pts[1:]:
            for d_ in (-1, 1):
                a = math.radians(ang + d_ * 35 + 10)
                setae.append(_d(_sc([q, (q[0] + 0.09 * math.cos(a), q[1] + 0.09 * math.sin(a))], k), False))
    els.append(_el("path", d=" ".join(rami), stroke=ink, stroke_width=k * 0.011, stroke_linecap="round", fill="none"))
    els.append(_el("path", d=" ".join(setae), stroke=ink, stroke_width=k * 0.0035, fill="none", stroke_linecap="round"))
    # gut (curved), heart, eggs in brood pouch
    gut = _smooth(_sc([(-0.3, -0.06), (-0.2, -0.08), (-0.05, -0.02), (0.12, 0.08), (0.27, 0.19)], k))
    els.append(_el("path", d=gut, fill="none", stroke="#6B8E3A", stroke_width=k * 0.026, stroke_linecap="round"))
    els.append(
        _el(
            "path",
            d=gut,
            fill="none",
            stroke=_mix("#6B8E3A", "#FFFFFF", 0.4),
            stroke_width=k * 0.009,
            stroke_linecap="round",
        )
    )
    eggs = [(0.08 + 0.07 * (i % 3), -0.11 + 0.045 * (i // 3) + 0.015 * (i % 2)) for i in range(5)]
    els.append(
        _el(
            "path",
            d=" ".join(_circ(x * k, y * k, 0.026 * k) for x, y in eggs),
            fill="#D99A3A",
            stroke=ink,
            stroke_width=k * 0.004,
        )
    )
    els.append(_el("path", d=_oval(-0.07 * k, -0.13 * k, 0.035 * k, 0.022 * k, 0.3), fill="#C7504B", stroke="none"))
    # thoracic legs (filter combs) inside the carapace gape
    els.append(
        _el(
            "path",
            d=" ".join(
                _d(_sc([(-0.1 + 0.05 * i, 0.1 - 0.01 * i), (-0.12 + 0.05 * i, 0.18 - 0.01 * i)], k), False)
                for i in range(5)
            ),
            stroke=ink,
            stroke_width=k * 0.005,
            fill="none",
            stroke_opacity=0.7,
        )
    )
    # compound eye, ocellus, antennules at the rostrum
    els.append(_el("circle", cx=-0.35 * k, cy=-0.08 * k, r=0.04 * k, fill="#1E2329"))
    els.append(_el("circle", cx=-0.362 * k, cy=-0.092 * k, r=0.011 * k, fill="#FFFFFF", fill_opacity=0.8))
    els.append(_el("circle", cx=-0.33 * k, cy=0.01 * k, r=0.01 * k, fill="#1E2329"))
    els.append(
        _el(
            "path", d=_d(_sc([(-0.34, 0.12), (-0.33, 0.17)], k), False), stroke=ink, stroke_width=k * 0.006, fill="none"
        )
    )
    looks = []
    if rich:  # reticulate carapace texture
        net = []
        for i in range(7):
            x = -0.1 + i * 0.055
            net.append(_smooth(_sc([(x, -0.18), (x + 0.03, 0), (x + 0.05, 0.2)], k)))
        looks.append(
            _el("path", d=" ".join(net), fill="none", stroke=ink, stroke_width=k * 0.0025, stroke_opacity=0.35)
        )
    return (
        els,
        looks,
        dict(
            head=(-0.42 * k, 0),
            eye=(-0.35 * k, -0.08 * k),
            antenna=(-0.12 * k, -0.3 * k),
            gut=(-0.05 * k, -0.02 * k),
            eggs=(0.15 * k, -0.09 * k),
            tail=(0.44 * k, 0.33 * k),
            carapace=(0.25 * k, 0.05 * k),
        ),
    )


def _org_copepod(k, color, rich):
    """Calanoid copepod, dorsal view: segmented prosome, narrow urosome, caudal rami with setae, long antennules, naupliar eye."""
    ink = _mix(color, "#3B2A10", 0.6)
    prosome = _cr(
        [
            (0, -0.34),
            (0.1, -0.3),
            (0.13, -0.12),
            (0.11, 0.06),
            (0.07, 0.14),
            (-0.07, 0.14),
            (-0.11, 0.06),
            (-0.13, -0.12),
            (-0.1, -0.3),
            (0, -0.34),
        ],
        6,
    )
    uro = [(-0.035, 0.13), (0.035, 0.13), (0.03, 0.3), (-0.03, 0.3)]
    els = [_el("path", d=_smooth(_sc(prosome, k), closed=True), fill=color, stroke=ink, stroke_width=k * 0.008)]
    els.append(
        _el(
            "path",
            d=_d(_sc(uro, k)),
            fill=_mix(color, "#000000", 0.08),
            stroke=ink,
            stroke_width=k * 0.007,
            stroke_linejoin="round",
        )
    )
    segs = " ".join(
        _smooth(_sc([(-0.125 + abs(y) * 0.02, y), (0, y + 0.015), (0.125 - abs(y) * 0.02, y)], k))
        for y in (-0.2, -0.1, -0.02, 0.05)
    )
    segs += " " + " ".join(_d(_sc([(-0.032, y), (0.032, y)], k), False) for y in (0.18, 0.23, 0.27))
    els.append(_el("path", d=segs, fill="none", stroke=ink, stroke_width=k * 0.005))
    ant = []
    for sg in (-1, 1):
        pts = _cr([(sg * 0.06, -0.3), (sg * 0.25, -0.32), (sg * 0.42, -0.24), (sg * 0.5, -0.08), (sg * 0.52, 0.06)], 6)
        ant.append(_d(_sc(pts, k), False))
        ant.extend(_d(_sc([p, (p[0] + sg * 0.03, p[1] + 0.02)], k), False) for p in pts[4::4])
    els.append(_el("path", d=" ".join(ant), fill="none", stroke=ink, stroke_width=k * 0.008, stroke_linecap="round"))
    furca = []
    for sg in (-1, 1):
        x0 = sg * 0.02
        furca.append(_d(_sc([(x0, 0.3), (sg * 0.04, 0.35)], k), False))
        for a in (-12, 0, 12):
            t = math.radians(90 + sg * 15 + a)
            furca.append(
                _d(_sc([(sg * 0.04, 0.35), (sg * 0.04 + 0.14 * math.cos(t), 0.35 + 0.14 * math.sin(t))], k), False)
            )
    els.append(_el("path", d=" ".join(furca), fill="none", stroke=ink, stroke_width=k * 0.005, stroke_linecap="round"))
    els.append(_el("path", d=_oval(0, -0.29 * k, 0.02 * k, 0.015 * k, 0), fill="#C7504B", stroke="none"))
    els.append(
        _el(
            "path",
            d=_smooth(_sc([(0, -0.24), (0.01, -0.08), (0, 0.1)], k)),
            fill="none",
            stroke="#8A6A3A",
            stroke_width=k * 0.02,
            stroke_linecap="round",
            stroke_opacity=0.6,
        )
    )
    looks = []
    if rich:
        looks.append(
            _el("path", d=_oval(-0.04 * k, -0.18 * k, 0.05 * k, 0.1 * k, 0), fill="#FFFFFF", fill_opacity=0.35)
        )
    return (
        els,
        looks,
        dict(
            head=(0, -0.34 * k),
            eye=(0, -0.29 * k),
            antennule=(0.52 * k, 0.06 * k),
            tail=(0, 0.45 * k),
            body=(0, -0.08 * k),
        ),
    )


def _org_algae(k, color, rich):
    """Chain of four centric diatom cells (girdle view): silica frustule valves, girdle bands, golden-brown chloroplasts."""
    ink = _mix(color, "#3B2A10", 0.55)
    els, looks = [], []
    cw, ch, gap = 0.2, 0.26, 0.035
    x0 = -(4 * cw + 3 * gap) / 2
    chl = []
    for i in range(4):
        x = x0 + i * (cw + gap)
        els.append(
            _el(
                "rect",
                x=x * k,
                y=-ch / 2 * k,
                width=cw * k,
                height=ch * k,
                rx=0.03 * k,
                fill=_mix(color, "#FFFFFF", 0.72),
                stroke=ink,
                stroke_width=k * 0.008,
            )
        )
        els.append(
            _el(
                "path",
                d=f"M{fmt((x + 0.02) * k)} {fmt(-ch / 2 * k)} V{fmt(ch / 2 * k)} M{fmt((x + cw - 0.02) * k)} {fmt(-ch / 2 * k)} V{fmt(ch / 2 * k)}",
                stroke=ink,
                stroke_width=k * 0.004,
                fill="none",
            )
        )
        for j in range(3):
            cx, cy = x + cw * (0.32 + 0.36 * (j % 2)), (-0.07 + 0.07 * j)
            chl.append(_oval(cx * k, cy * k, 0.035 * k, 0.025 * k, 0.4 * j))
        if i < 3:
            els.append(
                _el(
                    "path",
                    d=" ".join(_d(_sc([(x + cw, y), (x + cw + gap, y)], k), False) for y in (-0.06, 0, 0.06)),
                    stroke=ink,
                    stroke_width=k * 0.005,
                    fill="none",
                )
            )
    els.append(_el("path", d=" ".join(chl), fill=color, stroke=_mix(color, "#000000", 0.3), stroke_width=k * 0.003))
    if rich:
        striae = " ".join(
            _d(_sc([(x0 + i * (cw + gap) + 0.025, y), (x0 + i * (cw + gap) + cw - 0.025, y)], k), False)
            for i in range(4)
            for y in (-ch / 2 + 0.012, ch / 2 - 0.012)
        )
        looks.append(
            _el(
                "path",
                d=striae,
                stroke=ink,
                stroke_width=k * 0.004,
                stroke_dasharray=f"{fmt(k * 0.006)} {fmt(k * 0.006)}",
                fill="none",
            )
        )
    return (
        els,
        looks,
        dict(
            cell0=((x0 + cw / 2) * k, 0),
            cell3=((x0 + 3 * (cw + gap) + cw / 2) * k, 0),
            chloroplast=((x0 + cw * 0.32) * k, -0.07 * k),
            head=(x0 * k, 0),
            tail=(-x0 * k, 0),
        ),
    )


def _org_bivalve(k, color, rich):
    """Clam (lateral view): inequilateral shell, umbo, hinge ligament, concentric growth lines, siphons."""
    ink = _mix(color, "#2B1E10", 0.6)
    shell = _cr(
        [
            (-0.06, -0.25),
            (-0.2, -0.17),
            (-0.34, -0.04),
            (-0.36, 0.07),
            (-0.26, 0.17),
            (0, 0.22),
            (0.24, 0.18),
            (0.38, 0.05),
            (0.36, -0.06),
            (0.22, -0.16),
            (0.06, -0.23),
            (-0.06, -0.25),
        ],
        6,
    )
    umbo = (-0.06, -0.25)
    sip = _cr([(0.32, -0.08), (0.47, -0.17), (0.53, -0.15), (0.37, 0.0)], 5)
    els = [_el("path", d=_smooth(_sc(sip, k), closed=True), fill="#E9C9B0", stroke=ink, stroke_width=k * 0.007)]
    els.append(_el("path", d=_smooth(_sc(shell, k), closed=True), fill=color, stroke=ink, stroke_width=k * 0.009))
    margin = shell[13:-12]  # anterior → ventral → posterior margin
    rings = [
        _smooth(_sc([(umbo[0] + (x - umbo[0]) * t, umbo[1] + (y - umbo[1]) * t) for x, y in margin], k))
        for t in (0.86, 0.7, 0.54, 0.38, 0.22)
    ]
    els.append(_el("path", d=" ".join(rings), fill="none", stroke=ink, stroke_width=k * 0.005, stroke_opacity=0.8))
    els.append(
        _el(
            "path",
            d=_smooth(_sc([(-0.04, -0.245), (0.08, -0.225), (0.18, -0.18)], k)),
            fill="none",
            stroke="#5B3B1E",
            stroke_width=k * 0.014,
            stroke_linecap="round",
        )
    )
    els.append(
        _el(
            "path",
            d=_d(_sc([(0.5, -0.165), (0.53, -0.2)], k), False)
            + " "
            + _d(_sc([(0.52, -0.155), (0.56, -0.17)], k), False),
            stroke=ink,
            stroke_width=k * 0.005,
            fill="none",
        )
    )
    looks = []
    if rich:
        looks.append(
            _el(
                "path",
                d=_smooth(_sc([(-0.24, -0.08), (-0.12, -0.17), (0.02, -0.2)], k)),
                fill="none",
                stroke="#FFFFFF",
                stroke_width=k * 0.025,
                stroke_opacity=0.4,
                stroke_linecap="round",
            )
        )
    return (
        els,
        looks,
        dict(
            umbo=(umbo[0] * k, umbo[1] * k),
            siphon=(0.52 * k, -0.18 * k),
            shell=(0.1 * k, 0.05 * k),
            head=(-0.36 * k, 0.06 * k),
            tail=(0.52 * k, -0.18 * k),
        ),
    )


def _org_worm(k, color, rich):
    """Oligochaete (tubificid-like): sinuous segmented body tapering to both ends, clitellum, chaetae, prostomium."""
    ink = _mix(color, "#2B0F10", 0.55)
    spine = _cr([(-0.5, 0.05), (-0.3, -0.06), (-0.1, 0.04), (0.1, -0.06), (0.3, 0.03), (0.48, -0.04)], 10)
    n = len(spine)
    ws = [0.028 + 0.02 * math.sin(math.pi * i / (n - 1)) ** 0.6 for i in range(n)]
    outline = _offset(spine, ws) + _offset(spine, [-w for w in ws])[::-1]
    els = [_el("path", d=_smooth(_sc(outline, k), closed=True), fill=color, stroke=ink, stroke_width=k * 0.008)]
    a, b = int(n * 0.26), int(n * 0.36)
    clit = _offset(spine[a:b], [w * 1.12 for w in ws[a:b]]) + _offset(spine[a:b], [-w * 1.12 for w in ws[a:b]])[::-1]
    els.append(
        _el(
            "path",
            d=_smooth(_sc(clit, k), closed=True),
            fill=_mix(color, "#F0B8A0", 0.5),
            stroke=ink,
            stroke_width=k * 0.006,
        )
    )
    rings, chaet = [], []
    for i in range(3, n - 3, 3):
        (x, y), (nx, ny), w = spine[i], _normals(spine)[i], ws[i]
        rings.append(_d(_sc([(x + nx * w, y + ny * w), (x - nx * w, y - ny * w)], k), False))
        if i % 6 == 0:
            for sg in (1, -1):
                bx, by = x + sg * nx * w, y + sg * ny * w
                chaet.append(
                    _d(_sc([(bx, by), (bx + sg * nx * 0.025 - ny * 0.01, by + sg * ny * 0.025 + nx * 0.01)], k), False)
                )
    els.append(_el("path", d=" ".join(rings), stroke=ink, stroke_width=k * 0.004, stroke_opacity=0.7, fill="none"))
    els.append(_el("path", d=" ".join(chaet), stroke=ink, stroke_width=k * 0.004, fill="none"))
    looks = []
    if rich:
        hl = _offset(spine[2:-2], [w * 0.45 for w in ws[2:-2]])
        looks.append(
            _el(
                "path",
                d=_smooth(_sc(hl, k)),
                fill="none",
                stroke="#FFFFFF",
                stroke_width=k * 0.012,
                stroke_opacity=0.45,
                stroke_linecap="round",
            )
        )
    return (
        els,
        looks,
        dict(
            head=(spine[-1][0] * k, spine[-1][1] * k),
            tail=(spine[0][0] * k, spine[0][1] * k),
            clitellum=(spine[(a + b) // 2][0] * k, spine[(a + b) // 2][1] * k),
            body=(spine[n // 2][0] * k, spine[n // 2][1] * k),
        ),
    )


def _org_mouse(k, color, rich):
    """Laboratory mouse, lateral view facing right: rounded body, pointed snout, large ear, eye, whiskers, feet, long tail."""
    ink = "#5B5560"
    body = _cr(
        [
            (-0.3, 0.1),
            (-0.32, -0.02),
            (-0.22, -0.13),
            (-0.02, -0.17),
            (0.14, -0.13),
            (0.24, -0.1),
            (0.33, -0.05),
            (0.42, 0.01),
            (0.4, 0.04),
            (0.3, 0.06),
            (0.2, 0.1),
            (0.05, 0.13),
            (-0.15, 0.13),
            (-0.3, 0.1),
        ],
        6,
    )
    tail = _cr([(-0.3, 0.06), (-0.42, 0.1), (-0.52, 0.02), (-0.6, -0.06), (-0.66, -0.04)], 8)
    els = [
        _el(
            "path",
            d=_smooth(_sc(tail, k)),
            fill="none",
            stroke="#D9A8A8",
            stroke_width=k * 0.016,
            stroke_linecap="round",
        )
    ]
    feet = " ".join(
        _smooth(_sc(f, k))
        for f in ([(-0.18, 0.12), (-0.2, 0.17), (-0.13, 0.175)], [(0.16, 0.1), (0.15, 0.16), (0.2, 0.165)])
    )
    els.append(_el("path", d=feet, fill="none", stroke="#D9A8A8", stroke_width=k * 0.016, stroke_linecap="round"))
    els.append(_el("path", d=_smooth(_sc(body, k), closed=True), fill=color, stroke=ink, stroke_width=k * 0.008))
    ear = _cr([(0.17, -0.12), (0.12, -0.22), (0.18, -0.26), (0.24, -0.21), (0.23, -0.12)], 5)
    els.append(
        _el(
            "path",
            d=_smooth(_sc(ear, k), closed=True),
            fill=_mix(color, "#E9A9A9", 0.35),
            stroke=ink,
            stroke_width=k * 0.007,
        )
    )
    els.append(
        _el(
            "path",
            d=_smooth(_sc([(0.175, -0.14), (0.16, -0.21), (0.21, -0.2)], k)),
            fill="none",
            stroke="#D99A9A",
            stroke_width=k * 0.012,
        )
    )
    els.append(_el("circle", cx=0.3 * k, cy=-0.06 * k, r=0.017 * k, fill="#7A1F2B"))
    els.append(_el("circle", cx=0.42 * k, cy=0.012 * k, r=0.012 * k, fill="#D98A8A"))
    wh = " ".join(
        _smooth(_sc([(0.38, 0), (0.45 + 0.02 * j, -0.03 + 0.03 * j), (0.52, -0.06 + 0.05 * j)], k)) for j in range(3)
    )
    els.append(_el("path", d=wh, fill="none", stroke=ink, stroke_width=k * 0.003, stroke_opacity=0.8))
    els.append(
        _el(
            "path",
            d=_smooth(_sc([(-0.1, 0.12), (-0.04, 0.03), (0.06, 0.02)], k)),
            fill="none",
            stroke=ink,
            stroke_width=k * 0.004,
            stroke_opacity=0.5,
        )
    )
    looks = []
    if rich:
        looks.append(
            _el(
                "path",
                d=_smooth(_sc([(-0.22, -0.08), (-0.02, -0.13), (0.14, -0.1)], k)),
                fill="none",
                stroke="#FFFFFF",
                stroke_width=k * 0.03,
                stroke_opacity=0.55,
                stroke_linecap="round",
            )
        )
    return (
        els,
        looks,
        dict(
            head=(0.42 * k, 0),
            nose=(0.42 * k, 0.012 * k),
            ear=(0.18 * k, -0.22 * k),
            eye=(0.3 * k, -0.06 * k),
            body=(0, -0.02 * k),
            tail=(-0.66 * k, -0.04 * k),
            abdomen=(-0.02 * k, 0.1 * k),
        ),
    )


def _org_human(k, color, rich):
    """Anatomical outline, front view (neutral, arms slightly abducted) — the standard body-map figure."""
    ink = _mix(color, "#3B2A20", 0.6)
    half = [
        (0, -0.5),
        (0.055, -0.49),
        (0.075, -0.44),
        (0.065, -0.39),
        (0.035, -0.36),
        (0.04, -0.34),
        (0.12, -0.32),
        (0.15, -0.29),
        (0.17, -0.18),
        (0.2, -0.04),
        (0.215, 0.03),
        (0.195, 0.04),
        (0.16, -0.06),
        (0.13, -0.17),
        (0.12, -0.08),
        (0.13, 0.02),
        (0.11, 0.1),
        (0.1, 0.28),
        (0.085, 0.45),
        (0.095, 0.49),
        (0.04, 0.49),
        (0.035, 0.45),
        (0.025, 0.2),
        (0.01, 0.06),
        (0, 0.05),
    ]
    pts = half + _mirror(half[::-1])[1:]
    els = [_el("path", d=_smooth(_sc(pts, k), closed=True), fill=color, stroke=ink, stroke_width=k * 0.006)]
    els.append(
        _el(
            "path",
            d=_smooth(_sc([(-0.02, -0.31), (0, -0.3), (0.02, -0.31)], k))
            + " "
            + " ".join(_smooth(_sc([(sg * 0.1, -0.24), (sg * 0.06, -0.2), (sg * 0.02, -0.21)], k)) for sg in (-1, 1))
            + " "
            + _d(_sc([(0, -0.12), (0, -0.02)], k), False),
            fill="none",
            stroke=ink,
            stroke_width=k * 0.003,
            stroke_opacity=0.6,
        )
    )
    looks = []
    if rich:
        looks.append(
            _el(
                "path",
                d=_smooth(_sc([(-0.08, -0.28), (-0.11, -0.1), (-0.09, 0.04)], k)),
                fill="none",
                stroke="#FFFFFF",
                stroke_width=k * 0.02,
                stroke_opacity=0.35,
                stroke_linecap="round",
            )
        )
    return (
        els,
        looks,
        dict(
            head=(0, -0.44 * k),
            chest=(0.04 * k, -0.24 * k),
            heart=(0.03 * k, -0.22 * k),
            lungs=(-0.06 * k, -0.22 * k),
            abdomen=(0, -0.05 * k),
            liver=(-0.05 * k, -0.13 * k),
            gut=(0, -0.02 * k),
            hand=(0.2 * k, 0.03 * k),
            foot=(0.07 * k, 0.48 * k),
            brain=(0, -0.46 * k),
        ),
    )


def _org_plant(k, color, rich):
    els, top = _plant_shapes(0, 0.5 * k, k, random.Random(5), color)
    return (
        els,
        [],
        dict(top=(top[0], top[1]), root=(0, 0.5 * k), leaf=(0, -0.1 * k), head=(0, -0.5 * k), tail=(0, 0.5 * k)),
    )


@_drawing_api(
    "parts",
    purpose="生物剪影（教科书线描，非卡通）：鱼、水蚤（Daphnia）、桡足类、藻类（硅藻链）、双壳贝、寡毛类蠕虫、沉水植物、实验小鼠、人体轮廓，"
    "用于生态毒理、营养级、暴露途径、动物实验示意。",
    returns="Geometry（原点在中心；端口四边/center 与 head/tail，以及各物种的 eye/gill/gut/antenna/eggs/siphon/clitellum/ear/abdomen/heart/liver… 部位）",
    semantics=(
        'kind 取 "fish"/"daphnia"/"copepod"/"algae"/"bivalve"/"worm"/"plant"/"mouse"/"human"；size 为体长 px（人体为身高），color 为主色（默认按物种）。',
        "各物种画出鉴别特征：鱼（鳍、鳃盖、侧线、鳞）、水蚤（甲壳+尾刺、复眼、双肢游泳触角带刚毛、肠、育卵囊卵）、桡足类（分节前体、细尾、长第一触角、尾叉刚毛、无节幼体眼）、"
        "硅藻链（硅质壳、环带、色素体）、双壳贝（壳顶、韧带、生长纹、水管）、蠕虫（体节、环带、刚毛）、小鼠（耳、眼、须、长尾）、人体（正面解剖轮廓）。",
        'flip=True 水平镜像（改朝向）；暴露/摄食箭头指向 port("gut")/port("gill") 等部位；style="rich" 加纹理/高光（一个局部 SVG），"flat" 全原生。',
    ),
    example='f = d.place(organism("fish", 120), at=(200, 160), key="fish")\n'
    'dp = d.place(organism("daphnia", 70), at=(380, 160), key="daphnia")\nd.arrow(dp, f)',
    rank=22,
)
def organism(kind="fish", size=100, *, color=None, flip=False, style="rich"):
    rich = _style(style)
    if kind not in _ORGANISMS:
        raise ValueError(f"kind must be one of {_ORGANISMS}")
    _finite(size)
    color = color or _ORG_COLORS[kind]
    els, looks, ports = globals()[f"_org_{kind}"](float(size), color, rich)
    holder, defs = _el("g"), _el("defs")
    holder.append(defs)
    body = _el("g", transform="scale(-1 1)") if flip else holder
    if flip:
        holder.append(body)
    outline = next(e for e in els if e.get("fill") not in (None, "none"))
    outline.set("data-outline", "1")
    els.remove(outline)
    body.append(outline)  # outline first, then everything else in drawing order
    body.extend(els)
    if rich and looks:
        look = _look()
        look.extend(looks)
        body.append(look)
    xs, ys = [], []
    for e in [outline] + els:
        for x, y in _path_pts(e):
            xs.append(x)
            ys.append(y)
    pad = size * 0.012
    sgn = -1 if flip else 1
    box = Box(min(xs) - pad, min(ys) - pad, max(xs) - min(xs) + 2 * pad, max(ys) - min(ys) + 2 * pad)
    if flip:
        box = Box(-box.x - box.width, box.y, box.width, box.height)
    return _finish(holder, defs, box, **{n: (sgn * x, y) for n, (x, y) in ports.items()})


def _path_pts(e):
    tag = e.tag
    if tag == "circle":
        cx, cy, r = (float(e.get(a)) for a in ("cx", "cy", "r"))
        return [(cx - r, cy - r), (cx + r, cy + r)]
    if tag == "rect":
        x, y, w, h = (float(e.get(a)) for a in ("x", "y", "width", "height"))
        return [(x, y), (x + w, y + h)]
    nums = [float(v) for v in __import__("re").findall(r"-?\d*\.?\d+(?:e-?\d+)?", e.get("d", ""))]
    if "q" in e.get("d", "") or "l" in e.get("d", ""):
        return []  # relative segments: tiny decorations, skip
    return list(zip(nums[::2], nums[1::2]))


_STAR_KINDS = {  # (disk-centre colour, limb colour, granule tint) — photosphere tints by Teff
    "sun": ("#FFF3CF", "#E9902C", "#FFE6A8"),
    "k_dwarf": ("#FFE2B0", "#D9681F", "#FFCF8A"),
    "m_dwarf": ("#FFC08E", "#B23A17", "#FFA36E"),
}
_PLANET_KINDS = {  # (base, band light, band dark, atmosphere)
    "gas_giant": ("#D9B98E", "#EFDDBF", "#B98D63", "#8FC1EA"),
    "rocky": ("#B07A55", "#C99A72", "#7E5238", "#9CC3E8"),
    "ice": ("#8FCAD8", "#B9E0E8", "#6FA9BD", "#A9D6F0"),
}


def _limb_intensity(mu, u1=0.6, u2=0.0):
    """Quadratic limb-darkening law I(μ)/I(1) = 1 − u1(1−μ) − u2(1−μ)²."""
    return 1 - u1 * (1 - mu) - u2 * (1 - mu) ** 2


def _star_body(holder, defs, r, kind, *, limb_darkening, granulation, spots, rich, rnd, gid="st"):
    centre, limb, gran = _STAR_KINDS[kind]
    edge = _mix(limb, "#000000", 0.2)
    holder.append(
        _el(
            "circle",
            cx=0,
            cy=0,
            r=r,
            fill=_mix(centre, limb, 0.25) if limb_darkening else centre,
            stroke=edge,
            stroke_width=max(0.6, r * 0.006),
            data_outline="1",
        )
    )
    if limb_darkening:  # native concentric steps of I(μ): readable even when flat
        for k in range(1, 7):
            rr = r * (1 - k / 7.0) ** 0.5 if k else r
            mu = math.sqrt(max(0.0, 1 - (rr / r) ** 2))
            t = 1 - _limb_intensity(mu)
            holder.append(_el("circle", cx=0, cy=0, r=rr, fill=_mix(centre, limb, min(1, t * 1.25))))
    ports = {}
    if rich:
        g = _el("radialGradient", id=f"{gid}_ld", cx="50%", cy="50%", r="50%")
        for k in range(11):
            x = k / 10
            mu = math.sqrt(max(0.0, 1 - x * x))
            g.append(
                _el(
                    "stop",
                    offset=fmt(x),
                    stop_color=_mix(centre, limb, min(1, (1 - _limb_intensity(mu)) * 1.25)),
                    stop_opacity=1 if limb_darkening else 0,
                )
            )
        defs.append(g)
        look = _look()
        if limb_darkening:
            look.append(_el("circle", cx=0, cy=0, r=r * 0.997, fill=f"url(#{gid}_ld)"))
        if granulation:  # bright granules with dark intergranular lanes, fading to the limb
            cell = max(1.6, r * 0.028)
            lanes, grains = [], []
            n = int((r / cell) ** 2 * 1.6)
            for _ in range(n):
                rr = r * math.sqrt(rnd.random()) * 0.97
                a = rnd.uniform(0, 2 * math.pi)
                x, y = rr * math.cos(a), rr * math.sin(a)
                mu = math.sqrt(max(0.0, 1 - (rr / r) ** 2))
                s = cell * rnd.uniform(0.45, 0.7) * (0.35 + 0.65 * mu)
                pts = [
                    (
                        x + s * (1 + 0.3 * math.sin(3 * q + a)) * math.cos(q) * (mu**0.5 if abs(rr) > 1e-6 else 1),
                        y + s * (1 + 0.3 * math.cos(2 * q + a)) * math.sin(q),
                    )
                    for q in [2 * math.pi * j / 7 for j in range(7)]
                ]
                c, s_ = math.cos(a), math.sin(a)  # foreshorten radially toward the limb
                pts = [
                    (
                        x
                        + ((px - x) * c + (py - y) * s_) * (0.4 + 0.6 * mu) * c
                        - (-(px - x) * s_ + (py - y) * c) * s_,
                        y
                        + ((px - x) * c + (py - y) * s_) * (0.4 + 0.6 * mu) * s_
                        + (-(px - x) * s_ + (py - y) * c) * c,
                    )
                    for px, py in pts
                ]
                (grains if rnd.random() < 0.6 else lanes).append(_d(pts))
            look.append(_el("path", d=" ".join(grains), fill=gran, fill_opacity=0.22))
            look.append(_el("path", d=" ".join(lanes), fill=_mix(limb, "#000000", 0.1), fill_opacity=0.07))
        if limb_darkening:
            look.append(
                _el(
                    "circle",
                    cx=0,
                    cy=0,
                    r=r * 1.035,
                    fill="none",
                    stroke=_mix(centre, limb, 0.35),
                    stroke_opacity=0.25,
                    stroke_width=r * 0.05,
                )
            )
        holder.append(look)
    # starspots: dark umbra + penumbra, foreshortened toward the limb
    for k in range(int(spots)):
        rr = r * rnd.uniform(0.15, 0.65)
        a = rnd.uniform(-2.6, -0.4) if k % 2 == 0 else rnd.uniform(0.5, 2.6)
        x, y = rr * math.cos(a), rr * math.sin(a)
        mu = math.sqrt(max(0.0, 1 - (rr / r) ** 2))
        s = r * rnd.uniform(0.05, 0.09)
        ang = math.degrees(a)
        holder.append(
            _el(
                "ellipse",
                cx=x,
                cy=y,
                rx=s * max(mu, 0.25),
                ry=s,
                fill=_mix(limb, "#000000", 0.22),
                transform=f"rotate({fmt(ang)} {fmt(x)} {fmt(y)})",
            )
        )
        holder.append(
            _el(
                "ellipse",
                cx=x,
                cy=y,
                rx=s * 0.45 * max(mu, 0.25),
                ry=s * 0.45,
                fill=_mix(limb, "#000000", 0.62),
                transform=f"rotate({fmt(ang)} {fmt(x)} {fmt(y)})",
            )
        )
        ports[f"spot{k}"] = (x, y)
    return ports


@_drawing_api(
    "parts",
    purpose="恒星（期刊风格）：正视恒星盘面，按二次临边昏暗律由盘心向边缘变暗变红，细微米粒组织纹理，可加星斑（本影+半影、近边缘压扁）。",
    returns="Geometry（原点=星心；端口 center/四边、limb（右侧边缘）、spot{k} 星斑）",
    semantics=(
        'r 为半径；kind="sun"（G 型，黄白）、"k_dwarf"（橙）、"m_dwarf"（红矮星，偏红、临边昏暗更明显）。',
        "limb_darkening=True 由原生同心圆阶梯 + rich 径向渐变表现 I(μ)；granulation=True 在 rich 层画米粒组织（只在 rich）；spots=N 画 N 个星斑。",
        "凌星/凌日正视图把 planet 的暗盘放在星盘上即可；侧视的透射光谱几何用 transit_geometry()。",
        'style="rich" 渐变与米粒在一个局部 SVG；"flat" 全原生（同心圆阶梯仍保留临边昏暗）。',
    ),
    example='s = d.place(star(120, kind="k_dwarf", spots=3), at=(200, 200), key="star")\n'
    'd.callout("sp", "星斑", s.port("spot0"), at=(360, 60), font_size=13)',
    rank=25,
)
def star(r=120, *, kind="sun", limb_darkening=True, granulation=True, spots=0, style="rich", seed=5):
    rich = _style(style)
    _finite(r)
    if kind not in _STAR_KINDS:
        raise ValueError(f"kind must be one of {tuple(_STAR_KINDS)}")
    holder, defs = _el("g"), _el("defs")
    holder.append(defs)
    ports = _star_body(
        holder,
        defs,
        r,
        kind,
        limb_darkening=limb_darkening,
        granulation=granulation,
        spots=spots,
        rich=rich,
        rnd=random.Random(seed),
    )
    R = r * (1.06 if rich and limb_darkening else 1)
    return _finish(holder, defs, Box(-R, -R, 2 * R, 2 * R), limb=(r, 0), **ports)


def _disc_strip(r, y0, y1, n=14):
    """Closed polygon of the part of a disk of radius r (at the origin) between y0 < y1."""
    y0, y1 = max(y0, -r), min(y1, r)
    right = [(math.sqrt(max(r * r - y * y, 0)), y) for y in [y0 + (y1 - y0) * k / n for k in range(n + 1)]]
    return right + [(-x, y) for x, y in reversed(right)]


def _planet_body(
    holder, defs, r, kind, *, atmosphere, scale_height, bands, light, layers, atm_color, rich, rnd, gid="pl"
):
    base, lt, dk, atm = _PLANET_KINDS[kind]
    atm = atm_color or atm
    H = float(scale_height if scale_height is not None else r * 0.06)
    n_l = max(1, int(layers))
    thick = H * 1.4 * n_l if atmosphere else 0.0
    ports = {}
    if atmosphere:  # translucent annulus: one ring per layer, density falling off ~ e^(−z/H)
        holder.append(
            _el("circle", cx=0, cy=0, r=r + thick, fill=atm, fill_opacity=0.12, stroke="none", data_outline="1")
        )
        dz = thick / n_l
        for k in range(n_l):
            holder.append(
                _el(
                    "circle",
                    cx=0,
                    cy=0,
                    r=r + dz * (k + 0.5),
                    fill="none",
                    stroke=atm,
                    stroke_opacity=round(0.42 * math.exp(-1.2 * k / max(1.0, n_l / 2.2)), 3),
                    stroke_width=dz,
                )
            )
        for k in range(1, n_l):  # layer boundaries (native dashed circles)
            holder.append(
                _el(
                    "circle",
                    cx=0,
                    cy=0,
                    r=r + dz * k,
                    fill="none",
                    stroke=_mix(_mix(atm, "#000000", 0.25), "#FFFFFF", 0.35),
                    stroke_width=max(0.6, r * 0.006),
                )
            )
        ports["atmosphere"] = (0.0, -(r + thick / 2))
        ports["atmosphere_top"] = (0.0, -(r + thick))
    holder.append(
        _el(
            "circle",
            cx=0,
            cy=0,
            r=r,
            fill=base,
            stroke=_mix(base, "#000000", 0.35),
            stroke_width=max(0.6, r * 0.012),
            data_outline=None if atmosphere else "1",
        )
    )
    if bands and kind in ("gas_giant", "ice"):  # zones (light) and belts (dark), slightly uneven widths
        ys, y = [], -r
        while y < r:
            w = r * rnd.uniform(0.12, 0.22)
            ys.append((y, min(r, y + w)))
            y += w
        for k, (a, b) in enumerate(ys):
            if k % 2:
                col = dk if kind == "gas_giant" else _mix(dk, base, 0.45)
                holder.append(_el("path", d=_d(_disc_strip(r * 0.995, a, b)), fill=col, fill_opacity=0.85))
            elif k % 4 == 0:
                holder.append(_el("path", d=_d(_disc_strip(r * 0.995, a, b)), fill=lt, fill_opacity=0.8))
        if kind == "gas_giant":  # one oval storm in a southern belt
            sy = r * 0.38
            holder.append(
                _el(
                    "ellipse",
                    cx=r * 0.25,
                    cy=sy,
                    rx=r * 0.15,
                    ry=r * 0.08,
                    fill=_mix(dk, "#B5452B", 0.55),
                    stroke=_mix(dk, "#000000", 0.3),
                    stroke_width=max(0.4, r * 0.006),
                )
            )
    elif kind == "rocky":
        blobs = []
        for _ in range(5):
            cx, cy = rnd.uniform(-0.55, 0.55) * r, rnd.uniform(-0.55, 0.55) * r
            s = r * rnd.uniform(0.12, 0.22)
            blobs.append(
                _smooth(
                    [
                        (
                            cx + s * (1 + 0.35 * math.sin(3 * q + cx)) * math.cos(q),
                            cy + s * 0.8 * (1 + 0.3 * math.cos(2 * q)) * math.sin(q),
                        )
                        for q in [2 * math.pi * j / 9 for j in range(9)]
                    ],
                    closed=True,
                )
            )
        holder.append(_el("path", d=" ".join(blobs), fill=dk, fill_opacity=0.55))
    # terminator: the hemisphere facing away from `light` is the nightside
    la = math.radians(light)
    lx, ly = math.cos(la), math.sin(la)
    for off, op in ((0.0, 0.14 if rich else 0.55),):  # terminator: night cap (rich softens it with a gradient)
        a_s = math.acos(off)  # light frame (+x toward the star): night cap is x < off·r
        pts = [(r * math.cos(t), r * math.sin(t)) for t in [a_s + (2 * math.pi - 2 * a_s) * k / 24 for k in range(25)]]
        rot = [(x * lx - y * ly, x * ly + y * lx) for x, y in pts]
        holder.append(_el("path", d=_d(rot), fill="#0B1424", fill_opacity=op))
    ports.update(
        dayside=(lx * r * 0.5, ly * r * 0.5),
        nightside=(-lx * r * 0.5, -ly * r * 0.5),
        terminator=(-ly * r, lx * r),
        limb=(-ly * (r + thick / 2), lx * (r + thick / 2)),
    )
    if rich:
        g = _el(
            "linearGradient",
            id=f"{gid}_term",
            x1=fmt(0.5 + lx * 0.5),
            y1=fmt(0.5 + ly * 0.5),
            x2=fmt(0.5 - lx * 0.5),
            y2=fmt(0.5 - ly * 0.5),
        )
        for off, col, op in (
            ("0", "#FFFFFF", 0.3),
            (".38", "#FFFFFF", 0),
            (".46", "#0B1424", 0.12),
            (".6", "#0B1424", 0.38),
            ("1", "#0B1424", 0.5),
        ):
            g.append(_el("stop", offset=off, stop_color=col, stop_opacity=op))
        defs.append(g)
        sh = _el("radialGradient", id=f"{gid}_sph", cx="50%", cy="50%", r="50%")
        for off, col, op in (("0", "#000000", 0), (".75", "#000000", 0), ("1", "#000000", 0.3)):
            sh.append(_el("stop", offset=off, stop_color=col, stop_opacity=op))
        defs.append(sh)
        look = _look()
        look.append(_el("circle", cx=0, cy=0, r=r * 0.99, fill=f"url(#{gid}_term)"))
        look.append(_el("circle", cx=0, cy=0, r=r * 0.99, fill=f"url(#{gid}_sph)"))
        holder.append(look)
    return ports, r + thick


@_drawing_api(
    "parts",
    purpose="系外行星/行星（期刊风格）：气态巨行星带纹（带与区、风暴卵）、岩质行星地貌斑块、冰巨星淡带；按入射光方向画昼夜晨昏线，外加分层半透明大气环。",
    returns="Geometry（原点=行星中心；端口 center/四边、dayside/nightside/terminator、limb（晨昏线处大气中层）、atmosphere/atmosphere_top）",
    semantics=(
        'r 为固体/云顶半径；kind="gas_giant"|"rocky"|"ice"；bands=True 画带纹（gas_giant/ice）。',
        "atmosphere=True 画 layers 层半透明大气环，scale_height 为标高 px（示意需夸大，默认 0.09·r），环厚 ≈ 1.4·标高·层数，密度向外指数减弱。",
        "light 为恒星所在方向（度，0=右、180=左）：背光半球画成夜侧，晨昏线垂直于该方向。",
        '侧视透射光谱几何（光线掠过晨昏线大气）用 transit_geometry()；style="rich" 加球面明暗与昼侧大气亮边（一个局部 SVG），"flat" 全原生。',
    ),
    example='p = d.place(planet(60, kind="gas_giant", light=180), at=(300, 200), key="hj")\n'
    'd.callout("atm", "大气层", p.port("atmosphere_top"), at=(420, 60), font_size=13)',
    rank=26,
)
def planet(
    r=60,
    *,
    kind="gas_giant",
    atmosphere=True,
    scale_height=None,
    bands=True,
    light=180,
    layers=3,
    atm_color=None,
    style="rich",
    seed=8,
):
    rich = _style(style)
    _finite(r, light)
    if kind not in _PLANET_KINDS:
        raise ValueError(f"kind must be one of {tuple(_PLANET_KINDS)}")
    holder, defs = _el("g"), _el("defs")
    holder.append(defs)
    ports, R = _planet_body(
        holder,
        defs,
        r,
        kind,
        atmosphere=atmosphere,
        scale_height=scale_height,
        bands=bands,
        light=light,
        layers=layers,
        atm_color=atm_color,
        rich=rich,
        rnd=random.Random(seed),
    )
    return _finish(holder, defs, Box(-R, -R, 2 * R, 2 * R), **ports)


def _telescope(x, y, s, color):
    """Side view of a reflecting telescope pointing left (aperture at x, y): tube, primary, mount."""
    edge = _mix(color, "#000000", 0.45)
    tube = [(x, y - s * 0.42), (x + s * 1.5, y - s * 0.34), (x + s * 1.5, y + s * 0.34), (x, y + s * 0.42)]
    out = [
        _el("path", d=_d(tube), fill=color, stroke=edge, stroke_width=1),
        _el(
            "ellipse",
            cx=x,
            cy=y,
            rx=s * 0.12,
            ry=s * 0.42,
            fill=_mix(color, "#FFFFFF", 0.55),
            stroke=edge,
            stroke_width=1,
        ),
        _el(
            "path",
            d=_d([(x + s * 1.38, y - s * 0.3), (x + s * 1.3, y), (x + s * 1.38, y + s * 0.3)], False),
            fill="none",
            stroke="#E9C46A",
            stroke_width=max(1.2, s * 0.07),
        ),  # primary mirror
        _el(
            "path",
            d=_d(
                [
                    (x + s * 0.75, y + s * 0.38),
                    (x + s * 0.55, y + s * 1.0),
                    (x + s * 1.15, y + s * 1.0),
                    (x + s * 0.95, y + s * 0.36),
                ]
            ),
            fill=_mix(color, "#000000", 0.2),
            stroke=edge,
            stroke_width=0.8,
        ),
    ]
    return out, Box(x - s * 0.14, y - s * 0.44, s * 1.66, s * 1.46)


@_drawing_api(
    "parts",
    purpose="凌星透射光谱几何（期刊风格侧视图）：左侧恒星（临边昏暗）、其右为带分层大气环的行星（昼侧朝星、夜侧朝观测者），"
    "星光掠过晨昏线处的大气（被滤光变色）射向右侧望远镜，正对行星盘的光被挡住；另附单独框出的正视小图（行星暗盘叠在星盘上，标碰撞参数 b）。",
    returns="Geometry（原点在中心；端口 star/planet/atmosphere/limb（上缘掠射点）/limb_bottom/observer/inset/inset_planet/dayside/nightside/ray{k}）",
    semantics=(
        "侧视与正视绝不混画：主图是俯视轨道面的侧视（恒星→行星→观测者成一线），inset=True 时右上角另画一个带框与标题的观测者视角正视图。",
        "width/height 为整体尺寸；star_kind 同 star()，planet_kind 同 planet()；scale_height 为大气标高 px（示意夸大）；impact 为碰撞参数 b（0–1，单位 R★）。",
        "光线：掠射光（穿过上下晨昏线大气，变成 filtered 色）汇向望远镜，被挡光止于昼侧，未遮挡光从行星外侧经过；labels=True 写“恒星/行星/观测者”和正视图标题与“昼侧/夜侧”。",
        'style="rich" 加渐变/米粒/球面明暗（局部 SVG），"flat" 全原生。',
    ),
    example='t = d.place(transit_geometry(720, 320, impact=.4), at=(400, 200), key="tr")\n'
    'd.callout("lm", "透射光穿过晨昏线大气", t.port("limb"), at=(420, 30), font_size=13)',
    rank=27,
)
def transit_geometry(
    width=720,
    height=320,
    *,
    star_kind="sun",
    planet_kind="gas_giant",
    scale_height=None,
    impact=0.4,
    inset=True,
    labels=True,
    ray_color="#F2B33D",
    filtered="#C0392B",
    font_size=12,
    style="rich",
    seed=6,
):
    rich = _style(style)
    _finite(width, height, impact, font_size)
    if not 0 <= impact < 1:
        raise ValueError("impact must be within 0–1")
    W, Hh = float(width), float(height)
    fs = font_size
    holder, defs = _el("g"), _el("defs")
    holder.append(defs)
    rnd = random.Random(seed)
    cy = Hh * 0.56
    Rs = Hh * 0.4
    sx = Rs + 2
    rp = Hh * 0.09
    H = float(scale_height if scale_height is not None else rp * 0.13)
    px = sx + Rs + (W - sx - Rs) * 0.36
    boxes, ports = [Box(0, 0, W, Hh)], {}
    sg = _el("g", transform=f"translate({fmt(sx)} {fmt(cy)})")
    _star_body(sg, defs, Rs, star_kind, limb_darkening=True, granulation=True, spots=0, rich=rich, rnd=rnd, gid="tg_s")
    sg[0].attrib.pop("data-outline", None)
    holder.append(_el("rect", x=0, y=0, width=W, height=Hh, fill="#FFFFFF", fill_opacity=0, data_outline="1"))
    holder.append(sg)
    # orbit: dashed arc through the planet, centred on the star, with a direction arrow
    ro = px - sx
    oa = [(sx + ro * math.cos(t), cy + ro * math.sin(t)) for t in [math.radians(-14 + 28 * k / 30) for k in range(31)]]
    holder.append(_el("path", d=_d(oa, False), fill="none", stroke="#7D8794", stroke_width=1, stroke_dasharray="4 3"))
    t1 = math.radians(14)
    holder.append(_head(sx + ro * math.cos(t1) - 1, cy + ro * math.sin(t1), -math.sin(t1), math.cos(t1), 7, "#7D8794"))
    # planet, lit from the star side (left): dayside faces the star, nightside faces the observer
    pg = _el("g", transform=f"translate({fmt(px)} {fmt(cy)})")
    pp, Rp = _planet_body(
        pg,
        defs,
        rp,
        planet_kind,
        atmosphere=True,
        scale_height=H,
        bands=True,
        light=180,
        layers=3,
        atm_color=None,
        rich=rich,
        rnd=rnd,
        gid="tg_p",
    )
    pg[0].attrib.pop("data-outline", None)
    # telescope at the right, aperture on the optical axis
    ts = Hh * 0.13
    tx = W - ts * 1.7
    tel, tb = _telescope(tx, cy, ts, "#9AA6B4")
    boxes.append(tb)
    yg = rp + (Rp - rp) * 0.32  # grazing height through the terminator annulus
    ray_w = max(1.2, Hh * 0.006)
    rays = []

    def surf(y):
        return sx + math.sqrt(max(Rs * Rs - (y - cy) ** 2, 0))

    for s in (-1, 1):  # unocculted starlight, passes outside the planet
        y = cy + s * (Rp + rp * 1.25)
        rays.append(("direct", [(surf(y), y), (px + Rp * 2.2, y), (tx - 1, cy + s * ts * 0.3)]))
    for s in (-1, 1):  # transmitted through the limb (terminator) atmosphere
        y = cy + s * yg
        rays.append(("graze", [(surf(y), y), (px, y), (px + Rp * 2.2, y), (tx - 1, cy + s * ts * 0.12)]))
    for s in (-0.45, 0.45):  # blocked by the planetary disk (stops on the dayside)
        y = cy + s * rp
        rays.append(("block", [(surf(y), y), (px - math.sqrt(rp * rp - (y - cy) ** 2) - 1, y)]))
    for k, (kind, pts) in enumerate(rays):
        if kind == "graze":
            a, mid, b, end = pts
            holder.append(
                _el(
                    "path",
                    d=_d([a, (px - math.sqrt(max(Rp * Rp - (a[1] - cy) ** 2, 0)), a[1])], False),
                    fill="none",
                    stroke=ray_color,
                    stroke_width=ray_w,
                )
            )
            seg = [(px + math.sqrt(max(Rp * Rp - (a[1] - cy) ** 2, 0)), a[1]), b, end]
            pg.append(
                _el(
                    "path",
                    d=_d(
                        [
                            (-math.sqrt(max(Rp * Rp - (a[1] - cy) ** 2, 0)), a[1] - cy),
                            (math.sqrt(max(Rp * Rp - (a[1] - cy) ** 2, 0)), a[1] - cy),
                        ],
                        False,
                    ),
                    fill="none",
                    stroke=_mix(ray_color, filtered, 0.5),
                    stroke_width=ray_w,
                    stroke_dasharray="3 2",
                )
            )
            col = filtered
        else:
            seg, col = pts, (ray_color if kind == "direct" else _mix(ray_color, "#7A4B00", 0.25))
        u = (seg[-1][0] - seg[-2][0], seg[-1][1] - seg[-2][1])
        n_ = math.hypot(*u) or 1
        tip = seg[-1]
        body = seg[:-1] + [(tip[0] - u[0] / n_ * 6, tip[1] - u[1] / n_ * 6)]
        holder.append(
            _el(
                "path",
                d=_d(body, False),
                fill="none",
                stroke=col,
                stroke_width=ray_w,
                stroke_linejoin="round",
                stroke_opacity=0.85 if kind == "direct" else None,
            )
        )
        holder.append(_head(tip[0], tip[1], u[0] / n_, u[1] / n_, 7, col))
        ports[f"ray{k}"] = pts[1] if len(pts) > 2 else pts[-1]
    holder.append(pg)
    holder.extend(tel)
    ports.update(
        star=(sx, cy),
        planet=(px, cy),
        atmosphere=(px, cy - (rp + Rp) / 2),
        limb=(px, cy - yg),
        limb_bottom=(px, cy + yg),
        observer=(tx + ts * 0.75, cy),
        dayside=(px - rp * 0.5, cy),
        nightside=(px + rp * 0.5, cy),
    )
    if labels:
        for txt, x, y in (("恒星", sx, cy + Rs + fs * 1.4), ("观测者", tx + ts * 0.75, cy + ts * 1.0 + fs * 1.4)):
            t, b = _text(x, y, txt, fs, weight="bold")
            holder.append(t)
            boxes.append(b)
        t, b = _text(px, cy + Rp + rp * 1.25 + fs * 1.6, "行星", fs, weight="bold")
        holder.append(t)
        boxes.append(b)
        for txt, x, anchor in (("昼侧", px - Rp - 3, "end"), ("夜侧", px + Rp + 3, "start")):
            t, b = _text(x, cy - Rp - fs * 0.3, txt, fs * 0.85, weight="normal", anchor=anchor, fill="#4A5563")
            holder.append(t)
            boxes.append(b)
    if inset:  # observer's view, framed and titled
        iw = min(W * 0.3, Hh * 0.52)
        ix, iy = W - iw - 1, 1.0
        title_h = fs * 1.6 if labels else 0
        ih = iw * 0.72 + title_h
        holder.append(
            _el("rect", x=ix, y=iy, width=iw, height=ih, fill="#0E1726", stroke="#5E6773", stroke_width=1, rx=3)
        )
        ir = iw * 0.3
        icx, icy = ix + iw / 2, iy + title_h + (ih - title_h) / 2
        ig = _el("g", transform=f"translate({fmt(icx)} {fmt(icy)})")
        _star_body(
            ig, defs, ir, star_kind, limb_darkening=True, granulation=False, spots=0, rich=rich, rnd=rnd, gid="tg_i"
        )
        ig[0].attrib.pop("data-outline", None)
        holder.append(ig)
        b_y = icy + impact * ir
        holder.append(
            _el(
                "path",
                d=_d([(icx - ir * 1.35, b_y), (icx + ir * 1.35, b_y)], False),
                fill="none",
                stroke="#C9D3DF",
                stroke_width=0.9,
                stroke_dasharray="3 2",
            )
        )
        ipr = ir * rp / Rs * 1.15
        ipx = icx + ir * 0.25
        holder.append(_el("circle", cx=ipx, cy=b_y, r=ipr * 1.2, fill=_PLANET_KINDS[planet_kind][3], fill_opacity=0.35))
        holder.append(_el("circle", cx=ipx, cy=b_y, r=ipr, fill="#141414"))
        holder.append(_el("path", d=_d([(icx, icy), (icx, b_y)], False), fill="none", stroke="#FFFFFF", stroke_width=1))
        holder.append(_el("circle", cx=icx, cy=icy, r=1.6, fill="#FFFFFF"))
        t, b = _text(
            icx - fs * 0.25, (icy + b_y) / 2 + fs * 0.35, "b", fs * 0.9, fill="#FFFFFF", anchor="end", italic=True
        )
        holder.append(t)
        if labels:
            t, b = _text(icx, iy + fs * 1.15, "正视图（观测者视角）", fs * 0.9, fill="#FFFFFF", weight="bold")
            holder.append(t)
        boxes.append(Box(ix, iy, iw, ih))
        ports.update(inset=(icx, iy + ih), inset_planet=(ipx, b_y), inset_star=(icx, icy))
    return _finish(holder, defs, _union(boxes), **ports)
