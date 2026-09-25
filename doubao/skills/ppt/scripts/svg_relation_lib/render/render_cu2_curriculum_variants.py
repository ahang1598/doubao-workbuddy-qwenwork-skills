#!/usr/bin/env python3
"""Regenerate 4 CU2_curriculum variants into step2_codified.

Variants:
  - baseline: 6-module engineering academy (default BASELINE_MODULES) + KPIs
              + milestones + sidebar + reading guide
  - dense:    8-module data-science bootcamp (SQL → capstone)
              · 8 weeks × 2-block · rich topics
  - sparse:   4-module UX foundations track (research → ship)
              · fewer modules · fewer topics per module
  - minimal:  5-module ops track · no sidebar · no reading guide
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from svg_relation_lib.presets.hero_embed_32_CU2_curriculum_v2 import (  # type: ignore  # noqa: E402
    render_hero_embed_cu2_curriculum_v2,
    build_curriculum_data,
)


OUT_DIR = os.path.abspath(os.path.join(
    HERE, "..", "..", "final_svg_relation",
    "32_CU2_curriculum", "step2_codified",
))


def _write(name: str, svg: str) -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"wrote {path}  ({len(svg):,} chars)")


# ═════════════════════════════════════════════════════════════════
# DENSE · 8-module data-science bootcamp · 16 week
# ═════════════════════════════════════════════════════════════════

DENSE_MODULES = [
    {
        "code": "D01", "title": "SQL & data",
        "subtitle": "Postgres · dbt",
        "kind": "core", "hue": "navy",
        "duration": "18 h",
        "topics": [
            "Relational model",
            "Window funcs",
            "dbt models",
            "Lineage & catalog",
        ],
        "assessment": "SQL lab",
        "assessment_note": "6-question set",
        "prereq": "— none —",
        "prereq_note": "entry point",
        "weight": 0.55,
    },
    {
        "code": "D02", "title": "Python DS",
        "subtitle": "pandas · numpy",
        "kind": "core", "hue": "navy",
        "duration": "18 h",
        "topics": [
            "pandas idioms",
            "numpy vectorise",
            "matplotlib",
            "notebook hygiene",
        ],
        "assessment": "Notebook set",
        "assessment_note": "3 EDA notebooks",
        "prereq": "D01 · SQL",
        "prereq_note": "SQL joins req",
        "weight": 0.65,
    },
    {
        "code": "D03", "title": "Statistics",
        "subtitle": "inference · A/B",
        "kind": "core", "hue": "navy",
        "duration": "20 h",
        "topics": [
            "Hypothesis test",
            "A/B experiments",
            "Confidence int",
            "Bayesian priors",
        ],
        "assessment": "Stat set",
        "assessment_note": "peer review",
        "prereq": "D02 · Python",
        "prereq_note": "pandas fluency",
        "weight": 0.70,
    },
    {
        "code": "D04", "title": "ML fund",
        "subtitle": "sklearn · trees",
        "kind": "core", "hue": "navy",
        "duration": "22 h",
        "topics": [
            "Regression",
            "Gradient boost",
            "Cross-val eval",
            "Feature engr",
        ],
        "assessment": "Kaggle comp",
        "assessment_note": "leaderboard",
        "prereq": "D03 · Stats",
        "prereq_note": "inference basics",
        "weight": 0.80,
    },
    {
        "code": "D05", "title": "Deep learn",
        "subtitle": "PyTorch · CNN",
        "kind": "elective", "hue": "green",
        "duration": "22 h",
        "topics": [
            "PyTorch autograd",
            "CNN vision",
            "RNN sequence",
            "Transformer 101",
        ],
        "assessment": "Model card",
        "assessment_note": "eval on holdout",
        "prereq": "D04 · ML",
        "prereq_note": "sklearn base",
        "weight": 0.85,
    },
    {
        "code": "D06", "title": "LLM & RAG",
        "subtitle": "LangChain · vec",
        "kind": "elective", "hue": "green",
        "duration": "20 h",
        "topics": [
            "Prompt engr",
            "RAG arch",
            "Vector stores",
            "LLM evaluation",
        ],
        "assessment": "RAG app",
        "assessment_note": "OSS demo",
        "prereq": "D05 · DL",
        "prereq_note": "Transformer OK",
        "weight": 0.88,
    },
    {
        "code": "D07", "title": "MLOps",
        "subtitle": "MLflow · Airflow",
        "kind": "elective", "hue": "green",
        "duration": "18 h",
        "topics": [
            "Experiment track",
            "Pipeline orches",
            "Model registry",
            "Drift monitor",
        ],
        "assessment": "Deploy demo",
        "assessment_note": "live model",
        "prereq": "D04 + D05",
        "prereq_note": "ML + DL req",
        "weight": 0.75,
    },
    {
        "code": "D08", "title": "Capstone",
        "subtitle": "ship a product",
        "kind": "capstone", "hue": "gold_p",
        "duration": "40 h",
        "topics": [
            "Scoping & data",
            "Model & eval",
            "Deploy monitor",
            "Demo & retro",
        ],
        "assessment": "Panel jury",
        "assessment_note": "written report",
        "prereq": "all core + 1",
        "prereq_note": "D01-04 must",
        "weight": 1.00,
    },
]

DENSE_KPIS = [
    {"kicker": "MODULES", "value": "8",
     "note": "4 core · 3 elect · 1 caps", "hue": "navy"},
    {"kicker": "DURATION", "value": "16 wk",
     "note": "178 h contact · project sprints", "hue": "green"},
    {"kicker": "MILESTONES", "value": "5",
     "note": "gates every 2-3 module", "hue": "gold_p"},
    {"kicker": "COHORT", "value": "32",
     "note": "analysts → ML engineers", "hue": "navy"},
]

DENSE_WEEK_TICKS = [
    "W1-W2", "W3-W4", "W5-W6", "W7-W8",
    "W9-W10", "W11-W12", "W13-W14", "W15-W16",
]

DENSE_MILESTONES = [
    {"at_module": 2, "label": "GATE 1", "kind": "gate"},
    {"at_module": 4, "label": "GATE 2", "kind": "gate"},
    {"at_module": 6, "label": "GATE 3", "kind": "gate"},
    {"at_module": 7, "label": "GATE 4", "kind": "gate"},
    {"at_module": 8, "label": "DEMO DAY", "kind": "demo"},
]

DENSE_OUTCOMES = [
    {"code": "LO1", "title": "Query production data",
     "body": "Write correct SQL · pandas transforms · at scale."},
    {"code": "LO2", "title": "Ship a ML model",
     "body": "Train, evaluate, and deploy a supervised model."},
    {"code": "LO3", "title": "Operate MLOps",
     "body": "Track experiments, monitor drift, retrain on schedule."},
    {"code": "LO4", "title": "Present findings",
     "body": "Write reports, defend model choices, communicate risk."},
]

DENSE_SIDEBAR_STATS = [
    {"label": "PASS THRESHOLD", "value": "4 / 5 gates"},
    {"label": "CAPSTONE WEIGHT", "value": "35 %"},
    {"label": "MENTOR HOURS", "value": "48 h"},
]

DENSE_READ_LINES = [
    {"hue": "navy", "title": "Kind hue",
     "lines": ["navy = core · green = elective ·",
               "amber = capstone"]},
    {"hue": "gray", "title": "Prereq flow",
     "lines": ["chain arrows link module N → N+1 ·",
               "electives fork off core"]},
    {"hue": "gold_p", "title": "Milestone gate",
     "lines": ["5 flags on axis · dark = final",
               "demo day at W15-W16"]},
    {"hue": "green", "title": "Credit weight",
     "lines": ["bottom bar shows module weight ·",
               "capstone weighted 35 % of grade"]},
]

DENSE_NOTES = (
    "Notes. 8-module data-science bootcamp · 16 weeks · 4 core + 3 elective + "
    "1 capstone · duration and gate cadence follow standard bootcamp pattern."
)


# ═════════════════════════════════════════════════════════════════
# SPARSE · 4-module UX foundations · 8 week · 3 core + 1 capstone
# ═════════════════════════════════════════════════════════════════

SPARSE_MODULES = [
    {
        "code": "U01", "title": "User research",
        "subtitle": "interviews · surveys · synthesis",
        "kind": "core", "hue": "navy",
        "duration": "20 h",
        "topics": [
            "Interview technique",
            "Survey design & bias",
            "Affinity synthesis",
        ],
        "assessment": "Research report",
        "assessment_note": "3 user interviews",
        "prereq": "— none —",
        "prereq_note": "entry point",
        "weight": 0.55,
    },
    {
        "code": "U02", "title": "Interaction design",
        "subtitle": "flows · prototypes · Figma",
        "kind": "core", "hue": "navy",
        "duration": "22 h",
        "topics": [
            "Task flow modelling",
            "Prototype fidelity",
            "Figma component system",
        ],
        "assessment": "Interactive prototype",
        "assessment_note": "usability test",
        "prereq": "U01 · Research",
        "prereq_note": "user insights required",
        "weight": 0.75,
    },
    {
        "code": "U03", "title": "Design systems",
        "subtitle": "tokens · patterns · a11y",
        "kind": "core", "hue": "navy",
        "duration": "20 h",
        "topics": [
            "Design tokens & theming",
            "Component library patterns",
            "WCAG 2.2 accessibility",
        ],
        "assessment": "Token set + 5 components",
        "assessment_note": "peer critique",
        "prereq": "U02 · IxD",
        "prereq_note": "Figma fluency",
        "weight": 0.80,
    },
    {
        "code": "U04", "title": "Capstone",
        "subtitle": "ship a portfolio artefact",
        "kind": "capstone", "hue": "gold_p",
        "duration": "36 h",
        "topics": [
            "Brief & user research",
            "Design & prototype",
            "Test & iterate",
            "Portfolio write-up",
        ],
        "assessment": "Portfolio review",
        "assessment_note": "hiring panel jury",
        "prereq": "all core (U01-U03)",
        "prereq_note": "3 core mandatory",
        "weight": 1.00,
    },
]

SPARSE_KPIS = [
    {"kicker": "MODULES", "value": "4",
     "note": "3 core · 1 capstone", "hue": "navy"},
    {"kicker": "DURATION", "value": "8 wk",
     "note": "98 h contact · studio-style", "hue": "green"},
    {"kicker": "MILESTONES", "value": "3",
     "note": "gates at W3 · W6 · W8", "hue": "gold_p"},
    {"kicker": "COHORT", "value": "18",
     "note": "career-switchers · L1 → L3", "hue": "navy"},
]

SPARSE_WEEK_TICKS = ["W1 - W2", "W3 - W4", "W5 - W6", "W7 - W8"]

SPARSE_MILESTONES = [
    {"at_module": 1, "label": "GATE 1", "kind": "gate"},
    {"at_module": 3, "label": "GATE 2", "kind": "gate"},
    {"at_module": 4, "label": "PORTFOLIO", "kind": "demo"},
]

SPARSE_OUTCOMES = [
    {"code": "LO1", "title": "Run user research",
     "body": "Plan, conduct, and synthesise research end-to-end."},
    {"code": "LO2", "title": "Prototype at fidelity",
     "body": "Move from wireframe to testable Figma prototype."},
    {"code": "LO3", "title": "Ship a portfolio piece",
     "body": "Write up work in a hiring-ready case study."},
]

SPARSE_SIDEBAR_STATS = [
    {"label": "PASS THRESHOLD", "value": "2 / 3 gates"},
    {"label": "CAPSTONE WEIGHT", "value": "45 %"},
    {"label": "STUDIO HOURS", "value": "24 h"},
]

SPARSE_READ_LINES = [
    {"hue": "navy", "title": "Kind hue",
     "lines": ["navy = core · amber = capstone",
               "compressed 4-module ladder"]},
    {"hue": "gray", "title": "Prereq flow",
     "lines": ["strict chain U01→U02→U03→U04 ·",
               "no electives at this tier"]},
    {"hue": "gold_p", "title": "Milestone gate",
     "lines": ["3 gates · portfolio review is final ·",
               "hiring-panel jury"]},
    {"hue": "green", "title": "Credit weight",
     "lines": ["capstone weighted 45 % of grade ·",
               "portfolio is promotion currency"]},
]

SPARSE_NOTES = (
    "Notes. 4-module UX foundations · career-switcher track · compressed 8 "
    "weeks · strict prereq chain · capstone is portfolio artefact."
)


# ═════════════════════════════════════════════════════════════════
# MINIMAL · 5-module ops track · no sidebar · no reading guide
# ═════════════════════════════════════════════════════════════════

MINIMAL_MODULES = [
    {
        "code": "O01", "title": "Networking",
        "subtitle": "TCP · DNS · TLS",
        "kind": "core", "hue": "navy",
        "duration": "20 h",
        "topics": [
            "TCP + UDP fundamentals",
            "DNS resolution + caching",
            "TLS handshake + certs",
            "Load balancer basics",
        ],
        "assessment": "tcpdump lab",
        "assessment_note": "pass mark 70 %",
        "prereq": "— none —",
        "prereq_note": "entry point",
        "weight": 0.60,
    },
    {
        "code": "O02", "title": "Linux ops",
        "subtitle": "systemd · perf · logs",
        "kind": "core", "hue": "navy",
        "duration": "22 h",
        "topics": [
            "systemd services",
            "perf & flamegraph",
            "journalctl + logs",
            "cgroups + limits",
        ],
        "assessment": "Ops lab · runbook",
        "assessment_note": "written incident sim",
        "prereq": "O01 · Networking",
        "prereq_note": "TCP debug required",
        "weight": 0.70,
    },
    {
        "code": "O03", "title": "Kubernetes",
        "subtitle": "k8s · Helm · Argo",
        "kind": "core", "hue": "navy",
        "duration": "24 h",
        "topics": [
            "Pods · deployments",
            "Services · Ingress",
            "Helm charts",
            "ArgoCD gitops",
        ],
        "assessment": "k8s deploy demo",
        "assessment_note": "live cluster review",
        "prereq": "O02 · Linux",
        "prereq_note": "systemd + perf",
        "weight": 0.80,
    },
    {
        "code": "O04", "title": "Observability",
        "subtitle": "OTel · Prometheus · SLO",
        "kind": "elective", "hue": "green",
        "duration": "20 h",
        "topics": [
            "OTel traces + spans",
            "Prometheus metrics",
            "SLO / SLI / error budget",
            "Alertmanager rules",
        ],
        "assessment": "SLO dashboard build",
        "assessment_note": "30-day baseline",
        "prereq": "O03 · k8s",
        "prereq_note": "cluster ops",
        "weight": 0.75,
    },
    {
        "code": "O05", "title": "SRE capstone",
        "subtitle": "ship a runbook + game day",
        "kind": "capstone", "hue": "gold_p",
        "duration": "32 h",
        "topics": [
            "Incident scoping",
            "Runbook authoring",
            "Chaos game day",
            "Post-mortem review",
        ],
        "assessment": "Game-day + write-up",
        "assessment_note": "panel review",
        "prereq": "all core + O04",
        "prereq_note": "O01-O03 mandatory",
        "weight": 1.00,
    },
]

MINIMAL_KPIS = [
    {"kicker": "MODULES", "value": "5",
     "note": "3 core · 1 elect · 1 caps", "hue": "navy"},
    {"kicker": "DURATION", "value": "10 wk",
     "note": "118 h contact · on-call sim", "hue": "green"},
    {"kicker": "MILESTONES", "value": "3",
     "note": "gates at W3 · W7 · W10", "hue": "gold_p"},
    {"kicker": "COHORT", "value": "20",
     "note": "SREs · L2 → L4 pathway", "hue": "navy"},
]

MINIMAL_WEEK_TICKS = ["W1-W2", "W3-W4", "W5-W6", "W7-W8", "W9-W10"]

MINIMAL_MILESTONES = [
    {"at_module": 1, "label": "GATE 1", "kind": "gate"},
    {"at_module": 4, "label": "GATE 2", "kind": "gate"},
    {"at_module": 5, "label": "GAME DAY", "kind": "demo"},
]

MINIMAL_NOTES = (
    "Notes. 5-module SRE ops track · 10 weeks · no sidebar (compact view) · "
    "capstone is game-day + runbook."
)


# ═════════════════════════════════════════════════════════════════
# renderers
# ═════════════════════════════════════════════════════════════════

def render_baseline() -> str:
    data = build_curriculum_data()  # all defaults · 6 module engineering
    return render_hero_embed_cu2_curriculum_v2(data=data)


def render_dense() -> str:
    data = build_curriculum_data(
        modules=DENSE_MODULES,
        kpis=DENSE_KPIS,
        week_ticks=DENSE_WEEK_TICKS,
        milestones=DENSE_MILESTONES,
        outcomes=DENSE_OUTCOMES,
        sidebar_stats=DENSE_SIDEBAR_STATS,
        read_lines=DENSE_READ_LINES,
        notes=DENSE_NOTES,
        figure_tag="Figure 32 · curriculum · dense · 2026",
        kicker="FIGURE 32 · CURRICULUM MAP · DENSE",
        kicker_body=(
            "Horizontal 8-module timeline · 16 weeks · duration + topics + "
            "assessment per column · sidebar shows kind mix and outcomes"
        ),
        figure_title="Data Science Bootcamp · 2026 curriculum map",
        figure_caption=(
            "8 modules · 16 weeks · SQL to deployed model · 5 milestone "
            "gates · capstone ships a data product"
        ),
    )
    return render_hero_embed_cu2_curriculum_v2(data=data)


def render_sparse() -> str:
    data = build_curriculum_data(
        modules=SPARSE_MODULES,
        kpis=SPARSE_KPIS,
        week_ticks=SPARSE_WEEK_TICKS,
        milestones=SPARSE_MILESTONES,
        outcomes=SPARSE_OUTCOMES,
        sidebar_stats=SPARSE_SIDEBAR_STATS,
        read_lines=SPARSE_READ_LINES,
        notes=SPARSE_NOTES,
        figure_tag="Figure 32 · curriculum · sparse · 2026",
        kicker="FIGURE 32 · CURRICULUM MAP · SPARSE",
        kicker_body=(
            "Compressed 4-module timeline · 8 weeks · strict prereq chain · "
            "capstone is a portfolio artefact"
        ),
        figure_title="UX Foundations · 2026 curriculum map",
        figure_caption=(
            "4 modules · 8 weeks · research → interaction → system → "
            "portfolio · career-switcher pathway"
        ),
    )
    return render_hero_embed_cu2_curriculum_v2(data=data)


def render_minimal() -> str:
    data = build_curriculum_data(
        modules=MINIMAL_MODULES,
        kpis=MINIMAL_KPIS,
        week_ticks=MINIMAL_WEEK_TICKS,
        milestones=MINIMAL_MILESTONES,
        outcomes=[],
        sidebar_stats=[],
        read_lines=[],
        notes=MINIMAL_NOTES,
        sidebar=False,
        figure_tag="Figure 32 · curriculum · minimal · 2026",
        kicker="FIGURE 32 · CURRICULUM MAP · MINIMAL",
        kicker_body=(
            "5-module compact view · no sidebar · 10 weeks · SRE ops track "
            "· game-day capstone"
        ),
        figure_title="SRE Ops Track · 2026 curriculum map",
        figure_caption=(
            "5 modules · 10 weeks · networking → linux → k8s → observ → "
            "game day · compact layout without sidebar"
        ),
    )
    return render_hero_embed_cu2_curriculum_v2(data=data)


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    _write("baseline.svg", render_baseline())
    _write("dense.svg", render_dense())
    _write("sparse.svg", render_sparse())
    _write("minimal.svg", render_minimal())


if __name__ == "__main__":
    main()
