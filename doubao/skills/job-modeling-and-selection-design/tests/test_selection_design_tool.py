import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "selection_design_tool", ROOT / "scripts" / "selection_design_tool.py"
)
TOOL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TOOL)


def load_fixture():
    return json.loads(
        (ROOT / "tests" / "fixtures" / "interview-prep.json").read_text(encoding="utf-8")
    )


class SelectionDesignToolTest(unittest.TestCase):
    def test_complete_design_passes_and_hashes(self):
        with tempfile.TemporaryDirectory() as directory:
            result = TOOL.run(load_fixture(), directory)
            self.assertEqual(result["full"]["status"], "ready")
            self.assertTrue(result["full"]["gates"]["panel_coverage_gate"]["pass"])
            self.assertEqual(result["compact"]["full_sha256"], result["full_sha256"])
            self.assertTrue(TOOL.validate_artifacts(
                Path(result["artifacts"]["full"]), Path(result["artifacts"]["compact"])
            )["pass"])

    def test_missing_anchor_is_unknown_not_default_score(self):
        payload = load_fixture()
        payload["dimensions"][0]["anchors"] = []
        payload["claims"][0]["source_tier"] = "secondary"
        result = TOOL.run(payload)["full"]
        self.assertEqual(result["status"], "degraded")
        self.assertIn("anchors", result["unknowns"][0]["missing"])
        self.assertEqual(result["gates"]["claim_gate"]["unsupported_critical_claims"], ["CLM-ROLE-001"])

    def test_panel_perturbation_changes_hash_and_fails_coverage(self):
        payload = load_fixture()
        baseline = TOOL.run(payload)
        changed = copy.deepcopy(payload)
        changed["panel_assignments"] = changed["panel_assignments"][:1]
        perturbed = TOOL.run(changed)
        self.assertNotEqual(baseline["full_sha256"], perturbed["full_sha256"])
        self.assertEqual(perturbed["full"]["gates"]["panel_coverage_gate"]["uncovered_dimensions"], ["delivery"])

    def test_protected_criterion_and_mechanical_decision_fail(self):
        payload = load_fixture()
        payload["criteria_fields"].append("age")
        payload["automated_hiring_decision"] = True
        result = TOOL.run(payload)["full"]
        self.assertFalse(result["gates"]["privacy_gate"]["pass"])
        self.assertFalse(result["gates"]["decision_gate"]["pass"])


if __name__ == "__main__":
    unittest.main()
