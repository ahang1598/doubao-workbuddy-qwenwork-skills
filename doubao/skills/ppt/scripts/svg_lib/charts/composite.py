"""One-call scientific facets, aligned tracks and line/summary compositions."""

from __future__ import annotations

import math
from copy import deepcopy
from xml.sax.saxutils import quoteattr

from .._typography import chart_font_sizes
from ._academic_rigor import BBox, SeriesContext, SharedScale
from ._chart_layout import ChartLayout, finite, wrap_lines
from ._composition import (
    adjacent,
    attrs,
    color_key,
    footer,
    group_start,
    heading,
    numeric_axis,
    render_bar_plot,
    resolve_colors,
    scale_from,
    serialize_layout,
    size_key,
)
from ._matrix_core import ColorScale
from ._xy import (
    CategoryScale,
    _axis_format,
    _legend,
    _marker,
    fit_series,
    infer_scales,
    normalize_series,
    render_xy_plot,
    xy_density,
)

__all__ = ["make_composite"]


def _context(series, pal):
    names, colors = [], {}
    for s in series:
        name = s["name"]
        if name not in names:
            names.append(name)
        if s.get("color"):
            if name in colors and colors[name] != s["color"]:
                raise ValueError(f"series {name!r} has conflicting colors across panels")
            colors[name] = s["color"]
    context = SeriesContext(names, pal=pal)
    context.colors.update(colors)
    return context


def _p_label(value):
    from ._chart_layout import p_label, parse_p

    return p_label(parse_p(value, "pvalue"), ".4g")


def _prepare_panel(raw):
    if not isinstance(raw, dict) or "series" not in raw:
        raise ValueError("each panel needs name and canonical series")
    panel = dict(raw)
    panel["name"] = str(raw.get("name", ""))
    panel["x_transform"] = raw.get("x_transform", "linear")
    panel["y_transform"] = raw.get("y_transform", "linear")
    series = normalize_series(raw["series"])
    for s in series:
        if s.get("connect"):
            if s["curve"] or s.get("fit") not in (None, "none"):
                raise ValueError("connect cannot accompany a fit or precomputed curve")
            s["curve"] = [{"x": p["x"], "y": p["y"]} for p in sorted(s["points"], key=lambda p: p["x"])]
    panel["series"] = fit_series(
        series, show_ci=raw.get("show_ci", True), x_transform=panel["x_transform"], y_transform=panel["y_transform"]
    )
    return panel


def _shared_axis(panels, axis, share):
    if not isinstance(share, bool):
        raise TypeError(f"share_{axis} must be True or False")
    sources = [[s for p in panels for s in p["series"]]] * len(panels) if share else [p["series"] for p in panels]
    scales = []
    for panel, source in zip(panels, sources):
        transform = panel[f"{axis}_transform"]
        # Shared domains may use different explicit transforms for scale comparison.
        scales.append(infer_scales(source, **{f"{axis}_transform": transform})[0 if axis == "x" else 1])
    if share and all(not isinstance(s, CategoryScale) for s in scales):
        domain = (min(s.domain[0] for s in scales), max(s.domain[1] for s in scales))
        for scale in scales:
            if scale.transform == "log10" and domain[0] <= 0:
                # A linear comparison axis can include zero only due to padding;
                # the shared data bounds must remain positive on both views.
                domain = (min(s.domain[0] for s in scales if s.transform == "log10"), domain[1])
                break
        for scale in scales:
            scale.domain = domain
            scale.ticks = [v for v in scale.ticks or [] if domain[0] <= v <= domain[1]]
    for panel, scale in zip(panels, scales):
        if f"{axis}_domain" in panel:
            if share:
                raise ValueError(f"per-panel {axis}_domain requires share_{axis}=False")
            vals = [p[axis] for s in panel["series"] for p in s["points"] + s["curve"]]
            scale = scale_from(vals, domain=panel[f"{axis}_domain"], transform=panel[f"{axis}_transform"])
        panel[f"{axis}_scale"] = scale


def _panel_text(panel, show_stats):
    lines = []
    if "pvalue" in panel:
        lines.append(_p_label(panel["pvalue"]))
    for item in panel.get("significance", []):
        lines.append(f"{item.get('label', 'x = ' + str(item.get('x', '')))}: {_p_label(item['p'])}")
    for phase in panel.get("phases", []):
        if phase.get("label"):
            lines.append(f"{phase['label']}: {phase['start']}–{phase['end']}")
    for ref in panel.get("reference_lines", []):
        if ref.get("label"):
            lines.append(f"{ref['label']}: {ref.get('axis', 'y')} = {ref.get('value', 'x')}")
    if show_stats or panel.get("show_stats"):
        for s in panel["series"]:
            st = s.get("_stats")
            if st:
                lines.append(
                    f"{s['name']}: n = {st['n']}"
                    + (f" · R² = {st['r2']:.3f} · {_p_label(st['p'])}" if st["fit"] == "linear" else " · LOESS")
                )
    lines.extend(str(v) for v in panel.get("annotations", []))
    return lines


def _facets(data, layout, *, share_x, share_y, cols, show_stats, color_scale, size_label, **common):
    if not isinstance(data, (list, tuple)) or not data:
        raise ValueError("facets data must be a nonempty list of {name, series} panels")
    panels = [_prepare_panel(raw) for raw in data]
    _shared_axis(panels, "x", share_x)
    _shared_axis(panels, "y", share_y)
    series = [s for p in panels for s in p["series"]]
    context = _context(series, layout.pal)
    continuous = resolve_colors(series, layout.pal, color_scale)
    layout.font_sizes = chart_font_sizes(layout.width, layout.height, max(xy_density(p["series"]) for p in panels))
    outer_fonts = layout.font_sizes
    top = layout.header(common.get("title"), common.get("subtitle"), common.get("figure_label"))
    legend_series = list({s["name"]: s for s in reversed(series)}.values())[::-1]
    top = _legend(layout, legend_series, context, top)
    if continuous:
        top = color_key(layout, continuous, top)
    sizes = [p["size"] for s in series for p in s["points"] if "size" in p]
    size_max = max(sizes, default=1)
    if sizes:
        top = size_key(layout, size_max, top, label=size_label)
    cols = cols or min(3, math.ceil(math.sqrt(len(panels))))
    if not isinstance(cols, int) or isinstance(cols, bool) or cols < 1:
        raise ValueError("cols must be a positive integer")
    cols = min(cols, len(panels))
    min_cell = min(320, max(150, (layout.width - 56 - (cols - 1) * 26) / cols))
    layout.width = max(layout.width, cols * min_cell + 56 + (cols - 1) * 26)
    cell_w = (layout.width - 56 - (cols - 1) * 26) / cols
    rows = math.ceil(len(panels) / cols)
    for panel in panels:
        panel["_fonts"] = chart_font_sizes(cell_w, layout.height / rows, xy_density(panel["series"]))
        ys = panel["y_scale"]
        yfmt, _ = _axis_format(ys)
        labels = [p["label"] for s in panel["series"] for p in s["points"] if p.get("label")]
        rail = min(170, cell_w * 0.28) if labels else 0
        left = max(
            46 if min_cell == 320 else 36,
            min(160, max((layout.measure(yfmt(v), panel["_fonts"]["label"]) for v in ys.ticks or []), default=20) + 18),
        )
        panel["_gutters"] = (left, rail + (20 if labels else 14))
    if share_x:
        # One shared X scale retains one relative plot range even when panels
        # select different fonts from their own observation counts.
        shared_gutters = tuple(max(p["_gutters"][i] for p in panels) for i in (0, 1))
        for panel in panels:
            panel["_gutters"] = shared_gutters
    specs = []
    for panel in panels:
        layout.font_sizes = panel["_fonts"]
        xs, ys = panel["x_scale"], panel["y_scale"]
        labels = [p["label"] for s in panel["series"] for p in s["points"] if p.get("label")]
        rail = min(170, cell_w * 0.28) if labels else 0
        left, right = panel["_gutters"]
        plot_w = cell_w - left - right
        if plot_w < (110 if min_cell == 320 else 90):
            raise ValueError("facet labels need a wider canvas or fewer columns")
        title_lines = wrap_lines(panel["name"], cell_w, layout.font_sizes["group"], layout.heading)
        info = [
            line
            for text in _panel_text(panel, show_stats)
            for line in wrap_lines(text, cell_w, layout.font_sizes["foot"], layout.font)
        ]
        yheading = heading(
            panel.get("y_title", common.get("y_title")), ys, panel.get("y_unit", common.get("y_unit", ""))
        )
        ylines = wrap_lines(yheading, plot_w, layout.font_sizes["label"], layout.font) if yheading else []
        xheading = heading(
            panel.get("x_title", common.get("x_title")), xs, panel.get("x_unit", common.get("x_unit", ""))
        )
        xlines = wrap_lines(xheading, plot_w, layout.font_sizes["label"], layout.font) if xheading else []
        cat_lines = (
            max(
                (
                    len(
                        wrap_lines(
                            str(category), plot_w / len(xs.categories) * 0.92, layout.font_sizes["label"], layout.font
                        )
                    )
                    for category in xs.categories
                ),
                default=1,
            )
            if isinstance(xs, CategoryScale)
            else 1
        )
        top_h = (
            len(title_lines) * layout.font_sizes["group"] * 1.35
            + len(info) * layout.font_sizes["foot"] * 1.35
            + len(ylines) * layout.font_sizes["label"] * 1.35
            + 23
        )
        bottom_h = cat_lines * layout.font_sizes["label"] * 1.35 + len(xlines) * layout.font_sizes["label"] * 1.35 + 22
        label_h = sum(
            len(wrap_lines(v, max(40, rail - 8), layout.font_sizes["label"], layout.font))
            * layout.font_sizes["label"]
            * 1.35
            + 9
            for v in labels
        )
        category_h = (
            len(ys.categories)
            * max(
                (len(wrap_lines(v, left - 18, layout.font_sizes["label"], layout.font)) for v in ys.categories),
                default=1,
            )
            * layout.font_sizes["label"]
            * 1.35
            if isinstance(ys, CategoryScale)
            else 0
        )
        specs.append(
            {
                "left": left,
                "right": right,
                "top_h": top_h,
                "bottom_h": bottom_h,
                "min_h": top_h + max(160, label_h, category_h) + bottom_h,
                "title_lines": title_lines,
                "info": info,
                "ylines": ylines,
                "xlines": xlines,
                "labels": labels,
            }
        )
    if share_y:
        # A shared Y domain also needs one relative pixel range. Different
        # label sizes and wrapped headings must not move the data baselines.
        shared_top = max(spec["top_h"] for spec in specs)
        shared_bottom = max(spec["bottom_h"] for spec in specs)
        for spec in specs:
            spec["min_h"] += shared_top - spec["top_h"] + shared_bottom - spec["bottom_h"]
            spec["top_h"], spec["bottom_h"] = shared_top, shared_bottom
    cell_h = max(max(s["min_h"] for s in specs), (layout.height - top - 64 - (rows - 1) * 28) / rows)
    layout.font_sizes = outer_fonts
    footer_lines = sum(
        len(wrap_lines(v, layout.width - 56, layout.font_sizes["foot"], layout.font))
        for v in (common.get("note"), common.get("source"))
        if v
    )
    layout.height = max(
        layout.height, top + rows * cell_h + (rows - 1) * 28 + 48 + footer_lines * layout.font_sizes["foot"] * 1.35
    )
    boxes = []
    for i, (panel, spec) in enumerate(zip(panels, specs)):
        layout.font_sizes = panel["_fonts"]
        row, col = divmod(i, cols)
        x, y = 28 + col * (cell_w + 26), top + row * (cell_h + 28)
        layout.parts.append(group_start("facet", name=panel["name"], index=i))
        yy = y
        for line in spec["title_lines"]:
            layout.text(line, x, yy, fs=layout.font_sizes["group"], bold=True)
            yy += layout.font_sizes["group"] * 1.35
        for line in spec["info"]:
            layout.text(line, x, yy + 3, fs=layout.font_sizes["foot"], color=layout.pal["ink6"])
            yy += layout.font_sizes["foot"] * 1.35
        yy += 13
        for line in spec["ylines"]:
            layout.text(line, x + spec["left"], yy, fs=layout.font_sizes["label"])
            yy += layout.font_sizes["label"] * 1.35
        box = BBox(x + spec["left"], y + spec["top_h"], x + cell_w - spec["right"], y + cell_h - spec["bottom_h"])
        xs, ys = panel["x_scale"], panel["y_scale"]
        rail = BBox(box.x1 + 14, box.y0, x + cell_w, box.y1) if spec["labels"] else None
        layout.parts.append(
            render_xy_plot(
                panel["series"],
                box,
                x_scale=xs,
                y_scale=ys,
                context=context,
                palette=layout.pal,
                font_family=layout.font,
                font_sizes=layout.font_sizes,
                phases=panel.get("phases"),
                reference_lines=panel.get("reference_lines"),
                show_y_labels=not isinstance(ys, CategoryScale),
                label_bbox=rail,
                size_max=size_max,
                radius_max=12,
                summary=panel.get("summary", False),
            )
        )
        if isinstance(ys, CategoryScale):
            for category in ys.categories:
                lines = wrap_lines(category, spec["left"] - 18, layout.font_sizes["label"], layout.font)
                cy = ys.map(category, box.y1, box.y0)
                for j, line in enumerate(lines):
                    layout.text(
                        line,
                        box.x0 - 10,
                        cy - len(lines) * layout.font_sizes["label"] * 0.675 + j * layout.font_sizes["label"] * 1.35,
                        fs=layout.font_sizes["label"],
                        anchor="end",
                    )
        xy = y + cell_h - len(spec["xlines"]) * layout.font_sizes["label"] * 1.35 - 4
        for line in spec["xlines"]:
            layout.text(line, (box.x0 + box.x1) / 2, xy, fs=layout.font_sizes["label"], anchor="middle")
            xy += layout.font_sizes["label"] * 1.35
        layout.parts.append("</g>")
        boxes.append(
            {
                "name": panel["name"],
                "bbox": list(box),
                "x_domain": xs.domain,
                "y_domain": ys.domain,
                "x_transform": xs.transform,
                "y_transform": ys.transform,
            }
        )
    layout.font_sizes = outer_fonts
    footer(layout, common.get("note"), common.get("source"))
    serialize_layout(layout, "facets-layout", boxes)
    return layout.svg("Scientific facets with shared series identity and explicit axis domains")


def _row_records(data):
    rows = data.get("rows")
    if not rows:
        raise ValueError("tracks data requires explicit rows with stable ids")
    rows = [
        {"id": str(v["id"]), "label": str(v.get("label", v["id"]))}
        if isinstance(v, dict)
        else {"id": str(v), "label": str(v)}
        for v in rows
    ]
    ids = [r["id"] for r in rows]
    if len(set(ids)) != len(ids):
        raise ValueError("row ids must be unique")
    return rows, ids


def _tracks(data, layout, *, color_scale, size_label, **common):
    if not isinstance(data, dict):
        raise TypeError("tracks data must be a dictionary")
    rows, row_ids = _row_records(data)
    layout.font_sizes = chart_font_sizes(layout.width, layout.height, len(rows))
    tracks = deepcopy(data.get("tracks", []))
    if not tracks:
        raise ValueError("tracks data requires at least one track")
    groups = []
    all_sizes = []
    for t in tracks:
        t["kind"] = t.get("kind", "interval")
        if t["kind"] not in ("interval", "bar", "dots", "heatmap"):
            raise ValueError("track kind must be interval, bar, dots or heatmap")
        records = t.get("records", [])
        seen = set()
        for record in records:
            record["row_id"] = str(record["row_id"])
            if record["row_id"] not in row_ids:
                raise ValueError(f"unknown row_id {record['row_id']!r}")
            record["group"] = str(record.get("group", t.get("name", "Values")))
            group = record["group"]
            if group not in groups:
                groups.append(group)
            key = (record["row_id"], record.get("column"), group)
            if key in seen:
                raise ValueError("duplicate row/column/group track observation")
            seen.add(key)
            if t["kind"] == "dots":
                all_sizes.append(finite(record.get("size", 1), "size", minimum=0))
    for track in tracks:
        track["_groups"] = [g for g in groups if any(r["group"] == g for r in track["records"])]
        if track["kind"] in ("dots", "heatmap"):
            track["columns"] = list(
                map(str, track.get("columns") or dict.fromkeys(str(r["column"]) for r in track["records"]))
            )
    context = SeriesContext(groups, pal=layout.pal)
    top = layout.header(common.get("title"), common.get("subtitle"), common.get("figure_label"))
    legend_groups = [
        g for g in groups if any(r["group"] == g and "color_value" not in r for t in tracks for r in t["records"])
    ]
    if legend_groups:
        top = _legend(layout, [{"name": n, "points": [{}]} for n in legend_groups], context, top)
    size_max = max(all_sizes, default=1)
    if all_sizes:
        top = size_key(layout, size_max, top, label=size_label)
    color_values = [finite(r["color_value"], "color_value") for t in tracks for r in t["records"] if "color_value" in r]
    colors = ColorScale.from_values(color_values, layout.pal, **(color_scale or {})) if color_values else None
    if colors:
        top = color_key(layout, colors, top)
    row_label_w = min(240, max(layout.measure(r["label"], layout.font_sizes["label"]) for r in rows) + 15)
    weights = [finite(t.get("weight", 1), "track weight", minimum=0.1) for t in tracks]
    minimum_widths = [max(230, len(t.get("columns", [])) * max(1, len(t["_groups"])) * 32) for t in tracks]
    required_available = max(needed / weight * sum(weights) for needed, weight in zip(minimum_widths, weights))
    layout.width = max(layout.width, 56 + row_label_w + required_available + (len(tracks) - 1) * 32)
    available = layout.width - 56 - row_label_w - (len(tracks) - 1) * 32
    widths = [available * weight / sum(weights) for weight in weights]
    row_fonts = layout.font_sizes
    for track, track_width in zip(tracks, widths):
        track["_fonts"] = chart_font_sizes(track_width, layout.height, len(rows))
    row_lines = [wrap_lines(r["label"], row_label_w - 15, layout.font_sizes["label"], layout.font) for r in rows]
    row_h = max(35, max(len(v) for v in row_lines) * layout.font_sizes["label"] * 1.35 + 12)
    header_h = (
        max(
            len(wrap_lines(t.get("name", ""), w, t["_fonts"]["group"], layout.font)) * t["_fonts"]["group"] * 1.35
            for t, w in zip(tracks, widths)
        )
        + 18
    )
    title_h = 0
    for t, width in zip(tracks, widths):
        layout.font_sizes = t["_fonts"]
        if t["kind"] in ("dots", "heatmap"):
            columns = t.get("columns") or list(dict.fromkeys(str(r["column"]) for r in t["records"]))
            t["columns"] = list(map(str, columns))
            if not columns or len(set(t["columns"])) != len(columns):
                raise ValueError("matrix tracks need unique columns")
            if any(str(r["column"]) not in t["columns"] for r in t["records"]):
                raise ValueError("track column is absent from columns")
            column_h = (
                max(
                    len(wrap_lines(c, width / len(columns) - 8, layout.font_sizes["foot"], layout.font))
                    for c in t["columns"]
                )
                * layout.font_sizes["foot"]
                * 1.35
            )
            t["_column_h"] = column_h
            lane_width = width / len(columns) / max(1, len(t["_groups"]))
            group_h = (
                max(
                    (len(wrap_lines(g, lane_width - 6, layout.font_sizes["foot"], layout.font)) for g in t["_groups"]),
                    default=0,
                )
                * 14
            )
            title_h = max(title_h, column_h + group_h + 20)
        else:
            values = [finite(r[k], k) for r in t["records"] for k in ("value", "lo", "hi") if k in r]
            if not values:
                raise ValueError("numeric tracks require values")
            t["scale"] = scale_from(
                values, domain=t.get("domain"), transform=t.get("transform", "linear"), zero=t["kind"] == "bar"
            )
            title_h = max(
                title_h,
                len(
                    wrap_lines(
                        heading(t.get("axis_title"), t["scale"], t.get("unit", "")),
                        width,
                        layout.font_sizes["foot"],
                        layout.font,
                    )
                )
                * layout.font_sizes["foot"]
                * 1.35
                + 12,
            )
    bottom = top + header_h + title_h + len(rows) * row_h
    footer_lines = sum(
        len(wrap_lines(v, layout.width - 56, layout.font_sizes["foot"], layout.font))
        for v in (common.get("note"), common.get("source"))
        if v
    )
    layout.height = max(layout.height, bottom + 72 + footer_lines * layout.font_sizes["label"] * 1.35)
    y0, y1 = top + header_h + title_h, bottom
    centers = {rid: y0 + (i + 0.5) * row_h for i, rid in enumerate(row_ids)}
    layout.font_sizes = row_fonts
    for rid, lines in zip(row_ids, row_lines):
        for j, line in enumerate(lines):
            layout.text(
                line,
                28 + row_label_w - 15,
                centers[rid] - len(lines) * layout.font_sizes["label"] * 0.675 + j * layout.font_sizes["label"] * 1.35,
                fs=layout.font_sizes["label"],
                anchor="end",
            )
    x = 28 + row_label_w
    boxes = []
    for t, width in zip(tracks, widths):
        layout.font_sizes = t["_fonts"]
        box = BBox(x, y0, x + width, y1)
        layout.parts.append(group_start("aligned-track", name=t.get("name", ""), kind=t["kind"]))
        layout.text(t.get("name", ""), x, top, fs=layout.font_sizes["group"], bold=True, width=width)
        for i in range(len(rows)):
            if i % 2:
                layout.parts.append(
                    f'<rect x="{x:.3f}" y="{y0 + i * row_h:.3f}" width="{width:.3f}" height="{row_h:.3f}" fill={quoteattr(layout.pal["ink1"])} fill-opacity=".22"/>'
                )
        if t["kind"] in ("bar", "interval"):
            scale = t["scale"]
            numeric_axis(layout, box, scale, grid=True)
            layout.text(
                heading(t.get("axis_title"), scale, t.get("unit", "")),
                x,
                top + header_h,
                fs=layout.font_sizes["foot"],
                width=width,
            )
            grouping = {rid: [r for r in t["records"] if r["row_id"] == rid] for rid in row_ids}
            for rid, records in grouping.items():
                for i, r in enumerate(records):
                    center = centers[rid] + (i - (len(records) - 1) / 2) * row_h * 0.62 / max(1, len(records))
                    color = r.get("color", context.color_of(r["group"]))
                    if t["kind"] == "bar":
                        rec = dict(r, name=r["group"], interval_color=r.get("interval_color", layout.ink))
                        layout.parts.append(
                            render_bar_plot(
                                [rec],
                                box,
                                scale=scale,
                                colors={r["group"]: color},
                                orientation="horizontal",
                                centers=[center],
                                thickness=row_h * 0.58 / max(1, len(records)),
                            )
                        )
                    else:
                        value = finite(r["value"], "value")
                        lo, hi = finite(r.get("lo", value), "lo"), finite(r.get("hi", value), "hi")
                        if ("lo" in r) != ("hi" in r) or not lo <= value <= hi:
                            raise ValueError("interval must provide lo <= value <= hi")
                        points = [scale.map(v, box.x0, box.x1) for v in (lo, value, hi)]
                        layout.parts.append(
                            f'<path d="M{points[0]:.3f},{center:.3f} H{points[2]:.3f}" stroke={quoteattr(color)} stroke-width="1.6" {attrs(role="interval", row_id=rid, group=r["group"])}/>'
                        )
                        layout.parts.append(
                            _marker(
                                points[1],
                                center,
                                4,
                                "circle",
                                color,
                                opacity=1,
                                role="track-point",
                                attrs=attrs(row_id=rid, group=r["group"], value=value),
                            )
                        )
                    if "pvalue" in r:
                        # P values live in an allocated text strip below each track.
                        text = f"{next(row['label'] for row in rows if row['id'] == rid)} · {r['group']}: {_p_label(r['pvalue'])}"
                        t.setdefault("_p_lines", []).extend(
                            wrap_lines(text, width, layout.font_sizes["foot"], layout.font)
                        )
        else:
            columns = t["columns"]
            cw = width / len(columns)
            for j, column in enumerate(columns):
                layout.text(
                    column,
                    x + (j + 0.5) * cw,
                    top + header_h,
                    fs=layout.font_sizes["foot"],
                    anchor="middle",
                    width=cw - 8,
                )
                lane = cw / max(1, len(t["_groups"]))
                for gi, group in enumerate(t["_groups"]):
                    layout.text(
                        group,
                        x + j * cw + (gi + 0.5) * lane,
                        top + header_h + t["_column_h"] + 7,
                        fs=layout.font_sizes["foot"],
                        anchor="middle",
                        width=lane - 6,
                        color=layout.pal["ink6"],
                    )
            for r in t["records"]:
                column = str(r["column"])
                lane_width = cw / max(1, len(t["_groups"]))
                group_index = t["_groups"].index(r["group"])
                cx = x + columns.index(column) * cw + (group_index + 0.5) * lane_width
                cy = centers[r["row_id"]]
                color = (
                    colors.color(r["color_value"])
                    if colors and "color_value" in r
                    else r.get("color", context.color_of(r["group"]))
                )
                if t["kind"] == "heatmap":
                    layout.parts.append(
                        f'<rect x="{cx - lane_width / 2 + 0.4:.3f}" y="{cy - row_h / 2 + 0.4:.3f}" width="{lane_width - 0.8:.3f}" height="{row_h - 0.8:.3f}" fill={quoteattr(color)} {attrs(role="track-cell", row_id=r["row_id"], column=column)}/>'
                    )
                else:
                    value = finite(r.get("size", 1), "size", minimum=0)
                    radius = min(12, lane_width * 0.4, row_h * 0.36) * math.sqrt(value / size_max) if size_max else 0
                    layout.parts.append(
                        _marker(
                            cx,
                            cy,
                            radius,
                            "circle",
                            color,
                            opacity=0.9,
                            role="track-dot",
                            stroke_color=layout.pal["ink6"] if "color_value" in r else None,
                            attrs=attrs(row_id=r["row_id"], column=column, group=r["group"], size=value),
                        )
                    )
        layout.parts.append("</g>")
        boxes.append({"name": t.get("name", ""), "bbox": list(box), "row_centers": centers})
        x += width + 32
    pheight = max((len(t.get("_p_lines", [])) for t in tracks), default=0) * 14
    if pheight:
        layout.height = max(layout.height, bottom + 64 + pheight + footer_lines * layout.font_sizes["label"] * 1.35)
        for t, box in zip(tracks, boxes):
            for i, line in enumerate(t.get("_p_lines", [])):
                layout.text(
                    line, box["bbox"][0], bottom + 42 + i * 14, fs=layout.font_sizes["foot"], color=layout.pal["ink6"]
                )
    footer(layout, common.get("note"), common.get("source"))
    serialize_layout(layout, "tracks-layout", boxes)
    return layout.svg("Multiple evidence tracks aligned by explicit row identity")


def _auc(series, source, interval=None):
    if source not in ("points", "curve"):
        raise ValueError("AUC source must explicitly be points or curve")
    knots = []
    for s in series:
        values = sorted([(finite(p["x"], "AUC x"), finite(p["y"], "AUC y")) for p in s[source]])
        if len(values) < 2 or any(a[0] == b[0] for a, b in adjacent(values)):
            raise ValueError(
                "AUC needs at least two distinct x values per series; replicate observations require an explicit summary curve"
            )
        knots.append(values)
    low = max(v[0][0] for v in knots)
    high = min(v[-1][0] for v in knots)
    if interval is not None:
        low, high = map(float, interval)
        if any(low < v[0][0] or high > v[-1][0] for v in knots):
            raise ValueError("AUC interval must lie within every series; extrapolation is not supported")
    if not math.isfinite(low) or not math.isfinite(high) or low >= high:
        raise ValueError("AUC requires a nonempty common interval")
    records = []
    for s, values in zip(series, knots):
        clipped = []
        for a, b in adjacent(values):
            start, end = max(low, a[0]), min(high, b[0])
            if start < end:
                ya = a[1] + (b[1] - a[1]) * ((start - a[0]) / (b[0] - a[0]))
                yb = a[1] + (b[1] - a[1]) * ((end - a[0]) / (b[0] - a[0]))
                clipped.append((end - start) * (ya / 2 + yb / 2))
        records.append({"name": s["name"], "value": math.fsum(clipped)})
    return records, (low, high)


def _line_bar(data, layout, *, color_scale, size_label, **common):
    if not isinstance(data, dict) or "series" not in data:
        raise ValueError("line_bar requires a dictionary containing canonical series")
    panel = _prepare_panel(data)
    layout.font_sizes = chart_font_sizes(layout.width, layout.height, xy_density(panel["series"]))
    series = panel["series"]
    context = _context(series, layout.pal)
    xs, ys = infer_scales(series, x_transform=panel["x_transform"], y_transform=panel["y_transform"])
    inset = data.get("inset", {})
    if "bars" in data:
        records = deepcopy(data["bars"])
        caption = inset.get("title", "Summary")
    else:
        source = inset.get("source", "points")
        records, bounds = _auc(series, source, inset.get("interval"))
        caption = inset.get("title", "AUC") + f" · {bounds[0]:g}–{bounds[1]:g} · {source}"
    for r in records:
        r["name"] = str(r["name"])
        r.setdefault("interval_color", layout.ink)
        if r["name"] not in context.ids:
            raise ValueError("summary bars must reference a plotted series name")
    if not records or len({r["name"] for r in records}) != len(records):
        raise ValueError("summary bars need unique series names")
    bscale = scale_from([r[k] for r in records for k in ("value", "lo", "hi") if k in r], zero=True)
    layout.width = max(layout.width, 760, len(records) * 170 + 100)
    # Reserve an actual empty upper band in data coordinates for the inset.
    a, b = ys.domain
    if ys.transform == "log10":
        la, lb = math.log10(a), math.log10(b)
        ys = SharedScale((a, 10 ** (lb + (lb - la) * 1.05)), ys.ticks, "log10")
    else:
        ys = SharedScale((a, b + (b - a) * 1.05), ys.ticks)
    top = layout.header(common.get("title"), common.get("subtitle"), common.get("figure_label"))
    top = _legend(layout, series, context, top)
    continuous = resolve_colors(series, layout.pal, color_scale)
    if continuous:
        top = color_key(layout, continuous, top)
    sizes = [p["size"] for s in series for p in s["points"] if "size" in p]
    size_max = max(sizes, default=1)
    if sizes:
        top = size_key(layout, size_max, top, label=size_label)
    for record in records:
        if "pvalue" in record:
            top += (
                layout.text(
                    f"{record['name']}: {_p_label(record['pvalue'])}",
                    28,
                    top,
                    fs=layout.font_sizes["foot"],
                    width=layout.width - 56,
                )
                + 4
            )
    for info in _panel_text(panel, common.get("show_stats", False)):
        top += layout.text(info, 28, top, fs=layout.font_sizes["foot"], width=layout.width - 56) + 4
    left = max(
        60,
        max((layout.measure(_axis_format(ys)[0](v), layout.font_sizes["label"]) for v in ys.ticks or []), default=20)
        + 22,
    )
    title = heading(data.get("y_title", common.get("y_title")), ys, data.get("y_unit", common.get("y_unit", "")))
    if title:
        top += layout.text(title, left, top, fs=layout.font_sizes["label"], width=layout.width - left - 40) + 12
    foot_lines = sum(
        len(wrap_lines(v, layout.width - 56, layout.font_sizes["foot"], layout.font))
        for v in (common.get("note"), common.get("source"))
        if v
    )
    layout.height = max(layout.height, top + 520 + foot_lines * layout.font_sizes["label"] * 1.35)
    plot_bottom = layout.height - 94 - foot_lines * layout.font_sizes["label"] * 1.35
    labels = [p["label"] for s in series for p in s["points"] if p.get("label")]
    right = 185 if labels else 38
    box = BBox(left, top, layout.width - right, plot_bottom)
    rail = BBox(box.x1 + 14, box.y0, layout.width - 28, box.y1) if labels else None
    layout.parts.append(
        render_xy_plot(
            series,
            box,
            x_scale=xs,
            y_scale=ys,
            context=context,
            palette=layout.pal,
            font_family=layout.font,
            font_sizes=layout.font_sizes,
            phases=data.get("phases"),
            reference_lines=data.get("reference_lines"),
            label_bbox=rail,
            size_max=size_max,
            radius_max=12,
        )
    )
    ix0, ix1 = box.x0 + (box.x1 - box.x0) * 0.46, box.x1 - 18
    iy0, iy1 = box.y0 + 15, box.y0 + (box.y1 - box.y0) * 0.43
    layout.parts.append(
        f'<rect x="{ix0:.3f}" y="{iy0:.3f}" width="{ix1 - ix0:.3f}" height="{iy1 - iy0:.3f}" fill={quoteattr(layout.pal.get("bg") or "#FFFFFF")} stroke={quoteattr(layout.pal["ink2"])} stroke-width=".7" data-role="inset-background"/>'
    )
    main_fonts = layout.font_sizes
    layout.font_sizes = chart_font_sizes(ix1 - ix0, iy1 - iy0, len(records))
    inset_left = max(
        44,
        max(
            (layout.measure(_axis_format(bscale)[0](v), layout.font_sizes["foot"]) for v in bscale.ticks or []),
            default=20,
        )
        + 14,
    )
    title_h = layout.text(
        heading(caption, bscale), ix0 + 12, iy0 + 10, fs=layout.font_sizes["label"], bold=True, width=ix1 - ix0 - 24
    )
    cat_w = (ix1 - ix0 - inset_left - 15) / len(records)
    cat_lines = [wrap_lines(r["name"], cat_w - 6, layout.font_sizes["foot"], layout.font) for r in records]
    label_h = max(len(v) for v in cat_lines) * layout.font_sizes["foot"] * 1.35 + 9
    ibox = BBox(ix0 + inset_left, iy0 + title_h + 24, ix1 - 15, iy1 - label_h - 8)
    if ibox.y1 - ibox.y0 < 45 or cat_w < 20:
        raise ValueError("summary inset needs a larger canvas")
    layout.parts.append(group_start("summary-inset", title=caption))
    numeric_axis(layout, ibox, bscale, orientation="y", grid=True)
    layout.parts.append(render_bar_plot(records, ibox, scale=bscale, colors=context.colors))
    for i, lines in enumerate(cat_lines):
        for j, line in enumerate(lines):
            layout.text(
                line,
                ibox.x0 + (i + 0.5) * (ibox.x1 - ibox.x0) / len(records),
                ibox.y1 + 8 + j * layout.font_sizes["foot"] * 1.35,
                fs=layout.font_sizes["foot"],
                anchor="middle",
            )
    layout.parts.append("</g>")
    layout.font_sizes = main_fonts
    xtitle = heading(data.get("x_title", common.get("x_title")), xs, data.get("x_unit", common.get("x_unit", "")))
    layout.text(
        xtitle,
        (box.x0 + box.x1) / 2,
        box.y1 + layout.font_sizes["xtick"] * 1.35 + 12,
        fs=layout.font_sizes["xaxis"],
        anchor="middle",
        width=box.x1 - box.x0,
    )
    footer(layout, common.get("note"), common.get("source"))
    serialize_layout(
        layout,
        "line-bar-layout",
        [{"bbox": list(box), "inset_bbox": list(ibox), "x_domain": xs.domain, "y_domain": ys.domain}],
    )
    return layout.svg("Line chart with a measured summary bar inset")


def make_composite(
    data,
    *,
    template="facets",
    title=None,
    subtitle=None,
    figure_label=None,
    note=None,
    source=None,
    x_title=None,
    y_title=None,
    x_unit="",
    y_unit="",
    share_x=True,
    share_y=True,
    cols=None,
    show_stats=False,
    color_scale=None,
    size_label="Size",
    width=1300,
    height=900,
    palette="archive_ink",
    font_family=None,
):
    """Return one complete SVG from one data object.

    Templates:
      ``facets``: list of ``{name, series, ...}`` XY panels. Series follow the
        scatter/line contract. Axes, colors and marker areas share scales by
        default; ``share_x=False`` / ``share_y=False`` selects free domains.
      ``tracks``: ``{rows:[{id,label}], tracks:[{name,kind,records,...}]}``.
        Record identity is ``row_id``; optional ``group`` never implies row order.
        Kind is interval/bar/dots/heatmap. Dot records add column/size/color_value.
      ``line_bar``: ``{series, bars? , inset:{source,interval,title}}``. If bars
        are absent, trapezoidal AUC uses actual x spacing on the common interval.
        ``source='points'`` and ``source='curve'`` remain distinct. ``connect``
        explicitly connects observations; no prediction is inferred from it.
      ``heatmap``: matrix/line/inset/trees/side tracks; see composite_matrix.
      ``panels``: {panels:[{id,kind,data,...}], connections?:[...]}. Kinds are
        xy/volcano/heatmap/network/phylogeny/pairs/bar/forest/swimmer,
        radar/contour and violin/boxplot/raincloud. Axes are independent
        unless panel x_group/y_group explicitly names a shared physical axis.
        ``detail_of`` inherits an earlier xy/radar/contour panel without copying
        its data; optional x_range/y_range selects a true XY data-range zoom.
        ``span`` sets panel column span (details span the full row by default).
        XY data.inset accepts independent XY series and annotations, e.g.
        precomputed mortality curves. Contour z_group shares levels/color range.
        Compositions containing distributions reconcile matching XY/distribution
        group names across reordered series; explicit color conflicts reject.
        Radar panels accept the same axes/series/grid inputs as make_radar;
        common explicit axis bounds preserve comparison across panels.

    Width and height are minimum canvas dimensions; dense labels and additional
    panels can grow the canvas so no requested text is silently hidden.
    """
    if template not in ("facets", "tracks", "line_bar", "heatmap", "panels"):
        raise ValueError("template must be facets, tracks, line_bar, heatmap or panels")
    layout = ChartLayout(width, height, palette, font_family)
    common = {
        "title": title,
        "subtitle": subtitle,
        "figure_label": figure_label,
        "note": note,
        "source": source,
        "x_title": x_title,
        "y_title": y_title,
        "x_unit": x_unit,
        "y_unit": y_unit,
        "show_stats": show_stats,
    }
    if template == "panels":
        from ._composition_panels import make_panels

        return make_panels(data, layout, cols=cols, **common)
    if template == "facets":
        return _facets(
            data,
            layout,
            share_x=share_x,
            share_y=share_y,
            cols=cols,
            color_scale=color_scale,
            size_label=size_label,
            **common,
        )
    if template == "tracks":
        return _tracks(data, layout, color_scale=color_scale, size_label=size_label, **common)
    if template == "line_bar":
        return _line_bar(data, layout, color_scale=color_scale, size_label=size_label, **common)
    from .composite_matrix import make_matrix_composition

    return make_matrix_composition(data, layout=layout, color_scale=color_scale, size_label=size_label, **common)
