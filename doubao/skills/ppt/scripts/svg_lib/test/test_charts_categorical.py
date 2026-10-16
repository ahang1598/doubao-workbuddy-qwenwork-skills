"""Categorical / bar charts: grouped adaptive dispatch, grouped bar regressions, swimmer, category rows."""

import json
import math
import subprocess
import sys
import xml.etree.ElementTree as ET
import re
import warnings
import unittest
from copy import deepcopy
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from embed_svg_validator import validate_embedded_svgs, detect_embedded_svg_overlaps

from ._helpers import nodes, nodes as role
from .._common import _estimate_label_width_px
from ..charts.grouped_bar import make_grouped_bar
from ..charts._categorical import (
    normalize_cell,
    BrokenScale,
    _stack_records,
    normalize_records,
    render_categorical_plot,
)
from ..charts.forest import make_forest
from ..charts._academic_rigor import BBox, SeriesContext
from ..charts._composition import scale_from
from ..charts._xy import CategoryScale
from ..charts.bar_academic import make_bar_academic
from ..charts.swimmer import make_swimmer
from ..charts._chart_layout import ChartLayout
from ..charts._composition_panels import _prepare, _render
from ..charts._composition_rows import RowScale
from ..charts.composite import make_composite
import copy
from ..charts import matrix_heat


# ====================================================================================================
# Adaptive dispatch must preserve evidence, identity, geometry and explicit intent.
# ====================================================================================================


def draw(categories, series, **kwargs):
    original = deepcopy((categories, series, kwargs))
    svg = make_grouped_bar(categories, series, **kwargs)
    root = ET.fromstring(svg)
    slide = ET.Element("slide")
    ET.SubElement(slide, "embed").append(root)
    assert not validate_embedded_svgs(slide)
    assert not detect_embedded_svg_overlaps(slide)
    assert (categories, series, kwargs) == original
    return root


def mode(root):
    return role(root, "grouped-view")[0].get("data-mode")


def test_summaries_cartesian_and_matrix_routes():
    root = draw(
        ["A", "B", "C"],
        [("Before", [{"value": 12}, None, {"value": 0}]), ("After", [{"value": 19}, {"value": 23}, {"value": 4}])],
    )
    assert mode(root) == "bars"
    assert len(role(root, "missing")) == 1
    values = {(n.get("data-series"), n.get("data-category")): n.text for n in role(root, "bar-value-label")}
    assert values == {
        ("Before", "A"): "12",
        ("Before", "C"): "0",
        ("After", "A"): "19",
        ("After", "B"): "23",
        ("After", "C"): "4",
    }
    with pytest.raises(ValueError, match="radial ring was removed.*'bars'.*'heatmap'"):
        make_grouped_bar(["A", "B"], [("S", [{"value": 1}, {"value": 2}])], multi_mode="radial")
    cats = [f"C{i}" for i in range(8)]
    series = [(f"S{s}", [{"value": 10 + s + i} for i in range(8)]) for s in range(4)]
    root = draw(cats, series, multi_mode="auto")
    assert mode(root) == "heatmap"
    assert len(role(root, "grouped-cell")) == 32
    content = " ".join(root.itertext())
    assert all(name in content for name in cats + [name for name, _ in series])


@pytest.mark.parametrize(
    "labels,expected",
    [
        (["城市成年人", "农村成年人", "老年人群(≥65岁)", "青少年"], "horizontal"),
        (["低剂量", "中剂量", "高剂量"], "horizontal"),
        ([f"C{i}" for i in range(10)], "vertical"),
        ([f"非常长的类别名称第{i}组" for i in range(10)], "horizontal"),
    ],
)
def test_single_series_summary_picks_cartesian_orientation(labels, expected):
    series = [("患病率", [{"value": 5.0 + i} for i in range(len(labels))])]
    root = draw(labels, series, y_unit="%", width=1300, height=900)
    assert mode(root) == "bars"
    chart = role(root, "categorical-chart")[0]
    assert chart.get("data-orientation") == expected
    shown = {n.get("data-category"): float(n.text) for n in role(root, "bar-value-label")}
    assert shown == {label: 5.0 + i for i, label in enumerate(labels)}


def test_heatmap_values_and_ties():
    categories = [f"Condition {i}" for i in range(8)]
    series = [(f"Method {j}", [{"value": 10 + i + j} for i in range(8)]) for j in range(4)]
    root = draw(categories, series, multi_mode="heatmap", show_values=True, value_domain=(0, 100))
    info = json.loads(root.get("data-matrix-layout"))
    assert info["variant"] == "circle_full" and info["cell_label_position"] == "below"
    assert info["row_labels"] == [name for name, _ in series]
    assert info["col_labels"] == categories
    cells = [node for node in root.iter() if node.get("data-row") is not None and node.get("data-col") is not None]
    assert len(cells) == 32
    for cell in cells:
        ri, ci = int(cell.get("data-row")), int(cell.get("data-col"))
        value = series[ri][1][ci]["value"]
        assert float(cell.get("data-value")) == value
        assert str(value) in list(cell.itertext())
    # Independent area encoding stays linear in the original value.
    areas = [float(cell.find("{*}circle").get("r")) ** 2 / float(cell.get("data-value")) for cell in cells]
    assert max(areas) == pytest.approx(min(areas), rel=1e-4)
    root = draw(
        ["A", "B", "C"],
        [("X", [{"value": 3}, {"value": 0}, None]), ("Y", [{"value": 3}, {"value": 4}, {"value": 7}])],
        multi_mode="heatmap",
    )
    cells = [node for node in root.iter() if node.get("data-row") is not None and node.get("data-col") is not None]
    shown = [label for cell in cells for label in cell.itertext()]
    assert shown.count("3") == 2
    assert "0" in shown and "—" in shown
    assert "4" in shown and "7" in shown
    hidden = draw(
        ["A", "B"],
        [("X", [{"value": 0}, None]), ("Y", [{"value": 3}, {"value": 7}])],
        multi_mode="heatmap",
        show_values=False,
    )
    cells = [node for node in hidden.iter() if node.get("data-row") is not None and node.get("data-col") is not None]
    assert [text for cell in cells for text in cell.itertext()] == ["—"]


def test_heatmap_auto_range_is_not_forced_to_zero_and_explicit_range_is_honored(monkeypatch):
    original = matrix_heat.make_matrix_heat
    calls = []

    def capture(*args, **kwargs):
        calls.append(kwargs)
        return original(*args, **kwargs)

    monkeypatch.setattr(matrix_heat, "make_matrix_heat", capture)
    args = (["A", "B"], [("X", [{"value": 70}, {"value": 85}]), ("Y", [{"value": 75}, {"value": 90}])])
    draw(*args, multi_mode="heatmap")
    assert 0 < calls[-1]["vmin"] <= 70 and calls[-1]["vmax"] >= 90
    draw(*args, multi_mode="heatmap", value_domain=(0, 100))
    assert calls[-1]["vmin"] == 0 and calls[-1]["vmax"] == 100
    assert calls[-1]["size_max"] == 100


@pytest.mark.parametrize("value", [0, 5])
def test_constant_heatmap_keeps_observed_values_without_artificial_variation(value):
    root = draw(["A", "B"], [("S", [{"value": value}, {"value": value}])], multi_mode="heatmap")
    cells = [node for node in root.iter() if node.get("data-row") is not None and node.get("data-col") is not None]
    assert [float(n.get("data-value")) for n in cells] == [value, value]


def test_supplied_sd_and_sample_sem_remain_distinct_and_visible():
    root = draw(
        ["Condition"], [("Given", [{"mean": 10, "sd": 2, "n": 4}]), ("Observed", [[10, 12, 14, 16]])], error_kind="SEM"
    )
    assert mode(root) == "intervals"
    intervals = role(root, "grouped-interval")
    assert [(float(e.get("data-low")), float(e.get("data-high"))) for e in intervals][0] == (9, 11)
    calculated = normalize_cell([10, 12, 14, 16], "SEM")
    assert float(intervals[1].get("data-low")) == pytest.approx(calculated["lo"])
    assert [float(n.get("data-value")) for n in role(root, "replicate")] == [10, 12, 14, 16]
    assert "Intervals: SEM" in " ".join(root.itertext())
    assert "CI" not in " ".join(root.itertext())


@pytest.mark.parametrize("count,expected", [(2, "intervals"), (5, "boxplot"), (19, "boxplot"), (20, "raincloud")])
def test_sample_modes_require_actual_observations(count, expected):
    root = draw(["C"], [("A", [[20 + i for i in range(count)]]), ("B", [[25 + i for i in range(count)]])])
    assert mode(root) == expected
    assert [int(e.get("data-n")) for e in role(root, "grouped-cell")] == [count, count]


def test_missing_sample_cell_uses_intervals_without_discarding_other_samples():
    root = draw(["A", "B"], [("X", [[20, 21, 22, 23, 24], None]), ("Y", [[22, 23, 24, 25, 26], [30, 31, 32, 33, 34]])])
    assert mode(root) == "intervals"
    assert len(role(root, "replicate")) == 15
    assert "—" in list(root.itertext())


@pytest.mark.parametrize("requested", ["boxplot", "raincloud"])
def test_summary_values_cannot_become_synthetic_distributions(requested):
    with pytest.raises(ValueError, match="actual observations") as exc:
        make_grouped_bar(["C"], [("A", [{"mean": 20, "sd": 2, "n": 30}])], error_kind="SD", multi_mode=requested)
    assert str(exc.value)


@pytest.mark.parametrize("requested", ["heatmap", "marimekko"])
def test_view_override_cannot_drop_intervals_or_samples(requested):
    with pytest.raises(ValueError, match="omit") as exc:
        make_grouped_bar(["C"], [("A", [[10, 12, 14]])], multi_mode=requested)
    assert str(exc.value)


@pytest.mark.parametrize("requested", ["auto", "single", "heatmap", "intervals", "with_facet_by_series"])
def test_every_route_rejects_negative_data_with_native_chart_guidance(requested):
    for cell in ({"value": -1}, [-1, 10, 20], {"mean": 4, "lo": -1, "hi": 6}):
        with pytest.raises(ValueError, match="negative value.*原生柱状图") as exc:
            make_grouped_bar(["C"], [("S", [cell])], multi_mode=requested)
        assert str(exc.value)


def test_negative_line_and_axis_and_computed_interval_are_not_hidden():
    kwargs = dict(categories=["C"], series=[("S", [{"value": 10}])])
    for extra in [
        dict(value_domain=(-1, 20)),
        dict(line_series=[{"name": "L", "values": [-1]}], y_unit="%", right_y_unit="s"),
    ]:
        with pytest.raises(ValueError, match="negative value.*原生") as exc:
            make_grouped_bar(**kwargs, **extra)
        assert str(exc.value)
    with pytest.raises(ValueError, match="negative value.*原生") as exc:
        make_grouped_bar(["C"], [("S", [[0, 0, 1]])], error_kind="SD")
    assert str(exc.value)


def test_zero_intervals_marimekko_and_declared_additivity():
    root = draw(["C"], [("S", [[0, 0]])])
    interval = role(root, "grouped-interval")[0]
    assert interval.get("data-low") == interval.get("data-high") == "0.0"
    assert len(role(root, "replicate")) == 2
    root = draw(
        ["A", "B"], [("X", [{"value": 20}, {"value": 40}]), ("Y", [{"value": 30}, {"value": 60}])], stack="percent"
    )
    assert mode(root) == "marimekko"
    tiles = role(root, "marimekko-cell")
    by_key = {(n.get("data-category"), n.get("data-series")): n for n in tiles}
    assert float(by_key["B", "X"].get("width")) / float(by_key["A", "X"].get("width")) == pytest.approx(2)
    areas = [float(n.get("width")) * float(n.get("height")) / float(n.get("data-value")) for n in tiles]
    assert max(areas) == pytest.approx(min(areas))
    assert [n.get("data-total") for n in tiles] == ["50.0", "50.0", "100.0", "100.0"]
    with pytest.raises(ValueError, match="explicitly additive"):
        make_grouped_bar(["C"], [("A", [{"value": 20}]), ("B", [{"value": 80}])], multi_mode="marimekko")
    root = draw(["C"], [("A", [{"mean": 20, "lo": 18, "hi": 22}]), ("B", [{"value": 80}])], stack="percent")
    assert len(role(root, "bar-interval")) == 1
    assert not role(root, "marimekko-cell")


def test_explicit_comparisons_survive_distribution_and_cross_category_routes():
    series = [("A", [[10, 11, 12, 13, 14], [20, 21, 22, 23, 24]]), ("B", [[15, 16, 17, 18, 19], [25, 26, 27, 28, 29]])]
    root = draw(["C1", "C2"], series, pairwise_p=[(0, 0, 1, 0.012)])
    assert mode(root) == "boxplot"
    assert "0.012" in " ".join(root.itertext())
    root = draw(["C1", "C2"], series, pairwise_p=[{"a": ["C1", "A"], "b": ["C2", "A"], "p": 0.03}])
    assert mode(root) == "intervals"
    assert len(role(root, "significance")) == 1
    assert len(role(root, "replicate")) == 20


def test_explicit_labels_points_and_units_are_preserved():
    root = draw(
        ["C"],
        [("A", [[20 + i for i in range(20)]])],
        show_values=True,
        show_points=False,
        title="Title",
        subtitle="Subtitle",
        figure_label="FIG A",
        y_title="Response",
        y_unit="mg",
        x_title="Conditions",
        note="Study notes",
        source="Source",
        palette={"series": ["#A03456"], "bg": "#ffffff"},
    )
    assert mode(root) == "intervals"
    assert not role(root, "replicate")
    assert role(root, "grouped-estimate")[0].get("fill") == "#A03456"
    text = " ".join(root.itertext())
    for label in ["Title", "Subtitle", "FIG A", "Response (mg)", "Conditions", "Study notes", "Source"]:
        assert label in text


def test_cli_stays_stdlib_only_and_returns_actionable_negative_error(tmp_path):
    payload = tmp_path / "data.json"
    args = dict(categories=["A", "B"], series=[("S", [{"value": 12}, {"value": 23}])])
    payload.write_text(json.dumps(args))
    command = [
        sys.executable,
        "-I",
        "-S",
        str(SCRIPTS / "gen_svg_charts.py"),
        "--type",
        "grouped_bar",
        "--data-file",
        str(payload),
    ]
    result = subprocess.run(command, cwd=tmp_path, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert mode(ET.fromstring(result.stdout)) == "bars"
    args["series"][0][1][0]["value"] = -2
    payload.write_text(json.dumps(args))
    result = subprocess.run(command, cwd=tmp_path, capture_output=True, text=True, timeout=30)
    assert result.returncode != 0 and "原生柱状图" in result.stderr
    assert "<svg" not in result.stdout


# ====================================================================================================
# Regressions from real Chinese academic slides: broken axes, interval chrome, log bars, forest headers.
# ====================================================================================================


def text(root):
    return " ".join(root.itertext())


def _ticks(root, name):
    out = []
    for node in role(root, name):
        fs = float(node.get("font-size"))
        out.append((float(node.get("x")), float(node.get("y")), "".join(node.itertext()), fs))
    return out


RUBISCO = (
    [
        "红藻（典型值）",
        "C3 植物（典型值）",
        "C4 植物（典型值）",
        "蓝细菌 Te BP1",
        "蓝细菌 Se PCC6301",
        "典型中心代谢酶",
    ],
    [["羧化周转速率 kcat,C", [[2.0], [3.0], [5.0], [7.4], [12.6], [80.0]]]],
)


def test_axis_breaks_keep_label_gaps_and_real_samples():
    cats, series = RUBISCO
    root = ET.fromstring(
        make_grouped_bar(
            cats,
            series,
            orientation="horizontal",
            axis_break=(15, 62),
            x_title="羧化周转速率 kcat,C（s⁻¹）",
            width=735,
            height=430,
        )
    )
    ticks = sorted(_ticks(root, "x-tick"))
    labels = [t[2] for t in ticks]
    assert "15" in labels or "62" in labels
    assert any(float(v) <= 15 and float(v) > 0 for v in labels) and any(float(v) >= 62 for v in labels)
    for (x0, _, a, fs), (x1, _, b, _) in zip(ticks, ticks[1:]):
        wa = _estimate_label_width_px(a, fs)
        wb = _estimate_label_width_px(b, fs)
        gap = (x1 - wb / 2) - (x0 + wa / 2)
        assert gap >= max(wa, wb) - 1, (a, b, gap)
    # A single observation is the bar end: no replicate dot is drawn on top of it.
    assert not role(root, "replicate")
    # Two clear slash marks plus a gap band through the grid.
    assert len(re.findall(r"M", role(root, "axis-break")[0].get("d"))) == 2
    assert role(root, "axis-break-gap")
    root = ET.fromstring(
        make_grouped_bar(
            ["Parikh 2006", "Durão 2015", "Cai 2014", "Wilson 2018", "Zhou 2019"],
            [["报告的羧化性能增益", [[400], [200], [85], [43], [27]]]],
            orientation="vertical",
            axis_break=(120, 300),
            y_title="增益（%）",
            width=765,
            height=340,
        )
    )
    ticks = sorted(_ticks(root, "y-tick"), key=lambda t: t[1])
    values = [float(t[2]) for t in ticks]
    assert any(v >= 300 for v in values) and any(0 < v <= 120 for v in values)
    for (_, y0, _, fs), (_, y1, _, _) in zip(ticks, ticks[1:]):
        assert y1 - y0 >= fs * 2.2
    assert not role(root, "replicate")
    root = ET.fromstring(
        make_grouped_bar(
            ["A", "B"],
            [("S", [[1, 2, 3], [70, 80, 90]])],
            orientation="horizontal",
            axis_break=(10, 60),
            width=900,
            height=500,
        )
    )
    assert len(role(root, "replicate")) == 6


RRR = (
    ["<30 分钟", "0.5–3 小时", "3–6 小时", ">6 小时"],
    [
        [
            "内化问题 RRR（未调整）",
            [
                {"value": 1.30, "lo": 0.94, "hi": 1.78},
                {"value": 1.89, "lo": 1.36, "hi": 2.54},
                {"value": 2.47, "lo": 1.74, "hi": 3.49},
                {"value": 2.83, "lo": 1.88, "hi": 4.26},
            ],
        ]
    ],
)


@pytest.mark.parametrize("width,height", [(370, 354), (1200, 760)])
def test_single_series_intervals_hide_internal_words_and_do_not_repeat_series(width, height):
    cats, series = RRR
    root = ET.fromstring(
        make_grouped_bar(cats, series, x_title="每日使用时间", y_title="RRR（参照：不用）", width=width, height=height)
    )
    body = text(root)
    for leaked in ("supplied", "lo/hi", "Interval", "Series", "系列"):
        assert leaked not in body
    assert body.count("内化问题 RRR") == 1  # legend only, never once per row
    assert "区间" in body
    for category in cats:
        assert category in body


def test_interval_legend_names_a_stated_ci_level():
    cats, series = RRR
    body = text(ET.fromstring(make_grouped_bar(cats, series, ci_level=95, y_title="RRR", width=370, height=354)))
    assert "95% 置信区间" in body or "95% CI" in body
    assert "supplied" not in body


def test_multi_series_intervals_keep_series_rows():
    cats, (name, cells) = RRR[0], RRR[1][0]
    series = [[name, cells], ["调整后", cells]]
    body = text(ET.fromstring(make_grouped_bar(cats, series, y_title="RRR", width=900, height=900)))
    assert body.count("调整后") >= len(cats)
    assert "supplied" not in body


RC = (
    ["量子极限", "Sb（01-12）", "Bi（0001）", "1T-MoS2", "UHV Ni", "In/Au 少层", "常规金属"],
    [("Rc", [{"value": v} for v in [36, 42, 123, 250, 500, 800, 3000]])],
)


def test_wide_ranges_switch_to_log_axis_and_warn():
    import gen_svg_charts as g

    cats, series = RC
    root = ET.fromstring(
        make_grouped_bar(cats, series, orientation="horizontal", x_title="接触电阻 Rc（Ω·μm）", width=650, height=440)
    )
    assert "对数轴" in text(root)
    bars = {float(b.get("data-value")): float(b.get("width")) for b in role(root, "bar")}
    # On a log axis the 36 vs 3000 bars differ by far less than 83x and the smallest is clearly visible.
    assert bars[36] > 20 and bars[3000] / bars[36] < 30
    labels = [t[2] for t in _ticks(root, "x-tick")]
    assert "100" in labels and "1000" in labels
    cats, series = RC
    root = ET.fromstring(
        make_grouped_bar(
            cats, series, orientation="horizontal", value_scale="linear", x_title="接触电阻", width=650, height=440
        )
    )
    assert "对数轴" not in text(root)
    narrow = ET.fromstring(
        make_grouped_bar(
            ["A", "B", "C"],
            [("钉扎因子", [{"value": v} for v in (0.07, 0.27, 1.0)])],
            orientation="horizontal",
            x_title="钉扎因子 S",
            width=650,
            height=440,
        )
    )
    assert "对数轴" not in text(narrow)
    with pytest.raises(ValueError):
        make_grouped_bar(["A", "B"], [("S", [{"value": 0}, {"value": 5}])], orientation="horizontal", value_scale="log")
    cats, series = RC
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        g.chart_slide(
            "grouped_bar",
            0,
            0,
            520,
            352,
            categories=cats,
            series=series,
            orientation="horizontal",
            value_scale="linear",
            x_title="接触电阻",
        )
    assert any("value_scale='log'" in str(w.message) for w in caught)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        g.chart_slide(
            "grouped_bar", 0, 0, 520, 352, categories=cats, series=series, orientation="horizontal", x_title="接触电阻"
        )
    assert not any("value_scale='log'" in str(w.message) for w in caught)


def test_chinese_forest_without_subgroups_does_not_say_subgroup_and_separates_negative_bounds():
    rows = [
        {"label": "使用时间", "estimate": 0.08, "ci_lo": 0.01, "ci_hi": 0.15},
        {"label": "参与度", "estimate": 0.12, "ci_lo": 0.09, "ci_hi": 0.15},
        {"label": "问题性使用—幸福感", "estimate": -0.22, "ci_lo": -0.28, "ci_hi": -0.15},
    ]
    body = text(
        ET.fromstring(make_forest(rows, x_title="相关系数 r", midline_value=0, ci_level=95, width=840, height=292))
    )
    for leaked in ("Subgroup", "亚组", "Estimate", "Hazard"):
        assert leaked not in body
    assert "95% CI" in body
    assert "-0.28, -0.15" in body and "–-" not in body
    headed = text(
        ET.fromstring(
            make_forest(
                [{"label": "男性", "is_subgroup_header": True}] + rows,
                x_title="r",
                midline_value=0,
                width=840,
                height=360,
            )
        )
    )
    assert "亚组" in headed


# ====================================================================================================
# Statistical and geometric contracts of categorical and clinical charts.
# ====================================================================================================


def issues(svg):
    root = ET.fromstring(f'<slide><data><embed id="chart">{svg}</embed></data></slide>')
    return validate_embedded_svgs(root) + detect_embedded_svg_overlaps(root)


class CategoricalTests(unittest.TestCase):
    def test_categorical_statistics_stacks_and_validation(self):
        categories = ["Low / WT", "Low / Variant", "High / WT", "High / Variant"]
        series = [
            ("M0", [{"mean": v, "lo": v - 2, "hi": v + 2} for v in (20, 25, 24, 32)]),
            ("M1", [{"value": v} for v in (65, 35, 70, 50)]),
            ("M2", [{"value": v} for v in (15, 40, 6, 18)]),
        ]
        original = copy.deepcopy(series)
        comparisons = [
            {"a": [categories[0], "M0"], "b": [categories[1], "M0"], "p": 0.012},
            {"a": [categories[2], "M0"], "b": [categories[3], "M0"], "p": 0.0002},
        ]
        for orientation in ("vertical", "horizontal"):
            svg = make_grouped_bar(categories, series, stack="percent", pairwise_p=comparisons, orientation=orientation)
            self.assertEqual(len(role(svg, "bar")), 12)
            self.assertEqual(len(role(svg, "significance")), 2)
            elements = list(ET.fromstring(svg).iter())
            last_bar = max(i for i, node in enumerate(elements) if node.get("data-role") == "bar")
            first_interval = min(i for i, node in enumerate(elements) if node.get("data-role") == "bar-interval")
            self.assertGreater(first_interval, last_bar)
            self.assertEqual(
                [(float(e.get("data-lo")), float(e.get("data-hi"))) for e in role(svg, "bar-interval")],
                [(18, 22), (23, 27), (22, 26), (30, 34)],
            )
            self.assertIn("M0 · P = 0.012", svg)
            self.assertIn("M0 · P &lt; 0.001", svg)
            self.assertEqual(issues(svg), [])
        self.assertEqual(series, original)
        stat = normalize_cell([1, 2, 3], "CI95")
        self.assertAlmostEqual(stat["hi"] - 2, 4.3026527299 / math.sqrt(3), places=8)
        stat = normalize_cell({"mean": 3, "sd": 2, "n": 4}, "SEM")
        self.assertEqual((stat["lo"], stat["hi"], stat["replicates"]), (2, 4, []))
        with self.assertRaises(ValueError):
            normalize_cell({"mean": 3, "sd": 2}, "SEM")
        stat = normalize_cell([1e12 + 1, 1e12 + 2, 1e12 + 3], "SD")
        self.assertEqual(stat["hi"] - stat["value"], 1)
        self.assertNotIn("lo", normalize_cell([4], "SEM"))
        with self.assertRaises(ValueError):
            normalize_cell([4], "CI95")
        tiny = normalize_cell([1e-110, 2e-110, 3e-110], "SEM")
        self.assertAlmostEqual(tiny["value"] / 1e-110, 2)
        self.assertAlmostEqual((tiny["hi"] - tiny["value"]) / 1e-110, 1 / math.sqrt(3))
        huge = normalize_cell([1e110, 2e110, 3e110], "SEM")
        self.assertTrue(math.isfinite(huge["hi"]))
        cats, _, records = normalize_records(["A"], [("X", [{"mean": 20, "lo": 18, "hi": 22}]), ("Y", [{"value": 80}])])
        result = _stack_records(records, cats, "percent")
        self.assertEqual((result[0]["lo"], result[0]["hi"]), (18, 22))
        svg = make_grouped_bar(
            ["A"],
            [("X", [{"mean": 20, "lo": 18, "hi": 22}]), ("Y", [{"value": 80}])],
            orientation="horizontal",
            stack="percent",
        )
        self.assertIn("fixed observed total", svg)
        self.assertFalse(issues(svg))
        cats, _names, records = normalize_records(["A"], [("X", [{"value": 1}]), ("Y", [{"value": 3}])])
        records = _stack_records(records, cats, "percent")
        self.assertEqual([(r["start"], r["value"]) for r in records], [(0, 25), (25, 100)])
        svg = make_grouped_bar(cats, [("X", [{"value": 1}]), ("Y", [{"value": 3}])], stack="percent")
        self.assertFalse(issues(svg))
        with self.assertRaises(ValueError):
            make_grouped_bar(cats, [("X", [{"value": 0}])], stack="percent")
        cats, _, records = normalize_records(
            ["A"], [("X", [{"value": -3}]), ("Y", [{"value": 5}]), ("Z", [{"value": -2}])]
        )
        self.assertEqual(
            [(r["start"], r["value"]) for r in _stack_records(records, cats, "stacked")], [(0, -3), (0, 5), (-3, -5)]
        )
        for value in (math.inf, math.nan, True, "3"):
            with self.assertRaises((ValueError, TypeError)):
                make_bar_academic([("A", [value])], multi_mode="single")
        with self.assertRaises(ValueError):
            make_bar_academic([("A", [1, 2])], orientation="horizontal", variant="invented")
        with self.assertRaisesRegex(ValueError, "negative value.*原生"):
            make_grouped_bar(
                ["A", "B", "C"], [("Series", [{"value": -3}, None, {"value": 0}])], orientation="horizontal"
            )
        svg = make_grouped_bar(
            ["A", "B", "C"], [("Series", [{"value": 3}, None, {"value": 0}])], orientation="horizontal"
        )
        bars = role(svg, "bar")
        self.assertEqual(len(bars), 2)
        self.assertEqual(float(bars[1].get("width")), 0)
        self.assertFalse(issues(svg))

    def test_broken_and_dual_axes_and_significance_layout(self):
        scale = BrokenScale(scale_from([0, 100], domain=(0, 100)), (10, 90))
        self.assertAlmostEqual(scale.map(90, 0, 218) - scale.map(10, 0, 218), 18)
        records = [
            {
                "name": "A",
                "category": "one",
                "row_id": "one",
                "value": 95,
                "start": 0,
                "lo": 5,
                "hi": 99,
                "replicates": [],
            }
        ]
        fragment, _ = render_categorical_plot(
            records,
            BBox(0, 0, 218, 200),
            scale=scale,
            context=SeriesContext(["A"]),
            category_scale=CategoryScale(["one"]),
        )
        self.assertEqual(len(role(f"<svg>{fragment}</svg>", "bar")), 2)
        self.assertEqual(len(role(f"<svg>{fragment}</svg>", "bar-interval")), 2)
        with self.assertRaises(ValueError):
            scale.map(50, 0, 100)
        args = {"line_series": [{"name": "Rate", "values": [20, 30]}]}
        with self.assertRaises(ValueError):
            make_bar_academic([("A", {"value": 1}), ("B", {"value": 3})], **args)
        svg = make_bar_academic([("A", {"value": 1}), ("B", {"value": 3})], y_unit="mg", right_y_unit="%", **args)
        # Untitled axes state the unit explicitly instead of a bare "(mg)" caption line.
        self.assertIn(">Unit: mg<", svg)
        self.assertIn(">Unit: %<", svg)
        self.assertNotIn(">(mg)<", svg)
        self.assertTrue(role(svg, "curve"))
        self.assertFalse(issues(svg))
        svg = make_grouped_bar(
            ["A", "B", "C", "D", "E"],
            [("Bar", [{"value": i + 1} for i in range(5)])],
            line_series=[{"name": "Line", "values": [2.2, 3.2, None, 4.2, 5.2]}],
            y_unit="mg",
            right_y_unit="%",
        )
        bars = role(svg, "bar")
        points = role(svg, "observation")
        centers = [float(b.get("x")) + float(b.get("width")) / 2 for b in bars]
        self.assertEqual(len(role(svg, "curve")), 2)
        for point, center in zip(points, [centers[0], centers[1], centers[3], centers[4]]):
            self.assertAlmostEqual(float(point.get("cx")), center, places=2)
        self.assertFalse(issues(svg))
        with self.assertRaises(ValueError):
            make_bar_academic([("A", {"value": 1}), ("B", {"value": 2})], auto_test="welch", pairs="all")
        svg = make_bar_academic(
            [("A", [1, 2, 3]), ("B", [4, 5, 6])], auto_test="welch", pairs="all", multi_mode="single"
        )
        self.assertTrue(role(svg, "significance"))
        self.assertFalse(issues(svg))
        svg = make_grouped_bar(
            ["A"],
            [("One", [[1, 2, 3]]), ("Two", [[2, 3, 4]]), ("Three", [[3, 4, 5]])],
            orientation="horizontal",
            auto_test="welch",
            pairs="all",
        )
        self.assertEqual(len(role(svg, "significance")), 3)
        self.assertFalse(issues(svg))

    def test_forest_statistics_share_rows(self):
        rows = [
            {
                "row_id": "a",
                "label": "Arm A",
                "estimate": 1,
                "ci_lo": 0.5,
                "ci_hi": 2,
                "n": 30,
                "p": 0.2,
                "mean": 4,
                "sd": 1,
            },
            {
                "row_id": "b",
                "label": "Arm B",
                "estimate": 2,
                "ci_lo": 1,
                "ci_hi": 3,
                "n": 35,
                "p": 0.02,
                "mean": 6,
                "sd": 2,
            },
        ]
        svg = make_forest(rows, row_order=["b", "a"])
        self.assertEqual([r.get("data-row-id") for r in role(svg, "forest-row")], ["b", "a"])
        self.assertEqual(len(role(svg, "table-cell")), 10)
        self.assertFalse(issues(svg))
        with self.assertRaises(ValueError):
            make_forest([dict(rows[0], ci_lo=-1)], log_x=True)

    def test_swimmer_keeps_concurrent_times(self):
        svg = make_swimmer(
            [
                {
                    "id": "P1",
                    "segments": [{"start": 0, "end": 8, "treatment": "A"}],
                    "events": [{"time": 4, "kind": "Biopsy"}, {"time": 4, "kind": "Response"}],
                    "followup": {"start": 8, "end": 12, "ongoing": True},
                }
            ]
        )
        events = role(svg, "patient-event")
        self.assertEqual([e.get("data-time") for e in events], ["4.0", "4.0"])
        self.assertEqual([e.get("data-lane") for e in events], ["0", "1"])
        self.assertFalse(issues(svg))

    def test_adaptive_capacity_grows_without_dropping_categories_or_samples(self):
        categories = [f"Very long category {i}" for i in range(30)]
        svg = make_grouped_bar(categories, [("A", [[1, 2]] * 30)], width=400, height=300, multi_mode="single")
        self.assertEqual(issues(svg), [])
        self.assertEqual(len(role(svg, "replicate")), 60)
        self.assertTrue(all(name in svg for name in categories))
        self.assertGreater(float(ET.fromstring(svg).get("viewBox").split()[3]), 300)


# ====================================================================================================
# Explicit heterogeneous category Y groups share actual row geometry.
# ====================================================================================================


def example():
    categories = ["Patient A", "Patient B", "Patient C"]
    bars = []
    for i, names in enumerate((("T", "B"), ("Driver", "Passenger"))):
        bars.append(
            {
                "id": f"composition{i}",
                "name": f"Composition {i + 1}",
                "kind": "bar",
                "y_group": "patients",
                "data": {
                    "categories": categories,
                    "orientation": "horizontal",
                    "stack": "percent",
                    "value_domain": [0, 100],
                    "series": [
                        {"name": names[0], "values": [{"value": v} for v in (2, 3, 4)]},
                        {"name": names[1], "values": [{"value": v} for v in (8, 7, 6)]},
                    ],
                    "x_title": "Composition (%)",
                },
            }
        )
    bars.append(
        {
            "id": "mutation",
            "name": "Mutation rate",
            "kind": "xy",
            "y_group": "patients",
            "data": {
                "series": [
                    {
                        "name": "Mutation rate",
                        "color": "#8470B0",
                        "points": [{"x": x, "y": c} for x, c in zip((3, 7, 5), categories)],
                    }
                ],
                "x_title": "Mutations / Mb",
            },
        }
    )
    return bars


def geometry(svg):
    return json.loads(nodes(svg, "heterogeneous-panels-layout")[0].get("data-layout"))["panels"]


def centers(svg):
    result = []
    for panel in nodes(svg, "heterogeneous-panel"):
        rows = {}
        for mark in nodes(panel, "bar"):
            center = float(mark.get("y")) + float(mark.get("height")) / 2
            key = mark.get("data-row-id")
            assert key not in rows or abs(center - rows[key]) < 0.001
            rows[key] = center
        for mark in nodes(panel, "observation"):
            rows[mark.get("data-y")] = float(mark.get("cy"))
        result.append(rows)
    return result


@pytest.mark.parametrize("palette", ["archive_ink", "nightlab"])
def test_two_percent_compositions_and_mutations_share_every_actual_row(palette):
    data = example()
    before = deepcopy(data)
    svg = make_composite(data, template="panels", cols=3, palette=palette)
    assert data == before
    a, b, c = centers(svg)
    assert a == pytest.approx(b, abs=0.001)
    assert a == pytest.approx(c, abs=0.001)
    assert a["Patient A"] < a["Patient B"] < a["Patient C"]
    marks = nodes(nodes(svg, "heterogeneous-panel")[0], "bar")
    assert [float(n.get("data-value")) - float(n.get("data-start")) for n in marks] == [20, 30, 40, 80, 70, 60]
    observations = nodes(svg, "observation")
    assert [float(n.get("data-x")) for n in observations] == [3, 7, 5]
    assert {n.get("fill") for n in observations} == {"#8470B0"}


def test_shared_rows_survive_shuffles_missing_records_and_order():
    data = example()
    data[2]["data"]["series"][0]["points"] = [{"x": 5, "y": "Patient C"}, {"x": 3, "y": "Patient A"}]
    data[1]["data"]["categories"] = ["Patient A", "Patient C"]
    for item in data[1]["data"]["series"]:
        del item["values"][1]
    svg = make_composite(data, template="panels", cols=3)
    a, b, c = centers(svg)
    assert set(b) == set(c) == {"Patient A", "Patient C"}
    assert all(abs(a[k] - b[k]) < 0.001 and abs(a[k] - c[k]) < 0.001 for k in b)
    assert len(nodes(svg, "observation")) == 2
    assert {n.get("data-category") for n in nodes(svg, "row-label")} == {"Patient A", "Patient B", "Patient C"}
    data = example()
    data[0]["data"]["categories"] = ["Patient C", "Patient B", "Patient A"]
    for item in data[0]["data"]["series"]:
        item["values"].reverse()
    svg = make_composite(data, template="panels", cols=3)
    a, b, c = centers(svg)
    assert a == pytest.approx(b, abs=0.001)
    assert a == pytest.approx(c, abs=0.001)
    assert a["Patient C"] < a["Patient B"] < a["Patient A"]
    original = example()
    data = [original[0], original[2], deepcopy(original[1]), deepcopy(original[2])]
    data[2]["id"], data[3]["id"] = "second_bar", "second_xy"
    data[3]["name"] = "Second-row panel heading " * 8
    svg = make_composite(data, template="panels", cols=2)
    a, b, c, d = centers(svg)
    assert a == pytest.approx(b, abs=0.001)
    assert c == pytest.approx(d, abs=0.001)
    assert c["Patient A"] > a["Patient C"]


@pytest.mark.parametrize("height", [700, 1400])
def test_long_headers_and_axis_titles_preserve_shared_plot_top_and_bottom(height):
    data = example()
    data[0]["name"] = "Supplied percent composition with a deliberately long cohort and panel description " * 3
    data[1]["data"]["annotations"] = ["Supplied statistical annotation " * 8]
    data[2]["data"]["y_title"] = "Patient identity with a long explanatory row heading " * 4
    data[2]["data"]["x_title"] = "Mutation rate with a long denominator description " * 4
    svg = make_composite(data, template="panels", cols=3, height=height)
    a, b, c = centers(svg)
    assert a == pytest.approx(b, abs=0.001)
    assert a == pytest.approx(c, abs=0.001)
    bounds = [p["plot_bbox"][1::2] for p in geometry(svg)]
    assert bounds[0] == bounds[1] == bounds[2]
    host = ET.Element("slide")
    ET.SubElement(host, "embed").append(ET.fromstring(svg))
    assert not detect_embedded_svg_overlaps(host)


def test_global_identity_colors_do_not_add_unrelated_categorical_dodge_slots():
    canvas = ChartLayout(800, 650, "archive_ink", None)
    panel = _prepare(example()[2], canvas, 0)
    global_context = SeriesContext(["T", "B", "Driver", "Passenger", "Mutation rate"], pal=canvas.pal)
    global_context.colors["Mutation rate"] = "#123ABC"
    panel["context"] = global_context
    panel["axes"]["y"] = RowScale(panel["axes"]["y"].categories)
    panel["_row_gutters"] = (26, 52)
    result = _render(panel, canvas, BBox(28, 60, 772, 620))
    svg = canvas.svg("Local row slots with global colors")
    box = result["plot_bbox"]
    for point in nodes(svg, "observation"):
        expected = panel["axes"]["y"].map(point.get("data-y"), box.y0, box.y1)
        assert float(point.get("cy")) == pytest.approx(expected, abs=0.001)
        assert point.get("fill") == "#123ABC"


def test_inset_reservation_does_not_break_shared_main_row_centers():
    data = example()
    data[2]["data"]["inset"] = {"name": "Detail", "series": [{"name": "Detail", "curve": [(1, 1), (2, 2)]}]}
    svg = make_composite(data, template="panels", cols=3)
    panels = nodes(svg, "heterogeneous-panel")
    panels[-1].remove(nodes(panels[-1], "xy-inset")[0])
    a, b, c = centers(svg)
    assert a == pytest.approx(b, abs=0.001)
    assert a == pytest.approx(c, abs=0.001)
    g = geometry(svg)[2]
    assert g["plot_bbox"][3] < g["inset"]["bbox"][1]


def test_same_family_y_group_preserves_existing_category_direction():
    raw = example()[2]
    other = deepcopy(raw)
    other["id"] = "other"
    svg = make_composite([raw, other], template="panels", cols=2)
    a, b = centers(svg)
    assert a == pytest.approx(b, abs=0.001)
    assert a["Patient A"] > a["Patient B"] > a["Patient C"]


def test_grouped_bars_keep_their_offsets_around_the_shared_row_center():
    data = example()
    data[0]["data"]["stack"] = None
    svg = make_composite(data, template="panels", cols=3)
    bars = nodes(nodes(svg, "heterogeneous-panel")[0], "bar")
    dots = {n.get("data-y"): float(n.get("cy")) for n in nodes(svg, "observation")}
    for category, center in dots.items():
        offsets = [float(n.get("y")) + float(n.get("height")) / 2 for n in bars if n.get("data-row-id") == category]
        assert len(offsets) == 2 and offsets[0] != offsets[1]
        assert sum(offsets) / 2 == pytest.approx(center, abs=0.001)
