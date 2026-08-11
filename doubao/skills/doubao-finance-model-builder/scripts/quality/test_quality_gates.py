#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("run_quality_gates.py")
SPEC = importlib.util.spec_from_file_location("run_quality_gates", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class ConsolidatedQualityGateTests(unittest.TestCase):
    def make_root(self) -> Path:
        root = Path(tempfile.mkdtemp())
        (root / "model.xlsx").write_bytes(b"workbook")
        return root

    def write_result(self, root: Path, name: str, status: str = "PASS", hero_hash: str | None = None) -> None:
        payload = {"status": status, "errors": [], "warnings": []}
        if hero_hash is not None:
            payload["artifact_sha256"] = hero_hash
        (root / name).write_text(json.dumps(payload), encoding="utf-8")

    def complete_dcf(self, root: Path) -> None:
        hero_hash = MODULE.file_sha256(root / "model.xlsx")
        for name in (
            "reading-integrity.json",
            "execution-plan-validation.json",
            "announcement-sweep-validation.json",
            "source-validation.json",
            "equity-evidence-validation.json",
            "model-contract-validation.json",
            "dcf-validation.json",
            "cross-artifact-parity.json",
        ):
            self.write_result(root, name)
        for name in ("model-audit.json", "formula-semantic-audit.json", "artifact-audit.json", "visual-audit.json"):
            self.write_result(root, name, hero_hash=hero_hash)

    def test_complete_dcf_passes_and_releases_conclusion(self) -> None:
        root = self.make_root()
        self.complete_dcf(root)
        result = MODULE.run(root, {"dcf"}, "model.xlsx", root / "quality")
        self.assertEqual(result["report"]["overall_status"], "PASS")
        self.assertTrue(result["release_decision"]["conclusion_allowed"])

    def test_missing_formula_audit_is_incomplete_and_suppresses_values(self) -> None:
        root = self.make_root()
        self.complete_dcf(root)
        (root / "formula-semantic-audit.json").unlink()
        result = MODULE.run(root, {"dcf"}, "model.xlsx", root / "quality")
        self.assertEqual(result["report"]["overall_status"], "INCOMPLETE")
        self.assertFalse(result["release_decision"]["conclusion_allowed"])
        self.assertIn("target_price", result["release_decision"]["suppressed_outputs"])

    def test_incomplete_external_skill_reading_blocks_g0_and_release(self) -> None:
        root = self.make_root()
        self.complete_dcf(root)
        self.write_result(root, "reading-integrity.json", status="INCOMPLETE")
        result = MODULE.run(root, {"dcf"}, "model.xlsx", root / "quality")
        self.assertEqual(result["report"]["gates"]["G0"], "INCOMPLETE")
        self.assertEqual(result["report"]["overall_status"], "INCOMPLETE")
        self.assertFalse(result["release_decision"]["conclusion_allowed"])
        self.assertIn("model_complete", result["release_decision"]["suppressed_outputs"])

    def test_missing_unified_model_audit_blocks_release(self) -> None:
        root = self.make_root()
        self.complete_dcf(root)
        (root / "model-audit.json").unlink()
        result = MODULE.run(root, {"dcf"}, "model.xlsx", root / "quality")
        self.assertEqual(result["report"]["gates"]["G4"], "INCOMPLETE")
        self.assertFalse(result["release_decision"]["conclusion_allowed"])

    def test_failed_calculation_blocks_release(self) -> None:
        root = self.make_root()
        self.complete_dcf(root)
        self.write_result(root, "dcf-validation.json", status="FAIL")
        result = MODULE.run(root, {"dcf"}, "model.xlsx", root / "quality")
        self.assertEqual(result["report"]["overall_status"], "FAIL")
        self.assertFalse(result["release_decision"]["conclusion_allowed"])

    def test_stale_workbook_audit_hash_fails(self) -> None:
        root = self.make_root()
        self.complete_dcf(root)
        self.write_result(root, "artifact-audit.json", hero_hash="stale")
        result = MODULE.run(root, {"dcf"}, "model.xlsx", root / "quality")
        self.assertEqual(result["report"]["overall_status"], "FAIL")
        self.assertEqual(result["report"]["gates"]["G4"], "FAIL")

    def test_formal_report_cannot_replace_excel(self) -> None:
        root = self.make_root()
        self.complete_dcf(root)
        (root / "report.md").write_text("report")
        result = MODULE.run(root, {"dcf"}, "report.md", root / "quality")
        self.assertEqual(result["report"]["overall_status"], "FAIL")

    def test_zero_byte_workbook_is_not_a_deliverable(self) -> None:
        root = self.make_root()
        self.complete_dcf(root)
        (root / "model.xlsx").write_bytes(b"")
        result = MODULE.run(root, {"dcf"}, "model.xlsx", root / "quality")
        self.assertEqual(result["report"]["gates"]["G5"], "FAIL")
        self.assertFalse(result["release_decision"]["conclusion_allowed"])
        self.assertEqual(result["gates"][5]["checks"][1]["errors"], ["主要交付工作簿大小为0，不构成已生成的产物"])

    def test_missing_lbo_workbook_cannot_be_claimed_as_delivered(self) -> None:
        root = self.make_root()
        hero_hash = MODULE.file_sha256(root / "model.xlsx")
        for name in (
            "reading-integrity.json",
            "execution-plan-validation.json",
            "announcement-sweep-validation.json",
            "source-validation.json",
            "model-contract-validation.json",
            "lbo-validation.json",
            "cross-artifact-parity.json",
        ):
            self.write_result(root, name)
        for name in ("model-audit.json", "formula-semantic-audit.json", "artifact-audit.json", "visual-audit.json"):
            self.write_result(root, name, hero_hash=hero_hash)
        (root / "model.xlsx").unlink()
        result = MODULE.run(root, {"lbo"}, "model.xlsx", root / "quality")
        self.assertEqual(result["report"]["gates"]["G5"], "FAIL")
        self.assertFalse(result["release_decision"]["conclusion_allowed"])
        self.assertIn("model_complete", result["release_decision"]["suppressed_outputs"])
        self.assertEqual(result["gates"][5]["checks"][1]["errors"], ["主要交付工作簿不存在"])

    def test_dcf_requires_equity_evidence(self) -> None:
        root = self.make_root()
        self.complete_dcf(root)
        (root / "equity-evidence-validation.json").unlink()
        result = MODULE.run(root, {"dcf"}, "model.xlsx", root / "quality")
        self.assertEqual(result["report"]["gates"]["G1"], "INCOMPLETE")


if __name__ == "__main__":
    unittest.main(verbosity=2)
