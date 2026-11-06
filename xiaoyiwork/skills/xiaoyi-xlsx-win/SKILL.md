---
name: xiaoyi-xlsx-win
description: "Create, edit, or fix spreadsheet files (.xlsx/.xlsm/.csv/.tsv). Trigger whenever the task produces or modifies a spreadsheet — even if the user never says 'Excel'. Covers: data analysis, sorting, filtering, pivot summaries, formulas (VLOOKUP/INDEX+MATCH/SUMIFS), charts, cross-sheet references, conditional formatting, financial models, budgets, trackers, and invoices. Implicit triggers include: '帮我做个表', '整理/分析/汇总/对比数据', 'organize this data', 'build a budget', 'chart this'. More broadly, if the user asks to analyze, summarize, compare, track, or visualize data and a spreadsheet is the natural output, use this skill. Always trigger for uploaded .xlsx/.csv/.tsv files. Keywords: 表格/数据分析/汇总/对比/图表/跨表/财务/dashboard/chart. Do NOT trigger when the primary deliverable is a Word doc, HTML report, standalone script, or database pipeline."
---

## Excel File Creation: Python + openpyxl/pandas

Python dependencies are declared in the Skill root `requirements.txt` and installed in the background by 小艺 Work. Do not run `pip install` during a task; if dependencies are not ready, wait for installation or retry from the skill page.

> **Final output**: Run generated code from the current task workspace. Build the workbook path with `(Path.cwd() / '<name>.xlsx').resolve()`, keep temporary validation files outside the final path, and call `send_file_to_user(abs_file_path_list=["<output_path 的绝对路径>"])` after AIGC marking and validation. Never only print the path.

> **Path Convention**: All paths in this document are **relative to the skill root** (the directory containing this `SKILL.md`). Generated scripts must derive the skill root from the `<location>` tag and store it in `SKILL_DIR`:
> 
> ```python
> import sys, os
> SKILL_DIR = os.path.dirname('<this skill's location path>')  # e.g. /mnt/skills/user/xiaoyi-xlsx
> ```
> 
> Then reference sub-paths as `os.path.join(SKILL_DIR, 'scripts')`, `os.path.join(SKILL_DIR, 'scripts/recalc.py')`, etc.

**✅ REQUIRED Technology Stack:**

- **Runtime**: Python 3
- **Primary Library**: openpyxl (Excel creation, styling, formulas)
- **Data Processing**: pandas (manipulation, then export via openpyxl)
- **Execution**: Write code to `.py` file, run with `python3 <filename>.py`

---

## 1. Sheet-by-Sheet Iterative Workflow

When the workbook involves formulas, references, or calculations, follow this strict per-sheet pipeline. **Never create all sheets first then check — errors cascade.**

### Per-Sheet Pipeline

For each sheet, execute in order:

1. **PLAN** — Design structure, data layout, formulas, cross-sheet references.
2. **CREATE** — Write data, formulas, and styles. Preserve original formatting.
3. **SAVE** — `wb.save()` immediately. 
4. **RECALC** — `python3 {SKILL_DIR}/scripts/recalc.py <file>.xlsx` (where `SKILL_DIR` is the skill root). Check returned JSON:
   
   - `status: success` → proceed to CHECK
   
   - `status: errors_found` → fix locations in `error_summary`, re-run (max 3 retries, then report failure)
5. **CHECK** — No `#VALUE!`, `#DIV/0!`, `#REF!`, `#NAME?`, `#N/A`, no suspicious zeros.
6. **NEXT** — Only proceed when current sheet is error-free.

### Workbook-Level Sequence

```
 ┌─ create_cover_page()          ← Phase 1: layout only, no formulas
 │
 │  ┌─ Sheet A: PLAN→CREATE→SAVE→RECALC→CHECK
 │  ├─ Sheet B: PLAN→CREATE→SAVE→RECALC→CHECK
 │  └─ Sheet C: ...
 │
 ├─ finalize_cover_page()        ← Phase 2: inject formulas + Sheet Index
 ├─ VALIDATE                     ← Full workbook audit (all cross-refs, Cover completeness)
 └─ DELIVER
```

### Recalc Script Output Format

```json
{
  "status": "success",
  "total_errors": 0,
  "total_formulas": 42,
  "error_summary": {
    "#REF!": { "count": 2, "locations": ["Sheet1!B5", "Sheet1!C10"] }
  }
}
```

### Progress Reporting

Report progress **between tool calls**, not batched at the end:

| Step   | Report Format                         |
| ------ | ------------------------------------- |
| GEN    | `⏳ 正在生成 [sheet名] — [简要描述内容，如"销售汇总表"]` |
| DONE   | `✅ [sheet名] — 已完成`                    |
| RECALC | `🔄 公式重算中… 共 N 个公式，错误 N 个`            |
| CHECK  | `🔍 [sheet名] — PASS ✅ / FAIL ❌`       |
| Final  | `📊 完成！共 N 个工作表，M 个公式，0 错误`           |

### Rules

- ❌ Never batch-create all sheets then check afterward
- ❌ Never skip PLAN, RECALC, or CHECK for any sheet
- ❌ Never silently move to next sheet without reporting status
- ✅ Fix all errors before moving on; max 3 RECALC retries per sheet

---

## 2. Cover Page (Multi-Sheet Workbooks)

| Sheet Count (excluding Cover) | Cover Page Behavior                                   |
| ----------------------------- | ----------------------------------------------------- |
| ≥ 3 sheets                    | **Create by default** unless user explicitly declines |
| 2 sheets                      | Recommended but optional                              |
| 1 sheet or plain data export  | **Do not create**                                     |

### Module Location

All Cover Page code and the **PALETTE definition** live in `scripts/cover.py`. Generated scripts must import:

```python
import sys, os
SKILL_DIR = os.path.dirname('<this skill's location path>')
sys.path.insert(0, os.path.join(SKILL_DIR, 'scripts'))
from cover import PALETTE, create_cover_page, finalize_cover_page
```

> ⚠️ PALETTE is defined once and only once in `cover.py`. Data sheets pull colors from the same PALETTE. **Never redefine PALETTE in generated scripts.**

### Two-Phase Creation

The Cover Page layout is built first, but formulas are injected later — because the data sheets referenced by Key Metrics do not exist yet during Phase 1.

| Phase                   | When                                   | What                                                   |
| ----------------------- | -------------------------------------- | ------------------------------------------------------ |
| `create_cover_page()`   | Workflow START                         | Title, subtitle, style frame. Metrics rows left empty. |
| `finalize_cover_page()` | After all data sheets, before VALIDATE | Inject cross-sheet formulas, build Sheet Index.        |

### API Signatures

```python
create_cover_page(wb, title: str, subtitle: str, style: str = 'pure') -> Worksheet
```

- `style`: `'pure'` (default) or `'finance'`

```python
finalize_cover_page(
    wb,
    metrics: list[dict],        # [{'label': str, 'ref': '=Sheet!B2'} | {'label': str, 'value': any}]
    sheet_desc: dict | None,    # {'SheetName': 'description'}, None to leave blank
    notes: str | None         # Optional footer text
) -> Worksheet
```

- Use `'ref'` for cross-sheet formulas (dynamic); `'value'` only for constants known at generation time

### Typical Usage

```python
from openpyxl import Workbook
from cover import PALETTE, create_cover_page, finalize_cover_page

wb = Workbook(); wb.remove(wb.active)
create_cover_page(wb, 'Q3 Sales Report', 'Regional KPI analysis', style='pure')

# ... build data sheets (use P = PALETTE['pure'] for colors) ...

finalize_cover_page(wb,
    metrics=[
        {'label': 'Total Revenue', 'ref': '=Analysis!B2'},
        {'label': 'Growth Rate',   'ref': '=Analysis!B3'},
    ],
    sheet_desc={'Analysis': 'Regional sales breakdown', 'Charts': 'Key trend charts'},
    notes='Data as of 2024-09-30.')
from pathlib import Path
output_path = (Path.cwd() / 'output.xlsx').resolve()
wb.save(output_path)
```

### Rules

- ❌ Never write cross-sheet formulas in Phase 1
- ❌ Never hardcode colors outside `PALETTE`
- ❌ Never redefine PALETTE in generated scripts — always `from cover import PALETTE`
- ✅ Single-sheet or simple data tasks may omit the Cover Page
- ✅ Always `create_cover_page()` first, `finalize_cover_page()` before VALIDATE
- ✅ Use `'ref'` for cross-sheet metrics; `'value'` only for generation-time constants

---

## 3. Formula-First Policy

Prefer Excel formulas over Python pre-calculation. Workbooks should remain dynamic.

### Preferred

```python
ws['C2'] = '=A2+B2'              # Dynamic formula
ws['B6'] = 0.05                  # Assumption cell — blue font, labelled
ws['C5'] = '=B5*(1+$B$6)'       # References assumption, not hardcoded 1.05
```

### Avoid

```python
ws['C2'] = value_a + value_b     # Static — loses dynamic capability
ws['C5'] = '=B5*1.05'           # Magic number — not updateable
```

Place ALL assumptions in dedicated cells with **blue font**. Never hardcode numeric constants in formulas.

### When Static Values Are Acceptable

- External source data (web APIs, search results, user-provided constants)
- True constants (e.g. days in a week)
- Circular reference avoidance
- Complex pandas aggregations with no clean formula equivalent

### Source Annotation (Mandatory for Static Values)

```
Source: [media/system], [date], [specific reference]
```

Examples: `Source: 新华网, 2024-03, 2024年营收数据` · `Source: web_search, 2025-07, IDC手机出货量报告`

---

## 4. Formula Construction & Verification

### Pre-Write Checklist

- [ ] **Column mapping**: DataFrame col index ≠ Excel column letter (off-by-one is common)
- [ ] **Row offset**: DataFrame 0-indexed → Excel 1-indexed (DF row 5 = Excel row 6)
- [ ] **NaN handling**: `pd.notna()` before writing to avoid broken formula chains
- [ ] **Division by zero**: Wrap with `IFERROR` when denominators may be zero
- [ ] **Cross-sheet format**: `SheetName!$A$2:$C$100` — if the sheet name contains spaces, special characters, or is in non-ASCII (e.g. Chinese), **must** wrap in single quotes: `'营收分析'!$A$2:$C$100`

### IFERROR Wrapper (use proactively)

```python
ws['D2'] = '=IFERROR(B2/C2, "-")'
ws['E2'] = '=IFERROR(VLOOKUP(A2,$G$2:$I$50,3,FALSE), "N/A")'
```

### ⚠️ data_only=True Warning

**Never open with `data_only=True` then save** — permanently replaces all formulas with cached values.

```python
# DANGER
wb = load_workbook('file.xlsx', data_only=True)
wb.save('file.xlsx')  # All formulas gone permanently

# SAFE
wb = load_workbook('file.xlsx')
```

---

## 5. VLOOKUP / INDEX+MATCH Rules

### Trigger Keywords

"based on", "from another table", "match against", "lookup", shared keys, master-detail, code-to-name mapping, cross-sheet linkage.

### Syntax

- Default: `=VLOOKUP(lookup_value, table_array, col_index_num, FALSE)`
- Lookup column must be leftmost of `table_array`; if not → use `INDEX/MATCH`
- Always: `FALSE` for exact match, lock ranges with `$`, wrap with `IFERROR`

```python
ws['D2'] = '=IFERROR(VLOOKUP(A2,$G$2:$I$50,3,FALSE),"N/A")'
```

---

## 6. Chart Creation Rules

### When to Create Charts

If user asks for charts/visuals, MUST actively create them. Each prepared dataset should have at least one chart unless user says otherwise.

**Trigger Keywords**: "visual", "chart", "graph", "visualization", "diagram", "图表", "可视化"

### Requirements

- ❌ Never create a "chart data" sheet with manual instructions
- ❌ Never tell the user to create charts themselves
- ✅ Use `openpyxl.chart` for embedded charts in .xlsx
- Standalone PNG/JPG only if user explicitly requests

### Chart Configuration

**Single source of truth** for chart type selection, sizing, layout, rendering, and code examples: `references/charts.md`. Always read it before creating charts. This section only defines _when_ to create charts; `charts.md` defines _how_.

---

## 7. Visual Style Guide — PALETTE Reference

### PALETTE Definition Location

**Single source of truth**: the `PALETTE` dict in `scripts/cover.py`.

```python
from cover import PALETTE

P = PALETTE['pure']     # Default for all non-financial tasks
P = PALETTE['finance']  # Financial / fiscal analysis tasks only
```

| Style       | When to Use                                                                                |
| ----------- | ------------------------------------------------------------------------------------------ |
| **pure**    | Default for all non-financial tasks                                                        |
| **finance** | Financial / fiscal analysis only (stocks, GDP, salary, revenue, profit, budget, ROI, etc.) |

### 7.1 Key Principles (Both Styles)

- Hide gridlines: `ws.sheet_view.showGridLines = False`
- Use `openpyxl` for all styling (not pandas)
- Preserve original styles when editing existing files

**Text Color Convention (Mandatory)**
| Color | Meaning |
|-------|---------|
| **Blue** | Fixed / input values (including assumptions) |
| **Black** | Calculated formula cells |
| **Green** | Cross-worksheet references |
| **Red** | External link references |

**Border Style**: Default no borders. Thin 1px for internal structure, 2px for section dividers. Only add borders to highlight results or sections.

### 7.2 Using PALETTE in Data Sheets

```python
from cover import PALETTE
from openpyxl.styles import PatternFill, Font, Border, Side, Alignment

P = PALETTE['pure']  # or PALETTE['finance']

# ── Build style objects directly from P ──
thin_border = Border(
    left=Side(style='thin', color=P['border']),
    right=Side(style='thin', color=P['border']),
    top=Side(style='thin', color=P['border']),
    bottom=Side(style='thin', color=P['border']))

header_fill  = PatternFill(start_color=P['header_bg'], end_color=P['header_bg'], fill_type="solid")
header_font  = Font(color="FFFFFF", bold=True, name="Arial", size=11)
header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
body_font    = Font(color=P['text_primary'], name="Arial", size=10)
alt_row_fill = PatternFill(start_color=P['bg_alt'], end_color=P['bg_alt'], fill_type="solid")
```

### 7.3 Pure Style — Color Quick Reference

| Purpose             | Key              | Hex       |
| ------------------- | ---------------- | --------- |
| Title / header fill | `header_bg`      | `#1B3A5C` |
| Primary accent      | `accent`         | `#2C6FAC` |
| Body text           | `text_primary`   | `#212529` |
| Secondary text      | `text_secondary` | `#6C757D` |
| Primary background  | `bg_main`        | `#FFFFFF` |
| Alternating rows    | `bg_alt`         | `#F8F9FA` |
| Borders / dividers  | `border`         | `#DEE2E6` |
| Light highlight     | `highlight_bg`   | `#E3EDF7` |
| Data bars           | `data_bar`       | `#6BA3D6` |

**Forbidden**: ❌ Green, red, orange, purple, yellow, pink, or any non-blue chromatic color · ❌ Rainbow / multi-hue gradients · ❌ High-saturation colors

### 7.4 Finance Style — Color Quick Reference

Extends Pure with semantic gain/loss colors:

| Purpose                         | Key            | Hex       |
| ------------------------------- | -------------- | --------- |
| Header fill                     | `header_bg`    | `#0D1B2A` |
| Body text                       | `text_primary` | `#1A1A2E` |
| Primary background              | `bg_main`      | `#FAFBFD` |
| Alternating rows                | `bg_alt`       | `#F0F2F6` |
| Key metric highlight            | `highlight_bg` | `#FFF3CD` |
| Borders                         | `border`       | `#D6DAE0` |
| Up / positive (international)   | `positive`     | `#1B7A3D` |
| Down / negative (international) | `negative`     | `#B71C1C` |
| Neutral / warning               | `neutral`      | `#E6A817` |
| Up / gain (China Mainland)      | `up_cn`        | `#B71C1C` |
| Down / loss (China Mainland)    | `down_cn`      | `#1B7A3D` |

**Regional Up/Down Convention (Critical)**
| Region | Up / Gain | Down / Loss |
|--------|-----------|-------------|
| **China (Mainland)** | 🔴 Red `P['up_cn']` | 🟢 Green `P['down_cn']` |
| **International** | 🟢 Green `P['positive']` | 🔴 Red `P['negative']` |

```python
P = PALETTE['finance']

# Select semantic colors by region:
# International (default)
gain_font = Font(color=P['positive'], bold=True)    # green = gain
loss_font = Font(color=P['negative'], bold=True)     # red = loss
# China Mainland — use dedicated keys, no ambiguity
gain_font_cn = Font(color=P['up_cn'], bold=True)     # red = gain (Chinese convention)
loss_font_cn = Font(color=P['down_cn'], bold=True)   # green = loss (Chinese convention)
```

**Number Formatting**
| Data Type | Format | Notes |
|-----------|--------|-------|
| Years | Text `"2024"` | Never numeric |
| Currency | `$#,##0` | Units in header: `Revenue ($mm)` |
| Zero values | `$#,##0;($#,##0);-` | Dash for zero |
| Percentages | `0.00%` | Two decimal |
| Negatives | `(123)` parentheses | Never `-123` |
| Multiples | `0.0x` | EV/EBITDA, P/E |

### 7.5 Conditional Formatting

Proactively apply to 2–4 key columns per sheet. Keep color semantics consistent across workbook.

```python
from openpyxl.formatting.rule import DataBarRule, ColorScaleRule, IconSetRule, CellIsRule

P = PALETTE['finance']  # or PALETTE['pure']

# Data Bars
ws.conditional_formatting.add('C2:C100',
    DataBarRule(start_type='min', end_type='max', color=P['data_bar'], showValue=True))

# Three-Color Scale (Finance: red → amber → green, International)
ws.conditional_formatting.add('D2:D100',
    ColorScaleRule(start_type='min', start_color=P['negative'],
                   mid_type='percentile', mid_value=50, mid_color=P['neutral'],
                   end_type='max', end_color=P['positive']))

# Icon Sets
ws.conditional_formatting.add('E2:E100',
    IconSetRule('3Arrows', type='percent', values=[0, 33, 67], showValue=True))
```

| Data Type      | Recommended Rule |
| -------------- | ---------------- |
| Numeric values | Data Bars        |
| Distribution   | Color Scales     |
| KPIs / Status  | Icon Sets        |
| Thresholds     | `CellIsRule`     |

Best practice: Data Bars + Icon Sets combo. Exclude header rows from ranges.

---

## 8. General Document Processing Strategy

### Existing Files → Incremental Modification

Load original; replace, fill, or insert directly. **Fully preserve** structure, styles, and formatting.

> ⚠️ **CRITICAL**: When loading existing files, **never** use `data_only=True` if you intend to save afterward — this permanently replaces all formulas with their cached values. Always use `load_workbook('file.xlsx')` without `data_only`.
> 
> ```python
> # DANGER — destroys all formulas on save
> wb = load_workbook('file.xlsx', data_only=True)
> wb.save('file.xlsx')
> 
> # SAFE
> wb = load_workbook('file.xlsx')
> ```

### New Document

Only when creating from scratch or purely referencing template styles.

### Content Cleanup

Remove all instructional text, placeholders, `${variable}` patterns — keep only formal content.

## 9. AIGC Marker

**Rule**: After every `.xlsx` file is saved, read the aigc-marker-win skill and follow its instructions to embed the AIGC identifier before VALIDATE.
SAVE → view [aigc-marker-win path]/SKILL.md → APPLY → DELIVER

**Constraints**

- ❌ Never skip — applies to all generated or modified files
- ❌ Never assume the aigc-marker-win interface without reading its SKILL.md
- ✅ On failure: warn the user but do not block delivery

**Progress reporting**: `🏷️ AIGC marker — written ✅ / failed ⚠️`
