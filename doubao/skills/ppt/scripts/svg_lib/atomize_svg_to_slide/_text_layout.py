"""Split explicitly positioned text chunks without guessing glyph advances."""

from __future__ import annotations

import copy

from ._geometry import number, fmt


def native_text_baseline(element):
    """Supported horizontal, unshifted SVG baseline, or None for SVG fallback."""
    if any(element.get(k) for k in ("textLength", "lengthAdjust", "rotate")):
        return None
    if element.get("writing-mode", "horizontal-tb") not in ("horizontal-tb", "lr", "lr-tb"):
        return None
    if element.get("direction", "ltr") != "ltr" or element.get("unicode-bidi", "normal") != "normal":
        return None
    if element.get("alignment-baseline", "auto") not in ("auto", "baseline"):
        return None
    if element.get("baseline-shift", "baseline") not in ("baseline", "0", "0px", "0%"):
        return None
    if element.get("text-anchor", "start") not in ("start", "middle", "end"):
        return None
    baseline = element.get("dominant-baseline", "auto")
    if baseline not in ("auto", "alphabetic", "central", "middle"):
        return None
    try:
        number(element.get("x", "0"))
        number(element.get("y", "0"))
        if number(element.get("dx", "0")) or number(element.get("dy", "0")):
            return None
    except ValueError:
        return None
    return "alphabetic" if baseline == "auto" else baseline


def split_text(element, effective):
    if native_text_baseline(element) is None:
        return None
    if element.get("{http://www.w3.org/XML/1998/namespace}space") == "preserve":
        return None
    try:
        number(element.get("x", "0"))
        number(element.get("y", "0"))
    except ValueError:
        return None
    if not len(element):
        return [element]
    from ._rich_text import rich_runs

    if rich_runs(element) is not None:
        return [element]
    if number(element.get("opacity", "1")) != 1 or any(element.get(k) for k in ("filter", "clip-path", "mask")):
        return None
    result = []
    baseline = number(element.get("y", "0"))
    if element.text and element.text.strip():
        first = copy.deepcopy(element)
        for child in list(first):
            first.remove(child)
        result.append(effective(first, {}))
    try:
        for child in element:
            if child.tag.split("}")[-1] != "tspan" or len(child) or (child.tail and child.tail.strip()):
                return None
            if any(child.get(k) for k in ("rotate", "textLength", "lengthAdjust")):
                return None
            # A new x establishes an independent text chunk/anchor. Without it,
            # later spans depend on browser glyph shaping and stay an SVG unit.
            if result and child.get("x") is None:
                return None
            chunk = effective(child, element.attrib)
            chunk.tag = "text"
            chunk.tail = None
            if element.get("transform"):
                if child.get("transform"):
                    return None
                chunk.set("transform", element.get("transform"))
            if chunk.get("stroke") not in (None, "none") or any(
                chunk.get(k) for k in ("filter", "clip-path", "mask", "{http://www.w3.org/XML/1998/namespace}space")
            ):
                return None
            x = number(child.get("x", element.get("x", "0"))) + number(child.get("dx", "0"))
            y = number(child.get("y", fmt(baseline))) + number(child.get("dy", "0"))
            chunk.set("x", fmt(x))
            chunk.set("y", fmt(y))
            chunk.attrib.pop("dx", None)
            chunk.attrib.pop("dy", None)
            if native_text_baseline(chunk) is None:
                return None
            baseline = y
            result.append(chunk)
        return result
    except ValueError:
        return None
