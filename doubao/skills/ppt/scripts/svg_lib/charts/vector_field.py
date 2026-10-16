"""Academic chart: 2-D vector field. Each grid cell is drawn as an arrow whose
length and color encode the local magnitude. Optional singular points mark
"""

from __future__ import annotations

import math

from .._common import (
    _dist_font_sizes,
    _resolve_font,
    _resolve_palette,
    _variant_is_classic,
    _xesc,
)
from . import _academic_rigor as rigor
from ._shared import tr

# Multi-mode whitelist for vector_field.
# with_mag_hist : magnitude histogram to the right (left_right_3to1).
#                 Trigger: n_arrows (total grid cells) >= 50.
_VECTOR_FIELD_MULTI_WHITELIST = {
    "with_mag_hist": (
        "left_right_3to1",
        lambda s: s.get("n_arrows", 0) >= 50,
        lambda s: (
            (s.get("n_arrows", 0) >= 50 and len(s.get("mags") or []) >= 5),
            "need n_arrows>=50 and >=5 magnitudes",
        ),
    ),
}


def _draw_singular(cx, cy, kind, color, size=10.0):
    """Markers: source (filled circle), sink (ring), saddle (×)."""
    if kind == "source":
        return (
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{size:.1f}" fill="{color}" '
            f'stroke="rgba(28,28,26,1)" stroke-width="1.2"/>'
        )
    if kind == "sink":
        return f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{size:.1f}" fill="none" stroke="{color}" stroke-width="2.4"/>'
    s = size * 0.9
    return (
        f'<line x1="{cx - s:.1f}" y1="{cy - s:.1f}" '
        f'x2="{cx + s:.1f}" y2="{cy + s:.1f}" '
        f'stroke="{color}" stroke-width="2.6"/>'
        f'<line x1="{cx - s:.1f}" y1="{cy + s:.1f}" '
        f'x2="{cx + s:.1f}" y2="{cy - s:.1f}" '
        f'stroke="{color}" stroke-width="2.6"/>'
    )


def make_vector_field(
    grid,
    *,
    x_coords=None,
    y_coords=None,
    x_unit: str = "",
    y_unit: str = "",
    x_title: str | None = None,
    y_title: str | None = None,
    title: str | None = None,
    subtitle: str | None = None,
    figure_label: str | None = None,
    note: str | None = None,
    source: str | None = None,
    show_colorbar: bool = True,
    singular_points=None,
    arrow_scale: float = 1.0,
    mag_unit: str = "",
    width: float = 1050,
    height: float = 1050,
    font_family: str | None = None,
    palette=None,
    variant: str | None = None,
    multi_mode: str = "auto",
) -> str:
    """2-D vector field.

    Parameters
    ----------
    grid : list[list[(vx, vy)]]
        Row-major grid of velocity vectors. ``grid[row][col]`` is the vector at
        the cell indexed by ``(row, col)``. Row 0 is drawn at the **top** of the
        plot (standard screen convention).
    x_coords / y_coords : list of float, optional
        Positions of grid lines; default is cell indices.
    singular_points : list of dict, optional
        Each entry: ``x``, ``y``, ``label``, optional ``kind`` ∈
        {``"source"``, ``"sink"``, ``"saddle"``}.
    arrow_scale : global length multiplier applied on top of the per-cell
        magnitude normalization.
    """
    _variant_is_classic("vector_field", variant)
    if palette is None:
        palette = "archive_ink"
    pal = _resolve_palette(palette)
    body_font, heading_font = _resolve_font(font_family)
    W, H = float(width), float(height)
    n_rows = len(grid)
    n_cols = len(grid[0]) if n_rows else 0
    if n_rows == 0 or n_cols == 0:
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}">'
            f'<text x="{W / 2}" y="{H / 2}" text-anchor="middle" font-size="16" '
            f'fill="{pal["ink6"]}">{_xesc(tr("No data"))}</text></svg>'
        )

    fs = _dist_font_sizes(W, H, max(4, n_rows))

    margin_top = 120
    margin_bot = 170 if show_colorbar else 130
    margin_left = 110
    margin_right = 70
    plot_x_left = margin_left
    plot_x_right = W - margin_right
    plot_y_top = margin_top
    plot_y_bot = H - margin_bot

    if x_coords is None:
        x_coords = list(range(n_cols))
    if y_coords is None:
        y_coords = list(range(n_rows))

    x_min_data, x_max_data = min(x_coords), max(x_coords)
    y_min_data, y_max_data = min(y_coords), max(y_coords)
    x_ticks, x_min, x_max = rigor.nice_axis(x_min_data, x_max_data, 6)
    y_ticks, y_min, y_max = rigor.nice_axis(y_min_data, y_max_data, 6)

    mags = []
    for row in grid:
        for vx, vy in row:
            mags.append(math.hypot(vx, vy))
    mag_min, mag_max = min(mags), max(mags)
    if mag_max == mag_min:
        mag_max = mag_min + 1.0

    # Explicit magnitude ramp so the LOW end stays legible against bg. `value_to_color` default ramps bg→accent — arrows
    # at mag_min collapse into the paper on light palettes.
    _mag_ramp_lo = pal.get("secondary") or pal.get("ink2") or pal.get("ink")
    _mag_ramp_hi = pal.get("accent") or pal.get("ink")
    _mag_stops = [_mag_ramp_lo, _mag_ramp_hi]

    _plot_bbox = rigor.bbox_from_edges(
        plot_x_left,
        plot_x_right,
        plot_y_top,
        plot_y_bot,
    )
    _mm_signals = {
        "n_arrows": n_rows * n_cols,
        "mags": mags,
    }
    _mm_mode, _mm_template, _mm_reason = rigor.resolve_multi_mode_v2(
        multi_mode,
        _VECTOR_FIELD_MULTI_WHITELIST,
        _mm_signals,
        _plot_bbox,
    )
    _sub_bbox = None
    if _mm_mode is not None and _mm_template is not None:
        _rects = rigor.allocate_main_sub(_plot_bbox, _mm_template)
        _main_bb = _rects["main"]
        _sub_bbox = _rects["sub"]
        if _mm_template.startswith("left_right"):
            plot_x_right = _main_bb.x1
        else:
            plot_y_bot = _main_bb.y1

    def X(v):
        return rigor._lin(v, x_min, x_max, plot_x_left, plot_x_right)

    def Y(v):
        return rigor._lin(v, y_min, y_max, plot_y_bot, plot_y_top)

    # cell dimensions on screen (for arrow length cap)
    cell_w = (plot_x_right - plot_x_left) / max(1, n_cols - 1 if n_cols > 1 else 1)
    cell_h = (plot_y_bot - plot_y_top) / max(1, n_rows - 1 if n_rows > 1 else 1)
    # Cap arrow length so even a maximum-magnitude edge arrow stays inside
    # the plot bbox (keeps halos away from axis tick labels).
    max_arrow = min(cell_w, cell_h) * 0.75

    parts = rigor.draw_canvas_bg(pal, W, H)
    parts.append(
        rigor.draw_title_block(
            plot_x_left,
            plot_y_top - 24,
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

    for r, row in enumerate(grid):
        y_data = y_coords[r]
        y0 = Y(y_data)
        for c, (vx, vy) in enumerate(row):
            x_data = x_coords[c]
            x0 = X(x_data)
            mag = math.hypot(vx, vy)
            if mag < 1e-12:
                parts.append(f'<circle cx="{x0:.1f}" cy="{y0:.1f}" r="1.4" fill="{pal["ink6"]}"/>')
                continue
            length = max_arrow * (mag / mag_max) * arrow_scale
            # direction: screen y grows downward, data y usually grows upward,
            # so flip vy sign when mapping to screen.
            ux = vx / mag
            uy = -vy / mag
            # Center the arrow on the grid node: tail starts at half-length behind the node, tip ends at half-length
            # ahead.
            x_tail = x0 - ux * length * 0.5
            y_tail = y0 - uy * length * 0.5
            x_tip = x0 + ux * length * 0.5
            y_tip = y0 + uy * length * 0.5

            # Hard clamp to plot bbox as a belt-and-suspenders guard against
            # float drift / unusual grid cadences.
            def _clamp(v, lo, hi):
                return max(lo, min(hi, v))

            x_tail = _clamp(x_tail, plot_x_left, plot_x_right)
            x_tip = _clamp(x_tip, plot_x_left, plot_x_right)
            y_tail = _clamp(y_tail, plot_y_top, plot_y_bot)
            y_tip = _clamp(y_tip, plot_y_top, plot_y_bot)
            color = rigor.value_to_color(
                mag,
                mag_min,
                mag_max,
                pal=pal,
                stops=_mag_stops,
            )
            parts.append(
                f'<line x1="{x_tail:.1f}" y1="{y_tail:.1f}" '
                f'x2="{x_tip:.1f}" y2="{y_tip:.1f}" '
                f'stroke="{color}" stroke-width="1.8" stroke-linecap="round"/>'
            )
            head_size = max(4.0, length * 0.25)
            px, py = -uy, ux  # perpendicular
            hx = x_tip - ux * head_size
            hy = y_tip - uy * head_size
            p1 = (x_tip, y_tip)
            p2 = (hx + px * head_size * 0.45, hy + py * head_size * 0.45)
            p3 = (hx - px * head_size * 0.45, hy - py * head_size * 0.45)
            poly = " ".join(f"{p[0]:.1f},{p[1]:.1f}" for p in (p1, p2, p3))
            parts.append(f'<polygon points="{poly}" fill="{color}" stroke="none"/>')

    if singular_points:
        marker_fs = max(13.0, fs["label"])
        for sp in singular_points:
            cx = X(sp["x"])
            cy = Y(sp["y"])
            kind = sp.get("kind", "source")
            color = pal["accent"] if kind != "saddle" else pal["ink"]
            parts.append(_draw_singular(cx, cy, kind, color))
            label = sp.get("label", "")
            if label:
                parts.append(
                    f'<text x="{cx + 14:.1f}" y="{cy - 10:.1f}" '
                    f'font-size="{marker_fs:.1f}" fill="{pal["ink"]}" '
                    f'font-weight="600">{_xesc(label)}</text>'
                )

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

    if show_colorbar:
        cb_h = 16
        cb_w = (plot_x_right - plot_x_left) * 0.5
        cb_x = plot_x_left + ((plot_x_right - plot_x_left) - cb_w) * 0.5
        cb_y = H - 90
        parts.append(
            rigor.draw_colorbar(
                cb_x,
                cb_y,
                cb_w,
                cb_h,
                mag_min,
                mag_max,
                pal=pal,
                unit=mag_unit,
                orient="horizontal",
                fs_tick=fs["label"],
                title="|v|",
                stops=_mag_stops,
            )
        )

    if _sub_bbox is not None and _mm_mode == "with_mag_hist":
        sx_left, sx_right, sy_top, sy_bot = rigor.bbox_to_edges(_sub_bbox)
        # Reserve a bit of top for caption.
        sy_top = max(sy_top, plot_y_top + 10)
        sub_fs_tick = max(10.0, fs["ytick"] * 0.88)
        sub_fs_title = max(10.0, fs["yaxis"] * 0.88)

        parts.append(
            rigor.draw_magnitude_hist_subpanel(
                (sx_left, sx_right, sy_top, sy_bot),
                mags,
                mag_min,
                mag_max,
                color_range=(mag_min, mag_max),
                stops=_mag_stops,
                x_title="|v|",
                pal=pal,
                fs_tick=sub_fs_tick,
                fs_title=sub_fs_title,
            )
        )

    parts.append(rigor.draw_footer(note, source, pal, fs, plot_x_left, plot_x_right, H - 32))

    return rigor.wrap_svg(parts, W, H, body_font)
