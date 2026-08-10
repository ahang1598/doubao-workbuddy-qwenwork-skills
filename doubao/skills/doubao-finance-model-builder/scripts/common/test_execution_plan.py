#!/usr/bin/env python3

from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("validate_execution_plan", Path(__file__).with_name("validate_execution_plan.py"))
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def sample() -> dict:
    return json.loads((ROOT / "assets/common/execution-plan-example.json").read_text(encoding="utf-8"))


class ExecutionPlanTests(unittest.TestCase):
    def test_complete_plan_passes(self) -> None:
        self.assertTrue(MODULE.validate(sample())["valid"])

    def test_future_information_is_rejected(self) -> None:
        plan = sample()
        plan["meta"]["information_cutoff_date"] = "2026-07-01"
        result = MODULE.validate(plan)
        self.assertFalse(result["valid"])
        self.assertTrue(any("information_cutoff_date" in item for item in result["errors"]))

    def test_equity_evidence_must_be_acquired_before_bridge(self) -> None:
        plan = sample()
        plan["equity_evidence_plan"]["acquire_before_bridge"] = False
        self.assertFalse(MODULE.validate(plan)["valid"])

    def test_plan_cannot_pretend_conflicts_are_already_resolved(self) -> None:
        plan = sample()
        plan["evidence"].pop("conflict_resolution_required")
        plan["evidence"]["conflicts_resolved"] = True
        self.assertFalse(MODULE.validate(plan)["valid"])

    def test_missing_local_evidence_gate_is_rejected(self) -> None:
        plan = sample()
        plan["quality_gates"].remove("local_primary_equity_evidence")
        self.assertFalse(MODULE.validate(plan)["valid"])

    def test_scenario_sources_must_exist(self) -> None:
        plan = sample()
        plan["module_plans"]["dcf"]["scenarios"]["bull"]["source_ids"] = ["UNKNOWN"]
        result = MODULE.validate(plan)
        self.assertFalse(result["valid"])
        self.assertTrue(any("unknown source" in item for item in result["errors"]))

    def test_target_capital_structure_requires_rationale(self) -> None:
        plan = sample()
        plan["module_plans"]["dcf"]["wacc"]["basis"] = "target"
        plan["module_plans"]["dcf"]["wacc"]["rationale"] = ""
        self.assertFalse(MODULE.validate(plan)["valid"])

    def test_terminal_point_value_limit_cannot_be_relaxed(self) -> None:
        plan = sample()
        plan["module_plans"]["dcf"]["terminal_value"]["point_value_share_limit"] = 0.95
        plan["result_policy"]["point_value_terminal_share_limit"] = 0.95
        self.assertFalse(MODULE.validate(plan)["valid"])

    def test_missing_market_cap_gate_is_rejected(self) -> None:
        plan = sample()
        plan["quality_gates"].remove("market_cap_reverse_check")
        self.assertFalse(MODULE.validate(plan)["valid"])

    def test_unified_model_audit_cannot_be_omitted(self) -> None:
        plan = sample()
        plan["quality_gates"].remove("unified_model_audit")
        plan["deliverables"]["support"].remove("model-audit.json")
        result = MODULE.validate(plan)
        self.assertFalse(result["valid"])
        self.assertTrue(any("unified_model_audit" in item or "model-audit.json" in item for item in result["errors"]))

    def test_formal_plan_requires_latest_announcement_topic(self) -> None:
        plan = sample()
        plan["evidence"]["required_topics"].remove("latest_announcements")
        result = MODULE.validate(plan)
        self.assertFalse(result["valid"])
        self.assertTrue(any("latest_announcements" in item for item in result["errors"]))

    def test_formal_plan_requires_latest_announcement_gate_and_artifacts(self) -> None:
        plan = sample()
        plan["quality_gates"].remove("latest_announcement_sweep")
        plan["deliverables"]["support"].remove("announcement-sweep-validation.json")
        result = MODULE.validate(plan)
        self.assertFalse(result["valid"])
        self.assertTrue(any("latest_announcement_sweep" in item for item in result["errors"]))
        self.assertTrue(any("announcement-sweep-validation.json" in item for item in result["errors"]))

    def test_plan_does_not_need_duplicate_results(self) -> None:
        plan = copy.deepcopy(sample())
        plan["module_plans"]["dcf"].pop("terminal_value")
        result = MODULE.validate(plan)
        self.assertFalse(result["valid"])
        self.assertTrue(any("terminal_value" in item for item in result["errors"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
