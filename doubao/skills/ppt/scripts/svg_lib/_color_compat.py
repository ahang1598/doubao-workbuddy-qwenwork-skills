"""Rewrite CSS rgb()/rgba() paints into #RRGGBB plus SVG opacity attributes."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

_SVG_NS = "http://www.w3.org/2000/svg"
_COLOR = re.compile(
    r"^\s*rgba?\(\s*([\d.]+%?)\s*[,\s]\s*([\d.]+%?)\s*[,\s]\s*([\d.]+%?)\s*(?:[,/]\s*([\d.]+%?)\s*)?\)\s*$",
    re.IGNORECASE,
)
_PAINT_OPACITY = {
    "fill": "fill-opacity",
    "stroke": "stroke-opacity",
    "stop-color": "stop-opacity",
    "flood-color": "flood-opacity",
    "lighting-color": None,
}

ET.register_namespace("", _SVG_NS)
ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")


def _channel(raw: str) -> int:
    value = float(raw[:-1]) * 255 / 100 if raw.endswith("%") else float(raw)
    return max(0, min(255, round(value)))


def _alpha(raw: str | None) -> float:
    if raw is None:
        return 1.0
    value = float(raw[:-1]) / 100 if raw.endswith("%") else float(raw)
    return max(0.0, min(1.0, value))


def _format_opacity(value: float) -> str:
    return f"{value:.4g}"


def _rewrite_element(element: ET.Element) -> int:
    style = element.attrib.get("style")
    if style and "rgb" in style.lower():
        # Inline style overrides attributes; lift paint/opacity declarations so they can be rewritten together.
        lifted = set(_PAINT_OPACITY) | {name for name in _PAINT_OPACITY.values() if name}
        kept = []
        for declaration in filter(None, (part.strip() for part in style.split(";"))):
            key, _, value = (part.strip() for part in declaration.partition(":"))
            if key in lifted:
                element.set(key, value)
            else:
                kept.append(f"{key}:{value}")
        if kept:
            element.set("style", ";".join(kept))
        else:
            del element.attrib["style"]
    count = 0
    for paint, opacity_attr in _PAINT_OPACITY.items():
        match = _COLOR.match(element.get(paint, ""))
        if not match:
            continue
        red, green, blue, alpha = match.groups()
        element.set(paint, "#%02X%02X%02X" % (_channel(red), _channel(green), _channel(blue)))
        if opacity_attr is not None:
            total = _alpha(alpha) * float(element.get(opacity_attr, "1"))
            if total < 1:
                element.set(opacity_attr, _format_opacity(total))
            elif opacity_attr in element.attrib:
                del element.attrib[opacity_attr]
        count += 1
    return count


def parse_color(value):
    """CSS colour (#RGB/#RRGGBB/#RRGGBBAA, rgb()/rgba(), named, transparent) → ('#RRGGBB', alpha), or None."""
    text = str(value).strip()
    low = text.lower()
    if re.fullmatch(r"#[0-9a-f]{6}", low):
        return "#" + text[1:].upper(), 1.0
    if re.fullmatch(r"#[0-9a-f]{3}", low):
        return "#" + "".join(c * 2 for c in text[1:]).upper(), 1.0
    if re.fullmatch(r"#[0-9a-f]{8}", low):
        return "#" + text[1:7].upper(), int(text[7:9], 16) / 255
    match = _COLOR.match(text)
    if match:
        red, green, blue, alpha = match.groups()
        return "#%02X%02X%02X" % (_channel(red), _channel(green), _channel(blue)), _alpha(alpha)
    if low == "transparent":
        return "#000000", 0.0
    from .atomize_svg_to_slide._styles import _COLORS

    if low in _COLORS:
        return _COLORS[low].upper(), 1.0
    return None


def office_safe_svg(svg: str) -> str:
    """Return the same SVG with every rgb()/rgba() paint converted to hex + opacity."""
    if "rgb" not in svg.lower():
        return svg
    root = ET.fromstring(svg)
    changed = sum(_rewrite_element(element) for element in root.iter())
    if not changed:
        return svg
    return ET.tostring(root, encoding="unicode")
