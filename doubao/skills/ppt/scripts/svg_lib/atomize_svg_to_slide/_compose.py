"""Combine converted SVG and native SML objects without losing XML scope."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from ._serialize import _SML, _SVG, _declarations, _parse, serialize_slide
from ._styles import _COLORS

_SLIDE = f"{{{_SML}}}slide"
_DATA = f"{{{_SML}}}data"
_EMBED = f"{{{_SML}}}embed"
_SVG_ROOT = f"{{{_SVG}}}svg"
_WRAPPERS = {_SLIDE, _DATA, f"{{{_SML}}}presentation", "slide", "data", "presentation"}
_SML_PREFIX = f"{{{_SML}}}"
_CHART = f"{{{_SML}}}chart"
_NATIVE_OBJECTS = {
    f"{{{_SML}}}{name}" for name in ("shape", "line", "polyline", "img", "icon", "table", "chart", "embed")
}
_HEX_COLOR = re.compile(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})")
_NATIVE_COLOR_ATTRIBUTES = {
    "content": ("color", "backgroundColor", "bulletColor"),
    "span": ("color", "backgroundColor"),
    "p": ("bulletColor",),
    "ul": ("bulletColor",),
    "ol": ("bulletColor",),
    "fillColor": ("color",),
    "fillPattern": ("foregroundColor", "backgroundColor"),
    "border": ("color",),
    "borderTop": ("color",),
    "borderRight": ("color",),
    "borderBottom": ("color",),
    "borderLeft": ("color",),
    "shadow": ("color",),
    "outline": ("color",),
}


def _sml_literal_color(value):
    literal = value.strip()
    literal = "#00000000" if literal.lower() == "transparent" else _COLORS.get(literal.lower(), literal)
    if not _HEX_COLOR.fullmatch(literal):
        return value
    digits = literal[1:]
    if len(digits) in (3, 4):
        digits = "".join(ch * 2 for ch in digits)
    red, green, blue = (int(digits[i : i + 2], 16) for i in (0, 2, 4))
    if len(digits) == 6:
        return f"rgb({red},{green},{blue})"
    alpha = f"{int(digits[6:8], 16) / 255:.10f}".rstrip("0").rstrip(".")
    return f"rgba({red},{green},{blue},{alpha})"


def _normalize_native_colors(node):
    # Foreign documents are opaque, even if descendants re-enter SML. Chart
    # colors have a separate vocabulary; this pass handles basic SML only.
    if not isinstance(node.tag, str) or not node.tag.startswith(_SML_PREFIX) or node.tag == _CHART:
        return
    for attribute in _NATIVE_COLOR_ATTRIBUTES.get(node.tag[len(_SML_PREFIX) :], ()):
        value = node.get(attribute)  # Exact, unqualified attributes only.
        if value is not None:
            node.set(attribute, _sml_literal_color(value))
    for child in node:
        _normalize_native_colors(child)


def _page_nodes(node):
    yield node
    for child in node:
        # An embed's SVG is an independent document, including its own IDs.
        if node.tag == _EMBED and child.tag == _SVG_ROOT:
            continue
        yield from _page_nodes(child)


def _has_text(value):
    return bool(value and value.strip())


def _page(source, label, *, fragment=False):
    if not isinstance(source, str):
        raise TypeError(f"{label} must be an XML string, not {type(source).__name__}")
    try:
        root = _parse(source)
    except ET.ParseError as exc:
        raise ValueError(f"{label}: invalid XML: {exc}") from exc
    if root.tag != _SLIDE:
        raise ValueError(f"{label}: expected one <slide> in the SML 2.0 namespace")
    data_nodes = [child for child in root if child.tag == _DATA]
    if len(data_nodes) > 1:
        raise ValueError(f"{label}: expected at most one direct SML <data>")
    for child in root:
        if isinstance(child.tag, str) and child.tag.rsplit("}", 1)[-1] == "data" and child.tag != _DATA:
            raise ValueError(f"{label}: <data> must use the SML 2.0 namespace")
    data = data_nodes[0] if data_nodes else None
    for node in _page_nodes(root):
        if node is not root and node is not data and node.tag in _WRAPPERS:
            raise ValueError(
                f"{label}: nested slide/data/presentation wrappers are not supported — "
                "usually a to_slide()/chart_slide() fragment was pasted into page_xml AND passed as an argument; "
                "keep it out of page_xml and pass it only as publish_slide(page_xml, fragment, ...)"
            )

    if fragment:
        if data is None or len(root) != 1:
            raise ValueError(
                f"{label}: an atomized fragment must contain only one direct <data>; "
                "page-level style, note and other nodes cannot be imported"
            )
        for node, name in ((root, "slide"), (data, "data")):
            attributes = [key for key in node.attrib if key != "xmlns" and not key.startswith("xmlns:")]
            if attributes:
                raise ValueError(f"{label}: fragment <{name}> attributes cannot be imported: " + ", ".join(attributes))
        if any(_has_text(value) for value in (root.text, root.tail, data.tail)):
            raise ValueError(f"{label}: text outside <data> cannot be imported")
    if data is None:
        data = ET.Element(_DATA)
        note_index = next((i for i, child in enumerate(root) if child.tag == f"{{{_SML}}}note"), len(root))
        root.insert(note_index, data)
    if _has_text(data.text) or any(_has_text(child.tail) for child in data):
        raise ValueError(f"{label}: <data> must contain XML objects, not raw or escaped XML text")
    return root, data


def _collect_ids(root, seen, label):
    for node in _page_nodes(root):
        if isinstance(node.tag, str) and node.tag.startswith(f"{{{_SML}}}"):
            identifier = node.get("id")
            if identifier:
                if identifier in seen:
                    raise ValueError(
                        f"{label}: duplicate SML id {identifier!r} (already present in {seen[identifier]})"
                    )
                seen[identifier] = label


def _fragment(source, label):
    """Accept atomizer pages or native objects without guessing foreign XML."""
    if not isinstance(source, str):
        raise TypeError(f"{label} must be an XML string, not {type(source).__name__}")
    if not source.strip():
        raise ValueError(f"{label}: empty XML fragment")
    try:
        root = _parse(source)
    except ET.ParseError:
        root = None  # A sequence of native sibling objects may have no root.
    local = root.tag.rsplit("}", 1)[-1] if root is not None else None
    if local in {"slide", "presentation"}:
        # Keep the original strict namespace and page-metadata contract.
        return _page(source, label, fragment=True)
    if local == "data":
        wrapped = f'<slide xmlns="{_SML}">{source}</slide>'
    else:
        # Unqualified native snippets acquire SML from their enclosing data.
        wrapped = f'<slide xmlns="{_SML}"><data>{source}</data></slide>'
    fragment, data = _page(wrapped, label, fragment=True)
    objects = [child for child in data if isinstance(child.tag, str)]
    if local != "data" and not objects:
        raise ValueError(f"{label}: expected native SML objects")
    if any(child.tag not in _NATIVE_OBJECTS for child in objects):
        raise ValueError(f"{label}: expected native SML objects; page style/note and foreign roots cannot be imported")
    return fragment, data


_CHART_EMBED = re.compile(
    r'<embed\b([^>]*)>\s*(<svg\b[^>]*\bdata-(chart|drawing)-lib="1"[^>]*>.*?</svg>)\s*</embed>', re.S
)


def _editable_chart_embeds(source):
    """Hand-wrapped library SVG embeds become editable: charts semi-editable, drawings fully native."""
    if not isinstance(source, str) or not re.search(r'data-(chart|drawing)-lib="1"', source):
        return source

    def convert(match):
        attrs = dict(re.findall(r'(\w+)="([^"]*)"', match.group(1)))
        try:
            x, y, w = (float(attrs[k]) for k in ("topLeftX", "topLeftY", "width"))
        except (KeyError, ValueError):
            return match.group(0)
        if match.group(3) == "chart":
            from ..chart_split import split_chart_svg

            frag = split_chart_svg(match.group(2), x=x, y=y, width=w)
        else:
            frag = _atomize_drawing(match.group(2), x, y, w, float(attrs.get("height") or 0))
        return re.sub(r"^\s*<slide\b[^>]*>\s*<data>|</data>\s*</slide>\s*$", "", frag)

    return _CHART_EMBED.sub(convert, source)


def _atomize_drawing(svg, x, y, w, h):
    """Drawing-library SVG at (x, y, w, h) on the page → native elements, as Drawing.to_slide would do."""
    import tempfile
    from pathlib import Path
    from ._config import _CFG
    from . import atomize_svg_to_slide

    vw, vh = (float(v) for v in re.search(r'viewBox="([^"]+)"', svg).group(1).replace(",", " ").split()[2:])
    k = min(w / vw, h / vh) if h else w / vw
    keys = ("svg_w", "svg_h", "slide_x0", "slide_y0", "slide_w", "slide_h")
    saved = {key: _CFG[key] for key in keys}
    try:
        _CFG.update(svg_w=vw, svg_h=vh, slide_x0=x, slide_y0=y, slide_w=vw * k, slide_h=vh * k)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "drawing.svg"
            path.write_text(svg, encoding="utf-8")
            return atomize_svg_to_slide(path)
    finally:
        _CFG.update(saved)


# Generated-element marker. The server reassigns element ids and drops unknown attributes, but keeps
# these schema-valid, visually inert values, so a whole-deck readback can still tell generated chart /
# drawing objects from hand-written ones (lint_inspect.py waives their conversion artefacts the same way
# publish_slide does per page). Generated text has no tab characters and generated lines are single
# segments without joins, so neither value changes rendering.
GENERATED_TAB_SIZE = "47.0047"
GENERATED_MITER_LIMIT = "47"
_CONTENT = f"{{{_SML}}}content"
_BORDER = f"{{{_SML}}}border"


def _mark_generated(child):
    tag = child.tag
    if tag == f"{{{_SML}}}shape":
        content = child.find(_CONTENT)
        if content is not None:
            content.set("defaultTabSize", GENERATED_TAB_SIZE)
    elif tag == f"{{{_SML}}}line":
        border = child.find(_BORDER)
        if border is not None:
            border.set("miterLimit", GENERATED_MITER_LIMIT)


def is_generated_element(element) -> bool:
    """True when ``element`` (an SML data child, e.g. from a readback) carries the generated marker."""
    local = element.tag.rsplit("}", 1)[-1] if isinstance(element.tag, str) else ""
    if local == "shape":
        return any(
            c.tag.rsplit("}", 1)[-1] == "content" and c.get("defaultTabSize") == GENERATED_TAB_SIZE for c in element
        )
    if local == "line":
        return any(
            c.tag.rsplit("}", 1)[-1] == "border" and c.get("miterLimit") == GENERATED_MITER_LIMIT for c in element
        )
    if local == "embed":
        return any(c.tag.rsplit("}", 1)[-1] == "svg" and c.get("data-lark-generated") == "1" for c in element)
    return False


def _fit_label_backgrounds(children, margin=1.0):
    """Grow a generated label background (a small rect painted just behind a native text) to cover it."""

    def box(el):
        try:
            return [float(el.get(k)) for k in ("topLeftX", "topLeftY", "width", "height")]
        except (TypeError, ValueError):
            return None

    shape = f"{{{_SML}}}shape"
    for i, text in enumerate(children):
        if text.tag != shape or text.get("type") != "text" or text.get("rotation"):
            continue
        t = box(text)
        if not t:
            continue
        for back in reversed(children[max(0, i - 3) : i]):
            if back.tag != shape or back.get("type") not in ("rect", "roundRect") or back.get("rotation"):
                continue
            b = box(back)
            if not b or b[3] > max(2.5 * t[3], t[3] + 12) or b[2] > 3 * t[2] + 24:
                continue
            ix = min(b[0] + b[2], t[0] + t[2]) - max(b[0], t[0])
            iy = min(b[1] + b[3], t[1] + t[3]) - max(b[1], t[1])
            if ix < 0.6 * t[2] or iy < 0.6 * t[3]:
                continue
            x0, y0 = min(b[0], t[0] - margin), min(b[1], t[1] - margin)
            x1, y1 = max(b[0] + b[2], t[0] + t[2] + margin), max(b[1] + b[3], t[1] + t[3] + margin)
            if (x0, y0, x1, y1) != (b[0], b[1], b[0] + b[2], b[1] + b[3]):
                for key, value in zip(("topLeftX", "topLeftY", "width", "height"), (x0, y0, x1 - x0, y1 - y0)):
                    back.set(key, f"{value:.2f}".rstrip("0").rstrip("."))
            break


def compose_slide(page_xml: str, *atomized_fragments: str) -> str:
    """Return one SML page with fragments' direct ``<data>`` children appended."""
    page_xml = _editable_chart_embeds(page_xml)
    page, target = _page(page_xml, "page_xml")
    atomized_fragments = tuple(_editable_chart_embeds(source) for source in atomized_fragments)
    seen = {}
    _collect_ids(page, seen, "page_xml")
    for index, source in enumerate(atomized_fragments, 1):
        label = f"atomized_fragments[{index - 1}] (argument {index + 1})"
        fragment, data = _fragment(source, label)
        _collect_ids(fragment, seen, label)
        inherited = {**_declarations(fragment), **_declarations(data)}
        if data.text:
            if len(target):
                target[-1].tail = (target[-1].tail or "") + data.text
            else:
                target.text = (target.text or "") + data.text
        _fit_label_backgrounds([c for c in data if isinstance(c.tag, str)])
        for child in data:
            if isinstance(child.tag, str):
                # Keep ancestor prefix bindings used by names, QName values or
                # CSS after removing the fragment's slide/data wrappers.
                for prefix, uri in inherited.items():
                    child.attrib.setdefault("xmlns" + (":" + prefix if prefix else ""), uri)
                _mark_generated(child)
            target.append(child)
    _normalize_native_colors(page)
    return serialize_slide(page)
