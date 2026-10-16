"""
Skin · technical_whitepaper · Cool-White / Sapphire-Blue / Vermilion-Warn 白皮书式严谨

参照 dcg_style_experiments/HANDBOOK.md §1 technical-presentation token 建立：

视觉核心：
    * bg=#F2F4F8 冷雾白 · ink=#0F1729 深墨 · primary=#003087 宝石蓝
    * IBM Plex Sans (标题/正文) + IBM Plex Mono 通道保留 (数字/标签精确感)
    * 装饰母题：CAD 四角十字定位标 · 极淡网格底纹 · tier 标尺 · Plex Mono 编号
    * 首版复用 editorial_atelier 的 chrome / defs 函数几何 · 只改配色 + 字体
    * 警戒色 #C9302C 朱红 · 只在 retry / warn 语义位使用

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
# 8 支 hue · rust slot 重新映射到宝石蓝主色 · 保持 key 名不变 (preset 依赖 key)
# 冷色调 + 单点警戒（朱红 magenta / gold_p 硬警戒场景）· 工程感
HUE = {
    "rust":     "#003087",   # 主色 · 宝石蓝（原 rust 位）
    "orange":   "#0070BA",   # mid blue · 二级
    "magenta":  "#C9302C",   # 朱红 · retry warn
    "blue":     "#3F6892",   # steel blue
    "green":    "#3C6E50",   # deep engineering green · 正 delta
    "olive":    "#64748B",   # 中性灰
    "cinnamon": "#8A94A5",   # slate gray
    "gold_p":   "#C9302C",   # 朱红 · 同 magenta · 硬警戒场景
}

HUE_ORDER: Tuple[str, ...] = (
    "rust", "orange", "magenta", "blue", "green", "olive", "cinnamon",
)


# ─────────── Typography ───────────
# IBM Plex Sans (HANDBOOK §1 硬要求) · Serif 通道保留 Plex Serif / Georgia 备用
# 主要使用 SANS · SERIF 仅作 fallback / 图注 italic 通道
FONT_SANS = "IBM Plex Sans, Inter, Söhne, Helvetica Neue, Arial, sans-serif"
FONT_SERIF = "IBM Plex Serif, Georgia, serif"

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
# Palette · TECHNICAL_WHITEPAPER
# ═════════════════════════════════════════════════════════════════

TECHNICAL_WHITEPAPER = Palette(
    name="Technical Whitepaper · Cool-White / Sapphire",
    bg="#F2F4F8",
    bg_alt="#E4E9F0",
    bg_dim="#D5DCE4",
    ink="#0F1729",
    gray="rgba(15,23,41,0.60)",
    hair="#0F1729",                # opacity 靠属性叠加
    primary=HUE["rust"],           # 宝石蓝
    primary_dim=HUE["orange"],     # mid blue
    accent=HUE["magenta"],         # 朱红 warn
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
    figure_caption_prefix="FIG.",
    signature_note="TECHNICAL WHITEPAPER · COOL-WHITE / SAPPHIRE",
)

# preset 约定名 · 每个 skin 必须导出 PALETTE 单例
PALETTE = TECHNICAL_WHITEPAPER


# ═════════════════════════════════════════════════════════════════
# Filter / gradient / marker (id prefix 用 ea- · 与 boardroom_navy 保持一致，
# 避免 preset 里硬编码的 url(#ea-*) 断裂)
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
        'stroke="rgba(15,23,41,0.85)" stroke-width="2.6"/></marker>'
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
# 首版复用 editorial_atelier 的几何 · 只替换配色 (宝石蓝 / 朱红 / 冷雾白)
# ═════════════════════════════════════════════════════════════════

def svg_defs(hues: Sequence[str] = HUE_ORDER,
             include_markers: bool = True,
             include_gradients: bool = True) -> str:
    """一次注入 3 filter + hue gradient + hue marker · <defs> 段。

    preset 在渲染前置调用 · 生成的字符串直接拼进 SVG 头。
    id 前缀统一 `ea-` · 与 boardroom_navy / editorial_atelier 共享命名空间，
    避免 preset 里硬编码的 url(#ea-*) 断裂。
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
                palette: Palette = TECHNICAL_WHITEPAPER,
                canvas: CanvasProfile = HERO_CANVAS,
                include_bg: bool = True) -> str:
    """顶部 chrome (title + subtitle + hair + column headers)。

    canvas=EMBED 时字号缩到 embed 尺度 (title 17 · subtitle 10 · section 8)。
    与 editorial_atelier.hero_chrome 几何一致 · 颜色改用 whitepaper palette。
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
    # column headers · fill 用 primary (宝石蓝) tint · 与 editorial 的 rust tint 对应
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
                          size=note_sz, family=FONT_SANS, weight=500,
                          fill=palette.gray, anchor="end", italic=True))
    return "".join(parts)


def hero_footer(*, caption: str = "",
                source: str = "",
                read_lines: Optional[Sequence[str]] = None,
                italic_last: bool = False,
                palette: Palette = TECHNICAL_WHITEPAPER,
                canvas: CanvasProfile = HERO_CANVAS,
                min_read_chars: int = 40) -> str:
    """底部 chrome — 已按用户指令关闭渲染 · 与 editorial_atelier 保持一致 (return "")。

    参数保留 · 签名不变 · preset 调用方无需改动。
    """
    _ = (caption, source, read_lines, italic_last, palette, canvas, min_read_chars)
    return ""


def tspan(word: str, *, color: str = HUE["rust"], weight: int = 700) -> str:
    """READ 段内高亮 · fill 用 hue key 或 hex。

    默认色改为宝石蓝（whitepaper 里高亮惯例）· 与 editorial 的 rust 默认对应。
    """
    c = _resolve_hue(color) if not color.startswith("rgba") else color
    return (f'<tspan font-weight="{weight}" fill="{c}">'
            f'{esc(word)}</tspan>')


# ═════════════════════════════════════════════════════════════════
# Skin 契约 · draw_node · opt-in 分流
# 3 kind: category_card / kpi_card / problem_statement
# 视觉核心: 冷白底 + 宝石蓝主导 + IBM Plex Sans 严格 · rx=2 微圆角 ·
#   严格 hairline · 单点朱红 warn (类似 arxiv/whitepaper 排版)
# ═════════════════════════════════════════════════════════════════

class TechnicalWhitepaperSkin:
    """Technical Whitepaper · Cool-White / Sapphire · 工程感白皮书 skin.

    只实现"节点视觉". layout bbox (x/y/w/h) 由 preset 传入 · class 内不改
    · 保证 layout 计算不受影响.
    """

    name = "technical_whitepaper"

    def draw_node(self, x: float, y: float, w: float, h: float,
                  label: str, palette: Palette,
                  kind: str = "", **kwargs) -> Optional[str]:
        pal = palette or TECHNICAL_WHITEPAPER
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

    # ─────────── category_card · 顶端 hue 色条 · 网格数据行 ───────────
    def _category_card(self, x, y, w, h, label, pal, **kw) -> str:
        hue = kw.get("hue", "rust")
        hue_c = _resolve_hue(hue)
        sapphire = _resolve_hue("rust")
        subtitle = kw.get("subtitle", "")
        pct = kw.get("pct", "")
        parts: List[str] = []
        # 冷雾白底 · rx=2 微圆角 (whitepaper 数据网格) · 严格 hairline
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w}" height="{h}" '
            f'rx="2" fill="{pal.bg}" stroke="{pal.hair}" stroke-width="0.5" '
            f'opacity="0.98"/>'
        )
        # 顶端 3px hue 色条 · 分类识别 (whitepaper table header 味)
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w}" height="3" '
            f'fill="{hue_c}"/>'
        )
        # label · IBM Plex Sans bold ink · 左对齐
        parts.append(
            f'<text x="{x + 10:.1f}" y="{y + 18:.1f}" '
            f'font-family="{FONT_SANS}" font-size="12" font-weight="700" '
            f'fill="{pal.ink}" letter-spacing="0.01em">'
            f'{esc(label)}</text>'
        )
        if subtitle:
            parts.append(
                f'<text x="{x + 10:.1f}" y="{y + 30:.1f}" '
                f'font-family="{FONT_SANS}" font-size="8.5" font-weight="500" '
                f'fill="{pal.gray}" letter-spacing="0.02em">'
                f'{esc(subtitle)}</text>'
            )
        # pct · tabular-num 感 · 宝石蓝右对齐
        if pct:
            parts.append(
                f'<text x="{x + w - 8:.1f}" y="{y + 18:.1f}" '
                f'text-anchor="end" font-family="{FONT_SANS}" '
                f'font-size="12" font-weight="700" fill="{sapphire}" '
                f'letter-spacing="0.02em">'
                f'{esc(pct)}</text>'
            )
        return "".join(parts)

    # ─────────── kpi_card · 上下双线 · arxiv 图表脚注味 ───────────
    def _kpi_card(self, x, y, w, h, label, pal, **kw) -> str:
        sapphire = _resolve_hue("rust")
        value = kw.get("value", "")
        note = kw.get("note", "")
        parts: List[str] = []
        # 无 fill · 上下双 hairline (学术表格标准)
        parts.append(
            f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x + w:.1f}" y2="{y:.1f}" '
            f'stroke="{pal.ink}" stroke-width="0.7" opacity="0.85"/>'
        )
        parts.append(
            f'<line x1="{x:.1f}" y1="{y + h:.1f}" '
            f'x2="{x + w:.1f}" y2="{y + h:.1f}" '
            f'stroke="{pal.ink}" stroke-width="0.5" opacity="0.4"/>'
        )
        # kicker · gray uppercase spaced · IBM Plex Sans
        if label:
            parts.append(
                f'<text x="{x + 4:.1f}" y="{y + 12:.1f}" '
                f'font-family="{FONT_SANS}" font-size="8" font-weight="700" '
                f'fill="{pal.gray}" letter-spacing="0.16em">'
                f'{esc(label.upper())}</text>'
            )
        # value · IBM Plex Sans bold 宝石蓝 (whitepaper 数据强调)
        if value:
            parts.append(
                f'<text x="{x + 4:.1f}" y="{y + 29:.1f}" '
                f'font-family="{FONT_SANS}" font-size="15" font-weight="700" '
                f'fill="{sapphire}" letter-spacing="0.01em">'
                f'{esc(value)}</text>'
            )
        # note · gray italic 右对齐 · Serif 通道走 IBM Plex Serif
        if note:
            parts.append(
                f'<text x="{x + w - 4:.1f}" y="{y + 29:.1f}" '
                f'text-anchor="end" font-family="{FONT_SERIF}" font-size="9" '
                f'font-style="italic" fill="{pal.gray}">'
                f'{esc(note)}</text>'
            )
        return "".join(parts)

    # ─────────── problem_statement · FIG 编号感 · 大 stat 朱红警戒色 ───────────
    def _problem_statement(self, x, y, w, h, pal, **kw) -> str:
        sapphire = _resolve_hue("rust")
        warn = _resolve_hue("magenta")   # 朱红 · 数据异常警戒
        kicker = kw.get("kicker", "PROBLEM STATEMENT")
        label = kw.get("label", "")
        stat = kw.get("stat", "")
        range_txt = kw.get("range", "")
        parts: List[str] = []
        cx = x + w / 2
        # 冷雾白底 · rx=2 · 单细宝石蓝 hairline (arxiv fig box)
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w}" height="{h}" '
            f'rx="2" fill="{pal.bg}" stroke="{sapphire}" stroke-width="1"/>'
        )
        # 顶端宝石蓝色带 · FIG header
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w}" height="3" '
            f'fill="{sapphire}"/>'
        )
        # kicker · gray uppercase spaced · 左上小 tag 味
        parts.append(
            f'<text x="{cx:.1f}" y="{y + 24:.1f}" text-anchor="middle" '
            f'font-family="{FONT_SANS}" font-size="9" font-weight="700" '
            f'fill="{pal.gray}" letter-spacing="0.22em">'
            f'{esc(kicker)}</text>'
        )
        parts.append(
            f'<line x1="{cx - 34:.1f}" y1="{y + 32:.1f}" '
            f'x2="{cx + 34:.1f}" y2="{y + 32:.1f}" '
            f'stroke="{pal.ink}" stroke-width="0.5" opacity="0.4"/>'
        )
        if label:
            parts.append(
                f'<text x="{cx:.1f}" y="{y + 52:.1f}" text-anchor="middle" '
                f'font-family="{FONT_SANS}" font-size="14" '
                f'font-weight="600" fill="{pal.ink}">'
                f'{esc(label)}</text>'
            )
        if stat:
            # 大 stat · 朱红 warn · IBM Plex Sans (whitepaper 数据强调)
            parts.append(
                f'<text x="{cx:.1f}" y="{y + 98:.1f}" text-anchor="middle" '
                f'font-family="{FONT_SANS}" font-size="34" font-weight="700" '
                f'fill="{warn}" letter-spacing="-0.01em">'
                f'{esc(stat)}</text>'
            )
        if range_txt:
            # range · Serif italic gray · whitepaper 图注味
            parts.append(
                f'<line x1="{cx - 44:.1f}" y1="{y + h - 34:.1f}" '
                f'x2="{cx + 44:.1f}" y2="{y + h - 34:.1f}" '
                f'stroke="{pal.ink}" stroke-width="0.5" opacity="0.35"/>'
            )
            parts.append(
                f'<text x="{cx:.1f}" y="{y + h - 18:.1f}" text-anchor="middle" '
                f'font-family="{FONT_SERIF}" font-size="9.5" font-style="italic" '
                f'fill="{pal.gray}" letter-spacing="0.03em">'
                f'{esc(range_txt)}</text>'
            )
        return "".join(parts)

    # ═══════════════════════════════════════════════════════════
    # OSI kind · 冷雾白 + 顶端 hue 色条 + IBM Plex Sans + rx=2
    # ═══════════════════════════════════════════════════════════

    def _osi_layer_bar(self, x, y, w, h, pal, **kw) -> str:
        """whitepaper · 冷雾白底 + 严格 slate hairline + 顶端 3px hue 色条."""
        hue = kw.get("hue", "rust")
        hue_c = _resolve_hue(hue)
        parts: List[str] = [
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w}" height="{h}" '
            f'rx="2" fill="{pal.bg}" stroke="{pal.hair}" stroke-width="0.5" '
            f'opacity="0.95"/>',
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w}" height="3" '
            f'fill="{hue_c}"/>',
        ]
        return "".join(parts)

    def _osi_layer_num(self, x, y, text, pal, **kw) -> str:
        """whitepaper · IBM Plex Sans bold 宝石蓝 · tabular-num."""
        sapphire = _resolve_hue("rust")
        return (f'<text x="{x}" y="{y:.1f}" font-family="{FONT_SANS}" '
                f'font-size="18" font-weight="700" fill="{sapphire}" '
                f'letter-spacing="-0.01em">{esc(text)}</text>')

    def _osi_pdu_pill(self, x, y, w, h, pal, **kw) -> str:
        """whitepaper · rx=2 微圆 · 顶端 hue 色条 · 严格 hairline."""
        hue = kw.get("hue", "rust")
        hue_c = _resolve_hue(hue)
        parts: List[str] = [
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h}" '
            f'rx="2" fill="{pal.bg}" stroke="{hue_c}" stroke-width="0.7"/>',
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="2" '
            f'rx="1" fill="{hue_c}"/>',
        ]
        return "".join(parts)


TECHNICAL_WHITEPAPER_SKIN = TechnicalWhitepaperSkin()
# 约定名 · preset 通过 get_active_skin() 拿到 module 后, 读 SKIN_INSTANCE
SKIN_INSTANCE = TECHNICAL_WHITEPAPER_SKIN


__all__ = [
    # Palette
    "TECHNICAL_WHITEPAPER", "PALETTE",
    # Skin class
    "TechnicalWhitepaperSkin", "TECHNICAL_WHITEPAPER_SKIN", "SKIN_INSTANCE",
    # Canvas
    "CanvasProfile", "HERO_CANVAS", "EMBED_CANVAS", "TX_CANVAS",
    # Tokens
    "HUE", "HUE_ORDER", "TYPE_SCALE", "FONT_SERIF", "FONT_SANS",
    # Chrome
    "svg_defs", "hero_chrome", "hero_footer", "tspan",
]
