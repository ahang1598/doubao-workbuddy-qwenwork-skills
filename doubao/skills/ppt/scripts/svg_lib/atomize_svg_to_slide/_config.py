"""模块级配置 · 所有 SVG → slide 转换参数."""

from __future__ import annotations


# 默认映射: SVG 900×336 → slide (30, 102) 位置, 尺寸 900×336 (1:1)
_CFG = {
    "svg_w": 900.0,
    "svg_h": 336.0,
    # slide 落点 + 尺寸 (目标坐标空间)
    "slide_x0": 30.0,
    "slide_y0": 102.0,
    "slide_w": 900.0,
    "slide_h": 336.0,
    # 是否丢弃 SVG 里覆盖 ≥90% viewBox 的画布底色 rect
    "drop_bg": False,
    "font_metrics": "auto",
    # Text with no font-family, or a generic sans stack (sans-serif/system-ui), gets the same CJK sans font chart_split
    # uses, so drawing text (incl. Greek γ ν Δ σ and math glyphs) matches charts.
    "default_font_family": "思源黑体",
    # 小字过滤: 拆后 slide-font < 阈值 且 颜色中灰 → 跳过 (消除小灰噪点)
    "drop_micro_gray_below": 0,
    # 一刀切: 拆后 slide-font < 阈值 一律跳过 (不管颜色)
    "drop_text_below": 0,
    # slide 空间最小字号硬 clamp: 缩放后 < 该值抬到该值.
    # 普通文本/富文本基字号仍有6pt硬底；10为默认，0只取消配置下限。
    "min_slide_font_size": 10,
    # Preserve authored punctuation and mathematical continuation. Callers that
    # explicitly need the legacy character guard can still choose "fail".
    "ellipsis_policy": "preserve",
    # subtitle 松绑: SVG 层小灰字 (fs <= threshold + 中灰色) 允许 clamp 到更小 slide 字号,
    # 用于建立"主标 / 副标"字号分层. 0 = 关 (所有 text 走 min_slide_font_size).
    "subtitle_svg_threshold": 0,
    "min_slide_font_size_subtitle": 8,
    # >0 时 · 强制 subtitle slide-font ≤ 该值 (与自然缩放取小)
    "subtitle_slide_font_cap": 0,
    "subtitle_letter_spacing": 0.0,
    # 强制覆盖 subtitle 颜色, 空字符串 = 保持原色
    "subtitle_color_override": "",
}


def set_mapping(svg_w: float, svg_h: float, slide_x0: float, slide_y0: float, slide_w: float, slide_h: float) -> None:
    """配置 SVG → slide 坐标映射."""
    _CFG.update(
        svg_w=svg_w,
        svg_h=svg_h,
        slide_x0=slide_x0,
        slide_y0=slide_y0,
        slide_w=slide_w,
        slide_h=slide_h,
    )


def set_drop_background(flag: bool) -> None:
    """开启后 · 覆盖 viewBox ≥ 90% 的 canvas 底色 rect 会被跳过, 让 SVG 透明融入 slide."""
    _CFG["drop_bg"] = flag


def set_drop_micro_gray(fs_threshold: int) -> None:
    """字号 < fs_threshold 且颜色为中灰的 text 直接跳过, 消除缩放后的灰噪点标签."""
    _CFG["drop_micro_gray_below"] = int(fs_threshold)


def set_drop_text_below(fs_threshold: int) -> None:
    """字号 < fs_threshold 的所有 text 一律跳过 (不管颜色), 消除小字噪点."""
    _CFG["drop_text_below"] = int(fs_threshold)


def set_min_slide_font_size(min_fs: int) -> None:
    """强制 slide-space 最小字号, 避免 anisotropic 缩放导致 text 挤到 <10pt 撞成一坨."""
    _CFG["min_slide_font_size"] = int(min_fs)


def set_subtitle_relax(
    svg_threshold: int = 12,
    min_slide_font: int = 8,
    slide_font_cap: int = 0,
    letter_spacing: float = 0.5,
    color_override: str = "",
) -> None:
    """subtitle 字号松绑, 让 SVG 里的小灰字保持"次要说明"层级."""
    _CFG["subtitle_svg_threshold"] = int(svg_threshold)
    _CFG["min_slide_font_size_subtitle"] = int(min_slide_font)
    _CFG["subtitle_slide_font_cap"] = int(slide_font_cap)
    _CFG["subtitle_letter_spacing"] = float(letter_spacing)
    _CFG["subtitle_color_override"] = color_override


def set_font_metrics(mode: str = "auto") -> None:
    """auto uses cached font metrics."""
    if mode not in ("auto", "legacy"):
        raise ValueError("font metrics must be auto or legacy")
    _CFG["font_metrics"] = mode
