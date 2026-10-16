"""Data-preserving view selection for the public grouped_bar entry point."""

from __future__ import annotations

import math
from xml.sax.saxutils import quoteattr

from .._common import _estimate_label_width_px, _ink_on_bg, _pick_series_colors, _punchy_title_ink, _resolve_palette
from ._academic_rigor import BBox
from ._categorical import (
    _pairwise,
    draw_reference_line,
    interval_kind_label,
    interval_note_text,
    normalize_records,
    normalize_reference_lines,
)
from ._chart_layout import ChartLayout, finite, p_label, precise_number, readable_annotation_color, wrap_lines
from ._composition import numeric_axis, scale_from
from ._shared import tr

MODES = {
    "auto",
    "single",
    "off",
    None,
    "bars",
    "heatmap",
    "intervals",
    "boxplot",
    "raincloud",
    "marimekko",
    "composition",
    "with_facet_by_series",
}


def _negative(value, location):
    number = finite(value, location)
    if number < 0:
        raise ValueError(
            f"grouped_bar 不支持负值 (negative value)：{location} = {number:g}。"
            "请改用支持正负数轴的原生柱状图或原生折线图，保留原值、区间和零线；"
            "不要取绝对值、截为零或平移数据。"
        )


_SERIES_EXAMPLE = (
    "series=[{'name': '组A', 'values': [{'value': 32}, {'value': 2}, None]}]（每个类别一格；"
    "格子写 {'value': v} 汇总值、{'value': v, 'lo': a, 'hi': b} 区间或 [重复观测…]，也可直接写数字 32）"
)


def _unwrap(cells):
    """[[c1, c2, c3]] written for three categories is one extra list level, not a single replicate cell."""
    if (
        isinstance(cells, (list, tuple))
        and len(cells) == 1
        and isinstance(cells[0], (list, tuple))
        and len(cells[0]) > 1
        and all(isinstance(c, dict) for c in cells[0])
    ):
        return list(cells[0])
    return cells


def coerce_series(series):
    """Accept the shapes callers commonly write for reported summaries and return the canonical form."""

    def cell(c):
        if isinstance(c, bool):
            raise TypeError(f"grouped_bar 的格子不能是布尔值：{_SERIES_EXAMPLE}")
        if isinstance(c, (int, float)):
            return {"value": c}
        if isinstance(c, (list, tuple)) and len(c) == 1 and isinstance(c[0], dict):
            return dict(c[0])
        if isinstance(c, (list, tuple)) and any(isinstance(v, dict) for v in c):
            raise TypeError(f"grouped_bar 的一个格子里只能放一个汇总 dict 或一组数字，收到 {c!r}：{_SERIES_EXAMPLE}")
        return c

    out = []
    for raw in series:
        if isinstance(raw, dict):
            if "values" not in raw and "data" in raw:
                raw = {**{k: v for k, v in raw.items() if k != "data"}, "values": raw["data"]}
            if "name" not in raw or "values" not in raw:
                raise TypeError(
                    f"grouped_bar 的 series 项需要 'name' 和 'values'，收到键 {sorted(raw)}：{_SERIES_EXAMPLE}"
                )
            out.append({**raw, "values": [cell(c) for c in _unwrap(raw["values"])]})
        elif isinstance(raw, (list, tuple)) and len(raw) == 2 and isinstance(raw[1], (list, tuple)):
            out.append((raw[0], [cell(c) for c in _unwrap(raw[1])]))
        else:
            raise TypeError(f"grouped_bar 的 series 项格式不对：{raw!r}：{_SERIES_EXAMPLE}")
    return out


def validate_nonnegative(categories, series, *, line_series=None, value_domain=None, error_kind="SEM"):
    """Check observations before reducing them; do not hide a negative in a mean."""
    for raw in series:
        name, cells = (raw["name"], raw["values"]) if isinstance(raw, dict) else raw
        for ci, cell in enumerate(cells):
            where = f"series={name!r}, category={categories[ci] if ci < len(categories) else ci!r}"
            if cell is None:
                continue
            if isinstance(cell, dict):
                for key in ("value", "mean", "lo", "hi"):
                    if key in cell:
                        _negative(cell[key], where + ", " + key)
                samples = cell.get("replicates", [])
            else:
                if not isinstance(cell, (tuple, list)):
                    raise TypeError(
                        f"each grouped_bar cell must be a summary dictionary, replicate list, or None：{_SERIES_EXAMPLE}"
                    )
                samples = cell
            for i, value in enumerate(samples):
                _negative(value, where + f", observation[{i}]")
    for line in line_series or []:
        for i, value in enumerate(line["values"]):
            if value is not None:
                _negative(value, f"line={line['name']!r}, value[{i}]")
    if value_domain is not None:
        if len(value_domain) != 2:
            raise ValueError("value_domain must contain exactly two bounds")
        for i, value in enumerate(value_domain):
            _negative(value, f"value_domain[{i}]")
    return normalize_records(categories, series, error_kind)


def _svg_attrs(**values):
    return " ".join(
        f"{key.replace('_', '-')}={quoteattr(str(value))}" for key, value in values.items() if value is not None
    )


def _mark(svg, mode, records):
    # Semantics remain inspectable across renderers without adding visible text.
    rows = [
        f"""<g {
            _svg_attrs(
                data_role="grouped-cell",
                data_category=r["category"],
                data_series=r["name"],
                data_value=r["value"],
                data_low=r.get("lo"),
                data_high=r.get("hi"),
                data_n=r.get("n"),
            )
        }/>"""
        for r in records
    ]
    marker = f"<g {_svg_attrs(data_role='grouped-view', data_mode=mode)}>{''.join(rows)}</g>"
    return svg.replace("</svg>", marker + "</svg>")


def _joined(*lines):
    return "\n".join(str(line) for line in lines if line)


def _number(value, decimals=None):
    if decimals is not None:
        label = f"{value:.{decimals}f}".rstrip("0").rstrip(".")
        if value and float(label) == 0:
            return f"{value:.3g}"
        return label
    if float(value).is_integer() and abs(value) < 1e12:
        return str(int(value))
    return precise_number(value)


def _derived_number(value):
    """Computed means and SD/SEM/CI bounds: three significant digits, not float noise."""
    if float(value).is_integer() and abs(value) < 1e12:
        return str(int(value))
    return f"{value:.3g}"


def _palette(names, palette, highlight):
    pal = _resolve_palette(palette or "archive_ink")
    colors = _pick_series_colors(pal, len(names))
    if highlight is not None:
        if highlight not in names:
            raise ValueError("highlight_series must identify an existing series")
        colors[names.index(highlight)] = pal["accent"]
    # Every view receives the same explicit series identities and colors.
    return dict(pal, series=colors), dict(zip(names, colors))


def _legend(layout, names, colors, top, after=24):
    fs, x, row_h = layout.font_sizes["legend"], 28.0, 0.0
    for name in names:
        limit = layout.width - 92
        lines = wrap_lines(name, limit, fs, layout.font)
        w = max(layout.measure(line, fs) for line in lines) + 52
        if x > 28 and x + w > layout.width - 28:
            top += row_h + 12
            x, row_h = 28.0, 0.0
        layout.parts.append(f"<rect {_svg_attrs(x=x, y=top + 4, width=15, height=15, fill=colors[name])}/>")
        h = layout.text(name, x + 24, top, fs=fs, width=limit)
        row_h = max(row_h, h)
        x += w
    return top + row_h + after


def _footer(layout, top, note, source, compact=False):
    for line in (note, source):
        if line:
            top += layout.text(
                line,
                28,
                top,
                fs=layout.font_sizes["foot"] if compact else max(15, layout.font_sizes["foot"]),
                color=layout.pal["ink6"],
                width=layout.width - 56,
            ) + (4 if compact else 10)
    layout.height = max(layout.height, top + (8 if compact else 24))


def _intervals(categories, names, records, comparisons, options, pal, colors):
    """Aligned interval figure with observation rows and explicit numeric columns."""
    svg, layout = _intervals_at(categories, names, records, comparisons, options, pal, colors, None)
    W, H = finite(options["width"], "width"), finite(options["height"], "height")
    if layout.width <= W + 1 and layout.height <= H + 1:
        return svg
    base = ChartLayout(
        max(300, W), max(260, H), pal, options["font_family"], n_items=max(len(categories), len(names))
    ).font_sizes["label"]
    fs = base
    # A caller-sized canvas: compact rows first, then smaller (still >= 10) text.
    while True:
        svg, layout = _intervals_at(categories, names, records, comparisons, options, pal, colors, fs)
        if (layout.width <= W + 1 and layout.height <= H + 1) or fs <= 11:
            return svg
        fs = max(11, fs * 0.93)


def _intervals_at(categories, names, records, comparisons, options, pal, colors, compact_fs):
    compact = compact_fs is not None
    W = finite(options["width"], "width")
    layout = ChartLayout(
        max(300 if compact else 900, W),
        options["height"],
        pal,
        options["font_family"],
        n_items=max(len(categories), len(names)),
    )
    if compact:
        fs = compact_fs
        small = max(10.0, fs * 0.8)
        layout.font_sizes.update(
            title=max(fs * 1.25, 14.0),
            subtitle=max(small, 10.0),
            figure=max(small, 10.0),
            xtick=small,
            legend=max(10.0, fs * 0.9),
            foot=max(10.0, small * 0.9),
        )
    else:
        fs = max(19.0, layout.font_sizes["label"])
        small = max(16.0, fs * 0.8)
        layout.font_sizes.update(xtick=small, legend=max(18, fs * 0.9), foot=max(15, fs * 0.68))
    top = layout.header(
        options["title"], options["subtitle"], options["figure_label"], margin=16 if compact else 28
    ) - (10 if compact else 0)
    # One series: its name is said once (legend); rows are the categories themselves,
    # so the series name is never repeated on every row.
    single = len(names) == 1
    top = _legend(layout, names, colors, top, 10 if compact else 24)
    unit = options["y_unit"]
    from ._chart_layout import axis_caption

    caption = axis_caption(options["y_title"] or (None if unit else tr("Value")), unit, options["title"]) or tr("Value")
    ci_level = options.get("ci_level")
    note = interval_note_text(records, options["error_kind"], ci_level)
    if note:
        top += layout.text(note, 28, top, fs=small, color=layout.pal["ink6"], width=layout.width - 56) + (
            4 if compact else 12
        )
    if options["x_title"] and not single:
        top += layout.text(options["x_title"], 28, top, fs=small, width=layout.width - 56) + 10
    row_header = (options["x_title"] or tr("Category")) if single else tr("Series")
    kinds = sorted(
        {
            interval_kind_label(r.get("interval_kind", options["error_kind"]), r.get("ci_level", ci_level))
            for r in records
            if "lo" in r
        }
    )
    value_header = " / ".join(
        [tr("Value")]
        + ([kinds[0] if len(kinds) == 1 else tr("Interval")] if kinds else [])
        + (["n"] if any("n" in r for r in records) else [])
    )
    row_names = list(categories) if single else names
    number_text = {}
    for r in records:
        num = _derived_number if r.get("interval_kind") not in (None, "supplied lo/hi") else _number
        main = num(r["value"])
        interval = f"[{num(r['lo'])}, {num(r['hi'])}]" if "lo" in r else ""
        count = f"n={r['n']}" if "n" in r else ""
        number_text[id(r)] = main, " · ".join(v for v in (interval, count) if v)
    if compact:
        number_width = (
            max(
                layout.measure(main, fs, bold=True) + 6 + (layout.measure(extra, small) if extra else 0)
                for main, extra in number_text.values()
            )
            + 12
        )
        name_width = min(
            layout.width * 0.28,
            max([layout.measure(name, fs, bold=single) for name in row_names] + [layout.measure(row_header, small) + 8])
            + 22,
        )
        left = 28 + name_width + 12
        right = max(left + 110, layout.width - number_width - 34)
        layout.width = max(layout.width, right + number_width + 34)
    else:
        number_width = max(220, max(layout.measure(line, small) for pair in number_text.values() for line in pair) + 26)
        name_width = min(270, max(150, max(layout.measure(name, fs, bold=single) for name in row_names) + 30))
        left = 28 + name_width + 26
        right = max(left + 270, layout.width - number_width - 48)
        layout.width = max(layout.width, right + number_width + 48)
    layout.text(row_header, 48, top, fs=small, color=layout.pal["ink6"], width=name_width - 20)
    layout.text(caption, left, top, fs=small, width=right - left)
    layout.text(value_header, layout.width - 28, top, fs=small, anchor="end", color=layout.pal["ink6"])
    top += small * 1.5 + (6 if compact else 14)
    values = [r["value"] for r in records]
    values += [r[k] for r in records for k in ("lo", "hi") if k in r]
    if options["show_points"]:
        values += [v for r in records for v in r["replicates"]]
    refs = normalize_reference_lines(options.get("reference_lines"))
    values += [r["value"] for r in refs] if options["value_domain"] is None else []
    scale = scale_from(values, domain=options["value_domain"])
    if options["value_domain"] is None and scale.domain[0] < 0:
        scale = scale_from(values, domain=(0, scale.domain[1]))
    X = lambda value: scale.map(value, left, right)
    lookup = {(r["category"], r["name"]): r for r in records}
    start, body_start = top, len(layout.parts)
    show_values = options["show_values"] is not False
    for ci, category in enumerate(categories):
        if single:
            if ci % 2 == 0:
                band = (
                    max(
                        len(wrap_lines(category, name_width - 20, fs, layout.heading)) * fs * 1.35,
                        fs * 0.72 + 12
                        if options["show_points"] and lookup.get((category, names[0]), {}).get("replicates")
                        else 0,
                    )
                    + 4
                )
                band = band if compact else max(60, band + 10)
                layout.parts.append(
                    f"""<rect {
                        _svg_attrs(
                            x=28,
                            y=top - 2,
                            width=layout.width - 56,
                            height=band + 2,
                            fill=layout.pal["ink1"],
                            fill_opacity=0.3,
                        )
                    }/>"""
                )
        else:
            category_height = max(
                0 if compact else 38,
                len(wrap_lines(category, layout.width - 80, fs, layout.heading)) * fs * 1.35 + (4 if compact else 12),
            )
            layout.parts.append(
                f"""<rect {
                    _svg_attrs(
                        x=28,
                        y=top,
                        width=layout.width - 56,
                        height=category_height,
                        fill=layout.pal["ink1"],
                        fill_opacity=0.3,
                    )
                }/>"""
            )
            layout.text(category, 40, top + (2 if compact else 5), fs=fs, bold=True, width=layout.width - 80)
            top += category_height + (4 if compact else 8)
        for name in names:
            r = lookup.get((category, name))
            label = category if single else name
            label_lines = wrap_lines(label, name_width - 20, fs, layout.heading if single else layout.font)
            if compact:
                row_h = (
                    max(
                        len(label_lines) * fs * 1.35,
                        fs * 0.72 + 12 if options["show_points"] and r and r["replicates"] else 0,
                    )
                    + 4
                )
            else:
                row_h = max(60, len(label_lines) * fs * 1.35 + 14)
            y = top + fs * 0.72
            if single:
                layout.text(label, 48, top, fs=fs, bold=True, width=name_width - 20)
            else:
                layout.text(
                    label, 48, top, fs=fs, color=readable_annotation_color(colors[name], pal), width=name_width - 20
                )
            if r is None:
                layout.text("—", (left + right) / 2, top, fs=fs, anchor="middle")
                top += row_h
                continue
            common = dict(data_series=name, data_category=category)
            if "lo" in r:
                x0, x1 = X(r["lo"]), X(r["hi"])
                layout.parts.append(
                    f"""<path {
                        _svg_attrs(
                            d=f"M{x0},{y} H{x1} M{x0},{y - 6} V{y + 6} M{x1},{y - 6} V{y + 6}",
                            fill="none",
                            stroke=colors[name],
                            stroke_width=2,
                            data_role="grouped-interval",
                            data_low=r["lo"],
                            data_high=r["hi"],
                            data_interval_kind=r.get("interval_kind"),
                            **common,
                        )
                    }/>"""
                )
            layout.parts.append(
                f"""<circle {
                    _svg_attrs(
                        cx=X(r["value"]),
                        cy=y,
                        r=5.5,
                        fill=colors[name],
                        stroke=pal.get("bg") or "white",
                        stroke_width=1.1,
                        data_role="grouped-estimate",
                        data_value=r["value"],
                        **common,
                    )
                }/>"""
            )
            if options["show_points"]:
                for i, value in enumerate(r["replicates"]):
                    jitter = ((i * 0.61803398875) % 1 - 0.5) * (4 if compact else 10)
                    layout.parts.append(
                        f"""<circle {
                            _svg_attrs(
                                cx=X(value),
                                cy=y + (8 if compact else 20) + jitter,
                                r=2.6,
                                fill=colors[name],
                                fill_opacity=0.7,
                                data_role="replicate",
                                data_value=value,
                                **common,
                            )
                        }/>"""
                    )
            if show_values:
                main, extra = number_text[id(r)]
                if compact:
                    gap = layout.measure(extra, small) + 6 if extra else 0
                    layout.text(main, layout.width - 28 - gap, top, fs=fs, anchor="end", bold=True)
                    if extra:
                        layout.text(
                            extra,
                            layout.width - 28,
                            top + (fs - small) * 0.84,
                            fs=small,
                            anchor="end",
                            color=layout.pal["ink6"],
                        )
                    top += row_h
                    continue
                layout.text(main, layout.width - 28, top, fs=fs, anchor="end", bold=True)
                if extra:
                    layout.text(
                        extra, layout.width - 28, top + fs * 1.35, fs=small, anchor="end", color=layout.pal["ink6"]
                    )
            top += row_h
        top += (2 if compact else 6) if single else (4 if compact else 14)
    # Grid sits behind the observations and intervals.
    data_parts = layout.parts[body_start:]
    del layout.parts[body_start:]
    numeric_axis(layout, BBox(left, start, right, top), scale, orientation="x", grid=True)
    for ref in refs:
        draw_reference_line(layout, ref, X(ref["value"]), start, X(ref["value"]), top)
    layout.parts.extend(data_parts)
    top += small * 2.1 + (4 if compact else 16)
    for ref in [r for r in refs if r["label"]]:
        # Named under the axis at the line, like a direct label.
        w = layout.measure(ref["label"], small)
        cx = min(layout.width - 28 - w / 2, max(28 + w / 2, X(ref["value"])))
        layout.parts.append(
            f'<path d="M{cx - w / 2 - 22:.3f},{top + small * 0.55:.3f} h16" stroke={quoteattr(ref["color"] or layout.pal["ink6"])} '
            f'stroke-width="1.2" stroke-dasharray="5 4"/>'
            if cx - w / 2 - 22 >= 28
            else ""
        )
        top += layout.text(ref["label"], cx, top, fs=small, anchor="middle", color=layout.pal["ink6"]) + 6
    for a, b, p in comparisons:
        ra, rb = records[a], records[b]
        label = f"{ra['category']} / {ra['name']} ↔ {rb['category']} / {rb['name']} · " + p_label(p)
        layout.parts.append(f"<g {_svg_attrs(data_role='significance', data_p=p, data_a=a, data_b=b)}>")
        top += layout.text(label, 28, top, fs=small, width=layout.width - 56) + 10
        layout.parts.append("</g>")
    _footer(layout, top + 6, options["note"], options["source"], compact)
    return layout.svg("Grouped observations, point estimates and supplied or computed intervals"), layout


def summary_orientation(categories, width):
    """Cartesian bar orientation for few-value summaries."""
    slot = max(1.0, (float(width) - 160) / max(1, len(categories)))
    longest = max(_estimate_label_width_px(str(c), 16) for c in categories)
    return "horizontal" if len(categories) <= 8 or longest > slot * 0.9 else "vertical"


def _bars(categories, names, records, options, pal):
    from ._categorical import make_categorical

    lookup = {(r["category"], r["name"]): r for r in records}
    series = [
        (name, [None if (c, name) not in lookup else {"value": lookup[(c, name)]["value"]} for c in categories])
        for name in names
    ]
    orientation = summary_orientation(categories, options["width"])
    horizontal = orientation == "horizontal"
    return make_categorical(
        categories,
        series,
        orientation=orientation,
        summary_values=True,
        # One series needs no legend: the value heading already names it.
        single=len(names) == 1 and options["highlight_series"] is None,
        value_domain=options["value_domain"],
        y_unit=options["y_unit"],
        y_title=options["y_title"],
        x_title=None if horizontal else options["x_title"],
        note=_joined(options["x_title"], options["note"]) if horizontal else options["note"],
        title=options["title"],
        subtitle=options["subtitle"],
        figure_label=options["figure_label"],
        source=options["source"],
        show_points=False,
        show_values=options["show_values"],
        width=options["width"],
        height=options["height"],
        font_family=options["font_family"],
        palette=pal,
        highlight=options["highlight_series"],
        value_scale=options.get("value_scale", "auto"),
        reference_lines=options.get("reference_lines"),
    )


def _heatmap(categories, names, records, options, pal):
    from .matrix_heat import make_matrix_heat

    lookup = {(r["category"], r["name"]): r["value"] for r in records}
    matrix = [[lookup.get((c, n)) for n in names] for c in categories]
    values = [r["value"] for r in records]
    domain = options["value_domain"]
    if domain is not None:
        scale_from(values, domain=domain)
    elif min(values) == max(values):
        domain = (min(values), max(values))
    else:
        fitted = scale_from(values).domain
        domain = (max(0, fitted[0]), fitted[1])
    maximum = {c: max((r["value"] for r in records if r["category"] == c), default=None) for c in categories}
    labels = [
        [
            "—"
            if v is None
            else _number(v)
            if options["show_values"] is True or (options["show_values"] is None and (v == 0 or v == maximum[c]))
            else ""
            for v in row
        ]
        for c, row in zip(categories, matrix)
    ]
    row_labels, col_labels = list(categories), list(names)
    available_w = max(200, options["width"] - 320)
    available_h = max(200, options["height"] - 210)

    def aspect_cost(rows, cols):
        return abs(math.log(available_w * rows / (available_h * cols))) + max(0, cols - 20) * 0.07

    if aspect_cost(len(names), len(categories)) < aspect_cost(len(categories), len(names)):
        matrix = [list(row) for row in zip(*matrix)]
        labels = [list(row) for row in zip(*labels)]
        row_labels, col_labels = col_labels, row_labels
    width = max(options["width"], len(col_labels) * 68 + 340)
    height = max(options["height"], len(row_labels) * 84 + 210)
    legend_label = " ".join(v for v in (options["y_title"], options["y_unit"]) if v) or tr("Value")
    readout = tr("Circle area and color encode value.")
    if options["show_values"] is None:
        readout += " Labels mark each category's maximum and observed zeros."
    return make_matrix_heat(
        matrix,
        row_labels=row_labels,
        col_labels=col_labels,
        show_row_mean=False,
        show_col_mean=False,
        variant="circle_full",
        cell_label_position="below",
        size_matrix=matrix,
        size_max=domain[1],
        size_label=legend_label + " (area)",
        vmin=domain[0],
        vmax=domain[1],
        colormap="sequential",
        cell_text=labels,
        colorbar_label=" ".join(v for v in (options["y_title"], options["y_unit"]) if v) or tr("Value"),
        title=options["title"],
        subtitle=options["subtitle"],
        figure_label=options["figure_label"],
        note=_joined(readout, options["x_title"], options["note"]),
        source=options["source"],
        palette=pal,
        font_family=options["font_family"],
        width=width,
        height=height,
        multi_mode="single",
    )


def _distribution(categories, names, records, comparisons, mode, options, pal):
    from ._distribution import normalize_groups, render_distribution, sample_domain

    lookup = {(r["category"], r["name"]): r for r in records}
    conditions = [(c, [(n, lookup[(c, n)]["replicates"]) for n in names]) for c in categories]
    tests = {c: [] for c in categories}
    for a, b, p in comparisons:
        ra, rb = records[a], records[b]
        if ra["category"] != rb["category"]:
            raise ValueError("cross-category comparisons require multi_mode='intervals'")
        tests[ra["category"]].append((names.index(ra["name"]), names.index(rb["name"]), p))
    domain = options["value_domain"]
    if domain is None:
        groups = normalize_groups([(str(i), r["replicates"]) for i, r in enumerate(records)])
        low, high = sample_domain(groups, density=mode == "raincloud")
        domain = scale_from([max(0, low), high]).domain
        domain = (max(0, domain[0]), domain[1])
    # Three conditions fit one balanced row with a small minimum-width increase.
    width = max(options["width"], 1320) if len(categories) == 3 and options["width"] >= 1200 else options["width"]
    groups, orientation, highlight = None, "horizontal", options["highlight_series"]
    requested_tests = tests if comparisons else None
    if mode == "boxplot" and len(categories) * len(names) <= 12:
        # A single grouped panel uses the available width better than several
        # mostly empty two-row facets. Colors still identify the original series.
        groups = [(f"{c} / {n}", lookup[(c, n)]["replicates"]) for c in categories for n in names]
        indices = {(c, n): i for i, (c, n) in enumerate((c, n) for c in categories for n in names)}
        requested_tests = [
            (
                indices[records[a]["category"], records[a]["name"]],
                indices[records[b]["category"], records[b]["name"]],
                p,
            )
            for a, b, p in comparisons
        ] or None
        series_colors = pal["series"]
        pal = dict(pal, series=[series_colors[names.index(n)] for c in categories for n in names])
        conditions, orientation, highlight, width = None, "vertical", None, options["width"]
    return render_distribution(
        groups,
        conditions=conditions,
        kind=mode,
        orientation=orientation,
        y_min=domain[0],
        y_max=domain[1],
        academic=bool(comparisons),
        pairwise_p=requested_tests,
        show_points=options["show_points"],
        show_mean=True,
        title=options["title"],
        subtitle=options["subtitle"],
        figure_label=options["figure_label"],
        y_title=options["y_title"],
        y_unit=options["y_unit"],
        note=_joined(options["x_title"], options["note"]),
        source=options["source"],
        highlight_group=highlight,
        width=width,
        height=options["height"],
        palette=pal,
        font_family=options["font_family"],
    )


def _marimekko(categories, names, records, options, pal, colors):
    """Column width encodes total; tile area encodes each supplied component."""
    layout = ChartLayout(
        max(900, options["width"]),
        options["height"],
        pal,
        options["font_family"],
        n_items=max(len(categories), len(names)),
    )
    fs = max(18, layout.font_sizes["label"])
    top = layout.header(options["title"], options["subtitle"], options["figure_label"])
    top = _legend(layout, names, colors, top)
    lookup = {(r["category"], r["name"]): r["value"] for r in records}
    totals = {c: math.fsum(lookup[(c, n)] for n in names) for c in categories}
    if any(v <= 0 for v in totals.values()):
        raise ValueError("Marimekko requires a positive total in every category")
    largest = max(totals.values())
    relative = {c: totals[c] / largest for c in categories}
    weight_sum = math.fsum(relative.values())
    left, right = 74.0, layout.width - 28
    plot_width = right - left
    needed = max(140 * weight_sum / relative[c] for c in categories)
    if needed > max(options["width"] * 3, 2600):
        raise ValueError(
            "Marimekko has extremely narrow categories; use a heatmap for these summaries or explicitly regroup additive components"
        )
    plot_width = max(plot_width, needed)
    layout.width = max(layout.width, left + plot_width + 28)
    widths = {c: plot_width * relative[c] / weight_sum for c in categories}
    labels = [wrap_lines(c, widths[c] - 20, fs, layout.font) for c in categories]
    label_h = max(len(lines) for lines in labels) * fs * 1.35 + 42
    top += label_h
    height = max(300, options["height"] - top - 130)
    box = BBox(left, top, left + plot_width, top + height)
    scale = scale_from([0, 100], domain=(0, 100))
    numeric_axis(layout, box, scale, orientation="y", grid=True)
    x = left
    for ci, c in enumerate(categories):
        w = widths[c]
        middle = x + w / 2
        layout.text(c, middle, top - label_h + 4, fs=fs, bold=True, anchor="middle", width=w - 20)
        layout.text(
            tr("Total: {value}", value=_number(totals[c])) + (f" {options['y_unit']}" if options["y_unit"] else ""),
            middle,
            top - 31,
            fs=max(15, fs * 0.8),
            anchor="middle",
            color=layout.pal["ink6"],
        )
        cumulative = 0.0
        for name in names:
            value = lookup[(c, name)]
            share = 100 * value / totals[c]
            y = box.y1 - (cumulative + share) / 100 * height
            h = share / 100 * height
            layout.parts.append(
                f"""<rect {
                    _svg_attrs(
                        x=x,
                        y=y,
                        width=w,
                        height=h,
                        fill=colors[name],
                        stroke=pal.get("bg") or "white",
                        stroke_width=2,
                        data_role="marimekko-cell",
                        data_category=c,
                        data_series=name,
                        data_value=value,
                        data_percent=share,
                        data_total=totals[c],
                    )
                }/>"""
            )
            if options["show_values"] is not False and h >= fs * 1.6:
                fallback = _punchy_title_ink(
                    dict(pal, ink=_ink_on_bg(dict(pal, bg=colors[name], ink=colors[name])), bg=colors[name])
                )
                fill = readable_annotation_color(layout.ink, dict(pal, bg=colors[name], ink_fg=fallback))
                layout.text(f"{_number(share, 1)}%", middle, y + h / 2 - fs * 0.6, fs=fs, anchor="middle", color=fill)
            cumulative += share
        x += w
    _footer(
        layout,
        box.y1 + 26,
        _joined(
            tr("Column width = category total; tile area = component amount."), options["x_title"], options["note"]
        ),
        options["source"],
    )
    return layout.svg("Marimekko: category totals by width and component amounts by area")


def render_adaptive(categories, names, records, options):
    """Return an SVG, or None for an explicitly requested Cartesian geometry."""
    mode = options["multi_mode"]
    if mode == "composition":
        mode = "marimekko"
    if mode == "radial":
        raise ValueError(
            "grouped_bar multi_mode='radial': the radial ring was removed; use multi_mode='bars' (default) or 'heatmap'"
        )
    if mode not in MODES:
        raise ValueError(
            "grouped_bar multi_mode must be auto/single/bars/heatmap/intervals/boxplot/raincloud/marimekko/with_facet_by_series"
        )
    for key in ("show_points",):
        if not isinstance(options[key], bool):
            raise TypeError(f"{key} must be a boolean")
    if options["show_values"] is not None and not isinstance(options["show_values"], bool):
        raise TypeError("show_values must be a boolean or None")
    pal, colors = _palette(names, options["palette"], options["highlight_series"])
    auto = mode in {"auto", "single", "off", None}
    intervals = any("lo" in r for r in records)
    samples = any(len(r["replicates"]) > 1 for r in records)
    complete = len(records) == len(categories) * len(names)
    minimum = min(len(r["replicates"]) for r in records)
    has_tests = options["pairwise_p"] is not None or options["auto_test"] is not None or options["pairs"] is not None
    geometry = (
        options["orientation"] != "vertical" or options["axis_break"] is not None or options["line_series"] is not None
    )
    stacked = options["stack"] not in {None, "none"}
    if (
        auto
        and options["stack"] in {"percent", "stacked"}
        and not geometry
        and complete
        and not intervals
        and not samples
        and not has_tests
    ):
        mode = "marimekko"
    elif geometry or stacked or mode == "with_facet_by_series":
        if not auto and mode not in {"marimekko", "with_facet_by_series"}:
            raise ValueError(
                "explicit horizontal, stacked, broken-axis or dual-axis geometry cannot be combined with this adaptive mode"
            )
        if mode != "marimekko":
            for r in records:
                for key in ("lo", "hi"):
                    if key in r:
                        _negative(r[key], f"{r['category']}/{r['name']}, {key}")
            return None
    comparisons = _pairwise(
        records,
        categories,
        names,
        pairwise_p=options["pairwise_p"],
        auto_test=options["auto_test"],
        pairs=options["pairs"],
        single=False,
    )
    cross_tests = any(records[a]["category"] != records[b]["category"] for a, b, _ in comparisons)
    if auto and mode != "marimekko":
        if complete and minimum >= 5 and not cross_tests and options["show_values"] is not True:
            mode = (
                "raincloud"
                if options["show_points"] and minimum >= 20 and all(len(set(r["replicates"])) >= 5 for r in records)
                else "boxplot"
            )
        elif (
            intervals
            or samples
            or comparisons
            or (options["value_domain"] is not None and options["value_domain"][0] != 0)
        ):
            mode = "intervals"
        elif len(categories) * len(names) > 24 or len(categories) > 12 or len(names) > 4:
            mode = "intervals" if options["highlight_series"] else "heatmap"
        else:
            # Few nonnegative summary values: Cartesian bars on a shared value
            # axis (academic convention).
            mode = "bars"
    if mode in {"bars", "heatmap", "marimekko"} and (intervals or samples or comparisons):
        raise ValueError(f"{mode} would omit observation/interval/comparison evidence; use auto or intervals")
    if mode == "marimekko" and (options["stack"] not in {"stacked", "percent"} or not complete):
        raise ValueError("Marimekko requires stack='stacked'/'percent' and complete, explicitly additive components")
    if mode == "marimekko" and geometry:
        raise ValueError("Marimekko cannot override explicit horizontal, broken-axis or dual-axis geometry")
    if mode == "marimekko" and options["value_domain"] is not None and tuple(options["value_domain"]) != (0, 100):
        raise ValueError("Marimekko's within-category share axis uses value_domain=(0,100)")
    if options.get("reference_lines") and auto and mode in {"heatmap", "boxplot", "raincloud"}:
        mode = "intervals"
    if options.get("reference_lines") and mode not in {"bars", "intervals"}:
        raise ValueError(
            f"reference_lines are drawn on bar and interval views, not {mode}; "
            "pass multi_mode='intervals' (or 'bars' for plain summary values)"
        )
    if mode in {"boxplot", "raincloud"}:
        if not complete or minimum < 5:
            raise ValueError(
                "distribution mode requires at least 5 actual observations in every category/series; use intervals for sparse or mixed data"
            )
        if mode == "raincloud" and (minimum < 20 or any(len(set(r["replicates"])) < 5 for r in records)):
            raise ValueError(
                "raincloud requires at least 20 observations and 5 distinct values per cell; use boxplot or intervals"
            )
        if mode == "raincloud" and not options["show_points"]:
            raise ValueError("raincloud includes observations; use boxplot with show_points=False to hide them")
        if options["show_values"] is True:
            raise ValueError(
                "numeric summary labels require multi_mode='intervals'; distribution mode preserves samples and quartiles"
            )
        svg = _distribution(categories, names, records, comparisons, mode, options, pal)
    elif mode == "intervals":
        for r in records:
            for key in ("lo", "hi"):
                if key in r:
                    _negative(r[key], f"{r['category']}/{r['name']}, {key}")
        svg = _intervals(categories, names, records, comparisons, options, pal, colors)
    elif mode == "heatmap":
        if options["highlight_series"]:
            raise ValueError("heatmap does not encode a highlighted series; use intervals")
        svg = _heatmap(categories, names, records, options, pal)
    elif mode == "marimekko":
        svg = _marimekko(categories, names, records, options, pal, colors)
    else:
        svg = _bars(categories, names, records, options, pal)
    return _mark(svg, mode, records)
