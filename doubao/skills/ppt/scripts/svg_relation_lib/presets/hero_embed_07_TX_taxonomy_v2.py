# Bucket H · subtract_level default "L3" (2026-09-13)
"""HERO EMBED · 07_TX_taxonomy V2 · Hero canvas 1400×720 · dandelion 4-tier taxonomy.

参考 step1_reference/taxonomy_hero_reference.svg 1:1 复刻 + 完整数据可扩展性:
  - 顶部 chrome: serif title + caption + hairline + FIGURE 07 tag
  - 4 KPI 带 (domains / sub-groups / benchmarks / coverage)
  - 主 taxonomy body (4 tier · left → right):
      * T1 · ROOT   · 单张 navy card (x=70, w=90, h=70)
      * T2 · DOMAIN · 3-6 张 filled card (x=210, w=160, h=50)
      * T3 · SUB    · 2-5 张 per domain · stripe card (x=410, w=180, h=30, pitch 36)
      * T4 · LEAF   · 1-4 张 per sub · pill (x=640, w=200, h=16, pitch 16)
  - orthogonal connectors (根→域 · 域→子 · 子→叶) · hue tinted
  - sidebar (可选): coverage bar 段 + hue legend 段 + tier marker 段
  - footer: hairline + 3 notes + source (右下)

build_taxonomy_data kwargs:
    root: {label, sub, tag}                             # 中央 root card
    domains: [{
        key, code, label, sub, hue, leaf_count,
        subs: [{
            code, label, sub, hue?,        # hue 继承 domain
            leaves: [{code, label, tag}]  # 1-4 叶
        }]
    }]                                                   # 3-6 domain
    kpis: [{kicker, value, note, hue}]                   # 4 tile
    coverage: [{label, pct, note, hue}]                  # sidebar bar (可选)
    hue_legend: [{code, label, note, hue}]               # sidebar hue legend (可选)
    tier_markers: [{swatch_kind, label}]                 # sidebar tier legend (可选)
    show_sidebar: bool                                    # False → 主 body 满宽 (无 sidebar)
    kicker / figure_title / figure_caption / source / fig_tag / fig_tag_note
    notes_lines: [str] (up to 3)

密度支持:
    baseline · 4×3×2  (24 leaf)
    dense    · 5×4×3  (60 leaf · 逼近视觉上限)
    sparse   · 3×2×1  (6  leaf)
    minimal  · 3×2×1  · show_sidebar=False
"""
from __future__ import annotations

import re
from itertools import combinations
from typing import Any, Dict, List, Optional

from ..schemas import Tree, TreeNode
from ..palettes import Palette
from ..engine import esc
from ..skins.editorial_atelier import (
    BONE_RUST, HUE, FONT_SANS, FONT_SERIF,
)
from ..skins.registry import get_active_skin as _get_active_skin


# ═════════════════════════════════════════════════════════════════
# baseline data · 对齐 step1 taxonomy_hero_reference.svg
# ═════════════════════════════════════════════════════════════════

BASELINE_ROOT: Dict[str, Any] = {
    "label": "LLM",
    "sub": "BENCH",
    "tag": "ROOT",
}

BASELINE_DOMAINS: List[Dict[str, Any]] = [
    {
        "key": "reason", "code": "D1", "label": "Reasoning",
        "sub": "logic · math · plan",
        "hue": "magenta", "leaf_count": 6,
        "subs": [
            {"code": "S01", "label": "Mathematical", "sub": "arithmetic · algebra",
             "leaves": [
                 {"code": "L01", "label": "MATH-500",    "tag": "500 q"},
                 {"code": "L02", "label": "GSM8K",       "tag": "8.5k q"},
             ]},
            {"code": "S02", "label": "Abstract logic", "sub": "grid · induction",
             "leaves": [
                 {"code": "L03", "label": "ARC-AGI",       "tag": "400 tasks"},
                 {"code": "L04", "label": "BIG-Bench Hard","tag": "23 sub"},
             ]},
            {"code": "S03", "label": "Planning", "sub": "multi-step · agent",
             "leaves": [
                 {"code": "L05", "label": "PlanBench",     "tag": "1.2k plan"},
                 {"code": "L06", "label": "TravelPlanner", "tag": "1.6k"},
             ]},
        ],
    },
    {
        "key": "know", "code": "D2", "label": "Knowledge",
        "sub": "facts · common",
        "hue": "green", "leaf_count": 6,
        "subs": [
            {"code": "S04", "label": "Academic QA", "sub": "multi-domain · exam",
             "leaves": [
                 {"code": "L07", "label": "MMLU-Pro",     "tag": "12k q"},
                 {"code": "L08", "label": "GPQA-Diamond", "tag": "198 q"},
             ]},
            {"code": "S05", "label": "Open-domain", "sub": "trivia · retrieval",
             "leaves": [
                 {"code": "L09", "label": "TriviaQA",         "tag": "95k q"},
                 {"code": "L10", "label": "NaturalQuestions", "tag": "3.6k q"},
             ]},
            {"code": "S06", "label": "Commonsense", "sub": "pragmatics · WSC",
             "leaves": [
                 {"code": "L11", "label": "WinoGrande", "tag": "44k pr"},
                 {"code": "L12", "label": "PIQA",       "tag": "21k q"},
             ]},
        ],
    },
    {
        "key": "code", "code": "D3", "label": "Coding",
        "sub": "gen · repair · SQL",
        "hue": "slate", "leaf_count": 6,
        "subs": [
            {"code": "S07", "label": "Code synthesis", "sub": "function · unit test",
             "leaves": [
                 {"code": "L13", "label": "HumanEval+", "tag": "164 pb"},
                 {"code": "L14", "label": "MBPP+",      "tag": "378 pb"},
             ]},
            {"code": "S08", "label": "Repo repair", "sub": "issue → PR patch",
             "leaves": [
                 {"code": "L15", "label": "SWE-Bench",          "tag": "2.3k iss"},
                 {"code": "L16", "label": "SWE-Bench Verified", "tag": "500 iss"},
             ]},
            {"code": "S09", "label": "Data / SQL", "sub": "text2sql · pandas",
             "leaves": [
                 {"code": "L17", "label": "Spider 2.0", "tag": "632 q"},
                 {"code": "L18", "label": "DS-1000",    "tag": "1k pb"},
             ]},
        ],
    },
    {
        "key": "safe", "code": "D4", "label": "Safety",
        "sub": "truth · tox · jailbreak",
        "hue": "rust", "leaf_count": 6,
        "subs": [
            {"code": "S10", "label": "Truthfulness", "sub": "hallucination · calibration",
             "leaves": [
                 {"code": "L19", "label": "TruthfulQA", "tag": "817 q"},
                 {"code": "L20", "label": "HaluEval",   "tag": "35k"},
             ]},
            {"code": "S11", "label": "Toxicity / bias", "sub": "stereotype · harm",
             "leaves": [
                 {"code": "L21", "label": "ToxiGen", "tag": "274k"},
                 {"code": "L22", "label": "BBQ",     "tag": "58k q"},
             ]},
            {"code": "S12", "label": "Robustness", "sub": "jailbreak · redteam",
             "leaves": [
                 {"code": "L23", "label": "JailbreakBench", "tag": "100 pr"},
                 {"code": "L24", "label": "HarmBench",      "tag": "510 pr"},
             ]},
        ],
    },
]

BASELINE_KPIS: List[Dict[str, Any]] = [
    {"kicker": "DOMAINS",    "value": "4",   "note": "top-level buckets",     "hue": "magenta"},
    {"kicker": "SUB-GROUPS", "value": "12",  "note": "3 per domain · thematic","hue": "green"},
    {"kicker": "BENCHMARKS", "value": "24",  "note": "leaf-level test sets",  "hue": "rust"},
    {"kicker": "COVERAGE",   "value": "87%", "note": "of HELM v2 core suite", "hue": "slate"},
]

BASELINE_COVERAGE: List[Dict[str, Any]] = [
    {"label": "Reasoning", "pct": 90, "note": "6 of 7 targeted · math + logic strong", "hue": "magenta"},
    {"label": "Knowledge", "pct": 95, "note": "6 of 6 core · full academic suite",     "hue": "green"},
    {"label": "Coding",    "pct": 86, "note": "6 of 7 · repo-level agents pending",    "hue": "slate"},
    {"label": "Safety",    "pct": 86, "note": "6 of 7 · robustness redteam expanded",  "hue": "rust"},
]

BASELINE_HUE_LEGEND: List[Dict[str, Any]] = [
    {"code": "D1", "label": "Reasoning", "note": "math / logic", "hue": "magenta"},
    {"code": "D2", "label": "Knowledge", "note": "recall / QA",  "hue": "green"},
    {"code": "D3", "label": "Coding",    "note": "gen / repair", "hue": "slate"},
    {"code": "D4", "label": "Safety",    "note": "truth / harm", "hue": "rust"},
]

BASELINE_TIER_MARKERS: List[Dict[str, Any]] = [
    {"swatch_kind": "root",   "label": "T1 · root · single node"},
    {"swatch_kind": "domain", "label": "T2 · domain · filled card"},
    {"swatch_kind": "stripe", "label": "T3/T4 · sub & leaf · stripe"},
]

BASELINE_NOTES: List[str] = []  # chatter default off · pass notes_lines=[...] to opt-in


# ═════════════════════════════════════════════════════════════════
# dandelion hue palette (对齐 step1 reference RGB)
# ═════════════════════════════════════════════════════════════════

_DANDELION_HUE: Dict[str, str] = {
    "magenta":  "rgba(152,42,55,1)",     # D1 Reasoning
    "green":    "rgba(16,106,82,1)",     # D2 Knowledge
    "slate":    "rgba(68,78,100,1)",     # D3 Coding (navy)
    "rust":     "rgba(168,88,42,1)",     # D4 Safety
    "navy":     "rgba(22,40,70,0.97)",   # root fill
    "gold_p":   "rgba(182,138,56,1)",    # root accent / badge
    "blue":     "rgba(68,78,100,1)",     # alias for slate
    "orange":   "rgba(168,88,42,1)",     # alias for rust
    "cinnamon": "rgba(178,144,72,1)",
    "olive":    "rgba(88,64,52,1)",
}


def _hue_str(name: str, alpha: float = 1.0) -> str:
    """Resolve a hue name → rgba string.

    Priority (fix · 2026-09-11):
      1. Active skin's HUE dict (so boardroom_navy / mbb_consulting actually
         apply their own domain colors instead of being dandelion clones).
      2. Module-level HUE (= editorial_atelier.HUE, mutated by
         gen_svg_relations' _skin_override context) — this is the default
         path when skin=editorial_atelier and active skin stays None but
         ea.HUE reflects any user overrides / newly added keys (e.g. slate).
      3. _DANDELION_HUE baseline fallback (for keys like navy / gold_p that
         many skins don't ship — root card / accent still work everywhere).
    """
    # try active skin first
    try:
        skin = _get_active_skin()
        if skin is not None:
            skin_hue = getattr(skin, "HUE", None)
            if skin_hue and name in skin_hue:
                c = skin_hue[name]
                if isinstance(c, str) and c.startswith("#"):
                    h = c.lstrip("#")
                    r, g, b = int(h[:2], 16), int(h[2:4], 16), int(h[4:6], 16)
                    return f"rgba({r},{g},{b},{alpha:.3f})"
                if isinstance(c, str) and c.startswith("rgba"):
                    m = re.match(r"rgba\((\d+),\s*(\d+),\s*(\d+),\s*[\d.]+\)", c)
                    if m:
                        return f"rgba({m.group(1)},{m.group(2)},{m.group(3)},{alpha:.3f})"
                    return c
    except Exception:
        pass
    # module-level HUE (editorial_atelier.HUE) — reflects user overrides
    # via _skin_override context. Check before dandelion so newly added keys
    # (e.g. slate) resolve correctly for the default editorial_atelier path.
    c = HUE.get(name)
    if c is not None:
        if isinstance(c, str) and c.startswith("#"):
            h = c.lstrip("#")
            r, g, b = int(h[:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            return f"rgba({r},{g},{b},{alpha:.3f})"
        if isinstance(c, str) and c.startswith("rgba"):
            m = re.match(r"rgba\((\d+),\s*(\d+),\s*(\d+),\s*[\d.]+\)", c)
            if m:
                return f"rgba({m.group(1)},{m.group(2)},{m.group(3)},{alpha:.3f})"
            return c
    # fallback to dandelion baseline (navy / gold_p / etc that skins don't ship)
    base = _DANDELION_HUE.get(name)
    if base:
        m = re.match(r"rgba\((\d+),\s*(\d+),\s*(\d+),\s*[\d.]+\)", base)
        if m:
            return f"rgba({m.group(1)},{m.group(2)},{m.group(3)},{alpha:.3f})"
        return base
    # ultimate fallback: editorial rust
    return f"rgba(163,88,50,{alpha:.3f})"


# ═════════════════════════════════════════════════════════════════
# canvas constants (对齐 step1 SVG)
# ═════════════════════════════════════════════════════════════════

VIEW_W = 1400
VIEW_H = 720

BG_COLOR    = "rgba(247,240,226,1)"
KPI_BG      = "rgba(243,235,218,1)"
INK_COLOR   = "rgba(24,26,34,1)"
INK_DIM     = "rgba(64,70,82,1)"
GRAY_COLOR  = "rgba(115,120,132,1)"
HAIR_COLOR  = "rgba(24,26,34,1)"
HAIR_LIGHT  = "rgba(175,178,188,1)"

# body geometry
BODY_X0     = 60
ROOT_X      = 55
ROOT_W      = 170
ROOT_H      = 70
DOMAIN_X    = 260
DOMAIN_W    = 200
DOMAIN_H    = 50
SUB_X       = 485
SUB_W       = 240
SUB_H       = 30
LEAF_X      = 780
LEAF_W      = 200
LEAF_H      = 16
BODY_X1_MAIN = 1060    # right edge of leaf column area
BODY_X1_FULL = 1340    # right edge when no sidebar

# vertical layout region for body
BODY_Y0     = 210      # below section hairline
BODY_Y1     = 620      # top of footer band
BODY_MID_Y  = (BODY_Y0 + BODY_Y1) / 2

# sidebar geometry
SB_X_DIV    = 1080
SB_X0       = 1100
SB_X1       = 1340


# ═════════════════════════════════════════════════════════════════
# builder
# ═════════════════════════════════════════════════════════════════

def build_taxonomy_data(
    root: Optional[Dict[str, Any]] = None,
    domains: Optional[List[Dict[str, Any]]] = None,
    kpis: Optional[List[Dict[str, Any]]] = None,
    coverage: Optional[List[Dict[str, Any]]] = None,
    hue_legend: Optional[List[Dict[str, Any]]] = None,
    tier_markers: Optional[List[Dict[str, Any]]] = None,
    show_sidebar: bool = True,
    kicker: str = "",
    figure_title: str = "LLM Benchmark Taxonomy · four capability domains",
    # NOTE (2026-09-13 · R3 audit): 副标扩展成 LF + 数字 + 层级三段 legend · 让读者
    # 一眼理解徽标含义: LF = 该分支 leaf-count (二级学科下具体 benchmark 数) ·
    # 分支上数字 = 该子学科 sub-count · 一级/二级 = 学科层级.
    figure_caption: str = (
        "Hierarchical tree · 4 domains · 12 sub-groups · 24 benchmarks · "
        "LF = 二级学科分类 leaf-count · 数字 = 该分支 sub-count · "
        "一级 / 二级 = 学科层级"
    ),
    source: str = "Source · HELM v2 · Bloom-style taxonomy · illustrative snapshot 2026-09",
    fig_tag: str = "FIGURE 07",
    fig_tag_note: str = "",           # chatter default off (was TX·Taxonomy how-to-read)
    notes_lines: Optional[List[str]] = None,
    # ─── scaffold labels · parameterized so CN slides don't ship EN text ───
    section_head: str = "",           # was "TAXONOMY TREE" (chatter · default off)
    section_note: str = "",           # was "left → right · 4 tiers ..." (chatter · off)
    tier_headers: Optional[List[str]] = None,   # was ["T1 · ROOT", ...] (off by default)
    domain_kicker_word: str = "",     # was "DOMAIN" (per-card kicker prefix · off)
    leaves_word: str = "",            # was "LEAVES" (right-side count subtitle · off)
    lf_word: str = "LF",              # sub-card leaf-count abbrev (kept · short)
    coverage_head: str = "COVERAGE BY DOMAIN",  # sidebar sec head (still off if empty)
    hue_legend_head: str = "HUE LEGEND",
    tier_markers_head: str = "TIER MARKERS",
) -> Tree:
    """Build 4-tier taxonomy Tree.

    None ⇒ baseline. [] ⇒ 该 section 关闭 (仅 coverage / hue_legend / tier_markers / notes_lines).
    """
    r = root if root is not None else BASELINE_ROOT
    ds = domains if domains is not None else BASELINE_DOMAINS
    if not ds:
        raise ValueError("taxonomy: domains must be non-empty")

    kp = kpis if kpis is not None else BASELINE_KPIS
    cov = coverage if coverage is not None else BASELINE_COVERAGE
    hlg = hue_legend if hue_legend is not None else BASELINE_HUE_LEGEND
    tmk = tier_markers if tier_markers is not None else BASELINE_TIER_MARKERS
    nts = notes_lines if notes_lines is not None else BASELINE_NOTES

    # -- build TreeNode graph (root → domain → sub → leaf) --
    root_node = TreeNode(
        id="root",
        label=str(r.get("label", "LLM")),
        sublabel=str(r.get("sub", "BENCH")),
        extra={
            "tag": r.get("tag", "ROOT"),
            "kpis": kp or None,
            "coverage": cov or [],
            "hue_legend": hlg or [],
            "tier_markers": tmk or [],
            "notes_lines": nts or [],
            "fig_tag": fig_tag,
            "fig_tag_note": fig_tag_note,
            "show_sidebar": bool(show_sidebar),
            # scaffold labels (all default empty so slides stay chatter-free)
            "section_head": section_head,
            "section_note": section_note,
            "tier_headers": list(tier_headers) if tier_headers else [],
            "domain_kicker_word": domain_kicker_word,
            "leaves_word": leaves_word,
            "lf_word": lf_word,
            "coverage_head": coverage_head,
            "hue_legend_head": hue_legend_head,
            "tier_markers_head": tier_markers_head,
        },
    )
    for i, d in enumerate(ds):
        dhue = str(d.get("hue", "magenta"))
        dnode = TreeNode(
            id=str(d.get("key") or f"d{i}"),
            label=str(d.get("label", "")),
            sublabel=str(d.get("sub", "")),
            group=dhue,
            extra={
                "code": d.get("code", f"D{i + 1}"),
                "leaf_count": int(d.get("leaf_count", 0)),
            },
        )
        for j, s in enumerate(d.get("subs", []) or []):
            snode = TreeNode(
                id=f"{dnode.id}_s{j}",
                label=str(s.get("label", "")),
                sublabel=str(s.get("sub", "")),
                group=str(s.get("hue", dhue)),
                extra={"code": s.get("code", f"S{j + 1}")},
            )
            for k, lf in enumerate(s.get("leaves", []) or []):
                snode.children.append(TreeNode(
                    id=f"{snode.id}_l{k}",
                    label=str(lf.get("label", "")),
                    sublabel="",
                    detail=str(lf.get("tag", "")),
                    group=str(s.get("hue", dhue)),
                    extra={"code": lf.get("code", f"L{k + 1}")},
                ))
            dnode.children.append(snode)
        root_node.children.append(dnode)

    return Tree(
        root=root_node,
        kicker=kicker,
        figure_title=figure_title,
        figure_caption=figure_caption,
        source=source,
        encoding_note="",
    )


# alias for gen_svg_relations manifest lookup
build_tx_tree = build_taxonomy_data

HERO_TX_DATA = build_taxonomy_data()


# ═════════════════════════════════════════════════════════════════
# layout · self-contained (返回 y 坐标)
# ═════════════════════════════════════════════════════════════════

def _compute_layout(data: Tree) -> Dict[str, Any]:
    """Compute y-positions for every domain / sub / leaf.

    Strategy (density-adaptive):
      - Solve for a single "scale" factor in (0, 1] that lets all pitches
        shrink uniformly until total-span fits BODY_Y0..BODY_Y1 (410 px).
      - Hard floors keep leaf pills separated in ordinary 4×3×2 cases; very
        dense examples can still compress to the old compact floor.
        · inter_gap ≥ 6.
      - After shrink, if still overflowing, LayoutOverflow-like fallback:
        pin to BODY_Y0 (accept minor visual squeeze).
    """
    root = data.root
    domains = list(root.children)
    if not domains:
        raise ValueError("taxonomy: no domains to lay out")

    # sidebar-aware leaf column geometry: when no sidebar, the tree fills
    # the whole canvas width (leaves stretch to BODY_X1_FULL 1340).
    root_extra_local = getattr(root, "extra", {}) or {}
    show_sidebar_local = bool(root_extra_local.get("show_sidebar", True))
    leaf_body_x0 = LEAF_X                                # 640
    leaf_body_x1 = BODY_X1_MAIN if show_sidebar_local else BODY_X1_FULL
    leaf_body_w  = leaf_body_x1 - leaf_body_x0           # 310 or 590
    body_y0 = 128.0 if not show_sidebar_local else BODY_Y0
    body_y1 = BODY_Y1

    avail = body_y1 - body_y0
    n_dom = len(domains)

    # baseline pitches (visual sweet spot · matches reference)
    LP0 = 22.0        # leaf pitch; keep a visible gap between vertical leaves
    SM0 = 40.0        # sub minimum height (sub box 30 + breathing room)
    IG0 = 18.0        # inter-domain gap
    SH0 = float(SUB_H)  # baseline sub-card height (30)

    scale = 1.0
    n_cols = 1
    dh_dyn = DOMAIN_H
    sh_dyn = SH0

    # Detect density → choose 1 / 2 / 3 leaf columns
    max_leaf_per_sub = max((len(s.children) for d in domains for s in d.children), default=1)
    total_sub = sum(len(d.children) for d in domains)

    # floors (below which visual becomes unreadable)
    dense_layout = n_dom >= 5 or total_sub >= 16 or max_leaf_per_sub >= 3
    LP_MIN = 12.0 if dense_layout else (LEAF_H + 3.0)
    SM_MIN = 16.0 if dense_layout else 24.0
    IG_MIN = 6.0 if dense_layout else 8.0
    DH_MIN = DOMAIN_H  # keep filled domain cards tall enough for their strip label
    SH_MIN = 16.0 if dense_layout else 20.0

    def cols_needed(lp: float, sm: float, ig: float, sh: float, cols: int) -> float:
        # each sub has ceil(n_leaves / cols) rows
        s = 0.0
        for d in domains:
            subs = list(d.children)
            if not subs:
                s += DOMAIN_H
                continue
            dsum = 0.0
            for sub in subs:
                n = max(1, len(sub.children))
                rows = (n + cols - 1) // cols
                span = (rows - 1) * lp + max(sh, LEAF_H)
                span = max(span, sm)
                dsum += span
            s += max(dsum, DOMAIN_H)
        s += ig * (n_dom - 1)
        return s

    # try 1, then 2, then 3 columns (pick smallest that fits at scale=1)
    n_cols_try = [1, 2, 3]
    for c in n_cols_try:
        if cols_needed(LP0, SM0, IG0, SH0, c) <= avail:
            n_cols = c
            break
    else:
        n_cols = 3

    # Product requirement: leaf nodes must stay vertically ordered even when
    # there are many leaves under one sub-category.
    n_cols = 1

    def span_fn(lp: float, sm: float, ig: float, dh_min: float, sh: float) -> tuple:
        dom_spans_l: List[float] = []
        for d in domains:
            subs = list(d.children)
            if not subs:
                dom_spans_l.append(dh_min)
                continue
            dsum = 0.0
            for sub in subs:
                n = max(1, len(sub.children))
                rows = (n + n_cols - 1) // n_cols
                span = (rows - 1) * lp + max(sh, LEAF_H)
                span = max(span, sm)
                dsum += span
            dom_spans_l.append(max(dsum, dh_min))
        total = sum(dom_spans_l) + ig * (n_dom - 1)
        return dom_spans_l, total

    _, needed = span_fn(LP0, SM0, IG0, DOMAIN_H, SH0)
    if needed > avail:
        low, high = 0.0, 1.0
        for _ in range(24):
            mid = (low + high) / 2
            lp = max(LP_MIN, LP0 * mid + (1 - mid) * LP_MIN)
            sm = max(SM_MIN, SM0 * mid + (1 - mid) * SM_MIN)
            ig = max(IG_MIN, IG0 * mid + (1 - mid) * IG_MIN)
            dh = max(DH_MIN, DOMAIN_H * mid + (1 - mid) * DH_MIN)
            sh = max(SH_MIN, SH0 * mid + (1 - mid) * SH_MIN)
            _, tot = span_fn(lp, sm, ig, dh, sh)
            if tot <= avail:
                low = mid
            else:
                high = mid
        scale = low
    lp = max(LP_MIN, LP0 * scale + (1 - scale) * LP_MIN)
    sm = max(SM_MIN, SM0 * scale + (1 - scale) * SM_MIN)
    ig = max(IG_MIN, IG0 * scale + (1 - scale) * IG_MIN)
    dh_dyn = DOMAIN_H
    sh_dyn = max(SH_MIN, SH0 * scale + (1 - scale) * SH_MIN)
    two_col = (n_cols >= 2)  # keep old flag as alias for anything >=2

    leaf_pitch = lp
    inter_gap = ig
    sub_min_h = sm
    dom_card_h = dh_dyn

    def sub_span_final(sub: TreeNode) -> float:
        n = max(1, len(sub.children))
        rows = (n + n_cols - 1) // n_cols
        span = (rows - 1) * leaf_pitch + max(sh_dyn, LEAF_H)
        return max(span, sub_min_h)

    dom_spans: List[float] = []
    for d in domains:
        subs = list(d.children)
        if not subs:
            dom_spans.append(dom_card_h)
            continue
        span = sum(sub_span_final(s) for s in subs)
        dom_spans.append(max(span, dom_card_h))

    total_span = sum(dom_spans) + inter_gap * (n_dom - 1)
    top = body_y0 + max(0.0, (avail - total_span) / 2.0)
    if total_span > avail + 2:
        top = body_y0

    # per-domain assignments
    domain_positions: List[Dict[str, Any]] = []
    y_cursor = top
    for i, d in enumerate(domains):
        span = dom_spans[i]
        d_center_y = y_cursor + span / 2.0
        d_h = min(dom_card_h, span)   # if span < card_h · shrink card to fit
        d_box = {
            "kind": "domain",
            "code": d.extra.get("code", f"D{i + 1}"),
            "label": d.label,
            "sub": d.sublabel,
            "hue": d.group or "magenta",
            "leaf_count": int(d.extra.get("leaf_count", sum(len(s.children) for s in d.children))),
            "cx": (DOMAIN_X + DOMAIN_W / 2),
            "cy": d_center_y,
            "x": DOMAIN_X, "y": d_center_y - d_h / 2,
            "w": DOMAIN_W, "h": d_h,
        }

        # subs · stacked inside this domain span
        subs_positions: List[Dict[str, Any]] = []
        s_cursor = y_cursor
        for j, s in enumerate(d.children):
            ss = sub_span_final(s)
            s_center_y = s_cursor + ss / 2.0
            s_box = {
                "kind": "sub",
                "code": s.extra.get("code", f"S{j + 1}"),
                "label": s.label,
                "sub": s.sublabel,
                "hue": s.group or d.group or "magenta",
                "n_leaves": len(s.children),
                "cx": SUB_X + SUB_W / 2,
                "cy": s_center_y,
                "x": SUB_X, "y": s_center_y - sh_dyn / 2,
                "w": SUB_W, "h": sh_dyn,
            }

            # leaves · stacked inside sub span (using shrink-adjusted leaf_pitch)
            leaves_positions: List[Dict[str, Any]] = []
            n = len(s.children)
            # Available body width for leaves depends on sidebar visibility.
            LEAF_BODY_X0 = leaf_body_x0
            LEAF_BODY_W  = leaf_body_w
            # Keep leaves vertical and compact; the leaf label is the only
            # text payload, so long metadata chips do not force wide pills.
            leaf_w_full = min(LEAF_BODY_W, 300 if not show_sidebar_local else 220)
            if n_cols >= 2:
                # split full body into n_cols columns with 10-14 gap
                col_gap = 12 if n_cols == 2 else 8
                leaf_w = int((LEAF_BODY_W - col_gap * (n_cols - 1)) / n_cols)
                col_xs = [LEAF_BODY_X0 + i * (leaf_w + col_gap) for i in range(n_cols)]
                rows = (n + n_cols - 1) // n_cols
                half = (rows - 1) * leaf_pitch / 2.0
                for k, lf in enumerate(s.children):
                    row = k // n_cols
                    col = k % n_cols
                    lc = s_center_y - half + row * leaf_pitch
                    leaves_positions.append({
                        "kind": "leaf",
                        "code": lf.extra.get("code", "L?"),
                        "label": lf.label,
                        "tag": lf.detail,
                        "hue": lf.group or s.group or d.group or "magenta",
                        "cy": lc,
                        "x": col_xs[col], "y": lc - LEAF_H / 2,
                        "w": leaf_w, "h": LEAF_H,
                        "col": col,
                    })
            elif n == 1:
                lf = s.children[0]
                leaves_positions.append({
                    "kind": "leaf",
                    "code": lf.extra.get("code", "L?"),
                    "label": lf.label,
                    "tag": lf.detail,
                    "hue": lf.group or s.group or d.group or "magenta",
                    "cy": s_center_y,
                    "x": LEAF_BODY_X0, "y": s_center_y - LEAF_H / 2,
                    "w": leaf_w_full, "h": LEAF_H,
                    "col": 0,
                })
            else:
                half = (n - 1) * leaf_pitch / 2.0
                for k, lf in enumerate(s.children):
                    lc = s_center_y - half + k * leaf_pitch
                    leaves_positions.append({
                        "kind": "leaf",
                        "code": lf.extra.get("code", "L?"),
                        "label": lf.label,
                        "tag": lf.detail,
                        "hue": lf.group or s.group or d.group or "magenta",
                        "cy": lc,
                        "x": LEAF_BODY_X0, "y": lc - LEAF_H / 2,
                        "w": leaf_w_full, "h": LEAF_H,
                        "col": 0,
                    })

            s_box["leaves"] = leaves_positions
            subs_positions.append(s_box)
            s_cursor += ss

        d_box["subs"] = subs_positions
        domain_positions.append(d_box)
        y_cursor += span + inter_gap

    return {
        "root": {
            "kind": "root",
            "label": root.label,
            "sub": root.sublabel,
            "tag": root.extra.get("tag", "ROOT"),
            "cx": ROOT_X + ROOT_W / 2,
            "cy": (body_y0 + body_y1) / 2,
            "x": ROOT_X, "y": (body_y0 + body_y1) / 2 - ROOT_H / 2,
            "w": ROOT_W, "h": ROOT_H,
        },
        "domains": domain_positions,
        "two_col": two_col,
        "n_cols": n_cols,
    }


# ═════════════════════════════════════════════════════════════════
# render helpers (small SVG fragment emitters)
# ═════════════════════════════════════════════════════════════════

def _text(x, y, s, *, size=10.0, font=None, fill=INK_COLOR,
          weight="", style="", ls="", anchor="") -> str:
    if font is None:
        font = FONT_SANS  # 运行时读, 让 font_family 参数能覆写
    attrs = [
        f'x="{x:.1f}"', f'y="{y:.1f}"',
        f'font-family="{font}"', f'font-size="{size:g}"',
        f'fill="{fill}"',
    ]
    if weight: attrs.append(f'font-weight="{weight}"')
    if style:  attrs.append(f'font-style="{style}"')
    if ls:     attrs.append(f'letter-spacing="{ls}"')
    if anchor: attrs.append(f'text-anchor="{anchor}"')
    return f'<text {" ".join(attrs)}>{esc(s)}</text>'


def _rect(x, y, w, h, *, fill="none", stroke="none", sw=0.6) -> str:
    parts = [f'x="{x:.1f}"', f'y="{y:.1f}"',
             f'width="{w:.1f}"', f'height="{h:.1f}"']
    if fill != "none":   parts.append(f'fill="{fill}"')
    else:                parts.append('fill="none"')
    if stroke != "none":
        parts.append(f'stroke="{stroke}"')
        parts.append(f'stroke-width="{sw}"')
    return f'<rect {" ".join(parts)}/>'


def _line(x1, y1, x2, y2, *, stroke=HAIR_COLOR, sw=0.6, dash="") -> str:
    a = [f'x1="{x1:.1f}"', f'y1="{y1:.1f}"',
         f'x2="{x2:.1f}"', f'y2="{y2:.1f}"',
         f'stroke="{stroke}"', f'stroke-width="{sw}"']
    if dash: a.append(f'stroke-dasharray="{dash}"')
    return f'<line {" ".join(a)}/>'


def _orth_path(x1, y1, x2, y2, *, mid_frac=0.5, stroke, sw=1.1,
               opacity=1.0) -> str:
    """Orthogonal 3-segment path from (x1,y1) → (x2,y2) via mid x."""
    mx = x1 + (x2 - x1) * mid_frac
    d = f"M {x1:.1f} {y1:.1f} L {mx:.1f} {y1:.1f} L {mx:.1f} {y2:.1f} L {x2:.1f} {y2:.1f}"
    return (f'<path d="{d}" fill="none" stroke="{stroke}" '
            f'stroke-width="{sw}" stroke-linecap="round" '
            f'stroke-linejoin="round" opacity="{opacity:.2f}"/>')


def _atomize_text_width(s: str, size: float) -> float:
    """Approximate slide-native text width after atomization."""
    total = 0.0
    for ch in str(s or ""):
        if ord(ch) > 0x2E80:
            total += size * 1.0
        elif ch.isspace():
            total += size * 0.35
        elif ch.isupper() or ch in "·×→↑↓←◆◈§":
            total += size * 0.7
        else:
            total += size * 0.55
    return total + size * 0.5


def _fit_atomized_text_size(
    text: str,
    max_width: float,
    base_size: float,
    *,
    min_size: float = 7.0,
) -> float:
    """Fit a single-line label to the width model used by atomize_svg_to_slide."""
    if not text or max_width <= 0:
        return base_size
    safe_width = max_width * 0.88
    actual = _atomize_text_width(text, base_size)
    if actual <= safe_width:
        return base_size
    return max(min_size, base_size * safe_width / max(actual, 1.0))


def _is_cjk(ch: str) -> bool:
    return bool(ch) and ord(ch) > 0x2E80


def _preferred_wrap_positions(text: str) -> List[int]:
    """Return split positions that preserve every character when wrapped."""
    s = str(text or "")
    positions: List[int] = []
    for i, ch in enumerate(s[:-1], 1):
        nxt = s[i]
        if ch.isspace() or ch in "/-·:：":
            positions.append(i)
        elif _is_cjk(ch) != _is_cjk(nxt):
            positions.append(i)
    return positions


def _wrap_atomized_text(
    text: str,
    max_width: float,
    base_size: float,
    *,
    max_lines: int = 2,
    min_size: float = 7.0,
) -> tuple[List[str], float]:
    """Wrap without dropping/reordering characters; ``''.join(lines) == text``."""
    s = str(text or "")
    if not s:
        return [""], base_size
    if max_lines <= 1:
        return [s], _fit_atomized_text_size(s, max_width, base_size, min_size=min_size)

    safe_width = max_width * 0.84
    break_positions = _preferred_wrap_positions(s)
    size_steps = [base_size, 10.0, 9.5, 9.0, 8.5, 8.0, 7.5, min_size]
    size_steps = [v for i, v in enumerate(size_steps) if v <= base_size and v not in size_steps[:i]]

    for fs in size_steps:
        if _atomize_text_width(s, fs) <= safe_width:
            return [s], fs
        candidates = [p for p in break_positions if 0 < p < len(s)]
        if not candidates:
            candidates = list(range(1, len(s)))
        best: Optional[List[str]] = None
        best_score = float("inf")
        for line_count in range(2, max_lines + 1):
            for cuts in combinations(candidates, line_count - 1):
                lines: List[str] = []
                start = 0
                for cut in cuts:
                    lines.append(s[start:cut])
                    start = cut
                lines.append(s[start:])
                if any(line == "" for line in lines) or "".join(lines) != s:
                    continue
                widths = [_atomize_text_width(line, fs) for line in lines]
                overflow = max(0.0, max(widths) - safe_width)
                balance = (max(widths) - min(widths)) * 0.05
                score = overflow * 1000 + balance + line_count * 0.2
                if score < best_score:
                    best_score = score
                    best = lines
                if overflow <= 0:
                    return lines, fs
        if best is not None and max(_atomize_text_width(line, fs) for line in best) <= safe_width:
            return best, fs

    fs = min_size
    candidates = [p for p in break_positions if 0 < p < len(s)] or list(range(1, len(s)))
    line_count = min(max_lines, max(2, len(candidates) + 1))
    cuts = []
    for i in range(1, line_count):
        target = len(s) * i / line_count
        cuts.append(min(candidates, key=lambda pos: abs(pos - target)))
    cuts = sorted(set(cuts))
    lines = []
    start = 0
    for cut in cuts:
        lines.append(s[start:cut])
        start = cut
    lines.append(s[start:])
    return lines, fs


# ═════════════════════════════════════════════════════════════════
# render · main entry
# ═════════════════════════════════════════════════════════════════

def render_hero_embed_tx_taxonomy_v2(
    data: Tree = HERO_TX_DATA,
    palette: Palette = BONE_RUST,
    *,
    subtract_level: str = "L3",
) -> str:
    """Render 4-tier taxonomy hero embed (1400×720)."""

    # [SKIN-PATCH-L1] globals patch: skin.PALETTE 覆写模块级色常量
    _MOD_L1 = globals()
    _ORIG_L1 = {k: _MOD_L1[k] for k in ("BG_COLOR", "INK_COLOR", "INK_DIM", "GRAY_COLOR", "HAIR_COLOR", "HAIR_LIGHT",)}
    _SKIN_L1 = _get_active_skin()
    if _SKIN_L1 is not None:
        _SP_L1 = getattr(_SKIN_L1, 'PALETTE', None)
        if _SP_L1 is not None:
            if getattr(_SP_L1, 'bg', None): _MOD_L1['BG_COLOR'] = _SP_L1.bg
            if getattr(_SP_L1, 'ink', None): _MOD_L1['INK_COLOR'] = _SP_L1.ink
            if getattr(_SP_L1, 'gray', None): _MOD_L1['INK_DIM'] = _SP_L1.gray
            if getattr(_SP_L1, 'gray', None): _MOD_L1['GRAY_COLOR'] = _SP_L1.gray
            if getattr(_SP_L1, 'hair', None): _MOD_L1['HAIR_COLOR'] = _SP_L1.hair
            if getattr(_SP_L1, 'hair', None): _MOD_L1['HAIR_LIGHT'] = _SP_L1.hair
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
        _ = palette  # (kept for API parity)
        root = data.root
        root_extra = getattr(root, "extra", {}) or {}
        # Bucket H (2026-09-13) · subtract_level 默认 L3 · 清空次要说明字段
        # L1: 清 kicker / fig_tag_note / section_head / section_note
        # L2: L1 + kpis / notes_lines / coverage / hue_legend / tier_markers
        # L3: L2 + domain_kicker_word / leaves_word / tier_headers
        # (R3 2026-09-13: figure_caption 从 L3 subtract 移除 · caption 承载 LF /
        #  数字 / 一级二级 层级 legend · 是理解徽标的必要说明)
        if subtract_level and subtract_level != "L0":
            import copy as _copy
            data = _copy.deepcopy(data)
            root = data.root
            root_extra = getattr(root, "extra", {}) or {}
            if subtract_level in ("L1", "L2", "L3"):
                try:
                    data.kicker = ""
                except Exception:
                    pass
                root_extra["fig_tag_note"] = ""
                root_extra["section_head"] = ""
                root_extra["section_note"] = ""
            if subtract_level in ("L2", "L3"):
                root_extra["kpis"] = None
                root_extra["notes_lines"] = []
                root_extra["coverage"] = []
                root_extra["hue_legend"] = []
                root_extra["tier_markers"] = []
            if subtract_level == "L3":
                # R3 fix (2026-09-13): KEEP figure_caption at L3 · caption 现在
                # 承载 LF / 数字 / 一级二级 层级 legend · 是理解徽标的必要说明.
                # (L3 只清 chatter · 不清 legend caption)
                root_extra["domain_kicker_word"] = ""
                root_extra["leaves_word"] = ""
                root_extra["tier_headers"] = []
                root_extra["fig_tag"] = ""
            root.extra = root_extra
        title       = data.figure_title or ""
        caption     = data.figure_caption or ""
        source      = data.source or ""
        fig_tag     = root_extra.get("fig_tag", "")
        fig_tag_note = root_extra.get("fig_tag_note", "")
        kpis        = root_extra.get("kpis") or []
        coverage    = root_extra.get("coverage") or []
        hue_legend  = root_extra.get("hue_legend") or []
        tier_markers = root_extra.get("tier_markers") or []
        notes       = root_extra.get("notes_lines") or []
        sidebar_has_content = bool(coverage or hue_legend or tier_markers)
        show_sidebar = bool(root_extra.get("show_sidebar", True)) and sidebar_has_content
        root_extra["show_sidebar"] = show_sidebar
        # scaffold labels (all default empty · pass through build_taxonomy_data kwargs)
        section_head       = root_extra.get("section_head", "")
        section_note       = root_extra.get("section_note", "")
        tier_headers_txt   = root_extra.get("tier_headers", []) or []
        domain_kicker_word = root_extra.get("domain_kicker_word", "")
        leaves_word        = root_extra.get("leaves_word", "")
        lf_word            = root_extra.get("lf_word", "LF")
        coverage_head      = root_extra.get("coverage_head", "COVERAGE BY DOMAIN")
        hue_legend_head    = root_extra.get("hue_legend_head", "HUE LEGEND")
        tier_markers_head  = root_extra.get("tier_markers_head", "TIER MARKERS")

        # tier-column x-limit for the "TAXONOMY TREE" hairline
        section_hairline_x1 = SB_X_DIV - 20 if show_sidebar else BODY_X1_FULL

        layout = _compute_layout(data)

        parts: List[str] = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {VIEW_W} {VIEW_H}">',
            f'<rect width="{VIEW_W}" height="{VIEW_H}" fill="{BG_COLOR}"/>',
        ]

        # ── CHROME · title / caption / hairline / fig tag ──
        parts.append(_text(BODY_X0, 46, title,
                           size=24, font=FONT_SERIF, weight="600",
                           fill=INK_COLOR, ls="0.1"))
        if caption:
            parts.append(_text(BODY_X0, 68, caption,
                               size=11, fill=INK_DIM, ls="0.2"))
        parts.append(_line(BODY_X0, 84, VIEW_W - BODY_X0, 84,
                           stroke=HAIR_COLOR, sw=0.8))
        if fig_tag:
            parts.append(_text(BODY_X0, 102, fig_tag,
                               size=10, fill=INK_DIM, weight="600", ls="1.4"))
        if fig_tag_note:
            parts.append(_text(BODY_X0 + 90, 102, fig_tag_note,
                               size=10, fill=GRAY_COLOR, ls="0.3"))

        # ── KPI STRIP · 4 tiles ──
        if kpis:
            n_kpi = min(4, len(kpis))
            # widths (60/380/700/1020 · same as reference) — keep fixed for n=4
            x_slots = [60, 380, 700, 1020]
            w_slots = [300, 300, 300, 320]
            # If n<4, distribute evenly across canvas
            if n_kpi != 4:
                total_w = VIEW_W - 2 * BODY_X0
                tile_w = (total_w - (n_kpi - 1) * 20) / n_kpi
                x_slots = [BODY_X0 + i * (tile_w + 20) for i in range(n_kpi)]
                w_slots = [tile_w] * n_kpi
            for i in range(n_kpi):
                k = kpis[i]
                x, w = x_slots[i], w_slots[i]
                hue = _hue_str(k.get("hue", "magenta"))
                parts.append(_rect(x, 112, w, 38, fill=KPI_BG,
                                   stroke="rgba(175,178,188,1)", sw=0.6))
                parts.append(_rect(x, 112, 4, 38, fill=hue))
                parts.append(_text(x + 14, 126, str(k.get("kicker", "")),
                                   size=10, fill=GRAY_COLOR, weight="600", ls="1.2"))
                parts.append(_text(x + 14, 144, str(k.get("value", "")),
                                   size=15, font=FONT_SERIF, weight="700",
                                   fill=INK_COLOR))
                # note to the right of value · gap 76px like reference
                parts.append(_text(x + 90, 144, str(k.get("note", "")),
                                   size=10, fill=GRAY_COLOR))

        # ── SECTION HEADER (default off · pass section_head=... to opt-in) ──
        if section_head:
            parts.append(_text(BODY_X0, 176, section_head,
                               size=10, weight="600", fill=INK_COLOR, ls="1.4"))
        if section_note:
            parts.append(_text(BODY_X0 + 160, 176, section_note,
                               size=10, fill=GRAY_COLOR))
        if section_head or section_note:
            parts.append(_line(BODY_X0, 184, section_hairline_x1, 184,
                               stroke=HAIR_COLOR, sw=0.6))

        # ── tier column headers (default off · pass tier_headers=[4 strings]) ──
        if tier_headers_txt and len(tier_headers_txt) >= 4:
            tier_labels = [
                (ROOT_X + ROOT_W / 2 + 15, tier_headers_txt[0]),
                (DOMAIN_X + DOMAIN_W / 2, tier_headers_txt[1]),
                (SUB_X + SUB_W / 2, tier_headers_txt[2]),
                (LEAF_X + LEAF_W / 2, tier_headers_txt[3]),
            ]
            for cx, txt in tier_labels:
                if txt:
                    parts.append(_text(cx, 200, txt, size=10, fill=GRAY_COLOR,
                                       weight="700", ls="1.4", anchor="middle"))

        # ── faint tier dividers (only useful when tier labels are visible) ──
        if tier_headers_txt and len(tier_headers_txt) >= 4:
            for x_div in (150, 380, 620):
                parts.append(_line(x_div, 210, x_div, 620,
                                   stroke="rgba(115,120,132,0.12)", sw=0.4,
                                   dash="2 3"))

        # ── ROOT NODE ──
        r = layout["root"]
        rx, ry = r["x"], r["y"]
        parts.append(_rect(rx, ry, ROOT_W, ROOT_H,
                           fill=_hue_str("navy"),
                           stroke=_hue_str("navy", alpha=1.0), sw=1.4))
        parts.append(_rect(rx, ry, ROOT_W, 4, fill=_hue_str("gold_p")))
        root_tag_fs = _fit_atomized_text_size(str(r["tag"]), ROOT_W - 12, 10, min_size=7.0)
        root_label_fs = _fit_atomized_text_size(str(r["label"]), ROOT_W - 14, 15, min_size=7.0)
        root_sub_fs = _fit_atomized_text_size(str(r["sub"]), ROOT_W - 14, 12, min_size=6.5)
        parts.append(_text(r["cx"], ry + 21, r["tag"], size=root_tag_fs,
                           fill=_hue_str("gold_p"), weight="700", ls="1.6",
                           anchor="middle"))
        parts.append(_text(r["cx"], ry + 42, r["label"],
                           size=root_label_fs, font=FONT_SERIF, weight="700",
                           fill=BG_COLOR, anchor="middle"))
        parts.append(_text(r["cx"], ry + 58, r["sub"],
                           size=root_sub_fs, font=FONT_SERIF, weight="700",
                           fill=_hue_str("gold_p"), anchor="middle"))

        # ── ROOT → DOMAIN connectors (orthogonal trunk) ──
        trunk_mx = (ROOT_X + ROOT_W + DOMAIN_X) / 2
        root_cx_r = ROOT_X + ROOT_W       # right edge of root
        for d in layout["domains"]:
            stroke = _hue_str(d["hue"], alpha=0.85)
            d_cy = d["cy"]
            parts.append(
                f'<path d="M {root_cx_r:.1f} {r["cy"]:.1f} '
                f'L {trunk_mx:.1f} {r["cy"]:.1f} '
                f'L {trunk_mx:.1f} {d_cy:.1f} '
                f'L {DOMAIN_X:.1f} {d_cy:.1f}" '
                f'fill="none" stroke="{stroke}" stroke-width="1.6" '
                f'stroke-linecap="round" stroke-linejoin="round"/>'
            )

        # ── DOMAIN cards + DOMAIN → SUB connectors + SUB cards +
        #    SUB → LEAF connectors + LEAF pills ──
        for d in layout["domains"]:
            hue_full = _hue_str(d["hue"], alpha=1.0)
            hue_94   = _hue_str(d["hue"], alpha=0.94)
            hue_70   = _hue_str(d["hue"], alpha=0.7)
            hue_55   = _hue_str(d["hue"], alpha=0.55)
            hue_85   = _hue_str(d["hue"], alpha=0.85)
            dx, dy = d["x"], d["y"]
            dh = d["h"]
            # dynamic vertical anchors inside the domain card
            strip_h = min(12, max(6, dh * 0.24))
            y_kicker = dy + strip_h - 1.0
            y_label  = dy + strip_h + max(14, (dh - strip_h) * 0.42)
            y_sub    = y_label + 14

            # domain card body + top strip
            parts.append(_rect(dx, dy, DOMAIN_W, dh,
                               fill=hue_94, stroke=BG_COLOR, sw=1.4))
            parts.append(_rect(dx, dy, DOMAIN_W, strip_h, fill=hue_full))
            # domain kicker: only if user opted in (defaults empty → clean strip)
            if domain_kicker_word:
                domain_code_txt = f"{domain_kicker_word} · {d['code']}"
                domain_code_fs = _fit_atomized_text_size(
                    domain_code_txt, DOMAIN_W - 12, 10, min_size=7.0
                )
                parts.append(_text(d["cx"], y_kicker,
                                   domain_code_txt,
                                   size=domain_code_fs, fill=BG_COLOR, weight="700", ls="1.6",
                                   anchor="middle"))
            else:
                # keep the code visible on the strip so cards stay identifiable
                domain_code_fs = _fit_atomized_text_size(
                    str(d["code"]), DOMAIN_W - 12, 10, min_size=7.0
                )
                parts.append(_text(d["cx"], y_kicker, str(d["code"]),
                                   size=domain_code_fs, fill=BG_COLOR, weight="700", ls="1.6",
                                   anchor="middle"))
            domain_count_txt = str(d["leaf_count"])
            domain_count_fs = _fit_atomized_text_size(domain_count_txt, 38, 13, min_size=8.5)
            domain_count_w = _atomize_text_width(domain_count_txt, domain_count_fs)
            domain_label_w = max(44.0, DOMAIN_W - 30 - domain_count_w - 14)
            domain_label_lines, domain_label_fs = _wrap_atomized_text(
                str(d["label"]), domain_label_w, 13,
                max_lines=3, min_size=7.5
            )
            if len(domain_label_lines) == 1:
                parts.append(_text(dx + 12, y_label, domain_label_lines[0],
                                   size=domain_label_fs, weight="700", ls="0.4",
                                   fill=BG_COLOR))
            else:
                gap = max(14.0, domain_label_fs * 1.35)
                y0 = y_label - gap * (len(domain_label_lines) - 1) / 2.0 + 2.0
                for idx, line in enumerate(domain_label_lines):
                    parts.append(_text(dx + 12, y0 + idx * gap, line,
                                       size=domain_label_fs, weight="700",
                                       ls="0.4", fill=BG_COLOR))
            sub_text = d["sub"]
            if dh - strip_h > 32 and len(domain_label_lines) == 1:
                domain_sub_fs = _fit_atomized_text_size(
                    str(sub_text), DOMAIN_W - 24, 10, min_size=7.0
                )
                parts.append(_text(dx + 12, y_sub, sub_text,
                                   size=domain_sub_fs, style="italic",
                                   fill="rgba(247,240,226,0.85)"))
            parts.append(_text(dx + DOMAIN_W - 12, y_label,
                               domain_count_txt,
                               size=domain_count_fs, font=FONT_SERIF, weight="700",
                               fill=BG_COLOR, anchor="end"))
            if dh - strip_h > 26 and leaves_word:
                parts.append(_text(dx + DOMAIN_W - 12, y_sub, leaves_word,
                                   size=10, fill="rgba(247,240,226,0.85)",
                                   ls="1", anchor="end"))

            # trunk-2: domain → sub connectors (short orthogonal)
            d_right_x = dx + DOMAIN_W
            mid_x = d_right_x + 20  # x=390
            for s in d["subs"]:
                parts.append(
                    f'<path d="M {d_right_x:.1f} {d["cy"]:.1f} '
                    f'L {mid_x:.1f} {d["cy"]:.1f} '
                    f'L {mid_x:.1f} {s["cy"]:.1f} '
                    f'L {SUB_X:.1f} {s["cy"]:.1f}" '
                    f'fill="none" stroke="{hue_70}" stroke-width="1.1" '
                    f'stroke-linecap="round" stroke-linejoin="round"/>'
                )

            # sub cards + leaves + leaf connectors
            for s in d["subs"]:
                sx, sy = s["x"], s["y"]
                sh = s["h"]
                parts.append(_rect(sx, sy, SUB_W, sh,
                                   fill=BG_COLOR, stroke=hue_85, sw=1))
                parts.append(_rect(sx, sy, 3, sh, fill=hue_full))
                # baseline anchors when sh=30: code+label at y+10, sub at y+27 (Δy=17)
                # when sh is compressed, use one line; otherwise the subtitle
                # collides with the main label after slide-native atomization.
                single_line = sh < 30
                if single_line:
                    y_line1 = sy + (sh * 0.66)  # single line vertically centered
                else:
                    y_line1 = sy + 11           # top row
                y_line2 = sy + sh - 3           # bottom row (italic sub, Δy ≥ 12)
                sub_count_txt = (f"{s['n_leaves']} {lf_word}"
                                 if lf_word else str(s['n_leaves']))
                sub_count_fs = _fit_atomized_text_size(
                    sub_count_txt, 34 if single_line else 40,
                    8.8 if single_line else 10,
                    min_size=7.0,
                )
                sub_count_w = _atomize_text_width(sub_count_txt, sub_count_fs)
                label_x = sx + 12 if single_line else sx + 38
                count_x = sx + SUB_W - 10.0
                sub_label_w = max(64.0, count_x - sub_count_w - label_x - 10.0)
                sub_max_lines = 2 if sh >= 28 else 1
                sub_label_lines, sub_label_fs = _wrap_atomized_text(
                    str(s["label"]), sub_label_w,
                    10.6 if single_line else 11,
                    max_lines=sub_max_lines,
                    min_size=7.0,
                )
                if not single_line:
                    parts.append(_text(sx + 12, y_line1, s["code"],
                                       size=10, fill=GRAY_COLOR, weight="700",
                                       ls="1.2"))
                if len(sub_label_lines) > 1:
                    line_gap = max(7.0, sub_label_fs * 0.9)
                    first_y = sy + sh * 0.42
                    for idx, line in enumerate(sub_label_lines[:2]):
                        parts.append(_text(label_x, first_y + idx * line_gap, line,
                                           size=sub_label_fs, weight="600",
                                           fill=INK_COLOR))
                else:
                    parts.append(_text(label_x, y_line1, sub_label_lines[0],
                                       size=sub_label_fs, weight="600", fill=INK_COLOR))
                # Keep the LF counter in a reserved right-side lane; labels get
                # measured against the remaining width and are never truncated.
                parts.append(_text(count_x, y_line1,
                                   sub_count_txt,
                                   size=sub_count_fs, fill=hue_full, weight="700",
                                   ls="0.6", anchor="end"))
                if not single_line and s.get("sub"):
                    sub_desc_fs = _fit_atomized_text_size(
                        str(s["sub"]), SUB_W - 24, 10, min_size=7.0
                    )
                    parts.append(_text(sx + 12, y_line2, s["sub"],
                                       size=sub_desc_fs, fill=GRAY_COLOR, style="italic"))

                # sub → leaf connectors
                s_right_x = sx + SUB_W
                leaf_mid_x = s_right_x + 20   # x=610 for col0
                for lf in s["leaves"]:
                    target_x = lf["x"]
                    # route to sub-first then to leaf's x
                    mid_x = leaf_mid_x if lf.get("col", 0) == 0 else target_x - 8
                    parts.append(
                        f'<path d="M {s_right_x:.1f} {s["cy"]:.1f} '
                        f'L {mid_x:.1f} {s["cy"]:.1f} '
                        f'L {mid_x:.1f} {lf["cy"]:.1f} '
                        f'L {target_x:.1f} {lf["cy"]:.1f}" '
                        f'fill="none" stroke="{hue_55}" stroke-width="0.9" '
                        f'stroke-linecap="round"/>'
                    )

                # leaf pills
                for lf in s["leaves"]:
                    lx, ly = lf["x"], lf["y"]
                    lw = lf["w"]
                    parts.append(_rect(lx, ly, lw, LEAF_H,
                                       fill=BG_COLOR, stroke=hue_55, sw=0.7))
                    # dot + label. Leaf code/tag metadata is intentionally
                    # omitted to remove the gray micro-text called out in review.
                    parts.append(
                        f'<circle cx="{lx + 10:.1f}" cy="{lf["cy"]:.1f}" '
                        f'r="2.6" fill="{hue_full}"/>'
                    )
                    label_max_w = max(40.0, lw - 32)
                    lbl_src = str(lf["label"] or "")
                    lbl_fs = _fit_atomized_text_size(
                        lbl_src, label_max_w, 10.0, min_size=7.0
                    )
                    parts.append(_text(lx + 22, lf["cy"] + 3, lbl_src,
                                       size=lbl_fs, fill=INK_COLOR, weight="500"))

        # ── (removed 2026-09-11) total-annotation at y=595 was a chatter
        #    note that overlapped the last-domain leaf row in dense layouts.
        #    Count is already communicated via BENCHMARKS KPI tile. ──

        # ── SIDEBAR (optional) ──
        if show_sidebar:
            # vertical divider
            parts.append(_line(SB_X_DIV, 200, SB_X_DIV, 620,
                               stroke=HAIR_LIGHT, sw=0.5))
            # ── sidebar budget · alloc heights per section ──
            SB_Y_TOP = 208
            SB_Y_BOT = 620
            sb_total = SB_Y_BOT - SB_Y_TOP  # 412
            # weights per section (used when all 3 present): coverage gets biggest
            sec_present = [bool(coverage), bool(hue_legend), bool(tier_markers)]
            weights = [1.6, 1.0, 0.8]
            w_active = [w if p else 0 for w, p in zip(weights, sec_present)]
            w_sum = sum(w_active) or 1.0
            # per-section height (including header+hairline+content), leave 6px gap
            section_gap = 10
            n_active = sum(1 for p in sec_present if p)
            avail_sb = sb_total - section_gap * max(0, n_active - 1)
            heights = [int(avail_sb * w / w_sum) if w > 0 else 0 for w in w_active]

            sb_y = SB_Y_TOP
            # 1) COVERAGE BY DOMAIN
            if coverage:
                h_sec = heights[0]
                if coverage_head:
                    parts.append(_text(SB_X0, sb_y + 6, coverage_head,
                                       size=10, fill=GRAY_COLOR, weight="600", ls="1.5"))
                    parts.append(_line(SB_X0, sb_y + 14, SB_X1, sb_y + 14,
                                       stroke=HAIR_COLOR, sw=0.6))
                # rows: each row consumes 3 y-anchors (label / bar / note)
                row_min = 28
                row_h = max(row_min, min(46, (h_sec - 22) // max(1, len(coverage))))
                row_start = sb_y + 22
                for i, c in enumerate(coverage):
                    y = row_start + i * row_h
                    if y + row_h > sb_y + h_sec:
                        break  # protect against overflow
                    pct = int(c.get("pct", 0))
                    parts.append(_text(SB_X0, y + 8, str(c.get("label", "")),
                                       size=10, weight="700", ls="0.6",
                                       fill=INK_COLOR))
                    bar_y = y + 14
                    parts.append(_rect(SB_X0, bar_y, 180, 8,
                                       fill="rgba(175,178,188,0.3)"))
                    bar_w = max(4, min(180, int(180 * pct / 100)))
                    parts.append(_rect(SB_X0, bar_y, bar_w, 8,
                                       fill=_hue_str(c.get("hue", "magenta"), alpha=0.9)))
                    parts.append(_text(SB_X1, y + 8, f"{pct}%",
                                       size=10, font=FONT_SERIF, weight="700",
                                       fill=INK_COLOR, anchor="end"))
                    if row_h >= 34 and c.get("note"):
                        parts.append(_text(SB_X0, y + 32, str(c.get("note", "")),
                                           size=10, fill=GRAY_COLOR, style="italic"))
                sb_y = sb_y + h_sec
                parts.append(_line(SB_X0, sb_y, SB_X1, sb_y,
                                   stroke=HAIR_LIGHT, sw=0.4))
                sb_y += section_gap

            # 2) HUE LEGEND
            if hue_legend:
                h_sec = heights[1]
                top_hl = sb_y
                if hue_legend_head:
                    parts.append(_text(SB_X0, sb_y + 6, hue_legend_head,
                                       size=10, fill=GRAY_COLOR, weight="600", ls="1.5"))
                    parts.append(_line(SB_X0, sb_y + 14, SB_X1, sb_y + 14,
                                       stroke=HAIR_COLOR, sw=0.6))
                row_h = max(14, min(18, (h_sec - 20) // max(1, len(hue_legend))))
                row_start = sb_y + 22
                for i, hl in enumerate(hue_legend):
                    y = row_start + i * row_h
                    if y + row_h > top_hl + h_sec:
                        break
                    hue = _hue_str(hl.get("hue", "magenta"))
                    parts.append(_rect(SB_X0, y, 14, 10, fill=hue))
                    parts.append(_text(SB_X0 + 22, y + 9,
                                       f"{hl.get('code','')} · {hl.get('label','')}",
                                       size=10, fill=INK_COLOR, weight="600"))
                    if hl.get("note"):
                        parts.append(_text(SB_X1, y + 9, str(hl["note"]),
                                           size=10, fill=GRAY_COLOR,
                                           style="italic", anchor="end"))
                sb_y = top_hl + h_sec
                parts.append(_line(SB_X0, sb_y, SB_X1, sb_y,
                                   stroke=HAIR_LIGHT, sw=0.4))
                sb_y += section_gap

            # 3) TIER MARKERS
            if tier_markers:
                h_sec = heights[2]
                top_tm = sb_y
                if tier_markers_head:
                    parts.append(_text(SB_X0, sb_y + 6, tier_markers_head,
                                       size=10, fill=GRAY_COLOR, weight="600", ls="1.5"))
                    parts.append(_line(SB_X0, sb_y + 14, SB_X1, sb_y + 14,
                                       stroke=HAIR_COLOR, sw=0.6))
                row_h = max(16, min(20, (h_sec - 20) // max(1, len(tier_markers))))
                row_start = sb_y + 22
                for i, tm in enumerate(tier_markers):
                    y = row_start + i * row_h
                    if y + row_h > top_tm + h_sec:
                        break
                    kind = tm.get("swatch_kind", "stripe")
                    if kind == "root":
                        parts.append(_rect(SB_X0, y, 20, 14, fill=_hue_str("navy")))
                    elif kind == "domain":
                        parts.append(_rect(SB_X0, y, 20, 14, fill=_hue_str("magenta", alpha=0.94)))
                    else:  # stripe (sub/leaf)
                        parts.append(_rect(SB_X0, y, 20, 14, fill=BG_COLOR,
                                           stroke="rgba(115,120,132,0.85)", sw=1))
                        parts.append(_rect(SB_X0, y, 3, 14, fill=GRAY_COLOR))
                    parts.append(_text(SB_X0 + 28, y + 10, str(tm.get("label", "")),
                                       size=10, fill=INK_COLOR, weight="600"))

        # ── FOOTER · hairline + notes + source ──
        parts.append(_line(BODY_X0, 640, VIEW_W - BODY_X0, 640,
                           stroke=HAIR_LIGHT, sw=0.5))
        note_ys = [656, 674, 692]
        for i, ln in enumerate((notes or [])[:3]):
            parts.append(_text(BODY_X0, note_ys[i], ln,
                               size=10, fill=INK_DIM))
        if source:
            parts.append(_text(VIEW_W - BODY_X0, 710, source,
                               size=10, fill=GRAY_COLOR, anchor="end"))

        parts.append('</svg>')
        return "".join(parts)
    finally:
        _MOD_L1.update(_ORIG_L1)
__all__ = [
    "BASELINE_ROOT", "BASELINE_DOMAINS", "BASELINE_KPIS",
    "BASELINE_COVERAGE", "BASELINE_HUE_LEGEND", "BASELINE_TIER_MARKERS",
    "BASELINE_NOTES",
    "build_taxonomy_data", "build_tx_tree",
    "HERO_TX_DATA",
    "render_hero_embed_tx_taxonomy_v2",
    "_DANDELION_HUE",
]
