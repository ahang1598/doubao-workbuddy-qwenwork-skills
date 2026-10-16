"""
K4 · editorial skin · 期刊 / 报纸排版

视觉核心：
    * 大号 numeral 序号（36pt bold · serif）· 每 node 前置
    * 标题 serif bold 18pt · 副标 8pt uppercase gray
    * hairline 分隔（1px palette.hair）· 页眉页脚风
    * 灰色 body text 11pt · italic caption
    * edge 用极细 hairline 直线（0.6px）· 无 arrow head 或极小
    * container 用左右 wing hairline + kicker 标签
    * 强调用 palette.accent 竖条 · 期刊 pull-quote 感

被期望 kind：
    node.kind ∈ {item, headline, quote}    默认 item
    edge.kind ∈ {rule, dotted, ornament}   默认 rule
    container.kind ∈ {section, sidebar}
"""
from __future__ import annotations

from ..engine import text, rect, line, path
from ..palettes import Palette
from ._base import _label_clip


class EditorialSkin:
    name = "editorial"

    def defs(self, palette: Palette) -> str:
        return ""  # 期刊排版全靠 hairline / typography · 不需 filter

    # ── node ──
    def draw_node(self, x, y, w, h, label, palette: Palette,
                  kind: str = "item", numeral: str = "", sublabel: str = "",
                  **_) -> str:
        label = _label_clip(label, 32)
        sub = _label_clip(sublabel, 40) if sublabel else ""
        ink = palette.ink
        gray = palette.gray
        accent = palette.accent
        head_family = palette.head_family
        body_family = palette.body_family
        mono_family = palette.mono_family

        parts = []
        # 顶部 hairline
        parts.append(line(x, y, x + w, y, color=palette.hair, w=1))
        # 左侧 accent 竖条 · quote 用粗一点
        stripe_w = 4 if kind == "quote" else 2
        parts.append(rect(x, y, stripe_w, h, fill=accent))

        # 大号 numeral · 编号 · 用户没传就自动省略
        text_x = x + stripe_w + 14
        if numeral:
            parts.append(text(text_x, y + 32, numeral,
                              size=32, color=ink, family=head_family,
                              bold=True))
            text_x += (len(numeral) * 18) + 12

        if kind == "headline":
            parts.append(text(text_x, y + 22, label,
                              size=15, color=ink, family=head_family,
                              bold=True))
            if sub:
                parts.append(text(text_x, y + 38, sub.upper(),
                                  size=8, color=gray, family=mono_family,
                                  letter=1.5))
        elif kind == "quote":
            parts.append(text(text_x, y + 20, "“", size=22,
                              color=accent, family=head_family, bold=True))
            parts.append(text(text_x + 14, y + 22, label,
                              size=13, color=ink, family=head_family,
                              italic=True))
            if sub:
                parts.append(text(text_x + 14, y + 40, sub.upper(),
                                  size=8, color=gray, family=mono_family,
                                  letter=1.5))
        else:  # item
            if sub:
                parts.append(text(text_x, y + 20, sub.upper(),
                                  size=8, color=gray, family=mono_family,
                                  letter=1.8))
                parts.append(text(text_x, y + 38, label,
                                  size=12, color=ink, family=head_family,
                                  bold=True))
            else:
                parts.append(text(text_x, y + 28, label,
                                  size=12, color=ink, family=head_family,
                                  bold=True))

        # 底部 hairline
        parts.append(line(x, y + h, x + w, y + h, color=palette.hair, w=0.6))
        return "".join(parts)

    # ── edge ──
    def draw_edge(self, x1, y1, x2, y2, label, palette: Palette,
                  kind: str = "rule", **_) -> str:
        ink = palette.ink
        gray = palette.gray
        hair = palette.hair
        parts = []
        if kind == "dotted":
            parts.append(line(x1, y1, x2, y2, color=gray, w=0.8,
                              dash="2,3"))
        elif kind == "ornament":
            # 中间小方块作 · 装饰 rule
            mx = (x1 + x2) / 2
            my = (y1 + y2) / 2
            parts.append(line(x1, y1, mx - 6, my, color=gray, w=0.6))
            parts.append(rect(mx - 3, my - 3, 6, 6,
                              fill=palette.accent))
            parts.append(line(mx + 6, my, x2, y2, color=gray, w=0.6))
        else:  # rule · 期刊 hairline
            parts.append(line(x1, y1, x2, y2, color=hair, w=1.0))
        if label:
            mx = (x1 + x2) / 2
            my = (y1 + y2) / 2
            parts.append(text(mx, my - 6, label.upper(),
                              size=8, color=gray,
                              family=palette.mono_family,
                              anchor="middle", letter=1.8))
        return "".join(parts)

    # ── container ──
    def draw_container(self, x, y, w, h, label, palette: Palette,
                       kind: str = "section", **_) -> str:
        ink = palette.ink
        gray = palette.gray
        accent = palette.accent
        parts = []
        if kind == "sidebar":
            # 侧栏 · 左 hairline + 顶 accent 短线
            parts.append(rect(x, y, w, h, fill=palette.bg_alt))
            parts.append(line(x, y, x, y + h, color=accent, w=2))
            if label:
                parts.append(text(x + 10, y + 18, label.upper(),
                                  size=9, color=accent,
                                  family=palette.mono_family,
                                  bold=True, letter=2.2))
        else:  # section · 顶底 rule + kicker 居中
            parts.append(line(x, y, x + w, y, color=ink, w=1.4))
            parts.append(line(x, y + h, x + w, y + h,
                              color=palette.hair, w=0.6))
            if label:
                # kicker 居中 + 两侧 rule
                lbl_w = max(len(label) * 6.5 + 20, 60)
                cx = x + w / 2
                parts.append(rect(cx - lbl_w / 2, y - 8, lbl_w, 16,
                                  fill=palette.bg))
                parts.append(text(cx, y + 4, label.upper(),
                                  size=9, color=ink,
                                  family=palette.mono_family, bold=True,
                                  anchor="middle", letter=2.5))
        return "".join(parts)


EDITORIAL = EditorialSkin()
