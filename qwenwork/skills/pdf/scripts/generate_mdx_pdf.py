#!/usr/bin/env python3
"""Generate branded PDF from MD/MDX with local-first cloud fallback.

This is the Skill semantic entry.  ``generate_mdx_pdf_cloud.py`` remains the
strict cloud-only adapter used when a caller explicitly requires that backend.
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import shutil
import subprocess
import sys
from pathlib import Path


SCRIPT_DIRECTORY = Path(__file__).resolve().parent
if str(SCRIPT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIRECTORY))
from _cloud_runtime import CloudRuntimeError, resolve_qwenwork_cli, run_document_tool
from _execution_route import BackendFailure
from _semantic_route import execute_semantic_script


CLOUD_MAX_INPUT_BYTES = 5 << 20
MARKDOWN_TO_PDF = SCRIPT_DIRECTORY / "markdown_to_pdf.py"
REPORTLAB_MODULES = ("markdown_it", "reportlab", "pygments", "PIL")
QWENWORK_BRAND_MINIMUM_VERSION = (0, 4, 7)


def _valid_pdf(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size < 5:
        return False
    with path.open("rb") as source:
        return source.read(5) == b"%PDF-"


def _reportlab_ready(source: Path) -> bool:
    return (
        source.suffix.lower() == ".md"
        and MARKDOWN_TO_PDF.is_file()
        and all(importlib.util.find_spec(module) is not None for module in REPORTLAB_MODULES)
    )


def _cloud_compatible(source: Path, *, base_dir: Path | None, components: Path | None) -> bool:
    return (
        source.stat().st_size <= CLOUD_MAX_INPUT_BYTES
        and base_dir is None
        and components is None
    )


def _md2pdf_version(executable: str) -> tuple[int, int, int] | None:
    try:
        result = subprocess.run(
            [executable, "--version"],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    match = re.search(r"(?<!\d)(\d+)\.(\d+)\.(\d+)(?!\d)", result.stdout + result.stderr)
    if match is None:
        return None
    return tuple(int(part) for part in match.groups())


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a branded PDF from Markdown or MDX.")
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--page-size",
        choices=("A4", "Letter"),
        default="A4",
        type=lambda value: value.strip().title(),
    )
    parser.add_argument("--title", default="")
    parser.add_argument("--no-header", action="store_true")
    parser.add_argument("--no-page-numbers", action="store_true")
    parser.add_argument(
        "--base-dir",
        type=Path,
        help="Local md2pdf only: base directory for relative assets.",
    )
    parser.add_argument(
        "--components",
        type=Path,
        help="Local md2pdf only: custom MDX component module.",
    )
    parser.add_argument(
        "--render-profile",
        choices=("auto", "plain", "branded"),
        default="auto",
        help="Backend intent: auto, plain ReportLab, or branded MDX.",
    )
    args = parser.parse_args()

    source = args.source.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if source.suffix.lower() not in {".md", ".mdx"} or not source.is_file():
        parser.error("source must be an existing .md or .mdx file")
    if source.stat().st_size < 1:
        parser.error("source must not be empty")
    if output.suffix.lower() != ".pdf":
        parser.error("--output must use a .pdf extension")
    if len(args.title.encode("utf-8")) > 256 or any(
        marker in args.title for marker in ("\x00", "\r", "\n")
    ):
        parser.error("--title must be one line of at most 256 bytes")
    base_dir = args.base_dir.expanduser().resolve() if args.base_dir else None
    components = args.components.expanduser().resolve() if args.components else None
    if base_dir is not None and not base_dir.is_dir():
        parser.error("--base-dir must be an existing directory")
    if components is not None and not components.is_file():
        parser.error("--components must be an existing file")
    if args.render_profile == "plain" and source.suffix.lower() != ".md":
        parser.error("--render-profile plain requires a .md source")

    def cloud_ready() -> bool:
        if args.render_profile == "plain" or not _cloud_compatible(
            source,
            base_dir=base_dir,
            components=components,
        ):
            return False
        try:
            return resolve_qwenwork_cli(required=False) is not None
        except RuntimeError:
            return False

    def run_cloud() -> Path:
        flags: list[tuple[str, str | None]] = [("page-size", args.page_size)]
        if args.title:
            flags.append(("title", args.title))
        if args.no_header:
            flags.append(("no-header", None))
        if args.no_page_numbers:
            flags.append(("no-page-numbers", None))
        try:
            run_document_tool(
                ("document", "pdf", "generate"),
                source,
                save_path=output,
                flags=tuple(flags),
            )
        except CloudRuntimeError as exc:
            raise BackendFailure(exc.code, retryable=exc.retryable) from exc
        except RuntimeError as exc:
            raise BackendFailure("CLOUD_OPERATION_FAILED", retryable=True) from exc
        return output

    try:
        handled = execute_semantic_script(
            argv=[str(Path(__file__).resolve()), *sys.argv[1:]],
            local_ready=lambda: (
                (args.render_profile != "plain" and shutil.which("md2pdf") is not None)
                or (
                    args.render_profile != "branded"
                    and _reportlab_ready(source)
                )
            ),
            cloud_ready=cloud_ready,
            run_cloud=run_cloud,
            local_result=lambda: output,
            validate=_valid_pdf,
        )
        if handled:
            return 0

        md2pdf = None if args.render_profile == "plain" else shutil.which("md2pdf")
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_name(f".{output.name}.tmp.pdf")
        if md2pdf is not None:
            command = [
                md2pdf, "convert", str(source), "-o", str(temporary),
                "-p", args.page_size,
            ]
            version = _md2pdf_version(md2pdf)
            if version is not None and version < QWENWORK_BRAND_MINIMUM_VERSION:
                command.append("--no-header")
            else:
                command.extend(["--brand", "qwenwork-cn"])
            if args.title:
                command.extend(["--title", args.title])
            if args.no_header and "--no-header" not in command:
                command.append("--no-header")
            if args.no_page_numbers:
                command.append("--no-page-numbers")
            if base_dir is not None:
                command.extend(["--base-dir", str(base_dir)])
            if components is not None:
                command.extend(["--components", str(components)])
        elif args.render_profile != "branded" and _reportlab_ready(source):
            command = [
                sys.executable,
                str(MARKDOWN_TO_PDF),
                str(source),
                "--output",
                str(temporary),
                "--page-size",
                args.page_size.lower(),
                "--engine",
                "reportlab",
            ]
            if args.title:
                command.extend(["--title", args.title])
            if args.no_page_numbers:
                command.append("--no-page-numbers")
        else:
            raise RuntimeError("no compatible local Markdown PDF backend is available")
        result = subprocess.run(command, stdin=subprocess.DEVNULL, timeout=600, check=False)
        if result.returncode != 0 or not _valid_pdf(temporary):
            temporary.unlink(missing_ok=True)
            raise RuntimeError("local md2pdf rendering failed")
        temporary.replace(output)
        return 0
    except (BackendFailure, OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
