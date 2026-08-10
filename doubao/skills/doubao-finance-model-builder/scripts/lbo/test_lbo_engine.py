#!/usr/bin/env python3
"""Regression tests for the deterministic LBO engine."""

from __future__ import annotations

import unittest

from lbo_engine import run_case, validate_case, xirr
from render_lbo_report import render
from validate_case import _sample_case


class LboEngineTests(unittest.TestCase):
    def test_sample_case_validates_and_balances(self) -> None:
        case = _sample_case()
        errors, _ = validate_case(case)
        self.assertEqual(errors, [])
        result = run_case(case)
        self.assertAlmostEqual(
            result["sources_and_uses"]["balance_check"], 0.0, places=8
        )
        self.assertEqual(len(result["annual_debt_schedule"]), 7)
        self.assertEqual(len(result["exit_results"]), 15)
        self.assertEqual(result["model_status_code"], "PASS")

    def test_debt_schedule_and_return_bridge(self) -> None:
        result = run_case(_sample_case())
        ending_debt = [
            row["ending_debt"] for row in result["annual_debt_schedule"]
        ]
        self.assertTrue(
            all(later <= earlier + 1e-7 for earlier, later in zip(ending_debt, ending_debt[1:]))
        )
        for bridge in result["return_bridge"]:
            self.assertAlmostEqual(bridge["reconciliation_difference"], 0.0, places=6)
            percentages = bridge["contribution_pct_of_equity_change"]
            if abs(bridge["equity_value_change"]) > 1e-8:
                self.assertAlmostEqual(
                    sum(value for value in percentages.values() if value is not None),
                    1.0,
                    places=6,
                )

    def test_returns_are_economic(self) -> None:
        result = run_case(_sample_case())
        base = next(
            item
            for item in result["exit_results"]
            if item["exit_year"] == 5 and abs(item["exit_multiple"] - 7.625) < 1e-9
        )
        self.assertGreater(base["moic"], 1.0)
        self.assertIsNotNone(base["xirr"])
        self.assertGreater(base["xirr"], 0.0)
        self.assertAlmostEqual(
            base["profit"], base["total_proceeds"] - base["total_invested"], places=8
        )

    def test_xirr_simple_case(self) -> None:
        from datetime import date

        value = xirr(
            [
                (date(2025, 1, 1), -100.0),
                (date(2026, 1, 1), 110.0),
            ]
        )
        self.assertIsNotNone(value)
        self.assertAlmostEqual(value, 0.10, places=7)

    def test_invalid_cash_source_is_rejected(self) -> None:
        case = _sample_case()
        case["entry"]["target_cash_used"] = 999
        errors, _ = validate_case(case)
        self.assertTrue(any("target_cash_used" in message for message in errors))

    def test_unfunded_maturity_does_not_erase_debt(self) -> None:
        case = _sample_case()
        case["debt_tranches"][0]["maturity_year"] = 1
        case["debt_tranches"][1]["commitment"] = 0
        result = run_case(case)
        first_year = result["annual_debt_schedule"][0]
        self.assertGreater(first_year["unpaid_mandatory"], 0.0)
        self.assertGreater(first_year["ending_debt"], 0.0)
        self.assertGreater(first_year["liquidity_shortfall"], 0.0)

    def test_unfunded_distribution_is_excluded_from_returns(self) -> None:
        case = _sample_case()
        case["years"][0]["sponsor_distribution"] = 10_000
        result = run_case(case)
        first_year = result["annual_debt_schedule"][0]
        self.assertGreater(first_year["distribution_shortfall"], 0.0)
        self.assertLess(
            first_year["sponsor_distribution"],
            first_year["requested_sponsor_distribution"],
        )

    def test_assumption_ledger_is_mandatory(self) -> None:
        case = _sample_case()
        case.pop("assumption_ledger")
        errors, _ = validate_case(case)
        self.assertTrue(any("assumption_ledger" in message for message in errors))

    def test_management_case_comparison_is_quantified(self) -> None:
        result = run_case(_sample_case())
        comparison = result["management_case_comparison"]
        self.assertEqual(comparison["exit_year"], 5)
        self.assertGreater(
            comparison["management"]["enterprise_value"],
            comparison["base"]["enterprise_value"],
        )
        self.assertGreater(comparison["delta"]["equity_value"], 0)

    def test_chinese_report_contains_assumptions_and_attribution(self) -> None:
        report = render(run_case(_sample_case()), 5, 7.625)
        self.assertIn("关键假设清单", report)
        self.assertIn("回报来源量化", report)
        self.assertIn("经营改善量化对比", report)
        self.assertIn("至少一个退出倍数高于进入倍数", report)

    def test_invalid_numeric_input_returns_errors_without_crashing(self) -> None:
        mutations = [
            ("entry", "entry_ebitda"),
            ("entry", "target_cash_used"),
        ]
        for section, field in mutations:
            case = _sample_case()
            case[section][field] = "bad"
            errors, _ = validate_case(case)
            self.assertTrue(any(field in message for message in errors))
        case = _sample_case()
        case["debt_tranches"][0]["mandatory_amortization_rate"] = "bad"
        errors, _ = validate_case(case)
        self.assertTrue(any("mandatory_amortization_rate" in message for message in errors))
        case = _sample_case()
        case["years"][0]["ebitda"] = "bad"
        errors, _ = validate_case(case)
        self.assertTrue(any("years[0].ebitda" in message for message in errors))

    def test_missing_provenance_blocks_return_conclusion(self) -> None:
        case = _sample_case()
        case.pop("provenance")
        result = run_case(case)
        self.assertEqual(result["model_status_code"], "INCOMPLETE")
        report = render(result, 5, 7.625)
        self.assertIn("质量门未通过", report)
        self.assertNotIn("财务投资人利润：", report)


if __name__ == "__main__":
    unittest.main(verbosity=2)
