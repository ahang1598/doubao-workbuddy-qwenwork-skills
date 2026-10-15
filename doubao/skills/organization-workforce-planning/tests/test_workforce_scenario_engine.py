import importlib.util
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location("workforce_runtime", ROOT / "scripts/workforce_scenario_engine.py")
TOOL = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(TOOL)


class WorkforceScenarioTest(unittest.TestCase):
    def payload(self):
        return json.loads((ROOT / "fixtures/smoke.json").read_text(encoding="utf-8"))

    def test_decimal_calculation_and_metadata(self):
        result = TOOL.calculate(self.payload())
        row = result["scenarios"][0]
        self.assertEqual(row["ending_hc"], "12")
        self.assertEqual(row["recurring_cost_delta"], "60.5")
        self.assertEqual(row["one_time_cost"], "10.2")
        self.assertEqual(result["formula_metadata"]["source_ids"], ["snapshot-a"])
        self.assertTrue(row["hc_bridge"]["complete_flow_bridge"])
        self.assertEqual(row["hc_bridge"]["hires"], "2")

    def test_missing_costs_degrade_without_zero_fill_or_crash(self):
        payload = self.payload()
        payload.pop("currency")
        payload.pop("period")
        role = payload["scenarios"][0]["role_deltas"][0]
        role.pop("recurring_unit_cost")
        role.pop("one_time_unit_cost")
        result = TOOL.calculate(payload)
        scenario = result["scenarios"][0]
        self.assertEqual(result["artifact_state"], "degraded")
        self.assertEqual(scenario["ending_hc"], "12")
        self.assertIsNone(scenario["recurring_cost_delta"])
        self.assertIsNone(scenario["one_time_cost"])
        self.assertIsNone(scenario["role_deltas"][0]["recurring_unit_cost"])
        self.assertIsNone(scenario["role_deltas"][0]["one_time_unit_cost"])
        unknown_ids = {item["unknown_id"] for item in result["unknowns"]}
        self.assertIn("unknown-scenario-a-recurring-cost", unknown_ids)
        self.assertIn("unknown-scenario-a-one-time-cost", unknown_ids)
        TOOL.validate(result)

    def test_recurring_and_one_time_cost_unknowns_are_independent(self):
        payload = self.payload()
        payload["scenarios"][0]["role_deltas"][0].pop("one_time_unit_cost")
        result = TOOL.calculate(payload)
        scenario = result["scenarios"][0]
        self.assertEqual(scenario["recurring_cost_delta"], "60.5")
        self.assertIsNone(scenario["one_time_cost"])
        self.assertIn("unknown-scenario-a-one-time-cost", {item["unknown_id"] for item in result["unknowns"]})
        TOOL.validate(result)

    def test_empty_scenarios_cannot_be_ready(self):
        payload = self.payload()
        payload["scenarios"] = []
        payload["hc_flow_breakdown"] = {}
        result = TOOL.calculate(payload)
        self.assertEqual(result["artifact_state"], "degraded")
        self.assertFalse(result["hard_gates"]["scenarios_present"])
        self.assertIn("unknown-scenarios", {item["unknown_id"] for item in result["unknowns"]})
        TOOL.validate(result)

    def test_rejects_duplicate_scenario_id(self):
        payload = self.payload()
        payload["scenarios"].append(dict(payload["scenarios"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate scenario_id"):
            TOOL.calculate(payload)

    def test_rejects_negative_hc(self):
        payload = self.payload()
        payload["scenarios"][0]["baseline_hc"] = "-1"
        with self.assertRaisesRegex(ValueError, "non-negative"):
            TOOL.calculate(payload)
        payload = self.payload()
        payload["scenarios"][0]["role_deltas"][0]["hc_delta"] = "-20"
        with self.assertRaisesRegex(ValueError, "negative ending_hc"):
            TOOL.calculate(payload)

    def test_perturbation_changes_output(self):
        first = TOOL.calculate(self.payload())["scenarios"][0]["ending_hc"]
        payload = self.payload()
        payload["scenarios"][0]["role_deltas"][0]["hc_delta"] = "3"
        payload["hc_flow_breakdown"]["scenario-a"]["hires"] = "3"
        second = TOOL.calculate(payload)["scenarios"][0]["ending_hc"]
        self.assertNotEqual(first, second)

    def test_full_package_intent_overrides_direct_default(self):
        payload = self.payload()
        payload["route"]["intent"] = "full_package"
        payload["delivery_tier"] = "direct"
        self.assertEqual(TOOL.calculate(payload)["delivery_tier"], "full")

    def test_fc39_holdout_regression_minimum_complete_degraded_pack(self):
        case_path = ROOT / "fixtures/fc39-regression.json"
        payload = json.loads(case_path.read_text(encoding="utf-8"))["runtime_input"]
        result = TOOL.calculate(payload)
        self.assertEqual(result["delivery_tier"], "full")
        self.assertEqual(result["artifact_state"], "degraded")
        unknown_fields = {item["field"] for item in result["unknowns"]}
        self.assertTrue({"capability_map", "workload_forecast", "structure_baseline", "hc_flow_breakdown"} <= unknown_fields)
        self.assertTrue(result["capability_demand"][0]["role_dependencies"])
        self.assertEqual(len(result["structure_options"]), 2)
        for option in result["structure_options"]:
            self.assertEqual(option["option_type"], "scenario_support_option_not_org_chart")
            self.assertIsNone(option["reporting_lines"])
            self.assertTrue(option["unknown_ids"])
            self.assertIn("hc_cost", option)
            self.assertIn("reversibility", option)
        for scenario in result["scenarios"]:
            bridge = scenario["hc_bridge"]
            self.assertFalse(bridge["complete_flow_bridge"])
            self.assertIsNone(bridge["hires"])
            self.assertEqual(bridge["net_delta"], scenario["hc_delta"])
        self.assertTrue(all("decision_gate" in stage and "condition" in stage for stage in result["transition_route"]))
        self.assertFalse(any("date" in stage for stage in result["transition_route"]))
        self.assertTrue(any(item["type"] == "maximum_counterpoint" for item in result["risks_and_counterpoints"]))
        raw = (json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
        compact = TOOL.compact_for(result, TOOL.FULL_ARTIFACT, hashlib.sha256(raw).hexdigest())
        self.assertEqual(compact["artifact_type"], "organization_workforce_plan_pack")
        self.assertEqual(compact["full_artifact"], "organization-workforce-plan.full.json")
        self.assertEqual(compact["compact_artifact"], "organization-workforce-plan.compact.json")
        payload_without_hash = dict(compact)
        claimed = payload_without_hash.pop("compact_payload_sha256")
        actual = hashlib.sha256(
            (json.dumps(payload_without_hash, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
        ).hexdigest()
        self.assertEqual(claimed, actual)
        TOOL.validate(result, compact, raw)

    def test_validator_recomputes_hc_cost_state_and_cost_bridge(self):
        full = TOOL.calculate(self.payload())
        mutations = []
        bad = json.loads(json.dumps(full))
        bad["scenarios"][0]["role_deltas"][0]["hc_delta"] = "3"
        mutations.append(bad)
        bad = json.loads(json.dumps(full))
        bad["scenarios"][0]["recurring_cost_delta"] = "999"
        mutations.append(bad)
        bad = json.loads(json.dumps(full))
        bad["cost_bridge"][0]["one_time_cost"] = "999"
        mutations.append(bad)
        bad = json.loads(json.dumps(full))
        bad["hard_gates"]["scenarios_present"] = False
        mutations.append(bad)
        degraded = self.payload()
        degraded["scenarios"][0]["role_deltas"][0].pop("recurring_unit_cost")
        bad = TOOL.calculate(degraded)
        bad["artifact_state"] = "ready"
        mutations.append(bad)
        for index, bad in enumerate(mutations):
            with self.subTest(index=index), self.assertRaises(ValueError):
                TOOL.validate(bad)

    def test_privacy_and_user_defined_small_group_suppression(self):
        payload = self.payload()
        payload["privacy_policy"] = {"minimum_group_size": 5}
        payload["baseline"] = {
            "teams": [{
                "team": "rare-skill-team", "group_count": 2,
                "employee_name": "Alice", "婚育状态": "未知", "turnover_rate": "0.5",
            }]
        }
        result = TOOL.calculate(payload)
        group = result["baseline"]["teams"][0]
        self.assertNotIn("employee_name", group)
        self.assertNotIn("婚育状态", group)
        self.assertIsNone(group["turnover_rate"])
        self.assertTrue(group["suppressed"])
        self.assertEqual(group["suppression_reason"], "below_user_minimum_group_size")
        self.assertEqual(result["artifact_state"], "degraded")
        self.assertTrue(result["hard_gates"]["privacy_minimized"])
        TOOL.validate(result)
        tampered = json.loads(json.dumps(result))
        tampered["baseline"]["teams"][0]["turnover_rate"] = "0.5"
        with self.assertRaisesRegex(ValueError, "small_group_unsuppressed"):
            TOOL.validate(tampered)

    def test_small_group_threshold_must_be_user_supplied_and_positive(self):
        payload = self.payload()
        payload["privacy_policy"] = {"minimum_group_size": 0}
        with self.assertRaisesRegex(ValueError, "must be positive"):
            TOOL.calculate(payload)

    def test_route_intake_capability_failure_states(self):
        payload = self.payload()
        payload["route"] = {}
        with self.assertRaisesRegex(ValueError, "malformed route"):
            TOOL.calculate(payload)
        payload = self.payload()
        payload["route"]["route_status"] = "routed"
        self.assertEqual(TOOL.calculate(payload)["artifact_state"], "routed")
        payload = self.payload()
        payload["intake"]["planning_period_and_org_scope"] = None
        self.assertEqual(TOOL.calculate(payload)["artifact_state"], "intake_required")
        payload = self.payload()
        payload["capabilities"] = {}
        with self.assertRaisesRegex(ValueError, "malformed capabilities"):
            TOOL.calculate(payload)
        payload = self.payload()
        payload["capabilities"]["missing"] = ["can_model_cost"]
        self.assertEqual(TOOL.calculate(payload)["artifact_state"], "degraded")

    def test_malformed_intake_and_source_subsets_fail_close(self):
        payload = self.payload()
        payload["intake"] = []
        with self.assertRaisesRegex(ValueError, "malformed intake"):
            TOOL.calculate(payload)
        payload = self.payload()
        payload["scenarios"][0]["role_deltas"][0]["source_ids"] = ["fabricated"]
        with self.assertRaisesRegex(ValueError, "scenario subsets"):
            TOOL.calculate(payload)

    def test_smoke_cli_hash_and_validation(self):
        with tempfile.TemporaryDirectory() as temp:
            full = Path(temp) / "full.json"
            compact = Path(temp) / "compact.json"
            subprocess.run([
                sys.executable, str(ROOT / "scripts/workforce_scenario_engine.py"), "compute",
                "--input", str(ROOT / "fixtures/smoke.json"), "--full-out", str(full), "--compact-out", str(compact)
            ], check=True)
            TOOL.validate(json.loads(full.read_text()), json.loads(compact.read_text()), full.read_bytes())

    def test_compact_bad_cases_fail(self):
        full = TOOL.calculate(self.payload())
        raw = (json.dumps(full, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
        compact = TOOL.compact_for(full, "full.json", hashlib.sha256(raw).hexdigest())
        for field, value in (
            ("source_index", ["fake"]), ("core_slots", {}), ("hard_gates", {}),
            ("full_sha256", "bad"), ("compact_payload_sha256", "bad"),
        ):
            bad = dict(compact)
            bad[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                TOOL.validate(full, bad, raw)
        same_length = json.loads(json.dumps(compact))
        same_length["scenario_summary"][0]["scenario_id"] = "scenario-b"
        with self.assertRaises(ValueError):
            TOOL.validate(full, same_length, raw)

    def test_finalizer_rejects_empty_or_clearing_ledger(self):
        draft = TOOL.calculate(self.payload())
        with self.assertRaisesRegex(ValueError, "at least one validated"):
            TOOL.finalize(draft, {"claims": []})
        ledger = {
            "claims": [{
                "claim_id": "claim-a", "source_ids": ["snapshot-a"], "validated": True,
                "final_text": "approved preview", "allowed_slots": ["action_previews"],
            }],
            "structured_values": {"scenarios": []},
        }
        with self.assertRaisesRegex(ValueError, "cannot clear"):
            TOOL.finalize(draft, ledger)

    def test_finalizer_locks_structure_cost_and_text(self):
        draft = TOOL.calculate(self.payload())
        draft["structure_options"] = [{"text": "unsupported", "source_ids": ["fabricated"]}]
        draft["cost_bridge"] = [{"amount": "999", "assumption_ids": ["fabricated"]}]
        draft["risks_and_counterpoints"] = ["unsupported text"]
        with self.assertRaises(ValueError):
            TOOL.finalize(draft, {"claims": []})

    def test_finalizer_rebuilds_ledger_value_not_evil_note(self):
        draft = TOOL.calculate(self.payload())
        draft["structure_options"] = [{"claim_ids": ["claim-a"], "text": "EVIL NOTE", "source_ids": ["snapshot-a"]}]
        approved = TOOL.calculate(self.payload())["structure_options"]
        ledger = {
            "claims": [{
                "claim_id": "claim-a", "source_ids": ["snapshot-a"], "assumption_ids": ["assumption-a"],
                "validated": True, "allowed_slots": ["structure_options"],
                "allowed_fields": {"structure_options": sorted(approved[0])},
                "structured_value": {"structure_options": approved},
            }],
        }
        final = TOOL.finalize(draft, ledger)
        self.assertEqual(final["structure_options"][0]["option_id"], "support-scenario-a")
        self.assertNotIn("EVIL NOTE", json.dumps(final))
        TOOL.validate(final)

    def test_evil_no_source_structured_value_is_deleted(self):
        draft = TOOL.calculate(self.payload())
        approved = draft["structure_options"]
        ledger = {
            "claims": [{
                "claim_id": "claim-a", "source_ids": ["snapshot-a"], "validated": True,
                "allowed_slots": ["structure_options"],
                "allowed_fields": {"structure_options": sorted(approved[0])},
                "structured_value": {"structure_options": approved},
            }],
            "structured_values": {
                "structure_options": [{"claim_id": "claim-a", "text": "EVIL-NO-SOURCE"}]
            },
        }
        final = TOOL.finalize(draft, ledger)
        self.assertNotIn("EVIL-NO-SOURCE", json.dumps(final))
        self.assertEqual(final["structure_options"][0]["option_id"], "support-scenario-a")

    def test_finalizer_preserves_untouched_core_slots(self):
        draft = TOOL.calculate(self.payload())
        ledger = {
            "claims": [{
                "claim_id": "claim-preview", "source_ids": ["snapshot-a"], "validated": True,
                "final_text": "仅供审批预览，未执行。", "allowed_slots": ["action_previews"],
            }],
        }
        final = TOOL.finalize(draft, ledger)
        self.assertEqual(final["scenarios"], draft["scenarios"])
        self.assertEqual(final["cost_bridge"], draft["cost_bridge"])
        self.assertEqual(final["structure_options"], draft["structure_options"])
        self.assertEqual(final["action_previews"][0]["text"], "仅供审批预览，未执行。")
        TOOL.validate(final)

    def test_eval_assertion_executes(self):
        case = json.loads((ROOT / "evals/evals.json").read_text())["evals"][0]
        full = TOOL.calculate(self.payload())
        raw = (json.dumps(full, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
        compact = TOOL.compact_for(full, "full.json", hashlib.sha256(raw).hexdigest())
        response = {
            "artifact_state": case["expected_state"], "delivery_tier": case["expected_tier"],
            "search_mode": case["search_mode"], "route": full["route"], "capabilities": full["capabilities"],
            "full": full, "compact": compact, "full_sha256": hashlib.sha256(raw).hexdigest(),
            "body": " ".join(case["must_include"]),
        }
        TOOL.assert_eval(case, response)
        internal_only = json.loads(json.dumps(response))
        internal_only["full"]["limitations"] = [case["must_not_include"][0]]
        internal_raw = (json.dumps(internal_only["full"], ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
        internal_only["compact"] = TOOL.compact_for(internal_only["full"], "full.json", hashlib.sha256(internal_raw).hexdigest())
        internal_only["full_sha256"] = hashlib.sha256(internal_raw).hexdigest()
        TOOL.assert_eval(case, internal_only)
        visible_forbidden = dict(response)
        visible_forbidden["body"] += " " + case["must_not_include"][0]
        with self.assertRaisesRegex(AssertionError, "forbidden user-visible"):
            TOOL.assert_eval(case, visible_forbidden)
        process_leak = dict(response)
        process_leak["body"] = "我先读取 SKILL.md，再运行脚本。"
        with self.assertRaisesRegex(AssertionError, "work log leaked"):
            TOOL.assert_eval(case, process_leak)
        for field, value in (("delivery_tier", "full"), ("search_mode", "required"), ("full_sha256", "bad")):
            bad = dict(response)
            bad[field] = value
            with self.subTest(field=field), self.assertRaises(AssertionError):
                TOOL.assert_eval(case, bad)
        for path in ("route", "capabilities", "hard_gates", "source_index"):
            bad = json.loads(json.dumps(response))
            if path == "route":
                bad["route"]["selected_skill"] = "wrong"
            elif path == "capabilities":
                bad["capabilities"] = {}
            elif path == "hard_gates":
                bad["compact"]["hard_gates"] = {}
            else:
                bad["compact"]["source_index"] = ["fake"]
            with self.subTest(path=path), self.assertRaises((AssertionError, ValueError)):
                TOOL.assert_eval(case, bad)

    def test_runtime_config_and_eval_contract_are_aligned(self):
        config = json.loads((ROOT / "config/runtime.json").read_text(encoding="utf-8"))
        evals = json.loads((ROOT / "evals/evals.json").read_text(encoding="utf-8"))
        contract = (ROOT / "references/output-contract.md").read_text(encoding="utf-8")
        self.assertEqual(config["version"], evals["version"])
        self.assertEqual(config["tool_contract"]["schema_version"], TOOL.SCHEMA)
        self.assertTrue(config["tool_contract"]["missing_costs_are_null_not_zero"])
        self.assertTrue(config["tool_contract"]["empty_scenarios_cannot_be_ready"])
        self.assertFalse(config["finalizer"]["may_clear_nonempty_core_slots"])
        self.assertEqual(config["evaluation_assertion"]["keyword_scope"], "user_visible_body_only")
        self.assertIn("privacy_policy", config["compact_tool_output"]["fields"])
        self.assertIn('"privacy_policy"', contract)
        ids = [case["id"] for case in evals["evals"]]
        self.assertEqual(len(ids), len(set(ids)))
        for case in evals["evals"]:
            for token in case.get("must_include", []):
                self.assertIsNone(TOOL.USER_VISIBLE_INTERNAL.search(token), (case["id"], token))

    def test_routed_and_intake_assertions_are_route_only(self):
        routed = json.loads((ROOT / "evals/evals.json").read_text())["evals"][6]
        response = {
            "artifact_state": "routed", "delivery_tier": "direct", "search_mode": "off",
            "route": {"selected_skill": routed["expected_route"], "intent": "single_role", "route_status": "routed"},
            "body": "job-modeling-and-selection-design",
        }
        TOOL.assert_eval(routed, response)
        with self.assertRaises(AssertionError):
            TOOL.assert_eval(routed, {**response, "compact": {}})
        TOOL.assert_eval(
            {"expected_state": "intake_required", "expected_tier": "direct", "search_mode": "off"},
            {
                "artifact_state": "intake_required", "delivery_tier": "direct", "search_mode": "off",
                "route": {"selected_skill": "organization-workforce-planning", "intent": "clarify", "route_status": "intake_required"},
                "questions": ["请提供规划范围。"],
            },
        )


if __name__ == "__main__":
    unittest.main()
