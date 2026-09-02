# Formula Validation Guide

Ensure every formula in an xlsx file is provably correct before delivery. A file that opens without visible errors is not a passing file — only a file that has cleared both validation tiers is a passing file.

---

## Foundational Rules

- **Never declare PASS without running `formula_check.py` first.** Visual inspection of a spreadsheet is not validation.
- **`formula_check.py` is mandatory in every scenario.** It catches structural formula errors (broken references, syntax errors, orphan shared formulas) from the XML directly.
- **Never use openpyxl with `data_only=True` to check formula values.** Opening and saving a workbook in `data_only=True` mode permanently replaces all formulas with their last cached values. Formulas cannot be recovered afterward.
- **Auto-fix only deterministic errors.** Any fix that requires understanding business logic must be flagged for human review.

---

## Validation Architecture

```
Static Validation — XML scan, no external tools
  │
  ├── Detect: all 7 Excel error types already cached in <v> elements
  ├── Detect: cross-sheet references pointing to nonexistent sheets
  ├── Detect: formula cells with t="e" attribute (error type marker)
  ├── Detect: orphaned shared formula groups (consumers without primary)
  └── Tool: formula_check.py + manual XML inspection
```

**Why static only?**

openpyxl and all Python xlsx libraries write formula strings (e.g. `=SUM(B2:B9)`) into `<f>` elements but do not evaluate them. A freshly generated file has empty `<v>` cache elements for every formula cell. This means `formula_check.py` can only catch errors that are already encoded in the XML — either as `t="e"` cells or as structurally broken cross-sheet references.

For runtime errors (`#DIV/0!`, `#N/A`, etc.) that only appear after computation, open the file in Excel or WPS which auto-recalculates formulas on open.

---

## Tier 1 — Static Validation

Static validation requires no external tools. It works directly on the ZIP/XML structure of the xlsx file.

### Step 1: Run formula_check.py

**Standard (human-readable) output:**

```bash
python3 SKILL_DIR/scripts/formula_check.py /path/to/file.xlsx
```

**JSON output (for programmatic processing):**

```bash
python3 SKILL_DIR/scripts/formula_check.py /path/to/file.xlsx --json
```

**Single-sheet mode (faster for targeted checks):**

```bash
python3 SKILL_DIR/scripts/formula_check.py /path/to/file.xlsx --sheet Summary
```

**Summary mode (counts only, no per-cell detail):**

```bash
python3 SKILL_DIR/scripts/formula_check.py /path/to/file.xlsx --summary
```

Exit codes:
- `0` — no hard errors (PASS or PASS with heuristic warnings)
- `1` — hard errors detected, or file cannot be opened (FAIL)

#### What formula_check.py examines

The script opens the xlsx as a ZIP archive without using any Excel library. It reads `xl/workbook.xml` to enumerate sheet names and named ranges, reads `xl/_rels/workbook.xml.rels` to map each sheet to its XML file, then iterates every `<c>` element in every worksheet.

It performs five checks:

1. **Error-value detection**: If the cell has `t="e"`, its `<v>` element contains an Excel error string. The cell is recorded with its sheet name, cell reference (e.g. `C5`), the error value, and the formula text if present.

2. **Broken cross-sheet reference detection**: If the cell has an `<f>` element, the script extracts all sheet names referenced in the formula (both `SheetName!` and `'Sheet Name'!` syntax). Each name is compared against the list of sheets in `workbook.xml`. A mismatch is a broken reference.

3. **Unknown named-range detection (heuristic)**: Identifiers in formulas that are not function names, not cell references, and not found in `workbook.xml`'s `<definedNames>` are flagged as `unknown_name_ref` warnings. This is a heuristic — false positives are possible; always verify manually.

4. **Shared formula integrity**: Shared formula consumer cells (those with only `<f t="shared" si="N"/>`) are skipped for formula counting and cross-ref checks because they inherit the primary cell's formula. Only the primary cell (with `ref="..."` attribute and formula text) is checked and counted.

5. **Malformed error cells**: Cells with `t="e"` but no `<v>` child element are flagged as structural XML issues.

Hard errors (exit code 1): `error_value`, `broken_sheet_ref`, `malformed_error_cell`, `file_error`
Soft warnings (exit code 0): `unknown_name_ref` — must be verified manually but do not block delivery alone

#### Reading formula_check.py human-readable output

A clean file looks like this:

```
File   : /tmp/budget_2024.xlsx
Sheets : Summary, Q1, Q2, Q3, Q4, Assumptions
Formulas checked      : 312 distinct formula cells
Shared formula ranges : 4 ranges
Errors found          : 0

PASS — No formula errors detected
```

A file with errors looks like this:

```
File   : /tmp/budget_2024.xlsx
Sheets : Summary, Q1, Q2, Q3, Q4, Assumptions
Formulas checked      : 312 distinct formula cells
Shared formula ranges : 4 ranges
Errors found          : 4

── Error Details ──
  [FAIL] [Summary!C12] contains #REF! (formula: Q1!A0/Q1!A1)
  [FAIL] [Summary!D15] references missing sheet 'Q5'
         Formula: Q5!D15
         Valid sheets: ['Assumptions', 'Q1', 'Q2', 'Q3', 'Q4', 'Summary']
  [FAIL] [Q1!F8] contains #DIV/0!
  [WARN] [Q2!B10] uses unknown name 'GrowthAssumptions' (heuristic — verify manually)
         Formula: SUM(GrowthAssumptions)
         Defined names: ['RevenueRange', 'CostRange']

FAIL — 3 error(s) must be fixed before delivery
WARN — 1 heuristic warning(s) require manual review
```

Interpretation of each line:
- `[FAIL] [Summary!C12] contains #REF! (formula: Q1!A0/Q1!A1)` — The cell has `t="e"` and `<v>#REF!</v>`. The formula references row 0, which does not exist in Excel's 1-based system. This is an off-by-one error in a generated reference.
- `[FAIL] [Summary!D15] references missing sheet 'Q5'` — The formula contains `Q5!D15`, but no sheet named `Q5` exists in the workbook. The valid sheet list is provided for comparison.
- `[FAIL] [Q1!F8] contains #DIV/0!` — This cell's `<v>` is already an error value (the file was previously recalculated). The formula divided by zero.
- `[WARN] [Q2!B10] uses unknown name 'GrowthAssumptions'` — The identifier `GrowthAssumptions` appears in the formula but is not in `<definedNames>`. This may be a typo or a name that was accidentally omitted. It is a heuristic warning — verify manually. The warning alone does not block delivery.

#### Reading formula_check.py JSON output

```json
{
  "file": "/tmp/budget_2024.xlsx",
  "sheets_checked": ["Summary", "Q1", "Q2", "Q3", "Q4", "Assumptions"],
  "formula_count": 312,
  "shared_formula_ranges": 4,
  "error_count": 4,
  "errors": [
    {
      "type": "error_value",
      "error": "#REF!",
      "sheet": "Summary",
      "cell": "C12",
      "formula": "Q1!A0/Q1!A1"
    },
    {
      "type": "broken_sheet_ref",
      "sheet": "Summary",
      "cell": "D15",
      "formula": "Q5!D15",
      "missing_sheet": "Q5",
      "valid_sheets": ["Assumptions", "Q1", "Q2", "Q3", "Q4", "Summary"]
    },
    {
      "type": "error_value",
      "error": "#DIV/0!",
      "sheet": "Q1",
      "cell": "F8",
      "formula": null
    },
    {
      "type": "unknown_name_ref",
      "sheet": "Q2",
      "cell": "B10",
      "formula": "SUM(GrowthAssumptions)",
      "unknown_name": "GrowthAssumptions",
      "defined_names": ["RevenueRange", "CostRange"],
      "note": "Heuristic check — verify manually if this is a false positive"
    }
  ]
}
```

Field reference:

| Field | Meaning |
|-------|---------|
| `type: "error_value"` | Cell has `t="e"` — an Excel error is stored in the `<v>` element |
| `type: "broken_sheet_ref"` | Formula references a sheet name not present in workbook.xml |
| `type: "unknown_name_ref"` | Formula references an identifier not in `<definedNames>` (heuristic, soft warning) |
| `type: "malformed_error_cell"` | Cell has `t="e"` but no `<v>` child — structural XML problem |
| `type: "file_error"` | The file could not be opened (bad ZIP, not found, etc.) |
| `sheet` | The sheet where the error was found |
| `cell` | Cell reference in A1 notation |
| `formula` | The full formula text from the `<f>` element (null if not present) |
| `error` | The error string from `<v>` (for `error_value` type) |
| `missing_sheet` | The sheet name extracted from the formula that does not exist |
| `valid_sheets` | All sheet names actually present in workbook.xml |
| `unknown_name` | The identifier that was not found in `<definedNames>` |
| `defined_names` | All named ranges actually present in workbook.xml |
| `shared_formula_ranges` | Count of shared formula definitions (top-level `<f t="shared" ref="...">` elements) |

### Step 2: Manual XML inspection

When formula_check.py reports errors, unpack the file to inspect the raw XML:

```bash
python3 SKILL_DIR/scripts/xlsx_unpack.py /path/to/file.xlsx /tmp/xlsx_inspect/
```

Navigate to the worksheet file for the reported sheet. The sheet-to-file mapping is in `xl/_rels/workbook.xml.rels`. For example, if `rId1` maps to `worksheets/sheet1.xml`, then sheet1.xml is the file for the sheet with `r:id="rId1"` in `xl/workbook.xml`.

For each reported error cell, locate the `<c r="CELLREF">` element and examine:

**For `error_value` errors:**
```xml
<!-- This is what an error cell looks like in XML -->
<c r="C12" t="e">
  <f>Q1!C10/Q1!C11</f>
  <v>#DIV/0!</v>
</c>
```

Ask:
- Is the `<f>` formula syntactically correct?
- Does the cell reference in the formula point to a row/column that exists?
- If it is a division, is it possible the denominator cell is empty or zero?

**For `broken_sheet_ref` errors:**

Check `xl/workbook.xml` for the actual sheet list:

```xml
<sheets>
  <sheet name="Summary" sheetId="1" r:id="rId1"/>
  <sheet name="Q1"      sheetId="2" r:id="rId2"/>
  <sheet name="Q2"      sheetId="3" r:id="rId3"/>
</sheets>
```

Sheet names are case-sensitive. `q1` and `Q1` are different sheets. Compare the name in the formula exactly against the names here.

### Step 3: Cross-sheet reference audit (multi-sheet workbooks)

For workbooks with 3 or more sheets, run a broader cross-reference audit after unpacking:

```bash
# Extract all formulas containing cross-sheet references
grep -h "<f>" /tmp/xlsx_inspect/xl/worksheets/*.xml | grep "!"

# List all actual sheet names from workbook.xml
grep -o 'name="[^"]*"' /tmp/xlsx_inspect/xl/workbook.xml | grep -v sheetId
```

Every sheet name appearing in formulas (in the form `SheetName!` or `'Sheet Name'!`) must appear in the workbook sheet list. If any do not match, that is a broken reference even if formula_check.py did not catch it (which can happen with shared formulas where only the primary cell is examined).

To check shared formulas specifically, look for `<f t="shared" ref="...">` elements:

```xml
<!-- Shared formula: defined on D2, applied to D2:D100 -->
<c r="D2"><f t="shared" ref="D2:D100" si="0">Q1!B2*C2</f><v></v></c>

<!-- Shared formula consumers: only si is present, no formula text -->
<c r="D3"><f t="shared" si="0"/><v></v></c>
```

formula_check.py reads the formula text from the primary cell (`D2` above). The referenced sheet `Q1` in that formula applies to the entire range `D2:D100`. If the sheet is broken, all 99 rows are broken even though they appear as empty `<f>` elements.

---

## All 7 Error Types — Causes and Fix Strategies

### #REF! — Invalid Cell Reference

**What it means:** The formula references a cell, range, or sheet that no longer exists or never existed.

**Common causes in generated files:**
- Off-by-one error in row/column calculation (e.g., referencing row 0 which does not exist in Excel's 1-based system)
- Column letter computed incorrectly (e.g., column 64 maps to `BL`, not `BK`)
- Formula references a sheet that was never created or was renamed

**XML signature:**
```xml
<c r="D5" t="e">
  <f>Sheet2!A0</f>
  <v>#REF!</v>
</c>
```

**Fix — correct the reference:**
```xml
<c r="D5">
  <f>Sheet2!A1</f>
  <v></v>
</c>
```

Note: remove `t="e"` and clear `<v>` after correcting the formula. The error type marker belongs to the cached state, not the formula.

**Auto-fixable?** Only if the correct target can be determined with certainty from the surrounding context. Otherwise flag for human review.

---

### #DIV/0! — Division by Zero

**What it means:** The formula divides by a value that is zero or an empty cell (empty cells evaluate to 0 in arithmetic context).

**Common causes in generated files:**
- Percentage change formula `=(B2-B1)/B1` where `B1` is empty or zero
- Rate formula `=Value/Total` where the total row hasn't been populated yet

**XML signature:**
```xml
<c r="C8" t="e">
  <f>B8/B7</f>
  <v>#DIV/0!</v>
</c>
```

**Fix — wrap with IFERROR:**
```xml
<c r="C8">
  <f>IFERROR(B8/B7,0)</f>
  <v></v>
</c>
```

Alternative — explicit zero check:
```xml
<c r="C8">
  <f>IF(B7=0,0,B8/B7)</f>
  <v></v>
</c>
```

**Auto-fixable?** Yes. Wrapping with `IFERROR(...,0)` is safe for most financial formulas. If the business expectation is that the result should display as blank rather than zero, use `IFERROR(...,"")` instead.

---

### #VALUE! — Wrong Data Type

**What it means:** The formula attempts an arithmetic or logical operation on a value of the wrong type (e.g., adding a text string to a number).

**Common causes in generated files:**
- A cell intended to hold a number was written as a string type (`t="s"` or `t="inlineStr"`) instead of a numeric type
- A formula references a cell containing text (e.g., a unit label like "thousands") and treats it as a number

**XML signature:**
```xml
<c r="F3" t="e">
  <f>E3+D3</f>
  <v>#VALUE!</v>
</c>
```

**Fix — check source cells for incorrect type:**

If `D3` was incorrectly written as a string:
```xml
<!-- Wrong: numeric value stored as string -->
<c r="D3" t="inlineStr"><is><t>1000</t></is></c>

<!-- Correct: numeric value stored as number (t attribute omitted or "n") -->
<c r="D3"><v>1000</v></c>
```

Alternatively, wrap the formula with `VALUE()` conversion:
```xml
<c r="F3">
  <f>VALUE(E3)+VALUE(D3)</f>
  <v></v>
</c>
```

**Auto-fixable?** Partially. If the source cell type is visibly wrong (a number stored as string), fix the type. If the cause is ambiguous (the cell is supposed to contain text), flag for human review.

---

### #NAME? — Unrecognized Name

**What it means:** The formula contains an identifier that Excel does not recognize — either a misspelled function name, an undefined named range, or a function that is not available in the target Excel version.

**Common causes in generated files:**
- LLM writes a function name with a typo: `SUMIF` written as `SUMIFS` when only 3 arguments are provided, or `XLOOKUP` used in a context targeting Excel 2010
- Named range referenced in formula does not exist in `xl/workbook.xml`

**XML signature:**
```xml
<c r="B2" t="e">
  <f>SUMSQ(A2:A10)</f>
  <v>#NAME?</v>
</c>
```

**Fix — verify function name and named ranges:**

Check named ranges in `xl/workbook.xml`:
```xml
<definedNames>
  <definedName name="RevenueRange">Sheet1!$B$2:$B$13</definedName>
</definedNames>
```

If the formula references `RevenuRange` (typo), correct it to `RevenueRange`:
```xml
<c r="B2">
  <f>SUM(RevenueRange)</f>
  <v></v>
</c>
```

**Auto-fixable?** Only if the correct name is unambiguous (e.g., a single close match exists). Otherwise flag for human review — function name fixes require understanding the intended calculation.

---

### #N/A — Value Not Available

**What it means:** A lookup function (VLOOKUP, HLOOKUP, MATCH, INDEX/MATCH, XLOOKUP) searched for a value that does not exist in the lookup table.

**Common causes in generated files:**
- Lookup key exists in the formula but the lookup table is empty or not yet populated
- Key format mismatch (text "2024" vs numeric 2024)

**XML signature:**
```xml
<c r="G5" t="e">
  <f>VLOOKUP(F5,Assumptions!$A$2:$B$20,2,0)</f>
  <v>#N/A</v>
</c>
```

**Fix — wrap with IFERROR for missing-match tolerance:**
```xml
<c r="G5">
  <f>IFERROR(VLOOKUP(F5,Assumptions!$A$2:$B$20,2,0),0)</f>
  <v></v>
</c>
```

**Auto-fixable?** Adding `IFERROR` is safe if a zero default is acceptable. If the lookup failure indicates a data integrity problem (the key should always be present), do not auto-fix — flag for human review.

---

### #NULL! — Empty Intersection

**What it means:** The space operator (which computes the intersection of two ranges) was applied to two ranges that do not intersect.

**Common causes in generated files:**
- Accidental space between two range references: `=SUM(A1:A5 C1:C5)` instead of `=SUM(A1:A5,C1:C5)`
- Rarely seen in typical financial models; usually indicates a formula generation error

**XML signature:**
```xml
<c r="H10" t="e">
  <f>SUM(A1:A5 C1:C5)</f>
  <v>#NULL!</v>
</c>
```

**Fix — replace space with comma (union) or colon (range):**
```xml
<!-- Union of two separate ranges -->
<c r="H10">
  <f>SUM(A1:A5,C1:C5)</f>
  <v></v>
</c>
```

**Auto-fixable?** Yes. The space operator is almost never intentional in generated formulas. Replacing with a comma is safe.

---

### #NUM! — Numeric Error

**What it means:** A formula produced a number that Excel cannot represent (overflow, underflow) or a mathematical operation that has no real-number result (square root of negative, LOG of zero or negative).

**Common causes in generated files:**
- IRR or NPV formula where the cash flow series has no convergent solution
- `SQRT()` applied to a cell that can be negative
- Very large exponentiation

**XML signature:**
```xml
<c r="J15" t="e">
  <f>IRR(B5:B15)</f>
  <v>#NUM!</v>
</c>
```

**Fix — add a conditional guard:**
```xml
<c r="J15">
  <f>IFERROR(IRR(B5:B15),"")</f>
  <v></v>
</c>
```

For SQRT:
```xml
<c r="K5">
  <f>IF(A5>=0,SQRT(A5),"")</f>
  <v></v>
</c>
```

**Auto-fixable?** Partially. Wrapping with `IFERROR` suppresses the error display but does not fix the underlying calculation issue. Flag the cell for human review even after applying the IFERROR wrapper.

---

## Auto-Fix vs. Human Review Decision Matrix

| Error Type | Auto-Fix Safe? | Condition | Action |
|------------|---------------|-----------|--------|
| `#DIV/0!` | Yes | Always | Wrap with `IFERROR(formula,0)` |
| `#NULL!` | Yes | Always | Replace space operator with comma |
| `#REF!` | Yes | Only if correct target is unambiguous from context | Correct reference; otherwise flag |
| `#NAME?` | Yes | Only if typo has exactly one plausible correction | Fix name; otherwise flag |
| `#N/A` | Conditional | If a zero/blank default is business-acceptable | Add IFERROR wrapper; document assumption |
| `#VALUE!` | Conditional | Only if source cell type is clearly wrong | Fix type; otherwise flag |
| `#NUM!` | No | Always | Add IFERROR to suppress display, then flag |
| Broken sheet ref | Yes | Only if renamed sheet can be identified from workbook.xml | Correct name |
| Business logic errors | Never | Any case | Human review only |

**What counts as a business logic error (never auto-fix):**
- A formula that produces a wrong number but no Excel error (e.g., `=SUM(B2:B8)` when the intent was `=SUM(B2:B9)`)
- A formula where the IFERROR default value is meaningful (e.g., whether to use 0, blank, or a prior-period value)
- Any formula where fixing the error requires knowing what the formula was supposed to calculate

---

## Delivery Standard — Validation Report

Every validation task must produce a structured report. This report is the deliverable, regardless of whether errors were found.

### Required report format

```markdown
## Formula Validation Report

**File**: /path/to/filename.xlsx
**Date**: YYYY-MM-DD
**Sheets checked**: Sheet1, Sheet2, Sheet3
**Total formulas scanned**: N

---

### Tier 1 — Static Validation

**Status**: PASS / FAIL
**Tool**: formula_check.py (direct XML scan)

| Sheet | Cell | Error Type | Detail | Fix Applied |
|-------|------|-----------|--------|-------------|
| Summary | C12 | #REF! | Formula: Q1!A0 | Corrected to Q1!A1 |
| Summary | D15 | broken_sheet_ref | References missing sheet 'Q5' | Renamed to Q4 |

_(If no errors: "No errors detected.")_

---

### Summary

- **Total errors found**: N
- **Auto-fixed**: N (list types)
- **Flagged for human review**: N (list cells and reason)
- **Final status**: PASS (ready for delivery) / FAIL (blocked)

### Human Review Required

| Cell | Error | Reason Auto-Fix Not Applied |
|------|-------|----------------------------|
| Q2!B15 | #NUM! | IRR formula — business must confirm cash flow inputs |
```

### Minimum required fields

The report is invalid (and delivery is blocked) if any of these are missing:
- File path and date
- Which sheets were checked
- Total formula count
- Validation status with explicit PASS/FAIL
- For every error: sheet, cell, error type, and disposition (fixed or flagged)
- Final delivery status

---

## Common Scenarios

### Scenario 1: Validate immediately after creating a new file

When `create.md` workflow produces a new xlsx, run validation before any delivery response.

```bash
# Static check on the freshly written file
python3 SKILL_DIR/scripts/formula_check.py /path/to/output.xlsx
```

Expected behavior on a freshly created file: `formula_check.py` will find zero `error_value` errors (because `<v>` elements are empty, not error-valued). It will find any broken cross-sheet references if sheet names were misspelled. For runtime errors (like `#DIV/0!`), open the file in Excel/WPS which auto-recalculates formulas on open.

### Scenario 2: Validate after editing an existing file

When `edit.md` workflow modifies an existing xlsx, validate only the affected sheets if the edit was surgical. If the edit touched shared formulas or cross-sheet references, validate all sheets.

```bash
# Targeted static check — look at specific sheet
# (formula_check.py checks all sheets; examine only the relevant section of output)
python3 SKILL_DIR/scripts/formula_check.py /path/to/edited.xlsx --json \
  | python3 -c "
import json, sys
r = json.load(sys.stdin)
for e in r['errors']:
    if e.get('sheet') in ['Summary', 'Q1']:
        print(e)
"
```

If the edit modifies formulas, open the file in Excel/WPS after editing to verify runtime results — edits to data ranges can cause previously-valid formulas to produce runtime errors.

### Scenario 3: User provides a file with suspected formula errors

When a user submits a file and reports wrong values or visible errors:

```bash
# Step 1: Static scan — find all error cells
python3 SKILL_DIR/scripts/formula_check.py /path/to/user_file.xlsx --json > /tmp/validation_results.json

# Step 2: Unpack for manual inspection
python3 SKILL_DIR/scripts/xlsx_unpack.py /path/to/user_file.xlsx /tmp/xlsx_inspect/
```

Fix any errors found, repack, and re-run `formula_check.py`.

---

## Critical Pitfalls

**Pitfall 1: openpyxl `data_only=True` destroys formulas.**
Opening a workbook with `data_only=True` reads cached values instead of formulas. If you then save the workbook, all `<f>` elements are permanently removed and replaced with their last-cached values. Never use this mode for validation workflows.

**Pitfall 2: Empty `<v>` is not the same as a passing formula.**
A freshly generated file has empty `<v>` elements for all formula cells. formula_check.py will not report these as errors — they are not yet errors. They become errors only after opening in Excel/WPS which auto-recalculates formulas and surfaces runtime errors like `#DIV/0!`.

**Pitfall 3: Shared formula errors affect the entire range.**
If a shared formula's primary cell has a broken reference, every cell in the shared range (`ref="D2:D100"`) inherits that broken reference. The count of logical errors can be much larger than the count of distinct error entries in formula_check.py output. When fixing a broken shared formula, fix the primary cell's `<f t="shared" ref="...">` element; the consumers (`<f t="shared" si="N"/>`) automatically inherit the corrected formula.

**Pitfall 4: Sheet names are case-sensitive.**
`=q1!B5` and `=Q1!B5` are different references. Excel internally treats them the same, but formula_check.py's string comparison is case-sensitive. If a formula uses a lowercase sheet name that matches an uppercase sheet in the workbook, it will be flagged as a broken reference. The fix is to match the exact case in `workbook.xml`.
