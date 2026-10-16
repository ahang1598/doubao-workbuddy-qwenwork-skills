"""Short slide boxes must not crush the plot area under fixed journal margins.

chart_slide renders at the box size; a generator whose title/legend/axis chrome leaves only a
sliver for the data must either lay out compactly or be grown (same aspect) and scaled down.
"""

import inspect
import re
import sys
import warnings
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import gen_svg_charts as charts
from embed_svg_validator import detect_embedded_svg_overlaps
from svg_lib.chart_examples import EXAMPLES

SLUGS = "band_structure kinetics km_survival nyquist_bode stress_strain titration phase_diagram time_latitude histogram dose_response line_band scatter roc_pr volcano seismic_waveform contour vector_field spectrum depth_profile coef_plot".split()
COMPACT = "band_structure kinetics km_survival nyquist_bode titration phase_diagram time_latitude histogram".split()


def _render(slug, w, h):
    make = getattr(charts, "make_" + slug)
    kwargs = dict(EXAMPLES[slug], width=w, height=h)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        svg, _ = charts._render_fitting(make, inspect.signature(make).parameters, kwargs, w, h)
    return svg


def _slide_plot(svg, w, h):
    area = charts._plot_area(svg)
    assert area is not None, "axis spines must carry data-role=x-axis / y-axis"
    vw, vh = (float(v) for v in re.search(r'viewBox="([^"]+)"', svg).group(1).split()[2:])
    k = max(vw / w, vh / h)
    return area[2] / k, area[3] / k, vh / h


@pytest.mark.parametrize("w,h", [(848, 300), (480, 320)])
@pytest.mark.parametrize("slug", SLUGS)
def test_short_box_keeps_a_usable_plot(slug, w, h):
    svg = _render(slug, w, h)
    pw, ph, grow = _slide_plot(svg, w, h)
    assert ph >= 110, f"{slug} {w}x{h}: plot is only {ph:.0f} slide px tall"
    assert pw >= 0.33 * w, f"{slug} {w}x{h}: plot is only {pw:.0f} slide px wide"
    assert grow <= charts._PLOT_GROW_MAX + 0.3  # bounded growth (ValueError path may add a bit)


@pytest.mark.parametrize("slug", COMPACT)
def test_compact_margins_fit_without_scaling_or_collisions(slug):
    w, h = (848, 300)
    svg = _render(slug, w, h)
    vw = float(re.search(r'viewBox="([^"]+)"', svg).group(1).split()[2])
    if slug != "km_survival":  # the at-risk table legitimately needs a taller canvas
        assert vw == pytest.approx(w), f"{slug} should lay out compactly at the box size"
    root = ET.fromstring(f"<slide><data><embed>{svg}</embed></data></slide>")
    assert not detect_embedded_svg_overlaps(root)


def test_large_canvas_layout_is_unchanged_by_compact_path():
    svg = charts.make_band_structure(**EXAMPLES["band_structure"], width=1300, height=820)
    x, y, pw, ph = charts._plot_area(svg)
    assert (x, y) == (110, 110) and ph == pytest.approx(820 - 240)


def test_plot_area_reads_line_and_path_spines():
    svg = (
        '<svg viewBox="0 0 400 300"><line x1="50" y1="20" x2="50" y2="220" data-role="y-axis"/>'
        '<path d="M50.000,220.000 H380.000" data-role="x-axis"/></svg>'
    )
    assert charts._plot_area(svg) == (50.0, 20.0, 330.0, 200.0)
    assert charts._plot_area('<svg viewBox="0 0 10 10"/>') is None
