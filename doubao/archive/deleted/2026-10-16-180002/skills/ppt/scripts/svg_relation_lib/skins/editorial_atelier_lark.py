"""editorial_atelier · Lark Slides native backend

平行于 editorial_atelier.py 的 SVG primitive · 输出**飞书 slide 原生 XML** 而不是 SVG.
每个 primitive 返回 slide XML 片段字符串 · preset 拼一整页 <slide>.

飞书 slide canvas 是 960×540. hero_embed preset canvas 是 900×336.
坐标偏移: DX=30 · DY=102 · 让 900×336 body 居中于 slide.

设计原则:
- 每 chip / label / hub / line 是**独立** slide-native element (shape/line/text)
- 用户在 slide 里 · 每个都能单击选中 · 双击改字 · 拖动 · 改色
- filter/gradient/halo 装饰效果**无**（slide-native shape 不支持 SVG filter）· 用简单 fill+border 表达
- 与 editorial_atelier.py 视觉 90% 一致 · 剩下 10% 是 halo/shadow/ribbon 精细装饰的损失
"""
from __future__ import annotations

from typing import Optional


# ═════════════════════════════════════════════════════════════════
# Design tokens · 从 editorial_atelier.py 复用
# ═════════════════════════════════════════════════════════════════

HUE_HEX = {
    "rust":     "#A35832",
    "orange":   "#C87F3D",
    "magenta":  "#A63C6E",
    "blue":     "#3F6892",
    "green":    "#558045",
    "olive":    "#7A6A3A",
    "cinnamon": "#8B5A3C",
    "gold_p":   "#D9A448",
}

INK = "#1C1914"
BONE = "#F1E9DA"
GRAY_72 = "rgba(94,80,62,0.72)"
INK_82 = "rgba(28,25,20,0.82)"

FONT_SERIF = "Georgia"    # slide 平台需系统字体 · Georgia 常见
FONT_SANS = "Inter"       # Inter 可能没有 · fallback 系统
FONT_SANS_FB = "思源黑体" # 飞书默认 · 最保险
FONT_SERIF_FB = "思源宋体"

# ═════════════════════════════════════════════════════════════════
# canvas 映射: SVG 900×336 → Slide 960×540
# ═════════════════════════════════════════════════════════════════

CANVAS_W = 960
CANVAS_H = 540

# SVG body 中心 (450, 168) → slide 中心 (480, 270)
DX_DEFAULT = 30
DY_DEFAULT = 102


def s2l_x(x_svg: float, dx: float = DX_DEFAULT) -> float:
    """SVG x → slide x."""
    return x_svg + dx


def s2l_y(y_svg: float, dy: float = DY_DEFAULT) -> float:
    """SVG y → slide y."""
    return y_svg + dy


# ═════════════════════════════════════════════════════════════════
# color helpers
# ═════════════════════════════════════════════════════════════════

def hex_to_rgb(hex_color: str) -> str:
    """#RRGGBB → rgb(r,g,b) · slide color 属性用."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgb({r},{g},{b})"


def hex_to_rgba(hex_color: str, alpha: float) -> str:
    """#RRGGBB + alpha → rgba(r,g,b,a)."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha:.2f})"


def hue_rgb(hue: str) -> str:
    """hue key → rgb() string."""
    return hex_to_rgb(HUE_HEX.get(hue, HUE_HEX["rust"]))


def hue_rgba(hue: str, alpha: float) -> str:
    """hue key + alpha → rgba() string."""
    return hex_to_rgba(HUE_HEX.get(hue, HUE_HEX["rust"]), alpha)


# ═════════════════════════════════════════════════════════════════
# XML escape
# ═════════════════════════════════════════════════════════════════

def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ═════════════════════════════════════════════════════════════════
# Slide-native primitives
# ═════════════════════════════════════════════════════════════════

def chip_pill_lark(x_svg: float, y_svg: float, w: float, h: float, *,
                    label: str, hue: str = "rust",
                    dx: float = DX_DEFAULT, dy: float = DY_DEFAULT) -> str:
    """pill chip · slide-full-round-rect + text 居中."""
    x = s2l_x(x_svg, dx)
    y = s2l_y(y_svg, dy)
    c_rgb = hue_rgb(hue)
    tint = hue_rgba(hue, 0.12)
    return (
        f'<shape type="slides-full-round-rect" topLeftX="{x}" topLeftY="{y}" '
        f'width="{w}" height="{h}">'
        f'<fill><fillColor color="{tint}"/></fill>'
        f'<border color="{c_rgb}" width="1"/>'
        f'<content textType="body" fontSize="11" textAlign="center" verticalAlign="middle">'
        f'<p>{esc(label)}</p></content></shape>'
    )


def rect_card_lark(x_svg: float, y_svg: float, w: float, h: float, *,
                    title: str = "", sub: str = "",
                    hue: str = "rust", rx: int = 6,
                    fill_alpha: float = 0.14,
                    dx: float = DX_DEFAULT, dy: float = DY_DEFAULT) -> str:
    """三级 card · rect + tint fill + border + title + sub."""
    x = s2l_x(x_svg, dx)
    y = s2l_y(y_svg, dy)
    c_rgb = hue_rgb(hue)
    tint = hue_rgba(hue, fill_alpha)
    inner = ""
    if title:
        inner += f'<p><span bold="true" fontSize="12">{esc(title)}</span></p>'
    if sub:
        inner += f'<p><span fontSize="9" color="{c_rgb}">{esc(sub)}</span></p>'
    return (
        f'<shape type="rect" topLeftX="{x}" topLeftY="{y}" '
        f'width="{w}" height="{h}" presetHandlers="{rx}">'
        f'<fill><fillColor color="{tint}"/></fill>'
        f'<border color="{c_rgb}" width="1"/>'
        f'<content textType="body" textAlign="center" verticalAlign="middle">'
        f'{inner}</content></shape>'
    )


def hub_rect_lark(x_svg: float, y_svg: float, w: float, h: float, *,
                   name: str = "", kicker: str = "CORE",
                   stat: str = "", stat_note: str = "",
                   dark: bool = True,
                   dx: float = DX_DEFAULT, dy: float = DY_DEFAULT) -> str:
    """hub · 深底 rect + gold kicker + name + stat."""
    x = s2l_x(x_svg, dx)
    y = s2l_y(y_svg, dy)
    rust_rgb = hue_rgb("rust")
    gold_rgb = hue_rgb("gold_p")
    ink_rgba = hue_rgba(HUE_HEX["rust"].replace("#", "#"), 1)  # not used
    bg_color = "rgb(28,25,20)" if dark else "rgb(241,233,218)"
    text_color = "rgb(241,233,218)" if dark else "rgb(28,25,20)"
    inner_parts = []
    if kicker:
        inner_parts.append(
            f'<p><span fontSize="8" color="{gold_rgb}" bold="true">{esc(kicker)}</span></p>'
        )
    if name:
        inner_parts.append(
            f'<p><span fontSize="14" color="{text_color}" bold="true">{esc(name)}</span></p>'
        )
    if stat:
        stat_line = f'<span fontSize="12" color="{gold_rgb}" bold="true">{esc(stat)} </span>'
        if stat_note:
            stat_line += f'<span fontSize="8" color="rgba(241,233,218,0.72)" bold="true">{esc(stat_note)}</span>'
        inner_parts.append(f'<p>{stat_line}</p>')
    inner = "".join(inner_parts)
    return (
        f'<shape type="rect" topLeftX="{x}" topLeftY="{y}" '
        f'width="{w}" height="{h}" presetHandlers="8">'
        f'<fill><fillColor color="{bg_color}"/></fill>'
        f'<border color="{rust_rgb}" width="2"/>'
        f'<content textType="body" textAlign="center" verticalAlign="middle">'
        f'{inner}</content></shape>'
    )


def line_lark(x1_svg: float, y1_svg: float, x2_svg: float, y2_svg: float, *,
              hue: str = "rust", width: int = 2,
              arrow_end: bool = False, dashed: bool = False,
              dx: float = DX_DEFAULT, dy: float = DY_DEFAULT) -> str:
    """slide 原生 line · 骨干或 whisker."""
    x1 = s2l_x(x1_svg, dx)
    y1 = s2l_y(y1_svg, dy)
    x2 = s2l_x(x2_svg, dx)
    y2 = s2l_y(y2_svg, dy)
    c_rgb = hue_rgb(hue)
    arrow_attr = '<endArrow type="solid-triangle" widthScale="sm"/>' if arrow_end else ''
    # dashed 属性飞书 line 不支持 · 忽略
    return (
        f'<line startX="{x1}" startY="{y1}" endX="{x2}" endY="{y2}">'
        f'<border color="{c_rgb}" width="{width}"/>'
        f'{arrow_attr}</line>'
    )


def curve_lark(x1_svg: float, y1_svg: float, x2_svg: float, y2_svg: float, *,
               hue: str = "rust", width: int = 2,
               segments: int = 3, arrow_end: bool = False,
               dx: float = DX_DEFAULT, dy: float = DY_DEFAULT) -> str:
    """slide 原生 curved-connector · 可编辑弧线连接.

    输入起终点 (SVG 坐标) · 内部用 polyline type="curved-connectorN" 表达.
    polyline 用外接矩形 · 默认从左上到右下 · 用 flipX/flipY 换走向.

    segments: 2..5 · 曲线段数 · 越多越弯 · 默认 3.

    注意 slide 的 curved-connector 是"折角带弧"式曲线 · 不是任意 bezier ·
    但比直线 + 折线 (bent-connector) 更平滑 · 服务端可编辑拐点。
    """
    segments = max(2, min(5, segments))
    x1 = s2l_x(x1_svg, dx)
    y1 = s2l_y(y1_svg, dy)
    x2 = s2l_x(x2_svg, dx)
    y2 = s2l_y(y2_svg, dy)
    # bbox
    top_x = min(x1, x2)
    top_y = min(y1, y2)
    w = abs(x2 - x1)
    h = abs(y2 - y1)
    if w < 1: w = 1
    if h < 1: h = 1
    # flip 决定连线方向
    # default: 从 (top_x, top_y) [左上] 到 (top_x+w, top_y+h) [右下]
    # 起点在左下需 flipY · 起点在右上需 flipX · 起点在右下需 flipX+flipY
    flip_x = "true" if x1 > x2 else "false"
    flip_y = "true" if y1 > y2 else "false"
    c_rgb = hue_rgb(hue)
    arrow_attr = '<endArrow type="solid-triangle" widthScale="sm"/>' if arrow_end else ''
    flip_attrs = ""
    if flip_x == "true":
        flip_attrs += ' flipX="true"'
    if flip_y == "true":
        flip_attrs += ' flipY="true"'
    return (
        f'<polyline type="curved-connector{segments}" '
        f'topLeftX="{top_x}" topLeftY="{top_y}" '
        f'width="{w}" height="{h}"{flip_attrs}>'
        f'<border color="{c_rgb}" width="{width}"/>'
        f'{arrow_attr}</polyline>'
    )


def elbow_lark(x1_svg: float, y1_svg: float, x2_svg: float, y2_svg: float, *,
               hue: str = "rust", width: int = 2,
               segments: int = 3, arrow_end: bool = False,
               dx: float = DX_DEFAULT, dy: float = DY_DEFAULT) -> str:
    """slide 原生 bent-connector · 直角折线 · 用于 DAG edge 之类."""
    segments = max(2, min(5, segments))
    x1 = s2l_x(x1_svg, dx)
    y1 = s2l_y(y1_svg, dy)
    x2 = s2l_x(x2_svg, dx)
    y2 = s2l_y(y2_svg, dy)
    top_x = min(x1, x2)
    top_y = min(y1, y2)
    w = max(1, abs(x2 - x1))
    h = max(1, abs(y2 - y1))
    flip_attrs = ""
    if x1 > x2:
        flip_attrs += ' flipX="true"'
    if y1 > y2:
        flip_attrs += ' flipY="true"'
    c_rgb = hue_rgb(hue)
    arrow_attr = '<endArrow type="solid-triangle" widthScale="sm"/>' if arrow_end else ''
    return (
        f'<polyline type="bent-connector{segments}" '
        f'topLeftX="{top_x}" topLeftY="{top_y}" '
        f'width="{w}" height="{h}"{flip_attrs}>'
        f'<border color="{c_rgb}" width="{width}"/>'
        f'{arrow_attr}</polyline>'
    )


def text_lark(x_svg: float, y_svg: float, w: float, h: float, *,
              text: str, size: int = 11, bold: bool = False,
              italic: bool = False, color: str = INK,
              anchor: str = "left", family: str = FONT_SANS_FB,
              wrap: bool = True, auto_fit: bool = True,
              dx: float = DX_DEFAULT, dy: float = DY_DEFAULT) -> str:
    """slide 原生 text shape · 默认 wrap+autoFit 允许 shrink to fit."""
    x = s2l_x(x_svg, dx)
    y = s2l_y(y_svg, dy)
    c = color if color.startswith("rgb") else hex_to_rgb(color)
    text_align = {"left": "left", "middle": "center", "right": "right",
                   "center": "center"}.get(anchor, "left")
    attrs = f'fontSize="{size}" color="{c}" textAlign="{text_align}"'
    if bold:
        attrs += ' bold="true"'
    if italic:
        attrs += ' italic="true"'
    if wrap:
        attrs += ' wrap="true"'
    if auto_fit:
        attrs += ' autoFit="normal-auto-fit"'
    return (
        f'<shape type="text" topLeftX="{x}" topLeftY="{y}" '
        f'width="{w}" height="{h}">'
        f'<content {attrs}><p>{esc(text)}</p></content></shape>'
    )


def circle_badge_lark(cx_svg: float, cy_svg: float, r: float, *,
                       label: str = "", hue: str = "rust",
                       filled: bool = True,
                       dx: float = DX_DEFAULT, dy: float = DY_DEFAULT) -> str:
    """circle badge · numeral / P disc / kolb badge."""
    x = s2l_x(cx_svg - r, dx)
    y = s2l_y(cy_svg - r, dy)
    c_rgb = hue_rgb(hue)
    if filled:
        fill_color = c_rgb
        text_color = "rgb(241,233,218)"
    else:
        fill_color = hue_rgba(hue, 0.12)
        text_color = c_rgb
    return (
        f'<shape type="ellipse" topLeftX="{x}" topLeftY="{y}" '
        f'width="{r*2}" height="{r*2}">'
        f'<fill><fillColor color="{fill_color}"/></fill>'
        f'<border color="{c_rgb}" width="1"/>'
        f'<content textType="body" fontSize="9" textAlign="center" verticalAlign="middle" '
        f'color="{text_color}" bold="true">'
        f'<p>{esc(label)}</p></content></shape>'
    )


# ═════════════════════════════════════════════════════════════════
# 装饰底层 embed · 保留 SVG 里的 halo/hairline/background · 底层不可编辑
# ═════════════════════════════════════════════════════════════════

def embed_decoration_lark(svg_content: str, *,
                           topLeftX: float = 40, topLeftY: float = 110,
                           width: float = 880, height: float = 328) -> str:
    """把一段 SVG（装饰层）用 <embed> 塞进 slide 作为底层背景.

    自动 dedup: 移除具有完全相同 bbox 的重复 <rect> · 满足 lint bbox_overlap 规则.
    """
    svg_content = _dedup_overlapping_rects(svg_content)
    return (
        f'<embed topLeftX="{topLeftX}" topLeftY="{topLeftY}" '
        f'width="{width}" height="{height}">{svg_content}</embed>'
    )


def _dedup_overlapping_rects(svg_content: str) -> str:
    """扫描 SVG 里的 <rect> / <circle> · 移除后续 bbox 完全相同的重复 shape · 避免 lint bbox_overlap."""
    import re
    rect_pattern = re.compile(r'<rect\s+([^/>]*?)/>')
    circle_pattern = re.compile(r'<circle\s+([^/>]*?)/>')

    seen_rect = set()

    def rect_replacer(m):
        attrs = m.group(1)
        vals = {}
        for a in ('x', 'y', 'width', 'height'):
            am = re.search(rf'{a}="([^"]+)"', attrs)
            if am:
                vals[a] = am.group(1)
        if 'x' not in vals:
            return m.group(0)
        key = (vals.get('x'), vals.get('y'), vals.get('width'), vals.get('height'))
        if key in seen_rect:
            return ''
        seen_rect.add(key)
        return m.group(0)

    svg_content = rect_pattern.sub(rect_replacer, svg_content)

    seen_circle = set()

    def circle_replacer(m):
        attrs = m.group(1)
        vals = {}
        for a in ('cx', 'cy', 'r'):
            am = re.search(rf'{a}="([^"]+)"', attrs)
            if am:
                vals[a] = am.group(1)
        if 'cx' not in vals:
            return m.group(0)
        key = (vals.get('cx'), vals.get('cy'), vals.get('r'))
        if key in seen_circle:
            return ''
        seen_circle.add(key)
        return m.group(0)

    svg_content = circle_pattern.sub(circle_replacer, svg_content)

    return svg_content


def make_background_rect_lark(color: str = BONE) -> str:
    """给整页刷 cream 背景色 · slide 默认白 · 我们要 cream."""
    return (
        f'<shape type="rect" topLeftX="0" topLeftY="0" width="960" height="540">'
        f'<fill><fillColor color="{hex_to_rgb(color)}"/></fill>'
        f'<border color="{hex_to_rgb(color)}" width="0"/>'
        f'</shape>'
    )

def chrome_title_lark(title: str, subtitle: str = "",
                       encoding_right: str = "") -> str:
    """顶部 slide-native chrome · title + subtitle + top-right encoding."""
    parts = []
    parts.append(
        f'<shape type="text" topLeftX="40" topLeftY="30" width="880" height="40">'
        f'<content textType="title" fontSize="20" bold="true">'
        f'<p>{esc(title)}</p></content></shape>'
    )
    if subtitle:
        parts.append(
            f'<shape type="text" topLeftX="40" topLeftY="70" width="700" height="30">'
            f'<content fontSize="11" color="{GRAY_72}"><p>{esc(subtitle)}</p></content></shape>'
        )
    if encoding_right:
        parts.append(
            f'<shape type="text" topLeftX="740" topLeftY="70" width="180" height="30">'
            f'<content fontSize="10" color="{GRAY_72}" textAlign="right" italic="true">'
            f'<p>{esc(encoding_right)}</p></content></shape>'
        )
    return "".join(parts)


def chrome_footer_lark(read_lines: list[str], source: str = "") -> str:
    """底部 slide-native chrome · READ 段 + source.

    read_lines 单行安全长度 ~110 chars @ fontSize=9 · 若过长会因 wrap 导致 lint 报警.
    """
    parts = []
    y = 490
    parts.append(
        f'<shape type="text" topLeftX="40" topLeftY="{y}" width="80" height="14">'
        f'<content fontSize="9" color="{GRAY_72}" bold="true"><p>READ</p></content></shape>'
    )
    # 每行 gap 14 · 从 y=504 · 到 y=532 为止 · autoFit shrink to fit
    for i, line in enumerate(read_lines[:2]):
        line_y = y + 14 + i * 14
        parts.append(
            f'<shape type="text" topLeftX="40" topLeftY="{line_y}" width="600" height="14">'
            f'<content fontSize="9" color="{INK_82}" wrap="true" autoFit="normal-auto-fit"><p>{esc(line)}</p></content></shape>'
        )
    if source:
        parts.append(
            f'<shape type="text" topLeftX="650" topLeftY="510" width="270" height="20">'
            f'<content fontSize="9" color="{GRAY_72}" textAlign="right" bold="true" wrap="true" autoFit="normal-auto-fit">'
            f'<p>{esc(source)}</p></content></shape>'
        )
    return "".join(parts)


# ═════════════════════════════════════════════════════════════════
# Page wrapper
# ═════════════════════════════════════════════════════════════════

SML_NS = 'xmlns="https://www.larkoffice.com/sml/2.0"'


def wrap_slide(inner_xml: str) -> str:
    """把一堆 shape/line xml 包成完整 <slide>."""
    return f'<slide {SML_NS}><data>{inner_xml}</data></slide>'


__all__ = [
    "HUE_HEX", "INK", "BONE", "GRAY_72", "INK_82",
    "FONT_SERIF_FB", "FONT_SANS_FB",
    "s2l_x", "s2l_y", "hex_to_rgb", "hex_to_rgba", "hue_rgb", "hue_rgba", "esc",
    "chip_pill_lark", "rect_card_lark", "hub_rect_lark",
    "line_lark", "text_lark", "circle_badge_lark",
    "chrome_title_lark", "chrome_footer_lark",
    "wrap_slide", "DX_DEFAULT", "DY_DEFAULT",
]
