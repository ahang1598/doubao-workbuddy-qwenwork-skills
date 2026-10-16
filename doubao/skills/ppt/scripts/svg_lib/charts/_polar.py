"""Shared polar coordinates and data-preserving radial marks (stdlib only)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from xml.sax.saxutils import quoteattr

from .._common import _resolve_palette, _rgba_with_alpha
from ._academic_rigor import SeriesContext, SharedScale
from ._chart_layout import ChartLayout, finite, wrap_lines
from ._distribution import axis_ticks
from ._matrix_core import ColorScale


def canonical_palette(palette):
    """Polar grid contrast on top of the shared, CSS-aware palette parser."""
    pal = _resolve_palette(palette)
    if not isinstance(palette, dict) or "grid" not in palette:
        pal["grid"] = _rgba_with_alpha(pal["ink"], 0.16)
    return pal


def polar_layout(width, height, palette, font_family, n_items=None):
    return ChartLayout(width, height, canonical_palette(palette), font_family, n_items=n_items)


def categories_order(categories, order=None):
    cats = [dict(c) if isinstance(c, dict) else {"name": str(c)} for c in categories]
    for cat in cats:
        if "name" not in cat:
            raise ValueError("categories require a name")
        cat["name"] = str(cat["name"])
    names = [c["name"] for c in cats]
    if not cats or len(set(names)) != len(cats):
        raise ValueError("categories must contain unique names")
    ordered = names if order is None else [str(v) for v in order]
    if len(ordered) != len(names) or set(ordered) != set(names):
        raise ValueError("order must contain every category exactly once")
    indices = [names.index(v) for v in ordered]
    return [cats[i] for i in indices], indices


def observation(raw):
    if raw is None:
        return None
    point = dict(raw) if isinstance(raw, dict) else {"value": raw}
    point["value"] = finite(point.get("value"), "value")
    if ("low" in point) != ("high" in point):
        raise ValueError("error limits require both low and high")
    if "low" in point:
        point["low"], point["high"] = finite(point["low"], "low"), finite(point["high"], "high")
        if not point["low"] <= point["value"] <= point["high"]:
            raise ValueError("error limits require low <= value <= high")
    return point


def normalize_series(series, indices):
    result, names = [], set()
    for i, raw in enumerate(series or []):
        if not isinstance(raw, dict):
            raise TypeError("series entries must be dictionaries")
        s = dict(raw)
        s["name"] = str(s.get("name", f"Series {i + 1}"))
        if s["name"] in names:
            raise ValueError("series names must be unique within a panel")
        names.add(s["name"])
        s["kind"] = s.get("kind", "bar")
        if s["kind"] not in {"bar", "line", "point", "box", "violin"}:
            raise ValueError("series kind must be bar, line, point, box or violin")
        s["direction"] = s.get("direction", "out")
        if s["direction"] not in {"out", "in"}:
            raise ValueError("direction must be out or in")
        key = "samples" if s["kind"] in {"box", "violin"} else "values"
        if key not in s or len(s[key]) != len(indices):
            raise ValueError(f"{s['name']}: {key} must align with categories")
        if key == "samples":
            s[key] = [None if s[key][j] is None else [finite(v, "sample") for v in s[key][j]] for j in indices]
            if any(values == [] for values in s[key]):
                raise ValueError("sample groups must be nonempty or None")
            if "bandwidth" in s:
                s["bandwidth"] = finite(s["bandwidth"], "bandwidth", minimum=0)
                if s["bandwidth"] == 0:
                    raise ValueError("bandwidth must be positive")
        else:
            s[key] = [observation(s[key][j]) for j in indices]
        result.append(s)
    return result


def numeric_domain(values, limits=None, *, include_zero=False):
    if not values and limits is None:
        raise ValueError("no observed values; supply an explicit range for missing data")
    if limits is not None:
        if len(limits) != 2:
            raise ValueError("range must be [minimum, maximum]")
        low, high = (finite(v, "range") for v in limits)
        if high <= low:
            raise ValueError("range maximum must exceed minimum")
        if any(v < low or v > high for v in values):
            raise ValueError("range must contain every observation and error endpoint")
        if include_zero and not low <= 0 <= high:
            raise ValueError("bar ranges must contain the zero baseline")
    else:
        low, high = min(values), max(values)
        if include_zero:
            low, high = min(0.0, low), max(0.0, high)
        if high == low:
            delta = abs(low) * 0.1 or 1.0
            low, high = (0.0, delta) if include_zero and low == 0 else (low - delta, high + delta)
        elif not include_zero:
            pad = (high - low) * 0.05
            low, high = low - pad, high + pad
    if not math.isfinite(high - low) or not high > low:
        raise ValueError("range span must be finite and positive")
    return low, high


@dataclass
class PolarGeometry:
    cx: float
    cy: float
    inner: float
    outer: float
    count: int
    sweep: float = 360.0
    start: float = -90.0

    def __post_init__(self):
        if not 0 <= self.inner < self.outer or self.count < 1:
            raise ValueError("polar geometry needs positive radii and categories")
        self.sweep = finite(self.sweep, "sweep", minimum=1)
        if self.sweep > 360:
            raise ValueError("sweep must be at most 360 degrees")
        if self.sweep < 360:
            # Center a partial fan above its baseline.
            self.start = -90 - self.sweep / 2

    def angle(self, index):
        return math.radians(self.start + (index + 0.5) * self.sweep / self.count)

    @property
    def step(self):
        return math.radians(self.sweep / self.count)

    def point(self, radius, angle):
        return self.cx + radius * math.cos(angle), self.cy + radius * math.sin(angle)

    def radius(self, value, scale, direction="out", mode="linear"):
        a, b = (self.inner, self.outer) if direction == "out" else (self.outer, self.inner)
        if mode == "area":
            return math.sqrt(max(0.0, scale.map(value, a * a, b * b)))
        return scale.map(value, a, b)

    def sector(self, r0, r1, a0, a1):
        r0, r1 = sorted((r0, r1))
        if r1 == 0:
            return ""
        # Full circles need two arcs in SVG; half-arcs also remain numerically stable.
        segments = max(1, math.ceil(abs(a1 - a0) / math.pi))
        angles = [a0 + (a1 - a0) * j / segments for j in range(segments + 1)]
        x, y = self.point(r1, angles[0])
        d = [f"M{x:.4f},{y:.4f}"]
        for angle in angles[1:]:
            x, y = self.point(r1, angle)
            d.append(f"A{r1:.4f},{r1:.4f} 0 0 1 {x:.4f},{y:.4f}")
        x, y = self.point(r0, angles[-1])
        d.append(f"L{x:.4f},{y:.4f}")
        if r0:
            for angle in reversed(angles[:-1]):
                x, y = self.point(r0, angle)
                d.append(f"A{r0:.4f},{r0:.4f} 0 0 0 {x:.4f},{y:.4f}")
        d.append("Z")
        return " ".join(d)

    def arc(self, radius, start=None, end=None):
        a0 = math.radians(self.start) if start is None else start
        a1 = math.radians(self.start + self.sweep) if end is None else end
        segments = max(1, math.ceil(abs(a1 - a0) / math.pi))
        points = [self.point(radius, a0 + (a1 - a0) * j / segments) for j in range(segments + 1)]
        return f"M{points[0][0]:.4f},{points[0][1]:.4f} " + " ".join(
            f"A{radius:.4f},{radius:.4f} 0 0 1 {x:.4f},{y:.4f}" for x, y in points[1:]
        )


def path(points, closed=False):
    if not points:
        return ""
    return " ".join(f"{'M' if i == 0 else 'L'}{x:.4f},{y:.4f}" for i, (x, y) in enumerate(points)) + (
        " Z" if closed else ""
    )


def stroke(layout, d, color=None, width=1, **attrs):
    extras = " ".join(f"{key.replace('_', '-')}={quoteattr(str(value))}" for key, value in attrs.items())
    layout.parts.append(
        f'<path d="{d}" fill="none" stroke={quoteattr(color or layout.pal["grid"])} stroke-width="{width}" {extras}/>'
    )


def sector_mark(layout, geometry, r0, r1, a0, a1, color, *, opacity=1, role="bar", attrs=""):
    layout.parts.append(
        f'<path d="{geometry.sector(r0, r1, a0, a1)}" fill={quoteattr(color)} fill-opacity="{opacity}" '
        f'stroke={quoteattr(layout.pal.get("bg") or "#fff")} stroke-width=".7" data-role="{role}" '
        f'data-inner="{min(r0, r1):.12g}" data-outer="{max(r0, r1):.12g}" {attrs}/>'
    )


def circle_mark(layout, point, color, *, radius=3, role="point", attrs=""):
    x, y = point
    layout.parts.append(
        f'<circle cx="{x:.4f}" cy="{y:.4f}" r="{radius}" fill={quoteattr(color)} data-role="{role}" {attrs}/>'
    )


def error_mark(layout, geometry, scale, item, angle, color, direction, mode):
    if "low" not in item:
        return
    low, high = (geometry.radius(item[key], scale, direction, mode) for key in ("low", "high"))
    stroke(
        layout,
        path([geometry.point(low, angle), geometry.point(high, angle)]),
        color,
        1.25,
        data_role="error",
        data_low=item["low"],
        data_high=item["high"],
        data_r_low=low,
        data_r_high=high,
    )
    for radius in (low, high):
        x, y = geometry.point(radius, angle)
        tx, ty = 3.2 * math.sin(angle), -3.2 * math.cos(angle)
        stroke(layout, path([(x - tx, y - ty), (x + tx, y + ty)]), color, 1.25)


def normalize_tracks(tracks, indices, palette):
    result = []
    names = set()
    for i, raw in enumerate(tracks or []):
        t = dict(raw)
        t["name"] = str(t.get("name", f"Track {i + 1}"))
        if t["name"] in names:
            raise ValueError("track names must be unique")
        names.add(t["name"])
        kind = t["kind"] = t.get("kind", "heatmap")
        if kind not in {"heatmap", "category", "bar", "point"}:
            raise ValueError("track kind must be heatmap, category, bar or point")
        if "values" not in t or len(t["values"]) != len(indices):
            raise ValueError("track values must align with categories")
        t["values"] = [t["values"][i] for i in indices]
        t["direction"] = t.get("direction", "out")
        if t["direction"] not in {"out", "in"}:
            raise ValueError("track direction must be out or in")
        if kind == "category":
            t["values"] = [None if v is None else str(v) for v in t["values"]]
            keys = list(dict.fromkeys(v for v in t["values"] if v is not None))
            context = SeriesContext(keys, pal=palette)
            colors = t.get("colors", {})
            t["_colors"] = {v: colors.get(v, context.color_of(v)) for v in keys}
        else:
            t["values"] = [None if v is None else finite(v, "track value") for v in t["values"]]
            vals = [v for v in t["values"] if v is not None]
            if kind == "heatmap":
                limits = t.get("range")
                if limits is not None and (len(limits) != 2 or any(v < limits[0] or v > limits[1] for v in vals)):
                    raise ValueError("heatmap range must contain every observation")
                t["_scale"] = ColorScale.from_values(
                    vals,
                    palette,
                    vmin=limits[0] if limits else None,
                    vmax=limits[1] if limits else None,
                    midpoint=t.get("midpoint"),
                )
            else:
                t["_scale"] = SharedScale(numeric_domain(vals, t.get("range"), include_zero=kind == "bar"))
        result.append(t)
    return result


def render_tracks(layout, geometry, tracks, start_radius, thickness, *, angles=None, gap=4):
    """Render rings without a canvas; optional sector bounds support chord nodes."""
    for index, track in enumerate(tracks):
        r0 = start_radius + index * (thickness + gap)
        r1 = r0 + thickness
        tg = PolarGeometry(geometry.cx, geometry.cy, r0, r1, geometry.count, geometry.sweep, geometry.start)
        kind = track["kind"]
        color = track.get("color", layout.pal["accent"])
        for i, value in enumerate(track["values"]):
            if angles is None:
                a0, a1 = tg.angle(i) - tg.step * 0.475, tg.angle(i) + tg.step * 0.475
            else:
                a0, a1 = angles[i]
            angle = (a0 + a1) / 2
            attrs = f'data-track={quoteattr(track["name"])} data-category-index="{i}"'
            if value is None:
                sector_mark(layout, tg, r0, r1, a0, a1, layout.pal["ink1"], role="missing", attrs=attrs)
                continue
            if kind in {"heatmap", "category"}:
                fill = track["_colors"][value] if kind == "category" else track["_scale"].color(value)
                sector_mark(
                    layout,
                    tg,
                    r0,
                    r1,
                    a0,
                    a1,
                    fill,
                    role="track-cell",
                    attrs=attrs + f" data-value={quoteattr(str(value))}",
                )
            else:
                scale = track["_scale"]
                radius = tg.radius(value, scale, track["direction"])
                stroke(layout, tg.arc(r0, a0, a1), layout.pal["grid"], 0.6)
                stroke(layout, tg.arc(r1, a0, a1), layout.pal["grid"], 0.6)
                if kind == "bar":
                    sector_mark(
                        layout,
                        tg,
                        tg.radius(0, scale, track["direction"]),
                        radius,
                        a0,
                        a1,
                        color,
                        role="track-bar",
                        attrs=attrs + f' data-value="{value}"',
                    )
                else:
                    circle_mark(
                        layout,
                        tg.point(radius, angle),
                        color,
                        radius=2.4,
                        role="track-point",
                        attrs=attrs + f' data-value="{value}"',
                    )
    return start_radius + len(tracks) * (thickness + gap) - (gap if tracks else 0)


def label_requirements(layout, categories, width=145, fs=None):
    fs = layout.font_sizes["label"] if fs is None else fs
    heights = [
        len(wrap_lines(c["name"] + (f" · {c['annotation']}" if c.get("annotation") else ""), width, fs, layout.font))
        * fs
        * 1.35
        + 5
        for c in categories
    ]
    # Conservatively give either side enough rows for half the categories plus two.
    return max(100.0, sum(sorted(heights, reverse=True)[: math.ceil(len(heights) / 2) + 2]))


def render_labels(layout, geometry, categories, radius, top, bottom, *, left=28, right=None, rail_width=145):
    right = layout.width - 28 if right is None else right
    groups = {-1: [], 1: []}
    fs = layout.font_sizes["label"]
    for i, cat in enumerate(categories):
        angle = geometry.angle(i)
        x, y = geometry.point(radius + 5, angle)
        side = 1 if math.cos(angle) >= 0 else -1
        label = cat["name"] + (f" · {cat['annotation']}" if cat.get("annotation") else "")
        lines = wrap_lines(label, rail_width, fs, layout.font)
        h = len(lines) * fs * 1.35
        groups[side].append({"i": i, "x": x, "y": y, "lines": lines, "h": h, "label": label})
    for side, items in groups.items():
        items.sort(key=lambda item: item["y"])
        used = top
        for item in items:
            item["top"] = max(used, item["y"] - item["h"] / 2)
            used = item["top"] + item["h"] + 5
        if items:
            overflow = max(0.0, used - 5 - bottom)
            for item in reversed(items):
                item["top"] -= overflow
                bottom_here = item["top"] - 5
                pos = items.index(item)
                if pos:
                    overflow = max(0.0, items[pos - 1]["top"] + items[pos - 1]["h"] - bottom_here)
        for item in items:
            tx = left if side < 0 else right
            edge = tx + rail_width + 7 if side < 0 else tx - rail_width - 7
            end_y = item["top"] + item["h"] / 2
            elbow = geometry.cx + side * (radius + 14)
            stroke(
                layout,
                path([(item["x"], item["y"]), (elbow, item["y"]), (edge, end_y)]),
                layout.pal["ink2"],
                0.7,
                data_role="label-leader",
            )
            layout.text(item["label"], tx, item["top"], fs=fs, width=rail_width, anchor="start" if side < 0 else "end")


def legend_rows(layout, series, tracks, width=None):
    width = width or layout.width - 56
    context = SeriesContext([s["name"] for s in series], pal=layout.pal)
    entries = []
    for s in series:
        name = s["name"] + (" · inward" if s["direction"] == "in" else "")
        color = s.get("color", context.color_of(s["name"]))
        if isinstance(color, dict):
            values = [v["value"] for v in s.get("values", []) if v is not None]
            limits = color.get("range")
            if limits:
                numeric_domain(values, limits)
            color = ColorScale.from_values(
                values,
                layout.pal,
                vmin=limits[0] if limits else None,
                vmax=limits[1] if limits else None,
                midpoint=color.get("midpoint"),
            )
            name += f" [{color.low:.3g}, {color.high:.3g}]"
        entries.append((name, color))
    for i, track in enumerate(tracks):
        name = f"{i + 1}. {track['name']}"
        if track["kind"] == "category":
            entries.extend((f"{name} · {key}", color) for key, color in track["_colors"].items())
        else:
            scale = track["_scale"]
            lo, hi = (scale.low, scale.high) if track["kind"] == "heatmap" else scale.domain
            _, labels, offset = axis_ticks((lo, hi), 2) if hi > lo else ([], [f"{lo:.5g}", f"{hi:.5g}"], "")
            name += f" [{labels[0]}, {labels[-1]}]" + (f" · {offset}" if offset else "")
            if track["direction"] == "in":
                name += " · inward"
            entries.append((name, scale if track["kind"] == "heatmap" else track.get("color", layout.pal["accent"])))
    fs = layout.font_sizes["legend"]
    rows, x, y, rh = [], 0.0, 0.0, 0.0
    for name, color in entries:
        if isinstance(color, dict):
            color = layout.pal["accent"]
        label_width = min(width - 24, 270)
        lines = wrap_lines(name, label_width, fs, layout.font)
        w = min(width, max(layout.measure(line, fs) for line in lines) + (57 if isinstance(color, ColorScale) else 33))
        h = len(lines) * fs * 1.35 + 8
        if x and x + w > width:
            y += rh
            x, rh = 0.0, 0.0
        rows.append((x, y, name, color, label_width))
        x += w
        rh = max(rh, h)
    return rows, y + rh


def render_legend(layout, rows, top, left=28):
    for x, y, name, color, width in rows:
        if isinstance(color, ColorScale):
            for i in range(8):
                shade = color.color(color.value_at(i / 7))
                layout.parts.append(
                    f'<rect x="{left + x + i * 4:.2f}" y="{top + y + 3:.2f}" width="4.1" height="10" fill={quoteattr(shade)}/>'
                )
            offset = 39
        else:
            layout.parts.append(
                f'<rect x="{left + x:.2f}" y="{top + y + 3:.2f}" width="10" height="10" rx="2" fill={quoteattr(color)}/>'
            )
            offset = 16
        layout.text(name, left + x + offset, top + y, fs=layout.font_sizes["legend"], width=width)
