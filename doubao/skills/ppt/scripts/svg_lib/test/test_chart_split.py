"""chart_split semi-editable placement and compose/publish integration of chart and drawing embeds."""

import re
import unittest
import xml.etree.ElementTree as ET
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from ..svg_drawing import Drawing
from ..chart_split import split_chart_svg
import warnings
from ..atomize_svg_to_slide import compose_slide, publish_slide
from ..atomize_svg_to_slide._publish import _classify, _describe, _summarize
from gen_svg_charts import chart_slide, make_dumbbell
from text_fit import fit_text_boxes


# ====================================================================================================
# Contracts for one-call drawing shortcuts and semi-editable chart placement.
# ====================================================================================================


def fragment_children(xml):
    return list(ET.fromstring(xml).find("{*}data"))


class SplitChartTest(unittest.TestCase):
    SVG = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">'
        '<rect width="400" height="200" fill="#FAFAFC"/>'
        '<line x1="40" y1="180" x2="380" y2="180" stroke="#333"/>'
        '<rect x="60" y="80" width="40" height="100" fill="#5B1061"/>'
        '<rect x="160" y="60" width="40" height="120" fill="#5B1061"/>'
        '<rect x="260" y="100" width="40" height="80" fill="#9B2D6F"/>'
        '<circle cx="80" cy="85" r="2" fill="#111"/>'
        '<text x="20" y="195" text-anchor="start" font-size="12">A</text>'
        '<text x="380" y="20" text-anchor="end" font-size="14">Title</text></svg>'
    )

    def test_text_is_native_and_series_merge_into_one_shape(self):
        xml = split_chart_svg(self.SVG, x=40, y=60, width=800)
        kids = fragment_children(xml)
        texts = [k for k in kids if k.get("type") == "text"]
        self.assertEqual(sorted("".join(t.itertext()) for t in texts), ["A", "Title"])
        customs = [k for k in kids if k.get("type") == "custom"]
        self.assertEqual(len(customs), 2)
        self.assertEqual(max(c.get("path").count("M") for c in customs), 2)
        self.assertTrue(any(k.tag.endswith("embed") for k in kids))
        embeds = "".join(ET.tostring(k, encoding="unicode") for k in kids if k.tag.endswith("embed"))
        self.assertNotIn("<text", embeds.replace("ns0:", ""))

    def test_paint_order_keeps_marks_above_bars(self):
        xml = split_chart_svg(self.SVG, x=0, y=0, width=400)
        kids = fragment_children(xml)
        order = [("embed" if k.tag.endswith("embed") else k.get("type")) for k in kids]
        dot_embed = max(
            i for i, k in enumerate(kids) if k.tag.endswith("embed") and "circle" in ET.tostring(k, encoding="unicode")
        )
        bar = min(i for i, t in enumerate(order) if t == "custom")
        self.assertGreater(dot_embed, bar, order)

    def test_overlapping_same_color_marks_are_not_merged(self):
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
            '<rect x="10" y="10" width="40" height="40" fill="#5B1061"/>'
            '<rect x="20" y="20" width="40" height="40" fill="#FFFFFF"/>'
            '<rect x="30" y="30" width="40" height="40" fill="#5B1061"/></svg>'
        )
        kids = fragment_children(split_chart_svg(svg, x=0, y=0, width=100))
        paths = [k for k in kids if k.get("type") == "custom"]
        self.assertEqual(len(paths), 3)

    def test_merge_blocks_false_keeps_marks_in_svg(self):
        kids = fragment_children(split_chart_svg(self.SVG, x=0, y=0, width=400, merge_blocks=False))
        self.assertFalse(any(k.get("type") == "custom" for k in kids))

    def test_rejects_svg_without_viewbox(self):
        with self.assertRaises(ValueError):
            split_chart_svg('<svg xmlns="http://www.w3.org/2000/svg"/>', x=0, y=0, width=10)


class ComposeAutoSplitTest(unittest.TestCase):
    def test_hand_wrapped_chart_embed_becomes_semi_editable(self):
        import re

        svg = make_dumbbell(rows=[{"label": "P2", "before": 120, "after": 96}], width=880, height=300)
        vw, vh = map(float, re.search(r'viewBox="([^"]+)"', svg).group(1).split()[2:])
        page = '<slide xmlns="https://www.larkoffice.com/sml/2.0"><data></data></slide>'
        out = compose_slide(
            page, f'<embed topLeftX="40" topLeftY="100" width="880" height="{880 * vh / vw:.2f}">{svg}</embed>'
        )
        self.assertIn('type="text"', out)
        self.assertNotIn("data-chart-lib", out)

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            forced = compose_slide(
                page,
                chart_slide(
                    "dumbbell",
                    x=40,
                    y=100,
                    width=880,
                    height=300,
                    editable=False,
                    rows=[{"label": "a", "before": 1, "after": 2}],
                ),
            )
        self.assertIn('type="text"', forced)  # editable=False no longer produces an uneditable chart
        self.assertTrue(any("editable=False is ignored" in str(w.message) for w in caught))


class ComposeDrawingEmbedTest(unittest.TestCase):
    def test_hand_wrapped_drawing_svg_is_atomized_to_native_shapes(self):
        d = Drawing(600, 300)
        a = d.box_at((150, 150), "A 节点", font_size=16, stroke="#333")
        b = d.box_at((450, 150), "B 节点", font_size=16, stroke="#333")
        d.arrow(a, b)
        page = '<slide xmlns="https://www.larkoffice.com/sml/2.0"><data></data></slide>'
        out = compose_slide(page, f'<embed topLeftX="40" topLeftY="100" width="600" height="300">{d.to_svg()}</embed>')
        self.assertNotIn("<embed", out)
        self.assertIn("A 节点", out)
        xs = [float(v) for v in re.findall(r'topLeftX="([\d.]+)"', out)]
        self.assertTrue(min(xs) >= 40 - 1)


class SpeedPathTest(unittest.TestCase):
    def test_chart_slide_grows_instead_of_raising(self):
        rows = [{"label": f"Trial {i}（长标签用于换行测试）", "before": 10 + i, "after": 20 + i} for i in range(5)]
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            frag = chart_slide("dumbbell", box=(0, 0, 300, 200), rows=rows, note="注释" * 30)
        self.assertIn('type="text"', frag)
        self.assertTrue(any("scale" in str(w.message) for w in caught))

    def test_drawing_check_reports_real_conflicts_only(self):
        d = Drawing(600, 300)
        a = d.box_at((100, 150), "A", font_size=16, stroke="#333")
        b = d.box_at((500, 150), "B", font_size=16, stroke="#333")
        d.arrow(a, b)
        self.assertEqual(d.check(), [])
        d.box_at((300, 150), "middle", font_size=16, stroke="#333")
        kinds = {p["kind"] for p in d.check()}
        self.assertEqual(kinds, {"line_through_text"})


class PublishClassifyTest(unittest.TestCase):
    def _page(self):
        hand = (
            '<shape type="text" topLeftX="40" topLeftY="20" width="400" height="30"><content><p>标题</p></content></shape>'
            '<shape type="rect" topLeftX="40" topLeftY="60" width="100" height="40"/>'
        )
        gen = (
            '<shape type="custom" topLeftX="100" topLeftY="100" width="50" height="50"/>'
            '<shape type="custom" topLeftX="120" topLeftY="110" width="50" height="50"/>'
            '<shape type="text" topLeftX="100" topLeftY="200" width="80" height="10"><content><p>A</p></content></shape>'
            '<shape type="text" topLeftX="100" topLeftY="205" width="80" height="10"><content><p>B</p></content></shape>'
        )
        return f'<slide xmlns="https://www.larkoffice.com/sml/2.0"><data>{hand}{gen}</data></slide>', {2, 3, 4, 5}

    def _err(self, a, b, code="bbox_overlap"):
        return {"code": code, "elements": [a, b], "related_objects": [{"xml_path": a}, {"xml_path": b}]}

    def test_generated_shape_overlap_is_waived_but_text_collision_and_hand_written_are_reported(self):
        xml, generated = self._page()
        shapes = self._err("slide[1]/data/shape[3]", "slide[1]/data/shape[4]")
        texts = self._err("slide[1]/data/shape[5]", "slide[1]/data/shape[6]")
        hand = self._err("slide[1]/data/shape[2]", "slide[1]/data/shape[3]")
        other = {"code": "text_color_contrast", "elements": ["slide[1]/data/shape[5]"], "related_objects": []}
        ignorable, report = _classify(xml, generated, [shapes, texts, hand, other])
        self.assertEqual(ignorable, [shapes])
        self.assertEqual(report, [texts, hand, other])
        self.assertEqual([o["text"] for o in _describe(xml, texts)["objects"]], ["A", "B"])

    def test_without_presentation_it_only_composes(self):
        xml, _ = self._page()
        r = publish_slide(xml)
        self.assertTrue(r["ok"])
        self.assertEqual(r["screenshot"], "")

        self.assertEqual(r["page_xml"], fit_text_boxes(xml)[0])  # too-short text boxes are grown before writing


class PublishDescribeTest(unittest.TestCase):
    def test_describe_gives_boxes_sources_and_a_fix(self):
        xml = (
            '<slide xmlns="https://www.larkoffice.com/sml/2.0"><data>'
            '<shape type="text" topLeftX="40" topLeftY="100" width="300" height="30"><content fontSize="16"><p>正文一</p></content></shape>'
            '<shape type="text" topLeftX="40" topLeftY="120" width="300" height="30"><content fontSize="16"><p>正文二</p></content></shape>'
            "</data></slide>"
        )
        err = {
            "code": "bbox_overlap",
            "rule": {"name": "text_visual_bounds_do_not_overlap"},
            "measurement": {"intersection_width": 300, "intersection_height": 10},
            "related_objects": [
                {"xml_path": "slide[1]/data/shape[1]", "bbox": {"x": 40, "y": 100, "width": 300, "height": 30}},
                {"xml_path": "slide[1]/data/shape[2]", "bbox": {"x": 40, "y": 120, "width": 300, "height": 30}},
            ],
        }
        d = _describe(xml, err)
        self.assertEqual([o["text"] for o in d["objects"]], ["正文一", "正文二"])
        self.assertEqual(d["objects"][1]["xml_box"], [40.0, 120.0, 300.0, 30.0])
        self.assertEqual(d["objects"][0]["font_size"], 16.0)
        self.assertEqual({o["source"] for o in d["objects"]}, {"page_xml"})
        self.assertIn("下移至少 12px", d["fix"])
        self.assertTrue(_summarize([d])[0].startswith("bbox_overlap ×1"))
