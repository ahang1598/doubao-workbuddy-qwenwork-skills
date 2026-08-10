#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_ROOT = ROOT / "assets/common/equity-evidence-example"
SPEC = importlib.util.spec_from_file_location("validate_equity_evidence", Path(__file__).with_name("validate_equity_evidence.py"))
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def sample() -> dict:
    return json.loads((EXAMPLE_ROOT / "equity-evidence.json").read_text(encoding="utf-8"))


class EquityEvidenceTests(unittest.TestCase):
    def test_complete_evidence_passes(self) -> None:
        self.assertTrue(MODULE.validate(sample(), EXAMPLE_ROOT)["valid"])

    def test_old_report_shares_cannot_ignore_discovered_action(self) -> None:
        payload = sample()
        bridge = payload["share_bridge"]["security_classes"][0]
        bridge["actions"] = []
        bridge["valuation_date_shares"] = bridge["baseline_shares"]
        result = MODULE.validate(payload, EXAMPLE_ROOT)
        self.assertFalse(result["valid"])
        self.assertTrue(any("action bridge" in item for item in result["errors"]))

    def test_executor_cannot_clear_both_action_lists_when_snapshot_contains_action(self) -> None:
        payload = sample()
        payload["searches"][0]["discovered_action_ids"] = []
        bridge = payload["share_bridge"]["security_classes"][0]
        bridge["actions"] = []
        bridge["valuation_date_shares"] = bridge["baseline_shares"]
        result = MODULE.validate(payload, EXAMPLE_ROOT)
        self.assertFalse(result["valid"])
        self.assertTrue(any("markers" in item for item in result["errors"]))

    def test_url_without_local_evidence_fails(self) -> None:
        payload = sample()
        payload["evidence"][0]["local_file"] = "evidence/missing.pdf"
        self.assertFalse(MODULE.validate(payload, EXAMPLE_ROOT)["valid"])

    def test_modified_evidence_hash_fails(self) -> None:
        payload = sample()
        payload["evidence"][0]["sha256"] = "0" * 64
        self.assertFalse(MODULE.validate(payload, EXAMPLE_ROOT)["valid"])

    def test_non_official_corporate_action_source_fails(self) -> None:
        payload = sample()
        payload["evidence"][2]["url"] = "https://example.com/action"
        self.assertFalse(MODULE.validate(payload, EXAMPLE_ROOT)["valid"])

    def test_search_window_must_reach_valuation_date(self) -> None:
        payload = sample()
        payload["searches"][0]["search_end_date"] = "2026-06-01"
        self.assertFalse(MODULE.validate(payload, EXAMPLE_ROOT)["valid"])

    def test_formal_task_rejects_bundled_example_evidence(self) -> None:
        payload = sample()
        payload["meta"]["model_purpose"] = "formal"
        self.assertFalse(MODULE.validate(payload, EXAMPLE_ROOT)["valid"])

    def test_path_traversal_is_rejected(self) -> None:
        payload = sample()
        payload["evidence"][0]["local_file"] = "../../outside"
        self.assertFalse(MODULE.validate(payload, EXAMPLE_ROOT)["valid"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
