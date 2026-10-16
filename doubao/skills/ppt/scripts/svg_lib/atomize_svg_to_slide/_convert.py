"""单 tag → slide XML fragment."""

from __future__ import annotations

import re
from typing import List

from ._arrow import (
    _border_attrs_from_svg,
    _curved_connector_xml,
    _endpoint_decoration_xml,
    _line_cap,
    _line_join,
    _line_xml,
    _marker_kind,
    _stroke_border_width,
    _stroked_points_xml,
    _svg_dash_to_sml,
)
from ._config import _CFG
from ._paint import (
    _apply_opacity,
    _escape_xml,
    _format_num,
    _get_attr,
    _get_num,
    _is_muted_gray,
    _is_transparent_fill,
    _map_svg_font_family,
    _resolve_paint_color,
)
from ._gradient import native_linear_gradient
from ._path import (
    _custom_shape_from_points,
    _custom_shape_from_svg_path,
    _parse_path_bbox,
    _parse_stroked_path_segments,
    _sample_path_points,
    _segments_to_connected_points,
)
from ._scale import _font_scale_ratio, _sh, _sw, _sx, _sy, s2l_x, s2l_y


def _minimize_defs_for(tag: str, all_defs: str) -> str:
    """Retain the transitive closure of local URL/href dependencies."""
    from ._resources import resource_closure

    return resource_closure(tag, all_defs)


def _wrap_svg_embed(tag: str, x: float, y: float, w: float, h: float, defs: str = "") -> str:
    """把一个 SVG tag 包成独立小 embed (用于 halo / gradient rect / circle+filter 等)."""
    inner_svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x} {y} {w} {h}">{defs}{tag}</svg>'
    return (
        f'<embed topLeftX="{_sx(x):.1f}" topLeftY="{_sy(y):.1f}" '
        f'width="{_sw(w):.1f}" height="{_sh(h):.1f}">{inner_svg}</embed>'
    )


def convert_rect(tag: str, all_defs: str = "") -> str:
    """rect → slide-native shape rect; filter 走 embed."""
    x = _get_num(tag, "x")
    y = _get_num(tag, "y")
    w = _get_num(tag, "width")
    h = _get_num(tag, "height")
    if w < 1 or h < 1:
        return ""
    fill = _get_attr(tag, "fill") or "none"
    stroke = _get_attr(tag, "stroke") or ""
    stroke_w = _get_num(tag, "stroke-width", 1)
    opacity = _get_num(tag, "opacity", 1)
    rx = _get_num(tag, "rx", 0)
    filter_id = _get_attr(tag, "filter") or ""
    # drop background: 覆盖 viewBox ≥90% 的实色 rect (无 stroke) 视作 canvas 底色 · 跳过
    if _CFG.get("drop_bg") and fill != "none" and _is_transparent_fill(stroke):
        coverage = (w * h) / (_CFG["svg_w"] * _CFG["svg_h"])
        if coverage >= 0.9:
            return ""

    # 带 filter (drop-shadow / blur / glow) 的 rect · native shape 不支持 filter,
    # 走 embed fallback 保留原视觉 · 仍是一 tag 一可编辑对象
    if filter_id:
        buf = max(2.0, stroke_w / 2 + 2.0)
        return _wrap_svg_embed(tag, x - buf, y - buf, w + buf * 2, h + buf * 2, defs=_minimize_defs_for(tag, all_defs))

    # 无 filter · 转 native rect. gradient fill 尽量转 CSS gradient (见 _resolve_paint_color).
    slide_x = s2l_x(x)
    slide_y = s2l_y(y)
    slide_w_val = _sw(w)
    slide_h_val = _sh(h)
    fill_color = (
        _resolve_paint_color(fill, all_defs, _get_num(tag, "fill-opacity", 1))
        if not _is_transparent_fill(fill)
        else "rgba(0,0,0,0)"
    )
    border_color = (
        _resolve_paint_color(stroke, all_defs, _get_num(tag, "stroke-opacity", 1))
        if not _is_transparent_fill(stroke)
        else "rgba(0,0,0,0)"
    )
    border_w = _stroke_border_width(stroke_w) if not _is_transparent_fill(stroke) else 0
    rx_scaled = int(rx * _CFG["slide_w"] / _CFG["svg_w"]) if rx else 0
    rx_attr = f' presetHandlers="{rx_scaled}"' if rx_scaled else ""
    op_attr = f' alpha="{opacity}"' if opacity < 1 else ""
    return (
        f'<shape type="rect" topLeftX="{slide_x:.1f}" topLeftY="{slide_y:.1f}" '
        f'width="{slide_w_val:.1f}" height="{slide_h_val:.1f}"{rx_attr}{op_attr}>'
        f'<fill><fillColor color="{fill_color}"/></fill>'
        f'<border color="{border_color}" width="{border_w}"{_border_attrs_from_svg(tag) if border_w else ""}/>'
        f"</shape>"
    )


def convert_line(tag: str, all_defs: str = "") -> str:
    """line → slide-native line. gradient stroke 走 embed 保 gradient."""
    x1 = _get_num(tag, "x1")
    y1 = _get_num(tag, "y1")
    x2 = _get_num(tag, "x2")
    y2 = _get_num(tag, "y2")
    stroke = _get_attr(tag, "stroke") or "#000"
    stroke_w = _get_num(tag, "stroke-width", 1)
    opacity = _get_num(tag, "opacity", 1)
    stroke_opacity = _get_num(tag, "stroke-opacity", 1)

    # gradient stroke (url(#gradId)) native line 无法表达 (border color 只吃 solid),
    # 走 embed 保 gradient · 之前 bug 是直接把 url(#gradId) 塞进 border color, slide 端引用不到 defs.
    if "url(" in stroke:
        buf = max(2.0, stroke_w / 2 + 2.0)
        min_x = min(x1, x2) - buf
        min_y = min(y1, y2) - buf
        w = abs(x2 - x1) + buf * 2
        h = abs(y2 - y1) + buf * 2
        return _wrap_svg_embed(tag, min_x, min_y, w, h, defs=_minimize_defs_for(tag, all_defs))

    marker_start = _marker_kind(_get_attr(tag, "marker-start") or "")
    marker_end = _marker_kind(_get_attr(tag, "marker-end") or "")
    line_xml = _line_xml(
        x1,
        y1,
        x2,
        y2,
        stroke,
        stroke_w,
        opacity * stroke_opacity,
        dash_array=_svg_dash_to_sml(_get_attr(tag, "stroke-dasharray") or "", _line_cap(tag)),
        marker_start=marker_start,
        marker_end=marker_end,
        line_cap=_line_cap(tag),
        line_join=_line_join(tag),
    )
    if marker_start == "tbar":
        line_xml += _endpoint_decoration_xml(
            x1,
            y1,
            x2,
            y2,
            marker_kind="tbar",
            stroke=stroke,
            stroke_w=stroke_w,
            opacity=opacity * stroke_opacity,
        )
    if marker_end == "tbar":
        line_xml += _endpoint_decoration_xml(
            x2,
            y2,
            x1,
            y1,
            marker_kind="tbar",
            stroke=stroke,
            stroke_w=stroke_w,
            opacity=opacity * stroke_opacity,
        )
    return line_xml


def convert_text(tag: str, all_defs: str = "", *, _font_policy=None) -> str:
    """text → slide-native shape text (可编辑)."""
    if _font_policy is not None:
        _font_policy.clear()
    import xml.etree.ElementTree as ET

    element = ET.fromstring(tag)
    from ._text_layout import native_text_baseline

    baseline = native_text_baseline(element)
    if (
        baseline is None
        or element.get("{http://www.w3.org/XML/1998/namespace}space") == "preserve"
        or element.get("stroke") not in (None, "none")
    ):
        from ._effects import svg_embed

        return svg_embed(tag, all_defs)
    if len(element):
        from ._rich_text import convert_rich_text

        result = convert_rich_text(element, all_defs, convert_text, _font_policy=_font_policy)
        if result is not None:
            return result
        from ._effects import svg_embed

        return svg_embed(tag, all_defs)
    x = _get_num(tag, "x")
    y = _get_num(tag, "y")
    # ElementTree already decodes named/numeric entities. SVG's default white
    # space collapses ASCII whitespace; preserving it inflated estimated width.
    plain_text = re.sub(r"[\t\r\n ]+", " ", element.text or "").strip(" ")
    if not plain_text:
        return ""

    # A literal ellipsis can be authored prose or mathematical notation. The converter cannot infer whether a generator
    # truncated content from a glyph.
    _ellipsis_hits = [c for c in plain_text if c in ("…", "⋯")]
    if _ellipsis_hits and _CFG.get("ellipsis_policy", "preserve") == "fail":
        raise ValueError(
            f"ellipsis {_ellipsis_hits!r} in SVG text {plain_text!r}. "
            "Rejected by explicit ellipsis_policy='fail'; preserve authored text "
            "and handle any automatic truncation at its generating source."
        )

    size = _get_num(tag, "font-size", 11)  # SVG-space font size
    fill = _get_attr(tag, "fill") or "#1C1914"
    anchor = _get_attr(tag, "text-anchor") or "start"
    weight = _get_attr(tag, "font-weight") or ""
    italic = _get_attr(tag, "font-style") in ("italic", "oblique")
    bold = weight in ("600", "700", "800", "900", "bold", "bolder")
    font_family = _map_svg_font_family(_get_attr(tag, "font-family") or "")

    color = _apply_opacity(fill, _get_num(tag, "fill-opacity", 1))
    text_opacity = _get_num(tag, "opacity", 1)
    spacing_attr = _get_attr(tag, "letter-spacing")
    from ._geometry import number

    try:
        spacing_svg = (
            0
            if spacing_attr in (None, "normal")
            else (number(spacing_attr[:-2]) * size if spacing_attr.endswith("em") else number(spacing_attr))
        )
    except ValueError:
        from ._effects import svg_embed

        return svg_embed(tag, all_defs)

    # 目标: SVG 字号 × 缩放比 得到 slide 字号, 但不低于 min_font (可读性绝对下限).
    # 缩放比用 anisotropy 感知的 _font_scale_ratio(), 避免 y 方向压缩重时 shape 高度撞行.
    # min_font 是 slide 空间绝对下限, **不跟 scale 稀释** —— 缩放影响该图看起来多大,
    # 不该影响最小可读字号. 用户 set_min_slide_font_size(10) 意思就是 slide 端不低于 10pt.
    hard_thresh = _CFG.get("drop_text_below", 0)
    _min_font = max(6, int(_CFG.get("min_slide_font_size", 10)) or 6)
    _sf_ratio_raw = _font_scale_ratio()
    _sf_ratio_now = max(0.01, _sf_ratio_raw)

    # subtitle 松绑: SVG 层小灰字视为次要说明, 允许更小的 min_font 建立层级
    _subtitle_th = int(_CFG.get("subtitle_svg_threshold", 0) or 0)
    _is_subtitle = False
    if _subtitle_th > 0 and size <= _subtitle_th and _is_muted_gray(color):
        _is_subtitle = True
        _min_font_for_this = max(6, int(_CFG.get("min_slide_font_size_subtitle", 8)) or 6)
    else:
        _min_font_for_this = _min_font

    # 一刀切过滤: 拆后 slide 字号 < 阈值 → 直接跳过
    slide_size_preview = max(_min_font_for_this, size * _sf_ratio_now)
    if hard_thresh > 0 and slide_size_preview < hard_thresh:
        return ""

    # 灰噪点过滤: 拆后 slide 字号 < 阈值 且颜色中灰 → 跳过
    micro_thresh = _CFG.get("drop_micro_gray_below", 0)
    if micro_thresh > 0 and slide_size_preview < micro_thresh and _is_muted_gray(color):
        return ""

    # Resolve the final native font and spacing before measuring.
    from ._font_metrics import measure_text, text_advance, baseline_offset

    slide_font = max(_min_font_for_this, size * _sf_ratio_now)
    font_before_cap = slide_font
    cap = 0
    if _is_subtitle:
        cap = int(_CFG.get("subtitle_slide_font_cap", 0) or 0)
        if cap > 0:
            slide_font = max(_min_font_for_this, min(slide_font, cap))
    spacing_slide = (
        _sw(spacing_svg)
        if spacing_attr is not None
        else (float(_CFG.get("subtitle_letter_spacing", 0) or 0) if _is_subtitle else 0.0)
    )
    mode = _CFG.get("font_metrics", "auto")
    measure_weight = "bold" if bold else "normal"
    measure_style = "italic" if italic else "normal"
    metric = (
        measure_text(plain_text, font_family or "sans-serif", slide_font, measure_weight, measure_style)
        if mode == "auto"
        else None
    )
    advance = text_advance(
        plain_text, font_family, slide_font, measure_weight, measure_style, spacing_slide, metrics=mode
    )
    # A bounded per-box allowance, not a multiplier that grows every label. Ink
    # overhang is relevant for italic letters, while anchors follow advances.
    overhang = max(0, metric.right - metric.advance, -metric.left) if metric is not None else 0
    from ._font_metrics import lint_floor_width

    lint_width = lint_floor_width(plain_text, font_family, slide_font, measure_weight, spacing_slide)
    slide_w_val = max(1, advance + overhang + slide_font * 0.5, lint_width + slide_font * 0.1)
    slide_x = _sx(x) - (slide_w_val / 2 if anchor == "middle" else slide_w_val if anchor == "end" else 0)

    # Native text's existing alphabetic placement uses a .35em center offset.
    source_metric = (
        measure_text(plain_text, font_family or "sans-serif", size, measure_weight, measure_style)
        if mode == "auto"
        else None
    )
    alphabetic_y = y + baseline_offset(baseline, size, source_metric)
    slide_h_val = max(_sh(size), float(slide_font))
    slide_y = _sy(alphabetic_y) - 0.35 * _sh(size) - slide_h_val / 2

    text_align = {"start": "left", "middle": "center", "end": "right"}.get(anchor, "left")
    bold_attr = ' bold="true"' if bold else ""
    italic_attr = ' italic="true"' if italic else ""
    safe_font_family = _escape_xml(font_family).replace(chr(34), "&quot;")
    font_family_attr = f' fontFamily="{safe_font_family}"' if font_family else ""
    slide_text = _escape_xml(plain_text)

    # subtitle 松绑: 加 letterSpacing 透气 + 可选强制覆盖颜色
    letter_spacing_attr = ""
    if _is_subtitle:
        ls = float(_CFG.get("subtitle_letter_spacing", 0.0) or 0.0)
        if ls > 0:
            letter_spacing_attr = f' letterSpacing="{ls:g}"'
        override_color = _CFG.get("subtitle_color_override", "") or ""
        if override_color:
            color = override_color
    if spacing_attr is not None:
        letter_spacing_attr = f' letterSpacing="{_sw(spacing_svg):.12g}"'
    text_alpha_attr = f' alpha="{text_opacity:.12g}"' if text_opacity < 1 else ""
    fragment = (
        f'<shape type="text" topLeftX="{slide_x:.1f}" topLeftY="{slide_y:.1f}" '
        f'width="{slide_w_val:.1f}" height="{slide_h_val:.1f}"{text_alpha_attr}>'
        f'<content fontSize="{slide_font:g}"{font_family_attr} color="{color}" '
        f'textAlign="{text_align}" verticalAlign="middle" wrap="false" autoFit="no-auto-fit"{bold_attr}{italic_attr}{letter_spacing_attr}>'
        f"<p>{slide_text}</p></content></shape>"
    )
    if _font_policy is not None:
        adjustments = []
        if _sf_ratio_now != _sf_ratio_raw:
            adjustments.append("scale_ratio_floor")
        if size * _sf_ratio_now < _min_font_for_this:
            adjustments.append("minimum_font_size")
        if slide_font < font_before_cap:
            adjustments.append("subtitle_cap")
        _font_policy.update(
            kind="plain",
            source_font_size=size,
            font_scale_ratio=_sf_ratio_raw,
            applied_font_scale_ratio=_sf_ratio_now,
            natural_slide_font_size=size * _sf_ratio_raw,
            computed_slide_font_size=slide_font,
            configured_min_slide_font_size=int(_CFG.get("min_slide_font_size", 10)),
            effective_min_slide_font_size=_min_font_for_this,
            subtitle_matched=_is_subtitle,
            subtitle_svg_threshold=_subtitle_th,
            subtitle_min_slide_font_size=(int(_CFG.get("min_slide_font_size_subtitle", 8)) if _is_subtitle else None),
            subtitle_cap=cap if _is_subtitle else None,
            adjustments=adjustments,
        )
    return fragment


def convert_path(tag: str, all_defs: str = "") -> str:
    """path → slide-native line / custom shape / curved-connector / 或独立小 embed."""
    d = _get_attr(tag, "d") or ""
    if d.strip():
        from ._geometry import path_segments

        try:
            path_segments(d)
        except ValueError as error:
            raise ValueError(
                f"Invalid SVG path d={d[:60]!r}: {error}; fix the path data instead of deleting the element"
            ) from error
    stroke = _get_attr(tag, "stroke") or ""
    fill = _get_attr(tag, "fill")
    transform = _get_attr(tag, "transform") or ""
    filter_id = _get_attr(tag, "filter") or ""
    stroke_w = _get_num(tag, "stroke-width", 1)
    opacity = _get_num(tag, "opacity", 1)
    stroke_opacity = _get_num(tag, "stroke-opacity", 1)
    has_close = bool(re.search(r"[Zz]", d))
    has_curve = bool(re.search(r"[CcSsQqTtAa]", d))
    bbox = _parse_path_bbox(d)
    is_open_stroke = _is_transparent_fill(fill) or (fill is None and not has_close)
    if (
        bbox is not None
        and not transform
        and (len(re.findall(r"[Mm]", d)) > 1 or (fill and not _is_transparent_fill(fill)))
    ):
        exact = _custom_shape_from_svg_path(
            d,
            tag,
            fill=fill or "none",
            stroke=stroke,
            stroke_w=stroke_w,
            opacity=opacity,
            all_defs=all_defs,
            bbox=bbox,
            border_attrs=_border_attrs_from_svg(tag),
        )
        if exact:
            return exact

    # An open round cap does not make an arbitrary Bezier a preset connector. Preserve its controls (including
    # smooth_curve / guided connector output).
    if has_curve and not transform and bbox is not None:
        from ._geometry import path_segments

        commands = list(path_segments(d))
        flat = False
        if commands and commands[0][0] == "M" and all(op in ("L", "C", "Q") for op, _ in commands[1:]):
            start = tuple(commands[0][1])
            end = tuple(commands[-1][1][-2:])
            controls = [point for _, values in commands for point in zip(values[::2], values[1::2])]
            flat = any(
                abs(start[k] - end[k]) < 1e-10
                and all(abs(p[k] - start[k]) < 1e-10 for p in controls)
                and all(min(start[1 - k], end[1 - k]) <= p[1 - k] <= max(start[1 - k], end[1 - k]) for p in controls)
                for k in (0, 1)
            )
        if not flat:
            exact = _custom_shape_from_svg_path(
                d,
                tag,
                fill=fill or "none",
                stroke=stroke,
                stroke_w=stroke_w,
                opacity=opacity,
                all_defs=all_defs,
                bbox=bbox,
                border_attrs=_border_attrs_from_svg(tag),
            )
            if exact:
                return exact
            from ._effects import svg_embed

            return svg_embed(tag, all_defs)

    thin_stroke_curve = False
    if has_curve and bbox is not None:
        raw_w = bbox[2] - bbox[0]
        raw_h = bbox[3] - bbox[1]
        thin_stroke_curve = min(abs(raw_w), abs(raw_h)) <= 0.5
    round_cap_connector_curve = (
        has_curve
        and thin_stroke_curve
        and is_open_stroke
        and _line_cap(tag) == "round"
        and not _get_attr(tag, "marker-start")
        and not _get_attr(tag, "marker-end")
    )
    # Nonflat curves returned above; this fast path only handles proven flat strokes.
    if round_cap_connector_curve:
        segments = _parse_stroked_path_segments(d)
        points = _segments_to_connected_points(segments) if segments else None
        if points:
            endpoint_axis_aligned = (
                abs(points[0][0] - points[-1][0]) <= 0.001 or abs(points[0][1] - points[-1][1]) <= 0.001
            )
            if thin_stroke_curve or not endpoint_axis_aligned:
                curve = _curved_connector_xml(
                    points[0][0],
                    points[0][1],
                    points[-1][0],
                    points[-1][1],
                    tag,
                    stroke,
                    stroke_w,
                    opacity * stroke_opacity,
                )
                if curve:
                    return curve
            round_cap_connector_curve = False
    can_treat_as_stroke_path = (
        bool(stroke)
        and "url(" not in stroke
        and not transform
        and not filter_id
        and is_open_stroke
        and (not has_curve or thin_stroke_curve or round_cap_connector_curve)
    )
    if can_treat_as_stroke_path:
        segments = _parse_stroked_path_segments(d)
        if segments:
            combined_opacity = opacity * stroke_opacity
            points = _segments_to_connected_points(segments)
            if points:
                return _stroked_points_xml(points, tag, stroke, stroke_w, combined_opacity)
            parts: List[str] = []
            for idx, (x1, y1, x2, y2) in enumerate(segments):
                parts.append(
                    _line_xml(
                        x1,
                        y1,
                        x2,
                        y2,
                        stroke,
                        stroke_w,
                        combined_opacity,
                        dash_array=_svg_dash_to_sml(_get_attr(tag, "stroke-dasharray") or "", _line_cap(tag)),
                        marker_start=_marker_kind(_get_attr(tag, "marker-start") or "") if idx == 0 else "",
                        marker_end=_marker_kind(_get_attr(tag, "marker-end") or "") if idx == len(segments) - 1 else "",
                        line_cap=_line_cap(tag),
                        line_join=_line_join(tag),
                    )
                )
            return "".join(parts)
    if has_curve and not transform and bbox is not None:
        curve_shape = _custom_shape_from_svg_path(
            d,
            tag,
            fill=fill or "none",
            stroke=stroke,
            stroke_w=stroke_w,
            opacity=opacity,
            all_defs=all_defs,
            bbox=bbox,
            border_attrs=_border_attrs_from_svg(tag),
        )
        if curve_shape:
            return curve_shape
    can_treat_as_custom_path = not transform and fill is not None and fill != "none" and "url(" not in stroke
    if can_treat_as_custom_path:
        sampled = _sample_path_points(d)
        if sampled:
            points, closed = sampled
            return _custom_shape_from_points(
                points,
                fill=fill or "none",
                stroke=stroke,
                stroke_w=stroke_w,
                opacity=opacity,
                close=closed or has_close,
                all_defs=all_defs,
                border_attrs=_border_attrs_from_svg(tag),
            )

    if bbox is None:
        return ""
    x_min, y_min, x_max, y_max = bbox
    sw = stroke_w
    # embed bbox: 原 bbox 加 stroke 半径 buffer, 避免细线被 embed 边缘裁掉
    buf = max(1, sw / 2 + 1)
    x_min -= buf
    y_min -= buf
    w = (x_max - x_min) + buf * 2
    h = (y_max - y_min) + buf * 2
    if w < 1 or h < 1:
        return ""

    # sub-pixel stroke 补偿: slide 缩放狠 (< 0.5) 时 stroke 会缩到不可见.
    # rewrite inner SVG 的 stroke-width 让 render 后至少 ≥ 1.2 slide-px.
    # 保留 preset 里粗细比例 (leaf 1.4 vs branch 2.2), 用 BASELINE_SW 反算比例.
    scale_x = _CFG["slide_w"] / _CFG["svg_w"]
    scale_y = _CFG["slide_h"] / _CFG["svg_h"]
    render_scale = min(scale_x, scale_y)
    MIN_RENDER_STROKE_PX = 1.2
    effective_stroke_px = sw * render_scale
    tag_fixed = tag
    if sw > 0 and effective_stroke_px < MIN_RENDER_STROKE_PX and render_scale > 0:
        base_sw = MIN_RENDER_STROKE_PX / render_scale
        BASELINE_SW = 1.4  # preset 常用最细 stroke, 作为放大比例基准
        ratio = sw / BASELINE_SW if sw > BASELINE_SW else 1.0
        target_sw = base_sw * ratio
        tag_fixed = re.sub(
            r'stroke-width="[^"]*"',
            f'stroke-width="{target_sw:.2f}"',
            tag,
        )
        # 原 tag 无 stroke-width 时不硬插 · 默认 1 已按 sw 处理过

    # 构造 embed: viewBox 归零, path 内容用 <g transform> 平移到原点
    minimal_defs = _minimize_defs_for(tag_fixed, all_defs)
    inner_svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}">'
        f"{minimal_defs}"
        f'<g transform="translate({-x_min} {-y_min})">{tag_fixed}</g>'
        f"</svg>"
    )
    return (
        f'<embed topLeftX="{_sx(x_min):.1f}" topLeftY="{_sy(y_min):.1f}" '
        f'width="{_sw(w):.1f}" height="{_sh(h):.1f}">{inner_svg}</embed>'
    )


def convert_circle(tag: str, all_defs: str = "") -> str:
    """circle → native ellipse, including alpha/stroke and simple linear fills."""
    cx = _get_num(tag, "cx")
    cy = _get_num(tag, "cy")
    r = _get_num(tag, "r")
    if r <= 0:
        return ""
    fill = _get_attr(tag, "fill") or "none"
    stroke = _get_attr(tag, "stroke") or ""
    filter_id = _get_attr(tag, "filter") or ""
    stroke_w = _get_num(tag, "stroke-width", 1)
    fill_opacity = _get_num(tag, "fill-opacity", 1)
    stroke_opacity = _get_num(tag, "stroke-opacity", 1)
    opacity = _get_num(tag, "opacity", 1)
    gradient = native_linear_gradient(fill, all_defs, fill_opacity) if "url(" in fill else None
    unsupported = any(
        _get_attr(tag, key)
        for key in (
            "transform",
            "style",
            "clip-path",
            "mask",
            "vector-effect",
            "stroke-dasharray",
            "color-interpolation",
        )
    )
    if filter_id or unsupported or "url(" in stroke or ("url(" in fill and gradient is None):
        buf = max(2.0, stroke_w / 2 + 2.0)
        return _wrap_svg_embed(
            tag,
            cx - r - buf,
            cy - r - buf,
            r * 2 + buf * 2,
            r * 2 + buf * 2,
            defs=all_defs,
        )
    fill_c = gradient or (_apply_opacity(fill, fill_opacity) if not _is_transparent_fill(fill) else "rgba(0,0,0,0)")
    stroke_c = (
        _apply_opacity(stroke, stroke_opacity) if stroke and not _is_transparent_fill(stroke) else "rgba(0,0,0,0)"
    )
    border_w = _stroke_border_width(stroke_w) if stroke_c != "rgba(0,0,0,0)" else 0
    alpha = f' alpha="{opacity:.12g}"' if opacity < 1 else ""
    return (
        f'<shape type="ellipse" topLeftX="{_sx(cx - r):.1f}" topLeftY="{_sy(cy - r):.1f}" '
        f'width="{_sw(r * 2):.1f}" height="{_sh(r * 2):.1f}"{alpha}>'
        f'<fill><fillColor color="{fill_c}"/></fill>'
        f'<border color="{stroke_c}" width="{border_w}"{_border_attrs_from_svg(tag) if border_w else ""}/>'
        f"</shape>"
    )


def convert_ellipse(tag: str, all_defs: str = "") -> str:
    """ellipse → shape ellipse (支持 rotate transform); filter 走 embed."""
    cx = _get_num(tag, "cx")
    cy = _get_num(tag, "cy")
    rx = _get_num(tag, "rx")
    ry = _get_num(tag, "ry")
    fill = _get_attr(tag, "fill") or "none"
    stroke = _get_attr(tag, "stroke") or ""
    transform = _get_attr(tag, "transform") or ""
    filter_id = _get_attr(tag, "filter") or ""
    if rx <= 0 or ry <= 0:
        return ""
    stroke_w = _get_num(tag, "stroke-width", 1)
    opacity = _get_num(tag, "opacity", 1)
    # 带 filter 时走 embed 保留视觉 · native shape 不支持 filter
    if filter_id:
        buf = max(2.0, stroke_w / 2 + 2.0)
        return _wrap_svg_embed(
            tag,
            cx - rx - buf,
            cy - ry - buf,
            rx * 2 + buf * 2,
            ry * 2 + buf * 2,
            defs=_minimize_defs_for(tag, all_defs),
        )
    fill_c = (
        _resolve_paint_color(fill, all_defs, _get_num(tag, "fill-opacity", 1))
        if not _is_transparent_fill(fill)
        else "rgba(0,0,0,0)"
    )
    stroke_c = (
        _resolve_paint_color(stroke, all_defs, _get_num(tag, "stroke-opacity", 1))
        if not _is_transparent_fill(stroke)
        else "rgba(0,0,0,0)"
    )
    border_w = _stroke_border_width(stroke_w) if not _is_transparent_fill(stroke) else 0
    op_attr = f' alpha="{opacity}"' if opacity < 1 else ""
    rot_attr = ""
    if "rotate" in transform:
        m_rot = re.search(r"rotate\(\s*(-?\d+\.?\d*)", transform)
        if m_rot:
            rotation = float(m_rot.group(1)) % 360
            rot_attr = f' rotation="{_format_num(rotation)}"'
    return (
        f'<shape type="ellipse" topLeftX="{_sx(cx - rx):.1f}" topLeftY="{_sy(cy - ry):.1f}" '
        f'width="{_sw(rx * 2):.1f}" height="{_sh(ry * 2):.1f}"{rot_attr}{op_attr}>'
        f'<fill><fillColor color="{fill_c}"/></fill>'
        f'<border color="{stroke_c}" width="{border_w}"{_border_attrs_from_svg(tag) if border_w else ""}/>'
        f"</shape>"
    )


def convert_polygon(tag: str, all_defs: str = "") -> str:
    """polygon → custom shape; complex gradients/effects keep an SVG embed."""
    pts_m = re.search(r'points="([^"]*)"', tag)
    if not pts_m:
        return ""
    pts = pts_m.group(1).replace(",", " ").split()
    try:
        nums = [float(p) for p in pts]
    except ValueError:
        return ""
    xs = nums[::2]
    ys = nums[1::2]
    if len(nums) < 6 or len(nums) % 2:
        return ""
    fill = _get_attr(tag, "fill") or "none"
    stroke = _get_attr(tag, "stroke") or ""
    stroke_w = _get_num(tag, "stroke-width", 1)
    opacity = _get_num(tag, "opacity", 1)
    gradient = native_linear_gradient(fill, all_defs, _get_num(tag, "fill-opacity", 1))
    unsupported = any(
        _get_attr(tag, key)
        for key in (
            "filter",
            "transform",
            "style",
            "clip-path",
            "mask",
            "vector-effect",
            "stroke-dasharray",
            "marker-start",
            "marker-mid",
            "marker-end",
            "fill-rule",
            "color-interpolation",
        )
    )
    if gradient is not None and "url(" not in stroke and not unsupported:
        native = _custom_shape_from_points(
            list(zip(xs, ys)),
            fill=gradient,
            stroke=_apply_opacity(stroke, _get_num(tag, "stroke-opacity", 1)) if stroke else "",
            stroke_w=stroke_w,
            close=True,
            border_attrs=_border_attrs_from_svg(tag),
        )
        # Whole-object opacity must not be distributed across fill and stroke.
        if opacity < 1:
            native = native.replace("<shape ", f'<shape alpha="{opacity:.12g}" ', 1)
        return native
    if "url(" not in fill and "url(" not in stroke:
        return _custom_shape_from_points(
            list(zip(xs, ys)),
            fill=_apply_opacity(fill, _get_num(tag, "fill-opacity", 1)),
            stroke=_apply_opacity(stroke, _get_num(tag, "stroke-opacity", 1)) if stroke else "",
            stroke_w=stroke_w,
            opacity=opacity,
            close=True,
        )
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    buf = 2
    return _wrap_svg_embed(
        tag,
        x_min - buf,
        y_min - buf,
        (x_max - x_min) + buf * 2,
        (y_max - y_min) + buf * 2,
        defs=all_defs,
    )


def convert_polyline(tag: str, all_defs: str = "") -> str:
    """polyline → line 链; gradient stroke 走 embed 保 fidelity."""
    pts_m = re.search(r'points="([^"]*)"', tag)
    if not pts_m:
        return ""
    pts = pts_m.group(1).replace(",", " ").split()
    try:
        nums = [float(p) for p in pts]
    except ValueError:
        nums = []
    xs = nums[::2]
    ys = nums[1::2]
    stroke_attr = _get_attr(tag, "stroke") or ""
    fill = _get_attr(tag, "fill") or "none"
    if fill not in ("none", "transparent") and len(xs) >= 2 and len(xs) == len(ys):
        d = "M " + " L ".join(f"{x} {y}" for x, y in zip(xs, ys))
        native = _custom_shape_from_svg_path(
            d,
            tag,
            fill=fill,
            stroke=stroke_attr,
            stroke_w=_get_num(tag, "stroke-width", 1),
            opacity=_get_num(tag, "opacity", 1),
            all_defs=all_defs,
            border_attrs=_border_attrs_from_svg(tag),
        )
        if native:
            return native

    # gradient stroke → embed (slide-native line 不支持 url(...) stroke)
    if "url(" in stroke_attr and xs and ys:
        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)
        buf = 2
        return _wrap_svg_embed(
            tag,
            x_min - buf,
            y_min - buf,
            (x_max - x_min) + buf * 2,
            (y_max - y_min) + buf * 2,
            defs=all_defs,
        )
    if len(xs) >= 2 and len(ys) >= 2:
        stroke = stroke_attr or "#000"
        stroke_w = _get_num(tag, "stroke-width", 1)
        opacity = _get_num(tag, "opacity", 1)
        stroke_opacity = _get_num(tag, "stroke-opacity", 1)
        n_pts = min(len(xs), len(ys))
        return _stroked_points_xml(
            list(zip(xs[:n_pts], ys[:n_pts])),
            tag,
            stroke,
            stroke_w,
            opacity * stroke_opacity,
        )
    return ""


# One fidelity gate for public single-element calls and main entry-point calls.
from ._effects import faithful

convert_rect = faithful(convert_rect)
convert_circle = faithful(convert_circle)
convert_ellipse = faithful(convert_ellipse)
convert_line = faithful(convert_line)
convert_path = faithful(convert_path)
convert_polygon = faithful(convert_polygon)
convert_polyline = faithful(convert_polyline)
convert_text = faithful(convert_text)
