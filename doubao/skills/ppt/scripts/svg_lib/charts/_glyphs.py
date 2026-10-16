"""Reusable composition glyphs (pie slices) in flat SVG."""

from __future__ import annotations

import math
from xml.sax.saxutils import quoteattr

from ._chart_layout import finite


def zero_glyph(cx, cy, color):
    return (
        f'<path d="M{cx - 2:.3f},{cy - 2:.3f} L{cx + 2:.3f},{cy + 2:.3f} '
        f'M{cx - 2:.3f},{cy + 2:.3f} L{cx + 2:.3f},{cy - 2:.3f}" '
        f'stroke={quoteattr(color)} stroke-width="1" fill="none" data-zero="true"/>'
    )


def pie_glyph(cx, cy, radius, values, colors, *, stroke="rgb(255,255,255)", stroke_width=0.8):
    """Render nonnegative multi-category slices."""
    cx, cy, radius = finite(cx, "cx"), finite(cy, "cy"), finite(radius, "radius", minimum=0)
    values = [finite(v, "pie value", minimum=0) for v in values]
    if not values or len(values) != len(colors):
        raise ValueError("pie values and colors must be nonempty and have equal lengths")
    maximum = max(values)
    total = math.fsum(v / maximum for v in values) if maximum else 0
    if total == 0 or radius == 0:
        return zero_glyph(cx, cy, stroke)
    parts, angle = [], -math.pi / 2
    for i, (value, color) in enumerate(zip(values, colors)):
        if value == 0:
            continue
        fraction = (value / maximum) / total
        attrs = f'fill={quoteattr(color)} stroke={quoteattr(stroke)} stroke-width="{stroke_width}" data-slice="{i}" data-fraction="{fraction:.12g}"'
        if fraction >= 1 - 1e-12:
            parts.append(f'<circle cx="{cx:.3f}" cy="{cy:.3f}" r="{radius:.4f}" {attrs}/>')
        else:
            stop = angle + 2 * math.pi * fraction
            x1, y1 = cx + radius * math.cos(angle), cy + radius * math.sin(angle)
            x2, y2 = cx + radius * math.cos(stop), cy + radius * math.sin(stop)
            parts.append(
                f'<path d="M{cx:.3f},{cy:.3f} L{x1:.4f},{y1:.4f} A{radius:.4f},{radius:.4f} 0 '
                f'{int(fraction > 0.5)} 1 {x2:.4f},{y2:.4f} Z" {attrs}/>'
            )
            angle = stop
    return "".join(parts)
