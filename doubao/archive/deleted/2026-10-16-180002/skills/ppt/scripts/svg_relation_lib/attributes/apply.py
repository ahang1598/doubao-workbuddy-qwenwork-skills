"""
Attribute apply pipeline · Phase 1.

将 attribute list apply 到单个 element (node / edge dict) · 得到一份
SVG attribute dict · 可直接 merge 到 SVG rect / circle / line 的属性上。

用法：
    from svg_relation_lib.attributes import Category, Highlight, resolve_channels
    from svg_relation_lib.attributes.apply import apply_attributes
    from svg_relation_lib.palettes import GS_RESEARCH

    attrs = [Category("group"), Highlight()]
    node  = {"id": "n1", "group": "core", "highlight": True}
    svg_attrs = apply_attributes(node, attrs, GS_RESEARCH)
    # → {"fill": "#003A84", "stroke": "#003A84", "opacity": 1.0}

设计要点：
    1. 输入 element 是普通 dict · 不做 dataclass 限制 (Phase 0 已确认 v1
       aliases 用 dict[key] 取值)
    2. channels 参数可选 · 缺省时用 resolve_channels(attrs) 自动定位。
       调用方可以自己传 channels · 例如 preset 想强制某个 attribute
       走 fallback。
    3. palette 参数直接透传到每个 attribute.encode(value, channel, palette) ·
       目前只有 Category 真的看 palette (取 primary/accent 等色槽)。
    4. Later-write-wins · 相同 key 后声明的 attribute 会覆盖前面的。这与
       resolve_channels 的顺序语义一致：先声明的 attribute 占默认 channel ·
       后声明的走 fallback · 通常两者不会写同一 svg attribute · 但如果
       写了（例如两个都写 "stroke"）· 语义是"后者赢"。

铁律：
    * 本 pipeline 不修改当前 11 个 relation preset 的 render 代码 · 只是一个可选的
      apply 通道 · 供 examples/attribute_demo.py 演示使用。
    * cross_verify.py / verify_golden.py 必须继续通过。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..palettes import Palette
from ._resolver import resolve_channels


def _extract_palette_series(palette: Optional[Palette]) -> Optional[List[str]]:
    """把 Palette dataclass 的 12 色槽抽成一个"分类色系列" · 供 Category 循环。

    顺序：primary → accent → primary_dim → accent_dim → positive → negative
        → ink · gray · 语义次序稳定。返回 None 表示走 Category 的默认色板。
    """
    if palette is None:
        return None
    series = []
    for slot in ("primary", "accent", "primary_dim", "accent_dim",
                 "positive", "negative", "ink", "gray"):
        v = getattr(palette, slot, None)
        if isinstance(v, str) and v.startswith("#"):
            series.append(v)
    return series or None


def apply_attributes(
    element: Dict[str, Any],
    attrs: List,
    palette: Optional[Palette] = None,
    channels: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Apply 全部 attrs 到 element · 返回 svg attribute dict。

    Args:
        element:  普通 dict · 至少要含 attribute 声明的 field_name (或 v1 alias)。
                  缺失时对应 attribute 静默跳过。
        attrs:    List[Attribute] · 顺序影响 channel 分配 (resolve_channels)。
        palette:  Palette · 影响 Category 的分类色系列。可省略。
        channels: 可选 · {attribute_class_name: resolved_channel} · 若为 None
                  则自动 resolve_channels(attrs)。

    Returns:
        dict · 例如 {"fill": "#003A84", "opacity": 1.0, "stroke-width": 3.0}。
        对 `None` 值的 svg attribute 也保留 (例如 stroke-dasharray=None 表示
        实线) · 由调用方决定要不要写进 svg。
    """
    if channels is None:
        channels = resolve_channels(attrs)

    # Category attribute 想用 palette 的分类色系列 · 事前抽好传进去
    series = _extract_palette_series(palette)

    result: Dict[str, Any] = {}
    for attr in attrs:
        name = attr.__class__.__name__
        value = attr.resolve_value(element)
        if value is None:
            continue
        channel = channels.get(name, getattr(attr, "channel", None))
        if channel is None:
            continue
        # 只有 Category 真的用 palette · 其他 attribute 目前忽略 palette 参数
        if name == "Category":
            svg = attr.encode(value, channel, palette=series)
        else:
            svg = attr.encode(value, channel, palette=palette)
        if not svg:
            continue
        result.update(svg)
    return result


def apply_attributes_batch(
    elements: List[Dict[str, Any]],
    attrs: List,
    palette: Optional[Palette] = None,
) -> List[Dict[str, Any]]:
    """Convenience · 批量 apply · 只 resolve 一次 channel · 返回 list[svg_dict]。"""
    channels = resolve_channels(attrs)
    return [apply_attributes(el, attrs, palette=palette, channels=channels)
            for el in elements]


def svg_style_string(svg_attrs: Dict[str, Any]) -> str:
    """把 apply_attributes 的输出拍平成一个 SVG attribute string ·
    形如: fill="#003A84" opacity="1.0" stroke-width="3.0"

    * None 值跳过 (SVG 语义上表示"不设置")
    * 数字保留最多 3 位小数
    """
    parts = []
    for k in sorted(svg_attrs.keys()):
        v = svg_attrs[k]
        if v is None:
            continue
        if isinstance(v, float):
            parts.append(f'{k}="{v:.3f}"')
        else:
            parts.append(f'{k}="{v}"')
    return " ".join(parts)
