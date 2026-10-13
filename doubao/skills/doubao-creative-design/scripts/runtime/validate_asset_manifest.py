#!/usr/bin/env python3
"""Validate the lightweight AI + Coding asset manifest."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


METHODS = {"image_generate", "image_edit", "verified_existing"}
STATUSES = {"planned", "ready", "reused", "rejected"}
TOP_LEVEL_FIELDS = {"brief_snapshot", "assets", "unresolved_blockers"}
SNAPSHOT_FIELDS = {"path", "version", "status"}
ASSET_FIELDS = {
    "asset_id", "purpose", "production_method", "reference_inputs",
    "identity_source", "prompt", "target", "consumers", "acceptance",
    "postprocess", "status", "output",
}
TARGET_FIELDS = {"ratio", "width", "height", "safe_area"}
OUTPUT_FIELDS = {"uri", "width", "height", "version", "alpha"}


def text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def positive(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0


def uri(value: Any) -> bool:
    if not text(value) or value.strip().lower() in {"pending", "tbd", "todo", "placeholder"}:
        return False
    parsed = urlsplit(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def ratio_matches(value: Any, width: Any, height: Any) -> bool:
    if not text(value) or not positive(width) or not positive(height):
        return False
    parts = value.split(":")
    if len(parts) != 2:
        return False
    try:
        ratio_width, ratio_height = (float(part.strip()) for part in parts)
    except ValueError:
        return False
    if not positive(ratio_width) or not positive(ratio_height):
        return False
    return math.isclose(width / height, ratio_width / ratio_height, rel_tol=0.01)


def validate(data: Any, require_ready: bool = False) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["ASSET_MANIFEST_TYPE: top level must be an object"]
    unknown = set(data) - TOP_LEVEL_FIELDS
    if unknown:
        errors.append(f"ASSET_MANIFEST_FIELDS: unsupported top-level fields: {', '.join(sorted(unknown))}")
    snapshot = data.get("brief_snapshot")
    if not isinstance(snapshot, dict) or not all(text(snapshot.get(key)) for key in ("path", "version")):
        errors.append("ASSET_MANIFEST_BRIEF: frozen brief path and version are required")
    else:
        unknown = set(snapshot) - SNAPSHOT_FIELDS
        if unknown:
            errors.append(f"ASSET_MANIFEST_FIELDS: unsupported brief_snapshot fields: {', '.join(sorted(unknown))}")
        if snapshot.get("status") != "frozen":
            errors.append("ASSET_MANIFEST_BRIEF: brief status must be frozen")
    assets = data.get("assets")
    if not isinstance(assets, list) or not assets:
        errors.append("ASSET_MANIFEST_REQUIRED: assets must be a nonempty list")
        assets = []
    seen: set[str] = set()
    for index, item in enumerate(assets):
        path = f"assets[{index}]"
        if not isinstance(item, dict):
            errors.append(f"ASSET_MANIFEST_TYPE: {path} must be an object")
            continue
        unknown = set(item) - ASSET_FIELDS
        if unknown:
            errors.append(f"ASSET_MANIFEST_FIELDS: unsupported {path} fields: {', '.join(sorted(unknown))}")
        asset_id = item.get("asset_id")
        if not text(asset_id) or asset_id in seen:
            errors.append(f"ASSET_MANIFEST_ID: {path}.asset_id must be unique and nonempty")
        elif isinstance(asset_id, str):
            seen.add(asset_id)
        if not text(item.get("purpose")):
            errors.append(f"ASSET_MANIFEST_REQUIRED: {path}.purpose is required")
        method = item.get("production_method")
        if not isinstance(method, str) or method not in METHODS:
            errors.append(f"ASSET_MANIFEST_METHOD: {path}.production_method must be a supported string")
            method = None
        references = item.get("reference_inputs")
        if not isinstance(references, list) or any(not text(value) for value in references):
            errors.append(f"ASSET_MANIFEST_TYPE: {path}.reference_inputs must be a string list")
        if method == "image_edit" and not references:
            errors.append(f"ASSET_MANIFEST_REFERENCE: {path} image_edit requires a reference input")
        if not text(item.get("identity_source")):
            errors.append(f"ASSET_MANIFEST_IDENTITY: {path}.identity_source is required; use 'none' when not applicable")
        if method in {"image_generate", "image_edit"} and not text(item.get("prompt")):
            errors.append(f"ASSET_MANIFEST_PROMPT: {path}.prompt is required")
        target = item.get("target")
        if not isinstance(target, dict) or not text(target.get("ratio")) or not positive(target.get("width")) or not positive(target.get("height")) or not text(target.get("safe_area")):
            errors.append(f"ASSET_MANIFEST_TARGET: {path}.target requires ratio, positive width/height and safe_area")
        elif set(target) - TARGET_FIELDS:
            errors.append(f"ASSET_MANIFEST_FIELDS: unsupported {path}.target fields: {', '.join(sorted(set(target) - TARGET_FIELDS))}")
        elif not ratio_matches(target.get("ratio"), target.get("width"), target.get("height")):
            errors.append(f"ASSET_MANIFEST_RATIO: {path}.target ratio must match width/height")
        for field in ("consumers", "acceptance"):
            value = item.get(field)
            if not isinstance(value, list) or not value or any(not text(entry) for entry in value):
                errors.append(f"ASSET_MANIFEST_REQUIRED: {path}.{field} must be a nonempty string list")
        postprocess = item.get("postprocess")
        if postprocess is not None and (
            not isinstance(postprocess, list) or any(not text(entry) for entry in postprocess)
        ):
            errors.append(f"ASSET_MANIFEST_TYPE: {path}.postprocess must be a string list")
        status = item.get("status")
        if not isinstance(status, str) or status not in STATUSES:
            errors.append(f"ASSET_MANIFEST_STATUS: {path}.status must be a supported string")
            status = None
        if method == "verified_existing" and status not in {"ready", "reused"}:
            errors.append(f"ASSET_MANIFEST_STATUS: {path} verified_existing must already be ready or reused")
        if require_ready and status not in {"ready", "reused"}:
            errors.append(f"ASSET_MANIFEST_READY: {path} is not ready")
        if status in {"ready", "reused"}:
            output = item.get("output")
            if not isinstance(output, dict) or not uri(output.get("uri")) or not positive(output.get("width")) or not positive(output.get("height")) or not text(output.get("version")) or not isinstance(output.get("alpha"), bool):
                errors.append(f"ASSET_MANIFEST_OUTPUT: {path}.output requires uri, width, height, version and boolean alpha")
            elif set(output) - OUTPUT_FIELDS:
                errors.append(f"ASSET_MANIFEST_FIELDS: unsupported {path}.output fields: {', '.join(sorted(set(output) - OUTPUT_FIELDS))}")
    blockers = data.get("unresolved_blockers")
    if not isinstance(blockers, list):
        errors.append("ASSET_MANIFEST_TYPE: unresolved_blockers must be a list")
    elif blockers:
        errors.append("ASSET_MANIFEST_BLOCKERS: unresolved_blockers must be empty")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-ready", action="store_true")
    parser.add_argument("asset_manifest", type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.asset_manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ASSET_MANIFEST_READ: {exc}")
        return 1
    errors = validate(data, args.require_ready)
    if errors:
        print("\n".join(errors))
        return 1
    print(f"PASS asset manifest: {args.asset_manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
