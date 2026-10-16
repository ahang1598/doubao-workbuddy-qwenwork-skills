"""
A8 · Highlight attribute · boolean spotlight

字段：highlight (bool)
默认视觉通道：opacity_inverse (非高亮 dim 到 0.35)
备用通道：accent_color
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple


_ACCENT_COLOR = "#f97316"  # orange-500
_DIM_COLOR = "#cbd5e1"     # slate-300


@dataclass
class Highlight:
    """Highlight attribute · 高亮聚焦。"""
    field_name: str = "highlight"
    v1_aliases: Tuple[str, ...] = ("focus", "emphasized", "starred")
    channel: str = "opacity_inverse"
    fallback_channel: str = "accent_color"

    def resolve_value(self, element: dict) -> Optional[bool]:
        for name in (self.field_name,) + tuple(self.v1_aliases):
            if name in element and element[name] is not None:
                v = element[name]
                if isinstance(v, bool):
                    return v
                s = str(v).strip().lower()
                if s in ("true", "1", "yes", "y", "on"):
                    return True
                if s in ("false", "0", "no", "n", "off", ""):
                    return False
        return None

    def encode(self, value: bool, channel: str, palette=None) -> dict:
        if channel == "opacity_inverse":
            # 高亮 → 1.0；非高亮 → 0.35
            return {"opacity": 1.0 if value else 0.35}
        if channel == "accent_color":
            if value:
                return {"stroke": _ACCENT_COLOR, "fill": _ACCENT_COLOR, "stroke-width": 3}
            return {"stroke": _DIM_COLOR, "fill": _DIM_COLOR}
        return {}


DEFAULT_HIGHLIGHT = Highlight()
