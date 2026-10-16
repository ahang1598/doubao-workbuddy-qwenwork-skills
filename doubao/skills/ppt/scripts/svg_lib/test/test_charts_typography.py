"""Chart typography across XY, composition, distribution, matrix and spatial charts."""

import unittest
import xml.etree.ElementTree as ET
import math
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from embed_svg_validator import detect_embedded_svg_overlaps, validate_embedded_svgs

from ._helpers import nodes
from ..charts._categorical import make_categorical
from ..charts.composite import make_composite
from ..charts.line_band import make_line_band
from ..charts.scatter_fit import make_scatter
from ..charts._chart_layout import ChartLayout
from ..charts._distribution_panels import finalize_distribution_panel, prepare_distribution_panel
from ..charts.boxplot import make_boxplot
from ..charts.dumbbell import make_dumbbell
from ..charts.matrix_heat import make_matrix_heat
from ..charts.ridge import make_ridge
from ..charts.violin import make_violin
from ..charts.network import make_network
from ..charts.radar import make_radar
from ..charts.swimmer import make_swimmer
import json


# ====================================================================================================
# User-visible typography density contracts and preserved scientific records.
# ====================================================================================================


def sizes(svg, role):
    return {float(node.get("font-size")) for node in nodes(svg, role)}


def gate(svg):
    root = ET.Element("slide")
    ET.SubElement(root, "embed", id="typography").append(ET.fromstring(svg))
    return validate_embedded_svgs(root) + detect_embedded_svg_overlaps(root)


def observations(n, labels=False):
    return [
        {"x": i + 1, "y": 2 * i + (i % 3), **({"label": "Sample " + str(i + 1)} if labels and i < 3 else {})}
        for i in range(n)
    ]


class TypographyXYCompositionTests(unittest.TestCase):
    def test_sparse_axes_and_point_labels_grow_without_losing_samples(self):
        sparse = make_scatter(observations(3, True), x_title="Exposure", y_title="Response", multi_mode="single")
        dense = make_scatter(observations(30, True), x_title="Exposure", y_title="Response", multi_mode="single")
        for role in ("x-tick", "y-tick", "point-label"):
            self.assertGreater(min(sizes(sparse, role)), max(sizes(dense, role)))
        for n, svg in ((3, sparse), (30, dense)):
            self.assertEqual(len(nodes(svg, "observation")), n)
            self.assertEqual(gate(svg), [])
        for label in ("Exposure", "Response"):

            def text_size(svg, label=label):
                return next(float(node.get("font-size")) for node in ET.fromstring(svg).iter() if node.text == label)

            self.assertGreater(text_size(sparse), text_size(dense))

    def test_curve_sampling_does_not_shrink_type_or_create_observations(self):
        def svg(n):
            return make_line_band([{"name": "Prediction", "curve": [(i / (n - 1), i / (n - 1) + 1) for i in range(n)]}])

        low, high = svg(3), svg(401)
        for role in ("x-tick", "y-tick"):
            self.assertEqual(sizes(low, role), sizes(high, role))
            self.assertGreaterEqual(min(sizes(high, role)), 23)
        self.assertFalse(nodes(high, "observation"))
        self.assertEqual(len(nodes(high, "curve")), 400)

    def test_categories_ignore_replicate_volume_but_shrink_with_more_categories(self):
        def svg(ncat, reps):
            return make_categorical(
                ["C" + str(i) for i in range(ncat)],
                [{"name": "Treatment", "values": [[i + j / 10 + 1 for j in range(reps)] for i in range(ncat)]}],
            )

        sparse, replicated, dense = svg(3, 3), svg(3, 30), svg(30, 3)
        self.assertEqual(sizes(sparse, "y-tick"), sizes(replicated, "y-tick"))
        self.assertGreater(min(sizes(sparse, "y-tick")), max(sizes(dense, "y-tick")))
        self.assertEqual(len(nodes(replicated, "bar")), 3)
        for chart in (sparse, replicated, dense):
            self.assertEqual(gate(chart), [])

    def test_facets_measure_each_panel_density_independently_and_keep_shared_axes_aligned(self):
        panels = [
            {"name": "Sparse", "series": [{"name": "A", "points": observations(3)}]},
            {"name": "Dense", "series": [{"name": "A", "points": observations(30)}]},
        ]
        for cols, axis, coord in ((2, 1, "cy"), (1, 0, "cx")):  # side by side share y; stacked share x
            svg = make_composite(panels, cols=cols)
            metadata = json.loads(nodes(svg, "facets-layout")[0].get("data-layout"))
            self.assertEqual(metadata[0]["bbox"][axis::2], metadata[1]["bbox"][axis::2])
            sparse, dense = nodes(svg, "facet")
            self.assertEqual(
                [node.get(coord) for node in nodes(sparse, "observation")],
                [node.get(coord) for node in nodes(dense, "observation")][:3],
            )
            if cols == 2:
                self.assertGreater(min(sizes(sparse, "x-tick")), max(sizes(dense, "x-tick")))
                self.assertGreater(min(sizes(sparse, "y-tick")), max(sizes(dense, "y-tick")))
                self.assertEqual(len(nodes(svg, "observation")), 33)
                self.assertEqual(gate(svg), [])

    def test_global_footer_font_does_not_depend_on_last_facet_density(self):
        panels = [
            {"name": "Sparse", "series": [{"name": "A", "points": observations(3)}]},
            {"name": "Dense", "series": [{"name": "A", "points": observations(30)}]},
        ]
        note = "Global source note"
        sizes_found = []
        for order in (panels, list(reversed(panels))):
            svg = make_composite(order, cols=2, note=note)
            self.assertEqual(gate(svg), [])
            sizes_found.append(next(node.get("font-size") for node in ET.fromstring(svg).iter() if node.text == note))
        self.assertEqual(*sizes_found)


# ====================================================================================================
# Sparse category typography stays readable without changing data semantics.
# ====================================================================================================


def text_sizes(svg, text):
    return [
        float(node.get("font-size"))
        for node in ET.fromstring(svg).iter()
        if node.tag.endswith("text") and "".join(node.itertext()) == text
    ]


class DistributionMatrixTypography(unittest.TestCase):
    def assert_valid(self, svg):
        slide = ET.fromstring(f"<slide><embed>{svg}</embed></slide>")
        self.assertEqual(validate_embedded_svgs(slide), [])
        self.assertEqual(detect_embedded_svg_overlaps(slide), [])

    def test_two_groups_remain_sparse_with_500_samples_each(self):
        def draw(n):
            return make_boxplot(
                [
                    ("Control", [math.sin(i) + i / n for i in range(n)]),
                    ("Treatment", [math.cos(i) + 1 + i / n for i in range(n)]),
                ],
                width=1200,
                show_jitter=False,
                multi_mode="single",
                y_title="Response",
            )

        sparse, many = draw(5), draw(500)
        self.assertEqual(text_sizes(sparse, "Control"), text_sizes(many, "Control"))
        self.assertGreaterEqual(text_sizes(sparse, "Control")[0], 22)
        self.assertGreater(text_sizes(sparse, "Response")[0], text_sizes(sparse, "Control")[0])
        self.assertIn("n = 500", many)
        self.assert_valid(many)

    def test_dense_groups_and_small_canvas_use_smaller_type(self):
        sparse = make_boxplot([("A", [1, 2, 3]), ("B", [2, 3, 4])], width=1200, multi_mode="single")
        dense = make_boxplot([(f"G{i}", [i, i + 1, i + 2]) for i in range(30)], width=1200, multi_mode="single")
        small = make_boxplot([("A", [1, 2, 3]), ("B", [2, 3, 4])], width=640, multi_mode="single")
        self.assertLess(text_sizes(dense, "G0")[0], text_sizes(sparse, "A")[0])
        self.assertLess(text_sizes(small, "A")[0], text_sizes(sparse, "A")[0])
        for svg in (sparse, dense, small):
            self.assert_valid(svg)
        labels = {"".join(n.itertext()) for n in ET.fromstring(dense).iter() if n.tag.endswith("text")}
        self.assertTrue({f"G{i}" for i in range(30)} <= labels)

    def test_sparse_matrix_labels_and_values_enlarge_and_preserve_values(self):
        svg = make_matrix_heat(
            [[1, 2], [3, 4]], labels=["A", "B"], width=1200, height=800, show_row_mean=False, show_col_mean=False
        )
        self.assertGreaterEqual(text_sizes(svg, "A")[0], 22)
        self.assertGreaterEqual(text_sizes(svg, "1")[0], 22)
        values = [n.get("data-value") for n in ET.fromstring(svg).iter() if n.get("data-row") is not None]
        self.assertEqual(values, ["1.0", "2.0", "3.0", "4.0"])
        self.assert_valid(svg)

    def test_default_matrix_means_reserve_their_full_labels(self):
        svg = make_matrix_heat([[1, 0.4, -0.7], [0.4, 1, 0.2], [-0.7, 0.2, 1]], labels=["A", "B", "C"])
        self.assertIn("Col mean", "".join(ET.fromstring(svg).itertext()))
        self.assert_valid(svg)

    def test_distribution_panel_uses_its_own_width_and_visible_categories(self):
        canvas = ChartLayout(1200, 800, None, None)

        def fonts(width, n):
            data = {"groups": [("A", list(range(n))), ("B", list(range(1, n + 1)))], "show_points": False}
            panel = {"kind": "violin", "data": data, **prepare_distribution_panel("violin", data, canvas)}
            finalize_distribution_panel(panel, canvas, width)
            return panel["_fonts"]

        self.assertEqual(fonts(560, 5), fonts(560, 500))
        self.assertLess(fonts(560, 5)["group"], fonts(1100, 5)["group"])

    def test_dense_matrix_keeps_all_row_and_column_labels(self):
        n = 30
        svg = make_matrix_heat(
            [[float((i + j) % 5) for j in range(n)] for i in range(n)],
            labels=[f"C{i}" for i in range(n)],
            width=1200,
            height=800,
            show_row_mean=False,
            show_col_mean=False,
        )
        self.assertLess(text_sizes(svg, "C0")[0], 20)
        self.assertEqual(len([e for e in ET.fromstring(svg).iter() if e.get("data-row") is not None]), n * n)
        for i in range(n):
            self.assertEqual(len(text_sizes(svg, f"C{i}")), 2)
        self.assert_valid(svg)

    def test_long_labels_wrap_without_losing_words(self):
        names = ["Long treatment name alpha", "Very long control category beta"]
        svg = make_violin(
            [(names[0], [1, 2, 3]), (names[1], [2, 3, 5])], width=640, y_axis_label="Measured response concentration"
        )
        text = " ".join(ET.fromstring(svg).itertext())
        for name in names:
            self.assertIn(name, text)
        self.assert_valid(svg)

    def test_sparse_comparison_and_ridge_family_use_shared_density_policy(self):
        groups = [("Control", [1, 2, 3]), ("Treatment", [2, 4, 5])]
        ridge = make_ridge(groups, width=1200, x_unit="Response")
        dumbbell = make_dumbbell(
            [{"label": name, "before": values[0], "after": values[-1]} for name, values in groups],
            width=1200,
            x_title="Response",
        )
        self.assertGreaterEqual(text_sizes(ridge, "Control")[0], 22)
        self.assertGreaterEqual(text_sizes(dumbbell, "Control")[0], 22)
        for svg in (ridge, dumbbell):
            self.assert_valid(svg)


# ====================================================================================================
# Visible spatial labels scale with density and retain their measured layout.
# ====================================================================================================


def text_size(svg, label):
    return max(
        float(n.get("font-size")) for n in ET.fromstring(svg).iter() if n.tag.endswith("text") and n.text == label
    )


def assert_clear(svg):
    host = ET.Element("slide")
    ET.SubElement(host, "embed").append(ET.fromstring(svg))
    assert not validate_embedded_svgs(host)
    assert not detect_embedded_svg_overlaps(host)


def test_sparse_radar_labels_and_legends_grow():
    radar = make_radar(
        [{"name": n, "min": 0, "max": 10} for n in "ABCD"],
        [{"name": "Observed", "values": [2, 4, 6, 8]}],
        width=1200,
        height=800,
    )
    assert text_size(radar, "A") >= 23
    assert text_size(radar, "Observed") >= 20
    assert_clear(radar)


def test_graph_density_changes_label_size_without_dropping_nodes():
    small = [{"id": str(i), "label": f"Node {i}"} for i in range(4)]
    dense = [{"id": str(i), "label": f"Node {i}"} for i in range(40)]
    a, b = [make_network(data, [], width=1200, height=800) for data in (small, dense)]
    assert text_size(a, "Node 0") >= 23
    assert 12 <= text_size(b, "Node 0") < text_size(a, "Node 0")
    assert len([n for n in ET.fromstring(b).iter() if n.get("data-role") == "network-node"]) == 40
    assert_clear(a)
    assert_clear(b)


def test_swimmer_axis_and_patient_rows_use_measured_large_type():
    svg = make_swimmer(
        [
            {
                "id": "P1",
                "segments": [{"start": 0, "end": 8, "treatment": "Drug"}],
                "events": [{"time": 4, "label": "Review"}],
            }
        ],
        width=1200,
        height=800,
    )
    assert text_size(svg, "P1") >= 23
    assert text_size(svg, "Review") >= 23
    assert text_size(svg, "Time from treatment start (months)") >= 25
    assert_clear(svg)
