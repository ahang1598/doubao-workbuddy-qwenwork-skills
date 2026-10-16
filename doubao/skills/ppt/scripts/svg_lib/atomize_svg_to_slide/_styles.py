"""Bounded static SVG CSS cascade, not a general CSS engine or sanitizer."""

from __future__ import annotations

import io
import math
import re
import xml.etree.ElementTree as ET

SVG_NS = "http://www.w3.org/2000/svg"
_WS = " \t\r\n\f"
_IDENT = r"(?:--[-_A-Za-z0-9\u0080-\U0010ffff]*|-?[_A-Za-z\u0080-\U0010ffff][-_A-Za-z0-9\u0080-\U0010ffff]*)"
_NUMBER = r"[-+]?(?:[0-9]+\.?[0-9]*|\.[0-9]+)(?:[eE][-+]?[0-9]+)?"
# Fixed CSS named colors (sRGB). Kept local so SVG authoring needs no color library.
_COLORS = {
    "aliceblue": "#f0f8ff",
    "antiquewhite": "#faebd7",
    "aqua": "#00ffff",
    "aquamarine": "#7fffd4",
    "azure": "#f0ffff",
    "beige": "#f5f5dc",
    "bisque": "#ffe4c4",
    "black": "#000000",
    "blanchedalmond": "#ffebcd",
    "blue": "#0000ff",
    "blueviolet": "#8a2be2",
    "brown": "#a52a2a",
    "burlywood": "#deb887",
    "cadetblue": "#5f9ea0",
    "chartreuse": "#7fff00",
    "chocolate": "#d2691e",
    "coral": "#ff7f50",
    "cornflowerblue": "#6495ed",
    "cornsilk": "#fff8dc",
    "crimson": "#dc143c",
    "cyan": "#00ffff",
    "darkblue": "#00008b",
    "darkcyan": "#008b8b",
    "darkgoldenrod": "#b8860b",
    "darkgray": "#a9a9a9",
    "darkgreen": "#006400",
    "darkgrey": "#a9a9a9",
    "darkkhaki": "#bdb76b",
    "darkmagenta": "#8b008b",
    "darkolivegreen": "#556b2f",
    "darkorange": "#ff8c00",
    "darkorchid": "#9932cc",
    "darkred": "#8b0000",
    "darksalmon": "#e9967a",
    "darkseagreen": "#8fbc8f",
    "darkslateblue": "#483d8b",
    "darkslategray": "#2f4f4f",
    "darkslategrey": "#2f4f4f",
    "darkturquoise": "#00ced1",
    "darkviolet": "#9400d3",
    "deeppink": "#ff1493",
    "deepskyblue": "#00bfff",
    "dimgray": "#696969",
    "dimgrey": "#696969",
    "dodgerblue": "#1e90ff",
    "firebrick": "#b22222",
    "floralwhite": "#fffaf0",
    "forestgreen": "#228b22",
    "fuchsia": "#ff00ff",
    "gainsboro": "#dcdcdc",
    "ghostwhite": "#f8f8ff",
    "gold": "#ffd700",
    "goldenrod": "#daa520",
    "gray": "#808080",
    "green": "#008000",
    "greenyellow": "#adff2f",
    "grey": "#808080",
    "honeydew": "#f0fff0",
    "hotpink": "#ff69b4",
    "indianred": "#cd5c5c",
    "indigo": "#4b0082",
    "ivory": "#fffff0",
    "khaki": "#f0e68c",
    "lavender": "#e6e6fa",
    "lavenderblush": "#fff0f5",
    "lawngreen": "#7cfc00",
    "lemonchiffon": "#fffacd",
    "lightblue": "#add8e6",
    "lightcoral": "#f08080",
    "lightcyan": "#e0ffff",
    "lightgoldenrodyellow": "#fafad2",
    "lightgray": "#d3d3d3",
    "lightgreen": "#90ee90",
    "lightgrey": "#d3d3d3",
    "lightpink": "#ffb6c1",
    "lightsalmon": "#ffa07a",
    "lightseagreen": "#20b2aa",
    "lightskyblue": "#87cefa",
    "lightslategray": "#778899",
    "lightslategrey": "#778899",
    "lightsteelblue": "#b0c4de",
    "lightyellow": "#ffffe0",
    "lime": "#00ff00",
    "limegreen": "#32cd32",
    "linen": "#faf0e6",
    "magenta": "#ff00ff",
    "maroon": "#800000",
    "mediumaquamarine": "#66cdaa",
    "mediumblue": "#0000cd",
    "mediumorchid": "#ba55d3",
    "mediumpurple": "#9370db",
    "mediumseagreen": "#3cb371",
    "mediumslateblue": "#7b68ee",
    "mediumspringgreen": "#00fa9a",
    "mediumturquoise": "#48d1cc",
    "mediumvioletred": "#c71585",
    "midnightblue": "#191970",
    "mintcream": "#f5fffa",
    "mistyrose": "#ffe4e1",
    "moccasin": "#ffe4b5",
    "navajowhite": "#ffdead",
    "navy": "#000080",
    "oldlace": "#fdf5e6",
    "olive": "#808000",
    "olivedrab": "#6b8e23",
    "orange": "#ffa500",
    "orangered": "#ff4500",
    "orchid": "#da70d6",
    "palegoldenrod": "#eee8aa",
    "palegreen": "#98fb98",
    "paleturquoise": "#afeeee",
    "palevioletred": "#db7093",
    "papayawhip": "#ffefd5",
    "peachpuff": "#ffdab9",
    "peru": "#cd853f",
    "pink": "#ffc0cb",
    "plum": "#dda0dd",
    "powderblue": "#b0e0e6",
    "purple": "#800080",
    "rebeccapurple": "#663399",
    "red": "#ff0000",
    "rosybrown": "#bc8f8f",
    "royalblue": "#4169e1",
    "saddlebrown": "#8b4513",
    "salmon": "#fa8072",
    "sandybrown": "#f4a460",
    "seagreen": "#2e8b57",
    "seashell": "#fff5ee",
    "sienna": "#a0522d",
    "silver": "#c0c0c0",
    "skyblue": "#87ceeb",
    "slateblue": "#6a5acd",
    "slategray": "#708090",
    "slategrey": "#708090",
    "snow": "#fffafa",
    "springgreen": "#00ff7f",
    "steelblue": "#4682b4",
    "tan": "#d2b48c",
    "teal": "#008080",
    "thistle": "#d8bfd8",
    "tomato": "#ff6347",
    "turquoise": "#40e0d0",
    "violet": "#ee82ee",
    "wheat": "#f5deb3",
    "white": "#ffffff",
    "whitesmoke": "#f5f5f5",
    "yellow": "#ffff00",
    "yellowgreen": "#9acd32",
}
_ENUMS = {
    "fill-rule": {"nonzero", "evenodd"},
    "stroke-linecap": {"butt", "round", "square"},
    "stroke-linejoin": {"miter", "round", "bevel"},
    "font-style": {"normal", "italic"},
    "text-anchor": {"start", "middle", "end"},
    "display": {"inline", "none"},
    "visibility": {"visible", "hidden", "collapse"},
    "color-interpolation": {"auto", "sRGB", "linearRGB"},
    "dominant-baseline": {
        "auto",
        "use-script",
        "no-change",
        "reset-size",
        "ideographic",
        "alphabetic",
        "hanging",
        "mathematical",
        "central",
        "middle",
        "text-after-edge",
        "text-before-edge",
    },
    "alignment-baseline": {
        "auto",
        "baseline",
        "before-edge",
        "text-before-edge",
        "middle",
        "central",
        "after-edge",
        "text-after-edge",
        "ideographic",
        "alphabetic",
        "hanging",
        "mathematical",
    },
    "writing-mode": {"lr-tb", "rl-tb", "tb-rl", "lr", "rl", "tb", "horizontal-tb", "vertical-rl", "vertical-lr"},
    "direction": {"ltr", "rtl"},
    "unicode-bidi": {"normal", "embed", "bidi-override", "isolate", "isolate-override", "plaintext"},
}
_ALPHA = {"opacity", "fill-opacity", "stroke-opacity", "stop-opacity"}
_LENGTH = {"font-size", "stroke-width", "stroke-dashoffset", "letter-spacing", "baseline-shift"}
_URL = {"filter", "clip-path", "mask", "marker-start", "marker-mid", "marker-end"}
_PAINT = {"fill", "stroke", "color", "stop-color"}
_ALLOWED = (
    set(_ENUMS)
    | _ALPHA
    | _LENGTH
    | _URL
    | _PAINT
    | {"font-family", "font-weight", "stroke-dasharray", "stroke-miterlimit"}
)


def _name(node):
    if node.tag.startswith("{"):
        namespace, local = node.tag[1:].split("}", 1)
        return local if namespace == SVG_NS else ""
    return node.tag


def _error(message):
    raise ValueError("Unsupported static SVG CSS: " + message)


def _without_comments(text):
    output = []
    i = 0
    quote = None
    while i < len(text):
        char = text[i]
        if quote:
            output.append(char)
            if char == "\\":
                i += 1
                if i >= len(text):
                    _error("unterminated string escape")
                output.append(text[i])
            elif char == quote:
                quote = None
            elif char in "\r\n":
                _error("newline in a quoted string")
        elif char in "\"'":
            quote = char
            output.append(char)
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            if end < 0:
                _error("unterminated comment")
            output.append(" ")
            i = end + 1
        else:
            output.append(char)
        i += 1
    if quote:
        _error("unterminated quoted string")
    return "".join(output)


def _delimiters(text, wanted):
    """Locate syntax separators, never punctuation inside strings/functions."""
    found = []
    quote = None
    depth = 0
    i = 0
    while i < len(text):
        char = text[i]
        if quote:
            if char == "\\":
                i += 1
                if i >= len(text):
                    _error("unterminated string escape")
            elif char == quote:
                quote = None
        elif char in "\"'":
            quote = char
        elif char == "\\":
            _error("CSS escapes outside strings are not supported")
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth < 0:
                _error("unbalanced parentheses")
        elif depth == 0 and char in wanted:
            found.append((i, char))
        i += 1
    if quote or depth:
        _error("unterminated string or function")
    return found


def _split(text, delimiter):
    start = 0
    result = []
    for position, _ in _delimiters(text, delimiter):
        result.append(text[start:position])
        start = position + 1
    result.append(text[start:])
    return result


def _selector(text):
    text = text.strip(_WS)
    if len(text) > 4096:
        _error("selector exceeds 4096 characters")
    match = re.match(_IDENT, text)
    tag = match[0] if match else None
    position = match.end() if match else 0
    classes, ids = [], []
    while position < len(text):
        match = re.match(r"([.#])(" + _IDENT + r")", text[position:])
        if not match:
            _error(f"selector {text!r}; only tag/.class/#id compounds are supported")
        (classes if match[1] == "." else ids).append(match[2])
        position += match.end()
    if not tag and not classes and not ids:
        _error("empty selector")
    return tag, classes, ids, (len(ids), len(classes), int(tag is not None))


def _local_url(value):
    match = re.fullmatch(r'url\(\s*(?:"([^"\\]*)"|\'([^\'\\]*)\'|([^\s"\'()]+))\s*\)', value, re.I | re.ASCII)
    target = next((x for x in match.groups() if x is not None), "") if match else ""
    if not re.fullmatch(r'#[^\s\)\(\'";%\\{}]+', target):
        _error(f"URL {value!r}; only simple document-local #id resources are supported")
    return "url(" + target + ")"


def _value(prop, value):
    if prop not in _ALLOWED:
        _error(f"property {prop!r} cannot be mapped to a supported SVG attribute")
    if value.lower() == "inherit":
        return "inherit"
    if prop in _PAINT:
        if value.lower() == "currentcolor" and prop != "color":
            return "currentColor"
        if prop in {"fill", "stroke"} and value.lower() in {"none", "context-fill", "context-stroke"}:
            return value.lower()
        if value.lower() == "transparent":
            return "#00000000"
        if value.lower() in _COLORS:
            return _COLORS[value.lower()]
        if re.fullmatch(r"#[0-9a-fA-F]{3,4}|#[0-9a-fA-F]{6}|#[0-9a-fA-F]{8}", value):
            return value
        if prop in {"fill", "stroke"} and value.lower().startswith("url("):
            return _local_url(value)
        match = re.fullmatch(
            r"(rgb|rgba)\(\s*([0-9]+)\s*,\s*([0-9]+)\s*,\s*([0-9]+)\s*(?:,\s*(" + _NUMBER + r")\s*)?\)",
            value,
            re.I | re.ASCII,
        )
        if match and ((match[1].lower() == "rgba") == (match[5] is not None)):
            if max(int(match[i]) for i in (2, 3, 4)) <= 255 and (match[5] is None or 0 <= float(match[5]) <= 1):
                return value.lower()
    elif prop in _URL:
        return "none" if value.lower() == "none" else _local_url(value)
    elif prop in _ENUMS:
        for keyword in _ENUMS[prop]:
            if value.lower() == keyword.lower():
                return keyword
    elif prop == "font-family":
        families = _split(value, ",")
        valid = True
        for family in families:
            family = family.strip(_WS)
            if re.fullmatch(r'"[^"\\]+"|\'[^\'\\]+\'', family):
                continue
            if not re.fullmatch(_IDENT + r"(?:\s+" + _IDENT + r")*", family, re.ASCII):
                valid = False
            if any(
                word.lower() in {"inherit", "initial", "unset", "revert", "revert-layer", "default"}
                for word in family.split()
            ):
                valid = False
        if valid:
            return value
    elif prop == "font-weight":
        if value.lower() in {"normal", "bold"} or re.fullmatch(r"[1-9]00", value):
            return value.lower()
    elif prop == "stroke-dasharray":
        if value == "none":
            return value
        if re.fullmatch(_NUMBER + r"(?:(?:\s*,\s*|\s+)" + _NUMBER + r")*", value, re.ASCII):
            values = [float(x) for x in re.findall(_NUMBER, value)]
            if all(math.isfinite(x) and x >= 0 for x in values):
                return value
    else:
        if prop == "letter-spacing" and value == "normal":
            return value
        if prop == "baseline-shift" and value in {"baseline", "sub", "super"}:
            return value
        match = re.fullmatch("(" + _NUMBER + r")(px)?", value)
        if match:
            number = float(match[1])
            unit = match[2]
            if math.isfinite(number):
                if prop in _ALPHA and unit is None and 0 <= number <= 1:
                    return value
                if prop == "stroke-miterlimit" and unit is None and number >= 1:
                    return value
                if prop in _LENGTH and (prop != "font-size" or number > 0) and (prop != "stroke-width" or number >= 0):
                    return value
    _error(f"value {value!r} for {prop!r}")


def _declarations(text):
    declarations = []
    for declaration in _split(_without_comments(text), ";"):
        if not declaration.strip(_WS):
            continue
        positions = _delimiters(declaration, ":")
        if len(positions) != 1:
            _error(f"malformed declaration {declaration.strip(_WS)!r}")
        position = positions[0][0]
        prop, value = declaration[:position].strip(_WS).lower(), declaration[position + 1 :].strip(_WS)
        important = False
        bangs = _delimiters(value, "!")
        if bangs:
            if len(bangs) != 1 or not re.fullmatch(r"!\s*important\s*", value[bangs[0][0] :], re.I | re.ASCII):
                _error(f"malformed !important in {declaration!r}")
            important = True
            value = value[: bangs[0][0]].rstrip(_WS)
        declarations.append((prop, _value(prop, value), important))
    return declarations


def _rules(text):
    text = _without_comments(text)
    braces = _delimiters(text, "{}")
    cursor = 0
    rules = []
    if len(braces) % 2:
        _error("unbalanced stylesheet braces")
    for i in range(0, len(braces), 2):
        (start, opening), (end, closing) = braces[i : i + 2]
        if opening != "{" or closing != "}":
            _error("nested rules and @ rules are not supported")
        selector_text = text[cursor:start]
        if "@" in selector_text:
            _error("@ rules and external stylesheets are not supported")
        selectors = [_selector(item) for item in _split(selector_text, ",")]
        declarations = _declarations(text[start + 1 : end])
        rules.append((selectors, declarations))
        cursor = end + 1
    if text[cursor:].strip(_WS):
        _error("trailing stylesheet syntax or @ rule")
    return rules


def flatten_styles(root, source=""):
    """Flatten the supported cascade in place after validating the whole input."""
    if "xml-stylesheet" in source:
        for _, instruction in ET.iterparse(io.StringIO(source), events=("pi",)):
            if (instruction.text or "").split(None, 1)[0] == "xml-stylesheet":
                _error("external xml-stylesheet processing instructions are not supported")
    nodes = list(root.iter())
    for node in nodes:
        if node.tag.split("}")[-1] == "link":
            _error("external/link stylesheets are not supported")
    sheets = [node for node in nodes if _name(node) == "style"]
    if not sheets and not any("class" in node.attrib for node in nodes):
        return root
    if sum(len(sheet.text or "") for sheet in sheets) + sum(len(node.get("style", "")) for node in nodes) > 1_000_000:
        _error("stylesheet and inline CSS exceed 1000000 characters")
    for node in nodes:
        for key, value in node.attrib.items():
            if key.split("}")[-1] == "href" and not value.startswith("#"):
                _error("external resource href references are not supported")
    rules = []
    for sheet in sheets:
        if len(sheet) or set(sheet.attrib) - {
            "type",
            "media",
            "id",
            "class",
            "style",
            "{http://www.w3.org/XML/1998/namespace}space",
        }:
            _error("unsupported style element content or attributes")
        if sheet.get("type", "text/css").strip(_WS).lower() != "text/css" or sheet.get("media", "all").strip(
            _WS
        ) not in ("", "all"):
            _error("only unconditional text/css style elements are supported")
        rules.extend(_rules(sheet.text or ""))
    if sum(len(selectors) for selectors, _ in rules) * len(nodes) > 2_000_000:
        _error("stylesheet matching exceeds the bounded 2000000 selector/node pairs")
    resolved = []
    for node in nodes:
        # Presentation attributes precede author CSS with specificity zero.
        winners = {key: ((0, 0, 0, 0, 0, -1), value) for key, value in node.attrib.items() if key in _ALLOWED}
        classes = set(re.split(r"[ \t\r\n\f]+", node.get("class", ""))) - {""}
        order = 0
        for selectors, declarations in rules:
            matches = [
                specificity
                for tag, required, ids, specificity in selectors
                if (tag is None or tag == _name(node))
                and all(c in classes for c in required)
                and all(identifier == node.get("id") for identifier in ids)
            ]
            for prop, value, important in declarations:
                if matches:
                    priority = (int(important), 0, *max(matches), order)
                    if prop not in winners or priority >= winners[prop][0]:
                        winners[prop] = priority, value
                order += 1
        for prop, value, important in _declarations(node.get("style", "")):
            priority = (int(important), 1, 0, 0, 0, order)
            if prop not in winners or priority >= winners[prop][0]:
                winners[prop] = priority, value
            order += 1
        attributes = {key: value for key, (_, value) in winners.items()}
        # Presentation attributes can remain winners too. They must fit this
        # path's value subset; inherited defaults remain the walker's concern.
        for key in attributes:
            attributes[key] = _value(key, attributes[key].strip(_WS))
        resolved.append((node, attributes))
    for node, attributes in resolved:
        node.attrib.update(attributes)
        node.attrib.pop("style", None)
        node.attrib.pop("class", None)
    for parent in nodes:
        for child in list(parent):
            if child in sheets:
                index = list(parent).index(child)
                if child.tail:
                    if index:
                        sibling = parent[index - 1]
                        sibling.tail = (sibling.tail or "") + child.tail
                    else:
                        parent.text = (parent.text or "") + child.tail
                parent.remove(child)
    return root
