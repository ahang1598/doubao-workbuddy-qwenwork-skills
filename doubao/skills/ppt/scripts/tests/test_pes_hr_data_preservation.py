"""Regression checks for observed stellar coordinates and explicit PES states."""

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


def checked(svg):
    host = ET.fromstring(f"<slide><data><embed>{svg}</embed></data></slide>")
    assert validate_embedded_svgs(host) == []
    assert detect_embedded_svg_overlaps(host) == []
    return ET.fromstring(svg)


def labels(root):
    return " ".join(root.itertext())


def stars(root):
    return [node for node in root.findall(".//{*}circle") if node.get("r") == "3.20"]


@pytest.mark.parametrize(
    "slug, palette", [("potential_energy_surface", None), ("hr_diagram", None), ("hr_diagram", "nightlab")]
)
def test_original_examples_keep_all_data_and_input_dictionaries(slug, palette):
    kwargs = copy.deepcopy(EXAMPLES[slug])
    before = copy.deepcopy(kwargs)
    root = checked(getattr(charts, "make_" + slug)(**kwargs, palette=palette, title=slug.replace("_", " ").title()))
    assert kwargs == before
    if slug == "hr_diagram":
        assert len(stars(root)) == 4
        for name in ("Sun", "A", "B", "C"):
            assert name in labels(root)
        assert sum(bool(re.fullmatch(r"[\d,]+", node.text or "")) for node in root.findall(".//{*}text")) >= 3
    else:
        for name in ("Reactant", "Transition‡", "Product"):
            assert name in labels(root)


def test_explicit_off_curve_state_uses_one_affine_scale_and_is_not_mutated():
    curve, states = [[0, 0], [1, 1]], [{"x": 0.5, "y": 9, "label": "Measured state"}]
    before = copy.deepcopy((curve, states))
    root = checked(charts.make_potential_energy_surface(curve, states))
    assert (curve, states) == before
    path = next(node for node in root.findall(".//{*}path") if node.get("stroke-width") == "2.2")
    x0, y0, x1, y1 = map(float, re.findall(r"-?[\d.]+", path.get("d")))
    marker = next(node for node in root.findall(".//{*}circle") if node.get("r") == "6")
    assert float(marker.get("cx")) == pytest.approx((x0 + x1) / 2, abs=0.2)
    assert float(marker.get("cy")) == pytest.approx(y0 + 9 * (y1 - y0), abs=0.8)
    assert float(marker.get("cy")) < y1
    assert "clipPath" not in ET.tostring(root, encoding="unicode")


@pytest.mark.parametrize("key", ["temperature", "teff", "temp"])
@pytest.mark.parametrize("luminosity_key", ["luminosity", "L"])
def test_hr_coordinate_aliases_are_identical_without_mutation(key, luminosity_key):
    data = [
        {key: 5778, luminosity_key: 1, "name": "Measured solar analogue"},
        {key: 8000, luminosity_key: 20, "name": "Hot companion"},
    ]
    before = copy.deepcopy(data)
    actual = checked(charts.make_hr_diagram(data))
    expected = checked(
        charts.make_hr_diagram(
            [
                {"temperature": 5778, "luminosity": 1, "label": "Measured solar analogue"},
                {"temperature": 8000, "luminosity": 20, "label": "Hot companion"},
            ]
        )
    )
    assert data == before
    assert [node.attrib for node in stars(actual)] == [node.attrib for node in stars(expected)]
    assert labels(actual) == labels(expected)
    ring = next(node for node in actual.findall(".//{*}circle") if node.get("r") == "8")
    assert ring.get("fill") == "none"
    assert (ring.get("cx"), ring.get("cy")) == (stars(actual)[0].get("cx"), stars(actual)[0].get("cy"))


@pytest.mark.parametrize("xkey,ykey", [("bv", "abs_mag"), ("b_v", "absolute_magnitude"), ("B-V", "M_V")])
def test_color_magnitude_schema_keeps_direct_coordinates_and_brightness_direction(xkey, ykey):
    data = [{xkey: -0.2, ykey: -4, "name": "Hot bright star"}, {xkey: 1.5, ykey: 10, "name": "Cool faint star"}]
    before = copy.deepcopy(data)
    root = checked(charts.make_hr_diagram(data))
    assert data == before
    a, b = stars(root)
    assert float(a.get("cx")) < float(b.get("cx"))
    assert float(a.get("cy")) < float(b.get("cy"))
    assert "B−V color index" in labels(root) and "Absolute magnitude" in labels(root)
    assert "Effective Temperature" not in labels(root)


@pytest.mark.parametrize(
    "bad",
    [
        {"temp": 5000},
        {"temp": -3, "luminosity": 1},
        {"temp": 5000, "luminosity": 0},
        {"teff": math.nan, "luminosity": 1},
        {"bv": 0.5, "abs_mag": math.inf},
        {"name": "Missing coordinates"},
    ],
)
def test_hr_rejects_any_invalid_observation_instead_of_counting_and_dropping_it(bad):
    with pytest.raises(ValueError, match=r"stars\[1\]") as exc:
        charts.make_hr_diagram([{"temp": 5778, "luminosity": 1}, bad])
    assert str(exc.value)


def test_hr_rejects_mixed_coordinate_systems_and_invalid_track_vertices():
    with pytest.raises(ValueError, match="same") as exc:
        charts.make_hr_diagram([{"temp": 5778, "luminosity": 1}, {"bv": 0.5, "abs_mag": 4}])
    assert str(exc.value)
    with pytest.raises(ValueError, match="positive") as exc:
        charts.make_hr_diagram([], evolutionary_tracks=[{"points": [[6000, 1], [0, 2]]}])
    assert str(exc.value)


@pytest.mark.parametrize("slug", ["potential_energy_surface", "hr_diagram"])
def test_long_labels_are_complete_and_external_to_the_plot(slug):
    kwargs = copy.deepcopy(EXAMPLES[slug])
    name = "Measured object with a complete long scientific designation retained"
    if slug == "potential_energy_surface":
        kwargs["states"][0]["label"] = name
    else:
        kwargs["stars"][0]["name"] = name
    root = checked(getattr(charts, "make_" + slug)(**kwargs, palette="nightlab"))
    assert name in labels(root)
    assert "…" not in labels(root)


@pytest.mark.parametrize("value", [math.nan, math.inf, None])
def test_pes_rejects_invalid_state_coordinates(value):
    with pytest.raises(ValueError, match="finite") as exc:
        charts.make_potential_energy_surface([[0, 0], [1, 1]], [{"x": 0.5, "y": value}])
    assert str(exc.value)


def test_single_pes_sample_is_still_visible():
    root = checked(charts.make_potential_energy_surface([[2, 7]], []))
    assert len(root.findall(".//{*}circle")) == 1


def test_hr_explicit_mass_histogram_keeps_stars_and_mass_bins():
    data = copy.deepcopy(EXAMPLES["hr_diagram"])
    masses = [0.1 + (i / 20) ** 2 for i in range(80)]
    before = copy.deepcopy((data, masses))
    root = checked(charts.make_hr_diagram(**data, masses=masses, width=1450, multi_mode="with_mass_hist"))
    assert (data, masses) == before
    assert len(stars(root)) == 4
    assert len([node for node in root.findall(".//{*}rect") if node.get("stroke") == "none"]) == 12
    assert "Mass hist" in labels(root)


def test_free_energy_diagram_compares_pathways_and_marks_barriers():
    pathways = [
        {"name": "Cu(100)", "energies": [0, 0.62, -0.31, 0.95, -0.42], "ts": [1, 3]},
        {"name": "GB-Cu", "energies": [0, 0.41, -0.45, 0.58, None], "ts": [1, 3]},
    ]
    root = checked(
        charts.make_potential_energy_surface(
            pathways=pathways, steps=["*CO2", "TS1", "*COOH", "TS2", "*CO"], energy_unit="eV"
        )
    )
    text = labels(root)
    for value in ("0.62", "-0.31", "0.95", "0.58", "Cu(100)", "GB-Cu", "*COOH", "TS2"):
        assert value in text
    assert "ΔG‡ = 1.26 eV" in text and "ΔG‡ = 1.03 eV" in text
    with pytest.raises(ValueError):
        charts.make_potential_energy_surface(pathways=[{"name": "x", "energies": [0]}])
