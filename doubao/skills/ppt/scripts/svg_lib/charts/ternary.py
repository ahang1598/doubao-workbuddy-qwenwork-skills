"""Three-component scatter, bubble and density plots on a true simplex."""

from __future__ import annotations

import math
from collections.abc import Mapping
from xml.sax.saxutils import quoteattr

from .._common import _pick_series_colors, _rgba_with_alpha
from .._typography import chart_font_sizes
from . import _academic_rigor as rigor
from ._chart_layout import ChartLayout, finite, number_label, wrap_lines
from ._shared import tr

_ALTITUDE = math.sqrt(3) / 2


def _composition(values, total=1.0, normalize=False, name="point"):
    if len(values) != 3:
        raise ValueError(f"{name} must contain exactly three components")
    vals = tuple(finite(v, f"{name} component", minimum=0) for v in values)
    actual = sum(vals)
    if not math.isfinite(actual) or actual <= 0:
        raise ValueError(f"{name} components must have a positive finite sum")
    if not normalize and not math.isclose(actual, total, rel_tol=1e-6, abs_tol=1e-10 * total):
        raise ValueError(f"{name} sums to {actual:g}, expected {total:g}; use normalize=True for raw weights")
    return tuple(v / actual for v in vals)


def _barycentric(components):
    """A is the apex, B the left vertex, C the right; return Cartesian x/y."""
    a, _b, c = components
    return c + 0.5 * a, _ALTITUDE * a


def _read_points(points, total, normalize):
    out = []
    allowed = {"a", "b", "c", "group", "value", "size", "facet"}
    for i, raw in enumerate(points or []):
        if isinstance(raw, Mapping):
            if set(raw) - allowed:
                raise ValueError(f"point {i} has unsupported fields: {sorted(set(raw) - allowed)}")
            if not all(k in raw for k in ("a", "b", "c")):
                raise ValueError(f"point {i} needs a, b and c")
            p = dict(raw)
            components = [p[k] for k in ("a", "b", "c")]
        else:
            p, components = {}, raw
        p["components"] = _composition(components, total, normalize, f"point {i}")
        p["xy"] = _barycentric(p["components"])
        for key in ("value", "size"):
            if key in p:
                p[key] = finite(p[key], f"point {i} {key}", minimum=0 if key == "size" else None)
        for key in ("group", "facet"):
            if key in p:
                if p[key] is None or not str(p[key]).strip():
                    raise ValueError(f"point {i} {key} must be a nonempty label")
                p[key] = str(p[key])
        out.append(p)
    for key in ("value", "size", "group", "facet"):
        present = sum(key in p for p in out)
        if present and present != len(out):
            raise ValueError(f"{key} must be supplied for every point when used")
    if out and "value" in out[0] and "group" in out[0]:
        raise ValueError("use either group (categorical color) or value (continuous color), not both")
    if out and "size" in out[0] and max(p["size"] for p in out) == 0:
        raise ValueError("at least one point size must be positive")
    return out


def _mesh(resolution):
    """Equilateral triangular lattice, with exact simplex boundary vertices."""
    nodes = [(i, j) for i in range(resolution + 1) for j in range(resolution + 1 - i)]
    index = {ij: k for k, ij in enumerate(nodes)}
    xy = [_barycentric((i / resolution, j / resolution, 1 - (i + j) / resolution)) for i, j in nodes]
    triangles = []
    for i in range(resolution):
        for j in range(resolution - i):
            triangles.append((index[i, j], index[i + 1, j], index[i, j + 1]))
            if i + j < resolution - 1:
                triangles.append((index[i + 1, j], index[i + 1, j + 1], index[i, j + 1]))
    return xy, triangles


def _density_mesh(points, bandwidth=None, resolution=36):
    xy, triangles = _mesh(resolution)
    if not points:
        raise ValueError("density estimation requires points")
    # Scott's two-dimensional n^(-1/6) rule with a grid-aware lower bound.
    # Equal/one-point samples remain defined rather than dividing by zero.
    if bandwidth is None:
        mean = [sum(p[d] for p in points) / len(points) for d in (0, 1)]
        variance = sum(sum((p[d] - mean[d]) ** 2 for p in points) for d in (0, 1))
        sigma = math.sqrt(variance / max(1, 2 * (len(points) - 1)))
        bandwidth = max(1.5 / resolution, min(0.25, sigma * len(points) ** (-1 / 6)))
    else:
        bandwidth = finite(bandwidth, "bandwidth", minimum=0)
        if not 1 / resolution <= bandwidth <= 1:
            raise ValueError(f"bandwidth must be between {1 / resolution:.4g} and 1 in unit-side triangle coordinates")
    z = [sum(math.exp(-((x - px) ** 2 + (y - py) ** 2) / (2 * bandwidth**2)) for px, py in points) for x, y in xy]
    area = _ALTITUDE / (2 * resolution**2)
    integral = sum(sum(z[k] for k in tri) / 3 * area for tri in triangles)
    return xy, triangles, [v / integral for v in z]


def _precomputed_mesh(grid):
    rows = list(grid)
    resolution = len(rows) - 1
    if resolution < 1 or resolution > 120:
        raise ValueError("grid requires 2–121 rows of lengths n+1, n, …, 1")
    z = []
    for i, row in enumerate(rows):
        if len(row) != resolution + 1 - i:
            raise ValueError("grid row lengths must be n+1, n, …, 1")
        z.extend(finite(v, f"grid row {i}") for v in row)
    xy, triangles = _mesh(resolution)
    return xy, triangles, z


def _contour_segments(xy, triangles, values, level):
    """Marching triangles with a half-open edge rule, including saddle-free cells."""
    segments = []
    for tri in triangles:
        hits = []
        for u, v in ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])):
            zu, zv = values[u], values[v]
            if (zu <= level < zv) or (zv <= level < zu):
                t = (level - zu) / (zv - zu)
                hits.append((xy[u][0] + t * (xy[v][0] - xy[u][0]), xy[u][1] + t * (xy[v][1] - xy[u][1])))
        if len(hits) == 2:
            segments.append(tuple(hits))
    return segments


def _draw_triangle(
    layout, bbox, labels, total, facet, points, mesh, kind, color_domain, color_stops, colors, size_max, facet_h=0
):
    pal = layout.pal
    x0, y0, x1, y1 = bbox
    panel_w = x1 - x0
    if facet:
        layout.text(
            facet, (x0 + x1) / 2, y0, bold=True, width=panel_w - 24, anchor="middle", fs=layout.font_sizes["group"]
        )
    side = min(panel_w - 78, (y1 - y0 - facet_h - 99) / _ALTITUDE)
    # Vertex text widths follow the actual triangle, including wide/short
    # canvases. Iteration resolves the interaction between wrapping and height.
    for _ in range(12):
        label_width = max(55, side * 0.44)
        label_lines = [wrap_lines(s, label_width / 1.05, layout.font_sizes["xaxis"], layout.heading) for s in labels]
        label_h = max(len(lines) for lines in label_lines) * layout.font_sizes["xaxis"] * 1.35
        top = y0 + facet_h + label_h + 18
        bottom = y1 - label_h - layout.font_sizes["xtick"] * 1.35 - 22
        fitted = min(panel_w - 78, (bottom - top) / _ALTITUDE)
        if fitted >= side - 0.01:
            break
        side = fitted
    tick_width = max(
        layout.measure(number_label(total * k / 5, compact=True), layout.font_sizes["xtick"]) for k in range(1, 5)
    )
    if side < max(160, 5 * (tick_width + 6)):
        raise ValueError("ternary panels are too small; increase width/height or shorten labels")
    left = (x0 + x1 - side) / 2
    base = top + _ALTITUDE * side

    def project(xy):
        return left + xy[0] * side, base - xy[1] * side

    triangle = [project(_barycentric(c)) for c in ((1, 0, 0), (0, 1, 0), (0, 0, 1))]
    polygon = " ".join(f"{x:.2f},{y:.2f}" for x, y in triangle)
    if mesh:
        xy, triangles, z = mesh
        if kind == "density":
            for indices in triangles:
                poly = " ".join(f"{x:.2f},{y:.2f}" for x, y in (project(xy[k]) for k in indices))
                color = rigor.value_to_color(sum(z[k] for k in indices) / 3, *color_domain, pal, stops=color_stops)
                # A subpixel overlap prevents pale anti-alias seams between cells.
                layout.parts.append(
                    f'<polygon points="{poly}" fill="{color}" stroke="{color}" stroke-width=".85" stroke-linejoin="round"/>'
                )
        lo, hi = color_domain
        if hi > lo:
            for i in range(1, 7):
                level = lo + (hi - lo) * i / 7
                for p, q in _contour_segments(xy, triangles, z, level):
                    x, y = project(p)
                    xx, yy = project(q)
                    color = (
                        rigor.value_to_color(level, lo, hi, pal, stops=color_stops)
                        if kind == "contour"
                        else _rgba_with_alpha(layout.ink, 0.5)
                    )
                    layout.parts.append(
                        f'<path d="M{x:.2f},{y:.2f} L{xx:.2f},{yy:.2f}" '
                        f'fill="none" stroke="{color}" stroke-width="1.1"/>'
                    )
    # The three grid directions each encode a component, with ticks outside.
    for k in range(1, 5):
        t = k / 5
        for start, end in (
            ((t, 1 - t, 0), (t, 0, 1 - t)),
            ((1 - t, t, 0), (0, t, 1 - t)),
            ((1 - t, 0, t), (0, 1 - t, t)),
        ):
            x, y = project(_barycentric(start))
            xx, yy = project(_barycentric(end))
            layout.parts.append(
                f'<path d="M{x:.2f},{y:.2f} L{xx:.2f},{yy:.2f}" '
                f'stroke={quoteattr(pal["grid"])} stroke-width=".75" fill="none"/>'
            )
        tick = number_label(total * t, compact=True)
        x, y = project(_barycentric((t, 0, 1 - t)))
        layout.text(
            tick, x + 12, y - layout.font_sizes["xtick"] * 0.6, fs=layout.font_sizes["xtick"], color=pal["ink6"]
        )
        x, y = project(_barycentric((1 - t, t, 0)))
        layout.text(
            tick,
            x - 12,
            y - layout.font_sizes["xtick"] * 0.6,
            fs=layout.font_sizes["xtick"],
            color=pal["ink6"],
            anchor="end",
        )
        x, y = project(_barycentric((0, 1 - t, t)))
        layout.text(tick, x, y + 12, fs=layout.font_sizes["xtick"], color=pal["ink6"], anchor="middle")
    layout.parts.append(f'<polygon points="{polygon}" fill="none" stroke={quoteattr(pal["ink4"])} stroke-width="1.4"/>')
    if kind == "scatter":
        for p in sorted(points, key=lambda p: -p.get("size", 1)):
            x, y = project(p["xy"])
            radius = 4.4 if "size" not in p else 13 * math.sqrt(p["size"] / size_max)
            if radius == 0:
                continue
            color = (
                rigor.value_to_color(p["value"], *color_domain, pal, stops=color_stops)
                if "value" in p
                else colors[p.get("group", "")]
            )
            layout.parts.append(
                f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{radius:.2f}" '
                f'fill={quoteattr(color)} fill-opacity=".8" '
                f'stroke={quoteattr(pal.get("bg") or "white")} stroke-width=".8"/>'
            )
    # Vertex names always have their own lanes; no labels are placed over data.
    layout.text(
        labels[0],
        left + side / 2,
        top - label_h - 15,
        fs=layout.font_sizes["xaxis"],
        bold=True,
        anchor="middle",
        width=label_width,
    )
    layout.text(
        labels[1],
        left,
        base + layout.font_sizes["xtick"] * 1.35 + 18,
        fs=layout.font_sizes["xaxis"],
        bold=True,
        width=label_width,
    )
    layout.text(
        labels[2],
        left + side,
        base + layout.font_sizes["xtick"] * 1.35 + 18,
        fs=layout.font_sizes["xaxis"],
        bold=True,
        anchor="end",
        width=label_width,
    )


def _legend_number(layout, value, width):
    """Fit floating scientific measurements to their actual label lane."""
    candidates = [number_label(value)] + [f"{value:.{p}g}" for p in range(16, 2, -1)]
    for label in candidates:
        if layout.measure(label, layout.font_sizes["legend"]) <= width:
            return label
    raise ValueError("numeric legend labels need more horizontal room; increase width")


def _size_references(sizes):
    """Choose reference areas whose serialized circle sizes remain distinct."""
    maximum = max(sizes)
    minimum = min(value for value in sizes if value > 0)
    if 13 - 13 * math.sqrt(minimum / maximum) < 1:
        return [maximum]
    references = []
    for value in sorted({minimum, maximum / 2, maximum}, reverse=True):
        radius = 13 * math.sqrt(value / maximum)
        if radius >= 1 and all(abs(radius - 13 * math.sqrt(ref / maximum)) >= 1 for ref in references):
            references.append(value)
    return sorted(references)


def make_ternary(
    points=None,
    labels=("A", "B", "C"),
    *,
    total=1.0,
    normalize=False,
    kind="scatter",
    bandwidth=None,
    grid=None,
    value_label=None,
    size_label="Size",
    width=900,
    height=680,
    title=None,
    subtitle=None,
    figure_label=None,
    palette=None,
    font_family=None,
):
    """Return one SVG; optional ``facet`` fields create aligned panels in one call.

    ``points`` accepts triples or records with ``a,b,c`` and optional ``group``
    (categorical color), ``value`` (continuous color), ``size`` (circle area) and
    ``facet``. Each optional field must be present for all points. ``group`` and
    ``value`` are alternatives. All components must be finite/nonnegative and
    sum to ``total`` (default 1; use 100 for percentages). Only ``normalize=True``
    accepts arbitrary positive totals. Axis ticks remain in the chosen total.
    Large/small totals use one explicitly stated scientific multiplier.

    ``kind``: scatter, density (filled KDE + isolines), or contour (isolines).
    Density/contour support facets but not group/value/size encodings. Optional
    ``bandwidth`` is in coordinates of a unit-side equilateral triangle.
    ``grid`` bypasses KDE: triangular rows of lengths n+1, n, …, 1; row i,
    column j is located at (a=i/n, b=j/n, c=1-a-b). It is one scalar field,
    accepts finite signed values, and requires density/contour without points.
    All facets share color and size scales. Background is inherited from slides.
    """
    total = finite(total, "total", minimum=0)
    if total <= 0:
        raise ValueError("total must be positive")
    if not isinstance(normalize, bool):
        raise TypeError("normalize must be a boolean")
    if kind not in {"scatter", "density", "contour"}:
        raise ValueError("kind must be scatter, density or contour")
    if len(labels) != 3 or any(not str(label).strip() for label in labels):
        raise ValueError("labels must contain three nonempty component names")
    labels = tuple(str(label) for label in labels)
    data = _read_points(points, total, normalize)
    if not data and grid is None:
        raise ValueError("provide points or a precomputed triangular grid")
    if grid is not None and (data or kind == "scatter" or bandwidth is not None):
        raise ValueError("grid requires density/contour without points or bandwidth")
    if kind == "scatter" and bandwidth is not None:
        raise ValueError("bandwidth is only used for density/contour")
    if kind != "scatter" and any(k in p for p in data for k in ("group", "value", "size")):
        raise ValueError(
            "density/contour uses point coordinates and optional facet; group/value/size are scatter encodings"
        )
    facets = list(dict.fromkeys(p.get("facet", "") for p in data)) or [""]
    groups = list(dict.fromkeys(p.get("group", "") for p in data)) or [""]
    layout = ChartLayout(width, height, palette, font_family, n_items=max(3, len(data)) if kind == "scatter" else 3)
    pal = layout.pal
    colors = dict(zip(groups, _pick_series_colors(pal, len(groups))))
    low = rigor.value_to_color(
        0.38 if kind in {"scatter", "contour"} else 0.08,
        0,
        1,
        pal,
        stops=[pal.get("bg") or "rgba(255,255,255,1)", pal["accent"]],
    )
    stops = pal.get("color_stops") or [low, pal["accent"]]
    meshes = {}
    if grid is not None:
        meshes[""] = _precomputed_mesh(grid)
    elif kind != "scatter":
        meshes = {
            facet: _density_mesh([p["xy"] for p in data if p.get("facet", "") == facet], bandwidth) for facet in facets
        }
    values = [z for mesh in meshes.values() for z in mesh[2]] if meshes else [p["value"] for p in data if "value" in p]
    domain = (min(values), max(values)) if values else (0, 1)
    if domain[0] < 0 < domain[1] and not pal.get("color_stops"):
        # A zero-centered ramp keeps opposite signs distinct. A visible neutral
        # middle also preserves zero-level contours on either slide background.
        span = max(abs(v) for v in domain)
        domain = (-span, span)
        stops = [pal["secondary"], _rgba_with_alpha(pal["ink6"], 1), pal["accent"]]
    # Equal-valued observations get a visible middle-ramp color and a single value legend.
    color_domain = domain if domain[0] != domain[1] else (domain[0] - 0.5, domain[1] + 0.5)
    sizes = [p["size"] for p in data if "size" in p]
    size_max = max(sizes) if sizes else 1
    categorical = bool(data and "group" in data[0])
    has_legend = bool(categorical or values or sizes)
    top = layout.header(title, subtitle, figure_label)
    # All facets use one explicit multiplier. Short mantissas keep the three
    # directional tick lanes legible even for very large/small component totals.
    tick_scale = (10 ** math.floor(math.log10(total)) or total) if total >= 1e5 or total < 0.1 else 1
    total_label = number_label(int(total), compact=True) if total.is_integer() and total <= 2**53 else str(total)
    note = (
        tr("KDE density per unit area · Gaussian kernel on an equilateral triangle")
        if meshes and grid is None
        else tr("Precomputed scalar field · triangular lattice")
        if grid is not None
        else tr("Components sum to {total}", total=total_label)
        + (tr(" · normalized from supplied weights") if normalize else "")
    )
    if tick_scale != 1:
        note = tr("Axis ticks × {scale} · ", scale=number_label(tick_scale, compact=True)) + note
    footer_lines = wrap_lines(note, layout.width - 56, layout.font_sizes["foot"], layout.font)
    bottom = layout.height - 28 - len(footer_lines) * layout.font_sizes["foot"] * 1.35
    legend_w = min(210, max(160, layout.width * 0.21)) if has_legend else 0
    # Narrow canvases put a categorical-only legend in one row above the panels.
    legend_fs = layout.font_sizes["legend"]
    row_widths = [19 + layout.measure(group, legend_fs) for group in groups]
    top_legend = (
        categorical
        and not values
        and not sizes
        and layout.width - 52 - legend_w - 20 < 235 * len(facets) + 24 * (len(facets) - 1)
        and sum(row_widths) + 18 * (len(groups) - 1) <= layout.width - 56
    )
    if top_legend:
        x = 28.0
        for group, item_w in zip(groups, row_widths):
            layout.parts.append(
                f'<circle cx="{x + 5:.2f}" cy="{top + 6:.2f}" r="4.5" fill={quoteattr(colors[group])}/>'
            )
            layout.text(group, x + 19, top, fs=legend_fs)
            x += item_w + 18
        top += legend_fs * 1.35 + 8
        has_legend, legend_w = False, 0
    panel_right = layout.width - 28 - (legend_w + 20 if has_legend else 0)
    panel_bbox = rigor.BBox(24, top, panel_right, bottom - 20)
    # Maximize the drawable equilateral side, rather than packing the first
    # row: four facets then form a balanced 2x2 grid instead of a sparse 3+1.
    max_cols = min(len(facets), max(1, int((panel_right - 24 + 24) // 259)))

    def panel_size(cols):
        rows = math.ceil(len(facets) / cols)
        cell_w = (panel_bbox.x1 - panel_bbox.x0 - 24 * (cols - 1)) / cols
        cell_h = (panel_bbox.y1 - panel_bbox.y0 - 24 * (rows - 1)) / rows
        return min(cell_w - 78, (cell_h - (137 if len(facets) > 1 else 100)) / _ALTITUDE)

    cols = max(range(1, max_cols + 1), key=panel_size)
    cells = rigor.allocate_facet_grid(panel_bbox, len(facets), cols=cols, gutter=24, min_cell=(235, 235))
    # A common premeasured heading band keeps all triangles physically equal,
    # even when only one heading wraps. Vertex labels already share one schema.
    figure_fonts = layout.font_sizes
    layout.font_sizes = chart_font_sizes(
        cells[0].x1 - cells[0].x0,
        cells[0].y1 - cells[0].y0,
        max(3, max(sum(p.get("facet", "") == f for p in data) for f in facets)) if kind == "scatter" else 3,
    )
    facet_h = max(
        (
            len(wrap_lines(facet, (cell.x1 - cell.x0 - 24) / 1.05, layout.font_sizes["group"], layout.heading))
            * layout.font_sizes["group"]
            * 1.35
            + 16
            for facet, cell in zip(facets, cells)
            if facet
        ),
        default=0,
    )
    for facet, cell in zip(facets, cells):
        _draw_triangle(
            layout,
            (cell.x0, cell.y0, cell.x1, cell.y1),
            labels,
            total / tick_scale,
            facet,
            [p for p in data if p.get("facet", "") == facet],
            meshes.get(facet),
            kind,
            color_domain,
            stops,
            colors,
            size_max,
            facet_h,
        )
    layout.font_sizes = figure_fonts
    if has_legend:
        x, y = panel_right + 24, top + 15
        if categorical:
            y += layout.text(tr("Groups"), x, y, bold=True, fs=layout.font_sizes["legend"]) + 13
            for group in groups:
                layout.parts.append(
                    f'<circle cx="{x + 5:.2f}" cy="{y + 6:.2f}" r="4.5" fill={quoteattr(colors[group])}/>'
                )
                y += layout.text(group, x + 19, y, width=legend_w - 19, fs=layout.font_sizes["legend"]) + 12
        if values:
            label = (
                value_label if value_label is not None else (tr("Density") if meshes and grid is None else tr("Value"))
            )
            y += layout.text(label, x, y, bold=True, width=legend_w - 8, fs=layout.font_sizes["legend"]) + 10
            if domain[0] == domain[1]:
                color = rigor.value_to_color(domain[0], *color_domain, pal, stops=stops)
                layout.parts.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="18" height="18" fill={quoteattr(color)}/>')
                y += (
                    layout.text(
                        _legend_number(layout, domain[0], legend_w - 28), x + 28, y, fs=layout.font_sizes["legend"]
                    )
                    + 16
                )
            else:
                bar_h = min(185, max(105, (bottom - y) * 0.42))
                layout.parts.append(
                    rigor.draw_colorbar(
                        x,
                        y,
                        15,
                        bar_h,
                        *domain,
                        pal,
                        orient="vertical",
                        stops=stops,
                        fs_tick=layout.font_sizes["legend"],
                    )
                )
                y += bar_h + 26
        if sizes:
            y += (
                layout.text(
                    tr("{label} (area)", label=tr(size_label)),
                    x,
                    y,
                    bold=True,
                    width=legend_w - 8,
                    fs=layout.font_sizes["legend"],
                )
                + 10
            )
            used_labels = set()
            for value in _size_references(sizes):
                label = _legend_number(layout, value, legend_w - 38)
                if label in used_labels:
                    continue
                used_labels.add(label)
                r = 13 * math.sqrt(value / size_max)
                layout.parts.append(
                    f'<circle cx="{x + 14:.2f}" cy="{y + 14:.2f}" r="{r:.2f}" '
                    f"fill={quoteattr(_rgba_with_alpha(pal['accent'], 0.2))} "
                    f'stroke={quoteattr(pal["accent"])} stroke-width="1"/>'
                )
                layout.text(label, x + 38, y + 7, fs=layout.font_sizes["legend"])
                y += 39
        if y > bottom - 8:
            raise ValueError("ternary legend is too tall; increase height or shorten category labels")
    layout.text(note, 28, bottom + 13, color=pal["ink6"], fs=layout.font_sizes["foot"], width=layout.width - 56)
    return layout.svg(
        f"Ternary {kind}; apex={labels[0]}, left={labels[1]}, right={labels[2]}; "
        f"{len(data)} observations; {len(facets)} panel(s)."
    )
