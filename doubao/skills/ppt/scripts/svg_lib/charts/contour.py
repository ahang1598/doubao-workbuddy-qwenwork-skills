"""Academic chart: 2-D contour / isoline figure."""

from __future__ import annotations

import math

from .._common import (
    _dist_font_sizes,
    _estimate_label_width_px,
    _fmt_axis,
    _resolve_font,
    _resolve_palette,
    _variant_is_classic,
    _xesc,
)
from . import _academic_rigor as rigor
from ._chart_layout import ChartLayout, finite, wrap_lines
from ._shared import tr


# Multi-mode whitelist:
#   with_orthogonal_slices: 1-D cross-sections of the Z surface at user-chosen
#   X and/or Y coordinates. The main contour panel keeps the full XY plot, a
#   bottom sub-panel plots Z(X, y=slice_y), and a right sub-panel plots
#   Z(x=slice_x, Y). Layout is a custom L-shape built from allocate_tracks.
def _validate_orthogonal_slices(signals):
    sx = signals.get("slice_x")
    sy = signals.get("slice_y")
    if sx is None and sy is None:
        return (False, "need slice_x or slice_y")
    rows = signals.get("rows", 0)
    cols = signals.get("cols", 0)
    if rows < 10 or cols < 10:
        return (False, f"grid too small ({rows}x{cols})")
    xc = signals.get("x_coords") or []
    yc = signals.get("y_coords") or []
    if sx is not None and (not xc or sx < min(xc) or sx > max(xc)):
        return (False, "slice_x out of range")
    if sy is not None and (not yc or sy < min(yc) or sy > max(yc)):
        return (False, "slice_y out of range")
    return (True, "")


_CONTOUR_MULTI_WHITELIST = {
    "with_orthogonal_slices": (
        # Use left_right_3to1 just for the canvas min-size check; the actual
        # L-shape layout is hand-built below with allocate_tracks.
        "left_right_3to1",
        lambda s: s.get("slice_x") is not None or s.get("slice_y") is not None,
        lambda s: _validate_orthogonal_slices(s),
    ),
}


def _interp_bilinear(grid, x_coords, y_coords, x_q, y_q):
    """Bilinearly interpolate ``grid[i][j]`` at a single (x, y)."""
    cols = len(x_coords)
    rows = len(y_coords)
    if x_q <= x_coords[0]:
        j0 = 0
        j1 = 0
        tx = 0.0
    elif x_q >= x_coords[-1]:
        j0 = cols - 1
        j1 = cols - 1
        tx = 0.0
    else:
        j0 = 0
        for j in range(cols - 1):
            if x_coords[j] <= x_q <= x_coords[j + 1]:
                j0 = j
                j1 = j + 1
                tx = (x_q - x_coords[j]) / (x_coords[j + 1] - x_coords[j])
                break
        else:
            j0 = cols - 1
            j1 = cols - 1
            tx = 0.0
    if y_q <= y_coords[0]:
        i0 = 0
        i1 = 0
        ty = 0.0
    elif y_q >= y_coords[-1]:
        i0 = rows - 1
        i1 = rows - 1
        ty = 0.0
    else:
        i0 = 0
        for i in range(rows - 1):
            if y_coords[i] <= y_q <= y_coords[i + 1]:
                i0 = i
                i1 = i + 1
                ty = (y_q - y_coords[i]) / (y_coords[i + 1] - y_coords[i])
                break
        else:
            i0 = rows - 1
            i1 = rows - 1
            ty = 0.0
    v00 = grid[i0][j0]
    v01 = grid[i0][j1] if j1 < cols else v00
    v10 = grid[i1][j0] if i1 < rows else v00
    v11 = grid[i1][j1] if (i1 < rows and j1 < cols) else v00
    v0 = v00 * (1 - tx) + v01 * tx
    v1 = v10 * (1 - tx) + v11 * tx
    return v0 * (1 - ty) + v1 * ty


def _interp_edge(a_val, b_val, a_coord, b_coord, level):
    """Linear interpolation between two corner values along one cell edge."""
    if b_val == a_val:
        return (a_coord + b_coord) * 0.5
    t = (level - a_val) / (b_val - a_val)
    t = max(0.0, min(1.0, t))
    return a_coord + t * (b_coord - a_coord)


def density_grid(points, x_coords=None, y_coords=None, resolution=48):
    """Product-Gaussian KDE, centered and scaled before bandwidth estimation."""
    if len(points) < 2:
        raise ValueError("a density estimate requires at least two observations")
    coordinates = [
        (finite(p["x"], "point.x"), finite(p["y"], "point.y"))
        if isinstance(p, dict)
        else (finite(p[0], "point.x"), finite(p[1], "point.y"))
        for p in points
    ]

    def dimension(values, requested):
        low, high = min(values), max(values)
        span = high - low
        if span == 0:
            raise ValueError("2D density requires variation on both axes; provide a grid for degenerate data")
        normalized = [(value - low) / span for value in values]
        mean = sum(normalized) / len(values)
        sd = math.sqrt(sum((v - mean) ** 2 for v in normalized) / (len(values) - 1))
        bandwidth = sd * len(values) ** (-1 / 6)
        if requested is None:
            start, end = low - 3 * bandwidth * span, high + 3 * bandwidth * span
            requested = [start + i * (end - start) / (resolution - 1) for i in range(resolution)]
        requested = [finite(v, "density grid coordinate") for v in requested]
        if len(requested) < 2 or any(requested[i] <= requested[i - 1] for i in range(1, len(requested))):
            raise ValueError("density grid coordinates must be strictly increasing")
        return normalized, [(v - low) / span for v in requested], requested, span, bandwidth

    x, x_eval, x_coords, x_span, hx = dimension([p[0] for p in coordinates], x_coords)
    y, y_eval, y_coords, y_span, hy = dimension([p[1] for p in coordinates], y_coords)
    normalizer = 2 * math.pi * hx * hy * len(points)
    x_kernels = [[math.exp(-0.5 * ((q - value) / hx) ** 2) for value in x] for q in x_eval]
    y_kernels = [[math.exp(-0.5 * ((q - value) / hy) ** 2) for value in y] for q in y_eval]
    grid = [[sum(a * b for a, b in zip(xk, yk)) / normalizer / x_span / y_span for xk in x_kernels] for yk in y_kernels]
    if any(not math.isfinite(v) for row in grid for v in row):
        raise ValueError("density exceeds floating-point range; rescale the coordinate units")
    return grid, x_coords, y_coords


def _contour_segments(grid, level, x_coords, y_coords):
    """Marching squares with an asymptotic saddle decider in scalar space."""
    pairs = {
        1: ((3, 2),),
        14: ((3, 2),),
        2: ((2, 1),),
        13: ((2, 1),),
        3: ((3, 1),),
        12: ((3, 1),),
        4: ((0, 1),),
        11: ((0, 1),),
        6: ((0, 2),),
        9: ((0, 2),),
        7: ((3, 0),),
        8: ((3, 0),),
    }
    segments = []
    for i in range(len(grid) - 1):
        for j in range(len(grid[0]) - 1):
            values = (grid[i][j], grid[i][j + 1], grid[i + 1][j + 1], grid[i + 1][j])
            case = sum(bit for bit, value in zip((8, 4, 2, 1), values) if value >= level)
            if case in (0, 15):
                continue
            tl, tr, br, bl = values
            left, right = x_coords[j : j + 2]
            top, bottom = y_coords[i : i + 2]
            edges = (
                (_interp_edge(tl, tr, left, right, level), top),
                (right, _interp_edge(tr, br, top, bottom, level)),
                (_interp_edge(bl, br, left, right, level), bottom),
                (left, _interp_edge(tl, bl, top, bottom, level)),
            )
            if case in (5, 10):
                centered = [value - level for value in values]
                scale = max(abs(value) for value in centered)
                a, b, c, d = [value / scale for value in centered]
                topology = ((0, 1), (3, 2)) if a * c >= b * d else ((3, 0), (2, 1))
            else:
                topology = pairs[case]
            segments.extend((edges[a], edges[b]) for a, b in topology)
    return segments


def make_contour(
    grid=None,
    *,
    points=None,
    x_coords=None,
    y_coords=None,
    levels=None,
    x_unit: str = "",
    y_unit: str = "",
    z_unit: str = "",
    x_title: str | None = None,
    y_title: str | None = None,
    z_title: str | None = None,
    title: str | None = None,
    subtitle: str | None = None,
    figure_label: str | None = None,
    note: str | None = None,
    source: str | None = None,
    show_filled: bool = True,
    show_lines: bool = True,
    show_data_points=None,
    log_z: bool = False,
    width: float = 1200,
    height: float = 820,
    font_family: str | None = None,
    palette=None,
    variant: str | None = None,
    slice_x: float | None = None,
    slice_y: float | None = None,
    multi_mode: str = "auto",
    show_stats: bool = False,
) -> str:
    """2-D contour plot. ``grid[i][j]`` is z at ``(x_coords[j], y_coords[i])``.

    If ``x_coords`` / ``y_coords`` are ``None`` the column/row index is used.
    If ``levels`` is ``None`` 10 isolines are placed uniformly across ``[zmin, zmax]``.
    ``show_stats=True`` opts in to a grid-size / z-range line above the plot;
    off by default because the colour bar already shows the z range.
    """
    _variant_is_classic("contour", variant)
    if points is not None:
        if grid is not None:
            raise ValueError("provide either a scalar grid or observations for density, not both")
        grid, x_coords, y_coords = density_grid(points, x_coords, y_coords)
        if show_data_points is None:
            show_data_points = [p for p in points if isinstance(p, dict) and p.get("label")]
        if z_title is None:
            z_title = tr("Probability density")
    if grid is None:
        raise ValueError("provide a scalar grid or density observations")
    if palette is None:
        palette = "archive_ink"
    pal = _resolve_palette(palette)
    body_font, _heading_font = _resolve_font(font_family)
    W, H = float(width), float(height)

    rows = len(grid)
    cols = len(grid[0]) if rows else 0
    if any(len(row) != cols for row in grid):
        raise ValueError("contour grid must be rectangular")
    grid = [[finite(v, "grid value") for v in row] for row in grid]
    if rows < 2 or cols < 2:
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}">'
            f'<text x="{W / 2}" y="{H / 2}" text-anchor="middle" font-size="16" '
            f'fill="{pal["ink6"]}">{_xesc(tr("Grid too small"))}</text></svg>'
        )

    if x_coords is None:
        x_coords = list(range(cols))
    if y_coords is None:
        y_coords = list(range(rows))
    x_coords = [finite(v, "x coordinate") for v in x_coords]
    y_coords = [finite(v, "y coordinate") for v in y_coords]
    if len(x_coords) != cols or len(y_coords) != rows:
        raise ValueError("coordinate lengths must match grid columns and rows")
    if any(x_coords[i] <= x_coords[i - 1] for i in range(1, len(x_coords))) or any(
        y_coords[i] <= y_coords[i - 1] for i in range(1, len(y_coords))
    ):
        raise ValueError("contour coordinates must be strictly increasing")

    all_z = [v for row in grid for v in row]
    z_min_data = min(all_z)
    z_max_data = max(all_z)
    if log_z:
        if z_min_data <= 0:
            raise ValueError("log_z requires strictly positive grid values")
        z_min_eff = z_min_data
        z_max_eff = z_max_data
    else:
        z_min_eff = z_min_data
        z_max_eff = z_max_data

    if levels is None:
        n_lv = 10
        if log_z:
            lmin = math.log10(z_min_eff)
            lmax = math.log10(z_max_eff)
            levels = [10 ** (lmin + (i + 1) * (lmax - lmin) / (n_lv + 1)) for i in range(n_lv)]
        else:
            levels = [z_min_eff + (i + 1) * (z_max_eff - z_min_eff) / (n_lv + 1) for i in range(n_lv)]
    levels = [finite(level, "contour level") for level in levels]

    fs = _dist_font_sizes(W, H, 6)

    # layout: title top, main plot center, colorbar right, footer bottom
    header = ChartLayout(W, H, pal, font_family)
    header_bottom = header.header(title, subtitle, figure_label)
    compact = H < 600 or W < 700
    margin_top = header_bottom + 30 if compact else max(110, header_bottom + 30)
    foot_lines = [
        line
        for value in (note, source)
        if value
        for line in wrap_lines(value, W - 56, max(13.0, fs["foot"]), body_font)
    ]
    labeled_points = [p for p in (show_data_points or []) if isinstance(p, dict) and p.get("label")]
    margin_bot = (210 if labeled_points else 84 if compact else 110) + max(0, len(foot_lines) - 1) * 19
    margin_left = 60 if compact else 110
    margin_right = 270 if labeled_points else 132 if compact else 170

    plot_x_left = margin_left
    plot_x_right = W - margin_right
    plot_y_top = margin_top
    plot_y_bot = H - margin_bot

    x_data_min = min(x_coords)
    x_data_max = max(x_coords)
    y_data_min = min(y_coords)
    y_data_max = max(y_coords)
    x_ticks, x_min, x_max = rigor.nice_axis(x_data_min, x_data_max, 6)
    y_ticks, y_min, y_max = rigor.nice_axis(y_data_min, y_data_max, 5)
    tick_width = max(
        _estimate_label_width_px(_fmt_axis(v, y_max - y_min), fs["ytick"], font_family=body_font) for v in y_ticks
    )
    plot_x_left = max(plot_x_left, tick_width + (70 if y_title else 35))
    if plot_x_right - plot_x_left < (160 if compact else 240) or plot_y_bot - plot_y_top < (140 if compact else 200):
        raise ValueError("contour canvas is too small for the labels and plotting area")

    _signals = {
        "slice_x": slice_x,
        "slice_y": slice_y,
        "rows": rows,
        "cols": cols,
        "x_coords": x_coords,
        "y_coords": y_coords,
    }
    _canvas_bbox = rigor.bbox_from_edges(plot_x_left, plot_x_right, plot_y_top, plot_y_bot)
    _chosen_mode, _chosen_tpl, _reason = rigor.resolve_multi_mode_v2(
        multi_mode,
        _CONTOUR_MULTI_WHITELIST,
        _signals,
        _canvas_bbox,
    )
    if (
        compact
        and _chosen_mode is None
        and multi_mode == "auto"
        and (slice_x is not None or slice_y is not None)
        and _validate_orthogonal_slices(_signals)[0]
        and plot_x_right - plot_x_left >= 360
        and plot_y_bot - plot_y_top >= 220
    ):
        _chosen_mode = "with_orthogonal_slices"
    if compact and _chosen_mode == "with_orthogonal_slices" and not labeled_points:
        plot_y_bot += 50  # the bottom slice carries no tick labels
    _slice_x_bbox = None
    _slice_y_bbox = None
    if _chosen_mode == "with_orthogonal_slices":
        _slice_h = (plot_y_bot - plot_y_top) * (0.16 if compact else 0.20)
        _slice_w = (plot_x_right - plot_x_left) * 0.20
        _gutter_x = 28.0
        # The horizontal gutter carries main-axis tick labels and the slice caption.
        _slice_caption_fs = max(13.0, fs["label"])
        _gutter_y = fs["ytick"] * 1.6 + _slice_caption_fs + 16
        if x_title or x_unit:
            _gutter_y += fs["yaxis"] + 12
        _main_x_right = plot_x_right - _slice_w - _gutter_x
        _main_y_bot = plot_y_bot - _slice_h - _gutter_y
        if slice_y is not None:
            _slice_x_bbox = rigor.BBox(plot_x_left, _main_y_bot + _gutter_y, _main_x_right, plot_y_bot)
        if slice_x is not None:
            _slice_y_bbox = rigor.BBox(_main_x_right + _gutter_x, plot_y_top, plot_x_right, _main_y_bot)
        plot_x_right = _main_x_right
        plot_y_bot = _main_y_bot

    def X(v):
        return rigor._lin(v, x_min, x_max, plot_x_left, plot_x_right)

    def Y(v):
        # higher y_data -> higher on screen (y_min at bottom)
        return rigor._lin(v, y_min, y_max, plot_y_bot, plot_y_top)

    parts = rigor.draw_canvas_bg(pal, W, H)

    parts.extend(header.parts)

    # Clip region for cells (so filled color doesn't bleed past axes) Use nested group with simple rect clip via
    # explicit coordinate clipping instead of <clipPath> to keep SVG simple.

    if show_filled:
        fill_x, fill_y, fill_grid = x_coords, y_coords, grid
        if rows < 32 or cols < 32:
            nx, ny = max(cols, 32), max(rows, 32)
            fill_x = [x_coords[0] + i * (x_coords[-1] - x_coords[0]) / (nx - 1) for i in range(nx)]
            fill_y = [y_coords[0] + i * (y_coords[-1] - y_coords[0]) / (ny - 1) for i in range(ny)]
            fill_grid = [[_interp_bilinear(grid, x_coords, y_coords, x, y) for x in fill_x] for y in fill_y]
        for i in range(len(fill_y) - 1):
            for j in range(len(fill_x) - 1):
                xa = fill_x[j]
                xb = fill_x[j + 1]
                yta = fill_y[i]
                ytb = fill_y[i + 1]
                # average z over 4 corners
                zc = sum((fill_grid[i][j], fill_grid[i][j + 1], fill_grid[i + 1][j], fill_grid[i + 1][j + 1])) / 4
                c = rigor.value_to_color(zc, z_min_eff, z_max_eff, pal=pal, log=log_z)
                sx1 = X(xa)
                sx2 = X(xb)
                sy1 = Y(yta)
                sy2 = Y(ytb)
                rx = min(sx1, sx2)
                ry = min(sy1, sy2)
                rw = abs(sx2 - sx1) + 0.5  # +0.5 to avoid 1-px gaps on raster
                rh = abs(sy2 - sy1) + 0.5
                parts.append(
                    f'<rect x="{rx:.2f}" y="{ry:.2f}" width="{rw:.2f}" height="{rh:.2f}" fill="{c}" stroke="none"/>'
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

    if show_lines:
        ink = pal["ink"]
        for level in levels:
            segs = _contour_segments(grid, level, x_coords, y_coords)
            if not segs:
                continue
            path_parts = []
            for p1, p2 in segs:
                path_parts.append(f"M {X(p1[0]):.1f} {Y(p1[1]):.1f} L {X(p2[0]):.1f} {Y(p2[1]):.1f}")
            d = " ".join(path_parts)
            parts.append(f'<path d="{d}" fill="none" stroke="{ink}" stroke-width="0.8" stroke-opacity="0.85"/>')

    if show_data_points:
        accent = pal["accent"]
        for point in show_data_points:
            if isinstance(point, dict) and point.get("label"):
                continue
            dx, dy = (point["x"], point["y"]) if isinstance(point, dict) else point[:2]
            cx, cy = X(dx), Y(dy)
            parts.append(
                f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="2.6" fill="{accent}" '
                f'stroke="{pal["ink"]}" stroke-width="0.6"/>'
            )
    if labeled_points:
        from ._xy import normalize_series, render_xy_plot

        highlighted = normalize_series(
            [{"name": tr("Annotations"), "points": labeled_points, "color": pal["ink"], "marker": "diamond"}]
        )
        parts.append(
            render_xy_plot(
                highlighted,
                rigor.BBox(plot_x_left, plot_y_top, plot_x_right, plot_y_bot),
                x_scale=rigor.SharedScale((x_min, x_max), x_ticks),
                y_scale=rigor.SharedScale((y_min, y_max), y_ticks),
                palette=pal,
                font_family=body_font,
                axes=False,
                label_bbox=rigor.BBox(plot_x_right + 28, plot_y_top, W - 28, plot_y_bot),
            )
        )

    parts.append(
        f'<rect x="{plot_x_left:.1f}" y="{plot_y_top:.1f}" '
        f'width="{plot_x_right - plot_x_left:.1f}" height="{plot_y_bot - plot_y_top:.1f}" '
        f'fill="none" stroke="{pal["ink"]}" stroke-width="1.2"/>'
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

    cb_w = plot_x_right - plot_x_left if labeled_points else 18.0
    cb_x = plot_x_left if labeled_points else W - margin_right + 36
    cb_y = plot_y_bot + 75 if labeled_points else plot_y_top + 20
    cb_h = 14 if labeled_points else (plot_y_bot - plot_y_top) - 40
    parts.append(
        rigor.draw_colorbar(
            cb_x,
            cb_y,
            cb_w,
            cb_h,
            z_min_eff,
            z_max_eff,
            pal=pal,
            unit=z_unit,
            log=log_z,
            orient="horizontal" if labeled_points else "vertical",
            fs_tick=fs["ytick"],
            title=z_title,
        )
    )

    # Rendered as a SINGLE horizontal line ABOVE the plot area so the text never sits on top of filled contour cells.
    stats_pieces = (
        [
            tr("grid {rows}×{cols}", rows=rows, cols=cols),
            tr("z min {value}", value=f"{z_min_data:.3g}"),
            tr("z max {value}", value=f"{z_max_data:.3g}"),
        ]
        if show_stats
        else []
    )
    _ = rigor.draw_label_with_halo  # probe
    stats_fs = max(12.0, fs["label"] * 0.95)
    # Place stats on a single horizontal line just above plot_y_top, using the strip the top margin reserves.
    stats_y = plot_y_top - 6
    stats_x = plot_x_right
    # Build right-aligned chain: last piece first, then separator and
    # the previous piece, etc. We just render each piece with its own
    # halo and track the x cursor.
    from .._common import _estimate_label_width_px as _est_w

    gap = 14.0
    cursor_x = stats_x
    for text in reversed(stats_pieces):
        parts.append(
            rigor.draw_label_with_halo(
                cursor_x,
                stats_y,
                text,
                pal,
                fs=stats_fs,
                anchor="end",
                halo_alpha=0.9,
                halo_pad_x=5,
                halo_pad_y=2,
                bold=False,
                font_family=body_font,
            )
        )
        tw = _est_w(text, stats_fs, font_family=body_font)
        cursor_x -= tw + gap

    # Measured footer rows stay clear of the colorbar tick rail.
    foot_fs = max(13.0, fs["foot"])
    footer_layout = ChartLayout(W, H, pal, font_family)
    for i, line in enumerate(foot_lines):
        footer_layout.text(line, 28, H - 20 - (len(foot_lines) - i) * 19, fs=foot_fs, color=pal["ink6"])
    parts.extend(footer_layout.parts)

    if _chosen_mode == "with_orthogonal_slices":
        if slice_x is not None:
            parts.append(
                rigor.draw_source_marker(
                    "vline",
                    pal=pal,
                    x=X(slice_x),
                    y0=plot_y_top,
                    y1=plot_y_bot,
                )
            )
        if slice_y is not None:
            parts.append(
                rigor.draw_source_marker(
                    "hline",
                    pal=pal,
                    y=Y(slice_y),
                    x0=plot_x_left,
                    x1=plot_x_right,
                )
            )
        # Bottom slice: Z vs X at fixed y = slice_y
        if _slice_x_bbox is not None and slice_y is not None:
            # Preserve the requested slice coordinate, including between grid rows.
            _row_vals = [_interp_bilinear(grid, x_coords, y_coords, x, slice_y) for x in x_coords]
            _sb = _slice_x_bbox
            _z_lo, _z_hi = z_min_data, z_max_data
            _zspan = _z_hi - _z_lo or 1.0
            parts.append(
                f'<line x1="{_sb.x0:.1f}" y1="{_sb.y1:.1f}" x2="{_sb.x1:.1f}" y2="{_sb.y1:.1f}" '
                f'stroke="{pal.get("ink", "black")}" stroke-width="1"/>'
            )
            _pts = []
            for j in range(cols):
                _xp = rigor._lin(x_coords[j], x_min, x_max, _sb.x0, _sb.x1)
                _yp = rigor._lin(_row_vals[j], _z_lo, _z_hi, _sb.y1, _sb.y0)
                _pts.append((_xp, _yp))
            if _pts:
                _d = " ".join(f"{'M' if i == 0 else 'L'} {x:.1f} {y:.1f}" for i, (x, y) in enumerate(_pts))
                parts.append(f'<path d="{_d}" fill="none" stroke="{pal["accent"]}" stroke-width="1.6"/>')
            parts.append(
                f'<text x="{_sb.x0:.1f}" y="{_sb.y0 - 6:.1f}" font-size="{_slice_caption_fs:.1f}" '
                f'fill="{pal.get("ink6", "gray")}" font-style="italic">{_xesc(tr("Z at y={value}", value=f"{slice_y:.2g}"))}</text>'
            )
        # Right slice: Z vs Y at fixed x = slice_x
        if _slice_y_bbox is not None and slice_x is not None:
            _col_vals = [_interp_bilinear(grid, x_coords, y_coords, slice_x, y) for y in y_coords]
            _sb = _slice_y_bbox
            _z_lo, _z_hi = z_min_data, z_max_data
            parts.append(
                f'<line x1="{_sb.x0:.1f}" y1="{_sb.y0:.1f}" x2="{_sb.x0:.1f}" y2="{_sb.y1:.1f}" '
                f'stroke="{pal.get("ink", "black")}" stroke-width="1"/>'
            )
            _pts = []
            for i in range(rows):
                _yp = rigor._lin(y_coords[i], y_min, y_max, _sb.y1, _sb.y0)
                _xp = rigor._lin(_col_vals[i], _z_lo, _z_hi, _sb.x0, _sb.x1)
                _pts.append((_xp, _yp))
            if _pts:
                _d = " ".join(f"{'M' if i == 0 else 'L'} {x:.1f} {y:.1f}" for i, (x, y) in enumerate(_pts))
                parts.append(f'<path d="{_d}" fill="none" stroke="{pal["accent"]}" stroke-width="1.6"/>')
            parts.append(
                f'<text x="{_sb.x0:.1f}" y="{_sb.y0 - 6:.1f}" font-size="{_slice_caption_fs:.1f}" '
                f'fill="{pal.get("ink6", "gray")}" font-style="italic">{_xesc(tr("Z at x={value}", value=f"{slice_x:.2g}"))}</text>'
            )

    return rigor.wrap_svg(parts, W, H, body_font)
