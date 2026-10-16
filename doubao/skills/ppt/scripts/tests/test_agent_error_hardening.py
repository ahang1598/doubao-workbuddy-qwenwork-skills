"""Regression tests for errors real agents hit when driving the chart and drawing libraries."""

import re
import sys
import warnings
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

import gen_svg_charts as charts
from svg_lib.charts._academic_rigor import log_ticks
from svg_lib.charts._chart_layout import forest_scale, uniform_value_labels
from svg_lib.svg_drawing import Drawing
from gen_svg_charts import chart_fit

ROWS = [
    {"label": "A", "estimate": 1.2, "ci_lo": 0.9, "ci_hi": 1.6},
    {"label": "B", "estimate": 1.8, "ci_lo": 1.3, "ci_hi": 2.5},
    {"label": "C", "estimate": 1.1, "ci_lo": 0.95, "ci_hi": 1.3},
]
COEF_ROWS = [
    {"label": "a", "estimate": 1.0, "lo": 0.5, "hi": 2.0},
    {"label": "b", "estimate": 1.5, "lo": 1.2, "hi": 2.2},
]


# 1. rgba()/named colours in drawings ------------------------------------------------------------


def test_arrow_with_rgba_stroke_gets_valid_marker_id_and_hex_paint():
    d = Drawing(400, 300)
    a = d.box_at((60, 60), "A", font_size=12, fill="steelblue")
    b = d.box_at((300, 200), "B", font_size=12)
    d.arrow(a, b, stroke="rgba(74,127,163,1)")
    d.arrow(b, a, stroke="rgba(74,127,163,0.5)", head="inhibit")
    root = ET.fromstring(d.to_svg())
    ids = {m.get("id") for m in root.iter("{http://www.w3.org/2000/svg}marker")}
    assert ids and all(re.fullmatch(r"[A-Za-z0-9_-]+", i) for i in ids)
    refs = [e.get("marker-end") for e in root.iter() if e.get("marker-end")]
    assert refs and all(r[5:-1] in ids for r in refs)
    svg = d.to_svg()
    assert "rgba(" not in svg and "steelblue" not in svg
    assert 'fill="#4682B4"' in svg and 'stroke="#4A7FA3"' in svg and 'stroke-opacity="0.5"' in svg


# 2. SVG text-anchor words as text_at anchors -----------------------------------------------------


@pytest.mark.parametrize(
    "anchor, box_anchor, text_anchor",
    [
        ("start", "left", "start"),
        ("left", "left", "start"),
        ("middle", "center", "middle"),
        ("end", "right", "end"),
        ("right", "right", "end"),
    ],
)
def test_text_at_accepts_text_anchor_aliases(anchor, box_anchor, text_anchor):
    d = Drawing(400, 200)
    node = d.text_at((200, 100), "label", font_size=14, anchor=anchor)
    assert node.own_anchor == box_anchor
    assert f'text-anchor="{text_anchor}"' in d.to_svg()
    d.text_at((50, 50), "kept", font_size=14, anchor="top_left")  # box anchors still work


# 3. coef_plot reference=None ---------------------------------------------------------------------


def test_coef_reference_background_and_unknown_kwargs():
    assert 'data-role="zero-line"' not in charts.make_coef_plot(rows=COEF_ROWS, reference=None)
    assert 'data-role="zero-line"' in charts.make_coef_plot(rows=COEF_ROWS, value_min=0)
    series = [
        {
            "name": "s",
            "points": [{"x": k, "y": 1 + k * 0.1, "lo": 0.8 + k * 0.1, "hi": 1.2 + k * 0.1} for k in range(-2, 3)],
        }
    ]
    assert 'data-role="zero-line"' not in charts.make_coef_plot(series=series, reference=None)
    svg = charts.make_coef_plot(rows=COEF_ROWS, background="#10141C")
    assert "#10141C" in svg.upper()
    svg = charts.make_forest(ROWS, log_x=True, bg="rgb(242,244,248)", palette="archive_ink")
    assert "#F2F4F8" in svg.upper()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        assert "<slide" in charts.chart_slide("forest", 0, 0, 600, 320, rows=ROWS, background="white")
    with pytest.raises(TypeError) as info:
        charts.make_coef_plot(rows=COEF_ROWS, widht=600)
    message = str(info.value)
    assert "'widht'" in message and "did you mean 'width'" in message and "Valid parameters:" in message
    with pytest.raises(TypeError, match="dpi"):
        charts.make_forest(ROWS, dpi=300)
    with pytest.raises(TypeError, match="y_title"):  # matplotlib-style misspelling points at our name
        charts.make_scatter(points=[{"name": "s", "points": [{"x": 1, "y": 2}, {"x": 2, "y": 3}]}], ylabl="y")


# 4. background= / stray kwargs -------------------------------------------------------------------


# 5. default font for atomized drawing text -------------------------------------------------------


def test_drawing_text_defaults_to_chart_sans_and_keeps_greek():
    d = Drawing(400, 200)
    d.text_at((200, 100), "γ ν Δ σ ≈", font_size=16)
    xml = d.to_slide(x=0, y=0, width=400, summary=False)
    contents = [c for c in ET.fromstring(f"<r>{xml}</r>").iter() if c.tag.endswith("content")]
    assert contents and contents[0].get("fontFamily") == "思源黑体"
    assert "γ ν Δ σ ≈" in "".join(contents[0].itertext())


# 6. uniform decimals for value labels ------------------------------------------------------------


def test_tick_and_value_label_decimals_and_log_ticks():
    assert uniform_value_labels([6, 5.5]) == ["6.0", "5.5"]
    assert uniform_value_labels([6, 5.5, 4.257]) == ["6.00", "5.50", "4.26"]
    assert uniform_value_labels([6, 5, 4]) == ["6", "5", "4"]
    svg = charts.make_grouped_bar(
        ["a", "b", "c"], [{"name": "s", "values": [{"value": 6}, {"value": 5.5}, {"value": 4}]}], show_values=True
    )
    assert re.findall(r"bar-value-label[^>]*>([^<]*)", svg) == ["6.0", "5.5", "4.0"]
    assert log_ticks(0.9, 2.5) == [1.0, 1.5, 2.0, 2.5]
    assert len(log_ticks(0.5, 3)) >= 4 and len(log_ticks(1.5, 1.9)) >= 4
    assert log_ticks(1, 1000) == [1.0, 10.0, 100.0, 1000.0]
    assert len(forest_scale([0.5, 3], 1, log_x=True).ticks) >= 4


# 7. log axes under a decade get >= 4 labeled ticks -----------------------------------------------


@pytest.mark.parametrize("kw", [{}, {"width": 500, "height": 360}, {"value_domain": (0.9, 2.5)}])
def test_forest_log_axis_has_at_least_four_labels(kw):
    svg = charts.make_forest(ROWS, log_x=True, **kw)
    labels = re.findall(r"<text[^>]*>([\d.]+)</text>", svg)
    assert len(labels) >= 4 and "1" in labels


def test_chart_fit_reports_scale_and_boxes_without_placing():
    rows = [{"label": f"条件 {i}", "before": 10 * (i + 1), "after": 1} for i in range(4)]
    fit = chart_fit("dumbbell", 848, 300, rows=rows, title="下降倍数", x_title="倍数")
    assert 0 < fit["scale"] <= 1
    assert set(fit["box_for"]) == {"100%", "80%", "70%"}
    assert fit["box_for"]["100%"] == fit["canvas"]
