#!/usr/bin/env python3
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("pipeline_forecast", ROOT / "scripts" / "pipeline_forecast.py")
MODEL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODEL)


def claim():
    return {
        "claim_id": "c-forecast",
        "claim": "forecast snapshot truth",
        "claim_type": "fact",
        "critical": True,
        "object_id": "book-1",
        "period": "2026-Q3",
        "unit": "USD",
        "source_ids": ["crm-export"],
        "source_tier": "crm_truth",
        "confidence": "high",
        "conflict_state": "none",
    }


def payload():
    return {
        "currency": "USD",
        "period": "2026-Q3",
        "amount_basis": "contract_value",
        "stage_probabilities": {"proposal": 0.5, "negotiation": 0.8},
        "current_snapshot": [
            {"opportunity_id": "o1", "stage": "proposal", "amount": 100, "currency": "USD"},
            {"opportunity_id": "o2", "stage": "negotiation", "amount": 300, "currency": "USD"},
        ],
        "prior_snapshot": [
            {"opportunity_id": "o1", "stage": "proposal", "amount": 80, "currency": "USD"},
            {"opportunity_id": "o2", "stage": "proposal", "amount": 300, "currency": "USD"},
        ],
        "claims": [claim()],
        "gate_context": {
            "required_artifacts": ["forecast_full_json", "forecast_compact_json", "claim_ledger"],
            "permission_requests": [{"action": "analyze"}],
        },
    }


class PipelineForecastTest(unittest.TestCase):
    def test_rollup_movement_concentration(self):
        full, compact = MODEL.calculate(payload())
        self.assertEqual(full["total_amount"], 400)
        self.assertEqual(full["weighted_total"], 290)
        self.assertEqual(full["movement"]["status"], "evaluated")
        self.assertEqual(full["concentration"]["largest_amount"], 300)
        self.assertEqual(full["concentration"]["amount_ex_largest"], 100)
        self.assertTrue(full["set_conservation"]["passed"])
        self.assertEqual(compact["core_results"]["total_amount"], 400)

    def test_amount_perturbation_changes_outputs(self):
        data = payload()
        data["current_snapshot"][0]["amount"] = 200
        full, _ = MODEL.calculate(data)
        self.assertEqual(full["total_amount"], 500)
        self.assertEqual(full["concentration"]["amount_ex_largest"], 200)

    def test_snapshot_and_probability_unknowns(self):
        data = payload()
        data.pop("prior_snapshot")
        data["stage_probabilities"].pop("proposal")
        full, compact = MODEL.calculate(data)
        self.assertEqual(full["movement"]["status"], "not_evaluated")
        self.assertIsNone(full["weighted_total"])
        self.assertEqual(compact["artifact_state"], "degraded")

    def test_duplicate_preserves_input_set(self):
        data = payload()
        data["current_snapshot"].append(dict(data["current_snapshot"][0]))
        full, _ = MODEL.calculate(data)
        self.assertEqual(full["set_conservation"]["input_count"], 3)
        self.assertEqual(full["set_conservation"]["row_audit_count"], 3)
        self.assertEqual(full["set_conservation"]["unknown_or_duplicate_count"], 1)

    def test_full_compact_hash_gate_and_finalizer(self):
        with tempfile.TemporaryDirectory() as directory:
            full, compact = MODEL.calculate(payload(), Path(directory))
            self.assertTrue(Path(compact["full_artifact_path"]).exists())
            self.assertTrue(full["gates"]["artifact_gate"]["passed"])
            self.assertEqual(len(full["artifact_receipts"]), 4)
            self.assertEqual(
                MODEL.file_sha256(Path(compact["full_artifact_path"])),
                compact["full_sha256"],
            )
        data = payload()
        data["gate_context"]["permission_requests"] = [{"action": "write", "preview": True}]
        gates = MODEL.run_gates(data, ["forecast_full_json", "forecast_compact_json", "claim_ledger"])
        self.assertEqual(gates["artifact_state"], "confirmation_required")
        approved = {"claims": [claim()], "source_ids": ["s1"], "object_ids": ["o1"], "numeric_values": [1]}
        candidate = dict(approved, numeric_values=[1, 2])
        self.assertFalse(MODEL.finalize({"approved_context": approved, "candidate": candidate})["accepted"])

    def test_probability_must_be_between_zero_and_one(self):
        data = payload()
        data["stage_probabilities"]["proposal"] = 1.2
        full, compact = MODEL.calculate(data)
        self.assertIsNone(full["weighted_total"])
        self.assertEqual(compact["artifact_state"], "degraded")
        self.assertIn("probability_missing_or_out_of_range_0_1", {item.get("reason") for item in compact["unknowns"]})

    def test_claim_schema_and_fixed_artifacts(self):
        data = payload()
        data["claims"] = []
        full, _ = MODEL.calculate(data)
        self.assertFalse(full["gates"]["claim_gate"]["passed"])
        gates = MODEL.run_gates(data, ["claim_ledger"])
        self.assertFalse(gates["claim_gate"]["passed"])
        self.assertFalse(gates["artifact_gate"]["passed"])
        rejected = MODEL.finalize({
            "approved_context": {"claims": [], "source_ids": [], "object_ids": [], "numeric_values": []},
            "candidate": {"claims": [], "source_ids": [], "object_ids": [], "numeric_values": []},
        })
        self.assertFalse(rejected["accepted"])
        invalid = claim()
        invalid["extra"] = "not allowed"
        data["claims"] = [invalid]
        gates = MODEL.run_gates(data, MODEL.REQUIRED_ARTIFACTS)
        self.assertFalse(gates["claim_gate"]["passed"])

    def test_artifact_receipt_bad_cases(self):
        with tempfile.TemporaryDirectory() as directory:
            data = payload()
            full, _ = MODEL.calculate(data, Path(directory))
            receipts = [dict(item) for item in full["artifact_receipts"]]
            self.assertFalse(MODEL.run_gates(data, receipts[:-1])["artifact_gate"]["passed"])
            Path(receipts[0]["path"]).unlink()
            self.assertFalse(MODEL.run_gates(data, receipts)["artifact_gate"]["passed"])
        with tempfile.TemporaryDirectory() as directory:
            data = payload()
            full, _ = MODEL.calculate(data, Path(directory))
            receipts = [dict(item) for item in full["artifact_receipts"]]
            receipts[0]["expected_sha256"] = "f" * 64
            self.assertFalse(MODEL.run_gates(data, receipts)["artifact_gate"]["passed"])

    def test_artifact_count_inconsistency_fails_even_with_new_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            data = payload()
            full, _ = MODEL.calculate(data, Path(directory))
            receipts = [dict(item) for item in full["artifact_receipts"]]
            target = receipts[1]
            artifact = json.loads(Path(target["path"]).read_text())
            artifact["manifest"]["counts"]["records"] += 1
            MODEL.write_json(Path(target["path"]), artifact)
            target["expected_sha256"] = MODEL.file_sha256(Path(target["path"]))
            self.assertFalse(MODEL.run_gates(data, receipts)["artifact_gate"]["passed"])

    def test_constraint_order_blocks_contact_before_signal_ranking(self):
        result = MODEL.prioritize_accounts({
            "channel_capacities": {"sdr": 1},
            "accounts": [
                {"account_id": "A-02", "owner": None, "owner_verified": False, "signal": "high", "channel": "sdr"},
                {"account_id": "A-31", "owner": "rep-1", "owner_verified": True, "owner_conflict": True, "signal": "high", "channel": "sdr"},
                {"account_id": "A-32", "owner": "rep-2", "owner_verified": True, "suppressed": True, "signal": "high", "channel": "sdr"},
                {"account_id": "A-33", "owner": "rep-3", "owner_verified": True, "active_opportunity": True, "signal": "high", "channel": "sdr"},
                {
                    "account_id": "A-35", "owner": "rep-5", "owner_verified": True,
                    "suppressed": False, "active_opportunity": False,
                    "signal": "medium", "channel": "sdr",
                },
            ],
        })
        actions = {row["account_id"]: row for row in result["decisions"]}
        self.assertEqual(actions["A-02"]["action"], "internal_verification")
        self.assertEqual(actions["A-31"]["action"], "internal_coordination")
        self.assertFalse(actions["A-32"]["contact_allowed"])
        self.assertFalse(actions["A-33"]["contact_allowed"])
        self.assertEqual(result["selected_for_outreach"], ["A-35"])
        self.assertEqual(actions["A-35"]["constraint_order"], list(MODEL.CONSTRAINT_ORDER))

    def test_unknown_hard_constraints_never_allow_outreach(self):
        base = {
            "account_id": "A-1", "owner": "rep-1", "owner_verified": True,
            "signal": "high", "channel": "sdr",
        }
        cases = (
            ({**base, "active_opportunity": False}, "suppression_unknown"),
            ({**base, "suppressed": False}, "active_opportunity_unknown"),
            ({**base, "suppressed": False, "active_opportunity": False}, "channel_capacity_unknown_or_invalid"),
        )
        for account, reason in cases:
            with self.subTest(reason=reason):
                result = MODEL.prioritize_accounts({"accounts": [account]})
                self.assertEqual(result["selected_for_outreach"], [])
                self.assertEqual(result["decisions"][0]["reason"], reason)

    def test_channel_plan_requires_explicit_constraints_capacity_and_total_budget(self):
        result = MODEL.validate_channel_plan({
            "accounts": [{
                "account_id": "A-1", "owner": "rep-1", "owner_verified": True,
                "suppressed": False,
            }],
            "channels": [{"channel": "sdr", "account_ids": ["A-1"], "budget": 100}],
        })
        self.assertFalse(result["final_plan_allowed"])
        self.assertIn("channels[0] missing capacity", result["failures"])
        self.assertIn("missing expected total budget", result["failures"])
        self.assertEqual(result["channels"][0]["unavailable_account_ids"], ["A-1"])

    def test_crm_changes_remain_proposals_without_completion_evidence(self):
        safe = MODEL.validate_crm_actions([
            {"object_id": "O014", "current_state": "approval_record_not_seen",
             "proposed_action": "write_crm", "approval_required": True,
             "completion_evidence": [], "execution_state": "proposed"},
            {"object_id": "M017", "current_state": "unknown",
             "proposed_action": "create_opportunity", "approval_required": True,
             "completion_evidence": [], "execution_state": "proposed"},
        ])
        self.assertTrue(safe["passed"])
        unsafe = MODEL.validate_crm_actions([
            {"object_id": "M017", "current_state": "unknown",
             "proposed_action": "create_opportunity", "approval_required": True,
             "completion_evidence": [], "execution_state": "executed"},
        ])
        self.assertFalse(unsafe["passed"])

    def test_o24_stage_sensitivity_distinguishes_each_step_and_endpoint(self):
        result = MODEL.stage_sensitivity(
            1500000,
            ["discovery", "evaluation", "negotiation"],
            {"discovery": 0.2, "evaluation": 0.5, "negotiation": 0.75},
        )
        self.assertTrue(result["passed"])
        self.assertEqual([row["delta"] for row in result["adjacent_deltas"]], [450000, 375000])
        self.assertEqual(result["endpoint_delta"], 825000)

    def test_case_04_known_mapped_forecast_attainment_and_gap(self):
        data = payload()
        data["quota"] = 3000000
        data["stage_probabilities"] = {"D": 0.75, "E": 0.5, "F": 0.2}
        data["current_snapshot"] = [
            {"opportunity_id": "D1", "stage": "D", "amount": 1200000, "currency": "USD"},
            {"opportunity_id": "E1", "stage": "E", "amount": 900000, "currency": "USD"},
            {"opportunity_id": "F1", "stage": "F", "amount": 600000, "currency": "USD"},
        ]
        data["prior_snapshot"] = []
        full, _ = MODEL.calculate(data)
        self.assertEqual(full["forecast_metrics"]["known_mapped_forecast"], 1470000)
        self.assertAlmostEqual(full["forecast_metrics"]["known_mapped_attainment"], 0.49)
        self.assertEqual(full["forecast_metrics"]["known_mapped_attainment_percent"], 49.0)
        self.assertEqual(full["forecast_metrics"]["known_mapped_gap"], 1530000)
        self.assertEqual(full["concentration"]["top1_share"], 1200000 / 2700000)

    def test_channel_capacity_suppression_and_budget_are_hard_checks(self):
        accounts = [
            {"account_id": f"ABM-{index}", "owner": "abm-owner", "owner_verified": True, "suppressed": True}
            for index in range(1, 8)
        ] + [
            {"account_id": f"P-{index}", "owner": "partner-owner", "owner_verified": True}
            for index in range(1, 21)
        ]
        result = MODEL.validate_channel_plan({
            "accounts": accounts,
            "expected_total_budget": 530000,
            "channels": [
                {"channel": "ABM", "account_ids": [f"ABM-{index}" for index in range(1, 8)], "capacity": 7, "budget": 300000},
                {"channel": "partner", "account_ids": [f"P-{index}" for index in range(1, 21)], "capacity": 20, "budget": 230000},
            ],
        })
        self.assertEqual(result["channels"][0]["account_count"], 7)
        self.assertEqual(result["channels"][0]["unavailable_count"], 7)
        self.assertLessEqual(result["channels"][1]["account_count"], 20)
        self.assertEqual(result["total_budget"], 530000)
        self.assertFalse(result["final_plan_allowed"])

    def test_funnel_denominators_and_ctr_causality(self):
        result = MODEL.calculate_funnel_metrics({
            "overall": {"inquiries": 17, "valid_leads": 11, "spend": 318, "target_valid_leads": 12, "intent_grade_count": 14},
            "channels": [{"channel": "Alibaba", "inquiries": 7, "valid_leads": 4}],
        })
        self.assertTrue(result["passed"])
        self.assertAlmostEqual(result["overall"]["valid_rate"], 11 / 17)
        self.assertEqual(result["overall"]["valid_rate_percent"], 64.7)
        self.assertAlmostEqual(result["channels"]["Alibaba"]["valid_rate"], 4 / 7)
        self.assertEqual(result["channels"]["Alibaba"]["valid_rate_percent"], 57.1)
        self.assertEqual(result["overall"]["cpl"], 28.91)
        self.assertEqual(result["overall"]["target_cpl"], 26.5)
        self.assertFalse(result["intent_grade_is_valid_lead"])
        invalid = MODEL.calculate_funnel_metrics({
            "overall": {"inquiries": 17, "valid_leads": 11},
            "ctr_as_current_valid_lead_cause": True,
        })
        self.assertFalse(invalid["passed"])
        self.assertEqual(invalid["ctr_treatment"], "future_experiment_only")

    def test_event_cutoffs_are_separate_and_sample_is_not_population(self):
        result = MODEL.analyze_event_cutoffs({
            "events": [{
                "record_id": "L018",
                "start_at": "2026-08-01T09:00:00",
                "alert_at": "2026-08-01T11:00:00",
                "freeze_at": "2026-08-01T15:30:00",
            }],
            "sample_size": 1,
            "population_size": 20,
        })
        self.assertEqual(result["events"][0]["hours_to_alert"], 2)
        self.assertEqual(result["events"][0]["hours_to_final_freeze"], 6.5)
        self.assertEqual(result["events"][0]["start_at"], "2026-08-01T09:00:00")
        self.assertFalse(result["population_conclusion_allowed"])
        self.assertEqual(result["sample_conclusion"], "current_sample_only")

    def test_event_cutoffs_reject_reverse_timestamps(self):
        result = MODEL.analyze_event_cutoffs({
            "events": [{
                "record_id": "L018",
                "start_at": "2026-08-01T12:00:00",
                "alert_at": "2026-08-01T11:00:00",
                "freeze_at": "2026-08-01T15:30:00",
            }],
            "sample_size": 1,
            "population_size": 1,
        })
        self.assertFalse(result["passed"])
        self.assertEqual(result["events"], [])
        self.assertFalse(result["population_conclusion_allowed"])

    def test_user_visible_linter_blocks_internal_protocol(self):
        good = (
            "结论：本周管道预测只采用组织给定概率。账户行动清单按归属、抑制和容量先筛选。"
            "依据：CRM冻结快照。风险与待确认：一笔阶段未知，不纳入完整预测。"
            "下一步：先做内部核验，再由负责人审核外联草稿。"
        )
        self.assertTrue(MODEL.lint_user_visible(good)["passed"])
        bad = good + " artifact_state=ready，claim_gate通过，已写回CRM。"
        self.assertFalse(MODEL.lint_user_visible(bad)["passed"])

    def test_user_visible_linter_rejects_long_attachment_substitution_and_execution_narration(self):
        attachment_only = (
            "结论：本次给出账户与管道建议。账户与预测依据来自CRM。风险和待确认事项已经整理，"
            "下一步建议负责人核验。为避免正文过长，完整主工件请见附件，附件中包含全部外联和行动清单。"
        )
        narration = (
            "结论：已运行 scripts/pipeline_forecast.py，state=ready。账户与预测依据来自CRM，"
            "风险与待确认项如下，下一步由负责人内部核验后再决定是否外联。"
        )
        self.assertFalse(MODEL.lint_user_visible(attachment_only)["passed"])
        self.assertFalse(MODEL.lint_user_visible(narration)["passed"])

    def test_unknown_permission_action_is_not_allowed_and_stops_gate(self):
        permission = MODEL.evaluate_permissions([{"action": "bulk_export_contacts"}])
        self.assertFalse(permission["passed"])
        self.assertEqual(permission["execution"], "not_executed")
        data = payload()
        data["gate_context"]["permission_requests"] = [{"action": "bulk_export_contacts"}]
        self.assertEqual(MODEL.run_gates(data, [])["artifact_state"], "stopped")

    def test_sensitivity_is_bound_to_current_snapshot_amount(self):
        data = payload()
        data["stage_sensitivity"] = [{
            "opportunity_id": "o1",
            "amount": 999,
            "candidate_stages": ["proposal", "negotiation"],
        }]
        full, compact = MODEL.calculate(data)
        result = full["stage_sensitivity"]["o1"]
        self.assertFalse(result["passed"])
        self.assertEqual(result["snapshot_amount"], 100)
        self.assertIn("amount_does_not_match_current_snapshot", result["failures"])
        self.assertEqual(compact["artifact_state"], "degraded")

    def test_invalid_prior_snapshot_blocks_movement_instead_of_marking_new(self):
        data = payload()
        data["prior_snapshot"][0]["currency"] = "EUR"
        full, compact = MODEL.calculate(data)
        self.assertEqual(full["movement"]["status"], "not_evaluated_invalid_prior")
        self.assertEqual(full["movement"]["rows"], [])
        self.assertEqual(compact["artifact_state"], "degraded")

    def test_finalizer_locks_claim_content_and_requires_inline_output(self):
        visible = (
            "结论：当前管道判断仅依据已批准材料。账户行动清单保留负责人审核，"
            "依据与来源均可追溯。风险与待确认项未被改写。下一步先内部核验，再决定是否外联。"
            "本次不扩张账户集合，不把未证实信号写成事实，并保留负责人复核入口。"
        )
        approved = {
            "claims": [claim()], "source_ids": ["crm-export"],
            "object_ids": ["book-1"], "numeric_values": [],
        }
        candidate = {
            "claims": [claim()], "source_ids": ["crm-export"],
            "object_ids": ["book-1"], "numeric_values": [],
            "user_visible_text": visible,
        }
        self.assertTrue(MODEL.finalize({"approved_context": approved, "candidate": candidate})["accepted"])
        changed = json.loads(json.dumps(candidate))
        changed["claims"][0]["claim"] = "different forecast truth"
        result = MODEL.finalize({"approved_context": approved, "candidate": changed})
        self.assertFalse(result["accepted"])
        self.assertEqual(result["checks"]["claim_content"]["changed"], ["c-forecast"])
        without_text = dict(candidate)
        without_text.pop("user_visible_text")
        self.assertFalse(MODEL.finalize({"approved_context": approved, "candidate": without_text})["accepted"])

    def test_calculate_synchronizes_final_state_across_outputs(self):
        full, compact = MODEL.calculate(payload())
        self.assertEqual(full["manifest"]["artifact_state"], full["gates"]["artifact_state"])
        self.assertEqual(compact["artifact_state"], full["gates"]["artifact_state"])
        self.assertEqual(compact["manifest"]["artifact_state"], full["gates"]["artifact_state"])

    def test_runtime_and_evals_separate_internal_from_user_contract(self):
        runtime = json.loads((ROOT / "config" / "runtime.json").read_text())
        evals = json.loads((ROOT / "evals" / "evals.json").read_text())
        self.assertTrue(runtime["state_contract"]["internal_only"])
        self.assertTrue(runtime["route_contract"]["internal_only"])
        self.assertTrue((ROOT / runtime["deliverable_validator"]).exists())
        self.assertNotIn("period_and_scope", runtime["intake_required_inputs"]["blocking"])
        self.assertNotIn("router", runtime["search_runtime"])
        self.assertNotIn("evidence_validator", runtime["search_runtime"])
        self.assertIn("prompt_only_fallback", runtime["deterministic_tool"])
        forbidden = {item.lower() for item in evals["user_visible_checks"]["forbidden_tokens"]}
        for case in evals["evals"]:
            for phrase in case.get("must_include", []):
                self.assertNotIn(phrase.lower(), forbidden, case["id"])


if __name__ == "__main__":
    unittest.main()
