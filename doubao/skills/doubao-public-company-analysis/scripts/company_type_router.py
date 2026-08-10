#!/usr/bin/env python3
"""Route a company to a compact P1 metric pack. Stdlib only."""

import argparse
import json
from pathlib import Path


PACKS = {
    "financial_insurance": {
        "required_metrics": ["premium_or_revenue", "underwriting_or_credit_quality", "investment_income", "capital_adequacy", "roe"],
        "financial_bridge": "underwriting_or_spread + investment_result - losses_and_expenses -> earnings -> book_value_and_capital",
        "valuation": ["P/B-ROE", "P/EV where applicable"],
        "inapplicable": ["CFO-minus-capex as universal FCF"],
    },
    "retail_membership": {
        "required_metrics": ["same_store_sales", "traffic_or_members", "renewal_or_retention", "merchandise_margin", "inventory_turns"],
        "financial_bridge": "traffic × ticket + membership_fees -> operating_profit -> working_capital_and_capex -> cash",
        "valuation": ["P/E", "EV/EBIT", "reverse DCF"],
        "inapplicable": ["membership fees treated as all operating profit without costs"],
    },
    "project_credit_sales": {
        "required_metrics": ["orders", "gross_margin", "receivables_aging", "cash_collection", "impairment_and_non_cash_settlement"],
        "financial_bridge": "reported_profit - receivable_growth - non_cash_settlement - impairment_adjustments -> cash quality",
        "valuation": ["normalized P/E", "EV/EBIT", "reverse assumptions"],
        "inapplicable": ["CFO headline without collection-quality analysis"],
    },
    "manufacturing": {
        "required_metrics": ["volume", "price_mix", "unit_cost", "capacity_utilization", "inventory_and_capex"],
        "financial_bridge": "volume × price_mix - unit_cost -> operating_profit -> working_capital - capex -> cash",
        "valuation": ["mid-cycle P/E", "EV/EBITDA", "reverse DCF"],
        "inapplicable": ["peer growth comparison without product-scope alignment"],
    },
    "internet_platform_capital_intensive": {
        "required_metrics": ["segment_revenue", "take_rate_or_arpu", "traffic_or_users", "capex_and_depreciation", "utilization_or_monetization"],
        "financial_bridge": "segment monetization - operating costs - depreciation -> profit; CFO - capex -> cash",
        "valuation": ["SOTP", "normalized P/E", "FCF yield", "reverse DCF"],
        "inapplicable": ["broker target price as valuation"],
    },
    "content_platform": {
        "required_metrics": [
            "subscription_or_ad_revenue",
            "usage_or_engagement",
            "variable_rights_share",
            "minimum_guarantees",
            "owned_content_investment",
        ],
        "financial_bridge": (
            "statutory CFO -> cash content investment and cash capex -> "
            "conventional FCF; company adjusted FCF reconciled separately"
        ),
        "valuation": ["EV/revenue with margin context", "normalized FCF", "reverse DCF"],
        "inapplicable": [
            "variable rights or creator share treated as fixed-cost dilution",
            "operating-profit proxy labeled as universal FCF",
        ],
    },
    "brand_ip_licensing": {
        "required_metrics": ["product_or_ip_concentration", "repeat_purchase", "owned_vs_licensed_mix", "channel_efficiency", "inventory_turns"],
        "financial_bridge": "sell-through × gross margin - channel_and_content_costs -> operating_profit -> inventory_and_receivables -> cash",
        "valuation": ["P/E", "EV/EBIT", "reverse growth assumptions"],
        "inapplicable": [
            "management popularity claims as moat evidence",
            "variable royalty expense treated as fixed-cost dilution",
        ],
    },
    "general": {
        "required_metrics": ["revenue_driver", "margin_driver", "working_capital", "capex", "capital_returns"],
        "financial_bridge": "revenue -> operating profit -> working capital and capex -> cash",
        "valuation": ["P/E or EV/EBIT", "reverse assumptions"],
        "inapplicable": [],
    },
}


def route(payload):
    requested = payload.get("company_type", "general")
    selected = requested if requested in PACKS else "general"
    return {"type": selected, **PACKS[selected], "fallback_used": selected != requested}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("--output")
    args = parser.parse_args()
    result = route(json.loads(Path(args.input).read_text(encoding="utf-8")))
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
