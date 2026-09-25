# Bucket H · subtract_level default "L3" (2026-09-13)
"""HERO EMBED · 03_BL_bloom V2 · stepped Bloom cognitive pyramid

Redesigned to match `final_svg_relation/03_BL_bloom/step1_reference/bloom_hero_reference.svg`.

Structure (hero canvas 1400×720):
    - kicker + serif title + caption + hairline (top)
    - 4 KPI badges band (optional)
    - LEFT: rotated axis "HIGHER-ORDER COGNITIVE DEMAND" with arrow (top) + dot (bottom)
    - CENTER: stepped horizontal-band pyramid · L1 bottom widest → Ln top narrowest
        each tier: hue-tinted rect + left hue bar + Ln id + CN name (serif) +
                   EN name (Inter bold caps · hue) + italic verbs +
                   right example + optional progress bar + %
    - MASTERY CLIFF callout (auto-computed max-drop tier · pinned to lower of the pair)
    - RIGHT SIDEBAR (optional):
        · TIER MASTERY panel · one row per tier with 90-px bar
        · ACTION VERBS panel · hue bar + Ln + short verb group
        · HOW TO READ mini panel
    - LEGEND (bottom left) + SOURCE/READING dual footer

Elasticity:
    * n_tiers ∈ [3, 7]
    * CN name / EN name / verbs / example / mastery_pct optional per tier
    * KPI band toggles off when kpis=[] · sidebar toggles off when has_sidebar=False
    * callout auto-computed as max-Δpct tier · pass callout={"enabled": False} to hide

API:
    render_hero_embed_bl_bloom_v2(data, palette=None, params=None) -> str
    build_bloom_tree(tiers=..., kpis=..., callout=..., ...) -> Tree
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from ..schemas import Tree, TreeNode
from ..palettes import Palette
from ..engine import esc
from ..layouts.bloom_v2 import bloom_v2_layout, LayoutOverflow, BloomParams
from ..skins.editorial_atelier import (
    BONE_RUST, HUE, FONT_SANS, FONT_SERIF,
)
from ..skins.registry import get_active_skin as _get_active_skin


def _try_skin_draw(kind: str, x: float, y: float, w: float, h: float,
                   label: str, palette, **kwargs):
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
# baseline data · matches step1 reference SVG
# ═════════════════════════════════════════════════════════════════

# (cn, en, verbs, example, hue, mastery_pct)
BASELINE_TIERS: List[Tuple[str, str, str, str, str, Optional[float]]] = [
    ("记忆", "REMEMBER",   "recall · list · identify · 复述 / 识别",
     "transformer · attention · RoPE 术语背诵", "blue",    100.0),
    ("理解", "UNDERSTAND", "explain · summarize · paraphrase · 解释 / 归纳",
     "解释 GQA 比 MHA 推理更快的原因",         "green",    95.0),
    ("应用", "APPLY",      "implement · execute · demonstrate · 实施 / 执行",
     "在 1× H100 上 72h 内训完 1B 模型",         "gold_p",   84.0),
    ("分析", "ANALYZE",    "differentiate · decompose · relate · 拆解 / 关联",
     "loss 曲线 regime shift · GNS 分析",       "orange",   72.0),
    ("评价", "EVALUATE",   "critique · justify · defend · 论证 / 决策",
     "在 $1M + 40B token 预算下 MoE vs dense",  "magenta",  59.0),
    ("创造", "CREATE",     "design · produce · originate · 设计 / 产出",
     "设计新的多跳推理评测基准",                "olive",    35.0),
]

BASELINE_KPIS: List[Dict[str, str]] = [
    {"kicker": "TIERS",           "value": "6",       "note": "Anderson revised", "hue": "blue"},
    {"kicker": "CURRICULUM SPAN", "value": "L1 → L6", "note": "full ladder",       "hue": "green"},
    {"kicker": "COHORT",          "value": "n = 48",  "note": "2026 fall intake",  "hue": "orange"},
    {"kicker": "AVG MASTERY",     "value": "74%",     "note": "across L1–L6",      "hue": "gold_p"},
]

BASELINE_LEGEND: List[Tuple[str, str, str]] = [
    # (kind, hue, label)
    ("rect_tint", "blue",   "tier 面板 · 每层一个认知模式"),
    ("bar",       "orange", "progress bar · cohort 掌握度"),
    ("callout",   "orange", "callout · 断层与拐点"),
]

BASELINE_HOW_TO_READ = [
    "宽度 = 覆盖任务面 · 上窄下宽",
    "条形 = cohort mastery %",
    "色相 = 各层认知模式",
]

# reference-aligned callout · pinned to L4 tier · "drops 13pt"
# Step-3f fix: shorten kicker + text so they FIT the 90×48 gutter_shrunk
# callout at 10.5pt without needing textLength strong-fit (which visually
# overflowed the rect on Georgia italic). Short strings (5-char "CLIFF" +
# 10-char "drops 13pt") land naturally at ~40-60px width << 82px safe zone.
BASELINE_CALLOUT: Dict[str, Any] = {
    "tier_num": 4,
    "kicker": "CLIFF",
    "text": "drops 13pt",
    "hue": "orange",
    "enabled": True,
}


def build_bloom_tree(
    tiers: Optional[List[Any]] = None,
    *,
    kicker: str = "§ BLOOM · COGNITIVE LADDER · ANDERSON 2001 REVISED",
    figure_title: str = "Bloom 认知阶梯 · Senior ML engineer 培养路径 6 层全景",
    figure_caption: str = ("Anderson 2001 revised · L1 记忆 → Ln 创造 · "
                            "higher-order cognitive demand 上升 · 每层附动词族与真实任务范例"),
    source: str = ("L&D curriculum · Sept 2026 · cohort n=48 · "
                    "quarterly assessment · Anderson 2001 revised taxonomy"),
    reading: str = ('从底 L1 记忆 → 顶 L6 创造 · 每上一层认知复杂度递增 · '
                    '宽度收敛象征"能独立完成的人越来越少"'),
    fig_ref: str = "",
    kpis: Optional[List[Dict[str, str]]] = None,
    callout: Optional[Dict[str, Any]] = None,
    legend: Optional[List[Tuple[str, str, str]]] = None,
    how_to_read: Optional[List[str]] = None,
    has_sidebar: bool = True,
    axis_label: str = "HIGHER-ORDER  COGNITIVE  DEMAND",
    axis_top_tag: str = "CREATE",
    axis_bot_tag: str = "REMEMBER",
    encoding_note: Optional[str] = None,
    show_legend: bool = False,
) -> Tree:
    """Build a Bloom Tree.

    tiers : list of (cn, en, verbs, example, hue, mastery_pct)
        - 3-item form: (cn, verbs, hue) · en/example/pct default empty
        - 4-item form: (cn, en, verbs, example) · hue picks from cycle, no pct
        - 5-item form: (cn, en, verbs, example, hue) · pct=None
        - 6-item form: full
      tiers[0] = L1 (bottom, widest); tiers[-1] = Ln (top, narrowest).
    kpis : list of {kicker, value, note, hue} · [] disables the band · None uses baseline
    callout : {"tier_num": int, "kicker": str, "text": str, "hue": str, "enabled": bool}
        None = auto-detect max-drop tier · {"enabled": False} = hide
    legend : list of (kind, hue, label) · kind ∈ {rect_tint, bar, callout, dashed}
    how_to_read : list[str] · sidebar bottom mini panel
    has_sidebar : bool · False hides sidebar and expands pyramid rightward
    """
    src = tiers if tiers is not None else BASELINE_TIERS
    # if user passed baseline tiers (or nothing) and no callout override,
    # default to reference-aligned BASELINE_CALLOUT so hero baseline matches
    # step1 SVG exactly. When user passes custom tiers → auto-detect max drop.
    if callout is None and tiers is None:
        callout = dict(BASELINE_CALLOUT)
    _fallback_hues = ["blue", "green", "gold_p", "orange", "magenta", "olive", "cinnamon"]

    root = TreeNode(
        id="bloom", label="BLOOM",
        extra={
            "kpis": kpis if kpis is not None else BASELINE_KPIS,
            "callout": callout,   # None → layout will auto-compute
            "legend": legend if legend is not None else BASELINE_LEGEND,
            # Round-1: HOW TO READ default OFF · redundant with pyramid/sidebar
            # encoding. Callers can pass how_to_read=[...] explicitly to opt in.
            "how_to_read": how_to_read if how_to_read is not None else [],
            "has_sidebar": has_sidebar,
            "reading": reading,
            "fig_ref": fig_ref,
            "axis_label": axis_label,
            "axis_top_tag": axis_top_tag,
            "axis_bot_tag": axis_bot_tag,
            # Round-1: bottom LEGEND default OFF (chart-chatter, duplicates
            # the pyramid's own hue-to-tier encoding). Set show_legend=True
            # via build_bloom_tree(show_legend=True) or on the tree.extra.
            "show_legend": show_legend,
        },
    )
    cur = root
    for i, t in enumerate(src):
        if not isinstance(t, (list, tuple)):
            raise ValueError(f"tier[{i}] must be tuple/list, got {type(t)}")
        if len(t) == 6:
            cn, en, verbs, example, hue, pct = t
        elif len(t) == 5:
            cn, en, verbs, example, hue = t
            pct = None
        elif len(t) == 4:
            cn, en, verbs, example = t
            hue = _fallback_hues[i % len(_fallback_hues)]
            pct = None
        elif len(t) == 3:
            cn, verbs, hue = t
            en, example, pct = "", "", None
        elif len(t) == 2:
            cn, verbs = t
            en, example, pct = "", "", None
            hue = _fallback_hues[i % len(_fallback_hues)]
        else:
            raise ValueError(f"tier[{i}] must be 2/3/4/5/6-tuple, got {len(t)}")
        node = TreeNode(
            id=f"BL{i + 1}", label=str(cn), sublabel=str(en),
            detail=str(verbs), group=str(hue),
            extra={
                "example": str(example) if example else "",
                "mastery_pct": pct,
                "tier_num": i + 1,
            },
        )
        cur.children.append(node)
        cur = node

    if encoding_note is None:
        encoding_note = f"{len(src)} tier · Anderson 2001 revised · L1→L{len(src)}"
    tree = Tree(
        root=root,
        kicker=kicker,
        figure_title=figure_title,
        figure_caption=figure_caption,
        source=source,
        encoding_note=encoding_note,
    )
    # expose extra at Tree level for layout convenience
    setattr(tree, "extra", dict(root.extra))
    return tree


HERO_BL_DATA = build_bloom_tree()


# ═════════════════════════════════════════════════════════════════
# color fallback · dandelion editorial palette (aligned with step1 ref)
# ═════════════════════════════════════════════════════════════════

_DANDELION_HUE = {
    "blue":     "rgba(56,68,96,1)",       # L1 REMEMBER  deep navy
    "cinnamon": "rgba(168,88,42,1)",
    "green":    "rgba(16,106,82,1)",      # L2 UNDERSTAND
    "magenta":  "rgba(154,58,104,1)",     # L5 EVALUATE
    "olive":    "rgba(122,132,64,1)",     # L6 CREATE
    "rust":     "rgba(152,42,55,1)",
    "orange":   "rgba(168,88,42,1)",      # L4 ANALYZE  rust
    "gold_p":   "rgba(196,152,40,1)",     # L3 APPLY  gold
}


def _hue_dandelion(name: str) -> str:
    """Legacy dandelion accent — retained for backward compat. New code should
    route CALLOUT through palette.accent (see _callout_fill) so skin/palette
    changes actually reach the callout."""
    return _DANDELION_HUE.get(name, _DANDELION_HUE["cinnamon"])


def _hue(name: str) -> str:
    """Return palette hue (# hex or rgba) if present in current HUE (rebuilt by
    _apply_skin_palette), else fall back to dandelion accent. Previous version
    required '#'-prefix which threw all rgba() palettes back into dandelion —
    that was the "palette not swapping" bug in Round-1 audit."""
    c = HUE.get(name)
    if c:
        return c
    return _DANDELION_HUE.get(name, _DANDELION_HUE["cinnamon"])


def _callout_fill(pal) -> str:
    """Callout background · uses palette.accent (or .primary fallback) so the
    CLIFF callout adopts the current skin/palette instead of the hard-coded
    dandelion cinnamon `rgba(168,88,42,1)`. Round-1 audit issue B fix."""
    if pal is None:
        return _DANDELION_HUE["cinnamon"]
    for attr in ("accent", "primary", "ink"):
        v = getattr(pal, attr, None)
        if v:
            return v
    return _DANDELION_HUE["cinnamon"]


def _hue_rgba(name: str, alpha: float = 1.0) -> str:
    c = _hue(name)
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


def _rgb_triplet(color: str) -> Optional[Tuple[int, int, int]]:
    if not color:
        return None
    c = color.strip()
    if c.startswith("#") and len(c) == 7:
        h = c[1:]
        try:
            return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        except ValueError:
            return None
    import re
    m = re.match(r"rgba?\((\d+),(\d+),(\d+)", c)
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3))
    return None


def _with_alpha(color: str, alpha: float) -> str:
    rgb = _rgb_triplet(color)
    if rgb is None:
        return color
    return f"rgba({rgb[0]},{rgb[1]},{rgb[2]},{alpha:.2f})"


def _luma(color: str) -> float:
    rgb = _rgb_triplet(color)
    if rgb is None:
        return 0.0
    r, g, b = rgb
    return 0.299 * r + 0.587 * g + 0.114 * b


def _hue_visual(name: str, pal=None) -> str:
    """Return a hue safe for strokes and text on light slide backgrounds."""
    c = _hue(name)
    if _luma(c) >= 205.0:
        for attr in ("primary", "accent", "ink"):
            v = getattr(pal, attr, None) if pal is not None else None
            if v and _luma(v) < 160.0:
                return v
        return MUTE_INK
    return c


VIEW_W = 1400
VIEW_H = 720

MUTE_INK = "rgba(24,26,34,1)"
MUTE_SLATE = "rgba(115,120,132,1)"
MUTE_DIM = "rgba(64,70,82,1)"
BADGE_BG = "rgba(243,235,218,1)"
BADGE_STROKE = "rgba(175,178,188,1)"


# Bucket H (2026-09-13) · subtract_level 默认预设 · L3 = 极简 (默认)
_SUBTRACT_L0: List[str] = []
_SUBTRACT_L1: List[str] = ["tier_shadow", "layout_meta", "axis_dot"]
_SUBTRACT_L2: List[str] = _SUBTRACT_L1 + ["axis_label", "callout_kicker"]
_SUBTRACT_L3: List[str] = _SUBTRACT_L2 + [
    "tier_example", "tier_bar_bg", "tier_bar_fill", "tier_pct",
    "callout_rect", "callout_line",
]
_SUBTRACT_MAP = {"L0": _SUBTRACT_L0, "L1": _SUBTRACT_L1, "L2": _SUBTRACT_L2, "L3": _SUBTRACT_L3}


def _resolve_skip_kinds(skip_kinds: Optional[List[str]], subtract_level: str) -> set:
    if skip_kinds is not None:
        return set(skip_kinds)
    return set(_SUBTRACT_MAP.get(subtract_level, _SUBTRACT_L3))


def render_hero_embed_bl_bloom_v2(
    data: Tree = None,
    palette: Palette = None,
    params: Optional[BloomParams] = None,
    *,
    subtract_level: str = "L3",
    skip_kinds: Optional[List[str]] = None,
) -> str:
    """Render Bloom stepped pyramid · viewBox 1400×720."""
    # [FONT-PATCH-L1] font pass-through (standalone): ea.FONT_SANS/SERIF 覆写
    _MOD_FONT = globals()
    _ORIG_FONT = {k: _MOD_FONT[k] for k in ('FONT_SANS', 'FONT_SERIF') if k in _MOD_FONT}
    # [INK-PATCH-L1] skin-aware ink/gray
    _MOD_INK = globals()
    _ORIG_INK = {k: _MOD_INK[k] for k in ("MUTE_INK",) if k in _MOD_INK}
    try:
        from ..skins._base import _hex_to_rgba as _hex2rgba_ink
        _sk_ink = _get_active_skin()
        if _sk_ink is not None:
            _sp_ink = getattr(_sk_ink, 'PALETTE', None)
            if _sp_ink is not None and getattr(_sp_ink, 'ink', None):
                if 'MUTE_INK' in _MOD_INK: _MOD_INK['MUTE_INK'] = _hex2rgba_ink(_sp_ink.ink, 1.0)
    except Exception:
        pass
    try:
        from ..skins import editorial_atelier as _ea_font
        if 'FONT_SANS' in _MOD_FONT and _ea_font.FONT_SANS != _MOD_FONT['FONT_SANS']:
            _MOD_FONT['FONT_SANS'] = _ea_font.FONT_SANS
        if 'FONT_SERIF' in _MOD_FONT and _ea_font.FONT_SERIF != _MOD_FONT['FONT_SERIF']:
            _MOD_FONT['FONT_SERIF'] = _ea_font.FONT_SERIF
    except Exception:
        pass
    try:
        if data is None:
            data = HERO_BL_DATA
        pal = palette or BONE_RUST
        p = params or BloomParams()

        root = getattr(data, "root", None)
        if root is None:
            raise LayoutOverflow("bloom: no root")
        root_extra = getattr(root, "extra", {}) or {}
        kpis = root_extra.get("kpis", []) or []
        legend_items = root_extra.get("legend", []) or []
        how_to_read = root_extra.get("how_to_read", []) or []
        has_sidebar = bool(root_extra.get("has_sidebar", True))
        reading = str(root_extra.get("reading", "") or "")
        fig_ref = str(root_extra.get("fig_ref", "") or "")

        # ensure tree.extra reflects root.extra for layout
        if not hasattr(data, "extra") or not getattr(data, "extra", None):
            setattr(data, "extra", dict(root_extra))
        else:
            # merge (root_extra wins for structural keys)
            tree_extra = dict(data.extra)
            for k in ("callout", "axis_label", "axis_top_tag", "axis_bot_tag"):
                if k in root_extra:
                    tree_extra[k] = root_extra[k]
            setattr(data, "extra", tree_extra)

        # Bucket H · subtraction filter
        _skips = _resolve_skip_kinds(skip_kinds, subtract_level)
        render_sidebar = has_sidebar and "layout_meta" not in _skips
        raw_positions = bloom_v2_layout(
            data, params=p, has_sidebar=render_sidebar, has_kpi_band=bool(kpis)
        )
        raw_layout_meta = next(
            (pos for pos in raw_positions if pos.get("kind") == "layout_meta"),
            {},
        )
        positions = raw_positions
        if _skips:
            positions = [pos for pos in positions if pos.get("kind") not in _skips]
        has_visible_right_detail = any(
            pos.get("kind") in {"tier_example", "tier_bar_bg", "tier_bar_fill", "tier_pct"}
            for pos in positions
        )
        show_kpi_notes = bool(root_extra.get("show_kpi_notes", False))

        parts: List[str] = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {VIEW_W} {VIEW_H}">',
        ]
        # paper bg
        parts.append(
            f'<rect x="0" y="0" width="{VIEW_W}" height="{VIEW_H}" fill="{pal.bg}"/>'
        )

        # ── HEADER · kicker + title + caption + hairline ──
        # Round-1 fix: all body-tier text bumped to ≥15pt in SVG-space so that
        # after atomize scaling (900/1342 ≈ 0.67), on-slide font-size stays
        # ≥10pt hard red line.
        if getattr(data, "kicker", ""):
            parts.append(
                f'<text x="70" y="42" font-family="{FONT_SANS}" font-size="15" '
                f'font-weight="700" fill="{MUTE_SLATE}" letter-spacing="0.26em">'
                f'{esc(data.kicker)}</text>'
            )
        parts.append(
            f'<text x="70" y="76" font-family="{FONT_SERIF}" font-size="26" '
            f'font-weight="700" fill="{MUTE_INK}" letter-spacing="0.02em">'
            f'{esc(data.figure_title)}</text>'
        )
        # subtitle · only render when caption exists AND differs from title.
        _sub_txt = (getattr(data, "figure_caption", "") or "").strip()
        _title_txt = (getattr(data, "figure_title", "") or "").strip()
        if _sub_txt and _sub_txt != _title_txt:
            parts.append(
                f'<text x="70" y="100" font-family="{FONT_SANS}" font-size="15" '
                f'fill="{MUTE_DIM}" letter-spacing="0.02em">'
                f'{esc(_sub_txt)}</text>'
            )
        parts.append(
            f'<line x1="70" y1="118" x2="1330" y2="118" '
            f'stroke="{MUTE_INK}" stroke-width="0.8"/>'
        )

        # ── KPI BADGES BAND (optional) ──
        # Round-1: kicker 8.5→15, note 10→15 so slide-space ≥10pt. Row heights
        # slightly bumped (34→46) to hold the enlarged 3-row content.
        if kpis:
            kpi_y = 132
            kpi_h = 46
            kpi_gap = 20
            n_show = min(len(kpis), 4)
            kpi_left = 70.0
            kpi_right = float(raw_layout_meta.get("x_right", 1040.0) or 1040.0)
            kpi_w = max(180.0, (kpi_right - kpi_left - (n_show - 1) * kpi_gap) / n_show)
            for i in range(n_show):
                k = kpis[i]
                kx = kpi_left + i * (kpi_w + kpi_gap)
                hue = k.get("hue", "blue")
                c = _hue_visual(hue, pal)
                parts.append(
                    f'<rect x="{kx}" y="{kpi_y}" width="{kpi_w}" height="{kpi_h}" '
                    f'fill="{BADGE_BG}" stroke="{BADGE_STROKE}" stroke-width="0.6"/>'
                )
                parts.append(
                    f'<rect x="{kx}" y="{kpi_y}" width="4" height="{kpi_h}" '
                    f'fill="{c}"/>'
                )
                note = k.get("note")
                note_str = str(note) if note else ""
                value_str = str(k.get("value", ""))
                value_x = kx + 14
                kicker_full_w = kpi_w - 24.0
                kicker_str = str(k.get("kicker", "")).upper()
                kicker_tl = ""
                # kicker now 15pt tracked 0.16em → ~3.4px/char
                if len(kicker_str) * 3.4 > kicker_full_w:
                    kicker_tl = (
                        f' textLength="{kicker_full_w:.1f}" '
                        f'lengthAdjust="spacingAndGlyphs"'
                    )
                parts.append(
                    f'<text x="{value_x}" y="{kpi_y + 18}" font-family="{FONT_SANS}" '
                    f'font-size="15" font-weight="700" fill="{MUTE_SLATE}" '
                    f'letter-spacing="0.16em"{kicker_tl}>{esc(kicker_str)}</text>'
                )
                parts.append(
                    f'<text x="{value_x}" y="{kpi_y + 38}" font-family="{FONT_SERIF}" '
                    f'font-size="18" font-weight="700" fill="{MUTE_INK}">'
                    f'{esc(value_str)}</text>'
                )
                if show_kpi_notes and note_str:
                    value_w = max(24.0, len(value_str) * 12.0)
                    note_right = kx + kpi_w - 10
                    note_left_min = value_x + value_w + 12.0
                    note_available_w = max(20.0, note_right - note_left_min)
                    approx_w = 8.4 * len(note_str)
                    note_tl = ""
                    note_fs = 15.0
                    if approx_w > note_available_w:
                        note_tl = (
                            f' textLength="{note_available_w:.1f}" '
                            f'lengthAdjust="spacingAndGlyphs"'
                        )
                    parts.append(
                        f'<text x="{note_right}" y="{kpi_y + 38}" text-anchor="end" '
                        f'font-family="{FONT_SANS}" font-size="{note_fs:.1f}" '
                        f'fill="{MUTE_SLATE}"{note_tl}>{esc(note_str)}</text>'
                    )

        # ── AXIS (rotated left rail) ──
        # Round-1 fix: axis removed. rotate(-90) label survives atomize as a
        # horizontal 6pt sliver at x=4 (illegible after scale ≈0.67). Layout
        # still emits axis_* positions but preset ignores them; pyramid gets
        # left-margin bonus for larger tier CN glyphs.
        # (axis_line / axis_arrow / axis_dot / axis_label / axis_top_tag /
        #  axis_bot_tag are all skipped intentionally.)

        # ── TIER shadows first (drawn before rects) ──
        for pos in positions:
            if pos["kind"] == "tier_shadow":
                parts.append(
                    f'<rect x="{pos["x"]:.1f}" y="{pos["y"]:.1f}" '
                    f'width="{pos["w"]:.1f}" height="{pos["h"]:.1f}" '
                    f'fill="rgba(0,0,0,0.05)"/>'
                )

        # ── TIER RECTS · hue-tinted with hue stroke ──
        for pos in positions:
            if pos["kind"] == "tier_rect":
                c = _hue_visual(pos["hue"], pal)
                skin_svg = _try_skin_draw(
                    "bloom_tier_rect", pos["x"], pos["y"], pos["w"], pos["h"], "", pal,
                    hue=pos["hue"], hue_color=c,
                )
                if skin_svg:
                    parts.append(skin_svg)
                else:
                    parts.append(
                        f'<rect x="{pos["x"]:.1f}" y="{pos["y"]:.1f}" '
                        f'width="{pos["w"]:.1f}" height="{pos["h"]:.1f}" '
                        f'fill="{_with_alpha(c, 0.16)}" '
                        f'stroke="{_with_alpha(c, 0.95)}" stroke-width="1.4"/>'
                    )
            elif pos["kind"] == "tier_hue_bar":
                c = _hue_visual(pos["hue"], pal)
                parts.append(
                    f'<rect x="{pos["x"]:.1f}" y="{pos["y"]:.1f}" '
                    f'width="{pos["w"]:.1f}" height="{pos["h"]:.1f}" fill="{c}"/>'
                )
            elif pos["kind"] == "tier_guide_line" and not has_visible_right_detail:
                c = _hue_visual(pos["hue"], pal)
                parts.append(
                    f'<line x1="{pos["x1"]:.1f}" y1="{pos["y1"]:.1f}" '
                    f'x2="{pos["x2"]:.1f}" y2="{pos["y2"]:.1f}" '
                    f'stroke="{_with_alpha(c, 0.42)}" stroke-width="1.6"/>'
                )

        # ── TIER TEXT layer ──
        # Round-1: all body-tier text bumped to ≥15pt in SVG-space so on-slide
        # rendered pt (≈svg_pt × 0.67) stays ≥10pt hard red line.
        for pos in positions:
            k = pos["kind"]
            if k == "tier_id":
                c = _hue_visual(pos["hue"], pal)
                parts.append(
                    f'<text x="{pos["x"]:.1f}" y="{pos["y"]:.1f}" '
                    f'font-family="{FONT_SANS}" font-size="15" font-weight="700" '
                    f'fill="{c}" letter-spacing="0.18em">{esc(pos["text"])}</text>'
                )
            elif k == "tier_cn":
                fs = float(pos.get("font_size", 24.0))
                parts.append(
                    f'<text x="{pos["x"]:.1f}" y="{pos["y"]:.1f}" '
                    f'font-family="{FONT_SERIF}" font-size="{fs}" font-weight="700" '
                    f'fill="{MUTE_INK}">{esc(pos["text"])}</text>'
                )
            elif k == "tier_en":
                c = _hue_visual(pos["hue"], pal)
                parts.append(
                    f'<text x="{pos["x"]:.1f}" y="{pos["y"]:.1f}" '
                    f'font-family="{FONT_SANS}" font-size="16" font-weight="700" '
                    f'fill="{c}" letter-spacing="0.18em">{esc(pos["text"])}</text>'
                )
            elif k == "tier_verbs":
                parts.append(
                    f'<text x="{pos["x"]:.1f}" y="{pos["y"]:.1f}" '
                    f'font-family="{FONT_SANS}" font-size="15" font-style="italic" '
                    f'fill="{MUTE_SLATE}">{esc(pos["text"])}</text>'
                )
            elif k == "tier_example":
                parts.append(
                    f'<text x="{pos["x"]:.1f}" y="{pos["y"]:.1f}" text-anchor="end" '
                    f'font-family="{FONT_SANS}" font-size="15" font-weight="600" '
                    f'fill="{MUTE_INK}">{esc(pos["text"])}</text>'
                )
            elif k == "tier_bar_bg":
                c = _hue_visual(pos["hue"], pal)
                parts.append(
                    f'<rect x="{pos["x"]:.1f}" y="{pos["y"]:.1f}" '
                    f'width="{pos["w"]:.1f}" height="{pos["h"]:.1f}" '
                    f'fill="{_with_alpha(c, 0.22)}"/>'
                )
            elif k == "tier_bar_fill":
                c = _hue_visual(pos["hue"], pal)
                parts.append(
                    f'<rect x="{pos["x"]:.1f}" y="{pos["y"]:.1f}" '
                    f'width="{pos["w"]:.1f}" height="{pos["h"]:.1f}" '
                    f'fill="{_with_alpha(c, 0.92)}"/>'
                )
            elif k == "tier_pct":
                c = _hue_visual(pos["hue"], pal)
                parts.append(
                    f'<text x="{pos["x"]:.1f}" y="{pos["y"]:.1f}" text-anchor="end" '
                    f'font-family="{FONT_SERIF}" font-size="16" font-weight="700" '
                    f'fill="{c}">{esc(pos["text"])}</text>'
                )

        # ── CALLOUT ──
        for pos in positions:
            k = pos["kind"]
            if k == "callout_rect":
                # Round-1 fix: callout adopts palette.accent so skin/palette
                # changes propagate to the CLIFF callout (was hard-coded
                # cinnamon `rgba(168,88,42,1)` for every skin).
                c = _callout_fill(pal)
                parts.append(
                    f'<rect x="{pos["x"]:.1f}" y="{pos["y"]:.1f}" '
                    f'width="{pos["w"]:.1f}" height="{pos["h"]:.1f}" '
                    f'fill="{c}"/>'
                )
            elif k == "callout_kicker":
                fs = max(float(pos.get("font_size", 10.5)), 15.0)
                # constrain text within callout width: shrink glyphs via textLength
                tl = pos.get("text_length")
                length_attr = ""
                if tl is not None:
                    length_attr = f' textLength="{tl:.1f}" lengthAdjust="spacingAndGlyphs"'
                # letter-spacing from layout (drops from 0.22em to 0.06em when the
                # callout is narrow so "MASTERY CLIFF" still fits at 10.5pt)
                ls_em = pos.get("letter_spacing", 0.22)
                parts.append(
                    f'<text x="{pos["cx"]:.1f}" y="{pos["cy"]:.1f}" text-anchor="middle" '
                    f'font-family="{FONT_SANS}" font-size="{fs}" font-weight="700" '
                    f'fill="{pal.bg}" letter-spacing="{ls_em:.2f}em"{length_attr}>'
                    f'{esc(pos["text"])}</text>'
                )
            elif k == "callout_line":
                fs = max(float(pos.get("font_size", 13.0)), 16.0)
                tl = pos.get("text_length")
                length_attr = ""
                if tl is not None:
                    length_attr = f' textLength="{tl:.1f}" lengthAdjust="spacingAndGlyphs"'
                parts.append(
                    f'<text x="{pos["cx"]:.1f}" y="{pos["cy"]:.1f}" text-anchor="middle" '
                    f'font-family="{FONT_SERIF}" font-size="{fs}" font-weight="700" '
                    f'font-style="italic" fill="{pal.bg}"{length_attr}>'
                    f'{esc(pos["text"])}</text>'
                )

        # ── RIGHT SIDEBAR (optional) ──
        layout_meta = next((pos for pos in positions if pos["kind"] == "layout_meta"), None)
        if has_sidebar and layout_meta:
            tier_list = layout_meta.get("tiers", [])
            # sidebar column x
            sb_x = layout_meta.get("sidebar_x", 1140)
            sb_w = layout_meta.get("sidebar_w", 190)
            sb_right = sb_x + sb_w

            # ─ TIER MASTERY panel · rows from top-tier (Ln) down to L1
            # rename to "TIER PALETTE" when no pct data (test3 minimal) so the
            # label stays honest.
            panel_y = 200
            _panel_title = (
                "TIER MASTERY"
                if any(t.get("pct") is not None for t in tier_list)
                else "TIER PALETTE"
            )
            parts.append(
                f'<text x="{sb_x}" y="{panel_y}" font-family="{FONT_SANS}" font-size="15" '
                f'font-weight="700" fill="{MUTE_SLATE}" letter-spacing="0.18em">'
                f'{esc(_panel_title)}</text>'
            )
            parts.append(
                f'<line x1="{sb_x}" y1="{panel_y + 10}" x2="{sb_right}" y2="{panel_y + 10}" '
                f'stroke="{MUTE_INK}" stroke-width="0.6"/>'
            )
            row_h = 30
            # display top-tier first (Ln), descend to L1
            rev = list(reversed(tier_list))
            # detect whether ANY tier has pct data · when none, hide the bar/pct
            # column entirely so the sidebar row is just "L{n} · {cn}" (no faint
            # dead bars, no dash column). Fixes minimal-mode noise (test3).
            _sb_has_any_pct = any(
                t.get("pct") is not None for t in rev
            )
            for i, t in enumerate(rev):
                ry = panel_y + 22 + i * row_h
                hue = t.get("hue", "rust")
                c = _hue(hue)
                pct = t.get("pct")
                cn = t.get("cn", "")
                tn = t.get("tier_num", 0)
                label = f"L{tn} · {cn}" if cn else f"L{tn}"
                parts.append(
                    f'<text x="{sb_x}" y="{ry}" font-family="{FONT_SANS}" font-size="15" '
                    f'font-weight="700" fill="{MUTE_INK}" letter-spacing="0.06em">'
                    f'{esc(label)}</text>'
                )
                if not _sb_has_any_pct:
                    # add a small hue swatch instead of bar so column isn't blank
                    sw_w = 40.0
                    sw_h = 10.0
                    sw_x = sb_right - sw_w
                    sw_y = ry - 8.0
                    parts.append(
                        f'<rect x="{sw_x:.1f}" y="{sw_y:.1f}" width="{sw_w:.1f}" '
                        f'height="{sw_h:.1f}" fill="{_hue_rgba(hue, 0.85)}"/>'
                    )
                    continue
                # bar (right-aligned block · 90 wide, ends at sb_right - 30)
                bar_w = 90.0
                bar_h = 10.0
                bar_right = sb_right - 30.0
                bar_x = bar_right - bar_w
                bar_y = ry - 8.0
                parts.append(
                    f'<rect x="{bar_x:.1f}" y="{bar_y:.1f}" width="{bar_w:.1f}" '
                    f'height="{bar_h:.1f}" fill="{_hue_rgba(hue, 0.22)}"/>'
                )
                if pct is not None:
                    pf = max(0.0, min(1.0, float(pct) / 100.0))
                    parts.append(
                        f'<rect x="{bar_x:.1f}" y="{bar_y:.1f}" '
                        f'width="{bar_w * pf:.1f}" height="{bar_h:.1f}" '
                        f'fill="{_hue_rgba(hue, 0.92)}"/>'
                    )
                pct_text = f"{int(round(pct))}%" if pct is not None else "—"
                parts.append(
                    f'<text x="{sb_right}" y="{ry + 0.5:.1f}" text-anchor="end" '
                    f'font-family="{FONT_SERIF}" font-size="16" font-weight="700" '
                    f'fill="{MUTE_INK}">{esc(pct_text)}</text>'
                )

            # ─ ACTION VERBS panel (Ln → L1)
            av_y = panel_y + 22 + len(rev) * row_h + 22
            # Guard against overflow into footer (footer starts ~640 after
            # Round-1 footer-move; keep sidebar body above 620)
            if av_y + len(rev) * 28 + 60 > 620:
                av_y = min(av_y, 620 - len(rev) * 28 - 60)
            parts.append(
                f'<text x="{sb_x}" y="{av_y}" font-family="{FONT_SANS}" font-size="15" '
                f'font-weight="700" fill="{MUTE_SLATE}" letter-spacing="0.18em">'
                f'ACTION VERBS · 每层动词族</text>'
            )
            parts.append(
                f'<line x1="{sb_x}" y1="{av_y + 10}" x2="{sb_right}" y2="{av_y + 10}" '
                f'stroke="{MUTE_INK}" stroke-width="0.6"/>'
            )
            av_row_h = 28
            for i, t in enumerate(rev):
                ry = av_y + 22 + i * av_row_h
                hue = t.get("hue", "rust")
                c = _hue(hue)
                tn = t.get("tier_num", 0)
                # find verbs text (short form)
                verbs_short = ""
                en = t.get("en", "")
                parts.append(
                    f'<rect x="{sb_x}" y="{ry - 16}" width="3" height="20" fill="{c}"/>'
                )
                parts.append(
                    f'<text x="{sb_x + 10}" y="{ry}" font-family="{FONT_SANS}" '
                    f'font-size="15" font-weight="700" fill="{MUTE_INK}" '
                    f'letter-spacing="0.06em">L{tn}</text>'
                )
            # Verbs short label · derive from tree (walking chain)
            chain_verbs: List[str] = []
            cur = root
            while True:
                kids = list(getattr(cur, "children", []) or [])
                if not kids:
                    break
                child = kids[0]
                chain_verbs.append(str(getattr(child, "detail", "") or ""))
                cur = child
            n_tiers = len(chain_verbs)
            for i, t in enumerate(rev):
                ry = av_y + 22 + i * av_row_h
                idx_in_chain = n_tiers - 1 - i
                if 0 <= idx_in_chain < n_tiers:
                    verbs_full = chain_verbs[idx_in_chain]
                else:
                    verbs_full = ""
                short = _short_verbs(verbs_full, max_chars=18)
                parts.append(
                    f'<text x="{sb_x + 44}" y="{ry}" font-family="{FONT_SANS}" '
                    f'font-size="15" font-style="italic" fill="{MUTE_SLATE}">'
                    f'{esc(short)}</text>'
                )

            # ─ HOW TO READ mini panel (opt-in only)
            # Round-1: default hidden. how_to_read + LEGEND are redundant
            # chart-chatter. Sidebar already shows TIER MASTERY + ACTION VERBS
            # which explain the encoding by example. HOW TO READ only renders
            # when caller explicitly passes a non-empty list AND ACTION VERBS
            # doesn't already exceed vertical budget.
            htr_y = av_y + 22 + len(rev) * av_row_h + 24
            if how_to_read and htr_y + 60 < 640:
                parts.append(
                    f'<text x="{sb_x}" y="{htr_y}" font-family="{FONT_SANS}" '
                    f'font-size="15" font-weight="700" fill="{MUTE_SLATE}" '
                    f'letter-spacing="0.18em">HOW TO READ</text>'
                )
                parts.append(
                    f'<line x1="{sb_x}" y1="{htr_y + 10}" x2="{sb_right}" '
                    f'y2="{htr_y + 10}" stroke="{MUTE_INK}" stroke-width="0.6"/>'
                )
                for i, line in enumerate(how_to_read[:3]):
                    parts.append(
                        f'<text x="{sb_x}" y="{htr_y + 30 + i * 20}" '
                        f'font-family="{FONT_SANS}" font-size="15" fill="{MUTE_DIM}">'
                        f'{esc(line)}</text>'
                    )

        # ── LEGEND (bottom left, above footer hairline) ──
        # Round-1: default HIDDEN. LEGEND was a redundant re-explanation of the
        # tier rect + progress bar + callout encoding that already lives in the
        # pyramid itself. Only render when caller passes a non-empty legend AND
        # opts in via an implicit non-baseline (i.e. legend still gets built by
        # baseline default, so we now also gate on `show_legend` flag that
        # defaults False; callers can flip it).
        has_any_pct = any(
            pos["kind"] == "tier_bar_fill" for pos in positions
        )
        has_callout = any(
            pos["kind"] == "callout_rect" for pos in positions
        )
        show_legend = bool(root_extra.get("show_legend", False))
        if legend_items and show_legend:
            filtered_legend: List[Tuple[str, str, str]] = []
            for kind, hue, label in legend_items:
                if kind == "bar" and not has_any_pct:
                    continue
                if kind == "callout" and not has_callout:
                    continue
                filtered_legend.append((kind, hue, label))
        else:
            filtered_legend = []

        if filtered_legend:
            leg_y = 605
            cursor_x = 90.0
            parts.append(
                f'<text x="{cursor_x}" y="{leg_y}" font-family="{FONT_SANS}" '
                f'font-size="15" font-weight="700" fill="{MUTE_SLATE}" '
                f'letter-spacing="0.2em">LEGEND</text>'
            )
            cursor_x = 190.0
            for kind, hue, label in filtered_legend[:4]:
                c = _hue(hue)
                swatch_y = leg_y - 12
                if kind == "rect_tint":
                    parts.append(
                        f'<rect x="{cursor_x:.1f}" y="{swatch_y}" width="30" '
                        f'height="16" fill="{_hue_rgba(hue, 0.16)}" '
                        f'stroke="{_hue_rgba(hue, 0.95)}" stroke-width="1"/>'
                    )
                elif kind == "bar":
                    parts.append(
                        f'<rect x="{cursor_x:.1f}" y="{swatch_y}" width="30" '
                        f'height="16" fill="{_hue_rgba(hue, 0.92)}"/>'
                    )
                elif kind == "callout":
                    parts.append(
                        f'<rect x="{cursor_x:.1f}" y="{swatch_y}" width="30" '
                        f'height="16" fill="{c}"/>'
                    )
                elif kind == "dashed":
                    parts.append(
                        f'<rect x="{cursor_x:.1f}" y="{swatch_y}" width="30" '
                        f'height="16" fill="{pal.bg}" stroke="{c}" stroke-width="1" '
                        f'stroke-dasharray="4 3"/>'
                    )
                parts.append(
                    f'<text x="{cursor_x + 38:.1f}" y="{leg_y}" '
                    f'font-family="{FONT_SANS}" font-size="15" font-weight="600" '
                    f'fill="{MUTE_INK}">{esc(label)}</text>'
                )
                cursor_x += 38 + max(len(label) * 9.5, 160.0) + 40.0

        # ── FOOTER · source + reading + hairline ──
        # Round-1 fix: footer y=660/682/700 pushed content past atomize crop
        # (shrunk vb ended y≈691, on-slide ≈540 > 440 canvas). Move footer
        # into y=630/650/670 range so all rows land inside vb after shrink and
        # atomize to a 440-tall slide.
        parts.append(
            f'<line x1="70" y1="622" x2="1330" y2="622" '
            f'stroke="{MUTE_INK}" stroke-width="0.5"/>'
        )
        if getattr(data, "source", ""):
            parts.append(
                f'<text x="70" y="645" font-family="{FONT_SANS}" font-size="15" '
                f'font-weight="700" fill="{MUTE_SLATE}" letter-spacing="0.18em">'
                f'SOURCE</text>'
            )
            parts.append(
                f'<text x="160" y="645" font-family="{FONT_SANS}" font-size="15" '
                f'fill="{MUTE_DIM}">{esc(data.source)}</text>'
            )
        if reading:
            parts.append(
                f'<text x="70" y="672" font-family="{FONT_SANS}" font-size="15" '
                f'font-weight="700" fill="{MUTE_SLATE}" letter-spacing="0.18em">'
                f'READING</text>'
            )
            parts.append(
                f'<text x="160" y="672" font-family="{FONT_SANS}" font-size="15" '
                f'fill="{MUTE_DIM}">{esc(reading)}</text>'
            )
        if fig_ref:
            parts.append(
                f'<text x="1330" y="672" text-anchor="end" font-family="{FONT_SANS}" '
                f'font-size="15" font-style="italic" fill="{MUTE_SLATE}" '
                f'letter-spacing="0.06em">{esc(fig_ref)}</text>'
            )

        parts.append('</svg>')
        return "".join(parts)
    finally:
        try: _MOD_INK.update(_ORIG_INK)
        except Exception: pass
        _MOD_FONT.update(_ORIG_FONT)
def _short_verbs(text: str, max_chars: int = 20) -> str:
    """Trim verbs text · take first 2 tokens split on ' · ' or ' / '."""
    if not text:
        return ""
    # try ' · ' first
    for sep in [" · ", " / ", ", ", " "]:
        if sep in text:
            parts = [p_.strip() for p_ in text.split(sep) if p_.strip()]
            if len(parts) >= 2:
                out = f"{parts[0]} / {parts[1]}"
                if len(out) <= max_chars:
                    return out
                # fallback: just first
                if len(parts[0]) <= max_chars:
                    return parts[0]
                return parts[0][: max_chars]
    if len(text) <= max_chars:
        return text
    return text[: max_chars]


__all__ = [
    "BASELINE_TIERS", "BASELINE_KPIS", "BASELINE_LEGEND", "BASELINE_HOW_TO_READ",
    "BASELINE_CALLOUT",
    "build_bloom_tree", "HERO_BL_DATA",
    "render_hero_embed_bl_bloom_v2",
]
