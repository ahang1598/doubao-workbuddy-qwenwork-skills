#!/usr/bin/env python3
"""Provide stable unpack and pack operations for template-derived PPTX edits."""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

OXML_DIR = Path(__file__).resolve().parent / "oxml"
if str(OXML_DIR) not in sys.path:
    sys.path.insert(0, str(OXML_DIR))

from deck_prune import CleaningRefused, prune_package
from oxml.checks import DeckAuditor
from oxml.kit import repack, unzip_guarded


RESULT_SCHEMA = "qwenwork.pptx.edit-package/v1"


def _result(operation: str, **values) -> dict:
    return {"schema_version": RESULT_SCHEMA, "operation": operation, **values}


def unpack_package(source: Path, destination: Path) -> dict:
    source = source.resolve()
    destination = destination.resolve()
    if not source.is_file() or source.suffix.lower() != ".pptx":
        raise ValueError("input must be an existing .pptx file")
    if destination.exists():
        raise ValueError("unpack destination already exists")
    destination.mkdir(parents=True)
    try:
        with zipfile.ZipFile(source) as archive:
            unzip_guarded(archive, destination)
    except Exception:
        destination.rmdir()
        raise
    return _result(
        "unpack",
        ok=True,
        input=str(source),
        workspace=str(destination),
        next="edit XML, then run pack",
    )


def _audit(unpacked: Path, original: Path | None) -> tuple[bool, str]:
    output = io.StringIO()
    with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
        valid = DeckAuditor(unpacked, original, verbose=False).run_audit()
    return valid, output.getvalue().strip()


def pack_package(
    workspace: Path,
    output: Path,
    *,
    original: Path | None,
    prune: bool,
) -> dict:
    workspace = workspace.resolve()
    output = output.resolve()
    original = original.resolve() if original is not None else None
    if not workspace.is_dir() or not (workspace / "[Content_Types].xml").is_file():
        raise ValueError("workspace must be an unpacked PPTX package")
    if output.suffix.lower() != ".pptx":
        raise ValueError("output must use the .pptx extension")
    if original is not None and (
        not original.is_file() or original.suffix.lower() != ".pptx"
    ):
        raise ValueError("--original must be an existing .pptx file")

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=".pptx-edit-package-", dir=str(output.parent)
    ) as temporary:
        staged = Path(temporary) / "package"
        shutil.copytree(workspace, staged)
        removed = prune_package(staged) if prune else []
        audit_valid, audit_detail = _audit(staged, original)
        if not audit_valid:
            detail = f": {audit_detail}" if audit_detail else ""
            raise ValueError(f"package audit failed; output was not written{detail}")
        repack(staged, output)
    if not output.is_file() or output.stat().st_size == 0:
        raise ValueError("packed output is missing or empty")
    return _result(
        "pack",
        ok=True,
        workspace=str(workspace),
        output=str(output),
        original=str(original) if original is not None else None,
        pruned_parts=len(removed),
        audited=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="operation", required=True)

    unpack_parser = subparsers.add_parser("unpack", help="Safely unpack a PPTX once")
    unpack_parser.add_argument("input", type=Path)
    unpack_parser.add_argument("workspace", type=Path)

    pack_parser = subparsers.add_parser(
        "pack", help="Prune, audit, and atomically pack one edited PPTX"
    )
    pack_parser.add_argument("workspace", type=Path)
    pack_parser.add_argument("output", type=Path)
    pack_parser.add_argument("--original", type=Path)
    pack_parser.add_argument("--no-prune", action="store_true")

    args = parser.parse_args()
    try:
        if args.operation == "unpack":
            result = unpack_package(args.input, args.workspace)
        else:
            result = pack_package(
                args.workspace,
                args.output,
                original=args.original,
                prune=not args.no_prune,
            )
    except (CleaningRefused, OSError, ValueError, zipfile.BadZipFile) as exc:
        print(
            json.dumps(
                _result(args.operation, ok=False, error={"message": str(exc)}),
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )
        return 1
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
