"""Ridge panels sharing numeric domains, group order and series colors."""

import math

from .._typography import chart_font_sizes
from ._distribution import (
    Canvas,
    _derive_series_colors,
    _resolve_palette,
    _rgba_with_alpha,
    _xesc,
    axis_ticks,
    draw_header,
    finite,
    header_height,
    kde,
    legend_layout,
    measure,
    normalize_groups,
    quantile,
    sample_domain,
    sample_stats,
    value_scale,
    wrap,
)

VARIANTS = ("default_flat", "outlined_separated", "gradient_overlap", "joy_division", "histogram_binned")


def render_ridge(
    distributions,
    group_labels=None,
    x_range=None,
    *,
    conditions=None,
    variant=None,
    title=None,
    subtitle=None,
    x_unit=None,
    x_labels=None,
    academic=False,
    highlight_index=None,
    multi_mode="single",
    width=900,
    height=None,
    palette=None,
    font_family=None,
):
    """Named rows contain samples."""
    if variant not in (None, "classic", *VARIANTS):
        raise ValueError(f"unknown ridge variant {variant!r}")
    if multi_mode not in (None, "auto", "single", "off", "with_condition_facets", "with_counts", "with_median_trend"):
        raise ValueError(f"unsupported ridge multi_mode {multi_mode!r}")
    if multi_mode == "with_condition_facets" and conditions is None:
        raise ValueError("with_condition_facets requires conditions")
    if x_range is not None and (len(x_range) != 2 or finite(x_range[1], "x_range") <= finite(x_range[0], "x_range")):
        raise ValueError("x_range must contain two increasing finite numbers")
    inputs = conditions if conditions is not None else [(None, distributions)]
    normalized = []
    all_sample_groups = []
    order = []
    series_order = []
    for facet_name, rows in inputs:
        if not rows:
            raise ValueError("ridge requires nonempty distributions")
        if group_labels is not None and len(group_labels) != len(rows):
            raise ValueError("group_labels length must match distribution rows")
        named = all(isinstance(row, (tuple, list)) and len(row) == 2 and isinstance(row[0], str) for row in rows)
        panel = []
        for i, row in enumerate(rows):
            if named:
                name = str(group_labels[i]) if group_labels is not None else str(row[0])
                payload = row[1]
                series = payload if isinstance(payload, dict) else {"": payload}
                row_series = []
                for label, values in series.items():
                    sample = normalize_groups([(name, values)])[0]
                    all_sample_groups.append(sample)
                    row_series.append((str(label), sample))
                    if str(label) not in series_order:
                        series_order.append(str(label))
                if not row_series:
                    raise ValueError("grouped ridge requires at least one series")
                panel.append((name, row_series, None))
            else:
                name = str(group_labels[i]) if group_labels is not None else f"Group {i + 1}"
                density = [finite(value, "density") for value in row]
                if len(density) < 2 or any(value < 0 for value in density) or max(density) <= 0:
                    raise ValueError("density rows need at least two nonnegative ordinates and a positive peak")
                panel.append((name, [], density))
        if group_labels is not None and len(group_labels) != len(panel):
            raise ValueError("group_labels length must match distribution rows")
        names = [row[0] for row in panel]
        if len(set(names)) != len(names):
            raise ValueError("ridge row names must be unique")
        if not order:
            order = names
        elif set(names) != set(order):
            raise ValueError("ridge facets must contain the same row names")
        panel.sort(key=lambda row: order.index(row[0]))
        normalized.append((str(facet_name) if facet_name is not None else None, panel))
    if not normalized:
        raise ValueError("ridge requires at least one panel")
    if all_sample_groups:
        domain = sample_domain(all_sample_groups, *(x_range or (None, None)), density=True)
    elif x_range is not None:
        domain = tuple(finite(value, "x_range") for value in x_range)
        if len(domain) != 2 or domain[1] <= domain[0]:
            raise ValueError("x_range must contain two increasing finite numbers")
    else:
        domain = (0, len(normalized[0][1][0][2]) - 1)
    if variant == "histogram_binned" and not all_sample_groups:
        raise ValueError("histogram_binned requires raw samples, not precomputed densities")
    if multi_mode == "with_median_trend" and not all_sample_groups:
        raise ValueError("with_median_trend requires raw samples")
    if multi_mode == "with_counts" and not all_sample_groups:
        raise ValueError("with_counts requires raw samples")
    if multi_mode == "auto":
        multi_mode = (
            "with_median_trend"
            if conditions is None
            and len(order) >= 5
            and all(len(series) == 1 and len(series[0][1].values) >= 5 for _, series, _ in normalized[0][1])
            else "single"
        )
    series_order.sort()
    grouped = len(series_order) > 1
    width = finite(900 if width is None else width, "width")
    cols = min(len(normalized), max(1, int(width // 470)))
    rows = math.ceil(len(normalized) / cols)
    gap = 34
    cell_w = (width - 64 - gap * (cols - 1)) / cols
    fonts = chart_font_sizes(cell_w, (height or width * 0.7) / rows, max(len(order), len(series_order)))
    fs, tick_fs, axis_fs = fonts["group"], fonts["xtick"], fonts["xaxis"]
    legend_fs, count_fs, facet_fs = fonts["legend"], fonts["group_n"], fonts["subtitle"]
    header_fonts = chart_font_sizes(width, height or width * 0.7, len(order))
    left = min(cell_w * 0.34, max(88, max(measure(label, fs) for label in order) + 28))
    label_lines = {label: wrap(label, left - 20, fs) for label in order}
    label_block = max(len(lines) for lines in label_lines.values()) * fs * 1.35 + (count_fs * 1.35 if academic else 0)
    row_step = max(58, label_block + 12)
    # Ridges overlap by design; a caller-fixed height may compress the pitch to the label block.
    min_row_step = label_block + 2
    if variant == "joy_division" and palette is None:
        palette = "nightlab"
    resolved_palette = _resolve_palette(palette)
    colors = _derive_series_colors(resolved_palette, len(series_order) if grouped else len(order), mode="distinct")
    dash_patterns = ("", "4 3", "1 2", "6 2 1 2", "6 2 1 2 1 2", "2 2 6 2", "7 2 3 2", "3 2 1 2")
    series_styles = {}
    for index, label in enumerate(series_order):
        pattern = dash_patterns[index] if index < len(dash_patterns) else f"{10 + index} 3 1 3"
        series_styles[label] = (
            resolved_palette["ink"] if variant == "joy_division" else colors[index],
            f'stroke-dasharray="{pattern}"' if pattern else "",
        )
    legend_items = (
        [
            (
                label,
                series_styles[label][0],
                series_styles[label][1] + f' data-role="series-legend" data-series="{_xesc(label)}"',
            )
            for label in series_order
        ]
        if grouped
        else []
    )
    legend_rows, legend_h = legend_layout(legend_items, width, legend_fs)
    if x_labels is not None and len(x_labels) < 2:
        raise ValueError("x_labels requires at least two labels")
    tick_values, tick_labels, offset_label = axis_ticks(domain, len(x_labels) if x_labels else 5)
    if x_labels is not None:
        if len(x_labels) < 2:
            raise ValueError("x_labels requires at least two labels")
        tick_labels = [str(label) for label in x_labels]
    count_w = (
        max(108, measure("Total sample" if grouped else "Sample count", count_fs) + 24)
        if multi_mode == "with_counts"
        else 0
    )
    right_margin = max(12, max(measure(label, tick_fs) for label in tick_labels) / 2 + 4)
    plot_width = cell_w - left - right_margin - count_w
    if plot_width < 100:
        raise ValueError("ridge panel too narrow; increase width")
    axis_lines = wrap(x_unit, plot_width, axis_fs) if x_unit else []
    tick_lines = [
        wrap(label, max(32, plot_width / max(1, len(tick_labels) - 1) * 0.9), tick_fs) for label in tick_labels
    ]
    axis_h = max(len(lines) for lines in tick_lines) * tick_fs * 1.35 + len(axis_lines) * axis_fs * 1.35 + 24
    top = header_height(width, title, subtitle, fonts=header_fonts) + legend_h + 16
    trend_row_h = max(36, max(len(lines) for lines in label_lines.values()) * fs * 1.35 + 12)
    trend_h = facet_fs * 1.35 + 26 + len(order) * trend_row_h + axis_h if multi_mode == "with_median_trend" else 0
    facet_header = max(
        [len(wrap(name, cell_w, facet_fs)) * facet_fs * 1.35 + 15 for name, _ in normalized if name] or [36]
    )
    facet_header += count_fs * 1.35 + 8 if offset_label else 0
    if count_w:
        facet_header = max(facet_header, count_fs * 3.7)
    cell_min = facet_header + len(order) * row_step + axis_h + trend_h
    min_height = top + rows * cell_min + (rows - 1) * gap + 20
    if height is not None:
        trend_row_h = max(len(lines) for lines in label_lines.values()) * fs * 1.35 + 2
        trend_h = facet_fs * 1.35 + 26 + len(order) * trend_row_h + axis_h if trend_h else 0
        cell_min = facet_header + len(order) * min_row_step + axis_h + trend_h
        min_height = top + rows * cell_min + (rows - 1) * gap + 20
    height = min_height if height is None else finite(height, "height")
    if height < min_height:
        raise ValueError(f"ridge height must be at least {math.ceil(min_height)}")
    cell_h = (height - top - 20 - (rows - 1) * gap) / rows
    if variant == "joy_division" and palette is None:
        palette = "nightlab"
    c = Canvas(width, height, palette, font_family)
    draw_header(c, title, subtitle, fonts=header_fonts)
    colors = _derive_series_colors(c.pal, len(series_order) if grouped else len(order), mode="distinct")
    for x, y, lines, color, extra in legend_rows:
        c.line(x, top - legend_h + y - 6, x + 18, top - legend_h + y - 6, color, 2, extra)
        c.lines(x + 24, top - legend_h + y - 2, lines, legend_fs, color=c.muted)
    # Compute densities once; this also provides a common density-height scale.
    curves = {}
    for f, (_, panel) in enumerate(normalized):
        for i, (_, series, density) in enumerate(panel):
            if density is not None:
                xs = [domain[0] + (domain[1] - domain[0]) * j / (len(density) - 1) for j in range(len(density))]
                curves[f, i, 0] = (xs, density)
            else:
                for j, (_, sample) in enumerate(series):
                    if variant == "histogram_binned":
                        bins = max(8, min(28, int(math.sqrt(len(sample.values)))))
                        step = (domain[1] - domain[0]) / bins
                        counts = [0] * bins
                        for value in sample.values:
                            counts[min(bins - 1, int((value - domain[0]) / (domain[1] - domain[0]) * bins))] += 1
                        xs = [domain[0] + k * step for k in range(bins + 1)]
                        ys = [count * bins / len(sample.values) for count in counts]
                        curves[f, i, j] = (xs, ys)
                    else:
                        curves[f, i, j] = kde(sample.values, domain)
    peak = max(max(curve[1]) for curve in curves.values())
    max_n = max(
        (sum(len(sample.values) for _, sample in series) for _, panel in normalized for _, series, _ in panel),
        default=1,
    )
    for f, (name, panel) in enumerate(normalized):
        cx = 32 + (f % cols) * (cell_w + gap)
        cy = top + (f // cols) * (cell_h + gap)
        if name:
            c.lines(cx, cy + facet_fs, wrap(name, cell_w, facet_fs), facet_fs, weight=600)
        pl = cx + left
        pr = cx + cell_w - right_margin - count_w
        if pr - pl < 100:
            raise ValueError("ridge panel too narrow; increase width")
        pt = cy + facet_header
        pb = cy + cell_h - axis_h - trend_h
        step = (pb - pt) / len(order)
        scale = value_scale(domain, pl, pr)
        if offset_label:
            c.text(pl, pt - 9, offset_label, count_fs, color=c.muted)
        for value, lines in zip(tick_values, tick_lines):
            x = scale(value)
            c.line(x, pt, x, pb, c.grid, 0.7)
            c.lines(x, pb + tick_fs + 10, lines, tick_fs, "middle", c.muted)
        if axis_lines:
            c.lines(
                (pl + pr) / 2,
                pb + 10 + max(len(lines) for lines in tick_lines) * tick_fs * 1.35 + axis_fs,
                axis_lines,
                axis_fs,
                "middle",
                c.muted,
            )
        if count_w:
            count_title = "Total sample count" if grouped else "Sample count"
            count_lines = wrap(count_title, count_w - 20, count_fs)
            c.lines(
                pr + count_w / 2 + 8,
                pt - 12 - (len(count_lines) - 1) * count_fs * 1.35,
                count_lines,
                count_fs,
                "middle",
                c.muted,
            )
        medians = []
        for i, (label, series, density) in enumerate(panel):
            base = pt + (i + 0.92) * step
            lines = label_lines[label]
            block_h = len(lines) * fs * 1.35 + (count_fs * 1.35 if academic and series else 0)
            label_y = pt + (i + 0.5) * step - block_h / 2 + fs
            c.lines(pl - 14, label_y, lines, fs, "end", weight=600 if i == highlight_index else 400)
            if academic and series:
                c.text(
                    pl - 14,
                    label_y + len(lines) * fs * 1.35,
                    f"n = {sum(len(s.values) for _, s in series)}",
                    count_fs,
                    "end",
                    c.muted,
                )
            c.line(pl, base, pr, base, c.grid, 0.8)
            for j in range(len(series) or 1):
                series_name = series[j][0] if series else ""
                color, dash = (
                    series_styles[series_name] if grouped else (c.ink if variant == "joy_division" else colors[i], "")
                )
                xs, ys = curves[f, i, j]
                amplitude = step * 0.77
                if variant == "histogram_binned":
                    points = [(scale(xs[0]), base)]
                    for k, value in enumerate(ys):
                        points.extend(
                            (
                                (scale(xs[k]), base - value / peak * amplitude),
                                (scale(xs[k + 1]), base - value / peak * amplitude),
                            )
                        )
                    points.append((scale(xs[-1]), base))
                else:
                    points = (
                        [(pl, base)] + [(scale(x), base - y / peak * amplitude) for x, y in zip(xs, ys)] + [(pr, base)]
                    )
                fill = (
                    "none"
                    if variant in ("outlined_separated", "joy_division")
                    else _rgba_with_alpha(color, 0.18 if grouped else 0.27)
                )
                if variant == "gradient_overlap":
                    gradient_id = f"ridge-gradient-{f}-{i}-{j}"
                    c.parts.append(
                        f'<defs><linearGradient id="{gradient_id}" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="{color}" stop-opacity="0.60"/><stop offset="100%" stop-color="{color}" stop-opacity="0.08"/></linearGradient></defs>'
                    )
                    fill = f"url(#{gradient_id})"
                c.path(
                    points,
                    color,
                    fill,
                    2 if i == highlight_index else 1.5,
                    True,
                    f'{dash} data-role="ridge-density" data-input-kind="{"samples" if series else "density"}" data-group="{_xesc(label)}" data-series="{_xesc(series_name)}"',
                )
                if academic and series:
                    median = quantile(series[j][1].values, 0.5)
                    c.line(scale(median), base, scale(median), base - 10, color, 2)
            if series:
                samples = [v for _, sample in series for v in sample.values]
                medians.append(sample_stats(samples))
                if count_w:
                    count = len(samples)
                    c.line(
                        pr + 20,
                        base - 15,
                        pr + 20 + (count_w - 54) * count / max_n,
                        base - 15,
                        c.muted if grouped else colors[i % len(colors)],
                        8,
                        f'data-role="sample-count" data-count="{count}"',
                    )
                    c.text(pr + count_w - 5, base - 11, str(count), count_fs, "end", c.muted)
        if trend_h:
            trend_title_y = pb + axis_h + facet_fs
            c.text(
                pl,
                trend_title_y,
                "Group median and IQR" if not grouped else "Pooled group median and IQR",
                facet_fs,
                weight=600,
            )
            trend_top = trend_title_y + 16
            trend_bottom = trend_top + len(order) * trend_row_h
            for value, lines in zip(tick_values, tick_lines):
                x = scale(value)
                c.line(x, trend_top, x, trend_bottom, c.grid, 0.7)
                c.lines(x, trend_bottom + tick_fs + 10, lines, tick_fs, "middle", c.muted)
            points = []
            for i, (label, stats) in enumerate(zip(order, medians)):
                cy_trend = trend_top + (i + 0.5) * trend_row_h
                lines = label_lines[label]
                c.lines(pl - 14, cy_trend - (len(lines) - 1) * fs * 0.675 + fs * 0.33, lines, fs, "end")
                color = c.ink if grouped else colors[i]
                c.line(scale(stats["q1"]), cy_trend, scale(stats["q3"]), cy_trend, color, 2.4)
                points.append((scale(stats["median"]), cy_trend))
                c.circle(
                    scale(stats["median"]),
                    cy_trend,
                    3.2,
                    color,
                    f'data-role="ridge-median" data-group="{_xesc(label)}" data-value="{stats["median"]:.17g}"',
                )
            c.path(points, c.muted, stroke=1)
            if axis_lines:
                c.lines(
                    (pl + pr) / 2,
                    trend_bottom + 10 + max(len(lines) for lines in tick_lines) * tick_fs * 1.35 + axis_fs,
                    axis_lines,
                    axis_fs,
                    "middle",
                    c.muted,
                )
    return c.svg()
