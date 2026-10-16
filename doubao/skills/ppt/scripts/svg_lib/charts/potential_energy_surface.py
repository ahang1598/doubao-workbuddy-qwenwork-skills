"""Potential energy surface (reaction coordinate vs energy): smooth curve plus key
states (reactants / TS‡ / intermediates / products) and double-headed activation
"""

from __future__ import annotations


from .._common import (
    _dist_font_sizes,
    _estimate_label_width_px,
    _resolve_font,
    _resolve_palette,
    _variant_is_classic,
    _xesc,
)
from . import _academic_rigor as rigor
from ._shared import tr
from .grouped_bar import _wrap_label
from .hr_diagram import _finite


def make_potential_energy_surface(
    curve=None,
    states=None,
    *,
    pathways=None,
    steps=None,
    energy_unit: str = "kcal/mol",
    energy_label: str | None = None,
    x_title: str | None = None,
    title: str | None = None,
    subtitle: str | None = None,
    figure_label: str | None = None,
    note: str | None = None,
    source: str | None = None,
    activation_energies=None,
    width: float = 1300,
    height: float = 820,
    font_family: str | None = None,
    palette=None,
    variant: str | None = None,
) -> str:
    """Potential energy surface with key states and activation-energy arrows.

    Single curve: ``curve``: list of (x, y) sample points along the PES curve;
    ``states``: list of ``{x, y, label, kind?}``; ``kind='ts'`` renders as hollow
    square with ``‡`` suffix; ``activation_energies``: list of ``{from_x, to_x, value, label?}``.

    Free-energy diagram (several pathways / catalysts / surfaces on one axis): pass
    ``pathways=[{"name": "Cu(100)", "energies": [0, 0.62, -0.31, 0.95, -0.42], "ts": [1, 3]}, ...]``
    and ``steps=["*CO2", "TS1", "*COOH", "TS2", "*CO"]``. Each state is drawn as a level bar,
    neighbours joined by dashed connectors; indexes in ``ts`` are transition states. Each
    pathway's largest forward barrier (TS minus the preceding minimum) is annotated, and
    ``barriers=[[from_index, to_index], ...]`` per pathway selects other steps to annotate.
    ``energies`` may contain ``None`` where a pathway skips a step. ``energy_label`` is the
    y title (default "ΔG"), ``x_title`` the x title (default "Reaction coordinate").
    """
    if pathways is not None:
        return _free_energy_diagram(
            pathways,
            steps,
            energy_unit=energy_unit,
            energy_label=energy_label,
            x_title=x_title,
            title=title,
            subtitle=subtitle,
            figure_label=figure_label,
            note=note,
            source=source,
            width=width,
            height=height,
            font_family=font_family,
            palette=palette,
            variant=variant,
        )
    if curve is None and states is None:
        raise ValueError("pass curve/states for a single PES curve, or pathways=[...] for a free-energy diagram")
    _variant_is_classic("potential_energy_surface", variant)
    if palette is None:
        palette = "archive_ink"
    pal = _resolve_palette(palette)
    body_font, heading_font = _resolve_font(font_family)
    W, H = float(width), float(height)

    curve = [tuple(point) for point in (curve or [])]
    states = [dict(state) for state in (states or [])]
    activation_energies = [dict(item) for item in (activation_energies or [])]
    for i, point in enumerate(curve):
        if len(point) != 2 or not all(_finite(value) for value in point):
            raise ValueError(f"curve[{i}] must contain finite x and y coordinates")
    for i, state in enumerate(states):
        if not all(_finite(state.get(key)) for key in ("x", "y")):
            raise ValueError(f"states[{i}] must contain finite x and y coordinates")
    for i, item in enumerate(activation_energies):
        if not all(_finite(item.get(key)) for key in ("from_x", "to_x", "value")):
            raise ValueError(f"activation_energies[{i}] requires finite from_x, to_x and value")
    if not curve and not states:
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}">'
            f'<text x="{W / 2}" y="{H / 2}" text-anchor="middle" font-size="16" '
            f'fill="{pal["ink6"]}">{_xesc(tr("No data"))}</text></svg>'
        )

    fs = _dist_font_sizes(W, H, max(4, len(states)))
    label_fs = max(13.0, fs["label"])
    labels = []
    for state in states:
        label = str(state.get("label", ""))
        if state.get("kind") == "ts" and "‡" not in label:
            label += "‡"
        if label:
            labels.append((state["x"], state["y"], label, pal["ink"]))

    # Explicit state coordinates are observations, even when they differ from
    # the curve. Activation arrows use those observations when one is named.
    def energy_at(x):
        candidates = {state["y"] for state in states if state["x"] == x}
        if len(candidates) > 1:
            raise ValueError("activation-energy x coordinates must identify a unique state")
        value = next(iter(candidates)) if candidates else _interp_curve_y(curve, x)
        if value is None:
            raise ValueError("activation-energy endpoints require a state or a curve")
        return value

    arrows = []
    for item in activation_energies:
        x0, x1 = item["from_x"], item["to_x"]
        y0, y1 = energy_at(x0), energy_at(x1)
        mid_x = (x0 + x1) / 2
        arrows.append((x0, y0, x1, y1, mid_x))
        labels.append(
            (mid_x, (y0 + y1) / 2, f"{item.get('label', 'Ea')} = {item['value']:.1f} {energy_unit}", pal["accent"])
        )

    rail_width = min(
        W * 0.34,
        max(
            145.0,
            max(
                (_estimate_label_width_px(item[2], label_fs, bold=True, font_family=body_font) for item in labels),
                default=0,
            ),
        ),
    )
    wrapped = [_wrap_label(item[2], rail_width, label_fs, body_font, bold=True) for item in labels]
    rail_height = sum(len(lines) * label_fs * 1.3 + 16 for lines in wrapped)
    header_y = (
        24
        + (fs["title"] + 10 if title else 0)
        + (fs["subtitle"] + 10 if subtitle else 0)
        + (fs["figure"] + 10 if figure_label else 0)
    )
    plot_x_left = 110.0
    plot_x_right = W - rail_width - 64 if labels else W - 70
    plot_y_top = header_y + 60
    H = max(H, plot_y_top + rail_height + 130)
    plot_y_bot = H - 130

    all_x = [p[0] for p in curve] + [s["x"] for s in states] + [v for arrow in arrows for v in (arrow[0], arrow[2])]
    all_y = [p[1] for p in curve] + [s["y"] for s in states]
    x_ticks, x_min, x_max = rigor.nice_axis(min(all_x), max(all_x), 6)
    y_ticks, y_min, y_max = rigor.nice_axis(min(all_y), max(all_y), 5)
    # Keep marker perimeters away from the axes without changing any data.
    x_pad = (x_max - x_min) * 0.025
    y_pad = (y_max - y_min) * 0.035
    x_min, x_max = x_min - x_pad, x_max + x_pad
    y_min, y_max = y_min - y_pad, y_max + y_pad

    def X(v):
        return rigor._lin(v, x_min, x_max, plot_x_left, plot_x_right)

    def Y(v):
        return rigor._lin(v, y_min, y_max, plot_y_bot, plot_y_top)

    parts = rigor.draw_canvas_bg(pal, W, H)

    parts.append(
        rigor.draw_title_block(
            plot_x_left,
            header_y,
            plot_x_right - plot_x_left,
            title=title,
            subtitle=subtitle,
            figure_label=figure_label,
            pal=pal,
            fs=fs,
            body_font=body_font,
            heading_font=heading_font,
        )
    )

    parts.append(
        rigor.draw_grid(
            plot_x_left,
            plot_x_right,
            plot_y_top,
            plot_y_bot,
            pal=pal,
            y_ticks=y_ticks,
            y_min=y_min,
            y_max=y_max,
            orient="horizontal",
        )
    )

    # Every raw curve vertex participates in the axis domain. Straight segments
    # therefore remain inside its convex plot box without renderer-side clipping.
    if len(curve) >= 2:
        pts = [(X(x), Y(y)) for x, y in curve]
        d = " ".join(f"{'M' if i == 0 else 'L'} {x:.1f} {y:.1f}" for i, (x, y) in enumerate(pts))
        parts.append(f'<path d="{d}" fill="none" stroke="{pal["ink"]}" stroke-width="2.2"/>')

    if len(curve) == 1:
        x, y = curve[0]
        parts.append(f'<circle cx="{X(x):.1f}" cy="{Y(y):.1f}" r="3" fill="{pal["ink"]}"/>')

    # The arrow geometry stays in data space; its text shares the external
    # annotation rail with state names, so no label masks a curve or marker.
    accent = pal["accent"]
    for x0, y0, x1, y1, mid_x in arrows:
        ax, ay_top, ay_bot = X(mid_x), Y(max(y0, y1)), Y(min(y0, y1))
        for x, y in ((x0, y0), (x1, y1)):
            parts.append(
                f'<line x1="{X(x):.1f}" y1="{Y(y):.1f}" x2="{ax:.1f}" y2="{Y(y):.1f}" stroke="{accent}" stroke-width="0.9" stroke-dasharray="2 3"/>'
            )
        parts.append(
            f'<line x1="{ax:.1f}" y1="{ay_top:.1f}" x2="{ax:.1f}" y2="{ay_bot:.1f}" stroke="{accent}" stroke-width="1.4"/>'
        )
        if ay_bot - ay_top > 12:
            parts.append(
                f'<polygon points="{ax:.1f},{ay_top:.1f} {ax - 4:.1f},{ay_top + 7:.1f} {ax + 4:.1f},{ay_top + 7:.1f}" fill="{accent}"/>'
            )
            parts.append(
                f'<polygon points="{ax:.1f},{ay_bot:.1f} {ax - 4:.1f},{ay_bot - 7:.1f} {ax + 4:.1f},{ay_bot - 7:.1f}" fill="{accent}"/>'
            )

    # Route complete measured labels outside the numeric plot. The first leader endpoint is always the actual
    # observation, never an interpolated surrogate.
    rail_x = plot_x_right + 36
    rows = sorted(zip(labels, wrapped), key=lambda row: -row[0][1])
    cursor = plot_y_top + 8
    remaining = rail_height
    for (x, y, label, color), lines in rows:
        row_h = len(lines) * label_fs * 1.3 + 16
        top = max(cursor, min(Y(y) - label_fs * 0.5, plot_y_bot - remaining))
        center_y = top + label_fs * 0.45
        parts.append(
            f'<path d="M {X(x):.1f} {Y(y):.1f} L {plot_x_right + 16:.1f} {center_y:.1f} L {rail_x - 8:.1f} {center_y:.1f}" fill="none" stroke="{pal["ink4"]}" stroke-width="0.8" stroke-dasharray="2 3"/>'
        )
        for j, line in enumerate(lines):
            parts.append(
                f'<text x="{rail_x:.1f}" y="{top + label_fs + j * label_fs * 1.3:.1f}" font-size="{label_fs}" fill="{color}" font-weight="600">{_xesc(line)}</text>'
            )
        cursor = top + row_h
        remaining -= row_h

    # Markers are painted last at the supplied coordinates.
    for state in states:
        sx, sy = X(state["x"]), Y(state["y"])
        if state.get("kind") == "ts":
            parts.append(
                f'<rect x="{sx - 5:.1f}" y="{sy - 5:.1f}" width="10" height="10" fill="{pal.get("bg") or "white"}" stroke="{accent}" stroke-width="1.6"/>'
            )
        else:
            parts.append(
                f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="6" fill="{accent}" stroke="{pal["ink"]}" stroke-width="0.8"/>'
            )

    parts.append(
        rigor.draw_x_axis(
            plot_x_left,
            plot_x_right,
            plot_y_bot,
            x_ticks,
            x_min,
            x_max,
            pal=pal,
            fs_tick=fs["ytick"],
            fs_title=fs["yaxis"],
            title=x_title or tr("Reaction coordinate"),
        )
    )
    parts.append(
        rigor.draw_y_axis(
            plot_x_left,
            plot_y_top,
            plot_y_bot,
            y_ticks,
            y_min,
            y_max,
            unit=energy_unit,
            pal=pal,
            fs_tick=fs["ytick"],
            fs_title=fs["yaxis"],
            title=f"{energy_label or tr('Energy')} ({energy_unit})",
            side="left",
        )
    )

    stats = f"n states = {len(states)}"
    if states:
        energies = [state["y"] for state in states]
        stats += f" · ΔE = {max(energies) - min(energies):.1f} {energy_unit}"
    parts.append(
        f'<text x="{plot_x_left:.1f}" y="{header_y + 30:.1f}" font-size="{label_fs}" fill="{pal["ink6"]}">{_xesc(stats)}</text>'
    )

    parts.append(rigor.draw_footer(note, source, pal, fs, plot_x_left, plot_x_right, H - 22))

    return rigor.wrap_svg(parts, W, H, body_font)


def _interp_curve_y(curve, x_query):
    """Linear interpolate y at x_query along a sampled curve."""
    if not curve:
        return None
    if len(curve) == 1:
        return curve[0][1]
    sorted_c = sorted(curve, key=lambda p: p[0])
    if x_query <= sorted_c[0][0]:
        return sorted_c[0][1]
    if x_query >= sorted_c[-1][0]:
        return sorted_c[-1][1]
    for i in range(len(sorted_c) - 1):
        x1, y1 = sorted_c[i]
        x2, y2 = sorted_c[i + 1]
        if x1 <= x_query <= x2 and x2 > x1:
            t = (x_query - x1) / (x2 - x1)
            return y1 + t * (y2 - y1)
    return None


def _free_energy_diagram(
    pathways,
    steps,
    *,
    energy_unit,
    energy_label,
    x_title,
    title,
    subtitle,
    figure_label,
    note,
    source,
    width,
    height,
    font_family,
    palette,
    variant,
):
    """Level-bar free-energy diagram comparing several pathways on shared reaction steps."""
    _variant_is_classic("potential_energy_surface", variant)
    pal = _resolve_palette(palette or "archive_ink")
    body_font, heading_font = _resolve_font(font_family)
    W, H = float(width), float(height)
    paths = [dict(p) for p in pathways]
    if not paths:
        raise ValueError("pathways must contain at least one pathway")
    n = max(len(p.get("energies") or []) for p in paths)
    if n < 2:
        raise ValueError("each pathway needs at least two states in energies")
    steps = [str(s) for s in (steps or [f"S{i}" for i in range(n)])]
    if len(steps) < n:
        raise ValueError("steps must name every state index used by energies")
    for k, p in enumerate(paths):
        es = list(p.get("energies") or [])
        if any(e is not None and not _finite(e) for e in es):
            raise ValueError(f"pathways[{k}].energies must be finite numbers or None")
        if sum(e is not None for e in es) < 2:
            raise ValueError(f"pathways[{k}] needs at least two energies")
        for i in p.get("ts") or []:
            if not (isinstance(i, int) and 0 <= i < len(es)):
                raise ValueError(f"pathways[{k}].ts index {i!r} is out of range")
        p["energies"] = es + [None] * (n - len(es))

    series = pal.get("series") or [pal["ink"], pal["accent"]]
    fs = _dist_font_sizes(W, H, max(4, n))
    tick_fs = fs["ytick"]
    label_fs = max(13.0, fs["label"] * 0.92)
    legend_fs = fs["legend"]
    step_fs = max(13.0, fs["xtick"] * 0.9)
    header_y = (
        24
        + (fs["title"] + 10 if title else 0)
        + (fs["subtitle"] + 10 if subtitle else 0)
        + (fs["figure"] + 10 if figure_label else 0)
    )
    legend_h = legend_fs * 1.6
    plot_x_left, plot_x_right = 120.0, W - 50.0
    header_y += 14 if title else 0
    plot_y_top = header_y + legend_h + 40
    n_guess = max(len(p.get("energies") or []) for p in paths)
    slot_guess = (W - 170.0) / max(1, n_guess)
    step_lines = max(
        len(_wrap_label(str(x), slot_guess * 0.92, step_fs, body_font, bold=True)) for x in steps[:n_guess]
    )
    step_lines = min(step_lines, 3)
    plot_y_bot = H - (step_fs * (1.3 + 1.25 * step_lines) + fs["xaxis"] + 34)

    vals = [e for p in paths for e in p["energies"] if e is not None]
    span = (max(vals) - min(vals)) or 1.0
    # Head-room for the value labels above the highest bar and below the lowest one,
    # so gridlines at the nice-axis ends never strike through them.
    plot_h = max(120.0, plot_y_bot - plot_y_top)
    room = (label_fs * 2.0) / plot_h * span
    y_ticks, y_min, y_max = rigor.nice_axis(min(vals) - room, max(vals) + room, 5)
    y_ticks = [t for t in y_ticks if min(vals) - room <= t <= max(vals) + room] or y_ticks

    slot = (plot_x_right - plot_x_left) / n
    bar = slot * 0.46

    def X(i):
        return plot_x_left + slot * (i + 0.5)

    def Y(v):
        return rigor._lin(v, y_min, y_max, plot_y_bot, plot_y_top)

    parts = rigor.draw_canvas_bg(pal, W, H)
    parts.append(
        rigor.draw_title_block(
            plot_x_left,
            header_y,
            plot_x_right - plot_x_left,
            title=title,
            subtitle=subtitle,
            figure_label=figure_label,
            pal=pal,
            fs=fs,
            body_font=body_font,
            heading_font=heading_font,
        )
    )
    parts.append(
        rigor.draw_grid(
            plot_x_left,
            plot_x_right,
            plot_y_top,
            plot_y_bot,
            pal=pal,
            y_ticks=y_ticks,
            y_min=y_min,
            y_max=y_max,
            orient="horizontal",
        )
    )
    if y_min < 0 < y_max:
        parts.append(
            f'<line x1="{plot_x_left:.1f}" y1="{Y(0):.1f}" x2="{plot_x_right:.1f}" y2="{Y(0):.1f}" '
            f'stroke="{pal["ink4"]}" stroke-width="1" stroke-dasharray="4 4"/>'
        )

    # Offset the bars of overlapping pathways slightly so equal energies stay distinguishable.
    k_paths = len(paths)
    nudge = min(6.0, slot * 0.04)
    occupied = []
    for k, p in enumerate(paths):
        color = p.get("color") or series[k % len(series)]
        es, ts = p["energies"], set(p.get("ts") or [])
        dx = (k - (k_paths - 1) / 2) * nudge
        prev = None
        for i, e in enumerate(es):
            if e is None:
                continue
            x0, x1, y = X(i) - bar / 2 + dx, X(i) + bar / 2 + dx, Y(e)
            if prev is not None:
                pi, pe = prev
                parts.append(
                    f'<path d="M {X(pi) + bar / 2 + dx:.1f} {Y(pe):.1f} L {x0:.1f} {y:.1f}" fill="none" '
                    f'stroke="{color}" stroke-width="1.6" stroke-dasharray="5 4"/>'
                )
            dash = ' stroke-dasharray="7 3"' if i in ts else ""
            parts.append(
                f'<line x1="{x0:.1f}" y1="{y:.1f}" x2="{x1:.1f}" y2="{y:.1f}" stroke="{color}" '
                f'stroke-width="4.5" stroke-linecap="round"{dash}/>'
            )
            occupied.append((x0, y - 6, x1, y + 6))
            prev = (i, e)

    # Energy value labels: at each step the highest pathway is labelled above its bar and the
    # lowest below, so two compared pathways never stack labels; others search for free room.
    texts = []
    grid = [(plot_x_left, Y(t) - 0.6, plot_x_right, Y(t) + 0.6) for t in y_ticks]
    if y_min < 0 < y_max:
        grid.append((plot_x_left, Y(0) - 0.6, plot_x_right, Y(0) + 0.6))

    def hit(bx, extra=()):
        if bx[1] < plot_y_top or bx[3] > plot_y_bot - 2 or bx[0] < plot_x_left + 2:
            return True
        return any(
            bx[0] < q[2] and q[0] < bx[2] and bx[1] < q[3] and q[1] < bx[3]
            for q in list(texts) + occupied + grid + list(extra)
        )

    for i in range(n):
        here = sorted(
            ((p["energies"][i], k) for k, p in enumerate(paths) if p["energies"][i] is not None), reverse=True
        )
        for rank, (e, k) in enumerate(here):
            p = paths[k]
            color = p.get("color") or series[k % len(series)]
            dx = (k - (k_paths - 1) / 2) * nudge
            txt = f"{e:.2f}" if abs(e) < 10 else f"{e:.1f}"
            w = _estimate_label_width_px(txt, label_fs, bold=True, font_family=body_font) * 1.08
            cx = X(i) + dx
            above, below = Y(e) - 9, Y(e) + label_fs + 9
            # Keep the side fixed (top pathway above, bottom pathway below) and only slide away
            # from its bar; a label never jumps to the other pathway's side.
            if len(here) == 1:
                candidates = [above, below] + [above - d for d in (6, 12, 18)] + [below + d for d in (6, 12, 18)]
            elif rank == 0:
                candidates = [above - d for d in (0, 5, 10, 15, 20, 25)]
            elif rank == len(here) - 1:
                candidates = [below + d for d in (0, 5, 10, 15, 20, 25)]
            else:
                candidates = [above, below] + [above - d for d in (6, 12)] + [below + d for d in (6, 12)]
            ty = candidates[0]
            for ty in candidates:
                box = (cx - w / 2, ty - label_fs, cx + w / 2, ty + 3)
                if not hit(box):
                    break
            else:
                ty = candidates[0]
            texts.append((cx - w / 2, ty - label_fs, cx + w / 2, ty + 3))
            parts.append(
                f'<text x="{cx:.1f}" y="{ty:.1f}" font-size="{label_fs:.1f}" fill="{color}" '
                f'text-anchor="middle" font-weight="600">{_xesc(txt)}</text>'
            )

    # Barrier arrows: largest forward barrier per pathway unless explicit ones are given; the value
    # is written in the legend (colour-matched), which keeps the plot free of floating badges.
    accent_w = 1.6
    barrier_text = {}
    for k, p in enumerate(paths):
        color = p.get("color") or series[k % len(series)]
        es, ts = p["energies"], sorted(p.get("ts") or [])
        pairs = [tuple(b) for b in (p.get("barriers") or [])]
        if not pairs and ts:
            best = None
            for t in ts:
                if es[t] is None:
                    continue
                lows = [(es[j], j) for j in range(t) if es[j] is not None]
                if not lows:
                    continue
                lo, j = min(lows)
                if best is None or es[t] - lo > best[0]:
                    best = (es[t] - lo, j, t)
            if best:
                pairs = [(best[1], best[2])]
        for a, b in pairs:
            if es[a] is None or es[b] is None:
                continue
            dx = (k - (k_paths - 1) / 2) * nudge
            ax = X(b) - bar / 2 - 10 - k * 14 + dx
            ya, yb = Y(es[a]), Y(es[b])
            parts.append(
                f'<line x1="{X(a) + bar / 2 + dx:.1f}" y1="{ya:.1f}" x2="{ax:.1f}" y2="{ya:.1f}" stroke="{color}" '
                f'stroke-width="0.9" stroke-dasharray="2 3"/>'
            )
            parts.append(
                f'<line x1="{ax:.1f}" y1="{ya:.1f}" x2="{ax:.1f}" y2="{yb:.1f}" stroke="{color}" stroke-width="{accent_w}"/>'
            )
            top, bot = min(ya, yb), max(ya, yb)
            if bot - top > 12:
                parts.append(
                    f'<polygon points="{ax:.1f},{top:.1f} {ax - 4:.1f},{top + 7:.1f} {ax + 4:.1f},{top + 7:.1f}" fill="{color}"/>'
                )
            barrier_text[k] = es[b] - es[a]

    # Step names under the axis (wrapped), legend on top.
    for i, name in enumerate(steps[:n]):
        lines = _wrap_label(name, slot * 0.92, step_fs, body_font, bold=True)
        for j, line in enumerate(lines[:3]):
            parts.append(
                f'<text x="{X(i):.1f}" y="{plot_y_bot + step_fs * 1.4 + j * step_fs * 1.2:.1f}" '
                f'font-size="{step_fs:.1f}" fill="{pal["ink"]}" text-anchor="middle">{_xesc(line)}</text>'
            )
    parts.append(
        f'<line x1="{plot_x_left:.1f}" y1="{plot_y_bot:.1f}" x2="{plot_x_right:.1f}" y2="{plot_y_bot:.1f}" '
        f'stroke="{pal["ink4"]}" stroke-width="1"/>'
    )
    parts.append(
        f'<text x="{(plot_x_left + plot_x_right) / 2:.1f}" y="{plot_y_bot + step_fs * (1.3 + 1.25 * step_lines) + fs["xaxis"] + 6:.1f}" '
        f'font-size="{fs["xaxis"]:.1f}" fill="{pal["ink"]}" text-anchor="middle">{_xesc(x_title or tr("Reaction coordinate"))}</text>'
    )
    parts.append(
        rigor.draw_y_axis(
            plot_x_left,
            plot_y_top,
            plot_y_bot,
            y_ticks,
            y_min,
            y_max,
            unit="",
            pal=pal,
            fs_tick=tick_fs,
            fs_title=fs["yaxis"],
            title=f"{energy_label or 'ΔG'} ({energy_unit})",
            side="left",
        )
    )
    lx = plot_x_left
    ly = header_y + legend_fs + (10 if title else 0)
    for k, p in enumerate(paths):
        color = p.get("color") or series[k % len(series)]
        name = str(p.get("name", tr("Path {i}", i=k + 1)))
        if k in barrier_text:
            v = barrier_text[k]
            name += f"  ΔG‡ = {v:.2f} {energy_unit}" if abs(v) < 10 else f"  ΔG‡ = {v:.1f} {energy_unit}"
        parts.append(
            f'<line x1="{lx:.1f}" y1="{ly - legend_fs * 0.35:.1f}" x2="{lx + 26:.1f}" y2="{ly - legend_fs * 0.35:.1f}" '
            f'stroke="{color}" stroke-width="4.5" stroke-linecap="round"/>'
        )
        parts.append(
            f'<text x="{lx + 34:.1f}" y="{ly:.1f}" font-size="{legend_fs:.1f}" fill="{pal["ink"]}">{_xesc(name)}</text>'
        )
        lx += 34 + _estimate_label_width_px(name, legend_fs, font_family=body_font) + 28
    if any(p.get("ts") for p in paths):
        parts.append(
            f'<text x="{plot_x_right:.1f}" y="{ly:.1f}" font-size="{legend_fs * 0.85:.1f}" fill="{pal["ink6"]}" '
            f'text-anchor="end">{_xesc(tr("dashed bar = transition state ‡"))}</text>'
        )

    foot_fs = max(13.0, fs["foot"])
    if note:
        parts.append(
            f'<text x="{plot_x_left:.1f}" y="{H - 14:.1f}" font-size="{foot_fs}" fill="{pal["ink6"]}" font-style="italic">{_xesc(note)}</text>'
        )
    if source:
        parts.append(
            f'<text x="{plot_x_right:.1f}" y="{H - 14:.1f}" font-size="{foot_fs}" fill="{pal["ink6"]}" text-anchor="end" font-style="italic">{_xesc(source)}</text>'
        )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}" font-family="{body_font}">'
        + "".join(parts)
        + "</svg>"
    )
