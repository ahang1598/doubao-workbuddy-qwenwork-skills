#!/usr/bin/env python3
"""Flatten PDF widgets and annotations with local-first cloud fallback.

Usage: python scripts/flatten_form.py input.pdf output.pdf
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path


SCRIPT_DIRECTORY = Path(__file__).resolve().parent
if str(SCRIPT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIRECTORY))
from _cloud_runtime import resolve_qwenwork_cli, run_document_tool
from _execution_route import BackendFailure
from _semantic_route import execute_semantic_script


def _valid_pdf(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size < 5:
        return False
    with path.open("rb") as source:
        return source.read(5) == b"%PDF-"


def _flatten_locally(input_path: Path, output_path: Path) -> None:
    import fitz

    document = fitz.open(str(input_path))
    temporary = output_path.with_name(f".{output_path.name}.tmp")
    try:
        if not hasattr(document, "bake"):
            raise RuntimeError("installed PyMuPDF does not support PDF flattening")
        document.bake(annots=True, widgets=True)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        document.save(str(temporary), garbage=4, deflate=True)
    finally:
        document.close()
    temporary.replace(output_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Flatten PDF widgets and annotations.")
    parser.add_argument("input_pdf")
    parser.add_argument("output_pdf")
    args = parser.parse_args()

    input_path = Path(args.input_pdf).expanduser().resolve()
    output_path = Path(args.output_pdf).expanduser().resolve()
    if not input_path.is_file() or input_path.suffix.lower() != ".pdf":
        parser.error("input_pdf must be an existing PDF")
    if output_path.suffix.lower() != ".pdf":
        parser.error("output_pdf must use a .pdf extension")

    def cloud_ready() -> bool:
        try:
            return resolve_qwenwork_cli(required=False) is not None
        except RuntimeError:
            return False

    def run_cloud() -> Path:
        try:
            run_document_tool(
                ("document", "pdf", "flatten-form"),
                input_path,
                save_path=output_path,
            )
        except RuntimeError as exc:
            raise BackendFailure("CLOUD_FORM_FLATTEN_FAILED", retryable=True) from exc
        return output_path

    try:
        handled = execute_semantic_script(
            argv=[str(Path(__file__).resolve()), *sys.argv[1:]],
            local_ready=lambda: importlib.util.find_spec("fitz") is not None,
            cloud_ready=cloud_ready,
            run_cloud=run_cloud,
            local_result=lambda: output_path,
            validate=_valid_pdf,
        )
        if handled:
            return 0
        _flatten_locally(input_path, output_path)
        if not _valid_pdf(output_path):
            raise RuntimeError("local PDF flattening produced an invalid PDF")
        return 0
    except (BackendFailure, OSError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
