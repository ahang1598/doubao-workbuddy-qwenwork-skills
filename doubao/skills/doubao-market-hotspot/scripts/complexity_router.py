#!/usr/bin/env python3
"""Route financial requests to direct, brief, or full delivery tiers."""

import argparse
import json
import re
from pathlib import Path


FULL_RE = re.compile(
    r"完整|深度|正式报告|研究报告|投委会|IC|逐项|全市场|"
    r"情景.*监控|估值.*竞争.*财务|不少于|至少\d+|"
    r"(?:输出|交付)[:：]|①.*②.*③.*④.*⑤|"
    r"优先级.*(?:安全线|情景)|现金安全线.*情景",
    re.I,
)
BRIEF_RE = re.compile(
    r"比较|最新财报|筛选|候选|初筛|影响|规划|复盘|"
    r"现金流|单位经济|传导|风险|估值|ARR|NRR|毛利|"
    r"烧钱|融资|管理层|情景|优先级|安全线|房贷|教育|医疗",
    re.I,
)

TIER_CONFIG = {
    "company-analysis": {
        "direct": {
            "target_chars": 1400,
            "slots": ["bottom_line", "minimum_evidence", "counterpoint", "limitations"],
        },
        "brief": {
            "target_chars": 2600,
            "slots": ["bottom_line", "evidence_chain", "countercase", "verification_queue", "sources"],
        },
        "full": {
            "target_chars": 5200,
            "slots": ["executive_summary", "business", "competition", "financial_quality", "valuation_boundary", "countercase", "risks", "sources"],
        },
    },
    "investment-opportunity-screening": {
        "direct": {
            "target_chars": 1800,
            "slots": ["scope", "shortlist", "evidence_and_risk", "verification"],
        },
        "brief": {
            "target_chars": 3200,
            "slots": ["scope", "candidate_pool", "filters", "ranking_or_shortfall", "rejections", "verification"],
        },
        "full": {
            "target_chars": 5600,
            "slots": ["scope", "universe", "funnel", "score_ledger", "false_positives", "top_k", "rejections", "sources"],
        },
    },
    "private-market-project-evaluation": {
        "direct": {
            "target_chars": 1400,
            "slots": ["stage_gate", "meeting_decision", "key_reasons", "questions"],
        },
        "brief": {
            "target_chars": 2800,
            "slots": ["stage_and_mandate", "commercialization", "economics_unknowns", "red_flags", "questions", "decision"],
        },
        "full": {
            "target_chars": 6000,
            "slots": ["identity", "mandate", "commercialization", "market", "unit_economics", "team", "terms", "red_flags", "diligence", "decision"],
        },
    },
    "wealth-planning": {
        "direct": {
            "target_chars": 1200,
            "slots": ["direct_answer", "formula_or_priority", "immediate_actions", "missing_inputs"],
        },
        "brief": {
            "target_chars": 2600,
            "slots": ["baseline", "priority", "scenario", "actions", "professional_boundary"],
        },
        "full": {
            "target_chars": 6000,
            "slots": ["household_snapshot", "goals", "cashflow", "risk_capacity", "scenarios", "allocation_boundary", "actions", "assumptions"],
        },
    },
    "event-impact-analysis": {
        "direct": {
            "target_chars": 1400,
            "slots": ["bottom_line", "causal_chain", "winners_losers_or_unknown", "conditions"],
        },
        "brief": {
            "target_chars": 2800,
            "slots": ["event_status", "mechanisms", "impact_matrix", "financial_mapping", "countercase", "monitoring"],
        },
        "full": {
            "target_chars": 5400,
            "slots": ["event_status", "mechanism_decomposition", "transmission", "impact_matrix", "financial_mapping", "priced_in_boundary", "scenarios", "countercase", "monitoring", "sources"],
        },
    },
}


def route(skill, prompt, requested_artifacts=None):
    text = prompt or ""
    requested_artifacts = requested_artifacts or []
    explicit_full = bool(FULL_RE.search(text)) or len(requested_artifacts) >= 4
    if explicit_full:
        tier = "full"
        reason = "explicit full report or multi-artifact request"
    elif len(text) <= 80 and not re.search(r"[①②③④⑤⑥⑦⑧]|(?:^|\s)\d+[.)、]", text):
        tier = "direct"
        reason = "single natural-language question"
    elif BRIEF_RE.search(text):
        tier = "brief"
        reason = "focused multi-step analysis"
    else:
        tier = "direct"
        reason = "small request without full-report signals"
    result = dict(TIER_CONFIG[skill][tier])
    result.update({"skill": skill, "tier": tier, "reason": reason})
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    args = parser.parse_args()
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    print(
        json.dumps(
            route(
                payload["skill"],
                payload["prompt"],
                payload.get("requested_artifacts"),
            ),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
