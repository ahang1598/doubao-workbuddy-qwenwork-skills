"""Internal typography policy based on visible density and available canvas."""

from __future__ import annotations

import math


def chart_font_sizes(width, height, n_items):
    """Choose font sizes for a chart or panel without changing its viewBox."""
    width, height = float(width), float(height)
    if not math.isfinite(width) or not math.isfinite(height) or min(width, height) <= 0:
        raise ValueError("Typography requires positive finite canvas dimensions")
    count = float(n_items if n_items is not None else 8)
    if not math.isfinite(count):
        raise ValueError("Typography requires a finite visible item count")
    count = max(1.0, count)
    stops = ((4, 24), (8, 22), (15, 19), (30, 16), (60, 14))
    base = float(stops[-1][1])
    if count <= stops[0][0]:
        base = float(stops[0][1])
    else:
        for index in range(1, len(stops)):
            (lo, a), (hi, b) = stops[index - 1], stops[index]
            if count <= hi:
                base = a + (b - a) * (count - lo) / (hi - lo)
                break
    scale = min(1.35, max(0.45, min(math.sqrt(width / 1200), math.sqrt(height / 800))))
    body = max(12.0, base * scale)
    return {
        "title": max(18.0, body * 1.4),
        "subtitle": max(11.0, body * 0.75),
        "figure": max(10.0, body * 0.65),
        "body": body,
        "xtick": body,
        "ytick": body,
        "xaxis": body * 1.1,
        "yaxis": body * 1.1,
        "group": body,
        "group_n": max(10.0, body * 0.72),
        "label": body,
        "legend": max(10.0, body * 0.9),
        "foot": max(10.0, body * 0.6),
    }
