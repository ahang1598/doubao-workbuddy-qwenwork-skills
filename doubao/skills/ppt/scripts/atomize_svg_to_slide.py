"""HERO LARK v4 · 原子化拆分 · 每元素独立可选/拖/删.

从 hero_embed SVG 逐 tag parse:
- <rect> 实色 fill → slide-native shape rect (可编辑)
- <rect> halo (fill=none + opacity<0.6) → 独立小 embed (保 filter)
- <line> 直线 → slide-native line (可编辑)
- <text> → slide-native text (可编辑)
- <path> 直线/折线 → slide-native line (可编辑)
- <path> 曲线/填充形状 → 独立小 embed (保 SVG bezier)
- <polygon> → 独立小 embed

每小 embed 位置严格 = SVG viewBox 对应 slide 坐标 (DX=30, DY=102)
每小 embed viewBox 就是元素的 bbox · 让 slide 里 embed 尺寸严格 = bbox

不用 defs · 每小 embed 只含 1 个 path/rect · 但可能需要引用 gradient/filter.
简化: 每 path 用 inline stroke color + linear rgb (不 gradient) 近似原视觉.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional, Tuple


# ═════════════════════════════════════════════════════════════════
# 坐标映射: SVG viewBox → slide 区域 · 通过 module 级 CONFIG 可配置
# ═════════════════════════════════════════════════════════════════

# 默认: hero_embed 900×336 → slide (30, 102) 大小 900×336 (1:1)
_CFG = {
    "svg_w": 900.0,
    "svg_h": 336.0,
    "slide_x0": 30.0,
    "slide_y0": 102.0,
    "slide_w": 900.0,
    "slide_h": 336.0,
    "drop_bg": False,
    "drop_micro_gray_below": 0,   # >0 时 · 跳过字号 < 该值 且 颜色为中灰的 text (保守版 · 老参数)
    "drop_text_below": 0,          # >0 时 · 跳过字号 < 该值 的所有 text (激进版 · 一刀切)
    # slide 最小字号硬 clamp · 避免 slide_h 非等比缩放后 text 出现 <10pt 挤成一坨.
    # 6 = 与老 max(6, ...) 一致 · 10 = 推荐值 (audit 观察 <10pt 就撞) · 0 = 关.
    "min_slide_font_size": 10,
    # Bucket C hard red-line: 拒绝 `…` 输出 · 出现即报错 · "warn" = 只打警告不 raise
    "ellipsis_policy": "fail",
    # Bucket G (2026-09-13): subtitle 松绑
    # SVG-space 原字号 < subtitle_svg_threshold 且 颜色为中灰的 text
    #   → 允许 clamp 到 min_slide_font_size_subtitle (可 <10pt · 默认 8pt)
    #   → 可选 subtitle_slide_font_cap 主动压 slide-font 到该值以下 · 建立分层
    #   → 加 letterSpacing 让字组透气 · 保持信息量
    # 0 = 关闭 · 保持老 min_slide_font_size=10 行为
    "subtitle_svg_threshold": 0,
    "min_slide_font_size_subtitle": 8,
    "subtitle_slide_font_cap": 0,   # >0 时 · 强制 slide-font ≤ 该值 (与自然缩放取小)
    "subtitle_letter_spacing": 0.0,
    # 允许指定 subtitle 显色 (为空 = 保持原色)
    "subtitle_color_override": "",
}

DX = 30   # legacy · 保留
DY = 102


def set_mapping(svg_w: float, svg_h: float,
                slide_x0: float, slide_y0: float,
                slide_w: float, slide_h: float) -> None:
    """配置 SVG → slide 坐标映射."""
    _CFG.update(
        svg_w=svg_w, svg_h=svg_h,
        slide_x0=slide_x0, slide_y0=slide_y0,
        slide_w=slide_w, slide_h=slide_h,
    )


def set_drop_background(flag: bool) -> None:
    """开启后 · 覆盖 viewBox ≥ 90% 的 canvas 底色 rect 会被跳过 · 让关系图透明融入 slide."""
    _CFG["drop_bg"] = flag


def set_drop_micro_gray(fs_threshold: int) -> None:
    """字号 < fs_threshold 且颜色为中灰的 text 直接跳过 · 消除缩放后的灰噪点标签.
    传 0 关闭 (默认). 推荐值 8 (拆完后 fs≤7 的灰字通常是原 SVG eyebrow 缩过头)."""
    _CFG["drop_micro_gray_below"] = int(fs_threshold)


def set_drop_text_below(fs_threshold: int) -> None:
    """字号 < fs_threshold 的所有 text 一律跳过 (不管颜色) · 消除小字噪点.
    传 0 关闭. 推荐值 8-9 (激进 · 干净利落)."""
    _CFG["drop_text_below"] = int(fs_threshold)


def set_min_slide_font_size(min_fs: int) -> None:
    """强制 slide-space 最小字号 · 避免 slide_h 非等比缩放导致 text < 10pt 挤成一坨.

    audit (2026-09-11) 发现 · caller 传 slide_h=420 (viewBox 620-680pt) 时 · Y-scale ≈ 0.61
    · _sf() 只按 slide_w/svg_w 算 · 但 line-height 跟 svg_h 缩 · 导致 label 撞.
    保守修复: clamp slide-space font-size 到 >= min_fs · 不改整体 aspect ratio · 兼容 legacy caller.

    Args:
        min_fs: 硬底 · slide-space pt · 传 0 关闭 · 默认 10.
    """
    _CFG["min_slide_font_size"] = int(min_fs)


def set_subtitle_relax(
    svg_threshold: int = 12,
    min_slide_font: int = 8,
    slide_font_cap: int = 0,
    letter_spacing: float = 0.5,
    color_override: str = "",
) -> None:
    """Bucket G · subtitle 松绑.

    原设计里 SVG 小字 (fs<12 + 中灰色) 是次要说明 · atomize 强制 clamp 到 10pt 后
    与主标同量级 · 视觉挤压。本函数允许该类字 clamp 到更小字号 · 并加 letterSpacing 透气。

    Args:
        svg_threshold: SVG-空间原字号 <= 该值 且 颜色中灰 · 视为 subtitle. 0=关.
        min_slide_font: subtitle 的 slide 最小字号 · 默认 8pt (低于主标 10pt).
        slide_font_cap: >0 时 · 强制 subtitle slide-font ≤ 该值 (与自然缩放取小值) ·
            用于 subtitle 自然缩放后仍与主标接近的情况 · 建立视觉层级. 0=关.
        letter_spacing: subtitle 加 letterSpacing (px) · 0=关.
        color_override: 强制覆盖 subtitle 颜色 (如 "rgba(156,163,175,1)"). 空=保持原色.
    """
    _CFG["subtitle_svg_threshold"] = int(svg_threshold)
    _CFG["min_slide_font_size_subtitle"] = int(min_slide_font)
    _CFG["subtitle_slide_font_cap"] = int(slide_font_cap)
    _CFG["subtitle_letter_spacing"] = float(letter_spacing)
    _CFG["subtitle_color_override"] = color_override


def _is_muted_gray(color: str) -> bool:
    """判断 rgba/rgb 颜色是否是中灰调 (R≈G≈B 且明度介于 80-200)."""
    if not color:
        return False
    m = re.match(r'rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)', color)
    if not m:
        return False
    r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
    # 中灰: 三通道差 ≤ 25 · 明度 80-200 (太黑=正文/太白=底纹)
    max_diff = max(abs(r - g), abs(g - b), abs(r - b))
    avg = (r + g + b) / 3
    return max_diff <= 25 and 80 <= avg <= 200


def _sx(x: float) -> float:
    return _CFG["slide_x0"] + x * _CFG["slide_w"] / _CFG["svg_w"]


def _sy(y: float) -> float:
    return _CFG["slide_y0"] + y * _CFG["slide_h"] / _CFG["svg_h"]


def _sw(w: float) -> float:
    return w * _CFG["slide_w"] / _CFG["svg_w"]


def _sh(h: float) -> float:
    return h * _CFG["slide_h"] / _CFG["svg_h"]


def _sf(font_size: float) -> float:
    """字号也要按缩放比例调整 · 用 svg_w 的比例."""
    scale = _CFG["slide_w"] / _CFG["svg_w"]
    return font_size * scale


# R8 (2026-09-13) · 各向异性 (anisotropy) 感知的字号缩放
# 老 `_sf()` 只用 slide_w/svg_w (x 方向) · 若 y 方向缩得更狠 (x=0.669 y=0.239)
# `slide_font * 1.6` 强制 shape 高度 · 大于 svg y-line-gap × y_scale · 相邻 shape 撞
# 修法: 只当 y_scale < x_scale (y 方向压缩重) 且 anisotropy 显著时 · 用 sqrt(x_scale × y_scale)
# · 保持读性下限 (跟 x 完全同步会太小 · 跟 y 完全同步反过来 x 方向 wrap)
# · 1:1 或轻微 anisotropy (< 1.43) 保持老行为 · 老 caller 无 regression
# · 反向 anisotropy (x<y) 不触发 · 保留 x-only 保证 x 方向 fit
def _font_scale_ratio() -> float:
    """返回字号 SVG→slide 的缩放比 · 各向异性感知.

    仅当 y_scale 明显小于 x_scale (aspect ratio 被压扁 · y-line-gap 空间紧张) 时启用.
    反向 anisotropy (y_scale > x_scale · 如 embed 竖高瘦) 保持 x-scale · 避免文字 wrap.
    """
    import math
    sx = _CFG["slide_w"] / max(1.0, _CFG["svg_w"])
    sy = _CFG["slide_h"] / max(1.0, _CFG["svg_h"])
    # 只在 slide-space 缩小 (至少一方向 < 1.0) 且 y 显著小于 x 时启用
    # threshold 0.7: y_scale < 0.7 * x_scale (aniso > 1.43) · 兼容老 aniso ≤ 1.4 caller
    if sx < 1.0 and sy < 0.7 * sx:
        return math.sqrt(sx * sy)
    return sx


def s2l_x(x: float) -> float:
    return _sx(x)


def s2l_y(y: float) -> float:
    return _sy(y)


# ═════════════════════════════════════════════════════════════════
# helpers
# ═════════════════════════════════════════════════════════════════

def _get_attr(tag: str, name: str) -> Optional[str]:
    m = re.search(rf'{name}="([^"]*)"', tag)
    return m.group(1) if m else None


def _get_num(tag: str, name: str, default: float = 0) -> float:
    v = _get_attr(tag, name)
    try:
        return float(v) if v else default
    except (TypeError, ValueError):
        return default


def _normalize_color(color: str) -> str:
    """把 #RRGGBB / rgba(a,b,c) / rgba(a,b,c,d) 都转成 slide 可用 rgba(a,b,c,d)."""
    if not color:
        return "rgba(0,0,0,1)"
    c = color.strip()
    if c.startswith("#"):
        h = c.lstrip("#")
        if len(h) == 6:
            r, g, b = int(h[:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            return f"rgb({r},{g},{b})"
    return c   # rgba(...) 直接用


def _extract_tspan_text(text_tag: str) -> str:
    """从 <text>...</text> 里抓出 innerText · 忽略 <tspan> 结构.

    **重要**: 返回的是**原始 SVG 文本** (已经是 escape 过的 · 如 &amp;/&lt;/&gt;).
    调用者不要再 escape · 否则重复转义.
    """
    # 去掉所有子标签
    inner = re.sub(r'<[^>]+>', '', text_tag)
    return inner.strip()


def _unescape_svg_entities(s: str) -> str:
    """把 SVG 里的 XML entity 解回原字符 (&amp; → & · &lt; → < · &gt; → >)."""
    return s.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&apos;", "'")


def _escape_xml(s: str) -> str:
    """转义为 XML-safe 字符 (原字符 → &amp; &lt; &gt;)."""
    # 先把可能存在的 & 转 &amp; · 但避免 &amp; → &amp;amp; · 用 tmp placeholder
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ═════════════════════════════════════════════════════════════════
# 拆一个 tag 成一个 slide XML fragment
# ═════════════════════════════════════════════════════════════════

def convert_rect(tag: str, all_defs: str = "") -> str:
    """rect → slide-native shape 或独立 embed."""
    x = _get_num(tag, 'x')
    y = _get_num(tag, 'y')
    w = _get_num(tag, 'width')
    h = _get_num(tag, 'height')
    if w < 1 or h < 1:
        return ""
    fill = _get_attr(tag, 'fill') or 'none'
    stroke = _get_attr(tag, 'stroke') or ''
    stroke_w = _get_num(tag, 'stroke-width', 1)
    opacity = _get_num(tag, 'opacity', 1)
    rx = _get_num(tag, 'rx', 0)
    # drop background: 覆盖 viewBox ≥90% 的实色 rect (无 stroke) 视作 canvas 底色 · 跳过
    if _CFG.get("drop_bg") and fill != 'none' and not stroke:
        coverage = (w * h) / (_CFG["svg_w"] * _CFG["svg_h"])
        if coverage >= 0.9:
            return ""

    # filter/gradient 在可编辑模式下降级为 native shape；filter 阴影丢弃，gradient 尽量转 CSS gradient。
    slide_x = s2l_x(x)
    slide_y = s2l_y(y)
    slide_w_val = _sw(w)
    slide_h_val = _sh(h)
    fill_color = _resolve_paint_color(fill, all_defs) if not _is_transparent_fill(fill) else 'rgba(0,0,0,0)'
    border_color = _resolve_paint_color(stroke, all_defs) if not _is_transparent_fill(stroke) else 'rgba(0,0,0,0)'
    border_w = int(stroke_w) if stroke_w >= 1 and not _is_transparent_fill(stroke) else 0
    rx_scaled = int(rx * _CFG["slide_w"] / _CFG["svg_w"]) if rx else 0
    rx_attr = f' presetHandlers="{rx_scaled}"' if rx_scaled else ''
    op_attr = f' alpha="{opacity}"' if opacity < 1 else ''
    return (
        f'<shape type="rect" topLeftX="{slide_x:.1f}" topLeftY="{slide_y:.1f}" '
        f'width="{slide_w_val:.1f}" height="{slide_h_val:.1f}"{rx_attr}{op_attr}>'
        f'<fill><fillColor color="{fill_color}"/></fill>'
        f'<border color="{border_color}" width="{border_w}"/>'
        f'</shape>'
    )


def _svg_dash_to_sml(dash: str, line_cap: str = "") -> str:
    """Map SVG stroke-dasharray to the closest Slides dashArray enum."""
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
    """Return a rough native endpoint decoration kind from marker url(#...)."""
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
    """SVG stroke widths scale with the rendered SVG geometry."""
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
    return (" " + " ".join(attrs)) if attrs else ""


def _native_arrow_xml(marker_kind: str, tag_name: str, stroke_w: float) -> str:
    if not marker_kind or marker_kind == "tbar":
        return ""
    scale = _arrow_scale(stroke_w)
    return (
        f'<{tag_name} type="{marker_kind}" '
        f'widthScale="{scale}" heightScale="{scale}"/>'
    )


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
    """Fallback endpoint marker for custom-path connectors."""
    if not marker_kind:
        return ""
    import math

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
    return _custom_shape_from_points(
        points,
        fill=stroke,
        stroke="none",
        stroke_w=0,
        opacity=opacity,
        close=True,
    )


def convert_line(tag: str) -> str:
    """line → slide-native line."""
    x1 = _get_num(tag, 'x1')
    y1 = _get_num(tag, 'y1')
    x2 = _get_num(tag, 'x2')
    y2 = _get_num(tag, 'y2')
    stroke = _get_attr(tag, 'stroke') or '#000'
    stroke_w = _get_num(tag, 'stroke-width', 1)
    opacity = _get_num(tag, 'opacity', 1)
    stroke_opacity = _get_num(tag, 'stroke-opacity', 1)
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
            x1, y1, x2, y2,
            marker_kind="tbar",
            stroke=stroke,
            stroke_w=stroke_w,
            opacity=opacity * stroke_opacity,
        )
    if marker_end == "tbar":
        line_xml += _endpoint_decoration_xml(
            x2, y2, x1, y1,
            marker_kind="tbar",
            stroke=stroke,
            stroke_w=stroke_w,
            opacity=opacity * stroke_opacity,
        )
    return line_xml


def _line_xml(x1: float, y1: float, x2: float, y2: float,
              stroke: str, stroke_w: float, opacity: float = 1,
              *, dash_array: str = "solid",
              marker_start: str = "", marker_end: str = "",
              line_cap: str = "", line_join: str = "") -> str:
    """Build a slide-native line in current SVG-to-slide mapping."""
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
        f'{start_arrow}{end_arrow}'
        f'</line>'
    )


def _format_num(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _apply_opacity(color: str, opacity: float) -> str:
    normalized = _normalize_color(color)
    if opacity < 1:
        rgb_m = re.match(r"rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", normalized)
        if rgb_m:
            return f"rgba({rgb_m.group(1)},{rgb_m.group(2)},{rgb_m.group(3)},{opacity:.2f})"
        rgba_m = re.match(r"rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([0-9.]+)\s*\)", normalized)
        if rgba_m:
            alpha = max(0.0, min(1.0, float(rgba_m.group(4)) * opacity))
            return f"rgba({rgba_m.group(1)},{rgba_m.group(2)},{rgba_m.group(3)},{alpha:.3f})"
    return normalized


def _color_with_alpha(color: str, alpha: float = 1.0) -> str:
    return _apply_opacity(color, alpha)


def _offset_to_percent(offset: str) -> int:
    value = offset.strip()
    try:
        if value.endswith("%"):
            pct = float(value[:-1])
        else:
            pct = float(value) * 100
    except ValueError:
        pct = 0
    return int(max(0, min(100, round(pct))))


def _resolve_paint_color(paint: Optional[str], all_defs: str = "", opacity: float = 1.0) -> str:
    if _is_transparent_fill(paint):
        return "rgba(0,0,0,0)"
    value = (paint or "").strip()
    url_m = re.fullmatch(r"url\(#([^)]+)\)", value)
    if not url_m:
        return _apply_opacity(value, opacity)

    if not all_defs:
        return "rgba(0,0,0,0)"
    gradient_id = re.escape(url_m.group(1))
    grad_m = re.search(
        rf'<linearGradient\b[^>]*id="{gradient_id}"[^>]*>(.*?)</linearGradient>',
        all_defs,
        flags=re.DOTALL,
    )
    if not grad_m:
        return "rgba(0,0,0,0)"
    grad_tag = grad_m.group(0)
    body = grad_m.group(1)
    x1 = _get_num(grad_tag, "x1", 0)
    y1 = _get_num(grad_tag, "y1", 0)
    x2 = _get_num(grad_tag, "x2", 1)
    y2 = _get_num(grad_tag, "y2", 0)
    import math
    angle = int(round((math.degrees(math.atan2(y2 - y1, x2 - x1)) + 90) % 360))
    stops = []
    for stop_m in re.finditer(r'<stop\b([^>]*)/?>', body):
        stop_tag = stop_m.group(1)
        stop_color = _get_attr(stop_tag, "stop-color") or "rgba(0,0,0,1)"
        stop_alpha = _get_num(stop_tag, "stop-opacity", 1.0) * opacity
        stop_offset = _offset_to_percent(_get_attr(stop_tag, "offset") or "0%")
        stops.append(f"{_color_with_alpha(stop_color, stop_alpha)} {stop_offset}%")
    if len(stops) >= 2:
        return f"linear-gradient({angle}deg,{','.join(stops)})"
    if len(stops) == 1:
        return stops[0].rsplit(" ", 1)[0]
    return "rgba(0,0,0,0)"


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
    """Sample one SVG elliptical arc command into absolute points."""
    import math

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
    mapped = [(s2l_x(x), s2l_y(y)) for x, y in points]
    xs = [x for x, _ in mapped]
    ys = [y for _, y in mapped]
    x0, y0 = min(xs), min(ys)
    w = max(xs) - x0
    h = max(ys) - y0
    if w <= 0 or h <= 0:
        return ""
    path_parts = [f"M {_format_num(mapped[0][0] - x0)} {_format_num(mapped[0][1] - y0)}"]
    for x, y in mapped[1:]:
        path_parts.append(f"L {_format_num(x - x0)} {_format_num(y - y0)}")
    if close:
        path_parts.append("Z")
    fill_color = _resolve_paint_color(fill, all_defs, opacity) if fill and not _is_transparent_fill(fill) else "rgba(0,0,0,0)"
    border_color = _resolve_paint_color(stroke, all_defs, opacity) if stroke and not _is_transparent_fill(stroke) else "rgba(0,0,0,0)"
    border_w = _stroke_border_width(stroke_w) if border_color != "rgba(0,0,0,0)" else 0
    return (
        f'<shape type="custom" topLeftX="{_format_num(x0)}" topLeftY="{_format_num(y0)}" '
        f'width="{_format_num(max(w, 0.1))}" height="{_format_num(max(h, 0.1))}" '
        f'path="{" ".join(path_parts)}">'
        f'<fill><fillColor color="{fill_color}"/></fill>'
        f'<border color="{border_color}" width="{border_w}"{border_attrs}/>'
        f'</shape>'
    )


def _svg_path_to_local_custom_path(
    d: str,
    *,
    origin_x: float,
    origin_y: float,
) -> Optional[Tuple[str, Tuple[float, float], Tuple[float, float], Tuple[float, float], Tuple[float, float]]]:
    """Convert an SVG path to a slide-custom local path without flattening curves.

    Returns (path, start, start_ref, end, end_ref), all in original SVG space for
    marker orientation. Coordinates in the returned path are slide-space local to
    the custom shape's top-left. Unsupported or malformed commands return None.
    """
    tokens = re.findall(r"[MmLlHhVvCcSsQqTtAaZz]|-?\d*\.?\d+(?:e[-+]?\d+)?", d)
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
                        x1 += cx; y1 += cy; x2 += cx; y2 += cy; x3 += cx; y3 += cy
                    path_parts.append(
                        f"C {local_x(x1)} {local_y(y1)} "
                        f"{local_x(x2)} {local_y(y2)} {local_x(x3)} {local_y(y3)}"
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
                        x2 += cx; y2 += cy; x3 += cx; y3 += cy
                    path_parts.append(
                        f"S {local_x(x2)} {local_y(y2)} {local_x(x3)} {local_y(y3)}"
                    )
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
                        x1 += cx; y1 += cy; x2 += cx; y2 += cy
                    path_parts.append(
                        f"Q {local_x(x1)} {local_y(y1)} {local_x(x2)} {local_y(y2)}"
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
                    path_parts.append(
                        f"A {local_len_x(rx)} {local_len_y(ry)} "
                        f"{_format_num(rotation)} {large_arc} {sweep} {local_x(x)} {local_y(y)}"
                    )
                    note_segment_end(x, y, first_ref=(x, y), last_ref=(cx, cy))
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
    """Build a slide-native custom shape from an SVG path, preserving curves."""
    bbox = bbox or _parse_path_bbox(d)
    if bbox is None:
        return ""
    x_min, y_min, x_max, y_max = bbox
    buf = max(1.0, stroke_w / 2 + 1.0)
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
        _resolve_paint_color(fill, all_defs, opacity)
        if fill and not _is_transparent_fill(fill)
        else "rgba(0,0,0,0)"
    )
    border_color = (
        _resolve_paint_color(stroke, all_defs, opacity)
        if stroke and not _is_transparent_fill(stroke)
        else "rgba(0,0,0,0)"
    )
    border_w = _stroke_border_width(stroke_w) if border_color != "rgba(0,0,0,0)" else 0
    body = (
        f'<shape type="custom" topLeftX="{_format_num(_sx(x_min))}" '
        f'topLeftY="{_format_num(_sy(y_min))}" '
        f'width="{_format_num(max(_sw(w), 0.1))}" '
        f'height="{_format_num(max(_sh(h), 0.1))}" '
        f'path="{path}">'
        f'<fill><fillColor color="{fill_color}"/></fill>'
        f'<border color="{border_color}" width="{border_w}"{border_attrs}/>'
        f'</shape>'
    )
    marker_start = _marker_kind(_get_attr(tag, "marker-start") or "")
    marker_end = _marker_kind(_get_attr(tag, "marker-end") or "")
    if marker_start:
        body += _endpoint_decoration_xml(
            start_pt[0], start_pt[1], start_ref[0], start_ref[1],
            marker_kind=marker_start,
            stroke=stroke,
            stroke_w=stroke_w,
            opacity=opacity,
        )
    if marker_end:
        body += _endpoint_decoration_xml(
            end_pt[0], end_pt[1], end_ref[0], end_ref[1],
            marker_kind=marker_end,
            stroke=stroke,
            stroke_w=stroke_w,
            opacity=opacity,
        )
    return body


def _segments_to_connected_points(
    segments: List[Tuple[float, float, float, float]]
) -> Optional[List[Tuple[float, float]]]:
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


def _stroked_points_xml(points: List[Tuple[float, float]], tag: str,
                        stroke: str, stroke_w: float, opacity: float) -> str:
    if len(points) < 2:
        return ""
    marker_start = _marker_kind(_get_attr(tag, "marker-start") or "")
    marker_end = _marker_kind(_get_attr(tag, "marker-end") or "")
    if len(points) == 2:
        body = _line_xml(
            points[0][0], points[0][1], points[1][0], points[1][1],
            stroke, stroke_w, opacity,
            dash_array=_svg_dash_to_sml(_get_attr(tag, "stroke-dasharray") or "", _line_cap(tag)),
            marker_start=marker_start,
            marker_end=marker_end,
            line_cap=_line_cap(tag),
            line_join=_line_join(tag),
        )
        if marker_start == "tbar":
            body += _endpoint_decoration_xml(
                points[0][0], points[0][1],
                points[1][0], points[1][1],
                marker_kind=marker_start,
                stroke=stroke,
                stroke_w=stroke_w,
                opacity=opacity,
            )
        if marker_end == "tbar":
            body += _endpoint_decoration_xml(
                points[-1][0], points[-1][1],
                points[-2][0], points[-2][1],
                marker_kind=marker_end,
                stroke=stroke,
                stroke_w=stroke_w,
                opacity=opacity,
            )
        return body

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
            points[0][0], points[0][1],
            points[1][0], points[1][1],
            marker_kind=marker_start,
            stroke=stroke,
            stroke_w=stroke_w,
            opacity=opacity,
        )
    if marker_end:
        body += _endpoint_decoration_xml(
            points[-1][0], points[-1][1],
            points[-2][0], points[-2][1],
            marker_kind=marker_end,
            stroke=stroke,
            stroke_w=stroke_w,
            opacity=opacity,
        )
    return body


def _is_transparent_fill(fill: Optional[str]) -> bool:
    if fill is None:
        return False
    value = fill.strip().lower()
    if value in {"", "none", "transparent"}:
        return True
    rgba = re.match(r"rgba\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*([0-9.]+)\s*\)", value)
    return bool(rgba and float(rgba.group(1)) <= 0)


def _parse_stroked_path_segments(d: str) -> Optional[List[Tuple[float, float, float, float]]]:
    """Return editable line segments for stroked paths.

    Supports straight M/L/H/V commands, quadratic Q curves, cubic C curves,
    and elliptical A arcs. Curves are sampled into
    short native line segments so relation connectors remain selectable/editable
    in Slides instead of becoming small SVG embeds. Shorthand curve commands
    still return None for fidelity.
    """
    if re.search(r"[SsTt]", d):
        return None
    tokens = re.findall(r"[MmLlHhVvQqCcAaZz]|-?\d*\.?\d+(?:e[-+]?\d+)?", d)
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
                    x = (
                        mt * mt * mt * x0
                        + 3 * mt * mt * t * x1
                        + 3 * mt * t * t * x2
                        + t * t * t * x3
                    )
                    y = (
                        mt * mt * mt * y0
                        + 3 * mt * mt * t * y1
                        + 3 * mt * t * t * y2
                        + t * t * t * y3
                    )
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
    """Sample common SVG paths into points for editable custom shapes."""
    tokens = re.findall(r"[MmLlHhVvCcQqAaZz]|-?\d*\.?\d+(?:e[-+]?\d+)?", d)
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
                        x1 += cx; y1 += cy; x2 += cx; y2 += cy; x3 += cx; y3 += cy
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
                        x1 += cx; y1 += cy; x2 += cx; y2 += cy
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


def convert_text(tag: str) -> str:
    """text → slide-native shape text (可编辑). 坐标+字号+宽高全按 svg→slide 缩放."""
    x = _get_num(tag, 'x')
    y = _get_num(tag, 'y')
    raw_svg_text = _extract_tspan_text(tag)
    if not raw_svg_text:
        return ""
    plain_text = _unescape_svg_entities(raw_svg_text)
    # Bucket C fail-loud: 硬红线检测 · 一旦 preset 遗留 U+2026/U+22EF 立即报错
    # 强制所有 preset 迁移到 wrap/drop · 拒绝 `…` 输出
    _ellipsis_hits = [c for c in plain_text if c in ("…", "⋯")]
    if _ellipsis_hits and _CFG.get("ellipsis_policy", "fail") == "fail":
        raise ValueError(
            f"Bucket C hard red-line: ellipsis {_ellipsis_hits!r} in SVG text {plain_text!r}. "
            "Fix in preset (delete `+ '…'` truncation, use wrap/drop instead)."
        )
    size = _get_num(tag, 'font-size', 11)   # SVG-space font size
    fill = _get_attr(tag, 'fill') or '#1C1914'
    anchor = _get_attr(tag, 'text-anchor') or 'start'
    weight = _get_attr(tag, 'font-weight') or ''
    italic = _get_attr(tag, 'font-style') == 'italic'
    bold = weight in ('700', '800', 'bold')

    color = _normalize_color(fill)

    # 一刀切小字过滤: 拆后字号 < 阈值 → 直接跳过 (不管颜色)
    hard_thresh = _CFG.get("drop_text_below", 0)
    # min_slide_font_size 硬 clamp · 防非等比 Y-scale 导致 text 撞
    _min_font_baseline = max(6, int(_CFG.get("min_slide_font_size", 10)) or 6)
    # Bucket I (2026-09-13) 用户投诉根因: relation 图缩小 (slide_w < svg_w) 时
    # 字号被 clamp 到 min_font · 但邻居坐标已按 ratio 缩小 · 造成撞字
    # 修法: min_font 也按 ratio 缩 · 但不低于 6pt · 让字号跟随尺寸整体缩放
    # R8 (2026-09-13): 用 anisotropy 感知 ratio · 替代仅 x 方向比例
    # · 老 caller (1:1 或 aniso<1.43) 保持 x-only 行为 · 新 anisotropic caller (pathway 等) 收敛
    _sf_ratio_now = max(0.01, _font_scale_ratio())
    if _sf_ratio_now < 1.0:
        # slide 缩小 · min_font 相应缩 · 但保底 6pt (可读性下限)
        _min_font = max(6, int(round(_min_font_baseline * _sf_ratio_now)))
    else:
        _min_font = _min_font_baseline
    # Bucket G · subtitle 检测: SVG-空间 fs <= 阈值 且 颜色中灰 → 用更小的 min_font
    _subtitle_th = int(_CFG.get("subtitle_svg_threshold", 0) or 0)
    _is_subtitle = False
    if _subtitle_th > 0 and size <= _subtitle_th and _is_muted_gray(color):
        _is_subtitle = True
        _sub_baseline = max(6, int(_CFG.get("min_slide_font_size_subtitle", 8)) or 6)
        if _sf_ratio_now < 1.0:
            _min_font_for_this = max(6, int(round(_sub_baseline * _sf_ratio_now)))
        else:
            _min_font_for_this = _sub_baseline
    else:
        _min_font_for_this = _min_font
    # R8: 字号 preview 用 anisotropy 感知的 ratio (_sf_ratio_now) · 不再用 _sf(size)
    # · _sf() 只按 x_scale · 在 anisotropic 布局下 slide_font 会撑大 shape 高度撞行
    slide_size_preview = max(_min_font_for_this, int(round(size * _sf_ratio_now)))
    if hard_thresh > 0 and slide_size_preview < hard_thresh:
        return ""

    # 微灰噪点过滤: 拆后字号 < 阈值 且颜色是中灰 → 直接跳过
    micro_thresh = _CFG.get("drop_micro_gray_below", 0)
    if micro_thresh > 0:
        if slide_size_preview < micro_thresh and _is_muted_gray(color):
            return ""

    # 估算 shape 宽度 (SVG 空间 · 用原 size)
    def _char_width(c: str, sz: float) -> float:
        if ord(c) > 0x2E80:  # CJK
            return sz * 1.0
        if c.isspace():
            return sz * 0.35
        if c in '·×→↑↓←◆◈§':
            return sz * 0.7
        if c.isupper():
            return sz * 0.7
        if c.isdigit():
            return sz * 0.55
        return sz * 0.55
    # Bucket A fix R3: shape 宽度按 clamp 后 slide_font 反算 · 但反算强度加严 cap
    # R1: 无 cap · 反算到 min_font/sf · 过度放大会撞侧栏标记
    # R2: cap = size × 1.3 · 对某些宽侧栏标记无 binding
    # R3: cap = size + 2 · 对 15.5pt → 17.5pt cap < 15.56 target → cap 生效收敛
    #     对 10pt SVG → 12pt cap · 扩 shape 90% 避免 wrap · tx_taxonomy 继续 PASS
    # R8: 用 anisotropy ratio 而非 _sf() · _sf_ratio 与 _sf_ratio_now 一致
    _preview_natural = size * _sf_ratio_now
    _sf_ratio = _sf_ratio_now
    if _preview_natural < _min_font_for_this:
        _reflow_target = _min_font_for_this / _sf_ratio
        _effective_svg_size = min(size + 2.0, _reflow_target)
    else:
        _effective_svg_size = size
    est_w_svg = sum(_char_width(c, _effective_svg_size) for c in plain_text)
    # 加轻量 padding · 0.5×effective_size · 避免过宽挤邻居 (关键 for ratio<1.0)
    shape_w_svg = max(20, est_w_svg + _effective_svg_size * 0.5)   # SVG 空间宽度

    # y 校准 · SVG 空间: shape 顶边 = baseline - 0.35em - h/2
    # 2026-09-14 · shape_h 系数 1.6 → 1.0 · 让 shape bbox 严格等于 SVG 字形视觉高度
    # (无 line-height padding) · 相邻行在 preset 布局 row_h=1.2*fs 时也不撞
    # slide 端 <p> 用 verticalAlign="middle" · shape 太贴 · 字在中央
    shape_h_svg = size * 1.0
    shape_top_svg_y = y - 0.35 * size - shape_h_svg / 2

    # 按 anchor 调 shape SVG-空间 x
    if anchor == 'middle':
        shape_svg_x = x - shape_w_svg / 2
    elif anchor == 'end':
        shape_svg_x = x - shape_w_svg
    else:
        shape_svg_x = x

    # ── 转 slide 空间 ──
    slide_x = _sx(shape_svg_x)
    slide_y = _sy(shape_top_svg_y)
    slide_w_val = _sw(shape_w_svg)
    slide_h_val = _sh(shape_h_svg)
    slide_font = max(_min_font_for_this, int(round(size * _sf_ratio_now)))
    # Bucket G · subtitle 主动压 slide_font · 建立视觉分层
    if _is_subtitle:
        _sub_cap = int(_CFG.get("subtitle_slide_font_cap", 0) or 0)
        if _sub_cap > 0:
            slide_font = max(_min_font_for_this, min(slide_font, _sub_cap))
    # 若字号被 clamp 到大于自然缩放值 · 相应扩 shape 高度 · 避免 slide_h 非等比缩小下 text 撞行
    # 2026-09-14 · 与 shape_h_svg 一致 · fs*1.0 = 严格视觉字高
    min_shape_h = slide_font * 1.0
    if slide_h_val < min_shape_h:
        # 保持 y-baseline 大致对齐 · 中心向下平移
        extra = min_shape_h - slide_h_val
        slide_y -= extra / 2
        slide_h_val = min_shape_h
    # 飞书 slide 有隐性最小字号 · <8pt 时可能被放大 · 我们保底 shape 宽 = 至少能容 slide_font 尺寸
    # Bucket A fix: CJK 每字 1.0 系数 · 非 CJK 0.55 · 取 max
    def _slide_char_width(c: str, sz: float) -> float:
        if ord(c) > 0x2E80:
            return sz * 1.05  # CJK 保守放大 5%
        if c.isspace():
            return sz * 0.35
        if c in '·×→↑↓←◆◈§':
            return sz * 0.72
        if c.isupper():
            return sz * 0.72
        if c.isdigit():
            return sz * 0.60
        return sz * 0.58
    min_shape_w = sum(_slide_char_width(c, slide_font) for c in plain_text) + slide_font * 0.6
    slide_w_val = _sw(shape_w_svg)
    if slide_w_val < min_shape_w:
        slide_w_val = min_shape_w
        # 重新算 shape_svg_x 以居中/对齐
        if anchor == 'middle':
            slide_x = _sx(x) - slide_w_val / 2
        elif anchor == 'end':
            slide_x = _sx(x) - slide_w_val
        else:
            slide_x = _sx(x)
    else:
        slide_x = _sx(shape_svg_x)

    text_align = {'start': 'left', 'middle': 'center', 'end': 'right'}.get(anchor, 'left')
    bold_attr = ' bold="true"' if bold else ''
    italic_attr = ' italic="true"' if italic else ''
    slide_text = _escape_xml(plain_text)
    # Bucket G · subtitle 松绑: letterSpacing + 可选 color override
    letter_spacing_attr = ""
    if _is_subtitle:
        ls = float(_CFG.get("subtitle_letter_spacing", 0.0) or 0.0)
        if ls > 0:
            letter_spacing_attr = f' letterSpacing="{ls:g}"'
        override_color = _CFG.get("subtitle_color_override", "") or ""
        if override_color:
            color = override_color
    return (
        f'<shape type="text" topLeftX="{slide_x:.1f}" topLeftY="{slide_y:.1f}" '
        f'width="{slide_w_val:.1f}" height="{slide_h_val:.1f}">'
        f'<content fontSize="{slide_font}" color="{color}" '
        f'textAlign="{text_align}" verticalAlign="middle" wrap="false"{bold_attr}{italic_attr}{letter_spacing_attr}>'
        f'<p>{slide_text}</p></content></shape>'
    )


def _parse_path_bbox(d: str) -> Optional[Tuple[float, float, float, float]]:
    """解析 SVG path d 属性 · 返回 (x_min, y_min, x_max, y_max) 边界框.

    支持命令: M/m L/l H/h V/v C/c S/s Q/q T/t A/a Z/z
    对每个命令按参数结构提取真正的 x/y 坐标 · 跳过半径/角度/flag 参数.
    """
    # 分词: 命令字母 或 数字
    # 数字可以带 . - 或 e
    tokens = re.findall(r'[MmLlHhVvCcSsQqTtAaZz]|-?\d+\.?\d*(?:e[-+]?\d+)?', d)
    xs, ys = [], []
    cx, cy = 0.0, 0.0   # 当前点
    cmd = None
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok in "MmLlHhVvCcSsQqTtAaZz":
            cmd = tok
            i += 1
            continue
        if cmd is None:
            i += 1
            continue
        cmd_lower = cmd.lower()
        is_rel = cmd.islower()
        try:
            if cmd_lower == 'm' or cmd_lower == 'l' or cmd_lower == 't':
                x = float(tokens[i]); y = float(tokens[i+1])
                if is_rel: x += cx; y += cy
                xs.append(x); ys.append(y)
                cx, cy = x, y
                i += 2
                # M 后连续坐标当 L
                if cmd_lower == 'm':
                    cmd = 'l' if is_rel else 'L'
            elif cmd_lower == 'h':
                x = float(tokens[i])
                if is_rel: x += cx
                xs.append(x); ys.append(cy)
                cx = x
                i += 1
            elif cmd_lower == 'v':
                y = float(tokens[i])
                if is_rel: y += cy
                xs.append(cx); ys.append(y)
                cy = y
                i += 1
            elif cmd_lower == 'c':
                # 6 参数: x1 y1 x2 y2 x y (只 endpoint 和控制点算 · 简化用 endpoint + control)
                x1, y1 = float(tokens[i]), float(tokens[i+1])
                x2, y2 = float(tokens[i+2]), float(tokens[i+3])
                x, y = float(tokens[i+4]), float(tokens[i+5])
                if is_rel:
                    x1 += cx; y1 += cy; x2 += cx; y2 += cy; x += cx; y += cy
                xs.extend([x1, x2, x]); ys.extend([y1, y2, y])
                cx, cy = x, y
                i += 6
            elif cmd_lower == 's' or cmd_lower == 'q':
                # 4 参数: x2 y2 x y
                x2, y2 = float(tokens[i]), float(tokens[i+1])
                x, y = float(tokens[i+2]), float(tokens[i+3])
                if is_rel:
                    x2 += cx; y2 += cy; x += cx; y += cy
                xs.extend([x2, x]); ys.extend([y2, y])
                cx, cy = x, y
                i += 4
            elif cmd_lower == 'a':
                # 7 参数: rx ry x-axis-rotation large-arc-flag sweep-flag x y
                # arc 只经过 endpoint 到 endpoint · 弧顶最多离中点 ~ry 距离
                # 用 endpoint + 弧顶近似 (midpoint + perpendicular_offset)
                rx, ry = float(tokens[i]), float(tokens[i+1])
                sweep = int(tokens[i+4])
                x, y = float(tokens[i+5]), float(tokens[i+6])
                if is_rel: x += cx; y += cy
                # 弧顶近似: 起点终点的中点 · 上 (sweep=0) 或下 (sweep=1) 偏 ry
                mx = (cx + x) / 2
                my = (cy + y) / 2
                # 偏离方向 · 简化按 sweep 决定 (large-arc 也会影响但忽略)
                arc_apex_dy = -ry if sweep == 1 else ry
                xs.extend([x, cx, mx])
                ys.extend([y, cy, my + arc_apex_dy])
                cx, cy = x, y
                i += 7
            elif cmd_lower == 'z':
                # closepath · 无参数
                pass
            else:
                i += 1
                continue
        except (IndexError, ValueError):
            return None
    if not xs or not ys:
        return None
    return (min(xs), min(ys), max(xs), max(ys))


def _minimize_defs_for(tag: str, all_defs: str) -> str:
    """从 all_defs 里只留 tag 实际引用的 defs (filter/gradient/marker id)."""
    if not all_defs:
        return ""
    # 扫 tag 里 url(#xxx) / filter="url(#xxx)"
    used_ids = set(re.findall(r'url\(#([^)]+)\)', tag))
    if not used_ids:
        return ""
    # 从 defs 里挑出这些 id 对应的元素
    kept = []
    # 简单法: 逐个 top-level tag 扫 · 检查 id
    for m in re.finditer(r'<(filter|linearGradient|radialGradient|marker|clipPath|mask|pattern)[^>]*id="([^"]+)"[^>]*>.*?</\1>|<(filter|linearGradient|radialGradient|marker|clipPath|mask|pattern)[^>]*id="([^"]+)"[^/]*/>',
                          all_defs, re.DOTALL):
        elem = m.group(0)
        eid = m.group(2) or m.group(4)
        if eid in used_ids:
            kept.append(elem)
    if not kept:
        return ""
    return "<defs>" + "".join(kept) + "</defs>"


def convert_path(tag: str, all_defs: str = "") -> str:
    """path → 独立小 embed · 只保引用到的 defs · 减少 SVG 复杂度.

    直线 / 折线 path 优先转成 slide-native line，保证关系图连线可编辑；
    曲线 path 优先转成 slide-native custom path，保留 SVG Bézier/arc 命令，
    不再采样成短折线；无法安全转换的复杂 path 才回退小 embed。

    R6 fix (2026-09-13): 若 slide-scale (slide_w/svg_w · slide_h/svg_h) 极小
    (< 0.5 · 常见于 hero-canvas 1400×720 缩到 450×366 mindmap slot) · path
    的 stroke-width 会被同比缩到 sub-pixel · 视觉上连接线消失.
    修法: 在 inner SVG 里 rewrite path 的 stroke-width · 使其 effective
    render 值 ≥ MIN_RENDER_STROKE_PX (default 1.2 slide-px) · 保底可见性.
    该 rewrite 只影响 stroke-width · 不改路径几何 · 与所有 preset 兼容.
    """
    d = _get_attr(tag, 'd') or ""
    stroke = _get_attr(tag, 'stroke') or ''
    fill = _get_attr(tag, 'fill')
    transform = _get_attr(tag, 'transform') or ''
    filter_id = _get_attr(tag, 'filter') or ''
    stroke_w = _get_num(tag, 'stroke-width', 1)
    opacity = _get_num(tag, 'opacity', 1)
    stroke_opacity = _get_num(tag, 'stroke-opacity', 1)
    has_close = bool(re.search(r"[Zz]", d))
    has_curve = bool(re.search(r"[CcSsQqTtAa]", d))
    bbox = _parse_path_bbox(d)
    if has_curve and not transform and bbox is not None:
        curve_shape = _custom_shape_from_svg_path(
            d,
            tag,
            fill=fill or "none",
            stroke=stroke,
            stroke_w=stroke_w,
            opacity=opacity * stroke_opacity,
            all_defs=all_defs,
            bbox=bbox,
            border_attrs=_border_attrs_from_svg(tag),
        )
        if curve_shape:
            return curve_shape
    can_treat_as_stroke_path = (
        bool(stroke)
        and "url(" not in stroke
        and not transform
        and not filter_id
        and (_is_transparent_fill(fill) or (fill is None and not has_close))
        and not has_curve
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
                parts.append(_line_xml(
                    x1, y1, x2, y2, stroke, stroke_w, combined_opacity,
                    dash_array=_svg_dash_to_sml(_get_attr(tag, "stroke-dasharray") or "", _line_cap(tag)),
                    marker_start=_marker_kind(_get_attr(tag, "marker-start") or "") if idx == 0 else "",
                    marker_end=_marker_kind(_get_attr(tag, "marker-end") or "") if idx == len(segments) - 1 else "",
                    line_cap=_line_cap(tag),
                    line_join=_line_join(tag),
                ))
            return "".join(parts)
    can_treat_as_custom_path = (
        not transform
        and fill is not None
        and fill != "none"
        and "url(" not in stroke
    )
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
    # 只留 stroke-width 半径 buffer + 1px 保底 · 避免 embed bbox 比元素大很多
    buf = max(1, sw / 2 + 1)
    x_min -= buf
    y_min -= buf
    w = (x_max - x_min) + buf * 2
    h = (y_max - y_min) + buf * 2
    if w < 1 or h < 1:
        return ""
    # R6 fix: sub-pixel stroke 补偿 · SVG stroke 以 min(scale_x, scale_y) 缩放
    # (uniform stroke · aspect-preserving)
    scale_x = _CFG["slide_w"] / _CFG["svg_w"]
    scale_y = _CFG["slide_h"] / _CFG["svg_h"]
    render_scale = min(scale_x, scale_y)
    MIN_RENDER_STROKE_PX = 1.2   # 最小 slide-px stroke · 保底可见
    effective_stroke_px = sw * render_scale
    tag_fixed = tag
    if sw > 0 and effective_stroke_px < MIN_RENDER_STROKE_PX and render_scale > 0:
        # 目标 stroke = MIN_RENDER_STROKE_PX / render_scale · 让 render 后至少达标
        # 关键: 若原 stroke 比 baseline (常见 1.0) 更粗 · 相应比例放大 · 保持
        # preset 里 branch/leaf 的视觉层级 (如 leaf 1.4 vs branch 2.2 → 保 1.57×)
        base_sw = MIN_RENDER_STROKE_PX / render_scale
        BASELINE_SW = 1.4   # preset 常用最细 stroke · 与其比例作为放大基准
        ratio = sw / BASELINE_SW if sw > BASELINE_SW else 1.0
        target_sw = base_sw * ratio
        # 保留原 tag 里的 stroke-width 属性名 · 只换值
        tag_fixed = re.sub(
            r'stroke-width="[^"]*"',
            f'stroke-width="{target_sw:.2f}"',
            tag,
        )
        # 若 tag 原来没有 stroke-width · 也不硬插 (由默认 1 处理 · 上面 sw 已算过)
    # 只保 tag 实际引用的 defs · 大部分 path 无引用 · 直接不塞 defs
    minimal_defs = _minimize_defs_for(tag_fixed, all_defs)
    # embed viewBox 起点归零 · 让服务端 renderer 好处理
    # translate path 内容到 (0,0) 起 · 用 <g transform>
    inner_svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}">'
        f'{minimal_defs}'
        f'<g transform="translate({-x_min} {-y_min})">{tag_fixed}</g>'
        f'</svg>'
    )
    return (
        f'<embed topLeftX="{_sx(x_min):.1f}" topLeftY="{_sy(y_min):.1f}" '
        f'width="{_sw(w):.1f}" height="{_sh(h):.1f}">{inner_svg}</embed>'
    )


def _wrap_svg_embed(tag: str, x: float, y: float, w: float, h: float,
                     defs: str = "") -> str:
    """把一个 SVG tag 包成独立小 embed. 用于 halo / gradient rect / path.
    embed 位置和尺寸都按 svg→slide 缩放."""
    inner_svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x} {y} {w} {h}">'
        f'{defs}{tag}</svg>'
    )
    return (
        f'<embed topLeftX="{_sx(x):.1f}" topLeftY="{_sy(y):.1f}" '
        f'width="{_sw(w):.1f}" height="{_sh(h):.1f}">{inner_svg}</embed>'
    )


# ═════════════════════════════════════════════════════════════════
# 主 splitter · 逐 tag parse SVG · 输出 slide element 列表
# ═════════════════════════════════════════════════════════════════

TAG_ITER = re.compile(
    r'(<rect[^/>]*/>)|'
    r'(<line[^/>]*/>)|'
    r'(<circle[^/>]*/>)|'
    r'(<ellipse[^/>]*/>)|'
    r'(<text[^>]*>.*?</text>)|'
    r'(<path[^/>]*/>)|'
    r'(<polygon[^/>]*/>)|'
    r'(<polyline[^/>]*/>)',
    re.DOTALL
)


def atomize_svg_to_slide(svg_path: Path) -> str:
    """把一张 hero_embed SVG 原子化拆成 slide-native + N 小 embed."""
    svg_text = svg_path.read_text()
    # sanitize
    svg_text = re.sub(r'<feComponentTransfer[^>]*>.*?</feComponentTransfer>',
                       '', svg_text, flags=re.DOTALL)
    # Keep marker definitions/attributes until individual elements are converted.
    # Native line/custom conversion maps common markers to Slides arrows; SVG
    # fallback still needs the marker defs for visual fidelity.

    # 抓 <defs>
    defs_m = re.search(r'<defs>.*?</defs>', svg_text, re.DOTALL)
    defs = defs_m.group(0) if defs_m else ""

    # body = svg 内容 - <svg ...> header - </svg> - <defs>...</defs>
    # 这样 defs 前后的元素都能被 iterate
    header_m = re.match(r'<svg[^>]*>', svg_text)
    body_start = header_m.end() if header_m else 0
    body_end = svg_text.rfind('</svg>')
    body = svg_text[body_start:body_end]
    if defs_m:
        # 从 body 里移除 defs 段
        body = body.replace(defs, '', 1)

    parts: List[str] = []

    for m in TAG_ITER.finditer(body):
        tag = m.group(0)
        stripped = tag.strip()
        if stripped.startswith('<rect'):
            parts.append(convert_rect(stripped, all_defs=defs))
        elif stripped.startswith('<line'):
            parts.append(convert_line(stripped))
        elif stripped.startswith('<text'):
            parts.append(convert_text(stripped))
        elif stripped.startswith('<path'):
            parts.append(convert_path(stripped, all_defs=defs))
        elif stripped.startswith('<polygon'):
            # polygon → slide-native custom shape where possible.
            pts_m = re.search(r'points="([^"]*)"', stripped)
            if pts_m:
                pts = pts_m.group(1).replace(',', ' ').split()
                nums = [float(p) for p in pts]
                xs = nums[::2]
                ys = nums[1::2]
                if xs and ys:
                    fill = _get_attr(stripped, 'fill') or 'none'
                    stroke = _get_attr(stripped, 'stroke') or ''
                    stroke_w = _get_num(stripped, 'stroke-width', 1)
                    opacity = _get_num(stripped, 'opacity', 1)
                    if 'url(' not in fill and 'url(' not in stroke:
                        parts.append(_custom_shape_from_points(
                            list(zip(xs, ys)),
                            fill=fill,
                            stroke=stroke,
                            stroke_w=stroke_w,
                            opacity=opacity,
                            close=True,
                        ))
                    else:
                        x_min, x_max = min(xs), max(xs)
                        y_min, y_max = min(ys), max(ys)
                        buf = 2
                        parts.append(_wrap_svg_embed(
                            stripped, x_min - buf, y_min - buf,
                            (x_max - x_min) + buf * 2, (y_max - y_min) + buf * 2,
                            defs=defs,
                        ))
        elif stripped.startswith('<polyline'):
            # polyline · points="x1,y1 x2,y2 ..." · stroke-only chain (no fill)
            # 拆成 N-1 段 slide-native <line> · 每段用 polyline 的 stroke 属性
            # 若含 gradient stroke (url(...)) · fallback 走 embed 保 fidelity
            pts_m = re.search(r'points="([^"]*)"', stripped)
            if pts_m:
                pts = pts_m.group(1).replace(',', ' ').split()
                try:
                    nums = [float(p) for p in pts]
                except ValueError:
                    nums = []
                xs = nums[::2]
                ys = nums[1::2]
                stroke_attr = _get_attr(stripped, 'stroke') or ''
                # gradient stroke → embed (slide-native line 不支持 url(...) stroke)
                if 'url(' in stroke_attr and xs and ys:
                    x_min, x_max = min(xs), max(xs)
                    y_min, y_max = min(ys), max(ys)
                    buf = 2
                    parts.append(_wrap_svg_embed(
                        stripped, x_min - buf, y_min - buf,
                        (x_max - x_min) + buf * 2, (y_max - y_min) + buf * 2,
                        defs=defs,
                    ))
                elif len(xs) >= 2 and len(ys) >= 2:
                    stroke = stroke_attr or '#000'
                    stroke_w = _get_num(stripped, 'stroke-width', 1)
                    opacity = _get_num(stripped, 'opacity', 1)
                    stroke_opacity = _get_num(stripped, 'stroke-opacity', 1)
                    n_pts = min(len(xs), len(ys))
                    parts.append(_stroked_points_xml(
                        list(zip(xs[:n_pts], ys[:n_pts])),
                        stripped,
                        stroke,
                        stroke_w,
                        opacity * stroke_opacity,
                    ))
        elif stripped.startswith('<circle'):
            # circle: cx/cy/r · 转 shape ellipse
            cx = _get_num(stripped, 'cx')
            cy = _get_num(stripped, 'cy')
            r = _get_num(stripped, 'r')
            fill = _get_attr(stripped, 'fill') or 'none'
            stroke = _get_attr(stripped, 'stroke') or ''
            if 'url(' in fill:
                parts.append(_wrap_svg_embed(stripped, cx - r, cy - r, r * 2, r * 2, defs=defs))
            else:
                fill_c = _normalize_color(fill) if fill != 'none' else 'rgba(0,0,0,0)'
                stroke_c = _normalize_color(stroke) if stroke else 'rgba(0,0,0,0)'
                parts.append(
                    f'<shape type="ellipse" topLeftX="{_sx(cx-r):.1f}" topLeftY="{_sy(cy-r):.1f}" '
                    f'width="{_sw(r*2):.1f}" height="{_sh(r*2):.1f}">'
                    f'<fill><fillColor color="{fill_c}"/></fill>'
                    f'<border color="{stroke_c}" width="1"/>'
                    f'</shape>'
                )
        elif stripped.startswith('<ellipse'):
            # ellipse: cx/cy/rx/ry (± transform="rotate(...)") → slide-native shape.
            cx = _get_num(stripped, 'cx')
            cy = _get_num(stripped, 'cy')
            rx = _get_num(stripped, 'rx')
            ry = _get_num(stripped, 'ry')
            fill = _get_attr(stripped, 'fill') or 'none'
            stroke = _get_attr(stripped, 'stroke') or ''
            transform = _get_attr(stripped, 'transform') or ''
            if rx > 0 and ry > 0:
                stroke_w = _get_num(stripped, 'stroke-width', 1)
                opacity = _get_num(stripped, 'opacity', 1)
                fill_c = _resolve_paint_color(fill, defs) if not _is_transparent_fill(fill) else 'rgba(0,0,0,0)'
                stroke_c = _resolve_paint_color(stroke, defs) if not _is_transparent_fill(stroke) else 'rgba(0,0,0,0)'
                border_w = int(stroke_w) if stroke_w >= 1 and not _is_transparent_fill(stroke) else 0
                op_attr = f' alpha="{opacity}"' if opacity < 1 else ''
                rot_attr = ''
                if 'rotate' in transform:
                    m_rot = re.search(r'rotate\(\s*(-?\d+\.?\d*)', transform)
                    if m_rot:
                        rotation = float(m_rot.group(1)) % 360
                        rot_attr = f' rotation="{_format_num(rotation)}"'
                parts.append(
                    f'<shape type="ellipse" topLeftX="{_sx(cx-rx):.1f}" topLeftY="{_sy(cy-ry):.1f}" '
                    f'width="{_sw(rx*2):.1f}" height="{_sh(ry*2):.1f}"{rot_attr}{op_attr}>'
                    f'<fill><fillColor color="{fill_c}"/></fill>'
                    f'<border color="{stroke_c}" width="{border_w}"/>'
                    f'</shape>'
                )

    # 过滤空 str
    parts = [p for p in parts if p]

    # 不再 hardcode 加背景 · SVG 里的第一个 rect 就是原生底色 · atomizer 会转过去
    inner = "".join(parts)
    return (
        f'<slide xmlns="https://www.larkoffice.com/sml/2.0"><data>{inner}</data></slide>'
    )


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        # 默认: 批量跑 46 张
        svgs = sorted(Path("examples/hero_embed").glob("*.svg"))
    else:
        svgs = [Path(a) for a in sys.argv[1:]]

    out_dir = Path(".lark-slides/hero_lark_v4")
    out_dir.mkdir(parents=True, exist_ok=True)

    for svg_path in svgs:
        try:
            xml = atomize_svg_to_slide(svg_path)
            out = out_dir / f"{svg_path.stem}.xml"
            out.write_text(xml)
            n_shape = xml.count('<shape')
            n_line = xml.count('<line')
            n_embed = xml.count('<embed')
            print(f"OK · {svg_path.stem}: {len(xml)} bytes · shape={n_shape} line={n_line} embed={n_embed}")
        except Exception as e:
            print(f"FAIL · {svg_path.stem}: {e}")
