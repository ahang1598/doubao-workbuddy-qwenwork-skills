#!/usr/bin/env python3
"""Markdown chunker. Splits a markdown file into word-bounded chunks.

Output: writes <output-dir>/chunks/chunk-NN.md (and frontmatter.md when present),
prints a JSON summary to stdout.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from typing import Callable, Iterable, Iterator, List, Tuple, TypeVar

DEFAULT_MAX_WORDS = 5000

T = TypeVar("T")


@dataclass
class Block:
    kind: str
    md: str
    words: int


_CJK_RE = re.compile(r"[一-鿿㐀-䶿豈-﫿]")
_LATIN_RE = re.compile(r"[a-zA-Z0-9]+")
_PUNCT_STRIP_RE = re.compile(r"[#*`\[\]()>|_~\-]")

_FENCE_OPEN_RE = re.compile(r"^( {0,3})(`{3,}|~{3,})")
_ATX_HEADING_RE = re.compile(r"^ {0,3}#{1,6}(\s|$)")
_THEMATIC_BREAK_RE = re.compile(r"^ {0,3}([-_*])(?:[ \t]*\1){2,}[ \t]*$")
_HTML_BLOCK_START_RE = re.compile(r"^ {0,3}<[a-zA-Z!/?]")


def count_words(text: str) -> int:
    cleaned = _PUNCT_STRIP_RE.sub(" ", text)
    return len(_CJK_RE.findall(cleaned)) + len(_LATIN_RE.findall(cleaned))


def extract_frontmatter(content: str) -> Tuple[str, str]:
    lines = content.split("\n")
    if not lines or lines[0] != "---":
        return "", content
    for i in range(1, len(lines)):
        if lines[i] == "---" or lines[i] == "...":
            return "\n".join(lines[: i + 1]), "\n".join(lines[i + 1 :]).lstrip("\n")
    return "", content


def _make_block(kind: str, md: str) -> Block:
    body = md.strip("\n")
    return Block(kind=kind, md=body, words=count_words(body))


def _is_block_starter(line: str) -> bool:
    # HTML start intentionally excluded — would over-split paragraphs containing inline HTML.
    return bool(
        _ATX_HEADING_RE.match(line)
        or _THEMATIC_BREAK_RE.match(line)
        or _FENCE_OPEN_RE.match(line)
    )


def _pack(
    items: Iterable[T],
    weight: Callable[[T], int],
    max_weight: int,
) -> Iterator[Tuple[List[T], int]]:
    """Greedy-pack items into groups; flush when adding the next item would exceed max_weight."""
    buf: List[T] = []
    total = 0
    for item in items:
        w = weight(item)
        if total + w > max_weight and buf:
            yield buf, total
            buf, total = [item], w
        else:
            buf.append(item)
            total += w
    if buf:
        yield buf, total


def parse_markdown(content: str) -> List[Block]:
    if not content.strip():
        return []

    lines = content.split("\n")
    blocks: List[Block] = []
    i, n = 0, len(lines)

    while i < n:
        line = lines[i]
        if not line.strip():
            i += 1
            continue

        m = _FENCE_OPEN_RE.match(line)
        if m:
            fence_char, fence_len = m.group(2)[0], len(m.group(2))
            close_re = re.compile(rf"^ {{0,3}}{re.escape(fence_char)}{{{fence_len},}}[ \t]*$")
            start = i
            i += 1
            while i < n:
                if close_re.match(lines[i]):
                    i += 1
                    break
                i += 1
            blocks.append(_make_block("code", "\n".join(lines[start:i])))
            continue

        if _ATX_HEADING_RE.match(line):
            blocks.append(_make_block("heading", line))
            i += 1
            continue

        if _THEMATIC_BREAK_RE.match(line):
            blocks.append(_make_block("thematicBreak", line))
            i += 1
            continue

        if _HTML_BLOCK_START_RE.match(line):
            start = i
            while i < n and lines[i].strip():
                i += 1
            blocks.append(_make_block("html", "\n".join(lines[start:i])))
            continue

        start = i
        while i < n and lines[i].strip() and not (i > start and _is_block_starter(lines[i])):
            i += 1
        blocks.append(_make_block("flow", "\n".join(lines[start:i])))

    return blocks


def split_into_sections(blocks: List[Block]) -> List[List[Block]]:
    sections: List[List[Block]] = []
    current: List[Block] = []
    for b in blocks:
        if b.kind == "heading" and current:
            sections.append(current)
            current = [b]
        else:
            current.append(b)
    if current:
        sections.append(current)
    return sections


def split_oversized_block(block: Block, max_words: int) -> List[Block]:
    if block.words <= max_words:
        return [block]
    if block.kind in ("heading", "thematicBreak", "html", "code"):
        return [block]

    lines = block.md.split("\n")
    if len(lines) <= 1:
        return [block]

    return [
        _make_block(block.kind, "\n".join(group))
        for group, _ in _pack(lines, count_words, max_words)
    ]


def build_chunks(blocks: List[Block], max_words: int) -> List[Tuple[List[Block], int]]:
    normalized: List[Block] = []
    for section in split_into_sections(blocks):
        section_words = sum(b.words for b in section)
        if section_words <= max_words:
            normalized.append(Block(kind="flow", md="\n\n".join(b.md for b in section), words=section_words))
        else:
            for b in section:
                normalized.extend(split_oversized_block(b, max_words))

    return list(_pack(normalized, lambda b: b.words, max_words))


def chunk_markdown_file(file: str, max_words: int = DEFAULT_MAX_WORDS, output_dir: str = "") -> dict:
    with open(file, "r", encoding="utf-8-sig") as f:
        raw = f.read()

    frontmatter, body = extract_frontmatter(raw)
    chunks = build_chunks(parse_markdown(body), max_words)

    base = output_dir if output_dir else os.path.dirname(file)
    out_dir = os.path.realpath(os.path.join(base, "chunks"))
    allowed_root = os.path.realpath(os.getcwd())
    if not (out_dir == allowed_root or out_dir.startswith(allowed_root + os.sep)):
        raise ValueError(f"output directory escapes working directory: {out_dir}")
    os.makedirs(out_dir, exist_ok=True)

    if frontmatter:
        with open(os.path.join(out_dir, "frontmatter.md"), "w", encoding="utf-8") as f:
            f.write(frontmatter)

    for idx, (group, _) in enumerate(chunks, start=1):
        path = os.path.join(out_dir, f"chunk-{idx:02d}.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n\n".join(b.md for b in group))

    return {
        "source": file,
        "chunks": len(chunks),
        "output_dir": out_dir,
        "frontmatter": bool(frontmatter),
        "words_per_chunk": [w for _, w in chunks],
    }


def _positive_int(value: str) -> int:
    n = int(value)
    if n <= 0:
        raise argparse.ArgumentTypeError(f"must be positive: {value}")
    return n


def build_arg_parser(prog: str) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog=prog,
        description="Split markdown into chunks",
        usage=f"{prog} <file> [--max-words 5000] [--output-dir <dir>]",
    )
    p.add_argument("file", help="Input markdown file")
    p.add_argument("--max-words", type=_positive_int, default=DEFAULT_MAX_WORDS, help="Maximum words per chunk (default: 5000)")
    p.add_argument("--output-dir", default="", help="Write chunks into <dir>/chunks/")
    return p


def run_chunk_cli(argv: List[str], prog: str = "chunk.py") -> int:
    args = build_arg_parser(prog).parse_args(argv)
    result = chunk_markdown_file(args.file, max_words=args.max_words, output_dir=args.output_dir)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(run_chunk_cli(sys.argv[1:], prog=os.path.basename(sys.argv[0]) or "chunk.py"))
