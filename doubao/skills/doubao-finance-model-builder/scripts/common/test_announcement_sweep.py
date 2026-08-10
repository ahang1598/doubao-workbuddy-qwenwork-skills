#!/usr/bin/env python3

from __future__ import annotations

import copy
import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("validate_announcement_sweep.py")
SPEC = importlib.util.spec_from_file_location("validate_announcement_sweep", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixture(root: Path) -> dict:
    search = root / "search.html"
    search_text = root / "search.txt"
    notice = root / "notice.html"
    notice_text = root / "notice.txt"
    search.write_text("示例公司 DEMO.SH [DISCOVERED_ANNOUNCEMENT_ID:ANN-1]", encoding="utf-8")
    search_text.write_text("示例公司 DEMO.SH [DISCOVERED_ANNOUNCEMENT_ID:ANN-1]", encoding="utf-8")
    notice.write_text("示例公司 DEMO.SH 权益分派公告", encoding="utf-8")
    notice_text.write_text("示例公司 DEMO.SH 每10股转增3股，除权日2026-06-20", encoding="utf-8")
    return {
        "schema_version": "1.0",
        "company": "示例公司",
        "security_identifiers": ["DEMO.SH"],
        "valuation_date": "2026-06-30",
        "information_cutoff_date": "2026-06-30",
        "evidence": [
            {"evidence_id": "SEARCH-1", "role": "announcement_search_result", "authority_tier": "primary", "url": "https://example.com/search", "published_date": "2026-06-30", "local_file": "search.html", "text_file": "search.txt", "sha256": digest(search), "text_sha256": digest(search_text)},
            {"evidence_id": "DOC-1", "role": "announcement_document", "authority_tier": "primary", "url": "https://example.com/notice", "published_date": "2026-06-10", "local_file": "notice.html", "text_file": "notice.txt", "sha256": digest(notice), "text_sha256": digest(notice_text)},
        ],
        "sweeps": [{"market": "a_share", "official_entry_url": "https://example.com/search", "search_start_date": "2026-03-31", "search_end_date": "2026-06-30", "queries": ["DEMO.SH 权益分派 股本变动"], "result_evidence_ids": ["SEARCH-1"], "completed": True, "coverage_gaps": []}],
        "announcements": [{"announcement_id": "ANN-1", "evidence_id": "DOC-1", "published_date": "2026-06-10", "effective_date": "2026-06-20", "category": "capitalization_issue", "disposition": "incorporated", "affected_model_fields": ["shares_outstanding"], "rationale": "估值日前已生效，进入股数桥"}],
    }


class AnnouncementSweepTests(unittest.TestCase):
    def test_complete_sweep_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(MODULE.validate(fixture(root), root)["model_status_code"], "PASS")

    def test_discovered_announcement_must_be_dispositioned(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = fixture(root)
            payload["announcements"] = []
            result = MODULE.validate(payload, root)
            self.assertEqual(result["model_status_code"], "FAIL")
            self.assertTrue(any("not dispositioned" in item for item in result["errors"]))

    def test_cutoff_gap_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = fixture(root)
            payload["sweeps"][0]["search_end_date"] = "2026-06-29"
            self.assertEqual(MODULE.validate(payload, root)["model_status_code"], "FAIL")

    def test_blocking_announcement_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = fixture(root)
            payload["announcements"][0]["disposition"] = "blocking"
            self.assertEqual(MODULE.validate(payload, root)["model_status_code"], "FAIL")

    def test_modified_evidence_hash_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = copy.deepcopy(fixture(root))
            (root / "notice.txt").write_text("tampered", encoding="utf-8")
            self.assertEqual(MODULE.validate(payload, root)["model_status_code"], "FAIL")


if __name__ == "__main__":
    unittest.main(verbosity=2)
