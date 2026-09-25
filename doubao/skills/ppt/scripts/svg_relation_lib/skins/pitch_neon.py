"""
Skin · pitch_neon · Deep-Ink / Neon-Mint / Mauve business-pitch 演示

参照 dcg_style_experiments/HANDBOOK.md §5 business-pitch token 建立：

视觉核心：
    * bg=#0F0B14 深墨底 · ink=#F5F0EA 雪白 · primary=#7FE3C4 荧光薄荷 · accent=#E85D75 pink hot
    * Playfair Display italic 作 hero 大标题 (SERIF 22-42pt) + Inter 9-13pt 正文 (SANS)
    * 装饰母题：荧光薄荷渐变 · mauve 三档 duotone 背景层次 · REVEAL 图注
    * 首版复用 editorial_atelier 的 chrome / defs 函数几何 · 只改配色

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
# 8 支 hue · rust slot 重新映射到荧光薄荷 · 保持 key 名不变 (preset 依赖 key)
# 副 hue 走 mauve duotone 三档 + pink hot warn · 整体色相冷、亮、深墨底反衬
HUE = {
    "rust":     "#7FE3C4",   # 主色 · 荧光薄荷 hero flow（原 rust 位）
    "orange":   "#B8A0AF",   # mauve 中亮 · background 1st tier (原 warm orange)
    "magenta":  "#E85D75",   # pink hot · 强调 warn / 负 delta
    "blue":     "#4A90E2",   # 亮蓝 · secondary hero
    "green":    "#6EFCB0",   # 亮青绿 · 正 delta
    "olive":    "#8E7A88",   # mauve 中 · background 2nd tier
    "cinnamon": "#5A4E58",   # mauve 暗 · background 3rd tier · muted
    "gold_p":   "#7FE3C4",   # 同 hero · accent slot 复用荧光薄荷
}

HUE_ORDER: Tuple[str, ...] = (
    "rust", "orange", "magenta", "blue", "green", "olive", "cinnamon",
)


# ─────────── Typography ───────────
# 用 Playfair Display italic 作 hero 大标题（SERIF 22-42pt）+ Inter 9-13pt 正文（SANS）
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
# Palette · PITCH_NEON
# ═════════════════════════════════════════════════════════════════

PITCH_NEON = Palette(
    name="Pitch Neon · Deep-Ink / Neon-Mint / Mauve",
    bg="#0F0B14",
    bg_alt="#1A1520",
    bg_dim="#2A2230",
    ink="#F5F0EA",
    gray="rgba(245,240,234,0.60)",
    hair="#F5F0EA",                # opacity 靠属性叠加
    primary=HUE["rust"],           # 荧光薄荷
    primary_dim=HUE["blue"],       # 亮蓝
    accent=HUE["magenta"],         # pink hot
    accent_dim=HUE["olive"],
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
    figure_caption_prefix="REVEAL",
    signature_note="PITCH NEON · DEEP-INK / NEON-MINT / MAUVE",
)

# preset 约定名 · 每个 skin 必须导出 PALETTE 单例
PALETTE = PITCH_NEON


# ═════════════════════════════════════════════════════════════════
# Filter / gradient / marker (id prefix 用 ea- 避免与 bn- / ea- 冲突)
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
        'stroke="rgba(245,240,234,0.75)" stroke-width="2.6"/></marker>'
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
# 首版复用 editorial_atelier 的几何 · 只替换配色 (深墨底 / 荧光薄荷 / 雪白)
# ═════════════════════════════════════════════════════════════════

def svg_defs(hues: Sequence[str] = HUE_ORDER,
             include_markers: bool = True,
             include_gradients: bool = True) -> str:
    """一次注入 3 filter + hue gradient + hue marker · <defs> 段。

    preset 在渲染前置调用 · 生成的字符串直接拼进 SVG 头。
    id 前缀 `ea-` 与 boardroom_navy 的 `bn-` / editorial_atelier 的 `ea-` 隔离 · 可同页共存。
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
                palette: Palette = PITCH_NEON,
                canvas: CanvasProfile = HERO_CANVAS,
                include_bg: bool = True) -> str:
    """顶部 chrome (title + subtitle + hair + column headers)。

    canvas=EMBED 时字号缩到 embed 尺度 (title 20 · subtitle 10 · section 8)。
    与 editorial_atelier.hero_chrome 几何一致 · 颜色改用 pitch_neon palette。
    title 用 Playfair italic (serif_italic) · kicker 用荧光薄荷。
    """
    is_embed = (canvas.w == 900 and canvas.h == 336)
    title_sz = 20 if is_embed else 32
    subtitle_sz = 10 if is_embed else 13
    section_sz = 8 if is_embed else 10
    kicker_sz = 8 if is_embed else 10
    parts: List[str] = []
    # 背景 · 深墨底
    if include_bg:
        parts.append(_rect(0, 0, canvas.w, canvas.h, fill=palette.bg))
    # kicker (小字上方) · 用荧光薄荷 primary
    if kicker:
        parts.append(_txt(canvas.margin_x, canvas.title_y - 20, kicker,
                          size=kicker_sz, family=FONT_SANS, weight=700,
                          fill=palette.primary, letter_em=0.22))
    # title · Playfair Display italic · 雪白 ink
    if title:
        parts.append(_txt(canvas.margin_x, canvas.title_y, title,
                          size=title_sz, family=FONT_SERIF, weight=700,
                          fill=palette.ink, letter_em=0.01, italic=True))
    # subtitle
    if subtitle:
        parts.append(_txt(canvas.margin_x, canvas.subtitle_y, subtitle,
                          size=subtitle_sz, family=FONT_SANS, weight=500,
                          fill=palette.gray, letter_em=0.04))
    # title hairline · 雪白低透明
    parts.append(_line(canvas.margin_x, canvas.title_hair_y,
                       canvas.w - canvas.margin_x, canvas.title_hair_y,
                       stroke=palette.hair, sw=0.6, opacity=0.28))
    # column headers · fill 用 primary (荧光薄荷) tint · 对应 editorial 的 rust tint
    if column_headers:
        for lbl, cx in column_headers:
            parts.append(_txt(cx, canvas.section_hdr_y, lbl,
                              size=section_sz, family=FONT_SANS, weight=700,
                              fill=_tint(HUE["rust"], 0.95),
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
                palette: Palette = PITCH_NEON,
                canvas: CanvasProfile = HERO_CANVAS,
                min_read_chars: int = 40) -> str:
    """底部 chrome — 已按用户指令关闭渲染 · 与 editorial_atelier 保持一致 (return "")。

    参数保留 · 签名不变 · preset 调用方无需改动。
    """
    _ = (caption, source, read_lines, italic_last, palette, canvas, min_read_chars)
    return ""


def tspan(word: str, *, color: str = HUE["rust"], weight: int = 700) -> str:
    """READ 段内高亮 · fill 用 hue key 或 hex。

    默认色改为荧光薄荷（pitch 里高亮惯例）· 与 editorial 的 rust 默认对应。
    """
    c = _resolve_hue(color) if not color.startswith("rgba") else color
    return (f'<tspan font-weight="{weight}" fill="{c}">'
            f'{esc(word)}</tspan>')


# ═════════════════════════════════════════════════════════════════
# Skin 契约 · draw_node · opt-in 分流
# preset 调 skin.draw_node(kind=...) · 返回 None = 走 preset fallback
# 只覆盖 fishbone 3 个高价值 kind: category_card / kpi_card / problem_statement
# 风格: 深墨底 · 荧光薄荷 hairline · Playfair Display italic 大字号 · 多层 stroke 做假 glow
# ═════════════════════════════════════════════════════════════════

class PitchNeonSkin:
    """Pitch Neon · Deep-Ink / Neon-Mint / Mauve · 融资 pitch 招牌.

    只实现"节点视觉". layout bbox (x/y/w/h) 由 preset 传入 · class 内不改
    · 保证 layout 计算不受影响.
    """

    name = "pitch_neon"

    def draw_node(self, x: float, y: float, w: float, h: float,
                  label: str, palette: Palette,
                  kind: str = "", **kwargs) -> Optional[str]:
        pal = palette or PITCH_NEON
        if kind == "category_card":
            return self._category_card(x, y, w, h, label, pal, **kwargs)
        if kind == "kpi_card":
            return self._kpi_card(x, y, w, h, label, pal, **kwargs)
        if kind == "problem_statement":
            return self._problem_statement(x, y, w, h, pal, label=label, **kwargs)
        # ── mindmap hub (opt-in · mp_mindmap preset 用) ──
        if kind == "mindmap_hub":
            return self._mindmap_hub(x, y, w, h, label, pal, **kwargs)
        # ── tree preset ──
        if kind == "tree_pillar_card":
            return self._tree_pillar_card(x, y, w, h, pal, **kwargs)
        if kind == "tree_cap_card":
            return self._tree_cap_card(x, y, w, h, pal, **kwargs)
        if kind == "tree_root_pill":
            return self._tree_root_pill(x, y, w, h, pal, **kwargs)
        # ── kp_kpi preset ──
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

    # ─────────── category_card · 深底 + 荧光 hairline + Playfair label ───────────
    def _category_card(self, x, y, w, h, label, pal, **kw) -> str:
        hue = kw.get("hue", "rust")
        hue_c = _resolve_hue(hue)      # hue 用于 kicker 编号
        neon = _resolve_hue("rust")    # 主 hero neon (荧光薄荷) 用作描边基调
        subtitle = kw.get("subtitle", "")
        pct = kw.get("pct", "")
        parts: List[str] = []
        # bg_alt 深墨紫底 · 圆角 rx=4 · 荧光 hairline
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w}" height="{h}" '
            f'rx="4" fill="{pal.bg_alt}" stroke="{neon}" stroke-width="0.9" '
            f'opacity="0.95"/>'
        )
        # 底部 accent 光带 (hue color) 做分类识别
        parts.append(
            f'<rect x="{x:.1f}" y="{y + h - 2:.1f}" width="{w}" height="2" '
            f'rx="1" fill="{hue_c}" opacity="0.85"/>'
        )
        # label · Playfair Display italic ink
        parts.append(
            f'<text x="{x + 10:.1f}" y="{y + 16:.1f}" '
            f'font-family="{FONT_SERIF}" font-size="13" font-weight="700" '
            f'font-style="italic" fill="{pal.ink}" letter-spacing="0.01em">'
            f'{esc(label)}</text>'
        )
        if subtitle:
            parts.append(
                f'<text x="{x + 10:.1f}" y="{y + 29:.1f}" '
                f'font-family="{FONT_SANS}" font-size="8.5" '
                f'fill="{pal.gray}" letter-spacing="0.06em">'
                f'{esc(subtitle)}</text>'
            )
        if pct:
            parts.append(
                f'<text x="{x + w - 8:.1f}" y="{y + 16:.1f}" '
                f'text-anchor="end" font-family="{FONT_SERIF}" '
                f'font-size="13" font-weight="700" font-style="italic" '
                f'fill="{neon}">{esc(pct)}</text>'
            )
        return "".join(parts)

    # ─────────── kpi_card · 无框 · Playfair italic 大 value ───────────
    def _kpi_card(self, x, y, w, h, label, pal, **kw) -> str:
        neon = _resolve_hue("rust")
        value = kw.get("value", "")
        note = kw.get("note", "")
        parts: List[str] = []
        # 深墨底 (跟大 bg 融为一体) · 无边框 · 只有左侧 3px 荧光竖条做视觉锚
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="3" height="{h}" '
            f'fill="{neon}"/>'
        )
        # kicker · 荧光薄荷 uppercase spaced
        if label:
            parts.append(
                f'<text x="{x + 10:.1f}" y="{y + 12:.1f}" '
                f'font-family="{FONT_SANS}" font-size="8" font-weight="700" '
                f'fill="{neon}" letter-spacing="0.18em">'
                f'{esc(label.upper())}</text>'
            )
        # value · Playfair Display italic 大字号 (pitch 招牌)
        if value:
            parts.append(
                f'<text x="{x + 10:.1f}" y="{y + 30:.1f}" '
                f'font-family="{FONT_SERIF}" font-size="18" font-weight="700" '
                f'font-style="italic" fill="{pal.ink}">'
                f'{esc(value)}</text>'
            )
        # note · italic gray 右侧
        if note:
            parts.append(
                f'<text x="{x + w - 4:.1f}" y="{y + 30:.1f}" '
                f'text-anchor="end" font-family="{FONT_SANS}" font-size="9" '
                f'font-style="italic" fill="{pal.gray}">'
                f'{esc(note)}</text>'
            )
        return "".join(parts)

    # ─────────── problem_statement · 荧光边框圆矩形 + 反白 stat ───────────
    def _problem_statement(self, x, y, w, h, pal, **kw) -> str:
        neon = _resolve_hue("rust")       # 荧光薄荷
        pink = _resolve_hue("magenta")    # pink hot warn
        kicker = kw.get("kicker", "PROBLEM STATEMENT")
        label = kw.get("label", "")
        stat = kw.get("stat", "")
        range_txt = kw.get("range", "")
        parts: List[str] = []
        cx = x + w / 2
        # 假 glow: 外层 blur stroke + 内层实 stroke
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w}" height="{h}" '
            f'rx="14" fill="none" stroke="{neon}" stroke-width="4" '
            f'opacity="0.18"/>'
        )
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w}" height="{h}" '
            f'rx="14" fill="{pal.bg_alt}" stroke="{neon}" stroke-width="1.4" '
            f'opacity="0.95"/>'
        )
        # kicker · pink hot uppercase spaced
        parts.append(
            f'<text x="{cx:.1f}" y="{y + 24:.1f}" text-anchor="middle" '
            f'font-family="{FONT_SANS}" font-size="9" font-weight="700" '
            f'fill="{pink}" letter-spacing="0.24em">'
            f'{esc(kicker)}</text>'
        )
        parts.append(
            f'<line x1="{cx - 30:.1f}" y1="{y + 32:.1f}" '
            f'x2="{cx + 30:.1f}" y2="{y + 32:.1f}" '
            f'stroke="{neon}" stroke-width="0.8" opacity="0.6"/>'
        )
        if label:
            parts.append(
                f'<text x="{cx:.1f}" y="{y + 54:.1f}" text-anchor="middle" '
                f'font-family="{FONT_SERIF}" font-size="15" font-style="italic" '
                f'font-weight="600" fill="{pal.ink}">'
                f'{esc(label)}</text>'
            )
        if stat:
            # 大 stat · Playfair italic 荧光薄荷 (pitch deck 招牌)
            parts.append(
                f'<text x="{cx:.1f}" y="{y + 100:.1f}" text-anchor="middle" '
                f'font-family="{FONT_SERIF}" font-size="42" font-weight="700" '
                f'font-style="italic" fill="{neon}">'
                f'{esc(stat)}</text>'
            )
        if range_txt:
            parts.append(
                f'<text x="{cx:.1f}" y="{y + 128:.1f}" text-anchor="middle" '
                f'font-family="{FONT_SANS}" font-size="9.5" '
                f'fill="{pal.gray}" letter-spacing="0.1em">'
                f'{esc(range_txt)}</text>'
            )
        return "".join(parts)

    # ═══════════════════════════════════════════════════════════
    # mindmap hub · 深墨紫圆 + 荧光青多层 glow + Playfair italic
    # ═══════════════════════════════════════════════════════════

    def _mindmap_hub(self, x, y, w, h, name, pal, **kw) -> str:
        neon = _resolve_hue("rust")            # 荧光薄荷
        pink = _resolve_hue("magenta")         # pink hot
        kicker = kw.get("kicker", "")
        stat = kw.get("stat", "")
        stat_note = kw.get("stat_note", "")
        cx = kw.get("hub_cx", x + w / 2)
        cy = kw.get("hub_cy", y + h / 2)
        r = kw.get("hub_r", w / 2)
        parts: List[str] = []
        # 多层 glow: 外层大 blur ring + 中层描边 + 主圆
        parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r + 12}" fill="none" '
            f'stroke="{neon}" stroke-width="6" opacity="0.12"/>'
        )
        parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r + 6}" fill="none" '
            f'stroke="{neon}" stroke-width="3" opacity="0.22"/>'
        )
        # 主圆: 深墨紫 bg_alt (跟 bg 差一档 · 有立体感)
        parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{pal.bg_alt}" '
            f'stroke="{neon}" stroke-width="1.5"/>'
        )
        # 内环虚线 · 荧光薄荷
        parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r - 12}" fill="none" '
            f'stroke="{neon}" stroke-width="0.6" opacity="0.55" '
            f'stroke-dasharray="2 4"/>'
        )
        # kicker · pink hot uppercase spaced (pitch 招牌 warn 味)
        if kicker:
            parts.append(
                f'<text x="{cx}" y="{cy - 30:.1f}" text-anchor="middle" '
                f'font-family="{FONT_SANS}" font-size="8.5" '
                f'fill="{pink}" font-weight="700" letter-spacing="0.28em">'
                f'{esc(kicker.upper())}</text>'
            )
        # name · Playfair italic 亮米白
        if name:
            parts.append(
                f'<text x="{cx}" y="{cy + 3}" text-anchor="middle" '
                f'font-family="{FONT_SERIF}" font-size="24" '
                f'font-style="italic" font-weight="700" fill="{pal.ink}" '
                f'letter-spacing="0.01em">'
                f'{esc(name)}</text>'
            )
        # stat · Playfair italic 荧光青 (pitch 大 stat 招牌)
        if stat:
            parts.append(
                f'<text x="{cx}" y="{cy + 30}" text-anchor="middle" '
                f'font-family="{FONT_SERIF}" font-size="18" '
                f'font-style="italic" font-weight="700" fill="{neon}" '
                f'letter-spacing="-0.02em">'
                f'{esc(stat)}</text>'
            )
        # note · Inter 淡米白
        if stat_note:
            parts.append(
                f'<text x="{cx}" y="{cy + 48:.1f}" text-anchor="middle" '
                f'font-family="{FONT_SANS}" font-size="7" '
                f'fill="{pal.ink}" opacity="0.55" '
                f'letter-spacing="0.22em">'
                f'{esc(stat_note.upper())}</text>'
            )
        return "".join(parts)

    # ─────────── tree 系 · 深底 + 荧光 hairline + hue glow ───────────
    def _tree_pillar_card(self, x, y, w, h, pal, hue="rust", hue_color=None,
                          band_h=28, **kw) -> str:
        """5 支立柱主 card. 深底 body + hue 顶带 (保留亮 hue, 让 preset 的
        BG_COLOR 深字仍能在 hue 上反差可读) + 荧光双 hairline halo."""
        c = hue_color or HUE.get(hue, "#7FE3C4")
        parts = []
        # halo outer (soft glow)
        parts.append(
            f'<rect x="{x - 2:.1f}" y="{y - 2:.1f}" '
            f'width="{w + 4:.1f}" height="{h + 4:.1f}" '
            f'fill="none" stroke="{c}" stroke-width="0.5" opacity="0.35"/>'
        )
        # 主体: 深底 rx=2 (rx 小 = 舞台感 / rx 大 = 电影感, 这里选低 rx)
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'rx="2" fill="rgba(26,21,32,0.85)" '
            f'stroke="{c}" stroke-width="1.4"/>'
        )
        # 顶部 hue 光带 (保留亮 hue, kicker/title 深字仍能读)
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" '
            f'height="{band_h:.1f}" fill="{c}"/>'
        )
        # 底部 hue hairline (脱离 rx 的 pitch 感)
        parts.append(
            f'<line x1="{x + 8:.1f}" y1="{y + h - 3:.1f}" '
            f'x2="{x + w - 8:.1f}" y2="{y + h - 3:.1f}" '
            f'stroke="{c}" stroke-width="0.7" opacity="0.7"/>'
        )
        return "".join(parts)

    def _tree_cap_card(self, x, y, w, h, pal, hue="rust", hue_color=None,
                       rail_w=4, **kw) -> str:
        """capability 中卡. 深底半透明 + 左 rail + 顶部 pin dot."""
        c = hue_color or HUE.get(hue, "#7FE3C4")
        parts = []
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'rx="1" fill="rgba(26,21,32,0.5)" '
            f'stroke="{c}" stroke-width="0.7" opacity="0.95"/>'
        )
        # 左 rail (变宽版, 荧光)
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{rail_w:.1f}" '
            f'height="{h:.1f}" fill="{c}"/>'
        )
        # 右上角 pin dot · pitch 感
        parts.append(
            f'<circle cx="{x + w - 5:.1f}" cy="{y + 5:.1f}" r="1.8" '
            f'fill="{c}" opacity="0.85"/>'
        )
        return "".join(parts)

    def _tree_root_pill(self, x, y, w, h, pal, hue="navy", **kw) -> str:
        """root pill. 更深底 + 荧光双 hairline halo."""
        parts = []
        # halo (outer soft ring)
        parts.append(
            f'<rect x="{x - 3:.1f}" y="{y - 3:.1f}" '
            f'width="{w + 6:.1f}" height="{h + 6:.1f}" rx="12" '
            f'fill="none" stroke="{HUE.get("gold_p", "#F5D26B")}" '
            f'stroke-width="0.6" opacity="0.55"/>'
        )
        # 主体
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'rx="8" fill="rgba(10,8,15,0.95)" '
            f'stroke="{HUE.get("gold_p", "#F5D26B")}" stroke-width="1.2"/>'
        )
        return "".join(parts)

    # ─────────── kp_kpi 系 · 深底 + hue 荧光 hairline + halo glow ───────────
    def _kpi_hub_card(self, x, y, w, h, pal, hue="gold_hub", **kw) -> str:
        """north-star hub · 深底 + 双金 halo + 顶部粗金光带."""
        gold = HUE.get("gold_p", "#F5D26B")
        parts = []
        # halo (outer + inner double)
        parts.append(
            f'<rect x="{x - 4:.1f}" y="{y - 4:.1f}" '
            f'width="{w + 8:.1f}" height="{h + 8:.1f}" rx="12" '
            f'fill="none" stroke="{gold}" stroke-width="0.5" opacity="0.4"/>'
        )
        # 主体 深底
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="2" '
            f'fill="rgba(10,8,15,0.95)" stroke="{gold}" stroke-width="1.6"/>'
        )
        # 顶部粗金光带
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" '
            f'height="6" fill="{gold}"/>'
        )
        return "".join(parts)

    def _kpi_driver_card(self, x, y, w, h, pal, hue="rust", **kw) -> str:
        """driver card · 深底半透 + 顶带 hue 荧光 + 底部 hairline halo."""
        c = HUE.get(hue, "#7FE3C4")
        parts = []
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'rx="2" fill="rgba(26,21,32,0.75)" '
            f'stroke="{c}" stroke-width="1"/>'
        )
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="4" fill="{c}"/>'
        )
        # 底 hairline halo
        parts.append(
            f'<line x1="{x + 6:.1f}" y1="{y + h - 2:.1f}" '
            f'x2="{x + w - 6:.1f}" y2="{y + h - 2:.1f}" '
            f'stroke="{c}" stroke-width="0.6" opacity="0.6"/>'
        )
        return "".join(parts)

    def _kpi_leaf_card(self, x, y, w, h, pal, hue="rust", compact=False, **kw) -> str:
        """leaf card · 更淡深底 + 左 rail (compact 保留 3px, wide 保留 4px band)."""
        c = HUE.get(hue, "#7FE3C4")
        parts = []
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'rx="1.5" fill="rgba(26,21,32,0.45)" '
            f'stroke="{c}" stroke-width="0.5" opacity="0.9"/>'
        )
        if compact:
            parts.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="3" height="{h:.1f}" fill="{c}"/>'
            )
        else:
            parts.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="3" fill="{c}"/>'
            )
        return "".join(parts)


    def _bloom_tier_rect(self, x, y, w, h, pal, hue="rust", hue_color=None, **kw) -> str:
        c = hue_color or HUE.get(hue, "#7FE3C4")
        parts = []
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'fill="rgba(26,21,32,0.85)" stroke="{c}" stroke-width="1.2"/>'
        )
        # 左端粗 hue band
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="6" height="{h:.1f}" fill="{c}"/>'
        )
        return "".join(parts)


    def _why_chain_card(self, x, y, w, h, pal, hue="rust", hue_color=None, is_root=False, **kw) -> str:
        c = hue_color or HUE.get(hue, "#7FE3C4")
        gold = HUE.get("gold_p", "#F5D26B")
        parts = []
        sw = "2" if is_root else "1"
        stroke_c = gold if is_root else c
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w}" height="{h}" '
            f'rx="2" fill="rgba(26,21,32,0.85)" stroke="{stroke_c}" stroke-width="{sw}"/>'
        )
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w}" height="5" fill="{stroke_c}"/>'
        )
        return "".join(parts)


PITCH_NEON_SKIN = PitchNeonSkin()
# 约定名 · preset 通过 get_active_skin() 拿到 module 后, 读 SKIN_INSTANCE.
# 老 skin 不导出这个属性 → preset 检测 None 走 fallback · 向后兼容.
SKIN_INSTANCE = PITCH_NEON_SKIN


__all__ = [
    # Palette
    "PITCH_NEON", "PALETTE",
    # Skin class
    "PitchNeonSkin", "PITCH_NEON_SKIN", "SKIN_INSTANCE",
    # Canvas
    "CanvasProfile", "HERO_CANVAS", "EMBED_CANVAS", "TX_CANVAS",
    # Tokens
    "HUE", "HUE_ORDER", "TYPE_SCALE", "FONT_SERIF", "FONT_SANS",
    # Chrome
    "svg_defs", "hero_chrome", "hero_footer", "tspan",
]
