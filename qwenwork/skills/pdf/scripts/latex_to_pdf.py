#!/usr/bin/env python3
"""
latex_to_pdf.py — LaTeX to PDF Converter

Compiles a LaTeX source file to PDF using the Tectonic engine,
which auto-downloads required packages and handles multi-pass compilation.

Usage:
    python scripts/latex_to_pdf.py document.tex --output result.pdf
    python scripts/latex_to_pdf.py document.tex --output result.pdf --keep-logs
    python scripts/latex_to_pdf.py document.tex --output-dir ./build/

Requirements:
    tectonic CLI — see https://tectonic-typesetting.github.io/
    Install: cargo install tectonic  OR  brew install tectonic
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT_DIRECTORY = Path(__file__).resolve().parent
if str(SCRIPT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIRECTORY))
from _cloud_runtime import resolve_qwenwork_cli, run_document_tool
from _execution_route import BackendFailure
from _semantic_route import execute_semantic_script


COMMON_ERRORS = {
    "! LaTeX Error: File": "Missing package — tectonic should auto-fetch it. Check internet connection.",
    "! Undefined control sequence": "Undefined LaTeX command. Check spelling or missing \\usepackage.",
    "! Missing $ inserted": "Math mode error — wrap math in $…$ or \\[…\\].",
    "! Emergency stop": "Fatal LaTeX error — see log for details.",
    "Runaway argument": "Unclosed brace { or bracket [.",
    "No pages of output": "Document produced no output — check \\begin{document} is present.",
}


def _diagnose_log(log_text: str) -> list[str]:
    """Extract likely error causes from a LaTeX log."""
    hints: list[str] = []
    for marker, hint in COMMON_ERRORS.items():
        if marker in log_text:
            hints.append(hint)
    return hints or ["Check the log file for details."]


def compile_latex(tex_path: Path, output_path: Path, keep_logs: bool) -> None:
    if not shutil.which("tectonic"):
        print("=" * 60, file=sys.stderr)
        print("MISSING DEPENDENCY: tectonic", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        print(file=sys.stderr)
        print("LaTeX compilation requires the Tectonic engine.", file=sys.stderr)
        print("Tectonic is a self-contained LaTeX compiler that", file=sys.stderr)
        print("auto-downloads packages — no full TeX Live needed.", file=sys.stderr)
        print(file=sys.stderr)
        print("Install (pick one):", file=sys.stderr)
        if sys.platform == "darwin":
            print("  brew install tectonic          (recommended on macOS)", file=sys.stderr)
        elif sys.platform == "win32":
            print("  scoop install tectonic         (recommended on Windows)", file=sys.stderr)
            print("  choco install tectonic         (alternative on Windows)", file=sys.stderr)
        else:
            print("  # Download from https://tectonic-typesetting.github.io/", file=sys.stderr)
        print("  cargo install tectonic         (any platform with Rust)", file=sys.stderr)
        print("  conda install -c conda-forge tectonic", file=sys.stderr)
        print(file=sys.stderr)
        print("There is NO pure-Python fallback for LaTeX compilation.", file=sys.stderr)
        print("Do NOT attempt to install MacTeX / BasicTeX / texlive —", file=sys.stderr)
        print("these are multi-GB downloads that will time out.", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        sys.exit(1)

    # Run in a temp dir so compilation artifacts don't pollute the source
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Copy source and any sibling files (images, .bib, .cls, etc.)
        src_dir = tex_path.parent
        for f in src_dir.iterdir():
            dest = tmp_path / f.name
            if f.is_file():
                shutil.copy2(str(f), str(dest))

        tmp_tex = tmp_path / tex_path.name

        # --keep-logs is always passed because the compile log is our
        # only diagnostic channel on failure; the *user-facing* --keep-logs
        # flag only controls whether we copy the log next to the output.
        cmd = [
            "tectonic",
            "--outdir", tmp_dir,
            "--keep-logs",
            str(tmp_tex),
        ]
        if os.environ.get("QWENWORK_TECTONIC_OFFLINE", "").strip().lower() in {
            "1", "true", "yes",
        }:
            cmd[1:1] = ["--only-cached", "--untrusted"]

        print(f"Compiling {tex_path.name} with Tectonic…")
        result = subprocess.run(cmd, capture_output=True, text=True)

        log_file = tmp_path / tex_path.with_suffix(".log").name
        log_text = log_file.read_text(encoding="utf-8", errors="replace") if log_file.exists() else ""

        if result.returncode != 0:
            hints = _diagnose_log(log_text)
            print("Compilation failed.", file=sys.stderr)
            print(f"Tectonic stderr:\n{result.stderr.strip()}", file=sys.stderr)
            print("\nPossible causes:", file=sys.stderr)
            for h in hints:
                print(f"  • {h}", file=sys.stderr)
            if keep_logs and log_file.exists():
                dest_log = output_path.with_suffix(".log")
                shutil.copy2(str(log_file), str(dest_log))
                print(f"\nLog saved → {dest_log}", file=sys.stderr)
            sys.exit(1)

        # Move the compiled PDF to the requested output path
        compiled_pdf = tmp_path / tex_path.with_suffix(".pdf").name
        if not compiled_pdf.exists():
            print("Error: tectonic succeeded but no PDF found in output dir.", file=sys.stderr)
            sys.exit(1)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(compiled_pdf), str(output_path))

        if keep_logs and log_file.exists():
            dest_log = output_path.with_suffix(".log")
            shutil.copy2(str(log_file), str(dest_log))
            print(f"Log saved → {dest_log}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compile LaTeX source to PDF via Tectonic.")
    parser.add_argument("tex_file", help="Input .tex file path")
    parser.add_argument("--output", "-o", help="Output PDF path (default: same dir as input)")
    parser.add_argument("--output-dir", help="Output directory (alternative to --output)")
    parser.add_argument("--keep-logs", action="store_true", help="Save compilation log alongside PDF")
    args = parser.parse_args()

    tex_path = Path(args.tex_file)
    if not tex_path.exists():
        print(f"Error: file not found: {tex_path}", file=sys.stderr)
        sys.exit(1)

    if args.output:
        output_path = Path(args.output)
    elif args.output_dir:
        output_path = Path(args.output_dir) / tex_path.with_suffix(".pdf").name
    else:
        output_path = tex_path.with_suffix(".pdf")

    def local_ready() -> bool:
        return shutil.which("tectonic") is not None

    def source_is_self_contained() -> bool:
        try:
            source = tex_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return False
        return re.search(
            r"\\(?:input|include|includegraphics|bibliography|addbibresource)\s*[\[{]",
            source,
        ) is None

    def cloud_ready() -> bool:
        if not source_is_self_contained():
            return False
        try:
            return resolve_qwenwork_cli(required=False) is not None
        except RuntimeError:
            return False

    def run_cloud() -> Path:
        flags = (("keep-logs", None),) if args.keep_logs else ()
        try:
            run_document_tool(
                ("document", "pdf", "generate-latex"),
                tex_path,
                save_path=output_path,
                flags=flags,
            )
        except RuntimeError as exc:
            raise BackendFailure("CLOUD_LATEX_GENERATION_FAILED", retryable=True) from exc
        return output_path

    def valid_pdf(path: Path) -> bool:
        if not path.is_file() or path.stat().st_size < 5:
            return False
        with path.open("rb") as source:
            return source.read(5) == b"%PDF-"

    try:
        handled = execute_semantic_script(
            argv=[str(Path(__file__).resolve()), *sys.argv[1:]],
            local_ready=local_ready,
            cloud_ready=cloud_ready,
            run_cloud=run_cloud,
            local_result=lambda: output_path,
            validate=valid_pdf,
        )
        if handled:
            return
    except BackendFailure as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    compile_latex(tex_path, output_path, keep_logs=args.keep_logs)
    print(f"PDF created → {output_path}")


if __name__ == "__main__":
    main()
