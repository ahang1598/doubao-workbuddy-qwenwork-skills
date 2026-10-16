"""Plot-only sample distributions and independently scaled mirrored violins."""

from __future__ import annotations

import math
from xml.sax.saxutils import quoteattr

from .._common import _rgba_with_alpha
from .._typography import chart_font_sizes
from ._academic_rigor import BBox, SeriesContext, SharedScale
from ._chart_layout import ChartLayout, wrap_lines
from ._composition import attrs, footer, group_start, heading, numeric_axis, serialize_layout
from ._distribution import (
    Canvas,
    _draw_box,
    _observation_number,
    _observation_plan,
    axis_ticks,
    finite,
    kde,
    normalize_groups,
    p_label,
    quantile,
    resolve_tests,
    sample_domain,
    sample_stats,
)
from ._polar import legend_rows, render_legend
from ._xy import CategoryScale
from ._shared import tr

_VARIANTS = {
    "violin": (
        None,
        "classic",
        "boxplot_inner_flat",
        "quartile_outlined",
        "points_inner_flat",
        "half_gradient",
        "kde_only",
        "overlay",
    ),
    "boxplot": (
        None,
        "classic",
        "default_flat",
        "beeswarm",
        "notched_outlined",
        "variable_width_gradient",
        "strip_flat",
    ),
    "raincloud": (None, "classic"),
}


def prepare_distribution_panel(kind, data, canvas):
    """Normalize one distribution panel without creating a completed SVG."""
    if kind not in _VARIANTS or data.get("variant") not in _VARIANTS[kind]:
        raise ValueError(f"unsupported {kind} panel variant")
    orientation = data.get("orientation", "horizontal" if kind == "raincloud" else "vertical")
    if orientation not in ("vertical", "horizontal"):
        raise ValueError("distribution panel orientation must be vertical or horizontal")
    if data.get("conditions") is not None:
        raise ValueError("each distribution panel is one condition; pass conditions as separate panels")
    groups = normalize_groups(data["groups"])
    raw_groups = list(data["groups"].items()) if isinstance(data["groups"], dict) else data["groups"]
    colors = []
    for _, observations in raw_groups:
        colors.append(
            [
                str(p["color_group"]) if isinstance(p, dict) and p.get("color_group") is not None else None
                for p in observations
            ]
        )
    phases = list(dict.fromkeys(v for entries in colors for v in entries if v is not None))
    if phases and any(v is None for entries in colors for v in entries):
        raise ValueError("color_group must be present on every observation when used")
    if phases and data.get("variant") not in ("beeswarm", "strip_flat", None, "classic"):
        raise ValueError("color_group requires a variant that displays observations")
    if data.get("paired") and any(s is None for g in groups for s in g.subjects):
        raise ValueError("paired=True requires subject_id on every observation")
    if data.get("variant") == "overlay" and (len(groups) != 2 or data.get("paired")):
        raise ValueError("overlay requires two unpaired groups")
    density = kind != "boxplot"
    low, high = sample_domain(groups, data.get("y_min"), data.get("y_max"), data.get("bandwidth"), density)
    numeric = "x" if orientation == "horizontal" else "y"
    data.setdefault(numeric + "_unit", data.get("y_unit", ""))
    references = []
    for raw in data.get("reference_lines", []):
        reference = dict(raw)
        if reference.get("axis", numeric) != numeric:
            raise ValueError("distribution reference_lines must use the numeric axis")
        reference["value"] = finite(reference["value"], "reference value")
        references.append(reference)
        if data.get("y_min") is None:
            low = min(low, reference["value"])
        if data.get("y_max") is None:
            high = max(high, reference["value"])
        if not low <= reference["value"] <= high:
            raise ValueError("reference value must lie within the numeric domain")
    ticks, _, _ = axis_ticks((low, high))
    scale = SharedScale((low, high), ticks)
    names = [g.name for g in groups]
    context = SeriesContext(list(dict.fromkeys(names + phases)), pal=canvas.pal)
    context.colors.update(data.get("group_colors", {}))
    tests = resolve_tests(
        groups,
        data.get("academic", False),
        data.get("pairwise_p"),
        data.get("auto_test"),
        data.get("pairs"),
        paired=data.get("paired", False),
    )
    variant = data.get("variant")
    points = kind == "raincloud" or (
        data.get(
            "show_points",
            data.get("show_jitter", variant == "points_inner_flat" or kind == "boxplot" or data.get("paired", False)),
        )
        and variant not in ("kde_only", "quartile_outlined", "half_gradient", "overlay")
    )
    boxes = data.get("show_boxplot", True) and variant not in (
        "kde_only",
        "quartile_outlined",
        "half_gradient",
        "overlay",
        "strip_flat",
    )
    if phases and not points:
        raise ValueError("color_group requires visible observations")
    notes = ["; ".join(f"{g.name}: n={len(g.values)}" for g in groups) + tr(". Statistics use all raw observations.")]
    if density:
        notes.append(tr("KDE from observed samples; violin width is relative density within each group."))
    if boxes:
        notes.append(
            tr(
                "Box: Q1–Q3, median and Tukey whiskers; open dot: mean."
                if data.get("show_mean", True)
                else "Box: Q1–Q3, median and Tukey whiskers."
            )
        )
    notes += [str(r["label"]) for r in references if r.get("label")]
    legend_names = phases or names
    return {
        "groups": groups,
        "observation_colors": colors,
        "phases": phases,
        "context": context,
        "orientation": orientation,
        "density": density,
        "points_active": points,
        "boxes_active": boxes,
        "tests": tests,
        "refs": references,
        "axes": {numeric: scale, "y" if numeric == "x" else "x": CategoryScale(names)},
        "entries": [{"name": n, "color": context.color_of(n), "direction": "out"} for n in legend_names]
        if data.get("show_legend", True)
        else [],
        "notes": notes,
        "min_width": max(560, len(names) * 105 + 90) if orientation == "vertical" else 560,
        "min_height": 380,
    }


def distribution_gutters(panel, canvas):
    width = panel.get("_width", canvas.width)
    fonts = chart_font_sizes(width, panel.get("_font_height", canvas.height), len(panel["groups"]))
    fs = fonts["group"]
    if panel["orientation"] == "horizontal":
        return (max(55, min(width * 0.33, max(canvas.measure(g.name, fs) for g in panel["groups"]) + 18)), 18)
    _, labels, _ = axis_ticks(panel["axes"]["y"].domain)
    return (max(55, max(canvas.measure(v, fonts["ytick"]) for v in labels) + 18), 18)


def finalize_distribution_panel(panel, canvas, width):
    """Reserve count notes using the final shared domain and conservative geometry."""
    data = panel["data"]
    horizontal = panel["orientation"] == "horizontal"
    categories = panel["axes"]["y" if horizontal else "x"].categories
    fonts = chart_font_sizes(width, panel.get("_font_height", canvas.height), len(categories))
    panel["_fonts"] = fonts
    fs, axis_fs = fonts["group"], fonts["xaxis"]
    panel["_width"] = width
    left, right = panel.get("_axis_gutters", distribution_gutters(panel, canvas))
    panel["_axis_gutters"] = (left, right)
    names = [g.name for g in panel["groups"]]
    overlay = data.get("variant") == "overlay"
    count = 1 if overlay else len(categories)
    label_width = (
        panel.get("_category_label_width", max(30, left - 15)) if horizontal else (width - left - right) / count - 12
    )
    labels = [wrap_lines(name, label_width, fs, canvas.font) for name in categories]
    max_lines = max(map(len, labels))
    slot = (
        max(64 if panel["kind"] == "raincloud" else 52, max_lines * fs * 1.35 + 18)
        if horizontal
        else (width - left - right) / count
    )
    if horizontal and panel["points_active"]:
        slot = max(slot, min(160, math.sqrt(max(len(g.values) for g in panel["groups"])) * 12))
    if slot < 32:
        raise ValueError("distribution panels need more width for their categories")
    numeric_size = max(260, width - left - right) if horizontal else 260
    scale = panel["axes"]["x" if horizontal else "y"]
    phases = panel["phases"]
    plans = {}
    frequency_notes = []
    for i, group in enumerate(panel["groups"]):
        plans[i] = []
        if not panel["points_active"]:
            continue
        for phase_index, phase in enumerate(phases or [None]):
            indices = [j for j in range(len(group.values)) if not phases or panel["observation_colors"][i][j] == phase]
            if not indices:
                continue
            lane = slot * (0.14 if panel["kind"] == "raincloud" else 0.3)
            phase_slot = 2 * lane / max(1, len(phases))
            shift = (phase_index + 0.5) * phase_slot - lane if phases else 0
            lane = phase_slot * 0.45 if phases else lane
            values = [group.values[j] for j in indices]
            pixels = [scale.map(v, 0, numeric_size) for v in values]
            if data.get("variant") == "points_inner_flat" and not phases:
                density_x, density_y = kde(group.values, scale.domain, data.get("bandwidth"))
                peak = max(density_y)
                lane = [
                    max(
                        2.7,
                        density_y[min(range(len(density_x)), key=lambda j: abs(density_x[j] - value))]
                        / peak
                        * slot
                        * 0.30,
                    )
                    for value in values
                ]
            markers = _observation_plan(values, pixels, lane)
            for marker in markers:
                marker["indices"] = [indices[j] for j in marker["indices"]]
                marker["offset"] += shift
                marker["phase"] = phase
                plans[i].append(marker)
                if marker["kind"] != "raw":
                    label = group.name + (f" / {phase}" if phase else "")
                    count_text = tr("{n} observations", n=len(marker["indices"]))
                    if marker["kind"] == "frequency":
                        detail = f"{_observation_number(marker['value'])} × {count_text}"
                    else:
                        span = marker["high"] - marker["low"]
                        detail = tr(
                            "range [{low}, {high}], median {median}, {count}",
                            low=_observation_number(marker["low"], span),
                            high=_observation_number(marker["high"], span),
                            median=_observation_number(marker["value"], span),
                            count=count_text,
                        )
                    frequency_notes.append(tr("{label}: {detail}.", label=label, detail=detail))
    panel.setdefault("_finalize_base_notes", list(panel["notes"]))
    panel["notes"] = list(panel["_finalize_base_notes"])
    if frequency_notes:
        panel["notes"].append(
            tr("Dense dots preserve exact repeats or display-bin medians; full counts and measured ranges:")
        )
        panel["notes"] += frequency_notes
    panel["plans"] = plans
    panel["plan_slot"] = slot
    panel["labels"] = dict(zip(categories, labels))
    panel["min_height"] = (
        (slot * count if horizontal else 260)
        + axis_fs * 1.35
        + fs * 1.35
        + 50
        + (0 if horizontal else max_lines * fs * 1.35)
        + len(panel["tests"]) * (fonts["label"] * 1.35 + 14)
    )
    panel["min_height"] += (
        max(0, len(wrap_lines(str(data.get("y_title", tr("Value"))), width - left - right, axis_fs, canvas.font)) - 1)
        * axis_fs
        * 1.35
    )
    panel["group_order"] = names


def _mark_canvas(canvas):
    result = Canvas(canvas.width, canvas.height, canvas.pal, canvas.font)
    result.parts = canvas.parts
    result.ink = canvas.ink
    return result


def _draw_distribution_marks(panel, canvas, box, reverse=False):
    c = _mark_canvas(canvas)
    data, kind = panel["data"], panel["kind"]
    horizontal = panel["orientation"] == "horizontal"
    cs = panel["axes"]["y" if horizontal else "x"]
    numeric = panel["axes"]["x" if horizontal else "y"]
    overlay = data.get("variant") == "overlay"
    slot = ((box.y1 - box.y0) if horizontal else (box.x1 - box.x0)) / (1 if overlay else len(cs.categories))
    scale = lambda v: (
        numeric.map(v, box.x1 if reverse else box.x0, box.x0 if reverse else box.x1)
        if horizontal
        else numeric.map(v, box.y1, box.y0)
    )
    xy = lambda category, value: (value, category) if horizontal else (category, value)
    centers = [
        ((box.y0 + box.y1) / 2 if horizontal else (box.x0 + box.x1) / 2)
        if overlay
        else cs.map(g.name, box.y0 if horizontal else box.x0, box.y1 if horizontal else box.x1)
        for g in panel["groups"]
    ]
    anchors, coordinates = {}, []
    for index, group in enumerate(panel["groups"]):
        center = centers[index] + (slot * 0.24 if kind == "raincloud" else 0)
        points = [xy(center, scale(v)) for v in group.values]
        for marker in panel["plans"][index]:
            off = marker["offset"] * slot / panel["plan_slot"]
            for j in marker["indices"]:
                points[j] = xy(center + off, scale(group.values[j]))
        coordinates.append(points)
    if data.get("paired"):
        for i in range(len(panel["groups"]) - 1):
            a, b = panel["groups"][i : i + 2]
            first, second = dict(zip(a.subjects, coordinates[i])), dict(zip(b.subjects, coordinates[i + 1]))
            for identity in first.keys() & second.keys():
                c.line(
                    *first[identity],
                    *second[identity],
                    _rgba_with_alpha(c.ink, 0.2),
                    0.8,
                    attrs(role="paired-connection", subject_id=identity),
                )
    for index, group in enumerate(panel["groups"]):
        center, color = centers[index], panel["context"].color_of(group.name)
        stats = sample_stats(group.values)
        c.parts.append(
            group_start("distribution-group", group=group.name, count=len(group.values), median=stats["median"])
        )
        if panel["density"]:
            values, densities = kde(group.values, numeric.domain, data.get("bandwidth"))
            peak, half = max(densities) or 1, slot * 0.34
            if kind == "raincloud" or data.get("variant") == "half_gradient":
                outline = [(center - slot * 0.1 - d / peak * half, scale(v)) for v, d in zip(values, densities)]
                outline += [(center - slot * 0.1, scale(values[-1])), (center - slot * 0.1, scale(values[0]))]
            else:
                outline = [(center + d / peak * half, scale(v)) for v, d in zip(values, densities)] + [
                    (center - d / peak * half, scale(v)) for v, d in reversed(list(zip(values, densities)))
                ]
            dash = 'stroke-dasharray="5 4"' if overlay and index == 1 else ""
            fill = (
                "none"
                if data.get("variant") == "quartile_outlined" or (overlay and index == 1)
                else _rgba_with_alpha(color, 0.24)
            )
            if data.get("variant") == "half_gradient":
                gradient_id = f"distribution-panel-density-{len(c.parts)}"
                c.parts.append(
                    f'<defs><linearGradient id="{gradient_id}" x1="0" y1="0" x2="1" y2="0"><stop offset="0%" stop-color="{color}" stop-opacity="0.10"/><stop offset="100%" stop-color="{color}" stop-opacity="0.48"/></linearGradient></defs>'
                )
                fill = f"url(#{gradient_id})"
            c.path(
                [xy(*p) for p in outline],
                color,
                fill,
                1.7,
                True,
                f"{dash} {attrs(role='density', group=group.name)}",
            )
            if data.get("variant") == "quartile_outlined" or overlay:
                for probability in (0.25, 0.5, 0.75):
                    q = quantile(group.values, probability)
                    near = min(range(len(values)), key=lambda j: abs(values[j] - q))
                    h = densities[near] / peak * half
                    c.line(*xy(center - h, scale(q)), *xy(center + h, scale(q)), color, 1.3, dash)
        if panel["boxes_active"]:
            half = min(24, slot * (0.065 if panel["density"] else 0.18))
            if data.get("variant") == "variable_width_gradient":
                half *= math.sqrt(stats["n"] / max(len(g.values) for g in panel["groups"]))
            box_fill = "none" if data.get("variant") == "notched_outlined" else None
            if data.get("variant") == "variable_width_gradient":
                gradient_id = f"distribution-panel-box-{len(c.parts)}"
                c.parts.append(
                    f'<defs><linearGradient id="{gradient_id}" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="{color}" stop-opacity="0.52"/><stop offset="100%" stop-color="{color}" stop-opacity="0.12"/></linearGradient></defs>'
                )
                box_fill = f"url(#{gradient_id})"
            _draw_box(
                c,
                center,
                scale,
                stats,
                half,
                color,
                panel["orientation"],
                data.get("show_mean", True),
                data.get("variant") == "notched_outlined",
                attrs(role="box", group=group.name),
                fill=box_fill,
            )
        if panel["points_active"]:
            point_center = center + (slot * 0.24 if kind == "raincloud" else 0)
            for marker in panel["plans"][index]:
                n = len(marker["indices"])
                marker_color = panel["context"].color_of(marker["phase"]) if marker["phase"] is not None else color
                off = marker["offset"] * slot / panel["plan_slot"]
                c.circle(
                    *xy(point_center + off, scale(marker["value"])),
                    marker["radius"],
                    marker_color,
                    attrs(
                        role={"raw": "observation", "frequency": "observation-frequency", "bin": "observation-bin"}[
                            marker["kind"]
                        ],
                        count=n,
                        value=marker["value"],
                        low=marker["low"],
                        high=marker["high"],
                        color_group=marker["phase"] or group.name,
                    ),
                )
        elif panel["boxes_active"] and data.get("show_outliers", True):
            for value in group.values:
                if value < stats["lo"] or value > stats["hi"]:
                    c.circle(
                        *xy(center, scale(value)),
                        2.5,
                        c.bg,
                        f"stroke={quoteattr(color)} {attrs(role='outlier', value=value)}",
                    )
        anchors["group", group.name] = (*xy(center, scale(stats["median"])), 3)
        for j, identity in enumerate(group.subjects):
            if identity is not None:
                anchors["observation", group.name + "/" + identity] = (*coordinates[index][j], 2.5)
        c.parts.append("</g>")
    sig_fs = panel["_fonts"]["label"]
    for tier, (a, b, p) in enumerate(panel["tests"]):
        y = box.y0 - 18 - tier * (sig_fs * 1.35 + 14)
        if horizontal:
            canvas.text(
                f"{panel['groups'][a].name} vs {panel['groups'][b].name}: {p_label(p)}",
                box.x0,
                y - 12,
                fs=sig_fs,
                width=box.x1 - box.x0,
            )
        else:
            c.path([(centers[a], y + 4), (centers[a], y), (centers[b], y), (centers[b], y + 4)], c.ink, stroke=1)
            canvas.text(p_label(p), (centers[a] + centers[b]) / 2, y - sig_fs - 6, fs=sig_fs, anchor="middle")
    return anchors


def render_distribution_panel(panel, canvas, body):
    """Render marks/axes into an explicit body box; return semantic anchors."""
    if "plans" not in panel:
        finalize_distribution_panel(panel, canvas, body.x1 - body.x0)
    data = panel["data"]
    fonts = panel["_fonts"]
    fs, axis_fs = fonts["group"], fonts["xaxis"]
    horizontal = panel["orientation"] == "horizontal"
    axis = "x" if horizontal else "y"
    numeric, cs = panel["axes"][axis], panel["axes"]["y" if horizontal else "x"]
    left, right = panel["_axis_gutters"]
    hidden = panel.get("_hide_categories", False)
    max_lines = max(len(lines) for lines in panel["labels"].values())
    text = heading(
        data.get(axis + "_title", data.get("y_title", tr("Value"))),
        numeric,
        data.get(axis + "_unit", data.get("y_unit", "")),
    )
    plot_w = body.x1 - body.x0 - left - right
    text_h = max(panel.get("_heading_height", 0), len(wrap_lines(text, plot_w, axis_fs, canvas.font)) * axis_fs * 1.35)
    box = BBox(
        body.x0 + left,
        body.y0 + text_h + 15 + panel.get("_test_rows", len(panel["tests"])) * (fonts["label"] * 1.35 + 14),
        body.x1 - right,
        body.y1 - (fonts["xtick"] * 1.35 + 20 if horizontal else 25 + max_lines * fs * 1.35),
    )
    if box.y1 - box.y0 < 250 and not horizontal:
        raise ValueError("distribution panel requires more height")
    canvas.text(text, box.x0, body.y0, fs=axis_fs, width=plot_w)
    reverse = panel.get("_reverse_numeric", False)
    c = _mark_canvas(canvas)
    if reverse:
        ticks, labels, _ = axis_ticks(numeric.domain, max(2, min(6, int(plot_w / 80))))
        for value, label in zip(ticks, labels):
            x = numeric.map(value, box.x1, box.x0)
            c.line(x, box.y0, x, box.y1, canvas.pal["grid"], 0.7)
            canvas.text(label, x, box.y1 + 9, fs=fonts["xtick"], anchor="middle")
        c.line(box.x0, box.y1, box.x1, box.y1, canvas.pal["ink4"])
    else:
        numeric_axis(canvas, box, numeric, orientation=axis, grid=True, font_sizes=fonts)
    for reference in panel["refs"]:
        value = reference["value"]
        pixel = (
            numeric.map(value, box.x1 if reverse else box.x0, box.x0 if reverse else box.x1)
            if horizontal
            else numeric.map(value, box.y1, box.y0)
        )
        ends = (pixel, box.y0, pixel, box.y1) if horizontal else (box.x0, pixel, box.x1, pixel)
        c.line(
            *ends,
            reference.get("color", canvas.ink),
            1.2,
            'stroke-dasharray="4 4" ' + attrs(role="reference-line", value=value),
        )
    anchors = _draw_distribution_marks(panel, canvas, box, reverse)
    if not hidden and data.get("variant") != "overlay":
        for category in cs.categories:
            lines = panel["labels"][category]
            if horizontal:
                y = cs.map(category, box.y0, box.y1)
                canvas.text("\n".join(lines), box.x0 - 10, y - len(lines) * fs * 0.675, fs=fs, anchor="end")
            else:
                canvas.text("\n".join(lines), cs.map(category, box.x0, box.x1), box.y1 + 11, fs=fs, anchor="middle")
    return {"plot_bbox": box, "anchors": anchors}


def render_mirrored_distribution(
    groups,
    *,
    conditions,
    kind,
    variant,
    paired,
    academic,
    pairwise_p,
    auto_test,
    pairs,
    y_min,
    y_max,
    y_unit,
    y_title,
    bandwidth,
    title,
    subtitle,
    figure_label,
    note,
    source,
    width,
    height,
    palette,
    font_family,
    show_points,
    show_boxplot,
    show_mean,
    show_outliers,
    show_legend,
    highlight_group,
    per_group_n,
    effect_size,
    auto_effect,
):
    """Two independently scaled numeric variables, reversed left axis, central rows."""
    if kind != "violin" or conditions is None or len(conditions) != 2:
        raise ValueError("mirrored orientation requires violin conditions with exactly two named variables")
    if paired or effect_size or auto_effect or variant == "overlay" or per_group_n is not None:
        raise ValueError("mirrored violins use independent variables, without paired/effect/overlay/count overrides")
    canvas = ChartLayout(
        max(900, finite(width, "width")),
        max(400, finite(height, "height") if height is not None else 400),
        palette,
        font_family,
    )
    left_names = [g.name for g in normalize_groups(conditions[0][1])]
    normalized = []
    for name, raw in conditions:
        raw = list(raw.items()) if isinstance(raw, dict) else list(raw)
        if {str(k) for k, _ in raw} != set(left_names):
            raise ValueError("mirrored variables must contain identical category names")
        raw.sort(key=lambda item: left_names.index(str(item[0])))
        data = {
            "groups": raw,
            "variant": variant,
            "orientation": "horizontal",
            "academic": academic,
            "pairwise_p": pairwise_p.get(name) if isinstance(pairwise_p, dict) else pairwise_p,
            "auto_test": auto_test,
            "pairs": pairs,
            "y_min": y_min,
            "y_max": y_max,
            "y_unit": y_unit,
            "x_title": str(name),
            "bandwidth": bandwidth,
            "show_points": show_points,
            "show_boxplot": show_boxplot,
            "show_mean": show_mean,
            "show_outliers": show_outliers,
        }
        panel = {"kind": "violin", "data": data, "name": str(name)}
        panel.update(prepare_distribution_panel("violin", data, canvas))
        normalized.append(panel)
    center_fonts = chart_font_sizes((canvas.width - 56) / 2, canvas.height, len(left_names))
    fs = center_fonts["group"]
    foot_fs = center_fonts["foot"]
    center_w = min(300, max(160, max(canvas.measure(n, fs) for n in left_names) + 30))
    side_w = (canvas.width - 56 - center_w) / 2
    for panel in normalized:
        panel.update(_axis_gutters=(18, 18), _hide_categories=True, _category_label_width=center_w - 16)
        finalize_distribution_panel(panel, canvas, side_w)
    heading_height = max(
        len(wrap_lines(p["name"], side_w - 36, p["_fonts"]["xaxis"], canvas.font)) * p["_fonts"]["xaxis"] * 1.35
        for p in normalized
    )
    for panel in normalized:
        panel["_heading_height"] = heading_height
        panel["_test_rows"] = max(len(p["tests"]) for p in normalized)
    normalized[0]["_reverse_numeric"] = True
    top = canvas.header(title, subtitle, figure_label)
    if show_legend:
        rows, legend_h = legend_rows(canvas, normalized[0]["entries"], [], width=canvas.width - 56)
        render_legend(canvas, rows, top, left=28)
        top += legend_h + 12
    all_notes = []
    for panel in normalized:
        all_notes += [panel["name"] + ": " + n for n in panel["notes"]]
    for content in all_notes:
        top += canvas.text(content, 28, top, fs=foot_fs, color=canvas.pal["ink6"], width=canvas.width - 56) + 3
    label_h = max(len(wrap_lines(n, center_w - 16, fs, canvas.font)) for n in left_names) * fs * 1.35 + 20
    body_h = max(max(p["min_height"] for p in normalized), len(left_names) * label_h + 92)
    notes_h = (
        sum(
            len(wrap_lines(str(v), canvas.width - 56, foot_fs, canvas.font)) * foot_fs * 1.35
            for v in (note, source)
            if v
        )
        + 40
    )
    canvas.height = max(canvas.height, top + body_h + notes_h)
    body_h = canvas.height - top - notes_h
    contexts = []
    for i, panel in enumerate(normalized):
        x = 28 if i == 0 else 28 + side_w + center_w
        canvas.parts.append(
            group_start(
                "mirrored-variable",
                side="left" if i == 0 else "right",
                variable=panel["name"],
                domain=panel["axes"]["x"].domain,
            )
        )
        contexts.append(render_distribution_panel(panel, canvas, BBox(x, top, x + side_w, top + body_h)))
        canvas.parts.append("</g>")
    box = contexts[0]["plot_bbox"]
    other = contexts[1]["plot_bbox"]
    if abs(box.y0 - other.y0) > 0.01:
        raise ValueError("mirrored variable titles need matching line counts; increase width")
    for name in left_names:
        y = normalized[0]["axes"]["y"].map(name, box.y0, box.y1)
        lines = wrap_lines(name, center_w - 16, fs, canvas.font)
        canvas.text(
            "\n".join(lines),
            canvas.width / 2,
            y - len(lines) * fs * 0.675,
            fs=fs,
            anchor="middle",
            bold=name == highlight_group,
        )
    footer(canvas, note, source)
    serialize_layout(
        canvas,
        "mirrored-distribution-layout",
        {
            "variables": [
                {
                    "name": p["name"],
                    "domain": p["axes"]["x"].domain,
                    "reversed": i == 0,
                    "plot_bbox": list(contexts[i]["plot_bbox"]),
                }
                for i, p in enumerate(normalized)
            ],
            "categories": left_names,
        },
    )
    return canvas.svg("Mirrored violins with independent numeric axes and shared central category labels")
