"""Parse SVG once, then serialize atoms into the converters' canonical syntax."""

from __future__ import annotations

import copy
import xml.etree.ElementTree as ET
from typing import Iterator, Tuple

from ._geometry import Matrix, parse_transform, transform_element, number, fmt
from ._markers import expand_markers
from ._text_layout import split_text
from ._config import _CFG
from ._styles import _COLORS

SVG_NS = "http://www.w3.org/2000/svg"
GEOMETRY = {"rect", "line", "circle", "ellipse", "text", "path", "polygon", "polyline"}
_NON_RENDERING = {"title", "desc", "metadata", "defs"}
_PRESENTATION = {
    "fill",
    "fill-opacity",
    "fill-rule",
    "stroke",
    "stroke-width",
    "stroke-opacity",
    "stroke-dasharray",
    "stroke-linecap",
    "stroke-linejoin",
    "font-family",
    "font-size",
    "font-weight",
    "font-style",
    "text-anchor",
    "color",
    "opacity",
    "filter",
    "transform",
    "clip-path",
    "mask",
    "style",
    "class",
    "display",
    "visibility",
    "color-interpolation",
    "stop-color",
    "stop-opacity",
    "letter-spacing",
    "marker-start",
    "marker-mid",
    "marker-end",
    "stroke-dashoffset",
    "stroke-miterlimit",
    "dominant-baseline",
    "alignment-baseline",
    "baseline-shift",
    "writing-mode",
    "direction",
    "unicode-bidi",
}
_INHERITED = _PRESENTATION - {
    "opacity",
    "filter",
    "transform",
    "clip-path",
    "mask",
    "style",
    "class",
    "display",
    "alignment-baseline",
    "baseline-shift",
    "unicode-bidi",
    "stop-color",
    "stop-opacity",
}
_EFFECTS = {"filter", "clip-path", "mask", "mix-blend-mode", "isolation"}


def _effective(element, inherited):
    result = copy.deepcopy(element)
    attributes = {k: v for k, v in inherited.items() if k in _INHERITED}
    own = dict(element.attrib)
    for declaration in own.pop("style", "").split(";"):
        if not declaration.strip():
            continue
        key, sep, value = declaration.partition(":")
        key = key.strip()
        value = value.strip()
        if not sep or key not in _PRESENTATION | _EFFECTS:
            raise ValueError("Unsupported inline style")
        own[key] = value.removesuffix("!important").strip()
    for key, value in own.items():
        if value == "inherit" and key in _PRESENTATION:
            if key in inherited:
                attributes[key] = inherited[key]
            else:
                attributes.pop(key, None)
        else:
            attributes[key] = value
    # Presentation attributes and legacy inline styles bypass the stylesheet cascade.
    for key in ("fill", "stroke", "color", "stop-color"):
        if key in attributes:
            attributes[key] = _COLORS.get(attributes[key].strip().lower(), attributes[key])
    if not len(element):
        if attributes.get("fill") == "currentColor":
            attributes["fill"] = attributes.get("color", "#000000")
        if attributes.get("stroke") == "currentColor":
            attributes["stroke"] = attributes.get("color", "#000000")
    for key in ("font-size", "stroke-width", "opacity", "fill-opacity", "stroke-opacity"):
        if key in attributes:
            attributes[key] = fmt(number(attributes[key]))
    if "letter-spacing" in attributes:
        value = attributes["letter-spacing"]
        if value == "normal":
            value = "0"
        elif value.endswith("em"):
            if "font-size" not in attributes:
                raise ValueError("Relative spacing without font size")
            value = fmt(number(value[:-2]) * number(attributes["font-size"]))
        attributes["letter-spacing"] = fmt(number(value))
    result.attrib.clear()
    result.attrib.update(attributes)
    return result


def svg_name(tag: str) -> str:
    if tag.startswith("{"):
        namespace, name = tag[1:].split("}", 1)
        return name if namespace == SVG_NS else ""
    return tag


def serialize_svg(element: ET.Element) -> str:
    """Use double quotes/self-closing geometry without SVG namespace prefixes."""
    element = copy.deepcopy(element)
    element.tail = None
    for node in element.iter():
        if node.tag.startswith("{" + SVG_NS + "}"):
            node.tag = node.tag.split("}", 1)[1]
    return ET.tostring(element, encoding="unicode", short_empty_elements=True).replace(" />", "/>")


_GEOMETRY_NUMBERS = {
    "rect": ("x", "y", "width", "height", "rx", "ry"),
    "circle": ("cx", "cy", "r"),
    "ellipse": ("cx", "cy", "rx", "ry"),
    "line": ("x1", "y1", "x2", "y2"),
}


def _own_references(node):
    from ._resources import URL_REF, XLINK

    found = set()
    for key, value in node.attrib.items():
        found.update(URL_REF.findall(value))
        if key in ("href", XLINK) and value.startswith("#"):
            found.add(value[1:])
    return found


def _check_authoring_errors(root: ET.Element) -> None:
    """Reject broken input instead of silently dropping it or hiding it in an embed."""
    from ._geometry import numbers, path_segments
    from ._resources import references
    import math
    import re as _re

    index = {node.get("id"): node for node in root.iter() if node.get("id")}
    for node in root.iter():
        for key in _own_references(node):
            if key not in index:
                raise ValueError(
                    f"Missing SVG definition #{key} referenced by <{svg_name(node.tag)}>; "
                    "add the definition or remove the reference"
                )
    for start in index:
        seen, current = set(), start
        while current in index and current not in seen:
            seen.add(current)
            nxt = [ref for ref in references(index[current]) if ref in index]
            current = nxt[0] if len(nxt) == 1 else None
        if current is not None and current in seen:
            raise ValueError(f"Cyclic SVG reference through #{current}")
    for node in root.iter():
        tag = svg_name(node.tag)
        if tag == "path" and node.get("d", "").strip():
            try:
                path_segments(node.get("d"))
            except ValueError as error:
                raise ValueError(
                    f"Invalid SVG path d={node.get('d')[:60]!r}: {error}; "
                    "fix the path data instead of deleting the element"
                ) from error
        for key in _GEOMETRY_NUMBERS.get(tag, ()):
            value = node.get(key)
            if value is not None and value.strip() not in ("auto",):
                try:
                    number(value)
                except ValueError as error:
                    raise ValueError(f"Invalid <{tag}> {key}={value!r}; use a plain number") from error
        if tag in ("polygon", "polyline"):
            try:
                points = numbers(node.get("points", ""))
            except ValueError:
                points = None
            if points is None or len(points) % 2 or len(points) < 4:
                raise ValueError(f"<{tag}> points={node.get('points', '')!r} needs complete x/y pairs")
        for key in ("fill", "stroke", "stop-color", "color"):
            value = (node.get(key) or "").strip()
            if value.lower().startswith(("rgb(", "rgba(")) and not _re.fullmatch(
                r"rgba?\(\s*[\d.]+%?\s*[,\s]\s*[\d.]+%?\s*[,\s]\s*[\d.]+%?\s*(?:[,/]\s*[\d.eE+-]+%?\s*)?\)", value
            ):
                raise ValueError(f"Invalid SVG color {key}={value!r}; use #RRGGBB or rgb()/rgba() numbers")
        if tag == "marker" and node.get("viewBox") is not None:
            try:
                box = numbers(node.get("viewBox"))
            except ValueError:
                box = []
            if len(box) != 4 or not all(math.isfinite(v) for v in box) or min(box[2:]) <= 0:
                raise ValueError(f"Marker #{node.get('id')} needs a finite positive viewBox")


class InvalidSvgXml(ValueError, ET.ParseError):
    """Malformed source XML; never partially rendered."""

    def __init__(self, error: ET.ParseError):
        self.message = f"Invalid SVG XML: {error}"
        super().__init__(self.message)
        self.code, self.position = getattr(error, "code", None), getattr(error, "position", None)

    def __str__(self):
        return self.message


def parse_svg(source: str) -> Tuple[ET.Element, str]:
    try:
        root = ET.fromstring(source)
    except ET.ParseError as error:
        raise InvalidSvgXml(error) from error
    if svg_name(root.tag) != "svg":
        raise ValueError("Expected an SVG root element")
    ids = set()
    for node in root.iter():
        identifier = node.get("id")
        if identifier:
            if identifier in ids:
                raise ValueError(f"Duplicate SVG id: {identifier!r}")
            ids.add(identifier)
    # Mapping remains caller-owned. gen_svg_relations already compensates for
    # nonzero viewBox origins through set_mapping; do not apply it a second time.

    for parent in root.iter():
        if svg_name(parent.tag) == "script":
            raise ValueError("SVG scripts are not supported")
    _check_authoring_errors(root)
    from ._styles import flatten_styles

    root = flatten_styles(root, source)
    from ._instances import expand_instances

    root = expand_instances(root)
    resources = ET.Element("defs")

    def collect_resources(parent: ET.Element, inherited=None) -> None:
        try:
            context = _effective(parent, inherited or {}).attrib
        except ValueError:
            context = inherited or {}
        for child in parent:
            if svg_name(child.tag) == "defs":
                # Paint/marker definitions keep their own presentation context.
                def materialize(node, parent_style):
                    normalized = _effective(node, parent_style)
                    for item in list(normalized):
                        normalized.remove(item)
                    for item in node:
                        normalized.append(materialize(item, normalized.attrib))
                    return normalized

                definition_style = _effective(child, context).attrib
                for resource in child:
                    resources.append(materialize(resource, definition_style))
            elif svg_name(child.tag) == "g":
                collect_resources(child, context)

    collect_resources(root)
    return root, serialize_svg(resources) if len(resources) else ""


def _inline_markers(tree, defs):
    """Replace marker references inside an SVG fallback with the equivalent marker shapes."""
    keys = ("marker-start", "marker-mid", "marker-end")
    carried = ("opacity", "transform", "filter", "clip-path", "mask")
    for parent in list(tree.iter()):
        for index, child in reversed(list(enumerate(list(parent)))):
            if not any(child.get(k) not in (None, "none") for k in keys):
                continue
            # Group-level effects on the host apply equally to its markers: move them onto a
            # wrapping <g> so the plain host and the expanded marker shapes share them.
            wrap = {k: child.get(k) for k in carried if child.get(k) not in (None, "", "none")}
            probe = copy.deepcopy(child)
            for k in wrap:
                probe.attrib.pop(k, None)
            expanded = expand_markers(probe, defs)
            if not expanded or any(any(a.get(k) not in (None, "none") for k in keys) for a in expanded):
                continue
            parent.remove(child)
            if wrap:
                group = ET.Element(child.tag.rsplit("}", 1)[0] + "}g" if "}" in child.tag else "g", wrap)
                group.extend(expanded)
                group.tail = child.tail
                parent.insert(index, group)
            else:
                for offset, atom in enumerate(expanded):
                    parent.insert(index + offset, atom)


def iter_atoms(root: ET.Element, all_defs: str = "", *, observer=None) -> Iterator[Tuple[str, str]]:
    def emit(kind, tag, sources, reason):
        if observer is not None:
            observer({"source_ids": list(dict.fromkeys(sources)), "reason": reason, "kind": kind})
        return kind, tag

    def fallback(node, inherited, matrix, sources, reason):
        wrapper = ET.Element("g", {k: v for k, v in inherited.items() if k in _INHERITED})
        if matrix != Matrix():
            wrapper.set("transform", matrix.svg())

        def canonical(item, context):
            normalized = _effective(item, context)
            for child in list(normalized):
                normalized.remove(child)
            for child in item:
                normalized.append(canonical(child, normalized.attrib))
            return normalized

        original = canonical(node, inherited)
        if svg_name(original.tag) == "svg":
            original.tag = "g"
            for key in ("width", "height", "viewBox", "preserveAspectRatio", "version"):
                original.attrib.pop(key, None)
        for parent in original.iter():
            for child in list(parent):
                if svg_name(child.tag) in _NON_RENDERING:
                    parent.remove(child)
        wrapper.append(original)
        _inline_markers(wrapper, all_defs)
        return emit("_embed", serialize_svg(wrapper), sources, reason)

    def walk(node, inherited, matrix, sources=()):
        sources = sources + ((node.get("id"),) if node.get("id") else ())
        name = svg_name(node.tag)
        if name in _NON_RENDERING:
            return
        if name not in GEOMETRY | {"g", "svg"}:
            raise ValueError(f"Unsupported SVG element {node.tag!r}")
        try:
            element = _effective(node, inherited)
        except ValueError as error:
            yield fallback(node, inherited, matrix, sources, "presentation: " + str(error))
            return
        if element.get("display") == "none":
            return
        if element.get("clip-path") not in (None, "none"):
            from ._clip import expand_clip

            clipped = expand_clip(element, all_defs)
            if clipped is not None:
                yield from walk(clipped, {}, matrix, sources)
                return
        if name == "svg" and node is not root:
            raise ValueError("Nested SVG viewports are not supported")
        if name in ("g", "svg"):
            try:
                # A geometric group transform distributes over its children. Carry the full affine matrix; unsupported
                # leaf transforms keep that leaf as SVG instead of merging an entire scene.
                local = matrix.then(parse_transform(element.get("transform", "")))
                if number(element.get("opacity", "1")) != 1 or any(
                    element.get(k) not in (None, "none", "normal", "auto") for k in _EFFECTS
                ):
                    raise ValueError("Group compositing")
            except ValueError as error:
                yield fallback(node, inherited, matrix, sources, "group: " + str(error))
                return
            for child in node:
                yield from walk(child, element.attrib, local, sources)
            return
        if element.get("visibility") in ("hidden", "collapse"):
            return
        element.attrib.setdefault("fill", "none" if name == "line" else "#000000")
        element.attrib.setdefault("stroke", "none")
        if name == "text":
            element.attrib.setdefault("font-size", "16")
        if "url(" in element.get("fill", ""):
            element.set("data-atom-viewport", root.get("viewBox", f"0 0 {_CFG['svg_w']} {_CFG['svg_h']}"))
        if any(element.get(k) not in (None, "none", "normal", "auto") for k in _EFFECTS - {"filter"}):
            yield fallback(node, inherited, matrix, sources, "effect_compositing")
            return
        from ._effects import needs_svg

        probe = copy.deepcopy(element)
        probe.attrib.pop("transform", None)
        if needs_svg(probe, all_defs):
            yield fallback(node, inherited, matrix, sources, "fidelity_gate")
            return
        if name == "text" and element.get("stroke") not in (None, "none"):
            yield fallback(node, inherited, matrix, sources, "text_stroke")
            return
        if element.get("dx") or element.get("dy"):
            yield fallback(node, inherited, matrix, sources, "positioned_text")
            return
        pieces = split_text(element, _effective) if name == "text" else [element]
        if pieces is None:
            yield fallback(node, inherited, matrix, sources, "complex_text_layout")
            return
        output = []
        try:
            for piece in pieces:
                marked = expand_markers(piece, all_defs)
                if marked is None:
                    raise ValueError("Complex marker")
                for atom in marked:
                    if matrix != Matrix() or atom.get("transform"):
                        if any(atom.get(k) not in (None, "none") for k in _EFFECTS):
                            raise ValueError("Transformed effect")
                        if "url(" in atom.get("fill", "") + atom.get("stroke", ""):
                            raise ValueError("User-space paint under a transform")
                    transformed = transform_element(atom, matrix)
                    output.append((svg_name(transformed.tag), serialize_svg(transformed)))
            for kind, tag in output:
                yield emit(kind, tag, sources, "native_candidate")
        except ValueError as error:
            yield fallback(node, inherited, matrix, sources, "expansion: " + str(error))

    yield from walk(root, {}, Matrix())
