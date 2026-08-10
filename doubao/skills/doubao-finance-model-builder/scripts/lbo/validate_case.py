#!/usr/bin/env python3
"""Validate an LBO case before running the deterministic engine."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

from lbo_engine import run_case, validate_case


def _sample_case() -> Dict[str, Any]:
    years = []
    for year in range(1, 8):
        years.append(
            {
                "year": year,
                "ebitda": 160 * (1.05 ** year),
                "cash_taxes": 18 + year,
                "capex": 28 + year,
                "change_nwc": 5,
                "other_cash_costs": 0,
                "follow_on_equity": 0,
                "sponsor_distribution": 0,
            }
        )
    return {
        "company": {
            "name": "验证示例公司",
            "ticker": "TEST",
            "market": "US",
            "currency": "USD",
        },
        "as_of_date": "2026-07-16",
        "entry": {
            "equity_purchase_price": 1000,
            "debt_to_refinance": 300,
            "cash_acquired": 80,
            "target_cash_used": 40,
            "minimum_cash": 30,
            "minority_interest": 0,
            "preferred_stock": 0,
            "other_debt_like": 0,
            "preferred_stock_to_repay": 0,
            "other_debt_like_to_repay": 0,
            "transaction_fees": 20,
            "financing_fees": 10,
            "management_rollover": 50,
            "entry_ebitda": 160,
        },
        "debt_tranches": [
            {
                "name": "Term Loan",
                "opening_balance": 600,
                "cash_interest_rate": 0.08,
                "pik_rate": 0,
                "mandatory_amortization_rate": 0.01,
                "cash_sweep_priority": 2,
                "is_revolver": False,
                "commitment": 0,
                "maturity_year": 7,
            },
            {
                "name": "Revolver",
                "opening_balance": 0,
                "cash_interest_rate": 0.09,
                "pik_rate": 0,
                "mandatory_amortization_rate": 0,
                "cash_sweep_priority": 1,
                "is_revolver": True,
                "commitment": 100,
                "maturity_year": 5,
            },
        ],
        "years": years,
        "exit": {
            "years": [3, 4, 5, 6, 7],
            "multiples": [7.0, 7.625, 8.5],
            "exit_fee_rate": 0.01,
            "exit_debt_like_adjustments": 0,
            "sponsor_ownership": None,
        },
        "target_irrs": [0.20, 0.25, 0.30],
        "assumption_ledger": {
            "ebitda_growth": "Base按5%年增长；经营改善情景按完整年度路径输入",
            "depreciation_amortization": "未单独建模，现金税已作为显式输入",
            "depreciation_tax_shield": "不另行计算，避免与现金税重复",
            "capex": "逐年显式输入",
            "working_capital": "逐年显式输入",
            "cash_taxes": "逐年显式输入",
            "refinancing": "到期债务不自动再融资，流动性缺口保留",
        },
        "management_case": {
            "name": "经营改善情景",
            "years": [
                {**row, "ebitda": row["ebitda"] * 1.03}
                for row in years
            ],
            "exit_year": 5,
            "exit_multiple": 7.625,
        },
        "provenance": {
            "sources": [{"source_id": "SRC-TEST", "title": "自测数据", "date": "2026-07-16"}],
            "field_sources": {
                "entry": ["SRC-TEST"],
                "operating_case": ["SRC-TEST"],
                "debt_terms": ["SRC-TEST"],
                "exit": ["SRC-TEST"],
            },
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate LBO input JSON.")
    parser.add_argument("case", type=Path, nargs="?", help="Input case JSON.")
    parser.add_argument("--self-test", action="store_true", help="Run built-in validation.")
    args = parser.parse_args()

    if args.self_test:
        case = _sample_case()
        errors, warnings = validate_case(case)
        if errors:
            print(json.dumps({"valid": False, "errors": errors}, ensure_ascii=False, indent=2))
            return 1
        result = run_case(case)
        if not result["exit_results"]:
            print(json.dumps({"valid": False, "errors": ["No exit results."]}, ensure_ascii=False))
            return 1
        print(json.dumps({"valid": True, "warnings": warnings}, ensure_ascii=False, indent=2))
        return 0

    if args.case is None:
        parser.error("Provide a case JSON or use --self-test.")
    with args.case.open("r", encoding="utf-8") as handle:
        case = json.load(handle)
    errors, warnings = validate_case(case)
    print(
        json.dumps(
            {"valid": not errors, "errors": errors, "warnings": warnings},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
