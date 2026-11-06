# Chart Creation Reference for openpyxl

## Required Imports

```python
from openpyxl.chart import BarChart, LineChart, PieChart, AreaChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.chart.series import SeriesLabel     # ← needed for from_rows manual labelling
from openpyxl.chart.shapes import GraphicalProperties
from openpyxl.drawing.line import LineProperties
from openpyxl.drawing.effect import EffectList
from openpyxl.utils import get_column_letter
```

---

## Hard Rules

- **MUST** create real chart objects via `ws.add_chart(...)` — never create manual "chart data" sheets.
- **MUST** set: title, axis labels (except PieChart), data range, category range, explicit anchor cell.
- **MUST** set `chart.width` (cm) and `chart.height` (cm) on every chart — row/column sizing varies across environments, physical dimensions are the only reliable way to prevent overlap.
- **MUST** use the layout system below for multiple charts on one sheet.

---

## Sizing & Layout

### Explicit Sizing (CRITICAL)

```python
chart.width  = 18   # cm
chart.height = 10   # cm
```

### Multi-Chart Vertical Stack (≤ 4 charts, DEFAULT)

```python
CHART_HEIGHT_ROWS = 20  # rows per slot — over-estimated to guarantee no overlap

start_col = get_column_letter(ws.max_column + 2)  # clear of data
start_row = 2

for i, chart in enumerate(charts):
    anchor_row = start_row + i * CHART_HEIGHT_ROWS
    ws.add_chart(chart, f"{start_col}{anchor_row}")
# 3 charts → "E2", "E22", "E42"
```

### Grid Layout (5+ charts)

```python
CHART_WIDTH_COLS = 10
CHART_GAP_COLS   = 2

def get_anchor_grid(idx, start_col_num=5, start_row=2, cols=2):
    row = start_row + (idx // cols) * CHART_HEIGHT_ROWS
    col = start_col_num + (idx % cols) * (CHART_WIDTH_COLS + CHART_GAP_COLS)
    return f"{get_column_letter(col)}{row}"
```

---

## Rendering Quality Helpers

Apply to **every** chart:

```python
def apply_defaults(chart, title, width=18, height=10):
    chart.title = title
    chart.style = 10
    chart.width = width
    chart.height = height
    if chart.legend:
        chart.legend.position = 'b'  # bottom — avoid overlapping plot area

def style_axes(chart, y_title="", x_title=""):
    chart.y_axis.title = y_title
    chart.x_axis.title = x_title
    chart.y_axis.tickLblPos = 'low'
    chart.x_axis.tickLblPos = 'low'
```

---

## Chart Type Selection

| Scenario | Type | Key Config |
|---|---|---|
| Category comparison | `BarChart()` | `type="col"` or `"bar"` |
| Trend / time series | `LineChart()` | — |
| Proportion (≤ 6 slices) | `PieChart()` | No axes; `dataLabels.showPercent=True` |
| Cumulative composition | `AreaChart()` | `grouping="standard"` |
| Gantt timeline | `BarChart()` | `type="bar"`, `grouping="stacked"`, `overlap=100` |

---

## Data Orientation: Columns vs Rows

> ⚠️ **This is a common source of bugs.** openpyxl's `add_data()` defaults to reading data in **columns** (each column = one series). When your data is organized in **rows** (each row = one series), you must use `from_rows=True` and handle series labels manually.

### When to use which

| Data Layout | `from_rows` | Example |
|---|---|---|
| **Column-oriented** (default): each column is a series, rows are data points | `False` (default) | Col A = categories, Col B = Series1, Col C = Series2 |
| **Row-oriented**: each row is a series, columns are data points | `True` | Row 1 = categories/years, Row 2 = Company A values, Row 3 = Company B values |

### Column-oriented (default — no `from_rows`)

```
     A          B         C         D
1  Category   Sales     Profit    Growth
2  Q1         100       20        5%
3  Q2         120       25        8%
4  Q3         110       22        6%
```

```python
# Each column (B, C, D) becomes a series; column A is categories
chart.add_data(Reference(ws, min_col=2, min_row=1, max_col=4, max_row=4), titles_from_data=True)
chart.set_categories(Reference(ws, min_col=1, min_row=2, max_row=4))
```

### Row-oriented (requires `from_rows=True` + `SeriesLabel`)

```
     A          B       C       D       E
1  Company     2021    2022    2023    2024
2  Apple       365     394     383     391
3  Microsoft   168     198     211     245
4  NVIDIA      27      27      61      130
```

Here each row (2, 3, 4) is a series and columns B–E are data points. **Two approaches:**

#### Approach A: Loop with `from_rows=True` + `SeriesLabel` (RECOMMENDED)

```python
from openpyxl.chart.series import SeriesLabel

chart = LineChart()
apply_defaults(chart, "Revenue Trend by Company")
style_axes(chart, "Revenue ($B)", "Year")

# Categories = year headers (row 1, cols B–E)
cats = Reference(ws, min_col=2, max_col=5, min_row=1)

for r in range(2, 5):  # rows 2–4 = one series each
    vals = Reference(ws, min_col=2, max_col=5, min_row=r, max_row=r)
    chart.add_data(vals, from_rows=True)
    # ⚠️ Series.title is NOT a plain string — must use SeriesLabel
    chart.series[-1].tx = SeriesLabel(v=ws.cell(r, 1).value)

chart.set_categories(cats)
ws.add_chart(chart, "A8")
```

> ⚠️ **`series.title = "string"` will raise `TypeError`**. openpyxl requires a `SeriesLabel` object. Always use:
> ```python
> from openpyxl.chart.series import SeriesLabel
> chart.series[-1].tx = SeriesLabel(v="Label Text")
> ```

#### Approach B: Bulk `add_data` with `from_rows=True`

This works when your first column contains the series names and you include it in the reference range:

```python
# Include column A (labels) in the data range
data = Reference(ws, min_col=1, max_col=5, min_row=2, max_row=4)
chart.add_data(data, from_rows=True, titles_from_data=True)

# Categories = year headers (row 1, cols B–E)
cats = Reference(ws, min_col=2, max_col=5, min_row=1)
chart.set_categories(cats)
```

> **Approach A vs B**: Use Approach A when you need fine-grained control over each series (custom colors, styles). Use Approach B for quick multi-series charts where label auto-detection is sufficient.

---

## Examples

### Bar / Column

```python
chart = BarChart(); chart.type = "col"
apply_defaults(chart, "Sales by Category")
style_axes(chart, "Revenue ($)", "Category")

chart.add_data(Reference(ws, min_col=2, min_row=1, max_row=ws.max_row), titles_from_data=True)
chart.set_categories(Reference(ws, min_col=1, min_row=2, max_row=ws.max_row))
ws.add_chart(chart, "E2")
```

### Line

```python
chart = LineChart()
apply_defaults(chart, "Monthly Trend")
style_axes(chart, "Value", "Month")

chart.add_data(Reference(ws, min_col=2, min_row=1, max_row=ws.max_row, max_col=ws.max_column), titles_from_data=True)
chart.set_categories(Reference(ws, min_col=1, min_row=2, max_row=ws.max_row))
ws.add_chart(chart, "E2")
```

### Line (Row-Oriented — Multi-Entity Trend)

```python
from openpyxl.chart.series import SeriesLabel

chart = LineChart()
apply_defaults(chart, "Revenue Trend by Company ($B)")
style_axes(chart, "Revenue ($B)", "Year")

# Data layout: Row 1 = years, Rows 2+ = one company per row, Col A = company name
cats = Reference(ws, min_col=2, max_col=ws.max_column, min_row=1)
for r in range(2, ws.max_row + 1):
    vals = Reference(ws, min_col=2, max_col=ws.max_column, min_row=r, max_row=r)
    chart.add_data(vals, from_rows=True)
    chart.series[-1].tx = SeriesLabel(v=ws.cell(r, 1).value)

chart.set_categories(cats)
ws.add_chart(chart, "E2")
```

### Pie

```python
pie = PieChart()
apply_defaults(pie, "Market Share")

pie.add_data(Reference(ws, min_col=2, min_row=1, max_row=ws.max_row), titles_from_data=True)
pie.set_categories(Reference(ws, min_col=1, min_row=2, max_row=ws.max_row))
pie.dataLabels = DataLabelList()
pie.dataLabels.showPercent = True
pie.dataLabels.showCatName = True
ws.add_chart(pie, "E2")
```

### Gantt (Stacked Bar)

Data: Col A = task, Col B = start offset, Col C = duration.

```python
chart = BarChart(); chart.type = "bar"
chart.grouping = "stacked"; chart.overlap = 100
apply_defaults(chart, "Project Gantt Chart")
style_axes(chart, "Tasks", "Timeline (days)")

chart.add_data(Reference(ws, min_col=2, min_row=1, max_row=ws.max_row), titles_from_data=True)
chart.add_data(Reference(ws, min_col=3, min_row=1, max_row=ws.max_row), titles_from_data=True)
chart.set_categories(Reference(ws, min_col=1, min_row=2, max_row=ws.max_row))

# Hide offset series
s0 = chart.series[0]
s0.graphicalProperties = GraphicalProperties()
s0.graphicalProperties.noFill = True
s0.graphicalProperties.line = LineProperties(); s0.graphicalProperties.line.noFill = True
s0.graphicalProperties.effectLst = EffectList()
chart.legend = None
ws.add_chart(chart, "E2")
```

---

## Checklist

- [ ] `chart.width` / `chart.height` explicitly set (cm)
- [ ] Title and axis labels set (axes N/A for Pie)
- [ ] `add_data(ref, titles_from_data=True)` includes header row
- [ ] `set_categories(ref)` excludes header row
- [ ] `ws.add_chart(chart, anchor)` called with explicit cell
- [ ] Multiple charts use `CHART_HEIGHT_ROWS = 20` spacing
- [ ] Start column ≥ `ws.max_column + 2`
- [ ] Legend position = `'b'`
- [ ] **Row-oriented data?** → used `from_rows=True` + `SeriesLabel` for series names (NOT `series.title = "string"`)
- [ ] **`SeriesLabel` imported** from `openpyxl.chart.series` if using `from_rows=True` with manual labels