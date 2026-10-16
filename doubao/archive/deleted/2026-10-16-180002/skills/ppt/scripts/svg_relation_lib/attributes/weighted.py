"""
A1 · Weighted attribute · edge weight / node value

字段：weight (v1 alias: value)
默认视觉通道：stroke_width = sqrt(weight) * scale
备用通道：opacity
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Tuple
import math


@dataclass
class Weighted:
    """Weighted attribute · 声明 edge 或 node 上的 weight 字段用哪个视觉通道。"""
    field_name: str = "weight"
    v1_aliases: Tuple[str, ...] = ("value",)
    channel: str = "stroke_width"
    fallback_channel: str = "opacity"

    def resolve_value(self, element: dict) -> Optional[float]:
        """从 element dict 里取值 · 支持 v1 alias。"""
        for name in (self.field_name,) + tuple(self.v1_aliases):
            if name in element and element[name] is not None:
                try:
                    return float(element[name])
                except (TypeError, ValueError):
                    return None
        return None

    def encode(self, value: float, channel: str, palette=None) -> dict:
        """把 value 映射到 SVG attribute · 返回 dict 给 skin 合并。"""
        if channel == "stroke_width":
            return {"stroke-width": max(1.0, math.sqrt(max(value, 0.0)) * 1.5)}
        if channel == "opacity":
            return {"opacity": max(0.05, min(1.0, 0.3 + value * 0.7))}
        return {}


DEFAULT_WEIGHTED = Weighted()
