"""SVG path 解析 / 采样 / → slide custom shape."""

from __future__ import annotations

import math
import re
from typing import List, Optional, Tuple

from ._paint import (
    _format_num,
    _get_attr,
    _get_num,
    _is_transparent_fill,
    _resolve_paint_color,
)
from ._scale import _sh, _sw, _sx, _sy, s2l_x, s2l_y


def _safe_tokens(d: str) -> List[str]:
    """Tokens of a complete, valid path; malformed data yields [] so samplers stop."""
    from ._geometry import path_segments, path_tokens

    try:
        path_segments(d)
        return path_tokens(d)
    except ValueError:
        return []


def _absolute_path_commands(d: str):
    """Absolute M/L/C/Q/A/Z commands with S/T reflected; curves are not sampled."""
    from ._geometry import path_segments

    return [(op, tuple(values)) for op, values in path_segments(d)]


def _sample_svg_arc_points(
    x0: float,
    y0: float,
    rx: float,
    ry: float,
    x_axis_rotation: float,
    large_arc: int,
    sweep: int,
    x2: float,
    y2: float,
) -> List[Tuple[float, float]]:
    """把一条 SVG A (椭圆弧) 命令采样成绝对坐标点序列."""
    rx = abs(rx)
    ry = abs(ry)
    if rx <= 0 or ry <= 0:
        return [(x2, y2)]
    if abs(x0 - x2) < 0.001 and abs(y0 - y2) < 0.001:
        return []

    phi = math.radians(x_axis_rotation)
    cos_phi = math.cos(phi)
    sin_phi = math.sin(phi)
    dx = (x0 - x2) / 2
    dy = (y0 - y2) / 2
    x1p = cos_phi * dx + sin_phi * dy
    y1p = -sin_phi * dx + cos_phi * dy

    lam = (x1p * x1p) / (rx * rx) + (y1p * y1p) / (ry * ry)
    if lam > 1:
        scale = math.sqrt(lam)
        rx *= scale
        ry *= scale

    rx_sq = rx * rx
    ry_sq = ry * ry
    x1p_sq = x1p * x1p
    y1p_sq = y1p * y1p
    denom = rx_sq * y1p_sq + ry_sq * x1p_sq
    if denom <= 0:
        return [(x2, y2)]
    numer = max(0.0, rx_sq * ry_sq - rx_sq * y1p_sq - ry_sq * x1p_sq)
    coef = math.sqrt(numer / denom)
    if bool(large_arc) == bool(sweep):
        coef = -coef
    cxp = coef * (rx * y1p / ry)
    cyp = coef * (-ry * x1p / rx)
    cx = cos_phi * cxp - sin_phi * cyp + (x0 + x2) / 2
    cy = sin_phi * cxp + cos_phi * cyp + (y0 + y2) / 2

    def vector_angle(ux: float, uy: float, vx: float, vy: float) -> float:
        dot = ux * vx + uy * vy
        length = math.hypot(ux, uy) * math.hypot(vx, vy)
        if length == 0:
            return 0.0
        sign = -1 if ux * vy - uy * vx < 0 else 1
        return sign * math.acos(max(-1.0, min(1.0, dot / length)))

    ux = (x1p - cxp) / rx
    uy = (y1p - cyp) / ry
    vx = (-x1p - cxp) / rx
    vy = (-y1p - cyp) / ry
    theta1 = vector_angle(1, 0, ux, uy)
    delta = vector_angle(ux, uy, vx, vy)
    if not sweep and delta > 0:
        delta -= 2 * math.pi
    elif sweep and delta < 0:
        delta += 2 * math.pi

    steps = max(8, min(32, int(math.ceil(abs(delta) / (math.pi / 16)))))
    points: List[Tuple[float, float]] = []
    for step in range(1, steps + 1):
        theta = theta1 + delta * step / steps
        xp = rx * math.cos(theta)
        yp = ry * math.sin(theta)
        x = cos_phi * xp - sin_phi * yp + cx
        y = sin_phi * xp + cos_phi * yp + cy
        points.append((x, y))
    return points


def _custom_shape_from_points(
    points: List[Tuple[float, float]],
    *,
    fill: str,
    stroke: str,
    stroke_w: float,
    opacity: float = 1,
    close: bool = True,
    all_defs: str = "",
    border_attrs: str = "",
) -> str:
    """点序列 → slide custom shape (path 用 M/L 直折线)."""
    mapped = [(s2l_x(x), s2l_y(y)) for x, y in points]
    xs = [x for x, _ in mapped]
    ys = [y for _, y in mapped]
    x0, y0 = min(xs), min(ys)
    w = max(xs) - x0
    h = max(ys) - y0
    if w <= 0 and h <= 0:
        return ""
    if (w <= 3 or h <= 3) and not close and stroke and not _is_transparent_fill(stroke):
        # lazy import 避免 _arrow / _path 循环依赖
        from ._arrow import _line_xml, _stroke_border_width

        parts: List[str] = []
        for idx in range(len(points) - 1):
            x1, y1 = points[idx]
            x2, y2 = points[idx + 1]
            if abs(x1 - x2) <= 0.001 and abs(y1 - y2) <= 0.001:
                continue
            parts.append(
                _line_xml(
                    x1,
                    y1,
                    x2,
                    y2,
                    stroke,
                    stroke_w,
                    opacity,
                    dash_array="solid",
                )
            )
        return "".join(parts)
    if w <= 0 or h <= 0:
        return ""
    from ._arrow import _stroke_border_width

    path_parts = [f"M {_format_num(mapped[0][0] - x0)} {_format_num(mapped[0][1] - y0)}"]
    for x, y in mapped[1:]:
        path_parts.append(f"L {_format_num(x - x0)} {_format_num(y - y0)}")
    if close:
        path_parts.append("Z")
    fill_color = _resolve_paint_color(fill, all_defs) if fill and not _is_transparent_fill(fill) else "rgba(0,0,0,0)"
    border_color = (
        _resolve_paint_color(stroke, all_defs) if stroke and not _is_transparent_fill(stroke) else "rgba(0,0,0,0)"
    )
    border_w = _stroke_border_width(stroke_w) if border_color != "rgba(0,0,0,0)" else 0
    alpha_attr = f' alpha="{opacity:.12g}"' if opacity < 1 else ""
    return (
        f'<shape type="custom" topLeftX="{_format_num(x0)}" topLeftY="{_format_num(y0)}" '
        f'width="{_format_num(max(w, 0.1))}" height="{_format_num(max(h, 0.1))}" '
        f'path="{" ".join(path_parts)}"{alpha_attr}>'
        f'<fill><fillColor color="{fill_color}"/></fill>'
        f'<border color="{border_color}" width="{border_w}"{border_attrs}/>'
        f"</shape>"
    )


def _svg_path_to_local_custom_path(
    d: str,
    *,
    origin_x: float,
    origin_y: float,
) -> Optional[Tuple[str, Tuple[float, float], Tuple[float, float], Tuple[float, float], Tuple[float, float]]]:
    """把 SVG path 转成 slide custom 的 local path，不采样成折线。"""
    # Resolve relative/smooth commands before emitting cubics. Otherwise a
    # following S could accidentally reflect the new cubic introduced for Q.
    from ._geometry import path_segments

    try:
        from ._geometry import fmt

        d = " ".join(op + " " + " ".join(fmt(v) for v in values) for op, values in path_segments(d))
    except ValueError:
        return None
    tokens = _safe_tokens(d)
    if not tokens:
        return None

    def is_cmd(value: str) -> bool:
        return bool(re.fullmatch(r"[MmLlHhVvCcSsQqTtAaZz]", value))

    def local_x(x: float) -> str:
        return _format_num(_sw(x - origin_x))

    def local_y(y: float) -> str:
        return _format_num(_sh(y - origin_y))

    def local_len_x(value: float) -> str:
        return _format_num(abs(_sw(value)))

    def local_len_y(value: float) -> str:
        return _format_num(abs(_sh(value)))

    def next_float() -> float:
        nonlocal i
        value = float(tokens[i])
        i += 1
        return value

    i = 0
    cmd: Optional[str] = None
    cx = cy = 0.0
    sx = sy = 0.0
    have_point = False
    path_parts: List[str] = []
    endpoints: List[Tuple[float, float]] = []
    start_ref: Optional[Tuple[float, float]] = None
    end_ref: Optional[Tuple[float, float]] = None

    def note_segment_end(
        end_x: float,
        end_y: float,
        *,
        first_ref: Optional[Tuple[float, float]] = None,
        last_ref: Optional[Tuple[float, float]] = None,
    ) -> None:
        nonlocal start_ref, end_ref
        if len(endpoints) == 1 and start_ref is None:
            start_ref = first_ref or (end_x, end_y)
        end_ref = last_ref or (cx, cy)
        endpoints.append((end_x, end_y))

    while i < len(tokens):
        if is_cmd(tokens[i]):
            cmd = tokens[i]
            i += 1
            if cmd.lower() == "z":
                path_parts.append("Z")
                if have_point:
                    note_segment_end(sx, sy, first_ref=(sx, sy), last_ref=(cx, cy))
                    cx, cy = sx, sy
                cmd = None
                continue
        if cmd is None:
            return None

        lower = cmd.lower()
        rel = cmd.islower()
        try:
            if lower == "m":
                first = True
                consumed = False
                while i + 1 < len(tokens) and not is_cmd(tokens[i]) and not is_cmd(tokens[i + 1]):
                    x = next_float()
                    y = next_float()
                    if rel and have_point:
                        x += cx
                        y += cy
                    if first:
                        path_parts.append(f"M {local_x(x)} {local_y(y)}")
                        sx, sy = x, y
                        endpoints.append((x, y))
                        have_point = True
                        first = False
                    else:
                        path_parts.append(f"L {local_x(x)} {local_y(y)}")
                        note_segment_end(x, y, first_ref=(x, y), last_ref=(cx, cy))
                    cx, cy = x, y
                    consumed = True
                if not consumed:
                    return None
                cmd = "l" if rel else "L"
                continue

            if not have_point:
                return None

            if lower == "l":
                consumed = False
                while i + 1 < len(tokens) and not is_cmd(tokens[i]) and not is_cmd(tokens[i + 1]):
                    x = next_float()
                    y = next_float()
                    if rel:
                        x += cx
                        y += cy
                    path_parts.append(f"L {local_x(x)} {local_y(y)}")
                    note_segment_end(x, y, first_ref=(x, y), last_ref=(cx, cy))
                    cx, cy = x, y
                    consumed = True
                if not consumed:
                    return None
                continue

            if lower == "h":
                consumed = False
                while i < len(tokens) and not is_cmd(tokens[i]):
                    x = next_float()
                    if rel:
                        x += cx
                    path_parts.append(f"L {local_x(x)} {local_y(cy)}")
                    note_segment_end(x, cy, first_ref=(x, cy), last_ref=(cx, cy))
                    cx = x
                    consumed = True
                if not consumed:
                    return None
                continue

            if lower == "v":
                consumed = False
                while i < len(tokens) and not is_cmd(tokens[i]):
                    y = next_float()
                    if rel:
                        y += cy
                    path_parts.append(f"L {local_x(cx)} {local_y(y)}")
                    note_segment_end(cx, y, first_ref=(cx, y), last_ref=(cx, cy))
                    cy = y
                    consumed = True
                if not consumed:
                    return None
                continue

            if lower == "c":
                consumed = False
                while i + 5 < len(tokens) and not any(is_cmd(tokens[i + j]) for j in range(6)):
                    x1, y1 = next_float(), next_float()
                    x2, y2 = next_float(), next_float()
                    x3, y3 = next_float(), next_float()
                    if rel:
                        x1 += cx
                        y1 += cy
                        x2 += cx
                        y2 += cy
                        x3 += cx
                        y3 += cy
                    path_parts.append(
                        f"C {local_x(x1)} {local_y(y1)} {local_x(x2)} {local_y(y2)} {local_x(x3)} {local_y(y3)}"
                    )
                    note_segment_end(x3, y3, first_ref=(x1, y1), last_ref=(x2, y2))
                    cx, cy = x3, y3
                    consumed = True
                if not consumed:
                    return None
                continue

            if lower == "s":
                consumed = False
                while i + 3 < len(tokens) and not any(is_cmd(tokens[i + j]) for j in range(4)):
                    x2, y2 = next_float(), next_float()
                    x3, y3 = next_float(), next_float()
                    if rel:
                        x2 += cx
                        y2 += cy
                        x3 += cx
                        y3 += cy
                    path_parts.append(f"S {local_x(x2)} {local_y(y2)} {local_x(x3)} {local_y(y3)}")
                    note_segment_end(x3, y3, first_ref=(x3, y3), last_ref=(x2, y2))
                    cx, cy = x3, y3
                    consumed = True
                if not consumed:
                    return None
                continue

            if lower == "q":
                consumed = False
                while i + 3 < len(tokens) and not any(is_cmd(tokens[i + j]) for j in range(4)):
                    x1, y1 = next_float(), next_float()
                    x2, y2 = next_float(), next_float()
                    if rel:
                        x1 += cx
                        y1 += cy
                        x2 += cx
                        y2 += cy
                    # Slides interprets Q as a cubic with repeated controls;
                    # use the exact degree elevation of SVG's quadratic.
                    c1 = (cx + 2 * (x1 - cx) / 3, cy + 2 * (y1 - cy) / 3)
                    c2 = (x2 + 2 * (x1 - x2) / 3, y2 + 2 * (y1 - y2) / 3)
                    path_parts.append(
                        f"C {local_x(c1[0])} {local_y(c1[1])} "
                        f"{local_x(c2[0])} {local_y(c2[1])} {local_x(x2)} {local_y(y2)}"
                    )
                    note_segment_end(x2, y2, first_ref=(x1, y1), last_ref=(x1, y1))
                    cx, cy = x2, y2
                    consumed = True
                if not consumed:
                    return None
                continue

            if lower == "t":
                consumed = False
                while i + 1 < len(tokens) and not is_cmd(tokens[i]) and not is_cmd(tokens[i + 1]):
                    x, y = next_float(), next_float()
                    if rel:
                        x += cx
                        y += cy
                    path_parts.append(f"T {local_x(x)} {local_y(y)}")
                    note_segment_end(x, y, first_ref=(x, y), last_ref=(cx, cy))
                    cx, cy = x, y
                    consumed = True
                if not consumed:
                    return None
                continue

            if lower == "a":
                consumed = False
                while i + 6 < len(tokens) and not any(is_cmd(tokens[i + j]) for j in range(7)):
                    rx, ry = next_float(), next_float()
                    rotation = next_float()
                    large_arc = int(next_float())
                    sweep = int(next_float())
                    x, y = next_float(), next_float()
                    if rel:
                        x += cx
                        y += cy
                    from ._geometry import arc_to_cubics

                    cubics = arc_to_cubics(cx, cy, rx, ry, rotation, large_arc, sweep, x, y)
                    for op, values in cubics:
                        if op == "L":
                            path_parts.append(f"L {local_x(values[0])} {local_y(values[1])}")
                        else:
                            path_parts.append(
                                "C " + " ".join(f"{local_x(values[k])} {local_y(values[k + 1])}" for k in (0, 2, 4))
                            )
                    first_ref = tuple(cubics[0][1][:2]) if cubics else (x, y)
                    last_ref = tuple(cubics[-1][1][2:4]) if cubics and cubics[-1][0] == "C" else (cx, cy)
                    note_segment_end(x, y, first_ref=first_ref, last_ref=last_ref)
                    cx, cy = x, y
                    consumed = True
                if not consumed:
                    return None
                continue

            return None
        except (IndexError, ValueError):
            return None

    if len(endpoints) < 2:
        return None
    return (
        " ".join(path_parts),
        endpoints[0],
        start_ref or endpoints[1],
        endpoints[-1],
        end_ref or endpoints[-2],
    )


def _custom_shape_from_svg_path(
    d: str,
    tag: str,
    *,
    fill: str,
    stroke: str,
    stroke_w: float,
    opacity: float = 1,
    all_defs: str = "",
    bbox: Optional[Tuple[float, float, float, float]] = None,
    border_attrs: str = "",
) -> str:
    """SVG path → native custom 曲线；Q/T 升阶为 C，A 分段为 C。"""
    # lazy import 避免 _arrow / _path 循环依赖
    from ._arrow import _endpoint_decoration_xml, _marker_kind, _stroke_border_width

    bbox = bbox or _parse_path_bbox(d)
    if bbox is None:
        return ""
    x_min, y_min, x_max, y_max = bbox
    border_color = (
        _resolve_paint_color(stroke, all_defs, _get_num(tag, "stroke-opacity", 1))
        if stroke and not _is_transparent_fill(stroke)
        else "rgba(0,0,0,0)"
    )
    # Fill-only bounds need no stroke gutter. Keep unknown paints and degenerate
    # paths conservative, and leave stroke_w intact for paint/marker editing.
    zero_width_color = stroke_w <= 0 and bool(
        re.fullmatch(r"rgba?\(\s*\d+\s*,\s*\d+\s*,\s*\d+(?:\s*,\s*[\d.]+)?\s*\)", border_color)
    )
    tight_fill = (
        x_max > x_min
        and y_max > y_min
        and "url(" not in (stroke or "").lower()
        and (_is_transparent_fill(border_color) or zero_width_color)
    )
    buf = 0.0 if tight_fill else max(1.0, stroke_w / 2 + 1.0)
    x_min -= buf
    y_min -= buf
    x_max += buf
    y_max += buf
    w = x_max - x_min
    h = y_max - y_min
    if w <= 0 or h <= 0:
        return ""
    converted = _svg_path_to_local_custom_path(d, origin_x=x_min, origin_y=y_min)
    if converted is None:
        return ""
    path, start_pt, start_ref, end_pt, end_ref = converted
    fill_color = (
        _resolve_paint_color(fill, all_defs, _get_num(tag, "fill-opacity", 1))
        if fill and not _is_transparent_fill(fill)
        else "rgba(0,0,0,0)"
    )
    border_w = _stroke_border_width(stroke_w) if border_color != "rgba(0,0,0,0)" else 0
    alpha_attr = f' alpha="{opacity:.12g}"' if opacity < 1 else ""
    body = (
        f'<shape type="custom" topLeftX="{_format_num(_sx(x_min))}" '
        f'topLeftY="{_format_num(_sy(y_min))}" '
        f'width="{_format_num(max(_sw(w), 0.1))}" '
        f'height="{_format_num(max(_sh(h), 0.1))}" '
        f'path="{path}"{alpha_attr}>'
        f'<fill><fillColor color="{fill_color}"/></fill>'
        f'<border color="{border_color}" width="{border_w}"{border_attrs}/>'
        f"</shape>"
    )
    marker_start = _marker_kind(_get_attr(tag, "marker-start") or "")
    marker_end = _marker_kind(_get_attr(tag, "marker-end") or "")
    if marker_start:
        body += _endpoint_decoration_xml(
            start_pt[0],
            start_pt[1],
            start_ref[0],
            start_ref[1],
            marker_kind=marker_start,
            stroke=stroke,
            stroke_w=stroke_w,
            opacity=opacity,
        )
    if marker_end:
        body += _endpoint_decoration_xml(
            end_pt[0],
            end_pt[1],
            end_ref[0],
            end_ref[1],
            marker_kind=marker_end,
            stroke=stroke,
            stroke_w=stroke_w,
            opacity=opacity,
        )
    return body


def _segments_to_connected_points(
    segments: List[Tuple[float, float, float, float]],
) -> Optional[List[Tuple[float, float]]]:
    """把首尾相接的线段列表压缩成点序列; 段之间不首尾相连返回 None."""
    if not segments:
        return None
    points: List[Tuple[float, float]] = [(segments[0][0], segments[0][1])]
    cur_x, cur_y = segments[0][0], segments[0][1]
    for x1, y1, x2, y2 in segments:
        if abs(cur_x - x1) > 0.001 or abs(cur_y - y1) > 0.001:
            return None
        points.append((x2, y2))
        cur_x, cur_y = x2, y2
    return points


def _parse_stroked_path_segments(d: str) -> Optional[List[Tuple[float, float, float, float]]]:
    """把 stroke path 解析成可编辑线段 [(x1,y1,x2,y2), ...]."""
    if re.search(r"[SsTt]", d):
        return None
    tokens = _safe_tokens(d)
    if not tokens:
        return None

    segments: List[Tuple[float, float, float, float]] = []
    cmd: Optional[str] = None
    cx = cy = 0.0
    sx = sy = 0.0
    have_point = False
    i = 0

    def is_cmd(value: str) -> bool:
        return bool(re.fullmatch(r"[MmLlHhVvQqCcAaZz]", value))

    def add_line(x: float, y: float) -> None:
        nonlocal cx, cy, have_point
        if have_point and (abs(cx - x) > 0.001 or abs(cy - y) > 0.001):
            segments.append((cx, cy, x, y))
        cx, cy = x, y
        have_point = True

    while i < len(tokens):
        if is_cmd(tokens[i]):
            cmd = tokens[i]
            i += 1
        if cmd is None:
            return None
        lower = cmd.lower()
        rel = cmd.islower()
        if lower == "z":
            if have_point:
                add_line(sx, sy)
            cmd = None
            continue
        if lower in {"m", "l"}:
            first_pair = True
            consumed = False
            while i + 1 < len(tokens) and not is_cmd(tokens[i]) and not is_cmd(tokens[i + 1]):
                x = float(tokens[i])
                y = float(tokens[i + 1])
                i += 2
                if rel:
                    x += cx
                    y += cy
                if lower == "m" and first_pair:
                    cx, cy = x, y
                    sx, sy = x, y
                    have_point = True
                else:
                    add_line(x, y)
                first_pair = False
                consumed = True
            if not consumed:
                return None
            if lower == "m":
                cmd = "l" if rel else "L"
            continue
        if lower == "h":
            consumed = False
            while i < len(tokens) and not is_cmd(tokens[i]):
                x = float(tokens[i])
                i += 1
                if rel:
                    x += cx
                add_line(x, cy)
                consumed = True
            if not consumed:
                return None
            continue
        if lower == "v":
            consumed = False
            while i < len(tokens) and not is_cmd(tokens[i]):
                y = float(tokens[i])
                i += 1
                if rel:
                    y += cy
                add_line(cx, y)
                consumed = True
            if not consumed:
                return None
            continue
        if lower == "q":
            consumed = False
            while i + 3 < len(tokens) and not any(is_cmd(tokens[i + j]) for j in range(4)):
                x1, y1 = float(tokens[i]), float(tokens[i + 1])
                x2, y2 = float(tokens[i + 2]), float(tokens[i + 3])
                i += 4
                if rel:
                    x1 += cx
                    y1 += cy
                    x2 += cx
                    y2 += cy
                x0, y0 = cx, cy
                prev_x, prev_y = x0, y0
                steps = 8
                for step in range(1, steps + 1):
                    t = step / steps
                    mt = 1 - t
                    x = mt * mt * x0 + 2 * mt * t * x1 + t * t * x2
                    y = mt * mt * y0 + 2 * mt * t * y1 + t * t * y2
                    if abs(prev_x - x) > 0.001 or abs(prev_y - y) > 0.001:
                        segments.append((prev_x, prev_y, x, y))
                    prev_x, prev_y = x, y
                cx, cy = x2, y2
                have_point = True
                consumed = True
            if not consumed:
                return None
            continue
        if lower == "c":
            consumed = False
            while i + 5 < len(tokens) and not any(is_cmd(tokens[i + j]) for j in range(6)):
                x1, y1 = float(tokens[i]), float(tokens[i + 1])
                x2, y2 = float(tokens[i + 2]), float(tokens[i + 3])
                x3, y3 = float(tokens[i + 4]), float(tokens[i + 5])
                i += 6
                if rel:
                    x1 += cx
                    y1 += cy
                    x2 += cx
                    y2 += cy
                    x3 += cx
                    y3 += cy
                x0, y0 = cx, cy
                prev_x, prev_y = x0, y0
                steps = 10
                for step in range(1, steps + 1):
                    t = step / steps
                    mt = 1 - t
                    x = mt * mt * mt * x0 + 3 * mt * mt * t * x1 + 3 * mt * t * t * x2 + t * t * t * x3
                    y = mt * mt * mt * y0 + 3 * mt * mt * t * y1 + 3 * mt * t * t * y2 + t * t * t * y3
                    if abs(prev_x - x) > 0.001 or abs(prev_y - y) > 0.001:
                        segments.append((prev_x, prev_y, x, y))
                    prev_x, prev_y = x, y
                cx, cy = x3, y3
                have_point = True
                consumed = True
            if not consumed:
                return None
            continue
        if lower == "a":
            consumed = False
            while i + 6 < len(tokens) and not any(is_cmd(tokens[i + j]) for j in range(7)):
                rx, ry = float(tokens[i]), float(tokens[i + 1])
                x_axis_rotation = float(tokens[i + 2])
                large_arc = int(float(tokens[i + 3]))
                sweep = int(float(tokens[i + 4]))
                x2, y2 = float(tokens[i + 5]), float(tokens[i + 6])
                i += 7
                if rel:
                    x2 += cx
                    y2 += cy
                prev_x, prev_y = cx, cy
                for x, y in _sample_svg_arc_points(cx, cy, rx, ry, x_axis_rotation, large_arc, sweep, x2, y2):
                    if abs(prev_x - x) > 0.001 or abs(prev_y - y) > 0.001:
                        segments.append((prev_x, prev_y, x, y))
                    prev_x, prev_y = x, y
                cx, cy = x2, y2
                have_point = True
                consumed = True
            if not consumed:
                return None
            continue
        return None

    return [seg for seg in segments if abs(seg[0] - seg[2]) > 0.001 or abs(seg[1] - seg[3]) > 0.001]


def _sample_path_points(d: str) -> Optional[Tuple[List[Tuple[float, float]], bool]]:
    """SVG path → 采样点序列 + closed 标记, 供 custom shape (M/L 直折线) 用."""
    tokens = _safe_tokens(d)
    if not tokens:
        return None
    points: List[Tuple[float, float]] = []
    cmd: Optional[str] = None
    cx = cy = 0.0
    sx = sy = 0.0
    closed = False
    i = 0

    def is_cmd(value: str) -> bool:
        return bool(re.fullmatch(r"[MmLlHhVvCcQqAaZz]", value))

    def next_float() -> float:
        nonlocal i
        value = float(tokens[i])
        i += 1
        return value

    while i < len(tokens):
        if is_cmd(tokens[i]):
            cmd = tokens[i]
            i += 1
            if cmd.lower() == "z":
                if points and (points[-1] != (sx, sy)):
                    points.append((sx, sy))
                cx, cy = sx, sy
                closed = True
                cmd = None
                continue
        if cmd is None:
            continue
        rel = cmd.islower()
        lower = cmd.lower()
        try:
            if lower == "m":
                x, y = next_float(), next_float()
                if rel:
                    x += cx
                    y += cy
                points.append((x, y))
                cx, cy = x, y
                sx, sy = x, y
                cmd = "l" if rel else "L"
            elif lower == "l":
                while i + 1 < len(tokens) and not is_cmd(tokens[i]):
                    x, y = next_float(), next_float()
                    if rel:
                        x += cx
                        y += cy
                    points.append((x, y))
                    cx, cy = x, y
            elif lower == "h":
                while i < len(tokens) and not is_cmd(tokens[i]):
                    x = next_float()
                    if rel:
                        x += cx
                    cx = x
                    points.append((cx, cy))
            elif lower == "v":
                while i < len(tokens) and not is_cmd(tokens[i]):
                    y = next_float()
                    if rel:
                        y += cy
                    cy = y
                    points.append((cx, cy))
            elif lower == "c":
                while i + 5 < len(tokens) and not is_cmd(tokens[i]):
                    x1, y1 = next_float(), next_float()
                    x2, y2 = next_float(), next_float()
                    x3, y3 = next_float(), next_float()
                    if rel:
                        x1 += cx
                        y1 += cy
                        x2 += cx
                        y2 += cy
                        x3 += cx
                        y3 += cy
                    x0, y0 = cx, cy
                    for step in range(1, 11):
                        t = step / 10
                        mt = 1 - t
                        x = mt**3 * x0 + 3 * mt**2 * t * x1 + 3 * mt * t**2 * x2 + t**3 * x3
                        y = mt**3 * y0 + 3 * mt**2 * t * y1 + 3 * mt * t**2 * y2 + t**3 * y3
                        points.append((x, y))
                    cx, cy = x3, y3
            elif lower == "q":
                while i + 3 < len(tokens) and not is_cmd(tokens[i]):
                    x1, y1 = next_float(), next_float()
                    x2, y2 = next_float(), next_float()
                    if rel:
                        x1 += cx
                        y1 += cy
                        x2 += cx
                        y2 += cy
                    x0, y0 = cx, cy
                    for step in range(1, 9):
                        t = step / 8
                        mt = 1 - t
                        x = mt**2 * x0 + 2 * mt * t * x1 + t**2 * x2
                        y = mt**2 * y0 + 2 * mt * t * y1 + t**2 * y2
                        points.append((x, y))
                    cx, cy = x2, y2
            elif lower == "a":
                while i + 6 < len(tokens) and not is_cmd(tokens[i]):
                    rx, ry = next_float(), next_float()
                    angle = next_float()
                    large_arc = int(next_float())
                    sweep = int(next_float())
                    x2, y2 = next_float(), next_float()
                    if rel:
                        x2 += cx
                        y2 += cy
                    points.extend(_sample_svg_arc_points(cx, cy, rx, ry, angle, large_arc, sweep, x2, y2))
                    cx, cy = x2, y2
            else:
                return None
        except (IndexError, ValueError):
            return None
    if len(points) < 2:
        return None
    return points, closed


def _parse_path_bbox(d: str) -> Optional[Tuple[float, float, float, float]]:
    """Shared exact curve extrema include smooth controls and corrected arcs."""
    from ._bounds import path_bounds

    try:
        return path_bounds(d)
    except ValueError:
        return None
