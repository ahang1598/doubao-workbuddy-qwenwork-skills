"""Connector end markers whose geometry always converts to native Slides shapes."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from ..atomize_svg_to_slide._geometry import fmt
from ._help import _drawing_api


# Filled shapes inside a 0..10 viewBox; reference points sit where the line ends.
_KINDS = {
    "arrow": ("M0 0 L10 5 L0 10 Z", 9, 5, "auto"),
    "open_arrow": ("M0 0 L10 5 L0 10 L3 5 Z", 9, 5, "auto"),
    "inhibit": ("M3.5 0 L6.5 0 L6.5 10 L3.5 10 Z", 6.5, 5, "auto"),
    "dot": (None, 5, 5, "auto"),
    "diamond": ("M0 5 L5 0 L10 5 L5 10 Z", 5, 5, "auto"),
}
_ALIASES = {
    "activate": "arrow",
    "activation": "arrow",
    "tbar": "inhibit",
    "inhibition": "inhibit",
    "bind": "dot",
    "binding": "dot",
    "circle": "dot",
}


@_drawing_api(
    "connect",
    purpose="生成连线端点 marker（激活箭头、抑制横杠、结合圆点、菱形），转换后为原生端点形状。",
    returns="marker 元素（交给 Drawing.add_defs）",
    semantics=(
        "kind 为 arrow / open_arrow / inhibit / dot / diamond；也接受 activate、tbar、binding 等别名。",
        "size 为端点在画布上的大小（源 SVG 单位，不随线宽缩放）；color 为填充色，与连线颜色一致时传同一值。",
        "id 默认为 kind；同一张图里不同颜色的同类端点要给不同 id。"
        '用 drawing.add_defs(marker(...)) 注册后，在 connect 里写 marker_end="url(#id)"（或 marker_start）。',
        "几何都是闭合填充形状并留在 marker 视口内，atomize 后成为独立原生 shape，不会退化为 embed。",
    ),
    example='drawing.add_defs(marker("inhibit", color=line_color, id="inh"))\n'
    'drawing.connect(name, a.port("right"), b.port("left"), stroke=line_color, marker_end="url(#inh)")',
    limits=("不支持描边端点或自定义复杂图形；需要特殊端点时手写 marker 并预期可能保留为 SVG。",),
    rank=5,
)
def marker(kind="arrow", *, color="#333333", size=8, id=None):
    key = _ALIASES.get(kind, kind)
    if key not in _KINDS:
        raise ValueError(f"Unknown marker kind {kind!r}; use one of {sorted(_KINDS)}")
    if not isinstance(size, (int, float)) or size <= 0:
        raise ValueError("marker size must be positive")
    d, ref_x, ref_y, orient = _KINDS[key]
    element = ET.Element(
        "marker",
        {
            "id": id or key,
            "viewBox": "0 0 10 10",
            "refX": fmt(ref_x),
            "refY": fmt(ref_y),
            "markerWidth": fmt(size),
            "markerHeight": fmt(size),
            "markerUnits": "userSpaceOnUse",
            "orient": orient,
        },
    )
    from ._geometry import _attrs

    paint = _attrs({"fill": color})
    if d is None:
        ET.SubElement(element, "circle", {"cx": "5", "cy": "5", "r": "4", **paint})
    else:
        ET.SubElement(element, "path", {"d": d, **paint})
    return element
