#!/usr/bin/env python3
"""Generate the core logic / research-lineage graph for Lark Docs.

This replaces the old development-timeline SVG generator. It emits a single
compact logic graph as a Mermaid whiteboard XML. There is no PNG fallback.

The graph is a *research lineage* map, not a star/radial chart: theme (or
school-of-thought) nodes carry the literature, and *node-to-node* labelled
edges express how the research evolved -- one line inspiring / rebutting /
extending / inheriting from / diverging from another. The core research
question sits at the root, but it is no longer the only place edges converge.

Input JSON schema (required):
{
  "logic_title": "核心逻辑",
  "core_question": "企业数字化转型如何影响组织韧性",
  "nodes": [
    {"id": "M1", "label": "动态能力视角", "evidence": ["R1", "R3"]},
    {"id": "M2", "label": "信息处理视角", "evidence": ["R5"]}
  ],
  "edges": [
    {"source": "core", "target": "M1", "relation": "引出"},
    {"source": "M1", "target": "M2", "relation": "扩展"},
    {"source": "M2", "target": "M1", "relation": "反驳"}
  ]
}

`edges` is required. Inputs without edges, without valid edges, or with only
core-to-node edges fail closed because they would produce a low-information
radial chart instead of a real research-lineage graph.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


RELATION_ENUM = ("引出", "支持", "反驳", "限定", "扩展", "沿用", "分化", "融合", "补充")


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        raise SystemExit(f"missing file: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid JSON: {path} ({exc})")
    if not isinstance(data, dict):
        raise SystemExit(f"JSON must be object: {path}")
    return data


def safe_label(value: Any, fallback: str = "") -> str:
    text = str(value or fallback).strip()
    text = text.replace("\n", " ").replace("\r", " ")
    for char in ("[", "]", "{", "}", "<", ">", "|", "`", '"'):
        text = text.replace(char, " ")
    return " ".join(text.split())[:80]


def mermaid_whiteboard(code: str) -> str:
    theme = """%%{init: {'theme': 'base', 'themeVariables': {
  'fontFamily': 'Inter, Arial, Microsoft YaHei, sans-serif',
  'background': '#FAF9F6',
  'primaryColor': '#E8EEF6',
  'primaryTextColor': '#1F2933',
  'primaryBorderColor': '#2F5D8C',
  'lineColor': '#627D98',
  'secondaryColor': '#E6F0EA',
  'tertiaryColor': '#F4EFE6'
}}}%%"""
    return "<whiteboard type=\"mermaid\">\n" + theme + "\n" + code.strip() + "\n</whiteboard>\n"


def node_label(item: dict[str, Any], fallback: str) -> str:
    """Build a node label that embeds evidence ids so nodes stay traceable."""
    label = safe_label(item.get("label") or item.get("short_title") or item.get("title"), fallback)
    evidence = item.get("evidence")
    if isinstance(evidence, list) and evidence:
        ev = " ".join(safe_label(e) for e in evidence if str(e).strip())
    else:
        ev = safe_label(item.get("evidence_id") or "")
    return f"{label} ({ev})".strip() if ev else label


def _id_map(nodes: list[dict[str, Any]]) -> dict[str, str]:
    """Map author-supplied node ids to safe mermaid ids (N1, N2, ...)."""
    mapping: dict[str, str] = {}
    for index, node in enumerate(nodes, start=1):
        raw = str(node.get("id") or node.get("evidence_id") or f"M{index}").strip()
        mapping[raw] = f"N{index}"
    return mapping


def _resolve(ref: str, id_map: dict[str, str]) -> str:
    ref = str(ref or "").strip()
    if ref.lower() in {"core", "中心", "核心", "根", "root"}:
        return "Core"
    return id_map.get(ref, "")


def logic_graph(data: dict[str, Any]) -> tuple[str, list[str]]:
    warnings: list[str] = []
    title = safe_label(data.get("logic_title") or data.get("title"), "核心逻辑")
    core = safe_label(
        data.get("core_question") or data.get("core") or data.get("research_question"),
        "核心研究问题",
    )
    nodes = data.get("nodes") or data.get("logic_nodes") or []
    if not isinstance(nodes, list) or not nodes:
        warnings.append("logic_graph: no nodes provided")
        nodes = [{"id": "M1", "label": "核心证据", "evidence": ["E1"]}]

    id_map = _id_map(nodes)

    lines = [
        "flowchart TD",
        f"    Title[\"{title}\"]",
        f"    Core[\"{core}\"]",
        "    Title --> Core",
        "    classDef title fill:#F4EFE6,stroke:#9A7B4F,color:#1F2933,stroke-width:1px",
        "    classDef core fill:#E8EEF6,stroke:#2F5D8C,color:#102A43,stroke-width:1.5px",
        "    classDef theme fill:#E6F0EA,stroke:#3B7C6E,color:#1F2933,stroke-width:1px",
        "    class Title title",
        "    class Core core",
    ]

    # Declare all theme/school nodes.
    for node in nodes:
        if not isinstance(node, dict):
            continue
        raw = str(node.get("id") or node.get("evidence_id") or "").strip()
        nid = id_map.get(raw)
        if not nid:
            continue
        lines.append(f"    {nid}[[\"{node_label(node, nid)}\"]]")
        lines.append(f"    class {nid} theme")

    edges = data.get("edges")
    if not isinstance(edges, list) or not edges:
        raise SystemExit("logic_graph: edges are required; radial fallback is forbidden")

    connected: set[str] = set()
    drew_edge = False
    has_lineage_edge = False
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        src = _resolve(edge.get("source") or edge.get("from"), id_map)
        tgt = _resolve(edge.get("target") or edge.get("to"), id_map)
        relation = safe_label(edge.get("relation") or edge.get("label") or "关联")
        if not src or not tgt or src == tgt:
            warnings.append(f"logic_graph: skipped invalid edge {edge!r}")
            continue
        lines.append(f"    {src} -->|{relation}| {tgt}")
        drew_edge = True
        connected.add(src)
        connected.add(tgt)
        if src != "Core" and tgt != "Core":
            has_lineage_edge = True

    if not drew_edge:
        raise SystemExit("logic_graph: no valid edges; provide source/target ids from nodes")
    if not has_lineage_edge:
        raise SystemExit("logic_graph: at least one node-to-node edge is required (e.g. M1 -> M2)")

    # Root any theme node that no edge touched, so nothing floats.
    for raw, nid in id_map.items():
        if nid not in connected:
            lines.append(f"    Core -->|涉及| {nid}")

    return "\n".join(lines), warnings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate the core logic / research-lineage graph whiteboard")
    parser.add_argument("--input", "-i", required=True, help="visuals JSON path")
    parser.add_argument(
        "--output-dir",
        "--output",
        "-o",
        dest="output_dir",
        default=".workflow/figures",
        help="output directory",
    )
    parser.add_argument("--report", default="", help="optional visuals_report.json path")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    data = load_json(Path(args.input))
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    logic_code, logic_warnings = logic_graph(data)
    logic_path = output_dir / "logic_graph.whiteboard.xml"
    logic_path.write_text(mermaid_whiteboard(logic_code), encoding="utf-8")

    payload = {
        "status": "pass",
        "logic_graph": str(logic_path),
        "warnings": logic_warnings,
    }
    report_path = Path(args.report) if args.report else output_dir / "visuals_report.json"
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
