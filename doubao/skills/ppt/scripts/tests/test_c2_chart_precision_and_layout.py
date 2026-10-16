"""Synthetic fixtures for numerical precision, labels and bounded layouts."""

import copy
import math
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import gen_svg_charts as charts
from embed_svg_validator import validate_embedded_svgs, detect_embedded_svg_overlaps
from svg_lib.charts._chart_layout import precise_number, readable_annotation_color
from svg_lib.charts import _academic_rigor as rigor
from svg_lib._common import _estimate_label_width_px
from svg_lib.charts._chart_layout import forest_scale, wrap_lines
from svg_lib.charts._distribution import wrap
from svg_lib.charts.dumbbell import _dumbbell_ticks


def checked(svg):
    root = ET.fromstring(f"<slide><data><embed>{svg}</embed></data></slide>")
    assert not validate_embedded_svgs(root)
    assert not detect_embedded_svg_overlaps(root)
    return root


def texts(root):
    return ["".join(node.itertext()) for node in root.iter() if node.tag.endswith("text")]


def test_synthetic_forest_fits_full_header_footer_and_log_interval_geometry():
    rows = [
        dict(label="合成试验甲（界面布局测试用长标签，样本示例）", is_subgroup_header=True),
        dict(label="指标甲 · 合成分析（观察窗口 28 个月）", estimate=0.68, ci_lo=0.42, ci_hi=0.92),
        dict(label="指标乙 · 参考线邻近边界的精度测试", estimate=0.71, ci_lo=0.523, ci_hi=0.998),
        dict(label="合成试验乙（界面布局测试用长标签，样本示例）", is_subgroup_header=True),
        dict(label="指标乙 · 另一合成分析（观察窗口 38 个月）", estimate=0.78, ci_lo=0.58, ci_hi=0.94),
    ]
    note = "此处仅为排版回归的合成资料说明；各组合有独立的量纲与时间窗口，所示数值不代表真实试验。"
    source = "合成参考条目甲 2021；合成参考条目乙 2024；测试附录表 2"
    subtitle = "横轴为对数刻度比率，参考线为 1；例示不同已声明置信水平 98.25% 与 95%，不对应任何公开研究结果"
    root = checked(
        charts.make_forest(
            rows,
            log_x=True,
            width=1240,
            height=960,
            font_family="思源黑体",
            figure_label="FIG. 2",
            title="合成效应量与区间：保留参考线附近数值及完整说明文字",
            subtitle=subtitle,
            note=note,
            source=source,
        )
    )
    all_text = "".join(texts(root)).replace(" ", "")
    for value in (note, source, subtitle):
        assert value.replace(" ", "") in all_text
    domain = next(n for n in root.iter() if n.get("data-role") == "forest-layout")
    low, high = float(domain.get("data-domain-low")), float(domain.get("data-domain-high"))
    assert 0.3 < low <= 0.42 and 1 <= high < 2
    left, right = float(domain.get("data-plot-left")), float(domain.get("data-plot-right"))
    # The .523–.998 interval retains its logarithmic length; no fake gap at 1.
    expected = (right - left) * math.log(0.998 / 0.523) / math.log(high / low)
    ci_lines = [
        n
        for n in root.iter()
        if n.tag.endswith("line") and n.get("stroke-width") == "1.4" and n.get("y1") == n.get("y2")
    ]
    assert any(abs((float(n.get("x2")) - float(n.get("x1"))) - expected) < 0.2 for n in ci_lines)


@pytest.mark.parametrize("options", [{}, {"multi_mode": "single"}, {"multi_mode": "with_subgroup_facets"}])
def test_forest_explicit_domain_is_respected_and_cannot_hide_intervals(options):
    rows = [
        dict(label="A", estimate=0.7, ci_lo=0.5, ci_hi=0.9, subgroup="Trial A"),
        dict(label="B", estimate=0.8, ci_lo=0.6, ci_hi=0.95, subgroup="Trial B"),
    ]
    assert forest_scale([0.5, 0.95], 1, log_x=True, value_domain=(0.3, 1.2)).domain == (0.3, 1.2)
    checked(charts.make_forest(rows, log_x=True, value_domain=(0.1, 10), width=1500, height=950, **options))
    with pytest.raises(ValueError, match="contain every observation"):
        charts.make_forest(rows, log_x=True, value_domain=(0.6, 1), **options)


def test_summary_percent_bars_show_exact_values_without_invented_intervals():
    categories = ["合成类别甲", "合成类别乙", "合成类别丙", "合成类别丁"]
    series = [("合成方案甲", [[21.0], [34.7], [16.3], [28.4]]), ("合成方案乙", [[3.1], [7.8], [5.2], [12.4]])]
    options = dict(multi_mode="single", show_points=False, width=1180, height=700, y_unit="%")
    root = checked(charts.make_grouped_bar(categories, series, **options))

    def shown_values(tree):
        return {
            (n.get("data-series"), n.get("data-category")): float(n.text)
            for n in tree.iter()
            if n.get("data-role") == "bar-value-label"
        }

    shown = shown_values(root)
    assert shown == {(name, cat): cell[0] for name, cells in series for cat, cell in zip(categories, cells)}
    assert not any(n.get("data-role") == "bar-interval" for n in root.iter())
    hidden = checked(charts.make_grouped_bar(categories, series, show_values=False, **options))
    assert not shown_values(hidden)
    summary = [(name, [{"value": cell[0]} for cell in cells]) for name, cells in series]
    direct = checked(charts.make_grouped_bar(categories, summary, show_values=True, **options))
    assert shown_values(direct) == shown


def test_long_forest_axis_caption_uses_canvas_gutter_without_hiding_words():
    caption = "合成比率（对数刻度；虚线左侧表示低于参考值）"
    rows = [
        dict(label="终点·分析时点 " + str(i), estimate=0.71, ci_lo=0.523, ci_hi=0.998, ci_level=98.25 if i == 0 else 95)
        for i in range(8)
    ]
    root = checked(
        charts.make_forest(
            rows,
            width=700,
            height=470,
            log_x=True,
            x_title=caption,
            title="FIG. 3 合成数据区间森林图",
            subtitle="两组合成数据用于检验长轴题和脚注保留",
        )
    )
    assert caption.replace(" ", "") in "".join(texts(root)).replace(" ", "")


@pytest.mark.parametrize("options", [{}, {"multi_mode": "single"}, {"columns": []}])
def test_forest_preserves_source_digits_in_every_single_panel_route(options):
    row = {"label": "Synthetic ratio", "estimate": 0.71, "ci_lo": 0.5230000000000001, "ci_hi": 0.998}
    original = copy.deepcopy(row)
    root = checked(charts.make_forest([row], log_x=True, **options))
    assert "0.71 (0.523–0.998)" in texts(root)
    assert "Estimate (CI)" in texts(root)
    assert row == original


def test_forest_facet_precision_and_float_noise():
    rows = [
        dict(label="A", estimate=0.71, ci_lo=0.523, ci_hi=0.998, subgroup="Trial A"),
        dict(label="B", estimate=0.9, ci_lo=0.8, ci_hi=0.99996, subgroup="Trial B"),
    ]
    root = checked(charts.make_forest(rows, multi_mode="with_subgroup_facets", width=1600, height=900))
    assert "0.71 (0.523–0.998)" in texts(root)
    assert "0.90 (0.80–0.99996)" in texts(root)
    assert precise_number(0.1 + 0.2, decimals=2, reference=1) == "0.30"
    assert precise_number(0.5230000000000001, decimals=2, reference=1) == "0.523"
    assert precise_number(0.71, decimals=2, reference=1) == "0.71"


@pytest.mark.parametrize(
    "value,reference",
    [
        (0.998, 1),
        (0.99996, 1),
        (1.00004, 1),
        (-0.00004, 0),
        (0.00004, 0),
        (0.12499, 0.125),
        (0.12501, 0.125),
        (1e-20, 0),
        (math.nextafter(1, 0), 1),
    ],
)
def test_numeric_text_never_crosses_or_touches_a_distinct_reference(value, reference):
    shown = float(precise_number(value, decimals=2, reference=reference))
    sign = lambda x: (x > 0) - (x < 0)
    assert sign(shown - reference) == sign(value - reference)
    assert shown != 0


def test_forest_levels_explicit_mixed_unknown_and_fullwidth():
    rows = [
        dict(label="Metric A", estimate=0.68, ci_lo=0.42, ci_hi=0.92, ci_level=98.25),
        dict(label="Metric B", estimate=0.71, ci_lo=0.523, ci_hi=0.998, ci_level=95),
    ]
    root = checked(charts.make_forest(rows))
    assert any("98.25% CI" in t and "0.68" in t for t in texts(root))
    assert any("95% CI" in t and "0.71" in t for t in texts(root))
    assert "Estimate (CI level by row)" in texts(root)
    with pytest.raises(ValueError, match="conflicts with a row"):
        charts.make_forest(rows, right_header_label="HR (95% CI)")
    uniform = checked(charts.make_forest([dict(label="A", estimate=0.8, ci_lo=0.7, ci_hi=0.9)], ci_level=98.25))
    assert "Estimate (98.25% CI)" in texts(uniform)
    # A supplied percentage header is caller input, not a level inferred from bounds.
    explicit = checked(
        charts.make_forest([dict(label="A", estimate=0.8, ci_lo=0.7, ci_hi=0.9)], right_header_label="HR (95% CI)")
    )
    assert "HR (95% CI)" in texts(explicit)
    rows = [
        dict(label="A", estimate=0.7, ci_lo=0.6, ci_hi=0.9, ci_label="98.25% CI"),
        dict(label="B", estimate=0.8, ci_lo=0.7, ci_hi=0.95),
    ]
    root = checked(charts.make_forest(rows, columns=[]))
    assert "0.80 (0.70–0.95) · CI" in texts(root)
    assert any("98.25% CI" in t for t in texts(root))
    row = dict(label="Metric A", estimate=0.68, ci_lo=0.42, ci_hi=0.92, ci_label="９８.２５％置信区间")
    with pytest.raises(ValueError, match="contradicts ci_level"):
        charts.make_forest([dict(row, ci_level=95)])
    root = checked(charts.make_forest([dict(row, ci_level=98.25)]))
    assert "９８.２５％置信区间" in "".join(texts(root))
    row = dict(label="A", estimate=0.7, ci_lo=0.6, ci_hi=0.8)
    with pytest.raises(ValueError, match="conflicts with a row"):
        charts.make_forest([dict(row, ci_label="98.25%")], right_header_label="HR (95% CI)")
    with pytest.raises(ValueError, match="percentage must be"):
        charts.make_forest([dict(row, ci_label="120% CI")])


@pytest.mark.parametrize("header", ["HR（95%置信区间）", "HR（95％ CI）", "HR（９５％置信区间）"])
def test_forest_known_level_conflicts_are_detected_in_chinese_headers(header):
    row = dict(label="Metric A", estimate=0.68, ci_lo=0.42, ci_hi=0.92, ci_level=98.25)
    with pytest.raises(ValueError, match="conflicts with a row") as exc:
        charts.make_forest([row], right_header_label=header)
    assert str(exc.value)


def test_sparse_dumbbell_exact_values_compact_height_and_delta():
    rows = [dict(label="VendorA", before=47.6, after=45.3), dict(label="VendorBeta", before=36.0, after=35.5)]
    root = checked(charts.make_dumbbell(rows, x_min=30, x_max=50, x_unit="%"))
    annotations = [n for n in root.iter() if n.get("data-role") == "endpoint-value"]
    assert sorted(n.text for n in annotations) == sorted(["47.6", "45.3", "36.0", "35.5"])
    assert [n.text for n in root.iter() if n.get("data-role") == "row-delta"] == ["-2.3", "-0.5"]
    assert "Δ (pp)" in texts(root)
    assert [float(n.get("data-value")) for n in root.iter() if n.get("data-role") == "before"] == [47.6, 36.0]
    assert [float(n.get("data-value")) for n in root.iter() if n.get("data-role") == "after"] == [45.3, 35.5]
    minimal = checked(charts.make_dumbbell(rows, show_values=False, show_delta=False))
    assert not any(n.get("data-role") in ("endpoint-value", "row-delta") for n in minimal.iter())
    rows = [dict(label="A", before=10, after=11), dict(label="B", before=12, after=14)]
    # Measure the caller-selected minimal layout, then reuse that exact height.
    base = checked(charts.make_dumbbell(rows, show_values=False, show_delta=False))
    height = float(next(n for n in base.iter() if n.tag.endswith("svg")).get("viewBox").split()[3])
    checked(charts.make_dumbbell(rows, height=height + 0.01))
    with pytest.raises(ValueError, match="height must be at least"):
        charts.make_dumbbell(rows, height=120, show_values=True)
    root = checked(
        charts.make_dumbbell([dict(label="VendorBeta", before=36.976, after=36.528)], value_format=".1f", x_unit="%")
    )
    assert sorted(n.text for n in root.iter() if n.get("data-role") == "endpoint-value") == ["36.5", "37.0"]
    assert [n.text for n in root.iter() if n.get("data-role") == "row-delta"] == ["-0.4"]
    assert float(next(n for n in root.iter() if n.get("data-role") == "row-delta").get("data-value")) == pytest.approx(
        -0.448
    )


def test_palette_text_fallback_does_not_change_series_or_mutate_inputs():
    palette = {"bg": "#ffffff", "ink": "#0f172a", "muted": "rgba(100,116,139,0.6)", "series": ["#4338ca", "#64748b"]}
    original = copy.deepcopy(palette)
    assert readable_annotation_color(palette["muted"], palette) == palette["ink"]
    assert palette == original
    root = checked(charts.make_dumbbell([dict(label="A", before=2, after=3)], palette=palette, note="Reported data"))
    note = next(n for n in root.iter() if (n.text or "").startswith("Notes."))
    assert note.get("fill") == palette["ink"]
    assert palette == original


def test_synthetic_bubble_preserves_area_and_uses_short_ordered_labels():
    points = [
        {
            "name": "VendorA",
            "points": [
                {"x": 47.6, "y": 21.9, "size": 2.8, "label": "VendorA T1"},
                {"x": 45.3, "y": 20.4, "size": 3.3, "label": "VendorA T2"},
            ],
        },
        {
            "name": "VendorBeta",
            "points": [
                {"x": 36.2, "y": 9.9, "size": 39.2, "label": "VendorBeta T1"},
                {"x": 35.7, "y": 10.8, "size": 42.8, "label": "VendorBeta T2"},
            ],
        },
    ]
    original = copy.deepcopy(points)
    root = checked(
        charts.make_bubble(
            points,
            width=1100,
            height=760,
            r_max=30,
            note="Synthetic coordinates and unequal marker areas for a label placement regression fixture.",
            source="Synthetic fixture",
            font_family="思源黑体",
        )
    )
    marks = [n for n in root.iter() if n.get("data-role") == "observation"]
    assert len(marks) == 4 and points == original
    for mark, expected in zip(marks, [p for series in points for p in series["points"]]):
        assert float(mark.get("data-x")) == expected["x"] and float(mark.get("data-y")) == expected["y"]
        assert (float(mark.get("r")) / 30) ** 2 == pytest.approx(expected["size"] / 42.8, abs=1e-5)
    labels = {n.text: float(n.get("y")) for n in root.iter() if n.get("data-role") == "point-label"}
    assert labels["VendorA T1"] < labels["VendorA T2"]
    assert labels["VendorBeta T2"] < labels["VendorBeta T1"]
    for leader in [n for n in root.iter() if n.get("data-role") == "label-leader"]:
        vertices = [tuple(map(float, p)) for p in re.findall(r"[ML]([^, ]+),([^ ]+)", leader.get("d"))]
        assert sum(math.dist(a, b) for a, b in zip(vertices, vertices[1:])) < 40


@pytest.mark.parametrize("mode", ["auto", "with_facet_by_series", "single"])
def test_single_observation_grouped_cells_do_not_manufacture_sem(monkeypatch, mode):
    calls = []
    original = rigor.draw_error_bar

    def capture(*args, **kwargs):
        calls.append((args, kwargs))
        return original(*args, **kwargs)

    monkeypatch.setattr(rigor, "draw_error_bar", capture)
    root = checked(
        charts.make_grouped_bar(
            ["A", "B", "C"],
            [("Prior", [[47.6], [36.0], [43.0]]), ("Latest", [[45.3], [35.5], [42.0]])],
            multi_mode=mode,
        )
    )
    assert calls == []
    assert not any("error bars: sem" in t.lower() for t in texts(root))
    assert "n = 2" not in texts(root)


def test_zero_sem_from_repeated_equal_observations_is_still_valid():
    root = checked(charts.make_grouped_bar(["A", "B"], [("One", [[5, 5], [7, 7]])]))
    intervals = [n for n in root.iter() if n.get("data-role") == "grouped-interval"]
    assert [(float(n.get("data-low")), float(n.get("data-high"))) for n in intervals] == [(5, 5), (7, 7)]
    assert len([n for n in root.iter() if n.get("data-role") == "replicate"]) == 4


def test_dumbbell_ticks_markers_shared_height_and_formats():
    values, labels, _ = _dumbbell_ticks(30, 49)
    assert values == [30, 35, 40, 45]
    assert labels == ["30", "35", "40", "45"]
    assert _dumbbell_ticks(30, 49, [30, 33.8, 49])[0] == [30, 33.8, 49]
    root = checked(charts.make_dumbbell([dict(label="A", before=36.0, after=35.5)], x_min=30, x_max=49))
    layout = next(n for n in root.iter() if n.get("data-role") == "dumbbell-layout")
    assert layout.get("data-domain-low") == "30" and layout.get("data-domain-high") == "49"
    root = checked(
        charts.make_dumbbell([dict(label="Close", before=10, after=10.01), dict(label="Wide", before=0, after=20)])
    )
    for role in ("before", "after"):
        assert len({n.get("r") for n in root.iter() if n.get("data-role") == role}) == 1
    data = [dict(label="A", before=10, after=11), dict(label="B", before=12, after=14)]
    outputs = [
        checked(charts.make_dumbbell(data, width=700, height=500, plot_height=110, note=note, note_font_size=16))
        for note in ("Short source.", "Long source and accounting definition. " * 8)
    ]
    layout = [next(n for n in root.iter() if n.get("data-role") == "dumbbell-layout") for root in outputs]
    assert layout[0].get("data-plot-top") == layout[1].get("data-plot-top")
    assert layout[0].get("data-plot-bottom") == layout[1].get("data-plot-bottom")
    assert " ".join(texts(outputs[1])).count("accounting definition.") == 8
    with pytest.raises(ValueError, match="height must be at least"):
        charts.make_dumbbell(data, width=700, height=200, plot_height=110, note="Long source. " * 20, note_font_size=20)
    root = checked(charts.make_dumbbell([dict(label="A", before=1, after=1.5)], value_format="+.1f"))
    assert [n.text for n in root.iter() if n.get("data-role") == "row-delta"] == ["+0.5"]
    data = [dict(label="A", before=12.1, after=18.1)]
    neutral = checked(charts.make_dumbbell(data, x_unit="%"))
    assert "Δ (pp)" in texts(neutral)
    assert not any("after" in t or "before" in t for t in texts(neutral))
    explicit = checked(charts.make_dumbbell(data, x_unit="%", delta_label="营收 − 费用（pp）"))
    assert "营收 − 费用（pp）" in texts(explicit)
    assert [n.text for n in explicit.iter() if n.get("data-role") == "row-delta"] == ["+6.0"]


def test_wrapping_preserves_words_acronyms_and_unit_runs():
    text = "合成口径：GAAP 与BenchmarkX说明；单位pg/mL，边界HR=0.998。"
    for lines in (wrap_lines(text, 150, 14, "Inter, sans-serif"), wrap(text, 150, 14)):
        assert "".join(lines).replace(" ", "") == text.replace(" ", "")
        for token in ("GAAP", "BenchmarkX", "pg/mL", "HR=0.998"):
            assert any(token in line for line in lines)
    long_word = "UnexpectedlyLongUnbrokenSourceIdentifier"
    lines = wrap_lines(long_word, 50, 14, "Inter, sans-serif")
    assert len(lines) > 1 and "".join(lines) == long_word


@pytest.mark.parametrize("width", [70, 100, 130, 160, 200])
def test_axis_units_and_closing_punctuation_are_not_orphaned(width):
    text = "销售与市场费用率（%）；Operating margin (%)，GAAP（报告口径）。"
    lines = wrap_lines(text, width, 14, "Inter, sans-serif")
    assert "".join(lines).replace(" ", "") == text.replace(" ", "")
    assert all(not line.startswith(tuple("）)]，。；")) for line in lines if line)
    assert all(not line.endswith(tuple("（([")) for line in lines if line)
    assert all(_estimate_label_width_px(line, 14, font_family="Inter, sans-serif") <= width for line in lines)


def test_kinetics_wraps_complete_note_and_source_on_separate_measured_rows():
    note = "Complete conditions and measurement definitions for the formatting fixture. " * 2
    source = "Source citation with author, title, year, DOI and retrieval context. " * 2
    curves = [dict(name="Formatting fixture", time=[0, 1, 2, 3], value=[1, 2, 3, 4], fit_type="none")]
    root = checked(
        charts.make_kinetics(curves, width=1000, height=700, note=note, source=source, show_rate_constants=False)
    )
    plain = "".join(texts(root)).replace(" ", "")
    assert note.replace(" ", "") in plain and source.replace(" ", "") in plain
    assert any(t.startswith("Notes.") for t in texts(root)) and any(t.startswith("Source.") for t in texts(root))
    with pytest.raises(ValueError, match="too short for full note/source"):
        charts.make_kinetics(curves, width=500, height=300, note=note * 4, source=source * 4)
