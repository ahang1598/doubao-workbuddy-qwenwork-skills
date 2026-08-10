#!/usr/bin/env python3
"""Regression tests for comps analytical completion gates."""

from __future__ import annotations

import copy
import unittest
from pathlib import Path

from calculate_comps import calculate
from render_comps_report import render


def company(ticker: str, classification: str, price: float, equity: float) -> dict:
    payload = {
        "name": ticker,
        "ticker": ticker,
        "classification": classification,
        "price": price,
        "diluted_shares": 100,
        "price_date": "2026-06-30",
        "price_basis": "unadjusted_close",
        "share_count_date": "2026-06-30",
        "reference_market_cap": price * 100,
        "market_cap_date": "2026-06-30",
        "market_cap_source_id": "SRC-1",
        "market_cap_tolerance_pct": 0.02,
        "corporate_action_review": {
            "baseline_share_date": "2026-03-31",
            "search_start_date": "2026-03-31",
            "reviewed_through_date": "2026-06-30",
            "source_ids": ["SRC-1"],
            "no_unrecorded_actions_confirmed": True,
            "actions": [],
        },
        "balance_sheet_date": "2026-03-31",
        "balance_sheet_publication_date": "2026-04-30",
        "debt": 0,
        "cash": 0,
        "preferred_equity": 0,
        "noncontrolling_interest": 0,
        "debt_like_adjustments": 0,
        "non_operating_investments": 0,
        "ltm_net_income": 100,
        "common_equity": equity,
        "book_value_shares": 100,
        "average_common_equity": equity,
        "dividends": [],
        "field_sources": {
            "price": "SRC-1",
            "diluted_shares": "SRC-1",
            "capital_structure": "SRC-1",
            "primary_fundamentals": "SRC-1",
            "corporate_actions": "SRC-1",
            "market_cap_cross_check": "SRC-1",
        },
    }
    if classification != "Target":
        payload["field_sources"]["peer_analysis"] = "SRC-1"
        payload.update(
            {
                "peer_role": "Commercial Core",
                "selection_rationale": "产品、客户和商业模式可比",
                "classification_rationale": "满足核心评分和数据质量门槛",
                "metric_rationale": "采用P/B并结合ROE解释差异",
                "data_quality": "Pass",
                "peer_scores": {
                    "business_overlap": 5,
                    "business_model": 4,
                    "revenue_structure": 4,
                    "market_cap_band": 4,
                },
            }
        )
    return payload


def sample_payload() -> dict:
    return {
        "valuation_date": "2026-06-30",
        "currency": "CNY",
        "unit": "millions",
        "output_mode": "decision-brief",
        "data_tier": "B",
        "source_ledger": [
            {"source_id": "SRC-1", "publication_date": "2026-06-30"}
        ],
        "target_ticker": "TARGET",
        "valuation_profile": {
            "industry": "bank",
            "economic_model": "bank",
            "stage": "mature",
            "primary_metrics": ["price_to_book"],
            "secondary_metrics": ["ltm_pe"],
            "rejected_metrics": ["ltm_ev_ebitda"],
        },
        "companies": [
            company("TARGET", "Target", 10, 1000),
            company("CORE1", "Core", 11, 1000),
            company("CORE2", "Core", 12, 1000),
            company("CORE3", "Core", 13, 1000),
        ],
        "analysis_summary": {
            "conclusion": "目标公司相对核心同行处于合理区间",
            "peer_comparison": "增长、盈利、现金转化和风险逐项比较完成",
            "premium_discount_rationale": "未给予无依据溢价",
            "invalidation_conditions": ["资产质量恶化", "ROE下降", "资本补充超预期"],
        },
    }


class CompsQualityTests(unittest.TestCase):
    def test_delivery_docs_make_excel_primary(self) -> None:
        skill_root = Path(__file__).resolve().parents[2]
        workflow = (skill_root / "references" / "workflow-comps.md").read_text(
            encoding="utf-8"
        )
        modes = (skill_root / "references" / "comps-output-modes.md").read_text(
            encoding="utf-8"
        )
        combined = workflow + "\n" + modes
        self.assertIn("默认只交付一个", combined)
        self.assertIn("用户明确要求", combined)
        self.assertIn("不得替代Excel", combined)
        self.assertNotIn("产物为飞书文档", combined)
        self.assertNotIn("最终产物均以飞书文档形式交付", combined)

    def test_complete_analysis_passes(self) -> None:
        result = calculate(sample_payload())
        self.assertEqual(result["meta"]["model_status_code"], "PASS")
        report = render(result, "decision-brief")
        self.assertIn("目标公司相对核心同行处于合理区间", report)

    def test_missing_analysis_blocks_valuation_conclusion(self) -> None:
        payload = sample_payload()
        payload.pop("analysis_summary")
        result = calculate(payload)
        self.assertEqual(result["meta"]["model_status_code"], "INCOMPLETE")
        report = render(result, "decision-brief")
        self.assertIn("不得输出推荐倍数或目标价", report)
        self.assertIn("未输出（分析质量门未通过）", report)

    def test_missing_peer_rationale_is_incomplete(self) -> None:
        payload = sample_payload()
        payload["companies"][1].pop("selection_rationale")
        result = calculate(payload)
        self.assertEqual(result["meta"]["model_status_code"], "INCOMPLETE")
        self.assertTrue(any("候选池纳入理由" in issue for issue in result["blocking_issues"]))

    def test_nonempty_ledger_does_not_replace_field_mapping(self) -> None:
        payload = sample_payload()
        payload["companies"][0]["field_sources"] = {}
        result = calculate(payload)
        self.assertEqual(result["meta"]["model_status_code"], "INCOMPLETE")
        self.assertTrue(any("字段来源映射" in issue for issue in result["blocking_issues"]))

    def test_incomplete_report_suppresses_scenarios_and_sensitivity(self) -> None:
        payload = sample_payload()
        payload.pop("analysis_summary")
        payload["scenarios"] = [{"name": "基准", "metric": "price_to_book", "anchor": 1.2, "fundamental": 10.0}]
        payload["sensitivity"] = {"metric": "price_to_book", "anchors": [1.0, 1.2], "fundamentals": [9.0, 10.0]}
        result = calculate(payload)
        report = render(result, "decision-brief")
        self.assertEqual(result["meta"]["model_status_code"], "INCOMPLETE")
        self.assertIn("估值输出已阻断", report)
        self.assertNotIn("**12.00**", report)
        self.assertNotIn("## 二维敏感性", report)

    def test_stale_share_count_date_is_rejected(self) -> None:
        payload = sample_payload()
        payload["companies"][0]["share_count_date"] = "2025-12-31"
        with self.assertRaisesRegex(ValueError, "share_count_date must equal valuation_date"):
            calculate(payload)

    def test_market_cap_reverse_check_catches_wrong_shares(self) -> None:
        payload = sample_payload()
        payload["companies"][0]["reference_market_cap"] = 1250
        with self.assertRaisesRegex(ValueError, "does not reconcile to independent market cap"):
            calculate(payload)

    def test_effective_corporate_action_must_be_applied(self) -> None:
        payload = sample_payload()
        payload["companies"][0]["corporate_action_review"]["actions"] = [
            {
                "announcement_date": "2026-05-10",
                "effective_date": "2026-05-18",
                "before_shares": 80,
                "change_shares": 20,
                "after_shares": 100,
                "applied_to_share_count": False,
                "source_id": "SRC-1",
            }
        ]
        with self.assertRaisesRegex(ValueError, "effective corporate action was not applied"):
            calculate(payload)


if __name__ == "__main__":
    unittest.main(verbosity=2)
