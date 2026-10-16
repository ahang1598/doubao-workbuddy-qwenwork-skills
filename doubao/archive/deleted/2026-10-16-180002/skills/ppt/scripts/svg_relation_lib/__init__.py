"""svg_relation_lib · Relation Atelier v2 API for supported PPT relation diagrams.

Layers 分工：
    Layer 1 · Schema     (svg_relation_lib.schemas)      Tree 与基础 Graph 数据结构
    Layer 2 · Layout     (svg_relation_lib.layouts)      保留图表所需几何算法
    Layer 3 · Skin       (svg_relation_lib.skins)        视觉风格
    Layer 4 · Attribute  (svg_relation_lib.attributes)   可选维度

顶层入口（Phase 4 完整实现）：
    render(schema, layout, skin, attrs, palette, chrome) -> SVG string

Preset 用法（现在可用）：
    from svg_relation_lib.presets.hero_embed_01_AL_fishbone_v2 import build_al_tree
    from svg_relation_lib.schemas import Tree
    data = build_al_tree(effect="X", branches=[...])
"""
from __future__ import annotations

from .palettes import (
    Palette, ALL_PALETTES, get_palette,
    INSTITUTIONAL_WHITE, GS_RESEARCH, HBS_CASE,
    CELL_PRESS, CONSUMER_CHRONICLE,
)
from .engine import Pattern, PatternResult, svg_wrapper
from .chrome import BODY, BODY_DANDELION, BodyBox, top_chrome, bottom_chrome
from .render import render, ChromeConfig

# Schemas
from .schemas import (
    Graph, Node, Edge,
    Tree, TreeNode,
)

# Attributes · 10 attribute + resolver
from .attributes import (
    Weighted, Signed, Typed, Temporal, Category,
    Size, Status, Highlight, Confidence, Directional,
    resolve_channels,
)

__all__ = [
    # Palette
    "Palette", "ALL_PALETTES", "get_palette",
    "INSTITUTIONAL_WHITE", "GS_RESEARCH", "HBS_CASE",
    "CELL_PRESS", "CONSUMER_CHRONICLE",
    # Engine
    "Pattern", "PatternResult", "svg_wrapper",
    # Chrome
    "BODY", "BODY_DANDELION", "BodyBox", "top_chrome", "bottom_chrome",
    # Top-level entry (Phase 4 completes)
    "render", "ChromeConfig",
    # Schemas
    "Graph", "Node", "Edge",
    "Tree", "TreeNode",
    # Attributes
    "Weighted", "Signed", "Typed", "Temporal", "Category",
    "Size", "Status", "Highlight", "Confidence", "Directional",
    "resolve_channels",
]
