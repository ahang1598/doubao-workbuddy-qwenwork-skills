"""
K9 · editorial_atelier skin · Bone/Rust 编辑排印

按 4 张标杆图（mindmap_ml_4layer · mindmap_taxonomy_6layer ·
mindmap_system_design · p53_interactome）逆向抽出的 design tokens 建立。
细节见 skins/editorial_atelier_tokens.md。

视觉核心：
    * bg=#F1E9DA 报纸米 · ink=#1C1914 深墨 · primary=#A35832 rust
    * Georgia serif × Inter sans 二元字体
    * hub_double / card_double / chip_pill / ribbon_gradient primitive
    * 3 filter (soft-shadow / hub-shadow / hub-halo) + N gradient + N marker

被期望 node.kind：
    hub · paradigm_block · card · chip · kinase_chip · sibling_chip
    milestone_card · downstream_group · task_card · header_card
被期望 edge.kind：
    connector_dashed · phospho_line · rule · rule_arrow

Ribbon / feedback_arc / phospho_disc / halo_wrap / hero_chrome /
hero_footer 是 module-level helper（不在 skin 协议内，直接 import 用），
因为它们的几何不适合 draw_edge/draw_node 契约（多锚点 or 非几何形状）。

canvas 契约（skin 不假设，preset 传坐标）：
    HERO_CANVAS = 1400 × 820
    EMBED_CANVAS = 900 × 336 (legacy)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from ..engine import text, rect, line, path, circle, polygon, esc
from ..palettes import Palette
from ._base import _label_clip, _wrap_lines, _text_multiline_svg, _fit_font_size


# ═════════════════════════════════════════════════════════════════
# Design Tokens · 从 4 张标杆 SVG 逆向落库 (tokens.md §2/§3/§7/§8)
# ═════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class CanvasProfile:
    w: int
    h: int
    margin_x: int
    title_y: int
    subtitle_y: int
    title_hair_y: int
    section_hdr_y: int
    body_y0: int
    body_y1: int
    bottom_hair_y: int
    read_kicker_y: int
    read_body_y0: int
    read_body_lh: int      # line height 每行 y 增量
    source_y: int


HERO_CANVAS = CanvasProfile(
    w=1400, h=820, margin_x=55,
    title_y=46, subtitle_y=70, title_hair_y=92,
    section_hdr_y=115, body_y0=128, body_y1=700,
    bottom_hair_y=722, read_kicker_y=744,
    read_body_y0=763, read_body_lh=19,
    source_y=803,
)

# Embed 900×300 profile — 收紧左右+底部无用留白 (hero_footer 早已关闭)
EMBED_CANVAS = CanvasProfile(
    w=900, h=300, margin_x=12,
    title_y=22, subtitle_y=40, title_hair_y=54,
    section_hdr_y=70, body_y0=70, body_y1=290,
    bottom_hair_y=294, read_kicker_y=296,
    read_body_y0=298, read_body_lh=10,
    source_y=298,
)

# TX_CANVAS · 1400×800 · 用于 hub + radial 布局 (n≥5 slot 需要更多空间)
TX_CANVAS = CanvasProfile(
    w=1400, h=800, margin_x=40,
    title_y=30, subtitle_y=52, title_hair_y=66,
    section_hdr_y=80, body_y0=82, body_y1=770,
    bottom_hair_y=776, read_kicker_y=782,
    read_body_y0=790, read_body_lh=12,
    source_y=796,
)


# ─────────── 元素尺寸 profile · hero vs embed ───────────
# 元素尺寸 (width, height, gap_x, gap_y) · rx=height/2 for pill
# 字号在 TYPE_SCALE 里已定义 · profile 只管几何尺寸

@dataclass(frozen=True)
class ElementProfile:
    """元素几何尺寸 profile · 让 preset 从统一入口取 chip/card/hub 尺寸."""
    # chip pill
    chip_w: float
    chip_h: float
    chip_gap_x: float
    # card (三级 · 标题+desc)
    card_w: float
    card_h: float
    card_gap_x: float
    # hub (中心)
    hub_w: float
    hub_h: float
    hub_halo_pad: float
    # block (paradigm/kingdom-level · L2)
    block_w: float
    block_h: float
    # 字号缩放系数 (embed 相对 hero)
    font_scale: float


HERO_PROFILE = ElementProfile(
    chip_w=118, chip_h=28, chip_gap_x=9,
    card_w=220, card_h=48, card_gap_x=10,
    hub_w=200, hub_h=115, hub_halo_pad=10,
    block_w=145, block_h=130,
    font_scale=1.0,
)

# embed 900×336 · body 高 198 · 6 行 × 32px 高卡 是上限
# chip 缩到 88×22 rx=11 · 字号缩到 9-10pt (跟 hero 相比 chip label 从 11→10)
EMBED_PROFILE = ElementProfile(
    chip_w=88, chip_h=22, chip_gap_x=6,
    card_w=160, card_h=36, card_gap_x=6,
    hub_w=130, hub_h=90, hub_halo_pad=6,
    block_w=110, block_h=90,
    font_scale=0.82,
)


def profile_for(canvas: CanvasProfile) -> ElementProfile:
    """按 canvas 返回元素 profile · 目前 900×300/336 → embed / 其他 → hero."""
    if canvas.w == 900 and canvas.h in (300, 336):
        return EMBED_PROFILE
    return HERO_PROFILE


# ─────────── Hue table (tokens.md §3) ───────────
# category hue 池 · preset 按需从中挑 4-6 支
HUE = {
    "rust":     "#A35832",   # 主色
    "orange":   "#C87F3D",
    "magenta":  "#A63C6E",
    "blue":     "#3F6892",
    "green":    "#558045",
    "olive":    "#7A6A3A",
    "cinnamon": "#8B5A3C",
    "gold_p":   "#D9A448",   # p53 phospho disc
    "slate":    "#3F5C7A",   # atelier slate · 偏冷灰蓝 · 与 blue 邻近但更深偏灰
}

HUE_ORDER: Tuple[str, ...] = (
    "rust", "orange", "magenta", "blue", "green", "olive", "cinnamon",
)


# ─────────── Typography (tokens.md §7) ───────────
FONT_SERIF = "Georgia, serif"
FONT_SANS = "Inter, sans-serif"

TYPE_SCALE = {
    "title":         (26, FONT_SERIF, 700),
    "subtitle":      (13, FONT_SANS,  500),
    "section":       (10, FONT_SANS,  700),
    "column_header": (10, FONT_SANS,  700),
    "hub_name":      (19, FONT_SERIF, 800),   # 标杆 18-19 · 取 19
    "hub_name_xl":   (26, FONT_SERIF, 800),   # p53 巨号
    "block_title":   (17, FONT_SERIF, 700),
    "card_title":    (13, FONT_SANS,  800),
    "chip_kinase":   (14, FONT_SANS,  800),   # p53 kinase 用大一点
    "chip_label":    (11, FONT_SANS,  700),
    "body_desc":     (10, FONT_SANS,  500),   # card 说明
    "micro_numeric": (10, FONT_SERIF, 700),   # 数字/italic caption
    "footer_read":   (12, FONT_SANS,  500),
    "footer_italic": (11, FONT_SANS,  500),
    "kicker_mini":   (9,  FONT_SANS,  700),
    "source_tag":    (10, FONT_SANS,  700),
}


# ─────────── Filter / gradient / marker (tokens.md §4/§5/§6) ───────────

_FILTER_DEFS = """<filter id="ea-soft-shadow" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur in="SourceAlpha" stdDeviation="2"/><feOffset dx="0" dy="1.5"/><feComponentTransfer><feFuncA type="linear" slope="0.28"/></feComponentTransfer><feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge></filter><filter id="ea-hub-shadow" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur in="SourceAlpha" stdDeviation="3.5"/><feOffset dx="0" dy="2.5"/><feComponentTransfer><feFuncA type="linear" slope="0.35"/></feComponentTransfer><feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge></filter><filter id="ea-hub-halo" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur in="SourceGraphic" stdDeviation="5.5"/></filter>"""


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
        'stroke="rgba(94,80,62,0.85)" stroke-width="2.6"/></marker>'
    )
    return "".join(out)


# ═════════════════════════════════════════════════════════════════
# Palette · BONE_RUST (tokens.md §14)
# ═════════════════════════════════════════════════════════════════

BONE_RUST = Palette(
    name="Bone Rust · Editorial Atelier",
    bg="#F1E9DA",
    bg_alt="#EFE4CE",
    bg_dim="#E4D7BA",
    ink="#1C1914",
    gray="rgba(94,80,62,0.72)",
    hair="#1C1914",                # opacity 靠属性叠加 (0.22 by usage)
    primary=HUE["rust"],
    primary_dim=HUE["orange"],
    accent=HUE["gold_p"],
    accent_dim=HUE["magenta"],
    positive=HUE["green"],
    negative=HUE["magenta"],
    head_family=FONT_SERIF,
    body_family=FONT_SANS,
    mono_family=FONT_SANS,
    kicker_letter_spacing=2.8,
    kicker_case="upper",
    section_numbering="arabic",
    folio_style="hairline",
    title_style="serif_bold",
    subtitle_style="sans_italic",
    figure_caption_prefix="FIGURE",
    signature_note="EDITORIAL ATELIER · BONE RUST",
)


# ═════════════════════════════════════════════════════════════════
# 底层 SVG 拼装辅助 (engine 未暴露的字段用裸字符串)
# ═════════════════════════════════════════════════════════════════

def _txt(x, y, s, *, size, family, weight=500, fill="#1C1914",
         anchor="start", italic=False, letter_em: Optional[float] = None,
         opacity: Optional[float] = None) -> str:
    """比 engine.text 更贴 tokens 的 text · 支持 letter-spacing em / opacity。"""
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


def _line(x1, y1, x2, y2, *, stroke: str = "#1C1914", sw: float = 1.0,
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
    """把 #RRGGBB 加上 alpha · 返回 rgba() 字符串。"""
    h = hex_hue.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha:.3f})"


def _resolve_hue(hue_key_or_hex: str) -> str:
    """接受 'rust' / 'orange' 或直接 hex · 返回 hex 字符串。"""
    if not hue_key_or_hex:
        return HUE["rust"]
    if hue_key_or_hex.startswith("#"):
        return hue_key_or_hex
    return HUE.get(hue_key_or_hex, HUE["rust"])


# ═════════════════════════════════════════════════════════════════
# Primitive helpers (module-level · preset 直接 import)
# ═════════════════════════════════════════════════════════════════

def svg_defs(hues: Sequence[str] = HUE_ORDER,
             include_markers: bool = True,
             include_gradients: bool = True) -> str:
    """一次注入 3 filter + hue gradient + hue marker · <defs> 段。

    preset 在渲染前置调用 · 生成的字符串直接拼进 SVG 头。
    """
    inner = _FILTER_DEFS
    if include_gradients:
        inner += _gradient_defs(hues)
    if include_markers:
        inner += _marker_defs(hues)
    return f"<defs>{inner}</defs>"


def hub_frame(x: float, y: float, w: float, h: float, *,
              palette: Palette = BONE_RUST,
              hue: str = "rust",
              with_halo: bool = True,
              rx: float = 10.0,
              halo_rx: float = 14.0,
              halo_pad: float = 10.0,
              halo_sw: float = 2.2,
              halo_opacity: float = 0.5,
              tint_alpha: float = 0.24,
              stroke_sw: float = 2.4) -> str:
    """只画 hub 外框 · halo + cream 底 + tint 覆盖 · 内容由 preset 自绘。

    用于 preset 需要精确定制内容布局的场景（4 张标杆里的 hub 内容布局各不相同）。
    """
    c = _resolve_hue(hue)
    parts: List[str] = []
    if with_halo:
        parts.append(_rect(
            x - halo_pad, y - halo_pad,
            w + halo_pad * 2, h + halo_pad * 2,
            fill=None, stroke=c, sw=halo_sw, rx=halo_rx,
            opacity=halo_opacity, filter_id="ea-hub-halo",
        ))
    parts.append(_rect(x, y, w, h, fill=palette.bg, rx=rx,
                       filter_id="ea-hub-shadow"))
    parts.append(_rect(x, y, w, h,
                       fill=_tint(c, tint_alpha),
                       stroke=c, sw=stroke_sw, rx=rx))
    return "".join(parts)


def hub_double(x: float, y: float, w: float, h: float, *,
               name: str = "",
               role: str = "",
               tagline: str = "",
               stat: str = "",
               stat_note: str = "",
               palette: Palette = BONE_RUST,
               hue: str = "rust",
               with_halo: bool = True,
               name_size_key: str = "hub_name") -> str:
    """标杆同款 hub · halo (外光晕) + cream 底 + tint 覆盖 + 内文 4 行。

    Layout (基础 200×115 · 按传入 w/h 缩放)：
        name (serif 19-26)          y = y + 32
        role kicker (sans 10)       y = y + 51
        divider hairline            y = y + 62
        tagline (serif italic 12)   y = y + 82
        stat (serif 15) + note      y = y + 103
    """
    c = _resolve_hue(hue)
    parts: List[str] = []
    # 外 halo
    if with_halo:
        halo_pad = 10
        parts.append(_rect(
            x - halo_pad, y - halo_pad,
            w + halo_pad * 2, h + halo_pad * 2,
            fill=None, stroke=c, sw=2.2, rx=14, opacity=0.5,
            filter_id="ea-hub-halo",
        ))
    # cream 底 (带 shadow)
    parts.append(_rect(x, y, w, h, fill=palette.bg, rx=10,
                       filter_id="ea-hub-shadow"))
    # tint 覆盖
    parts.append(_rect(x, y, w, h,
                       fill=_tint(c, 0.22),
                       stroke=c, sw=2.2, rx=10))

    cx = x + w / 2
    # name
    size, fam, wt = TYPE_SCALE[name_size_key]
    if name:
        parts.append(_txt(cx, y + h * 0.30, name,
                          size=size, family=fam, weight=wt,
                          fill=palette.ink, anchor="middle"))
    # role kicker
    if role:
        size, fam, wt = TYPE_SCALE["kicker_mini"]
        parts.append(_txt(cx, y + h * 0.48, role,
                          size=size, family=fam, weight=wt,
                          fill="rgba(28,25,20,0.62)", anchor="middle",
                          letter_em=0.22))
    # divider
    parts.append(_line(x + 20, y + h * 0.58, x + w - 20, y + h * 0.58,
                       stroke=_tint(c, 0.45), sw=0.7))
    # tagline (italic serif)
    if tagline:
        parts.append(_txt(cx, y + h * 0.73, tagline,
                          size=12, family=FONT_SERIF, weight=500,
                          fill="rgba(28,25,20,0.70)", anchor="middle",
                          italic=True))
    # stat + note
    if stat:
        size, fam, wt = TYPE_SCALE["micro_numeric"]
        # stat 单独一行 · note 附在 stat 右
        line_y = y + h * 0.90
        stat_svg = (
            f'<text x="{cx}" y="{line_y}" text-anchor="middle" '
            f'font-family="{FONT_SERIF}" font-size="15" font-weight="700" '
            f'fill="{c}">{esc(stat)}'
        )
        if stat_note:
            stat_svg += (
                f'<tspan dx="5" font-family="{FONT_SANS}" font-size="10" '
                f'font-weight="600" fill="rgba(28,25,20,0.55)">'
                f'{esc(stat_note)}</tspan>'
            )
        stat_svg += '</text>'
        parts.append(stat_svg)

    return "".join(parts)


def card_double(x: float, y: float, w: float, h: float, *,
                title: str = "",
                sub: str = "",
                caption: str = "",
                palette: Palette = BONE_RUST,
                hue: str = "rust",
                rx: float = 7.0,
                title_size_key: str = "card_title",
                variant: str = "default") -> str:
    """三级 card · cream 底 + tint rect + title (bold sans) + sub (italic).

    variant="default"   : title 居中 · sub 居中
    variant="left"      : title 左对齐 · sub 左对齐（用于 taxonomy sibling）
    variant="header"    : 顶部粗 tint 34px 条 + 主体 · 用于 sysdesign branch
    """
    c = _resolve_hue(hue)
    parts: List[str] = []
    # cream 底
    parts.append(_rect(x, y, w, h, fill=palette.bg, rx=rx))
    # tint
    parts.append(_rect(x, y, w, h,
                       fill=_tint(c, 0.12),
                       stroke=c, sw=1.2, rx=rx))
    cx = x + w / 2
    size, fam, wt = TYPE_SCALE[title_size_key]

    if variant == "left":
        if title:
            parts.append(_txt(x + 11, y + 15, title,
                              size=11.5, family=FONT_SANS, weight=700,
                              fill=palette.ink))
        if sub:
            parts.append(_txt(x + w - 11, y + 15, sub,
                              size=9, family=FONT_SANS, weight=600,
                              fill=_tint(c, 0.85), anchor="end"))
        if caption:
            parts.append(_txt(x + 11, y + 29, caption,
                              size=9, family=FONT_SANS, weight=500,
                              fill="rgba(94,80,62,0.72)", italic=True))
    else:
        # default · 居中
        if title:
            parts.append(_txt(cx, y + 22, title,
                              size=size, family=fam, weight=wt,
                              fill=palette.ink, anchor="middle"))
        # in-card hairline
        if sub or caption:
            parts.append(_line(x + 14, y + 30, x + w - 14, y + 30,
                               stroke=_tint(c, 0.40), sw=0.6))
        if sub:
            parts.append(_txt(cx, y + 48, sub,
                              size=9.5, family=FONT_SANS, weight=500,
                              fill="rgba(28,25,20,0.75)", anchor="middle"))
        if caption:
            parts.append(_txt(cx, y + 64, caption,
                              size=9, family=FONT_SANS, weight=600,
                              fill=_tint(c, 1.0), anchor="middle",
                              italic=True))
    return "".join(parts)


def chip_pill(x: float, y: float, w: float, h: float, *,
              label: str = "",
              palette: Palette = BONE_RUST,
              hue: str = "rust") -> str:
    """pill chip · rx=h/2 · fill=tint 0.12 · stroke 1.1 · label 11pt bold ink."""
    return chip_pill_sized(x, y, w, h, label=label, palette=palette, hue=hue,
                            font_size=11.0)


def chip_pill_sized(x: float, y: float, w: float, h: float, *,
                    label: str = "",
                    palette: Palette = BONE_RUST,
                    hue: str = "rust",
                    font_size: float = 11.0,
                    max_lines: int = 1) -> str:
    """pill chip · 单行 · 字号自适应 (label 长时缩字号)."""
    c = _resolve_hue(hue)
    parts: List[str] = [
        _rect(x, y, w, h,
              fill=_tint(c, 0.12), stroke=c, sw=1.1, rx=h / 2),
    ]
    if label:
        avail_w = w - 12
        fs, txt = _fit_font_size(label, avail_w, font_size, min_size=7.0)
        parts.append(_txt(x + w / 2, y + h / 2 + fs * 0.35, txt,
                          size=fs, family=FONT_SANS, weight=700,
                          fill=palette.ink, anchor="middle"))
    return "".join(parts)


def ribbon_gradient(hub_top: Tuple[float, float],
                    hub_bot: Tuple[float, float],
                    blk_top: Tuple[float, float],
                    blk_bot: Tuple[float, float],
                    *, hue: str = "rust") -> str:
    """双 bezier 梯形 · 从 hub 侧 (top→bot) 到 block 侧 (top→bot)。

    输入 4 个 (x,y) 点：hub 侧上下 · block 侧上下。
    fill 用对应 hue linearGradient (svg_defs 里已注入)。
    """
    hx1, hy1 = hub_top
    hx2, hy2 = hub_bot
    bx1, by1 = blk_top
    bx2, by2 = blk_bot
    # 中控点 · x 方向 ~30% 处
    cx1 = hx1 + (bx1 - hx1) * 0.30
    cx2 = hx2 + (bx2 - hx2) * 0.30
    d = (
        f"M {hx1} {hy1} "
        f"C {cx1} {hy1}, {cx1} {by1}, {bx1} {by1} "
        f"L {bx2} {by2} "
        f"C {cx2} {by2}, {cx2} {hy2}, {hx2} {hy2} Z"
    )
    return f'<path d="{d}" fill="url(#ea-r-{hue})"/>'


def connector_dashed(x1: float, y1: float, x2: float, y2: float,
                     *, hue: str = "rust", opacity: float = 0.55) -> str:
    """L3→L4 虚线 hairline · dash 3 2 · sw 1.2 · opacity 0.55。"""
    c = _resolve_hue(hue)
    return _line(x1, y1, x2, y2, stroke=c, sw=1.2, dash="3 2",
                 opacity=opacity)


def or_gate_path(cx: float, cy: float, hw: float = 14.0, h: float = 26.0) -> str:
    """OR gate · 尖顶盾牌 (Ishikawa/FTA 传统). top vertex (cx, cy-h/2)."""
    top_x, top_y = cx, cy - h / 2
    bl_x, bl_y = cx - hw, cy + h / 2 - 2
    br_x, br_y = cx + hw, cy + h / 2 - 2
    bot_mid_x, bot_mid_y = cx, cy + h / 2 + 2
    left_ctrl_x, left_ctrl_y = cx - hw - 2, cy - 3
    right_ctrl_x, right_ctrl_y = cx + hw + 2, cy - 3
    return (f"M {top_x} {top_y} "
            f"Q {left_ctrl_x} {left_ctrl_y} {bl_x} {bl_y} "
            f"Q {bot_mid_x} {bot_mid_y - 6} {br_x} {br_y} "
            f"Q {right_ctrl_x} {right_ctrl_y} {top_x} {top_y} Z")


def and_gate_path(cx: float, cy: float, hw: float = 14.0, h: float = 26.0) -> str:
    """AND gate · 弧顶方底 (D-shape)."""
    top_y = cy - h / 2
    bot_y = cy + h / 2
    left_x = cx - hw
    right_x = cx + hw
    mid_y = top_y + hw
    return (f"M {left_x} {bot_y} "
            f"L {left_x} {mid_y} "
            f"A {hw} {hw} 0 0 1 {right_x} {mid_y} "
            f"L {right_x} {bot_y} Z")


def phospho_disc(cx: float, cy: float,
                 *, palette: Palette = BONE_RUST,
                 label: str = "P",
                 r: float = 9.0) -> str:
    """p53 phosphorylation 圆 · GOLD_P fill + BONE stroke + serif "P" label。"""
    parts: List[str] = [
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{HUE["gold_p"]}" '
        f'stroke="{palette.bg}" stroke-width="1.4"/>',
    ]
    if label:
        parts.append(_txt(cx, cy + 4, label,
                          size=12, family=FONT_SERIF, weight=800,
                          fill=palette.ink, anchor="middle"))
    return "".join(parts)


def feedback_arc(x1: float, y1: float, x2: float, y2: float, *,
                 direction: str = "transactivate",
                 palette: Palette = BONE_RUST) -> str:
    """p53 feedback 双弧 · transactivate=RUST solid + arrow · degrade=GRAY dashed + T-bar.

    control point 由起点自动 offset (上方向弧)。
    """
    # control point · 起终点中点上方 40px
    mx = (x1 + x2) / 2
    my = min(y1, y2) - 42
    d = f"M {x1} {y1} C {x1} {my}, {x2} {my}, {x2} {y2}"
    if direction == "transactivate":
        return (
            f'<path d="{d}" fill="none" stroke="{HUE["rust"]}" '
            f'stroke-width="1.9" opacity="0.88" '
            f'marker-end="url(#ea-arr-rust)"/>'
        )
    else:  # degrade
        return (
            f'<path d="{d}" fill="none" stroke="rgba(94,80,62,0.85)" '
            f'stroke-width="1.9" stroke-dasharray="5 3" opacity="0.9" '
            f'marker-end="url(#ea-tbar-gray)"/>'
        )


def halo_wrap(x: float, y: float, w: float, h: float,
              *, palette: Palette = BONE_RUST, sw: float = 2.0,
              opacity: float = 0.5, rx: float = 12.0) -> str:
    """在 highlighted 元素外画一圈 hub-halo · 用于 taxonomy lineage 首末端。"""
    pad = 10
    return _rect(x - pad, y - pad, w + pad * 2, h + pad * 2,
                 fill=None, stroke=palette.primary, sw=sw,
                 opacity=opacity, rx=rx, filter_id="ea-hub-halo")


# ═════════════════════════════════════════════════════════════════
# hero_chrome · hero_footer (canvas-aware 6-layer chrome)
# ═════════════════════════════════════════════════════════════════

def hero_chrome(*, kicker: str = "",
                title: str = "",
                subtitle: str = "",
                column_headers: Optional[Sequence[Tuple[str, float]]] = None,
                encoding_note_right: str = "",
                palette: Palette = BONE_RUST,
                canvas: CanvasProfile = HERO_CANVAS,
                include_bg: bool = True) -> str:
    """顶部 chrome (title + subtitle + hair + column headers)。

    include_bg: 是否绘制满版背景 rect (默认 True). 关掉后 slide 底色自然透出,
        避免 SVG 底色与 slide 底色不一致造成的突兀色块.
    canvas=EMBED 时字号缩到 embed 尺度 (title 17 · subtitle 10 · section 8).
    """
    is_embed = (canvas.w == 900 and canvas.h in (300, 336))
    title_sz = 17 if is_embed else 26
    subtitle_sz = 10 if is_embed else 13
    section_sz = 8 if is_embed else 10
    # R1-FIX: embed kicker 8 → 11 (post-atomize ≥ 10pt redline)
    kicker_sz = 11 if is_embed else 10
    parts: List[str] = []
    # 背景 (可关)
    if include_bg:
        parts.append(_rect(0, 0, canvas.w, canvas.h, fill=palette.bg))
    # kicker (小字上方) · 用户可以留空
    if kicker:
        parts.append(_txt(canvas.margin_x, canvas.title_y - 20, kicker,
                          size=kicker_sz, family=FONT_SANS, weight=700,
                          fill=palette.primary, letter_em=0.22))
    # title
    if title:
        parts.append(_txt(canvas.margin_x, canvas.title_y, title,
                          size=title_sz, family=FONT_SERIF, weight=700,
                          fill=palette.ink, letter_em=0.01))
    # subtitle
    if subtitle:
        parts.append(_txt(canvas.margin_x, canvas.subtitle_y, subtitle,
                          size=subtitle_sz, family=FONT_SANS, weight=500,
                          fill=palette.gray, letter_em=0.04))
    # title hairline
    parts.append(_line(canvas.margin_x, canvas.title_hair_y,
                       canvas.w - canvas.margin_x, canvas.title_hair_y,
                       stroke=palette.hair, sw=0.6, opacity=0.22))
    # column headers
    if column_headers:
        for lbl, cx in column_headers:
            parts.append(_txt(cx, canvas.section_hdr_y, lbl,
                              size=section_sz, family=FONT_SANS, weight=700,
                              fill=_tint(HUE["rust"], 0.90),
                              anchor="middle", letter_em=0.26))
    # 顶右侧 encoding
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
                palette: Palette = BONE_RUST,
                canvas: CanvasProfile = HERO_CANVAS,
                min_read_chars: int = 40) -> str:
    """底部 chrome — 已按用户指令关闭渲染 · 所有 hero_embed / hero canvas 保留顶部 chrome，
    底部 READ + source + bottom hairline 全部不再输出（slide 页面自带说明文本）。

    仍保留签名 · 让 preset 调用方无需改动 · 参数会被静默忽略。
    """
    _ = (caption, source, read_lines, italic_last, palette, canvas, min_read_chars)
    return ""


def _validate_read_line(line_svg: str, min_chars: int) -> None:
    """READ 每行必须 ≥ min_chars 字符（去 tag 后计）· 否则 raise ValueError."""
    # 粗略剥掉 <tspan ...>...</tspan>
    import re
    plain = re.sub(r"<[^>]+>", "", line_svg)
    if len(plain) < min_chars:
        raise ValueError(
            f"[editorial_atelier] READ line too short "
            f"({len(plain)} < {min_chars}): {plain[:60]!r}"
        )


def read_line(text_html: str) -> str:
    """占位 · 供 preset 明确"这是一段 read line SVG"的注解。

    preset 直接把 markup 字符串（含 <tspan>）传进 hero_footer.read_lines。
    """
    return text_html


def tspan(word: str, *, color: str = HUE["rust"], weight: int = 700) -> str:
    """READ 段内高亮 · fill 用 hue key 或 hex."""
    c = _resolve_hue(color) if not color.startswith("rgba") else color
    return (f'<tspan font-weight="{weight}" fill="{c}">'
            f'{esc(word)}</tspan>')


# ═════════════════════════════════════════════════════════════════
# Skin 协议实现 · draw_node / draw_edge / draw_container / defs
# ═════════════════════════════════════════════════════════════════

class EditorialAtelierSkin:
    """K9 · editorial_atelier · Bone/Rust 编辑排印 skin."""

    name = "editorial_atelier"

    # ── defs ──
    def defs(self, palette: Palette) -> str:
        """默认注入 3 filter + 全部 hue gradient + 全部 hue marker."""
        return svg_defs(hues=HUE_ORDER, include_gradients=True,
                        include_markers=True)

    # ── node · 按 kind 分流 ──
    def draw_node(self, x, y, w, h, label, palette: Palette,
                  kind: str = "card",
                  sublabel: str = "", caption: str = "",
                  hue: str = "rust", **kwargs) -> str:
        pal = palette or BONE_RUST
        label = _label_clip(label, 40) if label else ""
        sub = _label_clip(sublabel, 60) if sublabel else ""
        cap = _label_clip(caption, 40) if caption else ""

        if kind == "hub":
            role = kwargs.get("role", "")
            tagline = kwargs.get("tagline", "")
            stat = kwargs.get("stat", "")
            stat_note = kwargs.get("stat_note", "")
            xl = kwargs.get("hub_xl", False)
            return hub_double(x, y, w, h, name=label, role=role,
                              tagline=tagline, stat=stat, stat_note=stat_note,
                              palette=pal, hue=hue, with_halo=True,
                              name_size_key="hub_name_xl" if xl else "hub_name")
        elif kind == "chip":
            font_size = kwargs.get("font_size", 11)
            max_lines = kwargs.get("max_lines", 1)
            return chip_pill_sized(x, y, w, h, label=label, palette=pal,
                                    hue=hue, font_size=font_size,
                                    max_lines=max_lines)
        elif kind == "branch_label":
            # fishbone branch 标签 · tint 圆角矩形 + Georgia bold + label (单行字号自适应)
            c = _resolve_hue(hue)
            font_size = kwargs.get("font_size", 12)
            parts: List[str] = [
                _rect(x, y, w, h,
                      fill=_tint(c, 0.24), stroke=c, sw=1.4, rx=5),
            ]
            if label:
                fs, txt = _fit_font_size(label, w - 8, font_size, min_size=8.0)
                parts.append(_txt(x + w / 2, y + h / 2 + fs * 0.35, txt,
                                  size=fs, family=FONT_SERIF, weight=800,
                                  fill=pal.ink, anchor="middle"))
            return "".join(parts)
        elif kind == "row_bar":
            # stacked_layers · 整行 tint 底 + 细边
            c = _resolve_hue(hue)
            return _rect(x, y, w, h, fill=_tint(c, 0.14),
                         stroke=c, sw=1.2, rx=5)
        elif kind == "row_hue_bar":
            # 行左侧 hue 色条 · 无描边纯 fill
            c = _resolve_hue(hue)
            return _rect(x, y, w, h, fill=c, rx=2)
        elif kind == "row_circle":
            # layer 编号圆 · fill hue · label bg color
            c = _resolve_hue(hue)
            r = kwargs.get("r", w / 2)
            cx, cy = x + w / 2, y + h / 2
            parts: List[str] = [
                f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{c}"/>',
            ]
            if label:
                parts.append(_txt(cx, cy + 3.5, label,
                                  size=10, family=FONT_SERIF, weight=800,
                                  fill=pal.bg, anchor="middle"))
            return "".join(parts)
        elif kind == "row_short":
            # 短 kicker (L7 / L1 etc) · hue color · uppercase 追踪
            c = _resolve_hue(hue)
            return _txt(x, y + h / 2 + 3.5, label,
                        size=9, family=FONT_SANS, weight=700,
                        fill=c, letter_em=0.14)
        elif kind == "row_name":
            # layer 全名 · Georgia bold ink · 单行 · 字号自适应
            fs, txt = _fit_font_size(label, w - 4, 13.0, min_size=9.0)
            return _txt(x, y + h / 2 + fs * 0.4, txt,
                        size=fs, family=FONT_SERIF, weight=800,
                        fill=pal.ink)
        elif kind == "main_card":
            # 5why 主链常规卡 · soft-shadow bg + tint + left hue bar + kicker + label 字号自适应
            c = _resolve_hue(hue)
            kicker_txt = kwargs.get("kicker", "")
            parts: List[str] = [
                _rect(x, y, w, h, fill=pal.bg, rx=6, filter_id="ea-soft-shadow"),
                _rect(x, y, w, h, fill=_tint(c, 0.14),
                      stroke=c, sw=1.3, rx=6),
                _rect(x, y, 4, h, fill=c, rx=2),
            ]
            if kicker_txt:
                parts.append(_txt(x + 12, y + h / 2 + 3.5, kicker_txt,
                                  size=8, family=FONT_SANS, weight=700,
                                  fill=c, letter_em=0.18))
            if label:
                label_x = x + max(108, len(kicker_txt) * 5 + 20)
                label_avail = x + w - label_x - 6
                fs, txt = _fit_font_size(label, label_avail, 11.0, min_size=8.0)
                parts.append(_txt(label_x, y + h / 2 + fs * 0.32, txt,
                                  size=fs, family=FONT_SERIF, weight=700,
                                  fill=pal.ink))
            return "".join(parts)
        elif kind == "root_card":
            # 5why 主链末卡 · 外层 halo + 内层 tint 强化
            c = _resolve_hue(hue)
            kicker_txt = kwargs.get("kicker", "")
            parts = [
                _rect(x - 4, y - 4, w + 8, h + 8, fill=None,
                      stroke=c, sw=1.4, rx=9, opacity=0.55),
                _rect(x, y, w, h, fill=_tint(c, 0.22),
                      stroke=c, sw=2.2, rx=6),
            ]
            if kicker_txt:
                parts.append(_txt(x + 12, y + h / 2 + 3.5, kicker_txt,
                                  size=8, family=FONT_SANS, weight=700,
                                  fill=c, letter_em=0.18))
            if label:
                label_x = x + max(108, len(kicker_txt) * 5 + 20)
                label_avail = x + w - label_x - 6
                fs, txt = _fit_font_size(label, label_avail, 11.0, min_size=8.0)
                parts.append(_txt(label_x, y + h / 2 + fs * 0.32, txt,
                                  size=fs, family=FONT_SERIF, weight=800,
                                  fill=pal.ink))
            return "".join(parts)
        elif kind == "parallel_card":
            # 5why parallel 侧枝卡 · dashed stroke · 三行 · label / sub 字号自适应
            c = _resolve_hue(hue)
            kicker_txt = kwargs.get("kicker", "")
            sub_txt = kwargs.get("sub", "")
            parts = [
                _rect(x, y, w, h, fill=pal.bg, rx=7, filter_id="ea-soft-shadow"),
                _rect(x, y, w, h, fill=_tint(c, 0.18),
                      stroke=c, sw=1.5, rx=7, dash="4 3"),
            ]
            if kicker_txt:
                parts.append(_txt(x + 12, y + 16, kicker_txt,
                                  size=8, family=FONT_SANS, weight=700,
                                  fill=c, letter_em=0.20))
            if label:
                fs, txt = _fit_font_size(label, w - 24, 12.0, min_size=8.5)
                parts.append(_txt(x + 12, y + 33, txt,
                                  size=fs, family=FONT_SERIF, weight=800,
                                  fill=pal.ink))
            if sub_txt:
                fs, txt = _fit_font_size(sub_txt, w - 24, 8.5, min_size=7.0)
                parts.append(_txt(x + 12, y + 46, txt,
                                  size=fs, family=FONT_SANS, weight=500,
                                  fill="rgba(28,25,20,0.68)", italic=True))
            return "".join(parts)
        elif kind == "edge_label":
            # WHY? pill · ink bg + hue border + gold text
            c = _resolve_hue(hue)
            parts = [
                _rect(x, y, w, h, fill=pal.ink, stroke=c, sw=1.0,
                      rx=h / 2),
            ]
            if label:
                parts.append(_txt(x + w / 2, y + h / 2 + 3.5, label,
                                  size=7, family=FONT_SANS, weight=700,
                                  fill=HUE["gold_p"], anchor="middle",
                                  letter_em=0.24))
            return "".join(parts)
        elif kind == "top_event":
            # FT top event · rust bg + left hue bar + "TOP EVENT" kicker + label 字号自适应
            c = _resolve_hue(hue)
            parts = [
                _rect(x, y, w, h, fill=pal.bg, rx=6),
                _rect(x, y, w, h, fill=_tint(c, 0.22), stroke=c, sw=1.8, rx=6),
                _rect(x, y, 5, h, fill=c, rx=2.5),
            ]
            parts.append(_txt(x + 12, y + 11, "TOP EVENT",
                              size=7, family=FONT_SANS, weight=800,
                              fill=c, letter_em=0.22))
            if label:
                fs, txt = _fit_font_size(label, w - 20, 11.0, min_size=8.0)
                parts.append(_txt(x + w / 2, y + h - 8, txt,
                                  size=fs, family=FONT_SERIF, weight=800,
                                  fill=pal.ink, anchor="middle"))
            return "".join(parts)
        elif kind == "gate":
            # FT gate · OR (盾牌) or AND (D-shape) · center label
            op = kwargs.get("op", "OR")
            c = _resolve_hue(hue)
            cx_g, cy_g = x + w / 2, y + h / 2
            hw = w / 2
            gh = h
            if op == "AND":
                d = and_gate_path(cx_g, cy_g, hw=hw, h=gh)
            else:
                d = or_gate_path(cx_g, cy_g, hw=hw, h=gh)
            parts = [
                f'<path d="{d}" fill="{_tint(c, 0.18)}" '
                f'stroke="{c}" stroke-width="1.6" stroke-linejoin="round"/>',
            ]
            if label:
                parts.append(_txt(cx_g, cy_g + 3, label,
                                  size=8.5, family=FONT_SANS, weight=800,
                                  fill=c, anchor="middle", letter_em=0.10))
            return "".join(parts)
        elif kind == "intermediate":
            # FT intermediate · rect + left hue bar + name (字号自适应) + note italic (自适应)
            c = _resolve_hue(hue)
            note = kwargs.get("note", "")
            parts = [
                _rect(x, y, w, h, fill=pal.bg, rx=4),
                _rect(x, y, w, h, fill=_tint(c, 0.12),
                      stroke=c, sw=1.3, rx=4),
                _rect(x, y, 3, h, fill=c, rx=1.5),
            ]
            if label:
                fs, txt = _fit_font_size(label, w - 8, 10.5, min_size=7.5)
                # 有 note 时 label 上偏 · 无 note 时居中
                y_label = y + h / 2 - 4 if note else y + h / 2 + 3
                parts.append(_txt(x + w / 2, y_label, txt,
                                  size=fs, family=FONT_SERIF, weight=800,
                                  fill=pal.ink, anchor="middle"))
            if note:
                fs, txt = _fit_font_size(note, w - 8, 7.5, min_size=6.0)
                parts.append(_txt(x + w / 2, y + h - 6, txt,
                                  size=fs, family=FONT_SANS, weight=500,
                                  italic=True, fill="rgba(28,25,20,0.62)",
                                  anchor="middle"))
            return "".join(parts)
        elif kind == "basic_circle":
            # FT basic event · 双圆 (bg + inner tint) · label 下方单行 · 字号自适应
            c = _resolve_hue(hue)
            r = kwargs.get("r", w / 2)
            cx_b, cy_b = x + w / 2, y + h / 2
            label_y = kwargs.get("label_y", cy_b + r + 8)
            parts = [
                f'<circle cx="{cx_b}" cy="{cy_b}" r="{r}" '
                f'fill="{pal.bg}" stroke="{c}" stroke-width="1.6"/>',
                f'<circle cx="{cx_b}" cy="{cy_b}" r="{max(r - 4, 2)}" '
                f'fill="{_tint(c, 0.20)}"/>',
            ]
            if label:
                # basic 下方 avail = 5*r · 缩到 min_size=6
                fs, txt = _fit_font_size(label, r * 5.5, 7.5, min_size=6.0)
                parts.append(_txt(cx_b, label_y, txt,
                                  size=fs, family=FONT_SANS, weight=700,
                                  fill=c, anchor="middle"))
            return "".join(parts)
        elif kind == "hub_core":
            # mindmap hub · 深墨底 + rust halo + gold CORE kicker + label 字号自适应 + stat
            tagline = kwargs.get("tagline", "")
            stat = kwargs.get("stat", "")
            stat_note = kwargs.get("stat_note", "")
            rust = HUE["rust"]
            gold = HUE["gold_p"]
            parts = [
                _rect(x - 6, y - 6, w + 12, h + 12, fill=None,
                      stroke=rust, sw=1.6, rx=10, opacity=0.5),
                _rect(x, y, w, h, fill=pal.ink, stroke=rust,
                      sw=2.0, rx=8),
            ]
            parts.append(_txt(x + w / 2, y + 18, "CORE",
                              size=8, family=FONT_SANS, weight=700,
                              fill=gold, anchor="middle", letter_em=0.24))
            if label:
                fs, txt = _fit_font_size(label, w - 12, 14.0, min_size=9.0)
                parts.append(_txt(x + w / 2, y + 36, txt,
                                  size=fs, family=FONT_SERIF, weight=800,
                                  fill=pal.bg, anchor="middle"))
            if stat:
                stat_svg = (
                    f'<text x="{x + w / 2}" y="{y + 54}" text-anchor="middle" '
                    f'font-family="{FONT_SERIF}" font-size="12" font-weight="700" '
                    f'fill="{gold}">{esc(stat)}'
                )
                if stat_note:
                    stat_svg += (
                        f'<tspan dx="4" font-family="{FONT_SANS}" font-size="8" '
                        f'font-weight="500" fill="rgba(241,233,218,0.72)" '
                        f'letter-spacing="0.16em">{esc(stat_note.upper())}</tspan>'
                    )
                stat_svg += '</text>'
                parts.append(stat_svg)
            return "".join(parts)
        elif kind == "mp_branch_label":
            # mindmap branch label · tint fill + label 字号自适应 + "N IDEAS" 小字
            c = _resolve_hue(hue)
            n_leaf = kwargs.get("n_leaf", 0)
            parts = [
                _rect(x, y, w, h, fill=_tint(c, 0.20),
                      stroke=c, sw=1.4, rx=6),
            ]
            if label:
                fs, txt = _fit_font_size(label, w - 10, 12.0, min_size=8.5)
                y_offset = -1 if n_leaf > 0 else 3.5
                parts.append(_txt(x + w / 2, y + h / 2 + y_offset, txt,
                                  size=fs, family=FONT_SERIF, weight=800,
                                  fill=pal.ink, anchor="middle"))
            if n_leaf > 0:
                parts.append(_txt(x + w / 2, y + h / 2 + 10, f"{n_leaf} IDEAS",
                                  size=7, family=FONT_SANS, weight=700,
                                  fill=c, anchor="middle", letter_em=0.15))
            return "".join(parts)
        elif kind == "stat_card":
            # PMF pillar 顶部卡 · shadow bg + tint + hue bar + kicker + name + big stat + sub
            c = _resolve_hue(hue)
            kicker_txt = kwargs.get("kicker", "")
            stat = kwargs.get("stat", "")
            sub_txt = kwargs.get("sub", "")
            parts = [
                _rect(x, y, w, h, fill=pal.bg, rx=8, filter_id="ea-hub-shadow"),
                _rect(x, y, w, h, fill=_tint(c, 0.16),
                      stroke=c, sw=1.4, rx=8),
                _rect(x, y, 4, h, fill=c, rx=2),
            ]
            if kicker_txt:
                parts.append(_txt(x + 14, y + 16, kicker_txt,
                                  size=8, family=FONT_SANS, weight=700,
                                  fill=c, letter_em=0.22))
            # 大 stat 靠右 · 若无 stat 则跳过
            stat_reserve = 0
            if stat:
                fs_stat, stat_txt = _fit_font_size(stat, w * 0.35, 22.0, min_size=13.0)
                parts.append(_txt(x + w - 14, y + 36, stat_txt,
                                  size=fs_stat, family=FONT_SERIF, weight=800,
                                  fill=c, anchor="end"))
                stat_reserve = w * 0.35 + 10
            if label:
                name_avail = w - 28 - stat_reserve
                fs_name, name_txt = _fit_font_size(label, name_avail, 16.0, min_size=11.0)
                parts.append(_txt(x + 14, y + 36, name_txt,
                                  size=fs_name, family=FONT_SERIF, weight=800,
                                  fill=pal.ink))
            if sub_txt:
                fs_sub, sub_display = _fit_font_size(sub_txt, w - 28, 9.0, min_size=7.0)
                parts.append(_txt(x + 14, y + 51, sub_display,
                                  size=fs_sub, family=FONT_SANS, weight=500,
                                  italic=True, fill="rgba(28,25,20,0.72)"))
            return "".join(parts)
        elif kind == "stage_badge":
            # PMF 顶部装饰 pill · ink bg · rust border · gold 字
            c = _resolve_hue(hue)
            parts = [
                _rect(x, y, w, h, fill=pal.ink, stroke=c, sw=1.2, rx=8),
            ]
            if label:
                fs, txt = _fit_font_size(label, w - 20, 8.5, min_size=7.0)
                parts.append(_txt(x + w / 2, y + h / 2 + fs * 0.35, txt,
                                  size=fs, family=FONT_SANS, weight=700,
                                  fill=HUE["gold_p"], anchor="middle",
                                  letter_em=0.20))
            return "".join(parts)
        elif kind == "hub_root":
            # TR root · hub_frame halo + name + hairline + big stat + kicker
            c = _resolve_hue(hue)
            stat = kwargs.get("stat", "")
            stat_label = kwargs.get("stat_label", "")
            parts: List[str] = []
            parts.append(hub_frame(x, y, w, h, palette=pal, hue=hue,
                                     halo_pad=6, halo_rx=10, halo_sw=1.8,
                                     halo_opacity=0.55, rx=8, stroke_sw=2.0))
            if label:
                fs, txt = _fit_font_size(label, w - 16, 17.0, min_size=11.0)
                parts.append(_txt(x + w / 2, y + h / 2 - 8, txt,
                                  size=fs, family=FONT_SERIF, weight=800,
                                  fill=pal.ink, anchor="middle"))
            if stat or stat_label:
                parts.append(
                    f'<line x1="{x + w/2 - 26}" y1="{y + h/2 + 2}" '
                    f'x2="{x + w/2 + 26}" y2="{y + h/2 + 2}" '
                    f'stroke="rgba(163,88,50,0.5)" stroke-width="0.7"/>'
                )
            if stat:
                parts.append(_txt(x + w / 2, y + h / 2 + 15, stat,
                                  size=14, family=FONT_SERIF, weight=800,
                                  fill=c, anchor="middle"))
            if stat_label:
                fs, txt = _fit_font_size(stat_label, w - 16, 8.0, min_size=6.5)
                parts.append(_txt(x + w / 2, y + h / 2 + 26, txt,
                                  size=fs, family=FONT_SANS, weight=700,
                                  fill=c, anchor="middle", letter_em=0.22))
            return "".join(parts)
        elif kind == "d2_card":
            # 中级 card · tint + border + name (Georgia 12 · 自适应)
            c = _resolve_hue(hue)
            parts = [
                _rect(x, y, w, h, fill=_tint(c, 0.20),
                      stroke=c, sw=1.4, rx=6),
            ]
            if label:
                fs, txt = _fit_font_size(label, w - 12, 12.0, min_size=8.5)
                parts.append(_txt(x + w / 2, y + h / 2 + fs * 0.33, txt,
                                  size=fs, family=FONT_SERIF, weight=800,
                                  fill=pal.ink, anchor="middle"))
            return "".join(parts)
        elif kind == "d3_card":
            # 三级 card · 更小 · Inter bold
            c = _resolve_hue(hue)
            parts = [
                _rect(x, y, w, h, fill=_tint(c, 0.16),
                      stroke=c, sw=1.3, rx=5),
            ]
            if label:
                fs, txt = _fit_font_size(label, w - 10, 10.5, min_size=8.0)
                parts.append(_txt(x + w / 2, y + h / 2 + fs * 0.33, txt,
                                  size=fs, family=FONT_SANS, weight=800,
                                  fill=pal.ink, anchor="middle"))
            return "".join(parts)
        elif kind == "leaf_panel":
            # leaf 容器 · 淡 tint bg + dashed hairline · 无 label
            c = _resolve_hue(hue)
            return _rect(x, y, w, h, fill=_tint(c, 0.06),
                          stroke=_tint(c, 0.35), sw=0.8, rx=6,
                          dash="3 2")
        elif kind == "leaf_chip":
            # leaf pill · 若 highlight 加 gold ring
            highlight = kwargs.get("highlight", False)
            font_size = kwargs.get("font_size", 10.5)
            parts_l: List[str] = []
            if highlight:
                gold = HUE["gold_p"]
                parts_l.append(
                    f'<rect x="{x-3}" y="{y-3}" width="{w+6}" height="{h+6}" '
                    f'rx="{(h+6)/2}" fill="none" stroke="{gold}" '
                    f'stroke-width="2.0" opacity="0.9"/>'
                )
            parts_l.append(chip_pill_sized(x, y, w, h, label=label, palette=pal,
                                             hue=hue, font_size=font_size))
            return "".join(parts_l)
        elif kind == "taxonomy_hub":
            # TX hub · hub_frame + kicker "TAXONOMY" + name + big count + note
            c = _resolve_hue(hue)
            stat = kwargs.get("stat", "")
            stat_note = kwargs.get("stat_note", "")
            parts: List[str] = []
            parts.append(hub_frame(x, y, w, h, palette=pal, hue=hue,
                                     halo_pad=6, halo_rx=10, halo_sw=1.8,
                                     halo_opacity=0.55, rx=9, stroke_sw=2.0))
            parts.append(_txt(x + w / 2, y + 18, "TAXONOMY",
                              size=8, family=FONT_SANS, weight=700,
                              fill=c, anchor="middle", letter_em=0.22))
            if label:
                fs, txt = _fit_font_size(label, w - 16, 14.0, min_size=10.0)
                parts.append(_txt(x + w / 2, y + 36, txt,
                                  size=fs, family=FONT_SERIF, weight=800,
                                  fill=pal.ink, anchor="middle"))
            if stat:
                stat_svg = (
                    f'<text x="{x + w / 2}" y="{y + 52}" text-anchor="middle" '
                    f'font-family="{FONT_SERIF}" font-size="12" font-weight="800" '
                    f'fill="{c}">{esc(stat)}'
                )
                if stat_note:
                    stat_svg += (
                        f'<tspan dx="3" font-family="{FONT_SANS}" font-size="7.5" '
                        f'font-weight="700" fill="rgba(28,25,20,0.55)" '
                        f'letter-spacing="0.18em">{esc(stat_note.upper())}</tspan>'
                    )
                stat_svg += '</text>'
                parts.append(stat_svg)
            return "".join(parts)
        elif kind == "category_label":
            # TX category label · tint rect + name + "N BENCHMARKS" 小字
            c = _resolve_hue(hue)
            n_leaf = kwargs.get("n_leaf", 0)
            parts = [
                _rect(x, y, w, h, fill=_tint(c, 0.20),
                      stroke=c, sw=1.5, rx=6),
            ]
            if label:
                fs, txt = _fit_font_size(label, w - 10, 12.0, min_size=8.5)
                parts.append(_txt(x + w / 2, y + h / 2 - 2, txt,
                                  size=fs, family=FONT_SERIF, weight=800,
                                  fill=pal.ink, anchor="middle"))
            if n_leaf > 0:
                fs, txt = _fit_font_size(f"{n_leaf} ITEMS", w - 10, 7.0, min_size=6.0)
                parts.append(_txt(x + w / 2, y + h / 2 + 9, txt,
                                  size=fs, family=FONT_SANS, weight=700,
                                  fill=c, anchor="middle", letter_em=0.16))
            return "".join(parts)
        elif kind == "phospho_disc":
            return phospho_disc(x + w / 2, y + h / 2, palette=pal, label=label or "P")
        elif kind == "sibling":
            return card_double(x, y, w, h, title=label, sub=sub,
                               caption=cap, palette=pal, hue=hue,
                               variant="left", rx=7)
        elif kind == "kinase_chip":
            # kinase 小 chip · label + sublabel 双行 · 用较大 bold
            parts: List[str] = [
                _rect(x, y, w, h, fill=pal.bg, rx=7, filter_id="ea-soft-shadow"),
                _rect(x, y, w, h,
                      fill=_tint(_resolve_hue(hue), 0.13),
                      stroke=_resolve_hue(hue), sw=1.5, rx=7),
            ]
            if label:
                parts.append(_txt(x + w / 2, y + h * 0.48, label,
                                  size=14.5, family=FONT_SANS, weight=800,
                                  fill=pal.ink, anchor="middle"))
            if sub:
                parts.append(_txt(x + w / 2, y + h * 0.82, sub,
                                  size=9.5, family=FONT_SANS, weight=600,
                                  fill="rgba(28,25,20,0.60)",
                                  anchor="middle", letter_em=0.06))
            return "".join(parts)
        else:
            # default · card_double
            return card_double(x, y, w, h, title=label, sub=sub,
                               caption=cap, palette=pal, hue=hue)

    # ── edge · 按 kind 分流 ──
    def draw_edge(self, x1, y1, x2, y2, label, palette: Palette,
                  kind: str = "rule",
                  hue: str = "rust", **kwargs) -> str:
        pal = palette or BONE_RUST
        if kind == "connector_dashed":
            return connector_dashed(x1, y1, x2, y2, hue=hue)
        elif kind == "phospho_line":
            c = _resolve_hue(hue)
            return _line(x1, y1, x2, y2, stroke=c, sw=1.9,
                         opacity=0.82, linecap="round",
                         marker_end=f"ea-arr-{hue}")
        elif kind == "rule_arrow":
            c = _resolve_hue(hue)
            return _line(x1, y1, x2, y2, stroke=c, sw=1.4, opacity=0.7,
                         marker_end=f"ea-arr-{hue}")
        elif kind == "tbar":
            return _line(x1, y1, x2, y2, stroke="rgba(94,80,62,0.85)",
                         sw=1.9, dash="5 3", opacity=0.9,
                         marker_end="ea-tbar-gray")
        else:  # rule · hairline
            return _line(x1, y1, x2, y2, stroke=pal.hair, sw=1.0,
                         opacity=0.5)

    # ── container · 按 kind 分流 ──
    def draw_container(self, x, y, w, h, label, palette: Palette,
                       kind: str = "section", hue: str = "rust",
                       **kwargs) -> str:
        pal = palette or BONE_RUST
        c = _resolve_hue(hue)
        parts: List[str] = []
        if kind == "column_bg":
            # taxonomy 6 列的 dashed tint container
            parts.append(_rect(x, y, w, h,
                               fill=_tint(c, 0.04),
                               stroke=_tint(c, 0.30),
                               sw=1.0, dash="4 3", rx=10))
        elif kind == "downstream_group":
            # p53 group · fill 0.05 + dashed stroke + 4 chip 网格
            parts.append(_rect(x, y, w, h,
                               fill=_tint(c, 0.05),
                               stroke=c, sw=1.1, dash="5 3",
                               rx=9, opacity=0.85))
            # group label chip
            parts.append(_rect(x + 8, y + 8, 12, 12, fill=c))
            if label:
                parts.append(_txt(x + 27, y + 18.5, label,
                                  size=10, family=FONT_SANS, weight=700,
                                  fill=pal.ink, letter_em=0.18))
        elif kind == "branch":
            # sysdesign 顶头带 · tint header 34px + body dashed
            parts.append(_rect(x, y, w, h,
                               fill=_tint(c, 0.06),
                               stroke=c, sw=1.2, dash="6 4",
                               rx=10, opacity=0.85))
            parts.append(_rect(x, y, w, 34, fill=_tint(c, 0.28), rx=10))
            parts.append(_rect(x, y + 24, w, 10, fill=_tint(c, 0.28)))
            if label:
                parts.append(_txt(x + 50, y + 22, label,
                                  size=17, family=FONT_SERIF, weight=700,
                                  fill=pal.ink))
        else:  # section · legacy 顶底 rule + kicker
            parts.append(_line(x, y, x + w, y, stroke=pal.ink, sw=1.4))
            parts.append(_line(x, y + h, x + w, y + h,
                               stroke=pal.hair, sw=0.6, opacity=0.4))
            if label:
                parts.append(_txt(x + w / 2, y + 6, label,
                                  size=10, family=FONT_SANS, weight=700,
                                  fill=pal.ink, anchor="middle",
                                  letter_em=0.22))
        return "".join(parts)


EDITORIAL_ATELIER = EditorialAtelierSkin()


__all__ = [
    # Skin
    "EditorialAtelierSkin", "EDITORIAL_ATELIER",
    # Palette
    "BONE_RUST",
    # Canvas
    "CanvasProfile", "HERO_CANVAS", "EMBED_CANVAS", "TX_CANVAS",
    # Element profile
    "ElementProfile", "HERO_PROFILE", "EMBED_PROFILE", "profile_for",
    # Tokens
    "HUE", "HUE_ORDER", "TYPE_SCALE", "FONT_SERIF", "FONT_SANS",
    # Primitive helpers
    "svg_defs", "hub_frame", "hub_double", "card_double", "chip_pill",
    "chip_pill_sized",
    "ribbon_gradient", "connector_dashed", "phospho_disc",
    "feedback_arc", "halo_wrap",
    "or_gate_path", "and_gate_path",
    # Chrome
    "hero_chrome", "hero_footer", "read_line", "tspan",
]
