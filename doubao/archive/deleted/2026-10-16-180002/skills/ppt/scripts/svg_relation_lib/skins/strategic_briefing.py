"""
Strategic Briefing skin · Dark Navy / Cream / Gold 战略简报

参照 ppi_diagram/brca1_business.png 逆向抽视觉 tokens：
    * bg=#0F1E36 深墨底 · card_bg=#F5F0E4 cream 卡片
    * primary=#C5A968 deep gold · strategic=#213858 mid navy
    * top chrome: kicker + 大 sans title + prepared-for 右对齐 + 3 KPI column
    * hub: dark rect + gold border + serif bold white name + gold tag
    * team cards: cream 底 + navy title + 左右 meta 元数据
    * so-what: 3 numeral 阶 · 大数字 + title + tagline
    * footer: bottom hairline + disclaimer 左 + CONFIDENTIAL 右

对比 editorial_atelier (bone/rust cream 报纸)：本 skin 是反色系 (dark bg)。
Canvas 结构复用 editorial_atelier.CanvasProfile · HERO 1400×820 / EMBED 900×336。

被期望的 node.kind: hub · team_card · kpi · so_what · chip
被期望的 edge.kind: rule · rule_arrow · connector · phospho_line (通用命名)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from ..engine import esc
from ..palettes import Palette
from ._base import _label_clip
from .editorial_atelier import CanvasProfile, HERO_CANVAS, EMBED_CANVAS


# ═════════════════════════════════════════════════════════════════
# Hue table · dark-bg 友好色板
# ═════════════════════════════════════════════════════════════════

HUE_SB = {
    "gold":     "#C5A968",   # 主色 · warm deep gold
    "cream":    "#F5F0E4",   # 卡片底
    "navy":     "#213858",   # 战略深靛
    "rust":     "#B85A3C",   # 关键点强调
    "teal":     "#3E7378",   # 冷色 accent
    "sage":     "#6B8E5A",   # positive
    "burgundy": "#8B3A4A",   # negative
    "slate":    "#5A6B82",   # 中性 tag
}

HUE_ORDER_SB: Tuple[str, ...] = (
    "gold", "rust", "teal", "sage", "burgundy", "slate", "navy",
)


# ─────────── Typography ───────────
FONT_SERIF_SB = "Georgia, serif"
FONT_SANS_SB = "Inter, sans-serif"

TYPE_SCALE_SB = {
    "title":          (30, FONT_SANS_SB,  800),   # hero title 大 sans bold white
    "title_embed":    (20, FONT_SANS_SB,  800),
    "kicker":         (10, FONT_SANS_SB,  700),
    "kicker_embed":   (9,  FONT_SANS_SB,  700),
    "prepared_for":   (10, FONT_SANS_SB,  500),
    "kpi_kicker":     (9,  FONT_SANS_SB,  700),
    "kpi_number":     (44, FONT_SANS_SB,  800),
    "kpi_number_em":  (26, FONT_SANS_SB,  800),   # embed
    "kpi_sub":        (10, FONT_SANS_SB,  600),
    "kpi_note":       (10, FONT_SANS_SB,  500),
    "hub_name":       (22, FONT_SERIF_SB, 800),
    "hub_tag":        (9,  FONT_SANS_SB,  700),
    "hub_kicker":     (8,  FONT_SANS_SB,  700),
    "team_title":     (13, FONT_SANS_SB,  800),
    "team_action":    (11, FONT_SANS_SB,  500),
    "team_meta":      (9,  FONT_SANS_SB,  700),
    "so_num":         (48, FONT_SERIF_SB, 800),
    "so_num_em":      (28, FONT_SERIF_SB, 800),
    "so_title":       (13, FONT_SANS_SB,  800),
    "so_tag":         (10, FONT_SANS_SB,  500),
    "section":        (10, FONT_SANS_SB,  700),
    "footer_conf":    (9,  FONT_SANS_SB,  700),
    "footer_dis":     (8,  FONT_SANS_SB,  500),
}


# ─────────── Filter defs ───────────
_FILTER_DEFS_SB = (
    '<filter id="sb-soft-shadow" x="-20%" y="-20%" width="140%" height="140%">'
    '<feGaussianBlur in="SourceAlpha" stdDeviation="2.4"/>'
    '<feOffset dx="0" dy="2"/>'
    '<feComponentTransfer><feFuncA type="linear" slope="0.42"/></feComponentTransfer>'
    '<feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge>'
    '</filter>'
    '<filter id="sb-glow" x="-40%" y="-40%" width="180%" height="180%">'
    '<feGaussianBlur in="SourceGraphic" stdDeviation="3"/>'
    '</filter>'
    '<filter id="sb-hub-halo" x="-60%" y="-60%" width="220%" height="220%">'
    '<feGaussianBlur in="SourceGraphic" stdDeviation="5"/>'
    '</filter>'
)


def _gradient_defs_sb(hues: Sequence[str]) -> str:
    """给定 hue key list · 每支 hue 生成 sb-r-<hue> linearGradient."""
    out: List[str] = []
    for name in hues:
        c = HUE_SB.get(name, HUE_SB["gold"])
        gid = f"sb-r-{name}"
        out.append(
            f'<linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="0">'
            f'<stop offset="0" stop-color="{c}" stop-opacity="0.80"/>'
            f'<stop offset="1" stop-color="{c}" stop-opacity="0.30"/>'
            f'</linearGradient>'
        )
    return "".join(out)


def _marker_defs_sb(hues: Sequence[str]) -> str:
    out: List[str] = []
    for name in hues:
        c = HUE_SB.get(name, HUE_SB["gold"])
        mid = f"sb-arr-{name}"
        out.append(
            f'<marker id="{mid}" viewBox="0 0 10 10" refX="9" refY="5" '
            f'markerWidth="7" markerHeight="7" orient="auto">'
            f'<path d="M 0 0 L 9 5 L 0 10 Z" fill="{c}"/></marker>'
        )
    return "".join(out)


# ═════════════════════════════════════════════════════════════════
# Palette · STRATEGIC_NAVY
# ═════════════════════════════════════════════════════════════════

STRATEGIC_NAVY = Palette(
    name="Strategic Navy · Briefing",
    bg="#0F1E36",              # deep navy 底
    bg_alt="#213858",          # mid navy · hub / accent block
    bg_dim="#1A2B47",          # 三级 深靛
    ink="#F5F0E4",             # cream · 主文字 on dark
    gray="rgba(245,240,228,0.62)",  # 二级 cream 淡
    hair="rgba(245,240,228,0.22)",  # 分隔线 cream 淡
    primary="#C5A968",         # deep gold
    primary_dim="#8F7A45",     # gold 暗
    accent="#F5F0E4",          # cream 亮
    accent_dim="#B85A3C",      # rust warm
    positive="#6B8E5A",        # sage
    negative="#8B3A4A",        # burgundy
    head_family=FONT_SANS_SB,
    body_family=FONT_SANS_SB,
    mono_family=FONT_SANS_SB,
    kicker_letter_spacing=2.6,
    kicker_case="upper",
    section_numbering="arabic",
    folio_style="hairline",
    title_style="sans_bold",
    subtitle_style="sans_italic",
    figure_caption_prefix="EXHIBIT",
    signature_note="STRATEGIC BRIEFING · CONFIDENTIAL",
)


# ═════════════════════════════════════════════════════════════════
# 低层 SVG helper (dark bg 版本 · 与 editorial_atelier 独立)
# ═════════════════════════════════════════════════════════════════

def _txt(x, y, s, *, size, family, weight=500, fill="#F5F0E4",
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


def _line(x1, y1, x2, y2, *, stroke: str = "#F5F0E4", sw: float = 1.0,
          opacity: Optional[float] = None, dash: Optional[str] = None,
          linecap: Optional[str] = None,
          marker_end: Optional[str] = None) -> str:
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
    return f'<line {" ".join(parts)}/>'


def _tint(hex_hue: str, alpha: float) -> str:
    h = hex_hue.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha:.3f})"


def _resolve_hue(hue_key_or_hex: str) -> str:
    if not hue_key_or_hex:
        return HUE_SB["gold"]
    if hue_key_or_hex.startswith("#"):
        return hue_key_or_hex
    return HUE_SB.get(hue_key_or_hex, HUE_SB["gold"])


# ═════════════════════════════════════════════════════════════════
# Primitive helpers · module-level (preset 直接 import 用)
# ═════════════════════════════════════════════════════════════════

def svg_defs_sb(hues: Sequence[str] = HUE_ORDER_SB,
                include_markers: bool = True,
                include_gradients: bool = True) -> str:
    """一次注入 3 filter + hue gradient + hue marker · <defs> 段.

    preset 在渲染前置调用 · 生成的字符串直接拼进 SVG 头.
    """
    inner = _FILTER_DEFS_SB
    if include_gradients:
        inner += _gradient_defs_sb(hues)
    if include_markers:
        inner += _marker_defs_sb(hues)
    return f"<defs>{inner}</defs>"


def kpi_column(x: float, y: float, w: float, h: float, *,
               kicker: str = "",
               big_number: str = "",
               sub_note: str = "",
               subtitle: str = "",
               hue: str = "gold",
               palette: Palette = STRATEGIC_NAVY,
               canvas: CanvasProfile = HERO_CANVAS) -> str:
    """brca1_business.png 顶部大 KPI · kicker + 巨号 + sub + note.

    Layout:
        kicker (small gold caps)    y = y + 14
        big_number (44pt white)     y = y + 50  · gold underline decorator
        sub_note (10pt gold)        y = y + 78  · 右侧 inline 说明
        subtitle body (10pt cream)  y = y + 100
    """
    is_embed = (canvas.w == 900 and canvas.h == 336)
    parts: List[str] = []
    c = _resolve_hue(hue)
    kicker_key = "kpi_kicker" if not is_embed else "kicker_embed"
    number_key = "kpi_number" if not is_embed else "kpi_number_em"
    ksz, kfam, kwt = TYPE_SCALE_SB[kicker_key]
    nsz, nfam, nwt = TYPE_SCALE_SB[number_key]
    ssz, sfam, swt = TYPE_SCALE_SB["kpi_sub"]
    tsz, tfam, twt = TYPE_SCALE_SB["kpi_note"]
    # kicker
    if kicker:
        parts.append(_txt(x, y + (ksz + 4), kicker.upper(),
                          size=ksz, family=kfam, weight=kwt,
                          fill=c, letter_em=0.20))
    # gold underline hair (kicker 下 4px)
    parts.append(_line(x, y + ksz + 10, x + 42, y + ksz + 10,
                       stroke=c, sw=1.5, opacity=0.85))
    # big number
    if big_number:
        num_y = y + (48 if not is_embed else 34)
        parts.append(_txt(x, num_y, big_number,
                          size=nsz, family=nfam, weight=nwt,
                          fill=palette.accent, letter_em=-0.01))
    # inline sub_note (紧跟 big_number 右侧 · 更小字)
    if sub_note:
        note_y = y + (52 if not is_embed else 36)
        # 简单估算 big_number 宽度 · 用字符数 * nsz * 0.55
        est_w = len(big_number) * nsz * 0.55 + 8
        parts.append(_txt(x + est_w, note_y, sub_note,
                          size=ssz, family=sfam, weight=swt,
                          fill=c))
    # subtitle body
    if subtitle:
        sub_y = y + (h - 8 if h > 60 else h - 4)
        parts.append(_txt(x, sub_y, subtitle,
                          size=tsz, family=tfam, weight=twt,
                          fill=palette.ink, opacity=0.86))
    return "".join(parts)


def hub_dark(x: float, y: float, w: float, h: float, *,
             name: str = "",
             tag: str = "",
             kicker: str = "",
             tagline: str = "",
             palette: Palette = STRATEGIC_NAVY,
             hue: str = "gold",
             with_halo: bool = True) -> str:
    """深底 hub 带 gold 边 · serif bold white name + gold tag chip 顶.

    Layout:
        halo (soft gold glow · optional)
        rect fill=navy_alt · stroke=gold 2.4 · rx=6
        tag chip (顶部 kicker)   y = y + 20
        name (serif bold white)  y = y + 50
        tagline (sans 10 cream)  y = y + 74
    """
    c = _resolve_hue(hue)
    parts: List[str] = []
    if with_halo:
        halo_pad = 10
        parts.append(_rect(x - halo_pad, y - halo_pad,
                           w + halo_pad * 2, h + halo_pad * 2,
                           fill=None, stroke=c, sw=2.0, rx=8,
                           opacity=0.45, filter_id="sb-hub-halo"))
    # 深底 rect (soft shadow)
    parts.append(_rect(x, y, w, h, fill=palette.bg_alt, rx=6,
                       filter_id="sb-soft-shadow"))
    # gold border
    parts.append(_rect(x, y, w, h, fill=None, stroke=c, sw=2.4, rx=6))

    cx = x + w / 2
    # kicker at top
    if kicker:
        ksz, kfam, kwt = TYPE_SCALE_SB["hub_kicker"]
        parts.append(_txt(cx, y + 16, kicker.upper(),
                          size=ksz, family=kfam, weight=kwt,
                          fill=c, anchor="middle", letter_em=0.24))
    # name (center · 略靠上让出 tag 位)
    if name:
        nsz, nfam, nwt = TYPE_SCALE_SB["hub_name"]
        parts.append(_txt(cx, y + h * 0.48, name,
                          size=nsz, family=nfam, weight=nwt,
                          fill=palette.accent, anchor="middle"))
    # divider
    parts.append(_line(x + 16, y + h * 0.58, x + w - 16, y + h * 0.58,
                       stroke=c, sw=0.8, opacity=0.55))
    # tagline (紧接 divider 下)
    if tagline:
        parts.append(_txt(cx, y + h * 0.72, tagline,
                          size=10, family=FONT_SANS_SB, weight=500,
                          fill=_tint(HUE_SB["cream"], 0.85), anchor="middle"))
    # tag chip (底部 · 与 tagline 分开)
    if tag:
        tsz, tfam, twt = TYPE_SCALE_SB["hub_tag"]
        chip_w = max(6.6 * len(tag) + 14, 60)
        chip_x = cx - chip_w / 2
        chip_y = y + h - 20
        parts.append(_rect(chip_x, chip_y, chip_w, 14,
                           fill=_tint(c, 0.18), stroke=c, sw=0.8, rx=7))
        parts.append(_txt(cx, chip_y + 10.5, tag.upper(),
                          size=tsz, family=tfam, weight=twt,
                          fill=palette.accent, anchor="middle", letter_em=0.18))
    return "".join(parts)


def team_card(x: float, y: float, w: float, h: float, *,
              title: str = "",
              action: str = "",
              meta_left: str = "",
              meta_right: str = "",
              hue: str = "gold",
              palette: Palette = STRATEGIC_NAVY,
              variant: str = "default") -> str:
    """cream 卡片 + navy title + action body + 双侧 meta 元数据.

    Layout (h ≥ 64 推荐 · 3 层布局):
        title (bold navy) + meta_right (gold caps · 右)     y = y + 22
        in-card hairline                                     y = y + 32
        action (500 navy)                                    y = y + 48
        meta_left (small caps · 灰 navy)                     y = y + h - 10

    variant="default"   : 3 层
    variant="alert"     : 加 rust 左边 4px 强调条 (critical / warning)
    """
    c = _resolve_hue(hue)
    parts: List[str] = []
    # cream 底 + soft shadow
    parts.append(_rect(x, y, w, h, fill=palette.ink, rx=4,
                       filter_id="sb-soft-shadow"))
    # gold 顶边 hair
    parts.append(_rect(x, y, w, 3, fill=c, rx=0))
    # left accent bar for alert variant
    if variant == "alert":
        parts.append(_rect(x, y, 4, h, fill=HUE_SB["rust"]))
    # title
    if title:
        tsz, tfam, twt = TYPE_SCALE_SB["team_title"]
        parts.append(_txt(x + 14, y + 22, title,
                          size=tsz, family=tfam, weight=twt,
                          fill=HUE_SB["navy"]))
    # right meta (顶右 · tag)
    if meta_right:
        msz, mfam, mwt = TYPE_SCALE_SB["team_meta"]
        parts.append(_txt(x + w - 14, y + 22, meta_right.upper(),
                          size=msz, family=mfam, weight=mwt,
                          fill=c, anchor="end", letter_em=0.18))
    # in-card hairline
    parts.append(_line(x + 14, y + 32, x + w - 14, y + 32,
                       stroke=_tint(HUE_SB["navy"], 0.28), sw=0.7))
    # action body (给 meta_left 留出底部 14px)
    if action:
        asz, afam, awt = TYPE_SCALE_SB["team_action"]
        # 若有 meta_left 则 action 上移 · 否则居中于 hairline 下方
        action_y = y + 48 if meta_left else y + h - 14
        parts.append(_txt(x + 14, action_y, action,
                          size=asz, family=afam, weight=awt,
                          fill=_tint(HUE_SB["navy"], 0.85)))
    # meta_left (bottom · 与 action 至少间隔 12px)
    if meta_left:
        msz, mfam, mwt = TYPE_SCALE_SB["team_meta"]
        parts.append(_txt(x + 14, y + h - 10, meta_left.upper(),
                          size=msz, family=mfam, weight=mwt,
                          fill=_tint(HUE_SB["navy"], 0.62), letter_em=0.14))
    return "".join(parts)


def so_what_item(x: float, y: float, w: float, h: float, *,
                 number: str = "",
                 title: str = "",
                 tagline: str = "",
                 palette: Palette = STRATEGIC_NAVY,
                 hue: str = "gold",
                 canvas: CanvasProfile = HERO_CANVAS) -> str:
    """底部 so-what 3 阶 · 大 numeral (navy) + title (cream) + tagline (gray).

    Layout: 左侧巨号 numeral · 右侧 title/tagline 叠 2 行.
        灰底 subtle rect (bg_dim 上) 作为容器 · dark navy numeral · gold hair.
    """
    is_embed = (canvas.w == 900 and canvas.h == 336)
    c = _resolve_hue(hue)
    parts: List[str] = []
    # 灰底容器 (dim navy)
    parts.append(_rect(x, y, w, h, fill=palette.bg_dim, rx=4))
    # 顶部 gold hair
    parts.append(_line(x, y, x + w, y, stroke=c, sw=1.4, opacity=0.9))
    # numeral
    num_key = "so_num" if not is_embed else "so_num_em"
    nsz, nfam, nwt = TYPE_SCALE_SB[num_key]
    if number:
        parts.append(_txt(x + 16, y + h * 0.70, number,
                          size=nsz, family=nfam, weight=nwt,
                          fill=c))
    # title
    if title:
        tsz, tfam, twt = TYPE_SCALE_SB["so_title"]
        text_x = x + 16 + (nsz * 0.75)
        parts.append(_txt(text_x, y + h * 0.42, title,
                          size=tsz, family=tfam, weight=twt,
                          fill=palette.accent))
    # tagline
    if tagline:
        gsz, gfam, gwt = TYPE_SCALE_SB["so_tag"]
        text_x = x + 16 + (nsz * 0.75)
        parts.append(_txt(text_x, y + h * 0.72, tagline,
                          size=gsz, family=gfam, weight=gwt,
                          fill=_tint(HUE_SB["cream"], 0.80)))
    return "".join(parts)


def nav_bar_top(x: float, y: float, w: float, *,
                right_text: str = "",
                palette: Palette = STRATEGIC_NAVY) -> str:
    """顶部小条 · 右对齐 'Prepared for: ...' · gold hair 装饰."""
    parts: List[str] = []
    if right_text:
        psz, pfam, pwt = TYPE_SCALE_SB["prepared_for"]
        parts.append(_txt(x + w, y, right_text,
                          size=psz, family=pfam, weight=pwt,
                          fill=_tint(HUE_SB["cream"], 0.72), anchor="end"))
    return "".join(parts)


def chip_tag_dark(x: float, y: float, w: float, h: float, *,
                  label: str = "",
                  palette: Palette = STRATEGIC_NAVY,
                  hue: str = "gold") -> str:
    """dark bg 上的 pill chip · gold stroke + cream label."""
    c = _resolve_hue(hue)
    parts: List[str] = [
        _rect(x, y, w, h, fill=_tint(c, 0.18), stroke=c, sw=1.0, rx=h / 2),
    ]
    if label:
        parts.append(_txt(x + w / 2, y + h / 2 + 3.5, label,
                          size=10, family=FONT_SANS_SB, weight=700,
                          fill=palette.accent, anchor="middle"))
    return "".join(parts)


# ═════════════════════════════════════════════════════════════════
# Chrome · sb_chrome / sb_footer
# ═════════════════════════════════════════════════════════════════

def sb_chrome(*, kicker: str = "",
              title: str = "",
              prepared_for: str = "",
              kpi_columns: Optional[Sequence[dict]] = None,
              palette: Palette = STRATEGIC_NAVY,
              canvas: CanvasProfile = HERO_CANVAS) -> str:
    """顶部 chrome · dark bg + kicker + big title + prepared-for + 3 KPI zone.

    kpi_columns: list of dicts · 每 dict 有 kicker/big_number/sub_note/subtitle/hue.
                 长度通常 3 · 均分 hero 有效宽度.
    """
    is_embed = (canvas.w == 900 and canvas.h == 336)
    parts: List[str] = []
    # dark bg
    parts.append(_rect(0, 0, canvas.w, canvas.h, fill=palette.bg))
    # kicker
    if kicker:
        ksz, kfam, kwt = TYPE_SCALE_SB[
            "kicker" if not is_embed else "kicker_embed"]
        parts.append(_txt(canvas.margin_x, canvas.title_y - 22, kicker.upper(),
                          size=ksz, family=kfam, weight=kwt,
                          fill=palette.primary, letter_em=0.22))
    # title
    if title:
        title_key = "title" if not is_embed else "title_embed"
        tsz, tfam, twt = TYPE_SCALE_SB[title_key]
        parts.append(_txt(canvas.margin_x, canvas.title_y + 4, title,
                          size=tsz, family=tfam, weight=twt,
                          fill=palette.accent, letter_em=-0.005))
    # prepared_for right
    if prepared_for:
        psz, pfam, pwt = TYPE_SCALE_SB["prepared_for"]
        parts.append(_txt(canvas.w - canvas.margin_x, canvas.title_y - 8,
                          prepared_for,
                          size=psz, family=pfam, weight=pwt,
                          fill=_tint(HUE_SB["cream"], 0.72), anchor="end"))
    # title hairline (gold)
    parts.append(_line(canvas.margin_x, canvas.title_hair_y,
                       canvas.w - canvas.margin_x, canvas.title_hair_y,
                       stroke=palette.primary, sw=0.6, opacity=0.55))
    # KPI columns
    if kpi_columns:
        n = len(kpi_columns)
        avail_w = canvas.w - canvas.margin_x * 2
        col_w = avail_w / n
        # KPI zone y 起点在 title_hair_y 下方
        kpi_y = canvas.title_hair_y + 14
        # KPI zone 高度 · 大约 100px hero / 60px embed
        kpi_h = 100 if not is_embed else 60
        for i, col in enumerate(kpi_columns):
            cx = canvas.margin_x + i * col_w
            parts.append(kpi_column(
                cx, kpi_y, col_w - 12, kpi_h,
                kicker=col.get("kicker", ""),
                big_number=col.get("big_number", ""),
                sub_note=col.get("sub_note", ""),
                subtitle=col.get("subtitle", ""),
                hue=col.get("hue", "gold"),
                palette=palette,
                canvas=canvas,
            ))
        # KPI 底部 hairline
        hair_y = kpi_y + kpi_h + 8
        parts.append(_line(canvas.margin_x, hair_y,
                           canvas.w - canvas.margin_x, hair_y,
                           stroke=palette.hair, sw=0.6, opacity=0.28))
    return "".join(parts)


def sb_footer(*, disclaimer: str = "",
              confidential: str = "CONFIDENTIAL",
              palette: Palette = STRATEGIC_NAVY,
              canvas: CanvasProfile = HERO_CANVAS) -> str:
    """底部 · hairline + 灰 disclaimer 左 + CONFIDENTIAL 右下角 gold caps."""
    parts: List[str] = []
    # bottom hairline
    parts.append(_line(canvas.margin_x, canvas.bottom_hair_y,
                       canvas.w - canvas.margin_x, canvas.bottom_hair_y,
                       stroke=palette.hair, sw=0.6, opacity=0.28))
    # disclaimer (左 · 灰淡 italic)
    if disclaimer:
        dsz, dfam, dwt = TYPE_SCALE_SB["footer_dis"]
        parts.append(_txt(canvas.margin_x, canvas.source_y, disclaimer,
                          size=dsz, family=dfam, weight=dwt,
                          fill=_tint(HUE_SB["cream"], 0.42), italic=True))
    # confidential (右 · gold caps)
    if confidential:
        csz, cfam, cwt = TYPE_SCALE_SB["footer_conf"]
        parts.append(_txt(canvas.w - canvas.margin_x, canvas.source_y,
                          confidential.upper(),
                          size=csz, family=cfam, weight=cwt,
                          fill=palette.primary, anchor="end", letter_em=0.24))
    return "".join(parts)


# ═════════════════════════════════════════════════════════════════
# Skin 协议实现
# ═════════════════════════════════════════════════════════════════

class StrategicBriefingSkin:
    """Strategic Briefing · Dark navy / cream / gold 战略简报 skin."""

    name = "strategic_briefing"

    # ── defs ──
    def defs(self, palette: Palette) -> str:
        return svg_defs_sb(hues=HUE_ORDER_SB, include_gradients=True,
                           include_markers=True)

    # ── node ──
    def draw_node(self, x, y, w, h, label, palette: Palette,
                  kind: str = "team_card",
                  sublabel: str = "", caption: str = "",
                  hue: str = "gold", **kwargs) -> str:
        pal = palette or STRATEGIC_NAVY
        label = _label_clip(label, 44) if label else ""
        sub = _label_clip(sublabel, 70) if sublabel else ""
        cap = _label_clip(caption, 44) if caption else ""

        if kind == "hub":
            tag = kwargs.get("tag", "")
            kicker = kwargs.get("kicker", "")
            tagline = kwargs.get("tagline", sub)
            return hub_dark(x, y, w, h, name=label, tag=tag,
                            kicker=kicker, tagline=tagline,
                            palette=pal, hue=hue, with_halo=True)
        elif kind == "kpi":
            big = kwargs.get("big_number", sub)
            note = kwargs.get("sub_note", "")
            subtitle = kwargs.get("subtitle", cap)
            return kpi_column(x, y, w, h, kicker=label,
                              big_number=big, sub_note=note,
                              subtitle=subtitle, hue=hue, palette=pal)
        elif kind == "so_what":
            num = kwargs.get("number", "")
            tag = kwargs.get("tagline", cap)
            return so_what_item(x, y, w, h, number=num, title=label,
                                tagline=tag, palette=pal, hue=hue)
        elif kind == "chip":
            return chip_tag_dark(x, y, w, h, label=label, palette=pal, hue=hue)
        else:  # team_card default
            action = kwargs.get("action", sub)
            meta_left = kwargs.get("meta_left", cap)
            meta_right = kwargs.get("meta_right", "")
            variant = kwargs.get("variant", "default")
            return team_card(x, y, w, h, title=label, action=action,
                             meta_left=meta_left, meta_right=meta_right,
                             hue=hue, palette=pal, variant=variant)

    # ── edge ──
    def draw_edge(self, x1, y1, x2, y2, label, palette: Palette,
                  kind: str = "rule",
                  hue: str = "gold", **kwargs) -> str:
        pal = palette or STRATEGIC_NAVY
        c = _resolve_hue(hue)
        if kind == "connector":
            return _line(x1, y1, x2, y2, stroke=c, sw=1.2, dash="4 3",
                         opacity=0.65)
        elif kind == "rule_arrow":
            return _line(x1, y1, x2, y2, stroke=c, sw=1.5, opacity=0.82,
                         marker_end=f"sb-arr-{hue}")
        elif kind == "phospho_line":
            return _line(x1, y1, x2, y2, stroke=c, sw=1.9, opacity=0.88,
                         linecap="round", marker_end=f"sb-arr-{hue}")
        else:  # rule · hairline
            return _line(x1, y1, x2, y2, stroke=pal.hair, sw=1.0,
                         opacity=0.55)

    # ── container ──
    def draw_container(self, x, y, w, h, label, palette: Palette,
                       kind: str = "section", hue: str = "gold",
                       **kwargs) -> str:
        pal = palette or STRATEGIC_NAVY
        c = _resolve_hue(hue)
        parts: List[str] = []
        if kind == "team_zone":
            # 3 team card 容器 · dashed gold border · dim navy 底
            parts.append(_rect(x, y, w, h, fill=pal.bg_dim,
                               stroke=c, sw=1.0, dash="5 4",
                               rx=6, opacity=0.85))
            if label:
                parts.append(_txt(x + 12, y + 16, label.upper(),
                                  size=10, family=FONT_SANS_SB, weight=700,
                                  fill=c, letter_em=0.22))
        elif kind == "kpi_zone":
            # KPI 大区 · 上下 gold hair · 内容由 kpi_column 填
            parts.append(_line(x, y, x + w, y, stroke=c, sw=1.0, opacity=0.85))
            parts.append(_line(x, y + h, x + w, y + h,
                               stroke=pal.hair, sw=0.6, opacity=0.32))
            if label:
                parts.append(_txt(x, y - 6, label.upper(),
                                  size=9, family=FONT_SANS_SB, weight=700,
                                  fill=c, letter_em=0.22))
        else:  # section · legacy 顶底 rule + kicker
            parts.append(_line(x, y, x + w, y, stroke=c, sw=1.2))
            parts.append(_line(x, y + h, x + w, y + h,
                               stroke=pal.hair, sw=0.6, opacity=0.32))
            if label:
                parts.append(_txt(x, y - 6, label.upper(),
                                  size=10, family=FONT_SANS_SB, weight=700,
                                  fill=c, letter_em=0.22))
        return "".join(parts)


STRATEGIC_BRIEFING = StrategicBriefingSkin()


__all__ = [
    # Skin
    "StrategicBriefingSkin", "STRATEGIC_BRIEFING",
    # Palette
    "STRATEGIC_NAVY",
    # Canvas (re-export for preset convenience)
    "CanvasProfile", "HERO_CANVAS", "EMBED_CANVAS",
    # Tokens
    "HUE_SB", "HUE_ORDER_SB", "TYPE_SCALE_SB", "FONT_SERIF_SB", "FONT_SANS_SB",
    # Primitives
    "svg_defs_sb", "kpi_column", "hub_dark", "team_card",
    "so_what_item", "nav_bar_top", "chip_tag_dark",
    # Chrome
    "sb_chrome", "sb_footer",
]
