"""Distribution charts: boxplot, violin, ridge, raincloud, dumbbell, shift plot and distribution panels."""

import math
import unittest
import xml.etree.ElementTree as ET
import json
import sys
from unittest.mock import patch
from copy import deepcopy
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from ._helpers import nodes, nodes as elements
from ..charts._distribution import sample_stats, swarm, kde
from ..charts.boxplot import draw_boxplot, make_boxplot
from ..charts.dumbbell import make_dumbbell
from ..charts.raincloud import make_raincloud
from ..charts.ridge import make_ridge
from ..charts.violin import draw_violin, make_violin
from ..charts._chart_layout import ChartLayout
from ..charts._distribution_panels import finalize_distribution_panel, prepare_distribution_panel
from ..charts.composite import make_composite
from ..charts import _distribution
from ..charts._distribution import axis_ticks
from embed_svg_validator import detect_embedded_svg_overlaps, validate_embedded_svgs


# ====================================================================================================
# Semantic regressions for distribution geometry and explicit sample identity.
# ====================================================================================================


class DistributionSemanticsTest(unittest.TestCase):
    def setUp(self):
        self.groups = [("Control", [1, 2, 2, 3, 4, 5]), ("Treatment", [2, 3, 4, 5, 6, 8])]

    def test_whiskers_swarm_and_raincloud_keep_actual_observations(self):
        stats = sample_stats([0, 1, 2, 3, 4, 12])
        self.assertEqual(stats["hi"], 4)
        self.assertEqual(stats["lo"], 0)
        pixels = [100.0] * 30 + [101.0, 103.0, 106.0, 100.5]
        offsets, radius = swarm(pixels, 80)
        self.assertEqual(len(offsets), len(pixels))
        for i, value in enumerate(pixels):
            self.assertLessEqual(abs(offsets[i]) + radius, 80)
            for j in range(i):
                self.assertGreaterEqual(math.hypot(value - pixels[j], offsets[i] - offsets[j]) + 1e-6, radius * 2)
        svg = make_raincloud(self.groups)
        rendered = sorted(float(node.get("data-value")) for node in nodes(svg, "observation"))
        self.assertEqual(rendered, sorted(v for _, values in self.groups for v in values))
        self.assertEqual(len(nodes(svg, "density")), 2)
        self.assertEqual(len(nodes(svg, "box")), 2)

    def test_paired_connections_need_unique_ids_and_join_by_id(self):
        groups = [
            ("Before", [{"subject_id": "a", "value": 1}, {"subject_id": "b", "value": 3}]),
            ("After", [{"subject_id": "b", "value": 4}, {"subject_id": "c", "value": 2}]),
        ]
        svg = make_boxplot(groups, paired=True)
        lines = nodes(svg, "paired-connection")
        self.assertEqual([line.get("data-subject-id") for line in lines], ["b"])
        points = [node for node in nodes(svg, "observation") if node.get("data-subject-id") == "b"]
        ends = {(line.get("x1"), line.get("y1")) for line in lines} | {
            (line.get("x2"), line.get("y2")) for line in lines
        }
        self.assertEqual(ends, {(node.get("cx"), node.get("cy")) for node in points})
        with self.assertRaisesRegex(ValueError, "subject_id"):
            make_boxplot(self.groups, paired=True)
        with self.assertRaisesRegex(ValueError, "duplicate subject_id"):
            make_raincloud([("A", [{"value": 1, "subject_id": "x"}, {"value": 2, "subject_id": "x"}])])
        records = [("A", [{"value": 1}, {"value": 2}]), ("B", [{"value": 2}, {"value": 4}])]
        for fn in (make_boxplot, make_violin):
            svg = fn(records)
            self.assertIn("n = 2", svg)
            self.assertEqual(len(nodes(svg, "paired-connection")), 0)

    def test_variants_preserve_axes_academic_and_footnotes(self):
        for make, variant in (
            (make_boxplot, "beeswarm"),
            (make_boxplot, "notched_outlined"),
            (make_violin, "quartile_outlined"),
            (make_violin, "half_gradient"),
        ):
            with self.subTest(variant=variant):
                label = {"y_title": "Response"} if make is make_boxplot else {"y_axis_label": "Response"}
                svg = make(
                    self.groups,
                    variant=variant,
                    y_min=0,
                    y_max=10,
                    y_unit="mg",
                    academic=True,
                    pairwise_p=[(0, 1, 0.003)],
                    note="Validated input",
                    source="Instrument A",
                    **label,
                )
                self.assertIn("Response (mg)", svg)
                self.assertIn("Validated input", svg)
                self.assertIn("Instrument A", svg)
                self.assertEqual(len(nodes(svg, "significance")), 1)
                self.assertIn("P = 0.003", svg)

    def test_direct_draw_matches_make_semantics(self):
        for draw, variant in ((draw_boxplot, "beeswarm"), (draw_violin, "points_inner_flat")):
            svg = draw(
                {"groups": self.groups, "unit": "ms"},
                variant=variant,
                academic=True,
                pairwise_p=[(0, 1, 0.04)],
                orientation="horizontal",
                y_min=0,
                y_max=10,
                height=600,
            )
            self.assertEqual(len(nodes(svg, "significance")), 1)
            self.assertEqual(len(nodes(svg, "observation")), 12)

    def test_facets_share_order_and_keep_per_facet_p_values(self):
        conditions = [("North", self.groups), ("South", list(reversed(self.groups)))]
        svg = make_violin(
            [],
            conditions=conditions,
            variant="overlay",
            academic=True,
            pairwise_p={"North": [(0, 1, 0.01)], "South": [(0, 1, 0.02)]},
        )
        self.assertEqual(len(nodes(svg, "density")), 4)
        self.assertIn('stroke-dasharray="5 4"', svg)
        self.assertIn("P = 0.01", svg)
        self.assertIn("P = 0.02", svg)
        self.assertEqual([node.get("data-group") for node in nodes(svg, "density")], ["Control", "Treatment"] * 2)

    def test_density_matrix_and_raw_ridge_smoothing_counts(self):
        from ..charts._ridge_distribution import kde

        with patch("svg_lib.charts._ridge_distribution.kde", side_effect=AssertionError("KDE called on density")):
            svg = make_ridge(
                [[0, 1, 0], [0, 0.5, 0]], group_labels=["A", "B"], x_range=(10, 30), variant="default_flat"
            )
        self.assertEqual({node.get("data-input-kind") for node in nodes(svg, "ridge-density")}, {"density"})
        self.assertIn("30", svg)
        with patch("svg_lib.charts._ridge_distribution.kde", wraps=kde) as wrapped:
            svg = make_ridge(self.groups, variant="outlined_separated", academic=True, x_unit="ms")
        self.assertEqual(wrapped.call_count, 2)
        self.assertEqual({node.get("data-input-kind") for node in nodes(svg, "ridge-density")}, {"samples"})
        self.assertIn("n = 6", svg)
        rows = [
            ("Cell A", {"Before": [1, 2, 3], "After": [2, 4, 5]}),
            ("Cell B", {"Before": [2, 3, 4], "After": [3, 4, 5]}),
        ]
        svg = make_ridge([], conditions=[("X", rows), ("Y", rows)], width=1200, multi_mode="with_counts")
        self.assertEqual(len(nodes(svg, "ridge-density")), 8)
        self.assertEqual([int(node.get("data-count")) for node in nodes(svg, "sample-count")], [6] * 4)
        rows = [
            ("Cell A", {"Control": [1, 2, 3], "Treatment": [2, 3, 4]}),
            ("Cell B", {"Control": [2, 3, 4], "Treatment": [3, 4, 5]}),
        ]
        svg = make_ridge(rows, multi_mode="with_counts")
        self.assertEqual(len({node.get("stroke") for node in nodes(svg, "sample-count")}), 1)
        self.assertIn("Total sample", svg)

    def test_dumbbell_endpoints_negative_equal_and_nearby(self):
        svg = make_dumbbell(
            [{"label": "Reversed", "before": 3, "after": -2}, {"label": "Equal", "before": 0, "after": 0}]
        )
        self.assertEqual([node.get("data-value") for node in nodes(svg, "before")], ["3", "0"])
        self.assertEqual([node.get("data-value") for node in nodes(svg, "after")], ["-2", "0"])
        svg = make_dumbbell(
            [{"label": "Close", "before": 10, "after": 10.01}, {"label": "Range", "before": 0, "after": 20}], width=700
        )
        before = nodes(svg, "before")[0]
        after = nodes(svg, "after")[0]
        distance = float(after.get("cx")) - float(before.get("cx"))
        self.assertGreater(distance, 0)
        self.assertLess(distance, 1)
        self.assertEqual(before.get("fill"), "none")
        self.assertNotEqual(before.get("stroke"), after.get("fill"))
        self.assertGreater(float(before.get("r")), distance + float(after.get("r")))

    def test_degenerate_samples_and_undefined_effects(self):
        for fn, kwargs in (
            (make_raincloud, {"groups": [("A", [0] * 5), ("B", [0] * 5)]}),
            (make_ridge, {"distributions": [("A", [0] * 5)], "variant": "default_flat"}),
        ):
            svg = fn(**kwargs)
            ET.fromstring(svg)
            self.assertNotRegex(svg, r"(?i)(?:nan|[+-]?inf)(?:[\" ,])")
        constant = [("A", [1.0] * 6), ("B", [2.0] * 6)]
        for fn in (make_boxplot, make_violin):
            with self.subTest(function=fn.__name__):
                with self.assertRaises(ValueError):
                    fn(constant, academic=True, multi_mode="with_effect_size")
                svg = fn(constant, academic=True, multi_mode="auto")
                self.assertNotIn("Effect size", svg)
        groups = [
            ("A", [{"value": 1, "subject_id": "x"}, {"value": 2, "subject_id": "y"}]),
            ("B", [{"value": 2, "subject_id": "x"}, {"value": 3, "subject_id": "y"}]),
        ]
        with self.assertRaisesRegex(ValueError, "zero variance"):
            make_boxplot(groups, paired=True, multi_mode="with_effect_size")

    def test_gradient_variants_retain_their_style(self):
        for fn, kwargs in (
            (make_boxplot, {"groups": self.groups, "variant": "variable_width_gradient"}),
            (make_violin, {"groups": self.groups, "variant": "half_gradient"}),
            (make_ridge, {"distributions": self.groups, "variant": "gradient_overlap"}),
        ):
            self.assertIn("<linearGradient", fn(**kwargs))

    def test_effect_panel_composes_with_variants_orientation_and_facets(self):
        conditions = [("North", self.groups), ("South", list(reversed(self.groups)))]
        for fn, variant in ((make_boxplot, "beeswarm"), (make_violin, "points_inner_flat")):
            svg = fn(
                [],
                conditions=conditions,
                variant=variant,
                orientation="horizontal",
                multi_mode="with_effect_size",
                academic=True,
                pairwise_p=[(0, 1, 0.01)],
            )
            effects = nodes(svg, "effect-estimate")
            self.assertEqual(len(effects), 2)
            self.assertEqual(len(nodes(svg, "significance")), 2)
            self.assertIn("North · Treatment − Control", svg)
            self.assertEqual(effects[0].get("data-estimate"), effects[1].get("data-estimate"))

    def test_paired_effect_uses_matched_differences_and_is_unit_invariant(self):
        groups = [
            ("A", [{"value": 1, "subject_id": "x"}, {"value": 3, "subject_id": "y"}, {"value": 4, "subject_id": "z"}]),
            ("B", [{"value": 8, "subject_id": "z"}, {"value": 2, "subject_id": "x"}, {"value": 5, "subject_id": "y"}]),
        ]
        svg = make_raincloud(groups, paired=True, multi_mode="with_effect_size")
        effect = nodes(svg, "effect-estimate")[0]
        self.assertEqual(effect.get("data-effect-kind"), "paired-dz")
        differences = [1, 2, 4]
        mean = sum(differences) / 3
        sd = math.sqrt(sum((d - mean) ** 2 for d in differences) / 2)
        self.assertAlmostEqual(float(effect.get("data-estimate")), mean / sd, places=10)
        self.assertIn("n = 3 pairs", svg)
        effects = []
        for factor in (1, 1e-170, 1e170):
            groups = [
                ("Before", [{"value": value * factor, "subject_id": str(i)} for i, value in enumerate([1, 3, 5])]),
                ("After", [{"value": value * factor, "subject_id": str(i)} for i, value in enumerate([2, 4, 8])]),
            ]
            svg = make_raincloud(groups, paired=True, multi_mode="with_effect_size", width=950)
            effects.append(float(nodes(svg, "effect-estimate")[0].get("data-estimate")))
        self.assertAlmostEqual(effects[0], 1.44337567297, places=10)
        self.assertAlmostEqual(effects[0], effects[1], places=10)
        self.assertAlmostEqual(effects[0], effects[2], places=10)
        constant = [
            ("Before", [{"value": 10, "subject_id": "a"}, {"value": 20, "subject_id": "b"}]),
            ("After", [{"value": 15, "subject_id": "a"}, {"value": 25, "subject_id": "b"}]),
        ]
        with self.assertRaisesRegex(ValueError, "zero variance"):
            make_raincloud(constant, paired=True, multi_mode="with_effect_size")

    def test_overlay_and_classic_effects_do_not_require_extra_academic_toggle(self):
        for variant in (None, "overlay"):
            svg = make_violin(self.groups, variant=variant, multi_mode="with_effect_size")
            self.assertEqual(len(nodes(svg, "effect-estimate")), 1)
            if variant == "overlay":
                self.assertIn('stroke-dasharray="5 4"', svg)

    def test_r1_01_bandwidth_and_kde_are_affine_equivariant(self):
        from ..charts._distribution import bandwidth_for, kde, normalize_groups, sample_domain

        values = [1, 2, 3, 4, 5, 6]
        bandwidth = bandwidth_for(values)
        transformed = [value * 1e-15 + 7e-15 for value in values]
        self.assertAlmostEqual(bandwidth_for(transformed) / 1e-15, bandwidth, places=12)
        self.assertAlmostEqual(bandwidth_for([v + 1e12 for v in values]), bandwidth, places=12)
        first_domain = sample_domain(normalize_groups([("A", values)]), density=True)
        second_domain = sample_domain(normalize_groups([("A", transformed)]), density=True)
        _, first_density = kde(values, first_domain)
        _, second_density = kde(transformed, second_domain)
        for first, second in zip(first_density, second_density):
            self.assertAlmostEqual(first, second, places=12)
        self.assertGreater(bandwidth_for([0] * 500), 0)

    def test_r1_02_03_classic_whiskers_and_tiny_outliers_match_variants(self):
        for factor in (1.0, 1e-15):
            groups = [("Sample", [v * factor for v in [0, 1, 2, 3, 4, 12]])]
            for fn, variant in (
                (make_boxplot, None),
                (make_boxplot, "default_flat"),
                (make_violin, None),
                (make_violin, "boxplot_inner_flat"),
            ):
                kwargs = {"show_jitter": False} if fn is make_boxplot else {}
                svg = fn(groups, variant=variant, multi_mode="single", **kwargs)
                whisker = nodes(svg, "whisker")[0]
                self.assertAlmostEqual(float(whisker.get("data-high")) / factor, 4)
                self.assertEqual(len(nodes(svg, "outlier")), 1)
                self.assertAlmostEqual(float(nodes(svg, "outlier")[0].get("data-value")) / factor, 12)

    def test_r1_07_dense_frequencies_and_hidden_swarm(self):
        groups = [("A", [0] * 500), ("B", [0] * 500)]

        with patch.object(_distribution, "_observation_plan", wraps=_distribution._observation_plan) as plan:
            make_violin(groups, width=400, variant="kde_only")
            make_boxplot(groups, width=400, variant="default_flat", show_jitter=False)
            self.assertEqual(plan.call_count, 0)
            make_boxplot(groups, width=400, variant="beeswarm")
            self.assertGreater(plan.call_count, 0)
        svg = make_boxplot([("A", [0] * 500)], width=400, variant="beeswarm")
        dots = nodes(svg, "observation-frequency")
        self.assertEqual(sum(int(dot.get("data-count")) for dot in dots), 500)
        self.assertEqual([float(dot.get("data-value")) for dot in dots], [0])
        self.assertTrue(all(float(dot.get("r")) >= 1.6 for dot in dots))
        self.assertIn("0 × 500 observations", svg)
        self.assertIn("Repeated observations", svg)

    def test_r1_09_common_offset_preserves_distinct_tick_values(self):
        values, labels, offset = axis_ticks((1e12 + 0.001, 1e12 + 0.009))
        self.assertEqual(len(set(values)), 6)
        self.assertEqual(len(set(labels)), 6)
        self.assertIn("1000000000000", offset)
        self.assertTrue(all(len(label) < 16 for label in labels))

    def test_r1_10_11_counts_and_legends_follow_active_layers(self):
        for orientation in ("vertical", "horizontal"):
            svg = make_violin(self.groups, orientation=orientation, per_group_n=[100, 200])
            self.assertIn("n = 100", svg)
            self.assertIn("n = 200", svg)
        strip = make_boxplot(self.groups, variant="strip_flat")
        self.assertNotIn("Tukey", strip)
        self.assertIn("observations", strip)
        for variant in ("kde_only", "half_gradient"):
            svg = make_violin(self.groups, variant=variant)
            self.assertNotIn("quartiles", svg)
            self.assertNotIn("Q1–Q3", svg)
        self.assertNotIn("Q1–Q3", make_violin(self.groups, show_boxplot=False))

    def test_r1_14_median_panel_has_exact_values_and_group_names(self):
        rows = [("Cell " + str(i), [1 + i, 2 + i, 3 + i, 4 + i, 6 + i]) for i in range(5)]
        svg = make_ridge(rows, multi_mode="with_median_trend")
        medians = nodes(svg, "ridge-median")
        self.assertEqual([node.get("data-group") for node in medians], [row[0] for row in rows])
        self.assertEqual([float(node.get("data-value")) for node in medians], [3, 4, 5, 6, 7])
        self.assertIn("Group median and IQR", svg)

    def test_d2_01_05_subnormal_density_and_narrow_axis(self):
        from ..charts._distribution import kde, normalize_groups, sample_domain

        base = [1, 2, 3, 4, 5, 6]
        values = [value * 1e-320 for value in base]
        domain = sample_domain(normalize_groups([("A", values)]), density=True)
        _, heights = kde(values, domain)
        self.assertTrue(all(math.isfinite(height) for height in heights))
        self.assertGreater(max(heights), 0)
        svg = make_raincloud([("A", values), ("B", [value * 1.2 for value in values])], width=700)
        self.assertEqual(len(nodes(svg, "density")), 2)
        self.assertTrue(all("nan" not in node.get("d").lower() for node in nodes(svg, "density")))
        groups = [
            ("A", [value * 1e-15 for value in [1, 2, 3, 4, 5, 6]]),
            ("B", [value * 1e-15 for value in [2, 3, 4, 5, 6, 8]]),
        ]
        svg = make_raincloud(groups, width=450)
        width, height = ET.fromstring(svg).get("viewBox").split()[2:]
        slide = ET.fromstring(
            f'<slide xmlns="https://www.larkoffice.com/sml/2.0"><data><embed id="chart" topLeftX="0" topLeftY="0" width="{width}" height="{height}">{svg}</embed></data></slide>'
        )
        self.assertEqual(validate_embedded_svgs(slide) + detect_embedded_svg_overlaps(slide), [])

    def test_d2_04_dense_raincloud_frequencies_are_readable_and_lossless(self):
        svg = make_raincloud([("A", [0] * 500), ("B", [0] * 500)], width=700)
        counts = nodes(svg, "observation-frequency")
        self.assertEqual([int(node.get("data-count")) for node in counts], [500, 500])
        self.assertTrue(all(float(node.get("r")) >= 1.6 for node in counts))
        self.assertEqual([float(node.get("data-value")) for node in counts], [0, 0])
        self.assertIn("full observation count is retained", svg)

    def test_d3_01_series_styles_survive_row_mapping_and_facet_reordering(self):
        rows = [
            ("Cell A", {"Control": [1, 2, 3, 4, 5], "Treatment": [5, 6, 7, 8, 9]}),
            ("Cell B", {"Treatment": [5, 6, 7, 8, 9], "Control": [1, 2, 3, 4, 5]}),
        ]
        for variant in ("default_flat", "joy_division", "histogram_binned"):
            first_styles = None
            for conditions in (
                [("North", rows), ("South", list(reversed(rows)))],
                [("South", list(reversed(rows))), ("North", rows)],
            ):
                svg = make_ridge([], conditions=conditions, variant=variant, width=1200, palette="nightlab")
                legend = {
                    node.get("data-series"): (node.get("stroke"), node.get("stroke-dasharray"))
                    for node in nodes(svg, "series-legend")
                }
                self.assertEqual(set(legend), {"Control", "Treatment"})
                self.assertNotEqual(legend["Control"][1], legend["Treatment"][1])
                for node in nodes(svg, "ridge-density"):
                    self.assertEqual(
                        (node.get("stroke"), node.get("stroke-dasharray")), legend[node.get("data-series")]
                    )
                if first_styles is None:
                    first_styles = legend
                self.assertEqual(first_styles, legend)
                if variant == "joy_division":
                    self.assertEqual(legend["Control"][0], legend["Treatment"][0])

    def test_d3_02_dense_bins_paired_lines_and_inner_points(self):
        values = [index * 1e-5 for index in range(100)] + [1]
        expected = sample_stats(values)
        original = list(values)
        svg = make_raincloud([("A", values), ("B", values)], width=700)
        self.assertEqual(values, original)
        raw = nodes(svg, "observation")
        bins = nodes(svg, "observation-bin")
        self.assertEqual([float(node.get("data-value")) for node in raw], [1, 1])
        self.assertTrue(all(float(node.get("r")) >= 2.5 for node in raw))
        self.assertEqual([int(node.get("data-count")) for node in bins], [100, 100])
        self.assertTrue(all(float(node.get("r")) >= 1.8 for node in bins))
        self.assertTrue(all(node.get("data-representative") == "median" for node in bins))
        self.assertEqual([float(node.get("data-low")) for node in bins], [0, 0])
        self.assertEqual([float(node.get("data-high")) for node in bins], [values[99], values[99]])
        for node in nodes(svg, "box-median"):
            self.assertEqual(float(node.get("data-value")), expected["median"])
        for node in nodes(svg, "mean"):
            self.assertEqual(float(node.get("data-value")), expected["mean"])
        self.assertIn("display bins", svg)
        self.assertIn("Aggregated observations", svg)
        values = [index * 1e-5 for index in range(100)] + [1]
        groups = [
            (name, [{"value": value + shift, "subject_id": str(index)} for index, value in enumerate(values)])
            for name, shift in (("Before", 0), ("After", 0.1))
        ]
        svg = make_raincloud(groups, paired=True, width=700)
        lines = {line.get("data-subject-id"): line for line in nodes(svg, "paired-connection")}
        self.assertEqual(len(lines), 101)
        first = float(lines["0"].get("x1"))
        pixel_per_unit = float(lines["100"].get("x1")) - first
        for index, value in enumerate(values):
            self.assertEqual(float(lines[str(index)].get("data-value-start")), value)
            self.assertEqual(float(lines[str(index)].get("data-value-end")), value + 0.1)
            self.assertAlmostEqual(float(lines[str(index)].get("x1")), first + value * pixel_per_unit, places=5)
            self.assertAlmostEqual(float(lines[str(index)].get("x2")), first + (value + 0.1) * pixel_per_unit, places=5)
        self.assertEqual(len({line.get("x1") for key, line in lines.items() if key != "100"}), 100)
        self.assertIn("Paired lines", svg)
        self.assertEqual(sum(int(node.get("data-count")) for node in nodes(svg, "observation-bin")), 200)
        values = [index * 1e-5 for index in range(100)] + [1]
        svg = make_violin([("A", values), ("B", values)], variant="points_inner_flat", width=700)
        marks = nodes(svg, "observation") + nodes(svg, "observation-bin") + nodes(svg, "observation-frequency")
        self.assertTrue(all(float(node.get("r")) >= 1.8 for node in marks))
        self.assertEqual(sum(int(node.get("data-count")) for node in marks), 202)
        self.assertTrue(all(float(node.get("data-value")) == 1 for node in nodes(svg, "observation")))

    def test_d3_dense_kde_peak_and_fixed_canvas_bins(self):
        from ..charts._distribution import kde, normalize_groups, sample_domain

        values = [index * 1e-5 for index in range(100)] + [1]
        shifted = [value + 0.1 for value in values]
        domain = sample_domain(normalize_groups([("A", values), ("B", shifted)]), density=True)
        peaks = []
        for group in (values, shifted):
            x, density = kde(group, domain)
            peak_index = max(range(len(density)), key=density.__getitem__)
            peaks.append(x[peak_index])
            self.assertLess(abs(x[peak_index] - group[50]), 0.0001)
        self.assertAlmostEqual(peaks[1] - peaks[0], 0.1, places=4)
        values = [index * 1e-5 for index in range(100)] + [1]
        svg = make_raincloud([("A", values), ("B", values)], width=700, height=800)
        self.assertEqual(float(ET.fromstring(svg).get("viewBox").split()[3]), 800)
        for role in ("observation", "observation-bin", "observation-frequency"):
            self.assertTrue(all(float(node.get("r")) >= 1.8 for node in nodes(svg, role)))
        self.assertEqual(sum(int(node.get("data-count")) for node in nodes(svg, "observation-bin")), 200)
        self.assertIn("range [0, 0.00099]", svg)

    def test_d3_monochrome_three_series_have_distinct_consistent_patterns(self):
        rows = [
            ("Cell A", {"Control": [1, 2, 3], "Mid": [2, 3, 4], "Treatment": [3, 4, 5]}),
            ("Cell B", {"Treatment": [3, 4, 5], "Control": [1, 2, 3], "Mid": [2, 3, 4]}),
        ]
        svg = make_ridge(rows, variant="joy_division")
        legends = nodes(svg, "series-legend")
        self.assertEqual(len({node.get("stroke-dasharray") for node in legends}), 3)
        mapping = {node.get("data-series"): node.get("stroke-dasharray") for node in legends}
        for node in nodes(svg, "ridge-density"):
            self.assertEqual(node.get("stroke-dasharray"), mapping[node.get("data-series")])

    def test_d4_01_kde_keeps_minority_peaks_supplied_bandwidth_mass_and_bounded_work(self):
        from ..charts._distribution import bandwidth_for, kde

        # The default bandwidth preserves the interior minority peak.
        values = [index * 1e-5 for index in range(31)] + [0.5, 1.0]
        xs, density = kde(values, (-0.08, 1.08))
        bandwidth = bandwidth_for(values)
        expected = 1.16 / (len(values) * bandwidth * math.sqrt(2 * math.pi))
        for center in (0.5, 1.0):
            index = min(range(len(xs)), key=lambda index: abs(xs[index] - center))
            self.assertAlmostEqual(xs[index], center, places=12)
            self.assertAlmostEqual(density[index] / expected, 1, places=10)
        # A supplied bandwidth preserves every separated mode and weight.
        peaks = [(index / 10, 1 + index % 3) for index in range(1, 71)]
        values = [index * 1e-7 for index in range(96)]
        values += [center for center, count in peaks for _ in range(count)]
        bandwidth = 2e-4
        xs, density = kde(values, (-0.1, 7.1), bandwidth=bandwidth)
        for center, count in peaks:
            index = min(range(len(xs)), key=lambda index: abs(xs[index] - center))
            expected = 7.2 * count / (len(values) * bandwidth * math.sqrt(2 * math.pi))
            self.assertAlmostEqual(xs[index], center, places=12)
            self.assertAlmostEqual(density[index] / expected, 1, places=10)
        # Tails do not bridge empty regions with spurious mass.
        xs, density = kde([0, 0, 1], (-0.1, 1.1), bandwidth=1e-7)
        integral = math.fsum(
            (right - left) * (a + b) / 2 / 1.2 for left, right, a, b in zip(xs, xs[1:], density, density[1:])
        )
        self.assertAlmostEqual(integral, 1, delta=0.001)
        # Dense and separated kernels avoid all-pairs evaluation.
        cases = (([index * 1e-5 for index in range(512)], (-1, 1), 0.01), (list(range(512)), (-1, 513), 0.001))
        gaussian_exp = math.exp
        for values, domain, bandwidth in cases:
            with patch("svg_lib.charts._distribution.math.exp", wraps=gaussian_exp) as evaluate:
                kde(values, domain, bandwidth=bandwidth)
            self.assertLess(evaluate.call_count, 200 * len(values))

    def test_d4_01_kde_matches_gaussian_oracle_after_reordering_and_affine_changes(self):
        from ..charts._distribution import bandwidth_for, kde

        original = [index * 1e-5 for index in range(31)] + [0.5, 1.0]
        for supplied in (None, 2e-5):
            reference = None
            for scale, shift in ((1, 0), (1, 8), (1e-15, 7e-15), (1e150, 3e150)):
                values = [value * scale + shift for value in reversed(original)]
                domain = (-0.08 * scale + shift, 1.08 * scale + shift)
                span = domain[1] - domain[0]
                bandwidth = bandwidth_for(values, None if supplied is None else supplied * scale)
                xs, density = kde(values, domain, bandwidth=bandwidth)
                maximum = max(density)
                for x, actual in zip(xs, density):
                    expected = (
                        math.fsum(math.exp(-0.5 * ((x - value) / bandwidth) ** 2) for value in values)
                        * span
                        / (len(values) * bandwidth * math.sqrt(2 * math.pi))
                    )
                    self.assertAlmostEqual(actual / maximum, expected / maximum, places=8)
                peaks = []
                for center in (0.5, 1.0):
                    index = min(range(len(xs)), key=lambda index: abs(xs[index] - (center * scale + shift)))
                    self.assertAlmostEqual((xs[index] - shift) / scale, center, places=12)
                    peaks.append(density[index])
                if reference is None:
                    reference = peaks
                for actual, expected in zip(peaks, reference):
                    self.assertAlmostEqual(actual / expected, 1, places=8)
            forward = kde(original, (-0.08, 1.08), bandwidth=supplied)
            reverse = kde(list(reversed(original)), (-0.08, 1.08), bandwidth=supplied)
            self.assertEqual(forward, reverse)

    def test_shared_axis_ticks_keep_extreme_finite_endpoints(self):
        for domain in ((0.0, 1e308), (-1e308, 1e308), (1e308, 1.1e308)):
            values, labels, offset = axis_ticks(domain)
            self.assertEqual(values[0], domain[0])
            self.assertEqual(values[-1], domain[1])
            self.assertTrue(all(math.isfinite(value) for value in values))
            self.assertTrue(all(values[index] < values[index + 1] for index in range(len(values) - 1)))
            self.assertEqual(len(set(labels)), len(values))
            self.assertTrue(all("inf" not in label.lower() and "nan" not in label.lower() for label in labels))
            self.assertNotIn("inf", offset.lower())

    def test_invalid_data_limits_and_layout_raise_explicit_errors(self):
        with self.assertRaisesRegex(ValueError, "finite"):
            make_raincloud([("A", [float("nan")])])
        with self.assertRaisesRegex(ValueError, "contain every"):
            make_boxplot(self.groups, variant="beeswarm", y_max=3)
        with self.assertRaisesRegex(ValueError, "too small"):
            make_violin(self.groups, variant="overlay", height=100)
        with self.assertRaisesRegex(ValueError, "requires conditions"):
            make_violin(self.groups, multi_mode="with_condition_facets")
        with self.assertRaisesRegex(ValueError, "requires raw samples"):
            make_ridge([[1, 2, 1]], variant="histogram_binned")


# ====================================================================================================
# Semantic regression for independently scaled and composed distributions.
# ====================================================================================================


def layout(svg, role="heterogeneous-panels-layout"):
    return json.loads(elements(svg, role)[0].get("data-layout"))


class DistributionPanelsTest(unittest.TestCase):
    def test_independent_violin_domains_and_significance(self):
        panels = [
            {
                "id": str(i),
                "kind": "violin",
                "data": {
                    "groups": [("Control", [v, v * 1.02, v * 1.04]), ("Treated", [v * 1.2, v * 1.23, v * 1.25])],
                    "academic": True,
                    "pairwise_p": [(0, 1, 0.004)],
                },
            }
            for i, v in enumerate([0.78, 0.15, 0.03])
        ]
        svg = make_composite({"panels": panels}, template="panels", cols=3)
        result = layout(svg)["panels"]
        self.assertEqual(len({tuple(p["axes"]["y"]["domain"]) for p in result}), 3)
        self.assertEqual(len(elements(svg, "density")), 6)
        self.assertIn("P = 0.004", svg)

    def test_empirical_curve_is_not_recovered_samples_and_axes_align(self):
        svg = make_composite(
            {
                "panels": [
                    {
                        "id": "density",
                        "kind": "xy",
                        "x_group": "theta",
                        "data": {
                            "series": [
                                {
                                    "name": "Empirical",
                                    "points": [],
                                    "curve": [(-3, 0), (-1, 0.4), (0, 0.6), (2, 0.2), (4, 0)],
                                }
                            ]
                        },
                    },
                    {
                        "id": "samples",
                        "kind": "boxplot",
                        "x_group": "theta",
                        "data": {
                            "groups": [
                                ("Recovered observations with a long label", [-2, -1.1, -0.9, 0, 0.4, 1.1, 1.4])
                            ],
                            "variant": "beeswarm",
                            "orientation": "horizontal",
                        },
                    },
                ]
            },
            template="panels",
            cols=1,
        )
        result = layout(svg)["panels"]
        self.assertEqual(result[0]["axes"]["x"]["domain"], result[1]["axes"]["x"]["domain"])
        self.assertEqual(result[0]["plot_bbox"][::2], result[1]["plot_bbox"][::2])
        self.assertEqual(len(elements(svg, "observation")), 7)
        self.assertEqual(float(elements(svg, "box-median")[0].get("data-value")), 0)

    def test_shared_group_colours_with_nmds_and_reordered_xy(self):
        color = {"Control": "#334499", "Treated": "#aa4433"}
        svg = make_composite(
            {
                "panels": [
                    {
                        "kind": "violin",
                        "data": {"groups": [("Control", [1, 2, 3]), ("Treated", [2, 4, 5])], "group_colors": color},
                    },
                    {
                        "kind": "xy",
                        "data": {
                            "series": [
                                {"name": n, "color": c, "points": [(i, i / 2), (i + 0.4, i - 0.2)]}
                                for i, (n, c) in enumerate(color.items())
                            ],
                            "x_title": "NMDS1",
                            "y_title": "NMDS2",
                        },
                    },
                ]
            },
            template="panels",
        )
        for mark in elements(svg, "density"):
            self.assertEqual(mark.get("stroke"), color[mark.get("data-group")])
        self.assertIn("NMDS1", svg)
        self.assertEqual(len(elements(svg, "density")), 2)
        svg = make_composite(
            {
                "panels": [
                    {"kind": "violin", "data": {"groups": [("Control", [1, 2, 3]), ("Treated", [2, 4, 5])]}},
                    {
                        "kind": "xy",
                        "data": {
                            "series": [{"name": "Treated", "points": [(1, 2)]}, {"name": "Control", "points": [(3, 4)]}]
                        },
                    },
                ]
            },
            template="panels",
        )
        root = ET.fromstring(svg)
        density = {e.get("data-group"): e.get("stroke") for e in elements(svg, "density")}
        markers = [e for e in root.iter() if e.get("data-series") in density and e.get("data-role") == "observation"]
        self.assertTrue(markers)
        for marker in markers:
            self.assertEqual(marker.get("fill"), density[marker.get("data-series")])
        svg = make_composite(
            {
                "panels": [
                    {
                        "kind": "violin",
                        "data": {"groups": [("A", [1, 2, 3])], "annotations": ["Measured in the original experiment"]},
                    }
                ]
            },
            template="panels",
        )
        self.assertIn("Measured in the original experiment", svg)

    def test_mirror_variables_reverse_and_long_names_align(self):
        raw = [("Cell A", [1, 2, 3]), ("Cell B", [4, 5, 6])]
        svg = make_violin(
            [],
            orientation="mirrored",
            conditions=[("Left score", raw), ("Right score", [("Cell B", [40, 50, 60]), ("Cell A", [10, 20, 30])])],
        )
        result = layout(svg, "mirrored-distribution-layout")
        left, right = result["variables"]
        self.assertTrue(left["reversed"])
        self.assertFalse(right["reversed"])
        self.assertNotEqual(left["domain"], right["domain"])
        self.assertEqual(left["plot_bbox"][1::2], right["plot_bbox"][1::2])
        groups = elements(svg, "distribution-group")
        self.assertEqual([g.get("data-group") for g in groups], ["Cell A", "Cell B"] * 2)
        medians = elements(svg, "box-median")
        self.assertGreater(float(medians[0].get("x1")), float(medians[1].get("x1")))
        self.assertLess(float(medians[2].get("x1")), float(medians[3].get("x1")))
        svg = make_violin(
            [],
            orientation="mirrored",
            conditions=[
                ("Left short", [("A", [1, 2])]),
                ("Right variable with a substantially longer scientific axis description", [("A", [5, 6])]),
            ],
        )
        a, b = layout(svg, "mirrored-distribution-layout")["variables"]
        self.assertEqual(a["plot_bbox"][1::2], b["plot_bbox"][1::2])

    def test_observation_phase_colors_and_zero_reference(self):
        groups = [("Cell A", [{"value": -2, "color_group": "early"}, {"value": 3, "color_group": "late"}])]
        svg = make_composite(
            {
                "panels": [
                    {
                        "kind": "boxplot",
                        "data": {
                            "groups": groups,
                            "orientation": "horizontal",
                            "variant": "beeswarm",
                            "show_boxplot": False,
                            "reference_lines": [{"value": 0}],
                            "group_colors": {"early": "#334499", "late": "#aa4433"},
                        },
                    }
                ]
            },
            template="panels",
        )
        marks = elements(svg, "observation")
        self.assertEqual(
            {(m.get("data-color-group"), m.get("fill")) for m in marks}, {("early", "#334499"), ("late", "#aa4433")}
        )
        self.assertEqual(elements(svg, "reference-line")[0].get("data-value"), "0.0")
        self.assertEqual(len(elements(svg, "box")), 0)

    def test_shared_category_order_and_value_domains_for_location_time_facets(self):
        first = [("A", [1, 2]), ("B", [3, 4])]
        svg = make_composite(
            {
                "panels": [
                    {
                        "id": str(i),
                        "kind": "boxplot",
                        "x_group": "change",
                        "y_group": "cells",
                        "data": {
                            "groups": gs,
                            "orientation": "horizontal",
                            "variant": "beeswarm",
                            "show_boxplot": False,
                        },
                    }
                    for i, gs in enumerate([first, list(reversed(first))])
                ]
            },
            template="panels",
        )
        a, b = layout(svg)["panels"]
        self.assertEqual(a["axes"], b["axes"])
        self.assertEqual(a["anchors"]["group/A"][1], b["anchors"]["group/A"][1])

    def test_dense_phase_frequency_preserves_counts_and_all_raw_statistics(self):
        original = [("Dense", [{"value": 1, "color_group": "early"}] * 70 + [{"value": 1, "color_group": "late"}] * 50)]
        data = {
            "groups": original,
            "orientation": "horizontal",
            "variant": "beeswarm",
            "reference_lines": [{"value": 0}],
        }
        copy = deepcopy(data)
        svg = make_composite({"panels": [{"kind": "boxplot", "data": data}]}, template="panels")
        marks = elements(svg, "observation-frequency")
        self.assertEqual(sum(int(m.get("data-count")) for m in marks), 120)
        self.assertEqual({m.get("data-color-group") for m in marks}, {"early", "late"})
        self.assertIn("70 observations", svg)
        self.assertIn("50 observations", svg)
        self.assertEqual(data, copy)
        self.assertEqual(float(elements(svg, "box-median")[0].get("data-value")), 1)

    def test_plans_keep_numeric_samples_unchanged(self):
        values = [0.001 * i for i in range(500)] + [10]
        canvas = ChartLayout(600, 600, "archive_ink", None)
        data = {"groups": [("A", values)], "variant": "beeswarm", "orientation": "vertical"}
        before = list(values)
        panel = {"kind": "boxplot", "data": data}
        panel.update(prepare_distribution_panel("boxplot", data, canvas))
        finalize_distribution_panel(panel, canvas, 560)
        self.assertEqual(values, before)
        self.assertEqual(sample_stats(panel["groups"][0].values), sample_stats(before))
        self.assertEqual(sum(len(m["indices"]) for m in panel["plans"][0]), 501)
        self.assertTrue(any(m["kind"] == "bin" for m in panel["plans"][0]))
        self.assertEqual(kde(before, panel["axes"]["y"].domain), kde(values, panel["axes"]["y"].domain))

    def test_omitted_groups_and_invalid_phase_or_mirror_schemas(self):
        self.assertIn(
            "mirrored-distribution-layout",
            make_violin(orientation="mirrored", conditions=[("A", [("Cell", [1, 2])]), ("B", [("Cell", [3, 4])])]),
        )
        with self.assertRaisesRegex(ValueError, "nonempty sample group"):
            make_violin()
        with self.assertRaises(ValueError):
            make_composite(
                {
                    "panels": [
                        {"kind": "boxplot", "data": {"groups": [("A", [{"value": 1, "color_group": "early"}, 2])]}}
                    ]
                },
                template="panels",
            )
        with self.assertRaises(ValueError):
            make_violin([], orientation="mirrored", conditions=[("A", [("Cell A", [1])]), ("B", [("Cell B", [2])])])
