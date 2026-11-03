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
    def test_html_font_render_check_follows_source_write(self) -> None:
        for relative in ("SKILL.md", "references/workflow/template-rewrite.md",
                         "references/workflow/creation/ai-coding.md"):
            text = (ROOT / relative).read_text(encoding="utf-8")
            with self.subTest(file=relative):
                self.assertNotRegex(text, r"目标(?:文案)?字形覆盖和 Web 加载")
                self.assertRegex(text, r"字体声明.{0,30}写入 HTML.{0,30}`shot.py`.{0,15}检查实际加载")

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

    def test_html_gate_and_shared_font_failure_policy(self) -> None:
        text = self.read_doc()
        self.assertIn("<!-- html-font-gate: resolver-required -->", text)
        marker = re.search(r"<!--\s*font-failure-policy:\s*(\S+)\s*-->", text)
        self.assertIsNotNone(marker, "缺少字体失败处理入口")
        policy = marker.group(1)
        path, separator, anchor = policy.partition("#")
        self.assertEqual(path, "web-font-contract.md")
        self.assertTrue(separator and anchor, "入口须定位到处理章节")
        self.assertIn(policy, re.findall(r"\[[^\]]+\]\(([^)]+)\)", text))
        target = DOC.parent / path
        self.assertTrue(target.is_file())
        headings = re.findall(r"^#{1,6}\s+(.+)$", target.read_text(encoding="utf-8"), re.M)
        self.assertIn(anchor, [re.sub(r"\s+", "-", heading.lower()) for heading in headings])
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
