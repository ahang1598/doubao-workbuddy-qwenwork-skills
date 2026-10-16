"""Render 4 E2_5why hero-embed SVGs · baseline + 3 test variants.

Emits to final_svg_relation/09_E2_5why/step2_codified/.

Variants:
  - baseline · 6 layers (L0 + 5 whys) · full sidebar (BASELINE data)
  - dense    · 8 layers (L0 + 7 whys) · full sidebar
  - sparse   · 4 layers (L0 + 3 whys) · full sidebar
  - minimal  · 6 layers · no sidebar / no KPI band
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# put scripts/ on path so svg_relation_lib imports work
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from svg_relation_lib.presets.hero_embed_09_E2_5why_v2 import (  # noqa: E402
    build_5why_data,
    render_hero_embed_e2_5why_v2,
)
from svg_relation_lib._viewbox import shrink_viewbox  # noqa: E402


OUT_DIR = (_HERE.parent.parent
             / "final_svg_relation" / "09_E2_5why" / "step2_codified")


def _write(name: str, svg: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / name
    path.write_text(svg, encoding="utf-8")
    print(f"wrote {path}  ({len(svg):,} bytes)")


def _shrink(svg: str) -> str:
    return shrink_viewbox(svg, pad_x=12, pad_y=12)


# ═════════════════════════════════════════════════════════════════
# baseline · 6 layers (matches step1_reference)
# ═════════════════════════════════════════════════════════════════
def render_baseline() -> str:
    tree = build_5why_data()
    return _shrink(render_hero_embed_e2_5why_v2(tree))


# ═════════════════════════════════════════════════════════════════
# dense · L0 + 7 whys · SDLC pipeline stall postmortem
# ═════════════════════════════════════════════════════════════════
def render_dense() -> str:
    whys = [
        ("CI queue backed up 90 min",     "— jobs waiting > 90 min · 200% backlog —", "why1", "fact"),
        ("K8s node autoscaler stalled",     "— HPA target unreachable · pending 6 min —", "why2", "flaw"),
        ("Runner AMI missing python3.11",   "— snapshot rebuilt · older tag pinned —",     "why3", "flaw"),
        ("Terraform module out of sync",    "— main branch never applied —",                 "why4", "fact"),
        ("Plan reviewer rotation lapsed",   "— on-leave · no fallback assignee —",           "why5", "flaw"),
        ("No IaC ownership rota",            "— team wiki out of date · 4 owners left —",   "why5", "fact"),
        ("Runbook doesn't cover IaC drift",  "— last drift drill: 2025-06 —",                "why5", "root"),
    ]
    kpis = [
        {"kicker": "INCIDENT",   "value": "90 min",              "note": "CI queue stall",       "hue": "rust"},
        {"kicker": "DEPTH",      "value": "7 WHYs",              "note": "extended ladder",       "hue": "blue"},
        {"kicker": "ROOT CAUSE", "value": "IaC OWNERSHIP GONE",  "note": "drift undetected",      "hue": "orange"},
        {"kicker": "ACTIONS",    "value": "6",                    "note": "3 immediate · 3 later", "hue": "green"},
    ]
    parallel = {
        "title": "PARALLEL FACTOR",
        "tag":   "3× RETRY",
        "body":  "开发者手动重试放大 3×",
        "hint":  "— dev-console 未展示 queue depth · 触发人工重复触发 —",
        "amp":   "↳ COMPOUNDED THE BACKLOG",
    }
    actions = [
        ("A1", "IMMEDIATE", "在 IaC 顶层加 CODEOWNERS",       "this sprint"),
        ("A2", "IMMEDIATE", "补丁 runner AMI · 固化到 IaC",    "this sprint"),
        ("A3", "IMMEDIATE", "紧急 rota · 三人轮值",              "this sprint"),
        ("A4", "SHORT",     "runbook 加 IaC drift 演练",         "2 sprints"),
        ("A5", "PROCESS",   "季度 drift drill · 双人 review",     "ongoing"),
        ("A6", "MONITOR",   "CI queue depth 接入 SLO",           "1 sprint"),
    ]
    post_fix = [
        ("rust",   "Queue MTTR", "90 min → < 15 min",       "SLO board"),
        ("orange", "Drift alert", "0 → 100% coverage",       "Terraform Cloud"),
        ("green",  "Owner rota",  "4 → 8 named engineers",   "wiki"),
    ]
    tree = build_5why_data(
        incident="CI 队列积压 90 分钟",
        incident_sub="— 2026-09-09 09:14 · SEV-2 pipeline stall —",
        whys=whys,
        kicker="FIGURE 09 · POSTMORTEM · SDLC ROOT CAUSE LADDER",
        figure_title="5-Why 追问 · CI 队列 90 分钟积压",
        figure_caption=("Sakichi Toyoda root-cause ladder · 7 追问 · "
                          "1 平行因素 · 6 整改 · SDLC pipeline stall · Postmortem draft"),
        kpis=kpis,
        parallel_factor=parallel,
        corrective_actions=actions,
        post_fix_kpis=post_fix,
        fig_ref="Figure 09 · dense · 7-Why ladder",
    )
    return _shrink(render_hero_embed_e2_5why_v2(tree))


# ═════════════════════════════════════════════════════════════════
# sparse · L0 + 3 whys · quick RCA
# ═════════════════════════════════════════════════════════════════
def render_sparse() -> str:
    whys = [
        ("Login latency p99 spiked 5×",   "— p99 = 1.6s vs baseline 320ms —", "why2", "fact"),
        ("Redis connection storm",          "— ConnPool exhausted · 3200 open —", "why4", "flaw"),
        ("Retry hedge misconfigured",       "— hedge_ms=0 · 全量重试 —",           "why5", "root"),
    ]
    kpis = [
        {"kicker": "INCIDENT",   "value": "18 min",           "note": "login p99 spike",    "hue": "rust"},
        {"kicker": "DEPTH",      "value": "3 WHYs",           "note": "quick ladder",        "hue": "blue"},
        {"kicker": "ROOT CAUSE", "value": "HEDGE MISCONFIG",  "note": "0 ms 退避",           "hue": "orange"},
        {"kicker": "ACTIONS",    "value": "3",                 "note": "2 immediate · 1 later","hue": "green"},
    ]
    parallel = {
        "title": "PARALLEL FACTOR",
        "tag":   "2× LOAD",
        "body":  "TikTok live 引入 2× 平峰流量",
        "hint":  "— campaign 未预告 · SRE 无准备 —",
        "amp":   "↳ AMPLIFIED THE SPIKE",
    }
    actions = [
        ("A1", "IMMEDIATE", "修 hedge_ms 参数",           "this sprint"),
        ("A2", "IMMEDIATE", "Redis pool 加限流",          "this sprint"),
        ("A3", "MONITOR",   "hedge 参数接入 config diff", "1 sprint"),
    ]
    post_fix = [
        ("rust",   "MTTR",       "18 min → < 5 min",       "SLO board"),
        ("orange", "Hedge check", "0 → 100% covered",       "config-lint"),
        ("green",  "P99 login",   "1.6 s → < 400 ms",       "Prometheus"),
    ]
    tree = build_5why_data(
        incident="Login p99 1.6s · 18 分钟",
        incident_sub="— 2026-09-09 21:07 · SEV-2 login latency —",
        whys=whys,
        kicker="FIGURE 09 · POSTMORTEM · SPARSE LADDER",
        figure_title="5-Why 追问 · 登录延迟 18 分钟",
        figure_caption=("Sakichi Toyoda root-cause ladder · 3 追问 · "
                          "1 平行因素 · 3 整改 · quick RCA · Postmortem draft"),
        kpis=kpis,
        parallel_factor=parallel,
        corrective_actions=actions,
        post_fix_kpis=post_fix,
        fig_ref="Figure 09 · sparse · 3-Why ladder",
    )
    return _shrink(render_hero_embed_e2_5why_v2(tree))


# ═════════════════════════════════════════════════════════════════
# minimal · 6 layers · no sidebar · no KPI band
# ═════════════════════════════════════════════════════════════════
def render_minimal() -> str:
    tree = build_5why_data(
        show_sidebar=False,
        kpis=[],
        parallel_factor=None,
        corrective_actions=[],
        post_fix_kpis=[],
        figure_caption=("Sakichi Toyoda root-cause ladder · 5 追问 · "
                          "content-only · no sidebar · no KPI band"),
        fig_ref="Figure 09 · minimal · content-only",
    )
    return _shrink(render_hero_embed_e2_5why_v2(tree))


def main() -> None:
    _write("baseline.svg", render_baseline())
    _write("dense.svg", render_dense())
    _write("sparse.svg", render_sparse())
    _write("minimal.svg", render_minimal())


if __name__ == "__main__":
    main()
