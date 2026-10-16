"""Shared, data-preserving Cartesian layers and measured chart framing."""

from __future__ import annotations

import math
from collections import defaultdict
from copy import deepcopy
from xml.sax.saxutils import quoteattr

from .._common import _estimate_label_width_px, _resolve_font, _resolve_palette, _tick_decimals, _xesc
from .._typography import chart_font_sizes
from ._academic_rigor import BBox, SeriesContext, SharedScale, _student_t_sf, nice_axis, student_t_critical
from ._chart_layout import ChartLayout, axis_caption, finite, parse_p, readable_annotation_color, wrap_lines
from ._xy_geometry import marker_obstacle, obstacle_box, route_leader, segment_obstacle
from ._shared import tr


def xy_density(series):
    """Visible categories or observations; prediction knots never count as samples."""
    categories = {
        (axis, point[axis])
        for item in series
        for point in item.get("points", []) + item.get("curve", [])
        for axis in ("x", "y")
        if isinstance(point[axis], str)
    }
    if categories:
        return max(len(categories), len({item["name"] for item in series}))
    observations = sum(len(item.get("points", [])) for item in series)
    return observations or len({item["name"] for item in series})


def _coord(value, name):
    if isinstance(value, str) and value:
        return value
    return finite(value, name)


def _error(value, name):
    if isinstance(value, (list, tuple)):
        if len(value) != 2:
            raise ValueError(f"{name} must be a magnitude or [minus, plus]")
        return tuple(finite(v, name, minimum=0) for v in value)
    v = finite(value, name, minimum=0)
    return (v, v)


def normalize_series(series):
    """Validate/copy canonical series."""
    out = []
    names = set()
    for i, raw in enumerate(series):
        if not isinstance(raw, dict):
            raise TypeError("series must be dictionaries with points and/or curve")
        name = str(raw.get("name", f"Series {i + 1}"))
        if name in names:
            raise ValueError(f"duplicate series name: {name!r}")
        names.add(name)
        s = dict(raw, name=name)
        marker = s.get("marker", "circle")
        if marker not in ("circle", "square", "triangle", "diamond", "none"):
            raise ValueError("marker must be circle, square, triangle, diamond or none")
        s["marker"] = marker
        fit = s.get("fit")
        if fit not in (None, "none", "linear", "loess"):
            raise ValueError("fit must be linear, loess, none or None")
        s["fit"] = fit
        s["points"], s["curve"] = [], []
        for field in ("points", "curve"):
            for j, item in enumerate(raw.get(field, [])):
                p = dict(item) if isinstance(item, dict) else dict(zip(("x", "y"), item))
                if "x" not in p or "y" not in p:
                    raise ValueError(f"{name} {field}[{j}] needs x and y")
                p["x"], p["y"] = _coord(p["x"], "x"), _coord(p["y"], "y")
                if field == "points":
                    for key in ("x_err", "y_err"):
                        if key in p:
                            p[key] = _error(p[key], key)
                    if "size" in p:
                        p["size"] = finite(p["size"], "size", minimum=0)
                    if p.get("marker", marker) not in ("circle", "square", "triangle", "diamond", "none"):
                        raise ValueError("unknown point marker")
                else:
                    if ("lo" in p) != ("hi" in p):
                        raise ValueError("curve confidence limits require both lo and hi")
                    if "lo" in p:
                        p["lo"], p["hi"] = finite(p["lo"], "lo"), finite(p["hi"], "hi")
                        if not p["lo"] <= p["y"] <= p["hi"]:
                            raise ValueError("curve limits must satisfy lo <= y <= hi")
                s[field].append(p)
        if s["curve"] and fit not in (None, "none"):
            raise ValueError("supply a precomputed curve or a fit, not both")
        if s.get("dashed_from") is not None:
            s["dashed_from"] = finite(s["dashed_from"], "dashed_from")
        if not s["points"] and not s["curve"]:
            continue
        # Curves are functions, not trajectories. Stable sorting preserves
        # duplicate-x steps without manufacturing a path through row order.
        if s["curve"] and all(isinstance(p["x"], float) for p in s["curve"]):
            s["curve"].sort(key=lambda p: p["x"])
        out.append(s)
    if not out:
        raise ValueError("at least one observation or curve sample is required")
    return out


def points_to_series(points, *, fit=None, highlight_mask=None):
    """Legacy point adapter; a group field assigns categorical series identity."""
    if points and isinstance(points[0], dict) and ("points" in points[0] or "curve" in points[0]):
        if highlight_mask is not None:
            raise ValueError("highlight_mask is only supported for a flat observation list")
        return normalize_series([dict(s, fit=s.get("fit", None if s.get("curve") else fit)) for s in points])
    if highlight_mask is not None and len(highlight_mask) != len(points):
        raise ValueError("highlight_mask length mismatch")
    groups = {}
    for i, raw in enumerate(points):
        p = dict(raw) if isinstance(raw, dict) else {"x": raw[0], "y": raw[1]}
        group = str(p.pop("group", tr("Observations")))
        if highlight_mask is not None and highlight_mask[i]:
            p["_highlight"] = True
        if group not in groups:
            groups[group] = {"name": group, "points": [], "fit": fit}
        groups[group]["points"].append(p)
    return normalize_series(list(groups.values()))


def linreg(xs, ys):
    """OLS with centered arithmetic and the exact two-sided Student-t test."""
    n = len(xs)
    if n < 2:
        return 0.0, 0.0, 0.0, 1.0, 0.0, 0.0
    mx, my = math.fsum(xs) / n, math.fsum(ys) / n
    dx, dy = [x - mx for x in xs], [y - my for y in ys]
    sxx = math.fsum(v * v for v in dx)
    syy = math.fsum(v * v for v in dy)
    slope = math.fsum(a * b for a, b in zip(dx, dy)) / sxx if sxx else 0.0
    ssr = math.fsum((b - slope * a) ** 2 for a, b in zip(dx, dy))
    rmse = math.sqrt(ssr / max(1, n - 2))
    se = rmse / math.sqrt(sxx) if sxx else 0.0
    t = abs(slope / se) if se else (math.inf if slope else 0.0)
    p = 2 * _student_t_sf(t, n - 2) if n >= 3 and sxx else 1.0
    return slope, my - slope * mx, max(0.0, 1 - ssr / syy) if syy else 0.0, max(1e-300, p), se, rmse


def loess(xs, ys, sample_xs, span=0.45):
    """Nearest-neighbour tricube local-linear fit, centered at each target."""
    n = len(xs)
    if n < 3:
        raise ValueError("LOESS requires at least three observations")
    k = min(n, max(3, math.ceil(n * span)))
    result = []
    for x0 in sample_xs:
        distances = sorted(abs(x - x0) for x in xs)
        bw = distances[k - 1] * (1 + 1e-9)
        if bw == 0:
            near = [y for x, y in zip(xs, ys) if x == x0]
            result.append((x0, math.fsum(near) / len(near)))
            continue
        ws = [(1 - min(1.0, abs(x - x0) / bw) ** 3) ** 3 for x in xs]
        sw = math.fsum(ws)
        dx = [x - x0 for x in xs]
        mx, my = math.fsum(w * x for w, x in zip(ws, dx)) / sw, math.fsum(w * y for w, y in zip(ws, ys)) / sw
        sxx = math.fsum(w * (x - mx) ** 2 for w, x in zip(ws, dx))
        slope = math.fsum(w * (x - mx) * (y - my) for w, x, y in zip(ws, dx, ys)) / sxx if sxx else 0
        result.append((x0, my - slope * mx))
    return result


def _predict_model(model, transformed_xs):
    """Evaluate the fitted model in its fitting coordinates, without curve interpolation."""
    if model["kind"] == "loess":
        return [y for _, y in loess(model["xs"], model["ys"], transformed_xs)]
    return [model["center_y"] + model["slope"] * (x - model["center_x"]) for x in transformed_xs]


def fit_series(series, *, show_ci=True, x_transform="linear", y_transform="linear"):
    """Resolve fits into independent curves in the requested coordinate space."""
    out = deepcopy(series)
    for s in out:
        if s.get("fit") in (None, "none"):
            continue
        pts = s["points"]
        if len(pts) < 2:
            raise ValueError(f"{s['name']}: fitting requires at least two observations")

        def transform(v, mode):
            if isinstance(v, str) or (mode == "log10" and v <= 0):
                raise ValueError("fits require numerical coordinates valid on their axes")
            return math.log10(v) if mode == "log10" else v

        xs = [transform(p["x"], x_transform) for p in pts]
        ys = [transform(p["y"], y_transform) for p in pts]
        if min(xs) == max(xs):
            raise ValueError(f"{s['name']}: fitting requires distinct x values")
        samples = [min(xs) + (max(xs) - min(xs)) * i / 100 for i in range(101)]
        mx, my = math.fsum(xs) / len(xs), math.fsum(ys) / len(ys)
        b, _intercept, r2, pval, _slope_se, rmse = linreg(xs, ys)
        s["_model"] = {
            "kind": s["fit"],
            "x_transform": x_transform,
            "y_transform": y_transform,
            "center_x": mx,
            "center_y": my,
            "slope": b,
            "xs": xs,
            "ys": ys,
        }
        pairs = list(zip(samples, _predict_model(s["_model"], samples)))
        sxx = math.fsum((x - mx) ** 2 for x in xs)
        critical = student_t_critical(len(xs) - 2) if len(xs) >= 3 else None
        for x, y in pairs:
            point = {"x": 10**x if x_transform == "log10" else x, "y": 10**y if y_transform == "log10" else y}
            if show_ci and s["fit"] == "linear" and critical is not None:
                delta = critical * rmse * math.sqrt(1 / len(xs) + (x - mx) ** 2 / sxx)
                point.update(
                    lo=10 ** (y - delta) if y_transform == "log10" else y - delta,
                    hi=10 ** (y + delta) if y_transform == "log10" else y + delta,
                )
            s["curve"].append(point)
        s["_stats"] = {"n": len(xs), "r2": r2, "p": pval, "slope": b, "rmse": rmse, "fit": s["fit"]}
    return out


class CategoryScale(SharedScale):
    """A shared categorical axis with stable order and measured labels."""

    def __init__(self, categories):
        self.categories = list(categories)
        super().__init__((-0.5, len(self.categories) - 0.5), ticks=list(range(len(self.categories))))

    def map(self, v, p0, p1):
        if isinstance(v, str):
            v = self.categories.index(v)
        return super().map(v, p0, p1)


def _tight_linear(low, high, include_zero=False):
    """Domain hugging the data (small pad) with nice ticks inside it."""
    span = high - low
    pad = span * 0.04 if span else max(abs(low) * 0.05, 0.5)
    a, b = low - pad, high + pad
    if include_zero:
        a = 0.0 if low >= 0 else a
        b = 0.0 if high <= 0 else b
    ticks = []
    for n in (6, 8, 10):
        ticks = [t for t in nice_axis(a, b, n)[0] if a - 1e-9 * (b - a) <= t <= b + 1e-9 * (b - a)]
        if len(ticks) >= 3:
            break
    return SharedScale((a, b), ticks)


def infer_scales(series, *, x_transform="linear", y_transform="linear", extra=None, tight=False):
    """Return SharedScale pair."""
    result = []
    for axis, transform in (("x", x_transform), ("y", y_transform)):
        values, strings = [], []
        for s in series:
            for p in s["points"] + s["curve"]:
                v = p[axis]
                if isinstance(v, str):
                    if v not in strings:
                        strings.append(v)
                    continue
                values.append(v)
                if axis + "_err" in p:
                    e = p[axis + "_err"]
                    values.extend((v - e[0], v + e[1]))
                if axis == "y" and "lo" in p:
                    values.extend((p["lo"], p["hi"]))
        if strings:
            if values or transform != "linear":
                raise ValueError("an axis cannot mix categories with numbers or use categorical log scales")
            result.append(CategoryScale(strings))
            continue
        if not values:
            raise ValueError("axis has no data")
        values.extend(
            v for v in (extra or {}).get(axis, []) if not isinstance(v, str) and (transform != "log10" or v > 0)
        )
        if transform not in ("linear", "log10"):
            raise ValueError("axis transform must be linear or log10")
        low, high = min(values), max(values)
        if transform == "log10":
            if low <= 0:
                raise ValueError(f"{axis}: log10 requires positive observations, errors and bands")
            a, b = math.log10(low), math.log10(high)
            pad = max(0.035, (b - a) * 0.055)
            a, b = a - pad, b + pad
            from ._chart_layout import log_axis_ticks

            ticks = log_axis_ticks(10**a, 10**b)
            result.append(SharedScale((10**a, 10**b), ticks, transform))
        elif tight:
            result.append(
                _tight_linear(low, high, axis == "y" and (0 <= low <= 0.25 * high or 0 >= high >= 0.25 * low))
            )
        else:
            pad = (high - low) * 0.07 if low != high else max(abs(low) * 0.05, 0.5)
            ticks, a, b = nice_axis(low - pad, high + pad, 5)
            if low >= 0 and a < 0:
                a = 0.0
                ticks = [v for v in ticks if v >= 0]
            result.append(SharedScale((a, b), ticks))
    if all(isinstance(s, CategoryScale) for s in result):
        raise ValueError("at most one axis may be categorical")
    return tuple(result)


_FRONTIER = {"max": (False, True), "min": (False, False), "max_x_min": (True, True), "min_x_max": (True, False)}


def add_frontier(series, frontier):
    """Append the observed Pareto front as a dashed step-free line through the non-dominated points."""
    if frontier in (None, False):
        return series
    if frontier is True:
        frontier = "max"
    if frontier not in _FRONTIER:
        raise ValueError("frontier must be True, 'max', 'min', 'max_x_min' or 'min_x_max'")
    x_high, y_high = _FRONTIER[frontier]
    pts = [
        (p["x"], p["y"])
        for s in series
        for p in s["points"]
        if not isinstance(p["x"], str) and not isinstance(p["y"], str)
    ]
    if len(pts) < 2:
        raise ValueError("frontier needs at least two numeric points")
    better = lambda a, b, high: a > b if high else a < b
    front = [
        p
        for p in pts
        if not any(
            q != p
            and not better(p[0], q[0], x_high)
            and not better(p[1], q[1], y_high)
            and (better(q[0], p[0], x_high) or better(q[1], p[1], y_high))
            for q in pts
        )
    ]
    front = sorted(set(front))
    if len(front) < 2:
        return series
    name = tr("Pareto front")
    return list(series) + [
        {
            "name": name,
            "points": [],
            "curve": [{"x": x, "y": y} for x, y in front],
            "marker": "none",
            "fit": None,
            "_frontier": True,
            "color": None,
        }
    ]


def series_context(series, palette):
    pal = _resolve_palette(palette)
    context = SeriesContext([s["name"] for s in series if not s.get("_frontier")], pal=pal)
    context.ids += [s["name"] for s in series if s.get("_frontier")]
    context.order = list(context.ids)
    context.labels.update({s["name"]: s["name"] for s in series})
    for s in series:
        if s.get("color"):
            context.colors[s["name"]] = s["color"]
        elif s.get("_frontier"):
            context.colors[s["name"]] = pal["ink"]
    return context


def _axis_format(scale):
    if isinstance(scale, CategoryScale):
        return lambda v: scale.categories[int(v)], ""
    a, b = scale.domain
    span = b - a
    offset = round((a + b) / 2, max(0, -math.floor(math.log10(span)))) if span and abs(a) / span > 1e4 else 0.0
    factor = (
        10 ** math.floor(math.log10(span))
        if span and (span < 0.01 or span > 1e5) and scale.transform == "linear"
        else 1.0
    )
    ticks = scale.ticks or []
    step = min((ticks[i] - ticks[i - 1] for i in range(1, len(ticks)) if ticks[i] > ticks[i - 1]), default=span)
    decimals = max(0, 1 - math.floor(math.log10(step / factor))) if step else 3
    if ticks and scale.transform != "log10":
        # One decimal count for the whole tick set: "0.8 / 1.0 / 1.2", never
        # "0.80 / 1 / 1.20" (mixed precision reads as different measurements).
        decimals = min(
            decimals, _tick_decimals([(t - offset) / factor for t in ticks], step / factor if step else None)
        )

    def label(v):
        n = (v - offset) / factor
        if abs(n) < 1e-9:
            n = 0.0
        if scale.transform == "log10":
            return f"{n:.4g}"
        return f"{n:.{decimals}f}"

    annotation = tr("offset {value}", value=f"{offset:+}") if offset else ""
    if factor != 1:
        annotation += ("; " if annotation else "") + f"× {factor:g}"
    return label, annotation


def _text(text, x, y, font, color, *, fs=12, anchor="start", weight=400, role=""):
    return f'<text x="{x:.3f}" y="{y:.3f}" font-family={quoteattr(font)} font-size="{fs:g}" text-anchor="{anchor}" font-weight="{weight}" fill={quoteattr(color)} data-role="{role}">{_xesc(str(text))}</text>'


def _path(points):
    return " ".join(("M" if i == 0 else "L") + f"{x:.4f},{y:.4f}" for i, (x, y) in enumerate(points))


def _marker(
    x, y, radius, shape, color, *, opacity=0.78, role="observation", attrs="", clip_box=None, stroke_color=None
):
    base = f'fill={quoteattr(color)} fill-opacity="{opacity:g}" stroke={quoteattr(stroke_color or color)} stroke-width=".7" data-role="{role}" {attrs}'
    if shape == "none" or radius <= 0:
        return ""
    if clip_box is not None and (
        x - radius * 1.4 < clip_box.x0
        or x + radius * 1.4 > clip_box.x1
        or y - radius * 1.4 < clip_box.y0
        or y + radius * 1.4 > clip_box.y1
    ):
        if shape == "circle":
            vertices = [
                (x + radius * math.cos(i * math.tau / 64), y + radius * math.sin(i * math.tau / 64)) for i in range(64)
            ]
        elif shape == "square":
            vertices = [
                (x - radius, y - radius),
                (x + radius, y - radius),
                (x + radius, y + radius),
                (x - radius, y + radius),
            ]
        elif shape == "diamond":
            vertices = [(x, y - radius * 1.3), (x + radius * 1.3, y), (x, y + radius * 1.3), (x - radius * 1.3, y)]
        else:
            vertices = [
                (x, y - radius * 1.4),
                (x + radius * 1.2, y + radius * 0.7),
                (x - radius * 1.2, y + radius * 0.7),
            ]
        vertices = _clip_polygon(vertices, clip_box)
        return f'<path d="{_path(vertices)} Z" {base}/>' if vertices else ""
    if shape == "circle":
        return f'<circle cx="{x:.4f}" cy="{y:.4f}" r="{radius:.4f}" {base}/>'
    if shape == "square":
        return f'<rect x="{x - radius:.4f}" y="{y - radius:.4f}" width="{2 * radius:.4f}" height="{2 * radius:.4f}" {base}/>'
    if shape == "diamond":
        vertices = [(x, y - radius * 1.3), (x + radius * 1.3, y), (x, y + radius * 1.3), (x - radius * 1.3, y)]
    else:
        vertices = [(x, y - radius * 1.4), (x + radius * 1.2, y + radius * 0.7), (x - radius * 1.2, y + radius * 0.7)]
    return f'<path d="{_path(vertices)} Z" {base}/>'


def _inside(bbox, x, y):
    return bbox.x0 - 1e-8 <= x <= bbox.x1 + 1e-8 and bbox.y0 - 1e-8 <= y <= bbox.y1 + 1e-8


def _clip_segment(a, b, box):
    """Liang-Barsky clipping, without nested SVG, defs, or clipping IDs."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    u0, u1 = 0.0, 1.0
    for p, q in ((-dx, a[0] - box.x0), (dx, box.x1 - a[0]), (-dy, a[1] - box.y0), (dy, box.y1 - a[1])):
        if p == 0:
            if q < 0:
                return None
        else:
            t = q / p
            if p < 0:
                u0 = max(u0, t)
            else:
                u1 = min(u1, t)
            if u0 > u1:
                return None
    return ((a[0] + u0 * dx, a[1] + u0 * dy), (a[0] + u1 * dx, a[1] + u1 * dy))


def _clip_polygon(vertices, box):
    points = vertices
    for axis, edge, sign in ((0, box.x0, 1), (0, box.x1, -1), (1, box.y0, 1), (1, box.y1, -1)):
        result = []
        if not points:
            break
        for a, b in zip(points, points[1:] + points[:1]):
            ia, ib = (a[axis] - edge) * sign >= 0, (b[axis] - edge) * sign >= 0
            if ia:
                result.append(a)
            if ia != ib:
                t = (edge - a[axis]) / (b[axis] - a[axis])
                result.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
        points = result
    return points


def _linear_sample(a, b, fraction):
    """The external-curve contract: piecewise linear in original data coordinates."""
    result = {}
    for key in ("x", "y", "lo", "hi"):
        if key not in a or key not in b:
            continue
        delta = b[key] - a[key]
        result[key] = a[key] + fraction * delta if math.isfinite(delta) else (1 - fraction) * a[key] + fraction * b[key]
    return result


def interpolate_curve(curve, x):
    """Evaluate an external numerical curve with no extrapolation."""
    if not curve:
        raise ValueError("residuals require a prediction curve")
    if x < curve[0]["x"] or x > curve[-1]["x"]:
        raise ValueError("prediction curve must cover every residual observation")
    for index in range(1, len(curve)):
        a, b = curve[index - 1], curve[index]
        if a["x"] <= x <= b["x"]:
            return a["y"] if a["x"] == b["x"] else _linear_sample(a, b, (x - a["x"]) / (b["x"] - a["x"]))["y"]
    return curve[-1]["y"]


def _render_curve_samples(series, X, Y, *, transformed=False, x_log=False, y_log=False):
    """Approximate the same raw-coordinate function after nonlinear axis mapping."""
    curve = series["curve"]
    if not curve or any(isinstance(p[k], str) for p in curve for k in ("x", "y")):
        return curve
    model = series.get("_model")
    ci_factor = (
        student_t_critical(len(model["xs"]) - 2) * series["_stats"]["rmse"]
        if model and model["kind"] == "linear" and any("lo" in p for p in curve)
        else None
    )
    sxx = math.fsum((x - model["center_x"]) ** 2 for x in model["xs"]) if model else 0

    def evaluate(a, b, t):
        p = _linear_sample(a, b, t)
        if model:
            x = math.log10(p["x"]) if model["x_transform"] == "log10" else p["x"]
            y = _predict_model(model, [x])[0]
            p["y"] = 10**y if model["y_transform"] == "log10" else y
            if "lo" in p and ci_factor is not None:
                delta = ci_factor * math.sqrt(1 / len(model["xs"]) + (x - model["center_x"]) ** 2 / sxx)
                p["lo"] = 10 ** (y - delta) if model["y_transform"] == "log10" else y - delta
                p["hi"] = 10 ** (y + delta) if model["y_transform"] == "log10" else y + delta
        return p

    def refine(a, b):
        # Raw-coordinate bisection wastes its depth budget at the large end of a log domain. Probe log-spaced X and
        # external Y/CI values as well, then split at the largest screen error.
        stack, refined = [(a, b)], []
        while stack:
            start, end = stack.pop()
            fractions = {0.25, 0.5, 0.75}
            keys = (["x"] if x_log else []) + (
                [k for k in ("y", "lo", "hi") if k in start and k in end] if y_log and not model else []
            )
            for key in keys:
                low, high = start[key], end[key]
                if low == high:
                    continue
                for t in (0.25, 0.5, 0.75):
                    value = math.exp((1 - t) * math.log(low) + t * math.log(high))
                    fraction = (value - low) / (high - low)
                    if 0 < fraction < 1:
                        fractions.add(fraction)
            xa, xb = X(start["x"]), X(end["x"])
            worst_error, split = 0.0, None
            for t in sorted(fractions):
                middle = evaluate(start, end, t)
                if not start["x"] < middle["x"] < end["x"]:
                    continue
                fraction = (X(middle["x"]) - xa) / (xb - xa) if xb != xa else 0.5
                error = max(
                    abs(Y(middle[k]) - (Y(start[k]) + fraction * (Y(end[k]) - Y(start[k]))))
                    for k in ("y", "lo", "hi")
                    if k in middle
                )
                if error > worst_error:
                    worst_error, split = error, middle
            if worst_error > 0.08:
                if len(refined) + len(stack) > 100000:
                    raise ValueError("curve requires too many segments for the requested axis range")
                stack.extend(((split, end), (start, split)))
            else:
                refined.append(start)
        return refined + [b]

    result = []
    observations = [p["x"] for p in series["points"]]
    for index in range(1, len(curve)):
        a, b = curve[index - 1], curve[index]
        inside = sorted({x for x in observations if a["x"] < x < b["x"]})
        knots = [a] + [evaluate(a, b, (x - a["x"]) / (b["x"] - a["x"])) for x in inside] + [b]
        for j in range(1, len(knots)):
            segment = refine(knots[j - 1], knots[j]) if transformed else [knots[j - 1], knots[j]]
            result.extend(segment[:-1])
    if curve:
        result.append(curve[-1])
    return result


def _reference_value(value, scale):
    if isinstance(scale, CategoryScale) and isinstance(value, str):
        if value not in scale.categories:
            raise ValueError("reference category is not present on its axis")
        return value
    return finite(value, "reference value")


def _render_x_axis(scale, bbox, font, pal, show_labels=True, font_sizes=None):
    """One measured X-axis implementation for main plots and count tracks."""
    fs = (font_sizes or chart_font_sizes(bbox.x1 - bbox.x0, bbox.y1 - bbox.y0, 60))["xtick"]
    line_h = fs * 1.35
    fmt, _ = _axis_format(scale)
    ink = pal.get("ink_fg", pal["ink"])
    ticks = scale.ticks or []
    if not isinstance(scale, CategoryScale):
        maxw = max((_estimate_label_width_px(fmt(v), fs, font_family=font) for v in ticks), default=0)
        stride = max(1, math.ceil((maxw + 16) * max(0, len(ticks) - 1) / (bbox.x1 - bbox.x0)))
        ticks = ticks[::stride]
    parts = [
        f'<path d="M{bbox.x0:.3f},{bbox.y1:.3f} H{bbox.x1:.3f}" stroke={quoteattr(pal["ink4"])} stroke-width="1" fill="none" data-role="x-axis"/>'
    ]
    for v in ticks:
        x = scale.map(v, bbox.x0, bbox.x1)
        parts.append(f'<path d="M{x:.3f},{bbox.y1:.3f} v5" stroke={quoteattr(pal["ink4"])}/>')
        if show_labels:
            width = (bbox.x1 - bbox.x0) / len(scale.categories) * 0.92 if isinstance(scale, CategoryScale) else None
            lines = wrap_lines(fmt(v), width, fs, font) if width else [fmt(v)]
            for j, line in enumerate(lines):
                parts.append(
                    _text(
                        line, x, bbox.y1 + 5 + fs * 1.44 + j * line_h, font, ink, fs=fs, anchor="middle", role="x-tick"
                    )
                )
    return "".join(parts)


def render_xy_plot(
    series,
    bbox,
    *,
    x_scale=None,
    y_scale=None,
    context=None,
    palette=None,
    font_family=None,
    axes=True,
    show_x_labels=True,
    show_y_labels=True,
    reference_lines=None,
    phases=None,
    label_bbox=None,
    size_max=None,
    radius_max=18.0,
    summary=False,
    glyph_renderer=None,
    font_sizes=None,
    reference_labels=False,
    trend=False,
    annotations=None,
    reference_bands=None,
):
    """Render normalized/fitted series into a BBox as flat SVG fragments."""
    bbox = BBox(*bbox)
    if bbox.x1 <= bbox.x0 or bbox.y1 <= bbox.y0:
        raise ValueError("plot bbox must have positive width and height")
    pal = _resolve_palette(palette)
    font, _ = _resolve_font(font_family)
    ink = pal.get("ink_fg", pal["ink"])
    font_sizes = font_sizes or chart_font_sizes(bbox.x1 - bbox.x0, bbox.y1 - bbox.y0, xy_density(series))
    tick_fs = font_sizes["ytick"]
    tick_h = tick_fs * 1.35
    x_auto, y_auto = infer_scales(series)
    x_scale, y_scale = x_scale or x_auto, y_scale or y_auto
    context = context or series_context(series, pal)
    X = lambda v: x_scale.map(v, bbox.x0, bbox.x1)
    Y = lambda v: y_scale.map(v, bbox.y1, bbox.y0)
    global_order = list(dict.fromkeys(context.order + context.ids))
    if any(s["name"] not in global_order for s in series):
        raise ValueError("shared SeriesContext must include every rendered series")

    # Connected series on a category axis share each category's position: dodging them left/right would
    # misplace every vertex of the line (two curves over "293 K / 77 K / 4.2 K" must meet the same ticks).
    connected = any(len(s.get("curve") or []) > 1 for s in series)

    def maps(s):
        index = global_order.index(s["name"])

        def offset(scale, span):
            return (
                (index - (len(global_order) - 1) / 2) * span / len(scale.categories) * 0.72 / len(global_order)
                if isinstance(scale, CategoryScale) and not connected
                else 0.0
            )

        dx, dy = offset(x_scale, bbox.x1 - bbox.x0), offset(y_scale, bbox.y1 - bbox.y0)
        return (lambda v: X(v) + dx), (lambda v: Y(v) + dy)

    # Multiple disjoint curve runs may share a color/legend identity. Cache by
    # the actual series object so a later observation-only run cannot erase it.
    sampled = {
        id(s): _render_curve_samples(
            s,
            *maps(s),
            transformed=x_scale.transform == "log10" or y_scale.transform == "log10",
            x_log=x_scale.transform == "log10",
            y_log=y_scale.transform == "log10",
        )
        for s in series
    }
    parts = []
    for phase_index, phase in enumerate(phases or []):
        x0, x1 = X(phase["start"]), X(phase["end"])
        if x1 <= x0:
            raise ValueError("phase end must exceed start")
        x0, x1 = max(bbox.x0, x0), min(bbox.x1, x1)
        if x0 < x1:
            parts.append(
                f'<rect x="{x0:.3f}" y="{bbox.y0:.3f}" width="{x1 - x0:.3f}" height="{bbox.y1 - bbox.y0:.3f}" fill={quoteattr(phase.get("color", pal["ink"]))} fill-opacity="{0.05 if phase_index % 2 == 0 else 0.022}" data-role="phase"/>'
            )
    for band in reference_bands or []:  # shaded envelope of a reference population (conventional alloys …)
        polygon = _clip_polygon([(X(x), Y(y)) for x, y in band["points"]], bbox)
        if polygon:
            parts.append(
                f'<path d="{_path(polygon)} Z" fill={quoteattr(band.get("color") or pal["ink"])} fill-opacity=".09" '
                f'stroke={quoteattr(band.get("color") or pal["ink4"])} stroke-width=".8" stroke-dasharray="3 3" data-role="reference-band"/>'
            )
            if band.get("label"):
                cx = sum(p[0] for p in polygon) / len(polygon)
                cy = sum(p[1] for p in polygon) / len(polygon)
                parts.append(
                    _text(
                        band["label"],
                        cx,
                        cy + tick_fs * 0.35,
                        font,
                        pal["ink6"],
                        fs=tick_fs * 0.9,
                        anchor="middle",
                        role="reference-band-label",
                    )
                )
    for boundary in sorted({phase["start"] for phase in phases or []} | {phase["end"] for phase in phases or []}):
        x = X(boundary)
        if bbox.x0 < x < bbox.x1:
            parts.append(
                f'<path d="M{x:.3f},{bbox.y0:.3f} V{bbox.y1:.3f}" stroke={quoteattr(pal["ink2"])} stroke-width=".6" stroke-dasharray="2 3" data-role="phase-boundary"/>'
            )
    if axes:
        for v in y_scale.ticks or []:
            y = Y(v)
            parts.append(
                f'<path d="M{bbox.x0:.3f},{y:.3f} H{bbox.x1:.3f}" stroke={quoteattr(pal["grid"])} stroke-opacity=".6" stroke-width=".6" fill="none" data-role="grid"/>'
            )
    ref_fs = max(10.0, font_sizes["foot"])
    ref_ink = readable_annotation_color(pal["ink6"], pal)
    ref_boxes, ref_texts = [], []
    for ref in reference_lines or []:
        r = {"value": ref[0], "label": ref[1], "axis": ref[2]} if not isinstance(ref, dict) else ref
        if r.get("axis") in ("x", "v", "vertical"):
            x = X(_reference_value(r["value"], x_scale))
            a, b = (x, bbox.y0), (x, bbox.y1)
        elif r.get("axis", "y") in ("y", "h", "horizontal"):
            y = Y(_reference_value(r["value"], y_scale))
            a, b = (bbox.x0, y), (bbox.x1, y)
        elif r.get("axis") == "diagonal":
            a, b = (bbox.x0, Y(x_scale.domain[0])), (bbox.x1, Y(x_scale.domain[1]))
        else:
            raise ValueError("reference axis must be x, y or diagonal")
        seg = _clip_segment(a, b, bbox)
        if seg:
            parts.append(
                f'<path d="{_path(seg)}" fill="none" stroke={quoteattr(r.get("color", pal["ink4"]))} stroke-width="1.1" stroke-dasharray="5 4" data-role="reference"/>'
            )
            if reference_labels and r.get("label") and r.get("axis", "y") != "diagonal":
                text = str(r["label"])
                w = _estimate_label_width_px(text, ref_fs, font_family=font)
                if a[1] == b[1]:
                    y = seg[0][1]
                    base = y - 4 if y - 4 - ref_fs >= bbox.y0 else y + ref_fs + 2
                    x_end = bbox.x1 - 4
                    ref_texts.append(
                        _text(text, x_end, base, font, ref_ink, fs=ref_fs, anchor="end", role="reference-label")
                    )
                    ref_boxes.append((x_end - w, base - ref_fs, x_end, base + 3))
                else:
                    x = seg[0][0]
                    base = bbox.y0 + ref_fs + 2
                    left = x + 4 if x + 4 + w <= bbox.x1 else x - 4 - w
                    ref_texts.append(_text(text, left, base, font, ref_ink, fs=ref_fs, role="reference-label"))
                    ref_boxes.append((left, base - ref_fs, left + w, base + 3))
    # Bands behind all observations. Naive overpainting of individual series
    # would put later bands on earlier markers and change apparent density.
    for s in series:
        color = context.color_of(s["name"])
        SX, SY = maps(s)
        runs = []
        current = []
        for p in sampled[id(s)]:
            if "lo" in p:
                current.append(p)
            elif current:
                runs.append(current)
                current = []
        if current:
            runs.append(current)
        for curve in runs:
            if len(curve) == 1:
                p = curve[0]
                segment = _clip_segment((SX(p["x"]), SY(p["lo"])), (SX(p["x"]), SY(p["hi"])), bbox)
                if segment:
                    parts.append(
                        f'<path d="{_path(segment)}" fill="none" stroke={quoteattr(color)} stroke-opacity=".5" data-role="confidence-interval" data-series={quoteattr(s["name"])}/>'
                    )
                continue
            polygon = [(SX(p["x"]), SY(p["lo"])) for p in curve] + [(SX(p["x"]), SY(p["hi"])) for p in reversed(curve)]
            polygon = _clip_polygon(polygon, bbox)
            if polygon:
                parts.append(
                    f'<path d="{_path(polygon)} Z" fill={quoteattr(color)} fill-opacity=".14" stroke="none" data-role="confidence-band" data-series={quoteattr(s["name"])}/>'
                )
    for s in sorted(series, key=lambda s: s.get("_emphasis", False)):
        color = context.color_of(s["name"])
        SX, SY = maps(s)
        curve = sampled[id(s)]
        line_width = 3.2 if s.get("_emphasis") else 1.4 if s.get("_frontier") else 2.0
        dash = ' stroke-dasharray="6 4"' if s.get("_frontier") else ""

        dashed_from = s.get("dashed_from")
        for index in range(1, len(curve)):
            a, b = curve[index - 1], curve[index]
            ends = [(a["x"], a["y"]), (b["x"], b["y"])]
            pieces = [(ends, dash)]
            if dashed_from is not None and isinstance(a["x"], float) and isinstance(b["x"], float):
                lo_x, hi_x = sorted((a["x"], b["x"]))
                if lo_x >= dashed_from:
                    pieces = [(ends, ' stroke-dasharray="6 4"')]
                elif lo_x < dashed_from < hi_x:  # split the segment at the projection start
                    t = (dashed_from - a["x"]) / (b["x"] - a["x"])
                    mid = (dashed_from, a["y"] + t * (b["y"] - a["y"]))
                    first, second = (
                        ([ends[0], mid], [mid, ends[1]]) if a["x"] < b["x"] else ([mid, ends[1]], [ends[0], mid])
                    )
                    pieces = [(first, dash), (second, ' stroke-dasharray="6 4"')]
            for (p0, p1), piece_dash in pieces:
                seg = _clip_segment((SX(p0[0]), SY(p0[1])), (SX(p1[0]), SY(p1[1])), bbox)
                if seg:
                    role = (
                        "pareto-front"
                        if s.get("_frontier")
                        else "projection"
                        if "6 4" in piece_dash and not dash
                        else "curve"
                    )
                    parts.append(
                        f'<path d="{_path(seg)}" stroke={quoteattr(color)} stroke-width="{line_width:g}" stroke-linecap="round" fill="none"{piece_dash} data-role="{role}" data-series={quoteattr(s["name"])}/>'
                    )
    count = sum(len(s["points"]) for s in series)
    radius = 3.6 if count < 120 else 2.5 if count < 600 else 1.5
    size_values = [p["size"] for s in series for p in s["points"] if "size" in p]
    maximum = finite(size_max, "size_max", minimum=0) if size_max is not None else max(size_values, default=1.0)
    if maximum < max(size_values, default=0):
        raise ValueError("size_max must include every bubble size")
    labels, occupied = [], list(ref_boxes)
    if trend:
        for s in series:
            SX, SY = maps(s)
            curve = sampled[id(s)]
            for a, b in zip(curve, curve[1:]):
                if isinstance(a["x"], str) or isinstance(a["y"], str):
                    break
                p0, p1 = (SX(a["x"]), SY(a["y"])), (SX(b["x"]), SY(b["y"]))
                pieces = max(1, math.ceil(math.dist(p0, p1) / 10))
                for k in range(pieces):
                    q0 = (p0[0] + (p1[0] - p0[0]) * k / pieces, p0[1] + (p1[1] - p0[1]) * k / pieces)
                    q1 = (p0[0] + (p1[0] - p0[0]) * (k + 1) / pieces, p0[1] + (p1[1] - p0[1]) * (k + 1) / pieces)
                    occupied.append(segment_obstacle(("curve", s["name"]), q0, q1, width=2))
    data_start = len(parts)
    summaries = defaultdict(list)
    for s in series:
        si = global_order.index(s["name"])
        color = context.color_of(s["name"])
        if len(series) == 1 and any(p.get("_highlight") for p in s["points"]):
            color = pal["ink6"]
        points = s["points"]
        last_index = (
            max(range(len(points)), key=lambda i: points[i]["x"])
            if trend and s["curve"] and points and all(not isinstance(q["x"], str) for q in points)
            else None
        )
        for pi, p in enumerate(points):
            owner = (s["name"], pi)
            x, y = X(p["x"]), Y(p["y"])
            # Deterministic pixel jitter on the category axis only; numerical
            # measurements remain at their exact coordinate.
            categorical = isinstance(x_scale, CategoryScale) or isinstance(y_scale, CategoryScale)
            if categorical:
                horizontal = isinstance(y_scale, CategoryScale)
                scale = y_scale if horizontal else x_scale
                band = (bbox.y1 - bbox.y0 if horizontal else bbox.x1 - bbox.x0) / len(scale.categories)
                group_width = band * 0.72 / max(1, len(global_order))
                offset = 0.0 if connected else (si - (len(global_order) - 1) / 2) * group_width
                duplicates = [q for q in points if q["y" if horizontal else "x"] == p["y" if horizontal else "x"]]
                local_i = sum(1 for q in points[:pi] if q["y" if horizontal else "x"] == p["y" if horizontal else "x"])
                jitter = (((local_i * 0.61803398875 + 0.5) % 1) - 0.5) * group_width * 0.7 if len(duplicates) > 1 else 0
                if horizontal:
                    y += offset + jitter
                else:
                    x += offset + jitter
                summaries[(s["name"], p["y" if horizontal else "x"])].append((p, x, y, offset))
            if not _inside(bbox, x, y):
                continue
            r = (
                radius_max * math.sqrt(p["size"] / maximum)
                if "size" in p and maximum
                else 0.0
                if "size" in p
                else radius * 1.45
                if pi == last_index
                else radius
            )
            c = p.get("color") or (pal["accent"] if p.get("_highlight") else color)
            attrs = (
                f"data-series={quoteattr(s['name'])} data-x={quoteattr(str(p['x']))} data-y={quoteattr(str(p['y']))}"
            )
            if "size" in p:
                attrs += f' data-size="{p["size"]:g}"'
            for axis, F, value, center in (("x", X, p["x"], y), ("y", Y, p["y"], x)):
                if axis + "_err" not in p:
                    continue
                if isinstance(value, str):
                    raise TypeError("error bars require a numerical axis")
                lo, hi = p[axis + "_err"]
                ends = (F(value - lo), F(value + hi))
                a, b = ((ends[0], center), (ends[1], center)) if axis == "x" else ((center, ends[0]), (center, ends[1]))
                seg = _clip_segment(a, b, bbox)
                if seg:
                    occupied.append(segment_obstacle(owner, *seg))
                    parts.append(
                        f'<path d="{_path(seg)}" stroke={quoteattr(c)} stroke-width="1.2" fill="none" data-role="{axis}-error" {attrs}/>'
                    )
                    for pos in ends:
                        if axis == "x" and bbox.x0 <= pos <= bbox.x1:
                            d = f"M{pos:.4f},{center - 3:.4f} v6"
                        elif axis == "y" and bbox.y0 <= pos <= bbox.y1:
                            d = f"M{center - 3:.4f},{pos:.4f} h6"
                        else:
                            continue
                        parts.append(f'<path d="{d}" stroke={quoteattr(c)} stroke-width="1.2"/>')
                        cap = (
                            ((pos, center - 3), (pos, center + 3))
                            if axis == "x"
                            else ((center - 3, pos), (center + 3, pos))
                        )
                        occupied.append(segment_obstacle(owner, *cap))
            shape = "circle" if glyph_renderer is not None else p.get("marker", s.get("marker", "circle"))
            if glyph_renderer is None:
                parts.append(
                    _marker(
                        x,
                        y,
                        r,
                        shape,
                        c,
                        opacity=1 if pi == last_index else 0.48 if count > 1000 else 0.76,
                        attrs=attrs,
                        clip_box=bbox,
                        stroke_color=pal["ink6"] if "size" in p else c,
                    )
                )
            elif r > 0:
                glyph = glyph_renderer(p, x, y, r, c)
                if not isinstance(glyph, str):
                    raise TypeError("glyph_renderer must return an SVG fragment string")
                parts.append(f'<g {attrs} data-role="observation" data-radius="{r:.4f}">{glyph}</g>')
            obstacle = marker_obstacle(owner, x, y, r, shape)
            if obstacle is not None:
                occupied.append(obstacle)
            if p.get("label"):
                labels.append((x, y, str(p["label"]), c, owner))
    if summary:
        if not summaries:
            for s in series:
                if not s["points"]:
                    continue
                means = {}
                errors = {}
                for axis in ("x", "y"):
                    values = [p[axis] for p in s["points"]]
                    mean = math.fsum(values) / len(values)
                    means[axis] = mean
                    errors[axis] = (
                        math.sqrt(
                            math.fsum((value - mean) ** 2 for value in values) / (len(values) * (len(values) - 1))
                        )
                        if len(values) > 1
                        else 0.0
                    )
                x, y = X(means["x"]), Y(means["y"])
                occupied.append(marker_obstacle(("summary", s["name"]), x, y, 5, "diamond"))
                for axis, F, center in (("x", X, y), ("y", Y, x)):
                    ends = [F(means[axis] - errors[axis]), F(means[axis] + errors[axis])]
                    segment = (
                        ((ends[0], center), (ends[1], center))
                        if axis == "x"
                        else ((center, ends[0]), (center, ends[1]))
                    )
                    segment = _clip_segment(*segment, bbox)
                    if segment:
                        occupied.append(segment_obstacle(("summary", s["name"]), *segment, width=2))
                        parts.append(
                            f'<path d="{_path(segment)}" stroke={quoteattr(ink)} stroke-width="2" data-role="summary-{axis}-sem" data-series={quoteattr(s["name"])}/>'
                        )
                parts.append(
                    _marker(
                        x,
                        y,
                        5,
                        "diamond",
                        ink,
                        opacity=1,
                        role="summary-mean",
                        attrs=f'data-series={quoteattr(s["name"])} data-mean-x="{means["x"]:.17g}" data-mean-y="{means["y"]:.17g}"',
                        clip_box=bbox,
                    )
                )
        horizontal = isinstance(y_scale, CategoryScale)
        for (name, category), items in summaries.items():
            vals = [it[0]["x" if horizontal else "y"] for it in items]
            mean = math.fsum(vals) / len(vals)
            sem = (
                math.sqrt(math.fsum((v - mean) ** 2 for v in vals) / ((len(vals) - 1) * len(vals)))
                if len(vals) > 1
                else 0
            )
            category_pos = (Y(category) if horizontal else X(category)) + items[0][3]
            a, b = (
                ((X(mean - sem), category_pos), (X(mean + sem), category_pos))
                if horizontal
                else ((category_pos, Y(mean - sem)), (category_pos, Y(mean + sem)))
            )
            parts.append(
                f'<path d="{_path((a, b))}" stroke={quoteattr(ink)} stroke-width="2.2" data-role="summary-sem"/>'
            )
            center = (X(mean), category_pos) if horizontal else (category_pos, Y(mean))
            occupied.append(segment_obstacle(("summary", name, category), a, b, width=2.2))
            occupied.append(marker_obstacle(("summary", name, category), *center, 5, "diamond"))
            parts.append(
                _marker(*center, 5, "diamond", ink, opacity=1, role="summary-mean", attrs=f'data-mean="{mean:.17g}"')
            )
    if labels:
        try:
            leaders, label_text = _render_labels(
                labels, label_bbox or bbox, font, ink, occupied, rail=label_bbox is not None, fs=font_sizes["label"]
            )
        except ValueError:
            if not trend:
                raise
            occupied[:] = [
                o for o in occupied if not (isinstance(getattr(o, "owner", None), tuple) and o.owner[0] == "curve")
            ]
            leaders, label_text = _render_labels(
                labels, label_bbox or bbox, font, ink, occupied, rail=label_bbox is not None, fs=font_sizes["label"]
            )
        parts.insert(data_start, leaders)
        parts.append(label_text)
    parts.extend(ref_texts)
    if annotations:
        parts.append(_place_annotations(annotations, X, Y, bbox, occupied, font, ink, max(10.0, font_sizes["foot"])))
    if axes:
        parts.append(
            f'<path d="M{bbox.x0:.3f},{bbox.y0:.3f} V{bbox.y1:.3f}" stroke={quoteattr(pal["ink4"])} stroke-width="1" fill="none" data-role="y-axis"/>'
        )
        parts.append(_render_x_axis(x_scale, bbox, font, pal, show_x_labels, font_sizes))
        fmt, _ = _axis_format(y_scale)
        y_ticks = y_scale.ticks or []
        if not isinstance(y_scale, CategoryScale):
            stride = max(1, math.ceil((tick_h + 6) * max(0, len(y_ticks) - 1) / (bbox.y1 - bbox.y0)))
            y_ticks = y_ticks[::stride]
        for v in y_ticks:
            pos = Y(v)
            parts.append(f'<path d="M{bbox.x0 - 5:.3f},{pos:.3f} h5" stroke={quoteattr(pal["ink4"])}/>')
            if show_y_labels:
                lines = (
                    wrap_lines(fmt(v), max(30, bbox.x0 - 20), tick_fs, font)
                    if isinstance(y_scale, CategoryScale)
                    else [fmt(v)]
                )
                if (
                    isinstance(y_scale, CategoryScale)
                    and len(lines) * tick_h > (bbox.y1 - bbox.y0) / len(y_scale.categories) - 3
                ):
                    raise ValueError("Y category labels need a taller canvas or wider left margin")
                for j, line in enumerate(lines):
                    parts.append(
                        _text(
                            line,
                            bbox.x0 - 10,
                            pos + tick_fs * 0.3 + (j - (len(lines) - 1) / 2) * tick_h,
                            font,
                            ink,
                            anchor="end",
                            fs=tick_fs,
                            role="y-tick",
                        )
                    )
    return "".join(parts)


def _render_labels(labels, bbox, font, ink, occupied, *, rail, fs=11.0):
    line_h = fs * 1.35
    items = []
    for label_record in sorted(labels, key=lambda item: (item[1], item[0])):
        x, y, label, color = label_record[:4]
        owner = label_record[4] if len(label_record) > 4 else None
        lines = wrap_lines(label, bbox.x1 - bbox.x0 - 12, fs, font)
        items.append((x, y, label, color, lines, len(lines) * line_h, owner))
    if rail:
        total = sum(it[5] + 5 for it in items)
        if total > bbox.y1 - bbox.y0 + 5:
            raise ValueError("too many point labels for this canvas; increase height or label fewer points")
        ys = []
        cursor = bbox.y0
        for it in items:
            top = max(cursor, min(it[1] - it[5] / 2, bbox.y1 - it[5]))
            ys.append(top)
            cursor = top + it[5] + 5
        overflow = max(0, cursor - 5 - bbox.y1)
        for i in range(len(ys) - 1, -1, -1):
            ys[i] -= overflow
            if i > 0:
                overflow = max(0, ys[i - 1] + items[i - 1][5] + 5 - ys[i])
        parts = []
        leaders = []
        for (x, y, label, color, lines, h, owner), top in zip(items, ys):
            route = route_leader((x, y), (bbox.x0, top + h / 2), occupied, bbox, source_owner=owner)
            leaders.append(
                f'<path d="{_path(route)}" stroke={quoteattr(color)} stroke-opacity=".72" stroke-width="1.2" fill="none" data-role="label-leader" data-source-x="{x:.4f}" data-source-y="{y:.4f}"/>'
            )
            for j, line in enumerate(lines):
                parts.append(
                    _text(line, bbox.x0 + 3, top + fs * 0.84 + j * line_h, font, ink, fs=fs, role="point-label")
                )
        return "".join(leaders), "".join(parts)
    # Joint bounded search: candidate anchors use each actual glyph envelope.
    # Text placement never changes observation coordinates or marker radii.
    shape_obstacles = list(occupied)
    shape_boxes = [tuple(obstacle_box(obstacle)) for obstacle in shape_obstacles]
    records = []
    for x, y, label, color, lines, h, owner in items:
        w = max(_estimate_label_width_px(line, fs, font_family=font) for line in lines)
        marker = next(
            (
                o
                for o in shape_obstacles
                if getattr(o, "owner", None) == owner and getattr(o, "kind", None) in ("circle", "polygon")
            ),
            None,
        )
        envelope = tuple(obstacle_box(marker)) if marker is not None else (x, y, x, y)
        candidates, seen = [], set()
        for gap in (6, 6 + fs * 0.6, 6 + fs * 1.2, 6 + fs * 2.4, 6 + fs * 4):
            ml, mt, mr, mb = envelope
            placements = [
                (x - w / 2, mt - gap - h, 0),
                (mr + gap, y - h / 2, 0.3),
                (ml - gap - w, y - h / 2, 0.4),
                (x - w / 2, mb + gap, 0.6),
                (mr + gap, mt - gap - h, 1),
                (ml - gap - w, mt - gap - h, 1.1),
                (mr + gap, mb + gap, 1.3),
                (ml - gap - w, mb + gap, 1.4),
            ]
            for left, top, preference in placements:
                if w > bbox.x1 - bbox.x0 or h > bbox.y1 - bbox.y0:
                    continue
                clipped_left = max(bbox.x0, min(left, bbox.x1 - w))
                clipped_top = max(bbox.y0, min(top, bbox.y1 - h))
                preference += math.hypot(clipped_left - left, clipped_top - top) / max(fs, 1)
                left, top = clipped_left, clipped_top
                box = (left, top, left + w, top + h)
                if box in seen:
                    continue
                seen.add(box)
                if any(
                    min(box[2], b[2]) - max(box[0], b[0]) > -2 and min(box[3], b[3]) - max(box[1], b[1]) > -2
                    for b in shape_boxes
                ):
                    continue
                candidates.append((preference + (gap - 6) / max(fs, 1), box))
        if not candidates:
            raise ValueError(f"point label {label!r} has no clear position; increase canvas size or separate panels")
        records.append(
            dict(
                x=x,
                y=y,
                label=label,
                color=color,
                lines=lines,
                h=h,
                w=w,
                owner=owner,
                marker=marker,
                candidates=candidates,
            )
        )

    def endpoint(record, box):
        x, y = record["x"], record["y"]
        left, top, right, bottom = box
        if x < left:
            return left - 3, max(top + fs * 0.55, min(bottom - fs * 0.55, y))
        if x > right:
            return right + 3, max(top + fs * 0.55, min(bottom - fs * 0.55, y))
        return x, top - 3 if y < top else bottom + 3

    def crossing(a, b, c, d):
        cross = lambda p, q, r: (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
        return cross(a, b, c) * cross(a, b, d) < -1e-8 and cross(c, d, a) * cross(c, d, b) < -1e-8

    states = [(0.0, [])]
    for index, record in enumerate(records):
        next_states = []
        for score, boxes in states:
            for cost, box in record["candidates"]:
                if any(
                    min(box[2], b[2]) - max(box[0], b[0]) > -3 and min(box[3], b[3]) - max(box[1], b[1]) > -3
                    for b in boxes
                ):
                    continue
                penalty = 0.0
                for previous, prior_box in zip(records[:index], boxes):
                    same_group = (
                        isinstance(record["owner"], tuple)
                        and isinstance(previous["owner"], tuple)
                        and record["owner"][0] == previous["owner"][0]
                    )
                    if same_group:
                        dy = record["y"] - previous["y"]
                        label_dy = (box[1] + box[3] - prior_box[1] - prior_box[3]) / 2
                        if abs(dy) > fs * 0.2 and dy * label_dy < 0:
                            penalty += 40
                        dx = record["x"] - previous["x"]
                        label_dx = (box[0] + box[2] - prior_box[0] - prior_box[2]) / 2
                        if abs(dx) > fs and dx * label_dx < 0:
                            penalty += 15
                    if crossing(
                        (record["x"], record["y"]),
                        endpoint(record, box),
                        (previous["x"], previous["y"]),
                        endpoint(previous, prior_box),
                    ):
                        penalty += 25
                next_states.append((score + cost + penalty, boxes + [box]))
        if not next_states:
            raise ValueError("point labels have no clear position together; increase canvas size or separate panels")
        states = sorted(next_states, key=lambda item: item[0])[:48]

    for _, boxes in states:
        route_obstacles = shape_obstacles + boxes
        leaders, parts = [], []
        try:
            for record, box in zip(records, boxes):
                x, y, owner, marker = record["x"], record["y"], record["owner"], record["marker"]
                left, top, right, bottom = box
                distance = math.hypot(max(left - x, 0, x - right), max(top - y, 0, y - bottom))
                radius = getattr(marker, "radius", 0) if marker is not None else 0
                neighbors = any(
                    getattr(o, "owner", None) != owner
                    and getattr(o, "kind", None) == "circle"
                    and math.dist((x, y), o.vertices[0]) < radius + o.radius + fs * 1.4
                    for o in shape_obstacles
                )
                if marker is None or distance > radius + 16 or neighbors:
                    route = route_leader((x, y), endpoint(record, box), route_obstacles, bbox, source_owner=owner)
                    # The visible leader starts at the glyph boundary, not through its fill.
                    if (
                        marker is not None
                        and getattr(marker, "kind", None) == "circle"
                        and len(route) > 1
                        and math.dist(route[0], (x, y)) < 0.01
                    ):
                        dx, dy = route[1][0] - x, route[1][1] - y
                        length = math.hypot(dx, dy)
                        offset = min(length, marker.radius + marker.padding + 1)
                        if length:
                            route[0] = (x + dx * offset / length, y + dy * offset / length)
                    leaders.append(
                        f'<path d="{_path(route)}" stroke={quoteattr(record["color"])} stroke-opacity=".72" stroke-width="1.2" fill="none" data-role="label-leader" data-source-x="{x:.4f}" data-source-y="{y:.4f}" data-label={quoteattr(record["label"])}/>'
                    )
                    for a, b in zip(route, route[1:]):
                        route_obstacles.append(segment_obstacle(("label-leader", owner), a, b, width=1.2))
                for j, line in enumerate(record["lines"]):
                    parts.append(_text(line, left, top + fs * 0.84 + j * line_h, font, ink, fs=fs, role="point-label"))
        except ValueError:
            continue
        occupied.extend(boxes)
        return "".join(leaders), "".join(parts)
    raise ValueError("point labels have no unobstructed attachment; increase canvas size or separate panels")


def _place_annotations(notes, X, Y, bbox, occupied, font, ink, fs):
    """Key-point labels with short straight leaders; first collision-free candidate wins."""
    boxes = [tuple(obstacle_box(o)) for o in occupied]
    parts = []
    for note in notes:
        if "x" not in note or "y" not in note or not str(note.get("text", "")).strip():
            raise ValueError("annotations need x, y and text")
        ax, ay = X(note["x"]), Y(note["y"])
        if not _inside(bbox, ax, ay):
            raise ValueError("annotation lies outside the plotted domain")
        text = str(note["text"])
        w, h = _estimate_label_width_px(text, fs, font_family=font), fs * 1.2
        best = None
        for dist in (16, 26, 38, 52, 70):
            for dx, dy, cost in (
                (0, -1, 0),
                (1, -1, 0.2),
                (-1, -1, 0.3),
                (1, 0, 0.4),
                (-1, 0, 0.5),
                (0, 1, 0.6),
                (1, 1, 0.7),
                (-1, 1, 0.8),
            ):
                cx, cy = ax + dx * dist * (1.2 if dy else 1), ay + dy * dist
                left = cx - w / 2 if dx == 0 else cx if dx > 0 else cx - w
                top = cy - h / 2 if dy == 0 else cy - h if dy < 0 else cy
                box = (left, top, left + w, top + h)
                if box[0] < bbox.x0 + 2 or box[2] > bbox.x1 - 2 or box[1] < bbox.y0 + 1 or box[3] > bbox.y1 - 1:
                    continue
                if any(
                    min(box[2], b[2]) - max(box[0], b[0]) > -2 and min(box[3], b[3]) - max(box[1], b[1]) > -2
                    for b in boxes
                ):
                    continue
                best = (box, dx, dy)
                break
            if best:
                break
        if best is None:
            raise ValueError(f"annotation {text!r} has no clear position; increase width or height")
        box, dx, dy = best
        end = (
            min(max(ax, box[0]), box[2]) if dx == 0 else box[0] - 2 if dx > 0 else box[2] + 2,
            box[3] + 1 if dy < 0 else box[1] - 1 if dy > 0 else (box[1] + box[3]) / 2,
        )
        length = math.dist((ax, ay), end) or 1
        start = (ax + (end[0] - ax) * 5 / length, ay + (end[1] - ay) * 5 / length)
        parts.append(
            f'<path d="{_path((start, end))}" stroke={quoteattr(ink)} stroke-opacity=".6" stroke-width=".8" fill="none" data-role="annotation-leader"/>'
        )
        parts.append(_text(text, box[0], box[1] + fs * 0.92, font, ink, fs=fs, role="annotation"))
        boxes.append(box)
    return "".join(parts)


def _legend(layout, series, context, top):
    """Wrapped legend rows sized before plotting; long entries get their own row."""
    fs = layout.font_sizes["legend"]
    line_h = fs * 1.35
    x = 28.0
    available = layout.width - 56
    row_h = 0.0
    if not any(s.get("_legend", True) for s in series):
        return top
    for s in series:
        if not s.get("_legend", True):
            continue
        label = context.label_of(s["name"])
        lines = wrap_lines(label, min(available - 26, 300), fs, layout.font)
        width = max(layout.measure(line, fs) for line in lines) + 34
        h = max(18, len(lines) * line_h)
        if x + width > layout.width - 28 and x > 28:
            top += row_h + 7
            x = 28
            row_h = 0
        if s["points"]:
            layout.parts.append(
                _marker(
                    x + 5,
                    top + 7,
                    3.6,
                    s.get("marker", "circle") if s.get("marker") != "none" else "circle",
                    context.color_of(s["name"]),
                    opacity=1,
                    role="legend-symbol",
                )
            )
        else:
            dash = ' stroke-dasharray="4 2"' if s.get("_frontier") else ""
            layout.parts.append(
                f'<path d="M{x:.3f},{top + 7:.3f} h12" stroke={quoteattr(context.color_of(s["name"]))} stroke-width="2"{dash}/>'
            )
        for j, line in enumerate(lines):
            layout.text(line, x + 18, top + j * line_h, fs=fs)
        x += width + 15
        row_h = max(row_h, h)
    return top + row_h + 16


def _marginal(series, bbox, scale, context, axis):
    parts = []
    bins = 18
    histograms = []
    lo, hi = scale.domain
    if isinstance(scale, CategoryScale):
        return ""
    transform = math.log10 if scale.transform == "log10" else lambda v: v
    a, b = transform(lo), transform(hi)
    for s in series:
        hist = [0] * bins
        for p in s["points"]:
            v = transform(p[axis])
            if a <= v <= b:
                index = min(bins - 1, math.floor((v - a) / (b - a) * bins)) if b != a else bins // 2
                hist[index] += 1
        histograms.append((s["name"], hist))
    maximum = max((max(h) for _, h in histograms), default=1) or 1
    order = list(dict.fromkeys(context.order + context.ids))
    for name, hist in histograms:
        slot = order.index(name)
        for i, count in enumerate(hist):
            if axis == "x":
                bin_width = (bbox.x1 - bbox.x0) / bins
                slot_width = bin_width / len(order)
                w = slot_width * 0.88
                x = bbox.x0 + i * bin_width + slot * slot_width + slot_width * 0.06
                y = bbox.y1 - (bbox.y1 - bbox.y0) * count / maximum
                h = bbox.y1 - y
            else:
                bin_height = (bbox.y1 - bbox.y0) / bins
                slot_height = bin_height / len(order)
                h = slot_height * 0.88
                y = bbox.y1 - (i + 1) * bin_height + slot * slot_height + slot_height * 0.06
                x = bbox.x0
                w = (bbox.x1 - bbox.x0) * count / maximum
            if count:
                parts.append(
                    f'<rect x="{x:.3f}" y="{y:.3f}" width="{w:.3f}" height="{h:.3f}" fill={quoteattr(context.color_of(name))} fill-opacity=".6" data-role="marginal-count" data-count="{count}" data-series={quoteattr(name)}/>'
                )
    return "".join(parts)


def _spread_positions(centers, widths, low, high, gap=6):
    """Keep ordered annotations distinct without moving their data anchors."""
    if sum(widths) + gap * max(0, len(widths) - 1) > high - low:
        raise ValueError("annotation labels need a wider canvas")
    result = []
    for i, (center, width) in enumerate(zip(centers, widths)):
        minimum = low + width / 2 if not i else result[-1] + (widths[i - 1] + width) / 2 + gap
        result.append(max(minimum, min(center, high - width / 2)))
    for i in range(len(result) - 1, -1, -1):
        maximum = (
            high - widths[i] / 2 if i == len(result) - 1 else result[i + 1] - (widths[i] + widths[i + 1]) / 2 - gap
        )
        result[i] = min(result[i], maximum)
    return result


def _pad_glyph_scale(scale, extent, radius):
    """Reserve glyph envelopes while retaining a single data/axis mapping."""
    if isinstance(scale, CategoryScale):
        return scale
    if extent <= 2 * radius:
        raise ValueError("canvas must be wider and taller than its glyph diameters")
    low, high = scale.domain
    logarithmic = scale.transform == "log10"
    if logarithmic:
        low, high = math.log10(low), math.log10(high)
    padding = (high - low) * radius / (extent - 2 * radius)
    low, high = low - padding, high + padding
    try:
        domain = (10**low, 10**high) if logarithmic else (low, high)
        return SharedScale(domain, scale.ticks, transform=scale.transform)
    except (OverflowError, ValueError) as exc:
        raise ValueError("glyph extent exceeds the finite axis range; increase the canvas size") from exc


def _sample_track_specs(layout, tracks, width):
    fs = layout.font_sizes["foot"]
    specs = []
    for track in tracks:
        title = f"Sample size (n) · {track['name']}"
        height = len(wrap_lines(title, width, fs, layout.font)) * fs * 1.35
        specs.append((track, title, height, height + max(82, fs * 2.7 + 40)))
    return specs


def _render_sample_tracks(layout, tracks, bbox, scale, context):
    """Measured source titles, separate count labels and bars at their true X."""
    fs = layout.font_sizes["foot"]
    parts = []
    specs = _sample_track_specs(layout, tracks, bbox.x1 - bbox.x0)
    gap = 16
    extra = max(0, (bbox.y1 - bbox.y0 - sum(s[3] for s in specs) - gap * (len(specs) - 1)) / len(specs))
    top = bbox.y0
    for track, title, title_height, minimum in specs:
        positions, counts = track["positions"], track["counts"]
        if len(set(positions)) != len(positions):
            raise ValueError("sample counts need unique X positions within each source series")
        entries = sorted((scale.map(x, bbox.x0, bbox.x1), count, x) for x, count in zip(positions, counts))
        baseline = top + minimum + extra
        layout.text(title, bbox.x0, top, fs=fs, color=layout.pal["ink6"], width=bbox.x1 - bbox.x0)
        label_top = top + title_height + 7
        widths = [layout.measure(str(count), fs) for _, count, _ in entries]
        label_xs = _spread_positions([x for x, _, _ in entries], widths, bbox.x0, bbox.x1)
        maximum = max(counts, default=1) or 1
        color = context.color_of(track["name"])
        bar_capacity = baseline - label_top - fs * 1.35 - 15
        for (x, count, value), label_x in zip(entries, label_xs):
            nearest = min((abs(x - other) for other, _, _ in entries if other != x), default=40)
            bar_width = min(24, nearest * 0.6)
            bar_height = bar_capacity * count / maximum
            bar_top = baseline - bar_height
            parts.append(
                f'<rect x="{x - bar_width / 2:.4f}" y="{bar_top:.4f}" width="{bar_width:.4f}" height="{bar_height:.4f}" fill={quoteattr(color)} fill-opacity=".48" data-role="sample-size" data-series={quoteattr(track["name"])} data-x={quoteattr(str(value))} data-n="{count}"/>'
            )
            parts.append(
                f'<path d="M{x:.4f},{bar_top:.4f} L{label_x:.4f},{label_top + fs * 1.35:.4f}" stroke={quoteattr(color)} stroke-opacity=".4" stroke-width=".7" fill="none" data-role="sample-leader"/>'
            )
            layout.text(str(count), label_x, label_top, fs=fs, anchor="middle")
        top = baseline + gap
    return "".join(parts)


def make_xy_chart(
    series,
    *,
    title=None,
    subtitle=None,
    figure_label=None,
    note=None,
    source=None,
    x_title=None,
    y_title=None,
    x_unit="",
    y_unit="",
    width=1200,
    height=820,
    palette=None,
    font_family=None,
    x_transform="linear",
    y_transform="linear",
    reference_lines=None,
    phases=None,
    significance=None,
    show_stats=False,
    mode="single",
    residual_series=None,
    sample_sizes=None,
    size_legend_values=None,
    size_unit="",
    color_legend=None,
    radius_max=18.0,
    summary=False,
    x_scale=None,
    y_scale=None,
    table=None,
    extra_stats=None,
    rugs=None,
    glyph_renderer=None,
    legend_renderer=None,
    n_items=None,
    minimum_font_size=None,
    trend=False,
    annotations=None,
    reference_bands=None,
    end_labels=True,
):
    """Measured canvas shell used by all public Cartesian adapters."""
    layout = ChartLayout(
        width, height, palette or "archive_ink", font_family, n_items=xy_density(series) if n_items is None else n_items
    )
    fonts = layout.font_sizes
    if minimum_font_size is not None:
        floor = finite(minimum_font_size, "minimum_font_size", minimum=1)
        fonts.update({key: max(value, floor) for key, value in fonts.items()})
    tick_fs, axis_fs, small_fs = fonts["xtick"], fonts["xaxis"], fonts["foot"]
    if note or source:
        small_fs = max(small_fs, layout.width / 45)
    tick_h, small_h = tick_fs * 1.35, small_fs * 1.35
    pal = layout.pal
    W, H = layout.width, layout.height
    context = series_context(series, pal)
    ref_values = {"x": [], "y": []}
    for ref in reference_lines or []:
        r = {"value": ref[0], "label": ref[1], "axis": ref[2]} if not isinstance(ref, dict) else ref
        axis = (
            "x"
            if r.get("axis") in ("x", "v", "vertical")
            else "y"
            if r.get("axis", "y") in ("y", "h", "horizontal")
            else None
        )
        if axis and isinstance(r.get("value"), (int, float)) and math.isfinite(r["value"]):
            ref_values[axis].append(float(r["value"]))
    bands = []
    for band in [reference_bands] if isinstance(reference_bands, dict) else reference_bands or []:
        raw_points = band.get("points") if isinstance(band, dict) else band
        if not raw_points or len(raw_points) < 3:
            raise ValueError("reference_band needs >= 3 (x, y) vertices: {'points': [(x, y), ...], 'label': ...}")
        pts = [(finite(x, "reference_band x"), finite(y, "reference_band y")) for x, y in raw_points]
        bands.append({**(band if isinstance(band, dict) else {}), "points": pts})
        ref_values["x"] += [x for x, _ in pts]
        ref_values["y"] += [y for _, y in pts]
    if trend:
        ref_values["x"] += [v for ph in phases or [] for v in (ph["start"], ph["end"]) if isinstance(v, (int, float))]
        ref_values["x"] += [a["x"] for a in annotations or [] if isinstance(a.get("x"), (int, float))]
        ref_values["y"] += [a["y"] for a in annotations or [] if isinstance(a.get("y"), (int, float))]
    xa, ya = infer_scales(series, x_transform=x_transform, y_transform=y_transform, extra=ref_values, tight=bool(trend))
    xs, ys = x_scale or xa, y_scale or ya
    curve_series = [
        s
        for s in series
        if len(s["curve"]) >= 2 and all(not isinstance(p[k], str) for p in s["curve"] for k in ("x", "y"))
    ]
    direct = []
    # An unnamed series' end label would be the bare last value ("0"), which reads as a stray axis tick.
    if (
        end_labels
        and trend
        and curve_series
        and len(curve_series) <= 4
        and len(curve_series) == len(series)
        and all(str(context.label_of(s["name"])).strip() for s in curve_series)
    ):
        dfs = fonts["legend"]
        for s in curve_series:
            last = max(s["curve"], key=lambda p: p["x"])
            text = f"{context.label_of(s['name'])}  {last['y']:.4g}{y_unit if len(y_unit) <= 2 else ''}"
            direct.append((s, last, text, layout.measure(text, dfs)))
        if max(w for *_, w in direct) > W * 0.3:
            direct = []
    xfmt, xoffset = _axis_format(xs)
    yfmt, yoffset = _axis_format(ys)
    top = layout.header(title, subtitle, figure_label)
    # One named series needs no legend box: its name is the axis/title, not a key to decode.
    # A Pareto front is always named in the legend; a lone data series then shows there too.
    legend_names = {s["name"] for s in series if s.get("_legend", True)}
    if not direct and len(legend_names) > 1:
        top = _legend(layout, series, context, top)
    if legend_renderer is not None:
        top = legend_renderer(layout, top)
    stats = []
    if show_stats:
        for s in series:
            st = s.get("_stats")
            if not st:
                continue
            text = f"{s['name']} · n = {st['n']} · "
            if st["fit"] == "linear":
                text += (
                    f"R² = {st['r2']:.3f} · P {'< 0.001' if st['p'] < 0.001 else '= ' + format(st['p'], '.3f')} · "
                    + tr("Residual SE = {value}", value=f"{st['rmse']:.3g}")
                )
            else:
                text += "LOESS"
            stats.append(text)
    stats.extend(extra_stats or [])
    for line in stats:
        top += layout.text(line, 28, top, fs=fonts["label"], color=pal["ink6"], width=W - 56) + 6
    for ref in [] if trend else reference_lines or []:
        r = {"value": ref[0], "label": ref[1], "axis": ref[2]} if not isinstance(ref, dict) else ref
        if r.get("label"):
            caption = f"{r['label']} ({r.get('axis', 'y')} = {r.get('value', 'x')})"
            top += layout.text(caption, 28, top, fs=small_fs, color=pal["ink6"], width=W - 56) + 5
    if color_legend:
        lo, hi, label, color_fn = color_legend
        top += layout.text(f"{label or tr('Color')}: {lo:.4g} – {hi:.4g}", 28, top, fs=fonts["label"], width=W - 56) + 7
        bar_width = min(200, W - 56)
        for i in range(80):
            layout.parts.append(
                f'<rect x="{28 + i * bar_width / 80:.3f}" y="{top:.3f}" width="{bar_width / 80 + 0.1:.3f}" height="10" fill={quoteattr(color_fn(lo + (hi - lo) * i / 79))}/>'
            )
        top += 24
    size_values = [p["size"] for s in series for p in s["points"] if "size" in p]
    size_max = max(size_values, default=1.0)
    size_key = None  # (values, caption, width, height) when the size key goes into a free plot corner
    if size_values:
        values = (
            size_legend_values if size_legend_values is not None else sorted({size_max / 4, size_max / 2, size_max})
        )
        if any(finite(v, "size legend", minimum=0) > size_max for v in values):
            raise ValueError("size legend exceeds observed maximum")
        caption = tr("Area ∝ {label}", label=size_unit or tr("size"))
        key_w = (
            max(
                layout.measure(caption, fonts["label"]),
                sum(
                    2 * radius_max * math.sqrt(v / size_max if size_max else 0)
                    + layout.measure(f"{v:.4g}", fonts["label"])
                    + 14
                    for v in values
                ),
            )
            + 16
        )
        key_h = fonts["label"] * 1.35 + 2 * radius_max + 16
        if mode != "with_marginal" and key_w < W * 0.45:
            size_key = (values, caption, key_w, key_h)
    if size_values and size_key is None:
        x = 28.0
        row_height = 0
        label = tr("Area ∝ {label}", label=size_unit or tr("size"))
        top += layout.text(label, x, top, fs=fonts["label"], width=W - 56) + 8
        for value in values:
            r = radius_max * math.sqrt(value / size_max) if size_max else 0
            label = f"{value:.4g}"
            item_w = 2 * r + layout.measure(label, tick_fs) + 22
            if x + item_w > W - 28:
                top += max(24, row_height) + 10
                x = 28
                row_height = 0
            layout.parts.append(
                _marker(
                    x + r,
                    top + radius_max,
                    r,
                    "circle",
                    pal["ink6"],
                    opacity=0.5,
                    role="size-legend",
                    attrs=f'data-size="{value:g}"',
                )
            )
            layout.text(label, x + 2 * r + 8, top + radius_max - 6, fs=fonts["label"])
            row_height = max(row_height, 2 * radius_max)
            x += item_w
        top += max(28, row_height) + 14
    footer = []
    for value in (note, source):
        if value:
            footer.extend(wrap_lines(value, W - 56, small_fs, layout.font))
    footer_h = len(footer) * small_h + 16 if footer else 12
    ytick_width = max((layout.measure(yfmt(v), tick_fs) for v in ys.ticks or []), default=20)
    left = max(62, min(W * 0.55 if isinstance(ys, CategoryScale) else 180, ytick_width + 22))
    right = max(30.0, max((layout.measure(xfmt(v), tick_fs) for v in xs.ticks or []), default=0) / 2 + 12)
    labels = [p.get("label") for s in series for p in s["points"] if p.get("label")]
    # Rail mode only when there are many labels or labels are long: a rail outside the plot forces leader lines that
    # cross each other and detach labels from points.
    rail_width = (
        min(W * 0.32, max(110, max((layout.measure(label, fonts["label"]) for label in labels), default=0) + 16))
        if labels and len(labels) > 15
        else 0
    )
    if rail_width:
        right += rail_width + 18
    if direct:
        right = max(right, max(w for *_, w in direct) + 18)
    if table:
        right += min(280, W * 0.27) + 24
    x_lines = (
        max(
            (
                len(wrap_lines(xfmt(v), (W - left - right) / max(1, len(xs.categories)) * 0.92, tick_fs, layout.font))
                for v in xs.ticks
            ),
            default=1,
        )
        if isinstance(xs, CategoryScale)
        else 1
    )
    x_label_h = tick_h * x_lines + 14
    if x_title or x_unit:
        x_label_h += (
            max(
                18,
                len(wrap_lines(axis_caption(x_title, x_unit, title), W - left - right, axis_fs, layout.font))
                * axis_fs
                * 1.35,
            )
            + 8
        )
    bottom = H - footer_h - x_label_h
    # The y label and precision annotation live above the axes, not rotated into ticks.
    yheading = axis_caption(y_title, y_unit, title)
    if yoffset:
        yheading += (" · " if yheading else "") + yoffset
    if yheading:
        top += layout.text(yheading, left, top, fs=axis_fs, width=W - left - right, axis=True) + 9
    if xoffset:
        bottom -= small_h + 4
        layout.text(xoffset, W - right, bottom + x_label_h - 1, fs=small_fs, anchor="end", color=pal["ink6"])
    annotation_h = 0
    if phases:
        annotation_h += small_h + 10
    brackets = []
    if significance and trend and len(curve_series) >= 2:
        names = {s["name"]: s for s in curve_series}
        for sig in significance:
            pair = sig.get("between") or sig.get("pair")
            if pair is not None:
                if len(pair) != 2 or any(n not in names for n in pair):
                    raise ValueError("significance 'between' must name two curve series")
                chosen = [names[n] for n in pair]
            else:
                chosen = [s for s in curve_series if s["curve"][0]["x"] <= sig["x"] <= s["curve"][-1]["x"]][:2]
            if len(chosen) != 2:
                brackets = []
                break
            brackets.append((sig, [interpolate_curve(s["curve"], sig["x"]) for s in chosen]))
    if significance and not brackets:
        annotation_h += fonts["label"] * 1.35 + 10
    if annotation_h:
        top += annotation_h
    marginal_top = None
    marginal_right = None
    if mode == "with_marginal":
        marginal_top = BBox(left, top, W - right - 78, top + 60)
        top += 72
        marginal_right = BBox(W - right - 66, top, W - right, bottom)
        right += 78
    residual_box = None
    if residual_series is not None or sample_sizes is not None:
        available = bottom - top
        rh = max(78, min(140, available * 0.26))
        if sample_sizes is not None:
            rh = max(
                rh,
                sum(spec[3] for spec in _sample_track_specs(layout, sample_sizes, W - right - left))
                + 16 * (len(sample_sizes) - 1),
            )
        residual_box = BBox(left, bottom - rh, W - right, bottom)
        bottom -= rh + small_h + 25
    bbox = BBox(left, top, W - right, bottom)
    if bbox.x1 - bbox.x0 < 180 or bbox.y1 - bbox.y0 < 130:
        raise ValueError("canvas is too small for its titles, labels and panels; increase width or height")
    key_box = None
    if size_key is not None:
        _, _, key_w, key_h = size_key
        bubbles = [
            (
                xs.map(p["x"], bbox.x0, bbox.x1),
                ys.map(p["y"], bbox.y1, bbox.y0),
                radius_max * math.sqrt(p["size"] / size_max) if size_max else 0,
            )
            for s in series
            for p in s["points"]
            if "size" in p and not isinstance(p["x"], str) and not isinstance(p["y"], str)
        ]
        for cx0, cy0 in (
            (bbox.x1 - key_w - 6, bbox.y0 + 6),
            (bbox.x0 + 6, bbox.y0 + 6),
            (bbox.x1 - key_w - 6, bbox.y1 - key_h - 6),
            (bbox.x0 + 6, bbox.y1 - key_h - 6),
        ):
            box = (cx0, cy0, cx0 + key_w, cy0 + key_h)
            if all(
                bx + r < box[0] - 4 or bx - r > box[2] + 4 or by + r < box[1] - 4 or by - r > box[3] + 4
                for bx, by, r in bubbles
            ):
                key_box = box
                break
        if key_box is None:
            # No free corner: put the key back above the plot, as before.
            values, caption, _, _ = size_key
            shift = key_h + 6
            top += shift
            bbox = BBox(left, top, W - right, bottom)
            if bbox.y1 - bbox.y0 < 130:
                raise ValueError("canvas is too small for its titles, labels and panels; increase width or height")
            key_box = (28.0, top - shift, 28.0 + key_w, top - 6)
    if glyph_renderer is not None:
        if x_scale is None:
            xs = _pad_glyph_scale(xs, bbox.x1 - bbox.x0, radius_max + 2)
        if y_scale is None:
            ys = _pad_glyph_scale(ys, bbox.y1 - bbox.y0, radius_max + 2)
    # Label rail sits to the right of the plot.
    if labels and rail_width:
        rail_x0 = (marginal_right.x1 if marginal_right is not None else bbox.x1) + 14
        rail = BBox(rail_x0, bbox.y0, rail_x0 + rail_width, bbox.y1)
    else:
        rail = None
    if phases and trend:
        band_top = top - annotation_h
        spans = []
        for phase in phases:
            start = max(bbox.x0, xs.map(phase["start"], bbox.x0, bbox.x1))
            end = min(bbox.x1, xs.map(phase["end"], bbox.x0, bbox.x1))
            if end > start and phase.get("label"):
                spans.append(((start + end) / 2, layout.measure(phase["label"], small_fs), phase["label"]))
        if spans:
            centers = _spread_positions([c for c, _, _ in spans], [w for _, w, _ in spans], bbox.x0, bbox.x1, gap=10)
            for center, (_, _, name) in zip(centers, spans):
                layout.text(name, center, band_top, fs=small_fs, anchor="middle", color=pal["ink6"])
    elif phases:
        band_top = top - annotation_h
        for phase in phases:
            start = max(bbox.x0, xs.map(phase["start"], bbox.x0, bbox.x1))
            end = min(bbox.x1, xs.map(phase["end"], bbox.x0, bbox.x1))
            if end <= start:
                continue
            name = phase.get("label", "")
            lines = wrap_lines(name, end - start - 8, small_fs, layout.font)
            if len(lines) > 1:
                raise ValueError("phase label exceeds available interval; shorten it or increase width")
            layout.text(name, (start + end) / 2, band_top, fs=small_fs, anchor="middle")
    if significance and not brackets:
        used = []
        for sig in significance:
            p = parse_p(sig["p"]) if "p" in sig else None
            if p is not None and p > 1:
                raise ValueError("p must be between zero and one")
            label = sig.get("label") or (
                "***"
                if p is not None and p < 0.001
                else "**"
                if p is not None and p < 0.01
                else "*"
                if p is not None and p < 0.05
                else "ns"
            )
            x = xs.map(sig["x"], bbox.x0, bbox.x1)
            w = layout.measure(label, tick_fs)
            if not bbox.x0 <= x <= bbox.x1:
                raise ValueError("significance x lies outside the plotted X domain")
            if x - w / 2 < 0 or x + w / 2 > W:
                raise ValueError("significance label exceeds the canvas")
            interval = (x - w / 2, x + w / 2)
            if any(min(interval[1], b) - max(interval[0], a) > -5 for a, b in used):
                raise ValueError("significance labels overlap; increase width or use fewer annotations")
            used.append(interval)
            layout.parts.append(
                _text(
                    label, x, top - 7, layout.font, layout.ink, fs=fonts["label"], anchor="middle", role="significance"
                )
            )
    layout.parts.append(
        render_xy_plot(
            series,
            bbox,
            x_scale=xs,
            y_scale=ys,
            context=context,
            palette=pal,
            font_family=font_family,
            show_x_labels=residual_box is None,
            reference_lines=reference_lines,
            phases=phases,
            label_bbox=rail,
            radius_max=radius_max,
            size_max=size_max,
            summary=summary,
            glyph_renderer=glyph_renderer,
            font_sizes=fonts,
            reference_labels=bool(trend),
            trend=bool(trend),
            annotations=annotations,
            reference_bands=bands,
        )
    )
    if key_box is not None:
        values, caption, _, _ = size_key
        kx, ky = key_box[0] + 8, key_box[1] + 4
        layout.text(caption, kx, ky, fs=fonts["label"], color=pal["ink6"])
        cy = ky + fonts["label"] * 1.35 + 4 + radius_max
        for value in values:
            r = radius_max * math.sqrt(value / size_max) if size_max else 0
            layout.parts.append(
                _marker(
                    kx + r,
                    cy + radius_max - r,
                    r,
                    "circle",
                    pal["ink6"],
                    opacity=0.5,
                    role="size-legend",
                    attrs=f'data-size="{value:g}"',
                )
            )
            label = f"{value:.4g}"
            layout.text(label, kx + 2 * r + 5, cy + radius_max - r - fonts["label"] * 0.6, fs=fonts["label"])
            kx += 2 * r + layout.measure(label, fonts["label"]) + 14
    sig_fs = fonts["label"]
    for sig, (ya_, yb_) in brackets:
        p = parse_p(sig["p"]) if "p" in sig else None
        if p is not None and p > 1:
            raise ValueError("p must be between zero and one")
        label = sig.get("label") or (
            "***"
            if p is not None and p < 0.001
            else "**"
            if p is not None and p < 0.01
            else "*"
            if p is not None and p < 0.05
            else "ns"
        )
        x = xs.map(sig["x"], bbox.x0, bbox.x1)
        if not bbox.x0 <= x <= bbox.x1:
            raise ValueError("significance x lies outside the plotted X domain")
        y0, y1 = sorted((ys.map(ya_, bbox.y1, bbox.y0), ys.map(yb_, bbox.y1, bbox.y0)))
        if y1 - y0 > 16:
            y0, y1 = y0 + 5, y1 - 5
        w = layout.measure(label, sig_fs)
        side = 1 if x + 10 + 4 + w <= bbox.x1 else -1
        bx = x + side * 10
        tick = -side * 4
        layout.parts.append(
            f'<path d="M{bx + tick:.3f},{y0:.3f} H{bx:.3f} V{y1:.3f} H{bx + tick:.3f}" fill="none" stroke={quoteattr(layout.ink)} stroke-width=".9" data-role="significance-bracket"/>'
        )
        tx = bx + side * 4
        layout.parts.append(
            _text(
                label,
                tx,
                (y0 + y1) / 2 + sig_fs * 0.35,
                layout.font,
                layout.ink,
                fs=sig_fs,
                anchor="start" if side > 0 else "end",
                role="significance",
            )
        )
    if direct:
        dfs = fonts["legend"]
        line_h = dfs * 1.3
        entries = sorted(
            (
                (ys.map(last["y"], bbox.y1, bbox.y0), xs.map(last["x"], bbox.x0, bbox.x1), s, text)
                for s, last, text, _ in direct
            ),
            key=lambda e: e[0],
        )
        centers = _spread_positions([e[0] for e in entries], [line_h] * len(entries), bbox.y0, bbox.y1 + tick_h, gap=4)
        for (py, px, s, text), cy in zip(entries, centers):
            color = context.color_of(s["name"])
            tx = px + 9
            if abs(cy - py) > 3:
                layout.parts.append(
                    f'<path d="M{px + 5:.3f},{py:.3f} L{tx - 2:.3f},{cy:.3f}" stroke={quoteattr(color)} stroke-width=".7" fill="none" data-role="direct-label-leader"/>'
                )
            layout.parts.append(_text(text, tx, cy + dfs * 0.35, layout.font, color, fs=dfs, role="direct-label"))
    if marginal_top:
        layout.parts.append(_marginal(series, marginal_top, xs, context, "x"))
        layout.parts.append(_marginal(series, marginal_right, ys, context, "y"))
    if residual_series is not None:
        _, rs = infer_scales(residual_series)
        residual_units = {s.get("_residual_unit", "y") for s in residual_series}
        residual_label = tr("Residual · log₁₀(y)") if residual_units == {"log10(y)"} else tr("Residual")
        residual_annotation = _axis_format(rs)[1]
        if residual_annotation:
            residual_label += " · " + residual_annotation
        layout.text(residual_label, left, residual_box.y0 - 23, fs=small_fs, color=pal["ink6"])
        layout.parts.append(
            render_xy_plot(
                residual_series,
                residual_box,
                x_scale=xs,
                y_scale=rs,
                context=context,
                palette=pal,
                font_family=font_family,
                reference_lines=[{"axis": "y", "value": 0}],
                font_sizes=fonts,
            )
        )
    if sample_sizes is not None:
        layout.parts.append(_render_sample_tracks(layout, sample_sizes, residual_box, xs, context))
        layout.parts.append(_render_x_axis(xs, residual_box, layout.font, pal, font_sizes=fonts))
    axis_bottom = residual_box.y1 if residual_box else bbox.y1
    xheading = axis_caption(x_title, x_unit, title)
    if xheading:
        layout.text(
            xheading,
            (bbox.x0 + bbox.x1) / 2,
            axis_bottom + tick_h * x_lines + 16,
            fs=axis_fs,
            anchor="middle",
            width=bbox.x1 - bbox.x0,
            axis=True,
        )
    for i, line in enumerate(footer):
        layout.text(line, 28, H - footer_h + i * small_h, fs=small_fs, color=pal["ink6"])
    if table:
        tx = bbox.x1 + rail_width + 38
        tw = W - tx - 28
        ty = bbox.y0
        layout.text(tr("Top features"), tx, ty, fs=axis_fs, bold=True, width=tw)
        ty += axis_fs * 1.35 + 8
        for name, value in table:
            lines = wrap_lines(name, tw - 65, small_fs, layout.font)
            if ty + max(18, len(lines) * small_h) > bbox.y1:
                raise ValueError("top-feature table needs a taller canvas")
            layout.text(name, tx, ty, fs=small_fs, width=tw - 65)
            layout.text(value, W - 28, ty, fs=small_fs, anchor="end")
            ty += max(18, len(lines) * small_h) + 5
    if rugs:
        rug_y = bbox.y1 + 2
        for point, color in rugs:
            x = xs.map(point, bbox.x0, bbox.x1)
            if bbox.x0 <= x <= bbox.x1:
                layout.parts.append(
                    f'<path d="M{x:.4f},{rug_y:.4f} v5" stroke={quoteattr(color)} stroke-width="1.4" data-role="feature-rug"/>'
                )
    return layout.svg("Scientific Cartesian chart; observations, predictions and uncertainty retain independent data.")
