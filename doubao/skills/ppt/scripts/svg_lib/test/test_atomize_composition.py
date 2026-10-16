"""Atomizer composition, serialization, advanced mapping, drawing tools and native text layout."""

import math
import random
import re
import tempfile
import unittest
import xml.etree.ElementTree as ET
import sys
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[2]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from ._helpers import SvgTestCase
from ..atomize_svg_to_slide import compose_slide, serialize_slide, set_mapping, _font_metrics
from ..atomize_svg_to_slide._geometry import parse_transform, transform_element, path_segments
from ..atomize_svg_to_slide._stroke import dash_path
from ..atomize_svg_to_slide._resources import resource_closure
from ..atomize_svg_to_slide._font_metrics import measure_text
from ..atomize_svg_to_slide._bounds import paint_bounds
from ..atomize_svg_to_slide._markers import _placements
import ast
import importlib
import json
import sxsd_validator
from ..atomize_svg_to_slide import atomize_svg_to_slide, convert_path, convert_text, inspect_svg, set_subtitle_relax
from ..atomize_svg_to_slide._bounds import svg_bounds
from ..atomize_svg_to_slide._config import _CFG
from ..atomize_svg_to_slide._effects import _orient, svg_embed
from ..atomize_svg_to_slide._font_metrics import TextMetrics, estimate_advance, resolve_font, text_advance
from ..atomize_svg_to_slide._geometry import arc_to_cubics
from ..atomize_svg_to_slide._styles import flatten_styles
from ..atomize_svg_to_slide._svg_input import _effective, iter_atoms, parse_svg
from ..svg_drawing import (
    Box,
    CoordinateMap,
    Curve,
    Drawing,
    Geometry,
    Node,
    annular_sector,
    circle_tangent_points,
    circular_arc,
    cutaway,
    drawing_help,
    ellipse,
    extrude,
    path,
    repeat_along_path,
    ribbon,
    sample_function,
    sample_parametric,
    smooth_curve,
    wrap_label,
)
from types import SimpleNamespace


# ====================================================================================================
# Composition, effects and advanced mapping regressions (version-independent).
# ====================================================================================================


class StaticCssTest(SvgTestCase):
    @staticmethod
    def flattened(body):
        root = ET.fromstring('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">' + body + "</svg>")
        return flatten_styles(root)

    def test_css_cascade_use_compositing_and_stop_inheritance(self):
        root = self.flattened("""<style>
          .x, #not_this { fill: red; }
          rect.x { fill: blue; stroke: red; }
          .x { stroke: green; }
          rect.x { stroke: orange; }
          rect.x.y#special { fill: purple; }
        </style><style>rect.x { stroke: blue; }</style>
        <rect id="ordinary" class="x" fill="white" width="10" height="10"/>
        <rect id="special" class="x y" width="10" height="10"/>""")
        by_id = {node.get("id"): node for node in root.iter()}
        self.assertEqual(by_id["ordinary"].get("fill"), "#0000ff")
        self.assertEqual(by_id["ordinary"].get("stroke"), "#0000ff")
        self.assertEqual(by_id["special"].get("fill"), "#800080")
        self.assertFalse(root.findall("{*}style"))
        self.assertTrue(all("class" not in node.attrib and "style" not in node.attrib for node in root.iter()))
        root = self.flattened("""<style>
          #a, #b { fill: red !important; stroke: red !important; stroke: blue; }
          .x.x { stroke: green !important; }
          #b { fill: blue !important; }
        </style><rect id="a" class="x" style="fill:green; stroke:orange !important; stroke:purple"/>
        <rect id="b" class="x" style="fill:white !IMPORTANT; fill:black"/>""")
        a, b = list(root)
        self.assertEqual(a.get("fill"), "#ff0000")
        self.assertEqual(a.get("stroke"), "#ffa500")
        self.assertEqual(b.get("fill"), "#ffffff")
        self.assertEqual(b.get("stroke"), "#ff0000")
        root = self.flattened(
            "<style>.x{fill:red}.x\u00a0{stroke:blue}</style>"
            '<rect id="a" class="x\u00a0y" fill="#ffffff"/>'
            '<rect id="b" class="x\u00a0"/>'
        )
        a, b = list(root)
        self.assertEqual(a.get("fill"), "#ffffff")
        self.assertIsNone(a.get("stroke"))
        self.assertIsNone(b.get("fill"))
        self.assertEqual(b.get("stroke"), "#0000ff")
        root = self.flattened("""<style>/* ; } ignored */ .x {
          font-family: "A; B: C", sans-serif;
          fill: url("#g:paint"); stroke: rgb(1, 2, 3) ! /* comment */ important;
        }</style><defs><linearGradient id="g:paint"/></defs><rect class="x"/>""")
        rect = root.find("{*}rect")
        self.assertEqual(rect.get("font-family"), '"A; B: C", sans-serif')
        self.assertEqual(rect.get("fill"), "url(#g:paint)")
        self.assertEqual(rect.get("stroke"), "rgb(1, 2, 3)")
        source = """<svg viewBox="0 0 100 100"><style>
          .own {fill:red} .context {fill:currentColor}
          #blue {fill:blue !important; color:blue} #green {color:green}
        </style><defs fill="purple"><rect id="own" class="own" width="10" height="10"/>
          <rect id="context" class="context" width="10" height="10"/>
        </defs><use id="blue" href="#own"/><use id="green" href="#context" x="20"/></svg>"""
        root, defs = parse_svg(source)
        atoms = [ET.fromstring(fragment) for kind, fragment in iter_atoms(root, defs) if kind == "rect"]
        self.assertEqual([node.get("fill") for node in atoms], ["#ff0000", "#008000"])
        self.assertTrue(all("class" not in node.attrib and "style" not in node.attrib for node in root.iter()))
        body = """<style>
          .fade {opacity:.5} .paint {fill:url('#gradient')}
          .start {stop-color:red} .end {stop-color:blue}
          .arrow {fill:context-stroke} .edge {stroke:green; marker-end:url(#arrow)}
        </style><defs><linearGradient id="gradient"><stop class="start" offset="0"/>
          <stop class="end" offset="1"/></linearGradient>
          <marker id="arrow" markerWidth="5" markerHeight="5" refX="5" refY="2.5" orient="auto">
            <path class="arrow" d="M0 0 L5 2.5 L0 5 Z"/>
          </marker></defs><g class="fade"><rect class="paint" x="10" y="10" width="45" height="40"/>
          <rect class="paint" x="30" y="20" width="45" height="40"/>
          <path class="edge" d="M10 80 H80"/></g>"""
        result = self.convert(body)
        embed = result.find("{*}embed")
        self.assertIsNotNone(embed)
        self.assertEqual(len(result.findall("{*}embed")), 1)
        self.assertFalse(embed.findall(".//{*}style"))
        self.assertTrue(all("class" not in node.attrib and "style" not in node.attrib for node in embed.iter()))
        self.assertIsNotNone(embed.find(".//{*}linearGradient"))
        # Markers are expanded into plain shapes: the embed renderer does not accept <marker>.
        self.assertIsNone(embed.find(".//{*}marker"))
        self.assertFalse(any(node.get("marker-end") for node in embed.iter()))
        self.assertEqual(len(embed.findall(".//{*}path")), 2)
        self.assertTrue(any(node.get("opacity") == "0.5" for node in embed.findall(".//{*}g")))
        self.assertTrue(all(node.get("opacity") is None for node in embed.findall(".//{*}rect")))
        source = """<svg><style>.g {stop-color:red; stop-opacity:.25}</style><defs stop-color="blue">
          <linearGradient class="g" id="plain"><stop offset="0"/><stop offset="1"/></linearGradient>
          <linearGradient class="g" id="explicit"><stop offset="0" stop-color="inherit" stop-opacity="inherit"/></linearGradient>
          <linearGradient id="inherit"><stop offset="0" stop-color="inherit"/></linearGradient>
        </defs></svg>"""
        _, resources = parse_svg(source)
        gradients = {node.get("id"): node for node in ET.fromstring(resources)}
        self.assertIsNone(gradients["plain"][0].get("stop-color"))
        self.assertIsNone(gradients["plain"][0].get("stop-opacity"))
        self.assertEqual(gradients["explicit"][0].get("stop-color"), "#ff0000")
        self.assertEqual(gradients["explicit"][0].get("stop-opacity"), ".25")
        self.assertIsNone(gradients["inherit"][0].get("stop-color"))
        parent = _effective(ET.fromstring('<g opacity=".5"/>'), {}).attrib
        child = _effective(ET.fromstring('<rect id="inherit" opacity="inherit"/>'), parent)
        self.assertEqual(child.get("id"), "inherit")
        self.assertEqual(child.get("opacity"), "0.5")
        middle = _effective(ET.fromstring("<g/>"), parent).attrib
        self.assertIsNone(_effective(ET.fromstring('<rect opacity="inherit"/>'), middle).get("opacity"))

    def test_unsupported_external_and_absent_stylesheets(self):
        invalid = (
            ".unused > rect{fill:red}",
            ".unused rect{fill:red}",
            ".unused+rect{fill:red}",
            "rect:hover{fill:red}",
            "rect[fill]{fill:red}",
            "svg|rect{fill:red}",
            "@media screen{rect{fill:red}}",
            '@import url("other.css");',
            ".unused{transform:translate(10px,20px)}",
            ".unused{fill:var(--paint)}",
            ".unused{filter:blur(2px)}",
            '.unused{fill:url("https://example.com/a;b.svg#g")}',
            '.unused{fill:url("#a;b")}',
            ".unused{opacity:50%}",
            ".unused{font-size:1em}",
            ".unused{font-weight:bolder}",
            ".unused{color:currentColor}",
            ".unused{fill:initial}",
            ".unused{font-family:UNSET}",
            ".unused{fill:red !bad}",
            ".-1{fill:red}",
            ".-{fill:red}",
            ".unused{stroke-dasharray:3,,2}",
            ".unused{font-family:inherit, Arial}",
            ".unused{font-family:123}",
            ".unused{font-size:0}",
            ".unused{font-size:0px}",
            ".unused{fill:url(#a%20b)}",
            ".unused{unknown:blue}",
            ".unused{fill:red",
            ".unused,{fill:red}",
        )
        for css in invalid:
            with self.subTest(css=css):
                root = ET.Element("svg")
                ET.SubElement(root, "style").text = css
                ET.SubElement(root, "rect", {"class": "ok", "style": "fill:blue"})
                before = ET.tostring(root)
                with self.assertRaisesRegex(ValueError, "Unsupported static SVG CSS"):
                    flatten_styles(root)
                self.assertEqual(ET.tostring(root), before)
        for source in (
            '<?xml-stylesheet type="text/css" href="theme.css"?><svg/>',
            '<svg><link rel="stylesheet" href="theme.css"/></svg>',
            '<svg><style media="screen">rect{fill:red}</style></svg>',
            '<svg><style type="text/other">rect{fill:red}</style></svg>',
            '<svg><rect class="x" fill="url(https://example.invalid/paint.svg#g)"/></svg>',
            '<svg><defs><linearGradient class="x" href="https://example.invalid/g.svg#g"/></defs></svg>',
            '<svg><text class="x" font-size="0">Hidden</text></svg>',
        ):
            with self.subTest(source=source), self.assertRaisesRegex(ValueError, "Unsupported static SVG CSS"):
                parse_svg(source)
        root = ET.fromstring(
            '<svg><g fill="#ff0000"><rect width="10" height="10" style="stroke: #123456; stroke-width: 2"/></g></svg>'
        )
        before = ET.tostring(root)
        self.assertIs(flatten_styles(root), root)
        self.assertEqual(ET.tostring(root), before)


class SlideCompositionTest(SvgTestCase):
    sml = "https://www.larkoffice.com/sml/2.0"
    svg = "http://www.w3.org/2000/svg"
    xlink = "http://www.w3.org/1999/xlink"

    def page(self, body="", *, attributes=""):
        return f'<slide xmlns="{self.sml}" {attributes}><data>{body}</data></slide>'

    def test_composition_appends_in_order_and_keeps_page_metadata(self):
        first = self.atomize_body('<rect x="10" y="20" width="30" height="40" fill="#286A70"/>')
        second = self.atomize_body(
            '<rect x="5" y="8" width="60" height="30" rx="6" fill="white" stroke="#6B7886" stroke-dasharray="5 4"/>'
        )
        self.assertIsInstance(first, str)
        self.assertIsInstance(second, str)
        base = self.page(
            '<shape id="existing" type="text" topLeftX="1" topLeftY="2" '
            'width="80" height="30"><content><p>Existing</p></content></shape>'
        )
        manual = ET.fromstring(base)
        for fragment in (first, second):
            manual.find("{*}data").extend(ET.fromstring(fragment).find("{*}data"))
        result = compose_slide(base, first, second)
        self.assertIsInstance(result, str)
        root = ET.fromstring(result)
        self.assertEqual(len(root.findall("{*}data")), 1)
        self.assertEqual(len(root.findall(".//{*}slide")), 0)
        self.assertEqual(ET.tostring(root), ET.tostring(ET.fromstring(serialize_slide(manual))))
        embedded = re.search(r"<embed\b[^>]*>(.*?)</embed>", result, re.S).group(1)
        self.assertEqual(ET.fromstring(embedded).tag, f"{{{self.svg}}}svg")
        base = (
            f'<s:slide xmlns:s="{self.sml}" id="page1" custom="keep">'
            '<s:style><s:background color="rgb(1,2,3)"/></s:style>'
            "<s:note>Presenter note</s:note></s:slide>"
        )
        fragment = self.page(
            '<shape id="formula1" type="formula" topLeftX="1.50" '
            'topLeftY="2" width="30" height="20" formula="x^2 &amp; y"/>'
        )
        result = ET.fromstring(compose_slide(base, fragment))
        self.assertEqual(result.attrib, {"id": "page1", "custom": "keep"})
        self.assertEqual([node.tag.rsplit("}", 1)[-1] for node in result], ["style", "data", "note"])
        self.assertEqual(result.find("{*}note").text, "Presenter note")
        self.assertEqual(result.find("{*}style/{*}background").get("color"), "rgb(1,2,3)")
        self.assertEqual(
            result.find("{*}data/{*}shape").attrib, ET.fromstring(fragment).find("{*}data/{*}shape").attrib
        )
        self.assertEqual(len(ET.fromstring(compose_slide(base)).find("{*}data")), 0)
        data_attrs = self.page("<shape/>").replace("<data>", '<data custom="keep">')
        self.assertEqual(ET.fromstring(compose_slide(data_attrs)).find("{*}data").get("custom"), "keep")
        body = '<shape id="label" type="text"><content><p>A &amp; B</p></content></shape><line id="edge"/>'
        base = self.page('<shape id="existing"/>').replace("</slide>", "<note>keep</note></slide>")
        expected = compose_slide(base, self.page(body))
        for source in (body, "<data>" + body + "</data>", f'<data xmlns="{self.sml}">' + body + "</data>"):
            with self.subTest(source=source):
                self.assertEqual(compose_slide(base, source), expected)
        one = f'<s:shape xmlns:s="{self.sml}" id="one"/>'
        root = ET.fromstring(compose_slide(base, one, body))
        self.assertEqual([x.get("id") for x in root.find("{*}data")], ["existing", "one", "label", "edge"])
        self.assertEqual(root.find("{*}note").text, "keep")

    def test_invalid_arguments_wrappers_and_fragment_metadata_are_rejected(self):
        for source in (None, ET.Element("slide"), Path("page.xml"), [], b"<slide/>"):
            with self.subTest(source=source), self.assertRaisesRegex(TypeError, "page_xml.*XML string"):
                compose_slide(source)
            with (
                self.subTest(fragment=source),
                self.assertRaisesRegex(TypeError, r"atomized_fragments\[0\].*XML string"),
            ):
                compose_slide(self.page(), source)
        for source in ("<slide", self.page("<svg:rect/>")):
            with self.subTest(source=source), self.assertRaisesRegex(ValueError, "page_xml: invalid XML"):
                compose_slide(source)
        invalid = (
            f'<svg xmlns="{self.svg}"/>',
            f'<presentation xmlns="{self.sml}"/>',
            "<slide><data/></slide>",
            self.page().replace("<data></data>", "<data/><data/>"),
            self.page().replace("<data>", '<data xmlns="urn:wrong">'),
            self.page("<data/>"),
            self.page("<shape><slide/></shape>"),
            self.page("<presentation/>"),
            self.page('<data xmlns=""/>'),
            self.page('&lt;shape width="10"/&gt;'),
            self.page("<shape/>raw text"),
        )
        for source in invalid:
            with self.subTest(source=source), self.assertRaises(ValueError):
                compose_slide(source)
            with self.subTest(fragment=source), self.assertRaises(ValueError):
                compose_slide(self.page(), source)
        with self.assertRaises(ValueError):
            compose_slide(f'<data xmlns="{self.sml}"/>')
        for source in (
            "",
            "<!-- no objects -->",
            "<style/>",
            "<note>text</note>",
            '<data id="lost"><shape/></data>',
            '<data xml:lang="zh"><shape/></data>',
            '<shape xmlns=""/>',
            '<shape xmlns="urn:foreign"/>',
            "<shape/><svg:svg/>",
            "<shape/>raw text",
            "<shape><data/></shape>",
            "<data><data/></data>",
            "<shape/><note>keep me</note>",
        ):
            with self.subTest(source=source), self.assertRaisesRegex(ValueError, "atomized_fragments"):
                compose_slide(self.page(), source)
        with self.assertRaisesRegex(ValueError, "duplicate SML id"):
            compose_slide(self.page('<shape id="used"/>'), '<shape id="used"/>')
        fragments = (
            f'<slide xmlns="{self.sml}"/>',
            self.page().replace("<data>", "<style/><data>"),
            self.page().replace("</data>", "</data><note>keep me</note>"),
            self.page().replace("<data>", "<!--page comment--><data>"),
            self.page().replace("<data>", "page text<data>"),
            self.page(attributes='id="fragment-page"'),
            self.page(attributes='xml:lang="zh"'),
            self.page(attributes='xmlns:c="urn:custom" c:role="page"'),
            self.page().replace("<data>", '<data id="fragment-data">'),
        )
        for fragment in fragments:
            with self.subTest(fragment=fragment), self.assertRaisesRegex(ValueError, r"atomized_fragments\[0\]"):
                compose_slide(self.page(), fragment)

    def test_ids_resources_and_prefix_bindings_survive_composition(self):
        svg = (
            f'<svg xmlns="{self.svg}" xmlns:xlink="{self.xlink}">'
            '<defs><path id="part" d="M0 0L5 5"/></defs><use xlink:href="#part"/></svg>'
        )
        result = compose_slide(self.page(), '<embed id="a">' + svg + "</embed>", '<embed id="b">' + svg + "</embed>")
        for value in re.findall(r"<embed\b[^>]*>(.*?)</embed>", result, re.S):
            self.assertEqual(ET.tostring(ET.fromstring(value)), ET.tostring(ET.fromstring(svg)))
        base = self.page('<shape id="base"/>', attributes='id="page"')
        a, b = self.page('<shape id="a"/>'), self.page('<shape id="b"/>')
        result = ET.fromstring(compose_slide(base, a, b))
        self.assertEqual([node.get("id") for node in result.find("{*}data")], ["base", "a", "b"])
        for arguments in (
            (base, self.page('<shape id="base"/>')),
            (base, self.page('<shape id="page"/>')),
            (base, a, a),
            (base, self.page('<shape id="x"/><shape id="x"/>')),
            (self.page('<shape id="x"/><shape id="x"/>'),),
        ):
            with self.subTest(arguments=arguments), self.assertRaisesRegex(ValueError, "duplicate SML id"):
                compose_slide(*arguments)
        base = self.page('<shape id=""/><shape id=""/>', attributes='id=""')
        fragment = self.page('<shape id=""/><shape/>')
        result = ET.fromstring(compose_slide(base, fragment, fragment))
        self.assertEqual(result.get("id"), "")
        self.assertEqual([node.get("id") for node in result.find("{*}data")], ["", "", "", None, "", None])
        self.assertEqual(ET.tostring(ET.fromstring(compose_slide(base))), ET.tostring(ET.fromstring(base)))
        with self.assertRaisesRegex(ValueError, "duplicate SML id"):
            compose_slide(base, fragment, self.page('<shape id="used"/><shape id="used"/>'))
        svg = (
            f'<svg xmlns="{self.svg}" viewBox="0 0 100 80">'
            '<defs><linearGradient id="soft"><stop offset="0" stop-color="#123456"/>'
            '</linearGradient></defs><svg x="5" y="6" width="50" height="40">'
            '<rect id="part" width="20" height="10" fill="url(#soft)"/></svg></svg>'
        )
        a = self.page(f'<embed id="first" topLeftX="10">{svg}</embed>')
        b = self.page(f'<embed id="second" topLeftX="20">{svg}</embed>')
        result = compose_slide(self.page('<shape id="soft"/>'), a, b)
        for embedded in re.findall(r"<embed\b[^>]*>(.*?)</embed>", result, re.S):
            inner = ET.fromstring(embedded)
            self.assertEqual(ET.tostring(inner), ET.tostring(ET.fromstring(svg)))
        with self.assertRaisesRegex(ValueError, "duplicate SML id"):
            compose_slide(self.page(), a, a)
        base = self.page(attributes='xmlns:role="urn:target"')
        fragment = (
            f'<s:slide xmlns:s="{self.sml}" xmlns:v="{self.svg}" '
            f'xmlns:xlink="{self.xlink}" xmlns:role="urn:root"><s:data xmlns:role="urn:local">'
            '<s:shape role:kind="role:shape"/><s:embed><v:svg viewBox="0 0 10 10">'
            '<v:defs><v:path id="p" d="M 1 2 L 3 4"/></v:defs>'
            '<v:use xlink:href="#p" role:kind="role:part"/></v:svg></s:embed></s:data></s:slide>'
        )
        result = compose_slide(base, fragment)
        native = re.search(r"<shape\b[^>]*/>", result).group()
        self.assertIn('xmlns:role="urn:local"', native)
        self.assertEqual(ET.fromstring(result).find("{*}data/{*}shape").get("{urn:local}kind"), "role:shape")
        embedded = re.search(r"<embed\b[^>]*>(.*?)</embed>", result, re.S).group(1)
        self.assertIn('xmlns:role="urn:local"', embedded)
        use = ET.fromstring(embedded).find(f"{{{self.svg}}}use")
        self.assertEqual(use.get(f"{{{self.xlink}}}href"), "#p")
        self.assertEqual(use.get("{urn:local}kind"), "role:part")

    def test_comments_whitespace_text_and_order_survive_without_global_state(self):
        base = self.page('<shape><content><p xml:space="preserve"> A &amp; B </p></content></shape>')
        fragment = self.page('\n<!--keep--><?test value?><shape topLeftX="1.50"/>\n')
        inputs, settings = (base, fragment), dict(_CFG)
        expected = compose_slide(base, fragment, self.page(), fragment)
        self.assertEqual(expected.count("<!--keep--><?test value?>"), 2)
        self.assertEqual(expected.count('topLeftX="1.50"'), 2)
        self.assertEqual(ET.fromstring(expected).find(".//{*}p").text, " A & B ")
        with patch.dict(ET._namespace_map, {self.sml: "changed", self.svg: ""}, clear=True):
            registry = dict(ET._namespace_map)
            with patch.object(ET, "register_namespace", side_effect=AssertionError("global registry")):
                self.assertEqual(compose_slide(base, fragment, self.page(), fragment), expected)
            self.assertEqual(ET._namespace_map, registry)
        self.assertEqual((base, fragment), inputs)
        self.assertEqual(_CFG, settings)

    def test_native_hex_colours_fields_alpha_literals_and_opaque_content(self):
        body = (
            '<shape type="rect" topLeftX="1.50" topLeftY="2" width="100" height="40">'
            '<fill><fillPattern foregroundColor="#abc" backgroundColor="#abc"/></fill>'
            '<border color="#abc"/><shadow color="#abc"/>'
            '<content color="#abc" backgroundColor="#abc" bulletColor="#abc">'
            '<p bulletColor="#abc"><span color="#abc" backgroundColor="#abc">'
            '<outline color="#abc">HEX #abc</outline></span><a href="#abc">ref</a></p>'
            '<ul bulletColor="#abc"><li><p>U</p></li></ul>'
            '<ol bulletColor="#abc"><li><p>O</p></li></ol></content></shape>'
            '<table><tr><td><borderTop color="#abc"/><borderRight color="#abc"/>'
            '<borderBottom color="#abc"/><borderLeft color="#abc"/></td></tr></table>'
        )
        source = self.page(body).replace("<data>", '<style><fill><fillColor color="#abc"/></fill></style><data>')
        original = ET.fromstring(source)
        root = ET.fromstring(compose_slide(source))
        converted = [value for node in root.iter() for value in node.attrib.values() if value == "rgb(170,187,204)"]
        self.assertEqual(len(converted), 18)
        self.assertEqual(root.find(".//{*}a").get("href"), "#abc")
        self.assertEqual(root.find(".//{*}shape").get("topLeftX"), "1.50")
        self.assertEqual(list(root.itertext()), list(original.itertext()))
        cases = {
            " #aBc ": "rgb(170,187,204)",
            "#aBcDeF": "rgb(171,205,239)",
            "#1234": "rgba(17,34,51,0.2666666667)",
            "#01020380": "rgba(1,2,3,0.5019607843)",
            "#0000": "rgba(0,0,0,0)",
            "#ffffffFF": "rgba(255,255,255,1)",
            "white": "rgb(255,255,255)",
            " SteelBlue ": "rgb(70,130,180)",
            "red": "rgb(255,0,0)",
            "transparent": "rgba(0,0,0,0)",
        }
        for value, expected in cases.items():
            with self.subTest(value=value):
                source = self.page(f'<shape alpha="0.25"><fill><fillColor color="{value}"/></fill></shape>')
                root = ET.fromstring(compose_slide(source))
                self.assertEqual(root.find(".//{*}fillColor").get("color"), expected)
                self.assertEqual(root.find(".//{*}shape").get("alpha"), "0.25")
        values = (
            "",
            " ",
            "none",
            "inherit",
            "currentColor",
            "notacolor",
            " rgb(1, 2, 3) ",
            "rgba(1,2,3,0.2500)",
            "#12",
            "#12345",
            "#1234567",
            "#ggg",
            "#12345678more",
            "url(#abc)",
            "linear-gradient(90deg, #abc 0%, #def 100%)",
        )
        for value in values:
            with self.subTest(value=value):
                source = self.page(f'<shape><content color="{value}" backgroundColor=""><p>text</p></content></shape>')
                content = ET.fromstring(compose_slide(source)).find(".//{*}content")
                self.assertEqual(content.get("color"), value)
                self.assertEqual(content.get("backgroundColor"), "")
                self.assertNotIn("bulletColor", content.attrib)
        source = self.page(
            f'<shape xmlns:c="urn:custom" c:color="#123" color="#234" formula="#345">'
            '<content color="#abc" c:color="#456"><p color="#567">literal #678'
            '<strong color="#789">strong</strong></p></content></shape>'
            '<chart><stop color="#123"/><color value="#234"/>'
            '<content color="#345"/><shadow color="#456"/></chart>'
            f'<external xmlns="urn:external"><content xmlns="{self.sml}" color="#567"/></external>'
            f'<plain xmlns=""><content xmlns="{self.sml}" color="#678"/></plain>'
            f'<embed><svg xmlns="{self.svg}" color="#789"><rect fill="#abc"/>'
            f'<foreignObject><content xmlns="{self.sml}" color="#def"/></foreignObject>'
            '</svg><shadow color="#abc"/></embed>'
        )
        before = ET.fromstring(source)
        after = ET.fromstring(compose_slide(source))
        before_nodes, after_nodes = list(before.iter()), list(after.iter())
        self.assertEqual(len(before_nodes), len(after_nodes))
        changes = []
        for old, new in zip(before_nodes, after_nodes):
            self.assertEqual((old.tag, old.text, old.tail), (new.tag, new.text, new.tail))
            for name, value in old.attrib.items():
                if value != new.get(name):
                    changes.append((new.tag, name, value, new.get(name)))
        self.assertEqual(
            changes,
            [
                (f"{{{self.sml}}}content", "color", "#abc", "rgb(170,187,204)"),
                (f"{{{self.sml}}}shadow", "color", "#abc", "rgb(170,187,204)"),
            ],
        )

    def test_hex_composition_is_idempotent_and_does_not_change_serializer_or_inputs(self):
        base = self.page(
            '<shape id="base"><content color="#abc"><p xml:space="preserve"> A #def </p></content></shape>'
        )
        base = base.replace("</slide>", '<note><content color="#def"><p>Note</p></content></note></slide>')
        fragment = self.page('<shape id="added"><border color="#12345680"/></shape>')
        originals, settings, registry = (base, fragment), dict(_CFG), dict(ET._namespace_map)
        tree = ET.fromstring(base)
        tree_before = ET.tostring(tree)
        with patch.object(ET, "register_namespace", side_effect=AssertionError("global registry")):
            result = compose_slide(base, fragment)
            self.assertEqual(compose_slide(result), result)
            serialized = serialize_slide(tree)
        self.assertEqual(ET.fromstring(serialized).find(".//{*}content").get("color"), "#abc")
        self.assertEqual(ET.tostring(tree), tree_before)
        self.assertEqual((base, fragment), originals)
        self.assertEqual(_CFG, settings)
        self.assertEqual(ET._namespace_map, registry)
        self.assertEqual(ET.fromstring(result).find("{*}note/{*}content").get("color"), "rgb(221,238,255)")

    def test_sxsd_loses_only_hex_encoding_errors_and_keeps_unrelated_errors(self):
        import sys

        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

        schema = Path(__file__).resolve().parents[3] / "references/xml/slides_xml_schema_definition.xml"
        source = self.page(
            '<shape type="rect" topLeftX="10" topLeftY="10" width="100" height="50">'
            '<fill><fillColor color="#123456"/></fill><border color="#abc" width="1"/>'
            '<content color="#fedcba" fontSize="14"><p>text</p></content></shape>'
        )
        source = source.replace("<data>", '<style><fill><fillColor color="#f7f3e8"/></fill></style><data>')
        before = sxsd_validator.validate_sxsd(ET.fromstring(source), schema)
        self.assertEqual([issue["code"] for issue in before], ["sxsd_pattern_mismatch"] * 4)
        self.assertEqual(sxsd_validator.validate_sxsd(ET.fromstring(compose_slide(source)), schema), [])
        invalid_width = source.replace('width="100"', 'width="bad"')
        remaining = sxsd_validator.validate_sxsd(ET.fromstring(compose_slide(invalid_width)), schema)
        self.assertEqual(len(remaining), 1)
        self.assertIn("width", remaining[0]["message"])


class SlideSerializationTest(SvgTestCase):
    sml = "https://www.larkoffice.com/sml/2.0"
    svg = "http://www.w3.org/2000/svg"
    xlink = "http://www.w3.org/1999/xlink"

    def test_serialization_keeps_namespaces_comments_and_rejects_unbound_input(self):
        fragment = self.atomize_body(
            '<g><rect x="10" y="20" width="60" height="30" rx="6" fill="white" '
            'stroke="#6B7886" stroke-width="1.4" stroke-dasharray="5 4"/></g>'
        )
        page = ET.fromstring(
            f'<slide xmlns="{self.sml}"><data>'
            '<shape id="native1" type="rect" topLeftX="2" topLeftY="3" '
            'width="4" height="5"/></data></slide>'
        )
        page.find("{*}data").extend(ET.fromstring(fragment).find("{*}data"))
        before = [(e.tag, dict(e.attrib), e.text, e.tail) for e in page.iter()]
        result = serialize_slide(page)
        embedded = re.search(r"<embed\b[^>]*>(.*?)</embed>", result, re.S).group(1)
        inner = ET.fromstring(embedded)  # No SML ancestor declarations available.
        self.assertEqual(inner.tag, f"{{{self.svg}}}svg")
        self.assertTrue(all(e.tag.startswith(f"{{{self.svg}}}") for e in inner.iter()))
        rect = inner.find(".//{*}rect")
        self.assertEqual(rect.get("stroke-dasharray"), "5 4")
        self.assertEqual(rect.get("rx"), "6")
        self.assertNotRegex(result, r"<\w+:svg\b|<\w+:g\b|<\w+:rect\b")
        self.assertEqual(before, [(e.tag, dict(e.attrib), e.text, e.tail) for e in page.iter()])
        native = ET.fromstring(result).find("{*}data/{*}shape")
        self.assertEqual(native.attrib, page.find("{*}data/{*}shape").attrib)
        source = (
            f'<s:slide xmlns:s="{self.sml}" xmlns:v="{self.svg}" '
            f'xmlns:xlink="{self.xlink}" xmlns:custom="urn:custom"><s:data>'
            '<s:embed id="svg1"><v:svg viewBox="0 0 100 80">'
            '<v:defs><v:path id="part" d="M 1 2 L 3 4"/></v:defs>'
            '<v:use xlink:href="#part" custom:role="custom:part"/>'
            '<v:text xml:space="preserve"> A <v:tspan>B</v:tspan> C </v:text>'
            '<v:foreignObject><p xmlns="http://www.w3.org/1999/xhtml">html</p>'
            '<plain xmlns="">plain</plain></v:foreignObject>'
            "<v:metadata><xml:item>meta</xml:item></v:metadata>"
            "</v:svg></s:embed></s:data></s:slide>"
        )
        result = serialize_slide(source)
        inner = ET.fromstring(re.search(r"<embed\b[^>]*>(.*?)</embed>", result, re.S).group(1))
        use = inner.find(f"{{{self.svg}}}use")
        self.assertEqual(use.get(f"{{{self.xlink}}}href"), "#part")
        self.assertEqual(use.get("{urn:custom}role"), "custom:part")
        text = inner.find(f"{{{self.svg}}}text")
        self.assertEqual(text.get("{http://www.w3.org/XML/1998/namespace}space"), "preserve")
        self.assertEqual((text.text, text[0].text, text[0].tail), (" A ", "B", " C "))
        self.assertIsNotNone(inner.find(".//{http://www.w3.org/1999/xhtml}p"))
        self.assertIsNotNone(inner.find(".//plain"))
        self.assertIsNotNone(inner.find(".//{http://www.w3.org/XML/1998/namespace}item"))
        page = ET.Element("slide", {"xmlns": self.sml})
        data = ET.SubElement(page, "data")
        embed = ET.SubElement(data, "embed")
        svg = ET.SubElement(embed, "v:svg", {"xmlns:v": self.svg})
        ET.SubElement(
            svg,
            "v:use",
            {ET.QName(self.xlink, "href"): "#part", ET.QName("urn:one", "kind"): ET.QName("urn:two", "part")},
        )
        inner = ET.fromstring(re.search(r"<embed>(.*?)</embed>", serialize_slide(page), re.S).group(1))
        use = inner.find(f"{{{self.svg}}}use")
        self.assertEqual(use.get(f"{{{self.xlink}}}href"), "#part")
        self.assertRegex(use.get("{urn:one}kind"), r"ns\d+:part")
        source = f'<slide xmlns="{self.sml}"><data><!--keep--><?test value?><shape id="x"/></data></slide>'
        result = serialize_slide(source)
        self.assertIn("<!--keep--><?test value?>", result)
        with self.assertRaisesRegex(ET.ParseError, "unbound prefix"):
            serialize_slide(
                f'<slide xmlns="{self.sml}"><data><embed><svg xmlns="{self.svg}"><svg:g/></svg></embed></data></slide>'
            )
        page = ET.Element(f"{{{self.sml}}}slide")
        ET.SubElement(page, "svg:g")
        with self.assertRaisesRegex(ValueError, "Unbound XML prefix"):
            serialize_slide(page)
        for tag in ("v:v:rect", "{urn:other}v:rect", 'rect x="1"'):
            bad = ET.Element(f"{{{self.sml}}}slide", {"xmlns:v": self.svg})
            ET.SubElement(bad, tag)
            with self.subTest(tag=tag), self.assertRaisesRegex(ValueError, "Invalid XML local name"):
                serialize_slide(bad)
        with self.assertRaisesRegex(ValueError, "Expected one <slide>"):
            serialize_slide(f'<presentation xmlns="{self.sml}"/>')
        with self.assertRaises(TypeError):
            serialize_slide(None)

    def test_root_only_replacement_leaves_embed_dependent_on_slide_prefix(self):
        page = ET.fromstring(
            f'<slide xmlns="{self.sml}"><data><embed>'
            f'<svg xmlns="{self.svg}"><g><rect width="8" height="6"/></g>'
            "</svg></embed></data></slide>"
        )
        # Reproduce the delivered script's register/tostring/root-replace path
        # in an isolated registry, then model service extraction of the embed.
        with patch.dict(ET._namespace_map, {self.sml: "", self.svg: "svg"}, clear=True):
            old = (
                ET.tostring(page, encoding="unicode")
                .replace("<svg:svg", f'<svg xmlns="{self.svg}"')
                .replace("</svg:svg>", "</svg>")
            )
            ET.fromstring(old)  # Whole-page XML can still be well formed.
            old_embed = re.search(r"<embed>(.*?)</embed>", old, re.S).group(1)
            with self.assertRaisesRegex(ET.ParseError, "unbound prefix"):
                ET.fromstring(old_embed)
            fixed = serialize_slide(page)
        inner = ET.fromstring(re.search(r"<embed>(.*?)</embed>", fixed, re.S).group(1))
        self.assertEqual(inner.find(f"{{{self.svg}}}g/{{{self.svg}}}rect").get("width"), "8")

    def test_no_registry_dependency_and_no_changes_to_text_tail_or_geometry(self):
        page = ET.fromstring(
            f'<slide xmlns="{self.sml}"><data><shape id="native2" '
            'type="text" topLeftX="12.50" topLeftY="2" width="80" height="40">'
            '<content><p xml:space="preserve">A &amp; B<span>C</span> tail</p>'
            "</content></shape></data></slide>"
        )
        paragraph = page.find(".//{*}p")
        paragraph.text = " A\r\n<&>\t "
        paragraph[0].tail = " tail\r中文 "
        paragraph.set("test", 'a\t"b\nc\r')
        original = [(e.tag, dict(e.attrib), e.text, e.tail) for e in page.iter()]
        baseline = serialize_slide(page)
        with patch.dict(ET._namespace_map, {self.sml: "changed", self.svg: ""}, clear=True):
            registry = dict(ET._namespace_map)
            with patch.object(ET, "register_namespace", side_effect=AssertionError("global registry")):
                self.assertEqual(serialize_slide(page), baseline)
            self.assertEqual(ET._namespace_map, registry)
        parsed = ET.fromstring(baseline)
        self.assertEqual(original, [(e.tag, dict(e.attrib), e.text, e.tail) for e in parsed.iter()])
        self.assertEqual(original, [(e.tag, dict(e.attrib), e.text, e.tail) for e in page.iter()])


class CompositionMappingTest(SvgTestCase):
    canvas = (200, 200)

    def test_clipped_arrow_and_marker_bounds_stay_local(self):
        defs = (
            '<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" '
            'markerWidth="10" markerHeight="10" markerUnits="userSpaceOnUse" orient="auto">'
            '<path d="M 0 1 L 9 5 L 0 9" fill="none" stroke="#222222" stroke-width="1.8"/>'
            "</marker></defs>"
        )
        source = '<path d="M 20 80 L 180 80" fill="none" stroke="#222222" stroke-width="2" marker-end="url(#a)"/>'
        b = svg_bounds(source, defs, viewport=(0, 0, 1600, 1040))
        self.assertLess(b[2], 180)
        self.assertLess(b[3], 15)
        self.assertLessEqual(b[0], 20)
        self.assertGreaterEqual(b[0] + b[2], 181)
        fragment = ET.fromstring(svg_embed(source, defs, (0, 0, 1600, 1040)))
        self.assertLess(float(fragment.get("width")), 180)
        inner = fragment.find("{*}svg/{*}svg")
        self.assertEqual(inner.get("viewBox"), "0 0 1600 1040")
        self.assertIsNotNone(inner.find(".//{*}marker"))
        self.assertEqual(inner.find("{*}path").get("d"), "M 20 80 L 180 80")
        defs = (
            '<defs><marker id="a" markerWidth="10" markerHeight="6" refX="0" refY="3" '
            'markerUnits="strokeWidth" orient="auto"><rect width="10" height="6"/></marker></defs>'
        )
        source = '<line x1="50" y1="40" x2="50" y2="100" stroke="#222222" stroke-width="3" marker-end="url(#a)"/>'
        b = svg_bounds(source, defs)
        self.assertLessEqual(b[0], 41)
        self.assertGreaterEqual(b[0] + b[2], 59)
        self.assertGreaterEqual(b[1] + b[3], 130)
        self.assertLess(b[2], 25)
        defs = (
            '<defs><marker id="a" markerWidth="10" markerHeight="10" markerUnits="userSpaceOnUse" '
            'overflow="visible" orient="auto"><circle cx="30" cy="0" r="8"/></marker></defs>'
        )
        source = '<line x1="20" y1="50" x2="80" y2="50" stroke="#222222" marker-end="url(#a)"/>'
        b = svg_bounds(source, defs)
        self.assertGreaterEqual(b[0] + b[2], 118)
        self.assertLess(b[2], 110)
        self.assertEqual(svg_bounds(source, "", viewport=(0, 0, 900, 400)), (0, 0, 900, 400))
        defs = (
            '<defs><marker id="a" viewBox="10 20 10 10" markerWidth="20" markerHeight="10" '
            'refX="10" refY="20" markerUnits="userSpaceOnUse" orient="0">'
            '<rect x="10" y="20" width="10" height="10"/></marker></defs>'
        )
        source = '<g transform="translate(100 50)"><path d="M 0 0 L 20 0" stroke="black" marker-end="url(#a)"/></g>'
        b = svg_bounds(source, defs)
        self.assertLessEqual(b[0], 100)
        self.assertGreaterEqual(b[0] + b[2], 135)
        self.assertGreaterEqual(b[1] + b[3], 60)
        self.assertLess(b[2], 45)

    def test_fallback_and_mixed_fragments_keep_svg_namespace(self):
        fragment = convert_path('<path d="M 20 20 L 20 20" fill="none" stroke="#336699" stroke-width="2"/>')
        self.assertRegex(fragment, r'<svg\b[^>]*\bxmlns="http://www.w3.org/2000/svg"')
        self.assertNotRegex(fragment, r"<\w+:svg\b")
        root = ET.fromstring("<data>" + fragment + "</data>")
        self.assertEqual(root[0].tag, "embed")
        self.assertIsNotNone(root[0].find("{http://www.w3.org/2000/svg}svg"))
        source = (
            '<shape type="rect" topLeftX="0" topLeftY="0" width="10" height="10">'
            '<border color="rgb(0,0,0)" width="2"/></shape>'
            '<embed topLeftX="0" topLeftY="0" width="20" height="20">'
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">'
            '<defs><path id="p" d="M 0 0 L 10 10"/></defs>'
            '<use xmlns:xlink="http://www.w3.org/1999/xlink" xlink:href="#p"/>'
            "</svg></embed>"
        )
        result = _orient(source, ET.fromstring('<path stroke-linecap="round"/>'))
        root = ET.fromstring("<data>" + result + "</data>")
        self.assertEqual([n.tag for n in root], ["shape", "embed"])
        self.assertEqual(root.find("shape/border").get("lineCap"), "round")
        self.assertRegex(result, r'<svg\b[^>]*\bxmlns="http://www.w3.org/2000/svg"')
        use = root.find(".//{http://www.w3.org/2000/svg}use")
        self.assertEqual(use.get("{http://www.w3.org/1999/xlink}href"), "#p")
        self.assertIsNotNone(root.find(".//{http://www.w3.org/2000/svg}path"))

    def marker(self, body='<polygon points="0,0 10,5 0,10" fill="#336699"/>', attrs=""):
        return (
            '<defs><marker id="customTip" viewBox="0 0 10 10" markerWidth="10" markerHeight="10" refX="10" refY="5" '
            + attrs
            + ">"
            + body
            + "</marker></defs>"
        )

    def line(self, attr='marker-end="url(#customTip)"', coords='x1="20" y1="50" x2="100" y2="50"'):
        return "<line " + coords + ' stroke="#336699" stroke-width="2" ' + attr + "/>"

    def test_group_transforms_order_nesting_and_path_geometry(self):
        data = self.convert(
            '<g transform="translate(10 20) scale(2)" fill="#112233" stroke="#445566" stroke-width="2">'
            '<rect x="3" y="4" width="10" height="20" rx="3"/>'
            '<circle cx="20" cy="20" r="5" fill="#aabbcc"/></g>'
        )
        self.assertEqual(
            [data[0].get(k) for k in ("topLeftX", "topLeftY", "width", "height", "presetHandlers")],
            ["16.0", "28.0", "20.0", "40.0", "6"],
        )
        self.assertEqual(data[0].find("{*}border").get("width"), "4")
        self.assertEqual(data[1].find("{*}fill/{*}fillColor").get("color"), "rgb(170,187,204)")
        reverse = self.convert(
            '<g transform="scale(2) translate(10 20)"><rect x="3" y="4" width="10" height="20"/></g>'
        )[0]
        self.assertEqual((reverse.get("topLeftX"), reverse.get("topLeftY")), ("26.0", "48.0"))
        grouped = self.convert(
            '<g transform="translate(10 20)" fill="#112233"><g transform="scale(2)">'
            '<line x1="1" y1="2" x2="11" y2="12" stroke="#445566"/>'
            '<circle cx="20" cy="30" r="5"/></g></g>'
        )
        flat = self.convert(
            '<line x1="12" y1="24" x2="32" y2="44" stroke="#445566" stroke-width="2"/>'
            '<circle cx="50" cy="80" r="10" fill="#112233"/>'
        )
        self.assertEqual(ET.tostring(grouped), ET.tostring(flat))
        grouped = self.convert(
            '<g transform="scale(2 3)"><g transform="scale(.5 .3333333333333333)">'
            '<circle cx="40" cy="50" r="10"/></g></g>'
        )
        flat = self.convert('<circle cx="40" cy="50" r="10"/>')
        self.assertEqual(ET.tostring(grouped), ET.tostring(flat))
        grouped = self.convert(
            '<g transform="translate(10 20) scale(2)"><path d="m 1 2 q 3 4 5 6 a 7 8 20 0 1 9 10 z" '
            'fill="none" stroke="#112233" stroke-width="2"/></g>'
        )
        flat = self.convert(
            '<path d="M 12 24 Q 18 32 22 36 A 14 16 20 0 1 40 56 Z" fill="none" stroke="#112233" stroke-width="4"/>'
        )
        self.assertEqual(ET.tostring(grouped), ET.tostring(flat))

    def test_group_opacity_nonuniform_scale_and_affine_distribution(self):
        data = self.convert(
            '<g transform="translate(10 20) scale(2)" fill="#112233"><g opacity="0.5">'
            '<rect x="0" y="0" width="30" height="30"/>'
            '<rect x="10" y="10" width="30" height="30"/></g></g>'
        )
        self.assertEqual(len(data), 1)
        self.assertTrue(data[0].tag.endswith("}embed"))
        # The opacity group stays one compositing unit; the parent transform is pushed onto its leaves.
        group = next(g for g in data[0].findall(".//{*}g") if g.get("opacity"))
        self.assertEqual(group.get("opacity"), "0.5")
        self.assertEqual({r.get("transform") for r in group.findall("{*}rect")}, {"matrix(2 0 0 2 10 20)"})
        self.assertTrue(all(e.get("opacity") is None for e in data[0].findall(".//{*}rect")))
        data = self.convert(
            '<g transform="translate(10 20) scale(2 3)" opacity=".5">'
            '<rect width="30" height="30" fill="red"/>'
            '<rect x="10" y="10" width="30" height="30" fill="blue"/></g>'
        )
        self.assertEqual(len(data), 1)
        self.assertTrue(data[0].tag.endswith("}embed"))
        groups = data[0].findall(".//{*}g")
        self.assertEqual(sum(g.get("opacity") == "0.5" for g in groups), 1)
        self.assertEqual(len(data[0].findall(".//{*}rect")), 2)
        data = self.convert(
            '<g transform="scale(2 3)"><circle id="first" cx="20" cy="20" r="10"/>'
            '<circle id="second" cx="80" cy="20" r="10"/></g>'
        )
        self.assertEqual(len(data), 2)
        for item, source_id, center_x in zip(data, ("first", "second"), (40, 160)):
            self.assertTrue(item.tag.endswith("}embed"))
            circles = item.findall(".//{*}circle")
            self.assertEqual([c.get("id") for c in circles], [source_id])
            transform = circles[0].get("transform")  # group transforms are pushed onto leaves
            self.assertEqual(parse_transform(transform).point(20, 20), (40, 60))
            x, y, w, h = (float(item.get(k)) for k in ("topLeftX", "topLeftY", "width", "height"))
            self.assertAlmostEqual(x + w / 2, center_x, delta=0.1)
            self.assertAlmostEqual(y + h / 2, 60, delta=0.1)
            self.assertLess(w, 45)
            self.assertLess(h, 65)
        body = (
            '<defs><linearGradient id="paint" gradientUnits="userSpaceOnUse" x2="100">'
            '<stop offset="0" stop-color="red"/><stop offset="1" stop-color="blue"/></linearGradient></defs>'
            '<g id="parent" transform="matrix(1 .3 .4 1 10 20)" fill="url(#paint)">'
            '<path id="front" d="M0 0Q30 50 60 0Z"/>'
            '<g transform="translate(80 0)"><rect id="back" width="20" height="30"/></g></g>'
        )
        data = self.convert(body)
        self.assertEqual(len(data), 2)
        for item, identity in zip(data, ("front", "back")):
            self.assertTrue(item.tag.endswith("}embed"))
            self.assertIsNotNone(item.find(".//{*}linearGradient"))
            self.assertIsNotNone(item.find(f'.//*[@id="{identity}"]'))
            self.assertIn("url(#paint)", ET.tostring(item, encoding="unicode"))
        data = self.convert(
            '<defs><filter id="blur"><feGaussianBlur stdDeviation="4"/></filter></defs>'
            '<g filter="url(#blur)"><circle cx="50" cy="50" r="10"/></g>'
        )
        self.assertTrue(data[0].tag.endswith("}embed"))
        self.assertIsNotNone(data[0].find(".//{*}filter"))
        data = self.convert(
            '<defs><clipPath id="clip"><circle cx="30" cy="30" r="10"/></clipPath></defs>'
            '<g fill="#112233"><rect x="10" y="10" width="40" height="40" clip-path="url(#clip)"/></g>'
        )
        self.assertTrue(data[0].tag.endswith("}embed"))
        self.assertIsNotNone(data[0].find(".//{*}clipPath"))

    def test_inherited_presentation_alpha_current_colour_and_svg_fallbacks(self):
        data = self.convert(
            '<g style="fill:#112233; font-size:20px; font-weight:bold">'
            '<text x="20" y="30" style="fill:#445566">标题</text>'
            '<g display="none"><rect x="0" y="0" width="100" height="100"/></g></g>'
        )
        self.assertEqual(len(data), 1)
        content = data[0].find("{*}content")
        self.assertEqual(content.get("fontSize"), "20")
        self.assertEqual(content.get("bold"), "true")
        self.assertEqual(content.get("color"), "rgb(68,85,102)")
        data = self.convert(
            '<g fill="#112233" fill-opacity="0.5" stroke="#445566" stroke-opacity="0.3">'
            '<rect x="10" y="10" width="20" height="20"/>'
            '<ellipse cx="50" cy="50" rx="20" ry="10"/>'
            '<polygon points="20,20 40,20 30,40"/></g>'
        )
        for shape in data[:2]:
            self.assertEqual(shape.find("{*}fill/{*}fillColor").get("color"), "rgba(17,34,51,0.50)")
            self.assertEqual(shape.find("{*}border").get("color"), "rgba(68,85,102,0.30)")
        self.assertEqual(data[2].get("type"), "custom")
        self.assertEqual(data[2].find("{*}fill/{*}fillColor").get("color"), "rgba(17,34,51,0.50)")
        self.assertEqual(data[2].find("{*}border").get("color"), "rgba(68,85,102,0.30)")
        for text in (
            '<text x="20 40" y="50">AB</text>',
            '<text y="40 60"><tspan x="20">AB</tspan></text>',
            '<text><tspan x="20" y="40" stroke="#112233">AB</tspan></text>',
        ):
            self.assertTrue(self.convert(text)[0].tag.endswith("}embed"))
        data = self.convert(
            '<g fill="currentColor" color="#112233"><rect x="10" y="10" width="20" height="20" color="#445566"/></g>'
        )
        self.assertEqual(data[0].find("{*}fill/{*}fillColor").get("color"), "rgb(68,85,102)")

    def test_marker_geometry_reference_names_start_reverse_and_tangents(self):
        data = self.convert(self.marker(attrs='orient="auto" markerUnits="userSpaceOnUse"') + self.line())
        self.assertEqual(len(data), 2)
        self.assertIsNone(data[0].find("{*}endArrow"))
        self.assertEqual(
            [data[1].get(k) for k in ("topLeftX", "topLeftY", "width", "height")], ["90", "45", "10", "10"]
        )
        scaled = self.convert(self.marker(attrs='orient="auto"') + self.line())
        self.assertEqual(
            [scaled[1].get(k) for k in ("topLeftX", "topLeftY", "width", "height")], ["80", "40", "20", "20"]
        )
        marker = '<defs><marker id="stop1" viewBox="0 0 10 10" markerWidth="10" markerHeight="10" refX="7" refY="5" orient="auto" markerUnits="userSpaceOnUse">'
        marker += '<line x1="7" y1="0" x2="7" y2="10" stroke="#336699" stroke-width="2"/></marker></defs>'
        data = self.convert(marker + self.line('marker-end="url(#stop1)"'))
        self.assertEqual(len(data), 2)
        self.assertTrue(data[1].tag.endswith("}line"))
        self.assertEqual([float(data[1].get(k)) for k in ("startX", "startY", "endX", "endY")], [100, 45, 100, 55])
        normal = self.convert(
            self.marker(attrs='orient="auto" markerUnits="userSpaceOnUse"')
            + self.line('marker-start="url(#customTip)"')
        )
        reverse = self.convert(
            self.marker(attrs='orient="auto-start-reverse" markerUnits="userSpaceOnUse"')
            + self.line('marker-start="url(#customTip)"')
        )
        self.assertEqual(normal[1].get("topLeftX"), "10")
        self.assertEqual(reverse[1].get("topLeftX"), "20")
        vertical = self.convert(
            self.marker(attrs='orient="auto" markerUnits="userSpaceOnUse"')
            + self.line(coords='x1="20" y1="20" x2="20" y2="80"')
        )
        self.assertEqual((vertical[1].get("topLeftX"), vertical[1].get("topLeftY")), ("15", "70"))
        data = self.convert(
            self.marker(attrs='orient="auto" markerUnits="userSpaceOnUse"')
            + '<path d="M 20 20 C 20 80 100 30 100 80" fill="none" stroke="#336699" marker-end="url(#customTip)"/>'
        )
        self.assertEqual((data[1].get("topLeftX"), data[1].get("topLeftY")), ("95", "70"))
        marker = self.marker(
            '<polygon points="0,0 10,5 0,10" fill="context-stroke"/>',
            attrs='orient="auto" markerUnits="userSpaceOnUse"',
        )
        data = self.convert(marker + '<g transform="translate(10 20) scale(2)">' + self.line() + "</g>")
        self.assertEqual(data[1].find("{*}fill/{*}fillColor").get("color"), "rgb(51,102,153)")
        self.assertEqual((data[1].get("topLeftX"), data[1].get("topLeftY"), data[1].get("width")), ("190", "110", "20"))
        clipped = self.marker('<polygon points="-2,0 10,5 0,10" fill="#112233"/>', attrs='orient="auto"')
        self.assertTrue(self.convert(clipped + self.line())[0].tag.endswith("}embed"))
        translucent = self.convert(
            self.marker(attrs='orient="auto"') + self.line('marker-end="url(#customTip)" opacity="0.5"')
        )
        self.assertEqual(len(translucent), 1)
        self.assertTrue(translucent[0].tag.endswith("}embed"))
        # The marker is expanded into a plain tip shape sharing the host's opacity (embeds reject <marker>).
        self.assertIsNone(translucent[0].find(".//{*}marker"))
        group = next(g for g in translucent[0].iter() if g.tag.endswith("}g") and g.get("opacity") == "0.5")
        self.assertEqual(len([c for c in group if c.tag.split("}")[-1] in ("path", "polygon", "line")]), 2)
        data = self.convert(
            self.marker(attrs='orient="auto" markerUnits="userSpaceOnUse"')
            + '<g marker-end="url(#customTip)">'
            + self.line("")
            + self.line('marker-end="none"')
            + "</g>"
        )
        self.assertEqual(len(data), 3)
        self.assertIsNone(data[-1].find("{*}endArrow"))

    def test_letter_spacing_explicit_em_and_scaled(self):
        set_mapping(200, 200, 0, 0, 100, 100)
        plain = self.convert('<text x="100" y="50" font-size="20" text-anchor="middle">ABC</text>')[0]
        spaced = self.convert('<text x="100" y="50" font-size="20" text-anchor="middle" letter-spacing="3">ABC</text>')[
            0
        ]
        self.assertEqual(spaced.find("{*}content").get("letterSpacing"), "1.5")
        self.assertAlmostEqual(float(spaced.get("width")) - float(plain.get("width")), 3, places=1)
        self.assertAlmostEqual(float(spaced.get("topLeftX")) - float(plain.get("topLeftX")), -1.5, places=1)
        set_mapping(200, 200, 0, 0, 200, 200)  # identity mapping for the inherited em-spacing case
        shape = self.convert(
            '<g transform="scale(2)" font-size="20" letter-spacing="0.2em"><text x="20" y="40">AB</text></g>'
        )[0]
        self.assertEqual(shape.find("{*}content").get("fontSize"), "40")
        self.assertEqual(shape.find("{*}content").get("letterSpacing"), "8")

    def test_tspan_lines_dy_and_transform_keep_position(self):
        data = self.convert(
            '<text font-size="20" fill="#112233" text-anchor="middle">'
            '<tspan x="50" y="40">第一行</tspan>'
            '<tspan x="70" y="90" fill="#445566">第二行</tspan></text>'
        )
        self.assertEqual([e.find(".//{*}p").text for e in data], ["第一行", "第二行"])
        for e, cx, cy in zip(data, [50, 70], [40, 90]):
            self.assertAlmostEqual(float(e.get("topLeftX")) + float(e.get("width")) / 2, cx, delta=0.1)
            self.assertAlmostEqual(float(e.get("topLeftY")) + float(e.get("height")) / 2 + 7, cy, delta=0.1)
        self.assertEqual(data[1].find("{*}content").get("color"), "rgb(68,85,102)")
        data = self.convert(
            '<text x="20" y="40" font-size="20"><tspan>One</tspan><tspan x="20" dy="30">Two</tspan></text>'
        )
        self.assertEqual(len(data), 2)
        self.assertAlmostEqual(float(data[1].get("topLeftY")) - float(data[0].get("topLeftY")), 30)
        transformed = self.convert(
            '<text transform="translate(10 20) scale(2)" font-size="20"><tspan x="30" y="40">AB</tspan></text>'
        )
        flat = self.convert('<text x="70" y="100" font-size="40">AB</text>')
        self.assertEqual(ET.tostring(transformed), ET.tostring(flat))


class AdvancedMappingTest(SvgTestCase):
    canvas = (400, 300)

    def test_filters_radial_gradients_resource_closure_and_viewports(self):
        shapes = [
            '<rect x="30" y="40" width="40" height="30"',
            '<circle cx="50" cy="50" r="15"',
            '<ellipse cx="50" cy="50" rx="20" ry="10"',
            '<line x1="30" y1="40" x2="70" y2="60"',
            '<path d="M 30 40 Q 60 10 70 60 Z"',
            '<polygon points="30,40 70,40 50,60"',
            '<polyline points="30,40 70,40 50,60"',
        ]
        for shape in shapes:
            with self.subTest(shape=shape):
                data = self.convert(
                    '<defs><filter id="f"><feGaussianBlur stdDeviation="3"/><feComponentTransfer><feFuncA type="linear" slope="0.6"/></feComponentTransfer></filter></defs>'
                    + shape
                    + ' fill="#336699" filter="url(#f)"/>'
                )
                self.assertTrue(data[0].tag.endswith("}embed"))
                self.assertIsNotNone(data[0].find(".//{*}feComponentTransfer"))
        for shape in ['<rect x="20" y="20" width="80" height="50"', '<path d="M 20 20 L 100 20 L 70 70 Z"']:
            data = self.convert(
                '<defs><radialGradient id="r"><stop stop-color="#ffffff"/><stop offset="1" stop-color="#336699"/></radialGradient></defs>'
                + shape
                + ' fill="url(#r)"/>'
            )
            self.assertTrue(data[0].tag.endswith("}embed"))
            self.assertIsNotNone(data[0].find(".//{*}radialGradient"))
        defs = '<defs><linearGradient id="base"><stop stop-color="#336699"/></linearGradient><linearGradient id="derived" href="#base"/><path id="motif" d="M 0 0 L 5 5" fill="url(#derived)"/><pattern id="p"><use href="#motif"/></pattern><filter id="unused"/></defs>'
        result = ET.fromstring(resource_closure('<rect fill="url(#p)"/>', defs))
        self.assertEqual({n.get("id") for n in result}, {"p", "motif", "derived", "base"})
        cyclic = '<defs><linearGradient id="a" href="#b"/><linearGradient id="b" href="#a"/></defs>'
        self.assertEqual(len(ET.fromstring(resource_closure('<rect fill="url(#a)"/>', cyclic))), 2)  # terminates
        data = self.convert(
            '<defs><linearGradient id="g" gradientUnits="userSpaceOnUse" x2="100%"><stop stop-color="#ffffff"/><stop offset="1" stop-color="#336699"/></linearGradient></defs><g opacity="0.5"><rect x="120" y="80" width="40" height="30" fill="url(#g)"/></g>'
        )
        self.assertAlmostEqual(float(data[0].get("width")), 42)
        viewports = data[0].findall(".//{*}svg")
        self.assertEqual(viewports[1].get("viewBox"), "0 0 400 300")
        e = self.convert(
            '<defs><filter id="f" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="12"/></filter></defs><rect x="100" y="100" width="40" height="20" fill="#336699" filter="url(#f)"/>'
        )[0]
        self.assertLessEqual(float(e.get("topLeftX")), 60)
        self.assertGreaterEqual(float(e.get("width")), 120)
        self.assertLess(float(e.get("width")), 150)
        e = self.convert(
            '<defs><filter id="base" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="8"/></filter><filter id="f" href="#base"/></defs><rect x="100" y="100" width="40" height="20" fill="#112233" filter="url(#f)"/>'
        )[0]
        self.assertGreaterEqual(float(e.get("width")), 120)
        self.assertEqual({f.get("id") for f in e.findall(".//{*}filter")}, {"base", "f"})
        e = self.convert(
            '<defs><g id="unit"><defs><radialGradient id="inside"><stop stop-color="#ffffff"/><stop offset="1" stop-color="#336699"/></radialGradient></defs><circle cx="30" cy="30" r="20" fill="url(#inside)"/></g></defs><g opacity="0.5"><use href="#unit"/><use href="#unit" x="70"/></g>'
        )[0]
        ids = [n.get("id") for n in e.iter() if n.get("id")]
        self.assertEqual(len(ids), len(set(ids)))
        circles = e.findall(".//{*}circle")
        self.assertEqual(len(circles), 2)
        self.assertNotEqual(circles[0].get("fill"), circles[1].get("fill"))

    def test_rotated_shapes_text_and_markers_stay_native(self):
        e = self.convert(
            '<rect x="30" y="40" width="80" height="30" rx="8" fill="#336699" transform="rotate(35 70 55)"/>'
        )[0]
        self.assertEqual(e.get("type"), "rect")
        self.assertEqual(e.get("rotation"), "35")
        self.assertEqual(e.get("presetHandlers"), "8")
        self.assertEqual((float(e.get("topLeftX")), float(e.get("topLeftY"))), (30, 40))
        e = self.convert(
            '<text x="100" y="100" font-family="Arial" font-size="20" transform="rotate(90 100 100)" fill="#112233">ABC</text>'
        )[0]
        x, y, w, h = [float(e.get(k)) for k in ("topLeftX", "topLeftY", "width", "height")]
        self.assertEqual(e.get("rotation"), "90")
        self.assertAlmostEqual(x + w / 2, 107, delta=0.1)
        self.assertAlmostEqual(y + h / 2, 100 + w / 2, delta=0.1)
        e = self.convert('<text x="20" y="40" font-size="20" transform="translate(200 0) scale(-1 1)">Mirror</text>')[0]
        self.assertEqual(e.get("rotation"), "180")
        self.assertEqual(e.get("flipY"), "true")
        data = self.convert(
            '<defs><marker id="m" viewBox="0 0 10 10" markerWidth="10" markerHeight="10" refX="5" refY="5" markerUnits="userSpaceOnUse" orient="auto"><rect x="1" y="3" width="8" height="4" rx="1" fill="#336699"/></marker></defs><g transform="rotate(90 100 100)"><line x1="30" y1="100" x2="100" y2="100" stroke="#336699" marker-end="url(#m)"/></g>'
        )
        self.assertEqual(len(data), 2)
        self.assertEqual(data[1].get("rotation"), "90")
        self.assertAlmostEqual(float(data[1].get("topLeftX")) + float(data[1].get("width")) / 2, 100)
        node = ET.fromstring(
            '<rect x="10" y="20" width="30" height="10" fill="none" stroke="#336699" stroke-dasharray="4 2" stroke-dashoffset="1"/>'
        )
        transformed = transform_element(node, parse_transform("rotate(90) scale(2)"))
        self.assertEqual(transformed.tag, "path")
        self.assertEqual(transformed.get("stroke-dasharray"), "8 4")
        self.assertEqual(transformed.get("stroke-dashoffset"), "2")
        self.assertEqual(path_segments(transformed.get("d"))[0][1], [-40, 20])

    def test_path_transforms_keep_coordinates_under_reflection_and_random_similarity(self):
        node = ET.fromstring('<path d="M 10 20 A 30 10 25 0 1 80 50 L 90 60"/>')
        result = transform_element(node, parse_transform("translate(200 0) scale(-1 1)"))
        segments = path_segments(result.get("d"))
        self.assertEqual(segments[0][1], [190, 20])
        self.assertEqual(segments[1][1][4], 0)
        self.assertEqual(segments[-1][1], [110, 60])
        self.assertAlmostEqual(segments[1][1][2], 155)
        rng = random.Random(72)
        for _ in range(40):
            x, y = rng.uniform(-50, 50), rng.uniform(-50, 50)
            scale = rng.uniform(0.2, 3)
            angle = rng.uniform(-180, 180)
            reflection = rng.choice([-1, 1])
            matrix = parse_transform(f"translate(20 30) rotate({angle}) scale({scale} {scale * reflection})")
            node = ET.fromstring(f'<path d="M {x} {y} L 10 20" stroke-width="2"/>')
            result = transform_element(node, matrix)
            point = path_segments(result.get("d"))[0][1]
            for actual, expected in zip(point, matrix.point(x, y)):
                self.assertAlmostEqual(actual, expected, places=7)
            self.assertAlmostEqual(float(result.get("stroke-width")), 2 * scale, places=7)

    def test_use_instances_symbols_and_cycles(self):
        data = self.convert(
            '<defs><g id="unit"><rect width="20" height="10"/></g></defs><use href="#unit" x="20" y="30" fill="#112233"/><use xlink:href="#unit" x="80" y="90" fill="#445566"/>'
        )
        self.assertEqual(len(data), 2)
        self.assertEqual([e.get("topLeftX") for e in data], ["20.0", "80.0"])
        self.assertEqual(
            [e.find("{*}fill/{*}fillColor").get("color") for e in data], ["rgb(17,34,51)", "rgb(68,85,102)"]
        )

        data = self.convert(
            '<defs><rect id="unit" width="20" height="10" fill="#112233"/></defs><use href="#unit" fill="#445566"/>'
        )
        self.assertEqual(data[0].find("{*}fill/{*}fillColor").get("color"), "rgb(17,34,51)")
        data = self.convert(
            '<defs><symbol id="s" viewBox="10 20 100 100"><circle cx="60" cy="70" r="20" fill="#336699"/></symbol></defs><use href="#s" x="20" y="30" width="200" height="100"/>'
        )
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0].get("type"), "ellipse")
        self.assertAlmostEqual(float(data[0].get("topLeftX")), 100)
        self.assertAlmostEqual(float(data[0].get("topLeftY")), 60)

        data = self.convert(
            '<defs><symbol id="s" viewBox="0 0 100 100" preserveAspectRatio="xMidYMid slice"><rect width="100" height="100" fill="#336699"/></symbol></defs><use href="#s" width="200" height="50"/>'
        )
        self.assertEqual(data[0].get("type"), "custom")
        self.assertAlmostEqual(float(data[0].get("width")), 200)
        self.assertAlmostEqual(float(data[0].get("height")), 50)
        for body in [
            '<defs><g id="a"><use href="#a"/></g></defs><use href="#a"/>',
            '<use href="#missing"/>',
            '<use href="https://example.com/a.svg#x"/>',
        ]:
            with self.subTest(body=body), self.assertRaises(ValueError):
                self.convert(body)

    def test_compound_nonzero_and_evenodd_paths(self):
        data = self.convert(
            '<path d="M 10 10 L 50 10 L 50 50 L 10 50 Z M 20 20 L 20 40 L 40 40 L 40 20 Z" fill="#336699"/>'
        )
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0].get("type"), "custom")
        self.assertEqual(data[0].get("path").count("M "), 2)
        self.assertEqual(data[0].get("path").count("Z"), 2)
        data = self.convert(
            '<path d="M 10 10 H 80 V 80 H 10 Z M 20 20 H 70 V 70 H 20 Z" fill="#336699" fill-rule="evenodd"/>'
        )
        self.assertTrue(data[0].tag.endswith("}embed"))
        self.assertEqual(data[0].find(".//{*}path").get("fill-rule"), "evenodd")

    def test_dash_phase_odd_pattern_corner_continuity_and_zero_length_dots(self):
        node = ET.fromstring('<line x1="0" y1="0" x2="30" y2="0" stroke-dasharray="5 3" stroke-dashoffset="2"/>')
        self.assertEqual(dash_path(node), "M 0 0 L 3 0 M 6 0 L 11 0 M 14 0 L 19 0 M 22 0 L 27 0")
        node.set("stroke-dasharray", "3")
        node.set("stroke-dashoffset", "0")
        self.assertTrue(dash_path(node).startswith("M 0 0 L 3 0 M 6 0 L 9 0"))
        node = ET.fromstring('<polyline points="0,0 5,0 5,10" stroke-dasharray="10 5"/>')
        self.assertEqual(dash_path(node), "M 0 0 L 5 0 L 5 5")
        node = ET.fromstring('<line x1="0" y1="0" x2="20" y2="0" stroke-dasharray="0 5" stroke-dashoffset="2"/>')
        self.assertTrue(dash_path(node).startswith("M 3 0 L 3 0"))

    def test_native_caps_joins_round_dots_and_curved_dash(self):
        data = self.convert(
            '<path d="M 20 80 Q 80 10 150 80" fill="none" stroke="#336699" stroke-dasharray="7 3 1 3" stroke-dashoffset="2"/>'
        )
        self.assertTrue(data[0].tag.endswith("}embed"))
        self.assertEqual(data[0].find(".//{*}path").get("stroke-dashoffset"), "2")
        data = self.convert(
            '<polygon points="20,80 50,20 80,80" fill="none" stroke="#336699" stroke-linecap="square" stroke-linejoin="miter" stroke-miterlimit="3"/>'
        )
        border = data[0].find("{*}border")
        self.assertEqual(
            (border.get("lineCap"), border.get("lineJoin"), border.get("miterLimit")), ("square", "miter", "3")
        )
        data = self.convert(
            '<line x1="20" y1="50" x2="100" y2="50" stroke="#336699" stroke-width="2" stroke-dasharray="0 8" stroke-linecap="round"/>'
        )
        self.assertGreaterEqual(len(data), 10)
        self.assertTrue(all(e.get("type") == "ellipse" for e in data))
        self.assertTrue(all(e.find("{*}fill/{*}fillColor").get("color") == "rgb(51,102,153)" for e in data))

    def test_font_metrics_real_widths_and_missing_backend_fallback(self):
        narrow = measure_text("iiiiii", "Arial", 20)
        wide = measure_text("WWWWWW", "Arial", 20)
        if narrow is None or wide is None:
            self.skipTest("Optional Pillow/fontTools/fontconfig backend unavailable")
        self.assertGreater(wide.advance, narrow.advance * 2)
        a = self.convert('<text x="20" y="30" font-family="Arial" font-size="20">iiiiii</text>')[0]
        b = self.convert('<text x="20" y="30" font-family="Arial" font-size="20">WWWWWW</text>')[0]
        # Real glyph widths still drive the box; the lint-compatible floor only widens narrow runs.
        self.assertGreater(float(b.get("width")), float(a.get("width")))
        self.assertGreaterEqual(float(b.get("width")), wide.advance)
        self.assertGreaterEqual(float(a.get("width")), narrow.advance)
        with patch.object(_font_metrics, "measure_text", return_value=None):
            data = self.convert('<text x="20" y="30" font-family="Arial" font-size="20">Unavailable font</text>')
        self.assertEqual(data[0].get("type"), "text")

    def test_inline_rich_text_preserves_runs_spaces_and_scales_once(self):
        data = self.convert(
            '<text x="20" y="40" font-family="Arial" font-size="20" fill="#112233">Keep <tspan fill="#336699" font-weight="bold">rich</tspan> text</text>'
        )
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0].get("type"), "text")
        runs = data[0].findall(".//{*}span")
        self.assertEqual("".join(e.text for e in runs), "Keep rich text")
        self.assertEqual(runs[1].get("bold"), "true")
        self.assertEqual(runs[1].get("color"), "rgb(51,102,153)")

        with self.subTest(layout="tspan-only root"):
            data = self.convert(
                '<text x="20" y="40" font-size="20"><tspan>Hello</tspan><tspan fill="#445566">world</tspan></text>'
            )
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0].get("type"), "text")
            spans = data[0].findall(".//{*}span")
            self.assertEqual([span.text for span in spans], ["Hello", "world"])
            self.assertEqual(spans[1].get("color"), "rgb(68,85,102)")
        data = self.convert(
            '<g transform="scale(2)"><text x="20" y="40" font-size="20">A<tspan font-size="12">B</tspan></text></g>'
        )
        self.assertEqual([e.get("fontSize") for e in data[0].findall(".//{*}span")], ["40", "24"])

    def test_alpha_paint_polyline_and_inline_style_mapping(self):
        e = self.convert(
            '<path d="M 20 20 H 80 V 80 H 20 Z" fill="#112233" fill-opacity="0.5" stroke="#445566" stroke-opacity="0.3" opacity="0.125"/>'
        )[0]
        self.assertEqual(e.get("alpha"), "0.125")
        self.assertEqual(e.find("{*}fill/{*}fillColor").get("color"), "rgba(17,34,51,0.50)")
        self.assertEqual(e.find("{*}border").get("color"), "rgba(68,85,102,0.30)")
        e = self.convert('<polyline points="20,20 80,20 80,80" fill="#112233" stroke="#445566"/>')[0]
        self.assertEqual(e.get("type"), "custom")
        self.assertNotIn("Z", e.get("path"))
        self.assertEqual(e.find("{*}fill/{*}fillColor").get("color"), "rgb(17,34,51)")
        e = self.convert(
            '<g style="opacity:0.5;fill:#112233"><rect x="20" y="20" width="40" height="40" style="stroke:#445566"/></g>'
        )[0]
        self.assertTrue(e.tag.endswith("}embed"))
        self.assertTrue(all("style" not in n.attrib for n in e.iter()))
        self.assertEqual(e.find(".//{*}rect").get("stroke"), "#445566")

    def test_arc_cubics_are_accurate_and_stable(self):
        segments = arc_to_cubics(1000, 0, 1000, 1000, 0, 0, 1, 0, 1000)
        self.assertEqual(len(segments), 2)
        p0 = (1000, 0)
        for op, v in segments:
            self.assertEqual(op, "C")
            for step in range(101):
                t = step / 100
                u = 1 - t
                x = u**3 * p0[0] + 3 * u * u * t * v[0] + 3 * u * t * t * v[2] + t**3 * v[4]
                y = u**3 * p0[1] + 3 * u * u * t * v[1] + 3 * u * t * t * v[3] + t**3 * v[5]
                self.assertLess(abs(math.hypot(x, y) - 1000), 0.0044)
            p0 = tuple(v[-2:])
        self.assertEqual(p0, (0, 1000))
        self.assertAlmostEqual(segments[0][1][0], 1000, places=8)
        self.assertAlmostEqual(segments[-1][1][3], 1000, places=8)
        data = self.convert('<path d="M 100 50 A 50 30 25 1 1 100 150 A 50 30 25 1 1 100 50 Z" fill="#336699"/>')
        self.assertEqual(data[0].get("type"), "custom")
        self.assertNotIn("A ", data[0].get("path"))
        self.assertIn("C ", data[0].get("path"))


class ClipGradientMarkerTest(SvgTestCase):
    canvas = (400, 300)

    def gradient(self, attrs=""):
        return f'<defs><linearGradient id="g" {attrs}><stop offset="0" stop-color="#000000"/><stop offset="1" stop-color="#FFFFFF"/></linearGradient></defs>'

    def color(self, e):
        return e.find("{*}fill/{*}fillColor").get("color")

    def sample(self, e, x, y):
        css = self.color(e)
        angle = float(re.search(r"gradient\(([^d]+)deg", css)[1])
        a = math.radians(angle)
        ux, uy = math.sin(a), -math.cos(a)
        bx, by, w, h = [float(e.get(k)) for k in ("topLeftX", "topLeftY", "width", "height")]
        length = abs(w * ux) + abs(h * uy)
        t = 0.5 + ((x - bx - w / 2) * ux + (y - by - h / 2) * uy) / length
        stops = [
            (float(pos) / 100, tuple(map(float, rgba.split(","))))
            for rgba, pos in re.findall(r"rgba\(([^)]+)\) ([-+.e\d]+)%", css)
        ]
        if t <= stops[0][0]:
            return stops[0][1]
        for (p, c), (q, d) in zip(stops, stops[1:]):
            if p <= t < q:
                f = (t - p) / (q - p)
                return tuple(c[i] * (1 - f) + d[i] * f for i in range(4))
        return stops[-1][1]

    def test_object_and_user_space_gradients_preserve_colour_fields(self):
        e = self.convert(
            self.gradient('x2="1" y2="1"') + '<rect x="40" y="30" width="200" height="100" fill="url(#g)"/>'
        )[0]
        self.assertEqual(e.get("type"), "rect")
        for x, y in [(40, 30), (140, 30), (140, 80), (240, 130), (80, 110)]:
            expected = ((x - 40) / 200 + (y - 30) / 100) / 2 * 255
            self.assertAlmostEqual(self.sample(e, x, y)[0], expected, delta=2)
        data = self.convert(
            self.gradient('gradientUnits="userSpaceOnUse" x1="0" x2="400"')
            + '<rect x="100" y="50" width="100" height="80" fill="url(#g)"/><rect x="200" y="50" width="100" height="80" fill="url(#g)"/>'
        )
        self.assertAlmostEqual(self.sample(data[0], 200, 90)[0], 127.5, delta=0.5)
        self.assertAlmostEqual(self.sample(data[1], 200, 90)[0], 127.5, delta=0.5)
        self.assertAlmostEqual(self.sample(data[1], 250, 90)[0], 159.375, delta=0.5)
        e = self.convert(self.gradient('x1="0.2" x2="0.8"') + '<rect width="200" height="100" fill="url(#g)"/>')[0]
        for x, expected in [(0, 0), (40, 0), (100, 127.5), (160, 255), (200, 255)]:
            self.assertAlmostEqual(self.sample(e, x, 50)[0], expected)
        node = ET.fromstring('<path d="M 0 0 C 0 100 200 100 200 0 Z"/>')
        self.assertEqual(paint_bounds(node), (0, 0, 200, 75))
        for stroke, expected in [
            ('stroke="none" stroke-width="2"', (0, 0, 200, 75)),
            ('stroke="#112233" stroke-width="2"', (-2, -2, 204, 79)),
        ]:
            with self.subTest(stroke=stroke):
                e = self.convert(
                    self.gradient('x2="0" y2="1"')
                    + f'<path d="M 0 0 C 0 100 200 100 200 0 Z" fill="url(#g)" {stroke}/>'
                )[0]
                self.assertEqual(tuple(float(e.get(k)) for k in ("topLeftX", "topLeftY", "width", "height")), expected)
                self.assertAlmostEqual(self.sample(e, 100, 37.5)[0], 127.5, delta=2)
                self.assertAlmostEqual(self.sample(e, 100, 75)[0], 255, delta=2)
        e = self.convert(
            self.gradient('gradientUnits="userSpaceOnUse" x1="0" x2="400"')
            + '<path d="M40 100 C40 0 240 0 240 100 Z" fill="url(#g)" stroke="none" stroke-width="12"/>'
        )[0]
        self.assertEqual(tuple(float(e.get(k)) for k in ("topLeftX", "topLeftY", "width", "height")), (40, 25, 200, 75))
        for x, y in [(40, 100), (100, 70), (140, 25), (180, 70), (240, 100)]:
            self.assertAlmostEqual(self.sample(e, x, y)[0], x / 400 * 255, delta=2)
        e = self.convert(
            self.gradient('y2="1"')
            + '<polygon points="20,20 200,20 200,100" fill="url(#g)" fill-opacity="0.5" opacity="0.4"/>'
        )[0]
        self.assertEqual(e.get("alpha"), "0.4")
        self.assertAlmostEqual(self.sample(e, 110, 60)[3], 0.5)
        set_mapping(400, 300, -100, -50, 400, 300)
        e = self.convert(
            self.gradient('gradientUnits="userSpaceOnUse" x1="0%" x2="100%"')
            + '<rect x="200" y="100" width="100" height="80" fill="url(#g)"/>',
            "100 50 400 300",
        )[0]
        self.assertAlmostEqual(self.sample(e, 150, 80)[0], 95.625, delta=0.5)

    def test_marker_placements_tangents_mid_vertices_and_zero_length(self):
        marker = (
            '<defs><marker id="tip" viewBox="0 0 10 10" refX="5" refY="5" '
            'markerWidth="10" markerHeight="10" markerUnits="strokeWidth" orient="auto">'
            '<polygon points="0,0 10,5 0,10" fill="#dd7700"/></marker></defs>'
        )
        data = self.convert(
            marker + '<path d="M20 80 C20 0 260 0 260 80" fill="#336699" stroke="none" '
            'stroke-width="2.4" marker-end="url(#tip)"/>'
        )
        self.assertEqual(len(data), 2)
        self.assertEqual(
            tuple(float(data[0].get(k)) for k in ("topLeftX", "topLeftY", "width", "height")), (20, 20, 240, 60)
        )
        self.assertEqual(
            tuple(float(data[1].get(k)) for k in ("topLeftX", "topLeftY", "width", "height")), (248, 68, 24, 24)
        )
        self.assertEqual(self.color(data[1]), "rgb(221,119,0)")
        result = _placements(ET.fromstring('<path d="M 80 50 A 30 30 0 0 1 50 80"/>'))
        self.assertAlmostEqual(result[0][2], 90, places=7)
        self.assertAlmostEqual(abs(result[-1][2]), 180, places=7)
        data = self.convert(
            self.marker() + '<path d="M 80 50 A 30 30 0 0 1 50 80" fill="none" stroke="#336699" marker-end="url(#m)"/>'
        )
        self.assertEqual(len(data), 2)
        self.assertFalse(any(e.tag.endswith("}embed") for e in data))
        result = _placements(ET.fromstring('<polyline points="20,20 100,20 100,100" marker-mid="url(#m)"/>'))
        self.assertEqual(result[1][1], (100, 20))
        self.assertAlmostEqual(result[1][2], 45)
        data = self.convert(
            self.marker()
            + '<polyline points="20,20 100,20 100,100" fill="none" stroke="#336699" marker-mid="url(#m)"/>'
        )
        self.assertEqual(len(data), 2)
        result = _placements(ET.fromstring('<path d="M 80 50 A 30 30 0 0 1 50 80 L 20 80" marker-mid="url(#m)"/>'))
        self.assertEqual(len(result), 3)
        self.assertEqual(result[1][1], (50, 80))
        node = ET.fromstring('<path d="M 20 20 H 100 V 80 H 20 Z" marker-mid="url(#m)"/>')
        result = _placements(node)
        self.assertEqual(len(result), 5)
        self.assertEqual(result[0][1], result[-1][1])
        self.assertAlmostEqual(result[0][2], 0)
        self.assertAlmostEqual(result[-1][2], -45)
        data = self.convert(
            self.marker()
            + '<path d="M 20 20 H 100 V 80 H 20 Z" fill="none" stroke="#336699" marker-start="url(#m)" marker-mid="url(#m)" marker-end="url(#m)"/>'
        )
        self.assertEqual(len(data), 6)
        self.assertFalse(any(e.tag.endswith("}embed") for e in data))
        result = _placements(ET.fromstring('<polyline points="20,20 20,20 100,20" marker-mid="url(#m)"/>'))
        self.assertEqual([p[2] for p in result], [0, 0, 0])

    def test_gradient_numbers_stops_quantisation_and_tiny_alpha(self):
        e = self.convert(self.gradient('x2="1" y2="1"') + '<rect width="201" height="100" fill="url(#g)"/>')[0]
        css = self.color(e)
        self.assertRegex(css, r"^linear-gradient\(\d+deg,")
        self.assertTrue(all(re.fullmatch(r"\d+", p) for p in re.findall(r" ([-.\d]+)%", css)))
        for rgb in re.findall(r"rgba\(([^)]+)\)", css):
            self.assertTrue(all(re.fullmatch(r"\d+", c) for c in rgb.split(",")[:3]))
        defs = '<defs><linearGradient id="g"><stop offset="0.499" stop-color="#000000"/><stop offset="0.501" stop-color="#FFFFFF"/></linearGradient></defs>'
        e = self.convert(defs + '<rect width="200" height="100" fill="url(#g)"/>')[0]
        self.assertTrue(e.tag.endswith("}embed"))
        self.assertEqual([n.get("offset") for n in e.findall(".//{*}stop")], ["0.499", "0.501"])
        for width, height in [(50, 200), (200, 100), (201, 99), (390, 35), (37, 270)]:
            data = self.convert(
                self.gradient('x2="1" y2="1"') + f'<rect width="{width}" height="{height}" fill="url(#g)"/>'
            )
            e = data[0]
            if e.tag.endswith("}embed"):
                continue
            for ix in range(11):
                for iy in range(11):
                    x = width * ix / 10
                    y = height * iy / 10
                    self.assertLessEqual(abs(self.sample(e, x, y)[0] - (ix + iy) / 20 * 255), 2 + 1e-8)
        defs = '<defs><linearGradient id="g"><stop offset="0" stop-color="#000000" stop-opacity="0.00000001"/><stop offset="1" stop-color="#FFFFFF" stop-opacity="0.00000001"/></linearGradient></defs>'
        e = self.convert(defs + '<rect width="200" height="100" fill="url(#g)"/>')[0]
        self.assertIn(",0.00000001)", self.color(e))
        self.assertNotIn("e-", self.color(e))
        set_mapping(400, 300, 0, 0, 200, 300)
        e = self.convert(self.gradient('x2="1" y2="1"') + '<rect width="200" height="100" fill="url(#g)"/>')[0]
        self.assertAlmostEqual(self.sample(e, 50, 50)[0], 127.5, places=5)
        self.assertAlmostEqual(self.sample(e, 100, 50)[0], 191.25, places=5)

    def clip(self, body='<rect x="40" y="30" width="100" height="80"/>', attrs=""):
        return f'<defs><clipPath id="c" {attrs}>{body}</clipPath></defs>'

    def test_clips_cut_fills_groups_bboxes_and_convex_windows(self):
        e = self.convert(
            self.clip() + '<rect x="0" y="0" width="200" height="150" fill="#336699" clip-path="url(#c)"/>'
        )[0]
        self.assertEqual(e.get("type"), "custom")
        self.assertEqual([float(e.get(k)) for k in ("topLeftX", "topLeftY", "width", "height")], [40, 30, 100, 80])
        self.assertEqual(e.find("{*}border").get("width"), "0")
        data = self.convert(
            self.clip()
            + '<g clip-path="url(#c)" fill="#336699" transform="translate(10 20)"><rect width="80" height="150"/><g transform="translate(80 0)"><rect width="80" height="150" fill="#AA6633"/></g></g>'
        )
        self.assertEqual(len(data), 2)
        self.assertEqual([float(e.get("topLeftX")) for e in data], [50, 90])
        self.assertEqual([float(e.get("width")) for e in data], [40, 60])
        self.assertNotEqual(self.color(data[0]), self.color(data[1]))
        e = self.convert(
            self.clip('<rect x="0.25" y="0.25" width="0.5" height="0.5"/>', 'clipPathUnits="objectBoundingBox"')
            + '<rect x="10" y="20" width="100" height="80" fill="#336699" clip-path="url(#c)"/>'
        )[0]
        self.assertEqual([float(e.get(k)) for k in ("topLeftX", "topLeftY", "width", "height")], [35, 40, 50, 40])
        e = self.convert(self.clip() + '<polygon points="0,0 200,0 100,200" fill="#336699" clip-path="url(#c)"/>')[0]
        self.assertEqual(e.get("type"), "custom")
        self.assertGreater(float(e.get("width")), 0)
        self.assertLessEqual(float(e.get("width")), 100)
        e = self.convert(
            self.clip() + '<circle cx="80" cy="60" r="10" fill="none" stroke="#336699" clip-path="url(#c)"/>'
        )[0]
        self.assertEqual(e.get("type"), "ellipse")
        self.assertEqual(
            len(
                self.convert(
                    self.clip() + '<rect x="250" y="200" width="30" height="20" fill="#336699" clip-path="url(#c)"/>'
                )
            ),
            0,
        )

    def test_clips_that_need_compositing_or_hide_content_stay_svg(self):
        for body in (
            '<rect width="200" height="150" fill="none" stroke="#336699" clip-path="url(#c)"/>',
            '<g clip-path="url(#c)" opacity="0.5"><rect width="200" height="150" fill="#336699"/></g>',
        ):
            self.assertTrue(self.convert(self.clip() + body)[0].tag.endswith("}embed"))
        defs = '<defs><clipPath id="d"><circle cx="80" cy="70" r="20"/></clipPath><clipPath id="c" clip-path="url(#d)"><rect width="200" height="150"/></clipPath></defs>'
        e = self.convert(defs + '<rect width="200" height="150" fill="#336699" clip-path="url(#c)"/>')[0]
        self.assertTrue(e.tag.endswith("}embed"))
        self.assertEqual({c.get("id") for c in e.findall(".//{*}clipPath")}, {"c", "d"})
        for body, attrs in [
            ('<rect width="100" height="100" display="none"/>', ""),
            ('<rect width="100" height="100"/>', 'transform="scale(0)"'),
        ]:
            e = self.convert(
                self.clip(body, attrs) + '<rect width="200" height="150" fill="#336699" clip-path="url(#c)"/>'
            )[0]
            self.assertTrue(e.tag.endswith("}embed"))
            self.assertIsNotNone(e.find(".//{*}clipPath"))

    def marker(self):
        return '<defs><marker id="m" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="10" markerHeight="10" markerUnits="userSpaceOnUse" orient="auto"><polygon points="1,1 9,5 1,9" fill="#336699"/></marker></defs>'


class DrawingToolsTest(SvgTestCase):
    canvas = (600, 400)

    def test_live_bindings_ports_repeated_exports_cycles_and_missing_anchors(self):
        from ..svg_drawing import Drawing, rect, label

        drawing = Drawing(600, 400)
        body = drawing.add("body", rect(100, 50, fill="#336699"), at=(30, 40))
        note = drawing.add(
            "note",
            label("Label", font_size=20, fill="#112233"),
            at=body.anchor("right").shifted(15, 0),
            own_anchor="left",
        )
        drawing.connect("wire", body.anchor("right"), note.anchor("left"), stroke="#112233")
        self.assertEqual(drawing.resolve(note.anchor("left")), (145, 65))
        body.move_to(80, 100).set_geometry(rect(160, 60, fill="#336699")).set_transform(scale=1.5)
        self.assertEqual(drawing.resolve(note.anchor("left")), (335, 145))
        root = ET.fromstring(drawing.to_svg())
        edge = next(e for e in root if e.get("id") == "wire")
        self.assertEqual(edge.get("d"), "M 320 145 L 335 145")
        drawing = Drawing(600, 400)
        body = drawing.add(
            "body", rect(100, 40).with_ports(outlet=(100, 20)), at=(200, 120), own_anchor="center"
        ).set_transform(rotation=90)
        self.assertAlmostEqual(drawing.resolve(body.port("outlet"))[0], 200)
        self.assertAlmostEqual(drawing.resolve(body.port("outlet"))[1], 170)
        attached = drawing.add(
            "attached", rect(20, 20).with_ports(inlet=(0, 10)), at=body.port("outlet"), own_anchor="port:inlet"
        )
        self.assertEqual(drawing.resolve(attached.port("inlet")), drawing.resolve(body.port("outlet")))
        shape = rect(30, 20, fill="#336699")
        original = ET.tostring(shape.element)
        drawing = Drawing(300, 200)
        a = drawing.add("a", shape, at=(10, 20))
        drawing.add("b", shape, at=a.anchor("right").shifted(10), own_anchor="left")
        first = drawing.to_svg()
        a.move_to(50, 30)
        self.assertNotEqual(first, drawing.to_svg())
        self.assertEqual(ET.tostring(shape.element), original)
        self.assertEqual(drawing.to_svg(), drawing.to_svg())
        drawing = Drawing(300, 200)
        a = drawing.add("a", rect(20, 20))
        b = drawing.add("b", rect(20, 20))
        a.pin(b.anchor())
        b.pin(a.anchor())
        with self.assertRaisesRegex(ValueError, "a -> b -> a"):
            drawing.to_svg()
        other = Drawing(100, 100)
        with self.assertRaisesRegex(ValueError, "another drawing"):
            other.add("foreign", rect(10, 10), at=a.anchor())
        drawing = Drawing(100, 100)
        node = drawing.add("body", rect(20, 20))
        with self.assertRaisesRegex(ValueError, "Unknown box anchor"):
            drawing.resolve(node.anchor("typo"))
        with self.assertRaisesRegex(ValueError, "Unknown port"):
            drawing.resolve(node.port("typo"))

    def test_curve_sampling_and_repeat_along_path(self):
        from ..svg_drawing import Curve, rect
        from ..svg_drawing import repeat_along_path

        curve = Curve("M 0 0 C 100 0 -100 0 10 0", tolerance=0.05)
        self.assertGreater(curve.length, 50)
        straight = Curve("M 0 0 L 100 0")
        repeated = repeat_along_path(ellipse(2, fill="#336699"), straight, count=5)
        self.assertEqual([repeated.ports[f"item_{i}"] for i in range(5)], [(0, 0), (25, 0), (50, 0), (75, 0), (100, 0)])
        result = repeat_along_path(
            lambda i, t: rect(2 + i, 4, fill="#336699"), "M 0 0 L 100 0", spacing=25, phase=10, normal_offset=8
        )
        self.assertEqual(result.ports["item_0"], (10, 8))
        self.assertEqual(len(result.ports), 4)
        circle = Curve("M 10 0 A 10 10 0 1 1 -10 0 A 10 10 0 1 1 10 0 Z", tolerance=0.01)
        repeated = repeat_along_path(rect(2, 4), circle, count=8)
        self.assertEqual(len(set(repeated.ports.values())), 8)
        self.assertAlmostEqual(circle.length, 20 * math.pi, delta=0.2)
        geometry = repeat_along_path(rect(20, 4).with_ports(tip=(20, 2)), "M 0 0 L 0 100", count=1)
        self.assertAlmostEqual(geometry.bounds.width, 4)
        self.assertAlmostEqual(geometry.bounds.height, 20)
        self.assertEqual(geometry.ports["item_0"], (0, 50))
        self.assertAlmostEqual(geometry.ports["item_0.tip"][0], 0)
        self.assertAlmostEqual(geometry.ports["item_0.tip"][1], 60)

    def test_ribbons_extrusion_and_invalid_construction(self):
        from ..svg_drawing import Curve, rect, Drawing

        strip = ribbon("M 0 0 L 100 0", 20, fill="#336699")
        self.assertEqual((strip.bounds.x, strip.bounds.y, strip.bounds.width, strip.bounds.height), (0, -10, 100, 20))
        taper = ribbon("M 0 0 L 100 0", lambda t: 20 * (1 - t), fill="#336699")
        self.assertIn("100,0", taper.element.get("points"))
        sharp = ribbon("M 0 0 L 100 0 L 1 1", 20, miter_limit=2, fill="#336699")
        self.assertLess(sharp.bounds.width, 140)
        self.assertLess(sharp.bounds.height, 50)
        ring = ribbon("M 40 40 H 140 V 140 H 40 Z", 10, fill="#336699")
        self.assertEqual(ring.element.get("fill-rule"), "evenodd")
        drawing = Drawing(200, 200)
        drawing.add("ring", ring)
        data = self.convert(document=drawing.to_svg())
        self.assertTrue(data[0].tag.endswith("}embed"))
        self.assertEqual(data[0].find(".//{*}path").get("fill-rule"), "evenodd")
        faces = []
        shape = extrude(
            [(0, 0), (100, 0), (100, 40), (0, 40)],
            (20, 15),
            front={"fill": "#112233"},
            side=lambda i, normal: faces.append((i, normal)) or {"fill": "#445566"},
        )
        self.assertEqual([i for i, _ in faces], [1, 2])
        self.assertEqual((shape.bounds.width, shape.bounds.height), (120, 55))
        self.assertEqual(list(shape.element)[-1].get("fill"), "#112233")
        self.assertEqual(shape.ports["back_center"], (70, 35))
        for action in [
            lambda: Curve("M 0 0 L 0 0").samples(),
            lambda: Curve("M 0 0 L 10 0 M 20 0 L 30 0").samples(),
            lambda: repeat_along_path(rect(2, 2), "M 0 0 L 100 0", spacing=0),
            lambda: ribbon("M 0 0 L 100 0", -1),
            lambda: extrude([(0, 0), (10, 0), (5, 2), (10, 10), (0, 10)], (2, 2), front={}, side={}),
            lambda: Drawing(float("nan"), 100),
        ]:
            with self.assertRaises(ValueError):
                action()

    def test_cutaway_and_zoom_scopes_bounds_windows_and_resources(self):
        from ..svg_drawing import Drawing, Box, rect, zoom
        from ..svg_drawing import path, group
        from ..svg_drawing import cutaway

        source = rect(100, 80, fill="#336699").with_ports(center=(50, 40), outside=(95, 70))
        section = cutaway(source, Box(20, 10, 40, 40))
        self.assertEqual(
            (section.bounds.x, section.bounds.y, section.bounds.width, section.bounds.height), (20, 10, 40, 40)
        )
        self.assertNotIn("outside", section.ports)
        enlarged = zoom(source, Box(20, 10, 40, 40), 2)
        self.assertEqual(
            (enlarged.bounds.x, enlarged.bounds.y, enlarged.bounds.width, enlarged.bounds.height), (0, 0, 80, 80)
        )
        drawing = Drawing(300, 200)
        drawing.add("one", section)
        drawing.add("two", section, at=(100, 0))
        root = ET.fromstring(drawing.to_svg())
        ids = [n.get("id") for n in root.iter() if n.get("id")]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(self.convert(document=drawing.to_svg())), 2)
        first = rect(20, 10).moved(10, 20).rotated(90, about=(0, 0))
        second = path("M 0 0 L 10 0 L 0 10 Z").scaled(2).moved(60, 15)
        window = group(first, second)
        original = ET.tostring(window.element)
        result = cutaway(rect(200, 200, x=-50, y=-50), window)
        clip = result.element.find("./defs/clipPath")
        self.assertEqual([n.tag for n in clip], ["rect", "path"])
        expected = [((0, 0), (-20, 10)), ((20, 10), (-30, 30)), ((0, 0), (60, 15)), ((10, 10), (80, 35))]
        for leaf, cases in zip(clip, (expected[:2], expected[2:])):
            matrix = parse_transform(leaf.get("transform", ""))
            for point, target in cases:
                for actual, wanted in zip(matrix.point(*point), target):
                    self.assertAlmostEqual(actual, wanted)
        self.assertEqual(ET.tostring(window.element), original)
        ring = path("M 10 10 H 90 V 90 H 10 Z M 30 30 H 70 V 70 H 30 Z", fill_rule="evenodd")
        drawing = Drawing(100, 100)
        drawing.add("texture", cutaway(rect(100, 100, fill="#336699"), ring), own_anchor="origin")
        converted = self.convert(document=drawing.to_svg())
        self.assertEqual(converted.find(".//{*}clipPath/{*}path").get("clip-rule"), "evenodd")
        window = Geometry(
            ET.fromstring(
                '<g fill-rule="evenodd"><path d="M0 0H10V10Z"/>'
                '<g clip-rule="nonzero"><path d="M0 0H10V10Z" fill-rule="evenodd"/></g>'
                '<path d="M0 0H10V10Z" fill-rule="nonzero" style="fill-rule:evenodd;clip-rule:evenodd"/>'
                '<path d="M0 0H10V10Z" clip-rule="initial"/></g>'
            ),
            Box(0, 0, 10, 10),
        )
        clip = cutaway(rect(20, 20), window).element.find("./defs/clipPath")
        self.assertEqual([n.get("clip-rule") for n in clip], ["evenodd", "nonzero", "evenodd", "nonzero"])
        window = rect(20, 10, fill="none", stroke="#112233", stroke_width=12, filter="url(#blur)")
        clip = cutaway(rect(100, 100), window).element.find("./defs/clipPath")
        self.assertIsNone(clip[0].get("filter"))
        self.assertEqual((clip[0].get("width"), clip[0].get("height")), ("20", "10"))
        with self.assertRaisesRegex(ValueError, "existing clip or mask"):
            cutaway(rect(100, 100), rect(20, 10, mask="url(#mask)"))
        window = Geometry(
            ET.fromstring(
                '<g transform="translate(10 5)"><defs><path id="edge" fill-rule="evenodd" '
                'd="M0 0H40V40H0Z M10 10H30V30H10Z"/></defs>'
                '<use href="#edge"/></g>'
            ),
            Box(10, 5, 40, 40),
        )
        texture = Geometry(
            ET.fromstring(
                '<g><defs><pattern id="ink" width="5" height="5" patternUnits="userSpaceOnUse">'
                '<rect width="2" height="5" fill="#336699"/></pattern></defs>'
                '<rect width="70" height="60" fill="url(#ink)"/></g>'
            ),
            Box(0, 0, 70, 60),
        )
        clipped = cutaway(texture, window)
        drawing = Drawing(200, 100)
        drawing.add("one", clipped, at=(5, 5), own_anchor="origin")
        drawing.add("two", clipped, at=(110, 10), own_anchor="origin").set_transform(rotation=15, scale=0.8)
        root = ET.fromstring(drawing.to_svg())
        ids = [node.get("id") for node in root.iter() if node.get("id")]
        self.assertEqual(len(ids), len(set(ids)))
        for clip in root.findall(".//{*}clipPath"):
            self.assertEqual([node.tag.split("}")[-1] for node in clip], ["path"])
            self.assertEqual(clip[0].get("clip-rule"), "evenodd")
            self.assertIsNone(clip[0].get("id"))
        for node in root.iter():
            for value in node.attrib.values():
                for reference in re.findall(r"url\(#([^)]*)\)", value):
                    self.assertIn(reference, ids)
        self.assertEqual(len(self.convert(document=drawing.to_svg())), 2)
        shared_window = Geometry(ET.fromstring('<use href="#shared-outline" clip-rule="evenodd"/>'), Box(0, 0, 40, 40))
        shared = Drawing(100, 100)
        shared.add_defs('<path id="shared-outline" d="M0 0H40V40H0Z M10 10H30V30H10Z"/>')
        shared.add("sample", cutaway(texture, shared_window), own_anchor="origin")
        shared_root = ET.fromstring(shared.to_svg())
        self.assertEqual(shared_root.find(".//{*}clipPath/{*}use").get("href"), "#shared-outline")
        self.assertIsNotNone(shared_root.find('.//*[@id="shared-outline"]'))
        window = Geometry(
            ET.fromstring(
                '<g transform="translate(10 5)"><defs><g id="pair" transform="scale(2)">'
                '<rect id="a" width="10" height="10"/><rect id="b" x="20" width="10" height="10"/>'
                '</g></defs><use href="#pair" x="5" transform="rotate(90)"/>'
                '<use href="#pair" x="40"/></g>'
            ),
            Box(-10, 10, 100, 70),
        )
        clipped = cutaway(rect(200, 200, x=-50, y=-50), window)
        leaves = clipped.element.findall("./defs/clipPath/*")
        self.assertEqual(len(leaves), 4)
        self.assertEqual(parse_transform(leaves[0].get("transform")).point(0, 0), (10, 10))
        self.assertEqual(parse_transform(leaves[2].get("transform")).point(0, 0), (50, 5))
        drawing = Drawing(200, 200)
        drawing.add("clipped", clipped)
        drawing.to_svg()  # Repeated definitions must not duplicate instance IDs.
        cyclic = Geometry(ET.fromstring('<g id="cycle"><use href="#cycle"/></g>'), Box(0, 0, 10, 10))
        with self.assertRaisesRegex(ValueError, "Cyclic cutaway"):
            cutaway(rect(20, 20), cyclic)

    def test_callout_leader_and_label_bounds(self):
        from ..svg_drawing import Drawing, rect
        from ..svg_drawing import label

        drawing = Drawing(600, 400)
        body = drawing.add("body", rect(80, 40), at=(40, 80))
        note = drawing.callout(
            "note",
            "Two lines\nStay together",
            body.anchor("right"),
            at=body.anchor("right").shifted(50, -30),
            font_size=18,
            label_style={"fill": "#112233"},
            line_style={"stroke": "#445566"},
        )
        endpoint = drawing.resolve(note.edge_toward(body.anchor("right")))
        self.assertAlmostEqual(endpoint[0], note.bounds.x)
        before = drawing.resolve(note.anchor())
        body.move_to(100, 130)
        after = drawing.resolve(note.anchor())
        self.assertAlmostEqual(after[0] - before[0], 60)
        self.assertAlmostEqual(after[1] - before[1], 50)
        root = ET.fromstring(drawing.to_svg())
        ids = [n.get("id") for n in root]
        self.assertLess(ids.index("note-leader"), ids.index("note"))
        leader = next(n for n in root if n.get("id") == "note-leader")
        edge = drawing.resolve(note.edge_toward(body.anchor("right")))
        endpoint = path_segments(leader.get("d"))[-1][1]
        self.assertAlmostEqual(math.dist(edge, endpoint), 5, places=7)
        plain = label("AB", font_size=20, font_family="Arial")
        spaced = label("AB", font_size=20, font_family="Arial", letter_spacing=4)
        self.assertAlmostEqual(spaced.bounds.width - plain.bounds.width, 4, delta=0.1)
        centered = label("AB", font_size=20, font_family="Arial", text_anchor="middle")
        self.assertAlmostEqual(centered.bounds.anchor()[0], 0, delta=0.2)
        safe = label("A & B < C", font_size=20, font_family='Custom "Font"')
        self.assertEqual("".join(safe.element.itertext()), "A & B < C")
        ET.fromstring(ET.tostring(safe.element))


class DrawingHelpTest(unittest.TestCase):
    def test_public_facade_reload_keeps_registered_implementations(self):
        from .. import svg_drawing as drawing

        before = {name: getattr(drawing, name) for name in drawing.__all__}
        registry = dict(drawing._DRAWING_APIS)
        drawing = importlib.reload(drawing)
        self.assertEqual(set(before), set(drawing.__all__))
        for name, target in before.items():
            self.assertIs(getattr(drawing, name), target)
        self.assertEqual(drawing._DRAWING_APIS, registry)
        namespace = {}
        exec("from scripts.svg_lib.svg_drawing import *", namespace)
        self.assertTrue(set(drawing.__all__).issubset(namespace))
        self.assertNotIn("_DRAWING_APIS", namespace)

    def test_default_help_is_a_small_capability_index_and_empty_queries_return_it(self):
        text = drawing_help()
        topics = "shapes parts finish repeat ribbon extrude section anchors layout connect export math curves inspect"
        for topic in topics.split():
            self.assertIn("- " + topic + "：", text)
        self.assertEqual(sum(line.startswith("- ") for line in text.splitlines()), 14)
        for absent in ("【接口", "_flatten", "miter_limit"):
            self.assertNotIn(absent, text)
        self.assertLess(len(text), 3200)
        self.assertIn("d.arrow(start, end", text)
        self.assertEqual(text, drawing_help("  "))
        self.assertEqual(text, drawing_help("--help"))
        with self.assertRaises(TypeError):
            drawing_help(None)

    def test_exact_help_follows_actual_signatures_and_explains_semantics(self):
        text = drawing_help("Node.pin", "Drawing.resolve")
        self.assertIn("Node.pin(target, *, own_anchor='center', offset=(0, 0))", text)
        for phrase in ("保持联动", "固定位置", "画布坐标", "快照"):
            self.assertIn(phrase, text)
        self.assertNotIn("Node.pin(self", text)
        defaults = {**Node.pin.__kwdefaults__, "offset": (17, 9)}
        with patch.object(Node.pin, "__kwdefaults__", defaults):
            self.assertIn("offset=(17, 9)", drawing_help("Node.pin"))
        self.assertIn("offset=(0, 0)", drawing_help("Node.pin"))
        stretch = drawing_help("非等比缩放")
        self.assertEqual(stretch, drawing_help("Geometry.stretched"))
        self.assertIn("不烘焙成固定线宽", stretch)
        self.assertIn("不保证原生", stretch)
        self.assertIn("Node.bounds → Box 快照（只读属性）", drawing_help("Node.bounds"))
        self.assertNotIn("Node.bounds()", drawing_help("Node.bounds"))
        self.assertIn("Curve(d, tolerance=0.25)", drawing_help("Curve"))
        self.assertIn("Drawing.add_defs(xml)", drawing_help("渐变"))
        self.assertIn("None", drawing_help("Drawing.add_defs"))

    def test_topic_help_does_not_expand_unrelated_capabilities(self):
        text = drawing_help("anchors")
        self.assertIn("Drawing.add(", text)
        self.assertIn("Node.pin(", text)
        self.assertNotIn("extrude(", text)
        self.assertNotIn("repeat_along_path(", text)
        self.assertNotIn("【接口 Node.set_geometry】", text)
        self.assertIn("Node.set_geometry", text)

    def test_aliases_resolve_and_batch_queries_deduplicate_without_losing_detail(self):
        for alias, name in (
            ("沿曲线排列", "repeat"),
            ("绑定", "Node.pin"),
            ("pin", "Node.pin"),
            ("node.PIN", "Node.pin"),
            ("局部放大", "zoom"),
            ("裁切", "cutaway"),
            ("纹理", "texture_clip"),
            ("纹理裁切", "texture_clip"),
        ):
            self.assertEqual(drawing_help(alias), drawing_help(name), alias)
        texture = drawing_help("纹理")
        for phrase in ("cutaway(texture, outline)", "填充区域", "局部坐标", "快照", "Node.geometry"):
            self.assertIn(phrase, texture)
        text = drawing_help("Node.pin", "绑定", "pin", "repeat", "沿曲线排列")
        self.assertEqual(text.count("【接口 Node.pin】"), 1)
        self.assertEqual(text.count("【主题 repeat｜"), 1)
        both = drawing_help("anchors", "Node.pin")
        self.assertIn("【主题 anchors｜", both)
        self.assertIn("【接口 Node.pin】", both)

    def test_unknown_and_unimplemented_requests_are_explicit(self):
        typo = drawing_help("Node.pni")
        self.assertIn("未找到公开能力", typo)
        self.assertIn("Node.pin", typo)
        unsupported = drawing_help("自动避障")
        self.assertIn("不提供", unsupported)
        self.assertIn("connect", unsupported)
        for name in ("_Layout", "_flatten", "Geometry.transformed", "Matrix"):
            text = drawing_help(name)
            self.assertIn("未找到公开能力", text)
            self.assertNotIn("【接口 " + name + "】", text)

    def test_help_queries_do_not_construct_render_or_write(self):
        with patch("xml.etree.ElementTree.Element", side_effect=AssertionError("constructed SVG")):
            with patch("pathlib.Path.write_text", side_effect=AssertionError("wrote file")):
                with patch("subprocess.run", side_effect=AssertionError("started process")):
                    text = drawing_help("export", "repeat", "anchors", "Drawing.add_defs", "射线", "光路", "纹理")
        self.assertIn("atomize_svg_to_slide", text)
        self.assertIn("count 与 spacing", text)

    def test_metadata_is_registered_only_for_real_public_operations(self):
        from .. import svg_drawing as drawing

        for name, doc in drawing._DRAWING_APIS.items():
            self.assertFalse(any(part.startswith("_") for part in name.split(".")))
            self.assertIn(doc.topic, drawing._HELP_TOPICS)
            self.assertTrue(doc.semantics)
            self.assertTrue(doc.returns)
            self.assertLessEqual(len(doc.example.splitlines()), 3)
            ast.parse(doc.example)
            self.assertIn("【接口 " + name + "】", drawing.drawing_help(name))
            self.assertNotIn("<svg", doc.example)


class MathDrawingTest(unittest.TestCase):
    def test_mapping_roundtrip_and_validation(self):
        for y_up in (True, False):
            coords = CoordinateMap((-2, 6), (-3, 1), Box(20, 30, 400, 120), y_up=y_up)
            self.assertEqual(coords.point(-2, -3), (20, 150 if y_up else 30))
            self.assertEqual(coords.point(6, 1), (420, 30 if y_up else 150))
            for p in [(-2, -3), (1.25, -0.3), (8, 5)]:
                actual = coords.inverse(*coords.point(*p))
                for a, b in zip(actual, p):
                    self.assertAlmostEqual(a, b)
            dx, dy = coords.vector(1, 2)
            self.assertEqual((dx, dy), (50, -60 if y_up else 60))
            a, b = coords.point(0, 0), coords.point(1, 2)
            self.assertEqual((b[0] - a[0], b[1] - a[1]), (dx, dy))
        for limits in [(1, 1), (2, 1), (0, math.inf), (-1e308, 1e308)]:
            with self.assertRaises(ValueError):
                CoordinateMap(limits, (0, 1), Box(0, 0, 10, 10))
        with self.assertRaises(ValueError):
            CoordinateMap((0, 1), (0, 1), Box(0, 0, 0, 10))
        with self.assertRaises(TypeError):
            CoordinateMap((0, 1), (0, 1), (0, 0, 10, 10))
        with self.assertRaises(TypeError):
            CoordinateMap((0, 1), (0, 1), Box(0, 0, 10, 10), y_up="yes")
        coords = CoordinateMap((0, 1), (0, 1), Box(0, 0, 10, 10))
        with self.assertRaises(ValueError):
            coords.point(0, math.nan)

    def test_sampling_accuracy_continuity_asymptotes_and_clipping(self):
        coords = CoordinateMap((-2, 2), (-1, 5), Box(40, 30, 360, 300))
        samples = sample_function(lambda x: x * x, (-2, 2), mapping=coords, tolerance=0.2, max_step=1)
        self.assertEqual(samples.gaps, ())
        self.assertEqual(len(samples.segments), 1)
        for a, b in zip(samples.segments[0], samples.segments[0][1:]):
            for t in (0.2, 0.5, 0.8):
                sx, sy = (a[0] * (1 - t) + b[0] * t, a[1] * (1 - t) + b[1] * t)
                x, _ = coords.inverse(sx, sy)
                self.assertLessEqual(abs(sy - coords.point(x, x * x)[1]), 0.200001)
        samples = sample_function(lambda x: 10000 * x, (-1, 1), max_step=2)
        self.assertEqual(samples.segments, (((-1.0, -10000.0), (1.0, 10000.0)),))
        self.assertEqual(samples.gaps, ())
        called = []

        def function(x):
            self.assertNotIn(x, (-1, 0.13, 1))
            called.append(x)
            return x

        samples = sample_function(function, (-1, 1), breaks=(-1, 0.13, 1, 0.13))
        self.assertEqual(len(samples.segments), 2)
        self.assertLess(samples.segments[0][-1][0], 0.13)
        self.assertGreater(samples.segments[1][0][0], 0.13)
        self.assertIn((0.13, 0.13), samples.gaps)
        self.assertEqual(len(called), len(set(called)))
        self.assertEqual(samples.evaluations, len(called))
        samples = sample_function(math.log, (-1, 2))
        self.assertTrue(samples.segments)
        self.assertTrue(all(p[0] > 0 for s in samples.segments for p in s))
        for bad in [math.nan, math.inf, -math.inf]:
            samples = sample_function(lambda x: bad if abs(x) < 0.25 else x, (-1, 1))
            self.assertEqual(len(samples.segments), 2)
            self.assertTrue(any(a <= 0 <= b for a, b in samples.gaps))
        coords = CoordinateMap((-2, 2), (-4, 4), Box(0, 0, 400, 200))
        for location, function in [
            (0, lambda x: 1 / x),
            (0.013, lambda x: 1 / (x - 0.013)),
            (0.123, lambda x: 1 if x >= 0.123 else 0),
        ]:
            samples = sample_function(function, (-2, 2), mapping=coords)
            self.assertEqual(len(samples.segments), 2)
            self.assertTrue(any(a <= location <= b for a, b in samples.gaps))
            split = coords.point(location, 0)[0]
            for segment in samples.segments:
                self.assertFalse(segment[0][0] < split < segment[-1][0])
        for y_up in (True, False):
            coords = CoordinateMap((-1, 1), (-1, 1), Box(20, 30, 200, 100), y_up=y_up)
            samples = sample_function(lambda x: 3 * x, (-2, 2), mapping=coords)
            self.assertEqual(samples.gaps, ())
            self.assertEqual(len(samples.segments), 1)
            for point in samples.segments[0]:
                self.assertTrue(20 <= point[0] <= 220 and 30 <= point[1] <= 130)
            for actual, expected in zip(samples.segments[0][0], coords.point(-1 / 3, -1)):
                self.assertAlmostEqual(actual, expected)
            raw = sample_function(lambda x: 3 * x, (-2, 2), mapping=coords, clip=False)
            self.assertTrue(any(p[1] < 30 or p[1] > 130 for s in raw.segments for p in s))
        coords = CoordinateMap((-2, 2), (1, 2), Box(0, 0, 400, 200))
        samples = sample_function(lambda x: x * x, (-2, 2), mapping=coords)
        self.assertEqual(len(samples.segments), 2)
        self.assertEqual(samples.gaps, ())
        self.assertLess(samples.segments[0][-1][0], samples.segments[1][0][0])

    def test_sampler_errors_caps_and_invalid_configuration(self):
        with self.assertRaises(TypeError):
            sample_function(lambda x: object(), (0, 1))

        def broken(x):
            raise RuntimeError("bug")

        with self.assertRaisesRegex(RuntimeError, "bug"):
            sample_function(broken, (0, 1))
        calls = []

        def counted(x):
            calls.append(x)
            return x * x

        with self.assertRaisesRegex(ValueError, "max_points"):
            sample_function(counted, (0, 1), max_points=5, max_step=1, tolerance=1e-8)
        self.assertEqual(len(calls), 5)
        samples = sample_function(lambda x: x * x, (0, 1), max_step=1, max_depth=0, tolerance=1e-8)
        self.assertEqual(samples.segments, ())
        self.assertEqual(samples.gaps, ((0.0, 1.0),))
        function = unittest.mock.Mock(return_value=0)
        for kwargs in [
            dict(tolerance=0),
            dict(tolerance=math.inf),
            dict(max_step=0),
            dict(max_step=1e-300),
            dict(max_points=4),
            dict(max_points=True),
            dict(max_depth=31),
            dict(max_depth=-1),
            dict(max_depth=1.5),
            dict(breaks=[2]),
            dict(breaks=[math.nan]),
            dict(mapping="map"),
            dict(clip="yes"),
        ]:
            with self.assertRaises((TypeError, ValueError)):
                sample_function(function, (0, 1), **kwargs)
        function.assert_not_called()
        with self.assertRaises(TypeError):
            sample_function("x*x", (0, 1))

    def test_samples_export_geometry_ports_and_empty_samples(self):
        from ..svg_drawing import CoordinateMap, Box, sample_function, Drawing, rect

        coords = CoordinateMap((-2, 2), (-2, 2), Box(40, 30, 400, 200))
        samples = sample_function(lambda x: x, (-2, 2), mapping=coords, breaks=(0,))
        geometry = samples.to_geometry(stroke="#336699", stroke_width=2).with_ports(tip=coords.point(1, 1))
        self.assertEqual(geometry.element.get("d").count("M"), 2)
        self.assertEqual(geometry.element.get("fill"), "none")
        drawing = Drawing(500, 300)
        curve = drawing.add("curve", geometry)
        note = drawing.add("note", rect(10, 10), at=curve.port("tip"), own_anchor="center")
        self.assertEqual(drawing.resolve(note.anchor("center")), coords.point(1, 1))
        curve.move_to(10, 20)
        self.assertEqual(drawing.resolve(note.anchor("center")), (350, 100))
        with tempfile.TemporaryDirectory() as tmp:
            svg = drawing.write(Path(tmp) / "sample.svg")
            from ..atomize_svg_to_slide import set_mapping, atomize_svg_to_slide

            set_mapping(500, 300, 0, 0, 500, 300)
            converted = ET.fromstring(atomize_svg_to_slide(svg))
            self.assertEqual(len(converted.findall(".//{*}shape")), 2)
            self.assertFalse(converted.findall(".//{*}embed"))
        samples = sample_function(lambda x: math.nan, (-1, 1))
        self.assertEqual(samples.segments, ())
        drawing = Drawing(100, 100)
        drawing.add("empty", samples.to_geometry())
        self.assertFalse(ET.fromstring(drawing.to_svg()).findall(".//{*}path"))

    def test_task_hints_resolve_real_apis_and_allow_batch_aliases(self):
        from .. import svg_drawing as d

        for key, (_, _, apis) in d._HELP_TASKS.items():
            for api in apis:
                self.assertIn(api, d._DRAWING_APIS)
                self.assertIn("【接口 " + api + "】", d.drawing_help(api))
        self.assertEqual(d.drawing_help("导数"), d.drawing_help("derivatives"))
        self.assertEqual(d.drawing_help("蛋白结合"), d.drawing_help("protein"))
        self.assertEqual(d.drawing_help("射线"), d.drawing_help("rays"))
        self.assertEqual(d.drawing_help("光路"), d.drawing_help("rays"))
        rays = d.drawing_help("射线", "光路", "Curve.ray")
        self.assertEqual(rays.count("【任务提示 rays"), 1)
        self.assertIn("【接口 Curve.ray】", rays)
        combined = d.drawing_help("导数", "derivative", "sample_function")
        self.assertEqual(combined.count("【任务提示 derivatives"), 1)
        self.assertIn("【接口 sample_function】", combined)
        with patch.object(d, "sample_function", side_effect=AssertionError("computed")):
            self.assertIn("CoordinateMap", d.drawing_help("导数"))


class CircularConstructionTest(unittest.TestCase):
    def points(self, geometry, subpath=0):
        return geometry.contour(subpath, tolerance=0.001).samples()[0]

    def winding(self, points, point):
        result = 0
        for a, b in zip(points, points[1:]):
            cross = (b[0] - a[0]) * (point[1] - a[1]) - (b[1] - a[1]) * (point[0] - a[0])
            if a[1] <= point[1] < b[1] and cross > 0:
                result += 1
            if b[1] <= point[1] < a[1] and cross < 0:
                result -= 1
        return result

    def assertSweep(self, points, center, radius, sweep, tolerance=0.001):
        vectors = [(p[0] - center[0], p[1] - center[1]) for p in points]
        for vector in vectors:
            self.assertAlmostEqual(math.hypot(*vector), radius, delta=tolerance)
        angle = sum(
            math.atan2(a[0] * b[1] - a[1] * b[0], a[0] * b[0] + a[1] * b[1]) for a, b in zip(vectors, vectors[1:])
        )
        self.assertAlmostEqual(angle, math.radians(sweep), delta=tolerance)

    def test_circular_arcs_annuli_ports_and_invalid_radii(self):
        center, radius = (17, -9), 31
        for start, sweep in ((350, 30), (10, -30), (0, 180), (0, -180), (45, 270), (45, -270), (725, 40)):
            with self.subTest(start=start, sweep=sweep):
                arc = circular_arc(center, radius, start, sweep, stroke="#334455")
                self.assertEqual(arc.element.get("fill"), "none")
                self.assertNotIn("Z", arc.element.get("d"))
                self.assertSweep(self.points(arc), center, radius, sweep)
                for name, angle in (("start", start), ("mid", start + sweep / 2), ("end", start + sweep)):
                    want = (
                        center[0] + radius * math.cos(math.radians(angle)),
                        center[1] + radius * math.sin(math.radians(angle)),
                    )
                    for a, b in zip(arc.ports[name], want):
                        self.assertAlmostEqual(a, b, places=10)
        for sweep in (360, -360):
            arc = circular_arc((0, 0), 20, 37, sweep)
            self.assertEqual(arc.ports["start"], arc.ports["end"])
            self.assertTrue(arc.contour().samples()[1])
            self.assertSweep(self.points(arc), (0, 0), 20, sweep)
            self.assertAlmostEqual(arc.bounds.x, -20, places=8)
            self.assertAlmostEqual(arc.bounds.y, -20, places=8)
            self.assertAlmostEqual(arc.bounds.width, 40, places=8)
            self.assertAlmostEqual(arc.bounds.height, 40, places=8)
        center, inner, outer = (5, -3), 4, 10
        for sweep in (90, -90, 180, -180, 240, -240):
            region = annular_sector(center, inner, outer, 350, sweep)
            points = self.points(region)
            shifted = [(x - center[0], y - center[1]) for x, y in points]
            area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(shifted, shifted[1:])) / 2
            expected = (outer * outer - inner * inner) * math.radians(sweep) / 2
            self.assertAlmostEqual(area / expected, 1, places=3)
            self.assertEqual(self.winding(points, center), 0)
            self.assertEqual(self.winding(points, region.ports["mid"]), 1 if sweep > 0 else -1)
            for name in ("outer_start", "outer_end"):
                self.assertAlmostEqual(math.dist(region.ports[name], center), outer)
            for name in ("inner_start", "inner_end"):
                self.assertAlmostEqual(math.dist(region.ports[name], center), inner)
        for sweep in (360, -360):
            ring = annular_sector((0, 0), 4, 10, 37, sweep, fill="#334455", stroke="#112233")
            outer, inner = self.points(ring, 0), self.points(ring, 1)
            self.assertSweep(outer, (0, 0), 10, sweep)
            self.assertSweep(inner, (0, 0), 4, -sweep)
            for point, expected in (((0, 0), 0), ((7, 0), 1 if sweep > 0 else -1), ((11, 0), 0)):
                self.assertEqual(self.winding(outer, point) + self.winding(inner, point), expected)
            self.assertTrue(ring.contour(0).samples()[1])
            self.assertTrue(ring.contour(1).samples()[1])
            self.assertNotIn("L", [op for op, _ in path_segments(ring.element.get("d"))])
            self.assertEqual(ring.ports["outer_start"], ring.ports["outer_end"])
            self.assertEqual(ring.ports["inner_start"], ring.ports["inner_end"])
        sector = annular_sector((0, 0), 0, 10, 0, 90)
        self.assertEqual(sector.ports["inner_start"], (0, 0))
        self.assertEqual(sector.ports["inner_end"], (0, 0))
        self.assertEqual(self.winding(self.points(sector), (2, 2)), 1)
        self.assertEqual(self.winding(self.points(sector), (-2, 2)), 0)
        for sweep in (360, -360):
            disk = annular_sector((0, 0), 0, 10, 0, sweep)
            self.assertEqual(self.winding(self.points(disk), (0, 0)), 1 if sweep > 0 else -1)
            self.assertNotIn("L", [op for op, _ in path_segments(disk.element.get("d"))])
        start, regions = -90.0, []
        for value in (2, 3, 5):
            sweep = value / 10 * 360
            regions.append(annular_sector((17, 23), 8, 20, start, sweep))
            start += sweep
        for a, b in zip(regions, regions[1:] + regions[:1]):
            for outer in ("outer", "inner"):
                for x, y in zip(a.ports[outer + "_end"], b.ports[outer + "_start"]):
                    self.assertAlmostEqual(x, y, places=10)
        center = (13, -7)
        for geometry in (circular_arc(center, 30, 20, 240), annular_sector(center, 10, 30, 20, -240)):
            drawing = Drawing(400, 300)
            node = drawing.add("part", geometry, at=(123, 87), own_anchor="port:center")
            marker = drawing.add("marker", ellipse(1), at=node.port("mid"), own_anchor="center")
            node.set_transform(rotation=30, scale=1.7)
            for name, value in geometry.ports.items():
                x, y = value[0] - center[0], value[1] - center[1]
                expected = (
                    123 + 1.7 * (x * math.cos(math.pi / 6) - y * math.sin(math.pi / 6)),
                    87 + 1.7 * (x * math.sin(math.pi / 6) + y * math.cos(math.pi / 6)),
                )
                for a, b in zip(drawing.resolve(node.port(name)), expected):
                    self.assertAlmostEqual(a, b, places=9)
            node.move_to(150, 120)
            for a, b in zip(drawing.resolve(marker.anchor()), drawing.resolve(node.port("mid"))):
                self.assertAlmostEqual(a, b, places=9)
        for radius in (0, -1, math.inf, math.nan):
            with self.assertRaises(ValueError):
                circular_arc((0, 0), radius, 0, 90)
        for inner, outer in ((-1, 10), (10, 10), (11, 10), (0, 0), (math.inf, 10)):
            with self.assertRaises(ValueError):
                annular_sector((0, 0), inner, outer, 0, 90)
        for sweep in (0, 361, -361, math.inf, math.nan):
            with self.assertRaises(ValueError):
                circular_arc((0, 0), 10, 0, sweep)
            with self.assertRaises(ValueError):
                annular_sector((0, 0), 4, 10, 0, sweep)
        with self.assertRaises(ValueError):
            circular_arc((math.nan, 0), 10, 0, 90)
        with self.assertRaises(ValueError):
            annular_sector((0, 0), 4, 10, math.inf, 90)

    def test_atomize_preserves_arc_radius_direction_and_the_full_ring_hole(self):
        arc = circular_arc((80, 120), 50, 350, -270, stroke="#334455", stroke_width=2)
        ring = annular_sector((270, 120), 25, 70, 37, -360, fill="#778899")
        svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 240">'
        svg += "".join(ET.tostring(g.element, encoding="unicode") for g in (arc, ring)) + "</svg>"
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "arcs.svg"
            source.write_text(svg)
            set_mapping(400, 240, 0, 0, 400, 240)
            result = ET.fromstring(atomize_svg_to_slide(source))
        shapes = result.findall("{*}data/{*}shape")
        self.assertEqual(len(shapes), 2)
        self.assertTrue(all(s.get("type") == "custom" for s in shapes))

        def global_points(shape, subpath=0):
            points = self.points(path(shape.get("path")), subpath)
            return [(p[0] + float(shape.get("topLeftX")), p[1] + float(shape.get("topLeftY"))) for p in points]

        self.assertSweep(global_points(shapes[0]), (80, 120), 50, -270, tolerance=0.03)
        loops = [global_points(shapes[1], i) for i in (0, 1)]
        self.assertEqual(sum(self.winding(p, (270, 120)) for p in loops), 0)
        self.assertEqual(sum(self.winding(p, (320, 120)) for p in loops), -1)
        self.assertSweep(loops[0], (270, 120), 70, -360, tolerance=0.03)
        self.assertSweep(loops[1], (270, 120), 25, 360, tolerance=0.03)

    def test_circular_help_is_discoverable_without_expanding_the_index(self):
        from .. import svg_drawing as drawing

        for alias in ("圆弧", "arc", "角标", "角度标记"):
            self.assertEqual(drawing.drawing_help(alias), drawing.drawing_help("circular_arc"))
        for alias in ("扇形", "环段"):
            self.assertEqual(drawing.drawing_help(alias), drawing.drawing_help("annular_sector"))
        for name in ("circular_arc", "annular_sector"):
            self.assertIn(name, drawing.__all__)
            self.assertNotIn(name, drawing.drawing_help())
            self.assertIn("顺时针", drawing.drawing_help(name))


class CircleTangentPointsTest(unittest.TestCase):
    def assertTangency(self, center, radius, point, contact):
        radial = tuple((contact[i] - center[i]) / radius for i in (0, 1))
        length = math.dist(point, contact)
        direction = tuple((point[i] - contact[i]) / length for i in (0, 1))
        self.assertAlmostEqual(math.hypot(*radial), 1, places=13)
        self.assertAlmostEqual(sum(a * b for a, b in zip(radial, direction)), 0, places=13)

    def test_tangent_contacts_boundary_cases_and_invalid_inputs(self):
        for center, radius, point in [((0, 0), 5, (13, 0)), ((-7, 11), 3, (8, 15)), ((10, -6), 2, (8, -13))]:
            contacts = circle_tangent_points(center, radius, point)
            self.assertEqual(len(contacts), 2)
            for contact in contacts:
                self.assertTangency(center, radius, point, contact)
        expected = ((25 / 13, 60 / 13), (25 / 13, -60 / 13))
        contacts = circle_tangent_points((0, 0), 5, (13, 0))
        for actual, want in zip(contacts, expected):
            for a, b in zip(actual, want):
                self.assertAlmostEqual(a, b, places=13)
        angle, scale, offset = 0.73, 2.5, (-31, 17)

        def transform(point):
            x, y = point
            return (
                offset[0] + scale * (x * math.cos(angle) - y * math.sin(angle)),
                offset[1] + scale * (x * math.sin(angle) + y * math.cos(angle)),
            )

        center, point = transform((0, 0)), transform((13, 0))
        transformed = circle_tangent_points(center, 5 * scale, point)
        for i, (actual, original) in enumerate(zip(transformed, contacts)):
            for a, b in zip(actual, transform(original)):
                self.assertAlmostEqual(a, b, places=12)
            cross = (point[0] - center[0]) * (actual[1] - center[1]) - (point[1] - center[1]) * (actual[0] - center[0])
            self.assertGreater(cross if i == 0 else -cross, 0)
        for scale in (1e-150, 1e-75, 1.0, 1e75, 1e150):
            center, radius, point = (3 * scale, -4 * scale), 2 * scale, (8 * scale, 8 * scale)
            for contact in circle_tangent_points(center, radius, point):
                self.assertTangency(center, radius, point, contact)
        self.assertEqual(circle_tangent_points((1, -2), 5, (4, 2)), ((4.0, 2.0),))
        outside = (math.nextafter(1.0, math.inf), 0)
        contacts = circle_tangent_points((0, 0), 1, outside)
        self.assertEqual(len(contacts), 2)
        self.assertGreater(contacts[0][1], 0)
        self.assertLess(contacts[1][1], 0)
        for contact in contacts:
            self.assertTangency((0, 0), 1, outside, contact)
        with self.assertRaises(ValueError):
            circle_tangent_points((0, 0), 1, (math.nextafter(1.0, 0.0), 0))
        for radius in (0, -1, math.nan, math.inf, -math.inf):
            with self.subTest(radius=radius), self.assertRaises(ValueError):
                circle_tangent_points((0, 0), radius, (3, 0))
        for point in ((0, 0), (0.5, 0.5)):
            with self.subTest(point=point), self.assertRaises(ValueError):
                circle_tangent_points((0, 0), 1, point)
        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    circle_tangent_points((value, 0), 1, (3, 0))
                with self.assertRaises(ValueError):
                    circle_tangent_points((0, 0), 1, (3, value))
        for center, point in [((-1e308, 0), (1e308, 0)), ((0, 0), (1.3e308, 1.3e308))]:
            with self.assertRaises(ValueError):
                circle_tangent_points(center, 1, point)
        contact = circle_tangent_points((0, 0), 5, (13, 0))[0]
        segment = path(f"M {contact[0]} {contact[1]} L 13 0").with_ports(contact=contact)
        self.assertEqual(segment.ports["contact"], contact)
        moved = segment.scaled(2).rotated(90, about=(0, 0)).moved(4, 7)
        for a, b in zip(moved.ports["contact"], (4 - 2 * contact[1], 7 + 2 * contact[0])):
            self.assertAlmostEqual(a, b, places=12)

    def test_help_is_on_demand_and_keeps_derivative_alias(self):
        from .. import svg_drawing as drawing

        name = "circle_tangent_points"
        self.assertIn(name, drawing.__all__)
        text = drawing.drawing_help(name)
        self.assertEqual(text, drawing.drawing_help("圆外切点"))
        self.assertEqual(text, drawing.drawing_help("圆切线"))
        self.assertEqual(drawing.drawing_help("切线"), drawing.drawing_help("derivatives"))
        for word in ("+90°", "圆上", "ValueError", "截面", "椭圆", "不自动选分支"):
            self.assertIn(word, text)
        self.assertNotIn(name, drawing.drawing_help())


class CurveCapabilitiesTest(unittest.TestCase):
    def test_live_ports_and_frames_follow_transforms(self):
        from ..svg_drawing import rect, PathFrame
        from ..svg_drawing import Drawing
        from ..svg_drawing import group, Box

        unit = 1 / math.sqrt(2)
        source = rect(20, 10, fill="red", stroke="black", stroke_width=2).with_ports(
            pivot=(10, 5), face=PathFrame((20, 5), (unit, -unit), (unit, unit), 0)
        )
        original = ET.tostring(source.element)
        result = source.stretched(2, 0.5, about=(10, 5))
        self.assertEqual(result.ports["pivot"], (10, 5))
        self.assertEqual(result.ports["face"], (30, 5))
        self.assertEqual(source.ports["face"], (20, 5))
        self.assertEqual(ET.tostring(source.element), original)
        self.assertEqual(result.element[0].get("stroke-width"), "2")
        tangent = result.port_tangents["face"]
        normal = result.port_directions["face"]
        self.assertAlmostEqual(sum(a * b for a, b in zip(tangent, normal)), 0)
        self.assertAlmostEqual(math.hypot(*tangent), 1)
        self.assertAlmostEqual(math.hypot(*normal), 1)
        matrix = parse_transform(result.element.get("transform"))
        self.assertEqual(matrix.point(20, 5), result.ports["face"])
        for factors in ((0, 1), (-1, 1), (1, math.inf), (math.nan, 1)):
            with self.subTest(factors=factors), self.assertRaises(ValueError):
                source.stretched(*factors)
        d = Drawing(500, 400)
        node = d.add("part", rect(100, 60), at=(100, 100))
        port = node.contour_at(0.125, normal="outward")
        label = d.add("label", rect(10, 10), at=port, own_anchor="center")
        self.assertPoint(d.resolve(port), (140, 100))
        node.set_transform(rotation=90, scale=2)
        self.assertPoint(d.resolve(port), (100, 180))
        self.assertPoint(d.resolve_frame(port).normal, (1, 0))
        self.assertPoint(d.resolve(label.anchor()), (100, 180))
        target = d.add("target", rect(10, 10), at=(400, 200))
        hit = node.contour_toward(target.anchor())
        a = d.resolve(hit)
        target.move_to(200, 350)
        b = d.resolve(hit)
        self.assertNotEqual(a, b)
        node.set_geometry(rect(50, 50))
        self.assertNotEqual(d.resolve(port), (100, 180))
        part = rect(100, 60)
        frame = part.contour().frame(40, normal="outward")
        part = part.with_ports(p=frame)
        d = Drawing(500, 400)
        node = d.add("p", part.rotated(90, about=(0, 0)).scaled(2))
        result = d.resolve_frame(node.port("p"))
        self.assertPoint(result.point, (0, 80))
        self.assertPoint(result.normal, (1, 0))
        self.assertPoint(result.tangent, (0, 1))
        repeated = repeat_along_path(part, "M 0 0 L 100 0", count=2)
        self.assertIn("item_0.p", repeated.port_directions)
        self.assertIn("part_0.p", group(part).port_directions)
        self.assertIn("p", cutaway(part, Box(0, 0, 100, 60)).port_directions)
        self.assertNotIn("p", part.with_ports(p=(4, 5)).port_directions)

    def assertPoint(self, actual, expected, places=6):
        for a, b in zip(actual, expected):
            self.assertAlmostEqual(a, b, places=places)

    def test_curve_interpolation_trim_rays_and_parametric_ellipses(self):
        from ..svg_drawing import rect, path

        points = [(0, 0), (30, 50), (150, 20), (180, 80)]
        curve = smooth_curve(points)
        commands = list(path_segments(curve.d))
        cubics = [v for op, v in commands if op == "C"]
        self.assertEqual([tuple(commands[0][1])] + [tuple(v[-2:]) for v in cubics], points)
        for i in range(len(cubics) - 1):
            p = points[i + 1]
            a = (p[0] - cubics[i][-4], p[1] - cubics[i][-3])
            b = (cubics[i + 1][0] - p[0], cubics[i + 1][1] - p[1])
            self.assertAlmostEqual(a[0] * b[1] - a[1] * b[0], 0, places=5)
        c = smooth_curve(points, start_direction=(0, 1), end_direction=(1, 0))
        values = [v for op, v in path_segments(c.d) if op == "C"]
        self.assertEqual(values[0][0], 0)
        self.assertEqual(values[-1][3], 80)
        pts = [(0, 0), (80, 0), (80, 60), (0, 60)]
        c = smooth_curve(pts, closed=True, tension=1)
        self.assertAlmostEqual(c.length, 280)
        self.assertTrue(c.samples()[1])
        self.assertEqual(c.frame(40, normal="outward").normal, (0, -1))
        for kw in [dict(tension=-1), dict(alpha=2), dict(closed=True, start_direction=(1, 0))]:
            with self.assertRaises(ValueError):
                smooth_curve(pts, **kw)
        with self.assertRaises(ValueError):
            smooth_curve([(0, 0), (0, 0)])
        crossed = smooth_curve([(0, 0), (100, 80), (0, 100), (80, 0)], closed=True, tension=1)
        with self.assertRaisesRegex(ValueError, "Self-intersecting"):
            crossed.frame(10, normal="outward")
        c = Curve("M 0 0 L 100 0 L 100 100")
        part = c.trim(25, 150)
        self.assertAlmostEqual(part.length, 125)
        self.assertPoint(part.at(0)[0], (25, 0))
        self.assertPoint(part.at(part.length)[0], (100, 50))
        ring = Curve("M 0 0 L 100 0 L 100 100 L 0 100 Z")
        self.assertAlmostEqual(ring.trim(350, 50, wrap=True).length, 100)
        self.assertAlmostEqual(ring.trim(50, 50, wrap=True).length, 400)
        self.assertAlmostEqual(ring.trim(400, 0, wrap=True).length, 400)
        with self.assertRaises(ValueError):
            c.trim(150, 25)
        with self.assertRaises(ValueError):
            c.trim(0, 100, wrap=True)
        c = rect(100, 60).contour()
        self.assertPoint(c.ray((50, 30), (1, 0), normal="outward").point, (100, 30))
        self.assertPoint(c.ray((50, 30), (1, 0), normal="outward").normal, (1, 0))
        self.assertPoint(c.ray((-20, 30), (1, 0), hit="nearest").point, (0, 30))
        self.assertPoint(c.ray((-20, 30), (1, 0), hit="farthest").point, (100, 30))
        self.assertPoint(c.ray((30, 0), (1, 0), hit="nearest").point, (30, 0))
        with self.assertRaises(ValueError):
            c.ray((-10, -10), (-1, 0))
        multi = path("M 0 0 L 10 0 M 20 0 L 40 0")
        self.assertAlmostEqual(multi.contour(1).length, 20)
        with self.assertRaises(ValueError):
            multi.contour(2)
        sample = sample_parametric(
            lambda t: (50 * math.cos(t), 30 * math.sin(t)), (0, 2 * math.pi), closed=True, tolerance=0.05
        )
        self.assertEqual(len(sample.segments), 1)
        self.assertTrue(sample.closed)
        self.assertEqual(sample.segments[0][0], sample.segments[0][-1])
        self.assertTrue(sample.to_geometry().element.get("d").endswith("Z"))
        self.assertTrue(sample.curves()[0].samples()[1])
        for a, b in zip(sample.segments[0], sample.segments[0][1:]):
            x, y = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
            t = math.atan2(y / 30, x / 50)
            self.assertLess(math.dist((x, y), (50 * math.cos(t), 30 * math.sin(t))), 0.051)
        with self.assertRaises(ValueError):
            sample_parametric(lambda t: (t, t), (0, 1), closed=True)
        with self.assertRaises(TypeError):
            sample_parametric(lambda t: 10, (0, 1))
        with self.assertRaisesRegex(ValueError, "max_points"):
            sample_parametric(lambda t: (math.cos(t), math.sin(t)), (0, 6), max_points=5, max_step=6, tolerance=1e-6)
        s = sample_parametric(lambda t: (t, 1 / t), (-1, 1), breaks=(0,), tolerance=0.1)
        self.assertGreaterEqual(len(s.segments), 2)
        for segment in s.segments:
            self.assertFalse(segment[0][0] < 0 < segment[-1][0])
        with self.assertRaises(ValueError):
            sample_parametric(lambda t: (t, t), (-1, 1), breaks=(0,), closed=True)


class RoutingDiagnosticsTest(SvgTestCase):
    canvas = (500, 300)

    def path_of(self, drawing, key):
        return next(e for e in ET.fromstring(drawing.to_svg()) if e.get("id") == key).get("d")

    def test_routes_waypoints_beziers_orthogonal_and_invalid_requests(self):
        from ..svg_drawing import Drawing, rect

        d = Drawing(500, 300)
        a = d.add("a", rect(40, 40), at=(20, 100))
        b = d.add("b", rect(40, 40), at=(420, 100))
        w = d.add("waypoint", rect(10, 10), at=(200, 20))
        d.connect(
            "wire",
            a.anchor("right"),
            b.anchor("left"),
            route="polyline",
            start_direction="normal",
            end_direction="normal",
            lead=20,
            waypoints=[w.anchor()],
        )
        commands = list(path_segments(self.path_of(d, "wire")))
        points = [tuple(v) for _, v in commands]
        self.assertEqual(points[:2], [(60, 120), (80, 120)])
        self.assertIn((205, 25), points)
        self.assertEqual(points[-2:], [(400, 120), (420, 120)])
        w.move_to(220, 40)
        self.assertIn((225, 45), [tuple(v) for _, v in path_segments(self.path_of(d, "wire"))])
        d = Drawing(500, 300)
        a = d.add("a", rect(40, 40).with_ports(out=rect(40, 40).contour().frame(20, normal="outward")), at=(60, 150))
        a.set_transform(rotation=90)
        b = d.add("b", rect(40, 40), at=(400, 150))
        d.connect(
            "wire",
            a.port("out"),
            b.anchor("left"),
            route="bezier",
            start_direction="normal",
            end_direction="normal",
            waypoints=[(240, 70)],
            stroke="#336699",
            stroke_linecap="round",
        )
        commands = list(path_segments(self.path_of(d, "wire")))
        first = commands[1][1]
        last = commands[-1][1]
        self.assertGreater(first[0], commands[0][1][0])
        self.assertEqual(first[1], commands[0][1][1])
        self.assertEqual(tuple(first[-2:]), (240, 70))
        self.assertLess(last[2], last[4])
        self.assertEqual(last[3], last[5])
        data = self.atomize_body(document=d.to_svg())
        self.assertIn(" C ", data)
        self.assertNotIn("curved-connector3", data)
        d = Drawing(500, 300)
        ob = d.add("ob", rect(100, 100), at=(200, 70))
        d.connect("wire", (20, 120), (470, 120), route="orthogonal", avoid=[ob], clearance=10)
        first = self.path_of(d, "wire")
        points = [tuple(v) for _, v in path_segments(first)]
        self.assertGreater(len(points), 2)
        for a, b in zip(points, points[1:]):
            self.assertTrue(a[0] == b[0] or a[1] == b[1])
            for i in range(101):
                x, y = (a[k] + (b[k] - a[k]) * i / 100 for k in (0, 1))
                self.assertFalse(190 < x < 310 and 60 < y < 180)
        ob.move_to(200, 210)
        self.assertEqual(self.path_of(d, "wire"), "M 20 120 L 470 120")
        d = Drawing(500, 300)
        for kw in [
            dict(route="straight", waypoints=[(2, 3)]),
            dict(route="bezier", avoid=[Box(0, 0, 20, 20)]),
            dict(route="orthogonal", clearance=-1),
            dict(route="polyline", start_direction=(0, 0)),
            dict(route="orthogonal", avoid=[Box(1, 1, 1, 1)] * 33),
        ]:
            with self.assertRaises(ValueError):
                d.connect("bad", (0, 0), (100, 100), **kw)
        self.assertFalse(d.items)
        d.connect("blocked", (0, 0), (100, 100), route="orthogonal", waypoints=[(50, 50)], avoid=[Box(40, 40, 20, 20)])
        with self.assertRaisesRegex(ValueError, "inside"):
            d.to_svg()

    def test_inspection_reports_order_ports_overlap_and_failed_bindings(self):
        from ..svg_drawing import Drawing, rect

        d = Drawing(500, 300)
        g = rect(50, 50)
        a = d.add("a", g.with_ports(out=g.contour().frame(25, normal="outward")), at=(10, 10))
        d.add("b", rect(50, 50), at=(30, 30))
        d.add("far", rect(20, 20), at=(400, 200))
        with patch("pathlib.Path.write_text", side_effect=AssertionError("unexpected write")):
            report = d.inspect("a", "b", overlaps=True)
        self.assertEqual([r["key"] for r in report["objects"]], ["a", "b"])
        self.assertEqual([r["z_index"] for r in report["objects"]], [0, 1])
        self.assertEqual(report["objects"][0]["ports"]["out"]["point"], (35, 10))
        self.assertEqual(report["objects"][0]["ports"]["out"]["normal"], (0, -1))
        self.assertEqual(report["overlaps"][0]["bbox_overlap_area"], 900)
        json.dumps(report)
        self.assertNotIn("ports", d.inspect()["objects"][0])
        a.move_to(50, 10)
        self.assertEqual(d.inspect("a")["objects"][0]["ports"]["out"]["point"], (75, 10))
        d = Drawing(500, 300)
        a = d.add("a", rect(20, 20))
        b = d.add("b", rect(20, 20))
        d.add("ok", rect(20, 20), at=(100, 100))
        a.pin(b.anchor())
        b.pin(a.anchor())
        report = d.inspect("a", "ok")
        self.assertIn("Cyclic", report["errors"][0]["message"])
        self.assertEqual(report["objects"][1]["layout_bounds"], [100, 100, 20, 20])
        with self.assertRaises(KeyError):
            d.inspect("missing")

    def test_conversion_diagnostics_ids_and_unknown_bounds(self):
        with tempfile.TemporaryDirectory() as tmp:
            svg = Path(tmp) / "test.svg"
            svg.write_text(
                '<svg viewBox="0 0 500 300"><g id="body"><rect id="r" x="20" y="20" width="30" height="40" fill="red"/></g><circle id="other" cx="100" cy="100" r="20"/></svg>'
            )
            plain = atomize_svg_to_slide(svg)
            report = {}
            observed = atomize_svg_to_slide(svg, diagnostics=report)
            self.assertEqual(plain, observed)
            selected = inspect_svg(svg, object_ids=["body", "missing"])
            self.assertEqual(len(selected["objects"]), 1)
            self.assertEqual(selected["unmatched_ids"], ["missing"])
            self.assertEqual(selected["objects"][0]["source_ids"], ["body", "r"])
            self.assertEqual(selected["objects"][0]["decision"], "native")
            self.assertEqual(selected["objects"][0]["outputs"][0]["selection_bounds"], [20, 20, 30, 40])
            svg.write_text(
                '<svg viewBox="0 0 500 300"><defs><rect id="unit" width="20" height="20"/></defs><use id="instance" href="#unit" x="10" y="30"/></svg>'
            )
            selected = inspect_svg(svg, object_ids=["instance"])
            self.assertEqual(selected["unmatched_ids"], [])
            self.assertEqual(selected["objects"][0]["outputs"][0]["selection_bounds"], [10, 30, 20, 20])
        with tempfile.TemporaryDirectory() as tmp:
            svg = Path(tmp) / "test.svg"
            svg.write_text(
                '<svg viewBox="0 0 500 300"><defs><radialGradient id="g"><stop offset="0" stop-color="red"/></radialGradient></defs><text id="label" x="30" y="50" fill="url(#g)">Unknown font metrics</text><rect id="whole" width="500" height="300" fill="url(#g)"/></svg>'
            )
            with patch.object(_font_metrics, "measure_text", return_value=None):
                report = inspect_svg(svg)
            label = next(r for r in report["objects"] if "label" in r["source_ids"])
            whole = next(r for r in report["objects"] if "whole" in r["source_ids"])
            self.assertTrue(label["source_viewport_fallback"])
            self.assertEqual(label["bounds_evidence"]["reason"], "font_metrics_unavailable")
            self.assertFalse(whole["source_viewport_fallback"])
            self.assertEqual(whole["decision"], "svg")

    def test_group_and_affine_preservation_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            svg = Path(tmp) / "test.svg"
            for attribute in ('opacity="0.5"', 'style="opacity:0.5"', 'filter="url(#blur)"'):
                with self.subTest(attribute=attribute):
                    svg.write_text(
                        '<svg viewBox="0 0 500 300"><defs><filter id="blur"><feGaussianBlur stdDeviation="2"/></filter></defs>'
                        f'<g id="veil" {attribute}><rect x="20" y="20" width="80" height="60"/>'
                        '<rect x="60" y="40" width="80" height="60" fill="blue"/></g></svg>'
                    )
                    plain = atomize_svg_to_slide(svg)
                    report = {}
                    self.assertEqual(plain, atomize_svg_to_slide(svg, diagnostics=report))
                    item = report["objects"][0]
                    self.assertEqual(item["decision"], "svg")
                    self.assertEqual(item["reason_category"], "fidelity_preservation")
                    self.assertIn("已转换", item["reason_note"])
                    trigger = item["compositing_triggers"][0]
                    self.assertEqual(trigger["source_id"], "veil")
                    if "opacity" in attribute:
                        self.assertEqual(trigger["attributes"], {"opacity": "0.5"})
                        self.assertIn("group_opacity", item["features"])
                    else:
                        self.assertEqual(trigger["attributes"], {"filter": "url(#blur)"})
            svg.write_text('<svg viewBox="0 0 500 300"><g opacity="1"><rect width="20" height="20"/></g></svg>')
            self.assertNotIn("reason_category", inspect_svg(svg)["objects"][0])
        with tempfile.TemporaryDirectory() as tmp:
            svg = Path(tmp) / "test.svg"
            svg.write_text(
                '<svg viewBox="0 0 500 300"><g id="scene" transform="scale(2 .5)">'
                '<rect id="a" x="10" y="20" width="20" height="30"/>'
                '<circle id="b" cx="90" cy="50" r="10"/></g></svg>'
            )
            plain = atomize_svg_to_slide(svg)
            report = {}
            self.assertEqual(plain, atomize_svg_to_slide(svg, diagnostics=report))
            items = inspect_svg(svg, object_ids=["scene"])["objects"]
            self.assertEqual([item["source_ids"] for item in items], [["scene", "a"], ["scene", "b"]])
            self.assertTrue(all(item["decision"] == "svg" for item in items))
            self.assertTrue(all(item["reason_category"] == "fidelity_preservation" for item in items))
            self.assertTrue(all(not item["source_viewport_fallback"] for item in items))

    def test_multi_cubic_round_cap_preserves_every_curve(self):
        xml = self.atomize_body(
            '<path d="M 20 20 C 0 40 60 50 30 70 C 0 100 70 120 40 150" fill="none" stroke="#336699" stroke-width="6" stroke-linecap="round"/>'
        )
        self.assertNotIn("curved-connector", xml)
        self.assertEqual(xml.count(" C "), 2)


class TextLayoutHelpersTest(SvgTestCase):
    def test_wrapping_and_label_candidates(self):
        from ..svg_drawing import Drawing, rect, Box

        text = "Protein binding changes activity\n受体结合后发生磷酸化"
        result = wrap_label(text, max_width=110, font_size=16)
        self.assertLessEqual(result.bounds.width, 110.000001)
        visible = "".join(result.element.itertext())
        self.assertEqual("".join(visible.split()), "".join(text.split()))
        self.assertGreater(len(list(result.element)), 2)
        result = wrap_label("a\u0301b\u0301c\u0301d\u0301", max_width=30, font_size=16)
        self.assertTrue(all(child.get("font-size") == "16" for child in result.element))
        for child in result.element:
            self.assertFalse((child.text or "").startswith("\u0301"))
        with self.assertRaises(ValueError):
            wrap_label("toolongword", max_width=30, font_size=16, break_long_words=False)
        with self.assertRaises(ValueError):
            wrap_label("大", max_width=1, font_size=16)
        d = Drawing(500, 300)
        body = d.add("body", rect(40, 40), at=(80, 80))
        before = d.to_svg()
        candidates = d.label_candidates(rect(40, 20), body.anchor(), avoid=[Box(105, 70, 100, 60)])
        self.assertEqual(len(candidates), 8)
        self.assertEqual(candidates[0]["score"], 0)
        right = next(c for c in candidates if c["side"] == "right")
        self.assertGreater(right["overlap_area"], 0)
        self.assertEqual(d.to_svg(), before)
        choice = candidates[0]
        note = d.add("note", rect(40, 20), at=body.anchor().shifted(*choice["offset"]), own_anchor="top_left")
        self.assertEqual((note.bounds.x, note.bounds.y), choice["at"])
        body.move_to(100, 80)
        self.assertEqual(note.bounds.x, choice["at"][0] + 20)


class NativeTextLayoutTest(SvgTestCase):
    canvas = (960, 540)

    def test_authored_ellipsis_and_mathematical_continuation_remain_native_text(self):
        self.assertEqual(_CFG["ellipsis_policy"], "preserve")
        for source, expected in (
            ("慢一点……线搭上了。", "慢一点……线搭上了。"),
            ("1 + 2 + ⋯ + n", "1 + 2 + ⋯ + n"),
            ("等待&#x2026;&#x2026;完成", "等待……完成"),
        ):
            with self.subTest(source=source):
                data = self.convert(f'<text x="60" y="90" font-size="18">{source}</text>')
                self.assertEqual(len(data), 1)
                self.assertEqual(data[0].get("type"), "text")
                self.assertEqual("".join(data[0].find("{*}content").itertext()), expected)

    def test_native_text_ellipsis_rich_runs_and_fallback_measurement(self):
        data = self.convert(
            '<text x="60" y="90" font-size="18">慢一点'
            '<tspan fill="#b34230" font-weight="bold">……</tspan>线搭上了。</text>'
        )
        self.assertEqual(data[0].get("type"), "text")
        content = data[0].find("{*}content")
        self.assertEqual("".join(content.itertext()), "慢一点……线搭上了。")
        run = next(span for span in content.findall(".//{*}span") if span.text == "……")
        self.assertEqual(run.get("bold"), "true")
        self.assertEqual(run.get("color"), "rgb(179,66,48)")
        for attr in (
            'dominant-baseline="hanging"',
            'dominant-baseline="ideographic"',
            'alignment-baseline="text-top"',
            'baseline-shift="super"',
            'writing-mode="vertical-rl"',
            'direction="rtl"',
            'x="10 20"',
        ):
            xy = "" if attr.startswith("x=") else 'x="10" '
            body = f'<text {xy}y="30" font-size="20" {attr}>ABC</text>'
            with self.subTest(attr=attr):
                self.assertTrue(self.convert(body)[0].tag.endswith("}embed"))
                self.assertEqual(ET.fromstring(convert_text(body)).tag, "embed")
        self.assertGreater(
            text_advance("WWWW", "Missing", 20, metrics="legacy"),
            text_advance("iiii", "Missing", 20, metrics="legacy") * 2,
        )
        self.assertEqual(
            text_advance("e\u0301", "Missing", 20, letter_spacing=4, metrics="legacy"),
            text_advance("e", "Missing", 20, metrics="legacy"),
        )
        self.assertGreater(
            text_advance("MW12", "Missing", 20, "700", metrics="legacy"),
            text_advance("MW12", "Missing", 20, metrics="legacy"),
        )
        self.assertEqual(text_advance("文字", "Missing", 20, "bold", metrics="legacy"), 40)
        self.assertAlmostEqual(estimate_advance("—— 李白", 12), 51.96)
        self.assertGreater(estimate_advance("—— 李白", 12), 46)
        # Ambiguous-width punctuation is wide in the CJK credit, while a Latin
        # year range retains the existing proportional punctuation estimate.
        self.assertAlmostEqual(estimate_advance("2020–2023", 12), 64.32)
        self.assertAlmostEqual(estimate_advance("中…文", 12), 36)
        e = self.convert('<text x="50" y="50" font-size="10.5">Measured label</text>')[0]
        self.assertEqual(e.find("{*}content").get("fontSize"), "10.5")
        e = ET.fromstring(convert_text('<text x="0" y="20" font-size="20" font-weight="600"> A  &#x2192;\n B </text>'))
        self.assertEqual(e.find("content/p").text, "A → B")
        self.assertEqual(e.find("content").get("bold"), "true")
        a = ET.fromstring(convert_text('<text x="0" y="20" font-size="20" letter-spacing=".1em">ABC</text>'))
        b = ET.fromstring(convert_text('<text x="0" y="20" font-size="20" letter-spacing="2">ABC</text>'))
        self.assertEqual(a.get("width"), b.get("width"))
        self.assertEqual(a.find("content").get("letterSpacing"), "2")
        _CFG["font_metrics"] = "legacy"
        e = self.convert('<text x="50" y="50" font-size="10">i</text>')[0]
        self.assertLess(float(e.get("width")), 10)
        self.assertEqual(e.find("{*}content").get("fontSize"), "10")

    def test_missing_policy_preserves_text_and_explicit_legacy_guard_still_fails(self):
        _CFG.pop("ellipsis_policy", None)
        self.assertEqual("".join(self.convert('<text x="30" y="80">甲…乙</text>')[0].itertext()), "甲…乙")
        _CFG["ellipsis_policy"] = "fail"
        with self.assertRaisesRegex(ValueError, "explicit ellipsis_policy"):
            self.convert('<text x="30" y="80">甲…乙</text>')

    def test_baselines_have_distinct_font_metric_offsets(self):
        metric = TextMetrics(30, 0, -14, 30, 4, "fixture", 16, 4, 10)
        centers = {}
        with patch.object(_font_metrics, "measure_text", return_value=metric):
            for baseline in ("alphabetic", "central", "middle"):
                e = self.convert(
                    f'<text x="100" y="100" font-size="20" text-anchor="middle" dominant-baseline="{baseline}">Ag</text>'
                )[0]
                self.assertEqual(e.get("type"), "text")
                self.assertAlmostEqual(float(e.get("topLeftX")) + float(e.get("width")) / 2, 100)
                centers[baseline] = float(e.get("topLeftY")) + float(e.get("height")) / 2
        self.assertAlmostEqual(centers["alphabetic"], 93)
        self.assertAlmostEqual(centers["central"] - centers["alphabetic"], 6)
        self.assertAlmostEqual(centers["middle"] - centers["alphabetic"], 5)

    def test_centered_text_fallback_keeps_anchor_after_font_clamp(self):
        with patch.object(_font_metrics, "measure_text", return_value=None):
            for anchor in ("start", "middle", "end"):
                e = self.convert(
                    f'<text x="100" y="80" font-size="8" text-anchor="{anchor}" dominant-baseline="central">A</text>'
                )[0]
                x, y, w, h = [float(e.get(k)) for k in ("topLeftX", "topLeftY", "width", "height")]
                self.assertAlmostEqual(x + ({"start": 0, "middle": 0.5, "end": 1}[anchor]) * w, 100)
                self.assertAlmostEqual(y + h / 2, 80)
                self.assertEqual(e.find("{*}content").get("fontSize"), "10")

    def test_baseline_styles_inherit_through_groups(self):
        body = '<g style="dominant-baseline:central;font-size:20;writing-mode:horizontal-tb"><text x="60" y="80" text-anchor="middle">A</text></g>'
        with patch.object(_font_metrics, "measure_text", return_value=None):
            e = self.convert(body)[0]
        self.assertEqual(e.get("type"), "text")
        self.assertAlmostEqual(float(e.get("topLeftY")) + float(e.get("height")) / 2, 80)

    def test_centered_anchor_survives_rotation_and_scaling(self):
        body = '<g transform="translate(20 30) rotate(90) scale(2)"><text x="10" y="20" font-size="20" text-anchor="middle" dominant-baseline="central">Ag</text></g>'
        with patch.object(_font_metrics, "measure_text", return_value=None):
            e = self.convert(body)[0]
        self.assertEqual(e.get("type"), "text")
        self.assertEqual(e.get("rotation"), "90")
        self.assertAlmostEqual(float(e.get("topLeftX")) + float(e.get("width")) / 2, -20)
        self.assertAlmostEqual(float(e.get("topLeftY")) + float(e.get("height")) / 2, 50)
        self.assertEqual(e.find("{*}content").get("fontSize"), "40")

    def test_explicit_positioned_lines_keep_center_baseline(self):
        body = '<text dominant-baseline="central" font-size="20"><tspan x="50" y="60">A</tspan><tspan x="50" y="90">B</tspan></text>'
        with patch.object(_font_metrics, "measure_text", return_value=None):
            data = self.convert(body)
        self.assertEqual(len(data), 2)
        self.assertEqual([float(e.get("topLeftY")) + float(e.get("height")) / 2 for e in data], [60, 90])

    def test_width_includes_actual_subtitle_letter_spacing(self):
        body = '<text x="100" y="50" font-size="10" fill="#888888" text-anchor="end">ABCDEF</text>'
        _CFG["font_metrics"] = "legacy"
        set_subtitle_relax(svg_threshold=12, min_slide_font=8, letter_spacing=0)
        a = self.convert(body)[0]
        set_subtitle_relax(svg_threshold=12, min_slide_font=8, letter_spacing=2)
        b = self.convert(body)[0]
        self.assertAlmostEqual(float(b.get("width")) - float(a.get("width")), 10, places=1)
        self.assertAlmostEqual(float(b.get("topLeftX")) + float(b.get("width")), 100)
        self.assertEqual(b.find("{*}content").get("letterSpacing"), "2")
        self.assertEqual(b.find("{*}content").get("autoFit"), "no-auto-fit")
        self.assertEqual(b.find("{*}content").get("fontSize"), a.find("{*}content").get("fontSize"))

    def test_explicit_spacing_overrides_subtitle_spacing_after_scaling(self):
        _CFG["font_metrics"] = "legacy"
        set_mapping(960, 540, 0, 0, 480, 270)
        set_subtitle_relax(svg_threshold=30, min_slide_font=8, letter_spacing=3)
        plain = '<text x="50" y="50" font-size="20" fill="#888888" letter-spacing="{}">ABCD</text>'
        a = self.convert(plain.format(0))[0]
        b = self.convert(plain.format(4))[0]
        self.assertEqual(b.find("{*}content").get("letterSpacing"), "2")
        self.assertAlmostEqual(float(b.get("width")) - float(a.get("width")), 6, places=1)

    def test_rich_text_legacy_mode_does_not_probe_fonts(self):
        _CFG["font_metrics"] = "legacy"
        with patch.object(_font_metrics, "measure_text", side_effect=AssertionError("legacy must not probe fonts")):
            e = self.convert(
                '<text x="50" y="80" font-size="20" font-family="Arial" dominant-baseline="central">A<tspan fill="red">B</tspan></text>'
            )[0]
        self.assertEqual(e.get("type"), "text")
        self.assertEqual(len(e.findall(".//{*}span")), 2)
        self.assertAlmostEqual(float(e.get("topLeftY")) + float(e.get("height")) / 2, 80)

    def test_fontconfig_substitution_is_not_claimed_as_exact_metrics(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "font.ttf"
            file.write_bytes(b"placeholder")
            resolve_font.cache_clear()
            self.addCleanup(resolve_font.cache_clear)
            result = SimpleNamespace(stdout=f"{file}\n0\nVerdana")
            with (
                patch.object(_font_metrics.shutil, "which", return_value="/fontconfig"),
                patch.object(_font_metrics.subprocess, "run", return_value=result),
            ):
                self.assertIsNone(resolve_font("Unavailable Chinese Font"))
                self.assertEqual(resolve_font("Verdana"), (str(file), 0))
                self.assertEqual(resolve_font("sans-serif"), (str(file), 0))
