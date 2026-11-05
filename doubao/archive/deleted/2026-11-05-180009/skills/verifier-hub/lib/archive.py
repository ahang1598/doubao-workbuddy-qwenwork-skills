"""archive — ZIP archive inspection (read-only, stdlib only).

2 subcommands
-------------
zip-list           List archive entries with size, kind classification (subset of detect_kind).
zip-check-entries  Assert all expected entry names exist (subset semantics; mode = contains/exact/regex).

Why a dedicated family: GDPval ships a non-trivial number of ".zip with these
files inside" rubrics ("Exactly one top-level ZIP archive ... with WAV stems").
``file artifact-list`` only walks the filesystem, not zip contents; building a
specific zip primitive avoids fragile "extract → walk → cleanup" sequences.
"""
from __future__ import annotations

import argparse
import os
import re
import zipfile
from typing import Any

from . import _common as C

_ZIP_EXTS = (".zip",)


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("zip-list",
                       help="List archive entries (name/size/kind), with optional ext filter.")
    p.add_argument("file")
    p.add_argument("--ext", default=None,
                   help="comma-separated extensions to include (e.g. .wav,.mp3)")
    p.add_argument("--max-entries", type=int, default=200)

    p = sub.add_parser("zip-check-entries",
                       help="Assert all --expected names exist inside the archive.")
    p.add_argument("file")
    p.add_argument("--expected", nargs="+", required=True,
                   help="entry names / patterns to look for")
    p.add_argument("--mode", choices=("contains", "exact", "regex"), default="contains",
                   help="match mode against entry full path inside the archive")
    p.add_argument("--ignore-case", action="store_true")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _open(path: str) -> tuple[zipfile.ZipFile, str]:
    abs_path = C.require_file(path, _ZIP_EXTS)
    if not zipfile.is_zipfile(abs_path):
        raise C.VerifierError(C.ErrCode.PARSE_ERROR,
                              f"file {abs_path} is not a valid ZIP archive")
    try:
        return zipfile.ZipFile(abs_path, "r"), abs_path
    except zipfile.BadZipFile as e:
        raise C.VerifierError(C.ErrCode.PARSE_ERROR,
                              f"BadZipFile({abs_path}): {e}") from e


def _classify(name: str) -> str:
    # Trailing-slash entries are directories.
    if name.endswith("/"):
        return "dir"
    return C.detect_kind(name)


# ---------------------------------------------------------------------------
# zip-list
# ---------------------------------------------------------------------------

def cmd_zip_list(args: argparse.Namespace) -> dict:
    exts: set[str] | None = None
    if args.ext:
        exts = {
            (e if e.startswith(".") else "." + e).lower()
            for e in args.ext.split(",") if e.strip()
        }

    zf, abs_path = _open(args.file)
    entries: list[dict] = []
    summary_kinds: dict[str, int] = {}
    truncated = False
    try:
        for info in zf.infolist():
            ext = os.path.splitext(info.filename)[1].lower()
            if exts is not None and ext not in exts:
                continue
            kind = _classify(info.filename)
            entries.append({
                "name": info.filename,
                "size": info.file_size,
                "compressed": info.compress_size,
                "is_dir": info.is_dir(),
                "kind": kind,
            })
            summary_kinds[kind] = summary_kinds.get(kind, 0) + 1
            if len(entries) >= args.max_entries:
                truncated = True
                break
    finally:
        zf.close()

    summary = ", ".join(f"{k}={v}" for k, v in sorted(summary_kinds.items())) or "(empty)"
    return {
        "file": abs_path,
        "entry_count": len(entries),
        "ext_filter": sorted(exts) if exts else None,
        "truncated": truncated,
        "entries": entries,
        "_evidence": C.evidence(file=abs_path,
                                quote=f"{len(entries)} entries: {summary}"
                                + (" (truncated)" if truncated else "")),
    }


# ---------------------------------------------------------------------------
# zip-check-entries
# ---------------------------------------------------------------------------

def cmd_zip_check_entries(args: argparse.Namespace) -> dict:
    zf, abs_path = _open(args.file)
    try:
        names = [info.filename for info in zf.infolist()]
    finally:
        zf.close()

    if args.ignore_case:
        haystack = [n.lower() for n in names]
        wants = [w.lower() for w in args.expected]
    else:
        haystack = names
        wants = list(args.expected)

    matched: list[dict] = []
    missing: list[str] = []
    for orig, w in zip(args.expected, wants):
        hit_idx: int | None = None
        if args.mode == "exact":
            for i, n in enumerate(haystack):
                if n == w:
                    hit_idx = i
                    break
        elif args.mode == "contains":
            for i, n in enumerate(haystack):
                if w in n:
                    hit_idx = i
                    break
        else:  # regex
            try:
                rx = re.compile(w, re.IGNORECASE if args.ignore_case else 0)
            except re.error as e:
                raise C.VerifierError(C.ErrCode.BAD_ARGS,
                                      f"invalid regex {orig!r}: {e}") from e
            for i, n in enumerate(haystack):
                if rx.search(n):
                    hit_idx = i
                    break
        if hit_idx is None:
            missing.append(orig)
        else:
            matched.append({"expected": orig, "matched_entry": names[hit_idx]})

    passed = not missing
    return {
        "file": abs_path,
        "mode": args.mode,
        "ignore_case": args.ignore_case,
        "entry_count": len(names),
        "expected": args.expected,
        "matched": matched,
        "missing": missing,
        "passed": passed,
        "available_entries_sample": names[:50],
        "_evidence": C.evidence(file=abs_path,
                                quote=f"matched {len(matched)}/{len(args.expected)}"
                                + (f"; missing={missing}" if missing else "")),
    }
