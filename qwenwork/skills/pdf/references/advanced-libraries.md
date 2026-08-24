# Advanced Libraries Reference

Complete reference for pypdfium2, pdf-lib (JavaScript), qpdf CLI, and
advanced pdfplumber / reportlab techniques.

---

## pypdfium2 — High-Performance PDF Rendering

pypdfium2 is a Python binding for PDFium (Chromium's PDF engine) and the
default renderer for this skill. `scripts/convert_pdf_to_images.py`
already wraps it for the standard page-to-image flow. The recipes below
are for ad-hoc use when you need behaviour the script doesn't expose
(custom bitmap formats, page-level text extraction, etc.).

Install: `pip install pypdfium2`

### Render pages to images

```python
import pypdfium2 as pdfium

pdf = pdfium.PdfDocument("document.pdf")

# Render single page at 2× resolution
page = pdf[0]
bitmap = page.render(scale=2.0, rotation=0)
img = bitmap.to_pil()
img.save("page_1.png", "PNG")

# Render all pages to JPEG
for i, page in enumerate(pdf):
    bitmap = page.render(scale=1.5)
    img = bitmap.to_pil()
    img.save(f"page_{i+1}.jpg", "JPEG", quality=90)
```

### Extract text with pypdfium2

```python
import pypdfium2 as pdfium

pdf = pdfium.PdfDocument("document.pdf")
for i, page in enumerate(pdf):
    text = page.get_text()
    print(f"Page {i+1}: {len(text)} chars")
```

---

## pdf-lib — JavaScript PDF Creation and Manipulation

pdf-lib (MIT License) is the standard JS library for PDF operations
in Node.js and browser environments.

Install: `npm install pdf-lib`

### Load and modify an existing PDF

```javascript
import { PDFDocument } from 'pdf-lib';
import fs from 'fs';

async function addPageToPDF() {
    const existingBytes = fs.readFileSync('input.pdf');
    const pdfDoc = await PDFDocument.load(existingBytes);

    const newPage = pdfDoc.addPage([600, 400]);
    newPage.drawText('Added by pdf-lib', { x: 100, y: 300, size: 16 });

    const pdfBytes = await pdfDoc.save();
    fs.writeFileSync('modified.pdf', pdfBytes);
}
```

### Create a PDF with tables from scratch

```javascript
import { PDFDocument, rgb, StandardFonts } from 'pdf-lib';
import fs from 'fs';

async function createInvoicePDF() {
    const pdfDoc = await PDFDocument.create();
    const helvetica = await pdfDoc.embedFont(StandardFonts.Helvetica);
    const helveticaBold = await pdfDoc.embedFont(StandardFonts.HelveticaBold);

    const page = pdfDoc.addPage([595, 842]); // A4
    const { width, height } = page.getSize();

    // Title
    page.drawText('Invoice #12345', {
        x: 50, y: height - 50,
        size: 18, font: helveticaBold,
        color: rgb(0.2, 0.2, 0.8)
    });

    // Header bar
    page.drawRectangle({
        x: 40, y: height - 100,
        width: width - 80, height: 30,
        color: rgb(0.9, 0.9, 0.9)
    });

    // Table rows
    const rows = [
        ['Item', 'Qty', 'Price', 'Total'],
        ['Widget A', '2', '$50', '$100'],
        ['Widget B', '1', '$75', '$75'],
    ];
    let yPos = height - 150;
    for (const row of rows) {
        let xPos = 50;
        for (const cell of row) {
            page.drawText(cell, { x: xPos, y: yPos, size: 12, font: helvetica });
            xPos += 120;
        }
        yPos -= 25;
    }

    fs.writeFileSync('invoice.pdf', await pdfDoc.save());
}
```

### Merge with selective page copying

```javascript
import { PDFDocument } from 'pdf-lib';
import fs from 'fs';

async function selectiveMerge() {
    const merged = await PDFDocument.create();

    const pdf1 = await PDFDocument.load(fs.readFileSync('doc1.pdf'));
    const pdf2 = await PDFDocument.load(fs.readFileSync('doc2.pdf'));

    // All pages from doc1
    const pages1 = await merged.copyPages(pdf1, pdf1.getPageIndices());
    pages1.forEach(p => merged.addPage(p));

    // Only pages 0, 2, 4 from doc2
    const pages2 = await merged.copyPages(pdf2, [0, 2, 4]);
    pages2.forEach(p => merged.addPage(p));

    fs.writeFileSync('merged.pdf', await merged.save());
}
```

---

## pdfjs-dist — JavaScript PDF Rendering (Browser / Node)

PDF.js (Apache License) is Mozilla's PDF renderer. Use it for
in-browser PDF display or text extraction with precise coordinates.

Install: `npm install pdfjs-dist`

### Render a page to canvas

```javascript
import * as pdfjsLib from 'pdfjs-dist';
pdfjsLib.GlobalWorkerOptions.workerSrc = './pdf.worker.js';

async function renderPage() {
    const pdf = await pdfjsLib.getDocument('document.pdf').promise;
    const page = await pdf.getPage(1);
    const viewport = page.getViewport({ scale: 1.5 });

    const canvas = document.createElement('canvas');
    canvas.height = viewport.height;
    canvas.width = viewport.width;

    await page.render({
        canvasContext: canvas.getContext('2d'),
        viewport,
    }).promise;

    document.body.appendChild(canvas);
}
```

### Extract text with bounding coordinates

```javascript
async function extractTextWithCoords(pdfPath) {
    const pdf = await pdfjsLib.getDocument(pdfPath).promise;
    const results = [];

    for (let i = 1; i <= pdf.numPages; i++) {
        const page = await pdf.getPage(i);
        const content = await page.getTextContent();

        const items = content.items.map(item => ({
            text: item.str,
            x: item.transform[4],
            y: item.transform[5],
            width: item.width,
            height: item.height,
        }));
        results.push({ page: i, items });
    }
    return results;
}
```

### Extract annotations (forms, comments)

```javascript
async function readAnnotations(pdfPath) {
    const pdf = await pdfjsLib.getDocument(pdfPath).promise;
    for (let i = 1; i <= pdf.numPages; i++) {
        const page = await pdf.getPage(i);
        const annotations = await page.getAnnotations();
        for (const ann of annotations) {
            console.log(ann.subtype, ann.contents, ann.rect);
        }
    }
}
```

---

## qpdf — Advanced CLI Operations

### Complex page selection and merge

```bash
# Split into groups of 3 pages each
qpdf --split-pages=3 input.pdf output_%02d.pdf

# Extract non-contiguous pages
qpdf input.pdf --pages input.pdf 1,3-5,8,10-end -- extracted.pdf

# Merge specific page ranges from multiple files
qpdf --empty \
     --pages doc1.pdf 1-3 doc2.pdf 5-7 doc3.pdf 2,4 \
     -- combined.pdf
```

### Optimization and repair

```bash
# Linearize for web streaming (fast first-page display)
qpdf --linearize input.pdf optimized.pdf

# Remove unused objects and recompress streams
qpdf --optimize-level=all --recompress-flate input.pdf compressed.pdf

# Check PDF structure integrity
qpdf --check input.pdf

# Attempt to repair a corrupted PDF
qpdf --replace-input corrupted.pdf
```

### Fine-grained permission control

```bash
# Allow printing only — block copy, modify, annotations
qpdf --encrypt "" "ownerpass" 256 \
     --print=full --modify=none --extract=n --annotate=n \
     -- input.pdf restricted.pdf

# Show current encryption settings
qpdf --show-encryption encrypted.pdf
```

---

## pdfplumber — Advanced Python Techniques

### Precise character-level coordinate extraction

```python
import pdfplumber

with pdfplumber.open("document.pdf") as doc:
    page = doc.pages[0]
    # Every character with exact position
    for char in page.chars[:20]:
        print(f"'{char['text']}' at x={char['x0']:.1f} y={char['y0']:.1f}")

    # Extract only text within a bounding box
    region = page.within_bbox((100, 100, 400, 200))
    print(region.extract_text())
```

### Custom table extraction for complex layouts

```python
import pdfplumber, pandas as pd

with pdfplumber.open("complex.pdf") as doc:
    page = doc.pages[0]

    # Text-based column detection (no visible borders)
    settings = {
        "vertical_strategy": "text",
        "horizontal_strategy": "text",
        "intersection_x_tolerance": 10,
        "intersection_y_tolerance": 10,
    }
    tables = page.extract_tables(settings)

    # Visual debug: render page with detected lines
    img = page.to_image(resolution=150)
    img.save("debug_layout.png")
```

---

## reportlab — Professional Python PDF Generation

### Report with styled table

```python
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

data = [
    ['Product', 'Q1', 'Q2', 'Q3', 'Q4'],
    ['Widgets', '120', '135', '142', '158'],
    ['Gadgets', '85', '92', '98', '105'],
]

doc = SimpleDocTemplate("report.pdf")
styles = getSampleStyleSheet()
elements = [Paragraph("Quarterly Sales", styles['Title'])]

table = Table(data)
table.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, 0), 14),
    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
    ('GRID', (0, 0), (-1, -1), 1, colors.black),
]))
elements.append(table)
doc.build(elements)
```

---

## Batch Processing with Error Handling

```python
import glob
import logging
from pathlib import Path
from pypdf import PdfReader, PdfWriter

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

def batch_extract_text(input_dir: str, output_dir: str) -> None:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    for pdf_file in glob.glob(f"{input_dir}/*.pdf"):
        try:
            reader = PdfReader(pdf_file)
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            out_file = out / Path(pdf_file).with_suffix(".txt").name
            out_file.write_text(text, encoding="utf-8")
            log.info(f"Extracted: {pdf_file}")
        except Exception as exc:
            log.error(f"Failed: {pdf_file} — {exc}")
```

### Large PDF chunked processing

```python
from pypdf import PdfReader, PdfWriter

def process_in_chunks(pdf_path: str, chunk_size: int = 10) -> None:
    reader = PdfReader(pdf_path)
    total = len(reader.pages)

    for start in range(0, total, chunk_size):
        end = min(start + chunk_size, total)
        writer = PdfWriter()
        for i in range(start, end):
            writer.add_page(reader.pages[i])
        with open(f"chunk_{start // chunk_size:03d}.pdf", "wb") as fh:
            writer.write(fh)
```

---

## Advanced Cropping

```python
from pypdf import PdfReader, PdfWriter

reader = PdfReader("input.pdf")
writer = PdfWriter()

page = reader.pages[0]
# Crop to region (left, bottom, right, top in PDF points; origin = bottom-left)
page.mediabox.left   = 50
page.mediabox.bottom = 50
page.mediabox.right  = 550
page.mediabox.top    = 750

writer.add_page(page)
with open("cropped.pdf", "wb") as fh:
    writer.write(fh)
```

---

## Performance Tips

| Scenario | Best approach |
|---|---|
| Render pages to images | pypdfium2 (default — `convert_pdf_to_images.py`) |
| Plain text extraction | `pdftotext -bbox-layout` (CLI, fastest) |
| Structured text + tables | pdfplumber |
| Very large PDF (100+ pages) | Process in chunks; use `qpdf --split-pages` first |
| Image extraction | `pdfimages -all` CLI (fastest, original quality) |
| PDF creation in JS environment | pdf-lib |
| PDF viewing in browser | pdfjs-dist |

---

## Library License Summary

| Library | License |
|---|---|
| pypdf | BSD |
| pdfplumber | MIT |
| pypdfium2 | Apache / BSD |
| reportlab | BSD |
| pdf-lib | MIT |
| pdfjs-dist | Apache |
| poppler-utils | GPL-2 |
| qpdf | Apache |
