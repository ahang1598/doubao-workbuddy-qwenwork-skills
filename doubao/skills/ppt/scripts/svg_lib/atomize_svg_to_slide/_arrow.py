"""SVG stroke / marker / dashArray → slide native line / connector XML."""

from __future__ import annotations

import math
import re
from typing import List, Tuple

from ._config import _CFG
from ._paint import (
    _apply_opacity,
    _format_num,
    _get_attr,
)
from ._scale import s2l_x, s2l_y


# stroke / dash / marker 属性解析


def _svg_dash_to_sml(dash: str, line_cap: str = "") -> str:
    """SVG stroke-dasharray → Slides dashArray 枚举 (最接近映射)."""
    raw = (dash or "").strip().lower()
    if not raw or raw == "none":
        return "solid"
    nums = []
    for part in re.split(r"[\s,]+", raw):
        if not part:
            continue
        try:
            nums.append(float(part))
        except ValueError:
            return "dash"
    if not nums:
        return "solid"
    if len(nums) >= 4:
        return "dash-dot"
    dash_len = nums[0]
    if dash_len <= 1.5:
        return "round-dot" if line_cap == "round" else "dot"
    if dash_len >= 8:
        return "long-dash"
    return "dash"


def _line_cap(tag: str) -> str:
    value = (_get_attr(tag, "stroke-linecap") or "").strip().lower()
    return value if value in {"butt", "square", "round"} else ""


def _line_join(tag: str) -> str:
    value = (_get_attr(tag, "stroke-linejoin") or "").strip().lower()
    return value if value in {"round", "bevel", "miter"} else ""


def _marker_kind(marker_ref: str) -> str:
    """从 marker url(#...) 识别端点装饰类型 (tbar / diamond / circle / triangle)."""
    value = (marker_ref or "").strip().lower()
    if not value or value == "none":
        return ""
    m = re.search(r"url\(#([^)]+)\)", value)
    marker_id = (m.group(1) if m else value).lower()
    if "tbar" in marker_id or marker_id.endswith("bar"):
        return "tbar"
    if "diamond" in marker_id:
        return "solid-diamond"
    if "circle" in marker_id:
        return "solid-circle"
    return "solid-triangle"


def _arrow_scale(stroke_w: float) -> str:
    width = _stroke_border_width(stroke_w)
    if width >= 3:
        return "lg"
    if width >= 2:
        return "med"
    return "sm"


def _stroke_scale_ratio() -> float:
    """SVG stroke 按 min(x_scale, y_scale) 缩放, 保持 aspect (线不会一边粗一边细)."""
    sx = _CFG["slide_w"] / max(1.0, _CFG["svg_w"])
    sy = _CFG["slide_h"] / max(1.0, _CFG["svg_h"])
    return min(sx, sy)


def _stroke_border_width(stroke_w: float) -> int:
    if stroke_w <= 0:
        return 0
    return int(max(1, round(stroke_w * _stroke_scale_ratio())))


def _border_attrs_from_svg(tag: str) -> str:
    dash = _svg_dash_to_sml(_get_attr(tag, "stroke-dasharray") or "", _line_cap(tag))
    line_cap = _line_cap(tag)
    line_join = _line_join(tag)
    attrs = []
    if dash != "solid":
        attrs.append(f'dashArray="{dash}"')
    if line_cap:
        attrs.append(f'lineCap="{line_cap}"')
    if line_join:
        attrs.append(f'lineJoin="{line_join}"')
    miter = _get_attr(tag, "stroke-miterlimit")
    if miter is not None:
        attrs.append(f'miterLimit="{int(float(miter))}"')
    return (" " + " ".join(attrs)) if attrs else ""


def _native_arrow_xml(marker_kind: str, tag_name: str, stroke_w: float) -> str:
    if not marker_kind or marker_kind == "tbar":
        return ""
    scale = _arrow_scale(stroke_w)
    return f'<{tag_name} type="{marker_kind}" widthScale="{scale}" heightScale="{scale}"/>'


def _endpoint_decoration_xml(
    x_tip: float,
    y_tip: float,
    x_ref: float,
    y_ref: float,
    *,
    marker_kind: str,
    stroke: str,
    stroke_w: float,
    opacity: float,
) -> str:
    """自定义 path 端点的 marker 装饰 fallback (custom shape 上 native arrow 不生效, 手绘代替)."""
    if not marker_kind:
        return ""

    dx = x_tip - x_ref
    dy = y_tip - y_ref
    length = math.hypot(dx, dy)
    if length <= 0.001:
        return ""
    ux = dx / length
    uy = dy / length
    px = -uy
    py = ux
    if marker_kind == "tbar":
        half = max(3.0, stroke_w * 2.2)
        return _line_xml(
            x_tip + px * half,
            y_tip + py * half,
            x_tip - px * half,
            y_tip - py * half,
            stroke,
            stroke_w,
            opacity,
            line_cap="butt",
        )

    size = max(6.0, min(14.0, stroke_w * 4.5))
    half_w = size * 0.46
    bx = x_tip - ux * size
    by = y_tip - uy * size
    points = [
        (x_tip, y_tip),
        (bx + px * half_w, by + py * half_w),
        (bx - px * half_w, by - py * half_w),
    ]
    # 这里 import 放函数体内避免 _path 循环依赖 (custom shape 是 path 模块的功能)
    from ._path import _custom_shape_from_points

    return _custom_shape_from_points(
        points,
        fill=stroke,
        stroke="none",
        stroke_w=0,
        opacity=opacity,
        close=True,
    )


# line / curved connector / stroked points → slide XML


def _line_xml(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    stroke: str,
    stroke_w: float,
    opacity: float = 1,
    *,
    dash_array: str = "solid",
    marker_start: str = "",
    marker_end: str = "",
    line_cap: str = "",
    line_join: str = "",
) -> str:
    """按当前 SVG→slide 映射输出一条 slide-native line."""
    color = _apply_opacity(stroke, opacity)
    border_attrs = []
    if dash_array and dash_array != "solid":
        border_attrs.append(f'dashArray="{dash_array}"')
    if line_cap:
        border_attrs.append(f'lineCap="{line_cap}"')
    if line_join:
        border_attrs.append(f'lineJoin="{line_join}"')
    border_attr_text = (" " + " ".join(border_attrs)) if border_attrs else ""
    start_arrow = _native_arrow_xml(marker_start, "startArrow", stroke_w)
    end_arrow = _native_arrow_xml(marker_end, "endArrow", stroke_w)

    return (
        f'<line startX="{s2l_x(x1)}" startY="{s2l_y(y1)}" '
        f'endX="{s2l_x(x2)}" endY="{s2l_y(y2)}">'
        f'<border color="{color}" width="{_stroke_border_width(stroke_w)}"{border_attr_text}/>'
        f"{start_arrow}{end_arrow}"
        f"</line>"
    )


def _curved_connector_xml(
    x1: float, y1: float, x2: float, y2: float, tag: str, stroke: str, stroke_w: float, opacity: float = 1
) -> str:
    """开放曲线 (Bezier / arc 两点连接) → slide 原生 curved-connector."""
    sx1, sy1 = s2l_x(x1), s2l_y(y1)
    sx2, sy2 = s2l_x(x2), s2l_y(y2)
    if abs(sx1 - sx2) <= 0.001 and abs(sy1 - sy2) <= 0.001:
        return ""
    # 起终点共线时 curved-connector 无法表达原 SVG 的弧高，退回单条 line 更稳定。
    if abs(sx1 - sx2) <= 0.001 or abs(sy1 - sy2) <= 0.001:
        return _line_xml(
            x1,
            y1,
            x2,
            y2,
            stroke,
            stroke_w,
            opacity,
            dash_array=_svg_dash_to_sml(_get_attr(tag, "stroke-dasharray") or "", _line_cap(tag)),
            line_cap=_line_cap(tag),
            line_join=_line_join(tag),
        )

    top_x = min(sx1, sx2)
    top_y = min(sy1, sy2)
    width = max(1.0, abs(sx2 - sx1))
    height = max(1.0, abs(sy2 - sy1))
    flip_attrs = ""
    if sx1 > sx2:
        flip_attrs += ' flipX="true"'
    if sy1 > sy2:
        flip_attrs += ' flipY="true"'
    dash_array = _svg_dash_to_sml(_get_attr(tag, "stroke-dasharray") or "", _line_cap(tag))
    border_attrs = []
    if dash_array and dash_array != "solid":
        border_attrs.append(f'dashArray="{dash_array}"')
    if _line_cap(tag):
        border_attrs.append(f'lineCap="{_line_cap(tag)}"')
    if _line_join(tag):
        border_attrs.append(f'lineJoin="{_line_join(tag)}"')
    border_attr_text = (" " + " ".join(border_attrs)) if border_attrs else ""
    return (
        f'<polyline type="curved-connector3" '
        f'topLeftX="{_format_num(top_x)}" topLeftY="{_format_num(top_y)}" '
        f'width="{_format_num(width)}" height="{_format_num(height)}"{flip_attrs}>'
        f'<border color="{_apply_opacity(stroke, opacity)}" '
        f'width="{_stroke_border_width(stroke_w)}"{border_attr_text}/>'
        f"</polyline>"
    )


def _stroked_points_xml(
    points: List[Tuple[float, float]], tag: str, stroke: str, stroke_w: float, opacity: float
) -> str:
    """点序列 → slide XML."""
    if len(points) < 2:
        return ""
    marker_start = _marker_kind(_get_attr(tag, "marker-start") or "")
    marker_end = _marker_kind(_get_attr(tag, "marker-end") or "")
    if len(points) == 2:
        body = _line_xml(
            points[0][0],
            points[0][1],
            points[1][0],
            points[1][1],
            stroke,
            stroke_w,
            opacity,
            dash_array=_svg_dash_to_sml(_get_attr(tag, "stroke-dasharray") or "", _line_cap(tag)),
            marker_start=marker_start,
            marker_end=marker_end,
            line_cap=_line_cap(tag),
            line_join=_line_join(tag),
        )
        if marker_start == "tbar":
            body += _endpoint_decoration_xml(
                points[0][0],
                points[0][1],
                points[1][0],
                points[1][1],
                marker_kind=marker_start,
                stroke=stroke,
                stroke_w=stroke_w,
                opacity=opacity,
            )
        if marker_end == "tbar":
            body += _endpoint_decoration_xml(
                points[-1][0],
                points[-1][1],
                points[-2][0],
                points[-2][1],
                marker_kind=marker_end,
                stroke=stroke,
                stroke_w=stroke_w,
                opacity=opacity,
            )
        return body

    # 无箭头/端点装饰的多段开放 stroke: custom shape (path) 保接头连续性.
    # 之前拆多 line 会在接头处出现 sub-pixel gap (line 各自 cap 处理不到接头) —— 视觉断裂.
    # custom shape 用 M/L path 全程连续, join 由 slide 端处理; 透明 fill 不影响可视, lint 端如
    # 触发 overlap 误判需要另做 exception (那是 lint 层的 bug, 不该牺牲视觉换过 lint).
    if not marker_start and not marker_end:
        from ._path import _custom_shape_from_points

        return _custom_shape_from_points(
            points,
            fill="none",
            stroke=stroke,
            stroke_w=stroke_w,
            opacity=opacity,
            close=False,
            border_attrs=_border_attrs_from_svg(tag),
        )

    from ._path import _custom_shape_from_points

    body = _custom_shape_from_points(
        points,
        fill="none",
        stroke=stroke,
        stroke_w=stroke_w,
        opacity=opacity,
        close=False,
        border_attrs=_border_attrs_from_svg(tag),
    )
    if marker_start:
        body += _endpoint_decoration_xml(
            points[0][0],
            points[0][1],
            points[1][0],
            points[1][1],
            marker_kind=marker_start,
            stroke=stroke,
            stroke_w=stroke_w,
            opacity=opacity,
        )
    if marker_end:
        body += _endpoint_decoration_xml(
            points[-1][0],
            points[-1][1],
            points[-2][0],
            points[-2][1],
            marker_kind=marker_end,
            stroke=stroke,
            stroke_w=stroke_w,
            opacity=opacity,
        )
    return body
