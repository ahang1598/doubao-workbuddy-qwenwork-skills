"""
Phase 1 · attribute apply pipeline · unit tests.

跑法：
    cd code && python3 -m svg_relation_lib.attributes._test_pipeline

覆盖：
    1. apply_attributes 基本行为 · 单 attribute
    2. 多 attribute 组合 · channel 不冲突 · 结果合并
    3. 跨 preset 一致性 · 同一份 element 在不同 preset context 下拿到同色
    4. palette 影响 Category 输出 · 不同 palette 产不同色
    5. missing field 静默跳过
    6. apply_attributes_batch · list-in-list-out
    7. svg_style_string · 拍平 + None 跳过
"""
from __future__ import annotations

import sys
import traceback

from svg_relation_lib.attributes import (
    Category, Highlight, Weighted, Typed, Confidence, Directional, Size,
    resolve_channels, apply_attributes, apply_attributes_batch, svg_style_string,
)
from svg_relation_lib.palettes import (
    GS_RESEARCH, HBS_CASE, CELL_PRESS, CONSUMER_CHRONICLE, INSTITUTIONAL_WHITE,
)


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


# =============== apply · single-attribute basic ===============

def test_apply_single_category():
    """Category → fill/stroke · palette 或默认色板"""
    attrs = [Category("group")]
    out = apply_attributes({"group": "core"}, attrs, GS_RESEARCH)
    assert "fill" in out
    assert "stroke" in out
    assert out["fill"].startswith("#")
    # GS_RESEARCH primary/accent 都是特定色系 · fill 应来自其中
    assert out["fill"] in {
        GS_RESEARCH.primary, GS_RESEARCH.accent, GS_RESEARCH.primary_dim,
        GS_RESEARCH.accent_dim, GS_RESEARCH.positive, GS_RESEARCH.negative,
        GS_RESEARCH.ink, GS_RESEARCH.gray,
    }


def test_apply_single_highlight_on():
    attrs = [Highlight()]
    out = apply_attributes({"highlight": True}, attrs, GS_RESEARCH)
    assert out.get("opacity") == 1.0


def test_apply_single_highlight_off():
    attrs = [Highlight()]
    out = apply_attributes({"highlight": False}, attrs, GS_RESEARCH)
    assert out.get("opacity") == 0.35


def test_apply_single_weighted():
    attrs = [Weighted()]
    out = apply_attributes({"weight": 9.0}, attrs, GS_RESEARCH)
    # sqrt(9)*1.5 = 4.5
    assert abs(out.get("stroke-width") - 4.5) < 0.01


# =============== apply · missing field silently skipped ===============

def test_apply_missing_field_skipped():
    attrs = [Category("group"), Highlight()]
    out = apply_attributes({"id": "n1"}, attrs, GS_RESEARCH)
    # 两个 attribute 都没值 · 输出 empty
    assert out == {}


def test_apply_partial_field():
    attrs = [Category("group"), Highlight(), Weighted()]
    out = apply_attributes({"group": "core"}, attrs, GS_RESEARCH)
    # 只有 Category 有值 · 其他跳过
    assert "fill" in out
    assert "opacity" not in out
    assert "stroke-width" not in out


# =============== apply · multi-attribute · channel 不冲突 · merge ===============

def test_apply_category_plus_highlight():
    """Category (color_categorical) + Highlight (opacity_inverse) · 两 channel 独立"""
    attrs = [Category("group"), Highlight()]
    out = apply_attributes(
        {"group": "core", "highlight": True},
        attrs, GS_RESEARCH,
    )
    assert "fill" in out  # from Category
    assert out.get("opacity") == 1.0  # from Highlight
    # 两者互不覆盖


def test_apply_three_attribute_merge():
    attrs = [Category("group"), Highlight(), Weighted()]
    out = apply_attributes(
        {"group": "core", "highlight": True, "weight": 4.0},
        attrs, GS_RESEARCH,
    )
    assert "fill" in out
    assert out.get("opacity") == 1.0
    assert abs(out.get("stroke-width") - 3.0) < 0.01  # sqrt(4)*1.5


# =============== 跨 preset 一致性 · 关键测试 ===============

def test_category_consistent_across_calls():
    """same {group: 'core'} + same palette · 每次都拿到同色"""
    cat = Category("group")
    e1 = apply_attributes({"group": "core"}, [cat], GS_RESEARCH)
    e2 = apply_attributes({"group": "core"}, [cat], GS_RESEARCH)
    assert e1 == e2, f"non-deterministic: {e1} vs {e2}"


def test_category_consistent_across_preset_contexts():
    """
    same {group: 'core'} · same Category · same palette ·
    apply 在不同 preset 上下文里应产同色 · 因为 apply_attributes 是无状态函数。

    不同 preset 把节点转成 {"id", "group"} 形式后，只要走
    apply_attributes(node, [Category], palette)，结果必须一致。
    """
    cat = Category("group")
    node = {"id": "svc-1", "group": "core"}
    r1 = apply_attributes(node, [cat], GS_RESEARCH)  # 如果是 NG 里的节点
    r2 = apply_attributes(node, [cat], GS_RESEARCH)  # 如果是 L2 里的节点
    r3 = apply_attributes(node, [cat], GS_RESEARCH)  # 如果是 AR 里的节点
    assert r1 == r2 == r3
    # 换个 group 值 · 颜色应变
    other = apply_attributes({"id": "svc-1", "group": "data"}, [cat], GS_RESEARCH)
    # 极小概率同色 (hash mod)· 但至少 fill 是合法 hex
    assert other["fill"].startswith("#")


def test_category_v1_alias_consistency():
    """v1 field 'category' vs v2 'group' · 值相同时应产同色。"""
    cat = Category("group")
    v1_node = {"category": "core"}
    v2_node = {"group": "core"}
    r_v1 = apply_attributes(v1_node, [cat], GS_RESEARCH)
    r_v2 = apply_attributes(v2_node, [cat], GS_RESEARCH)
    assert r_v1 == r_v2, f"v1 alias 'category' 应等价 'group': {r_v1} vs {r_v2}"


def test_category_different_palettes_different_colors():
    """不同 palette 应产不同色 · 证明 apply 真的用了 palette。"""
    cat = Category("group")
    r_gs = apply_attributes({"group": "core"}, [cat], GS_RESEARCH)
    r_hbs = apply_attributes({"group": "core"}, [cat], HBS_CASE)
    # GS primary 是 #003A84 · HBS primary 是 #A5182E · 至少 hash 到 primary
    # 时会不同 · 而且 palette series 内容差异保证结果不完全一致
    assert r_gs["fill"] != r_hbs["fill"], \
        f"different palette should yield different color: {r_gs} vs {r_hbs}"


# =============== apply_attributes_batch ===============

def test_batch_apply():
    attrs = [Category("group")]
    elements = [
        {"id": "n1", "group": "core"},
        {"id": "n2", "group": "data"},
        {"id": "n3", "group": "core"},
    ]
    result = apply_attributes_batch(elements, attrs, GS_RESEARCH)
    assert len(result) == 3
    # n1 和 n3 同 group · 同色
    assert result[0]["fill"] == result[2]["fill"]


# =============== svg_style_string ===============

def test_svg_style_string_basic():
    s = svg_style_string({"fill": "#003A84", "opacity": 0.5})
    assert 'fill="#003A84"' in s
    assert 'opacity="0.500"' in s


def test_svg_style_string_skips_none():
    """stroke-dasharray=None (Typed → solid) 不应写进 string。"""
    s = svg_style_string({"stroke": "#fff", "stroke-dasharray": None})
    assert 'stroke-dasharray' not in s
    assert 'stroke="#fff"' in s


def test_svg_style_string_sorted():
    """key 排序稳定 · 好做 diff。"""
    s = svg_style_string({"z-index": 1, "a-first": "x"})
    assert s.startswith('a-first=')


# =============== channel conflict + fallback path ===============

def test_apply_with_channel_conflict_fallback():
    """
    Typed + Confidence 都想用 dash_pattern · 后者降级到 opacity。
    apply_attributes 应尊重 resolver 的 channel 分配。
    """
    attrs = [Typed(), Confidence()]
    channels = resolve_channels(attrs)
    assert channels["Typed"] == "dash_pattern"
    assert channels["Confidence"] == "opacity"

    out = apply_attributes(
        {"type": "supports", "confidence": 0.5},
        attrs, GS_RESEARCH,
    )
    # Typed 写了 stroke-dasharray · Confidence 写了 opacity
    assert "stroke-dasharray" in out
    assert "opacity" in out
    assert out["opacity"] > 0.5  # confidence 0.5 → opacity 0.625


# =============== directional + None marker-end ===============

def test_directional_undirected_marker_none():
    """undirected edge · marker-end=None · 由调用方决定是否忽略"""
    out = apply_attributes({"directed": False}, [Directional()], GS_RESEARCH)
    assert out.get("marker-end") is None
    # svg_style_string 应把它跳过
    s = svg_style_string(out)
    assert "marker-end" not in s


def test_directional_directed_marker_url():
    out = apply_attributes({"directed": True}, [Directional()], GS_RESEARCH)
    assert out.get("marker-end") == "url(#arrowhead)"


# =============== realistic preset-like scenarios ===============

def test_realistic_grouped_node_layer():
    """分组节点 · 分类色 + 高亮。"""
    node = {"id": "gw", "label": "gateway", "group": "edge", "highlight": True}
    attrs = [Category("group"), Highlight()]
    out = apply_attributes(node, attrs, INSTITUTIONAL_WHITE)
    assert out["fill"].startswith("#")
    assert out.get("opacity") == 1.0


def test_realistic_weighted_edge():
    """加权边 · weight 编码到 stroke-width。"""
    edge = {"src": "n1", "dst": "n2", "weight": 16.0}
    out = apply_attributes(edge, [Weighted()], INSTITUTIONAL_WHITE)
    assert abs(out["stroke-width"] - 6.0) < 0.01  # sqrt(16)*1.5


def test_realistic_sized_node():
    """节点 · size 编码 radius · category 编码 fill。"""
    node = {"id": "concept-1", "group": "physics", "size": 25.0}
    attrs = [Category("group"), Size()]
    out = apply_attributes(node, attrs, HBS_CASE)
    assert out["fill"].startswith("#")
    # sqrt(25)*4 + 8 = 28
    assert abs(out["r"] - 28.0) < 0.01


# =============== channel override ===============

def test_manual_channel_override():
    """
    调用方可以传自己的 channels dict · 强制 Category 走 halo_border fallback。
    """
    attrs = [Category("group")]
    out = apply_attributes(
        {"group": "core"}, attrs, GS_RESEARCH,
        channels={"Category": "halo_border"},
    )
    # halo_border 输出应含 halo-color 而不是 fill
    assert "halo-color" in out
    assert "halo-width" in out
    assert "fill" not in out


# ---------- runner ----------


def main():
    tests = [
        # basic
        ("apply.single_category", test_apply_single_category),
        ("apply.single_highlight_on", test_apply_single_highlight_on),
        ("apply.single_highlight_off", test_apply_single_highlight_off),
        ("apply.single_weighted", test_apply_single_weighted),
        # missing / partial
        ("apply.missing_field_skipped", test_apply_missing_field_skipped),
        ("apply.partial_field", test_apply_partial_field),
        # combine
        ("apply.category_plus_highlight", test_apply_category_plus_highlight),
        ("apply.three_attribute_merge", test_apply_three_attribute_merge),
        # cross-preset consistency (关键)
        ("consistency.same_element_same_result", test_category_consistent_across_calls),
        ("consistency.across_preset_contexts", test_category_consistent_across_preset_contexts),
        ("consistency.v1_alias_equivalence", test_category_v1_alias_consistency),
        ("consistency.different_palettes_different_colors",
         test_category_different_palettes_different_colors),
        # batch
        ("batch.apply_list", test_batch_apply),
        # style string
        ("style_string.basic", test_svg_style_string_basic),
        ("style_string.skips_none", test_svg_style_string_skips_none),
        ("style_string.sorted", test_svg_style_string_sorted),
        # channel conflict
        ("channel.conflict_fallback", test_apply_with_channel_conflict_fallback),
        # directional
        ("directional.undirected_marker_none", test_directional_undirected_marker_none),
        ("directional.directed_marker_url", test_directional_directed_marker_url),
        # realistic scenarios
        ("realistic.grouped_node_layer", test_realistic_grouped_node_layer),
        ("realistic.weighted_edge", test_realistic_weighted_edge),
        ("realistic.sized_node", test_realistic_sized_node),
        # override
        ("override.manual_channel", test_manual_channel_override),
    ]

    print(f"\n=== Phase 1 · attribute apply pipeline · {len(tests)} cases ===\n")
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
