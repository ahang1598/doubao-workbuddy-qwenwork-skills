"""Readability and collision regressions for sparse legacy chart inputs."""

import copy
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import gen_svg_charts as charts
from embed_svg_validator import detect_embedded_svg_overlaps, validate_embedded_svgs


def checked(svg):
    root = ET.fromstring(f"<slide><data><embed>{svg}</embed></data></slide>")
    assert not validate_embedded_svgs(root)
    assert not detect_embedded_svg_overlaps(root)
    return ET.fromstring(svg)


def size_of(root, label):
    return max(float(node.get("font-size")) for node in root.iter() if node.text == label)


def test_sparse_prices_enlarge_date_and_value_ticks_without_duplicate_ticks():
    values = [[100 + i, 103 + i, 98 + i, 101 + i] for i in range(4)]
    original = copy.deepcopy(values)
    sparse = checked(charts.make_candle(values, width=1200, height=800))
    dense = checked(charts.make_candle(values * 20, width=1200, height=800))
    assert values == original
    assert size_of(sparse, "$100") >= 20
    assert size_of(sparse, "$100") > size_of(dense, "$100")
    # Four candles must not receive repeated labels from a fixed six-tick loop.
    labels = [node.text for node in sparse.iter() if node.tag.endswith("text")]
    assert all(labels.count(str(i)) == 1 for i in range(1, 5))


def test_dense_long_dates_keep_both_endpoints_without_tick_collisions():
    values = [[100 + i, 103 + i, 98 + i, 101 + i] for i in range(80)]
    root = checked(
        charts.make_candle(values, date_labels=[f"October {i:02d}" for i in range(80)], width=1200, height=800)
    )
    labels = list(root.itertext())
    assert "October 00" in labels and "October 79" in labels


def test_sample_count_does_not_shrink_two_group_labels():
    def render(n):
        return checked(
            charts.make_bar_academic(
                [["Control", [1 + i % 5 for i in range(n)]], ["Treatment", [2 + i % 5 for i in range(n)]]],
                width=1200,
                height=800,
                multi_mode="single",
            )
        )

    small, large = render(10), render(500)
    assert size_of(small, "Control") == size_of(large, "Control")
    assert size_of(large, "Control") >= 24


def test_sparse_quantitative_quadrant_has_readable_axes():
    root = checked(
        charts.make_quadrant_2x2([["A", 12, 30], ["B", 22, 50], ["C", 18, 60]], x_title="Benefit", y_title="Cost")
    )
    assert size_of(root, "30") >= 20
    assert size_of(root, "A") >= 20
