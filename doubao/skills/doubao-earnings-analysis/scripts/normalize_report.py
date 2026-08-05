#!/usr/bin/env python3
"""Normalize final report markdown typography.

Draft reports may use corner quotes 「」/『』 because they are easier for the
model to distinguish from ASCII quotes. This script converts them to standard
Chinese curly quotes for the final markdown deliverable while leaving fenced
code blocks untouched.
"""

from __future__ import annotations

import argparse
from pathlib import Path


QUOTE_TRANSLATION = str.maketrans({
    "「": "“",
    "」": "”",
    "『": "‘",
    "』": "’",
})


def is_fence(line: str) -> bool:
    stripped = line.lstrip()
    return stripped.startswith("```") or stripped.startswith("~~~")


def normalize_markdown(text: str) -> str:
    out: list[str] = []
    in_fence = False
    for line in text.splitlines(keepends=True):
        if is_fence(line):
            out.append(line)
            in_fence = not in_fence
            continue
        if in_fence:
            out.append(line)
        else:
            out.append(line.translate(QUOTE_TRANSLATION))
    return "".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert draft corner quotes in markdown to final Chinese quotes.")
    parser.add_argument("paths", nargs="+", help="Markdown file(s) to normalize in place")
    parser.add_argument("--check", action="store_true", help="Only check whether files need normalization")
    args = parser.parse_args()

    changed: list[Path] = []
    for raw_path in args.paths:
        path = Path(raw_path)
        text = path.read_text(encoding="utf-8")
        normalized = normalize_markdown(text)
        if normalized != text:
            changed.append(path)
            if not args.check:
                path.write_text(normalized, encoding="utf-8")

    for path in changed:
        print(f"{'needs normalization' if args.check else 'normalized'}: {path}")
    return 1 if args.check and changed else 0


if __name__ == "__main__":
    raise SystemExit(main())
