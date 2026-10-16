"""
Skin · couture_noir · Haute Couture 时装屋手册

参考: Chanel / Dior / Hermès 品牌手册 + Vogue Paris lookbook 排版语言.

视觉核心:
    * bg=#0A0A0A 极致深黑 · 比 pitch_neon 的 #0F0B14 更纯粹 (无任何色偏)
    * ink=#EDE3C6 珍珠白 (warm cream · 不是纯白) · 印刷手册招牌
    * accent=#D4AF7A 玫瑰金 (单点用 · 数字/hero stat only)
    * 字体: Didot / Bodoni 极端 thin-fat 对比 serif italic + Futura all-caps sans
    * 装饰母题:
        - 罗马数字 (I / II / III / IV) 替代 M1/M2/M3
        - 极粗上下横线 (weight 3) 夹极细内文 (weight 0.4) - Vogue lookbook 招牌
        - 大量 white space (padding 30+px)
        - 单点玫瑰金 accent 只用在 hero stat / 数字上
    * 不用: 圆角 / 阴影 / tint 底色 / glow / filter · 全靠 typography + white space

canvas 契约复用 editorial_atelier.
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


# ═════════════════════════════════════════════════════════════════
# Canvas · 复用 editorial_atelier
# ═════════════════════════════════════════════════════════════════

HERO_CANVAS = _EA_HERO_CANVAS
EMBED_CANVAS = _EA_EMBED_CANVAS
TX_CANVAS = _EA_TX_CANVAS


# ─────────── Hue table ───────────
# 8 支 hue · 全部收敛到 warm neutral (白金/象牙/珍珠) + 玫瑰金 · 无饱和色
# haute couture 硬规则: 深黑底 + 单点玫瑰金 · 副 hue 走深浅珍珠灰阶
HUE = {
    "rust":     "#D4AF7A",   # 玫瑰金 · 主色 (hero stat / 数字 only)
    "orange":   "#C9B99A",   # 香槟金 · 二级 accent
    "magenta":  "#8B4A5E",   # 深酒红 · 极少用 (warn only)
    "blue":     "#6B7280",   # 石灰蓝 · 中性
    "green":    "#6B6B5C",   # 苔藓灰绿 · 中性
    "olive":    "#8B8579",   # 暖珍珠灰
    "cinnamon": "#A69682",   # 米金
    "gold_p":   "#D4AF7A",   # 玫瑰金 · accent 同主色
}

HUE_ORDER: Tuple[str, ...] = (
    "rust", "orange", "magenta", "blue", "green", "olive", "cinnamon",
)


# ─────────── Typography ───────────
# Didot: 极端 thin-fat 对比 serif · 时装屋招牌
# Bodoni fallback · Playfair Display 最后兜底 (更常见的浏览器 fallback)
# Futura: 几何 sans · kicker 用 all-caps 大字距
FONT_SERIF = ("Didot, Bodoni MT, Bodoni 72, "
              "Playfair Display, GT Sectra, Georgia, serif")
FONT_SANS = ("Futura, Futura PT, ITC Avant Garde Gothic, "
             "Century Gothic, Inter, sans-serif")

TYPE_SCALE = {
    "title":         (36, FONT_SERIF, 300),   # thin weight · Didot italic 招牌
    "subtitle":      (11, FONT_SANS,  500),
    "section":       (9,  FONT_SANS,  500),
    "column_header": (9,  FONT_SANS,  500),
    "hub_name":      (24, FONT_SERIF, 300),
    "hub_name_xl":   (36, FONT_SERIF, 300),
    "block_title":   (16, FONT_SERIF, 400),
    "card_title":    (12, FONT_SERIF, 400),
    "chip_kinase":   (13, FONT_SERIF, 400),
    "chip_label":    (10, FONT_SANS,  500),
    "body_desc":     (9,  FONT_SANS,  400),
    "micro_numeric": (11, FONT_SERIF, 400),
    "footer_read":   (11, FONT_SERIF, 400),
    "footer_italic": (11, FONT_SERIF, 400),
    "kicker_mini":   (8,  FONT_SANS,  500),
    "source_tag":    (9,  FONT_SANS,  500),
}


# ═════════════════════════════════════════════════════════════════
# Palette · COUTURE_NOIR
# ═════════════════════════════════════════════════════════════════

COUTURE_NOIR = Palette(
    name="Couture Noir · Haute Couture / Noir / Rose Gold",
    bg="#0A0A0A",                # 极致深黑 (比 pitch_neon 更纯)
    bg_alt="#141414",            # 微亮层
    bg_dim="#1F1F1F",            # 三级
    ink="#EDE3C6",               # 珍珠白 warm cream (不是纯白)
    gray="rgba(237,227,198,0.5)",# 珍珠白 50% (次要文字)
    hair="#EDE3C6",              # opacity 靠属性叠加
    primary=HUE["rust"],         # 玫瑰金
    primary_dim=HUE["orange"],   # 香槟金
    accent=HUE["gold_p"],        # 玫瑰金 · 同主色
    accent_dim=HUE["cinnamon"],  # 米金
    positive=HUE["gold_p"],      # 时装屋不做正负色 · 都是金
    negative=HUE["magenta"],
    head_family=FONT_SERIF,
    body_family=FONT_SANS,
    mono_family=FONT_SANS,
    kicker_letter_spacing=4.0,   # 极大字距 (haute couture 招牌)
    kicker_case="upper",
    section_numbering="roman",   # 罗马数字
    folio_style="hairline",
    title_style="serif_italic",
    subtitle_style="sans_italic",
    figure_caption_prefix="N°",  # Chanel N°5 招牌
    signature_note="COUTURE NOIR · HAUTE COUTURE / NOIR / ROSE GOLD",
)

PALETTE = COUTURE_NOIR


# ═════════════════════════════════════════════════════════════════
# Filter / gradient / marker · id prefix ea- 保持兼容
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
        'stroke="rgba(237,227,198,0.6)" stroke-width="2.6"/></marker>'
    )
    return "".join(out)


def _resolve_hue(hue_key_or_hex: str) -> str:
    if not hue_key_or_hex:
        return HUE["rust"]
    if hue_key_or_hex.startswith("#"):
        return hue_key_or_hex
    return HUE.get(hue_key_or_hex, HUE["rust"])


def _to_roman(n: int) -> str:
    """整数转罗马数字 (1-20 覆盖 fishbone 分类)."""
    romans = [(10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]
    if n <= 0:
        return str(n)
    out = ""
    for v, sym in romans:
        while n >= v:
            out += sym
            n -= v
    return out


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
                palette: Palette = COUTURE_NOIR,
                canvas: CanvasProfile = HERO_CANVAS,
                include_bg: bool = True) -> str:
    is_embed = (canvas.w == 900 and canvas.h == 336)
    title_sz = 26 if is_embed else 36
    subtitle_sz = 10 if is_embed else 11
    section_sz = 8 if is_embed else 9
    kicker_sz = 8 if is_embed else 9
    parts: List[str] = []
    if include_bg:
        parts.append(_rect(0, 0, canvas.w, canvas.h, fill=palette.bg))
    if kicker:
        parts.append(_txt(canvas.margin_x, canvas.title_y - 20, kicker,
                          size=kicker_sz, family=FONT_SANS, weight=500,
                          fill=palette.primary, letter_em=0.40))
    # title · Didot italic thin (haute couture 招牌)
    if title:
        parts.append(_txt(canvas.margin_x, canvas.title_y, title,
                          size=title_sz, family=FONT_SERIF, weight=300,
                          fill=palette.ink, italic=True, letter_em=0.01))
    if subtitle:
        parts.append(_txt(canvas.margin_x, canvas.subtitle_y, subtitle,
                          size=subtitle_sz, family=FONT_SANS, weight=500,
                          fill=palette.gray, letter_em=0.24))
    # title hairline · 极细珍珠白
    parts.append(_line(canvas.margin_x, canvas.title_hair_y,
                       canvas.w - canvas.margin_x, canvas.title_hair_y,
                       stroke=palette.hair, sw=0.4, opacity=0.35))
    if column_headers:
        for lbl, cx in column_headers:
            parts.append(_txt(cx, canvas.section_hdr_y, lbl,
                              size=section_sz, family=FONT_SANS, weight=500,
                              fill=palette.gray,
                              anchor="middle", letter_em=0.36))
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
                palette: Palette = COUTURE_NOIR,
                canvas: CanvasProfile = HERO_CANVAS,
                min_read_chars: int = 40) -> str:
    _ = (caption, source, read_lines, italic_last, palette, canvas, min_read_chars)
    return ""


def tspan(word: str, *, color: str = HUE["rust"], weight: int = 400) -> str:
    """READ 段内高亮 · 默认玫瑰金 · italic (haute couture 招牌)."""
    c = _resolve_hue(color) if not color.startswith("rgba") else color
    return (f'<tspan font-weight="{weight}" font-style="italic" fill="{c}">'
            f'{esc(word)}</tspan>')


# ═════════════════════════════════════════════════════════════════
# Skin 契约 · draw_node · haute couture opt-in 分流
# 视觉核心:
#   - 大量 white space (padding 30+px)
#   - 极粗横线 (weight 3) 夹极细内文 (weight 0.4)
#   - Didot italic thin + Futura all-caps kicker
#   - 罗马数字 (I/II/III/IV) 替代 M1/M2/M3
#   - 玫瑰金 accent 只用在 hero stat
#   - 无圆角 · 无 tint · 无 shadow · 无 filter
# 3 kind: category_card / kpi_card / problem_statement
# ═════════════════════════════════════════════════════════════════

class CoutureNoirSkin:
    """Couture Noir · Haute Couture 时装屋手册 · 极致克制."""

    name = "couture_noir"

    # 用于给分类卡编罗马数字 · fishbone 有 6 分类, 每次 draw_node 递增
    def __init__(self):
        self._roman_counter = 0

    def draw_node(self, x: float, y: float, w: float, h: float,
                  label: str, palette: Palette,
                  kind: str = "", **kwargs) -> Optional[str]:
        pal = palette or COUTURE_NOIR
        if kind == "category_card":
            return self._category_card(x, y, w, h, label, pal, **kwargs)
        if kind == "kpi_card":
            return self._kpi_card(x, y, w, h, label, pal, **kwargs)
        if kind == "problem_statement":
            # 每次问一次新数据时 reset (fishbone 是一次 render 一份 data)
            self._roman_counter = 0
            return self._problem_statement(x, y, w, h, pal, label=label, **kwargs)
        # ── mindmap hub (opt-in · mp_mindmap preset 用) ──
        if kind == "mindmap_hub":
            return self._mindmap_hub(x, y, w, h, label, pal, **kwargs)
        # ── tree preset · 极黑 + 玫瑰金 · N° 罗马 · 无 rx ──
        if kind == "tree_pillar_card":
            return self._tree_pillar_card(x, y, w, h, pal, **kwargs)
        if kind == "tree_cap_card":
            return self._tree_cap_card(x, y, w, h, pal, **kwargs)
        if kind == "tree_root_pill":
            return self._tree_root_pill(x, y, w, h, pal, **kwargs)
        # ── kp_kpi preset (极黑 + 玫瑰金 · 无 rx · 极粗上线) ──
        if kind == "kpi_hub_card":
            return self._kpi_hub_card(x, y, w, h, pal, **kwargs)
        if kind == "kpi_driver_card":
            return self._kpi_driver_card(x, y, w, h, pal, **kwargs)
        if kind == "kpi_leaf_card":
            return self._kpi_leaf_card(x, y, w, h, pal, **kwargs)
        # ── bl_bloom preset ──
        if kind == "bloom_tier_rect":
            return self._bloom_tier_rect(x, y, w, h, pal, **kwargs)
        # ── e2_5why preset ──
        if kind == "why_chain_card":
            return self._why_chain_card(x, y, w, h, pal, **kwargs)
        return None

    # ─────────── category_card · 极粗上横线 + 罗马数字 + Didot italic ───────────
    def _category_card(self, x, y, w, h, label, pal, **kw) -> str:
        rose = _resolve_hue("rust")          # 玫瑰金
        subtitle = kw.get("subtitle", "")
        pct = kw.get("pct", "")

        self._roman_counter += 1
        roman = _to_roman(self._roman_counter)

        parts: List[str] = []
        # 极粗顶横线 (珍珠白 sw=1.8) · haute couture 招牌
        parts.append(
            f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x + w:.1f}" y2="{y:.1f}" '
            f'stroke="{pal.ink}" stroke-width="1.8"/>'
        )
        # 底部极细横线 (opacity 0.25 · 若隐若现)
        parts.append(
            f'<line x1="{x:.1f}" y1="{y + h:.1f}" '
            f'x2="{x + w:.1f}" y2="{y + h:.1f}" '
            f'stroke="{pal.ink}" stroke-width="0.35" opacity="0.28"/>'
        )
        # 罗马数字 · Didot italic 玫瑰金 (Chanel N° 招牌)
        parts.append(
            f'<text x="{x + 4:.1f}" y="{y + 17:.1f}" '
            f'font-family="{FONT_SERIF}" font-size="12" font-weight="400" '
            f'font-style="italic" fill="{rose}" letter-spacing="0.02em">'
            f'N° {esc(roman)}</text>'
        )
        # label · Futura all-caps 珍珠白 · 极大字距
        parts.append(
            f'<text x="{x + 44:.1f}" y="{y + 17:.1f}" '
            f'font-family="{FONT_SANS}" font-size="10" font-weight="500" '
            f'fill="{pal.ink}" letter-spacing="0.32em">'
            f'{esc(label.upper())}</text>'
        )
        if subtitle:
            # subtitle · Didot italic gray
            parts.append(
                f'<text x="{x + 44:.1f}" y="{y + 30:.1f}" '
                f'font-family="{FONT_SERIF}" font-size="9.5" font-weight="400" '
                f'font-style="italic" fill="{pal.gray}" letter-spacing="0.04em">'
                f'{esc(subtitle)}</text>'
            )
        # pct · Didot italic 玫瑰金 (hero 数字招牌)
        if pct:
            parts.append(
                f'<text x="{x + w - 4:.1f}" y="{y + 17:.1f}" '
                f'text-anchor="end" font-family="{FONT_SERIF}" '
                f'font-size="16" font-weight="400" font-style="italic" '
                f'fill="{rose}" letter-spacing="-0.01em">'
                f'{esc(pct)}</text>'
            )
        return "".join(parts)

    # ─────────── kpi_card · 极粗底线 + Didot italic value · 罗马编号 ───────────
    def _kpi_card(self, x, y, w, h, label, pal, **kw) -> str:
        rose = _resolve_hue("rust")
        value = kw.get("value", "")
        note = kw.get("note", "")
        parts: List[str] = []
        # 无框 · 只有底部极粗珍珠白横线 (haute couture lookbook 招牌)
        parts.append(
            f'<line x1="{x:.1f}" y1="{y + h:.1f}" '
            f'x2="{x + w:.1f}" y2="{y + h:.1f}" '
            f'stroke="{pal.ink}" stroke-width="1.6"/>'
        )
        # kicker · Futura all-caps 珍珠白 · 极大字距
        if label:
            parts.append(
                f'<text x="{x + 2:.1f}" y="{y + 11:.1f}" '
                f'font-family="{FONT_SANS}" font-size="8" font-weight="500" '
                f'fill="{pal.ink}" letter-spacing="0.32em">'
                f'{esc(label.upper())}</text>'
            )
        # value · Didot italic thin 玫瑰金 · 大字号 (hero 数字)
        if value:
            parts.append(
                f'<text x="{x + 2:.1f}" y="{y + 32:.1f}" '
                f'font-family="{FONT_SERIF}" font-size="20" font-weight="300" '
                f'font-style="italic" fill="{rose}" letter-spacing="-0.01em">'
                f'{esc(value)}</text>'
            )
        # note · Futura italic gray · 右侧极小字
        if note:
            parts.append(
                f'<text x="{x + w - 4:.1f}" y="{y + 32:.1f}" '
                f'text-anchor="end" font-family="{FONT_SERIF}" font-size="9" '
                f'font-style="italic" fill="{pal.gray}" letter-spacing="0.06em">'
                f'{esc(note)}</text>'
            )
        return "".join(parts)

    # ─────────── problem_statement · 极致 haute couture · lookbook 招牌 ───────────
    def _problem_statement(self, x, y, w, h, pal, **kw) -> str:
        rose = _resolve_hue("rust")
        kicker = kw.get("kicker", "MAISON")
        label = kw.get("label", "")
        stat = kw.get("stat", "")
        range_txt = kw.get("range", "")
        parts: List[str] = []
        cx = x + w / 2

        # ─── 极致克制布局: 极粗顶线 + 极细底线 · 中间纯 typography ───
        # 极粗顶线 (珍珠白 sw=2.5 · 时装屋招牌)
        parts.append(
            f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x + w:.1f}" y2="{y:.1f}" '
            f'stroke="{pal.ink}" stroke-width="2.5"/>'
        )
        # 极粗底线
        parts.append(
            f'<line x1="{x:.1f}" y1="{y + h:.1f}" '
            f'x2="{x + w:.1f}" y2="{y + h:.1f}" '
            f'stroke="{pal.ink}" stroke-width="2.5"/>'
        )
        # 左侧极细竖线 (印刷手册书脊味)
        parts.append(
            f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x:.1f}" y2="{y + h:.1f}" '
            f'stroke="{pal.ink}" stroke-width="0.5" opacity="0.4"/>'
        )
        # 右侧极细竖线
        parts.append(
            f'<line x1="{x + w:.1f}" y1="{y:.1f}" '
            f'x2="{x + w:.1f}" y2="{y + h:.1f}" '
            f'stroke="{pal.ink}" stroke-width="0.5" opacity="0.4"/>'
        )

        # kicker · Futura all-caps 玫瑰金 · 极大字距 (Chanel N° tag)
        parts.append(
            f'<text x="{cx:.1f}" y="{y + 34:.1f}" text-anchor="middle" '
            f'font-family="{FONT_SANS}" font-size="9" font-weight="500" '
            f'fill="{rose}" letter-spacing="0.44em">'
            f'{esc(kicker)}</text>'
        )
        # 装饰性小 dot (奢华手册常见)
        parts.append(
            f'<circle cx="{cx:.1f}" cy="{y + 46:.1f}" r="1.5" fill="{rose}"/>'
        )
        # label · Didot italic thin 珍珠白
        if label:
            parts.append(
                f'<text x="{cx:.1f}" y="{y + 72:.1f}" text-anchor="middle" '
                f'font-family="{FONT_SERIF}" font-size="14" font-style="italic" '
                f'font-weight="300" fill="{pal.ink}" letter-spacing="0.08em">'
                f'{esc(label)}</text>'
            )
        if stat:
            # hero stat · Didot italic thin 玫瑰金 · 极端大字号
            # thin weight (300) 是 Didot 招牌的极端 thin-fat 对比
            parts.append(
                f'<text x="{cx:.1f}" y="{y + 118:.1f}" text-anchor="middle" '
                f'font-family="{FONT_SERIF}" font-size="52" font-weight="300" '
                f'font-style="italic" fill="{rose}" letter-spacing="-0.02em">'
                f'{esc(stat)}</text>'
            )
        if range_txt:
            # divider · 极细横线
            parts.append(
                f'<line x1="{cx - 30:.1f}" y1="{y + h - 32:.1f}" '
                f'x2="{cx + 30:.1f}" y2="{y + h - 32:.1f}" '
                f'stroke="{pal.ink}" stroke-width="0.3" opacity="0.5"/>'
            )
            parts.append(
                f'<text x="{cx:.1f}" y="{y + h - 16:.1f}" text-anchor="middle" '
                f'font-family="{FONT_SANS}" font-size="8.5" font-weight="500" '
                f'fill="{pal.gray}" letter-spacing="0.28em">'
                f'{esc(range_txt.upper())}</text>'
            )
        return "".join(parts)

    # ═══════════════════════════════════════════════════════════
    # mindmap hub · haute couture 招牌
    # 极黑圆 + 珍珠白 hairline 双圆 + Didot italic thin name + 玫瑰金 stat
    # ═══════════════════════════════════════════════════════════

    def _mindmap_hub(self, x, y, w, h, name, pal, **kw) -> str:
        """couture · 极黑圆 + 珍珠白 hairline + Didot italic thin name."""
        rose = _resolve_hue("rust")            # 玫瑰金
        kicker = kw.get("kicker", "")
        stat = kw.get("stat", "")
        stat_note = kw.get("stat_note", "")
        cx = kw.get("hub_cx", x + w / 2)
        cy = kw.get("hub_cy", y + h / 2)
        r = kw.get("hub_r", w / 2)
        parts: List[str] = []
        # 极黑主圆 (无阴影 · 无 tint · 极致克制)
        parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{pal.bg}"/>'
        )
        # 双 hairline: 外粗珍珠白 + 内细玫瑰金
        parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" '
            f'stroke="{pal.ink}" stroke-width="1.4"/>'
        )
        parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r - 8}" fill="none" '
            f'stroke="{rose}" stroke-width="0.5" opacity="0.6"/>'
        )
        # kicker · Futura all-caps 玫瑰金 · N° 前缀
        if kicker:
            parts.append(
                f'<text x="{cx}" y="{cy - 34:.1f}" text-anchor="middle" '
                f'font-family="{FONT_SANS}" font-size="8.5" '
                f'fill="{rose}" font-weight="500" letter-spacing="0.44em">'
                f'{esc("N° " + kicker.upper())}</text>'
            )
            # 装饰 dot
            parts.append(
                f'<circle cx="{cx}" cy="{cy - 22:.1f}" r="1.5" fill="{rose}"/>'
            )
        # name · Didot italic thin 珍珠白 (Chanel invitation 招牌)
        if name:
            parts.append(
                f'<text x="{cx}" y="{cy + 4}" text-anchor="middle" '
                f'font-family="{FONT_SERIF}" font-size="24" '
                f'font-style="italic" font-weight="300" fill="{pal.ink}" '
                f'letter-spacing="0.04em">'
                f'{esc(name)}</text>'
            )
        # stat · Didot italic thin 玫瑰金
        if stat:
            parts.append(
                f'<text x="{cx}" y="{cy + 30}" text-anchor="middle" '
                f'font-family="{FONT_SERIF}" font-size="18" '
                f'font-style="italic" font-weight="300" fill="{rose}" '
                f'letter-spacing="-0.01em">'
                f'{esc(stat)}</text>'
            )
        # note · Futura all-caps 珍珠白 opacity 0.5
        if stat_note:
            parts.append(
                f'<text x="{cx}" y="{cy + 48:.1f}" text-anchor="middle" '
                f'font-family="{FONT_SANS}" font-size="7" '
                f'fill="{pal.ink}" opacity="0.55" '
                f'letter-spacing="0.28em">'
                f'{esc(stat_note.upper())}</text>'
            )
        return "".join(parts)

    # ─────────── tree 系 · 极黑 + 玫瑰金 · 无 rx · 极粗上横线 ───────────
    def _tree_pillar_card(self, x, y, w, h, pal, hue="rust", hue_color=None,
                          band_h=28, **kw) -> str:
        """couture 立柱: 深黑底 + 玫瑰金顶粗线 (2px) + 底部玫瑰金 hairline."""
        rose_gold = HUE.get("gold_p", "#B8956B")
        parts = []
        # 主体 · 无 rx · 极黑
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'fill="{pal.bg_alt or pal.bg}"/>'
        )
        # 顶部粗玫瑰金横线 (2px · couture 招牌)
        parts.append(
            f'<line x1="{x:.1f}" y1="{y + 1:.1f}" x2="{x + w:.1f}" y2="{y + 1:.1f}" '
            f'stroke="{rose_gold}" stroke-width="2"/>'
        )
        # 顶部 band (深黑上稍浅) 承载 kicker/title
        parts.append(
            f'<rect x="{x:.1f}" y="{y + 3:.1f}" width="{w:.1f}" '
            f'height="{band_h - 3:.1f}" fill="rgba(30,30,30,1)"/>'
        )
        # 底部细金 hairline
        parts.append(
            f'<line x1="{x + 8:.1f}" y1="{y + h - 1:.1f}" '
            f'x2="{x + w - 8:.1f}" y2="{y + h - 1:.1f}" '
            f'stroke="{rose_gold}" stroke-width="0.5" opacity="0.7"/>'
        )
        return "".join(parts)

    def _tree_cap_card(self, x, y, w, h, pal, hue="rust", hue_color=None,
                       rail_w=4, **kw) -> str:
        """couture capability: 极黑 + 玫瑰金极细 hairline 边框 · 无 rail."""
        rose_gold = HUE.get("gold_p", "#B8956B")
        parts = []
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'fill="{pal.bg_alt or pal.bg}" '
            f'stroke="{rose_gold}" stroke-width="0.4" opacity="0.75"/>'
        )
        # 顶部玫瑰金极细线 (无 rail, 只保留一根线)
        parts.append(
            f'<line x1="{x + 4:.1f}" y1="{y + 4:.1f}" '
            f'x2="{x + w - 4:.1f}" y2="{y + 4:.1f}" '
            f'stroke="{rose_gold}" stroke-width="0.8" opacity="0.85"/>'
        )
        return "".join(parts)

    def _tree_root_pill(self, x, y, w, h, pal, hue="navy", **kw) -> str:
        """couture root: 极黑 + 玫瑰金双 hairline · 无 rx."""
        rose_gold = HUE.get("gold_p", "#B8956B")
        parts = []
        # halo (玫瑰金极细外框)
        parts.append(
            f'<rect x="{x - 4:.1f}" y="{y - 4:.1f}" '
            f'width="{w + 8:.1f}" height="{h + 8:.1f}" '
            f'fill="none" stroke="{rose_gold}" stroke-width="0.4"/>'
        )
        # 主体 · 无 rx · 极黑
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'fill="{pal.bg}"/>'
        )
        # 顶粗横线 (2px 玫瑰金)
        parts.append(
            f'<line x1="{x:.1f}" y1="{y + 1:.1f}" x2="{x + w:.1f}" y2="{y + 1:.1f}" '
            f'stroke="{rose_gold}" stroke-width="2"/>'
        )
        return "".join(parts)

    # ─────────── kp_kpi 系 · 极黑 + 玫瑰金 · 无 rx · 极粗上线 ───────────
    def _kpi_hub_card(self, x, y, w, h, pal, hue="gold_hub", **kw) -> str:
        """north-star hub · 极黑 + 双玫瑰金外框 + 顶粗 3px 玫瑰金."""
        rose_gold = HUE.get("gold_p", "#B8956B")
        parts = []
        # 外框
        parts.append(
            f'<rect x="{x - 5:.1f}" y="{y - 5:.1f}" '
            f'width="{w + 10:.1f}" height="{h + 10:.1f}" '
            f'fill="none" stroke="{rose_gold}" stroke-width="0.4" opacity="0.65"/>'
        )
        # 主体
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'fill="{pal.bg}"/>'
        )
        # 顶部粗玫瑰金 3px
        parts.append(
            f'<line x1="{x:.1f}" y1="{y + 1.5:.1f}" x2="{x + w:.1f}" y2="{y + 1.5:.1f}" '
            f'stroke="{rose_gold}" stroke-width="3"/>'
        )
        return "".join(parts)

    def _kpi_driver_card(self, x, y, w, h, pal, hue="rust", **kw) -> str:
        """driver card · 极黑 + 顶部玫瑰金 2px + 底部细金 hairline."""
        rose_gold = HUE.get("gold_p", "#B8956B")
        parts = []
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'fill="{pal.bg_alt or pal.bg}"/>'
        )
        # 顶部粗玫瑰金
        parts.append(
            f'<line x1="{x:.1f}" y1="{y + 1:.1f}" x2="{x + w:.1f}" y2="{y + 1:.1f}" '
            f'stroke="{rose_gold}" stroke-width="2"/>'
        )
        # 底部细 hairline
        parts.append(
            f'<line x1="{x + 8:.1f}" y1="{y + h - 1:.1f}" '
            f'x2="{x + w - 8:.1f}" y2="{y + h - 1:.1f}" '
            f'stroke="{rose_gold}" stroke-width="0.5" opacity="0.65"/>'
        )
        return "".join(parts)

    def _kpi_leaf_card(self, x, y, w, h, pal, hue="rust", compact=False, **kw) -> str:
        """leaf card · 极黑 + 玫瑰金极细边框."""
        rose_gold = HUE.get("gold_p", "#B8956B")
        parts = []
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'fill="{pal.bg_alt or pal.bg}" '
            f'stroke="{rose_gold}" stroke-width="0.4" opacity="0.75"/>'
        )
        # 顶部极细金线
        parts.append(
            f'<line x1="{x + 4:.1f}" y1="{y + 3:.1f}" '
            f'x2="{x + w - 4:.1f}" y2="{y + 3:.1f}" '
            f'stroke="{rose_gold}" stroke-width="0.7" opacity="0.85"/>'
        )
        return "".join(parts)


    def _bloom_tier_rect(self, x, y, w, h, pal, hue="rust", hue_color=None, **kw) -> str:
        rose_gold = HUE.get("gold_p", "#B8956B")
        parts = []
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'fill="{pal.bg_alt or pal.bg}"/>'
        )
        # 顶部粗玫瑰金 2px
        parts.append(
            f'<line x1="{x:.1f}" y1="{y + 1:.1f}" x2="{x + w:.1f}" y2="{y + 1:.1f}" '
            f'stroke="{rose_gold}" stroke-width="2"/>'
        )
        # 底部细金 hairline
        parts.append(
            f'<line x1="{x + 6:.1f}" y1="{y + h - 1:.1f}" x2="{x + w - 6:.1f}" y2="{y + h - 1:.1f}" '
            f'stroke="{rose_gold}" stroke-width="0.5" opacity="0.65"/>'
        )
        return "".join(parts)


    def _why_chain_card(self, x, y, w, h, pal, hue="rust", hue_color=None, is_root=False, **kw) -> str:
        rose_gold = HUE.get("gold_p", "#B8956B")
        parts = []
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w}" height="{h}" '
            f'fill="{pal.bg_alt or pal.bg}"/>'
        )
        stroke_w = "3" if is_root else "2"
        parts.append(
            f'<line x1="{x:.1f}" y1="{y + 1:.1f}" x2="{x + w}" y2="{y + 1:.1f}" '
            f'stroke="{rose_gold}" stroke-width="{stroke_w}"/>'
        )
        return "".join(parts)


COUTURE_NOIR_SKIN = CoutureNoirSkin()
SKIN_INSTANCE = COUTURE_NOIR_SKIN


__all__ = [
    # Palette
    "COUTURE_NOIR", "PALETTE",
    # Skin class
    "CoutureNoirSkin", "COUTURE_NOIR_SKIN", "SKIN_INSTANCE",
    # Canvas
    "CanvasProfile", "HERO_CANVAS", "EMBED_CANVAS", "TX_CANVAS",
    # Tokens
    "HUE", "HUE_ORDER", "TYPE_SCALE", "FONT_SERIF", "FONT_SANS",
    # Chrome
    "svg_defs", "hero_chrome", "hero_footer", "tspan",
]
