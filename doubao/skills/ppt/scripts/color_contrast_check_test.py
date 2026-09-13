from __future__ import annotations

import sys
import io
import unittest
from unittest import mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import color_contrast_check as checker


class ContrastMathTest(unittest.TestCase):
    def check_xml(self, xml: str, threshold: float = 4.5) -> tuple[list[dict], bool]:
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "slide.xml"
            path.write_text(xml, encoding="utf-8")
            records, slides = checker.parse_xml(str(path))
        return checker.check(records, slides, "", threshold)

    def test_alpha_is_composited(self) -> None:
        self.assertLess(checker.contrast(checker.over((0, 0, 0, .25), (255, 255, 255, 1))[:3], (255, 255, 255)), 4.5)

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
        self.assertFalse(checker.is_connector_label("Residual risk: APAC evening saturation remains under watch.", (0, 0, 495, 40)))
        self.assertTrue(checker.is_dark_gradient_annotation((32, 45, 48, 1), 2.81, True))
        self.assertFalse(checker.is_dark_gradient_annotation((32, 45, 48, 1), 2.1, True))

    def test_gradient_keeps_its_light_end(self) -> None:
        light = checker.color_or_gradient("linear-gradient(90deg,rgba(24,32,38,1) 0%,rgba(251,249,239,1) 100%)", 1)
        self.assertGreater(checker.luminance(light[:3]), .9)

    def test_single_stop_gradient_is_a_solid_rgba_color(self) -> None:
        color = checker.color_or_gradient("linear-gradient(90deg,rgba(12,34,56,1) 50%)", .5)
        self.assertEqual(color, (12, 34, 56, 1.0))

    def test_float_geometry_and_plain_text_are_parsed(self) -> None:
        xml = '''<presentation xmlns="https://www.larkoffice.com/sml/2.0"><slide id="p1"><style><fill><fillColor color="rgba(255,255,255,1)"/></fill></style><data><shape topLeftX="10.5" topLeftY="20.5" width="200.5" height="60.5" type="text"><content color="rgba(205,202,191,1)" fontSize="16"><p>PLAIN_TEXT</p></content></shape></data></slide></presentation>'''
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "slide.xml"; path.write_text(xml, encoding="utf-8")
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
            '</shape></data></slide></presentation>'
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
        self.assertEqual(checker.lint_level({"verdict": "FAIL", "contrast": 1.79, "required_contrast": 2.25, "complex_background": False, "source": "shape"}), "error")
        self.assertEqual(checker.lint_level({"verdict": "FAIL", "contrast": 1.80, "required_contrast": 2.25, "complex_background": False, "source": "shape"}), "warning")
        self.assertEqual(checker.lint_level({"verdict": "FAIL", "contrast": 2.0, "required_contrast": 2.25, "complex_background": False, "source": "shape"}), "warning")
        # The item-specific gate keeps --threshold and complex-background gates aligned.
        self.assertEqual(checker.lint_level({"verdict": "FAIL", "contrast": 2.39, "required_contrast": 3.0, "complex_background": False, "source": "shape"}), "error")
        self.assertEqual(checker.lint_level({"verdict": "FAIL", "contrast": 2.40, "required_contrast": 3.0, "complex_background": False, "source": "shape"}), "warning")
        self.assertEqual(checker.lint_level({"verdict": "FAIL", "contrast": 1.4, "required_contrast": 2.25, "complex_background": True, "source": "shape"}), "warning")
        self.assertEqual(checker.lint_level({"verdict": "FAIL", "contrast": 1.4, "required_contrast": 2.25, "complex_background": False, "source": "polyline"}), "warning")

    def ghost_level(self, text, font_size, color, shape_alpha=None) -> str:
        return checker.lint_level({
            "verdict": "FAIL", "contrast": 1.4, "complex_background": False, "source": "shape",
            "text": text, "font_size": font_size, "fg_color": color, "shape_alpha": shape_alpha,
        })

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
            '</data></slide></presentation>'
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
            '</data></slide></presentation>'
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
            '</data></slide></presentation>'
        )
        results, has_fail = self.check_xml(xml)
        self.assertTrue(has_fail)
        self.assertEqual(results[0]["verdict"], "FAIL")
        self.assertTrue(results[0]["complex_background"])
        self.assertNotEqual(results[0]["effective_bg_color"], "rgba(0, 0, 0, 1)")

    def test_partial_background_paint_is_warning_not_blocking(self) -> None:
        """A bar touching one sample in a wide text box needs visual review."""
        xml = (
            '<presentation xmlns="https://www.larkoffice.com/sml/2.0"><slide id="p1">'
            '<style><fill><fillColor color="rgba(255,255,255,1)"/></fill></style><data>'
            '<shape id="accent" type="rect" topLeftX="180" topLeftY="100" width="90" height="60">'
            '<fill><fillColor color="rgba(90,115,55,1)"/></fill></shape>'
            '<shape id="label" type="text" topLeftX="100" topLeftY="100" width="400" height="60">'
            '<content color="rgba(0,90,60,1)" fontSize="32"><p>江门</p></content></shape>'
            '</data></slide></presentation>'
        )
        results, has_fail = self.check_xml(xml)
        self.assertTrue(has_fail)
        self.assertEqual(results[0]["verdict"], "FAIL")
        self.assertTrue(results[0]["complex_background"])
        self.assertEqual(results[0]["worst_sample"]["x"], 200.0)
        self.assertEqual(checker.lint_level(results[0]), "warning")

    def test_two_sample_background_paint_keeps_severe_failure_blocking(self) -> None:
        """A paint behind most samples is a deterministic background, not decoration."""
        xml = (
            '<presentation xmlns="https://www.larkoffice.com/sml/2.0"><slide id="p1">'
            '<style><fill><fillColor color="rgba(255,255,255,1)"/></fill></style><data>'
            '<shape id="card" type="rect" topLeftX="180" topLeftY="100" width="150" height="60">'
            '<fill><fillColor color="rgba(90,115,55,1)"/></fill></shape>'
            '<shape id="label" type="text" topLeftX="100" topLeftY="100" width="400" height="60">'
            '<content color="rgba(0,90,60,1)" fontSize="32"><p>江门</p></content></shape>'
            '</data></slide></presentation>'
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
            '</data></slide></presentation>'
        )
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "slide.xml"
            path.write_text(xml, encoding="utf-8")
            with mock.patch.object(sys, "argv", ["color_contrast_check.py", "--xml", str(path), "--format", "json"]):
                with mock.patch("sys.stdout", new_callable=io.StringIO):
                    self.assertEqual(checker.main(), 0)

    def test_later_overlay_changes_the_visible_contrast(self) -> None:
        xml = '''<presentation xmlns="https://www.larkoffice.com/sml/2.0"><slide id="p1"><style><fill><fillColor color="rgba(255,255,255,1)"/></fill></style><data><shape topLeftX="0" topLeftY="0" width="400" height="200"><fill><fillColor color="rgba(35,45,42,1)"/></fill></shape><shape topLeftX="20" topLeftY="40" width="300" height="60" type="text"><content color="rgba(255,255,255,1)" fontSize="28"><p>OVERLAY</p></content></shape><shape topLeftX="0" topLeftY="0" width="400" height="200"><fill><fillColor color="rgba(255,255,255,.72)"/></fill></shape></data></slide></presentation>'''
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "slide.xml"; path.write_text(xml, encoding="utf-8")
            records, slides = checker.parse_xml(str(path))
        result, has_fail = checker.check(records, slides, "", 4.5)
        self.assertTrue(has_fail)
        self.assertEqual(result[0]["verdict"], "FAIL")

    def test_percentage_pattern_background_keeps_white_text_readable(self) -> None:
        xml = '''<presentation xmlns="https://www.larkoffice.com/sml/2.0"><slide id="p1"><style><fill><fillPattern type="pct90" foregroundColor="rgba(192,0,0,1)" backgroundColor="rgba(255,255,255,1)" alpha="1"/></fill></style><data><shape topLeftX="0" topLeftY="0" width="400" height="100" type="text"><content color="rgba(255,255,255,1)" fontSize="32"><p>WHITE_ON_RED_PATTERN</p></content></shape></data></slide></presentation>'''
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "slide.xml"; path.write_text(xml, encoding="utf-8")
            records, slides = checker.parse_xml(str(path))
        result, has_fail = checker.check(records, slides, "", 4.5)
        self.assertFalse(has_fail)
        self.assertEqual(result[0]["verdict"], "PASS")

    def test_transparent_text_background_does_not_mask_parent_shape(self) -> None:
        xml = '''<presentation xmlns="https://www.larkoffice.com/sml/2.0"><slide id="p1"><style><fill><fillColor color="rgba(255,255,255,1)"/></fill></style><data><shape topLeftX="0" topLeftY="0" width="400" height="200"><fill><fillColor color="rgba(44,89,38,1)"/></fill></shape><shape topLeftX="20" topLeftY="40" width="300" height="60" type="text"><content color="rgba(255,255,255,1)" backgroundColor="rgba(255,255,255,0)" fontSize="20"><p>WHITE_ON_GREEN</p></content></shape></data></slide></presentation>'''
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "slide.xml"; path.write_text(xml, encoding="utf-8")
            records, slides = checker.parse_xml(str(path))
        result, has_fail = checker.check(records, slides, "", 4.5)
        self.assertFalse(has_fail)
        self.assertEqual(result[0]["verdict"], "PASS")

    def test_icon_and_connector_backgrounds_are_checked(self) -> None:
        xml = '''<presentation xmlns="https://www.larkoffice.com/sml/2.0"><slide id="p1"><style><fill><fillColor color="rgba(255,255,255,1)"/></fill></style><data><icon iconType="iconpark/Charts/chart-line.svg" topLeftX="20" topLeftY="20" width="240" height="100"><fill><fillColor color="rgba(46,125,50,1)"/></fill></icon><shape topLeftX="20" topLeftY="20" width="240" height="100" type="text"><content color="rgba(66,165,75,1)" fontSize="16"><p>ICON_BACKED</p></content></shape><line startX="20" startY="190" endX="260" endY="190"><border color="rgba(15,23,42,1)" width="80"/></line><shape topLeftX="20" topLeftY="150" width="240" height="80" type="text"><content color="rgba(30,41,59,1)" fontSize="16"><p>LINE_BACKED</p></content></shape></data></slide></presentation>'''
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "slide.xml"; path.write_text(xml, encoding="utf-8")
            records, slides = checker.parse_xml(str(path))
        results, has_fail = checker.check(records, slides, "", 4.5)
        self.assertTrue(has_fail)
        self.assertEqual([result["verdict"] for result in results], ["FAIL", "FAIL"])

    def test_table_and_chart_backgrounds_apply_to_overlaid_text(self) -> None:
        xml = '''<presentation xmlns="https://www.larkoffice.com/sml/2.0"><slide id="p1"><style><fill><fillColor color="rgba(255,255,255,1)"/></fill></style><data><table topLeftX="20" topLeftY="20" width="240" height="90"><colgroup><col width="240"/></colgroup><tr height="90"><td><fill><fillColor color="rgba(226,232,240,1)"/></fill></td></tr></table><shape topLeftX="20" topLeftY="20" width="240" height="90" type="text"><content color="rgba(203,213,225,1)" fontSize="16"><p>TABLE_BACKED</p></content></shape><chart topLeftX="20" topLeftY="150" width="240" height="90"><chartBackground color="rgba(191,219,254,1)"/></chart><shape topLeftX="20" topLeftY="150" width="240" height="90" type="text"><content color="rgba(147,197,253,1)" fontSize="16"><p>CHART_BACKED</p></content></shape></data></slide></presentation>'''
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "slide.xml"; path.write_text(xml, encoding="utf-8")
            records, slides = checker.parse_xml(str(path))
        results, has_fail = checker.check(records, slides, "", 4.5)
        self.assertTrue(has_fail)
        self.assertEqual([result["verdict"] for result in results], ["FAIL", "FAIL"])

    def test_image_backed_text_is_excluded_without_a_screenshot(self) -> None:
        xml = '''<presentation xmlns="https://www.larkoffice.com/sml/2.0"><slide id="p1"><style><fill><fillColor color="rgba(255,255,255,1)"/></fill></style><data><img topLeftX="0" topLeftY="0" width="400" height="200"/><shape topLeftX="20" topLeftY="40" width="300" height="60" type="text"><content color="rgba(255,255,255,1)" fontSize="16"><p>BODY_COPY</p></content></shape></data></slide></presentation>'''
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "slide.xml"; path.write_text(xml, encoding="utf-8")
            records, slides = checker.parse_xml(str(path))
        result, has_fail = checker.check(records, slides, "", 4.5)
        self.assertFalse(has_fail)
        self.assertEqual(result[0]["verdict"], "SKIP")
        self.assertEqual(result[0]["reason"], "image-backed text excluded")

    def test_image_backed_text_is_excluded_even_with_an_unreadable_file(self) -> None:
        import tempfile
        xml = '''<presentation xmlns="https://www.larkoffice.com/sml/2.0"><slide id="p1"><style><fill><fillColor color="rgba(255,255,255,1)"/></fill></style><data><img topLeftX="0" topLeftY="0" width="400" height="200"/><shape topLeftX="20" topLeftY="40" width="300" height="60" type="text"><content color="rgba(255,255,255,1)" fontSize="16"><p>IMAGE_TEXT</p></content></shape></data></slide></presentation>'''
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "slide.xml"; path.write_text(xml, encoding="utf-8")
            bad = Path(directory) / "deck_p001_p1.jpg"; bad.write_bytes(b"not an image")
            records, slides = checker.parse_xml(str(path))
            results, has_fail = checker.check(records, slides, directory, 4.5)
        self.assertFalse(has_fail)
        self.assertEqual(results[0]["verdict"], "SKIP")
        self.assertEqual(results[0]["reason"], "image-backed text excluded")

    def test_three_stop_gradient_uses_its_middle_stop(self) -> None:
        gradient = "linear-gradient(90deg,rgba(255,255,255,1) 0%,rgba(0,0,0,1) 50%,rgba(255,255,255,1) 100%)"
        self.assertEqual(checker.color_or_gradient(gradient, .5), (0, 0, 0, 1.0))

    def test_unsupported_pattern_is_skipped_instead_of_falling_back_to_page_fill(self) -> None:
        xml = '''<presentation xmlns="https://www.larkoffice.com/sml/2.0"><slide id="p1"><style><fill><fillColor color="rgba(15,23,42,1)"/></fill></style><data><shape topLeftX="0" topLeftY="0" width="400" height="200"><fill><fillPattern type="diagCross" foregroundColor="rgba(255,255,255,1)" backgroundColor="rgba(0,0,0,1)"/></fill></shape><shape topLeftX="20" topLeftY="40" width="300" height="60" type="text"><content color="rgba(226,232,240,1)" fontSize="16"><p>UNSUPPORTED_PATTERN</p></content></shape></data></slide></presentation>'''
        results, has_fail = self.check_xml(xml)
        self.assertFalse(has_fail)
        self.assertEqual(results[0]["verdict"], "SKIP")
        self.assertEqual(results[0]["reason"], "unsupported background pattern")

    def test_polyline_background_is_checked(self) -> None:
        xml = '''<presentation xmlns="https://www.larkoffice.com/sml/2.0"><slide id="p1"><style><fill><fillColor color="rgba(255,255,255,1)"/></fill></style><data><polyline topLeftX="20" topLeftY="40" width="300" height="60"><border color="rgba(203,213,225,1)" width="80"/></polyline><shape topLeftX="20" topLeftY="40" width="300" height="60" type="text"><content color="rgba(191,219,254,1)" fontSize="16"><p>POLYLINE_BACKED</p></content></shape></data></slide></presentation>'''
        results, has_fail = self.check_xml(xml)
        self.assertTrue(has_fail)
        self.assertEqual(results[0]["verdict"], "FAIL")

    def test_native_chart_title_label_and_legend_are_all_checked(self) -> None:
        xml = '''<presentation xmlns="https://www.larkoffice.com/sml/2.0"><slide id="p1"><style><fill><fillColor color="rgba(255,255,255,1)"/></fill></style><data><chart topLeftX="20" topLeftY="20" width="400" height="220"><chartTitle color="rgba(147,197,253,1)" fontSize="16">CHART_TITLE</chartTitle><chartPlotArea><chartPlot type="column"><chartLabel color="rgba(147,197,253,1)" fontSize="11">CHART_LABEL</chartLabel></chartPlot></chartPlotArea><chartLegend color="rgba(147,197,253,1)" fontSize="11">CHART_LEGEND</chartLegend><chartStyle><chartBackground color="rgba(191,219,254,1)"/></chartStyle></chart></data></slide></presentation>'''
        results, has_fail = self.check_xml(xml)
        self.assertTrue(has_fail)
        self.assertEqual([item["text"] for item in results], ["CHART_TITLE", "CHART_LABEL", "CHART_LEGEND"])
        self.assertEqual([item["verdict"] for item in results], ["FAIL", "FAIL", "FAIL"])

    def test_xml_large_text_uses_three_to_one_threshold(self) -> None:
        xml = '''<presentation xmlns="https://www.larkoffice.com/sml/2.0"><slide id="p1"><style><fill><fillColor color="rgba(255,255,255,1)"/></fill></style><data><shape topLeftX="0" topLeftY="0" width="400" height="200"><fill><fillColor color="rgba(255,255,255,1)"/></fill></shape><shape topLeftX="20" topLeftY="40" width="300" height="40" type="text"><content color="rgba(142,142,142,1)" fontSize="16"><p>SMALL</p></content></shape><shape topLeftX="20" topLeftY="110" width="300" height="50" type="text"><content color="rgba(142,142,142,1)" fontSize="24"><p>LARGE</p></content></shape></data></slide></presentation>'''
        results, has_fail = self.check_xml(xml)
        self.assertTrue(has_fail)
        self.assertEqual([item["verdict"] for item in results], ["FAIL", "PASS"])

    def test_table_colspan_resolves_the_low_contrast_cell_only(self) -> None:
        xml = '''<presentation xmlns="https://www.larkoffice.com/sml/2.0"><slide id="p1"><style><fill><fillColor color="rgba(255,255,255,1)"/></fill></style><data><table topLeftX="20" topLeftY="20" width="400" height="100"><colgroup><col width="100"/><col width="150"/><col width="150"/></colgroup><tr height="100"><td><fill><fillColor color="rgba(15,23,42,1)"/></fill><content color="rgba(255,255,255,1)" fontSize="16"><p>GOOD</p></content></td><td colspan="2"><fill><fillColor color="rgba(226,232,240,1)"/></fill><content color="rgba(203,213,225,1)" fontSize="16"><p>BAD</p></content></td></tr></table></data></slide></presentation>'''
        results, has_fail = self.check_xml(xml)
        self.assertTrue(has_fail)
        self.assertEqual([item["verdict"] for item in results], ["PASS", "FAIL"])

if __name__ == "__main__":
    unittest.main()
