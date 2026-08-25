# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import itertools
import json
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest import mock

import sxsd_validator
import xml_lint


class XmlTextOverlapLintGeometryTest(unittest.TestCase):
    def assertNoXmlTextOverlapLintErrors(self, result: dict, sample_name: str) -> None:
        issue_summaries = []
        for slide in result.get("slides", []):
            for issue in slide.get("issues", []):
                issue_summaries.append(
                    f"slide {slide['slide_number']}: {issue['level']} {issue['code']} {issue['message']}"
                )
        if result.get("issues"):
            for issue in result["issues"]:
                issue_summaries.append(f"{issue['level']} {issue['code']} {issue['message']}")
        self.assertEqual(
            result["summary"]["error_count"],
            0,
            f"{sample_name} has XML text overlap lint errors:\n" + "\n".join(issue_summaries),
        )

    def test_cli_suggests_input_flag_for_positional_argument(self) -> None:
        script_path = Path(xml_lint.__file__).resolve()
        input_path = "/sandboxdata/workspace/file/full_presentation.xml"

        completed = subprocess.run(
            [sys.executable, str(script_path), input_path],
            capture_output=True,
            check=False,
            text=True,
        )

        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stdout, "")
        self.assertEqual(
            completed.stderr,
            f"xml-lint error: unexpected argument: {input_path}, need --input\n",
        )

    def test_cli_preserves_requested_symlink_path_in_result(self) -> None:
        script_path = Path(xml_lint.__file__).resolve()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            resolved_path = temp_path / "resolved.xml"
            requested_path = temp_path / "requested.xml"
            resolved_path.write_text(
                '<presentation xmlns="https://www.larkoffice.com/sml/2.0" width="960" height="540">'
                '<slide xmlns="https://www.larkoffice.com/sml/2.0"><data>'
                '<shape type="text" topLeftX="10" topLeftY="10" width="100" height="30">'
                '<content><p><span>Test</span></p></content>'
                '</shape></data></slide>'
                '</presentation>',
                encoding="utf-8",
            )
            requested_path.symlink_to(resolved_path)

            completed = subprocess.run(
                [sys.executable, str(script_path), "--input", str(requested_path)],
                capture_output=True,
                check=False,
                text=True,
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["file"], str(requested_path))

    def test_cli_reports_structured_slide_sxsd_error_outside_skill_directory(self) -> None:
        script_path = Path(xml_lint.__file__).resolve()
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "invalid-slide.xml"
            input_path.write_text(
                """
                <slide xmlns="https://www.larkoffice.com/sml/2.0">
                  <data><shape type="text" topLeftX="10" topLeftY="20" width="300"/></data>
                </slide>
                """,
                encoding="utf-8",
            )

            completed = subprocess.run(
                [sys.executable, str(script_path), "--input", str(input_path)],
                cwd=temp_dir,
                capture_output=True,
                check=False,
                text=True,
            )

        result = json.loads(completed.stdout)
        issue = result["slides"][0]["errors"][0]
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stderr, "")
        self.assertEqual(issue["code"], "sxsd_missing_required_attr")
        self.assertEqual(issue["path"], "slide/data/shape")
        self.assertEqual(issue["attr"], "height")
        self.assertEqual(issue["target"]["slide_number"], 1)
        self.assertTrue(issue["hint"])

    def test_xml_lint_accepts_inline_fixture_xml_samples(self) -> None:
        samples = {
            "image-led-cover": """
                <presentation xmlns="https://www.larkoffice.com/sml/2.0" width="960" height="540">
                  <slide xmlns="https://www.larkoffice.com/sml/2.0">
                    <style><fill><fillColor color="rgb(15,23,42)"/></fill></style>
                    <data>
                      <img src="tok" topLeftX="560" topLeftY="0" width="400" height="540"/>
                      <shape type="text" topLeftX="64" topLeftY="150" width="420" height="70">
                        <content textType="title"><p><span fontSize="42">Quarterly Review</span></p></content>
                      </shape>
                      <shape type="text" topLeftX="64" topLeftY="235" width="420" height="36">
                        <content textType="sub-headline"><p><span fontSize="20">Focus, progress, and next steps</span></p></content>
                      </shape>
                    </data>
                  </slide>
                </presentation>
            """,
            "content-grid": """
                <presentation xmlns="https://www.larkoffice.com/sml/2.0" width="960" height="540">
                  <slide xmlns="https://www.larkoffice.com/sml/2.0">
                    <data>
                      <shape type="text" topLeftX="60" topLeftY="44" width="620" height="46">
                        <content textType="title"><p><span fontSize="30">Execution Snapshot</span></p></content>
                      </shape>
                      <shape type="rect" topLeftX="60" topLeftY="126" width="250" height="150"/>
                      <shape type="text" topLeftX="84" topLeftY="152" width="200" height="36">
                        <content textType="headline"><p><span fontSize="22">Plan</span></p></content>
                      </shape>
                      <shape type="rect" topLeftX="355" topLeftY="126" width="250" height="150"/>
                      <shape type="text" topLeftX="379" topLeftY="152" width="200" height="36">
                        <content textType="headline"><p><span fontSize="22">Build</span></p></content>
                      </shape>
                      <shape type="rect" topLeftX="650" topLeftY="126" width="250" height="150"/>
                      <shape type="text" topLeftX="674" topLeftY="152" width="200" height="36">
                        <content textType="headline"><p><span fontSize="22">Launch</span></p></content>
                      </shape>
                    </data>
                  </slide>
                </presentation>
            """,
        }
        self.assertTrue(samples)
        for sample_name, sample_xml in samples.items():
            with self.subTest(sample=sample_name):
                result = xml_lint.lint_xml(
                    sample_xml,
                    sample_name,
                )
                self.assertNoXmlTextOverlapLintErrors(result, sample_name)

    def test_lint_xml_reports_unescaped_ampersand_in_text(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape type="text" topLeftX="80" topLeftY="80" width="300" height="60">
                  <content textType="body"><p>Q&A</p></content>
                </shape>
              </data>
            </slide>
            """
        )
        issue = result["issues"][0]
        self.assertEqual(result["summary"]["error_count"], 1)
        self.assertEqual(issue["code"], "xml_not_well_formed")
        self.assertIsInstance(issue["line"], int)
        self.assertIsInstance(issue["column"], int)
        self.assertIn("Q&A", issue["context"])
        self.assertIn("&amp;", issue["hint"])

    def test_lint_xml_reports_unescaped_ampersand_in_attribute(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape type="text" topLeftX="80" topLeftY="80" width="300" height="60">
                  <content textType="body"><p><a href="https://example.com/?a=1&b=2">link</a></p></content>
                </shape>
              </data>
            </slide>
            """
        )
        issue = result["issues"][0]
        self.assertEqual(issue["code"], "xml_not_well_formed")
        self.assertIn("attribute", issue["hint"])
        self.assertIn("a=1&amp;b=2", issue["hint"])

    def test_lint_xml_reports_mismatched_xml_tag(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape type="text" topLeftX="80" topLeftY="80" width="300" height="60">
                  <content textType="body"><p>Broken XML</content>
                </shape>
              </data>
            </slide>
            """
        )
        issue = result["issues"][0]
        self.assertEqual(result["summary"]["slide_count"], 0)
        self.assertEqual(result["summary"]["error_count"], 1)
        self.assertEqual(issue["code"], "xml_not_well_formed")
        self.assertIsInstance(issue["line"], int)
        self.assertIsInstance(issue["column"], int)
        self.assertIn("Broken XML", issue["context"])
        self.assertEqual(issue["related_objects"], [])
        self.assertNotIn("Locate via related_objects[].xml_path.", issue["hint"])

    def test_lint_xml_rejects_prefixed_sml_tags(self) -> None:
        result = xml_lint.lint_xml(
            """
            <ns0:slide xmlns:ns0="https://www.larkoffice.com/sml/2.0">
              <ns0:data>
                <sml:shape xmlns:sml="https://www.larkoffice.com/sml/2.0" type="text" topLeftX="80" topLeftY="80" width="300" height="60">
                  <sml:content textType="body"><sml:p>Prefixed SML</sml:p></sml:content>
                </sml:shape>
              </ns0:data>
            </ns0:slide>
            """
        )
        issues = result["issues"]
        self.assertEqual(result["summary"]["error_count"], 5)
        self.assertEqual([issue["code"] for issue in issues], ["sml_prefixed_tag"] * 5)
        self.assertEqual(issues[0]["tag"], "ns0:slide")
        self.assertIn("default namespace", issues[0]["hint"])
        self.assertEqual({issue["namespace"] for issue in issues}, {SML_NAMESPACE})

    def test_lint_xml_reports_bound_namespace_for_prefixed_sml_tags(self) -> None:
        for namespace in (
            "http://www.larkoffice.com/sml/2.0",
            "/sml/2.0",
            SML_NAMESPACE,
        ):
            with self.subTest(namespace=namespace):
                result = xml_lint.lint_xml(
                    f"""
                    <sml:slide xmlns:sml="{namespace}">
                      <sml:data>
                        <sml:shape type="text" topLeftX="80" topLeftY="80" width="300" height="60">
                          <sml:content textType="body"><sml:p>Prefixed SML</sml:p></sml:content>
                        </sml:shape>
                      </sml:data>
                    </sml:slide>
                    """
                )
                issues = result["issues"]
                self.assertEqual([issue["code"] for issue in issues], ["sml_prefixed_tag"] * 5)
                self.assertEqual({issue["namespace"] for issue in issues}, {namespace})

    def test_lint_xml_accepts_server_readback_slide_without_namespace(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide id="server-slide-id">
              <data>
                <shape id="server-shape-id" type="text" topLeftX="80" topLeftY="80" width="300" height="60">
                  <content textType="body"><p>Unprefixed SML</p></content>
                </shape>
              </data>
            </slide>
            """
        )
        self.assertEqual(result["summary"]["error_count"], 0)

    def test_lint_xml_accepts_server_readback_presentation_short_namespace(self) -> None:
        result = xml_lint.lint_xml(
            """
            <presentation xmlns="/sml/2.0" width="960" height="540" id="server-presentation-id">
              <slide id="server-slide-id">
                <data>
                  <shape id="server-shape-id" type="text" topLeftX="80" topLeftY="80" width="300" height="60">
                    <content textType="body"><p>Server readback presentation</p></content>
                  </shape>
                </data>
              </slide>
            </presentation>
            """
        )

        self.assertEqual(result["summary"]["slide_count"], 1)
        self.assertEqual(result["summary"]["error_count"], 0)

    def test_lint_xml_accepts_server_readback_presentation_https_namespace(self) -> None:
        result = xml_lint.lint_xml(
            """
            <presentation xmlns="https://www.larkoffice.com/sml/2.0" width="960" height="540" id="server-presentation-id">
              <slide id="server-slide-id">
                <data>
                  <shape id="server-shape-id" type="text" topLeftX="80" topLeftY="80" width="300" height="60">
                    <content textType="body"><p>Server readback presentation</p></content>
                  </shape>
                </data>
              </slide>
            </presentation>
            """
        )

        self.assertEqual(result["summary"]["slide_count"], 1)
        self.assertEqual(result["summary"]["error_count"], 0)

    def test_lint_xml_accepts_legacy_http_namespace(self) -> None:
        result = xml_lint.lint_xml(
            """
            <presentation xmlns="http://www.larkoffice.com/sml/2.0" width="960" height="540" id="legacy-http-id">
              <slide id="server-slide-id">
                <data>
                  <shape id="server-shape-id" type="text" topLeftX="80" topLeftY="80" width="300" height="60">
                    <content textType="body"><p>Legacy HTTP namespace</p></content>
                  </shape>
                </data>
              </slide>
            </presentation>
            """
        )

        self.assertEqual(result["summary"]["slide_count"], 1)
        self.assertEqual(result["summary"]["error_count"], 0)

    def test_lint_xml_rejects_server_readback_presentation_wrong_namespace(self) -> None:
        result = xml_lint.lint_xml(
            """
            <presentation xmlns="https://example.com/not-sml" width="960" height="540">
              <slide/>
            </presentation>
            """
        )

        self.assertEqual(result["summary"]["error_count"], 1)
        self.assertEqual(result["issues"][0]["code"], "sxsd_invalid_namespace")

    def test_lint_xml_rejects_xml_declaration(self) -> None:
        result = xml_lint.lint_xml(
            '<?xml version="1.0"?><slide xmlns="https://www.larkoffice.com/sml/2.0"><data/></slide>'
        )

        self.assertEqual(result["summary"]["error_count"], 1)
        self.assertEqual(result["issues"][0]["code"], "sxsd_unsupported_declaration")

    def test_lint_xml_reports_missing_required_sxsd_attribute(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data><shape type="text" topLeftX="80" topLeftY="80" width="300"/></data>
            </slide>
            """
        )

        self.assertEqual(result["summary"]["error_count"], 1)
        self.assertNotIn("issues", result)
        issue = result["slides"][0]["issues"][0]
        self.assertEqual(issue["code"], "sxsd_missing_required_attr")
        self.assertEqual(issue["attr"], "height")

    def test_lint_xml_rejects_child_order_that_violates_xsd_sequence(self) -> None:
        result = xml_lint.lint_xml(
            """
            <presentation xmlns="https://www.larkoffice.com/sml/2.0" width="960" height="540">
              <slide/>
              <title>Late title</title>
            </presentation>
            """
        )

        self.assertEqual(result["summary"]["error_count"], 1)
        self.assertEqual(result["issues"][0]["code"], "sxsd_invalid_child_order")

    def test_lint_xml_accepts_escaped_entities_without_suspicious_entity_warning(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape type="text" topLeftX="80" topLeftY="80" width="300" height="60">
                  <content textType="body"><p>Q&amp;A</p></content>
                </shape>
              </data>
            </slide>
            """
        )
        self.assertEqual(result["summary"]["error_count"], 0)
        self.assertNotIn("issues", result)

    def test_lint_xml_accepts_chinese_full_width_punctuation(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape type="text" topLeftX="80" topLeftY="80" width="620" height="90">
                  <content textType="body"><p>承诺：按期交付；持续复盘｜风险透明</p></content>
                </shape>
              </data>
            </slide>
            """
        )
        self.assertEqual(result["summary"]["error_count"], 0)

    def test_lint_xml_single_slide_reports_out_of_canvas_and_blank_slide_errors(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape type="text" topLeftX="1000" topLeftY="500" width="120" height="80">
                  <content textType="body"><p>Body text outside the canvas</p></content>
                </shape>
              </data>
            </slide>
            """
        )
        self.assertEqual(result["slide_size"], {"width": 960, "height": 540})
        self.assertEqual(result["summary"]["slide_count"], 1)
        self.assertEqual(result["summary"]["error_count"], 2)
        self.assertEqual(
            [issue["code"] for issue in result["slides"][0]["errors"]],
            ["shape_out_of_canvas", "blank_slide"],
        )

    def test_lint_xml_preserves_presentation_canvas_and_slide_order(self) -> None:
        result = xml_lint.lint_xml(
            """
            <presentation xmlns="https://www.larkoffice.com/sml/2.0" width="1280" height="720">
              <slide xmlns="https://www.larkoffice.com/sml/2.0">
                <data>
                  <shape id="first" type="text" topLeftX="80" topLeftY="80" width="300" height="60">
                    <content textType="body"><p>First slide</p></content>
                  </shape>
                </data>
              </slide>
              <slide xmlns="https://www.larkoffice.com/sml/2.0">
                <data>
                  <img id="second" src="tok" topLeftX="100" topLeftY="120" width="240" height="160"/>
                  <shape id="second-shape" type="text" topLeftX="80" topLeftY="80" width="300" height="60">
                    <content textType="body"><p>Second slide</p></content>
                  </shape>
                </data>
              </slide>
            </presentation>
            """
        )
        self.assertEqual(result["slide_size"], {"width": 1280, "height": 720})
        self.assertEqual(result["summary"]["slide_count"], 2)
        self.assertEqual([slide["slide_number"] for slide in result["slides"]], [1, 2])
        self.assertEqual([slide["element_count"] for slide in result["slides"]], [1, 2])
        self.assertEqual(result["summary"]["error_count"], 0)
        self.assertEqual(result["summary"]["warning_count"], 0)

    def test_lint_xml_handles_self_closing_slide_before_normal_slide(self) -> None:
        result = xml_lint.lint_xml(
            """
            <presentation xmlns="https://www.larkoffice.com/sml/2.0" width="960" height="540">
              <slide/>
              <slide>
                <data>
                  <shape type="text" topLeftX="80" topLeftY="80" width="300" height="60">
                    <content textType="body"><p>Second slide</p></content>
                  </shape>
                </data>
              </slide>
            </presentation>
            """
        )

        self.assertEqual(result["summary"]["slide_count"], 2)
        self.assertEqual(
            [issue["code"] for issue in result["slides"][0]["errors"]],
            ["blank_slide"],
        )
        self.assertEqual(result["slides"][1]["status"], "passed")

    def test_lint_xml_keeps_trailing_self_closing_slide(self) -> None:
        result = xml_lint.lint_xml(
            """
            <presentation xmlns="https://www.larkoffice.com/sml/2.0" width="960" height="540">
              <slide>
                <data>
                  <shape type="text" topLeftX="80" topLeftY="80" width="300" height="60">
                    <content textType="body"><p>First slide</p></content>
                  </shape>
                </data>
              </slide>
              <slide/>
            </presentation>
            """
        )

        self.assertEqual(result["summary"]["slide_count"], 2)
        self.assertEqual(
            [issue["code"] for issue in result["slides"][1]["errors"]],
            ["blank_slide"],
        )

    def test_lint_xml_ignores_slide_markup_inside_xml_comments(self) -> None:
        result = xml_lint.lint_xml(
            """
            <presentation xmlns="https://www.larkoffice.com/sml/2.0" width="960" height="540">
              <slide>
                <data>
                  <shape type="text" topLeftX="80" topLeftY="80" width="300" height="60">
                    <content textType="body"><p>Real slide</p></content>
                  </shape>
                </data>
              </slide>
              <!-- Old draft: <slide id="ghost"/> -->
            </presentation>
            """
        )

        self.assertEqual(result["summary"]["slide_count"], 1)
        self.assertEqual(result["slides"][0]["status"], "passed")

    def test_lint_xml_ignores_invalid_slide_markup_inside_xml_comments(self) -> None:
        result = xml_lint.lint_xml(
            """
            <presentation xmlns="https://www.larkoffice.com/sml/2.0" width="960" height="540">
              <slide><data/></slide>
              <!-- Old draft: <slide bogus="x"/> -->
            </presentation>
            """
        )

        self.assertEqual(result["summary"]["slide_count"], 1)
        self.assertEqual(
            [issue["code"] for issue in result["slides"][0]["errors"]],
            ["blank_slide"],
        )

    def test_lint_xml_skips_only_invalid_slide_and_continues_geometry_checks(self) -> None:
        result = xml_lint.lint_xml(
            """
            <presentation xmlns="https://www.larkoffice.com/sml/2.0" width="960" height="540">
              <slide>
                <data>
                  <shape id="invalid" type="text" topLeftX="1000" topLeftY="80" width="300">
                    <content textType="body"><p>Missing height</p></content>
                  </shape>
                </data>
              </slide>
              <slide>
                <data>
                  <shape id="outside" type="text" topLeftX="1000" topLeftY="80" width="120" height="60">
                    <content textType="body"><p>Outside canvas</p></content>
                  </shape>
                </data>
              </slide>
            </presentation>
            """
        )

        self.assertEqual(result["summary"]["slide_count"], 2)
        self.assertEqual(result["slides"][0]["element_count"], 0)
        self.assertEqual(
            [issue["code"] for issue in result["slides"][0]["errors"]],
            ["sxsd_missing_required_attr"],
        )
        self.assertNotIn(
            "shape_out_of_canvas",
            [issue["code"] for issue in result["slides"][0]["issues"]],
        )
        self.assertIn(
            "shape_out_of_canvas",
            [issue["code"] for issue in result["slides"][1]["errors"]],
        )

    def test_lint_xml_scopes_invalid_slide_root_attribute_to_that_slide(self) -> None:
        result = xml_lint.lint_xml(
            """
            <presentation xmlns="https://www.larkoffice.com/sml/2.0" width="960" height="540">
              <slide bogusAttr="oops">
                <data><shape type="rect" topLeftX="80" topLeftY="80" width="100" height="100"/></data>
              </slide>
              <slide>
                <data><shape type="rect" topLeftX="1000" topLeftY="80" width="100" height="100"/></data>
              </slide>
            </presentation>
            """
        )

        self.assertEqual(result["summary"]["slide_count"], 2)
        self.assertEqual(
            [issue["code"] for issue in result["slides"][0]["errors"]],
            ["sxsd_unsupported_attr"],
        )
        self.assertIn(
            "shape_out_of_canvas",
            [issue["code"] for issue in result["slides"][1]["errors"]],
        )

    def test_lint_xml_allows_svg_subtree_inside_embed(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="http://www.larkoffice.com/sml/2.0">
              <data>
                <embed topLeftX="80" topLeftY="120" width="240" height="140">
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 140">
                    <rect x="10" y="10" width="220" height="120" rx="12" fill="#EFF6FF"/>
                    <circle cx="70" cy="70" r="34" fill="#2563EB"/>
                    <text x="130" y="76" font-size="18" fill="#1E3A8A">SVG OK</text>
                    <foreignObject x="0" y="0" width="1" height="1">
                      <embed xmlns="http://www.w3.org/1999/xhtml">
                        <rect xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>
                      </embed>
                    </foreignObject>
                  </svg>
                </embed>
              </data>
            </slide>
            """
        )
        codes = [issue["code"] for issue in result["slides"][0]["issues"]]
        self.assertNotIn("sxsd_unsupported_tag", codes)
        self.assertNotIn("sxsd_unsupported_attr", codes)
        self.assertEqual(result["summary"]["error_count"], 0)

    def test_lint_xml_enforces_embed_svg_contract(self) -> None:
        cases = [
            ("missing SVG", "", "sxsd_missing_required_child"),
            ("wrong namespace", '<svg viewBox="0 0 20 20"/>', "sxsd_unsupported_tag"),
            (
                "multiple SVG roots",
                '<svg xmlns="http://www.w3.org/2000/svg"/><svg xmlns="http://www.w3.org/2000/svg"/>',
                "sxsd_too_many_children",
            ),
            (
                "non-SVG root element",
                '<rect xmlns="http://www.w3.org/2000/svg" width="20" height="20"/>',
                "sxsd_unexpected_child",
            ),
            (
                "SVG after reflection",
                '<reflection/><svg xmlns="http://www.w3.org/2000/svg"/>',
                "sxsd_invalid_child_order",
            ),
        ]
        for name, children, expected_code in cases:
            with self.subTest(name=name):
                result = xml_lint.lint_xml(
                    f"""
                    <slide xmlns="http://www.larkoffice.com/sml/2.0">
                      <data>
                        <embed topLeftX="80" topLeftY="120" width="240" height="140">
                          {children}
                        </embed>
                      </data>
                    </slide>
                    """
                )
                codes = [issue["code"] for issue in result["slides"][0]["issues"]]
                self.assertIn(expected_code, codes)

    def test_lint_xml_enforces_embed_svg_root_for_readback_namespaces(self) -> None:
        document_templates = [
            ("bare slide", "<slide>{content}</slide>"),
            (
                "short namespace",
                '<presentation xmlns="/sml/2.0" width="960" height="540">'
                "<slide>{content}</slide>"
                "</presentation>",
            ),
            (
                "HTTPS namespace",
                '<presentation xmlns="https://www.larkoffice.com/sml/2.0" width="960" height="540">'
                "<slide>{content}</slide>"
                "</presentation>",
            ),
        ]
        embed_template = """
            <data>
              <embed topLeftX="80" topLeftY="120" width="240" height="140">
                {svg_root}
              </embed>
            </data>
        """
        roots = [
            ("valid SVG root", '<svg xmlns="http://www.w3.org/2000/svg"/>', False),
            (
                "non-SVG root element",
                '<rect xmlns="http://www.w3.org/2000/svg" width="20" height="20"/>',
                True,
            ),
        ]

        for document_name, document_template in document_templates:
            for root_name, svg_root, should_error in roots:
                with self.subTest(document=document_name, root=root_name):
                    content = embed_template.format(svg_root=svg_root)
                    result = xml_lint.lint_xml(
                        document_template.format(content=content)
                    )
                    codes = [
                        issue["code"]
                        for slide in result["slides"]
                        for issue in slide["issues"]
                    ]
                    if should_error:
                        self.assertIn("sxsd_unexpected_child", codes)
                    else:
                        self.assertNotIn("sxsd_unexpected_child", codes)
                        self.assertEqual(result["summary"]["error_count"], 0)

    def test_lint_xml_reports_sxsd_unsupported_tag_with_alias_hint(self) -> None:
        cases = [
            ("textbox", '<textbox topLeftX="80" topLeftY="80" width="300" height="60">Text</textbox>', '<shape type="text">'),
            ("image", '<image src="tok" topLeftX="80" topLeftY="80" width="300" height="180"/>', "<img>"),
        ]
        for tag_name, element_xml, expected_hint in cases:
            with self.subTest(tag=tag_name):
                result = xml_lint.lint_xml(
                    f"""
                    <slide xmlns="https://www.larkoffice.com/sml/2.0">
                      <data>{element_xml}</data>
                    </slide>
                    """
                )
                slide_issues = result["slides"][0]["issues"]
                issue = next(
                    issue for issue in slide_issues if issue["code"] == "sxsd_unsupported_tag"
                )
                self.assertEqual(result["summary"]["error_count"], 1)
                self.assertEqual(
                    [reported["code"] for reported in slide_issues],
                    ["sxsd_unsupported_tag"],
                )
                self.assertEqual(issue["code"], "sxsd_unsupported_tag")
                self.assertEqual(issue["tag"], tag_name)
                self.assertIn(expected_hint, issue["hint"])

    def test_lint_xml_reports_sxsd_unsupported_attr_with_alias_hint(self) -> None:
        cases = [
            ("shape", "x", "topLeftX", '<shape type="text" x="80" topLeftY="80" width="300" height="60"><content><p>Text</p></content></shape>'),
            ("shape", "heigth", "height", '<shape type="text" topLeftX="80" topLeftY="80" width="300" heigth="60"><content><p>Text</p></content></shape>'),
            ("content", "fontColor", "color", '<shape type="text" topLeftX="80" topLeftY="80" width="300" height="60"><content fontColor="rgba(0, 0, 0, 1)"><p>Text</p></content></shape>'),
        ]
        for tag_name, attr_name, expected_attr, element_xml in cases:
            with self.subTest(attr=attr_name):
                result = xml_lint.lint_xml(
                    f"""
                    <slide xmlns="https://www.larkoffice.com/sml/2.0">
                      <data>{element_xml}</data>
                    </slide>
                    """
                )
                slide_issues = result["slides"][0]["issues"]
                issue = next(
                    issue for issue in slide_issues if issue["code"] == "sxsd_unsupported_attr"
                )
                self.assertEqual(result["summary"]["error_count"], 1)
                self.assertEqual(
                    [reported["code"] for reported in slide_issues],
                    ["sxsd_unsupported_attr"],
                )
                self.assertEqual(issue["code"], "sxsd_unsupported_attr")
                self.assertEqual(issue["tag"], tag_name)
                self.assertEqual(issue["attr"], attr_name)
                self.assertIn(expected_attr, issue["hint"])

    def test_lint_xml_keeps_unrelated_unsupported_and_missing_attrs(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape type="text" bogus="x" topLeftX="80" topLeftY="80" width="300"/>
              </data>
            </slide>
            """
        )

        self.assertEqual(
            [issue["code"] for issue in result["slides"][0]["issues"]],
            ["sxsd_unsupported_attr", "sxsd_missing_required_attr"],
        )

    def test_lint_xml_keeps_missing_attrs_when_suggestion_is_ambiguous(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape type="text" topLeft="80" width="300" height="60"/>
              </data>
            </slide>
            """
        )

        self.assertEqual(
            [issue["code"] for issue in result["slides"][0]["issues"]],
            [
                "sxsd_unsupported_attr",
                "sxsd_missing_required_attr",
                "sxsd_missing_required_attr",
            ],
        )

    def test_lint_xml_suppresses_only_missing_attr_that_resolves_ambiguous_suggestion(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape type="text" topLeftXX="80" topLeftY="80" width="300" height="60"/>
              </data>
            </slide>
            """
        )

        self.assertEqual(
            [
                (issue["code"], issue.get("attr"))
                for issue in result["slides"][0]["issues"]
            ],
            [("sxsd_unsupported_attr", "topLeftXX")],
        )

    def test_lint_xml_ignores_server_filled_id_attrs(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide id="server-slide-id" xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="server-shape-id" type="rect" topLeftX="80" topLeftY="80" width="300" height="160">
                  <fill id="server-fill-id" unexpected="value">
                    <fillColor color="rgba(255, 255, 255, 1)"/>
                  </fill>
                </shape>
              </data>
            </slide>
            """
        )

        self.assertEqual(result["summary"]["error_count"], 1)
        self.assertEqual(
            [(issue["tag"], issue["attr"]) for issue in result["slides"][0]["issues"]],
            [("fill", "unexpected")],
        )

    def test_lint_xml_ignores_chart_roundtrip_attrs(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <chart updated="true" topLeftX="80" topLeftY="80" width="300" height="160">
                  <chartPlotArea><chartPlot type="line"/></chartPlotArea>
                  <chartData isStaticData="true">
                    <dim1><chartField name="category" valueType="string">A</chartField></dim1>
                    <dim2><chartField name="value" valueType="number">1</chartField></dim2>
                  </chartData>
                </chart>
              </data>
            </slide>
            """
        )

        self.assertEqual(result["summary"]["error_count"], 0)

    def test_lint_xml_ignores_chart_parsed_values_roundtrip_tags(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <chart topLeftX="80" topLeftY="80" width="300" height="160">
                  <chartPlotArea><chartPlot type="line"/></chartPlotArea>
                  <chartData isStaticData="true">
                    <dim1>
                      <chartField name="category" valueType="string">
                        A<chartParsedValues>A</chartParsedValues>
                      </chartField>
                    </dim1>
                    <dim2><chartField name="value" valueType="number">1</chartField></dim2>
                  </chartData>
                </chart>
              </data>
            </slide>
            """
        )

        self.assertEqual(result["summary"]["error_count"], 0)

    def test_lint_xml_ignores_chart_parsed_values_roundtrip_tag(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <chart topLeftX="80" topLeftY="80" width="300" height="160">
                  <chartPlotArea><chartPlot type="line"/></chartPlotArea>
                  <chartData>
                    <dim1>
                      <chartField name="category" valueType="string">
                        Africa<chartParsedValues>Africa</chartParsedValues>
                      </chartField>
                    </dim1>
                    <dim2><chartField name="value" valueType="number">1</chartField></dim2>
                  </chartData>
                </chart>
              </data>
            </slide>
            """
        )

        self.assertEqual(result["summary"]["error_count"], 0)
        self.assertNotIn("issues", result)

    def test_lint_xml_rejects_chart_parsed_values_outside_chart_field(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape type="rect" topLeftX="80" topLeftY="80" width="300" height="160">
                  <chartParsedValues>unexpected</chartParsedValues>
                </shape>
              </data>
            </slide>
            """
        )

        self.assertEqual(result["summary"]["error_count"], 1)
        self.assertEqual(
            [issue["code"] for issue in result["slides"][0]["issues"]],
            ["sxsd_unsupported_tag"],
        )
        self.assertEqual(
            result["slides"][0]["issues"][0]["path"],
            "slide/data/shape/chartParsedValues",
        )

    def test_lint_xml_limits_chart_roundtrip_attrs_to_matching_tags(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <chart isStaticData="true" topLeftX="80" topLeftY="80" width="300" height="160">
                  <chartPlotArea><chartPlot type="line"/></chartPlotArea>
                  <chartData updated="true">
                    <dim1><chartField name="category" valueType="string">A</chartField></dim1>
                    <dim2><chartField name="value" valueType="number">1</chartField></dim2>
                  </chartData>
                </chart>
              </data>
            </slide>
            """
        )

        self.assertEqual(result["summary"]["error_count"], 2)
        slide_issues = result["slides"][0]["issues"]
        self.assertEqual(
            {(issue["tag"], issue["attr"]) for issue in slide_issues},
            {("chart", "isStaticData"), ("chartData", "updated")},
        )
        self.assertTrue(all(issue["code"] == "sxsd_unsupported_attr" for issue in slide_issues))

    def test_lint_xml_accepts_chart_with_numeric_value_dimension(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <chart topLeftX="80" topLeftY="80" width="300" height="160">
                  <chartPlotArea><chartPlot type="column"/></chartPlotArea>
                  <chartData>
                    <dim1><chartField name="季度">Q1,Q2,Q3,Q4</chartField></dim1>
                    <dim2><chartField name="营收">52,48,55,68</chartField></dim2>
                  </chartData>
                </chart>
              </data>
            </slide>
            """
        )

        self.assertEqual(result["summary"]["error_count"], 0)

    def test_lint_xml_rejects_chart_without_numeric_value_dimension(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <chart topLeftX="80" topLeftY="80" width="300" height="160">
                  <chartPlotArea><chartPlot type="column"/></chartPlotArea>
                  <chartData>
                    <dim1><chartField name="季度">Q1,Q2,Q3,Q4</chartField></dim1>
                    <dim2><chartField name="渠道">直营,分销,线上,其他</chartField></dim2>
                  </chartData>
                </chart>
              </data>
            </slide>
            """
        )

        self.assertEqual(result["summary"]["error_count"], 1)
        issue = result["issues"][0]
        self.assertEqual(issue["code"], "chart_missing_numeric_dimension")
        self.assertEqual(issue["tag"], "chartData")
        self.assertEqual(issue["path"], "slide[1]/data/chart[1]/chartData[1]")
        self.assertEqual(
            issue["target"]["chart_xml_path"], "slide[1]/data/chart[1]"
        )

    def test_lint_xml_chart_dimension_issue_carries_slide_and_chart_locators(self) -> None:
        # Two bad charts on slide 1 plus one on slide 2 must each be independently locatable.
        result = xml_lint.lint_xml(
            """
            <presentation xmlns="https://www.larkoffice.com/sml/2.0" width="960" height="540">
              <slide><data>
                <chart id="chart_a" topLeftX="10" topLeftY="10" width="300" height="160">
                  <chartPlotArea><chartPlot type="column"/></chartPlotArea>
                  <chartData>
                    <dim1><chartField name="a">Q1,Q2</chartField></dim1>
                    <dim2><chartField name="b">x,y</chartField></dim2>
                  </chartData>
                </chart>
                <chart topLeftX="400" topLeftY="10" width="300" height="160">
                  <chartPlotArea><chartPlot type="pie"/></chartPlotArea>
                  <chartData>
                    <dim1><chartField name="c">直营,分销</chartField></dim1>
                    <dim2><chartField name="d">高,低</chartField></dim2>
                  </chartData>
                </chart>
              </data></slide>
              <slide><data>
                <chart topLeftX="10" topLeftY="10" width="300" height="160">
                  <chartPlotArea><chartPlot type="bar"/></chartPlotArea>
                  <chartData>
                    <dim1><chartField name="e">A,B</chartField></dim1>
                    <dim2><chartField name="f">C,D</chartField></dim2>
                  </chartData>
                </chart>
              </data></slide>
            </presentation>
            """
        )

        self.assertEqual(result["summary"]["error_count"], 3)
        paths = [issue["target"]["chart_xml_path"] for issue in result["issues"]]
        self.assertEqual(
            paths,
            [
                "slide[1]/data/chart[1]",
                "slide[1]/data/chart[2]",
                "slide[2]/data/chart[1]",
            ],
        )
        self.assertEqual(result["issues"][0]["target"]["chart_id"], "chart_a")

    def test_lint_xml_chart_dimension_trusts_declared_value_type(self) -> None:
        # valueType="number" satisfies the axis regardless of sample text; both "string" fails even
        # when the text looks numeric, because the author declared it categorical.
        numeric_declared = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <chart topLeftX="80" topLeftY="80" width="300" height="160">
                  <chartPlotArea><chartPlot type="column"/></chartPlotArea>
                  <chartData>
                    <dim1><chartField name="x" valueType="string">Q1,Q2</chartField></dim1>
                    <dim2><chartField name="y" valueType="number">52,48</chartField></dim2>
                  </chartData>
                </chart>
              </data>
            </slide>
            """
        )
        self.assertEqual(numeric_declared["summary"]["error_count"], 0)

        both_string = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <chart topLeftX="80" topLeftY="80" width="300" height="160">
                  <chartPlotArea><chartPlot type="column"/></chartPlotArea>
                  <chartData>
                    <dim1><chartField name="x" valueType="string">1,2</chartField></dim1>
                    <dim2><chartField name="y" valueType="string">3,4</chartField></dim2>
                  </chartData>
                </chart>
              </data>
            </slide>
            """
        )
        self.assertEqual(both_string["summary"]["error_count"], 1)
        self.assertEqual(
            both_string["issues"][0]["code"], "chart_missing_numeric_dimension"
        )

    def test_lint_xml_accepts_chart_numeric_category_dimension(self) -> None:
        # dim1 numeric (years), dim2 labels: the numeric dim1 still drives the value axis.
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <chart topLeftX="80" topLeftY="80" width="300" height="160">
                  <chartPlotArea><chartPlot type="bar"/></chartPlotArea>
                  <chartData>
                    <dim1><chartField name="年份">2021,2022,2023</chartField></dim1>
                    <dim2><chartField name="标签">高,中,低</chartField></dim2>
                  </chartData>
                </chart>
              </data>
            </slide>
            """
        )

        self.assertEqual(result["summary"]["error_count"], 0)

    def test_lint_xml_chart_numeric_dimension_ignores_parsed_values_echo(self) -> None:
        # Readback echoes each value into <chartParsedValues>; the numeric test must read only the
        # author's original run, so a category-only chart still fails despite numeric-looking echoes.
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <chart topLeftX="80" topLeftY="80" width="300" height="160">
                  <chartPlotArea><chartPlot type="column"/></chartPlotArea>
                  <chartData>
                    <dim1>
                      <chartField name="季度">Q1,Q2<chartParsedValues>1</chartParsedValues></chartField>
                    </dim1>
                    <dim2>
                      <chartField name="渠道">直营,分销<chartParsedValues>2</chartParsedValues></chartField>
                    </dim2>
                  </chartData>
                </chart>
              </data>
            </slide>
            """
        )

        self.assertEqual(result["summary"]["error_count"], 1)
        self.assertEqual(
            result["issues"][0]["code"], "chart_missing_numeric_dimension"
        )

    def test_lint_xml_rejects_chart_format_template_placeholder(self) -> None:
        # `format` is an Excel-style number-format code; a "{value}bp" placeholder borrowed from
        # other chart libraries renders its braces verbatim, so each occurrence must be flagged.
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <chart id="chart_bp" topLeftX="80" topLeftY="80" width="300" height="160">
                  <chartPlotArea>
                    <chartPlot type="column">
                      <chartLabels value="true" format="{value}bp"/>
                    </chartPlot>
                    <chartAxes>
                      <chartAxis type="y" position="left">
                        <chartLabel fontSize="9" format="{value}bp"/>
                      </chartAxis>
                    </chartAxes>
                  </chartPlotArea>
                  <chartData>
                    <dim1><chartField name="季度">Q1,Q2,Q3,Q4</chartField></dim1>
                    <dim2><chartField name="利差" valueType="number">16,14,12,10</chartField></dim2>
                  </chartData>
                  <chartTooltip format="{value}bp"/>
                </chart>
              </data>
            </slide>
            """
        )

        self.assertEqual(result["summary"]["error_count"], 3)
        codes = {issue["code"] for issue in result["issues"]}
        self.assertEqual(codes, {"chart_invalid_format_code"})
        tags = sorted(issue["tag"] for issue in result["issues"])
        self.assertEqual(tags, ["chartLabel", "chartLabels", "chartTooltip"])
        for issue in result["issues"]:
            self.assertEqual(issue["target"]["chart_id"], "chart_bp")
            self.assertEqual(issue["target"]["chart_xml_path"], "slide[1]/data/chart[1]")
            self.assertEqual(issue["target"]["format"], "{value}bp")

    def test_lint_xml_accepts_chart_excel_style_format_code(self) -> None:
        # Real number-format codes (0, 0%, #,##0.00) carry no braces and must pass untouched.
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <chart topLeftX="80" topLeftY="80" width="300" height="160">
                  <chartPlotArea>
                    <chartPlot type="column">
                      <chartLabels value="true" format="0"/>
                    </chartPlot>
                    <chartAxes>
                      <chartAxis type="y" position="left">
                        <chartLabel fontSize="9" format="#,##0.00"/>
                      </chartAxis>
                    </chartAxes>
                  </chartPlotArea>
                  <chartData>
                    <dim1><chartField name="季度">Q1,Q2,Q3,Q4</chartField></dim1>
                    <dim2><chartField name="利差" valueType="number">16,14,12,10</chartField></dim2>
                  </chartData>
                  <chartTooltip format="0.00%"/>
                </chart>
              </data>
            </slide>
            """
        )

        self.assertEqual(result["summary"]["error_count"], 0)

    def test_lint_xml_rejects_chart_labels_with_nothing_to_show(self) -> None:
        # value/category/percentage all false leaves the data label empty; value defaults to true,
        # so this only trips when value is explicitly turned off without enabling the other two.
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <chart id="chart_blank" topLeftX="80" topLeftY="80" width="300" height="160">
                  <chartPlotArea>
                    <chartPlot type="column">
                      <chartLabels value="false"/>
                    </chartPlot>
                  </chartPlotArea>
                  <chartData>
                    <dim1><chartField name="季度">Q1,Q2,Q3,Q4</chartField></dim1>
                    <dim2><chartField name="利差" valueType="number">16,14,12,10</chartField></dim2>
                  </chartData>
                </chart>
              </data>
            </slide>
            """
        )

        self.assertEqual(result["summary"]["error_count"], 1)
        issue = result["issues"][0]
        self.assertEqual(issue["code"], "chart_labels_nothing_to_show")
        self.assertEqual(issue["target"]["chart_id"], "chart_blank")
        self.assertEqual(issue["target"]["chart_xml_path"], "slide[1]/data/chart[1]")

    def test_lint_xml_accepts_chart_labels_with_category_only(self) -> None:
        # value explicitly off but category on still has content to render, so it must pass.
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <chart topLeftX="80" topLeftY="80" width="300" height="160">
                  <chartPlotArea>
                    <chartPlot type="column">
                      <chartLabels value="false" category="true"/>
                    </chartPlot>
                  </chartPlotArea>
                  <chartData>
                    <dim1><chartField name="季度">Q1,Q2,Q3,Q4</chartField></dim1>
                    <dim2><chartField name="利差" valueType="number">16,14,12,10</chartField></dim2>
                  </chartData>
                </chart>
              </data>
            </slide>
            """
        )

        self.assertEqual(result["summary"]["error_count"], 0)

    def test_lint_xml_reports_gradient_shorthand_attrs_on_fill_color(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape type="rect" topLeftX="80" topLeftY="80" width="300" height="160">
                  <fill>
                    <fillColor
                      type="gradient"
                      color1="rgba(255, 0, 0, 1)"
                      color2="rgba(0, 0, 255, 1)"
                      angle="45"
                      stop1="0%"
                      stop2="100%"/>
                  </fill>
                </shape>
              </data>
            </slide>
            """
        )
        slide_issues = result["slides"][0]["issues"]
        unsupported_attrs = {issue["attr"] for issue in slide_issues}
        self.assertEqual(result["summary"]["error_count"], 6)
        self.assertEqual(
            unsupported_attrs,
            {"type", "color1", "color2", "angle", "stop1", "stop2"},
        )
        self.assertTrue(all(issue["code"] == "sxsd_unsupported_attr" for issue in slide_issues))
        self.assertTrue(all(issue["tag"] == "fillColor" for issue in slide_issues))

    def test_lint_xml_accepts_chart_field_simple_content_attrs(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <chart topLeftX="80" topLeftY="80" width="520" height="320">
                  <chartPlotArea>
                    <chartPlot type="line"/>
                  </chartPlotArea>
                  <chartData>
                    <dim1>
                      <chartField name="month" valueType="string">Jan, Feb</chartField>
                    </dim1>
                    <dim2>
                      <chartField name="value" valueType="number">1, 2</chartField>
                    </dim2>
                  </chartData>
                </chart>
              </data>
            </slide>
            """
        )
        self.assertEqual(result["summary"]["error_count"], 0)
        self.assertNotIn("issues", result)

    def test_lint_xml_does_not_load_iconpark_index_without_icons(self) -> None:
        original_loader = xml_lint.load_iconpark_icon_types

        def fail_if_loaded() -> set[str]:
            raise AssertionError("iconpark index should not be loaded without <icon iconType>")

        xml_lint.load_iconpark_icon_types = fail_if_loaded
        try:
            result = xml_lint.lint_xml(
                """
                <slide xmlns="https://www.larkoffice.com/sml/2.0">
                  <data>
                    <shape type="text" topLeftX="80" topLeftY="80" width="300" height="60">
                      <content><p>No icons here</p></content>
                    </shape>
                  </data>
                </slide>
                """
            )
        finally:
            xml_lint.load_iconpark_icon_types = original_loader

        self.assertEqual(result["summary"]["error_count"], 0)
        self.assertNotIn("issues", result)

    def test_lint_xml_accepts_iconpark_icon_type_from_index(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <icon iconType="iconpark/Base/setting.svg" topLeftX="80" topLeftY="80" width="48" height="48">
                  <fill><fillColor color="rgba(37, 99, 235, 1)"/></fill>
                </icon>
              </data>
            </slide>
            """
        )
        self.assertEqual(result["summary"]["error_count"], 0)
        self.assertNotIn("issues", result)

    def test_lint_xml_reports_icon_missing_fill_color(self) -> None:
        cases = [
            '<icon iconType="iconpark/Base/setting.svg" topLeftX="80" topLeftY="80" width="48" height="48"/>',
            '<icon iconType="iconpark/Base/setting.svg" topLeftX="80" topLeftY="80" width="48" height="48"><fill/></icon>',
            (
                '<icon iconType="iconpark/Base/setting.svg" topLeftX="80" topLeftY="80" width="48" height="48">'
                "<fill><fillColor/></fill></icon>"
            ),
        ]
        for icon_xml in cases:
            with self.subTest(icon=icon_xml):
                result = xml_lint.lint_xml(
                    f"""
                    <slide xmlns="https://www.larkoffice.com/sml/2.0">
                      <data>{icon_xml}</data>
                    </slide>
                    """
                )

                issue = result["issues"][0]
                self.assertEqual(result["summary"]["error_count"], 1)
                self.assertEqual(issue["code"], "icon_missing_fill_color")
                self.assertEqual(issue["tag"], "icon")

    def test_lint_xml_reports_icon_transparent_fill_color(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <icon iconType="iconpark/Base/setting.svg" topLeftX="80" topLeftY="80" width="48" height="48">
                  <fill><fillColor color="rgba(37, 99, 235, 0)"/></fill>
                </icon>
              </data>
            </slide>
            """
        )
        issue = result["issues"][0]
        self.assertEqual(result["summary"]["error_count"], 1)
        self.assertEqual(issue["code"], "icon_transparent_fill_color")
        self.assertEqual(issue["tag"], "icon")
        self.assertEqual(issue["attr"], "fillColor")

    def test_lint_xml_reports_iconpark_icon_type_outside_index(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <icon iconType="iconpark/Base/settng.svg" topLeftX="80" topLeftY="80" width="48" height="48">
                  <fill><fillColor color="rgba(37, 99, 235, 1)"/></fill>
                </icon>
              </data>
            </slide>
            """
        )
        issue = result["issues"][0]
        self.assertEqual(result["summary"]["error_count"], 1)
        self.assertEqual(issue["code"], "iconpark_unsupported_icon_type")
        self.assertEqual(issue["tag"], "icon")
        self.assertEqual(issue["attr"], "iconType")
        self.assertEqual(issue["iconType"], "iconpark/Base/settng.svg")
        self.assertIn("iconpark-index.json", issue["hint"])
        self.assertIn("iconpark/Base/setting.svg", issue["hint"])

    def test_lint_xml_skips_iconpark_validation_inside_embedded_svg(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="http://www.larkoffice.com/sml/2.0">
              <data>
                <embed topLeftX="80" topLeftY="120" width="240" height="140">
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 140">
                    <rect x="10" y="10" width="220" height="120" fill="#EFF6FF"/>
                    <icon iconType="not-an-iconpark-name"/>
                    <foreignObject x="0" y="0" width="60" height="60">
                      <icon xmlns="http://www.w3.org/1999/xhtml" iconType="not-an-iconpark-name"/>
                    </foreignObject>
                  </svg>
                </embed>
              </data>
            </slide>
            """
        )
        codes = [issue["code"] for issue in result["document"]["errors"]]
        self.assertNotIn("iconpark_unsupported_icon_type", codes)
        self.assertNotIn("icon_missing_fill_color", codes)
        self.assertEqual(result["summary"]["error_count"], 0)

    def test_lint_xml_detects_overlapping_text_boxes(self) -> None:
        result = xml_lint.lint_xml(
            """
            <presentation xmlns="https://www.larkoffice.com/sml/2.0" width="960" height="540">
              <slide xmlns="https://www.larkoffice.com/sml/2.0">
                <data>
                  <shape type="text" topLeftX="80" topLeftY="80" width="300" height="60">
                    <content textType="title"><p>Title</p></content>
                  </shape>
                  <shape type="text" topLeftX="80" topLeftY="80" width="300" height="80">
                    <content textType="body"><p>Body</p></content>
                  </shape>
                </data>
              </slide>
            </presentation>
            """
        )
        self.assertEqual(result["summary"]["error_count"], 1)
        self.assertEqual(result["summary"]["warning_count"], 0)
        self.assertEqual(result["slides"][0]["issues"][0]["code"], "bbox_overlap")

    def test_lint_xml_detects_current_itinerary_cjk_caption_occlusion(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide id="pQO" xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape width="190" height="80" topLeftX="580" topLeftY="170" presetHandlers="0" type="rect" id="blI">
                  <fill><fillColor color="rgba(255, 255, 255, 0.9)"/></fill>
                  <border color="rgba(220, 205, 185, 1)" width="1"/>
                  <content fontSize="16" fontFamily="思源黑体" color="rgba(31, 35, 41, 1)"/>
                </shape>
                <shape width="160" height="25" topLeftX="595" topLeftY="180" type="text" id="blX">
                  <content fontSize="14" fontFamily="思源黑体" color="rgba(120, 80, 40, 1)" bold="true"><p>日照金山</p></content>
                </shape>
                <shape width="160" height="40" topLeftX="595" topLeftY="205" type="text" id="blY">
                  <content textType="caption" fontSize="11" fontFamily="思源黑体" color="rgba(130, 100, 70, 1)"><p>清晨躺在床上看玉龙雪山日照金山奇观</p></content>
                </shape>
                <shape width="180" height="80" topLeftX="730" topLeftY="170" presetHandlers="0" type="rect" id="blH">
                  <fill><fillColor color="rgba(255, 255, 255, 0.9)"/></fill>
                  <border color="rgba(220, 205, 185, 1)" width="1"/>
                  <content fontSize="16" fontFamily="思源黑体" color="rgba(31, 35, 41, 1)"/>
                </shape>
                <shape width="150" height="25" topLeftX="745" topLeftY="180" type="text" id="blp">
                  <content fontSize="14" fontFamily="思源黑体" color="rgba(120, 80, 40, 1)" bold="true"><p>午餐返程</p></content>
                </shape>
                <shape width="150" height="40" topLeftX="745" topLeftY="205" type="text" id="blV">
                  <content textType="caption" fontSize="11" fontFamily="思源黑体" color="rgba(130, 100, 70, 1)"><p>享用特色午餐，带着美好回忆返程</p></content>
                </shape>
                <shape width="190" height="80" topLeftX="580" topLeftY="310" presetHandlers="0" type="rect" id="blP">
                  <fill><fillColor color="rgba(255, 255, 255, 0.9)"/></fill>
                  <border color="rgba(220, 205, 185, 1)" width="1"/>
                  <content fontSize="16" fontFamily="思源黑体" color="rgba(31, 35, 41, 1)"/>
                </shape>
                <shape width="160" height="25" topLeftX="595" topLeftY="320" type="text" id="blG">
                  <content fontSize="14" fontFamily="思源黑体" color="rgba(120, 80, 40, 1)" bold="true"><p>高路徒步</p></content>
                </shape>
                <shape width="160" height="40" topLeftX="595" topLeftY="345" type="text" id="blQ">
                  <content textType="caption" fontSize="11" fontFamily="思源黑体" color="rgba(130, 100, 70, 1)"><p>经典高路徒步，28道拐，龙洞瀑布，中虎跳峡</p></content>
                </shape>
                <shape width="180" height="80" topLeftX="730" topLeftY="310" presetHandlers="0" type="rect" id="blw">
                  <fill><fillColor color="rgba(255, 255, 255, 0.9)"/></fill>
                  <border color="rgba(220, 205, 185, 1)" width="1"/>
                  <content fontSize="16" fontFamily="思源黑体" color="rgba(31, 35, 41, 1)"/>
                </shape>
                <shape width="150" height="25" topLeftX="745" topLeftY="320" type="text" id="blZ">
                  <content fontSize="14" fontFamily="思源黑体" color="rgba(120, 80, 40, 1)" bold="true"><p>伴手礼</p></content>
                </shape>
                <shape width="150" height="40" topLeftX="745" topLeftY="345" type="text" id="blS">
                  <content textType="caption" fontSize="11" fontFamily="思源黑体" color="rgba(130, 100, 70, 1)"><p>酒店精心准备的归途伴手礼，留下难忘纪念</p></content>
                </shape>
              </data>
            </slide>
            """
        )
        overlap_pairs = {tuple(issue["elements"]) for issue in result["slides"][0]["issues"]}
        # Two caption/label pairs overlap; the two neighboring cards also cover the tail of the
        # preceding card's caption. blV additionally trips the width-wrap rule.
        self.assertEqual(result["summary"]["error_count"], 5)
        self.assertIn(("blY", "blV"), overlap_pairs)
        self.assertIn(("blQ", "blS"), overlap_pairs)
        self.assertIn(("blH", "blY"), overlap_pairs)
        self.assertIn(("blw", "blQ"), overlap_pairs)
        wrap_ids = {
            issue["elements"][0]
            for issue in result["slides"][0]["issues"]
            if issue.get("overflow_axis") == "width"
        }
        self.assertEqual(wrap_ids, {"blV"})

    def test_lint_xml_detects_horizontal_text_overflow_across_declared_box_gap(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="source" type="text" topLeftX="80" topLeftY="100" width="160" height="40">
                  <content fontSize="18" wrap="false"><p>这是一个足够长的中文文本用于检测跨越间隙的横向溢出</p></content>
                </shape>
                <shape id="target" type="text" topLeftX="260" topLeftY="100" width="160" height="40">
                  <content fontSize="18"><p>目标</p></content>
                </shape>
              </data>
            </slide>
            """
        )
        self.assertEqual(result["summary"]["warning_count"], 0)
        overlap_issues = [
            issue
            for issue in result["slides"][0]["issues"]
            if issue["code"] == "bbox_overlap"
        ]
        self.assertEqual(len(overlap_issues), 1)
        self.assertEqual(overlap_issues[0]["elements"], ["source", "target"])
        self.assertGreater(overlap_issues[0]["measurement"]["intersection_area"], 0)
        self.assertIsNotNone(overlap_issues[0].get("hint"))
        # The wrap="false" source string is far wider than its 160px box, so it also overflows on the
        # width axis -- the run cannot reflow and is clipped/spills past the edge.
        width_overflow = [
            issue
            for issue in result["slides"][0]["issues"]
            if issue["code"] == "text_may_overflow_shape"
            and issue.get("overflow_axis") == "width"
            and issue["elements"] == ["source"]
        ]
        self.assertEqual(len(width_overflow), 1)

    def test_lint_xml_allows_horizontal_text_with_default_wrap(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="source" type="text" topLeftX="80" topLeftY="100" width="160" height="40">
                  <content fontSize="18"><p>这是一个足够长的中文文本用于检测默认自动换行</p></content>
                </shape>
                <shape id="target" type="text" topLeftX="260" topLeftY="100" width="160" height="40">
                  <content fontSize="18"><p>目标</p></content>
                </shape>
              </data>
            </slide>
            """
        )
        self.assertEqual(result["summary"]["error_count"], 1)
        self.assertEqual(result["summary"]["warning_count"], 0)
        self.assertEqual(result["slides"][0]["issues"][0]["code"], "text_may_overflow_shape")
        self.assertEqual(result["slides"][0]["issues"][0]["level"], "error")
        self.assertEqual(result["slides"][0]["issues"][0]["elements"], ["source"])

    def test_lint_xml_reports_text_out_of_canvas_and_warns_for_text_height(self) -> None:
        result = xml_lint.lint_xml(
            """
            <presentation xmlns="https://www.larkoffice.com/sml/2.0" width="960" height="540">
              <slide xmlns="https://www.larkoffice.com/sml/2.0">
                <data>
                  <shape type="text" topLeftX="80" topLeftY="80" width="180" height="20">
                    <content textType="body" fontSize="18"><p>This paragraph is intentionally much longer than the box can safely contain.</p></content>
                  </shape>
                  <shape type="text" topLeftX="1000" topLeftY="500" width="120" height="80">
                    <content textType="body"><p>Body text outside the canvas</p></content>
                  </shape>
                </data>
              </slide>
            </presentation>
            """
        )
        issue = result["slides"][0]["issues"][0]
        self.assertEqual(result["summary"]["error_count"], 2)
        self.assertEqual(result["summary"]["warning_count"], 0)
        self.assertEqual(issue["code"], "shape_out_of_canvas")
        self.assertEqual(issue["overflow"], {"left": 0, "top": 0, "right": 160, "bottom": 40})

    def test_lint_xml_warns_when_text_may_overflow_its_own_shape(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="overflowing" type="text" topLeftX="80" topLeftY="80" width="360" height="80">
                  <content fontSize="20" lineSpacing="multiple:1.5" autoFit="no-auto-fit">
                    <p>第一段</p><p>第二段</p><p>第三段</p><p>第四段</p>
                  </content>
                </shape>
                <shape id="fitting" type="text" topLeftX="480" topLeftY="80" width="360" height="120">
                  <content fontSize="20" lineSpacing="multiple:1.5">
                    <p>第一段</p><p>第二段</p><p>第三段</p><p>第四段</p>
                  </content>
                </shape>
                <shape id="auto-fit" type="text" topLeftX="80" topLeftY="240" width="360" height="80">
                  <content fontSize="20" lineSpacing="multiple:1.5" autoFit="normal-auto-fit">
                    <p>第一段</p><p>第二段</p><p>第三段</p><p>第四段</p>
                  </content>
                </shape>
                <shape id="shape-auto-fit" type="text" topLeftX="480" topLeftY="240" width="360" height="30">
                  <content fontSize="20" lineSpacing="multiple:1.5" autoFit="shape-auto-fit">
                    <p>第一段</p><p>第二段</p><p>第三段</p>
                  </content>
                </shape>
              </data>
            </slide>
            """
        )
        issues = result["slides"][0]["issues"]
        overflow_issues = [issue for issue in issues if issue["code"] == "text_may_overflow_shape"]
        self.assertEqual(result["summary"]["error_count"], 1)
        overflow_ids = {issue["elements"][0] for issue in overflow_issues}
        self.assertIn("overflowing", overflow_ids)
        self.assertNotIn("auto-fit", overflow_ids)
        self.assertNotIn("shape-auto-fit", overflow_ids)
        self.assertNotIn("fitting", overflow_ids)
        overflowing_issue = next(issue for issue in overflow_issues if issue["elements"] == ["overflowing"])
        self.assertEqual(overflowing_issue["line_count"], 4)
        self.assertEqual(overflowing_issue["estimated_height"], 110)
        self.assertEqual(overflowing_issue["available_height"], 80)
        self.assertEqual(overflowing_issue["overflow"], 30)
        self.assertIn('wrap="true" autoFit="normal-auto-fit"', overflowing_issue["message"])

    def test_lint_xml_detects_short_label_that_wraps_by_width(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="http://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="near-fit" type="text" topLeftX="40" topLeftY="40" width="176" height="96">
                  <content textType="sub-headline" fontSize="32" fontFamily="思源黑体" bold="true"><p>Slides 87% </p></content>
                </shape>
                <shape id="under-measured" type="text" topLeftX="40" topLeftY="160" width="136" height="90">
                  <content fontSize="30" fontFamily="黑体"><p>Docs 99%</p></content>
                </shape>
                <shape id="auto-fit-spaced" type="text" topLeftX="300" topLeftY="40" width="227" height="96">
                  <content textType="sub-headline" fontSize="32" fontFamily="思源黑体" bold="true" autoFit="shape-auto-fit"><p>autofix      87% </p></content>
                </shape>
                <shape id="no-wrap-label" type="text" topLeftX="300" topLeftY="160" width="160" height="90">
                  <content fontSize="30" fontFamily="黑体" wrap="false"><p>Docs 99%</p></content>
                </shape>
                <shape id="comfortable" type="text" topLeftX="600" topLeftY="40" width="300" height="60">
                  <content fontSize="24" fontFamily="思源黑体"><p>OK</p></content>
                </shape>
              </data>
            </slide>
            """
        )
        wrap_issues = [
            issue for issue in result["slides"][0]["issues"] if issue.get("overflow_axis") == "width"
        ]
        wrap_ids = {issue["elements"][0] for issue in wrap_issues}
        # The three real false-negatives are caught, independent of autoFit and collapsed spaces.
        self.assertEqual(wrap_ids, {"near-fit", "under-measured", "auto-fit-spaced"})
        self.assertTrue(all(issue["level"] == "error" for issue in wrap_issues))
        self.assertTrue(all(issue["code"] == "text_may_overflow_shape" for issue in wrap_issues))
        # wrap="false" opts a run out; a label that comfortably fits is not flagged.
        self.assertNotIn("no-wrap-label", wrap_ids)
        self.assertNotIn("comfortable", wrap_ids)

    def test_lint_xml_skips_vertical_text_in_width_wrap_check(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="http://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="vertical" type="text" vert="vert" topLeftX="40" topLeftY="40" width="20" height="220">
                  <content fontSize="28"><p>纵向ABC</p></content>
                </shape>
                <shape id="vertical-270" type="text" vert="vert270" topLeftX="100" topLeftY="40" width="20" height="220">
                  <content fontSize="28"><p>纵向ABC</p></content>
                </shape>
                <shape id="word-art-vertical" type="text" vert="word-art-vert" topLeftX="160" topLeftY="40" width="20" height="220">
                  <content fontSize="28"><p>纵向ABC</p></content>
                </shape>
                <shape id="word-art-vertical-rtl" type="text" vert="word-art-vert-rtl" topLeftX="220" topLeftY="40" width="20" height="220">
                  <content fontSize="28"><p>纵向ABC</p></content>
                </shape>
                <shape id="east-asian-vertical" type="text" vert="ea-vert" topLeftX="280" topLeftY="40" width="20" height="220">
                  <content fontSize="28"><p>纵向ABC</p></content>
                </shape>
                <shape id="vertical-wrap-false" type="text" vert="vert" topLeftX="340" topLeftY="40" width="20" height="400">
                  <content fontSize="40" wrap="false"><p>纵向文字ABCDEFG很长很长</p></content>
                </shape>
              </data>
            </slide>
            """
        )
        width_wrap_ids = {
            issue["elements"][0]
            for issue in result["slides"][0]["issues"]
            if issue.get("overflow_axis") == "width"
        }
        self.assertEqual(width_wrap_ids, set())

    def test_lint_xml_vertical_text_overflow_stays_on_height_axis(self) -> None:
        # A vertical short label whose box is too short overflows on the height axis. It must never be
        # reclassified as a passive-wrap width overflow: horizontal advance width is meaningless for
        # stacked glyphs, so widening shape.width would not fix it. Mirrors the vertical guard in the
        # width-wrap check (detect_text_may_wrap_shapes).
        result = xml_lint.lint_xml(
            """
            <slide xmlns="http://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="v-metric" type="text" vert="vert" topLeftX="40" topLeftY="40" width="20" height="30">
                  <content fontSize="28"><p>60%+</p></content>
                </shape>
              </data>
            </slide>
            """
        )
        overflow_issues = [
            issue
            for issue in result["slides"][0]["issues"]
            if issue.get("code") == "text_may_overflow_shape" and issue["elements"] == ["v-metric"]
        ]
        self.assertEqual(len(overflow_issues), 1)
        self.assertEqual(overflow_issues[0].get("overflow_axis"), "height")

    def test_lint_xml_width_wrap_suggestion_pairs_wrap_false_with_widening(self) -> None:
        # wrap="false" does not fix a width overflow -- on its own it clips/spills text past a box
        # that is still too narrow. So the width-wrap suggestion must only offer wrap="false" bundled
        # with widening the shape, never as a standalone alternative to widen/shorten.
        result = xml_lint.lint_xml(
            """
            <slide xmlns="http://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="near-fit" type="text" topLeftX="40" topLeftY="40" width="176" height="96">
                  <content textType="sub-headline" fontSize="32" fontFamily="思源黑体" bold="true"><p>Slides 87% </p></content>
                </shape>
              </data>
            </slide>
            """
        )
        wrap_issues = [
            issue for issue in result["slides"][0]["issues"] if issue.get("overflow_axis") == "width"
        ]
        self.assertEqual(len(wrap_issues), 1)
        issue = wrap_issues[0]
        # The message must not present wrap="false" as a solo fix ("set content wrap=\"false\"").
        self.assertNotIn('or set content wrap="false"', issue["message"])
        self.assertNotIn(', or set content wrap="false"', issue["hint"])
        # When wrap="false" is mentioned, widening the shape must be recommended alongside it.
        for text in (issue["message"], issue["hint"]):
            if 'wrap="false"' in text:
                self.assertRegex(text.lower(), r"widen|increase shape\.width")

    def test_lint_xml_uses_fixed_line_spacing_for_text_height_overflow(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="fixed-overflow" type="text" topLeftX="80" topLeftY="80" width="360" height="50">
                  <content fontSize="20" lineSpacing="fixed:20" autoFit="no-auto-fit">
                    <p>第一段</p><p>第二段</p><p>第三段</p>
                  </content>
                </shape>
              </data>
            </slide>
            """
        )
        issue = result["slides"][0]["issues"][0]
        self.assertEqual(result["summary"]["warning_count"], 0)
        self.assertEqual(result["summary"]["error_count"], 1)
        self.assertEqual(issue["level"], "error")
        self.assertEqual(issue["line_height"], 20)
        self.assertEqual(issue["estimated_height"], 60)
        self.assertEqual(issue["overflow"], 10)

    def test_lint_xml_ignores_subpixel_text_height_overflow_tolerance(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="minor-overflow" type="text" topLeftX="80" topLeftY="80" width="360" height="39.8">
                  <content fontSize="20" lineSpacing="fixed:20" autoFit="no-auto-fit">
                    <p>第一段</p><p>第二段</p>
                  </content>
                </shape>
              </data>
            </slide>
            """
        )
        overflow_issues = [
            issue
            for issue in result["slides"][0]["issues"]
            if issue["code"] == "text_may_overflow_shape"
        ]
        self.assertEqual(overflow_issues, [])

    def test_lint_xml_allows_single_line_width_estimation_jitter(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="metric" type="text" topLeftX="80" topLeftY="80" width="152" height="54">
                  <content fontSize="36" lineSpacing="multiple:1.2" autoFit="no-auto-fit"><p>4.16万亿</p></content>
                </shape>
              </data>
            </slide>
            """
        )
        overflow_issues = [
            issue
            for issue in result["slides"][0]["issues"]
            if issue["code"] == "text_may_overflow_shape"
        ]
        self.assertEqual(overflow_issues, [])

    def test_lint_xml_reports_labeled_short_metric_when_it_wraps(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="http://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="sheet-success" type="text" topLeftX="520" topLeftY="385" width="180" height="50">
                  <content textType="headline" fontSize="32" bold="true" autoFit="no-auto-fit">
                    <p>Sheet 98.5%</p>
                  </content>
                </shape>
              </data>
            </slide>
            """
        )
        overflow_issues = [
            issue
            for issue in result["slides"][0]["issues"]
            if issue["code"] == "text_may_overflow_shape"
        ]
        self.assertEqual(len(overflow_issues), 1)
        self.assertEqual(overflow_issues[0]["elements"], ["sheet-success"])

    def test_lint_xml_reports_plain_short_metric_when_it_wraps(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="plain-age" type="text" topLeftX="80" topLeftY="80" width="50" height="80">
                  <content textType="title" fontSize="36" bold="true" autoFit="no-auto-fit"><p>82岁</p></content>
                </shape>
              </data>
            </slide>
            """
        )
        overflow_issues = [
            issue
            for issue in result["slides"][0]["issues"]
            if issue["code"] == "text_may_overflow_shape"
        ]
        self.assertEqual(len(overflow_issues), 1)
        self.assertEqual(overflow_issues[0]["elements"], ["plain-age"])

    def test_lint_xml_reports_wrap_false_text_wider_than_box(self) -> None:
        # wrap="false" text cannot reflow, so a hard line wider than the box is clipped or spills
        # past its edge -- a definite overflow. This mirrors slides I9dd p3 (bNQ "WidthExceed 87%"),
        # which the width-wrap heuristic used to skip outright because of the wrap="false" attribute.
        result = xml_lint.lint_xml(
            """
            <slide xmlns="http://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="width-exceed" type="text" topLeftX="32" topLeftY="403" width="176" height="79">
                  <content textType="sub-headline" fontSize="32" bold="true" wrap="false">
                    <p>WidthExceed 87% </p>
                  </content>
                </shape>
              </data>
            </slide>
            """
        )
        overflow_issues = [
            issue
            for issue in result["slides"][0]["issues"]
            if issue["code"] == "text_may_overflow_shape" and issue["elements"] == ["width-exceed"]
        ]
        self.assertEqual(len(overflow_issues), 1)
        self.assertEqual(overflow_issues[0]["overflow_axis"], "width")
        self.assertGreater(overflow_issues[0]["width_ratio"], 1.0)

    def test_lint_xml_allows_wrap_false_text_that_fits_its_box(self) -> None:
        # The wrap="false" width check reports only genuine overruns; a short run that fits on one
        # line inside a wide box must not be flagged just because it declares wrap="false".
        result = xml_lint.lint_xml(
            """
            <slide xmlns="http://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="fits" type="text" topLeftX="80" topLeftY="80" width="400" height="60">
                  <content textType="body" fontSize="16" wrap="false"><p>OK</p></content>
                </shape>
              </data>
            </slide>
            """
        )
        overflow_issues = [
            issue
            for issue in result["slides"][0]["issues"]
            if issue["code"] == "text_may_overflow_shape" and issue["elements"] == ["fits"]
        ]
        self.assertEqual(overflow_issues, [])

    def test_lint_xml_reports_cjk_credit_with_em_dashes_wrapping_narrow_box(self) -> None:
        # "—— 李白" in a tight author-credit box wraps in the renderer because the two em-dashes render
        # full-width inside a CJK run (slides p1: bMW). unicodedata marks em-dash as ambiguous width, so
        # a naive Latin-punctuation estimate under-reports the line and misses the wrap. The width check
        # must treat ambiguous glyphs as full-width in CJK context (Bucket A4).
        result = xml_lint.lint_xml(
            """
            <slide xmlns="http://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="credit" type="text" topLeftX="66" topLeftY="124" width="46" height="18">
                  <content fontSize="12"><p>—— 李白</p></content>
                </shape>
              </data>
            </slide>
            """
        )
        wrap_issues = [
            issue for issue in result["slides"][0]["issues"]
            if issue["code"] == "text_may_overflow_shape" and issue["elements"] == ["credit"]
        ]
        # Promoting the em-dashes to full-width makes the run too wide for the box; the renderer then
        # wraps it to two lines that also overflow the 18px height, so either the width or the height
        # detector may surface it first -- the contract is that the credit is flagged, not which axis.
        self.assertEqual(len(wrap_issues), 1)
        self.assertIn(wrap_issues[0]["overflow_axis"], {"width", "height"})

    def test_lint_xml_keeps_latin_en_dash_range_narrow(self) -> None:
        # The ambiguous-width promotion is context-gated: an en-dash in a pure-Latin run ("2020–2023")
        # stays half-width, so a comfortably-sized box must not be reported. Guards A4 from over-firing
        # by inflating every dash to full-width regardless of surrounding script.
        result = xml_lint.lint_xml(
            """
            <slide xmlns="http://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="range" type="text" topLeftX="80" topLeftY="80" width="140" height="30">
                  <content fontSize="14"><p>2020–2023</p></content>
                </shape>
              </data>
            </slide>
            """
        )
        wrap_issues = [
            issue for issue in result["slides"][0]["issues"]
            if issue["code"] == "text_may_overflow_shape"
        ]
        self.assertEqual(wrap_issues, [])

    def test_lint_xml_reports_percent_heavy_run_overflowing_by_full_width_glyph(self) -> None:
        # "%" is Unicode half-width (Na) but renders near full-width, so a percentage-heavy run wraps to
        # more lines than a naive punct-coefficient estimate and overflows its box height (slides p3:
        # bhU "Docs 99%Docs 99%Docs 99%%1"). Measuring "%" at its true advance is what surfaces this.
        result = xml_lint.lint_xml(
            """
            <slide xmlns="http://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="metrics" type="text" topLeftX="587" topLeftY="60" width="227" height="100">
                  <content fontSize="30" autoFit="no-auto-fit"><p>Docs 99%Docs 99%Docs 99%%1</p></content>
                </shape>
              </data>
            </slide>
            """
        )
        overflow = [
            issue for issue in result["slides"][0]["errors"]
            if issue["code"] == "text_may_overflow_shape" and issue["elements"] == ["metrics"]
        ]
        self.assertEqual(len(overflow), 1)

    def test_lint_xml_reports_range_percent_metric_wrapping_its_box(self) -> None:
        # A range percentage "10-20%" packs wide punctuation between numbers. With the short-metric
        # whitelist removed and those glyphs measured at their real advance, it must surface as a width
        # overflow error (slides I9dd p24: bvd, whose note records "10-20% 被迫换行导致溢出文本框").
        result = xml_lint.lint_xml(
            """
            <slide xmlns="http://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="bvd" type="text" topLeftX="720" topLeftY="190" width="140" height="60">
                  <content textType="title" fontSize="42" fontFamily="思源黑体" bold="true"><p>10-20%</p></content>
                </shape>
              </data>
            </slide>
            """
        )
        overflow = [
            issue for issue in result["slides"][0]["errors"]
            if issue["code"] == "text_may_overflow_shape" and issue["elements"] == ["bvd"]
        ]
        self.assertEqual(len(overflow), 1)
        self.assertEqual(overflow[0]["overflow_axis"], "width")
        self.assertGreater(overflow[0]["estimated_width"], overflow[0]["available_width"])

    def test_lint_xml_marginal_overflow_label_reported_once_as_error(self) -> None:
        # A short "Slides 87%" label sized so its wrapped two lines graze the box on both axes. Height
        # and width detectors share the text_may_overflow_shape code, so dedup_overlap_issues keeps a
        # single issue for the run (slides p3: bMP/bhd) and it surfaces at error level.
        result = xml_lint.lint_xml(
            """
            <slide xmlns="http://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="label" type="text" topLeftX="244" topLeftY="120" width="176" height="79">
                  <content fontSize="32" bold="true" autoFit="no-auto-fit"><p>Slides 87%</p></content>
                </shape>
              </data>
            </slide>
            """
        )
        reports = [
            issue for issue in result["slides"][0]["issues"]
            if issue["code"] == "text_may_overflow_shape" and issue["elements"] == ["label"]
        ]
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0]["level"], "error")

    def test_lint_xml_reports_id_less_label_overflowing_both_axes_once(self) -> None:
        # Same one-issue-per-run contract as above, for a shape with no authored id. The height and
        # width detectors must agree on the element_ref locator, otherwise the width check cannot
        # tell that the height check already reported this run and the pair surfaces twice.
        result = xml_lint.lint_xml(
            """
            <slide xmlns="http://www.larkoffice.com/sml/2.0">
              <data>
                <shape type="text" topLeftX="60" topLeftY="60" width="110" height="12">
                  <content fontSize="20"><p>Slides 87%</p></content>
                </shape>
              </data>
            </slide>
            """
        )
        reports = [
            issue for issue in result["slides"][0]["issues"]
            if issue["code"] == "text_may_overflow_shape"
        ]
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0]["elements"], ["slide[1]/data/shape[1]"])

    def test_lint_xml_allows_centered_short_label_near_fit_as_single_line(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="centered-label" type="text" topLeftX="80" topLeftY="80" width="200" height="30">
                  <content fontSize="14" bold="true" textAlign="center" autoFit="no-auto-fit">
                    <p>参数服务器 (Parameter Server)</p>
                  </content>
                </shape>
              </data>
            </slide>
            """
        )
        overflow_issues = [
            issue
            for issue in result["slides"][0]["issues"]
            if issue["code"] == "text_may_overflow_shape"
        ]
        self.assertEqual(overflow_issues, [])

    def test_lint_xml_allows_headline_near_fit_as_single_line(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="headline" type="text" topLeftX="80" topLeftY="80" width="700" height="50">
                  <content textType="headline" fontSize="26" bold="true" lineSpacing="multiple:1.3" autoFit="no-auto-fit">
                    <p>全球半导体市场规模持续高速增长，AI驱动新一轮景气周期</p>
                  </content>
                </shape>
              </data>
            </slide>
            """
        )
        overflow_issues = [
            issue
            for issue in result["slides"][0]["issues"]
            if issue["code"] == "text_may_overflow_shape"
        ]
        self.assertEqual(overflow_issues, [])

    def test_lint_xml_allows_dense_body_line_spacing_estimation_slack(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="dense-body" type="text" topLeftX="80" topLeftY="80" width="360" height="140">
                  <content fontSize="13" bold="true" lineSpacing="multiple:1.7" autoFit="no-auto-fit">
                    <p>总体目标：</p>
                    <p>建立深度神经网络高效训练的统一理论框架，实现训练效率与模型性能的协同优化。</p>
                    <p>具体目标：</p>
                    <p>提出自适应优化算法，收敛速度提升 2-3 倍</p>
                    <p>实现结构化压缩方法，模型体积减少 10 倍以上</p>
                    <p>构建分布式训练策略，64 GPU 加速比 &gt; 50x</p>
                  </content>
                </shape>
              </data>
            </slide>
            """
        )
        overflow_issues = [
            issue
            for issue in result["slides"][0]["issues"]
            if issue["code"] == "text_may_overflow_shape"
        ]
        self.assertEqual(overflow_issues, [])

    def test_lint_xml_reports_dense_body_when_adjusted_height_still_overflows(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="dense-body" type="text" topLeftX="80" topLeftY="80" width="360" height="100">
                  <content fontSize="13" bold="true" lineSpacing="multiple:1.7" autoFit="no-auto-fit">
                    <p>总体目标：</p>
                    <p>建立深度神经网络高效训练的统一理论框架，实现训练效率与模型性能的协同优化。</p>
                    <p>具体目标：</p>
                    <p>提出自适应优化算法，收敛速度提升 2-3 倍</p>
                    <p>实现结构化压缩方法，模型体积减少 10 倍以上</p>
                    <p>构建分布式训练策略，64 GPU 加速比 &gt; 50x</p>
                  </content>
                </shape>
              </data>
            </slide>
            """
        )
        overflow_issues = [
            issue
            for issue in result["slides"][0]["issues"]
            if issue["code"] == "text_may_overflow_shape"
        ]
        self.assertEqual(len(overflow_issues), 1)
        self.assertEqual(overflow_issues[0]["elements"], ["dense-body"])

    def test_lint_xml_reports_letter_spaced_caption_near_fit(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="caption" type="text" topLeftX="80" topLeftY="80" width="120" height="20">
                  <content textType="caption" fontSize="11" letterSpacing="1" autoFit="no-auto-fit">
                    <p>RISKS &amp; CHALLENGES</p>
                  </content>
                </shape>
              </data>
            </slide>
            """
        )
        overflow_issues = [
            issue
            for issue in result["slides"][0]["issues"]
            if issue["code"] == "text_may_overflow_shape"
        ]
        self.assertEqual(len(overflow_issues), 1)
        self.assertEqual(overflow_issues[0]["elements"], ["caption"])

    def test_lint_xml_reports_micro_caption_when_wrapping_overflows(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="micro-caption" type="text" topLeftX="80" topLeftY="60" width="200" height="16">
                  <content textType="caption" fontSize="3" lineSpacing="multiple:1.3" letterSpacing="160" autoFit="no-auto-fit">
                    <p>MARKET INSIGHT · 市场洞察</p>
                  </content>
                </shape>
              </data>
            </slide>
            """
        )
        overflow_issues = [
            issue
            for issue in result["slides"][0]["issues"]
            if issue["code"] == "text_may_overflow_shape"
        ]
        self.assertEqual(len(overflow_issues), 1)
        self.assertEqual(overflow_issues[0]["elements"], ["micro-caption"])

    def test_lint_xml_text_may_overflow_shape_reports_any_overflow_as_error(self) -> None:
        # No warning band: a small (10px) and a large (30px) vertical overflow are both errors, so a
        # marginal half-line overflow is no longer under-reported. Only the 0.5px sub-pixel tolerance
        # is exempt.
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="small-overflow" type="text" topLeftX="80" topLeftY="80" width="360" height="50">
                  <content fontSize="20" lineSpacing="fixed:20" autoFit="no-auto-fit">
                    <p>第一段</p><p>第二段</p><p>第三段</p>
                  </content>
                </shape>
                <shape id="error-overflow" type="text" topLeftX="80" topLeftY="200" width="360" height="30">
                  <content fontSize="20" lineSpacing="fixed:20" autoFit="no-auto-fit">
                    <p>第一段</p><p>第二段</p><p>第三段</p>
                  </content>
                </shape>
              </data>
            </slide>
            """
        )
        issues = {issue["elements"][0]: issue for issue in result["slides"][0]["issues"]}
        self.assertEqual(issues["small-overflow"]["level"], "error")
        self.assertEqual(issues["small-overflow"]["overflow"], 10)
        self.assertEqual(issues["error-overflow"]["level"], "error")
        self.assertEqual(issues["error-overflow"]["overflow"], 30)
        self.assertEqual(result["summary"]["error_count"], 2)
        self.assertEqual(result["summary"]["warning_count"], 0)

    def test_lint_xml_text_may_overflow_shape_downgrades_background_decoration_to_info(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="bg-deco" type="text" topLeftX="0" topLeftY="0" width="600" height="80" alpha="0.3">
                  <content fontSize="120" lineSpacing="fixed:120" autoFit="no-auto-fit"><p>2026</p></content>
                </shape>
                <shape id="foreground" type="text" topLeftX="40" topLeftY="20" width="400" height="60">
                  <content fontSize="20" lineSpacing="fixed:24"><p>Annual Report</p></content>
                </shape>
              </data>
            </slide>
            """
        )
        issues = {
            issue["elements"][0]: issue
            for issue in result["slides"][0]["issues"]
            if issue["code"] == "text_may_overflow_shape"
        }
        self.assertEqual(issues["bg-deco"]["level"], "info")
        self.assertEqual(result["summary"]["warning_count"], 0)
        self.assertEqual(result["summary"]["info_count"], 1)
        self.assertEqual(result["slides"][0]["infos"], [issues["bg-deco"]])
        self.assertIn("background decoration", issues["bg-deco"]["message"])

    def test_lint_xml_reports_shape_alpha_ghost_text_out_of_canvas_but_allows_overlap(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="ghost-number" type="text" topLeftX="-60" topLeftY="30" width="360" height="180" alpha="0.2">
                  <content fontSize="160" lineSpacing="fixed:160" wrap="false"><p>01</p></content>
                </shape>
                <shape id="title" type="text" topLeftX="80" topLeftY="80" width="360" height="80">
                  <content fontSize="30" lineSpacing="fixed:36"><p>Annual Review</p></content>
                </shape>
              </data>
            </slide>
            """
        )
        codes = [issue["code"] for issue in result["slides"][0]["issues"]]
        self.assertEqual(result["summary"]["error_count"], 1)
        self.assertIn("shape_out_of_canvas", codes)
        self.assertNotIn("bbox_overlap", codes)

    def test_lint_xml_reports_content_color_alpha_ghost_text_out_of_canvas_but_allows_overlap(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="ghost-year" type="text" topLeftX="760" topLeftY="20" width="260" height="160">
                  <content fontSize="140" color="rgba(0,0,0,0.2)" lineSpacing="fixed:140" wrap="false"><p>2026</p></content>
                </shape>
                <shape id="headline" type="text" topLeftX="700" topLeftY="70" width="220" height="80">
                  <content fontSize="28" lineSpacing="fixed:34"><p>Forecast</p></content>
                </shape>
              </data>
            </slide>
            """
        )
        codes = [issue["code"] for issue in result["slides"][0]["issues"]]
        self.assertEqual(result["summary"]["error_count"], 1)
        self.assertIn("shape_out_of_canvas", codes)
        self.assertNotIn("bbox_overlap", codes)

    def test_lint_xml_reports_faint_medium_ghost_text_out_of_canvas_but_allows_overlap(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="medium-ghost" type="text" topLeftX="820" topLeftY="300" width="270" height="72" alpha="0.32">
                  <content fontSize="40" lineSpacing="fixed:40" wrap="false"><p>OFF EDGE</p></content>
                </shape>
                <shape id="caption" type="text" topLeftX="760" topLeftY="315" width="180" height="36">
                  <content fontSize="16" lineSpacing="fixed:20"><p>Readable caption</p></content>
                </shape>
              </data>
            </slide>
            """
        )
        codes = [issue["code"] for issue in result["slides"][0]["issues"]]
        self.assertEqual(result["summary"]["error_count"], 1)
        self.assertIn("shape_out_of_canvas", codes)
        self.assertNotIn("bbox_overlap", codes)

    def test_lint_xml_allows_ghost_text_image_overlap(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="ghost-label" type="text" topLeftX="100" topLeftY="40" width="560" height="160" alpha="0.2">
                  <content fontSize="120" lineSpacing="fixed:120" wrap="false"><p>2026</p></content>
                </shape>
                <img id="photo" src="token" topLeftX="160" topLeftY="70" width="260" height="160"/>
                <shape id="title" type="text" topLeftX="610" topLeftY="95" width="320" height="60">
                  <content fontSize="28" lineSpacing="fixed:34"><p>Annual Review</p></content>
                </shape>
              </data>
            </slide>
            """
        )
        codes = [issue["code"] for issue in result["slides"][0]["issues"]]
        self.assertNotIn("image_covers_text", codes)
        self.assertNotIn("bbox_overlap", codes)

    def test_lint_slide_allows_ghost_text_whiteboard_overlap(self) -> None:
        result = xml_lint.lint_slide(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <whiteboard id="board" topLeftX="180" topLeftY="70" width="420" height="300"/>
                <shape id="ghost-label" type="text" topLeftX="100" topLeftY="40" width="560" height="160" alpha="0.2">
                  <content fontSize="120" lineSpacing="fixed:120" wrap="false"><p>2026</p></content>
                </shape>
                <shape id="title" type="text" topLeftX="610" topLeftY="95" width="220" height="60">
                  <content fontSize="28" lineSpacing="fixed:34"><p>Annual Review</p></content>
                </shape>
              </data>
            </slide>
            """,
            1,
        )
        codes = [issue["code"] for issue in result["issues"]]
        self.assertNotIn("whiteboard_external_overlap", codes)

    def test_lint_xml_reports_faint_ghost_text_out_of_canvas_without_area_threshold(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="small-ghost" type="text" topLeftX="940" topLeftY="300" width="40" height="40" alpha="0.32">
                  <content fontSize="36" lineSpacing="fixed:36" wrap="false"><p>土</p></content>
                </shape>
              </data>
            </slide>
            """
        )
        self.assertEqual(result["summary"]["error_count"], 1)
        self.assertEqual(result["slides"][0]["issues"][0]["code"], "shape_out_of_canvas")

    def test_lint_xml_keeps_out_of_canvas_error_for_medium_text_without_faint_alpha(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="medium-not-ghost" type="text" topLeftX="820" topLeftY="300" width="270" height="72" alpha="0.36">
                  <content fontSize="54" lineSpacing="fixed:54" wrap="false"><p>OFF EDGE</p></content>
                </shape>
              </data>
            </slide>
            """
        )
        self.assertEqual(result["summary"]["error_count"], 1)
        self.assertEqual(result["slides"][0]["issues"][0]["code"], "shape_out_of_canvas")
        self.assertEqual(result["slides"][0]["issues"][0]["elements"], ["medium-not-ghost"])

    def test_lint_xml_keeps_out_of_canvas_error_for_half_alpha_large_text(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="half-alpha" type="text" topLeftX="760" topLeftY="20" width="260" height="160">
                  <content fontSize="140" color="rgba(0,0,0,0.5)" lineSpacing="fixed:140" wrap="false"><p>2026</p></content>
                </shape>
              </data>
            </slide>
            """
        )
        # half-alpha (0.5) is not ghost-level, so the run keeps its out-of-canvas error. "2026" at
        # fontSize 140 is also far wider than the 260px box and cannot reflow (wrap="false"), so the
        # width-overflow catch is genuine and stacks on top of the out-of-canvas error.
        codes = [issue["code"] for issue in result["slides"][0]["issues"]]
        self.assertIn("shape_out_of_canvas", codes)
        out_of_canvas = [
            issue
            for issue in result["slides"][0]["issues"]
            if issue["code"] == "shape_out_of_canvas"
        ]
        self.assertEqual(out_of_canvas[0]["elements"], ["half-alpha"])
        width_overflow = [
            issue
            for issue in result["slides"][0]["issues"]
            if issue["code"] == "text_may_overflow_shape"
            and issue.get("overflow_axis") == "width"
            and issue["elements"] == ["half-alpha"]
        ]
        self.assertEqual(len(width_overflow), 1)
        self.assertEqual(width_overflow[0]["level"], "error")

    def test_lint_xml_text_may_overflow_shape_keeps_error_when_alpha_not_low(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="opaque-big" type="text" topLeftX="0" topLeftY="0" width="600" height="80" alpha="0.9">
                  <content fontSize="120" lineSpacing="fixed:120" autoFit="no-auto-fit"><p>2026</p></content>
                </shape>
                <shape id="foreground" type="text" topLeftX="40" topLeftY="20" width="400" height="60">
                  <content fontSize="20" lineSpacing="fixed:24"><p>Annual Report</p></content>
                </shape>
              </data>
            </slide>
            """
        )
        issue = next(
            issue
            for issue in result["slides"][0]["issues"]
            if issue["code"] == "text_may_overflow_shape" and issue["elements"] == ["opaque-big"]
        )
        self.assertEqual(issue["level"], "error")

    def test_lint_xml_text_may_overflow_shape_keeps_error_when_no_foreground_text(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="lonely-big" type="text" topLeftX="0" topLeftY="0" width="600" height="80" alpha="0.3">
                  <content fontSize="120" lineSpacing="fixed:120" autoFit="no-auto-fit"><p>2026</p></content>
                </shape>
              </data>
            </slide>
            """
        )
        issue = next(
            issue
            for issue in result["slides"][0]["issues"]
            if issue["code"] == "text_may_overflow_shape" and issue["elements"] == ["lonely-big"]
        )
        self.assertEqual(issue["level"], "error")

    def test_lint_xml_text_may_overflow_shape_keeps_error_when_foreground_alpha_zero(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="bg-deco" type="text" topLeftX="0" topLeftY="0" width="600" height="80" alpha="0.3">
                  <content fontSize="120" lineSpacing="fixed:120" autoFit="no-auto-fit"><p>2026</p></content>
                </shape>
                <shape id="transparent-foreground" type="text" topLeftX="40" topLeftY="20" width="400" height="60" alpha="0">
                  <content fontSize="20" lineSpacing="fixed:24"><p>Annual Report</p></content>
                </shape>
              </data>
            </slide>
            """
        )
        issue = next(
            issue
            for issue in result["slides"][0]["issues"]
            if issue["code"] == "text_may_overflow_shape" and issue["elements"] == ["bg-deco"]
        )
        self.assertEqual(issue["level"], "error")

    def test_lint_xml_text_may_overflow_shape_keeps_error_when_foreground_is_below_in_order(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="foreground" type="text" topLeftX="40" topLeftY="20" width="400" height="60">
                  <content fontSize="20" lineSpacing="fixed:24"><p>Annual Report</p></content>
                </shape>
                <shape id="top-big" type="text" topLeftX="0" topLeftY="0" width="600" height="80" alpha="0.3">
                  <content fontSize="120" lineSpacing="fixed:120" autoFit="no-auto-fit"><p>2026</p></content>
                </shape>
              </data>
            </slide>
            """
        )
        issue = next(
            issue
            for issue in result["slides"][0]["issues"]
            if issue["code"] == "text_may_overflow_shape" and issue["elements"] == ["top-big"]
        )
        self.assertEqual(issue["level"], "error")

    def test_lint_xml_uses_paragraph_spacing_overrides_for_text_height_overflow(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="paragraph-overflow" type="text" topLeftX="80" topLeftY="80" width="360" height="30">
                  <content fontSize="20" lineSpacing="multiple:1.5" autoFit="no-auto-fit">
                    <p lineSpacing="fixed:10" beforeLineSpacing="fixed:5" afterLineSpacing="fixed:5">第一行<br/>第二行</p>
                  </content>
                </shape>
                <shape id="paragraph-fitting" type="text" topLeftX="480" topLeftY="80" width="360" height="40">
                  <content fontSize="20" lineSpacing="multiple:1.5">
                    <p lineSpacing="fixed:10">第一行<br/>第二行<br/>第三行</p>
                  </content>
                </shape>
              </data>
            </slide>
            """
        )
        issues = result["slides"][0]["issues"]
        self.assertEqual(result["summary"]["error_count"], 1)
        self.assertEqual(result["summary"]["warning_count"], 0)
        self.assertEqual(issues[0]["level"], "error")
        self.assertEqual(issues[0]["elements"], ["paragraph-overflow"])
        self.assertEqual(issues[0]["line_count"], 2)
        self.assertEqual(issues[0]["line_height"], 10)
        self.assertEqual(issues[0]["estimated_height"], 40)
        self.assertEqual(issues[0]["overflow"], 10)

    def test_lint_xml_uses_letter_spacing_for_text_overflow_warning(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="baseline" type="text" topLeftX="0" topLeftY="0" width="120" height="30">
                  <content fontSize="20" lineSpacing="multiple:1.5" autoFit="no-auto-fit"><p>一二三四五六</p></content>
                </shape>
                <shape id="content-spaced" type="text" topLeftX="200" topLeftY="0" width="120" height="30">
                  <content fontSize="20" lineSpacing="multiple:1.5" letterSpacing="2" autoFit="no-auto-fit"><p>一二三四五六</p></content>
                </shape>
                <shape id="paragraph-spaced" type="text" topLeftX="400" topLeftY="0" width="120" height="30">
                  <content fontSize="20" lineSpacing="multiple:1.5" autoFit="no-auto-fit"><p letterSpacing="2">一二三四五六</p></content>
                </shape>
              </data>
            </slide>
            """
        )
        issues = result["slides"][0]["issues"]
        overflow_ids = [issue["elements"][0] for issue in issues if issue["code"] == "text_may_overflow_shape"]
        self.assertNotIn("baseline", overflow_ids)
        self.assertIn("content-spaced", overflow_ids)
        self.assertIn("paragraph-spaced", overflow_ids)
        by_id = {issue["elements"][0]: issue for issue in issues if issue["code"] == "text_may_overflow_shape"}
        # letterSpacing (whether on <content> or <p>) widens the single line past its 120px box, so it
        # wraps. This is a passive width overflow, not a genuine height overflow: the fix is to widen
        # the box or shrink the font, not raise its height. So it is reported on the width axis.
        self.assertEqual(by_id["content-spaced"]["overflow_axis"], "width")
        self.assertGreater(by_id["content-spaced"]["width_ratio"], 1.0)
        self.assertEqual(by_id["paragraph-spaced"]["overflow_axis"], "width")
        self.assertGreater(by_id["paragraph-spaced"]["width_ratio"], 1.0)

    def test_lint_xml_reclassifies_short_passive_wrap_as_width_not_height(self) -> None:
        # A big-number label "60%+" (42px, no hard break, 100px box) is too wide for one line, so it
        # passively wraps to 2 lines and inflates its height. This is slides I9dd p4 (bqE). The defect
        # is width, not height: wrap already defaults to true, so "set wrap=true"/raise height cannot
        # un-wrap it. The fix is to widen the box or shrink the font, so it must be reported on the
        # width axis with an actionable hint, never as a height overflow suggesting wrap="true".
        result = xml_lint.lint_xml(
            """
            <slide xmlns="http://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="big-number" type="text" topLeftX="100" topLeftY="180" width="100" height="60">
                  <content textType="headline" fontSize="42" fontFamily="思源黑体" bold="true"><p>60%+</p></content>
                </shape>
              </data>
            </slide>
            """
        )
        overflow_issues = [
            issue
            for issue in result["slides"][0]["issues"]
            if issue["code"] == "text_may_overflow_shape" and issue["elements"] == ["big-number"]
        ]
        self.assertEqual(len(overflow_issues), 1)
        issue = overflow_issues[0]
        self.assertEqual(issue["overflow_axis"], "width")
        self.assertGreater(issue["width_ratio"], 1.0)
        self.assertEqual(issue["level"], "error")
        # The actionable fix (widen / reduce font) must be present; the no-op wrap="true" must not.
        self.assertRegex(issue["hint"], r"widen shape\.width|reduce the font size")
        self.assertNotIn('wrap="true"', issue["message"])

    def test_lint_xml_keeps_multiline_prose_overflow_on_height_axis(self) -> None:
        # A genuine height overflow -- multi-paragraph prose that does not fit -- must keep the height
        # classification and its wrap="true" autoFit hint, so the reclassification only steals the
        # short-single-line passive-wrap case and does not swallow real vertical overflows.
        result = xml_lint.lint_xml(
            """
            <slide xmlns="http://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="prose" type="text" topLeftX="80" topLeftY="80" width="360" height="60">
                  <content fontSize="20" lineSpacing="multiple:1.5" autoFit="no-auto-fit">
                    <p>第一段落文字</p><p>第二段落文字</p><p>第三段落文字</p><p>第四段落文字</p>
                  </content>
                </shape>
              </data>
            </slide>
            """
        )
        overflow_issues = [
            issue
            for issue in result["slides"][0]["issues"]
            if issue["code"] == "text_may_overflow_shape" and issue["elements"] == ["prose"]
        ]
        self.assertEqual(len(overflow_issues), 1)
        issue = overflow_issues[0]
        self.assertEqual(issue["overflow_axis"], "height")
        self.assertIn('wrap="true" autoFit="normal-auto-fit"', issue["message"])

    def test_lint_xml_reclassifies_long_title_passive_wrap_as_width_not_height(self) -> None:
        # A long section title with no hard line break is authored to stay on one line, but its box is
        # too narrow so it passively wraps to 2 lines and inflates its height. Even though it exceeds
        # the short-label char cap, the defect is width: raising shape.height just leaves the two lines
        # overlapping, so it must be reported on the width axis with a widen/shrink-font hint, never as
        # a height overflow suggesting wrap="true"/increase height.
        result = xml_lint.lint_xml(
            """
            <slide xmlns="http://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="section-title" type="text" topLeftX="60" topLeftY="120" width="360" height="40">
                  <content textType="title" fontSize="24" fontFamily="思源黑体" bold="true"><p>两者定位截然不同：WorkBuddy是执行型智能体，豆包是全能助手加任务模式</p></content>
                </shape>
              </data>
            </slide>
            """
        )
        overflow_issues = [
            issue for issue in result["slides"][0]["issues"]
            if issue["code"] == "text_may_overflow_shape" and issue["elements"] == ["section-title"]
        ]
        self.assertEqual(len(overflow_issues), 1)
        issue = overflow_issues[0]
        self.assertEqual(issue["overflow_axis"], "width")
        self.assertRegex(issue["hint"], r"widen shape\.width|reduce the font size")
        self.assertNotIn('wrap="true"', issue["message"])

    def test_lint_xml_flags_title_width_wrap_even_when_height_fits_both_lines(self) -> None:
        # A long headline whose single line is wider than its box passively wraps to 2 lines. Here the
        # box is tall enough to absorb both lines, so the vertical overflow check stays silent -- yet the
        # title was authored for one line, so the wrap is still a defect. detect_text_may_wrap_shapes
        # must catch it on the width axis regardless of height (slides I9dd p25: the same title with a
        # height that fits 2 lines was a false negative until titles bypassed the short-label char cap).
        result = xml_lint.lint_xml(
            """
            <slide xmlns="http://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="tall-title" type="text" topLeftX="98" topLeftY="33" width="762.45" height="66">
                  <content textType="headline" fontSize="22" fontFamily="思源黑体" bold="true"><p>两者定位截然不同：WorkBuddy是"执行型智能体"，豆包是"全能助手+任务模式</p></content>
                </shape>
              </data>
            </slide>
            """
        )
        overflow_issues = [
            issue for issue in result["slides"][0]["issues"]
            if issue["code"] == "text_may_overflow_shape" and issue["elements"] == ["tall-title"]
        ]
        self.assertEqual(len(overflow_issues), 1)
        issue = overflow_issues[0]
        self.assertEqual(issue["overflow_axis"], "width")
        self.assertGreater(issue["width_ratio"], 1.0)
        self.assertEqual(issue["level"], "error")

    def test_lint_xml_does_not_flag_title_that_fits_its_box_width(self) -> None:
        # A title-like run that comfortably fits its box must not be a false positive.
        result = xml_lint.lint_xml(
            """
            <slide xmlns="http://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="fits-title" type="text" topLeftX="30" topLeftY="30" width="900" height="40">
                  <content textType="headline" fontSize="22" fontFamily="思源黑体" bold="true"><p>两者定位不同</p></content>
                </shape>
              </data>
            </slide>
            """
        )
        overflow_issues = [
            issue for issue in result["slides"][0]["issues"]
            if issue["code"] == "text_may_overflow_shape" and issue["elements"] == ["fits-title"]
        ]
        self.assertEqual(overflow_issues, [])

    def test_strip_xml_paragraphs_preserves_br_as_hard_line_break(self) -> None:
        self.assertEqual(
            xml_lint.strip_xml_paragraphs("<p>第一行<br/>第二行<br />第三行</p>"),
            "第一行\n第二行\n第三行",
        )

    def test_lint_xml_reports_template_style_images_outside_canvas(self) -> None:
        result = xml_lint.lint_xml(
            """
            <presentation xmlns="https://www.larkoffice.com/sml/2.0" width="960" height="540">
              <slide xmlns="https://www.larkoffice.com/sml/2.0">
                <data>
                  <img src="tok" topLeftX="-120" topLeftY="20" width="360" height="360"/>
                  <shape type="text" topLeftX="300" topLeftY="80" width="180" height="80">
                    <content textType="title" fontSize="44"><p>Title</p></content>
                  </shape>
                  <shape type="text" topLeftX="300" topLeftY="170" width="180" height="40">
                    <content textType="sub-headline" fontSize="20"><p>Subtitle</p></content>
                  </shape>
                </data>
              </slide>
            </presentation>
            """
        )
        self.assertEqual(result["summary"]["error_count"], 1)
        issue = result["slides"][0]["issues"][0]
        self.assertEqual(issue["code"], "img_out_of_canvas")
        self.assertEqual(issue["elements"], ["slide[1]/data/img[1]"])
        self.assertEqual(issue["overflow"], {"left": 120, "top": 0, "right": 0, "bottom": 0})
        self.assertEqual(result["summary"]["warning_count"], 0)

    def test_extract_elements_preserves_supported_element_geometry_order_and_text_metadata(self) -> None:
        elements = xml_lint.extract_elements(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <img id="photo" src="tok" topLeftX="10" topLeftY="20" width="100" height="80"/>
                <shape id="headline" type="text" topLeftX="40" topLeftY="60" width="320" height="90">
                  <content textType="headline" textAlign="center" autoFit="normal-auto-fit" fontSize="28">
                    <p><![CDATA[Growth & scale]]></p>
                    <p>Focused execution</p>
                  </content>
                </shape>
                <table id="table" topLeftX="400" topLeftY="60" width="220" height="120"></table>
                <chart id="chart" topLeftX="640" topLeftY="60" width="220" height="120"/>
                <whiteboard id="wb" topLeftX="80" topLeftY="220" width="760" height="240"/>
                <embed id="emb" topLeftX="600" topLeftY="320" width="240" height="140">
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 140"><rect x="0" y="0" width="240" height="140"/></svg>
                </embed>
                <shape id="missing-height" type="text" topLeftX="80" topLeftY="480" width="320">
                  <content><p>Skipped</p></content>
                </shape>
              </data>
            </slide>
            """
        )
        self.assertEqual([element["id"] for element in elements], ["photo", "headline", "table", "chart", "wb", "emb"])
        self.assertEqual([element["kind"] for element in elements], ["img", "shape", "table", "chart", "whiteboard", "embed"])
        self.assertEqual([element["order"] for element in elements], [0, 1, 2, 3, 4, 5])
        self.assertEqual(elements[1]["type"], "text")
        self.assertEqual(elements[1]["textType"], "headline")
        self.assertEqual(elements[1]["textAlign"], "center")
        self.assertEqual(elements[1]["autoFit"], "normal-auto-fit")
        self.assertEqual(elements[1]["fontSize"], 28)
        self.assertEqual(elements[1]["text"], "Growth & scale\nFocused execution")

    def test_lint_xml_reports_small_out_of_bounds_images(self) -> None:
        result = xml_lint.lint_xml(
            """
            <presentation xmlns="https://www.larkoffice.com/sml/2.0" width="960" height="540">
              <slide xmlns="https://www.larkoffice.com/sml/2.0">
                <data>
                  <img src="tok" topLeftX="-20" topLeftY="20" width="120" height="120"/>
                </data>
              </slide>
            </presentation>
            """
        )
        self.assertEqual(result["summary"]["error_count"], 1)
        issue = result["slides"][0]["issues"][0]
        self.assertEqual(issue["code"], "img_out_of_canvas")
        self.assertEqual(issue["overflow"], {"left": 20, "top": 0, "right": 0, "bottom": 0})

    def test_lint_xml_reports_out_of_canvas_images(self) -> None:
        result = xml_lint.lint_xml(
            """
            <presentation xmlns="https://www.larkoffice.com/sml/2.0" width="960" height="540">
              <slide xmlns="https://www.larkoffice.com/sml/2.0">
                <data>
                  <img src="right" topLeftX="780" topLeftY="0" width="500" height="540"/>
                  <img src="bottom" topLeftX="0" topLeftY="430" width="900" height="280"/>
                </data>
              </slide>
            </presentation>
            """
        )
        self.assertEqual(result["summary"]["error_count"], 2)
        self.assertEqual(
            [(issue["code"], issue["elements"], issue["overflow"]) for issue in result["slides"][0]["issues"]],
            [
                (
                    "img_out_of_canvas",
                    ["slide[1]/data/img[1]"],
                    {"left": 0, "top": 0, "right": 320, "bottom": 0},
                ),
                (
                    "img_out_of_canvas",
                    ["slide[1]/data/img[2]"],
                    {"left": 0, "top": 0, "right": 0, "bottom": 170},
                ),
            ],
        )

    def test_lint_xml_reports_full_bleed_images_outside_canvas(self) -> None:
        result = xml_lint.lint_xml(
            """
            <presentation xmlns="https://www.larkoffice.com/sml/2.0" width="960" height="540">
              <slide xmlns="https://www.larkoffice.com/sml/2.0">
                <data>
                  <img src="tok" topLeftX="-80" topLeftY="-20" width="1080" height="600"/>
                </data>
              </slide>
            </presentation>
            """
        )
        self.assertEqual(result["summary"]["error_count"], 1)
        issue = result["slides"][0]["issues"][0]
        self.assertEqual(issue["code"], "img_out_of_canvas")
        self.assertEqual(issue["overflow"], {"left": 80, "top": 20, "right": 40, "bottom": 40})

    def test_lint_xml_reports_text_chart_and_image_out_of_canvas(self) -> None:
        result = xml_lint.lint_xml(
            """
            <presentation xmlns="https://www.larkoffice.com/sml/2.0" width="960" height="540">
              <slide xmlns="https://www.larkoffice.com/sml/2.0">
                <data>
                  <shape id="outside-shape" type="text" topLeftX="-10" topLeftY="40" width="50" height="50"/>
                  <img id="outside-img" src="token" topLeftX="120" topLeftY="-20" width="50" height="50"/>
                  <chart id="outside-chart" topLeftX="900" topLeftY="100" width="100" height="100">
                    <chartPlotArea><chartPlot type="line"/></chartPlotArea>
                    <chartData>
                      <dim1><chartField name="category" valueType="string">A</chartField></dim1>
                      <dim2><chartField name="value" valueType="number">1</chartField></dim2>
                    </chartData>
                  </chart>
                </data>
              </slide>
            </presentation>
            """
        )
        issues = result["slides"][0]["issues"]
        self.assertEqual(result["summary"]["error_count"], 3)
        self.assertEqual(
            [(issue["code"], issue["elements"], issue["overflow"]) for issue in issues],
            [
                ("shape_out_of_canvas", ["outside-shape"], {"left": 10, "top": 0, "right": 0, "bottom": 0}),
                ("img_out_of_canvas", ["outside-img"], {"left": 0, "top": 20, "right": 0, "bottom": 0}),
                ("chart_out_of_canvas", ["outside-chart"], {"left": 0, "top": 0, "right": 40, "bottom": 0}),
            ],
        )

    def test_lint_xml_reports_line_out_of_canvas(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="body" type="text" topLeftX="80" topLeftY="80" width="300" height="60">
                  <content fontSize="18"><p>Visible content</p></content>
                </shape>
                <line id="connector" startX="80" startY="120" endX="980" endY="120"><border/></line>
              </data>
            </slide>
            """
        )

        self.assertEqual(result["summary"]["error_count"], 1)
        issue = result["slides"][0]["issues"][0]
        self.assertEqual(issue["code"], "line_out_of_canvas")
        self.assertEqual(issue["elements"], ["connector"])
        self.assertEqual(issue["overflow"], {"left": 0, "top": 0, "right": 20, "bottom": 0})

    def test_lint_xml_reports_horizontal_line_crossing_headline_glyphs(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="title" type="text" topLeftX="80" topLeftY="200" width="500" height="90">
                  <content fontSize="60"><p>测试文字 ABC</p></content>
                </shape>
                <line id="strike" startX="80" startY="245" endX="560" endY="245">
                  <border color="rgb(255, 0, 0)" width="4"/>
                </line>
              </data>
            </slide>
            """
        )
        crossing = [
            issue for issue in result["slides"][0]["errors"] if set(issue["elements"]) == {"strike", "title"}
        ]
        self.assertEqual(len(crossing), 1)
        self.assertEqual(crossing[0]["code"], "bbox_overlap")

    def test_lint_xml_reports_vertical_line_crossing_multiline_text(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="col" type="text" topLeftX="700" topLeftY="180" width="240" height="180">
                  <content fontSize="20"><p>第一行文字内容</p><p>第二行文字内容</p><p>第三行文字内容</p></content>
                </shape>
                <line id="vbar" startX="740" startY="170" endX="740" endY="360">
                  <border color="rgb(0, 0, 255)" width="3"/>
                </line>
              </data>
            </slide>
            """
        )
        crossing = [
            issue for issue in result["slides"][0]["errors"] if set(issue["elements"]) == {"vbar", "col"}
        ]
        self.assertEqual(len(crossing), 1)

    def test_lint_xml_reports_horizontal_line_inside_wide_line_spacing_span(self) -> None:
        # 3 lines of fontSize 20 at multiple:1.8 give a real 92px glyph span, but the flat
        # font_size*1.2 approximation is only 72px. Both boxes centre in the 200px shape, so the flat
        # eroded box is ~[246,314] while the spacing-aware eroded box is ~[236,324]. A rule at y=240
        # lands in that top margin -- inside the real glyph rows yet outside the flat box -- so it only
        # reports once the line-crossing path uses the spacing-aware height (Bucket C, slides p8/p10).
        result = xml_lint.lint_xml(
            """
            <slide xmlns="http://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="poem" type="text" topLeftX="80" topLeftY="180" width="360" height="200">
                  <content fontSize="20" lineSpacing="multiple:1.8"><p>第一行诗句文字</p><p>第二行诗句文字</p><p>第三行诗句文字</p></content>
                </shape>
                <line id="rule" startX="80" startY="240" endX="220" endY="240">
                  <border color="rgb(0, 0, 0)" width="3"/>
                </line>
              </data>
            </slide>
            """
        )
        crossing = [
            issue for issue in result["slides"][0]["errors"] if set(issue["elements"]) == {"rule", "poem"}
        ]
        self.assertEqual(len(crossing), 1)
        self.assertEqual(crossing[0]["code"], "bbox_overlap")

    def test_lint_xml_reports_diagonal_line_crossing_text_block(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="para" type="text" topLeftX="80" topLeftY="400" width="420" height="140">
                  <content fontSize="18"><p>这是一段测试文字用于验证线条穿过</p></content>
                </shape>
                <line id="diag" startX="80" startY="410" endX="500" endY="530">
                  <border color="rgb(255, 0, 0)" width="3"/>
                </line>
              </data>
            </slide>
            """
        )
        crossing = [
            issue for issue in result["slides"][0]["errors"] if set(issue["elements"]) == {"diag", "para"}
        ]
        self.assertEqual(len(crossing), 1)

    def test_lint_xml_ignores_diagonal_line_whose_bbox_but_not_segment_crosses_text(self) -> None:
        # The diagonal's axis-aligned bounding box overlaps the text, but the segment itself passes
        # through empty space in the opposite corner -- a naive bbox test would false-positive here.
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="corner-text" type="text" topLeftX="80" topLeftY="80" width="120" height="40">
                  <content fontSize="18"><p>corner</p></content>
                </shape>
                <line id="far-diag" startX="700" startY="80" endX="90" endY="500">
                  <border color="rgb(255, 0, 0)" width="3"/>
                </line>
              </data>
            </slide>
            """
        )
        crossing = [
            issue for issue in result["slides"][0]["errors"] if set(issue["elements"]) == {"far-diag", "corner-text"}
        ]
        self.assertEqual(crossing, [])

    def test_lint_xml_ignores_line_touching_text_frame_but_not_glyphs(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="lbl" type="text" topLeftX="80" topLeftY="80" width="300" height="200">
                  <content fontSize="18" verticalAlign="top"><p>短标签</p></content>
                </shape>
                <line id="below" startX="80" startY="270" endX="380" endY="270">
                  <border color="rgb(255, 0, 0)" width="2"/>
                </line>
              </data>
            </slide>
            """
        )
        self.assertEqual(result["summary"]["error_count"], 0)

    def test_lint_xml_ignores_invisible_line_crossing_text(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="title" type="text" topLeftX="80" topLeftY="200" width="500" height="90">
                  <content fontSize="60"><p>测试文字 ABC</p></content>
                </shape>
                <line id="ghost-line" startX="80" startY="245" endX="560" endY="245">
                  <border color="rgba(255, 0, 0, 0.03)" width="4"/>
                </line>
              </data>
            </slide>
            """
        )
        self.assertEqual(result["summary"]["error_count"], 0)

    def test_lint_xml_ignores_vertical_line_grazing_text_left_edge(self) -> None:
        # Verbatim from deck GpGusGCwplQyK8dFN9LczmBXnwQ slide 4: a vertical line sitting on the text
        # frame's left edge renders before the first glyph, so it must not be flagged.
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape width="240" height="60" topLeftX="120" topLeftY="100" type="text" id="bmm">
                  <content fontSize="20" fontFamily="Arial" color="rgba(31, 35, 41, 1)" lineSpacing="fixed:24">
                    <p>Vertical edge graze</p>
                  </content>
                </shape>
                <line id="bmX" startX="120.00000000000001" startY="90" endX="120.00000000000001" endY="150.00833275470998">
                  <border color="rgba(0, 0, 0, 1)"/>
                </line>
              </data>
            </slide>
            """
        )
        self.assertEqual(result["summary"]["error_count"], 0)

    def test_lint_xml_ignores_polyline_crossing_text(self) -> None:
        # Verbatim from deck GpGusGCwplQyK8dFN9LczmBXnwQ slide 6: the crossing check is scoped to
        # <line> only, so a <polyline> over text is not flagged.
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape width="240" height="60" topLeftX="120" topLeftY="100" type="text" id="bmr">
                  <content fontSize="20" fontFamily="Arial" color="rgba(31, 35, 41, 1)" lineSpacing="fixed:24">
                    <p>Polyline target</p>
                  </content>
                </shape>
                <polyline id="bmH" width="270" height="55" topLeftX="110" topLeftY="95">
                  <border color="rgba(0, 0, 0, 1)"/>
                </polyline>
              </data>
            </slide>
            """
        )
        self.assertEqual(result["summary"]["error_count"], 0)

    def test_lint_xml_ignores_line_below_visual_glyph_height(self) -> None:
        # Verbatim from deck GpGusGCwplQyK8dFN9LczmBXnwQ slide 7: the shape frame is 80px tall but the
        # single 20px line of glyphs occupies only its top; a line at the frame's lower region grazes
        # under the visual glyph box (underline look) and must not be flagged.
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape width="240" height="80" topLeftX="120" topLeftY="100" type="text" id="bmB">
                  <content fontSize="20" fontFamily="Arial" color="rgba(31, 35, 41, 1)" lineSpacing="fixed:24">
                    <p>Visual height target</p>
                  </content>
                </shape>
                <line id="bmQ" startX="110" startY="150" endX="380.00185184550116" endY="150">
                  <border color="rgba(0, 0, 0, 1)"/>
                </line>
              </data>
            </slide>
            """
        )
        self.assertEqual(result["summary"]["error_count"], 0)

    def test_lint_xml_uses_rotated_text_and_chart_bounds_for_canvas_validation(self) -> None:
        result = xml_lint.lint_xml(
            """
            <presentation xmlns="https://www.larkoffice.com/sml/2.0" width="960" height="540">
              <slide xmlns="https://www.larkoffice.com/sml/2.0">
                <data>
                  <shape id="rotated-text" type="text" topLeftX="0" topLeftY="0" width="100" height="100" rotation="45"/>
                  <chart id="rotated-chart" topLeftX="860" topLeftY="200" width="100" height="100" rotation="45">
                    <chartPlotArea><chartPlot type="line"/></chartPlotArea>
                    <chartData>
                      <dim1><chartField name="category" valueType="string">A</chartField></dim1>
                      <dim2><chartField name="value" valueType="number">1</chartField></dim2>
                    </chartData>
                  </chart>
                </data>
              </slide>
            </presentation>
            """
        )
        issues_by_element = {issue["elements"][0]: issue for issue in result["slides"][0]["issues"]}
        self.assertEqual(result["summary"]["error_count"], 2)
        self.assertEqual(issues_by_element["rotated-text"]["code"], "shape_out_of_canvas")
        self.assertAlmostEqual(issues_by_element["rotated-text"]["overflow"]["left"], 20.710678, places=5)
        self.assertAlmostEqual(issues_by_element["rotated-text"]["overflow"]["top"], 20.710678, places=5)
        self.assertEqual(issues_by_element["rotated-chart"]["code"], "chart_out_of_canvas")
        self.assertAlmostEqual(issues_by_element["rotated-chart"]["overflow"]["right"], 20.710678, places=5)

    def test_lint_xml_uses_declared_bounds_for_rect_and_images(self) -> None:
        result = xml_lint.lint_xml(
            """
            <presentation xmlns="https://www.larkoffice.com/sml/2.0" width="960" height="540">
              <slide xmlns="https://www.larkoffice.com/sml/2.0">
                <data>
                  <shape id="rotated-rect" type="rect" topLeftX="900" topLeftY="0" width="100" height="100" rotation="45"/>
                  <img id="rotated-image" src="token" topLeftX="900" topLeftY="200" width="100" height="100" rotation="45"/>
                </data>
              </slide>
            </presentation>
            """
        )
        issues_by_element = {issue["elements"][0]: issue for issue in result["slides"][0]["issues"]}
        self.assertEqual(result["summary"]["error_count"], 2)
        self.assertEqual(issues_by_element["rotated-rect"]["code"], "shape_out_of_canvas")
        self.assertEqual(issues_by_element["rotated-rect"]["overflow"], {"left": 0, "top": 0, "right": 40, "bottom": 0})
        self.assertEqual(issues_by_element["rotated-image"]["code"], "img_out_of_canvas")
        self.assertEqual(issues_by_element["rotated-image"]["overflow"], {"left": 0, "top": 0, "right": 40, "bottom": 0})

    def test_detect_elements_out_of_canvas_reports_every_element_kind(self) -> None:
        issues = xml_lint.detect_elements_out_of_canvas(
            [
                {"id": "table", "kind": "table", "x": 95, "y": 0, "width": 10, "height": 10, "rotation": 45},
                {"id": "chart", "kind": "chart", "x": 95, "y": 0, "width": 10, "height": 10, "rotation": 0},
                {
                    "id": "text",
                    "kind": "shape",
                    "type": "text",
                    "x": 95,
                    "y": 0,
                    "width": 10,
                    "height": 10,
                    "rotation": 0,
                },
                {
                    "id": "rect",
                    "kind": "shape",
                    "type": "rect",
                    "x": 95,
                    "y": 0,
                    "width": 10,
                    "height": 10,
                    "rotation": 45,
                },
                {"id": "image", "kind": "img", "x": 95, "y": 0, "width": 10, "height": 10, "rotation": 0},
                {
                    "id": "ellipse",
                    "kind": "shape",
                    "type": "ellipse",
                    "x": 95,
                    "y": 0,
                    "width": 10,
                    "height": 10,
                    "rotation": 0,
                },
                {
                    "id": "icon",
                    "kind": "icon",
                    "type": "icon",
                    "x": 95,
                    "y": 0,
                    "width": 10,
                    "height": 10,
                    "rotation": 0,
                },
                {
                    "id": "polyline",
                    "kind": "polyline",
                    "type": "polyline",
                    "x": 95,
                    "y": 0,
                    "width": 10,
                    "height": 10,
                    "rotation": 0,
                },
                {
                    "id": "line",
                    "kind": "line",
                    "type": "line",
                    "x": 95,
                    "y": 0,
                    "width": 10,
                    "height": 10,
                    "rotation": 0,
                },
                {
                    "id": "whiteboard",
                    "kind": "whiteboard",
                    "type": "whiteboard",
                    "x": 95,
                    "y": 0,
                    "width": 10,
                    "height": 10,
                    "rotation": 0,
                },
                {
                    "id": "embed",
                    "kind": "embed",
                    "type": "embed",
                    "x": 95,
                    "y": 0,
                    "width": 10,
                    "height": 10,
                    "rotation": 0,
                },
            ],
            100,
            100,
        )

        self.assertEqual(
            [issue["elements"] for issue in issues],
            [
                ["table"],
                ["chart"],
                ["text"],
                ["rect"],
                ["image"],
                ["ellipse"],
                ["icon"],
                ["polyline"],
                ["line"],
                ["whiteboard"],
                ["embed"],
            ],
        )
        self.assertEqual(issues[-1]["bbox"], {"x": 95, "y": 0, "width": 10, "height": 10})

    def test_lint_xml_rejects_non_finite_rotation_values_from_xsd(self) -> None:
        result = xml_lint.lint_xml(
            """
            <presentation xmlns="https://www.larkoffice.com/sml/2.0" width="960" height="540">
              <slide xmlns="https://www.larkoffice.com/sml/2.0">
                <data>
                  <shape id="infinite" type="text" topLeftX="-10" topLeftY="0" width="20" height="20" rotation="inf"/>
                  <shape id="negative-infinite" type="text" topLeftX="0" topLeftY="-10" width="20" height="20" rotation="-inf"/>
                  <chart id="not-a-number" topLeftX="950" topLeftY="0" width="20" height="20" rotation="nan">
                    <chartPlotArea><chartPlot type="line"/></chartPlotArea>
                    <chartData>
                      <dim1><chartField name="category" valueType="string">A</chartField></dim1>
                      <dim2><chartField name="value" valueType="number">1</chartField></dim2>
                    </chartData>
                  </chart>
                </data>
              </slide>
            </presentation>
            """
        )
        self.assertEqual(result["summary"]["error_count"], 3)
        slide_issues = result["slides"][0]["issues"]
        self.assertTrue(all(issue["code"] == "sxsd_invalid_scalar" for issue in slide_issues))
        self.assertEqual({issue["actual"] for issue in slide_issues}, {"inf", "-inf", "nan"})

    def test_lint_xml_reports_table_bottom_overflow_from_declared_bounds(self) -> None:
        result = xml_lint.lint_xml(
            """
            <presentation xmlns="https://www.larkoffice.com/sml/2.0" width="960" height="540">
              <slide xmlns="https://www.larkoffice.com/sml/2.0">
                <data>
                  <table id="score-table" topLeftX="54" topLeftY="238" width="414" height="385">
                    <tr><td><content><p>Score</p></content></td></tr>
                  </table>
                </data>
              </slide>
            </presentation>
            """
        )
        issue = result["slides"][0]["issues"][0]
        self.assertEqual(result["summary"]["error_count"], 1)
        self.assertEqual(issue["code"], "table_out_of_canvas")
        self.assertEqual(issue["elements"], ["score-table"])
        self.assertEqual(issue["overflow"], {"left": 0, "top": 0, "right": 0, "bottom": 83})
        self.assertEqual(issue["bbox"], {"x": 54, "y": 238, "width": 414, "height": 385})

    def test_lint_xml_reports_table_right_overflow_from_declared_bounds(self) -> None:
        result = xml_lint.lint_xml(
            """
            <presentation xmlns="https://www.larkoffice.com/sml/2.0" width="960" height="540">
              <slide xmlns="https://www.larkoffice.com/sml/2.0">
                <data>
                  <table id="wide-table" topLeftX="850" topLeftY="80" width="180" height="120">
                    <tr><td><content><p>Score</p></content></td></tr>
                  </table>
                </data>
              </slide>
            </presentation>
            """
        )
        issue = result["slides"][0]["issues"][0]
        self.assertEqual(result["summary"]["error_count"], 1)
        self.assertEqual(issue["code"], "table_out_of_canvas")
        self.assertEqual(issue["overflow"], {"left": 0, "top": 0, "right": 70, "bottom": 0})

    def test_lint_xml_allows_table_with_declared_bounds_inside_canvas(self) -> None:
        result = xml_lint.lint_xml(
            """
            <presentation xmlns="https://www.larkoffice.com/sml/2.0" width="960" height="540">
              <slide xmlns="https://www.larkoffice.com/sml/2.0">
                <data>
                  <table id="inside-table" topLeftX="40" topLeftY="120" width="880" height="360">
                    <tr><td><content><p>Score</p></content></td></tr>
                  </table>
                </data>
              </slide>
            </presentation>
            """
        )
        self.assertEqual(result["summary"]["error_count"], 0)
        self.assertEqual(result["summary"]["warning_count"], 0)

    def test_lint_xml_reports_resolved_table_bounds_when_declared_sizes_are_missing(self) -> None:
        result = xml_lint.lint_xml(
            """
            <presentation xmlns="https://www.larkoffice.com/sml/2.0" width="960" height="540">
              <slide xmlns="https://www.larkoffice.com/sml/2.0">
                <data>
                  <table id="implicit-size-table" topLeftX="850" topLeftY="480">
                    <colgroup><col/><col/></colgroup>
                    <tr><td/><td/></tr>
                    <tr><td/><td/></tr>
                  </table>
                </data>
              </slide>
            </presentation>
            """
        )
        issue = result["slides"][0]["issues"][0]
        self.assertEqual(result["summary"]["error_count"], 1)
        self.assertEqual(issue["code"], "table_out_of_canvas")
        self.assertEqual(issue["bbox"], {"x": 850, "y": 480, "width": 220, "height": 74})
        self.assertEqual(issue["overflow"], {"left": 0, "top": 0, "right": 110, "bottom": 14})

    def test_lint_xml_xml_path_preserves_source_index_after_filtered_table(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="http://www.larkoffice.com/sml/2.0">
              <data>
                <table id="t1" topLeftX="20" topLeftY="20">
                  <tr><td/></tr>
                </table>
                <table id="t2" topLeftX="20" topLeftY="100" width="9999" height="100">
                  <tr><td/></tr>
                </table>
              </data>
            </slide>
            """
        )

        issue = next(
            issue
            for issue in result["slides"][0]["issues"]
            if issue["code"] == "table_out_of_canvas"
        )
        self.assertEqual(issue["element_ids"], ["t2"])
        self.assertEqual(
            issue["related_objects"][0]["xml_path"],
            "slide[1]/data/table[2]",
        )

    def test_lint_xml_duplicate_id_keeps_issue_bound_to_original_shape(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="dup" type="rect" topLeftX="-20" topLeftY="40" width="50" height="50"/>
                <shape id="dup" type="rect" topLeftX="100" topLeftY="40" width="50" height="50"/>
              </data>
            </slide>
            """
        )

        canvas_issue = next(
            issue for issue in result["slides"][0]["issues"]
            if issue["code"] == "shape_out_of_canvas"
        )
        self.assertEqual(canvas_issue["element_ids"], ["dup"])
        self.assertEqual(
            canvas_issue["related_objects"],
            [
                {
                    "element_id": "dup",
                    "kind": "shape",
                    "type": "rect",
                    "bbox": {"x": -20, "y": 40, "width": 50, "height": 50},
                    "xml_path": "slide[1]/data/shape[1]",
                }
            ],
        )
        self.assertTrue(
            canvas_issue["hint"].startswith(
                "Locate via related_objects[].xml_path. "
            )
        )
        duplicate_issue = next(
            issue for issue in result["slides"][0]["issues"]
            if issue["code"] == "duplicate_element_id"
        )
        self.assertEqual(
            duplicate_issue["hint"],
            "Locate via related_objects[].xml_path. "
            "Do not invent replacement IDs. For newly authored elements, remove the id attribute. "
            "When updating read-back XML, keep the server ID on the original element only and remove it "
            "from copied or new elements.",
        )
        self.assertEqual(duplicate_issue["element_ids"], ["dup", "dup"])
        self.assertEqual(
            [obj["xml_path"] for obj in duplicate_issue["related_objects"]],
            ["slide[1]/data/shape[1]", "slide[1]/data/shape[2]"],
        )

    def test_lint_xml_blocks_duplicate_table_cell_ids(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <table id="table-1" topLeftX="80" topLeftY="80" width="800" height="120">
                  <colgroup><col width="400"/><col width="400"/></colgroup>
                  <tr height="120">
                    <td id="bjs"><content fontSize="24"><p>Original cell</p></content></td>
                    <td id="bjs"><content fontSize="24"><p>Copied cell</p></content></td>
                  </tr>
                </table>
              </data>
            </slide>
            """
        )

        issue = next(
            issue
            for issue in result["slides"][0]["issues"]
            if issue["code"] == "duplicate_element_id"
        )
        self.assertFalse(result["summary"]["release_ready"])
        self.assertEqual(issue["element_ids"], ["bjs", "bjs"])
        self.assertEqual(
            issue["related_objects"],
            [
                {
                    "element_id": "bjs",
                    "kind": "td",
                    "type": "td",
                    "xml_path": "slide[1]/data/table[1]/tr[1]/td[1]",
                },
                {
                    "element_id": "bjs",
                    "kind": "td",
                    "type": "td",
                    "xml_path": "slide[1]/data/table[1]/tr[1]/td[2]",
                },
            ],
        )

    def test_lint_xml_blocks_duplicate_id_shared_by_shape_and_table_cell(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="baa" type="rect" topLeftX="40" topLeftY="40" width="80" height="80"/>
                <table id="table-1" topLeftX="160" topLeftY="40" width="200" height="80">
                  <tr height="80"><td id="baa"><content fontSize="12"><p>Cell</p></content></td></tr>
                </table>
              </data>
            </slide>
            """
        )

        issue = next(
            issue
            for issue in result["slides"][0]["issues"]
            if issue["code"] == "duplicate_element_id"
        )
        self.assertEqual(issue["element_ids"], ["baa", "baa"])
        self.assertEqual(
            [obj["xml_path"] for obj in issue["related_objects"]],
            ["slide[1]/data/shape[1]", "slide[1]/data/table[1]/tr[1]/td[1]"],
        )

    def test_lint_xml_blocks_duplicate_id_shared_by_shape_and_undefined(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="dup" type="rect" topLeftX="40" topLeftY="40" width="80" height="80"/>
                <undefined id="dup" type="video"/>
              </data>
            </slide>
            """
        )

        issue = next(
            issue
            for issue in result["slides"][0]["issues"]
            if issue["code"] == "duplicate_element_id"
        )
        self.assertFalse(result["summary"]["release_ready"])
        self.assertEqual(issue["element_ids"], ["dup", "dup"])
        self.assertEqual(
            issue["related_objects"],
            [
                {
                    "element_id": "dup",
                    "kind": "shape",
                    "type": "rect",
                    "bbox": {"x": 40, "y": 40, "width": 80, "height": 80},
                    "xml_path": "slide[1]/data/shape[1]",
                },
                {
                    "element_id": "dup",
                    "kind": "undefined",
                    "type": "video",
                    "xml_path": "slide[1]/data/undefined[1]",
                },
            ],
        )

    def test_lint_xml_does_not_report_unique_table_cell_and_note_ids(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <table id="table-1" topLeftX="80" topLeftY="80" width="800" height="120">
                  <colgroup><col width="400"/><col width="400"/></colgroup>
                  <tr height="120"><td id="baa"/><td id="bab"/></tr>
                </table>
              </data>
              <note id="bac"><content fontSize="12"><p>Note</p></content></note>
            </slide>
            """
        )

        self.assertNotIn(
            "duplicate_element_id",
            [issue["code"] for issue in result["slides"][0]["issues"]],
        )

    def test_lint_xml_blocks_duplicate_ids_across_slides(self) -> None:
        result = xml_lint.lint_xml(
            """
            <presentation xmlns="https://www.larkoffice.com/sml/2.0" width="960" height="540">
              <slide>
                <data>
                  <shape id="dup" type="rect" topLeftX="40" topLeftY="40" width="80" height="80"/>
                </data>
              </slide>
              <slide>
                <data>
                  <shape id="dup" type="rect" topLeftX="140" topLeftY="40" width="80" height="80"/>
                </data>
              </slide>
            </presentation>
            """
        )

        issue = next(
            issue
            for issue in result["document"]["errors"]
            if issue["code"] == "duplicate_element_id"
        )
        self.assertFalse(result["summary"]["release_ready"])
        self.assertEqual(issue["element_ids"], ["dup", "dup"])
        self.assertEqual(
            issue["related_objects"],
            [
                {
                    "element_id": "dup",
                    "kind": "shape",
                    "type": "rect",
                    "bbox": {"x": 40, "y": 40, "width": 80, "height": 80},
                    "xml_path": "slide[1]/data/shape[1]",
                },
                {
                    "element_id": "dup",
                    "kind": "shape",
                    "type": "rect",
                    "bbox": {"x": 140, "y": 40, "width": 80, "height": 80},
                    "xml_path": "slide[2]/data/shape[1]",
                },
            ],
        )

    def test_lint_xml_does_not_treat_slide_ids_as_element_ids(self) -> None:
        result = xml_lint.lint_xml(
            """
            <presentation xmlns="https://www.larkoffice.com/sml/2.0" width="960" height="540">
              <slide id="dup"><data/></slide>
              <slide id="dup"><data/></slide>
            </presentation>
            """
        )

        self.assertNotIn(
            "duplicate_element_id",
            [issue["code"] for issue in result["document"]["errors"]],
        )

    def test_lint_xml_does_not_treat_presentation_id_as_element_id(self) -> None:
        result = xml_lint.lint_xml(
            """
            <presentation xmlns="https://www.larkoffice.com/sml/2.0" id="dup" width="960" height="540">
              <slide>
                <data><undefined id="dup" type="video"/></data>
              </slide>
            </presentation>
            """
        )

        self.assertNotIn(
            "duplicate_element_id",
            [
                issue["code"]
                for issue in [
                    *result["document"]["errors"],
                    *result["slides"][0]["errors"],
                ]
            ],
        )

    def test_lint_xml_blocks_duplicate_note_ids_across_slides(self) -> None:
        result = xml_lint.lint_xml(
            """
            <presentation xmlns="https://www.larkoffice.com/sml/2.0" width="960" height="540">
              <slide>
                <note id="baa"><content fontSize="12"><p>First note</p></content></note>
              </slide>
              <slide>
                <note id="baa"><content fontSize="12"><p>Copied note</p></content></note>
              </slide>
            </presentation>
            """
        )

        issue = next(
            issue
            for issue in result["document"]["errors"]
            if issue["code"] == "duplicate_element_id"
        )
        self.assertFalse(result["summary"]["release_ready"])
        self.assertEqual(issue["element_ids"], ["baa", "baa"])
        self.assertEqual(
            issue["related_objects"],
            [
                {
                    "element_id": "baa",
                    "kind": "note",
                    "type": "note",
                    "xml_path": "slide[1]/note[1]",
                },
                {
                    "element_id": "baa",
                    "kind": "note",
                    "type": "note",
                    "xml_path": "slide[2]/note[1]",
                },
            ],
        )

    def test_lint_xml_cross_kind_duplicate_id_does_not_change_related_object_kind(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="dup" type="rect" topLeftX="-20" topLeftY="40" width="50" height="50"/>
                <img id="dup" src="token" topLeftX="100" topLeftY="40" width="50" height="50"/>
              </data>
            </slide>
            """
        )

        issue = next(
            issue for issue in result["slides"][0]["issues"]
            if issue["code"] == "shape_out_of_canvas"
        )
        self.assertEqual(issue["related_objects"][0]["kind"], "shape")
        self.assertEqual(
            issue["related_objects"][0]["xml_path"],
            "slide[1]/data/shape[1]",
        )
        duplicate_issue = next(
            issue
            for issue in result["slides"][0]["issues"]
            if issue["code"] == "duplicate_element_id"
        )
        self.assertEqual(
            [obj["xml_path"] for obj in duplicate_issue["related_objects"]],
            ["slide[1]/data/shape[1]", "slide[1]/data/img[1]"],
        )

    def test_normalize_issue_does_not_repeat_xml_path_hint_prefix(self) -> None:
        xml_path = "slide[1]/data/shape[1]"
        element = {
            "id": "box",
            "_source_id": "box",
            "_ref": xml_path,
            "xml_path": xml_path,
            "kind": "shape",
            "type": "rect",
            "x": 0,
            "y": 0,
            "width": 40,
            "height": 40,
        }
        prefix = "Locate via related_objects[].xml_path."

        issue = xml_lint.normalize_issue(
            {
                "level": "error",
                "code": "shape_out_of_canvas",
                "elements": [xml_path],
                "canvas": {"width": 960, "height": 540},
                "bbox": {"x": -10, "y": 0, "width": 40, "height": 40},
                "overflow": {"left": 10, "top": 0, "right": 0, "bottom": 0},
                "hint": f"{prefix} Move the shape inside the canvas.",
            },
            1,
            {xml_path: element},
        )

        self.assertEqual(issue["hint"].count(prefix), 1)

    def test_lint_xml_elements_keep_locator_for_anonymous_related_object(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape type="text" topLeftX="100" topLeftY="100" width="300" height="100">
                  <content fontSize="24"><p>Important text</p></content>
                </shape>
                <img id="srv-42" src="token" topLeftX="100" topLeftY="100" width="300" height="100"/>
              </data>
            </slide>
            """
        )

        issue = next(
            issue
            for issue in result["slides"][0]["issues"]
            if issue["code"] == "image_covers_text"
        )
        self.assertEqual(
            issue["elements"],
            ["srv-42", "slide[1]/data/shape[1]"],
        )
        self.assertEqual(issue["element_ids"], ["srv-42"])
        self.assertEqual(len(issue["related_objects"]), 2)

    def test_normalize_issue_deduplicates_repeated_element_refs(self) -> None:
        xml_path = "slide[1]/data/shape[1]"
        element = {
            "id": "srv-42",
            "_source_id": "srv-42",
            "_ref": xml_path,
            "xml_path": xml_path,
            "kind": "shape",
            "type": "rect",
            "x": 0,
            "y": 0,
            "width": 40,
            "height": 40,
        }

        issue = xml_lint.normalize_issue(
            {
                "level": "warning",
                "code": "blank_slide",
                "measurement": {
                    "visible_element_count": 0,
                    "declared_element_count": 1,
                },
                "elements": [xml_path, xml_path],
            },
            1,
            {xml_path: element},
        )

        self.assertEqual(issue["elements"], ["srv-42"])
        self.assertEqual(issue["element_ids"], ["srv-42"])
        self.assertEqual(len(issue["related_objects"]), 1)

    def test_lint_xml_reports_duplicate_ids_for_every_linted_element_kind(self) -> None:
        duplicate_pairs = {
            "shape": (
                '<shape id="dup" type="rect" topLeftX="10" topLeftY="10" width="40" height="40"/>',
                '<shape id="dup" type="rect" topLeftX="60" topLeftY="10" width="40" height="40"/>',
            ),
            "chart": (
                '<chart id="dup" topLeftX="10" topLeftY="10" width="40" height="40"><chartPlotArea><chartPlot type="line"/></chartPlotArea><chartData><dim1><chartField name="category" valueType="string">A</chartField></dim1><dim2><chartField name="value" valueType="number">1</chartField></dim2></chartData></chart>',
                '<chart id="dup" topLeftX="60" topLeftY="10" width="40" height="40"><chartPlotArea><chartPlot type="line"/></chartPlotArea><chartData><dim1><chartField name="category" valueType="string">A</chartField></dim1><dim2><chartField name="value" valueType="number">1</chartField></dim2></chartData></chart>',
            ),
            "table": (
                '<table id="dup" topLeftX="10" topLeftY="10" width="40" height="40"><colgroup><col width="40"/></colgroup><tr height="40"><td/></tr></table>',
                '<table id="dup" topLeftX="60" topLeftY="10" width="40" height="40"><colgroup><col width="40"/></colgroup><tr height="40"><td/></tr></table>',
            ),
            "img": (
                '<img id="dup" src="token" topLeftX="10" topLeftY="10" width="40" height="40"/>',
                '<img id="dup" src="token" topLeftX="60" topLeftY="10" width="40" height="40"/>',
            ),
            "line": (
                '<line id="dup" startX="10" startY="10" endX="40" endY="40"><border color="rgb(0, 0, 0)"/></line>',
                '<line id="dup" startX="60" startY="10" endX="90" endY="40"><border color="rgb(0, 0, 0)"/></line>',
            ),
            "icon": (
                '<icon id="dup" iconType="iconpark/Base/setting.svg" topLeftX="10" topLeftY="10" width="40" height="40"><fill><fillColor color="rgb(0, 0, 0)"/></fill></icon>',
                '<icon id="dup" iconType="iconpark/Base/setting.svg" topLeftX="60" topLeftY="10" width="40" height="40"><fill><fillColor color="rgb(0, 0, 0)"/></fill></icon>',
            ),
            "polyline": (
                '<polyline id="dup" topLeftX="10" topLeftY="10" width="40" height="40"><border color="rgb(0, 0, 0)"/></polyline>',
                '<polyline id="dup" topLeftX="60" topLeftY="10" width="40" height="40"><border color="rgb(0, 0, 0)"/></polyline>',
            ),
        }
        for kind, pair in duplicate_pairs.items():
            with self.subTest(kind=kind):
                result = xml_lint.lint_xml(
                    f'<slide xmlns="https://www.larkoffice.com/sml/2.0"><data>{pair[0]}{pair[1]}</data></slide>'
                )
                issue = next(
                    issue
                    for issue in result["slides"][0]["issues"]
                    if issue["code"] == "duplicate_element_id"
                )
                self.assertEqual(issue["element_ids"], ["dup", "dup"])
                self.assertEqual(
                    [obj["xml_path"] for obj in issue["related_objects"]],
                    [
                        f"slide[1]/data/{kind}[1]",
                        f"slide[1]/data/{kind}[2]",
                    ],
                )

    def test_lint_xml_missing_id_does_not_collide_with_explicit_synthetic_like_id(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape type="rect" topLeftX="-20" topLeftY="40" width="50" height="50"/>
                <shape id="shape-1" type="rect" topLeftX="100" topLeftY="40" width="50" height="50"/>
              </data>
            </slide>
            """
        )

        issue = next(
            issue for issue in result["slides"][0]["issues"]
            if issue["code"] == "shape_out_of_canvas"
        )
        self.assertEqual(issue["element_ids"], [])
        self.assertNotIn("element_id", issue["related_objects"][0])
        self.assertEqual(
            issue["related_objects"][0]["xml_path"],
            "slide[1]/data/shape[1]",
        )
        self.assertTrue(
            issue["hint"].startswith("Locate via related_objects[].xml_path. ")
        )
        self.assertNotIn(
            "duplicate_element_id",
            [candidate["code"] for candidate in result["slides"][0]["issues"]],
        )

    def test_lint_xml_empty_id_is_not_exposed_as_an_element_id(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="" type="rect" topLeftX="-20" topLeftY="40" width="50" height="50"/>
              </data>
            </slide>
            """
        )

        issue = next(
            issue
            for issue in result["slides"][0]["issues"]
            if issue["code"] == "shape_out_of_canvas"
        )
        self.assertEqual(issue["element_ids"], [])
        self.assertNotIn("element_id", issue["related_objects"][0])
        self.assertEqual(
            issue["related_objects"][0]["xml_path"],
            "slide[1]/data/shape[1]",
        )

    def test_lint_xml_uses_resolved_table_bounds_for_canvas_validation(self) -> None:
        result = xml_lint.lint_xml(
            """
            <presentation xmlns="https://www.larkoffice.com/sml/2.0" width="960" height="540">
              <slide xmlns="https://www.larkoffice.com/sml/2.0">
                <data>
                  <table id="resolved-overflow-table" topLeftX="800" topLeftY="80" width="100" height="40">
                    <colgroup><col width="100"/><col width="100"/></colgroup>
                    <tr height="40"><td/><td/></tr>
                  </table>
                </data>
              </slide>
            </presentation>
            """
        )
        issues = result["slides"][0]["issues"]
        canvas_issue = next(issue for issue in issues if issue["code"] == "table_out_of_canvas")
        mismatch_issue = next(issue for issue in issues if issue["code"] == "table_resolved_size_mismatch")
        self.assertEqual(result["summary"]["error_count"], 1)
        self.assertEqual(canvas_issue["bbox"], {"x": 800, "y": 80, "width": 200, "height": 40})
        self.assertEqual(canvas_issue["overflow"]["right"], 40)
        self.assertEqual(mismatch_issue["dimension"], "width")
        self.assertEqual(mismatch_issue["resolved_size"], canvas_issue["bbox"]["width"])

    def test_lint_xml_uses_the_same_anonymous_table_path_for_all_table_diagnostics(self) -> None:
        result = xml_lint.lint_xml(
            """
            <presentation xmlns="https://www.larkoffice.com/sml/2.0" width="960" height="540">
              <slide xmlns="https://www.larkoffice.com/sml/2.0">
                <data>
                  <shape id="title" type="text" topLeftX="40" topLeftY="40" width="200" height="40"/>
                  <img id="logo" src="token" topLeftX="40" topLeftY="100" width="40" height="40"/>
                  <table topLeftX="900" topLeftY="80" width="100" height="40">
                    <colgroup><col width="100"/><col width="100"/></colgroup>
                    <tr height="40"><td/><td/></tr>
                  </table>
                </data>
              </slide>
            </presentation>
            """
        )
        issues = result["slides"][0]["issues"]
        canvas_issue = next(issue for issue in issues if issue["code"] == "table_out_of_canvas")
        mismatch_issue = next(issue for issue in issues if issue["code"] == "table_resolved_size_mismatch")
        self.assertEqual(canvas_issue["elements"], ["slide[1]/data/table[1]"])
        self.assertEqual(mismatch_issue["elements"], ["slide[1]/data/table[1]"])
        self.assertEqual(
            canvas_issue["related_objects"][0]["xml_path"],
            "slide[1]/data/table[1]",
        )
        self.assertEqual(
            mismatch_issue["related_objects"][0]["xml_path"],
            "slide[1]/data/table[1]",
        )
        self.assertNotIn("element_id", canvas_issue["related_objects"][0])
        self.assertNotIn("element_id", mismatch_issue["related_objects"][0])

    def test_lint_xml_reports_info_when_table_target_size_resolves_larger_than_declared(self) -> None:
        result = xml_lint.lint_xml(
            """
            <presentation xmlns="https://www.larkoffice.com/sml/2.0" width="960" height="540">
              <slide xmlns="https://www.larkoffice.com/sml/2.0">
                <data>
                  <table id="size-mismatch" topLeftX="40" topLeftY="120" width="200" height="80">
                    <colgroup><col span="2" width="100"/><col width="50"/></colgroup>
                    <tr height="40"><td/><td/><td/></tr>
                    <tr height="60"><td/><td/><td/></tr>
                  </table>
                </data>
              </slide>
            </presentation>
            """
        )
        issues_by_dimension = {issue["dimension"]: issue for issue in result["slides"][0]["issues"]}
        self.assertEqual(result["summary"]["error_count"], 0)
        self.assertEqual(result["summary"]["warning_count"], 0)
        self.assertEqual(result["summary"]["info_count"], 2)
        self.assertEqual(issues_by_dimension["width"]["level"], "info")
        self.assertEqual(issues_by_dimension["width"]["code"], "table_resolved_size_mismatch")
        self.assertEqual(issues_by_dimension["width"]["resolved_sizes"], [100, 100, 50])
        self.assertEqual(issues_by_dimension["width"]["resolved_size"], 250)
        self.assertEqual(issues_by_dimension["height"]["resolved_sizes"], [40, 60])
        self.assertEqual(issues_by_dimension["height"]["resolved_size"], 100)

    def test_lint_xml_does_not_report_info_when_table_target_size_is_resolved_exactly(self) -> None:
        result = xml_lint.lint_xml(
            """
            <presentation xmlns="https://www.larkoffice.com/sml/2.0" width="960" height="540">
              <slide xmlns="https://www.larkoffice.com/sml/2.0">
                <data>
                  <table id="size-match" topLeftX="40" topLeftY="120" width="300" height="100">
                    <colgroup><col width="100"/><col/></colgroup>
                    <tr height="40"><td/><td/></tr>
                    <tr><td/><td/></tr>
                  </table>
                </data>
              </slide>
            </presentation>
            """
        )
        self.assertEqual(result["summary"]["error_count"], 0)
        self.assertEqual(result["summary"]["warning_count"], 0)
        self.assertEqual(result["slides"][0]["issues"], [])

    def test_lint_xml_reports_rotated_text_colliding_with_horizontal_text(self) -> None:
        # A 270-rotated label sweeps a vertical footprint that overlaps a nearby horizontal label. With
        # rotation-aware glyph boxes the collision is detectable, and because the runs are not parallel
        # the overlap ratio is tiny so the absolute-area fallback must flag it (slides p6, Bucket D+E).
        result = xml_lint.lint_xml(
            """
            <slide xmlns="http://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="flat" type="text" topLeftX="240" topLeftY="200" width="64" height="24">
                  <content fontSize="16"><p>文字碰撞</p></content>
                </shape>
                <shape id="spun" type="text" topLeftX="272" topLeftY="232" width="64" height="24" rotation="270">
                  <content fontSize="16"><p>文字碰撞</p></content>
                </shape>
              </data>
            </slide>
            """
        )
        collisions = [
            issue for issue in result["slides"][0]["errors"]
            if issue["code"] == "bbox_overlap" and set(issue["elements"]) == {"flat", "spun"}
        ]
        self.assertEqual(len(collisions), 1)

    def test_lint_xml_still_suppresses_coincident_shadow_text_overlay(self) -> None:
        # A drop-shadow duplicate offset by a pixel is an intentional overlay; the coincidence check
        # must keep suppressing it even though the text is identical (guards the E1 tightening).
        result = xml_lint.lint_xml(
            """
            <slide xmlns="http://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="shadow" type="text" topLeftX="200" topLeftY="200" width="200" height="40">
                  <content fontSize="20"><p>标题文字</p></content>
                </shape>
                <shape id="fill" type="text" topLeftX="202" topLeftY="202" width="200" height="40">
                  <content fontSize="20"><p>标题文字</p></content>
                </shape>
              </data>
            </slide>
            """
        )
        collisions = [
            issue for issue in result["slides"][0]["errors"]
            if issue["code"] == "bbox_overlap" and set(issue["elements"]) == {"shadow", "fill"}
        ]
        self.assertEqual(collisions, [])

    def test_lint_xml_reports_text_overflowing_background_container(self) -> None:
        # Text anchored inside a background card whose glyph box spills past the card's bottom edge has
        # outgrown the box the author sized for it (slides p7). The card is drawn first (lower z-order),
        # so it is the container; the text must surface as text_overflows_container (Bucket B).
        result = xml_lint.lint_xml(
            """
            <slide xmlns="http://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="card" type="rect" topLeftX="200" topLeftY="200" width="120" height="40">
                  <fill><fillColor color="rgba(230,230,230,1)"/></fill>
                </shape>
                <shape id="body" type="text" topLeftX="205" topLeftY="205" width="110" height="120">
                  <content fontSize="16"><p>第一行</p><p>第二行</p><p>第三行</p></content>
                </shape>
              </data>
            </slide>
            """
        )
        overflow = [
            issue for issue in result["slides"][0]["errors"]
            if issue["code"] == "text_overflows_container" and set(issue["elements"]) == {"body", "card"}
        ]
        self.assertEqual(len(overflow), 1)
        self.assertGreater(overflow[0]["overflow"]["bottom"], 4)

    def test_lint_xml_locates_id_less_text_overflowing_container_by_xml_path(self) -> None:
        # Neither shape carries an authored id, so the issue must fall back to the xml_path locator
        # and carry both elements in related_objects. Reporting a bare synthesized "shape-N" name here
        # would leave the agent with no way to find either element in the source XML.
        result = xml_lint.lint_xml(
            """
            <slide xmlns="http://www.larkoffice.com/sml/2.0">
              <data>
                <shape type="rect" topLeftX="200" topLeftY="200" width="120" height="40">
                  <fill><fillColor color="rgba(230,230,230,1)"/></fill>
                </shape>
                <shape type="text" topLeftX="205" topLeftY="205" width="110" height="120">
                  <content fontSize="16"><p>第一行</p><p>第二行</p><p>第三行</p></content>
                </shape>
              </data>
            </slide>
            """
        )
        overflow = [
            issue for issue in result["slides"][0]["errors"]
            if issue["code"] == "text_overflows_container"
        ]
        self.assertEqual(len(overflow), 1)
        self.assertEqual(
            overflow[0]["elements"],
            ["slide[1]/data/shape[2]", "slide[1]/data/shape[1]"],
        )
        self.assertEqual(
            [related["xml_path"] for related in overflow[0]["related_objects"]],
            ["slide[1]/data/shape[2]", "slide[1]/data/shape[1]"],
        )

    def test_lint_xml_reports_text_frame_crossing_background_container_border(self) -> None:
        # The authored text frame crosses the card's bottom border even when vertical centering puts
        # the estimated glyph box fully below the card. This mirrors the Kimi slide p15 leak.
        result = xml_lint.lint_xml(
            """
            <slide xmlns="http://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="card" type="rect" topLeftX="60" topLeftY="140" width="420" height="280">
                  <fill><fillColor color="rgba(26, 43, 74, 0.04)"/></fill>
                </shape>
                <shape id="body" type="text" topLeftX="95" topLeftY="415" width="365" height="36">
                  <content fontSize="11" fontFamily="思源黑体" color="rgba(118, 118, 118, 1)">
                    <p>图文公式联合推理能力强，学术论文中的公式图表理解准确</p>
                  </content>
                </shape>
              </data>
            </slide>
            """
        )
        overflow = [
            issue for issue in result["slides"][0]["errors"]
            if issue["code"] == "text_overflows_container" and issue["elements"] == ["body", "card"]
        ]
        self.assertEqual(len(overflow), 1)
        self.assertEqual(overflow[0]["overflow"]["bottom"], 31)

    def test_lint_xml_uses_card_owner_in_front_of_full_canvas_background(self) -> None:
        # A full-slide background intersects the whole text frame, so raw max-area ownership would pick it
        # instead of the smaller card and miss the card overflow. Prefer the specific card when present.
        result = xml_lint.lint_xml(
            """
            <presentation xmlns="http://www.larkoffice.com/sml/2.0" width="960" height="540">
              <slide xmlns="http://www.larkoffice.com/sml/2.0">
                <data>
                  <shape id="background" type="rect" topLeftX="0" topLeftY="0" width="960" height="540">
                    <fill><fillColor color="rgba(0,0,0,1)"/></fill>
                  </shape>
                  <shape id="card" type="rect" topLeftX="200" topLeftY="200" width="120" height="40">
                    <fill><fillColor color="rgba(230,230,230,1)"/></fill>
                  </shape>
                  <shape id="body" type="text" topLeftX="205" topLeftY="205" width="110" height="120">
                    <content fontSize="16"><p>第一行</p><p>第二行</p><p>第三行</p></content>
                  </shape>
                </data>
              </slide>
            </presentation>
            """
        )
        overflow = [
            issue for issue in result["slides"][0]["errors"]
            if issue["code"] == "text_overflows_container" and issue["elements"] == ["body", "card"]
        ]
        self.assertEqual(len(overflow), 1)
        self.assertEqual(overflow[0]["overflow"]["bottom"], 85)

    def test_lint_xml_owns_text_to_innermost_nested_card_not_outer_panel(self) -> None:
        # A card nests inside a larger panel and the text overflows the card's bottom but fits inside the
        # panel. The outer panel overlaps the text frame at least as much as the card, so raw max-area
        # ownership would pick the panel and stay silent. Ownership must pick the innermost container so
        # the card overflow surfaces (slides IN6SsZSGFlvPEGdyir4cYbJanZe p2).
        result = xml_lint.lint_xml(
            """
            <presentation xmlns="http://www.larkoffice.com/sml/2.0" width="960" height="540">
              <slide xmlns="http://www.larkoffice.com/sml/2.0">
                <data>
                  <shape id="panel" type="rect" topLeftX="0" topLeftY="0" width="600" height="400">
                    <fill><fillColor color="rgba(240,240,245,1)"/></fill>
                  </shape>
                  <shape id="card" type="rect" topLeftX="200" topLeftY="100" width="200" height="100">
                    <fill><fillColor color="rgba(230,230,230,1)"/></fill>
                  </shape>
                  <shape id="body" type="text" topLeftX="210" topLeftY="110" width="180" height="110">
                    <content fontSize="14"><p>Same 20px overflow, but panel wins as owner.</p></content>
                  </shape>
                </data>
              </slide>
            </presentation>
            """
        )
        overflow = [
            issue for issue in result["slides"][0]["errors"]
            if issue["code"] == "text_overflows_container"
        ]
        self.assertEqual(len(overflow), 1)
        self.assertEqual(overflow[0]["elements"], ["body", "card"])
        self.assertEqual(overflow[0]["overflow"]["bottom"], 20)

    def test_lint_xml_ignores_text_fitting_inside_background_container(self) -> None:
        # Text whose glyph box stays inside its background card is fine; the container rule must stay
        # silent so tightly-fitted-but-valid cards are not falsely reported.
        result = xml_lint.lint_xml(
            """
            <slide xmlns="http://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="card" type="rect" topLeftX="200" topLeftY="200" width="200" height="120">
                  <fill><fillColor color="rgba(230,230,230,1)"/></fill>
                </shape>
                <shape id="body" type="text" topLeftX="210" topLeftY="210" width="180" height="40">
                  <content fontSize="14"><p>短文本</p></content>
                </shape>
              </data>
            </slide>
            """
        )
        codes = [issue["code"] for issue in result["slides"][0]["issues"]]
        self.assertNotIn("text_overflows_container", codes)

    def test_lint_xml_reports_filled_shape_covering_foreign_text_as_overlap(self) -> None:
        # A card painted after a neighboring card's text is a real visual occlusion. The error names
        # the covering shape and foreign text instead of treating every card-to-card intersection as
        # an error.
        result = xml_lint.lint_xml(
            """
            <slide xmlns="http://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="left-card" type="rect" topLeftX="100" topLeftY="100" width="160" height="80">
                  <fill><fillColor color="rgba(230,230,230,1)"/></fill>
                </shape>
                <shape id="left-text" type="text" topLeftX="110" topLeftY="120" width="140" height="30">
                  <content fontSize="16"><p>左侧文字</p></content>
                </shape>
                <shape id="right-card" type="rect" topLeftX="160" topLeftY="100" width="160" height="80">
                  <fill><fillColor color="rgba(230,230,230,0.2)"/></fill>
                </shape>
              </data>
            </slide>
            """
        )
        occlusions = [
            issue
            for issue in result["slides"][0]["errors"]
            if issue["code"] == "bbox_overlap"
            and issue["elements"] == ["right-card", "left-text"]
        ]
        self.assertEqual(len(occlusions), 1)
        self.assertGreater(occlusions[0]["measurement"]["intersection_area"], 4)

    def test_lint_xml_reports_rotated_shape_covering_text_as_overlap(self) -> None:
        # A shape authored as a tall bar beside the text but rotated 90 sweeps its footprint across the
        # glyphs. The glyph box is already rotated into canvas space, so the covering shape must be too;
        # comparing its unrotated bbox (which sits clear of the text) would miss the occlusion entirely.
        result = xml_lint.lint_xml(
            """
            <slide xmlns="http://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="label" type="text" topLeftX="150" topLeftY="185" width="130" height="30">
                  <content fontSize="16"><p>被遮挡文字</p></content>
                </shape>
                <shape id="bar" type="rect" topLeftX="250" topLeftY="100" width="60" height="200" rotation="90">
                  <fill><fillColor color="rgba(230,80,80,1)"/></fill>
                </shape>
              </data>
            </slide>
            """
        )
        occlusions = [
            issue
            for issue in result["slides"][0]["errors"]
            if issue["code"] == "bbox_overlap"
            and issue["elements"] == ["bar", "label"]
        ]
        self.assertEqual(len(occlusions), 1)
        self.assertGreater(occlusions[0]["measurement"]["intersection_area"], 4)

    def test_lint_xml_reports_neighboring_text_card_background_overlap(self) -> None:
        # A text card's background can overlap a neighboring card background without covering the
        # text glyphs directly. That is still a layout collision and should surface as bbox_overlap.
        result = xml_lint.lint_xml(
            """
            <slide xmlns="http://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="left-card" type="rect" topLeftX="100" topLeftY="100" width="140" height="55">
                  <fill><fillColor color="rgba(156,92,56,0.2)"/></fill>
                </shape>
                <shape id="right-card" type="rect" topLeftX="180" topLeftY="100" width="160" height="55">
                  <fill><fillColor color="rgba(120,100,160,0.15)"/></fill>
                </shape>
                <shape id="right-text" type="text" topLeftX="190" topLeftY="108" width="140" height="40">
                  <content fontSize="11" textAlign="center"><p><strong>韩孟诗派</strong></p><p>韩愈 · 孟郊 · 贾岛</p></content>
                </shape>
              </data>
            </slide>
            """
        )
        overlaps = [
            issue
            for issue in result["slides"][0]["errors"]
            if issue["code"] == "bbox_overlap"
            and issue["elements"] == ["left-card", "right-card"]
        ]
        self.assertEqual(len(overlaps), 1)
        self.assertEqual(overlaps[0]["measurement"]["intersection_area"], 3300)

    def test_lint_xml_reports_low_alpha_text_card_background_overlap(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="http://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="left-card" type="rect" topLeftX="100" topLeftY="100" width="140" height="55">
                  <fill><fillColor color="rgba(156,92,56,0.02)"/></fill>
                </shape>
                <shape id="right-card" type="rect" topLeftX="180" topLeftY="100" width="160" height="55">
                  <fill><fillColor color="rgba(120,100,160,0.02)"/></fill>
                </shape>
                <shape id="right-text" type="text" topLeftX="190" topLeftY="108" width="140" height="40">
                  <content fontSize="11" textAlign="center"><p><strong>韩孟诗派</strong></p><p>韩愈 · 孟郊 · 贾岛</p></content>
                </shape>
              </data>
            </slide>
            """
        )
        overlaps = [
            issue
            for issue in result["slides"][0]["errors"]
            if issue["code"] == "bbox_overlap"
            and issue["elements"] == ["left-card", "right-card"]
        ]
        self.assertEqual(len(overlaps), 1)
        self.assertEqual(overlaps[0]["measurement"]["left_fill_alpha"], 0.02)
        self.assertEqual(overlaps[0]["measurement"]["right_fill_alpha"], 0.02)

    def test_lint_xml_ignores_empty_decorative_shape_background_overlap(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="http://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="left-deco" type="rect" topLeftX="100" topLeftY="100" width="140" height="55">
                  <fill><fillColor color="rgba(156,92,56,0.2)"/></fill>
                </shape>
                <shape id="right-deco" type="rect" topLeftX="180" topLeftY="100" width="160" height="55">
                  <fill><fillColor color="rgba(120,100,160,0.15)"/></fill>
                </shape>
              </data>
            </slide>
            """
        )
        overlaps = [
            issue
            for issue in result["slides"][0]["issues"]
            if issue["code"] == "bbox_overlap"
            and set(issue["elements"]) == {"left-deco", "right-deco"}
        ]
        self.assertEqual(overlaps, [])

    def test_lint_xml_ignores_background_shape_behind_text(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="http://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="card" type="rect" topLeftX="100" topLeftY="100" width="200" height="80">
                  <fill><fillColor color="rgba(230,230,230,0.2)"/></fill>
                </shape>
                <shape id="text" type="text" topLeftX="110" topLeftY="120" width="180" height="30">
                  <content fontSize="16"><p>卡片文字</p></content>
                </shape>
              </data>
            </slide>
            """
        )
        codes = [issue["code"] for issue in result["slides"][0]["issues"]]
        self.assertNotIn("bbox_overlap", codes)

    def test_lint_xml_ignores_transparent_shape_over_text(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="http://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="text" type="text" topLeftX="100" topLeftY="120" width="180" height="30">
                  <content fontSize="16"><p>底层文字</p></content>
                </shape>
                <shape id="transparent-cover" type="rect" topLeftX="100" topLeftY="100" width="200" height="80">
                  <fill><fillColor color="rgba(230,230,230,0)"/></fill>
                </shape>
              </data>
            </slide>
            """
        )
        codes = [issue["code"] for issue in result["slides"][0]["issues"]]
        self.assertNotIn("bbox_overlap", codes)

    def test_lint_xml_respects_shape_fill_variants_for_text_occlusion(self) -> None:
        cases = [
            ("missing-fill", "", False),
            ("empty-fill", "<fill/>", True),
            ("image-fill", '<fill><fillImg src="token"/></fill>', True),
            ("transparent-image-fill", '<fill><fillImg src="token" alpha="0"/></fill>', False),
            ("pattern-fill", "<fill><fillPattern/></fill>", True),
            ("transparent-pattern-fill", '<fill><fillPattern alpha="0"/></fill>', False),
        ]
        for shape_id, fill_xml, should_report in cases:
            with self.subTest(shape_id=shape_id):
                result = xml_lint.lint_xml(
                    f"""
                    <slide xmlns="http://www.larkoffice.com/sml/2.0">
                      <data>
                        <shape id="text" type="text" topLeftX="100" topLeftY="120" width="180" height="30">
                          <content fontSize="16"><p>底层文字</p></content>
                        </shape>
                        <shape id="{shape_id}" type="rect" topLeftX="100" topLeftY="100" width="200" height="80">
                          {fill_xml}
                        </shape>
                      </data>
                    </slide>
                    """
                )
                overlaps = [
                    issue
                    for issue in result["slides"][0]["issues"]
                    if issue["code"] == "bbox_overlap" and set(issue["elements"]) == {shape_id, "text"}
                ]
                self.assertEqual(len(overlaps), 1 if should_report else 0)

    def test_lint_xml_reports_free_text_shape_overlapping_table_grid(self) -> None:
        # A free-floating text shape whose glyph box lands on top of a sibling table occludes the cell
        # contents (slides p4). The table renders its own text; a stray shape over the grid is an
        # accidental overlay, so it must surface as table_covers_text (Bucket B).
        result = xml_lint.lint_xml(
            """
            <presentation xmlns="http://www.larkoffice.com/sml/2.0" width="960" height="540">
              <slide xmlns="http://www.larkoffice.com/sml/2.0">
                <data>
                  <table id="grid" topLeftX="200" topLeftY="200" width="400" height="150">
                    <tr><td><content><p>A</p></content></td></tr>
                  </table>
                  <shape id="stray" type="text" topLeftX="260" topLeftY="240" width="120" height="30">
                    <content fontSize="16"><p>覆盖表格</p></content>
                  </shape>
                </data>
              </slide>
            </presentation>
            """
        )
        occlusions = [
            issue for issue in result["slides"][0]["errors"]
            if issue["code"] == "table_covers_text" and set(issue["elements"]) == {"grid", "stray"}
        ]
        self.assertEqual(len(occlusions), 1)
        issue = occlusions[0]
        self.assertEqual(issue["element_ids"], ["grid", "stray"])
        self.assertEqual(
            [
                (obj["element_id"], obj["kind"], obj["type"], obj["bbox"], obj["xml_path"])
                for obj in issue["related_objects"]
            ],
            [
                (
                    "grid",
                    "table",
                    "table",
                    {"x": 200, "y": 200, "width": 400, "height": 150},
                    "slide[1]/data/table[1]",
                ),
                (
                    "stray",
                    "shape",
                    "text",
                    {"x": 260, "y": 240, "width": 120, "height": 30},
                    "slide[1]/data/shape[1]",
                ),
            ],
        )
        self.assertTrue(issue["hint"].startswith("Locate via related_objects[].xml_path. "))

    def test_lint_xml_ignores_table_with_only_cell_text(self) -> None:
        # Cell text is part of the table's own layout and is never extracted as a standalone shape, so
        # a table alone must not self-report table_covers_text (guards against a runaway detector).
        result = xml_lint.lint_xml(
            """
            <presentation xmlns="http://www.larkoffice.com/sml/2.0" width="960" height="540">
              <slide xmlns="http://www.larkoffice.com/sml/2.0">
                <data>
                  <table id="solo" topLeftX="200" topLeftY="200" width="400" height="150">
                    <tr><td><content><p>Score</p></content></td></tr>
                  </table>
                </data>
              </slide>
            </presentation>
            """
        )
        codes = [issue["code"] for issue in result["slides"][0]["issues"]]
        self.assertNotIn("table_covers_text", codes)

    def test_lint_xml_reports_free_text_shape_overlapping_chart(self) -> None:
        # A free-floating text shape whose glyph box lands on top of a sibling chart occludes the chart's
        # generated labels and legend (slides p5: a headline dropped onto a pie chart's ring). The chart
        # renders its own text; a stray shape over the plot area is an accidental overlay, so it must
        # surface as chart_covers_text (Bucket B3).
        result = xml_lint.lint_xml(
            """
            <presentation xmlns="http://www.larkoffice.com/sml/2.0" width="960" height="540">
              <slide xmlns="http://www.larkoffice.com/sml/2.0">
                <data>
                  <chart id="pie" topLeftX="200" topLeftY="60" width="420" height="420">
                    <chartPlotArea><chartPlot type="pie"/></chartPlotArea>
                    <chartData>
                      <dim1><chartField name="category" valueType="string">A,B</chartField></dim1>
                      <dim2><chartField name="value" valueType="number">1,2</chartField></dim2>
                    </chartData>
                  </chart>
                  <shape id="stray" type="text" topLeftX="360" topLeftY="120" width="120" height="40">
                    <content fontSize="32"><p>abc 99%</p></content>
                  </shape>
                </data>
              </slide>
            </presentation>
            """
        )
        occlusions = [
            issue for issue in result["slides"][0]["errors"]
            if issue["code"] == "chart_covers_text" and set(issue["elements"]) == {"pie", "stray"}
        ]
        self.assertEqual(len(occlusions), 1)

    def test_lint_xml_ignores_chart_not_overlapping_text(self) -> None:
        # A chart and a text shape that sit side by side without their glyph boxes touching must not
        # report chart_covers_text (guards the detector from firing on mere co-existence).
        result = xml_lint.lint_xml(
            """
            <presentation xmlns="http://www.larkoffice.com/sml/2.0" width="960" height="540">
              <slide xmlns="http://www.larkoffice.com/sml/2.0">
                <data>
                  <chart id="pie" topLeftX="40" topLeftY="60" width="300" height="300">
                    <chartPlotArea><chartPlot type="pie"/></chartPlotArea>
                    <chartData>
                      <dim1><chartField name="category" valueType="string">A,B</chartField></dim1>
                      <dim2><chartField name="value" valueType="number">1,2</chartField></dim2>
                    </chartData>
                  </chart>
                  <shape id="caption" type="text" topLeftX="600" topLeftY="80" width="200" height="40">
                    <content fontSize="16"><p>Sales breakdown</p></content>
                  </shape>
                </data>
              </slide>
            </presentation>
            """
        )
        codes = [issue["code"] for issue in result["slides"][0]["issues"]]
        self.assertNotIn("chart_covers_text", codes)

    def test_lint_xml_ignores_text_inside_donut_center_hole(self) -> None:
        # A ring/donut chart (chartPlot type="pie" with chartSectors innerRadius > 0) has an empty
        # center. A headline like "70%+ / API收入占比" dropped into that hole occludes nothing -- the
        # blank middle is the classic KPI-donut design -- so chart_covers_text must NOT fire when the
        # glyph box sits fully inside the hole circle. Chart is 400x400 at (100,60): center (300,260),
        # pie radius 200, hole radius 0.55*200=110. The 80x36 headline centered at (300,260) fits.
        result = xml_lint.lint_xml(
            """
            <presentation xmlns="http://www.larkoffice.com/sml/2.0" width="960" height="540">
              <slide xmlns="http://www.larkoffice.com/sml/2.0">
                <data>
                  <chart id="donut" topLeftX="100" topLeftY="60" width="400" height="400">
                    <chartPlotArea>
                      <chartPlot type="pie">
                        <chartSeriesList>
                          <chartSeries index="1">
                            <chartSectors innerRadius="0.55" offsetRadius="0" startAngle="0"/>
                          </chartSeries>
                        </chartSeriesList>
                      </chartPlot>
                    </chartPlotArea>
                    <chartData>
                      <dim1><chartField name="category" valueType="string">A,B</chartField></dim1>
                      <dim2><chartField name="value" valueType="number">1,2</chartField></dim2>
                    </chartData>
                  </chart>
                  <shape id="kpi" type="text" topLeftX="260" topLeftY="242" width="80" height="36">
                    <content fontSize="16" textAlign="center"><p>70%+</p></content>
                  </shape>
                </data>
              </slide>
            </presentation>
            """
        )
        codes = [issue["code"] for issue in result["slides"][0]["issues"]]
        self.assertNotIn("chart_covers_text", codes)

    def test_lint_xml_reports_text_over_donut_ring(self) -> None:
        # The center-hole exemption is narrow: a text shape whose glyph box spills onto the donut's
        # colored ring (not fully inside the empty hole) still occludes the chart's segments/labels and
        # must surface as chart_covers_text. Same 400x400 donut (hole radius 110 around center 300,260);
        # this shape sits far to the left, its glyph box landing on the ring, not the hole.
        result = xml_lint.lint_xml(
            """
            <presentation xmlns="http://www.larkoffice.com/sml/2.0" width="960" height="540">
              <slide xmlns="http://www.larkoffice.com/sml/2.0">
                <data>
                  <chart id="donut" topLeftX="100" topLeftY="60" width="400" height="400">
                    <chartPlotArea>
                      <chartPlot type="pie">
                        <chartSeriesList>
                          <chartSeries index="1">
                            <chartSectors innerRadius="0.55" offsetRadius="0" startAngle="0"/>
                          </chartSeries>
                        </chartSeriesList>
                      </chartPlot>
                    </chartPlotArea>
                    <chartData>
                      <dim1><chartField name="category" valueType="string">A,B</chartField></dim1>
                      <dim2><chartField name="value" valueType="number">1,2</chartField></dim2>
                    </chartData>
                  </chart>
                  <shape id="stray" type="text" topLeftX="130" topLeftY="240" width="120" height="40">
                    <content fontSize="32"><p>abc 99%</p></content>
                  </shape>
                </data>
              </slide>
            </presentation>
            """
        )
        occlusions = [
            issue for issue in result["slides"][0]["errors"]
            if issue["code"] == "chart_covers_text" and set(issue["elements"]) == {"donut", "stray"}
        ]
        self.assertEqual(len(occlusions), 1)

    def test_lint_xml_rejects_donut_inner_radius_outside_fraction_range(self) -> None:
        # lint_slide skips schema validation on purpose here: innerRadius="55" is out of the [0,1]
        # fraction range, and via lint_xml the sxsd error would suppress the slide's geometry checks
        # before this occlusion could surface.
        result = xml_lint.lint_slide(
            """
            <slide xmlns="http://www.larkoffice.com/sml/2.0">
              <data>
                <chart id="donut" topLeftX="100" topLeftY="60" width="400" height="400">
                  <chartPlotArea>
                    <chartPlot type="pie">
                      <chartSeriesList>
                        <chartSeries index="1">
                          <chartSectors innerRadius="55" offsetRadius="0" startAngle="0"/>
                        </chartSeries>
                      </chartSeriesList>
                    </chartPlot>
                  </chartPlotArea>
                  <chartData>
                    <dim1><chartField name="category" valueType="string">A,B</chartField></dim1>
                    <dim2><chartField name="value" valueType="number">1,2</chartField></dim2>
                  </chartData>
                </chart>
                <shape id="stray" type="text" topLeftX="130" topLeftY="240" width="120" height="40">
                  <content fontSize="32"><p>abc 99%</p></content>
                </shape>
              </data>
            </slide>
            """,
            slide_number=1,
        )
        occlusions = [
            issue for issue in result["issues"]
            if issue["code"] == "chart_covers_text"
            and set(issue["elements"])
            == {"slide[1]/data/chart[1]", "slide[1]/data/shape[1]"}
        ]
        self.assertEqual(len(occlusions), 1)

    def test_lint_xml_reports_auto_fit_title_growing_onto_body_below(self) -> None:
        # A shape-auto-fit title sized for one line wraps to two, growing downward past its authored box
        # onto the body text beneath it (slides p9). shape-auto-fit only means the box grows to fit, so
        # the grown glyph height -- not the authored height -- is what collides. The dedicated auto-fit
        # growth detector reports this from the grown region; the generic text-text check now catches the
        # grown-box overlap too, and dedup collapses them to a single bbox_overlap for the pair.
        result = xml_lint.lint_xml(
            """
            <slide xmlns="http://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="title" type="text" topLeftX="80" topLeftY="20" width="480" height="36">
                  <content fontSize="24" autoFit="shape-auto-fit"><p>02. | Literature Review - International Research</p></content>
                </shape>
                <shape id="body" type="text" topLeftX="80" topLeftY="60" width="480" height="200">
                  <content fontSize="15" verticalAlign="top"><p>1. Marxist Perspective</p><p>Line two of body copy</p><p>Line three of body copy</p><p>Line four of body copy</p><p>Line five of body copy</p><p>Line six of body copy</p></content>
                </shape>
              </data>
            </slide>
            """
        )
        collisions = [
            issue for issue in result["slides"][0]["errors"]
            if issue["code"] == "bbox_overlap" and set(issue["elements"]) == {"title", "body"}
        ]
        self.assertEqual(len(collisions), 1)

    def test_lint_xml_ignores_auto_fit_title_with_space_below(self) -> None:
        # An identical wrapping auto-fit title with an empty gap below it grows harmlessly; the check
        # must stay silent so ordinary auto-fit growth is not flagged (guards the grown-region area gate).
        result = xml_lint.lint_xml(
            """
            <slide xmlns="http://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="title" type="text" topLeftX="80" topLeftY="20" width="480" height="36">
                  <content fontSize="24" autoFit="shape-auto-fit"><p>02. | Literature Review - International Research</p></content>
                </shape>
                <shape id="body" type="text" topLeftX="80" topLeftY="300" width="480" height="200">
                  <content fontSize="15"><p>1. Marxist Perspective</p></content>
                </shape>
              </data>
            </slide>
            """
        )
        collisions = [
            issue for issue in result["slides"][0]["issues"]
            if issue["code"] == "bbox_overlap" and set(issue["elements"]) == {"title", "body"}
        ]
        self.assertEqual(collisions, [])

    def test_lint_xml_does_not_treat_divider_rule_as_text_background_container(self) -> None:
        # A thin horizontal rule under a title is a divider, not a container. Owning a title's grown
        # glyph box to a 3px rule and reporting it as text_overflows_container is a false positive
        # (slides p9); the line-like guard must keep the divider out of the container candidate set.
        result = xml_lint.lint_xml(
            """
            <slide xmlns="http://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="rule" type="rect" topLeftX="40" topLeftY="60" width="880" height="3">
                  <fill><fillColor color="rgba(40,60,120,1)"/></fill>
                </shape>
                <shape id="title" type="text" topLeftX="80" topLeftY="20" width="480" height="36">
                  <content fontSize="24" autoFit="shape-auto-fit"><p>02. | Literature Review - International Research</p></content>
                </shape>
              </data>
            </slide>
            """
        )
        container_hits = [
            issue for issue in result["slides"][0]["issues"]
            if issue["code"] == "text_overflows_container" and "rule" in issue["elements"]
        ]
        self.assertEqual(container_hits, [])


    def test_lint_xml_keeps_resolved_table_sizes_positive_when_target_is_too_small(self) -> None:
        result = xml_lint.lint_xml(
            """
            <presentation xmlns="https://www.larkoffice.com/sml/2.0" width="960" height="540">
              <slide xmlns="https://www.larkoffice.com/sml/2.0">
                <data>
                  <table id="narrow-table" topLeftX="40" topLeftY="120" width="1">
                    <colgroup><col/><col/></colgroup>
                    <tr><td/><td/></tr>
                  </table>
                </data>
              </slide>
            </presentation>
            """
        )
        issue = result["slides"][0]["issues"][0]
        self.assertEqual(issue["dimension"], "width")
        self.assertEqual(issue["resolved_sizes"], [1, 1])
        self.assertEqual(issue["resolved_size"], 2)

    def test_fill_last_size_gap_preserves_target_when_positive_sizes_are_possible(self) -> None:
        final_sizes = xml_lint.fill_last_size_gap([10, 10], 3)
        self.assertEqual(final_sizes, [2, 1])
        self.assertEqual(sum(final_sizes), 3)

    def test_cli_reports_table_layout_size_info_for_weighted_min_layout_cases(self) -> None:
        cases = {
            "target-exact": (
                """
                <table topLeftX="40" topLeftY="120" width="360" height="150">
                  <colgroup><col width="100"/><col width="200"/></colgroup>
                  <tr height="40"><td/><td/></tr><tr height="60"><td/><td/></tr>
                </table>
                """,
                0,
            ),
            "declared-size-exceeds-target": (
                """
                <table topLeftX="40" topLeftY="120" width="200" height="80">
                  <colgroup><col span="2" width="100"/><col width="50"/></colgroup>
                  <tr height="40"><td/><td/><td/></tr><tr height="60"><td/><td/><td/></tr>
                </table>
                """,
                2,
            ),
            "remaining-space-insufficient": (
                """
                <table topLeftX="40" topLeftY="120" width="80" height="30">
                  <colgroup><col width="80"/><col/></colgroup>
                  <tr height="40"><td/><td/></tr><tr><td/><td/></tr>
                </table>
                """,
                2,
            ),
            "no-target-size": (
                """
                <table topLeftX="40" topLeftY="120">
                  <colgroup><col width="80"/><col/></colgroup>
                  <tr height="40"><td/><td/></tr><tr><td/><td/></tr>
                </table>
                """,
                0,
            ),
        }
        script_path = Path(xml_lint.__file__).resolve()
        with tempfile.TemporaryDirectory() as temp_dir:
            for name, (table_xml, expected_info_count) in cases.items():
                with self.subTest(case=name):
                    input_path = Path(temp_dir) / f"{name}.xml"
                    input_path.write_text(
                        f"""
                        <presentation xmlns="https://www.larkoffice.com/sml/2.0" width="960" height="540">
                          <slide xmlns="https://www.larkoffice.com/sml/2.0"><data>{table_xml}</data></slide>
                        </presentation>
                        """,
                        encoding="utf-8",
                    )
                    completed = subprocess.run(
                        [sys.executable, str(script_path), "--input", str(input_path)],
                        capture_output=True,
                        check=False,
                        text=True,
                    )
                    result = json.loads(completed.stdout)
                    self.assertEqual(completed.returncode, 0, completed.stderr)
                    self.assertEqual(result["summary"]["error_count"], 0)
                    self.assertEqual(result["summary"]["warning_count"], 0)
                    self.assertEqual(result["summary"]["info_count"], expected_info_count)
                    self.assertTrue(
                        all(issue["level"] == "info" for issue in result["slides"][0]["issues"]),
                        result["slides"][0]["issues"],
                    )

    def test_lint_xml_detects_invalid_template_text_stack_overlap(self) -> None:
        cases = [
            (
                "subtitle-too-high",
                """
                <shape type="text" topLeftX="40" topLeftY="80" width="240" height="90">
                  <content textType="title" fontSize="44"><p>Title</p></content>
                </shape>
                <shape type="text" topLeftX="40" topLeftY="90" width="240" height="80">
                  <content textType="sub-headline" fontSize="20"><p>Subtitle</p></content>
                </shape>
                """,
            ),
        ]
        for name, shapes in cases:
            with self.subTest(name=name):
                result = xml_lint.lint_xml(
                    f"""
                    <presentation xmlns="https://www.larkoffice.com/sml/2.0" width="960" height="540">
                      <slide xmlns="https://www.larkoffice.com/sml/2.0">
                        <data>{shapes}</data>
                      </slide>
                    </presentation>
                    """
                )
                self.assertEqual(result["summary"]["error_count"], 1)
                self.assertEqual(result["slides"][0]["issues"][0]["code"], "bbox_overlap")

    def test_lint_xml_reports_chart_covering_text_bearing_rect_shape(self) -> None:
        # slides p6 (Fix 1): a chart drawn in front of a filled rect that *carries its own text*
        # ("shape遮挡") occludes those glyphs. The detector used to key only on type="text" shapes and
        # missed text-bearing rects, so pin that a chart over a rect's glyphs surfaces chart_covers_text.
        result = xml_lint.lint_xml(
            """
            <presentation xmlns="https://www.larkoffice.com/sml/2.0" width="960" height="540">
              <slide xmlns="https://www.larkoffice.com/sml/2.0"><data>
                <shape id="label" type="rect" topLeftX="100" topLeftY="100" width="200" height="60">
                  <fill><fillColor color="rgba(255, 255, 255, 1)"/></fill>
                  <content fontSize="20"><p>覆盖文字</p></content>
                </shape>
                <chart id="chart" topLeftX="100" topLeftY="100" width="200" height="60">
                  <chartPlotArea>
                    <chartPlot type="bar"><chartSeriesList><chartSeries index="1"/></chartSeriesList></chartPlot>
                  </chartPlotArea>
                  <chartData>
                    <dim1><chartField name="category" valueType="string">A,B</chartField></dim1>
                    <dim2><chartField name="value" valueType="number">1,2</chartField></dim2>
                  </chartData>
                </chart>
              </data></slide>
            </presentation>
            """
        )
        occlusions = [
            issue
            for issue in result["slides"][0]["issues"]
            if issue["code"] == "chart_covers_text" and set(issue["elements"]) == {"chart", "label"}
        ]
        self.assertEqual(len(occlusions), 1)

    def test_lint_xml_reports_no_wrap_text_glyphs_running_off_canvas(self) -> None:
        # slides p16 (Fix 3): a wrap="false" run keeps its full unwrapped line width, so a 300px word in
        # a 400px box paints ink well past the 960 canvas even though the authored box stays on-canvas.
        # Pin that the off-canvas glyph extent is caught rather than hidden by the in-bounds authored box.
        result = xml_lint.lint_xml(
            """
            <presentation xmlns="https://www.larkoffice.com/sml/2.0" width="960" height="540">
              <slide xmlns="https://www.larkoffice.com/sml/2.0"><data>
                <shape id="huge" type="text" topLeftX="40" topLeftY="80" width="400" height="400">
                  <content fontSize="300" wrap="false"><p>CONTENTS</p></content>
                </shape>
              </data></slide>
            </presentation>
            """
        )
        out_of_canvas = [
            issue
            for issue in result["slides"][0]["issues"]
            if issue["code"] == "shape_out_of_canvas" and issue["elements"] == ["huge"]
        ]
        self.assertEqual(len(out_of_canvas), 1)

    def test_lint_xml_reports_wrapping_title_ink_landing_on_subtitle(self) -> None:
        # slides p17 (Fix 4): a 72px title sized for one line but authored with a hard break wraps to two
        # lines, growing its ink down onto the subtitle below even though the authored boxes are stacked
        # (vertical offset >= 0.75*font). The stack exemption must yield to the real glyph collision.
        result = xml_lint.lint_xml(
            """
            <presentation xmlns="https://www.larkoffice.com/sml/2.0" width="960" height="540">
              <slide xmlns="https://www.larkoffice.com/sml/2.0"><data>
                <shape id="title" type="text" topLeftX="60" topLeftY="140" width="500" height="200">
                  <content textType="title" fontSize="72"><p>数码宝贝</p><p>全系列巡礼</p></content>
                </shape>
                <shape id="subtitle" type="text" topLeftX="60" topLeftY="320" width="400" height="60">
                  <content textType="sub-headline" fontSize="18" lineSpacing="multiple:1.6"><p>九部TV动画</p></content>
                </shape>
              </data></slide>
            </presentation>
            """
        )
        overlaps = [
            issue
            for issue in result["slides"][0]["issues"]
            if issue["code"] == "bbox_overlap" and set(issue["elements"]) == {"title", "subtitle"}
        ]
        self.assertEqual(len(overlaps), 1)

    def test_lint_xml_reports_dense_body_authored_above_compression_floor(self) -> None:
        # slides p12 (Fix 2a): a body authored at multiple:2 with 8 paragraphs in a box that only fits
        # ~1.6x still overflows -- renderers tighten dense bodies by only a bounded fraction, not all the
        # way to the 1.6x floor. The flat 1.6x cap hid this; the compression model must keep flagging it.
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0"><data>
              <shape id="body" type="text" topLeftX="40" topLeftY="40" width="360" height="200">
                <content fontSize="12" lineSpacing="multiple:2" autoFit="no-auto-fit">
                  <p>第一段落文字内容说明</p><p>第二段落文字内容说明</p><p>第三段落文字内容说明</p>
                  <p>第四段落文字内容说明</p><p>第五段落文字内容说明</p><p>第六段落文字内容说明</p>
                  <p>第七段落文字内容说明</p><p>第八段落文字内容说明</p><p>第九段落文字内容说明</p>
                  <p>第十段落文字内容说明</p>
                </content>
              </shape>
            </data></slide>
            """
        )
        overflow = [
            issue
            for issue in result["slides"][0]["issues"]
            if issue["code"] == "text_may_overflow_shape" and issue["elements"] == ["body"]
        ]
        self.assertEqual(len(overflow), 1)

    def test_lint_xml_reports_caption_flush_against_container_bottom_edge(self) -> None:
        # slides p12 (Fix 2b): captions laid flush on a card's bottom border share its edge (0px gap), so
        # their boxes touch with exactly 0 intersection area. Area-only ownership orphaned them; the edge
        # adjacency tolerance must own the caption to the card so the overflow past its border is flagged.
        result = xml_lint.lint_xml(
            """
            <presentation xmlns="https://www.larkoffice.com/sml/2.0" width="960" height="540">
              <slide xmlns="https://www.larkoffice.com/sml/2.0"><data>
                <shape id="card" type="rect" topLeftX="680" topLeftY="175" width="260" height="295">
                  <fill><fillColor color="rgba(255, 255, 255, 1)"/></fill>
                </shape>
                <shape id="caption" type="text" topLeftX="719" topLeftY="470" width="58" height="12">
                  <content fontSize="10"><p>路由专家</p></content>
                </shape>
              </data></slide>
            </presentation>
            """
        )
        overflows = [
            issue
            for issue in result["slides"][0]["issues"]
            if issue["code"] == "text_overflows_container" and set(issue["elements"]) == {"caption", "card"}
        ]
        self.assertEqual(len(overflows), 1)
        self.assertGreater(overflows[0]["overflow"]["bottom"], 0)

    def test_lint_xml_does_not_own_title_to_flush_decorative_neighbour(self) -> None:
        # slides Rejusj: a decorative right-arrow shape (0..468px wide) sits flush against the left edge
        # of a title that starts at the arrow's right edge (468px, 0px x-gap) and is taller-overlapped by
        # it on the y axis. The edge adjacency tolerance must not promote the arrow to the title's
        # container just because their boxes touch -- the arrow (468px) is narrower than the title (492px)
        # on the touching axis, so it cannot contain it. Owning the title to the arrow produced a bogus
        # right:492px text_overflows_container.
        result = xml_lint.lint_xml(
            """
            <presentation xmlns="https://www.larkoffice.com/sml/2.0" width="960" height="540">
              <slide xmlns="https://www.larkoffice.com/sml/2.0"><data>
                <shape id="arrow" type="right-arrow" topLeftX="0" topLeftY="180" width="468" height="120">
                  <fill><fillColor color="rgba(79, 110, 145, 1)"/></fill>
                </shape>
                <shape id="title" type="text" topLeftX="468" topLeftY="188" width="492" height="80">
                  <content fontSize="30" fontFamily="Arial" wrap="false"><p>标题从装饰箭头右边缘开始</p></content>
                </shape>
              </data></slide>
            </presentation>
            """
        )
        overflows = [
            issue
            for issue in result["slides"][0]["issues"]
            if issue["code"] == "text_overflows_container" and set(issue["elements"]) == {"title", "arrow"}
        ]
        self.assertEqual(overflows, [])

    def test_lint_xml_reports_wide_sans_big_type_colliding_with_neighbour(self) -> None:
        # slides p19: a 60px bold Montserrat "48h" advances wider than the humanist-sans baseline assumes,
        # so its ink (real right edge ~179px) touches the "即做即售"/"当日鲜制" runs starting at x170. The
        # generic sans coefficients stopped the estimate at ~165px and scored the overlap as 0; the
        # wide-sans tier must measure it wide enough that the glyph collision surfaces as bbox_overlap.
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0"><data>
              <shape id="hero" type="text" topLeftX="60" topLeftY="175" width="240" height="70">
                <content textType="title" fontSize="60" fontFamily="Montserrat" bold="true" wrap="false"><p>48h</p></content>
              </shape>
              <shape id="label" type="text" topLeftX="170" topLeftY="195" width="200" height="24">
                <content fontSize="14" wrap="false"><p>即做即售</p></content>
              </shape>
              <shape id="sub" type="text" topLeftX="170" topLeftY="220" width="280" height="20">
                <content fontSize="11" wrap="false"><p>当日鲜制，锁住最佳风味</p></content>
              </shape>
            </data></slide>
            """
        )
        overlap_pairs = {
            frozenset(issue["elements"])
            for issue in result["slides"][0]["issues"]
            if issue["code"] == "bbox_overlap"
        }
        self.assertIn(frozenset({"hero", "label"}), overlap_pairs)
        self.assertIn(frozenset({"hero", "sub"}), overlap_pairs)

    def test_classify_font_family_routes_geometric_sans_to_wide_tier(self) -> None:
        # Pin the routing directly: geometric/wide sans families widen their glyph advance, so a digit in
        # Montserrat must measure wider than the same digit in the humanist-sans baseline (Arial).
        self.assertEqual(xml_lint.classify_font_family("Montserrat"), "wide-sans")
        self.assertEqual(xml_lint.classify_font_family("Arial"), "sans")
        wide_digit = xml_lint.estimate_character_width("8", 60, font_family="Montserrat")
        narrow_digit = xml_lint.estimate_character_width("8", 60, font_family="Arial")
        self.assertGreater(wide_digit, narrow_digit)

    def test_estimate_character_width_gives_wide_symbols_their_own_advance(self) -> None:
        # "%" and a handful of common symbols (@ & $ ¥ £ # + = < > ~) render much wider than the generic
        # punct coefficient (0.50em), so measuring them at that coefficient under-reports the line and
        # hides real wraps (slides I9dd p24). Each must carry a per-glyph advance strictly wider than a
        # narrow mark like ".", so the fix lives in the estimator, not a shape classifier.
        narrow = xml_lint.estimate_character_width(".", 100, font_family="思源黑体")
        for symbol in "%@&$¥£#+=<>~":
            with self.subTest(symbol=symbol):
                advance = xml_lint.estimate_character_width(symbol, 100, font_family="思源黑体")
                self.assertGreater(advance, narrow)
        # We only raise coefficients, never lower them: narrower marks keep the punct baseline so a
        # smaller estimate can never mask a wrap (the gate prefers false positives over missed overflow).
        for symbol in "*/":
            with self.subTest(symbol=symbol):
                self.assertEqual(
                    xml_lint.estimate_character_width(symbol, 100, font_family="思源黑体"),
                    narrow,
                )


    def test_lint_xml_reports_vertical_text_image_overlap_as_warning(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0"><data>
              <shape id="text" type="text" vert="vert" topLeftX="100" topLeftY="100" width="100" height="100">
                <content><p>Vertical</p></content>
              </shape>
              <img id="image" src="token" topLeftX="120" topLeftY="120" width="20" height="20"/>
            </data></slide>
            """
        )
        issue = next(issue for issue in result["slides"][0]["issues"] if issue["code"] == "image_may_cover_vertical_text")
        self.assertEqual(issue["level"], "info")
        self.assertEqual(result["summary"]["error_count"], 0)
        self.assertEqual(result["summary"]["info_count"], 1)

    def test_lint_xml_related_objects_include_source_xml_paths(self) -> None:
        result = xml_lint.lint_xml(
            """
            <presentation xmlns="http://www.larkoffice.com/sml/2.0" width="960" height="540">
              <slide>
                <data>
                  <shape type="text" topLeftX="80" topLeftY="80" width="400" height="60">
                    <content fontSize="24"><p>Control slide</p></content>
                  </shape>
                </data>
              </slide>
              <slide>
                <data>
                  <shape type="text" topLeftX="70" topLeftY="55" width="820" height="70">
                    <content fontSize="32"><p>shape-3 mapping experiment</p></content>
                  </shape>
                  <shape type="text" topLeftX="80" topLeftY="165" width="400" height="70">
                    <content fontSize="18"><p>First, preserve source order.</p></content>
                  </shape>
                  <shape type="text" topLeftX="80" topLeftY="315" width="400" height="64">
                    <content fontSize="26"><p>TARGET_SHAPE_THREE</p></content>
                  </shape>
                  <img src="token" topLeftX="80" topLeftY="305" width="400" height="110"/>
                </data>
              </slide>
            </presentation>
            """
        )

        issue = next(
            issue
            for issue in result["slides"][1]["issues"]
            if issue["code"] == "image_covers_text"
        )
        self.assertEqual(
            [(obj["kind"], obj["xml_path"]) for obj in issue["related_objects"]],
            [
                ("img", "slide[2]/data/img[1]"),
                ("shape", "slide[2]/data/shape[3]"),
            ],
        )
        self.assertTrue(
            all("element_id" not in obj for obj in issue["related_objects"])
        )

    def test_lint_xml_related_objects_include_line_xml_path(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="http://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="label" type="text" topLeftX="100" topLeftY="100" width="200" height="80">
                  <content fontSize="24"><p>Crossed text</p></content>
                </shape>
                <line id="connector" startX="80" startY="130" endX="330" endY="130">
                  <border color="rgb(15, 23, 42)" width="2"/>
                </line>
              </data>
            </slide>
            """
        )

        issue = next(
            issue
            for issue in result["slides"][0]["issues"]
            if issue["code"] == "bbox_overlap" and issue["elements"][0] == "connector"
        )
        self.assertEqual(
            {
                obj["element_id"]: obj["xml_path"]
                for obj in issue["related_objects"]
            },
            {
                "connector": "slide[1]/data/line[1]",
                "label": "slide[1]/data/shape[1]",
            },
        )

    def test_lint_xml_reports_image_text_overlap_even_when_image_precedes_text_in_xml_order(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="http://www.larkoffice.com/sml/2.0"><data>
              <img id="image" src="token" topLeftX="120" topLeftY="120" width="120" height="60"/>
              <shape id="text" type="text" topLeftX="100" topLeftY="100" width="220" height="90">
                <content fontSize="28" lineSpacing="fixed:34" wrap="false"><p>Quarterly Plan</p></content>
              </shape>
            </data></slide>
            """
        )
        issue = next(issue for issue in result["slides"][0]["issues"] if issue["code"] == "image_covers_text")
        self.assertEqual(issue["elements"], ["image", "text"])
        self.assertIn("no longer overlaps the text glyph area", issue["hint"])
        self.assertEqual(result["summary"]["error_count"], 1)

    def test_lint_xml_exempts_full_canvas_background_image_behind_text(self) -> None:
        # A full-bleed image at the bottom of the z-order is the slide backdrop; text rendered on top of
        # it is never occluded (slides p9: bBo fills the whole canvas under the content). It must not be
        # reported as image_covers_text (Bucket B5 background-image false positive).
        result = xml_lint.lint_xml(
            """
            <presentation xmlns="http://www.larkoffice.com/sml/2.0" width="960" height="540">
              <slide xmlns="http://www.larkoffice.com/sml/2.0"><data>
                <img id="backdrop" src="token" topLeftX="0" topLeftY="0" width="960" height="540"/>
                <shape id="text" type="text" topLeftX="100" topLeftY="100" width="400" height="60">
                  <content fontSize="28"><p>On the backdrop</p></content>
                </shape>
              </data></slide>
            </presentation>
            """
        )
        codes = [
            issue for issue in result["slides"][0]["issues"]
            if issue["code"] == "image_covers_text" and "backdrop" in issue["elements"]
        ]
        self.assertEqual(codes, [])

    def test_lint_xml_reports_full_canvas_image_drawn_above_text(self) -> None:
        # The exemption is z-order aware: a full-canvas image drawn *after* (above) the text really does
        # cover it, so it must still be flagged. Guards the backdrop exemption from swallowing real
        # occlusions where the image is on top.
        result = xml_lint.lint_xml(
            """
            <presentation xmlns="http://www.larkoffice.com/sml/2.0" width="960" height="540">
              <slide xmlns="http://www.larkoffice.com/sml/2.0"><data>
                <shape id="text" type="text" topLeftX="100" topLeftY="100" width="400" height="60">
                  <content fontSize="28"><p>Under the cover</p></content>
                </shape>
                <img id="cover" src="token" topLeftX="0" topLeftY="0" width="960" height="540"/>
              </data></slide>
            </presentation>
            """
        )
        codes = [
            issue for issue in result["slides"][0]["issues"]
            if issue["code"] == "image_covers_text" and set(issue["elements"]) == {"cover", "text"}
        ]
        self.assertEqual(len(codes), 1)

    def test_lint_xml_exempts_partial_background_image_enclosing_text_glyphs(self) -> None:
        # A partial-bleed image (not full-canvas) drawn behind the text that encloses essentially all of
        # the glyph box is that run's local background -- the glyphs paint on top, so it cannot occlude
        # them (slides LuwIs0LQXlmCm0d2XTHcHxeCnfd: the 852x380 backdrop tucks fully under each card's
        # copy). It is below the full-canvas coverage ratio, so this exemption -- not the backdrop one --
        # is what must clear it.
        result = xml_lint.lint_xml(
            """
            <presentation xmlns="http://www.larkoffice.com/sml/2.0" width="960" height="540">
              <slide xmlns="http://www.larkoffice.com/sml/2.0"><data>
                <img id="localbg" src="token" topLeftX="54" topLeftY="116" width="852" height="380"/>
                <shape id="text" type="text" topLeftX="90" topLeftY="150" width="200" height="60">
                  <content fontSize="16"><p>On the local backdrop</p></content>
                </shape>
              </data></slide>
            </presentation>
            """
        )
        # The image is well under the full-canvas ratio, so guard that the exemption came from glyph
        # enclosure rather than the pre-existing backdrop rule.
        self.assertFalse(
            xml_lint.is_full_canvas_background_image(
                {"x": 54, "y": 116, "width": 852, "height": 380}, 960, 540
            )
        )
        codes = [
            issue for issue in result["slides"][0]["issues"]
            if issue["code"] == "image_covers_text" and "localbg" in issue["elements"]
        ]
        self.assertEqual(codes, [])

    def test_lint_xml_reports_partial_background_image_clipping_text_glyphs(self) -> None:
        # The enclosure exemption is near-total by design: an image behind the text that only clips part
        # of the glyph box (the run spills past the image edge) is a real occlusion and must still be
        # reported. Pins the no-false-negative guarantee against a too-loose enclosure threshold.
        result = xml_lint.lint_xml(
            """
            <presentation xmlns="http://www.larkoffice.com/sml/2.0" width="960" height="540">
              <slide xmlns="http://www.larkoffice.com/sml/2.0"><data>
                <img id="clipper" src="token" topLeftX="0" topLeftY="100" width="300" height="200"/>
                <shape id="text" type="text" topLeftX="100" topLeftY="150" width="400" height="60">
                  <content fontSize="28"><p>Half off the image</p></content>
                </shape>
              </data></slide>
            </presentation>
            """
        )
        codes = [
            issue for issue in result["slides"][0]["issues"]
            if issue["code"] == "image_covers_text" and set(issue["elements"]) == {"clipper", "text"}
        ]
        self.assertEqual(len(codes), 1)

    def test_stacking_helpers_agree_on_paint_order(self) -> None:
        lower = {"order": 1}
        upper = {"order": 3}
        same = {"order": 3}
        # is_drawn_behind and is_drawn_in_front_of are strict and mutually exclusive inverses.
        self.assertTrue(xml_lint.is_drawn_behind(lower, upper))
        self.assertFalse(xml_lint.is_drawn_in_front_of(lower, upper))
        self.assertTrue(xml_lint.is_drawn_in_front_of(upper, lower))
        self.assertFalse(xml_lint.is_drawn_behind(upper, lower))
        # Equal order is neither behind nor in front, so an equal-order sibling never occludes.
        self.assertFalse(xml_lint.is_drawn_behind(same, upper))
        self.assertFalse(xml_lint.is_drawn_in_front_of(same, upper))

    def test_lint_xml_reports_multiline_block_bottom_line_touching_run_below(self) -> None:
        # slides p7: a 4-line block ("文字碰撞 / 123abc / 12312!! / /11??@@a") sits directly above a
        # single-line run ("文字碰撞3"). The flat font_size*1.2 block-height estimate shrank the 4-line
        # glyph box ~25%, so its bottom line stopped short of the run below and the collision was missed.
        # The real line-spacing (1.5x) estimate keeps the bottom line touching, so this must flag.
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape width="399" height="108" topLeftX="218" topLeftY="203" type="text" id="block">
                  <content fontSize="16" fontFamily="思源黑体" color="rgba(31,35,41,1)">
                    <p>文字碰撞</p>
                    <p>123abc</p>
                    <p>12312!!</p>
                    <p>/11??@@a</p>
                  </content>
                </shape>
                <shape width="399" height="41" topLeftX="218" topLeftY="290" type="text" id="run">
                  <content fontSize="16" fontFamily="思源黑体" color="rgba(31,35,41,1)">
                    <p>文字碰撞3</p>
                  </content>
                </shape>
              </data>
            </slide>
            """
        )
        collisions = [
            issue for issue in result["slides"][0]["errors"]
            if issue["code"] == "bbox_overlap" and set(issue["elements"]) == {"block", "run"}
        ]
        self.assertEqual(len(collisions), 1)

    def test_lint_xml_reports_vertical_title_edge_overlapping_horizontal_subtitle(self) -> None:
        # slides p7: a tall CJK vertical title ("西/双/版/纳", one glyph per line) whose bottom glyph
        # overlaps a centered horizontal subtitle ("热带雨林的诗意") beneath it. With the flat font_size*1.2
        # block height the 4-glyph title was estimated ~25% too short, its bottom glyph stopped above the
        # subtitle, and the collision was missed. The real 1.5x line-spacing estimate keeps the bottom
        # glyph overlapping the subtitle, so this must flag.
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape width="140" height="260" topLeftX="580" topLeftY="73" type="text" id="title">
                  <content textType="title" fontSize="42" fontFamily="思源宋体" color="rgba(42,42,42,1)" bold="true" letterSpacing="12" textAlign="center" wrap="false">
                    <p>西</p>
                    <p>双</p>
                    <p>版</p>
                    <p>纳</p>
                  </content>
                </shape>
                <shape width="220" height="24" topLeftX="540" topLeftY="293" type="text" id="subtitle">
                  <content fontSize="13" fontFamily="思源宋体" color="rgba(120,110,95,1)" letterSpacing="2" textAlign="center" wrap="false">
                    <p>热带雨林的诗意</p>
                  </content>
                </shape>
              </data>
            </slide>
            """
        )
        collisions = [
            issue for issue in result["slides"][0]["errors"]
            if issue["code"] == "bbox_overlap" and set(issue["elements"]) == {"title", "subtitle"}
        ]
        self.assertEqual(len(collisions), 1)


class XmlTextOverlapLintDensityTest(unittest.TestCase):
    def test_lint_xml_sparse_container_related_objects_include_icon_xml_path(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="http://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="card" type="rect" topLeftX="60" topLeftY="120" width="400" height="300"/>
                <icon id="visual" iconType="iconpark/Base/setting.svg" topLeftX="80" topLeftY="140" width="32" height="32">
                  <fill><fillColor color="rgb(37, 99, 235)"/></fill>
                </icon>
              </data>
            </slide>
            """
        )

        issue = next(
            issue
            for issue in result["slides"][0]["issues"]
            if issue["code"] == "sparse_container_content"
        )
        self.assertEqual(
            {
                obj["element_id"]: obj["xml_path"]
                for obj in issue["related_objects"]
            },
            {
                "card": "slide[1]/data/shape[1]",
                "visual": "slide[1]/data/icon[1]",
            },
        )

    def test_lint_xml_blocks_blank_slide(self) -> None:
        result = xml_lint.lint_xml(
            """
            <presentation xmlns="https://www.larkoffice.com/sml/2.0" width="960" height="540">
              <slide id="content-slide">
                <data>
                  <shape id="title" type="text" topLeftX="60" topLeftY="60" width="400" height="50">
                    <content fontSize="28"><p>Investment report</p></content>
                  </shape>
                </data>
              </slide>
              <slide id="blank-slide">
                <style><fill><fillColor color="rgba(255, 255, 255, 1)"/></fill></style>
                <data/>
                <note><content/></note>
              </slide>
            </presentation>
            """
        )

        self.assertEqual(result["summary"]["slide_count"], 2)
        self.assertEqual(result["summary"]["warning_count"], 0)
        self.assertEqual(result["summary"]["error_count"], 1)
        self.assertEqual(result["summary"]["status"], "blocked")
        self.assertFalse(result["summary"]["release_ready"])
        self.assertEqual(result["slides"][0]["issues"], [])
        self.assertEqual(result["slides"][1]["element_count"], 0)
        issue = result["slides"][1]["errors"][0]
        self.assertEqual(issue["level"], "error")
        self.assertEqual(issue["code"], "blank_slide")
        self.assertEqual(issue["element_ids"], [])
        self.assertEqual(issue["rule"]["id"], "blank_slide")
        self.assertEqual(issue["measurement"]["visible_element_count"], 0)
        self.assertEqual(issue["related_objects"], [])

    def test_lint_xml_blocks_blank_slide_with_only_transparent_image(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <img id="ghost" src="token" topLeftX="60" topLeftY="60" width="200" height="200" alpha="0"/>
              </data>
            </slide>
            """
        )

        self.assertEqual(result["summary"]["error_count"], 1)
        issue = result["slides"][0]["errors"][0]
        self.assertEqual(issue["code"], "blank_slide")

    def test_lint_xml_warns_when_large_container_is_mostly_empty(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="trend-card" type="rect" topLeftX="500" topLeftY="135" width="410" height="370"/>
                <shape id="trend-title" type="text" topLeftX="515" topLeftY="147" width="380" height="28">
                  <content fontSize="15"><p>Core trends</p></content>
                </shape>
                <shape id="trend-copy" type="text" topLeftX="515" topLeftY="177" width="380" height="315">
                  <content fontSize="12"><p>First point</p><p>Second point</p><p>Third point</p></content>
                </shape>
              </data>
            </slide>
            """
        )

        issue = result["slides"][0]["issues"][0]
        self.assertEqual(issue["code"], "sparse_container_content")
        self.assertEqual(issue["target"]["container_id"], "trend-card")
        self.assertEqual(issue["target"], {
            "slide_number": 1,
            "container_id": "trend-card",
            "container_xml_path": "slide[1]/data/shape[1]",
            "container_type": "rect",
            "bbox": {"x": 500, "y": 135, "width": 410, "height": 370},
        })
        self.assertLess(issue["measurement"]["content_coverage_ratio"], 0.15)
        self.assertEqual(issue["rule"], {
            "name": "large_container_visible_content_coverage",
            "threshold": 0.15,
            "comparison": "content_coverage_ratio < threshold",
            "id": "sparse_container_content",
        })
        self.assertEqual(issue["measurement"]["container_area"], 151700)
        self.assertEqual(issue["measurement"]["content_coverage_ratio"], 0.036)
        self.assertEqual(issue["elements"], ["trend-card", "trend-title", "trend-copy"])
        self.assertEqual(issue["element_ids"], ["trend-card", "trend-title", "trend-copy"])
        self.assertEqual(
            [obj["element_id"] for obj in issue["related_objects"]],
            ["trend-card", "trend-title", "trend-copy"],
        )
        self.assertEqual(result["slides"][0]["status"], "needs_screenshot_review")
        self.assertEqual(result["slides"][0]["warnings"], result["slides"][0]["issues"])

    def test_lint_xml_uses_xml_path_in_anonymous_sparse_container_message(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape type="rect" topLeftX="500" topLeftY="135" width="410" height="370"/>
                <shape id="trend-title" type="text" topLeftX="515" topLeftY="147" width="380" height="28">
                  <content fontSize="15"><p>Core trends</p></content>
                </shape>
              </data>
            </slide>
            """
        )

        issue = next(
            issue
            for issue in result["slides"][0]["issues"]
            if issue["code"] == "sparse_container_content"
        )
        self.assertNotIn("container_id", issue["target"])
        self.assertEqual(
            issue["target"]["container_xml_path"],
            "slide[1]/data/shape[1]",
        )
        self.assertEqual(
            issue["message"],
            "large card slide[1]/data/shape[1] content coverage 1.0% is below 15.0%",
        )

    def test_lint_xml_warns_for_sparse_short_cards(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="card-1" type="rect" topLeftX="60" topLeftY="180" width="400" height="105"/>
                <shape id="text-1" type="text" topLeftX="80" topLeftY="220" width="360" height="30">
                  <content fontSize="14"><p>期待认识大家</p></content>
                </shape>
                <shape id="card-2" type="rect" topLeftX="490" topLeftY="180" width="400" height="105"/>
                <shape id="text-2" type="text" topLeftX="510" topLeftY="220" width="360" height="30">
                  <content fontSize="14"><p>化学一起讨论</p></content>
                </shape>
                <shape id="card-3" type="rect" topLeftX="60" topLeftY="310" width="400" height="105"/>
                <shape id="text-3" type="text" topLeftX="80" topLeftY="350" width="360" height="30">
                  <content fontSize="14"><p>吉他随时交流</p></content>
                </shape>
                <shape id="card-4" type="rect" topLeftX="490" topLeftY="310" width="400" height="105"/>
                <shape id="text-4" type="text" topLeftX="510" topLeftY="350" width="360" height="30">
                  <content fontSize="14"><p>共度美好四年</p></content>
                </shape>
              </data>
            </slide>
            """
        )

        container_issues = [
            issue for issue in result["slides"][0]["issues"] if issue["code"] == "sparse_container_content"
        ]
        self.assertEqual(
            [issue["target"]["container_id"] for issue in container_issues],
            ["card-1", "card-2", "card-3", "card-4"],
        )
        self.assertTrue(all(issue["target"]["bbox"]["height"] == 105 for issue in container_issues))
        self.assertTrue(all(issue["measurement"]["content_coverage_ratio"] < 0.15 for issue in container_issues))
        self.assertEqual(
            [issue["code"] for issue in result["slides"][0]["issues"]],
            [
                "sparse_container_content",
                "sparse_container_content",
                "sparse_container_content",
                "sparse_container_content",
                "sparse_slide_content",
            ],
        )

    def test_lint_xml_warns_when_whole_slide_has_too_little_effective_content(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="background" type="rect" topLeftX="0" topLeftY="0" width="960" height="540"/>
                <shape id="text-1" type="text" topLeftX="60" topLeftY="80" width="200" height="30">
                  <content fontSize="14"><p>One short line</p></content>
                </shape>
                <shape id="text-2" type="text" topLeftX="500" topLeftY="180" width="200" height="30">
                  <content fontSize="14"><p>Another line</p></content>
                </shape>
                <shape id="text-3" type="text" topLeftX="60" topLeftY="310" width="200" height="30">
                  <content fontSize="14"><p>Third line</p></content>
                </shape>
                <shape id="text-4" type="text" topLeftX="500" topLeftY="410" width="200" height="30">
                  <content fontSize="14"><p>Fourth line</p></content>
                </shape>
              </data>
            </slide>
            """
        )

        issues = [issue for issue in result["slides"][0]["issues"] if issue["code"] == "sparse_slide_content"]
        self.assertEqual(len(issues), 1)
        issue = issues[0]
        self.assertEqual(issue["target"]["bbox"], {"x": 0, "y": 0, "width": 960, "height": 540})
        self.assertEqual(issue["rule"]["threshold"], 0.035)
        self.assertLess(issue["measurement"]["content_coverage_ratio"], 0.035)
        self.assertEqual(issue["measurement"]["content_element_count"], 4)
        self.assertNotIn("background", issue["elements"])

    def test_lint_xml_ignores_isolated_short_layout_bar(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="summary-bar" type="rect" topLeftX="52" topLeftY="82" width="856" height="105"/>
                <shape id="summary" type="text" topLeftX="72" topLeftY="115" width="816" height="30">
                  <content fontSize="14"><p>One concise summary</p></content>
                </shape>
              </data>
            </slide>
            """
        )

        self.assertEqual(result["slides"][0]["issues"], [])

    def test_lint_xml_counts_rect_own_content_as_visible_content(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="load-card" type="rect" topLeftX="60" topLeftY="140" width="220" height="184">
                  <content fontSize="18">
                    <p>被吊物</p>
                    <p><span fontSize="36">32.0 t</span></p>
                    <p>钢结构模块</p>
                  </content>
                </shape>
              </data>
            </slide>
            """
        )

        self.assertEqual(result["slides"][0]["issues"], [])

    def test_lint_xml_reports_nonzero_coverage_for_rect_own_content_reproduction(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="load-card" type="rect" topLeftX="60" topLeftY="140" width="220" height="320">
                  <content fontSize="18">
                    <p>被吊物</p>
                    <p>32.0 t</p>
                    <p>钢结构模块</p>
                  </content>
                </shape>
              </data>
            </slide>
            """
        )

        issue = result["slides"][0]["issues"][0]
        self.assertGreater(issue["measurement"]["visible_content_area"], 0)
        self.assertEqual(issue["measurement"]["content_element_count"], 1)
        self.assertGreater(issue["measurement"]["content_coverage_ratio"], 0)

    def test_lint_xml_still_warns_for_sparse_rect_own_content(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="sparse-card" type="rect" topLeftX="60" topLeftY="140" width="220" height="184">
                  <content fontSize="12"><p>A</p></content>
                </shape>
              </data>
            </slide>
            """
        )

        issue = result["slides"][0]["issues"][0]
        self.assertEqual(issue["target"]["container_id"], "sparse-card")
        self.assertGreater(issue["measurement"]["visible_content_area"], 0)
        self.assertEqual(issue["measurement"]["content_element_count"], 1)
        self.assertEqual(issue["elements"], ["sparse-card"])

    def test_lint_xml_unions_rect_own_content_with_child_content(self) -> None:
        self_only = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="card" type="rect" topLeftX="60" topLeftY="140" width="220" height="184">
                  <content fontSize="12"><p>A</p></content>
                </shape>
              </data>
            </slide>
            """
        )
        with_overlapping_child = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="card" type="rect" topLeftX="60" topLeftY="140" width="220" height="184">
                  <content fontSize="12"><p>A</p></content>
                </shape>
                <shape id="child" type="text" topLeftX="60" topLeftY="140" width="220" height="184">
                  <content fontSize="12"><p>A</p></content>
                </shape>
              </data>
            </slide>
            """
        )

        self_issue = self_only["slides"][0]["issues"][0]
        mixed_issue = with_overlapping_child["slides"][0]["issues"][0]
        self.assertEqual(
            mixed_issue["measurement"]["visible_content_area"],
            self_issue["measurement"]["visible_content_area"],
        )
        self.assertEqual(mixed_issue["measurement"]["content_element_count"], 2)

    def test_extract_density_elements_reads_nested_font_size_from_rect_content(self) -> None:
        elements = xml_lint.extract_density_elements(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="card" type="rect" topLeftX="60" topLeftY="140" width="220" height="184">
                  <content fontSize="12"><p><span fontSize="36">32.0 t</span></p></content>
                </shape>
              </data>
            </slide>
            """
        )

        self.assertEqual(elements[0]["fontSize"], 36)

    def test_extract_density_elements_does_not_attach_following_text_to_self_closing_rect(self) -> None:
        elements = xml_lint.extract_density_elements(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="card" type="rect" topLeftX="60" topLeftY="140" width="220" height="184"/>
                <shape id="title" type="text" topLeftX="80" topLeftY="160" width="180" height="30">
                  <content fontSize="18"><p>Following title</p></content>
                </shape>
              </data>
            </slide>
            """
        )

        self.assertEqual(elements[0]["text"], "")
        self.assertEqual(elements[1]["text"], "Following title")

    def test_lint_xml_allows_container_with_large_visual_child(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="chart-card" type="rect" topLeftX="500" topLeftY="135" width="410" height="300"/>
                <chart id="chart" topLeftX="525" topLeftY="170" width="350" height="220">
                  <chartPlotArea><chartPlot type="line"/></chartPlotArea>
                  <chartData>
                    <dim1><chartField name="category" valueType="string">A</chartField></dim1>
                    <dim2><chartField name="value" valueType="number">1</chartField></dim2>
                  </chartData>
                </chart>
              </data>
            </slide>
            """
        )

        self.assertEqual(result["summary"]["warning_count"], 0)

    def test_lint_xml_does_not_let_transparent_visual_child_suppress_sparse_warning(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="title" type="text" topLeftX="40" topLeftY="40" width="300" height="40">
                  <content fontSize="20"><p>Section title</p></content>
                </shape>
                <shape id="chart-card" type="rect" topLeftX="500" topLeftY="135" width="410" height="300"/>
                <chart id="chart" topLeftX="525" topLeftY="170" width="350" height="220" alpha="0">
                  <chartPlotArea><chartPlot type="line"/></chartPlotArea>
                  <chartData>
                    <dim1><chartField name="category" valueType="string">A</chartField></dim1>
                    <dim2><chartField name="value" valueType="number">1</chartField></dim2>
                  </chartData>
                </chart>
              </data>
            </slide>
            """
        )

        issue = next(
            issue for issue in result["slides"][0]["issues"] if issue["code"] == "sparse_container_content"
        )
        self.assertEqual(issue["target"]["container_id"], "chart-card")

    def test_lint_xml_warns_for_small_empty_visual_placeholder_cards(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="letter-placeholder" type="rect" topLeftX="520" topLeftY="180" width="200" height="200"/>
                <shape id="letter" type="text" topLeftX="540" topLeftY="250" width="160" height="70">
                  <content fontSize="46"><p>Z</p></content>
                </shape>
                <shape id="empty-placeholder" type="rect" topLeftX="744" topLeftY="180" width="144" height="200"/>
              </data>
            </slide>
            """
        )

        issues = result["slides"][0]["issues"]
        self.assertEqual(
            [issue["target"]["container_id"] for issue in issues],
            ["letter-placeholder", "empty-placeholder"],
        )
        self.assertEqual(issues[1]["measurement"]["content_element_count"], 0)

    def test_lint_xml_applies_global_threshold_to_normal_text_card(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="card" type="rect" topLeftX="70" topLeftY="184" width="260" height="288"/>
                <shape id="title" type="text" topLeftX="90" topLeftY="215" width="220" height="30">
                  <content fontSize="18"><p>梦境与现实</p></content>
                </shape>
                <shape id="copy" type="text" topLeftX="90" topLeftY="330" width="220" height="70">
                  <content fontSize="13"><p>边界溶解，逻辑失效。观众被拽入潜意识的迷宫。</p></content>
                </shape>
              </data>
            </slide>
            """
        )

        issue = result["slides"][0]["issues"][0]
        self.assertEqual(issue["target"]["container_id"], "card")
        self.assertEqual(issue["rule"]["threshold"], 0.15)

    def test_lint_xml_allows_image_overlay_rect(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <img id="hero" topLeftX="560" topLeftY="0" width="400" height="540"/>
                <shape id="tint" type="rect" topLeftX="560" topLeftY="0" width="400" height="540"/>
              </data>
            </slide>
            """
        )

        self.assertEqual(result["summary"]["warning_count"], 0)

    def test_lint_xml_does_not_let_transparent_image_overlay_suppress_sparse_warning(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="title" type="text" topLeftX="40" topLeftY="40" width="300" height="40">
                  <content fontSize="20"><p>Section title</p></content>
                </shape>
                <shape id="card" type="rect" topLeftX="330" topLeftY="120" width="300" height="300"/>
                <img id="ghost-overlay" src="token" topLeftX="330" topLeftY="120" width="300" height="300" alpha="0"/>
              </data>
            </slide>
            """
        )

        issue = next(
            issue for issue in result["slides"][0]["issues"] if issue["code"] == "sparse_container_content"
        )
        self.assertEqual(issue["target"]["container_id"], "card")

    def test_lint_xml_allows_edge_spanning_layout_panel_and_nested_decoration(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="panel" type="rect" topLeftX="600" topLeftY="0" width="360" height="540"/>
                <shape id="decoration" type="rect" topLeftX="660" topLeftY="150" width="240" height="240"/>
              </data>
            </slide>
            """
        )

        self.assertEqual(result["summary"]["warning_count"], 0)

    def test_lint_xml_counts_icons_as_visible_content(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="card" type="rect" topLeftX="80" topLeftY="140" width="320" height="240"/>
                <icon id="visual" iconType="iconpark/Safe/shield.svg" topLeftX="100" topLeftY="160" width="180" height="180">
                  <fill><fillColor color="rgba(37, 99, 235, 1)"/></fill>
                </icon>
              </data>
            </slide>
            """
        )

        self.assertEqual(result["summary"]["warning_count"], 0)

    def test_lint_xml_does_not_count_transparent_icon_as_visible_content(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="title" type="text" topLeftX="40" topLeftY="40" width="300" height="40">
                  <content fontSize="20"><p>Section title</p></content>
                </shape>
                <shape id="card" type="rect" topLeftX="80" topLeftY="140" width="320" height="240"/>
                <icon id="visual" iconType="iconpark/Safe/shield.svg" topLeftX="100" topLeftY="160" width="180" height="180" alpha="0">
                  <fill><fillColor color="rgba(37, 99, 235, 1)"/></fill>
                </icon>
              </data>
            </slide>
            """
        )

        issue = next(
            issue for issue in result["slides"][0]["issues"] if issue["code"] == "sparse_container_content"
        )
        self.assertEqual(issue["target"]["container_id"], "card")
        self.assertEqual(issue["measurement"]["content_coverage_ratio"], 0)

    def test_lint_xml_warns_when_coverage_is_below_global_threshold(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="card" type="rect" topLeftX="80" topLeftY="140" width="200" height="200"/>
                <icon id="visual" iconType="iconpark/Safe/shield.svg" topLeftX="100" topLeftY="160" width="70" height="70">
                  <fill><fillColor color="rgba(37, 99, 235, 1)"/></fill>
                </icon>
              </data>
            </slide>
            """
        )

        issue = result["slides"][0]["issues"][0]
        self.assertEqual(issue["target"]["container_id"], "card")
        self.assertEqual(issue["measurement"]["content_coverage_ratio"], 0.122)
        self.assertEqual(issue["rule"]["threshold"], 0.15)

    def test_lint_xml_allows_quarter_coverage_under_lower_threshold(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="card" type="rect" topLeftX="80" topLeftY="140" width="200" height="200"/>
                <icon id="visual" iconType="iconpark/Safe/shield.svg" topLeftX="100" topLeftY="160" width="100" height="100">
                  <fill><fillColor color="rgba(37, 99, 235, 1)"/></fill>
                </icon>
              </data>
            </slide>
            """
        )

        self.assertEqual(result["slides"][0]["issues"], [])

    def test_lint_xml_reports_large_metric_frame_crossing_card_border(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="metric-card" type="rect" topLeftX="80" topLeftY="140" width="360" height="300"/>
                <shape id="metric" type="text" topLeftX="104" topLeftY="190" width="340" height="90">
                  <content fontSize="12"><p><strong><span fontSize="62">400</span></strong>+ 项</p></content>
                </shape>
              </data>
            </slide>
            """
        )

        overflow = [
            issue for issue in result["slides"][0]["errors"]
            if issue["code"] == "text_overflows_container"
            and issue["elements"] == ["metric", "metric-card"]
        ]
        self.assertEqual(len(overflow), 1)
        self.assertEqual(overflow[0]["overflow"]["right"], 4)

    def test_lint_xml_does_not_report_blank_slide_for_embed_only_content(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="http://www.larkoffice.com/sml/2.0">
              <data>
                <embed id="emb" topLeftX="280" topLeftY="130" width="400" height="280">
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 280">
                    <circle cx="200" cy="140" r="100" fill="#2563EB"/>
                  </svg>
                </embed>
              </data>
            </slide>
            """
        )

        self.assertEqual(result["summary"]["error_count"], 0)
        codes = [issue["code"] for issue in result["slides"][0]["issues"]]
        self.assertNotIn("blank_slide", codes)

    def test_lint_xml_does_not_report_blank_slide_for_line_only_content(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <line id="l1" startX="100" startY="100" endX="800" endY="100"><border/></line>
                <line id="l2" startX="100" startY="200" endX="800" endY="200"><border/></line>
                <line id="l3" startX="100" startY="300" endX="800" endY="300"><border/></line>
                <line id="l4" startX="100" startY="400" endX="800" endY="400"><border/></line>
              </data>
            </slide>
            """
        )

        self.assertEqual(result["summary"]["error_count"], 0)
        codes = [issue["code"] for issue in result["slides"][0]["issues"]]
        self.assertNotIn("blank_slide", codes)

    def test_lint_xml_reports_bbox_overlap_measurement_from_decision_time_visual_bbox(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="left" type="text" topLeftX="80" topLeftY="80" width="300" height="60">
                  <content fontSize="14"><p>overlap text <span fontSize="96">big</span></p></content>
                </shape>
                <shape id="right" type="text" topLeftX="80" topLeftY="80" width="300" height="80">
                  <content fontSize="14"><p>other overlap text</p></content>
                </shape>
              </data>
            </slide>
            """
        )

        issue = result["slides"][0]["issues"][0]
        self.assertEqual(issue["code"], "bbox_overlap")
        # Must match the visual bbox that should_flag_overlap actually decided with (fontSize=14
        # from extract_elements), not the fontSize=96 max-descendant value that
        # extract_density_elements computes for the same "left" element id.
        self.assertEqual(issue["measurement"]["intersection_width"], 109.2)
        self.assertEqual(issue["measurement"]["intersection_height"], 6.8)
        self.assertEqual(issue["measurement"]["intersection_area"], 742.56)

    def test_has_similar_short_card_peer_excludes_the_element_itself(self) -> None:
        card_a = {"kind": "shape", "type": "rect", "x": 0, "y": 0, "width": 300, "height": 100}
        card_b = {"kind": "shape", "type": "rect", "x": 400, "y": 0, "width": 300, "height": 100}
        card_c = {"kind": "shape", "type": "rect", "x": 0, "y": 200, "width": 300, "height": 100}

        self.assertFalse(
            xml_lint.has_similar_short_card_peer(card_a, [card_a, card_b])
        )
        self.assertTrue(
            xml_lint.has_similar_short_card_peer(card_a, [card_a, card_b, card_c])
        )

    def test_lint_xml_reports_schema_version_2_for_sparse_issues(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="card" type="rect" topLeftX="60" topLeftY="140" width="220" height="184"/>
              </data>
            </slide>
            """
        )

        issue = next(
            issue for issue in result["slides"][0]["issues"] if issue["code"] == "sparse_container_content"
        )
        self.assertEqual(issue["schema_version"], "2.0")

    def test_lint_xml_does_not_report_blank_slide_for_textless_decorative_shapes(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="deco1" type="ellipse" topLeftX="60" topLeftY="60" width="300" height="300">
                  <fill><fillColor color="rgba(37, 99, 235, 1)"/></fill>
                </shape>
                <shape id="deco2" type="triangle" topLeftX="500" topLeftY="200" width="200" height="200">
                  <fill><fillColor color="rgba(220, 38, 38, 1)"/></fill>
                </shape>
              </data>
            </slide>
            """
        )

        self.assertEqual(result["summary"]["error_count"], 0)
        codes = [issue["code"] for issue in result["slides"][0]["issues"]]
        self.assertNotIn("blank_slide", codes)

    def test_lint_xml_still_warns_for_sparse_slide_content_despite_full_bleed_background(self) -> None:
        # A plain textless shape now counts as "not blank" (see the test above), but a
        # full-bleed background rect must still NOT count toward sparse_slide_content's
        # meaningful-content coverage ratio -- otherwise every slide with a background would
        # trivially "pass" that density check.
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="background" type="rect" topLeftX="0" topLeftY="0" width="960" height="540"/>
                <shape id="text-1" type="text" topLeftX="60" topLeftY="80" width="200" height="30">
                  <content fontSize="14"><p>One short line</p></content>
                </shape>
                <shape id="text-2" type="text" topLeftX="500" topLeftY="180" width="200" height="30">
                  <content fontSize="14"><p>Another line</p></content>
                </shape>
                <shape id="text-3" type="text" topLeftX="60" topLeftY="310" width="200" height="30">
                  <content fontSize="14"><p>Third line</p></content>
                </shape>
                <shape id="text-4" type="text" topLeftX="500" topLeftY="410" width="200" height="30">
                  <content fontSize="14"><p>Fourth line</p></content>
                </shape>
              </data>
            </slide>
            """
        )

        codes = [issue["code"] for issue in result["slides"][0]["issues"]]
        self.assertIn("sparse_slide_content", codes)

    def test_lint_xml_accepts_whitespace_around_attribute_equals_sign(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="visible" type="text" topLeftX = "80" topLeftY = "80" width = "300" height = "60">
                  <content><p>hello</p></content>
                </shape>
              </data>
            </slide>
            """
        )

        self.assertEqual(result["slides"][0]["element_count"], 1)
        codes = [issue["code"] for issue in result["slides"][0]["issues"]]
        self.assertNotIn("blank_slide", codes)

    def test_lint_xml_reports_blank_slide_for_full_canvas_background_only(self) -> None:
        result = xml_lint.lint_xml(
            """
            <slide xmlns="https://www.larkoffice.com/sml/2.0">
              <data>
                <shape id="background" type="rect" topLeftX="0" topLeftY="0" width="960" height="540">
                  <fill><fillColor color="rgba(240, 235, 220, 1)"/></fill>
                </shape>
              </data>
            </slide>
            """
        )

        codes = [issue["code"] for issue in result["slides"][0]["issues"]]
        self.assertIn("blank_slide", codes)

    def test_has_similar_short_card_peer_ignores_invisible_peers(self) -> None:
        visible_card = {"kind": "shape", "type": "rect", "x": 0, "y": 0, "width": 300, "height": 100}
        ghost_1 = {
            "kind": "shape", "type": "rect", "x": 400, "y": 0, "width": 300, "height": 100, "alpha": 0,
        }
        ghost_2 = {
            "kind": "shape", "type": "rect", "x": 800, "y": 0, "width": 300, "height": 100, "alpha": 0,
        }

        self.assertFalse(
            xml_lint.has_similar_short_card_peer(
                visible_card, [visible_card, ghost_1, ghost_2]
            )
        )


SML_NAMESPACE = "https://www.larkoffice.com/sml/2.0"


class SxsdSyntaxTestCase(unittest.TestCase):
    def validate(self, xml: str) -> list[dict[str, object]]:
        result = xml_lint.lint_xml(xml)
        return [
            *result.get("issues", []),
            *(issue for slide in result["slides"] for issue in slide["issues"]),
        ]

    def assert_issue(
        self,
        issues: list[dict[str, object]],
        code: str,
        *,
        path: str | None = None,
        attr: str | None = None,
    ) -> dict[str, object]:
        for issue in issues:
            if issue.get("code") != code:
                continue
            if path is not None and issue.get("path") != path:
                continue
            if attr is not None and issue.get("attr") != attr:
                continue
            return issue
        self.fail(f"missing issue code={code!r} path={path!r} attr={attr!r}: {issues!r}")

    def assert_no_issue(self, issues: list[dict[str, object]], code: str) -> None:
        self.assertNotIn(code, [issue.get("code") for issue in issues])


class SxsdSyntaxAttributeTest(SxsdSyntaxTestCase):

    def test_xsd_pattern_translation_only_expands_whitespace_classes(self) -> None:
        self.assertEqual(
            sxsd_validator.python_pattern_for_xsd(r"\s+\S+\w+\d+"),
            "[ \\t\\n\\r]+[^ \\t\\n\\r]+\\w+\\d+",
        )

    def test_href_domain_pattern_does_not_use_backtracking_regex(self) -> None:
        pattern = r"[\w.-]+[.:]\S*"
        adversarial_value = ("a." * 20_000) + " "
        original_fullmatch = sxsd_validator.re.fullmatch
        translated_pattern = sxsd_validator.python_pattern_for_xsd(pattern)

        def reject_unsafe_pattern(candidate: str, value: str):
            if candidate == translated_pattern:
                raise AssertionError("href domain pattern must not use re.fullmatch")
            return original_fullmatch(candidate, value)

        with mock.patch.object(sxsd_validator.re, "fullmatch", side_effect=reject_unsafe_pattern):
            self.assertFalse(sxsd_validator.xsd_pattern_matches(pattern, adversarial_value))

    def test_href_domain_pattern_keeps_xsd_matching_behavior(self) -> None:
        pattern = r"[\w.-]+[.:]\S*"
        reference_pattern = sxsd_validator.re.compile(
            sxsd_validator.python_pattern_for_xsd(pattern)
        )

        for length in range(5):
            for characters in itertools.product("a.:-/ ©", repeat=length):
                value = "".join(characters)
                with self.subTest(value=value):
                    self.assertEqual(
                        sxsd_validator.xsd_pattern_matches(pattern, value),
                        reference_pattern.fullmatch(value) is not None,
                    )

    def test_accepts_valid_shape_attributes(self) -> None:
        issues = self.validate(
            f"""
            <slide xmlns="{SML_NAMESPACE}">
              <data>
                <shape type="text" topLeftX="10" topLeftY="20" width="300" height="80">
                  <content textType="body"><p>Valid</p></content>
                </shape>
              </data>
            </slide>
            """
        )

        self.assertEqual(issues, [])

    def test_reports_missing_required_shape_attribute(self) -> None:
        issues = self.validate(
            f"""
            <slide xmlns="{SML_NAMESPACE}">
              <data><shape type="text" topLeftX="10" topLeftY="20" width="300"/></data>
            </slide>
            """
        )

        issue = self.assert_issue(
            issues,
            "sxsd_missing_required_attr",
            path="slide/data/shape",
            attr="height",
        )
        self.assertEqual(issue["expected"], "required attribute of type PositiveSize")
        self.assertIsNone(issue["actual"])

    def test_reports_invalid_scalar_value(self) -> None:
        issues = self.validate(
            f"""
            <slide xmlns="{SML_NAMESPACE}">
              <data>
                <shape type="text" topLeftX="NaN" topLeftY="20" width="300" height="80"/>
              </data>
            </slide>
            """
        )

        issue = self.assert_issue(issues, "sxsd_invalid_scalar", attr="topLeftX")
        self.assertEqual(issue["actual"], "NaN")

    def test_rejects_python_only_numeric_separator(self) -> None:
        issues = self.validate(
            f"""
            <slide xmlns="{SML_NAMESPACE}">
              <data>
                <shape type="rect" topLeftX="1_0" topLeftY="20" width="300" height="80"/>
              </data>
            </slide>
            """
        )

        self.assert_issue(issues, "sxsd_invalid_scalar", attr="topLeftX")

    def test_accepts_xsd_double_lexical_forms(self) -> None:
        for top_left_x in ("10", "-0.5", ".5", "1.", "1e2"):
            with self.subTest(top_left_x=top_left_x):
                issues = self.validate(
                    f"""
                    <slide xmlns="{SML_NAMESPACE}">
                      <data>
                        <shape type="rect" topLeftX="{top_left_x}" topLeftY="20" width="300" height="80"/>
                      </data>
                    </slide>
                    """
                )

                self.assertEqual(issues, [])

    def test_accepts_bullet_char_length_boundaries(self) -> None:
        for bullet_char in ("A", "12345678"):
            with self.subTest(bullet_char=bullet_char):
                issues = self.validate(
                    f"""
                    <slide xmlns="{SML_NAMESPACE}">
                      <data>
                        <shape type="text" topLeftX="10" topLeftY="20" width="300" height="80">
                          <content bulletChar="{bullet_char}"><p>Text</p></content>
                        </shape>
                      </data>
                    </slide>
                    """
                )

                self.assertEqual(issues, [])

    def test_rejects_bullet_char_outside_length_boundaries(self) -> None:
        for bullet_char in ("", "123456789"):
            with self.subTest(bullet_char=bullet_char):
                issues = self.validate(
                    f"""
                    <slide xmlns="{SML_NAMESPACE}">
                      <data>
                        <shape type="text" topLeftX="10" topLeftY="20" width="300" height="80">
                          <content bulletChar="{bullet_char}"><p>Text</p></content>
                        </shape>
                      </data>
                    </slide>
                    """
                )

                self.assert_issue(issues, "sxsd_value_out_of_range", attr="bulletChar")

    def test_rejects_zero_size_that_violates_xsd(self) -> None:
        issues = self.validate(
            f"""
            <slide xmlns="{SML_NAMESPACE}">
              <data>
                <shape type="text" topLeftX="10" topLeftY="20" width="0" height="80"/>
              </data>
            </slide>
            """
        )

        self.assert_issue(issues, "sxsd_value_out_of_range", attr="width")

    def test_reports_negative_size_rejected_by_xsd(self) -> None:
        issues = self.validate(
            f"""
            <slide xmlns="{SML_NAMESPACE}">
              <data>
                <shape type="text" topLeftX="10" topLeftY="20" width="-1" height="80"/>
              </data>
            </slide>
            """
        )

        self.assert_issue(issues, "sxsd_value_out_of_range", attr="width")

    def test_rejects_shape_enum_that_violates_xsd(self) -> None:
        issues = self.validate(
            f"""
            <slide xmlns="{SML_NAMESPACE}">
              <data>
                <shape type="not-a-shape" topLeftX="10" topLeftY="20" width="300" height="80"/>
              </data>
            </slide>
            """
        )

        issue = self.assert_issue(issues, "sxsd_invalid_enum", attr="type")
        self.assertLess(len(str(issue["message"])), 300)
        self.assertEqual(issue["actual"], "not-a-shape")

    def test_rejects_rotation_upper_bound_that_violates_xsd(self) -> None:
        issues = self.validate(
            f"""
            <slide xmlns="{SML_NAMESPACE}">
              <data>
                <shape type="text" topLeftX="10" topLeftY="20" width="300" height="80" rotation="360"/>
              </data>
            </slide>
            """
        )

        self.assert_issue(issues, "sxsd_value_out_of_range", attr="rotation")

    def test_rejects_fill_color_that_violates_xsd(self) -> None:
        issues = self.validate(
            f"""
            <slide xmlns="{SML_NAMESPACE}">
              <style><fill><fillColor color="red"/></fill></style>
              <data/>
            </slide>
            """
        )

        self.assert_issue(issues, "sxsd_pattern_mismatch", attr="color")

    def test_reports_missing_required_image_src(self) -> None:
        issues = self.validate(
            f"""
            <slide xmlns="{SML_NAMESPACE}">
              <data><img topLeftX="10" topLeftY="20" width="300" height="80"/></data>
            </slide>
            """
        )

        self.assert_issue(issues, "sxsd_missing_required_attr", attr="src")

    def test_accepts_inline_attribute_simple_type(self) -> None:
        issues = self.validate(
            f"""
            <slide xmlns="{SML_NAMESPACE}">
              <data>
                <shape type="text" topLeftX="10" topLeftY="20" width="300" height="80">
                  <content><p><a href="https://example.com">Link</a></p></content>
                </shape>
              </data>
            </slide>
            """
        )

        self.assertEqual(issues, [])

    def test_reports_inline_attribute_pattern_mismatch(self) -> None:
        issues = self.validate(
            f"""
            <slide xmlns="{SML_NAMESPACE}">
              <data>
                <shape type="text" topLeftX="10" topLeftY="20" width="300" height="80">
                  <content><p><a href="not a uri">Link</a></p></content>
                </shape>
              </data>
            </slide>
            """
        )

        self.assert_issue(issues, "sxsd_pattern_mismatch", attr="href")

    def test_accepts_values_matching_inline_union_members(self) -> None:
        for bullet_size in ("25%", "100%", "400%", "6", "14", "400"):
            with self.subTest(bullet_size=bullet_size):
                issues = self.validate(
                    f"""
                    <slide xmlns="{SML_NAMESPACE}">
                      <data>
                        <shape type="text" topLeftX="10" topLeftY="20" width="300" height="80">
                          <content bulletSize="{bullet_size}"><p>Text</p></content>
                        </shape>
                      </data>
                    </slide>
                    """
                )

                self.assertEqual(issues, [])

    def test_rejects_values_outside_inline_union_members(self) -> None:
        for bullet_size in ("24%", "401%", "5", "401", "abc"):
            with self.subTest(bullet_size=bullet_size):
                issues = self.validate(
                    f"""
                    <slide xmlns="{SML_NAMESPACE}">
                      <data>
                        <shape type="text" topLeftX="10" topLeftY="20" width="300" height="80">
                          <content bulletSize="{bullet_size}"><p>Text</p></content>
                        </shape>
                      </data>
                    </slide>
                    """
                )

                self.assert_issue(issues, "sxsd_pattern_mismatch", attr="bulletSize")

    def test_rejects_symbol_outside_python_word_semantics_in_href(self) -> None:
        issues = self.validate(
            f"""
            <slide xmlns="{SML_NAMESPACE}">
              <data>
                <shape type="text" topLeftX="10" topLeftY="20" width="300" height="80">
                  <content><p><a href="©:resource">Link</a></p></content>
                </shape>
              </data>
            </slide>
            """
        )

        self.assert_issue(issues, "sxsd_pattern_mismatch", attr="href")

    def test_accepts_common_email_href_with_python_regex_semantics(self) -> None:
        issues = self.validate(
            f"""
            <slide xmlns="{SML_NAMESPACE}">
              <data>
                <shape type="text" topLeftX="10" topLeftY="20" width="300" height="80">
                  <content><p><a href="mailto:user@example.com">Email</a></p></content>
                </shape>
              </data>
            </slide>
            """
        )

        self.assertEqual(issues, [])

    def test_accepts_common_gradient_with_python_regex_semantics(self) -> None:
        issues = self.validate(
            f"""
            <slide xmlns="{SML_NAMESPACE}">
              <style>
                <fill>
                  <fillColor color="linear-gradient(90deg, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%)"/>
                </fill>
              </style>
              <data>
                <shape type="text" topLeftX="10" topLeftY="20" width="300" height="80">
                  <content><p>Gradient</p></content>
                </shape>
              </data>
            </slide>
            """
        )

        self.assertEqual(issues, [])

    def test_rejects_non_xsd_whitespace_in_color_pattern(self) -> None:
        issues = self.validate(
            f"""
            <slide xmlns="{SML_NAMESPACE}">
              <style><fill><fillColor color="rgb(1,\u00a02,3)"/></fill></style>
              <data/>
            </slide>
            """
        )

        self.assert_issue(issues, "sxsd_pattern_mismatch", attr="color")

class SxsdSyntaxStructureTest(SxsdSyntaxTestCase):
    def test_accepts_nested_content_in_referenced_rich_text_shadow(self) -> None:
        issues = self.validate(
            f"""
            <slide xmlns="{SML_NAMESPACE}">
              <data>
                <shape type="text" topLeftX="10" topLeftY="20" width="300" height="80">
                  <content>
                    <p><span><shadow color="rgba(0, 0, 0, 1)"><strong>Text</strong></shadow></span></p>
                  </content>
                </shape>
              </data>
            </slide>
            """
        )

        self.assertEqual(issues, [])

    def test_keeps_shape_effect_shadow_as_childless_local_type(self) -> None:
        issues = self.validate(
            f"""
            <slide xmlns="{SML_NAMESPACE}">
              <data>
                <shape type="rect" topLeftX="10" topLeftY="20" width="300" height="80">
                  <shadow><strong>Not rich text</strong></shadow>
                </shape>
              </data>
            </slide>
            """
        )

        self.assert_issue(
            issues,
            "sxsd_unexpected_child",
            path="slide/data/shape/shadow/strong",
        )

    def test_accepts_standalone_slide_fragment_without_namespace(self) -> None:
        issues = self.validate(
            '<slide><data><shape type="text" topLeftX="10" topLeftY="20" width="300" height="80">'
            '<content><p>Text</p></content></shape></data></slide>'
        )

        self.assertEqual(issues, [])

    def test_rejects_presentation_without_namespace(self) -> None:
        issues = self.validate(
            '<presentation width="960" height="540"><slide/></presentation>'
        )

        self.assert_issue(issues, "sxsd_invalid_namespace", path="presentation")

    def test_rejects_wrong_namespace_that_violates_xsd(self) -> None:
        issues = self.validate('<slide xmlns="https://example.com/not-sml"><data/></slide>')

        self.assert_issue(issues, "sxsd_invalid_namespace", path="slide")

    def test_rejects_descendant_outside_document_namespace(self) -> None:
        issues = self.validate(
            f"""
            <slide xmlns="{SML_NAMESPACE}">
              <data xmlns="">
                <shape xmlns="{SML_NAMESPACE}" type="rect" topLeftX="10" topLeftY="20" width="300" height="80"/>
              </data>
            </slide>
            """
        )

        self.assert_issue(issues, "sxsd_invalid_namespace", path="slide/data")

    def test_rejects_unexpected_child_that_violates_xsd(self) -> None:
        issues = self.validate(
            f"""
            <slide xmlns="{SML_NAMESPACE}">
              <shape type="text" topLeftX="10" topLeftY="20" width="300" height="80"/>
            </slide>
            """
        )

        self.assert_issue(issues, "sxsd_unexpected_child", path="slide/shape")

    def test_rejects_child_order_that_violates_xsd(self) -> None:
        issues = self.validate(
            f"""
            <presentation xmlns="{SML_NAMESPACE}" width="1920" height="1080">
              <slide/>
              <title>Late title</title>
            </presentation>
            """
        )

        self.assert_issue(issues, "sxsd_invalid_child_order", path="presentation/title")

    def test_enforces_presentation_slide_minimum_from_xsd(self) -> None:
        issues = self.validate(
            f'<presentation xmlns="{SML_NAMESPACE}" width="1920" height="1080"/>'
        )

        self.assert_issue(issues, "sxsd_missing_required_child", path="presentation")

    def test_enforces_presentation_slide_maximum_from_xsd(self) -> None:
        slides = "".join("<slide/>" for _ in range(101))
        issues = self.validate(
            f'<presentation xmlns="{SML_NAMESPACE}" width="1920" height="1080">{slides}</presentation>'
        )

        self.assert_issue(issues, "sxsd_too_many_children", path="presentation/slide")

    def test_rejects_multiple_choice_children_that_violate_xsd(self) -> None:
        issues = self.validate(
            f"""
            <slide xmlns="{SML_NAMESPACE}">
              <style>
                <fill><fillColor/><fillImg src="token"/></fill>
              </style>
            </slide>
            """
        )

        self.assert_issue(issues, "sxsd_too_many_children", path="slide/style/fill")

    def test_rejects_line_without_required_border_from_xsd(self) -> None:
        issues = self.validate(
            f"""
            <slide xmlns="{SML_NAMESPACE}">
              <data><line startX="0" startY="0" endX="100" endY="100"/></data>
            </slide>
            """
        )

        self.assert_issue(issues, "sxsd_missing_required_child", path="slide/data/line")

    def test_reports_missing_required_chart_structure(self) -> None:
        issues = self.validate(
            f"""
            <slide xmlns="{SML_NAMESPACE}">
              <data><chart topLeftX="0" topLeftY="0" width="300" height="200"/></data>
            </slide>
            """
        )

        self.assert_issue(issues, "sxsd_missing_required_child", path="slide/data/chart")

    def test_reports_missing_required_nested_sequence_child(self) -> None:
        issues = self.validate(
            f"""
            <slide xmlns="{SML_NAMESPACE}">
              <data><table topLeftX="0" topLeftY="0"><tr/></table></data>
            </slide>
            """
        )

        issue = self.assert_issue(issues, "sxsd_missing_required_child", path="slide/data/table/tr")
        self.assertEqual(issue["expected"], "td (at least 1)")


class SxsdSchemaModelTest(unittest.TestCase):
    def test_reports_unsupported_xsd_pattern_without_crashing(self) -> None:
        schema = rf"""
        <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
                   xmlns:sml="{SML_NAMESPACE}"
                   targetNamespace="{SML_NAMESPACE}"
                   elementFormDefault="qualified">
          <xs:simpleType name="UnsupportedPatternType">
            <xs:union>
              <xs:simpleType>
                <xs:restriction base="xs:string"><xs:pattern value="[\S]"/></xs:restriction>
              </xs:simpleType>
              <xs:simpleType>
                <xs:restriction base="xs:string"><xs:pattern value="z+"/></xs:restriction>
              </xs:simpleType>
            </xs:union>
          </xs:simpleType>
          <xs:complexType name="SlideType">
            <xs:attribute name="value" type="sml:UnsupportedPatternType"/>
          </xs:complexType>
        </xs:schema>
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            schema_path = Path(temp_dir) / "schema.xsd"
            schema_path.write_text(schema, encoding="utf-8")
            try:
                issues = sxsd_validator.validate_sxsd(
                    ET.fromstring(f'<slide xmlns="{SML_NAMESPACE}" value="A"/>'),
                    schema_path,
                )
            except (ValueError, sxsd_validator.re.error) as error:
                self.fail(f"SXSD pattern capability errors must be reported, not raised: {error}")

        self.assertEqual([issue["code"] for issue in issues], ["sxsd_unsupported_pattern"])
        self.assertEqual(issues[0]["attr"], "value")
        self.assertIn("pattern interpreter", str(issues[0]["hint"]).lower())

    def test_standalone_slide_uses_slide_type_without_global_element(self) -> None:
        schema = f"""
        <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
                   xmlns:sml="{SML_NAMESPACE}"
                   targetNamespace="{SML_NAMESPACE}"
                   elementFormDefault="qualified">
          <xs:complexType name="SlideType"><xs:sequence/></xs:complexType>
          <xs:complexType name="PresentationType">
            <xs:sequence><xs:element name="slide" type="sml:SlideType"/></xs:sequence>
          </xs:complexType>
          <xs:element name="presentation" type="sml:PresentationType"/>
        </xs:schema>
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            schema_path = Path(temp_dir) / "schema.xsd"
            schema_path.write_text(schema, encoding="utf-8")
            issues = sxsd_validator.validate_sxsd(
                ET.fromstring(f'<slide xmlns="{SML_NAMESPACE}"/>'),
                schema_path,
            )

        self.assertEqual(issues, [])

    def test_standalone_slide_requires_slide_type_in_xsd(self) -> None:
        schema = f"""
        <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
                   xmlns:sml="{SML_NAMESPACE}"
                   targetNamespace="{SML_NAMESPACE}"
                   elementFormDefault="qualified">
          <xs:complexType name="PresentationType"><xs:sequence/></xs:complexType>
          <xs:element name="presentation" type="sml:PresentationType"/>
        </xs:schema>
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            schema_path = Path(temp_dir) / "schema.xsd"
            schema_path.write_text(schema, encoding="utf-8")
            issues = sxsd_validator.validate_sxsd(
                ET.fromstring(f'<slide xmlns="{SML_NAMESPACE}"/>'),
                schema_path,
            )

        self.assertEqual([issue["code"] for issue in issues], ["sxsd_unexpected_root"])


if __name__ == "__main__":
    unittest.main()
