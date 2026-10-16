"""Real regressions for legacy chart labels, annotations and encoded values."""

import copy
import math
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

import gen_svg_charts as charts
from embed_svg_validator import detect_embedded_svg_overlaps, validate_embedded_svgs
from svg_lib.chart_examples import EXAMPLES
from svg_lib.charts.nested_donut import VARIANTS
from svg_lib.charts.stress_strain import _auto_detect_features, _youngs_modulus

SLUGS = ("grouped_bar", "nested_donut", "stress_strain", "titration")


def clean_svg(svg):
    root = ET.fromstring(f"<slide><data><embed>{svg}</embed></data></slide>")
    assert validate_embedded_svgs(root) == []
    assert detect_embedded_svg_overlaps(root) == []
    return ET.fromstring(svg)


def text(root):
    return " ".join(root.itertext())


@pytest.mark.parametrize(
    "slug, palette", [(slug, None) for slug in SLUGS] + [("nested_donut", "archive_ink"), ("titration", "nightlab")]
)
def test_original_legacy_example_is_clean_without_extra_configuration(slug, palette):
    kwargs = copy.deepcopy(EXAMPLES[slug])
    original = copy.deepcopy(kwargs)
    root = clean_svg(getattr(charts, "make_" + slug)(**kwargs, title=slug.title(), palette=palette))
    assert kwargs == original
    if slug == "nested_donut":
        assert "Domain A" in text(root) and "Domain B" in text(root)
    elif slug == "titration":
        assert "pH_eq = 7.40" in text(root)
    elif slug == "stress_strain":
        assert "150 GPa" in text(root)


def test_grouped_facet_wraps_full_series_and_category_names():
    kwargs = copy.deepcopy(EXAMPLES["grouped_bar"])
    names = ["Control cohort receiving standard treatment", "Treated cohort receiving experimental compound"]
    categories = [
        "Baseline before treatment",
        "Primary response after intervention",
        "Follow-up with long category label",
    ]
    kwargs.update(series=[(name, row[1]) for name, row in zip(names, kwargs["series"])], categories=categories)
    root = clean_svg(
        charts.make_grouped_bar(**kwargs, title="Treatment response", y_unit="mg", y_title="Concentration")
    )
    for label in names + categories:
        assert label in text(root)


def test_grouped_pairwise_values_and_raw_samples_survive_auto_mode():
    kwargs = copy.deepcopy(EXAMPLES["grouped_bar"])
    kwargs["pairwise_p"] = [(0, 0, 1, 0.03), (1, 0, 1, 0.004)]
    root = clean_svg(charts.make_grouped_bar(**kwargs, title="Between-series comparisons"))
    assert "P = 0.030" in text(root) and "P = 0.004" in text(root)
    samples = [node for node in root.iter() if node.get("data-role") == "replicate"]
    assert len(samples) == 18
    expected = [value for _name, cells in kwargs["series"] for cell in cells for value in cell]
    assert sorted(float(node.get("data-value")) for node in samples) == sorted(expected)
    with pytest.raises(ValueError, match="shared grouped plot"):
        charts.make_grouped_bar(**kwargs, multi_mode="with_facet_by_series")


@pytest.mark.parametrize("variant", VARIANTS)
def test_nested_variants_keep_clean_rendering(variant):
    root = clean_svg(charts.make_nested_donut(**EXAMPLES["nested_donut"], variant=variant, title=variant))
    assert root.tag.endswith("svg")


@pytest.mark.parametrize("variant", [None, *VARIANTS])
def test_nested_small_sectors_and_long_names_keep_every_label(variant):
    name = "Research & development with a long complete department name"
    sub = "Core programme with the complete label retained"
    data = [
        (name, 99.9, [(sub, 50), ("Secondary programme", 49.9)]),
        ("Tiny but important domain", 0.1, [("Rare category retained", 0.1)]),
    ]
    root = clean_svg(charts.make_nested_donut(data, title="Full hierarchy", palette="nightlab", variant=variant))
    for label in (name, sub, "Tiny but important domain", "Rare category retained"):
        assert label in text(root)
    assert "…" not in text(root)


def test_nested_full_circle_and_polar_area_encoding():
    root = clean_svg(charts.make_nested_donut([("Only domain", 100, [("Only subcategory", 100)])]))
    rings = root.findall(".//{*}path")[:2]
    assert len(rings) == 2 and all(node.get("d").count("A ") == 4 for node in rings)
    assert "Only domain" in text(root) and "Only subcategory" in text(root)
    root = clean_svg(charts.make_nested_donut(**EXAMPLES["nested_donut"], variant="polar_area_outlined"))
    radii = [float(re.search(r"A ([\d.]+)", node.get("d")).group(1)) for node in root.findall(".//{*}path")]
    areas = [r * r - 4 * 4 for r in radii]
    assert [v / areas[0] for v in areas] == pytest.approx([1, 25 / 35, 25 / 35, 15 / 35], abs=0.001)


def test_stress_strain_yield_percent_strain_and_tangent_mode():
    curve = EXAMPLES["stress_strain"]["curve"]
    features = _auto_detect_features(curve)
    assert features["elastic_region"] == (0, 0.002)
    assert features["yield_point"] == (0.002, 300)
    assert _youngs_modulus(curve, features["elastic_region"]) == 150000
    kwargs = copy.deepcopy(EXAMPLES["stress_strain"])
    kwargs.update(
        curve=[(100 * x, y) for x, y in kwargs["curve"]],
        yield_point=(0.2, 300),
        ultimate_point=(6, 500),
        fracture_point=(10, 450),
        strain_unit="%",
    )
    root = clean_svg(charts.make_stress_strain(**kwargs, title="Percent strain"))
    assert "150 GPa" in text(root)
    curve = [(i * 0.004, 150000 * i * 0.004 if i < 2 else 300 + 200 * (1 - math.exp(-i / 5))) for i in range(26)]
    root = clean_svg(charts.make_stress_strain(curve, title="Tangent modulus", multi_mode="with_tangent_modulus"))
    labels = ["".join(node.itertext()) for node in root.findall(".//{*}text")]
    assert labels.count("Strain") == 1
    assert "Tangent modulus · dσ/dε (GPa)" in labels


def test_titration_markers_pka_labels_and_derivative():
    xs = list(range(61))
    ys = [2 + 5 / (1 + math.exp(-(x - 20) / 2)) + 5 / (1 + math.exp(-(x - 40) / 2)) for x in xs]
    root = clean_svg(
        charts.make_titration(
            xs,
            ys,
            equivalence_points=[20, 40],
            multi_mode="single",
            title="Two equivalence points",
            pka_values=[(7, "estimated second acid dissociation constant")],
        )
    )
    assert "estimated second acid dissociation constant" in text(root)
    assert "pH_eq = 4.50" in text(root) and "pH_eq = 9.50" in text(root)
    assert len([node for node in root.findall(".//{*}circle") if node.get("r") == "5.5"]) == 2
    xs = list(range(41))
    ys = [2 + 10 / (1 + math.exp(-(x - 23) / 2.5)) for x in xs]
    root = clean_svg(
        charts.make_titration(xs, ys, equivalence_points=[23], multi_mode="with_derivative", palette="nightlab")
    )
    assert "dpH/dV" in text(root) and "pH_eq = 7.00" in text(root)
