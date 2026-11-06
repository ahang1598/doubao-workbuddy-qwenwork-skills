---
name: xiaoyi-docx-win
description: |
  Use this skill whenever you need to create, modify, or generate Word documents (.docx). This includes writing reports, creating formatted documents, generating tables, adding Table of Contents, handling Chinese/CJK fonts, or any document output task. Even if the user just mentions "Word document", "docx", "report", or "document generation", use this skill.
post_process: aigc-marker-win
---

# Python-docx Document Creation Guide

Python dependencies are declared in the Skill root `requirements.txt` and installed in the background by 小艺 Work. Do not run `pip install` during a task; if dependencies are not ready, wait for installation or retry from the skill page.

## Output convention

Run generated Python from the current task workspace and derive final paths with `Path.cwd()`. Do not `cd` into this Skill. Save only the final DOCX in the workspace, then call `send_file_to_user` with its absolute path after AIGC marking.

## Workflow

1. Use `docx_utils.py` for specialized tasks: Chinese font support, Table of Contents (TOC) fields, Page Number fields,
   and Document Statistics.
2. Use **native python-docx API** for text insertion, paragraph formatting (indentation, spacing), and basic styling.
3. **Critical Rule:** Configure document styles via `setup_chinese_document_styles()` *before* adding any content.
4. **Important:** Do not read the source code of `docx_utils.py`. Only refer to this document for using the utility
   functions.

---

## 1. Quick Start

```python
import sys

sys.path.append('./scripts')

from docx import Document
from docx.shared import Inches, Pt, Cm
from docx_utils import (
    setup_chinese_document_styles,
    add_table_of_contents,
    add_page_number_footer,
    count_document_words
)

doc = Document()
# Initialize styles with Chinese support (SimSun body, SimHei headings)
setup_chinese_document_styles(doc)

doc.add_paragraph('Document Title', style='Title')

# Add TOC (Requires manual update in Word via F9)
doc.add_paragraph('Table of Contents', style='Heading 1')
add_table_of_contents(doc)

doc.add_paragraph('Chapter 1', style='Heading 1')
from pathlib import Path
output_path = (Path.cwd() / 'output.docx').resolve()
doc.save(output_path)
```

---

## 2. Text & Paragraphs

### Handling Multi-line Text

When using the native `doc.add_paragraph(text)` method, a `\n` character in the string creates a **Soft Return** (Line
Break). Soft returns do not trigger paragraph-level formatting like indentation or space-after.

**Correct Approach:** Split the text by line breaks and add each as a separate paragraph to ensure styles (like
first-line indent) apply correctly to every line.

```python
raw_text = """First paragraph of content.
Second paragraph of content.
Third paragraph of content."""

# Use native Python logic to add paragraphs
for line in raw_text.split('\n'):
    line = line.strip()
    if line:
        p = doc.add_paragraph(line, style='Normal')
        # Apply native paragraph formatting
        p.paragraph_format.first_line_indent = Pt(24)  # 2-character indent for 12pt font
        p.paragraph_format.space_after = Pt(6)
```

### Inline Formatting (Runs)

To format specific words within a paragraph, use the native `add_run()` method. Do not modify `paragraph.style` as it
changes the global style definition.

```python
p = doc.add_paragraph('This is ')
p.add_run('bold and red').font.bold = True
# Color requires RGBColor
from docx.shared import RGBColor

p.runs[1].font.color.rgb = RGBColor(255, 0, 0)
p.add_run(' text.')
```

---

## 3. Horizontal Lines & Text Alignment

### Adding Full-Page Horizontal Lines

Use the `add_horizontal_line` function from `docx_utils`:

```python
from docx_utils import add_horizontal_line

# Create an empty paragraph as the line container
line_para = doc.add_paragraph()
add_horizontal_line(line_para)

# Custom style: red double line, thicker
line_para2 = doc.add_paragraph()
add_horizontal_line(line_para2, line_style='double', line_size=12, color='FF0000')
```

**Supported Parameters:**

| Parameter    | Type | Default    | Description                                                            |
| ------------ | ---- | ---------- | ---------------------------------------------------------------------- |
| `line_style` | str  | `'single'` | Line style: `'single'`, `'double'`, `'dotted'`, `'dashed'`, `'triple'` |
| `line_size`  | int  | `6`        | Thickness in 1/8 points, 6 = 0.75pt, 12 = 1.5pt                        |
| `color`      | str  | `'auto'`   | Color: `'auto'` (auto/black) or hex like `'FF0000'` (red)              |
| `space`      | int  | `1`        | Space between line and text                                            |

### Left-Right Text Alignment with Fill

**Core Concept:** Use Tab Stops + dynamically calculated page width. Insert a `\t` tab character in the middle, use
`underline=True` to achieve underline effect.

```python
from docx.enum.text import WD_TAB_ALIGNMENT
from docx.shared import Pt

# Dynamically calculate available page width
section = doc.sections[0]
content_width = section.page_width - section.left_margin - section.right_margin

# Create paragraph
p = doc.add_paragraph()

# Add right-aligned tab stop at the right edge of page
p.paragraph_format.tab_stops.add_tab_stop(content_width, WD_TAB_ALIGNMENT.RIGHT)

# Left text
p.add_run('Left side text content')

# Middle tab (with underline)
run_tab = p.add_run('\t')
run_tab.underline = True  # Set to False for plain space

# Right text
p.add_run('Right side text content')
```

**Key Points:**

- `content_width` is dynamically calculated to adapt to margin changes
- `WD_TAB_ALIGNMENT.RIGHT` makes right text align to right margin
- `\t` tab's `underline` property controls whether to show underline or space

### Borderless Table Layout

**Background**: Tab Stops are the traditional way to align content in Word, but they can be unreliable for multi-line
content or mixed text-image layouts. Borderless tables (setting column widths then removing borders) provide a more
stable layout solution.

**Use Cases**:

- Multi-line label/value alignment (e.g., form labels on the left)
- Side-by-side images and text (vertical centering)
- Flexible column ratios (e.g., 1:2:1)
- Underlined fill-in forms (keep only bottom border)

**Implementation**: Create table → Set column widths → Add content → Call `remove_table_borders()` to hide all borders.

> **See** [borderless_tables.md](./references/borderless_tables.md) for code examples and details.

---

## 4. Customizing Styles (Indentation & Spacing)

Always apply a style (e.g., `'Normal'`) first, then override specific attributes using `paragraph_format`.

| Feature                | Native Property                        | Example Value               |
| ---------------------- | -------------------------------------- | --------------------------- |
| **First Line Indent**  | `p.paragraph_format.first_line_indent` | `Pt(24)` (2 chars @ 12pt)   |
| **Line Spacing**       | `p.paragraph_format.line_spacing`      | `1.5` (1.5 lines)           |
| **Space Before/After** | `p.paragraph_format.space_before`      | `Pt(12)`                    |
| **Alignment**          | `p.alignment`                          | `WD_ALIGN_PARAGRAPH.CENTER` |

### First Line Indent Best Practices

Different paragraph types have different first-line indent requirements:

| Paragraph Type                    | Needs First-Line Indent | Notes                                                          |
| --------------------------------- | ----------------------- | -------------------------------------------------------------- |
| Body (`Normal`)                   | **Yes**                 | Chinese documents typically indent 2 chars (~24pt @ 12pt font) |
| Headings (`Heading 1~6`, `Title`) | **No**                  | Headings are usually centered or left-aligned, keep default    |
| Unordered Lists (`List Bullet`)   | **No**                  | List items have their own bullet indentation                   |
| Ordered Lists (`List Number`)     | **No**                  | List items have their own number indentation                   |

```python
# Body paragraph - needs first-line indent (2 chars ≈ 24pt @ 12pt font)
p = doc.add_paragraph('This is body content...', style='Normal')
p.paragraph_format.first_line_indent = Pt(24)

# Headings - no first-line indent needed (keep default)
doc.add_paragraph('Chapter 1', style='Heading 1')

# List items - no first-line indent needed
doc.add_paragraph('List item one', style='List Bullet')
doc.add_paragraph('List item two', style='List Number')
```

---

## 5. Table of Contents (TOC)

Because `python-docx` lacks a rendering engine, it cannot calculate page numbers for a TOC. The utility function
`add_table_of_contents(doc)` inserts the necessary **Field Codes**.

1. Call `add_table_of_contents(doc)` where the TOC should appear.
2. **User Action Required:** After opening the generated `.docx` in Microsoft Word, you must press **F9** or right-click
   the TOC area and select **Update Field** to populate the entries.

---

## 6. Tables

Use the utility function to create a table with professional Chinese-compatible styles, then use native properties for
data.

```python
from docx_utils import create_styled_table, format_table_cell

# Create table with header logic
table = create_styled_table(doc, rows=3, cols=2, col_widths=[2.5, 4.0])

# Fill cells
table.rows[1].cells[0].text = "Data Name"
# Use helper for centered/bold cell text
format_table_cell(table.rows[1].cells[1], "Data Value", alignment='center')
```

**Multi-line in Cells:**
To add multiple lines inside a single cell with proper formatting, add paragraphs to the cell's element:

```python
cell = table.rows[2].cells[1]
cell.text = ""  # Clear default paragraph
cell.add_paragraph("Point A", style='List Bullet')
cell.add_paragraph("Point B", style='List Bullet')
```

---

## 7. Page Layout

### Page Setup (A4 + Standard Margins)

`setup_chinese_document_styles()` automatically configures:

- **A4 paper size** (21cm × 29.7cm)
- **Standard Chinese margins**: top/bottom 2.54cm, left/right 3.18cm

If you need custom margins after calling `setup_chinese_document_styles()`:

```python
from docx.shared import Cm

for section in doc.sections:
    section.top_margin = Cm(2.0)  # Custom top margin
    section.bottom_margin = Cm(2.0)  # Custom bottom margin
    section.left_margin = Cm(2.5)  # Custom left margin
    section.right_margin = Cm(2.5)  # Custom right margin
```

### Page Numbers

Use the utility function to insert auto-incrementing page numbers in the footer:

```python
add_page_number_footer(doc.sections[0], alignment='center')
```

---

## 8. Document Statistics (Word Count)

Use the utility function `count_document_words()` to calculate the word count. The counting logic mimics Microsoft
Word's standard mixed language behavior:

- Each Chinese character counts as 1 word.
- Consecutive English letters/numbers count as 1 word.
- Punctuation and whitespaces are ignored.
- Automatically extracts text from paragraphs, tables, headers, and footers.

```python
from docx_utils import count_document_words

# Pass the Document object during creation
count = count_document_words(doc)
print(f"Current word count: {count}")

# Or pass a file path for an existing document
count_from_file = count_document_words('output.docx')
```

### Word Limit Compliance Strategy

When the user specifies a clear word count target (e.g., 3000+ words), use a **multi-step incremental approach**
leveraging your ability to make multiple tool calls:

**Workflow:**

1. **Plan First**: Outline the document structure (sections/chapters) and estimate word count for each part.
2. **Generate by Parts**: In each tool call, generate **only one section** (or a few paragraphs) of content.
3. **Check Count**: Immediately call `count_document_words(doc)` to get the current total.
4. **Decide Next Step**: Based on the remaining word count budget, decide whether to:
   
    - Expand the next section (if behind target)
   
    - Condense the next section (if approaching target too quickly)
   
    - Skip less critical content (if nearly at limit)

This avoids overshooting or undershooting the target at the final stage when it's too late to adjust.

> **Note:** Word count targets are typically approximate. A reasonable margin of error (e.g., ±10%) is generally
> acceptable unless the user explicitly requires strict precision.

```python
from docx_utils import count_document_words

# After adding a section or significant content
current_count = count_document_words(doc)
remaining = target_word_count - current_count

# Use this information to guide your next action
# (e.g., expand, condense, or adjust the next section)
```

---

## 9. Ordered Lists (Numbered Lists)

`docx_utils` patches `doc.add_paragraph()` to support a `restart` parameter for controlling list numbering.

```python
# First item of a new list MUST have restart=True
doc.add_paragraph("First item", style="List Number", restart=True)  # 1. First item
doc.add_paragraph("Second item", style="List Number")  # 2. Second item

# Start a new list (resets numbering to 1)
doc.add_paragraph("New list item", style="List Number", restart=True)  # 1. New list...
```

**Critical Rules:**

1. **DO NOT** include manual number prefixes like `"1. text"` — Word adds its own numbers
2. The **first item** of any new list **MUST** have `restart=True`
3. Use `style='List Number 2'`, `'List Number 3'` for nested levels — the patch auto-detects the correct level

---

## 10. Formulas (OMath)

Word formulas use **Office Math Markup Language (OMML)**. The most common mistake is placing `w:r`/`w:t` directly under `m:oMath`; Word expects `m:r` (math run) with `m:t` (math text), and run properties must include `w:rPr` with font settings so formulas render correctly.

### Correct OOXML Structure

```xml
<m:oMath>
  <m:r>
    <w:rPr>
      <w:rFonts w:ascii="Cambria Math" w:hAnsi="Cambria Math" w:eastAsia="SimSun"/>
    </w:rPr>
    <m:t>...</m:t>
  </m:r>
</m:oMath>
```

### Helper Functions

Import the helpers from `docx_utils`:

```python
from docx_utils import add_formula, create_math_run, create_math_fraction
```

**`add_formula(paragraph, text)`** — add a simple inline formula.

```python
p = doc.add_paragraph()
p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
add_formula(p, 'E = mc²')
```

**`create_math_run(text)`** — create a single math run (`m:r`) with proper `w:rPr` font settings. Use it as a building block for complex formulas.

```python
from docx.oxml import OxmlElement

math_elem = OxmlElement('m:oMath')
math_elem.append(create_math_run('x = '))
math_elem.append(create_math_fraction('-b ± √(b²-4ac)', '2a'))

p = doc.add_paragraph()
p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
p._p.append(math_elem)
```

**`create_math_fraction(numerator, denominator)`** — create an `m:f` fraction element with properly structured `m:num` and `m:den` children.

### Important Notes

- Always use `m:r`/`m:t` inside `m:oMath`, never `w:r`/`w:t`.
- Always include `w:rPr` with `w:rFonts` so Word/WPS can render the formula.
- For complex structures (roots, integrals, superscripts, etc.), build the OMML elements manually and use `create_math_run` for every text run.

---

## 11. Charts

`xiaoyi-docx` 通过 `matplotlib` 生成静态图表图片并嵌入文档。

> **See** [charts.md](./references/charts.md) for complete examples per chart type.

### 导入

```python
from matplotlib_chart_utils import (
    add_column_chart,
    add_bar_chart,
    add_line_chart,
    add_pie_chart,
    add_area_chart,
    add_scatter_chart,
    add_radar_chart,
    add_histogram,
)
```

### Quick Example: Column Chart

```python
add_column_chart(
    doc,
    categories=["Q1", "Q2", "Q3"],
    series=[{"name": "销售额", "values": [100, 200, 150]}],
    title="季度销售额",
)
```

### Quick Example: Histogram

```python
add_histogram(doc, data=[1.2, 2.3, 1.8, 3.0], bins=4, title="分布")
```

---

## 12. Critical Rules Quick Reference

| #   | Rule                | ❌ Wrong                                          | ✅ Correct                                                      |
| --- | ------------------- | ------------------------------------------------ | -------------------------------------------------------------- |
| 1   | **Multi-line Text** | `doc.add_paragraph("Line 1\nLine 2")`            | `for line in text.split('\n'): doc.add_paragraph(line)`        |
| 2   | **Indentation**     | Changing 'Normal' style globally                 | `p.paragraph_format.first_line_indent = Pt(24)`                |
| 3   | **One-off Bold**    | `p.style.font.bold = True`                       | `p.add_run('text').bold = True`                                |
| 4   | **Lists**           | `doc.add_paragraph('text', style='List Number')` | `doc.add_paragraph('text', style='List Number', restart=True)` |
| 5   | **Chinese Font**    | `run.font.name = 'SimSun'`                       | `set_chinese_font(run.font, 'SimSun')`                         |
| 6   | **TOC Generation**  | Expecting TOC to be ready                        | User must press **F9** in Word to update                       |
| 7   | **OMML Formula**    | `m:oMath > w:r > w:t`                            | `m:oMath > m:r > w:rPr + m:t`                                  |

---

## 13. AIGC 标识（必须）

**所有生成的 DOCX 文档必须添加 AIGC 标识。** 在文档生成/编辑完成后，**立即调用 `aigc-marker-win` skill**：

```
使用 aigc-marker-win 为 output.docx 添加 AIGC 标识
```

**规则：**

- 这是合规要求，**不可跳过**
- 在 `doc.save()` 或文件生成命令完成后立即执行

### 使用示例

```bash
/aigc-marker-win output.docx
```

```python
# 保存文档后调用 aigc-marker-win
output_path = (Path.cwd() / 'output.docx').resolve()
doc.save(output_path)
# 然后：使用 aigc-marker-win 为 output.docx 添加 AIGC 标识
```

标记完成后读取 `output_path` 的字符串绝对路径，并调用 `send_file_to_user(abs_file_path_list=["<output_path 的绝对路径>"])`，不得只在回复中展示路径。
