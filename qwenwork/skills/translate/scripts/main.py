#!/usr/bin/env python3
"""Translate CLI. Default action splits markdown; explicit `chunk` subcommand also works."""
from __future__ import annotations

import sys

from chunker import run_chunk_cli  # type: ignore[import-not-found]


def main() -> int:
    args = sys.argv[1:]
    prog = "python3 scripts/main.py"
    if args and args[0] == "chunk":
        return run_chunk_cli(args[1:], prog=f"{prog} chunk")
    return run_chunk_cli(args, prog=prog)


if __name__ == "__main__":
    sys.exit(main())
