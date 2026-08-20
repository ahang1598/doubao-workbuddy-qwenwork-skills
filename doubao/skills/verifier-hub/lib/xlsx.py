"""xlsx — Excel workbook inspection (read-only).

12 subcommands
--------------
list-sheets        sheet names + dimensions.
get-value          cell value (data_only by default).
assert-value       cell value vs expected (with tolerance).
get-formula        cell formula text (data_only=False).
eval-formula       per-cell formula vs computed value (cross-cell consistency).
find-cell          find cells whose value matches a regex.
sheet-shape        rows/cols of a sheet, ignore-empty option.
header-check       first row contains expected headers (set/order).
nonempty-rows      count rows with at least one non-empty cell in given range.
style-check        font bold / fill color / number format on a cell.
sum-range          sum a numeric range; useful for cross-checks.
column-format      ALL non-empty cells in a range share a number format (currency / pct).
"""
from __future__ import annotations

import argparse
import re
from typing import Any

from . import _common as C

_XLSX_EXTS = (".xlsx", ".xlsm")


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("list-sheets", help="List sheet names + dims.")
    p.add_argument("file")

    p = sub.add_parser("get-value", help="Read a single cell.")
    p.add_argument("file")
    p.add_argument("--sheet", required=True)
    p.add_argument("--cell", required=True, help="A1-style cell ref")
    p.add_argument("--raw", action="store_true",
                   help="open with data_only=False (raw formula / unevaluated string)")

    p = sub.add_parser("assert-value", help="Compare a cell value to expected (with tolerance).")
    p.add_argument("file")
    p.add_argument("--sheet", required=True)
    p.add_argument("--cell", required=True)
    p.add_argument("--expected", required=True)
    p.add_argument("--tol-abs", type=float, default=None)
    p.add_argument("--tol-rel", type=float, default=None)
    p.add_argument("--str-mode", choices=("exact", "contains", "regex"), default=None,
                   help="if set, treat both values as strings")

    p = sub.add_parser("get-formula", help="Read a cell's formula text.")
    p.add_argument("file")
    p.add_argument("--sheet", required=True)
    p.add_argument("--cell", required=True)

    p = sub.add_parser("eval-formula",
                       help="Compare cached cell value with re-evaluated formula across referenced cells.")
    p.add_argument("file")
    p.add_argument("--sheet", required=True)
    p.add_argument("--cell", required=True)
    p.add_argument("--tol-abs", type=float, default=1e-6)
    p.add_argument("--tol-rel", type=float, default=None)

    p = sub.add_parser("find-cell", help="Find cells whose value matches a regex.")
    p.add_argument("file")
    p.add_argument("--sheet", required=True)
    p.add_argument("--regex", required=True)
    p.add_argument("--max-hits", type=int, default=20)

    p = sub.add_parser("sheet-shape", help="Reported rows × cols of a sheet (ignore-empty option).")
    p.add_argument("file")
    p.add_argument("--sheet", required=True)
    p.add_argument("--ignore-empty", action="store_true",
                   help="trim trailing empty rows/cols")

    p = sub.add_parser("header-check", help="Check whether the first row matches expected headers.")
    p.add_argument("file")
    p.add_argument("--sheet", required=True)
    p.add_argument("--expected", nargs="+", required=True,
                   help="ordered list of expected headers")
    p.add_argument("--mode", choices=("strict", "subset"), default="strict",
                   help="strict = exact ordered match; subset = all expected appear in any order")

    p = sub.add_parser("nonempty-rows", help="Count non-empty rows in a range.")
    p.add_argument("file")
    p.add_argument("--sheet", required=True)
    p.add_argument("--range", required=True, help="A1:C10-style range")

    p = sub.add_parser("style-check", help="Check cell font/fill/number-format.")
    p.add_argument("file")
    p.add_argument("--sheet", required=True)
    p.add_argument("--cell", required=True)
    p.add_argument("--expect-bold", choices=("true", "false"), default=None)
    p.add_argument("--expect-fill", default=None,
                   help="hex RGB without '#', e.g. FFC0C0C0; matches any prefix")
    p.add_argument("--expect-number-format", default=None,
                   help="exact match string, e.g. '0.00' or '0.00%'")

    p = sub.add_parser("sum-range", help="Sum numeric values in a range; report nonnumeric cells.")
    p.add_argument("file")
    p.add_argument("--sheet", required=True)
    p.add_argument("--range", required=True)

    p = sub.add_parser("column-format",
                       help="ALL non-empty cells in a range share a number format (exact or regex).")
    p.add_argument("file")
    p.add_argument("--sheet", required=True)
    p.add_argument("--range", required=True,
                   help="A1-style range, e.g. F2:F100")
    p.add_argument("--expected-format", default=None,
                   help="exact number_format string (e.g. '$#,##0.00' or '0.00%')")
    p.add_argument("--expected-regex", default=None,
                   help="regex the number_format must match (e.g. r'\\$|USD' for currency)")
    p.add_argument("--include-empty", action="store_true",
                   help="also check cells whose value is empty (default: skip them)")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _open(path: str, *, data_only: bool = True):
    openpyxl = C.lazy_import("openpyxl")
    abs_path = C.require_file(path, _XLSX_EXTS)
    try:
        return openpyxl.load_workbook(abs_path, data_only=data_only, read_only=False), abs_path
    except Exception as e:
        raise C.VerifierError(C.ErrCode.PARSE_ERROR,
                              f"openpyxl.load_workbook({abs_path}, data_only={data_only}) failed: {e}") from e


def _sheet(wb, name: str):
    if name not in wb.sheetnames:
        raise C.VerifierError(C.ErrCode.NOT_FOUND,
                              f"sheet {name!r} not in workbook; available: {wb.sheetnames}")
    return wb[name]


# ---------------------------------------------------------------------------
# list-sheets
# ---------------------------------------------------------------------------

def cmd_list_sheets(args: argparse.Namespace) -> dict:
    wb, abs_path = _open(args.file, data_only=True)
    try:
        sheets = []
        for name in wb.sheetnames:
            ws = wb[name]
            sheets.append({"name": name, "max_row": ws.max_row, "max_col": ws.max_column})
    finally:
        wb.close()
    return {
        "file": abs_path,
        "sheets": sheets,
        "_evidence": C.evidence(file=abs_path,
                                quote=", ".join(f"{s['name']}({s['max_row']}×{s['max_col']})" for s in sheets)),
    }


# ---------------------------------------------------------------------------
# get-value / assert-value / get-formula
# ---------------------------------------------------------------------------

def _read_cell_value(file: str, sheet: str, cell: str, *, data_only: bool = True) -> tuple[Any, str]:
    wb, abs_path = _open(file, data_only=data_only)
    try:
        ws = _sheet(wb, sheet)
        try:
            v = ws[cell].value
        except Exception as e:
            raise C.VerifierError(C.ErrCode.LOCATOR_INVALID,
                                  f"invalid cell ref {cell!r}: {e}") from e
    finally:
        wb.close()
    return v, abs_path


def cmd_get_value(args: argparse.Namespace) -> dict:
    v, abs_path = _read_cell_value(args.file, args.sheet, args.cell,
                                   data_only=not args.raw)
    return {
        "file": abs_path, "sheet": args.sheet, "cell": args.cell,
        "value": v, "raw": args.raw,
        "_evidence": C.evidence(file=abs_path,
                                locator={"sheet": args.sheet, "cell": args.cell},
                                quote=str(v)),
    }


def cmd_assert_value(args: argparse.Namespace) -> dict:
    v, abs_path = _read_cell_value(args.file, args.sheet, args.cell, data_only=True)
    if args.str_mode is not None:
        actual = "" if v is None else str(v)
        expected = args.expected
        if args.str_mode == "exact":
            ok = actual == expected
            note = f"exact match: {'yes' if ok else 'no'} (expected {expected!r}, actual {actual!r})"
        elif args.str_mode == "contains":
            ok = expected in actual
            note = f"contains {expected!r}: {'yes' if ok else 'no'}"
        else:  # regex
            ok = bool(re.search(expected, actual))
            note = f"regex /{expected}/ matches: {'yes' if ok else 'no'}"
    else:
        try:
            expected_num = float(args.expected)
        except ValueError as e:
            raise C.VerifierError(C.ErrCode.BAD_ARGS,
                                  f"--expected={args.expected!r} not numeric (use --str-mode for strings)") from e
        ok, note = C.in_tolerance(v, expected_num, args.tol_abs, args.tol_rel)
    return {
        "file": abs_path, "sheet": args.sheet, "cell": args.cell,
        "actual": v, "expected": args.expected, "passed": bool(ok), "note": note,
        "_evidence": C.evidence(file=abs_path,
                                locator={"sheet": args.sheet, "cell": args.cell},
                                quote=note),
    }


def cmd_get_formula(args: argparse.Namespace) -> dict:
    v, abs_path = _read_cell_value(args.file, args.sheet, args.cell, data_only=False)
    is_formula = isinstance(v, str) and v.startswith("=")
    return {
        "file": abs_path, "sheet": args.sheet, "cell": args.cell,
        "formula": v if is_formula else None,
        "is_formula": is_formula, "raw_value": v,
        "_evidence": C.evidence(file=abs_path,
                                locator={"sheet": args.sheet, "cell": args.cell},
                                quote=f"formula={v!r}" if is_formula else f"non-formula value={v!r}"),
    }


# ---------------------------------------------------------------------------
# eval-formula — light-weight cross-cell consistency check.
#
# We do NOT re-evaluate arbitrary Excel functions.  Instead we:
#   1. Read the formula at the target cell.
#   2. Resolve all referenced cells (same sheet, A1/A1:B2 syntax).
#   3. If the formula is one of {SUM, AVERAGE, MIN, MAX, COUNT, +-*/ scalar}
#      perform the computation in Python and compare to the cached value.
#   4. Otherwise, report the cached value + referenced cells so the caller
#      can sanity-check by inspection.
# ---------------------------------------------------------------------------

_REF_RE = re.compile(r"\b([A-Z]{1,3})(\d+)(?::([A-Z]{1,3})(\d+))?")


def _expand_range(sheet, ref: str) -> list[Any]:
    """Return flat list of values inside a single A1 or A1:B2 reference."""
    m = _REF_RE.match(ref)
    if not m:
        raise C.VerifierError(C.ErrCode.PARSE_ERROR, f"unable to parse cell ref {ref!r}")
    if m.group(3) is None:
        return [sheet[ref].value]
    start = f"{m.group(1)}{m.group(2)}"
    end = f"{m.group(3)}{m.group(4)}"
    out = []
    for row in sheet[f"{start}:{end}"]:
        for cell in row:
            out.append(cell.value)
    return out


def _formula_evaluate(formula: str, sheet) -> tuple[Any, str]:
    """Best-effort eval of common one-function formulas.  Returns (value, note)."""
    f = formula.strip().lstrip("=").strip()
    m = re.match(r"^(SUM|AVERAGE|MIN|MAX|COUNT|COUNTA)\s*\((.+)\)\s*$", f, re.IGNORECASE)
    if m:
        op = m.group(1).upper()
        body = m.group(2)
        refs = [r.strip() for r in body.split(",")]
        flat: list[Any] = []
        for r in refs:
            flat.extend(_expand_range(sheet, r))
        nums = [float(v) for v in flat if isinstance(v, (int, float))]
        if op == "SUM":
            return sum(nums), f"SUM over {len(nums)} numeric values"
        if op == "AVERAGE":
            return (sum(nums) / len(nums)) if nums else None, "AVERAGE"
        if op == "MIN":
            return min(nums) if nums else None, "MIN"
        if op == "MAX":
            return max(nums) if nums else None, "MAX"
        if op == "COUNT":
            return float(len(nums)), "COUNT (numeric only)"
        if op == "COUNTA":
            return float(sum(1 for v in flat if v not in (None, ""))), "COUNTA"
    # Single arithmetic on two cell refs: A1+B1, A1-B1, A1*B1, A1/B1
    m = re.match(r"^([A-Z]+\d+)\s*([+\-*/])\s*([A-Z]+\d+)\s*$", f)
    if m:
        a = sheet[m.group(1)].value
        b = sheet[m.group(3)].value
        op = m.group(2)
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            try:
                if op == "+":
                    return a + b, f"{m.group(1)}+{m.group(3)}"
                if op == "-":
                    return a - b, f"{m.group(1)}-{m.group(3)}"
                if op == "*":
                    return a * b, f"{m.group(1)}*{m.group(3)}"
                if op == "/":
                    return (a / b) if b != 0 else None, f"{m.group(1)}/{m.group(3)}"
            except Exception:
                return None, "arithmetic error"
    return None, "unsupported formula shape (no evaluation attempted)"


def cmd_eval_formula(args: argparse.Namespace) -> dict:
    # Read formula text from the raw workbook ...
    formula_v, _ = _read_cell_value(args.file, args.sheet, args.cell, data_only=False)
    # ... and the cached computed value from the data-only workbook.
    cached_v, abs_path = _read_cell_value(args.file, args.sheet, args.cell, data_only=True)

    if not (isinstance(formula_v, str) and formula_v.startswith("=")):
        return {
            "file": abs_path, "sheet": args.sheet, "cell": args.cell,
            "is_formula": False, "raw_value": formula_v, "cached_value": cached_v,
            "passed": None, "note": "cell does not contain a formula",
            "_evidence": C.evidence(file=abs_path,
                                    locator={"sheet": args.sheet, "cell": args.cell},
                                    quote=f"non-formula value={formula_v!r}"),
        }

    # Open data-only sheet to evaluate references using the *cached* numbers.
    wb, _ = _open(args.file, data_only=True)
    try:
        sheet = _sheet(wb, args.sheet)
        eval_v, eval_note = _formula_evaluate(formula_v, sheet)
    finally:
        wb.close()

    if eval_v is None:
        passed: bool | None = None
        note = f"formula={formula_v!r}; eval skipped ({eval_note}); cached={cached_v!r}"
    else:
        ok, ttext = C.in_tolerance(cached_v, eval_v, args.tol_abs, args.tol_rel)
        passed = bool(ok)
        note = f"formula={formula_v!r}; computed={eval_v}; cached={cached_v}; {ttext}"

    return {
        "file": abs_path, "sheet": args.sheet, "cell": args.cell,
        "is_formula": True, "formula": formula_v,
        "cached_value": cached_v, "computed_value": eval_v,
        "passed": passed, "note": note,
        "_evidence": C.evidence(file=abs_path,
                                locator={"sheet": args.sheet, "cell": args.cell},
                                quote=note),
    }


# ---------------------------------------------------------------------------
# find-cell, sheet-shape, header-check, nonempty-rows, style-check, sum-range
# ---------------------------------------------------------------------------

def cmd_find_cell(args: argparse.Namespace) -> dict:
    try:
        pattern = re.compile(args.regex)
    except re.error as e:
        raise C.VerifierError(C.ErrCode.BAD_ARGS, f"invalid regex: {e}") from e
    wb, abs_path = _open(args.file, data_only=True)
    hits: list[dict] = []
    try:
        ws = _sheet(wb, args.sheet)
        for row in ws.iter_rows():
            for cell in row:
                if cell.value is None:
                    continue
                if pattern.search(str(cell.value)):
                    hits.append({"cell": cell.coordinate, "value": cell.value})
                    if len(hits) >= args.max_hits:
                        break
            if len(hits) >= args.max_hits:
                break
    finally:
        wb.close()
    return {
        "file": abs_path, "sheet": args.sheet, "regex": args.regex,
        "count": len(hits), "hits": hits,
        "_evidence": C.evidence(file=abs_path,
                                locator={"sheet": args.sheet, "regex": args.regex},
                                quote=f"{len(hits)} hits, first: " + (hits[0]["cell"] if hits else "(none)")),
    }


def cmd_sheet_shape(args: argparse.Namespace) -> dict:
    wb, abs_path = _open(args.file, data_only=True)
    try:
        ws = _sheet(wb, args.sheet)
        max_row = ws.max_row
        max_col = ws.max_column
        if args.ignore_empty:
            # trim trailing empty rows
            while max_row > 0:
                row = next(ws.iter_rows(min_row=max_row, max_row=max_row, values_only=True), ())
                if any(v not in (None, "") for v in row):
                    break
                max_row -= 1
            # trim trailing empty cols
            while max_col > 0:
                col_vals = [ws.cell(r, max_col).value for r in range(1, max_row + 1)]
                if any(v not in (None, "") for v in col_vals):
                    break
                max_col -= 1
    finally:
        wb.close()
    return {
        "file": abs_path, "sheet": args.sheet,
        "max_row": max_row, "max_col": max_col,
        "ignore_empty": args.ignore_empty,
        "_evidence": C.evidence(file=abs_path,
                                locator={"sheet": args.sheet},
                                quote=f"shape {max_row}×{max_col}" + (" (trimmed)" if args.ignore_empty else "")),
    }


def cmd_header_check(args: argparse.Namespace) -> dict:
    wb, abs_path = _open(args.file, data_only=True)
    try:
        ws = _sheet(wb, args.sheet)
        first = next(ws.iter_rows(min_row=1, max_row=1, values_only=True), ())
        actual = ["" if v is None else str(v) for v in first]
    finally:
        wb.close()

    if args.mode == "strict":
        passed = actual[: len(args.expected)] == args.expected
        missing = [e for e in args.expected if e not in actual]
        note = (f"strict: {'OK' if passed else 'mismatch'}"
                + (f", missing={missing}" if missing else ""))
    else:
        actual_set = set(actual)
        missing = [e for e in args.expected if e not in actual_set]
        passed = not missing
        note = f"subset: missing={missing}" if missing else "subset: all expected headers present"
    return {
        "file": abs_path, "sheet": args.sheet, "mode": args.mode,
        "expected": args.expected, "actual": actual,
        "passed": bool(passed), "missing": missing, "note": note,
        "_evidence": C.evidence(file=abs_path,
                                locator={"sheet": args.sheet, "row": 1},
                                quote=note),
    }


def cmd_nonempty_rows(args: argparse.Namespace) -> dict:
    wb, abs_path = _open(args.file, data_only=True)
    try:
        ws = _sheet(wb, args.sheet)
        try:
            rows = ws[args.range]
        except Exception as e:
            raise C.VerifierError(C.ErrCode.LOCATOR_INVALID,
                                  f"invalid range {args.range!r}: {e}") from e
        n = 0
        for row in rows:
            if any((c.value not in (None, "")) for c in row):
                n += 1
    finally:
        wb.close()
    return {
        "file": abs_path, "sheet": args.sheet, "range": args.range, "nonempty_rows": n,
        "_evidence": C.evidence(file=abs_path,
                                locator={"sheet": args.sheet, "range": args.range},
                                quote=f"{n} non-empty rows in {args.range}"),
    }


def cmd_style_check(args: argparse.Namespace) -> dict:
    wb, abs_path = _open(args.file, data_only=True)
    try:
        ws = _sheet(wb, args.sheet)
        cell = ws[args.cell]
        bold = bool(cell.font and cell.font.b)
        fill_rgb: str | None = None
        if cell.fill and cell.fill.fgColor and cell.fill.fgColor.type == "rgb":
            fill_rgb = (cell.fill.fgColor.rgb or "").upper()
        nf = cell.number_format
    finally:
        wb.close()

    checks: list[dict] = []
    overall = True
    if args.expect_bold is not None:
        want = args.expect_bold == "true"
        passed = bold is want
        checks.append({"check": "bold", "expected": want, "actual": bold, "passed": passed})
        overall = overall and passed
    if args.expect_fill is not None:
        want = args.expect_fill.upper().lstrip("#")
        actual = (fill_rgb or "").lstrip("FF") if fill_rgb else ""
        passed = bool(actual) and (actual.startswith(want) or want.startswith(actual))
        checks.append({"check": "fill", "expected": want, "actual": fill_rgb, "passed": passed})
        overall = overall and passed
    if args.expect_number_format is not None:
        passed = nf == args.expect_number_format
        checks.append({"check": "number_format", "expected": args.expect_number_format,
                       "actual": nf, "passed": passed})
        overall = overall and passed
    if not checks:
        # No expectations passed → just dump current style
        overall = None  # type: ignore[assignment]

    return {
        "file": abs_path, "sheet": args.sheet, "cell": args.cell,
        "bold": bold, "fill_rgb": fill_rgb, "number_format": nf,
        "checks": checks, "passed": overall,
        "_evidence": C.evidence(file=abs_path,
                                locator={"sheet": args.sheet, "cell": args.cell},
                                quote=f"bold={bold} fill={fill_rgb} nf={nf!r}"),
    }


def cmd_sum_range(args: argparse.Namespace) -> dict:
    wb, abs_path = _open(args.file, data_only=True)
    try:
        ws = _sheet(wb, args.sheet)
        try:
            rows = ws[args.range]
        except Exception as e:
            raise C.VerifierError(C.ErrCode.LOCATOR_INVALID,
                                  f"invalid range {args.range!r}: {e}") from e
        total = 0.0
        nonnumeric: list[dict] = []
        n = 0
        for row in rows:
            for c in row:
                if isinstance(c.value, (int, float)):
                    total += float(c.value)
                    n += 1
                elif c.value not in (None, ""):
                    if len(nonnumeric) < 10:
                        nonnumeric.append({"cell": c.coordinate, "value": c.value})
    finally:
        wb.close()
    return {
        "file": abs_path, "sheet": args.sheet, "range": args.range,
        "sum": total, "numeric_count": n, "nonnumeric_sample": nonnumeric,
        "_evidence": C.evidence(file=abs_path,
                                locator={"sheet": args.sheet, "range": args.range},
                                quote=f"sum={total} (n={n})"
                                + (f"; {len(nonnumeric)} nonnumeric cells" if nonnumeric else "")),
    }


# ---------------------------------------------------------------------------
# column-format — assert ALL non-empty cells in a range share a number format.
#
# Closes "Currency columns use USD currency formatting" rubric class.  Use
# --expected-format for exact equality (e.g. '$#,##0.00') or --expected-regex
# for looser matching (e.g. r'\$|USD' to accept any USD-shaped pattern).
# ---------------------------------------------------------------------------

def cmd_column_format(args: argparse.Namespace) -> dict:
    if args.expected_format is None and args.expected_regex is None:
        raise C.VerifierError(
            C.ErrCode.BAD_ARGS,
            "either --expected-format or --expected-regex is required",
        )

    pattern: re.Pattern | None = None
    if args.expected_regex is not None:
        try:
            pattern = re.compile(args.expected_regex)
        except re.error as e:
            raise C.VerifierError(C.ErrCode.BAD_ARGS,
                                  f"invalid --expected-regex: {e}") from e

    # data_only=False so number_format style is preserved (data_only=True can
    # strip styles in some openpyxl versions).
    wb, abs_path = _open(args.file, data_only=False)
    try:
        ws = _sheet(wb, args.sheet)
        try:
            rows = ws[args.range]
        except Exception as e:
            raise C.VerifierError(C.ErrCode.LOCATOR_INVALID,
                                  f"invalid range {args.range!r}: {e}") from e

        checked = 0
        skipped_empty = 0
        formats_seen: dict[str, int] = {}
        mismatches: list[dict] = []
        for row in rows:
            for c in row:
                empty = c.value in (None, "")
                if empty and not args.include_empty:
                    skipped_empty += 1
                    continue
                fmt = c.number_format or ""
                formats_seen[fmt] = formats_seen.get(fmt, 0) + 1
                checked += 1
                if args.expected_format is not None:
                    matches = fmt == args.expected_format
                else:
                    matches = bool(pattern.search(fmt))  # type: ignore[union-attr]
                if not matches and len(mismatches) < 10:
                    mismatches.append({"cell": c.coordinate, "actual": fmt})
    finally:
        wb.close()

    passed = checked > 0 and not mismatches
    note = (f"checked {checked} cells (skipped {skipped_empty} empty); "
            f"distinct formats={len(formats_seen)}; mismatches={len(mismatches)}")

    return {
        "file": abs_path, "sheet": args.sheet, "range": args.range,
        "expected_format": args.expected_format,
        "expected_regex": args.expected_regex,
        "checked": checked, "skipped_empty": skipped_empty,
        "formats_seen": formats_seen,
        "mismatch_sample": mismatches,
        "passed": passed, "note": note,
        "_evidence": C.evidence(file=abs_path,
                                locator={"sheet": args.sheet, "range": args.range},
                                quote=note + (f"; first mismatch: {mismatches[0]}"
                                              if mismatches else "")),
    }
