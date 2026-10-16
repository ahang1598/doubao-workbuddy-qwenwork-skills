"""
Skin · luxury_manual · Ivory / Deep-Green / Muted-Gold 高端品牌手册

参照 dcg_style_experiments/HANDBOOK.md §8 design-proposal token 建立：

视觉核心：
    * bg=#F5F0E8 米白 · ink=#1F2E23 深墨绿 · accent=#C4A96B 哑金
    * Playfair Display italic + 思源宋体 · 材料色而非屏幕色
    * 装饰母题：四角小方块 ◼ · 深墨绿承载块 · 罗马数字章节 · `FIG.` 图注
    * 深墨绿承载色块为可选装饰母题 (深浅底交替) · 本轮 hero viewport bg 仍是米白
    * 首版复用 editorial_atelier 的 chrome / defs 函数几何 · 只改配色/字体/图注前缀

被期望 node.kind：（同 editorial_atelier · skin 契约以后再各自实现）
被期望 edge.kind：（同 editorial_atelier）

canvas 契约（skin 不假设 · preset 传坐标）：
    HERO_CANVAS  = 1400 × 820
    EMBED_CANVAS = 900  × 336
"""
from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

from ..engine import esc
from ..palettes import Palette
# 复用 editorial_atelier 的几何 helper（_txt / _rect / _line / _tint / _resolve_hue
# 目前是模块级函数 · 底层几何不含配色 · 我们只需要在本 skin 内 rebind 配色即可）
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
# Canvas · 与 editorial_atelier 完全复用同一份 CanvasProfile 尺寸
# ═════════════════════════════════════════════════════════════════

HERO_CANVAS = _EA_HERO_CANVAS
EMBED_CANVAS = _EA_EMBED_CANVAS
TX_CANVAS = _EA_TX_CANVAS


# ─────────── Hue table ───────────
# 8 支 hue · rust slot 重新映射到深墨绿 · 保持 key 名不变 (preset 依赖 key)
# 副 hue 保留奢侈手册调性：材料色、深沉、克制
HUE = {
    "rust":     "#1F2E23",   # 主色 · 深墨绿（原 rust 位）
    "orange":   "#C4A96B",   # 哑金 accent · 二级 (原 warm orange)
    "magenta":  "#8B4A5E",   # 深酒红 warn · 负 delta
    "blue":     "#3E5062",   # 深钢蓝
    "green":    "#2E4A38",   # deep forest · 正 delta
    "olive":    "#6E6656",   # 深暖灰
    "cinnamon": "#A69C8B",   # 中暖灰
    "gold_p":   "#C4A96B",   # 哑金 · accent
}

HUE_ORDER: Tuple[str, ...] = (
    "rust", "orange", "magenta", "blue", "green", "olive", "cinnamon",
)


# ─────────── Typography ───────────
# 用 Playfair Display italic 作为 serif 通道（HANDBOOK §8 硬要求）
# sans 通道保留 Inter 用于极小注脚 / column header letter-spacing
FONT_SANS = "Inter, Söhne, Helvetica Neue, sans-serif"
FONT_SERIF = "Playfair Display, Source Han Serif, GT Sectra, Georgia, serif"

TYPE_SCALE = {
    "title":         (26, FONT_SERIF, 700),
    "subtitle":      (13, FONT_SERIF, 500),
    "section":       (10, FONT_SANS,  700),
    "column_header": (10, FONT_SANS,  700),
    "hub_name":      (19, FONT_SERIF, 800),
    "hub_name_xl":   (26, FONT_SERIF, 800),
    "block_title":   (17, FONT_SERIF, 700),
    "card_title":    (13, FONT_SERIF, 800),
    "chip_kinase":   (14, FONT_SERIF, 800),
    "chip_label":    (11, FONT_SANS,  700),
    "body_desc":     (10, FONT_SANS,  500),
    "micro_numeric": (10, FONT_SANS,  700),
    "footer_read":   (12, FONT_SERIF, 500),
    "footer_italic": (11, FONT_SERIF, 500),
    "kicker_mini":   (9,  FONT_SANS,  700),
    "source_tag":    (10, FONT_SANS,  700),
}


# ═════════════════════════════════════════════════════════════════
# Palette · LUXURY_MANUAL
# ═════════════════════════════════════════════════════════════════

LUXURY_MANUAL = Palette(
    name="Luxury Manual · Ivory / Deep-Green / Muted-Gold",
    bg="#F5F0E8",
    bg_alt="#EDE6D6",
    bg_dim="#DFD5BE",
    ink="#1F2E23",
    gray="rgba(31,46,35,0.60)",
    hair="#1F2E23",                # opacity 靠属性叠加
    primary=HUE["rust"],           # 深墨绿
    primary_dim=HUE["olive"],      # 深暖灰
    accent=HUE["gold_p"],          # 哑金
    accent_dim=HUE["cinnamon"],
    positive=HUE["green"],
    negative=HUE["magenta"],
    head_family=FONT_SERIF,
    body_family=FONT_SANS,
    mono_family=FONT_SANS,
    kicker_letter_spacing=3.5,
    kicker_case="upper",
    section_numbering="roman",
    folio_style="hairline",
    title_style="serif_italic",
    subtitle_style="serif_italic",
    figure_caption_prefix="FIG.",
    signature_note="LUXURY MANUAL · IVORY / DEEP-GREEN / MUTED-GOLD",
)

# preset 约定名 · 每个 skin 必须导出 PALETTE 单例
PALETTE = LUXURY_MANUAL


# ═════════════════════════════════════════════════════════════════
# Filter / gradient / marker (id prefix 用 ea- 统一 · 与 boardroom 复用)
# ═════════════════════════════════════════════════════════════════

_FILTER_DEFS = """<filter id="ea-soft-shadow" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur in="SourceAlpha" stdDeviation="2"/><feOffset dx="0" dy="1.5"/><feComponentTransfer><feFuncA type="linear" slope="0.22"/></feComponentTransfer><feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge></filter><filter id="ea-hub-shadow" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur in="SourceAlpha" stdDeviation="3.5"/><feOffset dx="0" dy="2.5"/><feComponentTransfer><feFuncA type="linear" slope="0.28"/></feComponentTransfer><feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge></filter><filter id="ea-hub-halo" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur in="SourceGraphic" stdDeviation="5.5"/></filter>"""


def _gradient_defs(hues: Sequence[str]) -> str:
    """给定 hue key list · 生成对应的 linearGradient stops (0.75 → 0.35)。"""
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
    """给定 hue key list · 每支 hue 生成 arrow marker · 另加 tbar-gray。"""
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
        'stroke="rgba(31,46,35,0.85)" stroke-width="2.6"/></marker>'
    )
    return "".join(out)


def _resolve_hue(hue_key_or_hex: str) -> str:
    """接受 'rust' / 'orange' 或直接 hex · 返回 hex 字符串。"""
    if not hue_key_or_hex:
        return HUE["rust"]
    if hue_key_or_hex.startswith("#"):
        return hue_key_or_hex
    return HUE.get(hue_key_or_hex, HUE["rust"])


# ═════════════════════════════════════════════════════════════════
# svg_defs · hero_chrome · hero_footer · tspan
# 首版复用 editorial_atelier 的几何 · 只替换配色 (深墨绿 / 哑金 / 米白)
# ═════════════════════════════════════════════════════════════════

def svg_defs(hues: Sequence[str] = HUE_ORDER,
             include_markers: bool = True,
             include_gradients: bool = True) -> str:
    """一次注入 3 filter + hue gradient + hue marker · <defs> 段。

    preset 在渲染前置调用 · 生成的字符串直接拼进 SVG 头。
    id 前缀 `ea-` 与 editorial_atelier / boardroom_navy 复用 · 可同页共存。
    """
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
                palette: Palette = LUXURY_MANUAL,
                canvas: CanvasProfile = HERO_CANVAS,
                include_bg: bool = True) -> str:
    """顶部 chrome (title + subtitle + hair + column headers)。

    canvas=EMBED 时字号缩到 embed 尺度 (title 17 · subtitle 10 · section 8)。
    与 editorial_atelier.hero_chrome 几何一致 · 颜色/字体改用 luxury_manual 手册调性。
    title/subtitle 走 Playfair Display italic serif · kicker/column header 走 sans letter-spacing 3.5。
    """
    is_embed = (canvas.w == 900 and canvas.h == 336)
    title_sz = 17 if is_embed else 26
    subtitle_sz = 10 if is_embed else 13
    section_sz = 8 if is_embed else 10
    kicker_sz = 8 if is_embed else 10
    parts: List[str] = []
    # 背景 · 米白
    if include_bg:
        parts.append(_rect(0, 0, canvas.w, canvas.h, fill=palette.bg))
    # kicker (小字上方) · sans + 大字距 (luxury 感)
    if kicker:
        parts.append(_txt(canvas.margin_x, canvas.title_y - 20, kicker,
                          size=kicker_sz, family=FONT_SANS, weight=700,
                          fill=palette.accent, letter_em=0.35))
    # title · Playfair Display italic serif
    if title:
        parts.append(_txt(canvas.margin_x, canvas.title_y, title,
                          size=title_sz, family=FONT_SERIF, weight=700,
                          fill=palette.ink, letter_em=0.01, italic=True))
    # subtitle · Playfair Display italic serif
    if subtitle:
        parts.append(_txt(canvas.margin_x, canvas.subtitle_y, subtitle,
                          size=subtitle_sz, family=FONT_SERIF, weight=500,
                          fill=palette.gray, letter_em=0.02, italic=True))
    # title hairline · 深墨绿
    parts.append(_line(canvas.margin_x, canvas.title_hair_y,
                       canvas.w - canvas.margin_x, canvas.title_hair_y,
                       stroke=palette.hair, sw=0.6, opacity=0.28))
    # column headers · fill 用 accent (哑金) tint · 大字距 luxury letter-spacing
    if column_headers:
        for lbl, cx in column_headers:
            parts.append(_txt(cx, canvas.section_hdr_y, lbl,
                              size=section_sz, family=FONT_SANS, weight=700,
                              fill=_tint(HUE["gold_p"], 0.95),
                              anchor="middle", letter_em=0.35))
    # 顶右侧 encoding · Playfair italic
    if encoding_note_right:
        note_sz = 9 if is_embed else 11
        parts.append(_txt(canvas.w - canvas.margin_x, canvas.subtitle_y,
                          encoding_note_right,
                          size=note_sz, family=FONT_SERIF, weight=500,
                          fill=palette.gray, anchor="end", italic=True))
    return "".join(parts)


def hero_footer(*, caption: str = "",
                source: str = "",
                read_lines: Optional[Sequence[str]] = None,
                italic_last: bool = False,
                palette: Palette = LUXURY_MANUAL,
                canvas: CanvasProfile = HERO_CANVAS,
                min_read_chars: int = 40) -> str:
    """底部 chrome — 已按用户指令关闭渲染 · 与 editorial_atelier / boardroom_navy 保持一致 (return "")。

    参数保留 · 签名不变 · preset 调用方无需改动。
    """
    _ = (caption, source, read_lines, italic_last, palette, canvas, min_read_chars)
    return ""


def tspan(word: str, *, color: str = HUE["gold_p"], weight: int = 700) -> str:
    """READ 段内高亮 · fill 用 hue key 或 hex。

    默认色改为哑金（luxury_manual 里高亮惯例）· 与 boardroom 的铜金对应。
    """
    c = _resolve_hue(color) if not color.startswith("rgba") else color
    return (f'<tspan font-weight="{weight}" fill="{c}">'
            f'{esc(word)}</tspan>')


# ═════════════════════════════════════════════════════════════════
# Skin 契约 · draw_node · opt-in 分流
# 视觉核心: 象牙底 + 深墨绿 + 烫金 · 极简双 hairline · Playfair italic
# 3 kind: category_card / kpi_card / problem_statement
# ═════════════════════════════════════════════════════════════════

class LuxuryManualSkin:
    """Luxury Manual · 奢华手册 · 烫金细边框 + Playfair italic + 深墨绿."""

    name = "luxury_manual"

    def draw_node(self, x: float, y: float, w: float, h: float,
                  label: str, palette: Palette,
                  kind: str = "", **kwargs) -> Optional[str]:
        pal = palette or LUXURY_MANUAL
        if kind == "category_card":
            return self._category_card(x, y, w, h, label, pal, **kwargs)
        if kind == "kpi_card":
            return self._kpi_card(x, y, w, h, label, pal, **kwargs)
        if kind == "problem_statement":
            return self._problem_statement(x, y, w, h, pal, label=label, **kwargs)
        return None

    # ─────────── category_card · 烫金双 hairline · Playfair italic ───────────
    def _category_card(self, x, y, w, h, label, pal, **kw) -> str:
        forest = _resolve_hue("rust")        # 深墨绿
        gold = _resolve_hue("gold_p")        # 哑金
        subtitle = kw.get("subtitle", "")
        pct = kw.get("pct", "")
        parts: List[str] = []
        # 象牙底 · rx=0 直角 · 深墨绿 hairline
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w}" height="{h}" '
            f'fill="{pal.bg}" stroke="{forest}" stroke-width="0.6"/>'
        )
        # 烫金内嵌 hairline
        parts.append(
            f'<rect x="{x + 3:.1f}" y="{y + 3:.1f}" '
            f'width="{w - 6}" height="{h - 6}" '
            f'fill="none" stroke="{gold}" stroke-width="0.4" opacity="0.75"/>'
        )
        # label · Playfair italic 深墨绿
        parts.append(
            f'<text x="{x + 10:.1f}" y="{y + 17:.1f}" '
            f'font-family="{FONT_SERIF}" font-size="12" font-weight="700" '
            f'font-style="italic" fill="{forest}">'
            f'{esc(label)}</text>'
        )
        if subtitle:
            parts.append(
                f'<text x="{x + 10:.1f}" y="{y + 30:.1f}" '
                f'font-family="{FONT_SANS}" font-size="8" font-weight="500" '
                f'fill="{pal.gray}" letter-spacing="0.16em">'
                f'{esc(subtitle.upper())}</text>'
            )
        if pct:
            parts.append(
                f'<text x="{x + w - 10:.1f}" y="{y + 17:.1f}" '
                f'text-anchor="end" font-family="{FONT_SERIF}" '
                f'font-size="13" font-weight="700" font-style="italic" '
                f'fill="{gold}">{esc(pct)}</text>'
            )
        return "".join(parts)

    # ─────────── kpi_card · 烫金/深绿双 hairline ───────────
    def _kpi_card(self, x, y, w, h, label, pal, **kw) -> str:
        forest = _resolve_hue("rust")
        gold = _resolve_hue("gold_p")
        value = kw.get("value", "")
        note = kw.get("note", "")
        parts: List[str] = []
        parts.append(
            f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x + w:.1f}" y2="{y:.1f}" '
            f'stroke="{gold}" stroke-width="0.6"/>'
        )
        parts.append(
            f'<line x1="{x:.1f}" y1="{y + h:.1f}" '
            f'x2="{x + w:.1f}" y2="{y + h:.1f}" '
            f'stroke="{forest}" stroke-width="0.5" opacity="0.6"/>'
        )
        if label:
            parts.append(
                f'<text x="{x + 4:.1f}" y="{y + 12:.1f}" '
                f'font-family="{FONT_SERIF}" font-size="8.5" font-weight="500" '
                f'font-style="italic" fill="{forest}" letter-spacing="0.20em">'
                f'{esc(label.upper())}</text>'
            )
        if value:
            parts.append(
                f'<text x="{x + 4:.1f}" y="{y + 30:.1f}" '
                f'font-family="{FONT_SERIF}" font-size="17" font-weight="700" '
                f'font-style="italic" fill="{forest}">'
                f'{esc(value)}</text>'
            )
        if note:
            parts.append(
                f'<text x="{x + w - 4:.1f}" y="{y + 30:.1f}" '
                f'text-anchor="end" font-family="{FONT_SERIF}" font-size="9" '
                f'font-style="italic" fill="{pal.gray}">'
                f'{esc(note)}</text>'
            )
        return "".join(parts)

    # ─────────── problem_statement · 深墨绿 hero + 烫金 stat ───────────
    def _problem_statement(self, x, y, w, h, pal, **kw) -> str:
        forest = _resolve_hue("rust")
        gold = _resolve_hue("gold_p")
        kicker = kw.get("kicker", "PROLOGUE")
        label = kw.get("label", "")
        stat = kw.get("stat", "")
        range_txt = kw.get("range", "")
        parts: List[str] = []
        cx = x + w / 2
        # 深墨绿 hero 底 · rx=0 (奢华反白)
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w}" height="{h}" '
            f'fill="{forest}"/>'
        )
        parts.append(
            f'<rect x="{x + 5:.1f}" y="{y + 5:.1f}" '
            f'width="{w - 10}" height="{h - 10}" '
            f'fill="none" stroke="{gold}" stroke-width="0.6" opacity="0.75"/>'
        )
        # kicker · 烫金 uppercase 大字距
        parts.append(
            f'<text x="{cx:.1f}" y="{y + 28:.1f}" text-anchor="middle" '
            f'font-family="{FONT_SANS}" font-size="9" font-weight="600" '
            f'fill="{gold}" letter-spacing="0.32em">'
            f'{esc(kicker)}</text>'
        )
        parts.append(
            f'<line x1="{cx - 24:.1f}" y1="{y + 38:.1f}" '
            f'x2="{cx + 24:.1f}" y2="{y + 38:.1f}" '
            f'stroke="{gold}" stroke-width="0.5"/>'
        )
        if label:
            parts.append(
                f'<text x="{cx:.1f}" y="{y + 60:.1f}" text-anchor="middle" '
                f'font-family="{FONT_SERIF}" font-size="14" font-style="italic" '
                f'font-weight="500" fill="{pal.bg}">'
                f'{esc(label)}</text>'
            )
        if stat:
            parts.append(
                f'<text x="{cx:.1f}" y="{y + 108:.1f}" text-anchor="middle" '
                f'font-family="{FONT_SERIF}" font-size="42" font-weight="700" '
                f'font-style="italic" fill="{gold}" letter-spacing="-0.01em">'
                f'{esc(stat)}</text>'
            )
        if range_txt:
            parts.append(
                f'<text x="{cx:.1f}" y="{y + h - 20:.1f}" text-anchor="middle" '
                f'font-family="{FONT_SERIF}" font-size="10" font-style="italic" '
                f'fill="{pal.bg}" opacity="0.7" letter-spacing="0.06em">'
                f'{esc(range_txt)}</text>'
            )
        return "".join(parts)


LUXURY_MANUAL_SKIN = LuxuryManualSkin()
SKIN_INSTANCE = LUXURY_MANUAL_SKIN


__all__ = [
    # Palette
    "LUXURY_MANUAL", "PALETTE",
    # Skin class
    "LuxuryManualSkin", "LUXURY_MANUAL_SKIN", "SKIN_INSTANCE",
    # Canvas
    "CanvasProfile", "HERO_CANVAS", "EMBED_CANVAS", "TX_CANVAS",
    # Tokens
    "HUE", "HUE_ORDER", "TYPE_SCALE", "FONT_SERIF", "FONT_SANS",
    # Chrome
    "svg_defs", "hero_chrome", "hero_footer", "tspan",
]
