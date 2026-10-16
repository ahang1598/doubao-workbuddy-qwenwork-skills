"""Heterogeneous scientific panels built from data and plot-only renderers."""

from __future__ import annotations

import math
from copy import deepcopy
from xml.sax.saxutils import quoteattr

from .._typography import chart_font_sizes
from ._academic_rigor import BBox, SeriesContext, SharedScale
from ._categorical import _pairwise, _stack_records, normalize_records, render_categorical_plot
from ._categorical_table import _cell_text, normalize_columns, normalize_forest_rows, render_table_plot
from ._chart_layout import finite, wrap_lines
from ._composition import (
    attrs,
    footer,
    group_start,
    heading,
    numeric_axis,
    resolve_colors,
    scale_from,
    serialize_layout,
)
from ._composition_distribution import marginal_profiles, render_contours, render_marginal, transformed
from ._composition_rows import RowScale, align_category_rows
from ._network_core import aligned_tracks, node_colors, normalize_network, render_edges, render_size_key
from ._pair_glyphs import frequency_display, frequency_note, frequency_reference
from ._phylo_core import normalize_tree
from ._polar import legend_rows, render_legend
from ._scientific_panels import (
    finalize_contours,
    prepare_contour,
    render_contour_panel,
)
from ._xy import (
    CategoryScale,
    _axis_format,
    _marker,
    fit_series,
    infer_scales,
    normalize_series,
    render_xy_plot,
    series_context,
    xy_density,
)
from ._xy_geometry import Obstacle, route_leader
from .composite_matrix import MatrixPlot, _line_data, _tree
from .network import render_network_plot
from .pairs import _records, _series, correlation
from .phylogeny import _tree_tracks, render_phylogeny_plot
from .radar import prepare_radar, render_radar_panel
from .swimmer import render_swimmer_plot, swimmer_height, swimmer_state
from .volcano import _threshold_branches, classify_volcano
from ._shared import tr


def _panel_density(panel):
    """Measure visible identities for groups/grids, actual observations for XY."""
    kind, data = panel["kind"], panel["data"]
    if kind in ("xy", "volcano"):
        return xy_density(panel["series"])
    if kind in ("violin", "boxplot", "raincloud"):
        return max(1, len(panel.get("categories", data.get("categories", data.get("groups", [])))))
    if kind == "pairs":
        return sum(len(rows) for rows in panel["groups"].values())
    if kind == "heatmap":
        state = panel["state"]
        return max(state.nr, state.nc)
    if kind == "bar":
        return max(len(panel["categories"]), len(panel["context"].ids))
    if kind == "forest":
        return len(panel["rows"])
    if kind == "radar":
        return len(data.get("axes", data.get("categories", []))) or len(panel.get("series", []))
    if kind == "contour":
        return len(data["points"]) if data.get("points") else max(len(panel["grid"]), len(panel["grid"][0]))
    if kind == "swimmer":
        return len(data["patients"])
    return len(panel.get("nodes", panel.get("tree", {}).get("nodes", []))) or 1


def _panel_fonts(panel, canvas, width):
    panel["_fonts"] = chart_font_sizes(width, panel.get("_font_height", panel["min_height"]), _panel_density(panel))
    if panel.get("inset"):
        _panel_fonts(panel["inset"], canvas, width - 20)
    return panel["_fonts"]


def _entries(names, colors):
    return [{"name": name, "color": colors[name], "direction": "out"} for name in names]


def _volcano(data, canvas):
    points, function, cutoff = classify_volcano(
        data["points"], data.get("fc_threshold", 1), data.get("p_threshold", 0.05), data.get("threshold")
    )
    limit = finite(data.get("top_k_labels", 8), "top_k_labels", minimum=0)
    if not limit.is_integer():
        raise ValueError("top_k_labels must be an integer")
    ranked = sorted((p for p in points if p["category"] != "ns"), key=lambda p: (-p["np"], -abs(p["fc"]), p["name"]))
    labels = set(data.get("highlight_names", [])) | {p["name"] for p in ranked[: int(limit)]}
    names = {"ns": tr("Not significant"), "up": tr("Upregulated"), "down": tr("Downregulated")}
    colors = {"ns": canvas.pal["ink4"], "up": canvas.pal["accent"], "down": canvas.pal["secondary"]}
    series = []
    for category in ("ns", "down", "up"):
        members = [p for p in points if p["category"] == category]
        if members:
            series.append(
                {
                    "name": names[category],
                    "color": colors[category],
                    "points": [
                        {
                            "x": p["fc"],
                            "y": p["np"],
                            "id": p.get("id", p["name"]),
                            "label": p["name"] if p["name"] in labels else "",
                        }
                        for p in members
                    ],
                }
            )
    series = normalize_series(series)
    span = max(abs(p["fc"]) for p in points) or 1
    xs = scale_from([-span * 1.12, span * 1.12])
    ys = scale_from([0, max(max(p["np"] for p in points) * 1.12, cutoff * 1.3, 1)])
    refs = [{"axis": "x", "value": -data.get("fc_threshold", 1)}, {"axis": "x", "value": data.get("fc_threshold", 1)}]
    if data.get("threshold") is None:
        refs.append({"axis": "y", "value": cutoff})
    return (
        series,
        xs,
        ys,
        refs,
        (function, points),
        [f"Classification: |log₂ FC| ≥ {data.get('fc_threshold', 1):g}; P ≤ {data.get('p_threshold', 0.05):g}."],
    )


def _prepare(raw, canvas, index):
    if not isinstance(raw, dict) or "kind" not in raw or "data" not in raw:
        raise ValueError("each heterogeneous panel requires kind and data")
    panel = deepcopy(raw)
    panel["id"] = str(raw.get("id", f"panel{index + 1}"))
    panel["name"] = str(raw.get("name", panel["id"]))
    kind = panel["kind"]
    if kind not in (
        "xy",
        "volcano",
        "heatmap",
        "network",
        "phylogeny",
        "pairs",
        "bar",
        "forest",
        "swimmer",
        "radar",
        "contour",
        "violin",
        "boxplot",
        "raincloud",
    ):
        raise ValueError(
            "panel kind must be xy, volcano, heatmap, network, phylogeny, pairs, bar, forest, swimmer, radar, contour, violin, boxplot or raincloud"
        )
    data = panel["data"]
    if not isinstance(data, dict):
        raise TypeError("panel data is a dictionary of the selected family inputs")
    panel.update(entries=[], rings=[], notes=[], axes={}, min_width=560, min_height=330)
    if kind in ("xy", "volcano"):
        if kind == "volcano":
            series, xs, ys, refs, threshold, notes = _volcano(data, canvas)
            panel.update(refs=refs, threshold=threshold, notes=notes)
            data.setdefault("x_title", tr("log₂ fold change"))
            data.setdefault("y_title", "−log₁₀ P")
        else:
            series = normalize_series(data["series"])
            for item in series:
                if item.get("connect"):
                    if item["curve"] or item.get("fit") not in (None, "none"):
                        raise ValueError("connect cannot accompany a fit or prediction curve")
                    item["curve"] = [{"x": p["x"], "y": p["y"]} for p in sorted(item["points"], key=lambda p: p["x"])]
            series = fit_series(
                series,
                show_ci=data.get("show_ci", True),
                x_transform=data.get("x_transform", "linear"),
                y_transform=data.get("y_transform", "linear"),
            )
            xs, ys = infer_scales(
                series, x_transform=data.get("x_transform", "linear"), y_transform=data.get("y_transform", "linear")
            )
            panel["refs"] = data.get("reference_lines", [])
        continuous = resolve_colors(series, canvas.pal, data.get("color_scale"))
        context = series_context(series, canvas.pal)
        panel.update(
            series=series, context=context, axes={"x": xs, "y": ys}, entries=_entries(context.ids, context.colors)
        )
        labels = [p["label"] for s in series for p in s["points"] if p.get("label")]
        panel["min_height"] = max(
            330,
            sum(
                len(wrap_lines(v, 145, canvas.font_sizes["foot"], canvas.font)) * canvas.font_sizes["foot"] * 1.35 + 9
                for v in labels
            )
            + 85,
        )
        if labels:
            panel["min_width"] = 690
        if continuous:
            panel["entries"].append(
                {
                    "name": f"{continuous.label}: {continuous.low:.4g}–{continuous.high:.4g}",
                    "color": continuous,
                    "direction": "out",
                }
            )
        sizes = [p["size"] for item in series for p in item["points"] if "size" in p]
        if sizes:
            panel["notes"].append(f"Marker area ∝ {data.get('size_label', 'size')}; maximum {max(sizes):.4g}.")
        for phase in data.get("phases", []):
            if phase.get("label"):
                panel["notes"].append(f"{phase['label']}: {phase['start']}–{phase['end']}")
        for item in data.get("significance", []):
            from ._chart_layout import p_label

            panel["notes"].append(f"{item.get('label', item.get('x', ''))}: {p_label(item['p'], '.4g')}")
        for reference in panel["refs"]:
            if reference.get("label"):
                panel["notes"].append(
                    f"{reference['label']}: {reference.get('axis', 'y')} = {reference.get('value', 'x')}"
                )
        if data.get("show_stats"):
            for item in series:
                stat = item.get("_stats")
                if stat:
                    panel["notes"].append(
                        f"{item['name']}: n={stat['n']}; "
                        + (f"R²={stat['r2']:.3g}; P={stat['p']:.4g}" if stat["fit"] == "linear" else "LOESS")
                    )
    elif kind == "radar":
        panel.update(prepare_radar(data, canvas))
    elif kind == "contour":
        panel.update(prepare_contour(data, canvas))
    elif kind in ("violin", "boxplot", "raincloud"):
        from ._distribution_panels import prepare_distribution_panel

        panel.update(prepare_distribution_panel(kind, data, canvas))
    elif kind == "heatmap":
        if data.get("inset") or data.get("tracks"):
            raise ValueError(
                "heterogeneous heatmap panels take matrix/trees/line data; nested inset/side-track compositions use template='heatmap'"
            )
        state = MatrixPlot(data, canvas.pal, canvas.font, data.get("color_scale"))
        panel["state"] = state
        scales = [s for s in (state.scale, state.upper_scale) if s is not None]
        panel["entries"] = [
            {"name": f"{s.label}: {s.low:.4g}–{s.high:.4g}", "color": s, "direction": "out"} for s in scales
        ]
        panel["min_width"] = max(560, state.nc * 48 + 170)
        panel["min_height"] = max(330, state.nr * 32 + 80) + 90 * sum(side in state.trees for side in ("top", "bottom"))
        if data.get("line"):
            panel["line"], panel["line_scale"] = _line_data(state, data["line"])
            panel["notes"].append(heading(data["line"].get("label", "Column mean"), panel["line_scale"]))
    elif kind == "network":
        nodes, links = normalize_network(data["nodes"], data.get("edges", []))
        colors = node_colors(nodes, canvas.pal)
        cats = list(dict.fromkeys(n["category"] for n in nodes))
        panel.update(
            nodes=nodes,
            links=links,
            entries=_entries(cats, {c: colors[next(n["id"] for n in nodes if n["category"] == c)] for c in cats}),
        )
        outer = [n["id"] for n in nodes if n.get("side", "outer") == "outer"]
        panel["rings"] = aligned_tracks(data.get("tracks"), outer, outer, canvas.pal) if data.get("tracks") else []
        panel["min_width"] = max(720, 720 + max(0, math.sqrt(len(nodes)) - 4) * 100 + len(panel["rings"]) * 48)
        panel["min_height"] = max(
            410, sum(len(wrap_lines(n.get("label") or "", 125, 11.5, canvas.font)) * 15.6 + 7 for n in nodes) + 30
        )
        if any(e["_weighted"] for e in links):
            panel["notes"].append(
                f"Edge width ∝ |weight / correlation|; maximum {max(e['_magnitude'] for e in links):.3g}."
            )
        if any(e.get("pvalue") is not None for e in links):
            panel["notes"].append("Dashed associations: supplied P ≥ 0.05.")
        if any(e["_sign"] is not None for e in links):
            panel["entries"] += _entries(
                ["Positive association", "Negative association"],
                {"Positive association": canvas.pal["accent"], "Negative association": canvas.pal["secondary"]},
            )
    elif kind == "phylogeny":
        tree = normalize_tree(data["tree"], data.get("branch_mode", "auto"), data.get("leaf_order"))
        rings = _tree_tracks(tree, data.get("tracks"), canvas.pal)
        panel.update(
            tree=tree,
            rings=rings,
            min_width=720 + 48 * len(rings),
            min_height=max(
                420,
                sum(len(wrap_lines(n.get("label") or "", 125, 11.5, canvas.font)) * 15.6 + 7 for n in tree["nodes"])
                + 30,
            ),
        )
        panel["notes"].append(tr("Radius preserves cumulative branch length; dashed tip extensions add no length."))
    elif kind == "pairs":
        variables, groups = _records(data["records"], data.get("variables"), data.get("group_key", "group"))
        transforms = data.get("transforms", {})
        if set(transforms) - set(variables) or any(t not in ("linear", "log10") for t in transforms.values()):
            raise ValueError("pair transforms must name selected variables with linear/log10")
        if (
            data.get("diagonal", "hist") not in ("hist", "kde")
            or data.get("lower", "scatter") not in ("scatter", "density")
            or data.get("method", "pearson") not in ("pearson", "spearman")
        ):
            raise ValueError("invalid pairs diagonal/lower/method")
        scales = {
            v: infer_scales(
                _series(groups, v, v), x_transform=transforms.get(v, "linear"), y_transform=transforms.get(v, "linear")
            )[0]
            for v in variables
        }
        context = series_context(_series(groups, variables[0], variables[1]), canvas.pal)
        context.colors.update(data.get("group_colors", {}))
        panel.update(
            variables=variables,
            groups=groups,
            scales=scales,
            context=context,
            entries=_entries(
                [f"[{i + 1}] {name}" for i, name in enumerate(groups)],
                {f"[{i + 1}] {name}": context.color_of(name) for i, name in enumerate(groups)},
            ),
            min_width=len(variables) * 180 + 160,
            min_height=len(variables) * max(145, len(groups) * 24 + 60) + 95,
        )
        panel["notes"].append(
            f"Upper: {data.get('method', 'pearson')} per group; n is observed pairs. Diagonal: {data.get('diagonal', 'hist')}; lower: {data.get('lower', 'scatter')}."
        )
        panel["frequency_max"] = (
            frequency_reference(groups, variables) if data.get("lower", "scatter") == "scatter" else 1
        )
        if panel["frequency_max"] > 1:
            panel["notes"].append(frequency_note(panel["frequency_max"]))

    elif kind == "bar":
        categories, names, records = normalize_records(
            data["categories"], data["series"], data.get("error_kind", "SEM")
        )
        comparisons = _pairwise(
            records,
            categories,
            names,
            pairwise_p=data.get("pairwise_p"),
            auto_test=data.get("auto_test"),
            pairs=data.get("pairs"),
            single=len(names) == 1,
        )
        records = _stack_records(records, categories, data.get("stack"))
        for record in records:
            record["interval_color"] = canvas.ink
        scale = scale_from(
            [
                v
                for r in records
                for v in [r["start"], r["value"], *([r["lo"], r["hi"]] if "lo" in r else []), *r["replicates"]]
            ],
            domain=data.get("value_domain"),
            zero=True,
        )
        cs = CategoryScale(categories)
        context = SeriesContext(names, pal=canvas.pal)
        horizontal = data.get("orientation", "vertical") == "horizontal"
        if data.get("orientation", "vertical") not in ("vertical", "horizontal"):
            raise ValueError("bar orientation must be vertical or horizontal")
        panel.update(
            categories=categories,
            records=records,
            context=context,
            entries=_entries(names, context.colors),
            axes={"x": scale if horizontal else cs, "y": cs if horizontal else scale},
            min_height=max(330, len(categories) * 40 + 80) if horizontal else 360,
        )
        panel["notes"].append(
            "Intervals: "
            + data.get("error_kind", "SEM")
            + " or explicitly supplied bounds; dots are observed replicates."
        )
        panel["notes"] += [str(c) for c in comparisons]
    elif kind == "swimmer":
        state = swimmer_state(data["patients"], canvas, data.get("time_domain"))
        panel.update(state=state, axes={"x": state["scale"]}, min_width=680)
        data.setdefault("x_unit", data.get("time_unit", "months"))
        panel["entries"] = _entries(state["treatments"], state["context"].colors)
        panel["entries"] += [
            {"name": kind, "color": state["context"].color_of("event:" + kind), "direction": "out"}
            for kind in state["kinds"]
        ]
        shapes = ("circle", "diamond", "triangle", "square")
        if state["kinds"]:
            panel["notes"].append(
                "Event shapes: "
                + "; ".join(kind + " = " + shapes[i % len(shapes)] for i, kind in enumerate(state["kinds"]))
            )
        if any(p.get("followup") is not None for p in state["patients"]):
            panel["notes"].append(tr("Dashed line: follow-up; arrow: ongoing at last observation."))
        panel["min_height"] = swimmer_height(
            state,
            canvas,
            panel["min_width"],
            all_event_lanes=bool(panel.get("x_group")),
            x_title=data.get("x_title", "Time from treatment start"),
            time_unit=data.get("time_unit", "months"),
        )
    else:
        rows = normalize_forest_rows(data["rows"], data.get("log_x", False))
        if data.get("row_order") is not None:
            order = list(map(str, data["row_order"]))
            if len(order) != len(rows) or set(order) != {r["row_id"] for r in rows}:
                raise ValueError("forest row_order must list every row_id once")
            rows = sorted(rows, key=lambda r: order.index(r["row_id"]))
        columns = normalize_columns(data.get("columns", [k for k in ("n", "p") if any(k in r for r in rows)]))
        values = [v for r in rows if r.get("estimate") is not None for v in (r["ci_lo"], r["ci_hi"])]
        ref = data.get("midline_value", 1)
        scale = scale_from([*values, ref], transform="log10" if data.get("log_x") else "linear")
        for column in columns:
            column["width"] = (
                max(
                    canvas.measure(column["label"], canvas.font_sizes["label"], True),
                    max(canvas.measure(_cell_text(r.get(column["key"])), canvas.font_sizes["label"]) for r in rows),
                )
                + 23
            )
        panel.update(
            rows=rows,
            columns=columns,
            axes={"x": scale},
            min_width=470 + sum(c["width"] for c in columns),
            min_height=max(340, len(rows) * 40 + 100),
        )
        panel["notes"].append(data.get("right_header_label", "Estimate (95% CI)"))
    if data.get("inset") is not None:
        if kind != "xy" or not isinstance(data["inset"], dict) or data["inset"].get("inset"):
            raise ValueError("inset requires one independent XY data record without nested insets")
        inset = data["inset"]
        panel["inset"] = _prepare(
            {"kind": "xy", "id": panel["id"] + "/inset", "name": inset.get("name", "Detail"), "data": inset},
            canvas,
            index,
        )
        panel["main_min_height"] = panel["min_height"]
        panel["min_width"] = max(panel["min_width"], 800)
        panel["min_height"] = max(panel["min_height"], 620)
    for axis in ("x", "y"):
        if panel.get(axis + "_group") and axis not in panel["axes"]:
            raise ValueError(f"{kind} has no shareable {axis} axis")
    panel["notes"] += list(map(str, data.get("annotations", [])))
    if "pvalue" in data:
        from ._chart_layout import p_label

        panel["notes"].append(p_label(data["pvalue"], ".4g"))
    return panel


def _share_axes(panels):
    groups = {}
    for panel in panels:
        for axis in ("x", "y"):
            group = panel.get(axis + "_group")
            if group:
                groups.setdefault((axis, str(group)), []).append(panel)
    for (axis, _), members in groups.items():
        scales = [p["axes"][axis] for p in members]
        units = {p["data"].get(axis + "_unit", "") for p in members} - {""}
        if (
            len(units) > 1
            or len({s.transform for s in scales}) > 1
            or len({isinstance(s, CategoryScale) for s in scales}) > 1
        ):
            raise ValueError("explicit axis group requires consistent units, transforms and coordinate types")
        if isinstance(scales[0], CategoryScale):
            scale = CategoryScale(list(dict.fromkeys(c for s in scales for c in s.categories)))
        else:
            scale = scale_from([v for s in scales for v in s.domain], transform=scales[0].transform)
        for panel in members:
            panel["axes"][axis] = scale


def _inset_space(panel, canvas, width):
    """Measure the independent inset strip before allocating its parent row."""
    inset = panel["inset"]
    canvas.font_sizes = inset.get("_fonts", canvas.font_sizes)
    header = (
        len(wrap_lines(inset["name"], (width - 20) / 1.05, canvas.font_sizes["label"], canvas.heading))
        * canvas.font_sizes["label"]
        * 1.35
        + 11
    )
    header += sum(
        len(wrap_lines(note, width - 20, canvas.font_sizes["foot"], canvas.font)) * canvas.font_sizes["foot"] * 1.35 + 3
        for note in inset["notes"]
    )
    return header + inset["min_height"] + 12


def _xy_panel(panel, canvas, body):
    inset_outer = None
    if panel.get("inset"):
        inset_height = panel.get("inset_height", _inset_space(panel, canvas, body.x1 - body.x0))
        inset_outer = BBox(body.x0, body.y1 - inset_height, body.x1, body.y1)
        body = BBox(body.x0, body.y0, body.x1, inset_outer.y0 - 24)
    canvas.font_sizes = panel.get("_fonts", canvas.font_sizes)
    data = panel["data"]
    xs, ys = panel["axes"]["x"], panel["axes"]["y"]
    series = deepcopy(panel["series"])
    if panel["kind"] == "volcano" and data.get("threshold") is not None:
        function, points = panel["threshold"]
        branches = _threshold_branches(
            function, *xs.domain, data.get("fc_threshold", 1), [p["fc"] for p in points], ys.domain[1]
        )
        for i, branch in enumerate(branches):
            if len(branch) > 1:
                series.append(
                    {
                        "name": f"Threshold {i + 1}",
                        "points": [],
                        "curve": branch,
                        "color": canvas.pal["ink6"],
                        "marker": "none",
                    }
                )
        context = series_context(series, canvas.pal)
    else:
        context = panel["context"]
    if isinstance(ys, RowScale):
        names = [item["name"] for item in series]
        local_context = SeriesContext(names, pal=canvas.pal, order=[name for name in context.order if name in names])
        local_context.colors.update(context.colors)
        context = local_context
    labels = [p["label"] for s in series for p in s["points"] if p.get("label")]
    yfmt = _axis_format(ys)[0]
    left = max(
        55,
        min(180, max((canvas.measure(yfmt(v), canvas.font_sizes["label"]) for v in ys.ticks or []), default=20) + 20),
    )
    rail = 150 if labels else 0
    if panel.get("_axis_gutters"):
        left, right_gutter = panel["_axis_gutters"]
        rail = right_gutter - 18
    xtext = heading(data.get("x_title", "X"), xs, data.get("x_unit", ""))
    ytext = heading(data.get("y_title", "Y"), ys, data.get("y_unit", ""))
    plot_w = body.x1 - body.x0 - left - rail - 18
    yh = len(wrap_lines(ytext, plot_w, canvas.font_sizes["label"], canvas.font)) * canvas.font_sizes["label"] * 1.35 + 9
    xh = (
        len(wrap_lines(xtext, plot_w, canvas.font_sizes["label"], canvas.font)) * canvas.font_sizes["label"] * 1.35 + 30
    )
    if isinstance(xs, CategoryScale):
        xh += (
            max(
                len(wrap_lines(c, plot_w / len(xs.categories) * 0.9, canvas.font_sizes["label"], canvas.font))
                for c in xs.categories
            )
            * canvas.font_sizes["label"]
            * 1.35
        )
    box = BBox(body.x0 + left, body.y0 + yh, body.x1 - rail - 18, body.y1 - xh)
    if panel.get("_row_plot_y"):
        box = BBox(box.x0, panel["_row_plot_y"][0], box.x1, panel["_row_plot_y"][1])
    label_box = BBox(box.x1 + 12, box.y0, body.x1, box.y1) if labels else None
    canvas.text(ytext, box.x0, body.y0, fs=canvas.font_sizes["label"], width=plot_w)
    canvas.parts.append(
        render_xy_plot(
            series,
            box,
            x_scale=xs,
            y_scale=ys,
            context=context,
            palette=canvas.pal,
            font_family=canvas.font,
            font_sizes=canvas.font_sizes,
            reference_lines=panel["refs"],
            phases=data.get("phases"),
            label_bbox=label_box,
            summary=data.get("summary", False),
            show_y_labels=not isinstance(ys, RowScale),
        )
    )
    if isinstance(ys, RowScale):
        for category in ys.categories:
            lines = wrap_lines(category, max(30, left - 15), canvas.font_sizes["label"], canvas.font)
            y = ys.map(category, box.y0, box.y1)
            canvas.parts.append(group_start("row-label", category=category))
            canvas.text(
                "\n".join(lines),
                box.x0 - 10,
                y - len(lines) * canvas.font_sizes["label"] * 0.675,
                fs=canvas.font_sizes["label"],
                anchor="end",
            )
            canvas.parts.append("</g>")
    canvas.text(
        xtext,
        (box.x0 + box.x1) / 2,
        (box.y1 if panel.get("_row_plot_y") else body.y1 - xh)
        + 32
        + (
            xh
            - 30
            - len(wrap_lines(xtext, plot_w, canvas.font_sizes["label"], canvas.font))
            * canvas.font_sizes["label"]
            * 1.35
        ),
        fs=canvas.font_sizes["label"],
        anchor="middle",
        width=plot_w,
    )
    anchors = {}
    if not isinstance(xs, CategoryScale) and not isinstance(ys, CategoryScale):
        for item in series:
            for point in item["points"]:
                identifier = point.get("id") or point.get("label")
                if (
                    identifier
                    and xs.domain[0] <= point["x"] <= xs.domain[1]
                    and ys.domain[0] <= point["y"] <= ys.domain[1]
                ):
                    key = ("point", str(identifier))
                    if key in anchors:
                        raise ValueError("XY connection point ids must be unique within a panel")
                    anchors[key] = (xs.map(point["x"], box.x0, box.x1), ys.map(point["y"], box.y1, box.y0), 3.6)
    protected = [tuple(label_box)] if label_box else []
    if panel.get("inset"):
        inset = panel["inset"]
        canvas.font_sizes = inset.get("_fonts", canvas.font_sizes)
        outer = inset_outer
        iw, ih = outer.x1 - outer.x0, outer.y1 - outer.y0
        canvas.parts.append(group_start("xy-inset", parent=panel["id"]))
        canvas.parts.append(
            f'<rect x="{outer.x0:.4f}" y="{outer.y0:.4f}" width="{iw:.4f}" height="{ih:.4f}" fill={quoteattr(canvas.pal.get("bg") or "#fff")} stroke={quoteattr(canvas.pal["ink4"])}/>'
        )
        top = outer.y0 + 8
        top += (
            canvas.text(inset["name"], outer.x0 + 10, top, fs=canvas.font_sizes["label"], bold=True, width=iw - 20) + 3
        )
        for note in inset["notes"]:
            top += canvas.text(note, outer.x0 + 10, top, fs=canvas.font_sizes["foot"], width=iw - 20) + 3
        inner = BBox(outer.x0 + 6, top, outer.x1 - 5, outer.y1 - 4)
        context_inset = _xy_panel(inset, canvas, inner)
        canvas.parts.append("</g>")
        protected.append(tuple(outer))
        panel["inset_layout"] = {
            "bbox": list(outer),
            "plot_bbox": list(context_inset["plot_bbox"]),
            "x_domain": inset["axes"]["x"].domain,
            "y_domain": inset["axes"]["y"].domain,
        }
    return {"plot_bbox": box, "anchors": anchors, "protected": protected}


def _matrix_panel(panel, canvas, body):
    state = panel["state"]
    panel["data"]
    labels = [state.row_labels[i] for i in state.row_order]
    row_w = min(180, max(canvas.measure(v, canvas.font_sizes["label"]) for v in labels) + 15)
    top_tree = 90 if "top" in state.trees else 0
    bottom_tree = 90 if "bottom" in state.trees else 0
    left_tree = 80 if "left" in state.trees else 0
    right = 80 if panel.get("line") is not None else 14
    plot_w = body.x1 - body.x0 - row_w - left_tree - right
    col_lines = [
        wrap_lines(state.col_labels[j], plot_w / state.nc - 5, canvas.font_sizes["foot"], canvas.font)
        for j in state.col_order
    ]
    col_h = max(len(v) for v in col_lines) * canvas.font_sizes["foot"] * 1.35 + 12
    box = BBox(body.x0 + row_w + left_tree, body.y0 + top_tree, body.x1 - right, body.y1 - col_h - bottom_tree)
    context = state.render(canvas, box)
    for label, y in zip(context.row_labels, context.row_centers):
        lines = wrap_lines(label, row_w - 12, canvas.font_sizes["label"], canvas.font)
        if len(lines) * canvas.font_sizes["label"] * 1.35 > (box.y1 - box.y0) / state.nr - 2:
            raise ValueError("matrix panel needs more height for row labels")
        canvas.text(
            "\n".join(lines),
            body.x0 + row_w - 10,
            y - len(lines) * canvas.font_sizes["label"] * 0.675,
            fs=canvas.font_sizes["label"],
            anchor="end",
        )
    for lines, x in zip(col_lines, context.column_centers):
        canvas.text("\n".join(lines), x, box.y1 + 8, fs=canvas.font_sizes["foot"], anchor="middle")
    for side, tree_box in [
        ("top", BBox(box.x0, body.y0, box.x1, body.y0 + 80)),
        ("bottom", BBox(box.x0, box.y1 + col_h, box.x1, body.y1)),
        ("left", BBox(box.x0 - 75, box.y0, box.x0 - 5, box.y1)),
    ]:
        if side in state.trees:
            _tree(canvas, state, side, tree_box, context.row_centers if side == "left" else context.column_centers)
    if panel.get("line") is not None:
        scale = panel["line_scale"]
        points = []
        for j, value in enumerate(panel["line"]):
            if value is None:
                points.append(None)
            else:
                points.append((context.column_centers[j], scale.map(value, box.y1, box.y0)))
        for i, point in enumerate(points):
            if point is not None:
                canvas.parts.append(_marker(*point, 3, "circle", canvas.ink, opacity=1, role="matrix-line-point"))
            if i and point is not None and points[i - 1] is not None:
                a = points[i - 1]
                d = f"M{a[0]:.4f},{a[1]:.4f} L{point[0]:.4f},{point[1]:.4f}"
                canvas.parts.append(
                    f'<path d="{d}" fill="none" stroke={quoteattr(canvas.pal.get("bg") or "#fff")} stroke-width="4"/><path d="{d}" fill="none" stroke={quoteattr(canvas.ink)} stroke-width="1.7"/>'
                )
        numeric_axis(canvas, box, scale, orientation="y", side="right")
    anchors = {("row", label): (box.x1, y, 0) for label, y in zip(context.row_labels, context.row_centers)}
    anchors.update({("column", label): (x, box.y0, 0) for label, x in zip(context.col_labels, context.column_centers)})
    return {"plot_bbox": box, "anchors": anchors, "row_order": context.row_order, "col_order": context.col_order}


def _pairs_panel(panel, canvas, body):
    data = panel["data"]
    canvas.font_sizes = chart_font_sizes(
        (body.x1 - body.x0 - 190) / len(panel["variables"]),
        (body.y1 - body.y0) / len(panel["variables"]),
        _panel_density(panel),
    )
    variables = panel["variables"]
    groups = panel["groups"]
    context = panel["context"]
    scales = panel["scales"]
    n = len(variables)
    labels = {v: str(data.get("variable_labels", {}).get(v, v)) for v in variables}
    label_w = min(160, max(85, max(canvas.measure(v, canvas.font_sizes["label"]) for v in labels.values())))
    gap = 26
    left = body.x0 + label_w + 30
    right = body.x1 - 12
    width = (right - left - gap * (n - 1)) / n
    header = (
        max(len(wrap_lines(v, width - 4, canvas.font_sizes["label"], canvas.font)) for v in labels.values())
        * canvas.font_sizes["label"]
        * 1.35
        + 12
    )
    bottom = body.y1 - 48
    top = body.y0 + header
    height = (bottom - top - gap * (n - 1)) / n
    anchors = {}
    for j, var in enumerate(variables):
        x = left + j * (width + gap)
        canvas.text(
            labels[var],
            x + width / 2,
            body.y0,
            fs=canvas.font_sizes["label"],
            bold=True,
            anchor="middle",
            width=width - 4,
        )
        annotation = _axis_format(scales[var])[1]
        if annotation:
            canvas.text(
                annotation, x + width / 2, bottom + 27, fs=canvas.font_sizes["foot"], anchor="middle", width=width
            )
    for i, yvar in enumerate(variables):
        y = top + i * (height + gap)
        label = heading(labels[yvar], scales[yvar])
        lines = wrap_lines(label, label_w, canvas.font_sizes["foot"], canvas.font)
        canvas.text(
            "\n".join(lines),
            body.x0 + label_w,
            y + height / 2 - len(lines) * canvas.font_sizes["foot"] * 0.675,
            fs=canvas.font_sizes["foot"],
            anchor="end",
        )
        anchors[("variable", str(yvar))] = (right, y + height / 2, 0)
        for j, xvar in enumerate(variables):
            x = left + j * (width + gap)
            box = BBox(x, y, x + width, y + height)
            xs, ys = scales[xvar], scales[yvar]
            canvas.parts.append(group_start("pairs-cell", x_variable=xvar, y_variable=yvar))
            canvas.parts.append(
                f'<rect x="{x:.4f}" y="{y:.4f}" width="{width:.4f}" height="{height:.4f}" fill="none" stroke={quoteattr(canvas.pal["grid"])} stroke-width=".7"/>'
            )
            series = _series(groups, xvar, yvar)
            if i == j:
                profiles = marginal_profiles(
                    series, "x", xs, data.get("diagonal", "hist"), data.get("bins", 12), data.get("bandwidth")
                )
                canvas.parts.append(
                    render_marginal(
                        profiles, BBox(x, y + 24, x + width, y + height), xs, context, kind=data.get("diagonal", "hist")
                    )
                )
                canvas.text(
                    tr("Count / bin") if data.get("diagonal", "hist") == "hist" else tr("Gaussian KDE"),
                    x + 7,
                    y + 6,
                    fs=10,
                )
                if i == n - 1:
                    numeric_axis(canvas, box, xs)
            elif i > j:
                if data.get("fit"):
                    series = fit_series(
                        normalize_series([dict(s, fit=data["fit"]) for s in series]),
                        show_ci=data.get("show_ci", True),
                        x_transform=xs.transform,
                        y_transform=ys.transform,
                    )
                if data.get("lower") == "density":
                    canvas.parts.append(
                        render_contours(
                            series, box, xs, ys, context, levels=data.get("contour_levels", (0.2, 0.5, 0.8))
                        )
                    )
                    series = [dict(s, marker="none") for s in series]
                display, glyph = frequency_display(
                    series,
                    context,
                    panel["frequency_max"],
                    font=canvas.font,
                    ink=canvas.ink,
                    paper=canvas.pal.get("bg") or "#FFFFFF",
                )
                canvas.parts.append(
                    render_xy_plot(
                        display,
                        box,
                        x_scale=xs,
                        y_scale=ys,
                        context=context,
                        palette=canvas.pal,
                        font_family=canvas.font,
                        font_sizes=canvas.font_sizes,
                        show_x_labels=i == n - 1,
                        show_y_labels=j == 0,
                        glyph_renderer=glyph,
                        size_max=panel["frequency_max"] if glyph else None,
                        radius_max=9,
                    )
                )
            else:
                canvas.text(
                    "Spearman ρ" if data.get("method") == "spearman" else "Pearson r",
                    x + width / 2,
                    y + 7,
                    fs=canvas.font_sizes["foot"],
                    anchor="middle",
                )
                for gi, (name, records) in enumerate(groups.items()):
                    value = correlation(
                        [transformed(r[xvar], xs) for r in records],
                        [transformed(r[yvar], ys) for r in records],
                        data.get("method", "pearson"),
                    )
                    canvas.parts.append(
                        f"<g {attrs(role='correlation-value', series=name, value='undefined' if value is None else value, n=len(records))}>"
                    )
                    canvas.text(
                        f"[{gi + 1}] " + ("undefined" if value is None else f"{value:+.2f}") + f" (n={len(records)})",
                        x + width / 2,
                        y + 30 + gi * 23,
                        fs=canvas.font_sizes["foot"],
                        anchor="middle",
                        color=context.color_of(name),
                    )
                    canvas.parts.append("</g>")
            canvas.parts.append("</g>")
    return {
        "plot_bbox": BBox(left, top, right, bottom),
        "anchors": anchors,
        "variable_domains": {str(v): scales[v].domain for v in variables},
    }


def _bar_panel(panel, canvas, body):
    data = panel["data"]
    horizontal = data.get("orientation", "vertical") == "horizontal"
    axes = panel["axes"]
    scale = axes["x" if horizontal else "y"]
    cs = axes["y" if horizontal else "x"]
    label_w = (
        min(180, max(canvas.measure(c, canvas.font_sizes["label"]) for c in cs.categories) + 18) if horizontal else 55
    )
    plot_w = body.x1 - body.x0 - label_w - 15
    label_lines = (
        [wrap_lines(c, plot_w / len(cs.categories) - 6, canvas.font_sizes["foot"], canvas.font) for c in cs.categories]
        if not horizontal
        else []
    )
    bottom_h = 52 + (max(len(v) for v in label_lines) * canvas.font_sizes["foot"] * 1.35 if label_lines else 0)
    value_heading = heading(
        data.get("x_title" if horizontal else "y_title", "Value"),
        scale,
        data.get("x_unit" if horizontal else "y_unit", ""),
    )
    heading_h = (
        len(wrap_lines(value_heading, plot_w, canvas.font_sizes["label"], canvas.font))
        * canvas.font_sizes["label"]
        * 1.35
        + 9
    )
    bottom_h = max(bottom_h, canvas.font_sizes["xtick"] * 1.35 + 20)
    box = BBox(body.x0 + label_w, body.y0 + heading_h, body.x1 - 15, body.y1 - bottom_h)
    if panel.get("_row_plot_y"):
        box = BBox(box.x0, panel["_row_plot_y"][0], box.x1, panel["_row_plot_y"][1])
    canvas.text(
        heading(
            data.get("x_title" if horizontal else "y_title", "Value"),
            scale,
            data.get("x_unit" if horizontal else "y_unit", ""),
        ),
        box.x0,
        body.y0,
        fs=canvas.font_sizes["label"],
        width=plot_w,
    )
    fragment, centers = render_categorical_plot(
        panel["records"],
        box,
        scale=scale,
        context=panel["context"],
        category_scale=cs,
        orientation=data.get("orientation", "vertical"),
        stack=data.get("stack"),
        show_points=data.get("show_points", True),
        point_color=canvas.ink,
        point_stroke=canvas.pal.get("bg") or "#fff",
    )
    canvas.parts.append(fragment)
    numeric_axis(canvas, box, scale, orientation="x" if horizontal else "y")
    for i, category in enumerate(cs.categories):
        if horizontal:
            y = cs.map(category, box.y0, box.y1)
            lines = wrap_lines(category, label_w - 15, canvas.font_sizes["label"], canvas.font)
            canvas.text(
                "\n".join(lines),
                box.x0 - 10,
                y - len(lines) * canvas.font_sizes["label"] * 0.675,
                fs=canvas.font_sizes["label"],
                anchor="end",
            )
        else:
            canvas.text(
                "\n".join(label_lines[i]),
                cs.map(category, box.x0, box.x1),
                box.y1 + 10,
                fs=canvas.font_sizes["foot"],
                anchor="middle",
            )
    anchors = {("row", r["row_id"]): (box.x1, c, 0) for r, c in zip(panel["records"], centers)} if horizontal else {}
    return {"plot_bbox": box, "anchors": anchors}


def _forest_panel(panel, canvas, body):
    data = panel["data"]
    rows = panel["rows"]
    scale = panel["axes"]["x"]
    columns = panel["columns"]
    for column in columns:
        column["width"] = (
            max(
                canvas.measure(column["label"], canvas.font_sizes["label"], True),
                max(canvas.measure(_cell_text(r.get(column["key"])), canvas.font_sizes["label"]) for r in rows),
            )
            + 23
        )
    label_w = min(210, max(canvas.measure(r.get("label", ""), canvas.font_sizes["label"]) for r in rows) + 14)
    table_w = sum(c["width"] for c in columns)
    box = BBox(
        body.x0 + label_w + 16,
        body.y0 + canvas.font_sizes["label"] * 1.35 + 8,
        body.x1 - table_w - 22,
        body.y1 - canvas.font_sizes["label"] * 2.7 - 24,
    )
    step = (box.y1 - box.y0) / len(rows)
    centers = [box.y0 + (i + 0.5) * step for i in range(len(rows))]
    for row, y in zip(rows, centers):
        lines = wrap_lines(row.get("label", row["row_id"]), label_w, canvas.font_sizes["label"], canvas.font)
        canvas.text(
            "\n".join(lines),
            body.x0,
            y - len(lines) * canvas.font_sizes["label"] * 0.675,
            fs=canvas.font_sizes["label"],
            bold=bool(row.get("is_overall") or row.get("is_subgroup_header")),
        )
    canvas.parts.append(
        render_table_plot(
            rows,
            BBox(box.x1 + 18, box.y0, body.x1, box.y1),
            columns=columns,
            centers=centers,
            layout=canvas,
            header_top=body.y0,
        )
    )
    series = normalize_series(
        [
            {
                "name": "Estimate",
                "points": [
                    {
                        "x": r["estimate"],
                        "y": len(rows) - i - 0.5,
                        "x_err": [r["estimate"] - r["ci_lo"], r["ci_hi"] - r["estimate"]],
                        "marker": "none" if r.get("is_overall") else "square",
                    }
                    for i, r in enumerate(rows)
                    if r.get("estimate") is not None
                ],
            }
        ]
    )
    ys = SharedScale((0, len(rows)), [])
    canvas.parts.append(
        render_xy_plot(
            series,
            box,
            x_scale=scale,
            y_scale=ys,
            palette=canvas.pal,
            font_family=canvas.font,
            font_sizes=canvas.font_sizes,
            show_y_labels=False,
            reference_lines=[{"axis": "x", "value": data.get("midline_value", 1)}],
        )
    )
    for row, y in zip(rows, centers):
        if row.get("is_overall") and row.get("estimate") is not None:
            lo, x, hi = [scale.map(row[k], box.x0, box.x1) for k in ("ci_lo", "estimate", "ci_hi")]
            canvas.parts.append(
                f'<path d="M{lo:.4f},{y:.4f} L{x:.4f},{y - 6:.4f} L{hi:.4f},{y:.4f} L{x:.4f},{y + 6:.4f} Z" fill={quoteattr(canvas.pal["accent"])} data-role="forest-diamond"/>'
            )
    canvas.text(
        heading(data.get("x_title", "Estimate"), scale, data.get("x_unit", "")),
        (box.x0 + box.x1) / 2,
        box.y1 + 33,
        fs=canvas.font_sizes["label"],
        anchor="middle",
        width=box.x1 - box.x0,
    )
    return {"plot_bbox": box, "anchors": {("row", r["row_id"]): (box.x1, y, 0) for r, y in zip(rows, centers)}}


def _render(panel, canvas, body):
    if panel.get("_row_gutters"):
        top, bottom = panel["_row_gutters"]
        panel["_row_plot_y"] = (body.y0 + top, body.y1 - bottom)
    canvas.font_sizes = panel.get("_fonts", canvas.font_sizes)
    kind = panel["kind"]
    data = panel["data"]
    if kind in ("xy", "volcano"):
        return _xy_panel(panel, canvas, body)
    if kind == "radar":
        return render_radar_panel(panel, canvas, body)
    if kind == "contour":
        return render_contour_panel(panel, canvas, body)
    if kind in ("violin", "boxplot", "raincloud"):
        from ._distribution_panels import render_distribution_panel

        return render_distribution_panel(panel, canvas, body)
    if kind == "heatmap":
        return _matrix_panel(panel, canvas, body)
    if kind == "pairs":
        return _pairs_panel(panel, canvas, body)
    if kind == "bar":
        return _bar_panel(panel, canvas, body)
    if kind == "forest":
        return _forest_panel(panel, canvas, body)
    if kind == "swimmer":
        return render_swimmer_plot(
            canvas,
            body,
            panel["state"],
            time_unit=data.get("time_unit", "months"),
            x_title=data.get("x_title", "Time from treatment start"),
            scale=panel["axes"]["x"],
        )
    size_nodes = panel["nodes"] if kind == "network" else panel["tree"]["nodes"]
    key_h = 44 if any(n.get("size") is not None for n in size_nodes) else 0
    box = BBox(body.x0, body.y0, body.x1, body.y1 - key_h - (34 if kind == "phylogeny" else 0))
    if kind == "network":
        context = render_network_plot(
            canvas,
            box,
            data["nodes"],
            data.get("edges", []),
            layout=data.get("layout", "force"),
            positions=data.get("positions"),
            tracks=data.get("tracks"),
        )
    else:
        context = render_phylogeny_plot(
            canvas,
            box,
            data["tree"],
            leaf_order=data.get("leaf_order"),
            tracks=data.get("tracks"),
            branch_mode=data.get("branch_mode", "auto"),
        )
        length = context["max_distance"] / 5
        if length:
            pixels = context["distance_scale"].map(length, 0, context["radius"])
            y = box.y1 + 10
            canvas.parts.append(
                f'<path d="M{box.x0 + 16:.4f},{y:.4f} h{pixels:.4f}" stroke={quoteattr(canvas.ink)} stroke-width="1.5"/>'
            )
            canvas.text(
                f"{length:.4g} " + ("edges" if context["branch_mode"] == "cladogram" else "branch-length units"),
                box.x0 + 25 + pixels,
                y - 7,
                fs=canvas.font_sizes["foot"],
            )
    if key_h:
        render_size_key(canvas, size_nodes, context["node_radii"], body.y1 - key_h, left=body.x0)
    return {
        "plot_bbox": box,
        "anchors": {
            ("node", key): (*point, context["node_radii"].get(key, 0)) for key, point in context["positions"].items()
        },
        "protected": context.get("protected_labels", []),
    }


def _connections(canvas, records, contexts, insert_at, bounds):
    if not records:
        return []
    positions = {}
    radii = {}
    raw = []
    metadata = []

    def endpoint(spec):
        if not isinstance(spec, dict) or not {"panel", "id"} <= set(spec):
            raise ValueError("connection endpoints require {panel, id, anchor?}")
        panel = str(spec["panel"])
        anchor = str(spec.get("anchor", "node"))
        identifier = str(spec["id"])
        if panel not in contexts or (anchor, identifier) not in contexts[panel]["anchors"]:
            raise ValueError(f"unknown connection anchor {panel}/{anchor}/{identifier}")
        name = panel + "/" + anchor + "/" + identifier
        x, y, r = contexts[panel]["anchors"][(anchor, identifier)]
        positions[name] = (x, y)
        radii[name] = r
        return name

    for record in records:
        source, target = endpoint(record["source"]), endpoint(record["target"])
        raw.append(dict(record, source=source, target=target))
    _, edges = normalize_network([{"id": name} for name in positions], raw)
    obstacles = [tuple(box[:4]) for box in canvas.text_boxes]
    for context in contexts.values():
        obstacles.extend(context.get("protected", []))
    obstacles = [
        Obstacle(
            ("panel-text", i),
            "polygon",
            ((box[0], box[1]), (box[2], box[1]), (box[2], box[3]), (box[0], box[3])),
            padding=2,
        )
        for i, box in enumerate(obstacles)
    ]
    segments = []
    routed_positions = {}
    routed_radii = {}
    for index, edge in enumerate(edges):
        start, end = positions[edge["source"]], positions[edge["target"]]
        reversed_route = start[0] > end[0]
        route = route_leader(
            end if reversed_route else start,
            start if reversed_route else end,
            obstacles,
            bounds,
            source_owner=("connection", index),
        )
        if reversed_route:
            route.reverse()
        metadata.append(
            {
                "source": edge["source"],
                "target": edge["target"],
                "route": route,
                "weight": edge.get("weight"),
                "correlation": edge.get("correlation"),
                "pvalue": edge.get("pvalue"),
            }
        )
        for j, point in enumerate(route):
            key = f"connection{index}/point{j}"
            routed_positions[key] = point
            routed_radii[key] = radii[edge["source"]] if j == 0 else radii[edge["target"]] if j == len(route) - 1 else 0
        for j in range(1, len(route)):
            segments.append(dict(edge, source=f"connection{index}/point{j - 1}", target=f"connection{index}/point{j}"))
    begin = len(canvas.parts)
    canvas.parts.append(group_start("panel-connections"))
    render_edges(canvas, segments, routed_positions, routed_radii)
    canvas.parts.append("</g>")
    rendered = canvas.parts[begin:]
    del canvas.parts[begin:]
    canvas.parts[insert_at:insert_at] = rendered
    return metadata


def make_panels(data, canvas, *, cols=None, **common):
    """Single-call heterogeneous panels; axes are independent without explicit groups."""
    envelope = {"panels": data} if isinstance(data, (list, tuple)) else data
    if not isinstance(envelope, dict) or not envelope.get("panels"):
        raise ValueError("panels data requires a nonempty panels list")
    panels = []
    for i, raw in enumerate(envelope["panels"]):
        if "detail_of" not in raw:
            panels.append(_prepare(raw, canvas, i))
            continue
        if any(k in raw for k in ("kind", "data", "x_group", "y_group")):
            raise ValueError("detail_of inherits kind/data; derived detail axes cannot join source axis groups")
        matches = [p for p in panels if p["id"] == str(raw["detail_of"])]
        if not matches or matches[0]["kind"] not in ("xy", "radar", "contour"):
            raise ValueError("detail_of must name an earlier XY, radar or contour panel")
        panel = deepcopy(matches[0])
        panel.update({k: deepcopy(v) for k, v in raw.items()})
        panel["id"] = str(raw.get("id", f"panel{i + 1}"))
        panel["name"] = str(raw.get("name", panel["id"]))
        for axis in ("x", "y"):
            panel.pop(axis + "_group", None)
            if axis + "_range" in raw:
                if panel["kind"] != "xy":
                    raise ValueError("data-range detail currently requires an XY source")
                domain = list(raw[axis + "_range"])
                if len(domain) != 2:
                    raise ValueError("detail range requires two bounds")
                original = panel["axes"][axis]
                scale = scale_from(domain, domain=domain, transform=original.transform)
                if scale.domain[0] < original.domain[0] or scale.domain[1] > original.domain[1]:
                    raise ValueError("detail range must lie inside its source domain")
                panel["axes"][axis] = scale
        panel["min_height"] = max(panel["min_height"] * 1.4, 500)
        panels.append(panel)
    if len({p["id"] for p in panels}) != len(panels):
        raise ValueError("panel ids must be unique")
    _share_axes(panels)
    for panel in panels:
        if "detail_of" in panel:
            source = next(p for p in panels if p["id"] == str(panel["detail_of"]))
            for axis in ("x", "y"):
                if axis in panel["axes"] and axis + "_range" not in panel:
                    panel["axes"][axis] = source["axes"][axis]
    radar_panels = [p for p in panels if p["kind"] == "radar"]
    if radar_panels:
        radar_names = list(dict.fromkeys(s["name"] for p in radar_panels for s in p["series"]))
        radar_context = SeriesContext(radar_names, pal=canvas.pal)
        explicit = {}
        for panel in radar_panels:
            for item in panel["series"]:
                if "color" in item:
                    if item["name"] in explicit and explicit[item["name"]] != item["color"]:
                        raise ValueError("one radar series must use the same color across panels")
                    explicit[item["name"]] = item["color"]
        radar_context.colors.update(explicit)
        for panel in radar_panels:
            panel["context"] = radar_context
            panel["entries"] = _entries([s["name"] for s in panel["series"]], radar_context.colors)
    if any(p["kind"] in ("violin", "boxplot", "raincloud") for p in panels):
        members = [p for p in panels if p["kind"] in ("xy", "radar", "violin", "boxplot", "raincloud")]
        names = list(dict.fromkeys(name for p in members for name in p["context"].ids))
        shared_colors = SeriesContext(names, pal=canvas.pal).colors
        explicit = {}
        for panel in members:
            provided = dict(panel["data"].get("group_colors", {}))
            provided.update({s["name"]: s["color"] for s in panel["data"].get("series", []) if s.get("color")})
            for name, color in provided.items():
                if name in explicit and explicit[name] != color:
                    raise ValueError("one shared group identity requires one explicit color")
                explicit[name] = color
        shared_colors.update(explicit)
        for panel in members:
            panel["context"].colors.update(shared_colors)
            for entry in panel["entries"]:
                if entry["name"] in shared_colors:
                    entry["color"] = shared_colors[entry["name"]]
    finalize_contours(panels, canvas)
    columns = cols or envelope.get("columns") or min(2, len(panels))
    if not isinstance(columns, int) or isinstance(columns, bool) or not 1 <= columns <= len(panels):
        raise ValueError("panels columns must be a positive integer no larger than the panel count")
    gap = 56 if envelope.get("connections") else 32
    min_width = max(p["min_width"] for p in panels)
    canvas.width = max(canvas.width, 56 + columns * min_width + (columns - 1) * gap)
    width = (canvas.width - 56 - (columns - 1) * gap) / columns
    outer_fonts = canvas.font_sizes
    top = canvas.header(common.get("title"), common.get("subtitle"), common.get("figure_label"))
    if envelope.get("connections"):
        top += (
            canvas.text(
                "Cross-panel associations use supplied weights/correlations and P values; no Mantel or enrichment test is inferred.",
                28,
                top,
                fs=canvas.font_sizes["foot"],
                width=canvas.width - 56,
            )
            + 10
        )
    positions = []
    row, col = 0, 0
    for panel in panels:
        span = panel.get("span", columns if "detail_of" in panel else 1)
        if not isinstance(span, int) or isinstance(span, bool) or not 1 <= span <= columns:
            raise ValueError("panel span must be an integer within the column count")
        if col + span > columns:
            row, col = row + 1, 0
        positions.append((row, col, span))
        panel["_width"] = width * span + gap * (span - 1)
        col += span
        if col == columns:
            row, col = row + 1, 0
    row_count = max(position[0] for position in positions) + 1
    available_panel_height = max(1, (canvas.height - top - 64 - (row_count - 1) * 34) / row_count)
    for panel in panels:
        panel["_font_height"] = max(panel["min_height"], available_panel_height)
        _panel_fonts(panel, canvas, panel["_width"])
    for panel in panels:
        canvas.font_sizes = panel["_fonts"]
        if panel.get("inset"):
            panel["inset_height"] = _inset_space(panel, canvas, panel["_width"])
            panel["min_height"] = max(panel["min_height"], panel["main_min_height"] + panel["inset_height"] + 24)
    gutter_groups = {}
    for panel in panels:
        canvas.font_sizes = panel["_fonts"]
        if not panel.get("x_group"):
            continue
        if panel["kind"] in ("violin", "boxplot", "raincloud"):
            from ._distribution_panels import distribution_gutters

            gutter = distribution_gutters(panel, canvas)
        elif panel["kind"] == "xy":
            ys = panel["axes"]["y"]
            fmt = _axis_format(ys)[0]
            left = max(
                55,
                min(
                    180,
                    max((canvas.measure(fmt(v), canvas.font_sizes["label"]) for v in ys.ticks or []), default=20) + 20,
                ),
            )
            labels = any(p.get("label") for s in panel["series"] for p in s["points"])
            gutter = (left, 168 if labels else 18)
        else:
            continue
        gutter_groups.setdefault((str(panel["x_group"]), panel["_width"]), []).append((panel, gutter))
    for members in gutter_groups.values():
        gutter = tuple(max(g[i] for _, g in members) for i in (0, 1))
        for panel, _ in members:
            panel["_axis_gutters"] = gutter
    for panel in panels:
        canvas.font_sizes = panel["_fonts"]
        if panel["kind"] in ("violin", "boxplot", "raincloud"):
            from ._distribution_panels import finalize_distribution_panel

            finalize_distribution_panel(panel, canvas, panel["_width"])
    for panel in panels:
        canvas.font_sizes = panel["_fonts"]
        width = panel["_width"]
        panel["legend_rows"], legend_h = legend_rows(canvas, panel["entries"], panel["rings"], width=width)
        title_h = (
            len(wrap_lines(panel["name"], width, canvas.font_sizes["group"], canvas.heading))
            * canvas.font_sizes["group"]
            * 1.35
            + 10
        )
        notes = [
            line for note in panel["notes"] for line in wrap_lines(note, width, canvas.font_sizes["foot"], canvas.font)
        ]
        panel["note_lines"] = notes
        panel["header_h"] = title_h + legend_h + len(notes) * canvas.font_sizes["foot"] * 1.35 + 18
        panel["legend_h"] = legend_h
        panel["title_h"] = title_h
    rows = max(pos[0] for pos in positions) + 1
    if any(
        p["kind"] in ("radar", "contour", "violin", "boxplot", "raincloud") or p.get("detail_of") or p.get("inset")
        for p in panels
    ):
        for row in range(rows):
            members = [p for p, pos in zip(panels, positions) if pos[0] == row]
            shared_header = max(p["header_h"] for p in members)
            for panel in members:
                panel["header_h"] = shared_header
    align_category_rows(panels, positions, canvas)
    row_heights = [
        max(p["min_height"] + p["header_h"] for p, pos in zip(panels, positions) if pos[0] == row)
        for row in range(rows)
    ]
    notes = [common.get("note"), common.get("source")]
    canvas.font_sizes = outer_fonts
    footer_h = (
        sum(
            len(wrap_lines(note, canvas.width - 56, canvas.font_sizes["foot"], canvas.font))
            * canvas.font_sizes["foot"]
            * 1.35
            for note in notes
            if note
        )
        + 45
    )
    canvas.height = max(canvas.height, top + sum(row_heights) + (rows - 1) * 34 + footer_h)
    extra = max(0, (canvas.height - top - sum(row_heights) - (rows - 1) * 34 - footer_h) / rows)
    row_heights = [height + extra for height in row_heights]
    contexts = {}
    summary = []
    insert_at = len(canvas.parts)
    for i, panel in enumerate(panels):
        canvas.font_sizes = panel["_fonts"]
        row, col, span = positions[i]
        cell_width = (canvas.width - 56 - (columns - 1) * gap) / columns
        width = panel["_width"]
        x = 28 + col * (cell_width + gap)
        y = top + sum(row_heights[:row]) + row * 34
        canvas.parts.append(group_start("heterogeneous-panel", panel_id=panel["id"], kind=panel["kind"]))
        canvas.text(panel["name"], x, y, fs=canvas.font_sizes["group"], bold=True, width=width)
        yy = y + panel["title_h"]
        render_legend(canvas, panel["legend_rows"], yy, left=x)
        yy += panel["legend_h"] + 5
        for line in panel["note_lines"]:
            canvas.text(line, x, yy, fs=canvas.font_sizes["foot"], color=canvas.pal["ink6"])
            yy += canvas.font_sizes["foot"] * 1.35
        body = BBox(x, y + panel["header_h"], x + width, y + row_heights[row])
        context = _render(panel, canvas, body)
        contexts[panel["id"]] = context
        canvas.parts.append("</g>")
        summary.append(
            {
                "id": panel["id"],
                "kind": panel["kind"],
                "body_bbox": list(body),
                "plot_bbox": list(context["plot_bbox"]),
                "axes": {
                    axis: {"domain": scale.domain, "transform": scale.transform, "group": panel.get(axis + "_group")}
                    for axis, scale in panel["axes"].items()
                },
                "anchors": {"/".join(key): list(point) for key, point in context["anchors"].items()},
                **({"detail_of": panel["detail_of"]} if "detail_of" in panel else {}),
                **({"inset": panel["inset_layout"]} if "inset_layout" in panel else {}),
            }
        )
    connection_records = list(envelope.get("connections", []))
    for panel in panels:
        if "detail_of" not in panel:
            continue
        source = next(p for p in panels if p["id"] == str(panel["detail_of"]))
        source_context, target_context = contexts[source["id"]], contexts[panel["id"]]
        source_box, target_box = source_context["plot_bbox"], target_context["plot_bbox"]
        region = source_box
        if panel["kind"] == "xy":
            xs, ys = source["axes"]["x"], source["axes"]["y"]
            dx, dy = panel["axes"]["x"].domain, panel["axes"]["y"].domain
            region = BBox(
                xs.map(dx[0], source_box.x0, source_box.x1),
                ys.map(dy[1], source_box.y1, source_box.y0),
                xs.map(dx[1], source_box.x0, source_box.x1),
                ys.map(dy[0], source_box.y1, source_box.y0),
            )
        canvas.parts.append(
            f'<rect x="{region.x0:.4f}" y="{region.y0:.4f}" width="{region.x1 - region.x0:.4f}" height="{region.y1 - region.y0:.4f}" fill="none" stroke={quoteattr(canvas.pal["ink6"])} stroke-dasharray="4 3" data-role="detail-source-region" data-source={quoteattr(source["id"])} data-target={quoteattr(panel["id"])}/>'
        )
        for side in ("left", "right"):
            key = panel["id"] + "/" + side
            source_context["anchors"][("detail", key)] = (region.x0 if side == "left" else region.x1, region.y1, 0)
            target_context["anchors"][("detail", key)] = (
                target_box.x0 if side == "left" else target_box.x1,
                target_box.y0,
                0,
            )
            connection_records.append(
                {
                    "source": {"panel": source["id"], "anchor": "detail", "id": key},
                    "target": {"panel": panel["id"], "anchor": "detail", "id": key},
                }
            )
    connections = _connections(
        canvas,
        connection_records,
        contexts,
        insert_at,
        BBox(20, top - 4, canvas.width - 20, canvas.height - footer_h + 12),
    )
    canvas.font_sizes = outer_fonts
    footer(canvas, *notes)
    serialize_layout(canvas, "heterogeneous-panels-layout", {"panels": summary, "connections": connections})
    return canvas.svg("Heterogeneous scientific panels with explicit axis groups and semantic connection anchors")
