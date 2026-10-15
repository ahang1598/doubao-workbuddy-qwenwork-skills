import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "shortlist_evidence_tool", ROOT / "scripts" / "shortlist_evidence_tool.py"
)
TOOL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TOOL)


def load_fixture():
    return json.loads(
        (ROOT / "tests" / "fixtures" / "shortlist-evidence.json").read_text(encoding="utf-8")
    )


class ShortlistEvidenceToolTest(unittest.TestCase):
    def test_unknown_does_not_enter_eligible_shortlist(self):
        with tempfile.TemporaryDirectory() as directory:
            result = TOOL.run(load_fixture(), directory)
            self.assertEqual([item["candidate_id"] for item in result["full"]["eligible"]], ["C-001"])
            self.assertEqual(result["full"]["pending_unknown"][0]["candidate_id"], "C-002")
            self.assertEqual(result["compact"]["full_sha256"], result["full_sha256"])
            self.assertTrue(TOOL.validate_artifacts(
                Path(result["artifacts"]["full"]), Path(result["artifacts"]["compact"])
            )["pass"])

    def test_evidence_perturbation_changes_hash_and_eligibility(self):
        payload = load_fixture()
        baseline = TOOL.run(payload)
        changed = copy.deepcopy(payload)
        changed["candidates"][1]["evidence"].append({
            "criterion": "delivery",
            "observed_value": "launched",
            "source_locator": "profile:project-2",
        })
        changed["claims"][1].update({
            "claim_type": "fact",
            "source_ids": ["profile:work-1", "profile:project-2"],
            "source_tier": "primary",
            "confidence": "medium",
        })
        perturbed = TOOL.run(changed)
        self.assertNotEqual(baseline["full_sha256"], perturbed["full_sha256"])
        self.assertEqual(len(perturbed["full"]["eligible"]), 2)

    def test_duplicate_and_protected_field_fail_closed(self):
        payload = load_fixture()
        payload["candidates"].append(copy.deepcopy(payload["candidates"][0]))
        payload["decision_fields"].append("marital_status")
        result = TOOL.run(payload)["full"]
        self.assertFalse(result["gates"]["dedupe_gate"]["pass"])
        self.assertFalse(result["gates"]["privacy_gate"]["pass"])


if __name__ == "__main__":
    unittest.main()
