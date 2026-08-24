"""Component package — hard-shape PPTX functions.

Each component lives in its own module under ``components/`` and is
re-exported here. See ``from_scratch.md`` for usage and design intent.

Design provenance: components borrow geometry and field shape from
``dingtalk-x/ai_slides/docs/*.md`` (component specs) and the matching
renderers under ``ai_slides/renderers/*.js``. Each component module
cites its sources in a header docstring so we can refine one-by-one.
"""

from .gantt import add_gantt
from .funnel import add_funnel
from .flow_matrix import add_flow_matrix
from .radar import add_radar
from .swot import add_swot
from .flywheel import add_flywheel
from .metric_card import add_metric_card
from .timeline import add_timeline
from .layered_diagram import add_layered_diagram
from .quote_block import add_quote_block
from .comparison import add_comparison
from .allocation_bars import add_allocation_bars

__all__ = [
    "add_gantt",
    "add_funnel",
    "add_flow_matrix",
    "add_radar",
    "add_swot",
    "add_flywheel",
    "add_metric_card",
    "add_timeline",
    "add_layered_diagram",
    "add_quote_block",
    "add_comparison",
    "add_allocation_bars",
]
