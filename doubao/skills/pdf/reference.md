# PDF Processing Advanced Reference

This document contains advanced PDF processing features, detailed examples, and additional libraries not covered in the main skill instructions.

## PyMuPDF Advanced Extraction

Use PyMuPDF as the primary library for existing PDFs. See [SKILL.md](SKILL.md) for the standard text, rendering, merge, split, and rotation workflows.

### Extract Structured Text with Coordinates
```python
import pymupdf

with pymupdf.open("document.pdf") as document:
    for page_number, page in enumerate(document, start=1):
        blocks = page.get_text("blocks", sort=True)
        words = page.get_text("words", sort=True)
        structured = page.get_text("dict", sort=True)
        print(page_number, len(blocks), len(words))
```

`blocks` is compact and useful for reading order, `words` is useful for coordinate matching, and `dict` preserves spans, fonts, sizes, colors, and bounding boxes. Keep coordinates for multi-column pages instead of assuming flattened text is semantically ordered.

## JavaScript Libraries

### pdf-lib (MIT License)

pdf-lib is a powerful JavaScript library for creating and modifying PDF documents in any JavaScript environment.

#### Load and Manipulate Existing PDF
```javascript
import { PDFDocument } from 'pdf-lib';
import fs from 'fs';

async function manipulatePDF() {
    // Load existing PDF
    const existingPdfBytes = fs.readFileSync('input.pdf');
    const pdfDoc = await PDFDocument.load(existingPdfBytes);

    // Get page count
    const pageCount = pdfDoc.getPageCount();
    console.log(`Document has ${pageCount} pages`);

    // Add new page
    const newPage = pdfDoc.addPage([600, 400]);
    newPage.drawText('Added by pdf-lib', {
        x: 100,
        y: 300,
        size: 16
    });

    // Save modified PDF
    const pdfBytes = await pdfDoc.save();
    fs.writeFileSync('modified.pdf', pdfBytes);
}
```

#### Create Complex PDFs from Scratch
```javascript
import { PDFDocument, rgb, StandardFonts } from 'pdf-lib';
import fs from 'fs';

async function createPDF() {
    const pdfDoc = await PDFDocument.create();

    // Add fonts
    const helveticaFont = await pdfDoc.embedFont(StandardFonts.Helvetica);
    const helveticaBold = await pdfDoc.embedFont(StandardFonts.HelveticaBold);

    // Add page
    const page = pdfDoc.addPage([595, 842]); // A4 size
    const { width, height } = page.getSize();

    // Add text with styling
    page.drawText('Invoice #12345', {
        x: 50,
        y: height - 50,
        size: 18,
        font: helveticaBold,
        color: rgb(0.2, 0.2, 0.8)
    });

    // Add rectangle (header background)
    page.drawRectangle({
        x: 40,
        y: height - 100,
        width: width - 80,
        height: 30,
        color: rgb(0.9, 0.9, 0.9)
    });

    // Add table-like content
    const items = [
        ['Item', 'Qty', 'Price', 'Total'],
        ['Widget', '2', '$50', '$100'],
        ['Gadget', '1', '$75', '$75']
    ];

    let yPos = height - 150;
    items.forEach(row => {
        let xPos = 50;
        row.forEach(cell => {
            page.drawText(cell, {
                x: xPos,
                y: yPos,
                size: 12,
                font: helveticaFont
            });
            xPos += 120;
        });
        yPos -= 25;
    });

    const pdfBytes = await pdfDoc.save();
    fs.writeFileSync('created.pdf', pdfBytes);
}
```

#### Advanced Merge and Split Operations
```javascript
import { PDFDocument } from 'pdf-lib';
import fs from 'fs';

async function mergePDFs() {
    // Create new document
    const mergedPdf = await PDFDocument.create();

    // Load source PDFs
    const pdf1Bytes = fs.readFileSync('doc1.pdf');
    const pdf2Bytes = fs.readFileSync('doc2.pdf');

    const pdf1 = await PDFDocument.load(pdf1Bytes);
    const pdf2 = await PDFDocument.load(pdf2Bytes);

    // Copy pages from first PDF
    const pdf1Pages = await mergedPdf.copyPages(pdf1, pdf1.getPageIndices());
    pdf1Pages.forEach(page => mergedPdf.addPage(page));

    // Copy specific pages from second PDF (pages 0, 2, 4)
    const pdf2Pages = await mergedPdf.copyPages(pdf2, [0, 2, 4]);
    pdf2Pages.forEach(page => mergedPdf.addPage(page));

    const mergedPdfBytes = await mergedPdf.save();
    fs.writeFileSync('merged.pdf', mergedPdfBytes);
}
```

### pdfjs-dist (Apache License)

PDF.js is Mozilla's JavaScript library for rendering PDFs in the browser.

#### Basic PDF Loading and Rendering
```javascript
import * as pdfjsLib from 'pdfjs-dist';

// Configure worker (important for performance)
pdfjsLib.GlobalWorkerOptions.workerSrc = './pdf.worker.js';

async function renderPDF() {
    // Load PDF
    const loadingTask = pdfjsLib.getDocument('document.pdf');
    const pdf = await loadingTask.promise;

    console.log(`Loaded PDF with ${pdf.numPages} pages`);

    // Get first page
    const page = await pdf.getPage(1);
    const viewport = page.getViewport({ scale: 1.5 });

    // Render to canvas
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');
    canvas.height = viewport.height;
    canvas.width = viewport.width;

    const renderContext = {
        canvasContext: context,
        viewport: viewport
    };

    await page.render(renderContext).promise;
    document.body.appendChild(canvas);
}
```

#### Extract Text with Coordinates
```javascript
import * as pdfjsLib from 'pdfjs-dist';

async function extractText() {
    const loadingTask = pdfjsLib.getDocument('document.pdf');
    const pdf = await loadingTask.promise;

    let fullText = '';

    // Extract text from all pages
    for (let i = 1; i <= pdf.numPages; i++) {
        const page = await pdf.getPage(i);
        const textContent = await page.getTextContent();

        const pageText = textContent.items
            .map(item => item.str)
            .join(' ');

        fullText += `\n--- Page ${i} ---\n${pageText}`;

        // Get text with coordinates for advanced processing
        const textWithCoords = textContent.items.map(item => ({
            text: item.str,
            x: item.transform[4],
            y: item.transform[5],
            width: item.width,
            height: item.height
        }));
    }

    console.log(fullText);
    return fullText;
}
```

#### Extract Annotations and Forms
```javascript
import * as pdfjsLib from 'pdfjs-dist';

async function extractAnnotations() {
    const loadingTask = pdfjsLib.getDocument('annotated.pdf');
    const pdf = await loadingTask.promise;

    for (let i = 1; i <= pdf.numPages; i++) {
        const page = await pdf.getPage(i);
        const annotations = await page.getAnnotations();

        annotations.forEach(annotation => {
            console.log(`Annotation type: ${annotation.subtype}`);
            console.log(`Content: ${annotation.contents}`);
            console.log(`Coordinates: ${JSON.stringify(annotation.rect)}`);
        });
    }
}
```

## Optional Repair Fallback

Default workflows require no system commands. Use PyMuPDF or pypdf for text,
rendering, images, page operations, encryption, and validation. Only use `qpdf`
when both Python libraries cannot open or rewrite a structurally damaged PDF.

Install this optional repair tool only when the failure occurs:

```bash
# macOS
brew install qpdf

# Debian or Ubuntu
sudo apt-get install qpdf
```

Then check and attempt a recoverable rewrite without replacing the source:

```bash
qpdf --check damaged.pdf
qpdf damaged.pdf repaired.pdf
```

Reopen `repaired.pdf` with PyMuPDF and visually verify every page before use.

## Advanced Python Techniques

### pdfplumber Fallback Features

Use these only when PyMuPDF's `find_tables()`, `get_text("words")`, or `get_drawings()` are insufficient for a particular file.

#### Extract Text with Precise Coordinates
```python
import pdfplumber

with pdfplumber.open("document.pdf") as pdf:
    page = pdf.pages[0]

    # Extract all text with coordinates
    chars = page.chars
    for char in chars[:10]:  # First 10 characters
        print(f"Char: '{char['text']}' at x:{char['x0']:.1f} y:{char['y0']:.1f}")

    # Extract text by bounding box (left, top, right, bottom)
    bbox_text = page.within_bbox((100, 100, 400, 200)).extract_text()
```

#### Advanced Table Extraction with Custom Settings
```python
import pdfplumber
import pandas as pd

with pdfplumber.open("complex_table.pdf") as pdf:
    page = pdf.pages[0]

    # Extract tables with custom settings for complex layouts
    table_settings = {
        "vertical_strategy": "lines",
        "horizontal_strategy": "lines",
        "snap_tolerance": 3,
        "intersection_tolerance": 15
    }
    tables = page.extract_tables(table_settings)

    # Visual debugging for table extraction
    img = page.to_image(resolution=150)
    img.save("debug_layout.png")
```

### reportlab Advanced Features

#### Create Professional Reports with Tables
```python
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

# Sample data
data = [
    ['Product', 'Q1', 'Q2', 'Q3', 'Q4'],
    ['Widgets', '120', '135', '142', '158'],
    ['Gadgets', '85', '92', '98', '105']
]

# Create PDF with table
doc = SimpleDocTemplate("report.pdf")
elements = []

# Add title
styles = getSampleStyleSheet()
title = Paragraph("Quarterly Sales Report", styles['Title'])
elements.append(title)

# Add table with advanced styling
table = Table(data)
table.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, 0), 14),
    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
    ('GRID', (0, 0), (-1, -1), 1, colors.black)
]))
elements.append(table)

doc.build(elements)
```

## Complex Workflows

### Extract Figures/Images from PDF

Use PyMuPDF to detect and render image placements:

```python
from pathlib import Path

import pymupdf


def extract_figures(pdf_path, output_dir, min_width=40, min_height=40, scale=2):
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    saved_paths = []
    with pymupdf.open(pdf_path) as document:
        for page_num, page in enumerate(document, start=1):
            image_info = page.get_image_info(xrefs=True)
            for figure_num, info in enumerate(image_info, start=1):
                rect = pymupdf.Rect(info["bbox"])
                if rect.width < min_width or rect.height < min_height:
                    continue

                pixmap = page.get_pixmap(
                    matrix=pymupdf.Matrix(scale, scale),
                    clip=rect,
                    alpha=False,
                )
                figure_path = output_path / (
                    f"page_{page_num}_figure_{figure_num}.png"
                )
                pixmap.save(figure_path)
                saved_paths.append(figure_path)

    return saved_paths


paths = extract_figures("document.pdf", "figures")
print(f"Saved {len(paths)} figure placements")
```

### Batch PDF Processing with Error Handling
```python
import os
import glob
import logging

import pymupdf

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def batch_process_pdfs(input_dir, operation='merge'):
    pdf_files = glob.glob(os.path.join(input_dir, "*.pdf"))

    if operation == 'merge':
        output = pymupdf.open()
        for pdf_file in pdf_files:
            try:
                with pymupdf.open(pdf_file) as source:
                    output.insert_pdf(source)
                logger.info(f"Processed: {pdf_file}")
            except Exception as e:
                logger.error(f"Failed to process {pdf_file}: {e}")
                continue
        output.save("batch_merged.pdf", garbage=4, deflate=True)
        output.close()

    elif operation == 'extract_text':
        for pdf_file in pdf_files:
            try:
                with pymupdf.open(pdf_file) as document:
                    text = "\n\n".join(
                        page.get_text("text", sort=True) for page in document
                    )

                output_file = pdf_file.replace('.pdf', '.txt')
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(text)
                logger.info(f"Extracted text from: {pdf_file}")

            except Exception as e:
                logger.error(f"Failed to extract text from {pdf_file}: {e}")
                continue
```

### Advanced PDF Cropping
```python
import pymupdf

with pymupdf.open("input.pdf") as document:
    page = document[0]
    page.set_cropbox(pymupdf.Rect(50, 50, 550, 750))
    document.save("cropped.pdf", garbage=4, deflate=True)
```

## Performance Optimization Tips

### 1. For Large PDFs
- Use streaming approaches instead of loading entire PDF in memory
- Process pages individually with PyMuPDF and release pixmaps promptly

### 2. For Text Extraction
- Use PyMuPDF `page.get_text("text", sort=True)` by default
- Use `blocks`, `words`, or `dict` when coordinates and structure matter
- Use pdfplumber only as a table/edge-case fallback
- Avoid `pypdf.extract_text()` for large, cropped, or shared-content-stream documents

### 3. For Image Extraction
- Use PyMuPDF `document.extract_image()` for original embedded image bytes
- Use clipped PyMuPDF rendering when the visible placement matters
- Use low resolution for previews, high resolution for final output

### 4. For Form Filling
- Use PyMuPDF for the initial form probe and rendering
- Use the bundled pypdf workflow for canonical AcroForm field-tree values and appearances
- Pre-validate form fields before processing

### 5. Memory Management
```python
import pymupdf

# Process PDFs in chunks
def process_large_pdf(pdf_path, chunk_size=10):
    with pymupdf.open(pdf_path) as source:
        for start_idx in range(0, source.page_count, chunk_size):
            end_idx = min(start_idx + chunk_size, source.page_count) - 1
            output = pymupdf.open()
            output.insert_pdf(source, from_page=start_idx, to_page=end_idx)
            output.save(f"chunk_{start_idx // chunk_size}.pdf")
            output.close()
```

## Troubleshooting Common Issues

### Encrypted PDFs
```python
# Handle password-protected PDFs
import pymupdf

try:
    with pymupdf.open("encrypted.pdf") as document:
        if document.needs_pass and not document.authenticate("password"):
            raise ValueError("Incorrect password")
        print(document.page_count)
except Exception as e:
    print(f"Failed to decrypt: {e}")
```

### Corrupted PDFs

First try opening and rewriting the file with PyMuPDF or pypdf. If both Python
paths fail because of structural damage, use the optional `qpdf` repair workflow
described above. Never replace the source file during repair.

### Text Extraction Issues

If a page has visible text but PyMuPDF returns little or no text, treat it as a
scanned or outlined-text page. Render it with
`python scripts/convert_pdf_to_images.py input.pdf pages/` and inspect the page
images with the multimodal model. Increase render resolution for small or faint
text, preserve page boundaries, and visually verify uncertain passages.

This skill does not bundle a deterministic OCR engine. If the task requires a
searchable text layer, confidence scores, or word-level coordinates, report
that an external OCR backend is required.
