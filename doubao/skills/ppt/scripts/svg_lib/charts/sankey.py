"""svg_lib/charts/sankey.py

统一 API: draw_sankey(data, variant, palette, ...) -> str (SVG)

Data schema:
    通用 (default_ribbon_flat / alluvial_sinusoidal / multi_layer_flat / gradient_layered):
        data = {
            "layers": [[node_names], [node_names], ...],  # 至少 2 层
            "inter_flows": [ [(src, dst, value), ...], ... ],  # len == len(layers) - 1
        }
    chord_circular 双向 schema:
        data = {"nodes": [str], "flows": [(src, dst, value), ...]}

    draw_sankey 自动分派：
      - variant=chord_circular 且缺 flows：从 layers/inter_flows 扁平化
      - variant≠chord_circular 且给了 nodes/flows：作为 2 层 sankey

Variants:
    - default_ribbon_flat   经典 bezier ribbon
    - alluvial_sinusoidal   S 曲线 alluvial (仅 2 层)
    - chord_circular        圆形 chord (双向)
    - multi_layer_flat       多层 flat
    - gradient_layered      带渐变 + 高光的 ribbon
"""
from __future__ import annotations
import math

from ._shared import (

    resolve_palette,
    xesc,
    auto_font_size,
    viewbox_fs,
    svg_open,
    svg_close,
    _rgba_with_alpha,
    rgb_tuple,
)


from .._common import (_ACC, _INK, _INK1, _INK2, _INK4, _INK6, _derive_series_colors, _prepend_bg_if_dark, _resolve_font, _resolve_palette, _rgb_tuple, _rgba_with_alpha, _xesc, _variant_is_classic, _dispatch_to_svg_lib)
BODY_FONT = "Inter, sans-serif"
HEAD_FONT = "Georgia, serif"


def draw_sankey(
    data: dict,
    variant: str = "default_ribbon_flat",
    palette: str = "archive_ink",
    width: float = 900,
    height: float = 540,
    title: str = None,
    subtitle: str = None,
) -> str:
    pal = resolve_palette(palette)

    # Dispatch on variant + schema
    if variant == "chord_circular":
        nodes, flows = _normalize_chord(data)
        body = _draw_chord_circular(nodes, flows, pal, width, height, title, subtitle)
    else:
        layers, inter_flows = _normalize_layered(data)
        if variant == "default_ribbon_flat":
            body = _draw_ribbon(layers, inter_flows, pal, width, height, title, subtitle,
                                curve="bezier", gradient=False)
        elif variant == "multi_layer_flat":
            # stepped/orthogonal ribbons for 2-3 layers; deep-layer data (>=4) falls
            # back to bezier because the stepped router self-intersects at midpoints
            # when hubs have many crossing flows. Flat-style visual (higher fill
            # opacity + node strokes + layer guide lines) keeps it distinct from
            # default_ribbon_flat regardless of the underlying curve.
            curve = "stepped" if len(layers) <= 3 else "bezier"
            body = _draw_ribbon(layers, inter_flows, pal, width, height, title, subtitle,
                                curve=curve, gradient=False, flat_style=True)
        elif variant == "gradient_layered":
            body = _draw_ribbon(layers, inter_flows, pal, width, height, title, subtitle,
                                curve="bezier", gradient=True)
        elif variant == "alluvial_sinusoidal":
            body = _draw_ribbon(layers, inter_flows, pal, width, height, title, subtitle,
                                curve="sinusoidal", gradient=False)
        else:
            raise ValueError(
                f"unknown variant {variant!r}. Supported: default_ribbon_flat, "
                "alluvial_sinusoidal, chord_circular, multi_layer_flat, gradient_layered"
            )
        # header is inside _draw_ribbon (as it needs its own layout)
        return (
            svg_open(0, 0, float(width), float(height), bg=pal["bg"])
            + body
            + svg_close()
        )

    # chord assembles its own header
    return (
        svg_open(0, 0, float(width), float(height), bg=pal["bg"])
        + body
        + svg_close()
    )


def _normalize_layered(data):
    """Handle both layered and nodes/flows schemas."""
    if "layers" in data and "inter_flows" in data:
        layers = data["layers"]
        inter = data["inter_flows"]
        if len(layers) < 2:
            raise ValueError("draw_sankey: layers needs at least 2 groups")
        if len(inter) != len(layers) - 1:
            raise ValueError(f"draw_sankey: inter_flows must have {len(layers)-1} entries")
        return layers, inter
    if "nodes" in data and "flows" in data:
        # collapse into 2 layers: src set + dst set
        nodes = data["nodes"]
        flows = data["flows"]
        srcs = []
        dsts = []
        for s, d, v in flows:
            if s not in srcs:
                srcs.append(s)
            if d not in dsts:
                dsts.append(d)
        # keep nodes ordering as list
        left = [n for n in nodes if n in srcs]
        right = [n for n in nodes if n in dsts]
        if not left:
            left = srcs
        if not right:
            right = dsts
        return [left, right], [flows]
    raise ValueError("draw_sankey: data must have layers+inter_flows or nodes+flows")


def _normalize_chord(data):
    """Return (nodes:list, flows:list of (src,dst,val))."""
    if "nodes" in data and "flows" in data:
        return list(data["nodes"]), list(data["flows"])
    if "layers" in data and "inter_flows" in data:
        # flatten all unique nodes and all flows
        nodes = []
        seen = set()
        for layer in data["layers"]:
            for n in layer:
                if n not in seen:
                    nodes.append(n)
                    seen.add(n)
        flows = []
        for step in data["inter_flows"]:
            for s, d, v in step:
                flows.append((s, d, v))
        return nodes, flows
    raise ValueError("draw_sankey: data must have nodes+flows or layers+inter_flows")


# ============================================================
# ribbon (bezier / sinusoidal) with optional gradient
# ============================================================
def _draw_ribbon(layers, inter_flows, pal, W, H, title, subtitle, curve="bezier", gradient=False, flat_style=False):
    W = float(W); H = float(H)
    ink = pal["ink"]; mut = pal["muted"]; bg = pal["bg"]
    series = pal.get("series") or [pal["accent"]]
    n_layers = len(layers)

    # Dynamic margins driven by longest label in the outer columns.
    # Round 1 raised MR from 130 to 200 for "PaidPremiumCustomers" (20 chars);
    # Round 2 (multi_layer) exposed >30 char labels like "recommendation-
    # personalization-svc" that also overflow the LEFT column and still exceed
    # MR=200 on the right. Compute margin from actual label length instead of
    # a static number so all 5 ribbon variants stay OOB=0 for realistic names.
    # Formula: char_count * fs * 0.62 (advance) + 15 * fs * 0.55 (tspan/value
    # slack — _draw_ribbon has no tspan today but the extra slack is harmless
    # and matches make_sankey's label layout) + 20px breathing room.
    longest_left = max((len(str(n)) for n in layers[0]), default=0)
    longest_right = max((len(str(n)) for n in layers[-1]), default=0)
    fs_label = 14
    ML = max(100, longest_left * fs_label * 0.62 + 15 * fs_label * 0.55 + 20)
    MR = max(200, longest_right * fs_label * 0.62 + 15 * fs_label * 0.55 + 20)
    header_h = 20
    if title:
        header_h = 44
    if subtitle:
        header_h += 18
    plot_top = header_h + 12
    plot_bot = H - 30
    plot_h = plot_bot - plot_top
    plot_w = W - ML - MR

    NODE_W = 12.0
    NODE_GAP = 8.0

    # Compute per-node totals (sum of in + out, use max side to avoid ambiguity)
    node_totals = []  # per layer: dict name -> total flow through
    for li in range(n_layers):
        totals = {name: 0.0 for name in layers[li]}
        if li > 0:
            for s, d, v in inter_flows[li - 1]:
                if d in totals:
                    totals[d] += v
        if li < n_layers - 1:
            out_total = {name: 0.0 for name in layers[li]}
            for s, d, v in inter_flows[li]:
                if s in out_total:
                    out_total[s] += v
            for name in totals:
                totals[name] = max(totals[name], out_total.get(name, 0))
        node_totals.append(totals)

    # scale so tallest column fits plot_h
    max_col = 0.0
    for li in range(n_layers):
        col_total = sum(node_totals[li].values())
        col_h = col_total  # scale later
        if col_total > max_col:
            max_col = col_total
    # per-layer per-node y position
    scale = (plot_h - NODE_GAP * (max(len(l) for l in layers) - 1)) / max(max_col, 1e-6)

    # layout each layer
    layer_pos = []  # per layer: dict name -> (y_top, y_bot)
    for li in range(n_layers):
        col_names = layers[li]
        col_totals_this = sum(node_totals[li].get(n, 0) for n in col_names)
        col_h = col_totals_this * scale + NODE_GAP * (len(col_names) - 1)
        y = plot_top + (plot_h - col_h) / 2
        pos = {}
        for name in col_names:
            h = max(2.0, node_totals[li].get(name, 0) * scale)
            pos[name] = (y, y + h)
            y += h + NODE_GAP
        layer_pos.append(pos)

    # per-node source & dest slot bookkeeping (for stacking flows within node)
    src_slots = [dict() for _ in range(n_layers)]  # per node: dict name -> next_y for outflow
    dst_slots = [dict() for _ in range(n_layers)]
    for li in range(n_layers):
        for name, (y0, y1) in layer_pos[li].items():
            src_slots[li][name] = y0
            dst_slots[li][name] = y0

    # color assignment: per src (source of ribbon)
    def color_for_left(name, li):
        idx = layers[li].index(name) if name in layers[li] else 0
        return series[idx % len(series)]

    parts = []
    defs = []

    # header
    if title:
        parts.append(
            f'<text x="{ML}" y="30" font-family="{HEAD_FONT}" font-size="20" '
            f'font-weight="600" fill="{ink}" letter-spacing=".03em">{xesc(title)}</text>'
        )
    if subtitle:
        y = 48 if title else 30
        parts.append(
            f'<text x="{ML}" y="{y}" font-family="{BODY_FONT}" font-size="11" '
            f'fill="{mut}" letter-spacing=".14em">{xesc(subtitle)}</text>'
        )
    if title:
        parts.append(
            f'<line x1="{ML}" y1="{header_h}" x2="{W - MR}" y2="{header_h}" '
            f'stroke="{ink}" stroke-width="0.6" opacity="0.4"/>'
        )

    # layer x positions
    if n_layers == 1:
        layer_x = [ML]
    else:
        layer_x = [ML + i * (plot_w - NODE_W) / (n_layers - 1) for i in range(n_layers)]

    # flat_style: faint vertical guide at each layer column (behind flows)
    if flat_style:
        for lx in layer_x:
            gx = lx + NODE_W / 2
            parts.append(
                f'<line x1="{gx:.1f}" y1="{plot_top:.1f}" x2="{gx:.1f}" y2="{plot_bot:.1f}" '
                f'stroke="{ink}" stroke-width="0.4" opacity="0.15"/>'
            )

    # draw flows first
    grad_id = [0]
    for li in range(n_layers - 1):
        x_src = layer_x[li] + NODE_W
        x_dst = layer_x[li + 1]
        for s, d, v in inter_flows[li]:
            if s not in layer_pos[li] or d not in layer_pos[li + 1]:
                continue
            h = v * scale
            y_s = src_slots[li][s]
            y_d = dst_slots[li + 1][d]
            src_slots[li][s] += h
            dst_slots[li + 1][d] += h
            col = color_for_left(s, li)

            if curve == "sinusoidal":
                d_path = _sinusoidal_ribbon(x_src, y_s, y_s + h, x_dst, y_d, y_d + h)
            elif curve == "stepped":
                d_path = _stepped_ribbon(x_src, y_s, y_s + h, x_dst, y_d, y_d + h)
            else:
                d_path = _bezier_ribbon(x_src, y_s, y_s + h, x_dst, y_d, y_d + h)

            if gradient:
                gid = f"__snk_grad_{grad_id[0]}"
                grad_id[0] += 1
                dst_col = color_for_left(d, li + 1) if d in layers[li + 1] else col
                r1, g1, b1 = rgb_tuple(col)
                r2, g2, b2 = rgb_tuple(dst_col)
                defs.append(
                    f'<linearGradient id="{gid}" x1="0%" y1="0%" x2="100%" y2="0%">'
                    f'<stop offset="0%" stop-color="rgba({r1},{g1},{b1},0.55)"/>'
                    f'<stop offset="100%" stop-color="rgba({r2},{g2},{b2},0.25)"/>'
                    f'</linearGradient>'
                )
                fill = f"url(#{gid})"
            elif flat_style:
                # denser fill for a solid "flat layered" look
                fill = _rgba_with_alpha(col, 0.55)
            else:
                fill = _rgba_with_alpha(col, 0.32)
            stroke = _rgba_with_alpha(col, 0.5)
            parts.append(
                f'<path d="{d_path}" fill="{fill}" stroke="{stroke}" stroke-width="0.4">'
                f'</path>'
            )

    # draw nodes on top
    max_col_total = max(sum(node_totals[li].values()) for li in range(n_layers))
    # 字号自适应：viewBox 尺寸 + 节点总数 n 双重驱动
    n_total_nodes = sum(len(l) for l in layers)
    fs = viewbox_fs(W, H, n_total_nodes, role_mult=1.05)
    for li in range(n_layers):
        for name, (y0, y1) in layer_pos[li].items():
            h = y1 - y0
            col = color_for_left(name, li)
            if flat_style:
                # solid fill + darker ink stroke — reads as a "flat block"
                parts.append(
                    f'<rect x="{layer_x[li]:.1f}" y="{y0:.1f}" width="{NODE_W}" height="{h:.1f}" '
                    f'fill="{col}" stroke="{ink}" stroke-width="1.4"/>'
                )
            else:
                parts.append(
                    f'<rect x="{layer_x[li]:.1f}" y="{y0:.1f}" width="{NODE_W}" height="{h:.1f}" '
                    f'fill="{_rgba_with_alpha(col, 0.9)}"/>'
                )
            # label placement: leftmost on left, rightmost on right, else on right of node
            if li == 0:
                # label left of node
                parts.append(
                    f'<text x="{layer_x[li] - 6:.1f}" y="{(y0 + y1) / 2 + 4:.1f}" '
                    f'text-anchor="end" font-family="{BODY_FONT}" font-size="{fs}" '
                    f'fill="{ink}" font-weight="600">{xesc(name)}</text>'
                )
            elif li == n_layers - 1:
                parts.append(
                    f'<text x="{layer_x[li] + NODE_W + 6:.1f}" y="{(y0 + y1) / 2 + 4:.1f}" '
                    f'text-anchor="start" font-family="{BODY_FONT}" font-size="{fs}" '
                    f'fill="{ink}" font-weight="600">{xesc(name)}</text>'
                )
            else:
                parts.append(
                    f'<text x="{layer_x[li] + NODE_W + 4:.1f}" y="{(y0 + y1) / 2 + 4:.1f}" '
                    f'text-anchor="start" font-family="{BODY_FONT}" font-size="{fs}" '
                    f'fill="{ink}" font-weight="600" '
                    f'paint-order="stroke" stroke="{bg}" stroke-width="2.4">{xesc(name)}</text>'
                )

    defs_svg = "<defs>" + "".join(defs) + "</defs>" if defs else ""
    return defs_svg + "".join(parts)


def _bezier_ribbon(x1, y1_top, y1_bot, x2, y2_top, y2_bot):
    """Classic sankey bezier ribbon (2 curves)."""
    xm = (x1 + x2) / 2
    d = (
        f"M {x1:.1f} {y1_top:.1f} "
        f"C {xm:.1f} {y1_top:.1f} {xm:.1f} {y2_top:.1f} {x2:.1f} {y2_top:.1f} "
        f"L {x2:.1f} {y2_bot:.1f} "
        f"C {xm:.1f} {y2_bot:.1f} {xm:.1f} {y1_bot:.1f} {x1:.1f} {y1_bot:.1f} "
        f"Z"
    )
    return d


def _sinusoidal_ribbon(x1, y1_top, y1_bot, x2, y2_top, y2_bot, n=32):
    """S-curve using (1-cos(pi*t))/2 as easing."""
    def edge(y1, y2):
        pts = []
        for i in range(n + 1):
            t = i / n
            s = 0.5 - 0.5 * math.cos(math.pi * t)
            x = x1 + t * (x2 - x1)
            y = y1 + s * (y2 - y1)
            pts.append((x, y))
        return pts

    top = edge(y1_top, y2_top)
    bot = edge(y1_bot, y2_bot)
    d = [f"M {top[0][0]:.1f} {top[0][1]:.1f}"]
    for x, y in top[1:]:
        d.append(f"L {x:.1f} {y:.1f}")
    d.append(f"L {bot[-1][0]:.1f} {bot[-1][1]:.1f}")
    for x, y in reversed(bot[:-1]):
        d.append(f"L {x:.1f} {y:.1f}")
    d.append("Z")
    return " ".join(d)


def _stepped_ribbon(x1, y1_top, y1_bot, x2, y2_top, y2_bot):
    """Orthogonal / stepped ribbon: horizontal from src, sharp vertical at midpoint, horizontal to dst.
    Corners rounded via short beziers for a clean layered look, distinct from bezier."""
    xm = (x1 + x2) / 2
    # small radius for corner smoothing
    r = min(6.0, abs(x2 - x1) * 0.08)
    d = (
        f"M {x1:.1f} {y1_top:.1f} "
        # top edge: go horizontal to (xm-r, y1_top), arc/curve to (xm, y1_top+/-r), vertical to (xm, y2_top-/+r), curve to (xm+r, y2_top), horizontal to x2
        f"L {xm - r:.1f} {y1_top:.1f} "
        f"Q {xm:.1f} {y1_top:.1f} {xm:.1f} {y1_top + (r if y2_top > y1_top else -r):.1f} "
        f"L {xm:.1f} {y2_top - (r if y2_top > y1_top else -r):.1f} "
        f"Q {xm:.1f} {y2_top:.1f} {xm + r:.1f} {y2_top:.1f} "
        f"L {x2:.1f} {y2_top:.1f} "
        # right vertical edge
        f"L {x2:.1f} {y2_bot:.1f} "
        # bottom edge back
        f"L {xm + r:.1f} {y2_bot:.1f} "
        f"Q {xm:.1f} {y2_bot:.1f} {xm:.1f} {y2_bot - (r if y2_bot > y1_bot else -r):.1f} "
        f"L {xm:.1f} {y1_bot + (r if y2_bot > y1_bot else -r):.1f} "
        f"Q {xm:.1f} {y1_bot:.1f} {xm - r:.1f} {y1_bot:.1f} "
        f"L {x1:.1f} {y1_bot:.1f} "
        f"Z"
    )
    return d


# ============================================================
# chord_circular
# ============================================================
def _draw_chord_circular(nodes, flows, pal, W, H, title=None, subtitle=None):
    W = float(W); H = float(H)
    ink = pal["ink"]; mut = pal["muted"]; bg = pal["bg"]
    series = pal.get("series") or [pal["accent"]]
    N = len(nodes)
    node_idx = {n: i for i, n in enumerate(nodes)}
    # normalize flows -> index-based
    idx_flows = []
    for s, d, v in flows:
        if s not in node_idx or d not in node_idx:
            continue
        idx_flows.append((node_idx[s], node_idx[d], float(v)))

    # totals
    totals = [0.0] * N
    for s, d, v in idx_flows:
        totals[s] += v
        totals[d] += v
    grand = sum(totals)
    if grand <= 0:
        raise ValueError("draw_sankey chord_circular: total flow is zero")

    # header/title padding at top
    ML = 60
    header_h = 20
    if title:
        header_h = 44
    if subtitle:
        header_h += 18
    top_pad = header_h + 12 if (title or subtitle) else 20

    # layout — shift circle down to leave room for title
    CX = W / 2
    avail_h = H - top_pad - 20
    CY = top_pad + avail_h / 2
    R_OUTER = min(W - 80, avail_h) * 0.42
    R_INNER = R_OUTER - 14
    R_RIBBON = R_INNER - 4

    GAP = math.radians(3)
    total_gap = GAP * N
    remaining = 2 * math.pi - total_gap
    node_angles = []
    cur = -math.pi / 2
    for i in range(N):
        span = remaining * (totals[i] / grand) if grand > 0 else 0
        node_angles.append((cur, cur + span))
        cur += span + GAP

    # slots per node: allocate arc segments per flow (out first, then in)
    slots = [[] for _ in range(N)]
    for i in range(N):
        outs = [(d, v) for (s, d, v) in idx_flows if s == i]
        ins = [(s, v) for (s, d, v) in idx_flows if d == i]
        a0, a1 = node_angles[i]
        if totals[i] == 0:
            continue
        acur = a0
        for other, v in outs:
            span = (a1 - a0) * (v / totals[i])
            slots[i].append({"a0": acur, "a1": acur + span, "other": other, "value": v, "is_src": True})
            acur += span
        for other, v in ins:
            span = (a1 - a0) * (v / totals[i])
            slots[i].append({"a0": acur, "a1": acur + span, "other": other, "value": v, "is_src": False})
            acur += span

    def polar(r, a):
        return (CX + r * math.cos(a), CY + r * math.sin(a))

    def arc_frag(r, a0, a1, sweep=1):
        x1, y1 = polar(r, a1)
        large = 1 if abs(a1 - a0) > math.pi else 0
        return f"A {r} {r} 0 {large} {sweep} {x1:.2f} {y1:.2f}"

    def find_slot(node_i, other, is_src, val):
        for sl in slots[node_i]:
            if sl["other"] == other and sl["is_src"] == is_src and abs(sl["value"] - val) < 1e-6:
                return sl
        return None

    node_colors = [series[i % len(series)] for i in range(N)]

    parts = []

    # header (title + subtitle + divider)
    if title:
        parts.append(
            f'<text x="{ML}" y="30" font-family="{HEAD_FONT}" font-size="20" '
            f'font-weight="600" fill="{ink}" letter-spacing=".03em">{xesc(title)}</text>'
        )
    if subtitle:
        y_sub = 48 if title else 30
        parts.append(
            f'<text x="{ML}" y="{y_sub}" font-family="{BODY_FONT}" font-size="11" '
            f'fill="{mut}" letter-spacing=".14em">{xesc(subtitle)}</text>'
        )
    if title:
        parts.append(
            f'<line x1="{ML}" y1="{header_h}" x2="{W - ML}" y2="{header_h}" '
            f'stroke="{ink}" stroke-width="0.6" opacity="0.4"/>'
        )

    # draw ribbons
    for s, d, v in idx_flows:
        s_slot = find_slot(s, d, True, v)
        d_slot = find_slot(d, s, False, v)
        if s_slot is None or d_slot is None:
            continue
        sa0, sa1 = s_slot["a0"], s_slot["a1"]
        da0, da1 = d_slot["a0"], d_slot["a1"]

        p_s0 = polar(R_RIBBON, sa0)
        p_d0 = polar(R_RIBBON, da0)

        PULL = 0.55
        s_mid = (sa0 + sa1) / 2
        d_mid = (da0 + da1) / 2
        r_ctrl = R_RIBBON * PULL
        cps_x = CX + r_ctrl * math.cos(s_mid)
        cps_y = CY + r_ctrl * math.sin(s_mid)
        cpd_x = CX + r_ctrl * math.cos(d_mid)
        cpd_y = CY + r_ctrl * math.sin(d_mid)

        path = (
            f"M {p_s0[0]:.2f} {p_s0[1]:.2f} "
            f"{arc_frag(R_RIBBON, sa0, sa1)} "
            f"C {cps_x:.2f} {cps_y:.2f} {cpd_x:.2f} {cpd_y:.2f} {p_d0[0]:.2f} {p_d0[1]:.2f} "
            f"{arc_frag(R_RIBBON, da0, da1)} "
            f"C {cpd_x:.2f} {cpd_y:.2f} {cps_x:.2f} {cps_y:.2f} {p_s0[0]:.2f} {p_s0[1]:.2f} "
            f"Z"
        )
        col = node_colors[s]
        parts.append(
            f'<path d="{path}" fill="{_rgba_with_alpha(col, 0.34)}" '
            f'stroke="{_rgba_with_alpha(col, 0.5)}" stroke-width="0.4">'
            f'</path>'
        )

    # outer arcs (bands)
    for i in range(N):
        a0, a1 = node_angles[i]
        if a1 - a0 < 1e-6:
            continue
        col = node_colors[i]
        p_out0 = polar(R_OUTER, a0)
        p_out1 = polar(R_OUTER, a1)
        p_in0 = polar(R_INNER, a0)
        p_in1 = polar(R_INNER, a1)
        large = 1 if (a1 - a0) > math.pi else 0
        band = (
            f"M {p_out0[0]:.2f} {p_out0[1]:.2f} "
            f"A {R_OUTER} {R_OUTER} 0 {large} 1 {p_out1[0]:.2f} {p_out1[1]:.2f} "
            f"L {p_in1[0]:.2f} {p_in1[1]:.2f} "
            f"A {R_INNER} {R_INNER} 0 {large} 0 {p_in0[0]:.2f} {p_in0[1]:.2f} "
            f"Z"
        )
        parts.append(f'<path d="{band}" fill="{col}" stroke="none"/>')

        # label
        a_mid = (a0 + a1) / 2
        r_lbl = R_OUTER + 18
        lx = CX + r_lbl * math.cos(a_mid)
        ly = CY + r_lbl * math.sin(a_mid)
        deg = math.degrees(a_mid) % 360
        anchor = "start" if (deg < 90 or deg > 270) else "end"
        fs = viewbox_fs(W, H, N, role_mult=1.05)
        fs_val = viewbox_fs(W, H, N, role_mult=0.9)
        parts.append(
            f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}" '
            f'dominant-baseline="middle" font-family="{BODY_FONT}" '
            f'font-size="{fs}" font-weight="600" fill="{ink}">{xesc(nodes[i])}</text>'
        )
        parts.append(
            f'<text x="{lx:.1f}" y="{ly + fs + 2:.1f}" text-anchor="{anchor}" '
            f'dominant-baseline="middle" font-family="{BODY_FONT}" '
            f'font-size="{fs_val}" fill="{mut}">{int(totals[i]):,}</text>'
        )

    # center label
    parts.append(
        f'<text x="{CX:.1f}" y="{CY - 4:.1f}" text-anchor="middle" '
        f'dominant-baseline="middle" font-family="{HEAD_FONT}" font-size="16" '
        f'font-weight="600" fill="{ink}">{int(grand):,}</text>'
    )
    parts.append(
        f'<text x="{CX:.1f}" y="{CY + 14:.1f}" text-anchor="middle" '
        f'dominant-baseline="middle" font-family="{BODY_FONT}" font-size="9" '
        f'fill="{mut}" letter-spacing=".18em">TOTAL FLOWS</text>'
    )

    return "".join(parts)


def make_sankey(left_nodes=None,
                right_nodes=None,
                flows=None,
                layers: list = None,
                inter_flows: list = None,
                layer_titles: list = None,
                title: str = None,
                subtitle: str = None,
                figure_label: str = None,
                note: str = None,
                source: str = None,
                node_gap: float = 18.0,
                node_width: float = 14.0,
                width: float = 1200.0,
                height: float = 760.0,
                font_family: str = None,
                palette=None,
                variant: str = None) -> str:
    """
    桑基图 · dandelion academic 风格（支持任意层数）。

    两种输入：
    A) **多层（新 API）**：
       layers = [
         ["Organic","Paid","Social","Referral","Direct"],   # layer 0 节点名
         ["Signed Up","Browsed","Purchased","Left"],        # layer 1
         ["Active","Converted","Occasional","Churned"],     # layer 2
       ]
       inter_flows = [
         [ (src_name, dst_name, value), ... ],   # layer 0 → layer 1 的 flow
         [ (src_name, dst_name, value), ... ],   # layer 1 → layer 2 的 flow
       ]
       # len(inter_flows) == len(layers) - 1
       # 每层内相邻 (src, dst) 若 value=0 可省略

    B) **两层（老 API 兼容）**：
       left_nodes = [...], right_nodes = [...], flows = [(src, dst, value), ...]

    layer_titles: 每层顶部大写小字（可选）
    title/subtitle/figure_label: 顶部标题
    note/source: 底部脚注

    palette: 用 palette.series 或 accent 派生每层节点色
    """
    if not _variant_is_classic('sankey', variant):
        _data = ({"layers": layers, "inter_flows": inter_flows} if layers is not None and inter_flows is not None else {"layers": [left_nodes or [], right_nodes or []], "inter_flows": [flows or []]})
        return _dispatch_to_svg_lib(
            'sankey', variant, _data,
            title=title, subtitle=subtitle, figure_label=figure_label,
            palette=palette, font_family=font_family,
        )

    # ---------- API 归一化 ----------
    if layers is None:
        # 老 API 模式
        if left_nodes is None or right_nodes is None or flows is None:
            raise ValueError("sankey: need either `layers` (multi-layer) or `left_nodes/right_nodes/flows` (2-layer)")
        layers = [list(left_nodes), list(right_nodes)]
        inter_flows = [list(flows)]
    else:
        if inter_flows is None:
            raise ValueError("sankey: `inter_flows` required when `layers` given")
        if len(inter_flows) != len(layers) - 1:
            raise ValueError(f"sankey: inter_flows must have {len(layers)-1} groups, got {len(inter_flows)}")

    n_layers = len(layers)
    if n_layers < 2:
        raise ValueError(f"sankey: need at least 2 layers, got {n_layers}")

    _pal = _resolve_palette(palette)
    _body_font, _head_font = _resolve_font(font_family)
    _INK, _INK6, _INK4, _INK2, _INK1, _ACC = (
        _pal["ink"], _pal["ink6"], _pal["ink4"], _pal["ink2"], _pal["ink1"], _pal["accent"]
    )
    c_muted = _pal.get("muted", _rgba_with_alpha(_INK, 0.6))
    c_secondary = _pal.get("secondary", _rgba_with_alpha(_INK, 0.5))
    c_bg = _pal.get("bg")
    PAPER = c_bg if c_bg else "rgba(250,248,242,1)"

    # 校验流量守恒（相邻层的 dst 入流 = 下一层出流）—— 除首末层外
    # 计算每个节点的 in/out flow
    def _flow_dict(fl):
        d = {}
        for t in fl:
            if len(t) < 3:
                raise ValueError(f"sankey: flow entry must be (src, dst, value): {t}")
            s, dst, v = t[0], t[1], float(t[2])
            if v < 0:
                raise ValueError(f"sankey: flow value must be ≥ 0: {t}")
            if v == 0:
                continue
            d.setdefault(s, {})[dst] = d.get(s, {}).get(dst, 0) + v
        return d
    flow_dicts = [_flow_dict(fl) for fl in inter_flows]

    # 每层节点的 total flow：入流 vs 出流
    layer_totals = []
    for li in range(n_layers):
        totals = {}
        for name in layers[li]:
            in_sum = 0.0
            out_sum = 0.0
            if li > 0:
                # 入流
                for src in layers[li-1]:
                    in_sum += flow_dicts[li-1].get(src, {}).get(name, 0)
            if li < n_layers - 1:
                # 出流
                out_sum = sum(flow_dicts[li].get(name, {}).values())
            # 中间层用 max(in, out)（应该守恒，但取 max 兜底）
            if li == 0:
                totals[name] = out_sum
            elif li == n_layers - 1:
                totals[name] = in_sum
            else:
                totals[name] = max(in_sum, out_sum)
        layer_totals.append(totals)

    # 全局 N（第一层 total）
    total_n = sum(layer_totals[0].values()) if layer_totals[0] else 0

    # ---------- 派生每层节点色 ----------
    # 第一层用 palette.series（distinct）；后续层用中性灰阶（学术风）
    # 除非用户在 palette 里定义 sankey_layer_colors=[[...],...] 精确控制
    explicit_colors = _pal.get("sankey_layer_colors")
    layer_node_colors = []
    for li in range(n_layers):
        n_nodes = len(layers[li])
        if explicit_colors and li < len(explicit_colors) and len(explicit_colors[li]) >= n_nodes:
            layer_node_colors.append(list(explicit_colors[li][:n_nodes]))
        elif li == 0:
            layer_node_colors.append(_derive_series_colors(_pal, n_nodes, mode="distinct"))
        else:
            # 中间/末层：用同色系灰阶 + 微 hue shift 让相邻可辨
            # 用 ink 派生的灰阶为主，最后一层用 series 分色
            if li == n_layers - 1:
                layer_node_colors.append(_derive_series_colors(_pal, n_nodes, mode="distinct"))
            else:
                # 中间层：ink 60/70/80% alpha 灰阶
                mid_cols = []
                for k in range(n_nodes):
                    # 从 ink 到 muted 灰调
                    t = 0.3 + 0.4 * (k / max(1, n_nodes-1))
                    r, g, b = _rgb_tuple(_INK)
                    mid_cols.append(f"rgba({r},{g},{b},{t:.2f})")
                layer_node_colors.append(mid_cols)

    # ---------- 画布 & 布局 ----------
    # Dynamic outer margins based on **actual** label strings on the outer columns.
    # Round 1 fixed the right side (MARGIN_R 130 -> 200) for ~20-char names but
    # Round 2 multi_layer flow exposed >30 char names ("recommendation-
    # personalization-svc") that still overflow, and the left side was never
    # raised. Round 3 (this): value magnitude (e.g. 420,000) blew past the
    # fixed `_val_chars=15` upper bound because the concatenated label
    # `<name>  <total>  ·  <pct>%` is what the OOB linter measures (as a
    # single text via itertext), so we now build the exact strings from the
    # already-computed layer_totals and total_n, estimate width using the
    # validator's own per-glyph model, and clamp margin above.
    # The outer <text> also gets font-size=fs_node explicitly (below in the
    # node-drawing loop) so validator width tracks real render.
    _fs_name = 20   # matches fs_node upper bound below
    _fs_val = 15    # matches fs_nval upper bound below

    # Use the validator's own width model so what we reserve equals what the
    # OOB linter measures. If import fails (e.g. running outside the patched
    # skill), fall back to a conservative built-in estimate.
    try:
        from embed_svg_validator import _svg_text_width as _val_text_width
    except Exception:
        _val_text_width = None

    def _est_str_w(s, fs, bold=False):
        if _val_text_width is not None:
            return _val_text_width(s, fs, 0.0, bold, _body_font)
        # Fallback: coarse advance model roughly matching Inter sans.
        w = 0.0
        b = 1.05 if bold else 1.0
        for c in s:
            if c == " ": w += fs * 0.33 * b
            elif c == "%": w += fs * 0.85 * b
            elif c.isdigit(): w += fs * 0.58 * b
            elif c.isupper(): w += fs * 0.72 * b   # conservative wide-letter avg
            elif c.islower(): w += fs * 0.55 * b
            else: w += fs * 0.50 * b
        return w

    def _label_str(name, total_val):
        pct = (total_val / total_n * 100) if total_n > 0 else 0
        sub = f"{int(total_val):,}"
        if total_n > 0:
            sub += f"  ·  {pct:.1f}%"
        # actual concatenated text as the validator sees it (matches
        # "".join(node.itertext()).strip() from _svg_visual_bbox)
        return f"{name}  {sub}"

    def _col_max_label_width(col_names, col_totals, fs_name, fs_val):
        """Return max estimated **visual** width per label in this column.
        Uses tspan-specific sizes: name at fs_name (bold), value at fs_val (regular).
        This is what the human sees; the validator uses the outer-text size instead
        (see _col_max_flat_width). We take max(visual, flat) for the margin.
        """
        best = 0.0
        for nm in col_names:
            tv = col_totals.get(nm, 0)
            pct = (tv / total_n * 100) if total_n > 0 else 0
            sub = f"{int(tv):,}"
            if total_n > 0:
                sub += f"  ·  {pct:.1f}%"
            w_name = _est_str_w(str(nm), fs_name, bold=True)
            w_sep = _est_str_w("  ", fs_val)
            w_sub = _est_str_w(sub, fs_val)
            best = max(best, w_name + w_sep + w_sub)
        return best

    def _col_max_flat_width(col_names, col_totals, flat_fs):
        """Return the width the OOB linter will compute for the outer <text>.
        Validator reads outer-text font-size (we set it to fs_node) and applies
        it to the whole itertext-joined string with the outer font-weight
        (unset -> not bold).
        """
        best = 0.0
        for nm in col_names:
            tv = col_totals.get(nm, 0)
            full = _label_str(nm, tv)
            best = max(best, _est_str_w(full, flat_fs, bold=False))
        return best

    _left_names = layers[0]
    _right_names = layers[-1]
    _left_totals = layer_totals[0]
    _right_totals = layer_totals[-1]

    _left_visual = _col_max_label_width(_left_names, _left_totals, _fs_name, _fs_val)
    _right_visual = _col_max_label_width(_right_names, _right_totals, _fs_name, _fs_val)
    # Validator sees the outer <text> font-size, which we now force to fs_node
    # (its upper bound = _fs_name = 20). Use that for the flat estimate.
    _left_flat = _col_max_flat_width(_left_names, _left_totals, _fs_name)
    _right_flat = _col_max_flat_width(_right_names, _right_totals, _fs_name)

    # Padding: covers the tx offset (lx +/- 8), rounding, and small safety
    # margin. The label anchor sits at (lx +/- 8) so the effective reserved
    # column width is MARGIN_[L|R] - 8, hence extra +12 to keep OOB ≥ 4px.
    _label_pad = 24
    MARGIN_L = int(math.ceil(max(200, max(_left_visual, _left_flat) + _label_pad)))
    MARGIN_R = int(math.ceil(max(200, max(_right_visual, _right_flat) + _label_pad)))
    MARGIN_T = 165 if title else 80
    MARGIN_B = 100 if (note or source) else 60

    plot_top = MARGIN_T
    plot_bottom = height - MARGIN_B
    plot_h = plot_bottom - plot_top
    plot_left = MARGIN_L
    plot_right = width - MARGIN_R

    # 层 x 位置：均匀分布
    if n_layers == 1:
        layer_xs = [plot_left]
    else:
        step = (plot_right - plot_left) / (n_layers - 1)
        layer_xs = [plot_left + i * step for i in range(n_layers)]

    # ---------- 字号自适应基准 ----------
    # 密度指标：单列最多节点数 → 单节点平均高度
    # 基准：6 节点/列 · plot_h ≈ 495 · node_gap=18 → 节点高 ≈ 65px（此时 scale=1.0，节点名 14pt）
    _max_col_nodes = max(len(layers[li]) for li in range(n_layers))
    _est_node_h = max(20.0, (plot_h - node_gap * max(0, _max_col_nodes - 1)) / max(1, _max_col_nodes))
    _fs_scale = max(0.75, min(1.8, _est_node_h / 65.0))
    # 上限保护
    fs_title    = round(min(32.0, 26 * _fs_scale), 1)
    fs_subtitle = round(min(15.0, 12 * _fs_scale), 1)
    fs_figure   = round(min(12.0, 10 * _fs_scale), 1)
    fs_layer    = round(min(13.0, 10 * _fs_scale), 1)   # 层标题
    fs_node     = round(min(20.0, 15 * _fs_scale), 1)   # 节点名（单行布局，可以更大）
    fs_nval     = round(min(15.0, 11 * _fs_scale), 1)   # 节点数值
    fs_foot     = round(min(11.0, 9.5 * _fs_scale), 1)

    # 每层节点垂直位置
    def layout_column(items, totals):
        total_flow = sum(totals[n] for n in items)
        if total_flow <= 0:
            total_flow = 1
        n = len(items)
        available_h = plot_h - node_gap * max(0, n - 1)
        scale = available_h / total_flow
        y = plot_top
        pos = {}
        for name in items:
            h = totals[name] * scale
            pos[name] = (y, y + h)
            y += h + node_gap
        return pos, scale

    # 用全局 scale（所有层用同一 scale，让流带宽度可比）
    # 找出最大层 total 作为 scale 参考
    max_col_total = max(sum(t.values()) for t in layer_totals)
    if max_col_total <= 0:
        max_col_total = 1
    # 每层单独 layout（gap 数量不同）
    layer_positions = []
    scales = []
    for li in range(n_layers):
        totals = layer_totals[li]
        items = layers[li]
        # 用全局 scale
        n_nodes = len(items)
        # 用相同 scale
        # scale = available_h / total_flow_of_max_layer
        scale = (plot_h - node_gap * max(0, n_nodes - 1)) / max_col_total
        y = plot_top
        pos = {}
        # vertically center: 计算当前层 total 高度，往下偏移居中
        cur_total_h = sum(totals[n] for n in items) * scale + node_gap * max(0, n_nodes - 1)
        y = plot_top + (plot_h - cur_total_h) / 2
        for name in items:
            h = totals[name] * scale
            pos[name] = (y, y + h)
            y += h + node_gap
        layer_positions.append(pos)
        scales.append(scale)

    # 每个节点内部 in/out segment 位置
    # out_segments[li][node] = { dst: (y_top, y_bot) }  用于绘制右侧出流带的起点
    # in_segments[li][node]  = { src: (y_top, y_bot) }  用于绘制左侧入流带的终点
    out_segments = [{} for _ in range(n_layers)]
    in_segments = [{} for _ in range(n_layers)]
    for li in range(n_layers):
        for name in layers[li]:
            y0, y1 = layer_positions[li][name]
            # 出流 segments：按下一层 dst 顺序堆叠
            if li < n_layers - 1:
                scale = scales[li]
                y = y0
                out_segments[li][name] = {}
                for dst in layers[li+1]:
                    v = flow_dicts[li].get(name, {}).get(dst, 0)
                    if v > 0:
                        h = v * scale
                        out_segments[li][name][dst] = (y, y + h)
                        y += h
            # 入流 segments：按上一层 src 顺序堆叠
            if li > 0:
                scale = scales[li]
                y = y0
                in_segments[li][name] = {}
                for src in layers[li-1]:
                    v = flow_dicts[li-1].get(src, {}).get(name, 0)
                    if v > 0:
                        h = v * scale
                        in_segments[li][name][src] = (y, y + h)
                        y += h

    parts = []

    if c_bg:
        parts.append(f'<rect width="{width}" height="{height}" fill="{PAPER}"/>')

    # 顶部
    # y 位置跟字号联动，避免大 scale 时挤
    _y_title    = 20 + fs_title
    _y_subtitle = _y_title + fs_title * 0.55 + fs_subtitle
    _y_line     = _y_subtitle + 12
    _y_figure   = _y_line + 14 + fs_figure * 0.5
    if title:
        parts.append(f'<text x="{MARGIN_L}" y="{_y_title:.1f}" '
                     f'font-family="{_head_font}" '
                     f'font-size="{fs_title}" font-weight="600" fill="{_INK}" letter-spacing=".05em">'
                     f'{_xesc(title)}</text>')
    if subtitle:
        parts.append(f'<text x="{MARGIN_L}" y="{_y_subtitle:.1f}" '
                     f'font-family="{_body_font}" font-size="{fs_subtitle}" fill="{c_muted}" '
                     f'letter-spacing=".16em">{_xesc(subtitle)}</text>')
        parts.append(f'<line x1="{MARGIN_L}" y1="{_y_line:.1f}" x2="{width-MARGIN_R}" y2="{_y_line:.1f}" '
                     f'stroke="{_INK}" stroke-width="0.8"/>')
    if figure_label:
        parts.append(f'<text x="{MARGIN_L}" y="{_y_figure:.1f}" font-family="{_body_font}" font-size="{fs_figure}" '
                     f'fill="{c_muted}" font-weight="600" letter-spacing=".15em">{_xesc(figure_label)}</text>')
        lbl_w = max(72, len(figure_label) * 8 + 20)
        note_txt = f"{n_layers}-layer Sankey · N={int(total_n):,}" if total_n else f"{n_layers}-layer Sankey"
        parts.append(f'<text x="{MARGIN_L+lbl_w}" y="{_y_figure:.1f}" font-family="{_body_font}" font-size="{fs_figure}" '
                     f'fill="{c_muted}" letter-spacing=".04em">{_xesc(note_txt)}</text>')

    # 层标题（大写小字）
    if layer_titles:
        for li, lt in enumerate(layer_titles):
            if lt is None or lt == "":
                continue
            lx = layer_xs[li]
            anchor = "start" if li == 0 else ("end" if li == n_layers - 1 else "middle")
            if li == 0:
                tx = lx
            elif li == n_layers - 1:
                tx = lx + node_width
            else:
                tx = lx + node_width / 2
            parts.append(f'<text x="{tx:.1f}" y="{MARGIN_T-24}" text-anchor="{anchor}" '
                         f'font-family="{_body_font}" font-size="{fs_layer}" font-weight="600" '
                         f'fill="{_INK}" letter-spacing=".16em">{_xesc(str(lt).upper())}</text>')

    # ---------- 画流带 ----------
    def ribbon_path(x1, y1_top, y1_bot, x2, y2_top, y2_bot):
        xc = (x1 + x2) / 2
        return (f'M {x1:.1f} {y1_top:.1f} '
                f'C {xc:.1f} {y1_top:.1f} {xc:.1f} {y2_top:.1f} {x2:.1f} {y2_top:.1f} '
                f'L {x2:.1f} {y2_bot:.1f} '
                f'C {xc:.1f} {y2_bot:.1f} {xc:.1f} {y1_bot:.1f} {x1:.1f} {y1_bot:.1f} '
                f'Z')

    for li in range(n_layers - 1):
        src_layer = layers[li]
        dst_layer = layers[li + 1]
        # 用源层节点色（第一段用 layer0 色，后续段可选用左侧节点色或用中间灰）
        # 学术风：第一段用 layer 0 色（source 色）；后续段用左侧当前层节点色
        for si, s in enumerate(src_layer):
            col = layer_node_colors[li][si]
            for d in dst_layer:
                v = flow_dicts[li].get(s, {}).get(d, 0)
                if v <= 0:
                    continue
                seg_from = out_segments[li][s].get(d)
                seg_to = in_segments[li+1][d].get(s)
                if seg_from is None or seg_to is None:
                    continue
                x1 = layer_xs[li] + node_width
                x2 = layer_xs[li+1]
                y1t, y1b = seg_from
                y2t, y2b = seg_to
                d_path = ribbon_path(x1, y1t, y1b, x2, y2t, y2b)
                # 半透明填色 + 淡描边
                fill_col = _rgba_with_alpha(col, 0.32)
                stroke_col = _rgba_with_alpha(col, 0.55)
                parts.append(f'<path d="{d_path}" fill="{fill_col}" stroke="{stroke_col}" '
                             f'stroke-width="0.4">'
                             f'</path>')

    # ---------- 画节点 ----------
    for li in range(n_layers):
        items = layers[li]
        for ni, name in enumerate(items):
            y0, y1 = layer_positions[li][name]
            col = layer_node_colors[li][ni]
            lx = layer_xs[li]
            parts.append(f'<rect x="{lx:.1f}" y="{y0:.1f}" width="{node_width}" height="{y1-y0:.1f}" '
                         f'fill="{_rgba_with_alpha(col, 0.9)}"/>')
            # 顶端 2px accent 条
            parts.append(f'<rect x="{lx:.1f}" y="{y0:.1f}" width="{node_width}" height="2" '
                         f'fill="{col}"/>')

            # 标签位置
            total_val = layer_totals[li].get(name, 0)
            pct = (total_val / total_n * 100) if total_n > 0 else 0
            yc = (y0 + y1) / 2

            if li == 0:
                # 左列：标签左侧
                tx = lx - 8
                anchor = "end"
                use_stroke = False
            elif li == n_layers - 1:
                # 右列：标签右侧
                tx = lx + node_width + 8
                anchor = "start"
                use_stroke = False
            else:
                # 中间列：标签放右侧（压带子），加白描边
                tx = lx + node_width + 6
                anchor = "start"
                use_stroke = True

            # 数值文本
            sub_txt = f"{int(total_val):,}"
            if total_n > 0:
                sub_txt += f"  ·  {pct:.1f}%"

            # 节点名 + 数值：同一行、用 tspan 排布，数值放在"离图更近"的一侧
            # anchor=end（左列）：数值在节点名之后（视觉在节点名右侧、靠近节点）
            # anchor=start（右列/中间列）：数值在节点名之后（节点名右、数值再右）
            # baseline 与原节点名对齐（yc - 4）
            stroke_attr = f' paint-order="stroke" stroke="{PAPER}" stroke-width="3" stroke-linejoin="round"' if use_stroke else ''
            # 用两个独立 <text> 而不是 <text> 内两个 <tspan>——避免服务端 pretty-print
            # 时在 tspan 之间插入换行/缩进空白，导致 lint 用 itertext() 拿到长串后按外层
            # font-size 高估宽度触发 embed_svg_out_of_bounds。
            # 名字放靠近节点、数值往外偏移一个"名字宽度 + gap"或"数值宽度 + gap"的距离。
            def _approx_w(s, fs, bold=False):
                b = 1.05 if bold else 1.0
                w = 0.0
                for c in s:
                    if c == " ": w += fs * 0.33 * b
                    elif c == "%": w += fs * 0.85 * b
                    elif c.isdigit(): w += fs * 0.58 * b
                    elif c.isupper(): w += fs * 0.72 * b
                    elif c.islower(): w += fs * 0.55 * b
                    else: w += fs * 0.50 * b
                return w
            name_w = _approx_w(str(name), fs_node, bold=True)
            sub_w = _approx_w(sub_txt, fs_nval)
            gap = 6
            y_lbl = yc + fs_node * 0.35
            if anchor == "end":
                # 左列右对齐：sub 在最左，name 靠近节点在最右
                # name 在 tx；sub 在 tx - (name_w + gap)
                parts.append(
                    f'<text x="{tx:.1f}" y="{y_lbl:.1f}" text-anchor="end" '
                    f'font-family="{_body_font}" font-size="{fs_node}" font-weight="600" '
                    f'fill="{_INK}"{stroke_attr}>{_xesc(str(name))}</text>'
                )
                parts.append(
                    f'<text x="{tx - name_w - gap:.1f}" y="{y_lbl:.1f}" text-anchor="end" '
                    f'font-family="{_body_font}" font-size="{fs_nval}" '
                    f'fill="{c_muted}"{stroke_attr}>{_xesc(sub_txt)}</text>'
                )
            else:
                # 右列/中间列左对齐：name 在最左靠近节点，sub 在 name 之右
                parts.append(
                    f'<text x="{tx:.1f}" y="{y_lbl:.1f}" text-anchor="start" '
                    f'font-family="{_body_font}" font-size="{fs_node}" font-weight="600" '
                    f'fill="{_INK}"{stroke_attr}>{_xesc(str(name))}</text>'
                )
                parts.append(
                    f'<text x="{tx + name_w + gap:.1f}" y="{y_lbl:.1f}" text-anchor="start" '
                    f'font-family="{_body_font}" font-size="{fs_nval}" '
                    f'fill="{c_muted}"{stroke_attr}>{_xesc(sub_txt)}</text>'
                )

    # 底部脚注
    if note or source:
        foot_y = height - 45
        parts.append(f'<line x1="{MARGIN_L}" y1="{foot_y-14}" x2="{width-MARGIN_R}" y2="{foot_y-14}" '
                     f'stroke="{_INK4}" stroke-width="0.5"/>')
        if note:
            parts.append(f'<text x="{MARGIN_L}" y="{foot_y}" font-family="{_body_font}" '
                         f'font-size="{fs_foot}" fill="{c_muted}">'
                         f'<tspan font-weight="600">Notes.</tspan> {_xesc(note)}</text>')
        if source:
            parts.append(f'<text x="{MARGIN_L}" y="{foot_y+14}" font-family="{_body_font}" '
                         f'font-size="{fs_foot}" fill="{c_muted}">'
                         f'<tspan font-weight="600">Source.</tspan> {_xesc(source)}</text>')
        if figure_label:
            parts.append(f'<text x="{width-MARGIN_R}" y="{foot_y+14}" text-anchor="end" '
                         f'font-family="{_body_font}" font-size="{fs_foot}" fill="{c_muted}" '
                         f'letter-spacing=".05em">{_xesc(figure_label)}</text>')

    body = "".join(parts)
    _svg_result = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {int(width)} {int(height)}">{body}</svg>'
    return _prepend_bg_if_dark(_svg_result, _pal)



