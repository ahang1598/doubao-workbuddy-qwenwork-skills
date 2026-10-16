"""svg_relation_lib.schemas · data containers for supported relation diagrams."""
from __future__ import annotations

from .graph import Edge, Graph, Node
from .tree import Tree, TreeNode

__all__ = [
    # graph
    "Graph", "Node", "Edge",
    # tree
    "Tree", "TreeNode",
]
