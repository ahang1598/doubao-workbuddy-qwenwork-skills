"""Composite / heterogeneous panels, radar & chord, and clinical panels."""

import json
import math
import unittest
import xml.etree.ElementTree as ET
import sys
from copy import deepcopy
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from embed_svg_validator import detect_embedded_svg_overlaps, validate_embedded_svgs

from ._helpers import nodes, nodes as elements, nodes as role
from ..charts._chart_layout import ChartLayout
from ..charts._composition import render_bar_plot, scale_from
from ..charts._xy import normalize_series, _clip_segment
from ..charts.composite import _auc, make_composite
from ..charts.composite_matrix import MatrixPlot
from ..charts._academic_rigor import BBox
from ..charts._categorical import sample_summary
from ..charts._composition_panels import _connections, _prepare
from ..charts.pairs import correlation
from ..charts.volcano import classify_volcano
from ..charts.radar import make_radar
from ..charts.sankey import draw_sankey, make_sankey
from ..charts.swimmer import make_swimmer, render_swimmer_plot, swimmer_height, swimmer_state


# ====================================================================================================
# Semantic and coordinate invariants for public scientific compositions.
# ====================================================================================================


def layout_data(svg, value):
    return json.loads(role(svg, value)[0].get("data-layout"))


class CompositionTests(unittest.TestCase):
    def series(self):
        return [
            {"name": "A", "color": "#112233", "points": [(1, 2), (2, 4), (4, 7)]},
            {"name": "B", "points": [(1, 3), (3, 4), (4, 6)]},
        ]

    def test_shared_facets_domains_and_x_pixel_alignment(self):
        single = make_composite([{"name": "A", "series": self.series()}])
        self.assertEqual(single.count("<svg"), 1)  # composed from fragments, not finished SVGs
        self.assertNotIn('transform="translate', single)
        data = [{"name": "First", "series": self.series()}, {"name": "Second", "series": list(reversed(self.series()))}]
        svg = make_composite(data)
        boxes = layout_data(svg, "facets-layout")
        self.assertEqual(boxes[0]["x_domain"], boxes[1]["x_domain"])
        self.assertEqual(boxes[0]["y_domain"], boxes[1]["y_domain"])
        points = role(svg, "observation")
        self.assertTrue(points)
        for name in ["A", "B"]:
            colors = {p.get("fill") for p in points if p.get("data-series") == name}
            self.assertEqual(len(colors), 1)
        svg = make_composite(
            [{"name": "One", "series": [self.series()[0]]}, {"name": "Two", "series": [self.series()[0]]}], cols=1
        )
        boxes = layout_data(svg, "facets-layout")
        self.assertEqual(boxes[0]["bbox"][0::2], boxes[1]["bbox"][0::2])
        groups = role(svg, "facet")
        px = [[p.get("cx") for p in role(g, "observation")] for g in groups]
        self.assertEqual(px[0], px[1])

    def test_free_axes_and_ci_pvalues(self):
        svg = make_composite(
            [
                {
                    "name": "One",
                    "pvalue": 0.031,
                    "series": [
                        {
                            "name": "A",
                            "points": [(1, 2), (2, 4), (3, 6)],
                            "curve": [{"x": 1, "y": 2, "lo": 1, "hi": 3}, {"x": 3, "y": 6, "lo": 5, "hi": 7}],
                        }
                    ],
                },
                {"name": "Two", "pvalue": 0.73, "series": [{"name": "A", "points": [(10, 20), (20, 40)]}]},
            ],
            share_x=False,
            share_y=False,
        )
        boxes = layout_data(svg, "facets-layout")
        self.assertNotEqual(boxes[0]["x_domain"], boxes[1]["x_domain"])
        self.assertTrue(role(svg, "confidence-band"))
        self.assertIn("P = 0.031", svg)
        self.assertIn("P = 0.73", svg)

    def test_colour_values_and_bubble_areas_are_global(self):
        svg = make_composite(
            [
                {
                    "name": str(i),
                    "series": [
                        {
                            "name": "A",
                            "points": [{"x": 1, "y": 2, "color_value": 1 + i}, {"x": 2, "y": 3, "color_value": 2}],
                        }
                    ],
                }
                for i in range(2)
            ]
        )
        points = role(svg, "observation")
        self.assertEqual(points[1].get("fill"), points[2].get("fill"))
        self.assertEqual(points[1].get("fill"), points[3].get("fill"))
        svg = make_composite(
            [
                {
                    "name": str(i),
                    "series": [
                        {"name": "A", "points": [{"x": 1, "y": 2, "size": 4}, {"x": 2, "y": 3, "size": 16 if i else 4}]}
                    ],
                }
                for i in range(2)
            ]
        )
        points = role(svg, "observation")
        radii = [float(p.get("r")) for p in points]
        self.assertEqual(radii[0], radii[2])
        self.assertAlmostEqual(radii[3] ** 2 / radii[0] ** 2, 4)

    def test_log_linear_domain_and_offset_multiplier(self):
        series = [{"name": "A", "points": [(1, 2), (10, 3), (100, 4)]}]
        svg = make_composite([{"name": mode, "x_transform": mode, "series": series} for mode in ("linear", "log10")])
        boxes = layout_data(svg, "facets-layout")
        self.assertEqual(boxes[0]["x_domain"], boxes[1]["x_domain"])
        self.assertGreater(boxes[1]["x_domain"][0], 0)
        self.assertEqual(boxes[1]["x_transform"], "log10")
        svg = make_composite(
            [{"name": "Precision", "series": [{"name": "A", "points": [(1e12 + i, i * 1e-10) for i in range(4)]}]}]
        )
        self.assertIn("offset", svg)
        self.assertIn("×", svg)

    def test_auc_intervals_and_duplicate_x(self):
        s = normalize_series(
            [
                {"name": "A", "points": [(0, 1), (1, 3), (3, 7)], "curve": [(0, 2), (1, 2), (3, 2)]},
                {"name": "B", "points": [(1, 5), (3, 5)], "curve": [(1, 10), (2, 10), (3, 10)]},
            ]
        )
        raw, bounds = _auc(s, "points")
        predicted, _ = _auc(s, "curve")
        self.assertEqual(bounds, (1, 3))
        self.assertEqual([b["value"] for b in raw], [10, 10])
        self.assertEqual([b["value"] for b in predicted], [4, 20])
        with self.assertRaisesRegex(ValueError, "extrapolation"):
            _auc(s, "curve", (0, 3))
        bars, interval = _auc(normalize_series([{"name": "A", "points": [(0, 1), (1, 3), (3, 7)]}]), "points")
        self.assertEqual(interval, (0, 3))  # nonuniform sample times
        self.assertAlmostEqual(bars[0]["value"], 12)
        s = normalize_series([{"name": "A", "points": [(1, 2), (1, 3), (2, 4)]}])
        with self.assertRaisesRegex(ValueError, "replicate"):
            _auc(s, "points")

    def test_bars_zero_negative_starts_and_discontinuous_intervals(self):
        records = [{"name": "A", "value": -2, "lo": -3, "hi": -1}, {"name": "B", "value": 0}]
        scale = scale_from([-3, 0], zero=True)
        fragment = render_bar_plot(records, (0, 0, 300, 200), scale=scale, colors={"A": "#112233", "B": "#445566"})
        bars = role("<svg>" + fragment + "</svg>", "bar")
        self.assertEqual(float(bars[1].get("height")), 0)
        self.assertTrue(role("<svg>" + fragment + "</svg>", "bar-interval"))

        class Broken:
            domain = (0, 100)
            transform = "linear"
            visible_intervals = ((0, 10), (90, 100))

            def map(self, value, p0, p1):
                if 10 < value < 90:
                    raise AssertionError("renderer attempted to map a hidden value")
                span = abs(p1 - p0) - 18
                distance = value / 20 * span if value <= 10 else (value - 80) / 20 * span + 18
                return p0 + (1 if p1 >= p0 else -1) * distance

        svg = (
            "<svg>"
            + render_bar_plot(
                [{"name": "A", "start": 5, "value": 95, "lo": 8, "hi": 98}],
                (0, 0, 200, 200),
                scale=Broken(),
                colors={"A": "#112233"},
            )
            + "</svg>"
        )
        bars = role(svg, "bar")
        self.assertEqual(len(bars), 2)
        self.assertAlmostEqual(float(bars[0].get("height")), 45.5)
        self.assertAlmostEqual(float(bars[1].get("height")), 45.5)
        errors = role(svg, "bar-interval")
        self.assertEqual(len(errors), 2)
        self.assertEqual(sum(node.get("d").count(" h6") for node in errors), 2)

    def test_tracks_row_order_and_unknown_or_duplicate_ids(self):
        data = {
            "rows": ["A", "B", "C"],
            "tracks": [
                {
                    "name": "Intervals",
                    "kind": "interval",
                    "records": [{"row_id": "C", "value": 3}, {"row_id": "A", "value": 1}, {"row_id": "B", "value": 2}],
                },
                {
                    "name": "Bars",
                    "kind": "bar",
                    "records": [{"row_id": "B", "value": 2}, {"row_id": "C", "value": 3}, {"row_id": "A", "value": 1}],
                },
            ],
        }
        svg = make_composite(data, template="tracks")
        boxes = layout_data(svg, "tracks-layout")
        self.assertEqual(boxes[0]["row_centers"], boxes[1]["row_centers"])
        centers = boxes[0]["row_centers"]
        for node in role(svg, "track-point"):
            self.assertAlmostEqual(float(node.get("cy")), centers[node.get("data-row-id")], places=2)
        for node in role(svg, "bar"):
            self.assertAlmostEqual(
                float(node.get("y")) + float(node.get("height")) / 2, centers[node.get("data-row-id")], places=2
            )
        with self.assertRaisesRegex(ValueError, "unknown row_id"):
            make_composite({"rows": ["A"], "tracks": [{"records": [{"row_id": "B", "value": 1}]}]}, template="tracks")
        with self.assertRaisesRegex(ValueError, "unique"):
            make_composite({"rows": ["A", "A"], "tracks": []}, template="tracks")

    def test_matrix_line_centres_missing_mean_and_inset(self):
        data = {
            "matrix": [[1, 2, 3, 4], [2, 3, 4, 5]],
            "col_labels": ["1", "2", "5", "11"],
            "col_positions": [1, 2, 5, 11],
            "line": {"statistic": "mean"},
        }
        svg = make_composite(data, template="heatmap")
        geom = layout_data(svg, "matrix-composition-layout")[0]
        points = role(svg, "matrix-line-point")
        self.assertEqual(geom["line_values"], [1.5, 2.5, 3.5, 4.5])
        for point, x in zip(points, geom["column_centers"]):
            self.assertAlmostEqual(float(point.get("cx")), x, places=2)
        distances = [geom["column_centers"][i + 1] - geom["column_centers"][i] for i in range(3)]
        self.assertAlmostEqual(distances[1] / distances[0], 3)
        self.assertAlmostEqual(distances[2] / distances[0], 6)
        data = {
            "matrix": [[1, None, 3], [-1, None, 5]],
            "mask": [[False, False, True], [False, False, False]],
            "line": {"statistic": "mean"},
        }
        svg = make_composite(data, template="heatmap")
        self.assertEqual(layout_data(svg, "matrix-composition-layout")[0]["line_values"], [0, None, 5])
        self.assertEqual(len(role(svg, "matrix-line-point")), 2)
        self.assertTrue(any(c.get("data-value") == "-1.0" for c in role(svg, "matrix-cell")))
        data = {
            "matrix": [[i + j for j in range(8)] for i in range(6)],
            "row_labels": list("ABCDEF"),
            "col_labels": [str(i) for i in range(8)],
            "inset": {"rows": ["B", "C"], "columns": ["2", "3"]},
        }
        svg = make_composite(data, template="heatmap")
        geom = layout_data(svg, "matrix-composition-layout")[0]
        main, inset = geom["bbox"], geom["inset_bbox"]
        self.assertGreater((inset[2] - inset[0]) / 2, (main[2] - main[0]) / 8)
        self.assertGreater((inset[3] - inset[1]) / 2, (main[3] - main[1]) / 6)
        main_cells = role(role(svg, "matrix-plot")[0], "matrix-cell")
        crop_cells = role(role(svg, "matrix-inset")[0], "matrix-cell")
        originals = {(c.get("data-row-id"), c.get("data-column")): c for c in main_cells}
        for c in crop_cells:
            original = originals[(c.get("data-row-id"), c.get("data-column"))]
            self.assertEqual(c.get("data-value"), original.get("data-value"))
            self.assertEqual(next(iter(c)).get("fill"), next(iter(original)).get("fill"))

    def test_split_matrix_order_scales_and_explicit_mixing(self):
        layout = ChartLayout(1000, 700, "archive_ink", None)
        state = MatrixPlot(
            {
                "matrix": [[1, 2, 3], [4, 5, 6], [7, 8, 9]],
                "upper_matrix": [[10, 11, 12], [13, 14, 15], [16, 17, 18]],
                "row_order": [2, 0, 1],
                "col_order": [2, 0, 1],
            },
            layout.pal,
            layout.font,
        )
        self.assertEqual((state.scale.low, state.scale.high), (1, 9))
        self.assertEqual((state.upper_scale.low, state.upper_scale.high), (11, 17))
        data = {"matrix": [[1, 2], [3, 4]], "upper_matrix": [[10, 20], [30, 40]], "line": {"statistic": "mean"}}
        svg = make_composite(data, template="heatmap", x_title="Sequence position", y_title="Residue", x_unit="bp")
        self.assertEqual(layout_data(svg, "matrix-composition-layout")[0]["line_values"], [2, 3])
        data["line"]["source"] = "upper"
        svg = make_composite(data, template="heatmap")
        self.assertEqual(layout_data(svg, "matrix-composition-layout")[0]["line_values"], [20, 30])

    def test_bottom_tree_same_leaf_ids(self):
        tree = {"order": [2, 3, 0, 1], "linkage": [(0, 1, 1, 2), (2, 3, 1, 2), (5, 4, 2, 4)]}
        svg = make_composite(
            {
                "matrix": [[1 if i == j else 0.2 for j in range(4)] for i in range(4)],
                "top_tree": tree,
                "bottom_tree": tree,
            },
            template="heatmap",
        )
        self.assertEqual({t.get("data-side") for t in role(svg, "dendrogram")}, {"top", "bottom"})
        self.assertEqual(layout_data(svg, "matrix-composition-layout")[0]["col_order"], [2, 3, 0, 1])

    def test_labels_and_required_layout_gates(self):
        labels = ["长中文样本标签与完整含义 preserved text " + str(i) for i in range(4)]
        data = [
            {
                "name": "All retained",
                "series": [
                    {"name": "Group", "points": [{"x": i, "y": i, "label": label} for i, label in enumerate(labels)]}
                ],
            }
        ]
        svg = make_composite(data, width=700, height=300)
        # Labels may wrap into multiple text elements; no source text disappears.
        text = "".join(ET.fromstring(svg).itertext()).replace(" ", "")
        for label in labels:
            self.assertIn(label.replace(" ", ""), text)
        root = ET.Element("slide")
        embed = ET.SubElement(root, "embed", id="test")
        embed.append(ET.fromstring(svg))
        self.assertEqual(validate_embedded_svgs(root) + detect_embedded_svg_overlaps(root), [])

    def test_grouped_dot_tracks_use_separate_lanes_with_global_area(self):
        tracks = [
            {
                "name": str(n),
                "kind": "dots",
                "columns": ["X", "Y"],
                "records": [
                    {"row_id": "A", "column": c, "group": g, "size": s}
                    for c in ["X", "Y"]
                    for g, s in [("G1", 1), ("G2", 4)]
                ],
            }
            for n in range(2)
        ]
        svg = make_composite({"rows": ["A"], "tracks": tracks}, template="tracks")
        dots = role(svg, "track-dot")
        self.assertEqual(len(dots), 8)
        self.assertEqual(len({node.get("cx") for node in dots}), 8)
        self.assertEqual({float(node.get("r")) for node in dots if node.get("data-group") == "G1"}, {6.0})
        self.assertEqual({float(node.get("r")) for node in dots if node.get("data-group") == "G2"}, {12.0})

    def test_invalid_nonfinite_and_nonpositive(self):
        for value in (math.inf, math.nan):
            with self.assertRaises(ValueError):
                make_composite([{"series": [{"points": [(1, value)]}]}])
        with self.assertRaises(ValueError):
            make_composite([{"x_transform": "log10", "series": [{"points": [(0, 1), (1, 2)]}]}])


# ====================================================================================================
# Heterogeneous composition, shared-axis and true-anchor regression tests.
# ====================================================================================================


def geometry(svg):
    return json.loads(nodes(svg, "heterogeneous-panels-layout")[0].get("data-layout"))


def network():
    return {
        "id": "network",
        "kind": "network",
        "data": {
            "nodes": [{"id": n, "label": n, "size": i + 1} for i, n in enumerate(["A", "B", "C"])],
            "edges": [
                {"source": "A", "target": "B", "correlation": 0.5, "pvalue": 0.01},
                {"source": "B", "target": "C", "correlation": -0.4, "pvalue": 0.2},
            ],
        },
    }


class PanelsTests(unittest.TestCase):
    def xy(self, name, offset=0, **extra):
        return {
            "id": name,
            "name": name,
            "kind": "xy",
            "data": {
                "series": [
                    {
                        "name": "Signal",
                        "points": [{"x": i + offset, "y": 2 * i + offset, "id": str(i)} for i in range(1, 5)],
                    }
                ]
            },
            **extra,
        }

    def test_panel_axes_independent_shared_groups_and_unit_agreement(self):
        svg = make_composite([self.xy("a"), self.xy("b", 100)], template="panels")
        axes = [p["axes"] for p in geometry(svg)["panels"]]
        self.assertNotEqual(axes[0]["x"]["domain"], axes[1]["x"]["domain"])
        self.assertNotEqual(axes[0]["y"]["domain"], axes[1]["y"]["domain"])
        svg = make_composite(
            [self.xy("a", x_group="exposure"), self.xy("b", 100, x_group="exposure")], template="panels"
        )
        axes = [p["axes"] for p in geometry(svg)["panels"]]
        self.assertEqual(axes[0]["x"]["domain"], axes[1]["x"]["domain"])
        self.assertNotEqual(axes[0]["y"]["domain"], axes[1]["y"]["domain"])
        a, b = self.xy("a", x_group="value"), self.xy("b", x_group="value")
        a["data"]["x_unit"] = "mg"
        b["data"]["x_unit"] = "seconds"
        with self.assertRaisesRegex(ValueError, "consistent units"):
            make_composite([a, b], template="panels")
        b["data"]["x_unit"] = "mg"
        b["data"]["x_transform"] = "log10"
        with self.assertRaisesRegex(ValueError, "transforms"):
            make_composite([a, b], template="panels")

    def test_volcano_uses_real_classifier_and_threshold(self):
        data = {
            "points": [
                {"name": "High", "log2fc": 2, "neg_log10_p": 4},
                {"name": "Below", "log2fc": 1.01, "neg_log10_p": 2},
                {"name": "Down", "log2fc": -2, "neg_log10_p": 4},
            ],
            "threshold": {"s0": 0.5},
            "top_k_labels": 3,
        }
        expected, _, _ = classify_volcano(data["points"], threshold=data["threshold"])
        panel = _prepare({"id": "v", "kind": "volcano", "data": data}, ChartLayout(1200, 900, "archive_ink", None), 0)
        counts = {s["name"]: len(s["points"]) for s in panel["series"]}
        names = {"ns": "Not significant", "up": "Upregulated", "down": "Downregulated"}
        self.assertEqual(
            counts, {names[c]: sum(p["category"] == c for p in expected) for c in {p["category"] for p in expected}}
        )
        svg = make_composite([{"id": "v", "kind": "volcano", "data": data}, network()], template="panels")
        self.assertEqual(len(nodes(svg, "observation")), 3)
        self.assertTrue(nodes(svg, "curve"))
        self.assertIn("High", svg)

    def test_connections_attach_reject_unknown_and_avoid_text(self):
        matrix = {
            "id": "matrix",
            "kind": "heatmap",
            "data": {
                "matrix": [[1, 2], [3, 4]],
                "row_labels": ["A", "B"],
                "col_labels": ["X", "Y"],
                "row_order": [1, 0],
            },
        }
        edge = {
            "source": {"panel": "matrix", "anchor": "row", "id": "A"},
            "target": {"panel": "network", "id": "A"},
            "correlation": -0.7,
            "pvalue": 0.08,
        }
        svg = make_composite({"panels": [matrix, network()], "connections": [edge]}, template="panels")
        geo = geometry(svg)
        panels = {p["id"]: p for p in geo["panels"]}
        connection = geo["connections"][0]
        self.assertEqual(connection["route"][0], panels["matrix"]["anchors"]["row/A"][:2])
        self.assertEqual(connection["route"][-1], panels["network"]["anchors"]["node/A"][:2])
        self.assertGreater(panels["matrix"]["anchors"]["row/A"][1], panels["matrix"]["anchors"]["row/B"][1])
        self.assertEqual(connection["correlation"], -0.7)
        self.assertEqual(connection["pvalue"], 0.08)
        self.assertTrue(nodes(svg, "panel-connections"))
        with self.assertRaisesRegex(ValueError, "unknown connection anchor"):
            make_composite(
                {
                    "panels": [network()],
                    "connections": [
                        {"source": {"panel": "network", "id": "absent"}, "target": {"panel": "network", "id": "A"}}
                    ],
                },
                template="panels",
            )
        for reverse in (False, True):
            canvas = ChartLayout(500, 320, "archive_ink", None)
            canvas.text("Protected long label", 175, 140, fs=20)
            contexts = {
                "left": {"anchors": {("node", "A"): (40, 150, 0)}},
                "right": {"anchors": {("node", "B"): (460, 150, 0)}},
            }
            source = {"panel": "left", "id": "A"}
            target = {"panel": "right", "id": "B"}
            if reverse:
                source, target = target, source
            connection = _connections(
                canvas, [{"source": source, "target": target, "weight": 1}], contexts, 0, BBox(10, 70, 490, 250)
            )[0]
            route = connection["route"]
            self.assertGreater(len(route), 2)
            self.assertEqual(route[0], (460, 150) if reverse else (40, 150))
            self.assertEqual(route[-1], (40, 150) if reverse else (460, 150))
            obstacle = BBox(*canvas.text_boxes[0][:4])
            for i in range(1, len(route)):
                self.assertIsNone(_clip_segment(route[i - 1], route[i], obstacle))

    def test_pairs_statistics_observations_and_variable_anchor(self):
        records = [{"x": i, "y": i // 2, "z": 5 - i} for i in range(1, 6)]
        data = {"records": records, "variables": ["x", "y", "z"], "method": "spearman"}
        svg = make_composite([{"id": "pairs", "kind": "pairs", "data": data}, network()], template="panels")
        cells = nodes(svg, "correlation-value")
        self.assertEqual(len(cells), 3)
        expected = correlation([r["x"] for r in records], [r["y"] for r in records], "spearman")
        self.assertTrue(any(math.isclose(float(c.get("data-value")), expected) for c in cells))
        self.assertEqual(len(nodes(svg, "observation")), 15)
        self.assertEqual(sum(int(n.get("data-count")) for n in nodes(svg, "marginal-count")), 15)
        pair = {"id": "pairs", "kind": "pairs", "data": {"records": [{"x": i, "y": i * i} for i in range(1, 5)]}}
        svg = make_composite(
            {
                "panels": [pair, network()],
                "connections": [
                    {
                        "source": {"panel": "pairs", "anchor": "variable", "id": "x"},
                        "target": {"panel": "network", "id": "B"},
                        "weight": 2,
                    }
                ],
            },
            template="panels",
        )
        self.assertIn("variable/x", geometry(svg)["panels"][0]["anchors"])

    def test_bar_forest_and_phylogeny_panels_keep_source_records(self):
        values = [1, 2, 5, 6]
        bar = {
            "id": "bar",
            "kind": "bar",
            "data": {"categories": ["C"], "series": [{"name": "Treatment", "values": [values]}], "error_kind": "CI95"},
        }
        svg = make_composite([bar, network()], template="panels")
        expected = sample_summary(values, "CI95")
        self.assertAlmostEqual(float(nodes(svg, "bar")[0].get("data-value")), expected["value"])
        self.assertEqual(len(nodes(svg, "replicate")), len(values))
        self.assertTrue(nodes(svg, "bar-interval"))
        data = {
            "rows": [
                {"row_id": "b", "label": "Beta", "estimate": 2, "ci_lo": 1, "ci_hi": 3, "n": 21, "p": 0.03},
                {"row_id": "a", "label": "Alpha", "estimate": 1, "ci_lo": 0.5, "ci_hi": 1.5, "n": 18, "p": 0.7},
            ],
            "row_order": ["a", "b"],
        }
        svg = make_composite([{"id": "forest", "kind": "forest", "data": data}, network()], template="panels")
        anchors = geometry(svg)["panels"][0]["anchors"]
        self.assertLess(anchors["row/a"][1], anchors["row/b"][1])
        self.assertEqual({c.get("data-row-id") for c in nodes(svg, "table-cell")}, {"a", "b"})
        self.assertEqual(len(nodes(svg, "observation")), 2)
        svg = make_composite(
            [{"id": "tree", "kind": "phylogeny", "data": {"tree": "((A:1,B:2):3,C:4);"}}, network()], template="panels"
        )
        self.assertEqual(sorted(float(n.get("data-display-length")) for n in nodes(svg, "phylo-branch")), [1, 2, 3, 4])
        data = [self.xy("first"), network()]
        before = deepcopy(data)
        svg = make_composite(data, template="panels")
        self.assertEqual(data, before)
        self.assertEqual(svg.count("<svg"), 1)
        self.assertNotIn('transform="translate', svg)

    def test_all_eight_kinds_embed_without_collisions(self):
        panels = [
            self.xy("xy"),
            {
                "id": "volcano",
                "kind": "volcano",
                "data": {
                    "points": [
                        {"name": "A", "log2fc": 2, "neg_log10_p": 3},
                        {"name": "B", "log2fc": -2, "neg_log10_p": 4},
                    ]
                },
            },
            network(),
            {"id": "tree", "kind": "phylogeny", "data": {"tree": "(A:1,B:2,C:1);"}},
            {"id": "matrix", "kind": "heatmap", "data": {"matrix": [[1, 2], [3, 4]]}},
            {"id": "pairs", "kind": "pairs", "data": {"records": [{"x": i, "y": i * i} for i in range(1, 5)]}},
            {
                "id": "bar",
                "kind": "bar",
                "data": {"categories": ["A", "B"], "series": [{"name": "S", "values": [[1, 2], [3, 4]]}]},
            },
            {
                "id": "forest",
                "kind": "forest",
                "data": {"rows": [{"row_id": "a", "label": "Cohort", "estimate": 1, "ci_lo": 0.5, "ci_hi": 2}]},
            },
        ]
        svg = make_composite({"panels": panels, "columns": 2}, template="panels")
        root = ET.Element("slide")
        ET.SubElement(root, "embed", id="eight").append(ET.fromstring(svg))
        self.assertEqual(validate_embedded_svgs(root) + detect_embedded_svg_overlaps(root), [])


# ====================================================================================================
# Embedding contracts for radar and chord charts.
# ====================================================================================================


def validate(svg):
    root = ET.Element("slide")
    ET.SubElement(root, "embed").append(ET.fromstring(svg))
    return validate_embedded_svgs(root)


class RadarAndChordTests(unittest.TestCase):
    def test_radar_ranges_facets_and_missing_profiles(self):
        axes = [
            {"name": "A", "min": 0, "max": 100},
            {"name": "B", "min": -5, "max": 5},
            {"name": "C", "min": 1e12, "max": 1e12 + 4},
        ]
        svg = make_radar(axes, [{"name": "S", "facet": f, "values": [50, 0, 1e12 + 2]} for f in ["I", "II"]])
        radii = [float(e.get("data-radius")) for e in elements(svg, "radar-point")]
        self.assertEqual(len(set(radii)), 1)
        self.assertFalse(validate(svg))
        svg = make_radar([{"name": n, "min": 0, "max": 4} for n in ["a", "b", "c", "d"]], [{"values": [1, None, 2, 3]}])
        for e in elements(svg, "radar-profile"):
            self.assertEqual(e.get("fill"), "none")
            self.assertNotIn("Z", e.get("d"))

    def test_chord_tracks_and_dispatch(self):
        svg = draw_sankey(
            {
                "nodes": ["A", "B", "C"],
                "flows": [("A", "B", 2), ("B", "C", 4)],
                "tracks": [{"name": "T", "values": [1, 2, 3]}],
            },
            variant="chord_circular",
            width=1040,
            height=760,
        )
        self.assertEqual(len(elements(svg, "track-cell")), 3)
        self.assertFalse(validate(svg))
        self.assertIn(">6</text>", svg)
        svg = make_sankey(
            layers=[["A"], ["B"]],
            inter_flows=[[("A", "B", 2)]],
            variant="chord_circular",
            tracks=[{"name": "T", "values": [1, 2]}],
        )
        self.assertEqual(len(elements(svg, "track-cell")), 2)
        self.assertFalse(validate(svg))


# ====================================================================================================
# Clinical one-call composition: exact counts, sites, times and real anchors.
# ====================================================================================================


def issues(svg):
    root = ET.Element("slide")
    ET.SubElement(root, "embed", id="clinical").append(ET.fromstring(svg))
    return validate_embedded_svgs(root) + detect_embedded_svg_overlaps(root)


def patients():
    return [
        {
            "id": "p1",
            "segments": [{"start": -2, "end": 8, "treatment": "A"}, {"start": 0, "end": 12, "treatment": "B"}],
            "events": [{"id": "biopsy", "time": 5, "kind": "Biopsy"}, {"id": "scan", "time": 5, "kind": "Scan"}],
            "followup": {"start": 12, "end": 19, "ongoing": True},
        }
    ]


class ClinicalPanelTests(unittest.TestCase):
    def test_swimmer_times_autoheight_and_exact_segments(self):
        canvas = ChartLayout(900, 1000, "archive_ink", None)
        state = swimmer_state(patients(), canvas)
        body = BBox(20, 30, 860, 30 + swimmer_height(state, canvas, 840))
        context = render_swimmer_plot(canvas, body, state)
        fragments = "".join(canvas.parts)
        self.assertNotIn("<svg", fragments)
        self.assertEqual(context["anchors"][("event", "p1/biopsy")][0], context["anchors"][("event", "p1/scan")][0])
        self.assertNotEqual(context["anchors"][("event", "p1/biopsy")][1], context["anchors"][("event", "p1/scan")][1])
        source = patients() * 1
        source = [dict(p, id=str(i)) for i in range(12) for p in source]
        svg = make_swimmer(source, width=900, height=300)
        self.assertGreater(float(ET.fromstring(svg).get("viewBox").split()[-1]), 300)
        self.assertEqual(
            [(n.get("data-start"), n.get("data-end")) for n in nodes(svg, "treatment")],
            [("-2.0", "8.0"), ("0.0", "12.0")] * 12,
        )
        self.assertEqual([n.get("data-time") for n in nodes(svg, "patient-event")], ["5.0"] * 24)
        self.assertFalse(issues(svg))

    def test_one_call_clinical_three_panels(self):
        data = {
            "panels": [
                {"id": "swim", "kind": "swimmer", "data": {"patients": patients()}},
                {
                    "id": "counts",
                    "kind": "bar",
                    "data": {
                        "categories": ["P1"],
                        "series": [{"name": "A", "values": [{"value": 4}]}, {"name": "B", "values": [{"value": 3}]}],
                        "stack": "stacked",
                    },
                },
                {
                    "id": "paired",
                    "kind": "xy",
                    "data": {
                        "series": [{"name": "P1", "points": [(0, 0.2), (1, 0.3)], "connect": True}],
                        "pvalue": 0.03,
                    },
                },
            ]
        }
        before = deepcopy(data)
        for theme in ("archive_ink", "nightlab"):
            svg = make_composite(data, template="panels", palette=theme)
            self.assertEqual(len(nodes(svg, "heterogeneous-panel")), 3)
            self.assertEqual(len(nodes(svg, "treatment")), 2)
            self.assertEqual(len(nodes(svg, "observation")), 2)
            self.assertIn("P = 0.03", svg)
            self.assertEqual(svg.count("<svg"), 1)
            self.assertFalse(issues(svg))
        self.assertEqual(before, data)

    def test_clinical_time_axis_capacity_title_and_units(self):
        events = [{"time": i, "kind": "Test", "label": "Full event label " + str(i)} for i in range(6)]
        panels = [
            {"id": "a", "kind": "swimmer", "x_group": "clock", "data": {"patients": [{"id": "a", "events": events}]}},
            {
                "id": "b",
                "kind": "swimmer",
                "x_group": "clock",
                "data": {"patients": [{"id": "b", "followup": {"start": 0, "end": 10000}}]},
            },
        ]
        svg = make_composite(panels, template="panels")
        self.assertEqual(len(nodes(svg, "patient-event")), 6)
        self.assertFalse(issues(svg))
        svg = make_swimmer(patients(), height=300, width=720, x_title="Long supplied timing definition " * 12)
        self.assertFalse(issues(svg))
        a = {"id": "a", "kind": "swimmer", "x_group": "time", "data": {"patients": patients(), "time_unit": "months"}}
        b = {"id": "b", "kind": "swimmer", "x_group": "time", "data": {"patients": patients(), "time_unit": "days"}}
        with self.assertRaisesRegex(ValueError, "consistent units"):
            make_composite([a, b], template="panels")
        with self.assertRaisesRegex(ValueError, "no shareable"):
            make_composite([dict(network(), x_group="x")], template="panels")
