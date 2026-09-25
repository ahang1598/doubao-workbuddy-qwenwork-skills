"""Render 4 BL_bloom hero-embed SVGs · baseline + 3 test variants.

Emits to final_svg_relation/03_BL_bloom/step2_codified/. Used by the step-3f
re-audit to verify the callout font-size ≥ 10pt hard red line, subtitle-vs-
title deduplication, and test3 empty-band fix.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# put scripts/ on path so svg_relation_lib imports work
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from svg_relation_lib.presets.hero_embed_03_BL_bloom_v2 import (
    build_bloom_tree,
    render_hero_embed_bl_bloom_v2,
)


OUT_DIR = _HERE.parent / "final_svg_relation" / "03_BL_bloom" / "step2_codified"


def _write(name: str, svg: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / name).write_text(svg, encoding="utf-8")
    print(f"wrote {OUT_DIR / name}")


# ═══════════════════════════════════════════════════════════════════
# baseline · full 6-tier Bloom (uses HERO_BL_DATA default)
# ═══════════════════════════════════════════════════════════════════
def render_baseline() -> str:
    tree = build_bloom_tree()  # defaults · BASELINE_TIERS
    return render_hero_embed_bl_bloom_v2(tree)


# ═══════════════════════════════════════════════════════════════════
# test1 · 4-tier SRE Maturity Ladder · noCN · mid-count
# ═══════════════════════════════════════════════════════════════════
def render_test1() -> str:
    tiers = [
        ("",  "OBSERVE",  "monitor · watch · sample",       "SRE dashboards · SLO burn",   "blue",   92.0),
        ("",  "ALERT",    "notify · escalate · route",      "PagerDuty · incident triage", "green",  80.0),
        ("",  "MITIGATE", "throttle · degrade · rollback",  "auto-rollback · blast radius","orange", 62.0),
        ("",  "LEARN",    "postmortem · encode · share",    "blameless RCA · runbook diff","magenta",40.0),
    ]
    kpis = [
        {"kicker": "TIERS",   "value": "4",       "note": "SRE quartet",             "hue": "blue"},
        {"kicker": "SPAN",    "value": "L1 → L4", "note": "extended SRE ladder",     "hue": "green"},
        {"kicker": "COHORT",  "value": "n = 24",  "note": "perception → prevention", "hue": "orange"},
        {"kicker": "AVG MASTERY","value": "68%",  "note": "across L1–L4",            "hue": "magenta"},
    ]
    tree = build_bloom_tree(
        tiers=tiers,
        kicker="§ BLOOM · SRE MATURITY LADDER · 2026 Q3",
        figure_title="SRE Maturity Ladder · 4 层能力体系",
        # subtitle differs from title · describes what the visual encodes
        figure_caption=(
            "从 observe → alert → mitigate → learn · SRE cohort n=24 · "
            "L3→L4 断层 22pt · post-mitigation 学习环节最薄弱"
        ),
        source="L&D curriculum · Sept 2026 · SRE cohort n=24",
        reading="从底 L1 观测 → 顶 L4 学习 · 每上一层认知复杂度递增",
        fig_ref="figure 03 · BL · bloom pyramid · test1 · 4tier noCN",
        kpis=kpis,
        axis_top_tag="LEARN",
        axis_bot_tag="OBSERVE",
    )
    return render_hero_embed_bl_bloom_v2(tree)


# ═══════════════════════════════════════════════════════════════════
# test2 · 7-tier dense (extended cognitive ladder)
# ═══════════════════════════════════════════════════════════════════
def render_test2() -> str:
    tiers = [
        ("感知", "PERCEIVE",   "notice · observe · scan",       "grafana signal spotting",    "blue",    100.0),
        ("识别", "RECOGNIZE",  "classify · match · label",      "err pattern taxonomy",       "green",    92.0),
        ("拆解", "DECOMPOSE",  "split · isolate · reduce",      "flamegraph drill-down",      "gold_p",   85.0),
        ("推理", "REASON",     "infer · relate · connect",      "N+1 query hypothesis",       "orange",   72.0),
        ("评价", "EVALUATE",   "critique · rank · defend",      "canary vs blue-green",       "cinnamon", 60.0),
        ("设计", "DESIGN",     "compose · model · specify",     "backpressure protocol",      "magenta",  46.0),
        ("创造", "CREATE",     "invent · originate · publish",  "novel replay algorithm",     "olive",    28.0),
    ]
    kpis = [
        {"kicker": "TIERS",   "value": "7",       "note": "extended taxonomy",   "hue": "blue"},
        {"kicker": "SPAN",    "value": "L1 → L7", "note": "perceive → create",   "hue": "green"},
        {"kicker": "COHORT",  "value": "n = 60",  "note": "senior engineers",    "hue": "orange"},
        {"kicker": "AVG MASTERY","value": "69%",  "note": "across L1–L7",        "hue": "magenta"},
    ]
    tree = build_bloom_tree(
        tiers=tiers,
        kicker="§ BLOOM · EXTENDED COGNITIVE LADDER · 7 TIER",
        figure_title="扩展认知阶梯 · 7 层任务网 (dense)",
        figure_caption=(
            "在 Anderson 六层之外补 perceive / design · 高层任务人数下降更快 · "
            "L6→L7 断层 18pt · design → create 是稀缺跳跃"
        ),
        source=("L&D curriculum · Sept 2026 · cohort n=48 · "
                "quarterly assessment · Anderson 2001 revised taxonomy"),
        reading=('从底 L1 记忆 → 顶 L6 创造 · 每上一层认知复杂度递增 · '
                 '宽度收敛象征"能独立完成的人越来越少"'),
        fig_ref="figure 03 · BL · bloom pyramid · test2 · 7tier dense",
        kpis=kpis,
        axis_top_tag="CREATE",
        axis_bot_tag="PERCEIVE",
    )
    return render_hero_embed_bl_bloom_v2(tree)


# ═══════════════════════════════════════════════════════════════════
# test3 · 6-tier minimal (no KPI band, no examples, no pct)
# ═══════════════════════════════════════════════════════════════════
def render_test3() -> str:
    tiers = [
        ("", "SPOT",         "notice · flag",           "", "blue"),
        ("", "TRIAGE",       "classify · scope",        "", "green"),
        ("", "MITIGATE",     "throttle · rollback",     "", "gold_p"),
        ("", "INVESTIGATE",  "flamegraph · timeline",   "", "orange"),
        ("", "RESOLVE",      "patch · verify",          "", "magenta"),
        ("", "LEARN",        "postmortem · share",      "", "olive"),
    ]
    tree = build_bloom_tree(
        tiers=tiers,
        kicker="§ BLOOM · SRE MINIMAL LADDER · 2026",
        figure_title="SRE Minimal Ladder · 6 步简化模式",
        figure_caption=(
            "去掉 mastery 数据 · 只留每层认知动作 · Spot → Triage → Mitigate → "
            "Investigate → Resolve → Learn · 学习闭环"
        ),
        source="L&D curriculum · Sept 2026 · SRE minimal ladder",
        reading="6 步简化 · Spot → Learn · 无 mastery 数据",
        fig_ref="figure 03 · BL · bloom pyramid · test3 · 6tier minimal",
        kpis=[],  # minimal · no KPI band
        callout={"enabled": False},
        axis_top_tag="LEARN",
        axis_bot_tag="SPOT",
    )
    return render_hero_embed_bl_bloom_v2(tree)


def main() -> None:
    _write("baseline.svg", render_baseline())
    _write("bloom_test1_4tier_noCN.svg", render_test1())
    _write("bloom_test2_7tier_dense.svg", render_test2())
    _write("bloom_test3_6tier_minimal.svg", render_test3())


if __name__ == "__main__":
    main()
