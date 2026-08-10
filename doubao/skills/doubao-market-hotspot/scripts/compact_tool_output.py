#!/usr/bin/env python3
"""Compress deterministic tool JSON before injecting it into a model context."""

import argparse
import json
from pathlib import Path


def company(data):
    bridges = {}
    for period, row in data["bridges"].items():
        bridges[period] = {
            "net_profit": row["net_profit"],
            "adjustments": [
                [item["metric"], item["value"]] for item in row["adjustments"]
            ],
            "cfo": row["calculated_cfo"],
            "reported_cfo": row["reported_cfo"],
            "capex": row["capex"],
            "fcf": row["calculated_fcf"],
            "reconciles": row["reconciles"],
            "net_profit_to_cfo_pct": row["net_profit_to_cfo_pct"],
        }
    return {
        "entity": data["entity"],
        "currency": data["currency"],
        "unit": data["unit"],
        "periods": data["periods"],
        "bridges": bridges,
        "growth": data["growth"],
        "balance_growth": data["balance_growth"],
        "one_time_exclusions": data["one_time_exclusions"],
        "supplementary_facts": data["supplementary_facts"],
        "conflict_register": data["conflict_register"],
        "all_bridges_reconcile": data["all_bridges_reconcile"],
    }


def screening(data):
    first_evaluations = (
        data["hard_filter_ledger"][0].get("filter_evaluations", [])
        if data["hard_filter_ledger"]
        else []
    )
    hard_rejects = [
        {
            "candidate_id": item["candidate_id"],
            "first_failed_filter": item.get("first_failed_filter"),
            "reason": item.get("reason"),
        }
        for item in data["hard_filter_ledger"]
        if item["status"] != "pass"
    ]
    scores = []
    for item in data["score_ledger"]:
        scores.append(
            {
                "candidate_id": item["candidate_id"],
                "factor_scores": item.get("factor_scores"),
                "missing_factors": item.get("missing_factors"),
                "effective_weight": item.get("effective_weight"),
                "normalized_score": item.get("normalized_score"),
                "bucket": item.get("bucket"),
                "bucket_cap": item.get("bucket_cap"),
            }
        )
    return {
        "scope": data["scope"],
        "configuration_summary": data["configuration_summary"],
        "hard_filter_definitions": [
            {
                "filter_id": item.get("filter_id"),
                "field": item.get("field"),
                "operator": item.get("operator"),
                "expected": item.get("expected"),
            }
            for item in first_evaluations
        ],
        "funnel": data["funnel"],
        "hard_filter_rejections": hard_rejects,
        "scores": scores,
        "false_positive_rejections": [
            {
                "candidate_id": item["candidate_id"],
                "matched_rules": [
                    rule["rule_id"]
                    for rule in item.get("rule_evaluations", [])
                    if rule.get("matched")
                ],
            }
            for item in data["false_positive_ledger"]
            if item.get("decision") != "pass"
        ],
        "final_ranking": data["final_ranking"],
        "candidate_ledger": data["candidate_ledger"],
    }


def private(data):
    unit = {}
    for batch, item in data["unit_economics"].items():
        unit[batch] = {
            "selected_bom": item["selected_bom"],
            "selected_material_cost_per_unit_cny": item[
                "selected_material_cost_per_unit_cny"
            ],
            "quantity": item["quantity"],
            "unit_price_cny": item["unit_price_cny"],
            "delivery_status": item["delivery_status"],
            "winning_evidence": item.get("winning_evidence"),
            "conflicting_evidence_ids": item.get("conflicting_evidence_ids"),
            "management_to_adjusted_bridge_per_unit_cny": item.get(
                "management_to_adjusted_bridge_per_unit_cny"
            ),
            "known_cost_contribution_before_warranty_per_unit_cny": item[
                "known_cost_contribution_before_warranty_per_unit_cny"
            ],
            "known_cost_contribution_before_warranty_batch_cny": item[
                "known_cost_contribution_before_warranty_batch_cny"
            ],
            "warranty_rate": item["warranty_rate"],
            "cost_per_claim": item["cost_per_claim"],
            "adjusted_unit_contribution_formula": item[
                "adjusted_unit_contribution_formula"
            ],
            "positive_contribution_condition": item[
                "positive_contribution_condition"
            ],
        }
    runway = data["cash_runway"]
    return {
        "unit_economics": unit,
        "cash_runway": {
            "gross_bank_balance_cny": runway["gross_bank_balance_cny"],
            "restricted_cash_excluded_cny": runway[
                "restricted_cash_excluded_cny"
            ],
            "opening_available_cash_cny": runway["opening_available_cash_cny"],
            "dated_future_receipts": runway["dated_future_receipts"],
            "undated_receivables": runway["undated_receivables"],
            "known_dated_receipts_only": runway["known_dated_receipts_only"],
            "mechanical_earliest_collection_upper_bound": runway[
                "mechanical_earliest_collection_upper_bound"
            ],
        },
    }


def wealth(data):
    return {
        "assumption_change_log": data["assumption_change_log"],
        "base_scenario": data["base_scenario"],
        "goal_deferral_order": data["goal_deferral_order"],
        "non_deferrable_items": data["non_deferrable_items"],
        "recovery_conditions": data["recovery_conditions"],
    }


def event(data):
    price = data["price_comparability"]
    transmission = data["transmission_requirements"]
    return {
        "status": data["status"],
        "independent_original_source_count": data[
            "independent_original_source_count"
        ],
        "comparable_pairs": data["comparable_pairs"],
        "official_record": data["official_record"],
        "source_ledger": data["source_ledger"],
        "price_comparability": {
            "normalized_prices": price["normalized_prices"],
            "comparable_pairs": price["comparable_pairs"],
            "forbidden_comparisons": price["forbidden_comparisons"],
        },
        "transmission_requirements": {
            "required_exposure_fields": transmission["required_exposure_fields"],
            "company_exposures": transmission["company_exposures"],
            "exposure_gaps": transmission["exposure_gaps"],
        },
        "required_confirmer_topics": data["required_confirmer_topics"],
        "required_falsifier_topics": data["required_falsifier_topics"],
        "required_question_topics": data["required_question_topics"],
    }


FUNCTIONS = {
    "company-analysis": company,
    "investment-opportunity-screening": screening,
    "private-market-project-evaluation": private,
    "wealth-planning": wealth,
    "event-impact-analysis": event,
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skill", choices=FUNCTIONS, required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    output = FUNCTIONS[args.skill](data)
    text = json.dumps(output, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
