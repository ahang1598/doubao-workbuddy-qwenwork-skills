"""Shared statistics and geometry for sample distributions."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .._common import (
    _derive_series_colors,
    _estimate_label_width_px,
    _fmt_axis,
    _resolve_font,
    _resolve_palette,
    _rgba_with_alpha,
    _xesc,
)
from .._typography import chart_font_sizes
from ._shared import tr


@dataclass
class SampleGroup:
    name: str
    values: list[float]
    subjects: list[str | None]


def finite(value, label="value"):
    if isinstance(value, bool):
        raise TypeError(f"{label} must be a finite number")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a finite number") from exc
    if not math.isfinite(result):
        raise ValueError(f"{label} must be a finite number")
    return result


def normalize_groups(groups) -> list[SampleGroup]:
    if not groups:
        raise ValueError("at least one nonempty sample group is required")
    if isinstance(groups, dict):
        groups = list(groups.items())
    result = []
    names = set()
    for index, item in enumerate(groups):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError(f"group {index} must be (name, observations)")
        name, observations = str(item[0]), list(item[1])
        if name in names:
            raise ValueError(f"duplicate group name: {name}")
        names.add(name)
        if not observations:
            raise ValueError(f"group {name!r} has no observations")
        values, subjects = [], []
        for observation in observations:
            if isinstance(observation, dict):
                values.append(finite(observation.get("value"), f"{name}.value"))
                identity = observation.get("subject_id")
                subjects.append(str(identity) if identity is not None else None)
            else:
                values.append(finite(observation, name))
                subjects.append(None)
        present = [s for s in subjects if s is not None]
        if len(present) != len(set(present)):
            raise ValueError(f"duplicate subject_id within group {name!r}")
        result.append(SampleGroup(name, values, subjects))
    return result


def quantile(values, probability):
    values = sorted(values)
    position = probability * (len(values) - 1)
    lo = int(position)
    hi = min(lo + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (position - lo)


def sample_stats(values):
    q1, median, q3 = (quantile(values, q) for q in (0.25, 0.5, 0.75))
    iqr = q3 - q1
    inside = [v for v in values if q1 - 1.5 * iqr <= v <= q3 + 1.5 * iqr]
    return {
        "q1": q1,
        "median": median,
        "q3": q3,
        "lo": min(inside),
        "hi": max(inside),
        "mean": sum(values) / len(values),
        "n": len(values),
    }


def bandwidth_for(values, bandwidth=None, span=None):
    if bandwidth is not None:
        bandwidth = finite(bandwidth, "bandwidth")
        if bandwidth <= 0:
            raise ValueError("bandwidth must be positive")
        return bandwidth
    n = len(values)
    low, high = min(values), max(values)
    sample_span = high - low
    if sample_span > 0:
        # Compute dispersion in normalized coordinates: no absolute tolerance,
        # no squared tiny quantities, and no loss to a large common offset.
        normalized = [(value - low) / sample_span for value in values]
        mean = math.fsum(normalized) / n
        sd = math.sqrt(math.fsum((value - mean) ** 2 for value in normalized) / max(1, n - 1))
        iqr = (quantile(normalized, 0.75) - quantile(normalized, 0.25)) / 1.349
        spread = min(sd, iqr) if iqr > 0 else sd
        result = sample_span * (0.9 * spread * n ** (-0.2))
    else:
        # Constant samples contain no intrinsic width. Use the shared domain
        # when available; otherwise a relative display scale (unit scale at 0).
        display_span = span if span is not None and span > 0 else (abs(low) * 0.1 or 1.0)
        result = display_span * 0.03 * n ** (-0.2)
    return result if result > 0 else math.ulp(low or high or 1.0)


def kde(values, domain, bandwidth=None, points=100):
    """Relative density in the domain's unit interval, with real X values."""
    low, high = domain
    span = high - low
    normalized_bw = bandwidth_for(values, bandwidth, span) / span
    normalized_values = sorted((value - low) / span for value in values)
    grid = [index / (points - 1) for index in range(points)]
    if normalized_bw < 2 / (points - 1):
        # Cover every observation's eight-bandwidth neighborhood, merging overlaps before laying out a half-bandwidth
        # grid.
        radius = 8 * normalized_bw
        intervals = []
        first = last = normalized_values[0]
        for value in normalized_values[1:]:
            if value - last > 2 * radius:
                intervals.append((first, last))
                first = value
            last = value
        intervals.append((first, last))
        for first, last in intervals:
            start, stop = max(0, first - radius), min(1, last + radius)
            steps = max(2, 2 * math.ceil((stop - start) / normalized_bw))
            grid.extend(start + (stop - start) * index / steps for index in range(steps + 1))
            # Preserve exact isolated peaks and let tails reach floating-point
            # zero before bridging an arbitrarily wide empty region.
            grid.extend(
                position
                for position in (first, last, first - 39 * normalized_bw, last + 39 * normalized_bw)
                if 0 <= position <= 1
            )
        grid = sorted(set(grid))
    xs = [low + span * position for position in grid]
    factor = 1 / (len(values) * normalized_bw * math.sqrt(2 * math.pi))
    ys = []
    left = right = 0
    for position in grid:
        # exp(-z*z/2) is already zero in binary64 beyond 39 bandwidths.
        # Sliding bounds retain every nonzero kernel contribution while
        # keeping separated narrow kernels from requiring all-pairs work.
        while left < len(values) and normalized_values[left] < position - 39 * normalized_bw:
            left += 1
        while right < len(values) and normalized_values[right] <= position + 39 * normalized_bw:
            right += 1
        ys.append(
            math.fsum(
                math.exp(-0.5 * ((position - value) / normalized_bw) ** 2) for value in normalized_values[left:right]
            )
            * factor
        )
    return xs, ys


def sample_domain(groups, low=None, high=None, bandwidth=None, density=False):
    values = [v for g in groups for v in g.values]
    bottom, top = min(values), max(values)
    span = top - bottom
    if span == 0:
        span = abs(top) * 0.1 or 1.0
    pad = span * 0.08
    if density:
        pad = max(pad, max(bandwidth_for(g.values, bandwidth, span) for g in groups) * 3)
    if low is None:
        low = bottom - pad
        if low == bottom:
            low = math.nextafter(bottom, -math.inf)
    else:
        low = finite(low, "axis minimum")
    if high is None:
        high = top + pad
        if high == top:
            high = math.nextafter(top, math.inf)
    else:
        high = finite(high, "axis maximum")
    if high <= low:
        raise ValueError("axis maximum must be greater than axis minimum")
    if low > bottom or high < top:
        raise ValueError("explicit axis limits must contain every observation")
    return low, high


def resolve_tests(groups, academic=False, pairwise_p=None, auto_test=None, pairs=None, *, paired=False):
    if paired and auto_test is not None:
        raise ValueError(
            "paired observations cannot use independent-sample auto_test; supply valid paired pairwise_p results"
        )
    if pairwise_p is not None and (auto_test is not None or pairs is not None):
        raise ValueError("pairwise_p and auto_test/pairs are mutually exclusive")
    if (auto_test is None) != (pairs is None):
        raise ValueError("auto_test and pairs must be supplied together")
    if auto_test is not None:
        from ._academic_rigor import _PAIRWISE_TESTS, pairwise_test

        if auto_test not in _PAIRWISE_TESTS:
            raise ValueError(f"unknown auto_test {auto_test!r}")
        if isinstance(pairs, str):
            pairwise_p = pairwise_test([g.values for g in groups], method=auto_test, pair_strategy=pairs)
        else:
            pairwise_p = [(a, b, _PAIRWISE_TESTS[auto_test](groups[a].values, groups[b].values)) for a, b in pairs]
    result = []
    for entry in pairwise_p or []:
        if len(entry) != 3:
            raise ValueError("pairwise_p entries must be (group_index, group_index, p)")
        a, b, p = entry
        if not isinstance(a, int) or not isinstance(b, int) or a == b or min(a, b) < 0 or max(a, b) >= len(groups):
            raise ValueError("pairwise_p group indices must be distinct valid indices")
        p = finite(p, "P value")
        if not 0 <= p <= 1:
            raise ValueError("P value must be between 0 and 1")
        result.append((min(a, b), max(a, b), p))
    return sorted(result, key=lambda item: (item[1] - item[0], item[0])) if academic else []


def p_label(p):
    stars = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
    return f"{stars}  P < 0.001" if p < 0.001 else f"{stars}  P = {p:.3g}"


def measure(text, fs):
    # Match the embedding validator's conservative metric, including CJK.
    return _estimate_label_width_px(str(text), fs, 0, font_family="Inter, sans-serif")


def wrap(text, width, fs):
    """Use the shared word-preserving wrapper with this renderer's metrics."""
    from ._chart_layout import wrap_lines

    return wrap_lines(text, width, fs, "Inter, sans-serif")


def value_scale(domain, start, end):
    """Bind one plot's numeric domain and pixel endpoints without loop capture."""
    low, high = domain

    def scale(value):
        return start + (value - low) / (high - low) * (end - start)

    return scale


def axis_ticks(domain, count=6):
    low, high = domain
    span = high - low
    ratios = [index / (count - 1) for index in range(count)]
    if math.isfinite(span):
        # Form the bounded interpolation ratio before multiplying the range.
        values = [low + span * ratio for ratio in ratios]
        center = low + span * 0.5
        precision_span = abs(span) or max(abs(low), abs(high)) or 1.0
    else:
        # Finite opposite endpoints can have an unrepresentable signed span.
        values = [(1 - ratio) * low + ratio * high for ratio in ratios]
        center = 0.5 * low + 0.5 * high
        precision_span = max(abs(low), abs(high))
    offset = 0.0
    if math.isfinite(span) and span > 0 and abs(center) / span > 1000:
        offset_step = 10 ** (math.floor(math.log10(span)) + 1)
        offset = round(center / offset_step) * offset_step
    labels = [_fmt_axis(value - offset, precision_span) for value in values]
    if len(set(labels)) < len(set(values)):
        labels = [f"{value - offset:.17g}" for value in values]
    offset_label = tr("Offset {value}", value=f"{offset:+.17g}") if offset else ""
    return values, labels, offset_label


def legend_layout(items, width, fs=11.5):
    """Wrap individual entries as well as whole legend rows, preserving names."""
    available = width - 64
    x, y, row_height = 32.0, 0.0, 0.0
    rows = []
    for item in items:
        label, color = item[:2]
        extra = item[2] if len(item) > 2 else ""
        needed = measure(label, fs) + 44
        slot_width = min(available, needed)
        if x > 32 and x + slot_width > width - 32:
            x, y, row_height = 32.0, y + row_height, 0.0
        lines = wrap(label, available - 28, fs) if needed > available else [label]
        height = len(lines) * fs * 1.35 + 8
        rows.append((x, y, lines, color, extra))
        row_height = max(row_height, height)
        x += slot_width
    return rows, y + row_height


class Canvas:
    def __init__(self, width, height, palette=None, font_family=None):
        self.width, self.height = float(width), float(height)
        self.pal = _resolve_palette(palette)
        self.ink = self.pal["ink"]
        self.muted = self.pal.get("muted", _rgba_with_alpha(self.ink, 0.65))
        self.grid = _rgba_with_alpha(self.ink, 0.12)
        self.bg = self.pal.get("bg") or "#ffffff"
        self.font, self.head_font = _resolve_font(font_family)
        self.parts = [f'<rect x="0" y="0" width="{width:g}" height="{height:g}" fill="{self.bg}"/>']

    def line(self, x1, y1, x2, y2, color=None, stroke=1, extra=""):
        self.parts.append(
            f'<line x1="{x1:.6f}" y1="{y1:.6f}" x2="{x2:.6f}" y2="{y2:.6f}" stroke="{color or self.ink}" stroke-width="{stroke:g}" {extra}/>'
        )

    def text(self, x, y, content, fs=13, anchor="start", color=None, weight=400, extra=""):
        if color in (self.muted, self.pal.get("ink6")) and color is not None:
            from ._chart_layout import readable_annotation_color

            color = readable_annotation_color(color, self.pal)
        self.parts.append(
            f'<text x="{x:.3f}" y="{y:.3f}" text-anchor="{anchor}" font-family="{_xesc(self.font)}" font-size="{fs:g}" font-weight="{weight}" fill="{color or self.ink}" {extra}>{_xesc(str(content))}</text>'
        )

    def lines(self, x, y, lines, fs=13, anchor="start", color=None, weight=400):
        for i, content in enumerate(lines):
            self.text(x, y + i * fs * 1.35, content, fs, anchor, color, weight)

    def circle(self, x, y, radius, color, extra=""):
        self.parts.append(f'<circle cx="{x:.6f}" cy="{y:.6f}" r="{radius:.6f}" fill="{color}" {extra}/>')

    def path(self, points, color, fill="none", stroke=1.6, closed=False, extra=""):
        if not points:
            return
        commands = "M " + " L ".join(f"{x:.3f},{y:.3f}" for x, y in points) + (" Z" if closed else "")
        self.parts.append(
            f'<path d="{commands}" fill="{fill}" stroke="{color}" stroke-width="{stroke:g}" stroke-linejoin="round" {extra}/>'
        )

    def svg(self):
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.width:g} {self.height:g}">'
            + "".join(self.parts)
            + "</svg>"
        )


def header_height(width, title=None, subtitle=None, figure_label=None, fs=None, *, fonts=None):
    fonts = fonts or chart_font_sizes(width, width * 0.6, 1)
    height = 20
    for text, size in ((figure_label, fonts["figure"]), (title, fs or fonts["title"]), (subtitle, fonts["subtitle"])):
        if text:
            height += len(wrap(text, width - 64, size)) * size * 1.35 + 6
    return height


def draw_header(canvas, title=None, subtitle=None, figure_label=None, fs=None, *, fonts=None):
    fonts = fonts or chart_font_sizes(canvas.width, canvas.height, 1)
    y = 22
    for text, size, color, weight in (
        (figure_label, fonts["figure"], canvas.muted, 600),
        (title, fs or fonts["title"], canvas.ink, 600),
        (subtitle, fonts["subtitle"], canvas.muted, 400),
    ):
        if text:
            lines = wrap(text, canvas.width - 64, size)
            y += size
            canvas.lines(32, y, lines, size, color=color, weight=weight)
            y += (len(lines) - 1) * size * 1.35 + 6


def _pack_offsets(value_pixels, widths, radius):
    """Return fixed-radius offsets, or None when the lane cannot fit them."""
    diameter = 2 * radius * 1.04
    placed, offsets = [], [0.0] * len(value_pixels)
    for index in sorted(range(len(value_pixels)), key=value_pixels.__getitem__):
        value = value_pixels[index]
        placed = [(v, x) for v, x in placed if value - v < diameter]
        intervals = []
        for previous, offset in placed:
            extent = math.sqrt(max(0.0, diameter * diameter - (value - previous) ** 2))
            intervals.append((offset - extent, offset + extent))
        merged = []
        for low, high in sorted(intervals):
            if merged and low <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], high))
            else:
                merged.append((low, high))
        blocking = next(((low, high) for low, high in merged if low < 0 < high), None)
        candidates = [0.0] if blocking is None else list(blocking)
        available = widths[index] - radius
        candidates = [x for x in candidates if abs(x) <= available]
        if not candidates:
            return None
        offset = min(candidates, key=lambda x: (abs(x), x))
        offsets[index] = offset
        placed.append((value, offset))
    return offsets


def swarm(value_pixels, half_width, radius=2.5):
    """Pack readable circles without changing their measured coordinates."""
    widths = [float(half_width)] * len(value_pixels) if isinstance(half_width, (int, float)) else list(half_width)
    if len(widths) != len(value_pixels) or any(width <= 0 for width in widths):
        raise ValueError("observation lanes must have positive widths matching the samples")
    for candidate in (radius, 1.8):
        offsets = _pack_offsets(value_pixels, widths, candidate)
        if offsets is not None:
            return offsets, candidate
    raise ValueError("readable observations need more space or an explicit count representation")


def _observation_plan(values, pixels, lane_widths):
    """Plan independent local clusters."""
    widths = [float(lane_widths)] * len(values) if isinstance(lane_widths, (int, float)) else list(lane_widths)
    widths = [max(2.7, width) for width in widths]
    components = []
    for index in sorted(range(len(pixels)), key=pixels.__getitem__):
        if not components or pixels[index] - pixels[components[-1][-1]] > 2 * 3.2 * 1.04:
            components.append([])
        components[-1].append(index)

    def entry(indices):
        observations = [values[index] for index in indices]
        low, high = min(observations), max(observations)
        kind = "raw" if len(indices) == 1 else "frequency" if low == high else "bin"
        return {
            "indices": indices,
            "low": low,
            "high": high,
            "value": quantile(observations, 0.5),
            "pixel": quantile([pixels[index] for index in indices], 0.5),
            "kind": kind,
        }

    def pack(entries, preferred):
        positions = [item["pixel"] for item in entries]
        lanes = [min(widths[index] for index in item["indices"]) for item in entries]
        for radius in (preferred, 1.8):
            offsets = _pack_offsets(positions, lanes, radius)
            if offsets is not None:
                return [{**item, "offset": offset, "radius": radius} for item, offset in zip(entries, offsets)]
        return None

    plan = []
    for component in components:
        raw = [entry([index]) for index in component]
        packed = pack(raw, 2.5)
        if packed is None:
            equal_values = {}
            for index in component:
                equal_values.setdefault(values[index], []).append(index)
            exact = [entry(indices) for indices in equal_values.values()]
            packed = pack(exact, 3.2) if len(exact) < len(raw) else None
        if packed is None:
            bin_width = 7.0
            # Widen only this crowded component's display bins until fixed,
            # readable markers fit. Binning affects no sample statistic.
            while packed is None:
                bins = {}
                for index in component:
                    bins.setdefault(math.floor(pixels[index] / bin_width), []).append(index)
                packed = pack([entry(indices) for indices in bins.values()], 3.2)
                bin_width *= 2
        plan.extend(packed)
    return plan


def _draw_box(c, center, scale, stats, half, color, orientation, mean=True, notch=False, extra="", fill=None):
    def xy(category, value):
        return (category, scale(value)) if orientation == "vertical" else (scale(value), category)

    q1, q2, q3 = (stats[k] for k in ("q1", "median", "q3"))
    c.line(
        *xy(center, stats["lo"]),
        *xy(center, stats["hi"]),
        color,
        1.4,
        f'data-role="whisker" data-low="{stats["lo"]:.17g}" data-high="{stats["hi"]:.17g}"',
    )
    for value in (stats["lo"], stats["hi"]):
        c.line(*xy(center - half * 0.55, value), *xy(center + half * 0.55, value), color, 1.4)
    if notch:
        delta = 1.57 * (q3 - q1) / math.sqrt(stats["n"])
        lower, upper = max(q1, q2 - delta), min(q3, q2 + delta)
        outline = [
            (center - half, q1),
            (center + half, q1),
            (center + half, lower),
            (center + half * 0.55, q2),
            (center + half, upper),
            (center + half, q3),
            (center - half, q3),
            (center - half, upper),
            (center - half * 0.55, q2),
            (center - half, lower),
        ]
    else:
        outline = [(center - half, q1), (center + half, q1), (center + half, q3), (center - half, q3)]
    c.path(
        [xy(*point) for point in outline],
        color,
        fill if fill is not None else _rgba_with_alpha(color, 0.22),
        1.5,
        True,
        extra,
    )
    midhalf = half * (0.55 if notch else 1)
    c.line(
        *xy(center - midhalf, q2),
        *xy(center + midhalf, q2),
        color,
        2.3,
        f'data-role="box-median" data-value="{q2:.17g}"',
    )
    if mean:
        x, y = xy(center, stats["mean"])
        c.circle(
            x, y, 3, c.bg, f'stroke="{color}" stroke-width="1.4" data-role="mean" data-value="{stats["mean"]:.17g}"'
        )


def _facet_input(conditions):
    result = []
    for item in conditions or []:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("conditions must contain (facet_name, groups)")
        result.append((str(item[0]), normalize_groups(item[1])))
    if not result:
        raise ValueError("conditions must contain at least one facet")
    return result


def _effect_estimates(facets, paired):
    """Reference-first standardized effects with explicit paired semantics."""
    from ._academic_rigor import _scaled_stat_groups, effect_size_cohens_d

    rows = []
    for facet_name, groups in facets:
        if len(groups) < 2:
            raise ValueError("with_effect_size requires at least two groups per facet")
        reference = groups[0]
        for group in groups[1:]:
            label = f"{group.name} − {reference.name}"
            if facet_name is not None:
                label = f"{facet_name} · {label}"
            if paired:
                reference_by_id = dict(zip(reference.subjects, reference.values))
                comparison_by_id = dict(zip(group.subjects, group.values))
                subjects = sorted(reference_by_id.keys() & comparison_by_id.keys())
                if len(subjects) < 2:
                    raise ValueError("paired effect size requires at least two matched subject IDs per comparison")
                raw_differences = [comparison_by_id[identity] - reference_by_id[identity] for identity in subjects]
                if all(math.isfinite(value) for value in raw_differences):
                    # Preserve exact equal differences before changing units.
                    _, differences = _scaled_stat_groups([0.0], raw_differences)
                else:
                    reference_scaled, comparison_scaled = _scaled_stat_groups(
                        [reference_by_id[identity] for identity in subjects],
                        [comparison_by_id[identity] for identity in subjects],
                    )
                    differences = [after - before for before, after in zip(reference_scaled, comparison_scaled)]
                n = len(differences)
                mean = sum(differences) / n
                sd = math.sqrt(sum((difference - mean) ** 2 for difference in differences) / (n - 1))
                if sd <= 0:
                    raise ValueError("paired effect size is undefined when paired differences have zero variance")
                estimate = mean / sd
                se = math.sqrt(1 / n + estimate**2 / (2 * (n - 1)))
                low, high = estimate - 1.96 * se, estimate + 1.96 * se
                label += f" · n = {n} pairs"
            else:
                estimate, low, high = effect_size_cohens_d(reference.values, group.values)
            rows.append(
                {
                    "label": label,
                    "estimate": estimate,
                    "low": low,
                    "high": high,
                    "group": group.name,
                    "facet": facet_name,
                }
            )
    return rows


def _effect_layout(rows, width):
    if width < 600:
        raise ValueError("with_effect_size needs a canvas width of at least 600")
    fonts = chart_font_sizes(width, width * 0.4, len(rows))
    fs, tick_fs = fonts["label"], fonts["xtick"]
    estimates = [f"{row['estimate']:.2f} [{row['low']:.2f}, {row['high']:.2f}]" for row in rows]
    for _ in range(30):
        label_width = min(width * 0.37, max(130, max(measure(row["label"], fs) for row in rows)))
        estimate_width = max(measure(label, tick_fs) for label in estimates) + 24
        left, right = 32 + label_width + 24, width - 32 - estimate_width
        if right - left >= 120:
            break
        fs *= 0.95
        tick_fs *= 0.95
    labels = [wrap(row["label"], label_width, fs) for row in rows]
    row_heights = [max(34, len(lines) * fs * 1.35 + 14) for lines in labels]
    title_fs, detail_fs = fonts["subtitle"], fonts["foot"]
    # Both possible descriptors reserve the same height before rendering.
    descriptors = [tr("Paired standardized change (d_z)"), tr("Cohen's d · independent samples")]
    descriptor_h = (
        max(len(wrap(d + " · approximate 95% confidence interval", width - 64, detail_fs)) for d in descriptors)
        * detail_fs
        * 1.35
    )
    plot_top = title_fs * 1.35 + descriptor_h + detail_fs * 1.35 + 30
    return {
        "label_width": label_width,
        "labels": labels,
        "row_heights": row_heights,
        "left": left,
        "right": right,
        "fs": fs,
        "tick_fs": tick_fs,
        "title_fs": title_fs,
        "detail_fs": detail_fs,
        "plot_top": plot_top,
        "height": plot_top + sum(row_heights) + tick_fs * 1.35 + 16,
    }


def _draw_effect_panel(c, rows, layout, top, paired, colors):
    left, right = layout["left"], layout["right"]
    fs, tick_fs = layout["fs"], layout["tick_fs"]
    title_fs, detail_fs = layout["title_fs"], layout["detail_fs"]
    c.line(32, top, c.width - 32, top, c.grid)
    c.text(32, top + title_fs + 8, tr("Standardized effect sizes"), title_fs, weight=600)
    descriptor = tr("Paired standardized change (d_z)") if paired else tr("Cohen's d · independent samples")
    c.lines(
        32,
        top + title_fs * 1.35 + detail_fs + 14,
        wrap(descriptor + tr(" · approximate 95% confidence interval"), c.width - 64, detail_fs),
        detail_fs,
        color=c.muted,
    )
    plot_top = top + layout["plot_top"]
    c.text(32, plot_top - 10, tr("Comparison"), detail_fs, color=c.muted, weight=600)
    c.text(c.width - 32, plot_top - 10, tr("Estimate [95% CI]"), detail_fs, "end", c.muted, 600)
    max_abs = max(max(abs(row["low"]), abs(row["high"])) for row in rows) * 1.1 or 1
    scale = lambda value: left + (value + max_abs) / (2 * max_abs) * (right - left)
    bottom = plot_top + sum(layout["row_heights"])
    for value in (-max_abs, 0, max_abs):
        x = scale(value)
        c.line(x, plot_top, x, bottom, c.grid, 1, 'stroke-dasharray="3 3"' if value == 0 else "")
        c.text(x, bottom + tick_fs + 10, _fmt_axis(value, max_abs * 2), tick_fs, "middle", c.muted)
    y = plot_top
    for row, lines, row_height in zip(rows, layout["labels"], layout["row_heights"]):
        cy = y + row_height / 2
        c.lines(32, cy - (len(lines) - 1) * fs * 0.675 + fs * 0.33, lines, fs)
        color = colors[row["group"]]
        c.line(scale(row["low"]), cy, scale(row["high"]), cy, color, 1.7)
        for value in (row["low"], row["high"]):
            c.line(scale(value), cy - 4, scale(value), cy + 4, color, 1.4)
        c.circle(
            scale(row["estimate"]),
            cy,
            3.6,
            color,
            f'data-role="effect-estimate" data-effect-kind="{"paired-dz" if paired else "cohens-d"}" data-estimate="{row["estimate"]:.12g}" data-low="{row["low"]:.12g}" data-high="{row["high"]:.12g}"',
        )
        estimate_label = f"{row['estimate']:.2f} [{row['low']:.2f}, {row['high']:.2f}]"
        c.text(c.width - 32, cy + tick_fs * 0.33, estimate_label, tick_fs, "end", c.muted)
        y += row_height


def _observation_number(value, span=0):
    """Readable key labels, retaining differences at the displayed range scale."""
    compact = f"{value:.12g}"
    if span > 0 and abs(float(compact) - value) <= span * 1e-6:
        return compact
    return repr(float(value)).removesuffix(".0")


def _frequency_layout(rows, width, paired=False, compact=False):
    fonts = chart_font_sizes(width, width * 0.4, len(rows))
    fs, detail_fs, title_fs = fonts["label"], fonts["foot"], fonts["subtitle"]
    labels = []
    has_bins = any(row["kind"] == "bin" for row in rows)
    for row in rows:
        if row["kind"] == "bin":
            span = row["high"] - row["low"]
            low, high, median = (_observation_number(row[key], span) for key in ("low", "high", "value"))
            label = f"{row['label']} · range [{low}, {high}] · median {median} · {row['count']} observations"
        else:
            label = f"{row['label']} · {_observation_number(row['value'])} × {row['count']} observations"
        labels.append(wrap(label, width - 88, fs))
    heights = [len(lines) * fs * 1.35 + 10 for lines in labels]
    if has_bins:
        description = "Dense observations use display bins at the listed medians; their actual ranges and full counts are retained."
        if paired:
            description += " Paired lines still use the original measurements."
    else:
        description = "Identical values are shown once; the full observation count is retained below."
    explanation = wrap(description, width - 64, detail_fs)
    if compact:
        # Height-constrained key: same facts, one wrapped block without the title row.
        items = []
        for row in rows:
            if row["kind"] == "bin":
                span = row["high"] - row["low"]
                low, high, median = (_observation_number(row[key], span) for key in ("low", "high", "value"))
                items.append(f"{row['label']} [{low}, {high}] median {median} ×{row['count']}")
            else:
                items.append(f"{row['label']} {_observation_number(row['value'])} ×{row['count']}")
        note = (
            "display bins at medians; ranges and counts retained" if has_bins else "repeats drawn once; counts retained"
        )
        text = "; ".join(items) + f" ({note})"
        lines = wrap(text, width - 64, detail_fs)
        return {
            "compact": lines,
            "fs": fs,
            "detail_fs": detail_fs,
            "title_fs": title_fs,
            "height": len(lines) * detail_fs * 1.35 + 12,
        }
    return {
        "labels": labels,
        "heights": heights,
        "explanation": explanation,
        "title": "Aggregated observations" if has_bins else "Repeated observations",
        "fs": fs,
        "detail_fs": detail_fs,
        "title_fs": title_fs,
        "height": title_fs * 1.35 + 24 + len(explanation) * detail_fs * 1.35 + sum(heights),
    }


def _draw_frequency_panel(canvas, rows, layout, top, colors):
    canvas.line(32, top, canvas.width - 32, top, canvas.grid)
    if "compact" in layout:
        canvas.lines(32, top + layout["detail_fs"] + 6, layout["compact"], layout["detail_fs"], color=canvas.muted)
        return
    fs, detail_fs, title_fs = layout["fs"], layout["detail_fs"], layout["title_fs"]
    canvas.text(32, top + title_fs + 8, layout["title"], title_fs, weight=600)
    canvas.lines(32, top + title_fs * 1.35 + detail_fs + 14, layout["explanation"], detail_fs, color=canvas.muted)
    y = top + title_fs * 1.35 + 24 + len(layout["explanation"]) * detail_fs * 1.35
    for row, lines, height in zip(rows, layout["labels"], layout["heights"]):
        color = colors[row["group"]]
        canvas.circle(36, y + 4, 3.2, color)
        canvas.lines(48, y + fs, lines, fs)
        y += height


def render_distribution(
    groups,
    *,
    kind="boxplot",
    variant=None,
    orientation="vertical",
    paired=False,
    conditions=None,
    academic=False,
    pairwise_p=None,
    auto_test=None,
    pairs=None,
    y_min=None,
    y_max=None,
    y_unit="",
    y_title=None,
    bandwidth=None,
    title=None,
    subtitle=None,
    figure_label=None,
    note=None,
    source=None,
    width=1200,
    height=None,
    palette=None,
    font_family=None,
    show_points=True,
    show_boxplot=True,
    show_mean=True,
    show_outliers=True,
    show_legend=True,
    highlight_group=None,
    per_group_n=None,
    effect_size=False,
    auto_effect=0,
):
    if orientation == "mirrored":
        options = locals().copy()
        options.pop("orientation")
        from ._distribution_panels import render_mirrored_distribution

        return render_mirrored_distribution(**options)
    if orientation not in ("vertical", "horizontal"):
        raise ValueError("orientation must be 'vertical' or 'horizontal'")
    facets = _facet_input(conditions) if conditions is not None else [(None, normalize_groups(groups))]
    overlay = variant == "overlay"
    if overlay and any(len(gs) != 2 for _, gs in facets):
        raise ValueError("overlay requires exactly two sample groups in every facet")
    ordered_names = list(dict.fromkeys(g.name for _, gs in facets for g in gs))
    if any({g.name for g in gs} != set(ordered_names) for _, gs in facets):
        raise ValueError("facets must contain the same group names; their order may differ")
    facets = [(name, sorted(gs, key=lambda g: ordered_names.index(g.name))) for name, gs in facets]
    all_groups = [g for _, gs in facets for g in gs]
    if per_group_n is not None and (
        len(per_group_n) != len(ordered_names)
        or any(isinstance(n, bool) or not isinstance(n, int) or n <= 0 for n in per_group_n)
    ):
        raise ValueError("per_group_n must contain one positive integer per group")
    if paired and any(any(identity is None for identity in g.subjects) for g in all_groups):
        raise ValueError("paired=True requires subject_id on every observation")
    if paired and overlay:
        raise ValueError("paired connections require side-by-side distributions")
    density = kind in ("violin", "raincloud")
    domain = sample_domain(all_groups, y_min, y_max, bandwidth, density)
    tests = []
    for name, gs in facets:
        facet_p = pairwise_p.get(name) if isinstance(pairwise_p, dict) else pairwise_p
        tests.append(resolve_tests(gs, academic, facet_p, auto_test, pairs, paired=paired))
    effect_rows = _effect_estimates(facets, paired) if effect_size else []
    if not effect_size and auto_effect and all(len(group.values) >= auto_effect for group in all_groups):
        try:
            effect_rows = _effect_estimates(facets, paired)
        except ValueError:
            effect_rows = []
    width = finite(width, "width")
    effect_layout = _effect_layout(effect_rows, width) if effect_rows else None
    effect_height = effect_layout["height"] + 24 if effect_layout else 0
    if width < 320:
        raise ValueError("distribution canvas width must be at least 320")
    ncols = min(len(facets), max(1, int(width // 440)))
    nrows = math.ceil(len(facets) / ncols)
    outer = 32
    gap = 30
    cell_w = (width - 2 * outer - gap * (ncols - 1)) / ncols
    fonts = chart_font_sizes(cell_w, (height or width * 0.65) / nrows, len(ordered_names))
    fs, axis_fs = fonts["group"], fonts["yaxis"]
    legend_fs, foot_fs = fonts["legend"], fonts["foot"]
    if note or source:
        foot_fs = max(foot_fs, width / 45)
    facet_fs, count_fs = fonts["subtitle"], fonts["group_n"]
    sig_fs = fonts["label"]
    sig_step = sig_fs * 1.35 + 12
    header_fonts = chart_font_sizes(width, height or width * 0.65, len(ordered_names))
    count = 1 if overlay else len(ordered_names)
    colors = _derive_series_colors(_resolve_palette(palette), len(ordered_names), mode="distinct")
    color_by_name = dict(zip(ordered_names, colors))
    points_active = kind == "raincloud" or (
        show_points and not overlay and variant not in ("kde_only", "quartile_outlined", "half_gradient")
    )
    boxes_active = (
        kind in ("boxplot", "raincloud")
        or (show_boxplot and variant not in ("kde_only", "quartile_outlined", "overlay", "half_gradient"))
    ) and variant != "strip_flat"
    quartiles_active = boxes_active or variant in ("quartile_outlined", "overlay")
    legend_items = []
    if show_legend:
        if overlay:
            legend_items = [
                (name, color_by_name[name], 'stroke-dasharray="5 4"' if i else "")
                for i, name in enumerate(ordered_names)
            ]
        else:
            layers = []
            if density:
                layers.append(tr("KDE density"))
            if boxes_active:
                layers.append(tr("Q1–Q3 · median · Tukey whiskers"))
            elif quartiles_active:
                layers.append(tr("quartiles"))
            if boxes_active and show_mean:
                layers.append(tr("mean"))
            if boxes_active and show_outliers and not points_active:
                layers.append(tr("outliers"))
            if points_active:
                layers.append(tr("observations"))
            if paired:
                layers.append(tr("matching subject IDs"))
            if layers:
                legend_items = [(" · ".join(layers), colors[0])]
    legend_rows, legend_height = legend_layout(legend_items, width, legend_fs)
    top = header_height(width, title, subtitle, figure_label, fonts=header_fonts) + legend_height + 12
    footer_lines = []
    for prefix, content in ((tr("Notes. "), note), (tr("Source. "), source)):
        if content:
            footer_lines.extend(wrap(prefix + str(content), width - outer * 2, foot_fs))
    footer_h = len(footer_lines) * foot_fs * 1.35 + (22 if footer_lines else 0)
    axis_title = y_title or ""
    if y_unit and y_unit not in axis_title:
        axis_title = f"{axis_title} ({y_unit})".strip() if axis_title else y_unit
    tick_values, tick_labels, offset_label = axis_ticks(domain)
    offset_h = foot_fs * 1.35 + 8 if offset_label else 0
    cells = []
    for index, (name, gs) in enumerate(facets):
        max_tests = len(tests[index])
        if orientation == "vertical":
            axis_lines = wrap(axis_title, 210, axis_fs) if axis_title else []
            left = max(68, max(measure(label, fs) for label in tick_labels) + 18) + len(axis_lines) * axis_fs * 1.35
            right = 18
            slot = (cell_w - left - right) / count
            if slot < 32:
                raise ValueError("too many groups for vertical layout; increase width or use horizontal")
            label_lines = {g.name: wrap(g.name, slot - (4 if count >= 15 else 12), fs) for g in gs}
            bottom = (
                fs
                + count_fs * 1.35
                + 22
                + (0 if overlay else max(len(lines) for lines in label_lines.values()) * fs * 1.35)
            )
            plot_min_h = 140
            sig_h = max_tests * sig_step
        else:
            label_width = min(cell_w * 0.33, 230)
            label_lines = {g.name: wrap(g.name, label_width - 16, fs) for g in gs}
            left = label_width
            right = max(
                22,
                max(measure(label, fs) for label in tick_labels) / 2 + 8,
                max_tests * sig_step + (sig_fs * 5 if max_tests else 0),
            )
            if cell_w - left - right < 130:
                raise ValueError("canvas too narrow for horizontal annotations")
            axis_lines = wrap(axis_title, cell_w - left - right, axis_fs) if axis_title else []
            bottom = fs * 1.35 + 20 + len(axis_lines) * axis_fs * 1.35
            sig_h = 0
            plot_min_h = count * max(
                30 if kind == "raincloud" else 28,
                max(len(lines) for lines in label_lines.values()) * fs * 1.35 + count_fs * 1.35 + 6,
            )
        facet_lines = wrap(name, cell_w, facet_fs) if name else []
        facet_h = len(facet_lines) * facet_fs * 1.35 + 13 if name else 8
        cells.append(
            {
                "left": left,
                "right": right,
                "bottom": bottom,
                "sig_h": sig_h,
                "labels": label_lines,
                "minimum": plot_min_h + bottom + facet_h + sig_h + offset_h,
                "facet_h": facet_h,
                "facet_lines": facet_lines,
                "axis_lines": axis_lines,
            }
        )
    if orientation == "horizontal":
        available = min(cell_w - cell["left"] - cell["right"] for cell in cells)
        for tick_count in range(6, 1, -1):
            values_candidate, labels_candidate, offset_candidate = axis_ticks(domain, tick_count)
            needed = max(measure(label, fs) for label in labels_candidate) * 1.15 + 16
            if available / (tick_count - 1) >= needed or tick_count == 2:
                tick_values, tick_labels, offset_label = values_candidate, labels_candidate, offset_candidate
                break
    min_cell_h = max(cell["minimum"] for cell in cells)
    base_height = top + min_cell_h * nrows + gap * (nrows - 1) + footer_h + effect_height + 20
    requested_height = None if height is None else finite(height, "height")
    density_ratios = {}

    def plan_at_height(candidate_height, compact=False):
        plans, summaries = {}, []
        if points_active:
            for facet_index, ((facet_name, facet_groups), layout) in enumerate(zip(facets, cells)):
                plot_width = cell_w - layout["left"] - layout["right"]
                plot_height = candidate_height - layout["bottom"] - layout["facet_h"] - layout["sig_h"] - offset_h
                numeric_size = plot_height if orientation == "vertical" else plot_width
                slot_width = (plot_width if orientation == "vertical" else plot_height) / count
                pixel_scale = value_scale(domain, 0, numeric_size)
                for group_index, group in enumerate(facet_groups):
                    key = (facet_index, group_index)
                    lanes = slot_width * (0.21 if kind == "raincloud" else 0.3)
                    if variant == "points_inner_flat":
                        if key not in density_ratios:
                            density_x, density_y = kde(group.values, domain, bandwidth)
                            peak = max(density_y)
                            density_ratios[key] = [
                                density_y[
                                    min(range(len(density_x)), key=lambda k, value=value: abs(density_x[k] - value))
                                ]
                                / peak
                                for value in group.values
                            ]
                        lanes = [max(2.7, ratio * slot_width * 0.30) for ratio in density_ratios[key]]
                    plan = _observation_plan(group.values, [pixel_scale(value) for value in group.values], lanes)
                    plans[key] = plan
                    for marker in plan:
                        if marker["kind"] != "raw":
                            label = f"{facet_name} · {group.name}" if facet_name else group.name
                            summaries.append(
                                {**marker, "label": label, "group": group.name, "count": len(marker["indices"])}
                            )
        summary_layout = _frequency_layout(summaries, width, paired, compact) if summaries else None
        summary_height = summary_layout["height"] + 20 if summary_layout else 0
        return plans, summaries, summary_layout, summary_height

    if requested_height is None:
        cell_h = min_cell_h
        observation_plans, frequency_rows, frequency_layout, frequency_height = plan_at_height(cell_h)
        if any(row["kind"] == "bin" for row in frequency_rows):
            # Modest extra plotting space often preserves ordinary sample points and costs less than a long bin key.
            minimum_plot = max(
                cell["minimum"] - cell["bottom"] - cell["facet_h"] - cell["sig_h"] - offset_h for cell in cells
            )
            best_cost = cell_h * nrows + frequency_height
            for extra in (0.5, 1.0, 2.0):
                candidate_height = min_cell_h + minimum_plot * extra
                candidate = plan_at_height(candidate_height)
                cost = candidate_height * nrows + candidate[3]
                if cost < best_cost:
                    best_cost = cost
                    cell_h = candidate_height
                    observation_plans, frequency_rows, frequency_layout, frequency_height = candidate
        height = base_height + (cell_h - min_cell_h) * nrows + frequency_height
    else:
        height = requested_height
        for compact in (False, True):
            frequency_height = 0
            # Count-key reservations only grow, preventing alternating layouts.
            for _ in range(8):
                minimum_h = base_height + frequency_height
                if height + 1 < minimum_h:
                    break
                cell_h = (height - top - footer_h - effect_height - frequency_height - 20 - gap * (nrows - 1)) / nrows
                observation_plans, frequency_rows, frequency_layout, needed = plan_at_height(cell_h, compact)
                if needed <= frequency_height:
                    break
                frequency_height = needed
            else:
                raise ValueError("count labels require more canvas height for a stable readable layout")
            if height + 1 >= minimum_h:
                break
        else:
            raise ValueError(
                f"distribution canvas height {height:g} is too small; need at least {math.ceil(minimum_h)}"
            )
    c = Canvas(width, height, palette, font_family)
    draw_header(c, title, subtitle, figure_label, fonts=header_fonts)
    legend_y = top - legend_height - 4
    for x, offset, lines, color, extra in legend_rows:
        c.line(x, legend_y + offset, x + 18, legend_y + offset, color, 2, extra)
        c.lines(x + 26, legend_y + offset + 4, lines, legend_fs, color=c.muted)
    for facet_index, ((name, gs), layout) in enumerate(zip(facets, cells)):
        cx = outer + (facet_index % ncols) * (cell_w + gap)
        cy = top + (facet_index // ncols) * (cell_h + gap)
        if name:
            c.lines(cx, cy + facet_fs, layout["facet_lines"], facet_fs, weight=600)
        pl = cx + layout["left"]
        pr = cx + cell_w - layout["right"]
        pt = cy + layout["facet_h"] + layout["sig_h"] + offset_h
        pb = cy + cell_h - layout["bottom"]
        _low, _high = domain
        scale = value_scale(domain, pb, pt) if orientation == "vertical" else value_scale(domain, pl, pr)
        slot = ((pr - pl) if orientation == "vertical" else (pb - pt)) / count
        centers = [(pl if orientation == "vertical" else pt) + slot * (i + 0.5) for i in range(count)]
        if offset_label:
            c.text(pl, pt - 9, offset_label, foot_fs, color=c.muted)
        for value, label in zip(tick_values, tick_labels):
            pixel = scale(value)
            if orientation == "vertical":
                c.line(pl, pixel, pr, pixel, c.grid, 0.8)
                c.text(pl - 10, pixel + fs * 0.32, label, fs, "end", c.muted)
            else:
                c.line(pixel, pt, pixel, pb, c.grid, 0.8)
                c.text(pixel, pb + fs + 10, label, fs, "middle", c.muted)
        c.line(pl, pb, pr, pb, c.grid)
        if axis_title:
            if orientation == "vertical":
                for line_index, axis_line in enumerate(layout["axis_lines"]):
                    x = cx + axis_fs * 0.85 + line_index * axis_fs * 1.35
                    c.text(
                        x,
                        (pt + pb) / 2,
                        axis_line,
                        axis_fs,
                        "middle",
                        c.muted,
                        extra=f'transform="rotate(-90 {x:.3f} {(pt + pb) / 2:.3f})"',
                    )
            else:
                c.lines((pl + pr) / 2, pb + fs * 1.35 + axis_fs + 14, layout["axis_lines"], axis_fs, "middle", c.muted)
        point_sets = []

        def xy(category, value_pixel):
            return (category, value_pixel) if orientation == "vertical" else (value_pixel, category)

        for index, group in enumerate(gs):
            center = centers[0 if overlay else index]
            point_center = center + slot * 0.29 if kind == "raincloud" else center
            coords = [xy(point_center, scale(value)) for value in group.values]
            for marker in observation_plans.get((facet_index, index), []):
                for observation_index in marker["indices"]:
                    # Never move a subject's measured coordinate to a bin median.
                    coords[observation_index] = xy(
                        point_center + marker["offset"], scale(group.values[observation_index])
                    )
            point_sets.append(coords)
        if paired:
            for i in range(len(gs) - 1):
                first = dict(zip(gs[i].subjects, point_sets[i]))
                second = dict(zip(gs[i + 1].subjects, point_sets[i + 1]))
                first_values = dict(zip(gs[i].subjects, gs[i].values))
                second_values = dict(zip(gs[i + 1].subjects, gs[i + 1].values))
                for identity in first.keys() & second.keys():
                    c.line(
                        *first[identity],
                        *second[identity],
                        _rgba_with_alpha(c.ink, 0.2),
                        0.8,
                        f'data-role="paired-connection" data-subject-id="{_xesc(identity)}" data-value-start="{first_values[identity]:.17g}" data-value-end="{second_values[identity]:.17g}"',
                    )
        for index, group in enumerate(gs):
            center = centers[0 if overlay else index]
            color = color_by_name[group.name]
            stats = sample_stats(group.values)
            if density:
                values, densities = kde(group.values, domain, bandwidth)
                maximum = max(densities) or 1
                half = slot * (0.34 if not overlay else 0.32)
                positive = [(center + d / maximum * half, scale(v)) for v, d in zip(values, densities)]
                if kind == "raincloud" or variant == "half_gradient":
                    left = [(center - slot * 0.10 - d / maximum * half, scale(v)) for v, d in zip(values, densities)]
                    outline = left + [
                        (center - slot * 0.10, scale(values[-1])),
                        (center - slot * 0.10, scale(values[0])),
                    ]
                else:
                    outline = positive + [
                        (center - d / maximum * half, scale(v)) for v, d in reversed(list(zip(values, densities)))
                    ]
                if orientation == "horizontal":
                    outline = [(y, x) for x, y in outline]
                dash = 'stroke-dasharray="5 4"' if overlay and index == 1 else ""
                fill = (
                    "none"
                    if variant == "quartile_outlined" or (overlay and index == 1)
                    else _rgba_with_alpha(color, 0.24)
                )
                if variant == "half_gradient":
                    gradient_id = f"distribution-density-{facet_index}-{index}"
                    c.parts.append(
                        f'<defs><linearGradient id="{gradient_id}" x1="0" y1="0" x2="1" y2="0"><stop offset="0%" stop-color="{color}" stop-opacity="0.10"/><stop offset="100%" stop-color="{color}" stop-opacity="0.48"/></linearGradient></defs>'
                    )
                    fill = f"url(#{gradient_id})"
                c.path(outline, color, fill, 1.7, True, f'{dash} data-role="density" data-group="{_xesc(group.name)}"')
                if variant == "quartile_outlined" or overlay:
                    for probability in (0.25, 0.5, 0.75):
                        q = quantile(group.values, probability)
                        near = min(range(len(values)), key=lambda k: abs(values[k] - q))
                        h = densities[near] / maximum * half
                        c.line(*xy(center - h, scale(q)), *xy(center + h, scale(q)), color, 1.3, dash)
            draw_box = boxes_active
            if draw_box:
                half = min(24, slot * (0.065 if density else 0.18))
                if variant == "variable_width_gradient":
                    half *= math.sqrt(stats["n"] / max(len(g.values) for g in gs))
                box_fill = "none" if variant == "notched_outlined" else None
                if variant == "variable_width_gradient":
                    gradient_id = f"distribution-box-{facet_index}-{index}"
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
                    orientation,
                    show_mean,
                    variant == "notched_outlined",
                    f'data-role="box" data-group="{_xesc(group.name)}"',
                    fill=box_fill,
                )
            if points_active:
                point_center = center + slot * 0.29 if kind == "raincloud" else center
                for marker in observation_plans[facet_index, index]:
                    number = marker["indices"][0]
                    multiplicity = len(marker["indices"])
                    identity = group.subjects[number]
                    identity_attr = (
                        f' data-subject-id="{_xesc(identity)}"' if identity is not None and multiplicity == 1 else ""
                    )
                    role = {"raw": "observation", "frequency": "observation-frequency", "bin": "observation-bin"}[
                        marker["kind"]
                    ]
                    range_attr = (
                        f' data-low="{marker["low"]:.17g}" data-high="{marker["high"]:.17g}" data-representative="median"'
                        if marker["kind"] == "bin"
                        else ""
                    )
                    c.circle(
                        *xy(point_center + marker["offset"], scale(marker["value"])),
                        marker["radius"],
                        color,
                        f'fill-opacity="0.9" data-role="{role}" data-count="{multiplicity}" data-value="{marker["value"]:.17g}"{identity_attr}{range_attr}',
                    )
            elif show_outliers and draw_box:
                for value in group.values:
                    if value < stats["lo"] or value > stats["hi"]:
                        c.circle(
                            *xy(center, scale(value)),
                            2.5,
                            c.bg,
                            f'stroke="{color}" stroke-width="1.2" data-role="outlier" data-value="{value:.17g}"',
                        )
            if not overlay:
                label_lines = layout["labels"][group.name]
                if orientation == "vertical":
                    c.lines(
                        center,
                        pb + fs + 10,
                        label_lines,
                        fs,
                        "middle",
                        weight=600 if group.name == highlight_group else 400,
                    )
                    label_n = per_group_n[index] if per_group_n is not None else len(group.values)
                    c.text(
                        center,
                        pb + fs + 10 + len(label_lines) * fs * 1.35 + 4,
                        f"n = {label_n}",
                        count_fs,
                        "middle",
                        c.muted,
                    )
                else:
                    text_y = center - (len(label_lines) - 1) * fs * 0.675 - 3
                    c.lines(
                        pl - 14, text_y, label_lines, fs, "end", weight=600 if group.name == highlight_group else 400
                    )
                    c.text(
                        pl - 14,
                        text_y + len(label_lines) * fs * 1.35 + 1,
                        f"n = {per_group_n[index] if per_group_n is not None else len(group.values)}",
                        count_fs,
                        "end",
                        c.muted,
                    )
        for tier, (a, b, p) in enumerate(tests[facet_index]):
            if overlay:
                c.text(
                    (pl + pr) / 2,
                    pt - offset_h - 10 - tier * sig_step,
                    p_label(p),
                    sig_fs,
                    "middle",
                    extra='data-role="significance"',
                )
            elif orientation == "vertical":
                y = pt - offset_h - 9 - tier * sig_step
                c.path([(centers[a], y + 5), (centers[a], y), (centers[b], y), (centers[b], y + 5)], c.ink, stroke=1)
                c.text(
                    (centers[a] + centers[b]) / 2, y - 5, p_label(p), sig_fs, "middle", extra='data-role="significance"'
                )
            else:
                x = pr + 12 + tier * sig_step
                c.path([(x - 5, centers[a]), (x, centers[a]), (x, centers[b]), (x - 5, centers[b])], c.ink, stroke=1)
                c.text(
                    x + 13,
                    (centers[a] + centers[b]) / 2,
                    p_label(p),
                    sig_fs,
                    "middle",
                    extra=f'transform="rotate(-90 {x + 13:.3f} {(centers[a] + centers[b]) / 2:.3f})" data-role="significance"',
                )
    if frequency_layout:
        frequency_top = height - footer_h - effect_height - frequency_height
        _draw_frequency_panel(c, frequency_rows, frequency_layout, frequency_top, color_by_name)
    if effect_layout:
        effect_top = height - footer_h - effect_height
        _draw_effect_panel(c, effect_rows, effect_layout, effect_top, paired, color_by_name)
    if footer_lines:
        footer_top = height - footer_h
        c.line(outer, footer_top + 4, width - outer, footer_top + 4, c.grid)
        c.lines(outer, footer_top + 12 + foot_fs * 0.84, footer_lines, foot_fs, color=c.muted)
    return c.svg()
