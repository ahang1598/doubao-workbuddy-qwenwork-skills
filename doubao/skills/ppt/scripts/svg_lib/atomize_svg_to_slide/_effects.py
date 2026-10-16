"""Shared fidelity gate and SVG fallback for all public geometry converters."""

from __future__ import annotations

from functools import wraps
import math
import xml.etree.ElementTree as ET
from ._bounds import svg_bounds, paint_bounds
from ._config import _CFG
from ._geometry import number
from ._resources import name, resource_closure


def _viewport(element):
    from ._geometry import numbers

    return tuple(numbers(element.get("data-atom-viewport", f"0 0 {_CFG['svg_w']} {_CFG['svg_h']}")))


def _serialize_fragment(root):
    # Slides' CustomSvgService requires a literal <svg xmlns="..."> child. ET otherwise emits ns0:svg when a
    # native-operation pass reserializes embeds.
    from ._svg_input import serialize_svg

    for svg in root.iter("{http://www.w3.org/2000/svg}svg"):
        svg.set("xmlns", "http://www.w3.org/2000/svg")
    return "".join(serialize_svg(node) for node in root)


def _native_paint(fragment, element, defs):
    from ._gradient import native_linear_gradient

    root = ET.fromstring("<data>" + fragment + "</data>")
    sx = _CFG["slide_w"] / _CFG["svg_w"]
    sy = _CFG["slide_h"] / _CFG["svg_h"]
    for shape in root:
        fill = shape.find("fill/fillColor")
        if fill is None or fill.get("color") in ("none", "rgba(0,0,0,0)"):
            continue
        box = (
            (float(shape.get("topLeftX")) - _CFG["slide_x0"]) / sx,
            (float(shape.get("topLeftY")) - _CFG["slide_y0"]) / sy,
            float(shape.get("width")) / sx,
            float(shape.get("height")) / sy,
        )
        color = native_linear_gradient(
            element.get("fill"),
            defs,
            number(element.get("fill-opacity", "1")),
            bbox=paint_bounds(element),
            viewport=_viewport(element),
            target_bbox=box,
            scale_xy=(sx, sy),
        )
        if color is None:
            raise ValueError("Cannot map gradient onto native bounds")
        fill.set("color", color)
        break  # Other filled atoms may be endpoint decorations, not the host fill.
    return _serialize_fragment(root)


def needs_svg(element, defs=""):
    from ._gradient import native_linear_gradient

    n = name(element)
    for key in ("filter", "clip-path", "mask", "mix-blend-mode", "isolation"):
        if element.get(key) not in (None, "none", "normal", "auto"):
            return True
    if element.get("fill-rule", "nonzero") != "nonzero":
        return True
    if element.get("vector-effect") not in (None, "none"):
        return True
    if element.get("stroke-dasharray") not in (None, "none", ""):
        if "url(" in element.get("fill", ""):
            return True
        from ._stroke import can_dash

        if not can_dash(element):
            return True
        if element.get("fill", "none") not in ("none", "transparent") and element.get("opacity") not in (
            None,
            "1",
            "1.0",
        ):
            return True
    if element.get("stroke-linecap") not in (None, "butt", "round", "square"):
        return True
    if element.get("stroke-linejoin") not in (None, "miter", "round", "bevel"):
        return True
    if element.get("stroke-miterlimit"):
        try:
            value = number(element.get("stroke-miterlimit"))
            if value != int(value):
                return True
        except ValueError:
            return True
    if element.get("style"):
        return True  # parsed/inlined by the main entry point
    if element.get("transform"):
        return True  # flattened by the main entry point
    fill = element.get("fill", "none")
    stroke = element.get("stroke", "none")
    if "url(" in stroke:
        return True
    if "url(" in fill:
        box = paint_bounds(element)
        if (
            n == "text"
            or box is None
            or native_linear_gradient(fill, defs, bbox=box, viewport=_viewport(element)) is None
        ):
            return True
    return False


def _matrix_text(m):
    from ._geometry import fmt

    if (m.a, m.b, m.c, m.d) == (1, 0, 0, 1):
        return f"translate({fmt(m.e)} {fmt(m.f)})"
    return m.svg()


def _push_transforms_to_leaves(source):
    """Move group transforms onto the leaf elements below them (render-identical)."""
    from ._geometry import Matrix, parse_transform

    try:
        root = ET.fromstring(f"<root>{source}</root>")
    except ET.ParseError:
        return source

    def walk(node, acc):
        for child in list(node):
            tag = child.tag.split("}")[-1]
            own = parse_transform(child.get("transform", "")) if child.get("transform") else Matrix()
            total = acc.then(own)
            user_space = any(child.get(k) not in (None, "none") for k in ("clip-path", "mask", "filter"))
            if tag == "g" and not user_space and not child.get("id"):
                # Opacity composites the group as a whole; it is unaffected by where the transform sits.
                child.attrib.pop("transform", None)
                walk(child, total)
            elif tag in ("defs", "title", "desc", "metadata", "style"):
                continue
            elif total == own:
                continue
            elif total != Matrix():
                child.set("transform", _matrix_text(total))
            else:
                child.attrib.pop("transform", None)

    walk(root, Matrix())
    return "".join(ET.tostring(c, encoding="unicode", short_empty_elements=True).replace(" />", "/>") for c in root)


def svg_embed(source, defs="", viewport=None):
    from ._scale import _sx, _sy, _sw, _sh

    viewport = viewport or (0, 0, _CFG["svg_w"], _CFG["svg_h"])
    used = resource_closure(source, defs)
    x, y, w, h = svg_bounds(source, used, viewport)
    vx, vy, vw, vh = viewport
    source = _push_transforms_to_leaves(source)
    # Keep the original viewport inside the tightly positioned outer viewport.
    # userSpaceOnUse percentages and viewport lengths must not change on crop.
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x:.12g} {y:.12g} {w:.12g} {h:.12g}">'
        f'<svg x="{vx:.12g}" y="{vy:.12g}" width="{vw:.12g}" height="{vh:.12g}" '
        f'viewBox="{vx:.12g} {vy:.12g} {vw:.12g} {vh:.12g}" overflow="visible">{used}{source}</svg></svg>'
    )
    return (
        f'<embed topLeftX="{_sx(x):.6f}" topLeftY="{_sy(y):.6f}" '
        f'width="{_sw(w):.6f}" height="{_sh(h):.6f}">{svg}</embed>'
    )


def _orient(fragment, element):
    angle = float(element.get("data-atom-angle", "0"))
    flip = element.get("data-atom-flip-y") == "true"
    if not fragment:
        return fragment
    # Native shapes rotate about their center; SVG text rotates about its anchor.
    from ._scale import _sx, _sy

    root = ET.fromstring("<data>" + fragment + "</data>")
    for border in root.findall(".//border"):
        if float(border.get("width", "0")) > 0:
            border.set("lineCap", element.get("stroke-linecap", "butt"))
            border.set("lineJoin", element.get("stroke-linejoin", "miter"))
            border.set("miterLimit", str(int(number(element.get("stroke-miterlimit", "4")))))
    for shape in root:
        if name(shape) != "shape" or (abs(angle) < 1e-10 and not flip):
            continue
        if name(element) == "text":
            x, y, w, h = (float(shape.get(k)) for k in ("topLeftX", "topLeftY", "width", "height"))
            ax, ay = _sx(number(element.get("x", "0"))), _sy(number(element.get("y", "0")))
            dx = x + w / 2 - ax
            dy = (y + h / 2 - ay) * (-1 if flip else 1)
            a = math.radians(angle)
            cx = ax + dx * math.cos(a) - dy * math.sin(a)
            cy = ay + dx * math.sin(a) + dy * math.cos(a)
            shape.set("topLeftX", f"{cx - w / 2:.6f}")
            shape.set("topLeftY", f"{cy - h / 2:.6f}")
        shape.set("rotation", f"{angle % 360:.12g}")
        if flip:
            shape.set("flipY", "true")
    return _serialize_fragment(root)


def faithful(converter):
    """Guard direct converter calls as well as atomizer-dispatched calls."""

    @wraps(converter)
    def wrapped(tag, all_defs="", *, _font_policy=None):
        run_converter = converter
        if _font_policy is not None:
            _font_policy.clear()

            def run_converter(value, definitions):
                return converter(value, definitions, _font_policy=_font_policy)

        element = ET.fromstring(tag)
        # Keep the longstanding own-center ellipse rotation available to direct
        # callers; all other transform handling belongs to the input walker.
        if name(element) == "ellipse" and element.get("transform"):
            from ._geometry import Matrix, transform_element

            try:
                element = transform_element(element, Matrix())
                tag = ET.tostring(element, encoding="unicode")
            except ValueError:
                pass
        if needs_svg(element, all_defs):
            return svg_embed(tag, all_defs)
        if "url(" in element.get("fill", ""):
            # Convert geometry with a placeholder, then map onto its actual native
            # bbox. Custom paths include padding that SVG paint bboxes do not.
            import copy

            plain = copy.deepcopy(element)
            plain.set("fill", "#000000")
            plain.set("fill-opacity", "1")
            result = run_converter(ET.tostring(plain, encoding="unicode"), all_defs)
            if "<embed" in result:
                return svg_embed(tag, all_defs)
            try:
                return _orient(_native_paint(result, element, all_defs), element)
            except ValueError:
                return svg_embed(tag, all_defs)
        if element.get("stroke-dasharray") not in (None, "none", ""):
            from ._stroke import native_dash

            return _orient(native_dash(element, all_defs, run_converter), element)
        return _orient(run_converter(tag, all_defs), element)

    return wrapped
