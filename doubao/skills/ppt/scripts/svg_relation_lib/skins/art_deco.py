"""
Skin · art_deco · 装饰艺术 1920s / Gatsby / Chrysler Building

参考: Chrysler Building 顶部放射线 · Gatsby 电影海报 · Herbert Matter Deco 海报.

视觉核心:
    * bg=#0F1F3D 深藏青 (比 couture_noir 的纯黑更暖 · Deco 招牌深色)
    * ink=#F2E8D0 米白 (奶油纸质感)
    * primary=#D4A855 Deco 金 (比 luxury 的哑金更亮更 saturated)
    * accent=#8B2C3E 酒红 (Deco 常见次色 · 剧院丝绒)
    * 字体:
        - Cinzel / Trajan Pro (Roman all-caps 大写字母 · Deco 招牌 serif)
        - Poiret One (几何装饰 sans · 1920s 海报常见)
    * 装饰母题:
        - 金色 sunburst 放射线 (Chrysler Building 顶)
        - zigzag 阶梯纹 (Deco 边框招牌)
        - 双细金线夹内文 (frame 结构)
        - 四角 L 型阶梯装饰 (Chrysler 递减阶梯)
        - 对称构图 · 全 all-caps
"""
from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

from ..engine import esc
from ..palettes import Palette
from .editorial_atelier import (
    CanvasProfile,
    HERO_CANVAS as _EA_HERO_CANVAS,
    EMBED_CANVAS as _EA_EMBED_CANVAS,
    TX_CANVAS as _EA_TX_CANVAS,
    _txt,
    _rect,
    _line,
    _tint,
)


HERO_CANVAS = _EA_HERO_CANVAS
EMBED_CANVAS = _EA_EMBED_CANVAS
TX_CANVAS = _EA_TX_CANVAS


# ─────────── Hue table ───────────
# 8 支 hue · Deco 硬色: 金主导 + 酒红 + 藏青 + 深绿 · 无低饱和杂色
HUE = {
    "rust":     "#D4A855",   # Deco 金 · 主色 (比 luxury 更亮)
    "orange":   "#B8862F",   # 深金/古铜 · 二级
    "magenta":  "#8B2C3E",   # 酒红丝绒 · Deco 剧院色
    "blue":     "#2A4B7C",   # 皇家蓝 · Deco 常见
    "green":    "#3E7A5E",   # 翡翠绿 · Deco 珠宝色
    "olive":    "#7A6B4C",   # 深金橄榄
    "cinnamon": "#A67C4E",   # 铜金 · 中性金
    "gold_p":   "#F0C060",   # 亮金 · sunburst 光晕色
}

HUE_ORDER: Tuple[str, ...] = (
    "rust", "orange", "magenta", "blue", "green", "olive", "cinnamon",
)


# ─────────── Typography ───────────
# Cinzel: Roman all-caps · Trajan 的现代 web 复刻 · Deco 招牌
# Poiret One: 几何 sans 装饰 · 1920s 海报常见
FONT_SERIF = ("Cinzel, Trajan Pro, Trajan, "
              "Optima, Playfair Display, Georgia, serif")
FONT_SANS = ("Poiret One, Futura, Century Gothic, "
             "ITC Avant Garde Gothic, Inter, sans-serif")

TYPE_SCALE = {
    "title":         (32, FONT_SERIF, 500),
    "subtitle":      (11, FONT_SANS,  400),
    "section":       (9,  FONT_SANS,  400),
    "column_header": (9,  FONT_SANS,  400),
    "hub_name":      (22, FONT_SERIF, 500),
    "hub_name_xl":   (32, FONT_SERIF, 500),
    "block_title":   (15, FONT_SERIF, 500),
    "card_title":    (12, FONT_SERIF, 500),
    "chip_kinase":   (13, FONT_SERIF, 500),
    "chip_label":    (10, FONT_SANS,  400),
    "body_desc":     (9,  FONT_SANS,  400),
    "micro_numeric": (11, FONT_SERIF, 500),
    "footer_read":   (11, FONT_SERIF, 400),
    "footer_italic": (11, FONT_SERIF, 400),
    "kicker_mini":   (8,  FONT_SANS,  400),
    "source_tag":    (9,  FONT_SANS,  400),
}


# ═════════════════════════════════════════════════════════════════
# Palette · ART_DECO
# ═════════════════════════════════════════════════════════════════

ART_DECO = Palette(
    name="Art Deco · Gatsby / Chrysler Blue-Gold",
    bg="#0F1F3D",                # 深藏青
    bg_alt="#182B4F",            # 微亮层
    bg_dim="#233867",
    ink="#F2E8D0",               # 米白
    gray="rgba(242,232,208,0.6)",# 米白 60%
    hair="#F2E8D0",
    primary=HUE["rust"],         # Deco 金
    primary_dim=HUE["orange"],   # 古铜
    accent=HUE["gold_p"],        # 亮金 sunburst
    accent_dim=HUE["magenta"],   # 酒红
    positive=HUE["green"],
    negative=HUE["magenta"],
    head_family=FONT_SERIF,
    body_family=FONT_SANS,
    mono_family=FONT_SANS,
    kicker_letter_spacing=3.5,
    kicker_case="upper",
    section_numbering="roman",
    folio_style="hairline",
    title_style="serif_bold",
    subtitle_style="sans_italic",
    figure_caption_prefix="Pl.",   # Plate (Deco 图版招牌)
    signature_note="ART DECO · GATSBY / CHRYSLER BLUE-GOLD",
)

PALETTE = ART_DECO


# ═════════════════════════════════════════════════════════════════
# Filter / gradient / marker
# ═════════════════════════════════════════════════════════════════

_FILTER_DEFS = """<filter id="ea-soft-shadow" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur in="SourceAlpha" stdDeviation="2"/><feOffset dx="0" dy="1.5"/><feComponentTransfer><feFuncA type="linear" slope="0.20"/></feComponentTransfer><feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge></filter><filter id="ea-hub-shadow" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur in="SourceAlpha" stdDeviation="3.5"/><feOffset dx="0" dy="2.5"/><feComponentTransfer><feFuncA type="linear" slope="0.25"/></feComponentTransfer><feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge></filter><filter id="ea-hub-halo" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur in="SourceGraphic" stdDeviation="5.5"/></filter>"""


def _gradient_defs(hues: Sequence[str]) -> str:
    out: List[str] = []
    for name in hues:
        c = HUE.get(name, HUE["rust"])
        gid = f"ea-r-{name}"
        out.append(
            f'<linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="0">'
            f'<stop offset="0" stop-color="{c}" stop-opacity="0.75"/>'
            f'<stop offset="1" stop-color="{c}" stop-opacity="0.35"/>'
            f'</linearGradient>'
        )
    return "".join(out)


def _marker_defs(hues: Sequence[str]) -> str:
    out: List[str] = []
    for name in hues:
        c = HUE.get(name, HUE["rust"])
        mid = f"ea-arr-{name}"
        out.append(
            f'<marker id="{mid}" viewBox="0 0 10 10" refX="9" refY="5" '
            f'markerWidth="7" markerHeight="7" orient="auto">'
            f'<path d="M 0 0 L 9 5 L 0 10 Z" fill="{c}"/></marker>'
        )
    out.append(
        '<marker id="ea-tbar-gray" viewBox="0 0 10 10" refX="7" refY="5" '
        'markerWidth="8" markerHeight="8" orient="auto">'
        '<line x1="7" y1="0" x2="7" y2="10" '
        'stroke="rgba(242,232,208,0.6)" stroke-width="2.6"/></marker>'
    )
    return "".join(out)


def _resolve_hue(hue_key_or_hex: str) -> str:
    if not hue_key_or_hex:
        return HUE["rust"]
    if hue_key_or_hex.startswith("#"):
        return hue_key_or_hex
    return HUE.get(hue_key_or_hex, HUE["rust"])


def _zigzag_path(x: float, y: float, w: float, step: float = 8.0,
                 amp: float = 3.0) -> str:
    """生成 zigzag path · 从 (x,y) 起水平铺 w 宽度的锯齿."""
    pts: List[str] = [f"M {x:.1f} {y:.1f}"]
    n = int(w / step)
    for i in range(1, n + 1):
        px = x + i * step
        py = y - amp if (i % 2 == 1) else y
        pts.append(f"L {px:.1f} {py:.1f}")
    return " ".join(pts)


def _sunburst_lines(cx: float, cy: float, r_inner: float, r_outer: float,
                    n_rays: int = 7, span_deg: float = 180) -> List[Tuple[float, float, float, float]]:
    """生成 sunburst 放射线 · 从 (cx,cy) 向上半圆放射 n_rays 根.

    Returns: [(x1,y1,x2,y2), ...]
    """
    import math
    lines: List[Tuple[float, float, float, float]] = []
    if n_rays < 2:
        return lines
    start = 180 + (180 - span_deg) / 2      # 上半圆左端
    step = span_deg / (n_rays - 1)
    for i in range(n_rays):
        deg = start + i * step
        rad = math.radians(deg)
        x1 = cx + r_inner * math.cos(rad)
        y1 = cy + r_inner * math.sin(rad)
        x2 = cx + r_outer * math.cos(rad)
        y2 = cy + r_outer * math.sin(rad)
        lines.append((x1, y1, x2, y2))
    return lines


# ═════════════════════════════════════════════════════════════════
# svg_defs · hero_chrome · hero_footer · tspan · 契约必备
# ═════════════════════════════════════════════════════════════════

def svg_defs(hues: Sequence[str] = HUE_ORDER,
             include_markers: bool = True,
             include_gradients: bool = True) -> str:
    inner = _FILTER_DEFS
    if include_gradients:
        inner += _gradient_defs(hues)
    if include_markers:
        inner += _marker_defs(hues)
    return f"<defs>{inner}</defs>"


def hero_chrome(*, kicker: str = "",
                title: str = "",
                subtitle: str = "",
                column_headers: Optional[Sequence[Tuple[str, float]]] = None,
                encoding_note_right: str = "",
                palette: Palette = ART_DECO,
                canvas: CanvasProfile = HERO_CANVAS,
                include_bg: bool = True) -> str:
    is_embed = (canvas.w == 900 and canvas.h == 336)
    title_sz = 22 if is_embed else 32
    subtitle_sz = 10 if is_embed else 11
    section_sz = 8 if is_embed else 9
    kicker_sz = 8 if is_embed else 9
    parts: List[str] = []
    if include_bg:
        parts.append(_rect(0, 0, canvas.w, canvas.h, fill=palette.bg))
    if kicker:
        parts.append(_txt(canvas.margin_x, canvas.title_y - 20, kicker,
                          size=kicker_sz, family=FONT_SANS, weight=400,
                          fill=palette.primary, letter_em=0.35))
    if title:
        parts.append(_txt(canvas.margin_x, canvas.title_y, title,
                          size=title_sz, family=FONT_SERIF, weight=500,
                          fill=palette.ink, letter_em=0.05))
    if subtitle:
        parts.append(_txt(canvas.margin_x, canvas.subtitle_y, subtitle,
                          size=subtitle_sz, family=FONT_SANS, weight=400,
                          fill=palette.gray, letter_em=0.22))
    # title 双金线 (Deco 招牌: 双水平细金线夹标题)
    parts.append(_line(canvas.margin_x, canvas.title_hair_y,
                       canvas.w - canvas.margin_x, canvas.title_hair_y,
                       stroke=palette.primary, sw=1.2, opacity=0.85))
    parts.append(_line(canvas.margin_x, canvas.title_hair_y + 4,
                       canvas.w - canvas.margin_x, canvas.title_hair_y + 4,
                       stroke=palette.primary, sw=0.5, opacity=0.55))
    if column_headers:
        for lbl, cx in column_headers:
            parts.append(_txt(cx, canvas.section_hdr_y, lbl,
                              size=section_sz, family=FONT_SANS, weight=400,
                              fill=palette.primary,
                              anchor="middle", letter_em=0.32))
    if encoding_note_right:
        note_sz = 9 if is_embed else 10
        parts.append(_txt(canvas.w - canvas.margin_x, canvas.subtitle_y,
                          encoding_note_right,
                          size=note_sz, family=FONT_SERIF, weight=400,
                          fill=palette.gray, anchor="end", italic=True))
    return "".join(parts)


def hero_footer(*, caption: str = "",
                source: str = "",
                read_lines: Optional[Sequence[str]] = None,
                italic_last: bool = False,
                palette: Palette = ART_DECO,
                canvas: CanvasProfile = HERO_CANVAS,
                min_read_chars: int = 40) -> str:
    _ = (caption, source, read_lines, italic_last, palette, canvas, min_read_chars)
    return ""


def tspan(word: str, *, color: str = HUE["rust"], weight: int = 500) -> str:
    """READ 段内高亮 · 默认 Deco 金."""
    c = _resolve_hue(color) if not color.startswith("rgba") else color
    return (f'<tspan font-weight="{weight}" fill="{c}">'
            f'{esc(word.upper())}</tspan>')


# ═════════════════════════════════════════════════════════════════
# Skin 契约 · draw_node · Art Deco 招牌
# 3 kind:
#   - category_card: 顶端 zigzag 金线 + 双细金线夹内文
#   - kpi_card: 上下双金线 + Cinzel all-caps · 对称构图
#   - problem_statement: 顶端 sunburst 金放射线 + 四角 L 阶梯装饰
# ═════════════════════════════════════════════════════════════════

class ArtDecoSkin:
    """Art Deco · 1920s 装饰艺术 · zigzag + sunburst + Trajan all-caps."""

    name = "art_deco"

    def draw_node(self, x: float, y: float, w: float, h: float,
                  label: str, palette: Palette,
                  kind: str = "", **kwargs) -> Optional[str]:
        pal = palette or ART_DECO
        if kind == "category_card":
            return self._category_card(x, y, w, h, label, pal, **kwargs)
        if kind == "kpi_card":
            return self._kpi_card(x, y, w, h, label, pal, **kwargs)
        if kind == "problem_statement":
            return self._problem_statement(x, y, w, h, pal, label=label, **kwargs)
        # ── mindmap hub (opt-in · mp_mindmap preset 用) ──
        if kind == "mindmap_hub":
            return self._mindmap_hub(x, y, w, h, label, pal, **kwargs)
        return None

    # ─────────── category_card · zigzag 顶 + 单粗金底线 ───────────
    # h=36 极窄 · 只放 label + subtitle · 底金线单条避免与 subtitle 撞
    def _category_card(self, x, y, w, h, label, pal, **kw) -> str:
        gold = _resolve_hue("rust")          # Deco 金
        subtitle = kw.get("subtitle", "")
        pct = kw.get("pct", "")
        parts: List[str] = []
        # 底: 深藏青 bg_alt (Deco 场景色)
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w}" height="{h}" '
            f'fill="{pal.bg_alt}"/>'
        )
        # 顶端 zigzag 金线 (Deco 边框招牌 · amp 缩到 1.8 避免顶出)
        parts.append(
            f'<path d="{_zigzag_path(x, y + 1.8, w, step=6, amp=1.8)}" '
            f'fill="none" stroke="{gold}" stroke-width="1.0" '
            f'stroke-linejoin="miter"/>'
        )
        # 底部单粗金线 (取消第二根 · 让 subtitle 有空间)
        parts.append(
            f'<line x1="{x:.1f}" y1="{y + h:.1f}" '
            f'x2="{x + w:.1f}" y2="{y + h:.1f}" '
            f'stroke="{gold}" stroke-width="0.9"/>'
        )
        # label · Cinzel all-caps 米白 · y=17 (让出顶 zigzag · 与 subtitle 差 10)
        parts.append(
            f'<text x="{x + 12:.1f}" y="{y + 17:.1f}" '
            f'font-family="{FONT_SERIF}" font-size="11" font-weight="500" '
            f'fill="{pal.ink}" letter-spacing="0.18em">'
            f'{esc(label.upper())}</text>'
        )
        if subtitle:
            # subtitle · y=30 (与底金线 y=36 差 6 · 与 label 差 13)
            parts.append(
                f'<text x="{x + 12:.1f}" y="{y + 30:.1f}" '
                f'font-family="{FONT_SANS}" font-size="8" font-weight="400" '
                f'fill="{gold}" letter-spacing="0.28em" opacity="0.8">'
                f'{esc(subtitle.upper())}</text>'
            )
        # pct · Cinzel 金 · 右对齐 (与 label 同 baseline)
        if pct:
            parts.append(
                f'<text x="{x + w - 12:.1f}" y="{y + 17:.1f}" '
                f'text-anchor="end" font-family="{FONT_SERIF}" '
                f'font-size="14" font-weight="500" fill="{gold}" '
                f'letter-spacing="0.02em">'
                f'{esc(pct)}</text>'
            )
        return "".join(parts)

    # ─────────── kpi_card · 单顶粗金线 + 单底粗金线 (Deco 三线表) ───────────
    # h=34 极窄 · 取消 4 金线中的 2 条细线避免与 value 底沿相撞
    def _kpi_card(self, x, y, w, h, label, pal, **kw) -> str:
        gold = _resolve_hue("rust")
        bright = _resolve_hue("gold_p")
        value = kw.get("value", "")
        note = kw.get("note", "")
        parts: List[str] = []
        # 顶单粗金线 (只保留粗线 · Deco 三线表)
        parts.append(
            f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x + w:.1f}" y2="{y:.1f}" '
            f'stroke="{gold}" stroke-width="1.1"/>'
        )
        # 底单粗金线
        parts.append(
            f'<line x1="{x:.1f}" y1="{y + h:.1f}" '
            f'x2="{x + w:.1f}" y2="{y + h:.1f}" '
            f'stroke="{gold}" stroke-width="1.1"/>'
        )
        # kicker · Poiret sans 米白 · y=12 (baseline · 与顶线差 12)
        if label:
            parts.append(
                f'<text x="{x + w / 2:.1f}" y="{y + 12:.1f}" '
                f'text-anchor="middle" '
                f'font-family="{FONT_SANS}" font-size="8" font-weight="400" '
                f'fill="{pal.ink}" letter-spacing="0.36em">'
                f'{esc(label.upper())}</text>'
            )
        # value · Cinzel serif 亮金 · y=28 (16pt 字高 y=18-30 · 与底金 34 差 4)
        if value:
            parts.append(
                f'<text x="{x + w / 2:.1f}" y="{y + 28:.1f}" '
                f'text-anchor="middle" '
                f'font-family="{FONT_SERIF}" font-size="15" font-weight="500" '
                f'fill="{bright}" letter-spacing="0.02em">'
                f'{esc(value)}</text>'
            )
        # note · Poiret italic 金 · 挪回 value 同行右对齐 (与 pitch_neon 一致)
        # 之前放在 y+h+12 会溢出 bbox · 且遮到下一层
        if note:
            parts.append(
                f'<text x="{x + w - 4:.1f}" y="{y + 28:.1f}" '
                f'text-anchor="end" '
                f'font-family="{FONT_SANS}" font-size="8" font-weight="400" '
                f'font-style="italic" fill="{gold}" letter-spacing="0.14em" '
                f'opacity="0.85">'
                f'{esc(note.upper())}</text>'
            )
        return "".join(parts)

    # ─────────── problem_statement · sunburst 缩小成装饰帽 · 重排避免遮挡 ───────────
    # bbox = 210×156. 之前 sunburst 中心 y=76 半径 42 占据 y=34-118,
    # 直接覆盖了 label (y=106) 和 stat 顶端. 现在把 sunburst 抬到 y=22
    # 作为 kicker 上方的"装饰帽", 让 label/stat/range 有连续竖向空间.
    def _problem_statement(self, x, y, w, h, pal, **kw) -> str:
        gold = _resolve_hue("rust")
        bright = _resolve_hue("gold_p")
        kicker = kw.get("kicker", "PLATE")
        label = kw.get("label", "")
        stat = kw.get("stat", "")
        range_txt = kw.get("range", "")
        parts: List[str] = []
        cx = x + w / 2

        # ── Deco frame: 外粗金 + 内细亮金 ──
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w}" height="{h}" '
            f'fill="{pal.bg_alt}" stroke="{gold}" stroke-width="1.5"/>'
        )
        parts.append(
            f'<rect x="{x + 6:.1f}" y="{y + 6:.1f}" '
            f'width="{w - 12}" height="{h - 12}" '
            f'fill="none" stroke="{bright}" stroke-width="0.5" opacity="0.75"/>'
        )

        # ── 四角 L 阶梯装饰 (Chrysler Building 招牌) ──
        step = 8.0
        for corner in [(x + 3, y + 3, 1, 1),
                       (x + w - 3, y + 3, -1, 1),
                       (x + 3, y + h - 3, 1, -1),
                       (x + w - 3, y + h - 3, -1, -1)]:
            cx0, cy0, sx, sy = corner
            parts.append(
                f'<line x1="{cx0:.1f}" y1="{cy0:.1f}" '
                f'x2="{cx0 + sx * step:.1f}" y2="{cy0:.1f}" '
                f'stroke="{bright}" stroke-width="1.2"/>'
            )
            parts.append(
                f'<line x1="{cx0:.1f}" y1="{cy0:.1f}" '
                f'x2="{cx0:.1f}" y2="{cy0 + sy * step:.1f}" '
                f'stroke="{bright}" stroke-width="1.2"/>'
            )

        # ── sunburst 装饰帽 (缩小 · 只占顶部 y=6-32 区域) ──
        # 中心 y+22 · 半径 r_inner=5 r_outer=16 · 放射线只落在 kicker 上方
        sun_cy = y + 22
        rays = _sunburst_lines(cx, sun_cy, r_inner=5, r_outer=16,
                                n_rays=7, span_deg=120)
        for x1, y1, x2, y2 in rays:
            parts.append(
                f'<line x1="{x1:.1f}" y1="{y1:.1f}" '
                f'x2="{x2:.1f}" y2="{y2:.1f}" '
                f'stroke="{gold}" stroke-width="0.7" opacity="0.75"/>'
            )
        # sunburst 中心小圆 (亮金)
        parts.append(
            f'<circle cx="{cx:.1f}" cy="{sun_cy:.1f}" r="2.5" '
            f'fill="{bright}"/>'
        )

        # ── 布局 (bbox 内偏移):
        #   sunburst 装饰帽 y=6-38
        #   kicker           y=54     (baseline · 9pt 字高 y=45-56)
        #   divider          y=62     (装饰细线)
        #   label            y=82     (12pt 字高 y=70-84)
        #   stat             y=118    (30pt 字高 y=92-122 · 与 label 差 22)
        #   range divider    y=134
        #   range text       y=146    (9pt 字高 y=138-148 · 在 h=156 内)
        # ──
        parts.append(
            f'<text x="{cx:.1f}" y="{y + 54:.1f}" text-anchor="middle" '
            f'font-family="{FONT_SERIF}" font-size="9" font-weight="500" '
            f'fill="{bright}" letter-spacing="0.44em">'
            f'{esc(kicker.upper())}</text>'
        )
        # divider 双细金线 (取代原本会跟 label 撞的圆点 + 只保留水平线)
        parts.append(
            f'<line x1="{cx - 34:.1f}" y1="{y + 62:.1f}" '
            f'x2="{cx + 34:.1f}" y2="{y + 62:.1f}" '
            f'stroke="{gold}" stroke-width="0.4" opacity="0.6"/>'
        )
        if label:
            parts.append(
                f'<text x="{cx:.1f}" y="{y + 82:.1f}" text-anchor="middle" '
                f'font-family="{FONT_SERIF}" font-size="12" '
                f'font-weight="500" fill="{pal.ink}" letter-spacing="0.16em">'
                f'{esc(label.upper())}</text>'
            )
        if stat:
            # 大 stat · Cinzel serif 亮金 · 30pt (缩自 36pt · 与 label/range 空开)
            parts.append(
                f'<text x="{cx:.1f}" y="{y + 118:.1f}" text-anchor="middle" '
                f'font-family="{FONT_SERIF}" font-size="30" font-weight="500" '
                f'fill="{bright}" letter-spacing="0em">'
                f'{esc(stat)}</text>'
            )
        if range_txt:
            parts.append(
                f'<line x1="{cx - 40:.1f}" y1="{y + 134:.1f}" '
                f'x2="{cx + 40:.1f}" y2="{y + 134:.1f}" '
                f'stroke="{gold}" stroke-width="0.5" opacity="0.7"/>'
            )
            parts.append(
                f'<text x="{cx:.1f}" y="{y + 146:.1f}" text-anchor="middle" '
                f'font-family="{FONT_SANS}" font-size="8" font-weight="400" '
                f'fill="{gold}" letter-spacing="0.24em">'
                f'{esc(range_txt.upper())}</text>'
            )
        return "".join(parts)

    # ═══════════════════════════════════════════════════════════
    # mindmap hub · 藏青圆 + 双金环 + 顶端 sunburst 装饰帽 + Cinzel all-caps
    # ═══════════════════════════════════════════════════════════

    def _mindmap_hub(self, x, y, w, h, name, pal, **kw) -> str:
        gold = _resolve_hue("rust")            # Deco 金
        bright = _resolve_hue("gold_p")        # 亮金
        kicker = kw.get("kicker", "")
        stat = kw.get("stat", "")
        stat_note = kw.get("stat_note", "")
        cx = kw.get("hub_cx", x + w / 2)
        cy = kw.get("hub_cy", y + h / 2)
        r = kw.get("hub_r", w / 2)
        parts: List[str] = []
        # 主圆: bg_alt 深藏青
        parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{pal.bg_alt}"/>'
        )
        # 双金环 (Deco 招牌: 外粗内细)
        parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" '
            f'stroke="{gold}" stroke-width="1.6"/>'
        )
        parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r - 5}" fill="none" '
            f'stroke="{bright}" stroke-width="0.6" opacity="0.75"/>'
        )
        # 顶端 sunburst 装饰帽 (Chrysler Building 招牌 · 小尺度)
        rays = _sunburst_lines(cx, cy - r - 4, r_inner=3, r_outer=14,
                                n_rays=7, span_deg=120)
        for x1, y1, x2, y2 in rays:
            parts.append(
                f'<line x1="{x1:.1f}" y1="{y1:.1f}" '
                f'x2="{x2:.1f}" y2="{y2:.1f}" '
                f'stroke="{gold}" stroke-width="0.7" opacity="0.75"/>'
            )
        parts.append(
            f'<circle cx="{cx}" cy="{cy - r - 4:.1f}" r="2" fill="{bright}"/>'
        )
        # kicker · Cinzel all-caps 亮金
        if kicker:
            parts.append(
                f'<text x="{cx}" y="{cy - 30:.1f}" text-anchor="middle" '
                f'font-family="{FONT_SERIF}" font-size="9" '
                f'font-weight="500" fill="{bright}" letter-spacing="0.36em">'
                f'{esc(kicker.upper())}</text>'
            )
            parts.append(
                f'<line x1="{cx - 24}" y1="{cy - 22:.1f}" '
                f'x2="{cx + 24}" y2="{cy - 22:.1f}" '
                f'stroke="{gold}" stroke-width="0.5" opacity="0.7"/>'
            )
        # name · Cinzel Roman all-caps 米白 · 大字距
        if name:
            parts.append(
                f'<text x="{cx}" y="{cy + 3}" text-anchor="middle" '
                f'font-family="{FONT_SERIF}" font-size="18" '
                f'font-weight="500" fill="{pal.ink}" letter-spacing="0.14em">'
                f'{esc(name.upper())}</text>'
            )
        # stat · Cinzel 亮金
        if stat:
            parts.append(
                f'<text x="{cx}" y="{cy + 26}" text-anchor="middle" '
                f'font-family="{FONT_SERIF}" font-size="16" '
                f'font-weight="500" fill="{bright}" letter-spacing="0.02em">'
                f'{esc(stat)}</text>'
            )
        # note · Poiret sans 金 uppercase
        if stat_note:
            parts.append(
                f'<text x="{cx}" y="{cy + 44:.1f}" text-anchor="middle" '
                f'font-family="{FONT_SANS}" font-size="7" '
                f'fill="{gold}" opacity="0.85" letter-spacing="0.24em">'
                f'{esc(stat_note.upper())}</text>'
            )
        return "".join(parts)


ART_DECO_SKIN = ArtDecoSkin()
SKIN_INSTANCE = ART_DECO_SKIN


__all__ = [
    # Palette
    "ART_DECO", "PALETTE",
    # Skin class
    "ArtDecoSkin", "ART_DECO_SKIN", "SKIN_INSTANCE",
    # Canvas
    "CanvasProfile", "HERO_CANVAS", "EMBED_CANVAS", "TX_CANVAS",
    # Tokens
    "HUE", "HUE_ORDER", "TYPE_SCALE", "FONT_SERIF", "FONT_SANS",
    # Chrome
    "svg_defs", "hero_chrome", "hero_footer", "tspan",
]
