"""Focused regressions for chart discovery and preserved, readable labels."""

import ast
import inspect
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(SCRIPTS.parent))

import gen_svg_charts as charts
from embed_svg_validator import detect_embedded_svg_overlaps, validate_embedded_svgs
from svg_lib._common import _resolve_font, _resolve_palette
from svg_lib.charts._academic_rigor import BBox
from svg_lib.charts._xy import _render_labels
from svg_lib.chart_examples import EXAMPLES
from svg_lib.charts._shared import authored_strings
from svg_lib.charts.bar_academic import make_bar_academic


def test_overview_aliases_and_legacy_academic_bar_discovery():
    overview = charts.chart_help()
    catalog = charts.chart_catalog()
    assert len(overview) < 12000
    assert all(f"- {slug}:" in overview for slug in catalog)
    assert "example_kwargs" not in overview and "kwargs =" not in overview
    # The former overview repeated all example records, even enormous arrays.
    assert not any(entry["example"] in overview for entry in catalog.values())
    catalog = charts.chart_catalog()
    assert "bar_academic" not in catalog
    assert "academic_bar_chart" not in catalog
    assert "bar_academic" not in charts.chart_help()
    assert "academic_bar_chart" not in charts.chart_help()
    with pytest.raises(ValueError, match="grouped_bar"):
        charts.chart_help("bar_academic")
    assert "make_grouped_bar" in charts.chart_help("academic_bar_chart")
    assert charts.chart_help("grouped_bars") == charts.chart_help("grouped_bar")
    kwargs = EXAMPLES["grouped_bar"]
    assert charts.chart_slide("grouped_bars", 40, 100, 600, 380, **kwargs) == charts.chart_slide(
        "grouped_bar", 40, 100, 600, 380, **kwargs
    )
    assert charts.chart_fit("grouped_bars", 600, 380, **kwargs) == charts.chart_fit("grouped_bar", 600, 380, **kwargs)
    assert "grouped_bars" not in charts.chart_catalog()
    assert getattr(make_bar_academic, "__wrapped__", make_bar_academic) is getattr(
        charts.make_bar_academic, "__wrapped__", None
    )
    svg = charts.make_bar_academic([("Before", [1, 2, 3]), ("After", [3, 4, 5])], multi_mode="single")
    root = ET.fromstring(f"<slide><data><embed>{svg}</embed></data></slide>")
    assert not validate_embedded_svgs(root)


def test_academic_bar_chart_is_a_grouped_bar_alias():
    import warnings

    data = dict(categories=["R1", "R2", "R3"], series=[{"name": "A", "values": [62, 73, 68]}], y_unit="%")
    ring = dict(center={"mode": "mean", "error_kind": "SD"}, grouping="category", inner_radius=0.4)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        alias = charts.chart_slide("academic_bar_chart", 0, 0, 600, 400, **data, **ring)
    notes = [str(w.message) for w in caught if "academic_bar_chart" in str(w.message)]
    assert len(notes) == 1 and all(key in notes[0] for key in ring) and "grouped_bar" in notes[0]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        assert alias == charts.chart_slide("grouped_bar", 0, 0, 600, 400, **data)
        assert charts.chart_fit("academic_bar_chart", 600, 400, **data, **ring) == charts.chart_fit(
            "grouped_bar", 600, 400, **data
        )
        assert charts.make_academic_bar_chart(**data, **ring) == charts.make_grouped_bar(**data)
    assert "<p" in alias or "<embed" in alias
    assert "make_grouped_bar" in charts.chart_help("academic_bar_chart")
    with pytest.raises(ValueError, match="bars.*heatmap"):
        charts.make_grouped_bar(**data, multi_mode="radial")


def test_cli_help_does_not_advertise_legacy_academic_bar():
    result = subprocess.run(
        [sys.executable, "-I", "-S", str(SCRIPTS / "gen_svg_charts.py"), "--help"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "academic_bar_chart" not in result.stdout
    assert "bar_academic" not in result.stdout


def test_detail_keeps_exact_signature_and_provides_executable_python_examples():
    for slug, entry in charts.chart_catalog().items():
        detail = charts.chart_help(slug)
        assert entry["function"] + str(inspect.signature(getattr(charts, entry["function"]))) in detail
        code = re.search(r"```python\n(.*?)\n```", detail, re.S).group(1)
        parsed = ast.parse(code)
        # The example must define kwargs before calling the generator; JSON
        # null/true/false must not leak into what is advertised as Python.
        assert isinstance(parsed.body[1], ast.Assign)
        assert parsed.body[1].targets[0].id == "kwargs"
        assert not {"null", "true", "false"} & {node.id for node in ast.walk(parsed) if isinstance(node, ast.Name)}
    detail = charts.chart_help("boxplot")
    code = re.search(r"```python\n(.*?)\n```", detail, re.S).group(1)
    namespace = {}
    exec(code, namespace)
    assert ET.fromstring(namespace["svg"]).tag.endswith("svg")


def test_sankey_cjk_names_and_amounts_do_not_overlap():
    names = ["华东获客团队", "华南服务团队", "区域协作共享中心"]
    svg = charts.make_sankey(names[:2], names[2:], [(names[0], names[2], 30), (names[1], names[2], 20)])
    root = ET.fromstring(f'<slide><data><embed width="980" height="580">{svg}</embed></data></slide>')
    assert not validate_embedded_svgs(root)
    assert not detect_embedded_svg_overlaps(root)
    text = " ".join(root.itertext())
    assert all(name in text for name in names)
    assert "30" in text and "20" in text and "50" in text


def test_impossible_label_layout_fails_instead_of_emitting_an_overlap():
    font, _ = _resolve_font(None)
    with pytest.raises(ValueError, match="point label.*no clear position") as exc:
        _render_labels(
            [(50, 50, "Essential label", "#000000", "source")],
            BBox(0, 0, 100, 100),
            font,
            _resolve_palette(None)["ink"],
            [(0, 0, 100, 100)],
            rail=False,
            fs=14,
        )
    assert str(exc.value)


def test_gantt_stream_lines_and_small_rows():
    tasks = [("区域需求评审", 0, 2, "华东"), ("跨区原型联调", 2, 5, "华南"), ("联合验收发布", 5, 7, "共享")]
    svg = charts.make_gantt(tasks, width=1200, height=650, milestones=[(7, "共同验收")])
    root = ET.fromstring(f"<slide><data><embed>{svg}</embed></data></slide>")
    assert not validate_embedded_svgs(root)
    assert not detect_embedded_svg_overlaps(root)
    text = " ".join(root.itertext())
    assert all(name in text and stream in text for name, _, _, stream in tasks)
    assert "共同验收" in text and "…" not in text
    milestone = next(n for n in root.iter() if n.text == "共同验收")
    stream = next(n for n in root.iter() if n.text == "华东")
    assert milestone.get("font-size") == stream.get("font-size")
    with pytest.raises(ValueError, match="full label.*taller canvas"):
        charts.make_gantt([("Complete label " * 40, 0, 2)], width=900, height=230)


@pytest.mark.parametrize("count", [3, 7, 15, 16, 20, 30])
def test_gantt_default_height_fits_all_task_and_stream_labels(count):
    tasks = [(f"Task {i + 1}", i, i + 1, "Team A") for i in range(count)]
    svg = charts.make_gantt(tasks, width=1000)
    root = ET.fromstring(f"<slide><data><embed>{svg}</embed></data></slide>")
    assert not validate_embedded_svgs(root)
    assert not detect_embedded_svg_overlaps(root)
    labels = list(root.itertext())
    assert all(name in labels for name, *_ in tasks)
    assert labels.count("Team A") == count
    assert min(float(node.get("font-size")) for node in root.iter() if node.text == "Team A") >= 11


# Standard abbreviations and symbols that stay untranslated in Chinese papers.
_ZH_ALLOWED_LATIN = set(
    "HR CI SD SEM EC FC UMAP KDE RT Hill log rank Tukey Student PL mAU min nM mM MPa GPa eV Hz pKa pH mL kcal mol RMSE SE AUC Cohen Natural Earth of ECDF Q1 Q3 a.u".split()
)


def _generated_latin_words(svg, authored):
    words = set()
    for node in ET.fromstring(svg).iter():
        if node.tag.rsplit("}", 1)[-1] != "text":
            continue
        text = "".join(node.itertext())
        for value in sorted(authored, key=len, reverse=True):
            text = text.replace(value, " ")
        words |= {w for w in re.findall(r"[A-Za-z][A-Za-z]+", text) if w not in _ZH_ALLOWED_LATIN}
    return words


@pytest.mark.parametrize(
    "slug, kwargs",
    [
        (
            "km_survival",
            dict(
                title="总生存期",
                groups=[
                    {"name": "Control", "times": [3, 5, 8, 12, 15, 20], "events": [1, 1, 0, 1, 1, 0]},
                    {"name": "治疗组", "times": [6, 9, 14, 18, 24, 30], "events": [1, 0, 1, 0, 1, 0]},
                ],
            ),
        ),
        ("histogram", dict(values=[1.2, 2.3, 2.1, 3.3, 2.8, 3.9, 4.1, 2.2, 3.0, 2.6], title="细胞直径分布")),
        (
            "forest",
            dict(
                title="亚组分析",
                rows=[
                    {"label": "Age ≥ 65", "estimate": 0.8, "ci_lo": 0.6, "ci_hi": 1.1, "ci_level": 95},
                    {"label": "女性", "estimate": 0.7, "ci_lo": 0.5, "ci_hi": 0.95, "ci_level": 95},
                ],
            ),
        ),
        (
            "grouped_bar",
            dict(
                categories=["第1周", "第2周"],
                title="周均值",
                series=[
                    {"name": "Placebo", "values": [[3, 4, 5], [4, 5, 6]]},
                    {"name": "药物", "values": [[5, 6, 7], [6, 7, 8]]},
                ],
            ),
        ),
        (
            "dose_response",
            dict(
                title="剂量反应",
                points=[
                    {"group": "Drug A", "dose": d, "response": r}
                    for d, r in [(0.01, 2), (0.1, 10), (1, 50), (10, 88), (100, 98)]
                ],
            ),
        ),
    ],
)
def test_chinese_caller_text_gets_chinese_chrome_and_keeps_author_labels(slug, kwargs):
    svg = getattr(charts, "make_" + slug)(**kwargs)
    authored = authored_strings(kwargs)
    assert not _generated_latin_words(svg, authored), slug
    text = " ".join(ET.fromstring(svg).itertext())
    for label in {"Control", "Age ≥ 65", "Placebo", "Drug A"} & authored:
        assert label in text  # author-supplied English labels are never translated
    english = getattr(charts, "make_" + slug)(lang="en", **kwargs)
    assert _generated_latin_words(english, authored)  # lang="en" keeps the English chrome


def test_language_follows_explicit_lang_and_english_defaults_stay_english():
    kwargs = dict(groups=[{"name": "A", "times": [1, 2, 3], "events": [1, 0, 1]}])
    assert charts.make_km_survival(**kwargs) == charts.make_km_survival(lang="en", **kwargs)
    chinese = " ".join(ET.fromstring(charts.make_km_survival(lang="zh", **kwargs)).itertext())
    assert "生存概率" in chinese and "时间（月）" in chinese and "Survival probability" not in chinese
    # An English caption passed explicitly is the author's choice, even on a Chinese chart.
    forest = charts.make_forest(
        [{"label": "男性", "estimate": 1.2, "ci_lo": 1.0, "ci_hi": 1.5}], x_title="Hazard ratio"
    )
    assert "Hazard ratio" in " ".join(ET.fromstring(forest).itertext())
    with pytest.raises(ValueError, match="lang"):
        charts.make_km_survival(lang="fr", **kwargs)
