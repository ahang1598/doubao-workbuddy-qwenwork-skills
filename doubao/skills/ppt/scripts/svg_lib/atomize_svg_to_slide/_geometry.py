"""Similarity transforms, full path commands and stable native arc conversion."""

from __future__ import annotations

import copy
from dataclasses import dataclass
import math
import re
import xml.etree.ElementTree as ET

_NUMBER = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"
_PATH_TOKEN = re.compile(r"[A-Za-z]|" + _NUMBER)
# SVG grammar: arc flags are a single "0"/"1" and may be written without separators ("0 01300 150").
_ARC_FLAG = re.compile(r"[01]")
_PATH_SEPARATORS = " \t\r\n,"
_PATH_ARITY = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4, "T": 2, "A": 7, "Z": 0}


def path_tokens(value: str):
    """Tokenize path data per the SVG grammar, including compact arc flags."""
    tokens = []
    command = ""
    argument = 0
    pos = 0
    while True:
        while pos < len(value) and value[pos] in _PATH_SEPARATORS:
            pos += 1
        if pos >= len(value):
            return tokens
        in_arc_flag = command == "A" and argument % 7 in (3, 4)
        match = (_ARC_FLAG if in_arc_flag and not value[pos].isalpha() else _PATH_TOKEN).match(value, pos)
        if match is None:
            raise ValueError("Unsupported path syntax")
        token = match.group()
        if token.isalpha():
            if token.upper() not in _PATH_ARITY:
                raise ValueError("Unsupported path command")
            command, argument = token.upper(), 0
        else:
            argument += 1
        tokens.append(token)
        pos = match.end()


def number(value: str) -> float:
    value = value.strip()
    if value.endswith("px"):
        value = value[:-2]
    if not re.fullmatch(_NUMBER, value):
        raise ValueError("Expected one numeric coordinate")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("Non-finite coordinate")
    return result


def numbers(value: str):
    matches = list(re.finditer(_NUMBER, value))
    tail = re.sub(_NUMBER, "", value)
    if tail.strip(" ,\t\r\n"):
        raise ValueError("Unsupported coordinate list")
    return [number(m[0]) for m in matches]


def fmt(value: float) -> str:
    return f"{value:.12g}" if abs(value) > 1e-12 else "0"


@dataclass(frozen=True)
class Matrix:
    a: float = 1
    b: float = 0
    c: float = 0
    d: float = 1
    e: float = 0
    f: float = 0

    def point(self, x, y):
        return self.a * x + self.c * y + self.e, self.b * x + self.d * y + self.f

    def then(self, inner):
        """self @ inner: SVG transform lists multiply from left to right."""
        return Matrix(
            self.a * inner.a + self.c * inner.b,
            self.b * inner.a + self.d * inner.b,
            self.a * inner.c + self.c * inner.d,
            self.b * inner.c + self.d * inner.d,
            self.a * inner.e + self.c * inner.f + self.e,
            self.b * inner.e + self.d * inner.f + self.f,
        )

    @property
    def scale(self):
        return math.hypot(self.a, self.b)

    @property
    def determinant(self):
        return self.a * self.d - self.b * self.c

    @property
    def similarity(self):
        s2 = self.a * self.a + self.b * self.b
        return (
            s2 > 1e-20
            and abs(self.c * self.c + self.d * self.d - s2) < 1e-8 * max(1, s2)
            and abs(self.a * self.c + self.b * self.d) < 1e-8 * max(1, s2)
        )

    @property
    def angle(self):
        return math.degrees(math.atan2(self.b, self.a))

    def svg(self):
        return "matrix(" + " ".join(fmt(x) for x in (self.a, self.b, self.c, self.d, self.e, self.f)) + ")"


def translate(x, y=0):
    return Matrix(e=x, f=y)


def scale(s):
    return Matrix(a=s, d=s)


def rotate(degrees):
    a = math.radians(degrees)
    return Matrix(math.cos(a), math.sin(a), -math.sin(a), math.cos(a))


def parse_transform(value: str) -> Matrix:
    """Parse SVG's affine transform list; callers choose their supported subset."""
    result = Matrix()
    end = 0
    for match in re.finditer(r"([A-Za-z]+)\s*\(([^()]*)\)", value):
        if value[end : match.start()].strip(" ,\t\n\r"):
            raise ValueError("Unsupported transform syntax")
        name, args = match[1], numbers(match[2])
        if name == "translate" and len(args) in (1, 2):
            item = translate(args[0], args[1] if len(args) == 2 else 0)
        elif name == "scale" and len(args) in (1, 2):
            item = Matrix(a=args[0], d=args[-1])
        elif name == "rotate" and len(args) in (1, 3):
            item = rotate(args[0])
            if len(args) == 3:
                item = translate(*args[1:]).then(item).then(translate(-args[1], -args[2]))
        elif name == "matrix" and len(args) == 6:
            item = Matrix(*args)
        elif name in ("skewX", "skewY") and len(args) == 1:
            v = math.tan(math.radians(args[0]))
            item = Matrix(c=v) if name == "skewX" else Matrix(b=v)
        else:
            raise ValueError("Unsupported transform")
        result = result.then(item)
        end = match.end()
    if value[end:].strip():
        raise ValueError("Unsupported transform syntax")
    return result


def path_segments(value: str):
    """Return absolute full commands without sampling curves."""
    tokens = path_tokens(value)
    lengths = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4, "T": 2, "A": 7}
    i = 0
    cmd = None
    x = y = sx = sy = 0.0
    previous = ""
    control = None
    segments = []
    while i < len(tokens):
        if tokens[i].isalpha():
            cmd = tokens[i]
            i += 1
            if cmd.upper() == "Z":
                segments.append(("Z", []))
                x, y = sx, sy
                previous = "Z"
                control = None
                cmd = None
                continue
        if cmd is None or cmd.upper() not in lengths:
            raise ValueError("Unsupported path command")
        op = cmd.upper()
        n = lengths[op]
        if i + n > len(tokens) or any(t.isalpha() for t in tokens[i : i + n]):
            raise ValueError("Incomplete path command")
        v = [number(t) for t in tokens[i : i + n]]
        i += n
        relative = cmd.islower()
        if op == "H":
            v = [v[0] + (x if relative else 0), y]
            out = "L"
        elif op == "V":
            v = [x, v[0] + (y if relative else 0)]
            out = "L"
        elif op == "A":
            if v[3] not in (0, 1) or v[4] not in (0, 1):
                raise ValueError("Invalid arc flags")
            if relative:
                v[5] += x
                v[6] += y
            out = "A"
        else:
            if relative:
                v = [a + (x if k % 2 == 0 else y) for k, a in enumerate(v)]
            out = op
            if op == "S":
                c = (2 * x - control[0], 2 * y - control[1]) if previous in ("C", "S") else (x, y)
                v = [*c, *v]
                out = "C"
            elif op == "T":
                c = (2 * x - control[0], 2 * y - control[1]) if previous in ("Q", "T") else (x, y)
                v = [*c, *v]
                out = "Q"
        if out == "C":
            control = (v[2], v[3])
        elif out == "Q":
            control = (v[0], v[1])
        else:
            control = None
        x, y = v[-2:]
        if op == "M":
            sx, sy = x, y
            cmd = "l" if relative else "L"
        segments.append((out, v))
        previous = op
    return segments


def transform_element(element: ET.Element, matrix: Matrix) -> ET.Element:
    result = copy.deepcopy(element)
    name = result.tag.split("}")[-1]
    own = result.get("transform", "")
    # Compose orientation already introduced by marker expansion.
    if matrix != Matrix() and ("data-atom-angle" in result.attrib or "data-atom-flip-y" in result.attrib):
        if name == "rect":
            cx = number(result.get("x", "0")) + number(result.get("width", "0")) / 2
            cy = number(result.get("y", "0")) + number(result.get("height", "0")) / 2
        elif name == "text":
            cx = number(result.get("x", "0"))
            cy = number(result.get("y", "0"))
        else:
            cx = number(result.get("cx", "0"))
            cy = number(result.get("cy", "0"))
        orientation = rotate(number(result.attrib.pop("data-atom-angle", "0")))
        if result.attrib.pop("data-atom-flip-y", "false") == "true":
            orientation = orientation.then(Matrix(d=-1))
        matrix = matrix.then(translate(cx, cy)).then(orientation).then(translate(-cx, -cy))
    if own:
        matrix = matrix.then(parse_transform(own))
    if not matrix.similarity:
        raise ValueError("Nonuniform scaling or skew needs SVG compositing")
    if matrix == Matrix():
        if name == "path":
            result.set(
                "d",
                " ".join(
                    op + " " + " ".join(fmt(v) for v in values) for op, values in path_segments(result.get("d", ""))
                ),
            )
        result.attrib.pop("transform", None)
        return result
    result.attrib.pop("transform", None)
    s = matrix.scale
    reflected = matrix.determinant < 0

    def xy(kx, ky):
        px, py = matrix.point(number(result.get(kx, "0")), number(result.get(ky, "0")))
        result.set(kx, fmt(px))
        result.set(ky, fmt(py))

    def orientation():
        result.set("data-atom-angle", fmt(matrix.angle % 360))
        if reflected:
            result.set("data-atom-flip-y", "true")

    if (
        name == "rect"
        and result.get("stroke-dasharray") not in (None, "none")
        and (abs(matrix.angle) > 1e-9 or reflected)
    ):
        if number(result.get("rx", "0")) or number(result.get("ry", "0")):
            raise ValueError("Rounded dashed rect")
        x = number(result.get("x", "0"))
        y = number(result.get("y", "0"))
        w = number(result.get("width", "0"))
        h = number(result.get("height", "0"))
        pts = [matrix.point(a, b) for a, b in [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]]
        result.tag = "path"
        result.set("d", "M " + " L ".join(f"{fmt(a)} {fmt(b)}" for a, b in pts) + " Z")
        for key in ("x", "y", "width", "height", "rx", "ry"):
            result.attrib.pop(key, None)
    elif name == "rect":
        x = number(result.get("x", "0"))
        y = number(result.get("y", "0"))
        w = number(result.get("width", "0"))
        h = number(result.get("height", "0"))
        cx, cy = matrix.point(x + w / 2, y + h / 2)
        result.set("x", fmt(cx - w * s / 2))
        result.set("y", fmt(cy - h * s / 2))
        for key in ("width", "height", "rx", "ry"):
            if key in result.attrib:
                result.set(key, fmt(number(result.get(key)) * s))
        orientation()
    elif name in ("circle", "ellipse"):
        xy("cx", "cy")
        for key in ("r", "rx", "ry"):
            if key in result.attrib:
                result.set(key, fmt(number(result.get(key)) * s))
        if name == "ellipse":
            orientation()
    elif name == "line":
        xy("x1", "y1")
        xy("x2", "y2")
    elif name in ("polygon", "polyline"):
        nums = numbers(result.get("points", ""))
        if len(nums) % 2:
            raise ValueError("Invalid points")
        pts = [matrix.point(nums[k], nums[k + 1]) for k in range(0, len(nums), 2)]
        result.set("points", " ".join(f"{fmt(a)},{fmt(b)}" for a, b in pts))
    elif name == "path":
        parts = []
        for op, v in path_segments(result.get("d", "")):
            if op == "A":
                phi = math.radians(v[2])
                axis = math.degrees(
                    math.atan2(
                        matrix.b * math.cos(phi) + matrix.d * math.sin(phi),
                        matrix.a * math.cos(phi) + matrix.c * math.sin(phi),
                    )
                )
                v = [
                    abs(v[0] * s),
                    abs(v[1] * s),
                    axis,
                    v[3],
                    1 - v[4] if reflected else v[4],
                    *matrix.point(v[5], v[6]),
                ]
            else:
                v = [c for k in range(0, len(v), 2) for c in matrix.point(v[k], v[k + 1])]
            parts.append(op + " " + " ".join(fmt(a) for a in v))
        result.set("d", " ".join(parts))
    elif name == "text":
        if len(result):
            from ._rich_text import rich_runs

            runs = rich_runs(result)
            if runs is None:
                raise ValueError("Unsupported transformed text")
            for child in list(result):
                result.remove(child)
            result.text = None
            for text, style in runs:
                style = dict(style)
                style["font-size"] = fmt(number(style.get("font-size", result.get("font-size", "16"))) * s)
                if "letter-spacing" in style:
                    style["letter-spacing"] = fmt(number(style["letter-spacing"]) * s)
                ET.SubElement(result, "tspan", style).text = text
        orientation()
        xy("x", "y")
        result.set("font-size", fmt(number(result.get("font-size", "16")) * s))
        if "letter-spacing" in result.attrib and result.get("letter-spacing") != "normal":
            result.set("letter-spacing", fmt(number(result.get("letter-spacing")) * s))
    else:
        raise ValueError("Unsupported transformed geometry")
    if s != 1:
        if result.get("vector-effect") not in (None, "none"):
            raise ValueError("Vector effect")
        result.set("stroke-width", fmt(number(result.get("stroke-width", "1")) * s))
        if result.get("stroke-dashoffset") is not None:
            result.set("stroke-dashoffset", fmt(number(result.get("stroke-dashoffset")) * s))
        if result.get("stroke-dasharray") not in (None, "none"):
            result.set("stroke-dasharray", " ".join(fmt(n * s) for n in numbers(result.get("stroke-dasharray"))))
    return result


def arc_to_cubics(x0, y0, rx, ry, rotation, large, sweep, x1, y1):
    """Approximate an SVG endpoint arc with <=45-degree cubic segments."""
    rx, ry = abs(rx), abs(ry)
    if math.hypot(x1 - x0, y1 - y0) < 1e-12:
        return []
    if rx < 1e-12 or ry < 1e-12:
        return [("L", [x1, y1])]
    phi = math.radians(rotation)
    c, s = math.cos(phi), math.sin(phi)
    dx, dy = (x0 - x1) / 2, (y0 - y1) / 2
    xp, yp = c * dx + s * dy, -s * dx + c * dy
    adjust = max(1, math.hypot(xp / rx, yp / ry))
    rx *= adjust
    ry *= adjust
    denom = rx * rx * yp * yp + ry * ry * xp * xp
    q = math.sqrt(max(0, (rx * rx * ry * ry - denom) / denom)) if denom else 0
    if bool(large) == bool(sweep):
        q = -q
    cxp, cyp = q * rx * yp / ry, -q * ry * xp / rx
    cx, cy = c * cxp - s * cyp + (x0 + x1) / 2, s * cxp + c * cyp + (y0 + y1) / 2
    start = math.atan2((yp - cyp) / ry, (xp - cxp) / rx)
    end = math.atan2((-yp - cyp) / ry, (-xp - cxp) / rx)
    delta = end - start
    if sweep and delta < 0:
        delta += 2 * math.pi
    if not sweep and delta > 0:
        delta -= 2 * math.pi
    count = max(1, math.ceil(abs(delta) / (math.pi / 4)))
    step = delta / count
    result = []

    def point(t):
        return cx + rx * math.cos(t) * c - ry * math.sin(t) * s, cy + rx * math.cos(t) * s + ry * math.sin(t) * c

    def tangent(t):
        return -rx * math.sin(t) * c - ry * math.cos(t) * s, -rx * math.sin(t) * s + ry * math.cos(t) * c

    for i in range(count):
        a = start + i * step
        b = a + step
        k = 4 / 3 * math.tan(step / 4)
        p = point(a)
        v = tangent(a)
        q = point(b)
        w = tangent(b)
        result.append(("C", [p[0] + k * v[0], p[1] + k * v[1], q[0] - k * w[0], q[1] - k * w[1], *q]))
    result[-1][1][-2:] = [x1, y1]
    return result
