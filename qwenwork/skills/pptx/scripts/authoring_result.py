#!/usr/bin/env python3
"""Record or verify the PPT-authoring branch result used by fork-join."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from _pptx_package import validate_package


RESULT_SCHEMA = "qwenwork.pptx.authoring-result/v1"


def _validate_draft(path: Path) -> dict:
    path = path.resolve()
    if not path.is_file() or path.suffix.lower() != ".pptx" or path.stat().st_size == 0:
        raise ValueError("authoring draft is missing, empty, or not a .pptx file")
    validation = validate_package(path)
    slide_count = int(validation.get("document", {}).get("slide_count", 0))
    if validation.get("valid") is not True or slide_count < 1:
        raise ValueError("authoring draft is not an openable non-empty PPTX")
    return {"artifact_path": str(path), "slide_count": slide_count}


def record(draft: Path, build_script: Path, result_path: Path) -> dict:
    build_script = build_script.resolve()
    result_path = result_path.resolve()
    if not build_script.is_file() or build_script.stat().st_size == 0:
        raise ValueError("executed build script is missing or empty")
    artifact = _validate_draft(draft)
    payload = {
        "schema_version": RESULT_SCHEMA,
        "task_id": "ppt:author",
        "status": "ok",
        **artifact,
        "build_script": str(build_script),
        "build_executed": True,
        "validation_passed": True,
        "retryable": False,
        "message": None,
    }
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    return payload


def verify(result_path: Path) -> dict:
    result_path = result_path.resolve()
    if not result_path.is_file():
        raise ValueError("authoring result is missing")
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    if (
        not isinstance(payload, dict)
        or payload.get("schema_version") != RESULT_SCHEMA
        or payload.get("task_id") != "ppt:author"
        or payload.get("status") != "ok"
        or payload.get("build_executed") is not True
        or payload.get("validation_passed") is not True
    ):
        raise ValueError("authoring result contract is incomplete")
    artifact = _validate_draft(Path(str(payload.get("artifact_path", ""))))
    if artifact["slide_count"] != payload.get("slide_count"):
        raise ValueError("authoring result slide count no longer matches the draft")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="operation", required=True)

    record_parser = subparsers.add_parser("record")
    record_parser.add_argument("draft", type=Path)
    record_parser.add_argument("--build-script", type=Path, required=True)
    record_parser.add_argument("--result", type=Path, required=True)

    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("result", type=Path)

    args = parser.parse_args()
    try:
        if args.operation == "record":
            payload = record(args.draft, args.build_script, args.result)
        else:
            payload = verify(args.result)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(
            json.dumps(
                {
                    "schema_version": RESULT_SCHEMA,
                    "status": "invalid",
                    "error": {"message": str(exc)},
                },
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )
        return 1
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
