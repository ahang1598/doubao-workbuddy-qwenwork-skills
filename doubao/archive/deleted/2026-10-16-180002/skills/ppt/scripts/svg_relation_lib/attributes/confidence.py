"""
A9 · Confidence attribute · certainty in [0, 1]

字段：confidence (float 0-1)
默认视觉通道：dash_pattern (低 confidence → 虚线)
备用通道：opacity
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class Confidence:
    """Confidence attribute · 边/节点的确信度。"""
    field_name: str = "confidence"
    v1_aliases: Tuple[str, ...] = ("certainty", "prob", "probability")
    channel: str = "dash_pattern"
    fallback_channel: str = "opacity"

    def resolve_value(self, element: dict) -> Optional[float]:
        for name in (self.field_name,) + tuple(self.v1_aliases):
            if name in element and element[name] is not None:
                try:
                    v = float(element[name])
                    return max(0.0, min(1.0, v))
                except (TypeError, ValueError):
                    return None
        return None

    def encode(self, value: float, channel: str, palette=None) -> dict:
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
