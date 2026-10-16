"""Observation-only statistics and flat SVG layers for pairs charts."""

from __future__ import annotations

import math
from xml.sax.saxutils import quoteattr

from ._academic_rigor import BBox
from ._chart_layout import wrap_lines
from ._distribution import bandwidth_for, kde, sample_stats
from ._xy import _axis_format, _path


def transformed(value, scale):
    return math.log10(value) if scale.transform == "log10" else value


def transform_domain(scale):
    return tuple(transformed(value, scale) for value in scale.domain)


def inverse(value, scale):
    try:
        result = 10**value if scale.transform == "log10" else value
    except OverflowError as exc:
        raise ValueError("statistical layer exceeds finite axis coordinates") from exc
    if not math.isfinite(result) or (scale.transform == "log10" and result <= 0):
        raise ValueError("statistical layer exceeds finite axis coordinates")
    return result


def histogram(values, domain, bins=12):
    """Equal-width bins in the specified transform domain; final bin is closed."""
    if isinstance(bins, bool) or not isinstance(bins, int) or not 1 <= bins <= 200:
        raise ValueError("bins must be an integer from 1 to 200")
    low, high = domain
    if high <= low:
        raise ValueError("histogram domain must have positive width")
    counts = [0] * bins
    for value in values:
        if not low <= value <= high:
            raise ValueError("histogram domain must include every observation")
        index = min(bins - 1, int((value - low) / (high - low) * bins))
        counts[index] += 1
    return [low + (high - low) * i / bins for i in range(bins + 1)], counts


def marginal_profiles(series, axis, scale, kind, bins=12, bandwidth=None):
    """Compute one profile per observed group; predictions never add samples."""
    if kind == "hist_kde":
        profiles = marginal_profiles(series, axis, scale, "hist", bins, bandwidth)
        density = marginal_profiles(series, axis, scale, "kde", bins, bandwidth)
        for profile, curve in zip(profiles, density):
            profile["kde"] = dict(curve, ys=[v * curve["n"] / bins for v in curve["ys"]])
        return profiles
    if kind not in ("hist", "kde", "box"):
        raise ValueError("marginals/diagonal must be hist, kde or box")
    domain = transform_domain(scale)
    profiles = []
    for item in series:
        values = [transformed(point[axis], scale) for point in item["points"]]
        if not values:
            continue
        profile = {"name": item["name"], "n": len(values), "values": values}
        if kind == "hist":
            profile["xs"], profile["ys"] = histogram(values, domain, bins)
        elif kind == "kde":
            # A remote group's observations or an extended prediction curve can make a uniform full-domain grid miss
            # this group's entire kernel.
            bw = bandwidth_for(values, bandwidth, domain[1] - domain[0])
            support = (max(domain[0], min(values) - 5 * bw), min(domain[1], max(values) + 5 * bw))
            profile["xs"], heights = kde(values, support, bandwidth=bw, points=129)
            density_factor = (domain[1] - domain[0]) / (support[1] - support[0])
            profile["ys"] = [height * density_factor for height in heights]
        else:
            # Unit-interval arithmetic preserves tiny/offset observations.
            low, high = domain
            normalized = [(value - low) / (high - low) for value in values]
            stats = sample_stats(normalized)
            profile["outliers"] = [
                value for value, unit in zip(values, normalized) if unit < stats["lo"] or unit > stats["hi"]
            ]
            profile["stats"] = {key: low + (high - low) * stats[key] for key in ("q1", "median", "q3", "lo", "hi")}
        profiles.append(profile)
    return profiles


def render_marginal(profiles, bbox, scale, context, *, kind, axis="x", maximum=None):
    """Render a marginal in real shared coordinates, without axes or headers."""
    bbox = BBox(*bbox)
    low, high = transform_domain(scale)
    horizontal = axis == "x"
    along = lambda value: (
        (bbox.x0 + (value - low) / (high - low) * (bbox.x1 - bbox.x0))
        if horizontal
        else (bbox.y1 - (value - low) / (high - low) * (bbox.y1 - bbox.y0))
    )
    if kind == "hist_kde":
        curves = [p["kde"] for p in profiles]
        maximum = max(max(p["ys"]) for p in profiles + curves) or 1
        return render_marginal(
            profiles, bbox, scale, context, kind="hist", axis=axis, maximum=maximum
        ) + render_marginal(curves, bbox, scale, context, kind="kde", axis=axis, maximum=maximum).replace(
            'data-density-unit="shared-transform-domain"', 'data-density-unit="expected-count-per-bin"'
        )
    maximum = maximum or max((max(profile.get("ys", [0])) for profile in profiles), default=0) or 1
    parts = []
    profile_names = {profile["name"] for profile in profiles}
    group_order = [name for name in dict.fromkeys(context.order + context.ids) if name in profile_names]
    for index, profile in enumerate(profiles):
        color = context.color_of(profile["name"])
        attrs = f'data-series={quoteattr(profile["name"])} data-n="{profile["n"]}" data-axis="{axis}" data-transform="{scale.transform}"'
        if kind == "hist":
            for i, count in enumerate(profile["ys"]):
                if not count:
                    continue
                a, b = along(profile["xs"][i]), along(profile["xs"][i + 1])
                # Every group keeps one explicit sublane within the SAME bin.
                # Counts and the common count-height scale are unchanged.
                slot = abs(b - a) / len(group_order)
                lane = group_order.index(profile["name"])
                inset = slot * 0.10
                lane_start = min(a, b) + lane * slot + inset
                lane_span = slot - 2 * inset
                stroke_width = min(0.7, slot * 0.12)
                if horizontal:
                    x, y = lane_start, bbox.y1 - count / maximum * (bbox.y1 - bbox.y0)
                    width, height = lane_span, bbox.y1 - y
                else:
                    x, y = bbox.x0, lane_start
                    width, height = count / maximum * (bbox.x1 - bbox.x0), lane_span
                parts.append(
                    f'<rect x="{x:.4f}" y="{y:.4f}" width="{width:.4f}" height="{height:.4f}" fill={quoteattr(color)} fill-opacity=".38" stroke={quoteattr(color)} stroke-width="{stroke_width:.4f}" data-role="marginal-count" data-count="{count}" data-bin="{i}" data-bin-min="{inverse(profile["xs"][i], scale):.17g}" data-bin-max="{inverse(profile["xs"][i + 1], scale):.17g}" data-group-lane="{lane}" {attrs}/>'
                )
        elif kind == "kde":
            path = [
                (along(x), bbox.y1 - y / maximum * (bbox.y1 - bbox.y0))
                if horizontal
                else (bbox.x0 + y / maximum * (bbox.x1 - bbox.x0), along(x))
                for x, y in zip(profile["xs"], profile["ys"])
            ]
            polygon = (
                ([(bbox.x0, bbox.y1)] + path + [(bbox.x1, bbox.y1)])
                if horizontal
                else ([(bbox.x0, bbox.y1)] + path + [(bbox.x0, bbox.y0)])
            )
            parts.append(
                f'<path d="{_path(polygon)} Z" fill={quoteattr(color)} fill-opacity=".09" stroke="none" data-role="marginal-density-fill" {attrs}/>'
            )
            parts.append(
                f'<path d="{_path(path)}" fill="none" stroke={quoteattr(color)} stroke-width="1.6" data-role="marginal-density" data-density-unit="shared-transform-domain" {attrs}/>'
            )
        else:
            stats = profile["stats"]
            across = (
                bbox.y0 + (index + 0.5) * (bbox.y1 - bbox.y0) / len(profiles)
                if horizontal
                else bbox.x0 + (index + 0.5) * (bbox.x1 - bbox.x0) / len(profiles)
            )
            half = min(10, ((bbox.y1 - bbox.y0) if horizontal else (bbox.x1 - bbox.x0)) / len(profiles) * 0.27)
            coords = {key: along(value) for key, value in stats.items()}
            if horizontal:
                whiskers = f"M{coords['lo']:.4f},{across:.4f} H{coords['hi']:.4f} M{coords['lo']:.4f},{across - half:.4f} v{2 * half:.4f} M{coords['hi']:.4f},{across - half:.4f} v{2 * half:.4f}"
                box = (
                    f"M{coords['q1']:.4f},{across - half:.4f} H{coords['q3']:.4f} v{2 * half:.4f} H{coords['q1']:.4f} Z"
                )
                median = f"M{coords['median']:.4f},{across - half:.4f} v{2 * half:.4f}"
            else:
                whiskers = f"M{across:.4f},{coords['lo']:.4f} V{coords['hi']:.4f} M{across - half:.4f},{coords['lo']:.4f} h{2 * half:.4f} M{across - half:.4f},{coords['hi']:.4f} h{2 * half:.4f}"
                box = f"M{across - half:.4f},{coords['q3']:.4f} h{2 * half:.4f} V{coords['q1']:.4f} h{-2 * half:.4f} Z"
                median = f"M{across - half:.4f},{coords['median']:.4f} h{2 * half:.4f}"
            parts.append(
                f'<path d="{whiskers}" fill="none" stroke={quoteattr(color)} stroke-width="1.1" data-role="marginal-whisker" {attrs}/>'
            )
            parts.append(
                f'<path d="{box}" fill={quoteattr(color)} fill-opacity=".22" stroke={quoteattr(color)} stroke-width="1.2" data-role="marginal-box" {attrs}/>'
            )
            parts.append(
                f'<path d="{median}" fill="none" stroke={quoteattr(color)} stroke-width="2" data-role="marginal-median" data-value="{inverse(stats["median"], scale):.17g}" {attrs}/>'
            )
            for value in profile["outliers"]:
                x, y = (along(value), across) if horizontal else (across, along(value))
                parts.append(
                    f'<circle cx="{x:.4f}" cy="{y:.4f}" r="2" fill="none" stroke={quoteattr(color)} data-role="marginal-outlier" {attrs}/>'
                )
    return "".join(parts)


def covariance_ellipse(points, x_scale, y_scale, probability=0.95):
    """Sample-covariance ellipse with chi-square(2) normal-reference coverage."""
    if isinstance(probability, bool) or not isinstance(probability, (float, int)) or not 0 < probability < 1:
        raise ValueError("ellipse must be a probability strictly between 0 and 1, or None")
    if len(points) < 3:
        raise ValueError("covariance ellipses require at least three observations per group")
    ax, bx = transform_domain(x_scale)
    ay, by = transform_domain(y_scale)
    xs = [(transformed(p["x"], x_scale) - ax) / (bx - ax) for p in points]
    ys = [(transformed(p["y"], y_scale) - ay) / (by - ay) for p in points]
    mx, my = math.fsum(xs) / len(xs), math.fsum(ys) / len(ys)
    dx, dy = [x - mx for x in xs], [y - my for y in ys]
    xx = math.fsum(x * x for x in dx) / (len(points) - 1)
    yy = math.fsum(y * y for y in dy) / (len(points) - 1)
    xy = math.fsum(x * y for x, y in zip(dx, dy)) / (len(points) - 1)
    delta = math.hypot(xx - yy, 2 * xy)
    major, minor = (xx + yy + delta) / 2, (xx + yy - delta) / 2
    if major <= 0 or minor <= major * 1e-14:
        raise ValueError("covariance ellipses require nonsingular two-dimensional observations")
    angle = 0.5 * math.atan2(2 * xy, xx - yy)
    radius = math.sqrt(-2 * math.log1p(-probability))
    c, s = math.cos(angle), math.sin(angle)
    result = []
    for i in range(129):
        theta = math.tau * i / 128
        u, v = radius * math.sqrt(major) * math.cos(theta), radius * math.sqrt(minor) * math.sin(theta)
        result.append(
            {
                "x": inverse(ax + (bx - ax) * (mx + c * u - s * v), x_scale),
                "y": inverse(ay + (by - ay) * (my + s * u + c * v), y_scale),
            }
        )
    return result


def kde2d(points, x_scale, y_scale, *, grid_size=45):
    """Product Gaussian KDE on the unit transform domain, using Silverman widths."""
    if not points:
        raise ValueError("two-dimensional KDE requires observations")
    ax, bx = transform_domain(x_scale)
    ay, by = transform_domain(y_scale)
    xs = [(transformed(p["x"], x_scale) - ax) / (bx - ax) for p in points]
    ys = [(transformed(p["y"], y_scale) - ay) / (by - ay) for p in points]
    hx, hy = bandwidth_for(xs, span=1), bandwidth_for(ys, span=1)

    def support_grid(values, bandwidth):
        low, high = max(0.0, min(values) - 5 * bandwidth), min(1.0, max(values) + 5 * bandwidth)
        return [low + (high - low) * i / (grid_size - 1) for i in range(grid_size)]

    grid_x, grid_y = support_grid(xs, hx), support_grid(ys, hy)
    xweights = [[math.exp(-0.5 * ((x - value) / hx) ** 2) for value in xs] for x in grid_x]
    yweights = [[math.exp(-0.5 * ((y - value) / hy) ** 2) for value in ys] for y in grid_y]
    norm = 1 / (len(points) * 2 * math.pi * hx * hy)
    density = [
        [math.fsum(a * b for a, b in zip(xweights[i], yweights[j])) * norm for i in range(grid_size)]
        for j in range(grid_size)
    ]
    return grid_x, grid_y, density


def contour_segments(grid_x, grid_y, density, level):
    """Marching-squares isoline; ambiguous cells use their bilinear center."""
    result = []
    for j in range(len(grid_y) - 1):
        for i in range(len(grid_x) - 1):
            vertices = [
                (grid_x[i], grid_y[j]),
                (grid_x[i + 1], grid_y[j]),
                (grid_x[i + 1], grid_y[j + 1]),
                (grid_x[i], grid_y[j + 1]),
            ]
            values = [density[j][i], density[j][i + 1], density[j + 1][i + 1], density[j + 1][i]]
            crosses = []
            for edge, (a, b) in enumerate(((0, 1), (1, 2), (2, 3), (3, 0))):
                if (values[a] >= level) != (values[b] >= level):
                    fraction = (level - values[a]) / (values[b] - values[a])
                    crosses.append(
                        (
                            edge,
                            (
                                vertices[a][0] + fraction * (vertices[b][0] - vertices[a][0]),
                                vertices[a][1] + fraction * (vertices[b][1] - vertices[a][1]),
                            ),
                        )
                    )
            if len(crosses) == 2:
                result.append((crosses[0][1], crosses[1][1]))
            elif len(crosses) == 4:
                same = (math.fsum(values) / 4 >= level) == (values[0] >= level)
                pairs = ((0, 1), (2, 3)) if same else ((0, 3), (1, 2))
                result.extend((crosses[a][1], crosses[b][1]) for a, b in pairs)
    return result


def render_contours(series, bbox, x_scale, y_scale, context, *, levels=(0.2, 0.5, 0.8)):
    levels = tuple(levels)
    if not levels or any(
        isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 < value < 1 for value in levels
    ):
        raise ValueError("contour_levels must be nonempty fractions strictly between 0 and 1")
    parts = []
    for item in series:
        if not item["points"]:
            continue
        grid_x, grid_y, density = kde2d(item["points"], x_scale, y_scale)
        peak = max(max(row) for row in density)
        for fraction in sorted(set(levels)):
            segments = contour_segments(grid_x, grid_y, density, peak * fraction)
            pixels = [
                [(bbox.x0 + x * (bbox.x1 - bbox.x0), bbox.y1 - y * (bbox.y1 - bbox.y0)) for x, y in segment]
                for segment in segments
            ]
            path = " ".join(_path(segment) for segment in pixels)
            parts.append(
                f'<path d="{path}" fill="none" stroke={quoteattr(context.color_of(item["name"]))} stroke-width="{0.7 + fraction:.3f}" stroke-opacity=".8" data-role="density-contour" data-series={quoteattr(item["name"])} data-level="{fraction:g}" data-level-unit="fraction-of-peak" data-n="{len(item["points"])}"/>'
            )
    return "".join(parts)


def legend(layout, names, context, top, *, numbered=False):
    """Wrap every complete group label into measured independent rows."""
    cursor = top
    fs = layout.font_sizes["legend"]
    swatch = fs * 0.8
    labels = [f"[{index + 1}] {name}" if numbered else name for index, name in enumerate(names)]
    widths = [swatch + 9 + layout.measure(label, fs) for label in labels]
    if sum(widths) + 24 * (len(widths) - 1) <= layout.width - 56:
        x = 28.0
        for name, label, item_w in zip(names, labels, widths):
            layout.parts.append(
                f'<rect x="{x:.3f}" y="{cursor + fs * 0.12:.3f}" width="{swatch:.3f}" height="{swatch:.3f}" fill={quoteattr(context.color_of(name))} data-role="legend-swatch" data-series={quoteattr(name)}/>'
            )
            layout.text(label, x + swatch + 9, cursor, fs=fs)
            x += item_w + 24
        return cursor + fs * 1.35 + 18
    text_x = 28 + swatch + 9
    for name, label in zip(names, labels):
        lines = wrap_lines(label, layout.width - text_x - 28, fs, layout.font)
        layout.parts.append(
            f'<rect x="28" y="{cursor + fs * 0.12:.3f}" width="{swatch:.3f}" height="{swatch:.3f}" fill={quoteattr(context.color_of(name))} data-role="legend-swatch" data-series={quoteattr(name)}/>'
        )
        cursor += layout.text("\n".join(lines), text_x, cursor, fs=fs) + 5
    return cursor + 13


def footer_height(layout, notes):
    fs = layout.font_sizes["foot"]
    return sum(len(wrap_lines(value, layout.width - 56, fs, layout.font)) * fs * 1.35 + 5 for value in notes if value)


def footer(layout, notes, top):
    for value in notes:
        if value:
            top += (
                layout.text(
                    value, 28, top, fs=layout.font_sizes["foot"], color=layout.pal["ink6"], width=layout.width - 56
                )
                + 5
            )


def axis_note(scale):
    return _axis_format(scale)[1]


def x_ticks(layout, bbox, scale, *, labels=True):
    """Axis for distribution-only panels, with exactly the shared XY formatter."""
    fmt, _ = _axis_format(scale)
    ticks = scale.ticks or []
    fs = layout.font_sizes["xtick"]
    max_width = max((layout.measure(fmt(v), fs) for v in ticks), default=0)
    step = max(1, math.ceil((max_width + fs) * max(0, len(ticks) - 1) / (bbox.x1 - bbox.x0)))
    for value in ticks[::step]:
        x = scale.map(value, bbox.x0, bbox.x1)
        layout.parts.append(f'<path d="M{x:.4f},{bbox.y1:.4f} v5" stroke={quoteattr(layout.pal["ink4"])}/>')
        if labels:
            layout.text(fmt(value), x, bbox.y1 + 9, fs=fs, anchor="middle")
