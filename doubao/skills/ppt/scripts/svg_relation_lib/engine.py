"""
SVG generator engine · Pattern base + SVG helpers

每个 pattern 继承 Pattern，实现 .render_svg(data, palette) 返回 SVG 字符串（900×400 viewBox）。
上层 caller 拿到 SVG 后可以用 rsvg-convert 转 PNG，或直接嵌入 <img src="@./path.png"/>。
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, List, Tuple
import math
from .palettes import Palette


# ═════════════════════════════════════════════════════════════════
# SVG 尺寸约定
# ═════════════════════════════════════════════════════════════════
CANVAS_W = 900
CANVAS_H = 400


# ═════════════════════════════════════════════════════════════════
# XML-safe escape (SVG text 内容用)
# ═════════════════════════════════════════════════════════════════
def esc(s: str) -> str:
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;"))


# ═════════════════════════════════════════════════════════════════
# SVG primitive helpers · 所有 Pattern 都可以用
# ═════════════════════════════════════════════════════════════════

def svg_wrapper(inner: str, w: int = CANVAS_W, h: int = CANVAS_H, bg: str = "#FFFFFF") -> str:
    """外层 svg + 背景矩形"""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
            f'preserveAspectRatio="xMidYMid meet">'
            f'<rect x="0" y="0" width="{w}" height="{h}" fill="{bg}"/>'
            f'{inner}'
            f'</svg>')


def text(x, y, s, *, size=12, color="#1E2028", family="sans-serif",
         bold=False, italic=False, anchor="start", letter=None):
    attrs = [f'x="{x}"', f'y="{y}"', f'font-family="{family}"',
             f'font-size="{size}"', f'fill="{color}"',
             f'text-anchor="{anchor}"']
    if bold:
        attrs.append('font-weight="600"')
    if italic:
        attrs.append('font-style="italic"')
    if letter is not None:
        attrs.append(f'letter-spacing="{letter}"')
    return f'<text {" ".join(attrs)}>{esc(s)}</text>'


def line(x1, y1, x2, y2, *, color="#1E2028", w=1, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ''
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            f'stroke="{color}" stroke-width="{w}"{d}/>')


def rect(x, y, w, h, *, fill=None, stroke=None, sw=1, rx=0):
    fill_a = f' fill="{fill}"' if fill else ' fill="none"'
    stroke_a = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ''
    rx_a = f' rx="{rx}"' if rx else ''
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}"{fill_a}{stroke_a}{rx_a}/>'


def circle(cx, cy, r, *, fill=None, stroke=None, sw=1):
    fill_a = f' fill="{fill}"' if fill else ' fill="none"'
    stroke_a = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ''
    return f'<circle cx="{cx}" cy="{cy}" r="{r}"{fill_a}{stroke_a}/>'


def polygon(pts, *, fill=None, stroke=None, sw=1):
    fill_a = f' fill="{fill}"' if fill else ' fill="none"'
    stroke_a = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ''
    ptstr = " ".join(f"{x},{y}" for x, y in pts)
    return f'<polygon points="{ptstr}"{fill_a}{stroke_a}/>'


def path(d, *, fill="none", stroke="#1E2028", sw=1, dash=None):
    dash_a = f' stroke-dasharray="{dash}"' if dash else ''
    return f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{dash_a}/>'


def arrow(x1, y1, x2, y2, *, color="#1E2028", w=1.5, head=8):
    """线段末端 polygon 箭头 · SXSD marker 不支持只能拼"""
    ang = math.atan2(y2 - y1, x2 - x1)
    hx = x2 - head * math.cos(ang)
    hy = y2 - head * math.sin(ang)
    ax1 = hx - (head/2) * math.sin(ang)
    ay1 = hy + (head/2) * math.cos(ang)
    ax2 = hx + (head/2) * math.sin(ang)
    ay2 = hy - (head/2) * math.cos(ang)
    return (line(x1, y1, x2, y2, color=color, w=w) +
            f'<polygon points="{x2},{y2} {ax1},{ay1} {ax2},{ay2}" fill="{color}"/>')


# ═════════════════════════════════════════════════════════════════
# In-figure Chrome helpers · 让 pattern 页看起来像"论文/研报里的图"
# 而不是"空骨架示意图" —— 这是专业感的核心
# ═════════════════════════════════════════════════════════════════

def figure_kicker(x, y, kicker_text, palette: Palette):
    """图上方 kicker · REVIEW · § 01 · TREATMENT MILESTONES · 建立学术/研报语境"""
    return text(x, y, kicker_text, size=9, color=palette.primary,
                family=palette.mono_family, bold=True,
                letter=palette.kicker_letter_spacing)


def figure_title(x, y, title_text, palette: Palette, size=17):
    """图内主标题 · Thirty years of Alzheimer's therapeutics · serif 加粗"""
    is_serif_bold = palette.title_style == "serif_bold"
    return text(x, y, title_text, size=size, color=palette.ink,
                family=palette.head_family if is_serif_bold else palette.body_family,
                bold=True)


def figure_caption(x, y, caption_text, palette: Palette):
    """图下 caption · Fig. 1 | Landmark approvals and pivotal trials..."""
    return text(x, y, caption_text, size=9,
                color=palette.gray, family=palette.body_family, italic=True)


def figure_source(x, y, source_text, palette: Palette):
    """图下 source line · Source: EMA/FDA registries, accessed Aug 2026"""
    return text(x, y, source_text, size=8,
                color=palette.gray, family=palette.mono_family,
                letter=1.2)


def encoding_note(x, y, note_text, palette: Palette):
    """encoding 说明 · Colour codes mechanism class · circles = approval"""
    return text(x, y, note_text, size=9,
                color=palette.gray, family=palette.body_family, italic=True)


def hairline(x1, y1, x2, y2, palette: Palette, w=1):
    """按 palette 惯例的 hairline"""
    return line(x1, y1, x2, y2, color=palette.hair, w=w)


def separator_rule(x1, y1, x2, y2, palette: Palette, w=1):
    """章节/section 之间的强 rule · 用 primary 色"""
    return line(x1, y1, x2, y2, color=palette.primary, w=w)


# ═════════════════════════════════════════════════════════════════
# Pattern base
# ═════════════════════════════════════════════════════════════════

@dataclass
class PatternResult:
    """一个 pattern 渲染出来的东西"""
    svg: str                          # 完整 SVG 字符串（含 <svg> 包裹）
    figure_title: str = ""            # 图内 title（skeleton 会读来放置）
    figure_caption: str = ""          # 图下 caption
    figure_source: str = ""           # source line
    encoding_note: str = ""           # encoding 说明


class Pattern:
    """所有 pattern 继承这个。子类实现 .render(data, palette) 返回 PatternResult。"""

    id: str = ""
    tier: str = ""     # "S" / "A" / "R"
    name: str = ""
    description: str = ""
    minimum_data_points: int = 0
    ideal_data_points: int = 0

    def render(self, data: Any, palette: Palette) -> PatternResult:
        raise NotImplementedError

    # 便捷：直接返回 SVG 字符串
    def render_svg(self, data: Any, palette: Palette) -> str:
        return self.render(data, palette).svg


# ═════════════════════════════════════════════════════════════════
# Collision helpers · 供 preset 做 atomize-safe 布局用
#
# atomize (SVG → slide-native) 拆散元素后失去 SVG paint-order + opaque-fill
# mask 语义。preset 里凡是"放个带 opaque-fill 的 pill/badge 遮住背后信息"
# 的手法，必须先跑 collision check 让 pill 落在信息空白区，否则 slide 上
# 遮层不再遮，背后 text 就暴露与 pill 叠在一起。
#
# 这里的 helpers 只做几何判断，不做定位；preset 各自维护 candidate 列表。
# 惯用 pattern：
#   pill_w, pill_h = ...
#   candidates = [(mx, my)]          # 首选点
#   candidates += [...other segments, lane_y offsets...]
#   for cx, cy in candidates:
#       if not bbox_collides_any(cx-pill_w/2, cy-pill_h/2, pill_w, pill_h,
#                                 [(e["x"], e["y"], e["w"], e["h"]) for e in ...]):
#           mx, my = cx, cy
#           break
# ═════════════════════════════════════════════════════════════════

def bbox_intersects(ax: float, ay: float, aw: float, ah: float,
                    bx: float, by: float, bw: float, bh: float,
                    pad: float = 0.0) -> bool:
    """AABB overlap · 两个矩形是否相交 (含 pad 外扩)."""
    return (ax - pad < bx + bw and ax + aw + pad > bx and
            ay - pad < by + bh and ay + ah + pad > by)


def bbox_collides_any(x: float, y: float, w: float, h: float,
                      obstacles: List[Tuple[float, float, float, float]],
                      pad: float = 3.0) -> bool:
    """rect (x,y,w,h) 是否与 obstacles 里任一 rect 相交.

    obstacles: [(ox, oy, ow, oh), ...]. pad 默认 3 SVG-px 用于 breathing room.
    典型 caller: cardinality pill 判定与 entity card 是否重叠.
    """
    for ox, oy, ow, oh in obstacles:
        if bbox_intersects(x, y, w, h, ox, oy, ow, oh, pad):
            return True
    return False


def pick_first_free(candidates: List[Tuple[float, float]],
                     w: float, h: float,
                     obstacles: List[Tuple[float, float, float, float]],
                     center_coords: bool = True,
                     pad: float = 3.0) -> Tuple[float, float]:
    """从 candidates 列表里取第一个不撞 obstacles 的点.

    Args:
        candidates: [(cx, cy), ...] · 按优先级排序 · 首选放最想要的位置.
        w, h: 待放置矩形的宽高.
        obstacles: 障碍矩形列表 [(ox, oy, ow, oh), ...].
        center_coords: True (默认) 表示 candidates 是矩形中心点; False 表示左上角.
        pad: breathing room, 默认 3 SVG-px.

    Returns:
        (cx, cy) — 第一个不撞的; 全都撞就返回 candidates[0] (fallback).
    """
    if not candidates:
        return (0.0, 0.0)
    for cx, cy in candidates:
        x = cx - w / 2 if center_coords else cx
        y = cy - h / 2 if center_coords else cy
        if not bbox_collides_any(x, y, w, h, obstacles, pad):
            return (cx, cy)
    return candidates[0]
