"""
A5 · Category attribute · categorical group / cluster

字段：group (v1 alias: category)
默认视觉通道：color_categorical (palette 里循环)
备用通道：halo_border (给 node 加外圈)
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple


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
        for name in (self.field_name,) + tuple(self.v1_aliases):
            if name in element and element[name] is not None:
                return str(element[name])
        return None

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
