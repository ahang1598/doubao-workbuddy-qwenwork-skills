#!/usr/bin/env python3
import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location(
    "sales_merge_evidence_gate", SCRIPTS / "sales_merge_evidence_gate.py"
)
ENGINE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ENGINE)
FIXTURE_PATH = ROOT / "tests" / "fixtures" / "sales-merge-coverage.json"


class SalesMergeCoverageTest(unittest.TestCase):
    def test_all_ten_merge_mode_fixtures(self):
        result = ENGINE.evaluate_file(FIXTURE_PATH)
        self.assertTrue(result["passed"], result)
        self.assertEqual(result["coverage"], 10)
        self.assertEqual(result["expected"], 10)
        self.assertEqual(result["missing_slugs"], [])
        self.assertEqual(result["connector_support_coverage"], 6)
        self.assertEqual(result["connector_support_expected"], 6)
        self.assertEqual(result["connector_failures"], [])
        self.assertEqual(
            {item["source_slug"] for item in result["results"]},
            ENGINE.EXPECTED_SLUGS,
        )
        for item in result["results"]:
            with self.subTest(source_slug=item["source_slug"]):
                self.assertTrue(item["passed"], item["failures"])
                self.assertTrue(item["fixture_id"])

    def test_fixture_engine_rejects_bad_claim_schema(self):
        result = ENGINE.evaluate_fixture(
            {
                "fixture_id": "bad",
                "source_slug": "sales-company-research",
                "claims": [],
                "available_artifacts": [],
                "evidence": [],
                "facts": {},
            }
        )
        self.assertFalse(result["passed"])
        self.assertTrue(any("claim_schema" in item for item in result["failures"]))


if __name__ == "__main__":
    unittest.main()
