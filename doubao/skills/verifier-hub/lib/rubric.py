"""rubric — high-level DSL primitives that wrap lower families.

Use these when a single-shot rubric maps cleanly to a deterministic check
(faster + less error-prone than 3-4 lower-level commands stitched together).

11 subcommands
--------------
check-file-format        file exists + opens cleanly + extension matches.
check-section-exists     a section under heading-regex exists with ≥ min-chars body.
check-table-field        a table cell equals expected (str/regex/numeric).
check-keywords           all/any/none of --terms appear in a text/md file.
check-numeric            a numeric value matches expected within tolerance (xlsx cell or text regex).
check-formula            an xlsx cell formula is consistent with referenced cells.
check-excluded           none of --banned terms appear (banned-keyword guard).
check-revisions          a docx has NO tracked changes / inline comments.
check-signature-block    a docx contains a signature/seal block.
check-no-placeholder     a text file has zero TODO/TBD/<...>/{{...}} placeholders.
check-cross-consistency  same numeric value appears across multiple files within tolerance.
"""
from __future__ import annotations

import argparse
import re
from typing import Any

from . import _common as C
from . import docx as _docx_mod
from . import file_io as _file_mod
from . import text as _text_mod
from . import xlsx as _xlsx_mod


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("check-file-format",
                       help="file exists + opens cleanly + extension matches.")
    p.add_argument("file")
    p.add_argument("--expected-ext", required=True,
                   help="comma-separated allowed extensions (with dot)")

    p = sub.add_parser("check-section-exists",
                       help="docx section under --heading-regex with ≥ min-chars body.")
    p.add_argument("file")
    p.add_argument("--heading-regex", required=True)
    p.add_argument("--min-chars", type=int, default=1)

    p = sub.add_parser("check-table-field",
                       help="docx table cell equals expected (str/regex/numeric).")
    p.add_argument("file")
    p.add_argument("--table-index", type=int, default=0)
    p.add_argument("--row-header", required=True)
    p.add_argument("--col", type=int, required=True)
    p.add_argument("--expected", required=True)
    p.add_argument("--mode", choices=("exact", "contains", "regex", "numeric"), default="exact")
    p.add_argument("--tol-abs", type=float, default=None)
    p.add_argument("--tol-rel", type=float, default=None)

    p = sub.add_parser("check-keywords",
                       help="all/any/none of --terms appear in a text/md file.")
    p.add_argument("file")
    p.add_argument("--terms", nargs="+", required=True)
    p.add_argument("--mode", choices=("all", "any", "none"), default="all")
    p.add_argument("--regex", action="store_true")
    p.add_argument("--ignore-case", action="store_true")

    p = sub.add_parser("check-numeric",
                       help="numeric value matches expected within tolerance (xlsx cell OR text regex group).")
    p.add_argument("file")
    p.add_argument("--source", choices=("xlsx", "text"), required=True)
    # xlsx mode
    p.add_argument("--sheet", default=None)
    p.add_argument("--cell", default=None)
    # text mode
    p.add_argument("--regex", default=None,
                   help="regex with one capture group around the number; e.g. r'累计供应:\\s*([0-9.]+)'")
    p.add_argument("--expected", type=float, required=True)
    p.add_argument("--tol-abs", type=float, default=None)
    p.add_argument("--tol-rel", type=float, default=None)

    p = sub.add_parser("check-formula",
                       help="xlsx cell formula consistent with referenced cells.")
    p.add_argument("file")
    p.add_argument("--sheet", required=True)
    p.add_argument("--cell", required=True)
    p.add_argument("--tol-abs", type=float, default=1e-6)
    p.add_argument("--tol-rel", type=float, default=None)

    p = sub.add_parser("check-excluded",
                       help="NONE of --banned terms appear in a text/md file.")
    p.add_argument("file")
    p.add_argument("--banned", nargs="+", required=True)
    p.add_argument("--regex", action="store_true")
    p.add_argument("--ignore-case", action="store_true")

    p = sub.add_parser("check-revisions",
                       help="docx has NO tracked changes / inline comments.")
    p.add_argument("file")

    p = sub.add_parser("check-signature-block",
                       help="docx contains a signature/seal block.")
    p.add_argument("file")
    p.add_argument("--pattern", default=None)

    p = sub.add_parser("check-no-placeholder",
                       help="text file has ZERO TODO/TBD/<...>/{{...}} placeholders.")
    p.add_argument("file")
    p.add_argument("--extra-pattern", action="append", default=[])

    p = sub.add_parser(
        "check-cross-consistency",
        help=("Same numeric value appears across multiple sources within tolerance. "
              "Specify each source as KIND:KEY=VAL;...  (separator = SEMICOLON, so commas "
              "inside regexes are safe). KIND in {xlsx,text}. Example: "
              "--source 'xlsx:file=a.xlsx;sheet=Sum;cell=B2' "
              "--source 'text:file=memo.md;regex=Total: \\$([0-9,.]+)'"),
    )
    p.add_argument("--source", action="append", required=True,
                   help="repeatable; one --source per file/locator")
    p.add_argument("--tol-abs", type=float, default=None)
    p.add_argument("--tol-rel", type=float, default=None)


# ---------------------------------------------------------------------------
# Adapters — build a Namespace mimicking the lower family's CLI args, dispatch.
# Pass-through PASSED/FAILED into the rubric envelope.
# ---------------------------------------------------------------------------

def _ns(**kw: Any) -> argparse.Namespace:
    return argparse.Namespace(**kw)


def _envelope(passed: bool | None, evidence_quote: str, detail: dict) -> dict:
    return {"passed": passed, "evidence_quote": evidence_quote, "detail": detail,
            "_evidence": C.evidence(quote=evidence_quote)}


# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------

def cmd_check_file_format(args: argparse.Namespace) -> dict:
    res = _file_mod.cmd_validate(_ns(file=args.file, expected_ext=args.expected_ext))
    quote = res["_evidence"]["quote"]
    return _envelope(True, f"OK — {quote}", res)  # _file.cmd_validate raises on failure


def cmd_check_section_exists(args: argparse.Namespace) -> dict:
    res = _docx_mod.cmd_section_text(_ns(file=args.file,
                                         heading_regex=args.heading_regex,
                                         max_chars=max(args.min_chars * 2, 200)))
    found = bool(res.get("found"))
    n = res.get("char_count", 0)
    passed = found and n >= args.min_chars
    quote = (f"section {res.get('matched_heading')!r}: {n} chars (need ≥{args.min_chars})"
             if found else f"section matching {args.heading_regex!r} NOT FOUND")
    return _envelope(passed, quote, res)


def cmd_check_table_field(args: argparse.Namespace) -> dict:
    sub = _docx_mod.cmd_table_field(_ns(file=args.file, table_index=args.table_index,
                                        row=None, col=args.col, row_header=args.row_header))
    actual = sub["text"]
    if args.mode == "exact":
        passed = actual.strip() == args.expected.strip()
        quote = f"row={args.row_header!r} col={args.col}: actual={actual!r} expected={args.expected!r}"
    elif args.mode == "contains":
        passed = args.expected in actual
        quote = f"row={args.row_header!r} col={args.col}: contains {args.expected!r}? {passed}"
    elif args.mode == "regex":
        import re
        try:
            passed = bool(re.search(args.expected, actual))
        except re.error as e:
            raise C.VerifierError(C.ErrCode.BAD_ARGS, f"invalid regex: {e}") from e
        quote = f"row={args.row_header!r} col={args.col}: regex /{args.expected}/ on {actual!r} → {passed}"
    else:  # numeric
        try:
            expected_num = float(args.expected)
        except ValueError as e:
            raise C.VerifierError(C.ErrCode.BAD_ARGS,
                                  f"--mode=numeric but --expected={args.expected!r} not numeric") from e
        passed, ttext = C.in_tolerance(actual.strip().replace(",", ""),
                                       expected_num, args.tol_abs, args.tol_rel)
        quote = f"row={args.row_header!r} col={args.col}: {ttext}"
    return _envelope(bool(passed), quote, sub)


def cmd_check_keywords(args: argparse.Namespace) -> dict:
    if args.mode == "none":
        sub = _text_mod.cmd_must_not_contain(_ns(file=args.file, terms=args.terms,
                                                 regex=args.regex, ignore_case=args.ignore_case))
    else:
        sub = _text_mod.cmd_must_contain(_ns(file=args.file, terms=args.terms,
                                             mode=args.mode, regex=args.regex,
                                             ignore_case=args.ignore_case))
    return _envelope(bool(sub["passed"]), sub["note"], sub)


def cmd_check_numeric(args: argparse.Namespace) -> dict:
    if args.source == "xlsx":
        if not args.sheet or not args.cell:
            raise C.VerifierError(C.ErrCode.BAD_ARGS,
                                  "--source=xlsx requires --sheet and --cell")
        sub = _xlsx_mod.cmd_assert_value(_ns(file=args.file, sheet=args.sheet, cell=args.cell,
                                             expected=str(args.expected),
                                             tol_abs=args.tol_abs, tol_rel=args.tol_rel,
                                             str_mode=None))
        return _envelope(bool(sub["passed"]), sub["note"], sub)
    # text mode
    if not args.regex:
        raise C.VerifierError(C.ErrCode.BAD_ARGS, "--source=text requires --regex (with one capture group)")
    import re
    text, abs_path = _text_mod._read(args.file)  # type: ignore[attr-defined]
    try:
        rx = re.compile(args.regex)
    except re.error as e:
        raise C.VerifierError(C.ErrCode.BAD_ARGS, f"invalid regex: {e}") from e
    m = rx.search(text)
    if not m:
        return _envelope(False, f"regex /{args.regex}/ produced no match in {abs_path}",
                         {"file": abs_path, "regex": args.regex, "matched": False})
    if not m.groups():
        raise C.VerifierError(C.ErrCode.BAD_ARGS, "--regex must contain one capture group around the number")
    captured = m.group(1)
    passed, ttext = C.in_tolerance(captured, args.expected, args.tol_abs, args.tol_rel)
    quote = f"matched {captured!r}: {ttext}"
    return _envelope(bool(passed), quote,
                     {"file": abs_path, "regex": args.regex, "matched_text": captured})


def cmd_check_formula(args: argparse.Namespace) -> dict:
    sub = _xlsx_mod.cmd_eval_formula(_ns(file=args.file, sheet=args.sheet, cell=args.cell,
                                         tol_abs=args.tol_abs, tol_rel=args.tol_rel))
    passed = sub.get("passed")  # may be None when formula shape is unsupported
    return _envelope(passed, sub.get("note", ""), sub)


def cmd_check_excluded(args: argparse.Namespace) -> dict:
    sub = _text_mod.cmd_must_not_contain(_ns(file=args.file, terms=args.banned,
                                             regex=args.regex, ignore_case=args.ignore_case))
    return _envelope(bool(sub["passed"]), sub["note"], sub)


def cmd_check_revisions(args: argparse.Namespace) -> dict:
    sub = _docx_mod.cmd_has_revisions(_ns(file=args.file))
    passed = not sub["has_revisions"]
    quote = (f"clean — no tracked changes / comments"
             if passed
             else f"FAILED — insertions={sub['insertions']}, deletions={sub['deletions']}, comments={sub['comments']}")
    return _envelope(passed, quote, sub)


def cmd_check_signature_block(args: argparse.Namespace) -> dict:
    sub = _docx_mod.cmd_signature_block(_ns(file=args.file, pattern=args.pattern))
    passed = sub["found"]
    quote = sub["_evidence"]["quote"]
    return _envelope(passed, quote, sub)


def cmd_check_no_placeholder(args: argparse.Namespace) -> dict:
    sub = _text_mod.cmd_placeholder_audit(_ns(file=args.file, extra_pattern=args.extra_pattern))
    passed = sub["passed"]
    quote = sub["_evidence"]["quote"]
    return _envelope(passed, quote, sub)


# ---------------------------------------------------------------------------
# check-cross-consistency — cross-file numeric agreement.
#
# Source string format:  KIND:k1=v1;k2=v2;...
# Supported KINDs:
#   xlsx  — required keys: file, sheet, cell
#   text  — required keys: file, regex (must contain ONE capture group around the number)
#
# Why semicolon and not comma: GDPval-style numbers like 1,234.56 mean regexes
# very often need commas, so commas as field separators were too easily broken.
# Semicolons appear in neither regex syntax nor typical filenames.
# ---------------------------------------------------------------------------

def _parse_source_spec(spec: str) -> tuple[str, dict[str, str]]:
    if ":" not in spec:
        raise C.VerifierError(
            C.ErrCode.BAD_ARGS,
            f"--source must be 'KIND:k1=v1;k2=v2;...'; got {spec!r}",
        )
    kind, body = spec.split(":", 1)
    kind = kind.strip().lower()
    fields: dict[str, str] = {}
    for part in body.split(";"):
        part = part.strip()
        if not part:
            continue
        if "=" not in part:
            raise C.VerifierError(
                C.ErrCode.BAD_ARGS,
                f"--source field {part!r} missing '='; in spec {spec!r}",
            )
        k, v = part.split("=", 1)
        fields[k.strip()] = v.strip()
    return kind, fields


def _extract_xlsx(fields: dict[str, str]) -> tuple[float, str, str]:
    for req in ("file", "sheet", "cell"):
        if req not in fields:
            raise C.VerifierError(C.ErrCode.BAD_ARGS,
                                  f"xlsx source missing required field {req!r}")
    v, abs_path = _xlsx_mod._read_cell_value(  # type: ignore[attr-defined]
        fields["file"], fields["sheet"], fields["cell"], data_only=True)
    if v is None:
        raise C.VerifierError(
            C.ErrCode.NOT_FOUND,
            f"xlsx cell {fields['sheet']}!{fields['cell']} in {abs_path} is empty",
        )
    try:
        num = float(str(v).replace(",", "").replace("$", "").strip())
    except (ValueError, TypeError) as e:
        raise C.VerifierError(
            C.ErrCode.PARSE_ERROR,
            f"xlsx cell value {v!r} (sheet={fields['sheet']!r} cell={fields['cell']!r}) "
            f"in {abs_path} is not numeric",
        ) from e
    return num, abs_path, f"sheet={fields['sheet']} cell={fields['cell']}"


def _extract_text(fields: dict[str, str]) -> tuple[float, str, str]:
    for req in ("file", "regex"):
        if req not in fields:
            raise C.VerifierError(C.ErrCode.BAD_ARGS,
                                  f"text source missing required field {req!r}")
    text, abs_path = _text_mod._read(fields["file"])  # type: ignore[attr-defined]
    try:
        rx = re.compile(fields["regex"])
    except re.error as e:
        raise C.VerifierError(C.ErrCode.BAD_ARGS,
                              f"invalid regex {fields['regex']!r}: {e}") from e
    m = rx.search(text)
    if not m:
        raise C.VerifierError(
            C.ErrCode.NOT_FOUND,
            f"regex /{fields['regex']}/ produced no match in {abs_path}",
        )
    if not m.groups():
        raise C.VerifierError(
            C.ErrCode.BAD_ARGS,
            f"regex {fields['regex']!r} must contain one capture group around the number",
        )
    captured = m.group(1).replace(",", "").replace("$", "").strip()
    try:
        num = float(captured)
    except ValueError as e:
        raise C.VerifierError(
            C.ErrCode.PARSE_ERROR,
            f"captured text {captured!r} from {abs_path} is not numeric",
        ) from e
    return num, abs_path, f"regex={fields['regex']}"


_EXTRACTORS = {
    "xlsx": _extract_xlsx,
    "text": _extract_text,
}


def cmd_check_cross_consistency(args: argparse.Namespace) -> dict:
    if len(args.source) < 2:
        raise C.VerifierError(C.ErrCode.BAD_ARGS,
                              "need at least two --source specs to cross-check")

    extractions: list[dict] = []
    errors: list[dict] = []
    for spec in args.source:
        try:
            kind, fields = _parse_source_spec(spec)
            if kind not in _EXTRACTORS:
                raise C.VerifierError(
                    C.ErrCode.BAD_ARGS,
                    f"unsupported source kind {kind!r}; valid: {list(_EXTRACTORS)}",
                )
            num, path, locator = _EXTRACTORS[kind](fields)
            extractions.append({"spec": spec, "kind": kind, "file": path,
                                "locator": locator, "value": num})
        except C.VerifierError as e:
            errors.append({"spec": spec, "code": e.code, "msg": e.msg})

    if errors:
        return _envelope(
            False,
            f"extraction failed for {len(errors)}/{len(args.source)} source(s): "
            + "; ".join(f"{e['spec']!r} → {e['code']}" for e in errors),
            {"extractions": extractions, "errors": errors},
        )

    values = [e["value"] for e in extractions]
    base = values[0]
    pairwise: list[dict] = []
    all_match = True
    for i in range(1, len(values)):
        ok, ttext = C.in_tolerance(values[i], base, args.tol_abs, args.tol_rel)
        pairwise.append({"a": extractions[0]["spec"], "b": extractions[i]["spec"],
                         "passed": bool(ok), "note": ttext})
        all_match = all_match and bool(ok)

    quote = (f"all {len(values)} sources agree (base={base})"
             if all_match
             else f"MISMATCH across {len(values)} sources: values={values}")
    return _envelope(all_match, quote,
                     {"extractions": extractions, "pairwise": pairwise,
                      "base_value": base, "all_values": values})
