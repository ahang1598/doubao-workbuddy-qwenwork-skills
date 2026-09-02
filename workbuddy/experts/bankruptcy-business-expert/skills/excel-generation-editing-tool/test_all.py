#!/usr/bin/env python3
"""Comprehensive test for all xlsx scripts."""

import subprocess
import sys
import os
import tempfile
import zipfile


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def main():
    scripts = "scripts"
    templates = "templates/minimal_xlsx"
    passed = 0
    failed = 0
    results = []

    with tempfile.TemporaryDirectory() as tmp:
        # Prepare template xlsx
        tmpl_xlsx = os.path.join(tmp, "template.xlsx")
        with zipfile.ZipFile(tmpl_xlsx, "w", zipfile.ZIP_DEFLATED) as z:
            for root, _dirs, files in os.walk(templates):
                for f in files:
                    fpath = os.path.join(root, f)
                    arcname = os.path.relpath(fpath, templates).replace(os.sep, "/")
                    z.write(fpath, arcname)

        work = os.path.join(tmp, "work")

        def test(label, ok, details=""):
            results.append((label, ok, details))
            return ok

        # ── Test 1: unpack ──
        r = run([sys.executable, os.path.join(scripts, "xlsx_unpack.py"), tmpl_xlsx, work])
        ok = test("unpack", r.returncode == 0, r.stderr[:100] if r.returncode != 0 else "")

        # ── Test 2: pack ──
        out2 = os.path.join(tmp, "out2.xlsx")
        r = run([sys.executable, os.path.join(scripts, "xlsx_pack.py"), work, out2])
        ok2 = test("pack", r.returncode == 0 and os.path.exists(out2), r.stderr[:100] if r.returncode != 0 else "")

        # ── Test 3: shift_rows --sheet ──
        r = run([sys.executable, os.path.join(scripts, "xlsx_shift_rows.py"), work,
                 "insert", "3", "1", "--sheet", "Sheet1"])
        test("shift_rows --sheet", r.returncode == 0, r.stderr[:100] if r.returncode != 0 else "")

        # ── Test 4: insert_row ──
        r = run([sys.executable, os.path.join(scripts, "xlsx_insert_row.py"), work,
                 "--at", "3", "--sheet", "Sheet1",
                 "--text", "A=Hello", "--values", "B=42",
                 "--formula", "C=SUM(B{row})", "--copy-style-from", "2"])
        test("insert_row", r.returncode == 0, r.stderr[:100] if r.returncode != 0 else "")

        # ── Test 5: add_column with formula ──
        r = run([sys.executable, os.path.join(scripts, "xlsx_add_column.py"), work,
                 "--col", "G", "--sheet", "Sheet1",
                 "--header", "Total", "--formula", "=SUM(B{row}:E{row})",
                 "--formula-rows", "2:5"])
        test("add_column", r.returncode == 0, r.stderr[:100] if r.returncode != 0 else "")

        # ── Test 6: pack after edits ──
        out6 = os.path.join(tmp, "out6.xlsx")
        r = run([sys.executable, os.path.join(scripts, "xlsx_pack.py"), work, out6])
        ok6 = test("pack after edits",
                   r.returncode == 0 and os.path.exists(out6),
                   r.stderr[:100] if r.returncode != 0 else "")

        # ── Test 7: formula_check ──
        r = run([sys.executable, os.path.join(scripts, "formula_check.py"), out6])
        test("formula_check", r.returncode == 0, f"exit={r.returncode}")

        # ── Test 8: style_audit ──
        r = run([sys.executable, os.path.join(scripts, "style_audit.py"), out6])
        test("style_audit", r.returncode in (0, 1, 2), f"exit={r.returncode}")

        # ── Test 9: shared_strings_builder ──
        r = run([sys.executable, os.path.join(scripts, "shared_strings_builder.py"),
                 "Alpha", "Beta", "Gamma"])
        test("shared_strings_builder",
             r.returncode == 0 and "<!-- index" not in r.stdout,
             "comments found" if "<!--" in r.stdout else r.stderr[:100])

        # ── Test 10: add_column duplicate cell protection ──
        # First add cells to column H (unused), then try same column again
        r1 = run([sys.executable, os.path.join(scripts, "xlsx_add_column.py"), work,
                  "--col", "H", "--sheet", "Sheet1",
                  "--formula", "=A{row}+B{row}", "--formula-rows", "2:3"])
        test("add_column H (setup)", r1.returncode == 0, f"exit={r1.returncode}")

        r2 = run([sys.executable, os.path.join(scripts, "xlsx_add_column.py"), work,
                  "--col", "H", "--sheet", "Sheet1",
                  "--formula", "=X{row}", "--formula-rows", "2:3"])
        ok_dup = r2.returncode != 0 and "already exists" in (r2.stdout + r2.stderr)
        test("duplicate cell protection",
             ok_dup,
             f"exit={r2.returncode}, expected block" if not ok_dup else "correctly blocked")

        # ── Test 11: Windows path separator ──
        with zipfile.ZipFile(out6) as z:
            names = z.namelist()
            bad = [n for n in names if "\\" in n]
            test("path separator (/ not \\\\)",
                 not bad and "[Content_Types].xml" in names and "xl/workbook.xml" in names,
                 f"backslash: {bad}" if bad else f"{len(names)} entries")

        # ── Test 12: formula shifting protects function names ──
        # Verify that shift_formula doesn't modify LOG10, SUM10, etc.
        from scripts.xlsx_shift_rows import shift_formula
        f1 = shift_formula("=LOG10(B5)", 5, 1)  # B5 should shift, LOG10 should not
        f2 = shift_formula('=IF(A1="B5", B5, C5)', 5, 1)  # "B5" string literal should not shift
        ok_f1 = "LOG10" in f1 and "B6" in f1
        ok_f2 = '"B5"' in f2 and "B6" in f2 and "C6" in f2
        test("formula function name protection", ok_f1, f"got: {f1}")
        test("formula string literal protection", ok_f2, f"got: {f2}")

    # ── Report ──
    for label, ok, details in results:
        status = "PASS" if ok else "FAIL"
        line = f"  [{status}] {label}"
        if details:
            line += f"  ({details})"
        print(line)
        if ok:
            passed += 1
        else:
            failed += 1

    print()
    print(f"===== RESULTS: {passed} PASSED, {failed} FAILED =====")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
