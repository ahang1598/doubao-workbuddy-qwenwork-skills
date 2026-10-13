#!/usr/bin/env python3
"""Glossary compliance check for refined-mode review.

Reads a glossary (markdown table or `term -> translation` lines), counts
source-term occurrences in the source file, and verifies the draft uses the
expected target translation. Produces a deterministic report consumed by the
reviewer subagent in Step 4 of the refined workflow.

Zero third-party deps. Python 3.8+.

Usage:
    python3 glossary_check.py \\
        --source path/to/source.md \\
        --draft  path/to/draft.md \\
        --glossary path/to/glossary.md [--glossary path/to/another.md] \\
        [--output path/to/glossary-check.txt]

If --output is omitted, the report is printed to stdout.
Exit code is always 0 (this is a diagnostic, not a gate). The reviewer
subagent decides severity from the report.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass
class GlossaryEntry:
    source_term: str
    target_terms: list[str]  # multiple acceptable translations, separated by / or |
    notes: str = ""
    origin: str = ""  # which glossary file it came from


# ---------- Glossary parsing ----------

_TABLE_ROW = re.compile(r"^\s*\|(.+)\|\s*$")
_TABLE_SEP = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?\s*$")
_ARROW = re.compile(r"\s*(?:->|→|=>)\s*")


def parse_glossary(path: Path) -> list[GlossaryEntry]:
    """Parse a glossary file. Supports two formats:

    1. Markdown table — first two columns are source/target. Third column is notes.
    2. Plain lines — `source -> target` or `source → target` or `source = target`.
    """
    entries: list[GlossaryEntry] = []
    text = path.read_text(encoding="utf-8")

    # Try markdown table first.
    rows = _extract_table_rows(text)
    if rows:
        for cells in rows:
            if len(cells) < 2:
                continue
            source_term = cells[0].strip()
            target_raw = cells[1].strip()
            notes = cells[2].strip() if len(cells) > 2 else ""
            if not source_term or not target_raw:
                continue
            target_terms = [t.strip() for t in re.split(r"[/|]", target_raw) if t.strip()]
            entries.append(GlossaryEntry(source_term, target_terms, notes, str(path)))
        if entries:
            return entries

    # Fall back to line-based.
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("//"):
            continue
        if not _ARROW.search(line):
            continue
        src, tgt = _ARROW.split(line, maxsplit=1)
        src = src.strip().strip("`*_-")
        tgt = tgt.strip().strip("`*_-")
        if not src or not tgt:
            continue
        target_terms = [t.strip() for t in re.split(r"[/|]", tgt) if t.strip()]
        entries.append(GlossaryEntry(src, target_terms, "", str(path)))

    return entries


def _extract_table_rows(text: str) -> list[list[str]]:
    """Extract data rows from the first markdown table found. Returns list of cell lists."""
    lines = text.splitlines()
    rows: list[list[str]] = []
    in_table = False
    header_seen = False

    for i, raw in enumerate(lines):
        if _TABLE_SEP.match(raw) and i > 0 and _TABLE_ROW.match(lines[i - 1]):
            in_table = True
            header_seen = True
            continue
        if in_table:
            m = _TABLE_ROW.match(raw)
            if not m:
                if header_seen and rows:
                    break  # table ended
                in_table = False
                continue
            cells = [c.strip() for c in m.group(1).split("|")]
            rows.append(cells)

    return rows


def merge_glossaries(paths: Iterable[Path]) -> list[GlossaryEntry]:
    """Merge multiple glossaries. Later files override earlier on the same source term."""
    merged: dict[str, GlossaryEntry] = {}
    for p in paths:
        if not p.exists():
            print(f"warning: glossary not found: {p}", file=sys.stderr)
            continue
        for entry in parse_glossary(p):
            merged[entry.source_term.lower()] = entry
    return list(merged.values())


# ---------- Compliance check ----------

@dataclass
class CheckResult:
    entry: GlossaryEntry
    source_hits: int
    draft_hits_by_target: dict[str, int]
    draft_has_source_verbatim: int  # source term appearing untranslated in draft

    @property
    def found(self) -> int:
        return sum(self.draft_hits_by_target.values())

    @property
    def status(self) -> str:
        if self.found == 0 and self.draft_has_source_verbatim > 0:
            return "untranslated"
        if self.found == 0:
            return "missing"
        if self.found < self.source_hits:
            return "under"
        if self.found > self.source_hits:
            return "over"
        return "ok"


def _is_ascii_word(s: str) -> bool:
    return bool(s) and all(ord(c) < 128 for c in s) and re.search(r"[A-Za-z0-9]", s) is not None


def _compile_term(term: str):
    """Precompile a counter for `term`. Word-boundary regex for ASCII terms,
    plain substring for CJK (which has no spaces). Returns a callable
    `(text) -> int`."""
    if not term:
        return lambda _: 0
    if _is_ascii_word(term):
        pattern = re.compile(r"(?<![A-Za-z0-9])" + re.escape(term) + r"(?![A-Za-z0-9])", re.IGNORECASE)
        return lambda text: sum(1 for _ in pattern.finditer(text))
    return lambda text: text.count(term)


def check(source: str, draft: str, entries: list[GlossaryEntry]) -> list[CheckResult]:
    results: list[CheckResult] = []
    for entry in entries:
        count_source = _compile_term(entry.source_term)
        src_hits = count_source(source)
        if src_hits == 0:
            continue
        draft_target_hits = {t: _compile_term(t)(draft) for t in entry.target_terms}
        draft_source_verbatim = count_source(draft)
        results.append(CheckResult(entry, src_hits, draft_target_hits, draft_source_verbatim))
    return results


# ---------- Report ----------

def format_report(results: list[CheckResult]) -> str:
    if not results:
        return "Glossary check: no glossary terms found in source.\n"

    by_status: dict[str, list[CheckResult]] = {}
    for r in results:
        by_status.setdefault(r.status, []).append(r)

    lines: list[str] = []
    lines.append("# Glossary compliance report")
    lines.append("")
    lines.append(f"Terms checked (present in source): {len(results)}")
    summary = ", ".join(
        f"{status}: {len(items)}"
        for status, items in sorted(by_status.items())
    )
    lines.append(f"Summary: {summary}")
    lines.append("")

    severity_order = ["untranslated", "missing", "under", "over", "ok"]
    severity_label = {
        "untranslated": "UNTRANSLATED (source term appears as-is in draft)",
        "missing": "MISSING (no target translation found)",
        "under": "UNDER (fewer target hits than source occurrences)",
        "over": "OVER (more target hits than source occurrences — possible over-translation)",
        "ok": "OK",
    }

    for status in severity_order:
        items = by_status.get(status)
        if not items:
            continue
        lines.append(f"## {severity_label[status]}")
        for r in items:
            targets = " / ".join(r.entry.target_terms)
            target_breakdown = ", ".join(f"{t}: {n}" for t, n in r.draft_hits_by_target.items())
            note = f"  [{r.entry.notes}]" if r.entry.notes else ""
            lines.append(
                f"- `{r.entry.source_term}` → `{targets}`{note}\n"
                f"    source: {r.source_hits}  draft-target: {target_breakdown}"
                + (f"  draft-source-verbatim: {r.draft_has_source_verbatim}" if r.draft_has_source_verbatim else "")
            )
        lines.append("")

    return "\n".join(lines) + "\n"


# ---------- CLI ----------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check draft for glossary compliance.")
    parser.add_argument("--source", required=True, type=Path, help="Source markdown file")
    parser.add_argument("--draft", required=True, type=Path, help="Draft translation file")
    parser.add_argument(
        "--glossary",
        action="append",
        required=True,
        type=Path,
        help="Glossary file (markdown table or term->translation lines). Repeatable.",
    )
    parser.add_argument("--output", type=Path, default=None, help="Write report to this file (default: stdout)")
    args = parser.parse_args(argv)

    source_text = args.source.read_text(encoding="utf-8")
    draft_text = args.draft.read_text(encoding="utf-8")
    entries = merge_glossaries(args.glossary)
    if not entries:
        print("warning: no glossary entries parsed", file=sys.stderr)

    results = check(source_text, draft_text, entries)
    report = format_report(results)

    if args.output:
        resolved = args.output.resolve().absolute()
        allowed = Path.cwd().resolve()
        if not (resolved == allowed or str(resolved).startswith(str(allowed) + os.sep)):
            raise ValueError(f"output path escapes working directory: {resolved}")
        args.output.write_text(report, encoding="utf-8")
    else:
        sys.stdout.write(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
