#!/usr/bin/env python3
"""Invoke the typed cloud MDX-to-PDF capability without local fallback."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


SCRIPT_DIRECTORY = Path(__file__).resolve().parent
if str(SCRIPT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIRECTORY))
from _cloud_runtime import resolve_qwenwork_cli


MAX_INPUT_BYTES = 5 << 20


def resolve_qwenwork(
    script_path: Path | None = None,
    platform_name: str | None = None,
) -> str:
    return resolve_qwenwork_cli(
        script_path=script_path,
        platform_name=platform_name,
        required=True,
    )


def build_command(
    cli: str,
    source: Path,
    output: Path,
    page_size: str,
    title: str,
    no_header: bool,
    no_page_numbers: bool,
) -> list[str]:
    command = [
        cli,
        "tools",
        "document",
        "pdf",
        "generate",
        str(source),
        "--save",
        str(output),
        "--page-size",
        page_size,
        "--deadline",
        "10m",
    ]
    if title:
        command.extend(["--title", title])
    if no_header:
        command.append("--no-header")
    if no_page_numbers:
        command.append("--no-page-numbers")
    return command


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a branded PDF through qwenwork cloud runtime"
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--page-size", choices=("A4", "Letter"), default="A4")
    parser.add_argument("--title", default="")
    parser.add_argument("--no-header", action="store_true")
    parser.add_argument("--no-page-numbers", action="store_true")
    args = parser.parse_args()

    source = args.source.expanduser().resolve()
    if source.suffix.lower() not in {".md", ".mdx"} or not source.is_file():
        parser.error("source must be an existing .md or .mdx file")
    size = source.stat().st_size
    if size < 1 or size > MAX_INPUT_BYTES:
        parser.error("source must be between 1 byte and 5 MiB")
    output = args.output.expanduser().resolve()
    if output.suffix.lower() != ".pdf":
        parser.error("--output must use a .pdf extension")
    if len(args.title.encode("utf-8")) > 256 or any(
        marker in args.title for marker in ("\x00", "\r", "\n")
    ):
        parser.error("--title must be one line of at most 256 bytes")
    output.parent.mkdir(parents=True, exist_ok=True)
    command = build_command(
        resolve_qwenwork(),
        source,
        output,
        args.page_size,
        args.title,
        args.no_header,
        args.no_page_numbers,
    )
    return subprocess.run(command, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
