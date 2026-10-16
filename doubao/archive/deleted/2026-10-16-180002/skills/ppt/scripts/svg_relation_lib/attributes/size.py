"""
A6 · Size attribute · node radius / font scale

字段：size (float)
默认视觉通道：radius_sqrt (面积正比 size)
备用通道：font_size
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple
import math


@dataclass
class Size:
    """Size attribute · node 尺寸。"""
    field_name: str = "size"
    v1_aliases: Tuple[str, ...] = ("magnitude", "count")
    channel: str = "radius_sqrt"
    fallback_channel: str = "font_size"

    def resolve_value(self, element: dict) -> Optional[float]:
        for name in (self.field_name,) + tuple(self.v1_aliases):
            if name in element and element[name] is not None:
                try:
                    return float(element[name])
                except (TypeError, ValueError):
                    return None
        return None

    def encode(self, value: float, channel: str, palette=None) -> dict:
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
