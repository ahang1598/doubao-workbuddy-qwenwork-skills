---
name: PDF 处理工具包
name_en: pdf-processing-toolkit
description: PDF文档处理工具包，支持文本提取（提取文字内容供阅读、分析与后续处理）、表格提取、创建PDF、合并/拆分文档、表单处理。适用于程序化处理、生成、分析PDF文档。
license: Proprietary. LICENSE.txt has complete terms
official: true
category: general
metadata:
  version: "1.1"
  changelog:
    - version: "1.1"
      date: "2026-07-14"
      changes:
        - "扩展 description，新增典型用户话术和 negative 边界声明，明确精美PDF生成应路由到 pdf-generation-editing-tool"
        - "统一表单填写功能入口，承接 pdf-generation-editing-tool 移除的 FILL 路由"
    - version: "1.0"
      date: "2025-01-01"
      changes:
        - "初始版本：文本提取/表格提取/创建PDF/合并拆分/表单处理"
---

# PDF Processing Guide

## 核心约束（必须最先阅读）

**⛔ 以下约束强制执行，严禁绕过 ⛔**

- **提取 PDF 文本的唯一入口**：必须调用 `extract_text.py`，禁止自行编写提取脚本
- **严禁直接使用 pdfplumber / pypdf / pdftotext 等库或命令行工具读取正文**：这些方式没有内置的内容质量检测和 OCR 路由，会导致乱码或空白内容静默通过
- **必须检查 stdout JSON 中的 `status` 和 `next_action`**：不得假定提取成功，不得跳过路由判断
- **`next_action == "fadada-scanned-ocr"` 时立即停止当前路径**：不读取 `output_file`，直接将原始 PDF 路径交给法大大专用OCR skill
- **调用 OCR skill 的方式**：在 available_skills 中按 **name = "法大大专用OCR"** 查找并调用，不要用英文文件夹名 `fadada-scanned-ocr` 去搜索
- **检测到需要 OCR 时，必须自动调用法大大专用OCR skill，严禁向用户询问是否需要OCR、是否继续、或提示"请告知我"等**：用户已发起文件处理任务，OCR 路由是自动兜底，不需要用户再次确认
- **`status == "success"` 不等于内容有效**：还需检查 `extracted_chars / total_pages >= 50`，否则同样切换 OCR

## Overview

This guide covers essential PDF processing operations using Python libraries and command-line tools. For advanced features, JavaScript libraries, and detailed examples, see reference.md. If you need to fill out a PDF form, read forms.md and follow its instructions.

## Text Extraction (Reading PDF Content)

Use this when you need to read and understand the content of a PDF file.

> ⛔ **Always use `extract_text.py` — never bypass it.**
> When extracting text from one or multiple PDFs, you must call this script for each file.
> Do **not** write your own extraction script using pdfplumber, pypdf, or any other library directly.
> `extract_text.py` runs built-in content-quality checks that detect cid garbage, private-use glyphs, and empty pages, and sets `next_action` to trigger OCR fallback when needed.
> Bypassing it causes corrupted text to pass through silently with no OCR fallback.

### Command

```bash
python {skill_root}/scripts/extract_text.py <input.pdf> <output.txt> [--pages "1-3,5"] [--layout]
```

### Output (stdout JSON)

```json
{
  "status": "success" | "empty" | "partial",
  "next_action": null | "fadada-scanned-ocr",
  "total_pages": 10,
  "extracted_chars": 5832,
  "empty_pages": [3, 7],
  "corrupted_pages": [1, 2, 4],
  "output_file": "output.txt"
}
```

> ⚠️ `extracted_chars` is a raw character count and **does NOT reflect content quality**.
> A large number can still mean the page is full of garbage (e.g. encoding noise,
> missing font maps, private-use glyphs). Always check `status` and `next_action` first.

### ⚠️ You MUST validate the result before proceeding

| status | next_action | meaning | action |
|--------|-------------|---------|--------|
| `success` | `null` | All pages have readable content | Check content threshold (see below) before proceeding |
| `empty` | `"fadada-scanned-ocr"` | All pages are blank (scanned PDF) | **立即自动调用法大大专用OCR skill，不得询问用户。** |
| `partial` | `"fadada-scanned-ocr"` | Some pages blank or unreadable (encoding noise) | **立即自动调用法大大专用OCR skill，不得询问用户。** |

> **When `next_action` is `"fadada-scanned-ocr"`: do NOT read or use `output_file`.**
> 在 available_skills 中找到 **name = "法大大专用OCR"** 的 skill，将原始 PDF 路径传入并立即执行，无需向用户确认、无需提示"是否需要OCR"。

### Minimum content threshold

Even when `status == "success"`, check whether the extracted content is substantive:

```
extracted_chars / total_pages < 50  →  treat as suspect, 自动调用法大大专用OCR skill（不询问用户）
extracted_chars / total_pages >= 50 →  proceed normally
```

A low per-page character count typically means only headers, page numbers, or noise were extracted — not actual readable content.
>
> **How corruption is detected**: the script scores each page by (1) stripping known
> noise patterns (missing-font tokens, private-use glyphs, replacement characters,
> control chars) then (2) checking that the surviving characters are actual readable
> letters/CJK/digits. Pages scoring below 0.5 are listed in `corrupted_pages`.
> This catches any form of encoding garbage, not just one specific pattern.

## Quick Start

> ⚠️ The code samples below are reference snippets for library usage (merging, splitting, metadata, etc.).
> **Do not use them for reading PDF text content for analysis** — use `extract_text.py` instead (see Text Extraction section above).

```python
from pypdf import PdfReader, PdfWriter

# Read a PDF
reader = PdfReader("document.pdf")
print(f"Pages: {len(reader.pages)}")

# Extract text (for analysis, use extract_text.py instead)
text = ""
for page in reader.pages:
    text += page.extract_text()
```

## Python Libraries

### pypdf - Basic Operations

#### Merge PDFs
```python
from pypdf import PdfWriter, PdfReader

writer = PdfWriter()
for pdf_file in ["doc1.pdf", "doc2.pdf", "doc3.pdf"]:
    reader = PdfReader(pdf_file)
    for page in reader.pages:
        writer.add_page(page)

with open("merged.pdf", "wb") as output:
    writer.write(output)
```

#### Split PDF
```python
reader = PdfReader("input.pdf")
for i, page in enumerate(reader.pages):
    writer = PdfWriter()
    writer.add_page(page)
    with open(f"page_{i+1}.pdf", "wb") as output:
        writer.write(output)
```

#### Extract Metadata
```python
reader = PdfReader("document.pdf")
meta = reader.metadata
print(f"Title: {meta.title}")
print(f"Author: {meta.author}")
print(f"Subject: {meta.subject}")
print(f"Creator: {meta.creator}")
```

#### Rotate Pages
```python
reader = PdfReader("input.pdf")
writer = PdfWriter()

page = reader.pages[0]
page.rotate(90)  # Rotate 90 degrees clockwise
writer.add_page(page)

with open("rotated.pdf", "wb") as output:
    writer.write(output)
```

### pdfplumber - Table Extraction

> ⛔ **Do not use pdfplumber to extract text content from PDFs.** Use `extract_text.py` (see Text Extraction section). No code example is provided here to avoid confusion.

#### Extract Tables
```python
with pdfplumber.open("document.pdf") as pdf:
    for i, page in enumerate(pdf.pages):
        tables = page.extract_tables()
        for j, table in enumerate(tables):
            print(f"Table {j+1} on page {i+1}:")
            for row in table:
                print(row)
```

#### Advanced Table Extraction
```python
import pandas as pd

with pdfplumber.open("document.pdf") as pdf:
    all_tables = []
    for page in pdf.pages:
        tables = page.extract_tables()
        for table in tables:
            if table:  # Check if table is not empty
                df = pd.DataFrame(table[1:], columns=table[0])
                all_tables.append(df)

# Combine all tables
if all_tables:
    combined_df = pd.concat(all_tables, ignore_index=True)
    combined_df.to_excel("extracted_tables.xlsx", index=False)
```

### reportlab - Create PDFs

> ⛔ **创建含中文的 PDF 时，必须调用 `scripts/create_pdf.py`，禁止自行用 reportlab 实现。**
> 脚本已内置中文字体嵌入（STSong-Light CID 字体），自行实现会导致中文乱码（黑色方块）。

#### Create PDF with Chinese text
```bash
# From text content
python scripts/create_pdf.py output.pdf "长恨歌内容..." "长恨歌"

# From file
python scripts/create_pdf.py output.pdf @content.txt "长恨歌"
```

#### Subscripts and Superscripts

**IMPORTANT**: Never use Unicode subscript/superscript characters (₀₁₂₃₄₅₆₇₈₉, ⁰¹²³⁴⁵⁶⁷⁸⁹) in ReportLab PDFs. The built-in fonts do not include these glyphs, causing them to render as solid black boxes.

Instead, use ReportLab's XML markup tags in Paragraph objects:
```python
from reportlab.platypus import Paragraph
from reportlab.lib.styles import getSampleStyleSheet

styles = getSampleStyleSheet()

# Subscripts: use <sub> tag
chemical = Paragraph("H<sub>2</sub>O", styles['Normal'])

# Superscripts: use <super> tag
squared = Paragraph("x<super>2</super> + y<super>2</super>", styles['Normal'])
```

For canvas-drawn text (not Paragraph objects), manually adjust font size and position rather than using Unicode subscripts/superscripts.

## Command-Line Tools

### pdftotext (poppler-utils)
```bash
# Extract text
pdftotext input.pdf output.txt

# Extract text preserving layout
pdftotext -layout input.pdf output.txt

# Extract specific pages
pdftotext -f 1 -l 5 input.pdf output.txt  # Pages 1-5
```

### qpdf
```bash
# Merge PDFs
qpdf --empty --pages file1.pdf file2.pdf -- merged.pdf

# Split pages
qpdf input.pdf --pages . 1-5 -- pages1-5.pdf
qpdf input.pdf --pages . 6-10 -- pages6-10.pdf

# Rotate pages
qpdf input.pdf output.pdf --rotate=+90:1  # Rotate page 1 by 90 degrees

# Remove password
qpdf --password=mypassword --decrypt encrypted.pdf decrypted.pdf
```

### pdftk (if available)
```bash
# Merge
pdftk file1.pdf file2.pdf cat output merged.pdf

# Split
pdftk input.pdf burst

# Rotate
pdftk input.pdf rotate 1east output rotated.pdf
```

## Common Tasks

### Add Watermark
```python
from pypdf import PdfReader, PdfWriter

# Create watermark (or load existing)
watermark = PdfReader("watermark.pdf").pages[0]

# Apply to all pages
reader = PdfReader("document.pdf")
writer = PdfWriter()

for page in reader.pages:
    page.merge_page(watermark)
    writer.add_page(page)

with open("watermarked.pdf", "wb") as output:
    writer.write(output)
```

### Extract Images
```bash
# Using pdfimages (poppler-utils)
pdfimages -j input.pdf output_prefix

# This extracts all images as output_prefix-000.jpg, output_prefix-001.jpg, etc.
```

### Password Protection
```python
from pypdf import PdfReader, PdfWriter

reader = PdfReader("input.pdf")
writer = PdfWriter()

for page in reader.pages:
    writer.add_page(page)

# Add password
writer.encrypt("userpassword", "ownerpassword")

with open("encrypted.pdf", "wb") as output:
    writer.write(output)
```

## Quick Reference

| Task | Best Tool | Command/Code |
|------|-----------|--------------|
| Merge PDFs | pypdf | `writer.add_page(page)` |
| Split PDFs | pypdf | One page per file |
| Extract text | pdfplumber | `page.extract_text()` |
| Extract tables | pdfplumber | `page.extract_tables()` |
| Create PDFs | reportlab | Canvas or Platypus |
| Command line merge | qpdf | `qpdf --empty --pages ...` |
| OCR scanned PDFs | 法大大专用OCR skill | Use 法大大专用OCR skill |
| Fill PDF forms | Use scripts/fill_pdf_form_with_annotations.py (see forms.md) | **必须调用脚本，禁止自行用 pypdf/pdf-lib 实现**。脚本已内置中文字体嵌入，自行实现会导致中文乱码（黑色方块）。 |

## Next Steps

- For advanced pypdfium2 usage, see reference.md
- For JavaScript libraries (pdf-lib), see reference.md
- If you need to fill out a PDF form, follow the instructions in forms.md
- For troubleshooting guides, see reference.md
