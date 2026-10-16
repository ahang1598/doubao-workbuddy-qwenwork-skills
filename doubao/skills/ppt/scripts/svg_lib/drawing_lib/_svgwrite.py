"""svgwrite-style element methods on Drawing, so code written from svgwrite / SVG memory runs as is."""

from __future__ import annotations

from ._help import _drawing_api

_ANCHOR_WORDS = {
    "start": "start",
    "middle": "middle",
    "end": "end",
    "left": "start",
    "center": "middle",
    "right": "end",
}


def _position(name, at, center, insert, required=True):
    given = [k for k, v in (("at", at), ("center", center), ("insert", insert)) if v is not None]
    if len(given) > 1:
        raise TypeError(
            f"{name}(): pass one of at= / center= (centre) or insert= (svgwrite top-left/baseline), got {given}"
        )
    if not given and required:
        raise TypeError(
            f"{name}(): position missing — pass center=(x, y) or insert=(x, y) "
            f"(svgwrite: rect insert = top-left, text insert = baseline start)"
        )
    return ("insert", insert) if insert is not None else ("center", at if at is not None else center)


class SvgwriteAliases:
    # Registered in help as Drawing.<name> (see _help._drawing_api), like the rest of the canvas API.
    @_drawing_api(
        "shapes",
        purpose="svgwrite 写法的矩形：insert=(x, y) 左上角 + size=(w, h)；或 center=(x, y) 中心。",
        returns="Node",
        semantics=(
            "与 svgwrite 的 dwg.rect(insert, size, rx=, ry=) 同义，样式参数同 SVG 属性（fill/stroke/stroke_width…）。",
            "at=/center= 表示中心，insert= 表示左上角——全库同一规则；rect_at(insert=...) 也可以。",
        ),
        example='box = d.rect(insert=(40, 60), size=(200, 80), rx=8, fill="#F3EEF8", stroke="#5B1061")',
        rank=30,
    )
    def rect(self, insert=None, size=None, *, center=None, at=None, rx=0, ry=None, key=None, **style):
        if size is None:
            raise TypeError("rect(): size=(width, height) is required")
        w, h = size
        kind, p = _position("rect", at, center, insert)
        return self.rect_at(p, w, h, key=key, rx=rx, anchor="top_left" if kind == "insert" else "center", **style)

    @_drawing_api(
        "shapes",
        purpose="svgwrite 写法的圆：center=(x, y), r=。",
        returns="Node",
        semantics=("与 dwg.circle(center, r) 同义；等价于 ellipse_at(center, r)。",),
        example='n = d.circle(center=(300, 200), r=30, fill="#E9DDF2", stroke="#5B1061")',
        rank=31,
    )
    def circle(self, center=None, r=None, *, at=None, key=None, **style):
        if r is None:
            raise TypeError("circle(): r= is required")
        _, p = _position("circle", at, center, None)
        return self.ellipse_at(p, r, key=key, **style)

    @_drawing_api(
        "shapes",
        purpose="svgwrite 写法的椭圆：center=(x, y), r=(rx, ry)。",
        returns="Node",
        semantics=("与 dwg.ellipse(center, r=(rx, ry)) 同义；也接受 rx=, ry=。",),
        example='d.ellipse(center=(300, 200), r=(60, 30), fill="#E9DDF2")',
        rank=32,
    )
    def ellipse(self, center=None, r=None, *, at=None, rx=None, ry=None, key=None, **style):
        if r is not None:
            rx, ry = (r, r) if isinstance(r, (int, float)) else r
        if rx is None:
            raise TypeError("ellipse(): r=(rx, ry) or rx=/ry= is required")
        _, p = _position("ellipse", at, center, None)
        return self.ellipse_at(p, rx, ry, key=key, **style)

    @_drawing_api(
        "shapes",
        purpose="svgwrite 写法的文字：insert=(x, y) 基线起点（text_anchor 决定左/中/右）；或 center=(x, y) 文字框中心。",
        returns="Node",
        semantics=(
            "与 dwg.text(text, insert=(x, y), font_size=, text_anchor=) 同义；font_size 省略时为 16。",
            "insert 的 y 是基线（与 SVG 一致）；center 的 y 是文字框中心。多行用 \\n。",
        ),
        example='d.text("NF-κB 入核", insert=(420, 140), font_size=16, fill="#2A1A4A")',
        rank=33,
    )
    def text(self, text, insert=None, *, center=None, at=None, font_size=16, text_anchor="start", key=None, **style):
        kind, p = _position("text", at, center, insert)
        style.pop("anchor", None)
        if kind == "center":
            return self.text_at(p, text, font_size=font_size, key=key, **style)
        from ._geometry import label

        side = _ANCHOR_WORDS.get(text_anchor, "start")
        # label() puts the first baseline at y=font_size and the text-anchor point at x=0 in its own frame,
        # so placing its origin at (x, baseline - font_size) reproduces SVG's <text x y> exactly.
        geometry = label(text, font_size=font_size, text_anchor=side, **style)
        return self.add(key or self._auto("text"), geometry, at=(p[0], p[1] - font_size), own_anchor="origin")

    @_drawing_api(
        "shapes",
        purpose="svgwrite 写法的折线：points=[(x, y), ...]（画布坐标，不平移）。",
        returns="Node",
        semantics=('与 dwg.polyline(points) 同义；默认 fill="none"。两点也可以。',),
        example='d.polyline([(100, 300), (180, 260), (260, 300)], stroke="#5B1061", stroke_width=2)',
        rank=34,
    )
    def polyline(self, points, *, key=None, **style):
        pts = [tuple(p) for p in points]
        if len(pts) < 2:
            raise ValueError("polyline(): needs at least two points")
        style.setdefault("fill", "none")
        d = "M " + " L ".join(f"{x:g} {y:g}" for x, y in pts)
        return self.path_at(d, key=key or self._auto("polyline"), **style)

    @_drawing_api(
        "shapes",
        purpose="svgwrite 写法的多边形：points=[(x, y), ...]（画布坐标，不平移）。",
        returns="Node",
        semantics=("与 dwg.polygon(points) 同义；闭合路径，可填色。",),
        example='d.polygon([(100, 300), (180, 220), (260, 300)], fill="#F3EEF8", stroke="#5B1061")',
        rank=35,
    )
    def polygon(self, points, *, key=None, **style):
        pts = [tuple(p) for p in points]
        if len(pts) < 3:
            raise ValueError(
                "polygon(): needs at least three points; for two points use d.line(a, b) or d.polyline(points)"
            )
        d = "M " + " L ".join(f"{x:g} {y:g}" for x, y in pts) + " Z"
        return self.path_at(d, key=key or self._auto("polygon"), **style)

    @_drawing_api(
        "shapes",
        purpose='svgwrite 写法的路径：d="M ... "（画布坐标）。',
        returns="Node",
        semantics=("与 dwg.path(d=...) 同义；等价于 path_at(d)。",),
        example='d.path(d="M 100 300 C 200 200 300 400 400 300", stroke="#5B1061", fill="none")',
        rank=36,
    )
    def path(self, d=None, *, key=None, **style):
        if d is None:
            raise TypeError('path(): d="M ..." is required')
        return self.path_at(d, key=key, **style)

    @_drawing_api(
        "export",
        purpose="svgwrite 写法的导出：tostring() 返回 SVG 文本，saveas(path) 写文件；预览图用 preview(path)。",
        returns="str / Path",
        semantics=(
            "tostring() 等价于 to_svg()；saveas(path) 等价于 write(path)；to_image(path) / save_png(path) 等价于 preview(path)。",
            "放进幻灯片仍用 d.to_slide(x=, y=, width=) 交给 publish_slide。",
        ),
        example="svg_text = d.tostring()",
        rank=40,
    )
    def tostring(self):
        return self.to_svg()

    def saveas(self, filename, **_):
        return self.write(filename)

    def save(self, filename=None, **_):
        if filename is None:
            raise TypeError('save(): pass a path — d.save("p05.svg"); for a PNG preview use d.preview("p05.png")')
        return self.preview(filename) if str(filename).lower().endswith(".png") else self.write(filename)

    def to_image(self, path, **kw):
        return self.preview(path, **kw)

    save_png = to_image

    def get(self, key, default=None):
        """d.get("t") → the node with that key (dict-style lookup)."""
        return self.nodes.get(key, default)

    def __getitem__(self, key):
        return self.nodes[key]
