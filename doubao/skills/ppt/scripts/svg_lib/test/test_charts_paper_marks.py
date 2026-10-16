"""Journal-figure marks, coef_plot and chart defaults seen on real slides."""

from __future__ import annotations

import re
import sys
import warnings
import unittest
from html import unescape
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import gen_svg_charts as g

from ..charts.coef_plot import make_coef_plot
from ..charts.dumbbell import make_dumbbell
from ..charts.forest import make_forest
from ..charts.grouped_bar import make_grouped_bar
from ..charts.scatter_fit import make_scatter
from .. import chart_split
from ..charts._chart_layout import axis_caption, is_orphan_line, wrap_lines
from .._common import _estimate_label_width_px, _estimate_label_width_px as measure
from ..charts._chart_layout import ChartLayout
from ..charts.coef_plot import _interaction_text, _tick_labels
from ..charts.spectrum import make_spectrum
from gen_svg_charts import chart_slide


# ====================================================================================================
# Journal-figure marks: endpoint CIs / P / n on dumbbells, coef benchmarks, forest favours, bar reference lines.
# ====================================================================================================

ROWS = [
    {
        "label": "HbA1c 达标率",
        "before": 32.1,
        "after": 48.6,
        "before_lo": 28.0,
        "before_hi": 36.2,
        "after_lo": 44.1,
        "after_hi": 53.0,
        "p": "<0.001",
        "n": 412,
        "delta_ci": (10.2, 22.8),
    },
    {
        "label": "体重下降≥5%",
        "before": 18.4,
        "after": 27.9,
        "before_lo": 15.0,
        "before_hi": 21.8,
        "after_lo": 23.9,
        "after_hi": 31.9,
        "p": 0.003,
        "n": 398,
        "delta_ci": (4.1, 14.9),
    },
    {"label": "低血糖事件", "before": 6.2, "after": 5.1, "p": 0.42, "n": 405, "delta_ci": (-3.9, 1.7)},
]


FOREST = [
    {"label": "年龄 <65", "estimate": 0.72, "ci_lo": 0.60, "ci_hi": 0.86, "n": 1840, "events": "212/198", "p": 0.0004},
    {"label": "年龄 ≥65", "estimate": 0.81, "ci_lo": 0.66, "ci_hi": 0.99, "n": 1310, "events": "180/171", "p": 0.04},
    {"label": "eGFR <60", "estimate": 0.69, "ci_lo": 0.55, "ci_hi": 0.87, "n": 1020, "events": "150/140", "p": 0.002},
    {"label": "eGFR ≥60", "estimate": 0.88, "ci_lo": 0.72, "ci_hi": 1.07, "n": 2130, "events": "242/229", "p": 0.19},
    {
        "label": "总体",
        "estimate": 0.77,
        "ci_lo": 0.68,
        "ci_hi": 0.87,
        "n": 3150,
        "events": "392/369",
        "p": "<0.001",
        "is_overall": True,
    },
]


FAVOURS = ("SGLT2i 更优", "安慰剂更优")


def _texts(svg):
    return [unescape(re.sub(r"<[^>]+>", "", t)).strip() for t in re.findall(r"<text[^>]*>(.*?)</text>", svg, re.S)]


def _view_width(svg):
    return float(re.search(r'viewBox="0 0 ([0-9.]+)', svg).group(1))


def _text_right_edges(svg):
    edges = []
    for attrs, body in re.findall(r"<text([^>]*)>(.*?)</text>", svg, re.S):
        x = float(re.search(r'\bx="([-0-9.]+)"', attrs).group(1))
        fs = float(re.search(r'font-size="([0-9.]+)"', attrs).group(1))
        w = _estimate_label_width_px(unescape(re.sub(r"<[^>]+>", "", body)), fs)
        anchor = re.search(r'text-anchor="(\w+)"', attrs)
        anchor = anchor.group(1) if anchor else "start"
        edges.append(x + (w if anchor == "start" else w / 2 if anchor == "middle" else 0))
    return edges


def test_dumbbell_paper_marks_cis_stars_and_chart_slide_fields():
    svg = make_dumbbell(ROWS, series_labels=("基线", "24 周"), x_unit="%", x_title="达标比例", width=560, height=330)
    texts = _texts(svg)
    assert {"P<0.001", "P=0.003", "P=0.42", "n = 412", "(10.2–22.8)", "Δ (pp)"} <= set(texts)
    assert any("−3.9" in t and "1.7" in t for t in texts)
    assert svg.count('data-role="before-ci"') == 2 and svg.count('data-role="after-ci"') == 2
    assert max(_text_right_edges(svg)) <= _view_width(svg) + 1
    rows = [dict(r, delta_unit="mmol/L") for r in ROWS]
    svg = make_dumbbell(rows, series_labels=("Before", "After"), p_style="stars", width=900, height=420)
    texts = _texts(svg)
    assert {"***", "**", "ns"} <= set(texts)
    assert any("mmol/L" in t for t in texts)
    assert any("P<0.05" in t for t in texts)  # star legend is spelled out in the note
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fragment = chart_slide("dumbbell", 40, 110, 560, 330, rows=ROWS, series_labels=("基线", "24 周"), x_unit="%")
    for text in ("P=0.003", "n = 412", "(10.2–22.8)"):
        assert text in fragment


@pytest.mark.parametrize("labels", [("下限", "上限"), ("min", "max"), ("Lower", "Upper"), ("low", "high")])
def test_dumbbell_rejects_range_endpoints(labels):
    with pytest.raises(ValueError, match="coef_plot") as exc:
        make_dumbbell([{"label": "a", "before": 1, "after": 2}], series_labels=labels)
    assert str(exc.value)


def test_coef_plot_row_benchmarks_and_stat_columns():
    rows = [
        {"label": "本研究", "estimate": 62.5, "lo": 55.1, "hi": 69.4, "benchmark": 40, "n": 128, "p": "<0.001"},
        {"label": "KEYNOTE-189", "estimate": 48.0, "lo": 43.2, "hi": 52.9, "benchmark": 34, "n": 410, "p": 0.002},
        {"label": "真实世界", "estimate": 30.1, "lo": 24.0, "hi": 36.5, "n": 220},
    ]
    for width in (560, 700):
        svg = make_coef_plot(rows=rows, unit="%", reference=None, benchmark_label="历史对照", width=width, height=330)
        texts = _texts(svg)
        assert {"历史对照", "N", "P", "128", "P<0.001", "P=0.002"} <= set(texts)
        assert svg.count('data-role="benchmark"') == 2
        assert max(_text_right_edges(svg)) <= width + 1
    with pytest.raises(ValueError, match="benchmark"):
        make_coef_plot(rows=[{"label": "a", "estimate": 1}], benchmark_label="x")


@pytest.mark.parametrize("stats", [True, False])
def test_forest_slide_size_columns_diamond_and_favours(stats):
    rows = FOREST if stats else [{k: v for k, v in r.items() if k not in ("n", "p", "events")} for r in FOREST]
    svg = make_forest(rows, x_title="风险比", log_x=True, width=700, height=330, favours=FAVOURS)
    texts = _texts(svg)
    assert "← SGLT2i 更优" in texts and "安慰剂更优 →" in texts
    assert "forest-diamond" in svg or "<polygon" in svg
    if stats:
        assert {"P", "N", "事件数", "<0.001", "0.002", "0.19", "212/198", "3150"} <= set(texts)
    assert max(_text_right_edges(svg)) <= 700 + 1


def test_grouped_bar_reference_lines_in_every_cartesian_view():
    ref = [{"value": 1, "label": "无富集 (=1)"}]
    cats = ["糖酵解", "氧化磷酸化", "TNF-α 信号", "IFN-γ 应答", "缺氧"]
    summary = [("富集倍数", [{"value": v} for v in (3.2, 0.6, 2.1, 4.8, 1.4)])]
    wide = [("富集倍数", [{"value": v} for v in (32, 0.6, 2.1, 48, 1.4)])]
    interval = [("富集倍数", [{"value": v, "lo": v * 0.7, "hi": v * 1.3} for v in (3.2, 0.6, 2.1, 4.8, 1.4)])]
    for kwargs in (
        dict(series=summary),
        dict(series=summary, orientation="vertical", multi_mode="single"),
        dict(series=wide, value_scale="log"),
        dict(series=interval),
    ):
        svg = make_grouped_bar(cats, reference_lines=ref, width=560, height=330, **kwargs)
        assert 'data-role="reference-line"' in svg and "无富集 (=1)" in _texts(svg), kwargs


def test_single_series_scatter_has_no_legend_and_no_duplicate_unit():
    svg = make_scatter(
        [{"name": "模型", "points": [{"x": 1, "y": 2}, {"x": 3, "y": 5}, {"x": 5, "y": 4}]}],
        x_title="准确率 (%，越高越好)",
        x_unit="%",
        y_title="速度",
    )
    texts = _texts(svg)
    assert "模型" not in texts and 'role="legend-symbol"' not in svg
    assert "准确率 (%，越高越好)" in texts and not any(t.endswith("(%)") for t in texts)
    two = make_scatter(
        [
            {"name": "A", "points": [{"x": 1, "y": 2}, {"x": 2, "y": 3}]},
            {"name": "B", "points": [{"x": 1, "y": 3}, {"x": 2, "y": 1}]},
        ],
        x_title="准确率",
        x_unit="%",
    )
    assert "legend-symbol" in two and "准确率 (%)" in _texts(two)


# --- observational spectra and footer prefixes ------------------------------------------------------


def _transit():
    pts = [{"x": 3.0 + 0.2 * i, "y": 2.18 + 0.01 * (i % 3), "y_err": 0.01} for i in range(10)]
    mx = [3.0 + 0.1 * i for i in range(19)]
    model = {"name": "最佳拟合", "x": mx, "y": [2.19] * 19, "lo": [2.185] * 19, "hi": [2.195] * 19}
    return dict(
        points=pts,
        models=[model],
        bands=[{"start": 4.2, "end": 4.4, "label": "CO₂"}],
        x_title="波长",
        x_unit="μm",
        y_title="凌星深度",
        y_unit="%",
    )


def test_spectrum_points_models_bands_and_single_caption():
    svg = make_spectrum(**_transit(), width=800, height=380)
    texts = _texts(svg)
    assert svg.count('data-role="error-bar"') == 10 and svg.count('data-role="point"') == 10
    assert 'data-role="model-band"' in svg and 'data-role="model"' in svg and 'data-role="absorption-band"' in svg
    assert "CO₂" in texts and "最佳拟合" in texts and "波长 (μm)" in texts and "凌星深度 (%)" in texts
    assert "%" not in texts and "μm" not in texts  # no isolated unit line
    ticks = sorted(float(t) for t in texts if re.fullmatch(r"\d+\.\d+", t) and float(t) < 3)
    assert ticks[0] > 2.0  # axis hugs a 2.2% transit depth, not 0
    # x/y + y_err= form draws the same error bars
    alt = make_spectrum([p["x"] for p in _transit()["points"]], [p["y"] for p in _transit()["points"]], y_err=0.01)
    assert alt.count('data-role="error-bar"') == 10
    xs = [400 + i for i in range(200)]
    ys = [max(0.0, 1 - abs(x - 480) / 20) for x in xs]
    stick = make_spectrum(xs, ys, peaks=[(480, "A")], x_title="波长", x_unit="nm")
    band = make_spectrum(xs, ys, peaks=[(480, "A")], x_title="波长 (nm)", x_unit="nm", peak_style="band")
    assert 'data-role="peak-band"' in band and 'data-role="peak-band"' not in stick
    for svg in (stick, band):
        assert _texts(svg).count("波长 (nm)") == 1 and "nm" not in _texts(svg)
    with pytest.raises(ValueError, match="peak_style"):
        make_spectrum(xs, ys, peak_style="bar")


def test_dumbbell_and_coef_footer_prefix_not_doubled():
    rows = [{"label": c, "before": 1, "after": 2} for c in "abc"]
    svg = make_dumbbell(rows, note="注：数据为均值", source="来源：Smith 2020", width=700)
    texts = " ".join(_texts(svg))
    assert "注：注" not in texts and "来源：来源" not in texts and "注：数据为均值" in texts
    plain = " ".join(_texts(make_dumbbell(rows, note="数据为均值", width=700)))
    assert "注：数据为均值" in plain
    coef = " ".join(
        _texts(
            make_coef_plot(
                rows=[{"label": c, "estimate": 1, "lo": 0.5, "hi": 1.5} for c in "abc"],
                source="Source: NEJM",
                width=700,
                height=330,
            )
        )
    )
    assert "Source: NEJM" in coef and "Source. Source" not in coef and "来源：Source" not in coef


# ====================================================================================================
# Coefficient plots: signed estimates, event-study structure, Chinese chrome and slide fitting.
# ====================================================================================================

POINTS = [
    {"x": k, "y": y, "lo": y - 0.03, "hi": y + 0.03}
    for k, y in zip([-4, -3, -2, 0, 1, 2, 3], [0.01, -0.005, 0.008, -0.02, -0.035, -0.05, -0.045])
]


COEF_ROWS = [
    {"label": "Card & Krueger (1994)", "estimate": 0.13, "lo": -0.2, "hi": 0.46, "group": "经典研究"},
    {"label": "Neumark & Wascher (2000)", "estimate": -0.22, "lo": -0.4, "hi": -0.04, "group": "经典研究"},
    {"label": "Jardim et al. (2017)", "estimate": -0.9, "lo": -1.4, "hi": -0.4, "group": "群聚估计"},
]


def test_event_study_has_event_line_base_marker_and_negative_ticks():
    svg = make_coef_plot(
        series=[{"name": "TWFE", "points": POINTS}],
        base_x=-1,
        ci_level=95,
        x_title="Years relative to policy",
        width=1060,
        height=450,
    )
    assert svg == make_coef_plot(
        series=[{"name": "TWFE", "points": POINTS}],
        base_x=-1,
        ci_level=95,
        x_title="Years relative to policy",
        width=1060,
        height=450,
    )
    assert 'data-role="event-line"' in svg or "stroke-dasharray" in svg
    texts = _texts(svg)
    assert "Reference period" in texts
    assert any(t.startswith("−") for t in texts)
    assert len({len(t.split(".")[-1]) for t in texts if re.fullmatch(r"−?\d+\.\d+", t)}) <= 1


def test_coef_plot_negative_estimates_chinese_chrome_and_interval_check():
    svg = make_coef_plot(rows=COEF_ROWS, x_title="就业弹性", ci_level=95, width=1060, height=450)
    texts = _texts(svg)
    assert "−0.90 [−1.40, −0.40]" in texts
    assert "经典研究" in texts and "Card & Krueger (1994)" in texts
    svg = make_coef_plot(series=[{"name": "就业", "points": POINTS}], base_x=-1, ci_level=95, width=1060, height=450)
    texts = " ".join(_texts(svg))
    assert "基期" in texts and "置信区间" in texts
    assert "Reference period" not in texts and "Event time" not in texts
    with pytest.raises(ValueError, match="outside its interval"):
        make_coef_plot(rows=[{"label": "A", "estimate": 1.0, "lo": 0.0, "hi": 0.5}])


@pytest.mark.parametrize("box", [(56, 120, 848, 360), (56, 120, 480, 320)])
def test_chart_slide_fits_both_layouts(box):
    root = str(Path(__file__).resolve().parents[2])
    if root not in sys.path:
        sys.path.insert(0, root)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for kwargs in (
            {"rows": COEF_ROWS, "x_title": "就业弹性"},
            {"series": [{"name": "就业", "points": POINTS}], "base_x": -1},
        ):
            fragment = chart_slide("coef_plot", *box, **kwargs)
            sizes = [float(v) for v in re.findall(r'fontSize="([\d.]+)"', fragment)]
            assert sizes and min(sizes) >= 10


def test_panels_tick_format_and_interaction_text():
    with pytest.raises(ValueError, match="panels=True splits series"):
        make_coef_plot(rows=COEF_ROWS, panels=True)
    short = [{"x": h, "y": 0.1 * h, "lo": 0.1 * h - 0.1, "hi": 0.1 * h + 0.1} for h in range(5)]
    long = [{"x": h, "y": -0.05 * h, "lo": -0.05 * h - 0.1, "hi": -0.05 * h + 0.1} for h in range(9)]
    svg = make_coef_plot(series=[{"name": "A", "points": short}, {"name": "B", "points": long}], panels=True, band=True)
    ticks = re.findall(r'data-role="x-tick"[^>]*>([^<]*)', svg)
    assert ticks.count("8") == 2  # the short response is drawn on the same 0–8 horizon axis
    assert _tick_labels([2, 2.5, 3], 1) == ["2.0", "2.5", "3.0"]
    assert _tick_labels([-1, 0, 1, 2], 3) == ["−1", "0", "1", "2"]
    assert (
        _interaction_text({"b": 0.12, "ci": (0.04, 0.2), "p": 0.004}) == "Interaction B = 0.12, [0.04, 0.20], p = .004"
    )
    assert _interaction_text("B = 0.1") == "B = 0.1"
    with pytest.raises(ValueError):
        _interaction_text({"se": 0.1})


# ====================================================================================================
# Regressions for chart defaults seen on real Chinese academic slides.
# ====================================================================================================

CATS = ["逻辑回归", "随机森林", "XGBoost", "深度神经网络"]


AUC = [["ROC-AUC", [{"value": v} for v in (0.81, 0.86, 0.88, 0.90)]]]


def texts(svg):
    return [re.sub("<[^>]+>", "", t) for t in re.findall(r"<text[^>]*>(.*?)</text>", svg, re.S)]


def slide(slug, box, **kwargs):
    """chart_slide plus the SVG it rendered and the warnings it raised."""
    seen = {}
    original = chart_split.split_chart_svg

    def capture(svg, **kw):
        seen["svg"] = svg
        return original(svg, **kw)

    chart_split.split_chart_svg = capture
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            g.chart_slide(slug, box=box, **kwargs)
    finally:
        chart_split.split_chart_svg = original
    return seen["svg"], [str(w.message) for w in caught]


class OrphanUnitTest(unittest.TestCase):
    def test_wrap_and_layout_text_never_orphan_units(self):
        # Fits when rejoined, or when the previous word moves down with the unit.
        for text, width in (("平均住院时间中位数 (h)", 180), ("Model discrimination (ROC-AUC)", 240)):
            lines = wrap_lines(text, width, 16, "Inter, sans-serif")
            self.assertFalse(any(is_orphan_line(line) for line in lines), lines)
            self.assertEqual("".join(lines).replace(" ", ""), text.replace(" ", ""))
            self.assertTrue(all(measure(v, 16, font_family="Inter, sans-serif") <= width for v in lines), lines)
        for text, width in (("Discrimination (ROC-AUC)", 190), ("平均住院时间中位数 (h)", 150)):
            layout = ChartLayout(600, 400, "archive_ink", None)
            self.assertTrue(any(is_orphan_line(v) for v in wrap_lines(text, width, 16, layout.font)))
            layout.text(text, 0, 0, fs=16, width=width)
            lines = [box[4] for box in layout.text_boxes]
            self.assertFalse(any(is_orphan_line(v) for v in lines), lines)

    def test_axis_captions_without_title_and_on_one_line(self):
        self.assertEqual(axis_caption("", "ROC-AUC"), "ROC-AUC")
        self.assertEqual(axis_caption("时间", "h"), "时间 (h)")
        self.assertEqual(axis_caption("得分", "分"), "得分 (分)")  # 分 inside 得分 is not the unit
        self.assertEqual(axis_caption("", "h", chart_title="住院时间 (h)"), "")
        bar, _ = slide("grouped_bar", (0, 0, 420, 360), categories=CATS, series=AUC, y_unit="ROC-AUC", y_title="")
        bar_t = texts(bar)
        self.assertNotIn("(ROC-AUC)", bar_t)
        self.assertIn("ROC-AUC", bar_t)
        rows = [
            {"label": "逻辑回归", "before": 0.78, "after": 0.81},
            {"label": "随机森林", "before": 0.82, "after": 0.86},
            {"label": "XGBoost", "before": 0.84, "after": 0.88},
        ]
        bell, _ = slide("dumbbell", (0, 0, 380, 300), rows=rows, x_unit="ROC-AUC")
        self.assertIn("ROC-AUC", texts(bell))
        self.assertNotIn("5", texts(bell))
        self.assertIn("0.775", texts(bell))  # tick no longer split into "0.77" / "5"
        self.assertNotIn("0.77", texts(bell))
        fit, _ = slide(
            "scatter_fit",
            (0, 0, 420, 340),
            points=[(1, 0.81), (2, 0.83), (3, 0.86), (4, 0.87), (5, 0.9)],
            x_title="训练集规模",
            x_unit="万例",
            y_title="",
            y_unit="ROC-AUC",
        )
        self.assertNotIn("(ROC-AUC)", texts(fit))
        self.assertIn("训练集规模 (万例)", texts(fit))
        rows = [
            {"label": n, "estimate": e, "ci_lo": e - 0.1, "ci_hi": e + 0.2}
            for n, e in (("A", 1.2), ("B", 0.9), ("C", 1.5))
        ]
        svg, _ = slide("forest", (0, 0, 600, 380), rows=rows, x_title="比值比", x_unit="OR")
        self.assertIn("比值比 (OR)", texts(svg))
        self.assertNotIn("(OR)", texts(svg))


class SingleSeriesLegendTest(unittest.TestCase):
    def test_grouped_bar_vertical_and_horizontal(self):
        for orientation in ("vertical", "horizontal"):
            svg = g.make_grouped_bar(CATS, AUC, y_title="模型区分度", orientation=orientation, width=600, height=420)
            self.assertEqual(texts(svg).count("ROC-AUC"), 0, orientation)  # series name is not a legend entry
        two = g.make_grouped_bar(
            CATS[:3],
            [
                ["内部", [{"value": 1}, {"value": 2}, {"value": 3}]],
                ["外部", [{"value": 2}, {"value": 3}, {"value": 4}]],
            ],
            width=600,
            height=420,
        )
        self.assertIn("内部", texts(two))


class BoundedMetricTest(unittest.TestCase):
    def test_close_bars_warn_but_keep_zero_baseline(self):
        svg, msgs = slide("grouped_bar", (0, 0, 520, 360), categories=CATS, series=AUC, y_unit="ROC-AUC", upgrade=False)
        self.assertTrue(any("dumbbell" in m and "value_min" in m for m in msgs), msgs)
        self.assertRegex(svg, r'data-domain="\(0(\.0)?, ')
        _, msgs = slide(
            "grouped_bar",
            (0, 0, 520, 360),
            categories=CATS,
            series=[["得分", [{"value": v} for v in (30, 60, 80, 90)]]],
            y_unit="分",
        )
        self.assertFalse(any("dumbbell" in m for m in msgs), msgs)


class HorizontalValuesTest(unittest.TestCase):
    def test_horizontal_show_values_labels_bar_ends(self):
        svg = g.make_grouped_bar(CATS, AUC, orientation="horizontal", show_values=True, width=600, height=400)
        self.assertTrue({"0.81", "0.86", "0.88", "0.90"} <= set(texts(svg)))
        ends = {
            m.group(3): float(m.group(1)) + float(m.group(2))
            for m in re.finditer(
                r'<rect x="([0-9.]+)"[^>]*?width="([0-9.]+)"[^>]*data-role="bar"[^>]*?data-value="([0-9.]+)"', svg
            )
        }
        labels = {
            m.group(2): float(m.group(1))
            for m in re.finditer(r'<text x="([0-9.]+)"[^>]*text-anchor="start"[^>]*>(0\.\d\d)</text>', svg)
        }
        self.assertEqual(len(ends), 4)
        for value, end in ends.items():
            label = labels[f"{float(value):.2f}"]
            self.assertTrue(end < label < end + 20, (value, end, label))  # just past the bar end


class ChartChromeTest(unittest.TestCase):
    def test_slide_fonts_and_no_automatic_figure_label(self):
        svg, _ = slide("grouped_bar", (0, 0, 520, 360), categories=CATS, series=AUC)
        families = set(re.findall(r'font-family="([^"]+)"', svg))
        self.assertTrue(families)
        self.assertFalse([f for f in families if "Serif" in f or "Georgia" in f], families)
        svg, _ = slide("grouped_bar", (0, 0, 520, 360), categories=CATS, series=AUC)
        self.assertFalse([t for t in texts(svg) if re.search(r"(?i)\bfig(ure)?\.?\s*\d", t)])
        labelled = g.make_grouped_bar(CATS, AUC, figure_label="图 2", width=600, height=420)
        self.assertIn("图 2", texts(labelled))


class ForestWithoutCITest(unittest.TestCase):
    ROWS = [{"label": "年龄", "estimate": 1.2}, {"label": "BMI", "estimate": 0.9}, {"label": "吸烟", "estimate": 1.6}]

    def test_forest_without_ci_route_and_partial_intervals(self):
        svg, msgs = slide("forest", (0, 0, 600, 380), rows=self.ROWS, x_title="比值比")
        self.assertTrue(any("coef_plot(rows=" in m for m in msgs), msgs)
        self.assertFalse([t for t in texts(svg) if "CI" in t], texts(svg))
        self.assertIn("1.20", texts(svg))
        svg, msgs = slide("forest", (0, 0, 600, 380), rows=[dict(r, n=50) for r in self.ROWS])
        self.assertTrue(any("coef_plot" in m for m in msgs))
        self.assertNotIn('data-role="forest-interval"', svg)
        rows = [dict(r, ci_lo=r["estimate"] - 0.1, ci_hi=r["estimate"] + 0.2) for r in self.ROWS]
        svg, msgs = slide("forest", (0, 0, 600, 380), rows=rows)
        self.assertFalse(any("coef_plot" in m for m in msgs))
        self.assertTrue(any("CI" in t for t in texts(svg)))
        with self.assertRaises(ValueError):
            g.make_forest(rows=[{"label": "A", "estimate": 1.0, "ci_lo": 0.8}], width=600, height=380)
