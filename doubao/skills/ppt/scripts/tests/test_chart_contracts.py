"""Regression tests for data preservation and the public chart entry points."""

import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

import gen_svg_charts as charts
from svg_lib._common import _fmt_axis, _is_dark_palette, _resolve_palette, _rgb_tuple, _rgba_with_alpha
from svg_lib.charts import _academic_rigor as rigor
from svg_lib.charts.bar_academic import _ci95
from svg_lib.charts.gantt import draw_gantt
from svg_lib.charts.pyramid import draw_pyramid
from svg_lib.charts.sankey import _normalize_chord
from svg_lib.charts.scatter_fit import _linreg
import math
import warnings
from svg_lib._common import _delta_e, _derive_series_colors, _estimate_label_width_px
from svg_lib.chart_examples import EXAMPLES
from svg_lib.charts._chart_layout import log_axis_ticks, wrap_axis_title, wrap_lines


def test_sankey_flow_loss_references_and_chord_weights():
    for variant in (None, "multi_layer_flat", "gradient_layered"):
        with pytest.raises(ValueError, match="not conserved"):
            charts.make_sankey(
                layers=[["Source"], ["Middle"], ["Destination"]],
                inter_flows=[[("Source", "Middle", 10)], [("Middle", "Destination", 5)]],
                variant=variant,
            )
    with pytest.raises(ValueError, match="endpoint"):
        charts.make_sankey(["A"], ["B"], [("unknown", "B", 2)])
    with pytest.raises(ValueError, match="finite"):
        charts.make_sankey(["A"], ["B"], [("A", "B", float("nan"))])
    svg = charts.make_sankey(
        layers=[["A", "B"], ["C"], ["D", "E"]],
        inter_flows=[[("A", "C", 3), ("B", "C", 2)], [("C", "D", 4), ("C", "E", 1)]],
    )
    assert ET.fromstring(svg).tag.endswith("svg")
    nodes, flows = _normalize_chord({"nodes": ["A", "B"], "flows": [("A", "B", 2), ("A", "B", 2)]})
    assert nodes == ["A", "B"] and flows == [("A", "B", 4)]


def test_gantt_numeric_calendar_progress_and_units():
    import re

    svg = charts.make_gantt([("Preparation", 0.25, 1.5), ("Review", 2.25, 3.5)], weeks=5, critical_index=0)
    text = " ".join(ET.fromstring(svg).itertext())
    assert "2025" not in text and "Jan" not in text and "%" not in text and "slack" not in text
    assert "Preparation" in text and "Review" in text
    assert "Critical path" in text
    assert "Critical path" not in charts.make_gantt([("A", 0, 1)], critical_index=0, show_legend=False)
    with pytest.raises(ValueError, match="progress for every task"):
        charts.make_gantt([("A", 0, 1)], variant="progress_split")
    with pytest.raises(ValueError, match="precede"):
        charts.make_gantt([("A", 2, 1)])
    svg = draw_gantt({"tasks": [{"name": "A", "start": 0, "end": 4, "progress": 25}]}, variant="progress_split")
    assert "25%" in svg
    unknown = [{"name": "A", "start": "2026-01-01", "end": "2026-01-05"}]
    svg = charts.make_gantt(unknown, today="2026-01-03")
    text = " ".join(ET.fromstring(svg).itertext())
    assert "0/1 tasks reported" in text and "0/1 statuses reported" in text
    assert "0%" not in text
    svg = charts.make_gantt([{**unknown[0], "progress": 25.5, "status": "on-track"}], today="2026-01-03")
    assert "25.5%" in svg
    for value in (-1, 101, float("nan")):
        with pytest.raises(ValueError, match="progress"):
            charts.make_gantt([{**unknown[0], "progress": value}])
    for progress in (0, 0.5, 25.5, 100):
        task = {"name": "A", "start": "2026-01-01", "end": "2026-01-05", "progress": progress}
        svg = charts.make_gantt([task], variant="progress_split", today="2026-01-03")
        reported = [e.get("data-progress") for e in ET.fromstring(svg).iter() if e.get("data-role") == "task-progress"]
        assert reported == [f"{progress:g}"]
        assert f"{progress:g}%" in svg
        for variant in ("default_flat", "progress_split"):
            with pytest.raises(ValueError, match="domain"):
                charts.make_gantt([task], variant=variant, project_start="2026-01-02", project_end="2026-01-04")
    svg = charts.make_gantt([("A", 1, 3)], weeks=10, variant="default_flat")
    assert "10" in list(ET.fromstring(svg).itertext())
    svg = charts.make_gantt([("Myoglobin", 1, 24, "early"), ("cTnI", 3, 240, "specific")], time_unit="h")
    assert re.search(r">\d+ h</text>", svg)


def test_palettes_percent_grids_and_spectrum_baselines():
    import re

    for variant in (None, "square_10x10", "dot_10x10", "person_10x10", "square_stacked_row", "dot_faceted"):
        for data in ([("A", 80), ("B", 30)], [("A", 1.5), ("B", 20)], [("A", -1), ("B", 20)]):
            with pytest.raises(ValueError):
                charts.make_percent_grid(data, variant=variant)
    assert _rgb_tuple("#369") == (51, 102, 153)
    assert _rgb_tuple("#336699cc") == (51, 102, 153)
    assert _rgba_with_alpha("#fff", 0.4) == "rgba(255,255,255,0.4)"
    palette = _resolve_palette({"bg": "#101318", "ink": "#eeeeff", "accent": "#44aadd"})
    assert _is_dark_palette(palette)
    assert palette["ink6"] == "rgba(238,238,255,0.6)"
    for name in ("burgundy_analyst", "morandi_cool", "archive_ink", "nature_cover"):
        colors = _derive_series_colors(_resolve_palette(name), 3)
        assert min(_delta_e(a, b) for a, b in zip(colors, colors[1:])) >= 12, name
    assert _derive_series_colors(_resolve_palette("archive_ink"), 2) == _resolve_palette("archive_ink")["series"][:2]
    xs = [i / 2 for i in range(200)]
    ys = [1000 if 48 < x < 52 else (-25 if i % 7 == 0 else 5) for i, x in enumerate(xs)]
    svg = charts.make_spectrum(xs, ys, width=900, height=450)
    assert not any(t.startswith(("-", "−")) for t in re.findall(r">(−?-?\d+)</text>", svg))
    curve = [{"x": x, "y": 1 - x / 100} for x in range(0, 61, 20)]
    series = [{"name": n, "points": curve, "curve": curve} for n in ("A", "B")]
    assert "direct-label" in charts.make_scatter(series, width=700, height=400)
    assert "direct-label" not in charts.make_scatter(series, width=700, height=400, end_labels=False)


def test_stacked_pyramid_requires_real_component_data():
    with pytest.raises(ValueError, match="explicit"):
        charts.make_population_pyramid(["A", "B"], [10, 20], [15, 25], variant="stacked_flat")
    with pytest.raises(ValueError, match="sum to total"):
        draw_pyramid(
            {
                "categories": ["A", "B"],
                "left": [10, 20],
                "right": [15, 25],
                "left_series": [("first", [1, 2])],
                "right_series": [("first", [15, 25])],
            },
            variant="stacked_flat",
        )
    svg = charts.make_population_pyramid(
        ["A", "B"], {"observed": [7, 11], "remaining": [3, 9]}, {"observed": [8, 20], "remaining": [7, 5]}
    )
    assert "Citizens" not in svg and "Migrants" not in svg
    assert "observed" in svg and "remaining" in svg


def test_statistics_student_t_perfect_fit_undefined_effects_and_units():
    # df=4 critical value from the Student-t distribution, not normal 1.96.
    assert rigor.student_t_critical(4) == pytest.approx(2.7764451051977996, rel=1e-8)
    assert _ci95([1, 2, 3, 4, 5]) == pytest.approx(1.963243161477561, rel=1e-8)
    with pytest.raises(ValueError, match="at least two"):
        _ci95([1])
    assert _linreg([1, 2, 3, 4], [2, 4, 6, 8])[3] < 1e-20
    assert _linreg([1, 1, 1], [1, 2, 3])[3] == 1
    with pytest.raises(ValueError, match="two observations"):
        rigor.effect_size_cohens_d([1], [2])
    with pytest.raises(ValueError, match="undefined"):
        rigor.effect_size_cohens_d([1, 1], [2, 2])
    a, b = [1, 2, 4, 5, 7], [2, 4, 5, 7, 8]
    for function in (rigor.effect_size_cohens_d, rigor._welch_t_test, rigor._student_t_test):
        expected = function(a, b)
        for factor in (1e-170, 1e170):
            assert function([v * factor for v in a], [v * factor for v in b]) == pytest.approx(expected)


def test_ticks_for_tiny_ranges_offsets_log_colour_and_one_decade():
    import re

    ticks, low, high = rigor.nice_axis(1e-14, 3e-14, 4)
    assert 0 < low <= 1e-14
    assert 3e-14 <= high < 1e-13
    assert len(set(ticks)) == len(ticks) >= 3
    assert len({_fmt_axis(value, high - low) for value in ticks}) == len(ticks)
    svg = ET.fromstring("<svg>" + rigor.draw_colorbar(50, 20, 20, 160, 1e-14, 3e-14, orient="vertical") + "</svg>")
    labels = svg.findall("text")
    assert len(labels) >= 3
    assert all(label.text != "0" and 10 <= float(label.get("y")) <= 190 for label in labels)
    ticks, low, high = rigor.nice_axis(1e12 + 0.001, 1e12 + 0.008, 5)
    labels = [_fmt_axis(value, high - low) for value in ticks]
    assert len(labels) >= 3
    assert len(labels) == len(set(labels))
    colors = [rigor.value_to_color(value, 1e-200, 1e200, log=True) for value in (1e-200, 1.0, 1e200)]
    assert len(set(colors)) == 3
    svg = ET.fromstring(
        "<svg>" + rigor.draw_colorbar(20, 20, 20, 180, 1e-200, 1e200, log=True, orient="vertical") + "</svg>"
    )
    assert len(svg.findall("text")) <= 8
    with pytest.raises(ValueError, match="positive"):
        rigor.log_axis(0, 10)
    chart_slide = charts.chart_slide

    narrow = log_axis_ticks(24.0, 133.0)
    assert narrow and all(float(f"{t:.3g}") == t for t in narrow), narrow
    assert all(str(t).rstrip("0").rstrip(".")[0] in "12345" for t in narrow), narrow
    assert log_axis_ticks(2.5, 4000.0) == [10.0, 100.0, 1000.0]
    frag = chart_slide(
        "scatter",
        36,
        106,
        520,
        356,
        y_transform="log10",
        points=[{"name": "s", "points": [{"x": k + 1, "y": v} for k, v in enumerate([28, 40, 56, 80, 114])]}],
    )
    labels = re.findall(r"<p>([^<]*)</p>", frag)
    assert not any(v in labels for v in ("25.83", "38.2", "56.5", "83.55", "123.6")), labels
    assert "100" in labels


def test_unsupported_options_and_explicit_composition():
    with pytest.raises(ValueError, match="variant"):
        charts.make_bar_academic([("A", [1, 2, 3])], variant="invented")
    with pytest.raises(ValueError, match="fit"):
        charts.make_scatter_fit([(1, 2), (2, 3), (3, 5)], fit="quadratic")
    spec = {"detail": ("top_bottom_3to1", lambda _: True, lambda _: (False, "missing detail data"))}
    with pytest.raises(ValueError, match="missing detail data"):
        rigor.resolve_multi_mode_v2("detail", spec, {}, rigor.BBox(0, 0, 1200, 900))
    spec["detail"] = ("top_bottom_3to1", lambda _: True, lambda _: (True, ""))
    with pytest.raises(ValueError, match="plot area"):
        rigor.resolve_multi_mode_v2("detail", spec, {}, rigor.BBox(0, 0, 100, 100))
    assert rigor.resolve_multi_mode_v2("auto", spec, {}, rigor.BBox(0, 0, 100, 100))[0] is None


def test_help_and_cli_use_the_actual_registry(tmp_path):
    assert "candle" in charts.chart_catalog()
    assert "nested_donut" in charts.chart_catalog()
    payload = tmp_path / "chart.json"
    payload.write_text(json.dumps({"matrix": [[-0.5, 0], [0.3, 1]], "labels": ["A", "B"]}))
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "gen_svg_charts.py"), "--type", "matrix_heat", "--data-file", str(payload)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert ET.fromstring(result.stdout).tag.endswith("svg")


# --- 2026-10-12 decks: IRF panels, grouped coef rows, ratio forests, palettes, card background, explicit modes ---


def _caught(fn):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        out = fn()
    return out, [str(c.message) for c in caught]


def _irf(scale, sign=1):
    pts = []
    for h in range(9):
        y = sign * scale * h * math.exp(-h / 3) / 3
        pts.append({"x": h, "y": y, "lo": y - 0.3 * scale, "hi": y + 0.3 * scale})
    return pts


def test_irf_band_from_horizon_zero_has_no_event_line_and_panels_share_x():
    import re

    svg = charts.make_coef_plot(series=[{"name": "output", "points": _irf(1, -1)}], band=True)
    assert 'data-role="ci-band"' in svg and 'data-role="zero-line"' in svg
    assert 'data-role="event-line"' not in svg  # horizon 0 is the shock, not a policy date
    series = [{"name": n, "points": _irf(s)} for n, s in (("GDP", 1), ("CPI", 0.3), ("Rate", 2), ("Spread", 0.5))]
    svg = charts.make_coef_plot(series=series, panels=True, band=True, x_title="Quarters after shock", ci_level=90)
    panels = re.findall(r'data-role="coef-panel" data-series="([^"]+)"', svg)
    assert panels == ["GDP", "CPI", "Rate", "Spread"]
    assert svg.count('data-role="ci-band"') == 4 and "90% CI" in svg
    with pytest.raises(ValueError, match="at least two series"):
        charts.make_coef_plot(series=series[:1], panels=True)
    frag, msgs = _caught(
        lambda: charts.chart_slide("coef_plot", 40, 100, 880, 420, series=series, panels=True, band=True)
    )
    assert "<shape" in frag and not any("crowded" in m for m in msgs)


def test_coef_rows_groups_and_no_interval_legend():
    import re

    rows = [
        {"label": "base", "estimate": 0.3, "lo": 0.1, "hi": 0.5, "group": "Policy rate"},
        {"label": "ctrl", "estimate": 0.2, "lo": 0, "hi": 0.4, "group": "Policy rate"},
        {"label": "base", "estimate": 0.6, "lo": 0.3, "hi": 0.9, "group": "Spread"},
    ]
    svg = charts.make_coef_plot(rows=rows)
    legend = re.findall(r'data-role="group-legend" data-group="([^"]+)"', svg)
    assert legend == ["Policy rate", "Spread"]
    fills = {
        re.search(r'fill="([^"]+)"', p).group(1) for p in re.findall(r'<path[^>]*data-role="coef-point"[^>]*>', svg)
    }
    assert len(fills) == 2
    _, msgs = _caught(
        lambda: charts.chart_slide(
            "coef_plot", 40, 100, 640, 330, rows=[{"label": c, "estimate": v} for c, v in zip("abc", (1, 2, 3))]
        )
    )
    assert any("无区间不宜用系数图" in m and "dumbbell" in m for m in msgs)
    pts = [{"x": x, "y": y} for x, y in [(1, 0.2), (2, 0.35), (3, 0.3)]]
    svg = charts.make_coef_plot(
        series=[{"name": "城市", "points": pts}, {"name": "农村", "points": [dict(p, y=p["y"] - 0.1) for p in pts]}]
    )
    assert "置信区间" not in svg and "CI" not in re.sub(r"<[^>]+>", " ", svg)
    svg = charts.make_coef_plot(
        rows=[{"label": "a", "estimate": 0.110}, {"label": "b", "estimate": 0}, {"label": "c", "estimate": 2.5}],
        width=640,
    )
    values = re.findall(r'data-role="row-value"[^>]*>([^<]*)', svg)
    assert values == ["0.11", "0.00", "2.50"]  # max reported precision, not "0"
    assert "置信区间" not in svg and "CI" not in values
    ticks = re.findall(r'data-role="x-tick"[^>]*>([^<]*)', svg)
    assert len({len(t.split(".")[1]) if "." in t else 0 for t in ticks}) == 1


def test_ratio_forest_auto_log_axis_and_missing_ci_warning():
    import re

    rows = [
        {"label": "A", "estimate": 0.45, "ci_lo": 0.3, "ci_hi": 0.68},
        {"label": "B", "estimate": 8.5, "ci_lo": 4.1, "ci_hi": 17.6},
        {"label": "C", "estimate": 0.9, "ci_lo": 0.7, "ci_hi": 1.15},
    ]
    ticks = lambda svg: re.findall(r'data-role="x-tick"[^>]*>([^<]*)', svg)
    auto = charts.make_forest(rows, x_title="OR")
    assert (
        "1" in ticks(auto)
        and "10" in ticks(auto)
        and "20" not in ticks(charts.make_forest(rows, x_title="OR", log_x=False))[:1]
    )
    assert auto == charts.make_forest(rows, x_title="OR", log_x=True)
    assert auto != charts.make_forest(rows, x_title="OR", log_x=False)
    sparse = rows[:1] + [{"label": k, "estimate": v} for k, v in (("D", 1.2), ("E", 0.8))]
    _, msgs = _caught(lambda: charts.chart_slide("forest", 40, 100, 700, 330, rows=sparse, x_title="HR"))
    assert any("2/3 行没有 CI" in m for m in msgs)


def test_palette_by_series_name_list_and_bad_input():
    rows = [{"label": c, "before": 1, "after": 2} for c in "abc"]
    svg = charts.make_dumbbell(rows, series_labels=("Pre", "Post"), palette={"Pre": "#1F4E79", "Post": "#C0504D"})
    assert "#1F4E79" in svg and "#C0504D" in svg
    svg = charts.make_spectrum(
        points=[{"x": i, "y": 1 + i / 100, "y_err": 0.01} for i in range(6)],
        models=[{"name": "Best fit", "x": list(range(6)), "y": [1 + i / 100 for i in range(6)]}],
        palette={"Best fit": "#2E7D32"},
    )
    assert "#2E7D32" in svg
    assert "#111111" in charts.make_dumbbell(rows, palette=["#111111", "#999999"])
    with pytest.raises(ValueError, match="neither palette fields .* nor series/group names"):
        charts.make_dumbbell(rows, series_labels=("Pre", "Post"), palette={"Control": "#123456"})
    with pytest.raises(ValueError, match="is not a colour"):
        charts.make_dumbbell(rows, series_labels=("Pre", "Post"), palette={"Pre": "dark-ish"})


def test_chart_slide_background_and_explicit_bars():
    import re

    card = re.compile(
        r'<shape type="rect" topLeftX="[-\d.]+" topLeftY="[-\d.]+" width="([\d.]+)" height="([\d.]+)"><fill><fillColor'
    )
    for slug in ("coef_plot", "dumbbell", "forest", "boxplot", "gantt", "grouped_bar"):
        frag, _ = _caught(lambda: charts.chart_slide(slug, 0, 0, 600, 400, **EXAMPLES[slug]))
        assert not any(float(w) * float(h) > 0.5 * 600 * 400 for w, h in card.findall(frag)), slug
    frag, _ = _caught(
        lambda: charts.chart_slide("coef_plot", 0, 0, 600, 400, background="#FFFFFF", **EXAMPLES["coef_plot"])
    )
    assert any(float(w) * float(h) > 0.5 * 600 * 400 for w, h in card.findall(frag))
    kwargs = dict(
        categories=["A", "B", "C"], series=[{"name": "x", "values": [1, 2, 3]}, {"name": "y", "values": [2, 3, 4]}]
    )
    frag, msgs = _caught(lambda: charts.chart_slide("grouped_bar", 0, 0, 600, 400, multi_mode="bars", **kwargs))
    assert not any("drew 'dumbbell'" in m for m in msgs)
    _, msgs = _caught(lambda: charts.chart_slide("grouped_bar", 0, 0, 600, 400, **kwargs))
    assert any("drew 'dumbbell'" in m for m in msgs)


def test_frontier_and_size_key_inside_plot():
    import re

    pts = [
        (3, 58, 3, "E"),
        (7, 62, 7, "A"),
        (13, 66, 13, "B"),
        (40, 64, 40, "I"),
        (70, 75, 70, "C"),
        (405, 80, 405, "H"),
    ]
    svg = charts.make_bubble(pts, x_transform="log10", frontier=True, width=900, height=520)
    assert 'data-role="pareto-front"' in svg and "Pareto front" in svg
    # The size key sits inside the plot area (below the top of the y axis), not in a band above it.
    key_y = [float(v) for v in re.findall(r'<circle[^>]*\bcy="([\d.]+)"[^>]*data-role="size-legend"', svg)]
    plot_top = min(float(v) for v in re.findall(r'<path d="M[\d.]+,([\d.]+) H[\d.]+"[^>]*data-role="grid"', svg))
    assert key_y and min(key_y) > plot_top
    s = charts.make_scatter([{"x": x, "y": y} for x, y, _, _ in pts], frontier="max", x_transform="log10")
    assert s.count('data-role="pareto-front"') >= 1
    with pytest.raises(ValueError, match="frontier must be"):
        charts.make_scatter([{"x": 1, "y": 2}, {"x": 2, "y": 3}], frontier="best")


def test_axis_titles_break_at_spaces_and_keep_symbols_and_units():
    text = "患者比例 (%)"
    width = _estimate_label_width_px(text, 16, font_family="Inter") * 0.8
    lines, size = wrap_axis_title(text, width, 16, "Inter")
    assert "".join(lines).replace(" ", "") == text.replace(" ", "")
    assert lines[0] in ("患者比例", "患者比例 (%)") and size <= 16
    for w in range(60, 260, 10):
        assert not any(l.rstrip().endswith(" p") for l in wrap_lines("注：仅报告 p 值，未报告置信区间", w, 14, "Inter"))
    lines, _ = wrap_axis_title("标准化系数（仅报告 p 值的研究未纳入 CI 计算）", 330, 18, "Inter")
    assert not any(l.rstrip().endswith((" p", "CI")) for l in lines[:-1])
    pts = [(5, 0, 1e5), (25, 20, 1e3), (45, 0, 10)]
    model = [(5, 0), (25, 20), (45, 0), (60, 15), (90, 45)]
    svg = charts.make_nyquist_bode(
        nyquist_points=pts, magnitude_unit="Ω·cm²", width=800, height=520, models=[{"name": "R(RQ)W", "points": model}]
    )
    assert svg.count("Ω·cm²") == 2 and 'data-role="nyquist-model"' in svg
    assert ">90<" in svg or ">100<" in svg  # Warburg tail extends the axis instead of being clipped
    assert "Ω·cm²</text>" not in re.sub(r"\([^)]*Ω·cm²\)</text>", "", svg)


# --- 2026-10-12 r19 decks: d-forest favours, heterogeneity, coef formatting, contrast, units, moderators ---
_D_ROWS = [
    {"label": "Study A", "estimate": 0.31, "ci_lo": 0.12, "ci_hi": 0.50},
    {"label": "Study B", "estimate": 0.08, "ci_lo": -0.15, "ci_hi": 0.31},
    {"label": "Study C", "estimate": 0.45, "ci_lo": 0.20, "ci_hi": 0.70},
    {"label": "Pooled", "estimate": 0.27, "ci_lo": 0.11, "ci_hi": 0.43, "is_overall": True},
]


def test_difference_forest_warns_about_favours_direction_and_prints_heterogeneity():
    _, msgs = _caught(
        lambda: charts.chart_slide(
            "forest",
            40,
            100,
            880,
            380,
            rows=_D_ROWS,
            midline_value=0,
            x_title="Cohen's d",
            favours=("对照更优", "干预更优"),
            heterogeneity=dict(I2=43, tau2=0.02, p=0.03),
        )
    )
    assert any("右侧通常=干预更优" in m for m in msgs)
    _, msgs = _caught(
        lambda: charts.chart_slide(
            "forest",
            40,
            100,
            880,
            380,
            rows=_D_ROWS[:3] + [dict(_D_ROWS[3], estimate=0.8, ci_lo=0.7, ci_hi=0.9)],
            x_title="HR",
            favours=("A", "B"),
        )
    )
    assert not any("右侧通常" in m for m in msgs)
    for extra in ({}, {"n": 50}):  # plain and statistics-table layouts
        svg = charts.make_forest(
            [dict(r, **extra) for r in _D_ROWS],
            midline_value=0,
            width=880,
            height=420,
            heterogeneity=dict(I2=43, tau2=0.02, p=0.03),
        )
        assert "I²=43%" in svg and "τ²=0.02" in svg
    with pytest.raises(ValueError, match="pooled row"):
        charts.make_forest(_D_ROWS[:3], midline_value=0, heterogeneity={"I2": 10})


def test_moderator_interaction_plot_annotates_term_without_event_line():
    xs = [-2, -1, 0, 1, 2]
    arm = lambda b, s: [{"x": x, "y": b + s * x, "lo": b + s * x - 1, "hi": b + s * x + 1} for x in xs]
    svg = charts.make_coef_plot(
        series=[{"name": "干预", "points": arm(5, 0.5)}, {"name": "对照", "points": arm(4, 1)}],
        band=True,
        reference=None,
        x_title="基线成绩（中心化）",
        interaction={"b": -0.5, "se": 0.12, "p": "<.01"},
    )
    assert "交互项 B = −0.50, SE = 0.12, p &lt; .01" in svg
    assert 'data-role="event-line"' not in svg
    xs_drawn = {float(v) for v in re.findall(r'data-role="coef-point"[^>]*data-x="([^"]+)"', svg)}
    assert xs_drawn == set(map(float, xs))
    with pytest.raises(ValueError, match="series="):
        charts.make_coef_plot(rows=[{"label": "a", "estimate": 1, "lo": 0, "hi": 2}], interaction={"b": 1})
    assert "调节效应 / 异质性" in charts.chart_help()
