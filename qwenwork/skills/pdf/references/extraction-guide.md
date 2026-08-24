# Extraction Guide

### Layout modes

`extract_content.py` uses `pdfplumber.extract_text()` with `x_tolerance=3, y_tolerance=3`.

- `--layout preserve` (default) — keeps whitespace structure. Best for single-column documents, contracts, reports.
- `--layout plain` — same extraction without preserving whitespace. Use when you just want the words in order.

### Multi-column documents

pdfplumber does not automatically separate columns. For two-column layouts:

```python
import pdfplumber

with pdfplumber.open("two_col.pdf") as doc:
    page = doc.pages[0]
    width = page.width

    # Left column
    left = page.crop((0, 0, width / 2, page.height))
    left_text = left.extract_text()

    # Right column
    right = page.crop((width / 2, 0, width, page.height))
    right_text = right.extract_text()

    full_text = left_text + "\n" + right_text
```

### Header / footer removal

Use `--strip-hf` flag with `extract_content.py` to remove the first and last
line of each page (common for page numbers and running heads).

For more precise removal, crop the page vertically:

```python
# Skip top 50pt and bottom 50pt (header/footer zones)
cropped = page.crop((0, 50, page.width, page.height - 50))
text = cropped.extract_text()
```

---

## Table Extraction Edge Cases

### Tables without visible borders

pdfplumber detects tables using line detection. Tables rendered only with
whitespace (no rules) may not be detected. Try:

```python
settings = {
    "vertical_strategy": "text",
    "horizontal_strategy": "text",
    "intersection_x_tolerance": 10,
    "intersection_y_tolerance": 10,
}
tables = page.extract_tables(settings)
```

### Tables spanning multiple pages

`extract_tables.py` processes each page independently. To merge a table
that spans multiple pages:

1. Extract tables from each page separately (CSV output).
2. Remove the repeated header row from page 2+ files.
3. Concatenate with `pandas.concat()`.

### Merged cells

pdfplumber represents merged cells as repeated values or empty strings.
Post-process with pandas `ffill()` to forward-fill the merged content:

```python
df = pd.DataFrame(rows, columns=headers)
df = df.fillna(method="ffill")
```

---

## Image Extraction Notes

- `extract_images.py` uses pypdf's `page.images` — this extracts inline
  XObject images embedded in the PDF stream.
- Images embedded as Form XObjects (rare) may not be captured by this method.
- Vector graphics (drawn with PDF path operators) are not extractable as images.
  Render the relevant pages with `convert_pdf_to_images.py` (pypdfium2) to
  capture vector content as a raster image.

### Minimum size filter

The `--min-size 20` default skips images smaller than 20×20 pixels,
which are typically decorative bullets, line spacers, or compression artifacts.
Set `--min-size 0` to extract everything.
