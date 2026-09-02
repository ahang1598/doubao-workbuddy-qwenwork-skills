#!/usr/bin/env python3
"""Render a DOCX to page PNGs with LibreOffice and pdftoppm."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from skill_paths import generated_path


def run(command: list[str], env: dict | None = None) -> None:
    result = subprocess.run(command, text=True, capture_output=True, env=env)
    if result.returncode:
        raise SystemExit(
            f"command failed ({result.returncode}): {' '.join(command)}\n"
            f"{result.stdout}\n{result.stderr}"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("docx", type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--emit-pdf", action="store_true")
    parser.add_argument("--dpi", type=int, default=140)
    args = parser.parse_args()

    if not args.docx.exists():
        raise SystemExit(f"missing input: {args.docx}")
    soffice = shutil.which("soffice")
    pdftoppm = shutil.which("pdftoppm")
    if not soffice or not pdftoppm:
        raise SystemExit("soffice and pdftoppm are required")

    output_dir = generated_path(args.output_dir, "render output directory")
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="docx-render-") as temp:
        temp_dir = Path(temp)
        profile = temp_dir / "profile"
        profile.mkdir()
        env = os.environ.copy()
        env["HOME"] = str(profile)
        env["TMPDIR"] = str(temp_dir)
        run(
            [
                soffice,
                f"-env:UserInstallation=file://{profile}",
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                str(temp_dir),
                str(args.docx.resolve()),
            ],
            env,
        )
        pdf = temp_dir / f"{args.docx.stem}.pdf"
        if not pdf.exists():
            candidates = list(temp_dir.glob("*.pdf"))
            if not candidates:
                raise SystemExit("LibreOffice did not create a PDF")
            pdf = candidates[0]
        run(
            [
                pdftoppm,
                "-png",
                "-r",
                str(args.dpi),
                str(pdf),
                str(output_dir / "page"),
            ]
        )
        if args.emit_pdf:
            shutil.copy2(pdf, output_dir / f"{args.docx.stem}.pdf")

    pages = sorted(output_dir.glob("page-*.png"))
    if not pages:
        raise SystemExit("no page images were rendered")
    print(f"rendered {len(pages)} page(s) to {output_dir}")


if __name__ == "__main__":
    main()
