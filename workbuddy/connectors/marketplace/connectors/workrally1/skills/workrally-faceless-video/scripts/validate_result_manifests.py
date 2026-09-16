#!/usr/bin/env python3
"""Validate durable result manifests before the platform upload/report."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


def _is_http_url(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_asset_manifest(payload: Any) -> list[str]:
    errors: list[str] = []
    assets = payload.get("assets") if isinstance(payload, dict) else None
    if not isinstance(assets, list) or not assets:
        return ["asset manifest must contain a non-empty assets array"]
    for index, asset in enumerate(assets, start=1):
        if not isinstance(asset, dict):
            errors.append(f"asset {index} must be an object")
            continue
        for field in ("name", "kind"):
            value = asset.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"asset {index}.{field} is required")
        job_id = asset.get("job_id")
        reused_from_channel_dna = asset.get("reused_from_channel_dna")
        if (
            not isinstance(job_id, str)
            or not job_id.strip()
        ) and reused_from_channel_dna is not True:
            errors.append(
                f"asset {index}.job_id is required unless "
                "reused_from_channel_dna is true"
            )
        if not _is_http_url(asset.get("url")):
            errors.append(f"asset {index}.url must be an absolute HTTP URL")
    return errors


def _validate(script: Any, assets: Any) -> dict[str, Any]:
    errors = _validate_asset_manifest(assets)
    warnings: list[str] = []
    if not isinstance(script, dict):
        errors.append("script manifest must be an object")
        return {"valid": False, "errors": errors, "warnings": warnings}

    sources = script.get("sources")
    if not isinstance(sources, list):
        errors.append("sources must be an array")
    elif any(not _is_http_url(source) for source in sources):
        errors.append("sources must contain only absolute HTTP URLs")

    # Picture Story keeps two deliberately separate manifests. This validator
    # receives the authored script_manifest.json, whose beats are created before
    # any image jobs exist. Frame URLs/job IDs belong to the separate
    # scene_manifest.bound.json and are validated by bind_scene_frame_results.py,
    # materialize_scene_frames.py, and assemble_slides.sh. Do not require or
    # copy runtime frame provenance into the authored script here.

    if "generation_metrics" in script:
        errors.append(
            "generation_metrics is runtime-owned and must not be authored "
            "inside script_manifest.json"
        )
    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--script", required=True, type=Path)
    parser.add_argument("--assets", required=True, type=Path)
    arguments = parser.parse_args()
    try:
        script = _load_json(arguments.script)
        assets = _load_json(arguments.assets)
    except (OSError, json.JSONDecodeError) as error:
        print(
            json.dumps(
                {"valid": False, "errors": [str(error)], "warnings": []},
                ensure_ascii=False,
            )
        )
        return 1

    result = _validate(script, assets)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
