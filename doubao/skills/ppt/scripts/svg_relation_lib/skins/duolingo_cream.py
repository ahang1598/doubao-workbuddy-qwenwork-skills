"""
Skin · duolingo_cream · Cream-Yellow / Academic Indigo / Duolingo Green 学习训练

参照 HANDBOOK.md §6 learning-and-training token 建立：

视觉核心：
    * bg=#FFF9E8 奶油黄（Duolingo 亲和）· ink=#1F2E5A 深靛 · primary=#3B4F8A 学院靛
    * accent=#58CC02 Duolingo 绿 (key path / recovery) · warn=#E8720C 警告橙 (retry)
    * Fraunces 14-22pt (SERIF · 节点名) + Inter 9-11pt (SANS)
    * figure_caption_prefix="LESSON"
    * 首版复用 boardroom_navy 的 chrome / defs 函数几何 · 只改配色 + 字体

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
# 8 支 hue · rust slot 重新映射到学院靛（主色）· 保持 key 名不变 (preset 依赖 key)
# 副 hue 走 Duolingo 亲和系（绿/金/pink/天蓝）+ 警告橙/肉桂/暖橄榄
HUE = {
    "rust":     "#3B4F8A",   # 学院靛 · 主色（原 rust 位）
    "orange":   "#E8720C",   # 警告橙 · retry
    "magenta":  "#E64980",   # Duolingo pink
    "blue":     "#58ACF6",   # Duolingo 天蓝
    "green":    "#58CC02",   # Duolingo 绿 · accent 1 / key path
    "olive":    "#8B8B4C",   # warm olive
    "cinnamon": "#C97D3E",   # cinnamon · 辅助 accent
    "gold_p":   "#FFC800",   # Duolingo 金
}

HUE_ORDER: Tuple[str, ...] = (
    "rust", "orange", "magenta", "blue", "green", "olive", "cinnamon",
)


# ─────────── Typography ───────────
# 学习/训练调性：Fraunces (SERIF · 节点名 14-22pt) + Inter (SANS · 9-11pt body/label)
FONT_SANS = "Inter, Söhne, Helvetica Neue, Arial, sans-serif"
FONT_SERIF = "Fraunces, Georgia, GT Sectra, serif"

TYPE_SCALE = {
    "title":         (26, FONT_SERIF, 700),
    "subtitle":      (13, FONT_SANS,  500),
    "section":       (10, FONT_SANS,  700),
    "column_header": (10, FONT_SANS,  700),
    "hub_name":      (19, FONT_SERIF, 700),
    "hub_name_xl":   (22, FONT_SERIF, 700),
    "block_title":   (17, FONT_SERIF, 700),
    "card_title":    (14, FONT_SERIF, 700),
    "chip_kinase":   (14, FONT_SERIF, 700),
    "chip_label":    (11, FONT_SANS,  700),
    "body_desc":     (10, FONT_SANS,  500),
    "micro_numeric": (10, FONT_SANS,  700),
    "footer_read":   (11, FONT_SANS,  500),
    "footer_italic": (11, FONT_SERIF, 500),
    "kicker_mini":   (9,  FONT_SANS,  700),
    "source_tag":    (10, FONT_SANS,  700),
}


# ═════════════════════════════════════════════════════════════════
# Palette · DUOLINGO_CREAM
# ═════════════════════════════════════════════════════════════════

DUOLINGO_CREAM = Palette(
    name="Duolingo Cream · Cream-Yellow / Academic Indigo / Duolingo Green",
    bg="#FFF9E8",
    bg_alt="#FFF3D6",
    bg_dim="#FBE9B8",
    ink="#1F2E5A",
    gray="rgba(31,46,90,0.65)",
    hair="#1F2E5A",                # opacity 靠属性叠加
    primary=HUE["rust"],           # 学院靛 #3B4F8A
    primary_dim=HUE["blue"],       # Duolingo 天蓝
    accent=HUE["green"],           # Duolingo 绿 #58CC02
    accent_dim=HUE["gold_p"],      # Duolingo 金
    positive=HUE["green"],
    negative=HUE["orange"],        # 警告橙
    head_family=FONT_SERIF,
    body_family=FONT_SANS,
    mono_family=FONT_SANS,
    kicker_letter_spacing=2.8,
    kicker_case="upper",
    section_numbering="arabic",
    folio_style="hairline",
    title_style="serif_bold",
    subtitle_style="sans_italic",
    figure_caption_prefix="LESSON",
    signature_note="DUOLINGO CREAM · CREAM-YELLOW / ACADEMIC INDIGO / DUOLINGO GREEN",
)

# preset 约定名 · 每个 skin 必须导出 PALETTE 单例
PALETTE = DUOLINGO_CREAM


# ═════════════════════════════════════════════════════════════════
# Filter / gradient / marker (id prefix 用 ea- 避免与 ea-/bn- 冲突)
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
        'stroke="rgba(31,46,90,0.85)" stroke-width="2.6"/></marker>'
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
# 首版复用 boardroom_navy/editorial_atelier 的几何 · 只替换配色 (奶油黄 / 学院靛 / Duolingo 绿)
# ═════════════════════════════════════════════════════════════════

def svg_defs(hues: Sequence[str] = HUE_ORDER,
             include_markers: bool = True,
             include_gradients: bool = True) -> str:
    """一次注入 3 filter + hue gradient + hue marker · <defs> 段。

    preset 在渲染前置调用 · 生成的字符串直接拼进 SVG 头。
    id 前缀 `ea-` 与 `ea-` / `bn-` 隔离 · 可同页共存。
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
                palette: Palette = DUOLINGO_CREAM,
                canvas: CanvasProfile = HERO_CANVAS,
                include_bg: bool = True) -> str:
    """顶部 chrome (title + subtitle + hair + column headers)。

    canvas=EMBED 时字号缩到 embed 尺度 (title 17 · subtitle 10 · section 8)。
    与 boardroom_navy.hero_chrome 几何一致 · 颜色改用 duolingo_cream palette。
    title 用 serif (Fraunces) · kicker/subtitle/section 用 sans (Inter)。
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
    # title · serif bold (Fraunces)
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
    # column headers · fill 用 accent (Duolingo 绿) tint
    if column_headers:
        for lbl, cx in column_headers:
            parts.append(_txt(cx, canvas.section_hdr_y, lbl,
                              size=section_sz, family=FONT_SANS, weight=700,
                              fill=_tint(HUE["green"], 0.85),
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
                palette: Palette = DUOLINGO_CREAM,
                canvas: CanvasProfile = HERO_CANVAS,
                min_read_chars: int = 40) -> str:
    """底部 chrome — 已按用户指令关闭渲染 · 与 boardroom_navy 保持一致 (return "")。

    参数保留 · 签名不变 · preset 调用方无需改动。
    """
    _ = (caption, source, read_lines, italic_last, palette, canvas, min_read_chars)
    return ""


def tspan(word: str, *, color: str = HUE["green"], weight: int = 700) -> str:
    """READ 段内高亮 · fill 用 hue key 或 hex。

    默认色改为 Duolingo 绿（learning skin 里 key-path/正反馈惯例）。
    """
    c = _resolve_hue(color) if not color.startswith("rgba") else color
    return (f'<tspan font-weight="{weight}" fill="{c}">'
            f'{esc(word)}</tspan>')


# ═════════════════════════════════════════════════════════════════
# Skin 契约 · draw_node · opt-in 分流
# 视觉核心: 奶油黄底 + 学院靛 + Duolingo 绿 · 粗圆 tile + 底部 3D 阴影条
# Fraunces 圆润 serif · 儿童友好
# 3 kind: category_card / kpi_card / problem_statement
# ═════════════════════════════════════════════════════════════════

class DuolingoCreamSkin:
    """Duolingo Cream · 教育应用 tile · 粗圆 rx=12 + 3D 阴影 + Fraunces."""

    name = "duolingo_cream"

    def draw_node(self, x: float, y: float, w: float, h: float,
                  label: str, palette: Palette,
                  kind: str = "", **kwargs) -> Optional[str]:
        pal = palette or DUOLINGO_CREAM
        if kind == "category_card":
            return self._category_card(x, y, w, h, label, pal, **kwargs)
        if kind == "kpi_card":
            return self._kpi_card(x, y, w, h, label, pal, **kwargs)
        if kind == "problem_statement":
            return self._problem_statement(x, y, w, h, pal, label=label, **kwargs)
        return None

    # ─────────── category_card · Duolingo tile · 粗圆 + 底部 3D 阴影条 ───────────
    def _category_card(self, x, y, w, h, label, pal, **kw) -> str:
        hue = kw.get("hue", "rust")
        hue_c = _resolve_hue(hue)
        indigo = _resolve_hue("rust")      # 学院靛
        subtitle = kw.get("subtitle", "")
        pct = kw.get("pct", "")
        parts: List[str] = []
        # Duolingo tile 招牌: 底部 3px 深色影子条 (给 tile 立体感)
        # 影子条 = 上层 tile 高度往下+3, 颜色取 hue 的 darker
        parts.append(
            f'<rect x="{x:.1f}" y="{y + 3:.1f}" width="{w}" height="{h}" '
            f'rx="12" fill="{indigo}" opacity="0.28"/>'
        )
        # 上层 tile: 奶油白底 · rx=12 粗圆角 · hue 描边
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w}" height="{h - 3}" '
            f'rx="12" fill="{pal.bg}" stroke="{hue_c}" stroke-width="2"/>'
        )
        # label · Fraunces 圆润 serif bold · indigo
        parts.append(
            f'<text x="{x + 12:.1f}" y="{y + 17:.1f}" '
            f'font-family="{FONT_SERIF}" font-size="13" font-weight="700" '
            f'fill="{indigo}" letter-spacing="0em">'
            f'{esc(label)}</text>'
        )
        if subtitle:
            parts.append(
                f'<text x="{x + 12:.1f}" y="{y + 29:.1f}" '
                f'font-family="{FONT_SANS}" font-size="8.5" font-weight="600" '
                f'fill="{pal.gray}" letter-spacing="0.02em">'
                f'{esc(subtitle)}</text>'
            )
        # pct · Fraunces bold hue color · 圆润数字
        if pct:
            parts.append(
                f'<text x="{x + w - 10:.1f}" y="{y + 17:.1f}" '
                f'text-anchor="end" font-family="{FONT_SERIF}" '
                f'font-size="14" font-weight="800" fill="{hue_c}">'
                f'{esc(pct)}</text>'
            )
        return "".join(parts)

    # ─────────── kpi_card · pill tile · 底部 Duolingo 绿细条 ───────────
    def _kpi_card(self, x, y, w, h, label, pal, **kw) -> str:
        indigo = _resolve_hue("rust")
        duo_green = _resolve_hue("green")    # Duolingo 绿
        value = kw.get("value", "")
        note = kw.get("note", "")
        parts: List[str] = []
        # 无框 · 底部 Duolingo 绿细条 (进度条味)
        parts.append(
            f'<line x1="{x:.1f}" y1="{y + h:.1f}" '
            f'x2="{x + w * 0.7:.1f}" y2="{y + h:.1f}" '
            f'stroke="{duo_green}" stroke-width="3" stroke-linecap="round"/>'
        )
        # kicker · indigo uppercase spaced
        if label:
            parts.append(
                f'<text x="{x + 2:.1f}" y="{y + 12:.1f}" '
                f'font-family="{FONT_SANS}" font-size="8" font-weight="700" '
                f'fill="{indigo}" letter-spacing="0.14em">'
                f'{esc(label.upper())}</text>'
            )
        # value · Fraunces 圆润 bold indigo
        if value:
            parts.append(
                f'<text x="{x + 2:.1f}" y="{y + 30:.1f}" '
                f'font-family="{FONT_SERIF}" font-size="18" font-weight="800" '
                f'fill="{indigo}" letter-spacing="-0.01em">'
                f'{esc(value)}</text>'
            )
        # note · Fraunces italic gray 右侧
        if note:
            parts.append(
                f'<text x="{x + w - 4:.1f}" y="{y + 30:.1f}" '
                f'text-anchor="end" font-family="{FONT_SERIF}" font-size="9" '
                f'font-style="italic" fill="{pal.gray}">'
                f'{esc(note)}</text>'
            )
        return "".join(parts)

    # ─────────── problem_statement · 大 tile · Duolingo 金 stat ───────────
    def _problem_statement(self, x, y, w, h, pal, **kw) -> str:
        indigo = _resolve_hue("rust")
        gold = _resolve_hue("gold_p")        # Duolingo 金 (heart)
        pink = _resolve_hue("magenta")       # Duolingo pink (warn 补色)
        kicker = kw.get("kicker", "TASK")
        label = kw.get("label", "")
        stat = kw.get("stat", "")
        range_txt = kw.get("range", "")
        parts: List[str] = []
        cx = x + w / 2
        # 大 Duolingo tile · 深影子 + 粗圆 rx=16
        parts.append(
            f'<rect x="{x:.1f}" y="{y + 4:.1f}" width="{w}" height="{h}" '
            f'rx="16" fill="{indigo}" opacity="0.28"/>'
        )
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w}" height="{h - 4}" '
            f'rx="16" fill="{pal.bg}" stroke="{indigo}" stroke-width="2.5"/>'
        )
        # kicker · pink uppercase spaced (Duolingo 提示味)
        parts.append(
            f'<text x="{cx:.1f}" y="{y + 26:.1f}" text-anchor="middle" '
            f'font-family="{FONT_SANS}" font-size="9" font-weight="700" '
            f'fill="{pink}" letter-spacing="0.24em">'
            f'{esc(kicker)}</text>'
        )
        if label:
            parts.append(
                f'<text x="{cx:.1f}" y="{y + 54:.1f}" text-anchor="middle" '
                f'font-family="{FONT_SERIF}" font-size="15" '
                f'font-weight="700" fill="{indigo}">'
                f'{esc(label)}</text>'
            )
        if stat:
            # Fraunces italic 圆润大 stat · Duolingo 金
            parts.append(
                f'<text x="{cx:.1f}" y="{y + 102:.1f}" text-anchor="middle" '
                f'font-family="{FONT_SERIF}" font-size="42" font-weight="800" '
                f'font-style="italic" fill="{gold}" letter-spacing="-0.02em">'
                f'{esc(stat)}</text>'
            )
        if range_txt:
            parts.append(
                f'<text x="{cx:.1f}" y="{y + h - 22:.1f}" text-anchor="middle" '
                f'font-family="{FONT_SANS}" font-size="9.5" font-weight="600" '
                f'fill="{pal.gray}" letter-spacing="0.06em">'
                f'{esc(range_txt)}</text>'
            )
        return "".join(parts)


DUOLINGO_CREAM_SKIN = DuolingoCreamSkin()
SKIN_INSTANCE = DUOLINGO_CREAM_SKIN


__all__ = [
    # Palette
    "DUOLINGO_CREAM", "PALETTE",
    # Skin class
    "DuolingoCreamSkin", "DUOLINGO_CREAM_SKIN", "SKIN_INSTANCE",
    # Canvas
    "CanvasProfile", "HERO_CANVAS", "EMBED_CANVAS", "TX_CANVAS",
    # Tokens
    "HUE", "HUE_ORDER", "TYPE_SCALE", "FONT_SERIF", "FONT_SANS",
    # Chrome
    "svg_defs", "hero_chrome", "hero_footer", "tspan",
]
