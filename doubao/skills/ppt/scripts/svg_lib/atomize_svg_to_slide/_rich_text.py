"""Inline tspan runs expressed as native SML spans in one editable text box."""

from __future__ import annotations

import copy
import re
import xml.etree.ElementTree as ET
from ._geometry import number

_FORBIDDEN = {
    "x",
    "y",
    "dx",
    "dy",
    "rotate",
    "transform",
    "textLength",
    "lengthAdjust",
    "filter",
    "mask",
    "clip-path",
    "writing-mode",
    "dominant-baseline",
    "alignment-baseline",
    "baseline-shift",
}
_STYLE = {"font-family", "font-size", "font-weight", "font-style", "fill", "fill-opacity", "letter-spacing", "color"}


def rich_runs(element):
    """Return normalized text/style runs, or None for coordinate-dependent text."""
    from ._svg_input import _effective

    if not len(element):
        return None
    runs = []

    def visit(node, parent, root=False):
        if not root and (node.tag.split("}")[-1] != "tspan" or any(k in node.attrib for k in _FORBIDDEN)):
            raise ValueError("Positioned or unsupported inline span")
        current = _effective(node, parent)
        if current.get("stroke") not in (None, "none"):
            raise ValueError("Stroked rich text")
        if not root and current.get("opacity") not in (None, "1", "1.0"):
            raise ValueError("Composited span")
        if any(current.get(k) for k in ("filter", "mask", "clip-path")):
            raise ValueError("Text effect")
        if "url(" in current.get("fill", ""):
            raise ValueError("Painted text")
        style = {k: v for k, v in current.attrib.items() if k in _STYLE}
        if style.get("fill") == "currentColor":
            style["fill"] = style.get("color", "#000000")
        if node.text:
            runs.append((node.text, style))
        for child in node:
            visit(child, current.attrib)
            if child.tail:
                runs.append((child.tail, style))

    try:
        visit(element, {}, True)
    except ValueError:
        return None
    # Collapse across run boundaries, retaining one separating space and styles.
    clean = []
    last_space = True
    for text, style in runs:
        text = re.sub(r"[\t\r\n ]+", " ", text)
        if last_space:
            text = text.lstrip(" ")
        if text:
            clean.append((text, style))
            last_space = text.endswith(" ")
    if clean:
        clean[-1] = (clean[-1][0].rstrip(" "), clean[-1][1])
    clean = [(t, s) for t, s in clean if t]
    if element.get("dominant-baseline") in ("central", "middle"):
        # An inline span that changes the font's baseline table cannot safely
        # share the simple native box placement used for centered labels.
        for _, style in clean:
            if number(style.get("font-size", element.get("font-size", "16"))) != number(element.get("font-size", "16")):
                return None
            if style.get("font-family", element.get("font-family", "")) != element.get("font-family", ""):
                return None
    return clean or None


def convert_rich_text(element, defs, plain_converter, *, _font_policy=None):
    from ._font_metrics import text_advance
    from ._config import _CFG
    from ._paint import _map_svg_font_family, _apply_opacity
    from ._scale import _font_scale_ratio, _sw, _sx

    runs = rich_runs(element)
    if runs is None:
        return None
    plain = copy.deepcopy(element)
    for child in list(plain):
        plain.remove(child)
    plain.attrib.pop("data-atom-angle", None)
    plain.attrib.pop("data-atom-flip-y", None)
    plain.text = "".join(t for t, _ in runs)
    if _font_policy is None:
        fragment = plain_converter(ET.tostring(plain, encoding="unicode"), defs)
    else:
        fragment = plain_converter(ET.tostring(plain, encoding="unicode"), defs, _font_policy=_font_policy)
    if not fragment:
        return ""
    shape = ET.fromstring(fragment)
    content = shape.find("content")
    if content is None:
        return None
    p = content.find("p")
    p.text = None
    natural = number(element.get("font-size", "16")) * _font_scale_ratio()
    base = float(content.get("fontSize"))
    ratio = base / max(natural, 1e-9)
    width = 0
    max_size = base
    mode = _CFG.get("font_metrics", "auto")
    run_policies = [] if _font_policy is not None else None
    for index, (text, style) in enumerate(runs):
        source_size = number(style.get("font-size", element.get("font-size", "16")))
        run_natural = source_size * _font_scale_ratio()
        size = run_natural * ratio
        if run_policies is not None:
            run_policies.append(
                {
                    "run_index": index,
                    "source_font_size": source_size,
                    "natural_slide_font_size": run_natural,
                    "computed_slide_font_size": size,
                }
            )
        family = _map_svg_font_family(style.get("font-family", element.get("font-family", "")))
        weight = style.get("font-weight", "normal")
        italic = style.get("font-style", "normal")
        spacing = (
            _sw(number(style["letter-spacing"]))
            if "letter-spacing" in style
            else float(content.get("letterSpacing", "0"))
        )
        attrs = {
            "fontSize": f"{size:.6g}",
            "color": _apply_opacity(style.get("fill", "#000000"), number(style.get("fill-opacity", "1"))),
            "bold": "true" if weight in ("bold", "bolder", "600", "700", "800", "900") else "false",
            "italic": "true" if italic in ("italic", "oblique") else "false",
            "letterSpacing": f"{spacing:.6g}",
        }
        if family:
            attrs["fontFamily"] = family
        ET.SubElement(p, "span", attrs).text = text
        width += text_advance(text, family, size, weight, italic, spacing, metrics=mode)
        if index < len(runs) - 1:
            width += spacing
        max_size = max(max_size, size)
    from ._font_metrics import lint_floor_width

    # Mirror the server lint: it measures the joined line at the largest run size,
    # bold if any run is bold.
    bold_line = any(
        style.get("font-weight", "normal") in ("bold", "bolder", "600", "700", "800", "900") for _, style in runs
    )
    lint_width = lint_floor_width(
        "".join(text for text, _ in runs),
        _map_svg_font_family(element.get("font-family", "")),
        max_size,
        "bold" if bold_line else "normal",
    )
    width = max(1, width + max_size * 0.5, lint_width + max_size * 0.1)
    # Different font sizes share one native baseline; the shape has room for the
    # tallest run while preserving the original anchor and baseline estimate.
    anchor = element.get("text-anchor", "start")
    x = _sx(number(element.get("x", "0")))
    plain_height = float(shape.get("height"))
    baseline_y = float(shape.get("topLeftY")) + plain_height / 2 + 0.35 * base
    height = max(plain_height, max_size)
    shape.set("height", f"{height:.6f}")
    shape.set("topLeftY", f"{baseline_y - 0.35 * max_size - height / 2:.6f}")
    shape.set("width", f"{width:.6f}")
    shape.set("topLeftX", f"{x - (width / 2 if anchor == 'middle' else width if anchor == 'end' else 0):.6f}")
    if _font_policy is not None:
        _font_policy.update(
            kind="rich_text", rich_base_natural_slide_font_size=natural, base_adjustment_ratio=ratio, runs=run_policies
        )
    return ET.tostring(shape, encoding="unicode")
