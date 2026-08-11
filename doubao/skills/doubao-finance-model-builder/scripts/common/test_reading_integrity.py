#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = Path(__file__).with_name("validate_reading_integrity.py")
SPEC = importlib.util.spec_from_file_location("validate_reading_integrity", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def external_entry(path: str) -> dict:
    return {
        "name": "lark-sheets",
        "path": path,
        "resolved_path": f"/installed/lark-sheets/{path}",
        "total_lines": 150,
        "chunks_read": [[1, 100], [101, 150]],
        "end_marker_found": False,
        "eof_confirmed": True,
        "status": "READ_COMPLETE",
    }


class ReadingIntegrityTests(unittest.TestCase):
    def validate(self, entries: list[dict]) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "reading-ledger.json"
            ledger.write_text(
                json.dumps({"external_skills": entries}), encoding="utf-8"
            )
            return MODULE.validate(ROOT, ledger)

    def test_complete_lark_reading_passes(self) -> None:
        result = self.validate(
            [
                external_entry("SKILL.md"),
                external_entry("references/ref-financial-modeling-standards"),
            ]
        )
        self.assertEqual(result["status"], "PASS", result["errors"])

    def test_missing_lark_skill_blocks_g0_input(self) -> None:
        result = self.validate(
            [external_entry("references/ref-financial-modeling-standards")]
        )
        self.assertEqual(result["status"], "INCOMPLETE")
        self.assertTrue(any("lark-sheets/SKILL.md" in item for item in result["errors"]))

    def test_missing_financial_standard_blocks_g0_input(self) -> None:
        result = self.validate([external_entry("SKILL.md")])
        self.assertEqual(result["status"], "INCOMPLETE")
        self.assertTrue(
            any("ref-financial-modeling-standards" in item for item in result["errors"])
        )

    def test_gapped_chunks_are_incomplete(self) -> None:
        skill = external_entry("SKILL.md")
        skill["chunks_read"] = [[1, 99], [101, 150]]
        result = self.validate(
            [skill, external_entry("references/ref-financial-modeling-standards")]
        )
        self.assertEqual(result["status"], "INCOMPLETE")

    def test_duplicate_external_record_is_incomplete(self) -> None:
        skill = external_entry("SKILL.md")
        result = self.validate(
            [
                skill,
                dict(skill),
                external_entry("references/ref-financial-modeling-standards"),
            ]
        )
        self.assertEqual(result["status"], "INCOMPLETE")


if __name__ == "__main__":
    unittest.main(verbosity=2)
