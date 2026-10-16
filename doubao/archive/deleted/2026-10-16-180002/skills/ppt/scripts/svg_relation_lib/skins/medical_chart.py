"""
Skin · medical_chart · Clinical / NHS 医疗监护台风

参考: Nature Medicine / NEJM 论文图表 + NHS 临床监护屏 + 急诊分诊单.

视觉核心:
    * bg=#FFFFFF 纯白 · 临床可信度硬要求 (与 whitepaper 冷雾白 #F2F4F8 拉开)
    * ink=#0B1F33 医蓝墨 (比纯黑温暖 · 临床图表招牌)
    * primary=#005EB8 NHS 医疗蓝 (Royal Blue · WHO/NHS 硬色)
    * accent=#00A896 生命体征绿 (vital sign 监护台绿)
    * warn=#C8102E 朱红警戒 (WHO 危重警示色) · 单点用
    * 字体: IBM Plex Sans (临床数据招牌) + Source Serif Pro italic (caption)
    * 装饰母题:
        - 顶端 3px "critical band" 分类识别带 (监护屏病例信息带)
        - chevron ▶ 分诊分级标记
        - Vital sign 脉冲: value + range 并排, out-of-range 加朱红点
        - Rx: 数据字段前缀 (处方单招牌)
    * 圆角 rx=2 微圆 (临床图表常见) · 严格 hairline sw=0.5-0.8

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


HERO_CANVAS = _EA_HERO_CANVAS
EMBED_CANVAS = _EA_EMBED_CANVAS
TX_CANVAS = _EA_TX_CANVAS


# ─────────── Hue table ───────────
# 8 支 hue · 主色系走 NHS 医疗蓝 + 生命绿 + 单点警戒色 (朱红)
# 其它 hue 走中性蓝灰阶 (监护屏冷色系)
HUE = {
    "rust":     "#005EB8",   # NHS 医疗蓝 · 主色
    "orange":   "#00A896",   # 生命体征绿 · vital sign accent
    "magenta":  "#C8102E",   # WHO 朱红 · critical warn (单点)
    "blue":     "#0072CE",   # 亮医疗蓝 · 二级
    "green":    "#3C8D5B",   # normal-range 绿 · 正常值
    "olive":    "#5D7285",   # slate 灰蓝 · 中性文字
    "cinnamon": "#8792A2",   # 冷石灰 · 三级文字
    "gold_p":   "#F0A500",   # 琥珀警示 · caution (次于朱红)
}

HUE_ORDER: Tuple[str, ...] = (
    "rust", "orange", "magenta", "blue", "green", "olive", "cinnamon",
)


# ─────────── Typography ───────────
# IBM Plex Sans: 临床图表招牌 (Nature Medicine 用)
# Source Serif Pro italic: caption / vital sign label (NEJM figure caption 味)
FONT_SANS = "IBM Plex Sans, Inter, Söhne, Helvetica Neue, sans-serif"
FONT_SERIF = "Source Serif Pro, Source Serif 4, IBM Plex Serif, Georgia, serif"

TYPE_SCALE = {
    "title":         (24, FONT_SANS,  600),
    "subtitle":      (12, FONT_SANS,  500),
    "section":       (10, FONT_SANS,  600),
    "column_header": (10, FONT_SANS,  600),
    "hub_name":      (18, FONT_SANS,  700),
    "hub_name_xl":   (24, FONT_SANS,  700),
    "block_title":   (15, FONT_SANS,  600),
    "card_title":    (12, FONT_SANS,  700),
    "chip_kinase":   (13, FONT_SANS,  700),
    "chip_label":    (10, FONT_SANS,  600),
    "body_desc":     (9,  FONT_SANS,  500),
    "micro_numeric": (10, FONT_SANS,  600),
    "footer_read":   (11, FONT_SANS,  500),
    "footer_italic": (10, FONT_SERIF, 500),
    "kicker_mini":   (8,  FONT_SANS,  700),
    "source_tag":    (9,  FONT_SANS,  600),
}


# ═════════════════════════════════════════════════════════════════
# Palette · MEDICAL_CHART
# ═════════════════════════════════════════════════════════════════

MEDICAL_CHART = Palette(
    name="Medical Chart · Clinical / NHS Blue / Vital Green",
    bg="#FFFFFF",                  # 纯白 (临床硬要求)
    bg_alt="#F5F7FA",              # 极淡冷灰 · 分区带
    bg_dim="#E8ECF2",              # 灰
    ink="#0B1F33",                 # 医蓝墨
    gray="rgba(93,114,133,1)",     # slate gray
    hair="#0B1F33",                # opacity 靠属性叠加
    primary=HUE["rust"],           # NHS 医疗蓝
    primary_dim=HUE["blue"],       # 亮医疗蓝
    accent=HUE["orange"],          # 生命体征绿
    accent_dim=HUE["olive"],
    positive=HUE["green"],         # normal 绿
    negative=HUE["magenta"],       # critical 朱红
    head_family=FONT_SANS,
    body_family=FONT_SANS,
    mono_family=FONT_SANS,
    kicker_letter_spacing=2.4,
    kicker_case="upper",
    section_numbering="arabic",
    folio_style="hairline",
    title_style="sans_bold",
    subtitle_style="sans_italic",
    figure_caption_prefix="Fig.",
    signature_note="MEDICAL CHART · CLINICAL / NHS BLUE / VITAL GREEN",
)

PALETTE = MEDICAL_CHART


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
        'stroke="rgba(93,114,133,0.85)" stroke-width="2.6"/></marker>'
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
                palette: Palette = MEDICAL_CHART,
                canvas: CanvasProfile = HERO_CANVAS,
                include_bg: bool = True) -> str:
    is_embed = (canvas.w == 900 and canvas.h == 336)
    title_sz = 17 if is_embed else 24
    subtitle_sz = 10 if is_embed else 12
    section_sz = 8 if is_embed else 10
    kicker_sz = 8 if is_embed else 10
    parts: List[str] = []
    if include_bg:
        parts.append(_rect(0, 0, canvas.w, canvas.h, fill=palette.bg))
    if kicker:
        parts.append(_txt(canvas.margin_x, canvas.title_y - 20, kicker,
                          size=kicker_sz, family=FONT_SANS, weight=700,
                          fill=palette.primary, letter_em=0.20))
    if title:
        parts.append(_txt(canvas.margin_x, canvas.title_y, title,
                          size=title_sz, family=FONT_SANS, weight=600,
                          fill=palette.ink, letter_em=0.005))
    if subtitle:
        parts.append(_txt(canvas.margin_x, canvas.subtitle_y, subtitle,
                          size=subtitle_sz, family=FONT_SANS, weight=500,
                          fill=palette.gray, letter_em=0.03))
    # title hairline · NHS 医疗蓝 (临床图表招牌: 顶栏色带)
    parts.append(_line(canvas.margin_x, canvas.title_hair_y,
                       canvas.w - canvas.margin_x, canvas.title_hair_y,
                       stroke=palette.primary, sw=1.2, opacity=0.85))
    if column_headers:
        for lbl, cx in column_headers:
            parts.append(_txt(cx, canvas.section_hdr_y, lbl,
                              size=section_sz, family=FONT_SANS, weight=700,
                              fill=palette.primary,
                              anchor="middle", letter_em=0.22))
    if encoding_note_right:
        note_sz = 9 if is_embed else 10
        parts.append(_txt(canvas.w - canvas.margin_x, canvas.subtitle_y,
                          encoding_note_right,
                          size=note_sz, family=FONT_SERIF, weight=500,
                          fill=palette.gray, anchor="end", italic=True))
    return "".join(parts)


def hero_footer(*, caption: str = "",
                source: str = "",
                read_lines: Optional[Sequence[str]] = None,
                italic_last: bool = False,
                palette: Palette = MEDICAL_CHART,
                canvas: CanvasProfile = HERO_CANVAS,
                min_read_chars: int = 40) -> str:
    _ = (caption, source, read_lines, italic_last, palette, canvas, min_read_chars)
    return ""


def tspan(word: str, *, color: str = HUE["rust"], weight: int = 700) -> str:
    """READ 段内高亮 · 默认 NHS 医疗蓝."""
    c = _resolve_hue(color) if not color.startswith("rgba") else color
    return (f'<tspan font-weight="{weight}" fill="{c}">'
            f'{esc(word)}</tspan>')


# ═════════════════════════════════════════════════════════════════
# Skin 契约 · draw_node · 临床监护台招牌
# 3 kind: category_card / kpi_card / problem_statement
# ═════════════════════════════════════════════════════════════════

class MedicalChartSkin:
    """Medical Chart · 临床监护台 / NEJM figure · NHS 蓝 + vital 绿 + 朱红警戒."""

    name = "medical_chart"

    def draw_node(self, x: float, y: float, w: float, h: float,
                  label: str, palette: Palette,
                  kind: str = "", **kwargs) -> Optional[str]:
        pal = palette or MEDICAL_CHART
        if kind == "category_card":
            return self._category_card(x, y, w, h, label, pal, **kwargs)
        if kind == "kpi_card":
            return self._kpi_card(x, y, w, h, label, pal, **kwargs)
        if kind == "problem_statement":
            return self._problem_statement(x, y, w, h, pal, label=label, **kwargs)
        # ── OSI 3 kind (opt-in · j1_osi preset 用) ──
        if kind == "osi_layer_bar":
            return self._osi_layer_bar(x, y, w, h, pal, **kwargs)
        if kind == "osi_layer_num":
            return self._osi_layer_num(x, y, label, pal, **kwargs)
        if kind == "osi_pdu_pill":
            return self._osi_pdu_pill(x, y, w, h, pal, **kwargs)
        return None

    # ─────────── category_card · 顶端 critical band + Rx 前缀 ───────────
    def _category_card(self, x, y, w, h, label, pal, **kw) -> str:
        hue = kw.get("hue", "rust")
        hue_c = _resolve_hue(hue)
        nhs = _resolve_hue("rust")           # NHS 医疗蓝
        vital = _resolve_hue("orange")       # 生命绿
        subtitle = kw.get("subtitle", "")
        pct = kw.get("pct", "")
        parts: List[str] = []
        # 纯白底 · rx=2 微圆角 · slate 严格 hairline
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w}" height="{h}" '
            f'rx="2" fill="{pal.bg}" stroke="{pal.hair}" stroke-width="0.5" '
            f'opacity="0.95"/>'
        )
        # 顶端 3px critical band (hue color 分类识别 · 监护屏招牌)
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w}" height="3" '
            f'fill="{hue_c}"/>'
        )
        # 左侧 Dx: 前缀 (临床处方单招牌 · IBM Plex mono-ish)
        parts.append(
            f'<text x="{x + 8:.1f}" y="{y + 19:.1f}" '
            f'font-family="{FONT_SANS}" font-size="8" font-weight="700" '
            f'fill="{nhs}" letter-spacing="0.14em">Dx</text>'
        )
        # label · IBM Plex bold ink · Rx 后跟主症
        parts.append(
            f'<text x="{x + 28:.1f}" y="{y + 19:.1f}" '
            f'font-family="{FONT_SANS}" font-size="12" font-weight="700" '
            f'fill="{pal.ink}" letter-spacing="0em">'
            f'{esc(label)}</text>'
        )
        if subtitle:
            # subtitle · Source Serif italic gray (NEJM figure caption 味)
            parts.append(
                f'<text x="{x + 28:.1f}" y="{y + 32:.1f}" '
                f'font-family="{FONT_SERIF}" font-size="9" font-weight="400" '
                f'font-style="italic" fill="{pal.gray}" letter-spacing="0.02em">'
                f'{esc(subtitle)}</text>'
            )
        # pct · vital sign 绿 · IBM Plex bold (contribution 归因权重)
        if pct:
            parts.append(
                f'<text x="{x + w - 8:.1f}" y="{y + 19:.1f}" '
                f'text-anchor="end" font-family="{FONT_SANS}" '
                f'font-size="13" font-weight="700" fill="{vital}" '
                f'letter-spacing="-0.005em">'
                f'{esc(pct)}</text>'
            )
        return "".join(parts)

    # ─────────── kpi_card · vital sign 监护台 · value + range 并排 ───────────
    def _kpi_card(self, x, y, w, h, label, pal, **kw) -> str:
        nhs = _resolve_hue("rust")
        vital = _resolve_hue("orange")
        value = kw.get("value", "")
        note = kw.get("note", "")
        parts: List[str] = []
        # 底部 vital sign 波形基线 (监护屏招牌: 波浪线做背景装饰)
        # 简化: 单细横线 + 端点 vital 绿圆点
        parts.append(
            f'<line x1="{x:.1f}" y1="{y + h:.1f}" '
            f'x2="{x + w:.1f}" y2="{y + h:.1f}" '
            f'stroke="{pal.hair}" stroke-width="0.5" opacity="0.35"/>'
        )
        # 左侧 vital sign 端点圆 · 生命绿 (监护台"reading OK"味)
        parts.append(
            f'<circle cx="{x + 3:.1f}" cy="{y + h:.1f}" r="2" fill="{vital}"/>'
        )
        # kicker · slate gray uppercase spaced (临床数据字段名)
        if label:
            parts.append(
                f'<text x="{x + 10:.1f}" y="{y + 12:.1f}" '
                f'font-family="{FONT_SANS}" font-size="8" font-weight="700" '
                f'fill="{pal.gray}" letter-spacing="0.16em">'
                f'{esc(label.upper())}</text>'
            )
        # value · IBM Plex bold NHS 蓝 · tabular-num 感
        if value:
            parts.append(
                f'<text x="{x + 10:.1f}" y="{y + 30:.1f}" '
                f'font-family="{FONT_SANS}" font-size="16" font-weight="700" '
                f'fill="{nhs}" letter-spacing="-0.01em">'
                f'{esc(value)}</text>'
            )
        # note · Source Serif italic gray 右侧 (measurement range · NEJM 味)
        if note:
            parts.append(
                f'<text x="{x + w - 4:.1f}" y="{y + 30:.1f}" '
                f'text-anchor="end" font-family="{FONT_SERIF}" font-size="9" '
                f'font-style="italic" fill="{pal.gray}">'
                f'{esc(note)}</text>'
            )
        return "".join(parts)

    # ─────────── problem_statement · 急诊分诊单 · chevron ▶ + urgency ───────────
    def _problem_statement(self, x, y, w, h, pal, **kw) -> str:
        nhs = _resolve_hue("rust")
        warn = _resolve_hue("magenta")       # 朱红 critical
        vital = _resolve_hue("orange")
        kicker = kw.get("kicker", "CLINICAL FINDING")
        label = kw.get("label", "")
        stat = kw.get("stat", "")
        range_txt = kw.get("range", "")
        parts: List[str] = []
        cx = x + w / 2
        # 纯白 · rx=2 · NHS 蓝 hairline
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w}" height="{h}" '
            f'rx="2" fill="{pal.bg}" stroke="{nhs}" stroke-width="1.2"/>'
        )
        # 顶端 4px NHS 蓝色带 (临床图表 header)
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w}" height="4" '
            f'fill="{nhs}"/>'
        )
        # chevron ▶ · warn 朱红 (急诊分诊单招牌)
        parts.append(
            f'<path d="M {x + 12:.1f} {y + 20:.1f} '
            f'L {x + 22:.1f} {y + 26:.1f} '
            f'L {x + 12:.1f} {y + 32:.1f} Z" '
            f'fill="{warn}"/>'
        )
        # kicker · NHS 蓝 uppercase spaced (chevron 后 · header 定位)
        parts.append(
            f'<text x="{x + 30:.1f}" y="{y + 30:.1f}" '
            f'font-family="{FONT_SANS}" font-size="9" font-weight="700" '
            f'fill="{nhs}" letter-spacing="0.22em">'
            f'{esc(kicker)}</text>'
        )
        # divider · slate 极细
        parts.append(
            f'<line x1="{x + 12:.1f}" y1="{y + 42:.1f}" '
            f'x2="{x + w - 12:.1f}" y2="{y + 42:.1f}" '
            f'stroke="{pal.hair}" stroke-width="0.5" opacity="0.4"/>'
        )
        # label · IBM Plex medium ink (chief complaint 主症)
        if label:
            parts.append(
                f'<text x="{cx:.1f}" y="{y + 62:.1f}" text-anchor="middle" '
                f'font-family="{FONT_SANS}" font-size="14" '
                f'font-weight="600" fill="{pal.ink}">'
                f'{esc(label)}</text>'
            )
        if stat:
            # 大 stat · 朱红警戒色 (out-of-range value)
            parts.append(
                f'<text x="{cx:.1f}" y="{y + 106:.1f}" text-anchor="middle" '
                f'font-family="{FONT_SANS}" font-size="36" font-weight="700" '
                f'fill="{warn}" letter-spacing="-0.02em">'
                f'{esc(stat)}</text>'
            )
            # 朱红端点圆 · 强化 "out of range" 视觉 (监护屏警报圆点)
            parts.append(
                f'<circle cx="{cx + 5:.1f}" cy="{y + 78:.1f}" r="3" '
                f'fill="{warn}" opacity="0.9"/>'
            )
        if range_txt:
            # range · Source Serif italic gray (reference range · NEJM caption 味)
            parts.append(
                f'<line x1="{cx - 44:.1f}" y1="{y + h - 32:.1f}" '
                f'x2="{cx + 44:.1f}" y2="{y + h - 32:.1f}" '
                f'stroke="{vital}" stroke-width="0.6" opacity="0.6"/>'
            )
            parts.append(
                f'<text x="{cx:.1f}" y="{y + h - 16:.1f}" text-anchor="middle" '
                f'font-family="{FONT_SERIF}" font-size="10" font-style="italic" '
                f'fill="{pal.gray}" letter-spacing="0.03em">'
                f'ref. {esc(range_txt)}</text>'
            )
        return "".join(parts)

    # ═══════════════════════════════════════════════════════════
    # OSI kind · 纯白 + NHS 蓝 + vital 绿 · 监护台味
    # ═══════════════════════════════════════════════════════════

    def _osi_layer_bar(self, x, y, w, h, pal, **kw) -> str:
        """medical · 纯白 + NHS 蓝 hairline + 左侧 vital 绿 3px 竖条 (监护台)."""
        nhs = _resolve_hue("rust")
        vital = _resolve_hue("orange")
        parts: List[str] = [
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w}" height="{h}" '
            f'rx="2" fill="{pal.bg}" stroke="{nhs}" stroke-width="0.6" '
            f'opacity="0.95"/>',
            f'<rect x="{x:.1f}" y="{y:.1f}" width="3" height="{h}" '
            f'fill="{vital}"/>',
        ]
        return "".join(parts)

    def _osi_layer_num(self, x, y, text, pal, **kw) -> str:
        """medical · IBM Plex Sans bold NHS 蓝 · tabular-num."""
        nhs = _resolve_hue("rust")
        return (f'<text x="{x}" y="{y:.1f}" font-family="{FONT_SANS}" '
                f'font-size="18" font-weight="700" fill="{nhs}" '
                f'letter-spacing="-0.01em">{esc(text)}</text>')

    def _osi_pdu_pill(self, x, y, w, h, pal, **kw) -> str:
        """medical · rx=8 圆润 pill · vital 绿边框 + NHS 蓝浅底 (监护台 chip)."""
        nhs = _resolve_hue("rust")
        vital = _resolve_hue("orange")
        parts: List[str] = [
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h}" '
            f'rx="8" fill="{pal.bg}" stroke="{vital}" stroke-width="0.9"/>',
            f'<circle cx="{x + 4:.1f}" cy="{y + h/2:.1f}" r="1.8" '
            f'fill="{vital}"/>',
        ]
        return "".join(parts)


MEDICAL_CHART_SKIN = MedicalChartSkin()
SKIN_INSTANCE = MEDICAL_CHART_SKIN


__all__ = [
    # Palette
    "MEDICAL_CHART", "PALETTE",
    # Skin class
    "MedicalChartSkin", "MEDICAL_CHART_SKIN", "SKIN_INSTANCE",
    # Canvas
    "CanvasProfile", "HERO_CANVAS", "EMBED_CANVAS", "TX_CANVAS",
    # Tokens
    "HUE", "HUE_ORDER", "TYPE_SCALE", "FONT_SERIF", "FONT_SANS",
    # Chrome
    "svg_defs", "hero_chrome", "hero_footer", "tspan",
]
