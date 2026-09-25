"""
Unit tests for Layer 4 · Attributes.

跑法：
    cd code && python3 -m svg_relation_lib.attributes._test_attrs
"""
from __future__ import annotations
import sys
import traceback

from svg_relation_lib.attributes import (
    Weighted, Signed, Typed, Temporal, Category,
    Size, Status, Highlight, Confidence, Directional,
    resolve_channels,
)


# ---------- test helpers ----------

_PASSED: list = []
_FAILED: list = []


def _run(name, fn):
    try:
        fn()
        _PASSED.append(name)
        print(f"  [OK]  {name}")
    except AssertionError as e:
        _FAILED.append((name, str(e)))
        print(f"  [FAIL] {name} · {e}")
    except Exception as e:
        _FAILED.append((name, f"{type(e).__name__}: {e}"))
        print(f"  [ERR]  {name} · {type(e).__name__}: {e}")
        traceback.print_exc()


# =============== A1 · Weighted ===============

def test_weighted_resolve():
    attr = Weighted()
    assert attr.resolve_value({"weight": 4.0}) == 4.0
    # v1 alias
    assert attr.resolve_value({"value": 9.0}) == 9.0
    # missing
    assert attr.resolve_value({"other": 1.0}) is None


def test_weighted_default_channel():
    attr = Weighted()
    out = attr.encode(4.0, "stroke_width")
    assert "stroke-width" in out
    assert out["stroke-width"] >= 1.0


def test_weighted_fallback_channel():
    attr = Weighted()
    out = attr.encode(0.5, "opacity")
    assert "opacity" in out
    assert 0.0 <= out["opacity"] <= 1.0


# =============== A2 · Signed ===============

def test_signed_resolve():
    attr = Signed()
    assert attr.resolve_value({"sign": "+"}) == "+"
    assert attr.resolve_value({"sign": "positive"}) == "+"
    assert attr.resolve_value({"sign": "neg"}) == "-"
    assert attr.resolve_value({}) is None


def test_signed_default_channel():
    attr = Signed()
    out = attr.encode("+", "color_semantic")
    assert out["stroke"] == "#16a34a"


def test_signed_fallback_channel():
    attr = Signed()
    out = attr.encode("-", "arrow_shape")
    assert out["marker-shape"] == "bar"


# =============== A3 · Typed ===============

def test_typed_resolve():
    attr = Typed()
    assert attr.resolve_value({"type": "supports"}) == "supports"
    # v1 alias
    assert attr.resolve_value({"kind": "opposes"}) == "opposes"
    assert attr.resolve_value({"role": "leader"}) == "leader"
    assert attr.resolve_value({}) is None


def test_typed_default_channel():
    attr = Typed()
    out = attr.encode("supports", "dash_pattern")
    assert "stroke-dasharray" in out


def test_typed_fallback_channel():
    attr = Typed()
    out = attr.encode("supports", "arrow_shape")
    assert "marker-shape" in out


# =============== A4 · Temporal ===============

def test_temporal_resolve():
    attr = Temporal()
    assert attr.resolve_value({"phase": "early"}) == "early"
    # v1 alias
    assert attr.resolve_value({"t_start": 0.3}) == 0.3
    assert attr.resolve_value({}) is None


def test_temporal_default_channel():
    attr = Temporal()
    out = attr.encode("early", "color_gradient")
    assert "stroke" in out


def test_temporal_fallback_channel():
    attr = Temporal()
    out = attr.encode(0.8, "opacity_gradient")
    assert "opacity" in out
    assert out["opacity"] > 0.5


# =============== A5 · Category ===============

def test_category_resolve():
    attr = Category()
    assert attr.resolve_value({"group": "A"}) == "A"
    # v1 alias
    assert attr.resolve_value({"category": "B"}) == "B"
    assert attr.resolve_value({}) is None


def test_category_default_channel():
    attr = Category()
    out = attr.encode("A", "color_categorical")
    assert "fill" in out and out["fill"].startswith("#")


def test_category_fallback_channel():
    attr = Category()
    out = attr.encode("A", "halo_border")
    assert "halo-color" in out and out["halo-width"] > 0


# =============== A6 · Size ===============

def test_size_resolve():
    attr = Size()
    assert attr.resolve_value({"size": 16.0}) == 16.0
    assert attr.resolve_value({"count": 4}) == 4.0
    assert attr.resolve_value({}) is None


def test_size_default_channel():
    attr = Size()
    out = attr.encode(16.0, "radius_sqrt")
    # sqrt(16)*4 + 8 = 24
    assert abs(out["r"] - 24.0) < 0.01


def test_size_fallback_channel():
    attr = Size()
    out = attr.encode(4.0, "font_size")
    # 10 + sqrt(4)*2 = 14
    assert abs(out["font-size"] - 14.0) < 0.01


# =============== A7 · Status ===============

def test_status_resolve():
    attr = Status()
    assert attr.resolve_value({"status": "healthy"}) == "green"
    # v1 alias
    assert attr.resolve_value({"trend": "up"}) == "green"
    assert attr.resolve_value({"tone": "critical"}) == "red"
    assert attr.resolve_value({}) is None


def test_status_default_channel():
    attr = Status()
    out = attr.encode("green", "color_rag")
    assert out["fill"] == "#16a34a"


def test_status_fallback_channel():
    attr = Status()
    out = attr.encode("red", "icon")
    assert out["icon"] == "cross"


# =============== A8 · Highlight ===============

def test_highlight_resolve():
    attr = Highlight()
    assert attr.resolve_value({"highlight": True}) is True
    assert attr.resolve_value({"highlight": "true"}) is True
    assert attr.resolve_value({"focus": False}) is False
    assert attr.resolve_value({}) is None


def test_highlight_default_channel():
    attr = Highlight()
    out_on = attr.encode(True, "opacity_inverse")
    out_off = attr.encode(False, "opacity_inverse")
    assert out_on["opacity"] == 1.0
    assert out_off["opacity"] < 0.5


def test_highlight_fallback_channel():
    attr = Highlight()
    out = attr.encode(True, "accent_color")
    assert out["stroke"] == "#f97316"


# =============== A9 · Confidence ===============

def test_confidence_resolve():
    attr = Confidence()
    assert attr.resolve_value({"confidence": 0.9}) == 0.9
    # v1 alias · also clamped to [0, 1]
    assert attr.resolve_value({"prob": 1.5}) == 1.0
    assert attr.resolve_value({}) is None


def test_confidence_default_channel():
    attr = Confidence()
    out_high = attr.encode(0.95, "dash_pattern")
    out_low = attr.encode(0.1, "dash_pattern")
    # high confidence · solid
    assert out_high["stroke-dasharray"] is None
    # low confidence · dashed
    assert out_low["stroke-dasharray"] is not None


def test_confidence_fallback_channel():
    attr = Confidence()
    out = attr.encode(0.5, "opacity")
    assert 0.5 < out["opacity"] <= 1.0


# =============== A10 · Directional ===============

def test_directional_resolve():
    attr = Directional()
    assert attr.resolve_value({"directed": True}) is True
    assert attr.resolve_value({"has_arrow": False}) is False
    assert attr.resolve_value({}) is None


def test_directional_default_channel():
    attr = Directional()
    out_on = attr.encode(True, "arrow_head_present")
    out_off = attr.encode(False, "arrow_head_present")
    assert out_on["marker-end"] is not None
    assert out_off["marker-end"] is None


def test_directional_fallback_none():
    attr = Directional()
    # fallback is 'none' · returns empty dict
    out = attr.encode(True, "none")
    assert out == {}


# =============== Conflict Resolver ===============

def test_resolver_no_conflict():
    """Category (color_categorical) + Highlight (opacity_inverse) · 各自默认 channel。"""
    r = resolve_channels([Category(), Highlight()])
    assert r["Category"] == "color_categorical"
    assert r["Highlight"] == "opacity_inverse"


def test_resolver_three_distinct():
    """Category + Typed + Signed · 各占不同 channel · 不 raise。"""
    r = resolve_channels([Category(), Typed(), Signed()])
    assert r["Category"] == "color_categorical"
    assert r["Typed"] == "dash_pattern"
    assert r["Signed"] == "color_semantic"
    # 都是默认 channel · 互不冲突
    assert len(set(r.values())) == 3


def test_resolver_fallback_kicks_in():
    """两个都想用 dash_pattern · 第二个降级到 fallback。"""
    r = resolve_channels([Typed(), Confidence()])
    # Typed 拿到默认 dash_pattern
    assert r["Typed"] == "dash_pattern"
    # Confidence 降级到 opacity fallback
    assert r["Confidence"] == "opacity"


def test_resolver_raises_on_full_conflict():
    """三个都想用 dash_pattern · 且 fallback 也冲突 · 应 raise。"""
    # Construct scenario: Typed(dash_pattern|arrow_shape),
    # Confidence(dash_pattern|opacity), Weighted(stroke_width|opacity)
    # If we chain [Typed, Confidence, Weighted]:
    #   Typed → dash_pattern
    #   Confidence → opacity (fallback)
    #   Weighted → stroke_width (default, no conflict)
    # No raise. Need harder case: Typed, Confidence(force dash), Weighted(force opacity)
    # Use custom instances to force conflict.
    a = Typed()
    b = Confidence()
    c = Weighted(channel="dash_pattern", fallback_channel="opacity")
    raised = False
    try:
        # Typed → dash_pattern (used)
        # Confidence → dash_pattern taken → opacity (used)
        # c → dash_pattern taken, opacity taken → raise
        resolve_channels([a, b, c])
    except ValueError:
        raised = True
    assert raised, "expected ValueError on full channel conflict"


# ---------- runner ----------

def main():
    tests = [
        # Weighted
        ("weighted.resolve", test_weighted_resolve),
        ("weighted.default_channel", test_weighted_default_channel),
        ("weighted.fallback_channel", test_weighted_fallback_channel),
        # Signed
        ("signed.resolve", test_signed_resolve),
        ("signed.default_channel", test_signed_default_channel),
        ("signed.fallback_channel", test_signed_fallback_channel),
        # Typed
        ("typed.resolve", test_typed_resolve),
        ("typed.default_channel", test_typed_default_channel),
        ("typed.fallback_channel", test_typed_fallback_channel),
        # Temporal
        ("temporal.resolve", test_temporal_resolve),
        ("temporal.default_channel", test_temporal_default_channel),
        ("temporal.fallback_channel", test_temporal_fallback_channel),
        # Category
        ("category.resolve", test_category_resolve),
        ("category.default_channel", test_category_default_channel),
        ("category.fallback_channel", test_category_fallback_channel),
        # Size
        ("size.resolve", test_size_resolve),
        ("size.default_channel", test_size_default_channel),
        ("size.fallback_channel", test_size_fallback_channel),
        # Status
        ("status.resolve", test_status_resolve),
        ("status.default_channel", test_status_default_channel),
        ("status.fallback_channel", test_status_fallback_channel),
        # Highlight
        ("highlight.resolve", test_highlight_resolve),
        ("highlight.default_channel", test_highlight_default_channel),
        ("highlight.fallback_channel", test_highlight_fallback_channel),
        # Confidence
        ("confidence.resolve", test_confidence_resolve),
        ("confidence.default_channel", test_confidence_default_channel),
        ("confidence.fallback_channel", test_confidence_fallback_channel),
        # Directional
        ("directional.resolve", test_directional_resolve),
        ("directional.default_channel", test_directional_default_channel),
        ("directional.fallback_none", test_directional_fallback_none),
        # Resolver
        ("resolver.no_conflict", test_resolver_no_conflict),
        ("resolver.three_distinct", test_resolver_three_distinct),
        ("resolver.fallback_kicks_in", test_resolver_fallback_kicks_in),
        ("resolver.raises_on_full_conflict", test_resolver_raises_on_full_conflict),
    ]

    print(f"\n=== Layer 4 · Attribute tests · {len(tests)} cases ===\n")
    for name, fn in tests:
        _run(name, fn)

    print(f"\n---\nPASSED: {len(_PASSED)} / {len(tests)}")
    if _FAILED:
        print(f"FAILED: {len(_FAILED)}")
        for n, msg in _FAILED:
            print(f"  · {n} · {msg}")
        sys.exit(1)
    print("all green.")


if __name__ == "__main__":
    main()
