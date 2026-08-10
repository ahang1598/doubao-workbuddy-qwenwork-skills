#!/usr/bin/env python3
"""Regression tests for three-statement delivery gates."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from validate_delivery import file_sha256, self_test, validate


class ThreeStatementDeliveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.workbook = Path(self.tempdir.name) / "model.xlsx"
        self.workbook.write_bytes(b"formula-driven-workbook")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def valid_manifest(self) -> dict:
        return {
            "source_coverage_ratio": 1.0,
            "source_mapping_audit_passed": True,
            "source_conflict_count": 0,
            "hardcoded_calculation_count": 0,
            "unexplained_plug_count": 0,
            "all_visible_sheets_rendered": True,
        }

    def valid_audit(self) -> dict:
        return {
            "status": "PASS",
            "workbook_path": str(self.workbook),
            "workbook_sha256": file_sha256(self.workbook),
            "errors": [],
            "warnings": [],
            "metrics": {
                "formula_error_count": 0,
                "direct_circular_count": 0,
                "duplicate_semantic_key_count": 0,
                "failed_check_rows": 0,
                "formula_count": 10,
                "required_sheet_count": 7,
                "present_required_sheet_count": 7,
            },
        }

    def test_complete_delivery_passes(self) -> None:
        self.assertEqual(self_test()["model_status_code"], "PASS")
        self.assertEqual(validate(self.valid_manifest(), self.valid_audit())["model_status_code"], "PASS")

    def test_claimed_coverage_without_mapping_audit_fails(self) -> None:
        manifest = self.valid_manifest()
        manifest["source_mapping_audit_passed"] = False
        self.assertEqual(validate(manifest, self.valid_audit())["model_status_code"], "FAIL")

    def test_direct_audit_failure_cannot_be_overridden(self) -> None:
        audit = self.valid_audit()
        audit["status"] = "FAIL"
        audit["metrics"]["direct_circular_count"] = 1
        self.assertEqual(validate(self.valid_manifest(), audit)["model_status_code"], "FAIL")

    def test_changed_workbook_after_audit_fails_hash_gate(self) -> None:
        audit = self.valid_audit()
        self.workbook.write_bytes(b"changed-after-audit")
        self.assertEqual(validate(self.valid_manifest(), audit)["model_status_code"], "FAIL")


if __name__ == "__main__":
    unittest.main(verbosity=2)
