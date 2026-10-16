"""Radar profiles with explicit per-axis domains and shared-scale facets."""

from __future__ import annotations

import math
from xml.sax.saxutils import quoteattr

from .._typography import chart_font_sizes
from ._academic_rigor import BBox, SeriesContext, SharedScale
from ._distribution import axis_ticks
from ._polar import (
    PolarGeometry,
    categories_order,
    circle_mark,
    error_mark,
    label_requirements,
    legend_rows,
    normalize_series,
    numeric_domain,
    path,
    polar_layout,
    render_labels,
    render_legend,
    stroke,
)
from ._shared import tr


def make_radar(
    axes,
    series,
    *,
    grid="polygon",
    title=None,
    subtitle=None,
    figure_label=None,
    note=None,
    width=1040,
    height=820,
    palette=None,
    font_family=None,
):
    """Return one SVG containing one or more comparable radar profiles.

    Axes are names or ``{name, min, max, annotation}``. Explicit bounds must
    contain every observation and error endpoint; omitted bounds are inferred
    from all facets. Series contain ``name``, aligned ``values`` and optional
    ``color``/``facet``. Values are numbers, None or ``{value, low, high}``.
    The optional facet field automatically creates panels sharing axis ranges
    and series colors. Missing axes break outlines and suppress polygon fill.
    """
    if grid not in {"polygon", "circle"}:
        raise ValueError("grid must be polygon or circle")
    cats, indices = categories_order(axes)
    if len(cats) < 3:
        raise ValueError("radar requires at least three axes")
    raw_series = list(series)
    if not raw_series:
        raise ValueError("radar requires at least one series")
    facets = list(dict.fromkeys(str(s.get("facet", "")) for s in raw_series))
    panels = []
    all_data = []
    for facet in facets:
        data = normalize_series([dict(s, kind="line") for s in raw_series if str(s.get("facet", "")) == facet], indices)
        if any(s["direction"] != "out" for s in data):
            raise ValueError("radar directions are outward; inward profiles are not supported")
        panels.append((facet, data))
        all_data.extend(data)
    scales = []
    displayed = []
    for i, axis in enumerate(cats):
        if ("min" in axis) != ("max" in axis):
            raise ValueError("radar axis bounds require both min and max")
        observed = [
            item[key]
            for s in all_data
            if (item := s["values"][i]) is not None
            for key in ("value", "low", "high")
            if key in item
        ]
        bounds = (axis["min"], axis["max"]) if "min" in axis else None
        domain = numeric_domain(observed, bounds, include_zero=bounds is None)
        scales.append(SharedScale(domain))
        _, labels, offset = axis_ticks(domain, 2)
        label = f"{axis['name']}\n" + tr("{lo} to {hi}", lo=labels[0], hi=labels[1]) + (f"\n{offset}" if offset else "")
        displayed.append(dict(axis, name=label))
    layout = polar_layout(width, height, palette, font_family, n_items=len(cats))
    ids = list(dict.fromkeys(s["name"] for s in all_data))
    context = SeriesContext(ids, pal=layout.pal)
    explicit_colors = {}
    for s in all_data:
        if "color" in s:
            if s["name"] in explicit_colors and explicit_colors[s["name"]] != s["color"]:
                raise ValueError("one series name must use the same color across facets")
            explicit_colors[s["name"]] = s["color"]
    context.colors.update(explicit_colors)
    from ._chart_layout import wrap_lines

    columns = min(2, len(panels))
    panel_width = max(360.0, layout.width / columns)
    layout.width = panel_width * columns
    top = layout.header(title, subtitle, figure_label)
    layout.font_sizes = chart_font_sizes(panel_width, min(height, panel_width * 0.8), len(cats))
    unique = [dict(next(s for s in all_data if s["name"] == name), color=context.color_of(name)) for name in ids]
    legend, legend_height = legend_rows(layout, unique, [])
    rail_width = min(140.0, panel_width * 0.21)
    rows = math.ceil(len(panels) / columns)
    foot = layout.font_sizes["foot"]
    caption = tr("Grid rings show 25%, 50%, 75% and 100% of each stated axis range; ranges are shared across panels.")
    caption_height = len(wrap_lines(caption, layout.width - 56, foot, layout.font)) * foot * 1.35 + 7
    note_height = len(wrap_lines(note, layout.width - 56, foot, layout.font)) * foot * 1.35 + 8 if note else 0
    chrome = (37 if any(f for f, _ in panels) else 12) + 15 + 20
    available = (height - top - legend_height - caption_height - note_height - 32) / rows
    radius = min((panel_width - 2 * rail_width - 112) / 2, (available - chrome) / 2)
    radius = max(40.0, radius)
    plot_height = max(radius * 2 + chrome, label_requirements(layout, displayed, rail_width) + 20)
    layout.height = max(layout.height, top + rows * plot_height + legend_height + caption_height + note_height + 32)
    for index, (facet, data) in enumerate(panels):
        col, row = index % columns, index // columns
        left = col * panel_width
        panel_top = top + row * plot_height
        if facet:
            layout.text(
                facet,
                left + panel_width / 2,
                panel_top,
                fs=layout.font_sizes["group"],
                bold=True,
                anchor="middle",
                width=panel_width - 56,
            )
        plot_top = panel_top + (37 if facet else 12)
        plot_bottom = panel_top + plot_height - 15
        render_radar_panel(
            {"displayed": displayed, "scales": scales, "series": data, "context": context, "data": {"grid": grid}},
            layout,
            BBox(left, plot_top, left + panel_width, plot_bottom),
        )
    legend_top = top + rows * plot_height + 12
    render_legend(layout, legend, legend_top)
    layout.text(
        caption,
        28,
        legend_top + legend_height + 7,
        fs=layout.font_sizes["foot"],
        color=layout.pal["ink6"],
        width=layout.width - 56,
    )
    if note:
        layout.text(
            note,
            28,
            legend_top + legend_height + caption_height + 4,
            fs=layout.font_sizes["foot"],
            color=layout.pal["ink6"],
            width=layout.width - 56,
        )
    return layout.svg("Radar profiles with per-axis numerical ranges and shared-scale facets")


def prepare_radar(data, canvas):
    grid = data.get("grid", "polygon")
    if grid not in ("polygon", "circle"):
        raise ValueError("radar grid must be polygon or circle")
    cats, indices = categories_order(data["axes"])
    if len(cats) < 3:
        raise ValueError("radar requires at least three axes")
    series = normalize_series([dict(s, kind="line") for s in data["series"]], indices)
    if not series or any(s["direction"] != "out" for s in series):
        raise ValueError("radar requires outward profiles")
    context = SeriesContext([s["name"] for s in series], pal=canvas.pal)
    context.colors.update({s["name"]: s["color"] for s in series if "color" in s})
    scales, displayed = [], []
    for i, axis in enumerate(cats):
        if ("min" in axis) != ("max" in axis):
            raise ValueError("radar axis bounds require both min and max")
        values = [v[k] for s in series if (v := s["values"][i]) is not None for k in ("value", "low", "high") if k in v]
        domain = numeric_domain(
            values, (axis["min"], axis["max"]) if "min" in axis else None, include_zero="min" not in axis
        )
        scales.append(SharedScale(domain))
        _, labels, offset = axis_ticks(domain, 2)
        displayed.append(
            dict(
                axis,
                name=f"{axis['name']}\n"
                + tr("{lo} to {hi}", lo=labels[0], hi=labels[1])
                + (f"\n{offset}" if offset else ""),
            )
        )
    return {
        "cats": cats,
        "displayed": displayed,
        "scales": scales,
        "series": series,
        "context": context,
        "entries": [{"name": n, "color": context.color_of(n), "direction": "out"} for n in context.ids],
        "notes": ["Rings: 25%, 50%, 75%, 100% of each stated axis range."],
        "min_width": 620,
        "min_height": max(380, label_requirements(canvas, displayed, 140) + 40),
    }


def render_radar_panel(panel, canvas, body):
    displayed, scales, series = panel["displayed"], panel["scales"], panel["series"]
    rail = min(140, (body.x1 - body.x0) * 0.21)
    radius = min((body.x1 - body.x0 - 2 * rail - 112) / 2, (body.y1 - body.y0 - 20) / 2)
    geometry = PolarGeometry((body.x0 + body.x1) / 2, (body.y0 + body.y1) / 2, 0, radius, len(displayed))
    geometry.start = -90 - 180 / len(displayed)
    angles = [geometry.angle(i) for i in range(len(displayed))]
    for fraction in (0.25, 0.5, 0.75, 1):
        d = (
            geometry.arc(radius * fraction)
            if panel["data"].get("grid", "polygon") == "circle"
            else path([geometry.point(radius * fraction, a) for a in angles], True)
        )
        stroke(
            canvas,
            d,
            width=0.8,
            stroke_dasharray="3 4" if fraction < 1 else "none",
            data_role="radar-grid",
            data_fraction=fraction,
        )
    for angle in angles:
        stroke(canvas, path([(geometry.cx, geometry.cy), geometry.point(radius, angle)]), width=0.8)
    anchors = {}
    for s in series:
        color = panel["context"].color_of(s["name"])
        points = [
            None if v is None else geometry.point(scales[i].map(v["value"], 0, radius), angles[i])
            for i, v in enumerate(s["values"])
        ]
        if all(p is not None for p in points):
            canvas.parts.append(
                f'<path d="{path(points, True)}" fill={quoteattr(color)} fill-opacity=".12" stroke={quoteattr(color)} stroke-width="2" data-role="radar-profile" data-series={quoteattr(s["name"])}/>'
            )
        else:
            for i, p in enumerate(points):
                q = points[(i + 1) % len(points)]
                if p is not None and q is not None:
                    stroke(canvas, path([p, q]), color, 2, data_role="radar-profile", data_series=s["name"])
        for i, v in enumerate(s["values"]):
            if v is not None:
                error_mark(canvas, geometry, scales[i], v, angles[i], color, "out", "linear")
                circle_mark(
                    canvas,
                    points[i],
                    color,
                    radius=3.3,
                    role="radar-point",
                    attrs=f'data-series={quoteattr(s["name"])} data-axis="{i}" data-value="{v["value"]}" data-radius="{scales[i].map(v["value"], 0, radius):.12g}" data-domain="{scales[i].domain[0]},{scales[i].domain[1]}"',
                )
                anchors[("point", s["name"] + "/" + str(i))] = (*points[i], 3.3)
    render_labels(
        canvas,
        geometry,
        displayed,
        radius,
        body.y0 + 10,
        body.y1 - 10,
        left=geometry.cx - radius - rail - 32,
        right=geometry.cx + radius + rail + 32,
        rail_width=rail,
    )
    return {
        "plot_bbox": BBox(geometry.cx - radius, geometry.cy - radius, geometry.cx + radius, geometry.cy + radius),
        "anchors": anchors,
    }
