#!/usr/bin/env python3
"""Regenerate the 4 PY_pmf variants into step2_codified.

Variants:
  - baseline:             5 tiers (Olsen 2015)                      · sidebar + ladder + KPI
  - dense_6tier:          6 tiers · adds MARKETING layer            · sidebar + ladder + KPI
  - sparse_3tier:         3 tiers · CUSTOMER / NEEDS / VALUE        · sidebar + ladder + KPI
  - minimal_no_sidebar:   4 tiers · sidebar OFF · KPI stripped      · ladder + minimal

修的 bug (step-3 严审):
  - baseline: L2 detail shortened ("Kano · must / perf / delight") to fit ≥10pt · L3 detail
    shortened ("why we win on the needs above") · body font_size min raised 9.0 → 10.0
    · kicker / SOURCE / HOW-TO-READ eyebrow bumped 9 → 10 (清 grep -c 'font-size="9\\.'=0)
  - dense_6tier: how_to_read legend rewritten "L1 → L6 · 上三 market, 下三 product"
    · CUSTOMER sidebar description trimmed to fit ≥10pt
    · subtitle rewritten as 6-tier
  - sparse_3tier: how_to_read + subtitle rewritten as 3-tier · L3 VALUE hue = magenta (plum)
    以避免任何 sage/green 误映射
  - minimal_no_sidebar: how_to_read + subtitle rewritten as 4-tier

修的 bug (step-3b 严审 · codifier 造假被抓包):
  - KPI kicker font 8.5 → 10 (baseline / dense / sparse; minimal 无 KPI 不受影响)
  - Axis MARKET / PRODUCT(UX) label font 8 → 10 (all)
  - MARKET / PRODUCT dashed divider label font 8.5 → 10 (all)
  - _fit_font_size min_size 8.0 → 10.0 for tier sub-titles (保险)
  - Post-fix grep: 4 张 SVG 全部 '…'=0 · font-size="9.x"=0 · font-size="9"=0
    · font-size="8.x"=0 · font-size="8"=0
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from svg_relation_lib.presets.hero_embed_02_PY_pmf_v2 import (  # noqa: E402
    render_hero_embed_py_pmf_v2,
    build_pmf_data,
)


OUT_DIR = os.path.abspath(os.path.join(
    HERE, "..", "final_svg_relation", "02_PY_pmf", "step2_codified",
))


# ═════════════════════════════════════════════════════════════════
# BASELINE · 5 tiers (uses in-preset BASELINE_*)
# ═════════════════════════════════════════════════════════════════

def render_baseline() -> str:
    data = build_pmf_data()
    return render_hero_embed_py_pmf_v2(data=data)


# ═════════════════════════════════════════════════════════════════
# DENSE 6-TIER · adds a MARKETING / DISTRIBUTION layer as L4
#   L1 CUSTOMER   → market
#   L2 NEEDS      → market
#   L3 VALUE      → market
#   L4 MARKETING  → product (distribution stack)
#   L5 FEATURE    → product
#   L6 UX         → product
#   market_tier_count = 3
# ═════════════════════════════════════════════════════════════════

DENSE_TIERS = [
    (
        "CUSTOMER", "who we serve", "",
        "rust", "WHO", "the target",
        "personas · JTBD · segments · TAM",
        "\"mid-market SaaS PMs\"",
    ),
    (
        "UNDERSERVED NEEDS", "why they hurt today",
        "Kano · must / perf / delight",
        "cinnamon", "WHAT PAIN", "the gap",
        "jobs · pains · gains · importance × sat.",
        "\"analytics in < 1 day\"",
    ),
    (
        "VALUE PROPOSITION", "the promise that wins",
        "why we win on the needs above",
        "magenta", "WHY US", "the promise",
        "positioning · differentiators · why now",
        "\"insight in hours, not quarters\"",
    ),
    (
        "MARKETING", "how we reach them",
        "channel mix · positioning claims",
        "olive", "HOW REACH", "the funnel",
        "channel · message · attribution",
        "\"PLG + community + partner-led\"",
    ),
    (
        "FEATURE SET", "what we build",
        "MoSCoW · MVP → v1 · tied to needs",
        "blue", "WHAT BUILD", "the scope",
        "MVP scope · MoSCoW · epics · rollout",
        "\"auto-instrument SDK + funnels\"",
    ),
    (
        "USER EXPERIENCE", "where fit is felt",
        "flows · IA · visual · latency · onboarding",
        "green", "HOW FEELS", "the surface",
        "flows · IA · latency budget · a11y",
        "\"time-to-first-insight < 5 min\"",
    ),
]

DENSE_KPIS = [
    {"kicker": "TIERS",             "value": "6",         "note": "extended Olsen",     "hue": "rust"},
    {"kicker": "MARKET LAYERS",     "value": "3 / 6",     "note": "customer · needs · value","hue": "magenta"},
    {"kicker": "PRODUCT LAYERS",    "value": "3 / 6",     "note": "GTM · feature · UX", "hue": "blue"},
    {"kicker": "CURRENT FIT SCORE", "value": "62 / 100",  "note": "Sean Ellis test",    "hue": "green"},
]

DENSE_SIGNALS = [
    {"label": "Sean Ellis · very disappointed",  "value_pct": 0.62, "value_label": "62%",     "hue": "rust"},
    {"label": "NPS · promoters − detractors",    "value_pct": 0.44, "value_label": "+44",     "hue": "cinnamon"},
    {"label": "Retention · D30 active",          "value_pct": 0.49, "value_label": "49%",     "hue": "blue"},
    {"label": "Time-to-first-insight",           "value_pct": 0.80, "value_label": "4.2 min", "hue": "green"},
]

DENSE_HOW_TO_READ = (
    "L1 → L6 · 上三 market (客户 · 需求 · 价值), 下三 product (GTM · 特性 · UX) · 每层解释下一层为什么存在",
    "宽度 = 抽象度收缩 (顶层最抽象 · 底层最具体) · 色相 = 各层职能 · 虚线 = market / product 分界",
)


def render_dense_6tier() -> str:
    data = build_pmf_data(
        tiers=DENSE_TIERS,
        kicker="§ PMF · PRODUCT-MARKET-FIT · EXTENDED 6-TIER CUT",
        figure_title="PMF 金字塔 · 6 层扩展 · 加入 marketing / distribution 层",
        figure_caption=(
            "Dan Olsen · Lean Product Playbook (extended) · 6 tiers · "
            "客户 → 需求 → 价值 → 营销 → 特性 → UX · 上三 market, 下三 product"
        ),
        source="Dan Olsen · Lean Product Playbook 2015 · extended 6-tier cut · GTM layer inserted between value & feature",
        kpis=DENSE_KPIS,
        fit_signals=DENSE_SIGNALS,
        market_tier_count=3,
        how_to_read=DENSE_HOW_TO_READ,
        figure_footer_tag="figure 02 · PY · pmf pyramid · dense 6-tier",
    )
    return render_hero_embed_py_pmf_v2(data=data)


# ═════════════════════════════════════════════════════════════════
# SPARSE 3-TIER · CUSTOMER / NEEDS / VALUE only
#   L1 CUSTOMER  → market
#   L2 NEEDS     → market
#   L3 VALUE     → product · hue = magenta (plum) ⚠︎ 不 sage
#   market_tier_count = 2
# ═════════════════════════════════════════════════════════════════

SPARSE_TIERS = [
    (
        "CUSTOMER", "who we serve", "",
        "rust", "WHO", "the target",
        "personas · JTBD · segments · TAM",
        "\"mid-market SaaS PMs\"",
    ),
    (
        "UNDERSERVED NEEDS", "why they hurt today",
        "Kano · must / perf / delight",
        "cinnamon", "WHAT PAIN", "the gap",
        "jobs · pains · gains · imp × sat.",
        "\"analytics in < 1 day\"",
    ),
    (
        "VALUE PROPOSITION", "the promise that wins",
        "why we win on the needs above",
        "magenta", "WHY US", "the promise",  # ⚠︎ hue = magenta = plum
        "positioning · differentiators · why now",
        "\"insight in hours, not quarters\"",
    ),
]

SPARSE_KPIS = [
    {"kicker": "TIERS",             "value": "3",         "note": "problem-space cut",  "hue": "rust"},
    {"kicker": "MARKET LAYERS",     "value": "2 / 3",     "note": "customer · needs",   "hue": "cinnamon"},
    {"kicker": "PRODUCT LAYERS",    "value": "1 / 3",     "note": "value only",         "hue": "magenta"},
    {"kicker": "CURRENT FIT SCORE", "value": "58 / 100",  "note": "Sean Ellis test",    "hue": "green"},
]

SPARSE_SIGNALS = [
    {"label": "Sean Ellis · very disappointed", "value_pct": 0.58, "value_label": "58%",     "hue": "rust"},
    {"label": "NPS · promoters − detractors",   "value_pct": 0.38, "value_label": "+38",     "hue": "cinnamon"},
    {"label": "Willingness to pay (survey)",    "value_pct": 0.72, "value_label": "72%",     "hue": "magenta"},
]

SPARSE_HOW_TO_READ = (
    "L1 → L3 · 上二 market (客户 · 需求), 下一 product (价值主张) · 每层解释下一层为什么存在",
    "宽度 = 抽象度收缩 (顶层最抽象 · 底层最具体) · 色相 = 各层职能 · 虚线 = market / product 分界",
)


def render_sparse_3tier() -> str:
    data = build_pmf_data(
        tiers=SPARSE_TIERS,
        kicker="§ PMF · PRODUCT-MARKET-FIT · PROBLEM-SPACE 3-TIER CUT",
        figure_title="PMF 金字塔 · 3 层精简 · 只画 problem-space",
        figure_caption=(
            "Dan Olsen · Lean Product Playbook · 3 tiers · "
            "客户 → 未满足需求 → 价值主张 · 聚焦 problem-space discovery"
        ),
        source="Dan Olsen · The Lean Product Playbook 2015 · 3-tier problem-space cut · pre-solution phase",
        kpis=SPARSE_KPIS,
        fit_signals=SPARSE_SIGNALS,
        market_tier_count=2,
        how_to_read=SPARSE_HOW_TO_READ,
        figure_footer_tag="figure 02 · PY · pmf pyramid · sparse 3-tier",
    )
    return render_hero_embed_py_pmf_v2(data=data)


# ═════════════════════════════════════════════════════════════════
# MINIMAL_NO_SIDEBAR · 4 tiers · sidebar OFF · KPIs stripped
#   L1 CUSTOMER  → market
#   L2 NEEDS     → market
#   L3 VALUE     → product · magenta
#   L4 FEATURE   → product · blue
#   market_tier_count = 2
# ═════════════════════════════════════════════════════════════════

MINIMAL_TIERS = [
    (
        "CUSTOMER", "who we serve", "",
        "rust", "WHO", "the target",
        "", "",
    ),
    (
        "UNDERSERVED NEEDS", "why they hurt today",
        "Kano · must / perf / delight",
        "cinnamon", "WHAT PAIN", "the gap",
        "", "",
    ),
    (
        "VALUE PROPOSITION", "the promise that wins",
        "why we win on the needs above",
        "magenta", "WHY US", "the promise",
        "", "",
    ),
    (
        "FEATURE SET", "what we build",
        "MoSCoW · MVP → v1 · tied to needs",
        "blue", "WHAT BUILD", "the scope",
        "", "",
    ),
]

MINIMAL_HOW_TO_READ = (
    "L1 → L4 · 上二 market (客户 · 需求), 下二 product (价值 · 特性) · 每层解释下一层为什么存在",
    "宽度 = 抽象度收缩 · 色相 = 各层职能 · 虚线 = market / product 分界 · 无 sidebar, 聚焦骨架",
)


def render_minimal_no_sidebar() -> str:
    data = build_pmf_data(
        tiers=MINIMAL_TIERS,
        kicker="§ PMF · PRODUCT-MARKET-FIT · MINIMAL 4-TIER CUT",
        figure_title="PMF 金字塔 · 4 层最小骨架 · 无 sidebar · 无 KPI",
        figure_caption=(
            "Dan Olsen · Lean Product Playbook · 4 tiers · "
            "客户 → 需求 → 价值 → 特性 · 骨架版, 用于一次性单页"
        ),
        source="Dan Olsen · The Lean Product Playbook 2015 · 4-tier stripped cut · one-shot deck",
        kpis=[],
        fit_signals=[],
        market_tier_count=2,
        how_to_read=MINIMAL_HOW_TO_READ,
        show_sidebar=False,
        figure_footer_tag="figure 02 · PY · pmf pyramid · minimal no-sidebar",
    )
    return render_hero_embed_py_pmf_v2(data=data)


# ═════════════════════════════════════════════════════════════════
# entry
# ═════════════════════════════════════════════════════════════════

def _write(name: str, svg: str) -> None:
    out_path = os.path.join(OUT_DIR, name)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"wrote {out_path}  ({len(svg):,} bytes)")


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    _write("baseline.svg",           render_baseline())
    _write("dense_6tier.svg",        render_dense_6tier())
    _write("sparse_3tier.svg",       render_sparse_3tier())
    _write("minimal_no_sidebar.svg", render_minimal_no_sidebar())


if __name__ == "__main__":
    main()
