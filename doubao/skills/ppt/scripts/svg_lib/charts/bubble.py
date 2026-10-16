"""Grouped bubble scatter; marker area is proportional to the supplied size."""

import math

from .._common import _resolve_palette, _variant_is_classic
from ._academic_rigor import value_to_color
from ._chart_layout import finite
from ._xy import add_frontier, fit_series, make_xy_chart, points_to_series


def _pearson(xs, ys):
    if len(xs) < 2:
        return 0.0
    mx, my = math.fsum(xs) / len(xs), math.fsum(ys) / len(ys)
    xx = math.fsum((x - mx) ** 2 for x in xs)
    yy = math.fsum((y - my) ** 2 for y in ys)
    return math.fsum((x - mx) * (y - my) for x, y in zip(xs, ys)) / math.sqrt(xx * yy) if xx and yy else 0.0


def _quantile(values, q):
    if not values:
        return 0.0
    at = (len(values) - 1) * q
    i = int(at)
    j = min(i + 1, len(values) - 1)
    return values[i] + (values[j] - values[i]) * (at - i)


def make_bubble(
    points,
    *,
    x_unit="",
    y_unit="",
    size_unit="",
    x_title=None,
    y_title=None,
    title=None,
    subtitle=None,
    figure_label=None,
    note=None,
    source=None,
    size_legend_values=None,
    color_values=None,
    color_unit="",
    highlight_mask=None,
    r_min=6.0,
    r_max=36.0,
    width=1200,
    height=820,
    font_family=None,
    palette=None,
    variant=None,
    multi_mode="auto",
    fit=None,
    reference_lines=None,
    x_transform="linear",
    y_transform="linear",
    frontier=None,
    reference_band=None,
):
    """Tuple (x,y,size,label), grouped point dictionaries or canonical series.

    ``frontier=True`` draws the dashed Pareto front of the supplied points (lower x, higher y better);
    ``"min"`` when lower y is better (ML params–accuracy, materials 强度–塑性权衡). The size key sits in a free
    plot corner when one exists. ``reference_band={'points': [(x, y), ...], 'label': '传统合金'}`` (or a list) shades the envelope of a
    reference population behind the points (e.g. conventional alloys on a strength–ductility map).

    Size zero has zero area. ``r_max`` fixes the largest radius. ``r_min`` is
    retained for call compatibility; the former positive area floor was removed
    because it distorted size ratios. Numeric ``color_values`` shares one scale.
    """
    _variant_is_classic("bubble", variant)
    if finite(r_max, "r_max", minimum=0) <= 0:
        raise ValueError("r_max must be positive")
    if finite(r_min, "r_min", minimum=0) > r_max:
        raise ValueError("r_min cannot exceed r_max")
    raw = []
    for p in points:
        if isinstance(p, dict):
            raw.append(p)
        else:
            if len(p) < 3:
                raise ValueError("bubble points require x, y and size")
            raw.append({"x": p[0], "y": p[1], "size": p[2], "label": p[3] if len(p) > 3 else ""})
    resolved = points_to_series(raw, fit=fit, highlight_mask=highlight_mask)
    flat = [p for s in resolved for p in s["points"]]
    if any("size" not in p for p in flat):
        raise ValueError("every bubble observation requires size")
    color_legend = None
    if color_values is not None:
        if len(color_values) != len(flat):
            raise ValueError("color_values length mismatch")
        # Map by input order before grouping so interleaved categories do not
        # accidentally swap their numeric color measurements.
        pal = _resolve_palette(palette or "archive_ink")
        values = [finite(v, "color value") for v in color_values]
        low, high = min(values), max(values)
        color_fn = lambda value: value_to_color(value, low, high, pal=pal)
        colored = []
        offset = 0
        if raw and ("points" in raw[0] or "curve" in raw[0]):
            for s in raw:
                ps = []
                for p in s.get("points", []):
                    q = dict(p) if isinstance(p, dict) else {"x": p[0], "y": p[1]}
                    q["color"] = color_fn(values[offset])
                    offset += 1
                    ps.append(q)
                colored.append(dict(s, points=ps))
        else:
            colored = [dict(p, color=color_fn(v)) for p, v in zip(raw, values)]
        resolved = points_to_series(colored, fit=fit, highlight_mask=highlight_mask)
        color_legend = (low, high, color_unit, color_fn)
    resolved = fit_series(resolved, x_transform=x_transform, y_transform=y_transform)
    resolved = add_frontier(resolved, frontier)
    if multi_mode not in (None, "single", "off", "auto", "with_marginal"):
        raise ValueError("multi_mode must be single, auto or with_marginal")
    mode = (
        "with_marginal"
        if multi_mode == "with_marginal" or multi_mode == "auto" and len(flat) >= 60 and width >= 800 and height >= 670
        else "single"
    )
    return make_xy_chart(
        resolved,
        title=title,
        subtitle=subtitle,
        figure_label=figure_label,
        note=note,
        source=source,
        x_title=x_title,
        y_title=y_title,
        x_unit=x_unit,
        y_unit=y_unit,
        width=width,
        height=height,
        palette=palette,
        font_family=font_family,
        x_transform=x_transform,
        y_transform=y_transform,
        reference_lines=reference_lines,
        show_stats=fit not in (None, "none"),
        mode=mode,
        size_legend_values=size_legend_values,
        size_unit=size_unit,
        color_legend=color_legend,
        radius_max=r_max,
        reference_bands=reference_band,
    )
