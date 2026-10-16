"""Plot-only radar and scalar-contour providers for scientific compositions."""

from __future__ import annotations

from xml.sax.saxutils import quoteattr

from ._academic_rigor import BBox
from ._chart_layout import finite, wrap_lines
from ._composition import heading, numeric_axis, scale_from
from ._matrix_core import ColorScale
from ._polar import path
from ._xy import _axis_format
from .contour import _contour_segments, density_grid


def prepare_contour(data, canvas):
    if data.get("points") is not None:
        if data.get("grid") is not None:
            raise ValueError("provide either a scalar grid or density observations")
        grid, xs, ys = density_grid(data["points"], data.get("x_coords"), data.get("y_coords"))
    else:
        if not data.get("grid") or not data["grid"][0]:
            raise ValueError("contour requires a nonempty rectangular grid")
        grid = [[finite(v, "grid value") for v in row] for row in data["grid"]]
        xs, ys = data.get("x_coords", list(range(len(grid[0])))), data.get("y_coords", list(range(len(grid))))
    if len(grid) < 2 or len(grid[0]) < 2 or any(len(row) != len(grid[0]) for row in grid):
        raise ValueError("contour requires a rectangular grid with at least two rows and columns")
    xs, ys = [finite(v, "x coordinate") for v in xs], [finite(v, "y coordinate") for v in ys]
    if len(xs) != len(grid[0]) or len(ys) != len(grid):
        raise ValueError("coordinate lengths must match grid")
    if any(b <= a for coords in (xs, ys) for a, b in [(coords[i - 1], coords[i]) for i in range(1, len(coords))]):
        raise ValueError("contour coordinates must be strictly increasing")
    return {
        "grid": grid,
        "x_coords": xs,
        "y_coords": ys,
        "axes": {"x": scale_from(xs, domain=(xs[0], xs[-1])), "y": scale_from(ys, domain=(ys[0], ys[-1]))},
        "min_width": 560,
        "min_height": 360,
    }


def finalize_contours(panels, canvas):
    groups = {}
    for panel in panels:
        if panel["kind"] == "contour":
            groups.setdefault(str(panel.get("z_group", panel["id"])), []).append(panel)
    for members in groups.values():
        transforms = {bool(p["data"].get("log_z", False)) for p in members}
        requested = [p["data"]["levels"] for p in members if p["data"].get("levels") is not None]
        units = {p["data"].get("z_unit", "") for p in members} - {""}
        if len(units) > 1 or len(transforms) != 1 or any(v != requested[0] for v in requested):
            raise ValueError("shared contour z_group requires consistent units, identical levels and transforms")
        values = [v for p in members for row in p["grid"] for v in row]
        scale = ColorScale.from_values(
            values,
            canvas.pal,
            log=transforms.pop(),
            colormap="sequential",
            label=members[0]["data"].get(
                "z_title", "Density" if members[0]["data"].get("points") is not None else "Value"
            ),
        )
        levels = (
            [finite(v, "contour level") for v in requested[0]]
            if requested
            else sorted({scale.value_at(i / 8) for i in range(1, 8)})
        )
        if not levels or any(b <= a for a, b in [(levels[i - 1], levels[i]) for i in range(1, len(levels))]):
            raise ValueError("contour levels must be nonempty and strictly increasing")
        if scale.log and any(v <= 0 for v in levels):
            raise ValueError("log contour levels must be positive")
        for panel in members:
            panel.update(
                color_scale=scale,
                levels=levels,
                entries=[
                    {"name": f"{scale.label}: {scale.low:.4g}–{scale.high:.4g}", "color": scale, "direction": "out"}
                ],
            )
            panel["notes"].append("Filled bands use common scalar thresholds: " + ", ".join(f"{v:.3g}" for v in levels))


def _clip_scalar(vertices, level, above):
    result = []
    if not vertices:
        return result
    a = vertices[-1]
    for b in vertices:
        ina, inb = (a[2] >= level if above else a[2] <= level), (b[2] >= level if above else b[2] <= level)
        if ina != inb:
            t = (level - a[2]) / (b[2] - a[2])
            result.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]), level))
        if inb:
            result.append(b)
        a = b
    return result


def render_contour_panel(panel, canvas, body):
    xs, ys = panel["axes"]["x"], panel["axes"]["y"]
    data = panel["data"]
    xhead, yhead = (
        heading(data.get("x_title", "X"), xs, data.get("x_unit", "")),
        heading(data.get("y_title", "Y"), ys, data.get("y_unit", "")),
    )
    fonts = canvas.font_sizes
    left = max(66, max((canvas.measure(_axis_format(ys)[0](v), fonts["ytick"]) for v in ys.ticks), default=0) + 18)
    plot_w = body.x1 - body.x0 - left - 20
    top_h = len(wrap_lines(yhead, plot_w, fonts["label"], canvas.font)) * fonts["label"] * 1.35 + 10
    bottom_h = (fonts["xtick"] + fonts["label"]) * 1.35 + 20
    box = BBox(body.x0 + left, body.y0 + top_h, body.x1 - 20, body.y1 - bottom_h)
    canvas.text(yhead, box.x0, body.y0, fs=canvas.font_sizes["label"], width=box.x1 - box.x0)
    grid, gx, gy = panel["grid"], panel["x_coords"], panel["y_coords"]
    levels, scale = panel["levels"], panel["color_scale"]
    bands = [scale.low, *[v for v in levels if scale.low < v < scale.high], scale.high]
    if len(set(bands)) == 1:
        bands = [scale.low, scale.high]
    X, Y = lambda x: xs.map(x, box.x0, box.x1), lambda y: ys.map(y, box.y1, box.y0)
    for low, high in [(bands[i - 1], bands[i]) for i in range(1, len(bands))]:
        polygons = []
        for j in range(len(gy) - 1):
            for i in range(len(gx) - 1):
                cell = [
                    (gx[i], gy[j], grid[j][i]),
                    (gx[i + 1], gy[j], grid[j][i + 1]),
                    (gx[i + 1], gy[j + 1], grid[j + 1][i + 1]),
                    (gx[i], gy[j + 1], grid[j + 1][i]),
                ]
                for triangle in ((cell[0], cell[1], cell[2]), (cell[0], cell[2], cell[3])):
                    polygon = _clip_scalar(_clip_scalar(triangle, low, True), high, False)
                    if len(polygon) >= 3:
                        polygons.append(path([(X(x), Y(y)) for x, y, _ in polygon], True))
        if data.get("show_filled", True):
            canvas.parts.append(
                f'<path d="{" ".join(polygons)}" fill={quoteattr(scale.color((low + high) / 2))} stroke="none" data-role="contour-band" data-low="{low:.17g}" data-high="{high:.17g}"/>'
            )
    if data.get("show_lines", True):
        for level in levels:
            d = " ".join(
                path([(X(a[0]), Y(a[1])), (X(b[0]), Y(b[1]))]) for a, b in _contour_segments(grid, level, gx, gy)
            )
            canvas.parts.append(
                f'<path d="{d}" fill="none" stroke={quoteattr(canvas.ink)} stroke-opacity=".35" stroke-width=".65" data-role="contour-line" data-level="{level:.17g}"/>'
            )
    numeric_axis(canvas, box, xs)
    numeric_axis(canvas, box, ys, orientation="y")
    canvas.text(
        xhead,
        (box.x0 + box.x1) / 2,
        box.y1 + fonts["xtick"] * 1.35 + 12,
        fs=canvas.font_sizes["label"],
        anchor="middle",
        width=box.x1 - box.x0,
    )
    return {"plot_bbox": box, "anchors": {}}
