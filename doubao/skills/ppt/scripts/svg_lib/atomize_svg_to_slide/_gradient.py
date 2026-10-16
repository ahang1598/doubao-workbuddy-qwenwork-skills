"""Coordinate-aware linear fills with bounded service-compatible quantization."""

from __future__ import annotations

from functools import lru_cache
import math
import re
import xml.etree.ElementTree as ET
from typing import Optional, Tuple

from ._svg_input import svg_name


def _fraction(value: str) -> float:
    value = value.strip()
    result = float(value[:-1]) / 100 if value.endswith("%") else float(value)
    if not math.isfinite(result):
        raise ValueError("Non-finite gradient coordinate")
    return result


def _rgba(value: str) -> Tuple[int, int, int, float]:
    if re.fullmatch(r"#[0-9a-fA-F]{6}", value):
        return int(value[1:3], 16), int(value[3:5], 16), int(value[5:7], 16), 1.0
    match = re.fullmatch(r"(rgb|rgba)\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([.\d]+)\s*)?\)", value)
    if not match or (match[1] == "rgba") != (match[5] is not None):
        raise ValueError("Unsupported stop color")
    r, g, b = (int(match[i]) for i in (2, 3, 4))
    alpha = float(match[5]) if match[5] is not None else 1.0
    if max(r, g, b) > 255 or not 0 <= alpha <= 1:
        raise ValueError("Out-of-range stop color")
    return r, g, b, alpha


@lru_cache(maxsize=128)
def _gradient_spec(paint: str, all_defs: str):
    match = re.fullmatch(r"url\(#([^)]+)\)", paint.strip())
    if not match or not all_defs:
        return None
    try:
        resources = ET.fromstring(all_defs)
        gradient = next((e for e in resources if e.get("id") == match[1]), None)
        if gradient is None or svg_name(gradient.tag) != "linearGradient":
            return None
        supported = {"id", "x1", "y1", "x2", "y2", "gradientUnits", "spreadMethod", "color-interpolation"}
        if set(gradient.attrib) - supported:
            return None
        if (
            gradient.get("gradientUnits", "objectBoundingBox") not in ("objectBoundingBox", "userSpaceOnUse")
            or gradient.get("spreadMethod", "pad") != "pad"
            or gradient.get("color-interpolation", "sRGB") != "sRGB"
        ):
            return None
        coords = tuple(
            gradient.get(k, default) for k, default in (("x1", "0"), ("y1", "0"), ("x2", "100%"), ("y2", "0"))
        )
        units = gradient.get("gradientUnits", "objectBoundingBox")
        stops = []
        last_offset = -1.0
        for stop in gradient:
            if svg_name(stop.tag) in {"title", "desc"}:
                continue
            if svg_name(stop.tag) != "stop" or set(stop.attrib) - {"offset", "stop-color", "stop-opacity"}:
                return None
            offset = _fraction(stop.get("offset", "0"))
            alpha = float(stop.get("stop-opacity", "1"))
            if not last_offset <= offset <= 1 or offset < 0 or not 0 <= alpha <= 1:
                return None
            r, g, b, a = _rgba(stop.get("stop-color", "#000000").strip())
            stops.append((offset, r, g, b, a * alpha))
            last_offset = offset
        return (units, coords, tuple(stops)) if len(stops) >= 2 else None
    except (ET.ParseError, ValueError):
        return None


def gradient_field(paint, all_defs, bbox, viewport):
    """Return kx,ky,b,stops with SVG gradient parameter t=kx*x+ky*y+b."""
    spec = _gradient_spec(paint, all_defs)
    if spec is None or bbox is None:
        return None
    units, coords, stops = spec
    x, y, w, h = bbox
    if min(w, h) <= 0:
        return None
    try:
        if units == "objectBoundingBox":
            x1, y1, x2, y2 = map(_fraction, coords)
            dx = x2 - x1
            dy = y2 - y1
            norm = dx * dx + dy * dy
            if norm < 1e-24:
                return (0, 0, 1, stops)
            kx = dx / (w * norm)
            ky = dy / (h * norm)
            b = -(dx * x1 + dy * y1) / norm - kx * x - ky * y
        else:

            def coordinate(value, axis):
                return (
                    viewport[axis] + _fraction(value) * viewport[axis + 2]
                    if value.endswith("%")
                    else float(value.removesuffix("px"))
                )

            x1 = coordinate(coords[0], 0)
            y1 = coordinate(coords[1], 1)
            x2 = coordinate(coords[2], 0)
            y2 = coordinate(coords[3], 1)
            dx = x2 - x1
            dy = y2 - y1
            norm = dx * dx + dy * dy
            if norm < 1e-24:
                return (0, 0, 1, stops)
            kx = dx / norm
            ky = dy / norm
            b = -kx * x1 - ky * y1
        if not all(math.isfinite(v) for v in (kx, ky, b)):
            return None
        return kx, ky, b, stops
    except ValueError:
        return None


def _service_numbers(angle, positions, width, height):
    """Integer angle/RGB/percent syntax accepted by Slides' fill parser."""
    rounded_angle = round(angle) % 360

    def parameter(theta, x, y):
        a = math.radians(theta)
        ux, uy = math.sin(a), -math.cos(a)
        return 0.5 + (ux * x + uy * y) / (abs(width * ux) + abs(height * uy))

    shift = max(
        abs(parameter(angle, x, y) - parameter(rounded_angle, x, y))
        for x in (-width / 2, width / 2)
        for y in (-height / 2, height / 2)
    )
    quant = [(round(p * 100) / 100, tuple(round(v) for v in c[:3]) + (c[3],)) for p, c in positions]
    shift += max(abs(p - q) for (p, _), (q, _) in zip(positions, quant))
    color_error = max(abs(a - b) * c[3] for (_, c), (_, d) in zip(positions, quant) for a, b in zip(c[:3], d[:3]))
    slope = 0
    for (p, c), (q, d) in zip(positions, positions[1:]):
        delta = max(abs(c[i] * c[3] - d[i] * d[3]) + 255 * abs(c[3] - d[3]) for i in range(3))
        if q - p < 1e-14:
            if delta > 1e-12 and shift > 1e-12:
                return None
        else:
            slope = max(slope, delta / (q - p))
    if color_error + slope * shift > 2 + 1e-9:
        return None
    return rounded_angle, quant


def native_linear_gradient(
    paint: str,
    all_defs: str,
    opacity: float = 1.0,
    bbox=None,
    viewport=None,
    target_bbox=None,
    scale_xy=(1, 1),
    service_safe=True,
) -> Optional[str]:
    spec = _gradient_spec(paint, all_defs)
    if spec is None or not math.isfinite(opacity) or not 0 <= opacity <= 1:
        return None
    if bbox is None:
        # Preserve the standalone API for the original full-axis subset.
        units, coords, _ = spec
        if units != "objectBoundingBox":
            return None
        x1, y1, x2, y2 = map(_fraction, coords)
        if not (y1 == y2 and (x1, x2) in ((0, 1), (1, 0)) or x1 == x2 and (y1, y2) in ((0, 1), (1, 0))):
            return None
        bbox = (0, 0, 1, 1)
    field = gradient_field(paint, all_defs, bbox, viewport or (0, 0, 1, 1))
    if field is None:
        return None
    kx, ky, b, stops = field
    x, y, w, h = target_bbox or bbox
    sx, sy = scale_xy
    if min(w, h, sx, sy) <= 0:
        return None
    length = math.hypot(kx / sx, ky / sy)
    if length < 1e-20:
        angle = 90
        positions = [(0, stops[-1][1:]), (1, stops[-1][1:])]
    else:
        ux, uy = kx / sx / length, ky / sy / length
        angle = math.degrees(math.atan2(ux, -uy)) % 360
        span = (abs(w * sx * ux) + abs(h * sy * uy)) * length
        low = kx * (x + w / 2) + ky * (y + h / 2) + b - span / 2
        positions = [((off - low) / span, (r, g, bl, a)) for off, r, g, bl, a in stops]

        def color_at(t):
            if t < stops[0][0]:
                return stops[0][1:]
            for left, right in zip(stops, stops[1:]):
                if left[0] <= t < right[0]:
                    f = (t - left[0]) / (right[0] - left[0])
                    alpha = left[4] * (1 - f) + right[4] * f
                    rgb = [
                        (left[i] * left[4] * (1 - f) + right[i] * right[4] * f) / alpha if alpha > 1e-15 else 0
                        for i in (1, 2, 3)
                    ]
                    return (*rgb, alpha)
            return stops[-1][1:]

        trimmed = [(max(0, min(1, p)), c) for p, c in positions if -1e-10 <= p <= 1 + 1e-10]
        if positions[0][0] < -1e-10:
            trimmed.insert(0, (0, color_at(low)))
        if positions[-1][0] > 1 + 1e-10:
            trimmed.append((1, color_at(low + span)))
        positions = trimmed
        if not positions:
            return None
    positions = [(0 if abs(p) < 1e-10 else 1 if abs(p - 1) < 1e-10 else p, c) for p, c in positions]
    if service_safe:
        safe = _service_numbers(angle, positions, w * sx, h * sy)
        if safe is None:
            return None
        angle, positions = safe

    def alpha_text(value):
        return f"{value:.12f}".rstrip("0").rstrip(".") or "0"

    colors = [
        f"rgba({r:.12g},{g:.12g},{bl:.12g},{alpha_text(a * opacity)}) {pos * 100:.12g}%"
        for pos, (r, g, bl, a) in positions
    ]
    if len(colors) == 1:
        colors = [colors[0].rsplit(" ", 1)[0] + " 0%", colors[0].rsplit(" ", 1)[0] + " 100%"]
    return f"linear-gradient({angle:.12g}deg,{','.join(colors)})"
