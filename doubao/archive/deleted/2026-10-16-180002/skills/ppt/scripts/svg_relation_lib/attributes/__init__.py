"""
Layer 4 · Attribute · 10 可选维度视觉编码

用法：
    from svg_relation_lib.attributes import Category, Highlight, Weighted, resolve_channels
    render(graph, layout, skin, attrs=[Category("group"), Highlight()])

Phase 0 · 声明骨架 · 不改变现有 skin rendering。
真正 apply 到 render pipeline 里要等 Phase 1。
"""
from .weighted import Weighted, DEFAULT_WEIGHTED
from .signed import Signed, DEFAULT_SIGNED
from .typed import Typed, DEFAULT_TYPED
from .temporal import Temporal, DEFAULT_TEMPORAL
from .category import Category, DEFAULT_CATEGORY
from .size import Size, DEFAULT_SIZE
from .status import Status, DEFAULT_STATUS
from .highlight import Highlight, DEFAULT_HIGHLIGHT
from .confidence import Confidence, DEFAULT_CONFIDENCE
from .directional import Directional, DEFAULT_DIRECTIONAL
from ._resolver import resolve_channels
from .apply import apply_attributes, apply_attributes_batch, svg_style_string

__all__ = [
    "Weighted", "Signed", "Typed", "Temporal", "Category",
    "Size", "Status", "Highlight", "Confidence", "Directional",
    "resolve_channels",
    "apply_attributes", "apply_attributes_batch", "svg_style_string",
    "DEFAULT_WEIGHTED", "DEFAULT_SIGNED", "DEFAULT_TYPED",
    "DEFAULT_TEMPORAL", "DEFAULT_CATEGORY", "DEFAULT_SIZE",
    "DEFAULT_STATUS", "DEFAULT_HIGHLIGHT", "DEFAULT_CONFIDENCE",
    "DEFAULT_DIRECTIONAL",
]
