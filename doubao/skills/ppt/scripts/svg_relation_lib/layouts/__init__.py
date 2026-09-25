"""Layer 2 · Layout helpers for supported PPT relation diagrams.

仅保留当前 11 种树状图实际依赖的布局模块：
  bloom_v2 · c4_container_v2 · column_stack · fishbone_v2 ·
  hub_fanout · osi_stack_v2 · vertical_chain

Preset 直接 `from ..layouts.<name>_v2 import ...` (不再统一 re-export).
"""
from __future__ import annotations

__all__: list[str] = []
