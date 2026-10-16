"""Graph schema · v2 · basic nodes and edges for supported relation diagrams.

A Graph is nodes + edges. `directed=True` for DAGs and typed graphs.
Edges carry weight/type/label; nodes carry group/type/size/status.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class Node:
    id: str = ""
    label: str = ""
    # attribute channels
    group: str = ""           # Category
    type: str = ""            # Typed node category
    status: str = ""          # Status marker
    size: float = 0.0         # Size
    weight: float = 0.0
    highlight: bool = False
    role: str = ""            # optional layout role
    # supplemental
    sublabel: str = ""
    detail: str = ""
    x: float = 0.0            # optional manual XY
    y: float = 0.0
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Edge:
    src: str = ""
    dst: str = ""
    label: str = ""
    directed: bool = True
    weight: float = 1.0         # Weighted
    type: str = ""              # Typed
    group: str = ""
    status: str = ""
    highlight: bool = False
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Graph:
    nodes: List[Node] = field(default_factory=list)
    edges: List[Edge] = field(default_factory=list)
    directed: bool = True
    # chrome
    figure_title: str = ""
    figure_caption: str = ""
    source: str = ""
    encoding_note: str = ""
    kicker: str = ""
