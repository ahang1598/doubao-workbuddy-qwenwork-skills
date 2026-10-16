"""Display-only frequency glyphs for exact coincident pairs observations."""

from __future__ import annotations

import json
import math
from collections import Counter
from copy import deepcopy
from xml.sax.saxutils import quoteattr

from ._glyphs import pie_glyph
from ._shared import tr


def frequency_reference(groups, variables):
    """Largest exact XY multiplicity over the lower triangle, from raw rows."""
    maximum = 1
    for i, y in enumerate(variables):
        for x in variables[:i]:
            counts = Counter((row[x], row[y]) for rows in groups.values() for row in rows)
            maximum = max(maximum, max(counts.values(), default=1))
    return maximum


def frequency_note(maximum):
    return tr(
        "Coincident observations: circle/pie area ∝ n (largest n={max}); numerals give exact n, slices give "
        "group counts. Unnumbered marks are n=1. Statistics use all raw samples.",
        max=maximum,
    )


def frequency_display(series, context, maximum, *, font, ink, paper):
    """Return copied display series and a glyph callback."""
    if maximum <= 1:
        return series, None
    result = deepcopy(series)
    for item in result:
        item["points"] = []
    groups = {}
    for i, item in enumerate(series):
        for point in item["points"]:
            key = (point["x"], point["y"])
            group = groups.setdefault(key, {"owner": i, "point": dict(point), "counts": Counter()})
            group["counts"][item["name"]] += 1
    for group in groups.values():
        point = group["point"]
        counts = dict(group["counts"])
        total = sum(counts.values())
        point.update(size=total, _frequency_counts=counts, _frequency_total=total)
        result[group["owner"]]["points"].append(point)
    order = list(dict.fromkeys(context.order + context.ids))

    def glyph(point, x, y, radius, _color):
        counts = point["_frequency_counts"]
        total = point["_frequency_total"]
        values = [counts.get(name, 0) for name in order]
        colors = [context.color_of(name) for name in order]
        parts = [
            f'<g data-role="frequency-glyph" data-count="{total}" data-counts={quoteattr(json.dumps(counts, ensure_ascii=False, separators=(",", ":")))} data-x="{point["x"]:.17g}" data-y="{point["y"]:.17g}">',
            pie_glyph(x, y, radius, values, colors, stroke=paper, stroke_width=0.7),
        ]
        if total > 1:
            label = str(total)
            # At the n-reference radius a one/two-digit count remains readable;
            # longer exact counts fit the envelope rather than overflowing axes.
            fs = min(9, 2 * radius / max(1, len(label)) / 0.62)
            parts.append(
                f'<text x="{x:.4f}" y="{y + fs * 0.33:.4f}" text-anchor="middle" font-family={quoteattr(font)} font-size="{fs:.4f}" fill={quoteattr(ink)} stroke={quoteattr(paper)} stroke-width="1.7" paint-order="stroke" data-role="frequency-count">{label}</text>'
            )
        parts.append("</g>")
        return "".join(parts)

    # The callback uses the radius supplied by the XY engine; check normalization
    # independently so a future caller cannot accidentally give counts as radii.
    if any(p["size"] > maximum or not math.isfinite(p["size"]) for s in result for p in s["points"]):
        raise ValueError("frequency maximum must include every displayed count")
    return result, glyph
