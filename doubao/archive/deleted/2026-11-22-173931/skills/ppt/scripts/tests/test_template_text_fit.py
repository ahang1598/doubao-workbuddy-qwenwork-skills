import hashlib
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from lxml import etree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.template.template_text_fit import prepare_text_containers

SCRIPT = Path(__file__).resolve().parents[1] / "template" / "template_text_fit.py"
NS = "https://www.larkoffice.com/sml/2.0"

# Geometry, labels and text style are the verified L2/pbv page-6 defect.
# The surrounding comment, rich text and notes exercise source preservation.
PAGE = f'''<?xml version="1.0" encoding="UTF-8"?>
<slide xmlns="{NS}" id="pbv" width="960" height="540">
  <!-- keep authoring context -->
  <data>
    <shape id="bcq" type="ellipse" topLeftX="164" topLeftY="202" width="56" height="56"><content fontSize="15" fontFamily="思源黑体" bold="true"><p>开放</p><p>台账</p></content></shape>
    <shape id="bcU" type="ellipse" topLeftX="452" topLeftY="202" width="56" height="56"><content fontSize="15" fontFamily="思源黑体" bold="true"><p>联合</p><p>攻关</p></content></shape>
    <shape id="bci" type="ellipse" topLeftX="740" topLeftY="202" width="56" height="56"><content fontSize="15" fontFamily="思源黑体" bold="true"><p>中试</p><p>验证</p></content></shape>
    <shape id="other" type="text" topLeftX="50" topLeftY="20" width="800" height="80"><content fontSize="20" textType="title"><p>原文 <span color="#008000" fontSize="23">完整</span> &amp; 尾文</p></content></shape>
    <line id="link" startShapeId="bcq" endShapeId="bcU" startX="220" startY="230" endX="452" endY="230"/>
  </data>
  <note><content><p>保留讲稿 &amp; 来源。</p></content></note>
</slide>'''


def node(xml, shape_id):
    root = ET.fromstring(xml.encode())
    return root.xpath("//*[local-name()='shape' and @id=$id]", id=shape_id)[0]


class TemplateTextFitTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.source = Path(self.tmp.name) / "page-06.xml"
        self.source.write_text(PAGE, encoding="utf-8")

    def prepare(self, xml=PAGE, ids=("bcq",), **kwargs):
        self.source.write_text(xml, encoding="utf-8")
        return prepare_text_containers(self.source, ids, **kwargs)

    def test_verified_ellipse_padding_repair_keeps_full_authoring_copy(self):
        before = self.source.read_bytes()
        result = prepare_text_containers(self.source, ["bcq", "bcU", "bci"])
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "prepared")
        self.assertEqual(self.source.read_bytes(), before)
        self.assertEqual(result["source_sha256"], hashlib.sha256(before).hexdigest())
        self.assertEqual(result["selected_ids"], ["bcq", "bcU", "bci"])
        expected = PAGE.replace('bold="true">', 'bold="true" paddingTop="0" paddingRight="0" paddingBottom="0" paddingLeft="0">')
        self.assertEqual(result["xml"], expected)
        for row in result["containers"]:
            self.assertEqual(row["status"], "padding_reduced")
            self.assertEqual(set(row["effective_padding_before"].values()), {5})
            self.assertAlmostEqual(row["before"]["available_bbox"]["width"], 56 / math.sqrt(2) - 10)
            self.assertEqual(row["before"]["line_count"], 4)
            self.assertFalse(row["before"]["fits"])
            self.assertEqual(row["after"]["line_count"], 2)
            self.assertAlmostEqual(row["after"]["estimated_height"], 37.5)
            self.assertTrue(row["after"]["fits"])
        self.assertFalse(result["measurement"]["pixel_exact"])
        self.assertIn("heuristic", result["measurement"]["method"])
        self.assertIn("not loaded", result["measurement"]["font_source"])
        self.assertTrue(result["measurement"]["requires_rendered_review"])

    def test_unselected_ellipse_and_rich_runs_are_unchanged(self):
        result = self.prepare(ids=["bcq"])
        self.assertTrue(result["ok"])
        for shape_id in ["bcU", "bci", "other"]:
            self.assertEqual(ET.tostring(node(PAGE, shape_id)), ET.tostring(node(result["xml"], shape_id)))
        self.assertEqual(node(result["xml"], "bcq").attrib, node(PAGE, "bcq").attrib)
        self.assertEqual("".join(node(result["xml"], "bcq").itertext()), "开放台账")

    def test_rect_and_text_use_schema_defaults_without_unnecessary_edits(self):
        rect = PAGE.replace('id="bcq" type="ellipse"', 'id="bcq" type="rect"').replace('width="56" height="56"', 'width="66" height="66"', 1)
        result = self.prepare(rect)
        self.assertTrue(result["ok"])
        self.assertEqual(result["xml"], rect)
        self.assertEqual(set(result["containers"][0]["effective_padding_before"].values()), {5})
        text = rect.replace('id="bcq" type="rect"', 'id="bcq" type="text"')
        result = self.prepare(text)
        self.assertTrue(result["ok"])
        self.assertEqual(result["xml"], text)
        self.assertEqual(set(result["containers"][0]["effective_padding_before"].values()), {0})

    def test_explicit_asymmetric_padding_is_respected_then_zeroed(self):
        xml = PAGE.replace('bold="true">', 'bold="true" paddingTop="2" paddingRight="7" paddingBottom="3" paddingLeft="8">', 1)
        result = self.prepare(xml)
        self.assertTrue(result["ok"])
        row = result["containers"][0]
        self.assertEqual(row["effective_padding_before"], {"paddingTop": 2, "paddingRight": 7, "paddingBottom": 3, "paddingLeft": 8})
        self.assertEqual(set(row["padding_after"].values()), {0})
        self.assertEqual(node(result["xml"], "bcq").get("width"), "56")

    def test_long_text_returns_needed_box_without_deliverable_or_font_reduction(self):
        xml = PAGE.replace("<p>开放</p><p>台账</p>", "<p>完整保留项目事实和年度目标</p><p>完整保留验收指标和实施边界</p>", 1)
        before = xml.encode()
        result = self.prepare(xml, ids=["bcq", "bcU"])
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "needs_action")
        self.assertNotIn("xml", result)
        row = result["containers"][0]
        self.assertGreater(row["needed_bbox"]["height"], row["after"]["available_bbox"]["height"])
        self.assertEqual(row["needed_bbox"]["coordinate_space"], "text_area")
        self.assertTrue(row["suggestions"])
        self.assertNotIn("resize_outer_frame", [s["action"] for s in row["suggestions"]])
        self.assertEqual(self.source.read_bytes(), before)

    def test_allow_resize_adds_suggestion_only(self):
        xml = PAGE.replace("<p>开放</p><p>台账</p>", "<p>完整项目事实和年度目标</p><p>完整验收指标和边界</p>", 1)
        result = self.prepare(xml, allow_resize=True)
        self.assertFalse(result["ok"])
        self.assertNotIn("xml", result)
        suggestion = next(s for s in result["containers"][0]["suggestions"] if s["action"] == "resize_outer_frame")
        self.assertGreater(suggestion["bbox"]["height"], 56)
        self.assertEqual(suggestion["bbox"]["x"], 164)
        self.assertEqual(suggestion["bbox"]["y"], 202)
        self.assertTrue(suggestion["review_connections"])
        self.assertEqual(self.source.read_text(), xml)

    def test_prefixed_namespace_and_single_quotes_are_preserved(self):
        xml = PAGE.replace(f'xmlns="{NS}"', f'xmlns:s="{NS}"')
        import re
        xml = re.sub(r"<(\/?)(slide|data|shape|content|p|span|line|note)(?=[\s>\/])", r"<\1s:\2", xml)
        xml = xml.replace('fontFamily="思源黑体"', "fontFamily='思源黑体'")
        result = self.prepare(xml)
        self.assertTrue(result["ok"])
        self.assertIn("fontFamily='思源黑体'", result["xml"])
        expected = xml.replace('bold="true">', 'bold="true" paddingTop="0" paddingRight="0" paddingBottom="0" paddingLeft="0">', 1)
        self.assertEqual(result["xml"], expected)

    def test_attribute_value_that_mentions_padding_is_not_rewritten(self):
        xml = PAGE.replace('fontFamily="思源黑体"', "fontFamily=\"思源黑体 paddingLeft='6'\"", 1)
        result = self.prepare(xml)
        self.assertTrue(result["ok"])
        expected = xml.replace('bold="true">', 'bold="true" paddingTop="0" paddingRight="0" paddingBottom="0" paddingLeft="0">', 1)
        self.assertEqual(result["xml"], expected)

    def test_no_wrap_checks_width_even_when_height_fits(self):
        xml = PAGE.replace('bold="true">', 'bold="true" wrap="false">', 1).replace("<p>开放</p>", "<p>开放联合攻关</p>", 1)
        result = self.prepare(xml)
        self.assertFalse(result["ok"])
        self.assertGreater(result["containers"][0]["needed_bbox"]["width"], 56 / math.sqrt(2))
        self.assertNotIn("xml", result)

    def test_inline_letter_spacing_and_blank_paragraphs_keep_their_capacity(self):
        spaced = PAGE.replace("<p>开放</p>", '<p><span letterSpacing="20">开放</span></p>', 1)
        blank = PAGE.replace("<p>开放</p><p>台账</p>", "<p>开放</p><p></p><p>台账</p>", 1)
        for xml in [spaced, blank]:
            with self.subTest(xml=xml):
                result = self.prepare(xml)
                self.assertFalse(result["ok"])
                self.assertNotIn("xml", result)
                self.assertGreater(result["containers"][0]["after"]["line_count"], 2)
                self.assertEqual(self.source.read_text(), xml)

    def test_paragraph_font_override_is_measured_without_changing_the_run(self):
        xml = PAGE.replace("<p>开放</p>", '<p fontSize="32">开放</p>', 1)
        result = self.prepare(xml)
        self.assertFalse(result["ok"])
        self.assertNotIn("xml", result)
        self.assertEqual(self.source.read_text(), xml)

    def test_invalid_selection_is_rejected(self):
        for ids in [[], ["missing"], ["bcq", "bcq"], ["link"]]:
            with self.subTest(ids=ids), self.assertRaises(ValueError):
                prepare_text_containers(self.source, ids)

    def test_unsupported_shape_or_text_layout_does_not_claim_fit(self):
        for xml in [PAGE.replace('id="bcq" type="ellipse"', 'id="bcq" type="triangle"'),
                    PAGE.replace('bold="true">', 'bold="true" lineSpacing="invalid">', 1),
                    PAGE.replace('width="56" height="56"', 'width="56" height="56" vert="vert"', 1)]:
            with self.subTest(xml=xml):
                result = self.prepare(xml)
                self.assertFalse(result["ok"])
                self.assertNotIn("xml", result)
                self.assertEqual(result["containers"][0]["status"], "unsupported")

    def test_cli_writes_full_xml_and_report_sidecar_without_changing_source(self):
        output = Path(self.tmp.name) / "prepared.xml"
        before = self.source.read_bytes()
        run = subprocess.run([sys.executable, str(SCRIPT), "prepare", "--source", str(self.source), "--ids", "bcq", "--output", str(output)], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        self.assertTrue(report["ok"])
        self.assertTrue(output.is_file())
        manifest = json.loads(output.with_suffix(".text-fit.json").read_text())
        self.assertEqual(manifest["source_sha256"], hashlib.sha256(before).hexdigest())
        self.assertEqual(manifest["xml_sha256"], hashlib.sha256(output.read_bytes()).hexdigest())
        self.assertEqual(self.source.read_bytes(), before)

    def test_cli_failure_and_existing_output_never_emit_or_overwrite_xml(self):
        output = Path(self.tmp.name) / "blocked.xml"
        self.source.write_text(PAGE.replace("<p>开放</p>", "<p>完整项目事实与实施阶段验收指标</p>", 1))
        run = subprocess.run([sys.executable, str(SCRIPT), "prepare", "--source", str(self.source), "--ids", "bcq", "--output", str(output), "--allow-resize"], capture_output=True, text=True)
        self.assertEqual(run.returncode, 2)
        self.assertFalse(json.loads(run.stdout)["ok"])
        self.assertFalse(output.exists())
        self.assertFalse(output.with_suffix(".text-fit.json").exists())
        output.write_text("existing output")
        run = subprocess.run([sys.executable, str(SCRIPT), "prepare", "--source", str(self.source), "--ids", "bcq", "--output", str(output)], capture_output=True, text=True)
        self.assertEqual(run.returncode, 2)
        self.assertEqual(output.read_text(), "existing output")


if __name__ == "__main__":
    unittest.main()
