"""Strict, forward-compatible validation for PPTX metadata capabilities."""

from __future__ import annotations

from typing import Any


def _integer(value: object, *, minimum: int = 0) -> bool:
    return type(value) is int and value >= minimum


def _string_list(value: object) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _issues_valid(value: object) -> bool:
    if not isinstance(value, list):
        return False
    for issue in value:
        if not isinstance(issue, dict):
            return False
        if issue.get("severity") != "error" or not isinstance(issue.get("code"), str):
            return False
        if not isinstance(issue.get("message"), str):
            return False
        if "part" in issue and not isinstance(issue["part"], str):
            return False
    return True


def _summary_valid(value: object) -> bool:
    return (
        isinstance(value, dict)
        and _integer(value.get("errors"))
        and type(value.get("truncated")) is bool
    )


def _engine_valid(value: object) -> bool:
    return (
        isinstance(value, dict)
        and isinstance(value.get("name"), str)
        and isinstance(value.get("version"), str)
    )


def _document_valid(value: object, *, slide_count: int | None = None) -> bool:
    if not isinstance(value, dict):
        return False
    count = value.get("slide_count")
    return (
        _integer(count)
        and (slide_count is None or count == slide_count)
        and _integer(value.get("hidden_slide_count"))
        and value["hidden_slide_count"] <= count
        and _integer(value.get("width_emu"))
        and _integer(value.get("height_emu"))
        and _integer(value.get("zip_entries"), minimum=1)
        and _integer(value.get("uncompressed_bytes"), minimum=1)
    )


def _resources_valid(value: object) -> bool:
    required = {"charts", "embeddings", "layouts", "masters", "media", "notes", "themes"}
    return (
        isinstance(value, dict)
        and required <= set(value)
        and all(_integer(value[name]) for name in required)
    )


def _slides_valid(value: object) -> bool:
    if not isinstance(value, list) or len(value) > 300:
        return False
    for expected_index, slide in enumerate(value, start=1):
        if not isinstance(slide, dict) or slide.get("index") != expected_index:
            return False
        if not all(isinstance(slide.get(name), str) for name in ("slide_id", "part", "title")):
            return False
        if type(slide.get("hidden")) is not bool:
            return False
        if not _string_list(slide.get("text")) or not _string_list(slide.get("fonts")):
            return False
        relationships = slide.get("relationships")
        if not isinstance(relationships, dict) or not all(
            isinstance(name, str) and _integer(count)
            for name, count in relationships.items()
        ):
            return False
    return True


def inspection_result_valid(value: Any) -> bool:
    if not isinstance(value, dict) or value.get("schema_version") != "qwenwork.pptx.inspect/v1":
        return False
    slides = value.get("slides")
    return (
        type(value.get("valid")) is bool
        and _slides_valid(slides)
        and _document_valid(value.get("document"), slide_count=len(slides))
        and _resources_valid(value.get("resources"))
        and _issues_valid(value.get("issues"))
        and _summary_valid(value.get("issue_summary"))
        and _engine_valid(value.get("engine"))
        and ("metadata_truncated" not in value or type(value["metadata_truncated"]) is bool)
    )


def validation_result_valid(value: Any) -> bool:
    if not isinstance(value, dict) or value.get("schema_version") != "qwenwork.pptx.validation/v1":
        return False
    if type(value.get("valid")) is not bool:
        return False
    if not _issues_valid(value.get("issues")) or not _summary_valid(value.get("issue_summary")):
        return False
    if not _engine_valid(value.get("engine")):
        return False
    if value["valid"]:
        return _document_valid(value.get("document")) and _resources_valid(value.get("resources"))
    return (
        ("document" not in value or _document_valid(value["document"]))
        and ("resources" not in value or _resources_valid(value["resources"]))
    )
