"""Engineering / CS / physics parts drawn like textbook and paper figures."""

from __future__ import annotations

import math

from ..atomize_svg_to_slide._geometry import fmt
from ._bio_parts import _circ, _el, _look, _mix
from ._geometry import Box, Geometry, _finite, _union, label
from ._geometry import label as _label
from ._help import _drawing_api
from ._parts import _INK, _finish, _head, _linear, _start, _style, _with_edges


def _txt(x, y, content, fs, *, fill=_INK, anchor="middle", weight=None, rotate=None, italic=False):
    """Native text with baseline at y; returns (element, canvas box)."""
    t = _el(
        "text",
        x=x,
        y=y,
        font_size=fs,
        text_anchor=anchor,
        fill=fill,
        font_weight=weight,
        font_style="italic" if italic else None,
        transform=f"rotate({fmt(rotate)} {fmt(x)} {fmt(y)})" if rotate else None,
    )
    t.text = str(content)
    b = label(str(content), font_size=fs, text_anchor=anchor, font_weight=weight or "normal").bounds
    box = Box(x + b.x, y - fs + b.y, b.width, b.height)
    if rotate:
        a = math.radians(rotate)
        pts = [
            (box.x, box.y),
            (box.x + box.width, box.y),
            (box.x, box.y + box.height),
            (box.x + box.width, box.y + box.height),
        ]
        pts = [
            (x + (px - x) * math.cos(a) - (py - y) * math.sin(a), y + (px - x) * math.sin(a) + (py - y) * math.cos(a))
            for px, py in pts
        ]
        xs, ys = zip(*pts)
        box = Box(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))
    return t, box


def _centered_text(cx, cy, content, fs, **kw):
    return _txt(cx, cy + fs * 0.36, content, fs, **kw)


def _poly(pts, close=False):
    return "M" + " L".join(f"{fmt(x)} {fmt(y)}" for x, y in pts) + (" Z" if close else "")


def _radial_hi(gid, color, *, fx=0.35, fy=0.3):
    """White specular spot fading into transparent — overlays any native fill."""
    g = _el("radialGradient", id=gid, cx="50%", cy="50%", r="55%", fx=f"{fx:.0%}", fy=f"{fy:.0%}")
    g.append(_el("stop", offset=0, stop_color="#FFFFFF", stop_opacity=0.75))
    g.append(_el("stop", offset=0.55, stop_color="#FFFFFF", stop_opacity=0.12))
    g.append(_el("stop", offset=1, stop_color=_mix(color, "#000000", 0.35), stop_opacity=0.28))
    return g


@_drawing_api(
    "parts",
    purpose="神经网络层：竖排神经元（描边+高光），层底标签，可选浅色层底板。",
    returns="Geometry（端口 in_i/out_i 为第 i 个神经元左右侧，另有四边/center）",
    semantics=(
        "n 为神经元数；超过 max_drawn 时中间画竖排省略号，端口只给画出的神经元；连接两层用 dense_links。",
        "fill 为神经元色，描边按 fill 加深；panel=True 时画圆角层底板（rich 默认开）；name 写在层底。",
        'style="rich" 加球面高光（局部 SVG），"flat" 全部原生；r<7 时自动省略高光。',
    ),
    example='l1 = d.place(nn_layer(4, name="输入", fill="#4A6FA5"), at=(110, 200), key="in")\n'
    'l2 = d.place(nn_layer(6, name="隐藏", fill="#E08A3C"), at=(270, 200), key="h")\ndense_links(d, l1, l2)',
    rank=8,
)
def nn_layer(
    n,
    *,
    r=12,
    gap=14,
    fill="#4A6FA5",
    stroke=None,
    name=None,
    font_size=13,
    max_drawn=7,
    style="rich",
    panel=None,
    label_fill="#33404F",
):
    _finite(r, gap)
    rich = _style(style)
    panel = rich if panel is None else panel
    shown = list(range(n)) if n <= max_drawn else list(range(max_drawn - 2)) + [None, n - 1]
    edge = stroke if stroke not in (None, "none") else _mix(fill, "#000000", 0.35)
    holder, defs = _start(rich)
    h = len(shown) * 2 * r + (len(shown) - 1) * gap
    pad = r * 0.55
    boxes = [Box(0, 0, 2 * r, h)]
    if panel:
        holder.append(
            _el(
                "rect",
                x=-pad,
                y=-pad,
                width=2 * r + 2 * pad,
                height=h + 2 * pad,
                rx=r + pad,
                fill=_mix(fill, "#FFFFFF", 0.9),
                stroke=_mix(fill, "#FFFFFF", 0.6),
                stroke_width=1,
                data_outline="1",
            )
        )
        boxes.append(Box(-pad - 0.5, -pad - 0.5, 2 * r + 2 * pad + 1, h + 2 * pad + 1))
    ports, centers, y = {}, [], 0.0
    sw = max(0.8, min(1.6, r * 0.11))
    for idx in shown:
        if idx is None:
            for k in (-1, 0, 1):
                holder.append(_el("circle", cx=r, cy=y + r + k * r * 0.55, r=max(1.4, r * 0.14), fill=edge))
        else:
            holder.append(
                _el(
                    "circle",
                    cx=r,
                    cy=y + r,
                    r=r,
                    fill=fill,
                    stroke=edge,
                    stroke_width=sw,
                    data_outline=None if panel or centers else "1",
                )
            )
            centers.append(y + r)
            ports[f"in_{idx}"], ports[f"out_{idx}"] = (0, y + r), (2 * r, y + r)
        y += 2 * r + gap
    if rich and r >= 7:
        defs.append(_radial_hi("hi", fill))
        look = _look()
        for cy in centers:
            look.append(_el("circle", cx=r, cy=cy, r=r - sw / 2, fill="url(#hi)"))
        holder.append(look)
    if name:
        t, b = _txt(r, h + (pad if panel else 0) + font_size * 1.35, name, font_size, fill=label_fill)
        holder.append(t)
        boxes.append(b)
    return _finish(holder, defs, _union(boxes), **ports)


@_drawing_api(
    "parts",
    purpose="两层神经网络全连接线（接 nn_layer 节点），可按权重变化粗细/透明度。",
    returns="None（向 drawing 加入连线）",
    semantics=(
        "a/b 为 nn_layer 的 Node；weights 为 [len(a 画出神经元)][len(b 画出神经元)] 的数值矩阵（-1..1），"
        "|w| 决定线宽与不透明度，负权重用 negative 色；省略 weights 时为等粗浅色细线。",
        "其余样式参数同 connect（stroke/stroke_width 为基准）。",
    ),
    example='dense_links(d, l1, l2, weights=[[0.9, -0.3, 0.1], [0.2, 0.7, -0.8]], stroke="#4A6FA5")',
    rank=9,
)
def dense_links(drawing, a, b, *, weights=None, negative="#C0392B", **style):
    style.setdefault("stroke", "#C2CAD6" if weights is None else "#4A6FA5")
    style.setdefault("stroke_width", 0.8 if weights is None else 1.2)
    num = lambda k: int(k.split("_")[1])
    outs = sorted((k for k in a.geometry.ports if k.startswith("out_")), key=num)
    ins = sorted((k for k in b.geometry.ports if k.startswith("in_")), key=num)
    base = style["stroke_width"]
    for i, o in enumerate(outs):
        for j, n in enumerate(ins):
            paint = dict(style)
            if weights is not None:
                w = float(weights[i][j])
                _finite(w)
                m = min(1.0, abs(w))
                paint["stroke_width"] = base * (0.35 + 1.65 * m)
                paint["stroke_opacity"] = round(0.18 + 0.77 * m, 3)
                if w < 0:
                    paint["stroke"] = negative
            drawing.connect(f"{a.key}-{b.key}-{i}-{j}", a.port(o), b.port(n), **paint)


def _tensor_px(c, h, w, unit, size):
    if size is not None:
        return tuple(float(v) for v in size)
    thick = max(5.0, min(90.0, 3.5 * math.log2(max(c, 1)) + 2))
    return thick, max(16.0, min(170.0, h * unit)), max(10.0, min(120.0, w * unit * 0.55))


def _slab_defs():
    return [
        _linear("front", [(0, "#FFFFFF", 0.28), (1, "#000000", 0.06)], x2=1, y2=1),
        _linear("topf", [(0, "#FFFFFF", 0.35), (1, "#FFFFFF", 0.05)], x2=1, y2=0),
        _linear("sidef", [(0, "#000000", 0.02), (1, "#000000", 0.2)], x2=0, y2=1),
    ]


def _slab(holder, look, x, y, t, H, D, fill, edge, *, grid):
    """3-D feature-map slab whose back-top corner box starts at (x, y): front t×H, oblique depth D."""
    top_c, side_c = _mix(fill, "#FFFFFF", 0.38), _mix(fill, "#000000", 0.22)
    ox, oy = D * 0.7071, D * 0.7071 * 0.8
    P = lambda pts: [(x + px, y + py) for px, py in pts]
    hexagon = P([(0, oy), (ox, 0), (t + ox, 0), (t + ox, H), (t, oy + H), (0, oy + H)])
    sw = 1.0 if min(t, H) > 12 else 0.7
    holder.append(
        _el(
            "path",
            d=_poly(hexagon, True),
            fill=side_c,
            stroke=edge,
            stroke_width=sw,
            stroke_linejoin="round",
            data_outline="1",
        )
    )
    top = P([(0, oy), (ox, 0), (t + ox, 0), (t, oy)])
    side = P([(t, oy), (t + ox, 0), (t + ox, H), (t, oy + H)])
    holder.append(
        _el("path", d=_poly(top, True), fill=top_c, stroke=edge, stroke_width=sw * 0.8, stroke_linejoin="round")
    )
    holder.append(
        _el("path", d=_poly(side, True), fill=side_c, stroke=edge, stroke_width=sw * 0.8, stroke_linejoin="round")
    )
    holder.append(_el("rect", x=x, y=y + oy, width=t, height=H, fill=fill, stroke=edge, stroke_width=sw * 0.8))
    if look is not None:
        look.append(_el("rect", x=x, y=y + oy, width=t, height=H, fill="url(#front)"))
        look.append(_el("path", d=_poly(top, True), fill="url(#topf)"))
        look.append(_el("path", d=_poly(side, True), fill="url(#sidef)"))
    if grid and H >= 24 and D >= 14:
        gc = _mix(edge, "#FFFFFF", 0.25)
        rows = max(2, min(8, int(H / 11)))
        cols = max(2, min(8, int(D / 11)))
        X = lambda v: fmt(x + v)
        Y = lambda v: fmt(y + v)
        lines = []
        for k in range(1, rows):  # horizontal cells on the side face (spatial grid H×W)
            yy = H * k / rows
            lines.append(f"M{X(t)} {Y(oy + yy)} L{X(t + ox)} {Y(yy)}")
        for k in range(1, cols):
            f = k / cols
            lines.append(f"M{X(t + ox * f)} {Y(oy * (1 - f))} L{X(t + ox * f)} {Y(oy * (1 - f) + H)}")
            lines.append(f"M{X(ox * f)} {Y(oy * (1 - f))} L{X(t + ox * f)} {Y(oy * (1 - f))}")
        if t >= 14:
            slabs = max(2, min(8, int(t / 7)))
            for k in range(1, slabs):
                xx = t * k / slabs
                lines.append(f"M{X(xx)} {Y(oy)} L{X(xx + ox)} {Y(0)}")
        g = _el("path", d=" ".join(lines), fill="none", stroke=gc, stroke_width=0.55, stroke_opacity=0.7)
        (look if look is not None else holder).append(g)
    return ox, oy, sw


@_drawing_api(
    "parts",
    purpose="3D 特征图立方体（CNN/Transformer 架构图常用）：正面/顶面/侧面三面明度不同，可选网格与 C×H×W 标注。",
    returns="Geometry（原点在中心；端口 left/right 为正面左边与侧面右边中点，front 为正面中心，top_face 为顶面中心）",
    semantics=(
        "c/h/w 为张量尺寸（只用于标注与比例）：厚度按 log2(c) 递增、高度 = h×unit、斜向深度 = w×unit×0.55；"
        "size=(厚, 高, 深) 直接指定像素尺寸，几层并排时传同一 unit 保持比例。",
        'fill 为正面色，顶面自动提亮、侧面压暗；grid=True 画特征网格（rich 默认开），label="auto" 时在下方写通道数、左侧写 h、斜边写 w；'
        "label=None 关闭，传字符串则只在下方写该文字。",
        'style="rich" 三面加渐变与网格（局部 SVG），"flat" 全部原生纯色。整套 U-Net/编码器–解码器直接用 encoder_decoder。',
    ),
    example='x = d.place(tensor_block(64, 56, 56, unit=1.6, fill="#F2B880"), at=(160, 260), key="conv1")\n'
    'y = d.place(tensor_block(128, 28, 28, unit=1.6, fill="#F2B880"), at=(300, 260), key="conv2")\nd.arrow(x.port("right"), y.port("left"))',
    rank=13,
)
def tensor_block(
    c,
    h,
    w,
    *,
    unit=1.0,
    size=None,
    fill="#7FA7D9",
    stroke=None,
    grid=None,
    label="auto",
    font_size=11,
    style="rich",
    label_fill="#33404F",
):
    _finite(c, h, w, unit)
    rich = _style(style)
    grid = rich if grid is None else grid
    t, H, D = _tensor_px(c, h, w, unit, size)
    edge = stroke or _mix(fill, "#000000", 0.45)
    holder, defs = _start(rich)
    if rich:
        defs.extend(_slab_defs())
    look = _look() if rich else None
    ox, oy, sw = _slab(holder, look, 0, 0, t, H, D, fill, edge, grid=grid)
    if rich:
        holder.append(look)
    boxes = [Box(-sw / 2, -sw / 2, t + ox + sw, oy + H + sw)]
    label_hw = _label(str(h), font_size=font_size).bounds.width if label == "auto" else 0
    if label:
        fs = font_size
        if label == "auto":
            for content, kw in ((c, dict(x=t / 2, y=oy + H + fs * 1.3)),):
                el, b = _txt(kw["x"], kw["y"], content, fs, fill=label_fill)
                holder.append(el)
                boxes.append(b)
            hw = _label(str(h), font_size=fs).bounds.width
            el, b = _txt(-fs * 0.3, oy + H - hw / 2 - 1, h, fs, fill=label_fill, rotate=-90)
            holder.append(el)
            boxes.append(b)
            ang = -math.degrees(math.atan2(oy, ox))
            mx, my = t + ox / 2 + fs * 0.55, oy / 2 + H + fs * 0.9
            el, b = _txt(mx, my, w, fs, fill=label_fill, rotate=ang)
            holder.append(el)
            boxes.append(b)
        else:
            el, b = _txt(t / 2, oy + H + fs * 1.3, label, fs, fill=label_fill)
            holder.append(el)
            boxes.append(b)
    free = H - (label_hw + 3 if label == "auto" else 0)
    ports = dict(
        left=(0, oy + (max(2.0, free / 2) if free > 4 else H / 2)),
        right=(t + ox, H / 2 + oy / 2),
        front=(t / 2, oy + H / 2),
        top_face=(t / 2 + ox / 2, oy / 2),
    )
    return _finish(holder, defs, _union(boxes), **ports)


def _rrect(x, y, w, h, r):
    r = max(0.0, min(r, w / 2, h / 2))
    if r <= 0:
        return f"M{fmt(x)} {fmt(y)} H{fmt(x + w)} V{fmt(y + h)} H{fmt(x)} Z"
    return (
        f"M{fmt(x + r)} {fmt(y)} H{fmt(x + w - r)} A{fmt(r)} {fmt(r)} 0 0 1 {fmt(x + w)} {fmt(y + r)} "
        f"V{fmt(y + h - r)} A{fmt(r)} {fmt(r)} 0 0 1 {fmt(x + w - r)} {fmt(y + h)} H{fmt(x + r)} "
        f"A{fmt(r)} {fmt(r)} 0 0 1 {fmt(x)} {fmt(y + h - r)} V{fmt(y + r)} A{fmt(r)} {fmt(r)} 0 0 1 {fmt(x + r)} {fmt(y)} Z"
    )


def _shadow(look, outline_d_at, w, h, color, *, depth=3.0):
    """Soft drop shadow drawn only *outside* the shape (evenodd ring), so it can sit above the native outline."""
    for k, op in ((1.0, 0.10), (0.6, 0.12), (0.3, 0.14)):
        look.append(
            _el(
                "path",
                d=outline_d_at(depth * k * 0.5, depth * k, 1.0 + k * 0.02) + " " + outline_d_at(0, 0, 1.0),
                fill=_mix(color, "#000000", 0.6),
                fill_opacity=op,
                fill_rule="evenodd",
            )
        )


def _text_lines(title, subtitle, font_size, text_fill):
    t = label(title, font_size=font_size, text_anchor="middle", font_weight="bold").bounds
    s = label(subtitle, font_size=font_size * 0.78, text_anchor="middle").bounds if subtitle else None
    return t, s


@_drawing_api(
    "parts",
    purpose="模块框：算法/系统流程的模块（圆角+阴影+小标题条+图标位）、数据（圆柱/文档）、运算节点（⊕ ⊗ σ 圆形）。",
    returns="Geometry（端口四边与 center）",
    semantics=(
        'kind="module" 圆角框（默认）；"data" 数据库圆柱；"doc" 文档形（下缘波浪）；"op" 圆形运算符，title 写 "+"/"⊕" 画加号、"×"/"⊗" 画乘号，其他文字（σ、Σ、concat）居中写。',
        "title 为主文字（粗体），subtitle 为下方小字；header_fill 非空时顶部画色条；icon 为 1–2 个字符的图标位（左侧圆形徽标，颜色取 header_fill 或 stroke）。",
        '尺寸按文字自适应，min_width/min_height 可对齐同列；style="rich" 加外阴影与顶部光泽（局部 SVG），"flat" 全部原生。',
    ),
    example='enc = d.place(block("Encoder", subtitle="6 × Transformer", header_fill="#4A6FA5", icon="E"), at=(120, 200), key="enc")\n'
    'db = d.place(block("特征库", kind="data", fill="#EAF1FA"), at=(320, 200), key="db")\n'
    'add = d.place(block("+", kind="op", fill="#FFF4D6", stroke="#B8860B"), at=(480, 200), key="add")',
    rank=10,
)
def block(
    title,
    *,
    subtitle=None,
    kind="module",
    fill="#FFFFFF",
    stroke="#4A6FA5",
    header_fill=None,
    icon=None,
    text_fill="#1E191C",
    font_size=15,
    min_width=120,
    min_height=0,
    rx=8,
    padding=12,
    style="rich",
    stroke_width=1.5,
):
    rich = _style(style)
    if kind not in ("module", "data", "doc", "op"):
        raise ValueError("block kind must be module/data/doc/op")
    holder, defs = _start(rich)
    look = _look() if rich else None
    sw = stroke_width
    if kind == "op":
        r = max(
            min_width / 2 if min_width < 60 else 0,
            font_size * 0.95,
            min_height / 2,
            label(title, font_size=font_size).bounds.width / 2 + 5 if title not in ("+", "⊕", "×", "⊗") else 0,
        )
        holder.append(_el("circle", cx=r, cy=r, r=r, fill=fill, stroke=stroke, stroke_width=sw, data_outline="1"))
        if rich:
            defs.append(_radial_hi("hi", fill))
            _shadow(
                look,
                lambda dx, dy, s: (
                    f"M{fmt(r + dx + r * s)} {fmt(r + dy)} A{fmt(r * s)} {fmt(r * s)} 0 1 0 {fmt(r + dx - r * s)} {fmt(r + dy)} "
                    f"A{fmt(r * s)} {fmt(r * s)} 0 1 0 {fmt(r + dx + r * s)} {fmt(r + dy)} Z"
                ),
                2 * r,
                2 * r,
                stroke,
                depth=2,
            )
            look.append(_el("circle", cx=r, cy=r, r=r - sw / 2, fill="url(#hi)", fill_opacity=0.8))
            holder.append(look)
        k = r * 0.55
        if title in ("+", "⊕"):
            holder.append(
                _el(
                    "path",
                    d=f"M{fmt(r - k)} {fmt(r)} H{fmt(r + k)} M{fmt(r)} {fmt(r - k)} V{fmt(r + k)}",
                    fill="none",
                    stroke=stroke,
                    stroke_width=sw * 1.2,
                    stroke_linecap="round",
                )
            )
        elif title in ("×", "⊗"):
            k *= 0.75
            holder.append(
                _el(
                    "path",
                    d=f"M{fmt(r - k)} {fmt(r - k)} L{fmt(r + k)} {fmt(r + k)} M{fmt(r + k)} {fmt(r - k)} L{fmt(r - k)} {fmt(r + k)}",
                    fill="none",
                    stroke=stroke,
                    stroke_width=sw * 1.2,
                    stroke_linecap="round",
                )
            )
        else:
            el, _ = _centered_text(r, r, title, font_size, fill=text_fill)
            holder.append(el)
        return _finish(holder, defs, Box(-sw / 2, -sw / 2, 2 * r + sw, 2 * r + sw))
    tb, sb = _text_lines(title, subtitle, font_size, text_fill)
    gap = font_size * 0.3
    text_h = tb.height + (gap + sb.height if sb else 0)
    text_w = max(tb.width, sb.width if sb else 0)
    icon_d = font_size * 1.7 if icon else 0
    bar = 6 if header_fill and kind == "module" else 0
    w = max(min_width, text_w + 2 * padding + (icon_d + padding * 0.7 if icon else 0))
    cap = 0.0
    if kind == "data":
        cap = max(6.0, min(w * 0.09, 14.0))
    wav = max(5.0, font_size * 0.45) if kind == "doc" else 0
    body_h = max(min_height, text_h + 2 * padding * 0.8, icon_d + padding)
    h = body_h + bar + 2 * cap + wav
    if kind == "module":
        outline = lambda dx, dy, s: _rrect(dx - (s - 1) * w / 2, dy - (s - 1) * h / 2, w * s, h * s, rx)
    elif kind == "data":

        def outline(dx, dy, s):
            ww, hh = w * s, h * s
            x0, y0 = dx - (s - 1) * w / 2, dy - (s - 1) * h / 2
            return (
                f"M{fmt(x0)} {fmt(y0 + cap)} A{fmt(ww / 2)} {fmt(cap)} 0 0 1 {fmt(x0 + ww)} {fmt(y0 + cap)} "
                f"V{fmt(y0 + hh - cap)} A{fmt(ww / 2)} {fmt(cap)} 0 0 1 {fmt(x0)} {fmt(y0 + hh - cap)} Z"
            )
    else:

        def outline(dx, dy, s):
            ww, hh = w * s, h * s
            x0, y0 = dx - (s - 1) * w / 2, dy - (s - 1) * h / 2
            yb = y0 + hh - wav
            return (
                f"M{fmt(x0)} {fmt(y0)} H{fmt(x0 + ww)} V{fmt(yb)} "
                f"C{fmt(x0 + ww * 0.75)} {fmt(yb - wav * 1.4)} {fmt(x0 + ww * 0.5)} {fmt(yb + wav * 1.6)} {fmt(x0 + ww * 0.25)} {fmt(yb + wav * 0.6)} "
                f"C{fmt(x0 + ww * 0.15)} {fmt(yb + wav * 0.1)} {fmt(x0 + ww * 0.06)} {fmt(yb - wav * 0.2)} {fmt(x0)} {fmt(yb + wav * 0.2)} Z"
            )

    holder.append(
        _el(
            "path",
            d=outline(0, 0, 1.0),
            fill=fill,
            stroke=stroke,
            stroke_width=sw,
            stroke_linejoin="round",
            data_outline="1",
        )
    )
    if rich:
        defs.append(
            _linear("gloss", [(0, "#FFFFFF", 0.55), (0.5, "#FFFFFF", 0.0), (1, _mix(fill, "#000000", 0.5), 0.06)])
        )
        _shadow(look, outline, w, h, stroke)
        look.append(_el("path", d=outline(0, 0, 1.0), fill="url(#gloss)"))
        holder.append(look)
    if kind == "data":  # visible front lip of the cylinder top
        holder.append(
            _el(
                "path",
                d=f"M{fmt(0)} {fmt(cap)} A{fmt(w / 2)} {fmt(cap)} 0 0 0 {fmt(w)} {fmt(cap)}",
                fill="none",
                stroke=stroke,
                stroke_width=sw,
            )
        )
        holder.append(
            _el(
                "path",
                d=f"M0 {fmt(cap * 2.4)} A{fmt(w / 2)} {fmt(cap)} 0 0 0 {fmt(w)} {fmt(cap * 2.4)}",
                fill="none",
                stroke=_mix(stroke, "#FFFFFF", 0.45),
                stroke_width=sw * 0.7,
            )
        )
    if kind == "doc":  # folded corner
        f = min(w, h) * 0.16
        holder.append(
            _el(
                "path",
                d=f"M{fmt(w - f)} 0 V{fmt(f)} H{fmt(w)} Z",
                fill=_mix(fill, stroke, 0.25),
                stroke=stroke,
                stroke_width=sw * 0.8,
                stroke_linejoin="round",
            )
        )
    if bar:
        holder.append(
            _el(
                "path",
                d=f"M{fmt(rx)} 0 H{fmt(w - rx)} A{fmt(rx)} {fmt(rx)} 0 0 1 {fmt(w)} {fmt(min(rx, bar))} "
                f"V{fmt(bar)} H0 V{fmt(min(rx, bar))} A{fmt(rx)} {fmt(rx)} 0 0 1 {fmt(rx)} 0 Z",
                fill=header_fill,
                stroke="none",
            )
        )
    cy0 = bar + cap * 1.6 + body_h / 2
    tx = (w + (icon_d + padding * 0.7 if icon else 0)) / 2 if icon else w / 2
    if icon:
        ic = header_fill or stroke
        ix = padding + icon_d / 2
        holder.append(_el("circle", cx=ix, cy=cy0, r=icon_d / 2, fill=ic, stroke="none"))
        el, _ = _centered_text(ix, cy0, icon, font_size * 0.8, fill="#FFFFFF", weight="bold")
        holder.append(el)
        tx = ix + icon_d / 2 + padding * 0.7 + (w - ix - icon_d / 2 - padding * 0.7 - padding) / 2
    top = cy0 - text_h / 2
    el, _ = _txt(tx, top - tb.y + font_size, title, font_size, fill=text_fill, weight="bold")
    holder.append(el)
    if sb:
        el, _ = _txt(
            tx,
            top + tb.height + gap - sb.y + font_size * 0.78,
            subtitle,
            font_size * 0.78,
            fill=_mix(text_fill, "#FFFFFF", 0.3),
        )
        holder.append(el)
    return _finish(holder, defs, Box(-sw / 2, -sw / 2, w + sw, h + sw))


_TF_COLORS = {"attn": "#F6D7A7", "norm": "#F3F1B8", "ffn": "#BFE3F2", "cross": "#F6D7A7"}


@_drawing_api(
    "parts",
    purpose='Transformer 编码器/解码器块（"Attention Is All You Need" Fig.1 样式）：Multi-Head Attention、Add & Norm、Feed Forward 子层，'
    "输入分叉进 Q/K/V，残差连接绕行到 Add & Norm，外框圆角大底板，左侧 N× 标记。",
    returns="Geometry（端口 input 底部入口、output 顶部出口、memory 解码器交叉注意力 K/V 的左侧入口、四边/center）",
    semantics=(
        'kind="encoder" 两个子层（MHA + FFN）；"decoder" 三个子层（Masked MHA + 交叉 MHA + FFN）。',
        'n 写成左侧 "N×"（n=None 不写）；width 为子层宽；colors 可覆盖 {"attn","norm","ffn"} 子层底色，frame 为外框色。',
        '残差箭头与 Q/K/V 分叉线都是原生路径；output_arrow=False 时顶部出口只画线不画箭头（外部再接线时用）；style="rich" 加外框阴影与子层光泽（局部 SVG）。',
        'ViT 的图像分块与 token 输入用 patch_embed；U-Net 瓶颈换 Transformer 用 encoder_decoder(bottleneck="transformer")。',
    ),
    example='enc = d.place(transformer_block(n=6), at=(260, 270), key="enc")\nd.arrow(emb.port("top"), enc.port("input"))',
    rank=14,
)
def transformer_block(
    *,
    kind="encoder",
    n=6,
    width=150,
    font_size=12,
    colors=None,
    frame="#7F8A96",
    line="#33404F",
    style="rich",
    labels=None,
    output_arrow=True,
):
    rich = _style(style)
    if kind not in ("encoder", "decoder"):
        raise ValueError("kind must be encoder or decoder")
    col = dict(_TF_COLORS, **(colors or {}))
    names = dict(
        attn="Multi-Head\nAttention", masked="Masked\nMulti-Head\nAttention", norm="Add & Norm", ffn="Feed\nForward"
    )
    names.update(labels or {})
    fs = font_size
    pad = fs * 1.4  # frame padding around the sub-layers
    gap = fs * 0.9  # gap between a sublayer and its Add&Norm
    sub_gap = fs * 2.0  # gap between sublayer groups (room for residual turn)
    norm_h = fs * 1.9
    tall = lambda txt: fs * 1.25 * (txt.count("\n") + 1) + fs * 1.2
    seq = ["masked", "cross", "ffn"] if kind == "decoder" else ["attn", "ffn"]
    seq_h = {k: tall(names.get(k, names["attn"])) for k in seq}
    total = sum(seq_h.values()) + len(seq) * (gap + norm_h) + (len(seq) - 1) * sub_gap
    W, H = width + 2 * pad, total + 2 * pad
    x0 = pad
    holder, defs = _start(rich)
    look = _look() if rich else None
    holder.append(
        _el(
            "path",
            d=_rrect(0, 0, W, H, fs * 1.1),
            fill=_mix(frame, "#FFFFFF", 0.9),
            stroke=frame,
            stroke_width=1.4,
            data_outline="1",
        )
    )
    if rich:
        _shadow(
            look,
            lambda dx, dy, s: _rrect(dx - (s - 1) * W / 2, dy - (s - 1) * H / 2, W * s, H * s, fs * 1.1),
            W,
            H,
            frame,
        )
        defs.append(_linear("gloss", [(0, "#FFFFFF", 0.6), (0.55, "#FFFFFF", 0.0), (1, "#000000", 0.05)]))
    sub_boxes = []  # (kind, y_top, height) top-down order: build from bottom up
    y = H - pad
    lines, heads = [], []
    lw = 1.3
    hs = fs * 0.55
    ports = {}
    entry_y = H + fs * 1.6
    cx = W / 2
    prev_top = None  # y where the previous Add&Norm output leaves (top edge)
    for i, k in enumerate(seq):
        sh = seq_h[k]
        s_bot, s_top = y, y - sh
        n_bot, n_top = s_top - gap, s_top - gap - norm_h
        fill = col["attn"] if k in ("masked", "cross", "attn") else col["ffn"]
        text = names["masked"] if k == "masked" else names["ffn"] if k == "ffn" else names["attn"]
        sub_boxes.append((s_top, sh, fill, text))
        sub_boxes.append((n_top, norm_h, col["norm"], names["norm"]))
        stream_y = entry_y if i == 0 else prev_top
        L = pad if i == 0 else stream_y - s_bot
        branch_y, res_y = s_bot + L * 0.4, s_bot + L * 0.78
        if k == "cross":
            # Q comes from the decoder stream (right third); K, V from the encoder memory on the left
            lines.append(f"M{fmt(cx)} {fmt(stream_y)} V{fmt(branch_y)} H{fmt(cx + width * 0.28)} V{fmt(s_bot)}")
            heads.append((cx + width * 0.28, s_bot, 0, -1))
            mem_y = branch_y
            kx, vx = cx - width * 0.3, cx - width * 0.06
            lines.append(
                f"M{fmt(-fs * 1.4)} {fmt(mem_y)} H{fmt(vx)} V{fmt(s_bot)} M{fmt(kx)} {fmt(mem_y)} V{fmt(s_bot)}"
            )
            heads.extend([(kx, s_bot, 0, -1), (vx, s_bot, 0, -1)])
            holder.append(_el("circle", cx=kx, cy=mem_y, r=lw * 1.6, fill=line))
            ports["memory"] = (-fs * 1.4, mem_y)
        else:
            lines.append(f"M{fmt(cx)} {fmt(stream_y)} V{fmt(s_bot)}")
            heads.append((cx, s_bot, 0, -1))
            if k in ("attn", "masked"):
                # V / K / Q fork into the attention box
                for dx in (-width * 0.28, width * 0.28):
                    lines.append(f"M{fmt(cx)} {fmt(branch_y)} H{fmt(cx + dx)} V{fmt(s_bot)}")
                    heads.append((cx + dx, s_bot, 0, -1))
                holder.append(_el("circle", cx=cx, cy=branch_y, r=lw * 1.6, fill=line))
        holder.append(_el("circle", cx=cx, cy=res_y, r=lw * 1.6, fill=line))
        lines.append(f"M{fmt(cx)} {fmt(s_top)} V{fmt(n_bot)}")
        heads.append((cx, n_bot, 0, -1))
        # residual: from the stream below the branch, out to the right, up into Add&Norm side
        rx_ = x0 + width + pad * 0.55
        lines.append(f"M{fmt(cx)} {fmt(res_y)} H{fmt(rx_)} V{fmt(n_top + norm_h / 2)} H{fmt(x0 + width)}")
        heads.append((x0 + width, n_top + norm_h / 2, -1, 0))
        prev_top = n_top
        y = n_top - sub_gap
    out_y = -fs * 1.6
    lines.append(f"M{fmt(cx)} {fmt(prev_top)} V{fmt(out_y + (hs if output_arrow else 0))}")
    if output_arrow:
        heads.append((cx, out_y, 0, -1))
    holder.append(_el("path", d=" ".join(lines), fill="none", stroke=line, stroke_width=lw, stroke_linejoin="round"))
    for hx, hy, dx, dy in heads:
        holder.append(_head(hx, hy, dx, dy, hs, line))
    for top, hh, fill, text in sub_boxes:
        holder.append(
            _el(
                "rect",
                x=x0,
                y=top,
                width=width,
                height=hh,
                rx=fs * 0.45,
                fill=fill,
                stroke=_mix(fill, "#000000", 0.38),
                stroke_width=1.1,
            )
        )
    if rich:
        for top, hh, fill, _ in sub_boxes:
            look.append(_el("rect", x=x0, y=top, width=width, height=hh, rx=fs * 0.45, fill="url(#gloss)"))
        holder.append(look)
    boxes = [Box(-0.7, -0.7, W + 1.4, H + 1.4), Box(cx - hs, out_y, 2 * hs, -out_y), Box(cx - 1, H, 2, entry_y - H)]
    for top, hh, fill, text in sub_boxes:
        rows = text.split("\n")
        lh = fs * 1.2
        y0 = top + hh / 2 - lh * (len(rows) - 1) / 2
        for j, row in enumerate(rows):
            el, _ = _centered_text(x0 + width / 2, y0 + j * lh, row, fs, fill=_INK)
            holder.append(el)
    if n is not None:
        el, b = _centered_text(
            -fs * 0.9 if kind == "encoder" else W + fs * 1.0, H / 2, f"{n}×", fs * 1.25, weight="bold"
        )
        el.set("text-anchor", "end" if kind == "encoder" else "start")
        el.set("x", fmt(-fs * 0.5 if kind == "encoder" else W + fs * 0.5))
        holder.append(el)
        tw = b.width
        boxes.append(
            Box(-fs * 0.5 - tw, H / 2 - fs * 0.8, tw, fs * 1.6)
            if kind == "encoder"
            else Box(W + fs * 0.5, H / 2 - fs * 0.8, tw, fs * 1.6)
        )
    if "memory" in ports:
        boxes.append(Box(ports["memory"][0], ports["memory"][1] - 1, 1, 2))
    ports.update(input=(cx, entry_y), output=(cx, out_y))
    return _finish(holder, defs, _union(boxes), **ports)


_ED_OPS = {
    "conv": ("conv 3×3, ReLU", "#33404F"),
    "down": ("max pool 2×2", "#C0392B"),
    "up": ("up-conv 2×2", "#2E8B57"),
    "skip": ("copy & concat", "#8A94A3"),
    "out": ("conv 1×1", "#2B7BB9"),
}


def _scan_image(holder, x, y, s, *, mask, color, seed):
    """Framed square thumbnail: grey-scale scan with an organ-like blob, or the same blob as a segmentation mask."""
    from ._bio_parts import _blob

    holder.append(
        _el(
            "rect", x=x, y=y, width=s, height=s, fill="#111418" if mask else "#3B4048", stroke="#1E2329", stroke_width=1
        )
    )
    if not mask:
        holder.append(
            _el(
                "path",
                d=_blob(s * 0.4, s * 0.36, wobble=0.08, lobes=3, seed=seed + 2),
                fill="#6E747D",
                transform=f"translate({fmt(x + s * 0.1)} {fmt(y + s * 0.12)})",
            )
        )
    holder.append(
        _el(
            "path",
            d=_blob(s * 0.2, s * 0.16, wobble=0.18, lobes=3, seed=seed),
            fill=color if mask else "#B9BEC6",
            transform=f"translate({fmt(x + s * 0.34)} {fmt(y + s * 0.36)})",
        )
    )
    if not mask:
        holder.append(
            _el(
                "path",
                d=_blob(s * 0.07, s * 0.06, wobble=0.2, lobes=2, seed=seed + 5),
                fill="#D9DCE1",
                transform=f"translate({fmt(x + s * 0.2)} {fmt(y + s * 0.62)})",
            )
        )
    holder.append(_el("rect", x=x, y=y, width=s, height=s, fill="none", stroke="#1E2329", stroke_width=1.2))


@_drawing_api(
    "parts",
    purpose="编码器–解码器 / U-Net 架构图（论文级）：3D 特征图立方体按分辨率定高、按通道定厚，编码端逐级下采样、解码端逐级上采样，"
    "跳跃连接横跨 U 形并在解码端拼接（浅色副本 + 上采样两段立方体），可把瓶颈换成 Transformer（TransUNet / Swin-UNet 类混合），可带输入/输出缩略图与图例。",
    returns="Geometry（原点在中心；端口 input/output 为缩略图中心（io=None 时为首尾立方体）、enc{i}/dec{i} 第 i 级编/解码立方体正面中心、"
    "skip{i} 第 i 条跳跃连接中点、bottleneck 瓶颈（或 Transformer）中心）",
    semantics=(
        "levels 自顶到底列出各级 (通道 C, 分辨率 H) 或 (C, H, W)，最后一项是瓶颈；数值只用于比例与标注：立方体高 ∝ H^0.7（height 为第 0 级高度 px）、厚度随 log2(C) 增加。",
        "标注沿用 U-Net 论文惯例：每个立方体下方写通道数，每级编码端左侧竖写 H×W；labels=False 全部关闭。",
        'layout="u" 画 U 形（跳跃连接为横跨 U 的水平箭头）；"flat" 一字排开（跳跃连接为上方弧线）。skip="concat" 解码端画拼接立方体，"add" 画 ⊕ 相加（残差/LinkNet 类）。',
        'bottleneck="transformer" 用 transformer_block 替换瓶颈（n_layers 为层数），特征图展平进入、输出后重塑回解码端。',
        'io=(输入名, 输出名) 画灰度扫描图与分割掩膜缩略图；io=None 不画。legend=True 在下方画箭头图例；ops 可覆盖 {"conv","down","up","skip","out"} 的 (说明, 颜色)。',
        'colors=(编码色, 解码色, 拼接副本色)；style="rich" 立方体加渐变网格（局部 SVG），"flat" 全原生。',
    ),
    example='net = d.place(encoder_decoder([(64, 256), (128, 128), (256, 64), (512, 32), (1024, 16)]), at=(480, 280), key="unet")\n'
    'd.callout("sk", "跳跃连接保留边界细节", net.port("skip1"), at=(700, 60), font_size=13)',
    rank=14,
)
def encoder_decoder(
    levels=((64, 256), (128, 128), (256, 64), (512, 32), (1024, 16)),
    *,
    layout="u",
    skip="concat",
    bottleneck="conv",
    n_layers=12,
    io=("输入图像", "分割掩膜"),
    legend=True,
    labels=True,
    ops=None,
    height=90,
    colors=("#7FA7D9", "#F2B880", "#E3E7EC"),
    font_size=11,
    style="rich",
    seed=3,
):
    rich = _style(style)
    if layout not in ("u", "flat"):
        raise ValueError('layout must be "u" or "flat"')
    if skip not in ("concat", "add"):
        raise ValueError('skip must be "concat" or "add"')
    if bottleneck not in ("conv", "transformer"):
        raise ValueError('bottleneck must be "conv" or "transformer"')
    lv = [tuple(l) + ((l[1],) if len(l) == 2 else ()) for l in levels]
    if len(lv) < 2 or any(len(l) != 3 for l in lv):
        raise ValueError("levels needs ≥ 2 entries of (C, H) or (C, H, W)")
    _finite(height, font_size, *[v for l in lv for v in l])
    fs = float(font_size)
    base = dict(_ED_OPS, skip=("skip, add", _ED_OPS["skip"][1])) if skip == "add" else _ED_OPS
    op = {k: tuple(v) for k, v in dict(base, **(ops or {})).items()}
    enc_c, dec_c, copy_c = colors
    n = len(lv)
    c0, r0 = lv[0][0], lv[0][1]
    thick = lambda c: 6 + 3.6 * math.log2(max(c, 1) / max(c0, 1)) if c >= c0 else 6.0
    tall = lambda r: max(fs * 1.6, height * (r / r0) ** 0.7)
    gap = max(22.0, fs * 2.2)  # arrow length between slabs
    vgap = fs * 2.0 + 22  # label row + inter-level arrow
    holder, defs = _start(rich)
    if rich:
        defs.extend(_slab_defs())
    look = _look() if rich else None
    slabs, arrows, ports = [], [], {}

    def slab(x, cy, c, r, fill, *, tag):
        H = tall(r)
        t, D = thick(c), H * 0.42
        s = dict(x=x, cy=cy, t=t, H=H, D=D, ox=D * 0.7071, oy=D * 0.7071 * 0.8, fill=fill, c=c, tag=tag)
        slabs.append(s)
        return s

    right = lambda s: s["x"] + s["t"] + s["ox"]
    mid = lambda s: s["x"] + s["t"] / 2
    top_face = lambda s: (
        s["cy"] - s["H"] / 2 - s["oy"] * min(1.0, s["t"] / 2 / s["ox"])
    )  # silhouette top above front centre

    x, cy = 0.0, 0.0
    enc, dec = [], []  # per level: list of slabs
    tf = None
    for i, (c, r, w) in enumerate(lv):
        if i:
            prev = enc[-1][-1]
            if layout == "u":
                H = tall(r)
                cy = prev["cy"] + prev["H"] / 2 + vgap + H * 0.42 * 0.7071 * 0.8 + H / 2
                x = mid(prev) - thick(c) / 2
            else:
                x = right(prev) + gap
        a = slab(x, cy, c, r, enc_c, tag=f"enc{i}")
        if i == n - 1 and bottleneck == "transformer":
            enc.append([a])
            break
        b = slab(right(a) + gap, cy, c, r, enc_c, tag=f"enc{i}b")
        arrows.append(("conv", [(right(a), cy), (b["x"], cy)]))
        enc.append([a, b])
    bott = enc[-1][-1]
    if bottleneck == "transformer":
        tg = transformer_block(
            n=n_layers, width=max(92.0, fs * 8.5), font_size=fs * 0.85, style=style, output_arrow=False
        )
        tb = tg.bounds
        tx = right(bott) + gap * 1.2 + (tg.ports["input"][0] - tb.x)  # transformer centre-line x
        oy_ = tg.ports["output"][1]
        dy = bott["cy"] - oy_  # output exit sits on the bottleneck row
        tf = (tg, tx - tg.ports["input"][0], dy)
        ex, ey = tg.ports["input"][0] + tf[1], tg.ports["input"][1] + dy
        arrows.append(("feed", [(mid(bott), bott["cy"] + bott["H"] / 2), (mid(bott), ey), (ex, ey)]))
        x_after = tb.x + tb.width + tf[1] + gap * 0.6
        ports["bottleneck"] = (tx, tb.y + tb.height / 2 + dy)
        out_from = (tx, bott["cy"])
    else:
        x_after = right(bott) + gap
        ports["bottleneck"] = (mid(bott), bott["cy"])
        out_from = None
    last = None
    for i in range(n - 2, -1, -1):
        c, r, w = lv[i]
        lc, lr, _ = lv[i + 1]
        src = last if last is not None else bott
        if layout == "u":
            H = tall(r)
            cy = enc[i][0]["cy"]
            if last is None and out_from is not None:  # first decoder slab right after the transformer, one level up
                x = x_after
                tmp = slab(x, bott["cy"], lc, lr, dec_c, tag="bott_out")
                arrows.append(("conv", [out_from, (x, bott["cy"])]))
                src = tmp
            x = mid(src) - thick(c) * (1.5 if skip == "concat" else 0.5)  # up-conv slab centred over its source
        else:
            if last is None and out_from is not None:
                tmp = slab(x_after, bott["cy"], lc, lr, dec_c, tag="bott_out")
                arrows.append(("conv", [out_from, (x_after, bott["cy"])]))
                src = tmp
            x = right(src) + gap
        if skip == "concat":
            cp = slab(x, cy, c, r, copy_c, tag=f"copy{i}")
            up = slab(x + cp["t"], cy, c, r, dec_c, tag=f"up{i}")
            up["concat"] = cp
        else:
            up = slab(x, cy, c, r, dec_c, tag=f"up{i}")
            cp = up
        if layout == "u":
            arrows.append(("up", [(mid(src), top_face(src)), (mid(src), cy + up["H"] / 2)]))
            src["side_label"] = True
        else:
            arrows.append(("up", [(right(src), cy), (cp["x"], cy)]))
        d_ = slab(right(up) + gap, cy, c, r, dec_c, tag=f"dec{i}")
        arrows.append(("conv", [(right(up), cy), (d_["x"], cy)]))
        dec.append((i, cp, up, d_))
        last = d_
    if layout == "u":  # pooling arrows (need next-level slabs)
        for i in range(n - 1):
            b, a = enc[i][-1], enc[i + 1][0]
            arrows.append(("down", [(mid(b), b["cy"] + b["H"] / 2), (mid(b), top_face(a))]))
            a["side_label"] = True
    else:
        for i in range(n - 1):
            b, a = enc[i][-1], enc[i + 1][0]
            arrows.append(("down", [(right(b), b["cy"]), (a["x"], a["cy"])]))
    skips = []
    for i, cp, up, d_ in dec:
        b = enc[i][-1]
        if layout == "u":
            pts = [(right(b), b["cy"]), (cp["x"], cp["cy"])]
        else:
            y0 = min(s["cy"] - s["H"] / 2 - s["oy"] for s in slabs) - fs * (1.2 + 1.3 * (n - 2 - i))
            pts = [
                (mid(b) + b["ox"] / 2, b["cy"] - b["H"] / 2 - b["oy"] / 2),
                (mid(b) + b["ox"] / 2, y0),
                (mid(cp) + cp["ox"] / 2, y0),
                (mid(cp) + cp["ox"] / 2, cp["cy"] - cp["H"] / 2 - cp["oy"] / 2),
            ]
        skips.append((i, pts))
    return _ed_render(
        holder,
        defs,
        look,
        rich,
        slabs,
        arrows,
        skips,
        enc,
        dec,
        tf,
        lv,
        op,
        io,
        legend,
        labels,
        skip,
        layout,
        fs,
        gap,
        colors,
        ports,
        seed,
    )


def _ed_render(
    holder,
    defs,
    look,
    rich,
    slabs,
    arrows,
    skips,
    enc,
    dec,
    tf,
    lv,
    op,
    io,
    legend,
    labels,
    skip,
    layout,
    fs,
    gap,
    colors,
    ports,
    seed,
):
    above = layout == "u"
    boxes, texts = [], []
    copies = {id(s["concat"]) for s in slabs if "concat" in s}
    for s in slabs:
        _slab(
            holder,
            look,
            s["x"],
            s["cy"] - s["H"] / 2 - s["oy"],
            s["t"],
            s["H"],
            s["D"],
            s["fill"],
            _mix(s["fill"], "#000000", 0.45),
            grid=rich,
        )
        boxes.append(
            Box(s["x"] - 0.5, s["cy"] - s["H"] / 2 - s["oy"] - 0.5, s["t"] + s["ox"] + 1, s["H"] + s["oy"] + 1)
        )
    if look is not None:
        holder.append(look)
    lw, hs = 1.4, 6.5

    def stroke(kind, pts, color=None, head=True):
        color = color or op.get(kind, op["conv"])[1]
        holder.append(_el("path", d=_poly(pts), fill="none", stroke=color, stroke_width=lw, stroke_linejoin="round"))
        if head:
            (x0, y0), (x1, y1) = pts[-2], pts[-1]
            holder.append(_head(x1, y1, x1 - x0, y1 - y0, hs, color))
        boxes.append(
            Box(
                min(p[0] for p in pts) - 1,
                min(p[1] for p in pts) - 1,
                max(p[0] for p in pts) - min(p[0] for p in pts) + 2,
                max(p[1] for p in pts) - min(p[1] for p in pts) + 2,
            )
        )

    for kind, pts in arrows:
        stroke("conv" if kind == "feed" else kind, pts, head=kind != "feed")
    sk_c = op["skip"][1]
    for i, pts in skips:
        end = pts[-1]
        if skip == "add":
            r = fs * 0.7
            d = (pts[-1][0] - pts[-2][0], pts[-1][1] - pts[-2][1])
            nrm = math.hypot(*d) or 1
            cx, cy = end[0] - d[0] / nrm * r, end[1] - d[1] / nrm * r
            pts = pts[:-1] + [(cx - d[0] / nrm * r, cy - d[1] / nrm * r)]
            stroke("skip", pts, sk_c)
            holder.append(_el("circle", cx=cx, cy=cy, r=r, fill="#FFFFFF", stroke=sk_c, stroke_width=lw))
            k = r * 0.55
            holder.append(
                _el(
                    "path",
                    d=f"M{fmt(cx - k)} {fmt(cy)} H{fmt(cx + k)} M{fmt(cx)} {fmt(cy - k)} V{fmt(cy + k)}",
                    fill="none",
                    stroke=sk_c,
                    stroke_width=lw,
                )
            )
        else:
            stroke("skip", pts, sk_c)
        L = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
        half, acc = sum(L) / 2, 0.0
        for (a, b), l in zip(zip(pts, pts[1:]), L):
            if acc + l >= half:
                f = (half - acc) / (l or 1)
                ports[f"skip{i}"] = (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
                break
            acc += l
    if tf is not None:
        tg, dx, dy = tf
        g = _el("g", transform=f"translate({fmt(dx)} {fmt(dy)})")
        g.append(tg.element)
        holder.append(g)
        b = tg.bounds
        boxes.append(Box(b.x + dx, b.y + dy, b.width, b.height))
    if labels:
        for s in slabs:
            if id(s) in copies:
                continue
            c = s["c"] * 2 if "concat" in s else s["c"]
            x = s["x"] - (s["concat"]["t"] / 2 if "concat" in s else 0) + s["t"] / 2
            if above:
                y = s["cy"] - s["H"] / 2 - s["oy"] - fs * 0.45
                anchor = "middle"
                if s.get("side_label"):  # a vertical arrow lands on the top face: write beside it
                    x, anchor = s["x"] + s["t"] / 2 + fs * 0.4, "start"
            else:
                y, anchor = s["cy"] + s["H"] / 2 + fs * 1.25, "middle"
            el, b = _txt(x, y, c, fs, fill=_INK, anchor=anchor)
            texts.append(el)
            boxes.append(b)
        for i, row in enumerate(enc):
            a = row[0]
            r, w = lv[i][1], lv[i][2]
            txt = f"{r:g}×{w:g}" if not isinstance(r, str) else f"{r}×{w}"
            if above:
                el, b = _txt(
                    a["x"] - fs * 0.35, a["cy"] + a["H"] / 2, txt, fs * 0.9, fill="#5B6573", anchor="start", rotate=-90
                )
            else:
                el, b = _txt(a["x"] + a["t"] / 2, a["cy"] + a["H"] / 2 + fs * 2.45, txt, fs * 0.9, fill="#5B6573")
            texts.append(el)
            boxes.append(b)
    first, final = enc[0][0], dec[-1][3]
    ports.update({f"enc{i}": (row[0]["x"] + row[0]["t"] / 2, row[0]["cy"]) for i, row in enumerate(enc)})
    ports.update({f"dec{i}": (d_["x"] + d_["t"] / 2, d_["cy"]) for i, _, _, d_ in dec})
    ports["input"], ports["output"] = ports["enc0"], ports["dec0"]
    if io:
        sz = max(fs * 4, min(first["H"] * 0.8, 110.0))
        hw = _label(f"{lv[0][1]:g}×{lv[0][2]:g}", font_size=fs * 0.9).bounds.width if above and labels else 0
        clear = first["H"] / 2 - hw > fs * 0.8  # rotated H×W label sits below the arrow row
        ix = first["x"] - gap * 1.2 - sz - (0 if clear or not hw else fs * 1.4)
        _scan_image(holder, ix, first["cy"] - sz / 2, sz, mask=False, color=colors[1], seed=seed)
        stroke("conv", [(ix + sz + 2, first["cy"]), (first["x"] - (2 if clear or not hw else fs * 1.5), first["cy"])])
        ox_ = final["x"] + final["t"] + final["ox"] + gap * 1.2
        stroke("out", [(final["x"] + final["t"] + final["ox"] + 2, final["cy"]), (ox_ - 2, final["cy"])])
        _scan_image(holder, ox_, final["cy"] - sz / 2, sz, mask=True, color="#F2C14E", seed=seed)
        boxes += [
            Box(ix - 0.6, first["cy"] - sz / 2 - 0.6, sz + 1.2, sz + 1.2),
            Box(ox_ - 0.6, final["cy"] - sz / 2 - 0.6, sz + 1.2, sz + 1.2),
        ]
        for (x0, cy), name in zip(((ix, first["cy"]), (ox_, final["cy"])), io):
            if name:
                el, b = _txt(x0 + sz / 2, cy + sz / 2 + fs * 1.35, name, fs, fill=_INK)
                texts.append(el)
                boxes.append(b)
        ports["input"], ports["output"] = (ix + sz / 2, first["cy"]), (ox_ + sz / 2, final["cy"])
    if legend:
        used = ["conv", "down", "up", "skip"] + (["out"] if io else [])
        items = [("arrow", op[k][0], op[k][1]) for k in used]
        lg = legend_row(items, font_size=fs, gap=fs * 1.6)
        bb = _union(boxes)
        lx = bb.x + bb.width / 2 - lg.bounds.width / 2 - lg.bounds.x
        ly = bb.y + bb.height + fs * 1.2 - lg.bounds.y
        g = _el("g", transform=f"translate({fmt(lx)} {fmt(ly)})")
        g.append(lg.element)
        holder.append(g)
        boxes.append(Box(lg.bounds.x + lx, lg.bounds.y + ly, lg.bounds.width, lg.bounds.height))
    holder.extend(texts)
    return _finish(holder, defs, _union(boxes), **ports)


@_drawing_api(
    "parts",
    purpose='ViT 图像分块嵌入（"An Image is Worth 16×16 Words" Fig.1 样式）：图像切成 grid 个小块（细白分隔线）→ 展平成一排 patch，'
    "每块经线性投影成 token，前置 [CLS]，下方叠加位置编码编号，整排 token 可直接箭头接 transformer_block。",
    returns="Geometry（原点在中心；端口 image 原图中心、tokens 整排 token 中心、tokens_top/tokens_right token 行上缘中点/右端、"
    "cls [CLS] 上缘、token{k} 第 k 个 patch token 上缘、proj 线性投影条中心）",
    semantics=(
        "grid=(行, 列)；max_tokens 超出时 token 行中间画省略号（端口只给画出的）。cell 为原图每块边长 px，token 为 token 方块边长。",
        'cls=True 前置 [CLS] token（"*" 标记），pos=True 每个 token 下方画位置编码小圆（0,1,2…）；proj_label 写在线性投影条上（None 不画投影条）。',
        'image="scan"（灰度扫描）或 "photo"（彩色）只改缩略图纹理；color 为 patch token 色。style="rich" 加 token 光泽（局部 SVG），"flat" 全原生。',
    ),
    example='pe = d.place(patch_embed(grid=(4, 4)), at=(300, 300), key="pe")\n'
    'enc = d.place(transformer_block(n=12), at=(760, 300), key="enc")\nd.arrow(pe.port("tokens_right"), enc.port("input"), route="orthogonal")',
    rank=15,
)
def patch_embed(
    grid=(4, 4),
    *,
    cell=26,
    token=20,
    max_tokens=9,
    cls=True,
    pos=True,
    proj_label="Linear Projection of Flattened Patches",
    image="scan",
    color="#F2B880",
    font_size=11,
    style="rich",
    seed=3,
):
    rich = _style(style)
    rows, cols = (int(v) for v in grid)
    if rows < 1 or cols < 1:
        raise ValueError("grid must be (rows, cols) ≥ 1")
    if image not in ("scan", "photo"):
        raise ValueError('image must be "scan" or "photo"')
    _finite(cell, token, font_size)
    fs = float(font_size)
    holder, defs = _start(rich)
    boxes, ports = [], {}
    Wi, Hi = cell * cols, cell * rows
    if image == "scan":
        _scan_image(holder, 0, 0, max(Wi, Hi), mask=False, color=color, seed=seed)
    else:
        from ._bio_parts import _blob

        holder.append(_el("rect", x=0, y=0, width=Wi, height=Hi, fill="#9CC6E4"))
        holder.append(
            _el(
                "path",
                d=f"M0 {fmt(Hi * 0.62)} Q{fmt(Wi * 0.3)} {fmt(Hi * 0.45)} {fmt(Wi * 0.55)} {fmt(Hi * 0.6)} T{fmt(Wi)} {fmt(Hi * 0.55)} V{fmt(Hi)} H0 Z",
                fill="#7BAA5A",
            )
        )
        holder.append(
            _el(
                "path",
                d=_blob(Wi * 0.14, Hi * 0.14, seed=seed),
                fill="#F3C64B",
                transform=f"translate({fmt(Wi * 0.62)} {fmt(Hi * 0.1)})",
            )
        )
        holder.append(_el("rect", x=0, y=0, width=Wi, height=Hi, fill="none", stroke="#1E2329", stroke_width=1.2))
    Wi, Hi = (max(Wi, Hi),) * 2 if image == "scan" else (Wi, Hi)
    cw, ch = Wi / cols, Hi / rows
    holder[1].set("data-outline", "1")  # holder[0] is defs; [1] is the image frame
    sep = " ".join(
        [f"M{fmt(cw * k)} 0 V{fmt(Hi)}" for k in range(1, cols)]
        + [f"M0 {fmt(ch * k)} H{fmt(Wi)}" for k in range(1, rows)]
    )
    if sep:
        holder.append(_el("path", d=sep, fill="none", stroke="#FFFFFF", stroke_width=2.2))
    boxes.append(Box(-0.6, -0.6, Wi + 1.2, Hi + 1.2))
    ports["image"] = (Wi / 2, Hi / 2)
    n = rows * cols
    shown = list(range(n)) if n <= max_tokens else list(range(max_tokens - 2)) + [None, n - 1]
    pw = token * 0.62 if pos else 0.0  # position-embedding box joined to the left of each token
    unit_w = pw + token
    tg = token * 0.55
    seq = (["cls"] if cls else []) + shown
    x0 = Wi + max(40.0, fs * 4)
    row_w = len(seq) * unit_w + (len(seq) - 1) * tg
    rg = fs * 1.6  # vertical gap between rows (arrow length)
    bh = fs * 1.9 if proj_label else 0.0
    patch_y = Hi / 2 - token / 2  # patch row centred on the image
    proj_y = patch_y - rg - bh
    ty = (proj_y if proj_label else patch_y) - rg - token
    lc = "#33404F"
    slots = []
    x = x0
    for idx in seq:
        slots.append((x, idx))
        x += unit_w + tg
    texts, tok_x = [], []
    for x, idx in slots:
        tx = x + pw
        cx = tx + token / 2
        if idx is None:
            dots = " ".join(
                _circ(cx - pw / 2 + k * token * 0.3, yy, 1.5)
                for k in (-1, 0, 1)
                for yy in (ty + token / 2, patch_y + token / 2)
            )
            holder.append(_el("path", d=dots, fill="#4A5563"))
            continue
        fill = "#D9C2E8" if idx == "cls" else color
        holder.append(
            _el(
                "rect",
                x=tx,
                y=ty,
                width=token,
                height=token,
                rx=token * 0.12,
                fill=fill,
                stroke=_mix(fill, "#000000", 0.4),
                stroke_width=1,
            )
        )
        tok_x.append(tx)
        if pos:
            pc = "#8A6FB0"
            holder.append(
                _el(
                    "rect",
                    x=x,
                    y=ty,
                    width=pw + 0.5,
                    height=token,
                    rx=token * 0.12,
                    fill="#EDE3F5",
                    stroke=pc,
                    stroke_width=0.9,
                )
            )
            el, _ = _centered_text(
                x + pw / 2, ty + token / 2, 0 if idx == "cls" else idx + (1 if cls else 0), fs * 0.78, fill=_INK
            )
            texts.append(el)
        if idx == "cls":
            el, _ = _centered_text(cx, ty + token / 2 + fs * 0.25, "*", fs * 1.5, weight="bold")
            texts.append(el)
            ports["cls"] = (cx, ty)
            continue
        ports[f"token{idx}"] = (cx, ty)
        r_, c_ = divmod(idx, cols)  # the flattened patch: its share of the image, shaded by position
        v = math.exp(-(((r_ + 0.5) / rows - 0.5) ** 2) / 0.06 - ((c_ + 0.5) / cols - 0.5) ** 2 / 0.06)
        holder.append(
            _el(
                "rect",
                x=tx,
                y=patch_y,
                width=token,
                height=token,
                fill=_mix("#3B4048", "#C3C8CF", 0.15 + 0.8 * v),
                stroke="#1E2329",
                stroke_width=0.9,
            )
        )
        top_to = (proj_y + bh) if proj_label else ty + token
        holder.append(
            _el("path", d=f"M{fmt(cx)} {fmt(patch_y)} V{fmt(top_to + 4)}", fill="none", stroke=lc, stroke_width=0.9)
        )
        holder.append(_head(cx, top_to, 0, -1, 4.5, lc))
        if proj_label:
            holder.append(
                _el(
                    "path",
                    d=f"M{fmt(cx)} {fmt(proj_y)} V{fmt(ty + token + 4)}",
                    fill="none",
                    stroke=lc,
                    stroke_width=0.9,
                )
            )
            holder.append(_head(cx, ty + token, 0, -1, 4.5, lc))
    if proj_label:
        bw = max(row_w, _label(proj_label, font_size=fs * 0.9).bounds.width + fs * 2)
        bx = x0 + row_w / 2 - bw / 2
        holder.append(
            _el(
                "rect",
                x=bx,
                y=proj_y,
                width=bw,
                height=bh,
                rx=bh * 0.3,
                fill="#F3E3D3",
                stroke="#B88A62",
                stroke_width=1,
            )
        )
        el, _ = _centered_text(bx + bw / 2, proj_y + bh / 2, proj_label, fs * 0.9, fill=_INK)
        texts.append(el)
        boxes.append(Box(bx - 0.5, proj_y - 0.5, bw + 1, bh + 1))
        ports["proj"] = (bx + bw / 2, proj_y + bh / 2)
    first_patch = slots[1 if cls else 0][0] + pw
    holder.append(
        _el("path", d=f"M{fmt(Wi + 4)} {fmt(Hi / 2)} H{fmt(first_patch - 6)}", fill="none", stroke=lc, stroke_width=1.3)
    )
    holder.append(_head(first_patch - 1, Hi / 2, 1, 0, 6, lc))
    if rich:
        defs.append(_linear("tokg", [(0, "#FFFFFF", 0.5), (0.55, "#FFFFFF", 0.0), (1, "#000000", 0.06)]))
        look = _look()
        for tx in tok_x:
            look.append(_el("rect", x=tx, y=ty, width=token, height=token, rx=token * 0.12, fill="url(#tokg)"))
        holder.append(look)
    holder.extend(texts)
    boxes += [Box(x0 - 0.5, ty - 0.5, row_w + 1, token + 1), Box(x0, patch_y - 0.5, row_w, token + 1)]
    ports.update(
        tokens=(x0 + row_w / 2, ty + token / 2),
        tokens_top=(x0 + row_w / 2, ty),
        tokens_right=(x0 + row_w, ty + token / 2),
    )
    return _finish(holder, defs, _union(boxes), **ports)


def _wave_value(kind, t, cycles):
    ph = t * cycles * 2 * math.pi
    if kind == "square":
        return 1 if math.sin(ph) >= 0 else -1
    if kind == "pulse":
        return 1 if (t * cycles) % 1 < 0.18 else -1
    if kind == "damped":
        return math.exp(-3 * t) * math.sin(ph)
    if kind == "packet":
        return math.exp(-(((t - 0.5) / 0.16) ** 2)) * math.cos(ph)
    if kind == "sawtooth":
        return 2 * ((t * cycles) % 1) - 1
    return math.sin(ph)


@_drawing_api(
    "parts",
    purpose="波形/信号段（正弦、方波、脉冲、阻尼振荡、高斯波包、锯齿），可带坐标小轴与包络。",
    returns="Geometry（端口 left/right 为基线两端，peak 为最高点）",
    semantics=(
        "kind 为 sine/square/pulse/damped/packet/sawtooth；cycles 为周期数（packet 为载波周期数，建议 6–10）；用于信号、电磁波、振动示意，不用于数据曲线。",
        "axes=True 画带箭头的 t/幅值小轴（x_label/y_label 文字可改）；envelope=True 对 damped/packet 画虚线包络。",
        'style="rich" 在曲线下加淡色渐变填充（局部 SVG）；曲线本身始终是原生路径。',
    ),
    example='d.place(wave(260, 40, kind="packet", cycles=8, axes=True, stroke="#E24C3B"), at=(430, 220), key="w")',
    rank=11,
)
def wave(
    width,
    amplitude,
    *,
    kind="sine",
    cycles=3,
    stroke="#4A6FA5",
    stroke_width=2,
    samples=None,
    axes=False,
    envelope=None,
    x_label="t",
    y_label=None,
    font_size=11,
    style="rich",
):
    _finite(width, amplitude)
    if kind not in ("sine", "square", "pulse", "damped", "packet", "sawtooth"):
        raise ValueError("wave kind must be sine/square/pulse/damped/packet/sawtooth")
    rich = _style(style)
    samples = samples or max(120, int(cycles * 40))
    pts = []
    for i in range(samples + 1):
        t = i / samples
        pts.append((t * width, amplitude - _wave_value(kind, t, cycles) * amplitude))
    if kind in ("square", "pulse"):  # exact vertical edges
        sq = [pts[0]]
        for p in pts[1:]:
            if abs(p[1] - sq[-1][1]) > 1e-9:
                sq.append((p[0], sq[-1][1]))
            sq.append(p)
        pts = sq
    holder, defs = _start(rich)
    curve = _poly(pts)
    boxes = [Box(0, -stroke_width / 2, width, 2 * amplitude + stroke_width)]
    if rich and kind not in ("square", "pulse"):
        defs.append(_linear("wfill", [(0, stroke, 0.22), (0.5, stroke, 0.04), (1, stroke, 0.22)]))
        look = _look()
        look.append(_el("path", d=curve + f" L{fmt(width)} {fmt(amplitude)} L0 {fmt(amplitude)} Z", fill="url(#wfill)"))
        holder.append(look)
    envelope = (kind in ("damped", "packet") and (axes or rich)) if envelope is None else envelope
    if axes:
        ac = "#5A6573"
        ext = amplitude * 0.25 + 6
        holder.append(
            _el(
                "path",
                d=f"M0 {fmt(amplitude)} H{fmt(width + ext)} M0 {fmt(2 * amplitude + 4)} V{fmt(-ext)}",
                fill="none",
                stroke=ac,
                stroke_width=1,
            )
        )
        holder.append(_head(width + ext + 6, amplitude, 1, 0, 6, ac))
        holder.append(_head(0, -ext - 6, 0, -1, 6, ac))
        el, b = _txt(
            width + ext + 8, amplitude + font_size * 1.2, x_label, font_size, fill=ac, anchor="end", italic=True
        )
        holder.append(el)
        boxes += [b, Box(0, -ext - 6, width + ext + 6, 2 * amplitude + ext + 10)]
        if y_label:
            el, b = _txt(5, -ext, y_label, font_size, fill=ac, anchor="start", italic=True)
            holder.append(el)
            boxes.append(b)
    if envelope and kind in ("damped", "packet"):
        env = []
        for sign in (1, -1):
            e = []
            for i in range(61):
                t = i / 60
                v = math.exp(-3 * t) if kind == "damped" else math.exp(-(((t - 0.5) / 0.16) ** 2))
                e.append((t * width, amplitude - sign * v * amplitude))
            env.append(_poly(e))
        holder.append(
            _el(
                "path",
                d=" ".join(env),
                fill="none",
                stroke=_mix(stroke, "#FFFFFF", 0.35),
                stroke_width=1,
                stroke_dasharray="4 3",
            )
        )
    holder.append(
        _el(
            "path",
            d=curve,
            fill="none",
            stroke=stroke,
            stroke_width=stroke_width,
            stroke_linejoin="round",
            stroke_linecap="round",
        )
    )
    peak = min(pts, key=lambda p: p[1])
    return _finish(holder, defs, _union(boxes), left=(0, amplitude), right=(width, amplitude), peak=peak)


@_drawing_api(
    "parts",
    purpose="透镜（教科书光学图）：双凸/双凹截面，玻璃质感，可画主光轴与焦点 F。",
    returns="Geometry（端口 left/right 为光轴与透镜表面交点，top/bottom 为边缘，focus_l/focus_r 为焦点）",
    semantics=(
        'kind="convex" 双凸、"concave" 双凹；height 为口径、thickness 为中心（凸）或边缘（凹）厚度。',
        "axis=True 画贯穿的点划线主光轴（长度 axis_length，默认 3×height），focal 给出焦距时在两侧标 F；",
        'style="rich" 加玻璃渐变、边缘高光与反光条（局部 SVG），"flat" 为原生浅色填充。',
    ),
    example='L = d.place(lens(140, kind="convex", axis=True, focal=110), at=(480, 270), key="L")',
    rank=15,
)
def lens(
    height=120,
    *,
    kind="convex",
    thickness=None,
    fill="#CFE6F5",
    stroke="#4F7FA8",
    axis=False,
    axis_length=None,
    focal=None,
    font_size=12,
    style="rich",
):
    _finite(height)
    if kind not in ("convex", "concave"):
        raise ValueError("lens kind must be convex or concave")
    rich = _style(style)
    h = height
    t = thickness or h * (0.26 if kind == "convex" else 0.3)
    holder, defs = _start(rich)
    if kind == "convex":
        bulge = t / 2
        d = f"M0 {fmt(-h / 2)} Q{fmt(bulge * 2)} 0 0 {fmt(h / 2)} Q{fmt(-bulge * 2)} 0 0 {fmt(-h / 2)} Z"
        half_w = bulge
        face_x = bulge
    else:
        rim, waist = t / 2, max(2.5, t * 0.14)
        dip = rim - waist
        d = (
            f"M{fmt(-rim)} {fmt(-h / 2)} H{fmt(rim)} Q{fmt(rim - 2 * dip)} 0 {fmt(rim)} {fmt(h / 2)} "
            f"H{fmt(-rim)} Q{fmt(-rim + 2 * dip)} 0 {fmt(-rim)} {fmt(-h / 2)} Z"
        )
        half_w = rim
        face_x = waist
    holder.append(
        _el(
            "path",
            d=d,
            fill=fill,
            fill_opacity=0.85 if not rich else None,
            stroke=stroke,
            stroke_width=1.4,
            stroke_linejoin="round",
            data_outline="1",
        )
    )
    if rich:
        defs.append(
            _linear(
                "glass",
                [
                    (0, "#FFFFFF", 0.7),
                    (0.35, "#FFFFFF", 0.1),
                    (0.7, _mix(stroke, "#000000", 0.2), 0.18),
                    (1, "#FFFFFF", 0.55),
                ],
                x2=1,
                y2=0,
            )
        )
        defs.append(_linear("sheen", [(0, "#FFFFFF", 0.0), (0.5, "#FFFFFF", 0.85), (1, "#FFFFFF", 0.0)]))
        look = _look()
        look.append(_el("path", d=d, fill="url(#glass)"))
        sx = -face_x * 0.45
        look.append(
            _el(
                "path",
                d=f"M{fmt(sx)} {fmt(-h * 0.36)} Q{fmt(sx - face_x * 0.35)} 0 {fmt(sx)} {fmt(h * 0.36)}",
                fill="none",
                stroke="url(#sheen)",
                stroke_width=max(1.5, half_w * 0.28),
                stroke_linecap="round",
            )
        )
        look.append(
            _el(
                "path",
                d=d,
                fill="none",
                stroke="#FFFFFF",
                stroke_width=0.8,
                stroke_opacity=0.7,
                transform="translate(.8 .8)",
            )
        )
        holder.append(look)
    boxes = [Box(-half_w - 1, -h / 2 - 1, 2 * half_w + 2, h + 2)]
    ports = dict(left=(-face_x, 0), right=(face_x, 0))
    if axis:
        L = axis_length or max(3 * h, (focal or 0) * 2.5)
        holder.append(
            _el(
                "path",
                d=f"M{fmt(-L / 2)} 0 H{fmt(L / 2)}",
                fill="none",
                stroke="#6B7480",
                stroke_width=0.9,
                stroke_dasharray="9 3 2 3",
            )
        )
        boxes.append(Box(-L / 2, -1, L, 2))
    if focal:
        for sx, nm in ((-1, "focus_l"), (1, "focus_r")):
            fx = sx * focal
            holder.append(_el("circle", cx=fx, cy=0, r=2.6, fill="#33404F"))
            el, b = _txt(fx, font_size * 1.45, "F" if sx > 0 else "F'", font_size, italic=True)
            holder.append(el)
            boxes.append(b)
            ports[nm] = (fx, 0)
    if not len(defs):
        holder.remove(defs)
    g = Geometry(holder, _union(boxes))
    b = g.bounds
    ports.update(top=(0, -h / 2), bottom=(0, h / 2))
    return _with_edges(g, **ports)


@_drawing_api(
    "parts",
    purpose="激光光束：水平光束带（亮芯 + 辉光），可选高斯束腰与传播方向箭头。",
    returns="Geometry（端口 left/right 为光束两端中心，waist 为束腰）",
    semantics=(
        "length 为长度，width 为光束宽；waist=0–1 时在 waist_at（0–1）处收窄为 width×waist（聚焦光束）。",
        "color 为激光色（如 #E5322D 红、#2DB84D 绿）；arrow=True 在末端画传播方向箭头。",
        'style="rich" 外加多层辉光渐变（局部 SVG）；光束主体与亮芯始终为原生形状。需要斜向时 d.place 后 set_transform(rotation=…)。',
    ),
    example='d.place(laser_beam(320, color="#E5322D", waist=0.35, waist_at=0.6), at=(480, 200), key="beam")',
    rank=16,
)
def laser_beam(length, *, width=10, color="#E5322D", waist=None, waist_at=0.5, arrow=True, style="rich"):
    _finite(length, width)
    rich = _style(style)
    holder, defs = _start(rich)
    n = 48

    def half(t, scale=1.0):
        if not waist:
            return width / 2 * scale
        z = (t - waist_at) / max(0.12, min(waist_at, 1 - waist_at))
        return width / 2 * scale * (waist + (1 - waist) * min(1.0, abs(z)) ** 1.3)

    def band(scale):
        up = [(length * i / n, -half(i / n, scale)) for i in range(n + 1)]
        lo = [(x, -y) for x, y in reversed(up)]
        return _poly(up + lo, True)

    holder.append(_el("path", d=band(1.0), fill=color, stroke="none", data_outline="1"))
    if rich:
        defs.append(_linear("glow", [(0, color, 0.0), (0.5, color, 0.5), (1, color, 0.0)]))
        look = _look()
        for s, op in ((3.2, 0.18), (2.2, 0.3), (1.5, 0.45)):
            look.append(_el("path", d=band(s), fill="url(#glow)", fill_opacity=op))
        holder.append(look)
    holder.append(_el("path", d=band(0.38), fill=_mix(color, "#FFFFFF", 0.72), stroke="none"))
    boxes = [Box(0, -width * (1.6 if rich else 0.5), length, width * (3.2 if rich else 1))]
    if arrow:
        a = max(8.0, width * 1.1)
        holder.append(_head(length + a, 0, 1, 0, a, color))
        boxes.append(Box(length, -a * 0.45, a, a * 0.9))
    ports = dict(left=(0, 0), right=(length + (max(8.0, width * 1.1) if arrow else 0), 0))
    if waist:
        ports["waist"] = (length * waist_at, 0)
    return _finish(holder, defs, _union(boxes), **ports)


_CIRCUIT_KINDS = (
    "resistor",
    "resistor_iec",
    "capacitor",
    "inductor",
    "source_dc",
    "source_ac",
    "battery",
    "diode",
    "ground",
    "switch",
    "lamp",
    "galvanometer",
    "ammeter",
    "voltmeter",
    "rheostat",
    "inductor_core",
)
_METER_LETTER = {"galvanometer": "G", "ammeter": "A", "voltmeter": "V"}


@_drawing_api(
    "parts",
    purpose="电路元件符号（标准电路图形状）：电阻（ANSI 锯齿 / IEC 方框）、滑动变阻器、电容、电感（可带铁芯）、直流/交流源、电池、二极管、接地、开关、灯、电流计 G / 电流表 A / 电压表 V。",
    returns="Geometry（端口 a 为左端、b 为右端引线端点；接地只有 a 在上端；rheostat 另有 wiper 为滑片顶端）",
    semantics=(
        "kind 见 resistor/resistor_iec/rheostat/capacitor/inductor/inductor_core/source_dc/source_ac/battery/diode/ground/switch/lamp/galvanometer/ammeter/voltmeter；length 为含引线的总长（水平放置，a→b 从左到右）。",
        "galvanometer 画表盘刻度 + 指针，deflect=-1/0/1 指针左偏/居中/右偏（表示感应电流方向）；ammeter/voltmeter 为圆圈内字母。",
        "name 写元件标号（R1、C、L…）放在上方，value 写数值（10 kΩ）放在下方；竖直放置用 d.place 后 set_transform(rotation=90)。",
        '整个回路用 circuit_loop 自动布线；单独连线用 d.line(node.port("b"), other.port("a"), route="orthogonal")；全部是原生线条，style 仅为接口一致。',
    ),
    example='r = d.place(circuit_symbol("resistor", name="R1", value="10 kΩ"), at=(300, 200), key="r1")\n'
    'c = d.place(circuit_symbol("capacitor", name="C1"), at=(460, 200), key="c1")\nd.line(r.port("b"), c.port("a"), stroke="#222")',
    rank=17,
)
def circuit_symbol(
    kind,
    *,
    length=90,
    size=None,
    stroke="#1E1E1E",
    stroke_width=1.8,
    name=None,
    value=None,
    font_size=12,
    fill="#FFFFFF",
    accent=None,
    style="rich",
    deflect=0,
):
    if kind not in _CIRCUIT_KINDS:
        raise ValueError(f"circuit_symbol kind must be one of {_CIRCUIT_KINDS}")
    _style(style)
    s = size or 22.0  # body height scale
    L = float(length)
    holder = _el("g")
    sw = stroke_width
    paint = dict(fill="none", stroke=stroke, stroke_width=sw, stroke_linecap="round", stroke_linejoin="round")
    acc = accent or stroke
    body = min(L * 0.5, s * 2.2)
    x0, x1 = (L - body) / 2, (L + body) / 2
    lead = f"M0 0 H{fmt(x0)} M{fmt(x1)} 0 H{fmt(L)}"
    top, bot = -s / 2, s / 2
    extra = {}
    if kind == "ground":
        d = f"M0 0 V{fmt(s * 0.6)} M{fmt(-s * 0.6)} {fmt(s * 0.6)} H{fmt(s * 0.6)} M{fmt(-s * 0.38)} {fmt(s * 0.85)} H{fmt(s * 0.38)} M{fmt(-s * 0.16)} {fmt(s * 1.1)} H{fmt(s * 0.16)}"
        holder.append(_el("path", d=d, data_outline="1", **paint))
        return _finish(holder, None, Box(-s * 0.6 - sw, -sw / 2, s * 1.2 + 2 * sw, s * 1.1 + sw), a=(0, 0))
    if kind == "resistor":
        z = 6
        pts = [(x0, 0)] + [(x0 + body * (i + 0.5) / z, (-1) ** i * s * 0.38) for i in range(z)] + [(x1, 0)]
        holder.append(_el("path", d=lead + " " + _poly(pts), data_outline="1", **paint))
    elif kind == "resistor_iec":
        holder.append(_el("path", d=lead, data_outline="1", **paint))
        holder.append(
            _el("rect", x=x0, y=-s * 0.3, width=body, height=s * 0.6, fill=fill, stroke=stroke, stroke_width=sw)
        )
    elif kind == "capacitor":
        g = s * 0.32
        cx = L / 2
        holder.append(
            _el(
                "path",
                d=f"M0 0 H{fmt(cx - g / 2)} M{fmt(cx + g / 2)} 0 H{fmt(L)} "
                f"M{fmt(cx - g / 2)} {fmt(top)} V{fmt(bot)} M{fmt(cx + g / 2)} {fmt(top)} V{fmt(bot)}",
                data_outline="1",
                **dict(paint, stroke_linecap="butt"),
            )
        )
        holder[-1].set("stroke-width", fmt(sw))
        holder.append(
            _el(
                "path",
                d=f"M{fmt(cx - g / 2)} {fmt(top)} V{fmt(bot)} M{fmt(cx + g / 2)} {fmt(top)} V{fmt(bot)}",
                fill="none",
                stroke=stroke,
                stroke_width=sw * 1.6,
            )
        )
    elif kind == "inductor":
        k = 4
        r = body / k / 2
        arcs = " ".join(f"A{fmt(r)} {fmt(r)} 0 0 1 {fmt(x0 + 2 * r * (i + 1))} 0" for i in range(k))
        holder.append(_el("path", d=f"{lead} M{fmt(x0)} 0 {arcs}", data_outline="1", **paint))
        top = min(top, -r)
    elif kind in ("source_dc", "source_ac", "lamp"):
        r = s * 0.72
        cx = L / 2
        holder.append(_el("path", d=f"M0 0 H{fmt(cx - r)} M{fmt(cx + r)} 0 H{fmt(L)}", data_outline="1", **paint))
        holder.append(_el("circle", cx=cx, cy=0, r=r, fill=fill, stroke=stroke, stroke_width=sw))
        if kind == "source_ac":
            q = r * 0.5
            holder.append(
                _el(
                    "path",
                    d=f"M{fmt(cx - q)} 0 C{fmt(cx - q * 0.5)} {fmt(-q * 1.2)} {fmt(cx)} {fmt(-q * 1.2)} {fmt(cx)} 0 "
                    f"S{fmt(cx + q * 0.5)} {fmt(q * 1.2)} {fmt(cx + q)} 0",
                    **dict(paint, stroke=acc),
                )
            )
        elif kind == "source_dc":
            q = r * 0.28
            holder.append(
                _el(
                    "path",
                    d=f"M{fmt(cx - r * 0.55 - q)} 0 H{fmt(cx - r * 0.55 + q)} M{fmt(cx - r * 0.55)} {fmt(-q)} V{fmt(q)} "
                    f"M{fmt(cx + r * 0.55 - q)} 0 H{fmt(cx + r * 0.55 + q)}",
                    **dict(paint, stroke=acc, stroke_width=sw * 0.8),
                )
            )
        else:
            q = r * 0.7071
            holder.append(
                _el(
                    "path",
                    d=f"M{fmt(cx - q)} {fmt(-q)} L{fmt(cx + q)} {fmt(q)} M{fmt(cx + q)} {fmt(-q)} L{fmt(cx - q)} {fmt(q)}",
                    **paint,
                )
            )
        top, bot = -r, r
    elif kind == "battery":
        cx = L / 2
        g = s * 0.3
        xs = [cx - g * 1.5, cx - g * 0.5, cx + g * 0.5, cx + g * 1.5]
        holder.append(_el("path", d=f"M0 0 H{fmt(xs[0])} M{fmt(xs[3])} 0 H{fmt(L)}", data_outline="1", **paint))
        for i, x in enumerate(xs):
            hh = s * (0.55 if i % 2 == 0 else 0.28)
            holder.append(
                _el(
                    "path",
                    d=f"M{fmt(x)} {fmt(-hh)} V{fmt(hh)}",
                    fill="none",
                    stroke=stroke,
                    stroke_width=sw * (1 if i % 2 == 0 else 2.2),
                )
            )
        top, bot = -s * 0.55, s * 0.55
        el, b = _txt(xs[0] - 4, -s * 0.6, "+", font_size * 0.9, fill=stroke, anchor="end")
        holder.append(el)
    elif kind == "diode":
        cx = L / 2
        w = s * 0.8
        holder.append(_el("path", d=f"M0 0 H{fmt(L)}", data_outline="1", **paint))
        holder.append(
            _el(
                "path",
                d=f"M{fmt(cx - w / 2)} {fmt(-w / 2)} L{fmt(cx + w / 2)} 0 L{fmt(cx - w / 2)} {fmt(w / 2)} Z",
                fill=acc if accent else stroke,
                stroke=stroke,
                stroke_width=sw,
                stroke_linejoin="round",
            )
        )
        holder.append(
            _el(
                "path",
                d=f"M{fmt(cx + w / 2)} {fmt(-w / 2)} V{fmt(w / 2)}",
                fill="none",
                stroke=stroke,
                stroke_width=sw * 1.2,
            )
        )
        top, bot = -w / 2, w / 2
    elif kind == "switch":
        holder.append(
            _el("path", d=f"{lead} M{fmt(x0)} 0 L{fmt(x1 - body * 0.05)} {fmt(-s * 0.55)}", data_outline="1", **paint)
        )
        for x in (x0, x1):
            holder.append(_el("circle", cx=x, cy=0, r=sw * 1.4, fill=fill, stroke=stroke, stroke_width=sw * 0.8))
        top = -s * 0.55
    elif kind in _METER_LETTER:
        r = s * 0.82
        cx = L / 2
        holder.append(_el("path", d=f"M0 0 H{fmt(cx - r)} M{fmt(cx + r)} 0 H{fmt(L)}", data_outline="1", **paint))
        holder.append(_el("circle", cx=cx, cy=0, r=r, fill=fill, stroke=stroke, stroke_width=sw))
        if kind == "galvanometer":
            py, R = r * 0.5, r * 1.0  # needle pivot below the centre; scale arc around it
            ticks = []
            for i in range(-3, 4):
                a = math.radians(i * 15)
                ln = 0.2 if i % 3 == 0 else 0.12
                ticks.append(
                    f"M{fmt(cx + R * 0.78 * math.sin(a))} {fmt(py - R * 0.78 * math.cos(a))} "
                    f"L{fmt(cx + R * (0.78 - ln) * math.sin(a))} {fmt(py - R * (0.78 - ln) * math.cos(a))}"
                )
            holder.append(
                _el(
                    "path",
                    d=" ".join(ticks),
                    fill="none",
                    stroke=stroke,
                    stroke_width=sw * 0.55,
                    stroke_linecap="round",
                )
            )
            a = math.radians(max(-1, min(1, deflect)) * 38)
            tx, ty = cx + R * 0.74 * math.sin(a), py - R * 0.74 * math.cos(a)
            holder.append(
                _el(
                    "path",
                    d=f"M{fmt(cx)} {fmt(py)} L{fmt(tx)} {fmt(ty)}",
                    fill="none",
                    stroke=acc if accent else "#C0392B",
                    stroke_width=sw * 0.8,
                    stroke_linecap="round",
                )
            )
            holder.append(_el("circle", cx=cx, cy=py, r=sw * 1.1, fill=stroke))
        else:
            el, _ = _centered_text(cx, 0, _METER_LETTER[kind], r * 1.05, fill=stroke, weight="bold")
            holder.append(el)
        top, bot = -r, r
    elif kind == "rheostat":
        h = s * 0.5
        holder.append(_el("path", d=lead, data_outline="1", **paint))
        holder.append(_el("rect", x=x0, y=-h / 2, width=body, height=h, fill=fill, stroke=stroke, stroke_width=sw))
        wx, wy = x0 + body * 0.62, -h / 2 - s * 0.75
        holder.append(
            _el(
                "path",
                d=f"M{fmt(x0 + body * 0.2)} {fmt(wy)} H{fmt(wx)} V{fmt(-h / 2 - s * 0.22)}",
                fill="none",
                stroke=stroke,
                stroke_width=sw,
                stroke_linejoin="round",
                stroke_linecap="round",
            )
        )
        holder.append(_head(wx, -h / 2 - sw * 0.3, 0, 1, s * 0.32, stroke))
        holder.append(_el("circle", cx=x0 + body * 0.2, cy=wy, r=sw * 1.3, fill=stroke))
        extra["wiper"] = (x0 + body * 0.2, wy)
        top, bot = wy - sw * 1.3, h / 2
    elif kind == "inductor_core":
        k = 4
        r = body / k / 2
        arcs = " ".join(f"A{fmt(r)} {fmt(r)} 0 0 1 {fmt(x0 + 2 * r * (i + 1))} 0" for i in range(k))
        holder.append(_el("path", d=f"{lead} M{fmt(x0)} 0 {arcs}", data_outline="1", **paint))
        cy = -r - s * 0.22
        holder.append(
            _el(
                "path",
                d=f"M{fmt(x0)} {fmt(cy)} H{fmt(x1)} M{fmt(x0)} {fmt(cy - s * 0.18)} H{fmt(x1)}",
                fill="none",
                stroke=stroke,
                stroke_width=sw,
                stroke_linecap="butt",
            )
        )
        top = min(top, cy - s * 0.18 - sw)
    boxes = [Box(-sw / 2, top - sw, L + sw, bot - top + 2 * sw)]
    if name:
        el, b = _txt(L / 2, top - font_size * 0.45, name, font_size, fill=stroke, italic=True)
        holder.append(el)
        boxes.append(b)
    if value:
        el, b = _txt(L / 2, bot + font_size * 1.25, value, font_size * 0.92, fill=_mix(stroke, "#FFFFFF", 0.25))
        holder.append(el)
        boxes.append(b)
    return _finish(holder, None, _union(boxes), a=(0, 0), b=(L, 0), **extra)


@_drawing_api(
    "parts",
    purpose="弹簧（力学图）：两端直引线 + 螺旋线圈（前后圈明暗区分，呈立体感），可选两端挂点。",
    returns="Geometry（端口 a/b 为两端；水平放置）",
    semantics=(
        "length 为总长，coils 为圈数，diameter 为线圈直径；compression 只是视觉参数，不改变 length。",
        'style="rich" 画后半圈浅色、前半圈深色的立体螺旋并加金属高光（局部 SVG）；"flat" 画原生锯齿+后圈细线。',
        "竖直悬挂用 d.place 后 set_transform(rotation=90)。",
    ),
    example='d.place(spring(200, coils=8, diameter=24), at=(400, 260), key="k")',
    rank=18,
)
def spring(length, *, coils=8, diameter=22, stroke="#4A5563", stroke_width=1.8, lead=None, hooks=True, style="rich"):
    _finite(length, diameter)
    rich = _style(style)
    coils = max(2, int(coils))
    lead = lead if lead is not None else min(length * 0.12, 24)
    body = length - 2 * lead
    R = diameter / 2
    pitch = body / coils
    holder, defs = _start(rich)
    holder.append(
        _el(
            "path",
            d=f"M0 0 H{fmt(lead)} M{fmt(length - lead)} 0 H{fmt(length)}",
            fill="none",
            stroke=stroke,
            stroke_width=stroke_width,
            stroke_linecap="round",
            data_outline="1",
        )
    )
    # helix projected: x = lead + pitch*(u + .5 sin...) — use cycloid-like projection for depth
    tilt = pitch * 0.35
    back, front = [], []
    for c in range(coils):
        xa = lead + c * pitch
        # front stroke: top → bottom going forward; back stroke: bottom → top
        front.append(
            f"M{fmt(xa)} {fmt(-R if c else 0)} C{fmt(xa + tilt)} {fmt(-R * 0.2)} {fmt(xa + pitch * 0.5 - tilt * 0.3)} {fmt(R)} {fmt(xa + pitch * 0.5)} {fmt(R)}"
        )
        back.append(
            f"M{fmt(xa + pitch * 0.5)} {fmt(R)} C{fmt(xa + pitch * 0.5 + tilt * 0.3)} {fmt(R)} {fmt(xa + pitch - tilt)} {fmt(-R * 0.2)} "
            f"{fmt(xa + pitch)} {fmt(-R if c < coils - 1 else 0)}"
        )
    if c == coils - 1:
        pass
    holder.append(
        _el(
            "path",
            d=" ".join(back),
            fill="none",
            stroke=_mix(stroke, "#FFFFFF", 0.45),
            stroke_width=stroke_width * 0.85,
            stroke_linecap="round",
        )
    )
    holder.append(
        _el(
            "path",
            d=" ".join(front),
            fill="none",
            stroke=stroke,
            stroke_width=stroke_width * 1.15,
            stroke_linecap="round",
        )
    )
    if rich:
        look = _look()
        look.append(
            _el(
                "path",
                d=" ".join(front),
                fill="none",
                stroke="#FFFFFF",
                stroke_width=stroke_width * 0.35,
                stroke_opacity=0.6,
                stroke_linecap="round",
                transform=f"translate({fmt(-stroke_width * 0.25)} {fmt(-stroke_width * 0.3)})",
            )
        )
        holder.append(look)
    boxes = [Box(-stroke_width, -R - stroke_width, length + 2 * stroke_width, 2 * R + 2 * stroke_width)]
    if hooks:
        for x in (0, length):
            holder.append(
                _el(
                    "circle",
                    cx=x,
                    cy=0,
                    r=stroke_width * 1.5,
                    fill="#FFFFFF",
                    stroke=stroke,
                    stroke_width=stroke_width * 0.8,
                )
            )
    return _finish(holder, defs, _union(boxes), a=(0, 0), b=(length, 0))


@_drawing_api(
    "parts",
    purpose="磁铁：条形磁铁（N 红 / S 蓝两色 + 原生 N/S 字母）或 U 形磁铁，可选外部磁感线。",
    returns="Geometry（端口 north/south 为两极端面中心，四边/center）",
    semantics=(
        'kind="bar" 水平条形（N 在右）；"horseshoe" U 形（两极朝下，N 在左）；width/height 为外形尺寸。',
        "north/south 为两极颜色；field_lines=True 画条形磁铁外部从 N 到 S 的磁感线（带方向箭头，原生路径）——电磁感应/磁场示意图一律开 field_lines=True，否则看不出磁场；插入线圈见 coil。",
        'style="rich" 加金属立体渐变与高光（局部 SVG），"flat" 纯色。',
    ),
    example='d.place(magnet(160, 44, field_lines=True), at=(480, 270), key="mag")',
    rank=19,
)
def magnet(
    width=150,
    height=42,
    *,
    kind="bar",
    north="#D64541",
    south="#3C6EB4",
    field_lines=False,
    font_size=None,
    style="rich",
    line="#8A94A3",
):
    _finite(width, height)
    if kind not in ("bar", "horseshoe"):
        raise ValueError("magnet kind must be bar or horseshoe")
    rich = _style(style)
    holder, defs = _start(rich)
    fs = font_size or min(height * 0.55, 26)
    ports = {}
    boxes = []
    if kind == "bar":
        w, h = width, height
        r = min(4, h * 0.1)
        holder.append(
            _el(
                "path",
                d=_rrect(0, 0, w, h, r),
                fill=south,
                stroke=_mix(south, "#000000", 0.35),
                stroke_width=1.2,
                data_outline="1",
            )
        )
        holder.append(
            _el(
                "path",
                d=f"M{fmt(w / 2)} 0 H{fmt(w - r)} A{fmt(r)} {fmt(r)} 0 0 1 {fmt(w)} {fmt(r)} V{fmt(h - r)} "
                f"A{fmt(r)} {fmt(r)} 0 0 1 {fmt(w - r)} {fmt(h)} H{fmt(w / 2)} Z",
                fill=north,
                stroke=_mix(north, "#000000", 0.35),
                stroke_width=1.2,
            )
        )
        if rich:
            defs.append(
                _linear(
                    "metal",
                    [(0, "#FFFFFF", 0.45), (0.3, "#FFFFFF", 0.08), (0.75, "#000000", 0.1), (1, "#000000", 0.28)],
                )
            )
            look = _look()
            look.append(_el("path", d=_rrect(0, 0, w, h, r), fill="url(#metal)"))
            look.append(
                _el(
                    "path",
                    d=f"M{fmt(r * 2)} {fmt(h * 0.16)} H{fmt(w - r * 2)}",
                    stroke="#FFFFFF",
                    stroke_width=max(1, h * 0.05),
                    stroke_opacity=0.55,
                    stroke_linecap="round",
                    fill="none",
                )
            )
            holder.append(look)
        for x, t in ((w * 0.25, "S"), (w * 0.75, "N")):
            el, _ = _centered_text(x, h / 2, t, fs, fill="#FFFFFF", weight="bold")
            holder.append(el)
        boxes.append(Box(-0.6, -0.6, w + 1.2, h + 1.2))
        ports.update(north=(w, h / 2), south=(0, h / 2))
        if field_lines:
            lc = line
            paths = []
            for k, lift in enumerate((0.3, 0.65, 1.05)):
                dy = h * lift + h * 0.1
                y0 = h / 2 - h * (0.12 + k * 0.1)
                for sign in (-1, 1):
                    ya = h / 2 + sign * (h / 2 - y0)
                    ext = h * (0.3 + k * 0.28)
                    ypk = h / 2 + sign * (h / 2 + dy)
                    paths.append(
                        f"M{fmt(w)} {fmt(ya)} C{fmt(w + ext)} {fmt(ya + sign * ext * 0.25)} {fmt(w + ext * 0.55)} {fmt(ypk)} {fmt(w / 2)} {fmt(ypk)} "
                        f"C{fmt(-ext * 0.55)} {fmt(ypk)} {fmt(-ext)} {fmt(ya + sign * ext * 0.25)} 0 {fmt(ya)}"
                    )
                    holder.append(_head(w / 2 - 7, ypk, -1, 0, 7, lc))
                    boxes.append(Box(-ext * 0.78, min(ya, ypk), w + ext * 1.56, abs(ypk - ya)))
            paths.append(f"M{fmt(w)} {fmt(h / 2)} H{fmt(w + h * 0.9)} M{fmt(-h * 0.9)} {fmt(h / 2)} H0")
            holder.append(_head(-h * 0.9 + 6, h / 2, 1, 0, 6, lc))
            holder.append(_head(w + h * 0.9, h / 2, 1, 0, 6, lc))
            boxes.append(Box(-h * 0.9, h / 2 - 3, w + h * 1.8, 6))
            holder.insert(1, _el("path", d=" ".join(paths), fill="none", stroke=lc, stroke_width=1.1))
    else:
        w, h = width, height * 2.4 if height < width * 0.5 else height
        arm = w * 0.3
        R = w / 2
        Ri = R - arm
        outline = (
            f"M0 {fmt(h)} V{fmt(R)} A{fmt(R)} {fmt(R)} 0 0 1 {fmt(w)} {fmt(R)} V{fmt(h)} H{fmt(w - arm)} V{fmt(R)} "
            f"A{fmt(Ri)} {fmt(Ri)} 0 0 0 {fmt(arm)} {fmt(R)} V{fmt(h)} Z"
        )
        holder.append(
            _el(
                "path",
                d=outline,
                fill=_mix("#9AA3AE", "#FFFFFF", 0.2),
                stroke="#5E6773",
                stroke_width=1.2,
                stroke_linejoin="round",
                data_outline="1",
            )
        )
        tip = min(h - R, arm * 1.3)
        holder.append(
            _el(
                "rect",
                x=0,
                y=h - tip,
                width=arm,
                height=tip,
                fill=north,
                stroke=_mix(north, "#000000", 0.35),
                stroke_width=1.2,
            )
        )
        holder.append(
            _el(
                "rect",
                x=w - arm,
                y=h - tip,
                width=arm,
                height=tip,
                fill=south,
                stroke=_mix(south, "#000000", 0.35),
                stroke_width=1.2,
            )
        )
        if rich:
            defs.append(
                _linear(
                    "metal",
                    [(0, "#FFFFFF", 0.45), (0.35, "#FFFFFF", 0.05), (0.7, "#000000", 0.1), (1, "#000000", 0.3)],
                    x2=1,
                    y2=0,
                )
            )
            look = _look()
            look.append(_el("path", d=outline, fill="url(#metal)"))
            holder.append(look)
        fs = font_size or min(arm * 0.6, 24)
        for x, t in ((arm / 2, "N"), (w - arm / 2, "S")):
            el, _ = _centered_text(x, h - tip / 2, t, fs, fill="#FFFFFF", weight="bold")
            holder.append(el)
        boxes.append(Box(-0.6, -0.6, w + 1.2, h + 1.2))
        ports.update(north=(arm / 2, h), south=(w - arm / 2, h))
    return _finish(holder, defs, _union(boxes), **ports)


@_drawing_api(
    "parts",
    purpose="图例条：一行“符号 + 说明”，说明示意图中的线型/端点/颜色含义。",
    returns="Geometry",
    semantics=("items 为 [(kind, 文字, 颜色)]；kind 为 arrow/inhibit/dashed/line/dot/box/ring。放在图的角落。",),
    example='d.place(legend_row([("arrow", "激活", "#2A6F4E"), ("inhibit", "抑制", "#C0392B"), ("dashed", "间接", "#7A7A7A")]), at=(40, 380), anchor="left", key="lg")',
    rank=12,
)
def legend_row(items, *, font_size=12, gap=22, text_fill="#33404F"):
    holder, x, h = _el("g"), 0.0, font_size * 1.3
    cy = h / 2
    boxes = [Box(0, 0, 1, h)]
    for kind, text, color in items:
        if kind in ("arrow", "inhibit", "dashed", "line"):
            holder.append(
                _el(
                    "path",
                    d=f"M{fmt(x)} {fmt(cy)} H{fmt(x + (21 if kind == 'arrow' else 26))}",
                    stroke=color,
                    stroke_width=2,
                    fill="none",
                    stroke_linecap="round" if kind != "dashed" else "butt",
                    stroke_dasharray="5 3.5" if kind == "dashed" else None,
                )
            )
            if kind == "arrow":
                holder.append(_head(x + 27, cy, 1, 0, 8, color))
            elif kind == "inhibit":
                holder.append(_el("rect", x=x + 25, y=cy - 6, width=3, height=12, rx=1, fill=color))
            x += 33
        elif kind == "dot":
            holder.append(
                _el("circle", cx=x + 6, cy=cy, r=5.5, fill=color, stroke=_mix(color, "#000000", 0.3), stroke_width=0.8)
            )
            x += 17
        elif kind == "ring":
            holder.append(_el("circle", cx=x + 6, cy=cy, r=5, fill="#FFFFFF", stroke=color, stroke_width=2))
            x += 17
        else:
            holder.append(
                _el(
                    "rect",
                    x=x,
                    y=cy - 6,
                    width=12,
                    height=12,
                    rx=2.5,
                    fill=color,
                    stroke=_mix(color, "#000000", 0.3),
                    stroke_width=0.8,
                )
            )
            x += 18
        el, b = _txt(x, cy + font_size * 0.36, text, font_size, fill=text_fill, anchor="start")
        holder.append(el)
        boxes.append(b)
        x = b.x + b.width + gap
    boxes.append(Box(0, 0, max(1.0, x - gap), h))
    return _finish(holder, None, _union(boxes))


_DEVICES = ("phone", "laptop", "server", "database", "cloud", "hospital", "edge", "camera", "gpu")


def _lock_badge(cx, cy, s, color):
    """Small padlock (shackle + body + keyhole) — encrypted / private marker."""
    sw = max(0.9, s * 0.12)
    return [
        _el(
            "path",
            d=f"M{fmt(cx - s * 0.28)} {fmt(cy - s * 0.05)} V{fmt(cy - s * 0.28)} "
            f"A{fmt(s * 0.28)} {fmt(s * 0.28)} 0 0 1 {fmt(cx + s * 0.28)} {fmt(cy - s * 0.28)} V{fmt(cy - s * 0.05)}",
            fill="none",
            stroke=color,
            stroke_width=sw,
        ),
        _el("path", d=_rrect(cx - s * 0.45, cy - s * 0.08, s * 0.9, s * 0.62, s * 0.1), fill=color, stroke="none"),
        _el(
            "path",
            d=f"M{fmt(cx)} {fmt(cy + s * 0.1)} V{fmt(cy + s * 0.3)}",
            stroke="#FFFFFF",
            stroke_width=sw * 1.1,
            stroke_linecap="round",
        ),
    ]


@_drawing_api(
    "parts",
    purpose="系统图图标（NeurIPS/CCS 论文风格扁平线描）：手机、笔记本、服务器机柜、数据库、云、医院、边缘节点、摄像头、GPU 卡；统一线宽 + 浅色底。",
    returns="Geometry（原点在中心；端口 top/bottom/left/right/center，以及 screen（屏幕中心，phone/laptop/camera）、badge（右上角徽标位））",
    semantics=(
        'kind 取 "phone"/"laptop"/"server"/"database"/"cloud"/"hospital"/"edge"/"camera"/"gpu"；size 为图标高度 px（laptop/gpu/cloud 宽于高）。',
        "color 为线色（默认深蓝灰），fill 为浅色底（默认由 color 推导）；同一张图的所有图标共用一套 color 即风格统一。",
        "lock=True 在右上角画小锁（加密/隐私），name 在图标下方写短标签；联邦学习/隐私计算/边云协同系统图用多个 device + d.arrow 连接。",
        'style="rich" 加轻微顶光与阴影（一个局部 SVG），"flat" 全原生。',
    ),
    example='c = d.place(device("phone", 60, name="Client 1"), at=(120, 260), key="c1")\n'
    's = d.place(device("server", 80, name="Server", lock=True), at=(420, 120), key="srv")\nd.arrow(c, s)',
    rank=11,
)
def device(
    kind="server",
    size=64,
    *,
    color="#3E5A7A",
    fill=None,
    accent="#4A90D9",
    lock=False,
    name=None,
    font_size=12,
    style="rich",
):
    rich = _style(style)
    if kind not in _DEVICES:
        raise ValueError(f"kind must be one of {_DEVICES}")
    _finite(size)
    h = float(size)
    sw = max(1.2, h * 0.035)
    fill = fill or _mix(color, "#FFFFFF", 0.88)
    light = _mix(color, "#FFFFFF", 0.7)
    holder, defs = _start(rich)
    els, ports = [], {}
    line = dict(fill="none", stroke=color, stroke_width=sw, stroke_linecap="round", stroke_linejoin="round")
    if kind == "phone":
        w = h * 0.52
        x0, y0 = -w / 2, -h / 2
        els.append(_el("path", d=_rrect(x0, y0, w, h, w * 0.16), fill=fill, stroke=color, stroke_width=sw))
        els.append(
            _el(
                "path",
                d=_rrect(x0 + w * 0.1, y0 + h * 0.1, w * 0.8, h * 0.76, w * 0.05),
                fill=_mix(accent, "#FFFFFF", 0.78),
                stroke="none",
            )
        )
        els.append(_el("path", d=f"M{fmt(-w * 0.14)} {fmt(y0 + h * 0.055)} H{fmt(w * 0.14)}", **line))
        els.append(_el("circle", cx=0, cy=y0 + h * 0.93, r=h * 0.028, fill=color))
        rows = " ".join(
            f"M{fmt(x0 + w * 0.2)} {fmt(y0 + h * (0.22 + 0.12 * j))} H{fmt(x0 + w * (0.8 - 0.15 * (j % 2)))}"
            for j in range(4)
        )
        els.append(
            _el(
                "path",
                d=rows,
                fill="none",
                stroke=_mix(accent, "#FFFFFF", 0.3),
                stroke_width=sw * 0.8,
                stroke_linecap="round",
            )
        )
        ports["screen"] = (0, y0 + h * 0.48)
        box = Box(x0, y0, w, h)
    elif kind == "laptop":
        w = h * 1.5
        sh = h * 0.72
        els.append(
            _el("path", d=_rrect(-w * 0.4, -h / 2, w * 0.8, sh, h * 0.06), fill=fill, stroke=color, stroke_width=sw)
        )
        els.append(
            _el(
                "path",
                d=_rrect(-w * 0.34, -h / 2 + h * 0.08, w * 0.68, sh - h * 0.16, h * 0.02),
                fill=_mix(accent, "#FFFFFF", 0.78),
                stroke="none",
            )
        )
        bars = " ".join(
            f"M{fmt(-w * 0.26 + j * w * 0.1)} {fmt(-h / 2 + sh - h * 0.14)} V{fmt(-h / 2 + sh - h * (0.22 + 0.1 * ((j * 7) % 3)))}"
            for j in range(6)
        )
        els.append(_el("path", d=bars, fill="none", stroke=accent, stroke_width=sw * 1.6, stroke_linecap="butt"))
        yb = -h / 2 + sh
        els.append(
            _el(
                "path",
                d=f"M{fmt(-w * 0.4)} {fmt(yb)} L{fmt(-w / 2)} {fmt(h / 2 - h * 0.06)} Q{fmt(-w / 2)} {fmt(h / 2)} {fmt(-w * 0.46)} {fmt(h / 2)} "
                f"H{fmt(w * 0.46)} Q{fmt(w / 2)} {fmt(h / 2)} {fmt(w / 2)} {fmt(h / 2 - h * 0.06)} L{fmt(w * 0.4)} {fmt(yb)} Z",
                fill=light,
                stroke=color,
                stroke_width=sw,
                stroke_linejoin="round",
            )
        )
        els.append(_el("path", d=f"M{fmt(-w * 0.08)} {fmt(h / 2 - h * 0.1)} H{fmt(w * 0.08)}", **line))
        ports["screen"] = (0, -h / 2 + sh / 2)
        box = Box(-w / 2, -h / 2, w, h)
    elif kind in ("server", "edge"):
        w = h * (0.7 if kind == "server" else 0.9)
        n = 3 if kind == "server" else 1
        uh = h / n if kind == "server" else h * 0.5
        y0 = -h / 2 if kind == "server" else -uh / 2 - h * 0.1
        for j in range(n):
            y = y0 + j * uh
            els.append(
                _el(
                    "path",
                    d=_rrect(-w / 2, y + sw * 0.4, w, uh - sw * 0.8, h * 0.05),
                    fill=fill,
                    stroke=color,
                    stroke_width=sw,
                )
            )
            els.append(_el("circle", cx=-w * 0.32, cy=y + uh / 2, r=h * 0.032, fill="#4CB050"))
            els.append(_el("circle", cx=-w * 0.2, cy=y + uh / 2, r=h * 0.032, fill=accent))
            vents = " ".join(
                f"M{fmt(w * (0.0 + 0.08 * i))} {fmt(y + uh * 0.32)} V{fmt(y + uh * 0.68)}" for i in range(5)
            )
            els.append(_el("path", d=vents, fill="none", stroke=light, stroke_width=sw * 0.9, stroke_linecap="round"))
        if kind == "edge":  # gateway box with antennas and signal arcs
            yt = y0
            els.append(
                _el(
                    "path",
                    d=f"M{fmt(-w * 0.3)} {fmt(yt)} V{fmt(yt - h * 0.3)} M{fmt(w * 0.3)} {fmt(yt)} V{fmt(yt - h * 0.3)}",
                    **line,
                )
            )
            arcs = " ".join(
                f"M{fmt(sx * w * 0.3 - r)} {fmt(yt - h * 0.36 + r * 0.3)} A{fmt(r)} {fmt(r)} 0 0 1 {fmt(sx * w * 0.3 + r)} {fmt(yt - h * 0.36 + r * 0.3)}"
                for sx in (-1, 1)
                for r in (h * 0.08, h * 0.15)
            )
            els.append(_el("path", d=arcs, fill="none", stroke=accent, stroke_width=sw * 0.8, stroke_linecap="round"))
            els.append(
                _el(
                    "path",
                    d=f"M{fmt(-w * 0.35)} {fmt(y0 + uh)} V{fmt(h / 2)} M{fmt(w * 0.35)} {fmt(y0 + uh)} V{fmt(h / 2)}",
                    **line,
                )
            )
        box = Box(-w / 2 - sw / 2, -h / 2 - sw / 2, w + sw, h + sw)
    elif kind == "database":
        w = h * 0.8
        cap = h * 0.13
        x0, y0 = -w / 2, -h / 2
        body = (
            f"M{fmt(x0)} {fmt(y0 + cap)} V{fmt(h / 2 - cap)} A{fmt(w / 2)} {fmt(cap)} 0 0 0 {fmt(-x0)} {fmt(h / 2 - cap)} "
            f"V{fmt(y0 + cap)} A{fmt(w / 2)} {fmt(cap)} 0 0 0 {fmt(x0)} {fmt(y0 + cap)} Z"
        )
        els.append(_el("path", d=body, fill=fill, stroke=color, stroke_width=sw, stroke_linejoin="round"))
        els.append(_el("ellipse", cx=0, cy=y0 + cap, rx=w / 2, ry=cap, fill=light, stroke=color, stroke_width=sw))
        bands = " ".join(
            f"M{fmt(x0)} {fmt(y)} A{fmt(w / 2)} {fmt(cap)} 0 0 0 {fmt(-x0)} {fmt(y)}"
            for y in (y0 + cap + h * 0.27, y0 + cap + h * 0.52)
        )
        els.append(_el("path", d=bands, **line))
        box = Box(x0 - sw / 2, y0 - sw / 2, w + sw, h + sw)
    elif kind == "cloud":
        w = h * 1.55
        lobes = [
            (-w * 0.28, h * 0.1, h * 0.28),
            (-w * 0.05, -h * 0.12, h * 0.36),
            (w * 0.22, -h * 0.02, h * 0.3),
            (w * 0.34, h * 0.16, h * 0.2),
            (0, h * 0.2, h * 0.26),
        ]
        from ._bio_parts import _circle_union

        outline = _circle_union([((x, y), r) for x, y, r in lobes])
        els.append(_el("path", d=outline, fill=fill, stroke=color, stroke_width=sw, stroke_linejoin="round"))
        xs = [x for x, _, r in lobes for x in (x - r, x + r)]
        ys = [y for _, y, r in lobes for y in (y - r, y + r)]
        box = Box(min(xs) - sw, min(ys) - sw, max(xs) - min(xs) + 2 * sw, max(ys) - min(ys) + 2 * sw)
    elif kind == "hospital":
        w = h * 1.1
        els.append(
            _el(
                "path",
                d=f"M{fmt(-w / 2)} {fmt(h / 2)} V{fmt(-h * 0.12)} H{fmt(-w * 0.22)} V{fmt(-h / 2)} H{fmt(w * 0.22)} V{fmt(-h * 0.12)} "
                f"H{fmt(w / 2)} V{fmt(h / 2)} Z",
                fill=fill,
                stroke=color,
                stroke_width=sw,
                stroke_linejoin="round",
            )
        )
        c, t = h * 0.13, h * 0.045
        els.append(
            _el(
                "path",
                d=f"M{fmt(-t)} {fmt(-h * 0.32 - c)} H{fmt(t)} V{fmt(-h * 0.32 - t)} H{fmt(c)} V{fmt(-h * 0.32 + t)} H{fmt(t)} "
                f"V{fmt(-h * 0.32 + c)} H{fmt(-t)} V{fmt(-h * 0.32 + t)} H{fmt(-c)} V{fmt(-h * 0.32 - t)} H{fmt(-t)} Z",
                fill="#D64541",
                stroke="none",
            )
        )
        win = " ".join(
            _rrect(x, y, h * 0.1, h * 0.1, h * 0.015)
            for x in (-w * 0.4, -w * 0.25, w * 0.15, w * 0.3)
            for y in (0, h * 0.18)
        )
        els.append(_el("path", d=win, fill=_mix(accent, "#FFFFFF", 0.6), stroke=color, stroke_width=sw * 0.6))
        els.append(
            _el(
                "path",
                d=_rrect(-h * 0.09, h * 0.22, h * 0.18, h * 0.28, h * 0.02),
                fill=light,
                stroke=color,
                stroke_width=sw * 0.8,
            )
        )
        box = Box(-w / 2 - sw / 2, -h / 2 - sw / 2, w + sw, h + sw)
    elif kind == "camera":
        w = h * 1.25
        els.append(
            _el("path", d=_rrect(-w / 2, -h * 0.3, w, h * 0.72, h * 0.1), fill=fill, stroke=color, stroke_width=sw)
        )
        els.append(
            _el(
                "path",
                d=f"M{fmt(-w * 0.2)} {fmt(-h * 0.3)} L{fmt(-w * 0.12)} {fmt(-h / 2 + sw)} H{fmt(w * 0.12)} L{fmt(w * 0.2)} {fmt(-h * 0.3)}",
                fill=light,
                stroke=color,
                stroke_width=sw,
                stroke_linejoin="round",
            )
        )
        els.append(_el("circle", cx=0, cy=h * 0.06, r=h * 0.24, fill=light, stroke=color, stroke_width=sw))
        els.append(
            _el(
                "circle",
                cx=0,
                cy=h * 0.06,
                r=h * 0.14,
                fill=_mix(accent, "#1E2A3A", 0.4),
                stroke=color,
                stroke_width=sw * 0.6,
            )
        )
        els.append(_el("circle", cx=-h * 0.05, cy=h * 0.01, r=h * 0.04, fill="#FFFFFF", fill_opacity=0.8))
        els.append(_el("circle", cx=w * 0.36, cy=-h * 0.18, r=h * 0.04, fill="#D64541"))
        ports["screen"] = (0, h * 0.06)
        box = Box(-w / 2 - sw / 2, -h / 2, w + sw, h * 0.92 + sw)
    else:  # gpu card: PCB, two fans, gold edge fingers
        w = h * 1.8
        bh = h * 0.78
        els.append(_el("path", d=_rrect(-w / 2, -h / 2, w, bh, h * 0.06), fill=fill, stroke=color, stroke_width=sw))
        for cx in (-w * 0.22, w * 0.2):
            r = bh * 0.36
            els.append(_el("circle", cx=cx, cy=-h / 2 + bh / 2, r=r, fill=light, stroke=color, stroke_width=sw))
            blades = " ".join(
                f"M{fmt(cx)} {fmt(-h / 2 + bh / 2)} Q{fmt(cx + r * 0.9 * math.cos(a + 0.6))} {fmt(-h / 2 + bh / 2 + r * 0.9 * math.sin(a + 0.6))} "
                f"{fmt(cx + r * 0.85 * math.cos(a))} {fmt(-h / 2 + bh / 2 + r * 0.85 * math.sin(a))}"
                for a in (math.pi * 2 * j / 7 for j in range(7))
            )
            els.append(_el("path", d=blades, fill="none", stroke=color, stroke_width=sw * 0.6))
            els.append(_el("circle", cx=cx, cy=-h / 2 + bh / 2, r=r * 0.22, fill=color))
        fing = " ".join(f"M{fmt(-w * 0.3 + j * w * 0.045)} {fmt(-h / 2 + bh)} V{fmt(h / 2)}" for j in range(10))
        els.append(_el("path", d=fing, fill="none", stroke="#C9A227", stroke_width=w * 0.025))
        els.append(
            _el(
                "path",
                d=f"M{fmt(w * 0.44)} {fmt(-h / 2)} V{fmt(h / 2)}",
                stroke=color,
                stroke_width=sw * 1.5,
                fill="none",
            )
        )
        box = Box(-w / 2 - sw / 2, -h / 2 - sw / 2, w + sw, h + sw)
    els[0].set("data-outline", "1")
    holder.extend(els[:1])
    if rich:
        look = _look()
        defs.append(_linear("devhi", [(0, "#FFFFFF", 0.7), (0.6, "#FFFFFF", 0.0)]))
        look.append(_el("path", d=els[0].get("d") or "", fill="url(#devhi)"))
        holder.append(look)
    holder.extend(els[1:])
    boxes = [box]
    bx, by = box.x + box.width - h * 0.06, box.y + h * 0.08
    ports["badge"] = (bx, by)
    if lock:
        holder.extend(_lock_badge(bx, by, h * 0.32, "#D08A1F"))
        boxes.append(Box(bx - h * 0.16, by - h * 0.2, h * 0.32, h * 0.38))
    if name:
        t, b = _txt(0, box.y + box.height + font_size * 1.15, name, font_size, fill=_INK)
        holder.append(t)
        boxes.append(b)
    return _finish(holder, defs, _union(boxes), **ports)


def _grid_tex(kind, i, n, u, rnd, color):
    """Pixel grid (u×u values in 0..1) for thumbnail i of n."""
    t = i / max(n - 1, 1)
    vals = []
    for y in range(u):
        row = []
        for x in range(u):
            cx, cy = (x + 0.5) / u - 0.5, (y + 0.5) / u - 0.5
            if kind == "samples":  # distinct clean glyphs (MNIST/CIFAR-like stand-ins)
                g = lambda d, w=0.005: math.exp(-d * d / w)
                r = math.hypot(cx, cy)
                v = [
                    g(r - 0.27),
                    g(cx) * (abs(cy) < 0.34),
                    max(g(cx - cy), g(cx + cy)) * (abs(cx) < 0.3),
                    g(abs(cx) + abs(cy) - 0.3),
                    max(g(cx) * (abs(cy) < 0.3), g(cy) * (abs(cx) < 0.3)),
                    max(g(cy - 0.25) * (abs(cx) < 0.28), g(cx + 0.25) * (abs(cy) < 0.3)),
                    max(g(max(abs(cx), abs(cy)) - 0.28), 0.0),
                    g(cy + 0.28 - 1.1 * abs(cx)) * (cy < 0.3) + g(cy - 0.28) * (abs(cx) < 0.3),
                ][i % 8]
            else:
                base = math.exp(-((math.hypot(cx, cy * 1.15) - 0.26) ** 2) / 0.005) + 0.6 * math.exp(
                    -(cx**2 + (cy + 0.02) ** 2) / 0.004
                )
                noise = rnd.random()
                a = t if kind == "recon" else 1 - t  # recon: noise → clean; noise: clean → noise (forward diffusion)
                v = a * min(1, base) + (1 - a) * noise
            row.append(max(0.0, min(1.0, v)))
        vals.append(row)
    return vals


@_drawing_api(
    "parts",
    purpose="图像缩略图条/网格（梯度反演重建、扩散去噪/加噪、数据增强、生成样本）：一排小方格图像，程序化纹理从噪声渐变到清晰形状。",
    returns="Geometry（原点在中心；端口 img{k} 第 k 张中心、img{k}_top/img{k}_bottom，first/last）",
    semantics=(
        'n 为张数；kind="recon"（左噪声 → 右清晰，重建/去噪过程）、"noise"（左清晰 → 右噪声，前向加噪/扩散）、"samples"（n 张不同的清晰样本）。',
        'cell 为每张边长 px，gap 为间距，cols 给定时排成网格；res 为每张像素分辨率（默认 16）；color 为图像主色（灰度图用 "#202020"）。',
        'arrows=True 在相邻图之间画细箭头（过程感）；captions=["t=T", ..., "t=0"] 在每张下方写小字；style="rich" 加细边框阴影，"flat" 全原生。',
    ),
    example='g = d.place(image_grid(5, kind="recon", captions=["iter 0", "", "", "", "iter 300"]), at=(420, 200), key="recon")',
    rank=12,
)
def image_grid(
    n=5,
    *,
    kind="recon",
    cell=44,
    gap=10,
    cols=None,
    res=16,
    color="#2C4A6E",
    arrows=False,
    captions=None,
    font_size=11,
    style="rich",
    seed=3,
):
    rich = _style(style)
    if kind not in ("recon", "noise", "samples"):
        raise ValueError('kind must be "recon", "noise" or "samples"')
    _finite(cell, gap)
    import random

    rnd = random.Random(seed)
    cols = cols or n
    gap = gap + (cell * 0.35 if arrows else 0)
    holder, defs = _start(rich)
    boxes, ports = [], {}
    u = max(3, int(res))
    px = cell / u
    bg = "#F4F6F9"
    first = True
    for i in range(n):
        x0, y0 = (i % cols) * (cell + gap), (i // cols) * (cell + gap + (font_size * 1.4 if captions else 0))
        frame = _el(
            "rect", x=x0, y=y0, width=cell, height=cell, fill=bg, stroke=_mix(color, "#FFFFFF", 0.3), stroke_width=1
        )
        if first:
            frame.set("data-outline", "1")
            first = False
        holder.append(frame)
        vals = _grid_tex(kind, i, n, u, rnd, color)
        levels = {}
        for yy, row in enumerate(vals):
            for xx, v in enumerate(row):
                q = round(v * 7)
                if q:
                    levels.setdefault(q, []).append(
                        f"M{fmt(x0 + xx * px)} {fmt(y0 + yy * px)} h{fmt(px)} v{fmt(px)} h{fmt(-px)} Z"
                    )
        for q, cells in sorted(levels.items()):
            holder.append(_el("path", d=" ".join(cells), fill=_mix(bg, color, q / 7), stroke="none"))
        holder.append(
            _el(
                "rect",
                x=x0,
                y=y0,
                width=cell,
                height=cell,
                fill="none",
                stroke=_mix(color, "#FFFFFF", 0.2),
                stroke_width=1,
            )
        )
        ports[f"img{i}"] = (x0 + cell / 2, y0 + cell / 2)
        ports[f"img{i}_top"] = (x0 + cell / 2, y0)
        ports[f"img{i}_bottom"] = (x0 + cell / 2, y0 + cell)
        boxes.append(Box(x0, y0, cell, cell))
        if arrows and i < n - 1 and (i + 1) % cols:
            ax0, ax1, ay = x0 + cell + gap * 0.2, x0 + cell + gap * 0.8, y0 + cell / 2
            holder.append(
                _el("path", d=f"M{fmt(ax0)} {fmt(ay)} H{fmt(ax1 - 4)}", stroke="#6B7785", stroke_width=1.3, fill="none")
            )
            holder.append(_head(ax1, ay, 1, 0, 6, "#6B7785"))
        if captions and i < len(captions) and captions[i]:
            t, b = _txt(x0 + cell / 2, y0 + cell + font_size * 1.2, captions[i], font_size, fill="#4A5563")
            holder.append(t)
            boxes.append(b)
    if rich:
        look = _look()
        for i in range(n):
            x0, y0 = (i % cols) * (cell + gap), (i // cols) * (cell + gap + (font_size * 1.4 if captions else 0))
            look.append(
                _el(
                    "path",
                    d=f"M{fmt(x0 + 2)} {fmt(y0 + cell + 1.5)} H{fmt(x0 + cell + 1.5)} V{fmt(y0 + 2)}",
                    fill="none",
                    stroke="#000000",
                    stroke_opacity=0.15,
                    stroke_width=2,
                )
            )
        holder.append(look)
    ports["first"], ports["last"] = ports["img0"], ports[f"img{n - 1}"]
    return _finish(holder, defs, _union(boxes), **ports)


@_drawing_api(
    "parts",
    purpose="参数/梯度向量（联邦学习、模型更新、嵌入向量）：一排彩色小格（数值热度色），可加密（锁标 + 密文斜纹）、可加噪（差分隐私）。",
    returns="Geometry（原点在中心；端口 first/last/center、cell{k} 第 k 格中心、badge 锁标位、label 标签位）",
    semantics=(
        "n 为格数（默认 8）；values 为每格数值（-1..1，正值暖色、负值冷色），省略时按 seed 生成确定性的随机值；vertical=True 竖排。",
        'encrypted=True 格子变为密文灰底 + 斜纹并在末端画小锁；noise=True 每格加小噪点（DP 噪声）；name 写在向量左侧（如 "Δw₁"、"∇L"）。',
        'cell 为格边长 px；style="rich" 加轻微光泽（一个局部 SVG），"flat" 全原生。',
    ),
    example='v = d.place(vector_packet(8, name="Δw₁", encrypted=True), at=(300, 200), key="dw1")',
    rank=13,
)
def vector_packet(
    n=8,
    *,
    values=None,
    cell=14,
    vertical=False,
    encrypted=False,
    noise=False,
    name=None,
    font_size=12,
    pos="#D9653B",
    neg="#3B78B5",
    style="rich",
    seed=2,
):
    rich = _style(style)
    _finite(cell)
    import random

    rnd = random.Random(seed)
    values = list(values) if values is not None else [rnd.uniform(-1, 1) for _ in range(n)]
    n = len(values)
    holder, defs = _start(rich)
    ports, boxes = {}, []
    if name and not vertical:
        t, b = _txt(-6, cell / 2 + font_size * 0.36, name, font_size, anchor="end", italic=True)
        holder.append(t)
        boxes.append(b)
        ports["label"] = (b.x + b.width / 2, cell / 2)
    W, H = (cell, cell * n) if vertical else (cell * n, cell)
    holder.append(
        _el("rect", x=0, y=0, width=W, height=H, fill="#FFFFFF", stroke="#3E4A57", stroke_width=1.2, data_outline="1")
    )
    for k, v in enumerate(values):
        x, y = (0, k * cell) if vertical else (k * cell, 0)
        v = max(-1.0, min(1.0, float(v)))
        col = (
            _mix("#EEF0F3", "#8C96A3", 0.35 + 0.3 * abs(v))
            if encrypted
            else _mix("#F7F7F7", pos if v >= 0 else neg, 0.15 + 0.8 * abs(v))
        )
        holder.append(_el("rect", x=x, y=y, width=cell, height=cell, fill=col, stroke="#FFFFFF", stroke_width=0.8))
        ports[f"cell{k}"] = (x + cell / 2, y + cell / 2)
        if noise:
            dots = " ".join(
                f"M{fmt(x + cell * rnd.uniform(0.2, 0.8))} {fmt(y + cell * rnd.uniform(0.2, 0.8))} h.01"
                for _ in range(4)
            )
            holder.append(
                _el(
                    "path",
                    d=dots,
                    stroke="#1E2329",
                    stroke_opacity=0.55,
                    stroke_width=max(0.9, cell * 0.06),
                    stroke_linecap="round",
                    fill="none",
                )
            )
    if encrypted:
        segs, step = [], cell * 0.5  # 45° hatch clipped to the bar analytically (stays native)
        for i in range(int((W + H) / step) + 1):
            c = i * step  # line x + y = c
            x1, x2 = max(0.0, c - H), min(W, c)
            if x2 > x1:
                segs.append(f"M{fmt(x1)} {fmt(c - x1)} L{fmt(x2)} {fmt(c - x2)}")
        holder.append(
            _el("path", d=" ".join(segs), stroke="#5B6573", stroke_width=0.8, stroke_opacity=0.55, fill="none")
        )
    holder.append(_el("rect", x=0, y=0, width=W, height=H, fill="none", stroke="#3E4A57", stroke_width=1.2))
    if rich:
        look = _look()
        defs.append(_linear("vpg", [(0, "#FFFFFF", 0.45), (0.5, "#FFFFFF", 0.0)], y2=1))
        look.append(_el("rect", x=0, y=0, width=W, height=H, fill="url(#vpg)"))
        holder.append(look)
    boxes.append(Box(-0.6, -0.6, W + 1.2, H + 1.2))
    bx, by = (W + cell * 0.8, H / 2) if not vertical else (W / 2, H + cell * 0.8)
    ports["badge"] = (bx, by)
    if encrypted:
        s = cell * 1.1
        holder.extend(_lock_badge(bx, by - s * 0.1, s, "#D08A1F"))
        boxes.append(Box(bx - s * 0.5, by - s * 0.5, s, s))
    ports["first"], ports["last"] = ports["cell0"], ports[f"cell{n - 1}"]
    return _finish(holder, defs, _union(boxes), **ports)
