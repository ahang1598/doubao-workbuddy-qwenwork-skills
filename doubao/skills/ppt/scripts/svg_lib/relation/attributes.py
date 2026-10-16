"""Attribute encoders for relation diagrams.

This module keeps the public Attribute classes and apply pipeline in one place.
Each attribute declares a source field, v1 aliases, a preferred visual channel,
and a fallback channel used by ``resolve_channels`` when channels collide.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Dict, List, Optional, Tuple, Union

from .palettes import Palette


def _first_present(element: dict, field_name: str, aliases: Tuple[str, ...]) -> Any:
    for name in (field_name,) + tuple(aliases):
        if name in element and element[name] is not None:
            return element[name]
    return None


def _float_or_none(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _bool_or_none(value: Any, *, true_words: Tuple[str, ...], false_words: Tuple[str, ...]) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    s = str(value).strip().lower()
    if s in true_words:
        return True
    if s in false_words:
        return False
    return None


# weighted.py
@dataclass
class Weighted:
    """Weighted attribute · 声明 edge 或 node 上的 weight 字段用哪个视觉通道。"""

    field_name: str = "weight"
    v1_aliases: Tuple[str, ...] = ("value",)
    channel: str = "stroke_width"
    fallback_channel: str = "opacity"

    def resolve_value(self, element: dict) -> Optional[float]:
        """从 element dict 里取值 · 支持 v1 alias。"""
        return _float_or_none(_first_present(element, self.field_name, self.v1_aliases))

    def encode(self, value: float, channel: str, palette=None) -> dict:
        """把 value 映射到 SVG attribute · 返回 dict 给 skin 合并。"""
        _ = palette
        if channel == "stroke_width":
            return {"stroke-width": max(1.0, math.sqrt(max(value, 0.0)) * 1.5)}
        if channel == "opacity":
            return {"opacity": max(0.05, min(1.0, 0.3 + value * 0.7))}
        return {}


DEFAULT_WEIGHTED = Weighted()

# signed.py
_SIGNED_SEMANTIC_COLORS = {
    "+": "#16a34a",  # green-600
    "-": "#dc2626",  # red-600
    "=": "#64748b",  # slate-500
}

_SIGNED_ARROW_SHAPES = {
    "+": "triangle",
    "-": "bar",
    "=": "diamond",
}


@dataclass
class Signed:
    """Signed attribute · edge polarity。"""

    field_name: str = "sign"
    v1_aliases: Tuple[str, ...] = ()
    channel: str = "color_semantic"
    fallback_channel: str = "arrow_shape"

    def resolve_value(self, element: dict) -> Optional[str]:
        """从 element dict 里取值 · 归一到 '+/-/='。"""
        raw = _first_present(element, self.field_name, self.v1_aliases)
        if raw is None:
            return None
        v = str(raw).strip().lower()
        if v in ("+", "positive", "pos", "up", "gain"):
            return "+"
        if v in ("-", "negative", "neg", "down", "loss"):
            return "-"
        if v in ("=", "0", "neutral", "flat", "stable"):
            return "="
        if v in _SIGNED_SEMANTIC_COLORS:
            return v
        return None

    def encode(self, value: str, channel: str, palette=None) -> dict:
        _ = palette
        if channel == "color_semantic":
            color = _SIGNED_SEMANTIC_COLORS.get(value, "#64748b")
            return {"stroke": color, "fill": color}
        if channel == "arrow_shape":
            return {"marker-shape": _SIGNED_ARROW_SHAPES.get(value, "triangle")}
        return {}


DEFAULT_SIGNED = Signed()

# typed.py
_TYPED_DASH_PATTERNS = [
    "none",  # solid
    "6 3",  # dashed
    "2 3",  # dotted
    "8 3 2 3",  # dash-dot
    "12 4",  # long dash
    "4 2 2 2 2 2",  # complex
]

_TYPED_ARROW_SHAPES = [
    "triangle",
    "diamond",
    "circle",
    "bar",
    "square",
    "chevron",
]


@dataclass
class Typed:
    """Typed attribute · edge/node 的离散类型。"""

    field_name: str = "type"
    v1_aliases: Tuple[str, ...] = ("kind", "intensity", "sentiment", "role")
    channel: str = "dash_pattern"
    fallback_channel: str = "arrow_shape"

    def resolve_value(self, element: dict) -> Optional[str]:
        raw = _first_present(element, self.field_name, self.v1_aliases)
        return None if raw is None else str(raw)

    def encode(self, value: str, channel: str, palette=None) -> dict:
        _ = palette
        # 通过 hash 稳定映射离散 type 到 index
        idx = abs(hash(value)) % max(len(_TYPED_DASH_PATTERNS), 1)
        if channel == "dash_pattern":
            pattern = _TYPED_DASH_PATTERNS[idx % len(_TYPED_DASH_PATTERNS)]
            if pattern == "none":
                return {"stroke-dasharray": None}
            return {"stroke-dasharray": pattern}
        if channel == "arrow_shape":
            return {"marker-shape": _TYPED_ARROW_SHAPES[idx % len(_TYPED_ARROW_SHAPES)]}
        return {}


DEFAULT_TYPED = Typed()

# temporal.py
_GRADIENT_COLORS = [
    "#1e3a8a",  # blue-900 (old / cold)
    "#3b82f6",  # blue-500
    "#a78bfa",  # violet-400
    "#f472b6",  # pink-400
    "#f97316",  # orange-500 (new / hot)
]


def _phase_to_ratio(phase: Union[str, float, int]) -> float:
    """把 phase 归一到 [0, 1]。字符串按 hash 稳定映射。"""
    if isinstance(phase, (int, float)):
        return max(0.0, min(1.0, float(phase)))
    s = str(phase).strip().lower()
    # 常见 phase keyword
    ordered = [
        "past",
        "old",
        "early",
        "start",
        "begin",
        "initial",
        "mid",
        "middle",
        "recent",
        "current",
        "now",
        "latest",
        "end",
        "final",
    ]
    for i, kw in enumerate(ordered):
        if kw in s:
            return i / max(len(ordered) - 1, 1)
    # fallback: hash → [0, 1]
    return (abs(hash(s)) % 1000) / 999.0


def _interp_color(ratio: float) -> str:
    """线性插值 gradient palette。"""
    ratio = max(0.0, min(1.0, ratio))
    n = len(_GRADIENT_COLORS) - 1
    idx = int(ratio * n)
    # 只做步进色（Phase 0 简化）
    idx = min(idx, n)
    return _GRADIENT_COLORS[idx]


@dataclass
class Temporal:
    """Temporal attribute · phase 或时间区间。"""

    field_name: str = "phase"
    v1_aliases: Tuple[str, ...] = ("t_start", "t_end", "time", "timestamp")
    channel: str = "color_gradient"
    fallback_channel: str = "opacity_gradient"

    def resolve_value(self, element: dict) -> Optional[Union[str, float]]:
        return _first_present(element, self.field_name, self.v1_aliases)

    def encode(self, value, channel: str, palette=None) -> dict:
        _ = palette
        ratio = _phase_to_ratio(value)
        if channel == "color_gradient":
            return {"stroke": _interp_color(ratio), "fill": _interp_color(ratio)}
        if channel == "opacity_gradient":
            # 老 → 淡 · 新 → 浓
            return {"opacity": max(0.2, min(1.0, 0.3 + ratio * 0.7))}
        return {}


DEFAULT_TEMPORAL = Temporal()

# category.py
_DEFAULT_PALETTE = [
    "#2563eb",  # blue-600
    "#dc2626",  # red-600
    "#16a34a",  # green-600
    "#f59e0b",  # amber-500
    "#7c3aed",  # violet-600
    "#0891b2",  # cyan-600
    "#db2777",  # pink-600
    "#65a30d",  # lime-600
]


@dataclass
class Category:
    """Category attribute · 离散分组。"""

    field_name: str = "group"
    v1_aliases: Tuple[str, ...] = ("category", "cluster", "class")
    channel: str = "color_categorical"
    fallback_channel: str = "halo_border"

    def resolve_value(self, element: dict) -> Optional[str]:
        raw = _first_present(element, self.field_name, self.v1_aliases)
        return None if raw is None else str(raw)

    def encode(self, value: str, channel: str, palette=None) -> dict:
        pal = palette if palette else _DEFAULT_PALETTE
        idx = abs(hash(value)) % max(len(pal), 1)
        color = pal[idx]
        if channel == "color_categorical":
            return {"fill": color, "stroke": color}
        if channel == "halo_border":
            return {"halo-color": color, "halo-width": 3}
        return {}


DEFAULT_CATEGORY = Category()


# size.py
@dataclass
class Size:
    """Size attribute · node 尺寸。"""

    field_name: str = "size"
    v1_aliases: Tuple[str, ...] = ("magnitude", "count")
    channel: str = "radius_sqrt"
    fallback_channel: str = "font_size"

    def resolve_value(self, element: dict) -> Optional[float]:
        return _float_or_none(_first_present(element, self.field_name, self.v1_aliases))

    def encode(self, value: float, channel: str, palette=None) -> dict:
        _ = palette
        v = max(value, 0.0)
        if channel == "radius_sqrt":
            # 面积正比 value · r = sqrt(value) * scale + base
            r = math.sqrt(v) * 4.0 + 8.0
            return {"r": r}
        if channel == "font_size":
            # base 12 · scale by sqrt
            fs = 10.0 + math.sqrt(v) * 2.0
            return {"font-size": fs}
        return {}


DEFAULT_SIZE = Size()

# status.py
_RAG_COLORS = {
    "green": "#16a34a",
    "amber": "#f59e0b",
    "red": "#dc2626",
}

_ICON_MAP = {
    "green": "check",
    "amber": "warning",
    "red": "cross",
}


def _normalize_status(v) -> Optional[str]:
    """把各种 status 字符串归一到 red / amber / green。"""
    s = str(v).strip().lower()
    green_set = {"up", "healthy", "pass", "ok", "success", "good", "green", "positive"}
    amber_set = {"stable", "warning", "warn", "wait", "pending", "neutral", "amber", "yellow", "hold"}
    red_set = {"down", "critical", "fail", "failed", "error", "bad", "red", "negative", "danger"}
    if s in green_set:
        return "green"
    if s in amber_set:
        return "amber"
    if s in red_set:
        return "red"
    if s in _RAG_COLORS:
        return s
    return None


@dataclass
class Status:
    """Status attribute · 离散状态 (RAG)。"""

    field_name: str = "status"
    v1_aliases: Tuple[str, ...] = ("trend", "healthy", "tone", "state")
    channel: str = "color_rag"
    fallback_channel: str = "icon"

    def resolve_value(self, element: dict) -> Optional[str]:
        raw = _first_present(element, self.field_name, self.v1_aliases)
        return _normalize_status(raw) if raw is not None else None

    def encode(self, value: str, channel: str, palette=None) -> dict:
        _ = palette
        rag = value if value in _RAG_COLORS else "amber"
        if channel == "color_rag":
            color = _RAG_COLORS[rag]
            return {"fill": color, "stroke": color}
        if channel == "icon":
            return {"icon": _ICON_MAP.get(rag, "circle")}
        return {}


DEFAULT_STATUS = Status()

# highlight.py
_ACCENT_COLOR = "#f97316"  # orange-500
_DIM_COLOR = "#cbd5e1"  # slate-300


@dataclass
class Highlight:
    """Highlight attribute · 高亮聚焦。"""

    field_name: str = "highlight"
    v1_aliases: Tuple[str, ...] = ("focus", "emphasized", "starred")
    channel: str = "opacity_inverse"
    fallback_channel: str = "accent_color"

    def resolve_value(self, element: dict) -> Optional[bool]:
        return _bool_or_none(
            _first_present(element, self.field_name, self.v1_aliases),
            true_words=("true", "1", "yes", "y", "on"),
            false_words=("false", "0", "no", "n", "off", ""),
        )

    def encode(self, value: bool, channel: str, palette=None) -> dict:
        _ = palette
        if channel == "opacity_inverse":
            # 高亮 → 1.0；非高亮 → 0.35
            return {"opacity": 1.0 if value else 0.35}
        if channel == "accent_color":
            if value:
                return {"stroke": _ACCENT_COLOR, "fill": _ACCENT_COLOR, "stroke-width": 3}
            return {"stroke": _DIM_COLOR, "fill": _DIM_COLOR}
        return {}


DEFAULT_HIGHLIGHT = Highlight()


# confidence.py
@dataclass
class Confidence:
    """Confidence attribute · 边/节点的确信度。"""

    field_name: str = "confidence"
    v1_aliases: Tuple[str, ...] = ("certainty", "prob", "probability")
    channel: str = "dash_pattern"
    fallback_channel: str = "opacity"

    def resolve_value(self, element: dict) -> Optional[float]:
        v = _float_or_none(_first_present(element, self.field_name, self.v1_aliases))
        return None if v is None else max(0.0, min(1.0, v))

    def encode(self, value: float, channel: str, palette=None) -> dict:
        _ = palette
        v = max(0.0, min(1.0, value))
        if channel == "dash_pattern":
            if v >= 0.85:
                return {"stroke-dasharray": None}
            if v >= 0.6:
                return {"stroke-dasharray": "8 3"}
            if v >= 0.3:
                return {"stroke-dasharray": "4 3"}
            return {"stroke-dasharray": "2 4"}
        if channel == "opacity":
            return {"opacity": max(0.2, min(1.0, 0.25 + v * 0.75))}
        return {}


DEFAULT_CONFIDENCE = Confidence()


# directional.py
@dataclass
class Directional:
    """Directional attribute · edge 方向性。"""

    field_name: str = "directed"
    v1_aliases: Tuple[str, ...] = ("has_arrow", "is_directed")
    channel: str = "arrow_head_present"
    fallback_channel: str = "none"

    def resolve_value(self, element: dict) -> Optional[bool]:
        return _bool_or_none(
            _first_present(element, self.field_name, self.v1_aliases),
            true_words=("true", "1", "yes", "y", "on", "directed"),
            false_words=("false", "0", "no", "n", "off", "undirected"),
        )

    def encode(self, value: bool, channel: str, palette=None) -> dict:
        _ = palette
        if channel == "arrow_head_present":
            return {"marker-end": "url(#arrowhead)" if value else None}
        if channel == "none":
            return {}
        return {}


DEFAULT_DIRECTIONAL = Directional()


# _resolver.py
def resolve_channels(attrs: List) -> Dict[str, str]:
    """
    attrs: List[Attribute] instances
    return: dict {attribute_class_name: resolved_channel}
    """
    used = set()
    mapping: Dict[str, str] = {}
    for attr in attrs:
        name = attr.__class__.__name__
        chan = getattr(attr, "channel", None)
        fallback = getattr(attr, "fallback_channel", None)

        if chan is None:
            raise ValueError(f"{name} · missing `channel` attribute")

        # "none" fallback 表示没有降级选项 · 允许占用一次
        if chan not in used:
            mapping[name] = chan
            if chan != "none":
                used.add(chan)
        elif fallback and fallback != "none" and fallback not in used:
            mapping[name] = fallback
            used.add(fallback)
        else:
            raise ValueError(f"channel conflict · {name} wants '{chan}' or '{fallback}' · both taken by {sorted(used)}")
    return mapping


# apply.py
def _extract_palette_series(palette: Optional[Palette]) -> Optional[List[str]]:
    """把 Palette dataclass 的 12 色槽抽成一个"分类色系列" · 供 Category 循环。

    顺序：primary → accent → primary_dim → accent_dim → positive → negative
        → ink · gray · 语义次序稳定。返回 None 表示走 Category 的默认色板。
    """
    if palette is None:
        return None
    series = []
    for slot in ("primary", "accent", "primary_dim", "accent_dim", "positive", "negative", "ink", "gray"):
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
    return [apply_attributes(el, attrs, palette=palette, channels=channels) for el in elements]


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


__all__ = [
    "Weighted",
    "Signed",
    "Typed",
    "Temporal",
    "Category",
    "Size",
    "Status",
    "Highlight",
    "Confidence",
    "Directional",
    "resolve_channels",
    "apply_attributes",
    "apply_attributes_batch",
    "svg_style_string",
    "DEFAULT_WEIGHTED",
    "DEFAULT_SIGNED",
    "DEFAULT_TYPED",
    "DEFAULT_TEMPORAL",
    "DEFAULT_CATEGORY",
    "DEFAULT_SIZE",
    "DEFAULT_STATUS",
    "DEFAULT_HIGHLIGHT",
    "DEFAULT_CONFIDENCE",
    "DEFAULT_DIRECTIONAL",
]
