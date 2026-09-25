#!/usr/bin/env python3
"""Regenerate the 4 TX_taxonomy variants into step2_codified.

Variants:
  - baseline: 4 domain × 3 sub × 2 leaf (24 leaves · spec 4×3×2)      · sidebar on
  - dense:    5 domain × 4 sub × 3 leaf (60 leaves)                    · sidebar on
  - sparse:   3 domain × 2 sub × 1 leaf (6  leaves)                    · sidebar on
  - minimal:  3 domain × 2 sub × 1 leaf                                · sidebar off
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from svg_relation_lib.presets.hero_embed_07_TX_taxonomy_v2 import (  # noqa: E402
    render_hero_embed_tx_taxonomy_v2,
    build_taxonomy_data,
)


OUT_DIR = os.path.abspath(os.path.join(
    HERE, "..", "final_svg_relation", "07_TX_taxonomy", "step2_codified",
))


# ═════════════════════════════════════════════════════════════════
# DENSE · 5 × 4 × 3
# ═════════════════════════════════════════════════════════════════

DENSE_ROOT = {"label": "LLM", "sub": "BENCH·XL", "tag": "ROOT"}

DENSE_DOMAINS = [
    {
        "key": "reason", "code": "D1", "label": "Reasoning",
        "sub": "logic · math · plan",
        "hue": "magenta", "leaf_count": 12,
        "subs": [
            {"code": "S01", "label": "Mathematical", "sub": "arithmetic · algebra",
             "leaves": [
                 {"code": "L01", "label": "MATH-500",     "tag": "500 q"},
                 {"code": "L02", "label": "GSM8K",        "tag": "8.5k q"},
                 {"code": "L03", "label": "MATH-Hard",    "tag": "1k q"},
             ]},
            {"code": "S02", "label": "Abstract logic", "sub": "grid · induction",
             "leaves": [
                 {"code": "L04", "label": "ARC-AGI",     "tag": "400 tk"},
                 {"code": "L05", "label": "BBH",         "tag": "23 sub"},
                 {"code": "L06", "label": "LogicNLI",    "tag": "20k pr"},
             ]},
            {"code": "S03", "label": "Planning", "sub": "multi-step · agent",
             "leaves": [
                 {"code": "L07", "label": "PlanBench",    "tag": "1.2k"},
                 {"code": "L08", "label": "TravelPlanner","tag": "1.6k"},
                 {"code": "L09", "label": "WebArena",     "tag": "812"},
             ]},
            {"code": "S04", "label": "Causal", "sub": "counterfactual · do-calc",
             "leaves": [
                 {"code": "L10", "label": "CLadder",      "tag": "10k q"},
                 {"code": "L11", "label": "CausalQA",     "tag": "3.4k"},
                 {"code": "L12", "label": "CRAB",         "tag": "1.1k"},
             ]},
        ],
    },
    {
        "key": "know", "code": "D2", "label": "Knowledge",
        "sub": "facts · exam · sense",
        "hue": "green", "leaf_count": 12,
        "subs": [
            {"code": "S05", "label": "Academic QA", "sub": "multi-domain",
             "leaves": [
                 {"code": "L13", "label": "MMLU-Pro",   "tag": "12k"},
                 {"code": "L14", "label": "GPQA-Diamond","tag": "198 q"},
                 {"code": "L15", "label": "AGIEval",    "tag": "8.1k"},
             ]},
            {"code": "S06", "label": "Open-domain", "sub": "retrieval",
             "leaves": [
                 {"code": "L16", "label": "TriviaQA",   "tag": "95k"},
                 {"code": "L17", "label": "NQ",         "tag": "3.6k"},
                 {"code": "L18", "label": "HotpotQA",   "tag": "112k"},
             ]},
            {"code": "S07", "label": "Commonsense", "sub": "pragmatics",
             "leaves": [
                 {"code": "L19", "label": "WinoGrande", "tag": "44k"},
                 {"code": "L20", "label": "PIQA",       "tag": "21k"},
                 {"code": "L21", "label": "HellaSwag",  "tag": "70k"},
             ]},
            {"code": "S08", "label": "Domain expert", "sub": "law · med · fin",
             "leaves": [
                 {"code": "L22", "label": "LegalBench", "tag": "162 tk"},
                 {"code": "L23", "label": "MedQA",      "tag": "12.7k"},
                 {"code": "L24", "label": "FinBen",     "tag": "36 tk"},
             ]},
        ],
    },
    {
        "key": "code", "code": "D3", "label": "Coding",
        "sub": "gen · repair · SQL",
        "hue": "slate", "leaf_count": 12,
        "subs": [
            {"code": "S09", "label": "Code synthesis", "sub": "function",
             "leaves": [
                 {"code": "L25", "label": "HumanEval+", "tag": "164"},
                 {"code": "L26", "label": "MBPP+",      "tag": "378"},
                 {"code": "L27", "label": "APPS",       "tag": "10k"},
             ]},
            {"code": "S10", "label": "Repo repair", "sub": "issue → PR",
             "leaves": [
                 {"code": "L28", "label": "SWE-Bench",        "tag": "2.3k"},
                 {"code": "L29", "label": "SWE-Bench-Verif",  "tag": "500"},
                 {"code": "L30", "label": "R2E",              "tag": "246"},
             ]},
            {"code": "S11", "label": "Data / SQL", "sub": "text2sql",
             "leaves": [
                 {"code": "L31", "label": "Spider 2.0", "tag": "632"},
                 {"code": "L32", "label": "DS-1000",    "tag": "1k"},
                 {"code": "L33", "label": "BIRD",       "tag": "12k"},
             ]},
            {"code": "S12", "label": "Multi-file", "sub": "codebase edit",
             "leaves": [
                 {"code": "L34", "label": "RepoBench", "tag": "27k"},
                 {"code": "L35", "label": "CrossCode", "tag": "9.5k"},
                 {"code": "L36", "label": "SWE-Gym",   "tag": "2.6k"},
             ]},
        ],
    },
    {
        "key": "safe", "code": "D4", "label": "Safety",
        "sub": "truth · tox · privacy",
        "hue": "rust", "leaf_count": 12,
        "subs": [
            {"code": "S13", "label": "Truthfulness", "sub": "halluc · calib",
             "leaves": [
                 {"code": "L37", "label": "TruthfulQA", "tag": "817"},
                 {"code": "L38", "label": "HaluEval",   "tag": "35k"},
                 {"code": "L39", "label": "FActScore",  "tag": "500"},
             ]},
            {"code": "S14", "label": "Toxicity", "sub": "stereotype",
             "leaves": [
                 {"code": "L40", "label": "ToxiGen", "tag": "274k"},
                 {"code": "L41", "label": "BBQ",     "tag": "58k"},
                 {"code": "L42", "label": "RealTox", "tag": "100k"},
             ]},
            {"code": "S15", "label": "Robustness", "sub": "jailbreak",
             "leaves": [
                 {"code": "L43", "label": "JailbreakBench", "tag": "100"},
                 {"code": "L44", "label": "HarmBench",      "tag": "510"},
                 {"code": "L45", "label": "AdvBench",       "tag": "520"},
             ]},
            {"code": "S16", "label": "Privacy", "sub": "PII · leakage",
             "leaves": [
                 {"code": "L46", "label": "PII-Leak",    "tag": "3.2k"},
                 {"code": "L47", "label": "PrivacyQA",   "tag": "1.7k"},
                 {"code": "L48", "label": "MemExtract",  "tag": "820"},
             ]},
        ],
    },
    {
        "key": "multi", "code": "D5", "label": "Multimodal",
        "sub": "vision · audio · vid",
        "hue": "gold_p", "leaf_count": 12,
        "subs": [
            {"code": "S17", "label": "Vision QA", "sub": "chart · doc",
             "leaves": [
                 {"code": "L49", "label": "MMMU-Pro", "tag": "1.5k"},
                 {"code": "L50", "label": "ChartQA",  "tag": "32k"},
                 {"code": "L51", "label": "DocVQA",   "tag": "50k"},
             ]},
            {"code": "S18", "label": "Video", "sub": "temporal",
             "leaves": [
                 {"code": "L52", "label": "VideoMME",  "tag": "900"},
                 {"code": "L53", "label": "MVBench",   "tag": "4k"},
                 {"code": "L54", "label": "TempCompass","tag": "1.2k"},
             ]},
            {"code": "S19", "label": "Audio", "sub": "speech · music",
             "leaves": [
                 {"code": "L55", "label": "AudioBench","tag": "1k"},
                 {"code": "L56", "label": "MMAU",      "tag": "5k"},
                 {"code": "L57", "label": "AIR-Bench", "tag": "19k"},
             ]},
            {"code": "S20", "label": "Grounding", "sub": "detect · point",
             "leaves": [
                 {"code": "L58", "label": "RefCOCO",  "tag": "50k"},
                 {"code": "L59", "label": "PointQA",  "tag": "3.9k"},
                 {"code": "L60", "label": "SEED-Bench","tag": "24k"},
             ]},
        ],
    },
]

DENSE_KPIS = [
    {"kicker": "DOMAINS",    "value": "5",   "note": "top-level buckets",     "hue": "magenta"},
    {"kicker": "SUB-GROUPS", "value": "20",  "note": "4 per domain",          "hue": "green"},
    {"kicker": "BENCHMARKS", "value": "60",  "note": "leaf-level test sets",  "hue": "rust"},
    {"kicker": "COVERAGE",   "value": "92%", "note": "extended HELM+ suite",  "hue": "slate"},
]

DENSE_COVERAGE = [
    {"label": "Reasoning",  "pct": 92, "note": "12 of 13 targeted",           "hue": "magenta"},
    {"label": "Knowledge",  "pct": 96, "note": "12 of 12 core suite",         "hue": "green"},
    {"label": "Coding",     "pct": 90, "note": "12 of 13 · multi-file gap",   "hue": "slate"},
    {"label": "Safety",     "pct": 80, "note": "12 of 15 · privacy pending",  "hue": "rust"},
    {"label": "Multimodal", "pct": 75, "note": "12 of 16 · audio incomplete", "hue": "gold_p"},
]

DENSE_HUE_LEGEND = [
    {"code": "D1", "label": "Reasoning",  "note": "math / logic", "hue": "magenta"},
    {"code": "D2", "label": "Knowledge",  "note": "recall / QA",  "hue": "green"},
    {"code": "D3", "label": "Coding",     "note": "gen / repair", "hue": "slate"},
    {"code": "D4", "label": "Safety",     "note": "truth / harm", "hue": "rust"},
    {"code": "D5", "label": "Multimodal", "note": "vision / A/V", "hue": "gold_p"},
]

DENSE_NOTES = [
    "How to read. 5 capability domains × 4 sub-groups × 3 benchmarks · 60 leaves total. Hue identifies parent domain across every tier; count / tag on right of each node is illustrative size.",
    "Structure. Extended benchmark inventory · adds Causal reasoning (D1), Domain-expert (D2), Multi-file coding (D3), Privacy (D4), and full Multimodal branch (D5).",
    "Source. Extended snapshot inspired by HELM+ · Bloom taxonomy · 2026-09 planning cycle.",
]


# ═════════════════════════════════════════════════════════════════
# SPARSE · 3 × 2 × 1
# ═════════════════════════════════════════════════════════════════

SPARSE_ROOT = {"label": "LLM", "sub": "BENCH·S", "tag": "ROOT"}

SPARSE_DOMAINS = [
    {
        "key": "reason", "code": "D1", "label": "Reasoning",
        "sub": "logic · math",
        "hue": "magenta", "leaf_count": 2,
        "subs": [
            {"code": "S01", "label": "Mathematical", "sub": "arithmetic",
             "leaves": [{"code": "L01", "label": "MATH-500", "tag": "500 q"}]},
            {"code": "S02", "label": "Abstract logic", "sub": "grid",
             "leaves": [{"code": "L02", "label": "ARC-AGI",  "tag": "400 tk"}]},
        ],
    },
    {
        "key": "know", "code": "D2", "label": "Knowledge",
        "sub": "facts · common",
        "hue": "green", "leaf_count": 2,
        "subs": [
            {"code": "S03", "label": "Academic QA", "sub": "multi-domain",
             "leaves": [{"code": "L03", "label": "MMLU-Pro", "tag": "12k q"}]},
            {"code": "S04", "label": "Commonsense", "sub": "WSC",
             "leaves": [{"code": "L04", "label": "WinoGrande","tag": "44k pr"}]},
        ],
    },
    {
        "key": "safe", "code": "D3", "label": "Safety",
        "sub": "truth · robust",
        "hue": "rust", "leaf_count": 2,
        "subs": [
            {"code": "S05", "label": "Truthfulness", "sub": "hallucination",
             "leaves": [{"code": "L05", "label": "TruthfulQA","tag": "817 q"}]},
            {"code": "S06", "label": "Robustness", "sub": "jailbreak",
             "leaves": [{"code": "L06", "label": "JailbreakBench","tag": "100 pr"}]},
        ],
    },
]

SPARSE_KPIS = [
    {"kicker": "DOMAINS",    "value": "3",   "note": "compact cut",         "hue": "magenta"},
    {"kicker": "SUB-GROUPS", "value": "6",   "note": "2 per domain",        "hue": "green"},
    {"kicker": "BENCHMARKS", "value": "6",   "note": "one leaf per sub",    "hue": "rust"},
    {"kicker": "COVERAGE",   "value": "60%", "note": "essentials only",     "hue": "slate"},
]

SPARSE_COVERAGE = [
    {"label": "Reasoning", "pct": 65, "note": "essentials only",          "hue": "magenta"},
    {"label": "Knowledge", "pct": 70, "note": "MMLU + commonsense",       "hue": "green"},
    {"label": "Safety",    "pct": 55, "note": "truth + jailbreak sample", "hue": "rust"},
]

SPARSE_HUE_LEGEND = [
    {"code": "D1", "label": "Reasoning", "note": "math / logic", "hue": "magenta"},
    {"code": "D2", "label": "Knowledge", "note": "recall / QA",  "hue": "green"},
    {"code": "D3", "label": "Safety",    "note": "truth / harm", "hue": "rust"},
]

SPARSE_NOTES = [
    "How to read. Compact cut · 3 domains · 2 sub-groups each · 1 benchmark per sub. Suitable for exec briefing hero slot.",
    "Structure. Only essential leaves retained per sub-group to keep the tree scannable at glance.",
    "Source. Compact snapshot · HELM v2 · 2026-09 exec cut.",
]


# ═════════════════════════════════════════════════════════════════
# MINIMAL · 3 × 2 × 1 · no sidebar
# ═════════════════════════════════════════════════════════════════

MINIMAL_NOTES = [
    "How to read. Minimal cut · 3 domains · 2 sub-groups · 1 benchmark each · sidebar stripped. Bare taxonomy for a one-shot deck.",
    "Structure. No coverage bars · no hue legend · no tier markers · the tree fills the full canvas width.",
]


# ═════════════════════════════════════════════════════════════════
# runners
# ═════════════════════════════════════════════════════════════════

def _write(name: str, svg: str) -> None:
    out_path = os.path.join(OUT_DIR, name)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"wrote {out_path}  ({len(svg):,} bytes)")


def render_baseline() -> str:
    return render_hero_embed_tx_taxonomy_v2(data=build_taxonomy_data())


def render_dense() -> str:
    data = build_taxonomy_data(
        root=DENSE_ROOT,
        domains=DENSE_DOMAINS,
        kpis=DENSE_KPIS,
        coverage=DENSE_COVERAGE,
        hue_legend=DENSE_HUE_LEGEND,
        notes_lines=DENSE_NOTES,
        figure_title="LLM Benchmark Taxonomy · extended inventory (5 domains · 60 benchmarks)",
        figure_caption=(
            "Hierarchical tree · 5 capability domains · 20 sub-groups · "
            "60 benchmarks · extended HELM+ coverage"
        ),
        source="Source · HELM+ · Bloom-style taxonomy · extended cut · 2026-09",
        fig_tag_note="TX · Taxonomy · dense cut · 5×4×3 extended inventory",
    )
    return render_hero_embed_tx_taxonomy_v2(data=data)


def render_sparse() -> str:
    data = build_taxonomy_data(
        root=SPARSE_ROOT,
        domains=SPARSE_DOMAINS,
        kpis=SPARSE_KPIS,
        coverage=SPARSE_COVERAGE,
        hue_legend=SPARSE_HUE_LEGEND,
        tier_markers=None,  # keep baseline markers
        notes_lines=SPARSE_NOTES,
        figure_title="LLM Benchmark Taxonomy · compact trio",
        figure_caption=(
            "Hierarchical tree · 3 domains · 6 sub-groups · 6 benchmarks · "
            "essentials-only cut"
        ),
        source="Source · HELM v2 · compact cut · 2026-09 exec briefing",
        fig_tag_note="TX · Taxonomy · sparse cut · 3×2×1 essentials",
    )
    return render_hero_embed_tx_taxonomy_v2(data=data)


def render_minimal() -> str:
    data = build_taxonomy_data(
        root=SPARSE_ROOT,
        domains=SPARSE_DOMAINS,
        kpis=SPARSE_KPIS,
        coverage=[],       # no coverage panel
        hue_legend=[],     # no hue legend
        tier_markers=[],   # no tier markers
        show_sidebar=False,
        notes_lines=MINIMAL_NOTES,
        figure_title="LLM Benchmark Taxonomy · minimal · sidebar off",
        figure_caption=(
            "Hierarchical tree · 3 domains · 6 sub-groups · 6 benchmarks · "
            "sidebar stripped · bare taxonomy hero"
        ),
        source="Source · HELM v2 · minimal cut · 2026-09",
        fig_tag_note="TX · Taxonomy · minimal cut · no sidebar · one-shot",
    )
    return render_hero_embed_tx_taxonomy_v2(data=data)


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    _write("baseline.svg", render_baseline())
    _write("dense.svg",    render_dense())
    _write("sparse.svg",   render_sparse())
    _write("minimal.svg",  render_minimal())


if __name__ == "__main__":
    main()
