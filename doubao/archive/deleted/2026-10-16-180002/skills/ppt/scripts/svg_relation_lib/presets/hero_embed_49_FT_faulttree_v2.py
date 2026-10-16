# Bucket H · subtract_level default "L3" (2026-09-13)
"""HERO EMBED · 49_FT_faulttree V2 · Hero canvas 1400×720 · dandelion fault-tree.

参考 step1_reference/faulttree_hero_reference.svg 1:1 复刻 + 完整数据可扩展:
  - chrome: serif title + caption + hairline + FIGURE 49 tag
  - KPI strip · 4 tiles (top-event P · MTBF/MTTR · min cut sets · dominant path)
  - tier rail (left labels + 3 dashed rules · tier 2-4 支持)
  - top event · red rectangle w/ shoulder (dominant color)
  - top gate · OR/AND shield/D-shape
  - intermediate cards · one per gate (hue-tinted rail + name + P)
  - sub gates · under each intermediate
  - basic events · circles at bottom (可选 gold ring for dominant)
  - sidebar: gate legend + probability table + recommendation
  - footer: 4-step "HOW TO READ" + source

build_faulttree_data kwargs:
    top_event: {code, title, sub, hue}
    gates: [{
        id, op ("OR"|"AND"), title, sub, hue, p,
        basics: [{code, title, sub, p, dominant?, dominant_share?}]
    }]  # 3-8 gates supported
    kpis: [{kicker, value, note, hue}]  # 4 tiles
    sidebar: {
        legend_kicker, legend_items: [{kind ("OR"|"AND"|"basic"), title, sub, formula?}],
        table_kicker, table_rows: [{label, p, share_pct, hue}],
        recommendation_kicker, recommendation_lines: [str]
    } | None  # None ⇒ baseline · [] / {} ⇒ hide sidebar
    footer_steps: [{n, hue, title, sub}]  # 4 steps
    kicker / figure_title / figure_caption / source / fig_tag / fig_tag_note
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from ..schemas import Tree, TreeNode
from ..palettes import Palette
from ..engine import esc
from ..skins.editorial_atelier import (
    BONE_RUST, FONT_SANS, FONT_SERIF,
)
from ..skins.registry import get_active_skin as _get_active_skin
from ..skins._base import _fit_font_size
from .._viewbox import shrink_viewbox


# ═════════════════════════════════════════════════════════════════
# color · dandelion hue map (对齐 step1 reference RGB)
# ═════════════════════════════════════════════════════════════════

_DANDELION_HUE: Dict[str, str] = {
    "blue":     "rgba(22,40,70,1)",       # M1 / network intermediate + AND ink
    "green":    "rgba(16,106,82,1)",      # M3 / auth intermediate
    "gold_p":   "rgba(168,88,42,1)",      # dominant gold ring · KPI 3
    "magenta":  "rgba(152,42,55,1)",      # M2 / DB failure · TOP EVENT
    "rust":     "rgba(168,88,42,1)",      # alias for gold_p
    "navy":     "rgba(22,40,70,1)",       # alias for blue
    "orange":   "rgba(168,88,42,1)",
    "cinnamon": "rgba(178,144,72,1)",
    "olive":    "rgba(88,64,52,1)",
    "slate":    "rgba(68,78,100,1)",
}

_HUE_OVERRIDE: Optional[Dict[str, str]] = None


def _parse_rgb(c: str):
    """color string ('#RRGGBB' | 'rgba(r,g,b,a)' | 'rgb(r,g,b)') → (r,g,b)."""
    if not c:
        return 128, 128, 128
    if c.startswith("#"):
        h = c.lstrip("#")
        if len(h) >= 6:
            try:
                return int(h[:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            except ValueError:
                return 128, 128, 128
        return 128, 128, 128
    m = re.match(r"rgba?\((\d+),\s*(\d+),\s*(\d+)", c)
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3))
    return 128, 128, 128


def _active_hue_map() -> Dict[str, str]:
    """当前 active skin 的 HUE map · 无 active skin 时 fallback 到 editorial_atelier
    的 HUE (因为 make_relation 对 editorial 不会 set_active_skin · 但会把
    palette 的 hues 写入 ea.HUE · 走 ea.HUE 才能拿到 bone_rust 覆盖后的 hue)."""
    if _HUE_OVERRIDE:
        return _HUE_OVERRIDE
    skin_mod = _get_active_skin()
    if skin_mod is not None:
        skin_hue = getattr(skin_mod, "HUE", None)
        if skin_hue:
            return skin_hue
    # fallback · editorial_atelier's HUE (palette-overridden by make_relation)
    try:
        from ..skins import editorial_atelier as _ea
        return getattr(_ea, "HUE", {}) or {}
    except Exception:
        return {}


def _relative_luminance(color: str) -> float:
    def _linear(channel: int) -> float:
        v = channel / 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4

    r, g, b = _parse_rgb(color)
    return 0.2126 * _linear(r) + 0.7152 * _linear(g) + 0.0722 * _linear(b)


def _contrast_ratio(a: str, b: str) -> float:
    la = _relative_luminance(a)
    lb = _relative_luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def _rgba_with_alpha(color: str, alpha: float) -> str:
    r, g, b = _parse_rgb(color)
    return f"rgba({r},{g},{b},{alpha:.3f})"


def _readable_ink(bg: str, preferred: str) -> str:
    if preferred and _contrast_ratio(bg, preferred) >= 4.5:
        return _rgba_with_alpha(preferred, 1.0)
    return "rgba(248,250,252,1)" if _relative_luminance(bg) < 0.45 else "rgba(15,23,42,1)"


def _dark_palette_overrides(palette: Optional[Palette]) -> Dict[str, str]:
    """Keep fault-tree text readable when the slide background is dark."""
    if palette is None:
        return {}
    bg = str(getattr(palette, "bg", "") or "")
    if not bg or _relative_luminance(bg) >= 0.32:
        return {}
    ink = _readable_ink(bg, str(getattr(palette, "ink", "") or ""))
    return {
        "BG_COLOR": bg,
        "PANEL_BG": "rgba(255,255,255,0.105)",
        "INK_COLOR": ink,
        "INK_DIM": "rgba(226,232,240,0.92)",
        "GRAY_COLOR": "rgba(203,213,225,0.86)",
        "HAIR_COLOR": "rgba(226,232,240,0.82)",
        "HAIR_LIGHT": "rgba(226,232,240,0.46)",
        "DASH_COLOR": "rgba(226,232,240,0.20)",
    }


def _hue_str(name: str, alpha: float = 1.0) -> str:
    """name → rgba() with alpha.

    优先级: active skin HUE > dandelion 硬编码 fallback.
    这样 boardroom/mbb skin 下 top-event / KPI / intermediate 会用 skin palette
    而不是硬编码 dandelion 色 (skin 视觉区分度 fix per R2 audit)."""
    skin_hue = _active_hue_map()
    c = skin_hue.get(name) if skin_hue else None
    if not c:
        base = _DANDELION_HUE.get(name, _DANDELION_HUE["magenta"])
        m = re.match(r"rgba\((\d+),\s*(\d+),\s*(\d+),\s*[\d.]+\)", base)
        if m:
            return f"rgba({m.group(1)},{m.group(2)},{m.group(3)},{alpha:.3f})"
        return base
    r, g, b = _parse_rgb(c)
    return f"rgba({r},{g},{b},{alpha:.3f})"


# ═════════════════════════════════════════════════════════════════
# baseline data · 对齐 step1 faulttree_hero_reference.svg
# ═════════════════════════════════════════════════════════════════

BASELINE_TOP: Dict[str, Any] = {
    "code":  "TOP EVENT · T",
    "title": "Payment service 12-min outage",
    "sub":   "P0 incident · 2026-09-07 · 04:12 UTC",
    "hue":   "magenta",
}

BASELINE_GATES: List[Dict[str, Any]] = [
    {
        "id": "M1", "op": "OR",
        "title": "Network partition", "sub": "AZ boundary",
        "hue": "blue", "p": "2.1e-4",
        "basics": [
            {"code": "B1", "title": "AZ-b split-brain", "sub": "AZ boundary",       "p": "1.2e-4"},
            {"code": "B2", "title": "DNS flap 43s",     "sub": "upstream resolver", "p": "9.0e-5"},
        ],
    },
    {
        "id": "M2", "op": "AND",
        "title": "Database failure", "sub": "storage tier",
        "hue": "magenta", "p": "3.4e-5",
        "basics": [
            {"code": "B3", "title": "Primary DB crash", "sub": "storage tier",     "p": "1.8e-3"},
            {"code": "B4", "title": "Replica lag > 8s", "sub": "async replication","p": "1.9e-2"},
        ],
    },
    {
        "id": "M3", "op": "OR",
        "title": "Auth service down", "sub": "token issuer",
        "hue": "green", "p": "2.8e-4",
        "basics": [
            {"code": "B5", "title": "JWT verify slow", "sub": "crypto lib",         "p": "5.0e-5"},
            {"code": "B6", "title": "IdP timeout",     "sub": "upstream provider",  "p": "6.4e-5"},
            {"code": "B7", "title": "Token svc OOM",   "sub": "dominant · 61%",
             "p": "1.7e-4", "dominant": True, "dominant_share": 61},
        ],
    },
]

BASELINE_KPIS: List[Dict[str, Any]] = [
    {"kicker": "TOP EVENT PROBABILITY", "value": "P(T) = 4.6e-4",
     "note": "per request · rolling 7d window", "hue": "magenta"},
    {"kicker": "MTBF / MTTR",           "value": "42 d  ·  12 min",
     "note": "availability 99.98% · SLO 99.95%", "hue": "blue"},
    {"kicker": "MINIMAL CUT SETS",      "value": "3 sets · order 2",
     "note": "{B2,B3} · {B4,B5} · {B7}", "hue": "gold_p"},
    {"kicker": "DOMINANT PATH",         "value": "B7 · Token OOM",
     "note": "contributes 61% of P(T) · single-point", "hue": "green"},
]

BASELINE_SIDEBAR: Dict[str, Any] = {
    "legend_kicker": "GATE LEGEND",
    "legend_items": [
        {"kind": "OR",  "title": "OR gate · disjunction",
         "sub": "Output fires if ANY child event fires",
         "formula": "P(out) = 1 - Pi(1 - Pi)"},
        {"kind": "AND", "title": "AND gate · conjunction",
         "sub": "Output fires only if ALL children fire",
         "formula": "P(out) = Pi Pi"},
        {"kind": "basic", "title": "Basic event",
         "sub": "Elementary cause · leaf with P value",
         "formula": ""},
    ],
    "table_kicker": "PROBABILITY TABLE",
    "table_rows": [
        {"label": "B7 · Token svc OOM",  "p": "1.7e-4", "share_pct": 61, "hue": "gold_p", "highlight": True},
        {"label": "B1 · AZ-b split-brain","p": "1.2e-4", "share_pct": 18, "hue": "blue"},
        {"label": "B2 · DNS flap 43s",    "p": "9.0e-5", "share_pct": 14, "hue": "blue"},
        {"label": "B6 · IdP timeout",     "p": "6.4e-5", "share_pct": 4,  "hue": "green"},
        {"label": "B5 · JWT verify slow", "p": "5.0e-5", "share_pct": 2,  "hue": "green"},
        {"label": "B3-B4 (AND) joint",    "p": "3.4e-5", "share_pct": 1,  "hue": "magenta"},
    ],
    "recommendation_kicker": "RECOMMENDATION",
    "recommendation_lines": [
        "Prioritise B7 mitigation",
        "HPA memory guard · circuit-break token",
        "issuer path · target P(T) < 1e-4 by Q4.",
    ],
}

BASELINE_FOOTER_STEPS: List[Dict[str, Any]] = [
    {"n": 1, "hue": "magenta", "title": "Read top event",
     "sub": "The undesired outcome we want to prevent (red bar)."},
    {"n": 2, "hue": "blue",    "title": "Descend through gates",
     "sub": "OR = any child fires · AND = all children must fire."},
    {"n": 3, "hue": "gold_p",  "title": "Identify basic events",
     "sub": "Circles at bottom · elementary faults with P value."},
    {"n": 4, "hue": "green",   "title": "Rank cut sets",
     "sub": "Sort minimal cut sets by P · fix top contributors first."},
]


def build_faulttree_data(
    top_event: Optional[Dict[str, Any]] = None,
    gates: Optional[List[Dict[str, Any]]] = None,
    kpis: Optional[List[Dict[str, Any]]] = None,
    sidebar: Optional[Dict[str, Any]] = None,
    footer_steps: Optional[List[Dict[str, Any]]] = None,
    kicker: str = "",
    figure_title: str = "Fault tree analysis · Payment service P0 outage",
    figure_caption: str = "",
    source: str = (
        "Source. Post-mortem · Payment platform · 2026-09-07 · "
        "illustrative reconstruction based on FTA (IEC 61025)."
    ),
    fig_tag: str = "FIGURE 49 · FAULT TREE",
    fig_tag_note: str = (
        "Read bottom-up · AND gate needs all children · "
        "OR gate needs any one · probabilities per event"
    ),
) -> Tree:
    """Build fault-tree Tree.

    None ⇒ baseline. [] / {} ⇒ hide that section (sidebar/kpis/footer).
    Gates must be 3-8. Each gate's basics 1-5. Total basics 5-15.
    """
    top = top_event if top_event is not None else BASELINE_TOP
    gts = gates if gates is not None else BASELINE_GATES
    if not gts:
        raise ValueError("faulttree: gates must be non-empty")
    if not (2 <= len(gts) <= 8):
        raise ValueError(f"faulttree: gates count must be 2-8 (got {len(gts)})")

    kps = kpis if kpis is not None else BASELINE_KPIS
    sb = sidebar if sidebar is not None else BASELINE_SIDEBAR
    fs = footer_steps if footer_steps is not None else BASELINE_FOOTER_STEPS

    total_basics = sum(len(g.get("basics") or []) for g in gts)
    # AUDIT SOP 1.4: no hardcoded caption fallback · use caller-provided only
    caption = figure_caption or ""

    root = TreeNode(
        id="top",
        label=str(top.get("title", "")),
        sublabel=str(top.get("sub", "")),
        group=str(top.get("hue", "magenta")),
        extra={
            "kind": "top",
            "code": top.get("code", "TOP EVENT · T"),
            "hue": top.get("hue", "magenta"),
            "gates": gts,
            "kpis": kps or [],
            "sidebar": sb or {},
            "footer_steps": fs or [],
            "fig_tag": fig_tag,
            "fig_tag_note": fig_tag_note,
        },
    )

    for i, g in enumerate(gts):
        gid = g.get("id") or f"M{i+1}"
        gate_node = TreeNode(
            id=gid,
            label=str(g.get("title", "")),
            sublabel=str(g.get("sub", "")),
            detail=str(g.get("p", "")),
            group=str(g.get("hue", "blue")),
            extra={"kind": "intermediate", "op": g.get("op", "OR"),
                   "p": g.get("p", "")},
        )
        for j, b in enumerate(g.get("basics") or []):
            gate_node.children.append(TreeNode(
                id=f"{gid}_b{j}",
                label=str(b.get("title", "")),
                sublabel=str(b.get("sub", "")),
                detail=str(b.get("p", "")),
                group=str(g.get("hue", "blue")),
                highlight=bool(b.get("dominant", False)),
                extra={"kind": "basic", "code": b.get("code", ""),
                       "dominant": bool(b.get("dominant", False)),
                       "dominant_share": b.get("dominant_share", 0)},
            ))
        root.children.append(gate_node)

    return Tree(
        root=root,
        kicker=kicker,
        figure_title=figure_title,
        figure_caption=caption,
        source=source,
        encoding_note="",
    )


HERO_FT_DATA = build_faulttree_data()

# Alias for gen_svg_relations manifest lookup (`build_ft_tree`).
build_ft_tree = build_faulttree_data


# ═════════════════════════════════════════════════════════════════
# constants · canvas + palette
# ═════════════════════════════════════════════════════════════════

VIEW_W = 1400
VIEW_H = 720

BG_COLOR    = "rgba(247,240,226,1)"       # cream
PANEL_BG    = "rgba(243,235,218,1)"       # KPI tile / gate fill
INK_COLOR   = "rgba(24,26,34,1)"
INK_DIM     = "rgba(64,70,82,1)"
GRAY_COLOR  = "rgba(115,120,132,1)"
HAIR_COLOR  = "rgba(24,26,34,1)"
HAIR_LIGHT  = "rgba(175,178,188,1)"
DASH_COLOR  = "rgba(120,124,132,0.15)"

# body area constants (aligned to reference)
CHROME_H = 130       # title + caption + hairline + fig_tag row (bumped for ×1.7 fonts)
KPI_Y = 140
KPI_H = 92           # bumped from 60 to fit 17pt kicker + 37pt value + 17pt note
BODY_TOP = 250       # tree top event begins
BODY_BOT = 664       # tree bottom (basic titles can push to ~y=660 with 2-line wrap)
FOOTER_Y = 676       # bottom rule · pushed 640 -> 676 to clear 2-line basic titles


# ═════════════════════════════════════════════════════════════════
# layout · derive positions from data (support gate 2-8, basics 1-5)
# ═════════════════════════════════════════════════════════════════

def _layout_positions(data: Tree, show_sidebar: bool = True) -> Dict[str, Any]:
    """Derive x/y positions for all elements. Uses horizontal band 70..960
    for the tree (or 70..1330 if no sidebar)."""
    root = data.root
    if root is None:
        raise ValueError("faulttree: data.root is None")
    extra = root.extra or {}
    gates = extra.get("gates") or []
    n_gates = max(1, len(gates))

    tree_x0 = 70
    tree_x1 = 1125 if show_sidebar else 1330  # sidebar 1145..1330 (185pt=13.2% of 1400)
    tree_w = tree_x1 - tree_x0
    # gate column centers · evenly distributed with equal margins
    step = tree_w / n_gates
    gate_cx = [tree_x0 + step * (i + 0.5) for i in range(n_gates)]

    # top event centered above (mid of tree area) · shifted down for taller KPI band
    top_cx = (tree_x0 + tree_x1) / 2
    top_x = top_cx - 170
    top_y = 252
    top_w = 340         # wider · fit 26pt title without ellipsis
    top_h = 104         # bumped 76 -> 104 · code(y+22) + title(y+58) + sub(y+88) no overlap

    # top gate y-range · bumped to sit below taller top card (top_bot=356)
    top_gate_y_top = 366
    top_gate_y_bot = 400

    # intermediate row · bumped down 8pt to hold new top-gate range
    inter_y = 428
    inter_h = 56             # bumped from 40 for ×1.7 fonts (11/17 -> 19)
    # inter_w · 240 -> 280 (bug C1 fix: give title breathing room next to P value)
    inter_w = min(280.0, step * 0.9)  # width bounded by column spacing
    # sub-gate row
    subgate_y_top = 498
    subgate_y_bot = 534

    # basic circle row · r bumped 26 -> 32 to hold 20pt B-code + 17pt P value
    basic_cy = 584
    basic_r_default = 32

    # basics per gate positions (evenly within column)
    # slot is the within-gate pitch between adjacent basic circles.
    # For small mode (nb=2, external title shown) we want slot large enough
    # (≥ ~140pt) so the below-circle title doesn't collide with its neighbor.
    basics_positions: List[List[Dict[str, Any]]] = []
    for gi, g in enumerate(gates):
        basics = g.get("basics") or []
        nb = max(1, len(basics))
        # R2 fix (basic-title collision on small mode): raise slot cap from
        # 80 → 140 (external title ~140pt @ 17pt fits without horizontal
        # collision). step / nb factor caps it further on wide gates.
        slot = min(140.0, step / max(nb, 2) * 0.95) if nb > 1 else 0
        # place symmetric around gate_cx[gi]
        if nb == 1:
            xs = [gate_cx[gi]]
        else:
            span = slot * (nb - 1)
            start = gate_cx[gi] - span / 2
            xs = [start + slot * k for k in range(nb)]
        row: List[Dict[str, Any]] = []
        for k, b in enumerate(basics):
            row.append({"cx": xs[k], "cy": basic_cy, "r": basic_r_default,
                        "b": b, "hue": g.get("hue", "blue"),
                        "column_pitch": slot})
        basics_positions.append(row)

    return {
        "tree_x0": tree_x0,
        "tree_x1": tree_x1,
        "gate_cx": gate_cx,
        "top_cx": top_cx,
        "top_x": top_x, "top_y": top_y, "top_w": top_w, "top_h": top_h,
        "top_gate_y_top": top_gate_y_top, "top_gate_y_bot": top_gate_y_bot,
        "inter_y": inter_y, "inter_w": inter_w, "inter_h": inter_h,
        "subgate_y_top": subgate_y_top, "subgate_y_bot": subgate_y_bot,
        "basic_cy": basic_cy, "basic_r": basic_r_default,
        "basics_positions": basics_positions,
    }


# ═════════════════════════════════════════════════════════════════
# render helpers
# ═════════════════════════════════════════════════════════════════

def _draw_chrome(title: str, caption: str, fig_tag: str, fig_tag_note: str,
                 show_fig_tag_note: bool = False) -> List[str]:
    out: List[str] = []
    # title 26 -> 44 (×1.7 · target slide-native ~27pt for 0.611 shrink)
    out.append(
        f'<text x="70" y="60" font-family="{FONT_SERIF}" font-size="30" '
        f'font-weight="600" fill="{INK_COLOR}" letter-spacing="0.1">{esc(title)}</text>'
    )
    if caption:
        # caption 12 -> 20
        out.append(
            f'<text x="70" y="88" font-family="{FONT_SANS}" font-size="20" '
            f'fill="{INK_DIM}" letter-spacing="0.2">{esc(caption)}</text>'
        )
    out.append(
        f'<line x1="70" y1="100" x2="1330" y2="100" '
        f'stroke="{HAIR_COLOR}" stroke-width="0.8"/>'
    )
    if fig_tag:
        # fig_tag kicker 10 -> 17
        out.append(
            f'<text x="70" y="120" font-family="{FONT_SANS}" font-size="17" '
            f'fill="{INK_DIM}" font-weight="600" letter-spacing="1.5">{esc(fig_tag)}</text>'
        )
    # fig_tag_note (how-to-read chatter) · default OFF
    if fig_tag_note and show_fig_tag_note:
        out.append(
            f'<text x="330" y="120" font-family="{FONT_SANS}" font-size="17" '
            f'fill="{GRAY_COLOR}" letter-spacing="0.4">{esc(fig_tag_note)}</text>'
        )
    return out


def _draw_kpi_strip(kpis: List[Dict[str, Any]]) -> List[str]:
    """4 KPI tiles across the top · widths auto-fitted to canvas."""
    out: List[str] = []
    if not kpis:
        return out
    n = min(4, len(kpis))
    # aligned to reference: x0=70, x1=1330, gap=16
    x0, x1 = 70, 1330
    total_gap = 16 * (n - 1)
    tile_w = (x1 - x0 - total_gap) / n
    for i in range(n):
        k = kpis[i]
        x = x0 + i * (tile_w + 16)
        y = KPI_Y
        c = _hue_str(k.get("hue", "blue"))
        out.append(
            f'<rect x="{x:.1f}" y="{y}" width="{tile_w:.1f}" height="{KPI_H}" '
            f'fill="{PANEL_BG}" stroke="{HAIR_LIGHT}" stroke-width="0.6"/>'
        )
        out.append(
            f'<rect x="{x:.1f}" y="{y}" width="4" height="{KPI_H}" fill="{c}"/>'
        )
        # kicker 10 -> 17
        out.append(
            f'<text x="{x + 16:.1f}" y="{y + 22}" font-family="{FONT_SANS}" '
            f'font-size="17" fill="{GRAY_COLOR}" font-weight="600" '
            f'letter-spacing="1.4">{esc(str(k.get("kicker", "")))}</text>'
        )
        # value fitted · target 37, min 18 (was 20 · bug C2 fix)
        # · right padding bumped 32 -> 40 to prevent CJK-heavy value clipping
        # · base_size 37 -> 32 when text is CJK-heavy (better safety margin
        #   because _visual_width approximation undercounts CJK glyph advance
        #   for serif faces at large sizes)
        # · Bucket C part 3 fix: CJK-heavy value like "B5 · 医生审核积压" still
        #   overflows the right edge because _visual_width undercounts CJK serif
        #   advance in Lark render. When value is CJK-heavy AND contains " · "
        #   AND has 4+ CJK chars, split at " · " into 2 lines at ~22pt each,
        #   pushing the note down 8pt. Non-CJK values keep single-line behaviour.
        val = str(k.get("value", ""))
        from ..skins._base import _is_cjk as _is_cjk_ch, _visual_width as _vw_ch
        cjk_count = sum(1 for ch in val if _is_cjk_ch(ch))
        has_cjk = cjk_count > 0
        # atomize fix (2026-09-14): non-CJK base 37→32 · Lark serif 37pt advance
        # widens vs _visual_width estimate for values like "B7 · Token OOM";
        # padding 40→60 gives extra safety margin so KPI value never clips chip.
        base_v = 32.0 if has_cjk else 32.0
        note_y_off = 78
        # trigger 2-line wrap for problematic CJK values
        force_wrap = has_cjk and cjk_count >= 4 and " · " in val
        if force_wrap:
            line1, line2 = val.split(" · ", 1)
            line_size = 22.0
            char_w_r = 0.55
            max_w_line = tile_w - 32
            def _fit_line(t: str, base: float) -> tuple[float, str]:
                w = _vw_ch(t, base * char_w_r)
                if w <= max_w_line:
                    return base, t
                s = max(max_w_line / w * base, 16.0)
                return s, t
            s1, t1 = _fit_line(line1, line_size)
            s2, t2 = _fit_line(line2, line_size)
            ls = min(s1, s2)
            out.append(
                f'<text x="{x + 16:.1f}" y="{y + 44}" font-family="{FONT_SERIF}" '
                f'font-size="{ls:.1f}" font-weight="700" fill="{c}">{esc(t1)}</text>'
            )
            out.append(
                f'<text x="{x + 16:.1f}" y="{y + 68}" font-family="{FONT_SERIF}" '
                f'font-size="{ls:.1f}" font-weight="700" fill="{c}">{esc(t2)}</text>'
            )
            note_y_off = 86
        else:
            fs, val_fit = _fit_font_size(val, tile_w - 60, base_v, min_size=18.0)
            out.append(
                f'<text x="{x + 16:.1f}" y="{y + 54}" font-family="{FONT_SERIF}" '
                f'font-size="{fs:.1f}" font-weight="700" fill="{c}">{esc(val_fit)}</text>'
            )
        # note 10 -> 17
        note = str(k.get("note", ""))
        out.append(
            f'<text x="{x + 16:.1f}" y="{y + note_y_off}" font-family="{FONT_SANS}" '
            f'font-size="17" fill="{GRAY_COLOR}">{esc(note)}</text>'
        )
    return out


def _draw_tier_rail(tree_x0: int, tree_x1: int) -> List[str]:
    """left tier labels + 3 dashed rules · CHATTER · default OFF at render.
    labels 10pt -> 17pt · positions updated for new taller geometry."""
    out: List[str] = []
    labels = [
        ("TIER 1 · TOP EVENT",             290),
        ("TIER 2 · INTERMEDIATE + GATES",  440),
        ("TIER 3 · BASIC EVENTS",          570),
    ]
    for txt, y in labels:
        out.append(
            f'<text x="82" y="{y}" font-family="{FONT_SANS}" font-size="17" '
            f'font-weight="700" fill="{GRAY_COLOR}" letter-spacing="1.4">'
            f'{esc(txt)}</text>'
        )
    # dashed rules
    rule_ys = [287, 437, 567]
    rule_x0 = [340, 480, 400]
    for rx0, ry in zip(rule_x0, rule_ys):
        out.append(
            f'<line x1="{rx0}" y1="{ry}" x2="{tree_x1}" y2="{ry}" '
            f'stroke="{DASH_COLOR}" stroke-width="0.4" '
            f'stroke-dasharray="2 4"/>'
        )
    return out


def _draw_or_shield(cx: float, cy_top: float, cy_bot: float,
                    stroke: str, stroke_w: float = 1.5,
                    label: str = "OR", label_fs: float = 17.0) -> List[str]:
    """OR shield · Q curves. Label 10 -> 17 (×1.7)."""
    out: List[str] = []
    dy = cy_bot - cy_top  # e.g. 40
    # scale q-curves proportionally
    w = 56  # bumped 40 -> 56 to hold 17pt OR label
    x_left = cx - w / 2
    x_right = cx + w / 2
    # control points (mimic reference)
    q1_cx, q1_cy = cx - w * 0.6, cy_top + dy * 0.25
    q1_ex, q1_ey = cx - w * 0.5, cy_bot - dy * 0.06
    q2_cx, q2_cy = cx, cy_bot
    q2_ex, q2_ey = cx + w * 0.5, cy_bot - dy * 0.06
    q3_cx, q3_cy = cx + w * 0.6, cy_top + dy * 0.25
    d = (f"M {cx:.1f} {cy_top:.1f} "
         f"Q {q1_cx:.1f} {q1_cy:.1f} {q1_ex:.1f} {q1_ey:.1f} "
         f"Q {q2_cx:.1f} {q2_cy:.1f} {q2_ex:.1f} {q2_ey:.1f} "
         f"Q {q3_cx:.1f} {q3_cy:.1f} {cx:.1f} {cy_top:.1f} Z")
    out.append(
        f'<path d="{d}" fill="{PANEL_BG}" stroke="{stroke}" '
        f'stroke-width="{stroke_w}"/>'
    )
    out.append(
        f'<text x="{cx:.1f}" y="{cy_top + dy * 0.72:.1f}" text-anchor="middle" '
        f'font-family="{FONT_SANS}" font-size="{label_fs:.1f}" font-weight="800" '
        f'fill="{stroke}" letter-spacing="1.2">{esc(label)}</text>'
    )
    return out


def _draw_and_shape(cx: float, cy_top: float, cy_bot: float,
                    stroke: str, stroke_w: float = 1.5,
                    label: str = "AND", label_fs: float = 17.0) -> List[str]:
    """AND gate · standard upper half-round arch."""
    out: List[str] = []
    dy = max(24.0, cy_bot - cy_top)
    w = 60  # wide enough for 17pt "AND" after atomization
    x_left = cx - w / 2
    x_right = cx + w / 2
    arch_base_y = cy_top + dy * 0.72
    d = (f"M {x_left:.1f} {cy_bot:.1f} "
         f"L {x_left:.1f} {arch_base_y:.1f} "
         f"Q {x_left:.1f} {cy_top:.1f} {cx:.1f} {cy_top:.1f} "
         f"Q {x_right:.1f} {cy_top:.1f} {x_right:.1f} {arch_base_y:.1f} "
         f"L {x_right:.1f} {cy_bot:.1f} "
         f"Z")
    out.append(
        f'<path d="{d}" fill="{PANEL_BG}" stroke="{stroke}" '
        f'stroke-width="{stroke_w}"/>'
    )
    out.append(
        f'<text x="{cx:.1f}" y="{cy_top + dy * 0.68:.1f}" text-anchor="middle" '
        f'font-family="{FONT_SANS}" font-size="{label_fs:.1f}" font-weight="800" '
        f'fill="{stroke}" letter-spacing="1.2">{esc(label)}</text>'
    )
    return out


_NO_LINE_START = set(":：,，.;；、!！?？)]）】》")


def _atomized_text_width(text: str, font_size: float) -> float:
    total = 0.0
    for ch in text:
        if ord(ch) > 0x2E80:
            total += font_size * 1.0
        elif ch.isspace():
            total += font_size * 0.35
        elif ch.isupper() or ch in "·×→↑↓←◆◈§":
            total += font_size * 0.7
        elif ch.isdigit():
            total += font_size * 0.58
        else:
            total += font_size * 0.55
    return total + font_size * 0.35


def _wrap_no_leading_punct(text: str, max_w: float, font_size: float, max_lines: int = 2) -> List[str]:
    if not text:
        return []
    if _atomized_text_width(text, font_size) <= max_w:
        return [text]

    # Prefer splitting "context: item" after the colon, never before it.
    for sep in ("：", ":"):
        if sep in text:
            idx = text.find(sep)
            left = text[:idx + 1].rstrip()
            right = text[idx + 1:].lstrip()
            if left and right and _atomized_text_width(right, font_size) <= max_w:
                return [left, right][:max_lines]

    tokens: List[str] = []
    buf = ""
    for ch in text:
        if ch in _NO_LINE_START or ch.isspace() or ord(ch) > 0x2E80:
            if buf:
                tokens.append(buf)
                buf = ""
            tokens.append(ch)
        else:
            buf += ch
    if buf:
        tokens.append(buf)

    lines: List[str] = []
    cur = ""
    for tok in tokens:
        if tok.isspace():
            if cur:
                cur += " "
            continue
        candidate = cur + tok
        if _atomized_text_width(candidate, font_size) <= max_w or tok in _NO_LINE_START:
            cur = candidate
            continue
        if cur.strip():
            lines.append(cur.rstrip())
            cur = ""
        if _atomized_text_width(tok, font_size) <= max_w:
            cur = tok
        else:
            for ch in tok:
                candidate = cur + ch
                if _atomized_text_width(candidate, font_size) <= max_w or ch in _NO_LINE_START:
                    cur = candidate
                else:
                    if cur:
                        lines.append(cur.rstrip())
                    cur = ch
    if cur.strip():
        lines.append(cur.rstrip())

    for i in range(1, len(lines)):
        while lines[i] and lines[i][0] in _NO_LINE_START:
            lines[i - 1] = (lines[i - 1] + lines[i][0]).rstrip()
            lines[i] = lines[i][1:].lstrip()
    lines = [line for line in lines if line]
    return lines[:max_lines] if lines else [text]


def _fit_wrapped_label(text: str, max_w: float, base_size: float = 17.0,
                       min_size: float = 13.0, max_lines: int = 2) -> tuple[float, List[str]]:
    size = base_size
    while size >= min_size:
        lines = _wrap_no_leading_punct(text, max_w, size, max_lines=max_lines)
        if len(lines) <= max_lines and all(_atomized_text_width(line, size) <= max_w + 1.0 for line in lines):
            return size, lines
        size -= 1.0
    return min_size, _wrap_no_leading_punct(text, max_w, min_size, max_lines=max_lines)


def _draw_top_event(top: Dict[str, Any], layout: Dict[str, Any],
                    root_extra: Dict[str, Any]) -> List[str]:
    """red rectangle w/ shoulder · TOP EVENT · 3-line stack (code / title / sub).

    Rows spaced ≥28pt apart in a top_h=104 box · no vertical overlap.
    Fill hue routes through active-skin HUE map (R2 fix per audit)."""
    out: List[str] = []
    x, y, w, h = layout["top_x"], layout["top_y"], layout["top_w"], layout["top_h"]
    hue = root_extra.get("hue", "magenta")
    c = _hue_str(hue, alpha=0.92)
    out.append(
        f'<rect x="{x:.1f}" y="{y}" width="{w}" height="{h}" '
        f'fill="{c}" stroke="{INK_COLOR}" stroke-width="1.2" rx="3"/>'
    )
    out.append(
        f'<rect x="{x:.1f}" y="{y}" width="{w}" height="6" '
        f'fill="rgba(255,255,255,0.25)"/>'
    )
    cx = x + w / 2
    # ── Row 1 · code kicker · 17pt · baseline y+26 ──
    code = str(root_extra.get("code", "TOP EVENT · T"))
    out.append(
        f'<text x="{cx:.1f}" y="{y + 26}" text-anchor="middle" '
        f'font-family="{FONT_SANS}" font-size="17" font-weight="700" '
        f'fill="rgba(247,240,226,0.9)" letter-spacing="1.6">{esc(code)}</text>'
    )
    # ── Row 2 · title · 26pt (fit down to 20pt) · baseline y+62 (≥28pt below code) ──
    title = str(top.get("title", ""))
    fs_t, t_fit = _fit_font_size(title, w - 28, 26.0, min_size=20.0)
    out.append(
        f'<text x="{cx:.1f}" y="{y + 62}" text-anchor="middle" '
        f'font-family="{FONT_SERIF}" font-size="{fs_t:.1f}" font-weight="700" '
        f'fill="rgba(247,240,226,1)">{esc(t_fit)}</text>'
    )
    # ── Row 3 · sub · 17pt · baseline y+92 (≥24pt below title) ──
    sub = str(top.get("sub", ""))
    if sub:
        fs_s, s_fit = _fit_font_size(sub, w - 28, 17.0, min_size=17.0)
        out.append(
            f'<text x="{cx:.1f}" y="{y + 92}" text-anchor="middle" '
            f'font-family="{FONT_SANS}" font-size="{fs_s:.1f}" '
            f'fill="rgba(247,240,226,0.9)">{esc(s_fit)}</text>'
        )
    return out


def _draw_intermediate(i: int, g: Dict[str, Any], layout: Dict[str, Any]) -> List[str]:
    """intermediate card at gate_cx[i]. Fonts 10/11/10 -> 17/19/17."""
    out: List[str] = []
    cx = layout["gate_cx"][i]
    w = layout["inter_w"]
    h = layout["inter_h"]
    y = layout["inter_y"]
    x = cx - w / 2
    hue = g.get("hue", "blue")
    c = _hue_str(hue)
    out.append(
        f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="{h}" '
        f'fill="{PANEL_BG}" stroke="{c}" stroke-width="1.2" rx="2"/>'
    )
    out.append(
        f'<rect x="{x:.1f}" y="{y}" width="4" height="{h}" fill="{c}"/>'
    )
    # ID line 10 -> 17
    gid = str(g.get("id", f"M{i+1}"))
    out.append(
        f'<text x="{x + 12:.1f}" y="{y + 22}" font-family="{FONT_SANS}" '
        f'font-size="17" font-weight="700" fill="{c}" letter-spacing="1.2">'
        f'{esc(gid + " · INTERMEDIATE")}</text>'
    )
    # p value right-aligned · 10 -> 17 · reserve gutter for title (bug C1 fix)
    p_val = str(g.get("p", ""))
    # estimate p value visual width @ 17pt serif bold · use worst-case
    # bound = 17pt * 0.6 * len(p_val) (serif bold is wider than char_w_ratio=0.55)
    # examples: "3.4e-3" (6 char), "5.4e-3" (6 char), "6.5e-5" (6 char) ~ 60pt
    p_val_w = 17.0 * 0.62 * len(p_val) if p_val else 0.0
    # gutter between title and P value (min 24pt · was 14pt · atomizer
    # under-counted CJK render width by ~10pt in Bucket C bug C1)
    p_gutter = 24.0
    # title max width: reserve for kicker padding on left (x+12) and P value + gutter on right
    # available = w - left_pad(12) - right_pad(12) - p_val_w - gutter
    title_max_w = max(60.0, w - 24 - p_val_w - p_gutter)

    # title 11 -> 19 · min 13 (was 17 · bug C1 fix: min_size cascaded to
    # rendering full-width text without truncation when min was 17pt · dropping
    # to 13pt lets long EN titles shrink instead of hard-cut)
    title = str(g.get("title", ""))
    fs_t, t_fit = _fit_font_size(title, title_max_w, 19.0, min_size=13.0)
    # if fit returned min_size but text still overflows (fit doesn't truncate),
    # hard-cut to prevent visual overlap with P value (bug C1 hard fallback).
    # Use +0.5pt tolerance to avoid floating-point tie-breaks triggering cuts.
    from ..skins._base import _visual_width as _vw
    if _vw(t_fit, fs_t * 0.55) > title_max_w + 0.5:
        # trim characters until it fits (no ellipsis)
        cut = ""
        for ch in t_fit:
            trial = cut + ch
            if _vw(trial, fs_t * 0.55) > title_max_w:
                break
            cut = trial
        t_fit = cut.rstrip() or t_fit[:1]
    out.append(
        f'<text x="{x + 12:.1f}" y="{y + 46}" font-family="{FONT_SERIF}" '
        f'font-size="{fs_t:.1f}" font-weight="700" fill="{INK_COLOR}">'
        f'{esc(t_fit)}</text>'
    )
    if p_val:
        out.append(
            f'<text x="{x + w - 8:.1f}" y="{y + 46}" text-anchor="end" '
            f'font-family="{FONT_SERIF}" font-size="17" font-weight="700" '
            f'fill="{c}">{esc(p_val)}</text>'
        )
    return out


def _draw_basic_circle(pos: Dict[str, Any], b: Dict[str, Any],
                       total_basics: int = 6,
                       show_basic_sub: bool = False) -> List[str]:
    """basic event circle + label + (optional) sub.

    When total_basics >= 10 (large dataset), external title/sub are suppressed
    to avoid column-pitch overlap · full title is available in the sidebar
    PROBABILITY TABLE. Only B-code + P value render inside the circle.

    On small datasets (total_basics < 10) the external title renders below
    the circle · width is clipped to `column_pitch - 8pt` (from layout) so
    that neighbors don't collide horizontally. Title auto-wraps to 2 lines
    if needed (R2 fix per audit).

    show_basic_sub gates the sub-label row (default OFF · was compound
    overlap chatter per audit).
    """
    out: List[str] = []
    cx, cy, r = pos["cx"], pos["cy"], pos["r"]
    hue = pos["hue"]
    c = _hue_str(hue)
    dominant = bool(b.get("dominant", False))
    if dominant:
        gold = _hue_str("gold_p")
        gold_bg = _hue_str("gold_p", alpha=0.14)
        # outer gold ring
        out.append(
            f'<circle cx="{cx:.1f}" cy="{cy}" r="{r + 3:.1f}" '
            f'fill="{gold_bg}" stroke="{gold}" stroke-width="2.4"/>'
        )
        out.append(
            f'<circle cx="{cx:.1f}" cy="{cy}" r="{r - 4:.1f}" '
            f'fill="{PANEL_BG}" stroke="{c}" stroke-width="1.2"/>'
        )
        code_c = gold
    else:
        out.append(
            f'<circle cx="{cx:.1f}" cy="{cy}" r="{r}" '
            f'fill="{PANEL_BG}" stroke="{c}" stroke-width="1.4"/>'
        )
        code_c = c
    # code 12 -> 20
    code = str(b.get("code", ""))
    out.append(
        f'<text x="{cx:.1f}" y="{cy - 6}" text-anchor="middle" '
        f'font-family="{FONT_SERIF}" font-size="20" font-weight="800" '
        f'fill="{code_c}">{esc(code)}</text>'
    )
    # p inline · shrunk 17 -> 13 to fit within circle diameter (bug C3 fix)
    # · "P=1.5e-2" @ 17pt ≈ 74pt but circle diameter is only 64pt (r=32)
    # · at 13pt ≈ 57pt · fits with margin
    # · cy+12 (was cy+14) tightens the vertical stack so title gap grows
    p_val = str(b.get("p", ""))
    if p_val:
        out.append(
            f'<text x="{cx:.1f}" y="{cy + 12}" text-anchor="middle" '
            f'font-family="{FONT_SANS}" font-size="13" font-weight="600" '
            f'fill="{_hue_str(hue, alpha=0.85)}">{esc("P=" + p_val)}</text>'
        )
    # For large datasets (>=10 basics), suppress external title/sub · overlap
    # per audit hard-red-line #2. Full name lives in PROBABILITY TABLE sidebar.
    if total_basics >= 10:
        return out
    # title (below circle) · width bounded by column_pitch (R2 fix)
    # column_pitch is the horizontal distance to the adjacent basic. Cap title
    # width at pitch - 8pt so neighboring titles never overlap. If title
    # contains "context: item", keep the colon with the context line.
    title = str(b.get("title", ""))
    pitch = float(pos.get("column_pitch", r * 5.4) or (r * 5.4))
    # if pitch is 0 (nb==1) use a generous cap
    max_w = max(80.0, pitch - 8.0) if pitch > 0 else r * 5.4
    title_fs, lines = _fit_wrapped_label(title, max_w, base_size=17.0, min_size=13.0, max_lines=2)
    for li, ln in enumerate(lines):
        y_row = cy + r + 22 + li * max(16.0, title_fs + 3.0)
        out.append(
            f'<text x="{cx:.1f}" y="{y_row}" text-anchor="middle" '
            f'font-family="{FONT_SANS}" font-size="{title_fs:.1f}" font-weight="600" '
            f'fill="{INK_COLOR}">{esc(ln)}</text>'
        )
    # sub · default OFF · was compound overlap chatter
    sub = str(b.get("sub", ""))
    if sub and show_basic_sub:
        fs_s, s_fit = _fit_font_size(sub, max_w, 17.0, min_size=17.0)
        sub_c = _hue_str("gold_p") if dominant else GRAY_COLOR
        weight = ' font-weight="600"' if dominant else ""
        # sub row sits below whatever title used (1 or 2 lines)
        sub_y = cy + r + 22 + len(lines) * 20 + 4
        out.append(
            f'<text x="{cx:.1f}" y="{sub_y}" text-anchor="middle" '
            f'font-family="{FONT_SANS}" font-size="{fs_s:.1f}" '
            f'fill="{sub_c}"{weight}>{esc(s_fit)}</text>'
        )
    return out


def _draw_connectors(gates: List[Dict[str, Any]], layout: Dict[str, Any]) -> List[str]:
    """all orthogonal connectors."""
    out: List[str] = []
    primary_conn = _rgba_with_alpha(INK_COLOR, 0.78)
    # top event → top gate (vertical short)
    tcx = layout["top_cx"]
    top_bot = layout["top_y"] + layout["top_h"]
    tg_top = layout["top_gate_y_top"]
    out.append(
        f'<path d="M {tcx:.1f} {top_bot} L {tcx:.1f} {tg_top}" '
        f'fill="none" stroke="{primary_conn}" stroke-width="1.4" '
        f'stroke-linecap="round"/>'
    )
    # top gate → each intermediate (bus)
    tg_bot = layout["top_gate_y_bot"]
    inter_y = layout["inter_y"]
    bus_y = tg_bot + (inter_y - tg_bot) * 0.4  # ~mid
    for i, gcx in enumerate(layout["gate_cx"]):
        if abs(gcx - tcx) < 1:
            # straight vertical
            out.append(
                f'<path d="M {tcx:.1f} {tg_bot} L {tcx:.1f} {inter_y}" '
                f'fill="none" stroke="{primary_conn}" stroke-width="1.4" '
                f'stroke-linecap="round"/>'
            )
        else:
            out.append(
                f'<path d="M {tcx:.1f} {tg_bot} L {tcx:.1f} {bus_y:.1f} '
                f'L {gcx:.1f} {bus_y:.1f} L {gcx:.1f} {inter_y}" '
                f'fill="none" stroke="{primary_conn}" stroke-width="1.4" '
                f'stroke-linecap="round" stroke-linejoin="round"/>'
            )
    # intermediate → sub-gate (vertical)
    inter_bot = inter_y + layout["inter_h"]
    sg_top = layout["subgate_y_top"]
    for i, g in enumerate(gates):
        gcx = layout["gate_cx"][i]
        c = _hue_str(g.get("hue", "blue"), alpha=0.75)
        out.append(
            f'<path d="M {gcx:.1f} {inter_bot} L {gcx:.1f} {sg_top}" '
            f'fill="none" stroke="{c}" stroke-width="1.4" stroke-linecap="round"/>'
        )
    # sub-gate → basic events (bus)
    sg_bot = layout["subgate_y_bot"]
    basic_cy = layout["basic_cy"]
    basic_r = layout["basic_r"]
    bus_below = sg_bot + (basic_cy - basic_r - sg_bot) * 0.4
    for i, g in enumerate(gates):
        gcx = layout["gate_cx"][i]
        c = _hue_str(g.get("hue", "blue"), alpha=0.65)
        for pos in layout["basics_positions"][i]:
            bx = pos["cx"]
            top_of_circle = basic_cy - basic_r
            if abs(bx - gcx) < 1:
                out.append(
                    f'<path d="M {gcx:.1f} {sg_bot} L {gcx:.1f} {top_of_circle}" '
                    f'fill="none" stroke="{c}" stroke-width="1.2" '
                    f'stroke-linecap="round"/>'
                )
            else:
                out.append(
                    f'<path d="M {gcx:.1f} {sg_bot} L {gcx:.1f} {bus_below:.1f} '
                    f'L {bx:.1f} {bus_below:.1f} L {bx:.1f} {top_of_circle}" '
                    f'fill="none" stroke="{c}" stroke-width="1.2" '
                    f'stroke-linecap="round" stroke-linejoin="round"/>'
                )
    return out


def _draw_sidebar(sidebar: Dict[str, Any],
                  show_gate_legend: bool = False,
                  show_share_bar: bool = False) -> List[str]:
    """Right sidebar (legend + probability table + recommendation).

    Width narrowed 1000..1330 (330pt/25%) -> 1100..1330 (230pt/17%) per audit.
    GATE LEGEND default OFF (redundant with fig_tag_note that we killed).
    SHARE bar column default OFF (4-5pt unreadable chatter).
    All fonts × 1.7 (10 -> 17, 10.5 -> 18).
    """
    out: List[str] = []
    if not sidebar:
        return out
    x0, x1 = 1145, 1330
    # vertical hairline separator (nudged in for narrower sidebar)
    # R3 fix (2026-09-14 · rec-truncation): separator top 250→240 · bottom
    # 612→692 to encompass tighter sidebar (table lifted 20pt · rec compressed
    # so last line fits above footer source at y=700).
    out.append(
        f'<line x1="1133" y1="240" x2="1133" y2="692" '
        f'stroke="rgba(170,174,182,0.6)" stroke-width="0.5"/>'
    )

    # ── gate legend (default OFF · chatter) ──
    # Keep the table clear of the fourth KPI block after slide atomization
    # clamps small SVG text upward to readable sizes.
    tbl_y_start = 258  # table starts here when legend is off
    if show_gate_legend:
        legend_k = str(sidebar.get("legend_kicker", "GATE LEGEND"))
        out.append(
            f'<text x="{x0}" y="270" font-family="{FONT_SANS}" font-size="17" '
            f'font-weight="700" fill="{INK_COLOR}" letter-spacing="1.4">'
            f'{esc(legend_k)}</text>'
        )
        out.append(
            f'<line x1="{x0}" y1="280" x2="{x1}" y2="280" '
            f'stroke="{HAIR_COLOR}" stroke-width="0.5"/>'
        )
        items = sidebar.get("legend_items") or []
        legend_y_start = 300
        for idx, it in enumerate(items[:3]):
            base_y = legend_y_start + idx * 60
            kind = it.get("kind", "OR")
            # draw icon at (x0+20, base_y..base_y+40)
            icx = x0 + 20
            if kind == "OR":
                out.extend(_draw_or_shield(icx, base_y, base_y + 40,
                                           stroke=INK_COLOR, stroke_w=1.2,
                                           label="OR", label_fs=17.0))
            elif kind == "AND":
                out.extend(_draw_and_shape(icx, base_y + 6, base_y + 44,
                                           stroke=INK_COLOR, stroke_w=1.2,
                                           label="AND", label_fs=17.0))
            else:  # basic
                out.append(
                    f'<circle cx="{icx}" cy="{base_y + 22}" r="18" '
                    f'fill="{PANEL_BG}" stroke="{INK_COLOR}" stroke-width="1.2"/>'
                )
                out.append(
                    f'<text x="{icx}" y="{base_y + 28}" text-anchor="middle" '
                    f'font-family="{FONT_SERIF}" font-size="17" font-weight="800" '
                    f'fill="{INK_COLOR}">B</text>'
                )
            # title 10.5 -> 18 · sub/formula 10 -> 17
            tx = x0 + 48
            out.append(
                f'<text x="{tx}" y="{base_y + 16}" font-family="{FONT_SANS}" '
                f'font-size="18" font-weight="700" fill="{INK_COLOR}">'
                f'{esc(it.get("title", ""))}</text>'
            )
            out.append(
                f'<text x="{tx}" y="{base_y + 36}" font-family="{FONT_SANS}" '
                f'font-size="17" fill="{GRAY_COLOR}">'
                f'{esc(it.get("sub", ""))}</text>'
            )
            formula = it.get("formula", "")
            if formula:
                out.append(
                    f'<text x="{tx}" y="{base_y + 54}" font-family="{FONT_SANS}" '
                    f'font-size="17" fill="{GRAY_COLOR}" font-style="italic">'
                    f'{esc(formula)}</text>'
                )
        tbl_y_start = legend_y_start + 3 * 60 + 20

    # ── probability table ── (10 -> 17)
    table_k = str(sidebar.get("table_kicker", "PROBABILITY TABLE"))
    tbl_y = tbl_y_start
    out.append(
        f'<text x="{x0}" y="{tbl_y}" font-family="{FONT_SANS}" font-size="17" '
        f'font-weight="700" fill="{INK_COLOR}" letter-spacing="1.4">'
        f'{esc(table_k)}</text>'
    )
    out.append(
        f'<line x1="{x0}" y1="{tbl_y + 10}" x2="{x1}" y2="{tbl_y + 10}" '
        f'stroke="{HAIR_COLOR}" stroke-width="0.5"/>'
    )
    # header · 10 -> 17
    out.append(
        f'<text x="{x0}" y="{tbl_y + 32}" font-family="{FONT_SANS}" '
        f'font-size="17" font-weight="600" fill="{GRAY_COLOR}" '
        f'letter-spacing="1">EVENT</text>'
    )
    out.append(
        f'<text x="{x1}" y="{tbl_y + 32}" text-anchor="end" '
        f'font-family="{FONT_SANS}" font-size="17" font-weight="600" '
        f'fill="{GRAY_COLOR}" letter-spacing="1">P</text>'
    )
    out.append(
        f'<line x1="{x0}" y1="{tbl_y + 40}" x2="{x1}" y2="{tbl_y + 40}" '
        f'stroke="rgba(170,174,182,0.5)" stroke-width="0.4"/>'
    )
    rows = sidebar.get("table_rows") or []
    max_rows = 6
    # atomize fix (2026-09-14 R2 · Round-1 check): 之前用 truncate 砍尾字符
    # ("Token svc OOM" -> "Token sv", "AZ-b split-brain" -> "AZ-b spl") 违反
    # 用户规则 "保留信息 > 装饰". 改为按需 2-line wrap: label 短则 1 行 (row=28pt)
    # · 长则拆 2 行 (row=40pt · R3 缩紧 44→40 · line1@row_y line2@row_y+16 有
    # 24pt 高度余量足够 · 缩后可让整个 sidebar 收进 slide 底沿).
    # P 值仍在第 1 行. 每行独立
    # 计算高度 · 短 label 不吃行高浪费.
    p_col_w = 60.0
    gutter = 12.0
    label_max_w = (x1 - x0) - p_col_w - gutter  # 113pt SVG budget
    # atomize char widths for accurate wrapping (upper 0.7, digit/lower 0.55,
    # punct 0.7, space 0.35 · matches atomize_svg_to_slide._char_width).
    def _atomize_w(s: str, sz: float) -> float:
        total = 0.0
        for ch in s:
            if ord(ch) > 0x2E80:
                total += sz * 1.0
            elif ch.isspace():
                total += sz * 0.35
            elif ch.isupper() or ch in '·×→↑↓←◆◈§':
                total += sz * 0.7
            else:
                total += sz * 0.55
        return total + sz * 0.5

    def _wrap_label_2line(s: str, max_w: float, sz: float) -> List[str]:
        """Wrap label into up to 2 lines on ' · ' / space / '-' boundaries.

        No truncation · every char preserved · returns [line1, line2] or [line1].
        """
        if _atomize_w(s, sz) <= max_w:
            return [s]
        # try semantic separators in priority order
        for sep in [" · ", " ", "-"]:
            if sep not in s:
                continue
            # greedy pack line1
            best_cut = -1
            # find all sep positions
            i = 0
            while True:
                p = s.find(sep, i)
                if p < 0:
                    break
                cand = s[:p]
                if _atomize_w(cand, sz) <= max_w:
                    best_cut = p
                    i = p + 1
                else:
                    break
            if best_cut > 0:
                line1 = s[:best_cut].rstrip()
                line2 = s[best_cut + len(sep):].lstrip() if sep != "-" else s[best_cut:].lstrip()
                if sep == "-":
                    # keep the hyphen with left half for readability
                    line1 = s[:best_cut + 1].rstrip()
                    line2 = s[best_cut + 1:].lstrip()
                return [line1, line2]
        # last-resort: char-boundary split (still no truncation)
        line1 = ""
        for ch in s:
            trial = line1 + ch
            if _atomize_w(trial, sz) > max_w:
                break
            line1 = trial
        remaining = s[len(line1):]
        return [line1, remaining] if remaining else [line1]

    # measure each row · sum heights · confirm sidebar has room. row heights:
    # 1-line: 28pt, 2-line: 40pt (R3 · 44→40 tighter).
    row_specs: List[Dict[str, Any]] = []
    for r in rows[:max_rows]:
        label = str(r.get("label", ""))
        if _atomize_w(label, 17.0) <= label_max_w:
            lines = [label]
            line_fs = 17.0
            row_h_i = 28
        else:
            line_fs = 15.0
            lines = _wrap_label_2line(label, label_max_w, line_fs)
            # if still too wide at 15pt · shrink to 13pt (last resort)
            if any(_atomize_w(ln, line_fs) > label_max_w for ln in lines):
                line_fs = 13.0
                lines = _wrap_label_2line(label, label_max_w, line_fs)
            row_h_i = 40 if len(lines) >= 2 else 28
        row_specs.append({"lines": lines, "fs": line_fs, "h": row_h_i, "r": r})

    y_cursor = tbl_y + 62
    for spec in row_specs:
        row_y = y_cursor
        r = spec["r"]
        hue = r.get("hue", "blue")
        c = _hue_str(hue)
        weight = "700" if r.get("highlight", False) else "600"
        lines = spec["lines"]
        line_fs = spec["fs"]
        for k, ln in enumerate(lines[:2]):
            out.append(
                f'<text x="{x0}" y="{row_y + k * 16:.1f}" font-family="{FONT_SANS}" '
                f'font-size="{line_fs:.1f}" font-weight="{weight}" fill="{INK_COLOR}">'
                f'{esc(ln)}</text>'
            )
        # P value right-aligned at x1 · aligned with first label line
        out.append(
            f'<text x="{x1}" y="{row_y}" text-anchor="end" font-family="{FONT_SERIF}" '
            f'font-size="17" font-weight="700" fill="{c}">'
            f'{esc(str(r.get("p", "")))}</text>'
        )
        # share bar · default OFF (chatter · 4-5pt unreadable)
        if show_share_bar:
            share_pct = float(r.get("share_pct", 0) or 0)
            bar_w = 60
            fill_w = min(bar_w, max(0, share_pct * bar_w / 100.0))
            c_bar = _hue_str(hue, alpha=0.92)
            out.append(
                f'<rect x="{x1 - bar_w - 8}" y="{row_y - 12}" width="{bar_w}" height="8" '
                f'fill="rgba(170,174,182,0.25)"/>'
            )
            if fill_w > 0:
                out.append(
                    f'<rect x="{x1 - bar_w - 8}" y="{row_y - 12}" width="{fill_w:.1f}" height="8" '
                    f'fill="{c_bar}"/>'
                )
        y_cursor += spec["h"]
    # variable-height compat: expose y_cursor as end-of-table for rec below
    _table_end_y = y_cursor

    # ── recommendation ──
    # rec_y positioned below probability table (uses variable per-row heights)
    rec_y = _table_end_y + 8
    out.append(
        f'<line x1="{x0}" y1="{rec_y}" x2="{x1}" y2="{rec_y}" '
        f'stroke="rgba(170,174,182,0.4)" stroke-width="0.4"/>'
    )
    # rec kicker 10 -> 17
    rec_k = str(sidebar.get("recommendation_kicker", "RECOMMENDATION"))
    out.append(
        f'<text x="{x0}" y="{rec_y + 24}" font-family="{FONT_SANS}" '
        f'font-size="17" font-weight="700" fill="{INK_COLOR}" '
        f'letter-spacing="1.4">{esc(rec_k)}</text>'
    )
    lines = sidebar.get("recommendation_lines") or []
    rec_max_w = x1 - x0
    # atomize fix (2026-09-14 R2): moved _vw / char_w scope · outer removed by
    # R2 sidebar rewrite. Recommendation still uses bullet-boundary wrap.
    from ..skins._base import _visual_width as _vw
    char_w = 9.4
    # R7 fix (2026-09-13 · blueprint P5): 不再硬截 · wrap 到 2 行 (per line)
    # 之前 char_w=9.4 + no-wrap → "HPA memory guard · cir" 断词.
    # R9 fix (2026-09-13 · blueprint P5 audit): 之前 word-boundary wrap 把
    # "HPA memory guard · circuit-break token" 断在 target/P(T) 语义边界·
    # 读者视觉上把 "circuit-break token issuer path · target" 当一句 · "P(T)"
    # 变成孤立句 · 语义比不 wrap 还差.
    # 现: 优先在 " · " (bullet 分隔符) 处 break · 无 bullet 才 fallback 到空格 ·
    # 保证每个 "·"-分隔的短语始终完整不断.
    # char_w 7.5 → 8.6 (匹配 Lark 实际 sans 17pt advance).
    def _wrap_at_bullet(s: str, max_w_px: float, cw: float) -> List[str]:
        """Wrap string at ' · ' bullet boundary first · fallback to space.

        Never split a bullet-delimited phrase mid-word.  Emits up to 3 lines;
        overflow silently truncated (caller controls line budget).
        """
        if _vw(s, cw) <= max_w_px:
            return [s]
        # split by " · " · keep bullets attached to preceding token
        parts = s.split(" · ")
        if len(parts) < 2:
            # no bullet · fallback to space-based greedy wrap
            words = s.split(" ")
            out_lines: List[str] = []
            cur = ""
            for w in words:
                trial = (cur + " " + w).strip()
                if _vw(trial, cw) <= max_w_px:
                    cur = trial
                else:
                    if cur:
                        out_lines.append(cur)
                    cur = w
            if cur:
                out_lines.append(cur)
            return out_lines
        # greedy pack: fit as many bullet-phrases per line as possible
        out_lines2: List[str] = []
        cur = ""
        for i, part in enumerate(parts):
            piece = part if i == 0 else " · " + part
            trial = cur + piece
            if _vw(trial, cw) <= max_w_px or not cur:
                cur = trial
            else:
                out_lines2.append(cur)
                # start next line without leading " · "
                cur = part
        if cur:
            out_lines2.append(cur)
        return out_lines2
    _rec_y_cursor = rec_y + 40
    for i, ln in enumerate(lines[:3]):
        wrapped = _wrap_at_bullet(str(ln), rec_max_w, char_w)
        for k, seg in enumerate(wrapped):
            y = _rec_y_cursor
            if i == 0 and k == 0:
                out.append(
                    f'<text x="{x0}" y="{y}" font-family="{FONT_SANS}" '
                    f'font-size="17" fill="{INK_COLOR}" font-weight="600">'
                    f'{esc(seg)}</text>'
                )
            elif i == 0:
                # continuation of first (priority) line
                out.append(
                    f'<text x="{x0}" y="{y}" font-family="{FONT_SANS}" '
                    f'font-size="17" fill="{INK_COLOR}" font-weight="600">'
                    f'{esc(seg)}</text>'
                )
            else:
                out.append(
                    f'<text x="{x0}" y="{y}" font-family="{FONT_SANS}" '
                    f'font-size="17" fill="{GRAY_COLOR}">{esc(seg)}</text>'
                )
            _rec_y_cursor += 18  # R3: 20→18 tighter · fits within slide bottom
        _rec_y_cursor += 2  # R3: 4→2 tighter gap between rec entries
    return out


def _draw_footer(steps: List[Dict[str, Any]], source: str,
                 show_steps: bool = False) -> List[str]:
    """4-step how-to-read row + source line.

    show_steps default OFF · steps row is 'HOW TO READ' chatter per audit.
    Source line still drawn if provided.
    All fonts ×1.7 (10 -> 17, 10.5 -> 18, 12 -> 20).
    """
    out: List[str] = []
    if show_steps and steps:
        out.append(
            f'<line x1="70" y1="{FOOTER_Y}" x2="1330" y2="{FOOTER_Y}" '
            f'stroke="{HAIR_COLOR}" stroke-width="0.5"/>'
        )
        out.append(
            f'<text x="70" y="{FOOTER_Y + 24}" font-family="{FONT_SANS}" '
            f'font-size="18" font-weight="700" fill="{INK_COLOR}" '
            f'letter-spacing="1.4">HOW TO READ · trace a failure path from '
            f'top event downward</text>'
        )
        n = min(4, len(steps))
        # anchor positions from reference
        x_anchors = [82, 382, 712, 1042]
        text_offsets = [110, 410, 740, 1070]
        for i in range(n):
            step = steps[i]
            hue = step.get("hue", "blue")
            c = _hue_str(hue)
            cx = x_anchors[i]
            tx = text_offsets[i]
            # circle & number bumped: r 11 -> 15, num 12 -> 20
            out.append(
                f'<circle cx="{cx}" cy="{FOOTER_Y + 60}" r="15" fill="{c}"/>'
            )
            out.append(
                f'<text x="{cx}" y="{FOOTER_Y + 66}" text-anchor="middle" '
                f'font-family="{FONT_SERIF}" font-size="20" font-weight="700" '
                f'fill="rgba(247,240,226,1)">{esc(str(step.get("n", i + 1)))}</text>'
            )
            fs_t, t_fit = _fit_font_size(
                str(step.get("title", "")), 300, 18.0, min_size=17.0)
            out.append(
                f'<text x="{tx}" y="{FOOTER_Y + 56}" font-family="{FONT_SANS}" '
                f'font-size="{fs_t:.1f}" font-weight="700" fill="{INK_COLOR}">'
                f'{esc(t_fit)}</text>'
            )
            fs_s, s_fit = _fit_font_size(
                str(step.get("sub", "")), 300, 17.0, min_size=17.0)
            out.append(
                f'<text x="{tx}" y="{FOOTER_Y + 76}" font-family="{FONT_SANS}" '
                f'font-size="{fs_s:.1f}" fill="{INK_DIM}">{esc(s_fit)}</text>'
            )
    # source (kept · not chatter) · 10 -> 17
    src_y = FOOTER_Y + 100 if (show_steps and steps) else FOOTER_Y + 24
    if source:
        out.append(
            f'<text x="70" y="{src_y}" font-family="{FONT_SANS}" font-size="17" '
            f'fill="{GRAY_COLOR}">{esc(source)}</text>'
        )
    # AUDIT SOP 1.4: right-side "Figure 49 · Fault tree · 3-tier" is hardcoded chatter · skip
    return out


# ═════════════════════════════════════════════════════════════════
# main render entrypoint
# ═════════════════════════════════════════════════════════════════

# Bucket H (2026-09-13) · subtract_level 默认预设 · L3 = 极简 (默认)
# faulttree 无 kind 减法空间 · 保留 API 兼容
_SUBTRACT_L0: List[str] = []
_SUBTRACT_L1: List[str] = []
_SUBTRACT_L2: List[str] = []
_SUBTRACT_L3: List[str] = []
_SUBTRACT_MAP = {"L0": _SUBTRACT_L0, "L1": _SUBTRACT_L1, "L2": _SUBTRACT_L2, "L3": _SUBTRACT_L3}


def _resolve_skip_kinds(skip_kinds: Optional[List[str]], subtract_level: str) -> set:
    if skip_kinds is not None:
        return set(skip_kinds)
    return set(_SUBTRACT_MAP.get(subtract_level, _SUBTRACT_L3))


def render_hero_embed_ft_faulttree_v2(
    data: Tree = HERO_FT_DATA,
    palette: Palette = BONE_RUST,
    show_sidebar: bool = True,
    shrink: bool = True,
    show_footer_steps: bool = False,
    show_fig_tag_note: bool = False,
    show_tier_rail: bool = False,
    show_gate_legend: bool = False,
    show_share_bar: bool = False,
    show_basic_sub: bool = False,
    *,
    subtract_level: str = "L3",
    skip_kinds: Optional[List[str]] = None,
) -> str:
    """Render fault-tree hero embed (1400x720).

    shrink=True (default) 在渲染结束后调用 shrink_viewbox 收紧 viewBox 到实际内容
    bbox + 12px padding · 便于 embed 到 slides.

    NEW Round-2 flags (all default OFF · chatter suppression per audit):
        show_footer_steps · 4-step HOW TO READ row
        show_fig_tag_note · Read bottom-up · AND requires all · OR requires any
        show_tier_rail    · TIER 1/2/3 rail labels (self-evident from geometry)
        show_gate_legend  · GATE LEGEND sidebar block (redundant chatter)
        show_share_bar    · SHARE % bar column (4-5pt unreadable)
        show_basic_sub    · basic-event sub-label row (compound overlap chatter)
    """

    # [SKIN-PATCH-L1] globals patch: skin.PALETTE 覆写模块级色常量
    _MOD_L1 = globals()
    _ORIG_L1 = {k: _MOD_L1[k] for k in ("BG_COLOR", "PANEL_BG", "INK_COLOR", "INK_DIM", "GRAY_COLOR", "HAIR_COLOR", "HAIR_LIGHT", "DASH_COLOR", "_HUE_OVERRIDE",)}
    _SKIN_L1 = _get_active_skin()
    if _SKIN_L1 is not None:
        _SP_L1 = getattr(_SKIN_L1, 'PALETTE', None)
        if _SP_L1 is not None:
            if getattr(_SP_L1, 'bg', None): _MOD_L1['BG_COLOR'] = _SP_L1.bg
            if getattr(_SP_L1, 'bg_alt', None): _MOD_L1['PANEL_BG'] = _SP_L1.bg_alt
            if getattr(_SP_L1, 'ink', None): _MOD_L1['INK_COLOR'] = _SP_L1.ink
            if getattr(_SP_L1, 'gray', None): _MOD_L1['INK_DIM'] = _SP_L1.gray
            if getattr(_SP_L1, 'gray', None): _MOD_L1['GRAY_COLOR'] = _SP_L1.gray
            if getattr(_SP_L1, 'hair', None): _MOD_L1['HAIR_COLOR'] = _SP_L1.hair
            if getattr(_SP_L1, 'hair', None): _MOD_L1['HAIR_LIGHT'] = _SP_L1.hair
            if getattr(_SP_L1, 'hair', None): _MOD_L1['DASH_COLOR'] = _SP_L1.hair
    try:
        from ..skins import editorial_atelier as _ea_runtime
        _MOD_L1["_HUE_OVERRIDE"] = dict(getattr(_ea_runtime, "HUE", {}) or {})
    except Exception:
        pass
    _MOD_L1.update(_dark_palette_overrides(palette))
    # [FONT-PATCH-L1] font pass-through: editorial_atelier.FONT_SANS/SERIF 覆写
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
        root = data.root
        if root is None:
            raise ValueError("faulttree: data.root is None")
        extra = root.extra or {}
        gates = extra.get("gates") or []
        kpis = extra.get("kpis") or []
        sidebar = extra.get("sidebar") if show_sidebar else {}
        footer_steps = extra.get("footer_steps") or []

        # total_basics used to gate basic-event external labels (overlap fix)
        total_basics = sum(len(g.get("basics") or []) for g in gates)

        layout = _layout_positions(data, show_sidebar=bool(sidebar))

        parts: List[str] = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {VIEW_W} {VIEW_H}">',
            f'<rect width="{VIEW_W}" height="{VIEW_H}" fill="{BG_COLOR}"/>',
        ]

        # ── chrome ── (fig_tag_note gated OFF · chatter)
        parts.extend(_draw_chrome(
            data.figure_title,
            data.figure_caption,
            extra.get("fig_tag", ""),
            extra.get("fig_tag_note", ""),
            show_fig_tag_note=show_fig_tag_note,
        ))

        # ── KPI strip ──
        parts.extend(_draw_kpi_strip(kpis))

        # ── tier rail ── (chatter · default OFF)
        if show_tier_rail:
            parts.extend(_draw_tier_rail(layout["tree_x0"], layout["tree_x1"]))

        # ── connectors (before nodes for z-order) ──
        parts.extend(_draw_connectors(gates, layout))

        # ── top event ──
        top_dict = {
            "title": root.label,
            "sub": root.sublabel,
        }
        parts.extend(_draw_top_event(top_dict, layout, extra))

        # ── top gate (mid) ──
        top_hue = extra.get("hue", "magenta")
        parts.extend(_draw_or_shield(
            layout["top_cx"], layout["top_gate_y_top"], layout["top_gate_y_bot"],
            stroke=INK_COLOR, stroke_w=1.5, label="OR", label_fs=17.0,
        ))
        # G0 label at right shoulder · 10 -> 17
        parts.append(
            f'<text x="{layout["top_cx"] + 34:.1f}" y="{layout["top_gate_y_bot"] - 18:.1f}" '
            f'font-family="{FONT_SANS}" font-size="17" fill="{GRAY_COLOR}" '
            f'font-style="italic">G0</text>'
        )

        # ── intermediates ──
        for i, g in enumerate(gates):
            parts.extend(_draw_intermediate(i, g, layout))

        # ── sub gates ──
        for i, g in enumerate(gates):
            cx = layout["gate_cx"][i]
            op = str(g.get("op", "OR")).upper()
            c = _hue_str(g.get("hue", "blue"))
            if op == "AND":
                parts.extend(_draw_and_shape(
                    cx, layout["subgate_y_top"], layout["subgate_y_bot"],
                    stroke=c, stroke_w=1.4, label="AND", label_fs=17.0,
                ))
            else:
                parts.extend(_draw_or_shield(
                    cx, layout["subgate_y_top"], layout["subgate_y_bot"],
                    stroke=c, stroke_w=1.4, label="OR", label_fs=17.0,
                ))
            # G-label · 10 -> 17
            gate_label = f"G{i + 1}"
            parts.append(
                f'<text x="{cx + 34:.1f}" y="{layout["subgate_y_bot"] - 18:.1f}" '
                f'font-family="{FONT_SANS}" font-size="17" fill="{GRAY_COLOR}" '
                f'font-style="italic">{esc(gate_label)}</text>'
            )

        # ── basic events ── (total_basics ≥ 10 → skip external title/sub)
        for i, g in enumerate(gates):
            for k, pos in enumerate(layout["basics_positions"][i]):
                b = pos["b"]
                parts.extend(_draw_basic_circle(
                    pos, b,
                    total_basics=total_basics,
                    show_basic_sub=show_basic_sub,
                ))

        # ── sidebar ── (gate legend + share bar gated OFF · chatter)
        if sidebar:
            parts.extend(_draw_sidebar(
                sidebar,
                show_gate_legend=show_gate_legend,
                show_share_bar=show_share_bar,
            ))

        # ── footer ── (steps default OFF · HOW TO READ chatter)
        parts.extend(_draw_footer(footer_steps, data.source,
                                  show_steps=show_footer_steps))

        parts.append('</svg>')
        svg = "".join(parts)
        if shrink:
            svg = shrink_viewbox(svg, pad_x=12.0, pad_y=12.0, shrink_bg=True)
        return svg
    finally:
        _MOD_L1.update(_ORIG_L1)
        _MOD_FONT.update(_ORIG_FONT)
__all__ = [
    "BASELINE_TOP", "BASELINE_GATES", "BASELINE_KPIS",
    "BASELINE_SIDEBAR", "BASELINE_FOOTER_STEPS",
    "build_faulttree_data", "build_ft_tree",
    "HERO_FT_DATA",
    "render_hero_embed_ft_faulttree_v2",
    "_DANDELION_HUE",
]
