"""Run directly; LINT_INSPECT_SCRIPT may select a draft script for validation."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(os.environ.get("LINT_INSPECT_SCRIPT", Path(__file__).with_name("lint_inspect.py"))).resolve()
spec = importlib.util.spec_from_file_location("lint_inspect", SCRIPT)
lint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lint)


def issue(code="bbox_overlap", level="error", page=1):
    return {"code": code, "level": level, "elements": ["a", "b"],
            "target": {"slide_number": page}, "message": "完整消息", "hint": "检查位置",
            "measurement": {"intersection_area": 12}, "future_field": {"keep": True}}


def report(pages=None, document=None):
    pages = pages if pages is not None else [[issue()]]
    document = document or []
    slides = []
    all_issues = list(document)
    for i, values in enumerate(pages, 1):
        all_issues.extend(values)
        slides.append({"slide_number": i, "status": "blocked" if any(v["level"] == "error" for v in values) else "passed",
                       **{key: [v for v in values if v["level"] == level] for key, level in lint.LEVELS.items()},
                       "issues": list(reversed(values))})
    return {"schema_version": "2.0", "tool": "xml_lint",
            "summary": {"slide_count": len(slides), "status": "blocked" if any(v["level"] == "error" for v in all_issues) else "passed",
                        **{level + "_count": sum(v["level"] == level for v in all_issues) for level in lint.LEVELS.values()}},
            "document": {key: [v for v in document if v["level"] == level] for key, level in lint.LEVELS.items()},
            "issues": list(document), "slides": slides}


class LintInspectTests(unittest.TestCase):
    def args(self, *flags):
        return lint.parse_args(["--input", "response.json", *flags])

    def run_cli(self, directory, value, *flags):
        path = Path(directory) / "input.json"
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        return subprocess.run([sys.executable, "-B", str(SCRIPT), "--input", str(path), *flags], text=True, capture_output=True)

    def test_mirrors_not_double_counted_or_cross_page_merged(self):
        duplicate = issue("duplicate_element_id"); duplicate["target"] = {}
        r = report([[issue(), issue(level="info")], [issue(page=2)]], [duplicate])
        i = lint.Inspector({"ok": True, "data": {"issues": r}})
        self.assertEqual(i.status, "parsed")
        self.assertEqual(len(i.rows), 4)
        self.assertEqual(lint.counts(i.rows), {"error": 3, "warning": 0, "info": 1, "unknown": 0})
        self.assertTrue(all(len(row["sources"]) == 2 for row in i.rows))

    def test_duplicate_occurrences_within_one_list_are_preserved(self):
        r = report([[issue(), issue()]])
        self.assertEqual(len(lint.Inspector(r).rows), 2)

    def test_root_combined_all_pages(self):
        r = report([[issue()], [issue(page=2)]])
        r["issues"] = [issue(), issue(page=2)]
        i = lint.Inspector(r)
        self.assertEqual(i.status, "parsed")
        self.assertEqual(len(i.rows), 2)
        self.assertTrue(all(len(row["sources"]) == 3 for row in i.rows))

    def test_disagreeing_mirror_is_not_silently_discarded(self):
        r = report(); r["slides"][0]["issues"].append(issue("new_rule"))
        i = lint.Inspector(r)
        self.assertEqual(i.status, "partial")
        self.assertEqual(len(i.rows), 2)

    def test_lint_rejection_decodes_string_and_preserves_full_issue(self):
        r = report()
        i = lint.Inspector({"ok": False, "error": {"code": 4000153, "message": json.dumps(r)}})
        out = lint.render(i, self.args("--details"))
        self.assertFalse(out["response_ok"])
        self.assertEqual(out["inspection_status"], "parsed")
        self.assertEqual(out["lint_status"], "blocked")
        self.assertEqual(out["issues"][0]["issue"], r["slides"][0]["errors"][0])

    def test_failed_rejection_decode_keeps_original(self):
        raw = '{"summary":'
        i = lint.Inspector({"ok": False, "error": {"code": "4000153", "message": raw}})
        self.assertEqual(i.status, "partial")
        self.assertEqual(i.rows[0]["issue"], raw)

    def test_nonlint_error_not_interpreted_as_report(self):
        i = lint.Inspector({"ok": False, "error": {"code": 403, "message": json.dumps(report())}})
        self.assertEqual(i.status, "api_error")
        self.assertEqual(len(i.reports), 0)

    def test_missing_report_is_not_pass(self):
        out = lint.render(lint.Inspector({"ok": True, "data": {"slide_id": "p1"}}), self.args())
        self.assertEqual(out["inspection_status"], "no_report")
        self.assertEqual(out["lint_status"], "unknown")

    def test_zero_issue_report_is_distinct_from_empty_write_findings(self):
        clean = lint.render(lint.Inspector(report([[]])), self.args())
        empty = lint.render(lint.Inspector({"ok": True, "data": {"issues": []}}), self.args())
        self.assertEqual(clean["lint_status"], "passed")
        self.assertEqual(empty["lint_status"], "unknown")
        self.assertEqual(empty["inspection_status"], "findings_only")

    def test_missing_summary_counts_not_assumed_zero(self):
        r = report([[]]); del r["summary"]["error_count"]
        i = lint.Inspector(r)
        self.assertEqual(i.status, "partial")
        self.assertEqual(lint.render(i, self.args())["lint_status"], "unknown")

    def test_malformed_container_retains_raw(self):
        r = report(); r["document"] = "lint engine failed"
        i = lint.Inspector(r)
        self.assertEqual(i.status, "partial")
        self.assertTrue(any(v["issue"] == "lint engine failed" for v in i.rows))

    def test_malformed_metadata_and_status_return_diagnostics_not_traceback(self):
        r = report();r["summary"]["status"] = ["passed"]
        i = lint.Inspector({"ok": True, "data": {"slide_id": {"bad": True}, "slide_number": [1], "issues": r}})
        out = lint.render(i, self.args())
        self.assertEqual(out["inspection_status"], "partial")
        self.assertEqual(out["lint_status"], "unknown")

    def test_create_slide_findings_and_plain_text(self):
        i = lint.Inspector({"ok": True, "data": {"slide_issues": [
            {"slide_id": "p1", "slide_number": 1, "issues": json.dumps(report())},
            {"slide_id": "p2", "slide_number": 2, "issues": "unsupported attributes dropped"}]}})
        self.assertEqual(i.status, "partial")
        selected = lint.select_rows(i.rows, self.args("--details", "--slide-id", "p2"))
        self.assertEqual(selected[0]["issue"], "unsupported attributes dropped")
        self.assertEqual(i.rows[0]["slide_id"], "p1")

    def test_unknown_create_wrapper_keeps_all_original_fields(self):
        wrapper = {"page": "unknown mapping", "errors": [issue()], "custom_metadata": 3}
        i = lint.Inspector({"ok": True, "data": {"slide_issues": [wrapper]}})
        self.assertEqual(i.status, "partial")
        self.assertEqual(i.rows[0]["issue"], wrapper)

    def test_write_structured_findings_without_summary(self):
        i = lint.Inspector({"ok": True, "data": {"slide_id": "p1", "issues": [issue(level="warning")]}})
        self.assertEqual(i.status, "findings_only")
        self.assertEqual(i.rows[0]["slide_id"], "p1")

    def test_passed_report_does_not_hide_additional_findings(self):
        i = lint.Inspector({"ok": True, "data": {"issues": report([[]]), "slide_issues": [
            {"slide_id": "p2", "issues": [issue()]}]}})
        out = lint.render(i, self.args())
        self.assertEqual(out["inspection_status"], "findings_only")
        self.assertEqual(out["lint_status"], "unknown")
        self.assertEqual(out["parsed_counts"]["error"], 1)

    def test_rejection_with_passed_report_is_inconsistent(self):
        i = lint.Inspector({"ok": False, "error": {"code": 4000153, "message": json.dumps(report([[]]))}})
        self.assertEqual(i.status, "partial")

    def test_single_page_number_and_wrapper_number_remain_separate(self):
        i = lint.Inspector({"ok": True, "data": {"slide_id": "p5", "slide_number": 5, "scope": "slide", "issues": report()}})
        self.assertEqual(i.rows[0]["slide_number"], 1)
        self.assertEqual(i.metadata["slide_number"], 5)
        self.assertEqual(i.rows[0]["slide_id"], "p5")

    def test_unknown_slide_id_not_inferred(self):
        i = lint.Inspector(report())
        self.assertIsNone(i.rows[0]["slide_id"])

    def test_absent_selection_is_not_a_clean_page(self):
        i = lint.Inspector(report([[]]))
        for flags in (("--slide-number", "9"), ("--slide-id", "p9"), ("--details", "--issue-id", "i999999")):
            with self.assertRaises(ValueError):
                lint.render(i, self.args(*flags))
        self.assertEqual(lint.render(i, self.args("--details", "--slide-number", "1"))["selected_issue_total"], 0)

    def test_root_only_page_finding_updates_page_counts(self):
        r = report([[]]);r["issues"] = [issue()]
        r["summary"].update(error_count=1, status="blocked")
        i = lint.Inspector(r)
        self.assertEqual(i.pages[0]["parsed_counts"]["error"], 1)

    def test_diagnostics_not_lost_in_saved_output(self):
        value = {"ok": True, "data": {"issues": [f"unknown finding {n}" for n in range(15)]}}
        i = lint.Inspector(value)
        preview = lint.render(i, self.args())
        exported = lint.render(i, self.args("--output", "summary.json"))
        self.assertTrue(preview["diagnostics_truncated"])
        self.assertEqual(len(exported["diagnostics"]), 15)
        self.assertFalse(exported["diagnostics_truncated"])

    def test_filters_keep_document_reminder_and_full_warning(self):
        doc = issue("duplicate_element_id");doc["target"] = {}
        i = lint.Inspector(report([[issue(), issue("contrast", "warning")]], [doc]))
        out = lint.render(i, self.args("--details", "--slide-number", "1", "--level", "warning"))
        self.assertEqual(out["document_issue_total"], 1)
        self.assertEqual(out["selected_issue_total"], 1)
        self.assertEqual(out["issues"][0]["issue"]["code"], "contrast")

    def test_pagination_no_omissions_or_duplicate_ids(self):
        values = [issue(f"rule_{n}") for n in range(27)]
        i = lint.Inspector(report([values]))
        offset = 0; actual = []
        while True:
            out = lint.render(i, self.args("--details", "--offset", str(offset), "--limit", "7", "--max-chars", "2000"))
            actual.extend(out["issues"])
            paging = out["pagination"]
            if not paging["has_more"]: break
            self.assertGreater(paging["next_offset"], offset)
            offset = paging["next_offset"]
        self.assertEqual([v["issue"] for v in actual], values)
        self.assertEqual(len({v["issue_id"] for v in actual}), 27)

    def test_summary_pages_paginate(self):
        i = lint.Inspector(report([[] for _ in range(25)]))
        out = lint.render(i, self.args("--offset", "20", "--limit", "10"))
        self.assertEqual(len(out["pages"]), 5)
        self.assertFalse(out["page_pagination"]["has_more"])

    def test_large_single_issue_not_truncated_can_be_exported(self):
        large = issue();large["message"] = "文字" * 20000
        value = report([[large]])
        out = lint.render(lint.Inspector(value), self.args("--details"))
        self.assertEqual(out["issues"], [])
        self.assertEqual(out["pagination"]["oversized_issue_id"], "i000001")
        with tempfile.TemporaryDirectory() as d:
            target = str(Path(d) / "detail.json")
            result = self.run_cli(d, value, "--details", "--issue-id", "i000001", "--output", target)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(Path(target).read_text())["issues"][0]["issue"]["message"], large["message"])
            self.assertLess(len(result.stdout), 1000)

    def test_output_cannot_overwrite_input_or_create_directories(self):
        with tempfile.TemporaryDirectory() as d:
            for target in (str(Path(d) / "input.json"), str(Path(d) / "missing" / "out.json")):
                result = self.run_cli(d, report(), "--output", target)
                self.assertEqual(result.returncode, 2)
            self.assertFalse((Path(d) / "missing").exists())
            self.assertEqual(json.loads((Path(d) / "input.json").read_text()), report())

    def test_cli_exit_code_is_not_lint_status(self):
        with tempfile.TemporaryDirectory() as d:
            blocked = self.run_cli(d, report())
            self.assertEqual(blocked.returncode, 0)
            self.assertEqual(json.loads(blocked.stdout)["lint_status"], "blocked")
            missing = self.run_cli(d, {"ok": True, "data": {}})
            self.assertEqual(missing.returncode, 2)

    def test_invalid_json_and_invalid_arguments(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "invalid.json";path.write_text('{"ok":')
            result = subprocess.run([sys.executable, "-B", str(SCRIPT), "--input", str(path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stderr)["lint_status"], "unknown")
            result = self.run_cli(d, report(), "--limit", "0")
            self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
