"""
A2 · Signed attribute · positive / negative / neutral polarity

字段：sign ∈ {'+', '-', '='}
默认视觉通道：color_semantic (green / red / gray)
备用通道：arrow_shape
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple


_SEMANTIC_COLORS = {
    "+": "#16a34a",   # green-600
    "-": "#dc2626",   # red-600
    "=": "#64748b",   # slate-500
}

_ARROW_SHAPES = {
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
        for name in (self.field_name,) + tuple(self.v1_aliases):
            if name in element and element[name] is not None:
                v = str(element[name]).strip().lower()
                if v in ("+", "positive", "pos", "up", "gain"):
                    return "+"
                if v in ("-", "negative", "neg", "down", "loss"):
                    return "-"
                if v in ("=", "0", "neutral", "flat", "stable"):
                    return "="
                if v in _SEMANTIC_COLORS:
                    return v
        return None

    def encode(self, value: str, channel: str, palette=None) -> dict:
        if channel == "color_semantic":
            color = _SEMANTIC_COLORS.get(value, "#64748b")
            return {"stroke": color, "fill": color}
        if channel == "arrow_shape":
            return {"marker-shape": _ARROW_SHAPES.get(value, "triangle")}
        return {}


DEFAULT_SIGNED = Signed()
