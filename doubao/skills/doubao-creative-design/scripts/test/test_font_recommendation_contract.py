#!/usr/bin/env python3
"""Contract checks for the human entry, structured source and execution gate."""

from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "references/rendering/font-recommendation-list.md"
POOL = ROOT / "assets/fonts/font-curated-pool.json"
GENERATOR = ROOT / "scripts/maintenance/generate-font-recommendation-list.py"


class FontRecommendationContractTests(unittest.TestCase):
    def read_doc(self) -> str:
        self.assertTrue(DOC.exists(), "missing unified font recommendation entry")
        return DOC.read_text(encoding="utf-8")

    def test_entry_declares_scope_and_single_structured_source(self) -> None:
        text = self.read_doc()
        for marker in (
            "<!-- source-of-truth: assets/fonts/font-curated-pool.json -->",
            "<!-- recommendation-scope: curated-entry-not-whitelist -->",
            "<!-- query-role: deterministic-query-and-diagnostics -->",
            "<!-- row-quota: none -->",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

    def test_html_gate_and_locked_font_failure_are_explicit(self) -> None:
        text = self.read_doc()
        self.assertIn("<!-- html-font-gate: resolver-required -->", text)
        self.assertIn("<!-- locked-font-failure: user-confirmation-required -->", text)
        for term in ("family", "face", "weight", "许可", "覆盖", "Web"):
            with self.subTest(term=term):
                self.assertIn(term, text)

    def test_generated_table_is_current_and_uses_stable_font_keys(self) -> None:
        self.assertTrue(GENERATOR.exists(), "missing recommendation table generator")
        result = subprocess.run(
            [sys.executable, str(GENERATOR), "--check"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        text = self.read_doc()
        begin = "<!-- BEGIN GENERATED:FONT_RECOMMENDATIONS -->"
        end = "<!-- END GENERATED:FONT_RECOMMENDATIONS -->"
        self.assertEqual(text.count(begin), 1)
        self.assertEqual(text.count(end), 1)
        generated = text.split(begin, 1)[1].split(end, 1)[0]
        keys = re.findall(r"^\|\s*`([^`]+)`\s*\|", generated, flags=re.MULTILINE)
        self.assertTrue(keys, "generated recommendation table has no font_key rows")
        self.assertEqual(len(keys), len(set(keys)))
        pool_keys = {item["key"] for item in json.loads(POOL.read_text(encoding="utf-8"))["fonts"]}
        self.assertTrue(set(keys) <= pool_keys)

    def test_active_markdown_no_longer_routes_to_parallel_selection_docs(self) -> None:
        stale = {
            "references/rendering/font-theme-strategy.md",
            "references/style/coding/ai-coding/font-selection.md",
        }
        hits = []
        for path in ROOT.rglob("*.md"):
            relative = path.relative_to(ROOT).as_posix()
            if relative in stale:
                continue
            content = path.read_text(encoding="utf-8")
            for target in stale:
                if target in content or Path(target).name in content:
                    hits.append((relative, target))
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
