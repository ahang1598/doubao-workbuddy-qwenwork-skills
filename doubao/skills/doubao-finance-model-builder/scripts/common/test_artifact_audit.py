#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path


SPEC = importlib.util.spec_from_file_location("audit_report_artifact", Path(__file__).with_name("audit_report_artifact.py"))
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ReportArtifactAuditTests(unittest.TestCase):
    def test_hash_bound_report_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            calculated = root / "calculated.json"
            calculated.write_text('{"value": 1}', encoding="utf-8")
            digest = hashlib.sha256(calculated.read_bytes()).hexdigest()
            report = root / "report.md"
            report.write_text(f"# 报告\n\n<!-- CALCULATED_SHA256:{digest} -->\n", encoding="utf-8")
            self.assertEqual(MODULE.audit(report, calculated, "comps")["status"], "PASS")

    def test_stale_calculation_marker_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            calculated = root / "calculated.json"
            calculated.write_text('{"value": 2}', encoding="utf-8")
            report = root / "report.md"
            report.write_text("# 报告\n\n<!-- CALCULATED_SHA256:old -->\n", encoding="utf-8")
            self.assertEqual(MODULE.audit(report, calculated, "lbo")["status"], "FAIL")

    def test_placeholder_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            calculated = root / "calculated.json"
            calculated.write_text("{}", encoding="utf-8")
            digest = hashlib.sha256(calculated.read_bytes()).hexdigest()
            report = root / "report.md"
            report.write_text(f"TODO\n<!-- CALCULATED_SHA256:{digest} -->\n", encoding="utf-8")
            self.assertEqual(MODULE.audit(report, calculated, "dcf")["status"], "FAIL")


if __name__ == "__main__":
    unittest.main(verbosity=2)
