"""
Skin · mbb_consulting · Pure-White / Burgundy MBB 咨询报告

参照 dcg_style_experiments/HANDBOOK.md §2 strategy-and-analysis token 建立：

视觉核心：
    * bg=#FFFFFF 纯白（MBB 硬要求）· ink=#1A1A1A 近黑 · primary=#7B2532 勃艮第
    * 单色梯度（无第二色族）：勃艮第 100% / 淡红 60% / 灰阶
    * Georgia (title/节点) + Inter (label) · 咨询式衬线权威 + 无衬线数据
    * 装饰母题：Harvey ball · Fig. 图注 · 罗马小写章节标签 · 单色反白 hub
    * 首版复用 editorial_atelier 的 chrome / defs 函数几何 · 只改配色 tokens

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
# 8 支 hue · 全部收敛到勃艮第单色梯度 + 中性冷灰/暖灰（MBB 单色规则）
# 保持 key 名不变 (preset 依赖 key) · 副 hue 不引入第二色族
HUE = {
    "rust":     "#7B2532",   # 勃艮第 100% · 主色
    "orange":   "#B47278",   # 勃艮第 60% tint · 淡红
    "magenta":  "#5A1420",   # 勃艮第 130% shade
    "blue":     "#8E5058",   # 勃艮第 75% muted · 无蓝色相
    "green":    "#3C1017",   # 勃艮第 150% deepest · 无绿色相
    "olive":    "#8A8479",   # 暖中灰 · 纯中性
    "cinnamon": "#6B6B6B",   # 中灰 · 纯中性
    "gold_p":   "#7B2532",   # accent = 主色 · MBB 单色硬规则
    "slate":    "#322D37",   # mbb slate · 勃艮第基底冷灰 · 单色规则下的深中性
}

HUE_ORDER: Tuple[str, ...] = (
    "rust", "orange", "magenta", "blue", "green", "olive", "cinnamon",
)


# ─────────── Typography ───────────
# Georgia (标题 / 节点名 · MBB 衬线权威) + Inter (标签 / 数据 · 无衬线现代)
FONT_SANS = "Inter, Söhne, Helvetica Neue, sans-serif"
FONT_SERIF = "Georgia, GT Sectra, serif"

TYPE_SCALE = {
    "title":         (26, FONT_SERIF, 700),
    "subtitle":      (13, FONT_SANS,  500),
    "section":       (10, FONT_SANS,  700),
    "column_header": (10, FONT_SANS,  700),
    "hub_name":      (19, FONT_SERIF, 800),
    "hub_name_xl":   (26, FONT_SERIF, 800),
    "block_title":   (17, FONT_SERIF, 700),
    "card_title":    (13, FONT_SERIF, 800),
    "chip_kinase":   (14, FONT_SERIF, 800),
    "chip_label":    (11, FONT_SANS,  700),
    "body_desc":     (10, FONT_SANS,  500),
    "micro_numeric": (10, FONT_SANS,  700),
    "footer_read":   (12, FONT_SANS,  500),
    "footer_italic": (11, FONT_SERIF, 500),
    "kicker_mini":   (9,  FONT_SANS,  700),
    "source_tag":    (10, FONT_SANS,  700),
}


# ═════════════════════════════════════════════════════════════════
# Palette · MBB_CONSULTING
# ═════════════════════════════════════════════════════════════════

MBB_CONSULTING = Palette(
    name="MBB Consulting · Pure-White / Burgundy",
    bg="#FFFFFF",
    bg_alt="#FAFAFA",
    bg_dim="#F0F0F0",
    ink="#1A1A1A",
    gray="rgba(118,118,118,1)",     # #767676 · dcg_strategy 里所有次要文字都是这个灰
    hair="#1A1A1A",                 # opacity 靠属性叠加
    primary=HUE["rust"],            # 勃艮第
    primary_dim=HUE["orange"],      # 淡红 60%
    accent=HUE["rust"],             # accent 同主色 · MBB 单色规则
    accent_dim=HUE["cinnamon"],     # 中灰
    positive=HUE["rust"],           # MBB 单色不做正负色区分
    negative=HUE["magenta"],
    head_family=FONT_SERIF,         # 标题走 Georgia · MBB 衬线招牌
    body_family=FONT_SANS,
    mono_family=FONT_SANS,
    kicker_letter_spacing=2.8,
    kicker_case="upper",
    section_numbering="arabic",
    folio_style="hairline",
    title_style="serif_bold",
    subtitle_style="sans_italic",
    figure_caption_prefix="Fig.",
    signature_note="MBB CONSULTING · PURE-WHITE / BURGUNDY",
)

# preset 约定名 · 每个 skin 必须导出 PALETTE 单例
PALETTE = MBB_CONSULTING


# ═════════════════════════════════════════════════════════════════
# Filter / gradient / marker (id prefix 用 ea- 与其他 skin 兼容)
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
        'stroke="rgba(26,26,26,0.85)" stroke-width="2.6"/></marker>'
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
# 首版复用 editorial_atelier 的几何 · 只替换配色 (纯白 / 勃艮第 / 近黑)
# ═════════════════════════════════════════════════════════════════

def svg_defs(hues: Sequence[str] = HUE_ORDER,
             include_markers: bool = True,
             include_gradients: bool = True) -> str:
    """一次注入 3 filter + hue gradient + hue marker · <defs> 段。

    preset 在渲染前置调用 · 生成的字符串直接拼进 SVG 头。
    id 前缀 `ea-` 与其他 skin 保持一致 · 同页共存需注意 id 冲突。
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
                palette: Palette = MBB_CONSULTING,
                canvas: CanvasProfile = HERO_CANVAS,
                include_bg: bool = True) -> str:
    """顶部 chrome (title + subtitle + hair + column headers)。

    canvas=EMBED 时字号缩到 embed 尺度 (title 17 · subtitle 10 · section 8)。
    与 editorial_atelier.hero_chrome 几何一致 · 颜色改用 MBB palette。
    title 使用 Georgia serif · 咨询报告招牌。
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
    # title · Georgia serif（MBB 招牌）
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
    # column headers · fill 用勃艮第 tint · 与 editorial 的 rust tint 对应
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
                palette: Palette = MBB_CONSULTING,
                canvas: CanvasProfile = HERO_CANVAS,
                min_read_chars: int = 40) -> str:
    """底部 chrome — 已按用户指令关闭渲染 · 与 editorial_atelier 保持一致 (return "")。

    参数保留 · 签名不变 · preset 调用方无需改动。
    """
    _ = (caption, source, read_lines, italic_last, palette, canvas, min_read_chars)
    return ""


def tspan(word: str, *, color: str = HUE["rust"], weight: int = 700) -> str:
    """READ 段内高亮 · fill 用 hue key 或 hex。

    默认色改为勃艮第（MBB 高亮惯例 · 单色系）· 与 editorial 的 rust 默认对应。
    """
    c = _resolve_hue(color) if not color.startswith("rgba") else color
    return (f'<tspan font-weight="{weight}" fill="{c}">'
            f'{esc(word)}</tspan>')


# ═════════════════════════════════════════════════════════════════
# Skin 契约的 draw_node · opt-in 分流版本
# preset 调 skin.draw_node(kind=...)· 返回 None 表示"我不接管这个 kind，
# 让 preset 走原来的裸拼 SVG 分支". 只覆盖 MBB 视觉差异最大的几个 kind:
#   - category_card    · fishbone 分类卡 (rx=0 · 纯白 · 单细勃艮第描边)
#   - kpi_card         · 顶部 KPI 带 (rx=0 · 底部 hairline · Georgia 值)
#   - problem_statement · 右侧问题陈述 (方矩形取代椭圆 · 单色)
# 其他 kind (spine / sub_line / sub_dot / category_slash / ...) 保持 None,
# 让 preset 走原路径 · 保证已有 preset 不炸.
# ═════════════════════════════════════════════════════════════════

class MBBConsultingSkin:
    """MBB 咨询风 · rx=0 直角、无 tint、无 shadow、勃艮第单色描边.

    只实现"节点视觉"层. layout 几何 (x/y/w/h) 由 preset 传入,
    class 内不改 bbox · 保证 layout 计算不受影响.
    """

    name = "mbb_consulting"

    def draw_node(self, x: float, y: float, w: float, h: float,
                  label: str, palette: Palette,
                  kind: str = "", **kwargs) -> Optional[str]:
        """按 kind 分流. 返回 None = 让 preset 走 fallback 分支."""
        pal = palette or MBB_CONSULTING
        if kind == "category_card":
            return self._category_card(x, y, w, h, label, pal, **kwargs)
        if kind == "kpi_card":
            return self._kpi_card(x, y, w, h, label, pal, **kwargs)
        if kind == "problem_statement":
            # label 作位置参数传入 · 跟 kicker/stat/range 一起交给内部实现
            return self._problem_statement(x, y, w, h, pal, label=label, **kwargs)
        # ── OSI 3 kind (opt-in · j1_osi preset 用) ──
        if kind == "osi_layer_bar":
            return self._osi_layer_bar(x, y, w, h, pal, **kwargs)
        if kind == "osi_layer_num":
            return self._osi_layer_num(x, y, label, pal, **kwargs)
        if kind == "osi_pdu_pill":
            return self._osi_pdu_pill(x, y, w, h, pal, **kwargs)
        # ── mindmap hub (opt-in · mp_mindmap preset 用) ──
        if kind == "mindmap_hub":
            return self._mindmap_hub(x, y, w, h, label, pal, **kwargs)
        # ── tree preset (rx=0 直角 + 单色勃艮第 + 无 top strip) ──
        if kind == "tree_pillar_card":
            return self._tree_pillar_card(x, y, w, h, pal, **kwargs)
        if kind == "tree_cap_card":
            return self._tree_cap_card(x, y, w, h, pal, **kwargs)
        if kind == "tree_root_pill":
            return self._tree_root_pill(x, y, w, h, pal, **kwargs)
        # ── kp_kpi preset (rx=0 白底 · 勃艮第单色 · 三线表脚) ──
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
        return None  # 未接管的 kind · preset 走 fallback

    # ─────────── category_card · fishbone 分类卡 ───────────
    def _category_card(self, x, y, w, h, label, pal, **kw) -> str:
        primary = _resolve_hue("rust")
        subtitle = kw.get("subtitle", "")
        pct = kw.get("pct", "")
        parts: List[str] = []
        # rx=0 直角 · 纯白底 · 单细勃艮第描边 (MBB 硬要求)
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w}" height="{h}" '
            f'fill="{pal.bg}" stroke="{primary}" stroke-width="0.9"/>'
        )
        # label · Georgia serif bold ink
        parts.append(
            f'<text x="{x + 10:.1f}" y="{y + 15:.1f}" '
            f'font-family="{FONT_SERIF}" font-size="15" font-weight="700" '
            f'fill="{pal.ink}" letter-spacing="0.02em">'
            f'{esc(label)}</text>'
        )
        if subtitle:
            parts.append(
                f'<text x="{x + 10:.1f}" y="{y + 28:.1f}" '
                f'font-family="{FONT_SANS}" font-size="15" '
                f'fill="{pal.gray}">{esc(subtitle)}</text>'
            )
        if pct:
            parts.append(
                f'<text x="{x + w - 8:.1f}" y="{y + 15:.1f}" '
                f'text-anchor="end" font-family="{FONT_SERIF}" '
                f'font-size="15" font-weight="700" fill="{primary}">'
                f'{esc(pct)}</text>'
            )
        return "".join(parts)

    # ─────────── kpi_card · 顶部 KPI 带 ───────────
    def _kpi_card(self, x, y, w, h, label, pal, **kw) -> str:
        primary = _resolve_hue("rust")
        value = kw.get("value", "")
        note = kw.get("note", "")
        parts: List[str] = []
        # 纯白 · 无描边 · 底部单细 hairline (MBB 三线表招牌)
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w}" height="{h}" '
            f'fill="{pal.bg}"/>'
        )
        parts.append(
            f'<line x1="{x:.1f}" y1="{y + h:.1f}" '
            f'x2="{x + w:.1f}" y2="{y + h:.1f}" '
            f'stroke="{pal.ink}" stroke-width="0.6" opacity="0.4"/>'
        )
        # kicker (letter-spaced uppercase)
        if label:
            parts.append(
                f'<text x="{x + 4:.1f}" y="{y + 12:.1f}" '
                f'font-family="{FONT_SANS}" font-size="15" font-weight="700" '
                f'fill="{pal.gray}" letter-spacing="0.14em">'
                f'{esc(label.upper())}</text>'
            )
        # value · Georgia serif bold burgundy
        if value:
            parts.append(
                f'<text x="{x + 4:.1f}" y="{y + 28:.1f}" '
                f'font-family="{FONT_SERIF}" font-size="15" font-weight="700" '
                f'fill="{primary}">{esc(value)}</text>'
            )
        # note · italic gray 右侧
        if note:
            parts.append(
                f'<text x="{x + w - 4:.1f}" y="{y + 28:.1f}" '
                f'text-anchor="end" font-family="{FONT_SANS}" font-size="15" '
                f'font-style="italic" fill="{pal.gray}">'
                f'{esc(note)}</text>'
            )
        return "".join(parts)

    # ─────────── problem_statement · 右侧问题陈述 ───────────
    # MBB 版把 fishbone 原本的椭圆换成 rx=0 矩形 · 单色勃艮第描边
    def _problem_statement(self, x, y, w, h, pal, **kw) -> str:
        primary = _resolve_hue("rust")
        kicker = kw.get("kicker", "PROBLEM STATEMENT")
        label = kw.get("label", "")
        stat = kw.get("stat", "")
        range_txt = kw.get("range", "")
        parts: List[str] = []
        cx = x + w / 2
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w}" height="{h}" '
            f'fill="{pal.bg}" stroke="{primary}" stroke-width="1.2"/>'
        )
        # kicker (letter-spaced uppercase)
        parts.append(
            f'<text x="{cx:.1f}" y="{y + 22:.1f}" text-anchor="middle" '
            f'font-family="{FONT_SANS}" font-size="15" font-weight="700" '
            f'fill="{pal.gray}" letter-spacing="0.18em">'
            f'{esc(kicker)}</text>'
        )
        parts.append(
            f'<line x1="{cx - 40:.1f}" y1="{y + 30:.1f}" '
            f'x2="{cx + 40:.1f}" y2="{y + 30:.1f}" '
            f'stroke="{pal.ink}" stroke-width="0.6" opacity="0.4"/>'
        )
        if label:
            parts.append(
                f'<text x="{cx:.1f}" y="{y + 52:.1f}" text-anchor="middle" '
                f'font-family="{FONT_SERIF}" font-size="16" font-weight="600" '
                f'fill="{pal.ink}">{esc(label)}</text>'
            )
        if stat:
            parts.append(
                f'<text x="{cx:.1f}" y="{y + 92:.1f}" text-anchor="middle" '
                f'font-family="{FONT_SERIF}" font-size="30" font-weight="700" '
                f'fill="{primary}">{esc(stat)}</text>'
            )
        if range_txt:
            parts.append(
                f'<text x="{cx:.1f}" y="{y + 115:.1f}" text-anchor="middle" '
                f'font-family="{FONT_SANS}" font-size="15" '
                f'fill="{pal.gray}">{esc(range_txt)}</text>'
            )
        return "".join(parts)

    # ═══════════════════════════════════════════════════════════
    # OSI kind · rx=0 直角 + 单细勃艮第描边 + 左勃艮第 3px 条
    # ═══════════════════════════════════════════════════════════

    def _osi_layer_bar(self, x, y, w, h, pal, **kw) -> str:
        """MBB rx=0 硬规则 · 纯白底 + 单细勃艮第 hairline + 左侧 3px 勃艮第条."""
        primary = _resolve_hue("rust")
        parts: List[str] = [
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w}" height="{h}" '
            f'fill="{pal.bg}" stroke="{primary}" stroke-width="0.7"/>',
            f'<rect x="{x:.1f}" y="{y:.1f}" width="3" height="{h}" '
            f'fill="{primary}"/>',
        ]
        return "".join(parts)

    def _osi_layer_num(self, x, y, text, pal, **kw) -> str:
        """MBB · Georgia bold 勃艮第 · tabular-num 感."""
        primary = _resolve_hue("rust")
        return (f'<text x="{x}" y="{y:.1f}" font-family="{FONT_SERIF}" '
                f'font-size="18" font-weight="700" fill="{primary}" '
                f'letter-spacing="-0.02em">{esc(text)}</text>')

    def _osi_pdu_pill(self, x, y, w, h, pal, **kw) -> str:
        """MBB · rx=0 直角 · burgundy 淡 tint 底 · 单细勃艮第描边.

        R2 fix · 之前 fill=pal.bg (bone) 使得中文 large 数据下 pill 底色几乎
        不可见 · 与其他 skin 的 chip 视觉承诺不一致 · 改用勃艮第 0.14 alpha
        tint · 保证 chip 母题可见 · 同时保持 MBB 单色规则 (不切换到 hue).
        """
        primary = _resolve_hue("rust")   # 勃艮第
        return (f'<rect x="{x:.1f}" y="{y:.1f}" '
                f'width="{w:.1f}" height="{h}" '
                f'fill="{_tint(primary, 0.14)}" '
                f'stroke="{primary}" stroke-width="1"/>')

    # ═══════════════════════════════════════════════════════════
    # mindmap kind · hub 圆 · 深勃艮第实心反白 (MBB hero 招牌)
    # ═══════════════════════════════════════════════════════════

    def _mindmap_hub(self, x, y, w, h, name, pal, **kw) -> str:
        """MBB hub · 深勃艮第实心 · Georgia bold 白字 · 无阴影 · 单细白 hairline 内环."""
        primary = _resolve_hue("rust")     # 勃艮第 #7B2532
        kicker = kw.get("kicker", "")
        stat = kw.get("stat", "")
        stat_note = kw.get("stat_note", "")
        cx = kw.get("hub_cx", x + w / 2)
        cy = kw.get("hub_cy", y + h / 2)
        r = kw.get("hub_r", w / 2)
        parts: List[str] = []
        # 深勃艮第实心圆 (MBB hero reversed-out 招牌 · 无阴影)
        parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{primary}"/>'
        )
        # 单细白 hairline 内环 (MBB 二线表味)
        parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r - 8}" fill="none" '
            f'stroke="{pal.bg}" stroke-width="0.6" opacity="0.55"/>'
        )
        # kicker · Inter uppercase 大字距 · 淡粉勃艮第 F4C8CB (MBB 反白 chip)
        if kicker:
            parts.append(
                f'<text x="{cx}" y="{cy - 32:.1f}" text-anchor="middle" '
                f'font-family="{FONT_SANS}" font-size="8.5" '
                f'fill="#F4C8CB" font-weight="700" letter-spacing="0.24em">'
                f'{esc(kicker.upper())}</text>'
            )
            parts.append(
                f'<line x1="{cx - 28}" y1="{cy - 22:.1f}" '
                f'x2="{cx + 28}" y2="{cy - 22:.1f}" '
                f'stroke="#F4C8CB" stroke-width="0.4" opacity="0.6"/>'
            )
        # name · Georgia bold 白 · 大字号 (MBB hero 反白招牌)
        if name:
            parts.append(
                f'<text x="{cx}" y="{cy + 3}" text-anchor="middle" '
                f'font-family="{FONT_SERIF}" font-size="22" '
                f'font-weight="700" fill="{pal.bg}" letter-spacing="0.02em">'
                f'{esc(name)}</text>'
            )
        # stat · Georgia bold 淡粉勃艮第
        if stat:
            parts.append(
                f'<text x="{cx}" y="{cy + 28}" text-anchor="middle" '
                f'font-family="{FONT_SERIF}" font-size="14" '
                f'font-weight="700" fill="#F4C8CB">'
                f'{esc(stat)}</text>'
            )
        # note · Inter italic 淡白
        if stat_note:
            parts.append(
                f'<text x="{cx}" y="{cy + 46:.1f}" text-anchor="middle" '
                f'font-family="{FONT_SANS}" font-size="8" '
                f'font-style="italic" fill="{pal.bg}" opacity="0.7" '
                f'letter-spacing="0.14em">'
                f'{esc(stat_note)}</text>'
            )
        return "".join(parts)

    # ─────────── tree 系 · rx=0 直角 + 勃艮第单色 + 极细 hairline ───────────
    def _tree_pillar_card(self, x, y, w, h, pal, hue="rust", hue_color=None,
                          band_h=28, **kw) -> str:
        """MBB 立柱: 纯白底 + 极细 hairline + 顶部勃艮第 band (承载 kicker/title).
        无第二色族 · 勃艮第单色主导."""
        c = hue_color or HUE.get("rust", "#7B2532")
        parts = []
        # 主体: rx=0 · 白底 · hairline stroke
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'fill="{pal.bg}" stroke="rgba(26,26,26,0.4)" stroke-width="0.5"/>'
        )
        # 顶部勃艮第 band · 承载 kicker/title 白字
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" '
            f'height="{band_h:.1f}" fill="{c}"/>'
        )
        # 底部 hairline · MBB 三线表脚
        parts.append(
            f'<line x1="{x:.1f}" y1="{y + h:.1f}" x2="{x + w:.1f}" y2="{y + h:.1f}" '
            f'stroke="rgba(26,26,26,0.8)" stroke-width="1"/>'
        )
        return "".join(parts)

    def _tree_cap_card(self, x, y, w, h, pal, hue="rust", hue_color=None,
                       rail_w=4, **kw) -> str:
        """MBB capability: 纯白 + 顶部极细勃艮第线 (无 rail)."""
        c = hue_color or HUE.get("rust", "#7B2532")
        parts = []
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'fill="{pal.bg}" stroke="rgba(26,26,26,0.35)" stroke-width="0.5"/>'
        )
        # 顶部 hairline · 无左 rail (MBB 无装饰)
        parts.append(
            f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x + w:.1f}" y2="{y:.1f}" '
            f'stroke="{c}" stroke-width="1.4"/>'
        )
        return "".join(parts)

    def _tree_root_pill(self, x, y, w, h, pal, hue="navy", **kw) -> str:
        """MBB root: 勃艮第实心块 · rx=0 · 无 halo."""
        c = HUE.get("rust", "#7B2532")
        parts = []
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'fill="{c}"/>'
        )
        return "".join(parts)

    # ─────────── kp_kpi 系 · rx=0 白 · 勃艮第单色 · 三线表 ───────────
    def _kpi_hub_card(self, x, y, w, h, pal, hue="gold_hub", **kw) -> str:
        """north-star hub · 勃艮第实心 · rx=0 · 无 halo (MBB 极简)."""
        c = HUE.get("rust", "#7B2532")
        parts = []
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'fill="{c}"/>'
        )
        return "".join(parts)

    def _kpi_driver_card(self, x, y, w, h, pal, hue="rust", **kw) -> str:
        """driver card · 白底 + 顶部勃艮第 hairline + 底部三线表脚."""
        c = HUE.get("rust", "#7B2532")
        parts = []
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'fill="{pal.bg}" stroke="rgba(26,26,26,0.35)" stroke-width="0.5"/>'
        )
        # 顶部勃艮第 2px rule bar (取代 top strip band)
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" '
            f'height="2" fill="{c}"/>'
        )
        # 底三线表脚
        parts.append(
            f'<line x1="{x:.1f}" y1="{y + h - 0.5:.1f}" '
            f'x2="{x + w:.1f}" y2="{y + h - 0.5:.1f}" '
            f'stroke="rgba(26,26,26,0.8)" stroke-width="0.8"/>'
        )
        return "".join(parts)

    def _kpi_leaf_card(self, x, y, w, h, pal, hue="rust", compact=False, **kw) -> str:
        """leaf card · 白 + 顶部勃艮第 hairline · 无左 rail."""
        c = HUE.get("rust", "#7B2532")
        parts = []
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'fill="{pal.bg}" stroke="rgba(26,26,26,0.3)" stroke-width="0.4"/>'
        )
        # 顶部单 hairline
        parts.append(
            f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x + w:.1f}" y2="{y:.1f}" '
            f'stroke="{c}" stroke-width="1"/>'
        )
        return "".join(parts)


    def _bloom_tier_rect(self, x, y, w, h, pal, hue="rust", hue_color=None, **kw) -> str:
        c = HUE.get("rust", "#7B2532")
        parts = []
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'fill="{pal.bg}" stroke="rgba(26,26,26,0.4)" stroke-width="0.5"/>'
        )
        # 左端极细勃艮第 rule
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="3" height="{h:.1f}" fill="{c}"/>'
        )
        # 底部 hairline (三线表脚)
        parts.append(
            f'<line x1="{x:.1f}" y1="{y + h:.1f}" x2="{x + w:.1f}" y2="{y + h:.1f}" '
            f'stroke="rgba(26,26,26,0.8)" stroke-width="0.6"/>'
        )
        return "".join(parts)


    def _why_chain_card(self, x, y, w, h, pal, hue="rust", hue_color=None, is_root=False, **kw) -> str:
        c = HUE.get("rust", "#7B2532")
        parts = []
        sw = "1.4" if is_root else "0.5"
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w}" height="{h}" '
            f'fill="{pal.bg}" stroke="{c}" stroke-width="{sw}"/>'
        )
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w}" height="3" fill="{c}"/>'
        )
        return "".join(parts)


MBB_CONSULTING_SKIN = MBBConsultingSkin()
# 约定名 · preset 通过 get_active_skin() 拿到 module 后, 读 SKIN_INSTANCE
# 得到实现了 draw_node 的 skin 实例. 老 skin 不导出这个属性 → preset 检测
# 到 None 后走 fallback · 保证向后兼容.
SKIN_INSTANCE = MBB_CONSULTING_SKIN


__all__ = [
    # Palette
    "MBB_CONSULTING", "PALETTE",
    # Skin class
    "MBBConsultingSkin", "MBB_CONSULTING_SKIN", "SKIN_INSTANCE",
    # Canvas
    "CanvasProfile", "HERO_CANVAS", "EMBED_CANVAS", "TX_CANVAS",
    # Tokens
    "HUE", "HUE_ORDER", "TYPE_SCALE", "FONT_SERIF", "FONT_SANS",
    # Chrome
    "svg_defs", "hero_chrome", "hero_footer", "tspan",
]
