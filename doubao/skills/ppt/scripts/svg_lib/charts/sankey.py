"""统一 API: draw_sankey(data, variant, palette, ...) -> str (SVG)"""

from __future__ import annotations

import math

from .._common import (
    _legacy_inks,
    _derive_series_colors,
    _dispatch_to_svg_lib,
    _prepend_bg_if_dark,
    _resolve_font,
    _resolve_palette,
    _rgb_tuple,
    _rgba_with_alpha,
    _variant_is_classic,
    _xesc,
)
from .._typography import chart_font_sizes
from ._shared import (
    notes_source_footer,
    tr,
    resolve_palette,
    rgb_tuple,
    svg_close,
    svg_open,
    viewbox_fs,
    xesc,
)

BODY_FONT = "Inter, sans-serif"
HEAD_FONT = "Georgia, serif"


def draw_sankey(
    data: dict,
    variant: str = "default_ribbon_flat",
    palette: str = "archive_ink",
    width: float = 900,
    height: float = 540,
    title: str | None = None,
    subtitle: str | None = None,
) -> str:
    pal = resolve_palette(palette)

    if variant == "chord_circular":
        nodes, flows = _normalize_chord(data)
        height = _chord_canvas_height(nodes, flows, data.get("tracks"), pal, width, height, title, subtitle)
        body = _draw_chord_circular(nodes, flows, pal, width, height, title, subtitle, tracks=data.get("tracks"))
    else:
        layers, inter_flows = _normalize_layered(data)
        if variant == "default_ribbon_flat":
            body = _draw_ribbon(
                layers, inter_flows, pal, width, height, title, subtitle, curve="bezier", gradient=False
            )
        elif variant == "multi_layer_flat":
            # stepped/orthogonal ribbons for 2-3 layers; deep-layer data (>=4) falls
            # back to bezier because the stepped router self-intersects at midpoints
            # when hubs have many crossing flows. Flat-style visual (higher fill
            # opacity + node strokes + layer guide lines) keeps it distinct from
            # default_ribbon_flat regardless of the underlying curve.
            curve = "stepped" if len(layers) <= 3 else "bezier"
            body = _draw_ribbon(
                layers, inter_flows, pal, width, height, title, subtitle, curve=curve, gradient=False, flat_style=True
            )
        elif variant == "gradient_layered":
            body = _draw_ribbon(layers, inter_flows, pal, width, height, title, subtitle, curve="bezier", gradient=True)
        elif variant == "alluvial_sinusoidal":
            body = _draw_ribbon(
                layers, inter_flows, pal, width, height, title, subtitle, curve="sinusoidal", gradient=False
            )
        else:
            raise ValueError(
                f"unknown variant {variant!r}. Supported: default_ribbon_flat, "
                "alluvial_sinusoidal, chord_circular, multi_layer_flat, gradient_layered"
            )
        # header is inside _draw_ribbon (as it needs its own layout)
        return svg_open(0, 0, float(width), float(height), bg=pal["bg"]) + body + svg_close()

    return svg_open(0, 0, float(width), float(height), bg=pal["bg"]) + body + svg_close()


def _normalize_layered(data):
    """Handle both layered and nodes/flows schemas."""
    if "layers" in data and "inter_flows" in data:
        layers = data["layers"]
        inter = data["inter_flows"]
        if len(layers) < 2:
            raise ValueError("draw_sankey: layers needs at least 2 groups")
        if len(inter) != len(layers) - 1:
            raise ValueError(f"draw_sankey: inter_flows must have {len(layers) - 1} entries")
        return _validate_layered(layers, inter)
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
        return _validate_layered([left, right], [flows])
    raise ValueError("draw_sankey: data must have layers+inter_flows or nodes+flows")


def _validate_edges(flows, sources, targets):
    result = []
    for edge in flows:
        if len(edge) != 3:
            raise ValueError("sankey: every flow must be (source, target, value)")
        source, target, value = edge
        if source not in sources or target not in targets:
            raise ValueError(f"sankey: unknown flow endpoint {source!r} -> {target!r}")
        value = float(value)
        if not math.isfinite(value) or value < 0:
            raise ValueError("sankey: flow values must be finite and nonnegative")
        result.append((source, target, value))
    return result


def _validate_layered(layers, inter_flows):
    layers = [list(layer) for layer in layers]
    if len(layers) < 2 or len(inter_flows) != len(layers) - 1:
        raise ValueError("sankey: provide at least two layers and one flow list per adjacent layer")
    for layer in layers:
        if not layer or len(set(layer)) != len(layer):
            raise ValueError("sankey: each layer must contain unique node names and cannot be empty")
    flows = [_validate_edges(edges, set(layers[i]), set(layers[i + 1])) for i, edges in enumerate(inter_flows)]
    for i in range(1, len(layers) - 1):
        for node in layers[i]:
            incoming = sum(value for _, target, value in flows[i - 1] if target == node)
            outgoing = sum(value for source, _, value in flows[i] if source == node)
            if not math.isclose(incoming, outgoing, rel_tol=1e-8, abs_tol=1e-10):
                raise ValueError(
                    f"sankey: layer {i} node {node!r} is not conserved "
                    f"(incoming={incoming:g}, outgoing={outgoing:g}); include an explicit source or sink"
                )
    return layers, flows


def _normalize_chord(data):
    """Return (nodes:list, flows:list of (src,dst,val))."""
    if "nodes" in data and "flows" in data:
        nodes = list(data["nodes"])
        if not nodes or len(set(nodes)) != len(nodes):
            raise ValueError("chord: provide unique node names")
        return nodes, _combine_chord_flows(data["flows"], nodes)
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
        return nodes, _combine_chord_flows(flows, nodes)
    raise ValueError("draw_sankey: data must have nodes+flows or layers+inter_flows")


def _combine_chord_flows(flows, nodes):
    """One quantitative ribbon per ordered pair, including repeated input rows."""
    combined = {}
    for source, target, value in _validate_edges(flows, set(nodes), set(nodes)):
        combined.setdefault((source, target), []).append(value)
    return [(source, target, math.fsum(values)) for (source, target), values in combined.items()]


# ribbon (bezier / sinusoidal) with optional gradient
def _draw_ribbon(layers, inter_flows, pal, W, H, title, subtitle, curve="bezier", gradient=False, flat_style=False):
    W = float(W)
    H = float(H)
    ink = pal["ink"]
    mut = pal["muted"]
    bg = pal["bg"]
    series = pal.get("series") or [pal["accent"]]
    n_layers = len(layers)

    # Dynamic margins driven by longest label in the outer columns.
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
            for name, total in totals.items():
                totals[name] = max(total, out_total.get(name, 0))
        node_totals.append(totals)

    max_col = 0.0
    for li in range(n_layers):
        col_total = sum(node_totals[li].values())
        col_h = col_total  # scale later
        max_col = max(max_col, col_total)
    scale = (plot_h - NODE_GAP * (max(len(l) for l in layers) - 1)) / max(max_col, 1e-6)

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
    src_slots = [{} for _ in range(n_layers)]  # per node: dict name -> next_y for outflow
    dst_slots = [{} for _ in range(n_layers)]
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
                    f"</linearGradient>"
                )
                fill = f"url(#{gid})"
            elif flat_style:
                # denser fill for a solid "flat layered" look
                fill = _rgba_with_alpha(col, 0.55)
            else:
                fill = _rgba_with_alpha(col, 0.32)
            stroke = _rgba_with_alpha(col, 0.5)
            parts.append(f'<path d="{d_path}" fill="{fill}" stroke="{stroke}" stroke-width="0.4"></path>')

    max(sum(node_totals[li].values()) for li in range(n_layers))
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
    """Orthogonal / stepped ribbon: horizontal from src, sharp vertical at midpoint, horizontal to dst."""
    xm = (x1 + x2) / 2
    r = min(6.0, abs(x2 - x1) * 0.08)
    d = (
        f"M {x1:.1f} {y1_top:.1f} "
        # top edge: go horizontal to (xm-r, y1_top), arc/curve to (xm, y1_top+/-r), vertical to (xm, y2_top-/+r), curve to (xm+r, y2_top), horizontal to x2
        f"L {xm - r:.1f} {y1_top:.1f} "
        f"Q {xm:.1f} {y1_top:.1f} {xm:.1f} {y1_top + (r if y2_top > y1_top else -r):.1f} "
        f"L {xm:.1f} {y2_top - (r if y2_top > y1_top else -r):.1f} "
        f"Q {xm:.1f} {y2_top:.1f} {xm + r:.1f} {y2_top:.1f} "
        f"L {x2:.1f} {y2_top:.1f} "
        f"L {x2:.1f} {y2_bot:.1f} "
        f"L {xm + r:.1f} {y2_bot:.1f} "
        f"Q {xm:.1f} {y2_bot:.1f} {xm:.1f} {y2_bot - (r if y2_bot > y1_bot else -r):.1f} "
        f"L {xm:.1f} {y1_bot + (r if y2_bot > y1_bot else -r):.1f} "
        f"Q {xm:.1f} {y1_bot:.1f} {xm - r:.1f} {y1_bot:.1f} "
        f"L {x1:.1f} {y1_bot:.1f} "
        f"Z"
    )
    return d


def _chord_distribution(nodes, flows):
    indices = {name: i for i, name in enumerate(nodes)}
    indexed = [(indices[source], indices[target], float(value)) for source, target, value in flows]
    maximum = max((value for _, _, value in indexed), default=0)
    if maximum <= 0:
        raise ValueError("chord total flow must be positive")
    totals = [0.0] * len(nodes)
    for source, target, value in indexed:
        totals[source] += value / maximum
        totals[target] += value / maximum
    total_weight = math.fsum(totals)
    gap = min(math.radians(3), math.tau / (4 * len(nodes)))
    remaining = math.tau - gap * len(nodes)
    angles, position = [], -math.pi / 2
    for value in totals:
        extent = remaining * value / total_weight
        angles.append((position, position + extent))
        position += extent + gap
    return indexed, totals, angles, maximum


def _flow_number(values):
    try:
        return f"{math.fsum(values):g}"
    except OverflowError:
        from decimal import Decimal

        return f"{sum((Decimal(str(value)) for value in values), Decimal(0)):.6g}"


def _chord_labels(nodes, flows):
    return [
        {
            "name": str(node),
            "annotation": "in+out "
            + _flow_number(
                [value for source, target, value in flows for endpoint in (source, target) if endpoint == node]
            ),
        }
        for node in nodes
    ]


def _chord_canvas_height(nodes, flows, tracks, pal, width, height, title, subtitle):
    """Measure the actual weighted-angle label rails before drawing any geometry."""
    from ._chart_layout import wrap_lines
    from ._polar import legend_rows, normalize_tracks, polar_layout

    layout = polar_layout(width, height, pal, BODY_FONT)
    rings = normalize_tracks(tracks or [], list(range(len(nodes))), layout.pal)
    _, legend_height = legend_rows(layout, [], rings)
    _, _, angles, _ = _chord_distribution(nodes, flows)
    sides = {-1: 0.0, 1: 0.0}
    for item, pair in zip(_chord_labels(nodes, flows), angles):
        side = 1 if math.cos(sum(pair) / 2) >= 0 else -1
        label = item["name"] + " · " + item["annotation"]
        sides[side] += len(wrap_lines(label, 130, 11.5, layout.font)) * 11.5 * 1.35 + 5
    header = (44 if title else 20) + (18 if subtitle else 0) + 12
    return max(float(height), header + max(sides.values()) + legend_height + 72)


def _draw_chord_circular(nodes, flows, pal, W, H, title=None, subtitle=None, tracks=None):
    if tracks:
        from ._polar import canonical_palette

        pal = canonical_palette(pal)
    W = float(W)
    H = float(H)
    ink = pal["ink"]
    mut = pal["muted"]
    series = pal.get("series") or [pal["accent"]]
    N = len(nodes)
    idx_flows, totals, node_angles, weight_scale = _chord_distribution(nodes, flows)

    ML = 60
    header_h = 20
    if title:
        header_h = 44
    if subtitle:
        header_h += 18
    top_pad = header_h + 12 if (title or subtitle) else 20

    from ._polar import legend_rows, normalize_tracks, polar_layout

    track_layout = polar_layout(W, H, pal, BODY_FONT)
    ring_tracks = normalize_tracks(tracks or [], list(range(N)), track_layout.pal)
    track_legend, track_legend_height = legend_rows(track_layout, [], ring_tracks)

    # layout — shift circle down to leave room for title
    CX = W / 2
    avail_h = H - top_pad - 20 - (track_legend_height + 28 if ring_tracks else 0)
    CY = top_pad + avail_h / 2
    R_OUTER = min((W - 370) / 2, avail_h / 2 - 16) - len(ring_tracks) * 24 - 10
    if R_OUTER < 50:
        raise ValueError("chord labels and tracks need a larger canvas")
    R_INNER = R_OUTER - 14
    R_RIBBON = R_INNER - 4

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
            span = (a1 - a0) * ((v / weight_scale) / totals[i])
            slots[i].append({"a0": acur, "a1": acur + span, "other": other, "value": v, "is_src": True})
            acur += span
        for other, v in ins:
            span = (a1 - a0) * ((v / weight_scale) / totals[i])
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
            f"</path>"
        )

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

        # Track compositions place all labels on measured external rails.
    from ._polar import PolarGeometry, render_labels, render_legend, render_tracks

    geometry = PolarGeometry(CX, CY, 0, R_OUTER, N)
    outer = (
        render_tracks(track_layout, geometry, ring_tracks, R_OUTER + 8, 20, angles=node_angles)
        if ring_tracks
        else R_OUTER
    )
    geometry.angle = lambda i: sum(node_angles[i]) / 2
    render_labels(
        track_layout, geometry, _chord_labels(nodes, flows), outer, top_pad, top_pad + avail_h, rail_width=130
    )
    render_legend(track_layout, track_legend, H - track_legend_height - 16)
    parts.extend(track_layout.parts)

    parts.append(
        f'<text x="{CX:.1f}" y="{CY - 4:.1f}" text-anchor="middle" '
        f'dominant-baseline="middle" font-family="{HEAD_FONT}" font-size="16" '
        f'font-weight="600" fill="{ink}">{_flow_number([v for _, _, v in idx_flows])}</text>'
    )
    parts.append(
        f'<text x="{CX:.1f}" y="{CY + 14:.1f}" text-anchor="middle" '
        f'dominant-baseline="middle" font-family="{BODY_FONT}" font-size="11" '
        f'fill="{mut}" letter-spacing=".18em">{_xesc(tr("TOTAL FLOWS"))}</text>'
    )

    return "".join(parts)


def make_sankey(
    left_nodes=None,
    right_nodes=None,
    flows=None,
    layers: list | None = None,
    inter_flows: list | None = None,
    layer_titles: list | None = None,
    title: str | None = None,
    subtitle: str | None = None,
    figure_label: str | None = None,
    note: str | None = None,
    source: str | None = None,
    node_gap: float = 18.0,
    node_width: float = 14.0,
    width: float = 1200.0,
    height: float = 760.0,
    font_family: str | None = None,
    palette=None,
    variant: str | None = None,
    tracks: list | None = None,
) -> str:
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
    if not _variant_is_classic("sankey", variant):
        _data = (
            {"layers": layers, "inter_flows": inter_flows}
            if layers is not None and inter_flows is not None
            else {"layers": [left_nodes or [], right_nodes or []], "inter_flows": [flows or []]}
        )
        if tracks is not None:
            if variant != "chord_circular":
                raise ValueError("tracks are supported for chord_circular")
            _data["tracks"] = tracks
        return _dispatch_to_svg_lib(
            "sankey",
            variant,
            _data,
            title=title,
            subtitle=subtitle,
            figure_label=figure_label,
            palette=palette,
            font_family=font_family,
            width=width,
            height=height,
        )

    if tracks is not None:
        raise ValueError("tracks are supported for chord_circular")

    if layers is None:
        if left_nodes is None or right_nodes is None or flows is None:
            raise ValueError("sankey: need either `layers` (multi-layer) or `left_nodes/right_nodes/flows` (2-layer)")
        layers = [list(left_nodes), list(right_nodes)]
        inter_flows = [list(flows)]
    else:
        if inter_flows is None:
            raise ValueError("sankey: `inter_flows` required when `layers` given")
        if len(inter_flows) != len(layers) - 1:
            raise ValueError(f"sankey: inter_flows must have {len(layers) - 1} groups, got {len(inter_flows)}")

    layers, inter_flows = _validate_layered(layers, inter_flows)
    n_layers = len(layers)
    if n_layers < 2:
        raise ValueError(f"sankey: need at least 2 layers, got {n_layers}")

    _pal = _resolve_palette(palette)
    _body_font, _head_font = _resolve_font(font_family)
    _INK, _INK6, _INK4, _INK2, _INK1, _ACC = _legacy_inks(_pal)
    c_muted = _pal.get("muted", _rgba_with_alpha(_INK, 0.6))
    _pal.get("secondary", _rgba_with_alpha(_INK, 0.5))
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
                for src in layers[li - 1]:
                    in_sum += flow_dicts[li - 1].get(src, {}).get(name, 0)
            if li < n_layers - 1:
                out_sum = sum(flow_dicts[li].get(name, {}).values())
            # Interior node flow has already passed the conservation check.
            if li == 0:
                totals[name] = out_sum
            elif li == n_layers - 1:
                totals[name] = in_sum
            else:
                totals[name] = in_sum
        layer_totals.append(totals)

    total_n = sum(layer_totals[0].values()) if layer_totals[0] else 0

    # Keep the supplied decimal resolution; int(total) previously erased
    # fractional amounts, while raw float sums can expose binary noise.
    from decimal import Decimal, localcontext

    amount_places = max(
        (max(0, -Decimal(str(row[2])).as_tuple().exponent) for flow in inter_flows for row in flow), default=0
    )

    def _amount_label(value):
        decimal = Decimal(str(value))
        with localcontext() as context:
            context.prec = max(28, decimal.adjusted() + amount_places + 8)
            rounded = decimal.quantize(Decimal(1).scaleb(-amount_places))
        label = format(rounded, ",f")
        return label.rstrip("0").rstrip(".") if "." in label else label

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
                    t = 0.3 + 0.4 * (k / max(1, n_nodes - 1))
                    r, g, b = _rgb_tuple(_INK)
                    mid_cols.append(f"rgba({r},{g},{b},{t:.2f})")
                layer_node_colors.append(mid_cols)

    # Dynamic outer margins based on **actual** label strings on the outer columns.
    fonts = chart_font_sizes(width, height, max(map(len, layers)))
    _fs_name = max(fonts["label"], width * 0.026)
    _fs_val = max(fonts["group_n"], width * 0.024)

    # Use the validator's own width model so what we reserve equals what the OOB linter measures.
    try:
        from embed_svg_validator import _svg_text_width as _val_text_width
    except ImportError:
        _val_text_width = None

    def _est_str_w(s, fs, bold=False):
        if _val_text_width is not None:
            return _val_text_width(s, fs, 0.0, bold, _body_font)
        # Fallback: coarse advance model roughly matching Inter sans.
        w = 0.0
        b = 1.05 if bold else 1.0
        for c in s:
            if c == " ":
                w += fs * 0.33 * b
            elif c == "%":
                w += fs * 0.85 * b
            elif c.isdigit():
                w += fs * 0.58 * b
            elif c.isupper():
                w += fs * 0.72 * b  # conservative wide-letter avg
            elif c.islower():
                w += fs * 0.55 * b
            else:
                w += fs * 0.50 * b
        return w

    def _label_str(name, total_val):
        pct = (total_val / total_n * 100) if total_n > 0 else 0
        sub = _amount_label(total_val)
        if total_n > 0:
            sub += f"  ·  {pct:.1f}%"
        # actual concatenated text as the validator sees it (matches
        # "".join(node.itertext()).strip() from _svg_visual_bbox)
        return f"{name}  {sub}"

    def _col_max_label_width(col_names, col_totals, fs_name, fs_val):
        """Return max estimated **visual** width per label in this column."""
        best = 0.0
        for nm in col_names:
            tv = col_totals.get(nm, 0)
            pct = (tv / total_n * 100) if total_n > 0 else 0
            sub = _amount_label(tv)
            if total_n > 0:
                sub += f"  ·  {pct:.1f}%"
            w_name = _est_str_w(str(nm), fs_name, bold=True)
            w_sep = _est_str_w("  ", fs_val)
            w_sub = _est_str_w(sub, fs_val)
            best = max(best, w_name + w_sep + w_sub)
        return best

    def _col_max_flat_width(col_names, col_totals, flat_fs):
        """Return the width the OOB linter will compute for the outer <text>."""
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
    # (its upper bound is _fs_name). Use that for the flat estimate.
    _left_flat = _col_max_flat_width(_left_names, _left_totals, _fs_name)
    _right_flat = _col_max_flat_width(_right_names, _right_totals, _fs_name)

    # Padding: covers the tx offset (lx +/- 8), rounding, and small safety margin.
    _label_pad = 24
    MARGIN_L = math.ceil(max(200, max(_left_visual, _left_flat) + _label_pad))
    MARGIN_R = math.ceil(max(200, max(_right_visual, _right_flat) + _label_pad))
    MARGIN_T = 165 if title else 80
    MARGIN_B = 100 if (note or source) else 60

    plot_top = MARGIN_T
    plot_bottom = height - MARGIN_B
    plot_h = plot_bottom - plot_top
    plot_left = MARGIN_L
    plot_right = width - MARGIN_R

    if n_layers == 1:
        layer_xs = [plot_left]
    else:
        step = (plot_right - plot_left) / (n_layers - 1)
        layer_xs = [plot_left + i * step for i in range(n_layers)]

    # 密度指标：单列最多节点数 → 单节点平均高度
    # 基准：6 节点/列 · plot_h ≈ 495 · node_gap=18 → 节点高 ≈ 65px（此时 scale=1.0，节点名 14pt）
    _max_col_nodes = max(len(layers[li]) for li in range(n_layers))
    _est_node_h = max(20.0, (plot_h - node_gap * max(0, _max_col_nodes - 1)) / max(1, _max_col_nodes))
    _fs_scale = max(0.75, min(1.8, _est_node_h / 65.0))
    fs_title = round(min(32.0, 26 * _fs_scale), 1)
    fs_subtitle = round(min(15.0, 12 * _fs_scale), 1)
    fs_figure = round(min(12.0, 10 * _fs_scale), 1)
    fs_layer = round(max(_fs_val, min(13.0, 10 * _fs_scale)), 1)  # 层标题
    fs_node = round(min(_fs_name, max(12.0, _est_node_h * 0.45)), 1)  # 节点名（单行布局，可以更大）
    fs_nval = round(min(_fs_val, fs_node * 0.9), 1)  # 节点数值
    fs_foot = round(min(11.0, 9.5 * _fs_scale), 1)

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
    layer_positions = []
    scales = []
    for li in range(n_layers):
        totals = layer_totals[li]
        items = layers[li]
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
                for dst in layers[li + 1]:
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
                for src in layers[li - 1]:
                    v = flow_dicts[li - 1].get(src, {}).get(name, 0)
                    if v > 0:
                        h = v * scale
                        in_segments[li][name][src] = (y, y + h)
                        y += h

    parts = []

    if c_bg:
        parts.append(f'<rect width="{width}" height="{height}" fill="{PAPER}"/>')

    # 顶部
    # y 位置跟字号联动，避免大 scale 时挤
    _y_title = 20 + fs_title
    _y_subtitle = _y_title + fs_title * 0.55 + fs_subtitle
    _y_line = _y_subtitle + 12
    _y_figure = _y_line + 14 + fs_figure * 0.5
    if title:
        parts.append(
            f'<text x="{MARGIN_L}" y="{_y_title:.1f}" '
            f'font-family="{_head_font}" '
            f'font-size="{fs_title}" font-weight="600" fill="{_INK}" letter-spacing=".05em">'
            f"{_xesc(title)}</text>"
        )
    if subtitle:
        parts.append(
            f'<text x="{MARGIN_L}" y="{_y_subtitle:.1f}" '
            f'font-family="{_body_font}" font-size="{fs_subtitle}" fill="{c_muted}" '
            f'letter-spacing=".16em">{_xesc(subtitle)}</text>'
        )
        parts.append(
            f'<line x1="{MARGIN_L}" y1="{_y_line:.1f}" x2="{width - MARGIN_R}" y2="{_y_line:.1f}" '
            f'stroke="{_INK}" stroke-width="0.8"/>'
        )
    if figure_label:
        parts.append(
            f'<text x="{MARGIN_L}" y="{_y_figure:.1f}" font-family="{_body_font}" font-size="{fs_figure}" '
            f'fill="{c_muted}" font-weight="600" letter-spacing=".15em">{_xesc(figure_label)}</text>'
        )
        lbl_w = max(72, len(figure_label) * 8 + 20)
        note_txt = f"{n_layers}-layer Sankey · N={_amount_label(total_n)}" if total_n else f"{n_layers}-layer Sankey"
        parts.append(
            f'<text x="{MARGIN_L + lbl_w}" y="{_y_figure:.1f}" font-family="{_body_font}" font-size="{fs_figure}" '
            f'fill="{c_muted}" letter-spacing=".04em">{_xesc(note_txt)}</text>'
        )

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
            parts.append(
                f'<text x="{tx:.1f}" y="{MARGIN_T - 24}" text-anchor="{anchor}" '
                f'font-family="{_body_font}" font-size="{fs_layer}" font-weight="600" '
                f'fill="{_INK}" letter-spacing=".16em">{_xesc(str(lt).upper())}</text>'
            )

    def ribbon_path(x1, y1_top, y1_bot, x2, y2_top, y2_bot):
        xc = (x1 + x2) / 2
        return (
            f"M {x1:.1f} {y1_top:.1f} "
            f"C {xc:.1f} {y1_top:.1f} {xc:.1f} {y2_top:.1f} {x2:.1f} {y2_top:.1f} "
            f"L {x2:.1f} {y2_bot:.1f} "
            f"C {xc:.1f} {y2_bot:.1f} {xc:.1f} {y1_bot:.1f} {x1:.1f} {y1_bot:.1f} "
            f"Z"
        )

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
                seg_to = in_segments[li + 1][d].get(s)
                if seg_from is None or seg_to is None:
                    continue
                x1 = layer_xs[li] + node_width
                x2 = layer_xs[li + 1]
                y1t, y1b = seg_from
                y2t, y2b = seg_to
                d_path = ribbon_path(x1, y1t, y1b, x2, y2t, y2b)
                fill_col = _rgba_with_alpha(col, 0.32)
                stroke_col = _rgba_with_alpha(col, 0.55)
                parts.append(f'<path d="{d_path}" fill="{fill_col}" stroke="{stroke_col}" stroke-width="0.4"></path>')

    # Keep labels distinct when adjacent small flows are thinner than a line of text.
    label_centers = []
    min_separation = fs_node * 1.18
    for li, names in enumerate(layers):
        if len(names) * min_separation > plot_h:
            raise ValueError("sankey: full node labels require a taller canvas")
        centers = []
        cursor = plot_top + fs_node / 2
        for name in names:
            y0, y1 = layer_positions[li][name]
            center = max(cursor, min((y0 + y1) / 2, plot_bottom - fs_node / 2))
            centers.append(center)
            cursor = center + min_separation
        overflow = max(0.0, centers[-1] - (plot_bottom - fs_node / 2))
        for i in range(len(centers) - 1, -1, -1):
            centers[i] -= overflow
            if i:
                overflow = max(0.0, centers[i - 1] + min_separation - centers[i])
        label_centers.append(dict(zip(names, centers)))

    for li in range(n_layers):
        items = layers[li]
        for ni, name in enumerate(items):
            y0, y1 = layer_positions[li][name]
            col = layer_node_colors[li][ni]
            lx = layer_xs[li]
            parts.append(
                f'<rect x="{lx:.1f}" y="{y0:.1f}" width="{node_width}" height="{y1 - y0:.1f}" '
                f'fill="{_rgba_with_alpha(col, 0.9)}"/>'
            )
            # 顶端 2px accent 条
            parts.append(f'<rect x="{lx:.1f}" y="{y0:.1f}" width="{node_width}" height="2" fill="{col}"/>')

            total_val = layer_totals[li].get(name, 0)
            pct = (total_val / total_n * 100) if total_n > 0 else 0
            true_yc = (y0 + y1) / 2
            yc = label_centers[li][name]

            if li == 0:
                tx = lx - 8
                anchor = "end"
                use_stroke = False
            elif li == n_layers - 1:
                tx = lx + node_width + 8
                anchor = "start"
                use_stroke = False
            else:
                tx = lx + node_width + 6
                anchor = "start"
                use_stroke = True

            if abs(yc - true_yc) > 0.1 and li in (0, n_layers - 1):
                source_x = lx if li == 0 else lx + node_width
                end_x = tx + 3 if li == 0 else tx - 3
                parts.append(
                    f'<path d="M{source_x:.1f},{true_yc:.1f} L{end_x:.1f},{yc:.1f}" fill="none" stroke="{c_muted}" stroke-width="1.2" data-role="node-label-leader"/>'
                )
            sub_txt = _amount_label(total_val)
            if total_n > 0:
                sub_txt += f"  ·  {pct:.1f}%"

            # 节点名 + 数值：同一行、用 tspan 排布，数值放在"离图更近"的一侧
            # anchor=end（左列）：数值在节点名之后（视觉在节点名右侧、靠近节点）
            # anchor=start（右列/中间列）：数值在节点名之后（节点名右、数值再右）
            # baseline 与原节点名对齐（yc - 4）
            stroke_attr = (
                f' paint-order="stroke" stroke="{PAPER}" stroke-width="3" stroke-linejoin="round"' if use_stroke else ""
            )

            # 用两个独立 <text> 而不是 <text> 内两个 <tspan>——避免服务端 pretty-print
            # 时在 tspan 之间插入换行/缩进空白，导致 lint 用 itertext() 拿到长串后按外层
            # font-size 高估宽度触发 embed_svg_out_of_bounds。
            # 名字放靠近节点、数值往外偏移一个"名字宽度 + gap"或"数值宽度 + gap"的距离。
            # Reuse the measured glyph widths used for the outer margins;
            # the former ASCII approximation counted CJK characters at half width.
            name_w = _est_str_w(str(name), fs_node, bold=True)
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

    parts.append(
        notes_source_footer(
            note,
            source,
            x=MARGIN_L,
            x_right=width - MARGIN_R,
            y=height - 45,
            rule=_INK4,
            font=_body_font,
            fs=fs_foot,
            color=c_muted,
            figure_label=figure_label,
            figure_fs=fs_foot,
        )
    )

    body = "".join(parts)
    _svg_result = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {int(width)} {int(height)}">{body}</svg>'
    return _prepend_bg_if_dark(_svg_result, _pal)
