"""
ib_editorial skin · Information-Is-Beautiful pastel editorial

按 brca1_iib.png（Information Is Beautiful 手册风）逆向抽出：
    * bg cream #F0EBE0 温和 paper
    * 6 pastel hue: salmon / sage / peach / rose / dust_blue / lilac
    * ink deep #1A1A18
    * Georgia serif · italic-friendly · 大量小 caps kicker
    * numeral kicker "01 · 02 · 03 ..." · 巨号 KPI · dot row · patient story

Layout 语言（reference brca1_iib.png · 1400 × 820）：
    top    · 大 serif italic title + 小 subtitle + 分栏 kicker note
    middle · 8 pastel KPI card grid (kicker + big num + note + dot row)
    bottom · hub + 4 branch story card (with complement/right sublabel)
    foot   · italic 结论 + 灰色 credits

primitives（module-level · preset 直接 import）：
    svg_defs_iib        · <defs> filter 注入
    numeral_kicker      · "01 · WHAT IT IS" 编号标 kicker
    dot_row             · N 圆点 grid（heredity 5/8 之类）
    pastel_kpi_card     · 顶部大数字 KPI 卡
    hub_pastel          · 有 kicker 底 THE HUB · N complexes
    patient_story_card  · 底部叙事卡 (title/tagline/right complement)
    iib_chrome          · 大 serif italic title + subtitle
    iib_footer          · italic 结论 + credits

canvas：
    HERO_CANVAS  = 1400 × 820  (reference)
    EMBED_CANVAS = 900  × 336  (legacy embed)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from ..engine import esc
from ..palettes import Palette
from ._base import _label_clip


# ═════════════════════════════════════════════════════════════════
# Canvas profile
# ═════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class CanvasProfile:
    w: int
    h: int
    margin_x: int
    title_y: int
    subtitle_y: int
    title_hair_y: int
    body_y0: int
    body_y1: int
    bottom_hair_y: int
    footer_line_y: int
    credits_y: int


HERO_CANVAS = CanvasProfile(
    w=1400, h=820, margin_x=60,
    title_y=52, subtitle_y=78, title_hair_y=100,
    body_y0=118, body_y1=720,
    bottom_hair_y=736, footer_line_y=762,
    credits_y=800,
)

EMBED_CANVAS = CanvasProfile(
    w=900, h=336, margin_x=22,
    title_y=26, subtitle_y=46, title_hair_y=62,
    body_y0=76, body_y1=280,
    bottom_hair_y=290, footer_line_y=306,
    credits_y=328,
)


# ═════════════════════════════════════════════════════════════════
# Pastel hue table (RGB sum > 500 · 6 支)
# ═════════════════════════════════════════════════════════════════

HUE = {
    "salmon":    "#EEB598",   # 温暖 salmon pink
    "sage":      "#B5C9A5",   # 苔绿
    "peach":     "#F0C88F",   # 桃奶油
    "rose":      "#EEA7A7",   # 玫瑰粉
    "dust_blue": "#A5B9C9",   # 灰蓝
    "lilac":     "#C9B5D6",   # 淡紫
}

HUE_ORDER: Tuple[str, ...] = (
    "salmon", "sage", "peach", "rose", "dust_blue", "lilac",
)


# ═════════════════════════════════════════════════════════════════
# Typography
# ═════════════════════════════════════════════════════════════════

FONT_SERIF = "Georgia, 'Iowan Old Style', 'Palatino Linotype', serif"
FONT_SANS = "'Inter', 'Helvetica Neue', Arial, sans-serif"

TYPE_SCALE = {
    "title":         (32, FONT_SERIF, 700),    # hero title · italic友好
    "subtitle":      (12, FONT_SANS,  500),
    "kicker_top":    (9,  FONT_SANS,  700),    # 顶部 "one gene · three winners"
    "kpi_num":       (36, FONT_SERIF, 700),    # BRCA1 / $8.2B 巨号
    "kpi_num_xl":    (44, FONT_SERIF, 800),
    "kpi_unit":      (10, FONT_SANS,  600),    # tumor suppressor / 5/8
    "kpi_note":      (9.5, FONT_SANS, 500),
    "kicker_num":    (10, FONT_SANS,  700),    # "01 · WHAT IT IS"
    "story_title":   (14, FONT_SANS,  800),
    "story_tag":     (10, FONT_SANS,  500),
    "story_right":   (9.5, FONT_SANS, 600),
    "hub_name":      (26, FONT_SERIF, 800),
    "hub_kicker":    (9,  FONT_SANS,  700),
    "hub_tag":       (10, FONT_SANS,  500),
    "footer_conclusion": (13, FONT_SERIF, 500),   # italic
    "credits":       (8.5, FONT_SANS, 500),
}


# ═════════════════════════════════════════════════════════════════
# Filter defs · iib-soft-shadow
# ═════════════════════════════════════════════════════════════════

_FILTER_DEFS = (
    '<filter id="iib-soft-shadow" x="-15%" y="-15%" width="130%" height="130%">'
    '<feGaussianBlur in="SourceAlpha" stdDeviation="1.6"/>'
    '<feOffset dx="0" dy="1.2"/>'
    '<feComponentTransfer><feFuncA type="linear" slope="0.22"/></feComponentTransfer>'
    '<feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge>'
    '</filter>'
    '<filter id="iib-hub-shadow" x="-25%" y="-25%" width="150%" height="150%">'
    '<feGaussianBlur in="SourceAlpha" stdDeviation="3"/>'
    '<feOffset dx="0" dy="2"/>'
    '<feComponentTransfer><feFuncA type="linear" slope="0.28"/></feComponentTransfer>'
    '<feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge>'
    '</filter>'
)


# ═════════════════════════════════════════════════════════════════
# Palette · IIB_PASTEL
# ═════════════════════════════════════════════════════════════════

IIB_PASTEL = Palette(
    name="IIB Pastel · Editorial Atelier",
    bg="#F0EBE0",            # cream 温和 paper
    bg_alt="#E9E1CE",
    bg_dim="#DED2B8",
    ink="#1A1A18",           # deep ink
    gray="rgba(90,80,66,0.70)",
    hair="#1A1A18",
    primary=HUE["salmon"],
    primary_dim=HUE["rose"],
    accent=HUE["peach"],
    accent_dim=HUE["sage"],
    positive=HUE["sage"],
    negative=HUE["rose"],
    head_family=FONT_SERIF,
    body_family=FONT_SANS,
    mono_family=FONT_SANS,
    kicker_letter_spacing=2.6,
    kicker_case="upper",
    section_numbering="arabic",
    folio_style="hairline",
    title_style="serif_italic",
    subtitle_style="sans_italic",
    figure_caption_prefix="FIG",
    signature_note="INFORMATION IS BEAUTIFUL · PASTEL EDITORIAL",
)


# ═════════════════════════════════════════════════════════════════
# Local SVG helpers
# ═════════════════════════════════════════════════════════════════

def _txt(x, y, s, *, size, family, weight=500, fill="#1A1A18",
         anchor="start", italic=False, letter_em: Optional[float] = None,
         opacity: Optional[float] = None) -> str:
    attrs = [
        f'x="{x}"', f'y="{y}"',
        f'font-family="{family}"',
        f'font-size="{size}"',
        f'fill="{fill}"',
        f'text-anchor="{anchor}"',
        f'font-weight="{weight}"',
    ]
    if italic:
        attrs.append('font-style="italic"')
    if letter_em is not None:
        attrs.append(f'letter-spacing="{letter_em}em"')
    if opacity is not None:
        attrs.append(f'opacity="{opacity}"')
    return f'<text {" ".join(attrs)}>{esc(s)}</text>'


def _rect(x, y, w, h, *, fill: Optional[str] = None,
          stroke: Optional[str] = None, sw: float = 1.0,
          rx: float = 0.0, opacity: Optional[float] = None,
          dash: Optional[str] = None, filter_id: Optional[str] = None) -> str:
    parts = [
        f'x="{x}"', f'y="{y}"', f'width="{w}"', f'height="{h}"',
        f'fill="{fill}"' if fill else 'fill="none"',
    ]
    if stroke:
        parts.append(f'stroke="{stroke}"')
        parts.append(f'stroke-width="{sw}"')
    if rx:
        parts.append(f'rx="{rx}"')
    if opacity is not None:
        parts.append(f'opacity="{opacity}"')
    if dash:
        parts.append(f'stroke-dasharray="{dash}"')
    if filter_id:
        parts.append(f'filter="url(#{filter_id})"')
    return f'<rect {" ".join(parts)}/>'


def _line(x1, y1, x2, y2, *, stroke: str = "#1A1A18", sw: float = 1.0,
          opacity: Optional[float] = None, dash: Optional[str] = None,
          linecap: Optional[str] = None) -> str:
    parts = [
        f'x1="{x1}"', f'y1="{y1}"', f'x2="{x2}"', f'y2="{y2}"',
        f'stroke="{stroke}"', f'stroke-width="{sw}"',
    ]
    if opacity is not None:
        parts.append(f'opacity="{opacity}"')
    if dash:
        parts.append(f'stroke-dasharray="{dash}"')
    if linecap:
        parts.append(f'stroke-linecap="{linecap}"')
    return f'<line {" ".join(parts)}/>'


def _circle(cx, cy, r, *, fill: Optional[str] = None,
            stroke: Optional[str] = None, sw: float = 1.0,
            opacity: Optional[float] = None) -> str:
    parts = [f'cx="{cx}"', f'cy="{cy}"', f'r="{r}"',
             f'fill="{fill}"' if fill else 'fill="none"']
    if stroke:
        parts.append(f'stroke="{stroke}"')
        parts.append(f'stroke-width="{sw}"')
    if opacity is not None:
        parts.append(f'opacity="{opacity}"')
    return f'<circle {" ".join(parts)}/>'


def _tint(hex_hue: str, alpha: float) -> str:
    h = hex_hue.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha:.3f})"


def _resolve_hue(hue_key_or_hex: str) -> str:
    if not hue_key_or_hex:
        return HUE["salmon"]
    if hue_key_or_hex.startswith("#"):
        return hue_key_or_hex
    return HUE.get(hue_key_or_hex, HUE["salmon"])


# ═════════════════════════════════════════════════════════════════
# Primitives
# ═════════════════════════════════════════════════════════════════

def svg_defs_iib(hues: Sequence[str] = HUE_ORDER) -> str:
    """一次注入 iib-soft-shadow + iib-hub-shadow filters · <defs> 段。

    hues 参数留作扩展接口（未来 gradient / marker 可按 hue 注入），当前
    版本只输出 filter，因为 pastel 卡片以纯色填充为主。
    """
    _ = hues  # reserved for future gradient injection
    return f"<defs>{_FILTER_DEFS}</defs>"


def numeral_kicker(x: float, y: float, num_text: str,
                   *, hue: str = "salmon",
                   palette: Palette = IIB_PASTEL) -> str:
    """"01 · WHAT IT IS" 编号 kicker · 数字用 hue tinted · 文字用 ink.

    num_text 建议格式："01 · WHAT IT IS" · 分隔符 " · " 用来切前缀。
    前缀 (01) 用 hue · 主 label 用 ink faded · letter-spacing 0.22em。
    """
    c = _resolve_hue(hue)
    size, fam, wt = TYPE_SCALE["kicker_num"]

    # 拆前缀
    if " · " in num_text:
        prefix, rest = num_text.split(" · ", 1)
    else:
        prefix, rest = num_text, ""

    parts: List[str] = []
    # 组装 tspan 输出
    inner = (
        f'<tspan fill="{c}" font-weight="800">{esc(prefix)}</tspan>'
    )
    if rest:
        inner += (
            f'<tspan dx="6" fill="rgba(26,26,24,0.55)" font-weight="700">'
            f' · {esc(rest)}</tspan>'
        )
    parts.append(
        f'<text x="{x}" y="{y}" font-family="{fam}" font-size="{size}" '
        f'font-weight="{wt}" letter-spacing="0.22em">{inner}</text>'
    )
    return "".join(parts)


def dot_row(x: float, y: float, n: int,
            *, hue: str = "salmon",
            filled: Optional[int] = None,
            spacing: float = 11.0,
            r: float = 3.6,
            palette: Palette = IIB_PASTEL) -> str:
    """N 圆点 grid (heredity 5/8 之类) · 从 (x,y) 起横排 · filled 个实心其余空心.

    默认全部实心（filled=None → n）。
    """
    c = _resolve_hue(hue)
    if filled is None:
        filled = n
    parts: List[str] = []
    for i in range(n):
        cx = x + i * spacing
        if i < filled:
            parts.append(_circle(cx, y, r, fill=c, stroke=c, sw=0.6))
        else:
            parts.append(_circle(cx, y, r,
                                 fill=palette.bg,
                                 stroke=c, sw=1.2, opacity=0.85))
    return "".join(parts)


def pastel_kpi_card(x: float, y: float, w: float, h: float,
                    *, kicker: str = "",
                    big_num: str = "",
                    unit: str = "",
                    note: str = "",
                    hue: str = "salmon",
                    palette: Palette = IIB_PASTEL,
                    rx: float = 6.0,
                    variant: str = "num",
                    dots: Optional[Tuple[int, int]] = None) -> str:
    """顶部大数字 KPI 卡 · pastel fill + numeral kicker + huge num + unit + note.

    Layout（相对 x,y · w×h · 参考 h≈220 · w≈180）：
        kicker      y +  22   (numeral_kicker · 已包含拆前缀)
        big_num     y +  76   (serif 36-44 · hue-tinted)
        unit        y + 100   (sans 10 · gray)
        divider     y + 118   (hair line)
        note        y + 138   (sans 9.5 · ink faded)
        dot_row     y + 178   (可选 · dots=(filled, total))

    variant:
        "num"       · big_num 用 kpi_num_xl · 数字/短 slug
        "compact"   · big_num 用 kpi_num · 长 slug
    """
    c = _resolve_hue(hue)
    parts: List[str] = []
    # 卡片 · 淡 tint 底 · 无描边 (IIB 风)
    parts.append(_rect(x, y, w, h,
                       fill=_tint(c, 0.32),
                       rx=rx, filter_id="iib-soft-shadow"))

    # kicker
    if kicker:
        parts.append(numeral_kicker(x + 14, y + 22, kicker,
                                    hue=hue, palette=palette))

    # big_num
    num_key = "kpi_num_xl" if variant == "num" else "kpi_num"
    size, fam, wt = TYPE_SCALE[num_key]
    if big_num:
        parts.append(_txt(x + 14, y + 76, big_num,
                          size=size, family=fam, weight=wt,
                          fill=palette.ink))
    # unit (小 sans 灰)
    if unit:
        size, fam, wt = TYPE_SCALE["kpi_unit"]
        parts.append(_txt(x + 14, y + 100, unit,
                          size=size, family=fam, weight=wt,
                          fill="rgba(26,26,24,0.60)",
                          italic=True))

    # divider hairline
    parts.append(_line(x + 14, y + 116, x + w - 14, y + 116,
                       stroke=palette.ink, sw=0.5, opacity=0.18))

    # note (多行 wrap 由 caller 用 \n 提供 · 这里简化：单/多行)
    if note:
        size, fam, wt = TYPE_SCALE["kpi_note"]
        lines = note.split("\n")
        for i, ln in enumerate(lines[:5]):
            parts.append(_txt(x + 14, y + 136 + i * 14, ln,
                              size=size, family=fam, weight=wt,
                              fill="rgba(26,26,24,0.78)"))

    # optional dot row（heredity 5/8）
    if dots:
        filled, total = dots
        parts.append(dot_row(x + 14, y + h - 22, total,
                             filled=filled, hue=hue,
                             spacing=11, r=3.6, palette=palette))
    return "".join(parts)


def hub_pastel(x: float, y: float, w: float, h: float,
               *, name: str = "",
               kicker: str = "",
               tagline: str = "",
               palette: Palette = IIB_PASTEL,
               hue: str = "salmon",
               rx: float = 6.0) -> str:
    """底部叙事图 · hub 中心卡 · kicker + 巨号 name + tagline (italic serif).

    Layout (w×h · 参考 220×140)：
        kicker      y +  22   (kicker_top · 灰 letter-spaced · e.g. "THE HUB · 3 complexes")
        name        y +  70   (hub_name serif 26 bold ink)
        divider     y +  88
        tagline     y + 110   (italic serif · gray)
    """
    c = _resolve_hue(hue)
    parts: List[str] = []
    parts.append(_rect(x, y, w, h,
                       fill=_tint(c, 0.32),
                       rx=rx, filter_id="iib-hub-shadow"))

    cx = x + w / 2

    if kicker:
        size, fam, wt = TYPE_SCALE["hub_kicker"]
        parts.append(_txt(cx, y + 22, kicker,
                          size=size, family=fam, weight=wt,
                          fill="rgba(26,26,24,0.60)",
                          anchor="middle", letter_em=0.22))

    if name:
        size, fam, wt = TYPE_SCALE["hub_name"]
        parts.append(_txt(cx, y + 70, name,
                          size=size, family=fam, weight=wt,
                          fill=palette.ink, anchor="middle",
                          letter_em=0.01))

    parts.append(_line(x + 24, y + 86, x + w - 24, y + 86,
                       stroke=palette.ink, sw=0.5, opacity=0.22))

    if tagline:
        size, fam, wt = TYPE_SCALE["hub_tag"]
        parts.append(_txt(cx, y + 110, tagline,
                          size=size, family=fam, weight=wt,
                          fill="rgba(26,26,24,0.72)",
                          anchor="middle", italic=True))
    return "".join(parts)


def patient_story_card(x: float, y: float, w: float, h: float,
                       *, title: str = "",
                       tagline: str = "",
                       complement_right: str = "",
                       hue: str = "salmon",
                       palette: Palette = IIB_PASTEL,
                       rx: float = 6.0,
                       label: str = "") -> str:
    """底部 patient story 叙事卡 · title 主 · tagline 副 · complement_right 右上 sublabel.

    Layout（参考 w=320 h=76）：
        [hue dot] title (bold sans)     .............. complement_right (右 anchor)
                  tagline (italic 副)
        底部 hairline

    label: 可选 · 大写字母角标 "A/B/C" 放最左（brca1_iib 用了 A/B/C）。
    """
    c = _resolve_hue(hue)
    parts: List[str] = []
    parts.append(_rect(x, y, w, h,
                       fill=_tint(c, 0.28),
                       rx=rx, filter_id="iib-soft-shadow"))

    # 左侧 label 圆
    text_x = x + 18
    if label:
        parts.append(_circle(x + 22, y + h / 2, 14,
                             fill=palette.ink, stroke=palette.ink, sw=1.0))
        parts.append(_txt(x + 22, y + h / 2 + 5, label,
                          size=13, family=FONT_SERIF, weight=800,
                          fill=palette.bg, anchor="middle"))
        text_x = x + 46

    # title
    if title:
        size, fam, wt = TYPE_SCALE["story_title"]
        parts.append(_txt(text_x, y + 26, title,
                          size=size, family=fam, weight=wt,
                          fill=palette.ink, letter_em=0.02))
    # tagline
    if tagline:
        size, fam, wt = TYPE_SCALE["story_tag"]
        parts.append(_txt(text_x, y + 46, tagline,
                          size=size, family=fam, weight=wt,
                          fill="rgba(26,26,24,0.68)",
                          italic=True))
    # right complement
    if complement_right:
        size, fam, wt = TYPE_SCALE["story_right"]
        parts.append(_txt(x + w - 14, y + 26, complement_right,
                          size=size, family=fam, weight=wt,
                          fill="rgba(26,26,24,0.60)",
                          anchor="end", letter_em=0.14))

    # 底 hairline
    parts.append(_line(x + 14, y + h - 12, x + w - 14, y + h - 12,
                       stroke=palette.ink, sw=0.5, opacity=0.16))
    return "".join(parts)


# ═════════════════════════════════════════════════════════════════
# Chrome · iib_chrome / iib_footer
# ═════════════════════════════════════════════════════════════════

def iib_chrome(*, kicker: str = "",
               title: str = "",
               subtitle: str = "",
               top_notes: Optional[Sequence[Tuple[str, float]]] = None,
               palette: Palette = IIB_PASTEL,
               canvas: CanvasProfile = HERO_CANVAS) -> str:
    """顶部 chrome · kicker + 大 serif italic title + subtitle + top notes.

    top_notes: [(text, x_center), ...] 顶部 "one gene · three winners · ..." 说明栏。
    title 支持 " · " 分割 → 前段 normal · 后段 italic (报纸风)。
    """
    is_embed = (canvas.w == 900 and canvas.h == 336)
    title_sz = 20 if is_embed else 32
    subtitle_sz = 10 if is_embed else 12
    kicker_sz = 8 if is_embed else 10
    note_sz = 8 if is_embed else 9.5

    parts: List[str] = []
    parts.append(_rect(0, 0, canvas.w, canvas.h, fill=palette.bg))

    if kicker:
        parts.append(_txt(canvas.margin_x, canvas.title_y - 22, kicker,
                          size=kicker_sz, family=FONT_SANS, weight=700,
                          fill=palette.primary, letter_em=0.28))

    # title · 支持 "prefix · italic-part"
    if title:
        if "," in title and title.count(",") == 1:
            head, tail = title.split(",", 1)
            head = head.strip() + ","
            tail = tail.strip()
            # 前段
            parts.append(
                f'<text x="{canvas.margin_x}" y="{canvas.title_y}" '
                f'font-family="{FONT_SERIF}" font-size="{title_sz}" '
                f'font-weight="700" fill="{palette.ink}" letter-spacing="0.01em">'
                f'{esc(head)}'
                f'<tspan dx="8" font-style="italic" font-weight="700">'
                f'{esc(tail)}</tspan>'
                f'</text>'
            )
        else:
            parts.append(_txt(canvas.margin_x, canvas.title_y, title,
                              size=title_sz, family=FONT_SERIF, weight=700,
                              fill=palette.ink, letter_em=0.01))

    if subtitle:
        parts.append(_txt(canvas.margin_x, canvas.subtitle_y, subtitle,
                          size=subtitle_sz, family=FONT_SANS, weight=500,
                          fill=palette.gray, letter_em=0.04, italic=True))

    # title hairline
    parts.append(_line(canvas.margin_x, canvas.title_hair_y,
                       canvas.w - canvas.margin_x, canvas.title_hair_y,
                       stroke=palette.ink, sw=0.5, opacity=0.22))

    if top_notes:
        for txt, cx in top_notes:
            parts.append(_txt(cx, canvas.title_hair_y + 20, txt,
                              size=note_sz, family=FONT_SANS, weight=600,
                              fill="rgba(26,26,24,0.68)",
                              anchor="middle", letter_em=0.18))
    return "".join(parts)


def iib_footer(*, one_liner_conclusion: str = "",
               source: str = "",
               credits: str = "",
               palette: Palette = IIB_PASTEL,
               canvas: CanvasProfile = HERO_CANVAS) -> str:
    """底部 chrome · italic 结论 + 底部小灰字 credits.

    one_liner_conclusion 会以大 serif italic 显示（结论意向）。
    credits + source 走底部小灰字 letter-spaced 大写。
    """
    is_embed = (canvas.w == 900 and canvas.h == 336)
    conc_sz = 11 if is_embed else 13
    cred_sz = 7 if is_embed else 8.5

    parts: List[str] = []
    # 底 hairline
    parts.append(_line(canvas.margin_x, canvas.bottom_hair_y,
                       canvas.w - canvas.margin_x, canvas.bottom_hair_y,
                       stroke=palette.ink, sw=0.5, opacity=0.18))

    if one_liner_conclusion:
        parts.append(_txt(canvas.margin_x, canvas.footer_line_y,
                          one_liner_conclusion,
                          size=conc_sz, family=FONT_SERIF, weight=500,
                          fill=palette.ink, italic=True,
                          letter_em=0.01))

    # credits (左) + source (右) · 底部小灰
    if credits:
        parts.append(_txt(canvas.margin_x, canvas.credits_y, credits,
                          size=cred_sz, family=FONT_SANS, weight=600,
                          fill=palette.gray, letter_em=0.20))
    if source:
        parts.append(_txt(canvas.w - canvas.margin_x, canvas.credits_y,
                          source,
                          size=cred_sz, family=FONT_SANS, weight=700,
                          fill=palette.gray,
                          anchor="end", letter_em=0.22))
    return "".join(parts)


# ═════════════════════════════════════════════════════════════════
# Skin protocol
# ═════════════════════════════════════════════════════════════════

class IBEditorialSkin:
    """K12 · ib_editorial · Information-Is-Beautiful pastel editorial skin."""

    name = "ib_editorial"

    def defs(self, palette: Palette) -> str:
        return svg_defs_iib(HUE_ORDER)

    def draw_node(self, x, y, w, h, label, palette: Palette,
                  kind: str = "kpi", palette_hue: str = "salmon",
                  hue: str = "salmon", **kwargs) -> str:
        pal = palette or IIB_PASTEL
        label = _label_clip(label, 48) if label else ""
        sub = _label_clip(kwargs.get("sublabel", ""), 60)
        note = kwargs.get("note", "")
        h_key = hue if hue else palette_hue

        if kind == "hub":
            return hub_pastel(x, y, w, h,
                              name=label,
                              kicker=kwargs.get("kicker", ""),
                              tagline=kwargs.get("tagline", ""),
                              palette=pal, hue=h_key)
        elif kind == "story":
            return patient_story_card(
                x, y, w, h,
                title=label,
                tagline=sub,
                complement_right=kwargs.get("complement_right", ""),
                label=kwargs.get("story_label", ""),
                hue=h_key, palette=pal,
            )
        else:  # kind == "kpi" or default
            return pastel_kpi_card(
                x, y, w, h,
                kicker=kwargs.get("kicker", ""),
                big_num=label,
                unit=sub,
                note=note,
                hue=h_key, palette=pal,
                variant=kwargs.get("variant", "num"),
                dots=kwargs.get("dots"),
            )

    def draw_edge(self, x1, y1, x2, y2, label, palette: Palette,
                  kind: str = "connector",
                  hue: str = "salmon", **kwargs) -> str:
        pal = palette or IIB_PASTEL
        c = _resolve_hue(hue)
        if kind == "connector":
            return _line(x1, y1, x2, y2, stroke=c, sw=1.4,
                         opacity=0.62, linecap="round")
        elif kind == "dashed":
            return _line(x1, y1, x2, y2, stroke=c, sw=1.2,
                         dash="3 3", opacity=0.55, linecap="round")
        else:  # hairline
            return _line(x1, y1, x2, y2, stroke=pal.ink, sw=0.6,
                         opacity=0.30)

    def draw_container(self, x, y, w, h, label, palette: Palette,
                       kind: str = "section", hue: str = "salmon",
                       **kwargs) -> str:
        pal = palette or IIB_PASTEL
        c = _resolve_hue(hue)
        parts: List[str] = []
        if kind == "tint_panel":
            parts.append(_rect(x, y, w, h, fill=_tint(c, 0.12), rx=6))
        else:  # section
            parts.append(_line(x, y, x + w, y,
                               stroke=pal.ink, sw=0.6, opacity=0.22))
            parts.append(_line(x, y + h, x + w, y + h,
                               stroke=pal.ink, sw=0.5, opacity=0.14))
            if label:
                parts.append(_txt(x + w / 2, y + 12, label,
                                  size=9, family=FONT_SANS, weight=700,
                                  fill=pal.gray, anchor="middle",
                                  letter_em=0.22))
        return "".join(parts)


IB_EDITORIAL = IBEditorialSkin()


__all__ = [
    # Skin class + singleton
    "IBEditorialSkin", "IB_EDITORIAL",
    # Palette
    "IIB_PASTEL",
    # Canvas
    "CanvasProfile", "HERO_CANVAS", "EMBED_CANVAS",
    # Tokens
    "HUE", "HUE_ORDER", "TYPE_SCALE", "FONT_SERIF", "FONT_SANS",
    # Primitives
    "svg_defs_iib",
    "numeral_kicker",
    "dot_row",
    "pastel_kpi_card",
    "hub_pastel",
    "patient_story_card",
    # Chrome
    "iib_chrome", "iib_footer",
]
