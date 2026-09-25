"""
Skin · boardroom_navy · Warm-White / Navy / Copper 董事会仪表盘

参照 dcg_style_experiments/HANDBOOK.md §3 business-review token 建立：

视觉核心：
    * bg=#F7F3E8 暖白 · ink=#0D1B2A 深墨蓝 · accent=#C9A66B 铜金
    * Inter Display 数字对齐 (tabular-nums) 与 editorial_atelier 复用 sans/serif 通道
    * 装饰母题：三线表 · sparkline · status dot · Exhibit 图注 (后续迭代)
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
# 8 支 hue · rust slot 重新映射到深墨蓝 · 保持 key 名不变 (preset 依赖 key)
# 副 hue 保留相近色调，但整体色相偏冷、偏深、偏克制（董事会调性）
HUE = {
    "rust":     "#0D1B2A",   # 主色 · 深墨蓝（原 rust 位）
    "orange":   "#465667",   # 冷灰蓝 · 二级 (原 warm orange)
    "magenta":  "#96322D",   # 深赭红 warn · 负 delta
    "blue":     "#3A5A7C",   # 中蓝
    "green":    "#3C6E50",   # 深墨绿 · 正 delta
    "olive":    "#8A8477",   # 中性暖灰
    "cinnamon": "#64748B",   # 冷石灰
    "gold_p":   "#C9A66B",   # 铜金 · accent
    "slate":    "#253C54",   # boardroom slate · 深钢青 · 比 blue 更暗 · 董事会调性
}

HUE_ORDER: Tuple[str, ...] = (
    "rust", "orange", "magenta", "blue", "green", "olive", "cinnamon",
)


# ─────────── Typography ───────────
# 用 Inter Display（HANDBOOK 硬要求）· serif 通道保留 Georgia 供图注/exhibit italic
FONT_SANS = "Inter Display, Inter, Söhne, Helvetica Neue, Arial, sans-serif"
FONT_SERIF = "Georgia, GT Sectra, serif"

TYPE_SCALE = {
    "title":         (26, FONT_SANS,  700),
    "subtitle":      (13, FONT_SANS,  500),
    "section":       (10, FONT_SANS,  700),
    "column_header": (10, FONT_SANS,  700),
    "hub_name":      (19, FONT_SANS,  800),
    "hub_name_xl":   (26, FONT_SANS,  800),
    "block_title":   (17, FONT_SANS,  700),
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
# Palette · BOARDROOM_NAVY
# ═════════════════════════════════════════════════════════════════

BOARDROOM_NAVY = Palette(
    name="Boardroom Navy · Warm-White / Copper",
    bg="#F7F3E8",
    bg_alt="#F1EBD8",
    bg_dim="#E8DFC4",
    ink="#0D1B2A",
    gray="rgba(70,86,103,0.72)",
    hair="#0D1B2A",                # opacity 靠属性叠加
    primary=HUE["rust"],           # 深墨蓝
    primary_dim=HUE["blue"],       # 中蓝
    accent=HUE["gold_p"],          # 铜金
    accent_dim=HUE["olive"],
    positive=HUE["green"],
    negative=HUE["magenta"],
    head_family=FONT_SANS,
    body_family=FONT_SANS,
    mono_family=FONT_SANS,
    kicker_letter_spacing=2.8,
    kicker_case="upper",
    section_numbering="arabic",
    folio_style="hairline",
    title_style="sans_bold",
    subtitle_style="sans_italic",
    figure_caption_prefix="EXHIBIT",
    signature_note="BOARDROOM NAVY · WARM-WHITE / COPPER",
)

# preset 约定名 · 每个 skin 必须导出 PALETTE 单例
PALETTE = BOARDROOM_NAVY


# ═════════════════════════════════════════════════════════════════
# Filter / gradient / marker (id prefix 用 ea- 避免与 ea- 冲突)
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
        'stroke="rgba(70,86,103,0.85)" stroke-width="2.6"/></marker>'
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
# 首版复用 editorial_atelier 的几何 · 只替换配色 (深墨蓝 / 铜金 / 暖白)
# ═════════════════════════════════════════════════════════════════

def svg_defs(hues: Sequence[str] = HUE_ORDER,
             include_markers: bool = True,
             include_gradients: bool = True) -> str:
    """一次注入 3 filter + hue gradient + hue marker · <defs> 段。

    preset 在渲染前置调用 · 生成的字符串直接拼进 SVG 头。
    id 前缀 `ea-` 与 editorial_atelier 的 `ea-` 隔离 · 可同页共存。
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
                palette: Palette = BOARDROOM_NAVY,
                canvas: CanvasProfile = HERO_CANVAS,
                include_bg: bool = True) -> str:
    """顶部 chrome (title + subtitle + hair + column headers)。

    canvas=EMBED 时字号缩到 embed 尺度 (title 17 · subtitle 10 · section 8)。
    与 editorial_atelier.hero_chrome 几何一致 · 颜色改用 boardroom palette。
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
    # title
    if title:
        parts.append(_txt(canvas.margin_x, canvas.title_y, title,
                          size=title_sz, family=FONT_SANS, weight=700,
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
    # column headers · fill 用 accent (铜金) tint · 与 editorial 的 rust tint 对应
    if column_headers:
        for lbl, cx in column_headers:
            parts.append(_txt(cx, canvas.section_hdr_y, lbl,
                              size=section_sz, family=FONT_SANS, weight=700,
                              fill=_tint(HUE["gold_p"], 0.95),
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
                palette: Palette = BOARDROOM_NAVY,
                canvas: CanvasProfile = HERO_CANVAS,
                min_read_chars: int = 40) -> str:
    """底部 chrome — 已按用户指令关闭渲染 · 与 editorial_atelier 保持一致 (return "")。

    参数保留 · 签名不变 · preset 调用方无需改动。
    """
    _ = (caption, source, read_lines, italic_last, palette, canvas, min_read_chars)
    return ""


def tspan(word: str, *, color: str = HUE["gold_p"], weight: int = 700) -> str:
    """READ 段内高亮 · fill 用 hue key 或 hex。

    默认色改为铜金（board 里高亮惯例）· 与 editorial 的 rust 默认对应。
    """
    c = _resolve_hue(color) if not color.startswith("rgba") else color
    return (f'<tspan font-weight="{weight}" fill="{c}">'
            f'{esc(word)}</tspan>')


# ═════════════════════════════════════════════════════════════════
# Skin 契约 · draw_node · opt-in 分流
# 视觉核心: 暖白 + 深墨蓝 + 铜金 · 季度汇报三线表 / sparkline / tabular-num
# 3 kind: category_card / kpi_card / problem_statement
# ═════════════════════════════════════════════════════════════════

class BoardroomNavySkin:
    """Boardroom Navy · 董事会 / IB analyst note · 三线表 + 铜金 accent."""

    name = "boardroom_navy"

    def draw_node(self, x: float, y: float, w: float, h: float,
                  label: str, palette: Palette,
                  kind: str = "", **kwargs) -> Optional[str]:
        pal = palette or BOARDROOM_NAVY
        if kind == "category_card":
            return self._category_card(x, y, w, h, label, pal, **kwargs)
        if kind == "kpi_card":
            return self._kpi_card(x, y, w, h, label, pal, **kwargs)
        if kind == "problem_statement":
            return self._problem_statement(x, y, w, h, pal, label=label, **kwargs)
        # ── tree preset · 董事会三线表 + 铜金 chrome + navy 深顶带 ──
        if kind == "tree_pillar_card":
            return self._tree_pillar_card(x, y, w, h, pal, **kwargs)
        if kind == "tree_cap_card":
            return self._tree_cap_card(x, y, w, h, pal, **kwargs)
        if kind == "tree_root_pill":
            return self._tree_root_pill(x, y, w, h, pal, **kwargs)
        # ── kp_kpi preset (董事会三线表 + 铜金 · navy 顶带) ──
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

    # ─────────── category_card · 左铜金细条 + hue tag 右上 ───────────
    def _category_card(self, x, y, w, h, label, pal, **kw) -> str:
        hue = kw.get("hue", "rust")
        hue_c = _resolve_hue(hue)
        navy = _resolve_hue("rust")          # 深墨蓝
        copper = _resolve_hue("gold_p")      # 铜金
        subtitle = kw.get("subtitle", "")
        pct = kw.get("pct", "")
        parts: List[str] = []
        # 暖白 card · rx=1 微圆角 · 严格 hairline · 铜金左细条 (accent)
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w}" height="{h}" '
            f'rx="1" fill="{pal.bg}" stroke="{navy}" stroke-width="0.6" '
            f'opacity="0.98"/>'
        )
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="3" height="{h}" '
            f'fill="{copper}"/>'
        )
        # label · Inter Display bold navy
        parts.append(
            f'<text x="{x + 10:.1f}" y="{y + 16:.1f}" '
            f'font-family="{FONT_SANS}" font-size="15" font-weight="700" '
            f'fill="{navy}" letter-spacing="-0.005em">'
            f'{esc(label)}</text>'
        )
        if subtitle:
            parts.append(
                f'<text x="{x + 10:.1f}" y="{y + 28:.1f}" '
                f'font-family="{FONT_SANS}" font-size="15" font-weight="500" '
                f'fill="{pal.gray}" letter-spacing="0.02em">'
                f'{esc(subtitle)}</text>'
            )
        # pct · Georgia tabular-num 感 · 铜金右对齐 (董事会数字招牌)
        if pct:
            parts.append(
                f'<text x="{x + w - 8:.1f}" y="{y + 16:.1f}" '
                f'text-anchor="end" font-family="{FONT_SERIF}" '
                f'font-size="15" font-weight="700" fill="{copper}" '
                f'letter-spacing="-0.01em">'
                f'{esc(pct)}</text>'
            )
        return "".join(parts)

    # ─────────── kpi_card · 三线表 · Georgia 大数字 · Inter Display kicker ───────────
    def _kpi_card(self, x, y, w, h, label, pal, **kw) -> str:
        navy = _resolve_hue("rust")
        copper = _resolve_hue("gold_p")
        value = kw.get("value", "")
        note = kw.get("note", "")
        parts: List[str] = []
        # 三线表: 顶粗 (navy) + 中细 (copper) + 底细 (gray)
        parts.append(
            f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x + w:.1f}" y2="{y:.1f}" '
            f'stroke="{navy}" stroke-width="1.4"/>'
        )
        parts.append(
            f'<line x1="{x:.1f}" y1="{y + 16:.1f}" '
            f'x2="{x + w:.1f}" y2="{y + 16:.1f}" '
            f'stroke="{copper}" stroke-width="0.5" opacity="0.6"/>'
        )
        parts.append(
            f'<line x1="{x:.1f}" y1="{y + h:.1f}" '
            f'x2="{x + w:.1f}" y2="{y + h:.1f}" '
            f'stroke="{navy}" stroke-width="0.5" opacity="0.4"/>'
        )
        # kicker · Inter Display navy uppercase spaced
        if label:
            parts.append(
                f'<text x="{x + 4:.1f}" y="{y + 12:.1f}" '
                f'font-family="{FONT_SANS}" font-size="15" font-weight="700" '
                f'fill="{navy}" letter-spacing="0.16em">'
                f'{esc(label.upper())}</text>'
            )
        # value · Georgia serif bold navy · tabular-num (董事会数字招牌)
        if value:
            parts.append(
                f'<text x="{x + 4:.1f}" y="{y + 30:.1f}" '
                f'font-family="{FONT_SERIF}" font-size="16" font-weight="700" '
                f'fill="{navy}" letter-spacing="-0.005em">'
                f'{esc(value)}</text>'
            )
        # note · Georgia italic gray 右侧 (季度对比脚注味)
        if note:
            parts.append(
                f'<text x="{x + w - 4:.1f}" y="{y + 30:.1f}" '
                f'text-anchor="end" font-family="{FONT_SERIF}" font-size="15" '
                f'font-style="italic" fill="{pal.gray}">'
                f'{esc(note)}</text>'
            )
        return "".join(parts)

    # ─────────── problem_statement · Exhibit 图注味 · 铜金 stat ───────────
    def _problem_statement(self, x, y, w, h, pal, **kw) -> str:
        navy = _resolve_hue("rust")
        copper = _resolve_hue("gold_p")
        kicker = kw.get("kicker", "EXHIBIT")
        label = kw.get("label", "")
        stat = kw.get("stat", "")
        range_txt = kw.get("range", "")
        parts: List[str] = []
        cx = x + w / 2
        # 暖白 · rx=1 · 深墨蓝双 hairline (Exhibit box)
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w}" height="{h}" '
            f'rx="1" fill="{pal.bg}" stroke="{navy}" stroke-width="1.2"/>'
        )
        parts.append(
            f'<rect x="{x + 4:.1f}" y="{y + 4:.1f}" '
            f'width="{w - 8}" height="{h - 8}" '
            f'rx="0.5" fill="none" stroke="{copper}" stroke-width="0.5" '
            f'opacity="0.55"/>'
        )
        # kicker · navy uppercase 大字距 (Exhibit tag)
        parts.append(
            f'<text x="{cx:.1f}" y="{y + 26:.1f}" text-anchor="middle" '
            f'font-family="{FONT_SANS}" font-size="15" font-weight="700" '
            f'fill="{navy}" letter-spacing="0.28em">'
            f'{esc(kicker)}</text>'
        )
        parts.append(
            f'<line x1="{cx - 30:.1f}" y1="{y + 34:.1f}" '
            f'x2="{cx + 30:.1f}" y2="{y + 34:.1f}" '
            f'stroke="{copper}" stroke-width="0.6"/>'
        )
        if label:
            parts.append(
                f'<text x="{cx:.1f}" y="{y + 54:.1f}" text-anchor="middle" '
                f'font-family="{FONT_SERIF}" font-size="16" '
                f'font-weight="600" fill="{navy}">'
                f'{esc(label)}</text>'
            )
        if stat:
            # 大 stat · Georgia serif bold 铜金 (董事会 hero number)
            parts.append(
                f'<text x="{cx:.1f}" y="{y + 100:.1f}" text-anchor="middle" '
                f'font-family="{FONT_SERIF}" font-size="36" font-weight="700" '
                f'fill="{copper}" letter-spacing="-0.02em">'
                f'{esc(stat)}</text>'
            )
        if range_txt:
            parts.append(
                f'<text x="{cx:.1f}" y="{y + h - 16:.1f}" text-anchor="middle" '
                f'font-family="{FONT_SERIF}" font-size="15" font-style="italic" '
                f'fill="{pal.gray}" letter-spacing="0.02em">'
                f'{esc(range_txt)}</text>'
            )
        return "".join(parts)

    # ─────────── tree 系 · 三线表 + navy 顶带 + 铜金 chrome ───────────
    def _tree_pillar_card(self, x, y, w, h, pal, hue="rust", hue_color=None,
                          band_h=28, **kw) -> str:
        """boardroom 立柱: 暖白底 + navy 顶带 + 底部铜金三线表脚."""
        gold = HUE.get("gold_p", "#B58A3E")
        navy = pal.ink
        parts = []
        # 主体: 暖白 rx=1 · 顶线 navy + 底线 gold
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'rx="1" fill="{pal.bg}" stroke="{navy}" stroke-width="0.5"/>'
        )
        # 顶部 navy band (承载 kicker/title 白字)
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" '
            f'height="{band_h:.1f}" fill="{navy}"/>'
        )
        # 铜金 hairline · 三线表顶脚 (第二线, 距顶)
        parts.append(
            f'<line x1="{x:.1f}" y1="{y + band_h + 2:.1f}" '
            f'x2="{x + w:.1f}" y2="{y + band_h + 2:.1f}" '
            f'stroke="{gold}" stroke-width="0.6"/>'
        )
        # 底部三线表脚 (第三线, 底)
        parts.append(
            f'<line x1="{x:.1f}" y1="{y + h - 0.5:.1f}" '
            f'x2="{x + w:.1f}" y2="{y + h - 0.5:.1f}" '
            f'stroke="{navy}" stroke-width="1"/>'
        )
        return "".join(parts)

    def _tree_cap_card(self, x, y, w, h, pal, hue="rust", hue_color=None,
                       rail_w=4, **kw) -> str:
        """boardroom capability: 暖白 + 左铜金细条 + 顶底三线."""
        gold = HUE.get("gold_p", "#B58A3E")
        navy = pal.ink
        parts = []
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'rx="1" fill="{pal.bg}" stroke="{navy}" stroke-width="0.3" opacity="0.9"/>'
        )
        # 左铜金条 (细 rail · 董事会 chrome)
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{rail_w:.1f}" '
            f'height="{h:.1f}" fill="{gold}"/>'
        )
        # 顶部 hairline (三线表)
        parts.append(
            f'<line x1="{x + rail_w:.1f}" y1="{y:.1f}" '
            f'x2="{x + w:.1f}" y2="{y:.1f}" stroke="{navy}" stroke-width="0.7"/>'
        )
        parts.append(
            f'<line x1="{x + rail_w:.1f}" y1="{y + h:.1f}" '
            f'x2="{x + w:.1f}" y2="{y + h:.1f}" stroke="{navy}" stroke-width="0.7"/>'
        )
        return "".join(parts)

    def _tree_root_pill(self, x, y, w, h, pal, hue="navy", **kw) -> str:
        """boardroom root: navy 实心 + 铜金双 hairline halo."""
        gold = HUE.get("gold_p", "#B58A3E")
        parts = []
        # halo outer (double gold ring)
        parts.append(
            f'<rect x="{x - 4:.1f}" y="{y - 4:.1f}" '
            f'width="{w + 8:.1f}" height="{h + 8:.1f}" rx="14" '
            f'fill="none" stroke="{gold}" stroke-width="0.4" opacity="0.65"/>'
        )
        parts.append(
            f'<rect x="{x - 2:.1f}" y="{y - 2:.1f}" '
            f'width="{w + 4:.1f}" height="{h + 4:.1f}" rx="12" '
            f'fill="none" stroke="{gold}" stroke-width="0.4" opacity="0.85"/>'
        )
        # 主体 navy 实心
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'rx="10" fill="{pal.ink}"/>'
        )
        return "".join(parts)

    # ─────────── kp_kpi 系 · 三线表 + 铜金 + navy 顶带 ───────────
    def _kpi_hub_card(self, x, y, w, h, pal, hue="gold_hub", **kw) -> str:
        """north-star hub · navy 实心 + 铜金双 halo."""
        gold = HUE.get("gold_p", "#B58A3E")
        parts = []
        # halo (double gold)
        parts.append(
            f'<rect x="{x - 4:.1f}" y="{y - 4:.1f}" '
            f'width="{w + 8:.1f}" height="{h + 8:.1f}" rx="14" '
            f'fill="none" stroke="{gold}" stroke-width="0.4" opacity="0.6"/>'
        )
        parts.append(
            f'<rect x="{x - 2:.1f}" y="{y - 2:.1f}" '
            f'width="{w + 4:.1f}" height="{h + 4:.1f}" rx="12" '
            f'fill="none" stroke="{gold}" stroke-width="0.5" opacity="0.85"/>'
        )
        # 主体 navy 实心
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'rx="8" fill="{pal.ink}"/>'
        )
        # 顶部铜金极细线
        parts.append(
            f'<line x1="{x + 8:.1f}" y1="{y + 4:.1f}" x2="{x + w - 8:.1f}" y2="{y + 4:.1f}" '
            f'stroke="{gold}" stroke-width="0.5" opacity="0.9"/>'
        )
        return "".join(parts)

    def _kpi_driver_card(self, x, y, w, h, pal, hue="rust", **kw) -> str:
        """driver card · 暖白 + 顶部 navy hairline + 左铜金 rail + 底部三线表."""
        gold = HUE.get("gold_p", "#B58A3E")
        parts = []
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'rx="1" fill="{pal.bg}" stroke="{pal.ink}" stroke-width="0.4" opacity="0.9"/>'
        )
        # 顶部 navy 粗线 (三线表首)
        parts.append(
            f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x + w:.1f}" y2="{y:.1f}" '
            f'stroke="{pal.ink}" stroke-width="1.4"/>'
        )
        # 左铜金极细 rail
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="3" height="{h:.1f}" fill="{gold}"/>'
        )
        # 底 hairline
        parts.append(
            f'<line x1="{x:.1f}" y1="{y + h:.1f}" x2="{x + w:.1f}" y2="{y + h:.1f}" '
            f'stroke="{pal.ink}" stroke-width="0.7"/>'
        )
        return "".join(parts)

    def _kpi_leaf_card(self, x, y, w, h, pal, hue="rust", compact=False, **kw) -> str:
        """leaf card · 暖白 + 左铜金细 rail."""
        gold = HUE.get("gold_p", "#B58A3E")
        parts = []
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'rx="1" fill="{pal.bg}" stroke="{pal.ink}" stroke-width="0.3" opacity="0.85"/>'
        )
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="2.5" height="{h:.1f}" fill="{gold}"/>'
        )
        # 底 hairline
        parts.append(
            f'<line x1="{x:.1f}" y1="{y + h:.1f}" x2="{x + w:.1f}" y2="{y + h:.1f}" '
            f'stroke="{pal.ink}" stroke-width="0.5" opacity="0.6"/>'
        )
        return "".join(parts)


    def _bloom_tier_rect(self, x, y, w, h, pal, hue="rust", hue_color=None, **kw) -> str:
        gold = HUE.get("gold_p", "#B58A3E")
        parts = []
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'fill="{pal.bg}" stroke="{pal.ink}" stroke-width="0.4" opacity="0.9"/>'
        )
        # 左铜金 rail + 顶底三线表
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="4" height="{h:.1f}" fill="{gold}"/>'
        )
        parts.append(
            f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x + w:.1f}" y2="{y:.1f}" '
            f'stroke="{pal.ink}" stroke-width="1"/>'
        )
        parts.append(
            f'<line x1="{x:.1f}" y1="{y + h:.1f}" x2="{x + w:.1f}" y2="{y + h:.1f}" '
            f'stroke="{pal.ink}" stroke-width="0.7"/>'
        )
        return "".join(parts)


    def _why_chain_card(self, x, y, w, h, pal, hue="rust", hue_color=None, is_root=False, **kw) -> str:
        gold = HUE.get("gold_p", "#B58A3E")
        parts = []
        if is_root:
            parts.append(
                f'<rect x="{x - 4:.1f}" y="{y - 4:.1f}" width="{w + 8}" height="{h + 8}" '
                f'fill="none" stroke="{gold}" stroke-width="0.5" opacity="0.8"/>'
            )
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w}" height="{h}" '
            f'rx="1" fill="{pal.bg}" stroke="{pal.ink}" stroke-width="0.4" opacity="0.9"/>'
        )
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="4" height="{h}" fill="{gold}"/>'
        )
        parts.append(
            f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x + w}" y2="{y:.1f}" stroke="{pal.ink}" stroke-width="1.1"/>'
        )
        return "".join(parts)


BOARDROOM_NAVY_SKIN = BoardroomNavySkin()
SKIN_INSTANCE = BOARDROOM_NAVY_SKIN


__all__ = [
    # Palette
    "BOARDROOM_NAVY", "PALETTE",
    # Skin class
    "BoardroomNavySkin", "BOARDROOM_NAVY_SKIN", "SKIN_INSTANCE",
    # Canvas
    "CanvasProfile", "HERO_CANVAS", "EMBED_CANVAS", "TX_CANVAS",
    # Tokens
    "HUE", "HUE_ORDER", "TYPE_SCALE", "FONT_SERIF", "FONT_SANS",
    # Chrome
    "svg_defs", "hero_chrome", "hero_footer", "tspan",
]
