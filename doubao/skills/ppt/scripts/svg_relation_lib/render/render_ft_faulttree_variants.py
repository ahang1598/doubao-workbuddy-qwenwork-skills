#!/usr/bin/env python3
"""Regenerate the 4 FT_faulttree variants into step2_codified.

Variants:
  - baseline: 3 gates (OR/AND/OR) · 7 basic events · dominant B7 highlighted · sidebar + KPI
  - dense:    5 gates · 12 basics · full sidebar + KPI · full footer
  - sparse:   2 gates · 4 basics · sidebar + KPI
  - minimal:  2 gates · 4 basics · no sidebar (bare tree) · minimal KPI + footer
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from svg_relation_lib.presets.hero_embed_49_FT_faulttree_v2 import (  # noqa: E402
    render_hero_embed_ft_faulttree_v2,
    build_faulttree_data,
)


OUT_DIR = os.path.abspath(os.path.join(
    HERE, "..", "final_svg_relation", "49_FT_faulttree", "step2_codified",
))


# ═════════════════════════════════════════════════════════════════
# DENSE · 5 gates · 12 basics · full sidebar
# ═════════════════════════════════════════════════════════════════

DENSE_TOP = {
    "code":  "TOP EVENT · T",
    "title": "Global checkout freeze 27-min",
    "sub":   "SEV-1 · 2026-08-14 · 09:03 UTC",
    "hue":   "magenta",
}

DENSE_GATES = [
    {"id": "M1", "op": "OR",  "title": "Network partition",  "sub": "AZ boundary",
     "hue": "blue", "p": "2.1e-4",
     "basics": [
         {"code": "B1", "title": "AZ-b split-brain", "sub": "AZ boundary",       "p": "1.2e-4"},
         {"code": "B2", "title": "DNS flap 43s",     "sub": "upstream resolver", "p": "9.0e-5"},
     ]},
    {"id": "M2", "op": "AND", "title": "Database failure",   "sub": "storage tier",
     "hue": "magenta", "p": "3.4e-5",
     "basics": [
         {"code": "B3", "title": "Primary DB crash", "sub": "storage tier",  "p": "1.8e-3"},
         {"code": "B4", "title": "Replica lag > 8s", "sub": "async repl",    "p": "1.9e-2"},
     ]},
    {"id": "M3", "op": "OR",  "title": "Auth service down",  "sub": "token issuer",
     "hue": "green", "p": "2.8e-4",
     "basics": [
         {"code": "B5", "title": "JWT verify slow", "sub": "crypto lib",       "p": "5.0e-5"},
         {"code": "B6", "title": "IdP timeout",     "sub": "upstream provider","p": "6.4e-5"},
     ]},
    {"id": "M4", "op": "OR",  "title": "Cache stampede",     "sub": "edge cache",
     "hue": "gold_p", "p": "1.1e-4",
     "basics": [
         {"code": "B7", "title": "Token svc OOM",   "sub": "dominant · 44%",
          "p": "1.7e-4", "dominant": True, "dominant_share": 44},
         {"code": "B8", "title": "Redis eviction",  "sub": "TTL storm",   "p": "8.2e-5"},
     ]},
    {"id": "M5", "op": "AND", "title": "Payment gateway",    "sub": "3rd-party",
     "hue": "blue", "p": "6.2e-5",
     "basics": [
         {"code": "B9",  "title": "Bank API 5xx",   "sub": "issuer down",    "p": "3.1e-4"},
         {"code": "B10", "title": "Retry queue full","sub": "circuit open",   "p": "2.0e-4"},
     ]},
]

DENSE_KPIS = [
    {"kicker": "TOP EVENT PROBABILITY", "value": "P(T) = 7.2e-4",
     "note": "per request · rolling 30d",       "hue": "magenta"},
    {"kicker": "MTBF / MTTR",           "value": "31 d  ·  27 min",
     "note": "availability 99.94% · SLO 99.95%","hue": "blue"},
    {"kicker": "MINIMAL CUT SETS",      "value": "6 sets · order 2-3",
     "note": "{B7} · {B1,B2} · {B3,B4} · +3 more","hue": "gold_p"},
    {"kicker": "DOMINANT PATH",         "value": "B7 · Token OOM",
     "note": "44% of P(T) · single-point",      "hue": "green"},
]

DENSE_SIDEBAR = {
    "legend_kicker": "GATE LEGEND",
    "legend_items": [
        {"kind": "OR",    "title": "OR gate · disjunction",
         "sub":   "Output fires if ANY child event fires",
         "formula": "P(out) = 1 - Pi(1 - Pi)"},
        {"kind": "AND",   "title": "AND gate · conjunction",
         "sub":   "Output fires only if ALL children fire",
         "formula": "P(out) = Pi Pi"},
        {"kind": "basic", "title": "Basic event",
         "sub":   "Elementary cause · leaf with P value",
         "formula": ""},
    ],
    "table_kicker": "PROBABILITY TABLE",
    "table_rows": [
        {"label": "B7 · Token svc OOM",  "p": "1.7e-4", "share_pct": 44, "hue": "gold_p", "highlight": True},
        {"label": "B1 · AZ-b split-brain","p": "1.2e-4","share_pct": 17, "hue": "blue"},
        {"label": "B9 · Bank API 5xx",   "p": "3.1e-4", "share_pct": 12, "hue": "blue"},
        {"label": "B2 · DNS flap 43s",   "p": "9.0e-5", "share_pct": 10, "hue": "blue"},
        {"label": "B8 · Redis eviction", "p": "8.2e-5", "share_pct": 8,  "hue": "gold_p"},
        {"label": "B3-B4 (AND) joint",   "p": "3.4e-5", "share_pct": 4,  "hue": "magenta"},
    ],
    "recommendation_kicker": "RECOMMENDATION",
    "recommendation_lines": [
        "Add HPA guard on token service",
        "Warm cache TTL jitter · circuit-break",
        "issuer path · target P(T) < 2e-4 by Q4.",
    ],
}


# ═════════════════════════════════════════════════════════════════
# SPARSE · 2 gates · 4 basics · full sidebar
# ═════════════════════════════════════════════════════════════════

SPARSE_TOP = {
    "code":  "TOP EVENT · T",
    "title": "Checkout 5-min outage",
    "sub":   "P1 incident · 2026-09-03 · 12:41 UTC",
    "hue":   "magenta",
}

SPARSE_GATES = [
    {"id": "M1", "op": "OR",  "title": "Network partition", "sub": "AZ boundary",
     "hue": "blue", "p": "1.4e-4",
     "basics": [
         {"code": "B1", "title": "AZ-b split-brain", "sub": "AZ boundary",       "p": "1.2e-4"},
         {"code": "B2", "title": "DNS flap 43s",     "sub": "upstream resolver", "p": "9.0e-5",
          "dominant": True, "dominant_share": 64},
     ]},
    {"id": "M2", "op": "AND", "title": "Database failure",  "sub": "storage tier",
     "hue": "magenta", "p": "3.4e-5",
     "basics": [
         {"code": "B3", "title": "Primary DB crash", "sub": "storage tier", "p": "1.8e-3"},
         {"code": "B4", "title": "Replica lag > 8s", "sub": "async repl",   "p": "1.9e-2"},
     ]},
]

SPARSE_KPIS = [
    {"kicker": "TOP EVENT PROBABILITY", "value": "P(T) = 1.7e-4",
     "note": "per request · rolling 7d",         "hue": "magenta"},
    {"kicker": "MTBF / MTTR",           "value": "58 d  ·  5 min",
     "note": "availability 99.99% · SLO 99.95%", "hue": "blue"},
    {"kicker": "MINIMAL CUT SETS",      "value": "2 sets · order 1",
     "note": "{B1} · {B2}",                      "hue": "gold_p"},
    {"kicker": "DOMINANT PATH",         "value": "B2 · DNS flap",
     "note": "64% of P(T)",                      "hue": "green"},
]

SPARSE_SIDEBAR = {
    "legend_kicker": "GATE LEGEND",
    "legend_items": [
        {"kind": "OR",    "title": "OR gate · disjunction",
         "sub":   "Output fires if ANY child fires",
         "formula": "P(out) = 1 - Pi(1 - Pi)"},
        {"kind": "AND",   "title": "AND gate · conjunction",
         "sub":   "Output fires only if ALL children fire",
         "formula": "P(out) = Pi Pi"},
        {"kind": "basic", "title": "Basic event",
         "sub":   "Elementary cause · leaf with P",
         "formula": ""},
    ],
    "table_kicker": "PROBABILITY TABLE",
    "table_rows": [
        {"label": "B2 · DNS flap 43s",   "p": "9.0e-5", "share_pct": 64, "hue": "blue", "highlight": True},
        {"label": "B1 · AZ-b split-brain","p": "1.2e-4","share_pct": 26, "hue": "blue"},
        {"label": "B3-B4 (AND) joint",   "p": "3.4e-5", "share_pct": 10, "hue": "magenta"},
    ],
    "recommendation_kicker": "RECOMMENDATION",
    "recommendation_lines": [
        "Harden DNS resolver path",
        "Add fallback resolver · TTL cap 30s",
        "Target P(T) < 5e-5 by Q3.",
    ],
}


# ═════════════════════════════════════════════════════════════════
# MINIMAL · 2 gates · 4 basics · NO sidebar (bare tree)
# ═════════════════════════════════════════════════════════════════

MINIMAL_TOP = {
    "code":  "TOP EVENT · T",
    "title": "Login service brief outage",
    "sub":   "P2 incident · 2026-08-22",
    "hue":   "magenta",
}

MINIMAL_GATES = [
    {"id": "M1", "op": "OR",  "title": "Network partition", "sub": "AZ boundary",
     "hue": "blue", "p": "1.4e-4",
     "basics": [
         {"code": "B1", "title": "AZ split", "sub": "AZ boundary", "p": "1.2e-4"},
         {"code": "B2", "title": "DNS flap", "sub": "resolver",    "p": "9.0e-5"},
     ]},
    {"id": "M2", "op": "AND", "title": "Auth service down", "sub": "token issuer",
     "hue": "green", "p": "3.4e-5",
     "basics": [
         {"code": "B3", "title": "JWT slow",  "sub": "crypto",   "p": "5.0e-5"},
         {"code": "B4", "title": "IdP down",  "sub": "upstream", "p": "6.4e-5",
          "dominant": True, "dominant_share": 58},
     ]},
]

MINIMAL_KPIS = [
    {"kicker": "TOP EVENT PROBABILITY", "value": "P(T) = 1.7e-4",
     "note": "per request · rolling 7d", "hue": "magenta"},
    {"kicker": "MTBF / MTTR",           "value": "44 d  ·  8 min",
     "note": "availability 99.98%",      "hue": "blue"},
    {"kicker": "GATE COUNT",            "value": "2 · order 1",
     "note": "OR gate + AND gate",       "hue": "gold_p"},
    {"kicker": "DOMINANT PATH",         "value": "B4 · IdP down",
     "note": "58% of P(T)",              "hue": "green"},
]


# ═════════════════════════════════════════════════════════════════
# renderers
# ═════════════════════════════════════════════════════════════════

def _write(name: str, svg: str) -> None:
    out_path = os.path.join(OUT_DIR, name)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"wrote {out_path}  ({len(svg):,} bytes)")


def render_baseline() -> str:
    data = build_faulttree_data()  # baseline defaults
    return render_hero_embed_ft_faulttree_v2(data=data)


def render_dense() -> str:
    data = build_faulttree_data(
        top_event=DENSE_TOP,
        gates=DENSE_GATES,
        kpis=DENSE_KPIS,
        sidebar=DENSE_SIDEBAR,
        figure_title="Fault tree · Global checkout freeze",
        figure_caption=(
            "FTA · 1 top event · 5 logic gates · 10 basic events · "
            "extended cut · post-mortem 2026-08-14"
        ),
        source="Source · Post-mortem · Checkout platform · 2026-08-14 · IEC 61025 methodology.",
        fig_tag="FIGURE 49 · FAULT TREE",
        fig_tag_note="Dense cut · 5 gates · 10 basic events · dominant path B7",
    )
    return render_hero_embed_ft_faulttree_v2(data=data)


def render_sparse() -> str:
    data = build_faulttree_data(
        top_event=SPARSE_TOP,
        gates=SPARSE_GATES,
        kpis=SPARSE_KPIS,
        sidebar=SPARSE_SIDEBAR,
        figure_title="Fault tree · Checkout 5-min outage",
        figure_caption=(
            "FTA · 1 top event · 2 logic gates · 4 basic events · "
            "compact cut · post-mortem 2026-09-03"
        ),
        source="Source · Post-mortem · Checkout platform · 2026-09-03 · IEC 61025 methodology.",
        fig_tag="FIGURE 49 · FAULT TREE",
        fig_tag_note="Sparse cut · 2 gates · 4 basics · dominant path B2",
    )
    return render_hero_embed_ft_faulttree_v2(data=data)


def render_minimal() -> str:
    data = build_faulttree_data(
        top_event=MINIMAL_TOP,
        gates=MINIMAL_GATES,
        kpis=MINIMAL_KPIS,
        sidebar={},   # bare tree · no sidebar
        figure_title="Fault tree · Login service brief outage",
        figure_caption=(
            "FTA · 1 top event · 2 logic gates · 4 basic events · "
            "minimal cut · no sidebar"
        ),
        source="Source · Post-mortem · Auth platform · 2026-08-22 · IEC 61025 methodology.",
        fig_tag="FIGURE 49 · FAULT TREE",
        fig_tag_note="Minimal cut · sidebar stripped · exec briefing view",
    )
    return render_hero_embed_ft_faulttree_v2(data=data, show_sidebar=False)


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    _write("baseline.svg", render_baseline())
    _write("dense.svg", render_dense())
    _write("sparse.svg", render_sparse())
    _write("minimal.svg", render_minimal())


if __name__ == "__main__":
    main()
