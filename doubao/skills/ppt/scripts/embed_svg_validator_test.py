# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import unittest

import xml_lint


SML_NAMESPACE = "https://www.larkoffice.com/sml/2.0"


class SxsdEmbedSyntaxTest(unittest.TestCase):
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
    ) -> dict[str, object]:
        for issue in issues:
            if issue.get("code") != code:
                continue
            if path is not None and issue.get("path") != path:
                continue
            return issue
        self.fail(f"missing issue code={code!r} path={path!r}: {issues!r}")

    def test_accepts_embedded_svg_namespace_wildcard(self) -> None:
        issues = self.validate(
            f"""
            <slide xmlns="{SML_NAMESPACE}">
              <data>
                <embed id="visual" topLeftX="440" topLeftY="120" width="440" height="280">
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 440 280">
                    <rect width="440" height="280" fill="rgb(24, 36, 61)"/>
                  </svg>
                </embed>
              </data>
            </slide>
            """
        )

        self.assertEqual(issues, [])

    def test_rejects_embed_without_svg_child(self) -> None:
        issues = self.validate(
            f"""
            <slide xmlns="{SML_NAMESPACE}">
              <data><embed topLeftX="440" topLeftY="120" width="440" height="280"/></data>
            </slide>
            """
        )

        self.assert_issue(issues, "sxsd_missing_required_child", path="slide/data/embed")

    def test_rejects_embed_with_multiple_svg_children(self) -> None:
        issues = self.validate(
            f"""
            <slide xmlns="{SML_NAMESPACE}">
              <data>
                <embed topLeftX="440" topLeftY="120" width="440" height="280">
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 440 280"/>
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 440 280"/>
                </embed>
              </data>
            </slide>
            """
        )

        self.assert_issue(issues, "sxsd_too_many_children", path="slide/data/embed/svg")

    def test_rejects_embed_child_outside_svg_namespace(self) -> None:
        issues = self.validate(
            f"""
            <slide xmlns="{SML_NAMESPACE}">
              <data>
                <embed topLeftX="440" topLeftY="120" width="440" height="280">
                  <svg viewBox="0 0 440 280"/>
                </embed>
              </data>
            </slide>
            """
        )

        self.assert_issue(issues, "sxsd_unsupported_tag", path="slide/data/embed/svg")
        self.assert_issue(issues, "sxsd_missing_required_child", path="slide/data/embed")


class EmbeddedSvgLintTest(unittest.TestCase):
    def lint(self, svg_body: str, *, embed_attrs: str = "") -> dict:
        return xml_lint.lint_xml(
            f"""
            <slide xmlns="{SML_NAMESPACE}">
              <data>
                <embed id="visual" topLeftX="440" topLeftY="120" width="440" height="280" {embed_attrs}>
                  {svg_body}
                </embed>
              </data>
            </slide>
            """
        )

    def issue_codes(self, result: dict) -> list[str]:
        return [issue["code"] for slide in result["slides"] for issue in slide["issues"]]

    def test_accepts_self_contained_static_svg(self) -> None:
        result = self.lint(
            """
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 440 280">
              <defs>
                <linearGradient id="glow"><stop offset="0" stop-color="white"/></linearGradient>
              </defs>
              <rect width="440" height="280" fill="url(#glow)"/>
              <text x="220" y="140">局部 SVG</text>
            </svg>
            """
        )

        self.assertEqual(result["summary"]["error_count"], 0)
        self.assertNotIn("blank_slide", self.issue_codes(result))

    def test_rejects_missing_and_invalid_viewbox(self) -> None:
        missing = self.lint('<svg xmlns="http://www.w3.org/2000/svg"><rect width="10" height="10"/></svg>')
        invalid = self.lint('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 -1 20"/>')

        self.assertIn("embed_svg_missing_required_attr", self.issue_codes(missing))
        self.assertIn("embed_svg_invalid_viewbox", self.issue_codes(invalid))

    def test_rejects_forbidden_svg_content_and_external_references(self) -> None:
        result = self.lint(
            """
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 440 280">
              <script>bad()</script>
              <foreignObject x="0" y="0" width="10" height="10"/>
              <use href="https://example.com/asset.svg#icon"/>
              <rect style="fill:red" onclick="bad()" width="10" height="10"/>
            </svg>
            """
        )

        codes = self.issue_codes(result)
        self.assertIn("embed_svg_forbidden_element", codes)
        self.assertIn("embed_svg_external_reference", codes)
        self.assertIn("embed_svg_forbidden_attribute", codes)

    def test_accepts_allowlisted_smil_and_rejects_event_animation(self) -> None:
        accepted = self.lint(
            """
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 440 280">
              <defs><path id="motion" d="M0 0 L100 0"/></defs>
              <g>
                <animateTransform attributeName="transform" type="translate"
                  values="0 0;8 0;0 0" dur="2.8s" begin=".2s" repeatCount="indefinite"/>
              </g>
              <circle r="4">
                <animateMotion dur="3.2s" repeatCount="indefinite"><mpath href="#motion"/></animateMotion>
              </circle>
            </svg>
            """
        )
        rejected = self.lint(
            """
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 440 280">
              <g><animateTransform attributeName="transform" type="translate"
                values="0 0;8 0" dur="fast" begin="click" repeatCount="2"/></g>
            </svg>
            """
        )

        self.assertEqual(accepted["summary"]["error_count"], 0)
        self.assertIn("embed_svg_invalid_animation", self.issue_codes(rejected))

    def test_reports_renderer_sensitive_svg_as_visual_review_warning(self) -> None:
        result = self.lint(
            """
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 440 280">
              <defs><filter id="blur"><feGaussianBlur stdDeviation="12"/></filter></defs>
              <circle cx="220" cy="140" r="80" filter="url(#blur)"/>
            </svg>
            """
        )

        self.assertEqual(result["summary"]["error_count"], 0)
        self.assertIn("embed_svg_visual_review_required", self.issue_codes(result))

    def test_rejects_unbounded_filter_region_in_animated_svg(self) -> None:
        result = self.lint(
            """
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 440 280">
              <defs><filter id="blur"><feGaussianBlur stdDeviation="12"/></filter></defs>
              <g filter="url(#blur)">
                <animateTransform attributeName="transform" type="translate"
                  values="0 0;8 0;0 0" dur="2.8s" begin="0s" repeatCount="indefinite"/>
                <circle cx="220" cy="140" r="80"/>
              </g>
            </svg>
            """
        )

        self.assertIn("embed_svg_unbounded_filter_region", self.issue_codes(result))

    def test_rejects_filter_clip_animation_render_subtree(self) -> None:
        result = self.lint(
            """
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 440 280">
              <defs>
                <filter id="blur" filterUnits="userSpaceOnUse" x="-40" y="-40" width="520" height="360">
                  <feGaussianBlur stdDeviation="12"/>
                </filter>
                <clipPath id="crop"><rect width="440" height="280"/></clipPath>
              </defs>
              <g filter="url(#blur)" clip-path="url(#crop)">
                <g>
                  <animateTransform attributeName="transform" type="translate"
                    values="0 0;8 0;0 0" dur="2.8s" begin="0s" repeatCount="indefinite"/>
                  <circle cx="220" cy="140" r="80"/>
                </g>
              </g>
            </svg>
            """
        )

        self.assertIn("embed_svg_filter_clip_animation_conflict", self.issue_codes(result))

    def test_accepts_platform_safe_filtered_animation_layers(self) -> None:
        result = self.lint(
            """
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 440 280">
              <defs>
                <filter id="blur" filterUnits="userSpaceOnUse" x="-40" y="-40" width="520" height="360">
                  <feGaussianBlur stdDeviation="12"/>
                </filter>
                <clipPath id="crop"><rect width="440" height="280"/></clipPath>
              </defs>
              <circle cx="220" cy="140" r="80" filter="url(#blur)"/>
              <g clip-path="url(#crop)">
                <g>
                  <animateTransform attributeName="transform" type="translate"
                    values="0 0;8 0;0 0" dur="2.8s" begin="0s" repeatCount="indefinite"/>
                  <circle cx="220" cy="140" r="40"/>
                </g>
              </g>
            </svg>
            """
        )

        codes = self.issue_codes(result)
        self.assertEqual(result["summary"]["error_count"], 0)
        self.assertNotIn("embed_svg_unbounded_filter_region", codes)
        self.assertNotIn("embed_svg_filter_clip_animation_conflict", codes)

    def test_reports_embed_out_of_canvas(self) -> None:
        result = xml_lint.lint_xml(
            f"""
            <slide xmlns="{SML_NAMESPACE}">
              <data>
                <embed id="visual" topLeftX="800" topLeftY="400" width="300" height="200">
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 200"/>
                </embed>
              </data>
            </slide>
            """
        )

        self.assertIn("embed_out_of_canvas", self.issue_codes(result))

    def test_reports_overlapping_svg_text_and_duplicate_primitives(self) -> None:
        result = self.lint(
            """
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 440 280">
              <text x="220" y="140" font-size="18" text-anchor="middle">第一层</text>
              <text x="220" y="140" font-size="18" text-anchor="middle">第二层</text>
              <circle cx="80" cy="80" r="12"/>
              <circle cx="80" cy="80" r="12"/>
            </svg>
            """
        )

        issues = [
            issue
            for slide in result["slides"]
            for issue in slide["issues"]
            if issue["code"] == "embed_svg_bbox_overlap"
        ]
        self.assertEqual(len(issues), 2)
        self.assertEqual(
            {issue["measurement"]["primitive_kind"] for issue in issues},
            {"text", "circle"},
        )
        self.assertTrue(all(issue["elements"] == ["visual"] for issue in issues))


class EmbeddedSvgTextContainerOverflowTest(unittest.TestCase):
    """Exercise embed_svg_text_container_overflow across the container kinds it must generalize to.

    A truncated label can sit inside a straight-edged polygon, a circle, or a curved pie/donut
    wedge, and the label itself may be a name or a numeric/percentage annotation. These cases pin
    the positive detections, the negative (fitting) counterparts, and the animated-sector skip.
    """

    def overflow_issues(self, svg_body: str) -> list[dict[str, object]]:
        result = xml_lint.lint_xml(
            f"""
            <slide xmlns="{SML_NAMESPACE}">
              <data>
                <embed id="visual" topLeftX="0" topLeftY="0" width="440" height="280">
                  {svg_body}
                </embed>
              </data>
            </slide>
            """
        )
        return [
            issue
            for slide in result["slides"]
            for issue in slide["issues"]
            if issue["code"] == "embed_svg_text_container_overflow"
        ]

    def test_flags_label_wider_than_polygon_container(self) -> None:
        issues = self.overflow_issues(
            """
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
              <polygon points="60,80 140,80 140,120 60,120" fill="rgb(200,200,200)"/>
              <text x="100" y="104" font-size="14" text-anchor="middle"
                font-family="思源黑体">超长的标签文字</text>
            </svg>
            """
        )

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["measurement"]["container_width_px"], 80.0)
        self.assertGreater(
            issues[0]["measurement"]["text_width_px"],
            issues[0]["measurement"]["container_width_px"],
        )

    def test_flags_label_wider_than_circle_container(self) -> None:
        issues = self.overflow_issues(
            """
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
              <circle cx="100" cy="100" r="22" fill="rgb(50,50,50)"/>
              <text x="100" y="105" font-size="14" text-anchor="middle"
                font-family="思源黑体">环形标签文字</text>
            </svg>
            """
        )

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["measurement"]["container_width_px"], 44.0)

    def test_flags_label_wider_than_rect_container(self) -> None:
        issues = self.overflow_issues(
            """
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
              <rect x="20" y="70" width="100" height="50"
                fill="rgb(245,245,245)" stroke="rgb(80,80,80)"/>
              <text x="28" y="108" font-size="14" font-family="思源黑体">
                全国发生面积4500万亩次
              </text>
            </svg>
            """
        )

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["measurement"]["container_width_px"], 100.0)
        self.assertGreater(
            issues[0]["measurement"]["text_width_px"],
            issues[0]["measurement"]["container_width_px"],
        )

    def test_ignores_viewbox_background_rect_as_text_container(self) -> None:
        issues = self.overflow_issues(
            """
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
              <rect x="0" y="0" width="200" height="200" fill="rgb(245,245,245)"/>
              <text x="100" y="108" font-size="24" text-anchor="middle"
                font-family="思源黑体">背景装饰大标题文字</text>
            </svg>
            """
        )

        self.assertEqual(issues, [])

    def test_ignores_thin_decorative_rect_as_text_container(self) -> None:
        issues = self.overflow_issues(
            """
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
              <rect x="40" y="96" width="120" height="4" fill="rgb(180,180,180)"/>
              <text x="100" y="104" font-size="14" text-anchor="middle"
                font-family="思源黑体">装饰线上的长标签文字</text>
            </svg>
            """
        )

        self.assertEqual(issues, [])

    def test_accepts_label_that_fits_its_polygon_container(self) -> None:
        issues = self.overflow_issues(
            """
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
              <polygon points="40,80 160,80 160,120 40,120" fill="rgb(200,200,200)"/>
              <text x="100" y="104" font-size="14" text-anchor="middle"
                font-family="思源黑体">短标签</text>
            </svg>
            """
        )

        self.assertEqual(issues, [])

    def test_flags_label_truncated_inside_pie_donut_wedge(self) -> None:
        issues = self.overflow_issues(
            """
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400">
              <path d="M 200 60 A 140 140 0 0 1 280.0 85.0 L 240.0 130.0 A 70 70 0 0 0 200 130 Z"
                fill="rgb(40,60,110)"/>
              <text x="215" y="100" font-size="18" font-weight="700" text-anchor="middle"
                font-family="思源黑体">交通出行方向</text>
            </svg>
            """
        )

        self.assertEqual(len(issues), 1)
        measurement = issues[0]["measurement"]
        self.assertIn("sector_room_left_px", measurement)
        self.assertIn("sector_room_right_px", measurement)
        self.assertGreater(measurement["overflow_px"], 10.0)

    def test_flags_numeric_percentage_label_truncated_inside_wedge(self) -> None:
        # A percentage sub-label is judged purely on the sector room it has, exactly like a name
        # label; it is not skipped by category.
        issues = self.overflow_issues(
            """
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400">
              <path d="M 200 60 A 140 140 0 0 1 280.0 85.0 L 240.0 130.0 A 70 70 0 0 0 200 130 Z"
                fill="rgb(40,60,110)"/>
              <text x="215" y="100" font-size="18" font-weight="700" text-anchor="middle"
                font-family="思源黑体">88.8%</text>
            </svg>
            """
        )

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["overlaps"][0]["text"], "88.8%")

    def test_skips_truncation_check_for_animated_wedge(self) -> None:
        issues = self.overflow_issues(
            """
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400">
              <path d="M 200 60 A 140 140 0 0 1 280.0 85.0 L 240.0 130.0 A 70 70 0 0 0 200 130 Z"
                fill="rgb(40,60,110)">
                <animateTransform attributeName="transform" type="rotate" values="0;10;0"
                  dur="2s" begin="0s" repeatCount="indefinite"/>
              </path>
              <text x="215" y="100" font-size="18" font-weight="700" text-anchor="middle"
                font-family="思源黑体">交通出行方向</text>
            </svg>
            """
        )

        self.assertEqual(issues, [])


if __name__ == "__main__":
    unittest.main()
