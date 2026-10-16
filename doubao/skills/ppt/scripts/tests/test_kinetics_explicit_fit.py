"""Synthetic pulse/decay fixtures must not acquire an unrequested model fit."""

import re
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gen_svg_charts import make_kinetics
from embed_svg_validator import validate_embedded_svgs, detect_embedded_svg_overlaps


def parse(svg):
    root = ET.fromstring("<slide><data><embed>" + svg + "</embed></data></slide>")
    assert not validate_embedded_svgs(root)
    assert not detect_embedded_svg_overlaps(root)
    return root


def paths(root):
    return [n for n in root.iter() if n.tag.rsplit("}", 1)[-1] == "path"]


def test_unspecified_model_preserves_pulse_without_inferred_fit_or_rate():
    curve = dict(name="Pulse", time=[0, 2, 5, 12, 28], value=[0, 0.8, 1, 0.3, 0])
    root = parse(make_kinetics([curve], value_unit="", width=1000, height=680))
    data_paths = [n for n in paths(root) if len(re.findall(r"[ML]", n.get("d", ""))) == 5]
    assert len(data_paths) == 1
    points = [tuple(map(float, pair)) for pair in re.findall(r"[ML] ([\d.]+) ([\d.]+)", data_paths[0].get("d"))]
    assert points[0][1] == points[-1][1] > points[1][1] > points[2][1]
    assert not any(len(re.findall(r"[ML]", n.get("d", ""))) > 5 for n in paths(root))
    content = "".join(root.itertext())
    assert "Response" in content and "Concentration" not in content
    assert "k=" not in content and "Rate constants" not in content


def test_explicit_exponential_still_drawn_when_annotation_hidden():
    curve = dict(name="Decay", time=[0, 1, 2, 3, 4], value=[1, 0.6, 0.36, 0.22, 0.13], fit_type="exp1")
    root = parse(
        make_kinetics(
            [curve], value_label="Concentration", value_unit="mM", show_rate_constants=False, width=1000, height=680
        )
    )
    assert any(len(re.findall(r"[ML]", n.get("d", ""))) > 5 for n in paths(root))
    assert "Concentration (mM)" in "".join(root.itertext())
    assert "k=" not in "".join(root.itertext())


@pytest.mark.parametrize(
    "curve, message",
    [
        (dict(time=[0, 1, 2], value=[1, 2]), "equal nonzero lengths"),
        (dict(time=[0, 1], value=[1, 2], err=[0.1]), "err must match"),
        (dict(time=[0, 1], value=[1, 2], fit_type="exp"), "fit_type must be"),
    ],
)
def test_incomplete_or_misspelled_input_is_not_silently_drawn(curve, message):
    with pytest.raises(ValueError, match=message) as exc:
        make_kinetics([curve])
    assert str(exc.value)


def test_linear_slopes_keep_sign_and_units_and_do_not_become_first_order_rates():
    curves = [
        dict(name=f"Treatment {i}", time=[0, 1, 2], value=[4 + i, 3 + i, 2 + i], fit_type="linear") for i in range(3)
    ]
    root = parse(
        make_kinetics(curves, value_label="Concentration", value_unit="mM", time_unit="s", width=1200, height=820)
    )
    content = "".join(root.itertext())
    assert "Rate constants k" not in content
    assert "slope=-1 mM/s" in content
    with pytest.raises(ValueError, match="rate constant"):
        make_kinetics(curves, multi_mode="with_rate_bars")


def test_units_remain_in_axes_without_a_floating_duplicate_by_the_subtitle():
    curve = dict(name="Pulse", time=[0, 2, 5, 12, 28], value=[0, 0.8, 1, 0.3, 0])
    root = parse(
        make_kinetics(
            [curve],
            value_label="响应",
            value_unit="归一化水平",
            time_unit="min",
            title="合成响应的时间变化",
            subtitle="合成脉冲与后续恢复",
            width=1000,
            height=680,
        )
    )
    texts = ["".join(n.itertext()) for n in root.iter() if n.tag.rsplit("}", 1)[-1] == "text"]
    # Chinese caller text -> Chinese generated axis chrome, units kept as given.
    assert "响应（归一化水平）" in texts and "时间（min）" in texts
    assert "归一化水平" not in texts and "min" not in texts
