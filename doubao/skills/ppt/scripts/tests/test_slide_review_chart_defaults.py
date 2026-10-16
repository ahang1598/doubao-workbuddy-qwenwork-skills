"""Regressions from real-deck review: uniform tick text, year axes, no bookkeeping badges."""

import math
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

import gen_svg_charts as charts
from svg_lib._common import _fmt_axis, _fmt_axis_ticks
from svg_lib.charts import _academic_rigor as rigor
from svg_lib.charts._shared import tr


def texts(svg):
    return [("".join(node.itertext())).strip() for node in ET.fromstring(svg).iter() if node.tag.endswith("text")]


def decimals(label):
    return len(label.split(".")[1]) if "." in label else 0


# ---- shared tick formatter ---------------------------------------------------


@pytest.mark.parametrize(
    "low,high,n", [(0, 1.5, 6), (0, 1.2, 4), (0.8, 1.2, 4), (0, 12.5, 5), (-0.3, 0.3, 4), (0, 0.05, 5)]
)
def test_tick_set_shares_one_decimal_count(low, high, n):
    ticks, lo, hi = rigor.nice_axis(low, high, n)
    labels = _fmt_axis_ticks(ticks, hi - lo)
    assert len({decimals(label) for label in labels}) == 1, labels
    assert len(set(labels)) == len(labels)
    assert all(
        math.isclose(float(label.replace(",", "")), tick, abs_tol=(hi - lo) * 1e-6)
        for label, tick in zip(labels, ticks)
    )


def test_years_shared_axes_and_kinetics_ticks():
    assert _fmt_axis_ticks([0.8, 1.0, 1.2]) == ["0.8", "1.0", "1.2"]
    assert _fmt_axis_ticks([0, 0.25, 0.5, 0.75, 1.0]) == ["0.00", "0.25", "0.50", "0.75", "1.00"]
    assert _fmt_axis_ticks([2000, 2005, 2010, 2015, 2020]) == ["2000", "2005", "2010", "2015", "2020"]
    assert _fmt_axis(2020, 20) == "2020"
    assert _fmt_axis(1500.5, 5) == "1500.50"
    # From 10 000 upward the whole tick set is grouped alike.
    assert _fmt_axis_ticks([0, 5000, 10000, 15000]) == ["0", "5,000", "10,000", "15,000"]
    assert _fmt_axis(25000, 10000) == "25,000"
    svg = rigor.draw_x_axis(0, 500, 300, [2000, 2010, 2020], 2000, 2020) + rigor.draw_y_axis(
        0, 0, 300, [0.8, 1.0, 1.2], 0.8, 1.2
    )
    labels = texts(f"<svg xmlns='http://www.w3.org/2000/svg'>{svg}</svg>")
    assert labels == ["2000", "2010", "2020", "0.8", "1.0", "1.2"]
    years = [2000, 2004, 2008, 2012, 2016, 2020, 2024]
    svg = charts.make_kinetics(
        [{"name": "装机", "time": years, "value": [0.8, 1.1, 1.9, 3.2, 5.0, 7.4, 10.2]}],
        time_unit="年",
        value_unit="TW",
        value_label="装机容量",
    )
    content = texts(svg)
    assert "2000" in content and "2020" in content
    assert not any(re.fullmatch(r"\d,\d{3}", t) for t in content)
    svg = charts.make_scatter(
        [{"name": "A", "points": [{"x": i, "y": 0.8 + 0.1 * i} for i in range(5)]}], fit=None, show_ci=False
    )
    numeric = [t for t in texts(svg) if re.fullmatch(r"-?\d+\.\d+", t)]
    assert numeric and len({decimals(t) for t in numeric}) == 1, numeric


def _spectrum():
    xs = [400 + i * 0.5 for i in range(601)]
    gauss = lambda x, m, s, a: a * math.exp(-((x - m) ** 2) / (2 * s * s))
    ys = [gauss(x, 460, 8, 1.0) + gauss(x, 520, 10, 0.65) + gauss(x, 610, 12, 1.15) for x in xs]
    return xs, ys


def test_spectrum_has_no_default_stats_box_and_uniform_y_ticks():
    xs, ys = _spectrum()
    svg = charts.make_spectrum(xs, ys, peaks=[(460, "蓝光"), (520, "绿光"), (610, "红光")], x_unit="nm")
    content = texts(svg)
    assert "n" not in content and "601" not in content
    assert not any("最小值" in t or "最大值" in t or "x min" in t for t in content)
    numeric = [t for t in content if re.fullmatch(r"-?\d+(\.\d+)?", t)]
    y_labels = [t for t in numeric if float(t) <= 2]
    assert len(y_labels) >= 4 and len({decimals(t) for t in y_labels}) == 1, y_labels
    opt_in = texts(charts.make_spectrum(xs, ys, show_stats=True))
    assert "601" in opt_in


# ---- bookkeeping badges are opt-in ------------------------------------------------


def test_badges_kpi_cards_and_scientific_annotations_defaults():
    for slug, kwargs, marker, opt in [
        ("histogram", dict(values=[1, 2, 2, 3, 3, 3, 4, 4, 5, 6] * 4), "SD", "show_stats"),
        ("contour", dict(grid=[[1, 2, 3], [2, 3, 4], [3, 4, 5]]), "grid 3×3", "show_stats"),
        (
            "hr_diagram",
            dict(stars=[{"temperature": 5800, "luminosity": 1}, {"temperature": 9000, "luminosity": 20}]),
            "n stars = 2",
            "show_count",
        ),
        ("nyquist_bode", dict(nyquist_points=[(10, 1, 1e4), (20, 8, 1e3), (40, 3, 1e2)]), "n points", "show_count"),
        (
            "titration",
            dict(
                volume=[i * 0.5 for i in range(41)],
                ph_or_response=[2 + 10 / (1 + math.exp(-(i * 0.5 - 10) * 2)) for i in range(41)],
            ),
            "n points",
            "show_stats",
        ),
    ]:
        maker = getattr(charts, f"make_{slug}")
        default = " ".join(texts(maker(**kwargs)))
        assert tr(marker) not in default and marker not in default, slug
        enabled = " ".join(texts(maker(**kwargs, **{opt: True})))
        assert tr(marker) in enabled or marker in enabled, slug
    content = " ".join(texts(charts.make_histogram([1, 2, 2, 3, 3, 3, 4, 4, 5, 6] * 4)))
    assert tr("mean") + " 3.3" in content and tr("median") + " 3" in content
    ohlc = [(10 + i, 11 + i, 9 + i, 10.5 + i) for i in range(30)]
    default = " ".join(texts(charts.make_candle(ohlc)))
    assert tr("RANGE") not in default and tr("PERIOD CHANGE") not in default
    assert tr("RANGE") in " ".join(texts(charts.make_candle(ohlc, show_kpi=True)))
    pts = [{"x": i, "y": 2 * i + (0.3 if i % 2 else -0.3)} for i in range(12)]
    content = " ".join(texts(charts.make_scatter([{"name": "A", "points": pts}], fit="linear", show_stats_box=True)))
    assert "R²" in content
