"""
A4 · Temporal attribute · phase / time interval

字段：phase: str 或 t_start / t_end
默认视觉通道：color_gradient (温度梯度)
备用通道：opacity_gradient (老 → 淡)
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple, Union


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
    ordered = ["past", "old", "early", "start", "begin", "initial",
               "mid", "middle",
               "recent", "current", "now", "latest", "end", "final"]
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
        # 优先取 phase
        if self.field_name in element and element[self.field_name] is not None:
            return element[self.field_name]
        # 其次 t_start (作为 phase 归一化的输入)
        for name in self.v1_aliases:
            if name in element and element[name] is not None:
                return element[name]
        return None

    def encode(self, value, channel: str, palette=None) -> dict:
        ratio = _phase_to_ratio(value)
        if channel == "color_gradient":
            return {"stroke": _interp_color(ratio), "fill": _interp_color(ratio)}
        if channel == "opacity_gradient":
            # 老 → 淡 · 新 → 浓
            return {"opacity": max(0.2, min(1.0, 0.3 + ratio * 0.7))}
        return {}


DEFAULT_TEMPORAL = Temporal()
