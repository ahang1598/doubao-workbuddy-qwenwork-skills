#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def split_extra_args(argv: list[str]) -> tuple[list[str], list[str]]:
    if "--" not in argv:
        return argv, []
    index = argv.index("--")
    return argv[:index], argv[index + 1 :]


def run(cmd: list[str]) -> None:
    try:
        subprocess.run(cmd, check=True)
    except FileNotFoundError:
        print("Pandoc executable not found. Install Pandoc or add it to PATH.", file=sys.stderr)
        raise SystemExit(127)
    except subprocess.CalledProcessError as error:
        raise SystemExit(error.returncode)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Convert DOCX to Markdown with Pandoc.")
    parser.add_argument("input", help="Input DOCX file")
    parser.add_argument("-o", "--output", help="Output Markdown path. Default: INPUT.md")
    parser.add_argument("--media-dir", default="./assets", help="Directory for extracted media. Default: ./assets")
    parser.add_argument("--to", dest="to_format", default="gfm", help="Pandoc output format. Default: gfm")
    parser.add_argument("--wrap", dest="wrap_mode", default="none", help="Pandoc wrapping mode. Default: none")
    return parser


def main(argv: list[str]) -> int:
    parser_argv, extra_args = split_extra_args(argv)
    args = build_parser().parse_args(parser_argv)

    input_path = Path(args.input).expanduser()
    if not input_path.is_file():
        print(f"Input file not found: {input_path}", file=sys.stderr)
        return 1

    output_path = Path(args.output).expanduser() if args.output else input_path.with_suffix(".md")

    run(
        [
            "pandoc",
            str(input_path),
            "-t",
            args.to_format,
            "-o",
            str(output_path),
            f"--extract-media={args.media_dir}",
            f"--wrap={args.wrap_mode}",
            *extra_args,
        ]
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
