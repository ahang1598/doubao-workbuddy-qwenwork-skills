#!/usr/bin/env python3
from __future__ import annotations
"""Check task IDs, dependency references, cycles, and optional rubric coverage."""

import argparse
import json
import sys
from pathlib import Path


def find_cycle(graph):
    visiting: set[str] = set()
    visited: set[str] = set()
    stack: list[str] = []

    def visit(node):
        if node in visiting:
            start = stack.index(node)
            return stack[start:] + [node]
        if node in visited:
            return None
        visiting.add(node)
        stack.append(node)
        for dependency in graph[node]:
            cycle = visit(dependency)
            if cycle:
                return cycle
        stack.pop()
        visiting.remove(node)
        visited.add(node)
        return None

    for node in graph:
        cycle = visit(node)
        if cycle:
            return cycle
    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate TaskPlan IDs, dependencies, cycles, and rubric coverage."
    )
    parser.add_argument("path", type=Path, help="path to TaskPlan JSON")
    args = parser.parse_args()
    try:
        payload = json.loads(args.path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[ERROR] cannot read JSON: {exc}")
        return 1

    tasks = payload.get("tasks") if isinstance(payload, dict) else None
    if not isinstance(tasks, list) or not tasks:
        print("[ERROR] tasks must be a non-empty list")
        return 1

    errors: list[str] = []
    warnings: list[str] = []
    ids: list[str] = []
    for index, task in enumerate(tasks, start=1):
        if not isinstance(task, dict):
            errors.append(f"tasks[{index}] must be an object")
            continue
        task_id = task.get("task_id")
        if not isinstance(task_id, str) or not task_id.strip():
            errors.append(f"tasks[{index}].task_id must be a non-empty string")
        else:
            ids.append(task_id)
        if not isinstance(task.get("title"), str) or not task["title"].strip():
            errors.append(f"tasks[{index}].title must be a non-empty string")
        if not isinstance(task.get("owner"), str) or not task["owner"].strip():
            errors.append(f"{task_id or index}.owner must be a non-empty string or unassigned")
        if task.get("status") not in {"todo", "doing", "submitted", "accepted", "blocked"}:
            errors.append(f"{task_id or index}.status is invalid")
        if not isinstance(task.get("acceptance_criteria"), list) or not task.get(
            "acceptance_criteria"
        ):
            errors.append(
                f"{task_id or f'tasks[{index}]'}.acceptance_criteria must be a non-empty list"
            )
        if not isinstance(task.get("rubric_links", []), list):
            errors.append(f"{task_id or f'tasks[{index}]'}.rubric_links must be a list")
        if not isinstance(task.get("depends_on", []), list):
            errors.append(f"{task_id or f'tasks[{index}]'}.depends_on must be a list")

    duplicates = sorted({task_id for task_id in ids if ids.count(task_id) > 1})
    errors.extend(f"duplicate task_id: {task_id}" for task_id in duplicates)
    known = set(ids)
    graph: dict[str, list[str]] = {task_id: [] for task_id in known}
    for task in tasks:
        if not isinstance(task, dict) or not isinstance(task.get("task_id"), str):
            continue
        dependencies = task.get("depends_on", [])
        if not isinstance(dependencies, list):
            errors.append(f"{task['task_id']}.depends_on must be a list")
            continue
        graph[task["task_id"]] = [dep for dep in dependencies if isinstance(dep, str)]
        for dependency in dependencies:
            if not isinstance(dependency, str):
                errors.append(
                    f"{task['task_id']}.depends_on values must be strings"
                )
                continue
            if dependency not in known:
                errors.append(f"{task['task_id']} depends on missing task {dependency}")

    if not errors:
        cycle = find_cycle(graph)
        if cycle:
            errors.append("dependency cycle: " + " -> ".join(cycle))

    criteria = payload.get("rubric_criteria", [])
    if not isinstance(criteria, list):
        errors.append("rubric_criteria must be a list")
    elif criteria:
        covered = {
            criterion
            for task in tasks
            if isinstance(task, dict)
            for criterion in (
                task.get("rubric_links", [])
                if isinstance(task.get("rubric_links", []), list)
                else []
            )
        }
        uncovered = [criterion for criterion in criteria if criterion not in covered]
        if uncovered:
            warnings.append("uncovered rubric criteria: " + ", ".join(map(str, uncovered)))

    for warning in warnings:
        print(f"[WARN] {warning}")
    if errors:
        for error in errors:
            print(f"[ERROR] {error}")
        return 1
    print(f"VALID task graph: tasks={len(tasks)}, dependencies={sum(len(deps) for deps in graph.values())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
