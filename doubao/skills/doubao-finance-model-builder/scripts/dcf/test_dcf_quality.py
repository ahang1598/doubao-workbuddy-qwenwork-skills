#!/usr/bin/env python3
"""Regression tests for DCF share classes and delivery gates."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from calculate_dcf import calculate
from validate_dcf import validate as validate_calculation
from validate_delivery import validate as validate_delivery


ROOT = Path(__file__).resolve().parents[2]


class DcfQualityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = json.loads(
            (ROOT / "assets/dcf/example-normalized-dcf.json").read_text(encoding="utf-8")
        )

    def formal_payload(self) -> dict:
        payload = copy.deepcopy(self.payload)
        payload["meta"]["model_purpose"] = "formal"
        payload["wacc_components"]["capital_structure_basis"] = "current_actual"
        payload["wacc_components"]["capital_structure_rationale"] = "使用估值基准日实际结构"
        for scenario in payload["scenarios"].values():
            scenario["terminal_growth"] = 0.01
            scenario["scenario_evidence"] = {
                "rationale": "基于历史经营与稳态收敛",
                "changed_drivers": ["收入增长", "利润率"],
                "source_ids": ["SRC-DEMO"],
                "invalidation_conditions": ["增长连续低于下限"],
            }
        payload["equity_bridge"].pop("current_share_price", None)
        payload["equity_bridge"]["share_classes"] = [
            {
                "security_id": "A.TEST",
                "exchange": "SSE",
                "shares": 100,
                "shares_date": "2026-06-30",
                "price": 25,
                "price_date": "2026-06-30",
                "price_basis": "unadjusted_close",
                "currency": "CNY",
                "fx_to_valuation_currency": 1,
                "source_id": "SRC-DEMO",
                "reference_market_cap": 2500,
                "market_cap_date": "2026-06-30",
                "market_cap_source_id": "SRC-DEMO",
                "market_cap_tolerance_pct": 0.02,
            }
        ]
        payload["equity_bridge"]["corporate_action_review"] = {
            "baseline_share_date": "2025-12-31",
            "search_start_date": "2025-12-31",
            "reviewed_through_date": "2026-06-30",
            "source_ids": ["SRC-DEMO"],
            "no_unrecorded_actions_confirmed": True,
            "actions": [],
        }
        payload["field_sources"]["corporate_actions"] = {"source_id": "SRC-DEMO", "label": "R"}
        payload["field_sources"]["market_cap_cross_check"] = {"source_id": "SRC-DEMO", "label": "D"}
        return payload

    def valid_workbook_audit(self) -> dict:
        return {
            "status": "PASS",
            "workflow": "dcf",
            "errors": [],
            "metrics": {
                "formula_error_count": 0,
                "direct_circular_count": 0,
                "external_link_formula_count": 0,
            },
        }

    def test_dual_listing_market_cap_uses_each_security_price(self) -> None:
        payload = copy.deepcopy(self.payload)
        payload["equity_bridge"].pop("current_share_price", None)
        payload["equity_bridge"]["share_classes"] = [
            {
                "security_id": "A.TEST",
                "exchange": "SSE",
                "shares": 60,
                "shares_date": "2026-06-30",
                "price": 20,
                "price_date": "2026-06-30",
                "price_basis": "unadjusted_close",
                "currency": "CNY",
                "fx_to_valuation_currency": 1,
                "source_id": "SRC-DEMO",
            },
            {
                "security_id": "H.TEST",
                "exchange": "HKEX",
                "shares": 40,
                "shares_date": "2026-06-30",
                "price": 30,
                "price_date": "2026-06-30",
                "price_basis": "unadjusted_close",
                "currency": "HKD",
                "fx_to_valuation_currency": 0.9,
                "source_id": "SRC-DEMO",
            },
        ]
        result = calculate(payload)
        bridge = result["scenarios"][result["base_scenario"]]["equity_bridge"]
        self.assertAlmostEqual(bridge["current_market_cap"], 2280.0)
        self.assertAlmostEqual(bridge["current_share_price_equivalent"], 22.8)
        self.assertIsNotNone(result["reverse_dcf"])

    def test_share_class_sum_must_equal_diluted_shares(self) -> None:
        payload = copy.deepcopy(self.payload)
        payload["equity_bridge"]["share_classes"] = [
            {"security_id": "A.TEST", "exchange": "SSE", "shares": 99, "price": 20, "price_date": "2026-06-30", "currency": "CNY", "fx_to_valuation_currency": 1, "source_id": "SRC-DEMO"}
        ]
        with self.assertRaisesRegex(ValueError, "分证券股数合计"):
            calculate(payload)

    def test_delivery_gate_passes_one_source_of_truth(self) -> None:
        calculated = calculate(copy.deepcopy(self.payload))
        base = calculated["scenarios"][calculated["base_scenario"]]
        audit = {
            "formula_error_count": 0,
            "calculation_validation_status": "PASS",
            "source_coverage_ratio": 1.0,
            "source_mapping_audit_passed": True,
            "source_conflict_count": 0,
            "share_class_metadata_complete": True,
            "corporate_action_review_complete": True,
            "share_count_as_of_valuation_date": True,
            "price_share_basis_consistent": True,
            "market_cap_cross_check_passed": True,
            "corporate_action_unapplied_count": 0,
            "three_statements_in_scope": False,
            "wacc_outputs": {"summary": base["wacc"], "dcf": base["wacc"]},
            "per_share_outputs": {"excel": base["per_share_value"], "report": base["per_share_value"]},
            "scenario_uses_shared_model": True,
            "sensitivity_uses_shared_model": True,
            "hardcoded_key_output_count": 0,
            "share_bridge_difference": 0,
            "equity_bridge_difference": 0,
            "all_visible_sheets_rendered": True,
            "unresolved_warning_count": 0,
        }
        result = validate_delivery(self.payload, calculated, audit, self.valid_workbook_audit())
        self.assertEqual(result["model_status_code"], "PASS")

    def test_delivery_gate_rejects_wacc_mismatch_and_unbalanced_bs(self) -> None:
        calculated = calculate(copy.deepcopy(self.payload))
        base = calculated["scenarios"][calculated["base_scenario"]]
        audit = {
            "formula_error_count": 0,
            "calculation_validation_status": "PASS",
            "source_coverage_ratio": 1.0,
            "source_mapping_audit_passed": True,
            "source_conflict_count": 0,
            "share_class_metadata_complete": True,
            "corporate_action_review_complete": True,
            "share_count_as_of_valuation_date": True,
            "price_share_basis_consistent": True,
            "market_cap_cross_check_passed": True,
            "corporate_action_unapplied_count": 0,
            "three_statements_in_scope": True,
            "balance_sheet_checks": [{"period": "2027E", "difference": 1, "tolerance": 0.01}],
            "cash_rollforward_checks": [{"period": "2027E", "difference": 0, "tolerance": 0.01}],
            "wacc_outputs": {"summary": base["wacc"] + 0.01, "dcf": base["wacc"]},
            "per_share_outputs": {"excel": base["per_share_value"], "report": base["per_share_value"]},
            "scenario_uses_shared_model": True,
            "sensitivity_uses_shared_model": True,
            "hardcoded_key_output_count": 0,
            "share_bridge_difference": 0,
            "equity_bridge_difference": 0,
            "all_visible_sheets_rendered": True,
            "unresolved_warning_count": 0,
        }
        result = validate_delivery(self.payload, calculated, audit, self.valid_workbook_audit())
        self.assertEqual(result["model_status_code"], "FAIL")
        self.assertTrue(any("WACC" in message for message in result["errors"]))

    def test_delivery_gate_rejects_failed_direct_workbook_audit(self) -> None:
        calculated = calculate(copy.deepcopy(self.payload))
        base = calculated["scenarios"][calculated["base_scenario"]]
        audit = {
            "calculation_validation_status": "PASS", "source_coverage_ratio": 1.0,
            "source_mapping_audit_passed": True, "source_conflict_count": 0,
            "share_class_metadata_complete": True, "corporate_action_review_complete": True,
            "share_count_as_of_valuation_date": True, "price_share_basis_consistent": True,
            "market_cap_cross_check_passed": True, "corporate_action_unapplied_count": 0,
            "three_statements_in_scope": False,
            "wacc_outputs": {"summary": base["wacc"], "dcf": base["wacc"]},
            "per_share_outputs": {"excel": base["per_share_value"], "report": base["per_share_value"]},
            "scenario_uses_shared_model": True, "sensitivity_uses_shared_model": True,
            "hardcoded_key_output_count": 0, "share_bridge_difference": 0,
            "equity_bridge_difference": 0, "all_visible_sheets_rendered": True,
            "unresolved_warning_count": 0,
        }
        direct = self.valid_workbook_audit()
        direct["status"] = "FAIL"
        direct["metrics"]["direct_circular_count"] = 1
        result = validate_delivery(self.payload, calculated, audit, direct)
        self.assertEqual(result["model_status_code"], "FAIL")

    def test_formal_model_without_scenario_evidence_is_incomplete(self) -> None:
        payload = self.formal_payload()
        for scenario in payload["scenarios"].values():
            scenario.pop("scenario_evidence")
        result = validate_calculation(payload)
        self.assertEqual(result["model_status_code"], "INCOMPLETE")
        self.assertTrue(any("情景缺少" in message for message in result["incomplete_reasons"]))

    def test_formal_model_rejects_direct_wacc_hardcode(self) -> None:
        payload = self.formal_payload()
        payload.pop("wacc_components")
        payload["wacc"] = 0.08
        result = validate_calculation(payload)
        self.assertEqual(result["model_status_code"], "FAIL")
        self.assertTrue(any("不得直接硬编码最终WACC" in message for message in result["errors"]))

    def test_formal_model_rejects_terminal_value_over_90_percent(self) -> None:
        payload = self.formal_payload()
        for scenario in payload["scenarios"].values():
            scenario["terminal_growth"] = 0.068
            scenario["scenario_evidence"] = {
                "rationale": "压力测试",
                "changed_drivers": ["永续增长率"],
                "source_ids": ["SRC-DEMO"],
                "invalidation_conditions": ["长期增长回落"],
            }
        result = validate_calculation(payload)
        self.assertEqual(result["model_status_code"], "FAIL")
        self.assertTrue(any("终值占比超过90%" in message for message in result["errors"]))

    def test_empty_field_source_groups_do_not_pass(self) -> None:
        payload = self.formal_payload()
        payload["field_sources"] = {"forecast": {}, "wacc": {}, "equity_bridge": {}}
        result = validate_calculation(payload)
        self.assertEqual(result["model_status_code"], "FAIL")
        self.assertTrue(any("来源映射为空或无效" in message for message in result["errors"]))

    def test_scenario_evidence_requires_real_source_ids(self) -> None:
        payload = self.formal_payload()
        for scenario in payload["scenarios"].values():
            scenario["scenario_evidence"].pop("source_ids")
        result = validate_calculation(payload)
        self.assertEqual(result["model_status_code"], "INCOMPLETE")
        self.assertTrue(any("情景缺少" in message for message in result["incomplete_reasons"]))

    def test_share_classes_require_date_currency_fx_and_source(self) -> None:
        payload = self.formal_payload()
        payload["equity_bridge"]["share_classes"] = [
            {"security_id": "A.TEST", "exchange": "SSE", "shares": 60, "price": 20, "price_date": "2026-06-30", "currency": "CNY", "fx_to_valuation_currency": 1, "source_id": "SRC-DEMO"},
            {"security_id": "H.TEST", "exchange": "HKEX", "shares": 40, "price": 30, "price_date": "2026-06-30", "currency": "HKD", "source_id": "SRC-DEMO"},
        ]
        with self.assertRaisesRegex(ValueError, "fx_to_valuation_currency"):
            calculate(payload)

    def test_formal_model_requires_corporate_action_review(self) -> None:
        payload = self.formal_payload()
        payload["equity_bridge"].pop("corporate_action_review")
        result = validate_calculation(payload)
        self.assertEqual(result["model_status_code"], "FAIL")
        self.assertTrue(any("公司行动" in message for message in result["errors"]))

    def test_effective_capitalization_must_roll_into_valuation_date_shares(self) -> None:
        payload = self.formal_payload()
        payload["equity_bridge"]["corporate_action_review"]["actions"] = [
            {
                "security_id": "A.TEST",
                "action_type": "capitalization_issue",
                "announcement_date": "2026-05-10",
                "effective_date": "2026-05-18",
                "before_shares": 80,
                "change_shares": 20,
                "after_shares": 100,
                "applied_to_share_count": False,
                "source_id": "SRC-DEMO",
            }
        ]
        with self.assertRaisesRegex(ValueError, "已生效公司行动未计入股数"):
            calculate(payload)

    def test_last_effective_action_must_match_share_class_shares(self) -> None:
        payload = self.formal_payload()
        payload["equity_bridge"]["corporate_action_review"]["actions"] = [
            {
                "security_id": "A.TEST",
                "action_type": "capitalization_issue",
                "announcement_date": "2026-05-10",
                "effective_date": "2026-05-18",
                "before_shares": 80,
                "change_shares": 20,
                "after_shares": 100,
                "applied_to_share_count": True,
                "source_id": "SRC-DEMO",
            }
        ]
        payload["equity_bridge"]["share_classes"][0]["shares"] = 80
        payload["equity_bridge"]["share_classes"][0]["reference_market_cap"] = 2000
        payload["equity_bridge"]["diluted_shares"] = 80
        with self.assertRaisesRegex(ValueError, "估值日股数未反映"):
            calculate(payload)

    def test_share_price_market_cap_reverse_check_catches_stale_shares(self) -> None:
        payload = self.formal_payload()
        row = payload["equity_bridge"]["share_classes"][0]
        row["shares"] = 80
        row["reference_market_cap"] = 2500
        payload["equity_bridge"]["diluted_shares"] = 80
        with self.assertRaisesRegex(ValueError, "股价×估值日股数与独立市值不一致"):
            calculate(payload)

    def test_formal_model_rejects_adjusted_price_or_stale_share_date(self) -> None:
        payload = self.formal_payload()
        row = payload["equity_bridge"]["share_classes"][0]
        row["price_basis"] = "adjusted_close"
        with self.assertRaisesRegex(ValueError, "不复权收盘价"):
            calculate(payload)

        payload = self.formal_payload()
        payload["equity_bridge"]["share_classes"][0]["shares_date"] = "2025-12-31"
        result = validate_calculation(payload)
        self.assertEqual(result["model_status_code"], "FAIL")
        self.assertTrue(any("估值日股数" in message for message in result["errors"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
