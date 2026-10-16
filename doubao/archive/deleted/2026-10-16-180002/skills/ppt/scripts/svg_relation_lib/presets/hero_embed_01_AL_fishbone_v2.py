"""HERO EMBED · 01_AL_fishbone V2 · dandelion 风格 Ishikawa 鱼骨

彻底重写: 参考 dandelion/fishbone.svg 的顶级视觉密度 ·
  - 水平 spine + 粗箭头 + 箭羽装饰
  - 6 分类上下交替 · 每分类斜线 + N sub-cause 引线
  - 分类 card 带 name/% 归因
  - PRIMARY SUSPECT 高亮条
  - 右侧 problem statement 方框
  - viewBox 1400×700 · 大画布 · 直接 embed 到 slide 主体

build_kwargs 完整暴露:
    - root_label: 中心事件文本
    - figure_title: 大标题
    - problem: {kicker, label, stat, range} 右侧椭圆 · 空则不显示
    - legend: bool (预留)
    - categories: List[(name, hue, subtitle, pct, primary_suspect, subs)] 6 类别
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..schemas import Tree, TreeNode
from ..palettes import Palette
from ..engine import esc
from ..layouts.fishbone_v2 import (
    fishbone_v2_layout,
    LayoutOverflow,
    FishboneParams,
    _estimate_text_width,
)
from ..skins.editorial_atelier import (
    BONE_RUST, HUE, FONT_SANS, FONT_SERIF,
)


# ═════════════════════════════════════════════════════════════════
# baseline data · 与 dandelion.svg 对齐 (LLM latency regression)
# ═════════════════════════════════════════════════════════════════

BASELINE_CATEGORIES = [
    ("MODEL",     "blue",     "architecture · quant",   22.0, False,
        ["FP16 → INT8 conversion drift", "Attention kernel switch (v3)", "Larger 32K context window"]),
    ("SERVING",   "cinnamon", "framework · runtime",    34.0, True,
        ["KV-cache eviction storm", "Tokenizer regression v1.4", "Batch scheduler starvation"]),
    ("HARDWARE",  "green",    "compute · memory",        9.0, False,
        ["H100 thermal throttling", "HBM bandwidth saturation", "PCIe lane contention"]),
    ("DATA",      "magenta",  "request patterns",       14.0, False,
        ["P95 prompt length +60%", "Cache-cold off-hours traffic", "Geo shift APAC → US-east"]),
    ("NETWORK",   "olive",    "routing · transport",     8.0, False,
        ["Cross-AZ round-trip", "TLS handshake overhead", "CDN cache-miss ratio ↑"]),
    ("OPERATIONS","orange",   "deploy · scaling",       13.0, False,
        ["Rollout skew (v1 ↔ v2)", "HPA cool-down misfit", "Overloaded telemetry agent"]),
]

BASELINE_KPIS = [
    {"kicker": "BASELINE p99",  "value": "820 ms",   "note": "Jun 01 – Jul 11", "hue": "blue"},
    {"kicker": "CURRENT p99",   "value": "1 132 ms", "note": "7-day rolling",   "hue": "rust"},
    {"kicker": "REGRESSION",    "value": "▲ +38.0%", "note": "vs. baseline",    "hue": "rust"},
    {"kicker": "ONSET",         "value": "Jul 12",   "note": "post v1.4 rollout", "hue": "cinnamon"},
]

BASELINE_PROBLEM = {
    "kicker": "PROBLEM STATEMENT",
    "label":  "p99 latency",
    "stat":   "+38.0%",
    "range":  "820 ms → 1 132 ms",
}


def build_al_tree(
    root_label: str = "LLM serving latency regression",
    categories: Optional[List[Any]] = None,
    kicker: str = "",
    figure_title: str = "Root-cause analysis · LLM serving latency regression",
    figure_caption: str = "Ishikawa fishbone · six primary categories · post-mortem draft",
    source: str = "Source · SRE post-mortem · 2025-07",
    kpis: Optional[List[Dict[str, str]]] = None,
    problem: Optional[Dict[str, str]] = None,
    legend: bool = True,
) -> Tree:
    """Build fishbone Tree.

    Parameters
    ----------
    root_label : str
        effect / problem statement (纯记录, 视觉不直接显示)
    categories : List of tuple
        6-item form: (name, hue, subtitle, pct, primary_suspect, subs)
        3-item form: (name, hue, subs) — 无 subtitle/pct/primary
        max 6 categories · max 5 sub-causes per category (layout hard cap · overflow → LayoutOverflow)
        hue ∈ {'rust','orange','magenta','blue','green','olive','cinnamon'}
    kpis : List[dict]
        顶部 4 KPI 带 · 每项 {kicker, value, note, hue}. None → 默认 baseline. [] 空列表 → 不渲染 KPI 带.
    problem : dict
        右侧椭圆 {kicker, label, stat, range}. None → 默认 baseline. {} 空 dict → 不渲染.
    """
    src = categories if categories is not None else BASELINE_CATEGORIES

    root = TreeNode(
        id="effect", label=root_label,
        extra={
            "kpis": kpis if kpis is not None else BASELINE_KPIS,
            "problem": problem if problem is not None else BASELINE_PROBLEM,
            "legend": legend,
        },
    )
    for i, cat in enumerate(src):
        if len(cat) == 6:
            name, hue, subtitle, pct, primary, subs = cat
        elif len(cat) == 3:
            name, hue, subs = cat
            subtitle, pct, primary = "", None, False
        else:
            raise ValueError(f"category tuple must be 6-item or 3-item, got {len(cat)}")
        cat_node = TreeNode(
            id=f"c{i}", label=name, group=hue,
            extra={
                "subtitle": subtitle, "pct": pct,
                "primary_suspect": primary, "kicker": f"M{i + 1}",
            },
        )
        for j, sub in enumerate(subs):
            cat_node.children.append(TreeNode(id=f"c{i}_{j}", label=sub, group=hue))
        root.children.append(cat_node)

    return Tree(
        root=root,
        kicker=kicker,
        figure_title=figure_title,
        figure_caption=figure_caption,
        source=source,
        encoding_note=f"{len(src)} categories · {sum(len(c[-1]) for c in src)} sub-causes",
    )


HERO_AL_DATA = build_al_tree()


# ═════════════════════════════════════════════════════════════════
# 颜色 · 用一套固定 hue palette 对齐 dandelion (skin HUE fallback)
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


def _fit_font_size(text: str, preferred: float, minimum: float, max_width: float) -> float:
    estimated = _estimate_text_width(text, preferred)
    if estimated <= max_width or estimated <= 0:
        return preferred
    return max(minimum, preferred * max_width / estimated)


# ═════════════════════════════════════════════════════════════════
# render · viewBox 1400×700
# ═════════════════════════════════════════════════════════════════

VIEW_W = 1400
VIEW_H = 700


# Bucket H (2026-09-13) · subtract_level default "L3" (极简)
# [R6 REBUILD 2026-09-13] category_slash 是 Ishikawa 必要 rib 几何 · 从 L3 subtract 移除 ·
# 保留后 sub-bullet 引线端点终于有 rib 可落 · 不再悬空.
_SUBTRACT_L0: List[str] = []
_SUBTRACT_L1: List[str] = ["sub_kicker"]
_SUBTRACT_L2: List[str] = ["sub_kicker", "sub_dot_inner", "spine_barb"]
_SUBTRACT_L3: List[str] = ["sub_kicker", "sub_dot_inner", "spine_barb",
                            "spine_dot", "primary_suspect_bar"]
_SUBTRACT_MAP = {"L0": _SUBTRACT_L0, "L1": _SUBTRACT_L1,
                 "L2": _SUBTRACT_L2, "L3": _SUBTRACT_L3}


def _resolve_skip_kinds(skip_kinds: Optional[List[str]], subtract_level: str) -> set:
    if skip_kinds is not None:
        return set(skip_kinds)
    return set(_SUBTRACT_MAP.get(subtract_level, _SUBTRACT_L3))


def render_hero_embed_al_fishbone_v2(
    data: Tree = HERO_AL_DATA,
    palette: Palette = BONE_RUST,
    params: Optional[FishboneParams] = None,
    *,
    subtract_level: str = "L3",
    skip_kinds: Optional[List[str]] = None,
) -> str:
    """渲染 dandelion 风格 Ishikawa 鱼骨. viewBox 1400×700."""
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
        p = params or FishboneParams()
        pal = palette or BONE_RUST
        root = getattr(data, "root", None)
        if root is None:
            raise LayoutOverflow("fishbone: no root")

        extra = getattr(root, "extra", {}) or {}
        problem = extra.get("problem", None)

        positions = fishbone_v2_layout(data, 70, 110, 1120, 690, params=p)
        # Bucket H · subtraction filter
        _skips = _resolve_skip_kinds(skip_kinds, subtract_level)
        if _skips:
            positions = [pos for pos in positions if pos.get("kind") not in _skips]
        draw_priority = {
            "category_slash": 0,
            "sub_line": 1,
            "category_card": 2,
            "primary_suspect_bar": 3,
            "sub_label": 4,
            "sub_dot_inner": 5,
            "sub_dot_outer": 5,
            "spine": 6,
            "spine_dot": 7,
            "effect_box": 8,
            "spine_arrow": 9,
            "spine_barb": 10,
            "sub_kicker": 10,
        }
        positions = sorted(
            positions,
            key=lambda pos: draw_priority.get(str(pos.get("kind")), 4),
        )

        parts: List[str] = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {VIEW_W} {VIEW_H}">',
        ]
        parts.append(f'<rect x="0" y="0" width="{VIEW_W}" height="{VIEW_H}" '
                     f'fill="{pal.bg}"/>')

        # ── 顶部: title / hairline ──
        # [FONT-FIX-2026-09-11] atomize scale ≈ 0.68 (viewBox ~1322×673 → slide 900×440)
        # 需要 SVG-space 字号 ≥ 15 才能在 slide 上 ≥ 10pt.
        # 所有原本 ≤14 的字号上调至 15 · 大字保持.
        parts.append(
            f'<text x="90" y="60" font-family="{FONT_SERIF}" font-size="26" '
            f'font-weight="600" fill="{pal.ink}" letter-spacing="0.4">'
            f'{esc(data.figure_title)}</text>'
        )
        parts.append(
            f'<line x1="90" y1="88" x2="1310" y2="88" '
            f'stroke="{pal.ink}" stroke-width="0.8"/>'
        )

        # ── 主体 · fishbone geometry ─────────────────
        for pos in positions:
            k = pos["kind"]
            if k == "spine":
                # [R6 2026-09-13] stroke-width 2.6 → 4.2 · 让脊柱在 slide 上明显 ·
                # 之前 2.6 SVG × 0.629 scale = 1.6 slide-px · atomize int() cast → 2 slide-px ·
                # 与 masthead hairline (1.5) 视觉几乎无差 · 现在 4.2 × 0.629 = 2.6 → int 2 slide-px ·
                # 拉大到 5.0 保证 int cast 后 ≥ 3 slide-px · 视觉上是真正的骨干.
                parts.append(
                    f'<line x1="{pos["x1"]}" y1="{pos["y1"]}" '
                    f'x2="{pos["x2"]}" y2="{pos["y2"]}" '
                    f'stroke="{pal.ink}" stroke-width="5.0"/>'
                )
            elif k == "spine_arrow":
                parts.append(
                    f'<path d="{pos["d"]}" fill="{pal.ink}"/>'
                )
            elif k == "spine_barb":
                parts.append(
                    f'<line x1="{pos["x1"]}" y1="{pos["y1"]}" '
                    f'x2="{pos["x2"]}" y2="{pos["y2"]}" '
                    f'stroke="{pal.bg}" stroke-width="0.7"/>'
                )
            elif k == "spine_dot":
                c = _hue(pos["hue"], pal)
                # [R6 2026-09-13] r 3.4 → 5.0 · rib 与 spine 交汇点更醒目 ·
                # 让读者看到 rib 是从 spine 真实分叉出去 · 不是漂浮.
                parts.append(
                    f'<circle cx="{pos["cx"]}" cy="{pos["cy"]}" r="5.0" '
                    f'fill="{c}" stroke="{pal.bg}" stroke-width="1.8"/>'
                )
            elif k == "category_slash":
                c = _hue(pos["hue"], pal)
                # [R6 2026-09-13] rib stroke 2.2 → 3.4 · 让 ±30° 斜线在 slide 上明显 ·
                # 之前 2.2 × 0.629 = 1.4 slide-px → int cast 1 → 与 sub_line 无差别 ·
                # 现在 3.4 → 2 slide-px · 与 spine (2-3) 呈层级 · 视觉上是真正的 rib.
                parts.append(
                    f'<line x1="{pos["x1"]}" y1="{pos["y1"]}" '
                    f'x2="{pos["x2"]}" y2="{pos["y2"]}" '
                    f'stroke="{c}" stroke-width="3.4" stroke-linecap="round"/>'
                )
            elif k == "sub_kicker":
                c = _hue(pos["hue"], pal)
                parts.append(
                    f'<text x="{pos["x"]:.1f}" y="{pos["y"]:.1f}" '
                    f'font-family="{FONT_SANS}" font-size="17" fill="{c}" '
                    f'font-weight="700" letter-spacing="0.15em">'
                    f'{esc(pos["label"])}</text>'
                )
            elif k == "sub_line":
                # [R6 2026-09-13] opacity 0.55 → 0.85 · stroke 1 → 1.6 · leader-line 更清晰 ·
                # 之前 0.55 opacity + 1 stroke → 视觉几乎消失 · 端点看似悬空.
                c = _hue_rgba(pos["hue"], pal, 0.85)
                parts.append(
                    f'<line x1="{pos["x1"]:.1f}" y1="{pos["y1"]:.1f}" '
                    f'x2="{pos["x2"]:.1f}" y2="{pos["y2"]:.1f}" '
                    f'stroke="{c}" stroke-width="1.6"/>'
                )
            elif k == "sub_dot_inner":
                c = _hue(pos["hue"], pal)
                # [R6 2026-09-13] r 1.6 → 3.0 · leader-line 端点在 rib 上明显 ·
                # 之前 1.6 SVG × 0.629 = 1 slide-px · 视觉消失 · 现在 3.0 → 2 slide-px 可见.
                parts.append(
                    f'<circle cx="{pos["cx"]:.1f}" cy="{pos["cy"]:.1f}" '
                    f'r="3.0" fill="{c}"/>'
                )
            elif k == "sub_dot_outer":
                c = _hue_rgba(pos["hue"], pal, 0.95)
                parts.append(
                    f'<circle cx="{pos["cx"]:.1f}" cy="{pos["cy"]:.1f}" '
                    f'r="{pos["r"]}" fill="{pal.bg}" stroke="{c}" stroke-width="1.2"/>'
                )
            elif k == "sub_label":
                parts.append(
                    f'<text x="{pos["x"]:.1f}" y="{pos["y"]:.1f}" text-anchor="end" '
                    f'font-family="{FONT_SANS}" font-size="17" fill="{pal.ink}" '
                    f'font-weight="500">{esc(pos["label"])}</text>'
                )
            elif k == "category_card":
                title_lines = pos.get("title_lines") or [pos.get("title", pos["label"])]
                # Round6: keep the category card minimal and prevent skins from
                # reintroducing gray auxiliary subtitle text.
                c = _hue(pos["hue"], pal)
                c_dim = _hue_rgba(pos["hue"], pal, 0.85)
                parts.append(
                    f'<rect x="{pos["x"]:.1f}" y="{pos["y"]:.1f}" '
                    f'width="{pos["w"]}" height="{pos["h"]}" '
                    f'fill="{pal.bg}" stroke="{c_dim}" stroke-width="0.9"/>'
                )
                parts.append(
                    f'<rect x="{pos["x"]:.1f}" '
                    f'y="{float(pos.get("accent_y", pos["y"])):.1f}" '
                    f'width="4" '
                    f'height="{float(pos.get("accent_h", pos["h"])):.1f}" '
                    f'fill="{c}"/>'
                )
                title_y = float(pos.get("title_y", pos["y"] + 17))
                title_step = float(pos.get("title_step", 14.0))
                for line_index, line in enumerate(title_lines):
                    parts.append(
                        f'<text x="{pos["x"] + 12:.1f}" '
                        f'y="{title_y + line_index * title_step:.1f}" '
                        f'font-family="{FONT_SANS}" font-size="13" font-weight="600" '
                        f'fill="{pal.ink}">{esc(line)}</text>'
                    )
            elif k == "primary_suspect_bar":
                gold = _hue("gold_p", pal)
                # [FIX 2026-09-11 R2] chip bar 宽度自适应 · 原来固定 148 SVG-px ·
                # 但 "★ PRIMARY SUSPECT" 字号 15 + letter-spacing 0.2em 实测宽 ~180-200 ·
                # 超出 chip 底色右缘. 用估算取 max(cat_card_w, text_w + 2×padding).
                chip_label = pos["label"]
                fs = 15.0
                # letter-spacing 0.2em ≈ fs × 0.2 = 3 SVG-px per char
                text_w = len(chip_label) * fs * 0.62 + len(chip_label) * fs * 0.2
                hpad = 10.0
                chip_w = max(float(pos["w"]), text_w + 2 * hpad)
                # 让 chip 保持视觉与 card 中心对齐: 若 chip 变宽 · 向左延伸至和 card 中心对称
                cx_card = pos["x"] + pos["w"] / 2
                chip_x = cx_card - chip_w / 2
                parts.append(
                    f'<rect x="{chip_x:.1f}" y="{pos["y"]:.1f}" '
                    f'width="{chip_w:.1f}" height="{pos["h"]}" fill="{gold}" opacity="0.95"/>'
                )
                parts.append(
                    f'<text x="{cx_card:.1f}" y="{pos["y"] + 14:.1f}" '
                    f'text-anchor="middle" font-family="{FONT_SANS}" font-size="17" '
                    f'fill="{pal.bg}" font-weight="700" letter-spacing="0.2em">'
                    f'{esc(chip_label)}</text>'
                )
            elif k == "effect_box":
                # [R6 REBUILD 2026-09-13] Ishikawa 右端 effect box · 承载 problem 陈述
                # 数据源优先级:
                #   1. root_label · Tree.root.label (显式传入的 effect statement)
                #   2. problem.label / problem.stat (若 problem 非空)
                #   3. fallback 默认 "EFFECT" · 保证 R6 后无论 caller 如何 · effect box 永远有 label
                pc = _hue("rust", pal)
                bx = float(pos["x"])
                by = float(pos["y"])
                bw = float(pos["w"])
                bh = float(pos["h"])
                effect_title = ""
                effect_stat = ""
                if isinstance(problem, dict) and problem:
                    effect_title = str(problem.get("label", "")) or ""
                    effect_stat = str(problem.get("stat", "")) or ""
                # 若 problem 空 · 用 root_label 兜底
                if not effect_title:
                    rl = str(getattr(root, "label", "")) or ""
                    effect_title = rl or "问题陈述"
                effect_inner_w = bw - 28.0
                # 阴影
                parts.append(
                    f'<rect x="{bx + 3:.1f}" y="{by + 3:.1f}" '
                    f'width="{bw}" height="{bh}" fill="rgba(0,0,0,0.05)"/>'
                )
                # 主 box · 淡填充 + 粗描边
                # [R6 2026-09-13] fill 从 rgba(243,235,218) (与 bg 几乎同色) 改为
                # rgba(255,248,232) (明显浅) · 与 cream_bg #F4EFE4 拉开 8-10 亮度 ·
                # stroke-width 2.2 → 3.6 · 让 box 在 slide 上一眼可见.
                parts.append(
                    f'<rect x="{bx:.1f}" y="{by:.1f}" '
                    f'width="{bw}" height="{bh}" '
                    f'fill="{pal.bg}" stroke="{pc}" stroke-width="3.6"/>'
                )
                # 主标题 · serif · 中部
                title_y = by + 44 if effect_stat else by + bh/2 + 6
                title_font_size = _fit_font_size(effect_title, 17.0, 12.0, effect_inner_w)
                parts.append(
                    f'<text x="{bx + bw/2:.1f}" y="{title_y:.1f}" text-anchor="middle" '
                    f'font-family="{FONT_SERIF}" font-size="{title_font_size:.1f}" '
                    f'fill="{pal.ink}" '
                    f'font-weight="700">{esc(effect_title)}</text>'
                )
                # 大数字 · 底部 · 若有
                if effect_stat:
                    stat_font_size = _fit_font_size(effect_stat, 30.0, 16.0, effect_inner_w)
                    parts.append(
                        f'<text x="{bx + bw/2:.1f}" y="{by + 78:.1f}" text-anchor="middle" '
                        f'font-family="{FONT_SERIF}" font-size="{stat_font_size:.1f}" '
                        f'fill="{pc}" '
                        f'font-weight="700">{esc(effect_stat)}</text>'
                    )

        parts.append('</svg>')
        return "".join(parts)
    finally:
        _MOD_FONT.update(_ORIG_FONT)
__all__ = [
    "HERO_AL_DATA", "build_al_tree", "render_hero_embed_al_fishbone_v2",
    "BASELINE_CATEGORIES", "BASELINE_KPIS", "BASELINE_PROBLEM",
]
