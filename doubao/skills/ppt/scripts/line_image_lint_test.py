from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import xml_lint


class LineImageOverlapTest(unittest.TestCase):
    @staticmethod
    def image(x=200, y=100, width=200, height=200, *, element_id="photo", rotation=0, alpha=1):
        identifier = f' id="{element_id}"' if element_id else ""
        return (
            f'<img{identifier} src="fixture" topLeftX="{x}" topLeftY="{y}" '
            f'width="{width}" height="{height}" rotation="{rotation}" alpha="{alpha}"/>'
        )

    @staticmethod
    def line(start, end, *, element_id="leader", alpha=1):
        identifier = f' id="{element_id}"' if element_id else ""
        return (
            f'<line{identifier} startX="{start[0]}" startY="{start[1]}" '
            f'endX="{end[0]}" endY="{end[1]}" alpha="{alpha}">'
            '<border width="2" color="rgba(0,0,0,1)"/></line>'
        )

    @staticmethod
    def text(x, y, *, element_id="label", text="自行车注释", width=120, height=24):
        return (
            f'<shape id="{element_id}" type="text" topLeftX="{x}" topLeftY="{y}" '
            f'width="{width}" height="{height}">'
            '<content fontSize="16" fontFamily="思源黑体" color="rgba(31,35,41,1)" '
            f'autoFit="shape-auto-fit" wrap="false"><p>{text}</p></content></shape>'
        )

    @staticmethod
    def polyline():
        return (
            '<polyline id="elbow" type="bent-connector2" topLeftX="100" topLeftY="200" '
            'width="400" height="80"><border width="2" color="rgba(0,0,0,1)"/></polyline>'
        )

    @staticmethod
    def report(*nodes, width=960, height=540):
        report = xml_lint.lint_xml(
            f'<presentation xmlns="{xml_lint.SML_NAMESPACE}" width="{width:g}" height="{height:g}">'
            f"<slide><data>{''.join(nodes)}</data></slide></presentation>"
        )
        schema_issues = [
            issue
            for issue in [
                *report["document"]["errors"],
                *(issue for slide in report["slides"] for issue in slide["issues"]),
            ]
            if issue["code"].startswith("sxsd_")
        ]
        if schema_issues:
            raise AssertionError(schema_issues)
        return report

    @staticmethod
    def findings(report):
        return [
            issue for slide in report["slides"] for issue in slide["issues"] if issue["code"] == "line_image_overlap"
        ]

    def test_obvious_intersection_is_a_nonblocking_screenshot_warning(self):
        report = self.report(self.image(), self.line((100, 200), (500, 200)))
        findings = self.findings(report)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["level"], "warning")
        self.assertNotIn("screenshot", findings[0]["hint"])
        self.assertGreater(findings[0]["measurement"]["intersection_length"], 0)
        self.assertEqual(report["summary"]["status"], "needs_screenshot_review")
        self.assertTrue(report["summary"]["release_ready"])

    def test_annotation_intent_is_not_inferred_or_suppressed(self):
        nodes = [self.image(), self.line((300, 200), (600, 200)), self.text(608, 188)]
        slide_xml = f'<slide xmlns="{xml_lint.SML_NAMESPACE}"><data>{"".join(nodes)}</data></slide>'
        elements = xml_lint.extract_elements(slide_xml)
        source_paths = xml_lint.build_source_xml_paths(slide_xml, 1)
        xml_lint.attach_source_xml_paths(elements, source_paths)

        with mock.patch.object(xml_lint, "estimate_text_visual_bbox", side_effect=AssertionError("text scan")):
            findings = xml_lint.detect_line_image_overlaps(slide_xml, elements, source_paths)

        self.assertEqual(len(findings), 1)
        self.assertNotIn("relationship", findings[0])
        self.assertNotIn("endpoint_labels", findings[0]["measurement"])

    def test_nonintersection_edge_touch_and_tiny_graze_are_ignored(self):
        lines = [
            self.line((100, 50), (150, 90)),
            self.line((100, 100), (500, 100)),
            self.line((200, 200), (204, 200)),
        ]
        for line in lines:
            with self.subTest(line=line):
                self.assertEqual(self.findings(self.report(self.image(), line)), [])

    def test_polyline_is_outside_the_rule_scope(self):
        self.assertEqual(self.findings(self.report(self.image(), self.polyline())), [])

    def test_invisible_degenerate_and_full_canvas_background_objects_are_ignored(self):
        cases = [
            (self.image(alpha=0), self.line((100, 200), (500, 200))),
            (self.image(), self.line((100, 200), (500, 200), alpha=0)),
            (self.image(), self.line((300, 200), (300, 200))),
            (self.image(0, 0, 960, 540), self.line((100, 200), (800, 200))),
        ]
        for picture, line in cases:
            with self.subTest(picture=picture, line=line):
                self.assertEqual(self.findings(self.report(picture, line)), [])

    def test_rotated_image_uses_its_actual_footprint(self):
        picture = self.image(200, 200, 200, 40, rotation=90)

        self.assertEqual(self.findings(self.report(picture, self.line((210, 210), (250, 210)))), [])
        self.assertEqual(len(self.findings(self.report(picture, self.line((250, 130), (350, 130))))), 1)

    def test_anonymous_elements_have_structured_locators(self):
        findings = self.findings(
            self.report(self.image(element_id=None), self.line((100, 200), (500, 200), element_id=None))
        )

        self.assertEqual(findings[0]["elements"], ["slide[1]/data/line[1]", "slide[1]/data/img[1]"])
        self.assertEqual(
            [related["xml_path"] for related in findings[0]["related_objects"]],
            findings[0]["elements"],
        )

    def test_existing_line_text_error_remains_blocking(self):
        report = self.report(self.text(200, 188, width=160), self.line((100, 200), (500, 200)))

        self.assertEqual(self.findings(report), [])
        self.assertIn("bbox_overlap", [issue["code"] for issue in report["slides"][0]["errors"]])
        self.assertEqual(report["summary"]["status"], "blocked")

    def test_cli_warning_does_not_hide_other_errors(self):
        xml = (
            f'<slide xmlns="{xml_lint.SML_NAMESPACE}"><data>{self.image()}'
            f"{self.line((100, 200), (700, 200))}{self.text(500, 188, element_id='body')}</data></slide>"
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mixed.xml"
            path.write_text(xml, encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, "-B", str(Path(xml_lint.__file__).resolve()), "--input", str(path)],
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(completed.returncode, 1, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual([issue["level"] for issue in self.findings(report)], ["warning"])
        self.assertIn("bbox_overlap", [issue["code"] for issue in report["slides"][0]["errors"]])
        self.assertFalse(report["summary"]["release_ready"])


if __name__ == "__main__":
    unittest.main()
