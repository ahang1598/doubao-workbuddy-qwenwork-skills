"""XY / scientific charts: scientific_xy, scientific panels, pairs, contour, insets."""

from __future__ import annotations

import math
import re
import unittest
import xml.etree.ElementTree as ET
import json
import sys
from copy import deepcopy
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from embed_svg_validator import validate_embedded_svgs

from ._helpers import _text_boxes, nodes
from .._common import _resolve_palette
from ..charts._xy import (
    BBox,
    CategoryScale,
    SeriesContext,
    SharedScale,
    _axis_format,
    _marginal,
    fit_series,
    infer_scales,
    interpolate_curve,
    make_xy_chart,
    normalize_series,
    render_xy_plot,
)
from ..charts.bubble import make_bubble
from ..charts.line_band import make_line_band
from ..charts.scatter_fit import _linreg, _residuals, make_scatter, make_scatter_fit
from ..charts.volcano import _threshold_branches, classify_volcano, make_volcano
from ..charts._composition_distribution import marginal_profiles, covariance_ellipse, histogram, kde2d
from ..charts.composite import make_composite
from ..charts.pairs import average_ranks, correlation, make_pairs
from ..charts.contour import _contour_segments, _interp_edge, density_grid, make_contour
from ..charts import _composition_panels
from ..charts._composition_distribution import render_marginal
from ..charts._pair_glyphs import frequency_display


# ====================================================================================================
# Scientific-XY semantics: real samples, calibrated inference and shared layers.
# ====================================================================================================


class ScientificXYTest(unittest.TestCase):
    def test_xy_curves_domains_fits_and_highlights(self):
        series = normalize_series([{"curve": [(1, 1e-6), (1e6, 1e6)]}])
        xs = SharedScale((1, 1e6), transform="log10")
        ys = SharedScale((1e-6, 1e6), transform="log10")
        svg = "<svg>" + render_xy_plot(series, BBox(70, 50, 850, 580), x_scale=xs, y_scale=ys) + "</svg>"
        segments = [
            [tuple(map(float, p)) for p in re.findall(r"[ML]([^, ]+),([^ ]+)", e.get("d"))] for e in nodes(svg, "curve")
        ]
        for i in range(1, 1201):
            x = 10 ** (i / 200)
            expected = 1e-6 + (1e6 - 1e-6) * (x - 1) / (1e6 - 1)
            px, py = xs.map(x, 70, 850), ys.map(expected, 580, 50)
            a, b = next((a, b) for a, b in segments if a[0] - 1e-5 <= px <= b[0] + 1e-5)
            actual = a[1] + (b[1] - a[1]) * (px - a[0]) / (b[0] - a[0])
            self.assertLess(abs(actual - py), 0.15)
        for transform, values, domain in (
            ("linear", [-0.001, 0, 1, 2, 2.001], (0, 2)),
            ("log10", [0.999, 1, 10, 100, 100.001], (1, 100)),
        ):
            series = normalize_series([{"name": "A", "points": [(v, v) for v in values]}])
            for axis in ("x", "y"):
                svg = (
                    "<svg>"
                    + _marginal(
                        series,
                        BBox(10, 10, 500, 500),
                        SharedScale(domain, transform=transform),
                        SeriesContext(["A"]),
                        axis,
                    )
                    + "</svg>"
                )
                self.assertEqual(sum(int(n.get("data-count")) for n in nodes(svg, "marginal-count")), 3)
        svg = make_line_band(
            [{"name": "Control", "points": [(1, 2), (4, 6)], "curve": [(1, 1.9), (2, 3), (3, 4.5), (4, 6.1)]}]
        )
        self.assertEqual(len(nodes(svg, "observation")), 2)
        self.assertEqual(len(nodes(svg, "curve")), 3)
        self.assertEqual([float(p.get("data-x")) for p in nodes(svg, "observation")], [1, 4])
        self.assertEqual(
            len(nodes(make_line_band([{"name": "Prediction", "curve": [(1, 2), (2, 3)]}]), "observation")), 0
        )
        raw = [
            {"name": "A", "points": [(1, 1), (2, 2), (3, 3)], "fit": "linear"},
            {"name": "B", "points": [(1, 6), (2, 4), (3, 2)], "fit": "linear"},
        ]
        fitted = fit_series(normalize_series(raw))
        self.assertEqual([s["_stats"]["slope"] for s in fitted], [1, -2])
        self.assertNotIn("curve", raw[0])
        self.assertEqual(len(nodes(make_scatter(raw), "confidence-band")), 2)
        slope, intercept, r2, p, se, rmse = _linreg([1, 2, 3], [1, 3, 2])
        self.assertAlmostEqual(p, 2 / 3, places=12)
        series = fit_series(normalize_series([{"name": "A", "points": [(1, 1), (2, 3), (3, 2)], "fit": "linear"}]))
        center = series[0]["curve"][50]
        self.assertAlmostEqual(center["hi"] - center["y"], 12.7062047364 * rmse / math.sqrt(3), places=7)
        series = normalize_series([{"points": [{"x": 3, "y": 4, "x_err": [2, 5], "y_err": [6, 9]}]}])
        x, y = infer_scales(series)
        self.assertLessEqual(x.domain[0], 1)
        self.assertGreaterEqual(x.domain[1], 8)
        self.assertLessEqual(y.domain[0], -2)
        self.assertGreaterEqual(y.domain[1], 13)
        svg = make_scatter(series)
        self.assertEqual(len(nodes(svg, "x-error")), 1)
        self.assertEqual(len(nodes(svg, "y-error")), 1)
        svg = make_scatter([(1, 2), (2, 3)], highlight_mask=[False, True])
        fills = [p.get("fill") for p in nodes(svg, "observation")]
        self.assertNotEqual(fills[0], fills[1])
        svg = make_bubble([(1, 2, 0, ""), (2, 3, 1, ""), (3, 4, 4, "")], multi_mode="single")
        ps = nodes(svg, "observation")
        self.assertEqual(len(ps), 2)
        self.assertAlmostEqual((float(ps[1].get("r")) / float(ps[0].get("r"))) ** 2, 4, places=5)
        svg = make_scatter_fit([{"name": "A", "points": [(1, 2)], "curve": [(0, 0), (2, 4)]}], multi_mode="single")
        self.assertEqual(len(nodes(svg, "observation")), 1)
        self.assertTrue(nodes(svg, "curve"))
        data = normalize_series([{"name": "B", "points": [(5, 5)]}])
        context = SeriesContext(["A", "B"], series_colors=["#ff0000", "#0055aa"])
        fragment = render_xy_plot(
            data,
            BBox(10, 20, 210, 120),
            x_scale=SharedScale((0, 10), [0, 5, 10]),
            y_scale=SharedScale((0, 10), [0, 5, 10]),
            context=context,
        )
        node = nodes("<svg>" + fragment + "</svg>", "observation")[0]
        self.assertEqual(node.get("fill"), "#0055aa")
        self.assertEqual(float(node.get("cx")), 110)
        self.assertEqual(float(node.get("cy")), 70)
        self.assertNotIn("<svg", fragment)
        self.assertNotIn("transform=", fragment)

    def test_xy_volcano_group_means_axes_and_invalid_input(self):
        from embed_svg_validator import validate_embedded_svgs

        points = [
            {"name": "A", "log2fc": 2, "neg_log10_p": 2},
            {"name": "B", "log2fc": 3, "neg_log10_p": 3},
            {"name": "C", "log2fc": -3, "neg_log10_p": 3},
        ]
        classified, threshold, _ = classify_volcano(points, threshold={"s0": 2})
        self.assertEqual([p["category"] for p in classified], ["ns", "up", "down"])
        for p in classified:
            self.assertEqual(p["category"] != "ns", p["np"] >= threshold(p["fc"]))
        self.assertTrue(nodes(make_volcano(points, threshold={"s0": 2}), "curve"))
        with self.assertRaisesRegex(ValueError, "conflicts"):
            make_volcano([dict(points[0], is_up=True)], threshold={"s0": 2})
        svg = make_scatter(
            [{"name": "A", "points": [(1, 2), (3, 4), (5, 6)]}, {"name": "B", "points": [(4, 2), (6, 4)]}], summary=True
        )
        summaries = nodes(svg, "summary-mean")
        self.assertEqual(
            [(float(p.get("data-mean-x")), float(p.get("data-mean-y"))) for p in summaries], [(3, 4), (5, 3)]
        )
        self.assertEqual(len(nodes(svg, "summary-x-sem")), 2)
        self.assertEqual(len(nodes(svg, "summary-y-sem")), 2)
        points = [
            {"x": "甲", "y": 2, "group": "A"},
            {"x": "甲", "y": 4, "group": "A"},
            {"x": "乙", "y": 5, "group": "A"},
        ]
        svg = make_scatter(points, summary=True)
        self.assertEqual([float(p.get("data-y")) for p in nodes(svg, "observation")], [2, 4, 5])
        self.assertEqual([float(p.get("data-mean")) for p in nodes(svg, "summary-mean")], [3, 5])
        svg = make_scatter([{"x": 2, "y": "甲"}, {"x": 4, "y": "甲"}], summary=True)
        self.assertEqual(float(nodes(svg, "summary-mean")[0].get("data-mean")), 3)
        svg = make_line_band(
            [{"name": "A", "x": [0, 1, 2], "y_mean": [1, 3, 2], "y_err": [0.1, 0.2, 0.1]}],
            phases=[{"start": 0, "end": 1, "label": "Stage I"}],
            significance=[{"x": 1, "p": 0.01}],
            sample_sizes=[5, 8, 6],
        )
        self.assertEqual([p.get("data-n") for p in nodes(svg, "sample-size")], ["5", "8", "6"])
        self.assertEqual(len(nodes(svg, "significance")), 1)
        self.assertEqual(len(nodes(svg, "phase")), 1)
        svg = make_line_band(
            [{"name": "A", "points": [(1, 2), (10, 4), (100, 8)], "curve": [(1, 2), (5, 3), (30, 6), (100, 8)]}],
            x_transform="log10",
        )
        x = [float(p.get("cx")) for p in nodes(svg, "observation")]
        self.assertAlmostEqual(x[1] - x[0], x[2] - x[1], places=3)
        with self.assertRaisesRegex(ValueError, "positive"):
            make_scatter([{"x": 1, "y": 2, "x_err": 2}], x_transform="log10")
        for values in ([1e9, 1e9 + 0.0001, 1e9 + 0.0002], [1e-12, 2e-12, 3e-12]):
            series = normalize_series([{"points": [(x, x) for x in values]}])
            x, _y = infer_scales(series)
            fmt, annotation = _axis_format(x)
            labels = [fmt(v) for v in x.ticks]
            self.assertEqual(len(labels), len(set(labels)))
            self.assertTrue(annotation)
            fit = fit_series(normalize_series([{"points": [(x, x) for x in values], "fit": "linear"}]))
            self.assertAlmostEqual(fit[0]["_stats"]["slope"], 1)
        svg = make_scatter(
            [{"name": "A", "points": [{"x": 1, "y": 2, "label": "A & B"}, {"x": 2, "y": 3}], "fit": "linear"}]
        )
        slide = ET.Element("slide")
        ET.SubElement(slide, "embed").append(ET.fromstring(svg))
        self.assertEqual(validate_embedded_svgs(slide), [])
        svg = make_scatter_fit([(i, i * 0.3 + 2) for i in range(40)], width=600, height=400)
        self.assertEqual(len(nodes(svg, "observation")), 40)
        self.assertNotIn(">Residual<", svg)
        for fn in [
            lambda: make_scatter([(1, math.nan)]),
            lambda: make_scatter([{"x": 2, "y": 3, "y_err": -1}]),
            lambda: make_scatter_fit([(1, 1), (1, 3)]),
            lambda: make_scatter([(1, 2)], fit="quadratic"),
            lambda: make_bubble([(1, 2, -1)]),
            lambda: make_line_band([{"x": [1, 2], "y_mean": [2, 3], "y_ci_dn": [1], "y_ci_up": [3, 4]}]),
            lambda: make_volcano([{"log2fc": 1, "neg_log10_p": -1}]),
        ]:
            with self.assertRaises(ValueError):
                fn()

    def test_measured_text_bounds_no_overlaps_in_representative_layout(self):
        series = [
            {
                "name": "Long category A with a meaningful experimental condition",
                "points": [{"x": i, "y": i * 1.2 + 1, "label": "Key gene alpha" if i == 2 else ""} for i in range(6)],
                "fit": "linear",
            },
            {
                "name": "中文实验处理条件二",
                "points": [{"x": i, "y": i * 0.5 + 2, "label": "关键标记乙" if i == 4 else ""} for i in range(6)],
                "fit": "linear",
            },
        ]
        svg = make_scatter(
            series,
            title="分组实验的独立观测与预测曲线",
            subtitle="Bands encode confidence in the fitted mean",
            x_title="Exposure duration",
            y_title="Observed response",
            show_stats_box=True,
            note="Measurement error is supplied by the instrument.",
            width=1100,
            height=800,
        )
        width, height, boxes = _text_boxes(svg)
        for a in boxes:
            self.assertGreaterEqual(a[0], -1)
            self.assertGreaterEqual(a[1], -1)
            self.assertLessEqual(a[2], width + 1)
            self.assertLessEqual(a[3], height + 1)
        for i, a in enumerate(boxes):
            for b in boxes[:i]:
                overlap = (min(a[2], b[2]) - max(a[0], b[0]), min(a[3], b[3]) - max(a[1], b[1]))
                self.assertFalse(overlap[0] > 1 and overlap[1] > 1, (a[4], b[4], overlap))


class ScientificXYReviewRegressions(unittest.TestCase):
    def assert_text_clear(self, svg):
        width, height, boxes = _text_boxes(svg)
        for i, a in enumerate(boxes):
            self.assertTrue(a[0] >= -0.5 and a[1] >= -0.5 and a[2] <= width + 0.5 and a[3] <= height + 0.5, a)
            for b in boxes[:i]:
                self.assertFalse(
                    min(a[2], b[2]) - max(a[0], b[0]) > 1 and min(a[3], b[3]) - max(a[1], b[1]) > 1, (a, b)
                )

    def test_r1_residuals_colours_categories_and_size_descriptions(self):
        points = [(10 ** (i / 10), 10 ** (i / 5)) for i in range(31)]
        fitted = fit_series(
            normalize_series([{"name": "Perfect", "points": points, "fit": "linear"}]),
            x_transform="log10",
            y_transform="log10",
        )
        # Removing the plotting samples must not change fitted residuals.
        fitted[0]["curve"] = fitted[0]["curve"][::50]
        residuals = _residuals(fitted)
        self.assertLess(max(abs(p["y"]) for p in residuals[0]["points"]), 1e-12)
        self.assertEqual(residuals[0]["_residual_unit"], "log10(y)")
        series = [
            {"name": "A", "x": [1, 2, 3], "y_mean": [1, 2, 3]},
            {"name": "B", "x": [10, 20, 30], "y_mean": [3, 2, 1], "n_per_point": [9, 8, 7]},
        ]
        svg = make_line_band(series, show_n_per_point=True)
        samples = nodes(svg, "sample-size")
        observed = {
            p.get("data-x"): float(p.get("cx")) for p in nodes(svg, "observation") if p.get("data-series") == "B"
        }
        for p in samples:
            self.assertEqual(p.get("data-series"), "B")
            self.assertAlmostEqual(float(p.get("x")) + float(p.get("width")) / 2, observed[p.get("data-x")], places=3)
        series[0]["n_per_point"] = [9, 8, 7]
        svg = make_line_band(series, show_n_per_point=True, height=900)
        self.assertEqual({p.get("data-series") for p in nodes(svg, "sample-size")}, {"A", "B"})
        self.assertEqual(len(nodes(svg, "sample-size")), 6)
        self.assert_text_clear(svg)
        curve = [(-3, 2), (-1.9992, 2), (-1.999, 6), (-1.9988, 2), (0, 2), (3, 2)]
        points = [{"log2fc": -1.999, "neg_log10_p": 5}, {"log2fc": 2, "neg_log10_p": 5}]
        classified, fn, _ = classify_volcano(points, threshold={"curve": curve})
        branches = _threshold_branches(fn, -3, 3, 1, [-1.999, 2], 8)
        self.assertIn({"x": -1.999, "y": 6}, [p for b in branches for p in b])
        self.assertEqual([p["category"] for p in classified], ["ns", "up"])
        fn = lambda x: 2 + 4 * math.exp(-(((x + 1.999) / 0.0001) ** 2))
        branches = _threshold_branches(fn, -3, 3, 1, [-1.999, 2], 8)
        self.assertIn({"x": -1.999, "y": 6}, [p for b in branches for p in b])
        svg = make_line_band(
            [{"name": "A", "x": [0, 1], "y_mean": [1, 3]}, {"name": "B", "x": [0, 1], "y_mean": [3, 2]}],
            highlight_series="B",
        )
        colors = {p.get("data-series"): p.get("fill") for p in nodes(svg, "observation")}
        self.assertNotEqual(colors["A"], colors["B"])
        widths = {p.get("data-series"): float(p.get("stroke-width")) for p in nodes(svg, "curve")}
        self.assertGreater(widths["B"], widths["A"])
        svg = make_line_band(
            [
                {
                    "curve": [
                        {"x": 0, "y": 1, "lo": 0.5, "hi": 1.5},
                        {"x": 1, "y": 2, "lo": 1.5, "hi": 2.5},
                        {"x": 2, "y": 3},
                        {"x": 3, "y": 4, "lo": 3.5, "hi": 4.5},
                    ]
                }
            ]
        )
        self.assertEqual(len(nodes(svg, "confidence-band")), 1)
        self.assertEqual(len(nodes(svg, "confidence-interval")), 1)
        series = normalize_series([{"name": "A", "points": [("C", 1)]}, {"name": "B", "points": [("C", 2)]}])
        kwargs = {
            "x_scale": CategoryScale(["C"]),
            "y_scale": SharedScale((0, 4), [0, 2, 4]),
            "context": SeriesContext(["A", "B"]),
        }
        all_svg = "<svg>" + render_xy_plot(series, BBox(50, 50, 450, 350), **kwargs) + "</svg>"
        sub_svg = "<svg>" + render_xy_plot(series[1:], BBox(50, 50, 450, 350), **kwargs) + "</svg>"
        self.assertEqual(nodes(all_svg, "observation")[1].get("cx"), nodes(sub_svg, "observation")[0].get("cx"))
        points = [
            {"x": i % 4 + 1, "y": f"免疫细胞亚群{i + 1:02d} · Long experimental condition / dose 100 mg"}
            for i in range(22)
        ]
        self.assert_text_clear(make_scatter(points, width=1000, height=760))
        with self.assertRaisesRegex(ValueError, "category labels"):
            make_scatter(points, width=600, height=400)
        svg = make_line_band(
            [{"name": "A", "x": [0, 0.01, 0.02, 10], "y_mean": [1, 2, 3, 4]}],
            sample_sizes=[50, 48, 47, 40],
            width=1000,
            height=700,
        )
        bars = nodes(svg, "sample-size")
        for i in range(1, len(bars)):
            a, b = bars[i - 1], bars[i]
            self.assertLessEqual(float(a.get("x")) + float(a.get("width")), float(b.get("x")) + 0.0001)
        self.assertEqual([p.get("data-x") for p in bars], ["0.0", "0.01", "0.02", "10.0"])
        self.assert_text_clear(svg)
        points = [(1, 2, 1), (2, 3, 2), (3, 2, 4)]
        label = (
            "Normalized mitochondrial respiratory chain assembly and transcription regulation / 全量观测转录因子群的归一化表达总量 "
            * 2
        )
        self.assert_text_clear(make_bubble(points, color_values=[0, 1, 2], color_unit=label, width=900, height=750))
        self.assert_text_clear(make_bubble(points, size_unit=label, width=800, height=700))
        svg = make_bubble([(1, 2, 1), (2, 3, 4)], color_values=[0, 1])
        a, b = nodes(svg, "observation")
        self.assertNotEqual(a.get("fill"), a.get("stroke"))
        self.assertAlmostEqual((float(b.get("r")) / float(a.get("r"))) ** 2, 4)
        with self.assertRaisesRegex(ValueError, "significance x"):
            make_line_band([{"x": [0, 1, 2], "y_mean": [1, 2, 3]}], significance=[{"x": 100, "p": 0.01}])


class ScientificXYSecondReviewRegressions(unittest.TestCase):
    def assert_svg_clear(self, svg):
        from embed_svg_validator import detect_embedded_svg_overlaps, validate_embedded_svgs

        slide = ET.Element("slide")
        ET.SubElement(slide, "embed").append(ET.fromstring(svg))
        self.assertEqual(validate_embedded_svgs(slide), [])
        self.assertEqual(detect_embedded_svg_overlaps(slide), [])

    def test_r2_interpolation_category_curves_marginals_and_leaders(self):
        series = normalize_series(
            [{"name": "External", "points": [(1, 1), (10, 100), (100, 10000)], "curve": [(1, 1), (100, 10000)]}]
        )
        xs, ys = infer_scales(series, x_transform="log10", y_transform="log10")
        box = BBox(60, 60, 660, 460)
        svg = "<svg>" + render_xy_plot(series, box, x_scale=xs, y_scale=ys) + "</svg>"
        vertex = [
            tuple(map(float, p))
            for path in nodes(svg, "curve")
            for p in re.findall(r"[ML]([^, ]+),([^ ]+)", path.get("d"))
        ]
        expected = (xs.map(10, 60, 660), ys.map(910, 460, 60))
        self.assertLess(min(math.dist(p, expected) for p in vertex), 0.001)
        self.assertEqual(interpolate_curve(series[0]["curve"], 10), 910)
        self.assertAlmostEqual(
            _residuals(series, y_transform="log10")[0]["points"][1]["y"], 2 - math.log10(910), places=12
        )
        # Check the full raw linear function against rendered log-space segments.
        segments = []
        for path in nodes(svg, "curve"):
            segments.append([tuple(map(float, p)) for p in re.findall(r"[ML]([^, ]+),([^ ]+)", path.get("d"))])
        for i in range(101):
            x = 10 ** (i / 50)
            px = xs.map(x, 60, 660)
            actual = ys.map(101 * x - 100, 460, 60)
            for a, b in segments:
                if a[0] - 0.001 <= px <= b[0] + 0.001:
                    interpolated = a[1] + (b[1] - a[1]) * (px - a[0]) / (b[0] - a[0])
                    self.assertLess(abs(actual - interpolated), 0.15)
                    break
            else:
                self.fail("missing curve segment")
        svg = make_line_band(
            [
                {
                    "name": "A",
                    "x": ["T0", "T1", "T2"],
                    "y_mean": [1, 2, 3],
                    "y_ci_dn": [0.5, 1.5, 2.5],
                    "y_ci_up": [1.5, 2.5, 3.5],
                },
                {"name": "B", "x": ["T0", "T1", "T2"], "y_mean": [3, 2, 1]},
            ]
        )
        for observation in nodes(svg, "observation"):
            expected = (float(observation.get("cx")), float(observation.get("cy")))
            vertices = [
                tuple(map(float, p))
                for curve in nodes(svg, "curve")
                if curve.get("data-series") == observation.get("data-series")
                for p in re.findall(r"[ML]([^, ]+),([^ ]+)", curve.get("d"))
            ]
            self.assertLess(min(math.dist(p, expected) for p in vertices), 0.001)
        band_xs = [float(p[0]) for p in re.findall(r"[ML]([^, ]+),([^ ]+)", nodes(svg, "confidence-band")[0].get("d"))]
        for observation in nodes(svg, "observation")[:3]:
            self.assertLess(min(abs(x - float(observation.get("cx"))) for x in band_xs), 0.001)
        name = "Mitochondrial response after intervention / 全量呼吸链实验条件与长名称 " * 4
        svg = make_line_band(
            [{"name": name, "x": [0, 1, 2], "y_mean": [1, 2, 3], "n_per_point": [10, 9, 8]}],
            show_n_per_point=True,
            width=800,
            height=1000,
        )
        self.assert_svg_clear(svg)
        text = "".join(ET.fromstring(svg).itertext())
        self.assertIn("".join(name.split()), "".join(text.split()))
        self.assertEqual(len(nodes(svg, "sample-size")), 3)
        cats = [
            "Baseline / 干预前完整测量",
            "Early treatment / 早期干预后测量",
            "Late treatment / 长期干预后的完整测量",
            "Recovery / 恢复阶段完整测量",
        ]
        svg = make_line_band(
            [{"name": "Treatment", "x": cats, "y_mean": [1, 2, 3, 2], "n_per_point": [10, 9, 8, 7]}],
            show_n_per_point=True,
            width=800,
            height=850,
        )
        self.assert_svg_clear(svg)
        ticks = nodes(svg, "x-tick")
        self.assertGreater(len(ticks), len(cats))
        self.assertEqual("".join("".join(p.itertext()) for p in ticks).replace(" ", ""), "".join(cats).replace(" ", ""))
        for axis in ("x", "y"):
            for value in (math.nan, math.inf, -math.inf):
                with self.assertRaisesRegex(ValueError, "reference value"):
                    make_scatter([(0, 0), (1, 1)], reference_lines=[{"axis": axis, "value": value}])
        svg = make_scatter([("A", 1), ("B", 2)], reference_lines=[{"axis": "x", "value": "B"}])
        self.assertEqual(len(nodes(svg, "reference")), 1)
        data = normalize_series(
            [{"name": "A", "points": [(1, 1), (1, 1), (2, 2)]}, {"name": "B", "points": [(1, 1), (1, 1), (2, 2)]}]
        )
        context = SeriesContext(["A", "B"], pal=_resolve_palette("archive_ink"))
        for axis, box in (("x", BBox(40, 30, 460, 130)), ("y", BBox(40, 30, 180, 430))):
            svg = (
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 500">'
                + _marginal(data, box, SharedScale((0, 3), [0, 1, 2, 3]), context, axis)
                + "</svg>"
            )
            self.assert_svg_clear(svg)
            for name in ("A", "B"):
                self.assertEqual(
                    sum(int(p.get("data-count")) for p in nodes(svg, "marginal-count") if p.get("data-series") == name),
                    3,
                )
            rectangles = nodes(svg, "marginal-count")
            for i, a in enumerate(rectangles):
                ax, ay, aw, ah = (float(a.get(k)) for k in ("x", "y", "width", "height"))
                for b in rectangles[:i]:
                    bx, by, bw, bh = (float(b.get(k)) for k in ("x", "y", "width", "height"))
                    self.assertFalse(
                        min(ax + aw, bx + bw) - max(ax, bx) > 0.001 and min(ay + ah, by + bh) - max(ay, by) > 0.001
                    )
        data = normalize_series(
            [
                {
                    "name": "Sites",
                    "points": [
                        {"x": 1, "y": 2, "size": 1, "components": [2, 3]},
                        {"x": 2, "y": 3, "size": 4, "components": [1, 5]},
                    ],
                }
            ]
        )
        calls = []

        def glyph(point, x, y, radius, color):
            calls.append((point["components"], x, y, radius, color))
            return f'<circle cx="{x:.4f}" cy="{y:.4f}" r="{radius:.4f}" fill="{color}" data-role="custom-envelope"/>'

        svg = make_xy_chart(data, glyph_renderer=glyph, radius_max=18)
        self.assertEqual([call[0] for call in calls], [[2, 3], [1, 5]])
        self.assertEqual([call[3] for call in calls], [9, 18])
        self.assertEqual([p.get("data-series") for p in nodes(svg, "observation")], ["Sites", "Sites"])
        self.assertEqual(len(nodes(svg, "custom-envelope")), 2)
        self.assert_svg_clear(svg)
        for other in ((5.25, 4.625), (5.12, 4.8)):
            data = normalize_series(
                [
                    {
                        "name": "G",
                        "points": [
                            {"x": 5, "y": 5, "size": 1, "label": "Source"},
                            {"x": other[0], "y": other[1], "size": 4},
                        ],
                    }
                ]
            )
            svg = (
                "<svg>"
                + render_xy_plot(
                    data,
                    BBox(50, 50, 650, 450),
                    x_scale=SharedScale((0, 10), [0, 5, 10]),
                    y_scale=SharedScale((0, 10), [0, 5, 10]),
                    label_bbox=BBox(680, 60, 800, 430),
                )
                + "</svg>"
            )
            path = [
                tuple(map(float, p))
                for p in re.findall(r"[ML]([^, ]+),([^ ]+)", nodes(svg, "label-leader")[0].get("d"))
            ]
            for circle in nodes(svg, "observation"):
                center = (float(circle.get("cx")), float(circle.get("cy")))
                if math.dist(center, path[0]) < 0.01:
                    continue
                for i in range(1, len(path)):
                    a, b = path[i - 1], path[i]
                    dx, dy = b[0] - a[0], b[1] - a[1]
                    t = max(0, min(1, ((center[0] - a[0]) * dx + (center[1] - a[1]) * dy) / (dx * dx + dy * dy)))
                    self.assertGreaterEqual(math.dist(center, (a[0] + t * dx, a[1] + t * dy)), float(circle.get("r")))


# ====================================================================================================
# Composition additions preserve source data, scalar bands and sample statistics.
# ====================================================================================================


def geometry(svg):
    return json.loads(nodes(svg, "heterogeneous-panels-layout")[0].get("data-layout"))


def xy_source():
    return {
        "id": "source",
        "kind": "xy",
        "data": {
            "series": [
                {
                    "name": "Prediction",
                    "curve": [{"x": 0, "y": 0, "lo": -1, "hi": 1}, {"x": 10, "y": 10, "lo": 9, "hi": 11}],
                }
            ]
        },
    }


def test_zoom_clips_curve_and_band_at_real_domain_edges_without_resampling_observations():
    source = xy_source()
    data = [source, {"id": "zoom", "detail_of": "source", "x_range": [2, 4], "y_range": [1, 5]}]
    before = deepcopy(data)
    svg = make_composite(data, template="panels")
    assert data == before
    assert not nodes(svg, "observation")
    layout = geometry(svg)
    zoom = layout["panels"][1]
    assert zoom["axes"]["x"]["domain"] == [2, 4]
    assert zoom["axes"]["y"]["domain"] == [1, 5]
    assert len(layout["connections"]) == 2
    panel = nodes(svg, "heterogeneous-panel")[1]
    curve = nodes(panel, "curve")[0]
    pairs = [tuple(map(float, pair)) for pair in re.findall(r"([\d.-]+),([\d.-]+)", curve.get("d"))]
    x0, y0, x1, y1 = zoom["plot_bbox"]
    assert pairs[0][0] == pytest.approx(x0, abs=0.01)
    assert pairs[-1][0] == pytest.approx(x1, abs=0.01)
    assert pairs[0][1] == pytest.approx(y1 - (2 - 1) / 4 * (y1 - y0), abs=0.01)
    assert pairs[-1][1] == pytest.approx(y1 - (4 - 1) / 4 * (y1 - y0), abs=0.01)
    assert nodes(panel, "confidence-band")


def test_detail_inherits_shared_source_axes_and_is_enlarged():
    source = xy_source()
    source["x_group"] = "time"
    other = deepcopy(source)
    other["id"] = "other"
    other["data"]["series"][0]["curve"][1].update(x=100)
    svg = make_composite([source, other, {"id": "detail", "detail_of": "source"}], template="panels", cols=2)
    ps = geometry(svg)["panels"]
    assert ps[2]["axes"]["x"]["domain"] == ps[0]["axes"]["x"]["domain"]
    assert ps[2]["plot_bbox"][2] - ps[2]["plot_bbox"][0] > ps[0]["plot_bbox"][2] - ps[0]["plot_bbox"][0]


@pytest.mark.parametrize(
    "record",
    [
        {"detail_of": "unknown"},
        {"detail_of": "source", "x_range": [4, 2]},
        {"detail_of": "source", "x_range": [-100, 2]},
        {"detail_of": "source", "data": {}},
        {"detail_of": "source", "x_group": "time"},
        {"detail_of": "source", "span": 0},
    ],
)
def test_invalid_detail_is_rejected(record):
    with pytest.raises(ValueError) as exc:
        make_composite([xy_source(), record], template="panels")
    assert str(exc.value)


def test_mortality_inset_has_independent_curves_and_no_inferred_observations():
    source = xy_source()
    source["data"]["inset"] = {
        "name": "Mortality",
        "series": [{"name": "Mortality", "curve": [(0, 2), (10, 8)]}],
        "annotations": ["Supplied overall P = 0.02"],
    }
    svg = make_composite([source], template="panels")
    assert len(nodes(svg, "xy-inset")) == 1
    assert len(nodes(svg, "curve")) == 2
    assert not nodes(svg, "observation")
    assert "Supplied overall P = 0.02" in svg
    p = geometry(svg)["panels"][0]
    assert p["inset"]["y_domain"] != p["axes"]["y"]["domain"]


def test_radar_detail_uses_identical_data_ranges_and_larger_radius():
    src = {
        "id": "radar",
        "kind": "radar",
        "data": {
            "axes": [{"name": c, "min": 0, "max": 10} for c in "ABC"],
            "series": [{"name": "S", "values": [2, 4, 8]}],
            "grid": "circle",
        },
    }
    svg = make_composite([src, {"id": "detail", "detail_of": "radar"}], template="panels", cols=2)
    panels = nodes(svg, "heterogeneous-panel")
    first, second = [nodes(p, "radar-point") for p in panels]
    assert [p.get("data-value") for p in first] == [p.get("data-value") for p in second]
    assert [p.get("data-domain") for p in first] == [p.get("data-domain") for p in second]
    assert float(second[0].get("data-radius")) > float(first[0].get("data-radius"))


def test_filled_contours_share_true_levels_colors_and_xy_domains():
    ps = [
        {
            "id": str(i),
            "kind": "contour",
            "x_group": "x",
            "y_group": "y",
            "z_group": "z",
            "data": {"grid": [[0, v], [v, 0]], "x_coords": [2, 4], "y_coords": [100, 300], "levels": [0.25, 0.5, 0.75]},
        }
        for i, v in enumerate((1, 0.8))
    ]
    svg = make_composite(ps, template="panels")
    panels = nodes(svg, "heterogeneous-panel")
    bands = [nodes(p, "contour-band") for p in panels]
    signatures = [[(b.get("data-low"), b.get("data-high"), b.get("fill")) for b in row] for row in bands]
    assert signatures[0] == signatures[1]
    assert "L" in bands[0][1].get("d")
    assert geometry(svg)["panels"][0]["axes"] == geometry(svg)["panels"][1]["axes"]


@pytest.mark.parametrize(
    "data",
    [
        {"grid": []},
        {"grid": [[1, 2], [3]]},
        {"grid": [[1, 2], [3, 4]], "levels": [2, 1]},
        {"grid": [[0, 1], [2, 3]], "log_z": True},
        {"grid": [[1, 2], [3, 4]], "x_coords": [1, 1]},
    ],
)
def test_invalid_contour_fields_are_rejected(data):
    with pytest.raises(ValueError) as exc:
        make_composite([{"kind": "contour", "data": data}], template="panels")
    assert str(exc.value)


# ====================================================================================================
# Scientific and layout contracts for complete pairs compositions.
# ====================================================================================================


def records():
    return [
        {
            "time": i + 1,
            "response": 3 + i * 0.3 + math.sin(i),
            "marker": math.cos(i),
            "group": "Untreated control cells" if i % 2 else "中文实验处理条件",
        }
        for i in range(32)
    ]


class CompositionStatisticsTest(unittest.TestCase):
    def test_composition_statistics_histograms_kdes_boxes_and_correlation(self):
        edges, counts = histogram([0, 0.5, 1, 2, 3], (0, 3), 3)
        self.assertEqual(edges, [0, 1, 2, 3])
        self.assertEqual(counts, [2, 1, 2])
        scale = SharedScale((1, 1000), transform="log10")
        data = normalize_series([{"name": "A", "points": [(1, 1), (10, 2), (100, 3), (1000, 4)]}])
        profile = marginal_profiles(data, "x", scale, "hist", bins=3)[0]
        self.assertEqual(profile["xs"], [0, 1, 2, 3])
        self.assertEqual(profile["ys"], [1, 1, 2])
        scale = SharedScale((-5, 5))
        data = normalize_series([{"name": "A", "points": [(0, 1)]}])
        profile = marginal_profiles(data, "x", scale, "kde", bandwidth=1)[0]
        mid = len(profile["ys"]) // 2
        self.assertAlmostEqual(profile["xs"][mid], 0)
        self.assertAlmostEqual(profile["ys"][mid], 10 / math.sqrt(2 * math.pi))
        integral = math.fsum(profile["ys"][i] + profile["ys"][i + 1] for i in range(len(profile["ys"]) - 1)) / (
            2 * (len(profile["ys"]) - 1)
        )
        self.assertAlmostEqual(integral, 1, places=5)
        data = normalize_series([{"name": "A", "points": [(1, 1), (10, 2), (100, 3), (1000, 4)]}])
        scale = SharedScale((1, 1000), transform="log10")
        profile = marginal_profiles(data, "x", scale, "box")[0]
        self.assertAlmostEqual(profile["stats"]["median"], 1.5)
        self.assertEqual(profile["stats"]["lo"], 0)
        self.assertEqual(profile["stats"]["hi"], 3)
        self.assertEqual(profile["outliers"], [])
        points = [{"x": x, "y": y} for x, y in [(-1, -1), (-1, 1), (1, -1), (1, 1)]]
        scale = SharedScale((-4, 4))
        ellipse = covariance_ellipse(points, scale, scale, 0.95)
        radius = math.sqrt(-2 * math.log(0.05) * 4 / 3)
        self.assertAlmostEqual(max(point["x"] for point in ellipse), radius)
        self.assertAlmostEqual(min(point["y"] for point in ellipse), -radius)
        scale = SharedScale((0.001, 1000), transform="log10")
        points = [{"x": 10**x, "y": 10**y} for x, y in [(-1, -1), (-1, 1), (1, -1), (1, 1)]]
        ellipse = covariance_ellipse(points, scale, scale)
        self.assertAlmostEqual(math.log10(max(point["x"] for point in ellipse)), math.sqrt(-2 * math.log(0.05) * 4 / 3))
        with self.assertRaisesRegex(ValueError, "nonsingular"):
            covariance_ellipse([{"x": i, "y": i} for i in (1, 2, 3)], scale, scale)

        scale = SharedScale((-4e-200, 4e-200))
        points = [{"x": x * 1e-200, "y": y * 1e-200} for x, y in [(-1, -1), (-1, 1), (1, -1), (1, 1)]]
        ellipse = covariance_ellipse(points, scale, scale)
        self.assertGreater(max(point["x"] for point in ellipse), 2e-200)
        self.assertEqual(average_ranks([3, 1, 1, 2]), [4, 1.5, 1.5, 3])
        self.assertAlmostEqual(correlation([1, 1, 2], [1, 2, 3], "spearman"), math.sqrt(3) / 2)
        self.assertIsNone(correlation([1, 1, 1], [2, 3, 4]))
        self.assertIsNone(correlation([1], [2]))

        self.assertAlmostEqual(
            correlation([1e9 + i * 1e-4 for i in range(8)], [i * 1e-210 for i in range(8)]), 1, places=7
        )
        scale = SharedScale((0, 1))
        points = [{"x": 0.25 + i * 0.001, "y": 0.75 + i * 0.001} for i in range(5)]
        grid_x, grid_y, values = kde2d(points, scale, scale)
        peak_j, peak_i = max(
            ((j, i) for j in range(len(grid_y)) for i in range(len(grid_x))), key=lambda pair: values[pair[0]][pair[1]]
        )
        self.assertLess(abs(grid_x[peak_i] - 0.25), 0.03)
        self.assertLess(abs(grid_y[peak_j] - 0.75), 0.03)
        scale = SharedScale((0, 1e8))
        points = [{"x": 1 + i * 0.001, "y": 2 + math.sin(i) * 0.001} for i in range(10)]
        data = normalize_series([{"name": "A", "points": points}])
        profile = marginal_profiles(data, "x", scale, "kde")[0]
        self.assertGreater(max(profile["ys"]), 1e8)
        gx, gy, density = kde2d(points, scale, scale)
        self.assertGreater(max(max(row) for row in density), 1e16)
        self.assertLess(max(gx), 1e-6)
        self.assertLess(max(gy), 1e-6)


class GroupedHistogramTest(unittest.TestCase):
    def test_grouped_histogram_lanes_and_log_geometry(self):
        from ..charts._academic_rigor import SeriesContext

        scale = SharedScale((0, 4))
        series = normalize_series([{"name": name, "points": [(1, 1), (2, 2), (4, 4)]} for name in ["B", "A"]])
        context = SeriesContext(["A", "B"])
        profiles = marginal_profiles(series, "x", scale, "hist", 4)
        for axis in ("x", "y"):
            svg = (
                "<svg>" + render_marginal(profiles, (0, 0, 400, 200), scale, context, kind="hist", axis=axis) + "</svg>"
            )
            bars = nodes(svg, "marginal-count")
            self.assertEqual(sum(int(b.get("data-count")) for b in bars), 6)
            for index in {b.get("data-bin") for b in bars}:
                pair = [b for b in bars if b.get("data-bin") == index]
                self.assertEqual(pair[0].get("data-bin-min"), pair[1].get("data-bin-min"))
                coordinate = "x" if axis == "x" else "y"
                extent = "width" if axis == "x" else "height"
                a, b = sorted(pair, key=lambda b: float(b.get(coordinate)))
                self.assertLess(float(a.get(coordinate)) + float(a.get(extent)), float(b.get(coordinate)))
                self.assertEqual(a.get("data-series"), "A")
        scale = SharedScale((1, 1000), transform="log10")
        series = normalize_series([{"name": name, "points": [(1, 1), (10, 10), (1000, 1000)]} for name in ["A", "B"]])
        profiles = marginal_profiles(series, "x", scale, "hist", 3)
        svg = (
            "<svg>"
            + render_marginal(profiles, (0, 0, 300, 100), scale, SeriesContext(["A", "B"]), kind="hist")
            + "</svg>"
        )
        bars = nodes(svg, "marginal-count")
        self.assertEqual(sum(int(b.get("data-count")) for b in bars), 6)
        self.assertEqual(max(float(b.get("data-bin-max")) for b in bars), 1000)


class FrequencyGlyphTest(unittest.TestCase):
    def test_frequency_glyphs_preserve_observations_ties_and_fits(self):
        import json
        import xml.etree.ElementTree as ET
        from embed_svg_validator import detect_embedded_svg_overlaps, validate_embedded_svgs
        from ..charts._academic_rigor import SeriesContext
        from ..charts._xy import fit_series

        records = [
            {"x": 1, "y": 2, "group": "A"},
            {"x": 1, "y": 2, "group": "A"},
            {"x": 1, "y": 2, "group": "B"},
            {"x": 3, "y": 5, "group": "B"},
        ]
        svg = make_pairs(records, variables=["x", "y"])
        glyphs = nodes(svg, "frequency-glyph")
        self.assertEqual(sum(int(g.get("data-count")) for g in glyphs), 4)
        repeated = next(g for g in glyphs if g.get("data-count") == "3")
        self.assertEqual(json.loads(repeated.get("data-counts")), {"A": 2, "B": 1})
        self.assertEqual(float(repeated.get("data-x")), 1)
        self.assertEqual(float(repeated.get("data-y")), 2)
        self.assertEqual({n.text for n in nodes(svg, "frequency-count")}, {"3"})
        observations = nodes(svg, "observation")
        areas = {int(float(n.get("data-size"))): float(n.get("data-radius")) ** 2 for n in observations}
        self.assertAlmostEqual(areas[3] / areas[1], 3, places=3)
        self.assertEqual(sum(int(n.get("data-count")) for n in nodes(svg, "marginal-count")), 8)
        self.assertEqual({int(n.get("data-n")) for n in nodes(svg, "correlation-value")}, {2})
        records = [{"constant": 7, "binary": i % 2, "step": i // 3} for i in range(12)]
        svg = make_pairs(records, variables=["constant", "binary", "step"])
        self.assertEqual(sum(int(g.get("data-count")) for g in nodes(svg, "frequency-glyph")), 36)
        self.assertEqual(sum(int(n.get("data-count")) for n in nodes(svg, "marginal-count")), 36)
        self.assertTrue(any(n.get("data-value") == "undefined" for n in nodes(svg, "correlation-value")))
        root = ET.Element("slide")
        ET.SubElement(root, "embed", id="ties").append(ET.fromstring(svg))
        self.assertEqual(validate_embedded_svgs(root) + detect_embedded_svg_overlaps(root), [])
        series = fit_series(
            normalize_series([{"name": "A", "points": [(1, 2), (1, 2), (2, 5), (3, 4)], "fit": "linear"}])
        )
        display, _ = frequency_display(series, SeriesContext(["A"]), 2, font="Arial", ink="#000000", paper="#FFFFFF")
        self.assertEqual(display[0]["curve"], series[0]["curve"])
        self.assertEqual(display[0]["_stats"], series[0]["_stats"])
        self.assertEqual(len(series[0]["points"]), 4)
        self.assertEqual(sum(p["_frequency_total"] for p in display[0]["points"]), 4)


class PairsCompositionTest(unittest.TestCase):
    def test_pairs_observations_correlations_offsets_and_missing_records(self):
        svg = make_pairs(records(), variables=["time", "response", "marker"])
        self.assertEqual(len(nodes(svg, "pairs-lower")), 3)
        self.assertEqual(len(nodes(svg, "observation")), 3 * len(records()))
        self.assertEqual(sum(int(node.get("data-count")) for node in nodes(svg, "marginal-count")), 3 * len(records()))
        rows = [
            {"x": i, "y": i if group == "positive" else -i, "constant": 1, "group": group}
            for group in ("positive", "negative")
            for i in range(1, 6)
        ]
        svg = make_pairs(rows)
        panel = nodes(svg, "pairs-correlation")[0]
        coefficients = [node for node in panel.iter() if node.get("data-role") == "correlation-value"]
        self.assertEqual([float(node.get("data-value")) for node in coefficients], [1, -1])
        self.assertEqual(sum(node.get("data-value") == "undefined" for node in nodes(svg, "correlation-value")), 4)

        svg = make_pairs(records())
        panels = [panel for panel in nodes(svg, "pairs-lower") if panel.get("data-x-variable") == "time"]
        positions = [
            [node.get("cx") for node in panel.iter() if node.get("data-role") == "observation"] for panel in panels
        ]
        self.assertEqual(positions[0], positions[1])
        svg = make_pairs(records(), diagonal="kde", lower="density", method="spearman")
        self.assertEqual(len(nodes(svg, "marginal-density")), 6)
        self.assertEqual(len(nodes(svg, "density-contour")), 18)
        self.assertTrue(all(node.get("data-method") == "spearman" for node in nodes(svg, "correlation-value")))
        self.assertTrue(all(node.get("data-n") == "16" for node in nodes(svg, "density-contour")))
        rows = [{"offset": 1e9 + i * 1e-4, "tiny": (i + 1) * 1e-200, "group": "A"} for i in range(10)]
        svg = make_pairs(rows, width=1100)
        labels = ["".join(node.itertext()) for node in ET.fromstring(svg).iter() if node.tag.endswith("text")]
        self.assertGreaterEqual(sum("× 0.001" in label for label in labels), 2)
        self.assertGreaterEqual(sum("× 1e-199" in label for label in labels), 2)
        self.assertIn("+1000000000.0", labels)
        name = "完整中文实验条件与样本来源组名"
        rows = [{"variable_a": i, "variable_b": i + math.sin(i), "group": name} for i in range(10)]
        svg = make_pairs(
            rows,
            variable_labels={
                "variable_a": "A long variable label that must retain all words",
                "variable_b": "中文长变量标签的完整统计名称",
            },
            extra_panels=[
                {
                    "name": "Additional fit",
                    "series": [{"name": name, "points": [(i, i + math.sin(i)) for i in range(10)]}],
                    "fit": "linear",
                }
            ],
            height=1200,
        )
        texts = "".join(node.text or "" for node in ET.fromstring(svg).iter() if node.tag.endswith("text"))
        self.assertIn(name, texts)
        self.assertIn("中文长变量标签的完整统计名称", texts)
        self.assertEqual(len(nodes(svg, "pairs-extra")), 1)
        self.assertEqual(len({node.get("fill") for node in nodes(svg, "observation")}), 1)
        for rows in ([{"x": 1, "y": 2}, {"x": 3}], [{"x": 1, "y": math.nan}]):
            with self.assertRaises(ValueError):
                make_pairs(rows, variables=["x", "y"])
        with self.assertRaises(ValueError):
            make_pairs(records(), width=350, height=300)


class CompositionLayoutTest(unittest.TestCase):
    def assert_clear_svg(self, svg):
        slide = ET.Element("slide")
        ET.SubElement(slide, "embed").append(ET.fromstring(svg))
        self.assertEqual(validate_embedded_svgs(slide), [])
        width, height, boxes = _text_boxes(svg)
        for i, a in enumerate(boxes):
            self.assertTrue(a[0] >= -0.5 and a[1] >= -0.5 and a[2] <= width + 0.5 and a[3] <= height + 0.5, a)
            for b in boxes[:i]:
                self.assertFalse(
                    min(a[2], b[2]) - max(a[0], b[0]) > 1 and min(a[3], b[3]) - max(a[1], b[1]) > 1, (a, b)
                )

    def test_complete_svg_modes_have_clear_measured_text(self):
        for palette in ("archive_ink", "nightlab"):
            for lower in ("scatter", "density"):
                with self.subTest(palette=palette, lower=lower):
                    self.assert_clear_svg(
                        make_pairs(
                            records(),
                            lower=lower,
                            diagonal="kde",
                            method="spearman",
                            title="多变量与实验条件的统计比较",
                            palette=palette,
                        )
                    )


# ====================================================================================================
# Density adapters preserve probability and the units of supplied observations.
# ====================================================================================================


def _integral(grid, xs, ys):
    return sum(
        (grid[i][j] + grid[i + 1][j] + grid[i][j + 1] + grid[i + 1][j + 1])
        / 4
        * (xs[j + 1] - xs[j])
        * (ys[i + 1] - ys[i])
        for i in range(len(ys) - 1)
        for j in range(len(xs) - 1)
    )


def test_density_grid_integrals_validation_and_marching():
    points = [(i / 10, math.sin(i * 0.8) + i / 40) for i in range(30)]
    grid, xs, ys = density_grid(points)
    assert _integral(grid, xs, ys) == pytest.approx(1, abs=0.003)
    tiny, tiny_x, tiny_y = density_grid([(x * 1e-15, y * 1e-15) for x, y in points])
    assert _integral(tiny, tiny_x, tiny_y) == pytest.approx(1, abs=0.003)
    assert tiny[20][20] * 1e-30 == pytest.approx(grid[20][20], rel=1e-10)
    with pytest.raises(ValueError, match="variation"):
        density_grid([(1, 2), (1, 3)])
    with pytest.raises(ValueError, match="finite"):
        density_grid([(1, 2), (3, math.inf)])
    with pytest.raises(ValueError, match="strictly increasing"):
        density_grid([(1, 2), (3, 4)], x_coords=[1, 1, 2])
    assert _interp_edge(1e-20, 5e-20, 0, 1, 2e-20) == pytest.approx(0.25)
    original = _contour_segments([[0, 1], [1, 0]], 0.25, [0, 1], [0, 1])
    scaled = _contour_segments([[0, 1e-20], [1e-20, 0]], 0.25e-20, [0, 1], [0, 1])
    assert original == scaled
    points = [{"x": i / 4, "y": math.sin(i) + i / 8, "label": "Sentinel" if i == 4 else None} for i in range(20)]
    svg = make_contour(points=points, title="Density from observations")
    assert "Sentinel" in svg
    assert ET.fromstring(svg).tag.endswith("svg")


def test_grid_validation_and_constant_surface_are_truthful():
    with pytest.raises(ValueError, match="rectangular"):
        make_contour([[1, 2], [3]])
    with pytest.raises(ValueError, match="strictly positive"):
        make_contour([[0, 2], [3, 4]], log_z=True)
    svg = make_contour([[1.23, 1.23], [1.23, 1.23]], show_stats=True)
    text = " ".join(ET.fromstring(svg).itertext())
    assert "z min 1.23" in text and "z max 1.23" in text
    default_text = " ".join(ET.fromstring(make_contour([[1.23, 1.23], [1.23, 1.23]])).itertext())
    assert "z min" not in default_text and "grid" not in default_text


# ====================================================================================================
# Independent strips never obscure source samples, curves or confidence bands.
# ====================================================================================================


def layout(svg):
    return json.loads(nodes(svg, "heterogeneous-panels-layout")[0].get("data-layout"))


def path_points(node):
    return [tuple(map(float, pair)) for pair in re.findall(r"(-?[\d.]+),(-?[\d.]+)", node.get("d", ""))]


def assert_visible(main, plot, summary, expected):
    """Check actual rendered glyph extents, not just container separation."""
    assert plot[3] + 20 < summary[1]
    observed = nodes(main, "observation")
    assert len(observed) == expected
    for mark in observed:
        x, y, r = (float(mark.get(key)) for key in ("cx", "cy", "r"))
        assert plot[0] - 0.01 <= x <= plot[2] + 0.01
        assert plot[1] - 0.01 <= y <= plot[3] + 0.01
        assert y + r < summary[1]
    curves = nodes(main, "curve")
    bands = nodes(main, "confidence-band")
    assert curves and bands
    for mark in curves + bands:
        points = path_points(mark)
        assert points
        assert all(plot[0] - 0.01 <= x <= plot[2] + 0.01 and plot[1] - 0.01 <= y <= plot[3] + 0.01 for x, y in points)
        assert max(y for _, y in points) + 1 < summary[1]


def incidence(direction, log=False):
    series = []
    for slope in [1, -1] if direction == "opposing" else [1 if direction == "increasing" else -1]:
        points = [
            {"x": i, "y": 15 + slope * (i - 6) + (0.8 if slope < 0 else 0), "id": f"{slope}/{i}"} for i in range(1, 12)
        ]
        curve = [{"x": p["x"], "y": p["y"], "lo": p["y"] - 0.5, "hi": p["y"] + 0.5} for p in points]
        series.append({"name": str(slope), "points": points, "curve": curve})
    return {
        "id": "main",
        "kind": "xy",
        "data": {
            "series": series,
            "x_transform": "log10" if log else "linear",
            "y_transform": "log10" if log else "linear",
            "inset": {"name": "Mortality", "series": [{"name": "Mortality", "curve": [(1, 2), (11, 4)]}]},
        },
    }


@pytest.mark.parametrize("direction", ["increasing", "decreasing", "opposing"])
@pytest.mark.parametrize("log", [False, True])
def test_xy_inset_reserves_space_for_every_source_mark(direction, log):
    source = incidence(direction, log)
    before = deepcopy(source)
    svg = make_composite([source], template="panels")
    assert source == before
    panel = nodes(svg, "heterogeneous-panel")[0]
    inset = nodes(panel, "xy-inset")[0]
    panel.remove(inset)
    geometry = layout(svg)["panels"][0]
    assert_visible(panel, geometry["plot_bbox"], geometry["inset"]["bbox"], 22 if direction == "opposing" else 11)
    assert nodes(inset, "curve")


def test_categorical_source_observations_are_separate_from_inset():
    source = {
        "id": "category",
        "kind": "xy",
        "data": {
            "series": [{"name": "Observed", "points": [("High", 10), ("Middle", 5), ("Low", 1)]}],
            "inset": {"name": "Independent detail", "series": [{"name": "Detail", "points": [(0, 1), (1, 2)]}]},
        },
    }
    svg = make_composite([source], template="panels")
    geometry = layout(svg)["panels"][0]
    panel = nodes(svg, "heterogeneous-panel")[0]
    panel.remove(nodes(panel, "xy-inset")[0])
    marks = nodes(panel, "observation")
    assert len(marks) == 3
    assert {m.get("data-x") for m in marks} == {"High", "Middle", "Low"}
    assert all(float(m.get("cy")) + float(m.get("r")) < geometry["inset"]["bbox"][1] for m in marks)


def test_inset_preserves_shared_x_pixel_gutters():
    source = incidence("decreasing", True)
    source["x_group"] = "exposure"
    other = deepcopy(source)
    other["id"] = "other"
    other["data"].pop("inset")
    svg = make_composite([source, other], template="panels", cols=1)
    a, b = layout(svg)["panels"]
    assert a["axes"]["x"]["domain"] == b["axes"]["x"]["domain"]
    assert a["plot_bbox"][::2] == b["plot_bbox"][::2]


def test_inset_and_inherited_zoom_prepare_each_independent_data_record_once(monkeypatch):
    calls = []
    original = _composition_panels.fit_series

    def capture(series, **kwargs):
        calls.append([item["name"] for item in series])
        return original(series, **kwargs)

    monkeypatch.setattr(_composition_panels, "fit_series", capture)
    source = incidence("decreasing")
    make_composite([source, {"id": "zoom", "detail_of": "main", "x_range": [2, 8]}], template="panels")
    assert calls == [["-1"], ["Mortality"]]
