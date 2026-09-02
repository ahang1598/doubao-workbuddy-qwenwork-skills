#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""
xlsx_shift_rows.py — Shift all row references in an unpacked xlsx working directory
after inserting or deleting rows.

Usage:
    # Insert 2 rows at row 5 (rows 5+ shift down by 2), all sheets
    python3 xlsx_shift_rows.py <work_dir> insert 5 2

    # Insert 1 row at row 8, only Sheet1
    python3 xlsx_shift_rows.py <work_dir> insert 8 1 --sheet Sheet1

    # Delete 1 row at row 8 (rows 9+ shift up by 1)
    python3 xlsx_shift_rows.py <work_dir> delete 8 1

When --sheet is specified:
  - Only the named sheet's row numbers and cell references are physically shifted
  - All sheets still get formula references updated (cross-sheet formulas)
  - Other sheets' row/cell positions are NOT moved

What it updates in every XML file under <work_dir>:
  - <row r="N"> attributes in worksheet sheetData
  - <c r="XN"> cell address attributes in worksheet sheetData
  - <f> formula text: absolute row references (e.g. B7, $B$7, $B7) in all sheets
  - <mergeCell ref="A5:C7"> ranges
  - <conditionalFormatting sqref="..."> ranges
  - <dataValidations sqref="..."> ranges
  - <dimension ref="A1:D20"> extent marker
  - Table <table ref="A1:D20"> in xl/tables/*.xml
  - Chart series <numRef><f> and <strRef><f> range references in xl/charts/*.xml
  - PivotCache source <worksheetSource ref="..."> in xl/pivotCaches/*.xml

IMPORTANT: Run this script on the UNPACKED directory before repacking.
After running, repack with xlsx_pack.py and re-validate with formula_check.py.

Limitations:
  - Named ranges in workbook.xml <definedNames> are NOT updated automatically.
    Review them manually after running this script.
  - Structured table references (Table[@Column]) are NOT updated.
  - External workbook links in xl/externalLinks/ are NOT updated.
"""

import sys
import os
import re
import argparse
import xml.etree.ElementTree as ET
import xml.dom.minidom
import xml.parsers.expat

# Register all namespaces commonly found in xlsx files to prevent
# prefix renumbering by ElementTree (e.g. mc:Ignorable breakage).
NS_SS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

ET.register_namespace('', NS_SS)
ET.register_namespace('r', NS_REL)
ET.register_namespace('xdr', 'http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing')
ET.register_namespace('x14', 'http://schemas.microsoft.com/office/spreadsheetml/2009/9/main')
ET.register_namespace('xr2', 'http://schemas.microsoft.com/office/spreadsheetml/2015/revision2')
ET.register_namespace('mc', 'http://schemas.openxmlformats.org/markup-compatibility/2006')


def col_letter(n: int) -> str:
    """Convert 1-based column number to Excel column letter(s)."""
    r = ""
    while n > 0:
        n, rem = divmod(n - 1, 26)
        r = chr(65 + rem) + r
    return r


def col_number(s: str) -> int:
    """Convert Excel column letter(s) to 1-based column number."""
    n = 0
    for c in s.upper():
        n = n * 26 + (ord(c) - 64)
    return n


# ---------------------------------------------------------------------------
# Core shifting logic for formula strings
# ---------------------------------------------------------------------------

def _shift_refs(text: str, at: int, delta: int) -> str:
    """Shift cell references in a non-quoted formula fragment.

    Protects:
      - Function names: LOG10(...) etc. — a cell ref preceded by a letter is
        a function name, not a reference.
      - Double-quoted string literals: "B5" inside IF(A1="B5",...) is text,
        not a reference.
    """
    # Step 1: Protect double-quoted string literals with placeholders
    str_placeholders = {}

    def _protect_strings(s: str) -> str:
        result = []
        i = 0
        idx = 0
        while i < len(s):
            ch = s[i]
            if ch == '"':
                j = s.index('"', i + 1) if '"' in s[i + 1:] else len(s) - 1
                placeholder = f"\x00STRLIT{idx}\x00"
                str_placeholders[placeholder] = s[i:j + 1]
                result.append(placeholder)
                idx += 1
                i = j + 1
            else:
                result.append(ch)
                i += 1
        return ''.join(result)

    protected = _protect_strings(text)

    # Step 2: Apply reference shifting, skipping function names
    def replacer(m: re.Match) -> str:
        dollar_col = m.group(1)
        col_part = m.group(2)
        dollar_row = m.group(3)
        row_str = m.group(4)
        row = int(row_str)

        # Skip if column part is 3+ letters → cannot be a real cell ref
        # (catches function names like LOG10 where LOG≠valid column,
        #  SUM100, MAX1000, etc.)
        if len(col_part) >= 3:
            return m.group(0)

        # Skip if preceded by a letter → function name like IFS10, SUM10 etc.
        if m.start() > 0 and protected[m.start() - 1].isalpha():
            return m.group(0)

        if row >= at:
            row = max(1, row + delta)
        return f"{dollar_col}{col_part}{dollar_row}{row}"

    pattern = r'(\$?)([A-Z]+)(\$?)(\d+)'
    shifted = re.sub(pattern, replacer, protected)

    # Step 3: Restore string literals
    for placeholder, original in str_placeholders.items():
        shifted = shifted.replace(placeholder, original)

    return shifted


def shift_formula(formula: str, at: int, delta: int) -> str:
    """
    Shift absolute and mixed row references >= `at` by `delta` in a formula string.

    Handles:
      B7       (relative col, absolute row — shifts if row >= at)
      $B$7     (absolute col, absolute row — shifts)
      $B7      (absolute col, relative row — shifts)
      B$7      (relative col, absolute — shifts)
      BUT NOT:  B:B  (whole-column reference — left as-is)

    Skips content inside single-quoted sheet name prefixes to avoid
    corrupting names like 'Budget FY2025' (where FY2025 is NOT a cell ref).

    Does NOT handle:
      - Named ranges
      - Structured references (Table[@Col])
      - R1C1 notation
    """
    # Split on quoted sheet names: 'Sheet Name' portions are odd-indexed
    segments = re.split(r"('[^']*(?:''[^']*)*')", formula)
    result = []
    for i, seg in enumerate(segments):
        if i % 2 == 1:
            result.append(seg)
        else:
            result.append(_shift_refs(seg, at, delta))
    return "".join(result)


def shift_sqref(sqref: str, at: int, delta: int) -> str:
    """
    Shift row references in a sqref string (space-separated cell/range addresses).
    E.g. "A5:D20 B30" → shift rows >= 5 by delta.
    """
    parts = sqref.split()
    result = []
    for part in parts:
        if ':' in part:
            left, right = part.split(':', 1)
            left = shift_formula(left, at, delta)
            right = shift_formula(right, at, delta)
            result.append(f"{left}:{right}")
        else:
            result.append(shift_formula(part, at, delta))
    return " ".join(result)


def shift_chart_range(text: str, at: int, delta: int) -> str:
    """
    Shift row references inside a chart range formula like:
      Sheet1!$B$5:$B$20
      'Q1 Data'!$A$3:$A$15
    """
    # Split on the "!" to preserve sheet name
    if '!' not in text:
        return text
    bang = text.index('!')
    sheet_part = text[:bang + 1]
    range_part = text[bang + 1:]
    return sheet_part + shift_formula(range_part, at, delta)


# ---------------------------------------------------------------------------
# XML file processors
# ---------------------------------------------------------------------------

NS_DRAWING = "http://schemas.openxmlformats.org/drawingml/2006/chartDrawing"

# Namespace map used by ElementTree for tag lookup
NSMAP = {"ss": NS_SS}


def _tag(local: str) -> str:
    return f"{{{NS_SS}}}{local}"


def process_worksheet(path: str, at: int, delta: int) -> int:
    """Update row/cell references in a worksheet XML. Returns change count."""
    tree = ET.parse(path)
    root = tree.getroot()
    changes = 0

    # 1. <dimension ref="A1:D20">
    for dim in root.iter(_tag("dimension")):
        old = dim.get("ref", "")
        new = shift_sqref(old, at, delta)
        if new != old:
            dim.set("ref", new)
            changes += 1

    # 2. <row r="N"> and <c r="XN"> inside sheetData
    sheet_data = root.find(_tag("sheetData"))
    if sheet_data is not None:
        rows_to_reorder = []
        for row_el in list(sheet_data):
            r_str = row_el.get("r")
            if r_str is None:
                continue
            r = int(r_str)
            if r >= at:
                new_r = max(1, r + delta)
                row_el.set("r", str(new_r))
                changes += 1
                # Update each cell's r attribute
                for cell_el in row_el:
                    cell_ref = cell_el.get("r", "")
                    if cell_ref:
                        new_ref = shift_formula(cell_ref, at, delta)
                        if new_ref != cell_ref:
                            cell_el.set("r", new_ref)
                            changes += 1

            # Also update formulas in every row (formulas can reference any row)
            for cell_el in row_el:
                f_el = cell_el.find(_tag("f"))
                if f_el is not None and f_el.text:
                    new_f = shift_formula(f_el.text, at, delta)
                    if new_f != f_el.text:
                        f_el.text = new_f
                        changes += 1

    # 3. <mergeCell ref="A5:C7">
    for mc in root.iter(_tag("mergeCell")):
        old = mc.get("ref", "")
        new = shift_sqref(old, at, delta)
        if new != old:
            mc.set("ref", new)
            changes += 1

    # 4. <conditionalFormatting sqref="...">
    for cf in root.iter(_tag("conditionalFormatting")):
        old = cf.get("sqref", "")
        new = shift_sqref(old, at, delta)
        if new != old:
            cf.set("sqref", new)
            changes += 1

    # 5. <dataValidation sqref="...">
    for dv in root.iter(_tag("dataValidation")):
        old = dv.get("sqref", "")
        new = shift_sqref(old, at, delta)
        if new != old:
            dv.set("sqref", new)
            changes += 1

    if changes > 0:
        _write_tree(tree, path)
    return changes


def process_chart(path: str, at: int, delta: int) -> int:
    """Update data range references in a chart XML."""
    # Charts use DrawingML namespace; we look for <f> elements with range strings
    with open(path, "r", encoding="utf-8") as fh:
        content = fh.read()

    # Pattern matches content of <f>Sheet1!$A$1:$A$10</f> style elements
    def replace_f(m: re.Match) -> str:
        tag_open = m.group(1)
        inner = m.group(2)
        tag_close = m.group(3)
        new_inner = shift_chart_range(inner, at, delta)
        return f"{tag_open}{new_inner}{tag_close}"

    new_content = re.sub(r'(<(?:[^:>]+:)?f>)([^<]+)(</(?:[^:>]+:)?f>)',
                          replace_f, content)
    changes = content != new_content
    if changes:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(new_content)
    return 1 if changes else 0


def process_table(path: str, at: int, delta: int) -> int:
    """Update the ref attribute on the <table> root element."""
    tree = ET.parse(path)
    root = tree.getroot()
    # The root element IS the table
    old = root.get("ref", "")
    if not old:
        return 0
    new = shift_sqref(old, at, delta)
    if new == old:
        return 0
    root.set("ref", new)
    _write_tree(tree, path)
    return 1


def process_pivot_cache(path: str, at: int, delta: int) -> int:
    """Update worksheetSource ref in a pivot cache definition."""
    tree = ET.parse(path)
    root = tree.getroot()
    changes = 0
    # Look for <worksheetSource ref="A1:D100" ...>
    for ws in root.iter():
        if ws.tag.endswith("}worksheetSource") or ws.tag == "worksheetSource":
            old = ws.get("ref", "")
            if old:
                new = shift_sqref(old, at, delta)
                if new != old:
                    ws.set("ref", new)
                    changes += 1
    if changes:
        _write_tree(tree, path)
    return changes


def _find_sheet_path(work_dir: str, sheet_name: str) -> str:
    """Resolve a sheet name to its worksheet XML file path."""
    wb_path = os.path.join(work_dir, "xl", "workbook.xml")
    if not os.path.isfile(wb_path):
        print(f"ERROR: workbook.xml not found at {wb_path}")
        sys.exit(1)

    wb_tree = ET.parse(wb_path)
    wb_root = wb_tree.getroot()
    rid = None

    for sheet in wb_root.iter(_tag("sheet")):
        if sheet.get("name") == sheet_name:
            rid = sheet.get(f"{{{NS_REL}}}id")
            break

    if rid is None:
        print(f"ERROR: Sheet '{sheet_name}' not found in workbook.xml")
        sys.exit(1)

    rels_path = os.path.join(work_dir, "xl", "_rels", "workbook.xml.rels")
    rels_tree = ET.parse(rels_path)
    for rel in rels_tree.getroot():
        if rel.get("Id") == rid:
            target = rel.get("Target")
            # Handle absolute paths like "/xl/worksheets/sheet1.xml"
            if target.startswith("/"):
                return os.path.normpath(os.path.join(work_dir, target.lstrip("/")))
            return os.path.normpath(os.path.join(work_dir, "xl", target))

    print(f"ERROR: Relationship {rid} not found in workbook.xml.rels")
    sys.exit(1)


def process_worksheet_formulas_only(path: str, at: int, delta: int) -> int:
    """Update only formula references in a worksheet (no row shifting)."""
    tree = ET.parse(path)
    root = tree.getroot()
    changes = 0
    for f in root.iter(_tag("f")):
        if f.text:
            new_text = shift_formula(f.text, at, delta)
            if new_text != f.text:
                f.text = new_text
                changes += 1
    if changes:
        _write_tree(tree, path)
    return changes


def _write_tree(tree: ET.ElementTree, path: str) -> None:
    """Write ElementTree back to file with pretty-printing."""
    tree.write(path, encoding="unicode", xml_declaration=False)
    # Re-pretty-print for readability
    with open(path, "r", encoding="utf-8") as fh:
        raw = fh.read()
    try:
        dom = xml.dom.minidom.parseString(raw.encode("utf-8"))
        pretty = dom.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")
        lines = [line for line in pretty.splitlines() if line.strip()]
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
    except (xml.parsers.expat.ExpatError, UnicodeDecodeError):
        pass  # If pretty-print fails, leave the file as-is (already written)


# ---------------------------------------------------------------------------
# Main driver
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("work_dir", help="Unpacked xlsx working directory")
    parser.add_argument("operation", choices=["insert", "delete"],
                        help="'insert' to shift rows down, 'delete' to shift rows up")
    parser.add_argument("at", type=int, help="Row number where shift starts (inclusive)")
    parser.add_argument("count", type=int, help="Number of rows to shift")
    parser.add_argument("--sheet", default=None,
                        help="Limit physical row shifting to a single sheet. "
                             "Other sheets only get formula references updated.")
    args = parser.parse_args()

    work_dir = args.work_dir
    operation = args.operation
    at = args.at
    count = args.count
    sheet_name = args.sheet

    if operation == "insert":
        delta = count
    else:
        delta = -count

    if not os.path.isdir(work_dir):
        print(f"ERROR: Directory not found: {work_dir}")
        sys.exit(1)

    print(f"Operation : {operation} {count} row(s) at row {at} (delta={delta:+d})")
    print(f"Work dir  : {work_dir}")
    if sheet_name:
        print(f"Sheet     : {sheet_name} (only this sheet's rows are shifted)")
    print()

    # Resolve target sheet path if --sheet specified
    target_sheet_path = None
    if sheet_name:
        target_sheet_path = _find_sheet_path(work_dir, sheet_name)

    total_changes = 0

    # Process all worksheets
    ws_dir = os.path.join(work_dir, "xl", "worksheets")
    if os.path.isdir(ws_dir):
        for fname in sorted(os.listdir(ws_dir)):
            if fname.endswith(".xml"):
                fpath = os.path.join(ws_dir, fname)
                # If --sheet specified, only physically shift rows on the target sheet.
                # All sheets get formula references updated regardless.
                if sheet_name and fpath != target_sheet_path:
                    # Only update formula references (cross-sheet refs)
                    n = process_worksheet_formulas_only(fpath, at, delta)
                    if n:
                        print(f"  Updated {n:3d} formula refs in xl/worksheets/{fname} (rows not shifted)")
                        total_changes += n
                else:
                    n = process_worksheet(fpath, at, delta)
                    if n:
                        print(f"  Updated {n:3d} references in xl/worksheets/{fname}")
                        total_changes += n

    # Process all charts
    charts_dir = os.path.join(work_dir, "xl", "charts")
    if os.path.isdir(charts_dir):
        for fname in sorted(os.listdir(charts_dir)):
            if fname.endswith(".xml"):
                fpath = os.path.join(charts_dir, fname)
                n = process_chart(fpath, at, delta)
                if n:
                    print(f"  Updated chart ranges in xl/charts/{fname}")
                    total_changes += n

    # Process all tables
    tables_dir = os.path.join(work_dir, "xl", "tables")
    if os.path.isdir(tables_dir):
        for fname in sorted(os.listdir(tables_dir)):
            if fname.endswith(".xml"):
                fpath = os.path.join(tables_dir, fname)
                n = process_table(fpath, at, delta)
                if n:
                    print(f"  Updated table ref in xl/tables/{fname}")
                    total_changes += n

    # Process pivot cache definitions
    cache_dir = os.path.join(work_dir, "xl", "pivotCaches")
    if os.path.isdir(cache_dir):
        for fname in sorted(os.listdir(cache_dir)):
            if "Definition" in fname and fname.endswith(".xml"):
                fpath = os.path.join(cache_dir, fname)
                n = process_pivot_cache(fpath, at, delta)
                if n:
                    print(f"  Updated pivot source range in xl/pivotCaches/{fname}")
                    total_changes += n

    print()
    print(f"Total changes: {total_changes}")
    print()
    print("IMPORTANT: Review named ranges in xl/workbook.xml <definedNames> manually.")
    print("           Structured table references (Table[@Col]) are NOT updated.")
    print()
    print("Next steps:")
    print("  1. Review the changes above")
    print(f"  2. python3 xlsx_pack.py {work_dir} output.xlsx")
    print("  3. python3 formula_check.py output.xlsx")


if __name__ == "__main__":
    main()
