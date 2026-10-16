"""Cell–cell interface parts: immunological synapse and chemical synapse (``cell_interface``)."""

from __future__ import annotations

import math
import random

from ..atomize_svg_to_slide._geometry import fmt
from ._bio_parts import _el, _look, _mix, _hue, _smooth, _circ, _linear, _check_style, _finish, receptor, membrane
from ._geometry import Box, PathFrame, _finite, _hits, label
from ._help import _drawing_api

_PALETTE = ("#2E6FB0", "#9B2D6F", "#0B8A7A", "#C77B12", "#5B4BA8", "#B5473A")
_SHORT = ("gpcr", "channel")
_KINDS = ("bar", "antibody", "gpcr", "igsf", "car", "channel")


def _text(x, y, s, fs, fill, *, anchor="start", bold=True):
    t = _el("text", x=x, y=y, font_size=fs, fill=fill, text_anchor=anchor, font_weight="bold" if bold else None)
    t.text = s
    return t


@_drawing_api(
    "parts",
    purpose="细胞-细胞接触界面：上下两层平行磷脂双层 + 跨间隙成对受体-配体（免疫突触/检查点、神经突触、黏附、病毒-宿主附着）。",
    returns="Geometry（原点在中心；端口 top{i}_tip/top{i}_base/bottom{i}_tip/bottom{i}_base、cleft、top_cytoplasm、bottom_cytoplasm）",
    semantics=(
        'pairs 每项 {"top": "PD-1", "bottom": "PD-L1", "top_kind"/"bottom_kind": igsf|bar|antibody|gpcr|channel|car, '
        '"color": 受体色, "ligand_color": 配体色, "bound": 是否结合, "blocked_by": "阻断抗体名"}；top/bottom 可省略一侧。',
        "列等距排布；上方受体从上膜垂下、下方配体从下膜升起，bound=True 时尖端在间隙相接（接触点小圆），否则留空；"
        "blocked_by 在受体头部旁楔入一个抗体（有 blocked_by 时 bound 默认 False）。名称自动放在胞质侧茎旁，拥挤时换边/错行，均为原生文字。",
        '*_base 端口在胞质侧末端（带方向），信号箭头直接 d.arrow(node.port("top0_base"), box)。',
        'kind="neural"：上方为突触前末梢（突触囊泡 + 正在融合的囊泡释放递质），下方为突触后致密区；pairs 多为下方受体（默认 channel）。',
        'vesicles=None 时 neural 自动画囊泡；style="flat" 全原生。',
    ),
    example='syn = d.place(cell_interface([{"top": "TCR", "bottom": "pMHC"}, {"top": "PD-1", "bottom": "PD-L1", "blocked_by": "抗 PD-1"}]), at=(450, 200))\n'
    'd.arrow(syn.port("top1_base"), shp2, head="inhibit")',
    rank=4,
)
def cell_interface(
    pairs,
    *,
    width=820,
    gap=60,
    top_label=None,
    bottom_label=None,
    top_color="#7A6AA8",
    bottom_color="#C0705A",
    kind="immune",
    vesicles=None,
    font_size=13,
    style="rich",
    seed=3,
):
    rich = _check_style(style)
    if kind not in ("immune", "neural"):
        raise ValueError('kind must be "immune" or "neural"')
    _finite(width, gap, font_size)
    pairs = list(pairs)
    if not pairs and kind == "immune":
        raise ValueError("pairs must contain at least one receptor–ligand pair")
    if gap < 30:
        raise ValueError("gap must be at least 30")
    neural = kind == "neural"
    vesicles = neural if vesicles is None else vesicles
    if top_label is None:
        top_label = "突触前末梢" if neural else "T 细胞"
    if bottom_label is None:
        bottom_label = "突触后膜" if neural else "肿瘤细胞 / APC"
    W, fs, T, k = float(width), float(font_size), 22.0, 14.0
    cyto_top = 100.0 if vesicles else 70.0
    cyto_bot = 70.0
    Yu = cyto_top + T / 2  # upper membrane midline (at the centre)
    Yl = Yu + T + gap  # lower membrane midline
    H = Yl + T / 2 + cyto_bot
    c = (Yu + Yl) / 2  # cleft centre line
    f = lambda x: ((x - W / 2) / (W / 2)) ** 4
    yu = lambda x: Yu - k * f(x)
    yl = lambda x: Yl + k * f(x)
    xs_line = [W * i / 40 for i in range(41)]
    top_line = [(x, yu(x)) for x in xs_line]
    bot_line = [(x, yl(x)) for x in xs_line]
    top_tint = _mix(top_color, "#FFFFFF", 0.88)
    bot_tint = _mix(bottom_color, "#FFFFFF", 0.88)
    holder, defs = _el("g"), _el("defs")
    holder.append(defs)
    # cytoplasm tints (first one is the outline)
    up = [(x, y - T / 2 + 1) for x, y in top_line]
    holder.append(_el("path", d=_smooth(up) + f" L{fmt(W)} 0 L0 0 Z", fill=top_tint, data_outline="1"))
    lo = [(x, y + T / 2 - 1) for x, y in bot_line]
    holder.append(_el("path", d=_smooth(lo) + f" L{fmt(W)} {fmt(H)} L0 {fmt(H)} Z", fill=bot_tint))
    holder.append(
        _el(
            "path",
            d=_smooth([(x, y + T / 2 - 1) for x, y in top_line])
            + " "
            + " ".join(f"L{fmt(x)} {fmt(y - T / 2 + 1)}" for x, y in reversed(bot_line))
            + " Z",
            fill="#F6F4F1",
        )
    )  # extracellular cleft
    if rich:
        look = _look()
        defs.append(_linear("ci_top", [("0", top_tint, "0"), ("1", _mix(top_color, "#FFFFFF", 0.7), ".9")]))
        defs.append(_linear("ci_bot", [("0", _mix(bottom_color, "#FFFFFF", 0.7), ".9"), ("1", bot_tint, "0")]))
        look.append(_el("path", d=_smooth(up) + f" L{fmt(W)} 0 L0 0 Z", fill="url(#ci_top)"))
        look.append(_el("path", d=_smooth(lo) + f" L{fmt(W)} {fmt(H)} L0 {fmt(H)} Z", fill="url(#ci_bot)"))
        holder.append(look)

    n = max(1, len(pairs))
    margin = max(56.0, W * 0.07)
    col_x = [margin + (W - 2 * margin) * (i + 0.5) / n for i in range(n)]
    fusion_x = None
    if vesicles and neural:
        # dock the fusing vesicle between columns (or at the centre when there are none)
        cand = [W / 2] if len(col_x) < 2 else [(a + b) / 2 for a, b in zip(col_x, col_x[1:])]
        fusion_x = min(cand, key=lambda x: abs(x - W / 2))

    def mem(points, color, sd):
        g = membrane(_smooth(points), color=color, thickness=T, style=style, seed=sd).element
        g[0].attrib.pop("data-outline", None)
        return g

    if fusion_x is None:
        holder.append(mem(top_line, top_color, seed))
    else:
        rv = gap * 0.32 + 4
        left = [(x, y) for x, y in top_line if x < fusion_x - rv] + [(fusion_x - rv, yu(fusion_x - rv))]
        right = [(fusion_x + rv, yu(fusion_x + rv))] + [(x, y) for x, y in top_line if x > fusion_x + rv]
        holder.append(mem(left, top_color, seed))
        holder.append(mem(right, top_color, seed + 1))
    holder.append(mem(bot_line, bottom_color, seed + 2))

    nt = "#E0A23A"
    rnd = random.Random(seed)
    nt_dots = []
    if vesicles:
        # synaptic vesicles in the presynaptic terminal, each loaded with transmitter
        vr = 11.0
        nves = int(vesicles) if not isinstance(vesicles, bool) else max(5, int(W / 70))
        placed = []
        tries = 0
        while len(placed) < nves and tries < 600:
            tries += 1
            x = rnd.uniform(W * 0.16, W * 0.94)
            y = rnd.uniform(fs * 2 + vr, yu(x) - T / 2 - vr - 6)
            if all(math.dist((x, y), p) > 2 * vr + 6 for p in placed) and (
                fusion_x is None or math.dist((x, y), (fusion_x, Yu - 4)) > 2 * vr + 14
            ):
                placed.append((x, y))
        placed.sort()
        vcol = _mix(top_color, "#000000", 0.1)
        for x, y in placed:
            holder.append(_el("path", d=_circ(x, y, vr), fill="#FFFFFF", stroke=vcol, stroke_width=2.6))
            for j in range(5):
                a = j * 2 * math.pi / 5 + rnd.uniform(0, 0.6)
                rr = vr * (0.18 + 0.38 * (j % 2))
                nt_dots.append(_circ(x + rr * math.cos(a), y + rr * math.sin(a), 1.9))
        if fusion_x is not None:
            # omega-shaped fusion pore: vesicle membrane continuous with the plasma membrane, open to the cleft
            rv = gap * 0.32 + 4
            ym = yu(fusion_x)
            cx, cy = fusion_x, ym - rv * 0.45
            omega = (
                f"M{fmt(fusion_x - rv)} {fmt(ym)} C{fmt(fusion_x - rv * 0.2)} {fmt(ym)} {fmt(cx - rv * 1.15)} {fmt(cy + rv * 0.6)} "
                f"{fmt(cx - rv * 0.95)} {fmt(cy)} A{fmt(rv * 0.95)} {fmt(rv * 0.95)} 0 1 1 {fmt(cx + rv * 0.95)} {fmt(cy)} "
                f"C{fmt(cx + rv * 1.15)} {fmt(cy + rv * 0.6)} {fmt(fusion_x + rv * 0.2)} {fmt(ym)} {fmt(fusion_x + rv)} {fmt(ym)}"
            )
            holder.append(
                _el("path", d=omega, fill="#FFFFFF", stroke=top_color, stroke_width=T * 0.8, stroke_linejoin="round")
            )
            holder.append(
                _el("path", d=omega, fill="none", stroke=_mix(top_color, "#E9D9A6", 0.55), stroke_width=T * 0.22)
            )
            for j in range(6):
                a = j * 2 * math.pi / 6 + 0.3
                nt_dots.append(_circ(cx + rv * 0.45 * math.cos(a), cy + rv * 0.4 * math.sin(a), 1.9))
            for j in range(18):
                x = fusion_x + rnd.gauss(0, gap * 0.55)
                y = ym + T / 2 + 4 + abs(rnd.gauss(0, gap * 0.28))
                if y < Yl - T / 2 - 4:
                    nt_dots.append(_circ(x, y, 2.1))
    if neural:
        x0, x1 = col_x[0] - 46, col_x[-1] + 46
        pts = [(x, yl(x) + T / 2 + 2) for x in [x0 + (x1 - x0) * i / 16 for i in range(17)]]
        psd = _smooth(pts) + " " + " ".join(f"L{fmt(x)} {fmt(y + 9)}" for x, y in reversed(pts)) + " Z"
        holder.append(_el("path", d=psd, fill=_mix(bottom_color, "#3A2E2A", 0.35), stroke="none"))

    ports = {}
    texts, boxes = [], []
    region_top = _text(10, 6 + fs * 1.1, str(top_label), fs * 1.1, _mix(top_color, "#000000", 0.45))
    region_bot = _text(10, H - 8, str(bottom_label), fs * 1.1, _mix(bottom_color, "#000000", 0.45))
    for t, y_base in ((region_top, 6 + fs * 1.1), (region_bot, H - 8)):
        lw = label(t.text, font_size=fs * 1.1, font_weight="bold").bounds.width
        boxes.append(Box(10, y_base - fs * 1.1, lw, fs * 1.4))
        texts.append(t)
    stems, labels_todo = [], []
    tail = 14.0
    for i, (p, x) in enumerate(zip(pairs, col_x)):
        if not isinstance(p, dict):
            raise TypeError('each pair must be a dict like {"top": "PD-1", "bottom": "PD-L1"}')
        color = p.get("color") or _PALETTE[i % len(_PALETTE)]
        lcol = p.get("ligand_color") or _mix(_hue(color, 38), "#FFFFFF", 0.12)
        tk = p.get("top_kind", "igsf")
        bk = p.get("bottom_kind", "channel" if neural else "igsf")
        for kk in (tk, bk):
            if kk not in _KINDS:
                raise ValueError(f"receptor kind must be one of {_KINDS}")
        has_t, has_b = p.get("top") is not None, p.get("bottom") is not None
        bound = p.get("bound", not p.get("blocked_by"))
        ut, ub = yu(x), yl(x)
        t_short = has_t and tk in _SHORT and not (has_b and bk in _SHORT)
        b_short = has_b and bk in _SHORT and not (has_t and tk in _SHORT)
        t_base, b_base = ut - T / 2 - tail, ub + T / 2 + tail
        if t_short:
            t_base = ut - T / 2 - 8
        if b_short:
            b_base = ub + T / 2 + 8
        ext = gap * 0.3 if (tk if t_short else bk) == "channel" else gap * 0.14
        if t_short:
            contact = ut + T / 2 + ext
        elif b_short:
            contact = ub - T / 2 - ext
        else:
            contact = c
        t_tip = ut + T / 2 + ext if t_short else contact
        b_tip = ub - T / 2 - ext if b_short else contact
        if not bound:
            room = gap
            if has_t and not t_short:
                t_tip = contact - room * (0.16 if not b_short else 0.3)
            if has_b and not b_short:
                b_tip = contact + room * (0.16 if not t_short else 0.3)
        widths = {}
        for side, has, rk, col, base, tip in (
            ("top", has_t, tk, color, t_base, t_tip),
            ("bottom", has_b, bk, lcol, b_base, b_tip),
        ):
            if not has:
                continue
            h = abs(tip - base)
            dom = p.get(f"{side}_domains", 2 if (has_t and has_b) else 3)
            ecto = abs(tip - (ut + T / 2 if side == "top" else ub - T / 2))  # extracellular length
            rw_ = max(9.0, min(16.0, (ecto - 3) / max(1, min(3, int(dom))) / 1.08)) if rk == "igsf" else None
            g = receptor(kind=rk, color=col, height=h, domains=dom, width=rw_, style=style)
            if side == "top":
                g = g.rotated(180, about=(0, 0))
            g = g.moved(x, (base + tip) / 2)
            holder.append(g.element)
            rw = g.bounds.width
            widths[side] = rw
            sgn = -1 if side == "top" else 1
            ports[f"{side}{i}_tip"] = (x, tip)
            ports[f"{side}{i}_base"] = PathFrame((x, base), (1.0, 0.0), (0.0, float(sgn)), None)
            stem_w = rw if rk in _SHORT else min(rw, 22)
            surf = ut - T / 2 if side == "top" else ub + T / 2 + (12 if neural else 0)
            stems.append(Box(x - stem_w / 2, min(base, surf), stem_w, max(0.0, abs(surf - base))))
            labels_todo.append((side, i, x, stem_w, surf, str(p[side]), _mix(col, "#000000", 0.4)))
        if has_t and has_b and bound:
            holder.append(
                _el(
                    "path",
                    d=_circ(x, contact, 3.4),
                    fill="#F2C14E",
                    stroke=_mix("#F2C14E", "#000000", 0.45),
                    stroke_width=1,
                )
            )
        if p.get("blocked_by") and has_t:
            # blocking antibody wedged on the receptor head: Fab arms grip the receptor, Fc points sideways
            ah = min(gap * 0.78, 52.0)
            ab = receptor(kind="antibody", color="#2E6FB0" if color != "#2E6FB0" else "#3B8E4E", height=ah, style=style)
            ab = ab.rotated(-90, about=(0, 0))
            rw = widths.get("top", 18)
            ay = (ut + T / 2 + t_tip) / 2 + (2 if bound else 4)
            ax = x + rw / 2 + ab.bounds.width / 2 - 5
            right_free = i < n - 1 or ax + ab.bounds.width / 2 < W - 60
            if not right_free:
                ab = receptor(kind="antibody", color="#2E6FB0", height=ah, style=style).rotated(90, about=(0, 0))
                ax = x - rw / 2 - ab.bounds.width / 2 + 5
            ab = ab.moved(ax, ay)
            holder.append(ab.element)
            ports[f"block{i}"] = (ax, ay)
            afs = fs * 0.85
            lw = label(str(p["blocked_by"]), font_size=afs, font_weight="bold").bounds.width
            if right_free:
                lx = ax + ab.bounds.width / 2 + 3
            else:
                lx = ax - ab.bounds.width / 2 - 3 - lw
            lb = Box(lx, ay - afs * 0.7, lw, afs * 1.3)
            if _hits(lb, stems):
                lb = Box(ax - lw / 2, ay + ab.bounds.height / 2 + 1, lw, afs * 1.3)
            texts.append(_text(lb.x, lb.y + afs * 0.95, str(p["blocked_by"]), afs, "#1F4F80"))
            boxes.append(lb)
    # names on the cytoplasmic side next to each stem; alternate side / step outward when crowded
    for side, i, x, sw, surf, name, col in labels_todo:
        lw = label(name, font_size=fs, font_weight="bold").bounds.width
        lh = fs * 1.25
        sgn = -1 if side == "top" else 1
        cands = []
        for row in range(4):
            cy = surf + sgn * (3 + lh / 2 + row * (lh + 2))
            cands.append(Box(x + sw / 2 + 4, cy - lh / 2, lw, lh))
            cands.append(Box(x - sw / 2 - 4 - lw, cy - lh / 2, lw, lh))
        others = [s for s in stems if not (abs(s.x + s.width / 2 - x) < 1 and (s.y < c) == (side == "top"))]
        pick = None
        for b in cands:
            if b.x < 2 or b.x + b.width > W - 2 or b.y < 1 or b.y + b.height > H - 1:
                continue
            if not _hits(b, boxes) and not _hits(b, others, pad=1):
                pick = b
                break
        pick = pick or cands[0]
        boxes.append(pick)
        texts.append(_text(pick.x, pick.y + fs * 0.98, name, fs, col))
    if nt_dots:
        holder.append(_el("path", d=" ".join(nt_dots), fill=nt, stroke=_mix(nt, "#000000", 0.35), stroke_width=0.4))
    if neural:
        # a few transmitter molecules bound at receptor tips
        tips = [ports[k] for k in sorted(ports) if k.startswith("bottom") and k.endswith("_tip")]
        if tips:
            holder.append(
                _el(
                    "path",
                    d=" ".join(_circ(x + dx, y - 3.5, 2.1) for x, y in tips for dx in (-4, 4)),
                    fill=nt,
                    stroke=_mix(nt, "#000000", 0.35),
                    stroke_width=0.4,
                )
            )
    holder.extend(texts)
    ports.update(
        cleft=(W / 2, c),
        top_cytoplasm=(W / 2, (Yu - T / 2) / 2 + fs * 0.6),
        bottom_cytoplasm=(W / 2, (Yl + T / 2 + H) / 2),
    )
    if fusion_x is not None:
        ports["fusion"] = (fusion_x, yu(fusion_x))
    return _finish(holder, defs, Box(0, 0, W, H), **ports)
