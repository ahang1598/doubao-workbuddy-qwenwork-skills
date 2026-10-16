"""Matrix, network, phylogeny, ternary and UpSet charts."""

import json
import math
import sys
import unittest
import xml.etree.ElementTree as ET
import itertools
import random
from pathlib import Path
from fractions import Fraction

import pytest

SCRIPTS = Path(__file__).resolve().parents[2]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import embed_svg_validator
from embed_svg_validator import detect_embedded_svg_overlaps, validate_embedded_svgs

from ._helpers import _text_boxes, nodes as elements
from ..charts._matrix_core import render_matrix, text_svg
from ..charts.clustered_heatmap import _euclid, make_clustered_heatmap
from ..charts.dot_plot_scrna import make_dot_matrix, make_dot_plot_scrna
from ..charts.matrix_heat import draw_matrix_heat, make_matrix_heat
from ..charts._chart_layout import ChartLayout, number_label
from ..charts._network_core import fit_positions, force_positions, node_radii, normalize_network
from ..charts._phylo_core import normalize_tree
from ..charts.network import make_network, render_network_plot
from ..charts.phylogeny import make_phylogeny, render_phylogeny_plot
from ..charts.ternary import (
    _ALTITUDE,
    _barycentric,
    _composition,
    _contour_segments,
    _density_mesh,
    _mesh,
    _precomputed_mesh,
    _size_references,
    make_ternary,
)
from ..charts.upset import _inclusive_atom_witness, _inclusive_lp_witness, _prepare_upset, make_upset
import re
import subprocess
import tempfile
from .._common import _resolve_palette, _rgb_tuple
from ..charts._matrix_core import ColorScale, number_labels, numeric_tick_layout, prepare_tracks
from ..charts._matrix_math import stable_fraction, stable_lerp
from ..charts.clustered_heatmap import _apply_user_order, _hcluster


# ====================================================================================================
# Semantic regressions for missing values, layering, scales and clustering.
# ====================================================================================================

NS = {"s": "http://www.w3.org/2000/svg"}


def root(svg):
    return ET.fromstring(svg)


def cell(svg, r, c):
    return root(svg).find(f'.//s:g[@data-row="{r}"][@data-col="{c}"]', NS)


def all_text(svg):
    return "".join(root(svg).itertext())


def meta(svg):
    return json.loads(root(svg).get("data-matrix-layout"))


class MatrixContracts(unittest.TestCase):
    def test_matrix_text_observations_variants_and_invalid_inputs(self):
        from embed_svg_validator import validate_embedded_svgs

        lines = ["Line one", "Line two", "Line three"]
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">'
            + text_svg(90, 30, lines, 12, "#123456", "Inter, sans-serif", "end", 600, True)
            + "</svg>"
        )
        labels = root(svg).findall("s:text", NS)
        self.assertEqual([node.text for node in labels], lines)
        self.assertEqual([float(node.get("y")) for node in labels], [30, 45.6, 61.2])
        self.assertTrue(all(node.get("font-style") == "italic" and node.get("text-anchor") == "end" for node in labels))
        slide = ET.fromstring(f"<slide><embed>{svg}</embed></slide>")
        self.assertEqual(validate_embedded_svgs(slide), [])
        self.assertEqual(detect_embedded_svg_overlaps(slide), [])
        rotated = root(
            "<svg>" + text_svg(120.126, 25.006, ["A&B", "C<10"], 10.284, "#123456", "Inter", rotate=-90) + "</svg>"
        )
        self.assertEqual([n.text for n in rotated], ["A&B", "C<10"])
        self.assertEqual({n.get("transform") for n in rotated}, {"rotate(-90 120.13 25.01)"})
        self.assertEqual([n.get("y") for n in rotated], ["25.01", "38.38"])
        for variant in [None, "square_flat_full", "circle_full", "ellipse_upper", "pie_full", "annotated_number"]:
            svg = make_matrix_heat([[-1, 0.5], [0.2, 1]], labels=["A", "B"], variant=variant)
            self.assertEqual(cell(svg, 0, 0).get("data-value"), "-1.0")
            self.assertTrue(any(n.tag.endswith(("rect", "circle", "ellipse", "path")) for n in cell(svg, 0, 0)))
        svg = make_matrix_heat(
            [[None, math.nan], [-1, 99]], labels=["A", "B"], mask=[[False, False], [False, True]], vmin=-1, vmax=1
        )
        for i, j in [(0, 0), (0, 1), (1, 1)]:
            self.assertEqual(cell(svg, i, j).get("data-value"), "missing")
        self.assertEqual(cell(svg, 1, 0).get("data-value"), "-1.0")
        with self.assertRaises(ValueError):
            make_matrix_heat([[None]])
        self.assertEqual(cell(make_matrix_heat([[None]], vmin=0, vmax=1), 0, 0).get("data-value"), "missing")
        for variant in ["square_flat_full", "circle_full", "ellipse_upper", "pie_full", "annotated_number"]:
            svg = make_matrix_heat(
                [[1, 2, 3], [4, 5, 6]],
                row_labels=["row A", "row B"],
                col_labels=["x", "y", "z"],
                variant=variant,
                width=970,
                height=610,
                title="Title",
                note="A note",
                colorbar_label="Observed",
                show_row_mean=False,
                show_col_mean=False,
            )
            self.assertEqual(root(svg).get("viewBox"), "0 0 970 610")
            for text in ["row A", "row B", "Title", "A note", "Observed"]:
                self.assertIn(text, all_text(svg))
        svg = draw_matrix_heat(
            {
                "matrix": [[-1, 1]],
                "row_labels": ["R"],
                "col_labels": ["X", "Y"],
                "vmin": -2,
                "vmax": 2,
                "cell_text": [["low", "high"]],
            },
            width=960,
            height=540,
        )
        self.assertIn("low", all_text(svg))
        self.assertIn("high", all_text(svg))
        svg = make_matrix_heat(
            [[0.3, 0.7]],
            row_labels=["R"],
            col_labels=["X", "Y"],
            cell_text=[["A & B", ""]],
            pvalues=[[0.0001, 0.2]],
            show_row_mean=False,
            show_col_mean=False,
        )
        self.assertIn("A & B***", "".join(cell(svg, 0, 0).itertext()))
        self.assertNotIn("*", "".join(cell(svg, 0, 1).itertext()))
        cases = [
            {"matrix": [[1, 2], [3]]},
            {"matrix": [[math.inf]]},
            {"matrix": [[1]], "pvalues": [[1.1]]},
            {"matrix": [[1]], "mask": [[1]]},
            {"matrix": [[1]], "vmin": 2, "vmax": 1},
            {"matrix": [[1]], "midpoint": 7},
            {"matrix": [[1]], "variant": "typo"},
        ]
        for data in cases:
            with self.subTest(data=data), self.assertRaises(ValueError):
                make_matrix_heat(**data)
        with self.assertRaisesRegex(ValueError, "Canvas"):
            make_matrix_heat([[1, 2], [3, 4]], labels=["Long label " * 20] * 2, width=250, height=200)
        with self.assertRaisesRegex(ValueError, "Means"):
            make_matrix_heat([[1, 2], [3, 4]], upper_matrix=[[1, 3], [2, 4]], show_row_mean=True)
        with self.assertRaises(ValueError):
            make_matrix_heat([[1]], multi_mode="with_selected_comparison")
        with self.assertRaises(ValueError):
            make_clustered_heatmap([[1]], ["A"], ["B"], variant="typo")
        with self.assertRaises(ValueError):
            make_dot_plot_scrna(["G"], ["A"], [[20]], [[1]], variant="typo")
        svg = make_matrix_heat([[1]], labels=['Quoted "name" & symbol'], cell_text=[['A "quote"']])
        slide = ET.Element("slide")
        ET.SubElement(slide, "embed").append(root(svg))
        self.assertEqual(validate_embedded_svgs(slide), [])
        self.assertEqual(meta(svg)["row_labels"], ['Quoted "name" & symbol'])

    def test_matrix_scales_areas_categories_and_overlays(self):
        svg = make_matrix_heat(
            [[1, 2], [3, 4]],
            labels=["A", "B"],
            upper_matrix=[[999, 80], [777, 999]],
            upper_scale={"vmin": 0, "vmax": 100, "label": "Upper abundance", "palette": "nightlab"},
            colorbar_label="Lower correlation",
        )
        self.assertEqual(cell(svg, 0, 1).get("data-value"), "80.0")
        self.assertEqual(cell(svg, 1, 0).get("data-value"), "3.0")
        self.assertIn("Upper abundance", all_text(svg))
        self.assertIn("Lower correlation", all_text(svg))
        svg = make_dot_matrix([[0, 1, 4]], [[2, 2, 2]], ["R"], ["A", "B", "C"], size_max=4)
        self.assertIsNone(cell(svg, 0, 0).find("s:circle", NS))
        a = float(cell(svg, 0, 1).find("s:circle", NS).get("r"))
        b = float(cell(svg, 0, 2).find("s:circle", NS).get("r"))
        self.assertAlmostEqual((b / a) ** 2, 4, places=3)
        svg = make_matrix_heat(
            [[1, 2]], size_matrix=[[1, 4]], variant="square_flat_full", show_row_mean=False, show_col_mean=False
        )
        a = float(cell(svg, 0, 0).find("s:rect", NS).get("width"))
        b = float(cell(svg, 0, 1).find("s:rect", NS).get("width"))
        self.assertAlmostEqual((b / a) ** 2, 4, places=3)
        svg = make_dot_plot_scrna(
            ["G"], ["A", "B"], [[20, 40]], [[1, 2]], cluster_annotation=[("control", "#123456"), ("case", "#abcdef")]
        )
        self.assertIn("#123456", svg)
        self.assertIn("#abcdef", svg)
        with self.assertRaises(ValueError):
            make_dot_plot_scrna(["G"], ["A"], [[101]], [[2]])
        svg = make_matrix_heat(
            [["TP53", "Pathogenic", -1], ["EGFR", "Benign", 2]],
            row_labels=["Case 1", "Case 2"],
            columns=[
                {"name": "Gene", "type": "text"},
                {
                    "name": "Classification",
                    "type": "category",
                    "colors": {"Pathogenic": "#9F3333", "Benign": "#4B886F"},
                },
                {"name": "Effect", "type": "number", "vmin": -2, "vmax": 2},
            ],
        )
        self.assertEqual(cell(svg, 0, 0).get("data-value"), "TP53")
        self.assertEqual(cell(svg, 0, 1).get("data-value"), "Pathogenic")
        self.assertIn('fill="#9F3333"', svg)
        self.assertNotIn("Row mean", all_text(svg))
        self.assertEqual(cell(svg, 0, 2).get("data-value"), "-1.0")
        svg = make_matrix_heat(
            [[1, 2], [3, 4]],
            labels=["A", "B"],
            upper_matrix=[[1, 5], [3, 4]],
            size_matrix=[[1, 100], [4, 4]],
            size_max=4,
            upper_scale={"size_max": 100, "size_label": "Upper count"},
            width=1200,
            height=1000,
        )
        lower = float(cell(svg, 1, 0).find("s:circle", NS).get("r"))
        upper = float(cell(svg, 0, 1).find("s:circle", NS).get("r"))
        self.assertAlmostEqual(lower, upper)
        self.assertIn("Upper count", all_text(svg))
        svg = make_dot_matrix(
            [[1, 3]],
            [["T cells", "B cells"]],
            ["R"],
            ["A", "B"],
            colormap={"T cells": "#aabbcc", "B cells": "#112233"},
            colorbar_label="Lineage",
        )
        self.assertEqual(cell(svg, 0, 0).get("data-value"), "T cells")
        self.assertEqual(cell(svg, 0, 1).find("s:circle", NS).get("fill"), "#112233")
        self.assertIn("Lineage", all_text(svg))
        with self.assertRaises(ValueError):
            make_dot_matrix([[1]], [["Unknown"]], ["R"], ["A"], colormap={"T cells": "#aabbcc"})
        contexts = []

        def overlay(ctx):
            contexts.append(ctx)
            return "".join(
                f'<circle data-overlay-col="{j}" cx="{x}" cy="200" r="2"/>' for j, x in enumerate(ctx.column_centers)
            )

        svg = render_matrix([[1, 2, 3], [4, 5, 6]], ["R1", "R2"], ["A", "B", "C"], _overlays=[overlay])
        context = contexts[0]
        self.assertEqual(context.matrix, ((1.0, 2.0, 3.0), (4.0, 5.0, 6.0)))
        self.assertEqual(context.color_domains, ((1.0, 6.0),))
        for j, x in enumerate(context.column_centers):
            point = root(svg).find(f'.//s:circle[@data-overlay-col="{j}"]', NS)
            self.assertAlmostEqual(float(point.get("cx")), meta(svg)["column_centers"][j])

    def test_clustering_reorders_tracks_and_respects_distances_and_linkage(self):
        svg = make_clustered_heatmap(
            [[1, 2], [3, 4]],
            ["R1", "R2"],
            ["C1", "C2"],
            row_dendrogram={"order": [1, 0]},
            col_dendrogram={"order": [1, 0]},
            cell_text=[["a", "b"], ["c", "d"]],
            row_annotation={"Group": ["I", "II"]},
            col_annotation={"Condition": ["X", "Y"]},
            multi_mode="single",
        )
        self.assertEqual(meta(svg)["row_order"], [1, 0])
        self.assertIn("d", "".join(cell(svg, 0, 0).itertext()))
        self.assertEqual(cell(svg, 0, 0).get("data-value"), "4.0")
        svg = make_clustered_heatmap(
            [[1, 2], [3, 4]],
            ["A", "B"],
            ["A", "B"],
            row_dendrogram={"order": [1, 0]},
            col_dendrogram={"order": [1, 0]},
            upper_matrix=[[1, 5], [6, 4]],
            size_matrix=[[1, 2], [3, 4]],
            mask=[[False, False], [True, False]],
            vmin=0,
            vmax=10,
            upper_scale={"vmin": 0, "vmax": 10},
            width=1300,
            height=1200,
            multi_mode="single",
        )
        self.assertEqual(cell(svg, 0, 1).get("data-value"), "missing")
        self.assertAlmostEqual(_euclid([1, None, 3], [2, 5, 5]), math.sqrt(7.5))
        with self.assertRaisesRegex(ValueError, "no shared"):
            _euclid([1, None], [None, 2])
        with self.assertRaises(ValueError):
            make_clustered_heatmap([[1, 2], [3, 4]], ["A", "B"], ["X", "Y"], row_dendrogram={"order": [0, 0]})
        links = [(0, 1, 1, 2), (2, 3, 2, 2), (4, 5, 3, 4)]
        self.assertEqual(_apply_user_order({"linkage": links}, 4)[0], [0, 1, 2, 3])
        with self.assertRaisesRegex(ValueError, "contiguous"):
            _apply_user_order({"order": [0, 2, 1, 3], "linkage": links}, 4)
        with self.assertRaisesRegex(ValueError, "size"):
            _apply_user_order({"linkage": [(0, 1, 1, 3)]}, 2)


class MatrixReviewR1(unittest.TestCase):
    def test_m01_04_unit_scaling_log_domain_linkage_and_comparison(self):
        for variant in ("circle_full", "pie_full", "ellipse_upper"):
            geometries = []
            for factor in (1e-40, 1, 1e40):
                svg = make_matrix_heat(
                    [[factor, 2 * factor], [-factor, -2 * factor]],
                    labels=["A", "B"],
                    variant=variant,
                    show_row_mean=False,
                    show_col_mean=False,
                )
                geometries.append(
                    [
                        (
                            node.tag,
                            tuple((key, value) for key, value in node.attrib.items() if key not in {"fill", "stroke"}),
                        )
                        for node in cell(svg, 0, 0)
                    ]
                )
                if variant == "circle_full":
                    self.assertGreater(float(cell(svg, 0, 0).find("s:circle", NS).get("r")), 1)
            self.assertEqual(geometries[0], geometries[1])
            self.assertEqual(geometries[1], geometries[2])
        scale = ColorScale.from_values([1e-200, 1, 1e200], _resolve_palette("archive_ink"), log=True)
        self.assertEqual([scale.fraction(v) for v in (1e-200, 1, 1e200)], [0, 0.5, 1])
        self.assertAlmostEqual(scale.value_at(0.5), 1)
        self.assertEqual(len({scale.color(v) for v in (1e-200, 1, 1e200)}), 3)
        svg = make_dot_matrix([[1, 2, 3]], [[1e-200, 1, 1e200]], ["R"], ["A", "B", "C"], log_color=True)
        self.assertEqual(len({cell(svg, 0, j).find("s:circle", NS).get("fill") for j in range(3)}), 3)
        for factor in (1e-200, 1, 1e200):
            self.assertAlmostEqual(_euclid([factor, 2 * factor], [3 * factor, 4 * factor]) / factor, math.sqrt(8))
            _, links = _hcluster([[0], [4 * factor], [factor]])
            self.assertEqual(set(links[0][:2]), {0, 2})
            self.assertAlmostEqual(links[0][2] / factor, 1)
        svg = make_matrix_heat(
            [[1, 2], [3, 4]],
            labels=["A", "B"],
            upper_matrix=[[9, 80], [9, 9]],
            upper_scale={"vmin": 0, "vmax": 100, "label": "Method B"},
            compare_cols=(0, 1),
            width=1400,
            height=850,
        )
        first = root(svg).find('.//s:g[@data-comparison-row="0"]', NS)
        self.assertEqual([float(n.get("data-value")) for n in first.findall("s:circle", NS)], [1, 80])
        close_points = root(svg).find('.//s:g[@data-comparison-row="1"]', NS).findall("s:circle", NS)
        self.assertGreaterEqual(
            math.hypot(
                float(close_points[0].get("cx")) - float(close_points[1].get("cx")),
                float(close_points[0].get("cy")) - float(close_points[1].get("cy")),
            ),
            9,
        )
        self.assertIn("Displayed values", all_text(svg))
        self.assertTrue(
            any(float(n.get("data-scale-tick")) == 80 for n in root(svg).findall(".//s:g[@data-scale-tick]", NS))
        )
        with self.assertRaisesRegex(ValueError, "common unit"):
            make_matrix_heat([["text", 1]], columns=[{"type": "text"}, {"type": "number"}], compare_cols=(0, 1))

    def test_m05_09_ticks_minimums_masks_comparisons_and_pies(self):
        values = [1e12, 1e12 + 1, 1e12 + 3]
        self.assertEqual([float(v.replace(",", "")) for v in number_labels(values)], values)
        layout, _ = numeric_tick_layout([-0.001, 0, 1], [0, 0.15, 150], 0, 150, 12, "Arial", ["Min", "Midpoint", "Max"])
        self.assertEqual(len(layout), 3)
        self.assertGreater(layout[1]["lane"], 0)
        for i, left in enumerate(layout):
            for right in layout[i + 1 :]:
                if left["lane"] == right["lane"]:
                    self.assertTrue(
                        left["x"] + left["width"] + 8 <= right["x"] or right["x"] + right["width"] + 8 <= left["x"]
                    )
        svg = make_matrix_heat([[-0.001, 0, 1]], show_row_mean=False, show_col_mean=False)
        self.assertIn("-.001", all_text(svg).replace("-0.001", "-.001"))
        self.assertNotIn("-0.0<", svg)
        explicit = make_matrix_heat([[-0.001, 0, 1]], value_fmt=".1f", show_row_mean=False, show_col_mean=False)
        self.assertIn("-0.0", all_text(explicit))
        svg = make_dot_matrix([[1e12, 1e12 + 1]], [[1, 2]], ["R"], ["A", "B"], size_legend_values=[1e12, 1e12 + 1])
        labels = all_text(svg)
        self.assertIn("1000000000000", labels)
        self.assertIn("1000000000001", labels)
        svg = make_matrix_heat(
            [[1, 2], [3, 4]], labels=["A", "B"], variant="circle_full", show_row_mean=False, show_col_mean=False
        )
        node = cell(svg, 0, 0).find("s:circle", NS)
        self.assertIsNotNone(node.get("stroke"))
        self.assertNotEqual(_rgb_tuple(node.get("fill")), (255, 255, 255))
        tracks = prepare_tracks({"Numeric": [1, None, 4]}, 3, "Rows", _resolve_palette("archive_ink"))
        self.assertIsNone(tracks[0][1][1])
        self.assertNotEqual(_rgb_tuple(tracks[0][1][0]), (255, 255, 255))
        zero = make_matrix_heat([[0, 1]], variant="ellipse_upper", show_row_mean=False, show_col_mean=False)
        self.assertIsNotNone(cell(zero, 0, 0).find("s:ellipse", NS).get("stroke"))
        svg = make_matrix_heat(
            [["Visible", 1], ["Secret masked category", 999]],
            columns=[{"type": "category"}, {"type": "number"}],
            mask=[[False, False], [True, True]],
            cell_text=[[None, None], ["Secret annotation", "Hidden"]],
        )
        self.assertNotIn("Secret", svg)
        self.assertNotIn("Hidden", svg)
        natural = make_matrix_heat(
            [[None, 1]], cell_text=[["Not measured", None]], show_row_mean=False, show_col_mean=False
        )
        self.assertIn("Not measured", all_text(natural))
        categorical = make_dot_matrix(
            [[1, 2]], [["Visible", "Secret"]], ["R"], ["A", "B"], colormap={"Visible": "#123456"}, mask=[[False, True]]
        )
        self.assertNotIn("Secret", categorical)
        svg = make_matrix_heat(
            [[1, None], [2, 3], [None, 4]],
            row_labels=["R0", "R1", "R2"],
            col_labels=["Before", "After"],
            compare_cols=(0, 1),
            show_row_mean=False,
            show_col_mean=False,
        )
        rows = root(svg).findall(".//s:g[@data-comparison-row]", NS)
        self.assertEqual([len(row.findall("s:circle", NS)) for row in rows], [1, 2, 1])
        self.assertEqual([len(row.findall("s:line", NS)) for row in rows], [0, 1, 0])
        keys = root(svg).findall(".//s:circle[@data-comparison-key]", NS)
        self.assertEqual({n.get("data-comparison-key") for n in keys}, {"0", "1"})
        self.assertEqual(len({n.get("fill") for n in keys}), 2)
        svg = make_matrix_heat(
            [[1, 1], [1, None]], labels=["A", "B"], compare_cols=(0, 1), show_row_mean=False, show_col_mean=False
        )
        points = root(svg).find('.//s:g[@data-comparison-row="0"]', NS).findall("s:circle", NS)
        self.assertEqual(points[0].get("cx"), points[1].get("cx"))
        self.assertGreater(
            abs(float(points[0].get("cy")) - float(points[1].get("cy"))),
            float(points[0].get("r")) + float(points[1].get("r")),
        )
        svg = make_matrix_heat(
            [[9, 11]],
            row_labels=["R"],
            col_labels=["Below", "Above"],
            variant="pie_full",
            midpoint=10,
            vmin=8,
            vmax=12,
            show_row_mean=False,
            show_col_mean=False,
        )
        sweeps = []
        for j in range(2):
            path = cell(svg, 0, j).find("s:path", NS).get("d")
            sweeps.append(re.search(r"A \S+ \S+ 0 [01] ([01])", path).group(1))
        self.assertEqual(sweeps, ["0", "1"])


class MatrixReviewR2(unittest.TestCase):
    def test_mr2_hidden_triangles_extreme_clustering_and_finite_geometry(self):
        outputs = []
        for hidden in (0, 999):
            outputs.append(
                make_matrix_heat([[1, 2], [hidden, 3]], labels=["A", "B"], variant="ellipse_upper", compare_cols=(0, 1))
            )
        self.assertEqual(outputs[0], outputs[1])
        self.assertIsNone(cell(outputs[0], 1, 0))
        row = root(outputs[0]).find('.//s:g[@data-comparison-row="1"]', NS)
        self.assertEqual([float(n.get("data-value")) for n in row.findall("s:circle", NS)], [3])
        contexts = []

        def capture(context):
            contexts.append(context)
            return ""

        render_matrix([[1, 2], [999, 3]], ["A", "B"], ["A", "B"], variant="ellipse_upper", _overlays=[capture])
        self.assertEqual(contexts[0].matrix, ((1, 2), (None, 3)))
        self.assertEqual(contexts[0].color_domains, ((1, 3),))
        svg = make_matrix_heat(
            [[1, 2], [3, 4]], labels=["A", "B"], variant="ellipse_upper", upper_matrix=[[0, 9], [0, 0]]
        )
        self.assertEqual(
            [cell(svg, i, j).get("data-value") for i in range(2) for j in range(2)], ["1.0", "9.0", "3.0", "4.0"]
        )
        cases = [[[-1e308], [1e308]], [[-1e308], [1e308], [9e307]], [[-1e308], [1e308], [1e-308], [2e-308]]]
        for values in cases:
            order, linkage = _hcluster(values)
            self.assertEqual(sorted(order), list(range(len(values))))
            self.assertEqual(len(linkage), len(values) - 1)
            self.assertTrue(all(math.isfinite(d) for _, _, d, _ in linkage))
            svg = make_clustered_heatmap(
                values, [f"Row {i}" for i in range(len(values))], ["Measurement"], multi_mode="single"
            )
            self.assertEqual(meta(svg)["rows"], len(values))
            self.assertEqual(sorted(meta(svg)["row_order"]), list(range(len(values))))
        self.assertEqual(set(_hcluster(cases[-1])[1][0][:2]), {2, 3})
        self.assertEqual([stable_fraction(v, -1e308, 1e308) for v in (-1e308, 0, 1e308)], [0, 0.5, 1])
        scale = ColorScale.from_values([-1e308, 0, 1e308], _resolve_palette("archive_ink"), colormap="sequential")
        self.assertEqual([scale.fraction(v) for v in (-1e308, 0, 1e308)], [0, 0.5, 1])
        self.assertEqual(len({scale.color(v) for v in (-1e308, 0, 1e308)}), 3)
        positive = ColorScale.from_values(
            [1.2e308, 1.4e308, 1.6e308], _resolve_palette("archive_ink"), colormap="diverging"
        )
        self.assertTrue(math.isclose(positive.midpoint, 1.4e308, rel_tol=1e-15))
        for lo, hi in [(-sys.float_info.max, sys.float_info.max), (1.2e308, 1.6e308), (5e-324, 1e-323)]:
            for fraction in (0, 0.25, 0.5, 0.75, 1):
                value = stable_lerp(lo, hi, fraction)
                self.assertTrue(math.isfinite(value))
                self.assertLessEqual(lo, value)
                self.assertLessEqual(value, hi)
        for colormap in ("sequential", "diverging"):
            svg = make_matrix_heat(
                [[-1e308, 1e308], [-5e307, 5e307]], labels=["A", "B"], compare_cols=(0, 1), colormap=colormap
            )
            for node in root(svg).iter():
                for name in ("x", "y", "x1", "x2", "y1", "y2", "cx", "cy", "r", "width", "height"):
                    if node.get(name) is not None:
                        self.assertTrue(math.isfinite(float(node.get(name))), (node.tag, name, node.get(name)))
            points = root(svg).find('.//s:g[@data-comparison-row="0"]', NS).findall("s:circle", NS)
            self.assertLess(float(points[0].get("cx")), float(points[1].get("cx")))

    def test_mr2_03_extreme_domain_survives_public_cli(self):
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder) / "input.json"
            data.write_text(
                json.dumps(
                    {
                        "matrix": [[-1e308, 0, 1e308]],
                        "row_labels": ["R"],
                        "col_labels": ["Low", "Middle", "High"],
                        "colormap": "sequential",
                    }
                )
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).resolve().parents[2] / "gen_svg_charts.py"),
                    "--type",
                    "matrix_heat",
                    "--data-file",
                    str(data),
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertEqual(meta(result.stdout)["cols"], 3)


# ====================================================================================================
# Separate labels from area glyphs without altering their scale or values.
# ====================================================================================================


@pytest.mark.parametrize("palette, sized", [("archive_ink", False), ("nightlab", True)])
def test_below_labels_clear_circle_and_stay_inside_cell(palette, sized):
    matrix = [[25, 50], [75, 100]]
    options = dict(size_matrix=matrix, size_max=100) if sized else {}
    svg = make_matrix_heat(
        matrix,
        row_labels=["R1", "R2"],
        col_labels=["C1", "C2"],
        variant="circle_full",
        cell_label_position="below",
        cell_text=[["25", "50"], ["75", "100"]],
        vmin=0,
        vmax=100,
        show_row_mean=False,
        show_col_mean=False,
        palette=palette,
        **options,
    )
    root = ET.fromstring(svg)
    slide = ET.Element("slide")
    ET.SubElement(slide, "embed").append(root)
    assert not validate_embedded_svgs(slide)
    assert not detect_embedded_svg_overlaps(slide)
    info = json.loads(root.get("data-matrix-layout"))
    y0, y1 = info["plot_bbox"][1], info["plot_bbox"][3]
    height = (y1 - y0) / 2
    for cell in root.findall(".//{*}g[@data-row]"):
        circle = cell.find("{*}circle")
        label = cell.find("{*}text")
        fs = float(label.get("font-size"))
        top = float(label.get("y")) - fs * 0.85
        assert top > float(circle.get("cy")) + float(circle.get("r")) + 2
        assert float(label.get("y")) + fs * 0.2 <= y0 + (int(cell.get("data-row")) + 1) * height


def test_below_position_rejects_incompatible_square_variant():
    with pytest.raises(ValueError, match="circle_full or pie_full") as exc:
        make_matrix_heat([[1]], cell_label_position="below")
    assert str(exc.value)


# ====================================================================================================
# Scientific graph/tree invariants plus full SVG embedding/layout checks.
# ====================================================================================================


def assert_svg(test, svg):
    slide = ET.Element("slide")
    ET.SubElement(slide, "embed").append(ET.fromstring(svg))
    test.assertEqual(validate_embedded_svgs(slide), [])
    test.assertEqual(detect_embedded_svg_overlaps(slide), [])
    w, h, boxes = _text_boxes(svg)
    for x0, y0, x1, y1, label in boxes:
        test.assertTrue(0 <= x0 < x1 <= w and 0 <= y0 < y1 <= h, (label, (x0, y0, x1, y1), (w, h)))
    test.assertNotIn("transform=", svg)
    test.assertEqual(svg.count("<svg "), 1)


class NetworkAlgorithmTests(unittest.TestCase):
    def test_network_nodes_edges_layout_and_encodings(self):
        nodes = [{"id": str(i), "label": f"Node {i}"} for i in range(5)]
        edges = [{"source": "0", "target": "1", "correlation": value} for value in [-1, 0, 1, None]]
        edges += [{"source": "2", "target": "2", "weight": 0, "pvalue": 0.5}]
        svg = make_network(nodes, edges)
        self.assertEqual(len(elements(svg, "network-node")), 5)
        self.assertEqual(len(elements(svg, "network-edge")), 5)
        self.assertEqual([e.get("data-correlation") for e in elements(svg, "network-edge")[:3]], ["-1.0", "0.0", "1.0"])
        self.assertEqual(len({e.get("d") for e in elements(svg, "network-edge")}), 5)
        assert_svg(self, svg)
        nodes, edges = normalize_network(
            [{"id": str(i), "category": str(i // 3)} for i in range(9)],
            [{"source": str(i), "target": str(i + 1)} for i in range(7)],
        )
        self.assertEqual(force_positions(nodes, edges), force_positions(nodes, edges))
        a, b = force_positions(nodes, edges), force_positions(list(reversed(nodes)), edges)
        self.assertEqual(a, b)
        self.assertEqual(len(set(a.values())), 9)
        for unit in (1, 1e-320, 1e307):
            positions = fit_positions({"a": (0, 0), "b": (2 * unit, 0), "c": (0, unit)}, (50, 100, 450, 600))
            self.assertEqual(positions["b"][0] - positions["a"][0], 2 * (positions["c"][1] - positions["a"][1]))
            self.assertTrue(all(math.isfinite(v) for point in positions.values() for v in point))
        with self.assertRaisesRegex(ValueError, "overlap"):
            make_network([{"id": k} for k in "ABC"], [], positions={"A": (0, 0), "B": (0.001, 0), "C": (1, 0)})
        nodes, _ = normalize_network([{"id": "a", "size": 1}, {"id": "b", "size": 4}, {"id": "c", "size": 0}], [])
        radii = node_radii(nodes)
        self.assertEqual(radii["b"] ** 2 / radii["a"] ** 2, 4)
        self.assertEqual(radii["c"], 0)
        nodes = [{"id": str(i), "size": i % 9 + 1} for i in range(45)]
        edges = [{"source": str(i), "target": str(j)} for i in range(45) for j in range(i + 1, 45) if i // 9 == j // 9]
        svg = make_network(nodes, edges, width=420, height=320)
        circles = elements(svg, "network-node")
        for i, a in enumerate(circles):
            for b in circles[:i]:
                distance = math.hypot(float(a.get("cx")) - float(b.get("cx")), float(a.get("cy")) - float(b.get("cy")))
                self.assertGreaterEqual(distance + 0.01, float(a.get("r")) + float(b.get("r")) + 3.9)
        svg = make_network([{"id": "zero", "size": 0}, {"id": "missing", "size": None}], [])
        zero, missing = elements(svg, "network-node")
        self.assertIsNone(zero.get("stroke-dasharray"))
        self.assertEqual(missing.get("stroke-dasharray"), "2 1")
        svg = make_network(
            [{"id": "a"}, {"id": "b"}],
            [
                {"source": "a", "target": "b", "weight": weight, "pvalue": p}
                for weight, p in [(-2, 0), (0, 0.05), (4, None)]
            ],
        )
        a, b, c = elements(svg, "network-edge")
        self.assertNotEqual(a.get("stroke"), c.get("stroke"))
        self.assertLess(float(b.get("stroke-width")), float(a.get("stroke-width")))
        self.assertLess(float(a.get("stroke-width")), float(c.get("stroke-width")))
        self.assertEqual(b.get("stroke-dasharray"), "4 3")
        self.assertIsNone(a.get("stroke-dasharray"))
        nodes = [{"id": "l", "side": "left", "label": "输入"}, {"id": "r", "side": "right", "label": "Output"}]
        svg = make_network(nodes, [{"source": "l", "target": "r"}], layout="bipartite")
        circles = elements(svg, "network-node")
        self.assertLess(float(circles[0].get("cx")), float(circles[1].get("cx")))
        assert_svg(self, svg)
        with self.assertRaises(ValueError):
            make_network(nodes, [{"source": "l", "target": "l"}], layout="bipartite")
        nodes = [{"id": "hub", "side": "inner", "label": "功能类别"}] + [
            {"id": key, "label": key} for key in ["b", "a", "c"]
        ]
        edges = [{"source": "hub", "target": key} for key in ["b", "a", "c"]]
        svg = make_network(
            nodes,
            edges,
            layout="radial",
            tracks=[{"name": "Effect", "kind": "bar", "values": {"a": 1, "b": -2, "c": 0}}],
        )
        self.assertEqual([float(e.get("data-value")) for e in elements(svg, "track-bar")], [-2, 1, 0])
        self.assertEqual(len(elements(svg, "network-node")), 4)
        assert_svg(self, svg)
        canvas = ChartLayout(1200, 800, None, None)
        context = render_network_plot(
            canvas, (400, 100, 1100, 700), [{"id": "a"}, {"id": "b"}], [{"source": "a", "target": "b"}]
        )
        self.assertTrue(all(400 < x < 1100 and 100 < y < 700 for x, y in context["positions"].values()))
        self.assertEqual(context["plot_bbox"], (400, 100, 1100, 700))
        assert_svg(self, canvas.svg("Composition"))
        for nodes, edges in [
            ([], []),
            ([{"id": "a"}, {"id": "a"}], []),
            ([{"id": "a", "size": -1}], []),
            ([{"id": "a"}], [{"source": "a", "target": "x"}]),
            ([{"id": "a"}], [{"source": "a", "target": "a", "correlation": 1.1}]),
            ([{"id": "a"}], [{"source": "a", "target": "a", "pvalue": math.nan}]),
        ]:
            with self.subTest(nodes=nodes, edges=edges), self.assertRaises((ValueError, TypeError)):
                make_network(nodes, edges)
        with self.assertRaises(ValueError):
            make_network([{"id": "a"}], [], positions={})

    def test_dense_long_labels_small_and_dark_canvas(self):
        nodes = [
            {
                "id": str(i),
                "label": f"样本 {i:02d} / extended pathway classification",
                "category": str(i // 8),
                "size": i,
            }
            for i in range(32)
        ]
        edges = [{"source": str(i), "target": str((i + 1) % 32), "correlation": math.sin(i)} for i in range(32)]
        for palette in [None, {"bg": "#111827", "ink": "#f8fafc", "accent": "#f59e0b", "secondary": "#60a5fa"}]:
            svg = make_network(nodes, edges, width=420, height=320, palette=palette)
            self.assertEqual(len(elements(svg, "network-node")), 32)
            self.assertEqual(len(elements(svg, "network-edge")), 32)
            assert_svg(self, svg)


class PhylogenyAlgorithmTests(unittest.TestCase):
    def test_phylogeny_branches_orders_topology_and_colours(self):
        for unit in (5e-324, 1e-323, 1e-320, 1e307):
            svg = make_phylogeny(f"(A:{unit},B:{2 * unit},C:{3 * unit});")
            branches = elements(svg, "phylo-branch")
            radii = [float(e.get("data-r-end")) for e in branches]
            self.assertAlmostEqual(radii[1] / radii[0], 2, places=4)
            self.assertAlmostEqual(radii[2] / radii[0], 3, places=4)
            assert_svg(self, svg)
        data = normalize_tree("((A:1,B:3):2,C:7);")
        distance = {node["id"]: node["distance"] for node in data["leaves"]}
        self.assertEqual(distance, {"A": 3, "B": 5, "C": 7})
        svg = make_phylogeny("((A:1,B:3):2,C:7);")
        branches = elements(svg, "phylo-branch")
        ratios = [
            (float(e.get("data-r-end")) - float(e.get("data-r-start"))) / float(e.get("data-length")) for e in branches
        ]
        self.assertTrue(all(math.isclose(ratios[0], ratio) for ratio in ratios))
        self.assertEqual(len(branches), 4)
        assert_svg(self, svg)
        svg = make_phylogeny(
            "((A:1,B:2):1,(C:2,D:3):1);",
            leaf_order=["D", "C", "B", "A"],
            tracks=[
                {"name": "Count", "kind": "bar", "values": [1, 2, 3, 4]},
                {"name": "Score", "values": {"A": -1, "B": None, "C": 1, "D": 0}},
            ],
        )
        self.assertEqual([float(e.get("data-value")) for e in elements(svg, "track-bar")], [4, 3, 2, 1])
        self.assertEqual([float(e.get("data-value")) for e in elements(svg, "track-cell")], [0, 1, -1])
        self.assertEqual(len(elements(svg, "missing")), 1)
        self.assertEqual(len(elements(svg, "phylo-branch")), 6)
        assert_svg(self, svg)
        with self.assertRaisesRegex(ValueError, "clade contiguous"):
            make_phylogeny("((A:1,B:2):1,(C:2,D:3):1);", leaf_order=["A", "C", "B", "D"])
        self.assertEqual(normalize_tree("((A,B),C);")["branch_mode"], "cladogram")
        with self.assertRaisesRegex(ValueError, "partial branch"):
            normalize_tree("((A:1,B),C);")
        self.assertEqual(normalize_tree("((A:1,B),C);", "cladogram")["branch_mode"], "cladogram")
        with self.assertRaises(ValueError):
            normalize_tree("(A,B);", "length")
        a = normalize_tree("('A''s species':1[comment],中文:2);")
        b = normalize_tree(
            {"children": [{"id": "A's species", "branch_length": 1}, {"id": "中文", "branch_length": 2}]}
        )
        self.assertEqual(a["leaf_order"], b["leaf_order"])
        self.assertEqual([n["distance"] for n in a["leaves"]], [n["distance"] for n in b["leaves"]])
        for tree in [
            "(A:1,A:2);",
            "(A:-1,B:2);",
            "(A:inf,B:2);",
            "(A:1,B:2); trailing",
            "(A:1,B:2):1;",
            "(A:0,B:0);",
            "('A:1,B:2);",
        ]:
            with self.subTest(tree=tree), self.assertRaises(ValueError):
                normalize_tree(tree)
        cyclic = {"id": "a"}
        cyclic["children"] = [cyclic]
        with self.assertRaisesRegex(ValueError, "acyclic"):
            normalize_tree(cyclic)
        svg = make_phylogeny("((A:0,B:1):0,C:3);")
        self.assertEqual(sum(e.get("data-length") == "0.0" for e in elements(svg, "phylo-branch")), 2)
        self.assertEqual(len(elements(svg, "phylo-tip-guide")), 2)
        assert_svg(self, svg)
        tree = {
            "children": [
                {"id": "a", "label": "Taxon", "category": "Group 1", "size": 1},
                {"id": "b", "label": "Taxon", "category": "Group 2", "size": 4},
            ]
        }
        svg = make_phylogeny(tree)
        nodes = elements(svg, "phylo-node")
        self.assertAlmostEqual(float(nodes[1].get("r")) ** 2 / float(nodes[0].get("r")) ** 2, 4, places=3)
        self.assertEqual(len(elements(svg, "track-cell")), 2)
        assert_svg(self, svg)
        tree = {
            "children": [
                {"id": "a", "category": "One"},
                {"id": "b", "category": "Two"},
                {"id": "c", "category": "Three"},
            ]
        }
        first = make_phylogeny(tree)
        second = make_phylogeny(tree, leaf_order=["c", "b", "a"])
        colors = {e.get("data-value"): e.get("fill") for e in elements(first, "track-cell")}
        reordered = {e.get("data-value"): e.get("fill") for e in elements(second, "track-cell")}
        self.assertEqual(colors, reordered)
        nodes = {e.get("data-node-id"): e.get("fill") for e in elements(first, "phylo-node")}
        self.assertEqual(nodes, {"a": colors["One"], "b": colors["Two"], "c": colors["Three"]})
        canvas = ChartLayout(1200, 900, None, None)
        context = render_phylogeny_plot(canvas, (400, 50, 1150, 850), "((A:1,B:2):3,C:6);")
        self.assertEqual(context["leaf_order"], ["A", "B", "C"])
        self.assertTrue(all(400 < x < 1150 and 50 < y < 850 for x, y in context["positions"].values()))
        assert_svg(self, canvas.svg("Composition"))

    def test_dense_tree_small_canvas_and_many_tracks_retain_labels(self):
        tree = {
            "children": [
                {
                    "children": [
                        {
                            "id": f"{i}-{j}",
                            "label": f"物种 {i}-{j} / long bacterial classification",
                            "branch_length": j + 1,
                            "category": f"Clade {i}",
                        }
                        for j in range(5)
                    ],
                    "branch_length": i + 1,
                }
                for i in range(6)
            ]
        }
        tracks = [
            {"name": "Presence", "values": [i % 2 for i in range(30)]},
            {"name": "Amount", "kind": "bar", "values": list(range(30))},
            {"name": "Detection", "kind": "point", "values": [i / 30 for i in range(30)]},
        ]
        svg = make_phylogeny(tree, tracks=tracks, width=400, height=300)
        self.assertEqual(len(elements(svg, "phylo-branch")), 36)
        self.assertEqual(len(elements(svg, "track-point")), 30)
        self.assertEqual(len(elements(svg, "track-bar")), 30)
        assert_svg(self, svg)


# ====================================================================================================
# Algorithm/contract regression coverage for the two new coordinate families.
# ====================================================================================================


class TernaryAlgorithmTests(unittest.TestCase):
    def test_ternary_projection_mesh_density_and_encoding(self):
        self.assertEqual(_barycentric((1, 0, 0)), (0.5, _ALTITUDE))
        self.assertEqual(_barycentric((0, 1, 0)), (0, 0))
        self.assertEqual(_barycentric((0, 0, 1)), (1, 0))
        x, y = _barycentric((1 / 3, 1 / 3, 1 / 3))
        self.assertAlmostEqual(x, 0.5)
        self.assertAlmostEqual(y, _ALTITUDE / 3)
        self.assertEqual(_composition((20, 30, 50), total=100), (0.2, 0.3, 0.5))
        self.assertEqual(_composition((2, 3, 5), normalize=True), (0.2, 0.3, 0.5))
        self.assertRaises(ValueError, _composition, (2, 3, 5))
        self.assertRaises(ValueError, make_ternary, [(0, 0, 0)], normalize=True)
        self.assertRaises(ValueError, make_ternary, [(1, 0, 0)], total=0)
        self.assertRaises(ValueError, make_ternary, [(1, 0, 0)], total=math.inf)
        for point in ((-0.1, 0.1, 1), (0.2, 0.3), (math.nan, 0, 1), (math.inf, 0, 0), (True, 0, 0)):
            with self.subTest(point=point), self.assertRaises((ValueError, TypeError)):
                make_ternary([point])
        for n in (1, 2, 9):
            xy, triangles = _mesh(n)
            self.assertEqual(len(xy), (n + 1) * (n + 2) // 2)
            self.assertEqual(len(triangles), n * n)
            area = 0
            for tri in triangles:
                a, b, c = [xy[k] for k in tri]
                area += abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])) / 2
            self.assertAlmostEqual(area, _ALTITUDE / 2)
        target = _barycentric((0.7, 0.2, 0.1))
        xy, triangles, z = _density_mesh([target] * 4, bandwidth=0.08)
        integral = sum(sum(z[k] for k in tri) / 3 * _ALTITUDE / (2 * 36**2) for tri in triangles)
        self.assertAlmostEqual(integral, 1)
        peak = xy[max(range(len(z)), key=z.__getitem__)]
        self.assertLess(math.dist(peak, target), 0.04)
        self.assertTrue(all(math.isfinite(v) and v >= 0 for v in z))
        self.assertRaises(ValueError, _density_mesh, [target], 0)
        # z=A; the 0.5 isoline is horizontal halfway up the triangle.
        xy, triangles, z = _precomputed_mesh([[0, 0, 0], [0.5, 0.5], [1]])
        segments = _contour_segments(xy, triangles, z, 0.5)
        self.assertTrue(segments)
        for segment in segments:
            for x, y in segment:
                self.assertAlmostEqual(y, _ALTITUDE / 2)
        self.assertRaises(ValueError, _precomputed_mesh, [[0, 0], [0, 0]])
        self.assertRaises(ValueError, make_ternary, [{"a": 1, "b": 0, "c": 0, "value": 3}, {"a": 0, "b": 1, "c": 0}])
        self.assertRaises(ValueError, make_ternary, [{"a": 1, "b": 0, "c": 0, "group": "G", "value": 3}])
        self.assertRaises(ValueError, make_ternary, [{"a": 1, "b": 0, "c": 0, "weight": 3}])
        self.assertRaises(ValueError, make_ternary, [{"a": 1, "b": 0, "c": 0, "size": -3}])
        self.assertRaises(ValueError, make_ternary, [{"a": 1, "b": 0, "c": 0, "size": 0}])
        self.assertRaises(ValueError, make_ternary, [{"a": 1, "b": 0, "c": 0, "group": "G"}], kind="density")
        points = [{"a": 0.2, "b": 0.3, "c": 0.5, "facet": "A & B"}, {"a": 0.7, "b": 0.2, "c": 0.1, "facet": "C < D"}]
        for kind in ("scatter", "density", "contour"):
            root = ET.fromstring(make_ternary(points, kind=kind, title="A < B & C"))
            self.assertIn("A & B", "".join(root.itertext()))
        self.assertRaises(ValueError, make_ternary, points, width=400, height=300)
        points = [{"a": 0.2, "b": 0.3, "c": 0.5, "size": 1}, {"a": 0.7, "b": 0.2, "c": 0.1, "size": 4}]
        svg = ET.fromstring(make_ternary(points))
        circles = svg.findall(".//{http://www.w3.org/2000/svg}circle")[:2]
        radii = [float(c.attrib["r"]) for c in circles]
        self.assertAlmostEqual(radii[0] ** 2 / radii[1] ** 2, 4)
        svg = make_ternary(
            [{"a": 0.2, "b": 0.3, "c": 0.5, "facet": f"Facet {i}"} for i in range(4)], width=1000, height=1020
        )
        _, _, boxes = _text_boxes(svg)
        facets = [box for box in boxes if box[-1].startswith("Facet ")]
        self.assertEqual(len({round(box[1], 1) for box in facets}), 2)


class UpSetAlgorithmTests(unittest.TestCase):
    def assert_integer_certificate(self, known, witness):
        self.assertIsNotNone(witness)
        self.assertTrue(
            all(isinstance(value, int) and not isinstance(value, bool) and value >= 0 for value in witness.values())
        )
        for fact, target in known.items():
            self.assertEqual(sum(value for atom, value in witness.items() if atom & fact == fact), target)

    def setUp(self):
        self.sets = {"A": [1, 2, 3, 4, 4], "B": [3, 4, 5], "C": [4, 6]}

    def test_exclusive_and_inclusive_counts_and_explicit_sizes(self):
        names, counts, sizes = _prepare_upset(self.sets, None, None, "exclusive")
        self.assertEqual(sizes, {"A": 4, "B": 3, "C": 2})
        self.assertEqual(counts[frozenset(("A", "B", "C"))], 1)
        self.assertEqual(counts[frozenset(("A", "B"))], 1)
        self.assertEqual(counts[frozenset(("A",))], 2)
        self.assertEqual(sum(counts.values()), 6)
        for name in names:
            self.assertEqual(sum(v for k, v in counts.items() if name in k), sizes[name])
        _, counts, sizes = _prepare_upset(self.sets, None, None, "inclusive")
        self.assertEqual(counts[frozenset(("A", "B"))], 2)
        self.assertEqual(counts[frozenset(("A", "C"))], 1)
        self.assertEqual(counts[frozenset(("B", "C"))], 1)
        self.assertEqual(counts[frozenset(("A",))], sizes["A"])
        self.assertGreater(sum(counts.values()), 6)
        rows = [{"sets": ["A"], "size": 4}, {"sets": ["A", "B"], "size": 3}]
        _, _, sizes = _prepare_upset(None, rows, None, "exclusive")
        self.assertEqual(sizes, {"A": 7, "B": 3})
        self.assertRaises(ValueError, _prepare_upset, None, rows, {"A": 5, "B": 3}, "exclusive")
        rows = [{"sets": ["A", "B"], "size": 3}]
        self.assertRaises(ValueError, _prepare_upset, None, rows, None, "inclusive")
        _, _, sizes = _prepare_upset(None, rows, {"A": 9, "B": 8}, "inclusive")
        self.assertEqual(sizes, {"A": 9, "B": 8})
        self.assertRaises(ValueError, _prepare_upset, None, rows, {"A": 2, "B": 8}, "inclusive")
        # Pairwise monotonicity alone cannot detect negative A-only atom.
        rows = [
            {"sets": s, "size": v}
            for s, v in [
                (["A"], 2),
                (["B"], 2),
                (["C"], 2),
                (["A", "B"], 2),
                (["A", "C"], 2),
                (["B", "C"], 2),
                (["A", "B", "C"], 0),
            ]
        ]
        self.assertRaises(ValueError, _prepare_upset, None, rows, None, "inclusive")
        rows[-1]["size"] = 2
        _prepare_upset(None, rows, None, "inclusive")

    def test_upset_inclusive_validation_omitted_intersections_and_exhaustive_phase_one(self):
        rows = [
            {"sets": s, "size": v} for s, v in [(["A", "B"], 2), (["A", "C"], 2), (["B", "C"], 2), (["A", "B", "C"], 0)]
        ]
        sizes = {"A": 2, "B": 2, "C": 2}
        singletons = [{"sets": [name], "size": value} for name, value in sizes.items()]
        for extra in ({}, {"Unused D": 0}, {f"Unused {i}": 0 for i in range(14)}):
            with self.assertRaisesRegex(ValueError, "negative"):
                _prepare_upset(None, rows, dict(sizes, **extra), "inclusive")
        self.assertRaises(ValueError, _prepare_upset, None, singletons + rows, None, "inclusive")
        rows[-1]["size"] = 2
        _, separate_counts, separate_sizes = _prepare_upset(None, rows, sizes, "inclusive")
        _, embedded_counts, embedded_sizes = _prepare_upset(None, singletons + rows, None, "inclusive")
        self.assertEqual(separate_sizes, embedded_sizes)
        self.assertEqual(len(separate_counts), 4)  # No invented singleton columns.
        self.assertTrue(all(embedded_counts[key] == value for key, value in separate_counts.items()))
        rows = [{"sets": s, "size": v} for s, v in [(["A", "B"], 9), (["A", "C"], 9), (["B", "C"], 1)]]
        for extra in ({}, {f"Unused {i}": 0 for i in range(14)}):
            self.assertRaises(ValueError, _prepare_upset, None, rows, dict(A=10, B=10, C=10, **extra), "inclusive")
        rows[-1]["size"] = 8
        _, counts, _ = _prepare_upset(None, rows, {"A": 10, "B": 10, "C": 10}, "inclusive")
        self.assertEqual(len(counts), 3)  # Unknown ABC is not manufactured as zero or displayed.
        # A higher-order Bonferroni bound, not merely the review's ABC pattern.
        rows = [
            {"sets": s, "size": v} for s, v in [(["A", "B"], 9), (["A", "C"], 9), (["A", "D"], 9), (["B", "C", "D"], 6)]
        ]
        self.assertRaises(ValueError, _prepare_upset, None, rows, {"A": 10, "B": 10, "C": 10, "D": 10}, "inclusive")
        rows[-1]["size"] = 7
        _prepare_upset(None, rows, {"A": 10, "B": 10, "C": 10, "D": 10}, "inclusive")
        limit = 2**53
        rows = [{"sets": s, "size": v} for s, v in [(["A", "B"], limit), (["A", "C"], limit), (["B", "C"], limit - 1)]]
        self.assertRaises(ValueError, _prepare_upset, None, rows, {"A": limit, "B": limit, "C": limit}, "inclusive")
        masks = (1, 2, 4, 3, 5, 6)  # Three singleton and three pairwise facts; ABC unknown.
        feasible = set()
        for atoms in itertools.product(range(3), repeat=7):
            values = tuple(sum(atoms[atom - 1] for atom in range(1, 8) if atom & mask == mask) for mask in masks)
            if max(values[:3]) <= 2:
                feasible.add(values)
        for a, b, c in itertools.product(range(3), repeat=3):
            for ab, ac, bc in itertools.product(range(min(a, b) + 1), range(min(a, c) + 1), range(min(b, c) + 1)):
                values = (a, b, c, ab, ac, bc)
                witness = _inclusive_atom_witness(3, dict(zip(masks, values)))
                self.assertEqual(witness is not None, values in feasible, values)

    def test_partial_inclusive_random_feasible_certificates_and_size_limit(self):
        rng = random.Random(108)
        for n in range(3, 9):
            sets = {str(i): {j for j in range(25) if rng.random() < 0.5} for i in range(n)}
            rows = []
            for mask in rng.sample(list(range(1, 1 << n)), min(24, (1 << n) - 1)):
                names = [str(i) for i in range(n) if mask & (1 << i)]
                rows.append({"sets": names, "size": len(set.intersection(*(sets[name] for name in names)))})
            _, counts, _ = _prepare_upset(None, rows, {s: len(v) for s, v in sets.items()}, "inclusive")
            self.assertEqual(len(counts), len(rows))
        chain = [{"sets": [str(i), str(i + 1)], "size": 1} for i in range(8)]
        with self.assertRaisesRegex(ValueError, "at most 8 connected"):
            _prepare_upset(None, chain, {str(i): 2 for i in range(9)}, "inclusive")

    def test_upset_fractional_atoms_and_branch_bounds(self):
        known = {1: 2, 2: 2, 4: 2, 8: 2, 3: 1, 5: 1, 9: 1, 6: 1, 10: 1, 12: 1, 15: 0}
        relaxed = _inclusive_lp_witness(4, known)
        self.assertIsNotNone(relaxed)
        self.assertTrue(any(Fraction(value).denominator != 1 for value in relaxed.values()))
        self.assertIsNone(_inclusive_atom_witness(4, known))
        # Independent finite enumeration: after relabeling A={0,1}, B={0,2},
        # the union has at most 8 members, so all 28x28 candidate C/D pairs fit.
        candidates = [set(pair) for pair in itertools.combinations(range(8), 2)]
        integer_solutions = 0
        for c, d in itertools.product(candidates, repeat=2):
            samples = [{0, 1}, {0, 2}, c, d]
            if all(len(a & b) == 1 for a, b in itertools.combinations(samples, 2)) and not set.intersection(*samples):
                integer_solutions += 1
        self.assertEqual(integer_solutions, 0)
        names = list("ABCD")
        rows = [{"sets": list(pair), "size": 1} for pair in itertools.combinations(names, 2)]
        rows.append({"sets": names, "size": 0})
        with self.assertRaisesRegex(ValueError, "integer"):
            make_upset(intersections=rows, set_sizes=dict.fromkeys(names, 2), mode="inclusive")
        for positive in ({mask: value * 2 for mask, value in known.items()}, {**known, 15: 1}):
            self.assert_integer_certificate(positive, _inclusive_atom_witness(4, positive))
        known = {1: 3, 2: 3}
        self.assertEqual(_inclusive_lp_witness(2, known, bounds={3: (2, 2)}), {3: 2, 1: 1, 2: 1})
        for bounds in ({3: (0, 1)}, {3: (3, None)}, {1: (1, 2), 3: (1, 2)}):
            witness = _inclusive_lp_witness(2, known, bounds=bounds)
            self.assertIsNotNone(witness)
            for mask, target in known.items():
                self.assertEqual(sum(v for a, v in witness.items() if a & mask == mask), target)
            for atom, (lower, upper) in bounds.items():
                self.assertGreaterEqual(witness.get(atom, 0), lower)
                if upper is not None:
                    self.assertLessEqual(witness.get(atom, 0), upper)
        for bounds in ({3: (4, None)}, {3: (3, 2)}, {1: (2, None), 3: (2, None)}):
            self.assertIsNone(_inclusive_lp_witness(2, known, bounds=bounds))
        self.assertIsNone(_inclusive_lp_witness(2, {**known, 3: 0}, bounds={3: (1, None)}))
        # Fixed AB atoms affect A and B but not C; an upper bound on ABC must
        # be enforced independently through its nonnegative slack.
        triple = {1: 3, 2: 3, 4: 3, 3: 3}
        self.assertIsNotNone(_inclusive_lp_witness(3, triple, bounds={3: (2, 2)}))
        self.assertIsNone(_inclusive_lp_witness(3, triple, bounds={3: (2, 2), 7: (0, 0)}))

    def test_integer_search_accepts_a_fractional_first_lp_solution(self):
        samples = [
            {1, 2, 4, 6, 7, 9, 10, 11},
            {0, 1, 5, 7, 8, 9},
            {1, 3, 4, 8, 9},
            {0, 1, 2, 4, 8, 10, 11},
            {2, 3, 4, 6, 7, 8, 9, 11},
            {0, 1, 4, 6, 7, 8, 9, 10},
            {0, 4, 7, 10, 11},
            {0, 3, 6, 7, 8, 10},
        ]
        masks = [129, 13, 18, 150, 25, 27, 161, 34, 168, 170, 49, 55, 184, 192]
        masks += [195, 71, 81, 210, 88, 216, 97, 109, 251, 239, 243, 247, 121, 123, 255]
        known = {mask: len(set.intersection(*(samples[i] for i in range(8) if mask & (1 << i)))) for mask in masks}
        known.update({1 << i: len(sample) for i, sample in enumerate(samples)})
        relaxed = _inclusive_lp_witness(8, known)
        self.assertTrue(any(Fraction(value).denominator != 1 for value in relaxed.values()))
        self.assert_integer_certificate(known, _inclusive_atom_witness(8, known))
        rows = [{"sets": [str(i) for i in range(8) if mask & (1 << i)], "size": known[mask]} for mask in masks]
        _, displayed, _ = _prepare_upset(None, rows, {str(i): len(s) for i, s in enumerate(samples)}, "inclusive")
        self.assertEqual(len(displayed), len(rows))

    def test_integer_certificates_for_real_member_sets_across_densities(self):
        for seed in (308, 731):
            rng = random.Random(seed)
            for n in range(3, 9):
                for repetition in range(6):
                    density = 0.48 if seed == 308 else 0.2 + 0.1 * repetition
                    members = [
                        {m for m in range(12 if seed == 308 else 18) if rng.random() < density} for _ in range(n)
                    ]
                    masks = set(rng.sample(list(range(1, 1 << n)), min((1 << n) - 1, 4 * n)))
                    masks.update(1 << i for i in range(n))
                    known = {
                        mask: len(set.intersection(*(members[i] for i in range(n) if mask & (1 << i))))
                        for mask in masks
                    }
                    with self.subTest(seed=seed, n=n, repetition=repetition):
                        self.assert_integer_certificate(known, _inclusive_atom_witness(n, known))
                        rows = [
                            {"sets": [str(i) for i in range(n) if mask & (1 << i)], "size": value}
                            for mask, value in known.items()
                            if mask & (mask - 1)
                        ]
                        _, displayed, _ = _prepare_upset(
                            None, rows, {str(i): len(s) for i, s in enumerate(members)}, "inclusive"
                        )
                        self.assertEqual(len(displayed), len(rows))

    def test_count_validation_sorting_truncation_and_empty_sets(self):
        rows = [{"sets": ["A"], "size": 2**53}, {"sets": ["A", "B"], "size": 1}]
        with self.assertRaisesRegex(ValueError, "derived set size"):
            make_upset(intersections=rows)
        self.assertEqual(number_label(2**53 + 1), "9,007,199,254,740,993")
        self.assertEqual(number_label(9_000_000_000_000_000, compact=True), "9e15")
        self.assertEqual(float(number_label(2**53, compact=True).replace(",", "")), 2**53)
        for size in (-1, 1.5, math.nan, True, 2**53 + 1):
            self.assertRaises((ValueError, TypeError), make_upset, intersections=[{"sets": ["A"], "size": size}])
        self.assertRaises(ValueError, make_upset, intersections=[{"sets": ["A"], "size": 1}] * 2)
        self.assertRaises(ValueError, make_upset, intersections=[{"sets": ["A", "A"], "size": 1}])
        self.assertRaises(TypeError, make_upset, {"A": "abc"})
        self.assertRaises(ValueError, make_upset, self.sets, set_order=["A", "B"])
        svg = ET.fromstring(make_upset(self.sets, max_intersections=1, set_order=["C", "A", "B"]))
        text = svg.attrib["aria-label"] + "".join(svg.itertext())
        self.assertIn("row order: C, A, B", text)
        self.assertIn("Showing 1 of 5", text)
        self.assertIn("set sizes remain complete", text)
        # The full size A=4 remains in a set-size bar after selecting one column.
        labels = [t.text for t in svg.findall(".//{http://www.w3.org/2000/svg}text")]
        self.assertIn("4", labels)
        for sort in ("input", "degree", "size"):
            ET.fromstring(make_upset(self.sets, sort_by=sort))
        svg = make_upset({"A": [], "B": []})
        self.assertIn("No nonempty intersections", svg)
        rows = [{"sets": ["B"], "size": 2}, {"sets": ["A"], "size": 3}]
        svg = make_upset(intersections=rows, sort_by="input")
        self.assertIn("UpSet", svg)


class TextLayoutTests(unittest.TestCase):
    def test_generated_charts_pass_the_slide_embed_contract(self):
        examples = [
            make_ternary([(0.7, 0.2, 0.1), (0.2, 0.6, 0.2)], kind="density"),
            make_upset(
                intersections=[
                    {"sets": ["A"], "size": 21},
                    {"sets": ["A", "B"], "size": 9},
                    {"sets": ["B", "C"], "size": 4},
                    {"sets": ["C"], "size": 13},
                ],
                sort_by="degree",
                title="Explicit exclusive intersection counts",
            ),
        ]
        for svg in examples:
            root = ET.fromstring(svg)
            self.assertIn("aria-label", root.attrib)
            width, height = root.attrib["viewBox"].split()[2:]
            slide = ET.Element("slide")
            embed = ET.SubElement(
                ET.SubElement(slide, "data"),
                "embed",
                {"id": "chart", "topLeftX": "0", "topLeftY": "0", "width": width, "height": height},
            )
            embed.append(root)
            issues = embed_svg_validator.validate_embedded_svgs(slide)
            issues.extend(embed_svg_validator.detect_embedded_svg_overlaps(slide))
            self.assertEqual(issues, [])

    def assert_text_clear(self, svg):
        width, height, boxes = _text_boxes(svg)
        for i, a in enumerate(boxes):
            self.assertGreaterEqual(a[0], 0, a[-1])
            self.assertGreaterEqual(a[1], 0, a[-1])
            self.assertLessEqual(a[2], width, a[-1])
            self.assertLessEqual(a[3], height, a[-1])
            for b in boxes[i + 1 :]:
                intersection = (min(a[2], b[2]) - max(a[0], b[0]), min(a[3], b[3]) - max(a[1], b[1]))
                self.assertFalse(intersection[0] > 1 and intersection[1] > 1, (a[-1], b[-1]))

    def test_large_total_nine_facets_share_explicit_multiplier(self):
        svg = make_ternary(
            [{"a": 2e11, "b": 3e11, "c": 5e11, "facet": f"Sample {i}"} for i in range(9)],
            total=1e12,
            width=1500,
            height=1500,
        )
        self.assertTrue("Axis ticks × 1e12" in svg)
        _, _, boxes = _text_boxes(svg)
        self.assertEqual(sum(box[-1] == "0.2" for box in boxes), 27)
        self.assert_text_clear(svg)

    def test_compact_upset_retains_large_exact_counts(self):
        svg = make_upset(
            intersections=[{"sets": ["A"], "size": 9_000_000_000_000_000}],
            width=700,
            height=700,
            title="Large set count at a compact width",
        )
        _, _, boxes = _text_boxes(svg)
        self.assertGreaterEqual(sum(box[-1] == "9e15" for box in boxes), 3)
        self.assert_text_clear(svg)
        # The exact non-round limit also fits its measured count column.
        svg = make_upset(intersections=[{"sets": ["A"], "size": 2**53}], width=700, height=700)
        self.assertIn(number_label(2**53, compact=True), svg)
        self.assert_text_clear(svg)

    def test_scientific_float_legends_use_measured_lanes(self):
        for field, values in [
            ("value", (6.02214076e23, 6.02214076e23)),
            ("value", (1e60, 1e60)),
            ("size", (1e23, 2e23)),
            ("size", (1e50, 2e50)),
        ]:
            points = [dict(a=0.8, b=0.1, c=0.1, **{field: values[0]}), dict(a=0.1, b=0.8, c=0.1, **{field: values[1]})]
            svg = make_ternary(points)
            self.assert_text_clear(svg)
        self.assertEqual(number_label(6.02214076e23), "6.02214076e+23")
        self.assertEqual(number_label(602214076000000000000000), "602,214,076,000,000,000,000,000")

    def test_unequal_facet_titles_preserve_identical_plot_geometry(self):
        points = [
            {"a": 0.8, "b": 0.1, "c": 0.1, "facet": name}
            for name in (
                "A",
                "A much longer experimental condition title that spans at least three lines in this narrow facet",
            )
        ]
        svg = make_ternary(points, width=1100, height=520, title="Equal compositions in two facets")
        root = ET.fromstring(svg)
        triangles = [
            e for e in root.findall(".//{http://www.w3.org/2000/svg}polygon") if e.attrib.get("fill") == "none"
        ]
        coords = [[tuple(map(float, p.split(","))) for p in e.attrib["points"].split()] for e in triangles]
        self.assertEqual(len(coords), 2)
        self.assertAlmostEqual(coords[0][0][1], coords[1][0][1], places=2)
        self.assertAlmostEqual(coords[0][2][0] - coords[0][1][0], coords[1][2][0] - coords[1][1][0], places=2)
        circles = root.findall(".//{http://www.w3.org/2000/svg}circle")
        self.assertEqual(circles[0].attrib["cy"], circles[1].attrib["cy"])
        self.assert_text_clear(svg)

    def test_close_size_references_are_visually_distinct(self):
        self.assertEqual(_size_references([1.0001, 1.0002]), [1.0002])
        points = [{"a": 0.8, "b": 0.1, "c": 0.1, "size": 1.0001}, {"a": 0.1, "b": 0.8, "c": 0.1, "size": 1.0002}]
        root = ET.fromstring(make_ternary(points))
        self.assertEqual(
            len(root.findall(".//{http://www.w3.org/2000/svg}circle")), 3
        )  # Two data + one scale reference.
        self.assertIn("1.0002", "".join(root.itertext()))
        refs = _size_references([0.000001, 1, 4, 16])
        self.assertTrue(all(13 * math.sqrt(value / 16) >= 1 for value in refs))
        self.assertTrue(
            all(abs(13 * math.sqrt(a / 16) - 13 * math.sqrt(b / 16)) >= 1 for a, b in itertools.combinations(refs, 2))
        )

    def test_scientific_colorbar_ticks_stay_distinct_and_inside_bar(self):
        for lo, hi in ((1e-14, 3e-14), (-3e-14, 2e-14), (1e-14, 1.0002e-14), (1e9, 1e9 + 2)):
            with self.subTest(lo=lo, hi=hi):
                svg = make_ternary(
                    [{"a": 0.8, "b": 0.1, "c": 0.1, "value": lo}, {"a": 0.1, "b": 0.8, "c": 0.1, "value": hi}]
                )
                root = ET.fromstring(svg)
                namespace = "{http://www.w3.org/2000/svg}"
                bar = next(
                    e
                    for e in root.findall(".//" + namespace + "rect")
                    if e.attrib.get("fill") == "none" and e.attrib.get("width") == "15.0"
                )
                x, y, w, h = (float(bar.attrib[k]) for k in ("x", "y", "width", "height"))
                lines = [
                    e
                    for e in root.findall(".//" + namespace + "line")
                    if abs(float(e.attrib["x1"]) - (x + w)) < 0.11 and abs(float(e.attrib["x2"]) - (x + w + 4)) < 0.11
                ]
                texts = [
                    e
                    for e in root.findall(".//" + namespace + "text")
                    if abs(float(e.attrib["x"]) - (x + w + 6)) < 0.11
                ]
                values = [float("".join(e.itertext()).replace(",", "")) for e in texts]
                self.assertGreaterEqual(len(values), 2)
                self.assertEqual(len(values), len(set(values)))
                self.assertEqual(len(lines), len(values))
                domain = (-max(abs(lo), abs(hi)), max(abs(lo), abs(hi))) if lo < 0 < hi else (lo, hi)
                for line, value in zip(lines, values):
                    tick_y = float(line.attrib["y1"])
                    self.assertGreaterEqual(tick_y, y - 0.11)
                    self.assertLessEqual(tick_y, y + h + 0.11)
                    expected_y = y + h - h * (value - domain[0]) / (domain[1] - domain[0])
                    self.assertAlmostEqual(tick_y, expected_y, delta=0.11)
                self.assert_text_clear(svg)

    def test_long_multilingual_labels_do_not_overlap_or_leave_canvas(self):
        font = "Arial, PingFang SC, sans-serif"
        cases = [
            make_ternary(
                [
                    {"a": 0.2, "b": 0.3, "c": 0.5, "value": 2, "size": 4},
                    {"a": 0.7, "b": 0.2, "c": 0.1, "value": 8, "size": 1},
                ],
                labels=("长组分名称：蛋白质占比", "Lipid component with a long name", "碳水化合物占比"),
                title="A long but readable title for a professional ternary chart",
                value_label="浓度 Concentration",
                size_label="Sample size / 样本量",
                palette="nightlab",
                width=1080,
                height=760,
                font_family=font,
            ),
            make_upset(
                {
                    "转录组测序结果：第一批实验样本": range(20),
                    "Proteomics validation cohort with an intentionally long name": range(10, 30),
                    "单细胞检测的高置信度候选集合": range(15, 35),
                },
                width=1200,
                height=820,
                font_family=font,
            ),
        ]
        for svg in cases:
            self.assert_text_clear(svg)
