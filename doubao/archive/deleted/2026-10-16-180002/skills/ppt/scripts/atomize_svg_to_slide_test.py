from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from atomize_svg_to_slide import atomize_svg_to_slide, set_mapping


class AtomizeSvgToSlidePathTest(unittest.TestCase):
    def atomize_body(self, body: str) -> str:
        with TemporaryDirectory() as tmp_dir:
            svg_path = Path(tmp_dir) / "case.svg"
            svg_path.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
                f"{body}</svg>",
                encoding="utf-8",
            )
            set_mapping(100, 100, 0, 0, 100, 100)
            return atomize_svg_to_slide(svg_path)

    def test_quadratic_stroke_path_preserves_native_curve(self) -> None:
        xml = self.atomize_body(
            '<path d="M 10 80 Q 50 20 90 80" fill="none" '
            'stroke="rgba(24,26,34,0.92)" stroke-width="2.6"/>'
        )

        self.assertNotIn("<embed", xml)
        self.assertNotIn("<line", xml)
        self.assertIn('<shape type="custom"', xml)
        self.assertIn(" Q ", xml)

    def test_line_preserves_dash_and_arrow(self) -> None:
        xml = self.atomize_body(
            '<defs><marker id="arr"/></defs>'
            '<line x1="10" y1="10" x2="90" y2="10" '
            'stroke="rgba(24,26,34,0.92)" stroke-width="2" '
            'stroke-linecap="round" stroke-dasharray="5 4" '
            'marker-end="url(#arr)"/>'
        )

        self.assertNotIn("<embed", xml)
        self.assertIn('dashArray="dash"', xml)
        self.assertIn('lineCap="round"', xml)
        self.assertIn('<endArrow type="solid-triangle"', xml)

    def test_stroke_width_scales_with_svg_mapping(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            svg_path = Path(tmp_dir) / "case.svg"
            svg_path.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">'
                '<line x1="20" y1="20" x2="180" y2="20" '
                'stroke="rgba(24,26,34,0.92)" stroke-width="1.6"/>'
                '</svg>',
                encoding="utf-8",
            )
            set_mapping(200, 200, 0, 0, 100, 100)
            xml = atomize_svg_to_slide(svg_path)

        self.assertIn('width="1"', xml)
        self.assertNotIn('width="2"', xml)

    def test_markered_stroked_path_stays_continuous(self) -> None:
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
        self.assertIn('dashArray="dash"', xml)

    def test_fill_only_custom_path_uses_transparent_border_color(self) -> None:
        xml = self.atomize_body(
            '<path d="M 10 80 Q 50 20 90 80 L 90 90 L 10 90 Z" '
            'fill="rgba(168,88,42,0.08)" stroke="none"/>'
        )

        self.assertIn('<shape type="custom"', xml)
        self.assertNotIn('color="none"', xml)
        self.assertIn('color="rgba(0,0,0,0)"', xml)

    def test_arc_stroke_path_preserves_native_curve(self) -> None:
        xml = self.atomize_body(
            '<path d="M 80 50 A 30 30 0 0 1 50 80" fill="none" '
            'stroke="rgba(168,88,42,0.92)" stroke-width="3"/>'
        )

        self.assertNotIn("<embed", xml)
        self.assertNotIn("<line", xml)
        self.assertIn('<shape type="custom"', xml)
        self.assertIn(" A ", xml)

    def test_rotated_ellipse_stays_native_shape(self) -> None:
        xml = self.atomize_body(
            '<ellipse cx="50" cy="50" rx="30" ry="15" transform="rotate(-55 50 50)" '
            'fill="rgba(32,120,88,0.160)" stroke="rgba(32,120,88,0.920)" stroke-width="1.8"/>'
        )

        self.assertNotIn("<embed", xml)
        self.assertIn('<shape type="ellipse"', xml)
        self.assertIn('rotation="305"', xml)

    def test_gradient_filtered_path_becomes_native_custom_shape(self) -> None:
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
                '</svg>',
                encoding="utf-8",
            )
            set_mapping(100, 100, 0, 0, 100, 100)
            xml = atomize_svg_to_slide(svg_path)

        self.assertNotIn("<embed", xml)
        self.assertIn('<shape type="custom"', xml)
        self.assertIn('linear-gradient(', xml)

    def test_filtered_halo_rect_becomes_native_shape(self) -> None:
        xml = self.atomize_body(
            '<defs><filter id="halo"/></defs>'
            '<rect x="20" y="20" width="60" height="20" fill="none" '
            'stroke="#A35832" stroke-width="1.6" rx="8" opacity="0.5" filter="url(#halo)"/>'
        )

        self.assertNotIn("<embed", xml)
        self.assertIn('<shape type="rect"', xml)
        self.assertIn('alpha="0.5"', xml)


if __name__ == "__main__":
    unittest.main()
