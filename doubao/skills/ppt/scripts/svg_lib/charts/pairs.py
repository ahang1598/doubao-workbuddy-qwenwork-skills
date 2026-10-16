"""Shared-scale scatter/density matrix with observed marginals and correlation."""

from __future__ import annotations

import math
from collections.abc import Mapping
from xml.sax.saxutils import quoteattr

from .._typography import chart_font_sizes
from ._academic_rigor import BBox
from ._chart_layout import ChartLayout, finite, wrap_lines
from ._composition_distribution import (
    axis_note,
    footer,
    footer_height,
    legend,
    marginal_profiles,
    render_contours,
    render_marginal,
    transformed,
    x_ticks,
)
from ._pair_glyphs import frequency_display, frequency_note, frequency_reference
from ._xy import (
    fit_series,
    infer_scales,
    normalize_series,
    points_to_series,
    render_xy_plot,
    series_context,
    xy_density,
)
from ._shared import tr

__all__ = ["make_pairs"]


def average_ranks(values):
    """One-based average ranks; tied observations retain their exact identity."""
    order = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        end = start + 1
        while end < len(order) and values[order[end]] == values[order[start]]:
            end += 1
        rank = (start + 1 + end) / 2
        for index in order[start:end]:
            ranks[index] = rank
        start = end
    return ranks


def correlation(xs, ys, method="pearson"):
    """Centered, range-normalized correlation; undefined variance returns None."""
    if method not in ("pearson", "spearman"):
        raise ValueError("method must be pearson or spearman")
    if len(xs) != len(ys):
        raise ValueError("correlation requires paired observations")
    if len(xs) < 2:
        return None
    if method == "spearman":
        xs, ys = average_ranks(xs), average_ranks(ys)
    xlow, ylow = min(xs), min(ys)
    dx, dy = max(xs) - xlow, max(ys) - ylow
    if dx == 0 or dy == 0:
        return None
    xs, ys = [(v - xlow) / dx for v in xs], [(v - ylow) / dy for v in ys]
    mx, my = math.fsum(xs) / len(xs), math.fsum(ys) / len(ys)
    xs, ys = [v - mx for v in xs], [v - my for v in ys]
    cross = math.fsum(x * y for x, y in zip(xs, ys))
    norm = math.sqrt(math.fsum(x * x for x in xs) * math.fsum(y * y for y in ys))
    return max(-1.0, min(1.0, cross / norm)) if norm else None


def _records(data, variables, group_key):
    if isinstance(data, Mapping):
        lengths = {len(values) for values in data.values()}
        if len(lengths) != 1:
            raise ValueError("all input columns must have the same length")
        data = [dict(zip(data, row)) for row in zip(*data.values())]
    data = list(data)
    if not data or any(not isinstance(row, Mapping) for row in data):
        raise ValueError("pairs data must be nonempty record dictionaries or equal-length columns")
    variables = list(variables) if variables is not None else [key for key in data[0] if key != group_key]
    if len(variables) < 2 or len(set(variables)) != len(variables):
        raise ValueError("pairs requires at least two distinct variables")
    groups = {}
    for index, row in enumerate(data):
        if any(variable not in row for variable in variables):
            raise ValueError(f"record {index} must contain every selected variable; missing values are not dropped")
        name = str(row.get(group_key, "Observations")) if group_key is not None else "Observations"
        groups.setdefault(name, []).append({variable: finite(row[variable], str(variable)) for variable in variables})
    return variables, groups


def _series(groups, x, y):
    return normalize_series(
        [{"name": name, "points": [{"x": row[x], "y": row[y]} for row in rows]} for name, rows in groups.items()]
    )


def make_pairs(
    data,
    *,
    variables=None,
    group_key="group",
    variable_labels=None,
    diagonal="hist",
    lower="scatter",
    method="pearson",
    bins=12,
    bandwidth=None,
    contour_levels=(0.2, 0.5, 0.8),
    transforms=None,
    fit=None,
    show_ci=True,
    group_colors=None,
    extra_panels=None,
    title=None,
    subtitle=None,
    figure_label=None,
    note=None,
    source=None,
    width=1200,
    height=1040,
    palette=None,
    font_family=None,
    variant=None,
):
    """Return a complete pairs SVG from record dictionaries or column arrays.

    Lower cells show exact observations or product-Gaussian ``lower='density'``
    contours. Diagonal cells estimate actual per-group histograms/KDEs, while
    upper cells show separate per-group Pearson/Spearman coefficients and n.
    Constant variables report ``undefined``. ``transforms`` maps variable keys
    to ``linear``/``log10``; all statistics use those coordinate domains.
    Complete variable labels and numbered group names are preserved outside
    the matrix. Each variable has one scale everywhere; each group one color.

    Optional ``extra_panels=[{'name': ..., 'series': canonical_xy_series,
    'fit': 'linear', 'x_title': ..., 'y_title': ...}]`` adds up to three fitted
    scatter panels in a bottom row, using the same group colors. Their scales
    are independent, as their variables may differ from the matrix variables.
    """
    if variant not in (None, "classic", "default"):
        raise ValueError("pairs supports only the classic/default variant")
    if diagonal not in ("hist", "kde"):
        raise ValueError("diagonal must be hist or kde")
    if lower not in ("scatter", "density"):
        raise ValueError("lower must be scatter or density")
    if method not in ("pearson", "spearman"):
        raise ValueError("method must be pearson or spearman")
    variables, groups = _records(data, variables, group_key)
    frequency_max = frequency_reference(groups, variables) if lower == "scatter" else 1
    transforms = dict(transforms or {})
    labels = {variable: str((variable_labels or {}).get(variable, variable)) for variable in variables}
    if any(value not in ("linear", "log10") for value in transforms.values()):
        raise ValueError("variable transforms must be linear or log10")
    if set(transforms) - set(variables):
        raise ValueError("transforms must refer to selected variables")
    scales = {
        variable: infer_scales(
            _series(groups, variable, variable),
            x_transform=transforms.get(variable, "linear"),
            y_transform=transforms.get(variable, "linear"),
        )[0]
        for variable in variables
    }
    identity = _series(groups, variables[0], variables[1])
    extra_specs = list(extra_panels or [])
    if len(extra_specs) > 3:
        raise ValueError("pairs supports at most three extra panels per row")
    extras = []
    for spec in extra_specs:
        extra = points_to_series(spec["series"], fit=spec.get("fit"))
        xt, yt = spec.get("x_transform", "linear"), spec.get("y_transform", "linear")
        extra = fit_series(extra, show_ci=spec.get("show_ci", show_ci), x_transform=xt, y_transform=yt)
        if any(
            isinstance(point[axis], str)
            for item in extra
            for point in item["points"] + item["curve"]
            for axis in ("x", "y")
        ):
            raise ValueError("extra panels require numerical axes")
        extra_scales = infer_scales(extra, x_transform=xt, y_transform=yt)
        extras.append((spec, extra, extra_scales))
        known = {item["name"] for item in identity}
        identity.extend(item for item in extra if item["name"] not in known)
    for item in identity:
        if group_colors and item["name"] in group_colors:
            item["color"] = group_colors[item["name"]]
    layout = ChartLayout(width, height, palette, font_family, n_items=sum(len(rows) for rows in groups.values()))
    outer_fonts = layout.font_sizes
    # Matrix text uses the actual cell width, with observation count unchanged.
    layout.font_sizes = chart_font_sizes(
        (layout.width - 230) / len(variables),
        layout.height / len(variables),
        sum(len(rows) for rows in groups.values()),
    )
    fs, small_fs = layout.font_sizes["label"], layout.font_sizes["foot"]
    line_h, small_h = fs * 1.35, small_fs * 1.35
    context = series_context(identity, layout.pal)
    cell_fonts = layout.font_sizes
    layout.font_sizes = outer_fonts
    top = layout.header(title, subtitle, figure_label)
    layout.font_sizes = cell_fonts
    # Wide, short canvases keep the matrix tall by moving legend and notes to a sidebar.
    sidebar = not extras and layout.width >= 1.6 * layout.height
    sidebar_w = max(200.0, min(300.0, layout.width * 0.25)) if sidebar else 0.0
    if not sidebar:
        top = legend(layout, [item["name"] for item in identity], context, top, numbered=True)
    notes = [
        tr(
            "Upper: {method} per group; n counts complete observed pairs. Undefined means fewer than two values or zero variance.",
            method="Pearson r" if method == "pearson" else tr("Spearman ρ (average ranks for ties)"),
        ),
        tr(
            "Diagonal: {diagonal}. Lower: {lower}.",
            diagonal=tr(
                "observed histogram counts"
                if diagonal == "hist"
                else "Gaussian KDE with shared relative height per variable"
            ),
            lower=tr("observed scatter")
            if lower == "scatter"
            else tr(
                "2D Gaussian KDE; contours at {levels} of each group’s peak",
                levels=", ".join(f"{level:.0%}" for level in contour_levels),
            ),
        ),
    ]
    if frequency_max > 1:
        notes.append(frequency_note(frequency_max))
    if transforms:
        notes.append(
            tr("Axis/statistical coordinates: ")
            + "; ".join(f"{labels[var]}: {transforms.get(var, 'linear')}" for var in variables)
            + "."
        )
    notes.extend([note, source])
    foot_h = 0 if sidebar else footer_height(layout, notes)
    nvar = len(variables)
    row_label_width = min(160, max(24 if sidebar else 82, max(layout.measure(label, fs) for label in labels.values())))
    # Never break the numerical offset itself across lines. Long variable
    # names may wrap, while a scale multiplier must remain easy to read.
    precision_token_width = max(
        (layout.measure(token, fs) for scale in scales.values() for token in axis_note(scale).split()), default=0
    )
    row_label_width = max(row_label_width, precision_token_width + 8)
    left = row_label_width + 80
    right = layout.width - 34 - (sidebar_w + 20 if sidebar else 0)
    gap_x, gap_y = (26.0, 10.0) if sidebar else (26.0, 20.0)
    cell_w = (right - left - gap_x * (nvar - 1)) / nvar
    if cell_w < 126:
        raise ValueError("pairs canvas needs more width for all variables and labels")
    header_h = max(len(wrap_lines(label, cell_w - 4, fs, layout.font)) * line_h for label in labels.values())
    for col, variable in enumerate(variables):
        x0 = left + col * (cell_w + gap_x)
        layout.text(labels[variable], x0 + cell_w / 2, top, fs=fs, bold=True, anchor="middle", width=cell_w - 4)
    top += header_h + 15
    precision_h = max(
        (
            len(wrap_lines(axis_note(scales[var]), cell_w, small_fs, layout.font)) * small_h
            if axis_note(scales[var])
            else 0
            for var in variables
        ),
        default=0,
    )
    extra_h = 280 if extras else 0
    bottom = layout.height - (16 if sidebar else 28) - foot_h - 38 - precision_h - extra_h
    cell_h = (bottom - top - gap_y * (nvar - 1)) / nvar
    if cell_h < max(70 if sidebar else 105, 29 + len(groups) * max(24, small_h + 6)):
        raise ValueError("pairs canvas needs more height for all variables and groups")
    for row, yvar in enumerate(variables):
        y0 = top + row * (cell_h + gap_y)
        row_lines = wrap_lines(labels[yvar], row_label_width, fs, layout.font)
        for annotation in axis_note(scales[yvar]).split("; "):
            if not annotation:
                continue
            if layout.measure(annotation, fs) <= row_label_width:
                row_lines.append(annotation)
            elif annotation.startswith("offset "):
                row_lines.extend(["offset", annotation[7:]])
            else:
                row_lines.extend(wrap_lines(annotation, row_label_width, fs, layout.font))
        text_h = len(row_lines) * line_h
        if text_h > cell_h - 8:
            raise ValueError("variable label needs a taller or wider pairs canvas")
        layout.text("\n".join(row_lines), row_label_width + 18, y0 + (cell_h - text_h) / 2, fs=fs, anchor="end")
        for col, xvar in enumerate(variables):
            x0 = left + col * (cell_w + gap_x)
            box = BBox(x0, y0, x0 + cell_w, y0 + cell_h)
            xs, ys = scales[xvar], scales[yvar]
            role = "pairs-diagonal" if row == col else "pairs-lower" if row > col else "pairs-correlation"
            layout.parts.append(
                f'<g data-role="{role}" data-x-variable={quoteattr(str(xvar))} data-y-variable={quoteattr(str(yvar))} data-bbox="{box.x0:g},{box.y0:g},{box.x1:g},{box.y1:g}">'
            )
            layout.parts.append(
                f'<rect x="{box.x0:.4f}" y="{box.y0:.4f}" width="{cell_w:.4f}" height="{cell_h:.4f}" fill="none" stroke={quoteattr(layout.pal["grid"])} stroke-width=".8"/>'
            )
            cell_series = _series(groups, xvar, yvar)
            layout.font_sizes = chart_font_sizes(cell_w, cell_h, xy_density(cell_series))
            if row == col:
                profile_box = BBox(box.x0, box.y0 + 26, box.x1, box.y1)
                profiles = marginal_profiles(cell_series, "x", xs, diagonal, bins, bandwidth)
                diagonal_heading = (
                    tr("Count / bin · max {max}", max=max(max(profile["ys"]) for profile in profiles))
                    if diagonal == "hist"
                    else tr("Gaussian KDE")
                )
                layout.text(diagonal_heading, box.x0 + 8, box.y0 + 6, fs=small_fs)
                layout.parts.append(render_marginal(profiles, profile_box, xs, context, kind=diagonal))
                if row == nvar - 1:
                    x_ticks(layout, box, xs)
            elif row > col:
                if fit:
                    cell_series = fit_series(
                        normalize_series([dict(item, fit=fit) for item in cell_series]),
                        show_ci=show_ci,
                        x_transform=xs.transform,
                        y_transform=ys.transform,
                    )
                if lower == "density":
                    layout.parts.append(render_contours(cell_series, box, xs, ys, context, levels=contour_levels))
                    cell_series = [dict(item, marker="none") for item in cell_series]
                display, glyph = frequency_display(
                    cell_series,
                    context,
                    frequency_max,
                    font=layout.font,
                    ink=layout.ink,
                    paper=layout.pal.get("bg") or "#FFFFFF",
                )
                layout.parts.append(
                    render_xy_plot(
                        display,
                        box,
                        x_scale=xs,
                        y_scale=ys,
                        context=context,
                        palette=layout.pal,
                        font_family=layout.font,
                        font_sizes=layout.font_sizes,
                        show_x_labels=row == nvar - 1,
                        show_y_labels=col == 0,
                        glyph_renderer=glyph,
                        size_max=frequency_max if glyph else None,
                        radius_max=9,
                    )
                )
            else:
                layout.text(
                    "Pearson r" if method == "pearson" else "Spearman ρ",
                    (box.x0 + box.x1) / 2,
                    box.y0 + 8,
                    fs=small_fs,
                    anchor="middle",
                )
                for index, (name, rows) in enumerate(groups.items()):
                    values_x = [transformed(record[xvar], xs) for record in rows]
                    values_y = [transformed(record[yvar], ys) for record in rows]
                    value = correlation(values_x, values_y, method)
                    label = f"[{index + 1}] {'undefined' if value is None else f'{value:+.2f}'} (n={len(rows)})"
                    if layout.measure(label, small_fs) > cell_w - 12:
                        raise ValueError("correlation labels need a wider pairs canvas")
                    yy = box.y0 + 29 + index * max(24, small_h + 6)
                    opacity = 0.05 if value is None else 0.07 + 0.2 * abs(value)
                    layout.parts.append(
                        f'<rect x="{box.x0 + 4:.4f}" y="{yy - 2:.4f}" width="{cell_w - 8:.4f}" height="21" fill={quoteattr(context.color_of(name))} fill-opacity="{opacity:.3f}" data-role="correlation-value" data-series={quoteattr(name)} data-method="{method}" data-value="{"undefined" if value is None else f"{value:.17g}"}" data-n="{len(rows)}"/>'
                    )
                    layout.text(label, (box.x0 + box.x1) / 2, yy, fs=small_fs, anchor="middle")
            layout.parts.append("</g>")
    for col, variable in enumerate(variables):
        if axis_note(scales[variable]):
            center = left + col * (cell_w + gap_x) + cell_w / 2
            layout.text(axis_note(scales[variable]), center, bottom + 29, fs=small_fs, anchor="middle", width=cell_w)
    if extras:
        extra_top = bottom + 42 + precision_h
        panel_w = (layout.width - 114 - 44 * (len(extras) - 1)) / len(extras)
        if panel_w < 210:
            raise ValueError("extra scatter panels need a wider canvas")
        for index, (spec, extra, (xs, ys)) in enumerate(extras):
            layout.font_sizes = chart_font_sizes(panel_w, extra_h, xy_density(extra))
            fs, small_fs = layout.font_sizes["label"], layout.font_sizes["foot"]
            line_h, small_h = fs * 1.35, small_fs * 1.35
            x0 = 80 + index * (panel_w + 44)
            heading = str(spec.get("name", f"Additional scatter {index + 1}"))
            yheading = str(spec.get("y_title", "Y"))
            if axis_note(ys):
                yheading += " · " + axis_note(ys)
            heading_h = len(wrap_lines(heading, panel_w, fs, layout.font)) * line_h
            yheading_h = len(wrap_lines(yheading, panel_w, small_fs, layout.font)) * small_h
            layout.text(heading, x0, extra_top, fs=fs, bold=True, width=panel_w)
            layout.text(yheading, x0, extra_top + heading_h + 5, fs=small_fs, width=panel_w)
            panel_top = extra_top + heading_h + yheading_h + 14
            xheading = str(spec.get("x_title", "X"))
            if axis_note(xs):
                xheading += " · " + axis_note(xs)
            xheading_h = len(wrap_lines(xheading, panel_w, small_fs, layout.font)) * small_h
            panel_bottom = layout.height - 28 - foot_h - xheading_h - 42
            box = BBox(x0, panel_top, x0 + panel_w, panel_bottom)
            if box.y1 - box.y0 < 105:
                raise ValueError("extra scatter titles need a taller canvas")
            layout.parts.append('<g data-role="pairs-extra">')
            layout.parts.append(
                render_xy_plot(
                    extra,
                    box,
                    x_scale=xs,
                    y_scale=ys,
                    context=context,
                    palette=layout.pal,
                    font_family=layout.font,
                    font_sizes=layout.font_sizes,
                )
            )
            layout.parts.append("</g>")
            layout.text(xheading, x0 + panel_w / 2, panel_bottom + 31, fs=small_fs, anchor="middle", width=panel_w)
    layout.font_sizes = cell_fonts
    if sidebar:
        side_x, side_top = layout.width - 28 - sidebar_w, top
        legend_fs = layout.font_sizes["legend"]
        for index, item in enumerate(identity):
            layout.parts.append(
                f'<rect x="{side_x:.3f}" y="{side_top + legend_fs * 0.12:.3f}" width="{legend_fs * 0.8:.3f}" height="{legend_fs * 0.8:.3f}" fill={quoteattr(context.color_of(item["name"]))} data-role="legend-swatch" data-series={quoteattr(item["name"])}/>'
            )
            text_x = side_x + legend_fs * 0.8 + 9
            side_top += (
                layout.text(
                    f"[{index + 1}] {item['name']}", text_x, side_top, fs=legend_fs, width=layout.width - 28 - text_x
                )
                + 5
            )
        side_top += 8
        for value in notes:
            if value:
                side_top += (
                    layout.text(value, side_x, side_top, fs=small_fs, color=layout.pal["ink6"], width=sidebar_w) + 5
                )
        if side_top > layout.height - 12:
            raise ValueError("pairs canvas needs more height for its legend and notes")
    else:
        footer(layout, notes, layout.height - 28 - foot_h)
    return layout.svg("Pairs matrix with shared scales, observed marginals and group correlations")
