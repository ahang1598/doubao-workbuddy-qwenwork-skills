"""主入口: 逐 tag 遍历 SVG, 输出 slide XML 字符串."""

from __future__ import annotations

import re
from os import PathLike, fsdecode
from pathlib import Path
from typing import List

from ._convert import (
    convert_circle,
    convert_ellipse,
    convert_line,
    convert_path,
    convert_polygon,
    convert_polyline,
    convert_rect,
    convert_text,
)
from ._svg_input import iter_atoms, parse_svg
from ._config import _CFG


def atomize_svg_to_slide(svg_path: str | PathLike, *, diagnostics=None) -> str:
    """把一张 SVG 原子化拆成 slide-native shape/line/text + N 个独立小 embed."""
    if diagnostics is not None and not isinstance(diagnostics, dict):
        raise TypeError("diagnostics must be a dict or None")
    if not isinstance(svg_path, Path):
        svg_path = Path(fsdecode(svg_path))
    source_text = svg_path.read_text(encoding="utf-8")
    if diagnostics is None and 'data-chart-lib="1"' in source_text[:600]:
        # Chart-library figures keep their lines/points in SVG; text and color blocks go native.
        from ..chart_split import split_chart_svg

        vb = [float(v) for v in re.search(r'viewBox="([^"]+)"', source_text).group(1).replace(",", " ").split()]
        sx, sy = _CFG["slide_w"] / _CFG["svg_w"], _CFG["slide_h"] / _CFG["svg_h"]
        return split_chart_svg(
            source_text,
            x=_CFG["slide_x0"] + vb[0] * sx,
            y=_CFG["slide_y0"] + vb[1] * sy,
            width=vb[2] * sx,
            height=vb[3] * sy,
        )
    root, defs = parse_svg(source_text)
    parts: List[str] = []
    metadata = {}
    if diagnostics is not None:
        diagnostics.clear()
        diagnostics.update(
            source=str(svg_path),
            objects=[],
            output_count=0,
            mapping={k: _CFG[k] for k in ("svg_w", "svg_h", "slide_x0", "slide_y0", "slide_w", "slide_h")},
        )
    viewport = [float(n) for n in root.get("viewBox", f"0 0 {_CFG['svg_w']} {_CFG['svg_h']}").replace(",", " ").split()]
    converters = {
        "rect": convert_rect,
        "line": convert_line,
        "text": convert_text,
        "path": convert_path,
        "polygon": convert_polygon,
        "polyline": convert_polyline,
        "circle": convert_circle,
        "ellipse": convert_ellipse,
    }
    for name, tag in iter_atoms(root, defs, observer=metadata.update if diagnostics is not None else None):
        font_policy = {} if diagnostics is not None and name == "text" else None
        if name == "_embed":
            viewbox = [
                float(n) for n in root.get("viewBox", f"0 0 {_CFG['svg_w']} {_CFG['svg_h']}").replace(",", " ").split()
            ]
            from ._effects import svg_embed

            parts.append(svg_embed(tag, defs, viewbox))
        elif font_policy is not None:
            parts.append(convert_text(tag, all_defs=defs, _font_policy=font_policy))
        else:
            parts.append(converters[name](tag, all_defs=defs))
        if diagnostics is not None:
            from ._diagnostics import record_atom

            record_atom(diagnostics, metadata, tag, defs, parts[-1], viewport, font_policy=font_policy)

    parts = [p for p in parts if p]
    # 不硬编码背景 rect: SVG 里的画布底色由 set_drop_background 控制
    inner = "".join(parts)
    return f'<slide xmlns="https://www.larkoffice.com/sml/2.0"><data>{inner}</data></slide>'
