# Bucket H · subtract_level default "L3" (2026-09-13)
"""HERO EMBED · 05_MP_mindmap V2 · dandelion sql_tree 风格

彻底重写: 参考 dandelion/sql_tree.svg 的顶级视觉:
  - 中心圆形 hub (深墨蓝底 + 金字 + 内 dashed 环)
  - 5-8 branches 左右分布 · S 形贝塞尔曲线
  - branch card 180×46 · left hue bar + M{i}·meta kicker + name + subtitle + N LEAVES
  - leaf pill 170×22 · 色 dot + L01 编号 + name
  - 顶部 4 KPI 带
  - viewBox 1400×720 · hero canvas

build_kwargs 完整暴露:
    - root_label: hub 大字 (如 "SQL 5D")
    - kicker: 顶部 kicker (默认空)
    - figure_title: 大标题
    - figure_caption: 副标题
    - source: 底部来源
    - hub_kicker: 圆内小字 (如 "CORE CURRICULUM")
    - hub_stat: 圆内 stat (如 "25 HOURS")
    - hub_stat_note: 圆底微字 (如 "15 LESSONS · 5 MODULES")
    - kpis: List[{kicker, value, note, hue}] 顶部 4 KPI · [] 跳过
    - branches: List[(name, hue, subtitle, kicker, leaves)] · leaves 是 [(label, code)?] 或 [label]
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..schemas import Tree, TreeNode
from ..palettes import Palette
from ..engine import esc
from ..layouts.hub_fanout import hub_fanout_layout, LayoutOverflow, HubFanoutParams
from ..skins.editorial_atelier import (
    BONE_RUST, HUE, FONT_SANS, FONT_SERIF,
)
from ..skins._base import _fit_font_size, _wrap_lines, _visual_width, _luminance
from ..skins.registry import get_active_skin as _get_active_skin


# ── skin-aware 语义色 · 由 render 内 globals patch 按 active skin 覆写 ──
# 这些是 baseline (dandelion 米色 · gray · hair). skin 提供 PALETTE 时会
# 被替换成 skin 自己的 bg_alt / gray / hair / ink_soft.
_CARD = "rgba(243,235,218,1)"       # KPI + branch card 底
_GRAY = "rgba(115,120,132,1)"       # kicker / meta 文字
_INK_SOFT = "rgba(64,70,82,1)"      # figure caption
_HAIR = "rgba(175,178,188,1)"       # KPI stroke
_HUB_NOTE = "rgba(241,233,218,0.7)" # hub 圆内底部微字 (bg 派生)


def _try_skin_draw(kind: str, x: float, y: float, w: float, h: float,
                   label: str, palette: Palette, **kwargs) -> Optional[str]:
    """如果 active skin 提供了 draw_node 且接管这个 kind, 返回 SVG 片段;
    否则返回 None, 让 preset 走 fallback 分支."""
    skin_mod = _get_active_skin()
    if skin_mod is None:
        return None
    skin_inst = getattr(skin_mod, "SKIN_INSTANCE", None)
    if skin_inst is None:
        return None
    draw_fn = getattr(skin_inst, "draw_node", None)
    if draw_fn is None:
        return None
    try:
        return draw_fn(x, y, w, h, label, palette, kind=kind, **kwargs)
    except Exception:
        return None


# ═════════════════════════════════════════════════════════════════
# baseline data · 对齐 dandelion/sql_tree.svg
# ═════════════════════════════════════════════════════════════════

BASELINE_BRANCHES = [
    # (name, hue, subtitle, kicker, leaves)
    ("SELECT / FROM", "cinnamon", "projection · scope",   "M1 · 5 h",
        [("字段选择 · column pick", "L01"),
         ("别名 AS · aliasing",     "L02"),
         ("DISTINCT · uniqueness",  "L03")]),
    ("GROUP BY",      "green",    "aggregate · bucket",   "M4 · 5 h",
        [("聚合函数 · SUM / AVG",   "L10"),
         ("HAVING · group filter",  "L11"),
         ("细粒度 · granularity",   "L12")]),
    ("WHERE 过滤",    "magenta",  "predicate · filter",   "M2 · 5 h",
        [("比较运算 · comparators", "L04"),
         ("IN / BETWEEN · sets",    "L05"),
         ("NULL 语义 · tri-value",  "L06")]),
    ("ORDER / PAGE",  "olive",    "sort · window",        "M5 · 4 h",
        [("ORDER BY · sort keys",   "L13"),
         ("LIMIT · row cap",        "L14"),
         ("OFFSET · pagination",    "L15")]),
    ("JOIN 关联",     "blue",     "relation · merge",     "M3 · 6 h",
        [("INNER · intersection",   "L07"),
         ("LEFT · outer preserve",  "L08"),
         ("ON 条件 · key predicate","L09")]),
]

BASELINE_KPIS = [
    {"kicker": "MODULES",  "value": "5",     "note": "branches / topics",  "hue": "blue"},
    {"kicker": "LESSONS",  "value": "15",    "note": "atomic units",       "hue": "cinnamon"},
    {"kicker": "DURATION", "value": "25 h",  "note": "estimated total",    "hue": "gold_p"},
    {"kicker": "STAGE",    "value": "CORE",  "note": "foundational curric.","hue": "green"},
]


def build_mp_tree(
    root_label: str = "SQL 5D",
    branches: Optional[List[Any]] = None,
    kicker: str = "",
    figure_title: str = "SQL 学习路径 · five-module curriculum",
    # NOTE (2026-09-13 · P1 audit): 副标追加 Mi/N LEAVES 徽标 legend · 让域框右上
    # "4" 及 Q1-Q4 类编号可被自解释.
    figure_caption: str = "Radial learning tree · progressive dependencies · Mi = 模块编号 · 右上数字 = 该模块叶节点数",
    source: str = "Source · Data Platform onboarding · 2026",
    hub_kicker: str = "CORE CURRICULUM",
    hub_stat: str = "25 HOURS",
    hub_stat_note: str = "15 LESSONS · 5 MODULES",
    kpis: Optional[List[Dict[str, str]]] = None,
    leaf_count_suffix: str = "",
) -> Tree:
    """Build sql_tree Tree.

    branches : List of tuple
        Full form: (name, hue, subtitle, kicker, leaves)
        leaves : List of str OR List of (label, code)
    leaf_count_suffix : str
        Optional suffix on each branch card's right-side count label.
        Empty (default) → render as "N" only (no jargon like "LESSONS").
        Curriculum decks can pass "LESSONS", org charts "PEOPLE", etc.
        Legacy sentinel: "LESSONS" (baseline default kept for back-compat when
        `branches is None`).
    """
    src = branches if branches is not None else BASELINE_BRANCHES
    # baseline curriculum keeps "LESSONS"; user-provided branches default to none
    effective_suffix = leaf_count_suffix
    if branches is None and not leaf_count_suffix:
        effective_suffix = "LESSONS"

    root = TreeNode(
        id="hub", label=root_label,
        extra={
            "kicker": hub_kicker,
            "stat": hub_stat,
            "stat_note": hub_stat_note,
            "kpis": kpis if kpis is not None else BASELINE_KPIS,
        },
    )
    for i, br in enumerate(src):
        if len(br) == 5:
            name, hue, subtitle, b_kicker, leaves = br
        elif len(br) == 2:
            name, leaves = br
            hue, subtitle, b_kicker = "rust", "", f"M{i + 1}"
        else:
            raise ValueError(f"branch tuple must be 5-item or 2-item, got {len(br)}")
        n_leaf = len(leaves)
        n_leaf_label = f"{n_leaf} {effective_suffix}".strip() if effective_suffix else f"{n_leaf}"
        b_node = TreeNode(
            id=f"b{i}", label=name, group=hue,
            extra={
                "subtitle": subtitle,
                "kicker": b_kicker,
                "n_leaf_label": n_leaf_label,
            },
        )
        for j, leaf in enumerate(leaves):
            if isinstance(leaf, tuple):
                l_label, l_code = leaf[0], leaf[1] if len(leaf) > 1 else ""
            else:
                l_label, l_code = str(leaf), ""
            b_node.children.append(TreeNode(
                id=f"b{i}_{j}", label=l_label,
                extra={"code": l_code} if l_code else {},
            ))
        root.children.append(b_node)

    return Tree(
        root=root, kicker=kicker,
        figure_title=figure_title,
        figure_caption=figure_caption,
        source=source,
        encoding_note=f"{len(src)} branches · {sum(len(b[-1]) for b in src)} leaves",
    )


HERO_MP_DATA = build_mp_tree()


# ═════════════════════════════════════════════════════════════════
# color fallback · 对齐 dandelion
# ═════════════════════════════════════════════════════════════════

_DANDELION_HUE = {
    "blue":     "rgba(22,40,70,1)",
    "cinnamon": "rgba(168,88,42,1)",
    "green":    "rgba(16,106,82,1)",
    "magenta":  "rgba(152,42,55,1)",
    "olive":    "rgba(120,60,90,1)",
    "rust":     "rgba(152,42,55,1)",
    "orange":   "rgba(168,88,42,1)",
    "gold_p":   "rgba(182,138,56,1)",
}


def _readable_ink(fill: str) -> tuple[str, str]:
    if _luminance(fill) < 145:
        return "rgba(255,250,235,0.96)", "rgba(255,250,235,0.72)"
    return "rgba(28,30,38,0.96)", "rgba(64,70,82,0.78)"


def _trim_to_width(text: str, max_width: float, font_size: float,
                   char_w_ratio: float = 0.72) -> str:
    if not text:
        return ""
    if _visual_width(text, font_size * char_w_ratio) <= max_width:
        return text
    out = ""
    for ch in text:
        candidate = out + ch
        if _visual_width(candidate, font_size * char_w_ratio) > max_width:
            break
        out = candidate
    return out.rstrip()


def _fit_no_overflow(text: str, max_width: float, base_size: float,
                     *, min_size: float = 11.0,
                     char_w_ratio: float = 0.72) -> tuple[float, str]:
    fs, fitted = _fit_font_size(
        text, max_width, base_size, min_size=min_size, char_w_ratio=char_w_ratio
    )
    if _visual_width(fitted, fs * char_w_ratio) > max_width:
        fitted = _trim_to_width(fitted, max_width, fs, char_w_ratio)
    return fs, fitted


def _wrap_for_box(text: str, max_width: float, base_size: float,
                  *, max_lines: int, min_size: float = 12.0,
                  char_w_ratio: float = 0.72) -> list[tuple[str, float]]:
    if not text:
        return []
    lines = _wrap_lines(text, max_width, char_w=base_size * char_w_ratio, max_lines=max_lines)
    fitted: list[tuple[str, float]] = []
    for line in lines[:max_lines]:
        fs, safe_line = _fit_no_overflow(
            line, max_width, base_size, min_size=min_size, char_w_ratio=char_w_ratio
        )
        if safe_line:
            fitted.append((safe_line, fs))
    return fitted


def _hue(name: str, palette: Palette) -> str:
    c = HUE.get(name)
    if c and c.startswith("#"):
        return c
    return _DANDELION_HUE.get(name, _DANDELION_HUE["blue"])


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


VIEW_W = 1400
VIEW_H = 720


# Bucket H (2026-09-13) · subtract_level 默认预设 · L3 = 极简 (默认)
_SUBTRACT_L0: List[str] = []
_SUBTRACT_L1: List[str] = ["hub_shadow", "hub_divider", "hub_inner_ring"]
_SUBTRACT_L2: List[str] = _SUBTRACT_L1 + ["hub_kicker"]
_SUBTRACT_L3: List[str] = _SUBTRACT_L2 + ["hub_note", "hub_stat"]
_SUBTRACT_MAP = {"L0": _SUBTRACT_L0, "L1": _SUBTRACT_L1, "L2": _SUBTRACT_L2, "L3": _SUBTRACT_L3}


def _resolve_skip_kinds(skip_kinds: Optional[List[str]], subtract_level: str) -> set:
    if skip_kinds is not None:
        return set(skip_kinds)
    return set(_SUBTRACT_MAP.get(subtract_level, _SUBTRACT_L3))


def render_hero_embed_mp_mindmap_v2(
    data: Tree = HERO_MP_DATA,
    palette: Palette = BONE_RUST,
    params: Optional[HubFanoutParams] = None,
    *,
    subtract_level: str = "L3",
    skip_kinds: Optional[List[str]] = None,
) -> str:
    """渲染 dandelion sql_tree 风格 mindmap. viewBox 1400×720."""
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
        p = params or HubFanoutParams(
            hub_r=76.0,
            card_w=240.0,
            card_h=92.0,
            left_card_x=270.0,
            right_card_x=850.0,
            branch_row_h=190.0,
            leaf_w=176.0,
            leaf_h=30.0,
            leaf_row_h=36.0,
            leaf_card_gap=18.0,
        )
        pal = palette or BONE_RUST
        root = getattr(data, "root", None)
        if root is None:
            raise LayoutOverflow("mindmap: no root")

        # ── skin-aware globals patch · 按 active skin 覆写模块级语义色 ──
        _MOD = globals()
        _orig = {k: _MOD[k] for k in ("_CARD", "_GRAY", "_INK_SOFT", "_HAIR", "_HUB_NOTE")}
        _skin = _get_active_skin()
        if _skin is not None:
            _sp = getattr(_skin, "PALETTE", None)
            if _sp is not None:
                if getattr(_sp, "bg_alt", None):
                    _MOD["_CARD"] = _sp.bg_alt
                if getattr(_sp, "gray", None):
                    _MOD["_GRAY"] = _sp.gray
                    _MOD["_INK_SOFT"] = _sp.gray
                if getattr(_sp, "hair", None):
                    _MOD["_HAIR"] = _sp.hair
                if getattr(_sp, "bg", None):
                    # hub 底部 note 用 bg 的 70% alpha (在深墨 hub 上淡淡透出)
                    bg = _sp.bg
                    if bg.startswith("#") and len(bg) == 7:
                        r, g, b = int(bg[1:3], 16), int(bg[3:5], 16), int(bg[5:7], 16)
                        _MOD["_HUB_NOTE"] = f"rgba({r},{g},{b},0.7)"
                    else:
                        _MOD["_HUB_NOTE"] = bg

        try:
            return _render_body(data, pal, p, skip_kinds=skip_kinds, subtract_level=subtract_level)
        finally:
            _MOD.update(_orig)
    finally:
        _MOD_FONT.update(_ORIG_FONT)
def _render_body(data, pal, p, *, skip_kinds=None, subtract_level="L3") -> str:
    # Round1: remove the top KPI strip for mp_mindmap; in dense cases it can
    # collide with the fanout content below after slide atomization.
    kpis: List[Dict[str, str]] = []

    positions = hub_fanout_layout(data, 70, 100, 1330, 690, params=p)
    # Bucket H · subtraction filter
    _skips = _resolve_skip_kinds(skip_kinds, subtract_level)
    if _skips:
        positions = [pos for pos in positions if pos.get("kind") not in _skips]

    # ── dynamic VIEW_H · 若 branch/leaf 布局超过 720 · 扩到实际内容 + bottom_pad ──
    # 硬红线: 无溢出 · 若 dense (n_branch=8 · 4 rows/side) 需要 ~890 高
    max_content_y = float(VIEW_H)
    for pos in positions:
        k = pos.get("kind", "")
        if k == "branch_card":
            y_bot = pos["y"] + pos["h"]
            if y_bot > max_content_y:
                max_content_y = y_bot
        elif k == "leaf_pill":
            y_bot = pos["y"] + pos["h"]
            if y_bot > max_content_y:
                max_content_y = y_bot
    view_h = int(max(VIEW_H, max_content_y + 30))

    parts: List[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {VIEW_W} {view_h}">',
    ]
    parts.append(f'<rect x="0" y="0" width="{VIEW_W}" height="{view_h}" '
                 f'fill="{pal.bg}"/>')

    # ── 顶部 chrome ──
    if getattr(data, "kicker", ""):
        parts.append(
            f'<text x="90" y="34" font-family="{FONT_SANS}" font-size="15" '
            f'fill="{_hue("rust", pal)}" font-weight="700" '
            f'letter-spacing="0.22em">{esc(data.kicker.upper())}</text>'
        )
    parts.append(
        f'<text x="90" y="66" font-family="{FONT_SERIF}" font-size="26" '
        f'font-weight="600" fill="{pal.ink}" letter-spacing="0.4">'
        f'{esc(data.figure_title)}</text>'
    )
    if getattr(data, "figure_caption", ""):
        _, page_muted = _readable_ink(pal.bg)
        parts.append(
            f'<text x="90" y="96" font-family="{FONT_SANS}" font-size="15" '
            f'fill="{page_muted}" letter-spacing="0.2">'
            f'{esc(data.figure_caption)}</text>'
        )
    parts.append(
        f'<line x1="90" y1="114" x2="1310" y2="114" '
        f'stroke="{pal.ink}" stroke-width="0.8"/>'
    )

    # ── KPI 带 ──
    if kpis:
        kpi_y = 128
        kpi_w = 240
        kpi_h = 52
        kpi_start_x = 90
        kpi_gap = 20
        kpi_ink, kpi_muted = _readable_ink(_CARD)
        for i, k in enumerate(kpis[:4]):
            kx = kpi_start_x + i * (kpi_w + kpi_gap)
            hue = k.get("hue", "blue")
            c = _hue(hue, pal)
            parts.append(
                f'<rect x="{kx}" y="{kpi_y}" width="{kpi_w}" height="{kpi_h}" '
                f'fill="{_CARD}" stroke="{_HAIR}" '
                f'stroke-width="0.6"/>'
            )
            parts.append(
                f'<rect x="{kx}" y="{kpi_y}" width="4" height="{kpi_h}" fill="{c}"/>'
            )
            fs_kpi_kicker, txt_kpi_kicker = _fit_no_overflow(
                str(k.get("kicker", "")).upper(), kpi_w - 120, 10.0, min_size=7.5
            )
            parts.append(
                f'<text x="{kx + 14}" y="{kpi_y + 15}" font-family="{FONT_SANS}" '
                f'font-size="{fs_kpi_kicker:.1f}" fill="{kpi_muted}" font-weight="600" '
                f'letter-spacing="0.6">{esc(txt_kpi_kicker)}</text>'
            )
            value_lines = _wrap_for_box(
                str(k.get("value", "")), kpi_w - 48, 16.0, max_lines=2, min_size=9.5
            )
            value_y0 = kpi_y + (33.0 if len(value_lines) > 1 else 42.0)
            for li, (txt_kpi_value, fs_kpi_value) in enumerate(value_lines):
                parts.append(
                    f'<text x="{kx + 14}" y="{value_y0 + li * 16.5:.1f}" '
                    f'font-family="{FONT_SERIF}" font-size="{fs_kpi_value:.1f}" '
                    f'fill="{kpi_ink}" font-weight="700">'
                    f'{esc(txt_kpi_value)}</text>'
                )
            value_w = max(
                (_visual_width(txt, fs * 0.72) for txt, fs in value_lines),
                default=0.0,
            )
            if k.get("note") and len(value_lines) == 1 and value_w < 82:
                note_avail = max(48.0, kpi_w - 112)
                fs_kpi_note, txt_kpi_note = _fit_no_overflow(
                    str(k["note"]), note_avail, 12.0, min_size=8.5
                )
                parts.append(
                    f'<text x="{kx + 100}" y="{kpi_y + 43}" font-family="{FONT_SANS}" '
                    f'font-size="{fs_kpi_note:.1f}" fill="{kpi_muted}">'
                    f'{esc(txt_kpi_note)}</text>'
                )

    # ── z-order: curves → hub → cards & leaves ──
    # (曲线放最底 · hub 圆放中间 · card/leaf 覆盖上层)

    # branch curves
    for pos in positions:
        if pos["kind"] == "branch_curve":
            c = _hue(pos["hue"], pal)
            sw = float(pos.get("stroke_width", 2.2))
            parts.append(
                f'<path d="{pos["d"]}" fill="none" stroke="{c}" '
                f'stroke-width="{sw}" stroke-linecap="round"/>'
            )
            # 端点小圆 (在 card 一侧)
            parts.append(
                f'<circle cx="{pos["dot_cx"]:.1f}" cy="{pos["dot_cy"]:.1f}" '
                f'r="3.4" fill="{c}" stroke="{pal.bg}" stroke-width="1.4"/>'
            )
        elif pos["kind"] == "leaf_curve":
            # R4 fix (2026-09-13): use hue at 0.85 alpha + honour layout's
            # stroke_width hint (was 0.5/0.9 · sub-pixel in tiny figure slots).
            c = _hue_rgba(pos["hue"], pal, 0.85)
            sw = float(pos.get("stroke_width", 1.4))
            parts.append(
                f'<path d="{pos["d"]}" fill="none" stroke="{c}" '
                f'stroke-width="{sw}" stroke-linecap="round"/>'
            )

    hub_aux_visible = any(
        pos["kind"] in {"hub_kicker", "hub_stat", "hub_note"} for pos in positions
    )

    # hub 圆
    hub_deep = _hue("blue", pal)
    gold = _hue("gold_p", pal)
    for pos in positions:
        k = pos["kind"]
        if k == "hub_shadow":
            parts.append(
                f'<circle cx="{pos["cx"]}" cy="{pos["cy"]}" r="{pos["r"]}" '
                f'fill="rgba(0,0,0,0.06)"/>'
            )
        elif k == "hub_circle":
            parts.append(
                f'<circle cx="{pos["cx"]}" cy="{pos["cy"]}" r="{pos["r"]}" '
                f'fill="{_hue_rgba("blue", pal, 0.96)}" '
                f'stroke="{hub_deep}" stroke-width="1.6"/>'
            )
        elif k == "hub_inner_ring":
            parts.append(
                f'<circle cx="{pos["cx"]}" cy="{pos["cy"]}" r="{pos["r"]}" '
                f'fill="none" stroke="{_hue_rgba("gold_p", pal, 0.55)}" '
                f'stroke-width="0.7" stroke-dasharray="2 3"/>'
            )
        elif k == "hub_kicker":
            parts.append(
                f'<text x="{pos["cx"]}" y="{pos["cy"]}" text-anchor="middle" '
                f'font-family="{FONT_SANS}" font-size="15" fill="{gold}" '
                f'font-weight="700" letter-spacing="0.22em">'
                f'{esc(pos["label"].upper())}</text>'
            )
        elif k == "hub_divider":
            parts.append(
                f'<line x1="{pos["x1"]}" y1="{pos["y"]}" '
                f'x2="{pos["x2"]}" y2="{pos["y"]}" '
                f'stroke="{_hue_rgba("gold_p", pal, 0.55)}" stroke-width="0.5"/>'
            )
        elif k == "hub_name":
            max_w = p.hub_r * 1.56
            name_lines = _wrap_for_box(
                pos["label"], max_w, 21.0, max_lines=2, min_size=13.0
            )
            center_y = pos["cy"] if hub_aux_visible else pos["cy"] + 14.0
            line_h = 18.0
            first_y = center_y - (len(name_lines) - 1) * line_h / 2
            for li, (txt, fs) in enumerate(name_lines):
                parts.append(
                    f'<text x="{pos["cx"]}" y="{first_y + li * line_h:.1f}" '
                    f'text-anchor="middle" font-family="{FONT_SERIF}" '
                    f'font-size="{fs:.1f}" fill="{pal.bg}" '
                    f'font-weight="700" letter-spacing="0.4">'
                    f'{esc(txt)}</text>'
                )
        elif k == "hub_stat":
            max_w = p.hub_r * 1.72
            fs, txt = _fit_font_size(pos["label"], max_w, 18.0, min_size=15.0)
            if txt.endswith("…"):
                txt = txt.rstrip("…")
            parts.append(
                f'<text x="{pos["cx"]}" y="{pos["cy"]}" text-anchor="middle" '
                f'font-family="{FONT_SERIF}" font-size="{fs:.1f}" fill="{gold}" '
                f'font-weight="700">{esc(txt)}</text>'
            )
        elif k == "hub_note":
            max_w = p.hub_r * 1.72
            fs, txt = _fit_font_size(pos["label"], max_w, 15.0, min_size=15.0)
            if txt.endswith("…"):
                txt = txt.rstrip("…")
            parts.append(
                f'<text x="{pos["cx"]}" y="{pos["cy"]}" text-anchor="middle" '
                f'font-family="{FONT_SANS}" font-size="{fs:.1f}" '
                f'fill="{_HUB_NOTE}" letter-spacing="0.16em">'
                f'{esc(txt)}</text>'
            )

    # branch cards
    for pos in positions:
        if pos["kind"] != "branch_card":
            continue
        c = _hue(pos["hue"], pal)
        c_dim = _hue_rgba(pos["hue"], pal, 0.85)
        card_ink, card_muted = _readable_ink(_CARD)
        parts.append(
            f'<rect x="{pos["x"]:.1f}" y="{pos["y"]:.1f}" '
            f'width="{pos["w"]}" height="{pos["h"]}" '
            f'fill="{_CARD}" stroke="{c_dim}" stroke-width="1.2"/>'
        )
        parts.append(
            f'<rect x="{pos["x"]:.1f}" y="{pos["y"]:.1f}" '
            f'width="4" height="{pos["h"]}" fill="{c}"/>'
        )
        count_text = str(pos.get("n_leaf_label") or "")
        if _visual_width(count_text, 15.0 * 0.72) > 58:
            count_text = str(pos.get("n_leaf", "") or "")
        count_w = _visual_width(count_text, 15.0 * 0.55) + 8 if count_text else 0
        if pos.get("kicker"):
            kicker_avail = max(60.0, min(pos["w"] - 24 - count_w, pos["w"] - 110))
            fs_kicker, txt_kicker = _fit_no_overflow(
                str(pos["kicker"]).upper(), kicker_avail, 12.0, min_size=8.0
            )
            parts.append(
                f'<text x="{pos["x"] + 12:.1f}" y="{pos["y"] + 18:.1f}" '
                f'font-family="{FONT_SANS}" font-size="{fs_kicker:.1f}" '
                f'fill="{card_muted}" font-weight="600" '
                f'letter-spacing="0.06em">{esc(txt_kicker)}</text>'
            )
        label_avail = pos["w"] - 56
        label_lines = _wrap_for_box(pos["label"], label_avail, 16.5, max_lines=2, min_size=12.5)
        label_y = pos["y"] + 42.0
        for li, (txt_label, fs_label) in enumerate(label_lines):
            parts.append(
                f'<text x="{pos["x"] + 12:.1f}" y="{label_y + li * 17.5:.1f}" '
                f'font-family="{FONT_SANS}" font-size="{fs_label:.1f}" font-weight="700" '
                f'fill="{card_ink}" letter-spacing="0.2">'
                f'{esc(txt_label)}</text>'
            )
        subtitle_raw = str(pos.get("subtitle", "") or "").strip()
        if subtitle_raw:
            sub_max_lines = 1 if len(label_lines) > 1 else 2
            sub_lines = _wrap_for_box(
                subtitle_raw, label_avail, 13.0, max_lines=sub_max_lines, min_size=10.5
            )
            sub_y = pos["y"] + (75.0 if len(label_lines) > 1 else 64.0)
            for li, (txt_sub, fs_sub) in enumerate(sub_lines):
                parts.append(
                    f'<text x="{pos["x"] + 12:.1f}" y="{sub_y + li * 14.0:.1f}" '
                    f'font-family="{FONT_SANS}" font-size="{fs_sub:.1f}" '
                    f'fill="{card_muted}">'
                    f'{esc(txt_sub)}</text>'
                )
        if count_text:
            parts.append(
                f'<text x="{pos["x"] + pos["w"] - 10:.1f}" y="{pos["y"] + 18:.1f}" '
                f'text-anchor="end" font-family="{FONT_SANS}" font-size="15" '
                f'fill="{card_ink}" font-weight="700" letter-spacing="1.4">'
                f'{esc(count_text)}</text>'
            )

    # leaf pills
    for pos in positions:
        if pos["kind"] != "leaf_pill":
            continue
        c = _hue(pos["hue"], pal)
        c_dim = _hue_rgba(pos["hue"], pal, 0.55)
        leaf_ink, _ = _readable_ink(pal.bg)
        parts.append(
            f'<rect x="{pos["x"]:.1f}" y="{pos["y"]:.1f}" '
            f'width="{pos["w"]}" height="{pos["h"]}" '
            f'fill="{pal.bg}" stroke="{c_dim}" stroke-width="0.7"/>'
        )
        if pos.get("side") == "left":
            dot_x = pos["anchor_x"] - 10.0
            text_x = dot_x - 12.0
            text_anchor = "end"
        else:
            dot_x = pos["anchor_x"] + 10.0
            text_x = dot_x + 12.0
            text_anchor = "start"
        parts.append(
            f'<circle cx="{dot_x:.1f}" cy="{pos["y"] + pos["h"] / 2:.1f}" '
            f'r="3.5" fill="{c}"/>'
        )
        lines = pos.get("lines") or []
        leaf_avail = max(40.0, pos["w"] - 50.0)
        if len(lines) > 1:
            fs_leaf = 14.0
            line_h = fs_leaf * 1.18
            total_h = line_h * len(lines)
            first_y = pos["y"] + pos["h"] / 2 - total_h / 2 + fs_leaf * 0.85
            for li, ln in enumerate(lines):
                safe_ln = _trim_to_width(str(ln), leaf_avail, fs_leaf)
                parts.append(
                    f'<text x="{text_x:.1f}" y="{first_y + li * line_h:.1f}" '
                    f'text-anchor="{text_anchor}" font-family="{FONT_SANS}" '
                    f'font-size="{fs_leaf:.1f}" fill="{leaf_ink}" '
                    f'font-weight="500">{esc(safe_ln)}</text>'
                )
        else:
            leaf_text = lines[0] if lines else pos.get("display_label", pos["label"])
            fs_leaf, txt_leaf = _fit_no_overflow(leaf_text, leaf_avail, 15.0, min_size=12.0)
            parts.append(
                f'<text x="{text_x:.1f}" y="{pos["y"] + pos["h"] / 2 + 5:.1f}" '
                f'text-anchor="{text_anchor}" font-family="{FONT_SANS}" '
                f'font-size="{fs_leaf:.1f}" fill="{leaf_ink}" '
                f'font-weight="500">{esc(txt_leaf)}</text>'
            )

    # 底部 source 已按用户要求移除 · viewBox shrink 由 make_relation 统一处理

    parts.append('</svg>')
    return "".join(parts)


__all__ = [
    "HERO_MP_DATA", "build_mp_tree", "render_hero_embed_mp_mindmap_v2",
    "BASELINE_BRANCHES", "BASELINE_KPIS",
]
