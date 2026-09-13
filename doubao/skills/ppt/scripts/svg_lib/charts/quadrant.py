"""svg_lib/charts/quadrant.py

2x2 quadrant / scatter chart with 5 variants:
  dot_cross / bubble_L / label_box_quadrant_bg / emoji_icon_cross / ring_arrow

Data schema
-----------
data = {
    "items": [(name, x, y, size?), ...],   # size only used by `bubble_L`
    "x_axis": (low, high),                 # x label endpoints, e.g. ("Value", "Premium")
    "y_axis": (low, high),                 # y label endpoints
    "highlight_name"?: str,                # if given, this item is drawn with accent color
    "x_title"?: str,                       # optional axis title
    "y_title"?: str,
    "quadrant_labels"?: (TL, TR, BL, BR)?  # optional big quadrant labels (used by label_box_quadrant_bg)
}

Coordinates x, y expected in [0, 1] (like normalized market data) — anything outside
still renders but clipped inside plot.
"""
from __future__ import annotations
import math
from ._shared import (

    resolve_palette, is_dark_palette, xesc, auto_font_size,
    rgb_tuple, _rgba_with_alpha,
)


from .._common import (_ACC, _INK, _INK1, _INK2, _INK4, _INK6, _derive_series_colors, _prepend_bg_if_dark, _resolve_font, _resolve_palette, _rgb_tuple, _rgba_with_alpha, _xesc, auto_layout_labels, _variant_is_classic, _dispatch_to_svg_lib)
_VARIANTS = {
    "dot_cross",
    "bubble_L",
    "label_box_quadrant_bg",
    "emoji_icon_cross",
    "ring_arrow",
}

_ICONS = ["★", "●", "▲", "■", "◆", "✦", "◉", "❖", "⬢", "▼",
          "◐", "◑", "◒", "◓", "✚"]


def draw_quadrant(
    data: dict,
    variant: str = "dot_cross",
    palette: str = "archive_ink",
    width: float = 900,
    height: float = 620,
    title: str = None,
    subtitle: str = None,
    figure_label: str = None,
) -> str:
    """Render 2x2 quadrant chart."""
    if variant not in _VARIANTS:
        raise ValueError(f"unknown variant {variant!r}. Available: {sorted(_VARIANTS)}")

    items = data.get("items") or []
    if not items:
        raise ValueError("quadrant: data['items'] required non-empty")
    x_axis = data.get("x_axis") or ("Low", "High")
    y_axis = data.get("y_axis") or ("Low", "High")
    x_title = data.get("x_title", "")
    y_title = data.get("y_title", "")
    highlight_name = data.get("highlight_name")
    quadrant_labels = data.get("quadrant_labels")  # (TL, TR, BL, BR)

    pal = resolve_palette(palette)
    ink = pal["ink"]
    accent = pal["accent"]
    secondary = pal["secondary"]
    bg = pal["bg"]
    muted = pal["muted"]
    ink6 = pal["ink6"]; ink4 = pal["ink4"]; ink2 = pal["ink2"]; ink1 = pal["ink1"]

    dark = is_dark_palette(pal)

    W = float(width)
    H = float(height)
    ML = 90.0
    MR = 60.0
    # Reserve extra headroom when we need to render a figure_label under title/subtitle
    if title and figure_label:
        MT = 116.0
    elif title:
        MT = 100.0
    elif figure_label:
        MT = 80.0
    else:
        MT = 60.0
    MB = 80.0
    plot_x = ML
    plot_y = MT
    plot_w = W - ML - MR
    plot_h = H - MT - MB

    # Normalize items → compute px positions
    n = len(items)
    dot_r = max(6.0, min(14.0, 260.0 / max(6, n)))
    # bubble base radius scales down with n for bubble_L (25 items → ~12, 5 items → ~26)
    bubble_r_max = max(14.0, min(38.0, 46.0 - n * 0.9))
    bubble_r_min = max(5.0, min(9.0, 10.0 - n * 0.15))

    # x/y ranges: assume normalized 0..1; but if inputs are outside, we still map linearly using
    # observed min/max
    xs = [it[1] for it in items]
    ys = [it[2] for it in items]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    # ensure sensible span
    if xmax - xmin < 0.01:
        xmin -= 0.5; xmax += 0.5
    if ymax - ymin < 0.01:
        ymin -= 0.5; ymax += 0.5
    # pad
    xpad = (xmax - xmin) * 0.08
    ypad = (ymax - ymin) * 0.08
    xmin_p, xmax_p = xmin - xpad, xmax + xpad
    ymin_p, ymax_p = ymin - ypad, ymax + ypad

    # snap to nice 0..1 if the data looks like 0..1
    if 0 <= xmin and xmax <= 1:
        xmin_p, xmax_p = 0.0, 1.0
    if 0 <= ymin and ymax <= 1:
        ymin_p, ymax_p = 0.0, 1.0

    def sx(x):
        return plot_x + (x - xmin_p) / (xmax_p - xmin_p) * plot_w

    def sy(y):
        return plot_y + (1 - (y - ymin_p) / (ymax_p - ymin_p)) * plot_h

    mid_x = (xmin_p + xmax_p) / 2
    mid_y = (ymin_p + ymax_p) / 2
    mid_px = sx(mid_x)
    mid_py = sy(mid_y)

    label_fs = auto_font_size(n, base=12, min_size=8, max_size=14)

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {int(W)} {int(H)}">']
    parts.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="{bg}"/>')

    # ---- Title / subtitle / figure_label ----
    if title:
        parts.append(
            f'<text x="{ML:.1f}" y="{40:.1f}" font-family="Georgia, serif" '
            f'font-size="22" font-weight="600" fill="{ink}">{xesc(title)}</text>'
        )
    if subtitle:
        parts.append(
            f'<text x="{ML:.1f}" y="{60:.1f}" font-family="Inter, sans-serif" '
            f'font-size="12" fill="{muted}" letter-spacing="0.06em">{xesc(subtitle)}</text>'
        )
    if figure_label:
        # Place under title (or subtitle when both present) with academic caption styling.
        # y=80 sits below title (y=40) and subtitle (y=60) with enough gap; when no title
        # is drawn we lift it to y=32 so it doesn't float in blank space.
        fl_y = 80.0 if title else 32.0
        parts.append(
            f'<text x="{ML:.1f}" y="{fl_y:.1f}" font-family="Inter, sans-serif" '
            f'font-size="11" font-weight="600" fill="{muted}" letter-spacing="0.15em">'
            f'{xesc(figure_label)}</text>'
        )

    # ---- Quadrant background tint (for label_box_quadrant_bg mostly) ----
    if variant == "label_box_quadrant_bg":
        acc_rgb = rgb_tuple(accent)
        sec_rgb = rgb_tuple(secondary)
        tint_a = 0.10 if not dark else 0.16
        # TL, TR, BL, BR
        # TL uses secondary; TR uses accent (bright); BL uses muted grey; BR uses secondary
        tints = [
            (plot_x, plot_y, mid_px - plot_x, mid_py - plot_y, sec_rgb, tint_a * 0.6),        # TL
            (mid_px, plot_y, plot_x + plot_w - mid_px, mid_py - plot_y, acc_rgb, tint_a),     # TR
            (plot_x, mid_py, mid_px - plot_x, plot_y + plot_h - mid_py, sec_rgb, tint_a * 0.4),  # BL
            (mid_px, mid_py, plot_x + plot_w - mid_px, plot_y + plot_h - mid_py, acc_rgb, tint_a * 0.6),  # BR
        ]
        for tx, ty, tw, th, rgb, a in tints:
            parts.append(
                f'<rect x="{tx:.1f}" y="{ty:.1f}" width="{tw:.1f}" height="{th:.1f}" '
                f'fill="rgba({rgb[0]},{rgb[1]},{rgb[2]},{a:.2f})"/>'
            )
        # Big quadrant labels — placed near mid-cross to avoid corner-pill collisions
        if quadrant_labels and len(quadrant_labels) == 4:
            pad = 10
            positions = [
                # TL: right-aligned just left of mid-x, just below plot top
                (mid_px - pad, plot_y + 20, "end"),
                # TR: left-aligned just right of mid-x
                (mid_px + pad, plot_y + 20, "start"),
                # BL: right-aligned just above plot bottom
                (mid_px - pad, plot_y + plot_h - 10, "end"),
                # BR
                (mid_px + pad, plot_y + plot_h - 10, "start"),
            ]
            for lab, (lx, ly, anch) in zip(quadrant_labels, positions):
                parts.append(
                    f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anch}" '
                    f'font-family="Inter, sans-serif" font-size="11" font-weight="700" '
                    f'fill="{ink4}" letter-spacing="0.16em">{xesc(str(lab).upper())}</text>'
                )

    # ---- Axes ----
    axis_stroke = ink6
    if variant == "bubble_L":
        # L-shaped axis: left + bottom only, others removed
        parts.append(
            f'<line x1="{plot_x:.1f}" y1="{plot_y:.1f}" x2="{plot_x:.1f}" y2="{plot_y + plot_h:.1f}" '
            f'stroke="{ink}" stroke-width="1.2"/>'
        )
        parts.append(
            f'<line x1="{plot_x:.1f}" y1="{plot_y + plot_h:.1f}" x2="{plot_x + plot_w:.1f}" y2="{plot_y + plot_h:.1f}" '
            f'stroke="{ink}" stroke-width="1.2"/>'
        )
    elif variant == "ring_arrow":
        # cross axes with arrowheads — draw arrowheads as inline polygons instead of <marker>
        # (marker element is not supported by the embed validator)
        # horizontal through mid
        parts.append(
            f'<line x1="{plot_x:.1f}" y1="{mid_py:.1f}" x2="{plot_x + plot_w:.1f}" y2="{mid_py:.1f}" '
            f'stroke="{ink}" stroke-width="1.1"/>'
        )
        # right arrowhead
        arr_size = 6.0
        ax = plot_x + plot_w
        parts.append(
            f'<polygon points="{ax:.1f},{mid_py:.1f} {ax - arr_size:.1f},{mid_py - arr_size * 0.6:.1f} {ax - arr_size:.1f},{mid_py + arr_size * 0.6:.1f}" '
            f'fill="{ink}"/>'
        )
        # vertical through mid
        parts.append(
            f'<line x1="{mid_px:.1f}" y1="{plot_y + plot_h:.1f}" x2="{mid_px:.1f}" y2="{plot_y:.1f}" '
            f'stroke="{ink}" stroke-width="1.1"/>'
        )
        # top arrowhead (points up)
        ay = plot_y
        parts.append(
            f'<polygon points="{mid_px:.1f},{ay:.1f} {mid_px - arr_size * 0.6:.1f},{ay + arr_size:.1f} {mid_px + arr_size * 0.6:.1f},{ay + arr_size:.1f}" '
            f'fill="{ink}"/>'
        )
    else:
        # dot_cross / label_box_quadrant_bg / emoji_icon_cross → dashed cross + faint box
        parts.append(
            f'<rect x="{plot_x:.1f}" y="{plot_y:.1f}" width="{plot_w:.1f}" height="{plot_h:.1f}" '
            f'fill="none" stroke="{axis_stroke}" stroke-width="0.7"/>'
        )
        parts.append(
            f'<line x1="{mid_px:.1f}" y1="{plot_y:.1f}" x2="{mid_px:.1f}" y2="{plot_y + plot_h:.1f}" '
            f'stroke="{ink4}" stroke-width="0.9" stroke-dasharray="4 3"/>'
        )
        parts.append(
            f'<line x1="{plot_x:.1f}" y1="{mid_py:.1f}" x2="{plot_x + plot_w:.1f}" y2="{mid_py:.1f}" '
            f'stroke="{ink4}" stroke-width="0.9" stroke-dasharray="4 3"/>'
        )

    # ---- Axis endpoint labels ----
    xlow, xhigh = x_axis
    ylow, yhigh = y_axis
    parts.append(
        f'<text x="{plot_x:.1f}" y="{plot_y + plot_h + 22:.1f}" text-anchor="start" '
        f'font-family="Inter, sans-serif" font-size="11" fill="{muted}" letter-spacing="0.10em">'
        f'← {xesc(str(xlow).upper())}</text>'
    )
    parts.append(
        f'<text x="{plot_x + plot_w:.1f}" y="{plot_y + plot_h + 22:.1f}" text-anchor="end" '
        f'font-family="Inter, sans-serif" font-size="11" fill="{muted}" letter-spacing="0.10em">'
        f'{xesc(str(xhigh).upper())} →</text>'
    )
    # y axis rotated
    parts.append(
        f'<text x="{plot_x - 10:.1f}" y="{plot_y + plot_h - 4:.1f}" text-anchor="start" '
        f'font-family="Inter, sans-serif" font-size="11" fill="{muted}" letter-spacing="0.10em" '
        f'transform="rotate(-90 {plot_x - 10:.1f} {plot_y + plot_h - 4:.1f})">'
        f'← {xesc(str(ylow).upper())}</text>'
    )
    parts.append(
        f'<text x="{plot_x - 10:.1f}" y="{plot_y + 4:.1f}" text-anchor="end" '
        f'font-family="Inter, sans-serif" font-size="11" fill="{muted}" letter-spacing="0.10em" '
        f'transform="rotate(-90 {plot_x - 10:.1f} {plot_y + 4:.1f})">'
        f'{xesc(str(yhigh).upper())} →</text>'
    )

    # optional axis titles
    if x_title:
        parts.append(
            f'<text x="{plot_x + plot_w / 2:.1f}" y="{plot_y + plot_h + 46:.1f}" text-anchor="middle" '
            f'font-family="Inter, sans-serif" font-size="12" font-weight="600" fill="{ink}">'
            f'{xesc(x_title)}</text>'
        )
    if y_title:
        cxp = plot_x - 46
        cyp = plot_y + plot_h / 2
        parts.append(
            f'<text x="{cxp:.1f}" y="{cyp:.1f}" text-anchor="middle" '
            f'font-family="Inter, sans-serif" font-size="12" font-weight="600" fill="{ink}" '
            f'transform="rotate(-90 {cxp:.1f} {cyp:.1f})">{xesc(y_title)}</text>'
        )

    # ---- Data points ----
    # decide bubble sizes for bubble_L
    sizes = None
    if variant == "bubble_L":
        sizes = [(it[3] if len(it) > 3 and it[3] is not None else 100) for it in items]
        smin = min(sizes); smax = max(sizes)
        if smax == smin:
            smax = smin + 1
        # radius range scales with n (fewer items → bigger bubbles allowed)
        r_lo = bubble_r_min
        r_hi = bubble_r_max
        def size_r(sz):
            t = (sz - smin) / (smax - smin)
            return r_lo + t ** 0.5 * (r_hi - r_lo)

    acc_rgb = rgb_tuple(accent)
    sec_rgb = rgb_tuple(secondary)

    # ---- Precompute per-item (px, py, r, name) so label placer can see neighbours ----
    names = [it[0] for it in items]
    coords = [(sx(it[1]), sy(it[2])) for it in items]
    if variant == "bubble_L":
        radii = [size_r(sizes[i]) for i in range(n)]
    elif variant == "dot_cross":
        radii = [dot_r + 4 for _ in range(n)]  # halo radius
    elif variant == "emoji_icon_cross":
        # icon glyph height is ~ fs (see emit block). Approx visual radius = fs/2.
        # For crowded scenes we shrink fs; label placer uses the shrunk footprint.
        if n <= 8:
            emoji_fs = max(20.0, (dot_r + 2) * 2.2)
        else:
            emoji_fs = max(15.0, 24.0 - 0.45 * n)
        radii = [emoji_fs / 2 + 2 for _ in range(n)]
    elif variant == "ring_arrow":
        radii = [dot_r + 2 for _ in range(n)]
    else:  # label_box_quadrant_bg — pill is drawn instead of dot, no dot-avoidance needed for label
        radii = [dot_r for _ in range(n)]

    # decide which labels must be kept (highlight + corner extremes when crowded)
    keep_label_idx = set()
    if highlight_name:
        for i, nm in enumerate(names):
            if nm == highlight_name:
                keep_label_idx.add(i)
    if n > 15:
        xs_list = [it[1] for it in items]
        ys_list = [it[2] for it in items]
        keep_label_idx.add(xs_list.index(max(xs_list)))
        keep_label_idx.add(xs_list.index(min(xs_list)))
        keep_label_idx.add(ys_list.index(max(ys_list)))
        keep_label_idx.add(ys_list.index(min(ys_list)))
    else:
        keep_label_idx = set(range(n))

    # Precompute smart label placements for variants that use _append_name_label
    label_plans = None
    if variant in ("dot_cross", "bubble_L", "emoji_icon_cross", "ring_arrow"):
        points_for_place = [(coords[i][0], coords[i][1], radii[i]) for i in range(n)]
        keep_for_place = keep_label_idx if variant == "bubble_L" else (keep_label_idx if n > 12 else set(range(n)))
        # Obstacle lines that must not slice through the label glyph band:
        # the dashed median cross (only present on non-bubble_L variants) and the plot
        # top/bottom borders (validator flags line_through_text for either).
        _hline_ys = [plot_y, plot_y + plot_h]
        _vline_xs = [plot_x, plot_x + plot_w]
        if variant != "bubble_L":
            _hline_ys.append(mid_py)
            _vline_xs.append(mid_px)
        label_plans = _place_scatter_labels(
            points_for_place, names, label_fs,
            plot_x, plot_y, plot_w, plot_h,
            keep_all_idx=keep_for_place,
            hline_ys=_hline_ys, vline_xs=_vline_xs,
        )

    # For label_box_quadrant_bg — precompute pill bboxes.
    # (1) Push each pill fully into its own quadrant (never straddle median) so its text
    #     center does not fall into a neighbour quadrant tint rect.
    # (2) Drop pills that overlap earlier placed pills.
    # (3) Drop pills whose bbox straddles the mid-cross axes (would trip line_through_text).
    pill_plans = None
    if variant == "label_box_quadrant_bg":
        pill_plans = []
        placed_pill_bboxes = []
        fs_pill = label_fs + 1
        pill_order = sorted(range(n), key=lambda k: (0 if names[k] == highlight_name else 1, k))
        pill_slots = [None] * n
        # median lines in px (mid_px, mid_py) are already computed above
        for i in pill_order:
            name = names[i]
            px, py = coords[i]
            text_w = max(46, len(str(name)) * (fs_pill * 0.62) + 18)
            text_h = fs_pill + 12
            bx = px - text_w / 2
            by = py - text_h / 2
            bx = max(plot_x + 2, min(plot_x + plot_w - text_w - 2, bx))
            by = max(plot_y + 2, min(plot_y + plot_h - text_h - 2, by))
            # Push pill away from the median cross so it lives entirely in its own quadrant.
            # Only shove when the dot is genuinely off-median; dots ON the median can straddle.
            eps = 1.0
            # horizontal median (vertical shove)
            if abs(py - mid_py) > 3:
                if py < mid_py:  # dot is above median → pill must stay above
                    if by + text_h > mid_py - eps:
                        by = mid_py - text_h - eps
                else:            # dot is below median → pill stays below
                    if by < mid_py + eps:
                        by = mid_py + eps
                # re-clamp to plot bounds
                by = max(plot_y + 2, min(plot_y + plot_h - text_h - 2, by))
            # vertical median (horizontal shove)
            if abs(px - mid_px) > 3:
                if px < mid_px:
                    if bx + text_w > mid_px - eps:
                        bx = mid_px - text_w - eps
                else:
                    if bx < mid_px + eps:
                        bx = mid_px + eps
                bx = max(plot_x + 2, min(plot_x + plot_w - text_w - 2, bx))
            # Dots that sit *on* the median (|py-mid_py| <= 3 or |px-mid_px| <= 3)
            # need a definitive shove too — otherwise their pill straddles the
            # dashed median line and the text inside gets sliced by
            # embed_svg_line_through_text, AND overlaps the neighbour quadrant
            # tint rect (embed_svg_text_shape_overlap). Pick the side that keeps
            # the pill within its dominant quadrant based on data-space position.
            if abs(py - mid_py) <= 3:
                # pill fully above or below the horizontal median
                if by + text_h > mid_py - eps and by < mid_py + eps:
                    # currently straddles → shove based on where the pill fits
                    up_room = (mid_py - eps) - (plot_y + 2)
                    dn_room = (plot_y + plot_h - 2) - (mid_py + eps)
                    if up_room >= text_h and (dn_room < text_h or up_room >= dn_room):
                        by = mid_py - text_h - eps
                    else:
                        by = mid_py + eps
                    by = max(plot_y + 2, min(plot_y + plot_h - text_h - 2, by))
            if abs(px - mid_px) <= 3:
                if bx + text_w > mid_px - eps and bx < mid_px + eps:
                    lf_room = (mid_px - eps) - (plot_x + 2)
                    rt_room = (plot_x + plot_w - 2) - (mid_px + eps)
                    if lf_room >= text_w and (rt_room < text_w or lf_room >= rt_room):
                        bx = mid_px - text_w - eps
                    else:
                        bx = mid_px + eps
                    bx = max(plot_x + 2, min(plot_x + plot_w - text_w - 2, bx))
            bbox = (bx, by, text_w, text_h)
            # collision with earlier placed pills?
            collides = any(_bbox_overlap(bbox, b, pad=1.0) for b in placed_pill_bboxes)
            # After shove, does the bbox still straddle a median line?
            straddles = False
            if bx < mid_px - eps and bx + text_w > mid_px + eps:
                straddles = True
            if by < mid_py - eps and by + text_h > mid_py + eps:
                straddles = True
            show = True
            if names[i] != highlight_name:
                if collides:
                    show = False
                elif straddles and n > 6:
                    show = False
            if show:
                placed_pill_bboxes.append(bbox)
            pill_slots[i] = {"show": show, "bx": bx, "by": by, "w": text_w, "h": text_h, "fs": fs_pill}
        pill_plans = pill_slots

    # sort items so highlight goes last (drawn on top)
    order = list(range(len(items)))
    if highlight_name:
        order.sort(key=lambda k: 1 if items[k][0] == highlight_name else 0)

    for i in order:
        it = items[i]
        name = it[0]
        px, py = coords[i]
        is_highlight = (highlight_name is not None and name == highlight_name)

        if is_highlight:
            rgb = acc_rgb
        else:
            # cycle secondary/muted for others; make them consistent
            rgb = sec_rgb

        rr, gg, bb = rgb

        if variant == "dot_cross":
            r = dot_r
            parts.append(
                f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{r + 4:.1f}" '
                f'fill="rgba({rr},{gg},{bb},0.15)"/>'
            )
            parts.append(
                f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{r:.1f}" '
                f'fill="rgba({rr},{gg},{bb},0.85)" stroke="rgba({rr},{gg},{bb},1)" stroke-width="1.2"/>'
            )
            parts.append(
                f'<circle cx="{px:.1f}" cy="{py:.1f}" r="1.6" fill="{bg}"/>'
            )
            _emit_label_from_plan(parts, label_plans[i], name, ink, bg, label_fs)

        elif variant == "bubble_L":
            r = radii[i]
            parts.append(
                f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{r:.1f}" '
                f'fill="rgba({rr},{gg},{bb},0.35)" stroke="rgba({rr},{gg},{bb},0.95)" stroke-width="1.4"/>'
            )
            if i in keep_label_idx:
                _emit_label_from_plan(parts, label_plans[i], name, ink, bg, label_fs)

        elif variant == "label_box_quadrant_bg":
            slot = pill_plans[i]
            if not slot["show"]:
                continue
            bx = slot["bx"]; by = slot["by"]
            text_w = slot["w"]; text_h = slot["h"]; fs = slot["fs"]
            tx = bx + text_w / 2
            ty = by + text_h / 2
            parts.append(
                f'<rect x="{bx + 1.2:.1f}" y="{by + 1.8:.1f}" width="{text_w:.1f}" height="{text_h:.1f}" '
                f'rx="{text_h / 2:.1f}" ry="{text_h / 2:.1f}" fill="rgba(0,0,0,0.16)"/>'
            )
            parts.append(
                f'<rect x="{bx:.1f}" y="{by:.1f}" width="{text_w:.1f}" height="{text_h:.1f}" '
                f'rx="{text_h / 2:.1f}" ry="{text_h / 2:.1f}" '
                f'fill="rgba({rr},{gg},{bb},0.95)" stroke="rgba(255,255,255,0.9)" stroke-width="1"/>'
            )
            parts.append(
                f'<text x="{tx:.1f}" y="{ty + fs * 0.36:.1f}" text-anchor="middle" '
                f'font-family="Georgia, serif" font-size="{fs}" font-weight="700" '
                f'fill="rgba(255,255,255,0.98)">{xesc(name)}</text>'
            )

        elif variant == "emoji_icon_cross":
            icon = _ICONS[i % len(_ICONS)]
            r = dot_r + 2
            # For crowded scenes drop the halo circle (it competes with neighbour glyphs).
            # For small N keep it as a soft chip behind the icon.
            if n <= 8:
                parts.append(
                    f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{r + 3:.1f}" '
                    f'fill="rgba({rr},{gg},{bb},0.15)"/>'
                )
            # Emoji glyph size — allow shrinking for large N so glyphs do not devour neighbours.
            # Baseline behaviour (n<=8) preserved: fs stays >= 20.
            if n <= 8:
                fs = max(20, r * 2.2)
            else:
                # linear taper: n=10 → ~19, n=12 → ~18, n=20 → ~15
                fs = max(15.0, 24.0 - 0.45 * n)
            # Clamp emoji baseline so glyph stays inside the plot rect (avoids line_through_text
            # from the axis lines at plot_x/plot_y/plot_x+plot_w/plot_y+plot_h) AND does not
            # straddle the horizontal median line at mid_py (dashed cross line strikes glyph).
            gpy = py
            def _glyph_bounds(g):
                return (g + fs * 0.36 - fs * 1.1, g + fs * 0.36 + fs * 0.2)
            glyph_top, glyph_bot = _glyph_bounds(gpy)
            if glyph_top < plot_y + 1:
                gpy += (plot_y + 1 - glyph_top)
                glyph_top, glyph_bot = _glyph_bounds(gpy)
            if glyph_bot > plot_y + plot_h - 1:
                gpy -= (glyph_bot - (plot_y + plot_h - 1))
                glyph_top, glyph_bot = _glyph_bounds(gpy)
            # median-line avoidance: validator's band is 15%-70% of text bbox height.
            # text bbox top = y_attr - fs*0.8, so band [y_attr - 0.65*fs, y_attr - 0.1*fs].
            # y_attr = gpy + fs*0.36. Ensure mid_py is outside that band.
            for line_y in (mid_py,):
                y_attr = gpy + fs * 0.36
                band_top = y_attr - 0.65 * fs
                band_bot = y_attr - 0.1 * fs
                if band_top - 1 <= line_y <= band_bot + 1:
                    # push glyph either just above line or just below
                    up_shift = (band_bot + 2) - line_y   # to move band above line
                    dn_shift = line_y - (band_top - 2)   # to move band below line
                    if py <= line_y:
                        gpy -= up_shift
                    else:
                        gpy += dn_shift
            parts.append(
                f'<text x="{px:.1f}" y="{gpy + fs * 0.36:.1f}" text-anchor="middle" '
                f'font-family="Helvetica, Arial, sans-serif" font-size="{fs:.1f}" '
                f'fill="rgba({rr},{gg},{bb},1)" paint-order="stroke" '
                f'stroke="{bg}" stroke-width="2.4">{icon}</text>'
            )
            _emit_label_from_plan(parts, label_plans[i], name, ink, bg, label_fs)

        elif variant == "ring_arrow":
            r = dot_r + 2
            parts.append(
                f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{r:.1f}" '
                f'fill="rgba({rr},{gg},{bb},0.10)" stroke="rgba({rr},{gg},{bb},1)" stroke-width="2.2"/>'
            )
            parts.append(
                f'<circle cx="{px:.1f}" cy="{py:.1f}" r="1.8" fill="rgba({rr},{gg},{bb},1)"/>'
            )
            _emit_label_from_plan(parts, label_plans[i], name, ink, bg, label_fs)

    parts.append('</svg>')
    return "".join(parts)


def _emit_label_from_plan(parts, plan, name, ink, bg, fs):
    """Emit a text label at pre-computed position from _place_scatter_labels result."""
    if plan is None or not plan.get("show"):
        return
    lx = plan["lx"]; ly = plan["ly"]; anchor = plan["anchor"]
    parts.append(
        f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}" '
        f'font-family="Inter, sans-serif" font-size="{fs}" font-weight="600" '
        f'fill="{ink}" paint-order="stroke" stroke="{bg}" stroke-width="3" '
        f'stroke-linejoin="round">{xesc(name)}</text>'
    )


def _append_name_label(parts, px, py, r, name, ink, bg, fs,
                       plot_x=None, plot_y=None, plot_w=None, plot_h=None):
    """Place a name label near the point with a background halo.

    Default position: above-right of point.
    If plot bounds provided: flip to left/below when default would clip.
    """
    est_w = max(1, len(str(name))) * (fs * 0.62) + 6
    # default above-right
    lx = px + r + 4
    ly = py - r - 4
    anchor = "start"
    if plot_x is not None and plot_w is not None:
        right_edge = plot_x + plot_w
        # if label would exceed right border → put on left (anchor=end)
        if lx + est_w > right_edge - 2:
            lx = px - r - 4
            anchor = "end"
    if plot_y is not None and plot_h is not None:
        # if label above would clip plot top → put below point
        if ly - fs < plot_y + 2:
            ly = py + r + fs + 2
    parts.append(
        f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}" '
        f'font-family="Inter, sans-serif" font-size="{fs}" font-weight="600" '
        f'fill="{ink}" paint-order="stroke" stroke="{bg}" stroke-width="3" '
        f'stroke-linejoin="round">{xesc(name)}</text>'
    )


def _text_bbox(lx, ly, anchor, name, fs):
    """Return (bx, by, bw, bh) for a text label rendered at (lx, ly) with anchor.

    Matches the validator's bbox estimator (ascii*0.7 + cjk*1.1) * fs and height=fs*1.3.
    ly is the baseline; top is ly - fs*1.1.
    """
    s = str(name)
    n_ascii = sum(1 for c in s if ord(c) < 128)
    n_cjk = len(s) - n_ascii
    w = max(1, n_ascii * fs * 0.7 + n_cjk * fs * 1.1)
    h = fs * 1.3
    if anchor == "start":
        bx = lx
    elif anchor == "end":
        bx = lx - w
    else:
        bx = lx - w / 2
    by = ly - fs * 1.1
    return (bx, by, w, h)


def _bbox_overlap(a, b, pad=1.0):
    """Return True if bboxes (x,y,w,h) overlap with pad tolerance."""
    return not (a[0] + a[2] + pad <= b[0] or b[0] + b[2] + pad <= a[0]
                or a[1] + a[3] + pad <= b[1] or b[1] + b[3] + pad <= a[1])


def _center_inside_circle(cx, cy, ccx, ccy, cr):
    """Check if point (cx, cy) is inside circle centered at (ccx, ccy) radius cr."""
    return (cx - ccx) ** 2 + (cy - ccy) ** 2 <= cr * cr


def _bbox_overlaps_circle(bbox, ccx, ccy, cr):
    """Rect-vs-circle-bounding-box overlap. Matches validator behaviour which uses
    axis-aligned bounding boxes for both text and shapes (see _svg_bbox_overlap)."""
    bx, by, bw, bh = bbox
    cbx = ccx - cr; cby = ccy - cr
    return not (bx + bw <= cbx or cbx + 2 * cr <= bx
                or by + bh <= cby or cby + 2 * cr <= by)


def _place_scatter_labels(points, names, fs, plot_x, plot_y, plot_w, plot_h,
                          keep_all_idx=None, median_x=None, median_y=None,
                          point_data_xy=None, hline_ys=None, vline_xs=None):
    """Compute label positions for scatter points, avoiding other dots + text overlaps.

    points: list of (px, py, r) — dot center + radius (including any halo margin)
    names:  list of str
    fs:     label font size
    keep_all_idx: optional set of indices that must always be labeled (e.g. highlight)
    median_x, median_y: optional px positions of the quadrant median cross. When given,
        each label bbox must sit fully on the same side of the median as its own dot,
        otherwise the label's center falls into a neighbour quadrant tint and the
        validator flags text_shape_overlap against that tint rect.
    point_data_xy: optional list of (data_x, data_y) — required alongside median_x/y so
        we know which side of the median each dot belongs to.
    hline_ys, vline_xs: optional obstacle horizontal / vertical line coordinates. When a
        candidate label bbox's glyph band (15%-70% of height) crosses any of these lines
        the validator flags ``embed_svg_line_through_text``; scoring penalises such
        candidates so the placer prefers offsets that clear the dashed median cross and
        plot borders.

    Returns: list of dict per point:
        {"show": bool, "lx": float, "ly": float, "anchor": "start"|"end"|"middle",
         "bbox": (bx,by,bw,bh)}

    Algorithm:
      - Try 8 candidate positions per point (E, W, SE, SW, NE, NW, N, S)
      - Prefer candidates that don't overlap ANY other dot's expanded circle
      - Reject candidates whose bbox crosses the quadrant median (when given)
      - Among ok candidates, prefer the one with lowest text-vs-text overlap
      - If nothing works and n is large → hide label (unless keep_all_idx)
    """
    N = len(points)
    keep_all_idx = keep_all_idx or set()
    check_median = median_x is not None and median_y is not None and point_data_xy is not None
    hline_ys = hline_ys or []
    vline_xs = vline_xs or []

    def candidates(px, py, r):
        # (dx, dy, anchor) — dy is offset for baseline (positive = below dot center)
        # r+4 gap keeps label clear of the dot circle. When neighbouring dots
        # overlap this one (dense scatters), the "near ring" of 8 candidates all
        # collide with the neighbour's circle. Emit a "far ring" too — pushed out
        # by ~2r so the label clears the merged neighbour blob.
        gap = 4
        far = r + gap + int(round(r * 1.4)) + 2  # extra push for dense clusters
        near = [
            (r + gap, -(r * 0.4), "start"),         # E (right of dot)
            (-(r + gap), -(r * 0.4), "end"),        # W (left of dot)
            (r + gap, r + fs, "start"),             # SE
            (-(r + gap), r + fs, "end"),            # SW
            (r + gap, -(r + 2), "start"),           # NE (above-right, default)
            (-(r + gap), -(r + 2), "end"),          # NW
            (0, -(r + fs * 0.4), "middle"),         # N
            (0, r + fs + 2, "middle"),              # S
        ]
        far_ring = [
            (far, -(r * 0.4), "start"),             # E-far
            (-far, -(r * 0.4), "end"),              # W-far
            (far, r + fs, "start"),                 # SE-far
            (-far, r + fs, "end"),                  # SW-far
            (far, -(r + 2), "start"),               # NE-far
            (-far, -(r + 2), "end"),                # NW-far
            (0, -(far + fs * 0.4), "middle"),       # N-far
            (0, far + fs + 2, "middle"),            # S-far
        ]
        return near + far_ring

    def in_bounds(bbox):
        bx, by, bw, bh = bbox
        return (bx >= plot_x - 1 and bx + bw <= plot_x + plot_w + 1
                and by >= plot_y - 1 and by + bh <= plot_y + plot_h + 1)

    def crosses_median(bbox, i):
        if not check_median:
            return False
        bx, by, bw, bh = bbox
        dx_data, dy_data = point_data_xy[i]
        # Vertical median: bbox must stay on dot's side of median_x
        # Only apply when the dot is meaningfully offset from the median line;
        # dots that sit exactly on the median can be labelled on either side.
        px_own, py_own, _ = points[i]
        eps = 2.0
        if abs(px_own - median_x) > eps:
            if px_own < median_x and bx + bw > median_x + eps:
                return True
            if px_own > median_x and bx < median_x - eps:
                return True
        if abs(py_own - median_y) > eps:
            if py_own < median_y and by + bh > median_y + eps:
                return True
            if py_own > median_y and by < median_y - eps:
                return True
        return False

    def line_through(lx, ly, anchor, name):
        """Return True if any obstacle line crosses the glyph band (15%-70% of bbox height)
        as the embed validator's `embed_svg_line_through_text` rule does. That rule fires
        whenever a horizontal line intersects a text box's vertical [15%, 70%] slice AND
        spans at least half the text width horizontally — since our obstacle lines all
        run full-plot-width or full-plot-height, the horizontal-span condition is
        automatically satisfied and it's sufficient to check the band overlap here.

        NOTE: the placer's ``_text_bbox`` uses a padded box (height=fs*1.3, top=ly-1.1*fs)
        for text-vs-text collision scoring, but the validator uses a tighter box
        (height=fs, top=ly-0.8*fs). Recompute the tight box here so we agree with
        what the validator actually flags.
        """
        s = str(name)
        n_ascii = sum(1 for c in s if ord(c) < 128)
        n_cjk = len(s) - n_ascii
        w = max(1, n_ascii * fs * 0.7 + n_cjk * fs * 1.1)
        if anchor == "start":
            bx = lx
        elif anchor == "end":
            bx = lx - w
        else:
            bx = lx - w / 2
        by = ly - fs * 0.8
        band_top = by + fs * 0.15
        band_bot = by + fs * 0.7
        for hy in hline_ys:
            if band_top <= hy <= band_bot:
                return True
        return False

    results = [None] * N
    placed_boxes = []  # for text-vs-text conflict tracking

    # Sort so we place important labels first (higher priority get first pick)
    # Priority: keep_all, then reading-order
    order = sorted(range(N), key=lambda i: (0 if i in keep_all_idx else 1, i))

    for i in order:
        px, py, r = points[i]
        name = names[i]
        best = None
        best_score = None
        for dx, dy, anchor in candidates(px, py, r):
            lx = px + dx
            ly = py + dy
            bbox = _text_bbox(lx, ly, anchor, name, fs)
            if not in_bounds(bbox):
                continue
            median_cross = crosses_median(bbox, i)
            line_hit = line_through(lx, ly, anchor, name)
            # count dot overlaps (label center inside other dot is very bad)
            dot_overlap = 0
            center_inside = 0
            bcx = bbox[0] + bbox[2] / 2
            bcy = bbox[1] + bbox[3] / 2
            for j, (opx, opy, orad) in enumerate(points):
                if j == i:
                    continue
                # use a slightly expanded dot radius (halo)
                if _bbox_overlaps_circle(bbox, opx, opy, orad + 2):
                    dot_overlap += 1
                    if _center_inside_circle(bcx, bcy, opx, opy, orad + 2):
                        center_inside += 1
            # count text-vs-text overlaps with already placed
            text_overlap = sum(1 for b in placed_boxes if _bbox_overlap(bbox, b, pad=1.0))
            # line_through weight sits between median_cross (1000) and center_inside
            # (100): a labelled dot near an axis or median line should flip to the
            # opposite side even if that gives up a preferable NE→SW swap, but if the
            # only way to clear the line is to smash into another dot we prefer that.
            score = (int(median_cross) * 1000 + int(line_hit) * 500
                     + center_inside * 100 + dot_overlap * 10 + text_overlap)
            if best is None or score < best_score:
                best = (lx, ly, anchor, bbox, score, dot_overlap, center_inside, text_overlap, median_cross)
                best_score = score
                if score == 0:
                    break
        if best is None:
            # nothing fit in bounds → force default NE
            lx = px + r + 4
            ly = py - r - 2
            anchor = "start"
            bbox = _text_bbox(lx, ly, anchor, name, fs)
            results[i] = {"show": (i in keep_all_idx or N <= 12),
                          "lx": lx, "ly": ly, "anchor": anchor, "bbox": bbox}
            if results[i]["show"]:
                placed_boxes.append(bbox)
            continue
        lx, ly, anchor, bbox, score, dot_ov, cent_in, txt_ov, med_cross = best
        # decide show / hide
        show = True
        if i not in keep_all_idx:
            # Hard fail: if placement is really bad (label center falls inside
            # another dot, or crosses the quadrant median) the validator would
            # flag text_shape_overlap regardless of N. Drop the label rather than
            # keep a broken one.
            if cent_in > 0 or med_cross:
                show = False
            elif N > 12 and dot_ov > 0 and N > 15:
                show = False
        results[i] = {"show": show, "lx": lx, "ly": ly, "anchor": anchor, "bbox": bbox}
        if show:
            placed_boxes.append(bbox)

    return results


def make_quadrant_2x2(items: Sequence,
                      x_axis: Sequence[str] = None,
                      y_axis: Sequence[str] = None,
                      x_title: str = None,
                      y_title: str = None,
                      x_title_sub: str = None,
                      y_title_sub: str = None,
                      highlight_index: int = None,
                      quadrant_labels: Sequence[str] = None,
                      quadrant_subs: Sequence[str] = None,
                      x_range: Sequence[float] = None,
                      y_range: Sequence[float] = None,
                      x_median: float = None,
                      y_median: float = None,
                      title: str = None,
                      subtitle: str = None,
                      figure_label: str = None,
                      note: str = None,
                      source: str = None,
                      categories: dict = None,
                      category_labels: dict = None,
                      insights: list = None,
                      font_family: str = None,
                      palette=None,
                variant: str = None) -> str:
    """
    2×2 象限散点图（Dandelion FT/Bloomberg academic 风格）。

    items: list，每项支持：
      - (name, x, y)                          # 简单
      - (name, x, y, size)                    # size = point 半径 (px)，或作为 bubble 参数量
      - (name, x, y, size, category_key)      # category_key → categories[key] 派生色
      - (name, x, y, size, category_key, note) # note = 点标签下方斜体小字
      - 或 dict: {"name","x","y","size","category","note"}

    坐标系：
      - x_range/y_range: (min, max) 数据范围。缺省用 items 的 min/max 外扩 10%。
      - x_median/y_median: 中位线位置，缺省用 (min+max)/2。
      - x_title/y_title: 主轴标题；x_title_sub/y_title_sub 副标（斜体灰）
      - x_axis/y_axis: 简单模式（0-1 归一化）时的端点两级标签 ("低","高")

    象限：
      - quadrant_labels=(左上, 右上, 左下, 右下)；缺省 ("PREMIUM","LEADERS","LAGGARDS","VALUE")
      - quadrant_subs=(...) 4 个副标句

    顶部：title / subtitle / figure_label（学术论文风）
    右侧面板：categories 图例 + point size 图例 + insights 卡片
    底部：note / source 页脚

    categories: {key: rgba} 显式类别色；不传时从 palette 派生
    category_labels: {key: display}；不传用 key
    insights: [(title, body, key_or_rgba), ...] 关键观察卡片（右侧下方）
    highlight_index: 高亮某点（额外描边）

    palette: 支持 palette str/dict；使用 accent 系派生 categories 色
    """
    if not _variant_is_classic('quadrant_2x2', variant):
        _data = {"items": list(items), "x_axis": tuple(x_axis) if x_axis else (0.0,1.0), "y_axis": tuple(y_axis) if y_axis else (0.0,1.0), "x_title": x_title, "y_title": y_title, "highlight_name": (items[highlight_index][0] if highlight_index is not None and 0 <= highlight_index < len(items) else None)}
        return _dispatch_to_svg_lib(
            'quadrant_2x2', variant, _data,
            title=title, subtitle=subtitle, figure_label=figure_label,
            palette=palette, font_family=font_family,
        )

    if not items:
        raise ValueError("quadrant_2x2: at least one item required")

    _pal = _resolve_palette(palette)
    _body_font, _head_font = _resolve_font(font_family)
    _INK, _INK6, _INK4, _INK2, _INK1, _ACC = (
        _pal["ink"], _pal["ink6"], _pal["ink4"], _pal["ink2"], _pal["ink1"], _pal["accent"]
    )
    c_muted = _pal.get("muted", _rgba_with_alpha(_INK, 0.6))
    c_bg = _pal.get("bg")
    PAPER = c_bg if c_bg else "rgba(255,255,255,1)"

    # ---------- 归一化 items ----------
    norm = []
    for it in items:
        if isinstance(it, dict):
            name = it.get("name", "")
            x = it["x"]; y = it["y"]
            size = it.get("size", 100)
            cat = it.get("category") or it.get("cat")
            note_ = it.get("note")
        elif isinstance(it, (list, tuple)):
            if len(it) < 3:
                raise ValueError(f"quadrant_2x2: item too short: {it}")
            name = it[0]; x = it[1]; y = it[2]
            size = it[3] if len(it) > 3 else 100
            cat = it[4] if len(it) > 4 else None
            note_ = it[5] if len(it) > 5 else None
            if isinstance(cat, bool):
                cat = None  # 兼容老 highlight bool
        else:
            raise ValueError(f"quadrant_2x2: item must be tuple/dict: {it}")
        # size None → default
        if size is None:
            size = 100
        norm.append({"name": str(name), "x": float(x), "y": float(y),
                     "size": float(size), "cat": cat, "note": note_})

    # 检测简单模式（无 x_range 且 items 都在 [0,1]）
    simple_mode = (x_range is None and y_range is None
                   and all(0 <= it["x"] <= 1 and 0 <= it["y"] <= 1 for it in norm))
    if simple_mode:
        x_range = (0, 1)
        y_range = (0, 1)

    # 坐标范围
    if x_range is None:
        xs = [it["x"] for it in norm]
        pad = (max(xs) - min(xs)) * 0.1 if len(xs) > 1 else 1
        x_range = (min(xs) - pad, max(xs) + pad)
    if y_range is None:
        ys = [it["y"] for it in norm]
        pad = (max(ys) - min(ys)) * 0.1 if len(ys) > 1 else 1
        y_range = (min(ys) - pad, max(ys) + pad)
    X_MIN, X_MAX = float(x_range[0]), float(x_range[1])
    Y_MIN, Y_MAX = float(y_range[0]), float(y_range[1])

    if x_median is None:
        x_median = (X_MIN + X_MAX) / 2
    if y_median is None:
        y_median = (Y_MIN + Y_MAX) / 2

    # ---------- 类别色 ----------
    used_cats = []
    seen = set()
    for it in norm:
        c = it["cat"]
        if c and c not in seen:
            used_cats.append(c); seen.add(c)
    if categories is None:
        if used_cats:
            series = _derive_series_colors(_pal, len(used_cats))
            categories = {c: series[i] for i, c in enumerate(used_cats)}
        else:
            categories = {}
    if category_labels is None:
        category_labels = {c: c.replace("_", " ").title() for c in used_cats}

    # ---------- 画布 ----------
    # 如果有 categories / insights / 简单模式（无 categories 时省略右侧面板缩小画布）
    has_side = bool(used_cats) or bool(insights)
    W = 1500 if has_side else 1050
    H = 820
    MARGIN_L = 120
    MARGIN_R = 400 if has_side else 60
    MARGIN_T = 155 if title else 80
    MARGIN_B = 130 if (note or source) else 90

    plot_x = MARGIN_L
    plot_w = W - MARGIN_L - MARGIN_R
    plot_y = MARGIN_T
    plot_h = H - MARGIN_T - MARGIN_B

    # ---------- 字号自适应基准 ----------
    # viewBox 尺寸 + 数据规模 (n = items 数) 双重自适应。
    # slide 里排 3 张 SVG 缩到 400px 宽时字也读得清。
    _n_items_fs = len(norm)
    _base_fs = min(W, H) * 0.02   # W=1050/1500,H=820 → 16.4
    if _n_items_fs <= 4:
        _fs_data = _base_fs * 1.4
    elif _n_items_fs <= 8:
        _fs_data = _base_fs * 1.0
    elif _n_items_fs <= 15:
        _fs_data = _base_fs * 0.8
    else:
        _fs_data = max(_base_fs * 0.6, 10)

    # 各类文字：主体（title/subtitle/figure_label）按 _base_fs 倍数；
    # 数据点标签按 _fs_data；辅助文字（tick/median/corner）介于两者之间。
    _fs_title    = round(min(34.0, max(20.0, _base_fs * 1.6)), 1)
    _fs_subtitle = round(min(16.0, max(10.0, _base_fs * 0.75)), 1)
    _fs_figure   = round(min(13.0, max(9.0,  _base_fs * 0.62)), 1)
    _fs_tick     = round(min(15.0, max(10.0, _base_fs * 0.7)),  1)
    _fs_axis_title = round(min(18.0, max(11.0, _base_fs * 0.85)), 1)
    _fs_corner   = round(min(18.0, max(11.0, _base_fs * 0.85)), 1)
    _fs_corner_sub = round(min(13.0, max(9.0, _base_fs * 0.65)), 1)
    _fs_median   = round(min(12.0, max(8.5, _base_fs * 0.6)),  1)
    _fs_endpoint = round(min(13.0, max(9.0, _base_fs * 0.7)), 1)  # 简单模式端点
    _fs_side_hdr = round(min(13.0, max(9.0, _base_fs * 0.65)), 1)
    _fs_side_lbl = round(min(14.0, max(10.0, _base_fs * 0.75)), 1)

    def x_of(v):
        return plot_x + (v - X_MIN) / max(1e-9, X_MAX - X_MIN) * plot_w

    def y_of(v):
        return plot_y + (Y_MAX - v) / max(1e-9, Y_MAX - Y_MIN) * plot_h

    # 点半径：如果 size 值范围较大（>50），当作参数量 log 缩放；否则当作直接 px 半径
    all_sizes = [it["size"] for it in norm]
    max_size = max(all_sizes) if all_sizes else 1
    bubble_mode = max_size > 50  # size 是参数量而非半径 px
    def r_of(s):
        if bubble_mode:
            s_v = max(1, s)
            return 5 + math.log10(s_v) * 5.2
        # 直接当 px 半径，但至少 4，至多 20
        return max(4, min(20, float(s) if s else 8))

    parts = []

    # 深底 palette 加背景
    if c_bg:
        parts.append(f'<rect width="{W}" height="{H}" fill="{PAPER}"/>')

    # ---------- 顶部标题 ----------
    if title:
        parts.append(f'<text x="{MARGIN_L}" y="52" '
                     f'font-family="{_head_font}" '
                     f'font-size="{_fs_title}" font-weight="600" fill="{_INK}" letter-spacing=".05em">'
                     f'{_xesc(title)}</text>')
    if subtitle:
        parts.append(f'<text x="{MARGIN_L}" y="76" '
                     f'font-family="{_body_font}" font-size="{_fs_subtitle}" fill="{c_muted}" '
                     f'letter-spacing=".16em">{_xesc(subtitle)}</text>')
        # 分隔线（跨越到右侧面板）
        parts.append(f'<line x1="{MARGIN_L}" y1="92" x2="{W-40}" y2="92" '
                     f'stroke="{_INK}" stroke-width="0.8"/>')
    if figure_label:
        parts.append(f'<text x="{MARGIN_L}" y="112" font-family="{_body_font}" font-size="{_fs_figure}" '
                     f'fill="{c_muted}" font-weight="600" letter-spacing=".15em">{_xesc(figure_label)}</text>')
        label_w = max(72, len(figure_label) * 8 + 20)
        note_txt = f"2×2 quadrant · {len(norm)} items"
        parts.append(f'<text x="{MARGIN_L+label_w}" y="112" font-family="{_body_font}" font-size="{_fs_figure}" '
                     f'fill="{c_muted}" letter-spacing=".04em">{_xesc(note_txt)}</text>')

    # ---------- 象限背景 tint ----------
    mx = x_of(x_median)
    my = y_of(y_median)

    if quadrant_labels is None:
        # 默认四象限名（academic 版）
        quadrant_labels = ("PREMIUM", "LEADERS", "LAGGARDS", "VALUE")
    if quadrant_subs is None:
        quadrant_subs = ("Top score, lower value",
                         "High performance · high value",
                         "Underperform on both axes",
                         "Efficient, mid-tier score")

    # 4 象限位置：左上 / 右上 / 左下 / 右下
    quad_regions = [
        (plot_x, plot_y, mx, my),                      # 左上（PREMIUM）
        (mx, plot_y, plot_x + plot_w, my),             # 右上（LEADERS）
        (plot_x, my, mx, plot_y + plot_h),             # 左下（LAGGARDS）
        (mx, my, plot_x + plot_w, plot_y + plot_h),    # 右下（VALUE）
    ]
    # 每个象限的 tint 色：从 accent 派生 4 色（distinct 模式）
    tints = _derive_series_colors(_pal, 4, mode="distinct")
    tint_alphas = [0.08, 0.10, 0.06, 0.06]
    for i, (qx1, qy1, qx2, qy2) in enumerate(quad_regions):
        tint = tints[i]
        # 转成低 alpha 版本
        r, g, b = _rgb_tuple(tint)
        parts.append(f'<rect x="{qx1:.1f}" y="{qy1:.1f}" '
                     f'width="{qx2-qx1:.1f}" height="{qy2-qy1:.1f}" '
                     f'fill="rgba({r},{g},{b},{tint_alphas[i]})"/>')

    # ---------- 象限角标签 ----------
    # 角标放到 plot 外沿（顶部/底部），而不是象限内部：内部角落经常与靠近轴端的
    # marker circle 撞。放到外沿时需要避开轴端点标签（← LOW / HIGH →，y=plot_y+plot_h+22）
    # 和 x_title（y=plot_y+plot_h+46）。
    # 大数据（items > 12）时省略象限副标：副标会与 dot label 冲突。
    _n_items = len(norm)
    _show_corner_labels = _n_items <= 12
    _show_corner_subs = _n_items <= 8
    if _show_corner_labels:
        # 顶部两角：紧贴 plot 上沿；底部两角：放到 x_title 之下、page footer 之上。
        top_y = plot_y - 12
        # x_title 在 plot_y+plot_h+46；再下移 20 给它空间。
        bot_y = plot_y + plot_h + (68 if x_title else 44)
        corner_positions = [
            (plot_x + 12,               top_y, "start", quadrant_labels[0], quadrant_subs[0], tints[0], "above"),
            (plot_x + plot_w - 12,      top_y, "end",   quadrant_labels[1], quadrant_subs[1], tints[1], "above"),
            (plot_x + 12,               bot_y, "start", quadrant_labels[2], quadrant_subs[2], tints[2], "below"),
            (plot_x + plot_w - 12,      bot_y, "end",   quadrant_labels[3], quadrant_subs[3], tints[3], "below"),
        ]
        for cx, cy, anch, lab, sub, col, side in corner_positions:
            parts.append(f'<text x="{cx:.1f}" y="{cy:.1f}" text-anchor="{anch}" '
                         f'font-family="{_body_font}" font-size="{_fs_corner}" font-weight="700" '
                         f'fill="{col}" letter-spacing=".18em">{_xesc(lab)}</text>')
            if sub and _show_corner_subs:
                # 顶部的 sub 放在 lab 之上（更远离 plot），底部的 sub 放在 lab 之下。
                # 保留足够 baseline 差，避免 lab (h≈14) 与 sub (h≈11) bbox 相交（需 ≥17）。
                sub_dy = -18 if side == "above" else 18
                parts.append(f'<text x="{cx:.1f}" y="{cy + sub_dy:.1f}" text-anchor="{anch}" '
                             f'font-family="{_body_font}" font-size="{_fs_corner_sub}" font-style="italic" '
                             f'fill="{c_muted}">{_xesc(sub)}</text>')

    # ---------- 网格 + 刻度 ----------
    # 自动选 tick：数据范围 span / 8 nice-number
    def _nice_ticks(vmin, vmax, target=8):
        span = vmax - vmin
        if span <= 0:
            return [vmin]
        raw = span / target
        mag = 10 ** math.floor(math.log10(max(raw, 1e-9)))
        for nice in (1, 2, 2.5, 5, 10):
            if raw / mag <= nice:
                step = nice * mag
                break
        else:
            step = 10 * mag
        t = math.ceil(vmin / step) * step
        ticks = []
        while t <= vmax + 1e-9:
            ticks.append(t); t += step
        return ticks

    xticks = _nice_ticks(X_MIN, X_MAX)
    yticks = _nice_ticks(Y_MIN, Y_MAX)

    grid_stroke = _rgba_with_alpha(_INK, 0.05)
    for xv in xticks:
        px = x_of(xv)
        if abs(xv - x_median) < 1e-6:
            continue
        parts.append(f'<line x1="{px:.1f}" y1="{plot_y}" x2="{px:.1f}" y2="{plot_y+plot_h}" '
                     f'stroke="{grid_stroke}" stroke-width="0.6"/>')
    for yv in yticks:
        py = y_of(yv)
        if abs(yv - y_median) < 1e-6:
            continue
        parts.append(f'<line x1="{plot_x}" y1="{py:.1f}" x2="{plot_x+plot_w}" y2="{py:.1f}" '
                     f'stroke="{grid_stroke}" stroke-width="0.6"/>')

    # 中位线（双虚线，粗一些）
    parts.append(f'<line x1="{mx:.1f}" y1="{plot_y}" x2="{mx:.1f}" y2="{plot_y+plot_h}" '
                 f'stroke="{c_muted}" stroke-width="1.2" stroke-dasharray="4 4"/>')
    parts.append(f'<line x1="{plot_x}" y1="{my:.1f}" x2="{plot_x+plot_w}" y2="{my:.1f}" '
                 f'stroke="{c_muted}" stroke-width="1.2" stroke-dasharray="4 4"/>')

    # 中位线标注 "MEDIAN"
    parts.append(f'<text x="{mx:.1f}" y="{plot_y - 6}" text-anchor="middle" '
                 f'font-family="{_body_font}" font-size="{_fs_median}" fill="{c_muted}" '
                 f'letter-spacing=".14em">MEDIAN</text>')
    parts.append(f'<text x="{plot_x + plot_w + 6}" y="{my + 3:.1f}" text-anchor="start" '
                 f'font-family="{_body_font}" font-size="{_fs_median}" fill="{c_muted}" '
                 f'letter-spacing=".14em">MEDIAN</text>')

    # X/Y 轴边框
    parts.append(f'<line x1="{plot_x}" y1="{plot_y+plot_h}" x2="{plot_x+plot_w}" y2="{plot_y+plot_h}" '
                 f'stroke="{_INK}" stroke-width="1"/>')
    parts.append(f'<line x1="{plot_x}" y1="{plot_y}" x2="{plot_x}" y2="{plot_y+plot_h}" '
                 f'stroke="{_INK}" stroke-width="1"/>')

    # 刻度标签
    def _fmt_tick(v):
        if abs(v) >= 100:
            return f"{int(round(v)):,}"
        elif abs(v) >= 1:
            return f"{v:g}"
        else:
            return f"{v:.2f}"
    # 在 simple_mode（0..1 归一化）下省略数字刻度：象限图的语义是"象限"，
    # 具体坐标不重要，端点由 LOW/HIGH/MASS/PREMIUM 之类语义 label 承载，
    # 数字刻度反而会和端点 label 挤在一起。
    if not simple_mode:
        for xv in xticks:
            px = x_of(xv)
            parts.append(f'<text x="{px:.1f}" y="{plot_y+plot_h+18}" text-anchor="middle" '
                         f'font-family="{_body_font}" font-size="{_fs_tick}" fill="{c_muted}">'
                         f'{_xesc(_fmt_tick(xv))}</text>')
        for yv in yticks:
            py = y_of(yv)
            parts.append(f'<text x="{plot_x-10}" y="{py+3.5:.1f}" text-anchor="end" '
                         f'font-family="{_body_font}" font-size="{_fs_tick}" fill="{c_muted}">'
                         f'{_xesc(_fmt_tick(yv))}</text>')

    # ---------- 轴标题 + 副标 ----------
    if x_title:
        tspan = f' <tspan fill="{c_muted}" font-weight="400" font-style="italic">{_xesc(x_title_sub)}</tspan>' if x_title_sub else ""
        parts.append(f'<text x="{plot_x + plot_w/2}" y="{plot_y + plot_h + 42}" text-anchor="middle" '
                     f'font-family="{_body_font}" font-size="{_fs_axis_title}" font-weight="600" '
                     f'fill="{_INK}">{_xesc(x_title)}  →  {tspan}</text>')
    if y_title:
        tspan = f' <tspan fill="{c_muted}" font-weight="400" font-style="italic">{_xesc(y_title_sub)}</tspan>' if y_title_sub else ""
        ytx = plot_x - 60
        yty = plot_y + plot_h / 2
        parts.append(f'<text x="{ytx}" y="{yty}" transform="rotate(-90 {ytx} {yty})" '
                     f'text-anchor="middle" font-family="{_body_font}" font-size="{_fs_axis_title}" '
                     f'font-weight="600" fill="{_INK}">'
                     f'{_xesc(y_title)}  →  {tspan}</text>')

    # ---------- 简单模式端点标签 ----------
    if simple_mode and (x_axis or y_axis):
        if x_axis and len(x_axis) >= 2:
            parts.append(f'<text x="{plot_x + 8}" y="{plot_y + plot_h + 18}" '
                         f'font-family="{_body_font}" font-size="{_fs_endpoint}" font-weight="700" '
                         f'fill="{c_muted}" letter-spacing=".1em">{_xesc(str(x_axis[0]).upper())}</text>')
            parts.append(f'<text x="{plot_x + plot_w - 8}" y="{plot_y + plot_h + 18}" '
                         f'text-anchor="end" font-family="{_body_font}" font-size="{_fs_endpoint}" '
                         f'font-weight="700" fill="{c_muted}" letter-spacing=".1em">{_xesc(str(x_axis[1]).upper())}</text>')
        if y_axis and len(y_axis) >= 2:
            parts.append(f'<text x="{plot_x - 10}" y="{plot_y + plot_h - 4}" '
                         f'text-anchor="end" font-family="{_body_font}" font-size="{_fs_endpoint}" '
                         f'font-weight="700" fill="{c_muted}" letter-spacing=".1em">{_xesc(str(y_axis[0]).upper())}</text>')
            parts.append(f'<text x="{plot_x - 10}" y="{plot_y + 12}" '
                         f'text-anchor="end" font-family="{_body_font}" font-size="{_fs_endpoint}" '
                         f'font-weight="700" fill="{c_muted}" letter-spacing=".1em">{_xesc(str(y_axis[1]).upper())}</text>')

    # ---------- 点 + 标签 ----------
    # _fs_label 是数据点名字（跟 _fs_data 挂钩，n 大字小）；_fs_note 是小字备注
    _fs_label = round(min(20.0, max(9.5, _fs_data * 0.9)), 1)
    # items > 6 时会走"只画 keep_label_idx 的 label"分支，最多 ~5 张 label，
    # 剩下的字号可以放大到 4-item 档（1.4×）水平，保证 slide 里 <310px 窄 embed
    # 缩放后仍能读清。上限用 22 抑制过大画面。
    if len(norm) > 6:
        _fs_label = round(min(22.0, max(_fs_label, _base_fs * 1.35)), 1)
    _fs_note = round(min(14.0, max(8.0, _fs_label * 0.72)), 1)
    _fs_label_hl = round(min(24.0, _fs_label * 1.15), 1)   # highlight 稍大
    # 收集所有水平/垂直"障碍线"的 y/x 位置：包括 median 中线、grid 刻度线、plot 边框。
    # 这些线一旦穿过 label bbox 就会被 validator 判 line_through_text；
    # 而 median 中线两侧是不同象限，label 中心跨过就会触发 text_shape_overlap。
    _mx = x_of(x_median)
    _my = y_of(y_median)
    _h_line_ys = [_my, plot_y, plot_y + plot_h]
    _v_line_xs = [_mx, plot_x, plot_x + plot_w]
    for yv in yticks:
        _h_line_ys.append(y_of(yv))
    for xv in xticks:
        _v_line_xs.append(x_of(xv))
    # 标签偏移：简单交替左右（点在 x_median 左侧标签朝右，右侧朝左）；同时避免超出边界。
    # 若点靠近 median 或任何 grid 线，把标签推到 dot 的另一侧，避免 label bbox
    # 被线穿过、或 label 中心落到相邻象限触发 text_shape_overlap。
    def _label_offset(it_x, it_y, r, name=""):
        px = x_of(it_x)
        py = y_of(it_y)
        fs = _fs_label
        # 估计 label 文字宽度（与 auto_layout_labels 里的 bbox 计算保持一致）
        n_ascii = sum(1 for c in str(name) if ord(c) < 128)
        n_cjk = len(str(name)) - n_ascii
        text_w = n_ascii * fs * 0.7 + n_cjk * fs * 1.1
        # ---- 纵向 dy：默认 dy=4；若 label bbox 会覆盖某条水平线，推到 dot 的另一侧 ----
        def _bbox_covers_hline(ty):
            top = ty - fs * 1.1
            bot = ty + fs * 0.2
            for ly in _h_line_ys:
                # validator 判 line_through_text 用 15%~70% 中段；这里留 2px 余量
                if top - 2 <= ly <= bot + 2:
                    return True
            return False
        dy = 4
        if _bbox_covers_hline(py + dy):
            dy_up = -(r + 6)          # 完全在 dot 上方
            dy_dn = r + fs + 4        # 完全在 dot 下方
            up_ok = not _bbox_covers_hline(py + dy_up)
            dn_ok = not _bbox_covers_hline(py + dy_dn)
            if up_ok and (not dn_ok or it_y >= y_median):
                dy = dy_up
            elif dn_ok:
                dy = dy_dn
            elif up_ok:
                dy = dy_up
        # ---- 横向 anchor + dx：默认按 median 左右分侧 ----
        anchor = "end" if it_x > x_median else "start"
        dx = (-r - 4) if it_x > x_median else (r + 4)
        # 检查 label bbox 是否跨越了 vertical 中线 (mx) 或穿过其他 vertical grid 线
        def _bbox_x_range(anch, dxv):
            tx = px + dxv
            if anch == "start":
                return (tx, tx + text_w)
            elif anch == "end":
                return (tx - text_w, tx)
            else:
                return (tx - text_w / 2, tx + text_w / 2)
        def _bbox_crosses_vline(anch, dxv):
            lx, rx = _bbox_x_range(anch, dxv)
            for vx in _v_line_xs:
                # 只关心中线：validator 只把 median 与象限 rect 关联到 text_shape_overlap
                # 但为了稳，覆盖 mx 和 plot 边界即可（grid 竖线 stroke 太细，不会触发）
                if vx in (_mx, plot_x, plot_x + plot_w):
                    if lx - 1 <= vx <= rx + 1:
                        return True
            return False
        if _bbox_crosses_vline(anchor, dx):
            # 翻到另一侧
            alt_anchor = "start" if anchor == "end" else "end"
            alt_dx = (r + 4) if anchor == "end" else (-r - 4)
            if not _bbox_crosses_vline(alt_anchor, alt_dx):
                anchor = alt_anchor
                dx = alt_dx
        return (dx, dy, anchor)

    stroke_c = PAPER if c_bg else "rgba(255,255,255,1)"

    # 若 items 全都没传 category，按索引从 palette 派生 distinct 色（避免所有点同色）
    _has_any_cat = any(it["cat"] for it in norm)
    _auto_colors = None
    if not _has_any_cat and len(norm) >= 2:
        _auto_colors = _derive_series_colors(_pal, len(norm), mode="distinct")

    # 决定哪些标签必须保留（highlight + 4 个极值点）；其余在密集场景由 smart placer 决定去留
    _keep_label_idx = set()
    if highlight_index is not None and 0 <= highlight_index < len(norm):
        _keep_label_idx.add(highlight_index)
    _N = len(norm)
    # items > 6 时开始收敛：viewBox 只有 1050(无右侧面板) 或 1500，slide 里 embed
    # 缩到 <310px 宽时，7 张 label 全画会让每个字仅 ~4px 视觉高。此时保留
    # highlight + 4 个极值点（最多 5 张 label），其余点只画 dot、不画名字，
    # 保住关键语义（"我们 vs 竞品最好/最差"）同时让保留下来的 label 有余量放大。
    # 大量数据（>15）沿用原极值点保留策略（策略等价，不影响 baseline）。
    if _N > 6:
        _xs = [it["x"] for it in norm]
        _ys = [it["y"] for it in norm]
        _keep_label_idx.add(_xs.index(max(_xs)))
        _keep_label_idx.add(_xs.index(min(_xs)))
        _keep_label_idx.add(_ys.index(max(_ys)))
        _keep_label_idx.add(_ys.index(min(_ys)))

    # items > 6 时启用 smart placer 收敛：仅保留 highlight + 4 极值的 label，
    # 其余点只画 dot。密集散点（N ≤ 10）在 medium 规模也可能出现两个 dot 的圆
    # 相互侵占的情况——此时 `_label_offset` 只考虑网格线，不知道邻居 dot，会把
    # label 放到另一 dot 的圆里，触发 embed_svg_text_shape_overlap。把 smart
    # placer 的阈值下拉到 N > 3，且传入 hline/vline 以保留原来的 grid-line
    # 避让语义；同时对 N ≤ 6 用 keep_all=set(range(N)) 保住所有 label（与
    # `_label_offset` 分支的默认 show=True 语义一致）。
    _use_smart_placer = _N > 3
    _smart_plans = None
    if _use_smart_placer:
        _points_for_place = [(x_of(it["x"]), y_of(it["y"]), r_of(it["size"])) for it in norm]
        _names_for_place = [it["name"] for it in norm]
        _data_xy_for_place = [(it["x"], it["y"]) for it in norm]
        # N ≤ 6: 保留所有 label（不做收敛），placer 用 far-ring 候选避开邻居 dot；
        # N > 6: 仅保留 keep_label_idx（highlight + 4 极值），其余下方 hide。
        if _N <= 6:
            _keep_for_place = set(range(_N))
        else:
            _keep_for_place = _keep_label_idx
        _smart_plans = _place_scatter_labels(
            _points_for_place, _names_for_place, _fs_label,
            plot_x, plot_y, plot_w, plot_h,
            keep_all_idx=_keep_for_place,
            median_x=mx, median_y=my,
            point_data_xy=_data_xy_for_place,
            hline_ys=_h_line_ys, vline_xs=_v_line_xs,
        )
        # placer 内部仅在 N>12 且发生冲突时才主动隐藏非 keep 项，
        # 而窄 embed 场景 (<310px) 下即使不冲突，多个 label 缩放后也糊成一片。
        # items > 6 时统一按 keep_label_idx 收敛：非 keep 的 label 一律 hide，
        # dot 保留。保住关键语义（highlight + 4 极值）同时让保留下来的 label
        # 有余量放大到 22pt 级。N ≤ 6 保留全部 label。
        if _N > 6:
            for _idx_i in range(_N):
                if _idx_i not in _keep_label_idx and _smart_plans[_idx_i] is not None:
                    _smart_plans[_idx_i]["show"] = False

    # 先算 label 初始位置，跑一次避让
    _label_data = []  # (i, px, py, r, col, init_tx, init_ty, anchor, name, note, show)
    for i, it in enumerate(norm):
        px = x_of(it["x"])
        py = y_of(it["y"])
        r = r_of(it["size"])
        if it["cat"]:
            col = categories.get(it["cat"]) or _INK
        elif _auto_colors is not None:
            col = _auto_colors[i]
        else:
            col = _INK
        if _use_smart_placer and _smart_plans is not None:
            plan = _smart_plans[i]
            show = plan["show"]
            init_tx = plan["lx"]; init_ty = plan["ly"]; anch = plan["anchor"]
        else:
            dx, dy, anch = _label_offset(it["x"], it["y"], r, it["name"])
            init_tx = px + dx; init_ty = py + dy
            # items > 6 时非 keep 的 label 不画，只保留 dot（narrow embed 可读性）。
            show = (_N <= 6) or (i in _keep_label_idx)
        _label_data.append((i, px, py, r, col, init_tx, init_ty, anch, it["name"], it["note"], show))

    # 组装 auto_layout 输入：(x, y, text, anchor, fontsize, "y")
    # 只对 show=True 的 label 做避让；不显示的保留占位以便后续 zip 对齐
    _lay_input = [(ld[5], ld[6], ld[8], ld[7], _fs_label, "y") for ld in _label_data]
    _lay_out = auto_layout_labels(_lay_input, min_gap=4.0, iterations=40)

    for idx, (i, px, py, r, col, init_tx, init_ty, anch, name, note, show) in enumerate(_label_data):
        # 光晕
        r_r, r_g, r_b = _rgb_tuple(col)
        parts.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{r+2:.1f}" '
                     f'fill="rgba({r_r},{r_g},{r_b},0.18)"/>')
        # 主体
        parts.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{r:.1f}" '
                     f'fill="{_rgba_with_alpha(col, 0.85)}" '
                     f'stroke="{stroke_c}" stroke-width="1.2"/>')
        # 内白点
        parts.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="1.2" fill="{stroke_c}"/>')

        # highlight 加环
        if highlight_index is not None and i == highlight_index:
            parts.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{r+4:.1f}" '
                         f'fill="none" stroke="{col}" stroke-width="1.5" '
                         f'stroke-dasharray="3 2"/>')

        if not show:
            continue

        # 避让后的位置
        tx, ty = _lay_out[idx]
        # 若避让把 label 推得远（y 位移 > 6px），补一条从点到 label 的浅引线
        if abs(ty - init_ty) > 6:
            # 引线起点：点边缘（沿 label 方向的边）；终点：label 中心的 y
            lead_x1 = px + (r if anch == "start" else -r)
            lead_y1 = py
            lead_x2 = tx + (0 if anch == "middle" else (-4 if anch == "start" else 4))
            lead_y2 = ty - 4
            parts.append(f'<line x1="{lead_x1:.1f}" y1="{lead_y1:.1f}" '
                         f'x2="{lead_x2:.1f}" y2="{lead_y2:.1f}" '
                         f'stroke="{_rgba_with_alpha(col, 0.5)}" stroke-width="0.6"/>')

        # 标签（白/背景描边加粗到 4px，多层保护背景对比）
        # highlight 项字号稍大 (1.15×)
        _is_hl = (highlight_index is not None and i == highlight_index)
        _lbl_fs = _fs_label_hl if _is_hl else _fs_label
        parts.append(f'<text x="{tx:.1f}" y="{ty:.1f}" text-anchor="{anch}" '
                     f'font-family="{_body_font}" font-size="{_lbl_fs}" font-weight="700" '
                     f'fill="{_INK}" '
                     f'paint-order="stroke" stroke="{PAPER}" stroke-width="4" '
                     f'stroke-linejoin="round">{_xesc(name)}</text>')
        # note 小字
        if note:
            parts.append(f'<text x="{tx:.1f}" y="{ty + _fs_label + 1:.1f}" text-anchor="{anch}" '
                         f'font-family="{_body_font}" font-size="{_fs_note}" fill="{c_muted}" '
                         f'font-style="italic" '
                         f'paint-order="stroke" stroke="{PAPER}" stroke-width="3">'
                         f'{_xesc(note)}</text>')

    # ---------- 右侧面板 ----------
    if has_side:
        side_x = W - MARGIN_R + 40
        side_y = MARGIN_T
        side_w = 320

        # 类别图例
        if used_cats:
            parts.append(f'<text x="{side_x}" y="{side_y}" font-family="{_body_font}" '
                         f'font-size="{_fs_side_hdr}" fill="{c_muted}" font-weight="600" letter-spacing=".15em">'
                         f'CATEGORY</text>')
            parts.append(f'<line x1="{side_x}" y1="{side_y+8}" x2="{side_x+side_w}" y2="{side_y+8}" '
                         f'stroke="{_INK}" stroke-width="0.8"/>')
            cat_count = {}
            for it in norm:
                c = it["cat"]
                if c:
                    cat_count[c] = cat_count.get(c, 0) + 1
            for i, key in enumerate(used_cats):
                col = categories[key]
                label = category_labels.get(key, key)
                ly = side_y + 26 + i * 24
                parts.append(f'<circle cx="{side_x + 8}" cy="{ly - 3}" r="6" '
                             f'fill="{_rgba_with_alpha(col, 0.85)}" stroke="{stroke_c}" stroke-width="1"/>')
                parts.append(f'<text x="{side_x + 22}" y="{ly}" font-family="{_body_font}" '
                             f'font-size="{_fs_side_lbl}" font-weight="600" fill="{_INK}">{_xesc(label)}</text>')
                parts.append(f'<text x="{side_x + side_w - 8}" y="{ly}" text-anchor="end" '
                             f'font-family="{_body_font}" font-size="{_fs_side_hdr}" fill="{c_muted}">'
                             f'{cat_count.get(key, 0)}</text>')
            side_y_cursor = side_y + 26 + len(used_cats) * 24 + 24
        else:
            side_y_cursor = side_y

        # POINT SIZE 图例（仅 bubble_mode）
        if bubble_mode and all_sizes:
            parts.append(f'<text x="{side_x}" y="{side_y_cursor}" font-family="{_body_font}" '
                         f'font-size="{_fs_side_hdr}" fill="{c_muted}" font-weight="600" letter-spacing=".15em">'
                         f'POINT SIZE — parameters</text>')
            parts.append(f'<line x1="{side_x}" y1="{side_y_cursor+8}" x2="{side_x+side_w}" y2="{side_y_cursor+8}" '
                         f'stroke="{_INK4}" stroke-width="0.5"/>')
            sample_x = side_x + 20
            sample_y = side_y_cursor + 34
            # 三档 sample
            s_min = min(all_sizes)
            s_max = max(all_sizes)
            s_mid = (s_min * s_max) ** 0.5
            samples = [(s_min, f"~{int(s_min)}"), (s_mid, f"~{int(s_mid)}"), (s_max, f"{int(s_max)}+")]
            for i, (b, lbl) in enumerate(samples):
                sx = sample_x + i * 100
                r = r_of(b)
                parts.append(f'<circle cx="{sx}" cy="{sample_y}" r="{r:.1f}" '
                             f'fill="{_rgba_with_alpha(c_muted, 0.5)}" stroke="{stroke_c}" stroke-width="1.2"/>')
                parts.append(f'<text x="{sx}" y="{sample_y + r + 12:.1f}" text-anchor="middle" '
                             f'font-family="{_body_font}" font-size="{_fs_side_hdr}" fill="{c_muted}">'
                             f'{_xesc(lbl)}</text>')
            side_y_cursor += 90

        # KEY OBSERVATIONS
        if insights:
            parts.append(f'<text x="{side_x}" y="{side_y_cursor}" font-family="{_body_font}" '
                         f'font-size="{_fs_side_hdr}" fill="{c_muted}" font-weight="600" letter-spacing=".15em">'
                         f'KEY OBSERVATIONS</text>')
            parts.append(f'<line x1="{side_x}" y1="{side_y_cursor+8}" x2="{side_x+side_w}" y2="{side_y_cursor+8}" '
                         f'stroke="{_INK4}" stroke-width="0.5"/>')
            card_bg = _rgba_with_alpha(_INK, 0.03) if not c_bg else _rgba_with_alpha(_INK, 0.08)
            for i, ins in enumerate(insights):
                if not isinstance(ins, (tuple, list)) or len(ins) < 2:
                    continue
                ins_title = ins[0]; ins_body = ins[1]
                col_ref = ins[2] if len(ins) > 2 else None
                # col_ref 可以是 category key 或 rgba
                if isinstance(col_ref, str) and col_ref in categories:
                    ins_col = categories[col_ref]
                elif isinstance(col_ref, str) and col_ref.startswith("rgba"):
                    ins_col = col_ref
                else:
                    ins_col = tints[i % len(tints)] if len(tints) else _ACC
                iy = side_y_cursor + 26 + i * 78
                parts.append(f'<rect x="{side_x}" y="{iy}" width="{side_w}" height="66" '
                             f'fill="{card_bg}" stroke="{_INK4}" stroke-width="0.6"/>')
                parts.append(f'<rect x="{side_x}" y="{iy}" width="4" height="66" fill="{ins_col}"/>')
                parts.append(f'<text x="{side_x + 14}" y="{iy + 18}" font-family="{_body_font}" '
                             f'font-size="{_fs_side_lbl}" font-weight="700" fill="{_INK}">{_xesc(ins_title)}</text>')
                # body 分行
                max_line_chars = 45
                words = str(ins_body).split(" ")
                lines = []; cur = ""
                for w in words:
                    if len(cur) + len(w) + 1 > max_line_chars:
                        lines.append(cur); cur = w
                    else:
                        cur = (cur + " " + w).strip()
                if cur: lines.append(cur)
                for k, ln in enumerate(lines[:4]):
                    parts.append(f'<text x="{side_x + 14}" y="{iy + 33 + k*12}" '
                                 f'font-family="{_body_font}" font-size="{_fs_side_hdr}" fill="{c_muted}">'
                                 f'{_xesc(ln)}</text>')

    # ---------- 底部脚注 ----------
    if note or source:
        foot_y = H - 45
        parts.append(f'<line x1="{MARGIN_L}" y1="{foot_y-14}" x2="{W-40}" y2="{foot_y-14}" '
                     f'stroke="{_INK4}" stroke-width="0.5"/>')
        if note:
            parts.append(f'<text x="{MARGIN_L}" y="{foot_y}" font-family="{_body_font}" '
                         f'font-size="{_fs_side_hdr}" fill="{c_muted}">'
                         f'<tspan font-weight="600">Notes.</tspan> {_xesc(note)}</text>')
        if source:
            parts.append(f'<text x="{MARGIN_L}" y="{foot_y+14}" font-family="{_body_font}" '
                         f'font-size="{_fs_side_hdr}" fill="{c_muted}">'
                         f'<tspan font-weight="600">Source.</tspan> {_xesc(source)}</text>')
        if figure_label:
            parts.append(f'<text x="{W-40}" y="{foot_y+14}" text-anchor="end" '
                         f'font-family="{_body_font}" font-size="{_fs_figure}" fill="{c_muted}" '
                         f'letter-spacing=".05em">{_xesc(figure_label)}</text>')

    body = "".join(parts)
    _svg_result = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}">{body}</svg>'
    return _prepend_bg_if_dark(_svg_result, _pal)


# ==============================================================
# 17) Violin 小提琴分布
# ==============================================================
