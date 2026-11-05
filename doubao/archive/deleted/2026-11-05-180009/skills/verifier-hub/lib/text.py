"""text — text/markdown content checks (no third-party deps).

9 subcommands
-------------
must-contain        all/any/none of --terms appear in --file (literal or regex).
must-not-contain    NONE of --terms appear (banned-keyword check).
count-matches       count occurrences of one regex; report sample positions.
section-length      length of an MD section under a regex'd heading; min/max thresholds.
lang-ratio          CJK-character ratio in a file (CJK / total non-whitespace).
citation-check      look for inline citation markers (URL / [1] / (Doe, 2024)).
placeholder-audit   find leftover scaffolding placeholders (TODO/TBD/FIXME/<...>/{{...}}).
count-list-items    count bullet/numbered list items (optionally under a heading);
                    supports exact-count assertion via --expected.
date-extract        extract and normalize all dates in the file; assert match for --expected.
"""
from __future__ import annotations

import argparse
import re
from typing import Any, Iterable

from . import _common as C


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("must-contain", help="all/any of --terms appear in file.")
    p.add_argument("--file", required=True)
    p.add_argument("--terms", nargs="+", required=True)
    p.add_argument("--mode", choices=("all", "any"), default="all")
    p.add_argument("--regex", action="store_true",
                   help="treat each term as a regex (otherwise literal substring)")
    p.add_argument("--ignore-case", action="store_true")

    p = sub.add_parser("must-not-contain", help="NONE of --terms appear in file.")
    p.add_argument("--file", required=True)
    p.add_argument("--terms", nargs="+", required=True)
    p.add_argument("--regex", action="store_true")
    p.add_argument("--ignore-case", action="store_true")

    p = sub.add_parser("count-matches", help="Count occurrences of one regex; sample positions.")
    p.add_argument("--file", required=True)
    p.add_argument("--regex", required=True)
    p.add_argument("--ignore-case", action="store_true")
    p.add_argument("--sample", type=int, default=5)

    p = sub.add_parser("section-length",
                       help="Length of an MD section; checked against min/max thresholds.")
    p.add_argument("--file", required=True)
    p.add_argument("--heading-regex", required=True)
    p.add_argument("--min-chars", type=int, default=None)
    p.add_argument("--max-chars", type=int, default=None)

    p = sub.add_parser("lang-ratio", help="CJK character ratio.")
    p.add_argument("--file", required=True)

    p = sub.add_parser("citation-check",
                       help="Find inline citation markers (URL / [n] / (Doe, 2024)).")
    p.add_argument("--file", required=True)
    p.add_argument("--max-hits", type=int, default=20)

    p = sub.add_parser("placeholder-audit",
                       help="Find leftover scaffolding placeholders (TODO / TBD / <xxx> / {{...}}).")
    p.add_argument("--file", required=True)
    p.add_argument("--extra-pattern", action="append", default=[],
                   help="repeatable; additional regex(es) to OR into the default set")

    p = sub.add_parser("count-list-items",
                       help="Count bullet/numbered list items (optionally under a markdown heading).")
    p.add_argument("--file", required=True)
    p.add_argument("--heading-regex", default=None,
                   help="if set, only count items inside the section under this heading")
    p.add_argument("--expected", type=int, default=None,
                   help="if set, assert count == expected (exact)")
    p.add_argument("--min", type=int, default=None,
                   help="if set, assert count >= min")
    p.add_argument("--max", type=int, default=None,
                   help="if set, assert count <= max")

    p = sub.add_parser("date-extract",
                       help="Extract and normalize dates; optionally assert one expected date appears.")
    p.add_argument("--file", required=True)
    p.add_argument("--expected", default=None,
                   help="ISO date 'YYYY-MM-DD' to assert appears in the file (any format)")
    p.add_argument("--max-hits", type=int, default=50)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read(path: str) -> tuple[str, str]:
    abs_path = C.require_file(path)
    try:
        with open(abs_path, encoding="utf-8", errors="replace") as f:
            text = f.read()
    except Exception as e:
        raise C.VerifierError(C.ErrCode.PARSE_ERROR, f"failed to read {abs_path}: {e}") from e
    return text, abs_path


def _compile(term: str, *, regex: bool, ignore_case: bool) -> re.Pattern:
    flags = re.IGNORECASE if ignore_case else 0
    pat = term if regex else re.escape(term)
    try:
        return re.compile(pat, flags)
    except re.error as e:
        raise C.VerifierError(C.ErrCode.BAD_ARGS, f"invalid regex {term!r}: {e}") from e


def _line_col(text: str, pos: int) -> tuple[int, int]:
    line = text.count("\n", 0, pos) + 1
    last_nl = text.rfind("\n", 0, pos)
    col = pos - last_nl
    return line, col


def _sample_positions(text: str, pattern: re.Pattern, sample: int) -> list[dict]:
    out: list[dict] = []
    for m in pattern.finditer(text):
        line, col = _line_col(text, m.start())
        out.append({"line": line, "col": col, "match": m.group(0)})
        if len(out) >= sample:
            break
    return out


# ---------------------------------------------------------------------------
# must-contain / must-not-contain
# ---------------------------------------------------------------------------

def _term_results(text: str, terms: Iterable[str], *, regex: bool, ignore_case: bool) -> list[dict]:
    out: list[dict] = []
    for t in terms:
        pat = _compile(t, regex=regex, ignore_case=ignore_case)
        n = sum(1 for _ in pat.finditer(text))
        out.append({"term": t, "count": n, "found": n > 0})
    return out


def cmd_must_contain(args: argparse.Namespace) -> dict:
    text, abs_path = _read(args.file)
    rs = _term_results(text, args.terms, regex=args.regex, ignore_case=args.ignore_case)
    found = [r for r in rs if r["found"]]
    if args.mode == "all":
        passed = len(found) == len(rs)
        note = (f"all required: matched {len(found)}/{len(rs)}"
                + (f"; missing={[r['term'] for r in rs if not r['found']]}" if not passed else ""))
    else:
        passed = len(found) > 0
        note = f"any required: {len(found)}/{len(rs)} matched"
    return {
        "file": abs_path, "mode": args.mode, "regex": args.regex, "ignore_case": args.ignore_case,
        "results": rs, "passed": passed, "note": note,
        "_evidence": C.evidence(file=abs_path, quote=note),
    }


def cmd_must_not_contain(args: argparse.Namespace) -> dict:
    text, abs_path = _read(args.file)
    rs = _term_results(text, args.terms, regex=args.regex, ignore_case=args.ignore_case)
    banned = [r for r in rs if r["found"]]
    passed = not banned
    note = ("none of the banned terms appear" if passed
            else f"{len(banned)} banned terms appear: " +
            ", ".join(f"{r['term']!r}({r['count']}x)" for r in banned))
    return {
        "file": abs_path, "regex": args.regex, "ignore_case": args.ignore_case,
        "results": rs, "passed": passed, "note": note,
        "_evidence": C.evidence(file=abs_path, quote=note),
    }


# ---------------------------------------------------------------------------
# count-matches
# ---------------------------------------------------------------------------

def cmd_count_matches(args: argparse.Namespace) -> dict:
    text, abs_path = _read(args.file)
    pat = _compile(args.regex, regex=True, ignore_case=args.ignore_case)
    n = sum(1 for _ in pat.finditer(text))
    samples = _sample_positions(text, pat, args.sample)
    return {
        "file": abs_path, "regex": args.regex, "ignore_case": args.ignore_case,
        "count": n, "samples": samples,
        "_evidence": C.evidence(file=abs_path,
                                locator={"regex": args.regex},
                                quote=f"{n} matches"
                                + (f"; first @ line {samples[0]['line']}: {samples[0]['match']!r}" if samples else "")),
    }


# ---------------------------------------------------------------------------
# section-length (markdown only — splits on `^#+\s` headings)
# ---------------------------------------------------------------------------

_HEADING_RE = re.compile(r"^(#+)\s+(.*)$", re.MULTILINE)


def cmd_section_length(args: argparse.Namespace) -> dict:
    text, abs_path = _read(args.file)
    try:
        h_re = re.compile(args.heading_regex)
    except re.error as e:
        raise C.VerifierError(C.ErrCode.BAD_ARGS, f"invalid heading regex: {e}") from e

    headings = [(m.start(), len(m.group(1)), m.group(2)) for m in _HEADING_RE.finditer(text)]
    target_idx = -1
    matched_heading = None
    matched_level = -1
    for i, (_, lvl, htxt) in enumerate(headings):
        if h_re.search(htxt):
            target_idx = i
            matched_heading = htxt
            matched_level = lvl
            break

    if target_idx < 0:
        return {
            "file": abs_path, "heading_regex": args.heading_regex,
            "found": False, "char_count": 0, "passed": False,
            "_evidence": C.evidence(file=abs_path,
                                    locator={"heading_regex": args.heading_regex},
                                    quote="heading not found"),
        }

    start = headings[target_idx][0]
    # Find next heading of same-or-higher level
    end = len(text)
    for j in range(target_idx + 1, len(headings)):
        if headings[j][1] <= matched_level:
            end = headings[j][0]
            break

    # Body excludes the heading line itself
    line_end = text.find("\n", start)
    body_start = (line_end + 1) if line_end >= 0 else end
    body = text[body_start:end].strip()
    n = len(body)

    checks: list[dict] = []
    if args.min_chars is not None:
        checks.append({"check": "min_chars", "expected": args.min_chars, "actual": n,
                       "passed": n >= args.min_chars})
    if args.max_chars is not None:
        checks.append({"check": "max_chars", "expected": args.max_chars, "actual": n,
                       "passed": n <= args.max_chars})
    overall: bool | None = all(c["passed"] for c in checks) if checks else None

    return {
        "file": abs_path, "heading_regex": args.heading_regex,
        "found": True, "matched_heading": matched_heading, "matched_level": matched_level,
        "char_count": n, "checks": checks, "passed": overall,
        "_evidence": C.evidence(file=abs_path,
                                locator={"heading_regex": args.heading_regex,
                                         "matched_heading": matched_heading},
                                quote=f"section under {matched_heading!r}: {n} chars"),
    }


# ---------------------------------------------------------------------------
# lang-ratio
# ---------------------------------------------------------------------------

def cmd_lang_ratio(args: argparse.Namespace) -> dict:
    text, abs_path = _read(args.file)
    nonws = [c for c in text if not c.isspace()]
    cjk = sum(1 for c in nonws if "\u4e00" <= c <= "\u9fff")
    ratio = (cjk / len(nonws)) if nonws else 0.0
    return {
        "file": abs_path,
        "nonws_chars": len(nonws),
        "cjk_chars": cjk,
        "cjk_ratio": ratio,
        "_evidence": C.evidence(file=abs_path,
                                quote=f"cjk={cjk}/{len(nonws)} (ratio={ratio:.3f})"),
    }


# ---------------------------------------------------------------------------
# citation-check
# ---------------------------------------------------------------------------

_CITE_PATTERNS = [
    (r"https?://\S+", "url"),
    (r"\[\d+\]", "bracket-num"),
    (r"\(\s*[^)]{1,40}?,\s*\d{4}[a-z]?\s*\)", "author-year"),
    (r"\[[A-Z][a-zA-Z\s]+\d{4}\]", "ieee-style"),
]


def cmd_citation_check(args: argparse.Namespace) -> dict:
    text, abs_path = _read(args.file)
    by_kind: dict[str, list[dict]] = {}
    total = 0
    for pat, name in _CITE_PATTERNS:
        rx = re.compile(pat)
        hits = []
        for m in rx.finditer(text):
            line, col = _line_col(text, m.start())
            hits.append({"line": line, "col": col, "match": m.group(0)[:80]})
            if len(hits) >= args.max_hits:
                break
        if hits:
            by_kind[name] = hits
            total += len(hits)
    return {
        "file": abs_path,
        "total_citations": total,
        "by_kind": by_kind,
        "_evidence": C.evidence(file=abs_path,
                                quote=f"{total} citations: " +
                                ", ".join(f"{k}={len(v)}" for k, v in by_kind.items())),
    }


# ---------------------------------------------------------------------------
# placeholder-audit
# ---------------------------------------------------------------------------

_PLACEHOLDER_PATTERNS = [
    (r"\bTODO\b", "TODO"),
    (r"\bTBD\b", "TBD"),
    (r"\bFIXME\b", "FIXME"),
    (r"\bXXX\b", "XXX"),
    (r"\{\{\s*[^}]+?\s*\}\}", "mustache-placeholder"),
    (r"<[A-Z][A-Z_]{2,}>", "ANGLE_PLACEHOLDER"),
    (r"\.\.\.+", "ellipsis"),
    (r"\b(待补充|待填|占位)\b", "cn-placeholder"),
]


def cmd_placeholder_audit(args: argparse.Namespace) -> dict:
    text, abs_path = _read(args.file)
    patterns = list(_PLACEHOLDER_PATTERNS)
    for extra in args.extra_pattern:
        patterns.append((extra, f"extra:{extra[:20]}"))

    by_kind: dict[str, list[dict]] = {}
    total = 0
    for pat, name in patterns:
        try:
            rx = re.compile(pat)
        except re.error:
            continue
        hits = []
        for m in rx.finditer(text):
            line, col = _line_col(text, m.start())
            hits.append({"line": line, "col": col, "match": m.group(0)[:80]})
            if len(hits) >= 20:
                break
        if hits:
            by_kind[name] = hits
            total += len(hits)
    return {
        "file": abs_path,
        "total_placeholders": total,
        "by_kind": by_kind,
        "passed": total == 0,
        "_evidence": C.evidence(file=abs_path,
                                quote=f"{total} placeholders" +
                                (f": " + ", ".join(f"{k}={len(v)}" for k, v in by_kind.items()) if total else " (none)")),
    }


# ---------------------------------------------------------------------------
# count-list-items — count bullet/numbered items, optionally under a section.
#
# Closes "Lists all four cost drivers" rubric class.  Recognizes markdown
# bullet markers (-, *, +) and numbered lists (1., 1)) at line start, after
# optional indentation.
# ---------------------------------------------------------------------------

_LIST_ITEM_RE = re.compile(r"^[ \t]*(?:[-*+]|\d+[.)])\s+\S", re.MULTILINE)


def _section_slice(text: str, heading_regex: str) -> tuple[str, str | None]:
    """Return (body, matched_heading); body is the empty string if not found."""
    try:
        h_re = re.compile(heading_regex)
    except re.error as e:
        raise C.VerifierError(C.ErrCode.BAD_ARGS, f"invalid heading regex: {e}") from e
    headings = [(m.start(), len(m.group(1)), m.group(2)) for m in _HEADING_RE.finditer(text)]
    target_idx = -1
    matched_heading = None
    matched_level = -1
    for i, (_, lvl, htxt) in enumerate(headings):
        if h_re.search(htxt):
            target_idx = i
            matched_heading = htxt
            matched_level = lvl
            break
    if target_idx < 0:
        return "", None
    start = headings[target_idx][0]
    end = len(text)
    for j in range(target_idx + 1, len(headings)):
        if headings[j][1] <= matched_level:
            end = headings[j][0]
            break
    line_end = text.find("\n", start)
    body_start = (line_end + 1) if line_end >= 0 else end
    return text[body_start:end], matched_heading


def cmd_count_list_items(args: argparse.Namespace) -> dict:
    text, abs_path = _read(args.file)
    matched_heading: str | None = None
    if args.heading_regex is not None:
        body, matched_heading = _section_slice(text, args.heading_regex)
        if matched_heading is None:
            return {
                "file": abs_path, "heading_regex": args.heading_regex,
                "found": False, "count": 0, "passed": False,
                "_evidence": C.evidence(file=abs_path,
                                        locator={"heading_regex": args.heading_regex},
                                        quote=f"heading /{args.heading_regex}/ not found"),
            }
    else:
        body = text

    matches = list(_LIST_ITEM_RE.finditer(body))
    count = len(matches)

    checks: list[dict] = []
    if args.expected is not None:
        checks.append({"check": "expected", "expected": args.expected,
                       "actual": count, "passed": count == args.expected})
    if args.min is not None:
        checks.append({"check": "min", "expected": args.min,
                       "actual": count, "passed": count >= args.min})
    if args.max is not None:
        checks.append({"check": "max", "expected": args.max,
                       "actual": count, "passed": count <= args.max})
    overall: bool | None = all(c["passed"] for c in checks) if checks else None

    sample: list[str] = []
    for m in matches[:5]:
        end = body.find("\n", m.start())
        line = body[m.start(): end if end >= 0 else m.start() + 100]
        sample.append(line.strip()[:100])

    return {
        "file": abs_path,
        "heading_regex": args.heading_regex,
        "matched_heading": matched_heading,
        "count": count,
        "checks": checks, "passed": overall,
        "sample_items": sample,
        "_evidence": C.evidence(
            file=abs_path,
            locator=({"heading_regex": args.heading_regex,
                      "matched_heading": matched_heading}
                     if matched_heading else None),
            quote=f"{count} list items"
            + (f" under {matched_heading!r}" if matched_heading else "")
            + (f"; checks: " + ", ".join(f"{c['check']}={c['passed']}" for c in checks)
               if checks else ""),
        ),
    }


# ---------------------------------------------------------------------------
# date-extract — extract dates, normalize to ISO YYYY-MM-DD.
#
# Stdlib-only.  Recognizes the most common patterns shown in GDPval
# rubrics: M/D/YYYY, MM/DD/YYYY, YYYY-MM-DD, and "Month D, YYYY" /
# "D Month YYYY" (English).  Optional --expected asserts one ISO date appears
# anywhere in the extracted set.
# ---------------------------------------------------------------------------

_MONTHS = {
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
    "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
    "august": 8, "aug": 8, "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10, "november": 11, "nov": 11, "december": 12, "dec": 12,
}

_DATE_PATTERNS: list[tuple[re.Pattern, str]] = [
    # YYYY-MM-DD (ISO)
    (re.compile(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b"), "iso"),
    # M/D/YYYY or MM/DD/YYYY (US)
    (re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b"), "us"),
    # D-Month-YYYY or D Month YYYY (e.g. "1 March 2024")
    (re.compile(
        r"\b(\d{1,2})[ \-]([A-Za-z]+)[ \-,]+(\d{4})\b"), "dmy_text"),
    # Month D, YYYY or Month DD, YYYY (e.g. "March 1, 2024")
    (re.compile(
        r"\b([A-Za-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b"), "mdy_text"),
]


def _normalize_date(raw: str, kind: str, groups: tuple) -> str | None:
    try:
        if kind == "iso":
            y, m, d = int(groups[0]), int(groups[1]), int(groups[2])
        elif kind == "us":
            m, d, y = int(groups[0]), int(groups[1]), int(groups[2])
        elif kind == "dmy_text":
            d = int(groups[0])
            month_name = groups[1].lower()
            if month_name not in _MONTHS:
                return None
            m = _MONTHS[month_name]
            y = int(groups[2])
        elif kind == "mdy_text":
            month_name = groups[0].lower()
            if month_name not in _MONTHS:
                return None
            m = _MONTHS[month_name]
            d = int(groups[1])
            y = int(groups[2])
        else:
            return None
        if not (1 <= m <= 12 and 1 <= d <= 31 and 1900 <= y <= 2200):
            return None
        return f"{y:04d}-{m:02d}-{d:02d}"
    except (ValueError, IndexError):
        return None


def cmd_date_extract(args: argparse.Namespace) -> dict:
    text, abs_path = _read(args.file)
    seen: dict[str, list[dict]] = {}
    total = 0
    for rx, kind in _DATE_PATTERNS:
        for m in rx.finditer(text):
            iso = _normalize_date(m.group(0), kind, m.groups())
            if iso is None:
                continue
            line, col = _line_col(text, m.start())
            seen.setdefault(iso, []).append({
                "raw": m.group(0), "kind": kind, "line": line, "col": col,
            })
            total += 1
            if total >= args.max_hits:
                break
        if total >= args.max_hits:
            break

    iso_dates_sorted = sorted(seen.keys())
    expected = args.expected
    passed: bool | None = None
    if expected is not None:
        # Validate expected format
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", expected):
            raise C.VerifierError(
                C.ErrCode.BAD_ARGS,
                f"--expected must be ISO YYYY-MM-DD, got {expected!r}",
            )
        passed = expected in seen

    return {
        "file": abs_path,
        "total_dates": total,
        "unique_iso_dates": iso_dates_sorted,
        "by_iso": seen,
        "expected": expected,
        "passed": passed,
        "_evidence": C.evidence(
            file=abs_path,
            quote=f"{total} dates, {len(iso_dates_sorted)} unique"
            + (f"; sample: {iso_dates_sorted[:5]}" if iso_dates_sorted else "")
            + (f"; expected={expected}: {'OK' if passed else 'NOT FOUND'}"
               if expected is not None else ""),
        ),
    }
