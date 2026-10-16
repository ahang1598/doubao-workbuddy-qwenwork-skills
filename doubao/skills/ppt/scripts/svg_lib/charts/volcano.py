"""Volcano thresholds with one shared classification and drawing function."""

import math

from .._common import _resolve_palette, _variant_is_classic
from ._chart_layout import finite
from ._xy import SharedScale, infer_scales, interpolate_curve, make_xy_chart, normalize_series
from ._shared import tr


def _threshold_function(threshold, fc_threshold, p_cutoff):
    """One threshold function drives both point classification and curve samples."""
    if threshold is None:
        return lambda fc: p_cutoff
    if callable(threshold):

        def custom(fc):
            value = threshold(fc)
            if value == math.inf:
                return value
            return finite(value, "threshold value", minimum=0)

        return custom
    if not isinstance(threshold, dict):
        raise TypeError("threshold must be callable, {s0:...}, or {curve:[(x,y),...]}")
    if set(threshold) == {"s0"}:
        s0 = finite(threshold["s0"], "s0", minimum=0)
        if s0 == 0:
            return lambda fc: p_cutoff if abs(fc) >= fc_threshold else math.inf
        return lambda fc: p_cutoff + s0 / (abs(fc) - fc_threshold) if abs(fc) > fc_threshold else math.inf
    if set(threshold) == {"curve"}:
        curve = normalize_series([{"name": "Threshold", "curve": threshold["curve"]}])[0]["curve"]
        if len(curve) < 2 or len({p["x"] for p in curve}) != len(curve):
            raise ValueError("custom threshold needs at least two unique x values")
        if any(isinstance(p["x"], str) or p["y"] < 0 for p in curve):
            raise ValueError("threshold curve coordinates must be numeric and y nonnegative")

        def sampled(fc):
            return interpolate_curve(curve, fc)

        sampled.domain = (curve[0]["x"], curve[-1]["x"])
        sampled.knots = curve
        return sampled
    raise ValueError("threshold dict needs exactly s0 or curve")


def classify_volcano(points, fc_threshold=1.0, p_threshold=0.05, threshold=None):
    fc_threshold = finite(fc_threshold, "fc_threshold", minimum=0)
    p_threshold = finite(p_threshold, "p_threshold", minimum=0)
    if not 0 < p_threshold < 1:
        raise ValueError("p_threshold must be strictly between zero and one")
    cutoff = -math.log10(p_threshold)
    function = _threshold_function(threshold, fc_threshold, cutoff)
    classified = []
    for raw in points:
        if "log2fc" not in raw or "neg_log10_p" not in raw:
            raise ValueError("volcano points require log2fc and neg_log10_p")
        fc = finite(raw["log2fc"], "log2fc")
        p = finite(raw["neg_log10_p"], "neg_log10_p", minimum=0)
        y_limit = function(fc)
        significant = abs(fc) >= fc_threshold and p >= y_limit and fc != 0
        category = ("up" if fc > 0 else "down") if significant else "ns"
        if "is_up" in raw:
            if not isinstance(raw["is_up"], bool):
                raise ValueError("is_up must be a boolean")
            if raw["is_up"] != (category == "up"):
                raise ValueError("is_up conflicts with the displayed volcano threshold")
        classified.append(dict(raw, name=str(raw.get("name", "")), fc=fc, np=p, category=category, threshold=y_limit))
    if not classified:
        raise ValueError("volcano points must be nonempty")
    return classified, function, cutoff


def _threshold_branches(function, low, high, fc_threshold, observations, ymax):
    """Preserve supplied knots; adapt callable curves around actual observation X."""
    if hasattr(function, "domain"):
        low, high = max(low, function.domain[0]), min(high, function.domain[1])
    branches = []
    for start, end in ((low, min(high, -fc_threshold)), (max(low, fc_threshold), high)):
        if start >= end:
            continue
        if hasattr(function, "knots"):
            xs = sorted({start, end} | {p["x"] for p in function.knots if start <= p["x"] <= end})
            branches.append([{"x": x, "y": function(x)} for x in xs])
            continue
        # The asymptote is open: evaluate just inside it, then clip the segment
        # in screen coordinates rather than erasing its visible upper section.
        if not math.isfinite(function(start)):
            start += (end - start) * 1e-9
        if not math.isfinite(function(end)):
            end -= (end - start) * 1e-9
        seeds = sorted(
            {start + (end - start) * i / 32 for i in range(33)} | {x for x in observations if start < x < end}
        )

        def refine(a, ya, b, yb, depth=0):
            middle = (a + b) / 2
            ym = function(middle)
            finite_values = all(math.isfinite(v) for v in (ya, ym, yb))
            visible_error = (
                abs(min(ym, 2 * ymax) - (min(ya, 2 * ymax) + min(yb, 2 * ymax)) / 2) if finite_values else math.inf
            )
            if depth < 12 and visible_error > ymax / 800:
                return refine(a, ya, middle, ym, depth + 1)[:-1] + refine(middle, ym, b, yb, depth + 1)
            return [(a, ya), (b, yb)]

        sampled = []
        for i in range(1, len(seeds)):
            a, b = seeds[i - 1], seeds[i]
            sampled.extend(refine(a, function(a), b, function(b))[:-1])
        sampled.append((end, function(end)))
        current = []
        for x, y in sampled:
            if math.isfinite(y):
                current.append({"x": x, "y": y})
            elif current:
                branches.append(current)
                current = []
        if current:
            branches.append(current)
    return branches


def make_volcano(
    points,
    *,
    title=None,
    subtitle=None,
    figure_label=None,
    note=None,
    source=None,
    fc_threshold=1.0,
    p_threshold=0.05,
    top_k_labels=10,
    highlight_names=None,
    multi_mode="auto",
    width=1200,
    height=960,
    font_family=None,
    palette=None,
    variant=None,
    threshold=None,
    gene_sets=None,
):
    """Standard, hyperbolic or precomputed/callable threshold volcano.

    ``threshold={'s0':1}`` uses y = -log10(p_threshold) + s0/(|FC|-fc_threshold)
    outside the excluded central band. ``threshold={'curve':[(x,y),...]}`` uses
    linear interpolation (must cover every FC). ``gene_sets`` maps set names to
    feature-name lists and adds a colored position rug; membership is not a test.
    """
    _variant_is_classic("volcano", variant)
    classified, function, cutoff = classify_volcano(points, fc_threshold, p_threshold, threshold)
    if finite(top_k_labels, "top_k_labels", minimum=0) % 1:
        raise ValueError("top_k_labels must be a nonnegative integer")
    top_k_labels = int(top_k_labels)
    highlight = set(highlight_names or [])
    ranked = sorted(
        (p for p in classified if p["category"] != "ns"), key=lambda p: (-p["np"], -abs(p["fc"]), p["name"])
    )
    chosen = highlight | {p["name"] for p in ranked[:top_k_labels]}
    pal = _resolve_palette(palette or "archive_ink")
    labels = {"ns": tr("Not significant"), "up": tr("Upregulated"), "down": tr("Downregulated")}
    colors = {"ns": pal["ink4"], "up": pal["accent"], "down": pal["secondary"]}
    series = []
    for category in ("ns", "down", "up"):
        members = [p for p in classified if p["category"] == category]
        if members:
            series.append(
                {
                    "name": f"{labels[category]} (n = {len(members)})",
                    "color": colors[category],
                    "points": [
                        {"x": p["fc"], "y": p["np"], "label": p["name"] if p["name"] in chosen else ""} for p in members
                    ],
                }
            )
    series = normalize_series(series)
    xs, ys = infer_scales(series)
    span = max(abs(xs.domain[0]), abs(xs.domain[1]), float(fc_threshold) * 1.5)
    from ._academic_rigor import nice_axis

    ticks, low, high = nice_axis(-span, span, 6)
    xs = SharedScale((low, high), ticks)
    max_y = max(max(p["np"] for p in classified) * 1.12, cutoff * 1.3, 1.0)
    yticks, _, ymax = nice_axis(0, max_y, 5)
    ys = SharedScale((0, ymax), yticks)
    refs = [{"axis": "x", "value": -float(fc_threshold)}, {"axis": "x", "value": float(fc_threshold)}]
    if threshold is None:
        refs.append({"axis": "y", "value": cutoff})
    else:
        branches = _threshold_branches(function, low, high, fc_threshold, [p["fc"] for p in classified], ymax)
        for i, branch in enumerate(branches):
            if len(branch) > 1:
                series.append(
                    {
                        "name": tr("Threshold") if i == 0 else tr("Threshold {i}", i=i + 1),
                        "color": pal["ink6"],
                        "points": [],
                        "curve": branch,
                        "marker": "none",
                        "_legend": i == 0,
                    }
                )
    if multi_mode not in (None, "single", "off", "auto", "with_top_table"):
        raise ValueError("multi_mode must be single, auto or with_top_table")
    table = (
        [(p["name"], f"{p['fc']:+.3g}") for p in ranked[:10]]
        if multi_mode == "with_top_table"
        or multi_mode == "auto"
        and len(ranked) >= 10
        and width >= 1050
        and height >= 680
        else None
    )
    rugs = []
    if gene_sets:
        from ._academic_rigor import SeriesContext

        context = SeriesContext(list(gene_sets), pal=pal)
        sets = {name: set(values) for name, values in gene_sets.items()}
        for name, members in sets.items():
            for p in classified:
                if p["name"] in members:
                    rugs.append((p["fc"], context.color_of(name)))
        legend = "; ".join(
            f"{name}: {sum(p['name'] in members for p in classified)} features" for name, members in sets.items()
        )
        note = ("" if not note else note + " · ") + tr("Rug gene sets — {legend}", legend=legend)
    return make_xy_chart(
        series,
        title=title,
        subtitle=subtitle,
        figure_label=figure_label,
        note=note,
        source=source,
        x_title=tr("log₂ fold change"),
        y_title="−log₁₀ P",
        width=width,
        height=height,
        palette=pal,
        font_family=font_family,
        reference_lines=refs,
        x_scale=xs,
        y_scale=ys,
        table=table,
        rugs=rugs,
    )
