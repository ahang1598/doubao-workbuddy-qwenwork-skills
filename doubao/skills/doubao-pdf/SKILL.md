---
name: doubao-pdf
description: 用于处理所有 PDF 相关任务，包括读取、创建、编辑、转换、内容提取、页面处理、表单填写和扫描件解析。用户提供、提及或要求生成 PDF 时使用。
---

# PDF Processing Guide

## Overview

This guide covers essential PDF processing operations using bundled Python libraries and scripts. For advanced features, JavaScript libraries, and detailed examples, see [reference.md](reference.md). If you need to fill out a PDF form, read [forms.md](forms.md) and follow its instructions.


## Rules
- For editing scenarios (such as document translation or editing), prioritize modifying the original PDF copy.
- For tasks where layout and visuals matter (such as reading, creating, editing or translating reports, invoices, slides, figures, paperwork etc.) or for filling and validating interactive PDF forms: 1.Prefer visual review: render PDF pages to PNGs and inspect them. 2.After each meaningful update, re-render pages and verify alignment, spacing, and legibility.
- Prefer PyMuPDF for existing-PDF operations. Use pypdf only for canonical AcroForm handling, encryption/repair edge cases, or operations PyMuPDF cannot perform reliably; use pdfplumber only as a table/edge-case fallback.
- Use the bundled Python libraries and scripts for all default workflows. Do not invoke a system CLI when PyMuPDF, pypdf, pdfplumber, reportlab, or Pillow can perform the operation.
- When extracting text, check page count, empty pages, repeated-page hashes, replacement characters, and a visual sample. Do not assume a larger character count is more accurate.
- Install the locked Python dependencies with `python -m pip install -r requirements.txt`.
- If the user has no explicit file format requirements, keep the same file extension as the source file


## Quick Start

```python
import pymupdf

with pymupdf.open("document.pdf") as document:
    print(f"Pages: {document.page_count}")
    text = "\n\n".join(
        page.get_text("text", sort=True) for page in document
    )
```

For a reusable command-line path, run `python scripts/extract_pdf_text.py input.pdf output.txt`. Add `--structured` to write page text, blocks, words, and coordinates as JSON.

## Python Libraries

### PyMuPDF - Default for Existing PDFs

Use PyMuPDF (`pymupdf`) first for reading, text extraction, rendering, page manipulation, coordinates, images, annotations, and inspection. It respects visible page boundaries on PDFs that reuse a larger shared content stream and usually returns cleaner Unicode than `pypdf`, `pdfplumber`, or `pdfminer.six` defaults.

Always use `sort=True` for human reading order. For multi-column or card layouts, preserve coordinates with `"blocks"`, `"words"`, or `"dict"` and reconstruct the semantic order instead of flattening blindly.

#### Extract Text and Coordinates

```python
import pymupdf

with pymupdf.open("input.pdf") as document:
    for page in document:
        text = page.get_text("text", sort=True)
        blocks = page.get_text("blocks", sort=True)
        words = page.get_text("words", sort=True)
```

#### Render Pages

```python
import pymupdf

with pymupdf.open("input.pdf") as document:
    matrix = pymupdf.Matrix(2, 2)
    for index, page in enumerate(document, start=1):
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)
        pixmap.save(f"page_{index}.png")
```

Use a 2x matrix as a practical preview default. Increase it when small text or fine visual details require higher resolution.

#### Merge PDFs

```python
import pymupdf

output = pymupdf.open()
for pdf_path in ["doc1.pdf", "doc2.pdf", "doc3.pdf"]:
    with pymupdf.open(pdf_path) as source:
        output.insert_pdf(source)
output.save("merged.pdf", garbage=4, deflate=True)
output.close()
```

#### Split PDF
```python
import pymupdf

with pymupdf.open("input.pdf") as source:
    for index in range(source.page_count):
        output = pymupdf.open()
        output.insert_pdf(source, from_page=index, to_page=index)
        output.save(f"page_{index + 1}.pdf", garbage=4, deflate=True)
        output.close()
```

#### Extract Metadata
```python
import pymupdf

with pymupdf.open("document.pdf") as document:
    metadata = document.metadata
    print(metadata.get("title"))
    print(metadata.get("author"))
```

#### Rotate Pages
```python
import pymupdf

with pymupdf.open("input.pdf") as document:
    page = document[0]
    page.set_rotation((page.rotation + 90) % 360)
    document.save("rotated.pdf", garbage=4, deflate=True)
```

#### Extract Tables

Try PyMuPDF first. Use `pdfplumber` only as a fallback when its table strategies are needed.

```python
import pymupdf

with pymupdf.open("document.pdf") as document:
    for page in document:
        finder = page.find_tables()
        for table in finder.tables:
            print(table.extract())
```

### pypdf - AcroForms and Low-Level PDF Operations

Keep `pypdf` for canonical AcroForm field-tree inspection/filling, encryption cases not covered by the current PyMuPDF workflow, and low-level object repair. Follow [forms.md](forms.md) for forms. Do not use `pypdf.extract_text()` as the default text extractor.

### reportlab - Create PDFs

#### Basic PDF Creation
```python
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

c = canvas.Canvas("hello.pdf", pagesize=letter)
width, height = letter

# Add text
c.drawString(100, height - 100, "Hello World!")
c.drawString(100, height - 120, "This is a PDF created with reportlab")

# Add a line
c.line(100, height - 140, 400, height - 140)

# Save
c.save()
```

#### Create PDF with Multiple Pages
```python
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet

doc = SimpleDocTemplate("report.pdf", pagesize=letter)
styles = getSampleStyleSheet()
story = []

# Add content
title = Paragraph("Report Title", styles['Title'])
story.append(title)
story.append(Spacer(1, 12))

body = Paragraph("This is the body of the report. " * 20, styles['Normal'])
story.append(body)
story.append(PageBreak())

# Page 2
story.append(Paragraph("Page 2", styles['Heading1']))
story.append(Paragraph("Content for page 2", styles['Normal']))

# Build PDF
doc.build(story)
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

For canvas-drawn text (not Paragraph objects), manually adjust font the size and position rather than using Unicode subscripts/superscripts.

## Common Tasks

### Read Scanned PDFs with Multimodal Vision

Render the pages with `python scripts/convert_pdf_to_images.py scanned.pdf pages/`,
then inspect the PNG files directly with the multimodal model. Preserve page
order and page boundaries when transcribing or summarizing visible text. Render
at higher resolution when small or faint text is not legible.

This workflow supports reading and layout understanding but does not create a
searchable text layer or deterministic word-level coordinates. If the user
requires either, explain that an external OCR backend outside this skill is
needed.

### Add Watermark
```python
import pymupdf

with pymupdf.open("document.pdf") as document, pymupdf.open("watermark.pdf") as watermark:
    for page in document:
        page.show_pdf_page(page.rect, watermark, 0, overlay=True)
    document.save("watermarked.pdf", garbage=4, deflate=True)
```

### Extract Images
```python
from pathlib import Path

import pymupdf

output_dir = Path("images")
output_dir.mkdir(exist_ok=True)

with pymupdf.open("input.pdf") as document:
    seen = set()
    for page_number, page in enumerate(document, start=1):
        for image_number, image in enumerate(page.get_images(full=True), start=1):
            xref = image[0]
            if xref in seen:
                continue
            seen.add(xref)
            data = document.extract_image(xref)
            path = output_dir / f"p{page_number}_img{image_number}.{data['ext']}"
            path.write_bytes(data["image"])
```

### Password Protection
```python
import pymupdf

permissions = int(
    pymupdf.PDF_PERM_ACCESSIBILITY
    | pymupdf.PDF_PERM_PRINT
    | pymupdf.PDF_PERM_COPY
)
with pymupdf.open("input.pdf") as document:
    document.save(
        "encrypted.pdf",
        encryption=pymupdf.PDF_ENCRYPT_AES_256,
        owner_pw="ownerpassword",
        user_pw="userpassword",
        permissions=permissions,
    )
```

## Quick Reference

| Task | Best Tool | Command/Code |
|------|-----------|--------------|
| Render pages to images | PyMuPDF | `page.get_pixmap(matrix=...)` |
| Merge PDFs | PyMuPDF | `output.insert_pdf(source)` |
| Split PDFs | PyMuPDF | `insert_pdf(..., from_page=i, to_page=i)` |
| Extract text | PyMuPDF | `page.get_text("text", sort=True)` |
| Extract tables | PyMuPDF, then pdfplumber fallback | `page.find_tables()` |
| Extract images | PyMuPDF | `document.extract_image(xref)` |
| Add annotations/watermarks | PyMuPDF | `page.add_*_annot()` / `show_pdf_page()` |
| Create PDFs | reportlab | Canvas or Platypus |
| Read scanned PDFs | PyMuPDF + multimodal vision | Render pages, then inspect the images |
| Fill PDF forms | pypdf (see [forms.md](forms.md)) | Keep canonical field-tree handling |

## Next Steps

- For PyMuPDF coordinate extraction and advanced processing, see [reference.md](reference.md)
- For JavaScript libraries (pdf-lib), see [reference.md](reference.md)
- If you need to fill out a PDF form, follow the instructions in [forms.md](forms.md)
- For troubleshooting guides, see [reference.md](reference.md)
