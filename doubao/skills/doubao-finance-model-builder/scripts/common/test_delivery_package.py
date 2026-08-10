#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import hashlib
import json
import tempfile
import unittest
from pathlib import Path


SPEC = importlib.util.spec_from_file_location("finalize_delivery_package", Path(__file__).with_name("finalize_delivery_package.py"))
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class DeliveryPackageTests(unittest.TestCase):
    def plan(self) -> dict:
        return {
            "meta": {"task_id": "test", "model_purpose": "formal"},
            "workflows": ["dcf"],
            "deliverables": {"hero": "model.xlsx", "support": ["validation.json", "equity-evidence.json", "equity-evidence-validation.json", "formula-semantic-audit.json", "artifact-audit.json"]},
            "result_policy": {"conclusion_requires_pass": True},
        }

    def stages(self, status: str = "PASS") -> dict:
        stages = {name: status for name in MODULE.REQUIRED_STAGES}
        stages["equity_evidence_frozen"] = {"status": status, "evidence_file": "equity-evidence-validation.json"}
        stages["formula_semantics_audited"] = {"status": status, "audit_file": "formula-semantic-audit.json"}
        stages["artifact_directly_audited"] = {"status": status, "audit_file": "artifact-audit.json"}
        return {"stages": stages, "hard_failures": [], "warnings": []}

    def write_support(self, root: Path, evidence_status: str = "PASS") -> None:
        (root / "validation.json").write_text("{}")
        manifest_bytes = b"{}"
        (root / "equity-evidence.json").write_bytes(manifest_bytes)
        (root / "equity-evidence-validation.json").write_text(json.dumps({
            "model_status_code": evidence_status,
            "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest()
        }))
        hero = root / "model.xlsx"
        (root / "artifact-audit.json").write_text(json.dumps({
            "status": "PASS",
            "workflow": "dcf",
            "artifact_sha256": hashlib.sha256(hero.read_bytes()).hexdigest() if hero.is_file() else None,
        }))
        (root / "formula-semantic-audit.json").write_text(json.dumps({
            "status": "PASS",
            "workflow": "dcf",
            "artifact_sha256": hashlib.sha256(hero.read_bytes()).hexdigest() if hero.is_file() else None,
        }))

    def test_complete_package_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "model.xlsx").write_bytes(b"model")
            self.write_support(root)
            run, manifest = MODULE.build(self.plan(), self.stages(), root)
            self.assertEqual(run["model_status"], "PASS")
            self.assertTrue(run["conclusion_allowed"])
            self.assertTrue(all(item["sha256"] for item in manifest["files"]))

    def test_missing_support_is_incomplete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "model.xlsx").write_bytes(b"model")
            self.write_support(root)
            (root / "validation.json").unlink()
            run, _ = MODULE.build(self.plan(), self.stages(), root)
            self.assertEqual(run["model_status"], "INCOMPLETE")
            self.assertFalse(run["conclusion_allowed"])

    def test_missing_hero_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_support(root)
            run, _ = MODULE.build(self.plan(), self.stages(), root)
            self.assertEqual(run["model_status"], "FAIL")

    def test_failed_stage_cannot_be_overridden(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "model.xlsx").write_bytes(b"model")
            self.write_support(root)
            stages = self.stages()
            stages["stages"]["delivery_validated"] = "FAIL"
            run, _ = MODULE.build(self.plan(), stages, root)
            self.assertEqual(run["model_status"], "FAIL")

    def test_failed_equity_evidence_blocks_delivery(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "model.xlsx").write_bytes(b"model")
            self.write_support(root, evidence_status="FAIL")
            run, _ = MODULE.build(self.plan(), self.stages(), root)
            self.assertEqual(run["model_status"], "FAIL")

    def test_stale_equity_evidence_validation_blocks_delivery(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "model.xlsx").write_bytes(b"model")
            self.write_support(root)
            (root / "equity-evidence.json").write_text('{"changed": true}')
            run, _ = MODULE.build(self.plan(), self.stages(), root)
            self.assertEqual(run["model_status"], "FAIL")

    def test_artifact_changed_after_audit_blocks_delivery(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "model.xlsx").write_bytes(b"model")
            self.write_support(root)
            (root / "model.xlsx").write_bytes(b"changed")
            run, _ = MODULE.build(self.plan(), self.stages(), root)
            self.assertEqual(run["model_status"], "FAIL")

    def test_missing_semantic_audit_blocks_delivery(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "model.xlsx").write_bytes(b"model")
            self.write_support(root)
            (root / "formula-semantic-audit.json").unlink()
            run, _ = MODULE.build(self.plan(), self.stages(), root)
            self.assertEqual(run["model_status"], "FAIL")

    def test_formal_report_cannot_replace_workbook(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = self.plan()
            plan["deliverables"]["hero"] = "report.md"
            (root / "report.md").write_text("report")
            self.write_support(root)
            run, _ = MODULE.build(plan, self.stages(), root)
            self.assertEqual(run["model_status"], "FAIL")

    def test_path_traversal_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = self.plan()
            plan["deliverables"]["hero"] = "../escape.xlsx"
            with self.assertRaisesRegex(ValueError, "escapes"):
                MODULE.build(plan, self.stages(), root)


if __name__ == "__main__":
    unittest.main(verbosity=2)
