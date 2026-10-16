"""
Skin · journal_ivory · Ivory / Deep Indigo / Jade 学术期刊 figure

参照 dcg_style_experiments/HANDBOOK.md §4 academic-research token 建立：

视觉核心：
    * bg=#F7F3E8 象牙纸 (拒绝简陋白底 · Nature figure 感)
    * 主色 #1E2A5E 深靛 · 强调色 #4A7C6E 玉青 (anomaly · 3-cycle + retry)
    * 中性 #4F4A3E / #7A7566
    * 字体：EB Garamond (14-16pt 节点名 · 大标题) + Inter (9-10pt 标签)
    * 节点形态：rx=0 · fill=none · 0.6-1.2px hairline · 论文极简线稿
    * 装饰母题：panel 边框 · (a) TOPOLOGY 面板标签 · tier hairline tick ·
                数学符号度数 d⁻ = 1 · 单位符号 s⁻¹ · ★ Unicode 3-cycle ·
                Nature figure 底部 keyed legend · 右下 Fig. 3 · page 3
    * 首版复用 editorial_atelier 的 chrome / defs 函数几何 · 只改配色与字型

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
# 8 支 hue · rust slot 重新映射到深靛主色 · 保持 key 名不变 (preset 依赖 key)
# 副 hue 全部收敛到学术极简调色 · hairline 数学感 · Nature figure 配色
HUE = {
    "rust":     "#1E2A5E",   # 主色 · 深靛（原 rust 位）
    "orange":   "#4A7C6E",   # 玉青 · accent (anomaly · 3-cycle + retry)
    "magenta":  "#6B2E4E",   # 深紫红
    "blue":     "#2C4370",   # mid indigo
    "green":    "#3D5A4E",   # deep sage
    "olive":    "#4F4A3E",   # 深橄榄墨 · 中性
    "cinnamon": "#7A6A3E",   # 学术棕
    "gold_p":   "#B58A3E",   # muted 学术金 · 期刊 figure caption
}

HUE_ORDER: Tuple[str, ...] = (
    "rust", "orange", "magenta", "blue", "green", "olive", "cinnamon",
)


# ─────────── Typography ───────────
# HANDBOOK §4 硬要求：EB Garamond (大标题 / 节点名) + Inter (标签)
# head_family 走 SERIF (EB Garamond) · body 用 SANS (Inter)
FONT_SANS = "Inter, Söhne, Helvetica Neue, sans-serif"
FONT_SERIF = "EB Garamond, Baskerville, Georgia, serif"

TYPE_SCALE = {
    "title":         (26, FONT_SERIF, 700),
    "subtitle":      (13, FONT_SANS,  500),
    "section":       (10, FONT_SANS,  700),
    "column_header": (10, FONT_SANS,  700),
    "hub_name":      (19, FONT_SERIF, 700),
    "hub_name_xl":   (26, FONT_SERIF, 700),
    "block_title":   (17, FONT_SERIF, 700),
    "card_title":    (13, FONT_SERIF, 700),
    "chip_kinase":   (14, FONT_SERIF, 700),
    "chip_label":    (11, FONT_SANS,  700),
    "body_desc":     (10, FONT_SANS,  500),
    "micro_numeric": (10, FONT_SANS,  700),
    "footer_read":   (12, FONT_SANS,  500),
    "footer_italic": (11, FONT_SERIF, 500),
    "kicker_mini":   (9,  FONT_SANS,  700),
    "source_tag":    (10, FONT_SANS,  700),
}


# ═════════════════════════════════════════════════════════════════
# Palette · JOURNAL_IVORY
# ═════════════════════════════════════════════════════════════════

JOURNAL_IVORY = Palette(
    name="Journal Ivory · Deep Indigo / Jade",
    bg="#F7F3E8",
    bg_alt="#EFE8D2",
    bg_dim="#E3D8B6",
    ink="#1A1A2E",
    gray="rgba(26,26,46,0.60)",
    hair="#1A1A2E",                # opacity 靠属性叠加
    primary=HUE["rust"],           # 深靛 #1E2A5E
    primary_dim=HUE["blue"],       # mid indigo
    accent=HUE["orange"],          # 玉青 #4A7C6E · accent (anomaly)
    accent_dim=HUE["olive"],       # 深橄榄墨
    positive=HUE["green"],         # deep sage
    negative=HUE["magenta"],       # 深紫红
    head_family=FONT_SERIF,        # EB Garamond (HANDBOOK §4)
    body_family=FONT_SANS,         # Inter
    mono_family=FONT_SANS,
    kicker_letter_spacing=2.8,
    kicker_case="upper",
    section_numbering="arabic",
    folio_style="hairline",
    title_style="serif_bold",
    subtitle_style="sans_italic",
    figure_caption_prefix="Fig.",
    signature_note="JOURNAL IVORY · DEEP INDIGO / JADE",
)

# preset 约定名 · 每个 skin 必须导出 PALETTE 单例
PALETTE = JOURNAL_IVORY


# ═════════════════════════════════════════════════════════════════
# Filter / gradient / marker (id prefix 统一用 ea-)
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
        'stroke="rgba(26,26,46,0.85)" stroke-width="2.6"/></marker>'
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
# 首版复用 editorial_atelier 的几何 · 只替换配色与字型 (象牙 / 深靛 / 玉青)
# ═════════════════════════════════════════════════════════════════

def svg_defs(hues: Sequence[str] = HUE_ORDER,
             include_markers: bool = True,
             include_gradients: bool = True) -> str:
    """一次注入 3 filter + hue gradient + hue marker · <defs> 段。

    preset 在渲染前置调用 · 生成的字符串直接拼进 SVG 头。
    id 前缀 `ea-` 与 editorial_atelier / boardroom_navy 共用同一命名空间。
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
                palette: Palette = JOURNAL_IVORY,
                canvas: CanvasProfile = HERO_CANVAS,
                include_bg: bool = True) -> str:
    """顶部 chrome (title + subtitle + hair + column headers)。

    canvas=EMBED 时字号缩到 embed 尺度 (title 17 · subtitle 10 · section 8)。
    与 editorial_atelier.hero_chrome 几何一致 · 颜色改用 journal_ivory palette。
    title / column_header 走 EB Garamond (SERIF)，Nature figure 感。
    """
    is_embed = (canvas.w == 900 and canvas.h == 336)
    title_sz = 17 if is_embed else 26
    subtitle_sz = 10 if is_embed else 13
    section_sz = 8 if is_embed else 10
    kicker_sz = 8 if is_embed else 10
    parts: List[str] = []
    # 背景
    if include_bg:
        parts.append(_rect(0, 0, canvas.w, canvas.h, fill=palette.bg))
    # kicker (小字上方) · 用户可以留空
    if kicker:
        parts.append(_txt(canvas.margin_x, canvas.title_y - 20, kicker,
                          size=kicker_sz, family=FONT_SANS, weight=700,
                          fill=palette.primary, letter_em=0.22))
    # title · 走 SERIF (EB Garamond) · HANDBOOK §4 硬要求
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
                       stroke=palette.hair, sw=0.6, opacity=0.28))
    # column headers · fill 用 accent (玉青) tint · 学术极简
    if column_headers:
        for lbl, cx in column_headers:
            parts.append(_txt(cx, canvas.section_hdr_y, lbl,
                              size=section_sz, family=FONT_SANS, weight=700,
                              fill=_tint(HUE["orange"], 0.95),
                              anchor="middle", letter_em=0.26))
    # 顶右侧 encoding
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
                palette: Palette = JOURNAL_IVORY,
                canvas: CanvasProfile = HERO_CANVAS,
                min_read_chars: int = 40) -> str:
    """底部 chrome — 已按用户指令关闭渲染 · 与 editorial_atelier 保持一致 (return "")。

    参数保留 · 签名不变 · preset 调用方无需改动。
    """
    _ = (caption, source, read_lines, italic_last, palette, canvas, min_read_chars)
    return ""


def tspan(word: str, *, color: str = HUE["orange"], weight: int = 700) -> str:
    """READ 段内高亮 · fill 用 hue key 或 hex。

    默认色改为玉青（学术 accent 惯例 · anomaly / 3-cycle）· 与 editorial 的 rust 默认对应。
    """
    c = _resolve_hue(color) if not color.startswith("rgba") else color
    return (f'<tspan font-weight="{weight}" fill="{c}">'
            f'{esc(word)}</tspan>')


# ═════════════════════════════════════════════════════════════════
# Skin 契约 · draw_node · opt-in 分流
# 视觉核心: 象牙纸 + 深靛 + 玉青/学术金 · EB Garamond 大字号 · 极简 rx=0
# § 章节标记 · 学术 journal 排版
# 3 kind: category_card / kpi_card / problem_statement
# ═════════════════════════════════════════════════════════════════

class JournalIvorySkin:
    """Journal Ivory · 学术期刊 · EB Garamond + § chapter mark + 深靛."""

    name = "journal_ivory"

    def draw_node(self, x: float, y: float, w: float, h: float,
                  label: str, palette: Palette,
                  kind: str = "", **kwargs) -> Optional[str]:
        pal = palette or JOURNAL_IVORY
        if kind == "category_card":
            return self._category_card(x, y, w, h, label, pal, **kwargs)
        if kind == "kpi_card":
            return self._kpi_card(x, y, w, h, label, pal, **kwargs)
        if kind == "problem_statement":
            return self._problem_statement(x, y, w, h, pal, label=label, **kwargs)
        # ── tree preset · 期刊风: 象牙 + 深靛 · § 章节标记 · 深靛竖线 ──
        if kind == "tree_pillar_card":
            return self._tree_pillar_card(x, y, w, h, pal, **kwargs)
        if kind == "tree_cap_card":
            return self._tree_cap_card(x, y, w, h, pal, **kwargs)
        if kind == "tree_root_pill":
            return self._tree_root_pill(x, y, w, h, pal, **kwargs)
        # ── kp_kpi preset (象牙 + 深靛 + § 期刊感) ──
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

    # ─────────── category_card · § 章节标记 · EB Garamond ───────────
    def _category_card(self, x, y, w, h, label, pal, **kw) -> str:
        indigo = _resolve_hue("rust")        # 深靛
        jade = _resolve_hue("orange")        # 玉青 (accent slot)
        subtitle = kw.get("subtitle", "")
        pct = kw.get("pct", "")
        parts: List[str] = []
        # 纯象牙底 · rx=0 · 顶部单细深靛横线 (期刊分类栏)
        parts.append(
            f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x + w:.1f}" y2="{y:.1f}" '
            f'stroke="{indigo}" stroke-width="0.9"/>'
        )
        parts.append(
            f'<line x1="{x:.1f}" y1="{y + h:.1f}" '
            f'x2="{x + w:.1f}" y2="{y + h:.1f}" '
            f'stroke="{indigo}" stroke-width="0.35" opacity="0.4"/>'
        )
        # § 章节标记 · 玉青 (期刊招牌)
        parts.append(
            f'<text x="{x + 4:.1f}" y="{y + 17:.1f}" '
            f'font-family="{FONT_SERIF}" font-size="14" font-weight="500" '
            f'font-style="italic" fill="{jade}">§</text>'
        )
        # label · EB Garamond bold 深靛
        parts.append(
            f'<text x="{x + 22:.1f}" y="{y + 17:.1f}" '
            f'font-family="{FONT_SERIF}" font-size="13" font-weight="700" '
            f'fill="{indigo}" letter-spacing="0em">'
            f'{esc(label)}</text>'
        )
        if subtitle:
            parts.append(
                f'<text x="{x + 22:.1f}" y="{y + 30:.1f}" '
                f'font-family="{FONT_SERIF}" font-size="9" font-weight="400" '
                f'font-style="italic" fill="{pal.gray}">'
                f'{esc(subtitle)}</text>'
            )
        # pct · EB Garamond bold 玉青
        if pct:
            parts.append(
                f'<text x="{x + w - 4:.1f}" y="{y + 17:.1f}" '
                f'text-anchor="end" font-family="{FONT_SERIF}" '
                f'font-size="13" font-weight="700" fill="{jade}">'
                f'{esc(pct)}</text>'
            )
        return "".join(parts)

    # ─────────── kpi_card · 期刊 caption 味 · Garamond 数字 ───────────
    def _kpi_card(self, x, y, w, h, label, pal, **kw) -> str:
        indigo = _resolve_hue("rust")
        journal_gold = _resolve_hue("gold_p")   # muted 学术金
        value = kw.get("value", "")
        note = kw.get("note", "")
        parts: List[str] = []
        # 无框 · 顶部粗深靛线 (期刊分栏)
        parts.append(
            f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x + w:.1f}" y2="{y:.1f}" '
            f'stroke="{indigo}" stroke-width="1"/>'
        )
        # kicker · 学术金 uppercase 大字距 (fig 编号味)
        if label:
            parts.append(
                f'<text x="{x + 4:.1f}" y="{y + 13:.1f}" '
                f'font-family="{FONT_SERIF}" font-size="8.5" font-weight="500" '
                f'font-style="italic" fill="{journal_gold}" letter-spacing="0.22em">'
                f'{esc(label.upper())}</text>'
            )
        # value · EB Garamond bold 深靛 (期刊数据招牌)
        if value:
            parts.append(
                f'<text x="{x + 4:.1f}" y="{y + 32:.1f}" '
                f'font-family="{FONT_SERIF}" font-size="18" font-weight="700" '
                f'fill="{indigo}" letter-spacing="-0.005em">'
                f'{esc(value)}</text>'
            )
        # note · EB Garamond italic gray 右
        if note:
            parts.append(
                f'<text x="{x + w - 4:.1f}" y="{y + 32:.1f}" '
                f'text-anchor="end" font-family="{FONT_SERIF}" font-size="9.5" '
                f'font-style="italic" fill="{pal.gray}">'
                f'{esc(note)}</text>'
            )
        return "".join(parts)

    # ─────────── problem_statement · § 大章节 · 学术金 stat ───────────
    def _problem_statement(self, x, y, w, h, pal, **kw) -> str:
        indigo = _resolve_hue("rust")
        jade = _resolve_hue("orange")
        journal_gold = _resolve_hue("gold_p")
        kicker = kw.get("kicker", "ABSTRACT")
        label = kw.get("label", "")
        stat = kw.get("stat", "")
        range_txt = kw.get("range", "")
        parts: List[str] = []
        cx = x + w / 2
        # 象牙底 · rx=0 · 顶粗底细 (期刊 abstract box)
        parts.append(
            f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x + w:.1f}" y2="{y:.1f}" '
            f'stroke="{indigo}" stroke-width="1.4"/>'
        )
        parts.append(
            f'<line x1="{x:.1f}" y1="{y + h:.1f}" '
            f'x2="{x + w:.1f}" y2="{y + h:.1f}" '
            f'stroke="{indigo}" stroke-width="0.6"/>'
        )
        # kicker · EB Garamond italic 深靛
        parts.append(
            f'<text x="{cx:.1f}" y="{y + 24:.1f}" text-anchor="middle" '
            f'font-family="{FONT_SERIF}" font-size="11" font-weight="500" '
            f'font-style="italic" fill="{indigo}" letter-spacing="0.28em">'
            f'{esc(kicker)}</text>'
        )
        # § divider · 玉青
        parts.append(
            f'<text x="{cx:.1f}" y="{y + 42:.1f}" text-anchor="middle" '
            f'font-family="{FONT_SERIF}" font-size="14" font-style="italic" '
            f'fill="{jade}">§</text>'
        )
        if label:
            parts.append(
                f'<text x="{cx:.1f}" y="{y + 64:.1f}" text-anchor="middle" '
                f'font-family="{FONT_SERIF}" font-size="15" '
                f'font-weight="600" fill="{indigo}">'
                f'{esc(label)}</text>'
            )
        if stat:
            # 大 stat · EB Garamond bold 学术金
            parts.append(
                f'<text x="{cx:.1f}" y="{y + 108:.1f}" text-anchor="middle" '
                f'font-family="{FONT_SERIF}" font-size="40" font-weight="700" '
                f'fill="{journal_gold}" letter-spacing="-0.01em">'
                f'{esc(stat)}</text>'
            )
        if range_txt:
            parts.append(
                f'<text x="{cx:.1f}" y="{y + h - 18:.1f}" text-anchor="middle" '
                f'font-family="{FONT_SERIF}" font-size="10" font-style="italic" '
                f'fill="{pal.gray}">'
                f'{esc(range_txt)}</text>'
            )
        return "".join(parts)

    # ─────────── tree 系 · 象牙 + 深靛 + § 章节感 ───────────
    def _tree_pillar_card(self, x, y, w, h, pal, hue="rust", hue_color=None,
                          band_h=28, **kw) -> str:
        """journal 立柱: 象牙底 + 深靛顶带 (承载 kicker/title 白字) + 底部 § 线."""
        c = hue_color or HUE.get("blue", "#2C4370")  # journal 主色是深靛蓝, 不管传什么 hue
        parts = []
        # 主体: 象牙底 + 双 hairline (期刊边框感)
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'rx="1" fill="{pal.bg}" stroke="{pal.ink}" stroke-width="0.5"/>'
        )
        # 顶部深靛 band
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" '
            f'height="{band_h:.1f}" fill="{pal.ink}"/>'
        )
        # 底部 § 双 hairline (期刊章节尾饰)
        parts.append(
            f'<line x1="{x + 8:.1f}" y1="{y + h - 6:.1f}" '
            f'x2="{x + w - 8:.1f}" y2="{y + h - 6:.1f}" '
            f'stroke="{pal.ink}" stroke-width="0.4" opacity="0.6"/>'
        )
        parts.append(
            f'<line x1="{x + 8:.1f}" y1="{y + h - 4:.1f}" '
            f'x2="{x + w - 8:.1f}" y2="{y + h - 4:.1f}" '
            f'stroke="{pal.ink}" stroke-width="0.4" opacity="0.6"/>'
        )
        return "".join(parts)

    def _tree_cap_card(self, x, y, w, h, pal, hue="rust", hue_color=None,
                       rail_w=4, **kw) -> str:
        """journal capability: 象牙 + 左深靛竖线 (§ 章节竖标)."""
        c = hue_color or HUE.get("blue", "#2C4370")
        parts = []
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'rx="1" fill="{pal.bg}" stroke="{pal.ink}" stroke-width="0.4" opacity="0.9"/>'
        )
        # 左竖线 · § 章节标 (细双线)
        parts.append(
            f'<line x1="{x + 4:.1f}" y1="{y + 8:.1f}" '
            f'x2="{x + 4:.1f}" y2="{y + h - 8:.1f}" '
            f'stroke="{pal.ink}" stroke-width="0.5"/>'
        )
        parts.append(
            f'<line x1="{x + 6:.1f}" y1="{y + 8:.1f}" '
            f'x2="{x + 6:.1f}" y2="{y + h - 8:.1f}" '
            f'stroke="{pal.ink}" stroke-width="0.5"/>'
        )
        return "".join(parts)

    def _tree_root_pill(self, x, y, w, h, pal, hue="navy", **kw) -> str:
        """journal root: 深靛实心 + 金 hairline halo (期刊招牌)."""
        parts = []
        # halo (gold)
        parts.append(
            f'<rect x="{x - 3:.1f}" y="{y - 3:.1f}" '
            f'width="{w + 6:.1f}" height="{h + 6:.1f}" rx="12" '
            f'fill="none" stroke="{HUE.get("gold_p", "#B58A3E")}" '
            f'stroke-width="0.6" opacity="0.7"/>'
        )
        # 主体
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'rx="10" fill="{pal.ink}"/>'
        )
        return "".join(parts)

    # ─────────── kp_kpi 系 · 象牙 + 深靛 + § 期刊感 ───────────
    def _kpi_hub_card(self, x, y, w, h, pal, hue="gold_hub", **kw) -> str:
        """north-star hub · 象牙底 + 深靛边框 + 金 halo · § 双 hairline."""
        gold = HUE.get("gold_p", "#B58A3E")
        parts = []
        # halo (gold outer)
        parts.append(
            f'<rect x="{x - 3:.1f}" y="{y - 3:.1f}" '
            f'width="{w + 6:.1f}" height="{h + 6:.1f}" rx="12" '
            f'fill="none" stroke="{gold}" stroke-width="0.6" opacity="0.7"/>'
        )
        # 主体 象牙 + 深靛 stroke
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="2" '
            f'fill="{pal.bg}" stroke="{pal.ink}" stroke-width="1.5"/>'
        )
        # 顶部深靛 band
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="6" fill="{pal.ink}"/>'
        )
        # 底部 § 双 hairline
        parts.append(
            f'<line x1="{x + 10:.1f}" y1="{y + h - 6:.1f}" '
            f'x2="{x + w - 10:.1f}" y2="{y + h - 6:.1f}" '
            f'stroke="{pal.ink}" stroke-width="0.4" opacity="0.55"/>'
        )
        parts.append(
            f'<line x1="{x + 10:.1f}" y1="{y + h - 4:.1f}" '
            f'x2="{x + w - 10:.1f}" y2="{y + h - 4:.1f}" '
            f'stroke="{pal.ink}" stroke-width="0.4" opacity="0.55"/>'
        )
        return "".join(parts)

    def _kpi_driver_card(self, x, y, w, h, pal, hue="rust", **kw) -> str:
        """driver card · 象牙 + 顶部深靛 hairline + § 左双竖线 (缩短)."""
        parts = []
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'rx="1" fill="{pal.bg}" stroke="{pal.ink}" stroke-width="0.5" opacity="0.9"/>'
        )
        # 顶部深靛 hairline (2 line, 期刊感)
        parts.append(
            f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x + w:.1f}" y2="{y:.1f}" '
            f'stroke="{pal.ink}" stroke-width="1.4"/>'
        )
        parts.append(
            f'<line x1="{x + 8:.1f}" y1="{y + 3:.1f}" x2="{x + w - 8:.1f}" y2="{y + 3:.1f}" '
            f'stroke="{pal.ink}" stroke-width="0.3" opacity="0.5"/>'
        )
        return "".join(parts)

    def _kpi_leaf_card(self, x, y, w, h, pal, hue="rust", compact=False, **kw) -> str:
        """leaf card · 象牙 + § 左双竖线."""
        parts = []
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'rx="1" fill="{pal.bg}" stroke="{pal.ink}" stroke-width="0.3" opacity="0.85"/>'
        )
        # 左双竖线 (§ 章节标)
        parts.append(
            f'<line x1="{x + 3:.1f}" y1="{y + 4:.1f}" '
            f'x2="{x + 3:.1f}" y2="{y + h - 4:.1f}" '
            f'stroke="{pal.ink}" stroke-width="0.4"/>'
        )
        parts.append(
            f'<line x1="{x + 5:.1f}" y1="{y + 4:.1f}" '
            f'x2="{x + 5:.1f}" y2="{y + h - 4:.1f}" '
            f'stroke="{pal.ink}" stroke-width="0.4"/>'
        )
        return "".join(parts)


    def _bloom_tier_rect(self, x, y, w, h, pal, hue="rust", hue_color=None, **kw) -> str:
        parts = []
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'fill="{pal.bg}" stroke="{pal.ink}" stroke-width="0.5" opacity="0.9"/>'
        )
        # 左双竖线 (§ 章节)
        parts.append(
            f'<line x1="{x + 3:.1f}" y1="{y + 6:.1f}" x2="{x + 3:.1f}" y2="{y + h - 6:.1f}" '
            f'stroke="{pal.ink}" stroke-width="0.5"/>'
        )
        parts.append(
            f'<line x1="{x + 5:.1f}" y1="{y + 6:.1f}" x2="{x + 5:.1f}" y2="{y + h - 6:.1f}" '
            f'stroke="{pal.ink}" stroke-width="0.5"/>'
        )
        return "".join(parts)


    def _why_chain_card(self, x, y, w, h, pal, hue="rust", hue_color=None, is_root=False, **kw) -> str:
        gold = HUE.get("gold_p", "#B58A3E")
        parts = []
        if is_root:
            parts.append(
                f'<rect x="{x - 3:.1f}" y="{y - 3:.1f}" width="{w + 6}" height="{h + 6}" '
                f'fill="none" stroke="{gold}" stroke-width="0.6" opacity="0.7"/>'
            )
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w}" height="{h}" '
            f'rx="1" fill="{pal.bg}" stroke="{pal.ink}" stroke-width="0.5" opacity="0.9"/>'
        )
        parts.append(
            f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x + w}" y2="{y:.1f}" '
            f'stroke="{pal.ink}" stroke-width="1.4"/>'
        )
        return "".join(parts)


JOURNAL_IVORY_SKIN = JournalIvorySkin()
SKIN_INSTANCE = JOURNAL_IVORY_SKIN


__all__ = [
    # Palette
    "JOURNAL_IVORY", "PALETTE",
    # Skin class
    "JournalIvorySkin", "JOURNAL_IVORY_SKIN", "SKIN_INSTANCE",
    # Canvas
    "CanvasProfile", "HERO_CANVAS", "EMBED_CANVAS", "TX_CANVAS",
    # Tokens
    "HUE", "HUE_ORDER", "TYPE_SCALE", "FONT_SERIF", "FONT_SANS",
    # Chrome
    "svg_defs", "hero_chrome", "hero_footer", "tspan",
]
