#!/usr/bin/env python3
"""Inspect one PPTX through the cloud capability with local OOXML fallback."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from _cloud_runtime import (
    CloudRuntimeError,
    cloud_runtime_ready,
    extract_document_tool_metadata,
    run_document_tool,
)
from _execution_route import BackendFailure, execute_with_fallback, execution_mode
from _pptx_package import PackageInvalid, inspect_package
from _result_validation import inspection_result_valid


def _cloud(source: Path) -> dict:
    try:
        payload = run_document_tool(
            ("document", "pptx", "inspect"), source, deadline="5m", timeout_seconds=330,
        )
        return extract_document_tool_metadata(payload)
    except CloudRuntimeError as exc:
        raise BackendFailure(exc.code, fallback_allowed=exc.fallback_allowed) from exc


def _local(source: Path) -> dict:
    try:
        return inspect_package(source)
    except PackageInvalid as exc:
        raise BackendFailure("PPTX_INVALID", fallback_allowed=False, message=str(exc)) from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--pretty", action="store_true")
    parser.add_argument("--diagnostics", action="store_true")
    args = parser.parse_args()
    source = args.input.resolve()
    if not source.is_file() or source.suffix.lower() != ".pptx":
        parser.error("input must be an existing .pptx file")
    try:
        result, report = execute_with_fallback(
            mode=execution_mode(),
            local_ready=lambda: True,
            cloud_ready=cloud_runtime_ready,
            run_local=lambda: _local(source),
            run_cloud=lambda: _cloud(source),
            validate=inspection_result_valid,
        )
    except BackendFailure as exc:
        print(f"Error: {exc.code}: {exc}", file=sys.stderr)
        return 1
    report.emit(enabled=args.diagnostics)
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
