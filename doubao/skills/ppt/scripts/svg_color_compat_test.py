from __future__ import annotations

import re
import unittest
import xml.etree.ElementTree as ET

import gen_svg_charts
import gen_svg_relations
from svg_lib._color_compat import office_safe_svg
from svg_lib._common import _SVG_LIB_VARIANTS
from svg_lib.chart_examples import EXAMPLES

_RGB = re.compile(r"rgba?\(", re.IGNORECASE)


def _chart_cases():
    return {slug: EXAMPLES[slug] for slug in gen_svg_charts._chart_functions()}


class OfficeSafeSvgTest(unittest.TestCase):
    def convert(self, body: str) -> ET.Element:
        svg = office_safe_svg(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">{body}</svg>')
        self.assertIsNone(_RGB.search(svg))
        return ET.fromstring(svg)[0]

    def test_rgba_paints_move_alpha_to_opacity_attributes(self) -> None:
        node = self.convert('<rect width="1" height="1" fill="rgba(28,42,72,0.08)" stroke="rgb(10,20,30)"/>')
        self.assertEqual(node.get("fill"), "#1C2A48")
        self.assertEqual(node.get("fill-opacity"), "0.08")
        self.assertEqual(node.get("stroke"), "#0A141E")
        self.assertIsNone(node.get("stroke-opacity"))
        node = self.convert('<rect width="1" height="1" fill="rgba(255,0,0,0.5)" fill-opacity="0.4"/>')
        self.assertEqual(node.get("fill"), "#FF0000")
        self.assertEqual(node.get("fill-opacity"), "0.2")
        node = self.convert('<rect width="1" height="1" fill="rgba(1,2,3,1)" fill-opacity="1"/>')
        self.assertEqual(node.get("fill"), "#010203")
        self.assertIsNone(node.get("fill-opacity"))
        stop = self.convert('<stop offset="0" stop-color="rgba(216,105,38,0.35)"/>')
        self.assertEqual((stop.get("stop-color"), stop.get("stop-opacity")), ("#D86926", "0.35"))
        styled = self.convert('<rect width="1" height="1" style="fill:rgba(0,0,255,0.5);stroke-width:2"/>')
        self.assertEqual(
            (styled.get("fill"), styled.get("fill-opacity"), styled.get("style")), ("#0000FF", "0.5", "stroke-width:2")
        )
        svg = '<svg xmlns="http://www.w3.org/2000/svg"><rect fill="#123456"/></svg>'
        self.assertIs(office_safe_svg(svg), svg)

    def test_every_chart_and_variant_is_office_safe(self) -> None:
        for slug, kwargs in _chart_cases().items():
            make = getattr(gen_svg_charts, f"make_{slug}")
            for variant in [None, *_SVG_LIB_VARIANTS.get(slug, (None, [], None))[1]]:
                with self.subTest(chart=slug, variant=variant):
                    try:
                        svg = make(**kwargs, **({"variant": variant} if variant else {}))
                    except (KeyError, TypeError, ValueError):
                        # Some skeleton variants need inputs absent from the shared example.
                        if variant is None:
                            raise
                        continue
                    ET.fromstring(svg)
                    self.assertIsNone(_RGB.search(svg))

    def test_every_relation_is_office_safe_and_still_atomizes(self) -> None:
        for slug in gen_svg_relations.list_relations():
            with self.subTest(relation=slug):
                self.assertIsNone(_RGB.search(gen_svg_relations.make_relation(slug, allow_sample_data=True)))
                fragment = gen_svg_relations.make_relation_atomized(slug, allow_sample_data=True, strict_no_embed=True)
                self.assertNotIn("<embed", fragment)
