#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def fail(message):
    print(f"FAIL: {message}")
    return 1


def main():
    if len(sys.argv) != 2:
        return fail("usage: check_workflow_json.py <workflow.json>")

    path = Path(sys.argv[1])
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return fail(f"JSON parse error: {exc}")

    if isinstance(data, dict) and "nodes" in data:
        nodes = data.get("nodes")
        links = data.get("links", [])
        if not isinstance(nodes, list):
            return fail("UI workflow `nodes` must be a list")
        ids = [node.get("id") for node in nodes if isinstance(node, dict)]
        if len(ids) != len(set(ids)):
            return fail("duplicate node id")
        node_ids = set(ids)
        for node in nodes:
            if not isinstance(node, dict):
                return fail("node must be an object")
            for key in ("id", "type", "pos"):
                if key not in node:
                    return fail(f"node missing `{key}`")
        for link in links:
            if not isinstance(link, list) or len(link) < 6:
                return fail("each UI link must be a list with at least 6 items")
            if link[1] not in node_ids or link[3] not in node_ids:
                return fail(f"link references missing node: {link}")
        print("PASS: UI workflow JSON shape and link references look valid")
        return 0

    if isinstance(data, dict):
        for node_id, node in data.items():
            if not isinstance(node, dict):
                return fail(f"API node {node_id} must be an object")
            if "class_type" not in node:
                return fail(f"API node {node_id} missing `class_type`")
            if "inputs" not in node:
                return fail(f"API node {node_id} missing `inputs`")
        print("PASS: API prompt JSON shape looks valid")
        return 0

    return fail("workflow root must be an object")


if __name__ == "__main__":
    raise SystemExit(main())
