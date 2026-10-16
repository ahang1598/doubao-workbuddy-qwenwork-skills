"""Signalling-pathway figures and small annotation glyphs: ``signaling_cascade``, ``badge``."""

from __future__ import annotations

import math
import random

from ..atomize_svg_to_slide._geometry import fmt
from ._bio_parts import (
    _el,
    _look,
    _mix,
    _radial,
    _smooth,
    _circle_union,
    _check_style,
    _finish,
    _hue,
    _nucleus_layers,
    receptor as _receptor_part,
    membrane as _membrane_part,
    dna as _dna_part,
)
from ._geometry import Box, _finite, label
from ._help import _drawing_api

_INK = "#2A2A33"
_PALETTE = ("#2E6FB0", "#0B8A7A", "#7A5BB0", "#C77B12", "#3B8E4E", "#B5473A", "#4F7FA8", "#9B2D6F")
_PHOS = "#F2C14E"


def _tw(s, fs, bold=True, italic=False):
    return label(
        str(s), font_size=fs, font_weight="bold" if bold else "normal", font_style="italic" if italic else "normal"
    ).bounds.width


def _text(x, cy, s, fs, fill, *, anchor="middle", bold=True, italic=False):
    t = _el(
        "text",
        x=x,
        y=cy + fs * 0.35,
        font_size=fs,
        fill=fill,
        text_anchor=anchor,
        font_weight="bold" if bold else None,
        font_style="italic" if italic else None,
    )
    t.text = str(s)
    return t


def _dark(color):
    c = color.lstrip("#")
    if len(c) != 6:
        return True
    r, g, b = (int(c[i : i + 2], 16) for i in (0, 2, 4))
    return 0.299 * r + 0.587 * g + 0.114 * b < 150


def _protein_d(cx, cy, w, h, seed):
    """Globular protein outline: an ellipse with a few soft lobes (reads as a folded protein, not a box)."""
    rnd = random.Random(seed)
    ph = [rnd.uniform(0, 2 * math.pi) for _ in range(3)]
    pts = []
    for i in range(40):
        a = 2 * math.pi * i / 40
        k = 1 + 0.045 * math.sin(3 * a + ph[0]) + 0.03 * math.sin(5 * a + ph[1]) + 0.02 * math.sin(7 * a + ph[2])
        pts.append((cx + w / 2 * k * math.cos(a), cy + h / 2 * k * math.sin(a)))
    return _smooth(pts, closed=True)


def _line(pts, color, sw, head=None, dashed=False, size=None):
    """Polyline with a filled arrowhead (head='arrow'), a T-bar (head='inhibit') or a plain end; returns elements."""
    pts = [tuple(p) for p in pts]
    out = []
    size = size or max(7.0, sw * 4)
    (x1, y1), (x0, y0) = pts[-1], pts[-2]
    L = math.hypot(x1 - x0, y1 - y0) or 1
    ux, uy = (x1 - x0) / L, (y1 - y0) / L
    if head == "arrow":
        pts[-1] = (x1 - ux * size * 0.8, y1 - uy * size * 0.8)
    elif head == "inhibit":
        pts[-1] = (x1 - ux * sw * 1.2, y1 - uy * sw * 1.2)
    d = "M" + " L".join(f"{fmt(x)} {fmt(y)}" for x, y in pts)
    out.append(
        _el(
            "path",
            d=d,
            fill="none",
            stroke=color,
            stroke_width=sw,
            stroke_linejoin="round",
            stroke_linecap="butt",
            stroke_dasharray=f"{fmt(sw * 3)} {fmt(sw * 2.2)}" if dashed else None,
        )
    )
    if head == "arrow":
        bx, by, hw = x1 - ux * size, y1 - uy * size, size * 0.5
        out.append(
            _el(
                "path",
                d=f"M{fmt(x1)} {fmt(y1)} L{fmt(bx - uy * hw)} {fmt(by + ux * hw)} L{fmt(bx + uy * hw)} {fmt(by - ux * hw)} Z",
                fill=color,
                stroke="none",
            )
        )
    elif head == "inhibit":
        bw = max(12.0, sw * 6) / 2
        out.append(
            _el(
                "path",
                d=f"M{fmt(x1 - uy * bw)} {fmt(y1 + ux * bw)} L{fmt(x1 + uy * bw)} {fmt(y1 - ux * bw)}",
                fill="none",
                stroke=color,
                stroke_width=sw * 1.9,
                stroke_linecap="butt",
            )
        )
    return out


@_drawing_api(
    "parts",
    purpose="编号徽章：小圆（或圆角方块）+ 居中短文字作为一个对象（步骤序号、图注编号、显著性星号），check 不报文字压框。",
    returns="Geometry（原点在中心；端口四边/center）",
    semantics=(
        'text 为 1–3 个字符；r 为半径，font_size 默认 1.15·r；shape="circle"|"square"。',
        "fill 底色，color 文字色（默认按底色自动黑/白）；stroke 可加描边。",
    ),
    example='for i, x in enumerate((200, 320, 440), 1):\n    d.place(badge(str(i), fill="#5B1061"), at=(x, 80))',
    rank=40,
)
def badge(text, r=11, *, fill="#5B1061", color=None, font_size=None, shape="circle", stroke=None, bold=True):
    _finite(r)
    if shape not in ("circle", "square"):
        raise ValueError('shape must be "circle" or "square"')
    text = str(text)
    if not 1 <= len(text) <= 3:
        raise ValueError("badge text should be 1–3 characters; longer text belongs in a box_at / text_box")
    fs = font_size or r * 1.15
    color = color or ("#FFFFFF" if _dark(fill) else _INK)
    holder = _el("g")
    paint = dict(fill=fill, stroke=stroke or "none", stroke_width=1.2 if stroke else None, data_outline="1")
    if shape == "circle":
        holder.append(_el("circle", cx=0, cy=0, r=r, **paint))
    else:
        holder.append(_el("rect", x=-r, y=-r, width=2 * r, height=2 * r, rx=r * 0.3, **paint))
    holder.append(_text(0, 0, text, fs, color, bold=bold))
    return _finish(holder, None, Box(-r, -r, 2 * r, 2 * r))


def _norm_step(s, k):
    if isinstance(s, str):
        s = {"name": s}
    if not isinstance(s, dict) or "name" not in s:
        raise TypeError('each step is a name or a dict like {"name": "SMAD2/3", "phospho": True, "partner": "SMAD4"}')
    return dict(
        name=str(s["name"]),
        phospho=bool(s.get("phospho")),
        partner=s.get("partner"),
        color=s.get("color") or _PALETTE[k % len(_PALETTE)],
    )


def _pill(cx, cy, w, h, color):
    """Two-tone capsule (drug glyph)."""
    r = h / 2
    left = (
        f"M{fmt(cx)} {fmt(cy - r)} L{fmt(cx - w / 2 + r)} {fmt(cy - r)} A{fmt(r)} {fmt(r)} 0 0 0 {fmt(cx - w / 2 + r)} {fmt(cy + r)} "
        f"L{fmt(cx)} {fmt(cy + r)} Z"
    )
    right = (
        f"M{fmt(cx)} {fmt(cy - r)} L{fmt(cx + w / 2 - r)} {fmt(cy - r)} A{fmt(r)} {fmt(r)} 0 0 1 {fmt(cx + w / 2 - r)} {fmt(cy + r)} "
        f"L{fmt(cx)} {fmt(cy + r)} Z"
    )
    edge = _mix(color, "#000000", 0.35)
    return [
        _el("path", d=left, fill=color, stroke=edge, stroke_width=1),
        _el("path", d=right, fill="#FFFFFF", stroke=edge, stroke_width=1),
        _el("ellipse", cx=cx - w * 0.22, cy=cy - r * 0.45, rx=w * 0.14, ry=r * 0.2, fill="#FFFFFF", fill_opacity=0.55),
    ]


@_drawing_api(
    "parts",
    purpose="信号通路级联（教科书式）：配体 → 嵌在磷脂双层里的受体 → 胞质蛋白团块（可带磷酸化 P 徽章、形成复合体）→ 核内结合 DNA 的转录因子与靶基因；负反馈 T 形抑制线绕主干外侧，旁路分支在侧面，药物以胶囊 + 抑制线标在靶点旁。适用于任何通路（TGF-β/Smad、MAPK、PI3K-AKT、JAK-STAT、Wnt、NF-κB…）。",
    returns="Geometry（原点在中心；每个节点名都是端口，另有 名_left/名_right，以及 ligand/receptor/membrane/nucleus/dna/step{i}/药物名）",
    semantics=(
        'steps 为胞质级联，自上而下：名字或 {"name", "phospho": True 画 P, "partner": "SMAD4" 结合成复合体, "color"}。',
        'ligand 为配体名（受体顶部的二聚体小球）；receptor 为受体名，receptor_kind="kinase"（默认，跨膜激酶受体二聚体：胞外结构域-跨膜段-胞内激酶域）'
        "或 gpcr/igsf/channel/bar（用 receptor 部件）；receptor_phospho=True 在激酶域画 P。",
        "nucleus_targets 为靶基因名：最后一步经核孔入核，结合在 DNA 上，靶基因画成 DNA 上的色带 + 斜体基因名 + 转录起始箭头；为空则不画核。",
        'feedback 为 [(源, 靶)] 或 {"from", "to", "label", "head": "inhibit"|"arrow", "dashed"}：默认 T 形抑制，走主干右侧外车道，不穿过节点；源可为靶基因名。',
        'branches 为 [{"from": 节点名, "steps": [...], "label": "非经典", "to": 节点名或 "nucleus"}]：在主干左侧另起一列，从源节点胞质侧水平引出，不穿过受体/膜。',
        "inhibitors 为 [(药物名, 靶节点)]：胶囊 + 药物名放在靶点外侧，T 形线指向靶点；靶点可为 ligand/receptor/任一 step/分支 step。",
        'compartments 为 (胞外, 胞质, 细胞核) 区域名（灰色小字在左侧），None 不画；color 为主干色、accent 为抑制/药物色；仅支持 orientation="vertical"。',
    ),
    example='p = d.place(signaling_cascade(["Adaptor", {"name": "Kinase", "phospho": True}, {"name": "TF", "phospho": True, "partner": "Co-TF"}],\n'
    '        ligand="Ligand", receptor="Receptor", receptor_phospho=True, nucleus_targets=["Gene1", "Inhib"], feedback=[("Inhib", "receptor")],\n'
    '        branches=[{"from": "receptor", "steps": ["Kinase2"], "label": "非经典"}], inhibitors=[("Drug", "Kinase")]), at=(480, 270), key="path")',
    rank=6,
)
def signaling_cascade(
    steps,
    *,
    ligand=None,
    receptor="Receptor",
    receptor_kind="kinase",
    receptor_phospho=False,
    feedback=(),
    branches=(),
    nucleus_targets=(),
    inhibitors=(),
    orientation="vertical",
    color="#2E6FB0",
    accent="#C0392B",
    ligand_color="#E08A2C",
    membrane_color="#9A88C9",
    nucleus_color="#D9CCEB",
    font_size=13,
    compartments=("胞外", "胞质", "细胞核"),
    style="rich",
    seed=2,
):
    rich = _check_style(style)
    if orientation != "vertical":
        raise ValueError(
            'signaling_cascade supports orientation="vertical" only; for a left-to-right chain use row() + box_at/parts'
        )
    _finite(font_size)
    fs = float(font_size)
    steps = [_norm_step(s, k) for k, s in enumerate(steps)]
    if not steps:
        raise ValueError("steps must list at least one cytoplasmic node")
    branches = [dict(b) for b in branches]
    for b in branches:
        if "from" not in b or not b.get("steps"):
            raise ValueError('each branch needs "from" and a non-empty "steps" list')
    targets = [str(t) for t in nucleus_targets]
    sw = max(1.6, fs * 0.14)
    ink = _INK
    holder, defs = _el("g"), _el("defs")
    holder.append(defs)
    look = _look() if rich else None
    nodes = {}  # name -> (cx, cy, w, h)  hit box
    texts = []
    under, over = [], []  # elements below / above the protein glyphs
    grads = {}

    def grad(col):
        if col not in grads:
            gid = f"scg{len(grads)}"
            defs.append(_radial(gid, _mix(col, "#FFFFFF", 0.55), _mix(col, "#000000", 0.18), fx=0.36, fy=0.3))
            grads[col] = gid
        return grads[col]

    def protein(name, cx, cy, col, *, phospho=False, partner=None, sd=0, key=None):
        w = max(fs * 4.2, _tw(name, fs) + fs * 1.8)
        h = fs * 2.3
        glyph = []
        parts = [(name, cx, w, col)]
        if partner:
            pw = max(fs * 3.6, _tw(partner, fs) + fs * 1.4)
            parts.append((str(partner), cx + w / 2 + pw / 2 - fs * 0.5, pw, _hue(col, 140, light=0.42)))
        for j, (nm, x, ww, c) in enumerate(parts[::-1]):
            d = _protein_d(x, cy, ww, h * (1 if j == len(parts) - 1 else 0.94), seed + sd * 7 + j)
            glyph.append(_el("path", d=d, fill=c, stroke=_mix(c, "#000000", 0.35), stroke_width=1.1))
            if rich:
                look.append(_el("path", d=d, fill=f"url(#{grad(c)})"))
                look.append(
                    _el(
                        "ellipse",
                        cx=x - ww * 0.2,
                        cy=cy - h * 0.26,
                        rx=ww * 0.16,
                        ry=h * 0.1,
                        fill="#FFFFFF",
                        fill_opacity=0.4,
                    )
                )
        for nm, x, ww, c in parts:
            texts.append(_text(x, cy, nm, fs, "#FFFFFF" if _dark(c) else ink))
        right = parts[-1][1] + parts[-1][2] / 2
        if phospho:
            r = fs * 0.55
            bx, by = cx + w / 2 - r * 0.2, cy - h / 2 + r * 0.1
            if partner:
                bx = cx + w / 2 - fs * 1.2
            over.append(
                _el("circle", cx=bx, cy=by, r=r, fill=_PHOS, stroke=_mix(_PHOS, "#000000", 0.45), stroke_width=0.9)
            )
            texts.append(_text(bx, by, "P", fs * 0.72, ink))
        nodes[key or name] = (cx, cy, w, h, cx - w / 2, right)
        return glyph

    trunk_w = max(
        max(fs * 4.2, _tw(s["name"], fs) + fs * 1.8)
        + (max(fs * 3.6, _tw(s["partner"], fs) + fs * 1.4) * 2 - fs if s["partner"] else 0)
        for s in steps
    )
    trunk_half = max(trunk_w / 2, fs * 4.6)
    comp_w = max((_tw(c, fs * 0.85, bold=False) for c in compartments), default=0) + fs if compartments else 0
    col_gap = fs * 2.6
    br_w = [max(max(fs * 4.2, _tw(_norm_step(s, 0)["name"], fs) + fs * 1.8) for s in b["steps"]) for b in branches]
    left_span = sum(w + col_gap for w in br_w)
    Xc = comp_w + left_span + trunk_half + fs * 0.5
    br_x, x = [], Xc - trunk_half
    for w in br_w:
        x -= col_gap + w / 2
        br_x.append(x)
        x -= w / 2
    T = max(18.0, fs * 1.6)
    pitch = fs * 2.3 + fs * 2.6
    y_lig = fs * 1.3
    ecto_h = fs * 2.3
    ecto_top = y_lig + fs * 0.9 if ligand else fs * 0.4
    Ym = ecto_top + ecto_h + T / 2
    kin_top = Ym + T / 2
    kin_h = fs * 2.3
    kin_cy = kin_top + kin_h / 2 + fs * 0.2
    rcol, rcol2 = color, _hue(color, 30, light=0.62)
    if receptor_kind == "kinase":
        rw = fs * 1.55
        for j, (dx, c) in enumerate(((-rw * 0.62, rcol2), (rw * 0.62, rcol))):
            x = Xc + dx
            ecto = _smooth(
                [
                    (x - rw / 2, Ym - T / 2),
                    (x - rw * 0.58, ecto_top + ecto_h * 0.45),
                    (x - rw * 0.3, ecto_top + 1),
                    (x + rw * 0.3, ecto_top),
                    (x + rw * 0.58, ecto_top + ecto_h * 0.5),
                    (x + rw / 2, Ym - T / 2),
                ],
                closed=True,
            )
            under.append(_el("path", d=ecto, fill=c, stroke=_mix(c, "#000000", 0.35), stroke_width=1))
            under.append(
                _el(
                    "rect",
                    x=x - rw * 0.17,
                    y=Ym - T / 2 - 1,
                    width=rw * 0.34,
                    height=T + 2,
                    rx=rw * 0.1,
                    fill=_mix(c, "#000000", 0.15),
                )
            )
            kin = _circle_union(
                [
                    ((x + dx * 0.25, kin_cy - kin_h * 0.16), kin_h * 0.36),
                    ((x + dx * 0.45, kin_cy + kin_h * 0.16), kin_h * 0.42),
                ],
                40,
            )
            under.append(_el("path", d=kin, fill=c, stroke=_mix(c, "#000000", 0.35), stroke_width=1))
            if rich:
                look.append(_el("path", d=kin, fill=f"url(#{grad(c)})"))
                look.append(_el("path", d=ecto, fill=f"url(#{grad(c)})"))
        r_left, r_right = Xc - rw * 1.4 - kin_h * 0.45, Xc + rw * 1.4 + kin_h * 0.45
        if receptor_phospho:
            r = fs * 0.55
            for dx in (-1, 1):
                bx = Xc + dx * (rw * 0.62 + kin_h * 0.7)
                over.append(
                    _el(
                        "circle",
                        cx=bx,
                        cy=kin_cy - kin_h * 0.3,
                        r=r,
                        fill=_PHOS,
                        stroke=_mix(_PHOS, "#000000", 0.45),
                        stroke_width=0.9,
                    )
                )
                texts.append(_text(bx, kin_cy - kin_h * 0.3, "P", fs * 0.72, ink))
            r_left, r_right = (
                min(r_left, Xc - rw * 0.62 - kin_h * 0.7 - r),
                max(r_right, Xc + rw * 0.62 + kin_h * 0.7 + r),
            )
    else:
        if receptor_kind == "igsf":
            # extracellular Ig beads above the bilayer, stalk spanning it, short cytoplasmic tail
            g = _receptor_part(
                kind="igsf", color=rcol, height=ecto_h + T + fs * 1.2, domains=2, width=ecto_h / 2.16, style=style
            )
        else:
            g = _receptor_part(
                kind=receptor_kind,
                color=rcol,
                height=ecto_h + T + kin_h * 0.6,
                width=fs * 2.6 if receptor_kind == "gpcr" else None,
                style=style,
            )
        if receptor_kind in ("gpcr", "channel"):
            g = g.moved(Xc, Ym)  # transmembrane body centred in the bilayer
        else:
            g = g.moved(Xc, ecto_top - g.bounds.y + 0)
        under.append(g.element)
        r_left, r_right = g.bounds.x, g.bounds.x + g.bounds.width
        kin_h = max(fs * 1.0, g.bounds.y + g.bounds.height - kin_top)
        kin_cy = kin_top + kin_h / 2
    nodes["receptor"] = (Xc, kin_cy, r_right - r_left, kin_h, r_left, r_right)
    rows = [kin_cy + kin_h / 2 + fs * 1.15 + fs * 2.6 + pitch * k for k in range(len(steps))]
    glyphs = []
    for k, (s, y) in enumerate(zip(steps, rows)):
        glyphs += protein(
            s["name"], Xc, y, s["color"], phospho=s["phospho"], partner=s["partner"], sd=k, key=f"step{k}"
        )
    names = {s["name"]: f"step{k}" for k, s in reversed(list(enumerate(steps)))}

    def ref(name):
        name = str(name)
        if name in ("receptor", str(receptor)):
            return "receptor"
        if name in ("ligand", str(ligand)) and ligand:
            return "ligand"
        if name in nodes:
            return name
        if name in names:
            return names[name]
        raise ValueError(f"unknown pathway node {name!r}; use ligand/receptor, a step, branch step or target gene name")

    prev_bottom = kin_cy + kin_h / 2
    for k, y in enumerate(rows):
        under += _line([(Xc, prev_bottom + 2), (Xc, y - fs * 1.15 - 2)], ink, sw, "arrow")
        prev_bottom = y + fs * 1.15
    trunk_right = max(max(n[5] for n in nodes.values()), Xc + trunk_half)
    if ligand:
        lr = fs * 0.62
        lig = _circle_union([((Xc - lr * 0.85, y_lig), lr), ((Xc + lr * 0.85, y_lig), lr)], 48)
        glyphs.append(_el("path", d=lig, fill=ligand_color, stroke=_mix(ligand_color, "#000000", 0.35), stroke_width=1))
        if rich:
            look.append(_el("path", d=lig, fill=f"url(#{grad(ligand_color)})"))
        texts.append(_text(Xc + lr * 2.1, y_lig, ligand, fs, _mix(ligand_color, "#000000", 0.45), anchor="start"))
        nodes["ligand"] = (Xc, y_lig, lr * 3.7, lr * 2, Xc - lr * 1.85, Xc + lr * 2.1 + _tw(ligand, fs))
    texts.append(
        _text(Xc + fs * 2.4, ecto_top + ecto_h * 0.5, receptor, fs, _mix(rcol, "#000000", 0.35), anchor="start")
    )
    trunk_right = max(trunk_right, Xc + fs * 2.4 + _tw(receptor, fs))
    for bi, (b, bx) in enumerate(zip(branches, br_x)):
        src = ref(b["from"])
        sx, sy, _, _, sl, _ = nodes[src]
        bsteps = [_norm_step(s, len(steps) + bi * 3 + j) for j, s in enumerate(b["steps"])]
        y = sy
        first = True
        for j, s in enumerate(bsteps):
            ny = sy + pitch * (j + 1) if not first or True else sy
            if first:
                under += _line([(sl - 2, sy), (bx, sy), (bx, ny - fs * 1.15 - 2)], ink, sw, "arrow")
            else:
                under += _line([(bx, y + fs * 1.15 + 2), (bx, ny - fs * 1.15 - 2)], ink, sw, "arrow")
            glyphs += protein(
                s["name"],
                bx,
                ny,
                s["color"],
                phospho=s["phospho"],
                partner=s["partner"],
                sd=20 + bi * 5 + j,
                key=s["name"] if s["name"] not in nodes else f"b{bi}_{j}",
            )
            y, first = ny, False
        if b.get("label"):
            texts.append(
                _text(bx, y + fs * 2.1, b["label"], fs * 0.9, _mix(ink, "#FFFFFF", 0.3), bold=False, italic=True)
            )
        b["_end"] = (bx, y)
    last = nodes[f"step{len(steps) - 1}"]
    bottom = max([last[1] + last[3] / 2] + [b["_end"][1] + fs * 2.6 for b in branches])
    gene_ports = {}
    if targets:
        tf = steps[-1]
        n_top = bottom + fs * 2.0
        tf_y = n_top + fs * 3.0
        dna_y = tf_y + fs * 1.15 + fs * 0.55
        tf_w = last[5] - last[4]
        x0 = Xc - tf_w / 2 - fs * 1.4
        gx = last[5] + fs * 1.2
        bands = []
        for gname in targets:
            gw = max(fs * 3.2, _tw(gname, fs, italic=True) + fs * 0.9)
            bands.append((gname, gx, gw))
            gx += gw + fs * 0.8
        x1 = gx + fs * 0.6
        lab_y = dna_y + fs * 1.6
        n_bot = lab_y + fs * 1.9 + (fs * 0.9 if feedback else 0)
        nl = min([x0] + [bx - w / 2 for bx, w in zip(br_x, br_w)]) - fs * 0.8
        nr = max(x1, trunk_right) + fs * 0.8
        rx, ry = (nr - nl) / 2, (n_bot - n_top) / 2
        if rich:
            defs.append(
                _radial(
                    "nucg", _mix(nucleus_color, "#FFFFFF", 0.5), _mix(nucleus_color, "#000000", 0.12), fx=0.4, fy=0.35
                )
            )
        o, lk, after = _nucleus_layers(
            rx, ry, nucleus_color, rich=rich, seed=seed, pores=True, chromatin=False, nucleoli=0
        )
        ng = _el("g", transform=f"translate({fmt(nl)} {fmt(n_top)})")
        o.attrib.pop("data-outline", None)
        ng.append(o)
        if lk is not None:
            ng.append(lk)
        ng.extend(after)
        under.insert(0, ng)
        under.append(
            _el(
                "ellipse",
                cx=Xc,
                cy=n_top,
                rx=fs * 0.55,
                ry=fs * 0.32,
                fill="#FFFFFF",
                stroke=_mix(nucleus_color, "#000000", 0.35),
                stroke_width=0.9,
            )
        )
        under += _line([(Xc, bottom + 2), (Xc, tf_y - fs * 1.15 - 2)], ink, sw, "arrow")
        dg = _dna_part(x1 - x0, width=fs * 1.1, color="#2E5C9A", style=style).moved((x0 + x1) / 2, dna_y)
        under.append(dg.element)
        glyphs += protein(
            tf["name"], Xc, tf_y, tf["color"], phospho=tf["phospho"], partner=tf["partner"], sd=40, key="tf_nuclear"
        )
        for k, (gname, g0, gw) in enumerate(bands):
            gc = _PALETTE[(k + 3) % len(_PALETTE)]
            over.append(
                _el(
                    "rect",
                    x=g0,
                    y=dna_y - fs * 0.7,
                    width=gw,
                    height=fs * 1.4,
                    rx=fs * 0.25,
                    fill=gc,
                    fill_opacity=0.35,
                    stroke=gc,
                    stroke_width=1.2,
                )
            )
            over += _line(
                [
                    (g0 + fs * 0.3, dna_y - fs * 0.7),
                    (g0 + fs * 0.3, dna_y - fs * 1.7),
                    (g0 + fs * 1.4, dna_y - fs * 1.7),
                ],
                ink,
                sw * 0.75,
                "arrow",
                size=fs * 0.55,
            )
            texts.append(_text(g0 + gw / 2, lab_y, gname, fs, _mix(gc, "#000000", 0.45), italic=True))
            nodes[gname] = (g0 + gw / 2, lab_y, gw, fs * 1.3, g0, g0 + gw)
            gene_ports[gname] = (g0 + gw / 2, dna_y)
        nodes["nucleus"] = (nl + rx, n_top + ry, 2 * rx, 2 * ry, nl, nr)
        bottom = n_bot
        trunk_right = max(trunk_right, nr)
        for b in branches:
            if b.get("to") == "nucleus":
                bx, by = b["_end"]
                inner = n_top + ry - ry * math.sqrt(max(0, 1 - ((bx - nl - rx) / rx) ** 2))
                under += _line([(bx, by + fs * 1.15 + 2), (bx, inner - 2)], ink, sw, "arrow")
    for b in branches:
        to = b.get("to")
        if to and to != "nucleus":
            bx, by = b["_end"]
            tx, ty, *_r, tl, _tr = nodes[ref(to)]
            under += _line([(bx, by + fs * 1.15 + 2), (bx, ty), (tl - 2, ty)], ink, sw, "arrow")
    pill_w, pill_h = fs * 2.3, fs * 1.1
    inh_x = (
        trunk_right + fs * 2.4
        if not targets
        else max(n[5] for k, n in nodes.items() if k not in ("nucleus",) and k not in gene_ports) + fs * 2.4
    )
    drug_right = inh_x
    drug_ports = {}
    for item in inhibitors:
        drug, tgt = (item["name"], item["target"]) if isinstance(item, dict) else item
        key = ref(tgt)
        cx_, cy_, w_, h_, tl, tr = nodes[key]
        left_side = any(abs(cx_ - bx) < 1 for bx in br_x)
        yy = cy_ + h_ * 0.42 if key != "ligand" else cy_
        if left_side:
            px = tl - fs * 2.2 - pill_w / 2
            over += _pill(px, yy, pill_w, pill_h, accent)
            over += _line([(px + pill_w / 2 + 2, yy), (tl - 1, yy)], accent, sw, "inhibit")
            texts.append(_text(px, yy + pill_h / 2 + fs * 0.75, drug, fs * 0.9, _mix(accent, "#000000", 0.3)))
        else:
            px = max(inh_x, tr + fs * 2.2) + pill_w / 2
            over += _pill(px, yy, pill_w, pill_h, accent)
            over += _line([(px - pill_w / 2 - 2, yy), (tr + 1, yy)], accent, sw, "inhibit")
            texts.append(
                _text(px + pill_w / 2 + fs * 0.35, yy, drug, fs * 0.9, _mix(accent, "#000000", 0.3), anchor="start")
            )
            drug_right = max(drug_right, px + pill_w / 2 + fs * 0.35 + _tw(drug, fs * 0.9))
        drug_ports[str(drug)] = (px, yy)
    lane0 = max(drug_right, trunk_right) + fs * 1.6
    hits = {}
    for k, f in enumerate(feedback):
        f = dict(zip(("from", "to"), f)) if not isinstance(f, dict) else dict(f)
        src, dst = str(f["from"]), ref(f["to"])
        head = f.get("head", "inhibit")
        lane = lane0 + k * fs * 1.3
        n = hits[dst] = hits.get(dst, 0) + 1
        _, dy_, _, dh, _, dr = nodes[dst]
        ty = dy_ + dh * (0.05 - 0.2 * (n - 1))
        c = accent if head == "inhibit" else ink
        if src in gene_ports:
            gcx, gly, *_rest = nodes[src]
            run = gly + fs * 1.05 + k * fs * 0.45
            pts = [(gcx, gly + fs * 0.7), (gcx, run), (lane, run), (lane, ty), (dr + 2, ty)]
        else:
            s_ = ref(src)
            _, sy_, _, sh, _, sr = nodes[s_]
            pts = [(sr + 2, sy_ + sh * 0.1), (lane, sy_ + sh * 0.1), (lane, ty), (dr + 2, ty)]
        under += _line(pts, c, sw, head, dashed=f.get("dashed", False))
        if f.get("label"):
            texts.append(
                _text(
                    lane + fs * 0.4, (pts[-2][1] + pts[-3][1]) / 2, f["label"], fs * 0.85, c, anchor="start", bold=False
                )
            )
            drug_right = max(drug_right, lane + fs * 0.4 + _tw(f["label"], fs * 0.85, bold=False))
        drug_right = max(drug_right, lane + sw)
    right_edge = max(drug_right, trunk_right) + fs * 0.4
    mem = _membrane_part(
        f"M0 {fmt(Ym)} L{fmt(right_edge)} {fmt(Ym)}", color=membrane_color, thickness=T, style=style, seed=seed
    ).element
    mem[0].attrib.pop("data-outline", None)
    if compartments:
        cc = "#8A8A96"
        labs = list(compartments) + [None] * 3
        if labs[0]:
            texts.append(_text(0, (Ym - T / 2) / 2, labs[0], fs * 0.85, cc, anchor="start", bold=False))
        if labs[1]:
            texts.append(_text(0, Ym + T / 2 + fs * 1.1, labs[1], fs * 0.85, cc, anchor="start", bold=False))
        if labs[2] and targets:
            texts.append(_text(0, nodes["nucleus"][1], labs[2], fs * 0.85, cc, anchor="start", bold=False))
    H = bottom + fs * 0.6
    holder.append(_el("rect", x=0, y=0, width=right_edge, height=H, fill="none", stroke="none", data_outline="1"))
    holder.append(mem)
    holder.extend(under)
    holder.extend(glyphs)
    if look is not None and len(look):
        holder.append(look)
    holder.extend(over)
    holder.extend(texts)
    ports = {}
    for k_, (cx_, cy_, w_, h_, l_, r_) in nodes.items():
        ports[k_] = (cx_, cy_)
        ports[f"{k_}_left"] = (l_, cy_)
        ports[f"{k_}_right"] = (r_, cy_)
    for s_name, key in names.items():
        for suf in ("", "_left", "_right"):
            ports.setdefault(s_name + suf, ports[key + suf])
    ports.update({g: p for g, p in gene_ports.items()})
    ports.update(drug_ports)
    ports.update(membrane=(comp_w / 2 if compartments else fs, Ym), receptor_out=(Xc, ecto_top))
    if targets:
        ports["dna"] = (Xc, dna_y)
    if str(receptor) not in ports:
        ports[str(receptor)] = ports["receptor"]
    return _finish(holder, defs, Box(0, 0, right_edge, H), **ports)
