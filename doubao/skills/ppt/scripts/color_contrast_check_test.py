from __future__ import annotations

import copy
import sys
import io
import unittest
from unittest import mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import color_contrast_check as checker


def title_sampling_xml(panel_x: float = 180, panel_width: float = 110,
                       foreground: str = "rgba(30,58,95,1)",
                       panel_color: str = "rgba(255,255,255,1)") -> str:
    """Minimal SML fixture retaining the reported title and adjacent label geometry."""
    return (
        '<presentation xmlns="https://www.larkoffice.com/sml/2.0" width="960" height="540">'
        '<slide><style><fill><fillColor color="rgba(255,255,255,1)"/></fill></style><data>'
        '<shape type="text" topLeftX="64" topLeftY="56" width="200" height="50">'
        '<fill><fillColor color="rgba(255,255,255,1)"/></fill>'
        '<content textType="title" fontSize="34" fontFamily="思源黑体" '
        f'color="{foreground}" bold="true" wrap="false">'
        f'<p><strong><span color="{foreground}">目录</span></strong></p></content></shape>'
        f'<shape type="rect" topLeftX="{panel_x}" topLeftY="66" width="{panel_width}" height="30">'
        f'<fill><fillColor color="{panel_color}"/></fill></shape>'
        '</data></slide></presentation>'
    )


def formatted_title_xml(tag: str, panel_x: float = 180) -> str:
    xml = title_sampling_xml(panel_x)
    body = f'<a href="https://example.com">目录</a>' if tag == "a" else f'<{tag}>目录</{tag}>'
    xml = xml.replace('目录', body)
    if tag in {"u", "del"}:
        attr = "underline" if tag == "u" else "strikethrough"
        xml = xml.replace('wrap="false"', f'wrap="false" {attr}="true"')
    return xml


def paint_alpha_xml(tag: str, position: str, object_alpha: float, color_alpha: float) -> str:
    xml = title_sampling_xml().replace('<strong>', '').replace('</strong>', '')
    root = checker.ET.fromstring(xml)
    data = next(node for node in root.iter() if checker.local_name(node) == "data")
    paint = data[1]
    paint.tag = paint.tag.replace('shape', tag)
    paint.set('alpha', str(object_alpha))
    paint.set('topLeftX', '64')
    paint.set('width', '200')
    if tag == "icon":
        paint.attrib.pop('type')
        paint.set('iconType', 'iconpark/Charts/chart-line.svg')
    paint[0][0].set('color', f'rgba(30,58,95,{color_alpha})')
    # The text shape has no own fill, so the layer is visible behind its glyphs.
    data[0].remove(data[0][0])
    if position == "behind":
        data.remove(paint)
        data.insert(0, paint)
    return checker.ET.tostring(root, encoding="unicode").replace("ns0:", "").replace("xmlns:ns0", "xmlns")


def rowspan_table_xml() -> str:
    def cell(text, span=""):
        return (f'<td {span}><fill><fillColor color="rgba(255,255,255,1)"/></fill>'
                f'<content fontSize="16" color="rgba(31,35,41,1)"><p>{text}</p></content></td>')

    merged = cell("MERGED", 'rowspan="2"')
    return (
        '<presentation xmlns="https://www.larkoffice.com/sml/2.0" width="960" height="540">'
        '<slide><data><table topLeftX="40" topLeftY="40" width="200" height="110">'
        '<colgroup><col span="2" width="100"/></colgroup>'
        f'<tr height="20">{merged}{cell("TOP")}</tr>'
        f'<tr height="60">{cell("NEIGHBOR")}</tr>'
        f'<tr height="30">{cell("RELEASED")}{cell("BOTTOM")}</tr></table>'
        '<shape type="rect" topLeftX="40" topLeftY="65" width="100" height="30">'
        '<fill><fillColor color="rgba(255,255,255,1)"/></fill></shape>'
        '</data></slide></presentation>'
    )


class TextSamplingRegressionTest(unittest.TestCase):
    def test_simple_formatting_retains_glyph_samples_and_real_occlusion(self) -> None:
        for tag in ("a", "u", "del"):
            for x, expected in ((180, "PASS"), (64, "FAIL")):
                with self.subTest(tag=tag, x=x):
                    records, slides = checker.parse_xml_root(checker.ET.fromstring(formatted_title_xml(tag, x)))
                    self.assertIn("sample_bbox", records[0])
                    item = checker.check(records, slides, "", checker.DEFAULT_CONTRAST_GATE)[0][0]
                    self.assertEqual(item["verdict"], expected)
                    if expected == "FAIL":
                        self.assertEqual(checker.lint_level(item), "error")

    def test_inline_decoration_attributes_retain_samples(self) -> None:
        for attr in ("underline", "strikethrough"):
            xml = title_sampling_xml().replace('目录', f'<span {attr}="true">目录</span>')
            records, slides = checker.parse_xml_root(checker.ET.fromstring(xml))
            self.assertIn("sample_bbox", records[0])
            self.assertFalse(checker.check(records, slides, "", checker.DEFAULT_CONTRAST_GATE)[1])

    def test_adjacent_label_does_not_cover_title_glyphs(self) -> None:
        records, slides = checker.parse_xml_root(checker.ET.fromstring(title_sampling_xml()))
        results, failed = checker.check(records, slides, "", checker.DEFAULT_CONTRAST_GATE)
        self.assertFalse(failed)
        self.assertEqual(results[0]["verdict"], "PASS")
        self.assertAlmostEqual(results[0]["contrast"], 11.5026, places=4)
        self.assertEqual(records[0]["bbox"], (64, 56, 200, 50))
        for point, x in zip(results[0]["sample_points"], (81.85, 99.7, 117.55)):
            self.assertAlmostEqual(point["x"], x)
            self.assertAlmostEqual(point["y"], 81)

    def test_moved_label_and_real_occlusion(self) -> None:
        for x, width, expected in ((140, 110, "PASS"), (64, 30, "FAIL"),
                                   (110, 30, "FAIL"), (64, 200, "FAIL")):
            with self.subTest(x=x, width=width):
                records, slides = checker.parse_xml_root(checker.ET.fromstring(title_sampling_xml(x, width)))
                item = checker.check(records, slides, "", checker.DEFAULT_CONTRAST_GATE)[0][0]
                self.assertEqual(item["verdict"], expected)
                if expected == "FAIL":
                    self.assertEqual(item["contrast"], 1)
                    self.assertEqual(checker.lint_level(item), "error")
                    self.assertTrue(item["worst_sample_covered"])

    def test_low_contrast_is_not_downgraded_by_adjacent_decoration(self) -> None:
        for alpha in (0, 1):
            with self.subTest(alpha=alpha):
                xml = title_sampling_xml(foreground="rgba(210,210,210,1)",
                                         panel_color=f"rgba(255,255,255,{alpha})")
                item = checker.check(*checker.parse_xml_root(checker.ET.fromstring(xml)), "", 4.5)[0][0]
                self.assertEqual(item["verdict"], "FAIL")
                self.assertEqual(checker.lint_level(item), "error")
                self.assertAlmostEqual(item["contrast"], 1.5119, places=4)

    def test_translucent_occlusion_keeps_compositing(self) -> None:
        xml = title_sampling_xml(64, 200, panel_color="rgba(255,255,255,0.75)")
        item = checker.check(*checker.parse_xml_root(checker.ET.fromstring(xml)), "", 4.5)[0][0]
        expected_fg = checker.over((255, 255, 255, .75), (30, 58, 95, 1))
        self.assertAlmostEqual(item["contrast"], checker.contrast(expected_fg[:3], (255, 255, 255)))
        self.assertEqual(item["verdict"], "FAIL")
        self.assertTrue(item["worst_sample_covered"])
        self.assertEqual(checker.lint_level(item), "warning")

    def test_alignment_padding_and_original_bbox(self) -> None:
        import xml_lint

        for align in ("left", "center", "right"):
            for vertical in ("top", "middle", "bottom"):
                with self.subTest(align=align, vertical=vertical):
                    xml = title_sampling_xml().replace(
                        'wrap="false"', f'wrap="false" textAlign="{align}" verticalAlign="{vertical}" '
                        'paddingLeft="10" paddingRight="20" paddingTop="3" paddingBottom="4"')
                    root = checker.ET.fromstring(xml)
                    records, slides = checker.parse_xml_root(root)
                    element = xml_lint.extract_elements(xml_lint.serialize_slide_for_layout(root[0]))[0]
                    bbox = xml_lint.estimate_text_visual_bbox(element)
                    expected_x = {"left": 74, "center": 123.3, "right": 172.6}[align]
                    expected_y = {"top": 59, "middle": 60.1, "bottom": 61.2}[vertical]
                    self.assertAlmostEqual(bbox["x"], expected_x)
                    self.assertAlmostEqual(bbox["y"], expected_y)
                    self.assertEqual(records[0]["bbox"], (64, 56, 200, 50))
                    self.assertEqual(records[0]["sample_bbox"], tuple(bbox[k] for k in ("x", "y", "width", "height")))
                    points = checker.check(records, slides, "", 4.5)[0][0]["sample_points"]
                    for point, fraction in zip(points, (.25, .5, .75)):
                        self.assertAlmostEqual(point["x"], expected_x + 71.4 * fraction)
                        self.assertAlmostEqual(point["y"], expected_y + 20.4)

    def test_unsupported_layouts_keep_original_samples(self) -> None:
        base = title_sampling_xml()
        replacements = [
            ('目录', '目录<span color="rgba(210,210,210,1)">附录</span>'),
            ('目录', '目录<span fontSize="20">附录</span>'),
            ('</p>', '</p><p>附录</p>'),
            ('目录', '目<br/>录'),
            ('wrap="false"', 'wrap="true"'),
            ('type="text"', 'type="text" rotation="15"'),
            ('type="text"', 'type="text" vert="vert"'),
            ('wrap="false"', 'wrap="false" autoFit="normal-auto-fit"'),
            ('wrap="false"', 'wrap="false" autoFit="shape-auto-fit"'),
            ('wrap="false"', 'wrap="false" italic="true"'),
            ('<p>', '<p list="bullet">'),
            ('<p>', '<p textAlign="right">'),
            ('<p>', '<p indent="10">'),
            ('<p>', '<p marginLeft="10">'),
            ('<p>', '<p beforeLineSpacing="fixed:10">'),
            ('目录', '<span baseline="10">目录</span>'),
            ('目录', '<span letterSpacing="10">目录</span>'),
            ('目录', '<span fontSize="20">目录</span>'),
            ('目录', '<span fontSize="100"></span>目录'),
            ('目录', '<span fontFamily="Arial">目录</span>'),
            ('目录', '<span bold="false">目录</span>'),
            ('目录', ' 目录'), ('目录', '目录 '), ('目录', '目\t录'),
            ('目录', '目<tab/>录'), ('目录', '目\n录'),
            ('目录', '目  录'),
            ('width="200"', 'width="0"'), ('height="50"', 'height="0"'),
            ('width="200"', 'width="-1"'),
            ('type="text"', 'type="rect"'),
        ]
        for old, new in replacements:
            with self.subTest(old=old, new=new):
                xml = base.replace(old, new)
                if new == 'wrap="true"':
                    xml = xml.replace('width="200"', 'width="40"')
                root = checker.ET.fromstring(xml)
                records, slides = checker.parse_xml_root(root)
                old_records, old_slides = checker.parse_xml_root(root, resolve_sample_bboxes=False)
                self.assertTrue(records)
                self.assertTrue(all("sample_bbox" not in record for record in records))
                self.assertEqual(checker.check(records, slides, "", 4.5),
                                 checker.check(old_records, old_slides, "", 4.5))

    def test_full_text_controls_eligibility_beyond_diagnostic_limit(self) -> None:
        for text in ("A" * 170 + " ", "A" * 170 + "\t", "A" * 170 + "<br/>B"):
            xml = title_sampling_xml().replace('目录', text).replace('width="200"', 'width="9000"')
            records, _ = checker.parse_xml_root(checker.ET.fromstring(xml))
            self.assertEqual(len(records[0]["text"]), 160)
            self.assertTrue(all("sample_bbox" not in item for item in records))

    def test_xml_path_mapping_survives_missing_geometry_and_duplicate_ids(self) -> None:
        root = checker.ET.fromstring(title_sampling_xml())
        slide = root[0]
        data = next(node for node in slide if checker.local_name(node) == "data")
        data.insert(0, checker.ET.fromstring('<shape type="text"><content><p>MISSING</p></content></shape>'))
        data[1].set("id", "duplicate")
        second = copy.deepcopy(data[1])
        second.set("topLeftX", "400")
        data.append(second)
        second_slide = copy.deepcopy(slide)
        second_slide.find('.//{https://www.larkoffice.com/sml/2.0}shape').set("topLeftX", "200")
        root.append(second_slide)
        records, _ = checker.parse_xml_root(root)
        self.assertEqual([(r["slide"], r["object_path"]) for r in records],
                         [(page, f"data/shape[{index}]") for page in (1, 2) for index in (1, 2, 4)])
        self.assertNotIn("sample_bbox", records[0])
        self.assertAlmostEqual(records[1]["sample_bbox"][0], 64)
        self.assertAlmostEqual(records[2]["sample_bbox"][0], 400)
        self.assertAlmostEqual(records[4]["sample_bbox"][0], 200)
        self.assertAlmostEqual(records[5]["sample_bbox"][0], 400)


class ContrastMathTest(unittest.TestCase):
    def check_xml(self, xml: str, threshold: float = 4.5) -> tuple[list[dict], bool]:
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "slide.xml"
            path.write_text(xml, encoding="utf-8")
            records, slides = checker.parse_xml(str(path))
        return checker.check(records, slides, "", threshold)

    def test_alpha_is_composited(self) -> None:
        self.assertLess(checker.contrast(checker.over((0, 0, 0, 0.25), (255, 255, 255, 1))[:3], (255, 255, 255)), 4.5)

    def test_bold_19px_is_large_text(self) -> None:
        self.assertTrue(checker.is_large(19, True))
        self.assertFalse(checker.is_large(19, False))

    def test_only_giant_short_display_text_is_decorative(self) -> None:
        self.assertTrue(checker.is_decorative_display_text("SM", 260))
        self.assertFalse(checker.is_decorative_display_text("项目报告", 260))
        self.assertFalse(checker.is_decorative_display_text("SM", 48))

    def test_only_large_image_backed_numeric_badges_are_visual_review_only(self) -> None:
        self.assertTrue(checker.is_decorative_navigation_token("01", 40, True))
        self.assertTrue(checker.is_decorative_navigation_token("5", 32, True))
        self.assertFalse(checker.is_decorative_navigation_token("01", 24, True))
        self.assertFalse(checker.is_decorative_navigation_token("2026", 40, True))
        self.assertFalse(checker.is_decorative_navigation_token("01", 40, False))

    def test_visual_roles_do_not_become_contrast_failures(self) -> None:
        self.assertTrue(checker.is_display_percent("17%", 38))
        self.assertFalse(checker.is_display_percent("93.7%", 92))
        self.assertFalse(checker.is_display_percent("18%", 14))
        self.assertTrue(checker.is_white_status_card_label((255, 255, 255, 1), (23, 197, 68, 1), (0, 0, 96, 55)))
        self.assertFalse(checker.is_white_status_card_label((255, 255, 255, 1), (220, 220, 220, 1), (0, 0, 96, 55)))
        self.assertTrue(checker.is_connector_label("render payload", (0, 0, 170, 32)))
        self.assertFalse(
            checker.is_connector_label("Residual risk: APAC evening saturation remains under watch.", (0, 0, 495, 40))
        )
        self.assertTrue(checker.is_dark_gradient_annotation((32, 45, 48, 1), 2.81, True))
        self.assertFalse(checker.is_dark_gradient_annotation((32, 45, 48, 1), 2.1, True))

    def test_gradient_keeps_its_light_end(self) -> None:
        light = checker.color_or_gradient("linear-gradient(90deg,rgba(24,32,38,1) 0%,rgba(251,249,239,1) 100%)", 1)
        self.assertGreater(checker.luminance(light[:3]), 0.9)

    def test_single_stop_gradient_is_a_solid_rgba_color(self) -> None:
        color = checker.color_or_gradient("linear-gradient(90deg,rgba(12,34,56,1) 50%)", 0.5)
        self.assertEqual(color, (12, 34, 56, 1.0))

    def test_float_geometry_and_plain_text_are_parsed(self) -> None:
        xml = """<presentation xmlns="https://www.larkoffice.com/sml/2.0"><slide id="p1"><style><fill><fillColor color="rgba(255,255,255,1)"/></fill></style><data><shape topLeftX="10.5" topLeftY="20.5" width="200.5" height="60.5" type="text"><content color="rgba(205,202,191,1)" fontSize="16"><p>PLAIN_TEXT</p></content></shape></data></slide></presentation>"""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "slide.xml"
            path.write_text(xml, encoding="utf-8")
            records, slides = checker.parse_xml(str(path))
        self.assertEqual(records[0]["text"], "PLAIN_TEXT")
        self.assertEqual(records[0]["bbox"][0], 10.5)
        results, has_fail = checker.check(records, slides, "", 4.5)
        self.assertTrue(has_fail)
        self.assertEqual(results[0]["verdict"], "FAIL")

    def test_parse_xml_root_supports_xml_lint_in_memory_root(self) -> None:
        root = checker.ET.fromstring(
            '<presentation xmlns="https://www.larkoffice.com/sml/2.0"><slide id="p1"><data>'
            '<shape topLeftX="0" topLeftY="0" width="200" height="80" type="text">'
            '<content color="rgba(200,200,200,1)" fontSize="16"><p>ROOT_INPUT</p></content>'
            "</shape></data></slide></presentation>"
        )
        records, slides = checker.parse_xml_root(root)
        self.assertEqual(records[0]["text"], "ROOT_INPUT")
        self.assertIn(1, slides)

    def test_production_result_is_a_compact_issue_with_single_line_message(self) -> None:
        item = {
            "slide": 9,
            "slide_id": "pPF",
            "object_path": "data/shape[2]",
            "text": "靠色测试文本",
            "verdict": "FAIL",
            "contrast": 1.4,
            "complex_background": False,
            "source": "shape",
            "bg_source": "xml layered fill",
            "effective_fg_color": "rgba(163, 163, 163, 1)",
            "effective_bg_color": "rgba(204, 204, 204, 1)",
        }
        issue = checker.production_result(item)
        self.assertEqual(set(issue), {"slide_number", "slide_id", "xml_path", "level", "message"})
        self.assertEqual(issue["xml_path"], "data/shape[2]")
        self.assertEqual(issue["level"], "error")
        self.assertNotIn("\\n", issue["message"])
        self.assertNotIn("1.571", issue["message"])
        self.assertIn("文字与背景对比度不足", issue["message"])
        self.assertIn("背景来自页面元素底色", issue["message"])

    def test_lint_level_blocks_only_deterministic_severe_failures(self) -> None:
        # Default gate 2.25: only ratios below 1.80 (80% of the gate) block.
        self.assertEqual(
            checker.lint_level(
                {
                    "verdict": "FAIL",
                    "contrast": 1.79,
                    "required_contrast": 2.25,
                    "complex_background": False,
                    "source": "shape",
                }
            ),
            "error",
        )
        self.assertEqual(
            checker.lint_level(
                {
                    "verdict": "FAIL",
                    "contrast": 1.80,
                    "required_contrast": 2.25,
                    "complex_background": False,
                    "source": "shape",
                }
            ),
            "warning",
        )
        self.assertEqual(
            checker.lint_level(
                {
                    "verdict": "FAIL",
                    "contrast": 2.0,
                    "required_contrast": 2.25,
                    "complex_background": False,
                    "source": "shape",
                }
            ),
            "warning",
        )
        # The item-specific gate keeps --threshold and complex-background gates aligned.
        self.assertEqual(
            checker.lint_level(
                {
                    "verdict": "FAIL",
                    "contrast": 2.39,
                    "required_contrast": 3.0,
                    "complex_background": False,
                    "source": "shape",
                }
            ),
            "error",
        )
        self.assertEqual(
            checker.lint_level(
                {
                    "verdict": "FAIL",
                    "contrast": 2.40,
                    "required_contrast": 3.0,
                    "complex_background": False,
                    "source": "shape",
                }
            ),
            "warning",
        )
        self.assertEqual(
            checker.lint_level(
                {
                    "verdict": "FAIL",
                    "contrast": 1.4,
                    "required_contrast": 2.25,
                    "complex_background": True,
                    "source": "shape",
                }
            ),
            "warning",
        )
        self.assertEqual(
            checker.lint_level(
                {
                    "verdict": "FAIL",
                    "contrast": 1.4,
                    "required_contrast": 2.25,
                    "complex_background": False,
                    "source": "polyline",
                }
            ),
            "warning",
        )

    def ghost_level(self, text, font_size, color, shape_alpha=None) -> str:
        return checker.lint_level(
            {
                "verdict": "FAIL",
                "contrast": 1.4,
                "complex_background": False,
                "source": "shape",
                "text": text,
                "font_size": font_size,
                "fg_color": color,
                "shape_alpha": shape_alpha,
            }
        )

    def test_ghost_text_is_reported_without_blocking(self) -> None:
        """A faint oversized ornament must warn, never contribute to error_count."""
        # The two bands are owned by xml_lint.is_ghost_text: >96px under .5 alpha, >=36px under .35.
        self.assertEqual(self.ghost_level("CONTENTS", 120, "rgba(40,40,40,0.4)"), "warning")
        self.assertEqual(self.ghost_level("03", 40, "rgba(40,40,40,0.3)"), "warning")
        # Faintness may come from the shape's alpha rather than the text colour.
        self.assertEqual(self.ghost_level("2025", 60, "rgba(60,35,20,1)", 0.3), "warning")

    def test_ghost_text_delegates_to_xml_lint(self) -> None:
        item = {"text": "CONTENTS", "font_size": 120, "fg_color": "rgba(40,40,40,0.4)"}
        with mock.patch("xml_lint.is_ghost_text", return_value=True) as ghost_text:
            self.assertTrue(checker.is_ghost_decorative_text(item))
        ghost_text.assert_called_once_with(
            {
                "kind": "shape",
                "type": "text",
                "text": "CONTENTS",
                "fontSize": 120,
                "textAlpha": 0.4,
            }
        )

    def test_ordinary_low_contrast_copy_still_blocks(self) -> None:
        """The exemption must not leak onto real body copy or opaque display text."""
        # Prose is never an ornament, however large and faint the run is.
        self.assertEqual(self.ghost_level("我们的核心优势是稳定交付", 40, "rgba(150,150,150,0.55)"), "error")
        self.assertEqual(self.ghost_level("Investment is shifting", 40, "rgba(150,150,150,0.55)"), "error")
        # A short token painted fully opaque is ordinary display copy, not a ghost ornament.
        self.assertEqual(self.ghost_level("01", 48, "rgba(150,150,150,1)"), "error")
        self.assertEqual(self.ghost_level("01", 48, "rgba(150,150,150,0.55)"), "error")
        # Small faint text is unreadable body copy, not background decoration.
        self.assertEqual(self.ghost_level("01", 18, "rgba(150,150,150,0.3)"), "error")
        # Multi-word display text carries meaning and keeps the full requirement.
        self.assertEqual(self.ghost_level("CORE VALUE", 60, "rgba(150,150,150,0.45)"), "error")
        # A missing font size must not silently exempt anything.
        self.assertEqual(self.ghost_level("01", None, "rgba(150,150,150,0.3)"), "error")

    def test_ghost_ornament_still_appears_in_issue_output(self) -> None:
        """Downgrading to warning must not hide the finding: it stays a FAIL issue."""
        xml = (
            '<presentation xmlns="https://www.larkoffice.com/sml/2.0"><slide id="p1">'
            '<style><fill><fillColor color="rgba(250,248,244,1)"/></fill></style><data>'
            '<shape id="ghost" topLeftX="40" topLeftY="40" width="220" height="160" type="text">'
            '<content color="rgba(210,205,195,0.4)" fontSize="120"><p>01</p></content></shape>'
            "</data></slide></presentation>"
        )
        results, has_fail = self.check_xml(xml)
        self.assertTrue(has_fail)
        issue = next(item for item in results if item["verdict"] == "FAIL")
        self.assertEqual(checker.lint_level(issue), "warning")
        message = checker.issue_message(issue)
        self.assertIn("可能是幽灵字", message)
        self.assertIn("仅作为背景装饰", message)
        self.assertIn("正文、标题、状态或导航信息", message)
        self.assertNotIn("\\n", message)
        totals = checker.summary(results, has_fail)
        self.assertTrue(totals["has_issues"])
        self.assertFalse(totals["has_blocking_issues"])
        self.assertEqual(totals["issue_count"], 1)
        self.assertEqual(totals["warning_count"], 1)
        self.assertEqual(totals["review_pages"], [1])

    def test_shape_alpha_is_applied_to_visible_foreground(self) -> None:
        xml = (
            '<presentation xmlns="https://www.larkoffice.com/sml/2.0"><slide id="p1">'
            '<style><fill><fillColor color="rgba(255,255,255,1)"/></fill></style><data>'
            '<shape alpha="0.3" topLeftX="40" topLeftY="40" width="220" height="80" type="text">'
            '<content color="rgba(0,0,0,1)" fontSize="16"><p>FAINT_BLACK</p></content></shape>'
            "</data></slide></presentation>"
        )
        results, has_fail = self.check_xml(xml)
        self.assertTrue(has_fail)
        self.assertEqual(results[0]["verdict"], "FAIL")
        self.assertLess(results[0]["contrast"], 4.5)

    def test_shape_alpha_is_applied_to_its_fill_background(self) -> None:
        xml = (
            '<presentation xmlns="https://www.larkoffice.com/sml/2.0"><slide id="p1">'
            '<style><fill><fillColor color="rgba(255,255,255,1)"/></fill></style><data>'
            '<shape alpha="0.3" topLeftX="40" topLeftY="40" width="220" height="80" type="text">'
            '<fill><fillColor color="rgba(0,0,0,1)"/></fill>'
            '<content color="rgba(255,255,255,1)" fontSize="16"><p>FAINT_WHITE</p></content></shape>'
            "</data></slide></presentation>"
        )
        results, has_fail = self.check_xml(xml)
        self.assertTrue(has_fail)
        self.assertEqual(results[0]["verdict"], "FAIL")
        self.assertTrue(results[0]["complex_background"])
        self.assertNotEqual(results[0]["effective_bg_color"], "rgba(0, 0, 0, 1)")

    def test_partial_background_paint_is_warning_not_blocking(self) -> None:
        """A bar touching one glyph sample still needs visual review."""
        xml = (
            '<presentation xmlns="https://www.larkoffice.com/sml/2.0"><slide id="p1">'
            '<style><fill><fillColor color="rgba(255,255,255,1)"/></fill></style><data>'
            '<shape id="accent" type="rect" topLeftX="110" topLeftY="100" width="15" height="60">'
            '<fill><fillColor color="rgba(90,115,55,1)"/></fill></shape>'
            '<shape id="label" type="text" topLeftX="100" topLeftY="100" width="400" height="60">'
            '<content color="rgba(0,90,60,1)" fontSize="32"><p>江门</p></content></shape>'
            "</data></slide></presentation>"
        )
        results, has_fail = self.check_xml(xml)
        self.assertTrue(has_fail)
        self.assertEqual(results[0]["verdict"], "FAIL")
        self.assertTrue(results[0]["complex_background"])
        self.assertEqual(results[0]["worst_sample"]["x"], 116.0)
        self.assertEqual(checker.lint_level(results[0]), "warning")

    def test_two_sample_background_paint_keeps_severe_failure_blocking(self) -> None:
        """A paint behind most samples is a deterministic background, not decoration."""
        xml = (
            '<presentation xmlns="https://www.larkoffice.com/sml/2.0"><slide id="p1">'
            '<style><fill><fillColor color="rgba(255,255,255,1)"/></fill></style><data>'
            '<shape id="card" type="rect" topLeftX="110" topLeftY="100" width="30" height="60">'
            '<fill><fillColor color="rgba(90,115,55,1)"/></fill></shape>'
            '<shape id="label" type="text" topLeftX="100" topLeftY="100" width="400" height="60">'
            '<content color="rgba(0,90,60,1)" fontSize="32"><p>江门</p></content></shape>'
            "</data></slide></presentation>"
        )
        results, has_fail = self.check_xml(xml)
        self.assertTrue(has_fail)
        self.assertEqual(results[0]["verdict"], "FAIL")
        self.assertFalse(results[0]["complex_background"])
        self.assertEqual(checker.lint_level(results[0]), "error")

    def test_warning_only_checker_exits_zero(self) -> None:
        xml = (
            '<presentation xmlns="https://www.larkoffice.com/sml/2.0"><slide id="p1">'
            '<style><fill><fillColor color="rgba(250,248,244,1)"/></fill></style><data>'
            '<shape topLeftX="40" topLeftY="40" width="220" height="160" type="text">'
            '<content color="rgba(210,205,195,0.4)" fontSize="120"><p>01</p></content></shape>'
            "</data></slide></presentation>"
        )
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "slide.xml"
            path.write_text(xml, encoding="utf-8")
            with mock.patch.object(sys, "argv", ["color_contrast_check.py", "--xml", str(path), "--format", "json"]):
                with mock.patch("sys.stdout", new_callable=io.StringIO):
                    self.assertEqual(checker.main(), 0)

    def test_later_overlay_changes_the_visible_contrast(self) -> None:
        xml = """<presentation xmlns="https://www.larkoffice.com/sml/2.0"><slide id="p1"><style><fill><fillColor color="rgba(255,255,255,1)"/></fill></style><data><shape topLeftX="0" topLeftY="0" width="400" height="200"><fill><fillColor color="rgba(35,45,42,1)"/></fill></shape><shape topLeftX="20" topLeftY="40" width="300" height="60" type="text"><content color="rgba(255,255,255,1)" fontSize="28"><p>OVERLAY</p></content></shape><shape topLeftX="0" topLeftY="0" width="400" height="200"><fill><fillColor color="rgba(255,255,255,.72)"/></fill></shape></data></slide></presentation>"""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "slide.xml"
            path.write_text(xml, encoding="utf-8")
            records, slides = checker.parse_xml(str(path))
        result, has_fail = checker.check(records, slides, "", 4.5)
        self.assertTrue(has_fail)
        self.assertEqual(result[0]["verdict"], "FAIL")

    def test_percentage_pattern_background_keeps_white_text_readable(self) -> None:
        xml = """<presentation xmlns="https://www.larkoffice.com/sml/2.0"><slide id="p1"><style><fill><fillPattern type="pct90" foregroundColor="rgba(192,0,0,1)" backgroundColor="rgba(255,255,255,1)" alpha="1"/></fill></style><data><shape topLeftX="0" topLeftY="0" width="400" height="100" type="text"><content color="rgba(255,255,255,1)" fontSize="32"><p>WHITE_ON_RED_PATTERN</p></content></shape></data></slide></presentation>"""
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "slide.xml"
            path.write_text(xml, encoding="utf-8")
            records, slides = checker.parse_xml(str(path))
        result, has_fail = checker.check(records, slides, "", 4.5)
        self.assertFalse(has_fail)
        self.assertEqual(result[0]["verdict"], "PASS")

    def test_transparent_text_background_does_not_mask_parent_shape(self) -> None:
        xml = """<presentation xmlns="https://www.larkoffice.com/sml/2.0"><slide id="p1"><style><fill><fillColor color="rgba(255,255,255,1)"/></fill></style><data><shape topLeftX="0" topLeftY="0" width="400" height="200"><fill><fillColor color="rgba(44,89,38,1)"/></fill></shape><shape topLeftX="20" topLeftY="40" width="300" height="60" type="text"><content color="rgba(255,255,255,1)" backgroundColor="rgba(255,255,255,0)" fontSize="20"><p>WHITE_ON_GREEN</p></content></shape></data></slide></presentation>"""
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "slide.xml"
            path.write_text(xml, encoding="utf-8")
            records, slides = checker.parse_xml(str(path))
        result, has_fail = checker.check(records, slides, "", 4.5)
        self.assertFalse(has_fail)
        self.assertEqual(result[0]["verdict"], "PASS")

    def test_icon_and_connector_backgrounds_are_checked(self) -> None:
        xml = """<presentation xmlns="https://www.larkoffice.com/sml/2.0"><slide id="p1"><style><fill><fillColor color="rgba(255,255,255,1)"/></fill></style><data><icon iconType="iconpark/Charts/chart-line.svg" topLeftX="20" topLeftY="20" width="240" height="100"><fill><fillColor color="rgba(46,125,50,1)"/></fill></icon><shape topLeftX="20" topLeftY="20" width="240" height="100" type="text"><content color="rgba(66,165,75,1)" fontSize="16"><p>ICON_BACKED</p></content></shape><line startX="20" startY="190" endX="260" endY="190"><border color="rgba(15,23,42,1)" width="80"/></line><shape topLeftX="20" topLeftY="150" width="240" height="80" type="text"><content color="rgba(30,41,59,1)" fontSize="16"><p>LINE_BACKED</p></content></shape></data></slide></presentation>"""
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "slide.xml"
            path.write_text(xml, encoding="utf-8")
            records, slides = checker.parse_xml(str(path))
        results, has_fail = checker.check(records, slides, "", 4.5)
        self.assertTrue(has_fail)
        self.assertEqual([result["verdict"] for result in results], ["FAIL", "FAIL"])

    def test_table_and_chart_backgrounds_apply_to_overlaid_text(self) -> None:
        xml = """<presentation xmlns="https://www.larkoffice.com/sml/2.0"><slide id="p1"><style><fill><fillColor color="rgba(255,255,255,1)"/></fill></style><data><table topLeftX="20" topLeftY="20" width="240" height="90"><colgroup><col width="240"/></colgroup><tr height="90"><td><fill><fillColor color="rgba(226,232,240,1)"/></fill></td></tr></table><shape topLeftX="20" topLeftY="20" width="240" height="90" type="text"><content color="rgba(203,213,225,1)" fontSize="16"><p>TABLE_BACKED</p></content></shape><chart topLeftX="20" topLeftY="150" width="240" height="90"><chartBackground color="rgba(191,219,254,1)"/></chart><shape topLeftX="20" topLeftY="150" width="240" height="90" type="text"><content color="rgba(147,197,253,1)" fontSize="16"><p>CHART_BACKED</p></content></shape></data></slide></presentation>"""
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "slide.xml"
            path.write_text(xml, encoding="utf-8")
            records, slides = checker.parse_xml(str(path))
        results, has_fail = checker.check(records, slides, "", 4.5)
        self.assertTrue(has_fail)
        self.assertEqual([result["verdict"] for result in results], ["FAIL", "FAIL"])

    def test_image_backed_text_is_excluded_without_a_screenshot(self) -> None:
        xml = """<presentation xmlns="https://www.larkoffice.com/sml/2.0"><slide id="p1"><style><fill><fillColor color="rgba(255,255,255,1)"/></fill></style><data><img topLeftX="0" topLeftY="0" width="400" height="200"/><shape topLeftX="20" topLeftY="40" width="300" height="60" type="text"><content color="rgba(255,255,255,1)" fontSize="16"><p>BODY_COPY</p></content></shape></data></slide></presentation>"""
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "slide.xml"
            path.write_text(xml, encoding="utf-8")
            records, slides = checker.parse_xml(str(path))
        result, has_fail = checker.check(records, slides, "", 4.5)
        self.assertFalse(has_fail)
        self.assertEqual(result[0]["verdict"], "SKIP")
        self.assertEqual(result[0]["reason"], "image-backed text excluded")

    def test_image_backed_text_is_excluded_even_with_an_unreadable_file(self) -> None:
        import tempfile

        xml = """<presentation xmlns="https://www.larkoffice.com/sml/2.0"><slide id="p1"><style><fill><fillColor color="rgba(255,255,255,1)"/></fill></style><data><img topLeftX="0" topLeftY="0" width="400" height="200"/><shape topLeftX="20" topLeftY="40" width="300" height="60" type="text"><content color="rgba(255,255,255,1)" fontSize="16"><p>IMAGE_TEXT</p></content></shape></data></slide></presentation>"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "slide.xml"
            path.write_text(xml, encoding="utf-8")
            bad = Path(directory) / "deck_p001_p1.jpg"
            bad.write_bytes(b"not an image")
            records, slides = checker.parse_xml(str(path))
            results, has_fail = checker.check(records, slides, directory, 4.5)
        self.assertFalse(has_fail)
        self.assertEqual(results[0]["verdict"], "SKIP")
        self.assertEqual(results[0]["reason"], "image-backed text excluded")

    def test_three_stop_gradient_uses_its_middle_stop(self) -> None:
        gradient = "linear-gradient(90deg,rgba(255,255,255,1) 0%,rgba(0,0,0,1) 50%,rgba(255,255,255,1) 100%)"
        self.assertEqual(checker.color_or_gradient(gradient, 0.5), (0, 0, 0, 1.0))

    def test_unsupported_pattern_is_skipped_instead_of_falling_back_to_page_fill(self) -> None:
        xml = """<presentation xmlns="https://www.larkoffice.com/sml/2.0"><slide id="p1"><style><fill><fillColor color="rgba(15,23,42,1)"/></fill></style><data><shape topLeftX="0" topLeftY="0" width="400" height="200"><fill><fillPattern type="diagCross" foregroundColor="rgba(255,255,255,1)" backgroundColor="rgba(0,0,0,1)"/></fill></shape><shape topLeftX="20" topLeftY="40" width="300" height="60" type="text"><content color="rgba(226,232,240,1)" fontSize="16"><p>UNSUPPORTED_PATTERN</p></content></shape></data></slide></presentation>"""
        results, has_fail = self.check_xml(xml)
        self.assertFalse(has_fail)
        self.assertEqual(results[0]["verdict"], "SKIP")
        self.assertEqual(results[0]["reason"], "unsupported background pattern")

    def test_polyline_background_keeps_existing_estimate(self) -> None:
        xml = """<presentation xmlns="https://www.larkoffice.com/sml/2.0"><slide id="p1"><style><fill><fillColor color="rgba(255,255,255,1)"/></fill></style><data><polyline topLeftX="20" topLeftY="40" width="300" height="60"><border color="rgba(203,213,225,1)" width="80"/></polyline><shape topLeftX="20" topLeftY="40" width="300" height="60" type="text"><content color="rgba(191,219,254,1)" fontSize="16"><p>POLYLINE_BACKED</p></content></shape></data></slide></presentation>"""
        results, has_fail = self.check_xml(xml)
        self.assertTrue(has_fail)
        self.assertEqual(results[0]["verdict"], "FAIL")

    def test_native_chart_title_label_and_legend_are_all_checked(self) -> None:
        xml = """<presentation xmlns="https://www.larkoffice.com/sml/2.0"><slide id="p1"><style><fill><fillColor color="rgba(255,255,255,1)"/></fill></style><data><chart topLeftX="20" topLeftY="20" width="400" height="220"><chartTitle color="rgba(147,197,253,1)" fontSize="16">CHART_TITLE</chartTitle><chartPlotArea><chartPlot type="column"><chartLabel color="rgba(147,197,253,1)" fontSize="11">CHART_LABEL</chartLabel></chartPlot></chartPlotArea><chartLegend color="rgba(147,197,253,1)" fontSize="11">CHART_LEGEND</chartLegend><chartStyle><chartBackground color="rgba(191,219,254,1)"/></chartStyle></chart></data></slide></presentation>"""
        results, has_fail = self.check_xml(xml)
        self.assertTrue(has_fail)
        self.assertEqual([item["text"] for item in results], ["CHART_TITLE", "CHART_LABEL", "CHART_LEGEND"])
        self.assertEqual([item["verdict"] for item in results], ["FAIL", "FAIL", "FAIL"])

    def test_xml_large_text_uses_three_to_one_threshold(self) -> None:
        xml = """<presentation xmlns="https://www.larkoffice.com/sml/2.0"><slide id="p1"><style><fill><fillColor color="rgba(255,255,255,1)"/></fill></style><data><shape topLeftX="0" topLeftY="0" width="400" height="200"><fill><fillColor color="rgba(255,255,255,1)"/></fill></shape><shape topLeftX="20" topLeftY="40" width="300" height="40" type="text"><content color="rgba(142,142,142,1)" fontSize="16"><p>SMALL</p></content></shape><shape topLeftX="20" topLeftY="110" width="300" height="50" type="text"><content color="rgba(142,142,142,1)" fontSize="24"><p>LARGE</p></content></shape></data></slide></presentation>"""
        results, has_fail = self.check_xml(xml)
        self.assertTrue(has_fail)
        self.assertEqual([item["verdict"] for item in results], ["FAIL", "PASS"])

    def test_table_colspan_resolves_the_low_contrast_cell_only(self) -> None:
        xml = """<presentation xmlns="https://www.larkoffice.com/sml/2.0"><slide id="p1"><style><fill><fillColor color="rgba(255,255,255,1)"/></fill></style><data><table topLeftX="20" topLeftY="20" width="400" height="100"><colgroup><col width="100"/><col width="150"/><col width="150"/></colgroup><tr height="100"><td><fill><fillColor color="rgba(15,23,42,1)"/></fill><content color="rgba(255,255,255,1)" fontSize="16"><p>GOOD</p></content></td><td colspan="2"><fill><fillColor color="rgba(226,232,240,1)"/></fill><content color="rgba(203,213,225,1)" fontSize="16"><p>BAD</p></content></td></tr></table></data></slide></presentation>"""
        results, has_fail = self.check_xml(xml)
        self.assertTrue(has_fail)
        self.assertEqual([item["verdict"] for item in results], ["PASS", "FAIL"])


class OverlayEvidenceTest(unittest.TestCase):
    def result(self, foreground="rgba(31,35,41,1)", overlay="rgba(244,244,244,1)", background=None):
        prefix = (
            '<shape topLeftX="0" topLeftY="0" width="60" height="40">'
            f'<fill><fillColor color="{background}"/></fill></shape>' if background else ""
        )
        xml = (
            '<presentation xmlns="https://www.larkoffice.com/sml/2.0"><slide><data>' + prefix
            + '<shape topLeftX="0" topLeftY="0" width="200" height="40">'
            f'<content color="{foreground}" fontSize="16"><p>BODY TEXT</p></content></shape>'
            '<shape topLeftX="90" topLeftY="0" width="110" height="40">'
            f'<fill><fillColor color="{overlay}"/></fill></shape>'
            '</data></slide></presentation>'
        )
        records, slides = checker.parse_xml_root(checker.ET.fromstring(xml))
        return checker.check(records, slides, "", checker.DEFAULT_CONTRAST_GATE)[0][0]

    def test_opaque_and_translucent_overlay_explain_selected_evidence(self):
        for alpha in (1, 0.8):
            with self.subTest(alpha=alpha):
                result = self.result(overlay=f"rgba(244,244,244,{alpha})")
                self.assertEqual(result["verdict"], "FAIL")
                self.assertEqual(result["worst_sample"]["x"], 100)
                message = checker.issue_message(result)
                for evidence in ("原始文字色为 rgba(31, 35, 41, 1)", "后绘制", "层级",
                                 result["effective_fg_color"], result["effective_bg_color"], "100", "20"):
                    self.assertIn(evidence, message)

    def test_transparent_overlay_does_not_explain_low_contrast(self):
        result = self.result(foreground="rgba(255,255,255,1)", overlay="rgba(244,244,244,0)")
        self.assertEqual(result["verdict"], "FAIL")
        self.assertNotIn("后绘制", checker.issue_message(result))
        self.assertIn("调整文字或其底色", checker.issue_message(result))

    def test_overlay_at_another_sample_is_not_the_worst_sample_cause(self):
        result = self.result(background="rgba(31,35,41,1)", overlay="rgba(244,244,244,0.5)")
        self.assertEqual(result["worst_sample"]["x"], 50)
        self.assertEqual(result["contrast"], 1)
        self.assertNotIn("后绘制", checker.issue_message(result))


class PaintAlphaRegressionTest(unittest.TestCase):
    def test_object_and_fill_alpha_have_identical_visible_results(self) -> None:
        for tag in ("shape", "icon"):
            for position in ("behind", "above"):
                for alpha in (0, .1, .5, 1):
                    with self.subTest(tag=tag, position=position, alpha=alpha):
                        items = []
                        for shape_alpha, fill_alpha in ((alpha, 1), (1, alpha)):
                            xml = paint_alpha_xml(tag, position, shape_alpha, fill_alpha)
                            items.append(checker.check(*checker.parse_xml_root(checker.ET.fromstring(xml)),
                                                       "", checker.DEFAULT_CONTRAST_GATE)[0][0])
                        for key in ("contrast", "effective_fg_color", "effective_bg_color", "verdict",
                                    "complex_background", "worst_sample_covered"):
                            self.assertEqual(items[0][key], items[1][key], key)
                        self.assertEqual(checker.lint_level(items[0]), checker.lint_level(items[1]))
                        if alpha == 0:
                            self.assertEqual(items[0]["verdict"], "PASS")
                            self.assertFalse(items[0]["complex_background"])
                        elif alpha == 1:
                            self.assertEqual(items[0]["verdict"], "FAIL")
                            self.assertEqual(checker.lint_level(items[0]), "error")

    def test_object_alpha_multiplies_gradient_stop_alpha(self) -> None:
        paint = checker.Paint(0, 0, 100, 40,
                              'linear-gradient(90deg,rgba(0,0,0,0.2) 0%,rgba(255,255,255,0.6) 100%)',
                              0, alpha=.5)
        self.assertEqual(paint.at(0), (0, 0, 0, .1))
        self.assertAlmostEqual(paint.at(50)[3], .2)
        self.assertEqual(paint.at(100), (255, 255, 255, .3))

    def test_invisible_background_does_not_downgrade_real_low_contrast(self) -> None:
        for shape_alpha, fill_alpha in ((0, 1), (1, 0)):
            xml = paint_alpha_xml("shape", "behind", shape_alpha, fill_alpha)
            xml = xml.replace('rgba(30,58,95,1)', 'rgba(210,210,210,1)')
            root = checker.ET.fromstring(xml)
            paint = next(node for node in root.iter() if node.get('alpha') is not None)
            paint.set('width', '20')  # Only one glyph sample intersects this invisible paint.
            item = checker.check(*checker.parse_xml_root(root), "", checker.DEFAULT_CONTRAST_GATE)[0][0]
            self.assertEqual(item["verdict"], "FAIL")
            self.assertFalse(item["complex_background"])
            self.assertEqual(checker.lint_level(item), "error")


class TableSpanRegressionTest(unittest.TestCase):
    def test_rowspan_preserves_neighbor_and_detects_merged_cell_occlusion(self):
        root = checker.ET.fromstring(rowspan_table_xml())
        records, slides = checker.parse_xml_root(root)
        self.assertEqual([r["bbox"] for r in records],
                         [(40, 40, 100, 80), (140, 40, 100, 20), (140, 60, 100, 60),
                          (40, 120, 100, 30), (140, 120, 100, 30)])
        table = next(node for node in root.iter() if checker.local_name(node) == "table")
        self.assertEqual([r["bbox"] for r in records],
                         [(p.x, p.y, p.width, p.height) for p in checker.table_cell_paints(table, 0)])
        items = checker.check(records, slides, "", checker.DEFAULT_CONTRAST_GATE)[0]
        self.assertEqual([i["text"] for i in items if i["verdict"] == "FAIL"], ["MERGED"])
        self.assertEqual(checker.lint_level(items[0]), "error")

    def test_rowspan_and_colspan_skip_compact_occupied_ranges(self):
        for span in (2, 1000000000):
            xml = (f'<table width="{span + 1}" height="100"><colgroup><col span="{span + 1}" width="1"/></colgroup>'
                   f'<tr height="20"><td rowspan="1000000000" colspan="{span}"/><td/></tr>'
                   '<tr height="30"/><tr height="50"><td/></tr></table>')
            paints = list(checker.table_cell_paints(checker.ET.fromstring(xml), 0))
            self.assertEqual([(p.x, p.y, p.width, p.height) for p in paints],
                             [(0, 0, span, 100), (span, 0, 1, 20), (span, 50, 1, 50)])

    def parse_table(self, cols, spans=(1, 1, 1), rows=1, panel_x=620):
        cells = "".join(
            f'<td colspan="{span}"><fill><fillColor color="rgba(255,255,255,1)"/></fill>'
            '<content color="rgba(31,35,41,1)" fontSize="16"><p>CELL</p></content></td>'
            for span in spans
        )
        xml = (
            '<presentation xmlns="https://www.larkoffice.com/sml/2.0"><slide><data>'
            '<table topLeftX="56" topLeftY="156" width="540" height="160">'
            f'<colgroup>{cols}</colgroup>' + f'<tr height="32">{cells}</tr>' * rows
            + '</table>'
            f'<shape topLeftX="{panel_x}" topLeftY="140" width="284" height="190">'
            '<fill><fillColor color="rgba(244,244,244,1)"/></fill></shape>'
            '</data></slide></presentation>'
        )
        root = checker.ET.fromstring(xml)
        records, slides = checker.parse_xml_root(root)
        table = next(node for node in root.iter() if checker.local_name(node) == "table")
        paints = list(checker.table_cell_paints(table, 0))
        self.assertEqual([record["bbox"] for record in records],
                         [(paint.x, paint.y, paint.width, paint.height) for paint in paints])
        return records, slides

    def test_five_row_table_does_not_sample_adjacent_panel(self):
        expanded = self.parse_table('<col width="160"/><col width="190"/><col width="190"/>', rows=5)
        compressed = self.parse_table('<col width="160"/><col width="190" span="2"/>', rows=5)
        self.assertEqual([record["bbox"] for record in compressed[0]][2::3],
                         [(406, 156 + row * 32, 190, 32) for row in range(5)])
        self.assertEqual(compressed, expanded)
        results, failed = checker.check(*compressed, "", checker.DEFAULT_CONTRAST_GATE)
        self.assertFalse(failed)
        self.assertEqual(checker.summary(results)["issue_count"], 0)

    def test_span_positions_and_cell_colspan_match_expanded_columns(self):
        for before, after in ((0, 2), (1, 1), (2, 0)):
            for spans in ((1, 1, 1, 1), (2, 1, 1), (1, 2, 1)):
                with self.subTest(before=before, spans=spans):
                    prefix, suffix = '<col width="30.5"/>' * before, '<col width="40.5"/>' * after
                    expanded = self.parse_table(prefix + '<col width="50.5"/>' * 2 + suffix, spans)
                    compressed = self.parse_table(prefix + '<col width="50.5" span="2"/>' + suffix, spans)
                    self.assertEqual(compressed, expanded)
                    left = checker.check(*expanded, "", checker.DEFAULT_CONTRAST_GATE)[0]
                    right = checker.check(*compressed, "", checker.DEFAULT_CONTRAST_GATE)[0]
                    self.assertEqual(left, right)
                    self.assertEqual([checker.lint_level(item) for item in left],
                                     [checker.lint_level(item) for item in right])

    def test_default_and_invalid_spans_preserve_single_column_behavior(self):
        expected = self.parse_table('<col width="160"/><col width="190"/><col/>')
        for span in ('1', '1.0', '0', '-1', '1.5', 'nan', 'inf', '-inf', 'invalid'):
            with self.subTest(span=span):
                self.assertEqual(self.parse_table(f'<col width="160" span="{span}"/><col width="190"/><col/>'), expected)
        self.assertEqual([record["bbox"][2] for record in expected[0]], [160, 190, 190])
        self.assertEqual([record["bbox"][2] for record in self.parse_table('')[0]], [180, 180, 180])
        self.assertEqual([record["bbox"][2] for record in self.parse_table('<col width="0"/>')[0]], [180, 180, 180])

    def test_large_span_uses_compact_ranges(self):
        table = checker.ET.fromstring('<table width="540"><colgroup><col width="0.5" span="1000000000"/></colgroup>'
                                     '<tr><td colspan="1000000000"/></tr></table>')
        widths = checker.table_column_widths(table)
        self.assertEqual(len(widths), 1)
        self.assertEqual(checker.table_cell_width(widths, 999999998, 2, 540), 1)
        self.assertEqual(checker.table_cell_width(widths, 999999999, 2, 540), 0.5)
        self.assertEqual(checker.table_cell_width(widths, 1000000000, 1, 540), 540)

    def test_real_panel_overlap_still_fails_and_moving_it_clears_issue(self):
        cols = '<col width="160"/><col width="190" span="2"/>'
        results, failed = checker.check(*self.parse_table(cols, rows=5, panel_x=410), "", checker.DEFAULT_CONTRAST_GATE)
        self.assertTrue(failed)
        self.assertEqual(checker.summary(results)["issue_count"], 5)
        self.assertTrue(all(item["verdict"] == "FAIL" for item in results[2::3]))
        self.assertFalse(checker.check(*self.parse_table(cols, rows=5), "", checker.DEFAULT_CONTRAST_GATE)[1])


class ContrastBackgroundRegressionTest(unittest.TestCase):
    def check_xml(self, content):
        xml = ('<presentation xmlns="https://www.larkoffice.com/sml/2.0" width="960" height="540">'
               '<slide><data>' + content + '</data></slide></presentation>')
        return checker.check(*checker.parse_xml_root(checker.ET.fromstring(xml)), '', 2.25)[0]

    def test_cell_fill_survives_text_highlight(self):
        for highlight, expected in ((None, (24, 40, 65)), (0, (24, 40, 65)),
                                    (0.2, (70, 83, 103)), (1, (255, 255, 255))):
            for inline in (False, True):
                with self.subTest(highlight=highlight, inline=inline):
                    attr = '' if highlight is None else f' backgroundColor="rgba(255,255,255,{highlight})"'
                    body = f'<p><span{attr}>LABEL</span></p>' if inline else '<p>LABEL</p>'
                    text_attr = '' if inline else attr
                    xml = ('<table width="240" height="70" topLeftX="40" topLeftY="40">'
                           '<colgroup><col width="240"/></colgroup><tr height="70"><td>'
                           '<fill><fillColor color="rgba(24,40,65,1)"/></fill>'
                           f'<content fontSize="22" color="rgba(255,255,255,1)"{text_attr}>{body}'
                           '</content></td></tr></table>')
                    item = self.check_xml(xml)[0]
                    self.assertEqual(checker.parse_color(item['effective_bg_color'])[:3], expected)
                    self.assertEqual(item['verdict'], 'FAIL' if highlight == 1 else 'PASS')

    def test_transparent_highlight_does_not_hide_black_on_black(self):
        item = self.check_xml(
            '<table width="240" height="70" topLeftX="40" topLeftY="40">'
            '<colgroup><col width="240"/></colgroup><tr height="70"><td>'
            '<fill><fillColor color="rgba(0,0,0,1)"/></fill>'
            '<content color="rgba(0,0,0,1)" backgroundColor="rgba(255,255,255,0)">'
            '<p>BODY TEXT</p></content></td></tr></table>')[0]
        self.assertEqual(item['contrast'], 1)
        self.assertEqual(item['verdict'], 'FAIL')


class EqualStyleSamplingTest(unittest.TestCase):
    def test_split_runs_use_same_bounds_without_changing_records(self):
        for content in ('<p><span>目</span><span>录</span></p>', '<p>目<span>录</span></p>',
                        '<p><u>目</u><u>录</u></p>', '<p><strong>目</strong><strong>录</strong></p>'):
            for panel_x in (180, 64):
                with self.subTest(content=content, panel_x=panel_x):
                    xml = title_sampling_xml(panel_x)
                    start, end = xml.index('<p>'), xml.index('</p>') + 4
                    xml = xml[:start] + content + xml[end:]
                    records, slides = checker.parse_xml_root(checker.ET.fromstring(xml))
                    self.assertEqual([r['text'] for r in records], ['目', '录'])
                    self.assertTrue(all('sample_bbox' in r for r in records))
                    items = checker.check(records, slides, '', 2.25)[0]
                    self.assertEqual([i['verdict'] for i in items], ['PASS', 'PASS'] if panel_x == 180 else ['FAIL', 'FAIL'])

    def test_different_visual_styles_keep_original_sampling(self):
        for attr in ('color="rgba(210,210,210,1)"', 'backgroundColor="rgba(0,0,0,1)"',
                     'fontSize="20"', 'fontFamily="Arial"', 'bold="false"', 'italic="true"'):
            xml = title_sampling_xml().replace('目录', f'目<span {attr}>录</span>')
            records, _ = checker.parse_xml_root(checker.ET.fromstring(xml))
            with self.subTest(attr=attr):
                self.assertTrue(all('sample_bbox' not in r for r in records))

    def test_fragment_spaces_are_measured_without_rewriting(self):
        xml = title_sampling_xml().replace('目录', '<span>目 </span><span>录</span>')
        records, _ = checker.parse_xml_root(checker.ET.fromstring(xml))
        self.assertTrue(all('sample_bbox' in r for r in records))
        self.assertGreater(records[0]['sample_bbox'][2], 71.4)
        self.assertEqual([r['text'] for r in records], ['目', '录'])


class TableSizeResolutionTest(unittest.TestCase):
    def table(self, columns, row_heights=(30, 30, 30), width=240, height=90, cell_count=3):
        dims = ('' if width is None else f' width="{width}"') + ('' if height is None else f' height="{height}"')
        rows = ''.join('<tr' + ('' if h is None else f' height="{h}"') + '>' + '<td/>' * cell_count + '</tr>'
                       for h in row_heights)
        return checker.ET.fromstring(f'<table{dims}><colgroup>{columns}</colgroup>{rows}</table>')

    def test_column_sizes_follow_renderer_allocation(self):
        cases = [('<col/><col/><col/>', 240, [80, 80, 80]),
                 ('<col width="80"/>', 240, [80, 80, 80]),
                 ('<col width="50" span="3"/>', 240, [80, 80, 80]),
                 ('<col/>', None, [110, 110, 110]),
                 ('<col width="100"/><col width="300"/><col width="100"/>', 200, [100, 300, 100]),
                 ('<col width="10"/><col span="2"/>', 101, [10, 46, 45]),
                 ('<col width="300"/><col span="2"/>', 200, [300, 110, 110]),
                 ('<col width="1"/><col width="2"/><col width="3"/>', 100, [17, 33, 50]),
                 ('<col span="6" width="80"/>', 240, [80, 80, 80])]
        for columns, width, expected in cases:
            with self.subTest(columns=columns, width=width):
                boxes = [b for _, b in checker.table_cell_bboxes(self.table(columns, width=width))][:3]
                self.assertEqual([b[2] for b in boxes], expected)
                self.assertEqual([b[0] for b in boxes], [0, expected[0], sum(expected[:2])])

    def test_rows_use_same_allocation_with_rowspan(self):
        for heights, total, expected in [((None, None, None), 90, [30, 30, 30]),
                                        ((30, None, None), 101, [30, 36, 35]),
                                        ((20, 20, 20), 90, [30, 30, 30]),
                                        ((None, None, None), None, [37, 37, 37])]:
            t = self.table('<col width="80" span="3"/>', heights, height=total)
            boxes = [b for _, b in checker.table_cell_bboxes(t)]
            with self.subTest(heights=heights, total=total):
                self.assertEqual([b[3] for b in boxes[::3]], expected)
                self.assertEqual([b[1] for b in boxes[::3]], [0, expected[0], sum(expected[:2])])

    def test_large_missing_span_stays_compact(self):
        t = checker.ET.fromstring('<table width="2000000000" height="30"><colgroup>'
                                 '<col span="1000000000"/></colgroup><tr height="30">'
                                 '<td colspan="999999999"/><td/></tr></table>')
        widths = checker.table_column_widths(t)
        self.assertLessEqual(len(widths), 2)
        self.assertEqual([b for _, b in checker.table_cell_bboxes(t)],
                         [(0, 0, 1999999998, 30), (1999999998, 0, 2, 30)])


class LinearGradientCoordinatesTest(unittest.TestCase):
    def result(self, angle, x, y, *, own=False, transform='', stops=None, width=960, height=540):
        gradient = f'linear-gradient({angle}deg,{stops or "rgba(0,0,0,1) 0%,rgba(255,255,255,1) 100%"})'
        fill = f'<fill><fillColor color="{gradient}"/></fill>'
        shape_fill = fill if own else ''
        style = '' if own else '<style>' + fill + '</style>'
        xml = (f'<presentation xmlns="https://www.larkoffice.com/sml/2.0" width="{width}" height="{height}">'
               f'<slide>{style}<data><shape type="text" topLeftX="{x}" topLeftY="{y}" width="260" height="65" {transform}>'
               f'{shape_fill}<content color="rgba(24,32,44,1)" fontSize="26" wrap="false">'
               '<p>页面渐变</p></content></shape></data></slide></presentation>')
        records, slides = checker.parse_xml_root(checker.ET.fromstring(xml))
        return records, slides, checker.check(records, slides, '', 2.25)[0][0]

    def test_vertical_page_gradient_is_independent_of_x(self):
        items = [self.result(0, x, 150)[2] for x in (40, 340, 640)]
        self.assertTrue(all(i['verdict'] == 'PASS' for i in items))
        self.assertEqual(len({i['effective_bg_color'] for i in items}), 1)
        self.assertEqual(checker.parse_color(items[0]['effective_bg_color'])[:3], (169, 169, 169))

    def test_page_gradient_uses_declared_dimensions(self):
        records, slides, _ = self.result(90, 40, 150, width=1920, height=1080)
        bg, *_ = checker.background_at(records[0], slides[1], 960, 500)
        self.assertEqual(bg[:3], (128, 128, 128))

    def test_own_gradient_samples_text_region(self):
        stops = 'rgba(255,255,255,1) 0%,rgba(255,255,255,1) 45%,rgba(0,0,0,1) 46%,rgba(0,0,0,1) 100%'
        _, _, item = self.result(90, 40, 140, own=True, stops=stops)
        self.assertEqual(item['verdict'], 'PASS')
        self.assertEqual(item['effective_bg_color'], 'rgba(255, 255, 255, 1)')

    def test_all_angles_match_known_projection(self):
        for angle, point, expected in [(0, (20, 10), 230), (90, (20, 10), 26),
                                       (180, (20, 10), 26), (270, (20, 10), 230),
                                       (45, (150, 50), 170), (135, (150, 50), 170)]:
            records, slides, _ = self.result(angle, 40, 40, width=200, height=100)
            bg, *_ = checker.background_at(records[0], slides[1], *point)
            with self.subTest(angle=angle):
                self.assertEqual(bg[:3], (expected,) * 3)

    def test_transformed_own_gradient_keeps_legacy_midpoint(self):
        for transform in ('rotation="15"', 'flipX="true"', 'flipY="true"'):
            _, _, item = self.result(0, 40, 40, own=True, transform=transform)
            self.assertEqual(item['effective_bg_color'], 'rgba(128, 128, 128, 1)')

    def test_explicit_end_stops_extend_to_box_edges(self):
        stops = 'rgba(20,20,20,1) 20%,rgba(220,220,220,1) 80%'
        records, slides, _ = self.result(90, 40, 40, stops=stops)
        for point, expected in (((0, 100), 20), ((960, 100), 220)):
            bg, *_ = checker.background_at(records[0], slides[1], *point)
            self.assertEqual(bg[:3], (expected,) * 3)

    def test_background_and_overlay_use_vertical_coordinates(self):
        gradient = 'linear-gradient(0deg,rgba(0,0,0,1) 0%,rgba(255,255,255,1) 100%)'
        paint = checker.Paint(40, 40, 200, 100, gradient, 0)
        self.assertEqual(paint.at(80, 40), (255, 255, 255, 1))
        self.assertEqual(paint.at(80, 140), (0, 0, 0, 1))
        # A later solid-colour gradient paints over both the foreground and background.
        records, slides, _ = self.result(90, 40, 40)
        slides[1]['paints'].append(checker.Paint(40, 40, 260, 65, gradient, 99))
        item = checker.check(records, slides, '', 2.25)[0][0]
        self.assertEqual(item['contrast'], 1)
        self.assertTrue(item['worst_sample_covered'])

    def test_varying_alpha_is_still_composited(self):
        gradient = 'linear-gradient(0deg,rgba(0,0,0,0) 0%,rgba(0,0,0,1) 100%)'
        paint = checker.Paint(0, 0, 200, 100, gradient, 0, alpha=0.5)
        self.assertEqual(paint.at(30, 50), (0, 0, 0, 0.25))
        self.assertEqual(checker.over(paint.at(30, 50), (255, 255, 255, 1)), (191, 191, 191, 1))

    def test_radial_missing_positions_and_disabled_transform_use_legacy_path(self):
        for color in ('radial-gradient(circle at 50% 50%,rgba(0,0,0,1) 0%,rgba(255,255,255,1) 100%)',
                      'linear-gradient(0deg,rgba(0,0,0,1),rgba(255,255,255,1))'):
            self.assertEqual(checker.Paint(0, 0, 200, 100, color, 0).at(50, 99),
                             checker.color_or_gradient(color, .25))
        color = 'linear-gradient(0deg,rgba(0,0,0,1) 0%,rgba(255,255,255,1) 100%)'
        self.assertEqual(checker.Paint(0, 0, 200, 100, color, 0, gradient_geometry=False).at(50, 99),
                         checker.color_or_gradient(color, .25))

    def test_repeated_stops_keep_existing_interpolation(self):
        stops = 'rgba(0,0,0,1) 0%,rgba(0,0,0,1) 50%,rgba(255,255,255,1) 50%,rgba(255,255,255,1) 100%'
        records, slides, _ = self.result(0, 40, 40, stops=stops)
        bg, *_ = checker.background_at(records[0], slides[1], 720, 100)
        self.assertEqual(bg[:3], (255, 255, 255))

    def test_real_low_contrast_on_dark_gradient_still_fails(self):
        _, _, item = self.result(0, 40, 460)
        self.assertEqual(item['verdict'], 'FAIL')


class ThemeAndUnknownBackgroundTest(unittest.TestCase):
    def check(self, data, style='', theme=''):
        xml = ('<presentation xmlns="https://www.larkoffice.com/sml/2.0" width="960" height="540">'
               f'{theme}<slide>{style}<data>{data}</data></slide></presentation>')
        records, slides = checker.parse_xml_root(checker.ET.fromstring(xml))
        return checker.check(records, slides, '', checker.DEFAULT_CONTRAST_GATE)[0]

    def text(self, attrs='', body='BODY', x=40, y=40):
        return (f'<shape type="text" topLeftX="{x}" topLeftY="{y}" width="160" height="50">'
                f'<content fontSize="20" {attrs}><p>{body}</p></content></shape>')

    def test_text_type_uses_its_own_supplied_theme_color(self):
        colors = {'title': 'rgba(120,30,40,1)', 'headline': 'rgba(30,120,40,1)',
                  'sub-headline': 'rgba(30,40,120,1)', 'body': 'rgba(31,35,41,1)',
                  'caption': 'rgba(155,158,162,1)'}
        theme = '<theme><textStyles>' + ''.join(f'<{tag} fontColor="{color}"/>' for tag, color in colors.items()) + '</textStyles></theme>'
        for tag, color in colors.items():
            with self.subTest(tag=tag):
                style = f'<style><fill><fillColor color="{color}"/></fill></style>'
                item = self.check(self.text(f'textType="{tag}"'), style, theme)[0]
                self.assertEqual(checker.parse_color(item['fg_color']), checker.parse_color(color))
                self.assertEqual(item['contrast'], 1)
                self.assertEqual(item['verdict'], 'FAIL')

    def test_explicit_styles_override_theme_and_missing_theme_keeps_fallback(self):
        theme = '<theme><textStyles><body fontColor="rgba(50,60,70,1)"/><caption fontColor="rgba(200,200,200,1)"/></textStyles></theme>'
        item = self.check(self.text('textType="caption" color="rgba(0,0,0,1)"'), theme=theme)[0]
        self.assertEqual(checker.parse_color(item['fg_color'])[:3], (0, 0, 0))
        item = self.check(self.text('textType="caption"', '<span color="rgba(0,0,0,1)">BODY</span>'), theme=theme)[0]
        self.assertEqual(checker.parse_color(item['fg_color'])[:3], (0, 0, 0))
        self.assertEqual(checker.parse_color(self.check(self.text('textType="caption"'))[0]['fg_color'])[:3], (31, 35, 41))
        theme = '<theme><textStyles><body fontColor="rgba(50,60,70,1)"/></textStyles></theme>'
        self.assertEqual(checker.parse_color(self.check(self.text('textType="caption"'), theme=theme)[0]['fg_color'])[:3], (50, 60, 70))

    def test_table_retains_its_existing_fallback_and_explicit_color(self):
        theme = '<theme><textStyles><caption fontColor="rgba(155,158,162,1)"/></textStyles></theme>'
        table = ('<table topLeftX="40" topLeftY="40" width="200" height="60"><colgroup><col width="200"/></colgroup>'
                 '<tr height="60"><td><content textType="caption"><p>CAPTION</p></content></td></tr></table>')
        self.assertEqual(checker.parse_color(self.check(table, theme=theme)[0]['fg_color'])[:3], (31, 35, 41))
        explicit = table.replace('textType="caption"', 'textType="caption" color="rgba(0,0,0,1)"')
        self.assertEqual(checker.parse_color(self.check(explicit, theme=theme)[0]['fg_color'])[:3], (0, 0, 0))

    def test_image_fill_skips_only_intersecting_text_before_or_after_it(self):
        image = ('<shape type="rect" topLeftX="40" topLeftY="40" width="200" height="100">'
                 '<fill><fillImg src="opaque-reference"/></fill></shape>')
        label = self.text('color="rgba(255,255,255,1)"')
        unrelated = self.text('color="rgba(255,255,255,1)"', x=500)
        for data in (image + label + unrelated, label + image + unrelated):
            with self.subTest(order=data.index('<fill>')):
                items = self.check(data)
                self.assertEqual([i['verdict'] for i in items], ['SKIP', 'FAIL'])
                self.assertIsNone(items[0]['contrast'])
                self.assertIn('image', items[0]['reason'].lower())

    def test_page_shape_and_cell_image_fills_are_unknown(self):
        fill = '<fill><fillImg src="opaque-reference"/></fill>'
        items = [self.check(self.text(), '<style>' + fill + '</style>')[0],
                 self.check('<shape type="text" topLeftX="40" topLeftY="40" width="200" height="100">' + fill +
                            '<content><p>BODY</p></content></shape>')[0],
                 self.check('<table topLeftX="40" topLeftY="40" width="200" height="80"><colgroup><col width="200"/></colgroup>'
                            '<tr height="80"><td>' + fill + '<content><p>BODY</p></content></td></tr></table>')[0]]
        self.assertEqual([i['verdict'] for i in items], ['SKIP'] * 3)

    def test_invisible_image_fill_does_not_exempt_low_contrast(self):
        for shape_alpha, fill_alpha in ((0, 1), (1, 0)):
            image = (f'<shape type="rect" alpha="{shape_alpha}" topLeftX="40" topLeftY="40" width="200" height="100">'
                     f'<fill><fillImg src="opaque-reference" alpha="{fill_alpha}"/></fill></shape>')
            item = self.check(image + self.text('color="rgba(255,255,255,1)"'))[0]
            self.assertEqual(item['verdict'], 'FAIL')
        item = self.check(self.text('color="rgba(255,255,255,1)"'),
                          '<style><fill><fillImg src="opaque-reference" alpha="0"/></fill></style>')[0]
        self.assertEqual(item['verdict'], 'FAIL')

    def test_svg_uses_bounds_without_reading_its_paint(self):
        for alpha in (0, 1):
            svg = (f'<embed alpha="{alpha}" topLeftX="40" topLeftY="40" width="200" height="100">'
                   '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100"><rect width="200" height="100" fill="black"/></svg></embed>')
            text = self.text('color="rgba(255,255,255,1)"')
            for data in (svg + text, text + svg):
                item = self.check(data)[0]
                self.assertEqual(item['verdict'], 'SKIP' if alpha else 'FAIL')
                if alpha:
                    self.assertIsNone(item['contrast'])
                    self.assertIn('svg', item['reason'].lower())
            self.assertEqual(self.check(svg + self.text('color="rgba(255,255,255,1)"', x=500))[0]['verdict'], 'FAIL')

    def test_non_text_shape_retains_its_existing_color_fallback(self):
        theme = '<theme><textStyles><caption fontColor="rgba(155,158,162,1)"/></textStyles></theme>'
        shape = self.text('textType="caption"').replace('type="text"', 'type="rect"')
        self.assertEqual(checker.parse_color(self.check(shape, theme=theme)[0]['fg_color'])[:3], (31, 35, 41))

    def test_transparent_unsupported_shape_keeps_existing_calculation(self):
        shape = ('<shape type="custom" topLeftX="40" topLeftY="40" width="200" height="100">'
                 '<fill><fillColor color="rgba(0,0,0,0)"/></fill></shape>')
        self.assertEqual(self.check(shape + self.text('color="rgba(255,255,255,1)"'))[0]['verdict'], 'FAIL')
        gradient = 'linear-gradient(90deg,rgba(0,0,0,1) 0%,rgba(0,0,0,0) 50%,rgba(0,0,0,0) 100%)'
        self.assertEqual(self.check(shape.replace('rgba(0,0,0,0)', gradient) + self.text())[0]['verdict'], 'FAIL')

    def test_opaque_layer_above_image_keeps_accepted_skip_boundary(self):
        image = ('<shape type="rect" topLeftX="40" topLeftY="40" width="200" height="100">'
                 '<fill><fillImg src="opaque-reference"/></fill></shape>')
        cover = image.replace('<fillImg src="opaque-reference"/>', '<fillColor color="rgba(0,0,0,1)"/>')
        self.assertEqual(self.check(image + cover + self.text())[0]['verdict'], 'SKIP')

    def test_small_svg_between_samples_still_marks_intersecting_text_unknown(self):
        svg = ('<embed topLeftX="45" topLeftY="45" width="5" height="35">'
               '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 5 35"><rect width="5" height="35"/></svg></embed>')
        self.assertEqual(self.check(svg + self.text())[0]['verdict'], 'SKIP')


class SimplePaintGeometryTest(unittest.TestCase):
    def parse_paint(self, shape):
        xml = '<presentation><slide><data>' + shape + '</data></slide></presentation>'
        return checker.parse_xml_root(checker.ET.fromstring(xml))[1][1]['paints'][0]

    def shape(self, kind, attrs=''):
        return (f'<shape type="{kind}" topLeftX="10" topLeftY="20" width="200" height="100" {attrs}>'
                '<fill><fillColor color="rgba(0,0,0,1)"/></fill></shape>')

    def test_default_shapes_exclude_empty_corners_and_keep_centres(self):
        for kind in ('ellipse', 'triangle', 'diamond'):
            paint = self.parse_paint(self.shape(kind))
            with self.subTest(kind=kind):
                self.assertFalse(paint.covers(15, 25))
                self.assertTrue(paint.covers(110, 70))
                self.assertFalse(paint.covers(0, 0))
                self.assertTrue(paint.covers(110, 20))
        self.assertTrue(self.parse_paint(self.shape('rect')).covers(15, 25))

    def test_solid_butt_line_uses_segment_and_width(self):
        paint = self.parse_paint('<line startX="10" startY="20" endX="210" endY="120">'
                                 '<border color="rgba(0,0,0,1)" width="4"/></line>')
        self.assertTrue(paint.covers(110, 70))
        self.assertFalse(paint.covers(20, 100))
        self.assertFalse(paint.covers(8, 19))
        self.assertTrue(paint.covers(110, 71))
        self.assertFalse(paint.covers(110, 75))
        reverse = self.parse_paint('<line startX="210" startY="120" endX="10" endY="20">'
                                  '<border color="rgba(0,0,0,1)" width="4"/></line>')
        self.assertEqual([paint.covers(*p) for p in [(20,100),(110,70),(110,75)]],
                         [reverse.covers(*p) for p in [(20,100),(110,70),(110,75)]])

    def test_empty_corner_uses_underlying_page_but_real_colour_collision_fails(self):
        helper = ThemeAndUnknownBackgroundTest()
        for kind in ('triangle', 'diamond', 'ellipse'):
            for foreground, x, y in [('rgba(0,0,0,1)', 10, 20), ('rgba(0,0,0,1)', 90, 60)]:
                label = (f'<shape type="text" topLeftX="{x}" topLeftY="{y}" width="20" height="15">'
                         f'<content color="{foreground}" fontSize="10"><p>AB</p></content></shape>')
                item = helper.check(self.shape(kind) + label)[0]
                self.assertEqual(item['verdict'], 'PASS' if x == 10 else 'FAIL')

    def test_unsupported_shape_or_line_preserves_existing_detection(self):
        helper = ThemeAndUnknownBackgroundTest()
        shapes = [self.shape('triangle', 'presetHandlers="20000"'), self.shape('triangle', 'rotation="45"'),
                  self.shape('custom', 'path="M0 0L200 0L200 100Z"'),
                  '<polyline topLeftX="10" topLeftY="20" width="200" height="100"><border color="rgba(0,0,0,1)"/></polyline>',
                  '<line startX="10" startY="20" endX="210" endY="120"><border color="rgba(0,0,0,1)" dashArray="dash"/></line>']
        for shape in shapes:
            with self.subTest(shape=shape[:80]):
                items = helper.check(shape + helper.text() + helper.text('color="rgba(255,255,255,1)"', x=500))
                self.assertEqual([i['verdict'] for i in items], ['FAIL', 'FAIL'])

    def test_arrow_line_keeps_legacy_bounding_box(self):
        helper = ThemeAndUnknownBackgroundTest()
        line = ('<line startX="10" startY="20" endX="210" endY="120">'
                '<border color="rgba(0,0,0,1)"/><endArrow type="triangle"/></line>')
        self.assertEqual(helper.check(line + helper.text())[0]['verdict'], 'FAIL')

    def test_rounded_dark_background_retains_true_low_contrast_failure(self):
        helper = ThemeAndUnknownBackgroundTest()
        background = self.shape('round-rect', 'presetHandlers="16"')
        item = helper.check(background + helper.text('color="rgba(0,0,0,1)"'))[0]
        self.assertEqual(item['verdict'], 'FAIL')
        self.assertEqual(item['contrast'], 1)
        self.assertEqual(checker.lint_level(item), 'error')

    def test_rotated_white_shape_does_not_skip_clear_neighbour(self):
        helper = ThemeAndUnknownBackgroundTest()
        background = self.shape('rect', 'rotation="15"').replace('rgba(0,0,0,1)', 'rgba(255,255,255,1)')
        item = helper.check(background + helper.text())[0]
        self.assertEqual(item['verdict'], 'PASS')
        self.assertGreater(item['contrast'], 10)

    def test_rotated_unknown_svg_uses_conservative_rotated_bounds(self):
        helper = ThemeAndUnknownBackgroundTest()
        svg = ('<embed rotation="90" topLeftX="10" topLeftY="20" width="200" height="10">'
               '<svg xmlns="http://www.w3.org/2000/svg"><rect width="200" height="10"/></svg></embed>')
        self.assertEqual(helper.check(svg + helper.text(x=95, y=70))[0]['verdict'], 'SKIP')


if __name__ == "__main__":
    unittest.main()
