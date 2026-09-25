"""
Skin · pitch_ivory · Ivory / Coral / Ink 白底 pitch 风

pitch_neon 的白底孪生版:
    * bg=#FBF7EE 象牙白(cream broadsheet · 报纸质感)
    * primary=#E5674C 珊瑚桃(pitch 戏剧感的浅底替代)
    * accent=#D4A017 mustard 金(强调 stat/highlight)
    * ink=#1A1614 深墨(比纯黑温暖)
    * 字体: Playfair Display italic 大字号(pitch 招牌) + Inter 正文
    * 装饰母题: 大字号 stat · italic label · hairline · 珊瑚桃色条

跟 pitch_neon 反过来: 深底荧光 → 浅底珊瑚. 保持"戏剧化 · 大字号 · italic"的
pitch 骨架, 但改成路演白底手册风格. 适合印刷手册 / BP / A轮宣讲页.

canvas 契约: 全部复用 editorial_atelier(HERO 1400×820 · EMBED 900×336)
"""
from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

from ..engine import esc
from ..palettes import Palette
# 复用 editorial_atelier 的几何 helper(_txt / _rect / _line / _tint · 不含配色)
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
# Canvas · 复用 editorial_atelier 的 CanvasProfile
# ═════════════════════════════════════════════════════════════════

HERO_CANVAS = _EA_HERO_CANVAS
EMBED_CANVAS = _EA_EMBED_CANVAS
TX_CANVAS = _EA_TX_CANVAS


# ─────────── Hue table ───────────
# 8 支 hue · 主色系走珊瑚桃(rust slot) + mustard 金 accent · 副 hue 走深浅棕暖调
# 保持 key 名不变(preset 按 key 索引) · 白底轻盈但保留 pitch 温度
HUE = {
    "rust":     "#E5674C",   # 珊瑚桃 · 主色(pitch 白底戏剧色)
    "orange":   "#F0A375",   # 桃粉 tint · secondary
    "magenta":  "#B23A5A",   # 深玫红 · 强调 / warn / 负 delta
    "blue":     "#3F5F7A",   # 冷墨蓝 · 结构色(不喧宾)
    "green":    "#5A7B4E",   # 橄榄绿 · 正 delta(不亮)
    "olive":    "#8A7A5C",   # 卡其暖灰
    "cinnamon": "#8B5A3C",   # 肉桂棕
    "gold_p":   "#D4A017",   # mustard 金 · accent slot (stat 强调)
}

HUE_ORDER: Tuple[str, ...] = (
    "rust", "orange", "magenta", "blue", "green", "olive", "cinnamon",
)


# ─────────── Typography ───────────
# Playfair Display italic 作 hero 大字号(SERIF 22-42pt) + Inter 正文(SANS 9-13pt)
FONT_SANS = "Inter, Söhne, Helvetica Neue, Arial, sans-serif"
FONT_SERIF = "Playfair Display, Georgia, GT Sectra, serif"

TYPE_SCALE = {
    "title":         (32, FONT_SERIF, 700),
    "subtitle":      (13, FONT_SANS,  500),
    "section":       (10, FONT_SANS,  700),
    "column_header": (10, FONT_SANS,  700),
    "hub_name":      (22, FONT_SERIF, 700),
    "hub_name_xl":   (32, FONT_SERIF, 700),
    "block_title":   (18, FONT_SERIF, 700),
    "card_title":    (13, FONT_SANS,  800),
    "chip_kinase":   (14, FONT_SANS,  800),
    "chip_label":    (11, FONT_SANS,  700),
    "body_desc":     (10, FONT_SANS,  500),
    "micro_numeric": (10, FONT_SANS,  700),
    "footer_read":   (12, FONT_SANS,  500),
    "footer_italic": (11, FONT_SERIF, 500),
    "kicker_mini":   (9,  FONT_SANS,  700),
    "source_tag":    (10, FONT_SANS,  700),
}


# ═════════════════════════════════════════════════════════════════
# Palette · PITCH_IVORY
# ═════════════════════════════════════════════════════════════════

PITCH_IVORY = Palette(
    name="Pitch Ivory · Cream / Coral / Ink",
    bg="#FBF7EE",              # 象牙 cream
    bg_alt="#F3EEE0",          # 次背景 · card
    bg_dim="#E8E1CE",          # 三级背景
    ink="#1A1614",             # 深墨(比纯黑温暖)
    gray="rgba(120,110,96,1)", # 暖灰(米底适配)
    hair="#1A1614",            # opacity 靠属性叠加
    primary=HUE["rust"],       # 珊瑚桃
    primary_dim=HUE["orange"], # 桃粉
    accent=HUE["gold_p"],      # mustard 金
    accent_dim=HUE["cinnamon"],
    positive=HUE["green"],
    negative=HUE["magenta"],
    head_family=FONT_SERIF,
    body_family=FONT_SANS,
    mono_family=FONT_SANS,
    kicker_letter_spacing=2.8,
    kicker_case="upper",
    section_numbering="arabic",
    folio_style="hairline",
    title_style="serif_italic",
    subtitle_style="sans_italic",
    figure_caption_prefix="Fig.",
    signature_note="PITCH IVORY · CREAM / CORAL / INK",
)

PALETTE = PITCH_IVORY


# ═════════════════════════════════════════════════════════════════
# Filter / gradient / marker (id prefix 复用 ea-)
# ═════════════════════════════════════════════════════════════════

_FILTER_DEFS = """<filter id="ea-soft-shadow" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur in="SourceAlpha" stdDeviation="2"/><feOffset dx="0" dy="1.5"/><feComponentTransfer><feFuncA type="linear" slope="0.22"/></feComponentTransfer><feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge></filter><filter id="ea-hub-shadow" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur in="SourceAlpha" stdDeviation="3.5"/><feOffset dx="0" dy="2.5"/><feComponentTransfer><feFuncA type="linear" slope="0.28"/></feComponentTransfer><feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge></filter><filter id="ea-hub-halo" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur in="SourceGraphic" stdDeviation="5.5"/></filter>"""


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
        'stroke="rgba(94,80,62,0.85)" stroke-width="2.6"/></marker>'
    )
    return "".join(out)


def _resolve_hue(hue_key_or_hex: str) -> str:
    if not hue_key_or_hex:
        return HUE["rust"]
    if hue_key_or_hex.startswith("#"):
        return hue_key_or_hex
    return HUE.get(hue_key_or_hex, HUE["rust"])


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
                palette: Palette = PITCH_IVORY,
                canvas: CanvasProfile = HERO_CANVAS,
                include_bg: bool = True) -> str:
    is_embed = (canvas.w == 900 and canvas.h == 336)
    title_sz = 24 if is_embed else 34
    subtitle_sz = 10 if is_embed else 13
    section_sz = 8 if is_embed else 10
    kicker_sz = 8 if is_embed else 10
    parts: List[str] = []
    if include_bg:
        parts.append(_rect(0, 0, canvas.w, canvas.h, fill=palette.bg))
    if kicker:
        parts.append(_txt(canvas.margin_x, canvas.title_y - 20, kicker,
                          size=kicker_sz, family=FONT_SANS, weight=700,
                          fill=palette.primary, letter_em=0.22))
    # title · Playfair italic 珊瑚桃(pitch 招牌)
    if title:
        parts.append(_txt(canvas.margin_x, canvas.title_y, title,
                          size=title_sz, family=FONT_SERIF, weight=700,
                          fill=palette.ink, italic=True, letter_em=0.005))
    if subtitle:
        parts.append(_txt(canvas.margin_x, canvas.subtitle_y, subtitle,
                          size=subtitle_sz, family=FONT_SANS, weight=500,
                          fill=palette.gray, letter_em=0.04))
    # title hairline · 珊瑚桃
    parts.append(_line(canvas.margin_x, canvas.title_hair_y,
                       canvas.w - canvas.margin_x, canvas.title_hair_y,
                       stroke=palette.primary, sw=0.8, opacity=0.5))
    if column_headers:
        for lbl, cx in column_headers:
            parts.append(_txt(cx, canvas.section_hdr_y, lbl,
                              size=section_sz, family=FONT_SANS, weight=700,
                              fill=palette.primary,
                              anchor="middle", letter_em=0.26))
    if encoding_note_right:
        note_sz = 9 if is_embed else 11
        parts.append(_txt(canvas.w - canvas.margin_x, canvas.subtitle_y,
                          encoding_note_right,
                          size=note_sz, family=FONT_SANS, weight=500,
                          fill=palette.gray, anchor="end", italic=True))
    return "".join(parts)


def hero_footer(*, caption: str = "",
                source: str = "",
                read_lines: Optional[Sequence[str]] = None,
                italic_last: bool = False,
                palette: Palette = PITCH_IVORY,
                canvas: CanvasProfile = HERO_CANVAS,
                min_read_chars: int = 40) -> str:
    """底部 chrome · 保持关闭(与 editorial 一致)."""
    _ = (caption, source, read_lines, italic_last, palette, canvas, min_read_chars)
    return ""


def tspan(word: str, *, color: str = HUE["rust"], weight: int = 700) -> str:
    """READ 段内高亮 · 默认色改为珊瑚桃."""
    c = _resolve_hue(color) if not color.startswith("rgba") else color
    return (f'<tspan font-weight="{weight}" fill="{c}">'
            f'{esc(word)}</tspan>')


# ═════════════════════════════════════════════════════════════════
# Skin 契约 · draw_node · opt-in 分流(照 pitch_neon 结构)
# 3 kind: category_card / kpi_card / problem_statement
# 风格: 象牙底 · 珊瑚桃 hairline · Playfair italic 大字号 · mustard 金 stat
# ═════════════════════════════════════════════════════════════════

class PitchIvorySkin:
    """Pitch Ivory · 白底 pitch 风 · 象牙白 + 珊瑚桃 + Playfair italic."""

    name = "pitch_ivory"

    def draw_node(self, x: float, y: float, w: float, h: float,
                  label: str, palette: Palette,
                  kind: str = "", **kwargs) -> Optional[str]:
        pal = palette or PITCH_IVORY
        if kind == "category_card":
            return self._category_card(x, y, w, h, label, pal, **kwargs)
        if kind == "kpi_card":
            return self._kpi_card(x, y, w, h, label, pal, **kwargs)
        if kind == "problem_statement":
            return self._problem_statement(x, y, w, h, pal, label=label, **kwargs)
        return None

    # ─────────── category_card ───────────
    def _category_card(self, x, y, w, h, label, pal, **kw) -> str:
        hue = kw.get("hue", "rust")
        hue_c = _resolve_hue(hue)
        coral = _resolve_hue("rust")
        subtitle = kw.get("subtitle", "")
        pct = kw.get("pct", "")
        parts: List[str] = []
        # bg_alt cream 底 · rx=4 圆角 · 珊瑚桃 hairline
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w}" height="{h}" '
            f'rx="4" fill="{pal.bg_alt}" stroke="{coral}" stroke-width="0.9"/>'
        )
        # 顶部 accent 光带 (hue color 做分类识别)
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w}" height="2" '
            f'rx="1" fill="{hue_c}" opacity="0.85"/>'
        )
        # label · Playfair italic 深墨
        parts.append(
            f'<text x="{x + 10:.1f}" y="{y + 18:.1f}" '
            f'font-family="{FONT_SERIF}" font-size="13" font-weight="700" '
            f'font-style="italic" fill="{pal.ink}" letter-spacing="0.01em">'
            f'{esc(label)}</text>'
        )
        if subtitle:
            parts.append(
                f'<text x="{x + 10:.1f}" y="{y + 31:.1f}" '
                f'font-family="{FONT_SANS}" font-size="8.5" '
                f'fill="{pal.gray}" letter-spacing="0.06em">'
                f'{esc(subtitle)}</text>'
            )
        if pct:
            parts.append(
                f'<text x="{x + w - 8:.1f}" y="{y + 18:.1f}" '
                f'text-anchor="end" font-family="{FONT_SERIF}" '
                f'font-size="13" font-weight="700" font-style="italic" '
                f'fill="{coral}">{esc(pct)}</text>'
            )
        return "".join(parts)

    # ─────────── kpi_card ───────────
    def _kpi_card(self, x, y, w, h, label, pal, **kw) -> str:
        coral = _resolve_hue("rust")
        value = kw.get("value", "")
        note = kw.get("note", "")
        parts: List[str] = []
        # 无框 · 只有左侧 3px 珊瑚桃竖条
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="3" height="{h}" '
            f'fill="{coral}"/>'
        )
        # kicker · 珊瑚桃 uppercase spaced
        if label:
            parts.append(
                f'<text x="{x + 10:.1f}" y="{y + 12:.1f}" '
                f'font-family="{FONT_SANS}" font-size="8" font-weight="700" '
                f'fill="{coral}" letter-spacing="0.18em">'
                f'{esc(label.upper())}</text>'
            )
        # value · Playfair italic 深墨 (大字号)
        if value:
            parts.append(
                f'<text x="{x + 10:.1f}" y="{y + 30:.1f}" '
                f'font-family="{FONT_SERIF}" font-size="18" font-weight="700" '
                f'font-style="italic" fill="{pal.ink}">'
                f'{esc(value)}</text>'
            )
        if note:
            parts.append(
                f'<text x="{x + w - 4:.1f}" y="{y + 30:.1f}" '
                f'text-anchor="end" font-family="{FONT_SANS}" font-size="9" '
                f'font-style="italic" fill="{pal.gray}">'
                f'{esc(note)}</text>'
            )
        return "".join(parts)

    # ─────────── problem_statement ───────────
    def _problem_statement(self, x, y, w, h, pal, **kw) -> str:
        coral = _resolve_hue("rust")
        mustard = _resolve_hue("gold_p")
        kicker = kw.get("kicker", "PROBLEM STATEMENT")
        label = kw.get("label", "")
        stat = kw.get("stat", "")
        range_txt = kw.get("range", "")
        parts: List[str] = []
        cx = x + w / 2
        # bg_alt cream 底 · rx=14 · 珊瑚桃 hairline (无 glow · 干净白底)
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w}" height="{h}" '
            f'rx="14" fill="{pal.bg_alt}" stroke="{coral}" stroke-width="1.4"/>'
        )
        # 内嵌 hairline 边框 · 复古手册感
        parts.append(
            f'<rect x="{x + 6:.1f}" y="{y + 6:.1f}" '
            f'width="{w - 12}" height="{h - 12}" '
            f'rx="10" fill="none" stroke="{coral}" stroke-width="0.5" '
            f'opacity="0.4"/>'
        )
        # kicker · 珊瑚桃 uppercase spaced
        parts.append(
            f'<text x="{cx:.1f}" y="{y + 28:.1f}" text-anchor="middle" '
            f'font-family="{FONT_SANS}" font-size="9" font-weight="700" '
            f'fill="{coral}" letter-spacing="0.24em">'
            f'{esc(kicker)}</text>'
        )
        parts.append(
            f'<line x1="{cx - 30:.1f}" y1="{y + 36:.1f}" '
            f'x2="{cx + 30:.1f}" y2="{y + 36:.1f}" '
            f'stroke="{coral}" stroke-width="0.6" opacity="0.5"/>'
        )
        if label:
            parts.append(
                f'<text x="{cx:.1f}" y="{y + 58:.1f}" text-anchor="middle" '
                f'font-family="{FONT_SERIF}" font-size="15" font-style="italic" '
                f'font-weight="600" fill="{pal.ink}">'
                f'{esc(label)}</text>'
            )
        if stat:
            # 大 stat · Playfair italic mustard 金 (pitch 白底招牌)
            parts.append(
                f'<text x="{cx:.1f}" y="{y + 104:.1f}" text-anchor="middle" '
                f'font-family="{FONT_SERIF}" font-size="42" font-weight="700" '
                f'font-style="italic" fill="{mustard}">'
                f'{esc(stat)}</text>'
            )
        if range_txt:
            parts.append(
                f'<text x="{cx:.1f}" y="{y + 132:.1f}" text-anchor="middle" '
                f'font-family="{FONT_SANS}" font-size="9.5" '
                f'fill="{pal.gray}" letter-spacing="0.1em">'
                f'{esc(range_txt)}</text>'
            )
        return "".join(parts)


PITCH_IVORY_SKIN = PitchIvorySkin()
SKIN_INSTANCE = PITCH_IVORY_SKIN


__all__ = [
    # Palette
    "PITCH_IVORY", "PALETTE",
    # Skin class
    "PitchIvorySkin", "PITCH_IVORY_SKIN", "SKIN_INSTANCE",
    # Canvas
    "CanvasProfile", "HERO_CANVAS", "EMBED_CANVAS", "TX_CANVAS",
    # Tokens
    "HUE", "HUE_ORDER", "TYPE_SCALE", "FONT_SERIF", "FONT_SANS",
    # Chrome
    "svg_defs", "hero_chrome", "hero_footer", "tspan",
]
