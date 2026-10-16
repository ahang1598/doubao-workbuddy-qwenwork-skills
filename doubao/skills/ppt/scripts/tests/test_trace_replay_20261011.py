"""Calls that failed in real 60-minute agent traces (2026-10-11) and must now just work or explain the fix.

Each case is the model's own code shape, copied from the trace, not the documented API.
"""

import json
import re
import warnings

import pytest

from scripts.gen_svg_charts import chart_slide, make_grouped_bar, make_violin
from scripts.svg_lib.svg_drawing import Drawing, lattice
import inspect
import scripts.gen_svg_charts as g
import scripts.svg_lib.atomize_svg_to_slide._publish as pub
import sys
import warnings as w
import xml_lint
from pathlib import Path
from scripts.gen_svg_charts import _bar_upgrade, _is_ratio, chart_help
from scripts.svg_lib import svg_drawing as sd
from scripts.svg_lib.atomize_svg_to_slide import native_bullets, native_table, page_frame
from scripts.svg_lib.atomize_svg_to_slide._compose import compose_slide
from scripts.svg_lib.atomize_svg_to_slide._publish import (
    _HAND_DIAGRAM_NOTE,
    _children,
    _describe,
    _prepare,
    _saved_path,
    _summarize,
    publish_slide,
)
from scripts.svg_lib.drawing_examples import compare_panels, membrane_transport, overview_zoom
from scripts.svg_lib.drawing_lib._help import _DRAWING_APIS
from scripts.svg_lib.svg_drawing import cell, drawing_help, receptor

warnings.filterwarnings("ignore")

CATS = ["WT 野生型", "ΔacrB", "ΔtetA", "ΔacrBΔtetA 双敲"]


# --- chart library: matplotlib habits ---------------------------------------------------------------


def test_matplotlib_habits_tuple_unpack_axis_kwargs_and_distribution_dicts():  # 46× "too many values to unpack (expected 2)"
    svg, _ = make_grouped_bar(
        categories=CATS, series=[{"name": "MIC", "values": [32, 2, 2, 0.25]}], width=900, height=420
    )
    assert svg.startswith("<svg")
    frag = chart_slide(
        "grouped_bar",
        40,
        110,
        560,
        330,
        categories=CATS,
        series=[{"name": "MIC", "values": [32, 2, 2, 1]}],
        xlabel="菌株",
        ylabel="MIC (µg/mL)",
        y_min=0,
        y_max=40,
        colors=["#5B1061"],
        annotate=True,
    )
    assert "MIC (µg/mL)" in frag
    rows = [
        {"label": n, "estimate": e, "ci_lo": e * 0.7, "ci_hi": e * 1.4} for n, e in (("a", 0.8), ("b", 1.3), ("c", 0.6))
    ]
    assert "<shape" in chart_slide("forest", 40, 110, 700, 300, rows=rows, xlabel="HR", reference=1, xscale="log")
    groups = [{"name": n, "values": v} for n, v in (("对照", [1, 2, 3, 4, 5, 6]), ("处理", [2, 3, 5, 6, 7, 8]))]
    assert make_violin(groups=groups, ylim=(0, 9), ylabel="y").startswith("<svg")


@pytest.mark.parametrize(
    "series",
    [
        [{"name": "MIC", "values": [32, 2, 2, 0.25]}],  # bare numbers
        [{"name": "MIC", "data": [32, 2, 2, 0.25]}],  # KeyError: 'values'
        [{"name": "MIC", "values": [[{"value": v}] for v in (32, 2, 2, 0.25)]}],  # nested one-item lists
    ],
)
def test_grouped_bar_cell_shapes(series):
    assert "<shape" in chart_slide("grouped_bar", 40, 110, 560, 330, categories=CATS, series=series)


def test_chart_slide_box_tuple_wrong_argument_and_misplaced_imports():
    from scripts.svg_lib.atomize_svg_to_slide import chart_slide as a  # trace: cannot import name 'chart_slide'
    from scripts.gen_svg_charts import publish_slide as b

    kw = dict(categories=["a", "b", "c"], series=[{"name": "x", "values": [1, 2, 3]}])
    assert "<shape" in chart_slide("grouped_bar", (40, 100, 600, 300), **kw)
    with pytest.raises(TypeError, match="chart name, not an SVG"):
        chart_slide(make_grouped_bar(**kw), (40, 100, 600, 300))
    with pytest.raises(ValueError, match="did you mean 'grouped_bar'"):
        chart_slide("groupedbar", 40, 100, 600, 300, **kw)
    assert "<shape" in chart_slide("grouped_bars", 40, 100, 600, 300, **kw)  # alias
    assert callable(a) and callable(b)
    with pytest.raises(ImportError, match="Drawing method"):
        from scripts.svg_lib.svg_drawing import svg_at  # noqa: F401


# --- imports from the wrong module -------------------------------------------------------------------


# --- drawing library: svgwrite habits (rule A: center=/at= is the centre, insert= is svgwrite's) ----------


def test_svgwrite_methods_insert_keyword_and_text_baseline():
    d = Drawing(600, 300)
    a = d.rect(insert=(40, 60), size=(200, 80), rx=8, fill="#F3EEF8", stroke="#5B1061")
    b = d.rect(center=(450, 100), size=(120, 60), fill="#EEEEEE", stroke="#333333")
    c = d.circle(center=(140, 220), r=30, fill="#DDDDDD")
    d.ellipse(center=(450, 220), r=(60, 25), fill="#DDDDDD")
    d.text("基线", insert=(300, 40), font_size=20)
    d.polyline([(20, 280), (80, 250)], stroke="#5B1061")  # two points: polygon() used to raise
    d.polygon([(500, 280), (540, 250), (580, 280)], fill="#CCCCCC")
    d.path(d="M 300 150 L 340 150", stroke="#000000")
    d.arrow(a, b)
    d.arrow(c, b)
    assert d.resolve(a.anchor("top_left")) == (40.0, 60.0)
    assert d.resolve(b.anchor("center")) == (450.0, 100.0)
    assert d.check() == []
    assert d.tostring().startswith("<svg")
    d = Drawing(400, 200)
    r = d.rect_at(insert=(10, 20), size=(40, 30))
    assert d.resolve(r.anchor("top_left")) == (10.0, 20.0)
    box = d.box_at(insert=(100, 20), content="A", font_size=14, stroke="#333333")
    assert d.resolve(box.anchor("top_left")) == (100.0, 20.0)
    t = d.text_at(insert=(200, 50), content="hi", font_size=12)
    assert t is not None
    with pytest.raises(TypeError, match="one of at= / center="):
        d.rect_at(at=(1, 1), insert=(1, 1), size=(1, 1))
    d = Drawing(400, 200)
    for anchor in ("start", "middle", "end"):
        d.text("Hg", insert=(200, 100), font_size=20, text_anchor=anchor)
    nodes = list(d.nodes.values())
    xs = [d.resolve(n.anchor("left"))[0] for n in nodes]
    assert xs[0] == pytest.approx(200, abs=0.5) and xs[1] < 200 < xs[0] + 1 and xs[2] < xs[1]
    assert all(d.resolve(n.anchor("top"))[1] == pytest.approx(80, abs=0.5) for n in nodes)  # baseline 100 − font_size


def test_export_and_lookup_aliases(tmp_path):
    d = Drawing(200, 100)
    d.circle(center=(50, 50), r=10, key="c")
    assert d.get("c") is d["c"]
    assert d.saveas(tmp_path / "a.svg").exists()
    assert d.to_image(tmp_path / "a.png").exists()  # trace: no attribute 'to_image'


def test_lattice_integer_shorthand_and_instance_help():  # trace: 'int' object is not iterable
    d = Drawing(300, 200)
    d.place(lattice(3, pitch=20, bonds=True), at=(80, 100))
    d.place(lattice((2, 5), pitch=16), at=(220, 100))
    assert d.check() == []
    d = Drawing(400, 200)
    assert d.drawing_help("finish") == drawing_help("finish")
    assert d.drawing_help() == drawing_help()


# --- grouped_bar data that is really a paired / ranked comparison is drawn with the academic chart ----


def _drawn(kwargs):
    with w.catch_warnings(record=True) as caught:
        w.simplefilter("always")
        frag = chart_slide("grouped_bar", 40, 110, 560, 330, **kwargs)
    return frag, " ".join(str(c.message) for c in caught)


def test_grouped_bar_upgrades_to_dumbbell_dot_plot_or_log_axis():  # trace 410AF0 p11: 未改性 / 改性后
    _, msg = _drawn(
        dict(
            categories=["Mg/Ta", "Ta+Zr-Y", "Al(20℃)", "Al(60℃)"],
            series=[["未改性", [57.3, 67.4, 73.59, 87.32]], ["改性后", [90.5, 88.6, 96.15, 94.38]]],
        )
    )
    assert "drew 'dumbbell'" in msg
    _, msg = _drawn(
        dict(
            categories=["GCN", "GIN", "GIN-VN", "Graphormer"],
            series=[["Test ROC-AUC", [[{"value": v} for v in (0.7606, 0.8040, 0.8051, 0.8475)]]]],
        )
    )
    assert "drew 'coef_plot'" in msg
    frag, msg = _drawn(dict(categories=CATS, series=[{"name": "MIC", "values": [32, 2, 2, 0.25]}]))
    assert "logarithmic" in msg and "对数轴" in frag
    _, msg = _drawn(dict(categories=["A", "B", "C"], series=[{"name": "x", "values": [10, 25, 40]}]))
    assert "drew" not in msg and "logarithmic" not in msg
    _, msg = _drawn(dict(categories=["A", "B", "C"], series=[["前", [1, 2, 3]], ["后", [2, 3, 4]]], upgrade=False))
    assert "drew" not in msg


# --- detail review: structure only, no vocabulary --------------------------------------------------------


def _boxy_mechanism():  # trace D20A12 p05, reduced: boxes, sketched membrane, ⊣ glyphs
    d = Drawing(864, 360)
    d.line((36, 84), (828, 84))
    d.line((36, 102), (828, 102))
    d.rect_at((170, 93), 42, 48, fill="#7A202C")
    d.text_at((170, 93), "Xc⁻", font_size=13)
    nodes = {
        t: d.box_at(at, t, font_size=12, stroke="#999999")
        for t, at in (
            ("Cys", (96, 156)),
            ("GSH", (394, 206)),
            ("GPX4", (602, 190)),
            ("PLOOH", (508, 134)),
            ("PLOH", (696, 134)),
        )
    }
    d.arrow((158, 120), (112, 142))
    d.arrow(nodes["GSH"], nodes["GPX4"])
    d.arrow(nodes["PLOOH"], nodes["GPX4"])
    d.arrow(nodes["GPX4"], nodes["PLOH"])
    d.text_at((200, 92), "⊣", font_size=14)
    return d


def test_review_flags_plain_subjects_sketches_and_icon_level_svg_at():
    kinds = {r["kind"] for r in _boxy_mechanism().review()}
    assert {"plain_subject", "sketched_layer", "glyph_arrow"} <= kinds
    first = _boxy_mechanism().review()[0]
    assert first["kind"] == "plain_subject" and "GPX4" in first["hint"] and "保留方框" in first["hint"]
    for module in (compare_panels, overview_zoom, membrane_transport):
        assert module.build().review() == []
    notes = _icon_mechanism().review()
    flagged = {k for r in notes if r["kind"] == "plain_subject" for k in r["keys"]}
    assert {"sun", "cloud", "particle"} & flagged and any(r["kind"] == "mostly_plain" for r in notes)
    assert any("图标级 svg_at" in r["hint"] for r in notes)


# --- upgrade rules: numeric categories, ratios, mixed endpoints; the opt-out is never advertised -------------


def test_upgrade_warnings_teach_enrichment_not_opt_out():
    _, msg = _drawn(
        dict(
            categories=["Mg/Ta", "Ta+Zr-Y", "Al(20℃)"],
            series=[["未改性", [57.3, 67.4, 73.6]], ["改性后", [90.5, 88.6, 96.2]]],
        )
    )
    assert "upgrade=False" not in msg and "after_lo" in msg and "p and n" in msg
    _, msg = _drawn(
        dict(categories=["GCN", "GIN", "GIN-VN", "Graphormer"], series=[["AUC", [0.76, 0.80, 0.805, 0.85]]])
    )
    assert "upgrade=False" not in msg and "lo/hi" in msg
    _, msg = _drawn(dict(categories=CATS, series=[{"name": "MIC", "values": [32, 2, 2, 0.25]}]))
    assert "upgrade=False" not in msg

    assert "upgrade=False" not in chart_help() + chart_help("grouped_bar", full=True) + (chart_slide.__doc__ or "")


@pytest.mark.parametrize(
    "cats, x_title, log_x",
    [
        (["ε=0.5", "ε=1", "ε=4", "ε=16"], "ε", True),  # privacy–utility, spans 32x
        (["303 K", "323 K", "343 K"], None, False),
        (["10 epochs", "20 epochs", "40 epochs"], "epochs", False),
        (["1", "2", "3", "4"], None, False),
    ],
)
def test_numeric_categories_become_scatter_curves(cats, x_title, log_x):
    series = [
        {"name": "DP-SGD", "values": [60 + i for i in range(len(cats))]},
        {"name": "Ours", "values": [62 + 2 * i for i in range(len(cats))]},
    ]

    slug, kw, _ = _bar_upgrade(dict(categories=cats, series=series, y_title="Accuracy (%)"))
    assert slug == "scatter" and len(kw["points"]) == 2 and all(s["curve"] for s in kw["points"])
    assert (kw["x_transform"] == "log10") is log_x
    if x_title:
        assert kw["x_title"] == x_title
    frag, msg = _drawn(dict(categories=cats, series=series, y_title="Accuracy (%)"))
    assert "drew 'scatter'" in msg and "categories are numeric" in msg and "<shape" in frag


def test_index_names_and_explicit_axis_stay_categorical():
    for cats in (["Group 1", "Group 2", "Group 3"], ["NCM523", "NCM622", "NCM811"], ["Cu(100)", "Cu(110)", "Cu(111)"]):
        better = _bar_upgrade(dict(categories=cats, series=[{"name": "y", "values": [10, 25, 40]}]))
        assert better is None or better[0] != "scatter"
    assert (
        _bar_upgrade(
            dict(categories=["1", "2", "3"], series=[{"name": "y", "values": [10, 25, 40]}], y_min=0, y_max=50)
        )
        is None
    )


def test_ratio_series_becomes_dot_plot_against_one():
    assert _is_ratio(["Fold change"]) and _is_ratio(["BAF (L/kg)"]) and _is_ratio(["HR"]) and _is_ratio(["富集倍数"])
    assert not _is_ratio(["ORR (%)"]) and not _is_ratio(["Order parameter"]) and not _is_ratio(["Horizon"])
    assert not _is_ratio(["倍率性能"]) and not _is_ratio(["Accuracy"])
    slug, kw, reason = _bar_upgrade(
        dict(categories=["Cd", "Pb", "Zn", "Cu"], series=[{"name": "TMF", "values": [1.8, 0.6, 1.1, 2.4]}])
    )
    assert slug == "coef_plot" and kw["reference"] == 1 and "ratios" in reason
    frag, msg = _drawn(
        dict(categories=["Cd", "Pb", "Zn", "Cu"], series=[{"name": "TMF", "values": [1.8, 0.6, 1.1, 2.4]}])
    )
    assert "drew 'coef_plot'" in msg and "<shape" in frag
    # Numeric x + ratio: the curve gets the line at 1.
    _, kw, _ = _bar_upgrade(
        dict(categories=["1 d", "7 d", "28 d"], series=[{"name": "BCF", "values": [0.8, 1.6, 2.2]}])
    )
    assert any(r["value"] == 1 for r in kw["reference_lines"])


def test_mixed_endpoints_warn():
    _, msg = _drawn(
        dict(
            categories=["中位 OS (月)", "ORR (%)", "中位 PFS (月)"],
            series=[{"name": "本研究", "values": [18.2, 45, 7.9]}],
        )
    )
    assert "categories mix different endpoints" in msg and "benchmark" in msg
    _, msg = _drawn(
        dict(categories=["容量 (mAh/g)", "首效 (%)", "倍率 (C)"], series=[{"name": "x", "values": [180, 88, 5]}])
    )
    assert "mix different endpoints" in msg
    _, msg = _drawn(dict(categories=["A", "B", "C"], series=[{"name": "x", "values": [10, 25, 40]}]))
    assert "endpoints" not in msg


def _supports(slug, *fields):
    src = inspect.getsource(inspect.getmodule(inspect.unwrap(getattr(g, "make_" + slug))))
    return all(f in src for f in fields)


@pytest.mark.parametrize(
    "slug, fields", [("dumbbell", ("after_lo",)), ("forest", ("favours",)), ("coef_plot", ("benchmark",))]
)
def test_summary_snippets_render(slug, fields):
    if not _supports(slug, *fields):
        pytest.skip(f"{slug} statistical fields not landed yet")
    import re

    code = re.search(r"reported summary values.*?```py\n(.*?)\n```", chart_help(slug), re.S).group(1)
    ns = {"chart_slide": chart_slide}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        exec("frag = " + code, ns)
    assert "<shape" in ns["frag"]


def _icon_mechanism():  # icon-level svg_at: sun = circle + 8 rays, cloud path, hexagon, "<>"
    d = Drawing(900, 360)
    rays = "".join(
        f'<line x1="0" y1="-30" x2="0" y2="-42" stroke="#E0A030" stroke-width="3" transform="rotate({a})"/>'
        for a in range(0, 360, 45)
    )
    sun = d.svg_at((100, 120), '<circle r="24" fill="#F5C242" stroke="#E0A030"/>' + rays, key="sun")
    cloud = d.svg_at(
        (330, 110),
        '<path d="M-50 20 C-70 20 -70 -10 -45 -12 C-40 -40 0 -40 5 -18 C20 -35 55 -25 50 0 '
        'C70 5 65 20 50 20 Z" fill="#E8EEF5" stroke="#7A8BA0"/>',
        key="cloud",
    )
    hexa = d.svg_at(
        (560, 220),
        '<polygon points="30,0 15,26 -15,26 -30,0 -15,-26 15,-26" fill="#B9A6DA" stroke="#5B1061"/>',
        key="particle",
    )
    code = d.svg_at(
        (780, 120),
        '<path d="M-10 -14 L-24 0 L-10 14 M10 -14 L24 0 L10 14" fill="none" stroke="#333" stroke-width="3"/>',
        key="model",
    )
    soil = d.box_at((330, 300), "土壤", font_size=14, stroke="#999")
    for a, b in ((sun, cloud), (cloud, hexa), (hexa, code), (sun, hexa), (cloud, soil)):
        d.arrow(a, b)
    return d


def test_review_flags_isolated_subjects_and_apart_receptor_pairs():
    d = Drawing(900, 400)
    for k, x in (("a", 150), ("b", 450), ("c", 750)):
        d.place(cell(70), at=(x, 200), key=k)
    lonely = [r for r in d.review() if r["kind"] == "isolated_subject"]
    assert lonely and set(lonely[0]["keys"]) == {"a", "b", "c"} and "没有任何关系" in lonely[0]["hint"]

    d = Drawing(900, 400)
    t = d.place(cell(70), at=(200, 200), key="tcell")
    tu = d.place(cell(70), at=(650, 200), key="tumor")
    pd1 = d.mount(receptor(), on=t.contour_at(0.0, normal="outward"), inset=3, key="pd1")
    pdl1 = d.mount(receptor(), on=tu.contour_at(0.5, normal="outward"), inset=3, key="pdl1")
    d.line(pd1, pdl1, dashed=True)
    apart = [r for r in d.review() if r["kind"] == "apart_binding"]
    assert apart and "cell_interface" in apart[0]["hint"]
    assert not any(r["kind"] == "isolated_subject" for r in d.review())  # connected by the line


def test_check_flags_invisible_targets_heads_on_edges_and_hand_lines_through_text():
    d = Drawing(600, 300)
    src = d.box_at((80, 150), "沉积物", font_size=14, stroke="#333")
    helper = d.svg_at((400, 150), '<circle r="3" fill="none" stroke="none"/>', key="hp")
    d.arrow(src, helper, key="a1")
    d.rect_at((450, 220), 200, 60, fill="#EEE", stroke="#555", key="sed")
    d.arrow((300, 120), (450, 190), key="a2")  # tip lands on sed's top edge
    d.text_at((250, 260), "标签文字", font_size=16, key="lab")
    d.path("M 150 260 L 350 262", stroke="#000", fill="none", key="hand")
    found = {p["kind"]: p for p in d.check()}
    assert (
        found["invisible_endpoint"]["keys"] == ["a1", "hp"] and "contour_toward" in found["invisible_endpoint"]["hint"]
    )
    assert found["head_on_edge"]["keys"] == ["a2", "sed"] and "(450, 190)" in found["head_on_edge"]["hint"]
    assert found["line_through_text"]["keys"] == ["hand", "lab"]


def test_check_is_quiet_on_templates_and_every_documented_example(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for module in (compare_panels, overview_zoom, membrane_transport):
        assert module.build().check() == []
    ran = 0
    for name, doc in _DRAWING_APIS.items():
        d = sd.Drawing(960, 540)
        ns = dict(vars(sd), d=d, drawing=d)
        try:
            exec(doc.example, ns)
        except Exception:  # noqa: BLE001 — fragments that need outer variables
            continue
        ran += 1
        assert d.check() == [], name
    assert ran >= 40


def test_to_slide_marks_mostly_plain_review_as_must_fix(capsys):
    _icon_mechanism().to_slide(x=40, y=96, width=880, summary=False)
    out = capsys.readouterr().err
    assert "[drawing 细节审查·需修改]" in out and "写入前先把主体换成部件或带结构的 svg_at" in out


# --- publish_slide: an unwrapped native text box measured as one line ---------------------------------------


def test_publish_names_unwrapped_text_not_the_chart():
    page = (
        '<slide xmlns="https://www.larkoffice.com/sml/2.0"><data>'
        '<shape type="text" id="note" topLeftX="40" topLeftY="300" width="200" height="24"><content fontSize="16" wrap="false">'
        "<p>菌株对四环素的最低抑菌浓度随外排泵敲除显著下降，双敲株最敏感</p></content></shape></data></slide>"
    )
    frag = chart_slide(
        "grouped_bar", 260, 110, 560, 330, categories=["a", "b", "c"], series=[{"name": "x", "values": [1, 2, 3]}]
    )
    base, _ = _prepare(page)
    xml = compose_slide(base, frag)
    origins = {i: "fragment[0]" for i in range(len(_children(base)), len(_children(xml)))}
    err = {
        "code": "bbox_overlap",
        "related_objects": [{"xml_path": "slide[1]/data/shape[1]"}, {"xml_path": "slide[1]/data/embed[1]"}],
    }
    d = _describe(xml, err, set(origins), origins)
    assert "文字框 #note" in d["fix"] and "未开启换行" in d["fix"] and "不是图表/示意图的问题" in d["fix"]
    assert "嵌入 SVG" in d["fix"] and "未开启换行" in _summarize([d])[0]
    wrapped = _describe(xml.replace('wrap="false"', 'wrap="true"'), err, set(origins), origins)
    assert "未开启换行" not in wrapped["fix"] and "页面手写文字框" in wrapped["fix"]


# --- paper-mark advisories: one short line naming what the source could add (never an error) ----------


def _advice(slug, **kwargs):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        frag = chart_slide(slug, 40, 110, 700, 330, **kwargs)
    return frag, [str(c.message) for c in caught if "scale (vector" not in str(c.message)]


def _f(label, e, **extra):
    return dict(label=label, estimate=e, ci_lo=e * 0.7, ci_hi=e * 1.4, **extra)


@pytest.mark.parametrize(
    "slug, kwargs, needle",
    [
        (
            "forest",
            dict(rows=[_f("Study A", 0.5), _f("Study B", 0.8), _f("合并效应", 0.7)], x_title="HR"),
            "is_overall",
        ),
        ("forest", dict(rows=[_f("A", 0.5), _f("B", 0.8), _f("C", 0.7)], x_title="HR"), "n/events/p"),
        ("dumbbell", dict(rows=[{"label": c, "before": 1, "after": 2} for c in "abc"]), "after_lo"),
        ("coef_plot", dict(rows=[{"label": c, "estimate": v} for c, v in zip("abc", (1, 2, 3))]), "只有点估计"),
        ("scatter", dict(points=[{"name": "a", "points": [{"x": i, "y": i} for i in range(3)]}]), "curve"),
        (
            "grouped_bar",
            dict(categories=["A", "B", "C"], series=[{"name": "x", "values": [10, 25, 40]}]),
            "reference_lines",
        ),
    ],
)
def test_missing_paper_marks_are_named(slug, kwargs, needle):
    frag, msgs = _advice(slug, **kwargs)
    assert "<shape" in frag
    hits = [m for m in msgs if needle in m]
    assert len(hits) == 1 and len(hits[0]) <= 110, msgs
    if needle == "n/events/p":
        assert "is_overall" not in hits[0]


def test_paper_mark_advice_quiet_when_marks_present():
    for slug in ("forest", "dumbbell", "coef_plot", "spectrum"):
        code = re.search(r"reported summary values.*?```py\n(.*?)\n```", chart_help(slug), re.S).group(1)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            exec(code, {"chart_slide": chart_slide})
        assert not caught, (slug, [str(c.message) for c in caught])
    rows = [{"label": c, "before": 1, "after": 2, "p": 0.004} for c in "abc"]  # 0.01 exactly → threshold-p warning
    assert not _advice("dumbbell", rows=rows)[1]
    pts = [{"name": "a", "points": [{"x": i, "y": i} for i in range(3)], "curve": [{"x": i, "y": i} for i in range(3)]}]
    assert not any("curve" in m for m in _advice("scatter", points=pts)[1])
    _, msgs = _advice(
        "grouped_bar",
        categories=["A", "B", "C"],
        series=[{"name": "x", "values": [10, 25, 40]}],
        reference_lines=[{"value": 20, "label": "目标"}],
    )
    assert not any("单系列" in m for m in msgs)


def test_forest_mixed_measures_and_auto_log_axis():
    rows = [_f("OS HR", 0.5, n=10), _f("ORR OR", 8, n=10), _f("AE RR", 0.7, n=10)]
    frag, msgs = _advice("forest", rows=rows)
    assert any("混用效应量 HR/OR/RR" in m for m in msgs)
    assert any("log_x=True" in m for m in msgs) and "<shape" in frag
    _, msgs = _advice("forest", rows=rows, log_x=False)
    assert not any("对数轴" in m for m in msgs)
    _, msgs = _advice("forest", rows=[_f("a", 0.6, n=1), _f("b", 0.9, n=1), _f("c", 1.2, n=1)], x_title="HR (OS)")
    assert not any("混用" in m or "对数轴" in m for m in msgs)


# --- 2026-10-11 later traces: drawing help on the instance, ports, emitted text extents, stdout check ---------


@pytest.mark.parametrize(
    "svg",
    [
        '<ellipse rx="60" ry="40" fill="#EEE" stroke="#333"/><circle r="8" fill="#999"/>',
        '<g fill="#EEE" stroke="#333"><ellipse rx="60" ry="40"/><circle r="8"/></g>',  # outline inside a <g>
        '<circle r="6" fill="#999"/><ellipse rx="60" ry="40" fill="none" stroke="#333"/>',  # small detail drawn first
        '<line x1="-60" y1="0" x2="60" y2="0" stroke="#333"/><ellipse rx="60" ry="40" fill="#EEE" stroke="#333"/>',
    ],
)
def test_arrows_to_svg_at_honour_ports_and_stop_on_outline(svg):
    d = Drawing(600, 300)
    src = d.box_at((80, 150), "源", stroke="#333")
    n = d.svg_at((400, 150), svg, ports={"left": (-60, 20), "in": (-50, -20)})
    assert d.resolve(d.arrow(src, n.port("left")).end) == pytest.approx((340, 170))
    assert d.resolve(d.arrow(src, n.port("in")).end) == pytest.approx((350, 130))
    assert d.resolve(d.arrow(src, n.port("in"), route="orthogonal").end) == pytest.approx((350, 130))
    assert d.resolve(d.arrow(src, n).end) == pytest.approx((340, 150), abs=0.5)  # ellipse rim, not the box or centre


def test_check_uses_emitted_text_extent_and_text_inside_parts():  # trace: check() passed, arrow crossed the label on the page
    d = Drawing(1200, 600)
    up = d.box_at((530, 100), "上游", stroke="#333")
    down = d.box_at((530, 500), "下游", stroke="#333")
    mid = d.box_at((600, 300), "中间标签文字", font_size=12, key="mid")
    d.arrow(up, down, key="l")
    # Drawn at 12px the label sits right of x=552; on a 400px-wide slide it is clamped to 10pt and widens to x≈502.
    assert mid.bounds.x > 540 and d.check() == []
    assert [(p["kind"], p["keys"]) for p in d.check(width=400)] == [("line_through_text", ["l", "mid"])]
    d = Drawing(800, 400)
    a = d.box_at((80, 200), "A", stroke="#333")
    b = d.box_at((720, 200), "B", stroke="#333")
    d.svg_at(
        (400, 200),
        '<rect x="-80" y="-60" width="160" height="120" fill="#EEE" stroke="#333"/>'
        '<circle cx="0" cy="40" r="8" fill="#999"/>'
        '<text x="0" y="5" font-size="14" text-anchor="middle">内部标签</text>',
        key="host",
    )
    d.arrow(a, b, key="ab")
    assert ("line_through_text", ["ab", "host"]) in [(p["kind"], p["keys"]) for p in d.check()]


def test_to_slide_prints_check_problems_on_stderr(capsys):
    d = Drawing(1200, 600)
    up = d.box_at((530, 100), "上游", stroke="#333")
    down = d.box_at((530, 500), "下游", stroke="#333")
    d.box_at((600, 300), "中间标签文字", font_size=12, key="mid")
    d.arrow(up, down, key="l")
    d.to_slide(x=0, y=0, width=400, summary=False)
    captured = capsys.readouterr()
    out = captured.err
    assert "[drawing check]" not in captured.out  # stdout stays parseable for the caller's own prints
    assert "[drawing check] 1 处问题" in out and "line_through_text l/mid" in out


# --- publish_slide: pasted fragments, hand-pieced diagrams, the real screenshot path ------------------------

_TITLE = '<shape type="text" topLeftX="40" topLeftY="30" width="400" height="40"><content><p>标题</p></content></shape>'


def test_pasted_fragments_and_hand_pieced_diagrams():
    frag = chart_slide(
        "grouped_bar", 40, 110, 560, 330, categories=["a", "b", "c"], series=[{"name": "x", "values": [1, 2, 3]}]
    )
    d = Drawing(400, 200)
    d.arrow(d.box_at((80, 100), "A", stroke="#333"), d.ellipse_at((300, 100), 40, 30, fill="#EEE"))
    drawn = d.to_slide(x=600, y=110, width=300, summary=False)
    pasted = publish_slide(f"<slide><data>{_TITLE}{frag}{drawn}</data></slide>")
    proper = publish_slide(f"<slide><data>{_TITLE}</data></slide>", frag, drawn)
    assert pasted["page_xml"] == proper["page_xml"]
    assert pasted["summary"] == [
        "page_xml 里拼进了 2 个生成片段，已按片段处理；下次把 to_slide()/chart_slide() 的返回值"
        "作为 publish_slide 的第 2 个参数传入，不要拼进 page_xml"
    ]
    assert proper["summary"] == []
    assert publish_slide(_native_page(8, True))["summary"] == [_HAND_DIAGRAM_NOTE]
    assert publish_slide(_native_page(8, False))["summary"] == []  # cards + plain dividers: an ordinary layout
    assert publish_slide(_native_page(4, True))["summary"] == []


def _native_page(boxes, arrows):
    rects = "".join(
        f'<shape type="rect" topLeftX="{40 + 100 * i}" topLeftY="120" width="80" height="50"/>' for i in range(boxes)
    )
    head = '<endArrow type="arrow"/>' if arrows else ""
    lines = "".join(
        f'<line startX="{120 + 100 * i}" startY="145" endX="{140 + 100 * i}" endY="145">'
        f'<border color="rgb(0,0,0)" width="1"/>{head}</line>'
        for i in range(6)
    )
    return f"<slide><data>{_TITLE}{rects}{lines}</data></slide>"


def test_screenshot_path_is_the_file_actually_saved(tmp_path):
    out = tmp_path / ".lark-slides/screenshots/publish"
    out.mkdir(parents=True)
    (out / "sid-1.jpg").write_bytes(b"x")
    rel = ".lark-slides/screenshots/publish"
    assert _saved_path({"output": f"{rel}/sid-1.png"}, str(tmp_path), rel, "sid-1") == str(
        (out / "sid-1.jpg").resolve()
    )
    assert _saved_path({"output": str(out / "sid-1.jpg")}, str(tmp_path), rel, "sid-1") == str(out / "sid-1.jpg")


def test_waived_findings_force_write_and_screenshot(tmp_path, monkeypatch):
    note = '<shape type="text" id="note" topLeftX="60" topLeftY="40" width="200" height="30"><content><p>注</p></content></shape>'
    page = f"<slide><data>{_TITLE}{note}</data></slide>"
    report = {
        "slides": [
            {
                "errors": [
                    {"code": "bbox_overlap", "elements": ["slide[1]/data/shape[1]", "slide[1]/data/shape[2]"]},
                    {"code": "text_color_contrast", "elements": ["slide[1]/data/shape[2]"]},
                ]
            }
        ]
    }
    calls = []

    def fake_run(args, cwd):
        calls.append(args)
        if args[1] == "+screenshot":
            return {"ok": True, "data": {}}
        if "--no-lint" in args:
            return {"ok": True, "data": {"slide_id": "s1"}}
        return {"ok": False, "error": {"message": json.dumps(report)}}

    monkeypatch.setattr(pub, "_run", fake_run)
    monkeypatch.setattr(pub, "_screenshot", lambda *a, **k: "shot.jpg")
    blocked = pub.publish_slide(page, presentation="d", cwd=str(tmp_path))
    keys = [e["key"] for e in blocked["errors"]]
    assert not blocked["ok"] and keys[1] == "text_color_contrast:note" and "waive=" in blocked["summary"][-1]

    partial = pub.publish_slide(page, presentation="d", cwd=str(tmp_path), waive=keys[:1])
    assert not partial["ok"] and [e["key"] for e in partial["errors"]] == keys[1:]

    forced = pub.publish_slide(page, presentation="d", cwd=str(tmp_path), waive=keys)
    assert forced["ok"] and forced["no_lint"] and forced["waived"] == keys
    assert forced["screenshot"] == "shot.jpg" and "必须 Read" in forced["summary"][0]
    assert sum("--no-lint" in c for c in calls) == 1
    assert "lint_inspect.py" in forced["summary"][1] and "不要回头再改" in forced["summary"][1]
    assert any("text_color_contrast" in line for line in forced["summary"][2:])
    assert not (tmp_path / ".lark-slides/waived-d.json").exists()


# --- 2026-10-12 decks: page_frame / native_bullets replace each deck's home-made deck_parts helpers ---------


def _xml_lint():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

    return xml_lint


def _lint(xml):
    report = _xml_lint().lint_xml(xml)
    return [e["code"] for s in report["slides"] for e in s.get("errors", []) + s.get("warnings", [])]


def test_native_bullets_bold_leads_nested_and_formula():
    xml = native_bullets(
        [
            "机制：PD-1 与 PD-L1 结合后抑制 T 细胞活化" * 3,
            ["子项：硝酸根 $\\mathrm{NO_3^-}$ 被还原"],
            ("疗效", "ORR 40%"),
            "无前导的一句",
        ],
        (40, 100, 420),
        font_size=14,
        lead_color="#5B1061",
    )
    assert xml.count("<li>") == 4 and xml.count('<span bold="true"') == 3 and "疗效：</span>" in xml
    assert 'level="2"' in xml and "<formula><latex><![CDATA[\\mathrm{NO_3^-}]]>" in xml and 'wrap="true"' in xml
    assert float(re.search(r'height="([\d.]+)"', xml).group(1)) > 80  # three wrapped lines + three items
    plain = native_bullets(["$5 和 $10 两档：价格"], (0, 0, 300), bullet=None)
    assert "<ul" not in plain and "<formula" not in plain and "$5 和 $10 两档：" in plain


def test_page_frame_is_lint_clean_and_holds_body():
    body = native_bullets(["要点：说明文字"], (40, 110, 420))
    table = native_table(
        [["Model", "Acc", "Loss"], ["A", "85.3±0.2", "0.31"], ["B", "88.1", "0.29"]],
        (500, 110, 400, 90),
        best=[None, "↑", "↓"],
    )
    xml = page_frame(
        "PD-1 阻断恢复 T 细胞杀伤",
        body,
        table,
        kicker="02 机制",
        source="来源：Smith & Jones, 2024",
        page_no=3,
        note="第一句。\n第二句。",
        background="#FAFAFC",
    )
    assert _lint(xml) == []
    assert "02 机制" in xml and "Smith &amp; Jones" in xml and xml.count("<p>第") == 2 and "<fillColor" in xml
    with pytest.raises(TypeError, match="publish_slide"):
        page_frame("t", "<slide><data/></slide>")


def test_native_table_best_marks_per_column_winner():
    rows = [["Model", "Acc", "Loss"], ["A", "85.3±0.2", "0.31"], ["B", "88.1", "0.29"], ["C", "88.1", "0.40"]]
    cells = lambda xml: [re.findall(r"<td>.*?</td>", tr) for tr in re.findall(r"<tr.*?</tr>", xml)]
    grid = cells(native_table(rows, (0, 0, 300, 100), best=[None, "↑", "↓"]))
    bold = [[('bold="true"' in c) for c in r] for r in grid[1:]]
    assert bold == [[False, False, False], [False, True, True], [False, True, False]]
    by_name = cells(native_table(rows, (0, 0, 300, 100), best={"Loss": "min"}))
    assert [('bold="true"' in r[2]) for r in by_name[1:]] == [False, True, False]


def test_contrast_finding_names_text_colour_background_and_ratio():
    page = (
        '<slide xmlns="https://www.larkoffice.com/sml/2.0"><data>'
        '<shape type="rect" topLeftX="30" topLeftY="90" width="300" height="60"><fill><fillColor color="rgb(200,200,200)"/></fill></shape>'
        '<shape type="text" topLeftX="40" topLeftY="100" width="200" height="30"><content color="rgb(240,240,240)" fontSize="14">'
        "<p>浅灰字</p></content></shape></data></slide>"
    )
    d = _describe(page, {"code": "text_color_contrast", "elements": ["slide[1]/data/shape[2]"]})
    c = d["contrast"]
    assert c["text"] == "浅灰字" and c["text_color"].startswith("rgba(240, 240, 240") and c["ratio"] < 2
    assert c["under_text"][0]["color"] == "rgb(200,200,200)" and c["background"].startswith("rgba(200, 200, 200")
    assert "waive=[key]" in d["fix"] and "改深色字/浅底" in d["fix"]
