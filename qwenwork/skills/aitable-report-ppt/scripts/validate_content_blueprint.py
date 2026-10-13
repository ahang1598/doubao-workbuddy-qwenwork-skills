#!/usr/bin/env python3
"""Validate the report storyline/content blueprint and its overall approval."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


APPROVED_SCOPES = {"story", "key_messages", "slide_allocation", "chart_plan"}


def read_json(path: Path, errors: list[str], label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        errors.append(f"cannot read {label}: {error}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"{label} must be a JSON object")
        return {}
    return value


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_blueprint(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    report = data.get("report") if isinstance(data.get("report"), dict) else {}
    story = data.get("story") if isinstance(data.get("story"), dict) else {}
    slides = data.get("slides") if isinstance(data.get("slides"), list) else []
    for field in ("title", "purpose", "audience", "delivery_type", "density"):
        if not nonempty(report.get(field)):
            errors.append(f"report.{field} is required")
    for field in ("core_message", "narrative", "estimated_slide_count"):
        if story.get(field) in (None, "", []):
            errors.append(f"story.{field} is required")
    if not isinstance(story.get("chapters"), list) or not story.get("chapters"):
        errors.append("story.chapters must contain the proposed chapter sequence")
    if not slides:
        errors.append("slides must contain the page-by-page content list")
    seen: set[str] = set()
    for index, slide in enumerate(slides):
        base = f"slides[{index}]"
        if not isinstance(slide, dict):
            errors.append(f"{base} must be an object")
            continue
        for field in ("id", "title", "management_question", "key_message"):
            if not nonempty(slide.get(field)):
                errors.append(f"{base}.{field} is required")
        slide_id = slide.get("id")
        if slide_id in seen:
            errors.append(f"duplicate slide id: {slide_id}")
        if isinstance(slide_id, str):
            seen.add(slide_id)
        if not isinstance(slide.get("body_points"), list):
            errors.append(f"{base}.body_points must be an array")
        if not isinstance(slide.get("source_refs"), list) or not slide.get("source_refs"):
            errors.append(f"{base}.source_refs must contain evidence references")
        charts = slide.get("charts", [])
        if not isinstance(charts, list):
            errors.append(f"{base}.charts must be an array")
        else:
            for chart_index, chart in enumerate(charts):
                cbase = f"{base}.charts[{chart_index}]"
                if not isinstance(chart, dict):
                    errors.append(f"{cbase} must be an object")
                    continue
                for field in ("type", "title", "data_summary", "metric_ids"):
                    if chart.get(field) in (None, "", []):
                        errors.append(f"{cbase}.{field} is required")
    expected = story.get("estimated_slide_count")
    if isinstance(expected, int) and expected != len(slides):
        errors.append(f"story.estimated_slide_count={expected} but slides has {len(slides)} items")
    return errors


def validate_approval(blueprint_path: Path, approval: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in ("status", "approved_at", "approval_source", "blueprint_path", "blueprint_sha256"):
        if not approval.get(field):
            errors.append(f"approval.{field} is required")
    if approval.get("status") != "approved":
        errors.append("approval.status must equal approved")
    actual_hash = sha256(blueprint_path)
    if approval.get("blueprint_sha256") and approval.get("blueprint_sha256") != actual_hash:
        errors.append("approval blueprint_sha256 does not match the current content blueprint")
    scopes = set(approval.get("approved_scope") or [])
    missing = APPROVED_SCOPES - scopes
    if missing:
        errors.append(f"approval.approved_scope is missing: {', '.join(sorted(missing))}")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("blueprint")
    parser.add_argument("--approval")
    parser.add_argument("--output")
    args = parser.parse_args()
    blueprint_path = Path(args.blueprint).resolve()
    errors: list[str] = []
    blueprint = read_json(blueprint_path, errors, "content blueprint")
    if blueprint:
        errors.extend(validate_blueprint(blueprint))
    if args.approval:
        approval = read_json(Path(args.approval).resolve(), errors, "content approval")
        if approval and blueprint_path.exists():
            errors.extend(validate_approval(blueprint_path, approval))
    result = {"valid": not errors, "errors": errors, "blueprint_sha256": sha256(blueprint_path) if blueprint_path.exists() else None}
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    print(text)
    sys.exit(0 if not errors else 1)


if __name__ == "__main__":
    main()
