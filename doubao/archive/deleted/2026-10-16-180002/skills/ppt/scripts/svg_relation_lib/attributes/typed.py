"""
A3 · Typed attribute · categorical type / kind

字段：type (v1 aliases: kind, intensity, sentiment, role)
默认视觉通道：dash_pattern
备用通道：arrow_shape
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple


_DASH_PATTERNS = [
    "none",           # solid
    "6 3",            # dashed
    "2 3",            # dotted
    "8 3 2 3",        # dash-dot
    "12 4",           # long dash
    "4 2 2 2 2 2",    # complex
]

_ARROW_SHAPES = [
    "triangle", "diamond", "circle", "bar", "square", "chevron",
]


@dataclass
class Typed:
    """Typed attribute · edge/node 的离散类型。"""
    field_name: str = "type"
    v1_aliases: Tuple[str, ...] = ("kind", "intensity", "sentiment", "role")
    channel: str = "dash_pattern"
    fallback_channel: str = "arrow_shape"

    def resolve_value(self, element: dict) -> Optional[str]:
        for name in (self.field_name,) + tuple(self.v1_aliases):
            if name in element and element[name] is not None:
                return str(element[name])
        return None

    def encode(self, value: str, channel: str, palette=None) -> dict:
        # 通过 hash 稳定映射离散 type 到 index
        idx = abs(hash(value)) % max(len(_DASH_PATTERNS), 1)
        if channel == "dash_pattern":
            pattern = _DASH_PATTERNS[idx % len(_DASH_PATTERNS)]
            if pattern == "none":
                return {"stroke-dasharray": None}
            return {"stroke-dasharray": pattern}
        if channel == "arrow_shape":
            return {"marker-shape": _ARROW_SHAPES[idx % len(_ARROW_SHAPES)]}
        return {}


DEFAULT_TYPED = Typed()
