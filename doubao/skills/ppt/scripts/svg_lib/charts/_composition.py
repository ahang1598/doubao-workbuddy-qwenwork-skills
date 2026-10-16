"""Plot-only Cartesian composition primitives with measured outer layout."""

from __future__ import annotations

import json
import math
from xml.sax.saxutils import quoteattr

from .._common import _rgb_tuple
from ._academic_rigor import BBox, SharedScale, nice_axis
from ._chart_layout import finite, wrap_lines
from ._matrix_core import ColorScale
from ._xy import _axis_format, _marker, _text
from ._shared import tr


def attrs(**values):
    return " ".join(f"data-{key.replace('_', '-')}={quoteattr(str(value))}" for key, value in values.items())


def group_start(role, **values):
    return f"<g {attrs(role=role, **values)}>"


def scale_from(values, *, domain=None, transform="linear", zero=False):
    """Numeric scale using centered nice-axis arithmetic from the XY engine."""
    values = [finite(v, "coordinate") for v in values]
    if not values:
        raise ValueError("a numeric scale requires observations")
    if transform not in ("linear", "log10"):
        raise ValueError("transform must be linear or log10")
    if domain is not None:
        lo, hi = (finite(v, "domain") for v in domain)
        if lo >= hi:
            raise ValueError("domain must have two strictly increasing finite bounds")
        if lo > min(values) or hi < max(values):
            raise ValueError("explicit domain must contain every observation and interval")
    else:
        lo, hi = min(values), max(values)
        if zero:
            lo, hi = min(0, lo), max(0, hi)
    if transform == "log10":
        if lo <= 0:
            raise ValueError("log10 coordinates must be positive")
        a, b = math.log10(lo), math.log10(hi)
        if a == b:
            a, b = a - 0.1, b + 0.1
        if domain is None:
            pad = max(0.02, (b - a) * 0.05)
            a, b = a - pad, b + pad
        from ._academic_rigor import log_ticks

        ticks = [10**e for e in range(math.ceil(a), math.floor(b) + 1)]
        if len(ticks) < 4:  # under ~3 decades: 1-2-5 / nice-number labels, never only "1, 2"
            ticks = log_ticks(10**a, 10**b) or ticks
        if len(ticks) > 7:
            ticks = ticks[:: math.ceil(len(ticks) / 7)]
        return SharedScale((10**a, 10**b), ticks, transform)
    if lo == hi:
        pad = max(abs(lo) * 0.05, 0.5)
        lo, hi = lo - pad, hi + pad
    ticks, a, b = nice_axis(lo, hi, 5)
    if domain is not None:
        a, b = lo, hi
        ticks = [v for v in ticks if a <= v <= b]
    return SharedScale((a, b), ticks, transform)


def heading(label, scale, unit="", chart_title=None):
    from ._chart_layout import axis_caption

    text = axis_caption(label, unit, chart_title)
    offset = _axis_format(scale)[1]
    return text + ((" · " if text else "") + offset if offset else "")


def footer(layout, note, source):
    fs = layout.font_sizes["foot"]
    line_h = fs * 1.35
    lines = []
    for value in (note, source):
        if value:
            lines.extend(wrap_lines(value, layout.width - 56, fs, layout.font))
    top = layout.height - 24 - len(lines) * line_h
    for i, line in enumerate(lines):
        layout.text(line, 28, top + i * line_h, fs=fs, color=layout.pal["ink6"])
    return top - (16 if lines else 0)


def color_key(layout, scale, top):
    fs = layout.font_sizes["legend"]
    label = scale.label or tr("Color")
    top += layout.text(label, 28, top, fs=fs, width=layout.width - 56) + 5
    left, width = 28, min(240, layout.width - 56)
    for i in range(100):
        value = scale.value_at(i / 99)
        layout.parts.append(
            f'<rect x="{left + width * i / 100:.3f}" y="{top:.3f}" width="{width / 100 + 0.5:.3f}" '
            f'height="9" fill={quoteattr(scale.color(value))}/>'
        )
    layout.text(f"{scale.low:.4g}", left, top + 14, fs=fs)
    layout.text(f"{scale.high:.4g}", left + width, top + 14, fs=fs, anchor="end")
    return top + 19 + fs * 1.35


def size_key(layout, maximum, top, *, label="Size", radius=12):
    fs = layout.font_sizes["legend"]
    top += layout.text(tr("Area ∝ {label}", label=tr(label)), 28, top, fs=fs, width=layout.width - 56) + 7
    x = 28.0
    for value in sorted({maximum / 4, maximum / 2, maximum}):
        r = radius * math.sqrt(value / maximum) if maximum else 0
        text = f"{value:.4g}"
        needed = 2 * radius + layout.measure(text, fs) + 27
        if x + needed > layout.width - 28:
            x = 28
            top += 2 * radius + 13
        layout.parts.append(_marker(x + radius, top + radius, r, "circle", layout.pal["ink6"], role="size-key"))
        layout.text(text, x + 2 * radius + 7, top + max(radius, fs * 0.6) - fs * 0.5, fs=fs)
        x += needed
    return top + max(2 * radius, fs * 1.35) + 17


def resolve_colors(series, pal, options=None):
    """One continuous color domain; literal point colors stay authoritative."""
    vals = [p["color_value"] for s in series for p in s["points"] if "color_value" in p]
    if not vals:
        return None
    scale = ColorScale.from_values([finite(v, "color_value") for v in vals], pal, **(options or {}))
    for s in series:
        for p in s["points"]:
            if "color_value" in p:
                p["color"] = scale.color(p["color_value"])
    return scale


def numeric_axis(layout, box, scale, *, orientation="x", side="bottom", labels=True, grid=False, font_sizes=None):
    """Draw a numeric axis into an allocated gutter, thinning numeric ticks only."""
    fs = (font_sizes or layout.font_sizes)["xtick" if orientation == "x" else "ytick"]
    fmt, _ = _axis_format(scale)
    ticks = scale.ticks or []
    broken = hasattr(scale, "visible_intervals")
    if broken:
        # Ticks either side of a break sit only scale.gap px apart: thin by measured pixels
        # so every kept label keeps a full gap to its neighbours (never "1562" for 15 | 62).
        ticks = broken_axis_ticks(layout, box, scale, orientation, fs, fmt)
    if orientation == "x":
        if not broken:
            widths = [layout.measure(fmt(v), fs) for v in ticks]
            needed = max(widths, default=0) + 16
            stride = max(1, math.ceil(needed * max(0, len(ticks) - 1) / (box.x1 - box.x0)))
            ticks = ticks[::stride]
        y = box.y1 if side == "bottom" else box.y0
        sign = 1 if side == "bottom" else -1
        for x0, x1 in axis_runs(scale, box.x0, box.x1):
            layout.parts.append(
                f'<path d="M{x0:.3f},{y:.3f} H{x1:.3f}" fill="none" stroke={quoteattr(layout.pal["ink4"])}/>'
            )
        for value in ticks:
            x = scale.map(value, box.x0, box.x1)
            layout.parts.append(f'<path d="M{x:.3f},{y:.3f} v{5 * sign}" stroke={quoteattr(layout.pal["ink4"])}/>')
            if labels:
                layout.parts.append(
                    _text(
                        fmt(value),
                        x,
                        y + (5 + fs * 1.44 if sign == 1 else -10),
                        layout.font,
                        layout.ink,
                        anchor="middle",
                        role="x-tick",
                        fs=fs,
                    )
                )
            if grid:
                layout.parts.append(
                    f'<path d="M{x:.3f},{box.y0:.3f} V{box.y1:.3f}" stroke={quoteattr(layout.pal["grid"])} stroke-width=".7"/>'
                )
    else:
        x = box.x0 if side != "right" else box.x1
        sign = -1 if side != "right" else 1
        # Prevent tick labels colliding on compact tracks.
        stride = 1 if broken else max(1, math.ceil((fs * 1.35 + 6) * max(0, len(ticks) - 1) / (box.y1 - box.y0)))
        for value in ticks[::stride]:
            y = scale.map(value, box.y1, box.y0)
            layout.parts.append(f'<path d="M{x:.3f},{y:.3f} h{5 * sign}" stroke={quoteattr(layout.pal["ink4"])}/>')
            if labels:
                layout.parts.append(
                    _text(
                        fmt(value),
                        x + 10 * sign,
                        y + fs * 0.3,
                        layout.font,
                        layout.ink,
                        anchor="end" if sign == -1 else "start",
                        role="y-tick",
                        fs=fs,
                    )
                )
            if grid:
                layout.parts.append(
                    f'<path d="M{box.x0:.3f},{y:.3f} H{box.x1:.3f}" stroke={quoteattr(layout.pal["grid"])} stroke-width=".7"/>'
                )
        for y0, y1 in axis_runs(scale, box.y1, box.y0):
            layout.parts.append(
                f'<path d="M{x:.3f},{min(y0, y1):.3f} V{max(y0, y1):.3f}" stroke={quoteattr(layout.pal["ink4"])}/>'
            )


def axis_runs(scale, p0, p1):
    """Pixel runs of the axis line: one run, or one per visible interval of a broken scale."""
    visible = getattr(scale, "visible_intervals", None)
    if not visible:
        return [(p0, p1)]
    return [(scale.map(a, p0, p1), scale.map(b, p0, p1)) for a, b in visible]


def broken_axis_ticks(layout, box, scale, orientation, fs, fmt):
    """Nice ticks per visible interval, dropped until labels keep one label-width gap."""
    horizontal = orientation == "x"
    p0, p1 = (box.x0, box.x1) if horizontal else (box.y1, box.y0)
    candidates = []
    for index, (a, b) in enumerate(scale.visible_intervals):
        pixels = abs(scale.map(b, p0, p1) - scale.map(a, p0, p1))
        count = max(2, min(5, int(pixels // ((layout.measure(fmt(b), fs) + fs) if horizontal else fs * 2.6))))
        ticks, _, _ = nice_axis(a, b, count)
        span = b - a
        inside = [t for t in ticks if a - span * 1e-9 <= t <= b + span * 1e-9]
        # The outer domain ends are real data bounds; the break ends are labelled only if they fit.
        inside = sorted(set(inside + [a if index == 0 else b]))
        candidates.extend(inside)
    candidates = sorted(set(candidates))

    def extent(value):
        center = scale.map(value, p0, p1)
        half = layout.measure(fmt(value), fs) / 2 if horizontal else fs * 0.68
        return center - half, center + half

    def separation(u, v):
        (a0, a1), (b0, b1) = sorted((extent(u), extent(v)))
        return b0 - a1

    gap = max(fs, max((layout.measure(fmt(v), fs) for v in candidates), default=fs)) if horizontal else fs * 0.9
    break_value = scale.visible_intervals[0][1]
    low = [v for v in candidates if v <= break_value]
    high = [v for v in candidates if v > break_value]
    kept_low, kept_high = [], []
    for value in low:  # outward end first, toward the break
        if not kept_low or separation(value, kept_low[-1]) >= gap:
            kept_low.append(value)
    for value in reversed(high):
        if not kept_high or separation(value, kept_high[-1]) >= gap:
            kept_high.append(value)
    kept = kept_low + list(reversed(kept_high))
    # Across the break, drop whichever adjacent tick lies closer to it.
    resume = scale.visible_intervals[1][0]
    while kept_low and kept_high and separation(kept_high[-1], kept_low[-1]) < gap:
        low_closer = (break_value - kept_low[-1]) <= (kept_high[-1] - resume)
        if (low_closer and len(kept_low) > 1) or len(kept_high) == 1:
            kept_low.pop()
        else:
            kept_high.pop()
        kept = kept_low + list(reversed(kept_high))
    return kept


def render_bar_plot(records, bbox, *, scale, colors, orientation="vertical", centers=None, thickness=None):
    """Plot supplied bars/intervals, with explicit baselines and optional breaks."""
    box = BBox(*bbox)
    if orientation not in ("vertical", "horizontal"):
        raise ValueError("bar orientation must be vertical or horizontal")
    if scale.transform == "log10" and hasattr(scale, "visible_intervals"):
        raise ValueError("log bars cannot be combined with an axis break")
    horizontal = orientation == "horizontal"
    start, end = (box.y0, box.y1) if horizontal else (box.x0, box.x1)
    centers = (
        list(centers)
        if centers is not None
        else [start + (i + 0.5) * (end - start) / len(records) for i in range(len(records))]
    )
    if len(centers) != len(records):
        raise ValueError("bar centers must match records")
    thickness = (
        finite(thickness, "bar thickness", minimum=0)
        if thickness is not None
        else (end - start) / max(1, len(records)) * 0.55
    )
    transform = (lambda v: scale.map(v, box.x0, box.x1)) if horizontal else (lambda v: scale.map(v, box.y1, box.y0))
    visible = list(getattr(scale, "visible_intervals", [scale.domain]))
    previous = None
    for a, b in visible:
        if not scale.domain[0] <= a < b <= scale.domain[1] or (previous is not None and a <= previous):
            raise ValueError("visible intervals must be ordered disjoint subsets of the scale domain")
        previous = b

    def segments(a, b):
        low, high = sorted((a, b))
        return [(max(low, left), min(high, right)) for left, right in visible if max(low, left) <= min(high, right)]

    parts = []
    intervals = []
    for record, center in zip(records, centers):
        value, baseline = finite(record["value"], "bar value"), finite(record.get("start", 0), "bar start")
        if scale.transform == "log10" and baseline <= 0:
            baseline = scale.domain[0]  # a log axis has no zero: bars grow from the axis minimum
        if not scale.domain[0] <= value <= scale.domain[1] or not scale.domain[0] <= baseline <= scale.domain[1]:
            raise ValueError("bar endpoint and baseline must lie within the scale domain")
        lo, hi = finite(record.get("lo", value), "lo"), finite(record.get("hi", value), "hi")
        if ("lo" in record) != ("hi" in record) or not scale.domain[0] <= lo <= value <= hi <= scale.domain[1]:
            raise ValueError("bar interval must satisfy domain minimum <= lo <= value <= hi <= domain maximum")
        name = str(record["name"])
        color = record.get("color", colors[name])
        interval_color = record.get("interval_color", color)
        for segment_index, (a, b) in enumerate(segments(baseline, value)):
            pa, pb = transform(a), transform(b)
            x, y = (min(pa, pb), center - thickness / 2) if horizontal else (center - thickness / 2, min(pa, pb))
            width, height = (abs(pb - pa), thickness) if horizontal else (thickness, abs(pb - pa))
            parts.append(
                f'<rect x="{x:.3f}" y="{y:.3f}" width="{width:.3f}" height="{height:.3f}" fill={quoteattr(color)} {attrs(role="bar", name=name, value=value, start=baseline, segment=segment_index, row_id=record.get("row_id", name))}/>'
            )
        if "lo" in record:
            for a, b in segments(lo, hi):
                pa, pb = transform(a), transform(b)
                path = f"M{pa:.3f},{center:.3f} H{pb:.3f}" if horizontal else f"M{center:.3f},{pa:.3f} V{pb:.3f}"
                for real in (lo, hi):
                    if a <= real <= b:
                        pos = transform(real)
                        path += f" M{pos:.3f},{center - 3:.3f} v6" if horizontal else f" M{center - 3:.3f},{pos:.3f} h6"
                r, g, b = _rgb_tuple(interval_color)
                outline = "#111820" if 0.2126 * r + 0.7152 * g + 0.0722 * b > 128 else "#FFFFFF"
                intervals.append(
                    f'<path d="{path}" fill="none" stroke={quoteattr(outline)} stroke-width="3" data-role="bar-interval-outline"/>'
                )
                intervals.append(
                    f'<path d="{path}" fill="none" stroke={quoteattr(interval_color)} stroke-width="1.5" {attrs(role="bar-interval", name=name, lo=lo, hi=hi, row_id=record.get("row_id", name))}/>'
                )
    # Every component fill must be behind all interval shafts/caps. In stacked
    # bars an upper limit can legitimately lie inside the next component.
    return "".join(parts + intervals)


def serialize_layout(layout, role, boxes):
    """Semantic geometry for coordinate tests and downstream inspection."""
    layout.parts.insert(
        0, f"<g {attrs(role=role, layout=json.dumps(boxes, ensure_ascii=False, separators=(',', ':')))}></g>"
    )


def adjacent(values):
    """Adjacent pairs, compatible with the bundled Python 3.9 runtime."""
    return ((values[i - 1], values[i]) for i in range(1, len(values)))
