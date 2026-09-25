"""
K3 · napkin skin · 手绘感 · 会议室白板 / 咖啡桌餐巾纸

视觉核心：
    * stroke 用 feTurbulence + feDisplacementMap 抖动 · 边线不再是光滑直线
    * 手写字体 · Comic Sans MS / Marker Felt / cursive fallback
    * stroke-linecap="round" · stroke-linejoin="round" · 端点圆润
    * 填色轻 · bg_alt · 只做暗提示 · 强调用 primary
    * container 用双圈画法（先内圈再外圈错位）· 有 sketch 感

被期望 kind：
    node.kind ∈ {task, decision, bubble, note}    默认 task (圆角矩形)
    edge.kind ∈ {assoc, arrow, doodle}            默认 arrow
    container.kind ∈ {frame, cloud}
"""
from __future__ import annotations
import math

from ..engine import text, rect, circle, polygon, line, path, esc
from ..palettes import Palette
from ._base import _label_clip


# 手写字体 fallback chain
_NAPKIN_FAMILY = "Comic Sans MS, Marker Felt, Bradley Hand, Chalkboard, cursive"


class NapkinSkin:
    name = "napkin"

    # 唯一的 filter id · 允许同页多次调用
    _FILTER_ID = "napkin-roughen"

    def defs(self, palette: Palette) -> str:
        """SVG <defs> 里插入一次 filter · 用户负责在 svg root 之后放置。"""
        return (
            f'<defs>'
            f'<filter id="{self._FILTER_ID}" x="-5%" y="-5%" '
            f'width="110%" height="110%">'
            f'<feTurbulence type="fractalNoise" baseFrequency="0.02" '
            f'numOctaves="2" seed="7" result="noise"/>'
            f'<feDisplacementMap in="SourceGraphic" in2="noise" '
            f'scale="2" xChannelSelector="R" yChannelSelector="G"/>'
            f'</filter>'
            f'</defs>'
        )

    # ── 描边包裹 · 只在 shape 上加 filter 引用（text 不加 · 会糊）──
    @staticmethod
    def _wrap(inner: str) -> str:
        return f'<g filter="url(#{NapkinSkin._FILTER_ID})" ' \
               f'stroke-linecap="round" stroke-linejoin="round">{inner}</g>'

    # ─────────── node ───────────
    def draw_node(self, x, y, w, h, label, palette: Palette,
                  kind: str = "task", **_) -> str:
        label = _label_clip(label, 18)
        ink = palette.ink
        fill = palette.bg_alt

        if kind == "decision":
            cx, cy = x + w / 2, y + h / 2
            pts = [(cx, y), (x + w, cy), (cx, y + h), (x, cy)]
            shape = polygon(pts, fill=fill, stroke=ink, sw=2)
        elif kind == "bubble":
            r = min(w, h) / 2
            shape = circle(x + w / 2, y + h / 2, r,
                           fill=fill, stroke=ink, sw=2)
        elif kind == "note":
            # 便签折角
            fold = 10
            d = (f"M {x} {y} L {x + w - fold} {y} "
                 f"L {x + w} {y + fold} L {x + w} {y + h} "
                 f"L {x} {y + h} Z")
            fold_d = (f"M {x + w - fold} {y} "
                      f"L {x + w - fold} {y + fold} "
                      f"L {x + w} {y + fold}")
            shape = (path(d, fill=fill, stroke=ink, sw=2) +
                     path(fold_d, fill="none", stroke=ink, sw=1.5))
        else:  # task · 圆角矩形
            shape = rect(x, y, w, h, rx=10, fill=fill, stroke=ink, sw=2)

        shape_w = self._wrap(shape)
        # 手写字体 · 尺寸略大 · 不加 filter (保清晰)
        lbl = text(x + w / 2, y + h / 2 + 4, label,
                   size=12, color=ink, family=_NAPKIN_FAMILY,
                   anchor="middle", bold=True)
        return shape_w + lbl

    # ─────────── edge ───────────
    def draw_edge(self, x1, y1, x2, y2, label, palette: Palette,
                  kind: str = "arrow", **_) -> str:
        ink = palette.ink
        # 稍微弯一点 · sketchy 感
        mx = _midp(x1, x2)
        my = _midp(y1, y2)
        # 垂直偏移 · 30% 的弧
        dx, dy = x2 - x1, y2 - y1
        nx, ny = -dy, dx
        norm = max(math.hypot(nx, ny), 1e-6)
        off = 6
        cx = mx + nx / norm * off
        cy = my + ny / norm * off
        d = f"M {x1:.1f} {y1:.1f} Q {cx:.1f} {cy:.1f} {x2:.1f} {y2:.1f}"
        stroke = ink
        dash = "6,4" if kind == "doodle" else None
        p_str = path(d, fill="none", stroke=stroke, sw=2, dash=dash)
        arrow_str = ""
        if kind != "doodle":
            ang = math.atan2(y2 - cy, x2 - cx)
            head = 10
            ax1 = x2 - head * math.cos(ang - math.pi / 7)
            ay1 = y2 - head * math.sin(ang - math.pi / 7)
            ax2 = x2 - head * math.cos(ang + math.pi / 7)
            ay2 = y2 - head * math.sin(ang + math.pi / 7)
            arrow_str = polygon([(x2, y2), (ax1, ay1), (ax2, ay2)],
                                fill=ink)
        edge_svg = self._wrap(p_str + arrow_str)

        lbl_str = ""
        if label:
            lbl_str = text(mx, my - 6, label,
                           size=11, color=ink,
                           family=_NAPKIN_FAMILY, anchor="middle",
                           italic=True)
        return edge_svg + lbl_str

    # ─────────── container ───────────
    def draw_container(self, x, y, w, h, label, palette: Palette,
                       kind: str = "frame", **_) -> str:
        ink = palette.gray if palette.gray else palette.ink
        if kind == "cloud":
            # 6 段圆弧拼云朵
            n = 8
            pts = []
            cx, cy = x + w / 2, y + h / 2
            for i in range(n):
                a = 2 * math.pi * i / n
                rr = (w / 2 if i % 2 == 0 else w / 2 - 10)
                px = cx + rr * math.cos(a)
                py = cy + (h / 2) * math.sin(a)
                pts.append((px, py))
            shape = polygon(pts, fill="none", stroke=ink, sw=1.5)
        else:
            # 双线框 · 内外错位
            shape = (rect(x, y, w, h, rx=8, fill="none",
                          stroke=ink, sw=1.5) +
                     rect(x + 3, y + 3, w - 6, h - 6, rx=6,
                          fill="none", stroke=ink, sw=0.8))
        cont_svg = self._wrap(shape)
        lbl_str = ""
        if label:
            lbl_str = text(x + 12, y + 16, label,
                           size=11, color=ink, family=_NAPKIN_FAMILY,
                           bold=True)
        return cont_svg + lbl_str


def _midp(a: float, b: float) -> float:
    return (a + b) / 2.0


NAPKIN = NapkinSkin()
