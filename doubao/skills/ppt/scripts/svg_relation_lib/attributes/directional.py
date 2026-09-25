"""
A10 · Directional attribute · edge directed / undirected

字段：directed (bool · edge-level)
默认视觉通道：arrow_head_present (是否画箭头)
备用通道：none (Phase 0 无 fallback · 因为方向性没别的表达方式)
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class Directional:
    """Directional attribute · edge 方向性。"""
    field_name: str = "directed"
    v1_aliases: Tuple[str, ...] = ("has_arrow", "is_directed")
    channel: str = "arrow_head_present"
    fallback_channel: str = "none"

    def resolve_value(self, element: dict) -> Optional[bool]:
        for name in (self.field_name,) + tuple(self.v1_aliases):
            if name in element and element[name] is not None:
                v = element[name]
                if isinstance(v, bool):
                    return v
                s = str(v).strip().lower()
                if s in ("true", "1", "yes", "y", "on", "directed"):
                    return True
                if s in ("false", "0", "no", "n", "off", "undirected"):
                    return False
        return None

    def encode(self, value: bool, channel: str, palette=None) -> dict:
        if channel == "arrow_head_present":
            return {"marker-end": "url(#arrowhead)" if value else None}
        if channel == "none":
            return {}
        return {}


DEFAULT_DIRECTIONAL = Directional()
