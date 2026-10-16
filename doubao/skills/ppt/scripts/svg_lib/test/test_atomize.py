"""Atomizer core: SVG input, geometry, paint, paths, markers, borders, merge and robustness."""

import math
import unittest
import xml.etree.ElementTree as ET
import sys
import subprocess
from pathlib import Path
from os import PathLike, fsdecode, fsencode, path as os_path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from copy import deepcopy

SCRIPTS = Path(__file__).resolve().parents[2]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import xml_lint

from ._helpers import SvgTestCase
from ..atomize_svg_to_slide import (
    atomize_svg_to_slide,
    set_mapping,
    merge_atomized_slide,
    convert_path,
    set_min_slide_font_size,
)
from ..atomize_svg_to_slide._config import _CFG
from ..atomize_svg_to_slide._path import _absolute_path_commands, _parse_path_bbox, _sample_svg_arc_points
from ..atomize_svg_to_slide._paint import _get_attr
import json
from ..atomize_svg_to_slide import _publish, native_table
from ..atomize_svg_to_slide._bounds import paint_bounds, path_bounds, svg_bounds
from ..atomize_svg_to_slide._geometry import path_segments
from ..atomize_svg_to_slide._markers import _placements
from ..atomize_svg_to_slide._path import _custom_shape_from_svg_path, _svg_path_to_local_custom_path
from ..atomize_svg_to_slide._publish import _classify, _native_fixes, _prepare

_SML = "{https://www.larkoffice.com/sml/2.0}"


# ====================================================================================================
# Core geometry, SVG input and paint regressions.
# ====================================================================================================


class FilePathInputTest(SvgTestCase):
    class FileReference(PathLike):
        def __init__(self, value):
            self.value = value

        def __fspath__(self):
            return self.value

    def test_file_inputs_match_path_output_errors_and_read_behaviour(self):
        documents = (
            '<svg viewBox="0 0 100 100"><rect x="10" y="20" width="30" height="40" fill="#286A70"/></svg>',
            '<svg viewBox="0 0 100 100"><defs><radialGradient id="paint"><stop offset="0" stop-color="white"/>'
            '<stop offset="1" stop-color="#286A70"/></radialGradient></defs><circle cx="50" cy="50" r="30" fill="url(#paint)"/></svg>',
        )
        with TemporaryDirectory() as directory:
            filename = Path(directory) / "图形 one.svg"
            for document in documents:
                filename.write_text(document, encoding="utf-8")
                for reference in (
                    str(filename),
                    self.FileReference(str(filename)),
                    self.FileReference(fsencode(filename)),
                    os_path.relpath(filename),
                ):
                    with self.subTest(reference=reference, document=document):
                        canonical = Path(fsdecode(reference))
                        expected_report = {}
                        expected = atomize_svg_to_slide(canonical, diagnostics=expected_report)
                        report = {}
                        self.assertEqual(atomize_svg_to_slide(reference, diagnostics=report), expected)
                        self.assertEqual(report, expected_report)
        with TemporaryDirectory() as directory:
            directory = Path(directory)
            invalid_utf8 = directory / "invalid.svg"
            invalid_utf8.write_bytes(b"\xff")
            malformed = directory / "malformed.svg"
            malformed.write_text("<svg>", encoding="utf-8")
            for filename in (directory / "missing.svg", directory, invalid_utf8, malformed):
                try:
                    atomize_svg_to_slide(filename)
                except Exception as original:
                    expected_type, expected_args = type(original), original.args
                    expected_details = (getattr(original, "errno", None), getattr(original, "filename", None))
                else:
                    self.fail("Fixture must fail")
                for reference in (
                    str(filename),
                    self.FileReference(str(filename)),
                    self.FileReference(fsencode(filename)),
                ):
                    with self.subTest(reference=reference):
                        report = {"untouched": True}
                        with self.assertRaises(expected_type) as raised:
                            atomize_svg_to_slide(reference, diagnostics=report)
                        self.assertEqual(raised.exception.args, expected_args)
                        self.assertEqual(
                            (getattr(raised.exception, "errno", None), getattr(raised.exception, "filename", None)),
                            expected_details,
                        )
                        self.assertEqual(report, {"untouched": True})
            for reference in (filename, str(filename), self.FileReference(str(filename))):
                with self.assertRaisesRegex(TypeError, "diagnostics must be a dict or None"):
                    atomize_svg_to_slide(reference, diagnostics=[])
        raw = '<svg viewBox="0 0 100 100"><rect width="20" height="20"/></svg>'
        with patch.object(Path, "read_text", autospec=True, side_effect=FileNotFoundError("not a file")) as read:
            with self.assertRaises(FileNotFoundError):
                atomize_svg_to_slide(raw)
        read.assert_called_once_with(Path(raw), encoding="utf-8")
        original_error = PermissionError("custom path read failure")

        class ExistingPath(type(Path())):
            def read_text(self, encoding=None):
                raise original_error

        with self.assertRaises(PermissionError) as raised:
            atomize_svg_to_slide(ExistingPath("file.svg"))
        self.assertIs(raised.exception, original_error)


class PathMappingTest(SvgTestCase):
    canvas = (100, 100)

    STROKE = 'fill="none" stroke="rgba(24,26,34,0.92)" stroke-width="1.4"'

    def test_stroked_paths_map_to_native_lines_or_custom_curves(self) -> None:
        # Connector regressions: flat open paths must not vanish (zero-height custom bbox), real
        # curves keep their Bezier controls, and arcs/quadratics become cubic custom shapes.
        cases = [
            ("M 10 80 Q 50 20 90 80", "", 0, (" C ",), (" Q ",)),
            ("M 10 50 L 50 50 L 90 50", "", 2, (), ('<shape type="custom"',)),
            ("M 10 50 C 30 50, 70 50, 90 50", "", 2, (), ('<shape type="custom"',)),
            ("M 10 50 C 30 50, 70 50, 90 50", ' stroke-linecap="round"', 1, (), ('<shape type="custom"',)),
            ("M 10 80 C 30 20, 70 60, 90 30", ' stroke-linecap="round"', 0, (" C ",), ("<polyline",)),
            ("M 10 80 C 30 20, 70 20, 90 80", ' stroke-linecap="round"', 0, (" C ",), ()),
            ("M 80 50 A 30 30 0 0 1 50 80", "", 0, (" C ",), (" A ",)),
        ]
        for d, extra, lines, present, absent in cases:
            with self.subTest(d=d, extra=extra):
                xml = self.atomize_body(f'<path d="{d}" {self.STROKE}{extra}/>')
                self.assertNotIn("<embed", xml)
                if d == "M 10 50 C 30 50, 70 50, 90 50" and not extra:
                    self.assertGreaterEqual(xml.count("<line"), lines)
                else:
                    self.assertEqual(xml.count("<line"), lines)
                if not lines:
                    self.assertIn('<shape type="custom"', xml)
                for token in present:
                    self.assertIn(token, xml)
                for token in absent:
                    self.assertNotIn(token, xml)

    def test_dashes_markers_fill_only_borders_and_filters(self) -> None:
        xml = self.atomize_body(
            '<defs><marker id="arr"/></defs>'
            '<line x1="10" y1="10" x2="90" y2="10" '
            'stroke="rgba(24,26,34,0.92)" stroke-width="2" '
            'stroke-linecap="round" stroke-dasharray="5 4" '
            'marker-end="url(#arr)"/>'
        )

        self.assertNotIn("<embed", xml)
        self.assertNotIn("dashArray=", xml)
        self.assertIn(" M ", xml)
        self.assertIn('lineCap="round"', xml)
        self.assertEqual(xml.count('<shape type="custom"'), 2)  # dashed shaft + endpoint
        # A real marker definition: straight dashes are expanded at their real length/phase, the head is a shape.
        xml = self.atomize_body(
            '<defs><marker id="arr" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0L10 5L0 10Z" fill="#181A22"/></marker></defs>'
            '<line x1="10" y1="10" x2="90" y2="10" '
            'stroke="rgba(24,26,34,0.92)" stroke-width="2" '
            'stroke-linecap="round" stroke-dasharray="5 4" '
            'marker-end="url(#arr)"/>'
        )
        self.assertNotIn("<embed", xml)
        self.assertNotIn("dashArray=", xml)
        self.assertIn(" M ", xml)
        self.assertIn('lineCap="round"', xml)
        self.assertIn('<shape type="custom"', xml)
        self.assertNotIn("<endArrow", xml)
        xml = self.atomize_body(
            '<defs><marker id="arr"/></defs>'
            '<path d="M 10 80 L 50 20 L 90 80" fill="none" '
            'stroke="rgba(24,26,34,0.92)" stroke-width="2.6" '
            'stroke-dasharray="5 4" marker-end="url(#arr)" '
            'stroke-linejoin="round" stroke-linecap="round"/>'
        )

        self.assertNotIn("<embed", xml)
        self.assertEqual(xml.count("<line"), 0)
        self.assertIn('<shape type="custom"', xml)
        self.assertNotIn("dashArray=", xml)
        self.assertIn(" M ", xml)
        xml = self.atomize_body(
            '<defs><marker id="arr" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0L10 5L0 10Z" fill="#181A22"/></marker></defs>'
            '<path d="M 10 80 L 50 20 L 90 80" fill="none" '
            'stroke="rgba(24,26,34,0.92)" stroke-width="2.6" '
            'stroke-dasharray="5 4" marker-end="url(#arr)" '
            'stroke-linejoin="round" stroke-linecap="round"/>'
        )
        self.assertNotIn("<embed", xml)
        self.assertEqual(xml.count("<line"), 0)
        self.assertIn('<shape type="custom"', xml)
        self.assertNotIn("dashArray=", xml)
        xml = self.atomize_body(
            '<path d="M 10 80 Q 50 20 90 80 L 90 90 L 10 90 Z" fill="rgba(168,88,42,0.08)" stroke="none"/>'
        )

        self.assertIn('<shape type="custom"', xml)
        self.assertNotIn('color="none"', xml)
        self.assertIn('color="rgba(0,0,0,0)"', xml)
        xml = self.atomize_body(
            '<ellipse cx="50" cy="50" rx="30" ry="15" transform="rotate(-55 50 50)" '
            'fill="rgba(32,120,88,0.160)" stroke="rgba(32,120,88,0.920)" stroke-width="1.8"/>'
        )

        self.assertNotIn("<embed", xml)
        self.assertIn('<shape type="ellipse"', xml)
        self.assertIn('rotation="305"', xml)
        # Native text/shapes cannot express drop-shadow / halo / glow: keep one SVG object with the filter.
        for body in (
            '<text x="50" y="50" font-size="24" font-weight="800" fill="rgba(29,55,89,1)" filter="url(#f)">2,847</text>',
            '<rect x="20" y="20" width="60" height="20" fill="none" stroke="#A35832" stroke-width="1.6" rx="8" '
            'opacity="0.5" filter="url(#f)"/>',
        ):
            with self.subTest(body=body[:5]):
                xml = self.atomize_body('<defs><filter id="f"/></defs>' + body)
                self.assertIn("<embed", xml)
                self.assertIn('filter="url(#f)"', xml)
                self.assertRegex(xml, r'<defs><filter id="f"\s*/></defs>')
        # line 上的 gradient stroke (url(#gradId)) native line 无法表达,
        # 走 embed fallback 保 gradient 引用 · 之前 bug 是直接把 url(#gradId) 塞进 slide border color.
        xml = self.atomize_body(
            '<defs><linearGradient id="steamGrad" x1="0" y1="0" x2="1" y2="0">'
            '<stop offset="0" stop-color="rgba(200,60,60,0.9)"/>'
            '<stop offset="1" stop-color="rgba(200,60,60,0.2)"/>'
            "</linearGradient></defs>"
            '<line x1="10" y1="20" x2="90" y2="20" '
            'stroke="url(#steamGrad)" stroke-width="2.4"/>'
        )

        self.assertIn("<embed", xml)
        self.assertIn('stroke="url(#steamGrad)"', xml)
        self.assertIn("<linearGradient", xml)
        # 关键: slide XML 里不能出现 border color="url(...)" · 那是 bug 情况.
        self.assertNotIn('color="url(', xml)

    def test_stroke_width_scales_with_svg_mapping(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            svg_path = Path(tmp_dir) / "case.svg"
            svg_path.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">'
                '<line x1="20" y1="20" x2="180" y2="20" '
                'stroke="rgba(24,26,34,0.92)" stroke-width="1.6"/>'
                "</svg>",
                encoding="utf-8",
            )
            set_mapping(200, 200, 0, 0, 100, 100)
            xml = atomize_svg_to_slide(svg_path)

        self.assertIn('width="1"', xml)
        self.assertNotIn('width="2"', xml)

    def test_gradient_filtered_path_keeps_gradient_and_filter_in_svg(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            svg_path = Path(tmp_dir) / "case.svg"
            svg_path.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
                '<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">'
                '<stop offset="0%" stop-color="rgba(171,94,84,1)"/>'
                '<stop offset="100%" stop-color="rgba(113,36,46,1)"/>'
                '</linearGradient><filter id="shadow"/></defs>'
                '<path d="M 20 80 L 50 20 L 80 80 Z" fill="url(#g)" '
                'stroke="rgba(255,240,215,0.9)" stroke-width="2" filter="url(#shadow)"/>'
                "</svg>",
                encoding="utf-8",
            )
            set_mapping(100, 100, 0, 0, 100, 100)
            xml = atomize_svg_to_slide(svg_path)

        self.assertIn("<embed", xml)
        self.assertIn('filter="url(#shadow)"', xml)
        self.assertIn('linearGradient id="g"', xml)

    def test_font_family_maps_to_slide(self) -> None:
        # SVG font-family 常见值应映射到 slide 支持字体, 输出 fontFamily 属性.
        for svg_font, expected_slide in [
            ("Georgia, serif", "Georgia"),
            ("JetBrains Mono", "Roboto Mono"),
            ("Inter", "Inter"),
            ("'STIX Two Text', Georgia", "Georgia"),
            ("monospace", "Roboto Mono"),
            ("思源宋体", "思源宋体"),
            ("寒蝉锦书宋", "寒蝉锦书宋"),
            ("'寒蝉锦书宋', serif", "寒蝉锦书宋"),
            ("&quot;寒蝉锦书宋&quot;, serif", "寒蝉锦书宋"),
            ("Nunito, sans-serif", "Nunito"),
            ("Custom Family, Inter", "Custom Family"),
            ("'Custom &amp; Family', serif", "Custom & Family"),
            ("'Custom &quot;Label&quot;', serif", 'Custom "Label"'),
        ]:
            with self.subTest(svg_font=svg_font):
                xml = self.atomize_body(f'<text x="50" y="50" font-size="14" font-family="{svg_font}">Hello</text>')
                content = ET.fromstring(xml).find(".//{*}content")
                self.assertEqual(content.get("fontFamily"), expected_slide)

    def test_font_family_absent_or_generic_defaults_to_chart_sans(self) -> None:
        # 没写 font-family / 通用 sans 时与 chart_split 一致用思源黑体，希腊字母不再落到衬线兜底字体.
        for attr in ("", ' font-family="sans-serif"', ' font-family="system-ui, sans-serif"'):
            with self.subTest(attr=attr):
                xml = self.atomize_body(f'<text x="50" y="50" font-size="14"{attr}>γ ν Δ σ ≈ ±</text>')
                content = ET.fromstring(xml).find(".//{*}content")
                self.assertEqual(content.get("fontFamily"), "思源黑体")
                self.assertEqual("".join(content.itertext()), "γ ν Δ σ ≈ ±")
        saved = _CFG["default_font_family"]
        try:
            _CFG["default_font_family"] = ""
            xml = self.atomize_body('<text x="50" y="50" font-size="14">Plain</text>')
            self.assertNotIn("fontFamily=", xml)
        finally:
            _CFG["default_font_family"] = saved

    def custom_shape(self, xml: str) -> ET.Element:
        shapes = ET.fromstring(xml).findall(f"{_SML}data/{_SML}shape")
        self.assertEqual(len(shapes), 1, xml)
        self.assertEqual(shapes[0].get("type"), "custom")
        return shapes[0]

    def assert_box(self, shape: ET.Element, expected) -> None:
        actual = [float(shape.get(key)) for key in ("topLeftX", "topLeftY", "width", "height")]
        for got, want in zip(actual, expected):
            self.assertAlmostEqual(got, want, delta=0.5, msg=f"{actual} != {expected}")

    def test_arc_shapes_spellings_and_flags(self) -> None:
        cases = {
            "pie": ("M 50 50 L 90 50 A 40 40 0 0 1 50 90 Z", (50, 50, 40, 40)),
            "ring": ("M 90 50 A 40 40 0 0 1 10 50 L 30 50 A 20 20 0 0 0 70 50 Z", (10, 50, 80, 40)),
            "large_arc": ("M 50 10 A 40 40 0 1 1 10 50 L 50 50 Z", (10, 10, 80, 80)),
            # Vertical chord bulging right: the box covers the semicircle, not the chord.
            "vertical_chord": ("M 50 0 A 50 50 0 0 1 50 100 Z", (50, 0, 50, 100)),
        }
        for name, (d, box) in cases.items():
            with self.subTest(name):
                shape = self.custom_shape(self.atomize_body(f'<path d="{d}" fill="#4A7FA3"/>'))
                self.assert_box(shape, box)
                self.assertGreaterEqual(shape.get("path").count(" C "), 1)
        absolute = self.atomize_body(
            '<path d="M 10 50 A 40 40 0 0 1 90 50" fill="none" stroke="#333333" stroke-width="2"/>'
        )
        # Stroked bounds include half the 2px stroke on every side.
        self.assert_box(self.custom_shape(absolute), (8, 8, 84, 44))
        for d in ("M 10 50 a 40 40 0 0 1 80 0", "M10 50A40 40 0 0190 50", "M10,50A40,40,0,0,1,90,50"):
            with self.subTest(d=d):
                spelled = self.atomize_body(f'<path d="{d}" fill="none" stroke="#333333" stroke-width="2"/>')
                self.assertEqual(spelled, absolute)
        commands = _absolute_path_commands("M50 50a10 10 0 11-20-20 10 10 0 0020 20A5 5 30.5 0 1 .5.5")
        self.assertEqual(
            commands,
            [
                ("M", (50.0, 50.0)),
                ("A", (10.0, 10.0, 0.0, 1.0, 1.0, 30.0, 30.0)),
                ("A", (10.0, 10.0, 0.0, 0.0, 0.0, 50.0, 50.0)),
                ("A", (5.0, 5.0, 30.5, 0.0, 1.0, 0.5, 0.5)),
            ],
        )
        for d in ("M0 0A1 1 0 2 0 20 20", "M0 0A1 1 0 1.0 0 20 20", "M0 0A1 1 0 1"):
            with self.subTest(d=d), self.assertRaises(ValueError):
                self.atomize_body(f'<path d="{d}" fill="none" stroke="#333333"/>')


class FillOnlyPathBoundsTest(SvgTestCase):
    canvas = (400, 400)
    arch = "M20 80 C20 0 260 0 260 80 Z"

    def box(self, shape):
        return tuple(float(shape.get(k)) for k in ("topLeftX", "topLeftY", "width", "height"))

    def test_fill_only_paths_have_tight_frames_and_border_parameters(self):
        cases = [
            ("M0 0 H400 V400 H0 Z", (0, 0, 400, 400)),
            ("M0 300 Q200 180 400 300 L400 400 L0 400 Z", (0, 240, 400, 160)),
        ]
        for path, expected in cases:
            with self.subTest(path=path):
                shape = self.convert(f'<path d="{path}" fill="#336699" stroke="none" stroke-width="2.4"/>')[0]
                self.assertEqual(shape.get("type"), "custom")
                self.assertEqual(self.box(shape), expected)
        # Degree-elevated controls remain outside the tight box where needed.

        commands = path_segments(shape.get("path"))
        self.assertEqual(commands[0], ("M", [0, 60]))
        self.assertEqual(commands[1], ("C", [133.33, -20, 266.67, -20, 400, 60]))
        # A degenerate (zero-area) fill path keeps the padded fallback frame.
        shape = self.convert('<path d="M20 40 L260 40" fill="#336699" stroke="none" stroke-width="2.4"/>')[0]
        self.assertEqual(self.box(shape), (17.8, 37.8, 244.4, 4.4))
        cases = [
            ('stroke-width="20"', "rgba(0,0,0,0)", "0"),
            ('stroke="none" stroke-width="20"', "rgba(0,0,0,0)", "0"),
            ('stroke="transparent" stroke-width="20"', "rgba(0,0,0,0)", "0"),
            ('stroke="rgba(255,0,0,0)" stroke-width="20"', "rgba(0,0,0,0)", "0"),
            ('stroke="#ff0000" stroke-opacity="0" stroke-width="20"', "rgba(255,0,0,0.00)", "20"),
            ('stroke="#ff000000" stroke-width="20"', "rgba(255,0,0,0)", "20"),
            ('stroke="#ff0000" stroke-width="0"', "rgb(255,0,0)", "0"),
        ]
        for attrs, color, width in cases:
            with self.subTest(attrs=attrs):
                shape = self.convert(
                    f'<path d="{self.arch}" fill="#336699" fill-opacity="0.5" opacity="0.4" {attrs}/>'
                )[0]
                self.assertEqual(self.box(shape), (20, 20, 240, 60))
                self.assertEqual(shape.get("alpha"), "0.4")
                self.assertEqual(shape.find("{*}fill/{*}fillColor").get("color"), "rgba(51,102,153,0.50)")
                border = shape.find("{*}border")
                self.assertEqual((border.get("color"), border.get("width")), (color, width))
        for attrs in ('stroke="#ff7700" stroke-width="8"', 'stroke="rgba(255,0,0,0.01)" stroke-width="8"'):
            with self.subTest(attrs=attrs):
                shape = self.convert(f'<path d="{self.arch}" fill="#336699" {attrs}/>')[0]
                self.assertEqual(self.box(shape), (15, 15, 250, 70))
                self.assertEqual(shape.find("{*}border").get("width"), "8")

        for paint, width, expected in [
            ("url(#missing)", 2.4, (17.8, 17.8, 244.4, 64.4)),
            ("unresolved-color", 0, (19, 19, 242, 62)),
        ]:
            with self.subTest(paint=paint):
                tag = f'<path d="{self.arch}" fill="#336699" stroke="{paint}" stroke-width="{width}"/>'
                shape = ET.fromstring(
                    _custom_shape_from_svg_path(self.arch, tag, fill="#336699", stroke=paint, stroke_w=width)
                )
                self.assertEqual(self.box(shape), expected)
        set_mapping(400, 400, 50, 75, 800, 600)
        shape = self.convert(f'<path d="{self.arch}" fill="#336699" stroke="none" stroke-width="2.4"/>')[0]
        self.assertEqual(self.box(shape), (90, 105, 480, 90))

        commands = path_segments(shape.get("path"))
        self.assertEqual(commands[0], ("M", [0, 90]))
        self.assertEqual(commands[1], ("C", [0, -30, 480, -30, 480, 90]))


class CurveBoundsTest(SvgTestCase):
    """Selection frames follow the drawn segment, not its parent circle."""

    canvas = (400, 400)
    short_arc = "M 300 200 A 100 100 0 0 1 286.602540378444 250"

    def assertBox(self, actual, expected, delta=1e-7):
        self.assertIsNotNone(actual)
        self.assertEqual(len(actual), len(expected))
        for got, wanted in zip(actual, expected):
            self.assertAlmostEqual(got, wanted, delta=delta)

    def test_curve_bounds_arcs_extrema_and_quadratic_elevation(self):
        from ..svg_drawing import path

        shape = self.convert(
            f'<path d="{self.short_arc}" fill="none" stroke="#112233" stroke-width="2" stroke-linejoin="round"/>'
        )[0]
        self.assertEqual(shape.get("type"), "custom")
        self.assertBox(
            [float(shape.get(k)) for k in ("topLeftX", "topLeftY", "width", "height")], (284.6, 198, 17.4, 54)
        )

        commands = path_segments(shape.get("path"))
        self.assertEqual([op for op, _ in commands], ["M", "C"])
        offset = (float(shape.get("topLeftX")), float(shape.get("topLeftY")))
        world = [[n + offset[i % 2] for i, n in enumerate(v)] for _, v in commands]
        self.assertBox(world[0], (300, 200))
        # Same world-space curve as the uploaded baseline, including controls.
        self.assertBox(world[1], (300, 217.55, 295.38, 234.8, 286.6, 250), delta=0.011)
        x = 200 + 100 * math.cos(math.pi / 6)
        element = ET.fromstring(
            f'<path d="{self.short_arc}" fill="none" stroke="#112233" stroke-width="2" stroke-linejoin="round"/>'
        )
        self.assertBox(path_bounds(self.short_arc), (x, 200, 300, 250))
        self.assertBox(paint_bounds(element), (x, 200, 300 - x, 50))
        self.assertBox(svg_bounds(element), (x - 2, 198, 304 - x, 54))
        geometry = path(self.short_arc, fill="none", stroke="#112233", stroke_width=2, stroke_linejoin="round")
        b = geometry.bounds
        self.assertBox((b.x, b.y, b.width, b.height), (x - 1, 199, 302 - x, 52))
        element.set("stroke-dasharray", "4 3")  # Curved dashes retain local SVG.
        fallback = self.convert(ET.tostring(element, encoding="unicode"))[0]
        self.assertTrue(fallback.tag.endswith("}embed"))
        self.assertBox(
            [float(fallback.get(k)) for k in ("topLeftX", "topLeftY", "width", "height")],
            (x - 2, 198, 304 - x, 54),
            delta=0.011,
        )
        self.assertIn("A 100 100", ET.tostring(fallback, encoding="unicode"))
        hump = 100 * math.sqrt(3) / 6
        cases = [
            ("M 0 0 Q 50 100 100 0", (0, 0, 100, 50)),
            ("M 0 0 C 0 100 100 100 100 0", (0, 0, 100, 75)),
            ("M 0 0 C 100 0 -100 0 0 0", (-hump, 0, hump, 0)),
            ("M 0 0 q 50 100 100 0 t 100 0", (0, -50, 200, 50)),
            ("M 0 0 C 0 100 100 100 100 0 S 200 -100 200 0", (0, -75, 200, 75)),
        ]
        for data, expected in cases:
            with self.subTest(data=data):
                self.assertBox(path_bounds(data), expected)
                x, y, right, bottom = expected
                self.assertBox(paint_bounds(ET.Element("path", d=data)), (x, y, right - x, bottom - y))
        shape = self.convert('<path d="M 0 0 C 0 100 100 100 100 0" fill="none" stroke="#112233" stroke-width="2"/>')[0]
        self.assertBox([float(shape.get(k)) for k in ("topLeftX", "topLeftY", "width", "height")], (-2, -2, 104, 79))
        cubic = path_segments(shape.get("path"))[1][1]
        self.assertGreater(cubic[1], float(shape.get("height")))
        self.assertBox([v - 2 for v in cubic], (0, 100, 100, 100, 100, 0))
        source = "M 10 80 q 40 -60 80 0 t 80 20 s 30 0 50 -20"
        converted = _svg_path_to_local_custom_path(source, origin_x=0, origin_y=0)
        commands = path_segments(converted[0])
        self.assertEqual([op for op, _ in commands], ["M", "C", "C", "C"])
        self.assertBox(commands[1][1], (110 / 3, 40, 190 / 3, 40, 90, 80), delta=0.011)
        self.assertBox(commands[2][1], (350 / 3, 120, 430 / 3, 380 / 3, 170, 100), delta=0.011)
        # SVG S after Q/T starts at the current point; it must not reflect the
        # cubic control introduced while elevating the preceding quadratic.
        self.assertBox(commands[3][1], (170, 100, 200, 100, 220, 80))
        self.assertBox(converted[2], (50, 20))  # original start tangent reference
        self.assertBox(converted[4], (200, 100))
        quadratic = "M 10 80 Q 70 20 130 80"
        cubic = "M 10 80 C 50 40 90 40 130 80"
        gradient = (
            '<defs><linearGradient id="g" x2="0" y2="1">'
            '<stop stop-color="#112233" offset="0"/>'
            '<stop stop-color="#aabbcc" offset="1"/></linearGradient></defs>'
        )
        a = self.convert(gradient + f'<path d="{quadratic} Z" fill="url(#g)"/>')
        b = self.convert(gradient + f'<path d="{cubic} Z" fill="url(#g)"/>')
        self.assertEqual(ET.tostring(a), ET.tostring(b))
        marker = (
            '<defs><marker id="m" viewBox="0 0 10 10" refX="5" refY="5" '
            'markerWidth="10" markerHeight="10" markerUnits="userSpaceOnUse" '
            'orient="auto"><polygon points="1,1 9,5 1,9" fill="#336699"/></marker></defs>'
        )
        style = 'fill="none" stroke="#336699" marker-start="url(#m)" marker-end="url(#m)"'
        a = self.convert(marker + f'<path d="{quadratic}" {style}/>')
        b = self.convert(marker + f'<path d="{cubic}" {style}/>')
        self.assertEqual(len(a), 3)
        self.assertEqual(ET.tostring(a), ET.tostring(b))
        placements = _placements(ET.Element("path", d=quadratic))
        self.assertAlmostEqual(placements[0][2], -45)
        self.assertAlmostEqual(placements[-1][2], 45)
        for large, sweep, expected in [
            (0, 0, (50, 50, 80, 80)),
            (0, 1, (50, 50, 80, 80)),
            (1, 0, (20, 20, 80, 80)),
            (1, 1, (50, 50, 110, 110)),
        ]:
            with self.subTest(large=large, sweep=sweep):
                self.assertBox(path_bounds(f"M 80 50 A 30 30 0 {large} {sweep} 50 80"), expected)
        phi = math.radians(37)

        def point(degrees):
            t = math.radians(degrees)
            return (
                80 + 40 * math.cos(t) * math.cos(phi) - 15 * math.sin(t) * math.sin(phi),
                70 + 40 * math.cos(t) * math.sin(phi) + 15 * math.sin(t) * math.cos(phi),
            )

        # Known ellipse axes independently generate endpoints and sample oracle.
        for first, last in [(10, 140), (140, 10), (10, 300), (300, 10), (350, 390), (10, -20)]:
            with self.subTest(first=first, last=last):
                start, end = point(first), point(last)
                data = (
                    f"M {start[0]:.14g} {start[1]:.14g} A 40 15 37 "
                    f"{int(abs(last - first) > 180)} {int(last > first)} {end[0]:.14g} {end[1]:.14g}"
                )
                b = path_bounds(data)
                samples = [point(first + (last - first) * i / 4000) for i in range(4001)]
                sampled = (
                    min(p[0] for p in samples),
                    min(p[1] for p in samples),
                    max(p[0] for p in samples),
                    max(p[1] for p in samples),
                )
                self.assertBox(b, sampled, delta=1e-5)
                for x, y in samples:
                    self.assertTrue(b[0] - 1e-8 <= x <= b[2] + 1e-8)
                    self.assertTrue(b[1] - 1e-8 <= y <= b[3] + 1e-8)
        self.assertBox(path_bounds("M -20 0 A 10 5 0 0 1 20 0"), (-20, -10, 20, 0))
        self.assertBox(path_bounds("M -20 0 A -10 -5 0 0 0 20 0"), (-20, 0, 20, 10))
        self.assertBox(path_bounds("M 10 20 A 0 50 45 1 1 70 80"), (10, 20, 70, 80))
        self.assertBox(path_bounds("M 10 20 A 50 0 45 1 0 70 80"), (10, 20, 70, 80))
        self.assertIsNone(path_bounds("M 10 20 A 50 50 0 1 1 10 20"))
        self.assertIsNone(path_bounds("M 999 999"))
        self.assertBox(path_bounds("M 999 999 M 10 20 L 30 40 M -999 -999"), (10, 20, 30, 40))
        self.assertBox(path_bounds("M 10 20 L 10 20"), (10, 20, 10, 20))


class InputAndPaintMappingTest(SvgTestCase):
    canvas = (100, 100)

    def gradient(self, attrs="", stops=None, kind="linearGradient"):
        stops = stops or ('<stop offset="0" stop-color="#112233"/><stop offset="1" stop-color="#aabbcc"/>')
        return f'<defs><{kind} id="g" {attrs}>{stops}</{kind}></defs>'

    def atom(self, kind, attrs=""):
        geometry = {
            "circle": 'cx="50" cy="50" r="20"',
            "polygon": 'points="10,20 90,20 50,80"',
            "rect": 'x="10" y="20" width="80" height="60"',
        }[kind]
        return f'<{kind} {geometry} fill="url(#g)" {attrs}/>'

    def fill(self, element):
        return element.find("{*}fill/{*}fillColor").get("color")

    def test_paint_names_xml_spellings_gradients_and_opacities(self):
        for name, literal, expected in (
            ("white", "#ffffff", "rgb(255,255,255)"),
            ("BLACK", "#000000", "rgb(0,0,0)"),
            ("SteelBlue", "#4682b4", "rgb(70,130,180)"),
            ("rebeccapurple", "#663399", "rgb(102,51,153)"),
        ):
            geometry = 'cx="50" cy="50" r="20"'
            reference = self.convert(f'<circle {geometry} fill="{literal}"/>')
            variants = (
                f'<circle {geometry} fill=" {name} "/>',
                f'<circle {geometry} style="fill: {name}"/>',
                f'<style>.paint {{ fill: {name}; }}</style><circle class="paint" {geometry}/>',
            )
            for body in variants:
                with self.subTest(name=name, body=body):
                    result = self.convert(body)
                    self.assertEqual(self.fill(result[0]), expected)
                    self.assertEqual(ET.tostring(result), ET.tostring(reference))
        data = self.convert(
            '<g color="steelblue"><circle cx="50" cy="50" r="20" '
            'fill="currentColor" fill-opacity="0.5" stroke="white" '
            'stroke-width="2" stroke-opacity="0.25"/></g>'
        )
        self.assertEqual(self.fill(data[0]), "rgba(70,130,180,0.50)")
        self.assertEqual(data[0].find("{*}border").get("color"), "rgba(255,255,255,0.25)")
        named = '<stop offset="0" stop-color="white"/><stop offset="1" stop-color="steelblue"/>'
        explicit = '<stop offset="0" stop-color="#ffffff"/><stop offset="1" stop-color="#4682b4"/>'
        actual = self.convert(self.gradient(stops=named) + self.atom("rect"))
        expected = self.convert(self.gradient(stops=explicit) + self.atom("rect"))
        self.assertEqual(ET.tostring(actual), ET.tostring(expected))
        self.assertTrue(self.fill(actual[0]).startswith("linear-gradient("))
        vertical = self.convert(self.gradient('x1="0%" x2="0%" y2="100%"') + self.atom("rect"))[0]
        self.assertEqual(self.fill(vertical), "linear-gradient(180deg,rgba(17,34,51,1) 0%,rgba(170,187,204,1) 100%)")
        docs = [
            '<svg><rect x="10" y="20" width="30" height="40" fill="#112233"/></svg>',
            "<svg><rect x='10' y='20' width='30' height='40' fill='#112233'></rect></svg>",
            '<?xml version="1.0"?><s:svg xmlns:s="http://www.w3.org/2000/svg">'
            '<s:rect x="10" y="20" width="30" height="40" fill="#112233"></s:rect></s:svg>',
        ]
        reference = ET.tostring(self.convert(document=docs[0]))
        for document in docs[1:]:
            self.assertEqual(ET.tostring(self.convert(document=document)), reference)
        data = self.convert(
            '<!-- <rect x="0" y="0" width="99" height="99"/> -->'
            '<metadata><rect x="0" y="0" width="99" height="99"/></metadata>'
            '<defs id="resources"><marker id="arrow"><path d="M 0 0 L 5 5"/></marker></defs>'
            '<circle cx="50" cy="50" r="10" fill="#112233"/>'
        )
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0].get("type"), "ellipse")
        data = self.convert(
            self.atom("circle")
            + '<defs id="unused"><filter id="blur"/></defs>'
            + self.gradient().replace("<defs>", '<defs id="paints">')
        )
        self.assertEqual(len(data), 1)
        self.assertTrue(self.fill(data[0]).startswith("linear-gradient(90deg,"))
        data = self.convert("<g>" + self.gradient() + self.atom("circle") + "</g>")
        self.assertTrue(self.fill(data[0]).startswith("linear-gradient(90deg,"))
        data = self.convert(
            '<text x="10" y="30" font-size="14">甲 &amp; B &lt; C</text>'
            '<rect x="10" y="40" width="20" height="20" fill="#112233"/>'
        )
        self.assertEqual([e.get("type") for e in data], ["text", "rect"])
        self.assertEqual(data[0].find(".//{*}p").text, "甲 & B < C")
        shape = self.convert(document='<svg fill="#112233"><circle cx="20" cy="20" r="10"/></svg>')[0]
        self.assertEqual(self.fill(shape), "rgb(17,34,51)")
        embed = self.convert(
            self.gradient().replace("<defs>", '<defs color-interpolation="linearRGB">') + self.atom("circle")
        )[0]
        self.assertTrue(embed.tag.endswith("}embed"))
        self.assertEqual(embed.find(".//{*}linearGradient").get("color-interpolation"), "linearRGB")
        shape = self.convert('<circle cx="50" cy="50" r="20" fill="#112233"/>')[0]
        self.assertEqual(shape.find("{*}border").get("width"), "0")
        for kind in ("circle", "polygon"):
            shape = self.convert(self.gradient() + self.atom(kind, 'opacity="0.125"'))[0]
            self.assertEqual(shape.get("alpha"), "0.125")
        directions = [
            ("", 90),
            ('x1="100%" x2="0%"', 270),
            ('x1="0" x2="0" y1="0%" y2="100%"', 180),
            ('x1="0" x2="0" y1="1" y2="0"', 0),
        ]
        for kind in ("circle", "polygon"):
            for attrs, angle in directions:
                with self.subTest(kind=kind, angle=angle):
                    shape = self.convert(self.gradient(attrs) + self.atom(kind))[0]
                    self.assertTrue(shape.tag.endswith("}shape"))
                    self.assertEqual(shape.get("type"), "ellipse" if kind == "circle" else "custom")
                    self.assertEqual(
                        self.fill(shape), f"linear-gradient({angle}deg,rgba(17,34,51,1) 0%,rgba(170,187,204,1) 100%)"
                    )
        stops = (
            '<stop offset="0.333333" stop-color="rgba(20,40,60,0.8)" stop-opacity="0.5"/>'
            '<stop offset="100%" stop-color="#aabbcc"/>'
        )
        for kind in ("circle", "polygon"):
            shape = self.convert(self.gradient(stops=stops) + self.atom(kind, 'fill-opacity="0.5" opacity="0.4"'))[0]
            self.assertEqual(shape.get("alpha"), "0.4")
            self.assertIn("rgba(20,40,60,0.2) 33%", self.fill(shape))
            self.assertIn("rgba(170,187,204,0.5) 100%", self.fill(shape))
        polygon = 'points="10,20 90,20 50,80"'
        plain = self.convert(f'<polygon {polygon} fill="#112233"/>')[0]
        native = self.convert(self.gradient() + self.atom("polygon"))[0]
        for key in ("topLeftX", "topLeftY", "width", "height", "path"):
            self.assertEqual(native.get(key), plain.get(key))
        unsupported = [
            'gradientTransform="rotate(20)"',
            'spreadMethod="repeat"',
            'spreadMethod="reflect"',
            'color-interpolation="linearRGB"',
        ]
        for kind in ("circle", "polygon", "rect"):
            for attrs in unsupported:
                with self.subTest(kind=kind, attrs=attrs):
                    embed = self.convert(self.gradient(attrs) + self.atom(kind))[0]
                    self.assertTrue(embed.tag.endswith("}embed"))
                    self.assertIsNotNone(embed.find(".//{*}linearGradient"))
        for kind in ("circle", "polygon"):
            for attrs in ('filter="url(#blur)"', 'stroke="url(#g)" stroke-width="3"'):
                data = self.convert(self.gradient() + '<defs><filter id="blur"/></defs>' + self.atom(kind, attrs))
                self.assertTrue(data[0].tag.endswith("}embed"))
                self.assertIsNotNone(data[0].find(".//{*}" + kind))
        for kind in ("circle", "polygon"):
            radial = self.convert(self.gradient(kind="radialGradient") + self.atom(kind))[0]
            self.assertTrue(radial.tag.endswith("}embed"))
            self.assertIsNotNone(radial.find(".//{*}radialGradient"))
            linked = self.convert(
                '<defs xmlns:xlink="http://www.w3.org/1999/xlink">'
                '<linearGradient id="base"><stop offset="0" stop-color="#112233"/>'
                '<stop offset="1" stop-color="#aabbcc"/></linearGradient>'
                '<linearGradient id="g" xlink:href="#base"/></defs>' + self.atom(kind)
            )[0]
            self.assertTrue(linked.tag.endswith("}embed"))
            self.assertEqual({e.get("id") for e in linked.findall(".//{*}linearGradient")}, {"base", "g"})
        set_mapping(100, 100, -10, -20, 100, 100)
        shape = self.convert(
            document='<svg viewBox="10 20 100 100"><rect x="10" y="20" width="30" height="40" fill="#112233"/></svg>'
        )[0]
        self.assertEqual((shape.get("topLeftX"), shape.get("topLeftY")), ("0.0", "0.0"))

    def test_circle_has_scaled_border_and_separate_opacities(self):
        set_mapping(100, 100, 0, 0, 50, 50)
        shape = self.convert(
            '<circle cx="50" cy="50" r="20" fill="rgba(20,40,60,0.8)" '
            'fill-opacity="0.5" stroke="#112233" stroke-opacity="0.25" '
            'stroke-width="4" opacity="0.4"/>'
        )[0]
        self.assertEqual(shape.get("type"), "ellipse")
        self.assertEqual(shape.get("alpha"), "0.4")
        self.assertEqual((shape.get("topLeftX"), shape.get("width")), ("15.0", "20.0"))
        self.assertEqual(self.fill(shape), "rgba(20,40,60,0.400)")
        self.assertEqual(shape.find("{*}border").get("width"), "2")
        self.assertEqual(shape.find("{*}border").get("color"), "rgba(17,34,51,0.25)")


class PublishCliResponseTest(unittest.TestCase):
    def test_native_table_republishing_and_lint_report_parsing(self):
        import subprocess

        xml = native_table([["组", "值"], ["A", "1"], ["B", "2"]], (40, 100, 300, 90))
        root = ET.fromstring(xml)
        self.assertEqual(root.tag.split("}")[-1], "table")
        rows = root.findall("{*}tr")
        self.assertEqual(len(rows), 3)
        self.assertIsNotNone(rows[0].find("{*}td/{*}borderTop"))
        self.assertIsNotNone(rows[-1].find("{*}td/{*}borderBottom"))
        self.assertIsNone(root.find(".//{*}td[@width]"))
        calls = []

        def fake_run(args, cwd):
            calls.append(args)
            sid = args[args.index("--slide-id") + 1] if "--slide-id" in args else f"s{len(calls)}"
            return {"ok": True, "data": {"slide_id": sid}}

        page = '<slide xmlns="https://www.larkoffice.com/sml/2.0"><data></data></slide>'
        with TemporaryDirectory() as tmp, patch.object(_publish, "_run", side_effect=fake_run):
            first = _publish.publish_slide(page, presentation="D", page=1, screenshot=False, cwd=tmp)
            third = _publish.publish_slide(page, presentation="D", page=3, screenshot=False, cwd=tmp)
            again = _publish.publish_slide(page, presentation="D", page=1, screenshot=False, cwd=tmp)
            second = _publish.publish_slide(page, presentation="D", page=2, screenshot=False, cwd=tmp)
        self.assertEqual(again["slide_id"], first["slide_id"])
        self.assertIn("+update-slide", calls[2])
        self.assertEqual(calls[3][calls[3].index("--before-slide-id") + 1], third["slide_id"])
        self.assertTrue(second["ok"])
        xml, _ = _prepare(
            '<slide xmlns="https://www.larkoffice.com/sml/2.0"><data><shape type="text" topLeftX="0" '
            'topLeftY="0" width="200" height="30"><content><p>Smith & Jones &amp; Co &#169;</p></content>'
            "</shape></data></slide>"
        )
        self.assertIn("Smith &amp; Jones &amp; Co &#169;", xml)
        xml = (
            '<slide xmlns="https://www.larkoffice.com/sml/2.0"><data>'
            '<shape type="text" topLeftX="0" topLeftY="0" width="100" height="20"><content color="#5B544B">'
            '<p wrap="true">t</p></content></shape><embed topLeftX="0" topLeftY="0" width="10" height="10">'
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"><rect fill="#123456" color="#123456"/></svg>'
            '</embed><line startX="0" startY="0" endX="1" endY="1"><border color="#000" width="1.4"/></line></data></slide>'
        )
        out = _native_fixes(xml)
        self.assertIn('<content color="rgb(91,84,75)" wrap="true"><p>t</p>', out)
        self.assertIn('<border color="rgb(0,0,0)" width="1"/>', out)
        self.assertIn('color="#123456"', out)  # SVG paint stays hex
        xml = (
            '<slide xmlns="https://www.larkoffice.com/sml/2.0"><data>'
            '<embed topLeftX="100" topLeftY="100" width="200" height="120"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"/></embed>'
            '<shape type="text" topLeftX="150" topLeftY="140" width="60" height="20"><content><p>nCas9</p></content></shape>'
            '<shape type="text" topLeftX="400" topLeftY="140" width="60" height="20"><content><p>page</p></content></shape>'
            "</data></slide>"
        )
        over = {"code": "text_color_contrast", "elements": ["data/shape[1]"]}
        outside = {"code": "text_color_contrast", "elements": ["data/shape[2]"]}
        ignorable, report = _classify(xml, {0, 1, 2}, [over, outside])
        self.assertEqual((ignorable, report), ([over], [outside]))
        report = json.dumps(
            {"slides": [{"errors": [{"code": "bbox_overlap", "elements": ["slide[1]/data/shape[1]"]}]}]}
        )
        stdout = (
            'Uploading @./a.png ... {"file_token": "x"}\n'
            + json.dumps({"ok": False, "error": {"code": 4000153, "message": report}}, indent=2)
            + "\n"
        )
        done = subprocess.CompletedProcess([], 1, stdout=stdout, stderr="warning: {not json}\n")
        with patch.object(_publish.subprocess, "run", return_value=done):
            res = _publish._run(["slides", "+add-slide"], ".")
        self.assertFalse(res["ok"])
        self.assertEqual(json.loads(res["error"]["message"])["slides"][0]["errors"][0]["code"], "bbox_overlap")


# ====================================================================================================
# Real U-route regression: detached arrow geometry must not force a giant bbox.
# ====================================================================================================

SML = "https://www.larkoffice.com/sml/2.0"


MARKER = '<defs><marker id="arrowGray" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L8,3 L0,6 Z" fill="rgba(115,105,92,1)"/></marker></defs>'


PATH = '<path d="M804 72L804 106L96 106L96 72" fill="none" stroke="rgba(115,105,92,1)" stroke-width="1.4" stroke-dasharray="5 4" marker-end="url(#arrowGray)"/>'


class StraightMarkerRouteTest(unittest.TestCase):
    def setUp(self):
        self.config = dict(_CFG)
        set_mapping(900, 212, 0, 0, 900, 212)
        _CFG["drop_bg"] = False

    def tearDown(self):
        _CFG.clear()
        _CFG.update(self.config)

    def convert(self, body):
        with TemporaryDirectory() as directory:
            source = Path(directory) / "route.svg"
            source.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 212">' + MARKER + body + "</svg>"
            )
            return atomize_svg_to_slide(source)

    def children(self, xml):
        return list(ET.fromstring(xml).find(f"{{{SML}}}data"))

    def test_straight_routes_dashes_fills_curves_and_caps(self):
        nodes = self.children(self.convert(PATH))
        self.assertEqual([node.get("type") for node in nodes], ["custom", "custom"])
        route, arrow = nodes
        # Dashes are expanded at their true phase into one continuous editable route.
        self.assertGreater(route.get("path").count("M "), 10)
        self.assertIsNone(route.find(f"{{{SML}}}border").get("dashArray"))
        self.assertAlmostEqual(float(arrow.get("topLeftX")), 91.8)
        self.assertAlmostEqual(float(arrow.get("topLeftY")), 72)
        self.assertEqual(arrow.get("path"), "M 0 11.2 L 4.2 0 L 8.4 11.2 Z")
        alternate = PATH.replace("M804 72L804 106L96 106L96 72", "M804 72v34H96V72")
        self.assertEqual(self.convert(PATH), self.convert(alternate))
        solid = PATH.replace(' stroke-dasharray="5 4"', "")
        nodes = self.children(self.convert(solid))
        self.assertEqual([node.get("type") for node in nodes], ["custom", "custom"])
        self.assertEqual(nodes[0].get("path"), "M 708 0 L 708 34 L 0 34 L 0 0")
        unmarked = self.children(self.convert(solid.replace(' marker-end="url(#arrowGray)"', "")))
        self.assertEqual(len(unmarked), 1)
        self.assertEqual(unmarked[0].get("type"), "custom")
        route = PATH.replace("rgba(115,105,92,1)", "rgba(115,105,92,0.8)").replace(
            'stroke-width="1.4"', 'stroke-width="1.4" opacity="0.5" stroke-opacity="0.4"'
        )
        before = '<rect x="400" y="82" width="50" height="12" fill="#ffeeaa"/>'
        after = '<rect x="420" y="99" width="80" height="14" fill="#ffffff"/>'
        nodes = self.children(self.convert(before + route + after))
        # Element opacity must apply to the marker as a group; keep one SVG object between the rects.
        self.assertEqual([node.get("type", node.tag.rsplit("}", 1)[-1]) for node in nodes], ["rect", "embed", "rect"])
        self.assertEqual(nodes[-1].get("topLeftX"), "420.0")
        nodes = self.children(self.convert(PATH.replace('fill="none"', 'fill="#ddeeff"')))
        self.assertTrue(all(node.tag.rsplit("}", 1)[-1] == "shape" for node in nodes))
        self.assertEqual(nodes[0].get("type"), "custom")
        self.assertEqual(nodes[0].find(f"{{{SML}}}fill/{{{SML}}}fillColor").get("color"), "rgb(221,238,255)")
        curve = PATH.replace("M804 72L804 106L96 106L96 72", "M804 72C804 160 96 160 96 72").replace(
            ' stroke-dasharray="5 4"', ""
        )
        nodes = self.children(self.convert(curve))
        self.assertEqual(len(nodes), 2)
        self.assertTrue(all(node.get("type") == "custom" for node in nodes))
        self.assertIn(" C ", nodes[0].get("path"))
        for attribute, value, native_attribute in (
            ("stroke-linecap", "round", "lineCap"),
            ("stroke-linecap", "square", "lineCap"),
            ("stroke-linejoin", "round", "lineJoin"),
            ("stroke-linejoin", "bevel", "lineJoin"),
        ):
            with self.subTest(attribute=attribute, value=value):
                route = PATH.replace('stroke-width="1.4"', f'stroke-width="1.4" {attribute}="{value}"')
                nodes = self.children(self.convert(route))
                self.assertEqual(nodes[0].get("type"), "custom")
                self.assertEqual(nodes[0].find(f"{{{SML}}}border").get(native_attribute), value)
        nodes = self.children(self.convert(PATH.replace('stroke-width="1.4"', 'stroke-width="3"')))
        self.assertEqual(nodes[0].get("type"), "custom")
        self.assertEqual(nodes[0].find(f"{{{SML}}}border").get("width"), "3")
        set_mapping(900, 212, 30, 120, 720, 169.6)
        nodes = self.children(self.convert(PATH))
        arrow = nodes[-1]
        self.assertAlmostEqual(float(arrow.get("topLeftX")), 30 + 91.8 * 0.8, places=4)
        self.assertAlmostEqual(float(arrow.get("topLeftY")), 120 + 72 * 0.8, places=4)


# ====================================================================================================
# Protect dashed semantic borders observed in the clinical trial design SVG.
# ====================================================================================================


class SemanticBorderTest(unittest.TestCase):
    def test_rect_dash_style_survives_direct_and_inherited_presentation(self):
        saved = deepcopy(_CFG)
        try:
            set_mapping(960, 540, 0, 0, 960, 540)
            _CFG["drop_bg"] = False
            rect = (
                '<rect x="100" y="120" width="200" height="80" fill="none" stroke="#663366" stroke-width="2"{style}/>'
            )
            examples = [
                (rect.format(style=' stroke-dasharray="5 4"'), True),
                ('<g stroke-dasharray="5 4">' + rect.format(style="") + "</g>", True),
                (rect.format(style=' stroke-dasharray="none"'), False),
            ]
            for body, dashed in examples:
                with self.subTest(dashed=dashed, body=body), TemporaryDirectory() as directory:
                    source = Path(directory) / "design.svg"
                    source.write_text(
                        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 540">' + body + "</svg>",
                        encoding="utf-8",
                    )
                    root = ET.fromstring(atomize_svg_to_slide(source))
                    shapes = root.findall(f"{_SML}data/{_SML}shape")
                    self.assertEqual(len(shapes), 1)
                    shape = shapes[0]
                    border = shape.find(f"{_SML}border")
                    self.assertEqual(border.get("width"), "2")
                    self.assertEqual(border.get("color"), "rgb(102,51,102)")
                    if dashed:
                        # Inherited and direct dashes are both expanded into one exact dashed contour.
                        self.assertEqual(shape.get("type"), "custom")
                        self.assertGreater(shape.get("path").count("M "), 10)
                    else:
                        self.assertEqual(shape.get("type"), "rect")
                        self.assertEqual(
                            [float(shape.get(key)) for key in ("topLeftX", "topLeftY", "width", "height")],
                            [100, 120, 200, 80],
                        )
        finally:
            _CFG.clear()
            _CFG.update(saved)


# ====================================================================================================
# Integration regressions: merge SML without namespace loss or global state.
# ====================================================================================================

SVG = "http://www.w3.org/2000/svg"


XLINK = "http://www.w3.org/1999/xlink"


FIGURE = '<shape type="rect" topLeftX="400" topLeftY="150" width="160" height="100"><fill><fillColor color="rgb(51,102,153)"/></fill><border color="rgba(0,0,0,0)" width="0"/></shape>'


FRAGMENT = f'<slide xmlns="{SML}"><data>{FIGURE}</data></slide>'


BASE_BODY = '<shape type="text" topLeftX="50" topLeftY="40" width="250" height="30"><content fontSize="20"><p>标题😀</p></content></shape>'


BASE = f'<slide xmlns="{SML}"><data>{BASE_BODY}</data></slide>'


class MergeAtomizedSlideTest(unittest.TestCase):
    def test_merge_appends_bindings_byte_exact_and_rejects_invalid(self):
        expected = BASE[: -len("</data></slide>")] + FIGURE + "</data></slide>"
        merged = merge_atomized_slide(BASE, FRAGMENT)
        self.assertEqual(merged, expected)
        self.assertNotIn("ns0:", merged)
        data = ET.fromstring(merged).find(f"{{{SML}}}data")
        self.assertEqual(len(data), 2)
        svg = f'<embed topLeftX="1" topLeftY="2" width="30" height="40"><svg xmlns="{SVG}" xmlns:xlink="{XLINK}" viewBox="0 0 30 40"><defs><path id="p" d="M0 0L3 4"/></defs><use xlink:href="#p"/><!-- <data/> --><text>旧图 &amp; 原文</text></svg></embed>'
        base = f'<slide xmlns="{SML}"><data>{svg}</data></slide>'
        merged = merge_atomized_slide(base, FRAGMENT)
        self.assertIn(svg, merged)
        parsed = ET.fromstring(merged)
        self.assertIsNotNone(parsed.find(f".//{{{SVG}}}use"))
        self.assertEqual(parsed.find(f".//{{{SVG}}}use").get(f"{{{XLINK}}}href"), "#p")
        fragment = f'<slide xmlns="{SML}" xmlns:xlink="{XLINK}"><data xmlns:q="urn:fragment"><embed q:key="字"><svg xmlns="{SVG}"><use xlink:href="#part"/></svg></embed></data></slide>'
        base = f'<slide xmlns="{SML}" xmlns:xlink="urn:base"><data>{BASE_BODY}</data></slide>'
        merged = merge_atomized_slide(base, fragment)
        self.assertTrue(merged.startswith(base[: -len("</data></slide>")]))
        parsed = ET.fromstring(merged)
        embed = parsed.find(f"{{{SML}}}data/{{{SML}}}embed")
        self.assertEqual(embed.get("{urn:fragment}key"), "字")
        self.assertEqual(embed.find(f"{{{SVG}}}svg/{{{SVG}}}use").get(f"{{{XLINK}}}href"), "#part")
        self.assertIn('xmlns:xlink="urn:base"', merged)
        fragment = f'<slide xmlns="{SML}" xmlns:q="urn:root"><data xmlns:q="urn:data"><shape xmlns:q="urn:child" q:key="值"/></data></slide>'
        merged = merge_atomized_slide(BASE, fragment)
        shape = list(ET.fromstring(merged).find(f"{{{SML}}}data"))[-1]
        self.assertEqual(shape.get("{urn:child}key"), "值")
        self.assertEqual(merged.count('xmlns:q="urn:child"'), 1)
        self.assertNotIn('xmlns:q="urn:data"', merged)
        body = '<!-- 中文😃 --><shape q:name="第一项"/><shape q:name="第二项"/>'
        fragment = f'<slide xmlns="{SML}" xmlns:q="urn:test"><data>{body}</data></slide>'
        merged = merge_atomized_slide(BASE, fragment)
        nodes = list(ET.fromstring(merged).find(f"{{{SML}}}data"))[-2:]
        self.assertEqual([node.get("{urn:test}name") for node in nodes], ["第一项", "第二项"])
        self.assertEqual(merged.count('xmlns:q="urn:test"'), 2)
        base = f'<slide xmlns="{SML}" xmlns:q="urn:same"><data/></slide>'
        body = '<shape q:name="original"/>'
        fragment = f'<slide xmlns="{SML}" xmlns:q="urn:same"><data>{body}</data></slide>'
        merged = merge_atomized_slide(base, fragment)
        self.assertIn("<data>" + body + "</data>", merged)
        self.assertEqual(merged.count('xmlns:q="urn:same"'), 1)
        element = ET.Element(f"{{{SML}}}slide")
        before = ET.tostring(element, encoding="unicode")
        merge_atomized_slide(BASE, FRAGMENT)
        self.assertEqual(ET.tostring(element, encoding="unicode"), before)
        cdata = '<!-- <data>假结束</data> --><shape type="text"><content><p><![CDATA[字样 </data> 与 <data>，不是节点]]></p></content></shape>'
        cases = [
            (
                f'<?xml version="1.0" encoding="UTF-8"?>\r\n<!-- 原图😃 -->\r\n<slide xmlns="{SML}"><data>\n{BASE_BODY}\n',
                "</data>\r\n<!-- 原文尾部 -->\r\n</slide>",
            ),
            (f'<slide xmlns="{SML}"><data label="前>后" other=\'1 > 0\'>{BASE_BODY}', "</data></slide>"),
            (f'<slide xmlns="{SML}"><data>{cdata}', "</data><!-- another </data> --></slide>"),
        ]
        for before, after in cases:
            with self.subTest(before=before):
                self.assertEqual(merge_atomized_slide(before + after, FRAGMENT), before + FIGURE + after)
        for opening in ("<data/>", "<data />", '<data label="中文>" />'):
            with self.subTest(opening=opening):
                base = f'<slide xmlns="{SML}">{opening}</slide>'
                expected = f'<slide xmlns="{SML}">{opening[:-2]}>{FIGURE}</data></slide>'
                self.assertEqual(merge_atomized_slide(base, FRAGMENT), expected)
        for body in ("<data/>", "<data />", "<data>\r\n\t </data>"):
            with self.subTest(empty=body):
                self.assertEqual(merge_atomized_slide(BASE, f'<slide xmlns="{SML}">{body}</slide>'), BASE)
        body = '<!-- 保留原注释 --><shape type="text"><content><p><![CDATA[α < β & </data>]]></p></content></shape>'
        fragment = f'<slide xmlns="{SML}"><data>{body}</data></slide>'
        self.assertEqual(merge_atomized_slide(BASE, fragment), BASE.replace("</data>", body + "</data>"))
        for xml in (f'<slide xmlns="{SML}"/>', f'<slide xmlns="{SML}"><data/><data/></slide>'):
            with self.subTest(xml=xml), self.assertRaisesRegex(ValueError, "exactly one"):
                merge_atomized_slide(xml, FRAGMENT)
            with self.subTest(fragment=xml), self.assertRaisesRegex(ValueError, "exactly one"):
                merge_atomized_slide(BASE, xml)
        prefixed = f'<ns0:slide xmlns:ns0="{SML}"><ns0:data/></ns0:slide>'
        with self.assertRaisesRegex(ValueError, "prefixed SML"):
            merge_atomized_slide(prefixed, FRAGMENT)
        cases = [
            (prefixed, "prefixed SML"),
            ('<svg xmlns="http://www.w3.org/2000/svg"/>', "slide"),
            (f'<slide xmlns="{SML}"><data>lost text</data></slide>', "loose text"),
            (f'<slide xmlns="{SML}"><data><svg xmlns="{SVG}"/></data></slide>', "SML elements"),
            (f'<slide xmlns="{SML}">lost root text<data/></slide>', "loose text outside"),
            (f'<!DOCTYPE slide [<!ENTITY text "replacement">]><slide xmlns="{SML}"><data/></slide>', "DTD/entity"),
            (f'<slide xmlns="{SML}"><data>', "Invalid atomized fragment XML"),
            # Wrapper content that would otherwise be silently discarded.
            (f'<slide xmlns="{SML}"><style/><data/></slide>', ""),
            (f'<slide xmlns="{SML}" title="lost"><data/></slide>', ""),
            (f'<slide xmlns="{SML}"><data label="lost"/></slide>', ""),
        ]
        for xml, error in cases:
            with self.subTest(xml=xml), self.assertRaisesRegex(ValueError, error):
                merge_atomized_slide(BASE, xml)

    def test_real_atomize_result_merges_and_lints_without_handwritten_et(self):
        with TemporaryDirectory() as directory:
            svg = Path(directory) / "figure.svg"
            svg.write_text(
                f'<svg xmlns="{SVG}" viewBox="0 0 960 540"><rect x="400" y="150" width="160" height="100" fill="#369"/></svg>'
            )
            set_mapping(960, 540, 0, 0, 960, 540)
            merged = merge_atomized_slide(BASE, atomize_svg_to_slide(svg))
        sys.path.insert(0, str(Path(__file__).parents[2]))
        import xml_lint

        report = xml_lint.lint_xml(merged)
        self.assertEqual(report["summary"]["error_count"], 0, report)


# ====================================================================================================
# Rotated labels stay editable text instead of being rejected or deleted.
# ====================================================================================================


class TextTransformGuidanceTest(unittest.TestCase):
    def test_rotated_label_stays_native_text_with_rotation(self):
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100">'
            '<text x="20" y="50" transform="rotate(-90 20 50)" '
            'font-size="14">合成观测值</text></svg>'
        )
        with TemporaryDirectory() as directory:
            path = Path(directory) / "synthetic.svg"
            path.write_text(svg, encoding="utf-8")
            set_mapping(200, 100, 0, 0, 200, 100)
            xml = atomize_svg_to_slide(path)
            self.assertEqual(path.read_text(encoding="utf-8"), svg)
        shape = ET.fromstring(xml).find("{*}data/{*}shape")
        self.assertEqual(shape.get("type"), "text")
        self.assertEqual(shape.get("rotation"), "270")
        self.assertEqual("".join(shape.itertext()), "合成观测值")


# ====================================================================================================
# Regression cases from the atomizer audit; no validator rules are modified.
# ====================================================================================================

NS = {"s": "https://www.larkoffice.com/sml/2.0"}


class AtomizerRobustnessTest(unittest.TestCase):
    def setUp(self):
        self.original_config = deepcopy(_CFG)
        _CFG.update(
            drop_bg=False, drop_text_below=0, drop_micro_gray_below=0, min_slide_font_size=10, subtitle_svg_threshold=0
        )
        set_mapping(960, 540, 0, 0, 960, 540)

    def tearDown(self):
        _CFG.clear()
        _CFG.update(self.original_config)

    def atomize(self, body, header=""):
        with TemporaryDirectory() as directory:
            source = Path(directory) / "input.svg"
            source.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 540" ' + header + ">" + body + "</svg>",
                encoding="utf-8",
            )
            return atomize_svg_to_slide(source)

    def shape(self, xml):
        return ET.fromstring(xml).find("s:data/s:shape", NS)

    def assert_lint_passes(self, xml):
        report = xml_lint.lint_xml(xml)
        self.assertEqual(report["summary"]["error_count"], 0, report)

    def test_robust_xml_groups_paints_text_and_converters(self):
        common = ' fill="none" stroke="#369" stroke-width="2"/>'
        first = self.atomize('<path id="route1" d="M20 80Q50 20 80 80"' + common)
        second = self.atomize('<path d="M20 80Q50 20 80 80" id="route1"' + common)
        self.assertEqual(first, second)
        rect = self.shape(
            self.atomize('<rect rx="8" stroke-width="2" id="r" x="100" y="120" width="60" height="40" fill="#369"/>')
        )
        self.assertEqual(float(rect.get("topLeftX")), 100)
        self.assertEqual(float(rect.get("width")), 60)
        # Attribute values never become attributes.
        self.assertEqual(_get_attr("""<rect id="example width='999'" width="60"/>""", "width"), "60")
        # Only the opening tag's own attributes count, never those of a child tspan.
        self.assertIsNone(
            _get_attr('<text x="10"><tspan font-size="40">A</tspan></text>'[: len('<text x="10">')], "font-size")
        )
        xml = self.atomize(
            "<!-- not artwork --><rect x='100' y='100' width='60' height='40' fill='#369'></rect><circle cx='250' cy='150' r='30'/>"
        )
        self.assertEqual(len(ET.fromstring(xml).find("s:data", NS)), 2)
        self.assert_lint_passes(xml)
        xml = self.atomize(
            '<g fill="#369" font-family="Georgia"><rect x="100" y="100" width="60" height="40"/><text x="100" y="200" style="font-size:24;fill:#963">α = 0.05</text></g>'
        )
        nodes = ET.fromstring(xml).find("s:data", NS)
        self.assertEqual(nodes[0].find("s:fill/s:fillColor", NS).get("color"), "rgb(51,102,153)")
        self.assertEqual(nodes[1].find("s:content", NS).get("fontFamily"), "Georgia")
        self.assertEqual(nodes[1].find("s:content", NS).get("fontSize"), "24")
        line = self.atomize('<line x1="100" y1="100" x2="200" y2="100" stroke="#369" stroke-opacity="0.5"/>')
        self.assertIn("rgba(51,102,153,0.50)", line)
        curve = self.atomize(
            '<path d="M100 150Q150 50 200 150Z" fill="#369" fill-opacity="0.8" stroke="#000" stroke-opacity="0.5" opacity="0.5"/>'
        )
        # Paint alpha stays on each paint; element opacity is one shape-level alpha.
        self.assertIn("rgba(51,102,153,0.80)", curve)
        self.assertIn("rgba(0,0,0,0.50)", curve)
        self.assertIn('alpha="0.5"', curve)
        xml = self.atomize('<line x1="100" y1="100" x2="200" y2="100" stroke="rgba(10,20,30,1e-1)" opacity="0.5"/>')
        self.assertIn("rgba(10,20,30,0.050)", xml)  # scientific alpha combines with opacity
        xml = self.atomize(
            '<text x="100" y="100" font-size="24" font-family="Georgia">&#945; &#x3B2; &amp; &amp;alpha;</text>'
        )
        shape = self.shape(xml)
        self.assertEqual("".join(shape.find("s:content", NS).itertext()), "α β & &alpha;")
        self.assertEqual(shape.find("s:content", NS).get("fontFamily"), "Georgia")
        self.assert_lint_passes(xml)
        xml = self.atomize(
            '<text x="100" y="100" font-size="24" font-family="Georgia">Control <tspan font-weight="700" fill="#963">n = 24</tspan></text>'
        )
        root = ET.fromstring(xml)
        self.assertEqual("".join(root.find("s:data/s:shape/s:content", NS).itertext()), "Control n = 24")
        spans = root.findall(".//s:span", NS)
        self.assertEqual(spans[-1].get("bold"), "true")
        self.assertEqual(spans[-1].get("color"), "rgb(153,102,51)")
        self.assert_lint_passes(xml)
        normal = self.shape(self.atomize('<text x="100" y="100" font-size="24">WWWWWWWWWWWW</text>'))
        spaced = self.shape(
            self.atomize('<text x="100" y="100" font-size="24" letter-spacing="0.2em">WWWWWWWWWWWW</text>')
        )
        self.assertGreater(float(normal.get("width")), 280)
        self.assertGreater(float(spaced.get("width")), float(normal.get("width")) + 45)
        self.assertEqual(float(spaced.find("s:content", NS).get("letterSpacing")), 4.8)
        xml = convert_path('<path d="M10 10L20 20" transform="translate(50 50)" stroke="#000"/>')
        self.assertIn("<embed", xml)
        self.assertIn('transform="translate(50 50)"', xml)
        xml = self.atomize('<path d="M100 100L130 100L100 130Z M200 200L230 200L200 230Z" fill="#369"/>')
        path = self.shape(xml).get("path")
        self.assertEqual(path.count("M "), 2)
        self.assertEqual(path.count("Z"), 2)
        commands = _absolute_path_commands("M+.5 +.5L1E2 2e1l-1e1+.5")
        self.assertEqual(commands, [("M", (0.5, 0.5)), ("L", (100.0, 20.0)), ("L", (90.0, 20.5))])
        bbox = _parse_path_bbox("M100 200C100 100 200 100 200 200S300 300 300 200")
        self.assertEqual(bbox, (100.0, 125.0, 300.0, 275.0))
        commands = _absolute_path_commands("M100 200C100 100 200 100 200 200S300 300 300 200")
        self.assertEqual(commands[-1], ("C", (200.0, 300.0, 300.0, 300.0, 300.0, 200.0)))
        d = "M100 100A80 30 40 1 1 230 170"
        bounds = _parse_path_bbox(d)
        points = _sample_svg_arc_points(100, 100, 80, 30, 40, 1, 1, 230, 170)
        for x, y in points:
            self.assertTrue(bounds[0] - 1e-3 <= x <= bounds[2] + 1e-3)
            self.assertTrue(bounds[1] - 1e-3 <= y <= bounds[3] + 1e-3)
        placements = _placements(ET.fromstring('<path d="M80 50A30 30 0 0 1 50 80"/>'))
        start = next(p for p in placements if p[0] == "marker-start")
        end = next(p for p in placements if p[0] == "marker-end")
        self.assertAlmostEqual(start[2] % 360, 90, places=6)
        self.assertAlmostEqual(end[2] % 360, 180, places=6)
        set_mapping(960, 540, 0, 0, 480, 270)
        xml = self.atomize(
            '<circle cx="200" cy="200" r="40" fill="#369" stroke="#000" stroke-width="4" opacity="0.2"/>'
        )
        shape = self.shape(xml)
        self.assertEqual(shape.get("alpha"), "0.2")
        self.assertEqual(shape.find("s:border", NS).get("width"), "2")
        no_stroke = self.atomize('<circle cx="200" cy="200" r="40" fill="#369" stroke="none"/>')
        self.assertNotIn('color="none"', no_stroke)
        self.assertEqual(self.shape(no_stroke).find("s:border", NS).get("width"), "0")
        self.assert_lint_passes(no_stroke)

    def test_zero_font_floor_falls_back_to_six_point_minimum(self):
        set_mapping(960, 540, 0, 0, 480, 270)
        set_min_slide_font_size(0)
        shape = self.shape(self.atomize('<text x="100" y="100" font-size="8">small</text>'))
        self.assertEqual(shape.find("s:content", NS).get("fontSize"), "6")

    def test_malformed_paths_exit_without_hanging(self):
        for d in ("M10 10 L20", "M10 10Q20 20", "M10 10Z20", "M10 10 C", "M10 10L20 20@", "M0 0A1 1 0 2 0 20 20"):
            with self.subTest(d=d):
                script = (
                    "from scripts.svg_lib.atomize_svg_to_slide import convert_path; convert_path("
                    + repr('<path d="' + d + '" fill="#369"/>')
                    + ")"
                )
                result = subprocess.run(
                    [sys.executable, "-c", script],
                    cwd=Path(__file__).parents[3],
                    capture_output=True,
                    text=True,
                    timeout=2,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("ValueError", result.stderr)

    def test_unsupported_missing_and_fallback_content_is_explicit(self):
        xml = self.atomize(
            '<defs><filter id="shadow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="8"/></filter></defs><path d="M100 100L200 100L150 200Z" fill="#369" filter="url(#shadow)"/>'
        )
        embed = ET.fromstring(xml).find("s:data/s:embed", NS)
        self.assertIsNotNone(embed)
        # The filter region (50..250) plus the default 1px stroke allowance.
        self.assertLessEqual(float(embed.get("topLeftX")), 50)
        self.assertGreaterEqual(float(embed.get("width")), 200)
        self.assertIn("feGaussianBlur", xml)
        for body, message in (
            ('<image href="photo.png" width="40" height="30"/>', "Unsupported SVG element"),
            ('<rect width="20" height="20" clip-path="url(#clip)"/>', "Missing SVG definition #clip"),
            ('<rect width="broken" height="20"/>', "width"),
            ('<polygon points="10 10 20"/>', "complete x/y"),
            ("<text>unfinished", "Invalid SVG XML"),
        ):
            with self.subTest(body=body), self.assertRaisesRegex(ValueError, message):
                self.atomize('<rect x="100" y="100" width="40" height="40"/>' + body)
        # Group transforms are distributed into absolute coordinates.
        rects = ET.fromstring(
            self.atomize('<g transform="translate(10 20)"><rect width="20" height="20"/></g>')
        ).findall("s:data/s:shape", NS)
        self.assertEqual((rects[0].get("topLeftX"), rects[0].get("topLeftY")), ("10.0", "20.0"))
        with self.assertRaisesRegex(ValueError, "Missing SVG definition #missing referenced by <line>"):
            self.atomize('<line x1="100" y1="100" x2="200" y2="100" stroke="#369" marker-end="url(#missing)"/>')
        with self.assertRaisesRegex(ValueError, "urn:foreign"):
            self.atomize('<other:text xmlns:other="urn:foreign" x="100" y="100">not SVG</other:text>')
        with self.assertRaisesRegex(ValueError, "Cyclic"):
            self.atomize(
                '<defs><radialGradient id="g" href="#g"/></defs><circle cx="100" cy="100" r="20" fill="url(#g)"/>'
            )
        # Document-local <use> is expanded into editable geometry.
        xml = self.atomize(
            '<defs><path id="p" d="M0 0L20 20" stroke="#000"/></defs><use xmlns:xlink="http://www.w3.org/1999/xlink" xlink:href="#p"/>'
        )
        self.assertEqual(self.shape(xml).get("type"), "custom")
        xml = self.atomize(
            '<defs><radialGradient id="base"><stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#369"/></radialGradient><radialGradient xmlns:xlink="http://www.w3.org/1999/xlink" id="derived" xlink:href="#base"/></defs><circle cx="200" cy="200" r="40" fill="url(#derived)"/>'
        )
        self.assertIn('id="base"', xml)
        self.assertIn('id="derived"', xml)
        self.assertIn('href="#base"', xml)
        self.assertIn("<embed ", xml)
        xml = self.atomize(
            '<defs><marker id="arrow" markerUnits="userSpaceOnUse" markerWidth="20" markerHeight="20" refX="0" refY="0" orient="auto" overflow="visible"><path d="M0 -6L0 6" fill="none" stroke="#963" stroke-width="2"/></marker></defs><line x1="100" y1="100" x2="200" y2="100" stroke="#369" marker-end="url(#arrow)"/>'
        )
        data = ET.fromstring(xml).find("s:data", NS)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[1].tag.rsplit("}", 1)[-1], "line")
        self.assertEqual(float(data[1].get("startX")), 200)
        self.assertEqual(float(data[1].get("endX")), 200)
        self.assertEqual({float(data[1].get("startY")), float(data[1].get("endY"))}, {94, 106})
        self.assertEqual(data[1].find("s:border", NS).get("color"), "rgb(153,102,51)")
        self.assertNotIn("Arrow", xml)
        definitions = '<defs><marker id="not_an_arrow_name" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 0L10 5L0 10Z" fill="#963"/></marker></defs>'
        xml = self.atomize(
            definitions
            + '<line x1="100" y1="100" x2="200" y2="100" stroke="#369" stroke-width="2" marker-start="url(#not_an_arrow_name)" marker-end="url(#not_an_arrow_name)"/>'
        )
        data = ET.fromstring(xml).find("s:data", NS)
        self.assertEqual(len(data), 3)
        self.assertAlmostEqual(float(data[1].get("topLeftX")), 100)
        self.assertAlmostEqual(float(data[1].get("width")), 12)
        self.assertAlmostEqual(float(data[2].get("topLeftX")), 188)
        self.assertAlmostEqual(float(data[2].get("width")), 12)
        xml = self.atomize(
            '<defs><marker id="m" markerUnits="userSpaceOnUse" overflow="visible"><circle r="2"/><path d="M0 0L10 10" stroke="#000"/></marker></defs><line x1="100" y1="100" x2="200" y2="100" stroke="#000" marker-end="url(#m)"/>'
        )
        self.assertNotIn("<embed", xml)
        self.assertGreaterEqual(len(ET.fromstring(xml).find("s:data", NS)), 3)
        xml = self.atomize(
            '<defs><marker id="m" markerUnits="userSpaceOnUse" overflow="visible" orient="auto" fill="none" stroke="#963" stroke-width="4" stroke-linecap="round" stroke-linejoin="bevel"><path d="M0 -8L0 8"/></marker></defs><line x1="100" y1="100" x2="200" y2="100" stroke="#369" marker-end="url(#m)"/>'
        )
        marker_border = list(ET.fromstring(xml).find("s:data", NS))[-1].find("s:border", NS)
        self.assertEqual(marker_border.get("width"), "4")
        self.assertEqual(marker_border.get("lineCap"), "round")
        self.assertEqual(marker_border.get("lineJoin"), "bevel")
        for marker_attrs, child_attrs, expected in (
            ("", 'display="none"', 1),
            ("", 'visibility="hidden"', 1),
            ('visibility="hidden"', 'visibility="visible"', 2),
        ):
            with self.subTest(marker_attrs=marker_attrs, child_attrs=child_attrs):
                xml = self.atomize(
                    f'<defs><marker id="m" markerUnits="userSpaceOnUse" overflow="visible" {marker_attrs}><circle r="2" {child_attrs}/></marker></defs><line x1="100" y1="100" x2="200" y2="100" stroke="#369" marker-end="url(#m)"/>'
                )
                self.assertEqual(len(ET.fromstring(xml).find("s:data", NS)), expected)
        for viewbox in ("0 0 NaN 10", "inf 0 10 10", "0 0 10 inf"):
            with self.subTest(viewbox=viewbox), self.assertRaisesRegex(ValueError, "viewBox"):
                self.atomize(
                    f'<defs><marker id="m" viewBox="{viewbox}" overflow="visible"><circle r="2"/></marker></defs><line x1="100" y1="100" x2="200" y2="100" marker-end="url(#m)"/>'
                )
        for body, message in (
            ('<svg x="50" viewBox="0 0 10 10"><rect width="5" height="5"/></svg>', "Nested"),
            ('<rect width="20" height="20" fill="rgb(bad)"/>', "color"),
        ):
            with self.subTest(body=body), self.assertRaisesRegex(ValueError, message):
                self.atomize(body)
        # Baseline shifts and mixed run sizes now have native text representations.
        for body in (
            '<g dominant-baseline="middle"><text x="100" y="100">A</text></g>',
            '<text x="100" y="100" font-size="20">A<tspan font-size="30">B</tspan></text>',
        ):
            with self.subTest(body=body):
                self.assertEqual(self.shape(self.atomize(body)).get("type"), "text")
        xml = self.atomize(
            '<g visibility="hidden"><text x="100" y="100">hidden</text><text x="100" y="200" visibility="visible">visible</text></g>'
        )
        self.assertIn("visible", xml)
        self.assertNotIn("hidden", xml)
        xml = self.atomize('<polyline points="100 100 200 100 150 200" fill="#369" stroke="none"/>')
        self.assertEqual(self.shape(xml).get("type"), "custom")
        self.assertEqual(self.shape(xml).find("s:fill/s:fillColor", NS).get("color"), "rgb(51,102,153)")
        # Significant leading/trailing spaces cannot be laid out natively; keep the SVG text intact.
        xml = self.atomize(
            '<text xml:space="preserve" x="100" y="100" font-size="24"> A  <tspan font-weight="700"> B </tspan> C </text>'
        )
        self.assertIn("<embed", xml)
        self.assertIn("> A  <tspan", xml)
        self.assertIn("> B </tspan> C </text>", xml)
        set_mapping(960, 540, 0, 0, 480, 540)
        xml = self.atomize('<path d="M100 100A80 30 40 1 1 230 170" fill="none" stroke="#369"/>')
        shape = self.shape(xml)
        self.assertEqual(shape.get("type"), "custom")
        self.assertIn(" C ", shape.get("path"))
        self.assertNotIn("<embed", xml)
