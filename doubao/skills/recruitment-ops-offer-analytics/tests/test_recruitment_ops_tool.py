import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "recruitment_ops_tool", ROOT / "scripts" / "recruitment_ops_tool.py"
)
TOOL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TOOL)


def fixture(name):
    return json.loads((ROOT / "tests" / "fixtures" / name).read_text(encoding="utf-8"))


class RecruitmentOpsToolTest(unittest.TestCase):
    def test_recruiting_pipeline_conservation_conversion_velocity_and_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            result = TOOL.run(fixture("recruiting-pipeline.json"), directory)
            full, compact = result["full"], result["compact"]
            self.assertEqual(full["status"], "ready")
            self.assertEqual(full["reached_counts"]["sourced"], 2)
            self.assertEqual(full["reached_counts"]["accepted"], 1)
            self.assertEqual(full["conversions"][0]["rate"], 1.0)
            self.assertGreater(full["velocity"]["sourced"]["average_days"], 0)
            self.assertTrue(full["gates"]["conservation_gate"]["pass"])
            self.assertEqual(compact["full_sha256"], result["full_sha256"])
            self.assertTrue(TOOL.validate_artifacts(
                Path(result["artifacts"]["full"]), Path(result["artifacts"]["compact"])
            )["pass"])

    def test_pipeline_perturbation_changes_output_and_preserves_unknown(self):
        baseline = fixture("recruiting-pipeline.json")
        changed = copy.deepcopy(baseline)
        changed["records"][1]["history"] = []
        before, after = TOOL.run(baseline), TOOL.run(changed)
        self.assertNotEqual(before["full_sha256"], after["full_sha256"])
        self.assertEqual(after["full"]["unknowns"][0]["missing"], ["history"])
        self.assertEqual(after["full"]["reached_counts"]["sourced"], 1)
        no_snapshot = copy.deepcopy(baseline)
        no_snapshot.pop("snapshot_at")
        missing_snapshot = TOOL.run(no_snapshot)["full"]
        self.assertEqual(missing_snapshot["status"], "intake_required")
        self.assertIsNone(missing_snapshot["snapshot_at"])

    def test_offer_capabilities_separate_draft_approval_send(self):
        payload = fixture("draft-offer.json")
        result = TOOL.run(payload)["full"]
        self.assertTrue(result["capabilities"]["can_draft_offer"]["allowed"])
        self.assertTrue(result["capabilities"]["can_send_offer"]["allowed"])
        self.assertFalse(result["side_effect"]["executed"])
        changed = copy.deepcopy(payload)
        changed["approval_state"] = "pending"
        changed["user_confirmed_send"] = False
        degraded = TOOL.run(changed)["full"]
        self.assertTrue(degraded["capabilities"]["can_draft_offer"]["allowed"])
        self.assertFalse(degraded["capabilities"]["can_send_offer"]["allowed"])
        self.assertIn("approved_offer", degraded["capabilities"]["can_send_offer"]["missing"])

    def test_privacy_artifact_and_integration_coverage_9_of_9(self):
        payload = fixture("draft-offer.json")
        payload["decision_fields"].append("gender")
        with tempfile.TemporaryDirectory() as directory:
            result = TOOL.run(payload, directory)
            self.assertFalse(result["full"]["gates"]["privacy_gate"]["pass"])
            full_path = Path(result["artifacts"]["full"])
            full_path.write_text(full_path.read_text(encoding="utf-8") + " ", encoding="utf-8")
            self.assertFalse(TOOL.validate_artifacts(
                full_path, Path(result["artifacts"]["compact"])
            )["pass"])

        workspace = ROOT.parents[2]
        report = json.loads(
            (workspace / "skill-library-department-optimization" / "reports" / "merge-hr-report.json")
            .read_text(encoding="utf-8")
        )
        self.assertEqual(len(report["records"]), 9)
        eval_paths = [
            workspace / "skill-library-production" / "skills" / "talent-sourcing-and-shortlist" / "evals" / "evals.json",
            workspace / "skill-library-production" / "skills" / "job-modeling-and-selection-design" / "evals" / "evals.json",
            workspace / "skill-library-production" / "skills" / "recruitment-ops-offer-analytics" / "evals" / "evals.json",
            workspace / "skill-library-production" / "skills" / "interview-execution-and-review" / "evals" / "evals.json",
        ]
        eval_ids, eval_by_id = set(), {}
        for path in eval_paths:
            payload = json.loads(path.read_text(encoding="utf-8"))
            for item in payload.get("evals", []):
                eval_ids.add(item["id"])
                eval_by_id[item["id"]] = item
        route_fixtures = {
            path.stem: json.loads(path.read_text(encoding="utf-8"))
            for path in (ROOT / "tests" / "fixtures" / "routes").glob("*.json")
        }
        self.assertEqual(len(route_fixtures), 6)
        for record in report["records"]:
            self.assertTrue(set(record["tests"]).intersection(eval_ids), record["source_slug"])
            if "implementation" in record:
                for value in record["implementation"].values():
                    for relative in value if isinstance(value, list) else [value]:
                        self.assertTrue((workspace / relative).is_file(), relative)
                assertion = record["executable_assertion"]
                assertion_ids = assertion["test_id"] if isinstance(assertion["test_id"], list) else [assertion["test_id"]]
                assertion_paths = assertion["path"] if isinstance(assertion["path"], list) else [assertion["path"]]
                self.assertTrue(set(assertion_ids).issubset(eval_ids))
                self.assertTrue(all((workspace / relative).is_file() for relative in assertion_paths))
            else:
                route_fixture = route_fixtures[record["source_slug"]]
                self.assertIn(route_fixture["test_id"], eval_ids)
                self.assertEqual(
                    eval_by_id[route_fixture["test_id"]]["expected_route"],
                    route_fixture["expected_route"],
                )


if __name__ == "__main__":
    unittest.main()
