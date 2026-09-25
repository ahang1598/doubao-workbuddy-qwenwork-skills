"""
SaaS Product skin · Near-black · Cyan Neon · Magenta Accent

参照 ppi_diagram/brca1_saas.png 逆向抽视觉 tokens：
    * bg=#0A0F1E near-black · card_bg=#1E2942 深靛卡片
    * primary=#00E5C7 cyan neon · secondary=#EC4899 magenta / rose
    * ink=#F1F5F9 off-white · gray=#94A3B8 slate 亮
    * top nav: brand-left + links-right + subtle bottom hairline
    * hub: dark rounded rect + neon glow border + white serif name
    * neon chip: dark chip + neon border/glow · SENSOR / TEAM 类
    * cta button: neon fill + black text + 圆角 pill + → arrow
    * stat row: 巨号 stat (44pt) + 灰色说明 · 底部 4 栏
    * connector: neon stroke + glow filter

对比 strategic_briefing (navy/gold)：本 skin 更 near-black + neon 更亮 · SaaS 产品页风。
Canvas 结构复用 editorial_atelier.CanvasProfile · HERO 1400×820 / EMBED 900×336。

被期望的 node.kind: hub · neon_chip · chip · stat · cta
被期望的 edge.kind: rule · rule_arrow · connector · edge_glow

Primitives (module-level · preset 直接 import)：
    svg_defs_saas · neon_chip · hub_neon · cta_button · nav_bar_top
    stat_row_item · edge_glow · saas_chrome · saas_footer
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from ..engine import esc
from ..palettes import Palette
from ._base import _label_clip
from .editorial_atelier import CanvasProfile, HERO_CANVAS, EMBED_CANVAS


# ═════════════════════════════════════════════════════════════════
# Hue table · dark-bg SaaS 双 neon 主色
# ═════════════════════════════════════════════════════════════════

HUE_SAAS = {
    "cyan":    "#00E5C7",   # primary neon · 60% 权重
    "teal":    "#5EEAD4",   # cyan 淡 · secondary
    "magenta": "#EC4899",   # 二级 neon · rose/magenta
    "violet":  "#A78BFA",   # tertiary accent
    "amber":   "#FBBF24",   # 数字/关键 highlight
    "lime":    "#84CC16",   # positive
    "coral":   "#F87171",   # negative
    "sky":     "#38BDF8",   # cool 中性
}

HUE_ORDER_SAAS: Tuple[str, ...] = (
    "cyan", "magenta", "violet", "amber", "sky", "teal", "lime", "coral",
)


# ─────────── Typography ───────────
FONT_SANS_SAAS = "Inter, sans-serif"
FONT_SERIF_SAAS = "Georgia, serif"

TYPE_SCALE_SAAS = {
    "brand":         (14, FONT_SANS_SAAS,  800),   # 左上 logo/brand
    "nav_link":      (10, FONT_SANS_SAAS,  600),   # 右上 nav 链接
    "kicker":        (10, FONT_SANS_SAAS,  700),   # PATHWAY MAP · KICKER
    "kicker_embed":  (8,  FONT_SANS_SAAS,  700),
    "title":         (34, FONT_SANS_SAAS,  800),   # hero 巨号 title
    "title_embed":   (18, FONT_SANS_SAAS,  800),
    "subtitle":      (13, FONT_SANS_SAAS,  500),
    "subtitle_em":   (10, FONT_SANS_SAAS,  500),
    "hub_name":      (22, FONT_SANS_SAAS,  800),   # hub 中心名
    "hub_name_em":   (17, FONT_SANS_SAAS,  800),
    "hub_tag":       (9,  FONT_SANS_SAAS,  700),   # hub 上方 tag
    "hub_role":      (10, FONT_SANS_SAAS,  500),   # hub 内 tagline
    "hub_stat":      (12, FONT_SANS_SAAS,  700),
    "chip_kicker":   (8,  FONT_SANS_SAAS,  700),   # SENSOR · TEAM 上方小字
    "chip_label":    (13, FONT_SANS_SAAS,  800),   # chip 主标签
    "chip_sub":      (9,  FONT_SANS_SAAS,  500),   # chip 下方 desc
    "chip_meta":     (8,  FONT_SANS_SAAS,  600),
    "stat_number":   (36, FONT_SANS_SAAS,  800),   # 底部巨号 stat
    "stat_number_em":(24, FONT_SANS_SAAS,  800),
    "stat_label":    (10, FONT_SANS_SAAS,  500),
    "stat_note":     (9,  FONT_SANS_SAAS,  500),
    "cta":           (12, FONT_SANS_SAAS,  800),   # cta 按钮字
    "cta_em":        (10, FONT_SANS_SAAS,  800),
    "section":       (10, FONT_SANS_SAAS,  700),
    "footer":        (9,  FONT_SANS_SAAS,  500),
}


# ─────────── Filter defs ───────────
# saas-glow: neon 光晕 · stdDeviation 4 · feMerge 合并原图 + 模糊
# saas-hub-halo: 更大范围 · stdDeviation 5.5 · 只输出模糊
# saas-inner-shadow: 卡片轻微内阴 · dark bg 上 tint 卡片提亮
_FILTER_DEFS_SAAS = (
    '<filter id="saas-glow" x="-40%" y="-40%" width="180%" height="180%">'
    '<feGaussianBlur in="SourceGraphic" stdDeviation="3.5" result="blur"/>'
    '<feMerge>'
    '<feMergeNode in="blur"/>'
    '<feMergeNode in="blur"/>'
    '<feMergeNode in="SourceGraphic"/>'
    '</feMerge>'
    '</filter>'
    '<filter id="saas-hub-halo" x="-60%" y="-60%" width="220%" height="220%">'
    '<feGaussianBlur in="SourceGraphic" stdDeviation="5.5"/>'
    '</filter>'
    '<filter id="saas-soft-shadow" x="-20%" y="-20%" width="140%" height="140%">'
    '<feGaussianBlur in="SourceAlpha" stdDeviation="3"/>'
    '<feOffset dx="0" dy="3"/>'
    '<feComponentTransfer><feFuncA type="linear" slope="0.55"/></feComponentTransfer>'
    '<feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge>'
    '</filter>'
    '<filter id="saas-inner-shadow" x="-10%" y="-10%" width="120%" height="120%">'
    '<feGaussianBlur in="SourceAlpha" stdDeviation="1.6"/>'
    '<feOffset dx="0" dy="1"/>'
    '<feComposite in2="SourceAlpha" operator="arithmetic" k2="-1" k3="1" result="inner"/>'
    '<feColorMatrix in="inner" type="matrix" '
    'values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 0.35 0"/>'
    '<feComposite in2="SourceGraphic" operator="in"/>'
    '<feMerge><feMergeNode in="SourceGraphic"/><feMergeNode/></feMerge>'
    '</filter>'
    '<filter id="saas-line-glow" x="-30%" y="-30%" width="160%" height="160%">'
    '<feGaussianBlur in="SourceGraphic" stdDeviation="2.5"/>'
    '</filter>'
)


def _gradient_defs_saas(hues: Sequence[str]) -> str:
    """每支 hue 生成 saas-r-<hue> linearGradient · 用于 ribbon / neon-fill."""
    out: List[str] = []
    for name in hues:
        c = HUE_SAAS.get(name, HUE_SAAS["cyan"])
        gid = f"saas-r-{name}"
        out.append(
            f'<linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="0">'
            f'<stop offset="0" stop-color="{c}" stop-opacity="0.85"/>'
            f'<stop offset="1" stop-color="{c}" stop-opacity="0.30"/>'
            f'</linearGradient>'
        )
    # 通用 dark card gradient · 从 top 稍暗到 bot 稍亮
    out.append(
        '<linearGradient id="saas-card-grad" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#1E2942" stop-opacity="1"/>'
        '<stop offset="1" stop-color="#151E33" stop-opacity="1"/>'
        '</linearGradient>'
    )
    # hub 中央 radial glow
    out.append(
        '<radialGradient id="saas-hub-radial" cx="0.5" cy="0.5" r="0.6">'
        '<stop offset="0" stop-color="#00E5C7" stop-opacity="0.30"/>'
        '<stop offset="0.7" stop-color="#00E5C7" stop-opacity="0.06"/>'
        '<stop offset="1" stop-color="#00E5C7" stop-opacity="0"/>'
        '</radialGradient>'
    )
    return "".join(out)


def _marker_defs_saas(hues: Sequence[str]) -> str:
    """每支 hue arrow marker · saas-arr-<hue>."""
    out: List[str] = []
    for name in hues:
        c = HUE_SAAS.get(name, HUE_SAAS["cyan"])
        mid = f"saas-arr-{name}"
        out.append(
            f'<marker id="{mid}" viewBox="0 0 10 10" refX="9" refY="5" '
            f'markerWidth="7" markerHeight="7" orient="auto">'
            f'<path d="M 0 0 L 9 5 L 0 10 Z" fill="{c}"/></marker>'
        )
    return "".join(out)


# ═════════════════════════════════════════════════════════════════
# Palette · SAAS_NIGHT
# ═════════════════════════════════════════════════════════════════

SAAS_NIGHT = Palette(
    name="SaaS Night · Neon Product",
    bg="#0A0F1E",              # near-black · 大面积底
    bg_alt="#1E2942",          # card 深靛卡片
    bg_dim="#151E33",          # 三级 深靛
    ink="#F1F5F9",             # off-white 主字
    gray="rgba(148,163,184,0.85)",  # slate-300 · 二级 gray
    hair="rgba(241,245,249,0.14)",  # 分隔线 white 淡
    primary="#00E5C7",         # cyan neon
    primary_dim="#5EEAD4",     # cyan 淡 · teal
    accent="#EC4899",          # magenta neon
    accent_dim="#A78BFA",      # violet accent
    positive="#84CC16",        # lime
    negative="#F87171",        # coral
    head_family=FONT_SANS_SAAS,
    body_family=FONT_SANS_SAAS,
    mono_family=FONT_SANS_SAAS,
    kicker_letter_spacing=2.4,
    kicker_case="upper",
    section_numbering="arabic",
    folio_style="hairline",
    title_style="sans_bold",
    subtitle_style="sans_italic",
    figure_caption_prefix="MAP",
    signature_note="SAAS PRODUCT · LIVE",
)


# ═════════════════════════════════════════════════════════════════
# 低层 SVG helper (dark bg · off-white 默认字色)
# ═════════════════════════════════════════════════════════════════

def _txt(x, y, s, *, size, family, weight=500, fill="#F1F5F9",
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


def _line(x1, y1, x2, y2, *, stroke: str = "#F1F5F9", sw: float = 1.0,
          opacity: Optional[float] = None, dash: Optional[str] = None,
          linecap: Optional[str] = None,
          marker_end: Optional[str] = None,
          filter_id: Optional[str] = None) -> str:
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
    if marker_end:
        parts.append(f'marker-end="url(#{marker_end})"')
    if filter_id:
        parts.append(f'filter="url(#{filter_id})"')
    return f'<line {" ".join(parts)}/>'


def _tint(hex_hue: str, alpha: float) -> str:
    """把 #RRGGBB 加上 alpha · 返回 rgba() 字符串."""
    h = hex_hue.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha:.3f})"


def _resolve_hue(hue_key_or_hex: str) -> str:
    if not hue_key_or_hex:
        return HUE_SAAS["cyan"]
    if hue_key_or_hex.startswith("#"):
        return hue_key_or_hex
    return HUE_SAAS.get(hue_key_or_hex, HUE_SAAS["cyan"])


# ═════════════════════════════════════════════════════════════════
# Primitive helpers · module-level (preset 直接 import 用)
# ═════════════════════════════════════════════════════════════════

def svg_defs_saas(hues: Sequence[str] = HUE_ORDER_SAAS,
                  include_markers: bool = True,
                  include_gradients: bool = True) -> str:
    """一次注入 filter + hue gradient + hue marker · <defs> 段.

    preset 在渲染前置调用 · 生成的字符串直接拼进 SVG 头.
    """
    inner = _FILTER_DEFS_SAAS
    if include_gradients:
        inner += _gradient_defs_saas(hues)
    if include_markers:
        inner += _marker_defs_saas(hues)
    return f"<defs>{inner}</defs>"


def neon_chip(x: float, y: float, w: float, h: float, *,
              label: str = "",
              sub: str = "",
              kicker: str = "",
              hue: str = "cyan",
              palette: Palette = SAAS_NIGHT,
              rx: float = 10.0) -> str:
    """Dark chip + neon border + subtle glow · brca1_saas 左右列 SENSOR/TEAM 卡.

    Layout (基础 200×88 · 按传入 w/h 缩放)：
        kicker (8pt neon caps)       y = y + 15
        label (13pt bold white)      y = y + 34
        sub (9pt gray)               y = y + 52 · 可换 2 行
    """
    c = _resolve_hue(hue)
    parts: List[str] = []
    # 外层 glow · 只画 stroke 走 glow filter
    parts.append(_rect(x, y, w, h,
                       fill=None, stroke=c, sw=1.4,
                       rx=rx, opacity=0.55, filter_id="saas-glow"))
    # 卡片底 (dark card gradient)
    parts.append(_rect(x, y, w, h, fill="url(#saas-card-grad)", rx=rx))
    # 内 tint 提亮 + neon border 主 stroke
    parts.append(_rect(x, y, w, h,
                       fill=_tint(c, 0.05),
                       stroke=c, sw=1.3, rx=rx, opacity=0.95))
    # kicker (小 neon caps)
    if kicker:
        ksz, kfam, kwt = TYPE_SCALE_SAAS["chip_kicker"]
        parts.append(_txt(x + 14, y + 17, kicker,
                          size=ksz, family=kfam, weight=kwt,
                          fill=c, letter_em=0.22))
    # label (主标)
    if label:
        lsz, lfam, lwt = TYPE_SCALE_SAAS["chip_label"]
        parts.append(_txt(x + 14, y + 37, label,
                          size=lsz, family=lfam, weight=lwt,
                          fill=palette.ink))
    # sub (说明)
    if sub:
        ssz, sfam, swt = TYPE_SCALE_SAAS["chip_sub"]
        parts.append(_txt(x + 14, y + 55, sub,
                          size=ssz, family=sfam, weight=swt,
                          fill=palette.gray))
    return "".join(parts)


def hub_neon(x: float, y: float, w: float, h: float, *,
             name: str = "",
             tag: str = "",
             role: str = "",
             tagline: str = "",
             stat: str = "",
             stat_note: str = "",
             hue: str = "cyan",
             palette: Palette = SAAS_NIGHT,
             with_halo: bool = True,
             name_size_key: str = "hub_name") -> str:
    """Dark rounded rect + neon glow border + 中央 radial glow + 4 行内容.

    Layout (基础 220×130 · 按传入 w/h 缩放)：
        tag chip (top-center 8pt neon)     y = y + 4 · pill
        name (22pt bold white)             y = y + h*0.42
        role (9pt gray caps)               y = y + h*0.60
        divider hairline                   y = y + h*0.68
        tagline (10pt italic gray)         y = y + h*0.80
        stat + note                        y = y + h*0.94
    """
    c = _resolve_hue(hue)
    parts: List[str] = []
    # 外 halo · 大范围 blur
    if with_halo:
        halo_pad = 12
        parts.append(_rect(
            x - halo_pad, y - halo_pad,
            w + halo_pad * 2, h + halo_pad * 2,
            fill=None, stroke=c, sw=2.5, rx=16, opacity=0.55,
            filter_id="saas-hub-halo",
        ))
    # 卡片底 · dark card
    parts.append(_rect(x, y, w, h, fill="url(#saas-card-grad)", rx=14,
                       filter_id="saas-soft-shadow"))
    # 中央 radial cyan glow (让 hub 内部显得有光)
    parts.append(_rect(x + 6, y + 6, w - 12, h - 12,
                       fill="url(#saas-hub-radial)", rx=12))
    # neon border 主 stroke (强对比)
    parts.append(_rect(x, y, w, h,
                       fill=None, stroke=c, sw=2.2, rx=14))
    # 再叠一层薄 stroke 打光 (更亮 · 加 opacity 0.35)
    parts.append(_rect(x + 1.5, y + 1.5, w - 3, h - 3,
                       fill=None, stroke="#FFFFFF", sw=0.6, rx=12.5,
                       opacity=0.28))

    cx = x + w / 2
    # tag chip (顶部 pill · 用 neon 亮字)
    if tag:
        tsz, tfam, twt = TYPE_SCALE_SAAS["hub_tag"]
        # tag pill (semi-tint 底 + neon stroke)
        tag_w = min(w * 0.55, len(tag) * 6.2 + 20)
        tag_h = 16
        tag_x = cx - tag_w / 2
        tag_y = y - tag_h / 2
        parts.append(_rect(tag_x, tag_y, tag_w, tag_h,
                           fill=palette.bg, stroke=c, sw=1.2,
                           rx=tag_h / 2))
        parts.append(_txt(cx, tag_y + tag_h / 2 + 3.5, tag,
                          size=tsz, family=tfam, weight=twt,
                          fill=c, anchor="middle", letter_em=0.22))
    # name (主 · bold white 巨号)
    if name:
        nsz, nfam, nwt = TYPE_SCALE_SAAS[name_size_key]
        parts.append(_txt(cx, y + h * 0.42, name,
                          size=nsz, family=nfam, weight=nwt,
                          fill=palette.ink, anchor="middle"))
    # role (灰 caps · kicker 风)
    if role:
        rsz, rfam, rwt = TYPE_SCALE_SAAS["hub_role"]
        parts.append(_txt(cx, y + h * 0.60, role,
                          size=rsz, family=rfam, weight=rwt,
                          fill=palette.gray, anchor="middle",
                          letter_em=0.06))
    # divider hair
    parts.append(_line(x + 22, y + h * 0.68, x + w - 22, y + h * 0.68,
                       stroke=_tint(c, 0.45), sw=0.8, opacity=0.8))
    # tagline (italic gray)
    if tagline:
        parts.append(_txt(cx, y + h * 0.80, tagline,
                          size=10, family=FONT_SANS_SAAS, weight=500,
                          fill=palette.gray, anchor="middle", italic=True))
    # stat + note (bottom · big neon num + gray note)
    if stat:
        line_y = y + h * 0.94
        stat_svg = (
            f'<text x="{cx}" y="{line_y}" text-anchor="middle" '
            f'font-family="{FONT_SANS_SAAS}" font-size="12" '
            f'font-weight="800" fill="{c}">{esc(stat)}'
        )
        if stat_note:
            stat_svg += (
                f'<tspan dx="6" font-family="{FONT_SANS_SAAS}" '
                f'font-size="10" font-weight="600" '
                f'fill="rgba(148,163,184,0.85)">{esc(stat_note)}</tspan>'
            )
        stat_svg += '</text>'
        parts.append(stat_svg)
    return "".join(parts)


def cta_button(x: float, y: float, w: float, h: float, *,
               text: str = "Explore full pathway",
               hue: str = "cyan",
               palette: Palette = SAAS_NIGHT,
               with_arrow: bool = True) -> str:
    """Neon fill pill + black text + 右侧 → arrow · 底部 CTA.

    fill = 亮 neon (纯 hue)
    text = near-black (对比 4.5:1+)
    rx = h/2 (pill)
    """
    c = _resolve_hue(hue)
    parts: List[str] = []
    # glow halo 外圈
    parts.append(_rect(x - 4, y - 4, w + 8, h + 8,
                       fill=None, stroke=c, sw=1.5,
                       rx=(h + 8) / 2, opacity=0.5,
                       filter_id="saas-glow"))
    # 主体 pill · neon fill
    parts.append(_rect(x, y, w, h,
                       fill=c, stroke=None, rx=h / 2))
    # 内 highlight 顶端 (让 pill 有点立体感)
    parts.append(_rect(x + 2, y + 2, w - 4, h / 2 - 2,
                       fill="rgba(255,255,255,0.18)",
                       rx=(h - 4) / 2))
    # text (near-black)
    tsz, tfam, twt = TYPE_SCALE_SAAS["cta"]
    label = text
    if with_arrow:
        label = f"{text}  →"
    parts.append(_txt(x + w / 2, y + h / 2 + 4.5, label,
                      size=tsz, family=tfam, weight=twt,
                      fill=palette.bg, anchor="middle"))
    return "".join(parts)


def nav_bar_top(x: float, y: float, w: float, *,
                brand_left: str = "boltrepair",
                brand_kicker: str = "",
                links_right: Sequence[str] = ("Overview", "Live map"),
                highlight_last: bool = True,
                palette: Palette = SAAS_NIGHT,
                hue: str = "cyan",
                height: float = 44.0) -> str:
    """顶部 nav · 左 brand + 右 nav 链接 + 底部 hairline.

    x/y = nav 左上角 · w = nav 宽 · height = nav 高
    highlight_last=True: 最后一个链接高亮为 neon pill (Live map 效果)
    """
    c = _resolve_hue(hue)
    parts: List[str] = []
    # bottom hair
    parts.append(_line(x, y + height, x + w, y + height,
                       stroke=palette.hair, sw=0.8, opacity=1.0))
    # brand · dot + 名字
    dot_r = 5
    dot_cx = x + 4 + dot_r
    dot_cy = y + height / 2 - 1
    parts.append(
        f'<circle cx="{dot_cx}" cy="{dot_cy}" r="{dot_r}" fill="{c}" '
        f'filter="url(#saas-glow)" opacity="0.9"/>'
    )
    parts.append(
        f'<circle cx="{dot_cx}" cy="{dot_cy}" r="{dot_r}" fill="{c}"/>'
    )
    bsz, bfam, bwt = TYPE_SCALE_SAAS["brand"]
    parts.append(_txt(dot_cx + dot_r + 8, dot_cy + 3.5, brand_left,
                      size=bsz, family=bfam, weight=bwt,
                      fill=palette.ink))
    # brand kicker (下方小字)
    if brand_kicker:
        parts.append(_txt(dot_cx + dot_r + 8, dot_cy + 17, brand_kicker,
                          size=8, family=FONT_SANS_SAAS, weight=600,
                          fill=palette.gray, letter_em=0.22))

    # right side nav links
    nsz, nfam, nwt = TYPE_SCALE_SAAS["nav_link"]
    right_x = x + w - 6
    # 从右往左排 · 每个 link 之间 gap 22
    last_idx = len(links_right) - 1
    for i in range(last_idx, -1, -1):
        link = links_right[i]
        is_highlight = highlight_last and i == last_idx
        if is_highlight:
            # pill highlight
            pw = len(link) * 6.6 + 22
            ph = 22
            px = right_x - pw
            py = dot_cy - ph / 2
            parts.append(_rect(px, py, pw, ph,
                               fill=c, stroke=None, rx=ph / 2))
            parts.append(_txt(px + pw / 2, py + ph / 2 + 3.8, link,
                              size=nsz, family=nfam, weight=800,
                              fill=palette.bg, anchor="middle"))
            right_x = px - 18
        else:
            parts.append(_txt(right_x, dot_cy + 3.5, link,
                              size=nsz, family=nfam, weight=nwt,
                              fill=palette.ink, anchor="end", opacity=0.85))
            right_x -= len(link) * 6.6 + 22
    return "".join(parts)


def stat_row_item(x: float, y: float, *,
                  number: str = "",
                  label: str = "",
                  note: str = "",
                  hue: Optional[str] = None,
                  palette: Palette = SAAS_NIGHT,
                  canvas: CanvasProfile = HERO_CANVAS) -> str:
    """底部 stat row 单元 · 巨号 number (36pt) + label + note.

    x/y = 单元左上角。号字左对齐 · label / note 也左对齐 · 无 border。
    hue=None → number 用 ink 白; 传 hue → number 用 neon.
    """
    is_embed = (canvas.w == 900 and canvas.h == 336)
    num_key = "stat_number_em" if is_embed else "stat_number"
    parts: List[str] = []
    nsz, nfam, nwt = TYPE_SCALE_SAAS[num_key]
    lsz, lfam, lwt = TYPE_SCALE_SAAS["stat_label"]
    ntsz, ntfam, ntwt = TYPE_SCALE_SAAS["stat_note"]
    num_color = _resolve_hue(hue) if hue else palette.ink
    if number:
        parts.append(_txt(x, y + nsz * 0.85, number,
                          size=nsz, family=nfam, weight=nwt,
                          fill=num_color))
    if label:
        parts.append(_txt(x, y + nsz * 0.85 + 18, label,
                          size=lsz, family=lfam, weight=700,
                          fill=palette.ink, letter_em=0.02))
    if note:
        parts.append(_txt(x, y + nsz * 0.85 + 34, note,
                          size=ntsz, family=ntfam, weight=ntwt,
                          fill=palette.gray))
    return "".join(parts)


def edge_glow(x1: float, y1: float, x2: float, y2: float, *,
              hue: str = "cyan",
              sw: float = 1.8,
              opacity: float = 0.9,
              with_arrow: bool = False,
              with_glow: bool = True) -> str:
    """Neon edge with glow filter · connector 连接 hub 与 chip/team.

    with_arrow=True: 右端加 marker_end
    with_glow=True: 底下先画一根粗模糊线打光 · 再画主 stroke
    """
    c = _resolve_hue(hue)
    parts: List[str] = []
    if with_glow:
        # 打光层 · 粗 + blur + 低 alpha
        parts.append(_line(x1, y1, x2, y2, stroke=c,
                           sw=sw + 3, opacity=0.35,
                           filter_id="saas-line-glow"))
    marker = f"saas-arr-{hue}" if with_arrow else None
    parts.append(_line(x1, y1, x2, y2, stroke=c, sw=sw,
                       opacity=opacity, linecap="round",
                       marker_end=marker))
    return "".join(parts)


# ═════════════════════════════════════════════════════════════════
# Chrome · saas_chrome (top) · saas_footer (bottom)
# ═════════════════════════════════════════════════════════════════

def saas_chrome(*, nav_left: str = "boltrepair",
                nav_kicker: str = "",
                nav_right: Sequence[str] = ("Overview", "Live map"),
                kicker: str = "",
                title: str = "",
                title_highlight: str = "",
                subtitle: str = "",
                encoding_note_right: str = "",
                palette: Palette = SAAS_NIGHT,
                canvas: CanvasProfile = HERO_CANVAS,
                hue: str = "cyan") -> str:
    """顶部 chrome · 大 dark bg + nav_bar + kicker + big title + subtitle.

    title_highlight: 会被替换成 neon 高亮的关键词 (case-sensitive substring)
    canvas=EMBED 时 title 缩到 18pt · nav 缩到 9pt
    """
    is_embed = (canvas.w == 900 and canvas.h == 336)
    title_sz = TYPE_SCALE_SAAS["title_embed"][0] if is_embed else TYPE_SCALE_SAAS["title"][0]
    kicker_sz = TYPE_SCALE_SAAS["kicker_embed"][0] if is_embed else TYPE_SCALE_SAAS["kicker"][0]
    subtitle_sz = TYPE_SCALE_SAAS["subtitle_em"][0] if is_embed else TYPE_SCALE_SAAS["subtitle"][0]
    c = _resolve_hue(hue)
    parts: List[str] = []
    # 大背景 · near-black
    parts.append(_rect(0, 0, canvas.w, canvas.h, fill=palette.bg))
    # subtle bg gradient/pattern 打气氛 · 用 radial glow 淡淡一层
    parts.append(
        f'<ellipse cx="{canvas.w * 0.72}" cy="{canvas.h * 0.42}" '
        f'rx="{canvas.w * 0.35}" ry="{canvas.h * 0.35}" '
        f'fill="{_tint(c, 0.06)}" filter="url(#saas-hub-halo)"/>'
    )
    parts.append(
        f'<ellipse cx="{canvas.w * 0.22}" cy="{canvas.h * 0.75}" '
        f'rx="{canvas.w * 0.30}" ry="{canvas.h * 0.28}" '
        f'fill="{_tint(HUE_SAAS["magenta"], 0.05)}" '
        f'filter="url(#saas-hub-halo)"/>'
    )
    # nav bar
    nav_h = 44 if not is_embed else 30
    nav_y = 18 if not is_embed else 8
    parts.append(nav_bar_top(canvas.margin_x, nav_y,
                             canvas.w - canvas.margin_x * 2,
                             brand_left=nav_left,
                             brand_kicker=nav_kicker,
                             links_right=nav_right,
                             highlight_last=True,
                             palette=palette,
                             hue=hue,
                             height=nav_h))
    # kicker (小 neon caps)
    if kicker:
        parts.append(_txt(canvas.margin_x, nav_y + nav_h + 30, kicker,
                          size=kicker_sz, family=FONT_SANS_SAAS,
                          weight=700, fill=c, letter_em=0.24))
    # title (big bold white)
    if title:
        title_y = nav_y + nav_h + (58 if not is_embed else 40)
        # 处理 highlight: 找到 substring · 用两段 tspan 拼
        if title_highlight and title_highlight in title:
            idx = title.find(title_highlight)
            before = title[:idx]
            after = title[idx + len(title_highlight):]
            svg = (
                f'<text x="{canvas.margin_x}" y="{title_y}" '
                f'font-family="{FONT_SANS_SAAS}" font-size="{title_sz}" '
                f'font-weight="800" fill="{palette.ink}">'
                f'{esc(before)}'
                f'<tspan fill="{c}">{esc(title_highlight)}</tspan>'
                f'{esc(after)}</text>'
            )
            parts.append(svg)
        else:
            parts.append(_txt(canvas.margin_x, title_y, title,
                              size=title_sz, family=FONT_SANS_SAAS,
                              weight=800, fill=palette.ink))
    # subtitle
    if subtitle:
        sub_y = nav_y + nav_h + (86 if not is_embed else 58)
        parts.append(_txt(canvas.margin_x, sub_y, subtitle,
                          size=subtitle_sz, family=FONT_SANS_SAAS,
                          weight=500, fill=palette.gray))
    # encoding note right (若有 · title 行右对齐)
    if encoding_note_right:
        note_y = nav_y + nav_h + (58 if not is_embed else 40)
        parts.append(_txt(canvas.w - canvas.margin_x, note_y,
                          encoding_note_right,
                          size=subtitle_sz, family=FONT_SANS_SAAS,
                          weight=500, fill=palette.gray,
                          anchor="end", italic=True))
    return "".join(parts)


def saas_footer(*, stat_items: Optional[Sequence[dict]] = None,
                cta_text: str = "",
                cta_hue: str = "cyan",
                caption: str = "",
                source: str = "",
                palette: Palette = SAAS_NIGHT,
                canvas: CanvasProfile = HERO_CANVAS,
                kicker: str = "THE NUMBERS THAT MATTER") -> str:
    """底部 chrome · top hairline + kicker + stat row + CTA button on right.

    stat_items: list of dicts · 每个 dict {number, label, note, hue?} · 平均分布左侧
    cta_text: CTA 按钮文字 · 空则不画
    """
    is_embed = (canvas.w == 900 and canvas.h == 336)
    parts: List[str] = []
    # top hair
    parts.append(_line(canvas.margin_x, canvas.bottom_hair_y,
                       canvas.w - canvas.margin_x, canvas.bottom_hair_y,
                       stroke=palette.hair, sw=0.8, opacity=1.0))
    # kicker
    kicker_y = canvas.bottom_hair_y + (18 if not is_embed else 12)
    if kicker:
        c = _resolve_hue(cta_hue)
        parts.append(_txt(canvas.margin_x, kicker_y, kicker,
                          size=(9 if is_embed else 10),
                          family=FONT_SANS_SAAS, weight=700,
                          fill=c, letter_em=0.24))
    # stat row · 分布在 kicker 下方
    stat_row_y = kicker_y + (10 if is_embed else 12)
    if stat_items:
        n = len(stat_items)
        # 计算 CTA 占的宽度 (若有 CTA · stat 只占左 ~65%)
        avail_w = canvas.w - canvas.margin_x * 2
        if cta_text:
            avail_w = avail_w * 0.62
        col_w = avail_w / n
        for i, item in enumerate(stat_items):
            sx = canvas.margin_x + i * col_w
            parts.append(stat_row_item(
                sx, stat_row_y,
                number=item.get("number", ""),
                label=item.get("label", ""),
                note=item.get("note", ""),
                hue=item.get("hue"),
                palette=palette,
                canvas=canvas,
            ))
    # CTA button (右下 · pill)
    if cta_text:
        btn_w = min(240, len(cta_text) * 8.5 + 60)
        btn_h = 40 if not is_embed else 28
        btn_x = canvas.w - canvas.margin_x - btn_w
        btn_y = stat_row_y + (18 if not is_embed else 6)
        parts.append(cta_button(btn_x, btn_y, btn_w, btn_h,
                                text=cta_text, hue=cta_hue,
                                palette=palette, with_arrow=True))
    # caption + source (最底行)
    if caption:
        parts.append(_txt(canvas.margin_x, canvas.source_y, caption,
                          size=(8 if is_embed else 9),
                          family=FONT_SANS_SAAS, weight=500,
                          fill=palette.gray, italic=True))
    if source:
        parts.append(_txt(canvas.w - canvas.margin_x, canvas.source_y, source,
                          size=(8 if is_embed else 9),
                          family=FONT_SANS_SAAS, weight=700,
                          fill=palette.gray, anchor="end", letter_em=0.22))
    return "".join(parts)


# ═════════════════════════════════════════════════════════════════
# Skin 协议实现 · draw_node / draw_edge / draw_container / defs
# ═════════════════════════════════════════════════════════════════

class SaaSProductSkin:
    """SaaS Product · Near-black + Cyan Neon + Magenta 产品页 skin."""

    name = "saas_product"

    def defs(self, palette: Palette) -> str:
        return svg_defs_saas(hues=HUE_ORDER_SAAS,
                             include_gradients=True,
                             include_markers=True)

    def draw_node(self, x, y, w, h, label, palette: Palette,
                  kind: str = "chip", sublabel: str = "",
                  caption: str = "", hue: str = "cyan", **kwargs) -> str:
        pal = palette or SAAS_NIGHT
        label = _label_clip(label, 40) if label else ""
        sub = _label_clip(sublabel, 60) if sublabel else ""
        cap = _label_clip(caption, 40) if caption else ""

        if kind == "hub":
            tag = kwargs.get("tag", "")
            role = kwargs.get("role", "")
            tagline = kwargs.get("tagline", "")
            stat = kwargs.get("stat", "")
            stat_note = kwargs.get("stat_note", "")
            xl = kwargs.get("hub_xl", False)
            return hub_neon(x, y, w, h, name=label, tag=tag,
                            role=role, tagline=tagline, stat=stat,
                            stat_note=stat_note, palette=pal, hue=hue,
                            with_halo=True,
                            name_size_key="hub_name" if xl else "hub_name_em")
        elif kind == "neon_chip" or kind == "chip":
            kicker = kwargs.get("kicker", "")
            return neon_chip(x, y, w, h, label=label, sub=sub or cap,
                             kicker=kicker, palette=pal, hue=hue)
        elif kind == "cta":
            return cta_button(x, y, w, h, text=label or "Learn more",
                              hue=hue, palette=pal, with_arrow=True)
        elif kind == "stat":
            note = kwargs.get("note", "") or cap
            return stat_row_item(x, y, number=label, label=sub,
                                 note=note, hue=hue if kwargs.get("neon") else None,
                                 palette=pal)
        else:
            # default · dark rounded card
            c = _resolve_hue(hue)
            parts: List[str] = [
                _rect(x, y, w, h, fill="url(#saas-card-grad)", rx=10),
                _rect(x, y, w, h,
                      fill=_tint(c, 0.05),
                      stroke=c, sw=1.2, rx=10, opacity=0.9),
            ]
            if label:
                parts.append(_txt(x + w / 2, y + h / 2 + 4, label,
                                  size=13, family=FONT_SANS_SAAS,
                                  weight=800, fill=pal.ink, anchor="middle"))
            return "".join(parts)

    def draw_edge(self, x1, y1, x2, y2, label, palette: Palette,
                  kind: str = "rule", hue: str = "cyan", **kwargs) -> str:
        pal = palette or SAAS_NIGHT
        if kind == "edge_glow" or kind == "connector":
            with_arrow = kwargs.get("with_arrow", False)
            return edge_glow(x1, y1, x2, y2, hue=hue,
                             with_arrow=with_arrow)
        elif kind == "rule_arrow":
            c = _resolve_hue(hue)
            return _line(x1, y1, x2, y2, stroke=c, sw=1.4,
                         opacity=0.85, marker_end=f"saas-arr-{hue}")
        elif kind == "connector_dashed":
            c = _resolve_hue(hue)
            return _line(x1, y1, x2, y2, stroke=c, sw=1.2,
                         dash="4 3", opacity=0.65)
        else:  # rule · hairline
            return _line(x1, y1, x2, y2, stroke=pal.hair, sw=1.0,
                         opacity=0.7)

    def draw_container(self, x, y, w, h, label, palette: Palette,
                       kind: str = "section", hue: str = "cyan",
                       **kwargs) -> str:
        pal = palette or SAAS_NIGHT
        c = _resolve_hue(hue)
        parts: List[str] = []
        if kind == "panel":
            # dashed neon container
            parts.append(_rect(x, y, w, h,
                               fill=_tint(c, 0.04),
                               stroke=c, sw=1.1, dash="5 3",
                               rx=10, opacity=0.85))
            if label:
                parts.append(_txt(x + 12, y + 18, label,
                                  size=10, family=FONT_SANS_SAAS,
                                  weight=700, fill=c, letter_em=0.22))
        else:  # section · top/bottom rule
            parts.append(_line(x, y, x + w, y,
                               stroke=pal.hair, sw=0.8, opacity=1.0))
            parts.append(_line(x, y + h, x + w, y + h,
                               stroke=pal.hair, sw=0.8, opacity=1.0))
            if label:
                parts.append(_txt(x + w / 2, y + 6, label,
                                  size=10, family=FONT_SANS_SAAS,
                                  weight=700, fill=c, anchor="middle",
                                  letter_em=0.22))
        return "".join(parts)


SAAS_PRODUCT = SaaSProductSkin()


__all__ = [
    # Skin
    "SaaSProductSkin", "SAAS_PRODUCT",
    # Palette
    "SAAS_NIGHT",
    # Canvas (re-export)
    "CanvasProfile", "HERO_CANVAS", "EMBED_CANVAS",
    # Tokens
    "HUE_SAAS", "HUE_ORDER_SAAS", "TYPE_SCALE_SAAS",
    "FONT_SANS_SAAS", "FONT_SERIF_SAAS",
    # Primitive helpers
    "svg_defs_saas", "neon_chip", "hub_neon", "cta_button",
    "nav_bar_top", "stat_row_item", "edge_glow",
    # Chrome
    "saas_chrome", "saas_footer",
]
