"""Observed professional-chart failures: layouts, scale and inference boundaries."""

import copy
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import gen_svg_charts as charts
from svg_lib.chart_examples import EXAMPLES
from embed_svg_validator import detect_embedded_svg_overlaps, validate_embedded_svgs
import re
from svg_lib.charts._xy import linreg
from svg_lib.charts.dose_response import _sigmoid4pl


def checked(svg):
    root = ET.fromstring(f"<slide><data><embed>{svg}</embed></data></slide>")
    assert not validate_embedded_svgs(root)
    assert not detect_embedded_svg_overlaps(root)
    return root


@pytest.mark.parametrize("slug", ["bar_academic", "contour", "depth_profile", "dose_response", "histogram", "spectrum"])
def test_registered_composition_examples_keep_clear_labels(slug):
    kwargs = copy.deepcopy(EXAMPLES[slug])
    checked(getattr(charts, "make_" + slug)(**kwargs))
    assert kwargs == EXAMPLES[slug]


@pytest.mark.parametrize("function", [charts.make_boxplot, charts.make_violin])
@pytest.mark.parametrize("academic", [False, True])
@pytest.mark.parametrize("paired", [False, True])
def test_layout_and_academic_style_do_not_request_inference(function, academic, paired):
    groups = [("Before", [1, 2, 4, 6, 8]), ("After", [2, 4, 5, 7, 10])]
    if paired:
        groups = [
            (name, [{"value": value, "subject_id": str(i)} for i, value in enumerate(values)])
            for name, values in groups
        ]
    root = checked(function(groups, academic=academic, paired=paired))
    assert not any(node.get("data-role") in ("effect-estimate", "significance") for node in root.iter())
    explicit = checked(function(groups, academic=academic, paired=paired, multi_mode="with_effect_size"))
    assert any(node.get("data-role") == "effect-estimate" for node in explicit.iter())


@pytest.mark.parametrize("method", ["welch", "student", "mann_whitney"])
def test_independent_auto_tests_cannot_be_applied_to_declared_paired_samples(method):
    groups = [
        ("A", [{"value": 1, "subject_id": "x"}, {"value": 2, "subject_id": "y"}]),
        ("B", [{"value": 2, "subject_id": "x"}, {"value": 4, "subject_id": "y"}]),
    ]
    with pytest.raises(ValueError, match="paired observations.*independent") as exc:
        charts.make_boxplot(groups, paired=True, academic=True, auto_test=method, pairs=[(0, 1)])
    assert str(exc.value)


@pytest.mark.parametrize("values", [(330, 165, 174, 669), (-100, 20, 0, -80)])
def test_waterfall_absolute_totals_encode_length_from_zero(values):
    first, increment, second_increment, last = values
    steps = [
        ("Start", first, "total"),
        ("First addition", increment, "pos"),
        ("Second addition", second_increment, "pos"),
        ("End", last, "total"),
    ]
    root = checked(charts.make_waterfall(steps, multi_mode="single"))
    totals = [n for n in root.iter() if n.get("data-role") == "waterfall-total"]
    assert len(totals) == 2
    assert float(totals[1].get("height")) / float(totals[0].get("height")) == pytest.approx(
        abs(last / first), abs=0.002
    )
    for node in totals:
        y, height, zero = (float(node.get(name)) for name in ("y", "height", "data-zero-y"))
        assert (y + height if float(node.get("data-value")) >= 0 else y) == pytest.approx(zero, abs=0.11)
    assert "0" in list(root.itertext())


def test_large_bubble_labels_avoid_the_full_circle_extent():
    points = [
        {"x": 3.0, "y": 1.6, "size": 320, "label": "搜索广告"},
        {"x": 5.0, "y": 1.3, "size": 234, "label": "行业活动"},
        {"x": 2.5, "y": 2.7, "size": 288, "label": "合作伙伴"},
        {"x": 2.0, "y": 3.6, "size": 180, "label": "老客推荐"},
    ]
    root = checked(charts.make_bubble(points, width=1000, height=760))
    assert all(point["label"] in list(root.itertext()) for point in points)
    assert len([n for n in root.iter() if n.get("data-role") == "observation"]) == 4


def test_automatic_gantt_secondary_type_is_readable_at_600px():
    kwargs = copy.deepcopy(EXAMPLES["gantt"])
    root = checked(charts.make_gantt(**kwargs))
    svg = next(n for n in root.iter() if n.tag.endswith("svg"))
    width = float(svg.get("viewBox").split()[2])
    labels = {"1", "Critical path", "Non-critical", "原型完成", "正式发布", "CP"}
    for node in root.iter():
        if node.text in labels:
            assert float(node.get("font-size")) * 600 / width >= 11.95


def test_contour_interpolates_the_requested_between_row_slice():
    grid = [[float(x + y) for x in range(20)] for y in range(20)]
    root = checked(
        charts.make_contour(grid, slice_y=0.5, multi_mode="with_orthogonal_slices", show_filled=False, show_lines=False)
    )
    curves = [node for node in root.iter() if node.tag.endswith("path") and node.get("stroke-width") == "1.6"]
    assert len(curves) == 1
    first_y = float(re.match(r"M [\d.]+ ([\d.]+)", curves[0].get("d")).group(1))
    baselines = [
        float(node.get("y1")) for node in root.iter() if node.tag.endswith("line") and node.get("y1") == node.get("y2")
    ]
    # z=.5 at x=0 lies above the z=0 slice baseline; nearest-row sampling put it on that baseline.
    assert max(baselines) - first_y > 0.5


def test_fractional_amounts_and_residual_error_are_reported_exactly():
    root = checked(
        charts.make_waterfall(
            [("Start", 330.125, "total"), ("Addition", 165.375, "pos"), ("End", 495.5, "total")], multi_mode="single"
        )
    )
    labels = list(root.itertext())
    assert "330.125" in labels and "+165.375" in labels and "495.5" in labels
    xs, ys = [1, 2, 3, 4], [1, 3, 2, 5]
    slope, intercept, r2, p, se, residual_se = linreg(xs, ys)
    expected = (sum((y - (slope * x + intercept)) ** 2 for x, y in zip(xs, ys)) / 2) ** 0.5
    assert residual_se == pytest.approx(expected)
    root = checked(charts.make_scatter_fit(list(zip(xs, ys)), fit="linear"))
    assert "Residual SE" in " ".join(root.itertext()) and "RMSE" not in " ".join(root.itertext())
    root = checked(charts.make_sankey(["甲", "乙"], ["丙"], [("甲", "丙", 0.1), ("乙", "丙", 0.2)]))
    text = " ".join(root.itertext())
    assert "0.1" in text and "0.2" in text and "0.3" in text
    assert "0.300000" not in text


def _dose_points():
    doses = [0.1, 0.2, 0.5, 1, 2, 5, 10, 20]
    return [
        {"dose": x, "response": _sigmoid4pl(x, 10, 100, ec50, 1.3) + (i % 2) * 0.1, "group": group}
        for group, ec50 in (("A", 1.5), ("B", 3))
        for i, x in enumerate(doses)
    ]


def test_dose_response_residuals_explicit_fits_and_interval_checks():
    root = checked(charts.make_dose_response(_dose_points()))
    assert not any(node.get("data-role") in ("confidence-band", "ec50-confidence-interval") for node in root.iter())
    assert "confidence intervals not supplied" in " ".join(root.itertext())
    assert "95%" not in " ".join(root.itertext())
    fit_ci = {g: [(0.1, 0, 120), (20, 0, 120)] for g in ("A", "B")}
    ec50_ci = {"A": (0.5, 5), "B": (1, 10)}
    root = checked(charts.make_dose_response(_dose_points(), fit_ci=fit_ci, ec50_ci=ec50_ci))
    assert len([n for n in root.iter() if n.get("data-role") == "confidence-band"]) == 2
    intervals = [n for n in root.iter() if n.get("data-role") == "ec50-confidence-interval"]
    assert len(intervals) == 2
    actual = [(10 ** float(n.get("data-log-low")), 10 ** float(n.get("data-log-high"))) for n in intervals]
    assert actual[0] == pytest.approx((0.5, 5)) and actual[1] == pytest.approx((1, 10))
    hidden = checked(charts.make_dose_response(_dose_points(), fit_ci=fit_ci, ec50_ci=ec50_ci, show_ci=False))
    assert not any(n.get("data-role") in ("confidence-band", "ec50-confidence-interval") for n in hidden.iter())
    assert "interval display disabled" in " ".join(hidden.itertext())
    with pytest.raises(ValueError, match="contain the fitted"):
        charts.make_dose_response(_dose_points(), fit_ci={"A": [(0.1, 200, 300), (20, 200, 300)]})
    with pytest.raises(ValueError, match="contain the fitted EC50"):
        charts.make_dose_response(_dose_points(), ec50_ci={"A": (100, 200)})
    points = [{"dose": x, "response": 10} for x in (0, 1, 2, 3, 4)]
    root = checked(charts.make_dose_response(points, log_dose=False))
    observations = [n for n in root.iter() if n.get("data-role") == "observation"]
    assert len(observations) == 5 and any(float(n.get("data-x")) == 0 for n in observations)
    assert "EC50 =" not in " ".join(root.itertext())
    assert "fit unavailable" in " ".join(root.itertext())


def test_quadrant_reference_splits_are_not_claimed_as_sample_medians():
    items = [
        {"name": "A", "x": 7.8, "y": 8.5},
        {"name": "B", "x": 3.2, "y": 7.2},
        {"name": "C", "x": 6.2, "y": 3.2},
        {"name": "D", "x": 8.6, "y": 5.6},
        {"name": "E", "x": 8.4, "y": 3.4},
    ]
    root = checked(charts.make_quadrant_2x2(items, x_range=[0, 10], y_range=[0, 10], x_median=5, y_median=5))
    assert "MEDIAN" not in " ".join(root.itertext())
    assert [n.get("data-value") for n in root.iter() if n.get("data-role") == "reference-split"] == ["5", "5"]


def test_explicit_regional_gantt_keeps_all_labels_in_a_490px_column():
    tasks = [("整理台账与排班", 0, 2, 0), ("试点执行（共享值班诊断席）", 2, 6, 1), ("对照复盘与经营会复议", 6, 8, 0)]
    root = checked(
        charts.make_gantt(
            tasks,
            weeks=8,
            critical_index=1,
            milestones=[(2, "启动就绪"), (8, "复盘决策点")],
            width=1000,
            height=500,
            show_legend=False,
        )
    )
    text = " ".join(root.itertext())
    assert all(name in text for name, *_ in tasks)
    assert "启动就绪" in text and "复盘决策点" in text and "1" in list(root.itertext())
    # Zero is a real supplied stream ID, not a missing optional value.
    stream_zero = [n for n in root.iter() if n.text == "0" and n.get("font-weight") is None]
    assert len(stream_zero) >= 2
    for n in root.iter():
        if n.text in ("启动就绪", "复盘决策点", "CP"):
            assert float(n.get("font-size")) * 490 / 1000 >= 10.5
