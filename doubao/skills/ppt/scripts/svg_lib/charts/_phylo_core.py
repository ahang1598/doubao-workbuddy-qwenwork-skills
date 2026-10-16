"""Newick parsing, rooted topology validation and exact branch-length layout."""

from __future__ import annotations

import math

from ._chart_layout import finite


class _NewickParser:
    def __init__(self, source):
        self.source, self.pos = source, 0

    def skip(self):
        while self.pos < len(self.source):
            char = self.source[self.pos]
            if char.isspace():
                self.pos += 1
            elif char == "[":
                depth = 1
                self.pos += 1
                while depth and self.pos < len(self.source):
                    depth += (self.source[self.pos] == "[") - (self.source[self.pos] == "]")
                    self.pos += 1
                if depth:
                    raise ValueError("unterminated Newick comment")
            else:
                break

    def peek(self):
        self.skip()
        return self.source[self.pos] if self.pos < len(self.source) else ""

    def name(self):
        self.skip()
        if self.peek() == "'":
            self.pos += 1
            result = []
            while self.pos < len(self.source):
                char = self.source[self.pos]
                self.pos += 1
                if char == "'":
                    if self.pos < len(self.source) and self.source[self.pos] == "'":
                        result.append("'")
                        self.pos += 1
                    else:
                        return "".join(result)
                else:
                    result.append(char)
            raise ValueError("unterminated quoted Newick name")
        start = self.pos
        while (
            self.pos < len(self.source)
            and self.source[self.pos] not in ":,();[]"
            and not self.source[self.pos].isspace()
        ):
            self.pos += 1
        return self.source[start : self.pos]

    def subtree(self):
        node = {}
        if self.peek() == "(":
            self.pos += 1
            children = [self.subtree()]
            while self.peek() == ",":
                self.pos += 1
                children.append(self.subtree())
            if self.peek() != ")":
                raise ValueError("Newick child list needs a closing parenthesis")
            self.pos += 1
            node["children"] = children
        name = self.name()
        if name:
            node["label"] = name
            if "children" not in node:
                node["id"] = name
        elif "children" not in node:
            raise ValueError("Newick leaves require unique names")
        if self.peek() == ":":
            self.pos += 1
            token = self.name()
            try:
                node["branch_length"] = float(token)
            except ValueError as exc:
                raise ValueError("invalid Newick branch length") from exc
        return node

    def parse(self):
        node = self.subtree()
        if self.peek() == ";":
            self.pos += 1
        if self.peek():
            raise ValueError("unexpected text after Newick tree")
        return node


def normalize_tree(tree, branch_mode="auto", leaf_order=None):
    """Copy/validate topology."""
    if branch_mode not in {"auto", "length", "cladogram"}:
        raise ValueError("branch_mode must be auto, length or cladogram")
    if isinstance(tree, str):
        tree = _NewickParser(tree).parse()
    nodes, seen, objects = [], set(), set()

    def copy(raw, parent=None):
        if not isinstance(raw, dict):
            raise TypeError("tree nodes must be dictionaries or supply Newick text")
        if id(raw) in objects:
            raise ValueError("tree must be acyclic and each node must have exactly one parent")
        objects.add(id(raw))
        children = raw.get("children", [])
        if not isinstance(children, (list, tuple)):
            raise TypeError("children must be a list")
        key = raw.get("id")
        if key is None and children:
            key = f"@internal:{len(nodes)}"
        if not isinstance(key, str) or not key or key in seen:
            raise ValueError("tree nodes require unique nonempty ids; leaves must supply id")
        seen.add(key)
        node = dict(raw, id=key, parent=parent)
        node["label"] = str(raw["label"]) if raw.get("label") is not None else None
        node["category"] = str(raw["category"]) if raw.get("category") is not None else "Nodes"
        node["_sized"] = "size" in raw
        node["size"] = finite(raw["size"], "node size", minimum=0) if raw.get("size") is not None else None
        if raw.get("branch_length") is not None:
            node["branch_length"] = finite(raw["branch_length"], "branch_length", minimum=0)
        if parent is None and (node.get("branch_length") or 0) != 0:
            raise ValueError("root has no incoming edge; root branch_length must be zero or omitted")
        nodes.append(node)
        node["children"] = [copy(child, key) for child in children]
        return node

    root = copy(tree)
    incoming = [node for node in nodes if node["parent"] is not None]
    supplied = sum(node.get("branch_length") is not None for node in incoming)
    mode = branch_mode
    if mode == "auto":
        if supplied and supplied != len(incoming):
            raise ValueError("partial branch lengths are ambiguous; provide all lengths or use branch_mode='cladogram'")
        mode = "length" if supplied else "cladogram"
    if mode == "length" and supplied != len(incoming):
        raise ValueError("branch_mode='length' requires every non-root branch length")
    leaves = [node for node in nodes if not node["children"]]
    original = [node["id"] for node in leaves]
    order = original if leaf_order is None else list(leaf_order)
    if len(order) != len(original) or set(order) != set(original):
        raise ValueError("leaf_order must include every leaf id exactly once")
    ranks = {key: i for i, key in enumerate(order)}

    def resolve(node, distance=0, depth=0):
        length = node.get("branch_length", 0) if mode == "length" else 1
        node["distance"] = distance + length if node["parent"] is not None else 0.0
        node["depth"] = depth
        indices = []
        for child in node["children"]:
            indices.extend(resolve(child, node["distance"], depth + 1))
        if not indices:
            indices = [ranks[node["id"]]]
        if max(indices) - min(indices) + 1 != len(indices):
            raise ValueError("leaf_order must keep each clade contiguous to preserve a planar tree")
        node["leaf_span"] = (min(indices), max(indices))
        node["angle"] = -math.pi / 2 + ((min(indices) + max(indices)) / 2 + 0.5) * math.tau / len(leaves)
        node["children"].sort(key=lambda child: child["leaf_span"][0])
        return indices

    resolve(root)
    maximum = max(node["distance"] for node in nodes)
    if mode == "length" and not maximum and incoming:
        raise ValueError("all branch lengths are zero; use branch_mode='cladogram' to display topology")
    if not math.isfinite(maximum):
        raise ValueError("cumulative branch lengths must remain finite")
    return {
        "root": root,
        "nodes": nodes,
        "leaves": leaves,
        "original_order": original,
        "leaf_order": order,
        "max_distance": maximum,
        "branch_mode": mode,
    }
