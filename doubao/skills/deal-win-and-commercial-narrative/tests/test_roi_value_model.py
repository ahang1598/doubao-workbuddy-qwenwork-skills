#!/usr/bin/env python3
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("roi_value_model", ROOT / "scripts" / "roi_value_model.py")
MODEL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODEL)


def claim():
    return {
        "claim_id": "c-value",
        "claim": "customer value inputs",
        "claim_type": "fact",
        "critical": True,
        "object_id": "deal-1",
        "period": "12m",
        "unit": "CNY",
        "source_ids": ["customer-workbook"],
        "source_tier": "customer_primary",
        "confidence": "high",
        "conflict_state": "none",
    }


def payload():
    return {
        "object_id": "deal-1",
        "currency": "CNY",
        "period": "12m",
        "scenarios": {
            name: {
                "benefit_drivers": [
                    {
                        "driver_id": "time",
                        "quantity": quantity,
                        "unit_value": 10,
                        "realization_rate": rate,
                    }
                ],
                "costs": [{"cost_id": "subscription", "amount": 100}],
            }
            for name, quantity, rate in (
                ("low", 20, 0.5),
                ("base", 30, 0.5),
                ("high", 40, 0.5),
            )
        },
        "claims": [claim()],
        "gate_context": {
            "required_artifacts": ["roi_full_json", "roi_compact_json", "claim_ledger"],
            "permission_requests": [{"action": "draft"}],
        },
    }


class RoiValueModelTest(unittest.TestCase):
    def test_scenarios_and_perturbation(self):
        full, _ = MODEL.calculate(payload())
        self.assertEqual(full["results"]["low"]["net_value"], 0)
        self.assertEqual(full["results"]["base"]["net_value"], 50)
        self.assertEqual(full["results"]["high"]["net_value"], 100)
        changed = payload()
        changed["scenarios"]["base"]["benefit_drivers"][0]["quantity"] = 60
        changed_full, _ = MODEL.calculate(changed)
        self.assertEqual(changed_full["results"]["base"]["net_value"], 200)

    def test_unknown_propagates(self):
        data = payload()
        data["scenarios"]["base"]["benefit_drivers"][0]["unit_value"] = None
        full, compact = MODEL.calculate(data)
        self.assertIsNone(full["results"]["base"]["roi"])
        self.assertEqual(full["results"]["base"]["status"], "unknown")
        self.assertTrue(compact["unknowns"])

    def test_full_compact_and_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            full, compact = MODEL.calculate(payload(), Path(directory))
            self.assertTrue(Path(compact["full_artifact_path"]).is_file())
            self.assertTrue(full["gates"]["artifact_gate"]["passed"])
            self.assertEqual(len(full["artifact_receipts"]), 4)
            self.assertEqual(
                MODEL.file_sha256(Path(compact["full_artifact_path"])),
                compact["full_sha256"],
            )

    def test_claim_artifact_permission_gates(self):
        data = payload()
        data["gate_context"]["permission_requests"] = [{"action": "send", "preview": True}]
        gates = MODEL.run_gates(data, ["roi_full_json", "roi_compact_json", "claim_ledger"])
        self.assertEqual(gates["artifact_state"], "confirmation_required")
        weak = payload()
        weak["claims"][0]["source_ids"] = []
        gates = MODEL.run_gates(weak, ["roi_full_json", "roi_compact_json", "claim_ledger"])
        self.assertFalse(gates["claim_gate"]["passed"])

    def test_source_locked_finalizer(self):
        approved_claim = claim()
        approved = {
            "claims": [approved_claim],
            "source_ids": ["s1"],
            "object_ids": ["o1"],
            "numeric_values": [10],
        }
        ok = MODEL.finalize({"approved_context": approved, "candidate": approved})
        self.assertTrue(ok["accepted"])
        bad = dict(approved)
        bad["numeric_values"] = [10, 11]
        rejected = MODEL.finalize({"approved_context": approved, "candidate": bad})
        self.assertFalse(rejected["accepted"])

    def test_empty_and_invalid_claim_schema_fail(self):
        data = payload()
        data["claims"] = []
        full, _ = MODEL.calculate(data)
        self.assertFalse(full["gates"]["claim_gate"]["passed"])
        gates = MODEL.run_gates(data, MODEL.REQUIRED_ARTIFACTS)
        self.assertFalse(gates["claim_gate"]["passed"])
        rejected = MODEL.finalize({
            "approved_context": {"claims": [], "source_ids": [], "object_ids": [], "numeric_values": []},
            "candidate": {"claims": [], "source_ids": [], "object_ids": [], "numeric_values": []},
        })
        self.assertFalse(rejected["accepted"])
        invalid = claim()
        invalid.pop("period")
        invalid["unexpected"] = True
        data["claims"] = [invalid]
        gates = MODEL.run_gates(data, MODEL.REQUIRED_ARTIFACTS)
        self.assertFalse(gates["claim_gate"]["passed"])

    def test_required_artifacts_cannot_be_shrunk_by_caller(self):
        with tempfile.TemporaryDirectory() as directory:
            data = payload()
            data["gate_context"]["required_artifacts"] = []
            full, _ = MODEL.calculate(data, Path(directory))
            receipts = full["artifact_receipts"]
            gates = MODEL.run_gates(data, receipts[:-1])
            self.assertFalse(gates["artifact_gate"]["passed"])
            self.assertEqual(set(gates["artifact_gate"]["required"]), MODEL.REQUIRED_ARTIFACTS)

    def test_artifact_receipt_missing_file_and_bad_hash_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            data = payload()
            full, _ = MODEL.calculate(data, Path(directory))
            missing = [dict(item) for item in full["artifact_receipts"]]
            Path(missing[0]["path"]).unlink()
            self.assertFalse(MODEL.run_gates(data, missing)["artifact_gate"]["passed"])
        with tempfile.TemporaryDirectory() as directory:
            full, _ = MODEL.calculate(payload(), Path(directory))
            bad_hash = [dict(item) for item in full["artifact_receipts"]]
            bad_hash[0]["expected_sha256"] = "0" * 64
            self.assertFalse(MODEL.run_gates(payload(), bad_hash)["artifact_gate"]["passed"])

    def test_artifact_state_inconsistency_fails_even_with_new_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            data = payload()
            full, _ = MODEL.calculate(data, Path(directory))
            receipts = [dict(item) for item in full["artifact_receipts"]]
            target = receipts[1]
            artifact = json.loads(Path(target["path"]).read_text())
            artifact["manifest"]["artifact_state"] = "degraded"
            MODEL.write_json(Path(target["path"]), artifact)
            target["expected_sha256"] = MODEL.file_sha256(Path(target["path"]))
            self.assertFalse(MODEL.run_gates(data, receipts)["artifact_gate"]["passed"])


if __name__ == "__main__":
    unittest.main()
