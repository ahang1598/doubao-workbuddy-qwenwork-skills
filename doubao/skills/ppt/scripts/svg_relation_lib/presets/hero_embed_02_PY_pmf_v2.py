# Bucket H · subtract_level default "L3" (2026-09-13)
"""HERO EMBED · 02_PY_pmf V2 · dandelion brand_pyramid 风格

彻底重写: 参考 dandelion/brand_pyramid.svg 的顶级视觉:
  - 中央 5 层金字塔 · 顶尖到底渐宽 · 每层 title/sub/detail
  - 顶部 title + kicker + FIVE FLOORS 标注
  - 用户明确不要左右两侧 SOUL/BELIEFS/WHY/WHAT 问答
  - viewBox 1400×720 hero canvas

build_kwargs:
    - root_label: pyramid 总名 (不显示)
    - floors: List[(title, sub, detail, hue)] · 3-6 层 · 顶到底
    - kicker / figure_title / figure_caption / source
    - floors_note: str · 顶部左侧 "FIVE FLOORS" note
    - how_to_read: str · 底部一行 how-to-read 引导
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from ..schemas import Tree, TreeNode
from ..palettes import Palette
from ..engine import esc
from ..layouts.column_stack import column_stack_layout, LayoutOverflow, ColumnStackParams
from ..skins.editorial_atelier import (
    BONE_RUST, HUE, FONT_SANS, FONT_SERIF,
)
from ..skins._base import _fit_font_size, _wrap_lines, _is_cjk, _luminance


def _has_cjk(s: str) -> bool:
    """检测字符串是否含 CJK 字符 · 用于 italic 门控 (中文不加 italic)."""
    if not s:
        return False
    for ch in s:
        if _is_cjk(ch):
            return True
    return False


# ═════════════════════════════════════════════════════════════════
# baseline data · 对齐 dandelion/brand_pyramid.svg
# ═════════════════════════════════════════════════════════════════

BASELINE_FLOORS: List[Tuple[str, str, str, str]] = [
    # (title, sub, detail, hue)
    ("PURPOSE",     "why we exist",     "To turn everyday moments into small acts of joy.", "gold_p"),
    ("VALUES",      "what we stand for","Craft · Care · Kindness · Curiosity",              "cinnamon"),
    ("PERSONALITY", "how we behave",    "Warm · confident · curious · unhurried",           "magenta"),
    ("POSITIONING", "the promise",      "The everyday café ritual, elevated. Beans of provenance, service of warmth.", "blue"),
    ("PRODUCTS",    "what we sell",     "Golden Roast · Golden Cold Brew · Café Bar · Home Machine · Merchandise", "olive"),
]


def build_py_tree(
    root_label: str = "Golden · brand house",
    floors: Optional[List[Tuple[str, str, str, str]]] = None,
    kicker: str = "",
    figure_title: str = "Golden · brand house",
    figure_caption: str = "A single page that tells you who we are — from purpose down to the shelf.",
    source: str = "",
    floors_note: str = "each level explains the one below it",
    how_to_read: str = "",
) -> Tree:
    """Build brand_pyramid Tree.

    floors: List of (title, sub, detail, hue) · 顶到底 · 3-6 层
      hue ∈ {"gold_p","cinnamon","magenta","blue","olive","green","rust","orange"}
    """
    src = floors if floors is not None else BASELINE_FLOORS

    root = TreeNode(
        id="root", label=root_label,
        extra={
            "kicker": kicker,
            "floors_note": floors_note,
            "how_to_read": how_to_read,
        },
    )
    for i, fl in enumerate(src):
        if len(fl) == 4:
            title, sub, detail, hue = fl
        elif len(fl) == 3:
            title, sub, detail = fl
            hue = ["gold_p", "cinnamon", "magenta", "blue", "olive"][i % 5]
        elif len(fl) == 2:
            title, detail = fl
            sub, hue = "", ["gold_p", "cinnamon", "magenta", "blue", "olive"][i % 5]
        else:
            raise ValueError(f"floor tuple must be 4/3/2-item, got {len(fl)}")
        root.children.append(TreeNode(
            id=f"f{i}", label=title, group=hue,
            sublabel=sub, detail=detail,
        ))

    return Tree(
        root=root, kicker=kicker,
        figure_title=figure_title,
        figure_caption=figure_caption,
        source=source,
        encoding_note=f"{len(src)} floors",
    )


HERO_PY_DATA = build_py_tree()


# ═════════════════════════════════════════════════════════════════
# color fallback · dandelion 原色
# ═════════════════════════════════════════════════════════════════

_DANDELION_HUE = {
    "blue":     "rgba(70,86,124,1)",     # positioning: 紫青
    "cinnamon": "rgba(178,144,72,1)",    # values: 麦金
    "green":    "rgba(16,106,82,1)",
    "magenta":  "rgba(120,68,108,1)",    # personality: 紫红
    "olive":    "rgba(88,64,52,1)",      # products: 深棕
    "rust":     "rgba(152,42,55,1)",
    "orange":   "rgba(168,88,42,1)",
    "gold_p":   "rgba(212,168,88,1)",    # purpose: 金
}


def _hue(name: str, palette: Palette) -> str:
    c = HUE.get(name)
    if c and c.startswith("#"):
        return c
    return _DANDELION_HUE.get(name, _DANDELION_HUE["cinnamon"])


def _hue_rgba(name: str, palette: Palette, alpha: float = 1.0) -> str:
    c = _hue(name, palette)
    if c.startswith("#"):
        h = c.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"rgba({r},{g},{b},{alpha:.2f})"
    if c.startswith("rgba"):
        import re
        m = re.match(r"rgba\((\d+),(\d+),(\d+),[\d.]+\)", c)
        if m:
            return f"rgba({m.group(1)},{m.group(2)},{m.group(3)},{alpha:.2f})"
    return c


def _floor_text_colors(hue: str, palette: Palette) -> Tuple[str, str, str]:
    """Return title/sub/detail ink colors with enough contrast for a floor fill."""
    floor_fill = _hue(hue, palette)
    if _luminance(floor_fill) >= 155:
        return (
            "rgba(28,26,32,0.96)",
            "rgba(28,26,32,0.74)",
            "rgba(28,26,32,0.88)",
        )
    return (
        "rgba(255,249,232,0.98)",
        "rgba(255,249,232,0.86)",
        "rgba(255,249,232,0.94)",
    )


VIEW_W = 1400
VIEW_H = 720


# Bucket H (2026-09-13) · subtract_level 默认预设 · L3 = 极简 (默认)
# R5 fix (2026-09-13): L3 之前把 floor_sub + floor_detail 都 skip · 视觉信息断崖
# 5 层标签 + subtitle 空荡 · user report "信息密度断崖式下降". 修法: L3 只 skip
# floor_detail · 保留 floor_sub (每层短说明如 "why we exist" / "为什么存在") ·
# 视觉信息量 ≈ 5 tier × 2 lines = 10 lines · 密度回归合理.
_SUBTRACT_L0: List[str] = []
_SUBTRACT_L1: List[str] = ["floor_detail"]
_SUBTRACT_L2: List[str] = _SUBTRACT_L1 + ["floor_sub"]
_SUBTRACT_L3: List[str] = ["floor_detail"]
_SUBTRACT_MAP = {"L0": _SUBTRACT_L0, "L1": _SUBTRACT_L1, "L2": _SUBTRACT_L2, "L3": _SUBTRACT_L3}


def _resolve_skip_kinds(skip_kinds: Optional[List[str]], subtract_level: str) -> set:
    if skip_kinds is not None:
        return set(skip_kinds)
    return set(_SUBTRACT_MAP.get(subtract_level, _SUBTRACT_L3))


def render_hero_embed_py_pmf_v2(
    data: Tree = HERO_PY_DATA,
    palette: Palette = BONE_RUST,
    params: Optional[ColumnStackParams] = None,
    *,
    subtract_level: str = "L3",
    skip_kinds: Optional[List[str]] = None,
) -> str:
    """渲染 dandelion brand_pyramid 风格. viewBox 1400×720."""
    # [FONT-PATCH-L1] font pass-through (standalone): ea.FONT_SANS/SERIF 覆写
    _MOD_FONT = globals()
    _ORIG_FONT = {k: _MOD_FONT[k] for k in ('FONT_SANS', 'FONT_SERIF') if k in _MOD_FONT}
    try:
        from ..skins import editorial_atelier as _ea_font
        if 'FONT_SANS' in _MOD_FONT and _ea_font.FONT_SANS != _MOD_FONT['FONT_SANS']:
            _MOD_FONT['FONT_SANS'] = _ea_font.FONT_SANS
        if 'FONT_SERIF' in _MOD_FONT and _ea_font.FONT_SERIF != _MOD_FONT['FONT_SERIF']:
            _MOD_FONT['FONT_SERIF'] = _ea_font.FONT_SERIF
    except Exception:
        pass
    try:
        # [FIX-1] 收紧 pyramid 垂直范围: 原 top=130 bot=680 · 总高 550 ·
        # 经 shrunk 后 scale_y = slide_h / shrunk_h · 若 slide_h=440, shrunk_h≈669 → scale_y≈0.66 ·
        # 底部 y=680 映射到 slide_y0+440 = 542pt · 超出 lark 16:9 slide 视口 (~540pt) · 底部 2-4pt 被裁.
        # 收紧到 top=170 bot=620 (总高 450) 后 · shrunk_h≈474 · scale_y=440/474≈0.928 ·
        # 底部映射到 slide_y0 + 440 · 但同比缩放后小字号也放大, 综合结果: (1) 无底切;
        # (2) SVG-space 14pt 字号 → slide-space ~13pt (>=10pt 硬红线).
        # 覆盖后 preset 独立控制自己的垂直范围 · 不影响其它 caller (column_stack 只被 py_pmf 用).
        default_params = ColumnStackParams(
            canvas_w=1400.0, canvas_h=720.0,
            pyramid_cx=700.0,
            pyramid_top_y=208.0, pyramid_bot_y=616.0,
            pyramid_top_w=220.0, pyramid_bot_w=820.0,
            pyramid_apex_h=96.0,
            floor_gap_y=2.0,
        )
        p = params or default_params
        pal = palette or BONE_RUST

        root = getattr(data, "root", None)
        if root is None:
            raise LayoutOverflow("pyramid: no root")
        root_extra = getattr(root, "extra", {}) or {}
        floors_note = root_extra.get("floors_note", "")
        how_to_read = root_extra.get("how_to_read", "")

        positions = column_stack_layout(data, 70, 100, 1330, 690, params=p)

        _skips = _resolve_skip_kinds(skip_kinds, subtract_level)
        if _skips:
            positions = [pos for pos in positions if pos.get("kind") not in _skips]

        parts: List[str] = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {VIEW_W} {VIEW_H}">',
        ]
        parts.append(f'<rect x="0" y="0" width="{VIEW_W}" height="{VIEW_H}" '
                     f'fill="{pal.bg}"/>')

        # ── 顶部 chrome ──
        # [FIX-1] chrome 字号统一 >=14pt SVG-space · 经 atomize scale~0.72-0.93 后仍 >=10pt
        if getattr(data, "kicker", ""):
            parts.append(
                f'<text x="90" y="34" font-family="{FONT_SANS}" font-size="14" '
                f'fill="{_hue("rust", pal)}" font-weight="700" '
                f'letter-spacing="0.22em">{esc(data.kicker.upper())}</text>'
            )
        parts.append(
            f'<text x="90" y="60" font-family="{FONT_SERIF}" font-size="28" '
            f'font-weight="600" fill="{pal.ink}" letter-spacing="0.4">'
            f'{esc(data.figure_title)}</text>'
        )
        if getattr(data, "figure_caption", ""):
            parts.append(
                f'<text x="90" y="86" font-family="{FONT_SANS}" font-size="15" '
                f'fill="rgba(64,70,82,1)" letter-spacing="0.2">'
                f'{esc(data.figure_caption)}</text>'
            )
        parts.append(
            f'<line x1="90" y1="104" x2="1310" y2="104" '
            f'stroke="{pal.ink}" stroke-width="0.8"/>'
        )

        # (已按用户要求移除 · 左侧 "N FLOORS" 注解)

        # ── 金字塔切片 ──
        for pos in positions:
            if pos["kind"] != "pyramid_floor":
                continue
            c = _hue(pos["hue"], pal)
            parts.append(
                f'<path d="{pos["d"]}" fill="{c}" opacity="0.92" '
                f'stroke="{_hue_rgba(pos["hue"], pal, 0.6)}" stroke-width="0.5"/>'
            )

        # ── 每层文字 ──
        # [FIX-1] SVG-space 字号 >=14pt · 经 atomize scale~0.93 后 slide-space >=13pt
        # [FIX-2] 顶层 detail max_lines 2→4 · 避免长句静默截断 (硬红线: 不允许 content loss)
        # [FIX-4] 中文 sub 不加 italic · CJK 无 native italic · 渲染出人工倾斜
        floor_by_index = {
            pos["index"]: pos for pos in positions if pos["kind"] == "pyramid_floor"
        }
        for pos in positions:
            k = pos["kind"]
            if k == "floor_title":
                # 用金字塔当前层最窄的可用宽 (顶边) - 40px padding
                # 由于顶层最窄 · 用 w_top 保守
                # 找同 index 的 floor
                floor = floor_by_index.get(pos["index"])
                max_w = (floor.get("w_label", floor["w_top"]) - 40) if floor else 200
                title_fill, _, _ = _floor_text_colors(pos["hue"], pal)
                fs, txt = _fit_font_size(pos["text"], max_w, 22.0, min_size=16.0)
                parts.append(
                    f'<text x="{pos["cx"]}" y="{pos["y"]:.1f}" text-anchor="middle" '
                    f'font-family="{FONT_SERIF}" font-size="{fs:.1f}" '
                    f'fill="{title_fill}" font-weight="700" letter-spacing="0.5em">'
                    f'{esc(pos["text"])}</text>'
                )
            elif k == "floor_sub":
                floor = floor_by_index.get(pos["index"])
                max_w = (floor.get("w_label", floor["w_top"]) - 20) if floor else 300
                _, sub_fill, _ = _floor_text_colors(pos["hue"], pal)
                fs, txt = _fit_font_size(pos["text"], max_w, 15.0, min_size=14.0)
                # [FIX-4] CJK 不加 italic · 拉丁语系保留 italic
                italic_attr = ' font-style="italic"' if not _has_cjk(pos["text"]) else ''
                parts.append(
                    f'<text x="{pos["cx"]}" y="{pos["y"]:.1f}" text-anchor="middle" '
                    f'font-family="{FONT_SERIF}" font-size="{fs:.1f}" '
                    f'fill="{sub_fill}"{italic_attr}>'
                    f'{esc(txt)}</text>'
                )
            elif k == "floor_detail":
                floor = floor_by_index.get(pos["index"])
                max_w = (floor.get("w_label", floor["w_top"]) - 20) if floor else 500
                _, _, detail_fill = _floor_text_colors(pos["hue"], pal)
                # 顶层 (index=0) 最窄 · detail 走多行 wrap · fs=14pt SVG-space (~13pt slide)
                # max_lines 提到 4 · 避免长句被硬截断 (硬红线: 中文数据不能删)
                if pos["index"] == 0 and floor:
                    fs = 14.0
                    # char_w 用 fs * 0.55 与 _fit_font_size 一致 · 保证 wrap 阈值和字号匹配
                    lines = _wrap_lines(pos["text"], max_w, char_w=fs * 0.55, max_lines=4)
                    if len(lines) >= 1:
                        line_h = fs * 1.15  # ~16.1pt
                        # [R2-FIX] 改居中为向下累进:
                        # R1 fix 用 `y_start = pos["y"] - (len(lines)-1)*line_h/2` 让 detail
                        # 相对 detail_y 垂直居中 · 但 sub_y 只比 detail_y 高 18pt SVG-space ·
                        # 一旦 lines>=2 · detail 第 1 行飞到 sub label 上方 · 三层文字堆叠成不可读的糊糊.
                        # 修法: y_start = pos["y"] (detail_y) · 后续行往下累进.
                        # sub 基线 sub_y = cy_center+4 (fs~15pt · 下沿 ~sub_y+3);
                        # 第 1 行基线 pos["y"] = cy_center+22 (fs=14pt · 上沿 ~pos["y"]-10);
                        # 间隔 sub_bottom→line1_top = 18-13 = 5pt · 无重叠.
                        # 3-floor row_h=150 · 4 行下沿 = detail_y+48+3 = cy_center+73 · y_bot=cy_center+75 · 恰好收住.
                        # 5-floor row_h=90 · 数据实测 detail 最多 2 行 · 无跨层.
                        y_start = pos["y"]
                        for li, line in enumerate(lines):
                            parts.append(
                                f'<text x="{pos["cx"]}" y="{y_start + li * line_h:.1f}" '
                                f'text-anchor="middle" font-family="{FONT_SANS}" '
                                f'font-size="{fs:.1f}" fill="{detail_fill}" font-weight="500">'
                                f'{esc(line)}</text>'
                            )
                        continue
                fs, txt = _fit_font_size(pos["text"], max_w, 15.0, min_size=14.0)
                parts.append(
                    f'<text x="{pos["cx"]}" y="{pos["y"]:.1f}" text-anchor="middle" '
                    f'font-family="{FONT_SANS}" font-size="{fs:.1f}" '
                    f'fill="{detail_fill}" font-weight="500">'
                    f'{esc(txt)}</text>'
                )

        # (已按用户要求移除 · 底部 how-to-read 引导)
        if getattr(data, "source", ""):
            parts.append(
                f'<text x="90" y="700" font-family="{FONT_SANS}" font-size="14" '
                f'fill="rgba(115,120,132,1)">{esc(data.source)}</text>'
            )

        parts.append('</svg>')
        return "".join(parts)
    finally:
        _MOD_FONT.update(_ORIG_FONT)
__all__ = [
    "HERO_PY_DATA", "build_py_tree", "render_hero_embed_py_pmf_v2",
    "BASELINE_FLOORS",
]
