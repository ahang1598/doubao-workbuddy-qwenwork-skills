"""Shared fixtures for the svg_lib test modules (no tests of their own)."""

from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import unittest
import xml.etree.ElementTree as ET

if str(Path(__file__).resolve().parents[2]) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from embed_svg_validator import detect_embedded_svg_overlaps, validate_embedded_svgs

from ..atomize_svg_to_slide import atomize_svg_to_slide, set_mapping
from ..atomize_svg_to_slide._config import _CFG
from .._common import _estimate_label_width_px


class SvgTestCase(unittest.TestCase):
    """Shared test fixture only; contains no tests of its own."""

    canvas = (100, 100)

    def setUp(self):
        saved = dict(_CFG)
        self.addCleanup(self.restore_config, saved)
        width, height = self.canvas
        set_mapping(width, height, 0, 0, width, height)
        _CFG.update(
            drop_bg=False,
            min_slide_font_size=10,
            drop_text_below=0,
            drop_micro_gray_below=0,
            subtitle_svg_threshold=0,
            font_metrics="auto",
        )

    @staticmethod
    def restore_config(saved):
        _CFG.clear()
        _CFG.update(saved)

    def atomize_body(self, body="", viewbox=None, *, document=None):
        width, height = self.canvas
        viewbox = viewbox or f"0 0 {width} {height}"
        source = (
            document
            if document is not None
            else (
                '<svg xmlns="http://www.w3.org/2000/svg" '
                'xmlns:xlink="http://www.w3.org/1999/xlink" '
                f'viewBox="{viewbox}">{body}</svg>'
            )
        )
        with TemporaryDirectory() as directory:
            path = Path(directory) / "input.svg"
            path.write_text(source, encoding="utf-8")
            return atomize_svg_to_slide(path)

    def convert(self, body="", viewbox=None, *, document=None):
        xml = self.atomize_body(body, viewbox, document=document)
        return ET.fromstring(xml).find("{*}data")


def _text_boxes(svg):
    """Approximate (x0, y0, x1, y1, label) boxes of every <text> in a chart SVG, plus its viewBox size."""
    root = ET.fromstring(svg)
    width, height = map(float, root.attrib["viewBox"].split()[2:])
    boxes = []
    for node in root.findall(".//{http://www.w3.org/2000/svg}text"):
        label = "".join(node.itertext())
        fs = float(node.get("font-size", 13))
        x, y = float(node.get("x", 0)), float(node.get("y", 0))
        w = _estimate_label_width_px(
            label,
            fs,
            bold=int(node.get("font-weight", 400)) >= 600,
            font_family=node.get("font-family", root.get("font-family")),
        )
        anchor = node.get("text-anchor")
        x -= w if anchor == "end" else w / 2 if anchor == "middle" else 0
        boxes.append((x, y - fs * 0.84, x + w, y + fs * 0.26, label))
    return width, height, boxes


_NON_DRAWN = ("g", "defs", "linearGradient", "radialGradient", "stop")


def nodes(svg, role):
    """Every element of an SVG string/element whose data-role equals ``role``."""
    root = ET.fromstring(svg) if isinstance(svg, str) else svg
    return [node for node in root.iter() if node.get("data-role") == role]


def embed_issues(svg):
    """Embedded-SVG validation plus overlap findings for one chart SVG placed on a slide."""
    root = ET.fromstring(f"<slide><data><embed>{svg}</embed></data></slide>")
    return validate_embedded_svgs(root) + detect_embedded_svg_overlaps(root)


def first_drawn(geometry):
    """The first painted child of a part (skipping groups, defs and gradient stops)."""
    return [c for c in geometry.element.iter() if c is not geometry.element and c.tag not in _NON_DRAWN][0]


def quiet_slide(drawing, **kwargs):
    """drawing.to_slide(...) with its advisory warnings silenced; summary defaults to False."""
    import warnings

    kwargs.setdefault("x", 0)
    kwargs.setdefault("y", 0)
    kwargs.setdefault("summary", False)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return drawing.to_slide(**kwargs)


def assert_centered(test, g, msg=None):
    test.assertAlmostEqual(g.bounds.x + g.bounds.width / 2, 0, places=6, msg=msg)
    test.assertAlmostEqual(g.bounds.y + g.bounds.height / 2, 0, places=6, msg=msg)


def built_part(test, make, *, centered=True, outline=True, msg=None):
    """Build ``make()`` twice: assert it is deterministic, (optionally) centred and outline-first; return it."""
    g = make()
    if centered:
        assert_centered(test, g, msg)
    if outline:
        test.assertEqual(first_drawn(g).get("data-outline"), "1", msg)
    test.assertEqual(ET.tostring(g.element), ET.tostring(make().element), msg)
    return g


def assert_parts_centered_native(test, makers, *, paired=False, first_outline=True, embeds=None, no_complex=False):
    """Every maker(style) part is centred, deterministic, outlined and lint-clean when placed; returns the count checked.

    paired: place two copies 500px apart joined by an arrow and require an empty review();
    first_outline: the first drawn element (not just any) carries data-outline="1";
    embeds(name) -> (lo, hi): allowed <embed> count for the rich style (None skips the check);
    no_complex: path data must not contain complex numbers ("j ").
    """
    from ..svg_drawing import Drawing

    for name, make in makers.items():
        for style in ("rich", "flat"):
            g = make(style)
            assert_centered(test, g, name)
            if first_outline:
                test.assertEqual(first_drawn(g).get("data-outline"), "1", name)
            else:
                test.assertTrue([e for e in g.element.iter() if e.get("data-outline") == "1"], name)
            test.assertEqual(ET.tostring(g.element), ET.tostring(make(style).element), name)
            svg = ET.tostring(g.element, encoding="unicode")
            if no_complex:
                test.assertNotIn("j ", svg, name)  # no complex numbers leak into path data
            width = 1000 if paired else 600
            d = Drawing(width, 400 if paired else 500)
            if paired:
                a, b = d.place(g, at=(250, 200), key="p"), d.place(g, at=(750, 200), key="q")
                d.arrow(a, b)
            else:
                d.place(g, at=(300, 250), key="p")
            test.assertEqual(d.check(), [], name)
            if paired:
                test.assertEqual(d.review(), [], name)  # placed parts count as detailed subjects
            xml = quiet_slide(d, width=width)
            test.assertIn("<shape", xml, name)
            if style == "flat":
                test.assertNotIn("Gradient", svg, name)
                test.assertNotIn("<embed", xml, name)
            elif embeds is not None:
                lo, hi = embeds(name)
                test.assertTrue(lo <= xml.count("<embed") <= hi, (name, xml.count("<embed")))
    return len(makers)
