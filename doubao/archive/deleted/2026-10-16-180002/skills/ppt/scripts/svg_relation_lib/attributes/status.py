"""
A7 · Status attribute · discrete state (RAG semantic)

字段：status ∈ {up/down/stable, healthy/warning/critical, pass/fail/wait}
v1 aliases: trend, healthy, tone
默认视觉通道：color_rag (red / amber / green)
备用通道：icon
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple


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
        for name in (self.field_name,) + tuple(self.v1_aliases):
            if name in element and element[name] is not None:
                normalized = _normalize_status(element[name])
                if normalized is not None:
                    return normalized
        return None

    def encode(self, value: str, channel: str, palette=None) -> dict:
        rag = value if value in _RAG_COLORS else "amber"
        if channel == "color_rag":
            color = _RAG_COLORS[rag]
            return {"fill": color, "stroke": color}
        if channel == "icon":
            return {"icon": _ICON_MAP.get(rag, "circle")}
        return {}


DEFAULT_STATUS = Status()
