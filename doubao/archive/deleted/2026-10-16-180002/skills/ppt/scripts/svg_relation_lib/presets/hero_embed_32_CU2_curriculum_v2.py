# Bucket H · subtract_level default "L3" (2026-09-13)
"""HERO EMBED · 32_CU2_curriculum V2 · Hero canvas 1400×720 · dandelion 化.

参考 final_svg_relation/32_CU2_curriculum/step1_reference/curriculum_hero_reference.svg
1:1 复刻的视觉水准 + 完整数据可扩展性:

  - 顶部 chrome: serif title + inter caption + kicker hairline + FIGURE line
  - 4 KPI 带 (可选) · 左侧 hue vertical bar
  - Week axis + tick marks + module column labels
  - N module column (4-8): dark header + parchment body ·
      DURATION → TOPICS → ASSESSMENT → PREREQ → CREDIT WEIGHT
  - Milestone flag glyph 在 axis 上方 (2-6 gate)
  - Prereq flow arrow 在 body 下方
  - Sidebar (可选): KIND MIX + LEARNING OUTCOMES + stats
  - READING GUIDE 4 legend column (可选)
  - Notes · figure tag footer

build_curriculum_data kwargs:
    modules: [{
        code, title, subtitle, kind (core/elective/capstone),
        duration, topics: [str,...] (2-8), assessment, assessment_note,
        prereq, prereq_note, weight (0.0-1.0), hue (可选)
    }] · 4-8 个 · 默认 6 module engineering curriculum
    kpis: [{kicker, value, note, hue}] · 可选 · 4 张
    week_ticks: [str] · 每 module 一个 tick label
    axis_label: str · 默认 "WEEK"
    milestones: [{week_idx (0=first col start), label, kind (gate/demo)}]
        · 2-6 flag · 位置按 module 边界或中点
    sidebar: bool · 显示右侧 KIND MIX + LEARNING OUTCOMES
    outcomes: [{code, title, body}] · 3-4 sidebar 学习成果
    sidebar_stats: [{label, value}] · 底部 3 stat
    read_lines: [{hue, title, lines[]}] · 可选 · 4 legend
    notes / figure_tag · 底部
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from ..schemas import Graph
from ..schemas.graph import Node, Edge
from ..palettes import Palette
from ..engine import esc
from ..skins.editorial_atelier import (
    BONE_RUST, HUE, FONT_SANS, FONT_SERIF,
)
from ..skins.registry import get_active_skin as _get_active_skin
from ..skins._base import _fit_font_size, _visual_width


# ═════════════════════════════════════════════════════════════════
# baseline data · 对齐 step1 reference SVG · 6-module engineering curriculum
# ═════════════════════════════════════════════════════════════════

BASELINE_MODULES: List[Dict[str, Any]] = [
    {
        "code": "M01", "title": "Foundations",
        "subtitle": "shell · git · HTTP",
        "kind": "core", "hue": "navy",
        "duration": "24 h",
        "topics": [
            "Linux shell & SSH",
            "Git branching model",
            "HTTP/2 & TLS basics",
            "REST design patterns",
        ],
        "assessment": "CLI lab · quiz",
        "assessment_note": "pass mark 70%",
        "prereq": "— none —",
        "prereq_note": "entry point",
        "weight": 0.67,
    },
    {
        "code": "M02", "title": "Backend",
        "subtitle": "Go · Postgres · Redis",
        "kind": "core", "hue": "navy",
        "duration": "24 h",
        "topics": [
            "Go concurrency",
            "SQL modelling",
            "Redis caching layer",
            "gRPC contracts",
        ],
        "assessment": "API build · code rev",
        "assessment_note": "peer + mentor",
        "prereq": "M01 · Foundations",
        "prereq_note": "git & HTTP required",
        "weight": 0.90,
    },
    {
        "code": "M03", "title": "Frontend",
        "subtitle": "React 19 · Tailwind",
        "kind": "core", "hue": "navy",
        "duration": "24 h",
        "topics": [
            "React 19 & RSC",
            "State management",
            "Design tokens",
            "A11y WCAG 2.2",
        ],
        "assessment": "Widget · design QA",
        "assessment_note": "Vitest coverage 80%",
        "prereq": "M01 · Foundations",
        "prereq_note": "HTTP + REST needed",
        "weight": 0.80,
    },
    {
        "code": "M04", "title": "Cloud",
        "subtitle": "K8s · Helm · OTel",
        "kind": "elective", "hue": "green",
        "duration": "24 h",
        "topics": [
            "Docker & images",
            "K8s + Helm charts",
            "OTel tracing",
            "SLO burn alerts",
        ],
        "assessment": "Deploy demo · trace",
        "assessment_note": "live cluster review",
        "prereq": "M02 · Backend",
        "prereq_note": "API + Postgres skills",
        "weight": 0.75,
    },
    {
        "code": "M05", "title": "ML engineering",
        "subtitle": "PyTorch · vLLM · RAG",
        "kind": "elective", "hue": "green",
        "duration": "24 h",
        "topics": [
            "PyTorch basics",
            "LoRA fine-tune",
            "vLLM serving",
            "RAG + pgvector",
        ],
        "assessment": "Model card · eval",
        "assessment_note": "RAG demo required",
        "prereq": "M02 + M04",
        "prereq_note": "Backend + Cloud",
        "weight": 0.85,
    },
    {
        "code": "M06", "title": "Capstone",
        "subtitle": "ship + demo day",
        "kind": "capstone", "hue": "gold_p",
        "duration": "24 h",
        "topics": [
            "Scoping & brief",
            "Build sprint",
            "Runbook + review",
            "Demo & postmortem",
        ],
        "assessment": "Panel jury · demo",
        "assessment_note": "public artefact",
        "prereq": "all core + 1 elect",
        "prereq_note": "M01-03 mandatory",
        "weight": 1.00,
    },
]

BASELINE_KPIS: List[Dict[str, str]] = [
    {"kicker": "MODULES", "value": "6",
     "note": "3 core · 2 elect · 1 caps", "hue": "navy"},
    {"kicker": "DURATION", "value": "12 wk",
     "note": "144 h contact · 8h lab wkly", "hue": "green"},
    {"kicker": "MILESTONES", "value": "4",
     "note": "gates at W2 · W6 · W10 · W12", "hue": "gold_p"},
    {"kicker": "COHORT", "value": "24",
     "note": "engineers · L2 → L4 pathway", "hue": "navy"},
]

BASELINE_WEEK_TICKS: List[str] = [
    "W1 - W2", "W3 - W4", "W5 - W6",
    "W7 - W8", "W9 - W10", "W11 - W12",
]

BASELINE_MILESTONES: List[Dict[str, Any]] = [
    {"at_module": 1, "label": "GATE 1", "kind": "gate"},
    {"at_module": 3, "label": "GATE 2", "kind": "gate"},
    {"at_module": 5, "label": "GATE 3", "kind": "gate"},
    {"at_module": 6, "label": "DEMO DAY", "kind": "demo"},
]

BASELINE_OUTCOMES: List[Dict[str, str]] = [
    {"code": "LO1", "title": "Ship a service",
     "body": "Design + build + deploy an API-backed app end-to-end."},
    {"code": "LO2", "title": "Operate at SLO",
     "body": "Trace, alert, and remediate a running production system."},
    {"code": "LO3", "title": "Reason with AI",
     "body": "Evaluate LLM outputs and integrate RAG responsibly."},
    {"code": "LO4", "title": "Present artefacts",
     "body": "Write runbooks, review docs, and defend design choices."},
]

BASELINE_SIDEBAR_STATS: List[Dict[str, str]] = [
    {"label": "PASS THRESHOLD", "value": "3 / 4 gates"},
    {"label": "CAPSTONE WEIGHT", "value": "40 %"},
    {"label": "MENTOR HOURS", "value": "36 h"},
]

BASELINE_READ_LINES: List[Dict[str, Any]] = [
    {"hue": "navy", "title": "Kind hue",
     "lines": ["navy = core · green = elective ·",
               "amber = capstone"]},
    {"hue": "gray", "title": "Prereq flow",
     "lines": ["arrows link required module → next ·",
               "lower lane = branching"]},
    {"hue": "gold_p", "title": "Milestone gate",
     "lines": ["flag on axis at assessment week ·",
               "dark flag = demo day"]},
    {"hue": "green", "title": "Credit weight",
     "lines": ["bottom bar shows module contribution",
               "to final grade"]},
]

BASELINE_NOTES = (
    "Notes. Curriculum map is a horizontal timeline — position encodes "
    "week, colour encodes kind, arrows encode prerequisite. Sidebar carries "
    "kind counts and learning outcomes."
)


# ═════════════════════════════════════════════════════════════════
# color · dandelion hue map
# ═════════════════════════════════════════════════════════════════

_DANDELION_HUE: Dict[str, str] = {
    "navy":     "rgba(22,40,70,1)",
    "slate":    "rgba(68,78,100,1)",
    "green":    "rgba(16,106,82,1)",
    "gold_p":   "rgba(182,138,56,1)",
    "gold":     "rgba(182,138,56,1)",
    "rust":     "rgba(168,88,42,1)",
    "magenta":  "rgba(126,60,110,1)",
    "indigo":   "rgba(30,60,120,1)",
    "orange":   "rgba(196,120,52,1)",
    "olive":    "rgba(122,132,60,1)",
    "blue":     "rgba(56,90,148,1)",
    "cinnamon": "rgba(84,60,44,1)",
    "red":      "rgba(194,93,93,1)",
    "charcoal": "rgba(38,42,54,1)",
    "steel":    "rgba(84,108,120,1)",
    "teal":     "rgba(28,110,132,1)",
    "gray":     "rgba(115,120,132,1)",
}

# kind → hue 默认映射
_KIND_HUE: Dict[str, str] = {
    "core":     "navy",
    "elective": "green",
    "capstone": "gold_p",
}

_LEADING_HUE_FALLBACKS: Tuple[str, ...] = (
    "rust", "navy", "blue", "green", "olive", "gold_p", "magenta", "cinnamon",
)

_KIND_LABEL: Dict[str, str] = {
    "core":     "CORE",
    "elective": "ELECTIVE",
    "capstone": "CAPSTONE",
}


def _hue_rgba(name: str, alpha: float = 1.0) -> str:
    """Resolve a hue name → rgba string.

    Priority (fix · 2026-09-11 · R2):
      1. Active skin's HUE dict (so boardroom_navy / mbb_consulting actually
         apply their own domain colors instead of being dandelion clones).
      1b. Skin HUE alias: 'navy' → 'slate' (skin's dark cool tone) when navy
          not shipped by skin (mbb / boardroom / editorial all define slate).
      2. Module-level HUE (= editorial_atelier.HUE, mutated by
         gen_svg_relations' _skin_override context) — same alias table.
      3. _DANDELION_HUE baseline fallback.
    """
    _alias: Dict[str, Tuple[str, ...]] = {
        "navy":   ("slate", "blue", "rust"),
        "gold_p": ("gold_p", "cinnamon", "olive"),
        "green":  ("green", "olive"),
    }

    def _resolve_from(hmap: Dict[str, Any], key: str) -> Optional[str]:
        """Try `key`, then alias keys, in hmap. Return rgba string or None."""
        candidates: List[str] = [key] + list(_alias.get(key, ()))
        for cand in candidates:
            c = hmap.get(cand) if hmap else None
            if not c:
                continue
            if isinstance(c, str) and c.startswith("#"):
                h = c.lstrip("#")
                r, g, b = int(h[:2], 16), int(h[2:4], 16), int(h[4:6], 16)
                return f"rgba({r},{g},{b},{alpha:.3f})"
            if isinstance(c, str) and c.startswith("rgba"):
                m = re.match(r"rgba\((\d+),\s*(\d+),\s*(\d+),\s*[\d.]+\)", c)
                if m:
                    return f"rgba({m.group(1)},{m.group(2)},{m.group(3)},{alpha:.3f})"
                return c
        return None

    # 1. active skin
    try:
        skin = _get_active_skin()
        if skin is not None:
            skin_hue = getattr(skin, "HUE", None)
            resolved = _resolve_from(skin_hue or {}, name)
            if resolved is not None:
                return resolved
    except Exception:
        pass
    # 2. module-level HUE (editorial_atelier.HUE · palette 覆写后含 palette.hues)
    resolved = _resolve_from(HUE, name)
    if resolved is not None:
        return resolved
    # 3. dandelion fallback
    base = _DANDELION_HUE.get(name)
    if base:
        m = re.match(r"rgba\((\d+),\s*(\d+),\s*(\d+),\s*[\d.]+\)", base)
        if m:
            return f"rgba({m.group(1)},{m.group(2)},{m.group(3)},{alpha:.3f})"
        return base
    # ultimate fallback
    return f"rgba(163,88,50,{alpha:.3f})"


# ═════════════════════════════════════════════════════════════════
# canonical font-size 阶梯
# ═════════════════════════════════════════════════════════════════

_CANONICAL_SIZES: Tuple[float, ...] = (
    22.0, 20.0, 18.0, 17.0, 16.0, 15.0, 14.0, 13.0, 12.0,
    11.5, 11.0, 10.5, 10.0,
)


def _snap_fs(fs: float, floor_min: float = 10.0) -> float:
    for canon in _CANONICAL_SIZES:
        if fs >= canon - 1e-6:
            return max(canon, floor_min)
    return floor_min


def _fit_snap(text: str, max_w: float, base: float,
              min_size: float = 10.0) -> Tuple[float, str]:
    raw_fs, _ = _fit_font_size(text, max_w, base, min_size=min_size)
    snapped = _snap_fs(raw_fs, floor_min=min_size)
    _, out_text = _fit_font_size(text, max_w, snapped, min_size=snapped)
    return snapped, out_text


def _wrap_text_2line(text: str, max_w: float, char_w: float = 5.4) -> List[str]:
    if not text:
        return [""]
    max_chars = max(int(max_w / char_w), 6)
    if len(text) <= max_chars:
        return [text]
    cut = max_chars
    for j in range(max_chars, max(max_chars // 2, 6), -1):
        if j < len(text) and text[j] in " ·,-;/":
            cut = j
            break
    line1 = text[:cut].rstrip(" ·,-;/")
    remaining = text[cut:].lstrip(" ·,-;/")
    if len(remaining) <= max_chars:
        return [line1, remaining]
    cut2 = max_chars - 1
    for j in range(max_chars - 1, max(max_chars // 2, 6), -1):
        if j < len(remaining) and remaining[j] in " ·,-;/":
            cut2 = j
            break
    line2 = remaining[:cut2].rstrip(" ·,-;/")
    return [line1, line2]


def _text_width(text: str, font_size: float,
                char_w_ratio: float = 0.55) -> float:
    return _visual_width(text, font_size * char_w_ratio)


def _drop_to_width(text: str, max_w: float, font_size: float,
                   char_w_ratio: float = 0.55) -> str:
    """Return a single-line prefix that fits max_w. No ellipsis."""
    clean = re.sub(r"\s+", " ", str(text or "")).strip()
    if not clean or _text_width(clean, font_size, char_w_ratio) <= max_w:
        return clean
    out = ""
    for ch in clean:
        candidate = out + ch
        if _text_width(candidate, font_size, char_w_ratio) <= max_w:
            out = candidate
        else:
            break
    return out.rstrip(" ·,-;/") or clean[:1]


def _fit_drop(text: str, max_w: float, base: float,
              min_size: float = 11.0,
              char_w_ratio: float = 0.55) -> Tuple[float, str]:
    fs, _ = _fit_font_size(str(text or ""), max_w, base, min_size=min_size)
    fs = min(base, max(min_size, fs))
    fs = _snap_fs(fs, floor_min=min_size)
    out = _drop_to_width(str(text or ""), max_w, fs, char_w_ratio)
    return fs, out


def _section_label(label: str, max_w: float) -> str:
    short = {
        "ASSESSMENT": "ASSESS",
        "CREDIT WEIGHT": "WEIGHT",
    }
    candidate = short.get(label, label)
    if _text_width(candidate, 14.0, 0.64) <= max_w:
        return candidate
    return _drop_to_width(candidate, max_w, 13.0, 0.64)


def _week_tick_label(label: str, index: int, max_w: float) -> str:
    text = str(label or "")
    if _text_width(text, 14.0, 0.55) <= max_w:
        return text
    return f"W{index + 1}"


def _milestone_label(label: str, ordinal: int, kind: str, max_w: float) -> str:
    text = str(label or "").strip()
    if text and _text_width(text, 15.0, 0.58) <= max_w:
        return text
    if kind == "demo":
        return "DEMO"
    return f"G{ordinal}"


def _ensure_leading_hue_contrast(modules: List[Node]) -> None:
    """Differentiate the first curriculum card when early modules share one kind."""
    if len(modules) < 3:
        return
    early_hues = [str(getattr(m, "group", "") or "navy") for m in modules[:3]]
    if early_hues[0] not in set(early_hues[1:]):
        return
    peer_hues = set(early_hues[1:])
    for hue in _LEADING_HUE_FALLBACKS:
        if hue not in peer_hues:
            modules[0].group = hue
            return


# ═════════════════════════════════════════════════════════════════
# build_curriculum_data · Graph 工厂
# ═════════════════════════════════════════════════════════════════

def build_curriculum_data(
    modules: Optional[List[Dict[str, Any]]] = None,
    kpis: Optional[List[Dict[str, str]]] = None,
    week_ticks: Optional[List[str]] = None,
    milestones: Optional[List[Dict[str, Any]]] = None,
    outcomes: Optional[List[Dict[str, str]]] = None,
    sidebar_stats: Optional[List[Dict[str, str]]] = None,
    read_lines: Optional[List[Dict[str, Any]]] = None,
    notes: Optional[str] = None,
    axis_label: str = "WEEK",
    sidebar: bool = True,
    figure_tag: str = "",
    kicker: str = "FIGURE 32 · CURRICULUM MAP",
    kicker_body: str = "",
    figure_title: str = "Engineering Academy · 2026 curriculum map",
    # NOTE (2026-09-13 · P1 audit): 副标追加 C/EL/CAP 徽标 legend · 让模块类型徽标可
    # 被读者自解释 · 无需外部图例.
    figure_caption: str = (
        "6 modules · 12 weeks · prerequisite arrows connect module "
        "N → N+1 · milestone flags mark assessment gates · "
        "C=core · EL=elective · CAP=capstone"
    ),
    source: str = "Source · Learning ops · Sept 2026",
    read_kicker: str = "READING GUIDE · CURRICULUM MAP",
    show_reading_guide: bool = False,
    show_prereq_flow: bool = False,
    show_kind_mix_sidebar: bool = False,
) -> Graph:
    """构建 curriculum Graph.

    modules 必需 4-8 个 · 传 None 用 6 module baseline.
    sidebar=False ⇒ 隐藏右侧栏 · module column 铺满宽度.
    kpis / milestones / outcomes / read_lines 传 [] ⇒ 关闭该区.

    Chatter defaults (R2 fix · 2026-09-11):
        show_reading_guide=False (READING GUIDE 4-legend column)
        show_prereq_flow=False (bottom prereq flow band)
        show_kind_mix_sidebar=False (sidebar KIND MIX 冗余于 column header 色带)
        kicker_body="" · notes 默认走 [] 空 · figure_tag=""
        opt-in by passing True / non-empty strings.
    """
    mods = modules if modules is not None else BASELINE_MODULES
    kps = kpis if kpis is not None else BASELINE_KPIS
    ticks = week_ticks if week_ticks is not None else BASELINE_WEEK_TICKS
    mls = milestones if milestones is not None else BASELINE_MILESTONES
    ocs = outcomes if outcomes is not None else BASELINE_OUTCOMES
    sst = (sidebar_stats if sidebar_stats is not None
           else [])  # default empty · opt-in per audit
    # read_lines gated on show_reading_guide
    if read_lines is not None:
        rls = read_lines
    elif show_reading_guide:
        rls = BASELINE_READ_LINES
    else:
        rls = []
    nts = notes if notes is not None else ""

    if len(mods) < 4 or len(mods) > 8:
        raise ValueError(
            f"modules count {len(mods)} out of range · must be 4..8"
        )

    gnodes: List[Node] = []
    for i, m in enumerate(mods):
        mid = str(m.get("id", f"m{i}"))
        kind = str(m.get("kind", "core"))
        hue = str(m.get("hue", "")) or _KIND_HUE.get(kind, "navy")
        gnodes.append(Node(
            id=mid, label=str(m.get("title", "")),
            group=hue,
            extra={
                "code": str(m.get("code", f"M{i + 1:02d}")),
                "subtitle": str(m.get("subtitle", "")),
                "kind": kind,
                "duration": str(m.get("duration", "")),
                "topics": list(m.get("topics", []) or []),
                "assessment": str(m.get("assessment", "")),
                "assessment_note": str(m.get("assessment_note", "")),
                "prereq": str(m.get("prereq", "")),
                "prereq_note": str(m.get("prereq_note", "")),
                "weight": float(m.get("weight", 0.5)),
            },
        ))

    graph_extra: Dict[str, Any] = {
        "kpis": kps,
        "week_ticks": ticks,
        "milestones": mls,
        "outcomes": ocs,
        "sidebar_stats": sst,
        "read_lines": rls,
        "notes": nts,
        "figure_tag": figure_tag,
        "read_kicker": read_kicker,
        "axis_label": axis_label,
        "kicker_body": kicker_body,
        "sidebar": bool(sidebar),
        "show_prereq_flow": bool(show_prereq_flow),
        "show_kind_mix_sidebar": bool(show_kind_mix_sidebar),
    }

    g = Graph(
        nodes=gnodes, edges=[], directed=True,
        figure_title=figure_title,
        figure_caption=figure_caption,
        source=source,
        encoding_note="",
        kicker=kicker,
    )
    setattr(g, "extra", graph_extra)
    return g


# 向后兼容 alias (v1 tree 生成器)
def build_curriculum_tree(**kwargs) -> Graph:
    return build_curriculum_data(**kwargs)


HERO_CU2_DATA = build_curriculum_data()


# ═════════════════════════════════════════════════════════════════
# render constants
# ═════════════════════════════════════════════════════════════════

VIEW_W = 1400
VIEW_H = 720
BG_COLOR = "rgba(247,240,226,1)"
INK_COLOR = "rgba(24,26,34,1)"
INK_DIM = "rgba(64,70,82,1)"
GRAY_COLOR = "rgba(115,120,132,1)"
HAIR_COLOR = "rgba(24,26,34,1)"
HAIR_LIGHT = "rgba(175,178,188,1)"
CREAM_COLOR = "rgba(247,240,226,1)"
PARCHMENT = "rgba(247,240,226,1)"
KPI_BG = "rgba(243,235,218,1)"

BODY_LEFT = 60
BODY_RIGHT = 1340
BODY_WIDTH = BODY_RIGHT - BODY_LEFT

# Module column area
MODULES_LEFT = 108
MODULES_RIGHT_WITH_SIDEBAR = 1068   # leaves 1088..1340 for sidebar
MODULES_RIGHT_NO_SIDEBAR = 1340
COL_GAP = 4                          # gap between adjacent module columns

# Y bands · R2b · fix R1 layout regression:
# KPI strip 130-180 must not overlap milestone flags or axis.
# 3 stacked bands: KPI (130-180) · FLAG (198-232) · AXIS (240-244).
AXIS_Y = 244                         # was 200 · shifted +44 to clear flag band
AXIS_KICKER_Y = 236                  # "WEEK" label + tick labels · was 190
HEADER_TOP_Y = 258                   # was 214 · under axis
HEADER_H = 76                        # title 22-24pt + code 15pt + pill (stacked)
BODY_CARD_TOP_Y = 340                # was 296 · header_top+header_h+6
BODY_CARD_H = 296                    # was 306 · slightly tighter to reserve foot gap
BODY_CARD_BOTTOM_Y = BODY_CARD_TOP_Y + BODY_CARD_H   # 636

# Prereq arrow lane (default off · R2)
PREREQ_LANE_KICKER_Y = 650
PREREQ_LANE_LINE_Y = 654
PREREQ_UPPER_Y = 668
PREREQ_LOWER_Y = 682

# Milestone flag band · below KPI (180) · above axis (244)
FLAG_TOP_Y = 184
FLAG_MID_Y = 195
FLAG_BOTTOM_Y = 206

# Sidebar
SIDEBAR_X = 1088
SIDEBAR_RIGHT = 1340
SIDEBAR_TOP_Y = 258                  # was 192 · align with new HEADER_TOP_Y

# Footer
GUIDE_HAIR_Y = 668
GUIDE_KICKER_Y = 684
GUIDE_TITLE_Y = 700
GUIDE_BODY_Y = 712
FOOTER_HAIR_Y = 700
FOOTER_TEXT_Y = 714


# ═════════════════════════════════════════════════════════════════
# main render
# ═════════════════════════════════════════════════════════════════

def render_hero_embed_cu2_curriculum_v2(
    data: Graph = HERO_CU2_DATA,
    palette: Palette = BONE_RUST,
    *,
    subtract_level: str = "L3",
) -> str:
    """Render Curriculum-map hero embed (1400×720)."""

    # [SKIN-PATCH-L1] globals patch: skin.PALETTE 覆写模块级色常量
    _MOD_L1 = globals()
    _ORIG_L1 = {k: _MOD_L1[k] for k in ("BG_COLOR", "INK_COLOR", "INK_DIM", "GRAY_COLOR", "HAIR_COLOR", "HAIR_LIGHT", "CREAM_COLOR",)}
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
            if getattr(_SP_L1, 'bg_alt', None): _MOD_L1['CREAM_COLOR'] = _SP_L1.bg_alt
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
        pal = palette or BONE_RUST
        extra = getattr(data, "extra", {}) or {}

        modules = list(getattr(data, "nodes", []) or [])
        n_mod = len(modules)
        if n_mod < 4 or n_mod > 8:
            raise ValueError(
                f"modules count {n_mod} out of range · must be 4..8"
            )

        # Bucket H (2026-09-13) · subtract_level 默认 L3 · 清空次要说明字段
        # L1: 关 figure_tag / read_kicker / kicker_body
        # L2: L1 + kpis / read_lines / notes / figure_caption
        # L3: L2 + module.subtitle (右侧 italic 说明)
        if subtract_level and subtract_level != "L0":
            import copy as _copy
            data = _copy.deepcopy(data)
            extra = getattr(data, "extra", {}) or {}
            modules = list(getattr(data, "nodes", []) or [])
            if subtract_level in ("L1", "L2", "L3"):
                extra["figure_tag"] = ""
                extra["read_kicker"] = ""
                extra["kicker_body"] = ""
            if subtract_level in ("L2", "L3"):
                extra["kpis"] = []
                extra["read_lines"] = []
                extra["notes"] = ""
                try:
                    data.figure_caption = ""
                except Exception:
                    pass
            if subtract_level == "L3":
                for m in modules:
                    m_ex = getattr(m, "extra", None) or {}
                    m_ex["subtitle"] = ""
                    m_ex["assessment_note"] = ""
                    m_ex["prereq_note"] = ""
                    m.extra = m_ex
                extra["outcomes"] = []
                extra["sidebar_stats"] = []
                extra["sidebar"] = False
                extra["show_kind_mix_sidebar"] = False
                try:
                    data.kicker = ""
                except Exception:
                    pass
            data.extra = extra
            _ensure_leading_hue_contrast(modules)

        kpis: List[Dict[str, Any]] = list(extra.get("kpis", []) or [])
        week_ticks: List[str] = list(extra.get("week_ticks", []) or [])
        milestones: List[Dict[str, Any]] = list(extra.get("milestones", []) or [])
        outcomes: List[Dict[str, str]] = list(extra.get("outcomes", []) or [])
        sidebar_stats: List[Dict[str, str]] = list(
            extra.get("sidebar_stats", []) or [])
        read_lines: List[Dict[str, Any]] = list(extra.get("read_lines", []) or [])
        notes: str = str(extra.get("notes", "") or "")
        figure_tag: str = str(extra.get("figure_tag", "") or "")
        read_kicker: str = str(extra.get("read_kicker", "") or "")
        axis_label: str = str(extra.get("axis_label", "WEEK") or "WEEK")
        kicker_body: str = str(extra.get("kicker_body", "") or "")
        sidebar_on: bool = bool(extra.get("sidebar", True))
        show_prereq_flow: bool = bool(extra.get("show_prereq_flow", False))
        show_kind_mix_sidebar: bool = bool(
            extra.get("show_kind_mix_sidebar", False))

        kicker_txt = getattr(data, "kicker", "") or ""
        title = getattr(data, "figure_title", "") or ""
        caption = getattr(data, "figure_caption", "") or ""
        compact_chrome = bool(title and subtract_level == "L3" and not caption)

        parts: List[str] = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {VIEW_W} {VIEW_H}">',
            f'<rect x="0" y="0" width="{VIEW_W}" height="{VIEW_H}" fill="{BG_COLOR}"/>',
        ]

        # ─── defs · arrow markers ───
        parts.append(
            '<defs>'
            '<marker id="cu_arrow" viewBox="0 0 10 10" refX="9" refY="5" '
            'markerWidth="6" markerHeight="6" orient="auto">'
            f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{GRAY_COLOR}"/>'
            '</marker>'
            '</defs>'
        )

        # ─── chrome ───
        if title:
            if compact_chrome:
                title_fs, title_out = _fit_drop(
                    title, BODY_WIDTH, 22.0, min_size=18.0,
                    char_w_ratio=0.58,
                )
                parts.append(
                    f'<text x="{BODY_LEFT}" y="154" font-family="{FONT_SERIF}" '
                    f'font-size="{title_fs:.1f}" font-weight="600" fill="{INK_COLOR}" '
                    f'letter-spacing="0.1">{esc(title_out)}</text>'
                )
            else:
                parts.append(
                    f'<text x="{BODY_LEFT}" y="52" font-family="{FONT_SERIF}" '
                    f'font-size="30" font-weight="600" fill="{INK_COLOR}" '
                    f'letter-spacing="0.1">{esc(title)}</text>'
                )
        if caption:
            _, caption_out = _fit_font_size(
                caption, BODY_WIDTH, 20.0, min_size=17.0)
            parts.append(
                f'<text x="{BODY_LEFT}" y="80" font-family="{FONT_SANS}" '
                f'font-size="20" fill="{INK_DIM}" letter-spacing="0.2">'
                f'{esc(caption_out)}</text>'
            )
        if not compact_chrome and (title or caption or kicker_txt or kicker_body):
            parts.append(
                f'<line x1="{BODY_LEFT}" y1="94" x2="{BODY_RIGHT}" y2="94" '
                f'stroke="{HAIR_COLOR}" stroke-width="0.8"/>'
            )
        if kicker_txt:
            parts.append(
                f'<text x="{BODY_LEFT}" y="112" font-family="{FONT_SANS}" '
                f'font-size="16" fill="{INK_DIM}" font-weight="700" '
                f'letter-spacing="1.5">{esc(kicker_txt)}</text>'
            )
        if kicker_body:
            # kicker_body next to kicker (R2 · default off · opt-in)
            kicker_body_x = max(240, BODY_LEFT + len(kicker_txt) * 11 + 24)
            parts.append(
                f'<text x="{kicker_body_x}" y="112" font-family="{FONT_SANS}" '
                f'font-size="16" fill="{GRAY_COLOR}" letter-spacing="0.4">'
                f'{esc(kicker_body)}</text>'
            )

        # ─── KPI strip (可选 · 4 slot 均分) ───
        if kpis:
            n_kpi = min(len(kpis), 4)
            kpi_gap = 16
            kpi_avail = BODY_WIDTH - kpi_gap * (n_kpi - 1)
            kpi_w = kpi_avail / n_kpi
            kpi_y = 130
            kpi_h = 50
            for i in range(n_kpi):
                k = kpis[i]
                kx = BODY_LEFT + i * (kpi_w + kpi_gap)
                hue = str(k.get("hue", "navy"))
                c = _hue_rgba(hue)
                parts.append(
                    f'<rect x="{kx:.1f}" y="{kpi_y}" width="{kpi_w:.1f}" '
                    f'height="{kpi_h}" fill="{KPI_BG}" '
                    f'stroke="{HAIR_LIGHT}" stroke-width="0.6"/>'
                )
                parts.append(
                    f'<rect x="{kx:.1f}" y="{kpi_y}" width="4" height="{kpi_h}" '
                    f'fill="{c}"/>'
                )
                k_kicker = str(k.get("kicker", ""))
                parts.append(
                    f'<text x="{kx + 14:.1f}" y="{kpi_y + 18}" '
                    f'font-family="{FONT_SANS}" font-size="15" fill="{GRAY_COLOR}" '
                    f'font-weight="700" letter-spacing="1.4">'
                    f'{esc(k_kicker)}</text>'
                )
                val_txt = str(k.get("value", ""))
                val_fs, val_out = _fit_snap(
                    val_txt, kpi_w * 0.42, 25.0, min_size=20.0)
                parts.append(
                    f'<text x="{kx + 14:.1f}" y="{kpi_y + 42}" '
                    f'font-family="{FONT_SERIF}" font-size="{val_fs:.1f}" '
                    f'fill="{INK_COLOR}" font-weight="700">{esc(val_out)}</text>'
                )
                note_txt = str(k.get("note", ""))
                if note_txt:
                    note_x = kx + 14 + val_fs * 0.60 * max(3, len(val_out)) + 8
                    note_avail = kpi_w - (note_x - kx) - 8
                    note_fs, note_out = _fit_snap(
                        note_txt, note_avail, 16.0, min_size=15.0
                    )
                    parts.append(
                        f'<text x="{note_x:.1f}" y="{kpi_y + 42}" '
                        f'font-family="{FONT_SANS}" font-size="{note_fs:.1f}" '
                        f'fill="{GRAY_COLOR}">{esc(note_out)}</text>'
                    )

        # ─── modules geometry ───
        modules_right = (MODULES_RIGHT_WITH_SIDEBAR if sidebar_on
                         else MODULES_RIGHT_NO_SIDEBAR)
        modules_span = modules_right - MODULES_LEFT
        col_w = (modules_span - COL_GAP * (n_mod - 1)) / n_mod
        # Card box slightly wider than axis-tick gap (card is 156 wide over 160 gap)
        col_geoms: List[Dict[str, float]] = []
        for i in range(n_mod):
            cx0 = MODULES_LEFT + i * (col_w + COL_GAP)
            col_geoms.append({
                "x": cx0, "w": col_w,
                "cx": cx0 + col_w / 2,
                "tick_left": cx0,
                "tick_right": cx0 + col_w,
            })

        # ─── week axis ───
        axis_kicker_x = BODY_LEFT
        axis_label_max_w = MODULES_LEFT - BODY_LEFT - 4
        axis_label_out = (
            axis_label
            if _text_width(axis_label, 13.0, 0.66) <= axis_label_max_w
            else "WEEK"
        )
        axis_label_fs, axis_label_fit = _fit_drop(
            axis_label_out,
            axis_label_max_w,
            13.0,
            min_size=11.0,
            char_w_ratio=0.66,
        )
        parts.append(
            f'<text x="{axis_kicker_x}" y="{AXIS_KICKER_Y}" '
            f'font-family="{FONT_SANS}" font-size="{axis_label_fs:.1f}" fill="{GRAY_COLOR}" '
            f'font-weight="700" letter-spacing="0.4">{esc(axis_label_fit)}</text>'
        )
        axis_line_right = modules_right
        axis_bar_y = AXIS_KICKER_Y - 15
        axis_bar_h = 20
        i_group = 0
        while i_group < n_mod:
            group_hue = str(getattr(modules[i_group], "group", "") or "navy")
            j_group = i_group + 1
            while (
                j_group < n_mod
                and str(getattr(modules[j_group], "group", "") or "navy") == group_hue
            ):
                j_group += 1
            gx0 = col_geoms[i_group]["tick_left"]
            gx1 = (
                col_geoms[j_group]["tick_left"]
                if j_group < n_mod
                else col_geoms[j_group - 1]["tick_right"]
            )
            group_color = _hue_rgba(group_hue, 0.18)
            group_border = _hue_rgba(group_hue, 0.85)
            parts.append(
                f'<rect x="{gx0:.1f}" y="{axis_bar_y:.1f}" '
                f'width="{gx1 - gx0:.1f}" height="{axis_bar_h}" '
                f'fill="{group_color}" stroke="{group_border}" stroke-width="0.8"/>'
            )
            i_group = j_group

        # tick labels inside the progress range row.
        for i, geom in enumerate(col_geoms):
            module_hue = str(getattr(modules[i], "group", "") or "navy")
            seg_color = _hue_rgba(module_hue, 0.88)
            # tick mark at left edge
            parts.append(
                f'<line x1="{geom["tick_left"]:.1f}" y1="{axis_bar_y:.1f}" '
                f'x2="{geom["tick_left"]:.1f}" y2="{axis_bar_y + axis_bar_h:.1f}" '
                f'stroke="{seg_color}" stroke-width="1.0"/>'
            )
            if i < len(week_ticks):
                tick_label = _week_tick_label(week_ticks[i], i, col_w - 18)
                tk_fs, tk_out = _fit_drop(
                    tick_label, col_w - 18, 13.0, min_size=11.0)
                parts.append(
                    f'<text x="{geom["cx"]:.1f}" y="{axis_bar_y + 14:.1f}" '
                    f'text-anchor="middle" font-family="{FONT_SANS}" '
                    f'font-size="{tk_fs:.1f}" fill="{INK_COLOR}" font-weight="700">'
                    f'{esc(tk_out)}</text>'
                )
        # final tick at right edge
        parts.append(
            f'<line x1="{axis_line_right:.1f}" y1="{axis_bar_y:.1f}" '
            f'x2="{axis_line_right:.1f}" y2="{axis_bar_y + axis_bar_h:.1f}" '
            f'stroke="{_hue_rgba(str(getattr(modules[-1], "group", "") or "navy"), 0.88)}" '
            f'stroke-width="1.0"/>'
        )

        # ─── milestone flags (above axis) ───
        # Estimate right edge available for flag+label
        right_bound = (SIDEBAR_X - 4) if sidebar_on else BODY_RIGHT
        show_milestone_labels = col_w >= 230
        # atomize fix (2026-09-14): track placed label bboxes so that adjacent
        # milestones (esp. when the second one flips left because it doesn't
        # fit on the right) don't paint their labels on top of the previous
        # milestone's label. Stack colliding milestones vertically (row 2).
        _ms_label_bboxes: List[Tuple[float, float, float, float]] = []
        for ms_i, ms in enumerate(milestones, start=1):
            at = int(ms.get("at_module", 1))  # 1-indexed
            idx = max(1, min(n_mod, at))
            anchor_x = (
                col_geoms[idx]["tick_left"]
                if idx < n_mod
                else col_geoms[idx - 1]["tick_right"]
            )
            kind = str(ms.get("kind", "gate"))
            label = _milestone_label(
                str(ms.get("label", "")), ms_i, kind,
                max(42.0, min(88.0, col_w * 0.72)),
            )
            is_demo = (kind == "demo")
            module_hue = str(getattr(modules[idx - 1], "group", "") or "navy")
            flag_color = _hue_rgba(module_hue)
            flag_lift = 18 if not kpis else 0
            flag_bottom = FLAG_BOTTOM_Y - flag_lift
            flag_top = (FLAG_TOP_Y if is_demo else (FLAG_TOP_Y + 6)) - flag_lift
            flag_w = 40 if is_demo else 30
            notch = 8 if is_demo else 5
            label_fs = 15.0
            est_label_w = _text_width(label, label_fs, 0.62) + 8
            # decide flag direction: default right; flip left if would clip right edge
            needed_right = anchor_x + flag_w + 4 + est_label_w
            flip = needed_right > right_bound
            # vertical mast
            mast_axis_y = axis_bar_y if not kpis else AXIS_Y
            parts.append(
                f'<line x1="{anchor_x:.1f}" y1="{mast_axis_y:.1f}" '
                f'x2="{anchor_x:.1f}" y2="{flag_bottom + 5}" '
                f'stroke="{flag_color}" '
                f'stroke-width="{1.8 if is_demo else 1.5}"/>'
            )
            # candidate label bbox (17pt height ~ 20pt)
            lbl_h = 20.0
            if not flip:
                lbl_x0 = anchor_x + flag_w + 4
                lbl_y0 = FLAG_MID_Y - 14
                lbl_x1 = lbl_x0 + est_label_w
            else:
                lbl_x1 = anchor_x - flag_w - 4
                lbl_y0 = FLAG_MID_Y - 14
                lbl_x0 = lbl_x1 - est_label_w
            # collision check against previous labels
            y_shift = 0.0
            for (px0, py0, pw, ph) in _ms_label_bboxes:
                if (lbl_x0 < px0 + pw and lbl_x0 + est_label_w > px0 and
                        lbl_y0 + y_shift < py0 + ph and
                        lbl_y0 + y_shift + lbl_h > py0):
                    # shift this label down one row (below previous)
                    y_shift = max(y_shift, (py0 + ph) - lbl_y0 + 2.0)
            lbl_mid_y = FLAG_MID_Y - flag_lift + y_shift
            _ms_label_bboxes.append(
                (lbl_x0, lbl_y0 + y_shift, est_label_w, lbl_h))
            if not flip:
                # right-pointing pennant
                parts.append(
                    f'<polygon points="{anchor_x:.1f},{flag_top} '
                    f'{anchor_x:.1f},{flag_bottom} '
                    f'{anchor_x + flag_w:.1f},{flag_bottom} '
                    f'{anchor_x + flag_w - notch:.1f},'
                    f'{(flag_top + flag_bottom) / 2:.1f} '
                    f'{anchor_x + flag_w:.1f},{flag_top}" '
                    f'fill="{flag_color}" stroke="rgba(24,26,34,0.4)" '
                    f'stroke-width="0.4"/>'
                )
                if show_milestone_labels:
                    parts.append(
                        f'<text x="{anchor_x + flag_w + 4:.1f}" y="{lbl_mid_y:.1f}" '
                        f'font-family="{FONT_SANS}" font-size="{label_fs:.1f}" fill="{INK_COLOR}" '
                        f'font-weight="700">'
                        f'{esc(label)}</text>'
                    )
            else:
                # left-pointing pennant (mirror)
                parts.append(
                    f'<polygon points="{anchor_x:.1f},{flag_top} '
                    f'{anchor_x:.1f},{flag_bottom} '
                    f'{anchor_x - flag_w:.1f},{flag_bottom} '
                    f'{anchor_x - flag_w + notch:.1f},'
                    f'{(flag_top + flag_bottom) / 2:.1f} '
                    f'{anchor_x - flag_w:.1f},{flag_top}" '
                    f'fill="{flag_color}" stroke="rgba(24,26,34,0.4)" '
                    f'stroke-width="0.4"/>'
                )
                if show_milestone_labels:
                    parts.append(
                        f'<text x="{anchor_x - flag_w - 4:.1f}" y="{lbl_mid_y:.1f}" '
                        f'text-anchor="end" '
                        f'font-family="{FONT_SANS}" font-size="{label_fs:.1f}" fill="{INK_COLOR}" '
                        f'font-weight="700">'
                        f'{esc(label)}</text>'
                    )

        # ─── module columns ───
        for i, node in enumerate(modules):
            _emit_module_column(parts, col_geoms[i], node)

        # ─── prereq flow lane (可选 · default off · R2) ───
        if show_prereq_flow:
            parts.append(
                f'<line x1="{BODY_LEFT}" y1="{PREREQ_LANE_LINE_Y}" '
                f'x2="{modules_right}" y2="{PREREQ_LANE_LINE_Y}" '
                f'stroke="{HAIR_LIGHT}" stroke-width="0.5"/>'
            )
            parts.append(
                f'<text x="{BODY_LEFT}" y="{PREREQ_LANE_KICKER_Y}" '
                f'font-family="{FONT_SANS}" font-size="15" fill="{GRAY_COLOR}" '
                f'font-weight="700" letter-spacing="1.4">PREREQ FLOW</text>'
            )
            # Linear chain arrows M_i → M_(i+1) at upper lane
            for i in range(n_mod - 1):
                x1 = col_geoms[i]["cx"]
                x2 = col_geoms[i + 1]["cx"]
                parts.append(
                    f'<line x1="{x1:.1f}" y1="{PREREQ_UPPER_Y}" '
                    f'x2="{x2 - 6:.1f}" y2="{PREREQ_UPPER_Y}" '
                    f'stroke="{GRAY_COLOR}" stroke-width="1.1" '
                    f'marker-end="url(#cu_arrow)"/>'
                )
                # short verticals from card bottom to lane
                parts.append(
                    f'<line x1="{x1:.1f}" y1="{BODY_CARD_BOTTOM_Y}" '
                    f'x2="{x1:.1f}" y2="{PREREQ_UPPER_Y}" '
                    f'stroke="{GRAY_COLOR}" stroke-width="0.6" '
                    f'stroke-dasharray="2 2" opacity="0.6"/>'
                )
            # last module vertical (down to lane just for consistency)
            if n_mod >= 1:
                x_last = col_geoms[-1]["cx"]
                parts.append(
                    f'<line x1="{x_last:.1f}" y1="{BODY_CARD_BOTTOM_Y}" '
                    f'x2="{x_last:.1f}" y2="{PREREQ_UPPER_Y}" '
                    f'stroke="{GRAY_COLOR}" stroke-width="0.6" '
                    f'stroke-dasharray="2 2" opacity="0.6"/>'
                )

        # ─── sidebar (可选) ───
        if sidebar_on:
            _emit_sidebar(
                parts, outcomes, sidebar_stats, modules,
                show_kind_mix=show_kind_mix_sidebar)

        # ─── reading guide (可选 · default off · R2) ───
        if read_lines:
            parts.append(
                f'<line x1="{BODY_LEFT}" y1="{GUIDE_HAIR_Y}" x2="{BODY_RIGHT}" '
                f'y2="{GUIDE_HAIR_Y}" stroke="{HAIR_LIGHT}" stroke-width="0.4"/>'
            )
            if read_kicker:
                parts.append(
                    f'<text x="{BODY_LEFT}" y="{GUIDE_KICKER_Y}" '
                    f'font-family="{FONT_SANS}" font-size="17" '
                    f'font-weight="700" fill="{INK_COLOR}" letter-spacing="1.4">'
                    f'{esc(read_kicker)}</text>'
                )
            n_read = min(len(read_lines), 4)
            col_gap = 20
            col_avail = BODY_WIDTH - col_gap * (n_read - 1)
            col_w_r = col_avail / n_read
            for i in range(n_read):
                rl = read_lines[i]
                cx0 = BODY_LEFT + i * (col_w_r + col_gap)
                hue = str(rl.get("hue", "navy"))
                c = _hue_rgba(hue)
                parts.append(
                    f'<rect x="{cx0:.1f}" y="668" width="3" height="30" '
                    f'fill="{c}"/>'
                )
                title_txt = str(rl.get("title", ""))
                t_fs, t_out = _fit_snap(
                    title_txt, col_w_r - 14, 17.0, min_size=15.0)
                parts.append(
                    f'<text x="{cx0 + 10:.1f}" y="{GUIDE_TITLE_Y}" '
                    f'font-family="{FONT_SANS}" font-size="{t_fs:.1f}" '
                    f'font-weight="700" fill="{INK_COLOR}">{esc(t_out)}</text>'
                )
                body_lines: List[str] = list(rl.get("lines", []) or [])
                if body_lines:
                    first = body_lines[0]
                    f_fs, f_out = _fit_snap(
                        first, col_w_r - 14, 16.0, min_size=15.0)
                    if len(body_lines) >= 2:
                        second = body_lines[1]
                        s_fs, s_out = _fit_snap(
                            second, col_w_r - 14, 16.0, min_size=15.0)
                        parts.append(
                            f'<text x="{cx0 + 10:.1f}" y="{GUIDE_BODY_Y}" '
                            f'font-family="{FONT_SANS}" font-size="{f_fs:.1f}" '
                            f'fill="{INK_DIM}">{esc(f_out)}'
                            f'<tspan x="{cx0 + 10:.1f}" dy="12" '
                            f'font-size="{s_fs:.1f}">{esc(s_out)}</tspan>'
                            f'</text>'
                        )
                    else:
                        parts.append(
                            f'<text x="{cx0 + 10:.1f}" y="{GUIDE_BODY_Y}" '
                            f'font-family="{FONT_SANS}" font-size="{f_fs:.1f}" '
                            f'fill="{INK_DIM}">{esc(f_out)}</text>'
                        )

        # ─── footer hair + notes ───
        parts.append(
            f'<line x1="{BODY_LEFT}" y1="{FOOTER_HAIR_Y}" x2="{BODY_RIGHT}" '
            f'y2="{FOOTER_HAIR_Y}" stroke="{HAIR_LIGHT}" stroke-width="0.5"/>'
        )
        if notes:
            notes_max_w = BODY_WIDTH - 220
            if notes.lower().startswith("notes."):
                head = notes[:6]
                tail = notes[6:]
                _, tail_out = _fit_font_size(
                    tail, notes_max_w - 40, 16.0, min_size=15.0)
                parts.append(
                    f'<text x="{BODY_LEFT}" y="{FOOTER_TEXT_Y}" '
                    f'font-family="{FONT_SANS}" font-size="16" fill="{INK_DIM}">'
                    f'<tspan font-weight="700">{esc(head)}</tspan>'
                    f'{esc(tail_out)}</text>'
                )
            else:
                _, notes_out = _fit_font_size(
                    notes, notes_max_w, 16.0, min_size=15.0)
                parts.append(
                    f'<text x="{BODY_LEFT}" y="{FOOTER_TEXT_Y}" '
                    f'font-family="{FONT_SANS}" font-size="16" fill="{INK_DIM}">'
                    f'{esc(notes_out)}</text>'
                )
        if figure_tag:
            parts.append(
                f'<text x="{BODY_RIGHT}" y="{FOOTER_TEXT_Y}" text-anchor="end" '
                f'font-family="{FONT_SANS}" font-size="16" fill="{GRAY_COLOR}" '
                f'letter-spacing="0.5">{esc(figure_tag)}</text>'
            )

        parts.append('</svg>')
        return "".join(parts)


# ═════════════════════════════════════════════════════════════════
# module column emit
# ═════════════════════════════════════════════════════════════════
    finally:
        _MOD_L1.update(_ORIG_L1)
def _emit_module_column(
    parts: List[str],
    geom: Dict[str, float],
    node: Node,
) -> None:
    cx0 = geom["x"]
    cw = geom["w"]
    ex = getattr(node, "extra", {}) or {}
    hue = str(getattr(node, "group", "") or "navy")
    kind = str(ex.get("kind", "core"))
    c_full = _hue_rgba(hue, 1.0)
    c_hdr = _hue_rgba(hue, 0.97)

    # ── header slab (shadow + dark) ──
    parts.append(
        f'<rect x="{cx0 + 2:.1f}" y="{HEADER_TOP_Y + 2}" width="{cw:.1f}" '
        f'height="{HEADER_H}" fill="rgba(0,0,0,0.08)"/>'
    )
    parts.append(
        f'<rect x="{cx0:.1f}" y="{HEADER_TOP_Y}" width="{cw:.1f}" '
        f'height="{HEADER_H}" fill="{c_hdr}"/>'
    )
    parts.append(
        f'<rect x="{cx0 + 3:.1f}" y="{HEADER_TOP_Y + 3}" width="{cw - 6:.1f}" '
        f'height="{HEADER_H - 6}" fill="none" '
        f'stroke="rgba(247,240,226,0.35)" stroke-width="0.6"/>'
    )
    # code (left top)
    code_txt = str(ex.get("code", ""))
    parts.append(
        f'<text x="{cx0 + 12:.1f}" y="{HEADER_TOP_Y + 22}" '
        f'font-family="{FONT_SANS}" font-size="15" '
        f'fill="rgba(255,240,215,0.85)" font-weight="700" '
        f'letter-spacing="2">{esc(code_txt)}</text>'
    )
    # kind pill (right top) · R2b · narrow-col fix:
    #   ≥7 modules → cw < ~130 · use compact 2-3 char label so pill doesn't
    #   overlap the code text.  Wide columns keep full "CORE/ELECTIVE/CAPSTONE".
    kind_label_full = _KIND_LABEL.get(kind, kind.upper())
    _KIND_SHORT: Dict[str, str] = {
        "core":     "C",
        "elective": "EL",
        "capstone": "CAP",
    }
    if cw < 220:
        kind_label = _KIND_SHORT.get(kind, kind_label_full[:3])
    else:
        kind_label = kind_label_full
    if kind_label in {"C", "EL", "CAP"}:
        pill_w = {"C": 34, "EL": 38, "CAP": 48}.get(kind_label, 40)
    else:
        pill_w = max(48, len(kind_label) * 8 + 14)
    pill_x = cx0 + cw - pill_w - 6
    # guarantee pill left edge sits right of code_txt (code width ~ 44pt for "M0X")
    _code_right = cx0 + 12 + max(len(code_txt), 3) * 10 + 4
    if pill_x < _code_right:
        pill_x = _code_right
        pill_w = max(28, cx0 + cw - pill_x - 6)
    pill_y = HEADER_TOP_Y + 8
    pill_h = 24
    parts.append(
        f'<rect x="{pill_x:.1f}" y="{pill_y}" '
        f'width="{pill_w:.1f}" height="{pill_h}" '
        f'fill="none" stroke="rgba(255,240,215,0.7)" stroke-width="0.8"/>'
    )
    parts.append(
        f'<text x="{pill_x + pill_w / 2:.1f}" y="{HEADER_TOP_Y + 24}" '
        f'text-anchor="middle" font-family="{FONT_SANS}" font-size="15" '
        f'fill="rgba(247,240,226,1)" font-weight="700" '
        f'letter-spacing="1.0">{esc(kind_label)}</text>'
    )
    # title (serif)
    title_txt = str(getattr(node, "label", ""))
    title_fs, title_out = _fit_drop(
        title_txt, (cw - 24) * 0.68, 20.0, min_size=12.0,
        char_w_ratio=0.70,
    )
    parts.append(
        f'<text x="{cx0 + 12:.1f}" y="{HEADER_TOP_Y + 56}" '
        f'font-family="{FONT_SERIF}" font-size="{title_fs:.1f}" '
        f'fill="rgba(247,240,226,1)" font-weight="700">{esc(title_out)}</text>'
    )
    # subtitle (italic serif)
    sub_txt = str(ex.get("subtitle", ""))
    if sub_txt:
        _, sub_out = _fit_font_size(sub_txt, cw - 24, 15.0, min_size=15.0)
        parts.append(
            f'<text x="{cx0 + 12:.1f}" y="{HEADER_TOP_Y + 70}" '
            f'font-family="{FONT_SERIF}" font-size="15" '
            f'fill="rgba(255,240,215,0.80)" font-style="italic">'
            f'{esc(sub_out)}</text>'
        )

    # ── body card ──
    parts.append(
        f'<rect x="{cx0:.1f}" y="{BODY_CARD_TOP_Y}" width="{cw:.1f}" '
        f'height="{BODY_CARD_H}" fill="{PARCHMENT}" '
        f'stroke="{_hue_rgba(hue, 0.6)}" stroke-width="1.1"/>'
    )
    parts.append(
        f'<rect x="{cx0:.1f}" y="{BODY_CARD_TOP_Y}" width="4" '
        f'height="{BODY_CARD_H}" fill="{_hue_rgba(hue, 0.9)}"/>'
    )

    inner_x = cx0 + 16
    inner_right = cx0 + cw - 10
    inner_w = inner_right - inner_x
    text_w = max(28.0, inner_w * 0.66)
    label_fs = 14.0 if inner_w < 150 else 15.0
    label_tracking = 0.8 if inner_w < 150 else 1.2
    topics = list(ex.get("topics", []) or [])
    max_topics_visible = 2
    topics_visible = topics[:max_topics_visible]
    topics_rows = max(1, len(topics_visible))

    # ── section layout · self-adapts to the visible topic rows ──
    Y_DUR_LABEL = BODY_CARD_TOP_Y + 18      # 358 (kicker top row)
    Y_DUR_VAL = BODY_CARD_TOP_Y + 40        # 380 (value below kicker)
    Y_DUR_HAIR = BODY_CARD_TOP_Y + 50       # 390
    Y_TOPICS_LABEL = BODY_CARD_TOP_Y + 66   # 406
    Y_TOPICS_FIRST = BODY_CARD_TOP_Y + 84   # 424
    Y_ASSESS_HAIR = Y_TOPICS_FIRST + topics_rows * 20 + 2
    Y_ASSESS_LABEL = Y_ASSESS_HAIR + 16
    Y_ASSESS_TITLE = Y_ASSESS_HAIR + 34
    Y_ASSESS_NOTE = Y_ASSESS_HAIR + 50
    Y_PREREQ_HAIR = Y_ASSESS_HAIR + 62
    Y_PREREQ_LABEL = Y_ASSESS_HAIR + 78
    Y_PREREQ_TXT = Y_ASSESS_HAIR + 94
    Y_PREREQ_NOTE = Y_ASSESS_HAIR + 110
    Y_WEIGHT_HAIR = Y_ASSESS_HAIR + 122
    Y_WEIGHT_LABEL = Y_ASSESS_HAIR + 138
    Y_WEIGHT_BAR = Y_ASSESS_HAIR + 148

    # ── DURATION row · R2b · 2-row (kicker top, value below) to avoid
    # "DURATIO16h" collision on narrow columns (cw<140) ──
    dur_label = _section_label("DURATION", inner_w)
    parts.append(
        f'<text x="{inner_x:.1f}" y="{Y_DUR_LABEL}" '
        f'font-family="{FONT_SANS}" font-size="{label_fs:.1f}" fill="{GRAY_COLOR}" '
        f'font-weight="700" letter-spacing="{label_tracking:.1f}">{esc(dur_label)}</text>'
    )
    dur_txt = str(ex.get("duration", ""))
    dur_fs, dur_out = _fit_drop(
        dur_txt, text_w, 17.0, min_size=11.0, char_w_ratio=0.66)
    parts.append(
        f'<text x="{inner_x:.1f}" y="{Y_DUR_VAL}" '
        f'font-family="{FONT_SERIF}" font-size="{dur_fs:.1f}" fill="{INK_COLOR}" '
        f'font-weight="700">{esc(dur_out)}</text>'
    )
    parts.append(
        f'<line x1="{inner_x:.1f}" y1="{Y_DUR_HAIR}" '
        f'x2="{inner_right:.1f}" y2="{Y_DUR_HAIR}" '
        f'stroke="{_hue_rgba(hue, 0.25)}" stroke-width="0.6"/>'
    )

    # ── TOPICS section ──
    parts.append(
        f'<text x="{inner_x:.1f}" y="{Y_TOPICS_LABEL}" '
        f'font-family="{FONT_SANS}" font-size="{label_fs:.1f}" fill="{GRAY_COLOR}" '
        f'font-weight="700" letter-spacing="{label_tracking:.1f}">TOPICS</text>'
    )
    for j, tp in enumerate(topics_visible):
        ty = Y_TOPICS_FIRST + j * 20
        parts.append(
            f'<circle cx="{inner_x - 8:.1f}" cy="{ty - 5}" r="2.4" '
            f'fill="{c_full}"/>'
        )
        tp_fs, tp_out = _fit_drop(
            tp, text_w, 13.0, min_size=10.0, char_w_ratio=0.66)
        parts.append(
            f'<text x="{inner_x:.1f}" y="{ty:.1f}" '
            f'font-family="{FONT_SANS}" font-size="{tp_fs:.1f}" '
            f'fill="{INK_COLOR}">{esc(tp_out)}</text>'
        )

    # ── ASSESSMENT ──
    parts.append(
        f'<line x1="{inner_x:.1f}" y1="{Y_ASSESS_HAIR}" '
        f'x2="{inner_right:.1f}" y2="{Y_ASSESS_HAIR}" '
        f'stroke="{_hue_rgba(hue, 0.25)}" stroke-width="0.6"/>'
    )
    parts.append(
        f'<text x="{inner_x:.1f}" y="{Y_ASSESS_LABEL}" '
        f'font-family="{FONT_SANS}" font-size="{label_fs:.1f}" fill="{GRAY_COLOR}" '
        f'font-weight="700" letter-spacing="{label_tracking:.1f}">'
        f'{esc(_section_label("ASSESSMENT", inner_w))}</text>'
    )
    assess = str(ex.get("assessment", ""))
    a_fs, a_out = _fit_drop(
        assess, text_w, 15.0, min_size=10.0, char_w_ratio=0.66)
    parts.append(
        f'<text x="{inner_x:.1f}" y="{Y_ASSESS_TITLE}" '
        f'font-family="{FONT_SERIF}" font-size="{a_fs:.1f}" '
        f'fill="{INK_COLOR}" font-weight="700">{esc(a_out)}</text>'
    )
    a_note = str(ex.get("assessment_note", ""))
    if a_note:
        n_fs, n_out = _fit_drop(
            a_note, text_w, 12.0, min_size=10.0, char_w_ratio=0.66)
        parts.append(
            f'<text x="{inner_x:.1f}" y="{Y_ASSESS_NOTE}" '
            f'font-family="{FONT_SANS}" font-size="{n_fs:.1f}" fill="{GRAY_COLOR}" '
            f'font-style="italic">{esc(n_out)}</text>'
        )

    # ── PREREQ ──
    parts.append(
        f'<line x1="{inner_x:.1f}" y1="{Y_PREREQ_HAIR}" '
        f'x2="{inner_right:.1f}" y2="{Y_PREREQ_HAIR}" '
        f'stroke="{_hue_rgba(hue, 0.25)}" stroke-width="0.6"/>'
    )
    parts.append(
        f'<text x="{inner_x:.1f}" y="{Y_PREREQ_LABEL}" '
        f'font-family="{FONT_SANS}" font-size="{label_fs:.1f}" fill="{GRAY_COLOR}" '
        f'font-weight="700" letter-spacing="{label_tracking:.1f}">PREREQ</text>'
    )
    prereq = str(ex.get("prereq", "— none —"))
    pr_fs, pr_out = _fit_drop(
        prereq, text_w, 13.0, min_size=10.0, char_w_ratio=0.66)
    parts.append(
        f'<text x="{inner_x:.1f}" y="{Y_PREREQ_TXT}" '
        f'font-family="{FONT_SANS}" font-size="{pr_fs:.1f}" fill="{INK_COLOR}">'
        f'{esc(pr_out)}</text>'
    )
    pr_note = str(ex.get("prereq_note", ""))
    if pr_note:
        pn_fs, pn_out = _fit_drop(
            pr_note, text_w, 12.0, min_size=10.0, char_w_ratio=0.66)
        parts.append(
            f'<text x="{inner_x:.1f}" y="{Y_PREREQ_NOTE}" '
            f'font-family="{FONT_SANS}" font-size="{pn_fs:.1f}" fill="{GRAY_COLOR}" '
            f'font-style="italic">{esc(pn_out)}</text>'
        )

    # ── CREDIT WEIGHT ──
    parts.append(
        f'<line x1="{inner_x:.1f}" y1="{Y_WEIGHT_HAIR}" '
        f'x2="{inner_right:.1f}" y2="{Y_WEIGHT_HAIR}" '
        f'stroke="{_hue_rgba(hue, 0.25)}" stroke-width="0.6"/>'
    )
    parts.append(
        f'<text x="{inner_x:.1f}" y="{Y_WEIGHT_LABEL}" '
        f'font-family="{FONT_SANS}" font-size="{label_fs:.1f}" fill="{GRAY_COLOR}" '
        f'font-weight="700" letter-spacing="{label_tracking:.1f}">'
        f'{esc(_section_label("CREDIT WEIGHT", inner_w))}</text>'
    )
    weight = max(0.0, min(1.0, float(ex.get("weight", 0.5))))
    bar_w = inner_w
    parts.append(
        f'<rect x="{inner_x:.1f}" y="{Y_WEIGHT_BAR}" width="{bar_w:.1f}" '
        f'height="8" fill="{_hue_rgba(hue, 0.15)}"/>'
    )
    parts.append(
        f'<rect x="{inner_x:.1f}" y="{Y_WEIGHT_BAR}" '
        f'width="{bar_w * weight:.1f}" '
        f'height="8" fill="{_hue_rgba(hue, 0.85)}"/>'
    )


# ═════════════════════════════════════════════════════════════════
# sidebar emit
# ═════════════════════════════════════════════════════════════════

def _emit_sidebar(
    parts: List[str],
    outcomes: List[Dict[str, str]],
    stats: List[Dict[str, str]],
    modules: List[Node],
    show_kind_mix: bool = False,
) -> None:
    # ── KIND MIX (default off · R2 · 冗余于 column header 色带 + KPI note) ──
    kind_y = SIDEBAR_TOP_Y + 18
    if show_kind_mix:
        parts.append(
            f'<text x="{SIDEBAR_X}" y="{SIDEBAR_TOP_Y}" '
            f'font-family="{FONT_SANS}" font-size="16" fill="{GRAY_COLOR}" '
            f'font-weight="700" letter-spacing="1.4">KIND MIX</text>'
        )
        parts.append(
            f'<line x1="{SIDEBAR_X}" y1="{SIDEBAR_TOP_Y + 8}" '
            f'x2="{SIDEBAR_RIGHT}" y2="{SIDEBAR_TOP_Y + 8}" '
            f'stroke="{HAIR_COLOR}" stroke-width="0.6"/>'
        )

        # count per kind
        counts: Dict[str, int] = {}
        kind_modules: Dict[str, List[str]] = {}
        for n in modules:
            ex = getattr(n, "extra", {}) or {}
            k = str(ex.get("kind", "core"))
            counts[k] = counts.get(k, 0) + 1
            kind_modules.setdefault(k, []).append(str(ex.get("code", "")))

        # order: core / elective / capstone / other
        kind_order = [k for k in ("core", "elective", "capstone")
                      if k in counts]
        for k in counts:
            if k not in kind_order:
                kind_order.append(k)
        for k in kind_order:
            n_ct = counts[k]
            hue = _KIND_HUE.get(k, "navy")
            c = _hue_rgba(hue)
            parts.append(
                f'<rect x="{SIDEBAR_X}" y="{kind_y}" width="4" height="30" '
                f'fill="{c}"/>'
            )
            parts.append(
                f'<text x="{SIDEBAR_X + 12}" y="{kind_y + 14}" '
                f'font-family="{FONT_SANS}" font-size="18" fill="{INK_COLOR}" '
                f'font-weight="700" letter-spacing="1.2">'
                f'{esc(_KIND_LABEL.get(k, k.upper()))}</text>'
            )
            codes = " · ".join(kind_modules.get(k, [])[:4])
            _, codes_out = _fit_font_size(codes, 180, 16.0, min_size=15.0)
            parts.append(
                f'<text x="{SIDEBAR_X + 12}" y="{kind_y + 26}" '
                f'font-family="{FONT_SANS}" font-size="16" fill="{GRAY_COLOR}">'
                f'{esc(codes_out)}</text>'
            )
            # count on right
            parts.append(
                f'<text x="{SIDEBAR_RIGHT}" y="{kind_y + 14}" text-anchor="end" '
                f'font-family="{FONT_SERIF}" font-size="28" fill="{c}" '
                f'font-weight="700">{n_ct}</text>'
            )
            label = "module" if n_ct == 1 else "modules"
            parts.append(
                f'<text x="{SIDEBAR_RIGHT}" y="{kind_y + 26}" text-anchor="end" '
                f'font-family="{FONT_SANS}" font-size="16" fill="{GRAY_COLOR}">'
                f'{label}</text>'
            )
            kind_y += 38

    # ── LEARNING OUTCOMES ──
    lo_top_y = kind_y + 6 if show_kind_mix else SIDEBAR_TOP_Y
    if outcomes:
        parts.append(
            f'<text x="{SIDEBAR_X}" y="{lo_top_y}" '
            f'font-family="{FONT_SANS}" font-size="16" fill="{GRAY_COLOR}" '
            f'font-weight="700" letter-spacing="1.4">LEARNING OUTCOMES</text>'
        )
        parts.append(
            f'<line x1="{SIDEBAR_X}" y1="{lo_top_y + 8}" '
            f'x2="{SIDEBAR_RIGHT}" y2="{lo_top_y + 8}" '
            f'stroke="{HAIR_COLOR}" stroke-width="0.6"/>'
        )
        # each outcome ~ 54px stack · R2b · widened wrap width + realistic char_w
        # sidebar spans SIDEBAR_X..SIDEBAR_RIGHT (252pt); allow 244pt text width
        # so 16pt body fits without hitting slide chrome edge.
        oy = lo_top_y + 26
        max_outcomes = 4
        _sidebar_txt_w = SIDEBAR_RIGHT - SIDEBAR_X - 8  # 244
        for i, oc in enumerate(outcomes[:max_outcomes]):
            code = str(oc.get("code", f"LO{i + 1}"))
            title = str(oc.get("title", ""))
            body = str(oc.get("body", ""))
            # header line: "LO1 · title"
            head_txt = f"{code} · {title}" if title else code
            h_fs, h_out = _fit_snap(
                head_txt, _sidebar_txt_w, 18.0, min_size=15.0)
            parts.append(
                f'<text x="{SIDEBAR_X}" y="{oy:.1f}" '
                f'font-family="{FONT_SERIF}" font-size="{h_fs:.1f}" '
                f'fill="{INK_COLOR}" font-weight="700">{esc(h_out)}</text>'
            )
            # body wrap 2 lines · char_w tuned to actually fit 16pt latin+cjk
            body_lines = _wrap_text_2line(body, _sidebar_txt_w, char_w=7.2)
            for j, bl in enumerate(body_lines[:2]):
                parts.append(
                    f'<text x="{SIDEBAR_X}" y="{oy + 15 + j * 14:.1f}" '
                    f'font-family="{FONT_SANS}" font-size="16" '
                    f'fill="{INK_DIM}">{esc(bl)}</text>'
                )
            oy += 54

    # ── sidebar footer stats · R2b · pushed down for clearance vs LO stack
    # and to align near module body bottom (y=636) ──
    stats_top_y = 590
    if stats:
        parts.append(
            f'<line x1="{SIDEBAR_X}" y1="{stats_top_y}" '
            f'x2="{SIDEBAR_RIGHT}" y2="{stats_top_y}" '
            f'stroke="{HAIR_LIGHT}" stroke-width="0.5"/>'
        )
        sy = stats_top_y + 14
        for st in stats[:3]:
            lbl = str(st.get("label", ""))
            val = str(st.get("value", ""))
            parts.append(
                f'<text x="{SIDEBAR_X}" y="{sy}" '
                f'font-family="{FONT_SANS}" font-size="15" fill="{GRAY_COLOR}" '
                f'font-weight="700" letter-spacing="1">{esc(lbl)}</text>'
            )
            v_fs, v_out = _fit_snap(val, 130, 20.0, min_size=17.0)
            parts.append(
                f'<text x="{SIDEBAR_RIGHT}" y="{sy}" text-anchor="end" '
                f'font-family="{FONT_SERIF}" font-size="{v_fs:.1f}" '
                f'fill="{INK_COLOR}" font-weight="700">{esc(v_out)}</text>'
            )
            sy += 16


__all__ = [
    "BASELINE_MODULES", "BASELINE_KPIS", "BASELINE_WEEK_TICKS",
    "BASELINE_MILESTONES", "BASELINE_OUTCOMES", "BASELINE_SIDEBAR_STATS",
    "BASELINE_READ_LINES", "BASELINE_NOTES",
    "build_curriculum_data", "build_curriculum_tree",
    "HERO_CU2_DATA",
    "_DANDELION_HUE",
    "render_hero_embed_cu2_curriculum_v2",
]
