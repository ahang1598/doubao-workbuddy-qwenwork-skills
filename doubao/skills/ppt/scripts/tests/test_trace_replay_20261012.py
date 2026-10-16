"""Calls that misled agents in real traces (2026-10-12): discoverability, parseable output, chart facts."""

import re
import warnings

import pytest

from scripts.gen_svg_charts import (
    chart_slide,
    make_dumbbell,
    make_gantt,
    make_grouped_bar,
    make_scatter,
    make_stress_strain,
)
from scripts.svg_lib.svg_drawing import Drawing, drawing_help
from scripts.gen_svg_relations import make_relation_atomized
from scripts.svg_lib._common import _estimate_label_width_px, _rgb_tuple
from scripts.svg_lib.atomize_svg_to_slide import (
    _publish as pub,
    native_table,
    slide_help,
)
from scripts.svg_lib.atomize_svg_to_slide._config import _CFG
from scripts.svg_lib.drawing_lib import Drawing as D2, cell
from scripts.svg_lib.drawing_lib._scene import _format_layout_hints
from scripts.svg_lib.svg_drawing import cell as facade_cell

warnings.filterwarnings("ignore")


def _texts(svg):
    return re.findall(r"<text[^>]*>([^<]*)</text>", svg)


# --- discoverability -------------------------------------------------------------------------------------


def test_slide_and_drawing_help_entry_points_and_package_imports():
    text = slide_help()
    for name in (
        "publish_slide(page_xml",
        "page_frame(title",
        "native_bullets(items",
        "native_text(text",
        "native_line(start",
        "native_table(rows",
    ):
        assert name in text
    assert cell is facade_cell and D2 is Drawing
    with pytest.raises(ImportError):
        from scripts.svg_lib.drawing_lib import no_such_part  # noqa: F401
    assert "from scripts.svg_lib.svg_drawing import Drawing, cell" in drawing_help("cell")
    assert "from scripts.svg_lib.svg_drawing import" in drawing_help("parts")
    d = Drawing(400, 300)
    box = d.box_at((100, 100), "x")
    with pytest.raises(ValueError, match="第一个参数是 key"):
        d.callout("药物 结合位点", "说明", box, at=(250, 200), font_size=12)


# --- drawing: stdout stays parseable; key errors say what to pass -----------------------------------------


# --- charts: p values ------------------------------------------------------------------------------------


def test_p_values_threshold_strings_and_float_warning():
    svg = make_dumbbell(
        [
            {"label": "A", "before": 1, "after": 2, "p": "<.05"},
            {"label": "B", "before": 1, "after": 3, "p": "n.s."},
            {"label": "C", "before": 2, "after": 3},
        ]
    )
    assert "P&lt;0.05" in svg and "P=0.05" not in svg
    bar = make_grouped_bar(
        categories=["A", "B"],
        series=[{"name": "x", "values": [1, 2]}, {"name": "y", "values": [2, 3]}],
        pairwise_p=[(0, 0, 1, "<.05")],
    )
    assert "P &lt; 0.05" in bar
    rows = [{"label": n, "before": 1, "after": 2, "p": 0.05} for n in "ABC"]
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        chart_slide("dumbbell", 40, 100, 600, 300, rows=rows)
    assert any("p='<0.05'" in str(w.message) for w in caught)


# --- charts: gantt ---------------------------------------------------------------------------------------

TRIALS = [
    ("Resmetirom MAESTRO-NASH", "2019-03-01", "2023-12-31", "Phase 3"),
    ("Semaglutide ESSENCE", "2021-04-01", "2024-11-30", "Phase 3"),
    ("Efruxifermin SYNCHRONY", "2023-12-01", "2027-06-30", "Phase 3"),
]
MILESTONES = [
    ("2024-03-14", "Resmetirom 获批"),
    ("2024-11-01", "Semaglutide 3期读出"),
    ("2025-08-15", "Semaglutide 获批"),
]


def _boxes(svg, labels):
    out = []
    for m in re.finditer(
        r'<text x="([\d.]+)" y="([\d.]+)" text-anchor="middle"[^>]*font-size="([\d.]+)"[^>]*>([^<]+)</text>', svg
    ):
        x, y, fs, t = float(m[1]), float(m[2]), float(m[3]), m[4]
        if t in labels:
            w = _estimate_label_width_px(t, fs, bold=True)
            out.append((x - w / 2, y - fs, x + w / 2, y))
    return out


@pytest.mark.parametrize("dict_tasks", [False, True])
def test_gantt_milestone_labels_never_overlap_and_years_label_long_spans(dict_tasks):
    tasks = [{"name": t[0], "start": t[1], "end": t[2], "stream": t[3]} for t in TRIALS] if dict_tasks else TRIALS
    svg = make_gantt(tasks, milestones=MILESTONES, today="2025-10-12", width=900, height=420)
    boxes = _boxes(svg, {m[1] for m in MILESTONES} | {"今天", "TODAY"})
    assert len(boxes) >= 3
    for i, a in enumerate(boxes):
        for b in boxes[i + 1 :]:
            assert a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1], (a, b)
    texts = _texts(svg)
    assert sum(bool(re.fullmatch(r"20\d\d", t)) for t in texts) >= 3
    assert not any(re.fullmatch(r"[A-Z][a-z]{2} \d\d", t) for t in texts)


@pytest.mark.parametrize("extra", [[], [("2022-06-01", "NATiV3 入组完成"), ("2026-03-01", "SYNCHRONY 读出")]])
def test_gantt_leaders_cross_no_label_and_markers_differ_from_bars(extra):
    ms = MILESTONES + extra
    svg = make_gantt(TRIALS, milestones=ms, today="2025-10-12", width=900, height=420)
    boxes = _boxes(svg, {m[1] for m in ms})
    leaders = [
        (float(m[1]), float(m[2]), float(m[3]))
        for m in re.finditer(
            r'<line x1="([\d.]+)" y1="([\d.]+)" x2="[\d.]+" y2="([\d.]+)" stroke="[^"]+" stroke-width="0.8"/>', svg
        )
    ]
    for x, y0, y1 in leaders:
        for bx0, by0, bx1, by1 in boxes:
            assert not (bx0 < x < bx1 and y0 < by1 and by0 < y1 and not by1 <= y0 + 4), (
                (x, y0, y1),
                (bx0, by0, bx1, by1),
            )

    marker = _rgb_tuple(re.search(r'<polygon[^>]*fill="([^"]+)"', svg)[1])
    bars = {
        _rgb_tuple(c)
        for c in re.findall(r'<rect x="[\d.]+" y="[\d.]+" width="[\d.]+" height="[\d.]+" fill="([^"]+)"', svg)[1:]
    }
    assert bars and marker not in bars


def test_gantt_reports_today_marker_colour():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        chart_slide("gantt", 40, 100, 880, 380, tasks=TRIALS, milestones=MILESTONES, today="2025-10-12")
    assert any("今天线 =" in str(w.message) for w in caught)


# --- charts: line / scatter ------------------------------------------------------------------------------


def test_scatter_projection_unnamed_curves_category_lines_and_reference_band():
    pts = [{"x": 2020, "y": 0.7}, {"x": 2024, "y": 1.6}, {"x": 2030, "y": 5.4}]
    svg = make_scatter([{"name": "装机", "points": pts, "curve": pts}], projected_from=2024)
    assert svg.count('data-role="projection"') == 1 and 'data-role="curve"' in svg
    pts = [{"x": 2020, "y": 0.7}, {"x": 2024, "y": 1.6}, {"x": 2030, "y": 0}]
    frag = chart_slide("scatter", 40, 100, 600, 360, points=[{"name": "", "points": pts, "curve": pts}])
    labels = re.findall(r"<p[^>]*>(?:<span[^>]*>)?([^<]{1,14})<", frag)
    assert labels.count("0") <= 1  # the y-axis tick only, no stray "0" end label
    cats = ["293 K", "77 K", "4.2 K"]
    series = [
        {
            "name": n,
            "points": [{"x": c, "y": v} for c, v in zip(cats, vals)],
            "curve": [{"x": c, "y": v} for c, v in zip(cats, vals)],
        }
        for n, vals in (("NbTi", (0, 0.1, 9.5)), ("Nb3Sn", (0, 0.2, 23)))
    ]
    svg = make_scatter(series, width=700, height=420)
    xs = {}
    for m in re.finditer(r'<circle cx="([\d.]+)"[^>]*data-series="([^"]+)"', svg):
        xs.setdefault(m[2], []).append(round(float(m[1]), 1))
    assert len(xs) == 2 and xs["NbTi"] == xs["Nb3Sn"]
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        chart_slide("scatter", 40, 100, 600, 360, points=series)
    assert any("物理量用数值 x" in str(w.message) for w in caught)
    svg = make_scatter(
        [{"x": 1000, "y": 70}, {"x": 1500, "y": 85}],
        frontier=True,
        reference_band={"points": [(500, 60), (1500, 15), (1800, 3), (600, 30)], "label": "传统合金"},
    )
    assert 'data-role="reference-band"' in svg and "传统合金" in svg


# --- charts: stress-strain ---------------------------------------------------------------------------------


def test_stress_strain_overlays_curves_with_hardening_panel_from_sparse_points():
    curves = {
        "293 K": [(0, 0), (0.3, 320), (5, 520), (20, 760), (40, 950), (70, 1060)],
        "77 K": [(0, 0), (0.4, 520), (5, 800), (20, 1150), (60, 1520), (85, 1560)],
    }
    svg = make_stress_strain(curves=curves, hardening=True, strain_unit="%", width=900, height=560)
    assert svg.count('data-role="curve"') == 2 and svg.count('data-role="hardening-rate"') == 2
    assert "293 K" in svg and "dσ/dε" in svg
    single = make_stress_strain(curves["77 K"], multi_mode="with_tangent_modulus", strain_unit="%", height=900)
    assert "Tangent modulus" in single or "dσ/dε" in single


# --- relation palettes / lint / deck overview ---------------------------------------------------------------


def test_relation_accepts_any_chart_palette_name():
    frag = make_relation_atomized(
        "mp_mindmap",
        slide_x0=40,
        slide_y0=90,
        slide_w=880,
        slide_h=380,
        strict_no_embed=True,
        palette="dusk_plum_rose",
        allow_sample_data=True,
    )
    assert "rgb(147,130,163)" in frag

    assert _CFG["drop_bg"] is False  # relation settings must not leak into later chart_slide calls


# --- lint / check output that agents misread (round 2) --------------------------------------------------------


def test_chart_text_over_page_title_is_called_a_real_defect_not_waivable():
    xml = (
        '<slide xmlns="https://www.larkoffice.com/sml/2.0"><data>'
        '<shape type="text" topLeftX="40" topLeftY="30" width="600" height="40"><content><p>界面电阻对比</p></content></shape>'
        '<shape type="text" topLeftX="60.5" topLeftY="50.5" width="40.2" height="14"><content><p>Ω·cm²</p></content></shape>'
        "</data></slide>"
    )
    err = {
        "code": "bbox_overlap",
        "elements": ["slide[1]/data/shape[1]", "slide[1]/data/shape[2]"],
        "measurement": {"intersection_width": 40, "intersection_height": 14},
    }
    item = pub._describe(xml, err, {1}, {1: "fragment[0]"})
    assert "不是误报" in item["fix"] and "Ω·cm²" in item["fix"] and "界面电阻对比" in item["fix"]


def test_check_output_is_grouped_blocking_first_with_text_bbox_and_new_position(capsys):
    d = Drawing(600, 300)
    for i in range(4):
        d.text_at((100 + i * 4, 100), f"标签{i}", font_size=16, key=f"t{i}")
    problems = d.check()
    assert isinstance(problems, list) and all(p["severity"] == "blocking" for p in problems)
    text = str(problems)
    assert text.splitlines()[0].startswith("[drawing check]")
    assert "+" in text and "more text_overlap" in text  # capped per kind
    assert "bbox=" in text and "move key 't" in text and "at=(" in text

    hints = _format_layout_hints([f"w{i}" for i in range(7)], 400).splitlines()
    assert len(hints) == 5 and hints[-1].startswith("  +4 more")


def test_native_table_warns_when_rows_overflow_the_box():
    rows = [["方法", "说明"]] + [[f"方法{i}", "较长的说明文字，需要换行显示" * 2] for i in range(8)]
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        xml = native_table(rows, (40, 100, 400, 120))
    assert any("box height" in str(c.message) for c in caught)
    assert float(re.search(r'<table[^>]*height="([\d.]+)"', xml).group(1)) > 120
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        native_table([["a", "b"], ["1", "2"]], (40, 100, 400, 200))
    assert not any("box height" in str(c.message) for c in caught)
