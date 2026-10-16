"""Validated categorical summaries and shared plot-only bar rendering."""

from __future__ import annotations

import math
from xml.sax.saxutils import quoteattr

from ._academic_rigor import BBox, SeriesContext, SharedScale, pairwise_test, student_t_critical
from ._chart_layout import (
    ChartLayout,
    finite,
    p_label as _p_label,
    parse_p,
    wrap_lines,
    precise_number,
    uniform_value_labels,
)
from ._composition import attrs, footer, heading, numeric_axis, render_bar_plot, scale_from
from ._xy import CategoryScale, _axis_format, _marker, _text, normalize_series, render_xy_plot
from ._shared import has_cjk, tr


def sample_summary(values, error_kind):
    values = [finite(v, "replicate") for v in values]
    if not values:
        raise ValueError("replicates must be non-empty; use None for a missing cell")
    if len(values) == 1:
        if error_kind == "CI95":
            raise ValueError("CI95 requires at least two observations")
        return {"value": values[0], "n": 1, "replicates": values}
    # Center before scaling to retain small differences on a large offset.
    origin = values[0]
    shifts = [v - origin for v in values]
    if all(math.isfinite(v) for v in shifts):
        mean = origin + math.fsum(v / len(values) for v in shifts)
        differences = [v - mean for v in values]
        magnitude = max(map(abs, differences)) or 1.0
        scaled = [v / magnitude for v in differences]
    else:
        # Opposite near-limit values can overflow subtraction despite finite
        # observations; this branch scales before centering instead.
        magnitude = max(map(abs, values)) or 1.0
        scaled_values = [v / magnitude for v in values]
        scaled_mean = math.fsum(scaled_values) / len(values)
        mean = scaled_mean * magnitude
        scaled = [v - scaled_mean for v in scaled_values]
    sd = math.sqrt(math.fsum(v * v for v in scaled) / (len(values) - 1)) * magnitude
    error = sd if error_kind == "SD" else sd / math.sqrt(len(values))
    if error_kind == "CI95":
        error *= student_t_critical(len(values) - 1)
    return {
        "value": mean,
        "sd": sd,
        "lo": mean - error,
        "hi": mean + error,
        "n": len(values),
        "replicates": values,
        "interval_kind": error_kind,
    }


def normalize_cell(cell, error_kind):
    if error_kind not in ("SD", "SEM", "CI95"):
        raise ValueError("error_kind must be SD, SEM or CI95")
    if cell is None:
        return None
    if not isinstance(cell, dict):
        if not isinstance(cell, (tuple, list)):
            raise TypeError("a cell must be replicates, a summary dictionary, or None")
        return sample_summary(cell, error_kind)
    cell = dict(cell)
    if "replicates" in cell:
        if any(k in cell for k in ("value", "mean", "lo", "hi", "sd", "sem", "ci95")):
            raise ValueError("replicates and summary fields are mutually exclusive")
        return dict(cell, **sample_summary(cell["replicates"], error_kind))
    if ("value" in cell) == ("mean" in cell):
        raise ValueError("summary needs exactly one of value or mean")
    value = finite(cell.get("value", cell.get("mean")), "summary value")
    out = dict(cell, value=value, replicates=[])
    if "n" in cell:
        n = finite(cell["n"], "n", minimum=1)
        if not n.is_integer():
            raise ValueError("n must be an integer")
        out["n"] = int(n)
    if ("lo" in cell) != ("hi" in cell):
        raise ValueError("summary interval requires both lo and hi")
    if "lo" in cell:
        if any(k in cell for k in ("sd", "sem", "ci95")):
            raise ValueError("supply lo/hi or a dispersion field, not both")
        lo, hi = finite(cell["lo"], "lo"), finite(cell["hi"], "hi")
    else:
        fields = [k for k in ("sd", "sem", "ci95") if k in cell]
        if len(fields) > 1:
            raise ValueError("supply one summary dispersion field")
        if not fields:
            return out
        field = fields[0]
        error = finite(cell[field], field, minimum=0)
        if field == "sd" and error_kind in ("SEM", "CI95"):
            if out.get("n", 0) < 2:
                raise ValueError("SD conversion to SEM/CI95 requires n >= 2")
            error /= math.sqrt(out["n"])
        elif field != error_kind.lower():
            raise ValueError("summary dispersion field must match error_kind (or supply SD and n)")
        if field == "sd" and error_kind == "CI95":
            error *= student_t_critical(out["n"] - 1)
        lo, hi = value - error, value + error
    if not lo <= value <= hi:
        raise ValueError("summary interval must satisfy lo <= value <= hi")
    out.update(lo=lo, hi=hi, interval_kind="supplied lo/hi" if "lo" in cell else error_kind)
    return out


def interval_kind_label(kind, ci_level=None):
    """Reader-facing name of an interval kind; internal tags never reach the figure."""
    if kind == "supplied lo/hi":
        if ci_level is not None:
            return tr("{level}% CI", level=precise_number(finite(ci_level, "ci_level")))
        return tr("Interval")
    if kind == "CI95":
        return tr("{level}% CI", level="95")
    return str(kind)


def interval_note_text(records, error_kind, ci_level=None):
    kinds = sorted(
        {
            interval_kind_label(r.get("interval_kind", error_kind), r.get("ci_level", ci_level))
            for r in records
            if "lo" in r
        }
    )
    if not kinds:
        return None
    if kinds == [tr("Interval")]:
        # Level not stated: say what the whiskers are without inventing a confidence level.
        return tr("Whiskers: reported lower–upper bounds")
    return tr("Intervals: ") + " / ".join(kinds)


def normalize_records(categories, series, error_kind="SEM"):
    categories = [str(v) for v in categories]
    if not categories or len(set(categories)) != len(categories):
        raise ValueError("categories must be non-empty and unique")
    names, records = [], []
    for raw in series:
        if isinstance(raw, dict):
            name, cells = str(raw["name"]), raw["values"]
        else:
            name, cells = str(raw[0]), raw[1]
        if name in names:
            raise ValueError("series names must be unique")
        if len(cells) != len(categories):
            raise ValueError("every series must have one cell per category")
        names.append(name)
        for category, cell in zip(categories, cells):
            stat = normalize_cell(cell, error_kind)
            if stat is not None:
                records.append(dict(stat, category=category, name=name, row_id=str(stat.get("row_id", category))))
    if not records:
        raise ValueError("at least one non-missing cell is required")
    return categories, names, records


LOG_AUTO_RATIO = 30.0


def resolve_value_scale(value_scale, records, *, axis_break=None, stack=None, line_series=None, value_domain=None):
    """True when bars should use a log10 value axis."""
    if value_scale not in ("auto", "linear", "log"):
        raise ValueError("value_scale must be 'auto', 'linear' or 'log'")
    if value_scale == "linear":
        return False
    values = [v for r in records for v in [r["value"], *([r["lo"], r["hi"]] if "lo" in r else []), *r["replicates"]]]
    plain = stack in (None, "none") and axis_break is None and not line_series
    if value_scale == "log":
        if not plain:
            raise ValueError("value_scale='log' cannot be combined with stacking, an axis break or a line overlay")
        if any(v <= 0 for v in values) or (value_domain is not None and min(value_domain) <= 0):
            raise ValueError("value_scale='log' requires every value, interval and domain bound to be > 0")
        return True
    if not plain or value_domain is not None or not values or min(values) <= 0:
        return False
    return max(values) / min(values) > LOG_AUTO_RATIO


def log_axis_title(title):
    marker = tr("log scale")
    title = str(title or "")
    if marker in title or "对数" in title or "log" in title.lower():
        return title
    return f"{title}（{marker}）" if title and has_cjk([title]) else (f"{title} ({marker})" if title else marker)


class BrokenScale(SharedScale):
    """Two visible numerical intervals with a fixed pixel gap between them."""

    def __init__(self, base, axis_break, gap=18):
        a, b = (finite(v, "axis_break") for v in axis_break)
        if not base.domain[0] < a < b < base.domain[1]:
            raise ValueError("axis_break must lie strictly inside the value domain")
        super().__init__(base.domain, sorted(set([v for v in base.ticks if not a < v < b] + [a, b])))
        self.visible_intervals = [(base.domain[0], a), (b, base.domain[1])]
        self.gap = gap

    def map(self, value, p0, p1):
        a, b = self.visible_intervals[0][1], self.visible_intervals[1][0]
        if a < value < b:
            raise ValueError("value is inside the omitted axis interval")
        low, high = self.domain
        fraction = ((value - low) if value <= a else (value - low - (b - a))) / (high - low - (b - a))
        direction = 1 if p1 > p0 else -1
        return p0 + direction * (fraction * (abs(p1 - p0) - self.gap) + (self.gap if value >= b else 0))


def _stack_records(records, categories, stack):
    if stack not in (None, "none", "stacked", "percent"):
        raise ValueError("stack must be none, stacked or percent")
    if stack in (None, "none"):
        return [dict(r, start=0.0) for r in records]
    totals = {c: math.fsum(r["value"] for r in records if r["category"] == c) for c in categories}
    if stack == "percent" and any(r["value"] < 0 for r in records):
        raise ValueError("percent stacks require non-negative values")
    if stack == "percent" and any(t <= 0 for t in totals.values()):
        raise ValueError("every percent stack must have a positive total; missing is not zero")
    positive, negative, out = {}, {}, []
    for raw in records:
        r = dict(raw)
        c, amount = r["category"], r["value"]
        factor = 100 / totals[c] if stack == "percent" else 1
        amount *= factor
        accum = negative if amount < 0 else positive
        start = accum.get(c, 0.0)
        r.update(start=start, value=start + amount, amount=amount)
        for key in ("lo", "hi"):
            if key in r:
                r[key] = start + r[key] * factor
        r["replicates"] = [start + v * factor for v in r["replicates"]]
        accum[c] = r["value"]
        out.append(r)
    return out


def render_categorical_plot(
    records,
    bbox,
    *,
    scale,
    context,
    category_scale,
    orientation="vertical",
    stack=None,
    show_points=True,
    point_color="#283340",
    point_stroke="#FFFFFF",
):
    """Plot-only bars sharing authoritative numeric/category scales and colors."""
    box = BBox(*bbox)
    horizontal = orientation == "horizontal"
    start, end = (box.y0, box.y1) if horizontal else (box.x0, box.x1)
    categories = category_scale.categories
    names = [name for name in context.ids if any(r["name"] == name for r in records)]
    slot = (end - start) / len(categories)
    grouped = stack in (None, "none")
    thickness = min(66, slot * 0.72 / (len(names) if grouped else 1))
    centers = []
    for record in records:
        offset = (names.index(record["name"]) - (len(names) - 1) / 2) * thickness if grouped else 0
        centers.append(category_scale.map(record["category"], start, end) + offset)
    parts = [
        render_bar_plot(
            records,
            box,
            scale=scale,
            colors=context.colors,
            orientation=orientation,
            centers=centers,
            thickness=thickness * 0.90,
        )
    ]
    if show_points:
        for r, center in zip(records, centers):
            # A single observation *is* the bar end; a dot there is a stray mark, not evidence.
            if len(r["replicates"]) < 2:
                continue
            for i, value in enumerate(r["replicates"]):
                if hasattr(scale, "visible_intervals") and not any(a <= value <= b for a, b in scale.visible_intervals):
                    continue
                jitter = (((i * 0.61803398875) % 1) - 0.5) * thickness * 0.64
                coord = scale.map(value, box.x0, box.x1) if horizontal else scale.map(value, box.y1, box.y0)
                x, y = (coord, center + jitter) if horizontal else (center + jitter, coord)
                parts.append(
                    _marker(
                        x,
                        y,
                        2.3,
                        "circle",
                        point_color,
                        opacity=0.9,
                        stroke_color=point_stroke,
                        role="replicate",
                        attrs=attrs(value=value, row_id=r["row_id"]),
                    )
                )
    return "".join(parts), centers


def _legend(layout, names, context, top, line_names=()):
    fs = layout.font_sizes["legend"]
    x = 28
    for name in names:
        width = min(layout.width - 56, layout.measure(name, fs) + 34)
        if x + width > layout.width - 28:
            x = 28
            top += 27
        if name in line_names:
            layout.parts.append(
                f'<path d="M{x},{top + 7} h18" stroke={quoteattr(context.color_of(name))} stroke-width="2"/>'
            )
        else:
            layout.parts.append(
                f'<rect x="{x}" y="{top + 1}" width="14" height="12" fill={quoteattr(context.color_of(name))}/>'
            )
        h = layout.text(name, x + 22, top, fs=fs, width=width - 24)
        x += width
        if h > 22:
            x = 28
            top += h + 7
    return top + 34


def _pairwise(records, categories, names, *, pairwise_p, auto_test, pairs, single):
    if pairwise_p is not None and (auto_test is not None or pairs is not None):
        raise ValueError("pairwise_p and auto_test/pairs are mutually exclusive")
    if (auto_test is None) != (pairs is None):
        raise ValueError("auto_test and pairs must be supplied together")
    comparisons = []
    lookup = {(r["category"], r["name"]): r for r in records}
    if auto_test:
        from ._academic_rigor import _PAIRWISE_TESTS

        if auto_test not in _PAIRWISE_TESTS:
            raise ValueError("unknown automatic test")
        for c in [None] if single else categories:
            cells = (
                [lookup.get((category, names[0])) for category in categories]
                if single
                else [lookup.get((c, n)) for n in names]
            )
            if any(not r or not r["replicates"] for r in cells):
                raise ValueError("automatic tests require actual replicates in every compared cell")
            vals = [r["replicates"] for r in cells]
            if isinstance(pairs, str):
                result = pairwise_test(vals, method=auto_test, pair_strategy=pairs)
            else:
                result = []
                for a, b in pairs:
                    if not 0 <= a < len(vals) or not 0 <= b < len(vals) or a == b:
                        raise ValueError("comparison indices must identify different existing groups")
                    result.append((a, b, _PAIRWISE_TESTS[auto_test](vals[a], vals[b])))
            comparisons.extend((None if single else categories.index(c), a, b, p) for a, b, p in result)
    elif pairwise_p is not None:
        comparisons = [p if isinstance(p, dict) else (None, *p) for p in pairwise_p] if single else list(pairwise_p)
    result = []
    for comparison in comparisons:
        if isinstance(comparison, dict):
            if set(comparison) != {"a", "b", "p"}:
                raise ValueError("comparison records need a, b and p")
            references = []
            for key in ("a", "b"):
                ref = comparison[key]
                if not isinstance(ref, (list, tuple)) or len(ref) != 2:
                    raise ValueError("comparison endpoints must be [category, series] references")
                record = lookup.get((str(ref[0]), str(ref[1])))
                if record is None:
                    raise ValueError("comparisons cannot reference missing cells")
                references.append(records.index(record))
            if references[0] == references[1]:
                raise ValueError("comparison endpoints must identify different cells")
            result.append((*references, parse_p(comparison["p"], "P")))
            continue
        c, a, b, p = comparison
        maximum = len(categories) if single else len(names)
        if any(isinstance(i, bool) or not isinstance(i, int) or not 0 <= i < maximum for i in (a, b)) or a == b:
            raise ValueError("comparison indices must identify different existing groups")
        if not single:
            if not isinstance(c, int) or not 0 <= c < len(categories):
                raise ValueError("comparison category index is invalid")
            c = categories[c]
        p = parse_p(p, "P")
        ra = lookup.get((categories[a], names[0])) if single else lookup.get((c, names[a]))
        rb = lookup.get((categories[b], names[0])) if single else lookup.get((c, names[b]))
        if ra is None or rb is None:
            raise ValueError("comparisons cannot reference missing cells")
        result.append((records.index(ra), records.index(rb), p))
    return result


def normalize_reference_lines(reference_lines, log_axis=False):
    """``[{"value": 1, "label": "无富集 (=1)"}]`` or ``(value, label)`` pairs on the value axis."""
    out = []
    for ref in reference_lines or []:
        ref = ref if isinstance(ref, dict) else {"value": ref[0], "label": ref[1] if len(ref) > 1 else ""}
        value = finite(ref.get("value"), "reference_lines value")
        if log_axis and value <= 0:
            raise ValueError("reference_lines on a log value axis must be > 0")
        out.append({"value": value, "label": str(ref.get("label") or ""), "color": ref.get("color")})
    return out


def draw_reference_line(layout, ref, x0, y0, x1, y1, label_xy=None, fs=None, anchor="start", avoid=()):
    """Axis-parallel dashed line; it breaks around ``avoid`` boxes (value labels) instead of crossing them."""
    color = ref["color"] or layout.pal["ink6"]
    vertical = abs(x1 - x0) < 1e-9
    fixed, a, b = (x0, y0, y1) if vertical else (y0, x0, x1)
    blocked = sorted(
        (by0 - 2, by1 + 2) if vertical else (bx0 - 2, bx1 + 2)
        for bx0, by0, bx1, by1 in avoid
        if (bx0 <= fixed <= bx1 if vertical else by0 <= fixed <= by1)
    )
    runs, cursor = [], a
    for lo, hi in blocked:
        if lo > cursor:
            runs.append((cursor, min(lo, b)))
        cursor = max(cursor, hi)
    if cursor < b:
        runs.append((cursor, b))
    d = " ".join(
        f"M{fixed:.3f},{p:.3f} V{q:.3f}" if vertical else f"M{p:.3f},{fixed:.3f} H{q:.3f}" for p, q in runs if q > p
    )
    layout.parts.append(
        f'<path d="{d}" fill="none" stroke={quoteattr(color)} '
        f'stroke-width="1.2" stroke-dasharray="5 4" {attrs(role="reference-line", value=ref["value"])}/>'
    )
    if ref["label"] and label_xy:
        layout.parts.append(
            _text(
                ref["label"], *label_xy, layout.font, layout.pal["ink6"], fs=fs, anchor=anchor, role="reference-label"
            )
        )


def _value_text(svg, record, summary_values):
    """Summary views expose which cell each value label belongs to."""
    if not summary_values:
        return svg
    return svg.replace(
        'data-role="bar-value"',
        f'data-role="bar-value-label" {attrs(series=record["name"], category=record["category"], value=record["value"])}',
        1,
    )


def make_categorical(
    categories,
    series,
    *,
    orientation="vertical",
    stack=None,
    axis_break=None,
    line_series=None,
    right_y_unit="",
    right_y_title=None,
    value_domain=None,
    single=False,
    y_unit="",
    x_title=None,
    y_title=None,
    title=None,
    subtitle=None,
    figure_label=None,
    note=None,
    source=None,
    error_kind="SEM",
    show_points=True,
    show_values=None,
    pairwise_p=None,
    auto_test=None,
    pairs=None,
    width=1200,
    height=760,
    font_family=None,
    palette=None,
    highlight=None,
    summary_values=False,
    value_scale="auto",
    ci_level=None,
    reference_lines=None,
):
    """Measured categorical figure."""
    if orientation not in ("vertical", "horizontal"):
        raise ValueError("orientation must be vertical or horizontal")
    categories, names, records = normalize_records(categories, series, error_kind)
    comparisons = _pairwise(
        records, categories, names, pairwise_p=pairwise_p, auto_test=auto_test, pairs=pairs, single=single
    )
    stacked_comparisons = bool(comparisons) and stack not in (None, "none")
    if stacked_comparisons and any(records[a]["category"] == records[b]["category"] for a, b, _ in comparisons):
        raise ValueError("stacked comparisons require different categories; use a/b [category, series] references")
    records = _stack_records(records, categories, stack)
    if show_values is not None and not isinstance(show_values, bool):
        raise TypeError("show_values must be True, False or None")
    # Vertical bars label above the bar top, horizontal bars just past the bar end.
    values_supported = (
        stack in (None, "none") and axis_break is None and not line_series and all(r["value"] >= 0 for r in records)
    )
    if show_values is True and not values_supported:
        raise ValueError("show_values requires non-negative unstacked bars without an axis break or line overlay")
    if summary_values and show_values is None:
        display_values = values_supported and len(records) <= 24
    else:
        display_values = (
            show_values
            if show_values is not None
            else (values_supported and not show_points and len(records) <= 12 and not any("lo" in r for r in records))
        )
    values = [
        v
        for r in records
        for v in [
            r["start"],
            r["value"],
            *([r["lo"], r["hi"]] if "lo" in r else []),
            *(r["replicates"] if show_points else []),
        ]
    ]
    log_axis = resolve_value_scale(
        value_scale, records, axis_break=axis_break, stack=stack, line_series=line_series, value_domain=value_domain
    )
    refs = normalize_reference_lines(reference_lines, log_axis)
    if value_domain is None:
        values += [r["value"] for r in refs]
    if log_axis:
        positive = [v for v in values if v > 0]
        scale = scale_from(positive, domain=value_domain, transform="log10")
    else:
        scale = scale_from(values, domain=value_domain, zero=True)
    if axis_break is not None:
        scale = BrokenScale(scale, axis_break)
    layout = ChartLayout(width, height, palette or "archive_ink", font_family, n_items=max(len(categories), len(names)))
    fonts = layout.font_sizes
    fs, axis_fs, small_fs = fonts["label"], fonts["xaxis"], fonts["foot"]
    line_h, small_h = fs * 1.35, small_fs * 1.35
    top = layout.header(title, subtitle, figure_label)
    line_data, right_scale, line_names, line_runs = [], None, [], []
    if line_series:
        if orientation != "vertical" or not right_y_unit or not y_unit:
            raise ValueError("dual-axis bar/line charts require vertical orientation and both y_unit and right_y_unit")
        if axis_break is not None:
            raise ValueError("dual-axis lines cannot be combined with an axis break")
        for s in line_series:
            if len(s["values"]) != len(categories):
                raise ValueError("line values must match categories")
            points = [{"x": i, "y": finite(v, "line value")} for i, v in enumerate(s["values"]) if v is not None]
            line_data.append({"name": str(s["name"]), "points": points})
            run = []
            for category, value in enumerate(s["values"]):
                if value is None:
                    if len(run) > 1:
                        line_runs.append({"name": str(s["name"]), "curve": run, "points": [], "marker": "none"})
                    run = []
                else:
                    run.append({"x": category, "y": finite(value, "line value")})
            if len(run) > 1:
                line_runs.append({"name": str(s["name"]), "curve": run, "points": [], "marker": "none"})
        line_data = normalize_series(line_data)
        line_names = [s["name"] for s in line_data]
        if set(names) & set(line_names):
            raise ValueError("bar and line names must be distinct")
        right_scale = scale_from([p["y"] for s in line_data for p in s["points"]])
    for record in records:
        record["interval_color"] = layout.ink
    context = SeriesContext(names + line_names, pal=layout.pal)
    if single and highlight is not None:
        if highlight not in categories:
            raise ValueError("highlight_group must name an existing category")
        for record in records:
            record["color"] = layout.pal["accent"] if record["category"] == highlight else layout.pal["secondary"]
    elif highlight in context.colors:
        context.colors[highlight] = layout.pal["accent"]
    # One bar series needs no legend: its name repeats the value heading.
    one_series = len(names) == 1 and not line_data
    if one_series and not y_title and names[0] != y_unit and stack != "percent":
        y_title = names[0]
    if not (single or one_series) or line_data:
        top = _legend(layout, names + line_names, context, top, line_names)
    interval_note = interval_note_text(records, error_kind, ci_level)
    if interval_note:
        if stack == "percent":
            interval_note += "; components use a fixed observed total as denominator"
        top += layout.text(interval_note, 28, top, fs=small_fs, color=layout.pal["ink6"], width=layout.width - 56) + 8
    bottom = footer(layout, note, source)
    horizontal = orientation == "horizontal"
    fmt, _ = _axis_format(scale)
    tick_width = max((layout.measure(fmt(t), fs) for t in scale.ticks), default=20)
    category_width = min(layout.width * 0.30, max(layout.measure(c, fs, True) for c in categories)) if horizontal else 0
    left = 28 + (category_width + 20 if horizontal else tick_width + 18)
    right = layout.width - 28
    if right_scale:
        rfmt, _ = _axis_format(right_scale)
        right -= max(layout.measure(rfmt(t), fs) for t in right_scale.ticks) + 18
    ref_fs = max(10.0, fs * 0.85)
    ref_labels = [r for r in refs if r["label"]]
    if ref_labels and not horizontal:
        # Labels sit at the line end, right of the plot, so no bar can cover them.
        right -= max(layout.measure(r["label"], ref_fs) for r in ref_labels) + 10
    slot = (right - left) / len(categories)
    labels = [wrap_lines(c, category_width if horizontal else max(20, slot * 0.9), fs, layout.font) for c in categories]
    label_height = max(len(lines) for lines in labels) * line_h
    has_n = single and any("n" in r for r in records)
    if log_axis:
        # The reader must be told the bar lengths are logarithmic.
        if horizontal and x_title:
            x_title = log_axis_title(x_title)
        else:
            y_title = log_axis_title(y_title or "")
    value_heading = heading(y_title, scale, "%" if stack == "percent" else y_unit, chart_title=title)
    heading_height = 0
    if value_heading:
        heading_height = (
            layout.text(
                value_heading, left, top, fs=axis_fs, width=(right - left) / (2 if right_scale else 1), axis=True
            )
            + 10
        )
    if right_scale:
        heading_height = max(
            heading_height,
            layout.text(
                heading(right_y_title, right_scale, right_y_unit),
                right,
                top,
                fs=fs,
                anchor="end",
                width=(right - left) / 2,
            )
            + 10,
        )
    top += heading_height + 12
    value_space = fs * 1.35 + 10 if display_values else 0
    comparison_specs = []
    if stacked_comparisons:
        for a, b, p in comparisons:
            names_compared = list(dict.fromkeys([records[a]["name"], records[b]["name"]]))
            label = " / ".join(names_compared) + " · " + _p_label(p)
            lines = wrap_lines(label, min(220, right - left - 16), small_fs, layout.font)
            annotation_width = max(layout.measure(line, small_fs) for line in lines)
            annotation_height = len(lines) * small_h
            comparison_specs.append((label, annotation_width, annotation_height))
        bracket_space = sum(w + 24 if horizontal else h + 12 for _, w, h in comparison_specs)
    else:
        bracket_step = max(100, layout.measure("P = 0.999", small_fs) + 24) if horizontal else small_h + 12
        bracket_space = len(comparisons) * bracket_step
    value_texts = uniform_value_labels([r["value"] for r in records]) if display_values else []
    if horizontal:
        right -= bracket_space
        if value_texts:
            right -= max(layout.measure(value, fs) for value in value_texts) + 14
        bottom -= line_h + 20 + (axis_fs * 1.35 if x_title else 0)
        top += ref_fs * 1.35 + 6 if ref_labels else 0
    else:
        top += bracket_space + value_space
        bottom -= label_height + 32 + (small_h + 7 if has_n else 0) + (axis_fs * 1.35 + 4 if x_title else 0)
    box = BBox(left, top, right, bottom)
    min_height = len(categories) * max(30, label_height + 8 + (24 if has_n else 0)) if horizontal else 100
    if box.x1 - box.x0 < 130 or box.y1 - box.y0 < min_height or (not horizontal and slot < 28):
        raise ValueError(
            "canvas is too small for measured labels and data; increase width/height or use horizontal orientation"
        )
    numeric_axis(layout, box, scale, orientation="x" if horizontal else "y", grid=True)
    if right_scale:
        numeric_axis(layout, box, right_scale, orientation="y", side="right")
    category_scale = CategoryScale(categories)
    fragment, centers = render_categorical_plot(
        records,
        box,
        scale=scale,
        context=context,
        category_scale=category_scale,
        orientation=orientation,
        stack=stack,
        show_points=show_points,
        point_color=layout.ink,
        point_stroke=layout.pal.get("bg", "#FFFFFF"),
    )
    layout.parts.append(fragment)
    if summary_values and stack in (None, "none"):
        present = {(r["category"], r["name"]) for r in records}
        start, end = (box.y0, box.y1) if horizontal else (box.x0, box.x1)
        thickness = min(66, (end - start) / len(categories) * 0.72 / len(names))
        for category in categories:
            for index, name in enumerate(names):
                if (category, name) in present:
                    continue
                center = category_scale.map(category, start, end) + (index - (len(names) - 1) / 2) * thickness
                floor = scale.domain[0] if log_axis else max(scale.domain[0], 0)
                base = scale.map(floor, box.x0, box.x1) if horizontal else scale.map(floor, box.y1, box.y0)
                x, y = (base + 7, center + fs * 0.35) if horizontal else (center, base - 7)
                layout.parts.append(
                    _text(
                        "\u2014",
                        x,
                        y,
                        layout.font,
                        layout.pal["ink6"],
                        fs=fs,
                        anchor="start" if horizontal else "middle",
                        role="missing",
                    )
                )
    value_boxes = []
    if display_values and horizontal:
        # Value sits just past the bar end (or interval end); the right margin
        # was reserved above, so every label fits without shrinking digits.
        bar_slot = (box.y1 - box.y0) / len(categories)
        if min(66, bar_slot * 0.72 / len(names)) < fs * 1.05:
            if show_values is True:
                raise ValueError(
                    "canvas is too short for complete bar values; increase height or set show_values=False"
                )
        else:
            for r, center, value in zip(records, centers, value_texts):
                endpoint = max(r["value"], r.get("hi", r["value"]))
                x = scale.map(endpoint, box.x0, box.x1) + 7
                value_boxes.append((x, center - fs * 0.55, x + layout.measure(value, fs), center + fs * 0.55))
                layout.parts.append(
                    _value_text(
                        _text(
                            value,
                            x,
                            center + fs * 0.35,
                            layout.font,
                            layout.ink,
                            fs=fs,
                            anchor="start",
                            role="bar-value",
                        ),
                        r,
                        summary_values,
                    )
                )
    elif display_values:
        # Match render_categorical_plot's adjacent bar-center spacing. Never
        # shrink source digits or shift numerical values to solve a collision.
        available = min(66, slot * 0.72 / len(names)) - 6
        if any(layout.measure(value, fs) > available for value in value_texts):
            if show_values is True:
                raise ValueError(
                    "canvas is too narrow for complete bar values; increase width or set show_values=False"
                )
        else:
            for r, center, value in zip(records, centers, value_texts):
                endpoint = max(r["value"], r.get("hi", r["value"]))
                y = scale.map(endpoint, box.y1, box.y0) - 7 - fs * 0.26
                w = layout.measure(value, fs)
                value_boxes.append((center - w / 2, y - fs * 0.8, center + w / 2, y + fs * 0.25))
                layout.parts.append(
                    _value_text(
                        _text(value, center, y, layout.font, layout.ink, fs=fs, anchor="middle", role="bar-value"),
                        r,
                        summary_values,
                    )
                )
    for ref in refs:
        if not scale.domain[0] <= ref["value"] <= scale.domain[1]:
            raise ValueError(f"reference_lines value {ref['value']:g} lies outside value_domain")
        pos = scale.map(ref["value"], box.x0, box.x1) if horizontal else scale.map(ref["value"], box.y1, box.y0)
        if horizontal:
            w = layout.measure(ref["label"], ref_fs)
            lx = min(box.x1 + 20 - w / 2, max(box.x0 + w / 2, pos))
            draw_reference_line(
                layout, ref, pos, box.y0 - 4, pos, box.y1, (lx, box.y0 - 8), ref_fs, "middle", value_boxes
            )
        else:
            draw_reference_line(
                layout, ref, box.x0, pos, box.x1, pos, (box.x1 + 6, pos + ref_fs * 0.35), ref_fs, avoid=value_boxes
            )
    if line_data:
        layout.parts.append(
            render_xy_plot(
                line_runs + line_data,
                box,
                x_scale=SharedScale(category_scale.domain),
                y_scale=right_scale,
                context=context,
                palette=layout.pal,
                font_family=layout.font,
                axes=False,
            )
        )
    for category, lines in zip(categories, labels):
        center = (
            category_scale.map(category, box.y0, box.y1) if horizontal else category_scale.map(category, box.x0, box.x1)
        )
        label = "\n".join(lines)
        layout.text(
            label,
            box.x0 - 12 if horizontal else center,
            center - len(lines) * line_h / 2 if horizontal else box.y1 + 13,
            fs=fs,
            anchor="end" if horizontal else "middle",
            bold=True,
        )
        if has_n:
            r = next((r for r in records if r["category"] == category), {})
            if "n" in r:
                layout.text(
                    f"n = {r['n']}",
                    box.x0 - 12 if horizontal else center,
                    center + len(lines) * line_h / 2 + 3 if horizontal else box.y1 + 18 + label_height,
                    fs=small_fs,
                    anchor="end" if horizontal else "middle",
                    color=layout.pal["ink6"],
                )
    if x_title:
        layout.text(
            x_title,
            (box.x0 + box.x1) / 2,
            box.y1 + (line_h + 16 if horizontal else label_height + 32 + (small_h + 7 if has_n else 0)),
            fs=axis_fs,
            anchor="middle",
            width=box.x1 - box.x0,
        )
    comparison_offset = 0
    for lane, (a, b, p) in enumerate(comparisons):
        ca, cb = sorted((centers[a], centers[b]))
        label = _p_label(p)
        if stacked_comparisons:
            label, label_width, label_height = comparison_specs[lane]
            if horizontal:
                pos = box.x1 + 14 + comparison_offset
                path = f"M{pos - 5},{ca} H{pos} V{cb} H{pos - 5}"
                layout.text(label, pos + 5, (ca + cb) / 2 - label_height / 2, fs=small_fs, width=label_width + 1)
                comparison_offset += label_width + 24
            else:
                pos = box.y0 - 10 - comparison_offset
                path = f"M{ca},{pos + 5} V{pos} H{cb} V{pos + 5}"
                label_x = min(box.x1 - label_width / 2, max(box.x0 + label_width / 2, (ca + cb) / 2))
                layout.text(label, label_x, pos - label_height - 2, fs=small_fs, anchor="middle", width=label_width + 1)
                comparison_offset += label_height + 12
        elif horizontal:
            pos = box.x1 + 14 + lane * bracket_step
            path = f"M{pos - 5},{ca} H{pos} V{cb} H{pos - 5}"
            layout.text(label, pos + 5, (ca + cb) / 2 - 6, fs=small_fs)
        else:
            pos = box.y0 - value_space - 10 - lane * bracket_step
            path = f"M{ca},{pos + 5} V{pos} H{cb} V{pos + 5}"
            layout.text(label, (ca + cb) / 2, pos - small_h - 2, fs=small_fs, anchor="middle")
        layout.parts.append(f'<path d="{path}" stroke={quoteattr(layout.ink)} fill="none" data-role="significance"/>')
    if axis_break is not None:
        a, b = scale.visible_intervals[0][1], scale.visible_intervals[1][0]
        center = (
            (scale.map(a, box.x0, box.x1) + scale.map(b, box.x0, box.x1)) / 2
            if horizontal
            else (scale.map(a, box.y1, box.y0) + scale.map(b, box.y1, box.y0)) / 2
        )
        half = scale.gap / 2
        # Two parallel slashes, one on each axis stub, plus a background band cutting
        # the grid so the discontinuity reads at slide size.
        if horizontal:
            pa, pb = scale.map(a, box.x0, box.x1), scale.map(b, box.x0, box.x1)
            layout.parts.append(
                f'<rect x="{center - half + 2:.3f}" y="{box.y0:.3f}" width="{max(0, 2 * half - 4):.3f}" '
                f'height="{box.y1 - box.y0 + 1:.3f}" fill={quoteattr(layout.pal.get("bg") or "#FFFFFF")} data-role="axis-break-gap"/>'
            )
            path = " ".join(f"M{x - 3:.3f},{box.y1 + 6:.3f} l6,-12" for x in (pa, pb))
        else:
            pa, pb = scale.map(a, box.y1, box.y0), scale.map(b, box.y1, box.y0)
            layout.parts.append(
                f'<rect x="{box.x0 - 1:.3f}" y="{center - half + 2:.3f}" width="{box.x1 - box.x0 + 1:.3f}" '
                f'height="{max(0, 2 * half - 4):.3f}" fill={quoteattr(layout.pal.get("bg") or "#FFFFFF")} data-role="axis-break-gap"/>'
            )
            path = " ".join(f"M{box.x0 - 6:.3f},{y + 3:.3f} l12,-6" for y in (pa, pb))
        layout.parts.append(
            f'<path d="{path}" stroke={quoteattr(layout.ink)} stroke-width="1.6" fill="none" data-role="axis-break"/>'
        )
    layout.parts.insert(
        0,
        f"<g {attrs(role='categorical-chart', orientation=orientation, stack=stack or 'none', domain=scale.domain)}></g>",
    )
    return layout.svg(title or "Categorical bar chart")
