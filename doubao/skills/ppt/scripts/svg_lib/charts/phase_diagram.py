"""Academic chart: phase diagram (temperature / pressure / composition plane with
colored phase regions, bold boundaries, and critical / triple / eutectic point
"""

from __future__ import annotations

from .._common import (
    _derive_series_colors,
    _dist_font_sizes,
    _estimate_label_width_px,
    _resolve_font,
    _resolve_palette,
    _rgba_with_alpha,
    _variant_is_classic,
    _xesc,
)
from . import _academic_rigor as rigor
from ._shared import tr


def _polygon_centroid(pts):
    """Simple vertex-average centroid."""
    if not pts:
        return (0.0, 0.0)
    sx = sum(p[0] for p in pts) / len(pts)
    sy = sum(p[1] for p in pts) / len(pts)
    return (sx, sy)


# Marker helpers for critical / triple / eutectic points
def _critical_marker(cx, cy, color, size=10.0):
    """Upward triangle for critical points."""
    h = size * 0.9
    pts = [
        (cx, cy - h),
        (cx - size, cy + h * 0.6),
        (cx + size, cy + h * 0.6),
    ]
    poly = " ".join(f"{p[0]:.1f},{p[1]:.1f}" for p in pts)
    return f'<polygon points="{poly}" fill="{color}" stroke="rgba(28,28,26,1)" stroke-width="1.2"/>'


def _triple_marker(cx, cy, color, size=8.0):
    """Filled circle for triple points."""
    return (
        f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{size:.1f}" fill="{color}" '
        f'stroke="rgba(28,28,26,1)" stroke-width="1.2"/>'
    )


def _eutectic_marker(cx, cy, color, size=9.0):
    """Rotated square (diamond) for eutectic points."""
    pts = [
        (cx, cy - size),
        (cx + size, cy),
        (cx, cy + size),
        (cx - size, cy),
    ]
    poly = " ".join(f"{p[0]:.1f},{p[1]:.1f}" for p in pts)
    return f'<polygon points="{poly}" fill="{color}" stroke="rgba(28,28,26,1)" stroke-width="1.2"/>'


def make_phase_diagram(
    regions,
    *,
    critical_points=None,
    x_unit: str = "",
    y_unit: str = "",
    x_title: str | None = None,
    y_title: str | None = None,
    title: str | None = None,
    subtitle: str | None = None,
    figure_label: str | None = None,
    note: str | None = None,
    source: str | None = None,
    width: float = 1200,
    height: float = 900,
    font_family: str | None = None,
    palette=None,
    variant: str | None = None,
) -> str:
    """Phase diagram (filled phase regions + boundaries + critical points).

    Parameters
    ----------
    regions : list of dict
        Each entry: ``name`` (str), ``boundary`` (list of ``(x,y)``), optional
        ``color`` (rgba str), optional ``label_pos`` (``(x,y)``, defaults to
        polygon vertex centroid).
    critical_points : list of dict, optional
        Each entry: ``x``, ``y``, ``label``, optional ``kind`` ∈
        {``"critical"``, ``"triple"``, ``"eutectic"``}.
    """
    _variant_is_classic("phase_diagram", variant)
    if palette is None:
        palette = "archive_ink"
    pal = _resolve_palette(palette)
    body_font, heading_font = _resolve_font(font_family)
    W, H = float(width), float(height)
    n_regions = len(regions)
    fs = _dist_font_sizes(W, H, max(4, n_regions))

    margin_top = 120
    margin_bot = 140
    margin_left = 120
    margin_right = 80
    if H < rigor.COMPACT_HEIGHT:
        # Title block anchors at plot_y_top - 30 here (6 px higher than the shared layout).
        margin_top, margin_bot, margin_left = rigor.compact_margins(
            fs, title=title, subtitle=subtitle, figure_label=figure_label, footer=bool(note or source), top_extra=6
        )
        margin_right = 36
    plot_x_left = margin_left
    plot_x_right = W - margin_right
    plot_y_top = margin_top
    plot_y_bot = H - margin_bot

    all_x = []
    all_y = []
    for reg in regions:
        for px, py in reg.get("boundary", []):
            all_x.append(px)
            all_y.append(py)
    if critical_points:
        for cp in critical_points:
            all_x.append(cp["x"])
            all_y.append(cp["y"])
    if not all_x:
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}">'
            f'<text x="{W / 2}" y="{H / 2}" text-anchor="middle" font-size="16" '
            f'fill="{pal["ink6"]}">{_xesc(tr("No data"))}</text></svg>'
        )

    x_ticks, x_min, x_max = rigor.nice_axis(min(all_x), max(all_x), 6)
    y_ticks, y_min, y_max = rigor.nice_axis(min(all_y), max(all_y), 5)

    def X(v):
        return rigor._lin(v, x_min, x_max, plot_x_left, plot_x_right)

    def Y(v):
        return rigor._lin(v, y_min, y_max, plot_y_bot, plot_y_top)

    _derive_series_colors(pal, max(1, n_regions), saturation_hint=0.42)

    parts = rigor.draw_canvas_bg(pal, W, H)

    parts.append(
        rigor.draw_title_block(
            plot_x_left,
            plot_y_top - 30,
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
            x_ticks=x_ticks,
            x_min=x_min,
            x_max=x_max,
            orient="both",
        )
    )

    # C-polish:
    #   - "Supercritical" (or region whose ``highlight=True``) → accent fill at
    #     0.30 opacity + accent stroke → draws the eye to the physically
    #     distinguished region.
    #   - Other regions → neutral muted fill at 0.15 opacity + muted stroke,
    #     keeping them visible but secondary.
    label_entries = []
    accent_c = pal.get("accent", "rgba(217,106,46,1)")
    muted_c = pal.get("muted", pal.get("ink6", "rgba(94,80,62,0.6)"))
    for i, reg in enumerate(regions):
        boundary = reg.get("boundary", [])
        if len(boundary) < 3:
            continue
        screen_pts = [(X(px), Y(py)) for px, py in boundary]
        poly_str = " ".join(f"{p[0]:.1f},{p[1]:.1f}" for p in screen_pts)
        name = reg.get("name", "") or ""
        is_highlight = bool(reg.get("highlight")) or "supercritical" in name.lower()
        if is_highlight:
            base_color = reg.get("color") or accent_c
            fill_c = _rgba_with_alpha(base_color, 0.30)
            stroke_c = base_color
            stroke_w = 2.4
        else:
            base_color = reg.get("color") or muted_c
            fill_c = _rgba_with_alpha(base_color, 0.15)
            stroke_c = _rgba_with_alpha(base_color, 0.75)
            stroke_w = 1.8
        parts.append(
            f'<polygon points="{poly_str}" fill="{fill_c}" '
            f'stroke="{stroke_c}" stroke-width="{stroke_w}" stroke-linejoin="round"/>'
        )
        label_pos = reg.get("label_pos")
        if label_pos is None:
            cx, cy = _polygon_centroid(boundary)
        else:
            cx, cy = label_pos
        # Polygon width in screen px — used to shrink the region label when the
        # polygon is tiny (would otherwise overflow neighboring regions / sit on
        # top of nearby critical-point markers).
        xs_scr = [p[0] for p in screen_pts]
        poly_w_px = max(xs_scr) - min(xs_scr)
        label_entries.append((X(cx), Y(cy), name, poly_w_px, is_highlight))

    # R2 fix: when a region label (e.g. "Supercritical") lands near a critical
    # point marker, push the label off-centroid so the triangle isn't covered.
    cp_screen = []
    if critical_points:
        for cp in critical_points:
            cp_screen.append((X(cp["x"]), Y(cp["y"])))
    label_fs_base = max(13.0, fs["label"] * 1.05)
    for lx, ly, name, poly_w, is_highlight in label_entries:
        if not name:
            continue
        # Adaptive down-size: when polygon width is smaller than the label bbox the italic label would hang out over
        # neighbouring regions or markers.
        est_w = _estimate_label_width_px(name, label_fs_base, bold=True, font_family=body_font)
        if poly_w > 0 and est_w > poly_w * 0.6:
            scale = (poly_w * 0.9) / (est_w + 20.0)
            fs_cur = max(13.0, min(label_fs_base, label_fs_base * scale))
        else:
            fs_cur = label_fs_base
        # If any critical-point marker lies within fs_cur*2 of the region label centroid, nudge the label vertically
        # away so the triangle marker and label-glyph bboxes don't overlap.
        lx_adj, ly_adj = lx, ly
        for cpx, cpy in cp_screen:
            if abs(cpx - lx_adj) < fs_cur * 3.5 and abs(cpy - ly_adj) < fs_cur * 2.0:
                # push the region label away in whichever direction has more
                # breathing room inside the plot area
                if ly_adj > (plot_y_top + plot_y_bot) * 0.5:
                    ly_adj = max(ly_adj - fs_cur * 1.8, plot_y_top + fs_cur)
                else:
                    ly_adj = min(ly_adj + fs_cur * 1.8, plot_y_bot - fs_cur)
                break
        # Short canvases pack the y gridlines tightly; keep the label's glyph band
        # (baseline - 0.85 fs .. baseline + 0.2 fs) off every horizontal gridline.
        _grid_ys = [Y(v) for v in (y_ticks or []) if y_min <= v <= y_max]
        for _ in range(12):
            hit = next((gy for gy in _grid_ys if ly_adj - fs_cur * 0.95 <= gy <= ly_adj + fs_cur * 0.3), None)
            if hit is None:
                break
            up = hit + fs_cur * 0.95 + 1 - ly_adj  # shift down so the gridline sits above the glyphs
            dn = ly_adj - (hit - fs_cur * 0.3 - 1)  # shift up so it sits below
            ly_adj = ly_adj + up if up <= dn and ly_adj + up < plot_y_bot - 2 else ly_adj - dn
        label_color = accent_c if is_highlight else pal["ink"]
        # Halo keeps the italic label readable even when it lands on a
        # colored fill or near marker edges.
        parts.append(
            rigor.draw_label_with_halo(
                lx_adj,
                ly_adj,
                name,
                pal=pal,
                fs=fs_cur,
                anchor="middle",
                color=label_color,
                halo_alpha=0.72,
                halo_pad_x=4,
                halo_pad_y=2,
                bold=True,
                italic=True,
                font_family=body_font,
            )
        )

    # The region label already nudged away above when the two features' bboxes overlapped.
    if critical_points:
        marker_label_fs = max(13.0, fs["label"])
        # Pre-compute horizontal gridline screen-Ys to nudge labels away.
        _grid_ys_cp = [Y(v) for v in (y_ticks or []) if y_min <= v <= y_max]

        def _lift_label_above_grid(ly, fs_val, step=4.0, max_steps=10):
            # ``ly`` is the text baseline. Glyphs extend above the baseline by ~fs*0.85 (ascender) and below by ~fs*0.2
            # (descender).
            for _ in range(max_steps):
                band_top = ly - fs_val * 0.9
                band_bot = ly + fs_val * 0.25
                hit = False
                for gy in _grid_ys_cp:
                    if band_top <= gy <= band_bot:
                        hit = True
                        break
                if not hit:
                    return ly
                ly -= step
            return ly

        cp_marker_svgs = []
        cp_label_svgs = []
        for cp in critical_points:
            kind = cp.get("kind", "critical")
            cx = X(cp["x"])
            cy = Y(cp["y"])
            marker_color = pal["accent"]
            if kind == "triple":
                cp_marker_svgs.append(_triple_marker(cx, cy, marker_color))
            elif kind == "eutectic":
                cp_marker_svgs.append(_eutectic_marker(cx, cy, marker_color))
            else:
                cp_marker_svgs.append(_critical_marker(cx, cy, marker_color))
            label = cp.get("label", "")
            if label:
                # Place label above the marker (dy negative) rather than
                # alongside, so the triangle apex stays visible.
                dx = marker_label_fs * 0.4
                dy = marker_label_fs * 1.6
                _ly = _lift_label_above_grid(cy - dy, marker_label_fs)
                cp_label_svgs.append(
                    rigor.draw_label_with_halo(
                        cx + dx,
                        _ly,
                        label,
                        pal=pal,
                        fs=marker_label_fs,
                        anchor="start",
                        color=pal["ink"],
                        halo_alpha=0.85,
                        halo_pad_x=3,
                        halo_pad_y=1,
                        bold=True,
                        font_family=body_font,
                    )
                )
        parts.extend(cp_marker_svgs)
        parts.extend(cp_label_svgs)

    parts.append(
        rigor.draw_y_axis(
            plot_x_left,
            plot_y_top,
            plot_y_bot,
            y_ticks,
            y_min,
            y_max,
            unit=y_unit,
            pal=pal,
            fs_tick=fs["ytick"],
            fs_title=fs["yaxis"],
            title=y_title,
            side="left",
        )
    )
    parts.append(
        rigor.draw_x_axis(
            plot_x_left,
            plot_x_right,
            plot_y_bot,
            x_ticks,
            x_min,
            x_max,
            unit=x_unit,
            pal=pal,
            fs_tick=fs["ytick"],
            fs_title=fs["yaxis"],
            title=x_title,
        )
    )

    parts.append(rigor.draw_footer(note, source, pal, fs, plot_x_left, plot_x_right, H - 32))

    return rigor.wrap_svg(parts, W, H, body_font)
