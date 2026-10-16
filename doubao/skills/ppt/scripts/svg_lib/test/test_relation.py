"""Relation Layer 4 attributes and the attribute apply pipeline."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from ..relation.attributes import (
    Weighted,
    Signed,
    Typed,
    Temporal,
    Category,
    Size,
    Status,
    Highlight,
    Confidence,
    Directional,
    resolve_channels,
    apply_attributes,
    apply_attributes_batch,
    svg_style_string,
)
from ..relation.palettes import GS_RESEARCH, HBS_CASE, INSTITUTIONAL_WHITE


# ====================================================================================================
# Layer 4 · Attributes: field resolution (incl. v1 aliases) and per-channel encoding.
# ====================================================================================================

RESOLVE = [
    (Weighted, [({"weight": 4.0}, 4.0), ({"value": 9.0}, 9.0), ({"other": 1.0}, None)]),
    (Signed, [({"sign": "+"}, "+"), ({"sign": "positive"}, "+"), ({"sign": "neg"}, "-"), ({}, None)]),
    (
        Typed,
        [
            ({"type": "supports"}, "supports"),
            ({"kind": "opposes"}, "opposes"),
            ({"role": "leader"}, "leader"),
            ({}, None),
        ],
    ),
    (Temporal, [({"phase": "early"}, "early"), ({"t_start": 0.3}, 0.3), ({}, None)]),
    (Category, [({"group": "A"}, "A"), ({"category": "B"}, "B"), ({}, None)]),
    (Size, [({"size": 16.0}, 16.0), ({"count": 4}, 4.0), ({}, None)]),
    (Status, [({"status": "healthy"}, "green"), ({"trend": "up"}, "green"), ({"tone": "critical"}, "red"), ({}, None)]),
    (Highlight, [({"highlight": True}, True), ({"highlight": "true"}, True), ({"focus": False}, False), ({}, None)]),
    (Confidence, [({"confidence": 0.9}, 0.9), ({"prob": 1.5}, 1.0), ({}, None)]),  # clamped to [0, 1]
    (Directional, [({"directed": True}, True), ({"has_arrow": False}, False), ({}, None)]),
]


@pytest.mark.parametrize("cls, cases", RESOLVE, ids=[c.__name__ for c, _ in RESOLVE])
def test_resolve_value_and_aliases(cls, cases):
    attr = cls()
    for record, expected in cases:
        assert attr.resolve_value(record) == expected, record


ENCODE = [
    (Weighted, 4.0, "stroke_width", lambda o: o["stroke-width"] >= 1.0),
    (Weighted, 0.5, "opacity", lambda o: 0.0 <= o["opacity"] <= 1.0),
    (Typed, "supports", "dash_pattern", lambda o: "stroke-dasharray" in o),
    (Category, "A", "color_categorical", lambda o: o["fill"].startswith("#")),
    (Category, "A", "halo_border", lambda o: "halo-color" in o and o["halo-width"] > 0),
    (Size, 16.0, "radius_sqrt", lambda o: abs(o["r"] - 24.0) < 0.01),  # sqrt(16)*4 + 8
    (Highlight, True, "opacity_inverse", lambda o: o["opacity"] == 1.0),
    (Highlight, False, "opacity_inverse", lambda o: o["opacity"] < 0.5),
    (Directional, True, "arrow_head_present", lambda o: o["marker-end"] is not None),
    (Directional, False, "arrow_head_present", lambda o: o["marker-end"] is None),
    (Signed, "+", "color_semantic", lambda o: o["stroke"] == "#16a34a"),
    (Signed, "-", "arrow_shape", lambda o: o["marker-shape"] == "bar"),
    (Typed, "supports", "arrow_shape", lambda o: "marker-shape" in o),
    (Temporal, "early", "color_gradient", lambda o: "stroke" in o),
    (Temporal, 0.8, "opacity_gradient", lambda o: o["opacity"] > 0.5),
    (Size, 4.0, "font_size", lambda o: abs(o["font-size"] - 14.0) < 0.01),  # 10 + sqrt(4)*2
    (Status, "green", "color_rag", lambda o: o["fill"] == "#16a34a"),
    (Status, "red", "icon", lambda o: o["icon"] == "cross"),
    (Highlight, True, "accent_color", lambda o: o["stroke"] == "#f97316"),
    (Confidence, 0.95, "dash_pattern", lambda o: o["stroke-dasharray"] is None),  # high confidence: solid
    (Confidence, 0.1, "dash_pattern", lambda o: o["stroke-dasharray"] is not None),
    (Directional, True, "none", lambda o: o == {}),  # fallback 'none' encodes nothing
]


@pytest.mark.parametrize("cls, value, channel, check", ENCODE, ids=[f"{c.__name__}-{ch}-{v}" for c, v, ch, _ in ENCODE])
def test_encode_channel(cls, value, channel, check):
    assert check(cls().encode(value, channel))


def test_resolver_assigns_defaults_falls_back_and_raises_on_full_conflict():
    r = resolve_channels([Category(), Typed(), Signed()])
    assert r == {"Category": "color_categorical", "Typed": "dash_pattern", "Signed": "color_semantic"}
    assert resolve_channels([Category(), Highlight()])["Highlight"] == "opacity_inverse"
    # Typed takes dash_pattern; Confidence then takes its opacity fallback; a third claimant of both must raise.
    with pytest.raises(ValueError):
        resolve_channels([Typed(), Confidence(), Weighted(channel="dash_pattern", fallback_channel="opacity")])


# ====================================================================================================
# Phase 1 · attribute apply pipeline.
# ====================================================================================================


def test_apply_single_attributes():
    out = apply_attributes({"group": "core"}, [Category("group")], GS_RESEARCH)
    assert "stroke" in out
    p = GS_RESEARCH
    palette = {p.primary, p.accent, p.primary_dim, p.accent_dim, p.positive, p.negative, p.ink, p.gray}
    assert out["fill"] in palette
    assert apply_attributes({"highlight": False}, [Highlight()], GS_RESEARCH).get("opacity") == 0.35
    assert apply_attributes({"highlight": True}, [Highlight()], GS_RESEARCH).get("opacity") == 1.0
    assert abs(apply_attributes({"weight": 9.0}, [Weighted()], GS_RESEARCH)["stroke-width"] - 4.5) < 0.01
    out = apply_attributes({"directed": False}, [Directional()], GS_RESEARCH)
    assert out.get("marker-end") is None and "marker-end" not in svg_style_string(out)


def test_apply_pipeline_skips_merges_resolves_and_overrides():
    assert apply_attributes({"id": "n1"}, [Category("group"), Highlight()], GS_RESEARCH) == {}
    out = apply_attributes({"group": "core"}, [Category("group"), Highlight(), Weighted()], GS_RESEARCH)
    assert "fill" in out and "opacity" not in out and "stroke-width" not in out
    out = apply_attributes(
        {"group": "core", "highlight": True, "weight": 4.0}, [Category("group"), Highlight(), Weighted()], GS_RESEARCH
    )
    assert "fill" in out and out.get("opacity") == 1.0
    assert abs(out.get("stroke-width") - 3.0) < 0.01  # sqrt(4)*1.5
    attrs = [Typed(), Confidence()]
    assert resolve_channels(attrs) == {"Typed": "dash_pattern", "Confidence": "opacity"}
    out = apply_attributes({"type": "supports", "confidence": 0.5}, attrs, GS_RESEARCH)
    assert "stroke-dasharray" in out and out["opacity"] > 0.5  # confidence 0.5 → opacity 0.625
    out = apply_attributes({"group": "core"}, [Category("group")], GS_RESEARCH, channels={"Category": "halo_border"})
    assert "halo-color" in out and "halo-width" in out and "fill" not in out


def test_category_colour_is_stateless_alias_equivalent_and_palette_dependent():
    cat = Category("group")
    first = apply_attributes({"id": "svc-1", "group": "core"}, [cat], GS_RESEARCH)
    assert first == apply_attributes({"group": "core"}, [cat], GS_RESEARCH)
    assert first == apply_attributes({"category": "core"}, [cat], GS_RESEARCH)  # v1 alias
    assert apply_attributes({"group": "data"}, [cat], GS_RESEARCH)["fill"].startswith("#")
    assert apply_attributes({"group": "core"}, [cat], HBS_CASE)["fill"] != first["fill"]
    batch = apply_attributes_batch(
        [{"id": "n1", "group": "core"}, {"id": "n2", "group": "data"}, {"id": "n3", "group": "core"}],
        [cat],
        GS_RESEARCH,
    )
    assert len(batch) == 3 and batch[0]["fill"] == batch[2]["fill"]


def test_svg_style_string_formats_skips_none_and_sorts():
    s = svg_style_string({"fill": "#003A84", "opacity": 0.5})
    assert 'fill="#003A84"' in s and 'opacity="0.500"' in s
    s = svg_style_string({"stroke": "#fff", "stroke-dasharray": None})
    assert "stroke-dasharray" not in s and 'stroke="#fff"' in s
    assert svg_style_string({"z-index": 1, "a-first": "x"}).startswith("a-first=")


def test_realistic_preset_scenarios():
    assert apply_attributes({"directed": True}, [Directional()], GS_RESEARCH).get("marker-end") == "url(#arrowhead)"
    node = {"id": "gw", "label": "gateway", "group": "edge", "highlight": True}
    out = apply_attributes(node, [Category("group"), Highlight()], INSTITUTIONAL_WHITE)
    assert out["fill"].startswith("#") and out.get("opacity") == 1.0
    edge = apply_attributes({"src": "n1", "dst": "n2", "weight": 16.0}, [Weighted()], INSTITUTIONAL_WHITE)
    assert abs(edge["stroke-width"] - 6.0) < 0.01  # sqrt(16)*1.5
    out = apply_attributes({"id": "c", "group": "physics", "size": 25.0}, [Category("group"), Size()], HBS_CASE)
    assert out["fill"].startswith("#") and abs(out["r"] - 28.0) < 0.01  # sqrt(25)*4 + 8
