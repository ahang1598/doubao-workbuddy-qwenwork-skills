"""Tree schema · v2 · covers supported tree-style relation diagrams.

A Tree is a rooted hierarchy: exactly one root · each non-root has one parent.
`TreeNode.children` is a list of sub-nodes. `extra` dict carries pattern-specific
payload (verbs, kpi_value, outcome, tag, ...) so factories can round-trip v1 data.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class TreeNode:
    id: str = ""
    label: str = ""
    children: List["TreeNode"] = field(default_factory=list)
    # optional visual/attribute metadata
    group: str = ""            # Category attribute (== v1 `group`)
    type: str = ""             # Typed attribute (== v1 `kind` / `type`)
    status: str = ""           # Status attribute (== v1 `healthy` / `trend` / `outcome`)
    size: float = 0.0          # Size attribute
    weight: float = 0.0        # Weighted attribute
    highlight: bool = False    # Highlight attribute
    sublabel: str = ""         # visual sub-label
    detail: str = ""           # longer description
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Tree:
    root: Optional[TreeNode] = None
    # chrome metadata (kept for v1 compat)
    figure_title: str = ""
    figure_caption: str = ""
    source: str = ""
    encoding_note: str = ""
    kicker: str = ""

    # ─────────────────────── v1 factories ───────────────────────

    @classmethod
    def from_fishbone(
        cls,
        effect: str,
        branches: List[Tuple[str, List[str]]],
        *,
        figure_title: str = "",
        figure_caption: str = "",
        source: str = "",
        encoding_note: str = "",
        kicker: str = "§ ROOT CAUSE · FISHBONE",
    ) -> "Tree":
        """v1 alias · AL_FishboneData(effect, branches) → Tree."""
        root = TreeNode(id="effect", label=effect)
        for i, (cat, subs) in enumerate(branches):
            branch = TreeNode(id=f"b{i}", label=cat, group=cat)
            for j, sub in enumerate(subs):
                branch.children.append(TreeNode(id=f"b{i}_{j}", label=sub, group=cat))
            root.children.append(branch)
        return cls(
            root=root, figure_title=figure_title, figure_caption=figure_caption,
            source=source, encoding_note=encoding_note, kicker=kicker,
        )

    @classmethod
    def from_pyramid(
        cls,
        layers: List[Any],
        *,
        stage_label: str = "",
        pmf_score: str = "",
        figure_title: str = "",
        figure_caption: str = "",
        source: str = "",
        encoding_note: str = "",
        kicker: str = "",
    ) -> "Tree":
        """v1 alias · PMFPyramidData(layers=[PyramidLayer(label, sublabel, detail)])."""
        root = TreeNode(
            id="pyramid",
            label=figure_title or "PYRAMID",
            extra={"stage_label": stage_label, "pmf_score": pmf_score},
        )
        cur = root
        for i, ly in enumerate(layers):
            label = getattr(ly, "label", "") or (ly[0] if isinstance(ly, (tuple, list)) else str(ly))
            sublabel = getattr(ly, "sublabel", "") or ""
            detail = getattr(ly, "detail", "") or ""
            node = TreeNode(
                id=f"L{i}", label=label, sublabel=sublabel, detail=detail,
            )
            cur.children.append(node)
            cur = node  # strict chain
        return cls(
            root=root, figure_title=figure_title, figure_caption=figure_caption,
            source=source, encoding_note=encoding_note, kicker=kicker,
        )

    @classmethod
    def from_bloom(
        cls,
        layers: List[Any],
        *,
        figure_title: str = "",
        figure_caption: str = "",
        source: str = "",
        encoding_note: str = "",
        kicker: str = "§ LEARNING TAXONOMY · BLOOM",
    ) -> "Tree":
        """v1 alias · BL_BloomsPyramidData(layers=[BloomLayer(label, verbs)])."""
        root = TreeNode(id="bloom", label=figure_title or "BLOOM")
        cur = root
        for i, ly in enumerate(layers):
            label = getattr(ly, "label", "") or (ly[0] if isinstance(ly, (tuple, list)) else str(ly))
            verbs = getattr(ly, "verbs", "") or ""
            node = TreeNode(
                id=f"BL{i}", label=label, detail=verbs,
                extra={"verbs": verbs},
            )
            cur.children.append(node)
            cur = node
        return cls(
            root=root, figure_title=figure_title, figure_caption=figure_caption,
            source=source, encoding_note=encoding_note, kicker=kicker,
        )

    @classmethod
    def from_osi(
        cls,
        layers: List[Any],
        *,
        figure_title: str = "",
        figure_caption: str = "",
        source: str = "",
        encoding_note: str = "",
        kicker: str = "§ NETWORK MODEL · OSI 7 LAYERS",
    ) -> "Tree":
        """v1 alias · J1_OSIStackData(layers=[OSILayer(layer_no, short, label, desc)])."""
        root = TreeNode(id="osi", label=figure_title or "OSI")
        cur = root
        for ly in layers:
            layer_no = getattr(ly, "layer_no", 0)
            short = getattr(ly, "short", "")
            label = getattr(ly, "label", "")
            desc = getattr(ly, "desc", "")
            node = TreeNode(
                id=f"L{layer_no}", label=label, sublabel=short, detail=desc,
                group=short,
                extra={"layer_no": layer_no, "short": short, "desc": desc},
            )
            cur.children.append(node)
            cur = node
        return cls(
            root=root, figure_title=figure_title, figure_caption=figure_caption,
            source=source, encoding_note=encoding_note, kicker=kicker,
        )

    @classmethod
    def from_mindmap(
        cls,
        center: str,
        branches: List[Any],
        *,
        figure_title: str = "",
        figure_caption: str = "",
        source: str = "",
        encoding_note: str = "",
        kicker: str = "MIND MAP · IDEATION FAN-OUT",
    ) -> "Tree":
        """v1 alias · MindMapData(center, branches=[MindBranch(label, leaves)])."""
        root = TreeNode(id="center", label=center)
        for i, br in enumerate(branches):
            label = getattr(br, "label", "") or (br[0] if isinstance(br, (tuple, list)) else str(br))
            leaves = getattr(br, "leaves", None) or (br[1] if isinstance(br, (tuple, list)) and len(br) > 1 else [])
            branch = TreeNode(id=f"b{i}", label=label, group=label)
            for j, leaf in enumerate(leaves):
                branch.children.append(TreeNode(id=f"b{i}_{j}", label=leaf, group=label))
            root.children.append(branch)
        return cls(
            root=root, figure_title=figure_title, figure_caption=figure_caption,
            source=source, encoding_note=encoding_note, kicker=kicker,
        )

    @classmethod
    def from_taxonomy(
        cls,
        root_label: str,
        nodes: List[Tuple[str, str]],
        edges: List[Tuple[str, str]],
        *,
        figure_title: str = "",
        figure_caption: str = "",
        source: str = "",
        encoding_note: str = "",
        kicker: str = "§ TAXONOMY · RADIAL DENDROGRAM",
    ) -> "Tree":
        """v1 alias · TaxonomyRadialData(root_label, nodes=[(id, label)], edges=[(parent, child)])."""
        table: Dict[str, TreeNode] = {}
        for nid, nlabel in nodes:
            table[nid] = TreeNode(id=nid, label=nlabel)
        # build parent → children
        child_ids = set()
        for parent_id, child_id in edges:
            if parent_id in table and child_id in table:
                table[parent_id].children.append(table[child_id])
                child_ids.add(child_id)
        # root: whichever is referenced but never a child · else synthesize
        roots = [n for nid, n in table.items() if nid not in child_ids]
        if len(roots) == 1:
            root_node = roots[0]
            if root_label and not root_node.label:
                root_node.label = root_label
        else:
            root_node = TreeNode(id="root", label=root_label, children=roots)
        return cls(
            root=root_node, figure_title=figure_title, figure_caption=figure_caption,
            source=source, encoding_note=encoding_note, kicker=kicker,
        )

    @classmethod
    def from_kpi_cascade(
        cls,
        north_star: Any,
        leading: List[Any],
        lagging: List[List[Any]],
        *,
        figure_title: str = "",
        figure_caption: str = "",
        source: str = "",
        encoding_note: str = "",
        kicker: str = "§ CASCADE · KPI TREE",
    ) -> "Tree":
        """v1 alias · KPICascadeData(north_star, leading[3], lagging[3][3])."""
        def to_node(k: Any, nid: str) -> TreeNode:
            if k is None:
                return TreeNode(id=nid)
            trend = getattr(k, "trend", "")
            healthy = getattr(k, "healthy", True)
            status = trend if trend else ("healthy" if healthy else "warning")
            return TreeNode(
                id=nid,
                label=getattr(k, "label", ""),
                sublabel=getattr(k, "value", ""),
                detail=getattr(k, "formula", ""),
                status=status,
                extra={
                    "value": getattr(k, "value", ""),
                    "trend": trend,
                    "healthy": healthy,
                    "formula": getattr(k, "formula", ""),
                },
            )

        root_node = to_node(north_star, "root")
        for i, lead in enumerate(leading):
            lead_node = to_node(lead, f"L{i}")
            root_node.children.append(lead_node)
            sub_list = lagging[i] if i < len(lagging) else []
            for j, lag in enumerate(sub_list):
                lead_node.children.append(to_node(lag, f"L{i}_{j}"))
        return cls(
            root=root_node, figure_title=figure_title, figure_caption=figure_caption,
            source=source, encoding_note=encoding_note, kicker=kicker,
        )

    @classmethod
    def from_five_why(
        cls,
        root: Any,
        *,
        figure_title: str = "",
        figure_caption: str = "",
        source: str = "",
        encoding_note: str = "",
        kicker: str = "§ 5-WHY ANALYSIS · ROOT CAUSE LADDER",
    ) -> "Tree":
        """v1 alias · E2_FiveWhyData(root=WhyNode(id, label, type, outcome, edge_label, children))."""
        def walk(w: Any) -> TreeNode:
            node = TreeNode(
                id=getattr(w, "id", ""),
                label=getattr(w, "label", ""),
                type=getattr(w, "type", "decision"),
                status=getattr(w, "outcome", "neutral"),
                extra={
                    "edge_label": getattr(w, "edge_label", ""),
                    "outcome": getattr(w, "outcome", "neutral"),
                },
            )
            for c in getattr(w, "children", []) or []:
                node.children.append(walk(c))
            return node

        root_node = walk(root) if root is not None else TreeNode()
        return cls(
            root=root_node, figure_title=figure_title, figure_caption=figure_caption,
            source=source, encoding_note=encoding_note, kicker=kicker,
        )
